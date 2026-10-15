"""Xác thực lại (step-up) và đổi mật khẩu (T-104; SRS-IAM-08, SRS-IAM-11; ADR-006; API-AUTH-05, API-AUTH-09).

- **Xác thực lại (API-AUTH-05):** session đủ MFA + mật khẩu hiện tại; tài khoản đã bật MFA thì thêm mã TOTP hoặc mã khôi
  phục (mã đã dùng không dùng lại — `MfaService.use_code`). Đúng → `session.reauth_at = now()`; thao tác `STEP-UP` hợp
  lệ trong `AIEOS_REAUTH_MINUTES` (`Authenticator.require_step_up`). Giới hạn thử theo IP + tài khoản (D-57); sai →
  `401 INVALID_CREDENTIALS`, không phân biệt sai mật khẩu hay sai mã. Sai không tính vào khóa tạm của đăng nhập
  (SRS-IAM-07 chỉ nói đăng nhập — Implementation_Plan §28).
- **Đổi mật khẩu (API-AUTH-09, `STEP-UP`):** độ dài `AIEOS_PASSWORD_MIN_LENGTH`…`MAX_PASSWORD_LENGTH`; Argon2id; thu hồi
  mọi session **khác** của tài khoản (SRS-IAM-11; session hiện tại giữ nguyên theo API_Specification); audit không chứa
  mật khẩu (phần đổi mật khẩu của TC-AUD-02, D-55).
"""

from dataclasses import dataclass

from sqlalchemy import text

from aieos.audit.api import Outcome
from aieos.identity.auth import Authenticator, Principal, audit_security, hash_password, verify_password
from aieos.identity.mfa import MfaService
from aieos.platform.api import ApiError, transaction

MAX_PASSWORD_LENGTH = 1024


def password_problem(password: str, min_length: int) -> str | None:
    """Lý do mật khẩu không hợp lệ (không chứa mật khẩu) hoặc None."""
    if len(password) < min_length:
        return f"Mật khẩu phải có ít nhất {min_length} ký tự"
    if len(password) > MAX_PASSWORD_LENGTH:
        return f"Mật khẩu dài quá {MAX_PASSWORD_LENGTH} ký tự"
    return None


@dataclass(frozen=True)
class StepUpService:
    auth: Authenticator
    mfa: MfaService

    def reauth(self, principal: Principal, password: str, code: str | None, *, ip: str | None) -> None:
        try:
            self.auth.limiter.hit(f"reauth-ip:{ip or '?'}", f"reauth-acct:{principal.user_id}")
        except ApiError:
            with transaction(self.auth.factory) as session:
                audit_security(session, "auth.reauth", Outcome.BLOCKED, principal.user_id, "RATE_LIMITED")
            raise
        with transaction(self.auth.factory) as session:
            user = self.mfa.user_for_update(session, principal.user_id)
            stored = session.execute(
                text("SELECT password_hash FROM identity.user_account WHERE id = :i"), {"i": principal.user_id}
            ).scalar_one()
            password_ok = verify_password(stored, password)  # luôn kiểm Argon2 trước khi xét mã MFA
            method = None
            if password_ok and user.mfa_enabled:
                method = self.mfa.use_code(session, user, code) if code else None
            if not password_ok or (user.mfa_enabled and method is None):
                reason = "INVALID_PASSWORD" if not password_ok else "INVALID_CODE"
                audit_security(session, "auth.reauth", Outcome.DENIED, principal.user_id, reason)
            else:
                session.execute(
                    text("UPDATE identity.session SET reauth_at = now() WHERE id = :i"), {"i": principal.session_id}
                )
                audit_security(session, "auth.reauth", Outcome.SUCCESS, principal.user_id, method)
                return
        raise ApiError("INVALID_CREDENTIALS")

    def change_password(self, principal: Principal, new_password: str) -> int:
        """Đặt mật khẩu mới; trả số session khác bị thu hồi."""
        problem = password_problem(new_password, self.auth.settings.password_min_length)
        if problem:
            raise ApiError("VALIDATION_ERROR", errors=[{"field": "new_password", "message": problem}])
        new_hash = hash_password(new_password)
        with transaction(self.auth.factory) as session:
            session.execute(
                text(
                    "UPDATE identity.user_account SET password_hash = :p, version = version + 1, updated_at = now() "
                    "WHERE id = :i"
                ),
                {"p": new_hash, "i": principal.user_id},
            )
            revoked = self.auth.revoke_sessions(session, principal.user_id, keep=principal.session_id)
            audit_security(session, "auth.password.change", Outcome.SUCCESS, principal.user_id)
        return revoked
