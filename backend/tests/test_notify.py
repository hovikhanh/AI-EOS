"""T-010: thông báo in-app — bảng `notify.notification`, service, API-NOT-01/02 (SRS-NTF-01, SRS-NTF-02).

Bằng chứng thành phần TC-NTF-01 (chủ T-510, D-58): thông báo chỉ tới đúng người nhận
(`test_only_recipient_sees_and_marks_notification`), liên kết chỉ nội bộ (`test_link_must_be_internal`). Nội dung không
nhạy cảm của từng sự kiện kiểm ở task phát sinh sự kiện (T-304, T-403, T-505).
"""

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from aieos.access.api import grant_role
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password
from aieos.notify.api import build_notify_router, notify
from aieos.platform.api import (
    CSRF_HEADER,
    SESSION_COOKIE,
    CsrfConfig,
    Secret,
    create_api,
    create_db_engine,
    decode_cursor,
    encode_cursor,
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
    rate_limit_attempts=50,
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

    def user(self, email: str, roles: tuple[str, ...] = ("EMPLOYEE",)) -> uuid.UUID:
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

    def notify(self, user_id: uuid.UUID, title: str = "Có task mới", link: str | None = "/tasks/1") -> uuid.UUID:
        with transaction(make_session_factory(self.engine)) as session:
            return notify(session, user_id=user_id, type="TASK_ASSIGNED", title=title, link=link)

    def client(self, email: str | None = None) -> TestClient:
        """Client riêng cho mỗi người dùng; có session thì kèm token CSRF lấy từ `/auth/me`."""
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        if email is not None:
            response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
            assert response.status_code == 200, response.text
            if not response.json()["mfa_required"]:
                client.headers[CSRF_HEADER] = client.get("/api/v1/auth/me").json()["csrf_token"]
        return client


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    app = create_api(
        {},
        (build_auth_router(auth, KEY), build_notify_router(factory, auth.require_session)),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, app)
    engine.dispose()


def items(response: Any) -> list[dict[str, Any]]:
    assert response.status_code == 200, response.text
    return list(response.json()["items"])


@pytest.mark.db
def test_only_recipient_sees_and_marks_notification(env: Env) -> None:
    """TC-NTF-01 (thành phần): A thấy và đánh dấu thông báo của A; B không thấy, không đánh dấu được (404)."""
    a = env.user("a@example.com")
    env.user("b@example.com")
    note = env.notify(a)
    client_a, client_b = env.client("a@example.com"), env.client("b@example.com")

    listed = items(client_a.get("/api/v1/notifications"))
    assert [i["id"] for i in listed] == [str(note)]
    assert listed[0] | {"created_at": None} == {
        "id": str(note),
        "type": "TASK_ASSIGNED",
        "title": "Có task mới",
        "body": None,
        "link": "/tasks/1",
        "created_at": None,
        "read_at": None,
    }
    assert items(client_b.get("/api/v1/notifications")) == []

    denied = client_b.post(f"/api/v1/notifications/{note}/read")
    assert denied.status_code == 404 and denied.json()["code"] == "NOT_FOUND"
    missing = client_a.post(f"/api/v1/notifications/{uuid.uuid4()}/read")
    assert missing.status_code == 404 and missing.json()["code"] == "NOT_FOUND"
    with env.engine.connect() as conn:
        assert conn.execute(text("SELECT read_at FROM notify.notification")).scalar_one() is None

    first = client_a.post(f"/api/v1/notifications/{note}/read")
    assert first.status_code == 200 and first.json()["read_at"] is not None
    again = client_a.post(f"/api/v1/notifications/{note}/read")
    assert again.status_code == 200 and again.json()["read_at"] == first.json()["read_at"]
    assert items(client_a.get("/api/v1/notifications"))[0]["read_at"] == first.json()["read_at"]


@pytest.mark.db
def test_endpoints_require_session_csrf_and_mfa(env: Env) -> None:
    """Không session → 401; thiếu token CSRF khi có session → 403; ADMIN chưa qua MFA → 401 MFA_REQUIRED."""
    user = env.user("a@example.com")
    note = env.notify(user)
    anonymous = env.client()
    for response in (anonymous.get("/api/v1/notifications"), anonymous.post(f"/api/v1/notifications/{note}/read")):
        assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"

    client = env.client("a@example.com")
    del client.headers[CSRF_HEADER]
    response = client.post(f"/api/v1/notifications/{note}/read")
    assert response.status_code == 403 and response.json()["code"] == "CSRF_FAILED"

    admin = env.user("admin@example.com", roles=("ADMIN",))
    env.notify(admin)
    pending = env.client("admin@example.com")
    assert SESSION_COOKIE in pending.cookies
    response = pending.get("/api/v1/notifications")
    assert response.status_code == 401 and response.json()["code"] == "MFA_REQUIRED"


@pytest.mark.db
def test_cursor_pagination(env: Env) -> None:
    """API_Specification §1.8: mặc định 20, tối đa 100, cursor; mới nhất trước, không trùng, không sót."""
    user = env.user("a@example.com")
    created = [env.notify(user, title=f"Thông báo {n}") for n in range(25)]
    client = env.client("a@example.com")

    page = client.get("/api/v1/notifications").json()
    assert len(page["items"]) == 20 and page["next_cursor"]
    cursor = None
    seen = []
    while True:
        response = client.get("/api/v1/notifications", params={"limit": 7} | ({"cursor": cursor} if cursor else {}))
        body = response.json()
        seen += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert sorted(seen) == sorted(str(c) for c in created) and len(set(seen)) == 25
    times = [i["created_at"] for i in client.get("/api/v1/notifications", params={"limit": 100}).json()["items"]]
    assert times == sorted(times, reverse=True)

    for params in ({"limit": 0}, {"limit": 101}, {"cursor": "khong-hop-le"}, {"cursor": encode_cursor(["x", "y"])}):
        response = client.get("/api/v1/notifications", params=params)
        assert response.status_code == 422 and response.json()["code"] == "VALIDATION_ERROR", params


def test_cursor_round_trip_and_rejects_garbage() -> None:
    assert decode_cursor(encode_cursor(["2026-10-15T00:00:00+00:00", "id"]), 2) == ["2026-10-15T00:00:00+00:00", "id"]
    for bad in ("", "!!!", encode_cursor(["a"]), encode_cursor(["a", "b", "c"])):
        with pytest.raises(Exception) as info:
            decode_cursor(bad, 2)
        assert getattr(info.value, "code", None) == "VALIDATION_ERROR"


@pytest.mark.db
def test_link_must_be_internal(env: Env) -> None:
    """Liên kết chỉ là đường dẫn nội bộ — chặn ở service và ở CSDL (CHECK)."""
    user = env.user("a@example.com")
    for link in ("/", "/tasks/1?x=1", None):
        env.notify(user, link=link)
    bad_links = ("https://evil.example", "//evil.example", "/\\evil.example", "tasks/1", "")
    for link in bad_links:
        with pytest.raises(ValueError):
            env.notify(user, link=link)
    with pytest.raises(ValueError):
        env.notify(user, title="")
    for link in bad_links:
        with pytest.raises(IntegrityError), env.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO notify.notification (id, user_id, type, title, link) "
                    "VALUES (gen_random_uuid(), :u, 'T', 'Tiêu đề', :l)"
                ),
                {"u": user, "l": link},
            )


@pytest.mark.db
def test_app_role_cannot_delete_notifications(env: Env) -> None:
    """Quyền mặc định của 0001: `aieos_app` không DELETE."""
    env.notify(env.user("a@example.com"))
    with pytest.raises(DBAPIError) as info, env.engine.begin() as conn:
        conn.execute(text("DELETE FROM notify.notification"))
    assert "permission denied" in str(info.value)
