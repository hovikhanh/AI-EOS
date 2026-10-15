"""T-105: tạo tài khoản + lời mời, chấp nhận lời mời (SRS-IAM-01…03; API-ADM-02, API-ADM-03, API-AUTH-08; FL-02).

TC do T-105 làm chủ: TC-IAM-09 (`test_unusable_invitations_all_rejected_alike`), TC-IAM-10
(`test_concurrent_accept_single_winner`), TC-AUD-02 tổng (D-55; `test_audit_and_logs_have_no_secrets_end_to_end` —
đăng nhập, MFA, đổi mật khẩu, tạo + chấp nhận lời mời trong một luồng).
"""

import base64
import hashlib
import io
import logging
import os
import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import PermissionGuard, grant_role
from aieos.identity.api import (
    Authenticator,
    AuthSettings,
    InvitationService,
    MfaService,
    StepUpService,
    UserAdmin,
    build_auth_router,
    build_invitation_router,
    build_mfa_router,
    build_stepup_router,
    hash_password,
    hash_token,
)
from aieos.identity.mfa import current_step, totp
from aieos.platform.api import (
    CSRF_HEADER,
    IDEMPOTENCY_HEADER,
    SESSION_COOKIE,
    ApiError,
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
NEW_PASSWORD = "Mat-khau-nguoi-moi-789!"
SETTINGS = AuthSettings(
    idle=timedelta(minutes=30),
    absolute=timedelta(hours=8),
    rate_limit_attempts=20,
    rate_limit_window=timedelta(seconds=60),
    lockout_threshold=10,
    lockout_duration=timedelta(minutes=15),
    reauth=timedelta(minutes=5),
    password_min_length=12,
)
ACCEPT = "/api/v1/auth/invitations/accept"


@dataclass
class Clock:
    now: float = 1_800_000_000.0

    def __call__(self) -> float:
        return self.now


@dataclass
class Env:
    engine: Engine
    app: Any
    invitations: InvitationService
    clock: Clock = field(default_factory=Clock)

    def admin(self, email: str = "admin@example.com") -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                    "VALUES (:i, :e, 'Quản trị', 'ACTIVE', :p)"
                ),
                {"i": user_id, "e": email, "p": hash_password(PASSWORD)},
            )
        with transaction(make_session_factory(self.engine)) as session:
            grant_role(session, user_id=user_id, role="ADMIN", granted_by=None, reason=None)
        return user_id

    def client(self) -> TestClient:
        return TestClient(self.app, base_url="https://testserver", headers={"Origin": ORIGIN})

    def admin_client(self, email: str = "admin@example.com") -> TestClient:
        """Session ADMIN đã qua MFA và reauth (đánh dấu trong CSDL — luồng thật kiểm ở T-103/T-104 và TC-AUD-02)."""
        client = self.client()
        body = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()
        client.headers[CSRF_HEADER] = body["csrf_token"]
        with self.engine.begin() as conn:
            conn.execute(
                text("UPDATE identity.session SET mfa_verified = true, reauth_at = now() WHERE token_hash = :h"),
                {"h": hash_token(client.cookies[SESSION_COOKIE])},
            )
        return client

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory = make_session_factory(engine)
    auth = Authenticator(factory, SETTINGS)
    clock = Clock()
    mfa = MfaService(auth, TOTP_KEY, clock)
    guard = PermissionGuard(factory, auth.require_session, require_step_up=auth.require_step_up)
    invitations = InvitationService(auth, UserAdmin(auth), timedelta(hours=72))
    app = create_api(
        {},
        (
            build_auth_router(auth, KEY),
            build_mfa_router(auth, mfa),
            build_stepup_router(auth, StepUpService(auth, mfa)),
            build_invitation_router(invitations, guard),
        ),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login", ACCEPT})),
    )
    yield Env(engine, app, invitations, clock)
    engine.dispose()


def create(client: TestClient, email: str, roles: list[str] | None = None, key: str | None = None, **extra: Any) -> Any:
    body = {"email": email, "display_name": "Người mới", "roles": roles or ["EMPLOYEE"], "reason": "Tuyển mới", **extra}
    return client.post("/api/v1/admin/users", json=body, headers={IDEMPOTENCY_HEADER: key or uuid.uuid4().hex})


def token_of(response: Any) -> str:
    link: str = response.json()["invitation"]["link"]
    assert link.startswith("/invite#token=")
    return link.removeprefix("/invite#token=")


# ---------- Tạo, cấp lại (API-ADM-02, 03) ----------


