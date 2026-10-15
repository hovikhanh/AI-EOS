// T-607 — truy cập (WCAG 2.1 AA, SRS-NFR-08) và i18n vi/en (SRS-NFR-05). TC-NFR-05: phần tự động (axe-core trên từng
// màn, tương phản token màu, thao tác bàn phím chính); kiểm tra bàn phím thủ công toàn bộ ghi ở Implementation_Plan.
// TC-NFR-02: phần giao diện (nhãn đúng ngôn ngữ); phần AI trả lời theo ngôn ngữ câu hỏi chờ T-306.
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import axe from "axe-core";
import { createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi as vitest } from "vitest";
import { setCsrfToken } from "./api/client";
import { createQueryClient } from "./api/queryClient";
import { App } from "./App";
import { en } from "./i18n/en";
import { vi } from "./i18n/vi";
import CSS from "./index.css?raw";
import { routes } from "./routes";

// Mã nguồn giao diện (không gồm test, từ điển) đọc qua Vite để quét chuỗi viết cứng.
const SOURCES = import.meta.glob<string>(["./**/*.{ts,tsx}", "!./**/*.test.{ts,tsx}", "!./i18n/**"], {
  query: "?raw",
  import: "default",
  eager: true,
});

type Handler = () => Response;
let handlers: Record<string, Handler> = {};

const ADMIN = {
  id: "admin-1",
  email: "admin@example.com",
  display_name: "Quản trị",
  roles: ["ADMIN"],
  permissions: ["user.manage", "role.assign", "assignment.manage"],
  mfa_enabled: true,
  must_enroll_mfa: false,
  csrf_token: "csrf-me",
};
const USERS = {
  items: [
    {
      id: "u-2",
      email: "nv@example.com",
      display_name: "Nhân viên",
      status: "ACTIVE",
      roles: ["EMPLOYEE"],
      created_at: "2026-10-01T02:00:00Z",
      version: 1,
    },
  ],
  next_cursor: null,
};
const ROLES = [{ code: "EMPLOYEE", base: ["data.read"], eligible: ["finance.read"] }];
const ASSIGNMENTS = {
  items: [
    {
      id: "a-1",
      user_id: "u-2",
      permission: "finance.read",
      scope_type: "COMPANY",
      scope_id: null,
      valid_to: null,
      reason: "Thử",
      revoked_at: null,
    },
  ],
  next_cursor: null,
};

function problem(status: number, code: string): Response {
  return Response.json({ code, correlation_id: "cid-1", status }, { status });
}

beforeEach(() => {
  handlers = {
    "GET /auth/me": () => Response.json(ADMIN),
    "GET /admin/users": () => Response.json(USERS),
    "GET /admin/roles": () => Response.json(ROLES),
    "GET /admin/assignments": () => Response.json(ASSIGNMENTS),
  };
  setCsrfToken(null);
  vitest.stubGlobal(
    "fetch",
    vitest.fn<typeof fetch>(async (input, init = {}) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const path = url.replace(/^\/api\/v1/, "").split("?")[0] ?? "";
      const handler = handlers[`${(init.method ?? "GET").toUpperCase()} ${path}`];
      return Promise.resolve(handler ? handler() : problem(404, "NOT_FOUND"));
    }),
  );
});

afterEach(() => {
  cleanup();
  vitest.unstubAllGlobals();
  window.localStorage.clear();
  document.documentElement.lang = "vi";
});

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} queryClient={createQueryClient()} />);
  return router;
}

async function violations(): Promise<string[]> {
  // jsdom không tính được màu hiển thị → tương phản kiểm riêng trên token (test bên dưới).
  const result = await axe.run(document.body, { rules: { "color-contrast": { enabled: false } } });
  return result.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

describe("i18n vi/en (SRS-NFR-05)", () => {
  it("hai từ điển có cùng tập khóa, kể cả mã lỗi", () => {
    const keys = (value: unknown, prefix = ""): string[] =>
      value && typeof value === "object"
        ? Object.entries(value).flatMap(([k, v]) => keys(v, `${prefix}${k}.`))
        : [prefix];
    expect(keys(en).sort()).toEqual(keys(vi).sort());
  });

  it("mặc định tiếng Việt; đổi sang English → nhãn, <html lang>, lỗi theo ngôn ngữ; nhớ lựa chọn", async () => {
    handlers["GET /auth/me"] = () => problem(401, "UNAUTHENTICATED");
    handlers["POST /auth/login"] = () => problem(401, "INVALID_CREDENTIALS");
    renderAt("/login");
    expect(await screen.findByRole("heading", { name: vi.login.title })).toBeDefined();
    expect(document.documentElement.lang).toBe("vi");
    fireEvent.change(screen.getByLabelText(vi.language.label), { target: { value: "en" } });
    expect(await screen.findByRole("heading", { name: en.login.title })).toBeDefined();
    expect(document.documentElement.lang).toBe("en");
    fireEvent.change(screen.getByLabelText(en.common.email), { target: { value: "a@example.com" } });
    fireEvent.change(screen.getByLabelText(en.common.password), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: en.login.submit }));
    expect(await screen.findByText(en.errors.INVALID_CREDENTIALS!)).toBeDefined();
    expect(screen.getByText(en.common.reference("cid-1"))).toBeDefined();
    cleanup();
    renderAt("/login");
    expect(await screen.findByRole("heading", { name: en.login.title })).toBeDefined();
    expect(window.localStorage.getItem("aieos.lang")).toBe("en"); // chỉ mã ngôn ngữ, không có token
  });

  it("app shell và trang quản trị dịch đủ khi chọn English", async () => {
    window.localStorage.setItem("aieos.lang", "en");
    renderAt("/admin/users");
    expect(await screen.findByRole("heading", { name: en.users.title })).toBeDefined();
    expect(screen.getByRole("navigation", { name: en.nav.label })).toBeDefined();
    expect(screen.getByRole("link", { name: en.nav.assignments })).toBeDefined();
    expect(await screen.findByText(new RegExp(en.users.status.ACTIVE))).toBeDefined();
  });

  it("không còn chuỗi giao diện tiếng Việt viết cứng ngoài từ điển", () => {
    const VIETNAMESE = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;
    expect(Object.keys(SOURCES)).toContain("./pages/LoginPage.tsx");
    const offenders = Object.entries(SOURCES).filter(([, source]) => {
      const code = source
        .replace(/\/\*[\s\S]*?\*\//g, "")
        .replace(/(^|\s)\/\/.*$/gm, "")
        // Thông điệp cho lập trình viên (lỗi nội bộ, console), không hiển thị cho người dùng.
        .replace(/new Error\([^)]*\)|super\([^;]*\);|console\.\w+\([^)]*\)/g, "");
      return VIETNAMESE.test(code);
    });
    expect(offenders.map(([path]) => path)).toEqual([]);
  });
});

