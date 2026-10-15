# infra

Docker Compose và cấu hình triển khai một máy (Architecture §9.1, ADR-004). T-003 (D-43): **cấu hình** — `compose.yaml`, `caddy/Caddyfile`, kiểm tra tĩnh `scripts/check_compose.py` (bước `compose` của `scripts/ci.sh`). T-013: Dockerfile `api`/`worker`, chạy `docker compose up` đủ service vượt healthcheck, TC-NFR-01 — **chưa làm**; trước T-013 lệnh `up` không chạy được vì chưa có Dockerfile.

## Service

| Service | Mạng | Ghi chú |
| --- | --- | --- |
| `proxy` | `edge`, `backend` | Caddy 2.11.4; cổng duy nhất publish: 443; TLS nội bộ (`tls internal`); `/api/*` → `api:8000`, còn lại phục vụ bản build frontend `../frontend/dist` |
| `api` | `backend` | `uvicorn --factory aieos.app.asgi:create_app`; tin header `X-Forwarded-For` (chỉ nhận kết nối từ mạng `backend`) để rate limit theo IP thật (T-102) |
| `worker` | `backend` | `python -m aieos.app worker` |
| `migrate` | `backend` | profile `ops`, role chủ sở hữu CSDL; chạy tay, không chạy khi `api` khởi động |
| `db` | `backend` | PostgreSQL 18.6; không publish cổng; tạo role bằng `provision_roles.sql` khi khởi tạo lần đầu |
| `scanner` | `backend` | ClamAV 1.5.4; không tự tải chữ ký (`backend` không có đường ra) |
| `scanner-updater` | `egress` | Chỉ tải chữ ký ClamAV vào volume `clamav_db`; không gắn volume dữ liệu (ngoại lệ TC-NFR-01, D-45) |

Mạng `backend` là `internal: true` — `api`, `worker`, `db`, `scanner` không có đường ra internet. Không có profile `llm`/`observability` (D-43).

## Chuẩn bị (không commit)

- `infra/.env`: cấu hình theo `.env.example` (tên biến, Implementation_Plan §7). Đường dẫn storage, URL secret đã đặt trong `compose.yaml`.
- `infra/secrets/`: mỗi secret một file — `postgres_password`, `database_url` (role `aieos_app`), `database_owner_url` (role `aieos_owner`), `csrf_key`, `totp_encryption_key` (32 byte base64, vd. `openssl rand -base64 32`). Compose gắn vào `/run/secrets/…`; ứng dụng đọc qua `<TÊN>_FILE` (T-004).
- Mật khẩu role `aieos_owner`/`aieos_app` đặt sau khi `db` khởi tạo (vd. `\password` trong `psql`), khớp với `database_url`/`database_owner_url`.

## Lệnh (sau T-013)

```bash
cd infra
docker compose --profile ops run --rm migrate
docker compose up -d
docker compose run --rm api python -m aieos.app bootstrap-admin --email <email> --display-name "<tên>"
```

`.env.example` (T-004): danh sách tên biến cấu hình/secret, **không có giá trị**. Loader: `backend/src/aieos/platform/config.py` — thiếu biến bắt buộc thì tiến trình dừng (mã 2), thông báo chỉ nêu tên biến.
