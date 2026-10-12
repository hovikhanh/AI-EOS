# AI-EOS — Phân tích tài liệu nguồn (Giai đoạn 1)

> Phiên bản: 0.2 · Ngày: 12/10/2026 · Trạng thái: **Đã review ở checkpoint 2A** — trạng thái hiện hành của CON/GAP/Q/ASM nằm ở [Decision_Log.md](Decision_Log.md) §5; file này giữ phân tích nguồn gốc.
> Nguồn: `BRD_Review.md` (ký hiệu **BRD**), `UI_UX_Proposal.md` (ký hiệu **UX**). Tham chiếu dạng `BRD §3.5`, `UX §6.2`.
> Danh mục ID chi tiết: xem [Requirements_Traceability.md](Requirements_Traceability.md). File này giữ phân tích và diễn giải; không lặp lại danh sách yêu cầu.

**Quy ước nhãn**

| Nhãn | Ý nghĩa |
| --- | --- |
| `[XN]` | Phát biểu dạng yêu cầu/quy tắc trong BRD v1.1. Được coi là đã xác nhận **với điều kiện** BRD v1.1 đã được phê duyệt (xem Q-02) |
| `[PROPOSED]` | Đề xuất thiết kế (chủ yếu từ UX) hoặc nội dung BRD tự ghi là "gợi ý", "vd.", "đề xuất bộ mặc định" |
| `[ASSUMPTION]` | Giả định, nguồn tự nói cần kiểm chứng |
| `[TBD]` | Thiếu thông tin, chưa thể xác định |
| `[CONFLICT]` | Mâu thuẫn giữa hai nguồn hoặc trong cùng một nguồn |
| `[CẦN XÁC NHẬN]` | Cần người ra quyết định chốt |

---

## 1. Phạm vi và độ tin cậy của nguồn

| Đặc điểm | Phát hiện | Hệ quả |
| --- | --- | --- |
| BRD là bản **rà soát (delta)** của BRD v1.0 | Phần 3 là nội dung mới (Domain 22); Phần 4–6 là bản sửa cho các mục của v1.0 | Không có mô tả đầy đủ của các module lõi |
| BRD v1.0 **không có trong repo** | Được tham chiếu tại §5, 7.6, 9.2, 34, 37–42, 44, 46, 47, 50, 75–77, 82, 87–89, 91; UC-01…05; nhóm user story US-CEO, US-KPI, US-OKR, US-TASK, US-MTG, US-ORG, US-AI, US-PERF, US-FIN, US-SAL, US-STR; 21 domain; nguyên tắc P01–P08 | Các module KPI/OKR, Task, CEO Briefing, Finance Lite, Sales Lite (đều P0) **không có yêu cầu chi tiết** → GAP-01, GAP-04 |
| Tình trạng phê duyệt BRD v1.1 | Tiêu đề "Rà soát, bổ sung", dùng từ "đề xuất". **Cập nhật 2A:** CDA xác nhận BRD v1.1 đã được duyệt (D-01), nhưng **toàn văn BRD v1.1 không có trong repository**; chỉ có `BRD_Review.md` | `[XN]` → `CONFIRMED` cho nội dung kiểm chứng được trong `BRD_Review.md`; nội dung không có trong hai file nguồn vẫn `[CẦN XÁC NHẬN]` |
| UX dựa trên "BRD v1.1 (7 vai trò, 28 domain, ~100 user story)" | Con số này không khớp với BRD_Review | CON-01, CON-13 |
| 5 nội dung nhúng bị mất | Sơ đồ pipeline (BRD §3.3), sơ đồ IA 8 mục (UX §4), 3 wireframe (UX §6.1–6.3) | Chỉ còn phần chú thích; GAP-12 |
| Hiện trạng repo | `AI-EOS/` chưa có code, cấu hình, DB, API | Không có ràng buộc kỹ thuật từ implementation. **Cập nhật 2A:** AI-EOS là dự án mới, độc lập; dự án cũ A-EMS (`Final_Project/A-EMS`, `CyEyes/A-EMS`) nằm ngoài phạm vi và không phải nguồn yêu cầu hay baseline (D-04, D-05) |

