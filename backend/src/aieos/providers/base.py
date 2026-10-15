"""Kiểu dùng chung của provider adapter (ADR-011): yêu cầu/kết quả, interface adapter, call record, lỗi.

Logic nghiệp vụ chỉ phụ thuộc các interface này; adapter thật (API tương thích OpenAI, OCR) thuộc T-205.
"""

import enum
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal, Protocol


class Classification(enum.StrEnum):
    """Phân loại dữ liệu của lời gọi — cùng giá trị với `capture.source_document.sensitivity` (Database_Design §6)."""

    NORMAL = "NORMAL"
    PERSONAL = "PERSONAL"
    SENSITIVE = "SENSITIVE"


Outcome = Literal["SUCCESS", "TIMEOUT", "ERROR"]

LOCAL_ONLY = frozenset({Classification.PERSONAL, Classification.SENSITIVE})  # SRS-PRV-02, INV-15


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class LLMRequest:
    messages: list[Message]
    response_schema: dict[str, Any] | None = None  # structured output; đầu ra vẫn là dữ liệu không tin cậy


@dataclass(frozen=True)
class LLMResult:
    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    model: str | None = None


@dataclass(frozen=True)
class OCRRequest:
    content: bytes
    media_type: str


@dataclass(frozen=True)
class OCRBlock:
    text: str
    page_no: int
    bbox: tuple[float, float, float, float]
    confidence: float


@dataclass(frozen=True)
class OCRResult:
    pages: int
    blocks: list[OCRBlock] = field(default_factory=list)
    model: str | None = None


@dataclass(frozen=True)
class ConvertedDocument:
    content: bytes
    media_type: str


class LLMAdapter(Protocol):
    """Adapter phải tự áp `timeout` (giây) cho lời gọi mạng; hết giờ → `ProviderTimeout`."""

    def complete(self, request: LLMRequest, *, timeout: float) -> LLMResult: ...


class OCRAdapter(Protocol):
    def recognize(self, request: OCRRequest, *, timeout: float) -> OCRResult: ...


class DocumentConverter(Protocol):
    """DOC/DOCX/XLSX → định dạng xử lý được; chạy trong worker, không thực thi macro (ADR-011)."""

    def convert(self, content: bytes, media_type: str) -> ConvertedDocument: ...


@dataclass(frozen=True)
class CallRecord:
    """Một dòng `ai.call_log` (Database_Design §5). Không chứa nội dung lời gọi."""

    provider: str
    model: str | None
    purpose: str
    data_classification: Classification
    provider_is_local: bool
    outcome: Outcome
    latency_ms: int
    tokens_in: int | None = None
    tokens_out: int | None = None
    pages: int | None = None
    cost_estimate: Decimal | None = None
    job_id: uuid.UUID | None = None
    correlation_id: str | None = None


class CallRecorder(Protocol):
    """Ghi call log và cho biết chi phí đã dùng trong kỳ ngân sách — module `ai` hiện thực (Architecture §3)."""

    def record(self, call: CallRecord) -> None: ...

    def spent(self) -> Decimal: ...


class ProviderError(Exception):
    """Adapter báo lỗi (mạng, HTTP, phản hồi hỏng). Thông điệp không chứa nội dung tài liệu hay khóa."""


class ProviderTimeout(ProviderError):
    pass


class AIUnavailable(Exception):
    """Bước AI không chạy được → luồng thủ công tiếp tục (SRS-PRV-03, BR-21; lỗi API `AI_UNAVAILABLE`)."""

    def __init__(self, reason: Literal["NO_PROVIDER", "EXHAUSTED", "BUDGET"]) -> None:
        super().__init__(reason)
        self.reason = reason
