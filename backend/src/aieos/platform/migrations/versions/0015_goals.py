"""M-08 (phần goals) goals: `objective`, `key_result`, `kpi`, `measurement`, `check_in`.

Revision: 0015 (sau 0014)
Yêu cầu/ADR liên quan: T-501, SRS-GOAL-01…03, 05…07, 09, 11; Database_Design §6 (`goals.*`); D-39, D-51 (Q-28, Q-30).

- `status` CHECK `DRAFT`/`ACTIVE` (Q-28: chỉ hai trạng thái); `ACTIVE` ⇒ `activated_by`, `activated_at`
  (kích hoạt: T-502).
- `objective.parent_id` tự tham chiếu, không trỏ chính nó; `org_unit_id` NULL = cấp công ty.
- `key_result`, `kpi`: `baseline`, `target` kiểu `numeric` (không float); thêm `created_by` (Database_Design chỉ ghi ở
  `objective`) để idempotency theo người tạo và audit.
- Idempotency (API-GOAL-03/05/06 `IDEMPOTENT`, INV-08): `idempotency_key`, `request_hash`, UNIQUE theo người tạo.
- `measurement`, `check_in` append-only: `aieos_app` chỉ SELECT, INSERT; `measurement.target_id` phải trỏ tới KR/KPI
  có thật (trigger, SQLSTATE `AE040`).
- `check_in.confidence` 0–10 (Q-30 → D-51, thang theo đề xuất SRS-GOAL-07).
- Không có cột % đạt hay cảnh báo (SRS-GOAL-09; công thức Q-29 chưa duyệt).
- Khóa ngoại `work.task.objective_id` → `goals.objective` (để dành từ T-505).
- Index `goals.objective (org_unit_id, status)`, `goals.measurement (target_type, target_id, created_at)`.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER = "identity.user_account.id"
DOC = "capture.source_document.id"
STATUS = "status IN ('DRAFT', 'ACTIVE')"
ACTIVATED = "(status = 'ACTIVE') = (activated_by IS NOT NULL AND activated_at IS NOT NULL)"

TRIGGER = """
CREATE FUNCTION goals.measurement_target_exists() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.target_type = 'KR' AND NOT EXISTS (SELECT 1 FROM goals.key_result WHERE id = NEW.target_id))
       OR (NEW.target_type = 'KPI' AND NOT EXISTS (SELECT 1 FROM goals.kpi WHERE id = NEW.target_id)) THEN
        RAISE EXCEPTION 'measurement target not found' USING ERRCODE = 'AE040';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_measurement_target_exists BEFORE INSERT ON goals.measurement
    FOR EACH ROW EXECUTE FUNCTION goals.measurement_target_exists();
