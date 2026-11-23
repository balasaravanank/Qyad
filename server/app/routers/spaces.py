import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user, get_membership, require_space_owner, write_audit
from ..models import User, Space, SpaceMember, SpaceInvite
from ..serializers import space_json, user_json

router = APIRouter(prefix="/api", tags=["spaces"])


class CreateSpaceIn(BaseModel):
    name: str
    type: str  # "group" | "college"


class AddMemberIn(BaseModel):
    user_id: str
    role: str = "member"


@router.get("/spaces")
def list_spaces(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    out = []
    personal = db.query(Space).filter(Space.created_by == user.id, Space.type == "personal").first()
    if personal:
        out.append(space_json(personal, role="owner", member_count=1))
    memberships = db.query(SpaceMember).filter(SpaceMember.user_id == user.id).all()
    for m in memberships:
        s = db.get(Space, m.space_id)
        if not s:
            continue
        count = db.query(SpaceMember).filter(SpaceMember.space_id == s.id).count()
        out.append(space_json(s, role=m.role, member_count=count))
    return out


@router.post("/spaces", status_code=201)
def create_space(data: CreateSpaceIn, user: User = Depends(current_user),
                 db: OrmSession = Depends(get_db)):
    if data.type not in ("group", "college"):
        raise HTTPException(400, "type must be 'group' or 'college' (personal spaces are created at signup)")
    space = Space(type=data.type, name=data.name.strip(), created_by=user.id)
    db.add(space)
    db.flush()
    db.add(SpaceMember(space_id=space.id, user_id=user.id, role="owner"))
    write_audit(db, "user", user.id, "create", "spaces", space.id, after={"name": space.name, "type": space.type})
    db.commit()
    return space_json(space, role="owner", member_count=1)


@router.get("/spaces/{space_id}")
def get_space(space_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    space = get_space_for_user(db, space_id, user)
    role = "owner" if space.created_by == user.id else (get_membership(db, space.id, user.id) or None)
    if space.type != "personal":
        m = get_membership(db, space.id, user.id)
        role = m.role if m else None
        members = db.query(SpaceMember).filter(SpaceMember.space_id == space.id).all()
        member_list = []
        for mm in members:
            u = db.get(User, mm.user_id)
            member_list.append({"user": user_json(u), "role": mm.role, "joined_at": mm.joined_at.isoformat()})
    else:
        role = "owner"
        member_list = [{"user": user_json(user), "role": "owner", "joined_at": None}]
    return {**space_json(space, role=role, member_count=len(member_list)), "members": member_list}


@router.post("/spaces/{space_id}/members", status_code=201)
def add_member(space_id: str, data: AddMemberIn, user: User = Depends(current_user),
               db: OrmSession = Depends(get_db)):
    space = get_space_for_user(db, space_id, user)
    # Privacy rule: membership must never grant access to a personal space.
    if space.type == "personal":
        raise HTTPException(400, "members cannot be added to a personal space")
    require_space_owner(db, space, user)
    if data.role not in ("owner", "member"):
        raise HTTPException(400, "invalid role")
    if not db.get(User, data.user_id):
        raise HTTPException(404, "user not found")
    if get_membership(db, space.id, data.user_id):
        raise HTTPException(409, "already a member")
    db.add(SpaceMember(space_id=space.id, user_id=data.user_id, role=data.role))
    write_audit(db, "user", user.id, "create", "space_members", f"{space.id}:{data.user_id}",
                after={"role": data.role})
    db.commit()
    return {"ok": True}


@router.post("/spaces/{space_id}/invites", status_code=201)
def create_invite(space_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    space = get_space_for_user(db, space_id, user)
    if space.type == "personal":
        raise HTTPException(400, "personal spaces cannot be shared")
    require_space_owner(db, space, user)
    inv = SpaceInvite(
        token=secrets.token_urlsafe(24),
        space_id=space.id,
        created_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(inv)
    db.commit()
    return {"token": inv.token, "join_path": f"/?join={inv.token}", "expires_at": inv.expires_at.isoformat()}


@router.post("/invites/{token}/accept")
def accept_invite(token: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    inv = db.get(SpaceInvite, token)
    if not inv or inv.revoked_at is not None or inv.expires_at < datetime.utcnow():
        raise HTTPException(404, "invite invalid or expired")
    space = db.get(Space, inv.space_id)
    if not space or space.type == "personal":
        raise HTTPException(400, "cannot join a personal space")
    if not get_membership(db, space.id, user.id):
        db.add(SpaceMember(space_id=space.id, user_id=user.id, role="member"))
        write_audit(db, "user", user.id, "create", "space_members", f"{space.id}:{user.id}",
                    after={"role": "member", "via": "invite"})
        db.commit()
    count = db.query(SpaceMember).filter(SpaceMember.space_id == space.id).count()
    m = get_membership(db, space.id, user.id)
    return space_json(space, role=m.role if m else "member", member_count=count)
