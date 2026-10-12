# AI-EOS — Product Requirements Document (PRD)

> Phiên bản: 1.1 · Ngày: 12/10/2026 · Trạng thái: **Stage 2B — CDA duyệt có điều kiện (12/10/2026)**. Thay đổi 1.1: AMD-01 (D-37), AMD-02 (D-38), mặc định an toàn D-39, Sales Lite chưa triển khai (D-40) — ghi chú "[1.1]" trong mục 3.1 và epic E3, E5, E6, E7
> Nguồn: BRD (`BRD_Review.md`), UX (`UI_UX_Proposal.md`), [Decision_Log](../00-source/Decision_Log.md) 0.6, [Requirements_Traceability](../00-source/Requirements_Traceability.md). Toàn văn BRD v1.1 không có trong repository (D-01).
> Đặc tả phần mềm chi tiết: [SRS.md](SRS.md). Luồng màn hình: [UX_Flows.md](UX_Flows.md). Kiến trúc: [Architecture.md](../03-architecture/Architecture.md).

**Quy ước**
- Trạng thái yêu cầu: `CONFIRMED` (có nguồn đã duyệt hoặc quyết định CDA) · `PROPOSED` · `NEEDS_CONFIRMATION` · `DEFERRED`. Story có trạng thái `CONFIRMED` nghĩa là **căn cứ** đã được xác nhận, không phải CDA đã duyệt từng câu chữ của story.
- User story mới (Stage 2B) dùng tiền tố `US-IAM`, `US-GOAL`, `US-WRK`, `US-BRF`, `US-FNL`, `US-SLS`, `US-AIC`, `US-PRV` để không trùng với mã BRD v1.0 chưa có nội dung (US-KPI, US-TASK, US-FIN, US-AI, US-ORG…; Requirements_Traceability §6).
- `[CẦN XÁC NHẬN]` = không có nguồn; mặc định an toàn được ghi rõ.
- `F1`…`F5` = luồng UX; `CDA-F1`…`CDA-F7` = quy tắc tài chính CDA (D-14).
- Acceptance criteria (AC) viết dạng Given–When–Then; AC chi tiết hơn ở SRS.

---

## 1. Tầm nhìn và vấn đề

Xem [Product_Vision.md](../01-strategy/Product_Vision.md). Lời hứa MVP: CEO biết công ty đang đạt mục tiêu đến đâu, vì sao, và giao việc được ngay — với dữ liệu nhập vào dễ như gửi một file (BRD §6). Chỉ số thành công: [Business_OKRs.md](../01-strategy/Business_OKRs.md).

## 2. Người dùng và quyền ở mức nghiệp vụ

Persona: [Personas.md](Personas.md). Role hệ thống `ADMIN`, `CEO`, `CFO`, `MANAGER`, `EMPLOYEE`; Reviewer là assignment (D-21 R1). Ma trận permission chi tiết: Architecture §6.

| Quy tắc nghiệp vụ về quyền | Nguồn |
| --- | --- |
| Mỗi người chỉ thấy dữ liệu trong phạm vi: CEO toàn công ty; Manager đơn vị và cấp dưới; Employee của mình, team, mục tiêu cha; Reviewer tài liệu được giao | UX §4.1 |
| Mục không có quyền bị ẩn hẳn | UX-08 |
| Admin quản trị hệ thống, không mặc định xem dữ liệu nghiệp vụ, lương, dữ liệu cá nhân, không duyệt tài chính | R4, D-21 |
| CEO không duyệt tài chính mặc định | R2 |
| Quyền tài chính theo assignment, không theo tên role | R5 |
| Người tạo không tự duyệt giao dịch tài chính | D-14 |
| Dữ liệu nhân sự nhạy cảm có quyền riêng, hiện chưa giao cho ai | R6 |

## 3. Phạm vi

### 3.1. MVP (P0) và mức đặc tả

