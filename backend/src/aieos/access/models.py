"""Model `access.*` (Database_Design §4, ADR-007). Chỉ dùng nội bộ module `access`.

Bảng, seed và trigger INV-09/10/11 do migration 0005 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "access"}
_USER_FK = "identity.user_account.id"


class RoleRow(Base):
    __tablename__ = "role"
    __table_args__ = (_SCHEMA,)

    code: Mapped[str] = mapped_column(Text, primary_key=True)


class PermissionRow(Base):
    __tablename__ = "permission"
    __table_args__ = (
        CheckConstraint("category IN ('READ', 'WRITE', 'APPROVE', 'ADMIN', 'AI')", name="category"),
        _SCHEMA,
    )

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    category: Mapped[str] = mapped_column(Text)
    assignable: Mapped[bool] = mapped_column(Boolean)


class RolePermissionRow(Base):
    __tablename__ = "role_permission"
    __table_args__ = (CheckConstraint("kind IN ('BASE', 'ELIGIBLE')", name="kind"), _SCHEMA)

    role_code: Mapped[str] = mapped_column(Text, ForeignKey("access.role.code"), primary_key=True)
    permission_code: Mapped[str] = mapped_column(Text, ForeignKey("access.permission.code"), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)


class UserRoleRow(Base):
    __tablename__ = "user_role"
    __table_args__ = (
        CheckConstraint("granted_by IS NULL OR granted_by <> user_id", name="not_self_granted"),
        CheckConstraint("granted_by IS NULL OR (reason IS NOT NULL AND reason <> '')", name="reason_required"),
        _SCHEMA,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK), primary_key=True)
    role_code: Mapped[str] = mapped_column(Text, ForeignKey("access.role.code"), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER_FK))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(Text)


class AssignmentRow(Base):
    __tablename__ = "assignment"
    __table_args__ = (
        CheckConstraint("scope_type IN ('COMPANY', 'ORG_UNIT', 'DOCUMENT_TYPE', 'REVIEW_QUEUE')", name="scope_type"),
        CheckConstraint(
            "(scope_type = 'COMPANY') = (scope_id IS NULL) AND (scope_id IS NULL OR scope_id <> '')", name="scope_id"
        ),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="validity"),
        CheckConstraint("granted_by <> user_id", name="not_self_granted"),
        CheckConstraint("revoked_by IS NULL OR revoked_by <> user_id", name="not_self_revoked"),
        CheckConstraint("(revoked_at IS NULL) = (revoked_by IS NULL)", name="revocation"),
        CheckConstraint("reason <> ''", name="reason"),
        CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="idempotency_hash"),
        UniqueConstraint("granted_by", "idempotency_key"),
        Index("ix_assignment_user", "user_id", "permission_code"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    permission_code: Mapped[str] = mapped_column(Text, ForeignKey("access.permission.code"))
    scope_type: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str | None] = mapped_column(Text)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER_FK))
    idempotency_key: Mapped[str | None] = mapped_column(Text)  # 0008 (T-109, INV-08)
    request_hash: Mapped[str | None] = mapped_column(Text)