@pytest.mark.db
def test_create_user_returns_one_time_link_and_stores_hash(env: Env) -> None:
    env.admin()
    admin = env.admin_client()
    key = uuid.uuid4().hex
    response = create(admin, "moi@example.com", ["MANAGER"], key)
    assert response.status_code == 201 and response.headers["cache-control"] == "no-store"
    user = response.json()["user"]
    assert (user["status"], user["roles"], user["email"]) == ("INVITED", ["MANAGER"], "moi@example.com")
    token = token_of(response)
    assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) >= 32  # ≥ 256 bit
    stored = env.scalar("SELECT token_hash FROM identity.invitation")
    assert bytes(stored) == hashlib.sha256(token.encode()).digest() and token.encode() not in bytes(stored)
    expires = env.scalar("SELECT expires_at - created_at FROM identity.invitation")
    assert timedelta(hours=71, minutes=59) < expires <= timedelta(hours=72, minutes=1)

    replay = create(admin, "moi@example.com", ["MANAGER"], key)
    assert replay.status_code == 201 and replay.json()["user"]["id"] == user["id"]
    assert replay.json()["invitation"] is None  # link chỉ hiển thị một lần
    reused = create(admin, "khac@example.com", ["MANAGER"], key)
    assert reused.status_code == 409 and reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    missing = admin.post("/api/v1/admin/users", json={"email": "x@example.com", "display_name": "X", "reason": "r"})
    assert missing.status_code == 400 and missing.json()["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert env.scalar("SELECT count(*) FROM identity.user_account WHERE status = 'INVITED'") == 1


@pytest.mark.db
def test_create_user_validation_rolls_back(env: Env) -> None:
    env.admin()
    admin = env.admin_client()
    duplicate = create(admin, "Admin@Example.com")
    assert duplicate.status_code == 422 and duplicate.json()["errors"][0]["field"] == "email"
    combo = create(admin, "cfo@example.com", ["CFO", "ADMIN"])
    assert combo.status_code == 422 and combo.json()["code"] == "ROLE_COMBINATION_FORBIDDEN"
    assert env.scalar("SELECT count(*) FROM identity.user_account") == 1
    assert env.scalar("SELECT count(*) FROM identity.invitation") == 0
    assert (
        env.scalar("SELECT count(*) FROM audit.event WHERE action = 'identity.user.create' AND outcome = 'FAILED'") == 2
    )
    stale = env.client()
    stale.headers[CSRF_HEADER] = stale.post(
        "/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}
    ).json()["csrf_token"]
    with env.engine.begin() as conn:
        conn.execute(text("UPDATE identity.session SET mfa_verified = true WHERE reauth_at IS NULL"))
    assert create(stale, "y@example.com").json()["code"] == "REAUTH_REQUIRED"  # STEP-UP


@pytest.mark.db
def test_reissue_revokes_previous_invitation(env: Env) -> None:
    env.admin()
    admin = env.admin_client()
    created = create(admin, "moi@example.com")
    user_id, first = created.json()["user"]["id"], token_of(created)
    again = admin.post(f"/api/v1/admin/users/{user_id}/invitations")
    assert again.status_code == 201
    second = again.json()["link"].removeprefix("/invite#token=")
    assert env.client().post(ACCEPT, json={"token": first, "password": NEW_PASSWORD}).status_code == 400
    assert env.client().post(ACCEPT, json={"token": second, "password": NEW_PASSWORD}).status_code == 204
    active = admin.post(f"/api/v1/admin/users/{user_id}/invitations")
    assert active.status_code == 409 and active.json()["code"] == "INVALID_STATE"
    assert admin.post(f"/api/v1/admin/users/{uuid.uuid4()}/invitations").status_code == 404


# ---------- Chấp nhận (API-AUTH-08) ----------


@pytest.mark.db
def test_accept_activates_account_then_login(env: Env) -> None:
    env.admin()
    admin = env.admin_client()
    token = token_of(create(admin, "moi@example.com", ["ADMIN"]))
    weak = env.client().post(ACCEPT, json={"token": token, "password": "ngan"})
    assert weak.status_code == 422 and weak.json()["errors"][0]["field"] == "password"
    accepted = env.client().post(ACCEPT, json={"token": token, "password": NEW_PASSWORD})  # không cần CSRF/session
    assert accepted.status_code == 204
    assert env.scalar("SELECT status FROM identity.user_account WHERE email = 'moi@example.com'") == "ACTIVE"
    login = env.client().post("/api/v1/auth/login", json={"email": "moi@example.com", "password": NEW_PASSWORD})
    assert login.status_code == 200 and (login.json()["mfa_required"], login.json()["mfa_enrolled"]) == (True, False)


@pytest.mark.db
def test_unusable_invitations_all_rejected_alike(env: Env) -> None:
    """TC-IAM-09: lời mời dùng lần hai, hết hạn, bị thu hồi (và token sai) → `400 INVITATION_INVALID`, cùng thông
    báo."""
    env.admin()
    admin = env.admin_client()
    used = token_of(create(admin, "a@example.com"))
    assert env.client().post(ACCEPT, json={"token": used, "password": NEW_PASSWORD}).status_code == 204
    expired = token_of(create(admin, "b@example.com"))
    with env.engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE identity.invitation SET created_at = now() - interval '1 day', "
                "expires_at = now() - interval '1 second' WHERE token_hash = :h"
            ),
            {"h": hash_token(expired)},
        )
    revoked_response = create(admin, "c@example.com")
    revoked = token_of(revoked_response)
    admin.post(f"/api/v1/admin/users/{revoked_response.json()['user']['id']}/invitations")

    bodies = []
    for token in (used, expired, revoked, "token-khong-ton-tai"):
        response = env.client().post(ACCEPT, json={"token": token, "password": NEW_PASSWORD})
        assert response.status_code == 400 and response.json()["code"] == "INVITATION_INVALID", token
        body = response.json()
        body.pop("correlation_id")
        bodies.append(body)
    assert all(body == bodies[0] for body in bodies)  # không phân biệt lý do
    assert env.scalar("SELECT count(*) FROM identity.user_account WHERE status = 'INVITED'") == 2  # b, c không đổi