## 2. Tóm tắt sản phẩm

- **Định vị:** hệ điều hành doanh nghiệp AI-first (AI-EOS), vòng lặp Strategy → KPI/OKR → Initiative → Project → Task → Measurement; AI là actor có identity, permission, audit (BRD §2.1).
- **North Star** (từ v1.0, được BRD giữ): "quyết định và hành động có outcome được xác minh"; đo bằng Decision Log 30/60/90 ngày (BRD §4.6).
- **Lời hứa MVP (90 ngày):** "CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file" (BRD §6).
- **Thay đổi trọng tâm v1.1:** Domain 22 Data Capture & IDP (P0), Data Foundation, Autonomy L0–L4, bộ chỉ số sức khỏe, AI quality/cost, tuân thủ Việt Nam, MVP thu hẹp (BRD §1).
- **Định hướng UX:** xây quanh 3 hành động — xem ngoại lệ, hỏi AI, duyệt việc AI đã chuẩn bị; module nghiệp vụ lùi về lớp thứ hai (UX §1).
- **Thị trường:** doanh nghiệp Việt Nam vận hành nhiều bằng giấy, PDF, Excel (BRD §1); có dấu hiệu là sản phẩm thương mại ("tốc độ bán hàng" BRD UC-07, "tenant", "bán dạng SaaS" UX §8) → GAP-05.

## 3. Người dùng và vai trò

| Persona (UX §2.1) | Vai trò xuất hiện trong BRD | Ghi chú |
| --- | --- | --- |
| CEO | CEO (US-DC-011) | Phù hợp |
| Director / Manager | Manager (US-DC-002, 004, 005) | UX gộp Director và Manager |
| Employee | Employee, User (US-DC-001, 003) | "User" là vai trò chung |
| Reviewer dữ liệu (kế toán, thư ký, admin phòng ban) | Reviewer (US-DC-006), Thư ký (UC-06) | Reviewer là **chức năng** gán cho nhiều chức danh |
| Admin | Admin (US-DC-007, 008) | Phù hợp |
| — | **Finance** (US-DC-009, UC-08), **Legal/Sales** (US-DC-010), "bộ phận" (US-DC-012) | Không có persona tương ứng |

- UX nói BRD v1.1 có **7 vai trò** nhưng không liệt kê; UX chỉ có 5 persona → CON-13.
- Persona là `[ASSUMPTION]`: "xây từ BRD và giả định, cần kiểm chứng bằng phỏng vấn" (UX §2); lộ trình phỏng vấn 8–10 người ở tuần 1–2 (UX §10.2).
- Người dùng đa vai trò (Director kiêm Reviewer) đổi ngữ cảnh ở thanh trên (UX §4.2).

## 4. Danh mục tính năng theo nhóm

