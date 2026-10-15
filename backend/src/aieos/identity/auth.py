"""Đăng nhập, session, đăng xuất (T-102; SRS-IAM-04, SRS-IAM-06, SRS-IAM-07, SRS-GEN-01; ADR-006; API-AUTH-01, 06, 07).

- **Mật khẩu:** Argon2id (`argon2-cffi`, tham số mặc định theo khuyến nghị hiện hành của thư viện; hash cũ được băm lại
  khi tham số đổi). Email không tồn tại vẫn chạy một lần kiểm tra trên hash giả để thời gian xử lý tương đương
  (TC-IAM-03); thông báo lỗi luôn `INVALID_CREDENTIALS`.
- **Giới hạn thử (D-57):** theo IP và theo tài khoản (băm email) trước mọi kiểm tra → `429 RATE_LIMITED`.
  **Khóa tạm:** sai liên tiếp đủ `AIEOS_AUTH_LOCKOUT_THRESHOLD` lần → `locked_until`; `423 ACCOUNT_LOCKED` chỉ trả sau
  khi mật khẩu đúng (API-AUTH-01).
- **Session:** token 256 bit chỉ trả trong cookie `__Host-aieos_session` (`Secure`, `HttpOnly`, `SameSite=Lax`,
  `Path=/`); CSDL lưu SHA-256 (INV-16). Mỗi lần đăng nhập tạo session **mới** và thu hồi session cũ gửi kèm request
  (chống session fixation, TC-IAM-02). Hết hạn nhàn rỗi (trượt) và tuyệt đối theo cấu hình.
- **MFA (SRS-IAM-04, SRS-IAM-05):** tài khoản có role `ADMIN` hoặc đã bật MFA → session chờ MFA (`mfa_verified=false`),
  chỉ gọi được API MFA (T-103) và đăng xuất; endpoint khác trả `401 MFA_REQUIRED`.
- **Audit (ADR-010, SRS-AUD-02):** `SECURITY` cho đăng nhập thành công/bị từ chối/bị chặn và đăng xuất; không ghi
  email, mật khẩu, token.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from aieos.access.api import effective_permissions, roles_of
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.identity.tokens import hash_email, hash_token, new_token
from aieos.platform.api import SESSION_COOKIE, ApiError, RateLimiter, transaction

_HASHER = PasswordHasher()
_DUMMY_HASH = _HASHER.hash(secrets.token_urlsafe(32))  # cho email không tồn tại (TC-IAM-03)


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    try:
        return _HASHER.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@dataclass(frozen=True)
class AuthSettings:
    idle: timedelta
    absolute: timedelta
    rate_limit_attempts: int
    rate_limit_window: timedelta
    lockout_threshold: int
    lockout_duration: timedelta


@dataclass(frozen=True)
class Principal:
    """Người dùng của request hiện hành (session hợp lệ)."""

    user_id: uuid.UUID
    session_id: uuid.UUID
    mfa_verified: bool
    mfa_required: bool


@dataclass(frozen=True)
class LoginResult:
    token: str
    mfa_required: bool


def _audit(
    session: Session, action: str, outcome: Outcome, user_id: uuid.UUID | None, reason: str | None = None
) -> None:
    event = AuditEvent(
        category=Category.SECURITY,
        actor_type=ActorType.USER,
        actor_user_id=user_id,
        action=action,
        outcome=outcome,
        resource_type="identity.user_account" if user_id else None,
        resource_id=str(user_id) if user_id else None,
        reason=reason,
    )
    record(session, event)


def _mfa_required(session: Session, user_id: uuid.UUID, mfa_enabled: bool) -> bool:
    return mfa_enabled or "ADMIN" in roles_of(session, user_id)


class Authenticator:
    """Dịch vụ xác thực của tiến trình API; giữ bộ đếm giới hạn thử trong bộ nhớ (D-57, Implementation_Plan §20)."""

    def __init__(self, factory: sessionmaker[Session], settings: AuthSettings) -> None:
        self.factory = factory
        self.settings = settings
        self.limiter = RateLimiter(settings.rate_limit_attempts, settings.rate_limit_window)

    # ---------- Đăng nhập ----------
    def login(
        self, email: str, password: str, *, ip: str | None, old_token: str | None, user_agent: str | None
    ) -> LoginResult:
        email_hash = hash_email(email)
        try:
            self.limiter.hit(f"ip:{ip or '?'}", f"acct:{email_hash.hex()}")
        except ApiError:
            self._record_failure(email_hash, ip, "RATE_LIMITED", Outcome.BLOCKED)
            raise
        with transaction(self.factory) as session:
            row = session.execute(
                text(
                    "SELECT id, password_hash, status, mfa_enabled, coalesce(locked_until > now(), false) AS locked "
                    "FROM identity.user_account WHERE email = :e FOR UPDATE"
                ),
                {"e": email.strip()},
            ).one_or_none()
            # Luôn đúng một lần kiểm tra Argon2 (hash giả khi email không tồn tại): thời gian tương đương (TC-IAM-03).
            password_ok = verify_password(row.password_hash if row is not None else None, password)
            if row is None or not password_ok:
                self._count_failure(session, row)
                self._attempt(session, email_hash, ip, success=False)
                _audit(session, "auth.login", Outcome.DENIED, row.id if row else None, "INVALID_CREDENTIALS")
                error = ApiError("INVALID_CREDENTIALS")
            elif row.status == "LOCKED" or row.locked:  # chỉ báo khóa khi mật khẩu đúng (API-AUTH-01)
                self._attempt(session, email_hash, ip, success=False)
                _audit(session, "auth.login", Outcome.DENIED, row.id, "ACCOUNT_LOCKED")
                error = ApiError("ACCOUNT_LOCKED")
            elif row.status != "ACTIVE":
                _audit(session, "auth.login", Outcome.DENIED, row.id, "INVALID_CREDENTIALS")
                error = ApiError("INVALID_CREDENTIALS")
            else:
                return self._start_session(session, row, password, email_hash, ip, old_token, user_agent)
        raise error

    @staticmethod
    def _attempt(session: Session, email_hash: bytes, ip: str | None, *, success: bool) -> None:
        session.execute(
            text("INSERT INTO identity.login_attempt (email_hash, ip, success) VALUES (:h, :ip, :ok)"),
            {"h": email_hash, "ip": ip, "ok": success},
        )

    def _count_failure(self, session: Session, row: Any) -> None:
        """Sai mật khẩu: tăng bộ đếm; đủ ngưỡng → khóa tạm `AIEOS_AUTH_LOCKOUT_MINUTES` và đặt lại bộ đếm."""
        if row is None:
            return
        session.execute(
            text(
                "UPDATE identity.user_account SET "
                "locked_until = CASE WHEN failed_login_count + 1 >= :threshold "
                "THEN now() + make_interval(secs => :lock) ELSE locked_until END, "
                "failed_login_count = CASE WHEN failed_login_count + 1 >= :threshold THEN 0 "
                "ELSE failed_login_count + 1 END "
                "WHERE id = :id"
            ),
            {
                "id": row.id,
                "threshold": self.settings.lockout_threshold,
                "lock": self.settings.lockout_duration.total_seconds(),
            },
        )

    def _record_failure(self, email_hash: bytes, ip: str | None, reason: str, outcome: Outcome) -> None:
        with transaction(self.factory) as session:
            self._attempt(session, email_hash, ip, success=False)
            _audit(session, "auth.login", outcome, None, reason)

    def _start_session(
        self,
        session: Session,
        row: Any,
        password: str,
        email_hash: bytes,
        ip: str | None,
        old_token: str | None,
        user_agent: str | None,
    ) -> LoginResult:
        if old_token:  # chống session fixation: session cũ đi kèm request bị thu hồi
            session.execute(
                text("UPDATE identity.session SET revoked_at = now() WHERE token_hash = :h AND revoked_at IS NULL"),
                {"h": hash_token(old_token)},
            )
        new_hash = hash_password(password) if _HASHER.check_needs_rehash(row.password_hash) else row.password_hash
        session.execute(
            text(
                "UPDATE identity.user_account SET failed_login_count = 0, locked_until = NULL, "
                "password_hash = :ph, updated_at = now() WHERE id = :id"
            ),
            {"id": row.id, "ph": new_hash},
        )
        mfa_required = _mfa_required(session, row.id, row.mfa_enabled)
        token = new_token()
        self._insert_session(session, row.id, token, mfa_verified=not mfa_required, ip=ip, user_agent=user_agent)
        self._attempt(session, email_hash, ip, success=True)
        _audit(session, "auth.login", Outcome.SUCCESS, row.id)
        return LoginResult(token=token, mfa_required=mfa_required)

    def _insert_session(
        self,
        session: Session,
        user_id: uuid.UUID,
        token: str,
        *,
        mfa_verified: bool,
        ip: str | None,
        user_agent: str | None,
    ) -> uuid.UUID:
        session_id = uuid.uuid4()
        session.execute(
            text(
                "INSERT INTO identity.session (id, token_hash, user_id, mfa_verified, idle_expires_at, "
                "absolute_expires_at, ip, user_agent) VALUES (:i, :h, :u, :m, "
                "now() + make_interval(secs => :idle), now() + make_interval(secs => :abs), :ip, :ua)"
            ),
            {
                "i": session_id,
                "h": hash_token(token),
                "u": user_id,
                "m": mfa_verified,
                "idle": self.settings.idle.total_seconds(),
                "abs": self.settings.absolute.total_seconds(),
                "ip": ip,
                "ua": (user_agent or "")[:500] or None,
            },
        )
        return session_id

    # ---------- Session của request ----------
    def authenticate(self, token: str | None, *, allow_pending_mfa: bool = False) -> Principal:
        """Session hợp lệ của request; thiếu/hết hạn/thu hồi → `401 UNAUTHENTICATED`; chờ MFA → `401 MFA_REQUIRED`."""
        if not token:
            raise ApiError("UNAUTHENTICATED")
        with transaction(self.factory) as session:
            row = session.execute(
                text(
                    "UPDATE identity.session s SET last_seen_at = now(), "
                    "idle_expires_at = LEAST(now() + make_interval(secs => :idle), s.absolute_expires_at) "
                    "FROM identity.user_account u "
                    "WHERE s.token_hash = :h AND s.user_id = u.id AND s.revoked_at IS NULL "
                    "AND s.idle_expires_at > now() AND s.absolute_expires_at > now() AND u.status = 'ACTIVE' "
                    "RETURNING s.id, s.user_id, s.mfa_verified, u.mfa_enabled"
                ),
                {"h": hash_token(token), "idle": self.settings.idle.total_seconds()},
            ).one_or_none()
            if row is None:
                raise ApiError("UNAUTHENTICATED")
            mfa_required = _mfa_required(session, row.user_id, row.mfa_enabled)
        principal = Principal(row.user_id, row.id, row.mfa_verified, mfa_required)
        if mfa_required and not principal.mfa_verified and not allow_pending_mfa:
            raise ApiError("MFA_REQUIRED")
        return principal

    def require_session(self, request: Request) -> Principal:
        """Dependency FastAPI: session đầy đủ (đã xác minh MFA nếu bắt buộc) — SRS-GEN-01."""
        return self.authenticate(request.cookies.get(SESSION_COOKIE))

    def require_session_allow_pending(self, request: Request) -> Principal:
        """Dependency cho API MFA và đăng xuất: chấp nhận session chờ MFA (SRS-IAM-04)."""
        return self.authenticate(request.cookies.get(SESSION_COOKIE), allow_pending_mfa=True)

    def logout(self, principal: Principal) -> None:
        with transaction(self.factory) as session:
            session.execute(
                text("UPDATE identity.session SET revoked_at = now() WHERE id = :i AND revoked_at IS NULL"),
                {"i": principal.session_id},
            )
            _audit(session, "auth.logout", Outcome.SUCCESS, principal.user_id)

    def me(self, principal: Principal) -> dict[str, Any]:
        with transaction(self.factory) as session:
            user = session.execute(
                text(
                    "SELECT id, email, display_name, mfa_enabled, must_enroll_mfa "
                    "FROM identity.user_account WHERE id = :i"
                ),
                {"i": principal.user_id},
            ).one()
            return {
                "id": str(user.id),
                "email": str(user.email),
                "display_name": user.display_name,
                "roles": sorted(roles_of(session, principal.user_id)),
                "permissions": sorted(effective_permissions(session, principal.user_id)),
                "mfa_enabled": user.mfa_enabled,
                "must_enroll_mfa": user.must_enroll_mfa,
            }


__all__ = [
    "AuthSettings",
    "Authenticator",
    "LoginResult",
    "Principal",
    "hash_password",
    "verify_password",
]
