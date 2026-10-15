"""M-03 access_seed: role, permission, role_permission (seed), user_role, assignment + INV-09, INV-10, INV-11.

Revision: 0005 (sau 0004)
Yêu cầu/ADR liên quan: T-107, SRS-ACC-05, SRS-ACC-06, SRS-ACC-07, SRS-ACC-08, ADR-007, R1–R8 (D-21), A3–A5 (D-22),
INV-09, INV-10, INV-11; Database_Design §4, §8; Architecture §6; Implementation_Plan §5 (M-03).

- Seed theo ma trận Architecture §6 (bản chụp cố định trong revision; test đối chiếu tài liệu). `B` → `BASE`,
  `A` → `ELIGIBLE`. `hr.*`, `pii.unmask` không có role nào; `goals.activate` chỉ `ELIGIBLE` (D-39).
  Không seed tài khoản.
- INV-09: CHECK `granted_by <> user_id` (`user_role`, `assignment`), `revoked_by <> user_id` (`assignment`).
- INV-10: trigger từ chối tài khoản có cả `ADMIN` và `CFO` (SQLSTATE `AE001`).
- INV-11: trigger từ chối thay đổi làm mất ADMIN `ACTIVE` cuối cùng — gỡ role ADMIN hoặc chuyển tài khoản ADMIN khỏi
  `ACTIVE` (SQLSTATE `AE002`); trigger giữ advisory lock `admin-membership` để tuần tự hóa (A4).
- Assignment: permission phải `assignable` và user có role `ELIGIBLE` cho permission (SQLSTATE `AE003`); phạm vi, thời
  hạn, lý do bắt buộc; thu hồi bằng `revoked_at`, không xóa.
- Quyền: `aieos_app` thêm DELETE trên `access.user_role` (gỡ role — Database_Design §4); không DELETE `assignment`.
  Bảng danh mục (`role`, `permission`, `role_permission`) chỉ SELECT cho `aieos_app`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = ("ADMIN", "CEO", "CFO", "MANAGER", "EMPLOYEE")
# (permission, category, {role: 'BASE' | 'ELIGIBLE'}) — Architecture §6 tại thời điểm T-107.
MATRIX: tuple[tuple[str, str, dict[str, str]], ...] = (
    ("org.directory.read", "READ", {r: "BASE" for r in ROLES}),
    ("data.read", "READ", {"CEO": "BASE", "CFO": "BASE", "MANAGER": "BASE", "EMPLOYEE": "BASE"}),
    ("finance.read", "READ", {"CEO": "BASE", "CFO": "BASE", "MANAGER": "ELIGIBLE"}),
    ("hr.import", "WRITE", {"ADMIN": "BASE"}),
    ("hr.profile.read", "READ", {}),
    ("hr.salary.read", "READ", {}),
    ("hr.export", "READ", {}),
    ("pii.unmask", "READ", {}),
    ("record.submit", "WRITE", {"CEO": "BASE", "CFO": "BASE", "MANAGER": "BASE", "EMPLOYEE": "BASE"}),
    ("action.confirm", "APPROVE", {"CEO": "BASE", "CFO": "BASE", "MANAGER": "BASE", "EMPLOYEE": "BASE"}),
    ("action.undo", "WRITE", {"CEO": "BASE", "CFO": "BASE", "MANAGER": "BASE", "EMPLOYEE": "BASE"}),
    (
        "extraction.review",
        "APPROVE",
        {"CEO": "ELIGIBLE", "CFO": "ELIGIBLE", "MANAGER": "ELIGIBLE", "EMPLOYEE": "ELIGIBLE"},
    ),
    ("finance.submit", "WRITE", {"CFO": "ELIGIBLE", "MANAGER": "ELIGIBLE"}),
    ("finance.approve", "APPROVE", {"CFO": "ELIGIBLE"}),
    ("finance.reverse.request", "WRITE", {"CFO": "ELIGIBLE"}),
    ("finance.period.manage", "APPROVE", {"CFO": "ELIGIBLE"}),
    ("audit.read.admin", "ADMIN", {"ADMIN": "BASE"}),
    ("audit.read.business", "READ", {"CEO": "BASE"}),
    ("user.manage", "ADMIN", {"ADMIN": "BASE"}),
    ("role.assign", "ADMIN", {"ADMIN": "BASE"}),
    ("assignment.manage", "ADMIN", {"ADMIN": "BASE"}),
    ("config.document_schema", "ADMIN", {"ADMIN": "BASE"}),
    ("config.autonomy", "ADMIN", {"ADMIN": "BASE"}),
    ("config.draft_expiry", "ADMIN", {"ADMIN": "BASE"}),
    ("config.briefing_schedule", "ADMIN", {"ADMIN": "BASE"}),
    ("goals.activate", "APPROVE", {"CEO": "ELIGIBLE", "MANAGER": "ELIGIBLE"}),
    ("ai.kill_switch", "ADMIN", {"ADMIN": "BASE"}),
    ("system.health.read", "ADMIN", {"ADMIN": "BASE"}),
    ("ai.use", "AI", {r: "BASE" for r in ROLES}),
)
ADMIN_LOCK_KEY = 0x41454F53_00000002  # "AEOS", 2 — advisory lock `admin-membership` (A4)

_TRIGGERS = f"""
CREATE FUNCTION access.reject_admin_cfo() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.role_code IN ('ADMIN', 'CFO') AND EXISTS (
        SELECT 1 FROM access.user_role
         WHERE user_id = NEW.user_id
           AND role_code = CASE NEW.role_code WHEN 'ADMIN' THEN 'CFO' ELSE 'ADMIN' END) THEN
        RAISE EXCEPTION 'ROLE_COMBINATION_FORBIDDEN: ADMIN và CFO trên cùng tài khoản (INV-10)' USING ERRCODE = 'AE001';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_user_role_no_admin_cfo BEFORE INSERT OR UPDATE ON access.user_role
    FOR EACH ROW EXECUTE FUNCTION access.reject_admin_cfo();