| Nhóm | Nội dung chính | Nguồn | Mức chi tiết | Ưu tiên |
| --- | --- | --- | --- | --- |
| A. Data Capture & IDP (Domain 22) | 10 kênh (C1–C10), pipeline, catalog loại tài liệu, 23 FR, review, vòng đời, bảo mật, học từ chỉnh sửa, tool/entity/agent | BRD §3, §5.1, §5.2 | **Cao** | P0 (C1–C5) / P1 |
| B. Data Foundation | Master data, Data Quality Score, freshness, lineage, event backbone, semantic layer | BRD §4.1 | Trung bình | P0 bản cơ bản |
| C. AI Autonomy | L0–L4, cấu hình tool × vai trò × ngưỡng, hoàn tác, kill switch | BRD §4.2, UX §7.1 | Trung bình | P0 (L0–L3) |
| D. Bộ chỉ số sức khỏe | 18 dòng chỉ số, 5 nhóm, công thức tóm tắt, ngưỡng gợi ý | BRD §4.3 | Trung bình | [TBD] — CON-09 |
| E. AI Quality, Evaluation & Cost | Evaluation Engine, grounding, confidence, feedback, model routing, ngân sách, model-agnostic | BRD §4.4 | Trung bình | [TBD] |
| F. Tuân thủ Việt Nam | Dữ liệu cá nhân, ghi âm họp, hóa đơn điện tử, lưu trữ chứng từ, chữ ký số | BRD §4.5 | Thấp–TB | [TBD]; chữ ký số Phase 2+ |
| G. Mở rộng domain | Workflow Engine, Procurement/Vendor, Contract Lifecycle, Decision Log, Scenario planning, tích hợp VN | BRD §4.6 | Thấp | P1 (Workflow, Procurement); khác [TBD] |
| H. Module lõi MVP | KPI/OKR + check-in, Task, CEO Briefing, Finance Lite, Sales Pipeline Lite, Risk Intelligence | BRD §6.1 (chỉ nêu tên) | **Không có** | P0 / P1 — GAP-04 |
| I. UX & giao diện | 8 nguyên tắc U1–U8, IA 8 mục, 5 luồng F1–F5, 3 wireframe, mẫu AI, design system, responsive, WCAG, bản địa hóa | UX §3–§9 | Cao | `[PROPOSED]` |
| J. NFR | Hiệu năng tài liệu, thông lượng, RPO/RTO, data residency, ngôn ngữ, mobile, khả dụng AI | BRD §5.3 | Trung bình | — |
| K. Change management & đo lường | AI champion, đào tạo, chạy song song, adoption, chỉ số UX | BRD §5.3, UX §10.1 | Trung bình | — |

## 5. Quy tắc nghiệp vụ

Danh sách đầy đủ với ID `BR-xx` nằm trong Traceability §3.1. Các quy tắc quan trọng nhất cho kiến trúc:

1. **Một cửa dữ liệu, ghi chỉ qua Tool Registry** (BR-01, BR-04): mọi lần ghi từ Domain 22 dùng chung permission, approval, audit với hành động AI khác.
2. **Con người luôn duyệt** dữ liệu dưới ngưỡng tin cậy và mọi **trường trọng yếu** (số tiền, số tài khoản, MST, lương, giá trị hợp đồng) trong giai đoạn đầu (BR-03).
3. **Chỉ nới ngưỡng tự ghi** khi loại tài liệu đạt ≥ 98% field accuracy trên ≥ 200 tài liệu đã review và Admin phê duyệt (BR-05).
4. **Tài liệu là dữ liệu, không phải lệnh** (chống prompt injection) (BR-06).
5. **Data Capture Agent không tự ghi dữ liệu tài chính** (BR-08); ghi dữ liệu tài chính mặc định L2 (BR-10).
6. **L4 không bật trong MVP**; L3+ có hoàn tác tối thiểu 24 giờ nếu bản chất cho phép; có kill switch (BR-11, BR-12, BR-13).
7. **Grounding:** con số AI đưa ra phải có nguồn; không có nguồn thì bị chặn hoặc gắn nhãn "ước tính" (BR-14).
8. **AI-EOS không thay thế phần mềm kế toán** (BR-18).
9. **Nhập thủ công luôn hoạt động** khi AI lỗi (BR-21).

## 6. Phân loại nội dung nguồn

| Trạng thái | Số dòng trong ma trận | Thành phần chính |
| --- | --- | --- |
| `[XN]` | 134 | FR-DC, US-DC, UC, kênh C1–C10, BR, FR-DCS, SEC-DC, FR-LRN, FR-DF, FR-AUT, FR-AIQ, CMP, FR-EXT, NFR, CHG, SC, MET từ BRD |
| `[PROPOSED]` | 57 | U1–U8, F1–F5, UX-xx, MET từ UX §10.1, danh sách chỉ số sức khỏe cụ thể (BRD §4.3 ghi "đề xuất bộ mặc định") |
| `[ASSUMPTION]` | 1 (+ 8 ASM) | UX-32 thư viện UI; giả định chung ở mục 9 |
| `[TBD]` | 6 (+ 21 GAP) | Vòng đời tài liệu, Finance/Sales Lite, Governance, IA, chi phí/tài liệu; khoảng trống ở mục 8 |
| `[CONFLICT]` | 19 dòng (14 CON) | Các dòng chịu ảnh hưởng trực tiếp bởi CON-01…14 (mục 7) |
| **Tổng** | **217** | |

