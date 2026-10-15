"""Bootstrap và khôi phục ADMIN qua CLI (T-106; SRS-IAM-09, SRS-IAM-10; ADR-006 A2, A6). Không có trên HTTP.

- `bootstrap_admin`: chỉ khi chưa có ADMIN `ACTIVE`; tạo tài khoản `ACTIVE`, buộc đăng ký MFA (`must_enroll_mfa`), role
  `ADMIN` với `granted_by = NULL`; audit `actor_type = BOOTSTRAP`. Giữ advisory lock `admin-membership` (cùng khóa với
  trigger INV-11, migration 0005) để hai lệnh chạy đồng thời không cùng tạo ADMIN.
- `recover_admin`: tài khoản đích phải là ADMIN `ACTIVE`; đặt mật khẩu mới do người vận hành nhập, xóa MFA (secret, mã
  khôi phục còn lại) và buộc đăng ký lại, gỡ khóa tạm, thu hồi mọi session; audit `BOOTSTRAP` kèm lý do; thông báo mọi
  ADMIN `ACTIVE` khác (T-010). Cờ xác nhận do lệnh CLI kiểm tra (`aieos.app`).

Mật khẩu: độ dài tối thiểu `AIEOS_PASSWORD_MIN_LENGTH` (D-58), tối đa `MAX_PASSWORD_LENGTH` (giới hạn API đăng nhập).
Thông điệp lỗi không chứa email hay mật khẩu.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from aieos.access.api import active_admins, grant_role, roles_of
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.identity.auth import hash_password
from aieos.identity.stepup import password_problem
from aieos.notify.api import notify
from aieos.platform.api import transaction

ADMIN_LOCK_KEY = 0x41454F53_00000002  # advisory lock `admin-membership` — trùng migration 0005 (test đối chiếu)
MAX_EMAIL_LENGTH = 320
ADMIN_RECOVERED = "ADMIN_RECOVERED"


class AdminCommandError(Exception):
    """Lệnh bị từ chối; thông điệp an toàn để in ra (không có email, mật khẩu)."""


def check_password(password: str, min_length: int) -> None:
    problem = password_problem(password, min_length)
    if problem:
        raise AdminCommandError(f"{problem} (AIEOS_PASSWORD_MIN_LENGTH)" if len(password) < min_length else problem)


def _check_email(email: str) -> str:
    email = email.strip()
    if "@" not in email or len(email) > MAX_EMAIL_LENGTH:
        raise AdminCommandError("Email không hợp lệ")
    return email


def _audit(session: Session, action: str, user_id: uuid.UUID, reason: str | None) -> None:
    record(
        session,
        AuditEvent(
            category=Category.SECURITY,
            actor_type=ActorType.BOOTSTRAP,
            action=action,
            outcome=Outcome.SUCCESS,
            resource_type="identity.user_account",
            resource_id=str(user_id),
            reason=reason,
        ),
    )


def bootstrap_admin(
    factory: sessionmaker[Session], *, email: str, display_name: str, password: str, min_length: int
) -> uuid.UUID:
    """Tạo ADMIN đầu tiên; đã có ADMIN `ACTIVE` hoặc email đã tồn tại → `AdminCommandError`, không tạo gì."""
    email = _check_email(email)
    display_name = display_name.strip()
    if not display_name:
        raise AdminCommandError("Tên hiển thị không được rỗng")
    check_password(password, min_length)
    password_hash = hash_password(password)
    with transaction(factory) as session:
        session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": ADMIN_LOCK_KEY})
        if active_admins(session):
            raise AdminCommandError("Đã có ADMIN đang hoạt động — bootstrap bị từ chối")
        exists = session.execute(text("SELECT 1 FROM identity.user_account WHERE email = :e"), {"e": email}).first()
        if exists:
            raise AdminCommandError("Email đã có tài khoản — bootstrap không dùng tài khoản có sẵn")
        user_id = uuid.uuid4()
        session.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, must_enroll_mfa) "
                "VALUES (:i, :e, :n, 'ACTIVE', :p, true)"
            ),
            {"i": user_id, "e": email, "n": display_name, "p": password_hash},
        )
        grant_role(session, user_id=user_id, role="ADMIN", granted_by=None, reason=None)
        _audit(session, "identity.admin.bootstrap", user_id, None)
    return user_id


def recover_admin(
    factory: sessionmaker[Session], *, email: str, password: str, reason: str, min_length: int
) -> uuid.UUID:
    """Khôi phục ADMIN `ACTIVE` theo email (sau khi CLI đã có cờ xác nhận); trả `id` tài khoản đích."""
    email = _check_email(email)
    reason = reason.strip()
    if not reason:
        raise AdminCommandError("Lý do không được rỗng")
    check_password(password, min_length)
    password_hash = hash_password(password)
    with transaction(factory) as session:
        row = session.execute(
            text("SELECT id FROM identity.user_account WHERE email = :e AND status = 'ACTIVE' FOR UPDATE"),
            {"e": email},
        ).first()
        if row is None or "ADMIN" not in roles_of(session, row.id):
            raise AdminCommandError("Không có ADMIN đang hoạt động với email này")
        user_id: uuid.UUID = row.id
        session.execute(
            text(
                "UPDATE identity.user_account SET password_hash = :p, mfa_enabled = false, mfa_secret_enc = NULL, "
                "must_enroll_mfa = true, failed_login_count = 0, locked_until = NULL, version = version + 1, "
                "updated_at = now() WHERE id = :i"
            ),
            {"p": password_hash, "i": user_id},
        )
        session.execute(
            text("UPDATE identity.mfa_recovery_code SET used_at = now() WHERE user_id = :i AND used_at IS NULL"),
            {"i": user_id},
        )
        session.execute(
            text("UPDATE identity.session SET revoked_at = now() WHERE user_id = :i AND revoked_at IS NULL"),
            {"i": user_id},
        )
        _audit(session, "identity.admin.recover", user_id, reason)
        for admin in active_admins(session):
            if admin != user_id:
                notify(
                    session,
                    user_id=admin,
                    type=ADMIN_RECOVERED,
                    title="Một tài khoản quản trị vừa được khôi phục qua CLI — xem nhật ký audit",
                )
    return user_id
