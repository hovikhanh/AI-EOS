"""Thông báo in-app (T-010; SRS-NTF-01, SRS-NTF-02).

Module khác tạo thông báo bằng `notify()` trong transaction của chính thao tác nghiệp vụ (thông báo chỉ tồn tại khi
thao tác được ghi). Nội dung chỉ gồm loại, tiêu đề, liên kết nội bộ (và `body` ngắn nếu cần) — không số tiền, PII hay
nội dung tài liệu (SRS-NTF-02); module gọi chịu trách nhiệm nội dung, `notify` chặn liên kết ra ngoài hệ thống.

Đọc và đánh dấu đã đọc chỉ trên thông báo của chính người dùng; thông báo của người khác coi như không tồn tại.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.orm import Session

from aieos.notify.models import NotificationRow

_INTERNAL_LINK = re.compile(r"/([^/\\]|$)")


@dataclass(frozen=True)
class Notification:
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    link: str | None
    created_at: datetime
    read_at: datetime | None


def _to_notification(row: NotificationRow) -> Notification:
    return Notification(row.id, row.type, row.title, row.body, row.link, row.created_at, row.read_at)


def notify(
    session: Session,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    link: str | None = None,
    body: str | None = None,
) -> uuid.UUID:
    """Tạo thông báo cho `user_id` trong transaction của nơi gọi; trả `id`."""
    if not type or not title:
        raise ValueError("type và title không được rỗng")
    if link is not None and not _INTERNAL_LINK.match(link):
        raise ValueError("link phải là đường dẫn nội bộ bắt đầu bằng một '/'")
    row = NotificationRow(id=uuid.uuid4(), user_id=user_id, type=type, title=title, body=body, link=link)
    session.add(row)
    session.flush()
    return row.id


def list_for_user(
    session: Session, user_id: uuid.UUID, *, limit: int, after: tuple[datetime, uuid.UUID] | None = None
) -> list[Notification]:
    """Thông báo của `user_id`, mới nhất trước (`created_at`, `id` giảm dần); `after` = khóa mục cuối trang trước."""
    query = select(NotificationRow).where(NotificationRow.user_id == user_id)
    if after is not None:
        query = query.where(tuple_(NotificationRow.created_at, NotificationRow.id) < tuple_(*after))
    query = query.order_by(NotificationRow.created_at.desc(), NotificationRow.id.desc()).limit(limit)
    return [_to_notification(row) for row in session.scalars(query)]


def mark_read(session: Session, *, user_id: uuid.UUID, notification_id: uuid.UUID) -> Notification | None:
    """Đánh dấu đã đọc (lặp lại không đổi `read_at`); không phải của `user_id` hoặc không tồn tại → `None`."""
    row = session.scalars(
        update(NotificationRow)
        .where(NotificationRow.id == notification_id, NotificationRow.user_id == user_id)
        .values(read_at=func.coalesce(NotificationRow.read_at, func.now()))
        .returning(NotificationRow)
    ).one_or_none()
    return None if row is None else _to_notification(row)
