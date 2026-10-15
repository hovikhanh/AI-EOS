"""T-103: MFA TOTP — đăng ký, xác minh, mã khôi phục; bắt buộc với ADMIN (SRS-IAM-05, ADR-006; API-AUTH-02/03/04).

TC do T-103 làm chủ: TC-IAM-06 (`test_enrolled_admin_without_mfa_gets_mfa_required_everywhere`), TC-IAM-07
(`test_unenrolled_admin_can_only_enroll_and_logout`). Cả hai gọi **mọi** endpoint của ứng dụng (lấy từ OpenAPI của
`create_app`) nên API quản trị thêm sau (T-105, T-109) tự động thuộc phạm vi kiểm tra.
"""

import base64
import io
import logging
import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import grant_role
from aieos.app.asgi import PUBLIC_PATHS, create_app
from aieos.identity.api import (
    Authenticator,
    AuthSettings,
    MfaKeyError,
    MfaService,
    build_auth_router,
    build_mfa_router,
    hash_password,
    parse_totp_key,
)
from aieos.identity.mfa import (
    PERIOD_SECONDS,
    RECOVERY_CODE_COUNT,
    current_step,
    decrypt_secret,
    encrypt_secret,
    match_step,
    totp,
)
from aieos.notify.api import build_notify_router
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
from tests.test_auth import api_env

ORIGIN = "https://aieos.local"
KEY = Secret("khoa-csrf-test")
TOTP_KEY = os.urandom(32)
PASSWORD = "Mat-khau-dung-123!"
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
MFA_PATHS = {"/api/v1/auth/mfa/enroll", "/api/v1/auth/mfa/enroll/confirm", "/api/v1/auth/mfa/verify"}


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

    def user(self, email: str, roles: tuple[str, ...] = ("ADMIN",)) -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, "
                    "must_enroll_mfa) VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p, :m)"
                ),
                {"i": user_id, "e": email, "p": hash_password(PASSWORD), "m": "ADMIN" in roles},
            )
        with transaction(make_session_factory(self.engine)) as session:
            for role in roles:
                grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
        return user_id

    def login(self, email: str) -> tuple[TestClient, dict[str, Any]]:
        client = TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})
        response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        body = response.json()
        client.headers[CSRF_HEADER] = body["csrf_token"]
        return client, body

    def enroll(self, email: str) -> tuple[TestClient, bytes, list[str]]:
        """Đăng ký MFA đầy đủ; trả client (session đã xác minh), secret, mã khôi phục."""
        client, _ = self.login(email)
        secret = b32(client.post("/api/v1/auth/mfa/enroll").json()["secret"])
        response = client.post("/api/v1/auth/mfa/enroll/confirm", json={"code": self.code(secret)})
        assert response.status_code == 200, response.text
        refresh_csrf(client)
        return client, secret, response.json()["recovery_codes"]

    def code(self, secret: bytes, offset: int = 0) -> str:
        return totp(secret, current_step(self.clock.now) + offset)


def b32(secret: str) -> bytes:
    return base64.b32decode(secret + "=" * (-len(secret) % 8))


def assert_revoked(env: "Env", token: str) -> None:
    """Session cũ bị thu hồi: `UNAUTHENTICATED` (session chờ MFA còn sống sẽ trả `MFA_REQUIRED`)."""
    stale = TestClient(env.app, base_url="https://testserver", cookies={SESSION_COOKIE: token})
    response = stale.get("/api/v1/auth/me")
    assert response.status_code == 401 and response.json()["code"] == "UNAUTHENTICATED"


