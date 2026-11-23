import json, os, subprocess, sys
from pathlib import Path
from tests.test_privacy import client, register, make_group
from app.routers import discovery as d


def test_versioned_api_and_curated_no_network(monkeypatch):
    monkeypatch.setattr(d, 'fetch_public_jobs', lambda: (_ for _ in ()).throw(AssertionError('network')))
    c=client(); register(c,'V8','v8@example.com')
    assert c.get('/api/v1/health').json()=={'ok':True}
    data=c.get('/api/v1/opportunity-catalog?source=curated').json()
    assert data['source']=='curated'
    assert len(data['jobs'])>=4
    assert all(j['url'].startswith('https://') and j['checked_at']=='2026-11-23' for j in data['jobs'])
    assert {j['kind'] for j in data['jobs']}=={'internship','event'}
    assert c.get('/api/v1/discover').status_code==404
    job=next(j for j in data['jobs'] if j['id']=='kubenine-devops')
    a=c.post('/api/v1/opportunity-catalog/'+job['id']+'/save',json={})
    assert a.status_code==200
    assert '₹15,000' in a.json()['application']['notes']
    assert c.post('/api/v1/opportunity-catalog/'+job['id']+'/save',json={}).json()['already_saved']


def test_clerk_required_rejects_password_and_cookie(monkeypatch):
    c=client();register(c,'Old','v8-old@example.com')
    monkeypatch.setenv('AUTH_MODE','clerk')
    assert c.post('/api/v1/auth/login',json={'email':'x@example.com','password':'x'}).status_code==403
    assert c.post('/api/v1/auth/register',json={'name':'X','email':'x@example.com','password':'secret123'}).status_code==403
    assert c.get('/api/v1/spaces').status_code==401
    assert c.post('/api/v1/auth/clerk/link',json={'token':'x'}).status_code==403


def test_production_fails_closed_without_clerk(tmp_path):
    env={**os.environ,'APP_ENV':'production','AUTH_MODE':'clerk','DATABASE_URL':'sqlite:///'+str(tmp_path/'db')}
    for k in ['CLERK_SECRET_KEY','CLERK_PUBLISHABLE_KEY','CLERK_ISSUER_URL','CLERK_AUTHORIZED_PARTIES']:env.pop(k,None)
    r=subprocess.run([sys.executable,'-c','import app.main'],env=env,capture_output=True)
    assert r.returncode!=0 and b'Production requires' in r.stderr


def test_production_only_versioned_routes(tmp_path):
    env={**os.environ,'APP_ENV':'production','AUTH_MODE':'clerk','PUBLIC_URL':'https://app.example.com','ALLOWED_HOSTS':'testserver',
         'CLERK_SECRET_KEY':'synthetic','CLERK_PUBLISHABLE_KEY':'synthetic','CLERK_ISSUER_URL':'https://clerk.example.com',
         'CLERK_AUTHORIZED_PARTIES':'https://app.example.com','DATABASE_URL':'sqlite:///'+str(tmp_path/'db')}
    code="from app.main import app; from fastapi.testclient import TestClient; c=TestClient(app); assert c.get('/api/v1/health').status_code==200; assert c.get('/api/health').status_code==404; assert c.get('/api/v1/discover').status_code==404; assert c.get('/docs').status_code==404; assert c.get('/api/v1/spaces').status_code==401"
    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True)
    assert result.returncode==0,result.stderr.decode()


def test_sqlite_wal_and_timeout():
    from app.db import engine
    with engine.connect() as c:
        assert c.exec_driver_sql('PRAGMA journal_mode').scalar()=='wal'
        assert c.exec_driver_sql('PRAGMA busy_timeout').scalar()==5000


def test_resume_preview_private_and_no_save():
    c=client();register(c,'Upload','v8-upload@example.com')
    raw=b'Built APIs using Python FastAPI Docker React and Azure. Deployed my own project.'
    assert client().post('/api/v1/match-profile/resume-preview',files={'file':('resume.txt',raw,'text/plain')}).status_code==401
    result=c.post('/api/v1/match-profile/resume-preview',files={'file':('resume.txt',raw,'text/plain')})
    assert result.status_code==200 and 'python' in result.json()['skills']
    assert c.get('/api/v1/match-profile').json()['resume_text']==''
    assert c.post('/api/v1/match-profile/resume-preview',files={'file':('x.docx',raw,'application/octet-stream')}).status_code==415
    assert c.post('/api/v1/match-profile/resume-preview',files={'file':('x.txt',b'x'*2000001,'text/plain')}).status_code==413
    assert c.post('/api/v1/match-profile/resume-preview',files={'file':('x.pdf',b'%PDF-broken','application/pdf')}).status_code==400


def test_explainable_match():
    explanation=d.match_explanation(['python','docker','backend'],{'title':'Backend intern','company':'Test','description':'Python FastAPI'})
    assert explanation['match_score']==57
    assert explanation['matched_terms']==['python','backend']
    assert explanation['missing_skills']==['fastapi']


def test_safe_opportunity_preview_no_arbitrary_fetch():
    c=client();register(c,'Preview','v8-preview@example.com')
    result=c.post('/api/v1/opportunity-preview',json={'url':'https://careers.kubenine.com/jobs/apply/47157073749643768816/'})
    assert result.status_code==200 and result.json()['title']=='Devops Engineer Intern'
    unknown=c.post('/api/v1/opportunity-preview',json={'url':'http://127.0.0.1/private'})
    assert unknown.status_code==200 and unknown.json()['title']==''


def test_text_pdf_success_and_no_original_saved():
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 20 700 Td (Python FastAPI Docker Azure React SQL. Built backend applications.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=io.BytesIO();writer.write(out)
    c=client();register(c,'PDF','v8-pdf@example.com')
    result=c.post('/api/v1/match-profile/resume-preview',files={'file':('resume.pdf',out.getvalue(),'application/pdf')})
    assert result.status_code==200,result.text
    assert 'python' in result.json()['skills'] and 'azure' in result.json()['skills']
    assert c.get('/api/v1/match-profile').json()['resume_text']==''
