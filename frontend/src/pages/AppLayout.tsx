// App shell (T-111; UX_Flows §0.1, §0.2): yêu cầu session đủ MFA; điều hướng chỉ hiện mục người dùng có quyền
// (SRS-ACC-09 — backend vẫn kiểm tra độc lập). 8 mục nghiệp vụ chính thức chờ D-23: chưa hiển thị.
import { useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Navigate, NavLink, Outlet, useNavigate } from "react-router";
import { apiFetch, isApiError, setCsrfToken } from "@/api/client";
import { ReauthProvider } from "@/auth/reauth";
import { hasPermission, useMe } from "@/auth/session";
import { ErrorNotice, Loading } from "@/components/form";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export const NAV = [
  { to: "/", label: "Trang chủ", permission: null },
  { to: "/admin/users", label: "Người dùng", permission: "user.manage" },
  { to: "/admin/assignments", label: "Quyền được giao", permission: "assignment.manage" },
] as const;

export function AppLayout() {
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  if (me.isPending) {
    return <Loading />;
  }
  if (me.isError) {
    if (isApiError(me.error) && me.error.status === 401) {
      // Chưa đăng nhập, hết phiên hoặc session chờ MFA mà không còn token CSRF (tải lại trang) → đăng nhập lại.
      return <Navigate to="/login" replace />;
    }
    return (
      <main className="p-6">
        <ErrorNotice error={me.error} />
      </main>
    );
  }

  async function logout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      setCsrfToken(null);
      queryClient.clear();
      await navigate("/login", { replace: true });
    }
  }

  const items = NAV.filter((item) => item.permission === null || hasPermission(me.data, item.permission));
  return (
    <ReauthProvider>
      <div className="min-h-screen">
        <header className="flex items-center justify-between border-b border-border px-6 py-3">
          <span className="font-semibold">AI-EOS</span>
          <nav aria-label="Điều hướng chính" className="flex gap-4 text-sm">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => cn("hover:underline", isActive && "font-semibold")}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span>
              {me.data.display_name}
              <span className="ml-1 text-muted-foreground">({me.data.roles.join(", ") || "chưa có role"})</span>
            </span>
            <Button variant="outline" size="sm" onClick={() => void logout()}>
              Đăng xuất
            </Button>
          </div>
        </header>
        <Outlet />
      </div>
    </ReauthProvider>
  );
}

/** Chặn trang theo permission: không có quyền → trang chung "không tìm thấy hoặc không có quyền" (SRS-ACC-02). */
export function RequirePermission({ permission, children }: { permission: string; children: ReactNode }) {
  const me = useMe();
  if (!hasPermission(me.data, permission)) {
    return <Navigate to="/khong-tim-thay" replace />;
  }
  return <>{children}</>;
}
