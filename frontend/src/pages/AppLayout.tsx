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
import { LanguageSwitcher, useI18n } from "@/i18n";
import type { Messages } from "@/i18n/vi";
import { cn } from "@/lib/utils";

export const NAV = [
  { to: "/", label: "home", permission: null },
  { to: "/admin/users", label: "users", permission: "user.manage" },
  { to: "/admin/assignments", label: "assignments", permission: "assignment.manage" },
] as const satisfies readonly { to: string; label: keyof Messages["nav"]; permission: string | null }[];

const MAIN_ID = "noi-dung-chinh";

export function AppLayout() {
  const me = useMe();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useI18n();

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
        <a
          href={`#${MAIN_ID}`}
          className="sr-only rounded-md bg-background px-3 py-2 text-sm focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:ring-2 focus:ring-ring"
        >
          {t.nav.skip}
        </a>
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-3">
          <span className="font-semibold">{t.common.appName}</span>
          <nav aria-label={t.nav.label} className="flex gap-4 text-sm">
            {items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => cn("hover:underline", isActive && "font-semibold")}
              >
                {t.nav[item.label]}
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span>
              {me.data.display_name}
              <span className="ml-1 text-muted-foreground">({me.data.roles.join(", ") || t.common.noRole})</span>
            </span>
            <LanguageSwitcher />
            <Button variant="outline" size="sm" onClick={() => void logout()}>
              {t.nav.logout}
            </Button>
          </div>
        </header>
        <div id={MAIN_ID} tabIndex={-1} className="focus:outline-none">
          <Outlet />
        </div>
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
