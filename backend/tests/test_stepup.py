"""T-104: xác thực lại (step-up) và đổi mật khẩu (SRS-IAM-08, SRS-IAM-11; API-AUTH-05, API-AUTH-09).

TC do T-104 làm chủ: TC-IAM-08 (`test_step_up_requires_reauth_and_password_change_revokes_other_sessions`). Phần đổi
mật khẩu của TC-AUD-02 (chủ T-105, D-55): `test_password_change_audit_and_logs_have_no_secrets`.
"""

import base64
import io
import logging
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import grant_role
from aieos.identity.api import (
    Authenticator,
    AuthSettings,
    MfaService,
    StepUpService,
    build_auth_router,
    build_mfa_router,
    build_stepup_router,
    hash_password,
    verify_password,
)
from aieos.identity.mfa import current_step, totp
from aieos.platform.api import (
    CSRF_HEADER,
    SESSION_COOKIE,
    CsrfConfig,
    Secret,
    configure_logging,
    create_api,
    create_db_engine,
    make_session_factory,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head

ORIGIN = "https://aieos.local"
KEY = Secret("khoa-csrf-test")
TOTP_KEY = os.urandom(32)
PASSWORD = "Mat-khau-dung-123!"
NEW_PASSWORD = "Mat-khau-moi-456!"
SETTINGS = AuthSettings(
    idle=timedelta(minutes=30),
    absolute=timedelta(hours=8),
    rate_limit_attempts=5,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=10,
    lockout_duration=timedelta(minutes=15),
    reauth=timedelta(minutes=5),
    password_min_length=12,
)


@dataclass
class Clock:
    now: float = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@dataclass
class Env:
    engine: Engine
    app: Any
    clock: Clock = field(default_factory=Clock)

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

    def login(self, email: str, password: str = PASSWORD) -> TestClient:
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        client.headers[CSRF_HEADER] = response.json()["csrf_token"]
        return client

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()


def code_of(env: Env, secret: bytes, offset: int = 0) -> str:
    return totp(secret, current_step(env.clock.now) + offset)


def refresh_csrf(client: TestClient) -> None:
    client.headers[CSRF_HEADER] = client.get("/api/v1/auth/me").json()["csrf_token"]


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    clock = Clock()
    mfa = MfaService(auth, TOTP_KEY, clock)
    app = create_api(
        {},
        (
            build_auth_router(auth, KEY),
            build_mfa_router(auth, mfa),
            build_stepup_router(auth, StepUpService(auth, mfa)),
        ),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, app, clock)
    engine.dispose()


def enrolled_admin(env: Env) -> tuple[TestClient, bytes]:
    env.user("admin@example.com", ("ADMIN",))
    client = env.login("admin@example.com")
    secret_text = client.post("/api/v1/auth/mfa/enroll").json()["secret"]
    secret = base64.b32decode(secret_text + "=" * (-len(secret_text) % 8))
    assert client.post("/api/v1/auth/mfa/enroll/confirm", json={"code": code_of(env, secret)}).status_code == 200
    refresh_csrf(client)
    return client, secret


# ---------- TC-IAM-08 ----------


@pytest.mark.db
def test_step_up_requires_reauth_and_password_change_revokes_other_sessions(env: Env) -> None:
    """TC-IAM-08: thao tác STEP-UP không reauth → `401 REAUTH_REQUIRED`; đổi mật khẩu khi có 2 session khác → các
    session khác bị thu hồi, session hiện tại giữ nguyên."""
    user = env.user("nv@example.com")
    current, other1, other2 = (env.login("nv@example.com") for _ in range(3))

    denied = current.post("/api/v1/auth/password", json={"new_password": NEW_PASSWORD})
    assert denied.status_code == 401 and denied.json()["code"] == "REAUTH_REQUIRED"
    assert verify_password(
        env.scalar("SELECT password_hash FROM identity.user_account WHERE id = :u", {"u": user}), PASSWORD
    )

    assert current.post("/api/v1/auth/reauth", json={"password": PASSWORD}).status_code == 204
    assert current.post("/api/v1/auth/password", json={"new_password": NEW_PASSWORD}).status_code == 204

    for stale in (other1, other2):
        response = stale.get("/api/v1/auth/me")
        assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"
    assert current.get("/api/v1/auth/me").status_code == 200
    assert env.scalar("SELECT count(*) FROM identity.session WHERE revoked_at IS NULL") == 1
    stored = env.scalar("SELECT password_hash FROM identity.user_account WHERE id = :u", {"u": user})
    assert verify_password(stored, NEW_PASSWORD) and not verify_password(stored, PASSWORD)
    env.login("nv@example.com", NEW_PASSWORD)
    old = TestClient(env.app, base_url="https://testserver", headers={"Origin": ORIGIN})
    assert old.post("/api/v1/auth/login", json={"email": "nv@example.com", "password": PASSWORD}).status_code == 401


@pytest.mark.db
def test_reauth_window_expires_and_is_per_session(env: Env) -> None:
    env.user("nv@example.com")
    first, second = env.login("nv@example.com"), env.login("nv@example.com")
    assert first.post("/api/v1/auth/reauth", json={"password": PASSWORD}).status_code == 204
    response = second.post("/api/v1/auth/password", json={"new_password": NEW_PASSWORD})
    assert response.json()["code"] == "REAUTH_REQUIRED"  # reauth gắn với session, không với tài khoản
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE identity.session SET reauth_at = now() - interval '6 minutes'"))
    response = first.post("/api/v1/auth/password", json={"new_password": NEW_PASSWORD})
    assert response.status_code == 401 and response.json()["code"] == "REAUTH_REQUIRED"


@pytest.mark.db
def test_reauth_rejects_wrong_password_and_validates_new_password(env: Env) -> None:
    env.user("nv@example.com")
    client = env.login("nv@example.com")
    wrong = client.post("/api/v1/auth/reauth", json={"password": "sai-mat-khau-hoan-toan"})
    assert wrong.status_code == 401 and wrong.json()["code"] == "INVALID_CREDENTIALS"
    assert env.scalar("SELECT count(*) FROM identity.session WHERE reauth_at IS NOT NULL") == 0
    assert client.post("/api/v1/auth/reauth", json={"password": PASSWORD}).status_code == 204
    short = client.post("/api/v1/auth/password", json={"new_password": "ngan"})
    assert short.status_code == 422 and short.json()["errors"][0]["field"] == "new_password"
    assert "ngan" not in short.text.replace("ngắn", "")


@pytest.mark.db
def test_reauth_with_mfa_requires_unused_code(env: Env) -> None:
    client, secret = enrolled_admin(env)
    env.clock.now += 90
    no_code = client.post("/api/v1/auth/reauth", json={"password": PASSWORD})
    assert no_code.status_code == 401 and no_code.json()["code"] == "INVALID_CREDENTIALS"
    wrong_password = client.post(
        "/api/v1/auth/reauth", json={"password": "sai-mat-khau-x", "code": code_of(env, secret)}
    )
    assert wrong_password.status_code == 401
    code = code_of(env, secret)
    assert client.post("/api/v1/auth/reauth", json={"password": PASSWORD, "code": code}).status_code == 204
    replay = client.post("/api/v1/auth/reauth", json={"password": PASSWORD, "code": code})
    assert replay.status_code == 401  # mã đã dùng (RFC 6238 §5.2)


@pytest.mark.db
def test_reauth_needs_full_session_and_is_rate_limited(env: Env) -> None:
    env.user("admin@example.com", ("ADMIN",))
    pending = env.login("admin@example.com")  # ADMIN chưa đăng ký MFA → session chờ MFA
    response = pending.post("/api/v1/auth/reauth", json={"password": PASSWORD})
    assert response.status_code == 401 and response.json()["code"] == "MFA_REQUIRED"

    env.user("nv@example.com")
    client = env.login("nv@example.com")
    statuses = [client.post("/api/v1/auth/reauth", json={"password": "sai-mat-khau-x"}).status_code for _ in range(6)]
    assert statuses == [401] * 5 + [429]
    assert env.scalar("SELECT count(*) FROM audit.event WHERE action = 'auth.reauth' AND outcome = 'BLOCKED'") == 1


# ---------- TC-AUD-02 (phần đổi mật khẩu, D-55) ----------


@pytest.mark.db
def test_password_change_audit_and_logs_have_no_secrets(env: Env) -> None:
    stream = io.StringIO()
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    try:
        configure_logging(stream=stream)
        env.user("nv@example.com")
        client = env.login("nv@example.com")
        client.post("/api/v1/auth/reauth", json={"password": "sai-mat-khau-x"})
        client.post("/api/v1/auth/reauth", json={"password": PASSWORD})
        assert client.post("/api/v1/auth/password", json={"new_password": NEW_PASSWORD}).status_code == 204
        token = client.cookies[SESSION_COOKIE]
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
    with env.engine.connect() as conn:
        events = conn.execute(text("SELECT action, outcome, reason, changes::text FROM audit.event")).all()
    assert ("auth.password.change", "SUCCESS") in {(e.action, e.outcome) for e in events}
    assert ("auth.reauth", "DENIED") in {(e.action, e.outcome) for e in events}
    dumped = repr(events) + stream.getvalue()
    for secret in (PASSWORD, NEW_PASSWORD, "sai-mat-khau-x", token):
        assert secret not in dumped