@pytest.mark.db
def test_concurrent_accept_single_winner(env: Env) -> None:
    """TC-IAM-10: hai request chấp nhận cùng lời mời đồng thời → đúng một thành công."""
    env.admin()
    token = token_of(create(env.admin_client(), "moi@example.com"))
    barrier = threading.Barrier(4)
    results: list[str] = []

    def accept(n: int) -> None:
        barrier.wait()
        try:
            env.invitations.accept(token, f"{NEW_PASSWORD}-{n}", ip=f"10.0.0.{n}")
            results.append("ok")
        except ApiError as error:
            results.append(error.code)

    threads = [threading.Thread(target=accept, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["INVITATION_INVALID"] * 3 + ["ok"]
    assert env.scalar("SELECT count(*) FROM identity.invitation WHERE used_at IS NOT NULL") == 1


@pytest.mark.db
def test_accept_rate_limited(env: Env) -> None:
    statuses = [
        env.client().post(ACCEPT, json={"token": "sai", "password": NEW_PASSWORD}).status_code for _ in range(21)
    ]
    assert statuses[:20] == [400] * 20 and statuses[20] == 429


# ---------- TC-AUD-02 (tổng, D-55) ----------


@pytest.mark.db
def test_audit_and_logs_have_no_secrets_end_to_end(env: Env) -> None:
    """TC-AUD-02: đăng nhập, MFA, đổi mật khẩu, tạo + chấp nhận lời mời → audit/log không chứa mật khẩu, token, mã
    MFA."""
    stream = io.StringIO()
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    secrets_seen: list[str] = [PASSWORD, NEW_PASSWORD, "sai-mat-khau-x"]
    try:
        configure_logging(stream=stream)
        env.admin()
        admin = env.client()
        admin.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "sai-mat-khau-x"})
        body = admin.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}).json()
        admin.headers[CSRF_HEADER] = body["csrf_token"]
        secrets_seen += [body["csrf_token"], admin.cookies[SESSION_COOKIE]]
        enrolled = admin.post("/api/v1/auth/mfa/enroll").json()
        secret = base64.b32decode(enrolled["secret"] + "=" * (-len(enrolled["secret"]) % 8))
        code = totp(secret, current_step(env.clock.now))
        admin.post("/api/v1/auth/mfa/enroll/confirm", json={"code": "000000"})
        confirmed = admin.post("/api/v1/auth/mfa/enroll/confirm", json={"code": code}).json()
        secrets_seen += [enrolled["secret"], code, *confirmed["recovery_codes"], admin.cookies[SESSION_COOKIE]]
        admin.headers[CSRF_HEADER] = admin.get("/api/v1/auth/me").json()["csrf_token"]
        env.clock.now += 60
        code2 = totp(secret, current_step(env.clock.now))
        secrets_seen.append(code2)
        assert admin.post("/api/v1/auth/reauth", json={"password": PASSWORD, "code": code2}).status_code == 204
        assert admin.post("/api/v1/auth/password", json={"new_password": "Mat-khau-admin-moi-1!"}).status_code == 204
        secrets_seen.append("Mat-khau-admin-moi-1!")
        created = create(admin, "moi@example.com")
        assert created.status_code == 201, created.text
        invite = token_of(created)
        secrets_seen.append(invite)
        assert env.client().post(ACCEPT, json={"token": invite, "password": NEW_PASSWORD}).status_code == 204
        env.client().post(ACCEPT, json={"token": invite, "password": NEW_PASSWORD})
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])
    with env.engine.connect() as conn:
        events = conn.execute(text("SELECT action, outcome, row_to_json(e)::text AS raw FROM audit.event e")).all()
    actions = {(e.action, e.outcome) for e in events}
    for expected in (
        ("auth.login", "DENIED"),
        ("auth.login", "SUCCESS"),
        ("auth.mfa.enroll.confirm", "DENIED"),
        ("auth.mfa.enroll.confirm", "SUCCESS"),
        ("auth.reauth", "SUCCESS"),
        ("auth.password.change", "SUCCESS"),
        ("identity.user.create", "SUCCESS"),
        ("identity.invitation.issue", "SUCCESS"),
        ("identity.invitation.accept", "SUCCESS"),
        ("identity.invitation.accept", "DENIED"),
    ):
        assert expected in actions, expected
    dumped = "\n".join(e.raw for e in events) + stream.getvalue()
    assert stream.getvalue()
    for secret_value in secrets_seen:
        assert secret_value not in dumped, secret_value[:4]
