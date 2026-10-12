"""Contract C4 (Architecture §3 quy tắc 1): module chỉ import `<module>.api` của module khác.

Phân tích AST tĩnh; không bắt được import động (`importlib`) — giới hạn đã ghi ở Implementation_Plan §11.4.
"""

import ast
from pathlib import Path

import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "aieos"
ROOT = "aieos"


def _absolute(module: str | None, level: int, current: str, is_package: bool) -> str:
    if level == 0:
        return module or ""
    parts = current.split(".")
    base = parts if is_package else parts[:-1]
    base = base[: len(base) - (level - 1)]
    return ".".join([*base, module] if module else base)


def _allowed(target: str, own: str) -> bool:
    parts = target.split(".")
    if parts[0] != ROOT or len(parts) < 2 or parts[1] == own:
        return True
    return len(parts) >= 3 and parts[2] == "api"


def violations(source: str, current: str, is_package: bool = False) -> list[str]:
    """Trả về các import vi phạm C4 trong mã nguồn của module `current` (vd. `aieos.goals.service`)."""
    own = current.split(".")[1] if current.count(".") >= 1 else ""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            targets = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = _absolute(node.module, node.level, current, is_package)
            # `from aieos import x` / `from aieos.x import y` có thể nhập submodule → xét `base.<tên>`.
            targets = [f"{base}.{alias.name}" if base.count(".") <= 1 else base for alias in node.names]
        else:
            continue
        found.extend(t for t in targets if not _allowed(t, own))
    return found


def _module_name(path: Path) -> tuple[str, bool]:
    rel = path.relative_to(PACKAGE_DIR.parent).with_suffix("")
    parts = list(rel.parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


def test_source_tree_respects_c4() -> None:
    problems: list[str] = []
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        name, is_package = _module_name(path)
        for target in violations(path.read_text(encoding="utf-8"), name, is_package):
            problems.append(f"{name} import {target}")
    assert problems == []


@pytest.mark.parametrize(
    ("source", "current", "expected"),
    [
        ("from aieos.finance import api", "aieos.goals.service", []),
        ("from aieos.finance.api import read_x", "aieos.goals.service", []),
        ("import aieos.finance.api", "aieos.goals.service", []),
        ("from aieos.goals import models", "aieos.goals.service", []),
        ("import os", "aieos.goals.service", []),
        ("from aieos.finance import models", "aieos.goals.service", ["aieos.finance.models"]),
        ("from aieos.finance.models import Tx", "aieos.goals.service", ["aieos.finance.models"]),
        ("import aieos.finance", "aieos.goals.service", ["aieos.finance"]),
        ("from ..finance import repository", "aieos.goals.service", ["aieos.finance.repository"]),
        ("from .. import finance", "aieos.goals.service", ["aieos.finance"]),
    ],
)
def test_c4_checker(source: str, current: str, expected: list[str]) -> None:
    assert violations(source, current) == expected
