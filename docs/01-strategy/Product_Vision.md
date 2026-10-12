# AI-EOS — Product Vision

> Phiên bản: 1.0 · Ngày: 12/10/2026 · Trạng thái: **Stage 2B — chờ CDA duyệt**
> Nguồn: `BRD_Review.md` (BRD), `UI_UX_Proposal.md` (UX), Decision_Log 0.5. Toàn văn BRD v1.1 không có trong repository (D-01). AI-EOS là sản phẩm độc lập (D-05).

## 1. Vấn đề

| Vấn đề | Hệ quả | Nguồn |
| --- | --- | --- |
| Doanh nghiệp Việt Nam vận hành bằng giấy, PDF, Word, Excel, ảnh chụp; hệ thống quản trị giả định dữ liệu đã có sẵn | Dashboard rỗng, AI phân tích thiếu dữ liệu, người dùng quay lại Excel | BRD §1, G1 |
| CEO phải hỏi từng người, số liệu vênh nhau, không biết việc đã giao đi đến đâu | Quyết định chậm, thiếu căn cứ | UX §2.1 |
| Nhập liệu lặp lại, báo cáo nhiều nơi | Dữ liệu thiếu, cả hệ thống mất giá trị | UX §2.1, §2.3 |
| AI có thể hành động vượt quyền hoặc đưa số không có nguồn | Mất niềm tin, rủi ro tài chính | BRD G3, G5 |

## 2. Tầm nhìn

AI-EOS là hệ thống quản trị doanh nghiệp AI-first, xây quanh vòng lặp Strategy → KPI/OKR → Initiative → Project → Task → Measurement (BRD §2.1), với AI là actor có danh tính, quyền hạn và audit.

**Lời hứa MVP** (BRD §6): *"CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file."*

**North Star** (BRD §2.1, giữ từ v1.0): quyết định và hành động có outcome được xác minh.

## 3. Người dùng

CEO, Director/Manager, Employee, Reviewer dữ liệu, Admin (UX §2.1), với vai trò hệ thống `ADMIN`, `CEO`, `CFO`, `MANAGER`, `EMPLOYEE` và Reviewer là assignment (D-21). Chi tiết: [Personas.md](../02-requirements/Personas.md).

## 4. Giá trị cốt lõi

| Giá trị | Cơ chế | Nguồn |
| --- | --- | --- |
| Biết ngay, quyết nhanh | Trang chủ theo vai trò, ngoại lệ trước | UX §1, U1 |
| Nhập một lần, nhập ở đâu cũng được | Data Capture: form, ngôn ngữ tự nhiên, tải file, chụp ảnh, import | BRD §3, P09 |
| Tin được con số | Mọi con số có nguồn, độ mới, tài liệu gốc | U3, FR-DF-04, BR-14 |
| AI an toàn | Autonomy L0–L3, write gateway, kill switch, phê duyệt tài chính | D-09…D-12 |

## 5. Phạm vi

| Phạm vi | Nội dung | Nguồn |
| --- | --- | --- |
| MVP (P0) | Data Capture C1–C5; Data Foundation cơ bản; Autonomy L0–L3 + kill switch; Finance Lite; Sales Pipeline Lite; KPI/OKR + check-in; Task; CEO Briefing | BRD §6.1, D-24 |
| Phase 2 / P1 | Hóa đơn/biên lai, hợp đồng, email forwarding, C6–C10, Meeting bot, Performance Cycle, Risk Intelligence, Workflow Engine, Procurement | BRD §6.1, D-17, D-18 |
| Không làm | L4 autonomy trong MVP; thay thế phần mềm kế toán | D-11, BR-18 |

Mức độ đặc tả hiện có của từng module MVP: [PRD.md](../02-requirements/PRD.md) §3.

## 6. Tiêu chí thành công

Chỉ tiêu và phân loại (có nguồn / đề xuất / cần baseline): [Business_OKRs.md](Business_OKRs.md).

## 7. Ràng buộc

Hệ thống nội bộ một doanh nghiệp, Local/Docker Compose (D-03); chi phí thấp, mã nguồn mở (D-07); LLM/OCR qua adapter, chưa chọn provider (D-08); kiến trúc theo ADR-001…013.
