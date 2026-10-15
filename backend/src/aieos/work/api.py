"""Interface công khai của `work` (Architecture §3 quy tắc 1).

T-505: `work.task` (migration 0011), API-WORK-01/03/04/05. Biên bản họp, quyết định, action item: T-506.
"""

import aieos.work.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.work.router import build_work_router
from aieos.work.service import Task, create_task, get_task, list_tasks, set_status, update_task

__all__ = ["Task", "build_work_router", "create_task", "get_task", "list_tasks", "set_status", "update_task"]
