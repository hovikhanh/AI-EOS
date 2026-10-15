# OPEN DECISIONS & QUESTIONS – AI-EOS

> Nguồn sự thật duy nhất cho mọi quyết định và câu hỏi đang mở.
> CDA chỉ cần điền vào phần **Quyết định của CDA**.

**Cập nhật lần cuối:** 15/10/2026 — vòng 1 đã ghi vào Decision_Log 0.19 (D-44…D-54)
**Số mục đang mở:** **12** (mục 0). Các mục 1–4 bên dưới là phiếu vòng 1, giữ nguyên câu trả lời của CDA làm vết; mỗi mục có nhãn **[ĐÃ QUYẾT]**.
---

## Cách sử dụng
- Tôi (CDA) điền quyết định vào các chỗ trống.
- Claude các phiên sau chỉ cần đọc file này để biết quyết định mới nhất.
- **Ghi quyết định vào sổ chính thức:** theo [CLAUDE.md](../CLAUDE.md) §3, [Decision_Log](00-source/Decision_Log.md) là nguồn sự thật cấp 1. Khi một mục ở đây được điền, phiên kế tiếp phải: (1) chép nguyên văn quyết định vào Decision_Log và gán `D-xx` mới (hoặc ghi "Đã trả lời" cho Q-xx); (2) áp dụng **đúng phạm vi** được duyệt vào tài liệu liên quan; (3) chuyển mục sang phần "Đã quyết" ở cuối file này kèm `D-xx`. Không suy rộng quyết định.
- Mục ghi "(chưa có ID)" chưa được đăng ký trong Decision_Log; khi CDA trả lời sẽ được đăng ký ID mới.
- Ký hiệu: `PROPOSED` = đề xuất của người phân tích, chưa có hiệu lực. "Mặc định an toàn" = hành vi đang được đặc tả/triển khai tạm thời khi chưa có quyết định — **không** phải câu trả lời của CDA.
- P0–P3 ở file này là **mức ưu tiên quyết định**, khác giai đoạn P0–P6 của Implementation_Plan.

---

## 0. Còn mở sau vòng 15/10/2026 (cần CDA điền)

Thứ tự theo thời điểm task cần đến. Không mục nào chặn task đang được bắt đầu (T-007, T-008, T-010, T-101, T-003).

### 0.1. D-50 — Provider demo DeepSeek qua OpenRouter: ba điểm cần làm rõ (cần trước T-204)
- **Bối cảnh:** CDA chọn DeepSeek qua OpenRouter cho **mọi loại dữ liệu** khi demo (ADR-011 Amendment 1). CLAUDE.md §6 cấm dùng dữ liệu thật trong dev/test/CI; dữ liệu gửi tới provider ngoài Việt Nam.
- **Quyết định của CDA:**
  1. Môi trường demo dùng: [ ] chỉ dữ liệu tổng hợp/giả [ ] dữ liệu thật của doanh nghiệp (ghi người phê duyệt: ...)
  2. Production trước khi có provider local, dữ liệu `PERSONAL`/`SENSITIVE`: [ ] chặn bước AI, chuyển thủ công (ADR-011 gốc) [ ] vẫn gửi DeepSeek [ ] Khác: ...
  3. DeepSeek là một phương án trong benchmark T-606: [ ] Có [ ] Không
  4. T-205 (adapter DeepSeek cho demo) có cần chờ T-606 không: [ ] Có (giữ dependency) [ ] Không (bỏ T-606 khỏi dependency phần demo)
  Ngày / Người quyết định:

### 0.2. TC-FIN-14 — dependency thêm cho T-110 (D-44, câu 3 chọn (a))
- **Bối cảnh:** phương án (a) ghi "thêm T-401 (hoặc T-402)". TC-FIN-14 cần biết "không có kỳ mở" (bảng kỳ, T-401) và assignment (T-109, đã là tổ tiên). T-401 là đủ tối thiểu; T-402 kéo theo T-104.
- **Quyết định của CDA:** [ ] T-401 [ ] T-402
  Ngày / Người quyết định:

### 0.3. TC-ACC-10 — chưa có task chủ (phát hiện khi lập TEST_Plan §12)
- **Bối cảnh:** TC-ACC-10 (SRS-ACC-04, EMPLOYEE xem dữ liệu "team", P2) chưa được task nào tham chiếu, kể cả trước Q-51. Định nghĩa "team" = cùng đơn vị trực tiếp vẫn là `PROPOSED` (`[CẦN XÁC NHẬN]` ở SRS-ACC-04; T-108 `PARTIAL`).
- **Đề xuất:** theo R1, task chủ = T-108 (bộ lọc phạm vi).
- **Quyết định của CDA:** Task chủ: [ ] T-108 [ ] Khác: ... · Định nghĩa "team": [ ] cùng đơn vị trực tiếp [ ] Khác: ...
  Ngày / Người quyết định:

### 0.4. Q-29 — công thức % đạt (CDA giao agent đề xuất) và ngưỡng cảnh báo — `PROPOSED`, chưa có hiệu lực
- **Đã quyết:** chiều tốt = tăng; có điền check-in từ task đã xong.
- **Đề xuất công thức (agent, `PROPOSED`):** với KR/KPI có `baseline`, `target`, giá trị đo mới nhất `v`: **% đạt = (v − baseline) / (target − baseline) × 100**, làm tròn số nguyên; hiển thị cả số âm và > 100% (không cắt); `target = baseline` → "không áp dụng"; chưa có giá trị đo → "chưa có dữ liệu". Chỉ áp dụng cho chiều tăng (theo quyết định); chỉ số chiều giảm chưa hỗ trợ.
- **Ngưỡng "dưới 20%" — cách hiểu nào?**
  [ ] (a) Cảnh báo khi % đạt < 20% (giá trị tuyệt đối, bất kể thời gian trong kỳ)
  [ ] (b) Cảnh báo khi % đạt thấp hơn tiến độ thời gian của kỳ quá 20 điểm phần trăm (vd. đã qua 50% kỳ mà % đạt < 30%)
  [ ] (c) Khác: ...
- **Điền check-in từ task — quy tắc nào?** Mô hình dữ liệu hiện chưa có liên kết task ↔ KR.
  [ ] (a) Thêm liên kết task ↔ KR; khi task gắn KR chuyển DONE, form check-in gợi ý giá trị, người dùng xác nhận (không tự ghi)
  [ ] (b) KR loại "đếm task": giá trị = số task gắn KR đã DONE, tự cập nhật
  [ ] (c) Khác: ...
- **Quyết định của CDA:** Công thức: [ ] Duyệt đề xuất [ ] Sửa: ...
  Ngày / Người quyết định:

### 0.5. Q-28 — vòng đời mục tiêu
- **Bối cảnh:** câu trả lời "Vòng đời: Objective" chưa nói trạng thái nào ngoài `DRAFT → ACTIVE`.
- **Quyết định của CDA:** Trạng thái thêm: [ ] Không (chỉ DRAFT/ACTIVE) [ ] Có: ... (vd. CLOSED, CANCELLED, ARCHIVED) · Áp dụng cho: [ ] Objective [ ] Objective, KR, KPI
  Ngày / Người quyết định:

### 0.6. Q-39 — định nghĩa burn ròng (T-407 còn `BLOCKED`)
- **Đã quyết:** runway = tiền mặt / burn ròng hàng tháng (BRD §4.3); burn ≤ 0 → "không áp dụng".
- **Còn thiếu:** burn ròng hàng tháng = [ ] chi phí đã ghi sổ − doanh thu đã ghi sổ của tháng [ ] Khác: ... · Cửa sổ: [ ] tháng gần nhất đã khóa [ ] trung bình 3 tháng gần nhất [ ] Khác: ...
  Ngày / Người quyết định:

