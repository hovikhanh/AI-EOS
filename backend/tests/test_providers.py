"""T-204: provider adapter — định tuyến theo phân loại, timeout/retry/fallback, call log, trần chi phí, cấu hình
(SRS-PRV-01…04, SRS-NFR-07; ADR-011). Chỉ dùng adapter giả lập (CI không gọi provider thật).

TC do T-204 làm chủ: TC-PRV-04 (phần định tuyến; che PII: T-112) `test_sensitive_goes_only_to_local_and_is_logged`,
TC-PRV-05 `test_timeout_retries_then_falls_back_then_unavailable`,
TC-PRV-06 `test_budget_warns_at_80_and_blocks_at_100`,
TC-PRV-07 (phần cấu hình; adapter thật: T-205) `test_switch_provider_by_configuration_only`, TC-NFR-04 (phần khởi
động không provider; nhập tay tài chính/review: khi có T-403, T-208) `test_app_runs_without_any_provider`.
"""

import io
import json
import logging
from collections.abc import Iterator
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from aieos.ai.api import DbCallRecorder
from aieos.app.asgi import create_app
from aieos.platform.api import (
    JsonFormatter,
    Process,
    Secret,
    create_db_engine,
    load_settings,
    make_session_factory,
)
from aieos.providers.api import (
    AIUnavailable,
    CallRecord,
    Classification,
    FakeLLM,
    FakeOCR,
    LLMRequest,
    LLMResult,
    Message,
    OCRRequest,
    OCRResult,
    ProviderClient,
    ProviderConfigError,
    ProviderError,
    ProviderSpec,
    ProviderTimeout,
    client_from_settings,
)
from tests.conftest import ProvisionedDatabase, migrate_to_head
from tests.test_platform_config import full_env
from tests.test_platform_web import api_env, restore_logging  # noqa: F401 — fixture

REQUEST = LLMRequest([Message("user", "Tóm tắt biên bản")])
OK = LLMResult("tóm tắt", tokens_in=1000, tokens_out=500, model="m")


def spec(name: str, *, local: bool, classes: str = "NORMAL", **extra: Any) -> ProviderSpec:
    data: dict[str, Any] = {
        "name": name,
        "adapter": "fake",
        "local": local,
        "classifications": classes.split(","),
        "timeout_seconds": 5,
        "max_retries": 0,
        "backoff_seconds": 0,
        **extra,
    }
    return ProviderSpec.model_validate(data)


class MemoryRecorder:
    def __init__(self, spent: str = "0") -> None:
        self.calls: list[CallRecord] = []
        self._spent = Decimal(spent)

    def record(self, call: CallRecord) -> None:
        self.calls.append(call)

    def spent(self) -> Decimal:
        return self._spent


@pytest.fixture
def log_stream() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("aieos.providers")
    logger.addHandler(handler)
    yield stream
    logger.removeHandler(handler)


# ---------- TC-PRV-04: định tuyến theo phân loại ----------


def test_config_rejects_cloud_provider_for_personal_data() -> None:
    """ADR-011: provider không local không được khai báo nhận PERSONAL/SENSITIVE (ngoại lệ demo D-50: chờ Q-53)."""
    for classes in ("PERSONAL", "SENSITIVE", "NORMAL,SENSITIVE"):
        with pytest.raises(ValueError, match="không local"):
            spec("CLOUD", local=False, classes=classes)
    spec("LOCAL", local=True, classes="NORMAL,PERSONAL,SENSITIVE")


def test_no_local_provider_skips_ai_step() -> None:
    """SRS-PRV-02: dữ liệu nhạy cảm mà không có provider local phù hợp → bỏ bước AI, không gọi provider nào."""
    cloud = FakeLLM([OK])
    local_normal_only = FakeLLM([OK])
    recorder = MemoryRecorder()
    client = ProviderClient(
        llm=[(spec("CLOUD", local=False), cloud), (spec("LOCAL", local=True), local_normal_only)], recorder=recorder
    )
    for classification in (Classification.PERSONAL, Classification.SENSITIVE):
        with pytest.raises(AIUnavailable) as info:
            client.complete(REQUEST, purpose="extract", classification=classification)
        assert info.value.reason == "NO_PROVIDER"
    assert cloud.calls == [] and local_normal_only.calls == [] and recorder.calls == []


