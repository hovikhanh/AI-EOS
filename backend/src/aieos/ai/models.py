"""Model `ai.*` (Database_Design §5). Chỉ dùng nội bộ module `ai`.

Bảng, seed Tool Registry và trigger INV-12 do migration 0013 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "ai"}
_USER = "identity.user_account.id"


class ToolRow(Base):
    __tablename__ = "tool"
    __table_args__ = (
        CheckConstraint("operation_type IN ('READ', 'WRITE', 'EXECUTION')", name="operation_type"),
        CheckConstraint("risk_level IS NULL OR risk_level IN ('LOW', 'MEDIUM', 'HIGH')", name="risk_level"),
        CheckConstraint(
            "max_autonomy_level BETWEEN 0 AND 3 AND (NOT financial OR max_autonomy_level <= 2)", name="autonomy_cap"
        ),
        _SCHEMA,
    )

    name: Mapped[str] = mapped_column(Text, primary_key=True)
    module: Mapped[str] = mapped_column(Text)
    operation_type: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(Text)
    financial: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    max_autonomy_level: Mapped[int] = mapped_column(SmallInteger)
    approval_required: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    params_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class AutonomyPolicyRow(Base):
    __tablename__ = "autonomy_policy"
    __table_args__ = (
        CheckConstraint("level BETWEEN 0 AND 3", name="level"),
        CheckConstraint("version >= 1", name="version"),
        Index(
            "uq_autonomy_policy_tool_role",
            "tool_name",
            "role_code",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("value_threshold IS NULL"),
        ),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tool_name: Mapped[str] = mapped_column(Text, ForeignKey("ai.tool.name"))
    role_code: Mapped[str | None] = mapped_column(Text, ForeignKey("access.role.code"))
    value_threshold: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    level: Mapped[int] = mapped_column(SmallInteger)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class KillSwitchRow(Base):
    __tablename__ = "kill_switch"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton"),
        CheckConstraint("reason <> ''", name="reason"),
        _SCHEMA,
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    enabled: Mapped[bool] = mapped_column(Boolean)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class SettingRow(Base):
    __tablename__ = "setting"
    __table_args__ = (_SCHEMA,)

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[Any] = mapped_column(JSONB)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ActionRow(Base):
    __tablename__ = "action"
    __table_args__ = (
        UniqueConstraint("initiated_by", "idempotency_key"),
        CheckConstraint("effective_level BETWEEN 0 AND 3", name="effective_level"),
        CheckConstraint(
            "status IN ('PENDING_REVIEW', 'NEEDS_REVIEW_STALE', 'EXECUTED', 'REJECTED', 'UNDONE', 'FAILED')",
            name="status",
        ),
        CheckConstraint("idempotency_key <> ''", name="idempotency_key"),
        CheckConstraint(
            "effective_level <> 3 OR executed_at IS NULL OR undo_deadline >= executed_at + interval '24 hours'",
            name="undo_window",
        ),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_action_status_initiated_by", "status", "initiated_by"),
        Index("ix_action_status_stale", "status", "stale_at"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tool_name: Mapped[str] = mapped_column(Text, ForeignKey("ai.tool.name"))
    initiated_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    agent: Mapped[str | None] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    effective_level: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(Text)
    blocked_by_kill_switch: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    idempotency_key: Mapped[str] = mapped_column(Text)
    source_job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("jobs.job.id"))
    result_resource_type: Mapped[str | None] = mapped_column(Text)
    result_resource_id: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_reason: Mapped[str | None] = mapped_column(Text)
    undo_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class CallLogRow(Base):
    __tablename__ = "call_log"
    __table_args__ = (
        CheckConstraint("data_classification NOT IN ('SENSITIVE', 'PERSONAL') OR provider_is_local", name="local_only"),
        Index("ix_call_log_created", "created_at"),
        _SCHEMA,
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str] = mapped_column(Text)
    data_classification: Mapped[str] = mapped_column(Text)
    provider_is_local: Mapped[bool] = mapped_column(Boolean)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    pages: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_estimate: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    outcome: Mapped[str] = mapped_column(Text)
    job_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("jobs.job.id"))
    correlation_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FeedbackRow(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("target_type IN ('ANSWER', 'EXTRACTION', 'SUGGESTION')", name="target_type"),
        CheckConstraint("verdict IN ('UP', 'DOWN')", name="verdict"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
