"""Hạ tầng HTTP dùng chung (T-007, D-42): CSRF + `Origin`, idempotency, `ETag`/`If-Match`, giới hạn tốc độ.

- **CSRF (SRS-GEN-02, ADR-006, API_Specification §1.3):** mọi `POST`/`PUT`/`PATCH`/`DELETE` dưới `/api/v1` phải có
  `Origin` thuộc `AIEOS_ALLOWED_ORIGINS` và `X-CSRF-Token` khớp session. Token đồng bộ, gắn session, không lưu:
  `HMAC-SHA256(AIEOS_CSRF_KEY, token session)` (`csrf_token`) — `GET /auth/me` (T-102) trả token này. Đường dẫn
  công khai không có session (đăng nhập, xác minh MFA, chấp nhận lời mời — API_Specification §1.2) do composition
  root khai báo ở `exempt_paths`: chỉ miễn token, vẫn kiểm `Origin`.
- **Idempotency (SRS-GEN-03, §1.6, INV-08):** khóa lưu ở chính bảng tài nguyên (`UNIQUE (created_by, idempotency_key)`)
  kèm dấu vân tay request; `run_idempotent` trả lại kết quả cũ khi cùng khóa + cùng nội dung, `409
  IDEMPOTENCY_KEY_REUSED` khi khác nội dung, an toàn khi hai request đồng thời (savepoint + ràng buộc UNIQUE).
- **Đồng thời (SRS-GEN-04, §1.7):** `etag`, `require_if_match` (thiếu → 428), `check_version` (lệch → 412).
- **Giới hạn tốc độ (§1.9):** `RateLimiter` cửa sổ trượt trong bộ nhớ tiến trình; giới hạn do nơi gọi truyền (tài liệu
  chưa có giá trị). Giới hạn theo từng tiến trình API — `[CẦN XÁC NHẬN]` khi chạy nhiều worker ASGI
  (Implementation_Plan §20).
"""

import base64
import hashlib
import hmac
import json
import math
import threading
import time
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import timedelta
from urllib.parse import urlsplit

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import cookie_parser
from starlette.types import ASGIApp, Receive, Scope, Send

from aieos.platform.config import Secret
from aieos.platform.errors import ApiError, problem_response

SESSION_COOKIE = "__Host-aieos_session"
CSRF_HEADER = "x-csrf-token"
IDEMPOTENCY_HEADER = "Idempotency-Key"
MAX_IDEMPOTENCY_KEY_LENGTH = 128
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# ---------- CSRF + Origin ----------


class OriginConfigError(ValueError):
    """`AIEOS_ALLOWED_ORIGINS` không hợp lệ; thông điệp chỉ nêu tên biến."""


def parse_allowed_origins(value: str) -> frozenset[str]:
    """`AIEOS_ALLOWED_ORIGINS`: danh sách origin cách nhau bởi dấu phẩy, dạng `scheme://host[:port]`."""
    origins: set[str] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        parts = urlsplit(item)
        if parts.scheme not in {"http", "https"} or not parts.hostname or item.rstrip("/") != item:
            raise OriginConfigError("AIEOS_ALLOWED_ORIGINS: origin phải có dạng scheme://host[:port]")
        if parts.path or parts.query or parts.fragment or parts.username or parts.password:
            raise OriginConfigError(
                "AIEOS_ALLOWED_ORIGINS: origin không được có đường dẫn, query hay thông tin đăng nhập"
            )
        origins.add(f"{parts.scheme}://{parts.netloc}".lower())
    if not origins:
        raise OriginConfigError("AIEOS_ALLOWED_ORIGINS: cần ít nhất một origin")
    return frozenset(origins)