| Module | Nội dung MVP | Mức đặc tả 2B | Câu hỏi mở chính | Nguồn |
| --- | --- | --- | --- | --- |
| M1 Tài khoản và quyền | Lời mời, đăng nhập, MFA cho Admin, role, assignment, audit | Đầy đủ | R6 | D-21, D-22 |
| M2 Data Capture | C1 form, C2 ngôn ngữ tự nhiên, C3 tải file, C4 chụp ảnh, C5 import; review; lineage | Đầy đủ cho loại tài liệu MVP | D-16, D-29, Q-20 | BRD §3, SC-01 |
| M3 KPI/OKR + check-in | Dựng từ tài liệu, duyệt trước khi kích hoạt, xem theo phạm vi, đo lường, check-in | **Một phần** — thuộc tính và luồng có nguồn; công thức, trạng thái mở rộng, nhịp check-in chưa có | Q-28…Q-32 | US-DC-005, BRD §3.4, F4 |
| M4 Task và biên bản họp | Tạo task từ biên bản, giao việc, xem/cập nhật task | **Một phần** — task có owner, hạn, nguồn, hoàn thành; trạng thái mở rộng, workload, lịch chưa có | Q-33…Q-35, Q-41 | US-DC-004, UC-06, F1, F3 |
| M5 CEO Briefing / Trang chủ | Dòng tóm tắt, 4 ô chỉ số có độ mới và nguồn, "Cần anh quyết", "AI đã làm" | **Một phần** — bố cục và quy tắc nguồn/độ mới có; công thức ô, nội dung "Rủi ro", lịch tạo briefing chưa có | Q-36, Q-37, D-28 | UX §6.1, F1, FR-DF-03 |
| M6 Finance Lite | Doanh thu, chi phí, số dư tiền mặt; duyệt; đảo; điều chỉnh; kỳ báo cáo; runway | Đầy đủ cho quy trình; định nghĩa runway, danh mục chưa có | Q-39, Q-40, Q-42 | SC-04, D-12…D-14 |
| M7 Sales Pipeline Lite | CEO xem pipeline | **Chưa đặc tả được**; [1.1] chưa thuộc phạm vi triển khai MVP (D-40) | Q-38 | SC-05, FR-HM-04 |
| M8 AI control | Autonomy L0–L3, bản nháp L2, hoàn tác L3, kill switch, hỏi AI có nguồn, phản hồi | Đầy đủ | D-08 | D-09…D-11, FR-AIQ |

### 3.2. Ngoài MVP

| Hạng mục | Lý do | Nguồn |
| --- | --- | --- |
| L4 autonomy | Không thuộc MVP | D-11 |
| Hóa đơn, biên lai, phiếu chi, hợp đồng, báo giá/PO, sao kê, CV, danh thiếp, chấm công | Phase 2 | D-17, BRD §3.4 |
| Email forwarding, chat bot, Drive sync, API/Webhook nhập liệu (C6–C10) | Phase 2 | D-18, BRD §3.2 |
| Meeting bot Google Meet, Performance Cycle, Risk Intelligence, Workflow Engine, Procurement, Contract Lifecycle | P1 | BRD §6.1 |
| SSO, tích hợp lịch ngoài, kênh thông báo ngoài ứng dụng | DEFERRED/chưa chốt | D-30, D-31, D-32 |
| Thay thế phần mềm kế toán | Không làm | BR-18 |

### 3.3. Roadmap theo phase

| Phase | Nội dung | Nguồn |
| --- | --- | --- |
| MVP (90 ngày) | Mục 3.1 | BRD §6, UX §10.2 |
| P1 / Phase 2 | Hóa đơn, hợp đồng, email capture, XML hóa đơn cùng Finance đầy đủ; Procurement, Workflow Engine; Risk Intelligence; Meeting bot; Performance Cycle | BRD §6.1 |
| P2 | Governance | BRD §6.1 |

---

## 4. Epics và user stories

### E1 — Tài khoản và quyền (M1)

**US-IAM-01** — Là người được mời, tôi muốn kích hoạt tài khoản bằng lời mời dùng một lần để không ai phải gửi mật khẩu cho tôi. · P0 · Nguồn A1 · CONFIRMED
- Given lời mời còn hạn, chưa dùng, When tôi đặt mật khẩu hợp lệ, Then tài khoản kích hoạt và lời mời không dùng lại được.
- Given lời mời đã dùng, hết hạn hoặc bị thu hồi, When tôi mở link, Then tôi nhận cùng một thông báo "lời mời không còn hiệu lực".

