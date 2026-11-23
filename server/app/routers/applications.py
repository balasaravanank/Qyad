from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, write_audit
from ..models import User, Application, APP_STATUSES
from ..serializers import application_json

router = APIRouter(prefix="/api/applications", tags=["applications"])


class AppIn(BaseModel):
    title: str
    company: str | None = None
    url: str | None = None
    status: str = "saved"
    deadline: date | None = None
    resume_version: str | None = None
    next_action: str | None = None
    notes: str | None = None


class AppPatch(BaseModel):
    title: str | None = None
    company: str | None = None
    url: str | None = None
    status: str | None = None
    deadline: date | None = None
    resume_version: str | None = None
    next_action: str | None = None
    notes: str | None = None


@router.get("")
def list_apps(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    # Applications are always user-scoped; there is no shared read path.
    apps = db.query(Application).filter(Application.user_id == user.id)\
        .order_by(Application.updated_at.desc()).all()
    return [application_json(a) for a in apps]


@router.post("", status_code=201)
def create_app(data: AppIn, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    if data.status not in APP_STATUSES:
        raise HTTPException(400, f"status must be one of {APP_STATUSES}")
    app = Application(user_id=user.id, title=data.title.strip(), company=data.company,
                      url=data.url, status=data.status, deadline=data.deadline,
                      resume_version=data.resume_version, next_action=data.next_action,
                      notes=data.notes)
    db.add(app)
    db.flush()
    write_audit(db, "user", user.id, "create", "applications", app.id, after=application_json(app))
    db.commit()
    return application_json(app)


def _get_own(db, app_id: str, user: User) -> Application:
    app = db.get(Application, app_id)
    if not app or app.user_id != user.id:
        raise HTTPException(404, "application not found")
    return app


@router.patch("/{app_id}")
def patch_app(app_id: str, data: AppPatch, user: User = Depends(current_user),
              db: OrmSession = Depends(get_db)):
    app = _get_own(db, app_id, user)
    before = application_json(app)
    for field in ("title", "company", "url", "deadline", "resume_version", "next_action", "notes"):
        val = getattr(data, field)
        if field in data.model_fields_set:
            if field == "title" and (val is None or not val.strip()):
                raise HTTPException(400, "Title cannot be empty")
            setattr(app, field, val)
    if data.status is not None:
        if data.status not in APP_STATUSES:
            raise HTTPException(400, f"status must be one of {APP_STATUSES}")
        app.status = data.status
    app.updated_at = datetime.utcnow()
    write_audit(db, "user", user.id, "update", "applications", app.id, before=before,
                after=application_json(app))
    db.commit()
    return application_json(app)


@router.delete("/{app_id}")
def delete_app(app_id: str, user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    app = _get_own(db, app_id, user)
    before = application_json(app)
    db.delete(app)
    write_audit(db, "user", user.id, "delete", "applications", app_id, before=before)
    db.commit()
    return {"ok": True}
