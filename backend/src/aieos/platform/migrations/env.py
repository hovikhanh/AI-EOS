"""Môi trường Alembic (T-005). Chỉ chạy online với connection do `aieos.platform.db` truyền vào.

Không đọc URL hay biến môi trường ở đây: connection được tạo từ cấu hình T-004 bởi role `aieos_owner`.
"""

from alembic import context
from sqlalchemy import Connection, MetaData

from aieos.platform.db import SCHEMAS

if context.is_offline_mode():
    raise RuntimeError("Không hỗ trợ migration offline (sinh SQL); chạy qua lệnh migration với role aieos_owner")

connection = context.config.attributes.get("connection")
if not isinstance(connection, Connection):
    raise RuntimeError("Thiếu connection: chạy migration qua aieos.platform.db (lệnh `python -m aieos.app migrate`)")
target_metadata = context.config.attributes.get("target_metadata")
if target_metadata is not None and not isinstance(target_metadata, MetaData):
    raise RuntimeError("target_metadata phải là sqlalchemy.MetaData")


def include_name(name: str | None, type_: str, parent_names: object) -> bool:
    return name in SCHEMAS if type_ == "schema" else True


context.configure(
    connection=connection,
    target_metadata=target_metadata,
    include_schemas=True,
    include_name=include_name,
)
with context.begin_transaction():
    context.run_migrations()
