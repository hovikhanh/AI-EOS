"""Danh bạ và cây tổ chức (T-201; SRS-ACC-11, SRS-ACC-03; API-ORG-01, API-ORG-02).

- **Đọc:** cây đơn vị (danh sách phẳng có `parent_id`); danh bạ nhân viên `ACTIVE` chỉ gồm trường danh bạ — họ tên,
  chức danh, đơn vị, quản lý trực tiếp (SRS-ACC-11, R6). Không trả `status`, `source_document_id` hay trường khác.
- **Ghi** (`create_unit`, `create_employee`, `set_head`): cho import nhân sự (T-210, qua write gateway) và test; chưa có
  API ghi. Vòng trong cây/quan hệ quản lý bị trigger CSDL từ chối (`AE004`, `AE005`) → `422 VALIDATION_ERROR`.
- **Phạm vi MANAGER (`OrgDirectoryScope`, cài `access.api.OrgScope` của T-108):** đơn vị người dùng **làm trưởng**
  (`org_unit.head_employee_id` = nhân viên gắn với tài khoản qua `identity.user_account.employee_id`) và mọi đơn vị cấp
  dưới. Lựa chọn của agent theo nguyên tắc tối thiểu quyền (Implementation_Plan §34): chỉ là thành viên đơn vị thì
  không được quyền MANAGER trên đơn vị đó.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from aieos.platform.api import ApiError

_CYCLE = {"AE004": "parent_id", "AE005": "manager_id"}


@dataclass(frozen=True)
class Unit:
    id: uuid.UUID
    name: str
    code: str | None
    parent_id: uuid.UUID | None
    head_employee_id: uuid.UUID | None


@dataclass(frozen=True)
class DirectoryEntry:
    id: uuid.UUID
    full_name: str
    title: str | None
    org_unit_id: uuid.UUID | None
    org_unit_name: str | None
    manager_id: uuid.UUID | None
    manager_name: str | None


def _write(session: Session, sql: str, params: dict[str, object]) -> None:
    try:
        with session.begin_nested():
            session.execute(text(sql), params)
    except DBAPIError as error:
        field = _CYCLE.get(getattr(error.orig, "sqlstate", None) or "")
        if field is None:
            raise
        raise ApiError("VALIDATION_ERROR", errors=[{"field": field, "message": "Tạo vòng trong cây"}]) from None


def create_unit(
    session: Session, *, name: str, code: str | None = None, parent_id: uuid.UUID | None = None
) -> uuid.UUID:
    unit_id = uuid.uuid4()
    _write(
        session,
        "INSERT INTO org.org_unit (id, name, code, parent_id) VALUES (:i, :n, :c, :p)",
        {"i": unit_id, "n": name, "c": code, "p": parent_id},
    )
    return unit_id


def create_employee(
    session: Session,
    *,
    full_name: str,
    title: str | None = None,
    org_unit_id: uuid.UUID | None = None,
    manager_id: uuid.UUID | None = None,
) -> uuid.UUID:
    employee_id = uuid.uuid4()
    _write(
        session,
        "INSERT INTO org.employee (id, full_name, title, org_unit_id, manager_id) VALUES (:i, :n, :t, :u, :m)",
        {"i": employee_id, "n": full_name, "t": title, "u": org_unit_id, "m": manager_id},
    )
    return employee_id


def set_parent(session: Session, unit_id: uuid.UUID, parent_id: uuid.UUID | None) -> None:
    _write(
        session,
        "UPDATE org.org_unit SET parent_id = :p, version = version + 1 WHERE id = :i",
        {"p": parent_id, "i": unit_id},
    )


def set_head(session: Session, unit_id: uuid.UUID, employee_id: uuid.UUID | None) -> None:
    _write(
        session,
        "UPDATE org.org_unit SET head_employee_id = :e, version = version + 1 WHERE id = :i",
        {"e": employee_id, "i": unit_id},
    )


def list_units(session: Session) -> list[Unit]:
    rows = session.execute(
        text("SELECT id, name, code, parent_id, head_employee_id FROM org.org_unit ORDER BY name, id")
    )
    return [Unit(r.id, r.name, r.code, r.parent_id, r.head_employee_id) for r in rows]


def list_directory(
    session: Session,
    *,
    limit: int,
    after: tuple[str, uuid.UUID] | None = None,
    org_unit_id: uuid.UUID | None = None,
    query: str | None = None,
) -> list[DirectoryEntry]:
    """Nhân viên `ACTIVE`, sắp theo họ tên; `query` tìm theo họ tên (không phân biệt hoa thường)."""
    rows = session.execute(
        text(
            "SELECT e.id, e.full_name, e.title, e.org_unit_id, u.name AS org_unit_name, e.manager_id, "
            "m.full_name AS manager_name FROM org.employee e "
            "LEFT JOIN org.org_unit u ON u.id = e.org_unit_id "
            "LEFT JOIN org.employee m ON m.id = e.manager_id "
            "WHERE e.status = 'ACTIVE' "
            "AND (CAST(:unit AS uuid) IS NULL OR e.org_unit_id = :unit) "
            "AND (CAST(:q AS text) IS NULL OR e.full_name ILIKE '%' || :q || '%') "
            "AND (CAST(:after_name AS text) IS NULL OR (e.full_name, e.id) > (:after_name, :after_id)) "
            "ORDER BY e.full_name, e.id LIMIT :n"
        ),
        {
            "unit": org_unit_id,
            "q": query.replace("%", r"\%").replace("_", r"\_") if query else None,
            "after_name": after[0] if after else None,
            "after_id": after[1] if after else uuid.UUID(int=0),
            "n": limit,
        },
    )
    return [
        DirectoryEntry(r.id, r.full_name, r.title, r.org_unit_id, r.org_unit_name, r.manager_id, r.manager_name)
        for r in rows
    ]


def subtree(session: Session, unit_ids: Iterable[uuid.UUID]) -> frozenset[uuid.UUID]:
    """Các đơn vị đã cho và mọi đơn vị cấp dưới."""
    roots = list(unit_ids)
    if not roots:
        return frozenset()
    rows = session.execute(
        text(
            "WITH RECURSIVE down(id) AS (SELECT unnest(CAST(:roots AS uuid[])) "
            "UNION SELECT u.id FROM org.org_unit u JOIN down ON u.parent_id = down.id) SELECT id FROM down"
        ),
        {"roots": roots},
    )
    return frozenset(r.id for r in rows)


def user_unit_path(session: Session, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
    """Đơn vị của nhân viên gắn với tài khoản và mọi đơn vị cấp trên (`access.api.Resource.org_units`); rỗng nếu tài
    khoản chưa gắn nhân viên hoặc nhân viên chưa có đơn vị."""
    rows = session.execute(
        text(
            "WITH RECURSIVE up(id, parent_id) AS ("
            "SELECT u.id, u.parent_id FROM identity.user_account a JOIN org.employee e ON e.id = a.employee_id "
            "JOIN org.org_unit u ON u.id = e.org_unit_id WHERE a.id = :user "
            "UNION SELECT p.id, p.parent_id FROM org.org_unit p JOIN up ON p.id = up.parent_id) SELECT id FROM up"
        ),
        {"user": user_id},
    )
    return frozenset(r.id for r in rows)


@dataclass(frozen=True)
class OrgDirectoryScope:
    """`access.api.OrgScope` dựa trên cây tổ chức (T-201 cho T-108)."""

    def managed_units(self, session: Session, user_id: uuid.UUID) -> frozenset[uuid.UUID]:
        heads = session.execute(
            text(
                "SELECT u.id FROM org.org_unit u JOIN identity.user_account a ON a.employee_id = u.head_employee_id "
                "WHERE a.id = :user"
            ),
            {"user": user_id},
        )
        return subtree(session, [r.id for r in heads])

    def subtree(self, session: Session, unit_ids: Iterable[uuid.UUID]) -> frozenset[uuid.UUID]:
        return subtree(session, unit_ids)
