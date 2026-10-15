"""M-04 audit: bảng `audit.event` append-only.

Revision: 0002 (sau 0001)
Yêu cầu/ADR liên quan: T-008, SRS-AUD-01, SRS-AUD-02, SRS-AUD-03, ADR-010, INV-14, INV-05; Database_Design §2, §8, §9;
Implementation_Plan §5 (M-04).

- Cột theo Database_Design §9; CHECK cho `category`, `actor_type`, `outcome`; `ai_agent`, `autonomy_level` NULL khi
  không phải AI; `autonomy_level` trong L0–L3 (D-11). `id` là `bigint` identity `ALWAYS` (Database_Design §1).
- Index theo Database_Design §8: `(resource_type, resource_id, occurred_at)`, `(actor_user_id, occurred_at)`.
- Append-only (INV-14): `aieos_app` chỉ còn INSERT, SELECT (thu hồi UPDATE do quyền mặc định của 0001 cấp);
  trigger từ chối UPDATE, DELETE (từng dòng) và TRUNCATE (câu lệnh) với mọi role, kể cả chủ sở hữu.
- Chưa có khóa ngoại tới `identity.user_account` (bảng của T-101 chưa tồn tại).
Tên ràng buộc ghi đầy đủ, khớp quy ước đặt tên của `platform.db.Base`.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("on_behalf_of_user_id", sa.Uuid(), nullable=True),
        sa.Column("ai_agent", sa.Text(), nullable=True),
        sa.Column("autonomy_level", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("request_ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_event"),
        sa.CheckConstraint("category IN ('SECURITY', 'ADMIN', 'BUSINESS', 'AI')", name="ck_event_category"),
        sa.CheckConstraint("actor_type IN ('USER', 'AI', 'SYSTEM', 'BOOTSTRAP')", name="ck_event_actor_type"),
        sa.CheckConstraint("outcome IN ('SUCCESS', 'DENIED', 'FAILED', 'BLOCKED')", name="ck_event_outcome"),
        sa.CheckConstraint(
            "autonomy_level IS NULL OR autonomy_level IN ('L0', 'L1', 'L2', 'L3')", name="ck_event_autonomy_level"
        ),
        sa.CheckConstraint(
            "actor_type = 'AI' OR (ai_agent IS NULL AND autonomy_level IS NULL)", name="ck_event_ai_fields"
        ),
        sa.CheckConstraint("action <> ''", name="ck_event_action_not_empty"),
        schema="audit",
    )
    op.create_index("ix_event_resource", "event", ["resource_type", "resource_id", "occurred_at"], schema="audit")
    op.create_index("ix_event_actor", "event", ["actor_user_id", "occurred_at"], schema="audit")

    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit.event FROM aieos_app")
    op.execute(
        """
        CREATE FUNCTION audit.reject_modification() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'audit.event là append-only (INV-14): % bị từ chối', TG_OP
                USING ERRCODE = 'insufficient_privilege';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER event_reject_update_delete BEFORE UPDATE OR DELETE ON audit.event "
        "FOR EACH ROW EXECUTE FUNCTION audit.reject_modification()"
    )
    op.execute(
        "CREATE TRIGGER event_reject_truncate BEFORE TRUNCATE ON audit.event "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_modification()"
    )


def downgrade() -> None:
    op.drop_table("event", schema="audit")
    op.execute("DROP FUNCTION audit.reject_modification()")
