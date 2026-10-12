"""Cấu hình chung cho pytest: điều kiện chạy test PostgreSQL (ADR-013, D-41)."""

import os

import pytest

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
