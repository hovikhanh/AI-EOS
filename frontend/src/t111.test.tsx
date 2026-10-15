// T-111 — app shell, đăng nhập, MFA, lời mời, quản trị, ẩn mục không có quyền, trạng thái chung (UX_Flows §0, FL-01…03).
// Bằng chứng thành phần TC-E2E-01 (chủ T-608): luồng E2E thật chạy ở T-608 trên stack Compose (T-013).
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiFetch, setCsrfToken } from "./api/client";
import { createQueryClient } from "./api/queryClient";
import { App } from "./App";
import { formatDateTime } from "./lib/format";
import { routes } from "./routes";

type Handler = (init: RequestInit, url: string) => Response | Promise<Response>;
const calls: { method: string; url: string; headers: Headers; body: unknown }[] = [];
let handlers: Record<string, Handler> = {};

const ADMIN = {
  id: "admin-1",
  email: "admin@example.com",
  display_name: "Quản trị",
  roles: ["ADMIN"],
  permissions: ["user.manage", "role.assign", "assignment.manage", "audit.read.admin"],
  mfa_enabled: true,
  must_enroll_mfa: false,
  csrf_token: "csrf-me",
};
const EMPLOYEE = { ...ADMIN, id: "nv-1", display_name: "Nhân viên", roles: ["EMPLOYEE"], permissions: ["data.read"] };

function problem(status: number, code: string, correlation = "cid-123"): Response {
  return Response.json({ code, correlation_id: correlation, status }, { status });
}

beforeEach(() => {
  calls.length = 0;
  handlers = {};
  setCsrfToken(null);
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(async (input, init = {}) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      const method = (init.method ?? "GET").toUpperCase();
      const body: unknown = typeof init.body === "string" ? JSON.parse(init.body) : undefined;
      calls.push({ method, url, headers: new Headers(init.headers), body });
      const path = url.replace(/^\/api\/v1/, "").split("?")[0] ?? "";
      const handler = handlers[`${method} ${path}`];
      return handler ? handler(init, url) : problem(404, "NOT_FOUND");
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} queryClient={createQueryClient()} />);
  return router;
}

function call(method: string, path: string) {
  return calls.filter((c) => c.method === method && c.url.startsWith(`/api/v1${path}`));
}

describe("API client", () => {
  it("gửi token CSRF (chỉ trong bộ nhớ) cho request ghi, không gửi cho GET; đọc problem+json", async () => {
    handlers["POST /x"] = () => problem(409, "INVALID_STATE", "cid-9");
    handlers["GET /y"] = () => Response.json({});
    setCsrfToken("tok");
    await expect(apiFetch("/x", { method: "POST", json: { a: 1 } })).rejects.toMatchObject({
      status: 409,
      code: "INVALID_STATE",
      correlationId: "cid-9",
    });
    await apiFetch("/y");
    expect(calls[0]?.headers.get("X-CSRF-Token")).toBe("tok");
    expect(calls[0]?.headers.get("Content-Type")).toBe("application/json");
    expect(calls[1]?.headers.get("X-CSRF-Token")).toBeNull();
  });

  it("định dạng ngày giờ kiểu Việt Nam (SRS-GEN-06)", () => {
    expect(formatDateTime("2026-10-05T07:30:00Z")).toBe("05/10/2026 14:30");
    expect(formatDateTime(null)).toBe("—");
  });
});

