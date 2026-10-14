"""Nền CSDL (T-005, Database_Design §2, §10, D-42): engine, session, model gốc, chạy migration Alembic.

- Chỉ module `platform` tạo engine (C7). URL lấy từ `Secret` (T-004); lỗi không chứa giá trị URL.
- `aieos_app` cho api/worker (`AIEOS_DATABASE_URL`), `aieos_owner` chỉ cho lệnh migration (`AIEOS_DATABASE_OWNER_URL`).
- Alembic: một chuỗi revision ở `aieos/platform/migrations`; metadata model do nơi gọi truyền vào vì `platform`
  không import module khác (C5) — composition root `app` gom metadata.
- Role CSDL tạo một lần bằng `sql/provision_roles.sql` (superuser), không qua Alembic.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from typing import Any

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine, MetaData, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from aieos.platform.config import Secret, Settings

DRIVER = "postgresql+psycopg"
_ACCEPTED_DRIVERS = frozenset({"postgresql", "postgres", DRIVER})
SCRIPT_LOCATION = "aieos.platform:migrations"

# Schema theo module (Database_Design §2). Migration giữ bản sao riêng; test đối chiếu ba nguồn.
SCHEMAS: tuple[str, ...] = (
    "identity",
    "access",
    "org",
    "capture",
    "goals",
    "work",
    "insights",
    "knowledge",
    "finance",
    "ai",
    "jobs",
    "audit",
    "notify",
)
ROLES: tuple[str, ...] = ("aieos_owner", "aieos_app", "aieos_backup")

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Model gốc dùng chung; model của mỗi module khai báo `__table_args__ = {"schema": "<module>"}`."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class DatabaseConfigError(Exception):
    """URL CSDL không hợp lệ; thông điệp không chứa giá trị URL."""


def to_url(secret: Secret) -> URL:
    """Chuyển URL trong secret thành URL SQLAlchemy dùng psycopg 3; chỉ nhận PostgreSQL."""
    try:
        url = make_url(secret.reveal())
    except ArgumentError:
        raise DatabaseConfigError("URL CSDL không đúng định dạng") from None
    if url.drivername not in _ACCEPTED_DRIVERS:
        raise DatabaseConfigError("URL CSDL phải là PostgreSQL (postgresql:// hoặc postgresql+psycopg://)")
    return url.set(drivername=DRIVER)


def create_db_engine(secret: Secret, **kwargs: Any) -> Engine:
    return create_engine(to_url(secret), pool_pre_ping=True, **kwargs)


def create_app_engine(settings: Settings) -> Engine:
    """Engine role `aieos_app` cho api/worker."""
    return create_db_engine(settings.secret("AIEOS_DATABASE_URL"))


def create_owner_engine(settings: Settings) -> Engine:
    """Engine role `aieos_owner`, chỉ dùng trong lệnh migration."""
    return create_db_engine(settings.secret("AIEOS_DATABASE_OWNER_URL"))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False)


@contextmanager
def transaction(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Một unit of work: commit khi khối kết thúc bình thường, rollback khi có ngoại lệ (ADR-010)."""
    with factory.begin() as session:
        yield session


def provision_roles_sql() -> str:
    """SQL tạo 3 role CSDL và quyền ở mức database; chạy một lần bằng superuser, đang kết nối tới CSDL đích."""
    return resources.files("aieos.platform").joinpath("sql/provision_roles.sql").read_text(encoding="utf-8")


def _alembic_config(connection: Connection | None = None, target_metadata: MetaData | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", SCRIPT_LOCATION)
    config.attributes["connection"] = connection
    config.attributes["target_metadata"] = target_metadata
    return config


def head_revision() -> str:
    head = ScriptDirectory.from_config(_alembic_config()).get_current_head()
    if head is None:
        raise RuntimeError("Chưa có revision migration")
    return head


def script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(_alembic_config())


def current_revision(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def upgrade(connection: Connection, revision: str = "head", target_metadata: MetaData | None = None) -> None:
    command.upgrade(_alembic_config(connection, target_metadata), revision)


def downgrade(connection: Connection, revision: str) -> None:
    command.downgrade(_alembic_config(connection), revision)


def compare_schema(connection: Connection, metadata: MetaData) -> list[Any]:
    """Khác biệt model ↔ schema (TC-MIG-01) trong các schema của AI-EOS; rỗng nghĩa là khớp."""

    def include_name(name: str | None, type_: str, parent_names: Any) -> bool:
        return name in SCHEMAS if type_ == "schema" else True

    context = MigrationContext.configure(
        connection, opts={"include_schemas": True, "include_name": include_name, "target_metadata": metadata}
    )
    return list(compare_metadata(context, metadata))


def run_migrations(settings: Settings, target_metadata: MetaData | None = None) -> str:
    """Lệnh migration: nâng CSDL lên head bằng role `aieos_owner`; trả về revision hiện tại."""
    engine = create_owner_engine(settings)
    try:
        with engine.begin() as connection:
            upgrade(connection, "head", target_metadata)
            revision = current_revision(connection)
    finally:
        engine.dispose()
    return revision or ""