def test_router_refuses_cloud_even_if_config_check_bypassed() -> None:
    """Phòng thủ hai lớp: spec không qua validate (dựng tay) vẫn không nhận dữ liệu cá nhân ở provider cloud."""
    rogue = ProviderSpec.model_construct(**{**spec("CLOUD", local=False).model_dump(), "classifications": frozenset(
        Classification)})  # fmt: skip
    cloud = FakeLLM([OK])
    client = ProviderClient(llm=[(rogue, cloud)], recorder=MemoryRecorder())
    with pytest.raises(AIUnavailable):
        client.complete(REQUEST, purpose="extract", classification=Classification.SENSITIVE)
    assert cloud.calls == []


@pytest.mark.db
def test_sensitive_goes_only_to_local_and_is_logged(database: ProvisionedDatabase) -> None:
    """TC-PRV-04: có provider local → dữ liệu SENSITIVE chỉ tới local; `call_log.provider_is_local = true`."""
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    try:
        cloud, local = FakeLLM([OK]), FakeLLM([OK])
        client = ProviderClient(
            llm=[
                (spec("CLOUD", local=False), cloud),
                (spec("LOCAL", local=True, classes="NORMAL,PERSONAL,SENSITIVE"), local),
            ],
            recorder=DbCallRecorder(make_session_factory(engine)),
        )
        assert client.complete(REQUEST, purpose="extract", classification=Classification.SENSITIVE) == OK
        assert cloud.calls == [] and len(local.calls) == 1
        client.complete(REQUEST, purpose="chat", classification=Classification.NORMAL)
        assert len(cloud.calls) == 1  # dữ liệu thường: provider chính (cloud) trước
        with engine.begin() as conn:
            rows = conn.execute(
                text("SELECT provider, data_classification, provider_is_local, outcome FROM ai.call_log ORDER BY id")
            ).all()
        assert [tuple(r) for r in rows] == [
            ("LOCAL", "SENSITIVE", True, "SUCCESS"),
            ("CLOUD", "NORMAL", False, "SUCCESS"),
        ]
    finally:
        engine.dispose()


# ---------- TC-PRV-05: timeout, retry, fallback ----------


def test_timeout_retries_then_falls_back_then_unavailable(log_stream: io.StringIO) -> None:
    sleeps: list[float] = []
    primary = FakeLLM([ProviderTimeout("hết giờ")])
    backup = FakeLLM([ProviderError("lỗi"), OK])
    recorder = MemoryRecorder()
    client = ProviderClient(
        llm=[
            (spec("PRIMARY", local=True, max_retries=2, backoff_seconds=0.5, timeout_seconds=3), primary),
            (spec("BACKUP", local=True, max_retries=1, backoff_seconds=1), backup),
        ],
        recorder=recorder,
        sleep=sleeps.append,
    )
    assert client.complete(REQUEST, purpose="chat", classification=Classification.NORMAL) == OK
    assert primary.calls == [3, 3, 3]  # 1 lần + 2 lần thử lại, mỗi lần mang timeout cấu hình
    assert len(backup.calls) == 2
    assert sleeps == [0.5, 1.0, 1]  # backoff lũy thừa trong một provider
    assert [(c.provider, c.outcome) for c in recorder.calls] == [
        ("PRIMARY", "TIMEOUT"),
        ("PRIMARY", "TIMEOUT"),
        ("PRIMARY", "TIMEOUT"),
        ("BACKUP", "ERROR"),
        ("BACKUP", "SUCCESS"),
    ]
    assert recorder.calls[-1].tokens_in == 1000

    exhausted = ProviderClient(
        llm=[(spec("ONLY", local=True, max_retries=1), FakeLLM([ProviderTimeout("x")]))],
        recorder=MemoryRecorder(),
        sleep=lambda s: None,
    )
    with pytest.raises(AIUnavailable) as info:
        exhausted.complete(REQUEST, purpose="chat", classification=Classification.NORMAL)
    assert info.value.reason == "EXHAUSTED"
    assert "Tóm tắt" not in log_stream.getvalue()  # không ghi nội dung lời gọi


def test_fallback_keeps_classification_level() -> None:
    """Fallback chỉ sang provider cùng mức phân loại: provider local lỗi không rơi sang cloud với dữ liệu cá nhân."""
    cloud = FakeLLM([OK])
    client = ProviderClient(
        llm=[
            (spec("LOCAL", local=True, classes="NORMAL,PERSONAL"), FakeLLM([ProviderTimeout("x")])),
            (spec("CLOUD", local=False), cloud),
        ],
        recorder=MemoryRecorder(),
    )
    with pytest.raises(AIUnavailable):
        client.complete(REQUEST, purpose="extract", classification=Classification.PERSONAL)
    assert cloud.calls == []


