"""T-005: nền CSDL — engine/session, migration Alembic, role CSDL (Database_Design §2, §10; ADR-004, ADR-013).

Test `db` chạy trên PostgreSQL thật (`AIEOS_TEST_DATABASE_URL`, superuser của cụm test riêng). Mỗi test tạo một CSDL
tạm; role là đối tượng cấp cụm nên được tạo/đặt mật khẩu ngẫu nhiên mỗi lần chạy (không dùng cụm có dữ liệu thật).
"""

import ast
import os
import re
import secrets
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy import Engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import DBAPIError

from aieos.platform.api import (
    ROLES,
    SCHEMAS,
    Base,
    DatabaseConfigError,
    Secret,
    compare_schema,
    create_db_engine,
    current_revision,
    downgrade,
    head_revision,
    make_session_factory,
    provision_roles_sql,
    script_directory,
    to_url,
    transaction,
    upgrade,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "backend" / "src" / "aieos" / "platform" / "migrations" / "versions"
DATABASE_DESIGN = REPO_ROOT / "docs" / "03-architecture" / "Database_Design.md"
PASSWORD = "mat-khau-khong-duoc-lo"


# ---------- Không cần CSDL ----------


@pytest.mark.parametrize("scheme", ["postgresql", "postgres", "postgresql+psycopg"])
def test_url_uses_psycopg_driver(scheme: str) -> None:
    url = to_url(Secret(f"{scheme}://u:{PASSWORD}@h:5432/db"))
    assert url.drivername == "postgresql+psycopg"
    assert url.password == PASSWORD


def test_engine_never_renders_password() -> None:
    engine = create_db_engine(Secret(f"postgresql://u:{PASSWORD}@h:5432/db"))
    try:
        assert PASSWORD not in str(engine.url)
        assert PASSWORD not in repr(engine)
    finally:
        engine.dispose()


@pytest.mark.parametrize("raw", [f"mysql://u:{PASSWORD}@h/db", f"khong-phai-url-{PASSWORD}"])
def test_invalid_url_error_has_no_value(raw: str) -> None:
    with pytest.raises(DatabaseConfigError) as info:
        to_url(Secret(raw))
    assert PASSWORD not in str(info.value)
    # Không giữ ngoại lệ gốc (có thể chứa URL): không có cause, context nếu có thì bị chặn.
    assert info.value.__cause__ is None
    assert info.value.__context__ is None or info.value.__suppress_context__


def test_single_linear_revision_chain() -> None:
    script = script_directory()
    assert script.get_heads() == [head_revision()]
    revisions = list(script.walk_revisions())
    assert all(not isinstance(rev.down_revision, tuple) for rev in revisions)
    assert [rev.down_revision for rev in revisions][-1] is None


def test_every_revision_documents_requirement_or_adr() -> None:
    for path in sorted(VERSIONS_DIR.glob("[0-9]*.py")):
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        assert re.search(r"\b(SRS|ADR|T|D|INV)-\d+", doc), path.name


def test_schema_lists_agree_with_database_design() -> None:
    section = DATABASE_DESIGN.read_text(encoding="utf-8").split("## 2. Schema và role CSDL", 1)[1].split("\n## ", 1)[0]
    documented_schemas = re.findall(r"^\| `([a-z_]+)` \| [a-z]", section, flags=re.MULTILINE)
    documented_roles = re.findall(r"^\| `(aieos_[a-z]+)` \|", section, flags=re.MULTILINE)
    migration = ast.parse((VERSIONS_DIR / "0001_base_roles_schemas.py").read_text(encoding="utf-8"))
    migration_schemas = next(
        ast.literal_eval(node.value)
        for node in migration.body
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", None) == "SCHEMAS"
    )
    assert set(documented_schemas) == set(SCHEMAS) == set(migration_schemas)
    assert set(documented_roles) == set(ROLES)


def test_provision_sql_has_no_password() -> None:
    sql = provision_roles_sql()
    statements = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    assert not re.search(r"\bPASSWORD\b", statements, flags=re.IGNORECASE)
    for role in ROLES:
        assert role in sql


def test_migrate_command_requires_owner_url() -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AIEOS_")}
    result = subprocess.run(
        [sys.executable, "-m", "aieos.app", "migrate"], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert "AIEOS_DATABASE_OWNER_URL" in result.stderr


# ---------- PostgreSQL thật ----------


@dataclass(frozen=True)
class ProvisionedDatabase:
    admin: URL
    urls: dict[str, URL]

    def engine(self, role: str) -> Engine:
        return sqlalchemy.create_engine(self.urls[role])

    def secret(self, role: str) -> Secret:
        return Secret(self.urls[role].render_as_string(hide_password=False))


@pytest.fixture
def database() -> Iterator[ProvisionedDatabase]:
    base = make_url(os.environ["AIEOS_TEST_DATABASE_URL"]).set(drivername="postgresql+psycopg")
    name = f"aieos_t005_{secrets.token_hex(4)}"
    passwords = {role: secrets.token_urlsafe(24) for role in ROLES}
    server = sqlalchemy.create_engine(base, isolation_level="AUTOCOMMIT")
    with server.connect() as conn:
        conn.exec_driver_sql(f'CREATE DATABASE "{name}"')
    admin = base.set(database=name)
    target = sqlalchemy.create_engine(admin, isolation_level="AUTOCOMMIT")
    try:
        with target.connect() as conn:
            # Gửi nguyên văn qua psycopg (không tham số) như psql: `%I` của format() không phải placeholder.
            driver = conn.connection.driver_connection
            assert driver is not None
            driver.execute(provision_roles_sql())
            for role, password in passwords.items():
                conn.exec_driver_sql(f"ALTER ROLE {role} PASSWORD '{password}'")
        target.dispose()
        urls = {role: admin.set(username=role, password=passwords[role]) for role in ROLES}
        yield ProvisionedDatabase(admin, urls)
    finally:
        target.dispose()
        with server.connect() as conn:
            conn.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        server.dispose()


def migrate_to_head(db: ProvisionedDatabase) -> None:
    owner = db.engine("aieos_owner")
    with owner.begin() as conn:
        upgrade(conn, "head")
    owner.dispose()


def denied(engine: Engine, statement: str) -> bool:
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(statement)
    except DBAPIError as error:
        return getattr(error.orig, "sqlstate", None) == "42501"  # insufficient_privilege
    return False


@pytest.mark.db
def test_provisioned_roles_are_unprivileged(database: ProvisionedDatabase) -> None:
    server = sqlalchemy.create_engine(database.admin)
    with server.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolcanlogin "
                "FROM pg_roles WHERE rolname = ANY(:roles)"
            ),
            {"roles": list(ROLES)},
        ).all()
        owner = conn.execute(
            text("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()")
        ).scalar_one()
    server.dispose()
    assert {row.rolname for row in rows} == set(ROLES)
    for row in rows:
        assert row.rolcanlogin
        assert not (row.rolsuper or row.rolcreatedb or row.rolcreaterole or row.rolreplication or row.rolbypassrls)
    assert owner == "aieos_owner"


