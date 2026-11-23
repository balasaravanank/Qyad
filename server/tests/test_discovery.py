import pytest
from tests.test_privacy import client, register, make_group
from app.routers import discovery as d

FIXTURE = {'data':[
    {'slug':'python-intern','title':'Python Intern','company_name':'Example Ltd','description':'<p>Build APIs with Python, SQL and FastAPI.</p>','url':'https://www.arbeitnow.com/jobs/python-intern','location':'Berlin','remote':True,'created_at':1700000000},
    {'slug':'designer','title':'Designer','company_name':'Demo Studio','description':'Figma and UX','url':'https://www.arbeitnow.com/jobs/designer','location':'Munich','remote':False,'created_at':1700000010},
    {'slug':'bad','title':'Bad URL','url':'javascript://alert(1)','created_at':1700000000},
    {'slug':'other','title':'Wrong domain','url':'https://example.com','created_at':1700000000},
    {'slug':'bad-date','title':'Wrong date','url':'https://www.arbeitnow.com/jobs/x','created_at':'bad'}
]}

@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch):
    monkeypatch.setattr(d,'_cache',{'jobs':[],'fetched_at':None,'attempted_at':0,'error':None})


def signed_in():
    c=client();register(c,'A','discover@example.com');return c


def test_normalization_strips_html_and_rejects_bad_rows():
    jobs=d.normalize_jobs(FIXTURE)
    assert len(jobs)==2
    assert jobs[0]['description']=='Build APIs with Python, SQL and FastAPI.'
    assert jobs[0]['deadline'] is None
    assert jobs[0]['kind']=='internship' and jobs[0]['remote'] is True


def test_profile_private_and_resume_skill_extraction():
    a,b=signed_in(),signed_in()
    r=a.put('/api/match-profile',json={'roles':'Backend Intern','keywords':'python, SQL','resume_text':'Private Name at College. Built projects using React and Docker.'})
    assert r.status_code==200
    terms=r.json()['terms']
    assert all(t in terms for t in ['backend','intern','python','sql','react','docker'])
    assert 'college' not in terms and 'private' not in terms
    assert b.get('/api/match-profile').json()['resume_text']==''
    assert b.get('/api/match-profile').json()['terms']==[]
    a.put('/api/match-profile',json={})
    assert a.get('/api/match-profile').json()['terms']==[]
    assert client().get('/api/match-profile').status_code==401


def test_discovery_ranking_cache_and_no_personal_data_sent(monkeypatch):
    calls=[]
    monkeypatch.setattr(d,'fetch_public_jobs',lambda:(calls.append('static-source-only') or d.normalize_jobs(FIXTURE)))
    a=signed_in();a.put('/api/match-profile',json={'roles':'Backend Intern','keywords':'Python,SQL'})
    first=a.get('/api/discover').json();second=a.get('/api/discover').json()
    assert first['jobs'][0]['id']=='python-intern'
    assert set(first['jobs'][0]['matched_terms'])=={'python','sql','intern'}
    assert len(calls)==1 and first['fetched_at']==second['fetched_at']
    assert client().get('/api/discover').status_code==401


def test_source_failure_returns_empty_or_stale_without_breaking_app(monkeypatch):
    def fail():raise TimeoutError('internal provider detail')
    monkeypatch.setattr(d,'fetch_public_jobs',fail)
    a=signed_in();r=a.get('/api/discover')
    assert r.status_code==200 and r.json()['jobs']==[] and r.json()['error']
    assert 'internal provider detail' not in r.text
    assert a.get('/api/spaces').status_code==200
    d._cache['jobs']=d.normalize_jobs(FIXTURE);d._cache['attempted_at']=0;d._cache['fetched_at']='2026-01-01T00:00:00+00:00'
    r=a.get('/api/discover').json()
    assert len(r['jobs'])==2 and r['error'] and r['fetched_at'].startswith('2026-01-01')


def test_discover_save_private_or_team_idempotent_and_private_profile_not_shared(monkeypatch):
    monkeypatch.setattr(d,'fetch_public_jobs',lambda:d.normalize_jobs(FIXTURE))
    a,b=signed_in(),signed_in();g=make_group(a)
    a.put('/api/match-profile',json={'resume_text':'PRIVATE-RESUME Python','keywords':'SQL'})
    r=a.post('/api/discover/python-intern/save',json={})
    assert r.status_code==200,r.text
    app=r.json()['application']
    assert a.post('/api/discover/python-intern/save',json={}).json()['application']['id']==app['id']
    assert b.get('/api/applications').json()==[]
    assert b.post('/api/discover/python-intern/save',json={'space_id':g['id']}).status_code==404
    r=a.post('/api/discover/python-intern/save',json={'space_id':g['id']})
    assert r.status_code==200,r.text
    opp=r.json()['opportunity']
    assert 'Arbeitnow' in opp['description'] and 'PRIVATE-RESUME' not in str(opp)
    assert a.post('/api/discover/python-intern/save',json={'space_id':g['id']}).json()['opportunity']['id']==opp['id']
    assert len(a.get(f"/api/spaces/{g['id']}/opportunities").json())==1
    assert a.post('/api/discover/no-longer-listed/save',json={}).status_code==404
