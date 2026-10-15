"""M-02 (bổ sung) identity: idempotency cho `identity.user_account` (API-ADM-02 `IDEMPOTENT`).

Revision: 0009 (sau 0008)
Yêu cầu/ADR liên quan: T-105, SRS-IAM-01, SRS-GEN-03, INV-08 (Database_Design §8), API_Specification §1.6.

- `idempotency_key` text NULL (tài khoản tạo bằng CLI bootstrap không có khóa), `request_hash` text NULL (SHA-256 hex —
  `platform.api.request_fingerprint`); cùng NULL hoặc cùng có giá trị (CHECK).
- UNIQUE `(created_by, idempotency_key)` (NULL không trùng nhau).
- Quyền: giữ quyền mặc định của 0001.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("idempotency_key", sa.Text(), nullable=True), schema="identity")
    op.add_column("user_account", sa.Column("request_hash", sa.Text(), nullable=True), schema="identity")
    op.create_check_constraint(
        "ck_user_account_idempotency_hash",
        "user_account",
        "(idempotency_key IS NULL) = (request_hash IS NULL)",
        schema="identity",
    )
    op.create_unique_constraint(
        "uq_user_account_created_by", "user_account", ["created_by", "idempotency_key"], schema="identity"
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_account_created_by", "user_account", schema="identity", type_="unique")
    op.drop_constraint("ck_user_account_idempotency_hash", "user_account", schema="identity", type_="check")
    op.drop_column("user_account", "request_hash", schema="identity")
    op.drop_column("user_account", "idempotency_key", schema="identity")