describe("truy cập (SRS-NFR-08, WCAG 2.1 AA)", () => {
  it("các màn công khai không có lỗi axe, cả hai ngôn ngữ", async () => {
    handlers["GET /auth/me"] = () => problem(401, "UNAUTHENTICATED");
    for (const lang of ["vi", "en"] as const) {
      window.localStorage.setItem("aieos.lang", lang);
      renderAt("/login");
      await screen.findByRole("heading", { level: 1 });
      expect(await violations()).toEqual([]);
      cleanup();
      window.history.replaceState(null, "", "/invite#token=abc");
      renderAt("/invite");
      await screen.findByRole("heading", { level: 1 });
      expect(await violations()).toEqual([]);
      cleanup();
    }
    setCsrfToken("csrf-1");
    handlers["POST /auth/mfa/enroll"] = () => Response.json({ secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://x" });
    for (const path of ["/mfa/verify", "/mfa/enroll"]) {
      renderAt(path);
      await screen.findByRole("heading", { level: 1 });
      await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
      expect(await violations()).toEqual([]);
      cleanup();
    }
  });

  it("các màn sau đăng nhập không có lỗi axe", async () => {
    for (const [path, ready] of [
      ["/", vi.home.greeting(ADMIN.display_name)],
      ["/admin/users", "nv@example.com"],
      ["/admin/assignments", "Thử"],
      ["/khong-co", vi.notFound.title],
    ] as const) {
      renderAt(path);
      await screen.findByText(new RegExp(ready.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
      expect(await violations()).toEqual([]);
      cleanup();
    }
  });

  it("bàn phím: link bỏ qua tới nội dung chính; hộp thoại xác thực lại nhận focus và đóng bằng Esc", async () => {
    let reauthed = false;
    handlers["PATCH /admin/users/u-2"] = () => (reauthed ? Response.json({}) : problem(401, "REAUTH_REQUIRED"));
    renderAt("/admin/users");
    const skip = await screen.findByRole("link", { name: vi.nav.skip });
    const target = document.getElementById(skip.getAttribute("href")!.slice(1));
    expect(target?.contains(screen.getByRole("heading", { name: vi.users.title }))).toBe(true);
    expect(target?.getAttribute("tabindex")).toBe("-1"); // nhận focus khi theo link, không vào thứ tự Tab
    fireEvent.click(await screen.findByRole("button", { name: vi.users.lock }));
    const dialog = await screen.findByRole("dialog", { name: vi.reauth.title });
    await waitFor(() => expect(document.activeElement).toBe(screen.getByLabelText(vi.common.password)));
    fireEvent.keyDown(dialog, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    reauthed = true;
  });

  it("tương phản chữ/nền của token màu ≥ 4,5:1 (WCAG 1.4.3)", () => {
    const root = CSS.slice(CSS.indexOf(":root {"), CSS.indexOf("}", CSS.indexOf(":root {")));
    const tokens = new Map([...root.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1]!, m[2]!.trim()]));
    const hex = (name: string): string => {
      const value = tokens.get(name) ?? "";
      const ref = /^var\(--([\w-]+)\)$/.exec(value);
      return ref ? hex(ref[1]!) : value;
    };
    const luminance = (color: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => {
        const c = parseInt(color.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
    };
    const ratio = (a: string, b: string) => {
      const [x, y] = [luminance(hex(a)), luminance(hex(b))];
      return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
    };
    const pairs = [
      ["foreground", "background"],
      ["muted-foreground", "background"],
      ["muted-foreground", "muted"],
      ["primary-foreground", "primary"],
      ["secondary-foreground", "secondary"],
      ["accent-foreground", "accent"],
      ["ai-foreground", "ai"],
      ["danger-foreground", "danger"],
      ["danger", "background"],
      ["success", "background"],
      ["warning", "background"],
      ["info", "background"],
      ["stale", "background"],
    ] as const;
    const failing = pairs.filter(([a, b]) => ratio(a, b) < 4.5).map(([a, b]) => `${a}/${b}`);
    expect(failing).toEqual([]);
  });
});
