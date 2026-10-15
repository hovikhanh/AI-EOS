"""Interface công khai của `identity` (ADR-006, Architecture §3 quy tắc 1).

T-101: bảng và hàm băm token (INV-16). T-102: đăng nhập, session, đăng xuất, `/auth/me`, dependency session cho
router của module khác (SRS-GEN-01). MFA: T-103; reauth, đổi mật khẩu: T-104; lời mời: T-105; CLI: T-106.
"""

import aieos.identity.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.identity.auth import Authenticator, AuthSettings, LoginResult, Principal, hash_password, verify_password
from aieos.identity.router import LOGIN_PATH, build_auth_router
from aieos.identity.tokens import TOKEN_BYTES, hash_email, hash_token, new_token, token_matches

__all__ = [
    "LOGIN_PATH",
    "TOKEN_BYTES",
    "AuthSettings",
    "Authenticator",
    "LoginResult",
    "Principal",
    "build_auth_router",
    "hash_email",
    "hash_password",
    "hash_token",
    "new_token",
    "token_matches",
    "verify_password",
]