### 0.7. Người giữ quyền tài chính và `goals.activate` (D-14, Q-28 — cần trước nghiệm thu P4/P5, không chặn code)
- **Bối cảnh:** CDA xác nhận giữ D-21/D-14: không giao cho ADMIN. Cần người cụ thể.
- **Quyết định của CDA:** `finance.period.manage` (role CFO): ... · `finance.approve` (≥ 2 người, không ADMIN/CEO): ... · Phạm vi ủy quyền: ... · `goals.activate` cấp công ty (CEO): ... · cấp đơn vị (MANAGER): ...
  Ngày / Người quyết định:

### 0.8. D-54 — branch protection: tài khoản phê duyệt
- **Bối cảnh:** GitHub không cho tác giả PR tự approve. Các PR hiện được tạo từ tài khoản `hovikhanh`; `enforce_admins: true`. Nếu CDA cũng dùng `hovikhanh`, bật "≥ 1 approval" sẽ chặn mọi merge.
- **Quyết định của CDA:** Tài khoản approve của CDA: ... · [ ] Bật khi có tài khoản riêng [ ] Tạm không bật
  Ngày / Người quyết định:

### 0.9. Khác (thấp)
| Mục | Câu hỏi | Quyết định của CDA |
| --- | --- | --- |
| Q-36 | Phiếu chọn "Đồng ý mặc định" nhưng ô ngày/người quyết định để trống — xác nhận 15/10/2026, admin? | |
| Q-37 | Ngưỡng "dữ liệu cũ" cho doanh thu / dòng tiền / OKR / task trễ (đang là cấu hình trống) | |
| D-08 | Hai người nhập ground truth cho benchmark; điều kiện cho giai đoạn 2 (tài liệu thật) ngoài điều kiện đã chốt 12/10/2026 | |
| "admin" | "Người quyết định: admin" được ghi là CDA trong Decision_Log — đúng không? | |

---

## 1. Quyết định ưu tiên cao (P0 – Blocker)

### Q-51 – Phân công ownership Test Case — **[ĐÃ QUYẾT 15/10/2026 — D-44]**

- **Mô tả ngắn:** Mỗi test case (TC) trong TEST_Plan thuộc task nào để làm tiêu chí `DONE`? Hiện 65/199 TC được gán cho ≥ 2 task, khiến T-005, T-006, T-011 không bao giờ `DONE` được.
- **Bối cảnh / Vấn đề:**
  - Implementation_Plan §2 (DoD chung mục 2): "Test **tương ứng** trong TEST_Plan được viết và chạy xanh" — "tương ứng" chưa định nghĩa. DoD riêng của T-005, T-006, T-011 trong Plan §4 **không** gán TC nào.
  - Implementation_Handoff §5 lại ghi "nghiệm thu = DoD chung + DoD riêng + các TC dưới đây xanh", với cột TC suy ra theo SRS → một TC thuộc nhiều task, kể cả task đến sau. Ví dụ:
    - T-005 bị gán TC-DR-01/02 (diễn tập khôi phục, cần T-605 — mà T-605 phụ thuộc T-005 → **vòng**) và TC-MIG-02 (bất biến INV-01…16 tạo ở T-008, T-101, T-107, T-301, T-401…).
    - T-006 bị gán TC-GEN-05 (thuộc T-007) và TC-SEC-05 (cần T-102, T-203, T-204).
    - T-011 bị gán TC-FILE-03 (phần chuẩn hóa tên thuộc T-203).
  - Ba task đã có code merge và CI xanh: T-005 run `38543440774`, T-006 run `38544809935`, T-011 run `38544080219`.
- **Đề xuất hiện tại (phương án A, `PROPOSED`):** quy tắc "task chủ":
  - **R1** Mỗi TC có đúng một task chủ = task sớm nhất trong chuỗi dependency chạy được **toàn bộ** kịch bản TC; ưu tiên task có TC trong DoD riêng (Plan §4).
  - **R2** TC chỉ ghi đạt khi task chủ chạy toàn bộ kịch bản xanh trong CI.
  - **R3** Task khác nghiệm thu bằng DoD riêng + "bằng chứng thành phần" — **không** phải PASS, không đổi trạng thái TC.
  - **R4** Task sau chạy lại TC như hồi quy; CI đỏ → không đạt DoD.
  - **R5** Tách TC theo phần không tạo ID mới (ghi "TC-XXX-NN (phần …)").
  - **R6** TC không task nào chạy đủ → CDA chọn thêm dependency hoặc tách TC; chưa quyết thì TC không làm điều kiện `DONE` cho task nào.
  - **R7** Không đổi nội dung TC, không hạ yêu cầu bảo mật.
  - Hệ quả: "test tương ứng" = TC mà task đó làm chủ; T-005 làm chủ TC-MIG-01; T-006, T-011 không làm chủ TC nào → cả ba chuyển `DONE` dựa trên CI đã có.
  - Phương án khác: **B** chỉ ngoại lệ cho T-005/006/011 (vấn đề lặp lại ở T-007, T-009, T-101, T-107, T-302, T-401…); **C** giữ nguyên nghĩa chặt (T-005 không bao giờ `DONE`, chặn toàn bộ P0/P1 sau đó).
- **Tác động nếu chưa quyết:** không task nào được bắt đầu. T-007, T-008, T-010, T-101 chỉ còn thiếu T-005 `DONE`; toàn bộ P1–P6 đứng.
- **File liên quan:** Decision_Log §3.7; [Q-51_TC_Ownership_Draft](04-delivery/Q-51_TC_Ownership_Draft.md) (bảng 65 TC); Implementation_Plan §2, §4, §10; Implementation_Handoff §5; TEST_Plan.
- **Quyết định của CDA:**

**Câu 1 — Quy tắc chung**
[x] Phương án A — duyệt R1–R7, "test tương ứng" = TC task đó làm chủ, chuyển T-005, T-006, T-011 sang `DONE` dựa trên run CI đã có
[ ] Phương án A có chỉnh sửa: ...
[ ] Phương án B (chỉ ngoại lệ ba task)
[ ] Phương án C (giữ nguyên)
[ ] Từ chối – phương án khác: ...

**Câu 2 — 10 TC bị Plan §4 gán vào DoD của hai task** (đề xuất chủ; task còn lại đổi thành "bằng chứng thành phần")

| TC | Đang gán cho | Đề xuất chủ | Lý do | Đồng ý? / Chủ khác |
| --- | --- | --- | --- | --- |
| TC-CAP-05 | T-206, T-208 | T-208 | Bật tự ghi qua cấu hình (BR-05) | Đồng ý |
| TC-CAP-06 | T-206, T-208 | T-206 | Mặc định "mọi trường tiền trọng yếu" áp ở định tuyến | Đồng ý |
| TC-E2E-01…05 | Task frontend tương ứng, T-608 | T-608 | E2E chạy trên Compose → cần T-013; task frontend không phụ thuộc T-013 | Đồng ý |
| TC-KS-08 | T-303, T-511 | T-511 | Cần lịch Briefing | Đồng ý |
| TC-KS-09 | T-303, T-511 | T-511 | T-303 không phụ thuộc T-304 | Đồng ý |
| TC-FIN-14 | T-110, T-402 | Xem câu 3 | Xung đột dependency | Đồng ý |

Liệt kê cụ thể dependency đang ghi chung chung:
- T-601 "các API" = Agent tự tạo và chọn
- T-608 "Các task frontend" = Agent tự chọn

