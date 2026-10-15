"""Lỗi API dạng `application/problem+json` (T-007, SRS-GEN-05, API_Specification §1.5, §10).

- `ERROR_CATALOG`: mã lỗi → HTTP status, khớp bảng API_Specification §10 (test đối chiếu tài liệu ↔ code).
- `ApiError`: ngoại lệ mang mã lỗi; `detail` và `errors` là thông điệp do code viết, không bao giờ là thông điệp gốc
  của ngoại lệ (có thể chứa SQL, đường dẫn, dữ liệu).
- Body luôn có `correlation_id`; không có stack trace.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi.responses import JSONResponse

from aieos.platform.logs import CORRELATION_ID

PROBLEM_MEDIA_TYPE = "application/problem+json"
ERROR_TYPE_BASE = "https://aieos.local/errors/"

ERROR_CATALOG: Mapping[str, int] = {
    "VALIDATION_ERROR": 422,
    "UNAUTHENTICATED": 401,
    "INVALID_CREDENTIALS": 401,
    "REAUTH_REQUIRED": 401,
    "MFA_REQUIRED": 401,
    "FORBIDDEN": 403,
    "CSRF_FAILED": 403,
    "SELF_APPROVAL_FORBIDDEN": 403,
    "SELF_ROLE_CHANGE": 403,
    "NOT_FOUND": 404,
    "METHOD_NOT_ALLOWED": 405,
    "INVALID_STATE": 409,
    "PERIOD_CLOSED": 409,
    "NO_OPEN_PERIOD": 409,
    "PERIOD_OVERLAP": 409,
    "PERIOD_HAS_PENDING": 409,
    "ALREADY_REVERSED": 409,
    "LAST_ADMIN": 409,
    "IDEMPOTENCY_KEY_REUSED": 409,
    "UNDO_WINDOW_EXPIRED": 409,
    "INVITATION_INVALID": 400,
    "IDEMPOTENCY_KEY_REQUIRED": 400,
    "VERSION_CONFLICT": 412,
    "PRECONDITION_REQUIRED": 428,
    "FILE_TOO_LARGE": 413,
    "UNSUPPORTED_FILE_TYPE": 415,
    "ACCOUNT_LOCKED": 423,
    "ROLE_COMBINATION_FORBIDDEN": 422,
    "ASSIGNMENT_NOT_ELIGIBLE": 422,
    "AUTONOMY_CAP_EXCEEDED": 422,
    "CANNOT_REVERSE_REVERSAL": 422,
    "CRITICAL_FIELDS_NOT_REVIEWED": 422,
    "AUTO_COMMIT_CRITERIA_NOT_MET": 422,
    "TOO_MANY_FILES": 422,
    "RATE_LIMITED": 429,
    "INTERNAL_ERROR": 500,
    "AI_UNAVAILABLE": 503,
}

# Status do router/Starlette trả (route không tồn tại, sai method…) → mã lỗi.
STATUS_CODES: Mapping[int, str] = {
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_FILE_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
}


class ApiError(Exception):
    """Lỗi nghiệp vụ/HTTP có mã trong `ERROR_CATALOG`; được chuyển thành `problem+json`."""

    def __init__(
        self,
        code: str,
        detail: str | None = None,
        *,
        errors: Sequence[Mapping[str, str]] = (),
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if code not in ERROR_CATALOG:
            raise ValueError(f"Mã lỗi không có trong API_Specification §10: {code}")
        super().__init__(code)
        self.code = code
        self.status = ERROR_CATALOG[code]
        self.detail = detail
        self.errors = list(errors)
        self.headers = dict(headers or {})


def title_for(code: str) -> str:
    return code.replace("_", " ").capitalize()


def problem_body(
    code: str, status: int, detail: str | None = None, errors: Sequence[Mapping[str, str]] = ()
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": ERROR_TYPE_BASE + code,
        "title": title_for(code),
        "status": status,
        "code": code,
        "correlation_id": CORRELATION_ID.get(),
    }
    if detail:
        body["detail"] = detail
    if errors:
        body["errors"] = [dict(e) for e in errors]
    return body


def problem_response(error: ApiError) -> JSONResponse:
    return JSONResponse(
        problem_body(error.code, error.status, error.detail, error.errors),
        status_code=error.status,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=error.headers,
    )
