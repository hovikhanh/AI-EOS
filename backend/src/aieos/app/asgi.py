"""Ứng dụng API (composition root, D-42): `uvicorn --factory aieos.app.asgi:create_app` (server: T-013).

Lắp ráp: cấu hình (T-004) → logging JSON (T-006) → engine `aieos_app` (T-005) → storage (T-011) → CSRF (T-007) →
xác thực (T-102) → router → kiểm tra readiness.

`PUBLIC_PATHS`: endpoint không cần session (API_Specification §1.2) — mọi endpoint khác dưới `/api/v1` phải dùng
dependency session của `identity` (SRS-GEN-01; test TC-GEN-06 gọi mọi route không có session).
`CSRF_EXEMPT_PATHS`: endpoint công khai thay đổi trạng thái — chỉ miễn token CSRF, vẫn kiểm `Origin` (T-007).
"""

import sys
from datetime import timedelta

from fastapi import FastAPI

from aieos.identity.api import LOGIN_PATH, Authenticator, AuthSettings, build_auth_router
from aieos.platform.api import (
    API_PREFIX,
    CsrfConfig,
    OriginConfigError,
    Process,
    Settings,
    configure_logging,
    create_api,
    create_app_engine,
    database_ready,
    load_settings_or_exit,
    make_session_factory,
    parse_allowed_origins,
)
from aieos.storage.api import StorageError, storage_from_settings

CSRF_EXEMPT_PATHS: frozenset[str] = frozenset({API_PREFIX + LOGIN_PATH})
PUBLIC_PATHS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", API_PREFIX + LOGIN_PATH),
        ("GET", API_PREFIX + "/health/live"),
        ("GET", API_PREFIX + "/health/ready"),
    }
)


class AppConfigError(ValueError):
    """Giá trị cấu hình không hợp lệ; thông điệp chỉ nêu tên biến."""


def _positive_int(settings: Settings, name: str) -> int:
    raw = settings.config(name)
    try:
        value = int(raw)
    except ValueError:
        raise AppConfigError(f"{name} phải là số nguyên dương") from None
    if value < 1:
        raise AppConfigError(f"{name} phải là số nguyên dương")
    return value


def auth_settings(settings: Settings) -> AuthSettings:
    return AuthSettings(
        idle=timedelta(minutes=_positive_int(settings, "AIEOS_SESSION_IDLE_MINUTES")),
        absolute=timedelta(hours=_positive_int(settings, "AIEOS_SESSION_ABSOLUTE_HOURS")),
        rate_limit_attempts=_positive_int(settings, "AIEOS_AUTH_RATE_LIMIT_ATTEMPTS"),
        rate_limit_window=timedelta(seconds=_positive_int(settings, "AIEOS_AUTH_RATE_LIMIT_WINDOW_SECONDS")),
        lockout_threshold=_positive_int(settings, "AIEOS_AUTH_LOCKOUT_THRESHOLD"),
        lockout_duration=timedelta(minutes=_positive_int(settings, "AIEOS_AUTH_LOCKOUT_MINUTES")),
    )


def _exit_config_error(error: Exception) -> SystemExit:
    print(f"Cấu hình không hợp lệ cho tiến trình api: {error}", file=sys.stderr)
    return SystemExit(2)


def create_app() -> FastAPI:
    settings = load_settings_or_exit(Process.API)
    configure_logging()
    try:
        origins = parse_allowed_origins(settings.config("AIEOS_ALLOWED_ORIGINS"))
        auth_config = auth_settings(settings)
        storage = storage_from_settings(settings)
    except (OriginConfigError, AppConfigError, StorageError) as error:
        raise _exit_config_error(error) from None
    csrf_key = settings.secret("AIEOS_CSRF_KEY")
    csrf = CsrfConfig(csrf_key, origins, CSRF_EXEMPT_PATHS)
    engine = create_app_engine(settings)
    authenticator = Authenticator(make_session_factory(engine), auth_config)
    return create_api(
        {"database": lambda: database_ready(engine), "storage": storage.is_ready},
        (build_auth_router(authenticator, csrf_key),),
        csrf=csrf,
    )