@pytest.mark.db
def test_upgrade_from_empty_to_head(database: ProvisionedDatabase) -> None:
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        assert current_revision(conn) is None
        upgrade(conn, "head")
        assert current_revision(conn) == head_revision()
        schemas: dict[str, str] = dict(
            conn.execute(
                text("SELECT nspname, pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname = ANY(:s)"),
                {"s": list(SCHEMAS)},
            ).all()
        )
    owner.dispose()
    assert schemas == dict.fromkeys(SCHEMAS, "aieos_owner")


@pytest.mark.db
def test_model_matches_schema(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.connect() as conn:
        assert compare_schema(conn, Base.metadata) == []
    owner.dispose()


@pytest.mark.db
def test_downgrade_one_step_then_upgrade_again(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        downgrade(conn, "-1")
        assert current_revision(conn) is None
        left = conn.execute(text("SELECT count(*) FROM pg_namespace WHERE nspname = ANY(:s)"), {"s": list(SCHEMAS)})
        assert left.scalar_one() == 0
        upgrade(conn, "head")
        assert current_revision(conn) == head_revision()
    owner.dispose()


@pytest.mark.db
def test_app_role_has_no_ddl(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    app = database.engine("aieos_app")
    assert denied(app, "CREATE SCHEMA app_probe")
    assert denied(app, "CREATE TABLE public.app_probe (id int)")
    assert denied(app, "CREATE TEMP TABLE app_probe (id int)")
    for schema in SCHEMAS:
        assert denied(app, f"CREATE TABLE {schema}.app_probe (id int)"), schema
    app.dispose()


@pytest.mark.db
def test_app_cannot_run_migrations(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    app = database.engine("aieos_app")
    with pytest.raises(DBAPIError):
        with app.begin() as conn:
            downgrade(conn, "base")
    app.dispose()


@pytest.mark.db
def test_default_privileges_on_new_tables(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE identity.probe (id int PRIMARY KEY, v text)")
        privileges = {
            (role, privilege): conn.execute(
                text("SELECT has_table_privilege(:role, 'identity.probe', :privilege)"),
                {"role": role, "privilege": privilege},
            ).scalar_one()
            for role in ("aieos_app", "aieos_backup")
            for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
        }
    owner.dispose()
    allowed = {("aieos_app", p) for p in ("SELECT", "INSERT", "UPDATE")} | {("aieos_backup", "SELECT")}
    assert {key for key, value in privileges.items() if value} == allowed
    app = database.engine("aieos_app")
    assert denied(app, "ALTER TABLE identity.probe ADD COLUMN x int")
    assert denied(app, "DROP TABLE identity.probe")
    assert denied(app, "DELETE FROM identity.probe")
    with app.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one() == head_revision()
    app.dispose()


@pytest.mark.db
def test_transaction_commits_or_rolls_back(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    owner = database.engine("aieos_owner")
    with owner.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE identity.probe (id int PRIMARY KEY)")
    owner.dispose()
    engine = create_db_engine(database.secret("aieos_app"))
    factory = make_session_factory(engine)
    with transaction(factory) as session:
        session.execute(text("INSERT INTO identity.probe VALUES (1)"))
    with pytest.raises(RuntimeError):
        with transaction(factory) as session:
            session.execute(text("INSERT INTO identity.probe VALUES (2)"))
            raise RuntimeError("hủy")
    with transaction(factory) as session:
        assert session.execute(text("SELECT id FROM identity.probe ORDER BY id")).scalars().all() == [1]
    engine.dispose()


@pytest.mark.db
def test_migrate_command_requires_owner_role_and_hides_secret(database: ProvisionedDatabase) -> None:
    env = {k: v for k, v in os.environ.items() if not k.startswith("AIEOS_")}
    command = [sys.executable, "-m", "aieos.app", "migrate"]

    # CSDL chưa migrate: role ứng dụng không có DDL → lệnh thất bại, không in mật khẩu.
    app_url = database.urls["aieos_app"]
    env["AIEOS_DATABASE_OWNER_URL"] = app_url.render_as_string(hide_password=False)
    failed = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert failed.returncode == 1
    assert str(app_url.password) not in failed.stdout + failed.stderr

    owner_url = database.urls["aieos_owner"]
    env["AIEOS_DATABASE_OWNER_URL"] = owner_url.render_as_string(hide_password=False)
    result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr[-500:].replace(str(owner_url.password), "***")
    assert head_revision() in result.stdout
    assert str(owner_url.password) not in result.stdout + result.stderr
