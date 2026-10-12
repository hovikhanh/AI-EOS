# AI-EOS — User Journeys

> Phiên bản: 1.0 · Ngày: 12/10/2026 · Trạng thái: **Stage 2B — chờ CDA duyệt**
> Hành trình mức cao theo persona ([Personas.md](Personas.md)). Bước màn hình chi tiết, điểm kiểm tra quyền và nhánh lỗi đầy đủ ở [UX_Flows.md](UX_Flows.md); quy tắc ở [SRS.md](SRS.md). Số liệu trong ví dụ là minh họa (ASM-02).

| ID | Hành trình | Persona | Nguồn | Phạm vi MVP |
| --- | --- | --- | --- | --- |
| J1 | Onboarding doanh nghiệp trong một ngày | P5, P1 | UC-07 | Có |
| J2 | CEO buổi sáng: Briefing → giao việc | P1 | F1 (UC-01, UC-03 v1.0) | Có, phần tile/khối phụ thuộc Q-36, Q-37 |
| J3 | Gửi tài liệu và review trích xuất | P3, P4 | F2, US-DC-003, US-DC-006 | Có (không có email — D-18) |
| J4 | Biên bản họp thành việc | P2 | F3, UC-06, US-DC-004 | Có (không có Meeting bot — SC-06) |
| J5 | Check-in KPI/OKR | P3 | F4 | Có, nhịp check-in chờ Q-30 |
| J6 | Manager xử lý quá tải | P2 | F5 | **Chưa đủ căn cứ** — mô hình workload chờ Q-34 |
| J7 | Ghi nhận và duyệt giao dịch tài chính | P6, P2 | SC-04, D-12, D-14 | Có |
| J8 | Admin dừng khẩn cấp AI | P5 | D-09, D-10 | Có |

---

## J1 — Onboarding doanh nghiệp trong một ngày (UC-07)
- **Mục tiêu:** CEO có dashboard đầu tiên trong ngày (UC-07).
- **Bước:** Admin được bootstrap (A2) → Admin tạo tài khoản, gửi lời mời (A1) → Admin import danh sách nhân sự Excel (US-DC-007) và tải sơ đồ tổ chức → hệ thống dựng cây tổ chức → người phụ trách tải kế hoạch năm, bộ KPI (US-DC-005) → AI dựng cây mục tiêu ở trạng thái nháp → người có quyền duyệt từng phần → mục tiêu được kích hoạt → CEO mở Trang chủ.
- **Điểm chạm:** CLI bootstrap, trang quản trị người dùng, màn import, màn review, Trang chủ CEO.
- **Khó khăn:** dữ liệu Excel không theo template; tên người trong tài liệu không khớp danh bạ; chưa có người duyệt.
- **Nhánh lỗi:** dòng import lỗi → xuất file lỗi, ghi các dòng hợp lệ (FR-DC-18); tài liệu không phân loại được → người dùng chọn loại (FR-DC-09); chưa có người nhận assignment review → tài liệu chờ, Admin được cảnh báo.
- **Kết quả:** cây tổ chức, mục tiêu đã kích hoạt, dashboard có dữ liệu kèm nguồn.
- **Lưu ý:** "trong một ngày" là mục tiêu của UC-07, chưa đo.

## J2 — CEO buổi sáng (F1) — mục tiêu ≤ 2 phút, ≤ 5 chạm
- **Bước:** nhận thông báo Briefing sẵn sàng → Trang chủ: dòng tóm tắt, 4 ô chỉ số, khối "Cần anh quyết", khối "Rủi ro", "AI đã làm" → chạm ô chỉ số → panel AI giải thích kèm nguồn → chọn phương án → action card task/owner/hạn → Xác nhận → toast có Hoàn tác.
- **Khó khăn:** dữ liệu cũ, thiếu; con số không có nguồn.
- **Nhánh lỗi:** dữ liệu quá hạn → nhãn "cũ"; AI không có dữ liệu → nói rõ và gợi ý bổ sung (UX §7.3); AI lỗi → Trang chủ vẫn hiển thị số liệu không cần AI (BR-21); kill switch bật → action card ở L2 (luôn cần xác nhận).
- **Kết quả:** task được tạo với owner, hạn; quyết định được ghi (Decision Log — phạm vi theo dõi 30/60/90 chờ Q-41).
- **Chưa đủ căn cứ:** "đặt lịch" (Q-35, D-31); nội dung khối "Rủi ro" khi Risk Intelligence là P1 (Q-36).

