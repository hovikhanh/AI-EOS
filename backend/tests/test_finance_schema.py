"""T-401: bảng `finance.*` và bất biến INV-01…07 ở CSDL (SRS-FIN-13, SRS-FIN-17; ADR-009; Database_Design §7, §8).

TC do T-401 làm chủ (mức CSDL): TC-FIN-01 (`test_posted_amount_immutable`), TC-FIN-02 (`test_delete_refused`),
TC-FIN-03 (`test_approver_cannot_be_creator`), TC-FIN-04 (`test_on_hold_cannot_be_posted`). Thao tác chạy bằng role
ứng dụng `aieos_app` (như bị tấn công qua SQL), trừ khi ghi rõ.
"""

import hashlib
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from aieos.identity.api import hash_password
from tests.conftest import ProvisionedDatabase, migrate_to_head


@dataclass
class Env:
    app: Engine
    owner: Engine
    creator: uuid.UUID
    approver: uuid.UUID
    period: uuid.UUID

    def run(self, sql: str, params: dict[str, Any] | None = None, engine: Engine | None = None) -> Any:
        with (engine or self.app).begin() as conn:
            return conn.execute(text(sql), params or {})

    def sqlstate(self, sql: str, params: dict[str, Any] | None = None, engine: Engine | None = None) -> str | None:
        with pytest.raises(DBAPIError) as info:
            self.run(sql, params, engine)
        return getattr(info.value.orig, "sqlstate", None)

    def transaction(self, *, amount: str = "1250000.00", **extra: Any) -> uuid.UUID:
        tx_id = uuid.uuid4()
        columns = {
            "id": tx_id,
            "record_type": "EXPENSE",
            "amount": amount,
            "currency": "VND",
            "transaction_date": date(2026, 10, 5),
            "period_id": self.period,
            "created_by": self.creator,
            "idempotency_key": uuid.uuid4().hex,
            "request_hash": hashlib.sha256(tx_id.bytes).digest(),
            **extra,
        }
        names = ", ".join(columns)
        values = ", ".join(f":{k}" for k in columns)
        self.run(f"INSERT INTO finance.transaction ({names}) VALUES ({values})", columns)
        return tx_id

    def move(self, tx_id: uuid.UUID, status: str, extra: str = "") -> None:
        self.run(f"UPDATE finance.transaction SET status = :s{extra} WHERE id = :i", {"s": status, "i": tx_id})

    def post(self, tx_id: uuid.UUID) -> None:
        self.move(tx_id, "PENDING_APPROVAL", ", submitted_by = created_by, submitted_at = now()")
        self.run(
            "UPDATE finance.transaction SET status = 'POSTED', approved_by = :a, approved_at = now() WHERE id = :i",
            {"a": self.approver, "i": tx_id},
        )


@pytest.fixture
def env(database: ProvisionedDatabase) -> Iterator[Env]:
    migrate_to_head(database)
    app = database.engine("aieos_app")
    owner = database.engine("aieos_owner")
    users = []
    with app.begin() as conn:
        for email in ("tao@example.com", "duyet@example.com"):
            user_id = uuid.uuid4()
            conn.execute(
                text(
                    "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                    "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p)"
                ),
                {"i": user_id, "e": email, "p": hash_password("Mat-khau-dung-123!")},
            )
            users.append(user_id)
        period = uuid.uuid4()
        conn.execute(
            text(
                "INSERT INTO finance.reporting_period (id, code, start_date, end_date) "
                "VALUES (:i, '2026-10', '2026-10-01', '2026-10-31')"
            ),
            {"i": period},
        )
    yield Env(app, owner, users[0], users[1], period)
    app.dispose()
    owner.dispose()


# ---------- TC-FIN-01…04 ----------


@pytest.mark.db
def test_posted_amount_immutable(env: Env) -> None:
    """TC-FIN-01 (INV-04): UPDATE số tiền giao dịch POSTED bằng role ứng dụng → trigger từ chối; chỉ POSTED →
    REVERSED."""
    tx = env.transaction()
    env.post(tx)
    assert env.sqlstate("UPDATE finance.transaction SET amount = 1 WHERE id = :i", {"i": tx}) == "AE022"
    assert env.sqlstate("UPDATE finance.transaction SET description = 'sửa' WHERE id = :i", {"i": tx}) == "AE022"
    assert env.sqlstate("UPDATE finance.transaction SET status = 'CANCELLED' WHERE id = :i", {"i": tx}) == "AE022"
    assert env.sqlstate("UPDATE finance.transaction SET amount = 1 WHERE id = :i", {"i": tx}, env.owner) == "AE022"
    env.run("UPDATE finance.transaction SET status = 'REVERSED', version = version + 1 WHERE id = :i", {"i": tx})
    assert env.sqlstate("UPDATE finance.transaction SET amount = 1 WHERE id = :i", {"i": tx}) == "AE022"
    draft = env.transaction()
    env.run("UPDATE finance.transaction SET amount = 99 WHERE id = :i", {"i": draft})  # DRAFT sửa được


