"""T-107: bảng `access.*`, seed role/permission, INV-09/10/11, điều kiện assignment (ADR-007, Architecture §6).

DoD riêng T-107: không seed tài khoản (`test_seed_in_database_and_no_accounts`); seed `hr.*`, `pii.unmask`,
`goals.activate` không có quyền nền (`test_sensitive_permissions_have_no_base`). T-107 không làm chủ TC nào — bằng
chứng thành phần (phần CSDL) cho TC-ACC-04 (INV-10), TC-ACC-05 (INV-09), TC-ACC-06 (INV-11, đồng thời), TC-ACC-07
(điều kiện assignment); task chủ T-109.
"""

import importlib.util
import re
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.access.api import ScopeType, create_assignment, grant_role, revoke_assignment, revoke_role, roles_of
from aieos.platform.api import ApiError, create_db_engine, make_session_factory, transaction
from tests.conftest import ProvisionedDatabase, migrate_to_head

REPO = Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs" / "03-architecture" / "Architecture.md"
MIGRATION = REPO / "backend" / "src" / "aieos" / "platform" / "migrations" / "versions" / "0005_access_seed.py"
ROLES = ("ADMIN", "CEO", "CFO", "MANAGER", "EMPLOYEE")
CATEGORY = {"Đọc": "READ", "Ghi": "WRITE", "Duyệt": "APPROVE", "Quản trị": "ADMIN", "Sử dụng AI": "AI"}


def migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m0005", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def documented_matrix() -> dict[str, tuple[str, dict[str, str]]]:
    section = ARCHITECTURE.read_text(encoding="utf-8").split("## 6. Authorization và permission matrix", 1)[1]
    section = section.split("\n## ", 1)[0]
    matrix: dict[str, tuple[str, dict[str, str]]] = {}
    for line in section.splitlines():
        match = re.match(r"^\| `([a-z_.]+)` \| ([^|]+) \|(.*)$", line)
        if not match:
            continue
        cells = [c.strip() for c in match.group(3).split("|")][:5]
        kinds = {}
        for role, cell in zip(ROLES, cells, strict=True):
            if cell.startswith("B"):
                kinds[role] = "BASE"
            elif cell.startswith("A"):
                kinds[role] = "ELIGIBLE"
            else:
                assert cell == "—", (match.group(1), role, cell)
        matrix[match.group(1)] = (CATEGORY[match.group(2).strip()], kinds)
    return matrix


# ---------- Không cần CSDL ----------


def test_seed_matches_architecture_matrix() -> None:
    module = migration_module()
    seeded = {code: (category, dict(roles)) for code, category, roles in module.MATRIX}
    assert tuple(module.ROLES) == ROLES
    assert seeded == documented_matrix()


def test_sensitive_permissions_have_no_base() -> None:
    """DoD T-107: `hr.*`, `pii.unmask`, `goals.activate` không có quyền nền."""
    seeded = {code: roles for code, _, roles in migration_module().MATRIX}
    for code in ("hr.profile.read", "hr.salary.read", "hr.export", "pii.unmask"):
        assert seeded[code] == {}, code
    assert "BASE" not in seeded["goals.activate"].values() and seeded["goals.activate"]
    assert seeded["hr.import"] == {"ADMIN": "BASE"}  # R4: chỉ import, giới hạn tác vụ
    for code in ("finance.approve", "finance.period.manage"):
        assert "ADMIN" not in seeded[code] and "CEO" not in seeded[code]  # R2, D-21


# ---------- PostgreSQL thật ----------


@pytest.fixture
def db(database: ProvisionedDatabase) -> Iterator[tuple[Engine, Any]]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    yield engine, make_session_factory(engine)
    engine.dispose()


def new_user(engine: Engine, status: str = "ACTIVE") -> uuid.UUID:
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                "VALUES (:i, :e, 'U', :s, :p)"
            ),
            {
                "i": user_id,
                "e": f"{user_id}@example.com",
                "s": status,
                "p": None if status == "INVITED" else "$argon2id$x",
            },
        )
    return user_id


def sql_role(engine: Engine, user: uuid.UUID, role: str, granted_by: uuid.UUID | None = None) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO access.user_role (user_id, role_code, granted_by, reason) VALUES (:u, :r, :g, :why)"),
            {"u": user, "r": role, "g": granted_by, "why": "lý do" if granted_by else None},
        )


