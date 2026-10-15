"""T-505: task (SRS-WRK-01…04, SRS-WRK-10; API-WORK-01, 03, 04, 05).

TC do T-505 làm chủ: TC-WRK-01 (`test_create_requires_owner_due_and_title`), TC-WRK-02 (`test_overdue_and_on_time`),
TC-WRK-03 (`test_only_owner_or_assigner_completes_and_assigner_reopens`), TC-WRK-04
(`test_employee_only_assigns_to_self`), TC-WRK-05 (`test_listing_follows_role_scope`). TC-ACC-03 (chủ T-505 tổng, D-59):
phần task ở `test_listing_follows_role_scope`; phần mục tiêu thuộc T-502 → chưa ghi PASS. TC-NTF-01 (chủ T-510): phần
giao task ở `test_assignment_notifies_owner_without_task_content`.
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import PermissionGuard, grant_role
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password, hash_token
from aieos.notify.api import build_notify_router
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
from aieos.work.api import build_work_router
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
FUTURE = (date.today() + timedelta(days=7)).isoformat()


@dataclass
class Env:
    engine: Engine
    app: Any
    users: dict[str, uuid.UUID]
    clients: dict[str, TestClient]

    def task(self, who: str, owner: str, title: str = "Việc cần làm", due: str = FUTURE) -> Any:
        response = self.clients[who].post(
            "/api/v1/work/tasks",
            json={"title": title, "owner_user_id": str(self.users[owner]), "due_date": due},
            headers={IDEMPOTENCY_HEADER: uuid.uuid4().hex},
        )
        return response

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()


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
    """Công ty ⊃ Kinh doanh (trưởng: quản lý) ⊃ Miền Bắc (nv_bac); Kế toán (nv_ketoan)."""
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
        e_kd = create_employee(session, full_name="Nhân Viên Kinh Doanh", org_unit_id=sales)
        set_head(session, sales, e_manager)
    users = {
        "ceo": _user(engine, "ceo@example.com", ("CEO",), None),
        "quanly": _user(engine, "quanly@example.com", ("MANAGER",), e_manager),
        "nv_bac": _user(engine, "bac@example.com", ("EMPLOYEE",), e_bac),
        "nv_kd": _user(engine, "kd@example.com", ("EMPLOYEE",), e_kd),
        "nv_ketoan": _user(engine, "ketoan@example.com", ("EMPLOYEE",), e_kt),
    }
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, org=OrgDirectoryScope())
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_work_router(guard), build_notify_router(factory, auth.require_session)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    emails = {"ceo": "ceo", "quanly": "quanly", "nv_bac": "bac", "nv_kd": "kd", "nv_ketoan": "ketoan"}
    clients = {k: _login(app, engine, f"{v}@example.com") for k, v in emails.items()}
    yield Env(engine, app, users, clients)
    engine.dispose()


def titles(response: Any) -> set[str]:
    assert response.status_code == 200, response.text
    return {t["title"] for t in response.json()["items"]}


# ---------- TC-WRK-01 ----------


@pytest.mark.db
def test_create_requires_owner_due_and_title(env: Env) -> None:
    """TC-WRK-01: thiếu owner, hạn hoặc tiêu đề → `422`."""
    client = env.clients["quanly"]
    owner = str(env.users["nv_bac"])
    for body in (
        {"title": "A", "due_date": FUTURE},
        {"title": "A", "owner_user_id": owner},
        {"title": "", "owner_user_id": owner, "due_date": FUTURE},
        {"title": "   ", "owner_user_id": owner, "due_date": FUTURE},
        {"title": "A", "owner_user_id": str(uuid.uuid4()), "due_date": FUTURE},
    ):
        response = client.post("/api/v1/work/tasks", json=body, headers={IDEMPOTENCY_HEADER: uuid.uuid4().hex})
        assert response.status_code == 422 and response.json()["code"] == "VALIDATION_ERROR", body
    assert env.scalar("SELECT count(*) FROM work.task") == 0
    created = env.task("quanly", "nv_bac", title="Chuẩn bị báo cáo")
    assert created.status_code == 201 and created.headers["etag"] == '"1"'
    assert (created.json()["status"], created.json()["assigned_by"]) == ("OPEN", str(env.users["quanly"]))


# ---------- TC-WRK-02 ----------


@pytest.mark.db
def test_overdue_and_on_time(env: Env) -> None:
    """TC-WRK-02: task `OPEN` quá hạn → trễ; hoàn thành sau hạn → không đúng hạn; trước hạn → đúng hạn."""
    late = env.task("quanly", "nv_bac", title="Trễ").json()
    ontime = env.task("quanly", "nv_bac", title="Đúng hạn").json()
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE work.task SET due_date = current_date - 2 WHERE id = :i"), {"i": late["id"]})
    owner = env.clients["nv_bac"]
    listed = {t["title"]: t for t in owner.get("/api/v1/work/tasks").json()["items"]}
    assert listed["Trễ"]["overdue"] is True and listed["Đúng hạn"]["overdue"] is False
    assert titles(owner.get("/api/v1/work/tasks", params={"overdue": "true"})) == {"Trễ"}
    done_late = owner.post(f"/api/v1/work/tasks/{late['id']}/complete", headers={"If-Match": '"2"'})
    assert done_late.status_code == 412  # version vẫn 1 (UPDATE trực tiếp không tăng version)
    done_late = owner.post(f"/api/v1/work/tasks/{late['id']}/complete", headers={"If-Match": '"1"'})
    assert done_late.status_code == 200
    assert (done_late.json()["overdue"], done_late.json()["completed_on_time"]) == (False, False)
    today = env.task("quanly", "nv_bac", title="Hạn hôm nay", due=date.today().isoformat()).json()
    with env.engine.begin() as conn:  # "hôm nay" theo giờ Việt Nam
        conn.execute(
            text("UPDATE work.task SET due_date = (now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date WHERE id = :i"),
            {"i": today["id"]},
        )
    assert {t["title"]: t for t in owner.get("/api/v1/work/tasks").json()["items"]}["Hạn hôm nay"]["overdue"] is False
    done_ok = owner.post(f"/api/v1/work/tasks/{ontime['id']}/complete", headers={"If-Match": '"1"'})
    assert done_ok.json()["completed_on_time"] is True and done_ok.json()["completed_by"] == str(env.users["nv_bac"])


# ---------- TC-WRK-03 ----------


@pytest.mark.db
def test_only_owner_or_assigner_completes_and_assigner_reopens(env: Env) -> None:
    """TC-WRK-03: người không phải owner/người giao (dù thấy task) hoàn thành → `403`; mở lại chỉ người giao (Q-33)."""
    task = env.task("quanly", "nv_bac").json()
    path = f"/api/v1/work/tasks/{task['id']}"
    ceo = env.clients["ceo"].post(f"{path}/complete", headers={"If-Match": '"1"'})
    assert ceo.status_code == 403 and ceo.json()["code"] == "FORBIDDEN"
    other = env.clients["nv_ketoan"].post(f"{path}/complete", headers={"If-Match": '"1"'})
    assert other.status_code == 404  # không thấy task → không lộ tồn tại
    done = env.clients["nv_bac"].post(f"{path}/complete", headers={"If-Match": '"1"'})
    assert done.status_code == 200 and done.json()["status"] == "DONE"
    again = env.clients["nv_bac"].post(f"{path}/complete", headers={"If-Match": '"2"'})
    assert again.status_code == 409 and again.json()["code"] == "INVALID_STATE"
    reopen_by_owner = env.clients["nv_bac"].post(f"{path}/reopen", headers={"If-Match": '"2"'})
    assert reopen_by_owner.status_code == 403
    reopened = env.clients["quanly"].post(f"{path}/reopen", headers={"If-Match": '"2"'})
    assert reopened.status_code == 200 and reopened.json()["status"] == "OPEN"
    assert reopened.json()["completed_at"] is None and reopened.json()["completed_by"] is None
    assert env.clients["quanly"].post(f"{path}/reopen").json()["code"] == "PRECONDITION_REQUIRED"


# ---------- TC-WRK-04 ----------


@pytest.mark.db
def test_employee_only_assigns_to_self(env: Env) -> None:
    """TC-WRK-04: EMPLOYEE giao task cho người khác → từ chối (mặc định PROPOSED SRS-WRK-04); tự giao → được."""
    refused = env.task("nv_bac", "nv_kd")
    assert refused.status_code == 403 and refused.json()["code"] == "FORBIDDEN"
    assert env.task("nv_bac", "nv_bac").status_code == 201
    outside = env.task("quanly", "nv_ketoan")  # MANAGER giao ra ngoài đơn vị mình làm trưởng
    assert outside.status_code == 403
    assert env.task("ceo", "nv_ketoan").status_code == 201  # CEO: toàn công ty


# ---------- TC-WRK-05, TC-ACC-03 (phần task) ----------


@pytest.mark.db
def test_listing_follows_role_scope(env: Env) -> None:
    """TC-WRK-05 / TC-ACC-03 (phần task): CEO thấy tất cả; MANAGER thấy task của đơn vị mình làm trưởng và cấp dưới,
    không thấy đơn vị khác; EMPLOYEE chỉ thấy task của mình hoặc mình giao. Đọc ngoài phạm vi qua ID → `404`."""
    env.task("quanly", "nv_bac", title="Bắc")
    env.task("quanly", "nv_kd", title="Kinh doanh")
    kt = env.task("ceo", "nv_ketoan", title="Kế toán").json()
    env.task("nv_bac", "nv_bac", title="Tự giao")
    assert titles(env.clients["ceo"].get("/api/v1/work/tasks")) == {"Bắc", "Kinh doanh", "Kế toán", "Tự giao"}
    assert titles(env.clients["quanly"].get("/api/v1/work/tasks")) == {"Bắc", "Kinh doanh", "Tự giao"}
    assert titles(env.clients["nv_bac"].get("/api/v1/work/tasks")) == {"Bắc", "Tự giao"}
    assert titles(env.clients["nv_ketoan"].get("/api/v1/work/tasks")) == {"Kế toán"}
    hidden = env.clients["quanly"].patch(
        f"/api/v1/work/tasks/{kt['id']}", json={"title": "X"}, headers={"If-Match": '"1"'}
    )
    assert hidden.status_code == 404 and hidden.json()["code"] == "NOT_FOUND"
    ceo = env.clients["ceo"]
    sales_unit = env.scalar("SELECT id FROM org.org_unit WHERE name = 'Kinh doanh'")
    assert titles(ceo.get("/api/v1/work/tasks", params={"org_unit_id": str(sales_unit)})) == {
        "Bắc",
        "Kinh doanh",
        "Tự giao",
    }
    assert titles(ceo.get("/api/v1/work/tasks", params={"owner_user_id": str(env.users["nv_kd"])})) == {"Kinh doanh"}
    first = ceo.get("/api/v1/work/tasks", params={"limit": 3}).json()
    second = ceo.get("/api/v1/work/tasks", params={"limit": 3, "cursor": first["next_cursor"]}).json()
    assert len(first["items"]) == 3 and len(second["items"]) == 1 and second["next_cursor"] is None


# ---------- Sửa, idempotency, thông báo, audit ----------


@pytest.mark.db
def test_update_rules_and_idempotency(env: Env) -> None:
    client = env.clients["quanly"]
    key = uuid.uuid4().hex
    body = {"title": "Gốc", "owner_user_id": str(env.users["nv_bac"]), "due_date": FUTURE}
    first = client.post("/api/v1/work/tasks", json=body, headers={IDEMPOTENCY_HEADER: key})
    replay = client.post("/api/v1/work/tasks", json=body, headers={IDEMPOTENCY_HEADER: key})
    assert first.status_code == replay.status_code == 201 and first.json()["id"] == replay.json()["id"]
    reused = client.post("/api/v1/work/tasks", json={**body, "title": "Khác"}, headers={IDEMPOTENCY_HEADER: key})
    assert reused.status_code == 409 and reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    path = f"/api/v1/work/tasks/{first.json()['id']}"
    by_owner = env.clients["nv_bac"].patch(path, json={"title": "Owner sửa"}, headers={"If-Match": '"1"'})
    assert by_owner.status_code == 200 and by_owner.json()["version"] == 2
    owner_change = env.clients["nv_bac"].patch(
        path, json={"owner_user_id": str(env.users["nv_kd"])}, headers={"If-Match": '"2"'}
    )
    assert owner_change.status_code == 403  # chỉ người giao đổi owner
    by_ceo = env.task("ceo", "quanly", title="Giao cho quản lý").json()  # owner là MANAGER, có phạm vi rộng
    manager_moves = client.patch(
        f"/api/v1/work/tasks/{by_ceo['id']}",
        json={"owner_user_id": str(env.users["nv_bac"])},
        headers={"If-Match": '"1"'},
    )
    assert manager_moves.status_code == 403  # owner không phải người giao → không đổi owner dù người mới trong phạm vi
    moved = client.patch(path, json={"owner_user_id": str(env.users["nv_kd"])}, headers={"If-Match": '"2"'})
    assert moved.status_code == 200 and moved.json()["owner_user_id"] == str(env.users["nv_kd"])
    stale = client.patch(path, json={"title": "Cũ"}, headers={"If-Match": '"2"'})
    assert stale.status_code == 412
    assert env.scalar("SELECT count(*) FROM work.task") == 2
    assert (
        env.scalar("SELECT count(*) FROM audit.event WHERE resource_type = 'work.task' AND category = 'BUSINESS'") == 4
    )


@pytest.mark.db
def test_assignment_notifies_owner_without_task_content(env: Env) -> None:
    """TC-NTF-01 (phần giao task): người được giao nhận thông báo; không chép tiêu đề task; tự giao không thông báo."""
    task = env.task("quanly", "nv_bac", title="Hợp đồng 1.250.000.000 đ với khách A").json()
    env.task("nv_kd", "nv_kd", title="Tự giao")
    notes = env.clients["nv_bac"].get("/api/v1/notifications").json()["items"]
    assert len(notes) == 1
    note = notes[0]
    assert (note["type"], note["link"]) == ("TASK_ASSIGNED", f"/work/tasks/{task['id']}")
    assert "1.250.000.000" not in note["title"] and "khách A" not in note["title"]
    assert env.clients["nv_kd"].get("/api/v1/notifications").json()["items"] == []
    assert env.clients["quanly"].get("/api/v1/notifications").json()["items"] == []


@pytest.mark.db
def test_admin_without_data_read_cannot_use_tasks(env: Env) -> None:
    _user(env.engine, "admin@example.com", ("ADMIN",), None)
    admin = _login(env.app, env.engine, "admin@example.com")
    assert admin.get("/api/v1/work/tasks").status_code == 403
    response = admin.post(
        "/api/v1/work/tasks",
        json={"title": "A", "owner_user_id": str(env.users["nv_bac"]), "due_date": FUTURE},
        headers={IDEMPOTENCY_HEADER: uuid.uuid4().hex},
    )
    assert response.status_code == 403
