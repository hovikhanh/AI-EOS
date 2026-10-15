"""Model `goals.*` (Database_Design §6). Chỉ dùng nội bộ module `goals`.

Bảng do migration 0015 tạo; model phải khớp schema (TC-MIG-01). Không có cột % đạt/cảnh báo (SRS-GOAL-09).
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
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
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from aieos.platform.api import Base

_USER = "identity.user_account.id"
_DOC = "capture.source_document.id"


class _Goal:
    """Cột chung của Objective, KR, KPI: trạng thái DRAFT/ACTIVE, người kích hoạt, idempotency, version."""

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[object, ...]:
        return (
            UniqueConstraint("created_by", "idempotency_key"),
            CheckConstraint("status IN ('DRAFT', 'ACTIVE')", name="status"),
            CheckConstraint(
                "(status = 'ACTIVE') = (activated_by IS NOT NULL AND activated_at IS NOT NULL)", name="activated"
            ),
            CheckConstraint("period_label <> ''", name="period_label"),
            CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="idempotency_hash"),
            CheckConstraint("version >= 1", name="version"),
            *cls._extra_args(),
            {"schema": "goals"},
        )

    @classmethod
    def _extra_args(cls) -> tuple[object, ...]:
        return ()

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    period_label: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default=text("'DRAFT'"))
    activated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_DOC))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    request_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class ObjectiveRow(_Goal, Base):
    __tablename__ = "objective"

    @classmethod
    def _extra_args(cls) -> tuple[object, ...]:
        return (
            CheckConstraint("title <> ''", name="title"),
            CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
            Index("ix_objective_unit_status", "org_unit_id", "status"),
        )

    title: Mapped[str] = mapped_column(Text)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("goals.objective.id"))


class KeyResultRow(_Goal, Base):
    __tablename__ = "key_result"

    @classmethod
    def _extra_args(cls) -> tuple[object, ...]:
        return (CheckConstraint("metric <> ''", name="metric"), Index("ix_key_result_objective", "objective_id"))

    objective_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("goals.objective.id"))
    metric: Mapped[str] = mapped_column(Text)
    baseline: Mapped[Decimal | None] = mapped_column(Numeric)
    target: Mapped[Decimal] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(Text)


class KpiRow(_Goal, Base):
    __tablename__ = "kpi"

    @classmethod
    def _extra_args(cls) -> tuple[object, ...]:
        return (CheckConstraint("metric <> ''", name="metric"),)

    metric: Mapped[str] = mapped_column(Text)
    baseline: Mapped[Decimal | None] = mapped_column(Numeric)
    target: Mapped[Decimal] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(Text)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))


class MeasurementRow(Base):
    __tablename__ = "measurement"
    __table_args__ = (
        UniqueConstraint("recorded_by", "idempotency_key"),
        CheckConstraint("target_type IN ('KR', 'KPI')", name="target_type"),
        CheckConstraint("report_period_label <> ''", name="report_period_label"),
        CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="idempotency_hash"),
        Index("ix_measurement_target", "target_type", "target_id", "created_at"),
        {"schema": "goals"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    value: Mapped[Decimal] = mapped_column(Numeric)
    report_period_label: Mapped[str] = mapped_column(Text)
    recorded_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_DOC))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    request_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CheckInRow(Base):
    __tablename__ = "check_in"
    __table_args__ = (
        UniqueConstraint("submitted_by", "idempotency_key"),
        CheckConstraint("confidence BETWEEN 0 AND 10", name="confidence"),
        CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="idempotency_hash"),
        Index("ix_check_in_key_result", "key_result_id", "created_at"),
        {"schema": "goals"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    key_result_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("goals.key_result.id"))
    value: Mapped[Decimal] = mapped_column(Numeric)
    confidence: Mapped[int] = mapped_column(SmallInteger)
    blocker: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    request_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
