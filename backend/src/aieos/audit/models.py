"""Model `audit.event` (Database_Design §9, ADR-010). Chỉ dùng nội bộ module `audit`; module khác ghi qua `audit.api`.

Bảng do migration 0002 tạo; model phải khớp schema (TC-MIG-01, so khớp qua metadata do `app` gom).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Identity, Index, Text, Uuid, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base


class AuditEventRow(Base):
    __tablename__ = "event"
    __table_args__ = (
        CheckConstraint("category IN ('SECURITY', 'ADMIN', 'BUSINESS', 'AI')", name="category"),
        CheckConstraint("actor_type IN ('USER', 'AI', 'SYSTEM', 'BOOTSTRAP')", name="actor_type"),
        CheckConstraint("outcome IN ('SUCCESS', 'DENIED', 'FAILED', 'BLOCKED')", name="outcome"),
        CheckConstraint("autonomy_level IS NULL OR autonomy_level IN ('L0', 'L1', 'L2', 'L3')", name="autonomy_level"),
        CheckConstraint("actor_type = 'AI' OR (ai_agent IS NULL AND autonomy_level IS NULL)", name="ai_fields"),
        CheckConstraint("action <> ''", name="action_not_empty"),
        Index("ix_event_resource", "resource_type", "resource_id", "occurred_at"),
        Index("ix_event_actor", "actor_user_id", "occurred_at"),
        {"schema": "audit"},
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    category: Mapped[str] = mapped_column(Text)
    actor_type: Mapped[str] = mapped_column(Text)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    on_behalf_of_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    ai_agent: Mapped[str | None] = mapped_column(Text)
    autonomy_level: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(Text)
    resource_id: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    correlation_id: Mapped[str | None] = mapped_column(Text)
    request_ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