Thống kê theo nhóm ID: Traceability §5.

## 7. Mâu thuẫn `[CONFLICT]`

Mỗi mục nêu phương án nhưng **không tự quyết**. Phương án đánh dấu (★) chỉ là khuyến nghị của người phân tích.

### CON-01 — Số lượng domain
- **BRD:** 21 domain hiện có + Domain 22 (BRD §3); đề xuất thêm Procurement/Vendor và Contract Lifecycle (§4.6).
- **UX §1, §4:** "28 domain", gộp vào 8 mục điều hướng.
- **Tác động:** không lập được danh sách module, ma trận quyền, mô hình dữ liệu.
- **Phương án:** (a) 28 là số của bản BRD v1.1 đầy đủ chưa được chia sẻ → cần nhận tài liệu (★); (b) UX đếm sai → dùng 22 + các domain mới của §4.6.
- **Cần quyết:** Q-10.

### CON-02 — Autonomy L4 trong MVP
- **BRD §4.2, §6.1:** L4 "Không bật trong MVP"; MVP P0 chỉ L0–L3.
- **UX §7.1:** thiết kế mẫu giao diện L4 (báo cáo hoạt động tuần) với ví dụ "Phân loại email, gắn nhãn tài liệu"; feed "AI đã làm" ghi L3/L4.
- **Tác động:** phạm vi thiết kế và phát triển MVP.
- **Phương án:** (a) giữ thiết kế L4 trong design system nhưng tắt ở MVP (★); (b) loại L4 khỏi thiết kế MVP. Ngoài ra, "phân loại tài liệu" theo BRD §3.9 là READ (L0), không cần L4.
- **Cần quyết:** Q-07.

### CON-03 — Ghi dữ liệu tài chính ở mức L3
- **BRD §4.2:** "Ghi dữ liệu tài chính" mặc định **L2**; §3.9: Data Capture Agent "không tự ghi dữ liệu tài chính".
- **UX §7.1:** ví dụ L3 "nhập hóa đơn đã duyệt"; UX F2 bước 5 "Enter để duyệt → ghi vào domain đích; toast Hoàn tác".
- **Cách hiểu có thể dung hòa:** người đã duyệt (L2), việc commit sau đó chỉ là thực thi kèm hoàn tác. Nhưng nguồn chưa nói rõ.
- **Tác động:** cấu hình Approval Matrix, ngữ nghĩa hoàn tác của bút toán tài chính (liên quan CON-12).
- **Cần quyết:** Q-07.

### CON-04 — Kill switch: ai bật và hiệu lực
- **BRD §4.2:** "tắt **toàn bộ** hành động WRITE/EXECUTION của AI chỉ bằng một thao tác của **Admin**".
- **UX §7.2:** kill switch cho "**Admin và CEO**"; khi bật, "mọi thẻ L3/L4 chuyển sang **L2**" (AI vẫn soạn, người xác nhận).
- **Tác động:** quyền, hành vi hệ thống khi có sự cố, thiết kế Tool Registry.
- **Phương án:** (a) theo BRD — chặn mọi WRITE/EXECUTION do AI khởi tạo; (b) theo UX — hạ cấp về L2; (c) hai mức: "hạ cấp về L2" và "dừng hoàn toàn".
- **Cần quyết:** Q-06.

### CON-05 — Email forwarding trong luồng MVP
- **BRD §3.2:** C6 Email forwarding là **Phase 2**; US-DC-012 ưu tiên **P1**; §6.1 "email capture" là P1.
- **UX §5 F2 bước 1:** "…hoặc chuyển tiếp email" trong luồng F2, mà UX nói 5 luồng "bao phủ các use case MVP".
- **Cần quyết:** Q-08.

