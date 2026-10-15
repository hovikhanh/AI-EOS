# AI-EOS — Session checkpoint (Q-51)

> Tạo: 14/10/2026 20:33 (+07). Loại: checkpoint bàn giao phiên, **không** phải tài liệu quyết định. Nguồn sự thật vẫn là Decision_Log, Implementation_Plan, Handoff, TEST_Plan; nếu lệch, tài liệu gốc thắng.
> File này **chưa commit** (untracked) — theo yêu cầu không tạo commit/PR chỉ để lưu checkpoint. Ngày mai `git status` sẽ hiện `?? docs/04-delivery/SESSION_CHECKPOINT.md`; đó là file này.
> Nhãn: **[ĐÃ XÁC MINH]** = kiểm tra bằng lệnh lúc tạo checkpoint · **[THEO BÁO CÁO]** = từ báo cáo phiên, chưa kiểm lại lúc tạo · **[ĐỀ XUẤT]** = đề xuất của người phân tích · **[CHỜ CDA]** = cần CDA quyết định.

## 1. Repository, Git, CI — [ĐÃ XÁC MINH] lúc 14/10/2026 20:33

| Mục | Giá trị | Cách xác minh |
| --- | --- | --- |
| Repo | `/home/vika/CyEyes/AI-EOS` (remote `git@github.com:hovikhanh/AI-EOS.git`) | `pwd` |
| Branch / working tree | `main`, sạch (trước khi tạo file này) | `git status --short --branch` |
| HEAD = `origin/main` | `04f41bb` — "docs: Q-51 TC ownership draft analysis (PROPOSED) (#14)" | `git rev-parse HEAD origin/main` sau `git fetch` |
| CI gần nhất trên `main` | run `38550151393`, `completed`/`success`, commit `04f41bb` | GitHub API `actions/runs?branch=main` |
| PR #14 | merged, merge commit `04f41bb`; CI PR run `38549981993` (122 passed, 0 skipped) [THEO BÁO CÁO cho số test] | GitHub API `pulls/14` |
| PR đang mở | 0 | GitHub API `pulls?state=open` |
| Branch protection `main` | required check `ci`, `enforce_admins: true`, bắt buộc PR | GitHub API `branches/main/protection` |
| Repo cha `/home/vika/CyEyes` | HEAD `0a1a629`, 0 file staged; không thao tác ghi | `git -C /home/vika/CyEyes …` |
| `check_docs.py` | 0 lỗi, 0 cảnh báo | `python3 scripts/check_docs.py` |
| `scripts/ci.sh` local | rc 0: 111 passed, 11 skipped (test PostgreSQL — máy không có PostgreSQL), Vitest 47 passed [THEO BÁO CÁO, lần chạy lại trong phiên] | — |

Lưu ý phiên: lần chạy `ci.sh` đầu tiên trong phiên **không chạy thật** (`git diff --check` dừng chuỗi `&&` vì dòng trống thừa; `grep` không có file nên treo tới timeout). Đã sửa và chạy lại riêng; kết quả trên là lần chạy lại. Bài học: không nối kiểm tra bằng `;` sau `&&`, không pipe lệnh kiểm tra qua `tail` (mất exit code).

Môi trường local: Node 22.23.3 cài trong scratchpad của phiên (không phải mặc định máy — mặc định Node 24, sẽ bị chặn bởi bước runtime); phiên mới cần cài lại (`N_PREFIX=<thư mục tạm> n install 22.23.3`). `gh` 2.4 cũ: `gh pr edit` lỗi GraphQL Projects classic → dùng `gh api` REST.

## 2. Q-51 — **PROPOSED / CHƯA ĐƯỢC CDA PHÊ DUYỆT**

