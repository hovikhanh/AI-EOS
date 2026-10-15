"""T-008: module audit append-only (ADR-010, SRS-AUD-01…03, INV-14, Database_Design §9).

TC-AUD-03 (task chủ T-008, D-55): `UPDATE`/`DELETE` trên `audit.event` bằng role ứng dụng bị CSDL từ chối —
`test_app_role_cannot_modify_audit` (+ TRUNCATE). Test còn lại là bằng chứng thành phần cho TC-AUD-01 (chủ T-109:
ghi cùng transaction, transaction riêng cho DENIED/FAILED) và TC-AUD-02 (chủ T-105: che dữ liệu), không phải PASS
của hai TC đó (D-44 R3).
"""

import ast
import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from aieos.audit.api import (
    ActorType,
    AuditEvent,
    AuditEventError,
    AutonomyLevel,
    Category,
    Outcome,
    mask_changes,
    record,
    record_separately,
)
from aieos.platform.api import CORRELATION_ID, REDACTED, Secret, create_db_engine, make_session_factory, transaction
from tests.conftest import ProvisionedDatabase, migrate_to_head

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "aieos"
SECRET_VALUES = ("mat-khau-bi-mat", "tok-123456", "otp-654321", "sk-khoa-api", "csrf-abc")


def event(**overrides: object) -> AuditEvent:
    values: dict[str, object] = {
        "category": Category.BUSINESS,
        "actor_type": ActorType.USER,
        "actor_user_id": uuid.uuid4(),
        "action": "test.object.update",
        "outcome": Outcome.SUCCESS,
        "resource_type": "test_object",
        "resource_id": "42",
    }
    values.update(overrides)
    return AuditEvent(**values)  # type: ignore[arg-type]


def sensitive_changes() -> dict[str, object]:
    return {
        "before": {"name": "A", "password": SECRET_VALUES[0], "salary": 1000},
        "after": {
            "name": "B",
            "access_token": SECRET_VALUES[1],
            "mfa_code": SECRET_VALUES[2],
            "nested": [{"api_key": SECRET_VALUES[3]}, {"X-CSRF-Token": SECRET_VALUES[4]}],
            "salary": 2000,
            "key": Secret("gia-tri-secret"),
        },
    }


# ---------- Không cần CSDL ----------


def test_mask_changes_hides_secrets_and_declared_fields() -> None:
    masked = mask_changes(sensitive_changes(), frozenset({"Salary"}))
    dumped = json.dumps(masked, ensure_ascii=False)
    for value in (*SECRET_VALUES, "gia-tri-secret", "1000", "2000"):
        assert value not in dumped
    assert masked["before"] == {"name": "A", "password": REDACTED, "salary": REDACTED}
    assert masked["after"]["name"] == "B"
    assert masked["after"]["nested"] == [{"api_key": REDACTED}, {"X-CSRF-Token": REDACTED}]


def test_mask_changes_keeps_ordinary_values_json_safe() -> None:
    ident = uuid.uuid4()
    masked = mask_changes({"after": {"owner": ident, "tags": ("a", "b"), "amount": "12.50"}})
    assert masked == {"after": {"owner": str(ident), "tags": ["a", "b"], "amount": "12.50"}}
    assert mask_changes(None) is None


def test_event_rejects_ai_fields_for_non_ai_actor() -> None:
    with pytest.raises(AuditEventError):
        event(ai_agent="data_capture")
    with pytest.raises(AuditEventError):
        event(autonomy_level=AutonomyLevel.L2)
    ai = event(actor_type=ActorType.AI, actor_user_id=None, ai_agent="data_capture", autonomy_level=AutonomyLevel.L2)
    assert ai.autonomy_level is AutonomyLevel.L2


def test_event_requires_action() -> None:
    with pytest.raises(AuditEventError):
        event(action="  ")


def test_autonomy_levels_stop_at_l3() -> None:
    assert [level.value for level in AutonomyLevel] == ["L0", "L1", "L2", "L3"]  # L4 ngoài MVP (D-11)


