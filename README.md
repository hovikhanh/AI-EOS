# AI-EOS

Hệ thống điều hành doanh nghiệp có AI hỗ trợ, triển khai nội bộ. Tài liệu yêu cầu và thiết kế: [`docs/`](docs/) — bắt đầu từ [Implementation_Handoff](docs/Implementation_Handoff.md); quy tắc cho coding agent: [CLAUDE.md](CLAUDE.md).

> Trạng thái: khung repo (T-001) và toolchain/CI (T-002). Chưa có chức năng, API, CSDL, migration hay Docker.

## Cấu trúc

| Thư mục | Nội dung |
| --- | --- |
| `backend/` | Python package `aieos` (src layout); mỗi module của Architecture §3 là một package con (ADR-001, ADR-002) |
| `frontend/` | React + Vite + TypeScript strict (ADR-003) |
| `infra/` | Docker Compose — tạo ở T-003 |
| `docs/` | Tài liệu dự án |
| `scripts/` | `ci.sh` — mọi bước kiểm tra (local và GitHub Actions); `negative_checks.sh` — kiểm tra âm N1–N19; `check_docs.py` — kiểm tra tài liệu |
| `.github/workflows/` | `ci.yml` — GitHub Actions gọi `scripts/ci.sh` với PostgreSQL 18 |

## Yêu cầu môi trường

| Công cụ | Phiên bản | Ghi ở |
| --- | --- | --- |
| Python | 3.12.x | `backend/.python-version`, `backend/pyproject.toml` (`requires-python`), `backend/uv.lock` |
| uv | 0.12.x | Quản lý môi trường và lockfile Python; build backend `uv_build` |
| Node.js | 22 LTS (≥ 22.22.2, do jsdom 30 yêu cầu) | `frontend/.nvmrc` (22.23.3), `frontend/package.json` (`engines`, bị chặn nếu sai nhờ `frontend/.npmrc`) |
| npm | đi kèm Node 22 | `frontend/package-lock.json` |

Nếu máy chưa có: `uv python install 3.12` cài Python do uv quản lý (không thay `python3` của hệ thống); Node 22 cài bằng trình quản lý phiên bản bất kỳ (nvm, n, fnm…).

## Chạy local

Toàn bộ kiểm tra (giống GitHub Actions, dừng ở bước lỗi đầu tiên):

```bash
scripts/ci.sh
```

Không đặt `AIEOS_TEST_DATABASE_URL` thì test PostgreSQL không chạy và script in "PostgreSQL: NOT RUN — chưa xác minh". Có PostgreSQL 18:

```bash
AIEOS_REQUIRE_DB=1 AIEOS_TEST_DATABASE_URL=postgresql://<user>@<host>:5432/<db> scripts/ci.sh
```

Từng phần:

```bash
cd backend
uv sync --locked
uv run --locked ruff check && uv run --locked ruff format --check
uv run --locked mypy
uv run --locked lint-imports      # import-contract C1–C3
uv run --locked pytest            # gồm test cấu trúc và C4

cd ../frontend
npm ci
npm run lint && npm run format:check && npm run typecheck
npm run test
npm run build      # kết quả ở frontend/dist/
npm run dev        # máy chủ phát triển Vite
```

Kiểm tra âm (chạy trên bản sao tạm, không sửa repo; cần mạng; vài phút):

```bash
AIEOS_N17_NODE_DIR=<thư mục có node khác major 22> scripts/negative_checks.sh
```

Docker Compose ở T-003; cấu hình/secret ở T-004; CSDL và migration ở T-005.
