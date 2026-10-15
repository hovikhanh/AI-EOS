"""T-006: log JSON, correlation ID, che dữ liệu nhạy cảm, health (ADR-012, API-SYS-01, API-SYS-02, SRS-GEN-05)."""

import io
import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from aieos.app.asgi import create_app
from aieos.platform.api import (
    CORRELATION_ID,
    REDACTED,
    CsrfConfig,
    Secret,
    configure_logging,
    create_api,
    csrf_token,
    redact,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head

TEST_CSRF = CsrfConfig(Secret("khoa-csrf-test"), frozenset({"https://aieos.local"}))
LIVE = "/api/v1/health/live"
READY = "/api/v1/health/ready"
SECRETS = {
    "authorization": "Bearer tok-authorization-123",
    "cookie": "__Host-aieos_session=sess-cookie-456",
    "password": "mat-khau-789",
    "query_token": "invite-token-abc",
    "csrf": "csrf-token-def",
}


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    configure_logging(logging.DEBUG, stream=stream)
    yield stream
    root.handlers[:] = saved[0]
    root.setLevel(saved[1])


def records(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line]


# ---------- Log JSON và che dữ liệu ----------


def test_log_lines_are_json_with_correlation_id(log_stream: io.StringIO) -> None:
    token = CORRELATION_ID.set("req-12345678")
    try:
        logging.getLogger("aieos.test").info("xin chào %s", "bạn", extra={"count": 3})
    finally:
        CORRELATION_ID.reset(token)
    [record] = records(log_stream)
    assert record["message"] == "xin chào bạn"
    assert record["level"] == "INFO"
    assert record["logger"] == "aieos.test"
    assert record["correlation_id"] == "req-12345678"
    assert record["count"] == 3
    assert record["ts"].endswith("+00:00")


def test_sensitive_extra_fields_are_redacted(log_stream: io.StringIO) -> None:
    logging.getLogger("aieos.test").info(
        "su_kien",
        extra={
            "headers": {"Authorization": SECRETS["authorization"], "Cookie": SECRETS["cookie"], "Accept": "json"},
            "password": SECRETS["password"],
            "body": {"user": {"new_password": SECRETS["password"], "email": "a@example.test"}},
            "X-CSRF-Token": SECRETS["csrf"],
            "AIEOS_LLM_API_KEY_LOCAL": "khoa-api",
            "db": Secret("postgresql://u:p@h/db"),
        },
    )
    text = log_stream.getvalue()
    for value in [*SECRETS.values(), "khoa-api", "postgresql://u:p@h/db"]:
        assert value not in text
    [record] = records(log_stream)
    assert record["headers"] == {"Authorization": REDACTED, "Cookie": REDACTED, "Accept": "json"}
    assert record["body"]["user"]["email"] == "a@example.test"
    assert record["db"] == REDACTED


@pytest.mark.parametrize("key", ["Set-Cookie", "mfa_code", "totp", "invite_token", "client_secret", "api-key"])
def test_redact_by_key_name(key: str) -> None:
    assert redact("gia-tri", key) == REDACTED


def test_http_client_library_does_not_log_urls(log_stream: io.StringIO) -> None:
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).info("HTTP Request: GET https://provider.example/v1?api_key=khoa-api")
    assert "khoa-api" not in log_stream.getvalue()


def test_configure_logging_is_idempotent() -> None:
    root = logging.getLogger()
    saved = (list(root.handlers), root.level)
    try:
        configure_logging(stream=io.StringIO())
        configure_logging(stream=io.StringIO())
        assert len(root.handlers) == 1
    finally:
        root.handlers[:] = saved[0]
        root.setLevel(saved[1])


# ---------- HTTP: correlation ID, log request, health ----------


def client_for(checks: dict[str, Any], routers: tuple[APIRouter, ...] = ()) -> TestClient:
    return TestClient(create_api(checks, routers, csrf=TEST_CSRF), raise_server_exceptions=False)


def test_request_log_never_contains_headers_cookie_body_or_query(log_stream: io.StringIO) -> None:
    router = APIRouter()

    @router.post("/echo")
    def echo() -> dict[str, str]:
        return {"ok": "1"}

    client = client_for({}, (router,))
    client.cookies.set("__Host-aieos_session", "sess-cookie-456")
    real_csrf = csrf_token(TEST_CSRF.key, "sess-cookie-456")  # T-007: token CSRF hợp lệ cũng không được vào log
    response = client.post(
        f"/api/v1/echo?token={SECRETS['query_token']}",
        headers={"Authorization": SECRETS["authorization"], "X-CSRF-Token": real_csrf, "Origin": "https://aieos.local"},
        json={"password": SECRETS["password"]},
    )
    assert response.status_code == 200
    text = log_stream.getvalue()
    for value in [*SECRETS.values(), "sess-cookie-456", real_csrf]:
        assert value not in text
    request_log = [r for r in records(log_stream) if r["message"] == "request"]
    assert request_log == [
        {**request_log[0], "method": "POST", "path": "/api/v1/echo", "status": 200},
    ]
    assert request_log[0]["correlation_id"] == response.headers["x-request-id"]