**Câu 3 — 7 TC không task nào chạy đủ** (chọn a hoặc b cho từng TC)

| TC | Cần | Thiếu | (a) Thêm dependency | (b) Tách TC | Chọn |
| --- | --- | --- | --- | --- | --- |
| TC-DR-02 | Khôi phục (T-605) + hash file trong CSDL (T-203) + stack (T-013) | T-605 không phụ thuộc T-203 | Thêm T-203 vào dependency T-605 | Chủ là task khác do CDA chỉ định | [x] a [] b: ... |
| TC-FIN-14 | Trang tình trạng (T-110) + assignment (T-109) + kỳ (T-401) | T-110 không phụ thuộc T-401 | Thêm T-401 (hoặc T-402) vào T-110, chủ T-110 | Chặn thao tác ở T-402, cảnh báo ở T-110 | [x] a [ ] b |
| TC-MIG-02 | INV-01…16 từ T-008, T-101, T-107, T-301, T-302, T-401, T-403 | Chỉ T-511 (không liên quan) có đủ | Thêm dependency cho một task kiểm thử tổng hợp ở P6 | Mỗi task tạo bất biến kiểm phần của mình; đạt tổng ở mốc CDA chỉ định | [x] a [ ] b — mốc: ... |
| TC-REV-05 | Duyệt tài liệu (T-207) + giao dịch `DRAFT` (T-408) | Không task nào phụ thuộc cả hai | Thêm T-408 vào T-207 (chủ T-207) | Thêm T-207 vào T-408 (chủ T-408) | [x] a [ ] b |
| TC-SEC-01 | Render văn bản (frontend) + CSP ở proxy (T-013) | T-602 không phụ thuộc T-013 | Thêm T-013 vào T-602 | Render ở T-602, CSP ở T-013 | [x] a [ ] b |
| TC-SEC-02 | Header bảo mật do proxy đặt | T-602 không phụ thuộc T-013 | Thêm T-013 vào T-602 | Chủ T-013 | [x] a [ ] b |
| TC-SEC-06 | Nhãn dữ liệu (T-112) + không gọi ra ngoài (T-204) + luồng tài liệu (T-206) | Không task nào phụ thuộc cả T-112 và T-206 | Thêm T-112 vào T-206 (chủ T-206) | Định tuyến ở T-204, luồng tài liệu ở T-206 | [x] a [ ] b |

Khoảng trống liên quan: T-510 dùng lineage (SRS-BRF-04) nhưng không phụ thuộc T-211 → thêm T-211 vào T-510? [x] Có [ ] Không

**Câu 4 — TC hồi quy/tổng hợp**
[x] Đồng ý: TC-MIG-01 ghi đạt ở T-005 với phạm vi "schema tại revision `0001`" và bắt buộc xanh ở mọi CI sau; TC-MIG-02 chỉ đạt tổng khi đủ INV-01…16 tại mốc chọn ở câu 3
[ ] Đồng ý có chỉnh sửa: ...
[ ] Từ chối: ...

Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### D-43 – Lựa chọn công cụ Docker Compose (Caddy / ClamAV…) — **[ĐÃ QUYẾT 15/10/2026 — D-43, D-50]**

- **Mô tả ngắn:** Duyệt công cụ cho service `proxy`, `scanner` và phạm vi profile `observability`, `llm` của Docker Compose (T-003, T-013).
- **Bối cảnh / Vấn đề:** D-43 đã CONFIRMED phần tách task: T-003 chỉ còn DoD cấu hình; DoD tích hợp chuyển sang T-013; T-005 bỏ phụ thuộc T-003. Architecture §9.1 chỉ ghi "mã nguồn mở", không chọn công cụ. Phần chọn công cụ vẫn `PROPOSED` → T-003, T-013 `BLOCKED`. Runner GitHub Actions có Docker; máy phát triển không có.
- **Đề xuất hiện tại (`PROPOSED`):**

| # | Thành phần | Đề xuất | Phương án khác | Lý do đề xuất |
| --- | --- | --- | --- | --- |
| 1 | `proxy` | **Caddy** (Apache-2.0) | Nginx (BSD-2-Clause); Traefik (MIT) | CA nội bộ + TLS tự động (`tls internal`), không cần quy trình tạo/xoay chứng chỉ riêng; phục vụ SPA, chuyển `/api`, header bảo mật/CSP, giới hạn body trong một file cấu hình. Nginx phải tự tạo/xoay chứng chỉ nội bộ. Traefik dựa vào Docker socket — thừa cho một máy, tăng bề mặt tấn công |
| 2 | `scanner` | **ClamAV** (`clamd`, GPL-2.0) | Chưa có phương án mã nguồn mở khác được đánh giá | Container riêng, worker gọi qua mạng nội bộ nên không liên kết mã GPL vào AI-EOS; tốn RAM khi nạp chữ ký; cập nhật chữ ký cần kết nối ra ngoài → Q-50 |
| 3 | `observability` | **Không** đưa vào T-003 | Prometheus + dashboard | ADR-012: tùy chọn; log JSON + trang Tình trạng hệ thống đáp ứng phần bắt buộc |
| 4 | `llm` | **Hoãn** tới D-08 | Runtime local (vd. Ollama) | Chưa chọn provider; giữ adapter (ADR-011) |

- **Tác động nếu chưa quyết:** không có Docker Compose/image → không môi trường nào triển khai được; T-013, T-605 (backup/restore, RPO/RTO), T-608 (E2E) bị chặn; TC-SEC-01/02 (CSP, header proxy) không có chủ.
- **File liên quan:** Decision_Log D-43, §3.6, §3.6.2; Architecture §9.1; ADR-004, ADR-012; Implementation_Plan §4 (T-003, T-013).
- **Lưu ý:** trả lời cùng lúc với Q-50 — phương án B của Q-50 thêm một service vào T-003.
- **Quyết định của CDA:**

[ ] Đồng ý cả 4 mục đề xuất
[x] Đồng ý có chỉnh sửa: (1) proxy = như đề xuất (2) scanner = như đề xuất (3) observability = như đề xuất (4) llm = chọn provider deepseek qua openrouter
[ ] Cho phép chọn công cụ khi triển khai (như T-605)
[ ] Từ chối – phương án khác: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### Q-50 – Scanner: cập nhật chữ ký online hay offline — **[ĐÃ QUYẾT 15/10/2026 — D-45 — đổi sang phương án B]**

- **Mô tả ngắn:** Scanner mã độc cần cập nhật chữ ký từ bên ngoài, trong khi TC-NFR-01 cấm mọi kết nối ra ngoài máy (trừ đích backup). Cần chọn cách cập nhật và ranh giới TC-NFR-01.
- **Bối cảnh / Vấn đề:**
  - Architecture §9.1: scanner "cập nhật chữ ký định kỳ" — mọi scanner dựa trên chữ ký đều cần nguồn ngoài, không riêng ClamAV.
  - SRS-NFR-04: toàn bộ **dữ liệu và xử lý** trên máy triển khai, trừ lời gọi provider cloud được phép; không nói về kết nối không mang dữ liệu.
  - TC-NFR-01 (P0): theo dõi kết nối ra ngoài **của container** khi chỉ cấu hình provider local → **không có kết nối ra ngoài máy**, trừ đích backup. Chặt hơn SRS-NFR-04.
  - Tạm thời T-003 không cấu hình kết nối ra ngoài cho `scanner`.
- **Phương án:**

