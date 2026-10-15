# Image `proxy` (T-013): build frontend (T-012/T-111) rồi đóng gói cùng Caddy + Caddyfile — chạy demo không cần
# Node trên máy. Phiên bản ghim, phát hành ≥ 2 tuần: node 22.23.3 (khớp frontend/.nvmrc), caddy 2.11.4 (T-003).
FROM node:22.23.3-bookworm-slim AS frontend
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run -s build

FROM caddy:2.11.4
COPY infra/caddy/Caddyfile /etc/caddy/Caddyfile
COPY --from=frontend /src/dist /srv
