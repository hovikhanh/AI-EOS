"""M-10 ai: `tool` (Tool Registry), `autonomy_policy`, `kill_switch`, `setting`, `action`, `call_log`, `feedback`.

Revision: 0013 (sau 0012)
Yêu cầu/ADR liên quan: T-301, SRS-AIC-02, SRS-AIC-03, D-09, D-11, D-12, R8, K5, BR-09, BR-10, ADR-008, ADR-011;
Database_Design §5, INV-12, INV-13.

- `tool`: CHECK trần `0 ≤ max_autonomy_level ≤ 3`, tool tài chính ≤ 2 (INV-12). `risk_level` NULL = chưa phân loại
  (tài liệu chưa có giá trị cho từng tool; `commit_extraction` kế thừa từ tool đích — BR-09).
- Seed: 12 tool theo Database_Design §5 — 10 tool Domain 22 BRD §3.9 + `create_task`, `record_kpi_measurement`.
  `operation_type`: BR-09 (classify/extract/validate READ, commit WRITE); `search_documents`, `get_source_document`
  READ; tool còn lại WRITE. `max_autonomy_level` = 3 (trần chung; không tool nào là tài chính). `enabled = false` cho
  tới khi có handler qua write gateway (T-302 trở đi). `params_schema` NULL (tham số chờ 2B).
- `autonomy_policy`: trigger `level ≤ tool.max_autonomy_level`; đổi trần tool thấp hơn policy hiện có cũng bị chặn
  (INV-12, SQLSTATE `AE030`). Seed mặc định SRS-AIC-03 chỉ cho trường hợp tài liệu nêu rõ: tool READ → L0,
  `create_task` (task nội bộ) → L3; tool khác chưa có policy (T-302 quyết định cách xử lý).
- `kill_switch`: singleton CHECK `id = 1` (INV-13); seed `enabled = false`.
- `setting`: seed `draft_expiry_days = 30` (K5, Database_Design §5). Trần chi phí AI (GAP-14) chưa có giá trị — không
  seed.
- `action`: CHECK `status`, `effective_level` 0–3; UNIQUE `(initiated_by, idempotency_key)`; L3 đã thực thi có
  `undo_deadline ≥ executed_at + 24 giờ` (BR-11); trigger: tool tài chính → `reviewed_by ≠ initiated_by` (`AE031`).
- `call_log`: CHECK `data_classification IN ('SENSITIVE','PERSONAL') → provider_is_local` (ADR-011 gốc, như
  Database_Design §5). Ngoại lệ demo DeepSeek (D-50, ADR-011 Amendment 1) **chưa** phản ánh ở đây — Q-53.
- Khóa ngoại `work.task.ai_action_id`, `finance.transaction.ai_action_id` → `ai.action` (bảng nay đã có).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER = "identity.user_account.id"
TOOLS = (
    # name, module, operation_type
    ("upload_document", "capture", "WRITE"),
    ("classify_document", "capture", "READ"),
    ("extract_document", "capture", "READ"),
    ("validate_extraction", "capture", "READ"),
    ("submit_extraction_for_review", "capture", "WRITE"),
    ("approve_extraction", "capture", "WRITE"),
    ("commit_extraction", "capture", "WRITE"),
    ("import_table", "capture", "WRITE"),
    ("search_documents", "capture", "READ"),
    ("get_source_document", "capture", "READ"),
    ("create_task", "work", "WRITE"),
    ("record_kpi_measurement", "goals", "WRITE"),
)

TRIGGERS = """
CREATE FUNCTION ai.policy_within_cap() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.level > (SELECT max_autonomy_level FROM ai.tool WHERE name = NEW.tool_name) THEN
        RAISE EXCEPTION 'autonomy level above tool cap' USING ERRCODE = 'AE030';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_policy_within_cap BEFORE INSERT OR UPDATE ON ai.autonomy_policy
    FOR EACH ROW EXECUTE FUNCTION ai.policy_within_cap();

