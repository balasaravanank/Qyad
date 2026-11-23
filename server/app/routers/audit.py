"""Per-entity audit reads for the UI detail views (UI spec section 3.5).

The item/application detail modal shows an audit line such as
"Updated by Instinct, Nov 21, 8:40 PM". Read-only; the same privacy gates as
the entity itself apply.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user
from ..models import User, Item, Application, Opportunity, Update, AuditLog
from ..serializers import audit_json

router = APIRouter(prefix="/api", tags=["audit"])

_TABLES = {"items", "applications", "opportunities", "updates"}


@router.get("/audit/{table}/{entity_id}")
def entity_audit(table: str, entity_id: str, user: User = Depends(current_user),
                 db: OrmSession = Depends(get_db)):
    if table not in _TABLES:
        raise HTTPException(404, "unknown table")
    if table == "items":
        obj = db.get(Item, entity_id)
        if not obj:
            raise HTTPException(404, "not found")
        get_space_for_user(db, obj.space_id, user)
    elif table == "applications":
        obj = db.get(Application, entity_id)
        if not obj or obj.user_id != user.id:
            raise HTTPException(404, "not found")
    elif table == "opportunities":
        obj = db.get(Opportunity, entity_id)
        if not obj:
            raise HTTPException(404, "not found")
        get_space_for_user(db, obj.space_id, user)
    else:
        obj = db.get(Update, entity_id)
        if not obj:
            raise HTTPException(404, "not found")
        get_space_for_user(db, obj.space_id, user)
    rows = db.query(AuditLog).filter(
        AuditLog.entity_table == table, AuditLog.entity_id == entity_id
    ).order_by(AuditLog.created_at.desc()).limit(10).all()
    return [audit_json(r) for r in rows]
