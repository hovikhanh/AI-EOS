"""M-09 finance: `reporting_period`, `transaction`, `transaction_event`, `approval_delegation` + INV-01…07.

Revision: 0012 (sau 0011)
Yêu cầu/ADR liên quan: T-401, SRS-FIN-13, SRS-FIN-17, ADR-009 (+Amendment 1), D-13, D-14, D-37; Database_Design §7,
§8 (INV-01…07); Architecture §7.1.

- `reporting_period`: `start_date <= end_date`; không chồng lấn (`EXCLUDE USING gist` trên `daterange(start, end, '[]')`
  — kiểu range có sẵn opclass gist, không cần extension); `status` `OPEN`/`CLOSED`; `CLOSED → OPEN` bị trigger chặn
  (`AE020`).
- `transaction`: CHECK theo Database_Design §7 (`record_type`, `kind`, `status`, `hold_reason` ⇔ `ON_HOLD`,
  `reverses_id` ⇔ `REVERSAL`, `adjusts_id` ⇔ `ADJUSTMENT`, `reason` khi không phải `ORIGINAL`, `reject_reason` khi
  `REJECTED`, `currency` 3 chữ in hoa, `request_hash` 32 byte); `amount numeric(20,2)` (không float).
- INV-01: CHECK người duyệt/từ chối khác người tạo và người gửi.
- INV-02: UNIQUE `(reverses_id)` với bút toán đảo `DRAFT`/`PENDING_APPROVAL`/`POSTED`.
- INV-03: trigger — `reverses_id` phải trỏ tới giao dịch không phải `REVERSAL` và đang `POSTED` (`AE021`).
- INV-04: trigger — `POSTED`/`REVERSED`: không đổi nội dung; chỉ `POSTED → REVERSED` (`AE022`).
- INV-05: không cấp DELETE cho `aieos_app`; trigger chặn DELETE kể cả role khác (`AE023`). TRUNCATE (dọn test bằng
  owner) không kích hoạt trigger theo dòng.
- INV-06: trigger cặp chuyển trạng thái theo ADR-009 (`AE024`): DRAFT→PENDING_APPROVAL|CANCELLED;
  PENDING_APPROVAL→CANCELLED|REJECTED|POSTED|ON_HOLD; ON_HOLD→CANCELLED|REJECTED; POSTED→REVERSED. Không có
  ON_HOLD→POSTED. Bản ghi mới phải ở `DRAFT`.
- INV-07: trigger khi vào `PENDING_APPROVAL`/`POSTED`: có `period_id`, kỳ `OPEN`, `transaction_date` trong kỳ (`AE025`).
- `transaction_event`: append-only — `aieos_app` chỉ SELECT, INSERT; trigger chặn UPDATE/DELETE (`AE023`).
- `approval_delegation`: dự trữ (F6), không seed, logic MVP không đọc.
- `org_unit_id` → `org.org_unit`; `source_document_id`, `ai_action_id`: khóa ngoại ở T-202, T-302.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER = "identity.user_account.id"

TRIGGERS = """
CREATE FUNCTION finance.period_no_reopen() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'CLOSED' AND NEW.status = 'OPEN' THEN
        RAISE EXCEPTION 'reporting period cannot be reopened' USING ERRCODE = 'AE020';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_period_no_reopen BEFORE UPDATE OF status ON finance.reporting_period
    FOR EACH ROW EXECUTE FUNCTION finance.period_no_reopen();

CREATE FUNCTION finance.transaction_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    target record;
    period record;
    allowed boolean;