CREATE FUNCTION access.active_admin_count(excluding uuid) RETURNS bigint LANGUAGE sql STABLE AS $$
    SELECT count(DISTINCT ur.user_id) FROM access.user_role ur
      JOIN identity.user_account ua ON ua.id = ur.user_id
     WHERE ur.role_code = 'ADMIN' AND ua.status = 'ACTIVE' AND ur.user_id <> excluding
$$;

CREATE FUNCTION access.guard_last_admin_role() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.role_code = 'ADMIN' AND (TG_OP = 'DELETE' OR NEW.role_code <> 'ADMIN' OR NEW.user_id <> OLD.user_id) THEN
        PERFORM pg_advisory_xact_lock({ADMIN_LOCK_KEY});
        IF EXISTS (SELECT 1 FROM identity.user_account WHERE id = OLD.user_id AND status = 'ACTIVE')
           AND access.active_admin_count(OLD.user_id) = 0 THEN
            RAISE EXCEPTION 'LAST_ADMIN: không gỡ ADMIN hoạt động cuối cùng (INV-11)' USING ERRCODE = 'AE002';
        END IF;
    END IF;
    RETURN COALESCE(NEW, OLD);
END $$;

CREATE TRIGGER trg_last_admin_guard BEFORE DELETE OR UPDATE ON access.user_role
    FOR EACH ROW EXECUTE FUNCTION access.guard_last_admin_role();

CREATE FUNCTION access.guard_last_admin_status() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'ACTIVE' AND NEW.status <> 'ACTIVE'
       AND EXISTS (SELECT 1 FROM access.user_role WHERE user_id = OLD.id AND role_code = 'ADMIN') THEN
        PERFORM pg_advisory_xact_lock({ADMIN_LOCK_KEY});
        IF access.active_admin_count(OLD.id) = 0 THEN
            RAISE EXCEPTION 'LAST_ADMIN: không khóa/vô hiệu ADMIN hoạt động cuối cùng (INV-11)' USING ERRCODE = 'AE002';
        END IF;
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_last_admin_status BEFORE UPDATE OF status ON identity.user_account
    FOR EACH ROW EXECUTE FUNCTION access.guard_last_admin_status();

CREATE FUNCTION access.check_assignment_eligibility() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM access.permission WHERE code = NEW.permission_code AND assignable) OR NOT EXISTS (
        SELECT 1 FROM access.user_role ur
          JOIN access.role_permission rp ON rp.role_code = ur.role_code
         WHERE ur.user_id = NEW.user_id AND rp.permission_code = NEW.permission_code AND rp.kind = 'ELIGIBLE') THEN
        RAISE EXCEPTION 'ASSIGNMENT_NOT_ELIGIBLE: tài khoản không có role đủ điều kiện (SRS-ACC-08)'
            USING ERRCODE = 'AE003';
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER trg_assignment_eligibility BEFORE INSERT OR UPDATE OF user_id, permission_code ON access.assignment
    FOR EACH ROW EXECUTE FUNCTION access.check_assignment_eligibility();