@pytest.mark.db
def test_delete_refused(env: Env) -> None:
    """TC-FIN-02 (INV-05): DELETE giao dịch — role ứng dụng không có quyền; role khác bị trigger chặn."""
    tx = env.transaction()
    with pytest.raises(DBAPIError) as info:
        env.run("DELETE FROM finance.transaction WHERE id = :i", {"i": tx})
    assert "permission denied" in str(info.value)
    assert env.sqlstate("DELETE FROM finance.transaction WHERE id = :i", {"i": tx}, env.owner) == "AE023"


@pytest.mark.db
def test_approver_cannot_be_creator(env: Env) -> None:
    """TC-FIN-03 (INV-01): đặt `approved_by = created_by` (hoặc người gửi) bằng SQL → CHECK từ chối."""
    tx = env.transaction()
    env.move(tx, "PENDING_APPROVAL", ", submitted_by = created_by, submitted_at = now()")
    for sql in (
        "UPDATE finance.transaction SET status = 'POSTED', approved_by = created_by, approved_at = now() WHERE id = :i",
        "UPDATE finance.transaction SET status = 'POSTED', approved_by = submitted_by WHERE id = :i",
        "UPDATE finance.transaction SET status = 'REJECTED', rejected_by = created_by, reject_reason = 'x' "
        "WHERE id = :i",
    ):
        assert env.sqlstate(sql, {"i": tx}) == "23514", sql


@pytest.mark.db
def test_on_hold_cannot_be_posted(env: Env) -> None:
    """TC-FIN-04 (INV-06, SRS-FIN-17): `ON_HOLD → POSTED` bằng SQL → trigger từ chối; `ON_HOLD` cần `hold_reason`."""
    tx = env.transaction()
    env.move(tx, "PENDING_APPROVAL", ", submitted_by = created_by")
    assert env.sqlstate("UPDATE finance.transaction SET status = 'ON_HOLD' WHERE id = :i", {"i": tx}) == "23514"
    env.move(tx, "ON_HOLD", ", hold_reason = 'PERIOD_CLOSED'")
    posted = env.sqlstate(
        "UPDATE finance.transaction SET status = 'POSTED', hold_reason = NULL, approved_by = :a WHERE id = :i",
        {"a": env.approver, "i": tx},
    )
    assert posted == "AE024"
    env.move(tx, "CANCELLED", ", hold_reason = NULL, cancelled_by = created_by, cancel_reason = 'Rút lại'")


# ---------- INV-02, 03, 06, 07, kỳ, lịch sử ----------


@pytest.mark.db
def test_status_transitions_follow_adr009(env: Env) -> None:
    """INV-06: bản ghi mới ở DRAFT; chỉ các cặp chuyển trạng thái của ADR-009."""
    bad_new = uuid.uuid4()
    state = env.sqlstate(
        "INSERT INTO finance.transaction (id, record_type, amount, currency, transaction_date, created_by, status, "
        "idempotency_key, request_hash) VALUES (:i, 'REVENUE', 1, 'VND', '2026-10-05', :c, 'POSTED', 'k', :h)",
        {"i": bad_new, "c": env.creator, "h": b"x" * 32},
    )
    assert state == "AE024"
    tx = env.transaction()
    assert (
        env.sqlstate(
            "UPDATE finance.transaction SET status = 'POSTED', approved_by = :a WHERE id = :i",
            {"a": env.approver, "i": tx},
        )
        == "AE024"
    )
    env.move(tx, "CANCELLED", ", cancelled_by = created_by")
    assert env.sqlstate("UPDATE finance.transaction SET status = 'DRAFT' WHERE id = :i", {"i": tx}) == "AE024"
    rejected = env.transaction()
    env.move(rejected, "PENDING_APPROVAL", ", submitted_by = created_by")
    assert (
        env.sqlstate(
            "UPDATE finance.transaction SET status = 'REJECTED', rejected_by = :a WHERE id = :i",
            {"a": env.approver, "i": rejected},
        )
        == "23514"
    )
    env.run(
        "UPDATE finance.transaction SET status = 'REJECTED', rejected_by = :a, reject_reason = 'Sai chứng từ' "
        "WHERE id = :i",
        {"a": env.approver, "i": rejected},
    )


