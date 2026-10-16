"""Hồi quy bảo vệ dữ liệu cá nhân trong log kỹ thuật và audit (Q-55, quyết định CDA 16/10/2026; T-112).

Mọi giá trị là dữ liệu giả, dựng theo định dạng (không phải người thật). Mỗi test kiểm **giá trị gốc không còn
xuất hiện** sau xử lý — không chỉ kiểm có ký hiệu che. Heuristic theo quy tắc không nhận diện được mọi dữ liệu cá
nhân; giới hạn còn lại ghi ở Implementation_Plan §41.
"""

import io
import json
import logging
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from aieos.audit.api import ActorType, AuditEvent, Category, Outcome, audit_row_values, mask_changes, record
from aieos.platform.api import (
    PII_MASK,
    JsonFormatter,
    create_db_engine,
    find_pii,
    make_session_factory,
    mask_pii,
    transaction,
)
from aieos.platform.web import accept_request_id
from tests.conftest import ProvisionedDatabase, migrate_to_head

# Giá trị giả theo định dạng.
CCCD = "079203001234"
CCCD_SPACED = "079 203 001 234"
ACCOUNT = "19034567890123"
MOBILE = "0912 345 678"
LANDLINE = "024 3826 1234"
EMAIL_AT = "nguyen.van.a [at] example [dot] com"
EMAIL = "nguyen.van.a@example.com"  # tên miền dành riêng cho ví dụ (RFC 2606)