- Decision_Log: Q-51 `NEEDS_CONFIRMATION` (mục 8; hồ sơ mục 3.7) [ĐÃ XÁC MINH: dòng Q-51 không có "Đã trả lời"].
- Dự thảo phân tích: [Q-51_TC_Ownership_Draft.md](Q-51_TC_Ownership_Draft.md) (merge PR #14). **Merge PR không phải phê duyệt của CDA.** Chưa gán ID `D-xx`.
- Handoff §16: nhật ký phiên trỏ tới dự thảo.

### 2.1. Kết quả rà soát [ĐỀ XUẤT — nội dung chi tiết ở dự thảo]

- 65/199 TC được gán cho ≥ 2 task (Handoff §5 cột "Test case") — đếm bằng script đọc Plan §4, Handoff §5, TEST_Plan.
- Quy tắc đề xuất R1–R7 (dự thảo mục 2): mỗi TC đúng một task chủ; TC chỉ đạt khi task chủ chạy toàn bộ kịch bản xanh; bằng chứng thành phần ở task khác **không** là PASS; tách TC không tạo ID mới (`TC-XXX-NN (phần …)`).
- Task chủ đề xuất (dự thảo mục 3): 57 TC có chủ trong số task đang tham chiếu (5 TC-E2E chưa kiểm chứng được vì dependency T-608 ghi chung), 1 TC chủ ngoài danh sách (TC-SEC-05 → T-602), **7 TC chưa có chủ** (xung đột).
- 7 xung đột dependency (không task nào chạy đủ): TC-DR-02 (T-605 ↛ T-203), TC-FIN-14 (T-110 ↛ T-401), TC-REV-05 (không task nào phụ thuộc cả T-207 và T-408), TC-SEC-01, TC-SEC-02 (T-602 ↛ T-013), TC-SEC-06 (không task nào phụ thuộc cả T-112 và T-206), TC-MIG-02 (chỉ T-511 đủ — không hợp lý).
- 10 TC bị Plan §4 gán vào DoD của hai task: TC-CAP-05, TC-CAP-06, TC-E2E-01…05, TC-FIN-14, TC-KS-08, TC-KS-09.
- Dependency chung chung: T-601 ("các API"), T-608 ("Các task frontend"). Khoảng trống: T-510 dùng lineage nhưng không phụ thuộc T-211.
- TC đề xuất tách thành phần: TC-ACC-04, TC-ACC-05, TC-AIC-02, TC-FILE-03, TC-SEC-01, TC-SEC-06, TC-MIG-02.
- Nguy cơ ghi đạt khi mới kiểm tra một phần: TC-MIG-01, TC-MIG-02, TC-GEN-03, TC-ACC-02, TC-GEN-06, TC-SEC-04, TC-FILE-03 (cách chặn: dự thảo mục 6).
- Không vòng phụ thuộc trên 58 TC có chủ (kiểm tự động).
- Theo đề xuất: T-005 chỉ làm chủ TC-MIG-01; T-006, T-011 không làm chủ TC nào (chỉ bằng chứng thành phần).

### 2.2. Bốn nhóm câu hỏi [CHỜ CDA] — không tự trả lời

1. Duyệt R1–R7 (gồm "test tương ứng" = TC mà task làm chủ)? Có chuyển T-005, T-006, T-011 sang `DONE` không, theo tiêu chí nào?
2. 10 TC gán trùng trong Plan §4: chấp nhận task chủ đề xuất? Liệt kê cụ thể dependency của T-601, T-608 thế nào?
3. Từng TC trong 7 TC xung đột: (a) thêm dependency hay (b) tách TC và chỉ định mốc tổng hợp?
4. TC-MIG-01 ghi đạt ở T-005 với phạm vi revision hiện có (`0001`) và bắt buộc xanh ở mọi CI sau? TC-MIG-02 chỉ đạt khi đủ INV-01…16 tại mốc nào?

### 2.3. Sau khi CDA duyệt (chưa làm) — dự thảo mục 10

Decision_Log (quyết định mới + gán `D-xx`, dòng Q-51, mục 3.7) · Implementation_Plan §2, §4, §10 · Handoff §5 (cột "Task chủ") · TEST_Plan (bảng task chủ, không đổi nội dung TC) · Requirements_Traceability · tùy chọn `check_docs.py`. Chỉ áp dụng đúng phạm vi được duyệt; đổi trạng thái task/TC chỉ khi có quyết định và bằng chứng.

## 3. Trạng thái task / quyết định liên quan

| Mục | Trạng thái | Nhãn |
| --- | --- | --- |
| T-001, T-002, T-004 | `DONE` | [ĐÃ XÁC MINH] Plan §10 |
| T-005, T-006, T-011 | `IN_REVIEW` (chờ Q-51) | [ĐÃ XÁC MINH] Plan §10 |
| T-012 | `IN_REVIEW` (chờ duyệt `ĐX-12-1…7`; chưa vào TEST_Plan, không đổi thành `TC-*`) | [ĐÃ XÁC MINH] |
| T-003, T-013 | `BLOCKED` (công cụ D-43 `PROPOSED`, Q-50) | [ĐÃ XÁC MINH] Plan §4 |
| Task khác | `TODO`; không task nào đủ điều kiện bắt đầu. T-005 là dependency duy nhất còn thiếu của T-007, T-008, T-010, T-101 | [THEO BÁO CÁO] tính ở phiên lần 5 |
| D-42 (Q-48, Q-44) | CONFIRMED: `platform` (config/secret, DB/Alembic, log/health/FastAPI, HTTP), composition root `aieos/app/` | [ĐÃ XÁC MINH] Decision_Log |
| D-43 (Q-49) | CONFIRMED tách DoD/dependency T-003/T-013; **công cụ `PROPOSED`** (Caddy, ClamAV, không observability, hoãn `llm`) | [CHỜ CDA] phần công cụ |
| Q-50 | NEEDS_CONFIRMATION — cập nhật chữ ký scanner vs TC-NFR-01 (Decision_Log 3.6.3, phương án A–D) | [CHỜ CDA] |
| TEST_Plan | 199 TC, tất cả `NOT RUN` | [ĐÃ XÁC MINH] `check_docs.py` |

## 4. Ràng buộc không được vi phạm

- Chỉ thao tác trong `/home/vika/CyEyes/AI-EOS`; không ghi gì vào repo cha `CyEyes`.
- Không push `main`, không force-push, không bypass protection: branch → commit → push → PR → `ci` xanh → merge.
- Không tự coi Q-51, D-43 (công cụ), Q-50, `ĐX-12-1…7` là đã duyệt; không đổi trạng thái task/TC; không gán `D-xx`.
- Không xóa TC, không hạ yêu cầu bảo mật, không ghi PASS khi mới kiểm một phần; bằng chứng thành phần không phải PASS.
- Không cho scanner ra Internet, không tự chọn cơ chế/tuổi chữ ký.
- Không triển khai code cho phần đang chờ CDA.

## 5. Việc tiếp theo (theo thứ tự)

1. Kiểm tra (không sửa file): `cd /home/vika/CyEyes/AI-EOS && pwd && git fetch --prune && git status --short --branch && git log -5 --oneline && git rev-parse HEAD origin/main`; kiểm CI mới nhất trên `main`, PR mở; `git -C /home/vika/CyEyes rev-parse --short HEAD` (mong đợi `0a1a629`) — chỉ đọc.
2. Tìm bằng chứng CDA trả lời Q-51 (Decision_Log mục 8 dòng Q-51, PR/commit mới, chỉ đạo trong phiên).
3. **Chưa có phê duyệt** → chỉ làm hồ sơ: biểu mẫu phản hồi CDA cho 4 nhóm câu hỏi (mỗi TC xung đột một lựa chọn a/b), rà tính nhất quán của dự thảo; không áp dụng quyết định.
4. **Có phê duyệt** → trích nguyên văn, xác định đúng phạm vi duyệt, lập kế hoạch cập nhật tài liệu theo mục 2.3; không suy rộng.
5. Song song chờ CDA: D-43 (công cụ) + Q-50 → mở T-003; `ĐX-12-1…7` → T-012 `DONE`.
6. Trước khi kết thúc phiên: cập nhật file này (commit/PR/CI, file đổi, trạng thái task/TC, quyết định còn chờ).
