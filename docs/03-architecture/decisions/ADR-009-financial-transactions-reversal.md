# ADR-009 — Giao dịch tài chính: phê duyệt, ghi sổ, bút toán đảo

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED · Amendment 1 (12/10/2026, D-37) |
| Source | Quy tắc nghiệp vụ: D-12, D-13 (CDA) và F1–F7 (`CDA_DIRECTIVE`, yêu cầu 12/10/2026 §4). Cơ chế kỹ thuật (ràng buộc, khóa, idempotency): `ARCHITECTURE_DECISION` |
| Liên quan | D-12, D-13, D-14, D-15, D-16; SC-04, BR-15, BR-18, FR-DC-05, FR-AUT-03 |
| Ngày cập nhật | 12/10/2026 (amendment 1) |

## Context
Finance Lite (SC-04, BRD §6.1): doanh thu, chi phí, tiền mặt, runway — nhập tay hoặc import. Ghi tài chính luôn L2 (D-12); hoàn tác bằng bút toán đảo, không xóa lịch sử (D-13). AI-EOS không thay phần mềm kế toán (BR-18).

## Decision
**Phạm vi MVP (F7):** ba loại bản ghi `REVENUE`, `EXPENSE`, `CASH_BALANCE`; runway là chỉ số tính ra (BRD §4.3: tiền mặt / burn ròng hàng tháng). Ngân sách, hóa đơn (D-17), tích hợp ngân hàng: không thuộc MVP.

**Kỳ báo cáo quản trị (F1):** bảng kỳ `OPEN`/`CLOSED`; không phải sổ cái hay kỳ kế toán pháp lý. Mở và khóa kỳ dùng permission `finance.period.manage`, step-up, audit. Mở lại kỳ đã khóa: không hỗ trợ trong MVP (giữ lịch sử kỳ đã khóa).

**State machine:**

| Từ | Đến | Ai | Điều kiện |
| --- | --- | --- | --- |
| — | `DRAFT` | Người có `finance.submit` (trực tiếp hoặc qua AI soạn thay) | Idempotency key |
| `DRAFT` | `PENDING_APPROVAL` | Người tạo | Hợp lệ; kỳ của ngày giao dịch tồn tại **và `OPEN`** [Amendment 1] |
| `DRAFT` | `CANCELLED` | Người tạo | — |
| `PENDING_APPROVAL` | `CANCELLED` | Người tạo (rút lại, F3) | Lý do; audit |
| `PENDING_APPROVAL` | `POSTED` | Người có `finance.approve` trong phạm vi, **khác người tạo/gửi** | Kỳ ghi sổ `OPEN`; version khớp |
| `PENDING_APPROVAL` | `REJECTED` | Người có `finance.approve`, khác người tạo | Lý do bắt buộc |
| `POSTED` | `REVERSED` | Hệ thống | Khi bút toán đảo liên kết chuyển `POSTED`, cùng transaction |
| `PENDING_APPROVAL` | `ON_HOLD` | Hệ thống | Kỳ ghi sổ của giao dịch không còn `OPEN` (phòng thủ — xem Amendment 1) [Amendment 1] |
| `ON_HOLD` | `CANCELLED` | Người tạo | Rút lại, lý do bắt buộc [Amendment 1] |
| `ON_HOLD` | `REJECTED` | Người có `finance.approve`, khác người tạo | Lý do bắt buộc [Amendment 1] |

- Muốn sửa nội dung → tạo bản nháp mới (F3). Không có `PENDING_APPROVAL → DRAFT`.
- **Loại giao dịch:** `ORIGINAL`, `REVERSAL` (đảo toàn bộ, tham chiếu bắt buộc `reverses_id`), `ADJUSTMENT` (bút toán ghi lại số đúng sau khi đã đảo, tham chiếu `adjusts_id`). Đảo một phần: DEFERRED.
- **Không đảo bút toán đảo (F4):** chỉ `ORIGINAL`/`ADJUSTMENT` đang `POSTED` mới được đảo.
- **Kỳ gốc đã khóa (F2):** bút toán đảo ghi sổ vào **kỳ đang mở**, lưu liên kết giao dịch gốc, kỳ gốc và lý do; nếu không có kỳ mở hợp lệ → từ chối, yêu cầu người có `finance.period.manage` mở kỳ.
- **AI soạn (F5):** dùng cùng quy trình; người gửi là actor tạo/gửi; audit ghi riêng `ai_assisted=true`, `ai_action_id`.
- **Hạn mức (F6):** không có hạn mức tự suy đoán; chỉ người có `finance.approve` trong phạm vi được duyệt. Bảng `finance.approval_delegation` dự trữ cho ủy quyền/hạn mức sau, **không dùng trong MVP**.
- **Thiếu người duyệt:** nếu không tồn tại người dùng hoạt động nào có `finance.approve` phù hợp và khác người tạo, giao dịch giữ `PENDING_APPROVAL`, hiển thị cảnh báo "thiếu người duyệt hợp lệ" cho người tạo và ADMIN; **không** có cơ chế tự vượt kiểm soát.