def csrf_token(key: Secret, session_token: str) -> str:
    """Token CSRF đồng bộ của session (không lưu): HMAC-SHA256 của token session bằng `AIEOS_CSRF_KEY`."""
    digest = hmac.new(key.reveal().encode(), b"csrf:" + session_token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@dataclass(frozen=True)
class CsrfConfig:
    key: Secret
    allowed_origins: frozenset[str]
    exempt_paths: frozenset[str] = field(default_factory=frozenset)


class CsrfMiddleware:
    """Từ chối request thay đổi trạng thái thiếu/sai `Origin` hoặc `X-CSRF-Token` với `403 CSRF_FAILED`."""

    def __init__(self, app: ASGIApp, config: CsrfConfig, prefix: str) -> None:
        self.app = app
        self.config = config
        self.prefix = prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS and scope["path"].startswith(self.prefix):
            if not self._allowed(scope):
                await problem_response(ApiError("CSRF_FAILED"))(scope, receive, send)
                return
        await self.app(scope, receive, send)

    def _allowed(self, scope: Scope) -> bool:
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        origin = headers.get("origin", "").lower()
        if origin not in self.config.allowed_origins:
            return False
        if scope["path"] in self.config.exempt_paths:
            return True
        session = cookie_parser(headers.get("cookie", "")).get(SESSION_COOKIE)
        sent = headers.get(CSRF_HEADER)
        if not session or not sent:
            return False
        return hmac.compare_digest(sent, csrf_token(self.config.key, session))


# ---------- Idempotency ----------


def require_idempotency_key(value: str | None) -> str:
    """Header `Idempotency-Key` bắt buộc: 1–128 ký tự ASCII nhìn thấy được, không khoảng trắng."""
    if value is None or value == "":
        raise ApiError("IDEMPOTENCY_KEY_REQUIRED")
    if len(value) > MAX_IDEMPOTENCY_KEY_LENGTH or not all(33 <= ord(c) <= 126 for c in value):
        raise ApiError(
            "VALIDATION_ERROR",
            errors=[{"field": IDEMPOTENCY_HEADER, "message": "Tối đa 128 ký tự ASCII, không khoảng trắng"}],
        )
    return value


def request_fingerprint(method: str, path: str, body: bytes, actor: str) -> str:
    """Dấu vân tay nội dung request; JSON được chuẩn hóa (thứ tự khóa, khoảng trắng không ảnh hưởng)."""
    try:
        canonical = json.dumps(json.loads(body), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    except (ValueError, UnicodeDecodeError):
        canonical = body
    material = b"\n".join([method.upper().encode(), path.encode(), actor.encode(), canonical])
    return hashlib.sha256(material).hexdigest()


def run_idempotent[T](
    session: Session,
    *,
    fingerprint: str,
    find: Callable[[], tuple[str, T] | None],
    create: Callable[[], T],
) -> tuple[T, bool]:
    """Tạo tài nguyên một lần cho mỗi khóa idempotency; trả về (kết quả, có phải phát lại không).

    `find()` tìm bản ghi theo (người tạo, khóa) và trả về (dấu vân tay đã lưu, kết quả); `create()` ghi bản ghi kèm
    dấu vân tay — bảng phải có `UNIQUE (created_by, idempotency_key)` (INV-08). Request đồng thời cùng khóa: request
    sau chờ request trước commit, gặp vi phạm UNIQUE, rollback savepoint rồi phát lại kết quả đã commit.
    """

    def replay(existing: tuple[str, T]) -> tuple[T, bool]:
        stored, result = existing
        if not hmac.compare_digest(stored, fingerprint):
            raise ApiError("IDEMPOTENCY_KEY_REUSED")
        return result, True

    existing = find()
    if existing is not None:
        return replay(existing)
    try:
        with session.begin_nested():
            return create(), False
    except IntegrityError:
        existing = find()
        if existing is None:
            raise
        return replay(existing)


# ---------- ETag / If-Match ----------


def etag(version: int) -> str:
    return f'"{version}"'


def require_if_match(value: str | None) -> int:
    """Phiên bản trong `If-Match`; thiếu → `428 PRECONDITION_REQUIRED`, sai định dạng → `412 VERSION_CONFLICT`."""
    if value is None or value.strip() == "":
        raise ApiError("PRECONDITION_REQUIRED")
    raw = value.strip()
    if not (len(raw) >= 3 and raw[0] == raw[-1] == '"' and raw[1:-1].isdigit()):
        raise ApiError("VERSION_CONFLICT")
    return int(raw[1:-1])


def check_version(current: int, expected: int) -> None:
    if current != expected:
        raise ApiError("VERSION_CONFLICT")


# ---------- Giới hạn tốc độ ----------


class RateLimiter:
    """Cửa sổ trượt trong bộ nhớ: tối đa `limit` lần mỗi `window` cho mỗi khóa (vd. IP, tài khoản).

    Không có giá trị mặc định — nơi gọi truyền giới hạn. Phạm vi một tiến trình (nhiều worker ASGI → mỗi worker một bộ
    đếm).
    """

    def __init__(self, limit: int, window: timedelta, clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 1 or window <= timedelta(0):
            raise ValueError("limit ≥ 1 và window > 0")
        self.limit = limit
        self.window = window.total_seconds()
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, *keys: str) -> None:
        """Ghi một lần thử cho mỗi khóa; vượt giới hạn ở bất kỳ khóa nào → `429 RATE_LIMITED` + `Retry-After`."""
        now = self.clock()
        with self._lock:
            waits = [self._wait(key, now) for key in keys]
            blocked = [w for w in waits if w > 0]
            if blocked:
                retry = max(1, math.ceil(max(blocked)))
                raise ApiError("RATE_LIMITED", headers={"Retry-After": str(retry)})
            for key in keys:
                self._hits.setdefault(key, deque()).append(now)

    def _wait(self, key: str, now: float) -> float:
        hits = self._hits.get(key)
        if hits is None:
            return 0.0
        while hits and hits[0] <= now - self.window:
            hits.popleft()
        if len(hits) < self.limit:
            return 0.0
        return hits[0] + self.window - now

    def reset(self, keys: Iterable[str]) -> None:
        with self._lock:
            for key in keys:
                self._hits.pop(key, None)
