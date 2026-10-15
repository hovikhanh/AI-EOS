"""Interface công khai của `providers` (ADR-011, Architecture §3 quy tắc 1 và 6)."""

from collections.abc import Callable, Mapping
from typing import Any

from aieos.platform.api import Secret, Settings
from aieos.providers.base import (
    AIUnavailable,
    CallRecord,
    CallRecorder,
    Classification,
    ConvertedDocument,
    DocumentConverter,
    LLMAdapter,
    LLMRequest,
    LLMResult,
    Message,
    OCRAdapter,
    OCRBlock,
    OCRRequest,
    OCRResult,
    ProviderError,
    ProviderTimeout,
)
from aieos.providers.client import ProviderClient, eligible
from aieos.providers.config import (
    BUDGET_LIMIT,
    LLM_PROVIDERS,
    OCR_PROVIDERS,
    ProviderConfigError,
    ProviderSpec,
    api_keys,
    parse_budget,
    parse_specs,
)
from aieos.providers.fake import FakeConverter, FakeLLM, FakeOCR

__all__ = [
    "ADAPTERS",
    "AIUnavailable",
    "AdapterFactory",
    "CallRecord",
    "CallRecorder",
    "Classification",
    "ConvertedDocument",
    "DocumentConverter",
    "FakeConverter",
    "FakeLLM",
    "FakeOCR",
    "LLMAdapter",
    "LLMRequest",
    "LLMResult",
    "Message",
    "OCRAdapter",
    "OCRBlock",
    "OCRRequest",
    "OCRResult",
    "ProviderClient",
    "ProviderConfigError",
    "ProviderError",
    "ProviderSpec",
    "ProviderTimeout",
    "client_from_settings",
    "eligible",
]

AdapterFactory = Callable[[ProviderSpec, Secret | None], Any]

# Adapter thật (API tương thích OpenAI cho LLM, OCR sau benchmark) đăng ký ở T-205; T-204 chưa có adapter nào.
ADAPTERS: Mapping[str, AdapterFactory] = {}


def client_from_settings(
    settings: Settings, *, recorder: CallRecorder, adapters: Mapping[str, AdapterFactory] = ADAPTERS
) -> ProviderClient:
    """Dựng client từ cấu hình; cấu hình sai → `ProviderConfigError` (tiến trình không khởi động)."""
    llm_specs = parse_specs(LLM_PROVIDERS, settings.optional_config(LLM_PROVIDERS))
    ocr_specs = parse_specs(OCR_PROVIDERS, settings.optional_config(OCR_PROVIDERS))
    keys = api_keys(settings, llm_specs + ocr_specs)

    def build(specs: list[ProviderSpec]) -> list[tuple[ProviderSpec, Any]]:
        built = []
        for spec in specs:
            factory = adapters.get(spec.adapter)
            if factory is None:
                raise ProviderConfigError(f"provider {spec.name}: adapter `{spec.adapter}` chưa được hỗ trợ")
            built.append((spec, factory(spec, keys.get(spec.name))))
        return built

    return ProviderClient(
        llm=build(llm_specs),
        ocr=build(ocr_specs),
        recorder=recorder,
        budget_limit=parse_budget(settings.optional_config(BUDGET_LIMIT)),
    )
