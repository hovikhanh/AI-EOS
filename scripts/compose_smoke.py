#!/usr/bin/env python3
"""Smoke test tích hợp Docker Compose (T-013, D-43, D-45): dựng stack, kiểm healthcheck, chạy luồng demo đầu-cuối qua
HTTPS và TC-NFR-01. Dùng trong CI (bước `compose-smoke` của `scripts/ci.sh` khi `AIEOS_REQUIRE_DOCKER=1`).

Luồng: secret (`infra/scripts/init_secrets.py`) + `demo.env` → build → `db` → `migrate` (role chủ sở hữu) → `up` → mọi
service `healthy` → `bootstrap-admin` (CLI) → đăng nhập → đăng ký MFA (TOTP tính tại chỗ) → reauth → tạo tài khoản +
lời mời → người được mời kích hoạt → đăng nhập (`/auth/me` 200).

TC-NFR-01 (D-45): trong suốt luồng, một container `busybox` gắn vào network namespace của từng container xử lý dữ liệu
nghiệp vụ (`proxy`, `api`, `worker`, `db`, `scanner`) ghi lại kết nối TCP/UDP mỗi 0,5 giây; mọi địa chỉ đầu xa phải là
địa chỉ riêng (mạng Docker) hoặc loopback. Thêm phép thử chủ động: từ namespace của `api`, `worker`, `db`, `scanner` mở
TCP ra `1.1.1.1:443` phải thất bại; đối chứng: từ `scanner-updater` (ngoại lệ D-45) phải thành công — chứng minh phép
thử phát hiện được đường ra.

Chạy: `python3 scripts/compose_smoke.py [--keep]` (mặc định dọn stack + volume khi xong). Không in secret.
"""

import base64
import hashlib
import hmac
import http.cookiejar
import ipaddress
import json
import os
import shutil
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INFRA = ROOT / "infra"
PROJECT = "aieos-smoke"
BASE = "https://localhost"
ORIGIN = "https://localhost"
BUSYBOX = "busybox:1.37.0"
BUSINESS = ("proxy", "api", "worker", "db", "scanner")
SERVICES = ("proxy", "api", "worker", "db", "scanner", "scanner-updater")
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Demo-Admin-Pass-1!"
USER_EMAIL = "nhanvien@example.com"
USER_PASSWORD = "Demo-User-Pass-2!"


def compose(*args: str, check: bool = True, capture: bool = False, stdin: str | None = None) -> str:
    result = subprocess.run(
        ["docker", "compose", "-p", PROJECT, *args],
        cwd=INFRA,
        check=False,
        text=True,
        input=stdin,
        capture_output=capture,
    )
    if check and result.returncode:
        raise SystemExit(f"docker compose {' '.join(args[:2])} thất bại (rc={result.returncode})")
    return result.stdout if capture else ""


def container(service: str) -> str:
    return compose("ps", "-q", service, capture=True).strip()


def wait_healthy(timeout: float = 900) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        rows = [json.loads(line) for line in compose("ps", "--format", "json", capture=True).splitlines() if line]
        health = {row["Service"]: row.get("Health", "") for row in rows}
        if all(health.get(s) == "healthy" for s in SERVICES):
            print("Mọi service healthy:", ", ".join(SERVICES))
            return
        if any(h == "unhealthy" for h in health.values()):
            raise SystemExit(f"Service unhealthy: {health}")
        time.sleep(10)
    raise SystemExit("Hết thời gian chờ healthy")


# ---------- HTTP qua proxy HTTPS (chứng chỉ CA nội bộ của Caddy) ----------


class Client:
    def __init__(self) -> None:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # CA nội bộ của Caddy (tls internal); chỉ dùng trong smoke test
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.csrf: str | None = None

    def call(self, method: str, path: str, body: Any = None, headers: dict[str, str] | None = None) -> tuple[int, Any]:
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{BASE}/api/v1{path}", data=data, method=method)
        request.add_header("Origin", ORIGIN)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if self.csrf and method != "GET":
            request.add_header("X-CSRF-Token", self.csrf)
        for key, value in (headers or {}).items():
            request.add_header(key, value)
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as error:
            raw = error.read()
            return error.code, json.loads(raw) if raw else None

    def expect(self, status: int, method: str, path: str, body: Any = None, **kw: Any) -> Any:
        code, payload = self.call(method, path, body, **kw)
        if code != status:
            raise SystemExit(f"{method} {path}: mong {status}, nhận {code} {payload and payload.get('code')}")
        return payload


