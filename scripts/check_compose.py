#!/usr/bin/env python3
"""Kiểm tra tĩnh Docker Compose (T-003, D-43, D-45; Architecture §9.1; Implementation_Plan §4 DoD T-003).

Đọc cấu hình đã chuẩn hóa bằng `docker compose config --format json` (không cần `.env`, `secrets/`) rồi kiểm:
- `docker compose config` hợp lệ; chỉ `proxy` có `ports` và chỉ cổng 443; `db` không publish cổng.
- Mạng `backend` là `internal`; service xử lý dữ liệu nghiệp vụ (`proxy`, `api`, `worker`, `migrate`, `db`, `scanner`)
  không ở mạng có đường ra ngoài ngoài `edge` của `proxy` (TC-NFR-01, D-45); `scanner-updater` chỉ ở `egress`, không
  gắn volume dữ liệu (`storage`, `db_data`).
- Không có giá trị secret trong file: biến có tên secret chỉ được đặt dạng `<TÊN>_FILE`; secret Docker đọc từ file.
- Image ghim phiên bản chính xác `x.y.z` (PostgreSQL: `major.minor`), không dùng tag major/`latest` (trừ image backend
  build tại chỗ).
- `Caddyfile` hợp lệ (`caddy validate` trong image `proxy`).

Không có Docker: in NOT RUN và thoát 0, trừ khi `AIEOS_REQUIRE_DOCKER=1` (CI) → thoát 1.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "infra" / "compose.yaml"
CADDYFILE = ROOT / "infra" / "caddy" / "Caddyfile"
BUSINESS = {"proxy", "api", "worker", "migrate", "db", "scanner"}
SECRET_NAME = re.compile(r"(PASSWORD|SECRET|_KEY|TOKEN|DATABASE_URL|DATABASE_OWNER_URL)", re.IGNORECASE)
PINNED = re.compile(r"^[\w./-]+:\d+\.\d+(\.\d+)?$")  # PostgreSQL dùng major.minor (vd. 18.6)
LOCAL_IMAGES = {"aieos-backend:local"}


def violations(config: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    services: dict[str, Any] = config.get("services", {})
    networks: dict[str, Any] = config.get("networks", {})
    if not networks.get("backend", {}).get("internal"):
        problems.append("mạng backend phải internal: true")
    for name, service in services.items():
        ports = service.get("ports") or []
        if name == "proxy":
            published = {str(p.get("published")) for p in ports}
            if published != {"443"}:
                problems.append(f"proxy chỉ được publish cổng 443, đang có {sorted(published)}")
        elif ports:
            problems.append(f"{name} không được publish cổng")
        joined = set(service.get("networks") or {})
        if name in BUSINESS:
            allowed = {"backend", "edge"} if name == "proxy" else {"backend"}
            if not joined <= allowed:
                problems.append(f"{name} chỉ được ở mạng {sorted(allowed)}, đang ở {sorted(joined)}")
        if name == "scanner-updater":
            if joined != {"egress"}:
                problems.append("scanner-updater chỉ được ở mạng egress")
            sources = {v.get("source") for v in service.get("volumes") or []}
            if sources & {"storage", "db_data"}:
                problems.append("scanner-updater không được gắn volume dữ liệu")
        for key, value in (service.get("environment") or {}).items():
            if SECRET_NAME.search(key) and not key.endswith("_FILE") and value not in (None, ""):
                problems.append(f"{name}: biến secret {key} có giá trị trong file — dùng {key}_FILE + Docker secret")
        image = service.get("image", "")
        if image not in LOCAL_IMAGES and not PINNED.match(image):
            problems.append(f"{name}: image {image!r} chưa ghim phiên bản chính xác")
    for name, secret in (config.get("secrets") or {}).items():
        if "file" not in secret:
            problems.append(f"secret {name} phải đọc từ file (không ghi giá trị)")
    return problems


def main() -> int:
    if shutil.which("docker") is None or subprocess.run(["docker", "compose", "version"], capture_output=True).returncode:
        if os.environ.get("AIEOS_REQUIRE_DOCKER") == "1":
            print("AIEOS_REQUIRE_DOCKER=1 nhưng không có docker compose", file=sys.stderr)
            return 1
        print("Compose: NOT RUN — chưa xác minh (không có docker compose)")
        return 0
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "config", "--format", "json"], capture_output=True, text=True
    )
    if result.returncode:
        print(result.stderr.strip(), file=sys.stderr)
        return 1
    problems = violations(json.loads(result.stdout))
    proxy_image = json.loads(result.stdout)["services"]["proxy"]["image"]
    caddy = subprocess.run(
        [
            "docker", "run", "--rm", "--network", "none", "-v", f"{CADDYFILE}:/etc/caddy/Caddyfile:ro", proxy_image,
            "caddy", "validate", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile",
        ],
        capture_output=True,
        text=True,
    )
    if caddy.returncode:
        detail = (caddy.stderr.strip().splitlines() or ["(không có thông báo)"])[-1]
        problems.append(f"Caddyfile không hợp lệ: {detail}")
    for problem in problems:
        print(f"LỖI: {problem}", file=sys.stderr)
    print(f"Compose: {len(problems)} lỗi")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
