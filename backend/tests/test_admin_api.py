"""T-109: API quản trị tài khoản, role, assignment (SRS-ACC-05…08, SRS-IAM-11, SRS-AUD-01; API-ADM-01, 04…09).

TC do T-109 làm chủ: TC-ACC-04 (`test_admin_plus_cfo_rejected_by_api_and_database`), TC-ACC-05
(`test_self_role_and_assignment_change_rejected`), TC-ACC-06 (`test_two_admins_removing_each_other_keeps_one`),
TC-ACC-07 (`test_assignment_requires_eligible_role`), TC-ACC-08 (`test_role_change_revokes_target_sessions`),
TC-AUD-01 (`test_audit_success_denied_failed`).

Session ADMIN trong test: đăng nhập thật rồi đánh dấu `mfa_verified`/`reauth_at` trực tiếp trong CSDL (luồng MFA và
reauth đã kiểm ở T-103, T-104); `test_step_up_required_for_admin_writes` kiểm riêng việc thiếu reauth.
"""

import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.access.api import PermissionGuard, build_access_admin_router, grant_role
from aieos.identity.api import (
    Authenticator,
    AuthSettings,
    UserAdmin,
    build_auth_router,
    build_user_admin_router,
    hash_password,
    hash_token,
)
from aieos.platform.api import (
    CSRF_HEADER,
    IDEMPOTENCY_HEADER,
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


@dataclass
class Env:
    engine: Engine
    app: Any
    admin: UserAdmin
    database: ProvisionedDatabase

    def user(self, email: str, roles: tuple[str, ...] = ("EMPLOYEE",), status: str = "ACTIVE") -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                    "VALUES (:i, :e, 'Người dùng', :s, :p)"
                ),
                {"i": user_id, "e": email, "s": status, "p": None if status == "INVITED" else hash_password(PASSWORD)},
            )
        with transaction(make_session_factory(self.engine)) as session:
            for role in roles:
                grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
        return user_id

    def login(self, email: str, *, verified: bool = True, reauth: bool = True) -> TestClient:
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        client.headers[CSRF_HEADER] = response.json()["csrf_token"]
        if verified or reauth:
            with self.engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE identity.session SET mfa_verified = mfa_verified OR :v, "
                        "reauth_at = CASE WHEN :r THEN now() ELSE NULL END WHERE token_hash = :h"
                    ),
                    {"v": verified, "r": reauth, "h": hash_token(client.cookies[SESSION_COOKIE])},
                )
        return client

    def version(self, user_id: uuid.UUID) -> str:
        with self.engine.connect() as conn:
            value = conn.execute(text("SELECT version FROM identity.user_account WHERE id = :i"), {"i": user_id})
            return f'"{value.scalar_one()}"'

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, require_step_up=auth.require_step_up)
    admin = UserAdmin(auth)
    app = create_api(
        {},
        (
            build_auth_router(auth, KEY),
            build_user_admin_router(admin, guard),
            build_access_admin_router(guard, auth.revoke_sessions),
        ),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, app, admin, database)
    engine.dispose()


def put_roles(client: TestClient, env: Env, user_id: uuid.UUID, roles: list[str], reason: str = "Điều chỉnh") -> Any:
    return client.put(
        f"/api/v1/admin/users/{user_id}/roles",
        json={"roles": roles, "reason": reason},
        headers={"If-Match": env.version(user_id)},
    )


def assign(client: TestClient, body: dict[str, Any], key: str | None = None) -> Any:
    headers = {IDEMPOTENCY_HEADER: key or uuid.uuid4().hex}
    return client.post("/api/v1/admin/assignments", json={"reason": "Giao việc", **body}, headers=headers)


# ---------- TC-ACC-04 ----------


@pytest.mark.db
def test_admin_plus_cfo_rejected_by_api_and_database(env: Env) -> None:
    """TC-ACC-04: gán `ADMIN` cho tài khoản có `CFO` qua API → `422`; bằng SQL role ứng dụng → CSDL từ chối."""
    env.user("admin@example.com", ("ADMIN",))
    cfo = env.user("cfo@example.com", ("CFO",))
    client = env.login("admin@example.com")
    response = put_roles(client, env, cfo, ["CFO", "ADMIN"])
    assert response.status_code == 422 and response.json()["code"] == "ROLE_COMBINATION_FORBIDDEN"
    assert env.scalar("SELECT count(*) FROM access.user_role WHERE user_id = :u", {"u": cfo}) == 1
    with pytest.raises(DBAPIError) as info, env.engine.begin() as conn:
        conn.execute(text("INSERT INTO access.user_role (user_id, role_code) VALUES (:u, 'ADMIN')"), {"u": cfo})
    assert getattr(info.value.orig, "sqlstate", None) == "AE001"
    assert put_roles(client, env, cfo, ["ADMIN"]).status_code == 200  # thay CFO bằng ADMIN: gỡ trước, cấp sau


