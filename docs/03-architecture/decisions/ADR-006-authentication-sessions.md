# ADR-006 — Xác thực: session phía server, Argon2id, CSRF, MFA

| Trường | Giá trị |
| --- | --- |
| Status | CONFIRMED |
| Source | `ARCHITECTURE_DECISION` — `Pre2C_Decision_Proposals.md` §2.5; quy trình tài khoản A1–A6 là `CDA_DIRECTIVE` (yêu cầu 12/10/2026 §6) |
| Liên quan | D-22, D-30; GAP-09 |
| Ngày cập nhật | 12/10/2026 |

## Context
Nguồn AI-EOS không có yêu cầu xác thực (GAP-09). Cần thu hồi quyền tức thời khi đổi role (A3), không có tài khoản mặc định hay secret hardcode, ADMIN đầu tiên qua bootstrap (A2).

## Decision
- **Mật khẩu:** băm Argon2id bằng thư viện đã kiểm chứng; tham số theo khuyến nghị hiện hành, lưu kèm hash để nâng cấp dần.
- **Session phía server:** token ngẫu nhiên ≥ 256 bit, CSDL lưu **hash** của token; cookie `__Host-` prefix, `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`. Hết hạn khi không hoạt động và hết hạn tuyệt đối (giá trị cấu hình). **Đổi session ID sau đăng nhập và sau xác thực MFA** (chống session fixation).
- **CSRF:** token đồng bộ gắn với session, gửi qua header `X-CSRF-Token` cho mọi method thay đổi trạng thái; kiểm tra thêm `Origin`.
- **MFA:** TOTP; **bắt buộc với ADMIN**; với role khác là tùy chọn (D-30 còn mở). Mã khôi phục dùng một lần, lưu hash.
- **Step-up (xác thực lại):** bắt buộc cho thay đổi role/assignment, bật/tắt kill switch, cấu hình autonomy, khóa/mở kỳ, thay đổi thời hạn bản nháp; hiệu lực ngắn (giá trị cấu hình).
- **Chống brute force:** giới hạn tốc độ theo tài khoản và IP; khóa tạm theo số lần sai; thông báo lỗi đăng nhập không phân biệt "sai email" và "sai mật khẩu".
- **Cấp tài khoản (A1):** ADMIN tạo tài khoản ở trạng thái `INVITED` + lời mời; token mời ngẫu nhiên, **lưu hash**, có hạn, dùng một lần, thu hồi khi dùng/hết hạn/ADMIN hủy. Không có mật khẩu mặc định. Kênh gửi: ADMIN nhận link một lần trên giao diện để trao trực tiếp; email là adapter tùy chọn, không giả định đã cấu hình (K6).
- **Bootstrap (A2):** lệnh CLI `bootstrap-admin` chạy trong container, nhận email qua tham số, mật khẩu qua nhập tương tác hoặc file secret; từ chối nếu đã tồn tại ADMIN đang hoạt động; tài khoản tạo ra buộc đăng ký MFA trước khi dùng; ghi audit `actor_type=BOOTSTRAP`.
- **Khôi phục (A6):** lệnh CLI `recover-admin` yêu cầu quyền truy cập máy chủ + cờ xác nhận tường minh; vô hiệu mọi session của tài khoản đích; buộc đặt lại mật khẩu và MFA; ghi audit `actor_type=BOOTSTRAP` kèm lý do; tạo thông báo cho mọi ADMIN khác.
- **Không có endpoint đăng ký công khai.**
- **OIDC/SSO:** interface `IdentityProvider` cho phép thêm đăng nhập OIDC sau (D-30, DEFERRED); khi thêm, role vẫn do AI-EOS quản lý (không lấy role từ claim của IdP mặc định).

## Alternatives
| Phương án | Lý do không chọn |
| --- | --- |
| IdP tự host (Keycloak…) qua OIDC | Nặng, thêm vận hành; SSO chưa có yêu cầu (D-30) |
| JWT stateless | Không thu hồi tức thời khi đổi role (A3) |

## Consequences
- Mỗi request tra session trong CSDL (có thể cache ngắn hạn trong process; khi thu hồi phải xóa cache).
- Môi trường local cần HTTPS để cookie `Secure` hoạt động: reverse proxy cấp chứng chỉ nội bộ (Architecture §9).

## Security Considerations
- Đổi role/assignment, khóa tài khoản, đổi mật khẩu → **thu hồi mọi session** của tài khoản đích (A3).
- Token mời và token session không bao giờ ghi vào log/audit (chỉ ghi ID).
- Secret TOTP lưu mã hóa bằng khóa ứng dụng nạp từ secret, không lưu khóa trong CSDL.
- Bootstrap/recovery không có trên HTTP.
