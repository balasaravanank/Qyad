"""Seed dev data: owner + friend, one group, one college space, sample content.
Run: python -m scripts.seed  (from the repo root, with deps installed)"""
from app.db import Base, engine, SessionLocal
from app.models import User, Space, SpaceMember, Item, Opportunity, Application, Update, OpportunityResponse
from datetime import date, timedelta
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

def mkuser(name, email):
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    u = User(name=name, email=email, password_hash=hash_password("password123"))
    db.add(u); db.flush()
    db.add(Space(type="personal", name="My Space", created_by=u.id))
    return u

bala = mkuser("Bala", "bala@example.com")
friend = mkuser("Friend", "friend@example.com")

group = db.query(Space).filter(Space.name == "Internship Hunt").first()
if not group:
    group = Space(type="group", name="Internship Hunt", created_by=bala.id)
    db.add(group); db.flush()
    db.add(SpaceMember(space_id=group.id, user_id=bala.id, role="owner"))
    db.add(SpaceMember(space_id=group.id, user_id=friend.id, role="member"))
    college = Space(type="college", name="College - Year 3", created_by=bala.id)
    db.add(college); db.flush()
    db.add(SpaceMember(space_id=college.id, user_id=bala.id, role="owner"))

    opp = Opportunity(space_id=group.id, posted_by=friend.id, kind="internship",
                      title="SWE Intern, Summer 2027 (demo)", company="Example Corp", deadline=date.today() + timedelta(days=3),
                      url="https://example.com/careers", description="Posted by your friend")
    db.add(opp); db.flush()
    db.add(Application(user_id=bala.id, opportunity_id=opp.id, title=opp.title,
                       company=opp.company, url=opp.url, status="saved",
                       next_action="Tailor resume"))
    for title, company, kind, days, note in [
        ("Frontend Engineer (demo)", "Sample Studio", "job", 0, "Final day. Check eligibility before applying."),
        ("Data Science Internship (demo)", "Demo Labs", "internship", 1, "Portfolio and Python basics required."),
        ("Campus Buildathon (demo)", "Example Campus", "event", 6, "Teams of up to four. Share your project idea."),
        ("Product Design Internship (demo)", "Sample Design", "internship", -2, "Deadline passed. Check the source for an extension."),
        ("Backend Internship (demo)", "Demo Systems", "internship", None, "Deadline unknown. A friend can add it after checking."),
    ]:
        sample = Opportunity(space_id=group.id, posted_by=friend.id, title=title, company=company,
            kind=kind, deadline=date.today()+timedelta(days=days) if days is not None else None,
            url="https://example.com/" + company.lower().replace(" ","-"), description=note)
        db.add(sample); db.flush()
        if days in (1, 6):
            db.add(OpportunityResponse(opportunity_id=sample.id, user_id=friend.id,
                status="applied" if days == 1 else "interested"))
    plan = Item(space_id=[s for s in db.query(Space).filter(Space.created_by == bala.id, Space.type == "personal")][0].id,
                owner_id=bala.id, type="plan", title="This week")
    db.add(plan); db.flush()
    db.add(Item(space_id=plan.space_id, owner_id=bala.id, parent_id=plan.id, type="todo", title="DSA revision"))
    proj = Item(space_id=group.id, owner_id=bala.id, type="project", title="Qyad")
    db.add(proj); db.flush()
    db.add(Item(space_id=group.id, owner_id=bala.id, parent_id=proj.id, type="todo", title="API work", status="in_progress"))
    db.add(Update(space_id=group.id, author_id=bala.id, kind="status", body="Kicked off the workspace app MVP"))

db.commit()
print("Seeded. Login: bala@example.com / password123 (friend@example.com / password123)")
