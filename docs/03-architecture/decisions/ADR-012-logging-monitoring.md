# ADR-012 — Logging và monitoring

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` (`Pre2C_Decision_Proposals.md` §2.7, chỉ định của CDA 12/10/2026) |
| Liên quan | D-25, ADR-010; FR-AIQ-05, MET-05, NFR-03, NFR-07 |
| Ngày cập nhật | 12/10/2026 |

## Context
Cần chẩn đoán lỗi API/worker, theo dõi chi phí AI, phát hiện job kẹt, mà không xây hệ thống observability phân tán trong MVP.

## Decision
- **Log có cấu trúc JSON ra stdout** (API, worker, scheduler); Docker Compose thu thập; xoay vòng log của Docker được cấu hình.
- **Correlation ID**: nhận từ header `X-Request-ID` nếu hợp lệ hoặc sinh mới; truyền vào job (`correlation_id`) và audit.
- **Health/readiness:** `/health/live` (tiến trình sống), `/health/ready` (kết nối CSDL, storage, migration đã ở phiên bản mong đợi); worker có heartbeat ghi CSDL.
- **Theo dõi worker:** số job theo trạng thái, job `DEAD`, job có lease hết hạn, độ trễ queue, lỗi theo loại job — hiển thị trên trang "Tình trạng hệ thống" của ADMIN (UX §4.1) và log cảnh báo.
- **Chi phí AI:** tổng hợp từ `ai.call_log` (ADR-011).
- **Tùy chọn:** profile Compose bổ sung ngăn xếp quan sát mã nguồn mở (metrics + dashboard + thu log) khi cần; không bắt buộc trong MVP.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| OpenTelemetry đầy đủ + collector | Đường nâng cấp; quá mức cho MVP |
| Nền tảng theo dõi lỗi tự host | Nặng cho Docker Compose |

## Consequences
- Audit nghiệp vụ (ADR-010) tách khỏi log kỹ thuật; log không dùng làm bằng chứng nghiệp vụ.

## Security Considerations
- Bộ lọc log loại bỏ/che: mật khẩu, cookie, header `Authorization`, `X-CSRF-Token`, token mời, mã MFA, khóa API provider, nội dung tài liệu và trường nhạy cảm.
- Không log body request của endpoint xác thực và upload.
- Log lỗi không trả về client; client nhận `correlation_id` để tra cứu.
