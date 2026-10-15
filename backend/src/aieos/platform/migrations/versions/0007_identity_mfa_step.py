"""M-02 (bổ sung) identity: `user_account.mfa_last_step` — chống dùng lại mã TOTP.

Revision: 0007 (sau 0006)
Yêu cầu/ADR liên quan: T-103, SRS-IAM-05, ADR-006 (MFA TOTP); RFC 6238 §5.2 (mã đã chấp nhận không được chấp nhận lại).

- `mfa_last_step`: bước thời gian (Unix time / 30 giây) của mã TOTP được chấp nhận gần nhất; mã có bước ≤ giá trị này bị
  từ chối. NULL khi chưa dùng mã nào. CHECK `>= 0`.
- Quyền: giữ quyền mặc định của 0001.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_account", sa.Column("mfa_last_step", sa.BigInteger(), nullable=True), schema="identity")
    op.create_check_constraint("ck_user_account_mfa_last_step", "user_account", "mfa_last_step >= 0", schema="identity")


def downgrade() -> None:
    op.drop_constraint("ck_user_account_mfa_last_step", "user_account", schema="identity", type_="check")
    op.drop_column("user_account", "mfa_last_step", schema="identity")
