"""T-007: hạ tầng HTTP — problem+json, CSRF + Origin, idempotency, ETag/If-Match, giới hạn tốc độ.

TC do T-007 làm chủ (TEST_Plan §12): TC-GEN-01 (`test_post_without_csrf_token_rejected`), TC-GEN-02
(`test_csrf_ok_but_foreign_origin_rejected`), TC-GEN-03 (`test_same_key_same_body_sequential`,
`test_same_key_same_body_concurrent`), TC-GEN-04 (`test_same_key_different_body_conflict`), TC-GEN-05
(`test_if_match_wrong_and_missing`, `test_server_error_is_problem_json_with_correlation_id`).
Theo bảng task chủ (Q-51_TC_Ownership_Draft §6, D-44): ở T-007 dùng route thử; T-603 chạy lại trên endpoint nghiệp vụ.
"""

import re
import threading
import uuid
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from aieos.platform.api import (
    AUTHENTICATED,
    ERROR_CATALOG,
    PROBLEM_MEDIA_TYPE,
    PUBLIC,
    SESSION_COOKIE,
    ApiError,
    CsrfConfig,
    OriginConfigError,
    RateLimiter,
    Secret,
    check_version,
    create_api,
    create_db_engine,
    csrf_token,
    declare,
    etag,
    make_session_factory,
    parse_allowed_origins,
    request_fingerprint,
    require_idempotency_key,
    require_if_match,
    run_idempotent,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head

API_SPEC = Path(__file__).resolve().parents[2] / "docs" / "03-architecture" / "API_Specification.md"
ORIGIN = "https://aieos.local"
KEY = Secret("khoa-csrf-test")
SESSION = "phien-test-123"
CONFIG = CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/probe/public"}))


def safe_headers(**extra: str) -> dict[str, str]:
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf_token(KEY, SESSION), **extra}


def client(router: APIRouter, raise_errors: bool = False) -> TestClient:
    c = TestClient(create_api({}, (router,), csrf=CONFIG), raise_server_exceptions=raise_errors)
    c.cookies.set(SESSION_COOKIE, SESSION)
    return c


def assert_problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith(PROBLEM_MEDIA_TYPE)
    body: dict[str, Any] = response.json()
    assert body["code"] == code and body["status"] == status
    assert body["type"].endswith(code)
    assert body["correlation_id"] == response.headers["x-request-id"]
    return body


# ---------- Danh mục lỗi ↔ tài liệu ----------


def test_error_catalog_matches_api_specification() -> None:
    section = API_SPEC.read_text(encoding="utf-8").split("## 10. Mã lỗi", 1)[1].split("\n## ", 1)[0]
    documented: dict[str, int] = {}
    for codes, status in re.findall(r"^\| (`[A-Z_]+`(?:, `[A-Z_]+`)*) \| (\d{3}) \|", section, flags=re.M):
        for code in re.findall(r"`([A-Z_]+)`", codes):
            documented[code] = int(status)
    assert documented == dict(ERROR_CATALOG)


def test_unknown_error_code_rejected() -> None:
    with pytest.raises(ValueError):
        ApiError("MADE_UP_CODE")


# ---------- CSRF + Origin (TC-GEN-01, TC-GEN-02) ----------


@pytest.fixture
def counter_router() -> tuple[APIRouter, list[str]]:
    calls: list[str] = []
    router = APIRouter()

    @router.post("/probe/write", **declare(AUTHENTICATED))
    def write() -> dict[str, str]:
        calls.append("write")
        return {"ok": "1"}

    @router.post("/probe/public", **declare(PUBLIC))
    def public() -> dict[str, str]:
        calls.append("public")
        return {"ok": "1"}

    @router.get("/probe/read", **declare(AUTHENTICATED))
    def read() -> dict[str, str]:
        return {"ok": "1"}

    return router, calls


def test_post_without_csrf_token_rejected(counter_router: tuple[APIRouter, list[str]]) -> None:
    """TC-GEN-01: POST thiếu X-CSRF-Token → 403 CSRF_FAILED, không có thay đổi."""
    router, calls = counter_router
    c = client(router)
    assert_problem(c.post("/api/v1/probe/write", headers={"Origin": ORIGIN}), 403, "CSRF_FAILED")
    assert_problem(c.post("/api/v1/probe/write", headers=safe_headers(**{"X-CSRF-Token": "sai"})), 403, "CSRF_FAILED")
    assert calls == []
    c.cookies.clear()  # không có session: chỉ kiểm Origin; xác thực của endpoint trả 401 (T-102, TC-GEN-06)
    assert c.post("/api/v1/probe/write", headers={"Origin": ORIGIN}).status_code == 200
    assert_problem(c.post("/api/v1/probe/write", headers={"Origin": "https://evil.example"}), 403, "CSRF_FAILED")


