"""Endpoint danh bạ (T-201): API-ORG-01 `GET /org/units`, API-ORG-02 `GET /org/employees`.

Quyền `org.directory.read` (mọi role — Architecture §6) qua `PermissionGuard` (T-108). Chỉ trường danh bạ (SRS-ACC-11).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from aieos.access.api import PermissionGuard
from aieos.org.service import list_directory, list_units
from aieos.platform.api import (
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    ApiError,
    decode_cursor,
    encode_cursor,
    transaction,
)

READ = "org.directory.read"


class UnitOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str | None
    parent_id: uuid.UUID | None
    head_employee_id: uuid.UUID | None


class UnitList(BaseModel):
    items: list[UnitOut]


class EmployeeOut(BaseModel):
    id: uuid.UUID
    full_name: str
    title: str | None
    org_unit_id: uuid.UUID | None
    org_unit_name: str | None
    manager_id: uuid.UUID | None
    manager_name: str | None


class EmployeePage(BaseModel):
    items: list[EmployeeOut]
    next_cursor: str | None


def _after(cursor: str | None) -> tuple[str, uuid.UUID] | None:
    if cursor is None:
        return None
    name, item_id = decode_cursor(cursor, 2)
    try:
        return name, uuid.UUID(item_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "cursor", "message": "cursor không hợp lệ"}]) from None


def build_org_router(guard: PermissionGuard) -> APIRouter:
    router = APIRouter(tags=["org"])

    @router.get("/org/units", response_model=UnitList, **guard.route(READ))
    def units() -> UnitList:
        with transaction(guard.factory) as session:
            return UnitList(items=[UnitOut(**u.__dict__) for u in list_units(session)])

    @router.get("/org/employees", response_model=EmployeePage, **guard.route(READ))
    def employees(
        org_unit_id: uuid.UUID | None = None,
        q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
        limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
    ) -> EmployeePage:
        after = _after(cursor)
        with transaction(guard.factory) as session:
            items = list_directory(session, limit=limit + 1, after=after, org_unit_id=org_unit_id, query=q)
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor((items[-1].full_name, str(items[-1].id)))
        return EmployeePage(items=[EmployeeOut(**e.__dict__) for e in items], next_cursor=next_cursor)

    return router