# ---------- TC-ACC-05 ----------


@pytest.mark.db
def test_self_role_and_assignment_change_rejected(env: Env) -> None:
    """TC-ACC-05: ADMIN tự đổi role/assignment của mình → `403 SELF_ROLE_CHANGE`; CHECK CSDL từ chối."""
    admin = env.user("admin@example.com", ("ADMIN",))
    env.user("admin2@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    response = put_roles(client, env, admin, ["ADMIN", "CEO"])
    assert response.status_code == 403 and response.json()["code"] == "SELF_ROLE_CHANGE"
    response = assign(client, {"user_id": str(admin), "permission": "extraction.review", "scope_type": "COMPANY"})
    assert response.status_code == 403 and response.json()["code"] == "SELF_ROLE_CHANGE"
    with pytest.raises(DBAPIError) as info, env.engine.begin() as conn:
        conn.execute(
            text("INSERT INTO access.user_role (user_id, role_code, granted_by, reason) VALUES (:u, 'CEO', :u, 'x')"),
            {"u": admin},
        )
    assert getattr(info.value.orig, "sqlstate", None) == "23514"


# ---------- TC-ACC-06 ----------


@pytest.mark.db
def test_two_admins_removing_each_other_keeps_one(env: Env) -> None:
    """TC-ACC-06: hai ADMIN gỡ ADMIN của nhau đồng thời → còn ≥ 1 ADMIN hoạt động; một thao tác `409 LAST_ADMIN`."""
    a = env.user("a@example.com", ("ADMIN",))
    b = env.user("b@example.com", ("ADMIN",))
    barrier = threading.Barrier(2)
    results: list[str] = []

    def remove(actor: uuid.UUID, target: uuid.UUID) -> None:
        version = env.admin.get(target).version
        barrier.wait()
        try:
            env.admin.set_roles(actor=actor, user_id=target, roles={"EMPLOYEE"}, reason="Gỡ", expected_version=version)
            results.append("ok")
        except ApiError as error:
            results.append(error.code)

    threads = [threading.Thread(target=remove, args=pair) for pair in ((a, b), (b, a))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["LAST_ADMIN", "ok"]
    assert env.scalar("SELECT count(*) FROM access.user_role WHERE role_code = 'ADMIN'") == 1


@pytest.mark.db
def test_disabling_last_admin_rejected(env: Env) -> None:
    admin = env.user("admin@example.com", ("ADMIN",))
    other = env.user("admin2@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    ok = client.patch(
        f"/api/v1/admin/users/{other}", json={"status": "DISABLED"}, headers={"If-Match": env.version(other)}
    )
    assert ok.status_code == 200 and ok.json()["status"] == "DISABLED"
    with pytest.raises(ApiError) as info:
        env.admin.set_status(actor=other, user_id=admin, status="LOCKED", reason=None, expected_version=1)
    assert info.value.code == "LAST_ADMIN"


# ---------- TC-ACC-07 ----------


@pytest.mark.db
def test_assignment_requires_eligible_role(env: Env) -> None:
    """TC-ACC-07: `finance.period.manage` cho người không có `CFO`; `finance.approve` cho ADMIN/CEO → `422`."""
    env.user("admin@example.com", ("ADMIN",))
    manager = env.user("ql@example.com", ("MANAGER",))
    ceo = env.user("ceo@example.com", ("CEO",))
    other_admin = env.user("admin2@example.com", ("ADMIN",))
    cfo = env.user("cfo@example.com", ("CFO",))
    client = env.login("admin@example.com")
    for user, permission in (
        (manager, "finance.period.manage"),
        (ceo, "finance.approve"),
        (other_admin, "finance.approve"),
    ):
        response = assign(client, {"user_id": str(user), "permission": permission, "scope_type": "COMPANY"})
        assert response.status_code == 422 and response.json()["code"] == "ASSIGNMENT_NOT_ELIGIBLE", permission
    created = assign(client, {"user_id": str(cfo), "permission": "finance.period.manage", "scope_type": "COMPANY"})
    assert created.status_code == 201 and created.json()["permission"] == "finance.period.manage"


# ---------- TC-ACC-08 ----------


@pytest.mark.db
def test_role_change_revokes_target_sessions(env: Env) -> None:
    """TC-ACC-08: đổi role của U đang có 2 session → request kế tiếp của U bị `401`."""
    env.user("admin@example.com", ("ADMIN",))
    target = env.user("nv@example.com")
    sessions = [env.login("nv@example.com", verified=False, reauth=False) for _ in range(2)]
    assert all(s.get("/api/v1/auth/me").status_code == 200 for s in sessions)
    client = env.login("admin@example.com")
    response = put_roles(client, env, target, ["MANAGER"])
    assert response.status_code == 200 and response.json()["roles"] == ["MANAGER"]
    assert response.headers["etag"] == env.version(target)
    for stale in sessions:
        result = stale.get("/api/v1/auth/me")
        assert result.status_code == 401 and result.json()["code"] == "UNAUTHENTICATED"
    assert client.get("/api/v1/auth/me").status_code == 200  # người thao tác không bị ảnh hưởng


@pytest.mark.db
def test_assignment_change_and_lock_revoke_sessions(env: Env) -> None:
    """SRS-IAM-11: giao/thu hồi assignment, khóa tài khoản → thu hồi session của tài khoản đích."""
    env.user("admin@example.com", ("ADMIN",))
    cfo = env.user("cfo@example.com", ("CFO",))
    client = env.login("admin@example.com")
    first = env.login("cfo@example.com", verified=False, reauth=False)
    created = assign(client, {"user_id": str(cfo), "permission": "finance.approve", "scope_type": "COMPANY"})
    assert created.status_code == 201
    assert first.get("/api/v1/auth/me").status_code == 401
    second = env.login("cfo@example.com", verified=False, reauth=False)
    assert client.delete(f"/api/v1/admin/assignments/{created.json()['id']}").status_code == 204
    assert second.get("/api/v1/auth/me").status_code == 401
    third = env.login("cfo@example.com", verified=False, reauth=False)
    locked = client.patch(
        f"/api/v1/admin/users/{cfo}", json={"status": "LOCKED"}, headers={"If-Match": env.version(cfo)}
    )
    assert locked.status_code == 200 and locked.json()["status"] == "LOCKED"
    assert third.get("/api/v1/auth/me").status_code == 401
    relogin = TestClient(env.app, base_url="https://testserver", headers={"Origin": ORIGIN})
    response = relogin.post("/api/v1/auth/login", json={"email": "cfo@example.com", "password": PASSWORD})
    assert response.status_code == 423
    unlocked = client.patch(
        f"/api/v1/admin/users/{cfo}", json={"status": "ACTIVE"}, headers={"If-Match": env.version(cfo)}
    )
    assert unlocked.status_code == 200
    assert third.get("/api/v1/auth/me").status_code == 401  # mở khóa không làm session cũ sống lại
    assert (
        relogin.post("/api/v1/auth/login", json={"email": "cfo@example.com", "password": PASSWORD}).status_code == 200
    )


# ---------- TC-AUD-01 ----------


@pytest.mark.db
def test_audit_success_denied_failed(env: Env) -> None:
    """TC-AUD-01: thao tác thành công, bị từ chối quyền, thất bại validation trên đối tượng nhạy cảm → 3 bản ghi audit
    `SUCCESS`, `DENIED`, `FAILED`."""
    env.user("admin@example.com", ("ADMIN",))
    env.user("nv@example.com")
    target = env.user("cfo@example.com", ("CFO",))
    admin = env.login("admin@example.com")
    employee = env.login("nv@example.com")

    assert put_roles(admin, env, target, ["CFO", "MANAGER"]).status_code == 200
    assert put_roles(employee, env, target, ["CEO"]).status_code == 403
    assert put_roles(admin, env, target, ["CFO", "ADMIN"]).status_code == 422
    with env.engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT action, outcome, reason FROM audit.event "
                "WHERE action IN ('access.role.grant', 'access.denied', 'access.role.set') AND actor_type = 'USER' "
                "ORDER BY id"
            )
        ).all()
    assert [(r.action, r.outcome, r.reason) for r in rows] == [
        ("access.role.grant", "SUCCESS", None),
        ("access.denied", "DENIED", "NO_PERMISSION"),
        ("access.role.set", "FAILED", "ROLE_COMBINATION_FORBIDDEN"),
    ]