CREATE FUNCTION ai.tool_cap_covers_policies() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM ai.autonomy_policy WHERE tool_name = NEW.name AND level > NEW.max_autonomy_level) THEN
        RAISE EXCEPTION 'tool cap below existing policy' USING ERRCODE = 'AE030';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_tool_cap_covers_policies BEFORE UPDATE OF max_autonomy_level ON ai.tool
    FOR EACH ROW EXECUTE FUNCTION ai.tool_cap_covers_policies();

CREATE FUNCTION ai.financial_review_by_other() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.reviewed_by IS NOT NULL AND NEW.reviewed_by = NEW.initiated_by
       AND (SELECT financial FROM ai.tool WHERE name = NEW.tool_name) THEN
        RAISE EXCEPTION 'financial action must be reviewed by another person' USING ERRCODE = 'AE031';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_financial_review_by_other BEFORE INSERT OR UPDATE ON ai.action
    FOR EACH ROW EXECUTE FUNCTION ai.financial_review_by_other();
"""


def _now() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "tool",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("module", sa.Text(), nullable=False),
        sa.Column("operation_type", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.Text(), nullable=True),
        sa.Column("financial", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("max_autonomy_level", sa.SmallInteger(), nullable=False),
        sa.Column("approval_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("params_schema", postgresql.JSONB(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("name", name="pk_tool"),
        sa.CheckConstraint("operation_type IN ('READ', 'WRITE', 'EXECUTION')", name="ck_tool_operation_type"),
        sa.CheckConstraint("risk_level IS NULL OR risk_level IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_tool_risk_level"),
        sa.CheckConstraint(
            "max_autonomy_level BETWEEN 0 AND 3 AND (NOT financial OR max_autonomy_level <= 2)",
            name="ck_tool_autonomy_cap",
        ),
        schema="ai",
    )
    op.create_table(
        "autonomy_policy",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("role_code", sa.Text(), nullable=True),
        sa.Column("value_threshold", sa.Numeric(20, 2), nullable=True),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_autonomy_policy"),
        sa.ForeignKeyConstraint(["tool_name"], ["ai.tool.name"], name="fk_autonomy_policy_tool_name_tool"),
        sa.ForeignKeyConstraint(["role_code"], ["access.role.code"], name="fk_autonomy_policy_role_code_role"),
        sa.ForeignKeyConstraint(["updated_by"], [USER], name="fk_autonomy_policy_updated_by_user_account"),
        sa.CheckConstraint("level BETWEEN 0 AND 3", name="ck_autonomy_policy_level"),
        sa.CheckConstraint("version >= 1", name="ck_autonomy_policy_version"),
        schema="ai",
    )
    op.create_index(
        "uq_autonomy_policy_tool_role",
        "autonomy_policy",
        ["tool_name", "role_code"],
        unique=True,
        schema="ai",
        postgresql_nulls_not_distinct=True,  # một policy mặc định cho mỗi (tool, role|mọi role)
        postgresql_where=sa.text("value_threshold IS NULL"),
    )
    op.create_table(
        "kill_switch",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("changed_by", sa.Uuid(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_kill_switch"),
        sa.ForeignKeyConstraint(["changed_by"], [USER], name="fk_kill_switch_changed_by_user_account"),
        sa.CheckConstraint("id = 1", name="ck_kill_switch_singleton"),
        sa.CheckConstraint("reason <> ''", name="ck_kill_switch_reason"),
        schema="ai",
    )
    op.create_table(
        "setting",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("key", name="pk_setting"),
        sa.ForeignKeyConstraint(["updated_by"], [USER], name="fk_setting_updated_by_user_account"),
        schema="ai",
    )
    op.create_table(
        "action",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("initiated_by", sa.Uuid(), nullable=False),
        sa.Column("agent", sa.Text(), nullable=True),
        sa.Column("params", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("effective_level", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("blocked_by_kill_switch", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("source_job_id", sa.Uuid(), nullable=True),
        sa.Column("result_resource_type", sa.Text(), nullable=True),
        sa.Column("result_resource_id", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("undo_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_action"),
        sa.UniqueConstraint("initiated_by", "idempotency_key", name="uq_action_initiated_by"),
        sa.ForeignKeyConstraint(["tool_name"], ["ai.tool.name"], name="fk_action_tool_name_tool"),
        sa.ForeignKeyConstraint(["initiated_by"], [USER], name="fk_action_initiated_by_user_account"),
        sa.ForeignKeyConstraint(["reviewed_by"], [USER], name="fk_action_reviewed_by_user_account"),
        sa.ForeignKeyConstraint(["source_job_id"], ["jobs.job.id"], name="fk_action_source_job_id_job"),
        sa.CheckConstraint("effective_level BETWEEN 0 AND 3", name="ck_action_effective_level"),
        sa.CheckConstraint(
            "status IN ('PENDING_REVIEW', 'NEEDS_REVIEW_STALE', 'EXECUTED', 'REJECTED', 'UNDONE', 'FAILED')",
            name="ck_action_status",
        ),
        sa.CheckConstraint("idempotency_key <> ''", name="ck_action_idempotency_key"),
        sa.CheckConstraint(
            "effective_level <> 3 OR executed_at IS NULL OR undo_deadline >= executed_at + interval '24 hours'",
            name="ck_action_undo_window",
        ),
        sa.CheckConstraint("version >= 1", name="ck_action_version"),
        schema="ai",
    )
    op.create_index("ix_action_status_initiated_by", "action", ["status", "initiated_by"], schema="ai")
    op.create_index("ix_action_status_stale", "action", ["status", "stale_at"], schema="ai")
    op.create_table(
        "call_log",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("data_classification", sa.Text(), nullable=False),
        sa.Column("provider_is_local", sa.Boolean(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("pages", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_estimate", sa.Numeric(20, 6), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_call_log"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.job.id"], name="fk_call_log_job_id_job"),
        sa.CheckConstraint(
            "data_classification NOT IN ('SENSITIVE', 'PERSONAL') OR provider_is_local", name="ck_call_log_local_only"
        ),
        schema="ai",
    )
    op.create_index("ix_call_log_created", "call_log", ["created_at"], schema="ai")
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_feedback"),
        sa.ForeignKeyConstraint(["user_id"], [USER], name="fk_feedback_user_id_user_account"),
        sa.CheckConstraint("target_type IN ('ANSWER', 'EXTRACTION', 'SUGGESTION')", name="ck_feedback_target_type"),
        sa.CheckConstraint("verdict IN ('UP', 'DOWN')", name="ck_feedback_verdict"),
        schema="ai",
    )
    op.execute(TRIGGERS)
    tool = sa.table("tool", sa.column("name"), sa.column("module"), sa.column("operation_type"),
                    sa.column("max_autonomy_level"), schema="ai")  # fmt: skip
    op.bulk_insert(tool, [{"name": n, "module": m, "operation_type": o, "max_autonomy_level": 3} for n, m, o in TOOLS])
    defaults = [(n, 0) for n, _, o in TOOLS if o == "READ"] + [("create_task", 3)]
    for name, level in defaults:
        op.execute(
            sa.text(
                "INSERT INTO ai.autonomy_policy (id, tool_name, level, reason) "
                "VALUES (gen_random_uuid(), :n, :l, 'Mặc định SRS-AIC-03')"
            ).bindparams(n=name, l=level)
        )
    op.execute("INSERT INTO ai.kill_switch (id, enabled, reason) VALUES (1, false, 'Khởi tạo (migration 0013)')")
    op.execute("""INSERT INTO ai.setting (key, value) VALUES ('draft_expiry_days', '30'::jsonb)""")
    for table in ("work.task", "finance.transaction"):
        schema, name = table.split(".")
        op.create_foreign_key(
            f"fk_{name}_ai_action_id_action", name, "action", ["ai_action_id"], ["id"],
            source_schema=schema, referent_schema="ai",
        )  # fmt: skip


def downgrade() -> None:
    op.drop_constraint("fk_transaction_ai_action_id_action", "transaction", schema="finance", type_="foreignkey")
    op.drop_constraint("fk_task_ai_action_id_action", "task", schema="work", type_="foreignkey")
    for table in ("feedback", "call_log", "action", "setting", "kill_switch", "autonomy_policy", "tool"):
        op.drop_table(table, schema="ai")
    for function in ("financial_review_by_other", "tool_cap_covers_policies", "policy_within_cap"):
        op.execute(f"DROP FUNCTION IF EXISTS ai.{function}()")
