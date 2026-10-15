# Image backend cho `api`, `worker`, `migrate` và CLI quản trị (T-013, D-43; Architecture §9.1).
# Phiên bản ghim, phát hành ≥ 2 tuần: python 3.12.14 (khớp runtime T-002), uv 0.12.11 (khớp CI).
FROM astral/uv:0.12.11 AS uv

FROM python:3.12.14-slim-bookworm AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
# Phụ thuộc trước (cache lớp), mã nguồn sau; chỉ nhóm runtime (không dev/audit), cài không editable.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-group audit --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-group audit --no-editable

FROM python:3.12.14-slim-bookworm
RUN useradd --system --uid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin aieos \
    && mkdir -p /data/storage && chown aieos /data/storage
COPY --from=build /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER aieos
WORKDIR /nonexistent
EXPOSE 8000
CMD ["uvicorn", "--factory", "aieos.app.asgi:create_app", "--host", "0.0.0.0", "--port", "8000"]
