"""Cơ chế tạo ứng dụng FastAPI, correlation ID, health (T-006, ADR-002, ADR-012, API-SYS-01, API-SYS-02, D-42).

- Correlation ID: nhận `X-Request-ID` nếu hợp lệ, không thì sinh mới; đặt vào contextvar cho log và trả lại trong
  header response.
- Log mỗi request: phương thức, đường dẫn (không query string), status, thời gian — không log header, cookie, body.
- `/api/v1/health/live`: tiến trình sống. `/api/v1/health/ready`: mọi kiểm tra đạt → 200, ngược lại 503; body chỉ có
  trạng thái, không lộ kiểm tra nào lỗi (tên kiểm tra lỗi chỉ ghi vào log).
- `/docs`, `/redoc`, `/openapi.json` tắt ở HTTP; OpenAPI vẫn sinh được bằng `app.openapi()` cho contract test.
- `app` (composition root) truyền các kiểm tra readiness và gắn router của module.
"""

import logging
import re
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aieos.platform.logs import CORRELATION_ID

API_PREFIX = "/api/v1"
REQUEST_ID_HEADER = "x-request-id"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,127}")

ReadinessCheck = Callable[[], bool]

_log = logging.getLogger("aieos.http")


def accept_request_id(value: str | None) -> str:
    """Giữ `X-Request-ID` hợp lệ (8–128 ký tự chữ, số, `.`, `_`, `-`); ngược lại sinh mới."""
    if value is not None and _VALID_REQUEST_ID.fullmatch(value):
        return value
    return uuid.uuid4().hex


class CorrelationIdMiddleware:
    """Middleware ASGI thuần (không dùng BaseHTTPMiddleware để contextvar đi theo request)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = next((v.decode("latin-1") for k, v in scope["headers"] if k == REQUEST_ID_HEADER.encode()), None)
        correlation_id = accept_request_id(incoming)
        token = CORRELATION_ID.set(correlation_id)
        status = 500
        started = time.perf_counter()

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != REQUEST_ID_HEADER.encode()]
                message["headers"] = [*headers, (REQUEST_ID_HEADER.encode(), correlation_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            _log.exception("request_failed", extra={"method": scope["method"], "path": scope["path"]})
            raise
        finally:
            _log.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            CORRELATION_ID.reset(token)


def _run_checks(checks: Mapping[str, ReadinessCheck]) -> list[str]:
    failed: list[str] = []
    for name, check in checks.items():
        try:
            ok = check()
        except Exception as error:  # chỉ ghi loại lỗi; thông điệp có thể chứa chi tiết nội bộ
            _log.warning("readiness_check_error", extra={"check": name, "error_type": type(error).__name__})
            ok = False
        if not ok:
            failed.append(name)
    return failed


def create_api(readiness_checks: Mapping[str, ReadinessCheck], routers: tuple[APIRouter, ...] = ()) -> FastAPI:
    app = FastAPI(title="AI-EOS", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(CorrelationIdMiddleware)
    checks = dict(readiness_checks)
    health = APIRouter(prefix=f"{API_PREFIX}/health", tags=["system"])

    @health.get("/live")
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @health.get("/ready", responses={503: {"description": "Chưa sẵn sàng"}})
    def ready() -> Any:
        failed = _run_checks(checks)
        if failed:
            _log.warning("not_ready", extra={"failed_checks": failed})
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {"status": "ready"}

    app.include_router(health)
    for router in routers:
        app.include_router(router, prefix=API_PREFIX)
    return app
