"""Model `work.*` (Database_Design §6). Chỉ dùng nội bộ module `work`. Bảng do migration 0011 tạo (TC-MIG-01)."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_USER_FK = "identity.user_account.id"


class TaskRow(Base):
    __tablename__ = "task"
    __table_args__ = (
        UniqueConstraint("assigned_by", "idempotency_key"),
        CheckConstraint("title <> ''", name="title"),
        CheckConstraint("status IN ('OPEN', 'DONE')", name="status"),
        CheckConstraint(
            "(status = 'DONE') = (completed_at IS NOT NULL) AND (completed_at IS NULL) = (completed_by IS NULL)",
            name="done_iff_completed",
        ),
        CheckConstraint("created_via IN ('MANUAL', 'MEETING', 'AI')", name="created_via"),
        CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="idempotency_hash"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_task_owner_status_due", "owner_user_id", "status", "due_date"),
        Index("ix_task_assigned_by", "assigned_by"),
        {"schema": "work"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    assigned_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER_FK))
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, server_default=text("'OPEN'"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER_FK))
    objective_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # FK goals.objective: T-501
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)  # FK capture.source_document: T-202
    source_locator: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_via: Mapped[str] = mapped_column(Text, server_default=text("'MANUAL'"))
    ai_action_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai.action.id"))  # 0013 (T-301)
    idempotency_key: Mapped[str | None] = mapped_column(Text)
    request_hash: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
