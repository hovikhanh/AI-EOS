"""Model `capture.*` (Database_Design §6). Chỉ dùng nội bộ module `capture`.

Bảng do migration 0014 tạo; model phải khớp schema (TC-MIG-01).
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "capture"}
_USER = "identity.user_account.id"
_DOC = "capture.source_document.id"
_TYPE = "capture.document_type.code"


class DocumentTypeRow(Base):
    __tablename__ = "document_type"
    __table_args__ = (
        CheckConstraint("phase IN ('MVP', 'PHASE2')", name="phase"),
        CheckConstraint("phase = 'MVP' OR NOT enabled", name="phase2_disabled"),
        CheckConstraint("name <> ''", name="name"),
        _SCHEMA,
    )

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    phase: Mapped[str] = mapped_column(Text)
    target_module: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    auto_commit_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class ExtractionSchemaRow(Base):
    __tablename__ = "extraction_schema"
    __table_args__ = (
        UniqueConstraint("document_type_code", "version"),
        CheckConstraint("status IN ('DRAFT', 'ACTIVE', 'RETIRED')", name="status"),
        CheckConstraint("version >= 1", name="version"),
        Index(
            "uq_extraction_schema_one_active",
            "document_type_code",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_type_code: Mapped[str] = mapped_column(Text, ForeignKey(_TYPE))
    version: Mapped[int] = mapped_column(Integer)
    fields: Mapped[Any] = mapped_column(JSONB)
    display_thresholds: Mapped[Any | None] = mapped_column(JSONB)
    routing_thresholds: Mapped[Any | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, server_default=text("'DRAFT'"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SourceDocumentRow(Base):
    __tablename__ = "source_document"
    __table_args__ = (
        UniqueConstraint("storage_key"),
        CheckConstraint("channel IN ('C1', 'C2', 'C3', 'C4', 'C5')", name="channel"),
        CheckConstraint("scan_status IN ('PENDING', 'CLEAN', 'INFECTED', 'ERROR')", name="scan_status"),
        CheckConstraint(
            "status IN ('UPLOADED', 'PROCESSING', 'FAILED', 'EXTRACTED', 'NEEDS_REVIEW', 'APPROVED', 'REJECTED', "
            "'COMMITTED', 'SUPERSEDED')",
            name="status",
        ),
        CheckConstraint("sensitivity IN ('NORMAL', 'PERSONAL', 'SENSITIVE')", name="sensitivity"),
        CheckConstraint("octet_length(sha256) = 32", name="sha256"),
        CheckConstraint("size_bytes >= 0 AND (page_count IS NULL OR page_count >= 0)", name="size"),
        CheckConstraint(
            "classification_confidence IS NULL OR classification_confidence BETWEEN 0 AND 1", name="confidence"
        ),
        CheckConstraint("superseded_by IS NULL OR superseded_by <> id", name="not_self"),
        CheckConstraint("storage_key <> ''", name="storage_key"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_source_document_status_type", "status", "document_type_code"),
        Index("ix_source_document_sha256", "sha256"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    channel: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str] = mapped_column(Text)
    sha256: Mapped[bytes] = mapped_column(BYTEA)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    page_count: Mapped[int | None] = mapped_column(Integer)
    declared_mime: Mapped[str | None] = mapped_column(Text)
    detected_mime: Mapped[str | None] = mapped_column(Text)
    scan_status: Mapped[str] = mapped_column(Text, server_default=text("'PENDING'"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'UPLOADED'"))
    document_type_code: Mapped[str | None] = mapped_column(Text, ForeignKey(_TYPE))
    classification_confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    sensitivity: Mapped[str] = mapped_column(Text, server_default=text("'NORMAL'"))
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_DOC))
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DocumentPageRow(Base):
    __tablename__ = "document_page"
    __table_args__ = (CheckConstraint("page_no >= 1", name="page_no"), _SCHEMA)

    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_DOC), primary_key=True)
    page_no: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    image_storage_key: Mapped[str | None] = mapped_column(Text)
    text_layer: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class ExtractionRow(Base):
    __tablename__ = "extraction"
    __table_args__ = (
        CheckConstraint("status <> ''", name="status"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_extraction_document", "document_id"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_DOC))
    schema_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("capture.extraction_schema.id"))
    status: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class ExtractedFieldRow(Base):
    __tablename__ = "extracted_field"
    __table_args__ = (
        UniqueConstraint("extraction_id", "field_key"),
        CheckConstraint("confidence IS NULL OR confidence BETWEEN 0 AND 1", name="confidence"),
        CheckConstraint("field_key <> ''", name="field_key"),
        CheckConstraint("page_no IS NULL OR page_no >= 1", name="page_no"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    extraction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("capture.extraction.id"))
    field_key: Mapped[str] = mapped_column(Text)
    value: Mapped[Any | None] = mapped_column(JSONB)
    normalized_value: Mapped[Any | None] = mapped_column(JSONB)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    page_no: Mapped[int | None] = mapped_column(Integer)
    bbox: Mapped[Any | None] = mapped_column(JSONB)
    source_text: Mapped[str | None] = mapped_column(Text)
    uncertainty_reason: Mapped[str | None] = mapped_column(Text)  # SRS-CAP-13 "lý do không chắc"
    critical: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    reviewed_value: Mapped[Any | None] = mapped_column(JSONB)
    corrected: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class ExtractionReviewRow(Base):
    __tablename__ = "extraction_review"
    __table_args__ = (
        CheckConstraint(
            "decision IS NULL OR decision IN ('APPROVE', 'REJECT', 'REASSIGN', 'CHANGE_TYPE', 'SPLIT', 'MERGE')",
            name="decision",
        ),
        CheckConstraint(
            "decision IS DISTINCT FROM 'REJECT' OR (reason IS NOT NULL AND reason <> '')", name="reject_reason"
        ),
        CheckConstraint("(decision IS NULL) = (finished_at IS NULL)", name="finished"),
        CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="duration"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    extraction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("capture.extraction.id"))
    reviewer_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    decision: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewQueueRow(Base):
    __tablename__ = "review_queue"
    __table_args__ = (
        CheckConstraint("name <> ''", name="name"),
        CheckConstraint("sla_hours IS NULL OR sla_hours > 0", name="sla_hours"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    document_type_code: Mapped[str | None] = mapped_column(Text, ForeignKey(_TYPE))
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    sla_hours: Mapped[int | None] = mapped_column(Integer)


class ImportBatchRow(Base):
    __tablename__ = "import_batch"
    __table_args__ = (
        CheckConstraint("status IN ('PREVIEW', 'COMMITTED', 'PARTIAL', 'FAILED')", name="status"),
        CheckConstraint(
            "rows_committed >= 0 AND rows_committed <= rows_valid AND rows_valid >= 0 AND rows_valid <= rows_total",
            name="counts",
        ),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    source_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_DOC))
    target: Mapped[str] = mapped_column(Text)
    column_mapping: Mapped[Any | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, server_default=text("'PREVIEW'"))
    rows_total: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rows_valid: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    rows_committed: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_USER))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImportRowErrorRow(Base):
    __tablename__ = "import_row_error"
    __table_args__ = (
        CheckConstraint("row_no >= 1", name="row_no"),
        Index("ix_import_row_error_batch", "batch_id", "row_no"),
        _SCHEMA,
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    batch_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("capture.import_batch.id"))
    row_no: Mapped[int] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)


class DataLineageRow(Base):
    __tablename__ = "data_lineage"
    __table_args__ = (Index("ix_data_lineage_target", "target_type", "target_id"), _SCHEMA)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    target_type: Mapped[str] = mapped_column(Text)
    target_id: Mapped[str] = mapped_column(Text)
    target_field: Mapped[str | None] = mapped_column(Text)
    source_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey(_DOC))
    page_no: Mapped[int | None] = mapped_column(Integer)
    extraction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("capture.extraction.id"))
    extracted_field_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("capture.extracted_field.id"))
    committed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey(_USER))
    ai_action_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai.action.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
