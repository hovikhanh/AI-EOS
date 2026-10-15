"""M-03 (bổ sung) access: idempotency cho `access.assignment` (API-ADM-07 `IDEMPOTENT`).

Revision: 0008 (sau 0007)
Yêu cầu/ADR liên quan: T-109, SRS-GEN-03, SRS-ACC-08, INV-08 (Database_Design §8: bảng có endpoint `IDEMPOTENT` lưu
khóa + dấu vân tay request), API_Specification §1.6.

- `idempotency_key` text NULL (assignment tạo ngoài API — CLI/test — không có khóa), `request_hash` text NULL
  (SHA-256 hex của request — `platform.api.request_fingerprint`); có khóa thì phải có dấu vân tay (CHECK).
- UNIQUE `(granted_by, idempotency_key)` (NULL không trùng nhau).
- Quyền: giữ quyền đã cấp ở 0005.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("assignment", sa.Column("idempotency_key", sa.Text(), nullable=True), schema="access")
    op.add_column("assignment", sa.Column("request_hash", sa.Text(), nullable=True), schema="access")
    op.create_check_constraint(
        "ck_assignment_idempotency_hash",
        "assignment",
        "(idempotency_key IS NULL) = (request_hash IS NULL)",
        schema="access",
    )
    op.create_unique_constraint(
        "uq_assignment_granted_by", "assignment", ["granted_by", "idempotency_key"], schema="access"
    )


def downgrade() -> None:
    op.drop_constraint("uq_assignment_granted_by", "assignment", schema="access", type_="unique")
    op.drop_constraint("ck_assignment_idempotency_hash", "assignment", schema="access", type_="check")
    op.drop_column("assignment", "request_hash", schema="access")
    op.drop_column("assignment", "idempotency_key", schema="access")
