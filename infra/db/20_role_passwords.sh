#!/bin/bash
# Khởi tạo CSDL lần đầu (T-013): đặt mật khẩu cho role aieos_app, aieos_owner (role tạo bởi 10_provision_roles.sql,
# T-005) từ Docker secrets. Không in mật khẩu. Chạy bởi entrypoint của image postgres, chỉ khi thư mục dữ liệu trống.
set -euo pipefail
app_password="$(cat /run/secrets/db_app_password)"
owner_password="$(cat /run/secrets/db_owner_password)"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  -v app_password="$app_password" -v owner_password="$owner_password" <<'SQL'
ALTER ROLE aieos_app PASSWORD :'app_password';
ALTER ROLE aieos_owner PASSWORD :'owner_password';
SQL
