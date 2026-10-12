# ADR-002 — Backend: Python + FastAPI + SQLAlchemy 2 + Alembic

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` trong định hướng `[CDA nêu]` "backend Python" (Decision_Log D-06); so sánh tại `Pre2C_Decision_Proposals.md` §2.2 |
| Liên quan | D-06, D-07; UX-23, FR-DCS-01, FR-AIQ-02 |
| Ngày cập nhật | 12/10/2026 |

## Context
Backend cần: trả lời AI truyền dần với nút Dừng (UX-23), schema trích xuất do Admin cấu hình (FR-DCS-01), hợp đồng API rõ ràng, transaction và khóa dòng cho tài chính (D-14).

## Decision
- Python (phiên bản ổn định được hỗ trợ, chốt trong lockfile khi triển khai), **FastAPI** (ASGI), **SQLAlchemy 2** (typed ORM, `select()`), **Alembic** cho migration, **Pydantic v2** cho schema request/response và validation.
- Logic nghiệp vụ nằm ở tầng service của từng module; router chỉ làm validate → gọi service → trả response.
- Driver PostgreSQL hỗ trợ async cho API; worker có thể dùng cùng tầng service.
- OpenAPI sinh từ code là nguồn kiểm tra đối chiếu với `API_Specification.md` (contract test, ADR-013).
- Quản lý phụ thuộc có lockfile; quét lỗ hổng phụ thuộc trong CI.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Django + DRF | Auth/admin có sẵn, nhưng streaming AI và schema động kém tự nhiên; giao diện quản trị của AI-EOS theo UX riêng (UX §4) nên Django Admin ít giá trị |
| Framework Python khác (Flask, Litestar) | Hệ sinh thái/khả năng tuyển người kém hơn cho nhu cầu này |

## Consequences
- Phần xác thực phải lắp từ thư viện đã kiểm chứng (ADR-006) — rủi ro chính của lựa chọn này.
- Cần kỷ luật kiến trúc (ADR-001) vì FastAPI không áp đặt cấu trúc.

## Security Considerations
- Không tự viết thuật toán mật mã; dùng thư viện đã kiểm chứng cho hash mật khẩu, TOTP, token ngẫu nhiên.
- Pydantic validate mọi input; từ chối trường thừa ở schema ghi (`extra="forbid"`).
- Không trả stack trace ra client; lỗi theo định dạng chuẩn (API_Specification §1.5).
- Mọi route mặc định yêu cầu xác thực; route công khai phải khai báo tường minh và có test (ADR-013).
