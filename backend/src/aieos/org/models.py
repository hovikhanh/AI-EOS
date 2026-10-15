"""Model `org.*` (Database_Design §6). Chỉ dùng nội bộ module `org`.

Bảng do migration 0010 tạo; model phải khớp schema (TC-MIG-01). Chỉ trường danh bạ (R6).
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from aieos.platform.api import Base

_SCHEMA = {"schema": "org"}


class OrgUnitRow(Base):
    __tablename__ = "org_unit"
    __table_args__ = (
        UniqueConstraint("code"),
        CheckConstraint("name <> ''", name="name"),
        CheckConstraint("code IS NULL OR code <> ''", name="code"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="not_own_parent"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_org_unit_parent", "parent_id"),
        Index("ix_org_unit_head", "head_employee_id"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    head_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("org.employee.id", use_alter=True, name="fk_org_unit_head_employee_id_employee")
    )
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("capture.source_document.id", use_alter=True, name="fk_org_unit_source_document_id_source_document"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class EmployeeRow(Base):
    __tablename__ = "employee"
    __table_args__ = (
        CheckConstraint("full_name <> ''", name="full_name"),
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="status"),
        CheckConstraint("manager_id IS NULL OR manager_id <> id", name="not_own_manager"),
        CheckConstraint("version >= 1", name="version"),
        Index("ix_employee_org_unit", "org_unit_id"),
        Index("ix_employee_name", "full_name", "id"),
        _SCHEMA,
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.org_unit.id"))
    manager_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("org.employee.id"))
    status: Mapped[str] = mapped_column(Text, server_default=text("'ACTIVE'"))
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("capture.source_document.id", use_alter=True, name="fk_employee_source_document_id_source_document"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
