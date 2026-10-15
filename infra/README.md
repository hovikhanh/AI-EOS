# infra

Docker Compose triển khai một máy (Architecture §9.1, ADR-004). T-003: cấu hình (`compose.yaml`, `caddy/Caddyfile`, kiểm tra tĩnh `scripts/check_compose.py`). T-013: image (`backend/Dockerfile`, `caddy/Dockerfile` — đóng gói frontend), khởi tạo CSDL (`db/20_role_passwords.sh`), sinh secret (`scripts/init_secrets.py`), smoke test tích hợp + TC-NFR-01 (`scripts/compose_smoke.py`, bước `compose-smoke` của `scripts/ci.sh`).

## Service

| Service | Mạng | Ghi chú |
| --- | --- | --- |
| `proxy` | `edge`, `backend` | Caddy 2.11.4 + bản build frontend; cổng duy nhất publish: 443; TLS nội bộ (`tls internal`); `/api/*` → `api:8000` |
| `api` | `backend` | uvicorn; tin `X-Forwarded-For` (chỉ nhận kết nối từ mạng `backend`) để rate limit theo IP thật |
| `worker` | `backend` | `python -m aieos.app worker`; healthcheck `python -m aieos.app health` (CSDL + migration ở head) |
| `migrate` | `backend` | profile `ops`, role chủ sở hữu CSDL; chạy tay, không chạy khi `api` khởi động |
| `db` | `backend` | PostgreSQL 18.6; không publish cổng; khởi tạo lần đầu: tạo role (`provision_roles.sql`) + đặt mật khẩu role từ secret |
| `scanner` | `backend` | ClamAV 1.5.4; không tự tải chữ ký |
| `scanner-updater` | `egress` | Chỉ tải chữ ký vào volume `clamav_db`; không gắn volume dữ liệu (ngoại lệ TC-NFR-01, D-45) |

Mạng `backend` là `internal: true` — `api`, `worker`, `db`, `scanner` không có đường ra internet (TC-NFR-01). Không có profile `llm`/`observability` (D-43).

## Chạy demo (máy có Docker + Docker Compose v2.24+, cổng 443 trống)

```bash
cd infra
python3 scripts/init_secrets.py          # sinh infra/secrets/ (không commit); chạy lại không ghi đè
cp demo.env .env                         # cấu hình MINH HỌA — triển khai thật do người vận hành đặt
docker compose build
docker compose up -d --wait db
docker compose --profile ops run --rm migrate
docker compose up -d                     # đợi `docker compose ps` báo healthy (scanner tải chữ ký lần đầu ~1–3 phút)

# Tạo ADMIN đầu tiên (nhập mật khẩu 2 lần, ≥ AIEOS_PASSWORD_MIN_LENGTH ký tự):
docker compose run --rm api python -m aieos.app bootstrap-admin --email admin@example.com --display-name "Quản trị"
```

Trên trình duyệt mở **https://localhost** (chứng chỉ do CA nội bộ của Caddy cấp → trình duyệt cảnh báo; chấp nhận để tiếp tục, hoặc tin cậy CA: `docker compose cp proxy:/data/caddy/pki/authorities/local/root.crt .`):

1. Đăng nhập bằng ADMIN → màn **Đăng ký MFA**: thêm khóa vào ứng dụng xác thực (Google Authenticator, Aegis…), nhập mã 6 số → lưu 10 mã khôi phục.
2. **Người dùng** → Tạo tài khoản (email, tên, role, lý do) → hộp thoại **Xác thực lại** (mật khẩu + mã MFA) → sao chép **link mời** (hiển thị một lần).
3. Mở link mời trong cửa sổ ẩn danh → đặt mật khẩu → **Đăng nhập** bằng tài khoản mới (EMPLOYEE không thấy mục quản trị).

Dừng: `docker compose down` (giữ dữ liệu) hoặc `docker compose down -v` (xóa cả CSDL, chữ ký, chứng chỉ). Khôi phục ADMIN mất MFA: `docker compose run --rm api python -m aieos.app recover-admin --email … --reason "…" --confirm`.

Kiểm tra tự động cùng luồng (tự dựng project `aieos-smoke`, dọn khi xong): `python3 scripts/compose_smoke.py` từ gốc repo.

## Cấu hình và secret

- `infra/.env`: cấu hình (tên biến ở `.env.example`; `demo.env` là giá trị minh họa, **không** phải giá trị đã duyệt). `AIEOS_ALLOWED_ORIGINS` phải khớp địa chỉ mở trên trình duyệt (`https://localhost`).
- `infra/secrets/` (thư mục 0700, không commit): `postgres_password`, `db_app_password`, `db_owner_password`, `database_url`, `database_owner_url`, `csrf_key`, `totp_encryption_key`. Compose gắn vào `/run/secrets/…`; ứng dụng đọc qua `<TÊN>_FILE` (T-004). Mật khẩu role CSDL chỉ được đặt khi `db` khởi tạo lần đầu — đổi sau đó phải làm thủ công.
- Chưa có: backup/WAL (T-605), giám sát tuổi chữ ký ≤ 90 ngày (D-45, vận hành), provider AI (T-204/T-205; đường ra cho provider cloud chưa cấu hình — D-50).
