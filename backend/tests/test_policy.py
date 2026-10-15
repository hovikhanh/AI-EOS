"""T-108: policy `authorize()`, phạm vi dữ liệu, mặc định deny, bắt buộc khai báo quyền cho route (SRS-ACC-01, 02, 03,
09; ADR-007).

TC do T-108 làm chủ: TC-ACC-01 (`test_effective_permissions_base_union_valid_assignments`), TC-ACC-02
(`test_undeclared_route_denied`, `test_out_of_scope_object_by_id_is_404`). TC-ACC-03 (liệt kê task/mục tiêu của
MANAGER) cần bảng `work`/`goals` và `org` chưa có — ở đây chỉ là **bằng chứng thành phần** của bộ lọc phạm vi trên bảng
thử (`test_scope_filter_lists_only_in_scope_rows`), không ghi PASS (`[CẦN XÁC NHẬN]` task chủ, Implementation_Plan §27).
"""

import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import Engine, column, select, table, text
from sqlalchemy.orm import Session

from aieos.access.api import (
    FINANCE,
    Actor,
    Grant,
    PermissionGuard,
    Resource,
    ScopeType,
    authorize,
    create_assignment,
    grant_role,
    load_actor,
    require,
    scope_filter,
)
from aieos.access.policy import Source
from aieos.app.asgi import PUBLIC_PATHS
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password
from aieos.platform.api import (
    AUTHENTICATED,
    CSRF_HEADER,
    PUBLIC,
    CsrfConfig,
    Secret,
    create_api,
    create_db_engine,
    declare,
    declared_permission,
    make_session_factory,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head
from tests.test_auth import restore_logging  # noqa: F401 — fixture dùng bên dưới

ORIGIN = "https://aieos.local"
KEY = Secret("khoa-csrf-test")
PASSWORD = "Mat-khau-dung-123!"
SETTINGS = AuthSettings(
    idle=timedelta(minutes=30),
    absolute=timedelta(hours=8),
    rate_limit_attempts=50,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=10,
    lockout_duration=timedelta(minutes=15),
)
UNIT_A, UNIT_A1, UNIT_B = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
TREE = {UNIT_A: {UNIT_A, UNIT_A1}, UNIT_A1: {UNIT_A1}, UNIT_B: {UNIT_B}}


@dataclass(frozen=True)
class FakeOrg:
    """Cây tổ chức thử: A ⊃ A1, B riêng; `managers` = đơn vị trực tiếp người dùng quản lý."""

    managers: dict[uuid.UUID, frozenset[uuid.UUID]]

    def managed_units(self, session: Session, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
        return self.subtree(session, self.managers.get(user_id, frozenset()))

    def subtree(self, session: Session, unit_ids: Iterable[uuid.UUID]) -> frozenset[uuid.UUID]:
        return frozenset(u for unit in unit_ids for u in TREE.get(unit, {unit}))


def actor(roles: Iterable[str], grants: dict[str, tuple[Grant, ...]], managed: Iterable[uuid.UUID] = ()) -> Actor:
    return Actor(uuid.uuid4(), frozenset(roles), grants, frozenset(managed))


BASE = (Grant(Source.BASE),)


# ---------- authorize (đơn vị) ----------


def test_default_deny_and_role_scopes() -> None:
    employee = actor({"EMPLOYEE"}, {"data.read": BASE})
    own = Resource(owner_id=employee.user_id, org_units=frozenset({UNIT_A}))
    other = Resource(owner_id=uuid.uuid4(), org_units=frozenset({UNIT_A}))
    assert authorize(employee, "data.read", own).allowed
    assert authorize(employee, "data.read", other).reason == "OUT_OF_SCOPE"  # team: chưa làm (SRS-ACC-04)
    assert authorize(employee, "finance.read", own).reason == "NO_PERMISSION"
    assert authorize(employee, "khong.ton.tai").reason == "NO_PERMISSION"

    manager = actor({"MANAGER"}, {"data.read": BASE}, managed=TREE[UNIT_A])
    assert authorize(manager, "data.read", Resource(owner_id=uuid.uuid4(), org_units=frozenset({UNIT_A1, UNIT_A})))
    assert not authorize(manager, "data.read", Resource(owner_id=uuid.uuid4(), org_units=frozenset({UNIT_B}))).allowed

    ceo = actor({"CEO"}, {"data.read": BASE})
    assert authorize(ceo, "data.read", other).allowed
    cfo = actor({"CFO"}, {"data.read": BASE})
    assert authorize(cfo, "data.read", Resource(owner_id=uuid.uuid4(), domain=FINANCE)).allowed
    assert not authorize(cfo, "data.read", other).allowed

    admin = actor({"ADMIN"}, {"user.manage": BASE})
    assert authorize(admin, "user.manage", Resource(business=False)).allowed  # tài nguyên quản trị
    assert not authorize(admin, "data.read", other).allowed  # ADMIN không có data.read (D-21)
    assert not authorize(admin, "user.manage", other).allowed  # dữ liệu nghiệp vụ: ngoài phạm vi


def test_assignment_scopes() -> None:
    def assigned(scope_type: str, scope_id: str | None, units: Iterable[uuid.UUID] = ()) -> Actor:
        grant = Grant(Source.ASSIGNMENT, scope_type, scope_id, frozenset(units))
        return actor({"EMPLOYEE"}, {"extraction.review": (grant,)})

    doc = Resource(owner_id=uuid.uuid4(), org_units=frozenset({UNIT_A1, UNIT_A}), document_type="INVOICE_IN")
    assert authorize(assigned("COMPANY", None), "extraction.review", doc).allowed
    assert authorize(assigned("ORG_UNIT", str(UNIT_A), TREE[UNIT_A]), "extraction.review", doc).allowed
    assert not authorize(assigned("ORG_UNIT", str(UNIT_B), TREE[UNIT_B]), "extraction.review", doc).allowed
    assert authorize(assigned("DOCUMENT_TYPE", "INVOICE_IN"), "extraction.review", doc).allowed
    assert not authorize(assigned("DOCUMENT_TYPE", "CONTRACT"), "extraction.review", doc).allowed
    assert not authorize(assigned("REVIEW_QUEUE", "Q1"), "extraction.review", doc).allowed
    assert authorize(assigned("REVIEW_QUEUE", "Q1"), "extraction.review", Resource(review_queue="Q1")).allowed


def test_require_hides_out_of_scope_objects() -> None:
    employee = actor({"EMPLOYEE"}, {"data.read": BASE})
    other = Resource(owner_id=uuid.uuid4())
    with pytest.raises(Exception) as hidden:
        require(employee, "data.read", other)
    assert getattr(hidden.value, "code", None) == "NOT_FOUND"
    with pytest.raises(Exception) as shown:
        require(employee, "data.read", other, hide=False)
    assert getattr(shown.value, "code", None) == "FORBIDDEN"
    with pytest.raises(Exception) as no_permission:
        require(employee, "finance.read")
    assert getattr(no_permission.value, "code", None) == "FORBIDDEN"


# ---------- CSDL ----------


@dataclass
class Env:
    engine: Engine
    database: ProvisionedDatabase

    def user(self, email: str, roles: tuple[str, ...]) -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                    "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p)"
                ),
                {"i": user_id, "e": email, "p": hash_password(PASSWORD)},
            )
        with transaction(make_session_factory(self.engine)) as session:
            for role in roles:
                grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
        return user_id

    def assign(self, user_id: uuid.UUID, permission: str, by: uuid.UUID, *, sql: str | None = None) -> uuid.UUID:
        with transaction(make_session_factory(self.engine)) as session:
            assignment = create_assignment(
                session,
                user_id=user_id,
                permission=permission,
                scope_type=ScopeType.COMPANY,
                scope_id=None,
                granted_by=by,
                reason="Thử",
            )
        if sql:
            with self.engine.begin() as conn:
                conn.execute(text(f"UPDATE access.assignment SET {sql} WHERE id = :i"), {"i": assignment})
        return assignment

    def actor(self, user_id: uuid.UUID, org: Any = None) -> Actor:
        with transaction(make_session_factory(self.engine)) as session:
            return load_actor(session, user_id, org) if org else load_actor(session, user_id)


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    yield Env(engine, database)
    engine.dispose()


