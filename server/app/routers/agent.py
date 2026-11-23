"""Route B (TRD section 5): app-owned agent endpoint.

The owner's personal agent authenticates with a per-user personal access token
and applies a batch of already-confirmed, structured items. The review/confirm
conversation happens on the agent's side (e.g. WhatsApp); this endpoint only
accepts what the owner already confirmed. UNVERIFIED until a real end-to-end
call from the agent has been tested (see docs/gap-analysis.md G-T1).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, get_space_for_user, personal_space_of, write_audit
from ..models import (User, Item, Opportunity, Application, Update,
                      VoiceBatch, VoiceItem, AuditLog, AgentToken,
                      APP_STATUSES, ITEM_STATUSES)
from ..security import create_agent_token, resolve_agent_token
from ..serializers import audit_json

router = APIRouter(prefix="/api/agent", tags=["agent"])

MIN_CONFIDENCE = 0.5  # below this the agent must have asked, not guessed


class TokenIn(BaseModel):
    label: str | None = None


class VoiceItemIn(BaseModel):
    parsed_type: str
    destination_space_id: str | None = None  # null => owner's personal space
    payload: dict
    confidence: float | None = None


class ApplyIn(BaseModel):
    client_ref: str
    transcript: str | None = None
    items: list[VoiceItemIn]


@router.post("/tokens", status_code=201)
def make_token(data: TokenIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    tok, raw = create_agent_token(db, user.id, data.label)
    db.commit()
    return {"id": tok.id, "token": raw, "last4": tok.last4,
            "note": "Store this token now. It is shown once and only its hash is kept."}


@router.get("/tokens")
def list_tokens(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    rows = db.query(AgentToken).filter(AgentToken.user_id == user.id).all()
    return [{"id": t.id, "label": t.label, "last4": t.last4, "scopes": t.scopes,
             "revoked": t.revoked_at is not None, "created_at": t.created_at.isoformat()}
            for t in rows]


@router.post("/tokens/{token_id}/revoke")
def revoke_token(token_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    tok = db.get(AgentToken, token_id)
    if not tok or tok.user_id != user.id:
        raise HTTPException(404, "token not found")
    tok.revoked_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.get("/changes")
def agent_changes(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    """Settings > Agent connection: recent agent-made changes on MY data only."""
    rows = db.query(AuditLog).filter(
        AuditLog.actor_type == "agent", AuditLog.actor_id == user.id
    ).order_by(AuditLog.created_at.desc()).limit(50).all()
    return [audit_json(a) for a in rows]


def _apply_one(db, user: User, tok: AgentToken, vi: VoiceItem, batch: VoiceBatch):
    """Apply one confirmed voice item. Returns (table, id). Raises HTTPException
    on any rule violation; the caller rolls back the whole batch."""
    p = vi.parsed_type
    payload = vi.payload or {}

    if p == "todo":
        space_id = vi.destination_space_id or personal_space_of(db, user).id
        space = get_space_for_user(db, space_id, user)  # privacy gate applies to agents too
        item = Item(space_id=space.id, owner_id=user.id, type="todo",
                    title=(payload.get("title") or "").strip(),
                    description=payload.get("description"), status="open",
                    due_date=payload.get("due_date"), source="agent")
        if not item.title:
            raise HTTPException(400, "todo needs a title")
        parent_id = payload.get("parent_id")
        if parent_id:
            parent = db.get(Item, parent_id)
            if not parent or parent.space_id != space.id:
                raise HTTPException(400, "parent item must be in the same space")
            item.parent_id = parent_id
        db.add(item)
        db.flush()
        write_audit(db, "agent", user.id, "create", "items", item.id,
                    after={"title": item.title, "space_id": space.id, "batch": batch.id})
        return "items", item.id

    if p == "item_status":
        item = db.get(Item, payload.get("item_id") or "")
        if not item:
            raise HTTPException(404, "item not found")
        get_space_for_user(db, item.space_id, user)
        status = payload.get("status")
        if status not in ITEM_STATUSES:
            raise HTTPException(400, "bad status")
        before = {"status": item.status}
        item.status = status
        item.updated_at = datetime.utcnow()
        write_audit(db, "agent", user.id, "update", "items", item.id, before=before,
                    after={"status": status, "batch": batch.id})
        return "items", item.id

    if p == "opportunity":
        if not vi.destination_space_id:
            raise HTTPException(400, "opportunity needs a destination group/college space")
        space = get_space_for_user(db, vi.destination_space_id, user)
        if space.type == "personal":
            raise HTTPException(400, "opportunities cannot go to a personal space")
        opp = Opportunity(space_id=space.id, posted_by=user.id,
                          kind=payload.get("kind") or "internship",
                          title=(payload.get("title") or "").strip(), url=payload.get("url"),
                          company=payload.get("company"), deadline=payload.get("deadline"),
                          description=payload.get("description"))
        if not opp.title:
            raise HTTPException(400, "opportunity needs a title")
        db.add(opp)
        db.flush()
        write_audit(db, "agent", user.id, "create", "opportunities", opp.id,
                    after={"title": opp.title, "space_id": space.id, "batch": batch.id})
        return "opportunities", opp.id

    if p == "update":
        space_id = vi.destination_space_id or personal_space_of(db, user).id
        space = get_space_for_user(db, space_id, user)
        u = Update(space_id=space.id, author_id=user.id,
                   kind=payload.get("kind") or "status",
                   body=(payload.get("body") or "").strip())
        if not u.body:
            raise HTTPException(400, "update needs a body")
        db.add(u)
        db.flush()
        write_audit(db, "agent", user.id, "create", "updates", u.id,
                    after={"space_id": space.id, "batch": batch.id})
        return "updates", u.id

    if p == "application":
        app = Application(user_id=user.id, title=(payload.get("title") or "").strip(),
                          company=payload.get("company"), url=payload.get("url"),
                          status=payload.get("status") or "saved",
                          deadline=payload.get("deadline"),
                          next_action=payload.get("next_action"), notes=payload.get("notes"),
                          source="agent")
        if app.status not in APP_STATUSES:
            raise HTTPException(400, "bad application status")
        if not app.title:
            raise HTTPException(400, "application needs a title")
        db.add(app)
        db.flush()
        write_audit(db, "agent", user.id, "create", "applications", app.id,
                    after={"title": app.title, "batch": batch.id})
        return "applications", app.id

    if p == "application_status":
        app = db.get(Application, payload.get("application_id") or "")
        if not app or app.user_id != user.id:
            raise HTTPException(404, "application not found")
        status = payload.get("status")
        if status not in APP_STATUSES:
            raise HTTPException(400, "bad application status")
        before = {"status": app.status}
        app.status = status
        app.updated_at = datetime.utcnow()
        write_audit(db, "agent", user.id, "update", "applications", app.id, before=before,
                    after={"status": status, "batch": batch.id})
        return "applications", app.id

    raise HTTPException(400, f"unsupported parsed_type '{p}'")


@router.post("/apply")
def apply_batch(data: ApplyIn, authorization: str | None = Header(default=None),
                db: OrmSession = Depends(get_db)):
    raw = None
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(None, 1)[1].strip()
    tok = resolve_agent_token(db, raw)
    if not tok:
        raise HTTPException(401, "invalid or revoked agent token")
    user = db.get(User, tok.user_id)

    # Idempotency: a retried client_ref returns the stored result, never
    # double-applies (voice_batches UNIQUE(user_id, client_ref)).
    existing = db.query(VoiceBatch).filter(
        VoiceBatch.user_id == user.id, VoiceBatch.client_ref == data.client_ref).first()
    if existing:
        results = [{"parsed_type": vi.parsed_type, "status": vi.status,
                    "applied_table": vi.applied_table, "applied_id": vi.applied_id,
                    "error": vi.error} for vi in existing.items]
        return {"batch_id": existing.id, "status": "already_applied", "results": results}

    if not data.items:
        raise HTTPException(400, "empty batch")

    batch = VoiceBatch(user_id=user.id, client_ref=data.client_ref,
                       transcript=data.transcript, status="confirmed")
    db.add(batch)
    db.flush()

    applied = []
    try:
        for vi_in in data.items:
            vi = VoiceItem(batch_id=batch.id, parsed_type=vi_in.parsed_type,
                           destination_space_id=vi_in.destination_space_id,
                           payload=vi_in.payload, confidence=vi_in.confidence,
                           status="confirmed")
            # Safety rule: low-confidence items are refused, never guessed.
            if vi_in.confidence is not None and vi_in.confidence < MIN_CONFIDENCE:
                vi.status = "rejected"
                vi.error = f"confidence below {MIN_CONFIDENCE}; should have been clarified in review"
                db.add(vi)
                continue
            table, entity_id = _apply_one(db, user, tok, vi, batch)
            vi.status = "applied"
            vi.applied_table = table
            vi.applied_id = entity_id
            db.add(vi)
            applied.append(vi)
        batch.status = "applied"
        batch.applied_at = datetime.utcnow()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "batch conflict (possible retry race); safe to retry")

    return {"batch_id": batch.id, "status": "applied",
            "results": [{"parsed_type": vi.parsed_type, "status": vi.status,
                         "applied_table": vi.applied_table, "applied_id": vi.applied_id,
                         "error": vi.error} for vi in batch.items]}
