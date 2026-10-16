"""T-502: kích hoạt mục tiêu `DRAFT → ACTIVE` với `goals.activate` (SRS-GOAL-03, 04; API-GOAL-04; D-39, D-51).

TC do T-502 làm chủ: TC-GOAL-07 (`test_activate_without_assignment_is_forbidden`), TC-GOAL-08
(`test_activate_with_assignment_in_scope`). Phần mục tiêu của TC-ACC-03 (chủ T-505, D-59):
`test_manager_lists_only_goals_of_own_unit`. Quy tắc cấp (công ty — CEO, đơn vị — MANAGER) và lựa chọn chặt hơn của
agent: `test_activation_level_rules`, `test_document_draft_creator_cannot_self_activate_company_goal`.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest
import sqlalchemy
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import PermissionGuard, ScopeType, create_assignment
from aieos.goals.api import build_goals_router
from aieos.identity.api import Authenticator, build_auth_router
from aieos.org.api import OrgDirectoryScope, create_employee, create_unit, set_head
from aieos.platform.api import (
    IDEMPOTENCY_HEADER,
    CsrfConfig,
    create_api,
    create_db_engine,
    make_session_factory,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head
from tests.test_goals import KEY, ORIGIN, SETTINGS, _login, _user

ACTIVATE = "goals.activate"


@dataclass
class Env:
    engine: Engine
    owner: Engine
    users: dict[str, uuid.UUID]
    units: dict[str, uuid.UUID]
    clients: dict[str, TestClient]

    def create(self, who: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        response = self.clients[who].post(f"/api/v1{path}", json=body, headers={IDEMPOTENCY_HEADER: uuid.uuid4().hex})
        assert response.status_code == 201, response.text
        return dict(response.json())

    def objective(self, who: str, owner: str, unit: str | None, title: str = "Mục tiêu") -> dict[str, Any]:
        body = {"title": title, "owner_user_id": str(self.users[owner]), "period_label": "2026-Q4"}
        if unit:
            body["org_unit_id"] = str(self.units[unit])
        return self.create(who, "/goals/objectives", body)

    def kr(self, who: str, objective: str, owner: str) -> dict[str, Any]:
        body = {"objective_id": objective, "metric": "Doanh thu", "target": "20",
                "owner_user_id": str(self.users[owner]), "period_label": "2026-Q4"}  # fmt: skip
        return self.create(who, "/goals/key-results", body)

    def kpi(self, who: str, owner: str, unit: str | None, metric: str = "KPI") -> dict[str, Any]:
        body = {"metric": metric, "target": "5", "owner_user_id": str(self.users[owner]), "period_label": "2026-10"}
        if unit:
            body["org_unit_id"] = str(self.units[unit])
        return self.create(who, "/goals/kpis", body)

    def activate(self, who: str, kind: str, item_id: str, version: str | None = '"1"') -> Any:
        headers = {"If-Match": version} if version is not None else {}
        return self.clients[who].post(f"/api/v1/goals/{kind}/{item_id}/activate", headers=headers)

    def row(self, table: str, item_id: str) -> Any:
        with self.owner.connect() as conn:
            return conn.execute(
                text(f"SELECT status, activated_by, activated_at, version FROM goals.{table} WHERE id = :i"),
                {"i": item_id},
            ).one()


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    """Công ty ⊃ Kinh doanh (trưởng: quanly) ⊃ Miền Bắc (trưởng: quanly_plain; nv_bac); Kế toán (trưởng: quanly_kt).

    Assignment `goals.activate`: ceo, ceo2 — `COMPANY`; quanly — `ORG_UNIT` Kinh doanh; quanly_kt — `ORG_UNIT` Miền Bắc
    (không thấy đơn vị này); quanly_cty (MANAGER) — `COMPANY`; ceo_dv (CEO) — `ORG_UNIT` Kinh doanh. ceo_plain,
    quanly_plain, nv_bac: không có assignment.
    """
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    with transaction(factory) as session:
        company = create_unit(session, name="Công ty")
        sales = create_unit(session, name="Kinh doanh", parent_id=company)
        north = create_unit(session, name="Miền Bắc", parent_id=sales)
        finance = create_unit(session, name="Kế toán", parent_id=company)
        e_manager = create_employee(session, full_name="Quản Lý", org_unit_id=sales)
        e_manager2 = create_employee(session, full_name="Quản Lý Bắc", org_unit_id=north)
        e_kt = create_employee(session, full_name="Quản Lý Kế Toán", org_unit_id=finance)
        e_bac = create_employee(session, full_name="Nhân Viên Bắc", org_unit_id=north)
        set_head(session, sales, e_manager)
        set_head(session, north, e_manager2)
        set_head(session, finance, e_kt)
    users = {
        "admin": _user(engine, "admin@example.com", ("ADMIN",), None),
        "ceo": _user(engine, "ceo@example.com", ("CEO",), None),
        "ceo2": _user(engine, "ceo2@example.com", ("CEO",), None),
        "ceo_plain": _user(engine, "ceo_plain@example.com", ("CEO",), None),
        "ceo_dv": _user(engine, "ceo_dv@example.com", ("CEO",), None),
        "quanly": _user(engine, "quanly@example.com", ("MANAGER",), e_manager),
        "quanly_plain": _user(engine, "quanly_plain@example.com", ("MANAGER",), e_manager2),
        "quanly_kt": _user(engine, "quanly_kt@example.com", ("MANAGER",), e_kt),
        "quanly_cty": _user(engine, "quanly_cty@example.com", ("MANAGER",), None),
        "nv_bac": _user(engine, "nv_bac@example.com", ("EMPLOYEE",), e_bac),
    }
    grants = (
        ("ceo", ScopeType.COMPANY, None),
        ("ceo2", ScopeType.COMPANY, None),
        ("quanly", ScopeType.ORG_UNIT, sales),
        ("quanly_kt", ScopeType.ORG_UNIT, north),
        ("quanly_cty", ScopeType.COMPANY, None),
        ("ceo_dv", ScopeType.ORG_UNIT, sales),
    )
    with transaction(factory) as session:
        for who, scope, unit in grants:
            create_assignment(
                session, user_id=users[who], permission=ACTIVATE, scope_type=scope,
                scope_id=str(unit) if unit else None, granted_by=users["admin"], reason="Thử nghiệm T-502",
            )  # fmt: skip
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, org=OrgDirectoryScope())
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_goals_router(guard)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    clients = {k: _login(app, engine, f"{k}@example.com") for k in users if k != "admin"}
    owner = sqlalchemy.create_engine(database.admin)
    units = {"company": company, "sales": sales, "north": north, "finance": finance}
    yield Env(engine, owner, users, units, clients)
    owner.dispose()
    engine.dispose()


# ---------- TC-GOAL-07 ----------


@pytest.mark.db
def test_activate_without_assignment_is_forbidden(env: Env) -> None:
    """TC-GOAL-07: không có `goals.activate` (kể cả CEO, MANAGER chưa được giao; không có quyền nền) → `403`."""
    company = env.objective("ceo_plain", "ceo_plain", None, "Công ty")
    unit = env.objective("quanly_plain", "quanly_plain", "north", "Miền Bắc")
    kr = env.kr("quanly_plain", unit["id"], "nv_bac")
    kpi = env.kpi("quanly_plain", "quanly_plain", "north")
    for who, kind, item in (
        ("ceo_plain", "objectives", company), ("ceo_plain", "objectives", unit), ("quanly_plain", "objectives", unit),
        ("quanly_plain", "key-results", kr), ("quanly_plain", "kpis", kpi), ("nv_bac", "key-results", kr),
    ):  # fmt: skip
        response = env.activate(who, kind, item["id"])
        assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN", (who, kind)
    for table, item in (("objective", company), ("objective", unit), ("key_result", kr), ("kpi", kpi)):
        assert env.row(table, item["id"]).status == "DRAFT"
    with env.owner.connect() as conn:
        denied = conn.execute(
            text("SELECT count(*) FROM audit.event WHERE action = 'access.denied' AND actor_user_id = :u"),
            {"u": env.users["ceo_plain"]},
        ).scalar_one()
        roles = conn.execute(
            text("SELECT count(*) FROM access.role_permission WHERE permission_code = :p AND kind = 'BASE'"),
            {"p": ACTIVATE},
        ).scalar_one()
    assert denied == 2 and roles == 0  # chưa có quyền nền (D-39)


# ---------- TC-GOAL-08 ----------


@pytest.mark.db
def test_activate_with_assignment_in_scope(env: Env) -> None:
    """TC-GOAL-08: assignment trong phạm vi → `ACTIVE`, `activated_by`/`activated_at`, audit người kích hoạt."""
    company = env.objective("ceo", "ceo", None, "Công ty")
    missing = env.activate("ceo", "objectives", company["id"], None)
    assert missing.status_code == 428 and missing.json()["code"] == "PRECONDITION_REQUIRED"
    stale = env.activate("ceo", "objectives", company["id"], '"7"')
    assert stale.status_code == 412 and stale.json()["code"] == "VERSION_CONFLICT"
    assert env.row("objective", company["id"]).status == "DRAFT"
    response = env.activate("ceo", "objectives", company["id"])
    assert response.status_code == 200, response.text
    assert (response.json()["status"], response.json()["version"], response.headers["etag"]) == ("ACTIVE", 2, '"2"')
    row = env.row("objective", company["id"])
    assert (row.status, row.activated_by, row.version) == ("ACTIVE", env.users["ceo"], 2) and row.activated_at
    again = env.activate("ceo", "objectives", company["id"], '"2"')
    assert again.status_code == 409 and again.json()["code"] == "INVALID_STATE"

    # MANAGER: assignment `ORG_UNIT` Kinh doanh phủ cả đơn vị con (Miền Bắc); KR theo Objective cha; KPI theo đơn vị.
    north = env.objective("quanly", "nv_bac", "north", "Miền Bắc")
    kr = env.kr("quanly", north["id"], "nv_bac")
    kpi = env.kpi("quanly", "quanly", "sales")
    for kind, table, item in (("objectives", "objective", north), ("key-results", "key_result", kr),
                              ("kpis", "kpi", kpi)):  # fmt: skip
        result = env.activate("quanly", kind, item["id"])
        assert result.status_code == 200 and result.json()["status"] == "ACTIVE", (kind, result.text)
        assert env.row(table, item["id"]).activated_by == env.users["quanly"]
    with env.owner.connect() as conn:
        events = conn.execute(
            text(
                "SELECT action, actor_user_id, resource_id, category, changes FROM audit.event "
                "WHERE action LIKE 'goals.%.activate' ORDER BY id"
            )
        ).all()
    assert [(e.action, e.actor_user_id, e.resource_id) for e in events] == [
        ("goals.objective.activate", env.users["ceo"], company["id"]),
        ("goals.objective.activate", env.users["quanly"], north["id"]),
        ("goals.key_result.activate", env.users["quanly"], kr["id"]),
        ("goals.kpi.activate", env.users["quanly"], kpi["id"]),
    ]
    assert {e.category for e in events} == {"BUSINESS"}
    assert events[0].changes["status"] == {"from": "DRAFT", "to": "ACTIVE"}
    active = env.clients["ceo"].get("/api/v1/goals/objectives", params={"status": "ACTIVE"}).json()
    assert {o["id"] for o in active} == {company["id"], north["id"]}


# ---------- Quy tắc cấp (Q-28 → D-51) ----------


@pytest.mark.db
def test_activation_level_rules(env: Env) -> None:
    """Cấp công ty — CEO + assignment `COMPANY`; cấp đơn vị — MANAGER + assignment `ORG_UNIT` phủ đơn vị (lựa chọn
    chặt hơn của agent, `[CẦN XÁC NHẬN]`). Không thấy đối tượng → `404`."""
    company = env.objective("ceo", "quanly_cty", None, "Công ty")
    company_kr = env.kr("ceo", company["id"], "quanly")
    company_kpi = env.kpi("ceo", "ceo", None)
    sales = env.objective("ceo", "quanly_cty", "sales", "Kinh doanh")
    finance = env.objective("ceo", "quanly_kt", "finance", "Kế toán")
    cases = (
        ("ceo", "objectives", sales, 403),  # assignment COMPANY không thay cho cấp đơn vị
        ("ceo_dv", "objectives", sales, 403),  # CEO giữ assignment ORG_UNIT: cấp đơn vị chỉ MANAGER
        ("quanly_cty", "objectives", company, 403),  # MANAGER không kích hoạt cấp công ty
        ("quanly_cty", "objectives", sales, 403),  # MANAGER + assignment COMPANY: không phải ORG_UNIT
        ("quanly", "key-results", company_kr, 403),  # KR của Objective cấp công ty (owner KR vẫn thấy)
        ("quanly", "objectives", finance, 404),  # ngoài phạm vi đọc
        ("quanly_kt", "objectives", finance, 403),  # assignment Miền Bắc không phủ Kế toán
        ("ceo_dv", "kpis", company_kpi, 403),  # CEO thấy KPI cấp công ty, assignment ORG_UNIT
    )
    for who, kind, item, status in cases:
        response = env.activate(who, kind, item["id"])
        assert response.status_code == status, (who, kind, item.get("title"), response.text)
    for table, item in (("objective", company), ("key_result", company_kr), ("kpi", company_kpi),
                        ("objective", sales), ("objective", finance)):  # fmt: skip
        assert env.row(table, item["id"]).status == "DRAFT"
    assert env.activate("ceo", "key-results", company_kr["id"]).status_code == 200
    assert env.activate("ceo", "kpis", company_kpi["id"]).status_code == 200
    assert env.activate("quanly", "objectives", sales["id"]).status_code == 200


@pytest.mark.db
def test_document_draft_creator_cannot_self_activate_company_goal(env: Env) -> None:
    """SRS-GOAL-04: người tạo bản nháp từ tài liệu không tự kích hoạt Objective cấp công ty; CEO khác được."""
    document = uuid.uuid4()
    with env.owner.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO capture.source_document (id, uploaded_by, channel, storage_key, sha256, size_bytes) "
                "VALUES (:i, :u, 'C1', :k, :h, 1)"
            ),
            {"i": document, "u": env.users["ceo"], "k": f"t/{document}", "h": b"\x00" * 32},
        )
    from_document = env.objective("ceo", "ceo", None, "Từ tài liệu")
    manual = env.objective("ceo", "ceo", None, "Nhập tay")
    with env.owner.begin() as conn:
        conn.execute(text("UPDATE goals.objective SET source_document_id = :d WHERE id = :i"),
                     {"d": document, "i": from_document["id"]})  # fmt: skip
    self_activation = env.activate("ceo", "objectives", from_document["id"])
    assert self_activation.status_code == 403 and self_activation.json()["code"] == "FORBIDDEN"
    assert env.activate("ceo", "objectives", manual["id"]).status_code == 200
    other = env.activate("ceo2", "objectives", from_document["id"])
    assert other.status_code == 200 and env.row("objective", from_document["id"]).activated_by == env.users["ceo2"]


# ---------- TC-ACC-03 (phần mục tiêu, D-59) ----------


@pytest.mark.db
def test_manager_lists_only_goals_of_own_unit(env: Env) -> None:
    """TC-ACC-03 (phần mục tiêu): MANAGER đơn vị A liệt kê mục tiêu không thấy bản ghi đơn vị B (kể cả `ACTIVE`)."""
    sales = env.objective("ceo", "quanly_plain", "sales", "Kinh doanh")
    north = env.objective("ceo", "nv_bac", "north", "Miền Bắc")
    finance = env.objective("ceo", "quanly_kt", "finance", "Kế toán")
    sales_kpi = env.kpi("ceo", "nv_bac", "north", "KPI Bắc")
    finance_kpi = env.kpi("ceo", "quanly_kt", "finance", "KPI Kế toán")
    assert env.activate("quanly", "objectives", sales["id"]).status_code == 200
    with env.owner.begin() as conn:
        conn.execute(
            text("UPDATE goals.objective SET status = 'ACTIVE', activated_by = :u, activated_at = now() WHERE id = :i"),
            {"u": env.users["ceo"], "i": finance["id"]},
        )
    for who, mine, kpis, other_unit in (
        ("quanly", {sales["id"], north["id"]}, {sales_kpi["id"]}, env.units["finance"]),
        ("quanly_kt", {finance["id"]}, {finance_kpi["id"]}, env.units["sales"]),
    ):
        client = env.clients[who]
        assert {o["id"] for o in client.get("/api/v1/goals/objectives").json()} == mine, who
        active = {o["id"] for o in client.get("/api/v1/goals/objectives", params={"status": "ACTIVE"}).json()}
        assert active <= mine and len(active) == 1, who
        assert client.get("/api/v1/goals/objectives", params={"org_unit_id": str(other_unit)}).json() == [], who
        assert {k["id"] for k in client.get("/api/v1/goals/kpis").json()} == kpis, who