"""


def _now() -> sa.TextClause:
    return sa.text("now()")


def _common(table: str) -> list[Any]:
    return [
        sa.Column("status", sa.Text(), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("activated_by", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("request_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=f"pk_{table}"),
        sa.UniqueConstraint("created_by", "idempotency_key", name=f"uq_{table}_created_by"),
        sa.ForeignKeyConstraint(["owner_user_id"], [USER], name=f"fk_{table}_owner_user_id_user_account"),
        sa.ForeignKeyConstraint(["activated_by"], [USER], name=f"fk_{table}_activated_by_user_account"),
        sa.ForeignKeyConstraint(["created_by"], [USER], name=f"fk_{table}_created_by_user_account"),
        sa.ForeignKeyConstraint(["source_document_id"], [DOC], name=f"fk_{table}_source_document_id_source_document"),
        sa.CheckConstraint(STATUS, name=f"ck_{table}_status"),
        sa.CheckConstraint(ACTIVATED, name=f"ck_{table}_activated"),
        sa.CheckConstraint("period_label <> ''", name=f"ck_{table}_period_label"),
        sa.CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name=f"ck_{table}_idempotency_hash"),
        sa.CheckConstraint("version >= 1", name=f"ck_{table}_version"),
    ]


def _metric() -> list[Any]:
    return [
        sa.Column("metric", sa.Text(), nullable=False),
        sa.Column("baseline", sa.Numeric(), nullable=True),
        sa.Column("target", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "objective",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("period_label", sa.Text(), nullable=False),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        *_common("objective"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_objective_org_unit_id_org_unit"),
        sa.ForeignKeyConstraint(["parent_id"], ["goals.objective.id"], name="fk_objective_parent_id_objective"),
        sa.CheckConstraint("title <> ''", name="ck_objective_title"),
        sa.CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_objective_not_own_parent"),
        schema="goals",
    )
    op.create_index("ix_objective_unit_status", "objective", ["org_unit_id", "status"], schema="goals")
    op.create_table(
        "key_result",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("objective_id", sa.Uuid(), nullable=False),
        *_metric(),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("period_label", sa.Text(), nullable=False),
        *_common("key_result"),
        sa.ForeignKeyConstraint(["objective_id"], ["goals.objective.id"], name="fk_key_result_objective_id_objective"),
        sa.CheckConstraint("metric <> ''", name="ck_key_result_metric"),
        schema="goals",
    )
    op.create_index("ix_key_result_objective", "key_result", ["objective_id"], schema="goals")
    op.create_table(
        "kpi",
        sa.Column("id", sa.Uuid(), nullable=False),
        *_metric(),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("period_label", sa.Text(), nullable=False),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        *_common("kpi"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_kpi_org_unit_id_org_unit"),
        sa.CheckConstraint("metric <> ''", name="ck_kpi_metric"),
        schema="goals",
    )
    op.create_table(
        "measurement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("report_period_label", sa.Text(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("request_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_measurement"),
        sa.UniqueConstraint("recorded_by", "idempotency_key", name="uq_measurement_recorded_by"),
        sa.ForeignKeyConstraint(["recorded_by"], [USER], name="fk_measurement_recorded_by_user_account"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], [DOC], name="fk_measurement_source_document_id_source_document"
        ),
        sa.CheckConstraint("target_type IN ('KR', 'KPI')", name="ck_measurement_target_type"),
        sa.CheckConstraint("report_period_label <> ''", name="ck_measurement_report_period_label"),
        sa.CheckConstraint(
            "(idempotency_key IS NULL) = (request_hash IS NULL)", name="ck_measurement_idempotency_hash"
        ),
        schema="goals",
    )
    op.create_index("ix_measurement_target", "measurement", ["target_type", "target_id", "created_at"], schema="goals")
    op.create_table(
        "check_in",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key_result_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("confidence", sa.SmallInteger(), nullable=False),
        sa.Column("blocker", sa.Text(), nullable=True),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("request_hash", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_check_in"),
        sa.UniqueConstraint("submitted_by", "idempotency_key", name="uq_check_in_submitted_by"),
        sa.ForeignKeyConstraint(
            ["key_result_id"], ["goals.key_result.id"], name="fk_check_in_key_result_id_key_result"
        ),
        sa.ForeignKeyConstraint(["submitted_by"], [USER], name="fk_check_in_submitted_by_user_account"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 10", name="ck_check_in_confidence"),
        sa.CheckConstraint("(idempotency_key IS NULL) = (request_hash IS NULL)", name="ck_check_in_idempotency_hash"),
        schema="goals",
    )
    op.create_index("ix_check_in_key_result", "check_in", ["key_result_id", "created_at"], schema="goals")
    op.execute(TRIGGER)
    op.execute("REVOKE UPDATE ON goals.measurement, goals.check_in FROM aieos_app")
    op.create_foreign_key(
        "fk_task_objective_id_objective", "task", "objective", ["objective_id"], ["id"],
        source_schema="work", referent_schema="goals",
    )  # fmt: skip


def downgrade() -> None:
    op.drop_constraint("fk_task_objective_id_objective", "task", schema="work", type_="foreignkey")
    for table in ("check_in", "measurement", "kpi", "key_result", "objective"):
        op.drop_table(table, schema="goals")
    op.execute("DROP FUNCTION IF EXISTS goals.measurement_target_exists()")