@pytest.mark.db
def test_effective_permissions_base_union_valid_assignments(env: Env) -> None:
    """TC-ACC-01: quyền hiệu lực = quyền nền ∪ assignment còn hạn; hết hạn, chưa tới hạn, thu hồi → không có quyền."""
    admin = env.user("admin@example.com", ("ADMIN",))
    cfo = env.user("cfo@example.com", ("CFO",))
    base = env.actor(cfo)
    assert base.has("data.read") and base.has("finance.read") and not base.has("finance.approve")

    env.assign(
        cfo, "finance.approve", admin, sql="valid_from = now() - interval '2 days', valid_to = now() - interval '1 day'"
    )
    env.assign(cfo, "finance.submit", admin, sql="valid_from = now() + interval '1 day'")
    env.assign(cfo, "finance.reverse.request", admin, sql="revoked_at = now(), revoked_by = granted_by")
    expired = env.actor(cfo)
    for permission in ("finance.approve", "finance.submit", "finance.reverse.request"):
        assert not authorize(expired, permission).allowed, permission

    env.assign(cfo, "finance.approve", admin)
    current = env.actor(cfo)
    assert authorize(current, "finance.approve").allowed
    assert authorize(current, "finance.approve", Resource(owner_id=uuid.uuid4(), domain=FINANCE)).allowed  # COMPANY
    assert not current.has("user.manage")
    admin_actor = env.actor(admin)
    assert admin_actor.has("user.manage") and not admin_actor.has("data.read")


