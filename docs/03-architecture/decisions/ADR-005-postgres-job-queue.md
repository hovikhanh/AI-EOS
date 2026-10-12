# ADR-005 — Job queue trên PostgreSQL

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED · Amendment 1 (12/10/2026, D-38) |
| Source | `ARCHITECTURE_DECISION` — `Pre2C_Decision_Proposals.md` §2.4, chỉ định của CDA (12/10/2026) |
| Liên quan | D-10 (K2, K3), ADR-008; NFR-01, NFR-02, FR-DC-21 |
| Ngày cập nhật | 12/10/2026 (amendment 1) |

## Context
Xử lý tài liệu bất đồng bộ (NFR-01: p95 ≤ 60 giây cho tài liệu ≤ 5 trang), tác vụ AI, retry, lịch định kỳ (nhắc review hằng ngày — K6; chuyển bản nháp quá hạn — K5). Kill switch phải áp dụng đồng nhất cho worker, retry, lịch (D-10).

## Decision
- Bảng `jobs.job` trong PostgreSQL. Job được **xếp cùng transaction** với thay đổi nghiệp vụ tạo ra nó (transactional outbox: commit cả hai hoặc không gì cả).
- **Claim an toàn:** worker lấy job bằng `SELECT … FOR UPDATE SKIP LOCKED`, đặt `status=RUNNING`, `lease_expires_at = now() + lease`, `attempts = attempts + 1` trong cùng câu lệnh.
- **Lease/timeout:** worker gia hạn lease khi chạy lâu; tiến trình "reaper" trả job có lease hết hạn về `QUEUED` (nếu còn lượt) hoặc `DEAD`.
- **Retry có giới hạn** (`max_attempts` theo loại job), **backoff** lũy thừa có jitter; lỗi không thể retry (validation, quyền) → `FAILED` ngay.
- **Idempotent:** mỗi job có `idempotency_key` duy nhất; handler phải an toàn khi chạy lại (kiểm tra kết quả đã tồn tại trước khi ghi; ghi kết quả + đánh dấu job xong trong cùng transaction).
- **Hoàn tất bền vững (K2):** job chỉ chuyển `SUCCEEDED` trong cùng transaction lưu kết quả (bản ghi, bản nháp L2).
- **Lịch định kỳ** lưu ở bảng `jobs.schedule`; scheduler chạy trong worker, chỉ một instance nhờ advisory lock; mỗi lần đến hạn tạo job với khóa idempotency `schedule_id + slot`.
- **Kill switch (K2, K3):** job ghi dữ liệu luôn đi qua cổng ghi (ADR-008); lịch có cờ `may_write=true` bị **bỏ qua** khi kill switch bật, ghi log + audit, `next_run_at` nhảy sang chu kỳ kế tiếp, không chạy bù.
- **Phân loại job [Amendment 1]:** mỗi loại job (`kind`) có một `job_class` cố định khai báo trong code (registry), không cấu hình được qua giao diện/CSDL: `ORCHESTRATION` (điều phối: lên lịch, nhắc việc, đánh dấu bản nháp quá hạn, dọn dẹp — không tạo kết quả nghiệp vụ hay nội dung AI mới), `AI_CONTENT` (AI tạo nội dung mới, vd. tóm tắt Briefing), `BUSINESS_WRITE` (ghi dữ liệu nghiệp vụ, luôn qua gateway). Khi kill switch bật: `ORCHESTRATION` chạy bình thường; `AI_CONTENT` không khởi chạy/không tiếp tục, không ghi nội dung mới, ghi log + audit `job.skipped_kill_switch`; `BUSINESS_WRITE` theo ADR-008. Lịch kế thừa `job_class` của loại job nó sinh ra (`may_write` = `job_class <> 'ORCHESTRATION'`).
- Chuyển sang Redis/Valkey hoặc RabbitMQ chỉ khi có số đo cho thấy queue PostgreSQL không đạt NFR-01/NFR-02.

## Alternatives
| Phương án | Lý do không chọn trong MVP |
| --- | --- |
| Redis/Valkey + thư viện worker | Thêm container; job và dữ liệu không cùng transaction → cần outbox riêng |
| RabbitMQ | Nặng hơn nhu cầu; cùng vấn đề transaction |

## Consequences
- Không thêm hạ tầng; mọi trạng thái nhất quán khi process chết giữa chừng (job hoặc chưa commit → chạy lại; hoặc đã commit cùng kết quả).
- Bảng job tăng trưởng → dọn job hoàn tất cũ theo lịch (giữ audit riêng).
- Thông lượng phải đo trong test hiệu năng (ADR-013).

## Security Considerations
- Payload job không chứa secret hay dữ liệu nhạy cảm không cần thiết; tham chiếu bằng ID.
- Job chạy với danh tính của **người khởi tạo** (lưu `initiated_by`) và quyền được kiểm tra lại tại thời điểm thực thi (quyền có thể đã bị thu hồi).
- Job do nội dung tài liệu sinh ra không được tạo job loại khác ngoài danh sách cho phép của pipeline (BR-06).

## Amendments

### Amendment 1 — AMD-02 (12/10/2026)
- **Nguồn:** CDA duyệt AMD-02 theo phiên bản của CDA (Decision_Log D-38). Phiên bản do người phân tích đề xuất trước đó (Briefing vẫn chạy khi kill switch bật) **không** được áp dụng.
- **Thay đổi:** thêm phân loại `job_class` (mục Decision). Quản lý lịch Briefing (tạo/cập nhật lịch) là thao tác cấu hình, có authorization + audit, không phải job. Tạo nội dung Briefing là `AI_CONTENT`. Bộ hẹn giờ của lịch Briefing là `ORCHESTRATION`: khi kill switch bật, nó ghi nhận lần bỏ qua và không xếp job `AI_CONTENT`.
- **Chống né kiểm soát:** một loại job ghi dữ liệu nghiệp vụ hoặc ghi nội dung do AI tạo **không được** khai báo là `ORCHESTRATION`. Bộ test bắt buộc kiểm tra: mọi handler `ORCHESTRATION` không gọi gateway, không gọi `LLMProvider`/`OCRProvider`, không ghi bảng nghiệp vụ (chỉ ghi `jobs.*`, `notify.*`, `audit.*`, cờ trạng thái bản nháp).
- **Retry:** retry của `AI_CONTENT` kiểm tra kill switch ở mỗi lần chạy; job `AI_CONTENT` bị bỏ qua do kill switch chuyển `CANCELLED` với lý do `KILL_SWITCH`, không retry.
- **Tác động:** ADR-008, Architecture §8.2, Database_Design §5, SRS-BRF-11, SRS-AIC-06, API-INS-03, TEST_Plan.
