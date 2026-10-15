"""M-05 (phần notify) notify: bảng `notify.notification`.

Revision: 0006 (sau 0005)
Yêu cầu/ADR liên quan: T-010, SRS-NTF-01, SRS-NTF-02; Database_Design §9 (`notify.notification`), index
`(user_id, read_at)` (Database_Design §8); D-56 (M-05 tách: phần `jobs.*` ở 0003), D-58.

- `type`, `title` không rỗng; `link` (nếu có) là đường dẫn nội bộ bắt đầu bằng một `/` — không URL tuyệt đối, không
  `//` hay `/\\` (trình duyệt hiểu là host khác), để thông báo không dẫn ra ngoài hệ thống.
- Nội dung không chứa dữ liệu nhạy cảm (SRS-NTF-02): trách nhiệm của module gọi `notify.api.notify`; CSDL không kiểm
  được nội dung.
- Quyền: giữ quyền mặc định của 0001 (`aieos_app` SELECT, INSERT, UPDATE; không DELETE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INTERNAL_LINK = r"link IS NULL OR link ~ '^/([^/\\]|$)'"


def upgrade() -> None:
    op.create_table(
        "notification",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_notification"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.user_account.id"], name="fk_notification_user_id_user_account"),
        sa.CheckConstraint("type <> ''", name="ck_notification_type"),
        sa.CheckConstraint("title <> ''", name="ck_notification_title"),
        sa.CheckConstraint(INTERNAL_LINK, name="ck_notification_internal_link"),
        sa.CheckConstraint("read_at IS NULL OR read_at >= created_at", name="ck_notification_read_after_created"),
        schema="notify",
    )
    op.create_index("ix_notification_user_read", "notification", ["user_id", "read_at"], schema="notify")
    op.create_index("ix_notification_user_created", "notification", ["user_id", "created_at", "id"], schema="notify")


def downgrade() -> None:
    op.drop_table("notification", schema="notify")
