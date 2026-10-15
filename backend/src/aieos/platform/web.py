"""Cơ chế tạo ứng dụng FastAPI, correlation ID, health (T-006, ADR-002, ADR-012, API-SYS-01, API-SYS-02, D-42).

- Correlation ID: nhận `X-Request-ID` nếu hợp lệ, không thì sinh mới; đặt vào contextvar cho log và trả lại trong
  header response.
- Log mỗi request: phương thức, đường dẫn (không query string), status, thời gian — không log header, cookie, body.
- `/api/v1/health/live`: tiến trình sống. `/api/v1/health/ready`: mọi kiểm tra đạt → 200, ngược lại 503; body chỉ có
  trạng thái, không lộ kiểm tra nào lỗi (tên kiểm tra lỗi chỉ ghi vào log).
- `/docs`, `/redoc`, `/openapi.json` tắt ở HTTP; OpenAPI vẫn sinh được bằng `app.openapi()` cho contract test.
- `app` (composition root) truyền các kiểm tra readiness, cấu hình CSRF và gắn router của module.
- Lỗi (T-007, SRS-GEN-05): mọi lỗi trả `application/problem+json` có `correlation_id` — `ApiError`, lỗi định tuyến
  (404/405), lỗi validation (422, không lặp lại giá trị đầu vào), lỗi không lường trước (500 `INTERNAL_ERROR`, không
  stack trace, vẫn có header `X-Request-ID`).
"""

import logging
import re
import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from aieos.platform.errors import ERROR_CATALOG, STATUS_CODES, ApiError, problem_response
from aieos.platform.http import CsrfConfig, CsrfMiddleware
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
        response_started = False

        async def send_with_id(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != REQUEST_ID_HEADER.encode()]
                message["headers"] = [*headers, (REQUEST_ID_HEADER.encode(), correlation_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            _log.exception("request_failed", extra={"method": scope["method"], "path": scope["path"]})
            if response_started:
                raise
            # Trả lỗi ngay trong middleware để response 500 vẫn có `X-Request-ID` và `correlation_id`.
            await problem_response(ApiError("INTERNAL_ERROR"))(scope, receive, send_with_id)
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


def _validation_errors(error: RequestValidationError) -> list[dict[str, str]]:
    """Chỉ vị trí và thông điệp của trường lỗi; không lặp lại giá trị đầu vào (có thể là dữ liệu nhạy cảm)."""
    result = []
    for item in error.errors():
        location = [str(part) for part in item.get("loc", ()) if part not in ("body", "query", "path", "header")]
        result.append({"field": ".".join(location), "message": str(item.get("msg", ""))})
    return result


def _install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return problem_response(error)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return problem_response(ApiError("VALIDATION_ERROR", errors=_validation_errors(error)))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        code = STATUS_CODES.get(error.status_code, "INTERNAL_ERROR")
        response = problem_response(ApiError(code, headers=dict(error.headers or {})))
        if ERROR_CATALOG[code] != error.status_code and code == "INTERNAL_ERROR":
            _log.warning("unmapped_http_status", extra={"status": error.status_code})
        return response


def create_api(
    readiness_checks: Mapping[str, ReadinessCheck],
    routers: tuple[APIRouter, ...] = (),
    *,
    csrf: CsrfConfig,
) -> FastAPI:
    app = FastAPI(title="AI-EOS", docs_url=None, redoc_url=None, openapi_url=None)
    _install_error_handlers(app)
    # add_middleware chèn vào ngoài cùng: CSRF chạy bên trong correlation ID để lỗi 403 có correlation_id.
    app.add_middleware(CsrfMiddleware, config=csrf, prefix=API_PREFIX)
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
