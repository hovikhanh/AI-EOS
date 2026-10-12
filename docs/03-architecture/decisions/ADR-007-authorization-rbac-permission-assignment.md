# ADR-007 — Phân quyền: role → permission → assignment, policy tập trung

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | Cơ chế: `ARCHITECTURE_DECISION` (`Pre2C_Decision_Proposals.md` §2.5). Nội dung role/quyền R1–R8: `CDA_DIRECTIVE` (yêu cầu 12/10/2026 §5). Người giữ quyền dữ liệu nhân sự nhạy cảm: NEEDS_CONFIRMATION (R6) |
| Liên quan | D-09, D-11, D-12, D-14, D-21, D-22; UX §4.1, SEC-DC-01, SEC-DC-02 |
| Ngày cập nhật | 12/10/2026 |

## Context
Năm role nền tảng `ADMIN`, `CEO`, `CFO`, `MANAGER`, `EMPLOYEE`; Reviewer là assignment (R1). Quyền phải có phạm vi dữ liệu (UX §4.1), object-level, mặc định từ chối; tách quản trị hệ thống khỏi quyền nghiệp vụ.

## Decision
- Lưu trong CSDL: `role`, `permission`, `role_permission` (quyền nền của role), `user_role`, `assignment` (quyền được giao có phạm vi và thời hạn). Quyền hiệu lực = quyền nền của các role ∪ assignment còn hiệu lực, giới hạn bởi phạm vi.
- **Một policy module** ở backend (`access.policy`) với hàm duy nhất kiểu `authorize(actor, permission, resource) → Allow | Deny(reason)`; mọi router và mọi job handler gọi nó. **Mặc định deny.**
- **Object-level:** kiểm tra theo bản ghi cụ thể (chủ sở hữu, đơn vị, assignment), không chỉ theo loại endpoint; truy vấn danh sách áp bộ lọc phạm vi trong SQL.
- **Ràng buộc cứng trong code (không cấu hình được):**
  1. Người duyệt tài chính ≠ người tạo/gửi (D-14) — đồng thời là CHECK ở CSDL.
  2. Không cấp role `ADMIN` và `CFO` cho cùng tài khoản trong MVP (R7) — kiểm tra ở mọi đường cấp/đổi role, có trigger CSDL.
  3. ADMIN không tự đổi role/assignment của chính mình (A5) — CHECK `granted_by <> user_id`.
  4. Không gỡ/khóa ADMIN đang hoạt động cuối cùng (A4) — kiểm tra dưới khóa (advisory lock) để tránh hai ADMIN gỡ nhau đồng thời.
  5. Trần autonomy: tài chính ≤ L2, mọi tool ≤ L3 (D-11, D-12, R8).
- **AI** hành động với quyền của người dùng khởi tạo, giao với quyền của tool trong Tool Registry; không có "tài khoản hệ thống" vượt quyền người dùng.
- **Không có fallback tự động:** nếu không có người duyệt hợp lệ, giao dịch giữ `PENDING_APPROVAL` và hệ thống báo thiếu người duyệt (Architecture §7.4).
- Ma trận role/permission/assignment cụ thể: Architecture §6.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Thư viện policy ngoài (Casbin, OPA) | Thêm phụ thuộc/ngôn ngữ policy; nhu cầu MVP biểu diễn được bằng bảng + code |
| Phân quyền chỉ theo role | Không biểu diễn được Reviewer, ủy quyền tài chính, phạm vi đơn vị |

## Consequences
- Bộ test ma trận authorization sinh từ dữ liệu seed role/permission (ADR-013).
- Thay đổi quyền có hiệu lực ngay vì session bị thu hồi (ADR-006).

## Security Considerations
- Frontend chỉ ẩn/hiện; mọi quyết định ở backend.
- Lỗi 404 thay cho 403 khi người dùng không được biết đối tượng tồn tại (chống dò ID), trừ trường hợp hành động trên đối tượng họ đã thấy.
- Mọi lần từ chối quyền với hành động nhạy cảm được ghi audit `outcome=DENIED`.
- Seed role/permission đi theo migration; không seed tài khoản.