## J3 — Gửi tài liệu và review (F2)
- **Bước:** thả file ở bất kỳ màn nào hoặc chụp ảnh trên mobile → thẻ tiến trình → AI phân loại, trích xuất → thông báo "1 cần xem lại" → Reviewer mở màn review song song, đi qua trường vàng/đỏ và trường trọng yếu → Enter để duyệt → dữ liệu ghi vào đích, toast "Xem bản ghi".
- **Khó khăn:** ảnh mờ, chữ viết tay; trường tiền sai.
- **Nhánh lỗi:** file sai định dạng/quá lớn/nhiễm mã độc → từ chối, thông báo; xử lý lỗi → thử lại; reviewer từ chối → lý do; đổi loại tài liệu → trích xuất lại.
- **Kết quả:** bản ghi có liên kết "Xem tài liệu gốc" (FR-DC-23).

## J4 — Biên bản họp thành việc (F3) — mục tiêu ≤ 10 phút
- **Bước:** tải biên bản/transcript (Word, PDF, ảnh) → AI tóm tắt 3 khối: Quyết định, Việc cần làm, Vấn đề mở → bảng action item với tên đã khớp danh bạ, hạn đã quy ra ngày; mục chưa chắc có dấu hỏi → người chủ trì sửa trong bảng → "Giao việc" → mỗi người nhận task kèm trích đoạn gốc.
- **Nhánh lỗi:** tên không khớp → người chủ trì chọn người; hạn mơ hồ → để trống, bắt buộc nhập trước khi giao (`[CẦN XÁC NHẬN]` — nguồn không nói task bắt buộc có hạn, nhưng US-DC-004 yêu cầu mỗi task có deadline).
- **Kết quả:** task có owner, deadline, link đoạn gốc (US-DC-004).

## J5 — Check-in KPI/OKR (F4) — mục tiêu ≤ 30 giây
- **Bước:** thông báo "Check-in tuần: 2 KR của bạn" → thẻ check-in với giá trị điền sẵn từ dữ liệu đã có → kéo thanh độ tự tin, ghi blocker bằng giọng nói/gõ → Gửi → Manager thấy trong tổng hợp team.
- **Chưa đủ căn cứ:** nhịp check-in và ai bắt buộc check-in (Q-30); cách tính giá trị điền sẵn từ "task đã xong" (Q-29).

## J6 — Manager xử lý quá tải (F5) — chưa đủ căn cứ
- **Theo UX:** cảnh báo "B quá tải 130% trong 2 tuần" → heatmap người × tuần → AI gợi ý (L1) chuyển task → Manager áp dụng → B, C nhận thông báo kèm lý do.
- **Thiếu:** cách tính % tải (ước lượng công việc, năng lực); BRD đưa năng lực từ bảng chấm công là Phase 2 (BRD §3.4). Hành trình này **chưa đặc tả** trong SRS cho tới khi có Q-34; phần "gợi ý chuyển task ở L1" được giữ trong kiến trúc.

## J7 — Giao dịch tài chính
- **Bước:** người có `finance.submit` tạo bản ghi doanh thu/chi phí/số dư tiền mặt (tay hoặc import; AI có thể soạn nháp) → gửi duyệt → người duyệt (khác người tạo) duyệt → ghi sổ vào kỳ đang mở → số liệu CEO cập nhật kèm "thời điểm cập nhật".
- **Nhánh:** thiếu người duyệt hợp lệ → chờ, thông báo; kỳ đã khóa → không ghi; sai sau khi ghi → đề nghị đảo → duyệt → bản gốc `REVERSED` → nhập bản điều chỉnh nếu cần; chưa có người quản lý kỳ → không mở kỳ được → Admin giao assignment cho người có role `CFO`.
- **Kết quả:** lịch sử giao dịch đầy đủ, không có bản ghi bị xóa.

## J8 — Admin dừng khẩn cấp AI
- **Bước:** Admin thấy sự cố AI → bật kill switch (xác thực lại, nhập lý do) → băng thông báo xuất hiện cho mọi người → hành động AI tự động mới trở thành bản nháp chờ xác nhận → người khởi tạo nhận thông báo → khi ổn định, Admin tắt kill switch → bản nháp vẫn chờ review, không tự chạy.
- **Kết quả:** không có ghi tự động nào trong thời gian bật; audit đầy đủ.
