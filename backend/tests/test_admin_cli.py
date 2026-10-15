"""T-106: CLI `bootstrap-admin`, `recover-admin` (SRS-IAM-09, SRS-IAM-10; ADR-006 A2, A6).

TC do T-106 làm chủ: TC-IAM-11 (`test_bootstrap_refused_when_active_admin` — lần 1;
`test_bootstrap_creates_first_admin` — lần 2, trên CSDL chưa có ADMIN vì trigger INV-11 không cho gỡ ADMIN cuối),
TC-IAM-12 (`test_recover_requires_confirm_then_resets_and_notifies`).
"""

import importlib.util
import os
import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

import aieos.identity.admin as admin_module
from aieos.access.api import grant_role
from aieos.app.__main__ import main
from aieos.app.admin_cli import read_password
from aieos.identity.admin import ADMIN_LOCK_KEY
from aieos.identity.api import AdminCommandError, bootstrap_admin, hash_password, hash_token, verify_password
from aieos.platform.api import create_db_engine, make_session_factory, transaction
from tests.conftest import ProvisionedDatabase, migrate_to_head

REPO = Path(__file__).resolve().parents[2]
MIGRATION = REPO / "backend" / "src" / "aieos" / "platform" / "migrations" / "versions" / "0005_access_seed.py"
OLD_PASSWORD = "Mat-khau-cu-123!"
NEW_PASSWORD = "Mat-khau-moi-456!"
MIN_LENGTH = 12


@dataclass
class Env:
    engine: Engine
    password_file: Path

    def scalar(self, sql: str, params: dict[str, object] | None = None) -> Any:
        with self.engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one()

    def user(self, email: str, roles: tuple[str, ...], *, mfa: bool = False) -> uuid.UUID:
        user_id = uuid.uuid4()
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash, "
                    "mfa_enabled, mfa_secret_enc, locked_until, failed_login_count) "
                    "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p, :m, :s, now() + interval '1 hour', 3)"
                ),
                {"i": user_id, "e": email, "p": hash_password(OLD_PASSWORD), "m": mfa, "s": b"secret" if mfa else None},
            )
        with transaction(make_session_factory(self.engine)) as session:
            for role in roles:
                grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
        return user_id

    def session(self, user_id: uuid.UUID) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO identity.session (id, token_hash, user_id, idle_expires_at, absolute_expires_at) "
                    "VALUES (gen_random_uuid(), :h, :u, now() + interval '1 hour', now() + interval '8 hours')"
                ),
                {"h": hash_token(uuid.uuid4().hex), "u": user_id},
            )