**US-IAM-02** — Là Admin, tôi muốn đăng nhập bằng mật khẩu và mã MFA để tài khoản quản trị khó bị chiếm. · P0 · A2, ADR-006 · CONFIRMED
- Given tôi có role ADMIN chưa đăng ký MFA, When đăng nhập, Then tôi phải đăng ký MFA trước khi dùng bất kỳ chức năng nào.
- Given tôi nhập sai nhiều lần, Then tài khoản bị giới hạn/khóa tạm và thông báo lỗi không tiết lộ email có tồn tại hay không.

**US-IAM-03** — Là Admin, tôi muốn tạo tài khoản, gán role và assignment có lý do để quyền luôn đúng người và có dấu vết. · P0 · A1, A3–A5, R7 · CONFIRMED
- Given tôi xác thực lại, When gán role với lý do, Then thay đổi có hiệu lực ngay, phiên của người bị đổi bị thu hồi, audit ghi lại.
- Given tôi đổi role của chính mình, hoặc gán `ADMIN` và `CFO` cho cùng người, hoặc gỡ Admin hoạt động cuối cùng, Then hệ thống từ chối và giải thích lý do.

**US-IAM-04** — Là người vận hành máy chủ, tôi muốn tạo Admin đầu tiên bằng lệnh một lần để không có tài khoản mặc định. · P0 · A2, A6 · CONFIRMED
- Given đã có Admin hoạt động, When chạy lệnh bootstrap, Then lệnh từ chối.

### E2 — Data Capture (M2)

Sử dụng user story nguồn **US-DC-001, 002, 003, 004, 005, 006, 007, 008, 011** (BRD §5.1, P0). US-DC-009, 010, 012 là DEFERRED. AC bổ sung:

- **US-DC-001:** Given form của một entity, When nhập trường sai định dạng/thiếu bắt buộc, Then báo lỗi trước khi lưu; When có bản ghi có khả năng trùng, Then cảnh báo; When lưu nháp, Then mở lại được (FR-DC-01, 02, 04).
- **US-DC-002:** Given tôi gõ "Ghi chi phí tiếp khách 2,5 triệu hôm qua, khách ABC", When AI dựng bản ghi, Then tôi thấy bản ghi dự kiến và **không có gì được ghi** cho tới khi tôi xác nhận (FR-DC-03). Ghi tài chính sau xác nhận vẫn qua duyệt tài chính (D-12).
- **US-DC-003:** Given tôi tải PDF/DOCX/ảnh/XLSX hợp lệ ≤ 50 MB, When xử lý xong, Then tài liệu được phân loại và trích xuất, tôi được thông báo; file sai định dạng thật sự (theo nội dung) bị từ chối (FR-DC-07, 08, 09).
- **US-DC-006:** Given trích xuất có trường trọng yếu, When Reviewer chấp nhận tất cả mà chưa đi qua trường trọng yếu, Then hệ thống không cho chấp nhận (FR-DC-16, UX-15).
- **US-DC-007:** Given file nhân sự có dòng lỗi, When import, Then dòng hợp lệ được ghi, dòng lỗi được báo theo số dòng và xuất được file lỗi (FR-DC-18).
- **US-DC-008:** Given loại tài liệu MVP, When Admin bật tự ghi khi chưa đạt ≥ 98% trên ≥ 200 tài liệu đã review, Then hệ thống từ chối (BR-05).
- **US-DC-011:** Given một con số trên Trang chủ, When CEO bấm, Then thấy công thức/nguồn, thời điểm cập nhật, bản ghi và tài liệu gốc (nếu có) (FR-DF-04, U3).

### E3 — KPI/OKR (M3)