def digits(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def leaks(original: str, output: str) -> bool:
    """Giá trị gốc còn trong đầu ra — so cả nguyên văn lẫn dãy chữ số liền (bắt trường hợp chỉ che một phần)."""
    run = digits(original)
    return original in output or (len(run) >= 6 and run in digits(output))


# ---------- 1–6: dạng khó phát hiện ----------


@pytest.mark.parametrize(
    ("text", "secret", "kind"),
    [
        (f"Mã định danh {CCCD_SPACED} ghi trong biên bản", CCCD_SPACED, "NATIONAL_ID"),  # 1
        (f"Mã định danh {CCCD[:6]}-{CCCD[6:]} ghi trong biên bản", CCCD, "NATIONAL_ID"),  # 1, dấu gạch
        (f"Chuyển vào {ACCOUNT} Techcombank giúp mình", ACCOUNT, "BANK_ACCOUNT"),  # 2
        (f"Vietcombank - {ACCOUNT} - Nguyễn Văn A", ACCOUNT, "BANK_ACCOUNT"),  # 2
        (f"TK {ACCOUNT} ACB", ACCOUNT, "BANK_ACCOUNT"),  # 2
        ("Lương: 15 triệu đồng/tháng", "15 triệu", "SALARY"),  # 3
        ("mức lương 15,5 tr", "15,5 tr", "SALARY"),  # 3
        (f"Gọi số bàn {LANDLINE} giờ hành chính", LANDLINE, "PHONE"),  # 4
        ("Gọi +84 28 3822 4567", "+84 28 3822 4567", "PHONE"),  # 4
        (f"Gửi về {EMAIL_AT} nhé", EMAIL_AT, "EMAIL"),  # 5
        ("liên hệ tran.b(at)example.com", "tran.b(at)example.com", "EMAIL"),  # 5
    ],
)
def test_hard_formats_are_masked(text: str, secret: str, kind: str) -> None:
    masked = mask_pii(text)
    assert not leaks(secret, masked), masked
    assert PII_MASK in masked
    assert kind in {m.kind for m in find_pii(text)}


@pytest.mark.parametrize(
    ("text", "secret"),
    [
        (f"CCCD {CCCD[:7]}\n{CCCD[7:]}", CCCD),  # có từ khóa, ngắt dòng giữa số
        (f"Mã {CCCD[:6]}\n{CCCD[6:]} đã cấp", CCCD),  # không từ khóa
        ("Điện thoại 0912 345\n678", "0912345678"),
        (f"STK {ACCOUNT[:7]}\r\n{ACCOUNT[7:]}", ACCOUNT),
    ],
)
def test_values_broken_across_lines_are_fully_masked(text: str, secret: str) -> None:  # 6
    masked = mask_pii(text)
    assert not leaks(secret, masked), masked
    assert not any(len(digits(part)) >= 4 for part in masked.split(PII_MASK)), masked  # không sót phần đuôi


# ---------- 10: không che nhầm, không hỏng dữ liệu thường ----------


@pytest.mark.parametrize(
    "text",
    [
        "Doanh thu quý 3 đạt 1.500.000.000 đồng, tăng 12%",
        "Chi 1500000000 đồng cho dự án",  # số tiền liền có đơn vị
        "Task 6f1c2a3b-0000-4000-8000-012345678901 đã xong",
        "Kỳ 2026-10, hạn 15/10/2026 10:00",
        "Hợp đồng số 2026/HĐ-01, mã đơn 012345",
        "Thưởng lương 13 tháng theo quy chế",
        "Số seri thiết bị 0791234567891234",
        "Tải tệp 25 MB, 300 trang",
        "Lưu lượng 1048576 byte",
        'File "/app/src/aieos/jobs/worker.py", line 123, in _execute',
    ],
)
def test_ordinary_text_is_untouched(text: str) -> None:  # 10
    assert find_pii(text) == []
    assert mask_pii(text) == text


# ---------- 8–9: log kỹ thuật ----------


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("aieos.test.pii")
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    yield stream
    logger.removeHandler(handler)


def line(stream: io.StringIO) -> dict[str, Any]:
    return dict(json.loads(stream.getvalue().strip().splitlines()[-1]))


def test_log_message_and_nested_extra_are_masked(log_stream: io.StringIO) -> None:  # 8
    log = logging.getLogger("aieos.test.pii")
    log.warning(
        "ai_provider_failed khi xử lý CCCD %s",
        CCCD,
        extra={
            "provider": "LOCAL",
            "attempt": 2,
            "detail": {"rows": [{"ghi_chu": f"STK {ACCOUNT}"}, f"email {EMAIL_AT}"], "count": 3},
        },
    )
    record = line(log_stream)
    raw = log_stream.getvalue()
    for secret in (CCCD, ACCOUNT, EMAIL_AT):
        assert not leaks(secret, raw), secret
    assert record["provider"] == "LOCAL" and record["attempt"] == 2 and record["detail"]["count"] == 3  # cấu trúc giữ


def test_exception_traceback_is_masked_but_still_diagnosable(log_stream: io.StringIO) -> None:  # 8
    log = logging.getLogger("aieos.test.pii")

    def handler() -> None:
        raise ValueError(f"không ghi được dòng: CCCD {CCCD}, ĐT {MOBILE}")

    try:
        handler()
    except ValueError:
        log.exception("Job lỗi", extra={"job_id": "j-1"})
    record = line(log_stream)
    assert not leaks(CCCD, log_stream.getvalue()) and not leaks(MOBILE, log_stream.getvalue())
    assert record["exc_type"] == "ValueError"
    assert "Traceback (most recent call last)" in record["exc"]
    assert "in handler" in record["exc"] and "raise ValueError" in record["exc"]  # vẫn chẩn đoán được
    assert record["job_id"] == "j-1"


def test_retry_fallback_warning_with_provider_error_is_masked(log_stream: io.StringIO) -> None:  # 8
    from aieos.providers.api import ProviderError

    log = logging.getLogger("aieos.test.pii")
    error = ProviderError(f"upstream 500: echo 'Lương 15.000.000, STK {ACCOUNT}'")
    for attempt in (1, 2):
        log.warning("ai_provider_failed", extra={"provider": "BACKUP", "attempt": attempt, "error": str(error)})
    assert not leaks(ACCOUNT, log_stream.getvalue())
    assert "15.000.000" not in log_stream.getvalue()


def test_key_based_redaction_still_applies(log_stream: io.StringIO) -> None:
    logging.getLogger("aieos.test.pii").info("dang_nhap", extra={"password": "mat-khau-gia", "user": "u-1"})
    record = line(log_stream)
    assert record["password"] == "***" and record["user"] == "u-1"


# ---------- 7, 9: audit ----------


def event(**overrides: Any) -> AuditEvent:
    base: dict[str, Any] = {
        "category": Category.ADMIN,
        "actor_type": ActorType.USER,
        "action": "user.lock",
        "outcome": Outcome.SUCCESS,
        "resource_type": "identity.user_account",
        "resource_id": "6f1c2a3b-0000-4000-8000-012345678901",
    }
    return AuditEvent(**{**base, **overrides})


def test_audit_reason_and_free_text_fields_are_masked() -> None:  # 7
    values = audit_row_values(
        event(
            reason=f"Khóa theo yêu cầu, liên hệ {MOBILE}, CCCD {CCCD_SPACED}",
            user_agent=f"Mozilla/5.0 contact {EMAIL_AT}",
            resource_id=f"tài khoản {ACCOUNT} Techcombank",
            changes={"before": {"note": f"STK {ACCOUNT}"}, "list": [f"ĐT {LANDLINE}"]},
        )
    )
    dumped = json.dumps(values, ensure_ascii=False, default=str)
    for secret in (MOBILE, CCCD_SPACED, EMAIL_AT, ACCOUNT, LANDLINE):
        assert not leaks(secret, dumped), secret
    assert values["reason"].startswith("Khóa theo yêu cầu, liên hệ ")  # phần không nhạy cảm giữ nguyên


def test_audit_traceability_fields_are_unchanged() -> None:  # 7, 10
    target = str(uuid.uuid4())
    values = audit_row_values(event(resource_id=target, reason="RATE_LIMITED", correlation_id="req-12345678"))
    assert values["resource_id"] == target
    assert values["reason"] == "RATE_LIMITED"
    assert values["action"] == "user.lock" and values["resource_type"] == "identity.user_account"
    assert values["correlation_id"] == "req-12345678"


@pytest.fixture
def engine(database: ProvisionedDatabase) -> Iterator[Engine]:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    yield engine
    engine.dispose()


@pytest.mark.db
def test_audit_row_in_database_has_no_original_values(engine: Engine) -> None:  # 7, 9
    with transaction(make_session_factory(engine)) as session:
        event_id = record(session, event(reason=f"Theo đơn, CCCD {CCCD}", user_agent=f"bot {EMAIL_AT}"))
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT reason, user_agent, resource_id, changes::text FROM audit.event WHERE id = :i"),
            {"i": event_id},
        ).one()
    stored = " ".join(str(v) for v in row)
    assert not leaks(CCCD, stored) and not leaks(EMAIL_AT, stored)


