import os
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user
from ..models import User, Session, Space, ExternalIdentity
from ..security import hash_password, verify_password, create_session
from ..serializers import user_json

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE = "ws_session"

def require_local_mode():
    if os.getenv('AUTH_MODE', 'clerk' if os.getenv('APP_ENV') == 'production' else 'local') != 'local':
        raise HTTPException(403, 'Password login is disabled. Use Clerk.')


class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _set_cookie(response: Response, token: str):
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=30 * 86400, secure=os.getenv("APP_ENV")=="production")


@router.post("/register")
def register(data: RegisterIn, response: Response, db: OrmSession = Depends(get_db)):
    require_local_mode()
    if len(data.password) < 6:
        raise HTTPException(400, "password must be at least 6 characters")
    email = data.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "email already registered")
    user = User(name=data.name.strip(), email=email, password_hash=hash_password(data.password))
    db.add(user)
    db.flush()
    # FR-2: every user gets exactly one personal space at signup.
    db.add(Space(type="personal", name="My Space", created_by=user.id))
    s = create_session(db, user.id)
    db.commit()
    _set_cookie(response, s.token)
    return user_json(user)


@router.post("/login")
def login(data: LoginIn, response: Response, db: OrmSession = Depends(get_db)):
    require_local_mode()
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "wrong email or password")
    s = create_session(db, user.id)
    db.commit()
    _set_cookie(response, s.token)
    return user_json(user)


@router.post("/logout")
def logout(response: Response, request: Request, user: User = Depends(current_user),
           db: OrmSession = Depends(get_db)):
    db.query(Session).filter(Session.token == request.cookies.get(COOKIE, "")).delete()
    db.commit()
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_json(user)


from ..clerk_auth import ClerkTokenIn, public_config, verify_clerk_token, provision_user, mapped_user, clerk_profile

@router.get('/config')
def config():
    return public_config()

@router.post('/clerk')
def clerk_login(data: ClerkTokenIn, db: OrmSession = Depends(get_db)):
    return user_json(provision_user(db, verify_clerk_token(data.token)))

@router.post('/clerk/link')
def clerk_link(data: ClerkTokenIn, request: Request, db: OrmSession = Depends(get_db)):
    require_local_mode()
    # Linking requires the existing local password session, not a supplied bearer identity.
    from datetime import datetime
    session = db.query(Session).filter(Session.token == request.cookies.get(COOKIE, '')).first()
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(401, 'Log in with your existing Qyad password before linking')
    user = db.get(User, session.user_id)
    claims = verify_clerk_token(data.token)
    linked = mapped_user(db, claims['sub'])
    if linked:
        if linked.id != user.id:
            raise HTTPException(409, 'This Clerk account is already linked to another user')
        return {'ok': True}
    if db.query(ExternalIdentity).filter(ExternalIdentity.provider == 'clerk', ExternalIdentity.user_id == user.id).first():
        raise HTTPException(409, 'A Clerk account is already linked. Contact the server owner to change it.')
    email, _ = clerk_profile(claims['sub'])
    if email != user.email:
        raise HTTPException(409, 'Use a Clerk account with the same verified primary email as your Qyad account')
    db.add(ExternalIdentity(provider='clerk', subject=claims['sub'], user_id=user.id)); db.commit()
    return {'ok': True}