def test_csrf_ok_but_foreign_origin_rejected(counter_router: tuple[APIRouter, list[str]]) -> None:
    """TC-GEN-02: CSRF đúng nhưng Origin khác host → 403 CSRF_FAILED."""
    router, calls = counter_router
    c = client(router)
    for origin in ("https://evil.example", "http://aieos.local", "https://aieos.local:8443", "null"):
        response = c.post("/api/v1/probe/write", headers=safe_headers(Origin=origin))
        assert_problem(response, 403, "CSRF_FAILED")
    no_origin = {"X-CSRF-Token": csrf_token(KEY, SESSION)}
    assert_problem(c.post("/api/v1/probe/write", headers=no_origin), 403, "CSRF_FAILED")
    assert calls == []


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_every_unsafe_method_checked(method: str) -> None:
    router = APIRouter()
    router.add_api_route("/probe/x", lambda: {"ok": "1"}, methods=[method.upper()], **declare(AUTHENTICATED))
    c = client(router)
    assert_problem(getattr(c, method)("/api/v1/probe/x", headers={"Origin": ORIGIN}), 403, "CSRF_FAILED")
    assert getattr(c, method)("/api/v1/probe/x", headers=safe_headers()).status_code == 200


def test_valid_csrf_and_safe_methods_pass(counter_router: tuple[APIRouter, list[str]]) -> None:
    router, calls = counter_router
    c = client(router)
    assert c.post("/api/v1/probe/write", headers=safe_headers()).status_code == 200
    assert c.get("/api/v1/probe/read").status_code == 200  # GET không cần CSRF
    assert calls == ["write"]


def test_exempt_path_still_checks_origin(counter_router: tuple[APIRouter, list[str]]) -> None:
    router, calls = counter_router
    c = client(router)
    c.cookies.clear()
    assert c.post("/api/v1/probe/public", headers={"Origin": ORIGIN}).status_code == 200
    assert_problem(c.post("/api/v1/probe/public", headers={"Origin": "https://evil.example"}), 403, "CSRF_FAILED")
    assert calls == ["public"]


def test_csrf_token_bound_to_session_and_key() -> None:
    assert csrf_token(KEY, "a") != csrf_token(KEY, "b")
    assert csrf_token(KEY, "a") != csrf_token(Secret("khoa-khac"), "a")
    assert "a" not in csrf_token(KEY, "a") and len(csrf_token(KEY, "a")) == 43


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://aieos.local", {"https://aieos.local"}),
        (" https://A.example:8443 , http://localhost:5173 ", {"https://a.example:8443", "http://localhost:5173"}),
    ],
)
def test_parse_allowed_origins(raw: str, expected: set[str]) -> None:
    assert parse_allowed_origins(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", " , ", "aieos.local", "ftp://x", "https://x/", "https://x/path", "https://u:p@x", "https://x?q=1"]
)
def test_parse_allowed_origins_rejects(raw: str) -> None:
    with pytest.raises(OriginConfigError):
        parse_allowed_origins(raw)


# ---------- ETag / If-Match, lỗi (TC-GEN-05) ----------


class Patch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    amount: int


def versioned_router() -> APIRouter:
    router = APIRouter()
    state = {"version": 3}

    @router.patch("/probe/item", **declare(AUTHENTICATED))
    def update(body: Patch, if_match: str | None = Header(default=None)) -> JSONResponse:
        check_version(state["version"], require_if_match(if_match))
        state["version"] += 1
        return JSONResponse({"name": body.name}, headers={"ETag": etag(state["version"])})

    @router.get("/probe/boom", **declare(AUTHENTICATED))
    def boom() -> None:
        raise RuntimeError("SELECT * FROM finance.transaction -- /srv/app/secret.py mat-khau")

    return router


def test_if_match_wrong_and_missing() -> None:
    """TC-GEN-05: If-Match sai → 412; thiếu → 428; đúng → ghi và trả ETag mới."""
    c = client(versioned_router())
    body = {"name": "A", "amount": 1}
    assert_problem(
        c.patch("/api/v1/probe/item", json=body, headers=safe_headers(**{"If-Match": '"2"'})), 412, "VERSION_CONFLICT"
    )
    assert_problem(c.patch("/api/v1/probe/item", json=body, headers=safe_headers()), 428, "PRECONDITION_REQUIRED")
    assert_problem(
        c.patch("/api/v1/probe/item", json=body, headers=safe_headers(**{"If-Match": "3"})), 412, "VERSION_CONFLICT"
    )
    ok = c.patch("/api/v1/probe/item", json=body, headers=safe_headers(**{"If-Match": '"3"'}))
    assert ok.status_code == 200 and ok.headers["etag"] == '"4"'


