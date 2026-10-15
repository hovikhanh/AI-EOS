"""M-06 org: `org.org_unit`, `org.employee` (chỉ trường danh bạ) + khóa ngoại `identity.user_account.employee_id`.

Revision: 0010 (sau 0009)
Yêu cầu/ADR liên quan: T-201, SRS-ACC-11, SRS-ACC-03 (phạm vi MANAGER qua cây đơn vị), R6; Database_Design §6;
Implementation_Plan §5 (M-06).

- `org_unit`: `name` không rỗng; `code` UNIQUE (NULL được); `parent_id` tự tham chiếu, không trỏ chính nó; trigger
  `trg_org_unit_no_cycle` từ chối thay đổi tạo vòng trong cây (SQLSTATE `AE004`).
- `employee`: chỉ trường danh bạ (họ tên, chức danh, đơn vị, quản lý trực tiếp) — không có CCCD, lương, sức khỏe
  (R6; nếu cần: bảng riêng `org.employee_sensitive`). `status` CHECK `ACTIVE`/`INACTIVE` (`[CẦN XÁC NHẬN]` danh sách
  giá trị — Database_Design chỉ ghi `status`). `manager_id` không trỏ chính nó; trigger `trg_employee_no_cycle`
  (SQLSTATE `AE005`).
- `org_unit.head_employee_id` → `employee` (thêm sau khi tạo `employee`).
- `source_document_id` (uuid NULL): khóa ngoại tới `capture.source_document` thêm ở migration của T-202.
- `identity.user_account.employee_id` → `org.employee` (T-101 để dành cho T-201).
- Quyền: giữ quyền mặc định của 0001 (`aieos_app` SELECT, INSERT, UPDATE; không DELETE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NO_CYCLE = """
CREATE FUNCTION org.{name}() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.{parent} IS NOT NULL AND EXISTS (
        WITH RECURSIVE up(id) AS (
            SELECT NEW.{parent}
            UNION
            SELECT t.{parent} FROM org.{table} t JOIN up ON t.id = up.id WHERE t.{parent} IS NOT NULL
        )
        SELECT 1 FROM up WHERE id = NEW.id
    ) THEN
        RAISE EXCEPTION '{message}' USING ERRCODE = '{code}';
    END IF;
    RETURN NEW;
END
$$;
CREATE TRIGGER trg_{name} BEFORE INSERT OR UPDATE OF {parent} ON org.{table}
    FOR EACH ROW EXECUTE FUNCTION org.{name}();
"""


def _now() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "org_unit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("head_employee_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_org_unit"),
        sa.UniqueConstraint("code", name="uq_org_unit_code"),
        sa.ForeignKeyConstraint(["parent_id"], ["org.org_unit.id"], name="fk_org_unit_parent_id_org_unit"),
        sa.CheckConstraint("name <> ''", name="ck_org_unit_name"),
        sa.CheckConstraint("code IS NULL OR code <> ''", name="ck_org_unit_code"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_org_unit_not_own_parent"),
        sa.CheckConstraint("version >= 1", name="ck_org_unit_version"),
        schema="org",
    )
    op.create_index("ix_org_unit_parent", "org_unit", ["parent_id"], schema="org")
    op.create_table(
        "employee",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("manager_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_employee"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_employee_org_unit_id_org_unit"),
        sa.ForeignKeyConstraint(["manager_id"], ["org.employee.id"], name="fk_employee_manager_id_employee"),
        sa.CheckConstraint("full_name <> ''", name="ck_employee_full_name"),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_employee_status"),
        sa.CheckConstraint("manager_id IS NULL OR manager_id <> id", name="ck_employee_not_own_manager"),
        sa.CheckConstraint("version >= 1", name="ck_employee_version"),
        schema="org",
    )
    op.create_index("ix_employee_org_unit", "employee", ["org_unit_id"], schema="org")
    op.create_index("ix_employee_name", "employee", ["full_name", "id"], schema="org")
    op.create_foreign_key(
        "fk_org_unit_head_employee_id_employee",
        "org_unit",
        "employee",
        ["head_employee_id"],
        ["id"],
        source_schema="org",
        referent_schema="org",
    )
    op.create_index("ix_org_unit_head", "org_unit", ["head_employee_id"], schema="org")
    op.create_foreign_key(
        "fk_user_account_employee_id_employee",
        "user_account",
        "employee",
        ["employee_id"],
        ["id"],
        source_schema="identity",
        referent_schema="org",
    )
    op.execute(
        NO_CYCLE.format(
            name="org_unit_no_cycle", table="org_unit", parent="parent_id", message="org_unit cycle", code="AE004"
        )
    )
    op.execute(
        NO_CYCLE.format(
            name="employee_no_cycle", table="employee", parent="manager_id", message="manager cycle", code="AE005"
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_account_employee_id_employee", "user_account", schema="identity", type_="foreignkey")
    op.drop_constraint("fk_org_unit_head_employee_id_employee", "org_unit", schema="org", type_="foreignkey")
    op.drop_table("employee", schema="org")
    op.drop_table("org_unit", schema="org")
    op.execute("DROP FUNCTION IF EXISTS org.employee_no_cycle()")
    op.execute("DROP FUNCTION IF EXISTS org.org_unit_no_cycle()")
