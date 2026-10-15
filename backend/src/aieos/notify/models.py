"""Model `notify.*` (Database_Design §9). Chỉ dùng nội bộ module `notify`.

Bảng do migration 0006 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

INTERNAL_LINK = r"link IS NULL OR link ~ '^/([^/\\]|$)'"


class NotificationRow(Base):
    __tablename__ = "notification"
    __table_args__ = (
        CheckConstraint("type <> ''", name="type"),
        CheckConstraint("title <> ''", name="title"),
        CheckConstraint(INTERNAL_LINK, name="internal_link"),
        CheckConstraint("read_at IS NULL OR read_at >= created_at", name="read_after_created"),
        Index("ix_notification_user_read", "user_id", "read_at"),
        Index("ix_notification_user_created", "user_id", "created_at", "id"),
        {"schema": "notify"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("identity.user_account.id"))
    type: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