def test_ocr_records_pages_and_cost() -> None:
    recorder = MemoryRecorder()
    client = ProviderClient(
        ocr=[(spec("OCR", local=True, price_per_page="0.01"), FakeOCR([OCRResult(pages=3)]))], recorder=recorder
    )
    client.recognize(OCRRequest(b"%PDF", "application/pdf"), purpose="ocr", classification=Classification.NORMAL)
    [call] = recorder.calls
    assert (call.pages, call.cost_estimate) == (3, Decimal("0.03"))


# ---------- TC-PRV-06: trần chi phí ----------


def test_budget_warns_at_80_and_blocks_at_100(log_stream: io.StringIO) -> None:
    def client(spent: str) -> tuple[ProviderClient, FakeLLM]:
        adapter = FakeLLM([OK])
        return ProviderClient(
            llm=[(spec("P", local=True), adapter)], recorder=MemoryRecorder(spent), budget_limit=Decimal("100")
        ), adapter

    below, _ = client("79.99")
    below.complete(REQUEST, purpose="chat", classification=Classification.NORMAL)
    assert "ai_budget" not in log_stream.getvalue()

    warn, adapter = client("80")
    warn.complete(REQUEST, purpose="chat", classification=Classification.NORMAL)
    assert len(adapter.calls) == 1 and "ai_budget_threshold" in log_stream.getvalue()

    over, adapter = client("100")
    with pytest.raises(AIUnavailable) as info:
        over.complete(REQUEST, purpose="chat", classification=Classification.NORMAL)
    assert info.value.reason == "BUDGET" and adapter.calls == []
    assert "ai_budget_exceeded" in log_stream.getvalue()
    over.complete(REQUEST, purpose="extract", classification=Classification.NORMAL, essential=True)
    assert len(adapter.calls) == 1  # lời gọi thiết yếu không bị chặn


def test_cost_estimate_from_configured_prices() -> None:
    priced = spec("P", local=True, price_per_1k_tokens_in="0.2", price_per_1k_tokens_out="0.6")
    assert priced.cost(tokens_in=1000, tokens_out=500, pages=None) == Decimal("0.5")
    assert spec("Q", local=True).cost(tokens_in=1000, tokens_out=500, pages=None) is None  # không đoán đơn giá


@pytest.mark.db
def test_spent_sums_current_month_only(database: ProvisionedDatabase) -> None:
    migrate_to_head(database)
    engine = create_db_engine(database.secret("aieos_app"))
    try:
        recorder = DbCallRecorder(make_session_factory(engine))
        assert recorder.spent() == 0
        for cost in ("1.5", "2.25", None):
            recorder.record(
                CallRecord(
                    provider="P", model=None, purpose="chat", data_classification=Classification.NORMAL,
                    provider_is_local=True, outcome="SUCCESS", latency_ms=1,
                    cost_estimate=Decimal(cost) if cost else None,
                )
            )  # fmt: skip
        _old_call(engine)
        assert recorder.spent() == Decimal("3.75")
    finally:
        engine.dispose()


def _old_call(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO ai.call_log (provider, purpose, data_classification, provider_is_local, outcome, "
                "cost_estimate, created_at) VALUES ('P', 'chat', 'NORMAL', true, 'SUCCESS', 99, now() - :d)"
            ),
            {"d": timedelta(days=40)},
        )


# ---------- TC-PRV-07: đổi provider bằng cấu hình ----------


def summarize(client: ProviderClient) -> str:
    """Logic nghiệp vụ mẫu: chỉ phụ thuộc interface, không biết provider nào."""
    return client.complete(REQUEST, purpose="chat", classification=Classification.NORMAL).text


def _settings(**env: str) -> Any:
    return load_settings(Process.WORKER, {**full_env(Process.WORKER), **env})


PROVIDER = {
    "name": "MAIN",
    "local": True,
    "classifications": ["NORMAL"],
    "timeout_seconds": 10,
    "max_retries": 1,
    "backoff_seconds": 1,
}


