"""T-004: loader cấu hình và secret (Implementation_Plan §4, §7; D-42)."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from aieos.platform.api import (
    VARIABLES,
    ConfigError,
    Kind,
    Process,
    Secret,
    is_secret_name,
    load_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / "infra" / ".env.example"


def full_env(process: Process) -> dict[str, str]:
    """Môi trường đủ mọi biến bắt buộc của `process`; mỗi giá trị là một chuỗi canh gác duy nhất."""
    return {v.name: f"sentinel-{v.name.lower()}" for v in VARIABLES if process in v.processes and v.required}


@pytest.mark.parametrize("process", list(Process))
def test_loads_when_all_required_present(process: Process) -> None:
    env = full_env(process)
    settings = load_settings(process, env)
    for v in VARIABLES:
        if process not in v.processes or not v.required:
            continue
        if v.kind is Kind.SECRET:
            assert settings.secret(v.name).reveal() == env[v.name]
        else:
            assert settings.config(v.name) == env[v.name]


def test_missing_secret_is_reported_by_name_without_values() -> None:
    env = full_env(Process.API)
    del env["AIEOS_CSRF_KEY"]
    with pytest.raises(ConfigError) as info:
        load_settings(Process.API, env)
    message = str(info.value)
    assert "AIEOS_CSRF_KEY" in message
    assert all(value not in message for value in env.values())


def test_reports_every_problem_at_once() -> None:
    with pytest.raises(ConfigError) as info:
        load_settings(Process.API, {})
    required = {v.name for v in VARIABLES if Process.API in v.processes and v.required}
    assert len(info.value.problems) == len(required)


@pytest.mark.parametrize("blank", ["", "   "])
def test_blank_value_counts_as_missing(blank: str) -> None:
    env = full_env(Process.WORKER) | {"AIEOS_DATABASE_URL": blank}
    with pytest.raises(ConfigError, match="AIEOS_DATABASE_URL"):
        load_settings(Process.WORKER, env)


def test_processes_only_require_their_own_variables() -> None:
    migrate = load_settings(Process.MIGRATE, {"AIEOS_DATABASE_OWNER_URL": "x"})
    assert migrate.secret("AIEOS_DATABASE_OWNER_URL").reveal() == "x"
    worker_env = full_env(Process.WORKER)
    assert "AIEOS_CSRF_KEY" not in worker_env
    worker = load_settings(Process.WORKER, worker_env)
    with pytest.raises(KeyError):
        worker.secret("AIEOS_CSRF_KEY")


def test_optional_variables() -> None:
    settings = load_settings(Process.API, full_env(Process.API))
    assert settings.optional_config("AIEOS_LLM_PROVIDERS") is None
    env = full_env(Process.API) | {"AIEOS_LLM_PROVIDERS": "[]"}
    assert load_settings(Process.API, env).optional_config("AIEOS_LLM_PROVIDERS") == "[]"


def test_secret_from_file(tmp_path: Path) -> None:
    secret_file = tmp_path / "csrf"
    secret_file.write_text("value-from-file\n", encoding="utf-8")
    env = full_env(Process.API)
    del env["AIEOS_CSRF_KEY"]
    env["AIEOS_CSRF_KEY_FILE"] = str(secret_file)
    assert load_settings(Process.API, env).secret("AIEOS_CSRF_KEY").reveal() == "value-from-file"


def test_secret_value_and_file_together_rejected(tmp_path: Path) -> None:
    secret_file = tmp_path / "csrf"
    secret_file.write_text("a", encoding="utf-8")
    env = full_env(Process.API) | {"AIEOS_CSRF_KEY_FILE": str(secret_file)}
    with pytest.raises(ConfigError, match="AIEOS_CSRF_KEY_FILE"):
        load_settings(Process.API, env)


def test_unreadable_secret_file_rejected_without_path(tmp_path: Path) -> None:
    missing = tmp_path / "khong-co"
    env = full_env(Process.API)
    del env["AIEOS_CSRF_KEY"]
    env["AIEOS_CSRF_KEY_FILE"] = str(missing)
    with pytest.raises(ConfigError) as info:
        load_settings(Process.API, env)
    assert "AIEOS_CSRF_KEY_FILE" in str(info.value)
    assert str(missing) not in str(info.value)


def test_config_variables_do_not_read_file_suffix(tmp_path: Path) -> None:
    path_file = tmp_path / "p"
    path_file.write_text("x", encoding="utf-8")
    env = full_env(Process.API)
    del env["AIEOS_STORAGE_PATH"]
    env["AIEOS_STORAGE_PATH_FILE"] = str(path_file)
    with pytest.raises(ConfigError, match="AIEOS_STORAGE_PATH"):
        load_settings(Process.API, env)


def test_secrets_are_masked() -> None:
    env = full_env(Process.API)
    settings = load_settings(Process.API, env)
    secret = settings.secret("AIEOS_CSRF_KEY")
    rendered = [str(secret), repr(secret), f"{secret}", repr(settings), str(settings)]
    for text in rendered:
        assert env["AIEOS_CSRF_KEY"] not in text
    assert str(Secret("abc")) == "***"


def test_no_secret_has_a_default_and_secrets_are_required() -> None:
    for v in VARIABLES:
        if v.kind is Kind.SECRET:
            assert v.required, v.name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("AIEOS_DATABASE_URL", True),
        ("AIEOS_DATABASE_URL_FILE", True),
        ("AIEOS_LLM_API_KEY_LOCAL", True),
        ("AIEOS_STORAGE_PATH", False),
        ("AIEOS_UNKNOWN", False),
    ],
)
def test_is_secret_name(name: str, expected: bool) -> None:
    assert is_secret_name(name) is expected


def test_process_exits_on_missing_secret_without_printing_values() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AIEOS_")}
    provided = full_env(Process.API)
    del provided["AIEOS_TOTP_ENCRYPTION_KEY"]
    env.update(provided)
    code = "from aieos.platform.api import Process, load_settings_or_exit; load_settings_or_exit(Process.API)"
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "AIEOS_TOTP_ENCRYPTION_KEY" in result.stderr
    output = result.stdout + result.stderr
    assert all(value not in output for value in provided.values())


def test_env_example_lists_every_variable_without_values() -> None:
    lines = [line for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    for line in lines:
        assert re.fullmatch(r"AIEOS_[A-Z0-9_]+=", line), f"dòng có giá trị hoặc sai dạng: {line!r}"
    names = {line.removesuffix("=") for line in lines}
    assert names == {v.name for v in VARIABLES}
