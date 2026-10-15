"""Model `jobs.job`, `jobs.schedule` (Database_Design §5, ADR-005). Chỉ dùng nội bộ module `jobs`.

Bảng do migration 0003 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Interval,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_JOB_CLASSES = "('ORCHESTRATION', 'AI_CONTENT', 'BUSINESS_WRITE')"


class JobRow(Base):
    __tablename__ = "job"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint(f"job_class IN {_JOB_CLASSES}", name="job_class"),
        CheckConstraint("status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'DEAD', 'CANCELLED')", name="status"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint("attempts >= 0 AND attempts <= max_attempts", name="attempts_within_max"),
        CheckConstraint(
            "status <> 'RUNNING' OR (lease_expires_at IS NOT NULL AND locked_by IS NOT NULL)", name="running_lease"
        ),
        CheckConstraint("kind <> '' AND idempotency_key <> ''", name="not_empty"),
        Index("ix_job_claim", "run_after", "id", postgresql_where=text("status = 'QUEUED'")),
        Index("ix_job_reaper", "lease_expires_at", postgresql_where=text("status = 'RUNNING'")),
        {"schema": "jobs"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    job_class: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'QUEUED'"))
    attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer)
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(Text)
    initiated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    correlation_id: Mapped[str | None] = mapped_column(Text)
    last_error_code: Mapped[str | None] = mapped_column(Text)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScheduleRow(Base):
    __tablename__ = "schedule"
    __table_args__ = (
        CheckConstraint(f"job_class IN {_JOB_CLASSES}", name="job_class"),
        CheckConstraint("may_write = (job_class <> 'ORCHESTRATION')", name="may_write"),
        CheckConstraint(
            "interval > interval '0' AND date_part('month', interval) = 0 AND date_part('year', interval) = 0",
            name="interval_fixed",
        ),
        CheckConstraint("kind <> ''", name="kind_not_empty"),
        {"schema": "jobs"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    job_class: Mapped[str] = mapped_column(Text)
    interval: Mapped[timedelta] = mapped_column(Interval)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    may_write: Mapped[bool] = mapped_column(Boolean)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_skip_reason: Mapped[str | None] = mapped_column(Text)
