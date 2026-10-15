"""Model `finance.*` (Database_Design §7). Chỉ dùng nội bộ module `finance`.

Bảng, trigger INV-03…07 do migration 0012 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "finance"}
_USER = "identity.user_account.id"


class ReportingPeriodRow(Base):
    __tablename__ = "reporting_period"
    __table_args__ = (
        UniqueConstraint("code"),
        CheckConstraint("code <> ''", name="code"),
        CheckConstraint("start_date <= end_date", name="dates"),
        CheckConstraint("status IN ('OPEN', 'CLOSED')", name="status"),
        CheckConstraint("(status = 'CLOSED') = (closed_at IS NOT NULL AND closed_by IS NOT NULL)", name="closed"),
        CheckConstraint("version >= 1", name="version"),
        ExcludeConstraint(
            (text("daterange(start_date, end_date, '[]')"), "&&"), using="gist", name="ex_reporting_period_no_overlap"
        ),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    code: Mapped[str] = mapped_column(Text)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, server_default=text("'OPEN'"))
    opened_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_reason: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class TransactionRow(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        UniqueConstraint("created_by", "idempotency_key"),
        CheckConstraint("record_type IN ('REVENUE', 'EXPENSE', 'CASH_BALANCE')", name="record_type"),
        CheckConstraint("kind IN ('ORIGINAL', 'REVERSAL', 'ADJUSTMENT')", name="kind"),
        CheckConstraint(
            "status IN ('DRAFT', 'PENDING_APPROVAL', 'ON_HOLD', 'POSTED', 'REVERSED', 'REJECTED', 'CANCELLED')",
            name="status",
        ),
        CheckConstraint("(status = 'ON_HOLD') = (hold_reason IS NOT NULL)", name="hold_reason"),
        CheckConstraint("hold_reason IS NULL OR hold_reason = 'PERIOD_CLOSED'", name="hold_value"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency"),
        CheckConstraint("(kind = 'REVERSAL') = (reverses_id IS NOT NULL)", name="reversal_link"),
        CheckConstraint("(kind = 'ADJUSTMENT') = (adjusts_id IS NOT NULL)", name="adjustment_link"),
        CheckConstraint("kind = 'ORIGINAL' OR (reason IS NOT NULL AND reason <> '')", name="reason"),
        CheckConstraint(
            "approved_by IS NULL OR (approved_by <> created_by AND approved_by IS DISTINCT FROM submitted_by)",
            name="approver_not_creator",
        ),
        CheckConstraint(
            "rejected_by IS NULL OR (rejected_by <> created_by AND rejected_by IS DISTINCT FROM submitted_by)",
            name="rejecter_not_creator",
        ),
        CheckConstraint(
            "status <> 'REJECTED' OR (reject_reason IS NOT NULL AND reject_reason <> '')", name="reject_reason"
        ),
        CheckConstraint("octet_length(request_hash) = 32", name="request_hash"),
        CheckConstraint("idempotency_key <> ''", name="idempotency_key"),
        CheckConstraint("version >= 1", name="version"),
        Index(
            "uq_transaction_one_reversal",
            "reverses_id",
            unique=True,
            postgresql_where=text("kind = 'REVERSAL' AND status IN ('DRAFT', 'PENDING_APPROVAL', 'POSTED')"),
        ),
        Index("ix_transaction_status_period", "status", "period_id"),
        Index("ix_transaction_created_by_status", "created_by", "status"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    record_type: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text, server_default=text("'ORIGINAL'"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'DRAFT'"))
    hold_reason: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(CHAR(3))
    transaction_date: Mapped[date] = mapped_column(Date)
    period_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("finance.reporting_period.id"))
    description: Mapped[str | None] = mapped_column(Text)
    counterparty: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    reverses_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("finance.transaction.id"))
    adjusts_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("finance.transaction.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    no_eligible_approver: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ai_assisted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ai_action_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # FK ai.action: T-302
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # FK capture.source_document: T-202
    idempotency_key: Mapped[str] = mapped_column(Text)
    request_hash: Mapped[bytes] = mapped_column(BYTEA)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TransactionEventRow(Base):
    __tablename__ = "transaction_event"
    __table_args__ = (Index("ix_transaction_event_transaction", "transaction_id", "occurred_at"), _SCHEMA)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("finance.transaction.id"))
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    reason: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    correlation_id: Mapped[str | None] = mapped_column(Text)


class ApprovalDelegationRow(Base):
    """Dự trữ (F6): không seed, logic phê duyệt MVP không đọc."""

    __tablename__ = "approval_delegation"
    __table_args__ = (CheckConstraint("granted_by <> delegate_user_id", name="not_self"), _SCHEMA)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    delegate_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    scope_type: Mapped[str] = mapped_column(Text)
    scope_id: Mapped[str | None] = mapped_column(Text)
    amount_limit: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    granted_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    reason: Mapped[str] = mapped_column(Text)
