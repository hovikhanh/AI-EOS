"""T-305: cấu hình autonomy trong trần (SRS-AIC-15, SRS-AIC-02; API-AI-03, API-AI-04, API-AI-05).

TC do T-305 làm chủ: TC-AIC-12 (`test_level_above_cap_rejected`). Liên quan TC-AIC-02 (chủ T-302): kiểm tra của code
khớp CSDL — `test_cap_check_rules` (code), `test_database_backstop_when_code_check_skipped` (trigger `AE030`/CHECK).

Session ADMIN: đăng nhập thật rồi đánh dấu `mfa_verified`/`reauth_at` trong CSDL (như `test_admin_api.py`).
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import PermissionGuard, grant_role
from aieos.ai import autonomy
from aieos.ai.api import build_ai_admin_router
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password, hash_token
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
POLICIES = "/api/v1/admin/ai/autonomy-policies"
TOOL_FIELDS = {
    "name", "module", "operation_type", "risk_level", "financial", "max_autonomy_level", "approval_required",
    "params_schema", "enabled",
}  # fmt: skip
POLICY_FIELDS = {
    "id", "tool_name", "role_code", "value_threshold", "level", "max_autonomy_level", "financial", "updated_by",
    "updated_at", "reason", "version",
}  # fmt: skip


@dataclass
class Env:
    engine: Engine
    owner: Engine
    app: Any

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

    def login(self, email: str, *, reauth: bool = True) -> TestClient:
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        client.headers[CSRF_HEADER] = response.json()["csrf_token"]
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE identity.session SET mfa_verified = true, "
                    "reauth_at = CASE WHEN :r THEN now() ELSE NULL END WHERE token_hash = :h"
                ),
                {"r": reauth, "h": hash_token(client.cookies[SESSION_COOKIE])},
            )
        return client

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()

    def policy(self, tool: str) -> tuple[uuid.UUID, int, int]:
        with self.engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, level, version FROM ai.autonomy_policy WHERE tool_name = :t AND role_code IS NULL"),
                {"t": tool},
            ).one()
        return row.id, row.level, row.version

    def add_tool(self, name: str, *, cap: int, financial: bool = False, level: int = 0) -> uuid.UUID:
        """Tool thử (chỉ trong CSDL test; không seed thật) cùng một policy mặc định."""
        policy_id = uuid.uuid4()
        with self.owner.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO ai.tool (name, module, operation_type, financial, max_autonomy_level) "
                    "VALUES (:n, 'finance', 'WRITE', :f, :c)"
                ),
                {"n": name, "f": financial, "c": cap},
            )
            conn.execute(
                text("INSERT INTO ai.autonomy_policy (id, tool_name, level) VALUES (:i, :n, :l)"),
                {"i": policy_id, "n": name, "l": level},
            )
        return policy_id

    def audits(self, outcome: str) -> list[Any]:
        with self.engine.connect() as conn:
            return list(
                conn.execute(
                    text(
                        "SELECT actor_user_id, resource_id, reason, changes, category FROM audit.event "
                        "WHERE action = 'ai.autonomy_policy.update' AND outcome = :o ORDER BY id"
                    ),
                    {"o": outcome},
                )
            )


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    owner = database.engine("aieos_owner")
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    guard = PermissionGuard(factory, auth.require_session, require_step_up=auth.require_step_up)
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_ai_admin_router(guard)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, owner, app)
    engine.dispose()
    owner.dispose()


def put(client: TestClient, policy_id: uuid.UUID, body: dict[str, Any], version: int | str | None) -> Any:
    headers = {} if version is None else {"If-Match": version if isinstance(version, str) else f'"{version}"'}
    return client.put(f"{POLICIES}/{policy_id}", json=body, headers=headers)


# ---------- Đọc (API-AI-03, API-AI-04) ----------


@pytest.mark.db
def test_admin_reads_tool_registry_and_policies(env: Env) -> None:
    env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    tools = client.get("/api/v1/admin/ai/tools")
    assert tools.status_code == 200, tools.text
    assert len(tools.json()) == 12 and all(set(t) == TOOL_FIELDS for t in tools.json())
    by_name = {t["name"]: t for t in tools.json()}
    assert by_name["create_task"]["max_autonomy_level"] == 3 and by_name["create_task"]["risk_level"] is None
    policies = client.get(POLICIES)
    assert policies.status_code == 200, policies.text
    items = policies.json()
    assert all(set(p) == POLICY_FIELDS for p in items)
    levels = {p["tool_name"]: p["level"] for p in items}
    assert levels["create_task"] == 3 and levels["search_documents"] == 0  # seed SRS-AIC-03, không đổi
    assert len(items) == env.scalar("SELECT count(*) FROM ai.autonomy_policy")


@pytest.mark.db
def test_non_admin_forbidden(env: Env) -> None:
    """Chỉ `config.autonomy` (ADMIN nền): role khác → `403` trên cả ba endpoint; policy không đổi, audit `DENIED`."""
    for index, role in enumerate(("CEO", "CFO", "MANAGER", "EMPLOYEE")):
        env.user(f"u{index}@example.com", (role,))
        client = env.login(f"u{index}@example.com")
        policy_id, level, version = env.policy("create_task")
        assert client.get("/api/v1/admin/ai/tools").status_code == 403
        assert client.get(POLICIES).status_code == 403
        response = put(client, policy_id, {"level": 2, "reason": "Thử"}, version)
        assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"
        assert env.policy("create_task") == (policy_id, level, version)
    denied = env.scalar(
        "SELECT count(*) FROM audit.event WHERE action = 'access.denied' AND outcome = 'DENIED' "
        "AND changes->>'permission' = 'config.autonomy'"
    )
    assert denied == 12


# ---------- Sửa (API-AI-05) ----------


@pytest.mark.db
def test_admin_sets_level_within_cap(env: Env) -> None:
    admin = env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    policy_id, level, version = env.policy("create_task")
    assert level == 3
    response = put(client, policy_id, {"level": 2, "reason": "Giảm tự chủ"}, version)
    assert response.status_code == 200, response.text
    body = response.json()
    assert response.headers["ETag"] == f'"{version + 1}"'
    assert body["level"] == 2 and body["version"] == version + 1 and body["reason"] == "Giảm tự chủ"
    assert body["updated_by"] == str(admin) and body["max_autonomy_level"] == 3
    assert env.policy("create_task") == (policy_id, 2, version + 1)
    [audit] = env.audits("SUCCESS")
    assert audit.actor_user_id == admin and audit.resource_id == str(policy_id) and audit.category == "ADMIN"
    assert audit.reason == "Giảm tự chủ"
    assert audit.changes == {"tool_name": "create_task", "role_code": None, "level": {"old": 3, "new": 2}}
    # Lên lại đúng trần (L3) được phép.
    assert put(client, policy_id, {"level": 3, "reason": "Khôi phục"}, version + 1).status_code == 200


@pytest.mark.db
def test_level_above_cap_rejected(env: Env) -> None:
    """TC-AIC-12: đặt autonomy vượt trần → `422 AUTONOMY_CAP_EXCEEDED`; policy không đổi; audit `FAILED`."""
    admin = env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    low = env.add_tool("tool_tran_l1", cap=1)
    financial = env.add_tool("tool_tai_chinh", cap=2, financial=True, level=2)
    task_id, _, task_version = env.policy("create_task")
    cases = [(low, 2, 1, 1), (financial, 3, 1, 2), (task_id, 4, task_version, 3), (task_id, 99, task_version, 3)]
    for policy_id, level, version, cap in cases:
        response = put(client, policy_id, {"level": level, "reason": "Vượt trần"}, version)
        assert response.status_code == 422, response.text
        # Chặn bởi code (thông điệp nêu trần) — CSDL là lớp thứ hai (`test_database_backstop_when_code_check_skipped`).
        assert response.json()["code"] == "AUTONOMY_CAP_EXCEEDED"
        assert response.json()["detail"] == f"Mức L{level} vượt trần L{cap} của tool"
    assert env.scalar("SELECT level FROM ai.autonomy_policy WHERE id = :i", {"i": low}) == 0
    assert env.scalar("SELECT level FROM ai.autonomy_policy WHERE id = :i", {"i": financial}) == 2
    assert env.policy("create_task") == (task_id, 3, task_version)
    failed = env.audits("FAILED")
    assert len(failed) == 4 and all(a.reason == "AUTONOMY_CAP_EXCEEDED" and a.actor_user_id == admin for a in failed)
    assert env.audits("SUCCESS") == []
    # Trong trần thì được: tool tài chính tối đa L2, tool trần L1 tối đa L1.
    assert put(client, low, {"level": 1, "reason": "Trong trần"}, 1).status_code == 200
    assert put(client, financial, {"level": 1, "reason": "Trong trần"}, 1).status_code == 200


@pytest.mark.db
def test_step_up_and_preconditions(env: Env) -> None:
    env.user("admin@example.com", ("ADMIN",))
    policy_id, level, version = env.policy("create_task")
    stale = env.login("admin@example.com", reauth=False)
    response = put(stale, policy_id, {"level": 2, "reason": "Thử"}, version)
    assert response.status_code == 401 and response.json()["code"] == "REAUTH_REQUIRED"
    assert stale.get(POLICIES).status_code == 200  # đọc không cần step-up
    client = env.login("admin@example.com")
    body = {"level": 2, "reason": "Thử"}
    assert put(client, policy_id, body, None).json()["code"] == "PRECONDITION_REQUIRED"
    response = put(client, policy_id, body, version + 1)
    assert response.status_code == 412 and response.json()["code"] == "VERSION_CONFLICT"
    assert put(client, uuid.uuid4(), body, 1).status_code == 404
    for bad in (
        {"level": -1, "reason": "Thử"},
        {"level": "2", "reason": "Thử"},
        {"level": 2, "reason": ""},
        {"level": 2},
        {"level": 2, "reason": "Thử", "value_threshold": "1000"},
        {"level": 2, "reason": "Thử", "tool_name": "approve_extraction"},
    ):
        response = put(client, policy_id, bad, version)
        assert response.status_code == 422 and response.json()["code"] == "VALIDATION_ERROR", bad
    assert env.policy("create_task") == (policy_id, level, version)
    assert [a.reason for a in env.audits("FAILED")] == ["VERSION_CONFLICT"]


@pytest.mark.db
def test_no_create_or_delete_endpoint(env: Env) -> None:
    """API-AI-05 chỉ sửa policy đã có: không có POST/DELETE (không tạo/xóa policy qua API)."""
    env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    policy_id, _, _ = env.policy("create_task")
    assert client.post(POLICIES, json={"tool_name": "create_task", "level": 1}).status_code == 405
    assert client.delete(f"{POLICIES}/{policy_id}").status_code == 405
    assert client.put("/api/v1/admin/ai/tools", json={}).status_code == 405


@pytest.mark.db
def test_database_backstop_when_code_check_skipped(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-AIC-02 (phần T-305): bỏ kiểm tra của code → CSDL vẫn chặn (`AE030`/CHECK) và API vẫn trả mã vượt trần."""
    env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    monkeypatch.setattr(autonomy, "check_within_cap", lambda *a, **k: None)
    financial = env.add_tool("tool_tai_chinh", cap=2, financial=True)
    task_id, _, task_version = env.policy("create_task")
    for policy_id, level, version in ((financial, 3, 1), (task_id, 4, task_version)):
        response = put(client, policy_id, {"level": level, "reason": "Vượt trần"}, version)
        assert response.status_code == 422 and response.json()["code"] == "AUTONOMY_CAP_EXCEEDED", response.text
    assert env.scalar("SELECT level FROM ai.autonomy_policy WHERE id = :i", {"i": financial}) == 0


# ---------- Quy tắc trần (không cần CSDL) ----------


@pytest.mark.parametrize(
    ("level", "cap", "financial", "allowed"),
    [
        (3, 3, False, True),
        (4, 3, False, False),  # không có L4 (D-11)
        (4, 4, False, False),  # trần tool sai cũng không vượt L3
        (2, 1, False, False),
        (1, 1, False, True),
        (0, 0, False, True),
        (2, 2, True, True),
        (3, 2, True, False),
        (3, 3, True, False),  # tài chính luôn ≤ L2 kể cả khi trần tool ghi sai (D-12)
    ],
)
def test_cap_check_rules(level: int, cap: int, financial: bool, allowed: bool) -> None:
    if allowed:
        autonomy.check_within_cap(level, max_autonomy_level=cap, financial=financial)
        return
    with pytest.raises(ApiError) as info:
        autonomy.check_within_cap(level, max_autonomy_level=cap, financial=financial)
    assert info.value.code == "AUTONOMY_CAP_EXCEEDED" and info.value.status == 422
