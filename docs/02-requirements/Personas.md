# AI-EOS — Personas

> Phiên bản: 1.0 · Ngày: 12/10/2026 · Trạng thái: **Stage 2B — giả thuyết, cần kiểm chứng**
> Năm persona lấy từ UX §2.1. UX tự ghi: "xây từ BRD và giả định, cần kiểm chứng bằng phỏng vấn" (ASM-01). Kế hoạch kiểm chứng: phỏng vấn 8–10 người, 2 người mỗi persona, tuần 1–2 (UX §10.2); người tham gia chưa xác định (Q-20, D-35).
> Persona ≠ role hệ thống. Ánh xạ persona → role/permission theo D-21 (R1–R8) và Architecture §6.

## 1. Tổng quan

| Persona | Role hệ thống | Assignment thường có | Thiết bị chính | Tần suất | Nguồn |
| --- | --- | --- | --- | --- | --- |
| P1 CEO — "Biết ngay, quyết nhanh" | `CEO` | — | Mobile (sáng, giữa họp); desktop khi chuẩn bị họp | Nhiều lần/ngày, 1–5 phút | UX §2.1 |
| P2 Director/Manager — "Giữ team đúng hướng" | `MANAGER` (Director = MANAGER ở đơn vị cao hơn `[CẦN XÁC NHẬN]`) | `extraction.review` (đơn vị); `finance.submit` khi được giao | Desktop; mobile để duyệt | Hằng ngày, 15–60 phút | UX §2.1 |
| P3 Employee — "Làm việc, ít khai báo" | `EMPLOYEE` | `extraction.review` khi được giao | Mobile và desktop | Hằng ngày, vài phút | UX §2.1 |
| P4 Reviewer dữ liệu (kế toán, thư ký, admin phòng ban) | Role nghiệp vụ của chức danh (thường `EMPLOYEE`/`MANAGER`) | `extraction.review` theo hàng chờ | Desktop màn hình lớn, bàn phím | Nhiều giờ/ngày vào cao điểm | UX §2.1; D-21 R1 |
| P5 Admin — "Cấu hình an toàn" | `ADMIN` | — | Desktop | Theo đợt | UX §2.1 |
| P6 Người phụ trách tài chính | `CFO` | `finance.submit`, `finance.approve`, `finance.reverse.request`, `finance.period.manage` | Desktop | `[CẦN XÁC NHẬN]` | BRD US-DC-009, UC-08 ("Finance"); D-21 R5. **Không có trong UX §2.1** — persona suy ra, cần kiểm chứng |

Persona "Legal/Sales" (US-DC-010) thuộc P1/Phase 2, chưa mô tả (D-21: NEEDS_CONFIRMATION).

## 2. Chi tiết

### P1 — CEO
- **Mục tiêu:** biết công ty có ổn không, cái gì cần mình, giao việc.
- **Nỗi đau:** phải hỏi từng người; số liệu vênh nhau; không biết việc đã giao đi đến đâu.
- **Phát hiện thiết kế:** dùng theo nhịp ngắn (< 5 phút) → màn đầu tiên trả lời "có gì cần tôi?" không cần cuộn (UX §2.3); sai một con số trước HĐQT là bỏ dùng → nguồn, độ mới, độ tin cậy luôn hiển thị.
- **Quyền nghiệp vụ:** đọc toàn công ty; không duyệt tài chính mặc định (R2); không bật kill switch (D-09); xem audit nghiệp vụ chỉ đọc (R3).
- **Luồng chính:** F1 (Briefing → giao việc).

### P2 — Director / Manager
- **Mục tiêu:** theo dõi KPI/OKR, workload, duyệt việc, chuẩn bị báo cáo lên trên.
- **Nỗi đau:** tốn thời gian tổng hợp báo cáo, không thấy ai quá tải.
- **Quyền nghiệp vụ:** đọc đơn vị và cấp dưới; xác nhận bản nháp AI trong đơn vị; không duyệt tài chính (R5).
- **Luồng chính:** F3 (biên bản → việc), F5 (xử lý quá tải — phụ thuộc Q-34).

### P3 — Employee
- **Mục tiêu:** biết hôm nay làm gì, cập nhật tiến độ nhanh, gửi chứng từ.
- **Nỗi đau:** nhập liệu lặp lại, báo cáo nhiều nơi.
- **Phát hiện thiết kế:** cập nhật task/chứng từ quá 10 giây → dữ liệu thiếu (UX §2.3, U5).
- **Ghi chú phạm vi:** gửi chứng từ chi phí (biên lai) là Phase 2 (D-17).
- **Luồng chính:** F4 (check-in), F2 (gửi tài liệu).

### P4 — Reviewer dữ liệu
- **Mục tiêu:** duyệt nhanh, không sai.
- **Nỗi đau:** nhập tay từ giấy, sợ sai số tiền.
- **Phát hiện thiết kế:** người dùng "chuyên nghiệp": mật độ cao, phím tắt, xử lý hàng loạt (UX §2.3, U7).
- **Quyền:** chỉ thấy tài liệu được giao (UX §4.1); trường tài chính cần thêm quyền tài chính.
- **Luồng chính:** F2 bước review.

### P5 — Admin
- **Mục tiêu:** thiết lập tổ chức, quyền, AI policy, schema tài liệu.
- **Nỗi đau:** sợ AI vượt quyền, khó kiểm tra quyền.
- **Quyền:** quản trị hệ thống, kill switch; **không** đọc dữ liệu nghiệp vụ, lương, PII mặc định; không duyệt tài chính (R4, D-21).

### P6 — Người phụ trách tài chính (giả thuyết)
- **Mục tiêu (suy ra từ BRD):** ghi nhận doanh thu, chi phí, tiền mặt chính xác; duyệt giao dịch; đảo khi sai.
- **Quyền:** theo assignment tài chính; không tự duyệt giao dịch mình tạo (D-14); không giữ role `ADMIN` cùng lúc (R7).
- **Cần kiểm chứng:** tần suất, quy mô giao dịch, số người có quyền duyệt (ảnh hưởng rủi ro "thiếu người duyệt").
