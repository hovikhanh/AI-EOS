"""Smoke test PostgreSQL thật (ADR-013, Q-47). Schema và migration thuộc T-005."""

import os

import psycopg
import pytest

EXPECTED_MAJOR = 18


@pytest.mark.db
def test_postgresql_connection_and_major_version() -> None:
    url = os.environ["AIEOS_TEST_DATABASE_URL"]
    with psycopg.connect(url, connect_timeout=10) as conn:
        row = conn.execute(
            "SELECT 1, current_setting('server_version_num')::int, current_setting('server_version')"
        ).fetchone()
    assert row is not None
    one, version_num, version = row
    print(f"PostgreSQL server_version: {version}")
    assert one == 1
    assert version_num // 10000 == EXPECTED_MAJOR, version
