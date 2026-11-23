import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Date, DateTime, ForeignKey, Integer, Float,
    UniqueConstraint, Index, JSON, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from .db import Base


def uid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.utcnow()


SPACE_TYPES = ("personal", "group", "college")
MEMBER_ROLES = ("owner", "member")
ITEM_TYPES = ("todo", "plan", "project", "note")
ITEM_STATUSES = ("open", "in_progress", "done", "archived")
ITEM_SOURCES = ("manual", "voice", "agent")
OPP_KINDS = ("internship", "job", "event", "other")
APP_STATUSES = ("saved", "applied", "assessment", "interview", "offer", "rejected")
UPDATE_KINDS = ("status", "announcement", "progress")
BATCH_STATUSES = ("pending_review", "confirmed", "applied", "cancelled")
VOICE_ITEM_STATUSES = ("pending", "confirmed", "rejected", "applied")
ACTOR_TYPES = ("user", "agent")


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=uid)
    name = Column(Text, nullable=False)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    avatar_url = Column(Text)
    timezone = Column(Text, nullable=False, default="Asia/Kolkata")
    created_at = Column(DateTime, nullable=False, default=utcnow)


class ExternalIdentity(Base):
    __tablename__ = "external_identities"
    id = Column(String(36), primary_key=True, default=uid)
    provider = Column(String(32), nullable=False)
    subject = Column(String(256), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    __table_args__ = (UniqueConstraint("provider", "subject"), UniqueConstraint("provider", "user_id"))


class Session(Base):
    __tablename__ = "sessions"
    token = Column(String(128), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    expires_at = Column(DateTime, nullable=False)


class Space(Base):
    __tablename__ = "spaces"
    id = Column(String(36), primary_key=True, default=uid)
    type = Column(SAEnum(*SPACE_TYPES, name="space_type", native_enum=False), nullable=False)
    name = Column(Text, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        Index("one_personal_space", "created_by", unique=True,
              sqlite_where=(type == "personal"),
              postgresql_where=(type == "personal")),
    )


class SpaceMember(Base):
    __tablename__ = "space_members"
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(SAEnum(*MEMBER_ROLES, name="member_role", native_enum=False), nullable=False, default="member")
    joined_at = Column(DateTime, nullable=False, default=utcnow)


class SpaceInvite(Base):
    __tablename__ = "space_invites"
    token = Column(String(128), primary_key=True)
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)


class Item(Base):
    __tablename__ = "items"
    id = Column(String(36), primary_key=True, default=uid)
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    parent_id = Column(String(36), ForeignKey("items.id"))
    type = Column(SAEnum(*ITEM_TYPES, name="item_type", native_enum=False), nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    status = Column(SAEnum(*ITEM_STATUSES, name="item_status", native_enum=False), nullable=False, default="open")
    due_date = Column(Date)
    sort_order = Column(Integer, nullable=False, default=0)
    source = Column(SAEnum(*ITEM_SOURCES, name="item_source", native_enum=False), nullable=False, default="manual")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Opportunity(Base):
    __tablename__ = "opportunities"
    id = Column(String(36), primary_key=True, default=uid)
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    posted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    kind = Column(SAEnum(*OPP_KINDS, name="opportunity_kind", native_enum=False), nullable=False, default="internship")
    title = Column(Text, nullable=False)
    url = Column(Text)
    company = Column(Text)
    deadline = Column(Date)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class OpportunityResponse(Base):
    __tablename__ = "opportunity_responses"
    opportunity_id = Column(String(36), ForeignKey("opportunities.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(24), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Application(Base):
    __tablename__ = "applications"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(String(36), ForeignKey("opportunities.id"))
    title = Column(Text, nullable=False)
    company = Column(Text)
    url = Column(Text)
    status = Column(SAEnum(*APP_STATUSES, name="application_status", native_enum=False), nullable=False, default="saved")
    deadline = Column(Date)
    resume_version = Column(Text)
    next_action = Column(Text)
    notes = Column(Text)
    source = Column(SAEnum(*ITEM_SOURCES, name="app_source", native_enum=False), nullable=False, default="manual")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "opportunity_id", name="uq_app_user_opp"),
    )


class Update(Base):
    __tablename__ = "updates"
    id = Column(String(36), primary_key=True, default=uid)
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    kind = Column(SAEnum(*UPDATE_KINDS, name="update_kind", native_enum=False), nullable=False, default="status")
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class VoiceBatch(Base):
    __tablename__ = "voice_batches"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    client_ref = Column(Text, nullable=False)
    channel = Column(Text, nullable=False, default="whatsapp")
    transcript = Column(Text)
    status = Column(SAEnum(*BATCH_STATUSES, name="batch_status", native_enum=False), nullable=False, default="pending_review")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    applied_at = Column(DateTime)

    __table_args__ = (UniqueConstraint("user_id", "client_ref", name="uq_batch_user_ref"),)
    items = relationship("VoiceItem", back_populates="batch", cascade="all, delete-orphan")


class VoiceItem(Base):
    __tablename__ = "voice_items"
    id = Column(String(36), primary_key=True, default=uid)
    batch_id = Column(String(36), ForeignKey("voice_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    parsed_type = Column(Text, nullable=False)
    destination_space_id = Column(String(36), ForeignKey("spaces.id"))
    payload = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float)
    status = Column(SAEnum(*VOICE_ITEM_STATUSES, name="voice_item_status", native_enum=False), nullable=False, default="pending")
    applied_table = Column(Text)
    applied_id = Column(String(36))
    error = Column(Text)

    batch = relationship("VoiceBatch", back_populates="items")


class AgentToken(Base):
    __tablename__ = "agent_tokens"
    id = Column(String(36), primary_key=True, default=uid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(Text)
    token_hash = Column(Text, nullable=False, unique=True)
    last4 = Column(String(8), nullable=False)
    scopes = Column(JSON, nullable=False, default=lambda: ["items:write", "updates:write", "applications:write"])
    revoked_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_type = Column(SAEnum(*ACTOR_TYPES, name="actor_type", native_enum=False), nullable=False)
    actor_id = Column(String(36), nullable=False)
    action = Column(Text, nullable=False)
    entity_table = Column(Text, nullable=False)
    entity_id = Column(String(36), nullable=False)
    before = Column(JSON)
    after = Column(JSON)
    created_at = Column(DateTime, nullable=False, default=utcnow)


class Badge(Base):
    __tablename__ = "badges"
    id = Column(String(36), primary_key=True, default=uid)
    space_id = Column(String(36), ForeignKey("spaces.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    rule = Column(JSON)


class MemberBadge(Base):
    __tablename__ = "member_badges"
    badge_id = Column(String(36), ForeignKey("badges.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    awarded_at = Column(DateTime, nullable=False, default=utcnow)


class MatchProfile(Base):
    __tablename__ = "match_profiles"
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    roles = Column(Text, nullable=False, default="")
    keywords = Column(Text, nullable=False, default="")
    resume_text = Column(Text, nullable=False, default="")