def sqlstate(engine: Engine, sql: str, params: dict[str, object]) -> str | None:
    try:
        with engine.begin() as conn:
            conn.execute(text(sql), params)
    except DBAPIError as error:
        return str(getattr(error.orig, "sqlstate", "?"))
    return None


@pytest.mark.db
def test_seed_in_database_and_no_accounts(db: tuple[Engine, Any]) -> None:
    engine, _ = db
    with engine.connect() as conn:
        roles = set(conn.execute(text("SELECT code FROM access.role")).scalars())
        permissions = {
            row.code: (row.category, row.assignable)
            for row in conn.execute(text("SELECT code, category, assignable FROM access.permission"))
        }
        pairs = {
            (row.role_code, row.permission_code): row.kind
            for row in conn.execute(text("SELECT role_code, permission_code, kind FROM access.role_permission"))
        }
        accounts = conn.execute(text("SELECT count(*) FROM identity.user_account")).scalar_one()
        user_roles = conn.execute(text("SELECT count(*) FROM access.user_role")).scalar_one()
    expected = documented_matrix()
    assert roles == set(ROLES)
    assert permissions == {code: (cat, "ELIGIBLE" in kinds.values()) for code, (cat, kinds) in expected.items()}
    assert pairs == {(role, code): kind for code, (_, kinds) in expected.items() for role, kind in kinds.items()}
    assert (accounts, user_roles) == (0, 0)  # DoD: không seed tài khoản


@pytest.mark.db
def test_catalog_tables_read_only_for_app(db: tuple[Engine, Any], database: ProvisionedDatabase) -> None:
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        granted = {
            (table, privilege)
            for table in ("role", "permission", "role_permission", "user_role", "assignment")
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
            if conn.execute(
                text("SELECT has_table_privilege('aieos_app', :t, :p)"), {"t": f"access.{table}", "p": privilege}
            ).scalar_one()
        }
    owner.dispose()
    assert granted == {
        ("role", "SELECT"),
        ("permission", "SELECT"),
        ("role_permission", "SELECT"),
        ("user_role", "SELECT"),
        ("user_role", "INSERT"),
        ("user_role", "UPDATE"),
        ("user_role", "DELETE"),
        ("assignment", "SELECT"),
        ("assignment", "INSERT"),
        ("assignment", "UPDATE"),
    }


@pytest.mark.db
def test_admin_cfo_rejected_by_database(db: tuple[Engine, Any]) -> None:
    """INV-10 (phần CSDL của TC-ACC-04): SQL bằng role ứng dụng bị từ chối, cả hai thứ tự."""
    engine, _ = db
    granter = new_user(engine)
    for first, second in (("CFO", "ADMIN"), ("ADMIN", "CFO")):
        user = new_user(engine)
        sql_role(engine, user, first, granter)
        assert (
            sqlstate(
                engine,
                "INSERT INTO access.user_role (user_id, role_code, granted_by, reason) VALUES (:u, :r, :g, 'x')",
                {"u": user, "r": second, "g": granter},
            )
            == "AE001"
        )
    other = new_user(engine)
    sql_role(engine, other, "CEO", granter)
    sql_role(engine, other, "CFO", granter)  # nhiều role khác được phép (R7)
    assert (
        sqlstate(
            engine,
            "UPDATE access.user_role SET role_code = 'ADMIN' WHERE user_id = :u AND role_code = 'CEO'",
            {"u": other},
        )
        == "AE001"
    )


@pytest.mark.db
def test_self_grant_rejected_by_database(db: tuple[Engine, Any]) -> None:
    """INV-09 (phần CSDL của TC-ACC-05): tự cấp role/assignment bị CHECK từ chối."""
    engine, _ = db
    user = new_user(engine)
    assert (
        sqlstate(
            engine,
            "INSERT INTO access.user_role (user_id, role_code, granted_by, reason) VALUES (:u, 'CEO', :u, 'x')",
            {"u": user},
        )
        == "23514"
    )
    sql_role(engine, user, "CEO", new_user(engine))
    assert (
        sqlstate(
            engine,
            "INSERT INTO access.assignment (id, user_id, permission_code, scope_type, granted_by, reason) "
            "VALUES (gen_random_uuid(), :u, 'goals.activate', 'COMPANY', :u, 'x')",
            {"u": user},
        )
        == "23514"
    )
    assert (
        sqlstate(
            engine,
            "INSERT INTO access.user_role (user_id, role_code, granted_by, reason) VALUES (:u, 'MANAGER', :g, NULL)",
            {"u": user, "g": new_user(engine)},
        )
        == "23514"
    )  # có người cấp thì phải có lý do


