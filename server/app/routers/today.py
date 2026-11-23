from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as OrmSession

from ..db import get_db
from ..deps import current_user, accessible_space_ids
from ..models import User, Item, Application, Space, Opportunity, OpportunityResponse
from ..serializers import item_json, application_json, opportunity_json

router = APIRouter(prefix="/api", tags=["today"])


@router.get("/today")
def today(user: User = Depends(current_user), db: OrmSession = Depends(get_db)):
    """FR-13 / OPEN-1 (PROPOSED combined view): next actions across every space
    the user can see, each labelled with its space."""
    space_ids = accessible_space_ids(db, user)
    spaces = {s.id: s for s in db.query(Space).filter(Space.id.in_(space_ids)).all()} if space_ids else {}
    try:
        today_d = datetime.now(ZoneInfo(user.timezone)).date()
    except ZoneInfoNotFoundError:
        today_d = date.today()
    items = db.query(Item).filter(
        Item.space_id.in_(space_ids),
        Item.status.in_(["open", "in_progress"]),
        Item.type.in_(["todo"]),
    ).order_by(Item.due_date.asc().nulls_last(), Item.sort_order).all() if space_ids else []

    def label(item):
        s = spaces.get(item.space_id)
        if not s:
            return "?"
        return "Private" if s.type == "personal" else s.name

    overdue, due_today, upcoming = [], [], []
    for i in items:
        row = {**item_json(i), "space_label": label(i)}
        if i.due_date and i.due_date < today_d:
            overdue.append(row)
        elif i.due_date == today_d:
            due_today.append(row)
        else:
            upcoming.append(row)

    apps = db.query(Application).filter(
        Application.user_id == user.id,
        Application.next_action.isnot(None),
        Application.status.notin_(["offer", "rejected"]),
    ).order_by(Application.deadline.asc().nulls_last()).all()
    app_actions = [{**application_json(a), "space_label": "Private"} for a in apps]

    # Deadlines remain useful even when no next action was entered.
    end = today_d + timedelta(days=7)
    private_deadlines = db.query(Application).filter(
        Application.user_id == user.id, Application.deadline.isnot(None),
        Application.deadline <= end, Application.status == "saved"
    ).order_by(Application.deadline).all()
    shared_deadlines = db.query(Opportunity).filter(
        Opportunity.space_id.in_(space_ids), Opportunity.deadline.isnot(None),
        Opportunity.deadline <= end,
    ).order_by(Opportunity.deadline).all() if space_ids else []
    muted = {r.opportunity_id for r in db.query(OpportunityResponse).filter(
        OpportunityResponse.user_id == user.id,
        OpportunityResponse.status.in_(["applied", "skipped"])).all()}
    rows = [{**opportunity_json(o), "space_label": spaces[o.space_id].name}
            for o in shared_deadlines if o.id not in muted]
    return {"shared_deadlines": rows,
            "private_deadlines": [{**application_json(a), "space_label": "Private"} for a in private_deadlines],
            "date": today_d.isoformat(), "overdue": overdue, "due_today": due_today,
            "upcoming": upcoming[:20], "application_actions": app_actions}
