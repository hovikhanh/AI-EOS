# AI-EOS — Business OKRs và chỉ số thành công

> Phiên bản: 1.0 · Ngày: 12/10/2026 · Trạng thái: **Stage 2B — chờ CDA duyệt**
> **Nguyên tắc:** không có OKR kinh doanh định lượng nào được tự đặt. Mọi chỉ tiêu dưới đây hoặc có trong nguồn (`SOURCE`), hoặc là đề xuất từ UX (`PROPOSED`), hoặc cần baseline thực tế trước khi đặt mục tiêu (`BASELINE_NEEDED`). Không chỉ tiêu nào đã được đo; không tuyên bố đạt.

## 1. Phân loại

| Nhãn | Ý nghĩa |
| --- | --- |
| `SOURCE` | Có số mục tiêu trong `BRD_Review.md`; BRD v1.1 được CDA xác nhận đã duyệt (D-01) |
| `PROPOSED` | Số mục tiêu có trong `UI_UX_Proposal.md` (đề xuất thiết kế), chưa được CDA chốt |
| `BASELINE_NEEDED` | Cần đo hiện trạng trước khi đặt hoặc đánh giá mục tiêu |
| `TBD` | Nguồn không có mục tiêu |

## 2. Objectives

### O1 — Dữ liệu vào hệ thống dễ và đáng tin (BO-08, Domain 22)

| KR | Chỉ tiêu | Mục tiêu | Nhãn | ID |
| --- | --- | --- | --- | --- |
| KR1.1 | Giảm thời gian nhập liệu so với nhập tay hoàn toàn | ≥ 70% | SOURCE + BASELINE_NEEDED (cần đo thời gian nhập tay hiện tại) | MET-08, BO-08 |
| KR1.2 | Field accuracy | ≥ 90% chung; ≥ 95% tài liệu có lớp text | SOURCE; chưa benchmark (D-08) | MET-01 |
| KR1.3 | Độ chính xác trường trọng yếu sau review | ≥ 99% | SOURCE | MET-09 |
| KR1.4 | Error leakage trường trọng yếu | < 0,5% | SOURCE | MET-06 |
| KR1.5 | Review effort | ≤ 60 giây/tài liệu | SOURCE | MET-04 |
| KR1.6 | Straight-through rate | ≥ 50% sau 3 tháng | SOURCE; tự ghi mặc định tắt cho tới khi đạt BR-05 | MET-02 |
| KR1.7 | Phân loại đúng loại tài liệu MVP | ≥ 95% | SOURCE | MET-07 |
| KR1.8 | Time to data | p50 ≤ 5 phút (chưa tính chờ review) | SOURCE | MET-03 |
| KR1.9 | Chi phí AI + hạ tầng / tài liệu | Theo dõi, có ngân sách trần | SOURCE; trần TBD (GAP-14) | MET-05 |

### O2 — CEO biết tình hình và giao việc nhanh (lời hứa MVP)

| KR | Chỉ tiêu | Mục tiêu | Nhãn | ID |
| --- | --- | --- | --- | --- |
| KR2.1 | Giờ/tuần CEO tiết kiệm cho tổng hợp báo cáo | ≥ 5 giờ | SOURCE + BASELINE_NEEDED | MET-11 |
| KR2.2 | Thời gian từ phát hiện rủi ro đến hành động | TBD | TBD + BASELINE_NEEDED | MET-11 |
| KR2.3 | Thời gian CEO mở app → biết việc cần làm | ≤ 10 giây | PROPOSED | MET-12 |
| KR2.4 | Hoàn thành luồng F1–F5 phạm vi MVP không cần hỗ trợ | ≥ 90% | PROPOSED | MET-14 |

### O3 — Hệ thống được dùng thật (adoption)

| KR | Chỉ tiêu | Mục tiêu | Nhãn | ID |
| --- | --- | --- | --- | --- |
| KR3.1 | WAU / tổng user | ≥ 70% | SOURCE | MET-10 |
| KR3.2 | % KPI cập nhật đúng hạn | ≥ 90% | SOURCE; định nghĩa "đúng hạn" chờ Q-30 | MET-10 |
| KR3.3 | % dữ liệu vào qua AI capture | TBD | TBD | MET-10 |
| KR3.4 | Tỷ lệ quản lý dùng hàng tuần | ≥ 80% | PROPOSED | MET-16 |
| KR3.5 | Điểm SUS sau 30 ngày | ≥ 75 | PROPOSED | MET-15 |

### O4 — AI đáng tin và an toàn

| KR | Chỉ tiêu | Mục tiêu | Nhãn | ID |
| --- | --- | --- | --- | --- |
| KR4.1 | Action card L2 được xác nhận không sửa | ≥ 60% và tăng dần | PROPOSED | MET-17 |
| KR4.2 | Tỷ lệ hoàn tác hành động L3 | ≤ 5% | PROPOSED | MET-18 |
| KR4.3 | Tỷ lệ câu trả lời AI được mở nguồn | Theo dõi, không ngưỡng | PROPOSED | MET-19 |
| KR4.4 | Con số AI đưa ra có nguồn | 100% (hoặc gắn nhãn "ước tính") | SOURCE (quy tắc) | BR-14 |

## 3. Không có trong nguồn

- Mục tiêu kinh doanh (doanh thu, số khách hàng, chi phí vận hành của doanh nghiệp dùng AI-EOS): **không có** — không đặt.
- Ngưỡng cảnh báo chỉ số sức khỏe (BRD §4.3) là "gợi ý", không phải OKR (ASM-03, D-28).

## 4. Đo lường

Phương pháp đo từng chỉ số: SRS §13 (NFR và chỉ số). Trước khi đánh giá KR có nhãn `BASELINE_NEEDED`, cần một đợt đo hiện trạng trong giai đoạn khám phá/pilot (UX §10.2).