def test_server_error_is_problem_json_with_correlation_id() -> None:
    """TC-GEN-05: lỗi server giả lập → problem+json có correlation_id, không stack trace/SQL/đường dẫn."""
    c = client(versioned_router())
    response = c.get("/api/v1/probe/boom", headers={"X-Request-ID": "req-tc-gen-05"})
    body = assert_problem(response, 500, "INTERNAL_ERROR")
    assert body["correlation_id"] == "req-tc-gen-05"
    for leak in ("SELECT", "finance.transaction", "/srv/app", "mat-khau", "Traceback", "RuntimeError"):
        assert leak not in response.text


def test_validation_error_does_not_echo_input() -> None:
    c = client(versioned_router())
    response = c.patch(
        "/api/v1/probe/item",
        json={"name": "bi-mat-cccd-001", "amount": "khong-phai-so", "x": 1},
        headers=safe_headers(**{"If-Match": '"3"'}),
    )
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert {e["field"] for e in body["errors"]} == {"amount", "x"}
    assert "bi-mat" not in response.text and "khong-phai-so" not in response.text


def test_routing_errors_are_problem_json() -> None:
    c = client(versioned_router())
    assert_problem(c.get("/api/v1/khong-co"), 404, "NOT_FOUND")
    assert_problem(c.put("/api/v1/probe/item", headers=safe_headers()), 405, "METHOD_NOT_ALLOWED")


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (None, "PRECONDITION_REQUIRED"),
        ("", "PRECONDITION_REQUIRED"),
        ('W/"1"', "VERSION_CONFLICT"),
        ('"x"', "VERSION_CONFLICT"),
    ],
)
def test_require_if_match_errors(value: str | None, code: str) -> None:
    with pytest.raises(ApiError) as info:
        require_if_match(value)
    assert info.value.code == code


# ---------- Idempotency (TC-GEN-03, TC-GEN-04) ----------


def test_idempotency_key_header_rules() -> None:
    assert require_idempotency_key("abc-123_XYZ") == "abc-123_XYZ"
    for bad, code in [
        (None, "IDEMPOTENCY_KEY_REQUIRED"),
        ("", "IDEMPOTENCY_KEY_REQUIRED"),
        ("a" * 129, "VALIDATION_ERROR"),
        ("có dấu", "VALIDATION_ERROR"),
    ]:
        with pytest.raises(ApiError) as info:
            require_idempotency_key(bad)
        assert info.value.code == code


def test_fingerprint_canonical_json() -> None:
    a = request_fingerprint("POST", "/x", b'{"a": 1, "b": 2}', "u1")
    assert a == request_fingerprint("post", "/x", b'{"b":2,"a":1}', "u1")
    assert a != request_fingerprint("POST", "/x", b'{"a": 1, "b": 3}', "u1")
    assert a != request_fingerprint("POST", "/x", b'{"a": 1, "b": 2}', "u2")
    assert a != request_fingerprint("POST", "/y", b'{"a": 1, "b": 2}', "u1")


@pytest.fixture
def idempotent_app(database: ProvisionedDatabase) -> Iterator[tuple[TestClient, Engine, threading.Event]]:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE identity.probe_item (id uuid PRIMARY KEY, created_by text NOT NULL, "
            "idempotency_key text NOT NULL, request_hash text NOT NULL, amount text NOT NULL, "
            "UNIQUE (created_by, idempotency_key))"
        )
    owner.dispose()
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    factory: sessionmaker[Session] = make_session_factory(engine)
    slow = threading.Event()
    router = APIRouter()

    @router.post("/probe/items", status_code=201, **declare(AUTHENTICATED))
    async def create_item(request: Request) -> JSONResponse:
        key = require_idempotency_key(request.headers.get("idempotency-key"))
        actor = request.headers["x-test-user"]
        raw = await request.body()
        fingerprint = request_fingerprint(request.method, request.url.path, raw, actor)
        amount = str((await request.json())["amount"])

        def find(session: Session) -> tuple[str, dict[str, str]] | None:
            row = session.execute(
                text(
                    "SELECT id, request_hash, amount FROM identity.probe_item "
                    "WHERE created_by = :u AND idempotency_key = :k"
                ),
                {"u": actor, "k": key},
            ).one_or_none()
            return None if row is None else (row.request_hash, {"id": str(row.id), "amount": row.amount})

        def run() -> tuple[dict[str, str], bool]:
            with transaction(factory) as session:

                def create() -> dict[str, str]:
                    item_id = uuid.uuid4()
                    session.execute(
                        text("INSERT INTO identity.probe_item VALUES (:i, :u, :k, :h, :a)"),
                        {"i": item_id, "u": actor, "k": key, "h": fingerprint, "a": amount},
                    )
                    if slow.is_set():  # giữ transaction mở để request đồng thời đụng UNIQUE
                        threading.Event().wait(0.5)
                    return {"id": str(item_id), "amount": amount}

                return run_idempotent(session, fingerprint=fingerprint, find=lambda: find(session), create=create)

        from starlette.concurrency import run_in_threadpool

        result, _ = await run_in_threadpool(run)
        return JSONResponse(result, status_code=201)

    c = client(router)
    yield c, engine, slow
    engine.dispose()