def test_public_api_has_no_update_or_delete() -> None:
    import aieos.audit.api as api

    names = {name.lower() for name in api.__all__}
    assert not {n for n in names if any(word in n for word in ("update", "delete", "remove", "purge", "edit"))}


def test_audit_models_only_used_through_api() -> None:
    """C4: module khác không import `aieos.audit.models`/`recorder` trực tiếp (bổ sung cho test AST chung)."""
    for path in PACKAGE_DIR.rglob("*.py"):
        if path.is_relative_to(PACKAGE_DIR / "audit"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in {"aieos.audit.models", "aieos.audit.recorder"}, path


# ---------- PostgreSQL thật ----------


def denied(engine: Engine, statement: str) -> str | None:
    """Trả về thông điệp lỗi nếu CSDL từ chối vì quyền/trigger (SQLSTATE 42501), ngược lại None."""
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(statement)
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) == "42501":
            return str(error.orig)
        raise
    return None


def seeded(database: ProvisionedDatabase) -> tuple[Engine, int]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    with transaction(make_session_factory(engine)) as session:
        event_id = record(session, event())
    return engine, event_id


@pytest.mark.db
def test_app_role_cannot_modify_audit(database: ProvisionedDatabase) -> None:
    """TC-AUD-03: UPDATE/DELETE (và TRUNCATE) trên audit.event bằng role ứng dụng bị CSDL từ chối."""
    app, event_id = seeded(database)
    assert denied(app, f"UPDATE audit.event SET outcome = 'FAILED' WHERE id = {event_id}")
    assert denied(app, f"DELETE FROM audit.event WHERE id = {event_id}")
    assert denied(app, "TRUNCATE audit.event")
    with app.connect() as conn:
        row = conn.execute(text("SELECT outcome FROM audit.event WHERE id = :i"), {"i": event_id}).scalar_one()
    assert row == "SUCCESS"
    app.dispose()


@pytest.mark.db
def test_trigger_blocks_even_owner(database: ProvisionedDatabase) -> None:
    """INV-14: trigger chặn sửa/xóa với mọi role, không chỉ dựa vào quyền của aieos_app."""
    app, event_id = seeded(database)
    app.dispose()
    owner = database.engine("aieos_owner")
    for statement in (
        f"UPDATE audit.event SET reason = 'sửa' WHERE id = {event_id}",
        f"DELETE FROM audit.event WHERE id = {event_id}",
        "TRUNCATE audit.event",
    ):
        message = denied(owner, statement)
        assert message and "append-only" in message, statement
    with owner.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM audit.event")).scalar_one() == 1
    owner.dispose()


@pytest.mark.db
def test_table_privileges(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        granted = {
            (role, privilege)
            for role in ("aieos_app", "aieos_backup")
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
            if conn.execute(
                text("SELECT has_table_privilege(:r, 'audit.event', :p)"), {"r": role, "p": privilege}
            ).scalar_one()
        }
    owner.dispose()
    assert granted == {("aieos_app", "SELECT"), ("aieos_app", "INSERT"), ("aieos_backup", "SELECT")}


@pytest.mark.db
def test_app_cannot_forge_id_or_disable_trigger(database: ProvisionedDatabase) -> None:
    app, _ = seeded(database)
    with pytest.raises(DBAPIError):
        with app.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO audit.event (id, category, actor_type, action, outcome) "
                "VALUES (999, 'ADMIN', 'SYSTEM', 'x', 'SUCCESS')"
            )
    assert denied(app, "ALTER TABLE audit.event DISABLE TRIGGER event_reject_update_delete")
    app.dispose()


@pytest.mark.db
def test_record_is_part_of_caller_transaction(database: ProvisionedDatabase) -> None:
    """SRS-AUD-01: thay đổi không commit thì audit không tồn tại (bằng chứng thành phần TC-AUD-01)."""
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    factory = make_session_factory(engine)
    with pytest.raises(RuntimeError):
        with transaction(factory) as session:
            record(session, event(action="test.rolled_back"))
            raise RuntimeError("thao tác thất bại")
    with transaction(factory) as session:
        committed_id = record(session, event(action="test.committed"))
    with engine.connect() as conn:
        actions = conn.execute(text("SELECT id, action FROM audit.event ORDER BY id")).all()
    engine.dispose()
    assert [(row.id, row.action) for row in actions] == [(committed_id, "test.committed")]