# ---------- Còn lại của API-ADM-01, 04…09 ----------


@pytest.mark.db
def test_step_up_required_for_admin_writes(env: Env) -> None:
    env.user("admin@example.com", ("ADMIN",))
    target = env.user("nv@example.com")
    stale = env.login("admin@example.com", reauth=False)
    response = put_roles(stale, env, target, ["MANAGER"])
    assert response.status_code == 401 and response.json()["code"] == "REAUTH_REQUIRED"
    response = stale.patch(
        f"/api/v1/admin/users/{target}", json={"status": "LOCKED"}, headers={"If-Match": env.version(target)}
    )
    assert response.json()["code"] == "REAUTH_REQUIRED"
    assert (
        assign(stale, {"user_id": str(target), "permission": "extraction.review", "scope_type": "COMPANY"}).json()[
            "code"
        ]
        == "REAUTH_REQUIRED"
    )
    assert stale.get("/api/v1/admin/users").status_code == 200  # đọc không cần step-up
    employee = env.login("nv@example.com", reauth=False)
    assert put_roles(employee, env, target, ["MANAGER"]).status_code == 403  # không quyền → 403, không mời reauth


@pytest.mark.db
def test_if_match_and_status_rules(env: Env) -> None:
    admin = env.user("admin@example.com", ("ADMIN",))
    target = env.user("nv@example.com")
    invited = env.user("moi@example.com", status="INVITED")
    client = env.login("admin@example.com")
    path = f"/api/v1/admin/users/{target}"
    assert client.patch(path, json={"status": "LOCKED"}).json()["code"] == "PRECONDITION_REQUIRED"
    assert (
        client.patch(path, json={"status": "LOCKED"}, headers={"If-Match": '"99"'}).json()["code"] == "VERSION_CONFLICT"
    )
    response = client.patch(
        f"/api/v1/admin/users/{invited}", json={"status": "DISABLED"}, headers={"If-Match": env.version(invited)}
    )
    assert response.status_code == 409 and response.json()["code"] == "INVALID_STATE"
    response = client.patch(
        f"/api/v1/admin/users/{admin}", json={"status": "LOCKED"}, headers={"If-Match": env.version(admin)}
    )
    assert response.status_code == 403
    missing = client.patch(
        f"/api/v1/admin/users/{uuid.uuid4()}", json={"status": "LOCKED"}, headers={"If-Match": '"1"'}
    )
    assert missing.status_code == 404
    assert put_roles(client, env, target, ["KHONG_CO"]).json()["code"] == "VALIDATION_ERROR"


