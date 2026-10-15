"""Loader cấu hình và secret (T-004, Implementation_Plan §7, D-42).

- Mỗi biến được khai báo một lần trong `VARIABLES`: loại (secret/cấu hình), tiến trình dùng, bắt buộc hay không.
- Secret không có giá trị mặc định; đọc từ `NAME` hoặc từ file ở `NAME_FILE` (Docker secrets), không được đặt cả hai.
- Lỗi chỉ nêu tên biến, không bao giờ chứa giá trị.
- Kiểm tra nội dung (định dạng URL, số phút, JSON provider…) thuộc task dùng biến (T-005, T-007, T-102, T-204).
"""

import enum
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

FILE_SUFFIX = "_FILE"
LLM_API_KEY_PREFIX = "AIEOS_LLM_API_KEY_"
MASK = "***"


class Process(enum.Enum):
    API = "api"
    WORKER = "worker"
    MIGRATE = "migrate"
    ADMIN_CLI = "admin-cli"  # bootstrap-admin, recover-admin (T-106, ADR-006 A2/A6)


class Kind(enum.Enum):
    SECRET = "secret"
    CONFIG = "config"


@dataclass(frozen=True)
class Variable:
    name: str
    kind: Kind
    processes: frozenset[Process]
    required: bool = True
    note: str = ""


_API = frozenset({Process.API})
_WORKER = frozenset({Process.WORKER})
_API_WORKER = frozenset({Process.API, Process.WORKER})
_API_CLI = frozenset({Process.API, Process.ADMIN_CLI})

VARIABLES: tuple[Variable, ...] = (
    Variable("AIEOS_DATABASE_URL", Kind.SECRET, _API_WORKER | _API_CLI, note="role aieos_app"),
    Variable("AIEOS_DATABASE_OWNER_URL", Kind.SECRET, frozenset({Process.MIGRATE}), note="role aieos_owner"),
    Variable("AIEOS_CSRF_KEY", Kind.SECRET, _API),
    Variable("AIEOS_TOTP_ENCRYPTION_KEY", Kind.SECRET, _API),
    Variable("AIEOS_STORAGE_PATH", Kind.CONFIG, _API_WORKER),
    Variable("AIEOS_ALLOWED_ORIGINS", Kind.CONFIG, _API),
    Variable("AIEOS_SCANNER_HOST", Kind.CONFIG, _WORKER),
    # Không có provider vẫn phải chạy được (SRS-NFR-07); điều kiện bắt buộc khi có provider thuộc T-204 (D-08, GAP-14).
    Variable("AIEOS_LLM_PROVIDERS", Kind.CONFIG, _API_WORKER, required=False, note="JSON, T-204"),
    Variable("AIEOS_OCR_PROVIDERS", Kind.CONFIG, _API_WORKER, required=False, note="JSON, T-204"),
    Variable("AIEOS_AI_BUDGET_LIMIT", Kind.CONFIG, _API_WORKER, required=False, note="GAP-14, T-204"),
    Variable("AIEOS_SESSION_IDLE_MINUTES", Kind.CONFIG, _API),
    Variable("AIEOS_SESSION_ABSOLUTE_HOURS", Kind.CONFIG, _API),
    Variable("AIEOS_INVITE_TTL_HOURS", Kind.CONFIG, _API),
    Variable("AIEOS_REAUTH_MINUTES", Kind.CONFIG, _API),
    # Giới hạn thử và khóa tạm (D-57, SRS-IAM-07): bắt buộc, không mặc định — người vận hành đặt khi triển khai.
    Variable("AIEOS_AUTH_RATE_LIMIT_ATTEMPTS", Kind.CONFIG, _API, note="D-57"),
    Variable("AIEOS_AUTH_RATE_LIMIT_WINDOW_SECONDS", Kind.CONFIG, _API, note="D-57"),
    Variable("AIEOS_AUTH_LOCKOUT_THRESHOLD", Kind.CONFIG, _API, note="SRS-IAM-07, nguyên tắc D-57"),
    Variable("AIEOS_AUTH_LOCKOUT_MINUTES", Kind.CONFIG, _API, note="SRS-IAM-07, nguyên tắc D-57"),
    # Chính sách mật khẩu (D-58): bắt buộc, không mặc định — CLI T-106, đổi mật khẩu T-104, lời mời T-105.
    Variable("AIEOS_PASSWORD_MIN_LENGTH", Kind.CONFIG, _API_CLI, note="D-58"),
    # Dùng bởi công cụ backup (T-605), không phải tiến trình Python của AI-EOS.
    Variable("AIEOS_BACKUP_TARGET", Kind.CONFIG, frozenset(), required=False, note="T-605"),
)
_BY_NAME = {v.name: v for v in VARIABLES}