**US-GOAL-01** — (làm rõ US-DC-005) Là Manager, tôi muốn mục tiêu dựng từ file kế hoạch ở trạng thái nháp và chỉ được kích hoạt sau khi tôi duyệt. · P0 · US-DC-005 · CONFIRMED
- Given AI dựng Objective/KR/KPI từ tài liệu, Then chúng ở trạng thái nháp, không xuất hiện trong chỉ số và Briefing.
- When người có quyền duyệt kích hoạt, Then chúng trở thành hiệu lực và có liên kết tới tài liệu gốc.
- [1.1] Kích hoạt cần thao tác rõ ràng của người được giao permission `goals.activate` (D-39); ai được giao chờ Q-28.

**US-GOAL-02** — Là người dùng, tôi muốn xem cây mục tiêu trong phạm vi của mình để thấy việc mình đóng góp vào đâu. · P0 · UX §4.1, §4.2 (breadcrumb), BRD §2.1 · CONFIRMED
- Given tôi là Employee, Then tôi thấy mục tiêu của mình và mục tiêu cha; không thấy mục tiêu của đơn vị khác.

**US-GOAL-03** — Là Employee, tôi muốn check-in KR (giá trị, độ tự tin, blocker) trong ≤ 30 giây. · P0 · F4, FR-DC-06 · CONFIRMED (luồng) / NEEDS_CONFIRMATION (nhịp, Q-30)
- Given KR của tôi, When gửi check-in, Then giá trị, độ tự tin, blocker được lưu với thời điểm và Manager thấy trong tổng hợp team.
- Giá trị "điền sẵn từ task đã xong" chỉ khi Q-29 có quy tắc; mặc định: điền giá trị check-in gần nhất.

**US-GOAL-04** — Là Manager, tôi muốn tải báo cáo kết quả định kỳ để AI ghi giá trị thực tế của KPI/KR. · P0 · BRD §3.4 (Báo cáo kết quả định kỳ, MVP) · CONFIRMED
- Given báo cáo được trích xuất và review, When commit, Then mỗi giá trị thực tế ghi vào đúng chỉ số và kỳ, có lineage.
- "Cập nhật achievement, cảnh báo lệch" (BRD §3.4): công thức và ngưỡng chưa có (Q-29) → MVP chỉ hiển thị giá trị thực tế so với target, **không** hiển thị % đạt hay cảnh báo cho tới khi Q-29 được trả lời.

### E4 — Task và biên bản họp (M4)

**US-WRK-01** — (làm rõ US-DC-004, UC-06) Là người chủ trì, tôi muốn biến biên bản họp thành task có owner, hạn, trích đoạn gốc. · P0 · CONFIRMED
- Given bảng action item đã khớp tên với danh bạ, When tôi bấm "Giao việc", Then mỗi người nhận task kèm trích đoạn gốc và thông báo in-app.
- Given một dòng chưa có người phụ trách hoặc hạn, Then không giao được dòng đó cho tới khi bổ sung (US-DC-004 yêu cầu owner, deadline).

**US-WRK-02** — Là người dùng, tôi muốn xem task theo phạm vi: CEO tổng quan thực thi, Manager team, Employee task của tôi. · P0 · UX §4.1 · CONFIRMED

**US-WRK-03** — Là owner task, tôi muốn đánh dấu hoàn thành trong ≤ 10 giây. · P0 · U5, FR-HM-05 (tỷ lệ hoàn thành đúng hạn) · CONFIRMED
- When tôi đánh dấu xong, Then thời điểm hoàn thành được ghi để tính "đúng hạn".

**US-WRK-04** — Là người dùng, tôi muốn tạo task thủ công qua form có kiểm tra tức thì. · P0 · FR-DC-01 · CONFIRMED

**US-WRK-05** — Là CEO, tôi muốn xác nhận action card AI soạn sẵn (task, owner, hạn) và hoàn tác được. · P0 · F1, BR-10 (task là L3 mặc định), BR-11 · CONFIRMED
- Given kill switch bật, Then action card luôn cần tôi xác nhận (L2).
- "Đặt lịch" trong F1: chưa có căn cứ trong MVP (Q-35, D-31) — không thuộc AC.

