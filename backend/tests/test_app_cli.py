"""T-013: `python -m aieos.app health` — healthcheck `worker` trong Compose (CSDL + migration ở head, không ghi)."""

import os
from pathlib import Path

import pytest

from aieos.app.__main__ import main
from tests.conftest import ProvisionedDatabase, migrate_to_head


def worker_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, url: str) -> None:
    for name in list(os.environ):
        if name.startswith("AIEOS_") and name not in ("AIEOS_TEST_DATABASE_URL", "AIEOS_REQUIRE_DB"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("AIEOS_DATABASE_URL", url)
    monkeypatch.setenv("AIEOS_STORAGE_PATH", str(tmp_path))
    monkeypatch.setenv("AIEOS_SCANNER_HOST", "scanner")


@pytest.mark.db
def test_health_reports_migration_state(
    database: ProvisionedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    worker_env(monkeypatch, tmp_path, database.urls["aieos_app"].render_as_string(hide_password=False))
    assert main(["health"]) == 1  # chưa migrate
    migrate_to_head(database)
    assert main(["health"]) == 0


def test_health_fails_when_database_unreachable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    worker_env(monkeypatch, tmp_path, "postgresql://aieos_app:x@127.0.0.1:1/aieos")
    assert main(["health"]) == 1