| # | Phương án | Kết nối ra ngoài | Ưu điểm | Nhược điểm |
| --- | --- | --- | --- | --- |
| A | `scanner` tự tải chữ ký | Có, từ container giữ file người dùng | Đơn giản, chữ ký luôn mới | Container xử lý tài liệu có đường ra internet; trái TC-NFR-01 |
| B | Container cập nhật riêng (chỉ tải chữ ký vào volume); `scanner` ở mạng `internal` | Có, chỉ từ container cập nhật (không đọc file người dùng) | Đường xử lý tài liệu không có internet; vẫn tự động | Thêm một service; TC-NFR-01 cần ngoại lệ như "đích backup" |
| C | Ngoại tuyến: người vận hành tải gói chữ ký ở máy khác, kiểm chữ ký số, chép vào volume | Không | Đúng chữ nghĩa TC-NFR-01 | Thao tác tay; chữ ký có thể cũ; cần quy định tuổi tối đa và người chịu trách nhiệm |
| D | Mirror chữ ký nội bộ của doanh nghiệp | Chỉ ra mạng nội bộ | Tự động, không ra internet | Doanh nghiệp phải có hạ tầng mirror — ngoài phạm vi AI-EOS |

- **Đề xuất hiện tại (`PROPOSED`):** **B**. Nếu CDA chọn "cả máy, kể cả lúc cập nhật" ở câu 1 thì **C**.
- **Tác động nếu chưa quyết:** T-003, T-013 `BLOCKED` (cùng D-43); TC-NFR-01 không xác định được tiêu chí đạt.
- **File liên quan:** Decision_Log Q-50, §3.6.3; Architecture §9.1; SRS-NFR-04; TEST_Plan §10a (TC-NFR-01).
- **Quyết định của CDA:**

1. TC-NFR-01 áp dụng cho: [ ] (a) mọi container [x] (b) chỉ container xử lý dữ liệu nghiệp vụ [ ] (c) cả máy, kể cả lúc cập nhật chữ ký
2. Kết nối ra ngoài không mang dữ liệu nghiệp vụ (tải chữ ký) được chấp nhận như ngoại lệ "đích backup": [x] Có [ ] Không
3. Tuổi chữ ký tối đa chấp nhận được: 90 ngày
4. Nếu chọn C — người vận hành cập nhật: ...
5. Phương án: [x] A [ ] B [ ] C [ ] D [ ] Khác: ...

Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### Phê duyệt chính thức Implementation_Plan + TEST_Plan + CLAUDE.md (chưa có ID) — **[ĐÃ QUYẾT 15/10/2026 — D-46]**

- **Mô tả ngắn:** Ghi nhận chính thức CDA đã duyệt kế hoạch triển khai, kế hoạch kiểm thử và quy tắc cho coding agent.
- **Bối cảnh / Vấn đề:**
  - Documentation_Review §9 (12/10/2026) liệt kê điều kiện trước khi code: (1) CDA duyệt Implementation_Plan và TEST_Plan; (2) duyệt CLAUDE.md. Implementation_Handoff §9 cũng ghi đây là điều kiện bắt đầu T-001.
  - Thực tế: T-001…T-012 đã được làm theo chỉ đạo CDA trong từng phiên (vd. ngoại lệ T-002 ngày 12/10/2026, D-41, D-42, D-43); 5 PR code đã merge. Nhưng header Implementation_Plan vẫn ghi "Kế hoạch — **chờ CDA duyệt trước khi triển khai code**"; TEST_Plan 1.0 chưa có ghi nhận duyệt. Không tìm thấy dòng nào trong Decision_Log ghi phê duyệt hai file này.
  - Mọi DoD và tiêu chí nghiệm thu (Plan §2, §9; TEST_Plan §1 "tiêu chí vào/ra") đang dựa trên tài liệu chưa có phê duyệt chính thức.
- **Đề xuất hiện tại:** CDA duyệt Implementation_Plan (bản hiện hành: 1.0 cập nhật 14/10/2026 theo D-42, D-43), TEST_Plan 1.0 và CLAUDE.md hiện hành, kèm ngày hiệu lực; nếu có phần chưa duyệt, ghi rõ ngoại lệ.
- **Tác động nếu chưa quyết:** tiêu chí `DONE` của mọi task thiếu căn cứ chính thức; mâu thuẫn giữa header tài liệu và thực tế tiếp tục tồn tại.
- **File liên quan:** Implementation_Plan (header, §1, §2, §9); TEST_Plan §1; CLAUDE.md; Documentation_Review §9; Implementation_Handoff §9.
- **Quyết định của CDA:**

[x] Duyệt cả ba (Implementation_Plan, TEST_Plan, CLAUDE.md), hiệu lực từ: ngây bây giờ
[ ] Duyệt có ngoại lệ: ...
[ ] Ghi nhận phê duyệt hồi tố cho T-001…T-012 đã làm: [ ] Có [ ] Không
[ ] Từ chối – yêu cầu sửa: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### ĐX-12-1 đến ĐX-12-7 – Test case cho nền tảng frontend (T-012) — **[ĐÃ QUYẾT 15/10/2026 — D-47]**

