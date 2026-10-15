"""T-501: mục tiêu — Objective/KR/KPI bản nháp, đo lường, check-in, danh sách theo phạm vi (SRS-GOAL-01…03, 05…07, 09,
11; API-GOAL-01, 02, 03, 05, 06).

TC do T-501 làm chủ: TC-GOAL-01 (`test_create_drafts_with_sourced_fields`), TC-GOAL-03
(`test_measurement_has_period_and_source`),
TC-GOAL-04 (`test_check_in_own_kr_only`), TC-GOAL-05 (`test_kr_shows_numbers_without_percent`), TC-GOAL-06
(`test_manager_sees_team_check_ins_in_scope`). TC-GOAL-02 (DRAFT không ở ô chỉ số/Briefing/câu trả lời AI) chưa kiểm
được — các bề mặt đó chưa có (T-508, T-510, T-30x).
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.access.api import PermissionGuard, grant_role
from aieos.goals.api import build_goals_router
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password, hash_token
from aieos.org.api import OrgDirectoryScope, create_employee, create_unit, set_head
from aieos.platform.api import (
    CSRF_HEADER,
    IDEMPOTENCY_HEADER,
    SESSION_COOKIE,
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
    rate_limit_attempts=200,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=10,
    lockout_duration=timedelta(minutes=15),
    reauth=timedelta(minutes=5),
    password_min_length=12,
)


@dataclass
class Env:
    engine: Engine
    users: dict[str, uuid.UUID]
    units: dict[str, uuid.UUID]
    clients: dict[str, TestClient]

    def post(self, who: str, path: str, body: dict[str, Any], key: str | None = None) -> Any:
        return self.clients[who].post(
            f"/api/v1{path}", json=body, headers={IDEMPOTENCY_HEADER: key or uuid.uuid4().hex}
        )

    def objective(self, who: str, owner: str, unit: str | None = None, title: str = "Tăng doanh thu") -> dict[str, Any]:
        body = {"title": title, "owner_user_id": str(self.users[owner]), "period_label": "2026-Q4"}
        if unit:
            body["org_unit_id"] = str(self.units[unit])
        response = self.post(who, "/goals/objectives", body)
        assert response.status_code == 201, response.text
        return dict(response.json())

    def kr(self, who: str, objective: str, owner: str, metric: str = "Doanh thu") -> dict[str, Any]:
        body = {
            "objective_id": objective,
            "metric": metric,
            "baseline": "10",
            "target": "20",
            "unit": "tỷ đồng",
            "owner_user_id": str(self.users[owner]),
            "period_label": "2026-Q4",
        }
        response = self.post(who, "/goals/key-results", body)
        assert response.status_code == 201, response.text
        return dict(response.json())


def _user(engine: Engine, email: str, roles: tuple[str, ...], employee: uuid.UUID | None) -> uuid.UUID:
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, employee_id) "
                "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p, :emp)"
            ),
            {"i": user_id, "e": email, "p": hash_password(PASSWORD), "emp": employee},
        )
    with transaction(make_session_factory(engine)) as session:
        for role in roles:
            grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
    return user_id


def _login(app: Any, engine: Engine, email: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
    body = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()
    client.headers[CSRF_HEADER] = body["csrf_token"]
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE identity.session SET mfa_verified = true WHERE token_hash = :h"),
            {"h": hash_token(client.cookies[SESSION_COOKIE])},
        )
    return client


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    """Công ty ⊃ Kinh doanh (trưởng: quản lý) ⊃ Miền Bắc (nv_bac); Kế toán (nv_kt)."""
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    with transaction(factory) as session:
        company = create_unit(session, name="Công ty")
        sales = create_unit(session, name="Kinh doanh", parent_id=company)
        north = create_unit(session, name="Miền Bắc", parent_id=sales)
        finance = create_unit(session, name="Kế toán", parent_id=company)
        e_manager = create_employee(session, full_name="Quản Lý", org_unit_id=sales)
        e_bac = create_employee(session, full_name="Nhân Viên Bắc", org_unit_id=north)
        e_kt = create_employee(session, full_name="Nhân Viên Kế Toán", org_unit_id=finance)
        set_head(session, sales, e_manager)
    users = {
        "ceo": _user(engine, "ceo@example.com", ("CEO",), None),
        "quanly": _user(engine, "quanly@example.com", ("MANAGER",), e_manager),
        "nv_bac": _user(engine, "bac@example.com", ("EMPLOYEE",), e_bac),
        "nv_kt": _user(engine, "kt@example.com", ("EMPLOYEE",), e_kt),
    }
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, org=OrgDirectoryScope())
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_goals_router(guard)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    emails = {"ceo": "ceo", "quanly": "quanly", "nv_bac": "bac", "nv_kt": "kt"}
    clients = {k: _login(app, engine, f"{v}@example.com") for k, v in emails.items()}
    yield Env(engine, users, {"sales": sales, "north": north, "finance": finance, "company": company}, clients)
    engine.dispose()


# ---------- TC-GOAL-01 ----------


@pytest.mark.db
def test_create_drafts_with_sourced_fields(env: Env) -> None:
    """TC-GOAL-01: tạo Objective/KR/KPI thủ công → `DRAFT`, đủ thuộc tính có nguồn (SRS-GOAL-01, 02)."""
    objective = env.objective("quanly", "quanly", "sales")
    assert (objective["status"], objective["period_label"], objective["org_unit_id"]) == (
        "DRAFT",
        "2026-Q4",
        str(env.units["sales"]),
    )
    child = env.post(
        "quanly",
        "/goals/objectives",
        {"title": "Mở thị trường Bắc", "owner_user_id": str(env.users["nv_bac"]), "period_label": "2026-Q4",
         "org_unit_id": str(env.units["north"]), "parent_id": objective["id"]},
    ).json()  # fmt: skip
    assert child["parent_id"] == objective["id"]
    kr = env.kr("quanly", objective["id"], "nv_bac")
    assert (kr["status"], kr["baseline"], kr["target"], kr["unit"]) == ("DRAFT", "10", "20", "tỷ đồng")
    kpi = env.post(
        "quanly",
        "/goals/kpis",
        {"metric": "Số khách mới", "target": "50", "owner_user_id": str(env.users["quanly"]), "period_label": "2026-10",
         "org_unit_id": str(env.units["sales"])},
    )  # fmt: skip
    assert kpi.status_code == 201 and kpi.json()["status"] == "DRAFT" and kpi.json()["baseline"] is None
    for path, body in (
        ("/goals/objectives", {"owner_user_id": str(env.users["quanly"]), "period_label": "Q4"}),
        (
            "/goals/key-results",
            {
                "objective_id": objective["id"],
                "metric": "x",
                "owner_user_id": str(env.users["quanly"]),
                "period_label": "Q4",
            },
        ),
        ("/goals/kpis", {"metric": "x", "target": "1", "period_label": "Q4"}),
    ):  # fmt: skip
        assert env.post("quanly", path, body).status_code == 422, path
    outside = env.post(
        "quanly", "/goals/objectives", {"title": "X", "owner_user_id": str(env.users["nv_kt"]), "period_label": "Q4"}
    )
    assert outside.status_code == 403  # owner ngoài phạm vi
    ok_self = env.post(
        "nv_bac",
        "/goals/objectives",
        {"title": "Cá nhân", "owner_user_id": str(env.users["nv_bac"]), "period_label": "Q4"},
    )
    assert ok_self.status_code == 201


# ---------- TC-GOAL-03 ----------


@pytest.mark.db
def test_measurement_has_period_and_source(env: Env) -> None:
    """TC-GOAL-03: ghi giá trị đo gắn kỳ báo cáo và nguồn (người ghi; tài liệu nếu có)."""
    objective = env.objective("quanly", "quanly", "sales")
    kr = env.kr("quanly", objective["id"], "nv_bac")
    response = env.post(
        "nv_bac", f"/goals/key-results/{kr['id']}/measurements", {"value": "15.5", "report_period_label": "2026-10"}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["value"], body["report_period_label"], body["recorded_by"], body["source_document_id"]) == (
        "15.5", "2026-10", str(env.users["nv_bac"]), None,
    )  # fmt: skip
    missing = env.post("nv_bac", f"/goals/key-results/{kr['id']}/measurements", {"value": "1"})
    assert missing.status_code == 422
    bad_source = env.post(
        "nv_bac", f"/goals/key-results/{kr['id']}/measurements",
        {"value": "1", "report_period_label": "2026-10", "source_document_id": str(uuid.uuid4())},
    )  # fmt: skip
    assert bad_source.status_code == 422 and bad_source.json()["errors"][0]["field"] == "source_document_id"
    hidden = env.post(
        "nv_kt", f"/goals/key-results/{kr['id']}/measurements", {"value": "1", "report_period_label": "x"}
    )
    assert hidden.status_code == 404
    with pytest.raises(DBAPIError) as info, env.engine.begin() as conn:
        conn.execute(text("UPDATE goals.measurement SET value = 99"))
    assert "permission denied" in str(info.value)  # append-only


# ---------- TC-GOAL-04 ----------


@pytest.mark.db
def test_check_in_own_kr_only(env: Env) -> None:
    """TC-GOAL-04: check-in KR của mình → lưu đủ giá trị, độ tự tin, blocker, thời điểm; KR của người khác → `403`."""
    objective = env.objective("quanly", "quanly", "sales")
    kr = env.kr("quanly", objective["id"], "nv_bac")
    path = f"/goals/key-results/{kr['id']}/check-ins"
    response = env.post("nv_bac", path, {"value": "12", "confidence": 7, "blocker": "Chờ báo giá"})
    assert response.status_code == 201
    body = response.json()
    assert (body["value"], body["confidence"], body["blocker"]) == ("12", 7, "Chờ báo giá") and body["created_at"]
    other = env.post("quanly", path, {"value": "13", "confidence": 5})
    assert other.status_code == 403 and other.json()["code"] == "FORBIDDEN"
    for confidence in (-1, 11):
        assert env.post("nv_bac", path, {"value": "1", "confidence": confidence}).status_code == 422
    assert env.post("nv_kt", path, {"value": "1", "confidence": 5}).status_code == 404  # không thấy KR
    key = uuid.uuid4().hex
    first = env.post("nv_bac", path, {"value": "14", "confidence": 8}, key)
    replay = env.post("nv_bac", path, {"value": "14", "confidence": 8}, key)
    assert first.json() == replay.json()
    with env.engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM goals.check_in")).scalar_one() == 2


# ---------- TC-GOAL-05 ----------


@pytest.mark.db
def test_kr_shows_numbers_without_percent(env: Env) -> None:
    """TC-GOAL-05 (SRS-GOAL-09): KR có baseline 10, target 20, giá trị 15 → trả 3 số; không có % hay cảnh báo."""
    objective = env.objective("quanly", "quanly", "sales")
    kr = env.kr("quanly", objective["id"], "nv_bac")
    env.post("nv_bac", f"/goals/key-results/{kr['id']}/measurements", {"value": "15", "report_period_label": "2026-10"})
    listed = env.clients["quanly"].get("/api/v1/goals/objectives").json()
    item = listed[0]["key_results"][0]
    assert (item["baseline"], item["target"], item["latest_measurement"]["value"]) == ("10", "20", "15")
    flat = repr(listed).lower()
    for word in ("percent", "progress", "achievement", "warning", "alert", "%"):
        assert word not in flat, word
    assert set(item) == {
        "id", "objective_id", "metric", "baseline", "target", "unit", "owner_user_id", "period_label", "status",
        "version", "latest_measurement", "latest_check_in",
    }  # fmt: skip


# ---------- TC-GOAL-06 ----------


@pytest.mark.db
def test_manager_sees_team_check_ins_in_scope(env: Env) -> None:
    """TC-GOAL-06 (SRS-GOAL-11): MANAGER thấy check-in của team trong phạm vi, không thấy đơn vị khác."""
    sales_objective = env.objective("quanly", "quanly", "sales", title="Kinh doanh")
    sales_kr = env.kr("quanly", sales_objective["id"], "nv_bac")
    finance_objective = env.objective("ceo", "nv_kt", "finance", title="Kế toán")
    finance_kr = env.kr("ceo", finance_objective["id"], "nv_kt")
    env.post("nv_bac", f"/goals/key-results/{sales_kr['id']}/check-ins", {"value": "11", "confidence": 6})
    env.post("nv_kt", f"/goals/key-results/{finance_kr['id']}/check-ins", {"value": "3", "confidence": 2})
    manager = env.clients["quanly"].get("/api/v1/goals/objectives").json()
    assert [o["title"] for o in manager] == ["Kinh doanh"]
    assert manager[0]["key_results"][0]["latest_check_in"]["confidence"] == 6
    ceo = env.clients["ceo"].get("/api/v1/goals/objectives").json()
    assert {o["title"] for o in ceo} == {"Kinh doanh", "Kế toán"}
    assert [o["title"] for o in env.clients["nv_kt"].get("/api/v1/goals/objectives").json()] == ["Kế toán"]
    assert [o["title"] for o in env.clients["nv_bac"].get("/api/v1/goals/objectives").json()] == [
        "Kinh doanh"
    ]  # owner KR


# ---------- Sửa bản nháp, KPI ----------


@pytest.mark.db
def test_patch_only_drafts_with_if_match(env: Env) -> None:
    objective = env.objective("quanly", "quanly", "sales")
    path = f"/api/v1/goals/objectives/{objective['id']}"
    client = env.clients["quanly"]
    assert client.patch(path, json={"title": "Mới"}).json()["code"] == "PRECONDITION_REQUIRED"
    updated = client.patch(path, json={"title": "Mới"}, headers={"If-Match": '"1"'})
    assert updated.status_code == 200 and updated.json()["title"] == "Mới" and updated.headers["etag"] == '"2"'
    assert env.clients["nv_kt"].patch(path, json={"title": "X"}, headers={"If-Match": '"2"'}).status_code == 404
    with env.engine.begin() as conn:
        conn.execute(
            text("UPDATE goals.objective SET status = 'ACTIVE', activated_by = :u, activated_at = now() WHERE id = :i"),
            {"u": env.users["ceo"], "i": objective["id"]},
        )
    active = client.patch(path, json={"title": "Sửa khi đã kích hoạt"}, headers={"If-Match": '"2"'})
    assert active.status_code == 409 and active.json()["code"] == "INVALID_STATE"
    kpi = env.post(
        "quanly", "/goals/kpis",
        {"metric": "KPI", "target": "5", "owner_user_id": str(env.users["nv_bac"]), "period_label": "2026-10",
         "org_unit_id": str(env.units["north"])},
    ).json()  # fmt: skip
    env.post("nv_bac", f"/goals/kpis/{kpi['id']}/measurements", {"value": "4", "report_period_label": "2026-10"})
    kpis = env.clients["quanly"].get("/api/v1/goals/kpis").json()
    assert kpis[0]["latest_measurement"]["value"] == "4"
    assert env.clients["nv_kt"].get("/api/v1/goals/kpis").json() == []
    hidden = env.post(
        "nv_kt", f"/goals/kpis/{kpi['id']}/measurements", {"value": "1", "report_period_label": "2026-10"}
    )
    assert hidden.status_code == 404  # KPI ngoài phạm vi qua ID
