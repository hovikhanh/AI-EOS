"""M-07 capture: tài liệu nguồn, trang, trích xuất, review, hàng chờ, import, lineage.

Revision: 0014 (sau 0013)
Yêu cầu/ADR liên quan: T-202, SRS-CAP-13, SRS-REV-07, SRS-REV-09, SEC-DC-01, FR-DF-04, D-17, BR-05;
Database_Design §6 (`capture.*`).

- `document_type`: `phase` `MVP`/`PHASE2`; loại Phase 2 không bật được trong MVP (CHECK `phase = 'MVP' OR NOT enabled`,
  D-17); `auto_commit_enabled` mặc định false (BR-05). Không seed — danh mục và schema chờ 2B / T-207.
- `extraction_schema`: UNIQUE `(document_type_code, version)`; một `ACTIVE` mỗi loại (UNIQUE có điều kiện);
  `display_thresholds`, `routing_thresholds` tách riêng (D-29).
- `source_document`: CHECK `channel` C1…C5, `scan_status`, `status`, `sensitivity`; `storage_key` UNIQUE; `sha256`
  32 byte, index không unique (trùng chỉ cảnh báo — FR-DC-08); `classification_confidence` 0..1; kích thước/trang
  ≥ 0 (giới hạn thật là cấu hình, kiểm ở T-203).
- `extracted_field`: `confidence` 0..1 (SRS-CAP-13); `reviewed_value`, `corrected` (SRS-REV-07).
- `extraction_review`: `decision` CHECK; lý do bắt buộc khi `REJECT`; `started_at`/`finished_at` (SRS-REV-09).
- `import_batch.status` `PREVIEW`/`COMMITTED`/`PARTIAL`/`FAILED`; `import_row_error` chỉ lỗi (không sao chép dữ liệu).
- `extraction.status`: tài liệu chưa liệt kê giá trị → không CHECK (T-206).
- Khóa ngoại `source_document_id` của `org.org_unit`, `org.employee`, `work.task`, `finance.transaction` →
  `capture.source_document` (các bảng đó để dành cho T-202).
- Quyền: giữ quyền mặc định của 0001.
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USER = "identity.user_account.id"
DOC = "capture.source_document.id"
JSONB = postgresql.JSONB


def _now() -> sa.TextClause:
    return sa.text("now()")


def _id() -> sa.Column[Any]:
    return sa.Column("id", sa.Uuid(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "document_type",
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("phase", sa.Text(), nullable=False),
        sa.Column("target_module", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("auto_commit_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("code", name="pk_document_type"),
        sa.CheckConstraint("phase IN ('MVP', 'PHASE2')", name="ck_document_type_phase"),
        sa.CheckConstraint("phase = 'MVP' OR NOT enabled", name="ck_document_type_phase2_disabled"),
        sa.CheckConstraint("name <> ''", name="ck_document_type_name"),
        schema="capture",
    )
    op.create_table(
        "extraction_schema",
        _id(),
        sa.Column("document_type_code", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("fields", JSONB(), nullable=False),
        sa.Column("display_thresholds", JSONB(), nullable=True),
        sa.Column("routing_thresholds", JSONB(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'DRAFT'"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_schema"),
        sa.UniqueConstraint("document_type_code", "version", name="uq_extraction_schema_document_type_code"),
        sa.ForeignKeyConstraint(
            ["document_type_code"],
            ["capture.document_type.code"],
            name="fk_extraction_schema_document_type_code_document_type",
        ),  # fmt: skip
        sa.ForeignKeyConstraint(["created_by"], [USER], name="fk_extraction_schema_created_by_user_account"),
        sa.CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'RETIRED')", name="ck_extraction_schema_status"),
        sa.CheckConstraint("version >= 1", name="ck_extraction_schema_version"),
        schema="capture",
    )
    op.create_index(
        "uq_extraction_schema_one_active", "extraction_schema", ["document_type_code"], unique=True,
        schema="capture", postgresql_where=sa.text("status = 'ACTIVE'"),
    )  # fmt: skip
    op.create_table(
        "source_document",
        _id(),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("sha256", postgresql.BYTEA(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("declared_mime", sa.Text(), nullable=True),
        sa.Column("detected_mime", sa.Text(), nullable=True),
        sa.Column("scan_status", sa.Text(), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'UPLOADED'"), nullable=False),
        sa.Column("document_type_code", sa.Text(), nullable=True),
        sa.Column("classification_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("sensitivity", sa.Text(), server_default=sa.text("'NORMAL'"), nullable=False),
        sa.Column("superseded_by", sa.Uuid(), nullable=True),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_source_document"),
        sa.UniqueConstraint("storage_key", name="uq_source_document_storage_key"),
        sa.ForeignKeyConstraint(["uploaded_by"], [USER], name="fk_source_document_uploaded_by_user_account"),
        sa.ForeignKeyConstraint(
            ["document_type_code"],
            ["capture.document_type.code"],
            name="fk_source_document_document_type_code_document_type",
        ),  # fmt: skip
        sa.ForeignKeyConstraint(["superseded_by"], [DOC], name="fk_source_document_superseded_by_source_document"),
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_source_document_org_unit_id_org_unit"),
        sa.CheckConstraint("channel IN ('C1', 'C2', 'C3', 'C4', 'C5')", name="ck_source_document_channel"),
        sa.CheckConstraint(
            "scan_status IN ('PENDING', 'CLEAN', 'INFECTED', 'ERROR')", name="ck_source_document_scan_status"
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'FAILED', 'EXTRACTED', 'NEEDS_REVIEW', 'APPROVED', 'REJECTED', "
            "'COMMITTED', 'SUPERSEDED')",
            name="ck_source_document_status",
        ),
        sa.CheckConstraint("sensitivity IN ('NORMAL', 'PERSONAL', 'SENSITIVE')", name="ck_source_document_sensitivity"),
        sa.CheckConstraint("octet_length(sha256) = 32", name="ck_source_document_sha256"),
        sa.CheckConstraint(
            "size_bytes >= 0 AND (page_count IS NULL OR page_count >= 0)", name="ck_source_document_size"
        ),
        sa.CheckConstraint(
            "classification_confidence IS NULL OR classification_confidence BETWEEN 0 AND 1",
            name="ck_source_document_confidence",
        ),
        sa.CheckConstraint("superseded_by IS NULL OR superseded_by <> id", name="ck_source_document_not_self"),
        sa.CheckConstraint("storage_key <> ''", name="ck_source_document_storage_key"),
        sa.CheckConstraint("version >= 1", name="ck_source_document_version"),
        schema="capture",
    )
    op.create_index(
        "ix_source_document_status_type", "source_document", ["status", "document_type_code"], schema="capture"
    )
    op.create_index("ix_source_document_sha256", "source_document", ["sha256"], schema="capture")
    op.create_table(
        "document_page",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=False),
        sa.Column("image_storage_key", sa.Text(), nullable=True),
        sa.Column("text_layer", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("document_id", "page_no", name="pk_document_page"),
        sa.ForeignKeyConstraint(["document_id"], [DOC], name="fk_document_page_document_id_source_document"),
        sa.CheckConstraint("page_no >= 1", name="ck_document_page_page_no"),
        schema="capture",
    )
    op.create_table(
        "extraction",
        _id(),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("schema_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_extraction"),
        sa.ForeignKeyConstraint(["document_id"], [DOC], name="fk_extraction_document_id_source_document"),
        sa.ForeignKeyConstraint(
            ["schema_id"], ["capture.extraction_schema.id"], name="fk_extraction_schema_id_extraction_schema"
        ),
        sa.CheckConstraint("status <> ''", name="ck_extraction_status"),
        sa.CheckConstraint("version >= 1", name="ck_extraction_version"),
        schema="capture",
    )
    op.create_index("ix_extraction_document", "extraction", ["document_id"], schema="capture")
    op.create_table(
        "extracted_field",
        _id(),
        sa.Column("extraction_id", sa.Uuid(), nullable=False),
        sa.Column("field_key", sa.Text(), nullable=False),
        sa.Column("value", JSONB(), nullable=True),
        sa.Column("normalized_value", JSONB(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("bbox", JSONB(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("uncertainty_reason", sa.Text(), nullable=True),
        sa.Column("critical", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("reviewed_value", JSONB(), nullable=True),
        sa.Column("corrected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_extracted_field"),
        sa.UniqueConstraint("extraction_id", "field_key", name="uq_extracted_field_extraction_id"),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["capture.extraction.id"], name="fk_extracted_field_extraction_id_extraction"
        ),
        sa.CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="ck_extracted_field_confidence"),
        sa.CheckConstraint("field_key <> ''", name="ck_extracted_field_field_key"),
        sa.CheckConstraint("page_no IS NULL OR page_no >= 1", name="ck_extracted_field_page_no"),
        schema="capture",
    )
    op.create_table(
        "extraction_review",
        _id(),
        sa.Column("extraction_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_extraction_review"),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["capture.extraction.id"], name="fk_extraction_review_extraction_id_extraction"
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], [USER], name="fk_extraction_review_reviewer_id_user_account"),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('APPROVE', 'REJECT', 'REASSIGN', 'CHANGE_TYPE', 'SPLIT', 'MERGE')",
            name="ck_extraction_review_decision",
        ),
        sa.CheckConstraint(
            "decision IS DISTINCT FROM 'REJECT' OR (reason IS NOT NULL AND reason <> '')",
            name="ck_extraction_review_reject_reason",
        ),
        sa.CheckConstraint("(decision IS NULL) = (finished_at IS NULL)", name="ck_extraction_review_finished"),
        sa.CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="ck_extraction_review_duration"),
        schema="capture",
    )
    op.create_table(
        "review_queue",
        _id(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("document_type_code", sa.Text(), nullable=True),
        sa.Column("org_unit_id", sa.Uuid(), nullable=True),
        sa.Column("sla_hours", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_review_queue"),
        sa.ForeignKeyConstraint(
            ["document_type_code"],
            ["capture.document_type.code"],
            name="fk_review_queue_document_type_code_document_type",
        ),  # fmt: skip
        sa.ForeignKeyConstraint(["org_unit_id"], ["org.org_unit.id"], name="fk_review_queue_org_unit_id_org_unit"),
        sa.CheckConstraint("name <> ''", name="ck_review_queue_name"),
        sa.CheckConstraint("sla_hours IS NULL OR sla_hours > 0", name="ck_review_queue_sla_hours"),
        schema="capture",
    )
    op.create_table(
        "import_batch",
        _id(),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("target", sa.Text(), nullable=False),
        sa.Column("column_mapping", JSONB(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'PREVIEW'"), nullable=False),
        sa.Column("rows_total", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_valid", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("rows_committed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_import_batch"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], [DOC], name="fk_import_batch_source_document_id_source_document"
        ),
        sa.ForeignKeyConstraint(["created_by"], [USER], name="fk_import_batch_created_by_user_account"),
        sa.CheckConstraint("status IN ('PREVIEW', 'COMMITTED', 'PARTIAL', 'FAILED')", name="ck_import_batch_status"),
        sa.CheckConstraint(
            "rows_committed >= 0 AND rows_committed <= rows_valid AND rows_valid >= 0 AND rows_valid <= rows_total",
            name="ck_import_batch_counts",
        ),
        schema="capture",
    )
    op.create_table(
        "import_row_error",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False),
        sa.Column("field", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_import_row_error"),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["capture.import_batch.id"], name="fk_import_row_error_batch_id_import_batch"
        ),
        sa.CheckConstraint("row_no >= 1", name="ck_import_row_error_row_no"),
        schema="capture",
    )
    op.create_index("ix_import_row_error_batch", "import_row_error", ["batch_id", "row_no"], schema="capture")
    op.create_table(
        "data_lineage",
        _id(),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("target_field", sa.Text(), nullable=True),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("page_no", sa.Integer(), nullable=True),
        sa.Column("extraction_id", sa.Uuid(), nullable=True),
        sa.Column("extracted_field_id", sa.Uuid(), nullable=True),
        sa.Column("committed_by", sa.Uuid(), nullable=True),
        sa.Column("ai_action_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_data_lineage"),
        sa.ForeignKeyConstraint(
            ["source_document_id"], [DOC], name="fk_data_lineage_source_document_id_source_document"
        ),
        sa.ForeignKeyConstraint(
            ["extraction_id"], ["capture.extraction.id"], name="fk_data_lineage_extraction_id_extraction"
        ),
        sa.ForeignKeyConstraint(
            ["extracted_field_id"],
            ["capture.extracted_field.id"],
            name="fk_data_lineage_extracted_field_id_extracted_field",
        ),  # fmt: skip
        sa.ForeignKeyConstraint(["committed_by"], [USER], name="fk_data_lineage_committed_by_user_account"),
        sa.ForeignKeyConstraint(["ai_action_id"], ["ai.action.id"], name="fk_data_lineage_ai_action_id_action"),
        schema="capture",
    )
    op.create_index("ix_data_lineage_target", "data_lineage", ["target_type", "target_id"], schema="capture")
    for schema, table in (("org", "org_unit"), ("org", "employee"), ("work", "task"), ("finance", "transaction")):
        op.create_foreign_key(
            f"fk_{table}_source_document_id_source_document", table, "source_document", ["source_document_id"],
            ["id"], source_schema=schema, referent_schema="capture",
        )  # fmt: skip


def downgrade() -> None:
    for schema, table in (("org", "org_unit"), ("org", "employee"), ("work", "task"), ("finance", "transaction")):
        op.drop_constraint(f"fk_{table}_source_document_id_source_document", table, schema=schema, type_="foreignkey")
    for table in (
        "data_lineage", "import_row_error", "import_batch", "review_queue", "extraction_review", "extracted_field",
        "extraction", "document_page", "source_document", "extraction_schema", "document_type",
    ):  # fmt: skip
        op.drop_table(table, schema="capture")
