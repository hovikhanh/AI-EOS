"""T-202: bảng `capture.*` (SRS-CAP-13, SRS-REV-07, SRS-REV-09; Database_Design §6). T-202 không làm chủ TC nào.

Thao tác bằng role ứng dụng `aieos_app`.
"""

import hashlib
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.identity.api import hash_password
from tests.conftest import ProvisionedDatabase, migrate_to_head


@pytest.fixture
def app(database: ProvisionedDatabase) -> Iterator[Engine]:
    migrate_to_head(database)
    engine = database.engine("aieos_app")
    yield engine
    engine.dispose()


def run(engine: Engine, sql: str, params: dict[str, Any] | None = None) -> Any:
    with engine.begin() as conn:
        return conn.execute(text(sql), params or {})


def sqlstate(engine: Engine, sql: str, params: dict[str, Any] | None = None) -> str | None:
    with pytest.raises(DBAPIError) as info:
        run(engine, sql, params)
    return getattr(info.value.orig, "sqlstate", None)


def setup(engine: Engine) -> dict[str, Any]:
    user = uuid.uuid4()
    run(
        engine,
        "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
        "VALUES (:i, 'a@example.com', 'A', 'ACTIVE', :p)",
        {"i": user, "p": hash_password("Mat-khau-dung-123!")},
    )
    run(
        engine,
        "INSERT INTO capture.document_type (code, name, phase, enabled) "
        "VALUES ('MEETING_MINUTES', 'Biên bản họp', 'MVP', true)",
    )
    schema = uuid.uuid4()
    run(
        engine,
        "INSERT INTO capture.extraction_schema (id, document_type_code, version, fields, status) "
        "VALUES (:i, 'MEETING_MINUTES', 1, '[]', 'ACTIVE')",
        {"i": schema},
    )
    doc = uuid.uuid4()
    run(
        engine,
        "INSERT INTO capture.source_document (id, uploaded_by, channel, storage_key, sha256, size_bytes) "
        "VALUES (:i, :u, 'C2', :k, :h, 1024)",
        {"i": doc, "u": user, "k": str(uuid.uuid4()), "h": hashlib.sha256(b"x").digest()},
    )
    extraction = uuid.uuid4()
    run(
        engine,
        "INSERT INTO capture.extraction (id, document_id, schema_id, status) VALUES (:i, :d, :s, 'EXTRACTED')",
        {"i": extraction, "d": doc, "s": schema},
    )
    return {"user": user, "doc": doc, "schema": schema, "extraction": extraction}


@pytest.mark.db
def test_document_type_and_schema_rules(app: Engine) -> None:
    ids = setup(app)
    phase2 = (
        "INSERT INTO capture.document_type (code, name, phase, enabled) VALUES ('INVOICE', 'Hóa đơn', 'PHASE2', :e)"
    )
    assert sqlstate(app, phase2, {"e": True}) == "23514"  # D-17: Phase 2 không bật trong MVP
    run(app, phase2, {"e": False})
    second_active = (
        "INSERT INTO capture.extraction_schema (id, document_type_code, version, fields, status) "
        "VALUES (gen_random_uuid(), 'MEETING_MINUTES', :v, '[]', :s)"
    )
    assert sqlstate(app, second_active, {"v": 2, "s": "ACTIVE"}) == "23505"  # một ACTIVE mỗi loại
    assert sqlstate(app, second_active, {"v": 1, "s": "DRAFT"}) == "23505"  # (loại, version) duy nhất
    run(app, second_active, {"v": 2, "s": "DRAFT"})
    assert ids["schema"]


