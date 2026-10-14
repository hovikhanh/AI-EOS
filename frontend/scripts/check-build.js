// Kiểm tra bản build frontend (T-012), chạy sau `vite build` (scripts/ci.sh, bước build-check):
// - dist/index.html không có script inline hay thuộc tính sự kiện inline (CSP không 'unsafe-inline', ADR-003);
// - manifest PWA hợp lệ và icon khai báo có trong bản build;
// - dist/sw.js tồn tại ở gốc và là một file độc lập (không import chunk khác).
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

const dist = join(import.meta.dirname, "..", "dist");
const errors = [];

const html = readFileSync(join(dist, "index.html"), "utf8");
for (const [, attrs, body] of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
  if (!/\bsrc\s*=/.test(attrs) || body.trim() !== "") {
    errors.push(`index.html có script inline: <script${attrs}>`);
  }
}
if (/<[^>]+\son[a-z]+\s*=/i.test(html)) {
  errors.push("index.html có thuộc tính sự kiện inline (on...=)");
}
if (!/<link\b[^>]*rel="manifest"[^>]*href="\/manifest\.webmanifest"/.test(html)) {
  errors.push("index.html không liên kết /manifest.webmanifest");
}

const manifestPath = join(dist, "manifest.webmanifest");
if (!existsSync(manifestPath)) {
  errors.push("thiếu dist/manifest.webmanifest");
} else {
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  for (const key of ["name", "short_name", "start_url", "display"]) {
    if (typeof manifest[key] !== "string" || manifest[key] === "") {
      errors.push(`manifest thiếu trường "${key}"`);
    }
  }
  const icons = Array.isArray(manifest.icons) ? manifest.icons : [];
  for (const size of ["192x192", "512x512"]) {
    if (!icons.some((icon) => icon.sizes === size)) {
      errors.push(`manifest thiếu icon ${size}`);
    }
  }
  for (const icon of icons) {
    if (typeof icon.src !== "string" || !existsSync(join(dist, icon.src))) {
      errors.push(`icon không có trong bản build: ${String(icon.src)}`);
    }
  }
}

const swPath = join(dist, "sw.js");
if (!existsSync(swPath)) {
  errors.push("thiếu dist/sw.js");
} else {
  const sw = readFileSync(swPath, "utf8");
  if (/\bimport\s*\(|\bimport\s*[{*"']|\bfrom\s*["']/.test(sw)) {
    errors.push("dist/sw.js import module khác; service worker phải là một file độc lập");
  }
}

if (errors.length > 0) {
  for (const error of errors) {
    console.error(`build-check: ${error}`);
  }
  process.exit(1);
}
console.log("build-check: OK (không script inline, manifest hợp lệ, sw.js độc lập)");
