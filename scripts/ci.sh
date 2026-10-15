#!/usr/bin/env bash
# Nguồn lệnh kiểm tra thống nhất cho local và GitHub Actions (T-002, Implementation_Plan §11.3).
# Chạy tuần tự, dừng ở bước lỗi đầu tiên và in: "CI FAILED step=<tên> rc=<mã>".
#
# Biến môi trường:
#   AIEOS_REQUIRE_DB=1          bắt buộc test PostgreSQL (CI đặt biến này); thiếu URL → thất bại
#   AIEOS_TEST_DATABASE_URL     chuỗi kết nối PostgreSQL dùng cho test `db` (không in ra log)
#   AIEOS_REQUIRE_DOCKER=1      bắt buộc kiểm Compose (scripts/check_compose.py, T-003); không có docker → thất bại
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
NODE_MIN="22.22.2"
NODE_MAJOR="22"
PYTHON_SERIES="3.12"

step() {
  local name="$1"
  shift
  echo "==> [$name]"
  "$@"
  local rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "CI FAILED step=$name rc=$rc"
    exit "$rc"
  fi
  echo "<== [$name] OK"
}

check_runtime() {
  local py
  # Kiểm tra đúng interpreter mà các lệnh uv sau sẽ dùng: `uv python find` không tự áp UV_PYTHON.
  py="$(cd "$BACKEND" && uv python find ${UV_PYTHON:+"$UV_PYTHON"})" || return 1
  "$py" -c "import sys; v = sys.version_info; print(f'Python {v.major}.{v.minor}.{v.micro}'); \
sys.exit(0 if f'{v.major}.{v.minor}' == '$PYTHON_SERIES' else 1)" || {
    echo "Cần Python $PYTHON_SERIES.x"
    return 1
  }
  node -e "
    const [ma, mi, pa] = process.versions.node.split('.').map(Number);
    const [rma, rmi, rpa] = '$NODE_MIN'.split('.').map(Number);
    const ok = ma === $NODE_MAJOR && (mi > rmi || (mi === rmi && pa >= rpa));
    console.log('Node ' + process.versions.node);
    process.exit(ok ? 0 : 1);
  " || {
    echo "Cần Node >= $NODE_MIN và < $((NODE_MAJOR + 1))"
    return 1
  }
}

in_backend() { (cd "$BACKEND" && "$@"); }
in_frontend() { (cd "$FRONTEND" && "$@"); }

audit_python() {
  local req rc
  req="$(mktemp)"
  in_backend uv export --locked --all-groups --no-emit-project --format requirements-txt -q -o "$req" || {
    rm -f "$req"
    return 1
  }
  in_backend uv run --locked pip-audit --strict --disable-pip --require-hashes --progress-spinner off -r "$req"
  rc=$?
  rm -f "$req"
  return "$rc"
}

step runtime check_runtime
step docs python3 "$ROOT/scripts/check_docs.py"
step compose python3 "$ROOT/scripts/check_compose.py"

step backend-lock in_backend uv lock --check
step backend-sync in_backend uv sync --locked
step ruff-check in_backend uv run --locked ruff check
step ruff-format in_backend uv run --locked ruff format --check
step mypy in_backend uv run --locked mypy
step import-contracts in_backend uv run --locked lint-imports
step pytest in_backend uv run --locked pytest

step frontend-install in_frontend npm ci --no-audit --no-fund
step eslint in_frontend npm run -s lint
step prettier in_frontend npm run -s format:check
step tsc in_frontend npm run -s typecheck
step vitest in_frontend npm run -s test
step vite-build in_frontend npx vite build
step build-check in_frontend npm run -s check:build

step audit-python audit_python
step audit-npm in_frontend npm audit --audit-level=high

if [ -z "${AIEOS_TEST_DATABASE_URL:-}" ]; then
  echo "PostgreSQL: NOT RUN — chưa xác minh (thiếu AIEOS_TEST_DATABASE_URL)"
fi
echo "CI OK"