- **Mô tả ngắn:** Duyệt 7 test đã viết cho T-012 để đăng ký thành TC chính thức trong TEST_Plan; sau đó T-012 chuyển `DONE`.
- **Bối cảnh / Vấn đề:** T-012 đã merge (PR #5) và CI xanh (run `38536047844`: Vitest 47 passed, `build-check` OK), nhưng DoD yêu cầu TC trong TEST_Plan; T-012 chưa có TC nào. `ĐX-12-n` chỉ là nhãn đề xuất, không phải ID. Chưa kiểm trên trình duyệt thật (cài PWA, đăng ký service worker).
- **Đề xuất hiện tại (`PROPOSED`):**

| Mã đề xuất | Mục tiêu | Kết quả mong đợi | Loại · Mức đề xuất | Hiện thực | ID đề xuất | Đồng ý? |
| --- | --- | --- | --- | --- | --- | --- |
| ĐX-12-1 | Router: route gốc và route không tồn tại | `/` hiện "AI-EOS"; đường dẫn lạ hiện "Không tìm thấy hoặc bạn không có quyền" + liên kết về `/` | U · P1 | `frontend/src/routes.test.tsx` | FE-01 | |
| ĐX-12-2 | Client API dùng cookie session, không dùng Web Storage | `credentials: "include"` mọi request; không gọi `Storage`; lỗi HTTP → `ApiError` | U · P0 | `frontend/src/api/client.test.ts` | FE-02 | |
| ĐX-12-3 | Service worker không cache `/api` và HTML | Chỉ `/assets/*` (GET, cùng origin, không query) và manifest/icon được cache | U · P0 | `frontend/src/sw/cachePolicy.test.ts` | FE-03 | |
| ĐX-12-4 | Manifest PWA hợp lệ trong bản build | Có `name`, `short_name`, `start_url`, `display`, icon 192/512 | U · P1 | `frontend/scripts/check-build.js` | FE-04 | |
| ĐX-12-5 | Bản build không có script inline (CSP, ADR-003) | `dist/index.html` không có script inline hay thuộc tính `on…=` | S · P0 | `frontend/scripts/check-build.js` | FE-05 | |
| ĐX-12-6 | Lint chặn `dangerouslySetInnerHTML` | Lỗi `no-restricted-syntax` mức error | S · P0 | `frontend/src/lint.test.ts` + `eslint.config.js` | FE-06 | |
| ĐX-12-7 | Component nền tảng render với token trung tính (D-35) | Đủ token UX §8.2; `primary` thuộc thang xám | U · P2 | `frontend/src/components/ui/button.test.tsx` | FE-07 | |

  Cách đăng ký sau khi duyệt: thêm mục "Nền tảng frontend (T-012)" vào TEST_Plan, cột "Yêu cầu" ghi ADR-003, trạng thái `NOT RUN`; Handoff §5 ghi ID mới; chuyển T-012 sang `DONE` dựa trên run `38536047844` (mã test không đổi nên không chạy lại).
- **Tác động nếu chưa quyết:** T-012 giữ `IN_REVIEW`; T-111, T-207, T-212, T-409, T-504, T-509 (cần T-012 `DONE`) không bắt đầu được khi tới lượt.
- **File liên quan:** Implementation_Plan §4 (T-012), §10, §12, §12.1, §12.2; TEST_Plan.
- **Quyết định của CDA:**

[x] Đồng ý cả 7, nhóm ID `FE` (FE-01…FE-07), mức như đề xuất
[ ] Đồng ý có chỉnh sửa: nhóm ID = ... ; mức = ... ; bỏ/sửa: ...
[ ] Từ chối – phương án khác: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

## 2. Quyết định / Câu hỏi ưu tiên cao khác (P1)

### D-08 – Provider LLM/OCR và dataset benchmark — **[ĐÃ QUYẾT 15/10/2026 — D-08, D-50 — một phần]**

- **Mô tả ngắn:** Chọn provider LLM/OCR. Việc cần CDA làm **bây giờ** là duyệt dataset benchmark; chọn provider sau khi có báo cáo T-606.
- **Bối cảnh / Vấn đề:** Đã chốt (`CDA_DIRECTIVE` 12/10/2026): benchmark trước bằng tài liệu tiếng Việt **tổng hợp, không PII thật**; tài liệu thật chỉ khi được phê duyệt và đã xử lý; không gửi dữ liệu nhạy cảm ra provider ngoài; không tuyên bố đạt MET-01 trước benchmark. Kế hoạch (TEST_Plan §9):
  - So sánh ≥ 2 phương án, ít nhất một chạy local.
  - Dataset giai đoạn 1 tổng hợp: biên bản họp, kế hoạch/KPI, báo cáo định kỳ, danh sách nhân sự, SOP; dạng PDF có lớp text, PDF scan, ảnh chụp, có chữ viết tay; tối thiểu 30 tài liệu mỗi loại (`PROPOSED`).
  - Ground truth do hai người nhập độc lập rồi đối chiếu.
  - Metric: field accuracy (MET-01), phân loại đúng (MET-07), lỗi nghiêm trọng, p50/p95 latency, chi phí/tài liệu.
- **Đề xuất hiện tại:** duyệt dataset giai đoạn 1 như trên; giai đoạn 2 (tài liệu thật) chỉ với provider local và sau khi ẩn/giả danh PII.
- **Tác động nếu chưa quyết:** T-205 (adapter thật), T-604 (hiệu năng) `BLOCKED`; T-306, T-511 chỉ làm được với adapter giả lập; giá trị cốt lõi (trích xuất tài liệu tiếng Việt) chưa được chứng minh. T-606 có thể bắt đầu khi T-204 xong — dataset cần sẵn trước đó.
- **File liên quan:** Decision_Log D-08; ADR-011; TEST_Plan §9; Implementation_Plan T-205, T-604, T-606.
- **Quyết định của CDA:**

Dataset giai đoạn 1: [x] Duyệt như đề xuất [ ] Duyệt có chỉnh sửa: ...
Quy mô mỗi loại tài liệu: ...
Người tạo ground truth (2 người): ...
Giai đoạn 2 (tài liệu thật): [x] Cho phép, điều kiện: ... [ ] Không
Provider (sau báo cáo T-606): ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### Người giữ `finance.period.manage` và assignment vận hành (phần mở của D-14) — **[ĐÃ QUYẾT 15/10/2026 — D-14 — chỉ phần người giao hàng chờ review; người giữ quyền tài chính còn mở]**

- **Mô tả ngắn:** Giao người thật cho các quyền vận hành bắt buộc trước nghiệm thu Finance (P4) và Goals (P5).
- **Bối cảnh / Vấn đề:** `finance.period.manage` chỉ giao được cho role `CFO`; chưa giao → không mở/khóa kỳ được → không gửi/ghi sổ được, Admin thấy cảnh báo. Người tạo không tự duyệt và không có fallback (D-12, D-14) → cần **≥ 2 người** có `finance.approve` để duyệt chéo. `finance.approve` không cấp cho ADMIN/CEO. `goals.activate` chỉ qua assignment, không quyền nền (D-39). Người giao assignment hàng chờ review: `ADMIN` hoặc `MANAGER` của đơn vị — `[CẦN XÁC NHẬN]`.
- **Đề xuất hiện tại:** không có đề xuất về người cụ thể (là quyết định vận hành của CDA).
- **Tác động nếu chưa quyết:** không chặn code; chặn **nghiệm thu** P4/P5 và vận hành thật (rủi ro "một người tài chính duy nhất" ở Implementation_Plan §8).
- **File liên quan:** Decision_Log D-14, §4.4; Documentation_Review §9 mục 3; Architecture §6, §7.4; Implementation_Plan T-402.
- **Quyết định của CDA:**

Người giữ `finance.period.manage` (role CFO): ADMIN
Người giữ `finance.approve` (≥ 2): ADMIN
Phạm vi ủy quyền duyệt tài chính (đơn vị/loại giao dịch; không tự đặt hạn mức — D-16): ADMIN
Người giữ `goals.activate`: ADMIN
Người giao assignment hàng chờ review: [ ] ADMIN [x] MANAGER của đơn vị [ ] Khác: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### R6 (phần mở của D-21) – Người giữ quyền dữ liệu nhân sự nhạy cảm — **[ĐÃ QUYẾT 15/10/2026 — D-21]**

- **Mô tả ngắn:** Ai được giữ `hr.profile.read`, `hr.salary.read`, `hr.export`, `pii.unmask`?
- **Bối cảnh / Vấn đề:** Chỉ đạo 12/10/2026: deny mặc định; các quyền tách riêng; không cấp theo tên role. Hiện không ai giữ; dữ liệu bị che. `hr.import` thuộc ADMIN (giới hạn tác vụ). ADMIN không được đọc lương/PII (D-21).
- **Đề xuất hiện tại:** giữ "không ai giữ" cho tới khi CDA chỉ định.
- **Tác động nếu chưa quyết:** T-907 `BLOCKED`; T-112 `PARTIAL`; không ai xem được hồ sơ/lương đầy đủ trong hệ thống.
- **File liên quan:** Decision_Log D-21; Architecture §6; Implementation_Plan T-112, T-907.
- **Quyết định của CDA:**

[x] Giữ mặc định: không ai giữ trong MVP
[ ] Chỉ định: `hr.profile.read` = ... ; `hr.salary.read` = ... ; `hr.export` = ... ; `pii.unmask` = ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### Diễn giải ADR-008 Amendment 1 – Chat AI chỉ đọc khi kill switch bật (chưa có ID) — **[ĐÃ QUYẾT 15/10/2026 — D-48]**

- **Mô tả ngắn:** Khi kill switch bật, chat AI chỉ đọc (L0) có tiếp tục hoạt động không?
- **Bối cảnh / Vấn đề:** ADR-008 Amendment 1 (AMD-02, D-38): kill switch chặn job `AI_CONTENT` (tạo nội dung Briefing) ngoài gateway. Diễn giải hiện tại: trả lời hội thoại trực tiếp (chat, chỉ đọc, L0) **không** bị chặn vì không ghi gì và do người dùng chủ động — D-09 nói về hành động WRITE/EXECUTION; BRD §4.2 định nghĩa L0 là "chỉ đọc và trả lời". ADR ghi: muốn tắt cả chat cần quyết định riêng.
- **Đề xuất hiện tại:** chat chỉ đọc vẫn hoạt động.
- **Tác động nếu chưa quyết:** cần trước T-303 (kill switch) và T-306 (chat); đổi hành vi sau sẽ phải sửa test TC-KS-*.
- **File liên quan:** ADR-008 (Decision, Amendment 1); Documentation_Review §9 mục 5; Implementation_Handoff §7.
- **Quyết định của CDA:**

[x] Đồng ý: chat chỉ đọc vẫn hoạt động khi kill switch bật
[ ] Không: kill switch tắt cả chat AI
[ ] Khác: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

### Task frontend cho panel chat AI và Trang chủ CEO (chưa có ID) — **[ĐÃ QUYẾT 15/10/2026 — D-49]**

- **Mô tả ngắn:** Giao task nào làm giao diện panel chat AI và màn Trang chủ CEO (FL-07)?
- **Bối cảnh / Vấn đề:** Implementation_Plan §12 `[CẦN XÁC NHẬN]`: chưa task frontend nào được giao tường minh cho (1) phần giao diện của SRS-AIC-12 (source chip, độ tin cậy, nút Dừng) — T-306 chỉ có API SSE; (2) Trang chủ CEO FL-07 — T-510 chỉ có API-INS-01/02; TC-E2E-05 có FL-07 nhưng gắn với T-509 "Frontend công việc". Đây là hai màn hình cốt lõi của lời hứa MVP (F1 CEO buổi sáng).
- **Đề xuất hiện tại:** không có. Các lựa chọn: (a) task mới trong dải P3/P5 (ID kế tiếp, không tái sử dụng); (b) mở rộng phạm vi T-306 / T-510 thêm phần frontend (+ dependency T-012); (c) gộp vào T-111.
- **Tác động nếu chưa quyết:** không chặn ngay; tới P3/P5 sẽ thiếu màn hình chính, E2E FL-07 không có chủ rõ.
- **File liên quan:** Implementation_Plan §4 (T-306, T-509, T-510), §12; UX_Flows FL-07; SRS-AIC-12.
- **Quyết định của CDA:**

Panel chat AI: [x] (a) task mới [ ] (b) mở rộng T-306 [ ] (c) T-111 [ ] Khác: ...
Trang chủ CEO: [x] (a) task mới [ ] (b) mở rộng T-510 [ ] (c) T-111 [ ] Khác: ...
Ngày quyết định: 15/10/2026
Người quyết định: admin
Ghi chú:

---

## 3. Câu hỏi nghiệp vụ còn mở

Tất cả đang dùng "mặc định an toàn" — đó **không** phải câu trả lời. Nguồn: Decision_Log §2, §5, §7. Năm câu ưu tiên **Cao** trình bày đầy đủ trước; các câu còn lại ở bảng 3.2.

### 3.1. Ưu tiên Cao

#### Q-28 – Vòng đời mục tiêu và quyền kích hoạt (M3) — **[ĐÃ QUYẾT 15/10/2026 — D-51 — một phần]**
- **Câu hỏi:** Vòng đời Objective/KR/KPI ngoài `DRAFT → ACTIVE` (đóng, hủy, lưu trữ)? Ai kích hoạt mục tiêu cấp công ty/đơn vị?
- **Mặc định đang áp dụng (D-39):** mục tiêu mới ở `DRAFT`; kích hoạt cần thao tác rõ ràng của người có `goals.activate`, giao qua assignment, không quyền nền. Chỉ DRAFT/ACTIVE.
- **Phương án đề xuất (§7):** kích hoạt cấp công ty: CEO; cấp đơn vị: MANAGER.
- **Tác động:** T-502 `PARTIAL`; SRS-GOAL-03, 04.
- **Quyết định của CDA:** Vòng đời: Objective · Người kích hoạt cấp công ty: CEO · cấp đơn vị: MANAGER
  Ngày / Người quyết định: 15/10/2026 | admin

#### Q-29 – Công thức % đạt và cảnh báo lệch (M3, M5) — **[ĐÃ QUYẾT 15/10/2026 — D-51 — một phần]**
- **Câu hỏi:** Công thức % đạt của KR/KPI, chiều tốt (tăng/giảm), ngưỡng cảnh báo lệch? Có điền check-in từ task đã xong không?
- **Mặc định đang áp dụng (D-39):** không tính %; chỉ hiển thị baseline/target/giá trị; không cảnh báo.
- **Tác động:** T-904 `BLOCKED`; T-504 `PARTIAL`; ô OKR trên Trang chủ CEO.
- **Quyết định của CDA:** Công thức: tự đề xuất · Chiều tốt: tăng · Ngưỡng cảnh báo: dưới 20% · Check-in từ task: [x] Có [ ] Không
  Ngày / Người quyết định: 15/10/2026 | admin

#### Q-36 – Nội dung CEO Briefing (M5) — **[ĐÃ QUYẾT 15/10/2026 — D-51]**
- **Câu hỏi:** Loại mục trong "Cần anh quyết"; có khối "Rủi ro" không (Risk Intelligence là P1); giờ/tần suất tạo Briefing?
- **Mặc định đang áp dụng (D-39 + §7):** chỉ hiển thị nội dung có nguồn truy vết được, ẩn khối chưa đủ căn cứ; "Cần anh quyết" = bản nháp AI chờ CEO + task giao cho CEO trễ/sắp đến hạn; ẩn khối Rủi ro; 07:00 hằng ngày (`PROPOSED`, cài dạng cấu hình).
- **Tác động:** T-510, T-511 `PARTIAL`.
- **Quyết định của CDA:** [x] Đồng ý mặc định [ ] Khác — Cần anh quyết gồm: ... · Khối Rủi ro: ... · Giờ/tần suất: ...
  Ngày / Người quyết định:

#### Q-37 – Công thức 4 ô chỉ số và ngưỡng "dữ liệu cũ" (M5; liên quan D-28) — **[ĐÃ QUYẾT 15/10/2026 — D-51]**
- **Câu hỏi:** Công thức 4 ô mặc định (doanh thu, dòng tiền, OKR, task trễ) và ngưỡng "dữ liệu cũ" của từng chỉ số?
- **Mặc định đang áp dụng (D-39):** công thức theo SRS-BRF-05 (`PROPOSED`, gợi ý từ BRD §4.3), ô gắn nhãn "đề xuất — chưa chính thức", không cảnh báo; ngưỡng "dữ liệu cũ" là cấu hình trống.
- **Tác động:** T-510 `PARTIAL`; trả lời luôn D-28 (bộ chỉ số sức khỏe MVP).
- **Quyết định của CDA:** [x] Duyệt công thức SRS-BRF-05 làm chính thức [ ] Khác: ... · Ngưỡng dữ liệu cũ: doanh thu ... / dòng tiền ... / OKR ... / task ...
  Ngày / Người quyết định: 15/10/2026 | admin

#### Q-38 – Sales Pipeline Lite (M7) — **[ĐÃ QUYẾT 15/10/2026 — D-51]**
- **Câu hỏi:** Thực thể, trường, giai đoạn, trọng số/xác suất, nguồn chỉ tiêu, ai nhập, nhập tay hay import?
- **Mặc định đang áp dụng (D-40):** không triển khai trong MVP; không hiển thị số liệu pipeline. SC-05 giữ `NEEDS_CONFIRMATION` vì BRD xếp P0 — chỉ việc triển khai bị chặn.
- **Tác động:** T-901 `BLOCKED`; API-SALES-01 giữ `SKELETON`.
- **Quyết định của CDA:** [x] Giữ ngoài MVP [ ] Cung cấp đặc tả: ...
  Ngày / Người quyết định: 15/10/2026 | admin

### 3.2. Ưu tiên Trung bình / Thấp — **[ĐÃ QUYẾT 15/10/2026 — D-51; D-16…D-33 cập nhật trong Decision_Log]**

| ID | Câu hỏi | Mặc định an toàn / đề xuất hiện tại | Tác động | Ưu tiên | Quyết định của CDA |
| --- | --- | --- | --- | --- | --- |
| Q-30 | Nhịp check-in, ai bắt buộc check-in, định nghĩa "KPI cập nhật đúng hạn" (MET-10) | Không nhắc tự động; check-in tự nguyện; thang độ tự tin 0–10 là cấu hình `PROPOSED` | T-501 `PARTIAL`, T-906 `BLOCKED` | TB | Như đề xuất |
| Q-31 | Độ dài kỳ mục tiêu (quý/tháng/năm); quan hệ với kỳ tài chính | Kỳ mục tiêu văn bản tự do; kỳ tài chính mặc định tháng | T-402 `PARTIAL`, schema kỳ | TB | Như đề xuất |
| Q-32 | Cây alignment: KPI gắn Objective? Có cấp Chiến lược/Initiative/Dự án? | Chỉ Objective cha–con, KR thuộc Objective, KPI độc lập | SRS-GOAL-01, 10 | TB | Như đề xuất |
| Q-33 | Trạng thái task ngoài Mở/Xong; task cần gửi duyệt? Ai mở lại task? | Chỉ OPEN/DONE; không duyệt; mở lại bởi người giao; EMPLOYEE tự giao (`PROPOSED`) | T-505 `PARTIAL` | TB | Như đề xuất |
| Q-34 | Mô hình workload (ước lượng, năng lực) cho F5 | Không có workload trong MVP | T-902 `BLOCKED` | TB | Như đề xuất |
| Q-35 | "Đặt lịch"/đồng bộ lịch trong F1, UC-06 có thuộc MVP? Lịch nội bộ hay ngoài? | Không có lịch trong MVP | T-903 `BLOCKED` (cùng D-31) | TB | Như đề xuất |
| Q-39 | Định nghĩa "burn ròng hàng tháng" và cửa sổ tính runway | Runway "không áp dụng" khi burn ≤ 0; công thức BRD §4.3 làm mặc định đề xuất | T-407 `BLOCKED` | TB | Như đề xuất |
| Q-41 | Decision Log: theo dõi kết quả sau 30/60/90 ngày trong MVP? | Chỉ ghi quyết định, không theo dõi | T-905 `BLOCKED` | Thấp | Như đề xuất |
| Q-42 | Danh mục doanh thu/chi phí; một hay nhiều tài khoản tiền mặt | Danh mục văn bản tự do; một số dư tiền mặt tổng | T-403 `PARTIAL` | TB | Như đề xuất |
| D-16 | Danh sách trường trọng yếu, ngưỡng giá trị autonomy, ngưỡng sinh trắc học | Mọi trường tiền là trọng yếu; tự ghi tắt; không hạn mức (nguồn chỉ có ví dụ: số tiền, số TK, MST, lương, giá trị HĐ; "5 triệu") | T-206 `PARTIAL` | TB | Như đề xuất |
| D-29 | Ngưỡng độ tin cậy hiển thị vs định tuyến | Hai cấu hình tách biệt: hiển thị 90/60 (UX §6.2), tự ghi theo loại tài liệu + trường; tự ghi tắt | T-206, T-208 | TB | Như đề xuất |
| D-20 | Tài liệu chuẩn cho chỉ số "review ≤ 60 giây" (MET-13 dùng hóa đơn) | Đo MET-04 trên biên bản họp, báo cáo KPI; MET-13 `DEFERRED` sang Phase 2 | TC-NFR-07, Business_OKRs | TB | Như đề xuất |
| D-23 | Danh sách domain (22 vs 28) và 8 mục IA | 22 domain + Procurement/Contract (P1) tới khi có danh sách 28 | PRD, UX_Flows | TB | Như đề xuất |
| D-27 (phần) | Sinh trắc học, offline, camera nền trên mobile | PWA đã chốt; không cam kết các mục này trong MVP, `DEFERRED` | ADR-003, UX mobile | TB | Như đề xuất |
| D-31 | Tích hợp lịch và tích hợp ngoài trong MVP | Không tích hợp lịch ngoài; "đồng bộ lịch" dùng lịch nội bộ | T-903 | TB | Như đề xuất |
| D-33 | Màn ngoài 4 việc cốt lõi trên mobile | Chỉ đọc (UX §9.1) | UX_Flows | Thấp | Như đề xuất |
| GAP-13 | Nguồn dữ liệu đơn vị hành chính (chuẩn hóa địa chỉ VN) | Chỉ validate định dạng; không chặn MVP | T-206 `PARTIAL` | Thấp | Như đề xuất |
| GAP-14 | Ngân sách AI, trần chi phí/tài liệu | Trần cấu hình được, mặc định thấp, vượt trần chặn lời gọi không thiết yếu (`AIEOS_AI_BUDGET_LIMIT` tùy chọn) | T-204, MET-05 | TB | Như đề xuất |
| GAP-15 | Chính sách lưu trữ ngoài chứng từ kế toán và CV | Không tự xóa dữ liệu; không cam kết lưu ≥ 10 năm (BR-16) | Architecture §9.3, vận hành | TB | Như đề xuất |
| GAP-18 | SLA review | Cấu hình được, giá trị trống | T-207 `PARTIAL` | Thấp | Như đề xuất |
| GAP-21 | NFR nền tảng chung (độ trễ API, SRS-NFR-12) | `[CẦN XÁC NHẬN]`; đề xuất đo và đặt mục tiêu sau pilot | SRS-NFR-12 | TB | Như đề xuất |

---

## 4. Quyết định P2 / kỹ thuật — **[ĐÃ QUYẾT 15/10/2026 — D-34, D-35, D-36, D-52, D-53, D-54 (D-54 chưa áp dụng)]**

| ID | Nội dung | Đề xuất hiện tại | Tác động | Quyết định của CDA |
| --- | --- | --- | --- | --- |
| D-34 | Sửa tham chiếu CON-10, CON-11 | Theo BRD §6.1: 5 kênh MVP; US-PERF-001 và UC-02 là P1 (`PROPOSED`, đóng nếu không phản đối) | PRD, UX_Flows | Như đề xuất |
| D-36 | Vị trí tài liệu và CLAUDE.md | Tài liệu ở `AI-EOS/docs/`, `CLAUDE.md` ở `AI-EOS/`, không trỏ tới A-EMS (`PROPOSED`, đóng nếu không phản đối) | Mọi tái cấu trúc thư mục `docs/` |Như đề xuất |
| D-35 | Thương hiệu, xưng hô AI, người tham gia test | `DEFERRED` tới trước giai đoạn hi-fi/usability test; token trung tính; xưng hô "bạn" cấu hình được | T-012 (token giữ chỗ), kiểm chứng persona | Như đề xuất |
| Giả định C1 (chưa có ID) | `providers` có bị cấm import cả module hạ tầng `audit`, `storage` không? (diễn giải chặt hiện tại; `platform` được phép theo D-42) | Giữ diễn giải chặt (import-contract C1, Implementation_Plan §11.4) | T-204 (provider adapter: call log, audit) | Như đề xuất |
| Trạng thái API (chưa có ID) | API_Specification §1.10 không có giá trị cho "đã triển khai"; API-SYS-01/02 đã chạy nhưng vẫn ghi `DESIGNED` (Plan §16 "không tự thêm") | Thêm trạng thái `IMPLEMENTED` (chỉ khi có code + test) — cần CDA duyệt vì là thay đổi quy ước API (CLAUDE.md §7) | Truy vết tiến độ API | Như đề xuất |
| Branch protection (chưa có ID; đề xuất của review 15/10/2026, không có trong tài liệu gốc) | Branch protection `main` hiện yêu cầu **0 approval** → phê duyệt CDA chỉ ghi trong tài liệu, không được cưỡng chế kỹ thuật | Yêu cầu ≥ 1 approval của CDA trước khi merge | Quy trình review; mọi PR sau | Như đề xuất |

---

## 5. Bảng tra cứu nhanh

| ID     | Tiêu đề ngắn              | Ưu tiên | Trạng thái | Quyết định của CDA |
|--------|---------------------------|---------|------------|--------------------|
| Q-51   | Ownership Test Case       | P0      | Đã quyết (D-44) |                    |
| D-43   | Công cụ proxy/scanner     | P0      | Đã quyết (D-43, D-50) |                    |
| Q-50   | Scanner offline/update    | P0      | Đã quyết (D-45) |                    |
| —      | Phê duyệt Plan + TEST_Plan + CLAUDE.md | P0 | Đã quyết (D-46) |                    |
| ĐX-12-1…7 | TC nền tảng frontend   | P0      | Đã quyết (D-47) |                    |
| D-08   | Provider LLM/OCR + dataset benchmark | P1 | Một phần (D-08, D-50) |                    |
| D-14 (phần) | Người giữ `finance.period.manage`, assignment vận hành | P1 | Một phần — người giữ quyền còn mở | |
| D-21 (R6) | Quyền dữ liệu nhân sự nhạy cảm | P1 | Đã quyết (D-21) |                    |
| —      | Chat AI khi kill switch bật (ADR-008 AMD 1) | P1 | Đã quyết (D-48) |             |
| —      | Task frontend chat AI, Trang chủ CEO | P1 | Đã quyết (D-49) |                    |
| Q-28   | Vòng đời, quyền kích hoạt mục tiêu | Cao | Một phần (D-51) |                   |
| Q-29   | % đạt, cảnh báo lệch      | Cao     | Một phần (D-51) |                    |
| Q-36   | Nội dung CEO Briefing     | Cao     | Đã quyết (D-51) |                    |
| Q-37   | Công thức 4 ô chỉ số      | Cao     | Đã quyết (D-51) |                    |
| Q-38   | Sales Pipeline Lite       | Cao     | Đã quyết (D-51) |                    |
| Q-30   | Nhịp check-in             | TB      | Đã quyết (D-51) |                    |
| Q-31   | Độ dài kỳ mục tiêu        | TB      | Đã quyết (D-51) |                    |
| Q-32   | Cây alignment             | TB      | Đã quyết (D-51) |                    |
| Q-33   | Trạng thái task           | TB      | Đã quyết (D-51) |                    |
| Q-34   | Mô hình workload          | TB      | Đã quyết (D-51) |                    |
| Q-35   | Lịch trong MVP            | TB      | Đã quyết (D-51) |                    |
| Q-39   | Burn ròng, runway         | TB      | Một phần (D-51) |                    |
| Q-41   | Theo dõi quyết định 30/60/90 | Thấp | Đã quyết (D-51) |                    |
| Q-42   | Danh mục, tài khoản tiền mặt | TB   | Đã quyết (D-51) |                    |
| D-16   | Trường trọng yếu, ngưỡng  | TB      | Đã quyết (D-51) |                    |
| D-29   | Ngưỡng hiển thị vs định tuyến | TB  | Đã quyết (D-51) |                    |
| D-20   | Tài liệu chuẩn cho MET-04/13 | TB   | Đã quyết (D-51) |                    |
| D-23   | Danh sách domain          | TB      | Đã quyết (D-51) |                    |
| D-27 (phần) | Sinh trắc học, offline | TB    | Đã quyết (D-51) |                    |
| D-31   | Tích hợp lịch             | TB      | Đã quyết (D-51) |                    |
| D-33   | Màn mobile ngoài 4 việc   | Thấp    | Đã quyết (D-51) |                    |
| GAP-13 | Đơn vị hành chính         | Thấp    | Đã quyết (D-51) |                    |
| GAP-14 | Ngân sách AI              | TB      | Đã quyết (D-51) |                    |
| GAP-15 | Chính sách lưu trữ        | TB      | Đã quyết (D-51) |                    |
| GAP-18 | SLA review                | Thấp    | Đã quyết (D-51) |                    |
| GAP-21 | NFR độ trễ API            | TB      | Đã quyết (D-51) |                    |
| D-34   | Tham chiếu CON-10/11      | P2      | Đã quyết (D-34) |                    |
| D-36   | Vị trí tài liệu           | P2      | Đã quyết (D-36) |                    |
| D-35   | Thương hiệu, xưng hô AI   | P2      | Deferred (CDA xác nhận) |                    |
| —      | Giả định C1 (import `providers`) | P2 | Đã quyết (D-53) |                     |
| —      | Trạng thái `IMPLEMENTED` cho API | P2 | Đã quyết (D-52) |                     |
| —      | Branch protection ≥ 1 approval | P2 | Đã quyết (D-54), chưa áp dụng |        |

Không liệt kê (đã đóng hoặc `DEFERRED` có điều kiện rõ, không cần quyết bây giờ): Q-43 (đã trả lời qua D-41), Q-44 và Q-48 (D-42), Q-49 (D-43 — chỉ còn phần công cụ ở trên), Q-40 (D-37); D-30 (SSO `DEFERRED`), D-32 (kênh ngoài in-app `DEFERRED`).

---

## 6. Đã quyết (lưu vết)

Chuyển mục từ trên xuống đây sau khi đã chép vào Decision_Log.

| Mục | Ngày | Quyết định tóm tắt | ID trong Decision_Log |
| --- | --- | --- | --- |
| Q-51 | 15/10/2026 | Phương án A, task chủ ở TEST_Plan §12 | D-44 |
| Q-50 | 15/10/2026 | Phương án B, TC-NFR-01 cho container dữ liệu nghiệp vụ, chữ ký ≤ 90 ngày | D-45 |
| Phê duyệt Plan/TEST_Plan/CLAUDE.md | 15/10/2026 | Duyệt, hiệu lực ngay | D-46 |
| ĐX-12-1…7 | 15/10/2026 | TC-FE-01…07 | D-47 |
| Chat AI khi kill switch bật | 15/10/2026 | Vẫn hoạt động (chỉ đọc) | D-48 |
| Task frontend chat AI, Trang chủ CEO | 15/10/2026 | T-308, T-513 | D-49 |
| D-43 công cụ + provider demo | 15/10/2026 | Caddy, ClamAV, không observability; DeepSeek qua OpenRouter cho demo | D-43, D-50 |
| Câu hỏi nghiệp vụ | 15/10/2026 | Như đề xuất; Q-28, Q-29, Q-39 một phần | D-51 (+ D-16, D-20, D-23, D-27, D-28, D-29, D-31, D-33) |
| Trạng thái API, C1, branch protection | 15/10/2026 | `IMPLEMENTED`; C1 chặt; ≥ 1 approval (chưa áp dụng) | D-52, D-53, D-54 |
| D-34, D-35, D-36, R6 | 15/10/2026 | Như đề xuất; R6 không ai giữ | D-34, D-35, D-36, D-21 |