@pytest.mark.db
def test_list_users_roles_and_assignments(env: Env) -> None:
    env.user("admin@example.com", ("ADMIN",))
    cfo = env.user("cfo@example.com", ("CFO",))
    for n in range(3):
        env.user(f"nv{n}@example.com")
    client = env.login("admin@example.com")
    first = client.get("/api/v1/admin/users", params={"limit": 3}).json()
    second = client.get("/api/v1/admin/users", params={"limit": 3, "cursor": first["next_cursor"]}).json()
    emails = [u["email"] for u in first["items"] + second["items"]]
    assert sorted(emails) == sorted(
        ["admin@example.com", "cfo@example.com", "nv0@example.com", "nv1@example.com", "nv2@example.com"]
    )
    assert second["next_cursor"] is None
    assert not any("password" in key or "secret" in key for key in first["items"][0])

    roles = {r["code"]: r for r in client.get("/api/v1/admin/roles").json()}
    assert set(roles) == {"ADMIN", "CEO", "CFO", "MANAGER", "EMPLOYEE"}
    assert "finance.approve" in roles["CFO"]["eligible"] and "user.manage" in roles["ADMIN"]["base"]

    key = uuid.uuid4().hex
    body = {"user_id": str(cfo), "permission": "finance.approve", "scope_type": "COMPANY"}
    created = assign(client, body, key)
    replay = assign(client, body, key)
    assert created.status_code == replay.status_code == 201 and created.json()["id"] == replay.json()["id"]
    reused = assign(client, {**body, "reason": "Khác"}, key)
    assert reused.status_code == 409 and reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    missing_key = client.post("/api/v1/admin/assignments", json={"reason": "x", **body})
    assert missing_key.status_code == 400 and missing_key.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    bad_scope = assign(client, {**body, "scope_type": "ORG_UNIT"})
    assert bad_scope.status_code == 422 and bad_scope.json()["errors"][0]["field"] == "scope_id"
    assert env.scalar("SELECT count(*) FROM access.assignment") == 1

    listed = client.get("/api/v1/admin/assignments", params={"user_id": str(cfo)}).json()["items"]
    assert [a["id"] for a in listed] == [created.json()["id"]]
    assert client.get("/api/v1/admin/assignments", params={"permission": "finance.submit"}).json()["items"] == []
    assert client.delete(f"/api/v1/admin/assignments/{uuid.uuid4()}").status_code == 404
    assert client.delete(f"/api/v1/admin/assignments/{created.json()['id']}").status_code == 204
    revoked = client.get("/api/v1/admin/assignments").json()["items"][0]
    assert revoked["revoked_at"] is not None

    employee = env.login("nv0@example.com")
    for path in ("/api/v1/admin/users", "/api/v1/admin/roles", "/api/v1/admin/assignments"):
        assert employee.get(path).status_code == 403, path