@pytest.fixture
def env(database: ProvisionedDatabase, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Env]:
    migrate_to_head(database)
    for name in list(os.environ):
        if name.startswith("AIEOS_") and name not in ("AIEOS_TEST_DATABASE_URL", "AIEOS_REQUIRE_DB"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("AIEOS_DATABASE_URL", database.urls["aieos_app"].render_as_string(hide_password=False))
    monkeypatch.setenv("AIEOS_PASSWORD_MIN_LENGTH", str(MIN_LENGTH))
    password_file = tmp_path / "password"
    password_file.write_text(NEW_PASSWORD + "\n", encoding="utf-8")
    engine = create_db_engine(database.secret("aieos_app"), pool_size=5)
    yield Env(engine, password_file)
    engine.dispose()


def bootstrap(env: Env, email: str = "admin@example.com", *extra: str) -> int:
    return main(
        ["bootstrap-admin", "--email", email, "--display-name", "Quản trị", "--password-file", str(env.password_file)]
        + list(extra)
    )


def recover(env: Env, *flags: str, email: str = "admin@example.com") -> int:
    args = ["recover-admin", "--email", email, "--reason", "Mất thiết bị MFA"]
    return main([*args, "--password-file", str(env.password_file), *flags])


# ---------- TC-IAM-11 ----------


@pytest.mark.db
def test_bootstrap_refused_when_active_admin(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    """TC-IAM-11 (lần 1): đã có ADMIN hoạt động → lệnh thoát lỗi, không tạo tài khoản, không audit bootstrap."""
    env.user("old-admin@example.com", ("ADMIN",))
    assert bootstrap(env) == 1
    assert env.scalar("SELECT count(*) FROM identity.user_account") == 1
    assert env.scalar("SELECT count(*) FROM audit.event WHERE action = 'identity.admin.bootstrap'") == 0
    assert "Đã có ADMIN đang hoạt động" in capsys.readouterr().err


@pytest.mark.db
def test_bootstrap_creates_first_admin(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    """TC-IAM-11 (lần 2): chưa có ADMIN → tài khoản `ACTIVE`, `must_enroll_mfa`, role ADMIN không người cấp, audit."""
    assert bootstrap(env, "Admin@Example.com") == 0
    out = capsys.readouterr()
    user_id = uuid.UUID(env.scalar("SELECT id::text FROM identity.user_account"))
    assert str(user_id) in out.out
    assert "example.com" not in out.out + out.err and NEW_PASSWORD not in out.out + out.err
    with env.engine.connect() as conn:
        user = conn.execute(
            text("SELECT status, must_enroll_mfa, mfa_enabled, created_by, password_hash FROM identity.user_account")
        ).one()
        role = conn.execute(text("SELECT role_code, granted_by FROM access.user_role")).one()
        audit = conn.execute(
            text(
                "SELECT actor_type, actor_user_id, resource_id FROM audit.event "
                "WHERE action = 'identity.admin.bootstrap'"
            )
        ).one()
    assert (user.status, user.must_enroll_mfa, user.mfa_enabled, user.created_by) == ("ACTIVE", True, False, None)
    assert verify_password(user.password_hash, NEW_PASSWORD)
    assert tuple(role) == ("ADMIN", None)
    assert tuple(audit) == ("BOOTSTRAP", None, str(user_id))
    assert bootstrap(env, "second@example.com") == 1  # đã có ADMIN → lần sau từ chối
    assert env.scalar("SELECT count(*) FROM identity.user_account") == 1


@pytest.mark.db
def test_bootstrap_validation_refuses_without_side_effects(env: Env, tmp_path: Path) -> None:
    short = tmp_path / "short"
    short.write_text("ngan", encoding="utf-8")
    base = ["bootstrap-admin", "--email", "a@example.com", "--display-name", "A", "--password-file"]
    assert main([*base, str(short)]) == 1
    assert main([*base, str(tmp_path / "khong-co")]) == 1
    assert main(["bootstrap-admin", "--email", "khong-email", "--display-name", "A"]) == 1
    env.user("taken@example.com", ("EMPLOYEE",))
    assert bootstrap(env, "taken@example.com") == 1  # email có sẵn: không biến tài khoản cũ thành ADMIN
    assert env.scalar("SELECT count(*) FROM access.user_role WHERE role_code = 'ADMIN'") == 0
    assert env.scalar("SELECT count(*) FROM audit.event WHERE action = 'identity.admin.bootstrap'") == 0


@pytest.mark.db
def test_concurrent_bootstrap_creates_one_admin(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    """Advisory lock `admin-membership`: hai lệnh đồng thời → đúng một ADMIN.

    Barrier giữ mỗi lệnh ngay sau bước kiểm tra "đã có ADMIN chưa": không có khóa thì cả hai cùng thấy "chưa có" và cùng
    tạo; có khóa thì lệnh thứ hai chờ khóa (barrier hết hạn) và thấy ADMIN do lệnh đầu tạo.
    """
    barrier = threading.Barrier(2)
    original = admin_module.active_admins  # type: ignore[attr-defined]

    def checked_then_wait(session: Any) -> list[uuid.UUID]:
        result = original(session)
        try:
            barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return result

    monkeypatch.setattr(admin_module, "active_admins", checked_then_wait)
    factory = make_session_factory(env.engine)
    results: list[str] = []

    def attempt(n: int) -> None:
        try:
            bootstrap_admin(
                factory, email=f"a{n}@example.com", display_name="A", password=NEW_PASSWORD, min_length=MIN_LENGTH
            )
            results.append("ok")
        except AdminCommandError:
            results.append("refused")

    threads = [threading.Thread(target=attempt, args=(n,)) for n in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == ["ok", "refused"]
    assert env.scalar("SELECT count(*) FROM access.user_role WHERE role_code = 'ADMIN'") == 1


def test_lock_key_matches_last_admin_trigger() -> None:
    spec = importlib.util.spec_from_file_location("m0005", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.ADMIN_LOCK_KEY == ADMIN_LOCK_KEY


# ---------- TC-IAM-12 ----------


@pytest.mark.db
def test_recover_requires_confirm_then_resets_and_notifies(env: Env, capsys: pytest.CaptureFixture[str]) -> None:
    """TC-IAM-12: thiếu `--confirm` → từ chối, không đổi gì; có cờ → session thu hồi, MFA/mật khẩu đặt lại, audit,
    ADMIN khác được thông báo."""
    target = env.user("admin@example.com", ("ADMIN",), mfa=True)
    other = env.user("admin2@example.com", ("ADMIN",))
    employee = env.user("nv@example.com", ("EMPLOYEE",))
    env.session(target)
    env.session(target)
    env.session(other)
    with env.engine.begin() as conn:
        conn.execute(
            text("INSERT INTO identity.mfa_recovery_code (id, user_id, code_hash) VALUES (gen_random_uuid(), :u, :h)"),
            {"u": target, "h": hash_token("ma-khoi-phuc")},
        )

    assert recover(env) == 1
    assert "--confirm" in capsys.readouterr().err
    assert env.scalar("SELECT count(*) FROM identity.session WHERE revoked_at IS NULL") == 3
    assert env.scalar("SELECT mfa_enabled FROM identity.user_account WHERE id = :u", {"u": target}) is True
    assert env.scalar("SELECT count(*) FROM notify.notification") == 0

    assert recover(env, "--confirm") == 0
    out = capsys.readouterr()
    assert "example.com" not in out.out + out.err and NEW_PASSWORD not in out.out + out.err
    with env.engine.connect() as conn:
        user = conn.execute(text("SELECT * FROM identity.user_account WHERE id = :u"), {"u": target}).one()
        live = conn.execute(text("SELECT user_id FROM identity.session WHERE revoked_at IS NULL")).scalars().all()
        unused_codes = conn.execute(
            text("SELECT count(*) FROM identity.mfa_recovery_code WHERE used_at IS NULL")
        ).scalar_one()
        audit = conn.execute(
            text("SELECT actor_type, reason, resource_id FROM audit.event WHERE action = 'identity.admin.recover'")
        ).one()
        notified = conn.execute(text("SELECT user_id, type, link FROM notify.notification")).all()
    assert verify_password(user.password_hash, NEW_PASSWORD) and not verify_password(user.password_hash, OLD_PASSWORD)
    assert (user.mfa_enabled, user.mfa_secret_enc, user.must_enroll_mfa) == (False, None, True)
    assert (user.locked_until, user.failed_login_count, user.version) == (None, 0, 2)
    assert live == [other] and unused_codes == 0
    assert tuple(audit) == ("BOOTSTRAP", "Mất thiết bị MFA", str(target))
    assert [tuple(n) for n in notified] == [(other, "ADMIN_RECOVERED", None)]
    assert employee not in [n.user_id for n in notified]


@pytest.mark.db
def test_recover_refuses_non_admin_and_unknown(env: Env) -> None:
    env.user("nv@example.com", ("EMPLOYEE",))
    env.session(env.user("admin@example.com", ("ADMIN",)))
    assert recover(env, "--confirm", email="nv@example.com") == 1
    assert recover(env, "--confirm", email="khong-co@example.com") == 1
    assert env.scalar("SELECT count(*) FROM identity.session WHERE revoked_at IS NULL") == 1
    assert env.scalar("SELECT count(*) FROM audit.event WHERE action = 'identity.admin.recover'") == 0


@pytest.mark.db
def test_missing_or_invalid_min_length_exits_2(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    """D-58: `AIEOS_PASSWORD_MIN_LENGTH` bắt buộc, không mặc định."""
    monkeypatch.setenv("AIEOS_PASSWORD_MIN_LENGTH", "0")
    assert bootstrap(env) == 2
    monkeypatch.delenv("AIEOS_PASSWORD_MIN_LENGTH")
    with pytest.raises(SystemExit) as info:
        bootstrap(env)
    assert info.value.code == 2
    assert env.scalar("SELECT count(*) FROM identity.user_account") == 0


def test_read_password_sources(tmp_path: Path) -> None:
    file = tmp_path / "p"
    file.write_text("mat khau\r\n", encoding="utf-8")
    assert read_password(file, lambda _: "x", interactive=False) == "mat khau"
    answers = iter(["mot", "mot"])
    assert read_password(None, lambda _: next(answers), interactive=True) == "mot"
    answers = iter(["mot", "hai"])
    with pytest.raises(AdminCommandError):
        read_password(None, lambda _: next(answers), interactive=True)
    with pytest.raises(AdminCommandError):
        read_password(None, lambda _: "x", interactive=False)


def test_password_never_accepted_as_argument() -> None:
    with pytest.raises(SystemExit):
        main(["bootstrap-admin", "--email", "a@example.com", "--display-name", "A", "--password", "x"])
