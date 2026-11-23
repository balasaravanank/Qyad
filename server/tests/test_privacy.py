"""Privacy + agent-pipeline regression tests required by TRD sections 3-4.
Run: pytest -q  (from the repo root)"""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def client():
    return TestClient(app)


_counter = {"n": 0}


def register(c, name, email):
    _counter["n"] += 1
    email = f"{_counter['n']}-{email}"
    r = c.post("/api/auth/register", json={"name": name, "email": email, "password": "secret123"})
    assert r.status_code == 200, r.text
    return r.json()


def make_group(c, name="Internship Hunt"):
    r = c.post("/api/spaces", json={"name": name, "type": "group"})
    assert r.status_code == 201, r.text
    return r.json()


def join_via_invite(owner_c, member_c, space_id):
    r = owner_c.post(f"/api/spaces/{space_id}/invites")
    assert r.status_code == 201, r.text
    token = r.json()["token"]
    r = member_c.post(f"/api/invites/{token}/accept")
    assert r.status_code == 200, r.text
    return r.json()


def personal_space(c):
    return [s for s in c.get("/api/spaces").json() if s["type"] == "personal"][0]


def test_personal_space_invisible_to_other_user():
    a, b = client(), client()
    register(a, "A", "a@example.com")
    register(b, "B", "b@example.com")
    pa = personal_space(a)
    item = a.post(f"/api/spaces/{pa['id']}/items", json={"type": "todo", "title": "private thing"}).json()
    # every read path returns 404 for B (existence not leaked)
    assert b.get(f"/api/spaces/{pa['id']}").status_code == 404
    assert b.get(f"/api/spaces/{pa['id']}/items").status_code == 404
    assert b.patch(f"/api/items/{item['id']}", json={"status": "done"}).status_code == 404
    assert b.delete(f"/api/items/{item['id']}").status_code == 404
    assert all(s["id"] != pa["id"] for s in b.get("/api/spaces").json())


def test_cannot_add_member_to_personal_space():
    a, b = client(), client()
    ua = register(a, "A", "a@example.com")
    ub = register(b, "B", "b@example.com")
    pa = personal_space(a)
    r = a.post(f"/api/spaces/{pa['id']}/members", json={"user_id": ub["id"]})
    assert r.status_code == 400
    r = a.post(f"/api/spaces/{pa['id']}/invites")
    assert r.status_code == 400


def test_cross_space_parent_rejected():
    a = client()
    register(a, "A", "a@example.com")
    pa = personal_space(a)
    priv = a.post(f"/api/spaces/{pa['id']}/items", json={"type": "plan", "title": "my plan"}).json()
    grp = make_group(a)
    r = a.post(f"/api/spaces/{grp['id']}/items",
               json={"type": "todo", "title": "leak attempt", "parent_id": priv["id"]})
    assert r.status_code == 400


def test_applications_are_owner_only():
    a, b = client(), client()
    register(a, "A", "a@example.com")
    register(b, "B", "b@example.com")
    app_row = a.post("/api/applications", json={"title": "Secret application", "notes": "private notes"}).json()
    assert b.get(f"/api/applications/{app_row['id']}").status_code in (404, 405)
    assert b.patch(f"/api/applications/{app_row['id']}", json={"status": "applied"}).status_code == 404
    assert all(x["id"] != app_row["id"] for x in b.get("/api/applications").json())


def test_track_for_me_privacy_and_idempotency():
    a, b = client(), client()
    register(a, "A", "a@example.com")
    register(b, "B", "b@example.com")
    grp = make_group(a)
    join_via_invite(a, b, grp["id"])
    opp = a.post(f"/api/spaces/{grp['id']}/opportunities",
                 json={"title": "SWE Intern", "company": "Corp"}).json()
    t1 = b.post(f"/api/opportunities/{opp['id']}/track")
    assert t1.status_code in (200, 201), t1.text
    t2 = b.post(f"/api/opportunities/{opp['id']}/track")
    assert t2.json()["id"] == t1.json()["id"]  # no duplicate
    # A cannot see B's tracking row
    assert all(x["id"] != t1.json()["id"] for x in a.get("/api/applications").json())
    # the group opportunity is still visible to both
    assert b.get(f"/api/spaces/{grp['id']}/opportunities").json()[0]["tracked_by_me"] is True
    assert a.get(f"/api/spaces/{grp['id']}/opportunities").json()[0]["tracked_by_me"] is False


def test_non_member_cannot_read_group():
    a, b = client(), client()
    register(a, "A", "a@example.com")
    register(b, "B", "b@example.com")
    grp = make_group(a)
    assert b.get(f"/api/spaces/{grp['id']}").status_code == 404
    assert b.get(f"/api/spaces/{grp['id']}/updates").status_code == 404
    assert b.get(f"/api/spaces/{grp['id']}/opportunities").status_code == 404


def test_agent_apply_idempotent_and_audited():
    a = client()
    register(a, "A", "a@example.com")
    pa = personal_space(a)
    tok = a.post("/api/agent/tokens", json={"label": "instinct"}).json()["token"]
    hdr = {"Authorization": f"Bearer {tok}"}
    body = {"client_ref": "batch-001", "items": [
        {"parsed_type": "todo", "payload": {"title": "DSA revision"}, "confidence": 0.95},
    ]}
    r1 = a.post("/api/agent/apply", json=body, headers=hdr)
    assert r1.status_code == 200, r1.text
    r2 = a.post("/api/agent/apply", json=body, headers=hdr)
    assert r2.json()["status"] == "already_applied"
    items = a.get(f"/api/spaces/{pa['id']}/items").json()
    assert len([i for i in items if i["title"] == "DSA revision"]) == 1
    assert items[0]["source"] == "agent"
    changes = a.get("/api/agent/changes").json()
    assert any(c["entity_table"] == "items" and c["actor_type"] == "agent" for c in changes)


def test_agent_respects_privacy_and_confidence():
    a, b = client(), client()
    register(a, "A", "a@example.com")
    register(b, "B", "b@example.com")
    grp_b = make_group(b)  # A is NOT a member
    tok = a.post("/api/agent/tokens", json={}).json()["token"]
    hdr = {"Authorization": f"Bearer {tok}"}
    # agent of A cannot write into B's group
    r = a.post("/api/agent/apply", headers=hdr, json={"client_ref": "x1", "items": [
        {"parsed_type": "update", "destination_space_id": grp_b["id"],
         "payload": {"body": "intrusion"}, "confidence": 0.99}]})
    assert r.status_code == 404
    # low confidence items are rejected, never guessed
    r = a.post("/api/agent/apply", headers=hdr, json={"client_ref": "x2", "items": [
        {"parsed_type": "todo", "payload": {"title": "vague"}, "confidence": 0.2}]})
    assert r.json()["results"][0]["status"] == "rejected"
    pa = personal_space(a)
    assert all(i["title"] != "vague" for i in a.get(f"/api/spaces/{pa['id']}/items").json())
    # revoked token stops working
    tok_id = a.get("/api/agent/tokens").json()[0]["id"]
    a.post(f"/api/agent/tokens/{tok_id}/revoke")
    r = a.post("/api/agent/apply", headers=hdr, json={"client_ref": "x3", "items": [
        {"parsed_type": "todo", "payload": {"title": "after revoke"}, "confidence": 0.9}]})
    assert r.status_code == 401