@pytest.mark.db
def test_denied_and_failed_survive_rollback(database: ProvisionedDatabase) -> None:
    """ADR-010: thao tác bị từ chối/thất bại ghi audit trong transaction riêng (bằng chứng thành phần TC-AUD-01)."""
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    factory = make_session_factory(engine)
    for outcome in (Outcome.DENIED, Outcome.FAILED):
        with pytest.raises(RuntimeError):
            with transaction(factory) as session:
                record(session, event(action="test.main_write"))
                record_separately(factory, event(action="test.sensitive", outcome=outcome, reason="lý do"))
                raise RuntimeError("rollback thao tác chính")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT action, outcome FROM audit.event ORDER BY id")).all()
    engine.dispose()
    assert [tuple(row) for row in rows] == [("test.sensitive", "DENIED"), ("test.sensitive", "FAILED")]


@pytest.mark.db
def test_stored_changes_are_masked(database: ProvisionedDatabase) -> None:
    """SRS-AUD-02: giá trị bí mật không xuống CSDL (bằng chứng thành phần TC-AUD-02)."""
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    with transaction(make_session_factory(engine)) as session:
        record(session, event(changes=sensitive_changes(), masked_fields=frozenset({"salary"})))
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT changes::text FROM audit.event")).scalar_one()
    engine.dispose()
    for value in (*SECRET_VALUES, "gia-tri-secret", "1000", "2000"):
        assert value not in stored


@pytest.mark.db
def test_all_columns_round_trip_and_correlation_id(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    principal = uuid.uuid4()
    token = CORRELATION_ID.set("req-abc12345")
    try:
        with transaction(make_session_factory(engine)) as session:
            record(
                session,
                event(
                    category=Category.AI,
                    actor_type=ActorType.AI,
                    actor_user_id=None,
                    on_behalf_of_user_id=principal,
                    ai_agent="data_capture",
                    autonomy_level=AutonomyLevel.L2,
                    outcome=Outcome.BLOCKED,
                    reason="kill switch",
                    request_ip="10.0.0.5",
                    user_agent="pytest",
                ),
            )
    finally:
        CORRELATION_ID.reset(token)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM audit.event")).mappings().one()
    engine.dispose()
    assert row["category"] == "AI" and row["actor_type"] == "AI" and row["outcome"] == "BLOCKED"
    assert row["on_behalf_of_user_id"] == principal and row["autonomy_level"] == "L2"
    assert row["correlation_id"] == "req-abc12345"
    assert str(row["request_ip"]) == "10.0.0.5" and row["occurred_at"] is not None


@pytest.mark.db
@pytest.mark.parametrize(
    "columns",
    [
        "category = 'OTHER'",
        "actor_type = 'ROBOT'",
        "outcome = 'MAYBE'",
        "action = ''",
        "autonomy_level = 'L4', actor_type = 'AI', ai_agent = 'x'",
        "ai_agent = 'x'",
    ],
)
def test_check_constraints(database: ProvisionedDatabase, columns: str) -> None:
    migrate_to_head(database)
    base = {"category": "'ADMIN'", "actor_type": "'SYSTEM'", "action": "'x'", "outcome": "'SUCCESS'"}
    for part in columns.split(", "):
        key, value = part.split(" = ")
        base[key] = value
    app = database.engine("aieos_app")
    with pytest.raises(IntegrityError):
        with app.begin() as conn:
            conn.exec_driver_sql(f"INSERT INTO audit.event ({', '.join(base)}) VALUES ({', '.join(base.values())})")
    app.dispose()


@pytest.mark.db
def test_indexes_exist(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        indexes: dict[str, str] = dict(
            conn.execute(text("SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'audit'")).all()
        )
    owner.dispose()
    assert "(resource_type, resource_id, occurred_at)" in indexes["ix_event_resource"]
    assert "(actor_user_id, occurred_at)" in indexes["ix_event_actor"]