def refresh_csrf(client: TestClient) -> None:
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200, me.text
    client.headers[CSRF_HEADER] = me.json()["csrf_token"]


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    clock = Clock()
    app = create_api(
        {},
        (
            build_auth_router(auth, KEY),
            build_mfa_router(auth, MfaService(auth, TOTP_KEY, clock)),
            build_notify_router(factory, auth.require_session),
        ),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    yield Env(engine, app, clock)
    engine.dispose()


def scalar(engine: Engine, sql: str, params: dict[str, object] | None = None) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar_one()


# ---------- TOTP, mã hóa, khóa ----------


def test_totp_rfc6238_vectors() -> None:
    """RFC 6238 Phụ lục B (SHA1, secret ASCII "12345678901234567890"), 6 chữ số cuối của mã 8 chữ số."""
    secret = b"12345678901234567890"
    for unix_time, expected in ((59, "287082"), (1111111109, "081804"), (1234567890, "005924"), (2000000000, "279037")):
        assert totp(secret, unix_time // PERIOD_SECONDS) == expected


def test_match_step_window_and_replay() -> None:
    secret = os.urandom(20)
    now = 1_800_000_000.0
    step = current_step(now)
    assert match_step(secret, totp(secret, step), now, None) == step
    assert match_step(secret, totp(secret, step - 1), now, None) == step - 1  # lệch đồng hồ ±1 bước
    assert match_step(secret, totp(secret, step + 1), now, None) == step + 1
    assert match_step(secret, totp(secret, step - 2), now, None) is None
    assert match_step(secret, totp(secret, step), now, step) is None  # đã dùng (RFC 6238 §5.2)
    assert match_step(secret, totp(secret, step - 1), now, step - 1) is None
    assert match_step(secret, "12345", now, None) is None and match_step(secret, "abcdef", now, None) is None


def test_secret_encryption_bound_to_user() -> None:
    user, other = uuid.uuid4(), uuid.uuid4()
    blob = encrypt_secret(TOTP_KEY, user, b"secret-20-bytes-long")
    assert b"secret-20-bytes-long" not in blob
    assert decrypt_secret(TOTP_KEY, user, blob) == b"secret-20-bytes-long"
    with pytest.raises(RuntimeError):
        decrypt_secret(TOTP_KEY, other, blob)
    with pytest.raises(RuntimeError):
        decrypt_secret(os.urandom(32), user, blob)


def test_totp_key_must_be_32_bytes_base64() -> None:
    good = base64.b64encode(os.urandom(32)).decode()
    assert len(parse_totp_key(Secret(good))) == 32
    assert len(parse_totp_key(Secret(base64.urlsafe_b64encode(os.urandom(32)).decode()))) == 32
    for bad in ("k", base64.b64encode(os.urandom(16)).decode(), "khong phai base64!!"):
        with pytest.raises(MfaKeyError) as info:
            parse_totp_key(Secret(bad))
        assert bad not in str(info.value)


# ---------- Đăng ký (API-AUTH-03, 04) ----------


@pytest.mark.db
def test_enroll_confirm_enables_mfa_and_rotates_session(env: Env) -> None:
    user = env.user("admin@example.com")
    client, body = env.login("admin@example.com")
    assert (body["mfa_required"], body["mfa_enrolled"]) == (True, False)
    pending = client.cookies[SESSION_COOKIE]

    enrolled = client.post("/api/v1/auth/mfa/enroll")
    assert enrolled.status_code == 200
    secret = b32(enrolled.json()["secret"])
    assert enrolled.json()["otpauth_uri"].startswith("otpauth://totp/AI-EOS:admin@example.com?secret=")
    stored = scalar(env.engine, "SELECT mfa_secret_enc FROM identity.user_account WHERE id = :u", {"u": user})
    assert secret not in bytes(stored)
    assert scalar(env.engine, "SELECT mfa_enabled FROM identity.user_account WHERE id = :u", {"u": user}) is False

    wrong = client.post("/api/v1/auth/mfa/enroll/confirm", json={"code": env.code(secret, 5)})
    assert wrong.status_code == 401 and wrong.json()["code"] == "INVALID_CREDENTIALS"

    confirmed = client.post("/api/v1/auth/mfa/enroll/confirm", json={"code": env.code(secret)})
    assert confirmed.status_code == 200
    codes = confirmed.json()["recovery_codes"]
    assert len(codes) == RECOVERY_CODE_COUNT == len(set(codes))
    assert client.cookies[SESSION_COOKIE] != pending  # xoay session (ADR-006)
    assert_revoked(env, pending)
    refresh_csrf(client)
    me = client.get("/api/v1/auth/me").json()
    assert (me["mfa_enabled"], me["must_enroll_mfa"]) == (True, False)
    with env.engine.connect() as conn:
        hashes = conn.execute(text("SELECT code_hash FROM identity.mfa_recovery_code WHERE user_id = :u"), {"u": user})
        stored_hashes = [bytes(h) for (h,) in hashes]
    assert len(stored_hashes) == RECOVERY_CODE_COUNT and all(len(h) == 32 for h in stored_hashes)  # INV-16

    again = client.post("/api/v1/auth/mfa/enroll")
    assert again.status_code == 409 and again.json()["code"] == "INVALID_STATE"


@pytest.mark.db
def test_enroll_forbidden_for_roles_without_mandatory_mfa(env: Env) -> None:
    """MFA cho role khác là DEFERRED (D-30): EMPLOYEE không đăng ký được."""
    env.user("nv@example.com", roles=("EMPLOYEE",))
    client, body = env.login("nv@example.com")
    assert body["mfa_required"] is False
    response = client.post("/api/v1/auth/mfa/enroll")
    assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN"
    response = client.post("/api/v1/auth/mfa/enroll/confirm", json={"code": "123456"})
    assert response.status_code == 409


# ---------- Xác minh (API-AUTH-02) ----------


@pytest.mark.db
def test_verify_totp_rotates_session_and_rejects_replay(env: Env) -> None:
    env.user("admin@example.com")
    _, secret, _ = env.enroll("admin@example.com")
    env.clock.now += 120  # bước mới, mã lúc đăng ký đã cũ

    client, body = env.login("admin@example.com")
    assert (body["mfa_required"], body["mfa_enrolled"]) == (True, True)
    pending = client.cookies[SESSION_COOKIE]
    code = env.code(secret)
    assert client.post("/api/v1/auth/mfa/verify", json={"code": code}).status_code == 204
    assert client.cookies[SESSION_COOKIE] != pending
    assert_revoked(env, pending)
    assert client.get("/api/v1/auth/me").status_code == 200
    again = client.post("/api/v1/auth/mfa/verify", json={"code": code}, headers={CSRF_HEADER: "x"})
    assert again.status_code == 403  # session mới cần token CSRF mới
    refresh_csrf(client)
    assert client.post("/api/v1/auth/mfa/verify", json={"code": code}).status_code == 409  # đã xác minh

    replay, _ = env.login("admin@example.com")  # cùng mã, cùng bước, session khác
    response = replay.post("/api/v1/auth/mfa/verify", json={"code": code})
    assert response.status_code == 401 and response.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.db
def test_recovery_code_is_single_use(env: Env) -> None:
    env.user("admin@example.com")
    _, _, codes = env.enroll("admin@example.com")
    client, _ = env.login("admin@example.com")
    assert client.post("/api/v1/auth/mfa/verify", json={"code": codes[0].lower()}).status_code == 204
    reuse, _ = env.login("admin@example.com")
    assert reuse.post("/api/v1/auth/mfa/verify", json={"code": codes[0]}).status_code == 401
    assert reuse.post("/api/v1/auth/mfa/verify", json={"code": codes[1].replace("-", "")}).status_code == 204
    assert scalar(env.engine, "SELECT count(*) FROM identity.mfa_recovery_code WHERE used_at IS NULL") == 8


@pytest.mark.db
def test_verify_rate_limited_and_audited_without_codes(env: Env) -> None:
    env.user("admin@example.com")
    _, secret, codes = env.enroll("admin@example.com")
    client, _ = env.login("admin@example.com")
    statuses = [client.post("/api/v1/auth/mfa/verify", json={"code": "000000"}).status_code for _ in range(5)]
    assert statuses == [401] * 4 + [429]  # giới hạn 5 lượt/cửa sổ; bước xác nhận đăng ký đã dùng 1 lượt
    blocked = client.post("/api/v1/auth/mfa/verify", json={"code": env.code(secret, 1)})
    assert blocked.status_code == 429 and "retry-after" in blocked.headers
    with env.engine.connect() as conn:
        events = conn.execute(
            text("SELECT action, outcome, coalesce(reason, ''), coalesce(changes::text, '') FROM audit.event")
        ).all()
    assert ("auth.mfa.verify", "DENIED") in {(e[0], e[1]) for e in events}
    assert ("auth.mfa.verify", "BLOCKED") in {(e[0], e[1]) for e in events}
    dumped = repr(events)
    assert "000000" not in dumped and all(c not in dumped for c in codes)


# ---------- TC-IAM-06, TC-IAM-07 (mọi endpoint của ứng dụng) ----------


@pytest.fixture
def app_client(
    database: ProvisionedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[tuple[Any, Engine]]:
    migrate_to_head(database)
    api_env(monkeypatch, tmp_path, database.urls["aieos_app"].render_as_string(hide_password=False))
    monkeypatch.setenv("AIEOS_TOTP_ENCRYPTION_KEY", base64.b64encode(TOTP_KEY).decode())
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    app = create_app()
    engine = create_db_engine(database.secret("aieos_app"), pool_size=5)
    yield app, engine
    engine.dispose()
    root.handlers[:] = saved[0]
    root.setLevel(saved[1])


def call_all(app: Any, client: TestClient) -> dict[tuple[str, str], Any]:
    results = {}
    for path, operations in app.openapi()["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method in sorted(m.upper() for m in operations):
            if (method, path) in PUBLIC_PATHS or path == "/api/v1/auth/logout":
                continue
            concrete = path.replace("{", "").replace("}", "")
            results[(method, path)] = client.request(method, concrete, json={"code": "000000"})
    return results


def admin_login(app: Any, engine: Engine, *, enrolled: bool) -> TestClient:
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, mfa_enabled, "
                "mfa_secret_enc, must_enroll_mfa) VALUES (:i, 'admin@example.com', 'A', 'ACTIVE', :p, :m, :s, :w)"
            ),
            {
                "i": user_id,
                "p": hash_password(PASSWORD),
                "m": enrolled,
                "s": encrypt_secret(TOTP_KEY, user_id, os.urandom(20)) if enrolled else None,
                "w": not enrolled,
            },
        )
    with transaction(make_session_factory(engine)) as session:
        grant_role(session, user_id=user_id, role="ADMIN", granted_by=None, reason=None)
    client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
    body = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}).json()
    assert (body["mfa_required"], body["mfa_enrolled"]) == (True, enrolled)
    client.headers[CSRF_HEADER] = body["csrf_token"]
    return client