**Toàn vẹn:**
- Nội dung tài chính của bản ghi `POSTED`/`REVERSED` bất biến (trigger CSDL chặn UPDATE các cột nội dung; chỉ cột trạng thái/liên kết được đổi theo state machine).
- Không có DELETE (quyền CSDL + không có API) — D-15.
- CHECK `approved_by <> created_by AND approved_by <> submitted_by`.
- Unique có điều kiện: mỗi giao dịch gốc tối đa một bút toán đảo ở trạng thái chưa kết thúc hoặc `POSTED` → chặn hai đề nghị đảo song song.
- Idempotency key duy nhất theo (người tạo, key); gửi lại cùng key + cùng nội dung → trả kết quả cũ; khác nội dung → 409.
- Concurrency: duyệt/đảo dùng `SELECT … FOR UPDATE` trên giao dịch (và kỳ) + kiểm tra `version` (HTTP `If-Match`); hai request duyệt đồng thời → một thành công, một nhận 409/412.
- Lịch sử trạng thái append-only (`finance.transaction_event`) + audit cùng transaction.
- Lý do bắt buộc cho rút lại, từ chối, đảo (BR-15, FR-DC-05).

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| Sửa tại chỗ có lịch sử phiên bản | Vi phạm D-13 |
| Cho trả về `DRAFT` để sửa | Lịch sử phức tạp; F3 chọn tạo bản nháp mới |
| Lấy kỳ từ phần mềm kế toán ngoài | Không có tích hợp trong MVP (D-31); F1 chọn kỳ quản trị nội bộ |

## Consequences
- Báo cáo tổng hợp tính trên giao dịch `POSTED` (bút toán đảo mang dấu ngược); runway và số liệu CEO có "thời điểm cập nhật" (FR-DF-03).
- Doanh nghiệp cần ≥ 1 người có `finance.approve` khác người tạo; nếu không, giao dịch không thể ghi sổ (rủi ro vận hành đã được CDA chấp nhận ở yêu cầu 12/10/2026 §4).

## Security Considerations
- Kiểm tra tách nhiệm vụ ở cả backend và CSDL (phòng thủ nhiều lớp).
- Mọi thao tác thành công và thất bại (từ chối quyền, xung đột version, kỳ đóng) được audit.
- Không trường tài chính nào được ghi trực tiếp bởi AI; AI chỉ tạo `DRAFT` qua gateway.

## Amendments

### Amendment 1 — AMD-01 (12/10/2026)
- **Nguồn:** CDA duyệt AMD-01 (Decision_Log D-37), đề xuất tại SRS §15.2.
- **Trước:** `DRAFT → PENDING_APPROVAL` chỉ yêu cầu "kỳ của ngày giao dịch tồn tại"; giao dịch thuộc kỳ đã khóa có thể nằm chờ duyệt và chỉ bị chặn khi duyệt (`PERIOD_CLOSED`).
- **Sau:**
  1. Gửi duyệt yêu cầu kỳ của ngày giao dịch tồn tại **và `OPEN`**; ngược lại từ chối (`PERIOD_CLOSED` hoặc `NO_OPEN_PERIOD`). Hệ thống **không** tự đổi ngày giao dịch, **không** tự chuyển kỳ, **không** bỏ qua phê duyệt. Giao dịch gốc có ngày thuộc kỳ đã khóa không gửi duyệt được (trả lời Q-40).
  2. **Phòng ngừa chính (không đổi):** không khóa kỳ khi kỳ còn giao dịch `PENDING_APPROVAL`; gửi duyệt giữ khóa chia sẻ trên hàng kỳ, khóa kỳ giữ khóa độc quyền → hai thao tác được tuần tự hóa.
  3. **Phòng thủ (mới):** nếu tại thời điểm duyệt hệ thống phát hiện kỳ ghi sổ của giao dịch không còn `OPEN` (không xảy ra trong vận hành bình thường; ví dụ do khôi phục dữ liệu hoặc can thiệp ngoài ứng dụng), giao dịch chuyển `ON_HOLD` với `hold_reason = PERIOD_CLOSED`, duyệt trả `409 PERIOD_CLOSED`, thông báo người tạo, người duyệt và Admin. Chỉ người có thẩm quyền giải quyết: người tạo rút lại, hoặc người duyệt từ chối. Không có chuyển `ON_HOLD → POSTED`.
- **Tác động:** Database_Design (trạng thái `ON_HOLD`, cột `hold_reason`), SRS-FIN-05/16/17, API-FIN-08/10, FL-11, TEST_Plan.
- **Kiểm soát không thay đổi:** tách nhiệm vụ, idempotency, version, audit, không xóa.