def count_items(engine: Engine) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text("SELECT count(*) FROM identity.probe_item")).scalar_one())


def post_item(c: TestClient, key: str | None, body: dict[str, Any], user: str = "u1") -> Any:
    headers = safe_headers(**{"X-Test-User": user})
    if key is not None:
        headers["Idempotency-Key"] = key
    return c.post("/api/v1/probe/items", json=body, headers=headers)


@pytest.mark.db
def test_same_key_same_body_sequential(idempotent_app: tuple[TestClient, Engine, threading.Event]) -> None:
    """TC-GEN-03 (tuần tự): một bản ghi; hai response giống nhau."""
    c, engine, _ = idempotent_app
    first = post_item(c, "key-1", {"amount": "1250000.00"})
    second = post_item(c, "key-1", {"amount": "1250000.00"})
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert count_items(engine) == 1
    other_user = post_item(c, "key-1", {"amount": "1250000.00"}, user="u2")  # khóa theo người tạo
    assert other_user.status_code == 201 and other_user.json() != first.json()
    assert count_items(engine) == 2


@pytest.mark.db
def test_same_key_same_body_concurrent(idempotent_app: tuple[TestClient, Engine, threading.Event]) -> None:
    """TC-GEN-03 (đồng thời): hai request cùng lúc → một bản ghi; hai response giống nhau."""
    c, engine, slow = idempotent_app
    slow.set()
    barrier = threading.Barrier(2)
    responses: list[Any] = [None, None]

    def send(slot: int) -> None:
        barrier.wait()
        responses[slot] = post_item(c, "key-concurrent", {"amount": "5"})

    threads = [threading.Thread(target=send, args=(n,)) for n in (0, 1)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert [r.status_code for r in responses] == [201, 201]
    assert responses[0].json() == responses[1].json()
    assert count_items(engine) == 1


@pytest.mark.db
def test_same_key_different_body_conflict(idempotent_app: tuple[TestClient, Engine, threading.Event]) -> None:
    """TC-GEN-04: cùng key, body khác → 409 IDEMPOTENCY_KEY_REUSED, không ghi thêm."""
    c, engine, _ = idempotent_app
    assert post_item(c, "key-2", {"amount": "1"}).status_code == 201
    assert_problem(post_item(c, "key-2", {"amount": "2"}), 409, "IDEMPOTENCY_KEY_REUSED")
    assert count_items(engine) == 1


@pytest.mark.db
def test_missing_idempotency_key(idempotent_app: tuple[TestClient, Engine, threading.Event]) -> None:
    c, engine, _ = idempotent_app
    assert_problem(post_item(c, None, {"amount": "1"}), 400, "IDEMPOTENCY_KEY_REQUIRED")
    assert count_items(engine) == 0


# ---------- Giới hạn tốc độ ----------


def test_rate_limiter_window_and_retry_after() -> None:
    now = [100.0]
    limiter = RateLimiter(2, timedelta(seconds=60), clock=lambda: now[0])
    limiter.hit("ip:1", "acct:a")
    limiter.hit("ip:1", "acct:a")
    with pytest.raises(ApiError) as info:
        limiter.hit("ip:1", "acct:b")  # IP đã đủ lượt dù tài khoản khác
    assert info.value.code == "RATE_LIMITED" and info.value.headers == {"Retry-After": "60"}
    limiter.hit("ip:2", "acct:b")
    now[0] = 130.0
    with pytest.raises(ApiError) as info:
        limiter.hit("ip:1")
    assert info.value.headers == {"Retry-After": "30"}
    now[0] = 160.5
    limiter.hit("ip:1")  # lần đầu đã ra khỏi cửa sổ
    with pytest.raises(ValueError):
        RateLimiter(0, timedelta(seconds=1))


def test_rate_limited_response_has_retry_after() -> None:
    limiter = RateLimiter(1, timedelta(seconds=30))
    router = APIRouter()

    @router.post("/probe/login", **declare(PUBLIC))
    def login() -> dict[str, str]:
        limiter.hit("ip:test")
        return {"ok": "1"}

    c = client(router)
    assert c.post("/api/v1/probe/login", headers=safe_headers()).status_code == 200
    response = c.post("/api/v1/probe/login", headers=safe_headers())
    assert_problem(response, 429, "RATE_LIMITED")
    assert response.headers["retry-after"] == "30"
