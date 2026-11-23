from datetime import date
from urllib.parse import urlsplit, urlunsplit

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy import func

from ..db import get_db
from ..deps import current_user, get_space_for_user, write_audit
from ..models import User, Opportunity, Application, OpportunityResponse, SpaceMember, AuditLog, OPP_KINDS
from ..serializers import opportunity_json, application_json

router = APIRouter(prefix="/api", tags=["opportunities"])
SHARED_STATUSES = ("interested", "applied", "skipped")


def clean_url(value):
    if not value:
        return None
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Use a normal http or https link, without a username or password")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


class OppIn(BaseModel):
    title: str = ""
    kind: str = "internship"
    url: str | None = None
    company: str | None = None
    deadline: date | None = None
    description: str | None = None
    _url = field_validator("url")(clean_url)


class OppPatch(BaseModel):
    title: str | None = None
    kind: str | None = None
    url: str | None = None
    company: str | None = None
    deadline: date | None = None
    description: str | None = None
    _url = field_validator("url")(clean_url)


class ResponseIn(BaseModel):
    status: str | None = None


def _check_kind(kind):
    if kind not in OPP_KINDS:
        raise HTTPException(400, f"kind must be one of {OPP_KINDS}")


def _opp(db, opp_id, user):
    obj = db.get(Opportunity, opp_id)
    if not obj:
        raise HTTPException(404, "opportunity not found")
    get_space_for_user(db, obj.space_id, user)
    return obj


def shared_opportunity(db, opp, user, tracked=False):
    # Shared responses are deliberate disclosures. Never derive them from private applications.
    rows = db.query(OpportunityResponse, User).join(User, User.id == OpportunityResponse.user_id).join(
        SpaceMember, (SpaceMember.user_id == User.id) & (SpaceMember.space_id == opp.space_id)
    ).filter(OpportunityResponse.opportunity_id == opp.id).all()
    responses = [{"user_id": r.user_id, "name": u.name, "status": r.status} for r, u in rows]
    updated = db.query(func.max(AuditLog.created_at)).filter(
        AuditLog.entity_table == "opportunities", AuditLog.entity_id == opp.id).scalar() or opp.created_at
    return {**opportunity_json(opp, tracked), "updated_at": updated.isoformat() + "Z", "responses": responses,
            "my_shared_status": next((r["status"] for r in responses if r["user_id"] == user.id), None)}


def _duplicate(db, space_id, url, exclude=None):
    if not url:
        return
    q = db.query(Opportunity).filter(Opportunity.space_id == space_id, Opportunity.url == url)
    if exclude:
        q = q.filter(Opportunity.id != exclude)
    if q.first():
        raise HTTPException(409, "This link is already in this space. Search the table to update it instead.")


class PreviewIn(BaseModel):
    url: str
    _url = field_validator("url")(clean_url)


@router.post("/opportunity-preview")
def preview_opportunity(data: PreviewIn, user: User = Depends(current_user)):
    # No arbitrary URL fetch: avoids server-side request forgery and untrusted page execution.
    # Known checked sources fill exact recorded details. Unknown links require human review.
    from .discovery import curated_jobs
    job = next((j for j in curated_jobs() if clean_url(j['url']) == data.url), None)
    if job:
        return {k:job.get(k) for k in ('title','company','kind','url','deadline','description','location')}
    return {"title":"", "company":"", "kind":"internship", "url":data.url,
            "description":"Open the source and add its real title, company, location and eligibility. This link has not been verified."}


@router.get("/spaces/{space_id}/opportunities")
def list_opps(space_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    space = get_space_for_user(db, space_id, user)
    if space.type == "personal":
        raise HTTPException(400, "opportunities live in group and college spaces")
    opps = db.query(Opportunity).filter(Opportunity.space_id == space_id).order_by(
        Opportunity.deadline.asc().nulls_last(), Opportunity.created_at.desc()).all()
    tracked = {a.opportunity_id for a in db.query(Application).filter(Application.user_id == user.id).all()}
    from .discovery import profile_terms, match_explanation
    from ..models import MatchProfile
    terms=profile_terms(db.get(MatchProfile,user.id))
    result=[]
    for o in opps:
        record=shared_opportunity(db,o,user,o.id in tracked)
        record.update(match_explanation(terms, {'title':o.title,'company':o.company or '', 'description':o.description or ''}))
        result.append(record)
    return result


@router.post("/spaces/{space_id}/opportunities", status_code=201)
def create_opp(space_id: str, data: OppIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    space = get_space_for_user(db, space_id, user)
    if space.type == "personal":
        raise HTTPException(400, "Use your private applications tracker for personal finds")
    _check_kind(data.kind)
    title = data.title.strip() or (urlsplit(data.url).hostname if data.url else "")
    if not title:
        raise HTTPException(400, "Add a title or paste a link")
    _duplicate(db, space_id, data.url)
    opp = Opportunity(space_id=space_id, posted_by=user.id, kind=data.kind,
                      title=title, url=data.url, company=data.company,
                      deadline=data.deadline, description=data.description)
    db.add(opp)
    db.flush()
    write_audit(db, "user", user.id, "create", "opportunities", opp.id, after=opportunity_json(opp))
    db.commit()
    return shared_opportunity(db, opp, user)


@router.patch("/opportunities/{opp_id}")
def edit_opp(opp_id: str, data: OppPatch, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    opp = _opp(db, opp_id, user)
    changes = data.model_dump(exclude_unset=True)
    if "kind" in changes:
        _check_kind(changes["kind"])
    if "title" in changes:
        if not changes["title"] or not changes["title"].strip():
            raise HTTPException(400, "Title cannot be empty")
        changes["title"] = changes["title"].strip()
    if "url" in changes:
        _duplicate(db, opp.space_id, changes["url"], opp.id)
    before = opportunity_json(opp)
    for key, val in changes.items():
        setattr(opp, key, val)
    write_audit(db, "user", user.id, "update", "opportunities", opp.id, before=before, after=opportunity_json(opp))
    db.commit()
    return shared_opportunity(db, opp, user)


@router.put("/opportunities/{opp_id}/my-response")
def respond(opp_id: str, data: ResponseIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    opp = _opp(db, opp_id, user)
    if data.status is not None and data.status not in SHARED_STATUSES:
        raise HTTPException(400, "Choose interested, applied, skipped, or clear your status")
    row = db.get(OpportunityResponse, (opp_id, user.id))
    if data.status is None:
        if row:
            db.delete(row)
    elif row:
        row.status = data.status
    else:
        db.add(OpportunityResponse(opportunity_id=opp_id, user_id=user.id, status=data.status))
    write_audit(db, "user", user.id, "share_status", "opportunities", opp.id,
                after={"user_id": user.id, "status": data.status})
    db.commit()
    return shared_opportunity(db, opp, user)


@router.post("/opportunities/{opp_id}/track", status_code=201)
def track_opp(opp_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    """Copy to the caller's private tracker, never remove or publish private activity."""
    opp = _opp(db, opp_id, user)
    existing = db.query(Application).filter(Application.user_id == user.id, Application.opportunity_id == opp.id).first()
    if existing:
        return {**application_json(existing), "already_tracked": True}
    app = Application(user_id=user.id, opportunity_id=opp.id, title=opp.title,
                      company=opp.company, url=opp.url, deadline=opp.deadline, status="saved")
    db.add(app)
    db.flush()
    write_audit(db, "user", user.id, "create", "applications", app.id,
                after={"title": app.title, "from_opportunity": opp.id})
    db.commit()
    return application_json(app)
