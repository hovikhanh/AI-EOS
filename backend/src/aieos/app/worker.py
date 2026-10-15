"""Tiến trình worker (composition root, D-42): `python -m aieos.app worker`.

Lắp ráp: cấu hình (T-004) → logging JSON (T-006) → engine `aieos_app` (T-005) → registry loại job của các module →
`jobs.api.Worker`. Chưa module nào đăng ký loại job (T-009 chỉ dựng queue); module sau thêm vào `build_registry`.
Chưa có `access.policy` (T-108) nên authorizer mặc định từ chối mọi job cần quyền người khởi tạo (mặc định deny).
"""

import signal
import threading
from types import FrameType

import aieos.app.metadata  # noqa: F401 — nạp model mọi module (khóa ngoại liên module)
from aieos.jobs.api import JobRegistry, Worker
from aieos.platform.api import (
    Process,
    configure_logging,
    create_app_engine,
    load_settings_or_exit,
    make_session_factory,
)


def build_registry() -> JobRegistry:
    """Registry loại job của toàn ứng dụng; mỗi module có job gọi hàm đăng ký của nó ở đây."""
    return JobRegistry()


def run(once: bool = False) -> int:
    settings = load_settings_or_exit(Process.WORKER)
    configure_logging()
    engine = create_app_engine(settings)
    try:
        worker = Worker(make_session_factory(engine), build_registry())
        if once:
            worker.reap()
            worker.tick_scheduler()
            worker.run_once()
            return 0
        stop = threading.Event()

        def request_stop(signum: int, frame: FrameType | None) -> None:
            stop.set()

        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)
        worker.run_forever(stop)
        return 0
    finally:
        engine.dispose()
