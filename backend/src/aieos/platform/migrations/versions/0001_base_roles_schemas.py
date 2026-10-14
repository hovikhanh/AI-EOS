"""M-01 base_roles_schemas: schema theo module và quyền mặc định của role CSDL.

Revision: 0001 (đầu chuỗi)
Yêu cầu/ADR liên quan: T-005, SRS-NFR-03, ADR-001, ADR-004, Database_Design §2, §10; Implementation_Plan §5 (M-01).

- Chạy bằng `aieos_owner` (đã là chủ CSDL qua sql/provision_roles.sql): mọi schema thuộc `aieos_owner`.
- `aieos_app`: USAGE trên schema; mặc định SELECT, INSERT, UPDATE trên bảng và USAGE, SELECT trên sequence do
  `aieos_owner` tạo sau này. Không DDL, không DELETE/TRUNCATE mặc định (cấp riêng theo bảng ở migration sau nếu cần).
- `aieos_backup`: USAGE và SELECT (chỉ đọc).
- `aieos_app` được đọc `alembic_version` để kiểm tra phiên bản migration ở `/health/ready` (Database_Design §10).
Danh sách schema giữ cố định ở đây (không import hằng số) để revision không đổi theo code.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = (
    "identity",
    "access",
    "org",
    "capture",
    "goals",
    "work",
    "insights",
    "knowledge",
    "finance",
    "ai",
    "jobs",
    "audit",
    "notify",
)


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f"CREATE SCHEMA {schema} AUTHORIZATION aieos_owner")
        op.execute(f"REVOKE ALL ON SCHEMA {schema} FROM PUBLIC")
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO aieos_app, aieos_backup")
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} "
            "GRANT SELECT, INSERT, UPDATE ON TABLES TO aieos_app"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} "
            "GRANT USAGE, SELECT ON SEQUENCES TO aieos_app"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} GRANT SELECT ON TABLES TO aieos_backup"
        )
    op.execute("GRANT SELECT ON public.alembic_version TO aieos_app, aieos_backup")


def downgrade() -> None:
    op.execute("REVOKE SELECT ON public.alembic_version FROM aieos_app, aieos_backup")
    for schema in reversed(SCHEMAS):
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} REVOKE ALL ON TABLES FROM aieos_backup"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} REVOKE ALL ON SEQUENCES FROM aieos_app"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE aieos_owner IN SCHEMA {schema} REVOKE ALL ON TABLES FROM aieos_app"
        )
        op.execute(f"DROP SCHEMA {schema} RESTRICT")