BEGIN
    -- INV-06: bản ghi mới ở DRAFT; cặp chuyển trạng thái theo ADR-009.
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'DRAFT' THEN
            RAISE EXCEPTION 'new transaction must be DRAFT' USING ERRCODE = 'AE024';
        END IF;
    ELSE
        -- INV-04: giao dịch đã ghi sổ bất biến; chỉ POSTED → REVERSED.
        IF OLD.status IN ('POSTED', 'REVERSED') THEN
            IF (to_jsonb(NEW) - 'status' - 'version' - 'updated_at')
                IS DISTINCT FROM (to_jsonb(OLD) - 'status' - 'version' - 'updated_at')
               OR NOT (NEW.status = OLD.status OR (OLD.status = 'POSTED' AND NEW.status = 'REVERSED')) THEN
                RAISE EXCEPTION 'posted transaction is immutable' USING ERRCODE = 'AE022';
            END IF;
        END IF;
        IF NEW.status <> OLD.status THEN
            allowed := (OLD.status, NEW.status) IN (
                ('DRAFT', 'PENDING_APPROVAL'), ('DRAFT', 'CANCELLED'),
                ('PENDING_APPROVAL', 'CANCELLED'), ('PENDING_APPROVAL', 'REJECTED'),
                ('PENDING_APPROVAL', 'POSTED'), ('PENDING_APPROVAL', 'ON_HOLD'),
                ('ON_HOLD', 'CANCELLED'), ('ON_HOLD', 'REJECTED'),
                ('POSTED', 'REVERSED'));
            IF NOT allowed THEN
                RAISE EXCEPTION 'invalid status transition % -> %', OLD.status, NEW.status USING ERRCODE = 'AE024';
            END IF;
        END IF;
    END IF;
    -- INV-03: chỉ đảo giao dịch không phải bút toán đảo và đang POSTED.
    IF NEW.reverses_id IS NOT NULL AND (TG_OP = 'INSERT' OR NEW.reverses_id IS DISTINCT FROM OLD.reverses_id) THEN
        SELECT kind, status INTO target FROM finance.transaction WHERE id = NEW.reverses_id;
        IF target.kind = 'REVERSAL' OR target.status IS DISTINCT FROM 'POSTED' THEN
            RAISE EXCEPTION 'can only reverse a posted non-reversal transaction' USING ERRCODE = 'AE021';
        END IF;
    END IF;
    -- INV-07: gửi duyệt và ghi sổ chỉ vào kỳ OPEN chứa ngày giao dịch.
    IF NEW.status IN ('PENDING_APPROVAL', 'POSTED') AND (TG_OP = 'INSERT' OR NEW.status <> OLD.status) THEN
        SELECT status, start_date, end_date INTO period FROM finance.reporting_period WHERE id = NEW.period_id;
        IF period.status IS DISTINCT FROM 'OPEN'
           OR NEW.transaction_date NOT BETWEEN period.start_date AND period.end_date THEN
            RAISE EXCEPTION 'reporting period is not open for this transaction' USING ERRCODE = 'AE025';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_transaction_guard BEFORE INSERT OR UPDATE ON finance.transaction
    FOR EACH ROW EXECUTE FUNCTION finance.transaction_guard();

CREATE FUNCTION finance.no_delete() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% is append-only/undeletable', TG_TABLE_NAME USING ERRCODE = 'AE023';
END $$;
CREATE TRIGGER trg_transaction_no_delete BEFORE DELETE ON finance.transaction
    FOR EACH ROW EXECUTE FUNCTION finance.no_delete();
CREATE TRIGGER trg_transaction_event_append_only BEFORE UPDATE OR DELETE ON finance.transaction_event
    FOR EACH ROW EXECUTE FUNCTION finance.no_delete();
