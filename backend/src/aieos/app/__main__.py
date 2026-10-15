"""Lệnh quản trị của AI-EOS (composition root, D-42): `python -m aieos.app <lệnh>`.

- `migrate`: nâng CSDL lên head bằng role `aieos_owner` (Database_Design §10: lệnh riêng, không chạy khi API khởi động).
- `worker [--once]`: tiến trình job queue (ADR-005, T-009); `--once` chạy một vòng (reaper, scheduler, một job).
- `bootstrap-admin`, `recover-admin`: tạo/khôi phục ADMIN (T-106, `admin_cli.py`).
- `health`: kiểm tra CSDL kết nối được và migration ở head (healthcheck của `worker` trong Compose, T-013); không chạy
  job, không ghi gì. Mã thoát 0 đạt, 1 không đạt.
Lỗi chỉ in loại lỗi, không in thông điệp gốc (có thể chứa chuỗi kết nối).
"""

import argparse
import sys

from aieos.app import admin_cli
from aieos.app.metadata import metadata
from aieos.app.worker import run as run_worker
from aieos.platform.api import (
    Process,
    create_app_engine,
    database_ready,
    load_settings_or_exit,
    run_migrations,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aieos.app")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="Nâng CSDL lên revision mới nhất (role aieos_owner)")
    worker = commands.add_parser("worker", help="Chạy worker job queue (role aieos_app)")
    worker.add_argument("--once", action="store_true", help="Chạy một vòng rồi thoát")
    admin_cli.add_commands(commands)
    commands.add_parser("health", help="Kiểm tra CSDL và migration (healthcheck worker)")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        settings = load_settings_or_exit(Process.MIGRATE)
        try:
            revision = run_migrations(settings, metadata())
        except Exception as error:  # chỉ in loại lỗi để không lộ chuỗi kết nối
            print(f"Migration thất bại: {type(error).__name__}", file=sys.stderr)
            return 1
        print(f"Migration xong: revision {revision}")
    elif args.command == "worker":
        return run_worker(once=args.once)
    elif args.command == "health":
        settings = load_settings_or_exit(Process.WORKER)
        engine = create_app_engine(settings)
        try:
            return 0 if database_ready(engine) else 1
        finally:
            engine.dispose()
    else:
        return admin_cli.run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
