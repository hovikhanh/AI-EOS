# ADR-008 — AI write gateway: Tool Registry, autonomy, kill switch

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED · Amendment 1 (12/10/2026, D-38) |
| Source | Cơ chế: `ARCHITECTURE_DECISION` (`Pre2C_Decision_Proposals.md` ADR-008). Hành vi kill switch K1–K6: `CDA_DIRECTIVE` (yêu cầu 12/10/2026 §3); D-09, D-11, D-12 là quyết định CDA trước đó |
| Liên quan | D-09, D-10, D-11, D-12, D-26; BR-04, BR-06, BR-09, BR-11, BR-13, FR-DC-17, FR-DCS-05, FR-AUT-01…04 |
| Ngày cập nhật | 12/10/2026 (amendment 1) |

## Context
BRD yêu cầu mọi lần ghi từ Domain 22 đi qua Tool Registry với permission, approval, audit (BR-04); tool có `risk_level`, `approval_required` (BRD §2.1); autonomy L0–L3 trong MVP (D-11); kill switch chỉ ADMIN, hạ L3 về L2, thực thi ở backend (D-09); retry/worker không được đi vòng (D-10).

## Decision
- Module `gateway` là **đường ghi duy nhất** cho: (a) mọi hành động ghi do AI đề xuất/khởi tạo, (b) commit dữ liệu trích xuất vào domain đích (FR-DC-17). Module domain không cung cấp đường ghi công khai cho agent/worker ngoài gateway.
- **Tool Registry** (bảng + định nghĩa trong code): `name`, `module`, `operation_type` (READ/WRITE/EXECUTION), `risk_level`, `financial`, `max_autonomy_level` (trần), `approval_required`, schema tham số.
- **Thứ tự kiểm tra tại gateway** (trong một transaction CSDL):
  1. Xác thực tham số theo schema tool.
  2. Authorization của **người khởi tạo** (ADR-007) cho tool và đối tượng.
  3. Mức autonomy hiệu lực = min(cấu hình theo tool × role × ngưỡng, trần tool, trần hệ thống L3; tài chính ≤ L2).
  4. **Kill switch:** đọc hàng `ai.kill_switch` với `FOR SHARE`; nếu bật và hành động không có xác nhận của người → mức hiệu lực tối đa L2.
  5. Idempotency key (bắt buộc với WRITE/EXECUTION).
  6. Nếu mức hiệu lực ≤ L2 và chưa có xác nhận hợp lệ → tạo **bản nháp hành động** (`ai.action`, trạng thái `PENDING_REVIEW`), không ghi domain. Nếu L3 → thực thi, đặt hạn hoàn tác ≥ 24 giờ (BR-11).
  7. Ghi audit (thành công, bị chặn, lỗi) trong cùng transaction.
- **Diễn giải K2 "chặn mọi ghi mới qua gateway":** khi kill switch bật, gateway chặn mọi ghi **không có xác nhận của người có thẩm quyền**; ghi đã được người có thẩm quyền xác nhận (L2) vẫn thực hiện. Căn cứ: D-09 quy định hạ về L2 (người xác nhận), không tắt hoàn toàn khả năng ghi.
- **Job/worker/retry:** handler không gọi domain trực tiếp; gọi gateway. Kill switch được đọc ở **mỗi** lần thực thi, kể cả retry. Khi bị chặn: nếu đủ dữ liệu và an toàn → lưu bản nháp L2 rồi mới đánh dấu job `SUCCEEDED` (cùng transaction); nếu không đủ dữ liệu → job `FAILED` với lý do `BLOCKED_BY_KILL_SWITCH`, audit, thông báo người khởi tạo (K2, K6). Retry không bao giờ biến một lần bị chặn thành lần ghi.
- **Bật/tắt kill switch:** chỉ permission `ai.kill_switch` (chỉ ADMIN), step-up, lý do bắt buộc; cập nhật hàng kill switch `FOR UPDATE` — mọi transaction gateway đang giữ `FOR SHARE` hoàn tất trước, transaction sau thấy trạng thái mới (thứ tự rõ ràng).
- **Tắt kill switch:** bản nháp giữ nguyên chờ review, không tự thực thi; lịch chạy lại từ chu kỳ kế tiếp (K3).
- **Nội dung AI không qua gateway [Amendment 1]:** tác vụ AI tạo nội dung mới không phải ghi nghiệp vụ (vd. tóm tắt CEO Briefing, job class `AI_CONTENT` — ADR-005) cũng chịu kill switch: khi bật, không khởi chạy, không tiếp tục, không ghi nội dung mới. Trả lời hội thoại trực tiếp cho người dùng (chat, chỉ đọc, L0) không bị chặn vì không ghi gì và do người dùng chủ động yêu cầu.
- **Bản nháp:** reviewer phải có quyền tương ứng; tài chính theo quyền duyệt tài chính và không tự duyệt (K4); quá thời hạn cấu hình (mặc định 30 ngày) → `NEEDS_REVIEW_STALE`, không xóa (K5); thay đổi thời hạn có audit.
- **An toàn AI (BR-06):** đầu ra LLM/OCR và nội dung tài liệu là **dữ liệu**; chỉ orchestrator (code) chọn tool theo luồng được định nghĩa; tham số tool từ đầu ra LLM luôn validate schema và kiểm tra quyền như input không tin cậy; nội dung tài liệu không thể thay đổi policy, quyền, autonomy.

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Mỗi module tự kiểm tra autonomy/kill switch | Dễ có đường vòng; không kiểm thử tập trung được |
| Kill switch chỉ ở frontend hoặc chỉ khi xếp job | Vi phạm D-09, D-10 |

## Consequences
- Cần bảng `ai.action`, `ai.kill_switch`, `ai.autonomy_policy`, `ai.tool` (Database_Design §5).
- Lint kiến trúc chặn import trực tiếp service ghi của domain từ module `ai`/`jobs`.

## Security Considerations
- Gateway là điểm kiểm soát an ninh chính cho AI; mọi nhánh (cho phép, nháp, chặn, lỗi) có test (ADR-013).
- Hàng kill switch là singleton có `CHECK (id = 1)`; chỉ policy module cho phép cập nhật.
- Không có cấu hình nào cho phép bỏ qua phê duyệt tài chính, kill switch, authorization hoặc audit (R8).

## Amendments

### Amendment 1 — AMD-02 (12/10/2026)
- **Nguồn:** CDA duyệt AMD-02 theo phiên bản của CDA (Decision_Log D-38).
- **Thay đổi:** mở rộng phạm vi kill switch tới job `AI_CONTENT` ngoài gateway (mục Decision); phân loại job ở ADR-005 Amendment 1.
- **Không thay đổi:** thứ tự kiểm tra tại gateway, hạ L3 về L2, bản nháp không tự thực thi.
- **Diễn giải cần CDA lưu ý:** chat AI chỉ đọc theo yêu cầu trực tiếp của người dùng vẫn hoạt động khi kill switch bật (D-09 nói về hành động WRITE/EXECUTION; BRD §4.2 L0 là "chỉ đọc và trả lời"). Nếu CDA muốn tắt cả chat khi bật kill switch, cần một quyết định riêng. **CDA xác nhận diễn giải này ngày 15/10/2026 (D-48).**
