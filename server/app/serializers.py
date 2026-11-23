def iso(v):
    return v.isoformat() if v is not None else None


def user_json(u):
    return {"id": u.id, "name": u.name, "email": u.email,
            "avatar_url": u.avatar_url, "timezone": u.timezone}


def space_json(s, role=None, member_count=None):
    return {"id": s.id, "type": s.type, "name": s.name, "created_by": s.created_by,
            "role": role, "member_count": member_count, "created_at": iso(s.created_at)}


def item_json(i):
    return {"id": i.id, "space_id": i.space_id, "owner_id": i.owner_id,
            "parent_id": i.parent_id, "type": i.type, "title": i.title,
            "description": i.description, "status": i.status,
            "due_date": iso(i.due_date), "sort_order": i.sort_order,
            "source": i.source, "created_at": iso(i.created_at), "updated_at": iso(i.updated_at)}


def opportunity_json(o, tracked=False):
    return {"id": o.id, "space_id": o.space_id, "posted_by": o.posted_by,
            "kind": o.kind, "title": o.title, "url": o.url, "company": o.company,
            "deadline": iso(o.deadline), "description": o.description,
            "tracked_by_me": tracked, "created_at": iso(o.created_at)}


def application_json(a):
    return {"id": a.id, "user_id": a.user_id, "opportunity_id": a.opportunity_id,
            "title": a.title, "company": a.company, "url": a.url, "status": a.status,
            "deadline": iso(a.deadline), "resume_version": a.resume_version,
            "next_action": a.next_action, "notes": a.notes, "source": a.source,
            "created_at": iso(a.created_at), "updated_at": iso(a.updated_at)}


def update_json(u):
    return {"id": u.id, "space_id": u.space_id, "author_id": u.author_id,
            "kind": u.kind, "body": u.body, "created_at": iso(u.created_at)}


def audit_json(a):
    return {"id": a.id, "actor_type": a.actor_type, "action": a.action,
            "entity_table": a.entity_table, "entity_id": a.entity_id,
            "after": a.after, "created_at": iso(a.created_at)}