"""


def upgrade() -> None:
    op.create_table(
        "role",
        sa.Column("code", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_role"),
        schema="access",
    )
    op.create_table(
        "permission",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("assignable", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_permission"),
        sa.CheckConstraint("category IN ('READ', 'WRITE', 'APPROVE', 'ADMIN', 'AI')", name="ck_permission_category"),
        schema="access",
    )
    op.create_table(
        "role_permission",
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("permission_code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("role_code", "permission_code", name="pk_role_permission"),
        sa.ForeignKeyConstraint(["role_code"], ["access.role.code"], name="fk_role_permission_role_code_role"),
        sa.ForeignKeyConstraint(
            ["permission_code"], ["access.permission.code"], name="fk_role_permission_permission_code_permission"
        ),
        sa.CheckConstraint("kind IN ('BASE', 'ELIGIBLE')", name="ck_role_permission_kind"),
        schema="access",
    )
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_code", sa.Text(), nullable=False),
        sa.Column("granted_by", sa.Uuid(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("user_id", "role_code", name="pk_user_role"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.user_account.id"], name="fk_user_role_user_id_user_account"),
        sa.ForeignKeyConstraint(["role_code"], ["access.role.code"], name="fk_user_role_role_code_role"),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["identity.user_account.id"], name="fk_user_role_granted_by_user_account"
        ),
        sa.CheckConstraint("granted_by IS NULL OR granted_by <> user_id", name="ck_user_role_not_self_granted"),
        sa.CheckConstraint(
            "granted_by IS NULL OR (reason IS NOT NULL AND reason <> '')", name="ck_user_role_reason_required"
        ),
        schema="access",
    )
    op.create_table(
        "assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("permission_code", sa.Text(), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_assignment"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.user_account.id"], name="fk_assignment_user_id_user_account"),
        sa.ForeignKeyConstraint(
            ["permission_code"], ["access.permission.code"], name="fk_assignment_permission_code_permission"
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"], ["identity.user_account.id"], name="fk_assignment_granted_by_user_account"
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by"], ["identity.user_account.id"], name="fk_assignment_revoked_by_user_account"
        ),
        sa.CheckConstraint(
            "scope_type IN ('COMPANY', 'ORG_UNIT', 'DOCUMENT_TYPE', 'REVIEW_QUEUE')", name="ck_assignment_scope_type"
        ),
        sa.CheckConstraint(
            "(scope_type = 'COMPANY') = (scope_id IS NULL) AND (scope_id IS NULL OR scope_id <> '')",
            name="ck_assignment_scope_id",
        ),
        sa.CheckConstraint("valid_to IS NULL OR valid_to > valid_from", name="ck_assignment_validity"),
        sa.CheckConstraint("granted_by <> user_id", name="ck_assignment_not_self_granted"),
        sa.CheckConstraint("revoked_by IS NULL OR revoked_by <> user_id", name="ck_assignment_not_self_revoked"),
        sa.CheckConstraint("(revoked_at IS NULL) = (revoked_by IS NULL)", name="ck_assignment_revocation"),
        sa.CheckConstraint("reason <> ''", name="ck_assignment_reason"),
        schema="access",
    )
    op.create_index("ix_assignment_user", "assignment", ["user_id", "permission_code"], schema="access")

    role_table = sa.table("role", sa.column("code", sa.Text()), schema="access")
    permission_table = sa.table(
        "permission",
        sa.column("code", sa.Text()),
        sa.column("category", sa.Text()),
        sa.column("assignable", sa.Boolean()),
        schema="access",
    )
    role_permission_table = sa.table(
        "role_permission",
        sa.column("role_code", sa.Text()),
        sa.column("permission_code", sa.Text()),
        sa.column("kind", sa.Text()),
        schema="access",
    )
    op.bulk_insert(role_table, [{"code": r} for r in ROLES])
    op.bulk_insert(
        permission_table,
        [
            {"code": code, "category": category, "assignable": "ELIGIBLE" in roles.values()}
            for code, category, roles in MATRIX
        ],
    )
    op.bulk_insert(
        role_permission_table,
        [
            {"role_code": role, "permission_code": code, "kind": kind}
            for code, _, roles in MATRIX
            for role, kind in roles.items()
        ],
    )

    op.execute(_TRIGGERS)
    op.execute("REVOKE INSERT, UPDATE ON access.role, access.permission, access.role_permission FROM aieos_app")
    op.execute("GRANT DELETE ON access.user_role TO aieos_app")


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_last_admin_status ON identity.user_account")
    for table in ("assignment", "user_role", "role_permission", "permission", "role"):
        op.drop_table(table, schema="access")
    for function in (
        "reject_admin_cfo()",
        "guard_last_admin_role()",
        "guard_last_admin_status()",
        "check_assignment_eligibility()",
        "active_admin_count(uuid)",
    ):
        op.execute(f"DROP FUNCTION access.{function}")
