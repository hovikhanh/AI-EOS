"""Contract C7 (Architecture §3 quy tắc 10, D-42): chỉ `platform` tạo engine CSDL, cấu hình logging
toàn cục, đọc biến môi trường.

Phân tích AST tĩnh theo tên; không bắt được gọi gián tiếp (`getattr`, `importlib`) — giới hạn ghi ở
Implementation_Plan §11.4.
"""

import ast
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "aieos"
OWNER = "platform"
# Tên thuộc quyền riêng của platform: tạo engine, cấu hình logging toàn cục, đọc/ghi biến môi trường.
RESERVED_NAMES = frozenset(
    {
        "create_engine",
        "create_async_engine",
        "basicConfig",
        "dictConfig",
        "fileConfig",
        "environ",
        "environb",
        "getenv",
        "putenv",
        "unsetenv",
    }
)
RESERVED_MODULES = frozenset({"logging.config"})


def violations(source: str) -> list[str]:
    """Trả về các cách dùng tên/module dành riêng cho platform trong một file mã nguồn."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if alias.name in RESERVED_MODULES)
        elif isinstance(node, ast.ImportFrom):
            if node.module in RESERVED_MODULES:
                found.append(node.module)
            found.extend(alias.name for alias in node.names if alias.name in RESERVED_NAMES)
        elif isinstance(node, ast.Attribute) and node.attr in RESERVED_NAMES:
            found.append(node.attr)
        elif isinstance(node, ast.Name) and node.id in RESERVED_NAMES:
            found.append(node.id)
    return found


def test_only_platform_owns_infrastructure() -> None:
    problems: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        rel = path.relative_to(PACKAGE_DIR)
        if rel.parts[0] == OWNER:
            continue
        problems.extend(f"{rel}: {name}" for name in violations(path.read_text(encoding="utf-8")))
    assert problems == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("from aieos.platform.api import settings", []),
        ("import logging\nlog = logging.getLogger(__name__)", []),
        ("from sqlalchemy import select", []),
        ("import os\npath = os.path.join('a', 'b')", []),
        ("from sqlalchemy import create_engine", ["create_engine"]),
        ("import sqlalchemy\ne = sqlalchemy.create_engine('x')", ["create_engine"]),
        ("from sqlalchemy.ext.asyncio import create_async_engine", ["create_async_engine"]),
        ("import logging\nlogging.basicConfig()", ["basicConfig"]),
        ("import logging.config", ["logging.config"]),
        ("from logging.config import dictConfig", ["logging.config", "dictConfig"]),
        ("import os\nx = os.environ['A']", ["environ"]),
        ("import os\nx = os.getenv('A')", ["getenv"]),
        ("from os import environ", ["environ"]),
    ],
)
def test_c7_checker(source: str, expected: list[str]) -> None:
    assert sorted(violations(source)) == sorted(expected)