Trạng thái task ngoài "chưa xong/đã xong", luồng "gửi duyệt" task, workload/quá tải (F5): chưa có căn cứ → Q-33, Q-34; không thuộc AC MVP.

### E5 — CEO Briefing (M5)

**US-BRF-01** — Là CEO, tôi muốn màn đầu tiên trả lời "có gì cần tôi?" bằng một dòng tóm tắt và 4 ô chỉ số có độ mới dữ liệu. · P0 · UX §6.1, U1, FR-DF-03 · CONFIRMED (bố cục) / NEEDS_CONFIRMATION (công thức ô, D-28, Q-37)
- Given dữ liệu của ô cũ hơn ngưỡng, Then ô hiện nhãn dữ liệu cũ.
- Given một ô chưa có dữ liệu (vd. chưa có giao dịch ghi sổ), Then ô hiện trạng thái trống kèm gợi ý cách bổ sung, không hiện số 0 giả.
- Bốn ô mặc định: doanh thu, dòng tiền, OKR, task trễ (UX §6.1); CEO chọn được ô khác trong danh sách chỉ số có sẵn.
- [1.1] Bốn ô là `PROPOSED`: hiển thị nhãn "chưa chính thức", không có cảnh báo (D-39).

**US-BRF-02** — Là CEO, tôi muốn khối "Cần anh quyết" liệt kê việc chờ chính tôi, có nút hành động tại chỗ. · P0 · UX §6.1, U6 · CONFIRMED (khối) / NEEDS_CONFIRMATION (loại mục, Q-36)
- MVP mặc định an toàn: chỉ gồm bản nháp hành động AI chờ CEO xác nhận và mục khác đã giao cho CEO trong hệ thống.

**US-BRF-03** — Là CEO, tôi muốn thấy "AI đã làm" tách khỏi việc của người, có lối hoàn tác. · P0 · UX §6.1, U4, UX-27 · CONFIRMED

**US-BRF-04** — [1.1] Khi kill switch bật, không tạo Briefing mới; Trang chủ hiện bản gần nhất kèm nhãn "AI đang tạm dừng" (D-38). — Là CEO, tôi muốn nhận thông báo khi Briefing sẵn sàng. · P0 · F1 · CONFIRMED (thông báo in-app) / NEEDS_CONFIRMATION (giờ và tần suất, Q-36)

Khối "Rủi ro": Risk Intelligence là P1 (SC-08) → nội dung MVP chờ Q-36; mặc định ẩn khối khi không có nguồn rủi ro.

### E6 — Finance Lite (M6)

**US-FNL-01** — Là người được giao quyền tài chính, tôi muốn ghi doanh thu, chi phí, số dư tiền mặt (tay, import hoặc AI soạn) và gửi duyệt. · P0 · SC-04, CDA-F7, D-12 · CONFIRMED
- Given AI soạn bản ghi, Then bản ghi ở trạng thái nháp và tôi là người tạo; AI hỗ trợ được ghi trong lịch sử (CDA-F5).
- Given cùng một yêu cầu gửi lại do mạng lỗi, Then không tạo bản ghi trùng.

**US-FNL-02** — Là người duyệt tài chính, tôi muốn duyệt hoặc từ chối (có lý do) giao dịch của người khác. · P0 · D-12, D-14 · CONFIRMED
- Given tôi là người tạo, Then tôi không duyệt được.
- Given hai người duyệt cùng lúc, Then chỉ một thao tác có hiệu lực.
- Given không có người duyệt hợp lệ nào, Then giao dịch chờ và người tạo, Admin được báo "thiếu người duyệt"; không có cơ chế tự duyệt.

**US-FNL-03** — Là người được giao quyền, tôi muốn đảo toàn bộ một giao dịch đã ghi sổ và ghi bút toán điều chỉnh. · P0 · D-13, CDA-F2, CDA-F4 · CONFIRMED
- Given kỳ gốc đã khóa, Then bút toán đảo ghi vào kỳ đang mở và liên kết bản gốc; không có kỳ mở → từ chối kèm hướng dẫn.
- [1.1] Given giao dịch gốc có ngày thuộc kỳ đã khóa, When gửi duyệt, Then bị từ chối; hệ thống không tự đổi ngày hay kỳ (D-37).
- Given giao dịch là bút toán đảo, Then không đảo được.

