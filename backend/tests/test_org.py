"""T-201: `org.*`, danh bạ và cây đơn vị (SRS-ACC-11; API-ORG-01, API-ORG-02), phạm vi MANAGER cho T-108 (SRS-ACC-03).

TC do T-201 làm chủ: TC-ACC-09 (`test_every_role_reads_directory_fields_only`).
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, column, select, table, text
from sqlalchemy.exc import DBAPIError

from aieos.access.api import PermissionGuard, grant_role, load_actor, scope_filter
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password, hash_token
from aieos.org.api import (
    OrgDirectoryScope,
    build_org_router,
    create_employee,
    create_unit,
    set_head,
    set_parent,
)
from aieos.platform.api import (
    CSRF_HEADER,
    SESSION_COOKIE,
    ApiError,
    CsrfConfig,
    Secret,
    create_api,
    create_db_engine,
    make_session_factory,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head

ORIGIN = "https://aieos.local"
KEY = Secret("khoa-csrf-test")
PASSWORD = "Mat-khau-dung-123!"
SETTINGS = AuthSettings(
    idle=timedelta(minutes=30),
    absolute=timedelta(hours=8),
    rate_limit_attempts=100,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=10,
    lockout_duration=timedelta(minutes=15),
    reauth=timedelta(minutes=5),
    password_min_length=12,
)
DIRECTORY_FIELDS = {"id", "full_name", "title", "org_unit_id", "org_unit_name", "manager_id", "manager_name"}


@dataclass
class Env:
    engine: Engine
    app: Any

    def session(self) -> Any:
        return transaction(make_session_factory(self.engine))

    def user(self, email: str, roles: tuple[str, ...], employee_id: uuid.UUID | None = None) -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, employee_id) "
                    "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p, :emp)"
                ),
                {"i": user_id, "e": email, "p": hash_password(PASSWORD), "emp": employee_id},
            )
        with self.session() as session:
            for role in roles:
                grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
        return user_id

    def login(self, email: str) -> TestClient:
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        body = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()
        client.headers[CSRF_HEADER] = body["csrf_token"]
        with self.engine.begin() as conn:  # ADMIN cần MFA: đánh dấu đã xác minh (luồng MFA kiểm ở T-103)
            conn.execute(
                text("UPDATE identity.session SET mfa_verified = true WHERE token_hash = :h"),
                {"h": hash_token(client.cookies[SESSION_COOKIE])},
            )
        return client


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, org=OrgDirectoryScope())
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_org_router(guard)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, app)
    engine.dispose()


def seed(env: Env) -> dict[str, uuid.UUID]:
    """Công ty ⊃ Kinh doanh ⊃ Kinh doanh miền Bắc; Kế toán riêng. Trưởng Kinh doanh: Bình."""
    with env.session() as session:
        company = create_unit(session, name="Công ty", code="CTY")
        sales = create_unit(session, name="Kinh doanh", code="KD", parent_id=company)
        north = create_unit(session, name="Kinh doanh miền Bắc", parent_id=sales)
        finance = create_unit(session, name="Kế toán", parent_id=company)
        binh = create_employee(session, full_name="Trần Bình", title="Trưởng phòng", org_unit_id=sales)
        an = create_employee(session, full_name="Nguyễn An", title="Nhân viên", org_unit_id=north, manager_id=binh)
        chi = create_employee(session, full_name="Lê Chi", org_unit_id=finance)
        nghi = create_employee(session, full_name="Phạm Nghỉ", org_unit_id=finance)
        session.execute(text("UPDATE org.employee SET status = 'INACTIVE' WHERE id = :i"), {"i": nghi})
        set_head(session, sales, binh)
    return {"company": company, "sales": sales, "north": north, "finance": finance, "binh": binh, "an": an, "chi": chi}


# ---------- TC-ACC-09 ----------


@pytest.mark.db
def test_every_role_reads_directory_fields_only(env: Env) -> None:
    """TC-ACC-09: mọi role đọc danh bạ — chỉ họ tên, chức danh, đơn vị, quản lý; không trường khác; không nhân viên
    nghỉ."""
    ids = seed(env)
    for role in ("ADMIN", "CEO", "CFO", "MANAGER", "EMPLOYEE"):
        env.user(f"{role.lower()}@example.com", (role,))
        response = env.login(f"{role.lower()}@example.com").get("/api/v1/org/employees")
        assert response.status_code == 200, (role, response.text)
        items = response.json()["items"]
        assert [i["full_name"] for i in items] == ["Lê Chi", "Nguyễn An", "Trần Bình"], role
        assert all(set(i) == DIRECTORY_FIELDS for i in items), role
    an = next(i for i in items if i["id"] == str(ids["an"]))
    assert (an["org_unit_name"], an["manager_name"], an["title"]) == ("Kinh doanh miền Bắc", "Trần Bình", "Nhân viên")
    anonymous = TestClient(env.app, base_url="https://testserver").get("/api/v1/org/employees")
    assert anonymous.status_code == 401


@pytest.mark.db
def test_units_tree_and_directory_filters(env: Env) -> None:
    ids = seed(env)
    env.user("nv@example.com", ("EMPLOYEE",))
    client = env.login("nv@example.com")
    units = client.get("/api/v1/org/units").json()["items"]
    assert {u["name"]: u["parent_id"] for u in units}["Kinh doanh miền Bắc"] == str(ids["sales"])
    assert next(u for u in units if u["code"] == "KD")["head_employee_id"] == str(ids["binh"])

    by_unit = client.get("/api/v1/org/employees", params={"org_unit_id": str(ids["finance"])}).json()["items"]
    assert [i["full_name"] for i in by_unit] == ["Lê Chi"]
    assert [i["full_name"] for i in client.get("/api/v1/org/employees", params={"q": "an"}).json()["items"]] == [
        "Nguyễn An"
    ]
    assert client.get("/api/v1/org/employees", params={"q": "%"}).json()["items"] == []  # ký tự đại diện bị thoát

    first = client.get("/api/v1/org/employees", params={"limit": 2}).json()
    second = client.get("/api/v1/org/employees", params={"limit": 2, "cursor": first["next_cursor"]}).json()
    assert [i["full_name"] for i in first["items"] + second["items"]] == ["Lê Chi", "Nguyễn An", "Trần Bình"]
    assert second["next_cursor"] is None
    bad = client.get("/api/v1/org/employees", params={"cursor": "sai"})
    assert bad.status_code == 422 and bad.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.db
def test_cycles_rejected_by_database(env: Env) -> None:
    ids = seed(env)
    with pytest.raises(ApiError) as unit_cycle, env.session() as session:
        set_parent(session, ids["company"], ids["north"])  # Công ty dưới cháu của chính nó
    assert unit_cycle.value.errors[0]["field"] == "parent_id"
    with pytest.raises(DBAPIError) as raw, env.engine.begin() as conn:
        conn.execute(text("UPDATE org.employee SET manager_id = :a WHERE id = :b"), {"a": ids["an"], "b": ids["binh"]})
    assert getattr(raw.value.orig, "sqlstate", None) == "AE005"
    with pytest.raises(DBAPIError) as own, env.engine.begin() as conn:
        conn.execute(text("UPDATE org.org_unit SET parent_id = id WHERE id = :i"), {"i": ids["sales"]})
    assert getattr(own.value.orig, "sqlstate", None) in ("AE004", "23514")  # trigger chạy trước CHECK
    with pytest.raises(DBAPIError) as delete, env.engine.begin() as conn:
        conn.execute(text("DELETE FROM org.employee WHERE id = :i"), {"i": ids["chi"]})
    assert "permission denied" in str(delete.value)


# ---------- Phạm vi MANAGER (T-108 + T-201) ----------


@pytest.mark.db
def test_manager_scope_follows_units_headed(env: Env, database: ProvisionedDatabase) -> None:
    """MANAGER làm trưởng Kinh doanh: thấy Kinh doanh và Kinh doanh miền Bắc, không thấy Kế toán; MANAGER chỉ là thành
    viên đơn vị (không làm trưởng) không có phạm vi đơn vị."""
    ids = seed(env)
    head = env.user("binh@example.com", ("MANAGER",), employee_id=ids["binh"])
    member = env.user("chi@example.com", ("MANAGER",), employee_id=ids["chi"])
    scope = OrgDirectoryScope()
    with env.session() as session:
        assert scope.managed_units(session, head) == {ids["sales"], ids["north"]}
        assert scope.managed_units(session, member) == frozenset()
        head_actor = load_actor(session, head, scope)
        member_actor = load_actor(session, member, scope)

    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.execute(text("CREATE TABLE public.probe (id serial, owner_id uuid, org_unit_id uuid)"))
        conn.execute(text("GRANT SELECT ON public.probe TO aieos_app"))
        for unit in ("sales", "north", "finance"):
            conn.execute(
                text("INSERT INTO probe (owner_id, org_unit_id) VALUES (:o, :u)"), {"o": uuid.uuid4(), "u": ids[unit]}
            )
    owner.dispose()
    probe = table("probe", column("owner_id"), column("org_unit_id"), schema="public")
    with env.engine.connect() as conn:

        def visible(actor: Any) -> set[Any]:
            condition = scope_filter(actor, "data.read", owner=probe.c.owner_id, org_unit=probe.c.org_unit_id)
            return {r.org_unit_id for r in conn.execute(select(probe).where(condition))}

        assert visible(head_actor) == {ids["sales"], ids["north"]}
        assert visible(member_actor) == set()


@pytest.mark.db
def test_user_employee_link_must_exist(env: Env) -> None:
    with pytest.raises(DBAPIError) as info:
        env.user("x@example.com", ("EMPLOYEE",), employee_id=uuid.uuid4())
    assert getattr(info.value.orig, "sqlstate", None) == "23503"
