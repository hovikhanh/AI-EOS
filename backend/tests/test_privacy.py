"""T-112: phát hiện và che dữ liệu cá nhân bằng quy tắc, nhãn `sensitivity`, che theo quyền `pii.unmask`, quyền `hr.*`
(SRS-ACC-10, SRS-PRV-02, R6, D-21, FL-13).

TC do T-112 làm chủ: TC-PRV-01 (`test_every_role_reads_masked_and_none_can_unmask`), TC-PRV-02
(`test_admin_gets_403_on_hr_reads_and_export`). TC-PRV-03 (câu trả lời AI) chưa kiểm được — chưa có chat AI (T-306);
T-306 dùng `access.api.mask_for` cho câu trả lời.
"""

import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.access.api import (
    PermissionGuard,
    ScopeType,
    can_unmask,
    create_assignment,
    grant_role,
    known_roles,
    load_actor,
    mask_fields,
    mask_for,
)
from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, record
from aieos.identity.api import Authenticator, AuthSettings, build_auth_router, hash_password, hash_token
from aieos.platform.api import (
    CSRF_HEADER,
    PII_MASK,
    SESSION_COOKIE,
    ApiError,
    CsrfConfig,
    Secret,
    classify_text,
    create_api,
    create_db_engine,
    find_pii,
    make_session_factory,
    mask_pii,
    transaction,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head

CCCD = "079203001234"

# ---------- Phát hiện theo quy tắc ----------


@pytest.mark.parametrize(
    ("text", "kinds"),
    [
        (f"Số CCCD: {CCCD}, cấp ngày 01/01/2021", ["NATIONAL_ID"]),
        (f"căn cước công dân {CCCD}", ["NATIONAL_ID"]),
        ("CMND 025123456", ["NATIONAL_ID"]),
        (f"Mã định danh {CCCD} trong biên bản", ["NATIONAL_ID"]),  # dạng CCCD 12 số không cần từ khóa
        ("STK: 0071 0004 12345 tại Vietcombank", ["BANK_ACCOUNT"]),
        ("số tài khoản 19034567890123", ["BANK_ACCOUNT"]),
        ("Lương cơ bản: 15.000.000 đồng", ["SALARY"]),
        ("Liên hệ 0912 345 678 hoặc +84 912.345.678", ["PHONE", "PHONE"]),
        ("email nguyen.van.a+hr@congty.com.vn", ["EMAIL"]),
    ],
)
def test_detects_personal_data(text: str, kinds: list[str]) -> None:
    assert [m.kind for m in find_pii(text)] == kinds


@pytest.mark.parametrize(
    "text",
    [
        "Doanh thu quý 3 đạt 1.500.000.000 đồng, tăng 12%",
        "Task 6f1c2a3b-0000-4000-8000-012345678901 đã xong",  # UUID có nhóm 12 số
        "Kỳ 2026-10, hạn 15/10/2026 10:00",
        "Mã đơn hàng 012345, hợp đồng số 2026/HĐ-01",
        "Thu nhập lương thực tế tăng",  # từ khóa không kèm số
        "Mestk 123456789",  # từ khóa nằm trong từ khác
        "Số seri thiết bị 0791234567891234",  # dãy 16 số không phải CCCD
        "Thưởng lương 13 tháng theo quy chế",  # số ngắn sau từ khóa
    ],
)
def test_ordinary_numbers_are_not_masked(text: str) -> None:
    assert find_pii(text) == [] and mask_pii(text) == text


def test_mask_keeps_keywords_and_classify_takes_highest_label() -> None:
    text = f"Nhân viên A, CCCD {CCCD}, STK 1903456789, ĐT 0912345678"
    assert mask_pii(text) == f"Nhân viên A, CCCD {PII_MASK}, STK {PII_MASK}, ĐT {PII_MASK}"
    assert classify_text("Kế hoạch quý 4") == "NORMAL"
    assert classify_text(f"CCCD {CCCD}") == "PERSONAL"
    assert classify_text(text) == "SENSITIVE"
    assert classify_text("Kế hoạch", floor="PERSONAL") == "PERSONAL"  # nhãn nguồn không bị hạ


# ---------- Theo quyền ----------

PASSWORD = "Mat-khau-dung-123!"
KEY = Secret("khoa-csrf-test")
ORIGIN = "https://aieos.local"


def _user(engine: Engine, email: str, role: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO identity.user_account (id, email, display_name, status, password_hash) "
                "VALUES (:i, :e, 'Người dùng', 'ACTIVE', :p)"
            ),
            {"i": user_id, "e": email, "p": hash_password(PASSWORD)},
        )
    with transaction(make_session_factory(engine)) as session:
        grant_role(session, user_id=user_id, role=role, granted_by=None, reason=None)
    return user_id