**US-FNL-04** — Là người được giao `finance.period.manage`, tôi muốn mở và khóa kỳ báo cáo quản trị. · P0 · CDA-F1 · CONFIRMED (quy tắc) / NEEDS_CONFIRMATION (người giữ quyền)
- Given chưa ai giữ quyền, Then không có kỳ mở; người gửi giao dịch nhận thông báo rõ và Admin thấy cảnh báo "chưa có người quản lý kỳ" (SRS-FIN-12).

**US-FNL-05** — Là CEO/CFO, tôi muốn xem doanh thu, chi phí, tiền mặt, runway kèm thời điểm cập nhật. · P0 · SC-04, FR-HM-03, FR-DF-03 · CONFIRMED (số liệu) / NEEDS_CONFIRMATION (công thức runway, Q-39)

### E7 — Sales Pipeline Lite (M7)

**US-SLS-01** — Là CEO, tôi muốn xem pipeline bán hàng. · P0 · SC-05 · **NEEDS_CONFIRMATION** · [1.1] chưa thuộc phạm vi triển khai MVP (D-40)
- Nguồn chỉ có: "CEO luôn hỏi pipeline" (BRD §6.1) và công thức gợi ý pipeline coverage, tỷ lệ chuyển đổi (BRD §4.3). Không có thực thể, giai đoạn, trọng số, nguồn chỉ tiêu. AC chờ Q-38. Mặc định an toàn: module không hiển thị số liệu nào cho tới khi có đặc tả.

### E8 — AI control (M8)

**US-AIC-01** — Là Admin, tôi muốn bật kill switch để mọi hành động AI tự động phải chờ người xác nhận. · P0 · D-09, D-10 · CONFIRMED
- Given kill switch bật, Then không có ghi tự động; bản nháp được tạo; người khởi tạo được báo; tắt kill switch không tự chạy bản nháp.

**US-AIC-02** — Là người có quyền, tôi muốn xem, sửa và xác nhận/từ chối bản nháp AI. · P0 · UX §7.1 (L2), K4 · CONFIRMED

**US-AIC-03** — Là người khởi tạo, tôi muốn hoàn tác hành động L3 trong 24 giờ. · P0 · BR-11, UX-41 · CONFIRMED

**US-AIC-04** — Là Admin, tôi muốn cấu hình autonomy theo tool × role trong giới hạn hệ thống. · P0 · FR-AUT-02, R8 · CONFIRMED

**US-AIC-05** — Là người dùng, tôi muốn hỏi AI ở bất kỳ đâu và nhận câu trả lời có trích dẫn, chỉ trong dữ liệu tôi được xem. · P0 · UX-02, UX-24, BR-14 · CONFIRMED
- Given AI không có dữ liệu, Then AI nói rõ và gợi ý cách bổ sung (UX-30).

**US-AIC-06** — Là người dùng, tôi muốn đánh giá câu trả lời/bản trích xuất bằng một chạm. · P0 · FR-AIQ-04, UX-28 · CONFIRMED

### E9 — Quyền riêng tư dữ liệu nhân sự

**US-PRV-01** — Là người lao động, tôi muốn dữ liệu cá nhân nhạy cảm của mình bị che với người không có quyền. · P0 · SEC-DC-02, CMP-01, R6 · CONFIRMED (che) / NEEDS_CONFIRMATION (ai được xem)
- Given người dùng không có quyền xem dữ liệu nhạy cảm, Then trường bị che trên mọi màn hình, file xuất và câu trả lời AI.
- Given dữ liệu nhạy cảm, Then không được gửi tới provider AI bên ngoài.

---

## 5. Business rules

Quy tắc nguồn BR-01…BR-22 (Requirements_Traceability §3.1) và quyết định D-09…D-14, D-21, D-22 áp dụng toàn bộ. Quy tắc được làm rõ ở Stage 2B (chi tiết và AC ở SRS):