### CON-06 — Hóa đơn và chứng từ chi phí trong MVP
- **BRD §3.4, §6.1:** hóa đơn GTGT, biên lai, phiếu chi là **Phase 2 / P1**; US-DC-009 (Finance chụp hóa đơn) là P1.
- **UX:** chỉ số UX MVP "review một hóa đơn 6 trường ≤ 60 giây" (§6.2, §10.1); Employee "gửi chứng từ" (§2.1, gắn US-DC-009); mobile "chụp chứng từ" (§6.3).
- **Liên quan:** Finance Lite là P0 nhưng chỉ "nhập tay hoặc import" (BRD §6.1). Mục tiêu review ≤ 60 giây trong BRD US-DC-006 áp cho **mọi** tài liệu, không riêng hóa đơn.
- **Phương án:** (a) giữ BRD; đổi tài liệu chuẩn cho chỉ số UX sang loại MVP (vd. biên bản họp); (b) đưa hóa đơn/biên lai vào MVP (tăng phạm vi, tác động FR-DC-14, CMP-04).
- **Cần quyết:** Q-08.

### CON-07 — Ngưỡng độ tin cậy: định tuyến và hiển thị
- **BRD FR-DC-15:** ngưỡng định tuyến cấu hình **theo loại tài liệu và theo trường**.
- **UX §6.2:** 3 mức hiển thị, mặc định ≥ 90% / 60–89% / < 60%, Admin chỉnh **theo loại tài liệu**.
- **Vấn đề:** chưa rõ ngưỡng hiển thị và ngưỡng tự ghi là một hay hai cấu hình; UX thiếu cấu hình theo trường.
- **Cần quyết:** Q-14.

### CON-08 — Nền tảng mobile
- **BRD §5.3:** "PWA hoặc app".
- **UX §9.1:** đề xuất web responsive + PWA, chưa làm native. Nhưng §6.3 yêu cầu **xác thực sinh trắc học** cho mục tài chính trên ngưỡng và **chế độ ngoại tuyến**; UX tự ghi native "cân nhắc nếu cần sinh trắc học hoặc ngoại tuyến sâu".
- **Phương án:** (a) PWA + WebAuthn (passkey/sinh trắc học nền tảng) + offline queue bằng Service Worker; (b) native app.
- **Cần quyết:** Q-12 (trùng câu hỏi UX §10.3-2).

### CON-09 — Bộ chỉ số sức khỏe
- **BRD §1:** 4 nhóm (tài chính, khách hàng, vận hành, con người); **§4.3:** bảng có thêm nhóm **Chiến lược**.
- Nhiều chỉ số cần dữ liệu ngoài phạm vi MVP: DIO (tồn kho — không có domain), CAC/LTV/NPS, NRR, DSO/DPO (cần công nợ — P1), turnover (HR), workload (chấm công — Phase 2).
- **Tác động:** CEO Dashboard và Briefing MVP không tính được phần lớn chỉ số.
- **Cần quyết:** Q-13 — tập chỉ số MVP. UX §6.1 đề xuất 4 ô mặc định: doanh thu, dòng tiền, OKR, task trễ.

### CON-10 — Số kênh trong pipeline
- Chú thích sơ đồ BRD §3.3: "4 kênh, 4 bước xử lý, 1 cổng duyệt"; bảng §3.2 có **5 kênh MVP** (C1–C5). Sơ đồ bị mất nên không đối chiếu được. Mức độ: thấp. → Q-22.

### CON-11 — Tham chiếu user story đã hạ ưu tiên
- UX §2.2 gắn US-PERF-001 vào nhóm "Thiết lập" trong khi Performance Cycle đầy đủ hạ xuống **P1** (BRD §6.1).
- UX F3 tham chiếu UC-02 (AI join Google Meet), đã hạ xuống **P1**; UC-06 thay thế ở MVP. Mức độ: thấp. → Q-22.

### CON-12 — Hoàn tác và tính bất biến của audit
- **BRD §4.2:** L3+ có hoàn tác ≥ 24 giờ "nếu bản chất hành động cho phép". **UX:** hoàn tác trong feed 24 giờ, hoàn tác theo lô cho L4.
- **BRD FR-DC-05, §4.5:** audit đầy đủ; lưu chứng từ kế toán theo luật.
- **Chưa định nghĩa:** hoàn tác là xóa, đảo bút toán hay tạo phiên bản bù; hành động nào "không cho phép" hoàn tác (gửi thông báo, email ra ngoài); trạng thái tài liệu sau hoàn tác (vòng đời §3.6 không có).
- **Cần quyết:** Q-11.

