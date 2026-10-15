"""T-301: bảng `ai.*`, Tool Registry, trần autonomy (INV-12), kill switch singleton (INV-13) — SRS-AIC-02, SRS-AIC-03.

T-301 không làm chủ TC nào (DoD: "CHECK trần có hiệu lực"). Thao tác bằng role ứng dụng `aieos_app`.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.identity.api import hash_password
from tests.conftest import ProvisionedDatabase, migrate_to_head

EXPECTED_TOOLS = {
    "upload_document": "WRITE",
    "classify_document": "READ",
    "extract_document": "READ",
    "validate_extraction": "READ",
    "submit_extraction_for_review": "WRITE",
    "approve_extraction": "WRITE",
    "commit_extraction": "WRITE",
    "import_table": "WRITE",
    "search_documents": "READ",
    "get_source_document": "READ",
    "create_task": "WRITE",
    "record_kpi_measurement": "WRITE",
}


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


def user(engine: Engine, email: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    run(
        engine,
        "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
        "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p)",
        {"i": user_id, "e": email, "p": hash_password("Mat-khau-dung-123!")},
    )
    return user_id


@pytest.mark.db
def test_tool_registry_seed(app: Engine) -> None:
    rows = run(
        app, "SELECT name, operation_type, financial, max_autonomy_level, enabled, risk_level FROM ai.tool"
    ).all()
    assert {r.name: r.operation_type for r in rows} == EXPECTED_TOOLS
    assert all(r.max_autonomy_level == 3 and not r.financial and not r.enabled and r.risk_level is None for r in rows)
    policies = dict(run(app, "SELECT tool_name, level FROM ai.autonomy_policy WHERE role_code IS NULL").all())
    assert policies == {**{n: 0 for n, o in EXPECTED_TOOLS.items() if o == "READ"}, "create_task": 3}  # SRS-AIC-03
    assert "create_invoice" not in {r.name for r in rows}  # Phase 2
    assert run(app, "SELECT value FROM ai.setting WHERE key = 'draft_expiry_days'").scalar_one() == 30
    assert run(app, "SELECT enabled FROM ai.kill_switch WHERE id = 1").scalar_one() is False


@pytest.mark.db
def test_autonomy_caps(app: Engine) -> None:
    """INV-12 (SRS-AIC-02): mọi tool ≤ L3, tài chính ≤ L2; policy không vượt trần tool; hạ trần dưới policy bị chặn."""
    insert = (
        "INSERT INTO ai.tool (name, module, operation_type, financial, max_autonomy_level) "
        "VALUES (:n, 'finance', 'WRITE', :f, :m)"
    )
    assert sqlstate(app, insert, {"n": "t1", "f": False, "m": 4}) == "23514"
    assert sqlstate(app, insert, {"n": "t2", "f": True, "m": 3}) == "23514"
    run(app, insert, {"n": "create_finance_draft", "f": True, "m": 2})
    policy = "INSERT INTO ai.autonomy_policy (id, tool_name, role_code, level) VALUES (gen_random_uuid(), :t, :r, :l)"
    assert sqlstate(app, policy, {"t": "create_finance_draft", "r": "CFO", "l": 3}) == "AE030"
    run(app, policy, {"t": "create_finance_draft", "r": "CFO", "l": 2})
    assert sqlstate(app, policy, {"t": "create_task", "r": None, "l": 4}) in ("AE030", "23514")  # trigger chạy trước
    lower = "UPDATE ai.tool SET max_autonomy_level = 2 WHERE name = 'create_task'"
    assert sqlstate(app, lower) == "AE030"  # policy create_task L3 hiện có
    raise_policy = "UPDATE ai.autonomy_policy SET level = 3 WHERE tool_name = 'create_finance_draft'"
    assert sqlstate(app, raise_policy) == "AE030"
    assert sqlstate(app, policy, {"t": "create_task", "r": None, "l": 1}) == "23505"  # một policy mặc định/tool/role


@pytest.mark.db
def test_kill_switch_singleton(app: Engine) -> None:
    """INV-13: chỉ một dòng kill switch."""
    assert sqlstate(app, "INSERT INTO ai.kill_switch (id, enabled, reason) VALUES (2, true, 'x')") == "23514"
    assert sqlstate(app, "INSERT INTO ai.kill_switch (id, enabled, reason) VALUES (1, true, 'x')") == "23505"


@pytest.mark.db
def test_call_log_sensitive_only_local(app: Engine) -> None:
    """ADR-011 (Database_Design §5): dữ liệu SENSITIVE/PERSONAL chỉ ghi nhận với provider local."""
    insert = (
        "INSERT INTO ai.call_log (provider, purpose, data_classification, provider_is_local, outcome) "
        "VALUES ('p', 'extract', :c, :l, 'OK')"
    )
    for classification in ("SENSITIVE", "PERSONAL"):
        assert sqlstate(app, insert, {"c": classification, "l": False}) == "23514"
        run(app, insert, {"c": classification, "l": True})
    run(app, insert, {"c": "INTERNAL", "l": False})


@pytest.mark.db
def test_action_rules(app: Engine) -> None:
    """Tool tài chính: người duyệt ≠ người khởi tạo; L3 đã thực thi có hạn hoàn tác ≥ 24 giờ (BR-11)."""
    a, b = user(app, "a@example.com"), user(app, "b@example.com")
    run(app, "INSERT INTO ai.tool (name, module, operation_type, financial, max_autonomy_level) "
        "VALUES ('create_finance_draft', 'finance', 'WRITE', true, 2)")  # fmt: skip
    insert = (
        "INSERT INTO ai.action (id, tool_name, initiated_by, effective_level, status, idempotency_key, reviewed_by, "
        "executed_at, undo_deadline) VALUES (gen_random_uuid(), :t, :i, :lv, 'EXECUTED', :k, :r, now(), :u)"
    )
    base = {"t": "create_finance_draft", "i": a, "lv": 2, "k": "k1", "r": a, "u": None}
    assert sqlstate(app, insert, base) == "AE031"
    run(app, insert, {**base, "r": b})
    run(app, insert, {**base, "t": "create_task", "lv": 2, "k": "k2", "r": a})  # không tài chính: tự xác nhận được
    late = run(app, "SELECT now() + interval '23 hours'").scalar_one()
    ok = run(app, "SELECT now() + interval '25 hours'").scalar_one()
    l3 = {**base, "t": "create_task", "lv": 3, "r": None}
    assert sqlstate(app, insert, {**l3, "k": "k3", "u": late}) == "23514"
    run(app, insert, {**l3, "k": "k4", "u": ok})
    assert sqlstate(app, insert, {**l3, "k": "k4", "u": ok}) == "23505"  # idempotency (initiated_by, key)
    assert sqlstate(app, insert, {**base, "t": "khong_ton_tai", "k": "k5", "r": b}) == "23503"
