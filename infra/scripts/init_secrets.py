#!/usr/bin/env python3
"""Sinh Docker secrets cho stack Compose (T-013) vào `infra/secrets/` (đã `.gitignore`).

Quyền: thư mục 0700 (user khác trên máy không vào được), file 0644 — Compose gắn secret dạng file giữ nguyên quyền của
máy chủ, và tiến trình trong container chạy bằng user khác (api uid 10001, postgres uid 999) cần đọc được.

Mỗi lần chạy chỉ tạo file còn thiếu (không ghi đè secret đang dùng — đổi mật khẩu CSDL sau khi đã khởi tạo cần làm
thủ công). Không in giá trị secret. Mật khẩu role CSDL và URL kết nối được sinh khớp nhau.
"""

import base64
import os
import secrets
import sys
from pathlib import Path

SECRETS = Path(__file__).resolve().parents[1] / "secrets"
DB_HOST = "db:5432"
DB_NAME = "aieos"


def write(name: str, value: str) -> bool:
    path = SECRETS / name
    if path.exists():
        return False
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(value)
    return True


def read(name: str) -> str:
    return (SECRETS / name).read_text(encoding="utf-8")


def main() -> int:
    SECRETS.mkdir(mode=0o700, exist_ok=True)
    SECRETS.chmod(0o700)
    created = [
        name
        for name, value in (
            ("postgres_password", secrets.token_hex(24)),
            ("db_app_password", secrets.token_hex(24)),
            ("db_owner_password", secrets.token_hex(24)),
            ("csrf_key", secrets.token_urlsafe(48)),
            ("totp_encryption_key", base64.b64encode(secrets.token_bytes(32)).decode()),
        )
        if write(name, value)
    ]
    created += [
        name
        for name, value in (
            ("database_url", f"postgresql://aieos_app:{read('db_app_password')}@{DB_HOST}/{DB_NAME}"),
            ("database_owner_url", f"postgresql://aieos_owner:{read('db_owner_password')}@{DB_HOST}/{DB_NAME}"),
        )
        if write(name, value)
    ]
    print(f"infra/secrets: tạo {len(created)} file ({', '.join(created) or 'không có file mới'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