| Quy tắc | Căn cứ | SRS |
| --- | --- | --- |
| BR-01…BR-22 như nguồn | BRD | Toàn bộ |
| Mục tiêu dựng từ tài liệu ở trạng thái nháp tới khi được kích hoạt | US-DC-005 | SRS-GOAL-03 |
| Task phải có owner và hạn khi giao từ biên bản | US-DC-004 | SRS-WRK-07 |
| "Đúng hạn" của task = hoàn thành không muộn hơn hạn | FR-HM-05 ("Task xong đúng hạn / Task đến hạn") | SRS-WRK-02 |
| Số liệu tài chính chỉ tính từ giao dịch đã ghi sổ | ADR-009 | SRS-FIN-14 |
| Mục tiêu nháp, giao dịch chưa ghi sổ không vào Briefing | Suy ra từ US-DC-005, D-12 | SRS-GOAL-05, SRS-BRF-05 |
| Không có kỳ mở thì không ghi sổ; khôi phục bằng giao quyền tường minh | CDA-F1, R5 | SRS-FIN-12 |

## 6. Yêu cầu phi chức năng

Tóm tắt; chỉ số đo và phương pháp ở SRS §13. Không chỉ số nào đã được đo.

| Nhóm | Yêu cầu | Nguồn |
| --- | --- | --- |
| Bảo mật | Session an toàn, MFA Admin, CSRF, phân quyền mặc định từ chối, write gateway, không log bí mật | ADR-006…008, ADR-012 |
| Hiệu năng | Tài liệu ≤ 5 trang p95 ≤ 60 giây; ≥ 1.000 trang/giờ | NFR-01, NFR-02 |
| Khả dụng | Nhập tay luôn hoạt động khi AI lỗi; model dự phòng | NFR-07, BR-21 |
| Audit | Mọi thay đổi và hành động AI có audit; append-only | FR-DC-05, ADR-010 |
| Quyền riêng tư | Che dữ liệu cá nhân; dữ liệu nhạy cảm chỉ tới provider local | SEC-DC-02, ADR-011 |
| Phục hồi | RPO ≤ 15 phút, RTO ≤ 4 giờ | NFR-03 |
| Ngôn ngữ, truy cập | Tiếng Việt mặc định, tiếng Anh; WCAG 2.1 AA | NFR-05, NFR-08 |

## 7. Dependencies, constraints, risks

| Loại | Nội dung | Ảnh hưởng |
| --- | --- | --- |
| Dependency | Provider LLM/OCR chưa chọn (D-08) | M2, M8; mục tiêu accuracy chưa xác minh |
| Dependency | Người giữ `finance.period.manage` chưa xác định | M6 không ghi sổ được nếu chưa giao |
| Dependency | Danh sách loại tài liệu MVP và Extraction Schema do Admin cấu hình | M2, M3, M4 |
| Constraint | Local/Docker Compose; chi phí thấp | Toàn bộ |
| Constraint | PWA: không cam kết camera nền, sinh trắc học, offline | UX mobile |
| Risk | Một người tài chính duy nhất → không ai duyệt được giao dịch của người đó | M6 |
| Risk | Module M3, M4, M5, M7 thiếu quy tắc nghiệp vụ → phải bổ sung sau, có thể đổi API | Stage 2D |
| Risk | Persona chưa kiểm chứng | UX |

## 8. Câu hỏi mở và giả định

Câu hỏi Stage 2B: **Q-28…Q-42** (định nghĩa, tác động, phương án đề xuất ở [Decision_Log](../00-source/Decision_Log.md) §7). Câu hỏi còn mở từ trước: D-08, D-16, D-20, D-23, D-27 (một phần), D-28, D-29, D-31, D-33, R6, người giữ `finance.period.manage`. Giả định: ASM-01…ASM-08.

## 9. Truy vết

Ánh xạ requirement nguồn → PRD/SRS: Requirements_Traceability (cột PRD, SRS và §10). Mỗi epic ở mục 4 liệt kê ID nguồn ngay trong story.
