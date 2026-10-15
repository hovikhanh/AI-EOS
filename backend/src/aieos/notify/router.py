"""Endpoint thông báo (T-010): API-NOT-01 `GET /notifications`, API-NOT-02 `POST /notifications/{id}/read`.

Router mỏng (ADR-002). Quyền: đã đăng nhập (session đủ MFA) — chỉ thấy và đánh dấu thông báo của chính mình; thông báo
của người khác → `404 NOT_FOUND` (API_Specification §1.4). Phân trang cursor theo §1.8.
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from aieos.identity.api import Principal
from aieos.notify.service import Notification, list_for_user, mark_read
from aieos.platform.api import (
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    ApiError,
    decode_cursor,
    encode_cursor,
    transaction,
)


class NotificationOut(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    link: str | None
    created_at: datetime
    read_at: datetime | None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    next_cursor: str | None


def _out(item: Notification) -> NotificationOut:
    return NotificationOut(**item.__dict__)


def _after(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if cursor is None:
        return None
    created_at, item_id = decode_cursor(cursor, 2)
    try:
        return datetime.fromisoformat(created_at), uuid.UUID(item_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "cursor", "message": "cursor không hợp lệ"}]) from None


def build_notify_router(factory: sessionmaker[Session], require_session: Callable[..., Principal]) -> APIRouter:
    router = APIRouter(tags=["notifications"])
    signed_in = Annotated[Principal, Depends(require_session)]

    @router.get("/notifications", response_model=NotificationPage)
    def list_notifications(
        principal: signed_in,
        limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
    ) -> NotificationPage:
        after = _after(cursor)
        with transaction(factory) as session:
            items = list_for_user(session, principal.user_id, limit=limit + 1, after=after)
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = encode_cursor((last.created_at.isoformat(), str(last.id)))
        return NotificationPage(items=[_out(item) for item in items], next_cursor=next_cursor)

    @router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
    def read_notification(principal: signed_in, notification_id: uuid.UUID) -> NotificationOut:
        with transaction(factory) as session:
            item = mark_read(session, user_id=principal.user_id, notification_id=notification_id)
        if item is None:
            raise ApiError("NOT_FOUND")
        return _out(item)

    return router
