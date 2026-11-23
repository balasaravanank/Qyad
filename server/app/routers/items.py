from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user, write_audit
from ..models import User, Item, ITEM_TYPES, ITEM_STATUSES
from ..serializers import item_json

router = APIRouter(prefix="/api", tags=["items"])


class ItemIn(BaseModel):
    type: str = "todo"
    title: str
    description: str | None = None
    status: str = "open"
    due_date: date | None = None
    parent_id: str | None = None
    sort_order: int | None = None


class ItemPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: date | None = None
    parent_id: str | None = None
    sort_order: int | None = None


def _validate(data_type, status):
    if data_type not in ITEM_TYPES:
        raise HTTPException(400, f"type must be one of {ITEM_TYPES}")
    if status not in ITEM_STATUSES:
        raise HTTPException(400, f"status must be one of {ITEM_STATUSES}")


def _check_parent(db, space_id: str, parent_id: str | None):
    """Cross-space references are refused so a shared item can never expose a
    private parent (TRD section 3)."""
    if parent_id is None:
        return
    parent = db.get(Item, parent_id)
    if not parent:
        raise HTTPException(400, "parent item not found")
    if parent.space_id != space_id:
        raise HTTPException(400, "parent item must belong to the same space")


@router.get("/spaces/{space_id}/items")
def list_items(space_id: str, type: str | None = None, status: str | None = None,
               user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    get_space_for_user(db, space_id, user)
    q = db.query(Item).filter(Item.space_id == space_id)
    if type:
        q = q.filter(Item.type == type)
    if status:
        q = q.filter(Item.status == status)
    items = q.order_by(Item.sort_order, Item.created_at).all()
    return [item_json(i) for i in items]


@router.post("/spaces/{space_id}/items", status_code=201)
def create_item(space_id: str, data: ItemIn, user: User = Depends(current_user),
                db: OrmSession = Depends(get_db)):
    get_space_for_user(db, space_id, user)
    _validate(data.type, data.status)
    _check_parent(db, space_id, data.parent_id)
    if data.sort_order is None:
        top = db.query(Item).filter(Item.space_id == space_id).order_by(Item.sort_order.desc()).first()
        data.sort_order = (top.sort_order + 1) if top else 0
    item = Item(space_id=space_id, owner_id=user.id, type=data.type, title=data.title.strip(),
                description=data.description, status=data.status, due_date=data.due_date,
                parent_id=data.parent_id, sort_order=data.sort_order)
    db.add(item)
    db.flush()
    write_audit(db, "user", user.id, "create", "items", item.id, after=item_json(item))
    db.commit()
    return item_json(item)


def _get_item_for_user(db, item_id: str, user: User) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(404, "item not found")
    get_space_for_user(db, item.space_id, user)
    return item


@router.patch("/items/{item_id}")
def patch_item(item_id: str, data: ItemPatch, user: User = Depends(current_user),
               db: OrmSession = Depends(get_db)):
    item = _get_item_for_user(db, item_id, user)
    before = item_json(item)
    if data.status is not None:
        _validate(item.type, data.status)
        item.status = data.status
    if data.title is not None:
        item.title = data.title.strip()
    if data.description is not None:
        item.description = data.description
    if data.due_date is not None:
        item.due_date = data.due_date
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    if data.parent_id is not None:
        _check_parent(db, item.space_id, data.parent_id)
        item.parent_id = data.parent_id
    item.updated_at = datetime.utcnow()
    write_audit(db, "user", user.id, "update", "items", item.id, before=before, after=item_json(item))
    db.commit()
    return item_json(item)


@router.delete("/items/{item_id}")
def delete_item(item_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    item = _get_item_for_user(db, item_id, user)
    before = item_json(item)
    db.delete(item)
    write_audit(db, "user", user.id, "delete", "items", item_id, before=before)
    db.commit()
    return {"ok": True}
