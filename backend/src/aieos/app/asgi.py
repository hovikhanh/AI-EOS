"""Ứng dụng API (composition root, D-42): `uvicorn --factory aieos.app.asgi:create_app` (server: T-013).

Lắp ráp: cấu hình (T-004) → logging JSON (T-006) → engine `aieos_app` (T-005) → storage (T-011) → kiểm tra readiness.
Router nghiệp vụ được gắn ở đây khi các module có API.
"""

import sys

from fastapi import FastAPI

from aieos.platform.api import (
    Process,
    configure_logging,
    create_api,
    create_app_engine,
    database_ready,
    load_settings_or_exit,
)
from aieos.storage.api import StorageError, storage_from_settings


def create_app() -> FastAPI:
    settings = load_settings_or_exit(Process.API)
    configure_logging()
    try:
        storage = storage_from_settings(settings)
    except StorageError as error:
        print(f"Cấu hình không hợp lệ cho tiến trình api: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    engine = create_app_engine(settings)
    return create_api({"database": lambda: database_ready(engine), "storage": storage.is_ready})