@pytest.mark.db
def test_enrolled_admin_without_mfa_gets_mfa_required_everywhere(app_client: tuple[Any, Engine]) -> None:
    """TC-IAM-06: ADMIN đã đăng ký nhưng chưa xác minh MFA → mọi API ngoài MFA trả `401 MFA_REQUIRED`."""
    app, engine = app_client
    client = admin_login(app, engine, enrolled=True)
    results = call_all(app, client)
    assert results, "không tìm thấy endpoint nào"
    for (method, path), response in results.items():
        if path in MFA_PATHS:
            continue
        assert response.status_code == 401 and response.json()["code"] == "MFA_REQUIRED", (method, path)
    assert results[("POST", "/api/v1/auth/mfa/verify")].json()["code"] == "INVALID_CREDENTIALS"  # được gọi, mã sai
    assert results[("POST", "/api/v1/auth/mfa/enroll")].json()["code"] == "INVALID_STATE"  # đã đăng ký


@pytest.mark.db
def test_unenrolled_admin_can_only_enroll_and_logout(app_client: tuple[Any, Engine]) -> None:
    """TC-IAM-07: ADMIN chưa đăng ký MFA → chỉ gọi được API đăng ký MFA và đăng xuất; mọi API khác `401 MFA_REQUIRED`
    (xác minh → `409 INVALID_STATE` vì chưa có MFA)."""
    app, engine = app_client
    client = admin_login(app, engine, enrolled=False)
    results = call_all(app, client)
    for (method, path), response in results.items():
        if path in MFA_PATHS:
            continue
        assert response.status_code == 401 and response.json()["code"] == "MFA_REQUIRED", (method, path)
    assert results[("POST", "/api/v1/auth/mfa/enroll")].status_code == 200
    assert results[("POST", "/api/v1/auth/mfa/verify")].json()["code"] == "INVALID_STATE"
    assert client.post("/api/v1/auth/logout").status_code == 204


@pytest.mark.db
def test_mfa_logs_contain_no_codes(env: Env) -> None:
    stream = io.StringIO()
    root = logging.getLogger()
    saved = (root.handlers[:], root.level)
    try:
        configure_logging(stream=stream)
        env.user("admin@example.com")
        _, secret, codes = env.enroll("admin@example.com")
        client, _ = env.login("admin@example.com")
        code = env.code(secret, 1)
        client.post("/api/v1/auth/mfa/verify", json={"code": code})
    finally:
        root.handlers[:] = saved[0]
    root.setLevel(saved[1])
    output = stream.getvalue()
    assert output and code not in output and all(c not in output for c in codes)
    assert base64.b32encode(secret).decode().rstrip("=") not in output
