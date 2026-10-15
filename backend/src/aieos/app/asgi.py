"""Ứng dụng API (composition root, D-42): `uvicorn --factory aieos.app.asgi:create_app` (server: T-013).

Lắp ráp: cấu hình (T-004) → logging JSON (T-006) → engine `aieos_app` (T-005) → storage (T-011) → CSRF (T-007) →
kiểm tra readiness. Router nghiệp vụ được gắn ở đây khi các module có API.

`CSRF_EXEMPT_PATHS`: endpoint công khai không có session (API_Specification §1.2) — chỉ miễn token, vẫn kiểm `Origin`.
Thêm khi module identity có endpoint (T-102, T-105).
"""

import sys

from fastapi import FastAPI

from aieos.platform.api import (
    CsrfConfig,
    OriginConfigError,
    Process,
    configure_logging,
    create_api,
    create_app_engine,
    database_ready,
    load_settings_or_exit,
    parse_allowed_origins,
)
from aieos.storage.api import StorageError, storage_from_settings

CSRF_EXEMPT_PATHS: frozenset[str] = frozenset()


def create_app() -> FastAPI:
    settings = load_settings_or_exit(Process.API)
    configure_logging()
    try:
        origins = parse_allowed_origins(settings.config("AIEOS_ALLOWED_ORIGINS"))
    except OriginConfigError as error:
        print(f"Cấu hình không hợp lệ cho tiến trình api: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    csrf = CsrfConfig(settings.secret("AIEOS_CSRF_KEY"), origins, CSRF_EXEMPT_PATHS)
    try:
        storage = storage_from_settings(settings)
    except StorageError as error:
        print(f"Cấu hình không hợp lệ cho tiến trình api: {error}", file=sys.stderr)
        raise SystemExit(2) from None
    engine = create_app_engine(settings)
    return create_api({"database": lambda: database_ready(engine), "storage": storage.is_ready}, csrf=csrf)