def totp(secret_b32: str, at: float) -> str:
    secret = base64.b32decode(secret_b32 + "=" * (-len(secret_b32) % 8))
    digest = hmac.new(secret, struct.pack(">Q", int(at) // 30), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    return str((struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000).zfill(6)


def fresh_totp(secret: str, used: set[str]) -> str:
    """Mã TOTP chưa dùng (mã đã dùng bị từ chối — RFC 6238 §5.2): chờ sang bước 30 giây mới nếu cần."""
    while (code := totp(secret, time.time())) in used:
        time.sleep(2)
    used.add(code)
    return code


def demo_flow() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        password_file = Path(tmp) / "pw"
        password_file.write_text(ADMIN_PASSWORD, encoding="utf-8")
        password_file.chmod(0o644)
        compose(
            "run", "--rm", "-T", "-v", f"{password_file}:/run/demo/pw:ro", "api",
            "python", "-m", "aieos.app", "bootstrap-admin", "--email", ADMIN_EMAIL,
            "--display-name", "Quản trị demo", "--password-file", "/run/demo/pw",
        )  # fmt: skip
    print("bootstrap-admin: đã tạo ADMIN")

    admin = Client()
    login = admin.expect(200, "POST", "/auth/login", {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login["mfa_required"] and not login["mfa_enrolled"], login
    admin.csrf = login["csrf_token"]
    secret = admin.expect(200, "POST", "/auth/mfa/enroll")["secret"]
    used: set[str] = set()
    codes = admin.expect(200, "POST", "/auth/mfa/enroll/confirm", {"code": fresh_totp(secret, used)})
    assert len(codes["recovery_codes"]) == 10
    admin.csrf = admin.expect(200, "GET", "/auth/me")["csrf_token"]
    print("ADMIN: đăng nhập + đăng ký MFA")

    admin.expect(204, "POST", "/auth/reauth", {"password": ADMIN_PASSWORD, "code": fresh_totp(secret, used)})
    created = admin.expect(
        201,
        "POST",
        "/admin/users",
        {"email": USER_EMAIL, "display_name": "Nhân viên demo", "roles": ["EMPLOYEE"], "reason": "Demo"},
        headers={"Idempotency-Key": uuid.uuid4().hex},
    )
    token = created["invitation"]["link"].split("#token=", 1)[1]
    print("ADMIN: tạo tài khoản + lời mời")

    guest = Client()
    guest.expect(204, "POST", "/auth/invitations/accept", {"token": token, "password": USER_PASSWORD})
    user = Client()
    result = user.expect(200, "POST", "/auth/login", {"email": USER_EMAIL, "password": USER_PASSWORD})
    assert result["mfa_required"] is False, result
    me = user.expect(200, "GET", "/auth/me")
    assert me["roles"] == ["EMPLOYEE"] and "user.manage" not in me["permissions"], me
    user.expect(403, "GET", "/admin/users")
    print("Người dùng mới: kích hoạt + đăng nhập; không vào được trang quản trị")


# ---------- TC-NFR-01 ----------


def is_internal(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip.is_private or ip.is_loopback or ip.is_unspecified or ip.is_link_local


def remote_addresses(netstat: str) -> set[str]:
    found: set[str] = set()
    for line in netstat.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0] in ("tcp", "udp", "tcp6", "udp6"):
            host = parts[4].rsplit(":", 1)[0].strip("[]")
            if host not in ("*", "0.0.0.0", "::"):
                found.add(host.removeprefix("::ffff:"))
    return found


class Monitor(threading.Thread):
    """Ghi địa chỉ đầu xa của kết nối trong network namespace của từng container nghiệp vụ, mỗi 0,5 giây."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.stop = threading.Event()
        self.seen: dict[str, set[str]] = {service: set() for service in BUSINESS}
        self.ids = {service: container(service) for service in BUSINESS}

    def run(self) -> None:
        while not self.stop.is_set():
            for service, cid in self.ids.items():
                output = subprocess.run(
                    ["docker", "run", "--rm", "--network", f"container:{cid}", BUSYBOX, "netstat", "-tun"],
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout
                self.seen[service] |= remote_addresses(output)
            self.stop.wait(0.5)


def can_reach_internet(service: str) -> bool:
    result = subprocess.run(
        ["docker", "run", "--rm", "--network", f"container:{container(service)}", BUSYBOX,
         "nc", "-z", "-w", "5", "1.1.1.1", "443"],
        capture_output=True,
        check=False,
    )  # fmt: skip
    return result.returncode == 0


def main() -> int:
    if shutil.which("docker") is None:
        if os.environ.get("AIEOS_REQUIRE_DOCKER") == "1":
            print("AIEOS_REQUIRE_DOCKER=1 nhưng không có docker", file=sys.stderr)
            return 1
        print("Compose smoke: NOT RUN — chưa xác minh (không có docker)")
        return 0
    keep = "--keep" in sys.argv
    env_file = INFRA / ".env"
    created_env = not env_file.exists()
    if created_env:
        shutil.copy(INFRA / "demo.env", env_file)
    subprocess.run([sys.executable, str(INFRA / "scripts" / "init_secrets.py")], check=True)
    try:
        compose("build", "--quiet")
        compose("up", "-d", "--wait", "db")
        compose("--profile", "ops", "run", "--rm", "-T", "migrate")
        compose("up", "-d")
        wait_healthy()
        monitor = Monitor()
        monitor.start()
        try:
            demo_flow()
        finally:
            monitor.stop.set()
            monitor.join()
        problems = []
        for service, addresses in monitor.seen.items():
            outside = sorted(a for a in addresses if not is_internal(a))
            print(f"TC-NFR-01 {service}: {len(addresses)} địa chỉ đầu xa, ra ngoài: {outside or 'không'}")
            if outside:
                problems.append(f"{service} kết nối ra ngoài: {outside}")
        for service in ("api", "worker", "db", "scanner"):
            if can_reach_internet(service):
                problems.append(f"{service} mở được kết nối ra internet")
        if not can_reach_internet("scanner-updater"):
            problems.append("đối chứng thất bại: scanner-updater không ra được internet — phép thử không đáng tin")
        print("TC-NFR-01 phép thử chủ động: api/worker/db/scanner không ra được internet; scanner-updater ra được")
        for problem in problems:
            print(f"LỖI: {problem}", file=sys.stderr)
        print(f"Compose smoke: {len(problems)} lỗi")
        return 1 if problems else 0
    finally:
        if not keep:
            compose("down", "-v", "--remove-orphans", check=False)
            if created_env:
                env_file.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
