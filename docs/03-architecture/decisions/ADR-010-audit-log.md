# ADR-010 — Audit log append-only

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` (`Pre2C_Decision_Proposals.md` ADR-010); phạm vi xem audit R3, R4: `CDA_DIRECTIVE` |
| Liên quan | D-25, D-21 (R3); FR-DC-05, BR-04, FR-DCS-06, FR-DF-04, CMP-01 |
| Ngày cập nhật | 12/10/2026 |

## Context
Nguồn yêu cầu audit cho mọi thay đổi thủ công (FR-DC-05) và mọi hành động AI (BR-04, BRD §2.1). CDA yêu cầu lưu cả thành công và thất bại của thao tác nhạy cảm, không log bí mật.

## Decision
- Bảng `audit.event` trong PostgreSQL, **ghi cùng transaction** với thay đổi nghiệp vụ (thay đổi không commit → audit không tồn tại; thao tác bị từ chối → audit ghi trong transaction riêng).
- Trường: `occurred_at`, `category` (`SECURITY` | `ADMIN` | `BUSINESS` | `AI`), `actor_type` (`USER` | `AI` | `SYSTEM` | `BOOTSTRAP`), `actor_user_id`, `on_behalf_of_user_id`, `ai_agent`, `autonomy_level`, `action`, `resource_type`, `resource_id`, `outcome` (`SUCCESS` | `DENIED` | `FAILED` | `BLOCKED`), `reason`, `changes` (trước/sau đã che), `correlation_id`, `request_ip`, `user_agent`.
- **Append-only ở cấp ứng dụng và CSDL:** role ứng dụng chỉ có `INSERT`, `SELECT`; trigger chặn `UPDATE`/`DELETE`; không có API sửa/xóa.
- **Che dữ liệu:** không ghi mật khẩu, token, secret, mã MFA, nội dung tài liệu; trường nhạy cảm (SEC-DC-02) che trong `changes`.
- **Phạm vi xem (R3, R4):** `ADMIN` xem audit `SECURITY`/`ADMIN` toàn hệ thống và **siêu dữ liệu** của audit `BUSINESS`/`AI` (không có `changes`); `CEO` xem audit `BUSINESS`/`AI` chỉ đọc trong phạm vi được phép; người dùng khác xem lịch sử của đối tượng họ có quyền đọc (tab "Lịch sử", UX §4.2).
- Phân vùng theo thời gian khi dung lượng lớn; thời hạn lưu trữ: chưa có chính sách (GAP-15), mặc định **không xóa** trong MVP.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Audit qua log kỹ thuật | Không bảo đảm toàn vẹn, không cùng transaction, khó truy vấn theo đối tượng |
| Event sourcing toàn hệ thống | Quá phức tạp cho MVP |

## Consequences
- Bảng tăng trưởng liên tục → theo dõi dung lượng (ADR-012), phân vùng.
- Tab "Lịch sử" và "Hoạt động AI" trên trang chi tiết (UX-11) đọc từ bảng này.

## Security Considerations
- Chuỗi hash liên kết giữa các bản ghi audit để phát hiện sửa đổi ngoài ứng dụng: **không** làm trong MVP; append-only dựa trên quyền CSDL + trigger. Ghi nhận là rủi ro còn lại khi người có quyền chủ sở hữu CSDL can thiệp.
- Mọi lần xem audit `SECURITY` cũng được audit.