def is_secret_name(name: str) -> bool:
    """Tên biến chứa secret: khai báo SECRET hoặc khóa API provider `AIEOS_LLM_API_KEY_<NAME>` (Plan §7)."""
    base = name.removesuffix(FILE_SUFFIX)
    variable = _BY_NAME.get(base)
    return (variable is not None and variable.kind is Kind.SECRET) or base.startswith(LLM_API_KEY_PREFIX)


class Secret:
    """Giá trị secret; `str`/`repr` luôn che, chỉ `reveal()` trả giá trị thật."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"Secret({MASK})"

    def __str__(self) -> str:
        return MASK


class ConfigError(Exception):
    """Cấu hình không hợp lệ; thông điệp chỉ chứa tên biến."""

    def __init__(self, process: Process, problems: list[str]) -> None:
        self.process = process
        self.problems = problems
        super().__init__(f"Cấu hình không hợp lệ cho tiến trình {process.value}: " + "; ".join(problems))


@dataclass(frozen=True)
class Settings:
    process: Process
    _values: Mapping[str, str | Secret]

    def config(self, name: str) -> str:
        value = self._lookup(name, Kind.CONFIG)
        if not isinstance(value, str):
            raise KeyError(f"{name} không được đặt")
        return value

    def optional_config(self, name: str) -> str | None:
        value = self._lookup(name, Kind.CONFIG)
        return value if isinstance(value, str) else None

    def secret(self, name: str) -> Secret:
        value = self._lookup(name, Kind.SECRET)
        if not isinstance(value, Secret):
            raise KeyError(f"{name} không được đặt")
        return value

    def provider_key(self, provider: str) -> Secret | None:
        """Khóa API của provider `AIEOS_LLM_API_KEY_<PROVIDER>` (T-204); không đặt → `None`."""
        value = self._values.get(LLM_API_KEY_PREFIX + provider.upper())
        return value if isinstance(value, Secret) else None

    def _lookup(self, name: str, kind: Kind) -> str | Secret | None:
        variable = _BY_NAME.get(name)
        if variable is None or variable.kind is not kind or self.process not in variable.processes:
            raise KeyError(f"{name} không phải biến {kind.value} của tiến trình {self.process.value}")
        return self._values.get(name)

    def __repr__(self) -> str:
        return f"Settings(process={self.process.value}, names={sorted(self._values)})"


def _read(variable: Variable, environ: Mapping[str, str], problems: list[str]) -> str | None:
    direct = environ.get(variable.name)
    file_name = variable.name + FILE_SUFFIX
    file_path = environ.get(file_name) if variable.kind is Kind.SECRET else None
    if direct is not None and file_path is not None:
        problems.append(f"{variable.name} và {file_name} cùng được đặt (chỉ dùng một)")
        return None
    if file_path is not None:
        try:
            direct = Path(file_path).read_text(encoding="utf-8").rstrip("\r\n")
        except OSError:
            problems.append(f"không đọc được file của {file_name}")
            return None
    if direct is None or direct.strip() == "":
        if variable.required:
            hint = f" (hoặc {file_name})" if variable.kind is Kind.SECRET else ""
            problems.append(f"thiếu {variable.kind.value} {variable.name}{hint}")
        return None
    return direct


def load_settings(process: Process, environ: Mapping[str, str] | None = None) -> Settings:
    """Đọc và kiểm tra mọi biến của `process`; lỗi → `ConfigError` liệt kê toàn bộ vấn đề (chỉ tên biến)."""
    env = os.environ if environ is None else environ
    problems: list[str] = []
    values: dict[str, str | Secret] = {}
    for variable in VARIABLES:
        if process not in variable.processes:
            continue
        raw = _read(variable, env, problems)
        if raw is not None:
            values[variable.name] = Secret(raw) if variable.kind is Kind.SECRET else raw
    if process in _API_WORKER:
        names = {k.removesuffix(FILE_SUFFIX) for k in env if k.startswith(LLM_API_KEY_PREFIX)}
        for name in sorted(names):  # tên do cấu hình provider quyết định; bắt buộc hay không: T-204 kiểm
            raw = _read(Variable(name, Kind.SECRET, _API_WORKER, required=False), env, problems)
            if raw is not None:
                values[name] = Secret(raw)
    if problems:
        raise ConfigError(process, problems)
    return Settings(process, values)


def load_settings_or_exit(process: Process) -> Settings:
    """Dùng khi tiến trình khởi động: cấu hình lỗi → in lỗi (không giá trị) ra stderr và thoát mã 2."""
    try:
        return load_settings(process)
    except ConfigError as error:
        _exit(error)


def _exit(error: ConfigError) -> NoReturn:
    print(str(error), file=sys.stderr)
    raise SystemExit(2)