@pytest.mark.parametrize("incoming", ["req-abcdef12", "0f8fad5b-d9cb-469f-a165-70867728950e"])
def test_valid_request_id_is_kept(incoming: str) -> None:
    response = client_for({}).get(LIVE, headers={"X-Request-ID": incoming})
    assert response.headers["x-request-id"] == incoming


@pytest.mark.parametrize("incoming", ["short", "a" * 200, "abc/12345678", "abc 12345678", "-leading-dash"])
def test_invalid_request_id_is_replaced(incoming: str) -> None:
    response = client_for({}).get(LIVE, headers={"X-Request-ID": incoming})
    generated = response.headers["x-request-id"]
    assert generated != incoming
    assert len(generated) == 32


def test_request_id_generated_when_absent() -> None:
    client = client_for({})
    first = client.get(LIVE).headers["x-request-id"]
    second = client.get(LIVE).headers["x-request-id"]
    assert first != second


def test_live() -> None:
    response = client_for({"database": lambda: False}).get(LIVE)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_all_checks_pass() -> None:
    response = client_for({"database": lambda: True, "storage": lambda: True}).get(READY)
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def boom() -> bool:
    raise RuntimeError("chi-tiet-noi-bo postgresql://u:p@h/db")


@pytest.mark.parametrize("failing", [lambda: False, boom])
def test_not_ready_without_details(failing: Any, log_stream: io.StringIO) -> None:
    response = client_for({"database": lambda: True, "storage": failing}).get(READY)
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "storage" not in response.text
    assert "chi-tiet-noi-bo" not in log_stream.getvalue()
    not_ready = [r for r in records(log_stream) if r["message"] == "not_ready"]
    assert not_ready[0]["failed_checks"] == ["storage"]


def test_unhandled_error_has_no_stack_trace(log_stream: io.StringIO) -> None:
    router = APIRouter()

    @router.get("/hong")
    def broken() -> None:
        raise RuntimeError("bi-mat-noi-bo")

    response = client_for({}, (router,)).get("/api/v1/hong")
    assert response.status_code == 500
    assert "bi-mat-noi-bo" not in response.text
    assert "Traceback" not in response.text


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_api_docs_not_exposed(path: str) -> None:
    assert client_for({}).get(path).status_code == 404


def test_openapi_available_in_code() -> None:
    paths = create_api({}, csrf=TEST_CSRF).openapi()["paths"]
    assert {LIVE, READY} <= set(paths)


# ---------- Composition root ----------


def api_env(monkeypatch: pytest.MonkeyPatch, storage: Path, database_url: str) -> None:
    for name, value in {
        "AIEOS_DATABASE_URL": database_url,
        "AIEOS_CSRF_KEY": "k",
        "AIEOS_TOTP_ENCRYPTION_KEY": "k",
        "AIEOS_STORAGE_PATH": str(storage),
        "AIEOS_ALLOWED_ORIGINS": "https://aieos.local",
        "AIEOS_SESSION_IDLE_MINUTES": "1",
        "AIEOS_SESSION_ABSOLUTE_HOURS": "1",
        "AIEOS_INVITE_TTL_HOURS": "1",
        "AIEOS_REAUTH_MINUTES": "1",
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


def test_create_app_not_ready_when_database_unreachable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, restore_logging: None
) -> None:
    api_env(monkeypatch, tmp_path, "postgresql://aieos_app:khong-dung@127.0.0.1:1/aieos")
    client = TestClient(create_app())
    assert client.get(LIVE).status_code == 200
    assert client.get(READY).status_code == 503


def test_create_app_exits_when_config_missing(monkeypatch: pytest.MonkeyPatch, restore_logging: None) -> None:
    monkeypatch.delenv("AIEOS_CSRF_KEY", raising=False)
    with pytest.raises(SystemExit) as info:
        create_app()
    assert info.value.code == 2


def test_create_app_exits_when_storage_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, restore_logging: None
) -> None:
    api_env(monkeypatch, tmp_path / "khong-co", "postgresql://aieos_app:x@127.0.0.1:1/aieos")
    with pytest.raises(SystemExit) as info:
        create_app()
    assert info.value.code == 2


@pytest.mark.db
def test_ready_follows_database_migration_state(
    database: ProvisionedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, restore_logging: None
) -> None:
    api_env(monkeypatch, tmp_path, database.urls["aieos_app"].render_as_string(hide_password=False))
    client = TestClient(create_app())
    assert client.get(READY).status_code == 503  # CSDL chưa migrate
    migrate_to_head(database)
    assert client.get(READY).status_code == 200
