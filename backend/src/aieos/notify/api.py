"""Interface công khai của `notify` (Architecture §3 quy tắc 1).

T-010: bảng `notify.notification`, `notify()` cho module khác (trong transaction của nơi gọi), API-NOT-01/02.
"""

from aieos.notify.router import build_notify_router
from aieos.notify.service import Notification, list_for_user, mark_read, notify

__all__ = ["Notification", "build_notify_router", "list_for_user", "mark_read", "notify"]