def test_switch_provider_by_configuration_only() -> None:
    adapters = {
        "fake_a": lambda spec, key: FakeLLM([LLMResult("từ A")]),
        "fake_b": lambda spec, key: FakeLLM([LLMResult("từ B")]),
    }
    for adapter, expected in (("fake_a", "từ A"), ("fake_b", "từ B")):
        settings = _settings(AIEOS_LLM_PROVIDERS=json.dumps([{**PROVIDER, "adapter": adapter}]))
        client = client_from_settings(settings, recorder=MemoryRecorder(), adapters=adapters)
        assert summarize(client) == expected


def test_api_key_is_read_from_secret_and_required_when_declared() -> None:
    seen: list[Secret | None] = []

    def factory(spec: ProviderSpec, key: Secret | None) -> FakeLLM:
        seen.append(key)
        return FakeLLM([OK])

    providers = json.dumps([{**PROVIDER, "adapter": "x", "api_key": True}])
    client_from_settings(
        _settings(AIEOS_LLM_PROVIDERS=providers, AIEOS_LLM_API_KEY_MAIN="khoa-bi-mat"),
        recorder=MemoryRecorder(),
        adapters={"x": factory},
    )
    assert seen[0] is not None and seen[0].reveal() == "khoa-bi-mat"
    with pytest.raises(ProviderConfigError, match="AIEOS_LLM_API_KEY_MAIN"):
        client_from_settings(
            _settings(AIEOS_LLM_PROVIDERS=providers), recorder=MemoryRecorder(), adapters={"x": factory}
        )


@pytest.mark.parametrize(
    ("env", "fragment"),
    [
        ({"AIEOS_LLM_PROVIDERS": "{không phải json"}, "không phải JSON"),
        ({"AIEOS_LLM_PROVIDERS": json.dumps({"name": "A"})}, "mảng"),
        ({"AIEOS_LLM_PROVIDERS": json.dumps([{**PROVIDER, "adapter": "x", "timeout_seconds": None}])}, "timeout"),
        ({"AIEOS_LLM_PROVIDERS": json.dumps([{**PROVIDER, "adapter": "x", "max_retries": 1}] * 2)}, "trùng"),
        ({"AIEOS_LLM_PROVIDERS": json.dumps([{**PROVIDER, "adapter": "x", "secret": "khoa-lo"}])}, "secret"),
        ({"AIEOS_OCR_PROVIDERS": json.dumps([{**PROVIDER, "adapter": "chua-co"}])}, "chưa được hỗ trợ"),
        ({"AIEOS_AI_BUDGET_LIMIT": "0"}, "số dương"),
        ({"AIEOS_AI_BUDGET_LIMIT": "nhieu"}, "không phải số"),
    ],
)
def test_invalid_configuration_is_rejected_without_values(env: dict[str, str], fragment: str) -> None:
    with pytest.raises(ProviderConfigError) as info:
        client_from_settings(_settings(**env), recorder=MemoryRecorder(), adapters={"x": lambda s, k: FakeLLM([OK])})
    assert fragment in str(info.value)
    assert "khoa-lo" not in str(info.value)


# ---------- TC-NFR-04: không provider ----------


def test_no_configuration_means_no_provider() -> None:
    client = client_from_settings(_settings(), recorder=MemoryRecorder())
    assert not client.configured
    with pytest.raises(AIUnavailable) as info:
        summarize(client)
    assert info.value.reason == "NO_PROVIDER"


def test_app_exits_on_invalid_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    restore_logging: None,  # noqa: F811
) -> None:
    api_env(monkeypatch, tmp_path, "postgresql://aieos_app:x@127.0.0.1:1/aieos")
    monkeypatch.setenv("AIEOS_LLM_PROVIDERS", json.dumps([{**PROVIDER, "adapter": "chua-co"}]))
    with pytest.raises(SystemExit) as info:
        create_app()
    assert info.value.code == 2


@pytest.mark.db
def test_app_runs_without_any_provider(
    database: ProvisionedDatabase,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    restore_logging: None,  # noqa: F811
) -> None:
    """TC-NFR-04 (phần T-204): tắt mọi provider → ứng dụng khởi động, sẵn sàng; bước AI báo `NO_PROVIDER`."""
    migrate_to_head(database)
    api_env(monkeypatch, tmp_path, database.urls["aieos_app"].render_as_string(hide_password=False))
    for name in ("AIEOS_LLM_PROVIDERS", "AIEOS_OCR_PROVIDERS", "AIEOS_AI_BUDGET_LIMIT"):
        monkeypatch.delenv(name, raising=False)
    app = create_app()
    assert TestClient(app).get("/api/v1/health/ready").status_code == 200
    assert not app.state.providers.configured
