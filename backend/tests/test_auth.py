"""T-102: đăng nhập, session, đăng xuất, `/auth/me`, giới hạn thử (SRS-IAM-04, 06, 07, SRS-GEN-01; ADR-006).

TC do T-102 làm chủ: TC-IAM-01 (`test_login_sets_secure_session_cookie`), TC-IAM-02 (`test_session_fixation`),
TC-IAM-03 (`test_unknown_email_and_wrong_password_indistinguishable`), TC-IAM-04 (`test_rate_limit_and_lockout`),
TC-IAM-05 (`test_idle_and_absolute_expiry`), TC-GEN-06 (`test_every_endpoint_requires_session`). Phần đăng nhập của
TC-AUD-02 (chủ T-105, D-55): `test_login_audit_and_logs_have_no_secrets`.
"""

import base64
import hashlib
import io
import logging
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import grant_role
from aieos.app.asgi import PUBLIC_PATHS, create_app
from aieos.identity.api import Authenticator, AuthSettings, Principal, build_auth_router, hash_password
from aieos.platform.api import (
    SESSION_COOKIE,
    CsrfConfig,
    Secret,
    configure_logging,
    create_api,
    create_db_engine,
    csrf_token,
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
    rate_limit_attempts=5,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=3,
    lockout_duration=timedelta(minutes=15),
)


@dataclass
class Env:
    engine: Engine
    auth: Authenticator
    client: TestClient
    database: ProvisionedDatabase

    def user(self, email: str, *, status: str = "ACTIVE", roles: tuple[str, ...] = ("EMPLOYEE",)) -> uuid.UUID:
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