@pytest.mark.db
def test_scope_filter_lists_only_in_scope_rows(env: Env) -> None:
    """Bằng chứng thành phần TC-ACC-03: danh sách lọc trong SQL — MANAGER đơn vị A thấy A và A1, không thấy B."""
    manager = env.user("ql@example.com", ("MANAGER",))
    employee = env.user("nv@example.com", ("EMPLOYEE",))
    ceo = env.user("ceo@example.com", ("CEO",))
    admin = env.user("admin@example.com", ("ADMIN",))
    owner = env.database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.execute(text("CREATE TABLE public.probe_item (id serial PRIMARY KEY, owner_id uuid, org_unit_id uuid)"))
        conn.execute(text("GRANT SELECT, INSERT ON public.probe_item TO aieos_app"))
        conn.execute(text("GRANT USAGE ON SEQUENCE public.probe_item_id_seq TO aieos_app"))
    owner.dispose()
    rows = [(employee, UNIT_A1), (uuid.uuid4(), UNIT_A), (uuid.uuid4(), UNIT_B), (manager, UNIT_B)]
    with env.engine.begin() as conn:
        for row_owner, unit in rows:
            conn.execute(
                text("INSERT INTO public.probe_item (owner_id, org_unit_id) VALUES (:o, :u)"),
                {"o": row_owner, "u": unit},
            )
    item = table("probe_item", column("id"), column("owner_id"), column("org_unit_id"), schema="public")
    org = FakeOrg({manager: frozenset({UNIT_A})})

    def visible(user: uuid.UUID) -> set[tuple[Any, Any]]:
        who = env.actor(user, org)
        condition = scope_filter(who, "data.read", owner=item.c.owner_id, org_unit=item.c.org_unit_id)
        with env.engine.connect() as conn:
            return {(r.owner_id, r.org_unit_id) for r in conn.execute(select(item).where(condition))}

    assert visible(manager) == {(employee, UNIT_A1), (rows[1][0], UNIT_A), (manager, UNIT_B)}  # A, A1 + của mình
    assert visible(employee) == {(employee, UNIT_A1)}
    assert visible(ceo) == set(rows)
    assert visible(admin) == set()  # không có data.read


# ---------- TC-ACC-02 (route) ----------


@dataclass
class Api:
    client: TestClient
    env: Env


