"""M-02 identity: tài khoản, session, lời mời, mã khôi phục MFA, lần đăng nhập.

Revision: 0004 (sau 0003)
Yêu cầu/ADR liên quan: T-101, SRS-IAM-06, ADR-006, INV-16; Database_Design §4; Implementation_Plan §5 (M-02).

- INV-16 (token chỉ lưu hash): `session.token_hash`, `session.csrf_token_hash`, `invitation.token_hash`,
  `mfa_recovery_code.code_hash`, `login_attempt.email_hash` là `bytea` đúng 32 byte (SHA-256); không có cột token rõ.
- `user_account`: email `citext` UNIQUE (extension `citext`, trusted — chủ CSDL tạo được); `INVITED` ⇔ chưa có
  `password_hash`; `mfa_enabled` ⇒ có `mfa_secret_enc`; `version` cho optimistic locking (Database_Design §1).
- `invitation`: không đồng thời `used_at` và `revoked_at`; một lời mời còn hiệu lực mỗi user (unique có điều kiện).
- `session`: index `(user_id) WHERE revoked_at IS NULL` để thu hồi hàng loạt (A3).
- Chưa có khóa ngoại `user_account.employee_id` → `org.employee` (bảng của T-201); thêm ở migration của T-201.
- Quyền: giữ quyền mặc định của 0001 (`aieos_app` SELECT, INSERT, UPDATE; không DELETE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SHA256 = "octet_length({}) = 32"


def _now() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public")

    op.create_table(
        "user_account",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("mfa_secret_enc", postgresql.BYTEA(), nullable=True),
        sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("must_enroll_mfa", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("failed_login_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("employee_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_user_account"),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
        sa.UniqueConstraint("employee_id", name="uq_user_account_employee_id"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["identity.user_account.id"], name="fk_user_account_created_by_user_account"
        ),
        sa.CheckConstraint("status IN ('INVITED', 'ACTIVE', 'LOCKED', 'DISABLED')", name="ck_user_account_status"),
        sa.CheckConstraint(
            "(status = 'INVITED') = (password_hash IS NULL)", name="ck_user_account_password_iff_not_invited"
        ),
        sa.CheckConstraint("NOT mfa_enabled OR mfa_secret_enc IS NOT NULL", name="ck_user_account_mfa_secret"),
        sa.CheckConstraint("failed_login_count >= 0", name="ck_user_account_failed_login_count"),
        sa.CheckConstraint("version >= 1", name="ck_user_account_version"),
        sa.CheckConstraint("display_name <> ''", name="ck_user_account_display_name"),
        schema="identity",
    )

    op.create_table(
        "session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("csrf_token_hash", postgresql.BYTEA(), nullable=True),
        sa.Column("mfa_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("reauth_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_session"),
        sa.UniqueConstraint("token_hash", name="uq_session_token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.user_account.id"], name="fk_session_user_id_user_account"),
        sa.CheckConstraint(SHA256.format("token_hash"), name="ck_session_token_hash_sha256"),
        sa.CheckConstraint(
            "csrf_token_hash IS NULL OR " + SHA256.format("csrf_token_hash"), name="ck_session_csrf_hash_sha256"
        ),
        sa.CheckConstraint("absolute_expires_at > created_at", name="ck_session_absolute_after_created"),
        schema="identity",
    )
    op.create_index(
        "ix_session_active_user",
        "session",
        ["user_id"],
        schema="identity",
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "invitation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_invitation"),
        sa.UniqueConstraint("token_hash", name="uq_invitation_token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.user_account.id"], name="fk_invitation_user_id_user_account"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["identity.user_account.id"], name="fk_invitation_created_by_user_account"
        ),
        sa.CheckConstraint(SHA256.format("token_hash"), name="ck_invitation_token_hash_sha256"),
        sa.CheckConstraint("used_at IS NULL OR revoked_at IS NULL", name="ck_invitation_used_or_revoked"),
        schema="identity",
    )
    op.create_index(
        "uq_invitation_one_active_per_user",
        "invitation",
        ["user_id"],
        unique=True,
        schema="identity",
        postgresql_where=sa.text("used_at IS NULL AND revoked_at IS NULL"),
    )

    op.create_table(
        "mfa_recovery_code",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_mfa_recovery_code"),
        sa.UniqueConstraint("user_id", "code_hash", name="uq_mfa_recovery_code_user_id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["identity.user_account.id"], name="fk_mfa_recovery_code_user_id_user_account"
        ),
        sa.CheckConstraint(SHA256.format("code_hash"), name="ck_mfa_recovery_code_code_hash_sha256"),
        schema="identity",
    )

    op.create_table(
        "login_attempt",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("email_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("ip", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_login_attempt"),
        sa.CheckConstraint(SHA256.format("email_hash"), name="ck_login_attempt_email_hash_sha256"),
        schema="identity",
    )
    op.create_index("ix_login_attempt_email", "login_attempt", ["email_hash", "occurred_at"], schema="identity")
    op.create_index("ix_login_attempt_ip", "login_attempt", ["ip", "occurred_at"], schema="identity")


def downgrade() -> None:
    for table in ("login_attempt", "mfa_recovery_code", "invitation", "session", "user_account"):
        op.drop_table(table, schema="identity")
    op.execute("DROP EXTENSION IF EXISTS citext")
