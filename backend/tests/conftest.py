"""Cấu hình chung cho pytest: điều kiện chạy test PostgreSQL (ADR-013, D-41) và CSDL tạm cho test `db` (T-005).

CSDL tạm: mỗi test tạo một CSDL riêng trên cụm `AIEOS_TEST_DATABASE_URL` (superuser của cụm test riêng), chạy
`provision_roles.sql`, đặt mật khẩu ngẫu nhiên cho 3 role (cấp cụm; không in ra) và xóa CSDL khi kết thúc.
"""

import os
import secrets
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
import sqlalchemy
from sqlalchemy import Engine
from sqlalchemy.engine import URL, make_url

from aieos.platform.api import ROLES, Secret, provision_roles_sql, upgrade

NOT_RUN = "PostgreSQL: NOT RUN — chưa xác minh (thiếu AIEOS_TEST_DATABASE_URL)"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("AIEOS_TEST_DATABASE_URL"):
        return
    if os.environ.get("AIEOS_REQUIRE_DB") == "1":
        # CI bắt buộc có CSDL: thiếu URL là lỗi, không được skip.
        pytest.exit("AIEOS_REQUIRE_DB=1 nhưng thiếu AIEOS_TEST_DATABASE_URL", returncode=1)
    skip = pytest.mark.skip(reason=NOT_RUN)
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@dataclass(frozen=True)
class ProvisionedDatabase:
    admin: URL
    urls: dict[str, URL]

    def engine(self, role: str) -> Engine:
        return sqlalchemy.create_engine(self.urls[role])

    def secret(self, role: str) -> Secret:
        return Secret(self.urls[role].render_as_string(hide_password=False))


@pytest.fixture
def database() -> Iterator[ProvisionedDatabase]:
    base = make_url(os.environ["AIEOS_TEST_DATABASE_URL"]).set(drivername="postgresql+psycopg")
    name = f"aieos_test_{secrets.token_hex(4)}"
    passwords = {role: secrets.token_urlsafe(24) for role in ROLES}
    server = sqlalchemy.create_engine(base, isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    admin = base.set(database=name)
    target = sqlalchemy.create_engine(admin, isolation_level="AUTOCOMMIT")
    try:
        with target.connect() as conn:
            # Gửi nguyên văn qua psycopg (không tham số) như psql: `%I` của format() không phải placeholder.
            driver = conn.connection.driver_connection
            assert driver is not None
            driver.execute(provision_roles_sql())
            for role, password in passwords.items():
                conn.exec_driver_sql(f"ALTER ROLE {role} PASSWORD '{password}'")
        target.dispose()
        urls = {role: admin.set(username=role, password=passwords[role]) for role in ROLES}
        yield ProvisionedDatabase(admin, urls)
    finally:
        target.dispose()
        with server.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        server.dispose()


def migrate_to_head(db: ProvisionedDatabase) -> None:
    owner = db.engine("aieos_owner")
    with owner.begin() as conn:
        upgrade(conn, "head")
    owner.dispose()