### CON-13 — Vai trò và persona
- UX nói BRD v1.1 có **7 vai trò**; UX chỉ định nghĩa **5 persona**; user story BRD dùng thêm Finance, Legal/Sales, Thư ký, "bộ phận".
- **Tác động:** RBAC, trang chủ theo vai trò (UX §4.1), Personas.md.
- **Cần quyết:** Q-09.

### CON-14 — Màn hình ngoài 4 việc cốt lõi trên mobile
- **UX §6.3:** "Mọi thứ khác (cấu hình, báo cáo sâu, quản trị) **chỉ có trên desktop**".
- **UX §9.1:** < 768 px "các màn khác hiển thị **chế độ chỉ đọc**".
- **BRD FR-DC-06:** mobile cho check-in KPI/OKR, chi phí, task — "chi phí" phụ thuộc CON-06.
- **Cần quyết:** Q-21.

## 8. Khoảng trống và thông tin còn thiếu `[TBD]`

| ID | Khoảng trống | Ảnh hưởng tới tài liệu Giai đoạn 2 | Câu hỏi |
| --- | --- | --- | --- |
| GAP-01 | BRD v1.0 không có (các mục và ID được tham chiếu, xem §1) | PRD, SRS, Database cho module lõi | Q-01 |
| GAP-02 | Không rõ BRD v1.1 đã được phê duyệt chưa | Mọi `[XN]` | Q-02 |
| GAP-03 | Danh sách 7 vai trò và ma trận quyền RBAC/ABAC | SRS, API (authz), Architecture | Q-09 |
| GAP-04 | Không có yêu cầu chi tiết cho KPI/OKR, Task, CEO Briefing, Finance Lite, Sales Pipeline Lite, Risk Intelligence | PRD, SRS, DB, API | Q-01, Q-03 |
| GAP-05 | Mô hình triển khai: SaaS đa tenant hay nội bộ một công ty; cách cô lập dữ liệu tenant | Architecture, DB, ADR | Q-04 |
| GAP-06 | Tech stack, hạ tầng, nhà cung cấp OCR/LLM chưa chốt (chỉ có giả định shadcn/ui, Model Gateway model-agnostic, hỗ trợ on-premise) | Architecture, CLAUDE.md, ADR | Q-05 |
| GAP-07 | Vòng đời tài liệu (BRD §3.6) thiếu: trạng thái nháp (FR-DC-04), đường straight-through (bỏ qua NEEDS_REVIEW), REJECTED → xử lý lại hay kết thúc, FAILED → retry, trạng thái sau hoàn tác, tách/gộp (FR-DC-22) | SRS, DB | Q-11 |
| GAP-08 | Danh sách "trường trọng yếu" theo loại tài liệu; ngưỡng giá trị cho Autonomy (5 triệu là ví dụ); "ngưỡng" sinh trắc học trên mobile | SRS, cấu hình | Q-07 |
| GAP-09 | Không có yêu cầu xác thực: SSO, MFA, chính sách phiên, quản lý mật khẩu, API key cho C10 | SRS, API, Architecture | Q-15 |
| GAP-10 | Tích hợp MVP chưa rõ: "đồng bộ lịch" (UC-06, F1) dùng Google Calendar hay M365? Thông báo qua kênh nào? | Architecture, API | Q-16, Q-17 |
| GAP-11 | Kênh thông báo (in-app, email, push PWA, Zalo/Slack/Teams) | UX Flows, Architecture | Q-17 |
| GAP-12 | 5 nội dung nhúng bị mất (pipeline, IA, 3 wireframe) | UX_Flows, Architecture | Q-01 |
| GAP-13 | Dữ liệu tham chiếu đơn vị hành chính mới (FR-DC-13): nguồn, cách cập nhật | DB, SRS | — |
| GAP-14 | Ngân sách AI: giá trị trần chi phí/tài liệu, ngân sách theo tenant/phòng ban | SRS, NFR | Q-05 |
| GAP-15 | Chính sách lưu trữ cho các loại khác ngoài chứng từ kế toán và CV; hồ sơ đánh giá tác động (DPIA) | SRS, DB | — |
| GAP-16 | Nguồn dữ liệu cho từng chỉ số sức khỏe ở MVP | PRD, Database | Q-13 |
| GAP-17 | Nội dung 8 mục IA: Finance nằm ở "Kinh doanh"? Quản trị gồm những gì? | UX_Flows | Q-10 |
| GAP-18 | SLA review và quy tắc escalation (BRD chỉ ghi "vd. 1 ngày làm việc") | SRS | — |
| GAP-19 | Bộ nhận diện thương hiệu | Design system | Q-18 |
| GAP-20 | Người tham gia phỏng vấn và usability test | Personas, Test Plan | Q-20 |
| GAP-21 | NFR nền tảng chung chưa có: availability SLA, độ trễ API, số người dùng đồng thời, mã hóa at-rest/in-transit, quy mô dữ liệu | SRS, Architecture, Test Plan | Q-05 |