"""


def _now() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "reporting_period",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'OPEN'"), nullable=False),
        sa.Column("opened_by", sa.Uuid(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("closed_by", sa.Uuid(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_reporting_period"),
        sa.UniqueConstraint("code", name="uq_reporting_period_code"),
        sa.ForeignKeyConstraint(["opened_by"], [USER], name="fk_reporting_period_opened_by_user_account"),
        sa.ForeignKeyConstraint(["closed_by"], [USER], name="fk_reporting_period_closed_by_user_account"),
        sa.CheckConstraint("code <> ''", name="ck_reporting_period_code"),
        sa.CheckConstraint("start_date <= end_date", name="ck_reporting_period_dates"),
        sa.CheckConstraint("status IN ('OPEN', 'CLOSED')", name="ck_reporting_period_status"),
        sa.CheckConstraint(
            "(status = 'CLOSED') = (closed_at IS NOT NULL AND closed_by IS NOT NULL)", name="ck_reporting_period_closed"
        ),
        sa.CheckConstraint("version >= 1", name="ck_reporting_period_version"),
        postgresql.ExcludeConstraint(
            (sa.text("daterange(start_date, end_date, '[]')"), "&&"),
            using="gist",
            name="ex_reporting_period_no_overlap",
        ),
        schema="finance",
    )
    op.create_table(
        "transaction",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("record_type", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), server_default=sa.text("'ORIGINAL'"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("period_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("counterparty", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.Column("adjusts_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by", sa.Uuid(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("no_eligible_approver", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_assisted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_action_id", sa.Uuid(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("request_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_transaction"),
        sa.UniqueConstraint("created_by", "idempotency_key", name="uq_transaction_created_by"),
        sa.ForeignKeyConstraint(
            ["period_id"], ["finance.reporting_period.id"], name="fk_transaction_period_id_reporting_period"
        ),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_transaction_org_unit_id_org_unit"),
        sa.ForeignKeyConstraint(
            ["reverses_id"], ["finance.transaction.id"], name="fk_transaction_reverses_id_transaction"
        ),
        sa.ForeignKeyConstraint(
            ["adjusts_id"], ["finance.transaction.id"], name="fk_transaction_adjusts_id_transaction"
        ),
        sa.ForeignKeyConstraint(["created_by"], [USER], name="fk_transaction_created_by_user_account"),
        sa.ForeignKeyConstraint(["submitted_by"], [USER], name="fk_transaction_submitted_by_user_account"),
        sa.ForeignKeyConstraint(["approved_by"], [USER], name="fk_transaction_approved_by_user_account"),
        sa.ForeignKeyConstraint(["rejected_by"], [USER], name="fk_transaction_rejected_by_user_account"),
        sa.ForeignKeyConstraint(["cancelled_by"], [USER], name="fk_transaction_cancelled_by_user_account"),
        sa.CheckConstraint("record_type IN ('REVENUE', 'EXPENSE', 'CASH_BALANCE')", name="ck_transaction_record_type"),
        sa.CheckConstraint("kind IN ('ORIGINAL', 'REVERSAL', 'ADJUSTMENT')", name="ck_transaction_kind"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PENDING_APPROVAL', 'ON_HOLD', 'POSTED', 'REVERSED', 'REJECTED', 'CANCELLED')",
            name="ck_transaction_status",
        ),
        sa.CheckConstraint("(status = 'ON_HOLD') = (hold_reason IS NOT NULL)", name="ck_transaction_hold_reason"),
        sa.CheckConstraint("hold_reason IS NULL OR hold_reason = 'PERIOD_CLOSED'", name="ck_transaction_hold_value"),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="ck_transaction_currency"),
        sa.CheckConstraint("(kind = 'REVERSAL') = (reverses_id IS NOT NULL)", name="ck_transaction_reversal_link"),
        sa.CheckConstraint("(kind = 'ADJUSTMENT') = (adjusts_id IS NOT NULL)", name="ck_transaction_adjustment_link"),
        sa.CheckConstraint("kind = 'ORIGINAL' OR (reason IS NOT NULL AND reason <> '')", name="ck_transaction_reason"),
        sa.CheckConstraint(
            "approved_by IS NULL OR (approved_by <> created_by AND approved_by IS DISTINCT FROM submitted_by)",
            name="ck_transaction_approver_not_creator",
        ),
        sa.CheckConstraint(
            "rejected_by IS NULL OR (rejected_by <> created_by AND rejected_by IS DISTINCT FROM submitted_by)",
            name="ck_transaction_rejecter_not_creator",
        ),
        sa.CheckConstraint(
            "status <> 'REJECTED' OR (reject_reason IS NOT NULL AND reject_reason <> '')",
            name="ck_transaction_reject_reason",
        ),
        sa.CheckConstraint("octet_length(request_hash) = 32", name="ck_transaction_request_hash"),
        sa.CheckConstraint("idempotency_key <> ''", name="ck_transaction_idempotency_key"),
        sa.CheckConstraint("version >= 1", name="ck_transaction_version"),
        schema="finance",
    )
    op.create_index(
        "uq_transaction_one_reversal",
        "transaction",
        ["reverses_id"],
        unique=True,
        schema="finance",
        postgresql_where=sa.text("kind = 'REVERSAL' AND status IN ('DRAFT', 'PENDING_APPROVAL', 'POSTED')"),
    )
    op.create_index("ix_transaction_status_period", "transaction", ["status", "period_id"], schema="finance")
    op.create_index("ix_transaction_created_by_status", "transaction", ["created_by", "status"], schema="finance")
    op.create_table(
        "transaction_event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("transaction_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=True),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_transaction_event"),
        sa.ForeignKeyConstraint(
            ["transaction_id"], ["finance.transaction.id"], name="fk_transaction_event_transaction_id_transaction"
        ),
        sa.ForeignKeyConstraint(["actor_id"], [USER], name="fk_transaction_event_actor_id_user_account"),
        schema="finance",
    )
    op.create_index(
        "ix_transaction_event_transaction", "transaction_event", ["transaction_id", "occurred_at"], schema="finance"
    )
    op.create_table(
        "approval_delegation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("delegate_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.Text(), nullable=False),
        sa.Column("scope_id", sa.Text(), nullable=True),
        sa.Column("amount_limit", sa.Numeric(20, 2), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("granted_by", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_approval_delegation"),
        sa.ForeignKeyConstraint(
            ["delegate_user_id"], [USER], name="fk_approval_delegation_delegate_user_id_user_account"
        ),
        sa.ForeignKeyConstraint(["granted_by"], [USER], name="fk_approval_delegation_granted_by_user_account"),
        sa.CheckConstraint("granted_by <> delegate_user_id", name="ck_approval_delegation_not_self"),
        schema="finance",
    )
    op.execute(TRIGGERS)
    op.execute("REVOKE UPDATE ON finance.transaction_event FROM aieos_app")


def downgrade() -> None:
    for table in ("approval_delegation", "transaction_event", "transaction", "reporting_period"):
        op.drop_table(table, schema="finance")
    for function in ("no_delete", "transaction_guard", "period_no_reopen"):
        op.execute(f"DROP FUNCTION IF EXISTS finance.{function}()")
