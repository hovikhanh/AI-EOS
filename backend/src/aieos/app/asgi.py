"""Ứng dụng API (composition root, D-42): `uvicorn --factory aieos.app.asgi:create_app` (server: T-013).

Lắp ráp: cấu hình (T-004) → logging JSON (T-006) → engine `aieos_app` (T-005) → storage (T-011) → CSRF (T-007) →
xác thực (T-102) → router (auth, MFA T-103, step-up T-104, quản trị T-109, lời mời T-105, thông báo T-010) →
kiểm tra readiness.

`PUBLIC_PATHS`: endpoint không cần session (API_Specification §1.2) — mọi endpoint khác dưới `/api/v1` phải dùng
dependency session của `identity` (SRS-GEN-01; test TC-GEN-06 gọi mọi route không có session).
`CSRF_EXEMPT_PATHS`: endpoint công khai thay đổi trạng thái — chỉ miễn token CSRF, vẫn kiểm `Origin` (T-007).
"""

import sys
from datetime import timedelta

from fastapi import FastAPI

from aieos.access.api import PermissionGuard, build_access_admin_router
from aieos.identity.api import (
    ACCEPT_INVITATION_PATH,
    LOGIN_PATH,
    Authenticator,
    AuthSettings,
    InvitationService,
    MfaKeyError,
    MfaService,
    StepUpService,
    UserAdmin,
    build_auth_router,
    build_invitation_router,
    build_mfa_router,
    build_stepup_router,
    build_user_admin_router,
    parse_totp_key,
)
from aieos.notify.api import build_notify_router
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

CSRF_EXEMPT_PATHS: frozenset[str] = frozenset({API_PREFIX + LOGIN_PATH, API_PREFIX + ACCEPT_INVITATION_PATH})
PUBLIC_PATHS: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", API_PREFIX + LOGIN_PATH),
        ("POST", API_PREFIX + ACCEPT_INVITATION_PATH),
        ("GET", API_PREFIX + "/health/live"),
        ("GET", API_PREFIX + "/health/ready"),
    }
)


class AppConfigError(ValueError):
    """Giá trị cấu hình không hợp lệ; thông điệp chỉ nêu tên biến."""


def positive_int(settings: Settings, name: str) -> int:
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
        idle=timedelta(minutes=positive_int(settings, "AIEOS_SESSION_IDLE_MINUTES")),
        absolute=timedelta(hours=positive_int(settings, "AIEOS_SESSION_ABSOLUTE_HOURS")),
        rate_limit_attempts=positive_int(settings, "AIEOS_AUTH_RATE_LIMIT_ATTEMPTS"),
        rate_limit_window=timedelta(seconds=positive_int(settings, "AIEOS_AUTH_RATE_LIMIT_WINDOW_SECONDS")),
        lockout_threshold=positive_int(settings, "AIEOS_AUTH_LOCKOUT_THRESHOLD"),
        lockout_duration=timedelta(minutes=positive_int(settings, "AIEOS_AUTH_LOCKOUT_MINUTES")),
        reauth=timedelta(minutes=positive_int(settings, "AIEOS_REAUTH_MINUTES")),
        password_min_length=positive_int(settings, "AIEOS_PASSWORD_MIN_LENGTH"),
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
        totp_key = parse_totp_key(settings.secret("AIEOS_TOTP_ENCRYPTION_KEY"))
        invite_ttl = timedelta(hours=positive_int(settings, "AIEOS_INVITE_TTL_HOURS"))
    except (OriginConfigError, AppConfigError, StorageError, MfaKeyError) as error:
        raise _exit_config_error(error) from None
    csrf_key = settings.secret("AIEOS_CSRF_KEY")
    csrf = CsrfConfig(csrf_key, origins, CSRF_EXEMPT_PATHS)
    engine = create_app_engine(settings)
    factory = make_session_factory(engine)
    authenticator = Authenticator(factory, auth_config)
    mfa = MfaService(authenticator, totp_key)
    users = UserAdmin(authenticator)
    guard = PermissionGuard(factory, authenticator.require_session, require_step_up=authenticator.require_step_up)
    return create_api(
        {"database": lambda: database_ready(engine), "storage": storage.is_ready},
        (
            build_auth_router(authenticator, csrf_key),
            build_mfa_router(authenticator, mfa),
            build_stepup_router(authenticator, StepUpService(authenticator, mfa)),
            build_user_admin_router(users, guard),
            build_invitation_router(InvitationService(authenticator, users, invite_ttl), guard),
            build_access_admin_router(guard, authenticator.revoke_sessions),
            build_notify_router(factory, authenticator.require_session),
        ),
        csrf=csrf,
    )