## 9. Giả định `[ASSUMPTION]`

| ID | Giả định | Nguồn |
| --- | --- | --- |
| ASM-01 | 5 persona xây từ BRD và giả định, chưa phỏng vấn | UX §2 |
| ASM-02 | Số liệu trong wireframe và luồng (82%, 130%…) chỉ là minh họa | UX §6 |
| ASM-03 | Ngưỡng cảnh báo chỉ số sức khỏe là "gợi ý", doanh nghiệp tinh chỉnh được | BRD §4.3 |
| ASM-04 | Thư viện UI shadcn/ui trên Radix là giả định, cần team kỹ thuật xác nhận | UX §8.3 |
| ASM-05 | Ngưỡng hiển thị độ tin cậy mặc định 90/60 | UX §6.2 |
| ASM-06 | Các giá trị có "vd." trong BRD (5 triệu, SLA 1 ngày, invoices@…, 20 triệu trong workflow) là ví dụ, không phải quy tắc | BRD §3.2, §3.5, §4.2, §4.6 |
| ASM-07 | Phần 3–6 của BRD_Review được dự định chèn vào BRD chính thức, nên được coi là yêu cầu | BRD §1 |
| ASM-08 | Wireframe dùng "anh" khi AI nói với CEO là ví dụ; cách xưng hô là cấu hình | UX §9.3 |

## 10. Câu hỏi cần quyết định

