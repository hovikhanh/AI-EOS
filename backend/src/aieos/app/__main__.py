"""Lệnh quản trị của AI-EOS (composition root, D-42): `python -m aieos.app <lệnh>`.

- `migrate`: nâng CSDL lên head bằng role `aieos_owner` (Database_Design §10: lệnh riêng, không chạy khi API khởi động).
Lỗi chỉ in loại lỗi, không in thông điệp gốc (có thể chứa chuỗi kết nối).
"""

import argparse
import sys

from aieos.app.metadata import metadata
from aieos.platform.api import Process, load_settings_or_exit, run_migrations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aieos.app")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="Nâng CSDL lên revision mới nhất (role aieos_owner)")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        settings = load_settings_or_exit(Process.MIGRATE)
        try:
            revision = run_migrations(settings, metadata())
        except Exception as error:  # chỉ in loại lỗi để không lộ chuỗi kết nối
            print(f"Migration thất bại: {type(error).__name__}", file=sys.stderr)
            return 1
        print(f"Migration xong: revision {revision}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
