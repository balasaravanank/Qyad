import os
from datetime import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from .db import get_db
from .models import User, Session, Space, SpaceMember, AuditLog


def current_user(request: Request, db: OrmSession = Depends(get_db)) -> User:
    from .clerk_auth import token_from_request, verify_clerk_token, mapped_user
    bearer = token_from_request(request)
    if bearer:
        claims = verify_clerk_token(bearer)
        user = mapped_user(db, claims['sub'])
        if not user:
            raise HTTPException(401, 'Complete Clerk sign-in first')
        return user
    if os.getenv('AUTH_MODE', 'clerk' if os.getenv('APP_ENV') == 'production' else 'local') == 'clerk':
        raise HTTPException(401, 'A verified Clerk bearer token is required')
    token = request.cookies.get("ws_session")
    if not token:
        raise HTTPException(401, "not signed in")
    s = db.query(Session).filter(Session.token == token).first()
    if not s or s.expires_at < datetime.utcnow():
        raise HTTPException(401, "session expired")
    user = db.get(User, s.user_id)
    if not user:
        raise HTTPException(401, "unknown user")
    return user


def write_audit(db, actor_type, actor_id, action, table, entity_id, before=None, after=None):
    """Must be called inside the caller's transaction (before commit)."""
    db.add(AuditLog(
        actor_type=actor_type, actor_id=actor_id, action=action,
        entity_table=table, entity_id=str(entity_id), before=before, after=after,
    ))


def get_space_for_user(db, space_id: str, user: User) -> Space:
    """Server-side privacy gate. Personal spaces: owner only, and outsiders get
    404 (existence is not leaked). Group/college: membership required."""
    space = db.get(Space, space_id)
    if not space:
        raise HTTPException(404, "space not found")
    if space.type == "personal":
        if space.created_by != user.id:
            raise HTTPException(404, "space not found")
        return space
    member = db.query(SpaceMember).filter(
        SpaceMember.space_id == space.id, SpaceMember.user_id == user.id
    ).first()
    if not member:
        raise HTTPException(404, "space not found")
    return space


def get_membership(db, space_id: str, user_id: str):
    return db.query(SpaceMember).filter(
        SpaceMember.space_id == space_id, SpaceMember.user_id == user_id
    ).first()


def require_space_owner(db, space: Space, user: User):
    if space.type == "personal":
        if space.created_by != user.id:
            raise HTTPException(404, "space not found")
        return
    m = get_membership(db, space.id, user.id)
    if not m or m.role != "owner":
        raise HTTPException(403, "owner role required")


def personal_space_of(db, user: User) -> Space:
    return db.query(Space).filter(
        Space.created_by == user.id, Space.type == "personal"
    ).first()


def accessible_space_ids(db, user: User):
    ids = [s.id for s in db.query(Space).filter(
        Space.created_by == user.id, Space.type == "personal").all()]
    ids += [m.space_id for m in db.query(SpaceMember).filter(SpaceMember.user_id == user.id).all()]
    return ids
