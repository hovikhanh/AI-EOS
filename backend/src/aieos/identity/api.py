"""Interface công khai của `identity` (ADR-006, Architecture §3 quy tắc 1).

T-101: bảng và hàm băm token (INV-16). T-102: đăng nhập, session, đăng xuất, `/auth/me`, dependency session cho
router của module khác (SRS-GEN-01). T-106: `bootstrap_admin`, `recover_admin` cho CLI. T-103: MFA TOTP (`MfaService`,
`build_mfa_router`). T-104: xác thực lại, đổi mật khẩu (`StepUpService`, `build_stepup_router`,
`Authenticator.require_step_up`, `Authenticator.revoke_sessions`). T-109: quản trị tài khoản (`UserAdmin`,
`build_user_admin_router`). T-105: tạo tài khoản + lời mời (`InvitationService`, `build_invitation_router`).
"""

import aieos.identity.models  # noqa: F401 — đăng ký model vào metadata (TC-MIG-01)
from aieos.identity.admin import AdminCommandError, bootstrap_admin, check_password, recover_admin
from aieos.identity.auth import Authenticator, AuthSettings, LoginResult, Principal, hash_password, verify_password
from aieos.identity.invitations import InvitationService
from aieos.identity.mfa import MfaKeyError, MfaService, parse_totp_key
from aieos.identity.router import (
    ACCEPT_INVITATION_PATH,
    LOGIN_PATH,
    build_auth_router,
    build_invitation_router,
    build_mfa_router,
    build_stepup_router,
    build_user_admin_router,
)
from aieos.identity.stepup import StepUpService
from aieos.identity.tokens import TOKEN_BYTES, hash_email, hash_token, new_token, token_matches
from aieos.identity.users import UserAdmin

__all__ = [
    "ACCEPT_INVITATION_PATH",
    "InvitationService",
    "LOGIN_PATH",
    "TOKEN_BYTES",
    "AdminCommandError",
    "AuthSettings",
    "Authenticator",
    "LoginResult",
    "MfaKeyError",
    "MfaService",
    "StepUpService",
    "UserAdmin",
    "Principal",
    "bootstrap_admin",
    "build_auth_router",
    "build_invitation_router",
    "build_mfa_router",
    "build_stepup_router",
    "build_user_admin_router",
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
