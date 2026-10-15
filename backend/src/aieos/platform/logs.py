"""Log JSON ra stdout, correlation ID, che dữ liệu nhạy cảm (T-006, ADR-012, SRS-GEN-05, TC-SEC-05).

- Chỉ `platform` cấu hình logging toàn cục (C7); module khác dùng `logging.getLogger(__name__)`.
- Mỗi dòng log là một object JSON: `ts` (UTC), `level`, `logger`, `message`, `correlation_id` và trường `extra`.
- Trường `extra` có tên nhạy cảm (authorization, cookie, password, token, secret, csrf, api key, mã OTP/MFA, session…)
  hoặc là tên biến secret (T-004) bị thay bằng `***`; giá trị `Secret` luôn hiển thị `***`.
- Không log header, body hay query string của request (xem `platform.web`); logger `httpx`, `httpcore` chỉ từ WARNING
  (chúng ghi URL đầy đủ ở INFO).
- Che theo **nội dung** (Q-55, quyết định CDA 16/10/2026): `message`, mọi chuỗi trong `extra` (kể cả lồng nhau),
  traceback và stack đi qua `platform.privacy.mask_pii` — dữ liệu cá nhân phát hiện được thay bằng `•••`. Cấu trúc
  JSON, tên lớp lỗi, tên hàm và số dòng trong traceback giữ nguyên. Heuristic không bắt được mọi dữ liệu cá nhân:
  nơi gọi vẫn không được log prompt, câu trả lời AI, nội dung tài liệu hay payload (CLAUDE.md §6).
"""

import json
import logging
import re
import sys
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import IO, Any

from aieos.platform.config import Secret, is_secret_name
from aieos.platform.privacy import mask_pii

REDACTED = "***"
CORRELATION_ID: ContextVar[str | None] = ContextVar("aieos_correlation_id", default=None)
_SENSITIVE_KEY = re.compile(
    r"authorization|cookie|passw|secret|token|csrf|api[_-]?key|otp|mfa|totp|session|credential", re.IGNORECASE
)
# Logger thư viện ghi URL đầy đủ (kể cả query string có thể chứa token/khóa) ở mức INFO → chỉ cho WARNING trở lên.
_QUIET_LIBRARY_LOGGERS = ("httpx", "httpcore")
_STANDARD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY.search(key)) or is_secret_name(key)


def redact(value: Any, key: str | None = None) -> Any:
    """Trả về bản sao an toàn để log: che theo tên khóa, đệ quy qua dict/list."""
    if key is not None and is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Secret):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [redact(v) for v in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)


def _mask_content(value: Any) -> Any:
    """Che dữ liệu cá nhân trong mọi chuỗi của giá trị đã `redact` (dict/list lồng nhau)."""
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _mask_content(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask_content(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_pii(record.getMessage()),
            "correlation_id": CORRELATION_ID.get(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = _mask_content(redact(value, key))
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            payload["exc"] = mask_pii(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack"] = mask_pii(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: int | str = logging.INFO, stream: IO[str] | None = None) -> None:
    """Thay handler của root logger bằng một handler JSON (gọi một lần khi tiến trình khởi động; gọi lại an toàn)."""
    handler = logging.StreamHandler(stream if stream is not None else sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    for name in _QUIET_LIBRARY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
