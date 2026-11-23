from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user, write_audit
from ..models import User, Update, UPDATE_KINDS
from ..serializers import update_json


def _with_author(db, u):
    author = db.get(User, u.author_id)
    return {**update_json(u), "author_name": author.name if author else "?"}

router = APIRouter(prefix="/api", tags=["updates"])


class UpdateIn(BaseModel):
    body: str
    kind: str = "status"


@router.get("/spaces/{space_id}/updates")
def list_updates(space_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    get_space_for_user(db, space_id, user)
    rows = db.query(Update).filter(Update.space_id == space_id)\
        .order_by(Update.created_at.desc()).limit(100).all()
    return [_with_author(db, u) for u in rows]


@router.post("/spaces/{space_id}/updates", status_code=201)
def post_update(space_id: str, data: UpdateIn, user: User = Depends(current_user),
                db: OrmSession = Depends(get_db)):
    get_space_for_user(db, space_id, user)
    if data.kind not in UPDATE_KINDS:
        raise HTTPException(400, f"kind must be one of {UPDATE_KINDS}")
    u = Update(space_id=space_id, author_id=user.id, kind=data.kind, body=data.body.strip())
    db.add(u)
    db.flush()
    write_audit(db, "user", user.id, "create", "updates", u.id, after=update_json(u))
    db.commit()
    return _with_author(db, u)
