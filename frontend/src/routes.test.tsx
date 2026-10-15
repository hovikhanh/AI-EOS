// T-012 — Implementation_Plan §12, test dự kiến 1: router hiển thị route gốc và route không tồn tại.
// T-111: trang gốc và route lạ nằm trong app shell (cần session) → giả lập `GET /auth/me` thành công.
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createQueryClient } from "./api/queryClient";
import { App } from "./App";
import { routes } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} queryClient={createQueryClient()} />);
  return router;
}

const ME = {
  id: "u1",
  email: "an@example.com",
  display_name: "An",
  roles: ["EMPLOYEE"],
  permissions: ["data.read"],
  mfa_enabled: false,
  must_enroll_mfa: false,
  csrf_token: "csrf",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>(() => Promise.resolve(Response.json(ME))),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("routes", () => {
  it("hiển thị trang gốc", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { level: 1, name: "AI-EOS" })).toBeDefined();
  });

  it("đường dẫn không tồn tại hiển thị thông điệp chung và liên kết về Trang chủ", async () => {
    renderAt("/khong-ton-tai/123");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Không tìm thấy hoặc bạn không có quyền" }),
    ).toBeDefined();
    expect(screen.getByRole("link", { name: "Về Trang chủ" }).getAttribute("href")).toBe("/");
  });
});
