"""Model `identity.*` (Database_Design §4, ADR-006). Chỉ dùng nội bộ module `identity`.

Bảng do migration 0004 tạo (0007 thêm `user_account.mfa_last_step`); model phải khớp schema (TC-MIG-01). Token, mã
khôi phục, email trong `login_attempt` chỉ lưu dạng băm SHA-256 32 byte (INV-16).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, CITEXT
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "identity"}
_USER_FK = "identity.user_account.id"


class UserAccountRow(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        UniqueConstraint("email"),
        UniqueConstraint("employee_id"),
        CheckConstraint("status IN ('INVITED', 'ACTIVE', 'LOCKED', 'DISABLED')", name="status"),
        CheckConstraint("(status = 'INVITED') = (password_hash IS NULL)", name="password_iff_not_invited"),
        CheckConstraint("NOT mfa_enabled OR mfa_secret_enc IS NOT NULL", name="mfa_secret"),
        CheckConstraint("failed_login_count >= 0", name="failed_login_count"),
        CheckConstraint("version >= 1", name="version"),
        CheckConstraint("display_name <> ''", name="display_name"),
        CheckConstraint("mfa_last_step >= 0", name="mfa_last_step"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT)
    display_name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str | None] = mapped_column(Text)
    mfa_secret_enc: Mapped[bytes | None] = mapped_column(BYTEA)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    must_enroll_mfa: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    mfa_last_step: Mapped[int | None] = mapped_column(BigInteger)  # bước TOTP đã dùng gần nhất (0007, T-103)
    failed_login_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # FK org.employee thêm ở T-201
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER_FK))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class SessionRow(Base):
    __tablename__ = "session"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        CheckConstraint("octet_length(token_hash) = 32", name="token_hash_sha256"),
        CheckConstraint("csrf_token_hash IS NULL OR octet_length(csrf_token_hash) = 32", name="csrf_hash_sha256"),
        CheckConstraint("absolute_expires_at > created_at", name="absolute_after_created"),
        Index("ix_session_active_user", "user_id", postgresql_where=text("revoked_at IS NULL")),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    token_hash: Mapped[bytes] = mapped_column(BYTEA)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    csrf_token_hash: Mapped[bytes | None] = mapped_column(BYTEA)
    mfa_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reauth_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    idle_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    absolute_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(Text)
    user_agent: Mapped[str | None] = mapped_column(Text)


class InvitationRow(Base):
    __tablename__ = "invitation"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        CheckConstraint("octet_length(token_hash) = 32", name="token_hash_sha256"),
        CheckConstraint("used_at IS NULL OR revoked_at IS NULL", name="used_or_revoked"),
        Index(
            "uq_invitation_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    token_hash: Mapped[bytes] = mapped_column(BYTEA)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MfaRecoveryCodeRow(Base):
    __tablename__ = "mfa_recovery_code"
    __table_args__ = (
        UniqueConstraint("user_id", "code_hash"),
        CheckConstraint("octet_length(code_hash) = 32", name="code_hash_sha256"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    code_hash: Mapped[bytes] = mapped_column(BYTEA)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginAttemptRow(Base):
    __tablename__ = "login_attempt"
    __table_args__ = (
        CheckConstraint("octet_length(email_hash) = 32", name="email_hash_sha256"),
        Index("ix_login_attempt_email", "email_hash", "occurred_at"),
        Index("ix_login_attempt_ip", "ip", "occurred_at"),
        _SCHEMA,
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    email_hash: Mapped[bytes] = mapped_column(BYTEA)
    ip: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    success: Mapped[bool] = mapped_column(Boolean)
