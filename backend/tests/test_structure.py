"""T-001: cấu trúc package backend khớp bảng module của Architecture.md §3."""

import importlib
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO_ROOT / "docs" / "03-architecture" / "Architecture.md"
PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "aieos"


def documented_modules() -> set[str]:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    section = text.split("## 3. Module boundaries", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([a-z_]+)` \|", section, flags=re.MULTILINE))


class StructureTest(unittest.TestCase):
    def test_packages_match_architecture_modules(self) -> None:
        expected = documented_modules()
        self.assertTrue(expected, "không đọc được bảng module trong Architecture.md §3")
        # Mọi mục ở cấp gốc của aieos phải là package module đã khai báo (không file .py lẻ, không namespace package).
        entries = {p for p in PACKAGE_DIR.iterdir() if p.name not in {"__init__.py", "__pycache__"}}
        self.assertEqual({p.name for p in entries}, expected)
        for entry in entries:
            with self.subTest(module=entry.name):
                self.assertTrue((entry / "__init__.py").is_file(), f"{entry.name} thiếu __init__.py")

    def test_every_module_imports(self) -> None:
        package = importlib.import_module("aieos")
        self.assertIsNotNone(package.__file__)
        package_file = str(package.__file__)
        self.assertEqual(Path(package_file).resolve().parent, PACKAGE_DIR, "aieos được import từ nơi khác")
        for name in sorted(documented_modules()):
            with self.subTest(module=name):
                importlib.import_module(f"aieos.{name}")


if __name__ == "__main__":
    unittest.main()
