"""Optional Clerk integration. Signature, issuer, origin and short session expiry are checked server-side."""
import os
import secrets
from functools import lru_cache
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import HTTPException
from pydantic import BaseModel

from .models import User, Space, ExternalIdentity
from .security import hash_password


def settings():
    pk = os.getenv('CLERK_PUBLISHABLE_KEY', '').strip()
    secret = os.getenv('CLERK_SECRET_KEY', '').strip()
    issuer = os.getenv('CLERK_ISSUER_URL', '').strip().rstrip('/')
    parties = [v.strip().rstrip('/') for v in os.getenv('CLERK_AUTHORIZED_PARTIES', '').split(',') if v.strip()]
    enabled = bool(pk and secret and issuer and parties)
    return pk, secret, issuer, parties, enabled


def public_config():
    pk, _, issuer, _, enabled = settings()
    # Only an explicitly configured HTTPS frontend host is allowed to supply scripts/JWKS.
    host = urlparse(issuer)
    if enabled and (host.scheme != 'https' or not host.hostname or host.path):
        raise HTTPException(503, 'Clerk issuer must be an HTTPS origin without a path')
    return {'clerk_enabled': enabled, 'publishable_key': pk if enabled else '', 'frontend_url': issuer if enabled else '', 'auth_mode': os.getenv('AUTH_MODE', 'clerk' if os.getenv('APP_ENV') == 'production' else 'local')}


@lru_cache(maxsize=4)
def jwks_client(issuer):
    return jwt.PyJWKClient(issuer + '/.well-known/jwks.json', cache_keys=True, lifespan=300, timeout=8)


def verify_clerk_token(token):
    _, _, issuer, parties, enabled = settings()
    if not enabled:
        raise HTTPException(503, 'Clerk is not configured')
    public_config()
    try:
        key = jwks_client(issuer).get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=['RS256'], issuer=issuer,
                            options={'require': ['exp', 'nbf', 'iat', 'sub', 'sid'], 'verify_aud': False}, leeway=5)
        if claims.get('azp') not in parties or claims.get('sts') == 'pending':
            raise ValueError('origin or session status')
        if not claims['sub'].startswith('user_') or not claims['sid'].startswith('sess_'):
            raise ValueError('not a user session')
        return claims
    except Exception:
        raise HTTPException(401, 'Clerk session could not be verified. Sign in again.')


def clerk_profile(subject):
    _, secret, _, _, _ = settings()
    try:
        res = httpx.get('https://api.clerk.com/v1/users/' + subject,
                        headers={'Authorization': 'Bearer ' + secret}, timeout=8)
        res.raise_for_status()
        data = res.json()
        primary = next((v for v in data.get('email_addresses', []) if v['id'] == data.get('primary_email_address_id')), None)
        if not primary or primary.get('verification', {}).get('status') != 'verified':
            raise HTTPException(403, 'Verify your primary email in Clerk first.')
        email = primary['email_address'].strip().lower()
        name = ' '.join(v for v in [data.get('first_name'), data.get('last_name')] if v) or data.get('username') or email.split('@')[0]
        return email, name
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, 'Clerk profile could not be loaded. Try again later.')


def mapped_user(db, subject):
    link = db.query(ExternalIdentity).filter(ExternalIdentity.provider == 'clerk', ExternalIdentity.subject == subject).first()
    return db.get(User, link.user_id) if link else None


def provision_user(db, claims):
    user = mapped_user(db, claims['sub'])
    if user:
        return user
    email, name = clerk_profile(claims['sub'])
    if db.query(User).filter(User.email == email).first():
        # Never auto-merge local data by email, even a verified email.
        raise HTTPException(409, 'This email already has a Qyad account. Log in with your existing password, then use Settings > Link Clerk account.')
    user = User(email=email, name=name, password_hash=hash_password(secrets.token_urlsafe(48)))
    db.add(user); db.flush()
    db.add(Space(type='personal', name='My Space', created_by=user.id))
    db.add(ExternalIdentity(provider='clerk', subject=claims['sub'], user_id=user.id))
    db.commit()
    return user


class ClerkTokenIn(BaseModel):
    token: str


def token_from_request(request):
    auth = request.headers.get('authorization', '')
    return auth[7:] if auth.startswith('Bearer ') else None
