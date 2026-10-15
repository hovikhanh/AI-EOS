"""T-101: bảng `identity.*` (Database_Design §4, ADR-006, INV-16, SRS-IAM-06).

DoD riêng T-101: "Token chỉ lưu hash" — `test_secret_columns_are_sha256_hashes_only`, `test_hash_length_enforced`,
`test_token_helpers`. T-101 không làm chủ TC nào (TEST_Plan §12: TC-IAM-02, TC-IAM-05 chủ T-102 — T-101 là bằng
chứng thành phần: bảng session, token chỉ lưu hash, cột hạn session).
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, LargeBinary, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from aieos.app.metadata import metadata
from aieos.identity.api import TOKEN_BYTES, hash_email, hash_token, new_token, token_matches
from tests.conftest import ProvisionedDatabase, migrate_to_head

IDENTITY_TABLES = ("user_account", "session", "invitation", "mfa_recovery_code", "login_attempt")
SECRET_WORDS = ("token", "code", "secret", "email_hash")


# ---------- Không cần CSDL ----------


def test_token_helpers() -> None:
    tokens = {new_token() for _ in range(100)}
    assert len(tokens) == 100 and all(len(t) == 43 for t in tokens)  # 256 bit base64url
    assert TOKEN_BYTES * 8 >= 256
    token = new_token()
    digest = hash_token(token)
    assert len(digest) == 32 and digest == hash_token(token) and token.encode() not in digest
    assert token_matches(token, digest) and not token_matches(new_token(), digest)
    assert hash_email("  An.Nguyen@Example.COM ") == hash_email("an.nguyen@example.com")
    with pytest.raises(ValueError):
        hash_token("")


def test_secret_columns_are_sha256_hashes_only() -> None:
    """INV-16: mọi cột liên quan token/mã là `*_hash` kiểu bytea; ngoại lệ có chủ đích được liệt kê rõ."""
    allowed_non_hash = {("user_account", "mfa_secret_enc")}  # bí mật TOTP mã hóa bằng khóa ứng dụng (ADR-006)
    found = []
    for table in metadata().tables.values():
        if table.schema != "identity":
            continue
        for column in table.columns:
            if any(word in column.name for word in SECRET_WORDS) or column.name.endswith("_hash"):
                found.append((table.name, column.name))
                if (table.name, column.name) in allowed_non_hash:
                    continue
                if column.name == "password_hash":
                    continue  # chuỗi Argon2id đã mã hóa (ADR-006), không phải token
                if column.name == "request_hash":
                    continue  # dấu vân tay request cho idempotency (INV-08, migration 0009), không phải token
                assert column.name.endswith("_hash"), column.name
                assert isinstance(column.type, LargeBinary), column.name
    assert ("session", "token_hash") in found and ("invitation", "token_hash") in found
    assert ("mfa_recovery_code", "code_hash") in found


# ---------- PostgreSQL thật ----------


@pytest.fixture
def app(database: ProvisionedDatabase) -> Iterator[Engine]:
    migrate_to_head(database)
    engine = database.engine("aieos_app")
    yield engine
    engine.dispose()


def insert_user(
    engine: Engine, email: str, status: str = "ACTIVE", password: str | None = "$argon2id$v=19$x"
) -> uuid.UUID:
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                "VALUES (:i, :e, 'Người dùng', :s, :p)"
            ),
            {"i": user_id, "e": email, "s": status, "p": password},
        )
    return user_id


def violates(engine: Engine, sql: str, params: dict[str, object]) -> bool:
    try:
        with engine.begin() as conn:
            conn.execute(text(sql), params)
    except IntegrityError:
        return True
    return False


@pytest.mark.db
def test_email_unique_case_insensitive(app: Engine) -> None:
    insert_user(app, "An@Example.com")
    with pytest.raises(IntegrityError):
        insert_user(app, "an@example.COM")
    with app.connect() as conn:
        found = conn.execute(text("SELECT count(*) FROM identity.user_account WHERE email = 'AN@EXAMPLE.COM'"))
        assert found.scalar_one() == 1


@pytest.mark.db
def test_user_account_constraints(app: Engine) -> None:
    insert_user(app, "invited@example.com", status="INVITED", password=None)
    with pytest.raises(IntegrityError):
        insert_user(app, "x1@example.com", status="INVITED", password="$argon2id$v=19$x")  # INVITED có mật khẩu
    with pytest.raises(IntegrityError):
        insert_user(app, "x2@example.com", status="ACTIVE", password=None)  # ACTIVE không mật khẩu
    with pytest.raises(IntegrityError):
        insert_user(app, "x3@example.com", status="SUSPENDED")
    user = insert_user(app, "mfa@example.com")
    assert violates(app, "UPDATE identity.user_account SET mfa_enabled = true WHERE id = :i", {"i": user})
    assert violates(app, "UPDATE identity.user_account SET failed_login_count = -1 WHERE id = :i", {"i": user})
    with app.connect() as conn:
        row = conn.execute(
            text(
                "SELECT mfa_enabled, must_enroll_mfa, failed_login_count, version "
                "FROM identity.user_account WHERE id = :i"
            ),
            {"i": user},
        ).one()
    assert tuple(row) == (False, False, 0, 1)


@pytest.mark.db
def test_hash_length_enforced(app: Engine) -> None:
    """INV-16: cột hash nhận đúng 32 byte; chuỗi token rõ (43 ký tự) không vừa."""
    user = insert_user(app, "s@example.com")
    now = datetime.now(UTC)
    session_sql = (
        "INSERT INTO identity.session (id, token_hash, user_id, idle_expires_at, absolute_expires_at) "
        "VALUES (:i, :h, :u, :idle, :abs)"
    )
    base = {"u": user, "idle": now + timedelta(minutes=30), "abs": now + timedelta(hours=8)}
    assert violates(app, session_sql, {**base, "i": uuid.uuid4(), "h": new_token().encode()})
    assert violates(app, session_sql, {**base, "i": uuid.uuid4(), "h": b"\x00" * 16})
    assert not violates(app, session_sql, {**base, "i": uuid.uuid4(), "h": hash_token(new_token())})
    assert violates(
        app,
        "INSERT INTO identity.mfa_recovery_code (id, user_id, code_hash) VALUES (:i, :u, :h)",
        {"i": uuid.uuid4(), "u": user, "h": b"ABCD-EFGH"},
    )
    assert violates(
        app,
        "INSERT INTO identity.login_attempt (email_hash, success) VALUES (:h, false)",
        {"h": b"an@example.com"},
    )


@pytest.mark.db
def test_session_constraints_and_active_index(app: Engine, database: ProvisionedDatabase) -> None:
    user = insert_user(app, "sess@example.com")
    now = datetime.now(UTC)
    sql = (
        "INSERT INTO identity.session (id, token_hash, user_id, idle_expires_at, absolute_expires_at, created_at) "
        "VALUES (:i, :h, :u, :idle, :abs, :c)"
    )
    params = {"u": user, "idle": now, "c": now}
    digest = hash_token(new_token())
    assert not violates(app, sql, {**params, "i": uuid.uuid4(), "h": digest, "abs": now + timedelta(hours=1)})
    assert violates(app, sql, {**params, "i": uuid.uuid4(), "h": digest, "abs": now + timedelta(hours=1)})  # trùng hash
    assert violates(
        app, sql, {**params, "i": uuid.uuid4(), "h": hash_token(new_token()), "abs": now - timedelta(seconds=1)}
    )
    assert violates(
        app,
        sql,
        {**params, "i": uuid.uuid4(), "h": hash_token(new_token()), "u": uuid.uuid4(), "abs": now + timedelta(hours=1)},
    )  # FK user
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        definition = conn.execute(
            text(
                "SELECT indexdef FROM pg_indexes WHERE schemaname = 'identity' AND indexname = 'ix_session_active_user'"
            )
        ).scalar_one()
    owner.dispose()
    assert "WHERE (revoked_at IS NULL)" in definition


@pytest.mark.db
def test_invitation_one_active_per_user(app: Engine) -> None:
    admin = insert_user(app, "admin@example.com")
    invited = insert_user(app, "new@example.com", status="INVITED", password=None)
    sql = (
        "INSERT INTO identity.invitation (id, user_id, token_hash, expires_at, created_by) "
        "VALUES (:i, :u, :h, now() + interval '1 day', :c)"
    )
    first = uuid.uuid4()
    assert not violates(app, sql, {"i": first, "u": invited, "h": hash_token(new_token()), "c": admin})
    assert violates(app, sql, {"i": uuid.uuid4(), "u": invited, "h": hash_token(new_token()), "c": admin})
    assert violates(
        app, "UPDATE identity.invitation SET used_at = now(), revoked_at = now() WHERE id = :i", {"i": first}
    )
    assert not violates(app, "UPDATE identity.invitation SET revoked_at = now() WHERE id = :i", {"i": first})
    assert not violates(app, sql, {"i": uuid.uuid4(), "u": invited, "h": hash_token(new_token()), "c": admin})


@pytest.mark.db
def test_app_privileges_no_delete(database: ProvisionedDatabase, app: Engine) -> None:
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        granted = {
            (table, privilege)
            for table in IDENTITY_TABLES
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
            if conn.execute(
                text("SELECT has_table_privilege('aieos_app', :t, :p)"), {"t": f"identity.{table}", "p": privilege}
            ).scalar_one()
        }
        extension = conn.execute(
            text("SELECT extnamespace::regnamespace::text FROM pg_extension WHERE extname = 'citext'")
        )
        assert extension.scalar_one() == "public"
    owner.dispose()
    assert granted == {(t, p) for t in IDENTITY_TABLES for p in ("SELECT", "INSERT", "UPDATE")}
    with pytest.raises(DBAPIError):  # id identity ALWAYS: không tự đặt được
        with app.begin() as conn:
            conn.execute(
                text("INSERT INTO identity.login_attempt (id, email_hash, success) VALUES (1, :h, true)"),
                {"h": hash_email("a")},
            )
