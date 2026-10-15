"""Lệnh `bootstrap-admin`, `recover-admin` (T-106; ADR-006 A2, A6). Chạy trong container có quyền truy cập máy chủ.

Cấu hình: tiến trình `admin-cli` — `AIEOS_DATABASE_URL` (role `aieos_app`), `AIEOS_PASSWORD_MIN_LENGTH` (D-58).
Mật khẩu: `--password-file` (file secret, bỏ một ký tự xuống dòng cuối) hoặc nhập tương tác hai lần khi có terminal;
không nhận mật khẩu qua tham số dòng lệnh (lộ trong lịch sử shell, danh sách tiến trình). `recover-admin` bắt buộc
`--confirm` và `--reason`. Mã thoát: 0 thành công, 1 bị từ chối/lỗi, 2 cấu hình sai. Không in email, mật khẩu.
"""

import argparse
import getpass
import sys
from collections.abc import Callable
from pathlib import Path

from aieos.app.asgi import AppConfigError, positive_int
from aieos.identity.api import AdminCommandError, bootstrap_admin, recover_admin
from aieos.platform.api import Process, create_app_engine, load_settings_or_exit, make_session_factory

PasswordPrompt = Callable[[str], str]


def add_commands(commands: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
    bootstrap = commands.add_parser("bootstrap-admin", help="Tạo ADMIN đầu tiên (từ chối nếu đã có ADMIN hoạt động)")
    bootstrap.add_argument("--email", required=True)
    bootstrap.add_argument("--display-name", required=True)
    bootstrap.add_argument("--password-file", type=Path, help="File chứa mật khẩu (Docker secret)")
    recover = commands.add_parser("recover-admin", help="Khôi phục ADMIN: mật khẩu mới, đăng ký lại MFA")
    recover.add_argument("--email", required=True)
    recover.add_argument("--reason", required=True, help="Lý do (ghi vào audit)")
    recover.add_argument("--password-file", type=Path, help="File chứa mật khẩu mới (Docker secret)")
    recover.add_argument("--confirm", action="store_true", help="Xác nhận tường minh (bắt buộc)")


def read_password(path: Path | None, prompt: PasswordPrompt, interactive: bool) -> str:
    if path is not None:
        try:
            value = path.read_text(encoding="utf-8")
        except OSError:
            raise AdminCommandError("Không đọc được file mật khẩu") from None
        return value.removesuffix("\n").removesuffix("\r")
    if not interactive:
        raise AdminCommandError("Cần --password-file hoặc chạy trong terminal để nhập mật khẩu")
    first = prompt("Mật khẩu: ")
    if prompt("Nhập lại mật khẩu: ") != first:
        raise AdminCommandError("Hai lần nhập mật khẩu không khớp")
    return first


def run(args: argparse.Namespace, prompt: PasswordPrompt = getpass.getpass, interactive: bool | None = None) -> int:
    if args.command == "recover-admin" and not args.confirm:
        print("recover-admin cần cờ --confirm; không thay đổi gì", file=sys.stderr)
        return 1
    settings = load_settings_or_exit(Process.ADMIN_CLI)
    try:
        min_length = positive_int(settings, "AIEOS_PASSWORD_MIN_LENGTH")
    except AppConfigError as error:
        print(f"Cấu hình không hợp lệ cho lệnh {args.command}: {error}", file=sys.stderr)
        return 2
    engine = create_app_engine(settings)
    try:
        password = read_password(args.password_file, prompt, sys.stdin.isatty() if interactive is None else interactive)
        factory = make_session_factory(engine)
        if args.command == "bootstrap-admin":
            user_id = bootstrap_admin(
                factory, email=args.email, display_name=args.display_name, password=password, min_length=min_length
            )
            print(f"Đã tạo ADMIN {user_id}; đăng nhập rồi đăng ký MFA trước khi dùng")
        else:
            user_id = recover_admin(
                factory, email=args.email, password=password, reason=args.reason, min_length=min_length
            )
            print(f"Đã khôi phục ADMIN {user_id}; session cũ đã thu hồi, cần đăng ký lại MFA")
    except AdminCommandError as error:
        print(f"{args.command} bị từ chối: {error}", file=sys.stderr)
        return 1
    except Exception as error:  # chỉ in loại lỗi để không lộ chuỗi kết nối
        print(f"{args.command} thất bại: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    return 0