@pytest.mark.db
def test_last_admin_guard(db: tuple[Engine, Any]) -> None:
    """INV-11: không gỡ role / khóa / vô hiệu ADMIN hoạt động cuối cùng."""
    engine, _ = db
    first = new_user(engine)
    sql_role(engine, first, "ADMIN")  # bootstrap: granted_by NULL
    delete = "DELETE FROM access.user_role WHERE user_id = :u AND role_code = 'ADMIN'"
    assert sqlstate(engine, delete, {"u": first}) == "AE002"
    for status in ("LOCKED", "DISABLED"):
        assert (
            sqlstate(engine, "UPDATE identity.user_account SET status = :s WHERE id = :u", {"u": first, "s": status})
            == "AE002"
        )
    second = new_user(engine)
    sql_role(engine, second, "ADMIN", first)
    assert sqlstate(engine, "UPDATE identity.user_account SET status = 'LOCKED' WHERE id = :u", {"u": first}) is None
    assert sqlstate(engine, delete, {"u": second}) == "AE002"  # first đã khóa → second là ADMIN hoạt động cuối
    assert sqlstate(engine, delete, {"u": first}) is None  # gỡ ADMIN không hoạt động: không ảnh hưởng


@pytest.mark.db
def test_concurrent_admin_removal_keeps_one(db: tuple[Engine, Any], database: ProvisionedDatabase) -> None:
    """INV-11 đồng thời (phần CSDL của TC-ACC-06): hai thao tác gỡ hai ADMIN cùng lúc → còn ≥ 1 ADMIN."""
    engine, _ = db
    owner = database.engine("aieos_owner")
    for _ in range(10):
        with owner.begin() as conn:  # dọn giữa các vòng: TRUNCATE không kích hoạt trigger theo dòng (chỉ owner)
            conn.execute(text("TRUNCATE access.user_role"))
        admins = [new_user(engine), new_user(engine)]
        sql_role(engine, admins[0], "ADMIN")
        sql_role(engine, admins[1], "ADMIN", admins[0])
        barrier = threading.Barrier(2)
        results: list[str | None] = [None, None]

        def remove(slot: int, target: uuid.UUID, barrier: threading.Barrier, results: list[str | None]) -> None:
            barrier.wait()
            results[slot] = sqlstate(
                engine, "DELETE FROM access.user_role WHERE user_id = :u AND role_code = 'ADMIN'", {"u": target}
            )

        threads = [threading.Thread(target=remove, args=(n, admins[n], barrier, results)) for n in (0, 1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert sorted(results, key=str) == sorted([None, "AE002"], key=str)
        with engine.connect() as conn:
            remaining = conn.execute(text("SELECT count(*) FROM access.user_role WHERE role_code = 'ADMIN'"))
            assert remaining.scalar_one() == 1
    owner.dispose()


@pytest.mark.db
def test_assignment_eligibility(db: tuple[Engine, Any]) -> None:
    """Phần CSDL của TC-ACC-07: chỉ role đủ điều kiện mới nhận assignment."""
    engine, _ = db
    granter = new_user(engine)
    users = {role: new_user(engine) for role in ("ADMIN", "CEO", "CFO", "MANAGER")}
    sql_role(engine, users["ADMIN"], "ADMIN")
    for role in ("CEO", "CFO", "MANAGER"):
        sql_role(engine, users[role], role, granter)
    sql = (
        "INSERT INTO access.assignment (id, user_id, permission_code, scope_type, scope_id, granted_by, reason) "
        "VALUES (gen_random_uuid(), :u, :p, :st, :sid, :g, 'lý do')"
    )

    def assign(role: str, permission: str, scope: str = "COMPANY", scope_id: str | None = None) -> str | None:
        return sqlstate(engine, sql, {"u": users[role], "p": permission, "st": scope, "sid": scope_id, "g": granter})

    assert assign("MANAGER", "finance.period.manage") == "AE003"
    assert assign("ADMIN", "finance.approve") == "AE003"
    assert assign("CEO", "finance.approve") == "AE003"
    assert assign("CFO", "data.read") == "AE003"  # không assignable
    assert assign("ADMIN", "hr.profile.read") == "AE003"  # R6: không ai giữ
    assert assign("CFO", "finance.period.manage") is None
    assert assign("CFO", "finance.approve") is None
    assert assign("MANAGER", "goals.activate", "ORG_UNIT", str(uuid.uuid4())) is None
    assert assign("MANAGER", "goals.activate", "ORG_UNIT", None) == "23514"  # phạm vi đơn vị phải có scope_id
    assert assign("CEO", "goals.activate", "COMPANY", "x") == "23514"  # COMPANY không có scope_id
    assert sqlstate(engine, "DELETE FROM access.assignment", {}) == "42501"  # thu hồi bằng revoked_at, không xóa


@pytest.mark.db
def test_service_maps_errors_and_audits(db: tuple[Engine, Any]) -> None:
    engine, factory = db
    admin, other, cfo = new_user(engine), new_user(engine), new_user(engine)
    with transaction(factory) as session:
        grant_role(session, user_id=admin, role="ADMIN", granted_by=None, reason=None)  # bootstrap (T-106)
        grant_role(session, user_id=cfo, role="CFO", granted_by=admin, reason="Kế toán trưởng")
        grant_role(session, user_id=cfo, role="CFO", granted_by=admin, reason="lặp")  # đã có → không đổi
    cases: list[tuple[str, Any]] = [
        ("SELF_ROLE_CHANGE", lambda s: grant_role(s, user_id=admin, role="CEO", granted_by=admin, reason="x")),
        (
            "ROLE_COMBINATION_FORBIDDEN",
            lambda s: grant_role(s, user_id=cfo, role="ADMIN", granted_by=admin, reason="x"),
        ),
        ("LAST_ADMIN", lambda s: revoke_role(s, user_id=admin, role="ADMIN", revoked_by=other, reason="x")),
        ("SELF_ROLE_CHANGE", lambda s: revoke_role(s, user_id=admin, role="ADMIN", revoked_by=admin, reason="x")),
        (
            "ASSIGNMENT_NOT_ELIGIBLE",
            lambda s: create_assignment(
                s,
                user_id=admin,
                permission="finance.approve",
                scope_type=ScopeType.COMPANY,
                scope_id=None,
                granted_by=other,
                reason="x",
            ),
        ),
        ("VALIDATION_ERROR", lambda s: grant_role(s, user_id=other, role="ROOT", granted_by=admin, reason="x")),
    ]
    for code, action in cases:
        with pytest.raises(ApiError) as info:
            with transaction(factory) as session:
                action(session)
        assert info.value.code == code
    with transaction(factory) as session:
        assignment = create_assignment(
            session,
            user_id=cfo,
            permission="finance.period.manage",
            scope_type=ScopeType.COMPANY,
            scope_id=None,
            granted_by=admin,
            reason="Giữ kỳ báo cáo",
        )
    with pytest.raises(ApiError) as info:
        with transaction(factory) as session:
            revoke_assignment(session, assignment_id=assignment, revoked_by=cfo)
    assert info.value.code == "SELF_ROLE_CHANGE"
    with transaction(factory) as session:
        revoke_assignment(session, assignment_id=assignment, revoked_by=admin)
        assert roles_of(session, cfo) == {"CFO"}
    with engine.connect() as conn:
        audit = conn.execute(text("SELECT action, actor_type, category FROM audit.event ORDER BY id")).all()
        revoked = conn.execute(text("SELECT revoked_at IS NOT NULL FROM access.assignment")).scalar_one()
    assert [tuple(row) for row in audit] == [
        ("access.role.grant", "BOOTSTRAP", "ADMIN"),
        ("access.role.grant", "USER", "ADMIN"),
        ("access.assignment.create", "USER", "ADMIN"),
        ("access.assignment.revoke", "USER", "ADMIN"),
    ]
    assert revoked is True