@pytest.fixture
def api(env: Env) -> Api:
    factory = make_session_factory(env.engine)
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session)
    router = APIRouter()
    owners: dict[str, uuid.UUID] = {}

    @router.get("/probe/undeclared")
    def undeclared() -> dict[str, str]:
        return {"ok": "1"}

    @router.get("/probe/hidden", include_in_schema=False)
    def hidden() -> dict[str, str]:
        return {"ok": "1"}

    @router.get("/probe/finance", **guard.route("finance.read"))
    def finance() -> dict[str, str]:
        return {"ok": "1"}

    @router.get("/probe/items/{item}", **guard.route("data.read"))
    def read_item(item: str, who: Annotated[Actor, Depends(guard.actor)]) -> dict[str, str]:
        require(who, "data.read", Resource(owner_id=owners.get(item)))
        return {"item": item}

    @router.get("/probe/open", **declare(AUTHENTICATED))
    def open_route() -> dict[str, str]:
        return {"ok": "1"}

    app = create_api(
        {},
        (build_auth_router(auth, KEY), router),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
    app.state.owners = owners
    return Api(client, env)


def login(api: Api, email: str) -> TestClient:
    client = TestClient(api.client.app, base_url="https://testserver", headers={"Origin": ORIGIN})
    body = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()
    client.headers[CSRF_HEADER] = body["csrf_token"]
    return client


@pytest.mark.db
def test_undeclared_route_denied(api: Api) -> None:
    """TC-ACC-02 (phần 1): route không khai báo permission → `403`, kể cả khi có session hợp lệ và route ẩn."""
    api.env.user("nv@example.com", ("EMPLOYEE",))
    client = login(api, "nv@example.com")
    for path in ("/api/v1/probe/undeclared", "/api/v1/probe/hidden"):
        response = client.get(path)
        assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN", path
    assert client.get("/api/v1/probe/open").status_code == 200
    anonymous = TestClient(api.client.app, base_url="https://testserver").get("/api/v1/probe/undeclared")
    assert anonymous.status_code == 403


@pytest.mark.db
def test_route_permission_checked_and_denial_audited(api: Api) -> None:
    api.env.user("nv@example.com", ("EMPLOYEE",))
    api.env.user("ceo@example.com", ("CEO",))
    response = login(api, "nv@example.com").get("/api/v1/probe/finance")
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"
    assert login(api, "ceo@example.com").get("/api/v1/probe/finance").status_code == 200
    assert TestClient(api.client.app, base_url="https://testserver").get("/api/v1/probe/finance").status_code == 401
    with api.env.engine.connect() as conn:
        event = conn.execute(
            text(
                "SELECT category, outcome, reason, changes->>'permission' FROM audit.event "
                "WHERE action = 'access.denied'"
            )
        ).one()
    assert tuple(event) == ("SECURITY", "DENIED", "NO_PERMISSION", "finance.read")


@pytest.mark.db
def test_out_of_scope_object_by_id_is_404(api: Api) -> None:
    """TC-ACC-02 (phần 2): đọc đối tượng ngoài phạm vi qua ID → `404` (không lộ sự tồn tại)."""
    mine = api.env.user("nv@example.com", ("EMPLOYEE",))
    other = api.env.user("nv2@example.com", ("EMPLOYEE",))
    owners = api.client.app.state.owners  # type: ignore[attr-defined]
    owners.update({"cua-toi": mine, "cua-nguoi-khac": other})
    client = login(api, "nv@example.com")
    assert client.get("/api/v1/probe/items/cua-toi").json() == {"item": "cua-toi"}
    response = client.get("/api/v1/probe/items/cua-nguoi-khac")
    assert response.status_code == 404 and response.json()["code"] == "NOT_FOUND"


def test_every_application_route_declares_permission(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    restore_logging: None,  # noqa: F811
) -> None:
    """Mọi route của `create_app` có khai báo; `PUBLIC` khớp đúng danh sách công khai (API_Specification §1.2)."""
    from aieos.app.asgi import create_app
    from tests.test_auth import api_env

    api_env(monkeypatch, tmp_path, "postgresql://aieos_app:x@127.0.0.1:1/aieos")
    app = create_app()
    declared: dict[tuple[str, str], str | None] = {}
    for path, operations in app.openapi()["paths"].items():
        for method, operation in operations.items():
            declared[(method.upper(), path)] = operation.get("x-aieos-permission")
    assert declared and all(declared.values()), [k for k, v in declared.items() if not v]
    assert {k for k, v in declared.items() if v == PUBLIC} == set(PUBLIC_PATHS)
    assert declared_permission(None) is None