@pytest.fixture
def engine(database: ProvisionedDatabase) -> Iterator[Engine]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"), pool_size=10)
    yield engine
    engine.dispose()


@pytest.mark.db
def test_every_role_reads_masked_and_none_can_unmask(engine: Engine) -> None:
    """TC-PRV-01: mọi role đọc trường nhạy cảm → bị che; không role nào bỏ che được, kể cả qua assignment (R6)."""
    factory = make_session_factory(engine)
    with transaction(factory) as session:
        roles = sorted(known_roles(session))
    assert {"ADMIN", "CEO", "CFO", "MANAGER", "EMPLOYEE"} <= set(roles)
    granter = _user(engine, "cap-quyen@example.com", "ADMIN")
    record_in: dict[str, Any] = {"full_name": "Nguyễn Văn A", "salary_band": "Bậc 3", "note": f"CCCD {CCCD}"}
    for role in roles:
        user_id = _user(engine, f"{role.lower()}@example.com", role)
        with transaction(factory) as session:
            actor = load_actor(session, user_id)
            assert not can_unmask(actor), role
            assert mask_for(actor, f"CCCD {CCCD}") == f"CCCD {PII_MASK}", role
            assert mask_fields(actor, record_in, sensitive=("salary_band",)) == {
                "full_name": "Nguyễn Văn A",
                "salary_band": PII_MASK,  # trường khai báo nhạy cảm: che cả giá trị dù không khớp quy tắc
                "note": f"CCCD {PII_MASK}",
            }, role
        with pytest.raises(ApiError) as info, transaction(factory) as session:
            create_assignment(
                session, user_id=user_id, permission="pii.unmask", scope_type=ScopeType.COMPANY, scope_id=None,
                granted_by=granter, reason="Thử bỏ che",
            )  # fmt: skip
        assert info.value.code == "ASSIGNMENT_NOT_ELIGIBLE", role  # không role nào đủ điều kiện (CSDL: AE003)


@pytest.mark.db
def test_admin_gets_403_on_hr_reads_and_export(engine: Engine) -> None:
    """TC-PRV-02: ADMIN đọc hồ sơ/lương/xuất dữ liệu nhân sự → `403`; chỉ có `hr.import`."""
    factory = make_session_factory(engine)
    settings = AuthSettings(
        idle=timedelta(minutes=30), absolute=timedelta(hours=8), rate_limit_attempts=200,
        rate_limit_window=timedelta(seconds=60), lockout_threshold=10, lockout_duration=timedelta(minutes=15),
        reauth=timedelta(minutes=5), password_min_length=12,
    )  # fmt: skip
    auth = Authenticator(factory, settings)
    guard = PermissionGuard(factory, auth.require_session)
    router = APIRouter()
    for permission in ("hr.profile.read", "hr.salary.read", "hr.export", "hr.import"):
        router.add_api_route(f"/probe/{permission}", lambda: {"ok": "1"}, methods=["GET"], **guard.route(permission))
    app = create_api(
        {},
        (build_auth_router(auth, KEY), router),
        csrf=CsrfConfig(KEY, frozenset({ORIGIN}), frozenset({"/api/v1/auth/login"})),
    )
    _user(engine, "admin@example.com", "ADMIN")
    client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
    body = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": PASSWORD}).json()
    client.headers[CSRF_HEADER] = body["csrf_token"]
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE identity.session SET mfa_verified = true WHERE token_hash = :h"),
            {"h": hash_token(client.cookies[SESSION_COOKIE])},
        )
    for permission in ("hr.profile.read", "hr.salary.read", "hr.export"):
        response = client.get(f"/api/v1/probe/{permission}")
        assert response.status_code == 403 and response.json()["code"] == "FORBIDDEN", permission
    assert client.get("/api/v1/probe/hr.import").status_code == 200


@pytest.mark.db
def test_audit_changes_are_masked_automatically(engine: Engine) -> None:
    """Plan §18: phát hiện tự động trong `changes` của audit (không cần nơi gọi khai báo `masked_fields`)."""
    with transaction(make_session_factory(engine)) as session:
        event_id = record(
            session,
            AuditEvent(
                category=Category.BUSINESS, actor_type=ActorType.SYSTEM, action="hr.import.row",
                outcome=Outcome.FAILED, changes={"row": {"ghi_chu": f"CCCD {CCCD}", "so_dong": 3}},
            ),
        )  # fmt: skip
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT changes FROM audit.event WHERE id = :i"), {"i": event_id}).scalar_one()
    assert stored == {"row": {"ghi_chu": f"CCCD {PII_MASK}", "so_dong": 3}}
