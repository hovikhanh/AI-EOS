"""Gọi provider qua adapter (ADR-011, SRS-PRV-01…04): định tuyến theo phân loại dữ liệu, timeout, thử lại có giới hạn
với backoff, fallback cùng mức phân loại, ghi call log, trần chi phí.

Không ghi nội dung lời gọi/kết quả vào log (CLAUDE.md §6). Đầu ra là dữ liệu không tin cậy (BR-06).
"""

import logging
import time
import uuid
from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import TypeVar

from aieos.platform.api import CORRELATION_ID
from aieos.providers.base import (
    LOCAL_ONLY,
    AIUnavailable,
    CallRecord,
    CallRecorder,
    Classification,
    LLMAdapter,
    LLMRequest,
    LLMResult,
    OCRAdapter,
    OCRRequest,
    OCRResult,
    Outcome,
    ProviderError,
    ProviderTimeout,
)
from aieos.providers.config import ProviderSpec

logger = logging.getLogger(__name__)

WARN_RATIO = Decimal("0.8")  # SRS-PRV-04: cảnh báo ở 80% trần

A = TypeVar("A")
R = TypeVar("R")


def eligible(spec: ProviderSpec, classification: Classification) -> bool:
    """Provider nhận được phân loại này: có trong danh sách cho phép và, với dữ liệu cá nhân/nhạy cảm, là local."""
    return classification in spec.classifications and (spec.local or classification not in LOCAL_ONLY)


class ProviderClient:
    def __init__(
        self,
        *,
        llm: Sequence[tuple[ProviderSpec, LLMAdapter]] = (),
        ocr: Sequence[tuple[ProviderSpec, OCRAdapter]] = (),
        recorder: CallRecorder,
        budget_limit: Decimal | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._llm = list(llm)
        self._ocr = list(ocr)
        self._recorder = recorder
        self._budget = budget_limit
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self._llm or self._ocr)

    def complete(
        self,
        request: LLMRequest,
        *,
        purpose: str,
        classification: Classification,
        essential: bool = False,
        job_id: uuid.UUID | None = None,
    ) -> LLMResult:
        def usage(result: LLMResult) -> tuple[int | None, int | None, int | None, str | None]:
            return result.tokens_in, result.tokens_out, None, result.model

        return self._run(
            self._llm, lambda a, t: a.complete(request, timeout=t), usage, purpose, classification, essential, job_id
        )

    def recognize(
        self,
        request: OCRRequest,
        *,
        purpose: str,
        classification: Classification,
        essential: bool = False,
        job_id: uuid.UUID | None = None,
    ) -> OCRResult:
        def usage(result: OCRResult) -> tuple[int | None, int | None, int | None, str | None]:
            return None, None, result.pages, result.model

        return self._run(
            self._ocr, lambda a, t: a.recognize(request, timeout=t), usage, purpose, classification, essential, job_id
        )

    def _check_budget(self, essential: bool) -> None:
        if self._budget is None:
            return
        spent = self._recorder.spent()
        if spent >= self._budget and not essential:
            logger.warning("ai_budget_exceeded", extra={"budget_ratio": str(spent / self._budget)})
            raise AIUnavailable("BUDGET")
        if spent >= self._budget * WARN_RATIO:
            logger.warning("ai_budget_threshold", extra={"budget_ratio": str(spent / self._budget)})

    def _run(
        self,
        providers: Sequence[tuple[ProviderSpec, A]],
        invoke: Callable[[A, float], R],
        usage: Callable[[R], tuple[int | None, int | None, int | None, str | None]],
        purpose: str,
        classification: Classification,
        essential: bool,
        job_id: uuid.UUID | None,
    ) -> R:
        candidates = [(spec, adapter) for spec, adapter in providers if eligible(spec, classification)]
        if not candidates:
            raise AIUnavailable("NO_PROVIDER")  # SRS-PRV-02: bỏ bước AI, chuyển xử lý thủ công
        self._check_budget(essential)
        for spec, adapter in candidates:  # thứ tự cấu hình: chính → dự phòng cùng mức phân loại
            for attempt in range(spec.max_retries + 1):
                if attempt:
                    self._sleep(spec.backoff_seconds * 2 ** (attempt - 1))
                started = time.monotonic()
                try:
                    result = invoke(adapter, spec.timeout_seconds)
                except ProviderError as error:
                    outcome: Outcome = "TIMEOUT" if isinstance(error, ProviderTimeout) else "ERROR"
                    self._record(spec, purpose, classification, outcome, started, job_id)
                    logger.warning("ai_provider_failed", extra={"provider": spec.name, "outcome": outcome})
                    continue
                tokens_in, tokens_out, pages, model = usage(result)
                self._record(
                    spec, purpose, classification, "SUCCESS", started, job_id,
                    tokens_in=tokens_in, tokens_out=tokens_out, pages=pages, model=model,
                )  # fmt: skip
                return result
        raise AIUnavailable("EXHAUSTED")

    def _record(
        self, spec: ProviderSpec, purpose: str, classification: Classification, outcome: Outcome, started: float,
        job_id: uuid.UUID | None, *, tokens_in: int | None = None, tokens_out: int | None = None,
        pages: int | None = None, model: str | None = None,
    ) -> None:  # fmt: skip
        self._recorder.record(
            CallRecord(
                provider=spec.name,
                model=model or spec.model,
                purpose=purpose,
                data_classification=classification,
                provider_is_local=spec.local,
                outcome=outcome,
                latency_ms=int((time.monotonic() - started) * 1000),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                pages=pages,
                cost_estimate=spec.cost(tokens_in=tokens_in, tokens_out=tokens_out, pages=pages),
                job_id=job_id,
                correlation_id=CORRELATION_ID.get(),
            )
        )
