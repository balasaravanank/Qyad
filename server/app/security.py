import hashlib
import hmac
import secrets
from datetime import datetime, timedelta

from .models import Session, AgentToken

PBKDF2_ROUNDS = 120_000
SESSION_DAYS = 30


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, hexdigest = stored.split("$", 1)
    except ValueError:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ROUNDS)
    return hmac.compare_digest(digest.hex(), hexdigest)


def create_session(db, user_id: str) -> Session:
    s = Session(
        token=secrets.token_urlsafe(32),
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
    )
    db.add(s)
    return s


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_agent_token(db, user_id: str, label: str | None = None):
    raw = "wst_" + secrets.token_urlsafe(32)
    tok = AgentToken(user_id=user_id, label=label, token_hash=hash_token(raw), last4=raw[-4:])
    db.add(tok)
    return tok, raw


def resolve_agent_token(db, raw: str):
    if not raw:
        return None
    tok = db.query(AgentToken).filter(AgentToken.token_hash == hash_token(raw)).first()
    if not tok or tok.revoked_at is not None:
        return None
    return tok
