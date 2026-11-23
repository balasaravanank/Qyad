"""Shared inbox behavior and regression coverage. Original privacy tests stay unchanged."""
from datetime import date, timedelta, datetime

from tests.test_privacy import client, register, make_group, join_via_invite
from app.db import SessionLocal
from app.models import Opportunity, AuditLog


def setup_team():
    a,b,c=client(),client(),client()
    ua=register(a,'A','a@example.com');ub=register(b,'B','b@example.com');register(c,'C','c@example.com')
    group=make_group(a);join_via_invite(a,b,group['id'])
    return a,b,c,ua,ub,group


def add(c,g,**kw):
    r=c.post(f"/api/spaces/{g['id']}/opportunities",json={'title':'SWE Intern',**kw})
    assert r.status_code==201,r.text
    return r.json()


def test_any_member_can_edit_and_clear_shared_details():
    a,b,c,_,_,g=setup_team();o=add(a,g,deadline='2026-12-01')
    r=b.patch(f"/api/opportunities/{o['id']}",json={'title':'Graduate Engineer','description':'Shared eligibility notes','deadline':None,'kind':'job'})
    assert r.status_code==200,r.text
    row=a.get(f"/api/spaces/{g['id']}/opportunities").json()[0]
    assert row['title']=='Graduate Engineer' and row['deadline'] is None
    assert row['description']=='Shared eligibility notes' and row['kind']=='job'
    assert 'updated_at' in row
    assert a.get(f"/api/audit/opportunities/{o['id']}").json()[0]['action']=='update'
    assert c.patch(f"/api/opportunities/{o['id']}",json={'title':'intrusion'}).status_code==404


def test_opt_in_responses_and_private_tracker_independent():
    a,b,c,ua,ub,g=setup_team();o=add(a,g)
    private=b.post(f"/api/opportunities/{o['id']}/track").json()
    b.patch(f"/api/applications/{private['id']}",json={'status':'interview','notes':'SECRET','resume_version':'PRIVATE'})
    rows=a.get(f"/api/spaces/{g['id']}/opportunities").json()
    assert rows[0]['responses']==[] and rows[0]['tracked_by_me'] is False
    assert 'SECRET' not in str(rows) and 'PRIVATE' not in str(rows)
    r=b.put(f"/api/opportunities/{o['id']}/my-response",json={'status':'applied','user_id':ua['id']})
    assert r.status_code==200
    row=a.get(f"/api/spaces/{g['id']}/opportunities").json()[0]
    assert row['responses']==[{'user_id':ub['id'],'name':'B','status':'applied'}]
    assert row['my_shared_status'] is None
    assert c.put(f"/api/opportunities/{o['id']}/my-response",json={'status':'applied'}).status_code==404
    assert b.put(f"/api/opportunities/{o['id']}/my-response",json={'status':'interview'}).status_code==400
    b.put(f"/api/opportunities/{o['id']}/my-response",json={'status':None})
    assert a.get(f"/api/spaces/{g['id']}/opportunities").json()[0]['responses']==[]
    assert b.get('/api/applications').json()[0]['status']=='interview'


def test_quick_link_normalization_and_duplicates():
    a,b,c,_,_,g=setup_team()
    r=b.post(f"/api/spaces/{g['id']}/opportunities",json={'url':'EXAMPLE.com/careers#section'})
    assert r.status_code==201,r.text
    assert r.json()['url']=='https://example.com/careers' and r.json()['title']=='example.com'
    assert a.post(f"/api/spaces/{g['id']}/opportunities",json={'url':'https://example.com/careers'}).status_code==409
    other=make_group(a,'Different group')
    assert a.post(f"/api/spaces/{other['id']}/opportunities",json={'url':'https://example.com/careers'}).status_code==201
    assert a.post(f"/api/spaces/{g['id']}/opportunities",json={}).status_code==400


def test_link_and_edit_validation():
    a,b,c,_,_,g=setup_team();o=add(a,g)
    for url in ['javascript://alert(1)','data://x','https://user:pass@example.com']:
        assert a.post(f"/api/spaces/{g['id']}/opportunities",json={'url':url}).status_code==422
        assert b.patch(f"/api/opportunities/{o['id']}",json={'url':url}).status_code==422
    assert b.patch(f"/api/opportunities/{o['id']}",json={'title':'  '}).status_code==400
    assert b.patch(f"/api/opportunities/{o['id']}",json={'kind':None}).status_code==400


def test_today_surfaces_deadlines_without_next_action_and_scopes_privacy():
    a,b,c,_,_,g=setup_team();today=date.today()
    o=add(a,g,deadline=(today+timedelta(days=1)).isoformat())
    old=add(a,g,title='Overdue',deadline=(today-timedelta(days=1)).isoformat())
    future=add(a,g,title='Later',deadline=(today+timedelta(days=20)).isoformat())
    private=b.post('/api/applications',json={'title':'Private secret role','deadline':today.isoformat()}).json()
    r=b.get('/api/today').json()
    assert {x['id'] for x in r['shared_deadlines']}=={o['id'],old['id']}
    assert private['id'] in {x['id'] for x in r['private_deadlines']}
    assert a.get('/api/today').json()['private_deadlines']==[]
    assert c.get('/api/today').json()['shared_deadlines']==[]
    b.put(f"/api/opportunities/{o['id']}/my-response",json={'status':'skipped'})
    assert o['id'] not in {x['id'] for x in b.get('/api/today').json()['shared_deadlines']}
    assert o['id'] in {x['id'] for x in a.get('/api/today').json()['shared_deadlines']}


def test_shared_edit_does_not_overwrite_private_snapshot():
    a,b,c,_,_,g=setup_team();o=add(a,g,deadline='2026-12-01')
    private=b.post(f"/api/opportunities/{o['id']}/track").json()
    a.patch(f"/api/opportunities/{o['id']}",json={'title':'Updated shared title','deadline':'2026-12-05'})
    app=b.get('/api/applications').json()[0]
    assert app['title']=='SWE Intern' and app['deadline']=='2026-12-01'
    assert b.post(f"/api/opportunities/{o['id']}/track").json()['id']==private['id']


def test_recent_update_timestamp_changes_and_nonmember_audit_hidden():
    a,b,c,_,_,g=setup_team();o=add(a,g)
    db=SessionLocal();obj=db.get(Opportunity,o['id']);obj.created_at=datetime(2020,1,1)
    db.query(AuditLog).filter(AuditLog.entity_id==o['id']).delete();db.commit();db.close()
    before=a.get(f"/api/spaces/{g['id']}/opportunities").json()[0]
    assert before['updated_at'].startswith('2020')
    b.patch(f"/api/opportunities/{o['id']}",json={'company':'New company'})
    after=a.get(f"/api/spaces/{g['id']}/opportunities").json()[0]
    assert after['updated_at']>before['updated_at']
    assert c.get(f"/api/audit/opportunities/{o['id']}").status_code==404
