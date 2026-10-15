"""M-08 (phần task) work: `work.task`.

Revision: 0011 (sau 0010)
Yêu cầu/ADR liên quan: T-505, SRS-WRK-01…04, SRS-WRK-10, SRS-GEN-03 (INV-08); Database_Design §6 (`work.task`).

- `status` CHECK `OPEN`/`DONE` (Q-33 → D-51); `DONE` ⇔ `completed_at` và `completed_by` có giá trị.
- `title` không rỗng; `created_via` CHECK `MANUAL`/`MEETING`/`AI`; `version` cho `If-Match`.
- Idempotency (API-WORK-03 `IDEMPOTENT`, INV-08): `idempotency_key`, `request_hash` (cùng NULL hoặc cùng có),
  UNIQUE `(assigned_by, idempotency_key)` — người giao là người tạo task.
- `objective_id` (FK `goals.objective` — T-501), `source_document_id` (FK `capture.source_document` — T-202),
  `ai_action_id` (FK `ai.action` — T-302): chưa có khóa ngoại, thêm ở migration của task tạo bảng đích.
- Index `(owner_user_id, status, due_date)` (Database_Design §6), `(assigned_by)`.
- Quyền: giữ quyền mặc định của 0001 (`aieos_app` SELECT, INSERT, UPDATE; không DELETE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'OPEN'"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.Uuid(), nullable=True),
        sa.Column("objective_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("source_locator", postgresql.JSONB(), nullable=True),
        sa.Column("created_via", sa.Text(), server_default=sa.text("'MANUAL'"), nullable=False),
        sa.Column("ai_action_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("request_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_task"),
        sa.UniqueConstraint("assigned_by", "idempotency_key", name="uq_task_assigned_by"),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["identity.user_account.id"], name="fk_task_owner_user_id_user_account"
        ),
        sa.ForeignKeyConstraint(["assigned_by"], ["identity.user_account.id"], name="fk_task_assigned_by_user_account"),
        sa.ForeignKeyConstraint(
            ["completed_by"], ["identity.user_account.id"], name="fk_task_completed_by_user_account"
        ),
        sa.CheckConstraint("title <> ''", name="ck_task_title"),
        sa.CheckConstraint("status IN ('OPEN', 'DONE')", name="ck_task_status"),
        sa.CheckConstraint(
            "(status = 'DONE') = (completed_at IS NOT NULL) AND (completed_at IS NULL) = (completed_by IS NULL)",
            name="ck_task_done_iff_completed",
        ),
        sa.CheckConstraint("created_via IN ('MANUAL', 'MEETING', 'AI')", name="ck_task_created_via"),
        sa.CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="ck_task_idempotency_hash"),
        sa.CheckConstraint("version >= 1", name="ck_task_version"),
        schema="work",
    )
    op.create_index("ix_task_owner_status_due", "task", ["owner_user_id", "status", "due_date"], schema="work")
    op.create_index("ix_task_assigned_by", "task", ["assigned_by"], schema="work")


def downgrade() -> None:
    op.drop_table("task", schema="work")
