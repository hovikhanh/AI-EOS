"""Cấu hình provider (T-204, Implementation_Plan §7): `AIEOS_LLM_PROVIDERS`, `AIEOS_OCR_PROVIDERS` (JSON),
`AIEOS_LLM_API_KEY_<NAME>` (secret), `AIEOS_AI_BUDGET_LIMIT` (GAP-14 → D-51: giá trị là cấu hình).

- Danh sách theo thứ tự ưu tiên: phần tử đầu là provider chính, các phần tử sau là dự phòng (fallback).
- Timeout, số lần thử lại, backoff là trường bắt buộc, không có mặc định (giống D-57 cho giới hạn tốc độ).
- Provider không `local` không được nhận `PERSONAL`/`SENSITIVE` (ADR-011, SRS-PRV-02). Ngoại lệ demo D-50 chưa hiện
  thực — chờ Q-53 và các điểm D-50 còn mở (T-205).
- Biến không đặt → không có provider: bước AI trả `AI_UNAVAILABLE`, luồng thủ công vẫn chạy (SRS-NFR-07).
"""

import json
from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from aieos.platform.api import Secret, Settings
from aieos.providers.base import LOCAL_ONLY, Classification

LLM_PROVIDERS = "AIEOS_LLM_PROVIDERS"
OCR_PROVIDERS = "AIEOS_OCR_PROVIDERS"
BUDGET_LIMIT = "AIEOS_AI_BUDGET_LIMIT"

Price = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=8)]


class ProviderConfigError(Exception):
    """Cấu hình provider sai; thông điệp chỉ nêu tên biến/provider/trường, không chứa giá trị secret."""


class ProviderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,39}$")]  # hậu tố của AIEOS_LLM_API_KEY_<NAME>
    adapter: Annotated[str, Field(min_length=1)]
    url: str | None = None
    model: str | None = None
    local: bool
    classifications: Annotated[frozenset[Classification], Field(min_length=1)]
    timeout_seconds: Annotated[float, Field(gt=0)]
    max_retries: Annotated[int, Field(ge=0, le=10)]
    backoff_seconds: Annotated[float, Field(ge=0)]
    api_key: bool = False
    price_per_1k_tokens_in: Price | None = None
    price_per_1k_tokens_out: Price | None = None
    price_per_page: Price | None = None

    @model_validator(mode="after")
    def _local_only(self) -> "ProviderSpec":
        if not self.local and self.classifications & LOCAL_ONLY:
            raise ValueError("provider không local không được nhận PERSONAL/SENSITIVE (ADR-011)")
        return self

    def cost(self, *, tokens_in: int | None, tokens_out: int | None, pages: int | None) -> Decimal | None:
        """Chi phí ước tính theo đơn giá cấu hình; thiếu đơn giá → `None` (không đoán)."""
        parts: list[Decimal] = []
        for price, amount, per in (
            (self.price_per_1k_tokens_in, tokens_in, 1000),
            (self.price_per_1k_tokens_out, tokens_out, 1000),
            (self.price_per_page, pages, 1),
        ):
            if price is not None and amount is not None:
                parts.append(price * amount / per)
        return sum(parts, Decimal(0)) if parts else None


def parse_specs(variable: str, raw: str | None) -> list[ProviderSpec]:
    if raw is None:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        raise ProviderConfigError(f"{variable}: không phải JSON") from None
    if not isinstance(items, list):
        raise ProviderConfigError(f"{variable}: phải là mảng provider")
    specs: list[ProviderSpec] = []
    for index, item in enumerate(items):
        try:
            specs.append(ProviderSpec.model_validate(item))
        except ValidationError as error:
            fields = sorted({".".join(str(p) for p in e["loc"]) or "provider" for e in error.errors()})
            raise ProviderConfigError(f"{variable}[{index}]: sai trường {', '.join(fields)}") from None
    names = [s.name for s in specs]
    if len(set(names)) != len(names):
        raise ProviderConfigError(f"{variable}: tên provider trùng")
    return specs


def parse_budget(raw: str | None) -> Decimal | None:
    """Trần chi phí (cùng đơn vị với đơn giá provider); không đặt → không giới hạn (`[CẦN XÁC NHẬN]` GAP-14)."""
    if raw is None:
        return None
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ProviderConfigError(f"{BUDGET_LIMIT}: không phải số") from None
    if not value.is_finite() or value <= 0:
        raise ProviderConfigError(f"{BUDGET_LIMIT}: phải là số dương")
    return value


def api_keys(settings: Settings, specs: list[ProviderSpec]) -> dict[str, Secret]:
    """Khóa API cho provider có `api_key: true`; thiếu → lỗi cấu hình (chỉ nêu tên biến)."""
    keys: dict[str, Secret] = {}
    for spec in specs:
        if not spec.api_key:
            continue
        key = settings.provider_key(spec.name)
        if key is None:
            raise ProviderConfigError(f"thiếu secret AIEOS_LLM_API_KEY_{spec.name}")
        keys[spec.name] = key
    return keys