@pytest.mark.db
def test_submit_and_post_only_into_open_period(env: Env) -> None:
    """INV-07: gửi duyệt/ghi sổ cần kỳ OPEN chứa ngày giao dịch; kỳ CLOSED không mở lại; kỳ không chồng lấn."""
    no_period = env.transaction(period_id=None)
    assert (
        env.sqlstate("UPDATE finance.transaction SET status = 'PENDING_APPROVAL' WHERE id = :i", {"i": no_period})
        == "AE025"
    )
    outside = env.transaction(transaction_date=date(2026, 11, 3))
    assert (
        env.sqlstate("UPDATE finance.transaction SET status = 'PENDING_APPROVAL' WHERE id = :i", {"i": outside})
        == "AE025"
    )
    pending = env.transaction()
    env.move(pending, "PENDING_APPROVAL", ", submitted_by = created_by")
    env.run(
        "UPDATE finance.reporting_period SET status = 'CLOSED', closed_by = :u, closed_at = now() WHERE id = :p",
        {"u": env.approver, "p": env.period},
    )
    post = env.sqlstate(
        "UPDATE finance.transaction SET status = 'POSTED', approved_by = :a WHERE id = :i",
        {"a": env.approver, "i": pending},
    )
    assert post == "AE025"
    draft = env.transaction()
    assert (
        env.sqlstate("UPDATE finance.transaction SET status = 'PENDING_APPROVAL' WHERE id = :i", {"i": draft})
        == "AE025"
    )
    reopen = env.sqlstate(
        "UPDATE finance.reporting_period SET status = 'OPEN', closed_by = NULL, closed_at = NULL WHERE id = :p",
        {"p": env.period},
    )
    assert reopen == "AE020"
    overlap = env.sqlstate(
        "INSERT INTO finance.reporting_period (id, code, start_date, end_date) "
        "VALUES (gen_random_uuid(), '2026-10b', '2026-10-31', '2026-11-30')"
    )
    assert overlap == "23P01"
    env.run(
        "INSERT INTO finance.reporting_period (id, code, start_date, end_date) "
        "VALUES (gen_random_uuid(), '2026-11', '2026-11-01', '2026-11-30')"
    )


@pytest.mark.db
def test_reversal_rules(env: Env) -> None:
    """INV-02: tối đa một bút toán đảo đang mở/đã ghi cho mỗi giao dịch; INV-03: chỉ đảo giao dịch POSTED không phải
    bút toán đảo; bút toán đảo cần lý do và liên kết."""
    original = env.transaction()
    draft_target = env.transaction()
    state = env.sqlstate(
        "INSERT INTO finance.transaction (id, record_type, kind, amount, currency, transaction_date, created_by, "
        "reverses_id, reason, idempotency_key, request_hash) VALUES (gen_random_uuid(), 'EXPENSE', 'REVERSAL', -1, "
        "'VND', '2026-10-05', :c, :r, 'Đảo', 'k1', :h)",
        {"c": env.creator, "r": draft_target, "h": b"x" * 32},
    )
    assert state == "AE021"  # gốc chưa POSTED
    env.post(original)
    reversal = env.transaction(kind="REVERSAL", reverses_id=original, reason="Nhập sai", amount="-1250000.00")
    duplicate = env.sqlstate(
        "INSERT INTO finance.transaction (id, record_type, kind, amount, currency, transaction_date, created_by, "
        "reverses_id, reason, idempotency_key, request_hash) VALUES (gen_random_uuid(), 'EXPENSE', 'REVERSAL', -1, "
        "'VND', '2026-10-05', :c, :r, 'Đảo lần 2', 'k2', :h)",
        {"c": env.creator, "r": original, "h": b"y" * 32},
    )
    assert duplicate == "23505"
    env.post(reversal)
    state = env.sqlstate(
        "INSERT INTO finance.transaction (id, record_type, kind, amount, currency, transaction_date, created_by, "
        "reverses_id, reason, idempotency_key, request_hash) VALUES (gen_random_uuid(), 'EXPENSE', 'REVERSAL', 1, "
        "'VND', '2026-10-05', :c, :r, 'Đảo bút toán đảo', 'k3', :h)",
        {"c": env.creator, "r": reversal, "h": b"z" * 32},
    )
    assert state == "AE021"
    missing_reason = env.sqlstate(
        "INSERT INTO finance.transaction (id, record_type, kind, amount, currency, transaction_date, created_by, "
        "adjusts_id, idempotency_key, request_hash) VALUES (gen_random_uuid(), 'EXPENSE', 'ADJUSTMENT', 1, "
        "'VND', '2026-10-05', :c, :r, 'k4', :h)",
        {"c": env.creator, "r": original, "h": b"w" * 32},
    )
    assert missing_reason == "23514"


@pytest.mark.db
def test_event_log_append_only_and_money_exact(env: Env) -> None:
    tx = env.transaction(amount="1250000.55")
    env.run(
        "INSERT INTO finance.transaction_event (transaction_id, from_status, to_status, actor_id) "
        "VALUES (:t, NULL, 'DRAFT', :a)",
        {"t": tx, "a": env.creator},
    )
    with pytest.raises(DBAPIError) as update:
        env.run("UPDATE finance.transaction_event SET reason = 'sửa'")
    assert "permission denied" in str(update.value)
    assert env.sqlstate("UPDATE finance.transaction_event SET reason = 'sửa'", engine=env.owner) == "AE023"
    assert env.sqlstate("DELETE FROM finance.transaction_event", engine=env.owner) == "AE023"
    amount = env.run("SELECT amount FROM finance.transaction WHERE id = :i", {"i": tx}).scalar_one()
    assert str(amount) == "1250000.55"  # NUMERIC, không float
    assert env.sqlstate("UPDATE finance.transaction SET currency = 'vnd' WHERE id = :i", {"i": tx}) == "23514"