@pytest.mark.db
def test_source_document_checks(app: Engine) -> None:
    ids = setup(app)
    insert = (
        "INSERT INTO capture.source_document (id, uploaded_by, channel, storage_key, sha256, size_bytes, sensitivity) "
        "VALUES (gen_random_uuid(), :u, :c, :k, :h, :s, :sens)"
    )
    good = {"u": ids["user"], "c": "C1", "k": "k-1", "h": hashlib.sha256(b"y").digest(), "s": 10, "sens": "PERSONAL"}
    run(app, insert, good)
    for bad in (
        {"c": "C6"},
        {"h": b"short"},
        {"s": -1},
        {"sens": "SECRET"},
        {"k": "k-1"},  # storage_key UNIQUE
    ):
        assert sqlstate(app, insert, {**good, "k": f"k-{uuid.uuid4()}", **bad}) in ("23514", "23505"), bad
    duplicate_content = {**good, "k": "k-2", "h": hashlib.sha256(b"x").digest()}
    run(app, insert, duplicate_content)  # sha256 trùng chỉ cảnh báo (FR-DC-08), không chặn
    with pytest.raises(DBAPIError) as info:
        run(app, "DELETE FROM capture.source_document")
    assert "permission denied" in str(info.value)


@pytest.mark.db
def test_extraction_fields_and_review(app: Engine) -> None:
    """SRS-CAP-13 (độ tin cậy 0–1, vị trí, lý do), SRS-REV-07 (giá trị gốc + đúng), SRS-REV-09 (thời điểm review)."""
    ids = setup(app)
    field = (
        "INSERT INTO capture.extracted_field (id, extraction_id, field_key, value, confidence, page_no, bbox, "
        "source_text, uncertainty_reason, reviewed_value, corrected) "
        "VALUES (gen_random_uuid(), :e, :k, '\"10\"', :c, 1, "
        "'[0,0,1,1]', '10', NULL, '\"12\"', true)"
    )
    run(app, field, {"e": ids["extraction"], "k": "amount", "c": 0.42})
    assert sqlstate(app, field, {"e": ids["extraction"], "k": "other", "c": 1.5}) == "23514"
    assert sqlstate(app, field, {"e": ids["extraction"], "k": "amount", "c": 0.5}) == "23505"
    review = (
        "INSERT INTO capture.extraction_review (id, extraction_id, reviewer_id, decision, reason, finished_at) "
        "VALUES (gen_random_uuid(), :e, :u, :d, :r, :f)"
    )
    base = {"e": ids["extraction"], "u": ids["user"]}
    assert sqlstate(app, review, {**base, "d": "REJECT", "r": None, "f": "2099-01-01T00:00:00+07"}) == "23514"
    assert sqlstate(app, review, {**base, "d": "APPROVE", "r": None, "f": None}) == "23514"
    run(app, review, {**base, "d": None, "r": None, "f": None})  # đang review
    run(app, review, {**base, "d": "REJECT", "r": "Sai loại", "f": "2099-01-01T00:00:00+07"})


@pytest.mark.db
def test_import_and_lineage_links(app: Engine) -> None:
    ids = setup(app)
    batch = uuid.uuid4()
    insert = (
        "INSERT INTO capture.import_batch (id, source_document_id, target, created_by, rows_total, rows_valid, "
        "rows_committed) VALUES (:i, :d, 'org.employee', :u, :t, :v, :c)"
    )
    assert (
        sqlstate(app, insert, {"i": uuid.uuid4(), "d": ids["doc"], "u": ids["user"], "t": 10, "v": 11, "c": 0})
        == "23514"
    )
    run(app, insert, {"i": batch, "d": ids["doc"], "u": ids["user"], "t": 100, "v": 97, "c": 97})
    run(
        app,
        "INSERT INTO capture.import_row_error (batch_id, row_no, field, message) VALUES (:b, 3, 'ngay', 'Sai ngày')",
        {"b": batch},
    )
    run(
        app,
        "INSERT INTO capture.data_lineage (id, target_type, target_id, source_document_id, page_no, extraction_id) "
        "VALUES (gen_random_uuid(), 'work.task', 'x', :d, 1, :e)",
        {"d": ids["doc"], "e": ids["extraction"]},
    )
    task_fk = (
        "INSERT INTO work.task (id, title, owner_user_id, assigned_by, source_document_id) "
        "VALUES (gen_random_uuid(), 'Từ biên bản', :u, :u, :d)"
    )
    run(app, task_fk, {"u": ids["user"], "d": ids["doc"]})
    assert sqlstate(app, task_fk, {"u": ids["user"], "d": uuid.uuid4()}) == "23503"  # FK nay đã có (T-202)
