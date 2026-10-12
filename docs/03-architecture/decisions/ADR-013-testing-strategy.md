# ADR-013 — Chiến lược kiểm thử và cổng CI

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` (`Pre2C_Decision_Proposals.md` §2.8, chỉ định của CDA 12/10/2026) |
| Liên quan | Toàn bộ ADR-001…012; Architecture §11; TEST_Plan (Stage 2D) |
| Ngày cập nhật | 12/10/2026 |

## Context
Các bất biến quan trọng (tách nhiệm vụ, đảo một lần, idempotency, kill switch, phân quyền) phải được chứng minh bằng test, không chỉ bằng tài liệu.

## Decision
| Tầng | Công cụ | Phạm vi bắt buộc |
| --- | --- | --- |
| Unit backend | pytest | State machine tài chính, tính autonomy hiệu lực, policy authorization, chuẩn hóa dữ liệu VN (FR-DC-13) |
| Integration backend | pytest + **PostgreSQL thật** trong container | Ràng buộc CSDL, khóa dòng, queue claim/lease/retry, outbox, trigger audit; **không dùng SQLite thay PostgreSQL** |
| API | pytest + HTTP client; contract test theo OpenAPI | Status code, lỗi, CSRF, idempotency, `If-Match` |
| Authorization matrix | Sinh từ seed role/permission/assignment | Mỗi endpoint × role × phạm vi: cho phép và **từ chối** |
| Migration | Alembic upgrade từ rỗng → head; downgrade một bước khi có thể; so khớp model ↔ schema | Mọi migration |
| Tài chính | Test đồng thời (hai duyệt, hai đảo cùng lúc), retry trùng idempotency key, kỳ đóng, thiếu người duyệt | ADR-009 |
| Kill switch | Job trong queue, đang chạy, retry, lịch, bật/tắt giữa chừng | ADR-008, ADR-005 |
| Frontend | Vitest + Testing Library | Component, trạng thái lỗi |
| E2E | Playwright | Luồng F1–F5 phạm vi MVP, review tài liệu, kill switch từ góc nhìn người dùng |
| AI | Adapter giả lập trong CI; bộ đánh giá vàng (FR-AIQ-01) chạy riêng | Không gọi provider thật trong CI |
| Bảo mật | Quét phụ thuộc Python/JS, phân tích tĩnh, test upload độc hại, prompt injection qua tài liệu (BR-06), brute force, session fixation, tái dùng token mời | Architecture §10 |
| Backup/restore | Diễn tập khôi phục trên môi trường thử | NFR-03 |

**Cổng CI trước khi merge:** lint (Python, TypeScript), type checking (Python, TypeScript strict), unit + integration + authorization matrix + migration test, quét phụ thuộc mức nghiêm trọng cao. E2E và hiệu năng chạy theo lịch/trước release.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| SQLite cho test nhanh | Khác hành vi khóa dòng, ràng buộc, JSON → bỏ sót lỗi tài chính |
| Chỉ E2E | Chậm, không bao phủ tổ hợp quyền |

## Consequences
- CI cần chạy container PostgreSQL.
- Test case chi tiết và tiêu chí nghiệm thu được viết ở `docs/04-delivery/TEST_Plan.md` (Stage 2D), liên kết tới AC-ARCH ở Architecture §11.

## Security Considerations
- Dữ liệu test là dữ liệu giả; không dùng dữ liệu thật của doanh nghiệp trong CI.
- Secret cho CI nạp từ kho secret của CI, không commit.