def build(engine: Engine, settings: AuthSettings = SETTINGS) -> tuple[Authenticator, TestClient]:
    auth = Authenticator(make_session_factory(engine), settings)
    protected = APIRouter()

    @protected.get("/probe/private")
    def private(principal: Principal = Depends(auth.require_session)) -> dict[str, str]:  # noqa: B008
        return {"user": str(principal.user_id)}

    app = create_api(
        {},
        (build_auth_router(auth, KEY), protected),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    return auth, TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    auth, client = build(engine)
    yield Env(engine, auth, client, database)
    engine.dispose()


def login(client: TestClient, email: str, password: str = PASSWORD) -> Any:
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def scalar(engine: Engine, sql: str, params: dict[str, object] | None = None) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


# ---------- TC-IAM-01 ----------


@pytest.mark.db
def test_login_sets_secure_session_cookie(env: Env) -> None:
    """TC-IAM-01: đăng nhập đúng (role không cần MFA) → session mới, cookie `__Host-` Secure HttpOnly SameSite=Lax."""
    user = env.user("an@example.com")
    response = login(env.client, "An@Example.com")
    body = response.json()
    assert response.status_code == 200 and (body["mfa_required"], body["mfa_enrolled"]) == (False, False)
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for attribute in ("Secure", "HttpOnly", "SameSite=lax", "Path=/"):
        assert attribute.lower() in cookie.lower(), attribute
    assert "domain=" not in cookie.lower()  # __Host-: không có Domain
    token = env.client.cookies[SESSION_COOKIE]
    assert len(token) == 43
    stored = scalar(env.engine, "SELECT token_hash FROM identity.session WHERE user_id = :u", {"u": user})
    assert bytes(stored) == hashlib.sha256(token.encode()).digest()  # INV-16
    me = env.client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["id"] == str(user) and body["roles"] == ["EMPLOYEE"]
    assert "record.submit" in body["permissions"] and "user.manage" not in body["permissions"]
    assert body["csrf_token"] == csrf_token(KEY, token)


# ---------- TC-IAM-02 ----------


@pytest.mark.db
def test_session_fixation(env: Env) -> None:
    """TC-IAM-02: ID sau đăng nhập khác ID trước (kể cả ID kẻ tấn công gài sẵn); ID cũ vô hiệu."""
    env.user("binh@example.com")

    def client_with(token: str | None) -> TestClient:
        cookies = {SESSION_COOKIE: token} if token else None
        return TestClient(env.client.app, base_url="https://testserver", headers={"Origin": ORIGIN}, cookies=cookies)

    planted = "gia-tri-ke-tan-cong-dat-san"
    first = session_token(login(client_with(planted), "binh@example.com"))
    assert first != planted
    second = session_token(login(client_with(first), "binh@example.com"))  # đăng nhập lại mang session cũ
    assert second != first
    assert client_with(first).get("/api/v1/auth/me").json()["code"] == "UNAUTHENTICATED"
    assert client_with(planted).get("/api/v1/auth/me").json()["code"] == "UNAUTHENTICATED"
    assert client_with(second).get("/api/v1/auth/me").status_code == 200
    assert scalar(env.engine, "SELECT count(*) FROM identity.session WHERE revoked_at IS NULL") == 1


def session_token(response: Any) -> str:
    assert response.status_code == 200, response.text
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(SESSION_COOKIE + "=")
    return str(cookie.split(";", 1)[0].split("=", 1)[1])


# ---------- TC-IAM-03 ----------


@pytest.mark.db
def test_unknown_email_and_wrong_password_indistinguishable(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-IAM-03: email không tồn tại và sai mật khẩu → cùng response; cùng chạy một lần kiểm tra Argon2."""
    import aieos.identity.auth as auth_module

    env.user("cuong@example.com")
    calls: list[str] = []
    real = auth_module._HASHER

    class CountingHasher:
        def verify(self, stored: str, password: str) -> bool:
            calls.append("verify")
            return bool(real.verify(stored, password))

        def __getattr__(self, name: str) -> Any:
            return getattr(real, name)

    monkeypatch.setattr(auth_module, "_HASHER", CountingHasher())
    unknown = login(env.client, "khong-ton-tai@example.com", "sai")
    unknown_calls = len(calls)
    wrong = login(env.client, "cuong@example.com", "sai")
    assert unknown_calls == 1 and len(calls) == 2
    assert unknown.status_code == wrong.status_code == 401

    def strip(body: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in body.items() if k != "correlation_id"}

    assert strip(unknown.json()) == strip(wrong.json())
    assert unknown.json()["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in unknown.headers and "set-cookie" not in wrong.headers


# ---------- TC-IAM-04 ----------


@pytest.mark.db
def test_rate_limit_and_lockout(env: Env) -> None:
    """TC-IAM-04: sai liên tục vượt ngưỡng → 429 + Retry-After; khóa tạm theo cấu hình (423 chỉ khi mật khẩu đúng)."""
    user = env.user("dung@example.com")
    for _ in range(2):
        assert login(env.client, "dung@example.com", "sai").status_code == 401
    assert scalar(env.engine, "SELECT failed_login_count FROM identity.user_account WHERE id = :u", {"u": user}) == 2
    assert login(env.client, "dung@example.com", "sai").status_code == 401  # lần thứ 3 = ngưỡng → khóa tạm
    assert scalar(env.engine, "SELECT locked_until > now() FROM identity.user_account WHERE id = :u", {"u": user})
    locked = login(env.client, "dung@example.com")
    assert locked.status_code == 423 and locked.json()["code"] == "ACCOUNT_LOCKED"  # mật khẩu đúng
    limited = login(env.client, "dung@example.com", "sai")  # lần thứ 5 trong cửa sổ vẫn được xử lý
    assert limited.status_code == 401  # mật khẩu sai khi đang khóa: không lộ trạng thái khóa
    blocked = login(env.client, "dung@example.com")
    assert blocked.status_code == 429 and blocked.json()["code"] == "RATE_LIMITED"
    assert int(blocked.headers["retry-after"]) > 0
    # Giới hạn theo IP: email khác từ cùng IP cũng bị chặn
    assert login(env.client, "nguoi-khac@example.com", "sai").status_code == 429
    # Hết khóa tạm → đăng nhập được (bộ đếm IP/tài khoản của tiến trình mới)
    with env.engine.begin() as conn:
        conn.execute(
            text("UPDATE identity.user_account SET locked_until = now() - interval '1 second' WHERE id = :u"),
            {"u": user},
        )
    _, fresh = build(env.engine)
    assert login(fresh, "dung@example.com").status_code == 200
    assert scalar(env.engine, "SELECT failed_login_count FROM identity.user_account WHERE id = :u", {"u": user}) == 0


@pytest.mark.db
def test_inactive_and_admin_locked_accounts(env: Env) -> None:
    env.user("invited@example.com", status="INVITED")
    disabled = env.user("disabled@example.com", roles=())
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE identity.user_account SET status = 'DISABLED' WHERE id = :u"), {"u": disabled})
    assert login(env.client, "invited@example.com").json()["code"] == "INVALID_CREDENTIALS"
    assert login(env.client, "disabled@example.com").json()["code"] == "INVALID_CREDENTIALS"
    locked = env.user("admin-locked@example.com", roles=())
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE identity.user_account SET status = 'LOCKED' WHERE id = :u"), {"u": locked})
    assert login(env.client, "admin-locked@example.com").status_code == 423
    assert login(env.client, "admin-locked@example.com", "sai").status_code == 401


# ---------- TC-IAM-05 ----------


@pytest.mark.db
def test_idle_and_absolute_expiry(env: Env) -> None:
    """TC-IAM-05: session nhàn rỗi / tuyệt đối hết hạn → 401 UNAUTHENTICATED; dùng session gia hạn nhàn rỗi."""
    user = env.user("em@example.com")
    assert login(env.client, "em@example.com").status_code == 200
    with env.engine.begin() as conn:
        conn.execute(
            text("UPDATE identity.session SET idle_expires_at = now() + interval '1 minute' WHERE user_id = :u"),
            {"u": user},
        )
    assert env.client.get("/api/v1/auth/me").status_code == 200
    extended = scalar(
        env.engine,
        "SELECT idle_expires_at > now() + interval '20 minutes' FROM identity.session WHERE user_id = :u",
        {"u": user},
    )
    assert extended  # trượt theo AIEOS_SESSION_IDLE_MINUTES
    with env.engine.begin() as conn:
        conn.execute(
            text("UPDATE identity.session SET idle_expires_at = now() - interval '1 second' WHERE user_id = :u"),
            {"u": user},
        )
    assert env.client.get("/api/v1/auth/me").json()["code"] == "UNAUTHENTICATED"
    assert login(env.client, "em@example.com").status_code == 200
    with env.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE identity.session SET absolute_expires_at = now() - interval '1 second', "
                "created_at = now() - interval '9 hours' WHERE user_id = :u AND revoked_at IS NULL"
            ),
            {"u": user},
        )
    response = env.client.get("/api/v1/auth/me")
    assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


# ---------- MFA, đăng xuất ----------


@pytest.mark.db
def test_admin_session_pending_mfa(env: Env) -> None:
    """SRS-IAM-04/05: ADMIN → session chờ MFA; chỉ đăng xuất (và API MFA — T-103) được phép."""
    env.user("quantri@example.com", roles=("ADMIN",))
    body = login(env.client, "quantri@example.com").json()
    assert (body["mfa_required"], body["mfa_enrolled"]) == (True, False)
    for path in ("/api/v1/auth/me", "/api/v1/probe/private"):
        response = env.client.get(path)
        assert response.status_code == 401 and response.json()["code"] == "MFA_REQUIRED"
    token = env.client.cookies[SESSION_COOKIE]
    assert body["csrf_token"] == csrf_token(KEY, token)  # session chờ MFA lấy token CSRF từ response đăng nhập (T-103)
    logout = env.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]})
    assert logout.status_code == 204


@pytest.mark.db
def test_logout_revokes_session(env: Env) -> None:
    env.user("giang@example.com")
    assert login(env.client, "giang@example.com").status_code == 200
    token = env.client.cookies[SESSION_COOKIE]
    assert env.client.post("/api/v1/auth/logout").status_code == 403  # thiếu CSRF khi có session
    response = env.client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token(KEY, token)})
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    stale = TestClient(env.client.app, base_url="https://testserver", cookies={SESSION_COOKIE: token})
    assert stale.get("/api/v1/auth/me").status_code == 401


# ---------- TC-AUD-02 (phần đăng nhập) ----------


@pytest.mark.db
def test_login_audit_and_logs_have_no_secrets(env: Env) -> None:
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    stream = io.StringIO()
    configure_logging(logging.DEBUG, stream=stream)
    try:
        user = env.user("hoa@example.com")
        login(env.client, "hoa@example.com", "mat-khau-sai-XYZ")
        login(env.client, "khong-co@example.com", "mat-khau-sai-ABC")
        login(env.client, "hoa@example.com")
        token = env.client.cookies[SESSION_COOKIE]
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
    with env.engine.connect() as conn:
        audit = conn.execute(
            text(
                "SELECT action, outcome, category, actor_user_id, reason FROM audit.event "
                "WHERE action LIKE 'auth.%' ORDER BY id"
            )
        ).all()
        dump = str(conn.execute(text("SELECT json_agg(e) FROM audit.event e")).scalar_one())
        attempts = str(conn.execute(text("SELECT json_agg(a) FROM identity.login_attempt a")).scalar_one())
    assert [tuple(r) for r in audit] == [
        ("auth.login", "DENIED", "SECURITY", user, "INVALID_CREDENTIALS"),
        ("auth.login", "DENIED", "SECURITY", None, "INVALID_CREDENTIALS"),
        ("auth.login", "SUCCESS", "SECURITY", user, None),
    ]
    for secret in ("mat-khau-sai-XYZ", "mat-khau-sai-ABC", PASSWORD, token, "hoa@example.com", "khong-co@example.com"):
        assert secret not in dump and secret not in attempts and secret not in stream.getvalue(), secret


# ---------- TC-GEN-06 ----------


def api_env(monkeypatch: pytest.MonkeyPatch, storage: Path, database_url: str) -> None:
    for name, value in {
        "AIEOS_DATABASE_URL": database_url,
        "AIEOS_CSRF_KEY": "k",
        "AIEOS_TOTP_ENCRYPTION_KEY": base64.b64encode(os.urandom(32)).decode(),  # khóa ngẫu nhiên mỗi lần chạy
        "AIEOS_STORAGE_PATH": str(storage),
        "AIEOS_ALLOWED_ORIGINS": ORIGIN,
        "AIEOS_SESSION_IDLE_MINUTES": "30",
        "AIEOS_SESSION_ABSOLUTE_HOURS": "8",
        "AIEOS_INVITE_TTL_HOURS": "1",
        "AIEOS_REAUTH_MINUTES": "5",
        "AIEOS_AUTH_RATE_LIMIT_ATTEMPTS": "5",
        "AIEOS_AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "AIEOS_AUTH_LOCKOUT_THRESHOLD": "5",
        "AIEOS_AUTH_LOCKOUT_MINUTES": "15",
        "AIEOS_PASSWORD_MIN_LENGTH": "12",
    }.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    yield
    root.handlers[:] = saved[0]
    root.setLevel(saved[1])


@pytest.mark.db
def test_every_endpoint_requires_session(
    database: ProvisionedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, restore_logging: None
) -> None:
    """TC-GEN-06: gọi mọi endpoint của ứng dụng không có session → 401, trừ đúng danh sách công khai (§1.2)."""
    migrate_to_head(database)
    api_env(monkeypatch, tmp_path, database.urls["aieos_app"].render_as_string(hide_password=False))
    app = create_app()
    client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
    seen: set[tuple[str, str]] = set()
    for path, operations in app.openapi()["paths"].items():  # FastAPI ≥ 0.142 lồng router: dùng OpenAPI từ code
        if not path.startswith("/api/v1"):
            continue
        for method in sorted(m.upper() for m in operations):
            seen.add((method, path))
            if (method, path) in PUBLIC_PATHS:
                continue
            concrete = path.replace("{", "").replace("}", "")
            response = client.request(method, concrete, json={})
            assert response.status_code == 401, (method, path, response.status_code)
            assert response.json()["code"] == "UNAUTHENTICATED"
    assert PUBLIC_PATHS <= seen  # danh sách công khai chỉ gồm route có thật
    assert ("GET", "/api/v1/auth/me") in seen and ("POST", "/api/v1/auth/logout") in seen


def test_create_app_rejects_invalid_auth_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, restore_logging: None
) -> None:
    api_env(monkeypatch, tmp_path, "postgresql://aieos_app:x@127.0.0.1:1/aieos")
    for name, value in (("AIEOS_AUTH_LOCKOUT_THRESHOLD", "0"), ("AIEOS_SESSION_IDLE_MINUTES", "ba-muoi")):
        monkeypatch.setenv(name, value)
        with pytest.raises(SystemExit) as info:
            create_app()
        assert info.value.code == 2
        api_env(monkeypatch, tmp_path, "postgresql://aieos_app:x@127.0.0.1:1/aieos")