describe("đăng nhập và MFA (FL-01)", () => {
  it("chưa đăng nhập → trang đăng nhập; đăng nhập không cần MFA → trang chủ", async () => {
    let loggedIn = false;
    handlers["GET /auth/me"] = () => (loggedIn ? Response.json(EMPLOYEE) : problem(401, "UNAUTHENTICATED"));
    handlers["POST /auth/login"] = () => {
      loggedIn = true;
      return Response.json({ mfa_required: false, mfa_enrolled: false, csrf_token: "csrf-login" });
    };
    const router = renderAt("/");
    fireEvent.change(await screen.findByLabelText("Email"), { target: { value: "nv@example.com" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "mat-khau" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(await screen.findByText(/Xin chào, Nhân viên/)).toBeDefined();
    expect(router.state.location.pathname).toBe("/");
    expect(call("POST", "/auth/login")[0]?.body).toEqual({ email: "nv@example.com", password: "mat-khau" });
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("sai thông tin → thông báo chung, có mã tham chiếu", async () => {
    handlers["POST /auth/login"] = () => problem(401, "INVALID_CREDENTIALS", "cid-login");
    renderAt("/login");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "a@example.com" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(await screen.findByText("Email, mật khẩu hoặc mã không đúng.")).toBeDefined();
    expect(screen.getByText("Mã tham chiếu: cid-login")).toBeDefined();
  });

  it("ADMIN đã đăng ký MFA → nhập mã → trang chủ, dùng token CSRF từ response đăng nhập", async () => {
    let verified = false;
    handlers["POST /auth/login"] = () =>
      Response.json({ mfa_required: true, mfa_enrolled: true, csrf_token: "csrf-1" });
    handlers["POST /auth/mfa/verify"] = () => {
      verified = true;
      return new Response(null, { status: 204 });
    };
    handlers["GET /auth/me"] = () => (verified ? Response.json(ADMIN) : problem(401, "MFA_REQUIRED"));
    const router = renderAt("/login");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@example.com" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    fireEvent.change(await screen.findByLabelText(/Mã từ ứng dụng xác thực/), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Xác minh" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/"));
    expect(call("POST", "/auth/mfa/verify")[0]?.headers.get("X-CSRF-Token")).toBe("csrf-1");
    expect(await screen.findByRole("link", { name: "Người dùng" })).toBeDefined();
  });

  it("ADMIN chưa đăng ký MFA → đăng ký, hiển thị mã khôi phục một lần", async () => {
    handlers["POST /auth/login"] = () =>
      Response.json({ mfa_required: true, mfa_enrolled: false, csrf_token: "csrf-1" });
    handlers["POST /auth/mfa/enroll"] = () =>
      Response.json({ secret: "JBSWY3DPEHPK3PXP", otpauth_uri: "otpauth://totp/AI-EOS:admin@example.com?secret=X" });
    handlers["POST /auth/mfa/enroll/confirm"] = () => Response.json({ recovery_codes: ["AAAAA-BBBBB", "CCCCC-DDDDD"] });
    handlers["GET /auth/me"] = () => Response.json(ADMIN);
    renderAt("/login");
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "admin@example.com" } });
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect((await screen.findByLabelText("Khóa bí mật")).textContent).toBe("JBSWY3DPEHPK3PXP");
    fireEvent.change(screen.getByLabelText("Mã 6 số"), { target: { value: "123456" } });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận" }));
    expect(await screen.findByText("AAAAA-BBBBB")).toBeDefined();
    expect(window.localStorage.length + window.sessionStorage.length).toBe(0);
  });

  it("vào trang MFA khi không có token CSRF trong bộ nhớ (tải lại trang) → về đăng nhập", async () => {
    const router = renderAt("/mfa/verify");
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
  });
});

describe("ẩn mục không có quyền (SRS-ACC-09) và trạng thái chung", () => {
  it("EMPLOYEE không thấy mục quản trị; truy cập trực tiếp → trang chung không lộ tồn tại", async () => {
    handlers["GET /auth/me"] = () => Response.json(EMPLOYEE);
    const router = renderAt("/admin/users");
    expect(await screen.findByRole("heading", { name: "Không tìm thấy hoặc bạn không có quyền" })).toBeDefined();
    expect(screen.queryByRole("link", { name: "Người dùng" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Quyền được giao" })).toBeNull();
    expect(router.state.location.pathname).not.toBe("/admin/users");
    expect(call("GET", "/admin/users")).toHaveLength(0);
  });

  it("lỗi máy chủ khi tải phiên → thông báo + mã tham chiếu", async () => {
    handlers["GET /auth/me"] = () => problem(500, "INTERNAL_ERROR", "cid-500");
    renderAt("/");
    expect(await screen.findByText("Mã tham chiếu: cid-500", undefined, { timeout: 4000 })).toBeDefined();
  });
});

describe("chấp nhận lời mời (FL-02)", () => {
  it("đọc token từ fragment rồi xóa khỏi địa chỉ; mật khẩu không khớp → báo tại chỗ; thành công → đăng nhập", async () => {
    window.history.replaceState(null, "", "/invite#token=tok-123");
    handlers["POST /auth/invitations/accept"] = () => new Response(null, { status: 204 });
    renderAt("/invite");
    expect(window.location.hash).toBe("");
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), { target: { value: "Mat-khau-dai-123" } });
    fireEvent.change(screen.getByLabelText("Nhập lại mật khẩu"), { target: { value: "khac" } });
    fireEvent.click(screen.getByRole("button", { name: "Kích hoạt" }));
    expect(await screen.findByText("Hai lần nhập mật khẩu không khớp.")).toBeDefined();
    expect(call("POST", "/auth/invitations/accept")).toHaveLength(0);
    fireEvent.change(screen.getByLabelText("Nhập lại mật khẩu"), { target: { value: "Mat-khau-dai-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Kích hoạt" }));
    expect(await screen.findByRole("link", { name: "Đăng nhập" })).toBeDefined();
    expect(call("POST", "/auth/invitations/accept")[0]?.body).toEqual({
      token: "tok-123",
      password: "Mat-khau-dai-123",
    });
  });

  it("lời mời không còn hiệu lực → một thông báo chung", async () => {
    window.history.replaceState(null, "", "/invite#token=cu");
    handlers["POST /auth/invitations/accept"] = () => problem(400, "INVITATION_INVALID");
    renderAt("/invite");
    fireEvent.change(screen.getByLabelText("Mật khẩu mới"), { target: { value: "Mat-khau-dai-123" } });
    fireEvent.change(screen.getByLabelText("Nhập lại mật khẩu"), { target: { value: "Mat-khau-dai-123" } });
    fireEvent.click(screen.getByRole("button", { name: "Kích hoạt" }));
    expect(await screen.findByText("Lời mời không còn hiệu lực. Vui lòng liên hệ quản trị.")).toBeDefined();
  });
});

describe("quản trị người dùng (FL-02, FL-03)", () => {
  const USERS = {
    items: [
      {
        id: "admin-1",
        email: "admin@example.com",
        display_name: "Quản trị",
        status: "ACTIVE",
        roles: ["ADMIN"],
        mfa_enabled: true,
        created_at: "2026-10-15T01:00:00Z",
        version: 1,
      },
      {
        id: "u2",
        email: "nv@example.com",
        display_name: "Nhân viên",
        status: "ACTIVE",
        roles: ["EMPLOYEE"],
        mfa_enabled: false,
        created_at: "2026-10-15T02:00:00Z",
        version: 3,
      },
    ],
    next_cursor: null,
  };
  const ROLES = [
    { code: "ADMIN", base: ["user.manage"], eligible: [] },
    { code: "CFO", base: [], eligible: ["finance.approve"] },
    { code: "EMPLOYEE", base: ["data.read"], eligible: ["extraction.review"] },
  ];

  beforeEach(() => {
    handlers["GET /auth/me"] = () => Response.json(ADMIN);
    handlers["GET /admin/users"] = () => Response.json(USERS);
    handlers["GET /admin/roles"] = () => Response.json(ROLES);
  });

  it("tạo tài khoản: step-up khi cần, gửi Idempotency-Key, hiển thị link mời một lần", async () => {
    let reauthed = false;
    handlers["POST /admin/users"] = () =>
      reauthed
        ? Response.json(
            {
              user: { ...USERS.items[1], id: "u3", status: "INVITED" },
              invitation: { link: "/invite#token=abc", expires_at: "2026-10-18T02:00:00Z" },
            },
            { status: 201 },
          )
        : problem(401, "REAUTH_REQUIRED");
    handlers["POST /auth/reauth"] = () => {
      reauthed = true;
      return new Response(null, { status: 204 });
    };
    renderAt("/admin/users");
    const form = await screen.findByRole("form", { name: "Tạo tài khoản" });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "moi@example.com" } });
    fireEvent.change(screen.getByLabelText("Họ tên"), { target: { value: "Người mới" } });
    fireEvent.click(screen.getByLabelText("EMPLOYEE"));
    fireEvent.change(screen.getAllByLabelText("Lý do")[0]!, { target: { value: "Tuyển mới" } });
    fireEvent.submit(form);
    const dialog = await screen.findByRole("dialog", { name: "Xác thực lại" });
    expect(dialog).toBeDefined();
    fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "x" } });
    fireEvent.change(screen.getByLabelText("Mã MFA hoặc mã khôi phục"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Xác nhận" }));
    expect((await screen.findByLabelText("Link mời")).textContent).toBe(`${window.location.origin}/invite#token=abc`);
    const posts = call("POST", "/admin/users");
    expect(posts).toHaveLength(2);
    const key = posts[0]?.headers.get("Idempotency-Key");
    expect(key).toBeTruthy();
    expect(posts[1]?.headers.get("Idempotency-Key")).toBe(key); // thử lại sau reauth dùng cùng khóa
    expect(posts[0]?.body).toEqual({
      email: "moi@example.com",
      display_name: "Người mới",
      roles: ["EMPLOYEE"],
      reason: "Tuyển mới",
    });
    expect(call("POST", "/auth/reauth")[0]?.body).toEqual({ password: "x", code: "654321" });
  });

  it("chặn chọn ADMIN + CFO; không có nút sửa cho chính mình; đổi role gửi If-Match", async () => {
    handlers["PUT /admin/users/u2/roles"] = () => Response.json({ ...USERS.items[1], roles: ["CFO"], version: 4 });
    renderAt("/admin/users");
    const list = await screen.findByRole("list", { name: "Danh sách người dùng" });
    expect(list.textContent).toContain("Không thể tự sửa tài khoản của mình.");
    expect(screen.getAllByRole("button", { name: "Sửa role" })).toHaveLength(1);
    fireEvent.click(screen.getByLabelText("ADMIN", { selector: "form input" }));
    fireEvent.click(screen.getByLabelText("CFO", { selector: "form input" }));
    expect(screen.getByText("Không được gán ADMIN và CFO cho cùng một tài khoản.")).toBeDefined();
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Tạo và cấp lời mời" }).disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Sửa role" }));
    const editor = await screen.findByLabelText("Sửa role của nv@example.com");
    fireEvent.click(screen.getAllByLabelText("EMPLOYEE").at(-1)!);
    fireEvent.click(screen.getAllByLabelText("CFO").at(-1)!);
    fireEvent.change(screen.getByLabelText("Lý do", { selector: "#reason-u2" }), { target: { value: "Điều chuyển" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu role" }));
    await waitFor(() => expect(call("PUT", "/admin/users/u2/roles")).toHaveLength(1));
    const put = call("PUT", "/admin/users/u2/roles")[0];
    expect(put?.headers.get("If-Match")).toBe('"3"');
    expect(put?.body).toEqual({ roles: ["CFO"], reason: "Điều chuyển" });
    expect(editor).toBeDefined();
  });

  it("xung đột version → thông báo tải lại", async () => {
    handlers["PATCH /admin/users/u2"] = () => problem(412, "VERSION_CONFLICT", "cid-v");
    renderAt("/admin/users");
    fireEvent.click(await screen.findByRole("button", { name: "Khóa" }));
    expect(await screen.findByText("Dữ liệu đã thay đổi bởi người khác. Tải lại rồi thao tác lại.")).toBeDefined();
    expect(call("PATCH", "/admin/users/u2")[0]?.body).toEqual({ status: "LOCKED" });
  });
});

describe("ApiError", () => {
  it("giữ mã HTTP, mã lỗi, correlation id", () => {
    const error = new ApiError(422, "VALIDATION_ERROR", "cid", [{ field: "email", message: "Sai" }]);
    expect([error.status, error.code, error.correlationId, error.errors.length]).toEqual([
      422,
      "VALIDATION_ERROR",
      "cid",
      1,
    ]);
  });
});
