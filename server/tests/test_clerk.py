import time
from types import SimpleNamespace
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from tests.test_privacy import client, register
from app import clerk_auth as ca


def test_clerk_disabled_by_default(monkeypatch):
    for key in ['CLERK_PUBLISHABLE_KEY','CLERK_SECRET_KEY','CLERK_ISSUER_URL','CLERK_AUTHORIZED_PARTIES']:
        monkeypatch.delenv(key, raising=False)
    assert client().get('/api/auth/config').json()['clerk_enabled'] is False
    assert client().post('/api/auth/clerk',json={'token':'invalid'}).status_code == 503


def claims():
    return {'sub':'user_test','sid':'sess_test','iss':'https://clerk.test','azp':'http://testserver','iat':int(time.time()),'nbf':int(time.time())-1,'exp':int(time.time())+60}


def test_jwt_signature_issuer_origin_expiry_and_pending(monkeypatch):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    monkeypatch.setattr(ca,'settings',lambda:('pk_test_x','sk_test_x','https://clerk.test',['http://testserver'],True))
    monkeypatch.setattr(ca,'jwks_client',lambda _:SimpleNamespace(get_signing_key_from_jwt=lambda t:SimpleNamespace(key=key.public_key())))
    good=claims()
    assert ca.verify_clerk_token(jwt.encode(good,key,algorithm='RS256'))['sub']=='user_test'
    for changes in [{'exp':0},{'iss':'https://wrong.test'},{'azp':'https://attacker.test'},{'sts':'pending'},{'sid':'machine_test'}]:
        with pytest.raises(HTTPException):ca.verify_clerk_token(jwt.encode({**good,**changes},key,algorithm='RS256'))
    wrong=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    with pytest.raises(HTTPException):ca.verify_clerk_token(jwt.encode(good,wrong,algorithm='RS256'))


def test_existing_email_requires_explicit_link_and_keeps_same_user(monkeypatch):
    c=client();user=register(c,'Existing','clerk@example.com')
    monkeypatch.setattr(ca,'verify_clerk_token',lambda t:{'sub':'user_existing'})
    monkeypatch.setattr(ca,'clerk_profile',lambda sub:(user['email'],'Existing'))
    # Router imports verification function directly.
    from app.routers import auth
    monkeypatch.setattr(auth,'verify_clerk_token',ca.verify_clerk_token)
    monkeypatch.setattr(auth,'clerk_profile',ca.clerk_profile)
    assert c.post('/api/auth/clerk',json={'token':'synthetic'}).status_code==409
    assert client().post('/api/auth/clerk/link',json={'token':'synthetic'}).status_code==401
    assert c.post('/api/auth/clerk/link',json={'token':'synthetic'}).status_code==200
    assert c.post('/api/auth/clerk/link',json={'token':'synthetic'}).status_code==200
    assert client().post('/api/auth/clerk',json={'token':'synthetic'}).json()['id']==user['id']
    other=client();register(other,'Other','other@example.com')
    assert other.post('/api/auth/clerk/link',json={'token':'synthetic'}).status_code==409


def test_new_clerk_user_provisions_once_and_bearer_access(monkeypatch):
    from app.routers import auth
    monkeypatch.setattr(auth,'verify_clerk_token',lambda t:{'sub':'user_new'})
    monkeypatch.setattr(ca,'verify_clerk_token',lambda t:{'sub':'user_new'})
    monkeypatch.setattr(ca,'clerk_profile',lambda sub:('new-clerk-test@example.com','New user'))
    c=client();first=c.post('/api/auth/clerk',json={'token':'synthetic'})
    assert first.status_code==200
    assert c.post('/api/auth/clerk',json={'token':'synthetic'}).json()['id']==first.json()['id']
    spaces=c.get('/api/spaces',headers={'Authorization':'Bearer synthetic'}).json()
    assert len([s for s in spaces if s['type']=='personal'])==1


def test_link_rejects_different_verified_email(monkeypatch):
    from app.routers import auth
    c=client();register(c,'A','local@example.com')
    monkeypatch.setattr(auth,'verify_clerk_token',lambda t:{'sub':'user_different'})
    monkeypatch.setattr(auth,'clerk_profile',lambda sub:('different@example.com','Different'))
    assert c.post('/api/auth/clerk/link',json={'token':'synthetic'}).status_code==409


def test_logout_revokes_server_session():
    c=client();register(c,'A','logout@example.com');token=c.cookies.get('ws_session')
    assert c.post('/api/auth/logout').status_code==200
    assert client().get('/api/auth/me',headers={'Cookie':'ws_session='+token}).status_code==401


def test_cross_origin_write_and_sensitive_cache_headers():
    c=client()
    assert c.post('/api/auth/login',json={'email':'a@example.com','password':'bad'},headers={'Origin':'https://wrong.test'}).status_code==403
    r=c.get('/api/health');assert r.headers['cache-control']=='no-store'
    assert r.headers['x-content-type-options']=='nosniff'
