"""Quản trị tài khoản (T-109; SRS-ACC-05…07, SRS-IAM-11; API-ADM-01, API-ADM-04, API-ADM-05).

- **Danh sách (API-ADM-01):** tài khoản, role, trạng thái; không trả hash mật khẩu, secret MFA.
- **Trạng thái (API-ADM-04):** `ACTIVE` ↔ `LOCKED` / `DISABLED`; tài khoản `INVITED` không đổi được ở đây (kích hoạt qua
  lời mời — T-105). Không tự đổi trạng thái của chính mình (tránh tự khóa — lựa chọn của agent, Implementation_Plan
  §29). Rời `ACTIVE` → thu hồi mọi session (SRS-IAM-11); ADMIN hoạt động cuối → `409 LAST_ADMIN` (trigger INV-11).
  Mở khóa xóa khóa tạm (`locked_until`, bộ đếm).
- **Role (API-ADM-05):** `access.api.set_roles` (INV-09/10/11 ở CSDL); thu hồi mọi session của tài khoản đích.
- Cả hai thao tác ghi dùng `If-Match` = `user_account.version` (tăng 1 mỗi lần đổi). Lỗi nghiệp vụ trên đối tượng
  nhạy cảm được audit `FAILED` trong transaction riêng (SRS-AUD-01, TC-AUD-01); thành công audit trong cùng transaction.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker

from aieos.access.api import roles_of, set_roles
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record, record_separately
from aieos.identity.admin import ADMIN_LOCK_KEY
from aieos.identity.auth import Authenticator
from aieos.platform.api import ApiError, check_version, transaction

STATUSES = ("ACTIVE", "LOCKED", "DISABLED")


@dataclass(frozen=True)
class UserView:
    id: uuid.UUID
    email: str
    display_name: str
    status: str
    roles: list[str]
    mfa_enabled: bool
    created_at: datetime
    version: int


_COLUMNS = "id, email, display_name, status, mfa_enabled, created_at, version"


def _view(session: Session, row: Any) -> UserView:
    return UserView(
        row.id,
        str(row.email),
        row.display_name,
        row.status,
        sorted(roles_of(session, row.id)),
        row.mfa_enabled,
        row.created_at,
        row.version,
    )


def _lock_admin_membership(session: Session) -> None:
    """Advisory lock `admin-membership` (A4) **trước** khi khóa dòng tài khoản: trigger INV-11 cũng lấy khóa này rồi đọc
    các tài khoản ADMIN khác; khóa dòng trước sẽ ngược thứ tự và deadlock khi hai ADMIN gỡ nhau (TC-ACC-06)."""
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ADMIN_LOCK_KEY})


def _audit(session: Session, actor: uuid.UUID, action: str, target: uuid.UUID, changes: dict[str, str]) -> None:
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
class UserAdmin:
    auth: Authenticator

    @property
    def factory(self) -> sessionmaker[Session]:
        return self.auth.factory

    def list(self, *, limit: int, after: tuple[datetime, uuid.UUID] | None) -> list[UserView]:
        with transaction(self.factory) as session:
            rows = session.execute(
                text(
                    f"SELECT {_COLUMNS} FROM identity.user_account "
                    "WHERE CAST(:c AS timestamptz) IS NULL OR (created_at, id) < (CAST(:c AS timestamptz), :i) "
                    "ORDER BY created_at DESC, id DESC LIMIT :n"
                ),
                {"c": after[0] if after else None, "i": after[1] if after else uuid.UUID(int=0), "n": limit},
            ).all()
            return [_view(session, row) for row in rows]

    def get(self, user_id: uuid.UUID) -> UserView:
        with transaction(self.factory) as session:
            return self._locked(session, user_id, lock=False)

    @staticmethod
    def _locked(session: Session, user_id: uuid.UUID, *, lock: bool = True) -> UserView:
        row = session.execute(
            text(f"SELECT {_COLUMNS} FROM identity.user_account WHERE id = :i" + (" FOR UPDATE" if lock else "")),
            {"i": user_id},
        ).one_or_none()
        if row is None:
            raise ApiError("NOT_FOUND")
        return _view(session, row)

    def _failed(self, actor: uuid.UUID, action: str, target: uuid.UUID, error: ApiError) -> None:
        record_separately(
            self.factory,
            AuditEvent(
                category=Category.ADMIN,
                actor_type=ActorType.USER,
                actor_user_id=actor,
                action=action,
                outcome=Outcome.FAILED,
                resource_type="identity.user_account",
                resource_id=str(target),
                reason=error.code,
            ),
        )

    def set_status(
        self, *, actor: uuid.UUID, user_id: uuid.UUID, status: str, reason: str | None, expected_version: int
    ) -> UserView:
        try:
            with transaction(self.factory) as session:
                _lock_admin_membership(session)
                user = self._locked(session, user_id)
                check_version(user.version, expected_version)
                if actor == user_id:
                    raise ApiError("FORBIDDEN", "Không tự đổi trạng thái tài khoản của mình")
                if user.status == "INVITED":
                    raise ApiError("INVALID_STATE", "Tài khoản chưa nhận lời mời")
                if status not in STATUSES:
                    raise ApiError(
                        "VALIDATION_ERROR", errors=[{"field": "status", "message": "Trạng thái không hợp lệ"}]
                    )
                if status == user.status:
                    return user
                try:
                    with session.begin_nested():
                        session.execute(
                            text(
                                "UPDATE identity.user_account SET status = :s, version = version + 1, "
                                "updated_at = now(), locked_until = CASE WHEN :s = 'ACTIVE' THEN NULL "
                                "ELSE locked_until END, failed_login_count = CASE WHEN :s = 'ACTIVE' THEN 0 "
                                "ELSE failed_login_count END WHERE id = :i"
                            ),
                            {"s": status, "i": user_id},
                        )
                except DBAPIError as error:  # trigger INV-11 (SQLSTATE AE002)
                    if getattr(getattr(error, "orig", None), "sqlstate", None) == "AE002":
                        raise ApiError("LAST_ADMIN") from None
                    raise
                if status != "ACTIVE":
                    self.auth.revoke_sessions(session, user_id)
                _audit(
                    session,
                    actor,
                    "identity.user.status",
                    user_id,
                    {"from": user.status, "to": status, "reason": reason or ""},
                )
                return self._locked(session, user_id)
        except ApiError as error:
            if error.code not in ("NOT_FOUND",):
                self._failed(actor, "identity.user.status", user_id, error)
            raise

    def set_roles(
        self, *, actor: uuid.UUID, user_id: uuid.UUID, roles: set[str], reason: str, expected_version: int
    ) -> UserView:
        try:
            with transaction(self.factory) as session:
                _lock_admin_membership(session)
                user = self._locked(session, user_id)
                check_version(user.version, expected_version)
                added, removed = set_roles(session, user_id=user_id, roles=roles, changed_by=actor, reason=reason)
                if added or removed:
                    session.execute(
                        text(
                            "UPDATE identity.user_account SET version = version + 1, updated_at = now() WHERE id = :i"
                        ),
                        {"i": user_id},
                    )
                    self.auth.revoke_sessions(session, user_id)  # A3, SRS-IAM-11
                return self._locked(session, user_id)
        except ApiError as error:
            if error.code not in ("NOT_FOUND",):
                self._failed(actor, "access.role.set", user_id, error)
            raise