| ID | Ưu tiên | Câu hỏi | Liên quan |
| --- | --- | --- | --- |
| Q-01 | **Cao** | Có cung cấp BRD v1.0 (và bản v1.1 đầy đủ, các hình nhúng) không? Nếu không, Giai đoạn 2 sẽ để `[TBD]` cho KPI/OKR, Task, CEO Briefing, Finance Lite, Sales Lite. | GAP-01, 04, 12 |
| Q-02 | **Cao** | Nội dung BRD v1.1 (Phần 3–6, gồm ma trận ưu tiên §6.1) đã được phê duyệt chưa? | GAP-02 |
| Q-03 | **Cao** | Phạm vi tài liệu Giai đoạn 2: chi tiết cho MVP P0, còn P1/P2 ở mức roadmap? | GAP-04 |
| Q-04 | **Cao** | Sản phẩm là SaaS đa tenant hay hệ thống nội bộ một doanh nghiệp? | GAP-05 |
| Q-05 | **Cao** | Đã có ràng buộc về tech stack, cloud/on-premise, nhà cung cấp LLM/OCR, ngân sách AI chưa? Hay Giai đoạn 2 đề xuất dưới dạng `[PROPOSED]` + ADR? | GAP-06, 14, 21 |
| Q-06 | **Cao** | Kill switch: ai được bật, và chặn hoàn toàn hay hạ về L2? | CON-04 |
| Q-07 | **Cao** | L4 có nằm trong thiết kế MVP không? Commit dữ liệu tài chính sau khi người đã duyệt là L2 hay L3? Danh sách trường trọng yếu và ngưỡng giá trị? | CON-02, 03; GAP-08 |
| Q-08 | **Cao** | Email forwarding và hóa đơn/biên lai có vào MVP không? | CON-05, 06 |
| Q-09 | **Cao** | Danh sách vai trò chính thức (7?) và ánh xạ sang persona? | CON-13; GAP-03 |
| Q-10 | TB | Danh sách domain chính thức (22 hay 28) và ánh xạ vào 8 mục IA? | CON-01; GAP-17 |
| Q-11 | TB | Hoàn tác nghĩa là gì với từng loại hành động (xóa, đảo, bù)? Vòng đời tài liệu đầy đủ? | CON-12; GAP-07 |
| Q-12 | TB | MVP web + PWA (UX đề xuất) hay cần native? Sinh trắc học và offline có trong MVP không? | CON-08 |
| Q-13 | TB | Tập chỉ số sức khỏe cho MVP và nguồn dữ liệu của từng chỉ số? | CON-09; GAP-16 |
| Q-14 | TB | Ngưỡng hiển thị độ tin cậy và ngưỡng tự ghi là một hay hai cấu hình; có cấu hình theo trường không? | CON-07 |
| Q-15 | TB | Yêu cầu xác thực: SSO (Google/M365), MFA? | GAP-09 |
| Q-16 | TB | Tích hợp lịch và tích hợp khác trong MVP? | GAP-10 |
| Q-17 | TB | Briefing/duyệt có đẩy qua Zalo/Slack/Teams không? (UX §10.3-4) | GAP-11 |
| Q-18 | Thấp | Đã có bộ nhận diện thương hiệu chưa? (UX §10.3-1) | GAP-19 |
| Q-19 | Thấp | AI xưng hô "anh/chị" hay "bạn" mặc định? (UX §10.3-5) | ASM-08 |
| Q-20 | Thấp | Ai tham gia phỏng vấn và test (≥ 2 người/persona)? (UX §10.3-3) | GAP-20 |
| Q-21 | TB | Trên mobile, màn ngoài 4 việc cốt lõi là ẩn hay chỉ đọc? | CON-14 |
| Q-22 | Thấp | Xác nhận CON-10 (số kênh) và CON-11 (US-PERF-001, UC-02) chỉ là lỗi tham chiếu, sửa theo BRD §6.1? | CON-10, 11 |

## 11. Đề xuất cho Giai đoạn 2 (sau khi có trả lời)

- Câu hỏi **Cao** (Q-01…Q-09) chặn PRD, SRS, Database, API; nên trả lời trước.
- Nếu Q-05 chưa có ràng buộc, Architecture và ADR sẽ ở trạng thái `[PROPOSED]`, mỗi lựa chọn công nghệ một ADR. **Cập nhật 2A:** nguyên tắc tích hợp LLM/OCR qua adapter và hạ tầng Local/Docker Compose đã chốt (D-03, D-07); stack cụ thể chưa được ghi nhận trong nguồn (D-06).
- OKR định lượng: nguồn chỉ có chỉ số sản phẩm/vận hành (MET-xx), **không có** OKR kinh doanh (doanh thu, khách hàng). Business_OKRs.md sẽ dùng MET-xx làm Key Result ứng viên và để `[TBD]` phần kinh doanh.

## 12. Ghi chú hiệu chỉnh

| Phiên bản | Thay đổi |
| --- | --- |
| 0.1 | Phân tích Giai đoạn 1 |
| 0.2 | Bổ sung giới hạn nguồn (toàn văn BRD v1.1 không có) và ranh giới dự án (AI-EOS độc lập, A-EMS ngoài phạm vi) ở mục 1 và 11. Phân tích, CON-01…14, GAP-01…21, ASM, Q-01…22 giữ nguyên; trạng thái hiện hành xem Decision_Log §5. Phát hiện mới ở checkpoint 2A (CON-15…19, GAP-22…25, Q-23…27) chỉ ghi trong Decision_Log; CON-15…18 và GAP-22…25 là `[LEGACY FINDING — A-EMS]` |