@pytest.mark.db
def test_database_error_logged_without_original_values(engine: Engine, log_stream: io.StringIO) -> None:  # 8, 9
    """Lỗi CSDL: SQLAlchemy không kèm tham số (`hide_parameters`). PostgreSQL vẫn đưa giá trị dòng vào DETAIL của lỗi
    ("Failing row contains …") — ứng dụng không xóa được trong đối tượng exception, nên kênh lộ ra ngoài là log:
    traceback ghi qua `JsonFormatter` phải không còn giá trị gốc."""
    with pytest.raises(Exception) as info, engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO audit.event (category, actor_type, action, outcome, reason) VALUES ('X', :a, :b, :c, :r)"
            ),
            {"a": "USER", "b": "x", "c": "SUCCESS", "r": f"CCCD {CCCD}, STK {ACCOUNT}"},
        )
    assert "SQL parameters hidden" in str(info.value)
    try:
        raise info.value
    except Exception:
        logging.getLogger("aieos.test.pii").exception("request_failed", extra={"path": "/api/v1/x"})
    record = line(log_stream)
    assert not leaks(CCCD, log_stream.getvalue()) and not leaks(ACCOUNT, log_stream.getvalue())
    assert "INSERT INTO audit.event" in record["exc"]  # câu SQL vẫn còn để chẩn đoán


# ---------- Lỗ hổng tìm thấy khi review PR #41 ----------


def test_log_dict_keys_are_masked(log_stream: io.StringIO) -> None:  # 8: khóa dict cũng là dữ liệu
    logging.getLogger("aieos.test.pii").warning("dem", extra={"jobs": {EMAIL: 1, CCCD: 2, "j-1": 3}})
    raw = log_stream.getvalue()
    assert not leaks(EMAIL, raw) and not leaks(CCCD, raw)
    assert line(log_stream)["jobs"]["j-1"] == 3


def test_audit_changes_keys_are_masked() -> None:  # 7
    stored = json.dumps(mask_changes({"theo_email": {EMAIL: "đã mời"}, CCCD: "x"}), ensure_ascii=False)
    assert not leaks(EMAIL, stored) and not leaks(CCCD, stored)
    assert "theo_email" in stored and "đã mời" in stored


@pytest.mark.parametrize("incoming", ["0912345678", "nv-0912345678-x"])
def test_request_id_that_looks_like_pii_is_replaced(incoming: str) -> None:  # 8: correlation_id không bị che
    replaced = accept_request_id(incoming)
    assert replaced != incoming and len(replaced) == 32
    assert accept_request_id("req-abcdef12") == "req-abcdef12"  # ID thường vẫn giữ để tương quan


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_uvicorn_logs_go_through_masking_and_no_raw_access_log(tmp_path: Path) -> None:  # 8: kênh log thật của server
    """Chạy uvicorn thật như `infra/compose.yaml`: uvicorn tự gắn handler văn bản trước khi gọi factory; access log của
    nó ghi cả query string. Sau `configure_logging`, mọi dòng phải là JSON đã che và không có dòng access log thô."""
    (tmp_path / "probe_app.py").write_text(
        "from aieos.platform.api import CsrfConfig, Secret, configure_logging, create_api\n"
        "def make():\n"
        "    configure_logging()\n"
        "    return create_api({}, (), csrf=CsrfConfig(Secret('k'), frozenset({'https://x'}), frozenset()))\n",
        encoding="utf-8",
    )
    port = _free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "--factory",
            "probe_app:make",
            "--app-dir",
            str(tmp_path),
            "--port",
            str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        url = f"http://127.0.0.1:{port}/api/v1/health/live?sdt={MOBILE.replace(' ', '')}&email={EMAIL}"
        deadline = time.monotonic() + 20
        while True:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    assert response.status == 200
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
    finally:
        server.terminate()
        output, _ = server.communicate(timeout=20)
    lines = [text_line for text_line in output.splitlines() if text_line.strip()]
    assert lines, output
    assert not leaks(MOBILE, output) and EMAIL not in output, output
    assert all(text_line.startswith("{") for text_line in lines), output  # không còn dòng văn bản thô của uvicorn
    assert any(json.loads(text_line).get("message") == "request" for text_line in lines)  # log request vẫn còn
