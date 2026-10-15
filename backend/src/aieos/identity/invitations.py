"""Tạo tài khoản và lời mời (T-105; SRS-IAM-01, 02, 03; API-ADM-02, API-ADM-03, API-AUTH-08; FL-02).

- **Tạo (API-ADM-02):** tài khoản `INVITED` (chưa có mật khẩu), role do người tạo chọn (`access.api.set_roles`,
  INV-09/10), lời mời; `IDEMPOTENT` theo `(created_by, idempotency_key)` (migration 0009, INV-08). Token mời 256 bit
  (`new_token`), CSDL chỉ lưu SHA-256 (INV-16); link chỉ trả **một lần** — gọi lại cùng khóa trả tài khoản nhưng không
  có link (token không lưu được; dùng API-ADM-03 để cấp lại).
- **Cấp lại (API-ADM-03):** chỉ tài khoản `INVITED`; thu hồi lời mời còn hiệu lực, tạo lời mời mới.
- **Chấp nhận (API-AUTH-08, công khai):** kiểm mật khẩu trước (`AIEOS_PASSWORD_MIN_LENGTH`, không lộ token có hợp lệ
  không); đánh dấu lời mời đã dùng bằng một câu `UPDATE … RETURNING` (chưa dùng, chưa thu hồi, còn hạn) — hai request
  đồng thời chỉ một thành công (TC-IAM-10); mọi lý do lỗi → `400 INVITATION_INVALID` cùng thông báo (TC-IAM-09).
  Không tự đăng nhập: người dùng đăng nhập sau (Architecture §1.1 sơ đồ "Yêu cầu đăng nhập").
- Thời hạn: `AIEOS_INVITE_TTL_HOURS` (bắt buộc, không mặc định; SRS-IAM-02 ghi 72 giờ là `PROPOSED`). Danh sách mật
  khẩu phổ biến (SRS-IAM-03 `PROPOSED`) chưa làm — chỉ độ dài tối thiểu (D-58).
- Audit: `identity.user.create`, `identity.invitation.issue`, `identity.invitation.accept` (SUCCESS/DENIED); không ghi
  token, mật khẩu, email.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aieos.access.api import set_roles
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record, record_separately
from aieos.identity.auth import Authenticator, audit_security, hash_password
from aieos.identity.stepup import password_problem
from aieos.identity.tokens import hash_token, new_token
from aieos.identity.users import UserAdmin, UserView
from aieos.platform.api import ApiError, run_idempotent, transaction

INVITE_PATH = "/invite#token="  # trang chấp nhận lời mời của frontend (T-111); token trong fragment, không tới máy chủ
MAX_EMAIL_LENGTH = 320


class _Invalid(Exception):
    """Lời mời không dùng được (sai, hết hạn, đã dùng, đã thu hồi) — không phân biệt lý do ra ngoài."""


@dataclass(frozen=True)
class Invitation:
    link: str
    expires_at: datetime


@dataclass(frozen=True)
class Created:
    user: UserView
    invitation: Invitation | None  # None khi phát lại theo khóa idempotency


def _admin_audit(session: Session, actor: uuid.UUID, action: str, target: uuid.UUID, changes: dict[str, str]) -> None:
    record(
        session,
        AuditEvent(
            category=Category.ADMIN,
            actor_type=ActorType.USER,
            actor_user_id=actor,
            action=action,
            outcome=Outcome.SUCCESS,
            resource_type="identity.user_account",
            resource_id=str(target),
            changes=changes,
        ),
    )


@dataclass(frozen=True)
class InvitationService:
    auth: Authenticator
    users: UserAdmin
    ttl: timedelta

    def _issue(self, session: Session, user_id: uuid.UUID, actor: uuid.UUID) -> Invitation:
        session.execute(
            text(
                "UPDATE identity.invitation SET revoked_at = now() "
                "WHERE user_id = :u AND used_at IS NULL AND revoked_at IS NULL"
            ),
            {"u": user_id},
        )
        token = new_token()
        expires_at = session.execute(
            text(
                "INSERT INTO identity.invitation (id, user_id, token_hash, expires_at, created_by) "
                "VALUES (gen_random_uuid(), :u, :h, now() + make_interval(secs => :ttl), :a) RETURNING expires_at"
            ),
            {"u": user_id, "h": hash_token(token), "ttl": self.ttl.total_seconds(), "a": actor},
        ).scalar_one()
        _admin_audit(session, actor, "identity.invitation.issue", user_id, {"expires_at": expires_at.isoformat()})
        return Invitation(INVITE_PATH + token, expires_at)

    def _failed(self, actor: uuid.UUID, action: str, target: uuid.UUID | None, error: ApiError) -> None:
        record_separately(
            self.auth.factory,
            AuditEvent(
                category=Category.ADMIN,
                actor_type=ActorType.USER,
                actor_user_id=actor,
                action=action,
                outcome=Outcome.FAILED,
                resource_type="identity.user_account" if target else None,
                resource_id=str(target) if target else None,
                reason=error.code,
            ),
        )

    def create_user(
        self,
        *,
        actor: uuid.UUID,
        email: str,
        display_name: str,
        roles: set[str],
        reason: str,
        idempotency_key: str,
        fingerprint: str,
    ) -> Created:
        email, display_name = email.strip(), display_name.strip()
        if "@" not in email or len(email) > MAX_EMAIL_LENGTH:
            raise ApiError("VALIDATION_ERROR", errors=[{"field": "email", "message": "Email không hợp lệ"}])
        if not display_name:
            raise ApiError("VALIDATION_ERROR", errors=[{"field": "display_name", "message": "Không được rỗng"}])
        try:
            with transaction(self.auth.factory) as session:

                def find() -> tuple[str, Created] | None:
                    row = session.execute(
                        text(
                            "SELECT id, request_hash FROM identity.user_account "
                            "WHERE created_by = :a AND idempotency_key = :k"
                        ),
                        {"a": actor, "k": idempotency_key},
                    ).one_or_none()
                    if row is None:
                        return None
                    return row.request_hash, Created(UserAdmin.view(session, row.id), None)

                def create() -> Created:
                    user_id = uuid.uuid4()
                    try:
                        with session.begin_nested():
                            session.execute(
                                text(
                                    "INSERT INTO identity.user_account (id, email, display_name, status, "
                                    "must_enroll_mfa, created_by, idempotency_key, request_hash) "
                                    "VALUES (:i, :e, :n, 'INVITED', :m, :a, :k, :f)"
                                ),
                                {
                                    "i": user_id,
                                    "e": email,
                                    "n": display_name,
                                    "m": "ADMIN" in roles,
                                    "a": actor,
                                    "k": idempotency_key,
                                    "f": fingerprint,
                                },
                            )
                    except IntegrityError as error:
                        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                        if constraint == "uq_user_account_email":
                            raise ApiError(
                                "VALIDATION_ERROR", errors=[{"field": "email", "message": "Email đã có tài khoản"}]
                            ) from None
                        raise
                    _admin_audit(session, actor, "identity.user.create", user_id, {"reason": reason})
                    set_roles(session, user_id=user_id, roles=roles, changed_by=actor, reason=reason)
                    invitation = self._issue(session, user_id, actor)
                    return Created(UserAdmin.view(session, user_id), invitation)

                result, _ = run_idempotent(session, fingerprint=fingerprint, find=find, create=create)
                return result
        except ApiError as error:
            self._failed(actor, "identity.user.create", None, error)
            raise

    def reissue(self, *, actor: uuid.UUID, user_id: uuid.UUID) -> Invitation:
        with transaction(self.auth.factory) as session:
            user = UserAdmin.view(session, user_id, lock=True)
            if user.status != "INVITED":
                raise ApiError("INVALID_STATE", "Tài khoản đã kích hoạt")
            return self._issue(session, user_id, actor)

    def accept(self, token: str, password: str, *, ip: str | None) -> None:
        token_hash = hash_token(token) if token else b""
        try:
            self.auth.limiter.hit(f"invite-ip:{ip or '?'}", f"invite-token:{token_hash.hex()[:32]}")
        except ApiError:
            with transaction(self.auth.factory) as session:
                audit_security(session, "identity.invitation.accept", Outcome.BLOCKED, None, "RATE_LIMITED")
            raise
        problem = password_problem(password, self.auth.settings.password_min_length)
        if problem:
            raise ApiError("VALIDATION_ERROR", errors=[{"field": "password", "message": problem}])
        password_hash = hash_password(password)
        try:
            self._activate(token_hash, password_hash)
        except _Invalid:
            with transaction(self.auth.factory) as session:
                audit_security(session, "identity.invitation.accept", Outcome.DENIED, None, "INVITATION_INVALID")
            raise ApiError("INVITATION_INVALID") from None

    def _activate(self, token_hash: bytes, password_hash: str) -> None:
        """Một transaction: đánh dấu lời mời đã dùng + kích hoạt tài khoản; không hợp lệ → `_Invalid` (rollback)."""
        with transaction(self.auth.factory) as session:
            user_id = session.execute(
                text(
                    "UPDATE identity.invitation SET used_at = now() WHERE token_hash = :h AND used_at IS NULL "
                    "AND revoked_at IS NULL AND expires_at > now() RETURNING user_id"
                ),
                {"h": token_hash},
            ).scalar_one_or_none()
            activated = None
            if user_id is not None:
                activated = session.execute(
                    text(
                        "UPDATE identity.user_account SET status = 'ACTIVE', password_hash = :p, "
                        "version = version + 1, updated_at = now() WHERE id = :i AND status = 'INVITED' RETURNING id"
                    ),
                    {"p": password_hash, "i": user_id},
                ).scalar_one_or_none()
            if activated is None:
                raise _Invalid
            audit_security(session, "identity.invitation.accept", Outcome.SUCCESS, user_id)
