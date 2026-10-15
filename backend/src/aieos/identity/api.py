"""Interface công khai của `identity` (ADR-006, Architecture §3 quy tắc 1).

T-101: bảng và hàm băm token (INV-16). T-102: đăng nhập, session, đăng xuất, `/auth/me`, dependency session cho
router của module khác (SRS-GEN-01). T-106: `bootstrap_admin`, `recover_admin` cho CLI. T-103: MFA TOTP (`MfaService`,
`build_mfa_router`). Reauth, đổi mật khẩu: T-104; lời mời: T-105.
"""

import aieos.identity.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.identity.admin import AdminCommandError, bootstrap_admin, check_password, recover_admin
from aieos.identity.auth import Authenticator, AuthSettings, LoginResult, Principal, hash_password, verify_password
from aieos.identity.mfa import MfaKeyError, MfaService, parse_totp_key
from aieos.identity.router import LOGIN_PATH, build_auth_router, build_mfa_router
from aieos.identity.tokens import TOKEN_BYTES, hash_email, hash_token, new_token, token_matches

__all__ = [
    "LOGIN_PATH",
    "TOKEN_BYTES",
    "AdminCommandError",
    "AuthSettings",
    "Authenticator",
    "LoginResult",
    "MfaKeyError",
    "MfaService",
    "Principal",
    "bootstrap_admin",
    "build_auth_router",
    "build_mfa_router",
    "check_password",
    "hash_email",
    "hash_password",
    "hash_token",
    "new_token",
    "parse_totp_key",
    "recover_admin",
    "token_matches",
    "verify_password",
]
