"""M-05 (phần jobs) jobs: bảng `jobs.job` và `jobs.schedule`.

Revision: 0003 (sau 0002)
Yêu cầu/ADR liên quan: T-009, SRS-JOB-01, SRS-JOB-02, SRS-JOB-03, SRS-AIC-06, ADR-005 (+Amendment 1), INV-08;
Database_Design §5; D-56 (M-05 tách: `notify.notification` thuộc revision của T-010; lịch chỉ `interval`).

- `jobs.job`: CHECK `job_class`, `status`, `attempts <= max_attempts`, `max_attempts > 0`; job `RUNNING` phải có lease
  và người giữ; `idempotency_key` UNIQUE (INV-08). Index claim `(run_after, id) WHERE status = 'QUEUED'`, index reaper
  `(lease_expires_at) WHERE status = 'RUNNING'`.
- `jobs.schedule`: `interval` dương, không chứa tháng/năm (đổi được sang khoảng thời gian cố định);
  `may_write = (job_class <> 'ORCHESTRATION')` (ADR-005 Amendment 1).
- Quyền: giữ quyền mặc định của 0001 (`aieos_app` SELECT, INSERT, UPDATE; không DELETE).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_CLASSES = "('ORCHESTRATION', 'AI_CONTENT', 'BUSINESS_WRITE')"


def upgrade() -> None:
    op.create_table(
        "job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("job_class", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'QUEUED'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("initiated_by", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_job"),
        sa.UniqueConstraint("idempotency_key", name="uq_job_idempotency_key"),
        sa.CheckConstraint(f"job_class IN {JOB_CLASSES}", name="ck_job_job_class"),
        sa.CheckConstraint(
            "status IN ('QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'DEAD', 'CANCELLED')", name="ck_job_status"
        ),
        sa.CheckConstraint("max_attempts > 0", name="ck_job_max_attempts_positive"),
        sa.CheckConstraint("attempts >= 0 AND attempts <= max_attempts", name="ck_job_attempts_within_max"),
        sa.CheckConstraint(
            "status <> 'RUNNING' OR (lease_expires_at IS NOT NULL AND locked_by IS NOT NULL)",
            name="ck_job_running_lease",
        ),
        sa.CheckConstraint("kind <> '' AND idempotency_key <> ''", name="ck_job_not_empty"),
        schema="jobs",
    )
    op.create_index(
        "ix_job_claim", "job", ["run_after", "id"], schema="jobs", postgresql_where=sa.text("status = 'QUEUED'")
    )
    op.create_index(
        "ix_job_reaper", "job", ["lease_expires_at"], schema="jobs", postgresql_where=sa.text("status = 'RUNNING'")
    )

    op.create_table(
        "schedule",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("job_class", sa.Text(), nullable=False),
        sa.Column("interval", sa.Interval(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("may_write", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_skip_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_schedule"),
        sa.CheckConstraint(f"job_class IN {JOB_CLASSES}", name="ck_schedule_job_class"),
        sa.CheckConstraint("may_write = (job_class <> 'ORCHESTRATION')", name="ck_schedule_may_write"),
        sa.CheckConstraint(
            "interval > interval '0' AND date_part('month', interval) = 0 AND date_part('year', interval) = 0",
            name="ck_schedule_interval_fixed",
        ),
        sa.CheckConstraint("kind <> ''", name="ck_schedule_kind_not_empty"),
        schema="jobs",
    )


def downgrade() -> None:
    op.drop_table("schedule", schema="jobs")
    op.drop_table("job", schema="jobs")
