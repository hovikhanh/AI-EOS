// T-012 — Implementation_Plan §12, test dự kiến 1: router hiển thị route gốc và route không tồn tại.
import { cleanup, render, screen } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { createQueryClient } from "./api/queryClient";
import { App } from "./App";
import { routes } from "./routes";

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<App router={router} queryClient={createQueryClient()} />);
  return router;
}

afterEach(cleanup);

describe("routes", () => {
  it("hiển thị trang gốc", () => {
    renderAt("/");
    expect(screen.getByRole("heading", { level: 1, name: "AI-EOS" })).toBeDefined();
  });

  it("đường dẫn không tồn tại hiển thị thông điệp chung và liên kết về Trang chủ", () => {
    renderAt("/khong-ton-tai/123");
    expect(screen.getByRole("heading", { level: 1, name: "Không tìm thấy hoặc bạn không có quyền" })).toBeDefined();
    expect(screen.getByRole("link", { name: "Về Trang chủ" }).getAttribute("href")).toBe("/");
  });
});
