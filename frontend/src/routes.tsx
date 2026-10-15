import type { RouteObject } from "react-router";
import { AppLayout, RequirePermission } from "@/pages/AppLayout";
import { HomePage } from "@/pages/HomePage";
import { InvitePage } from "@/pages/InvitePage";
import { LoginPage } from "@/pages/LoginPage";
import { MfaEnrollPage, MfaVerifyPage } from "@/pages/MfaPages";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { AssignmentsPage } from "@/pages/admin/AssignmentsPage";
import { UsersPage } from "@/pages/admin/UsersPage";

// Công khai: đăng nhập, MFA (session chờ MFA), lời mời. Còn lại nằm trong AppLayout (cần session đủ MFA).
export const routes: RouteObject[] = [
  { path: "/login", element: <LoginPage /> },
  { path: "/mfa/verify", element: <MfaVerifyPage /> },
  { path: "/mfa/enroll", element: <MfaEnrollPage /> },
  { path: "/invite", element: <InvitePage /> },
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      {
        path: "admin/users",
        element: (
          <RequirePermission permission="user.manage">
            <UsersPage />
          </RequirePermission>
        ),
      },
      {
        path: "admin/assignments",
        element: (
          <RequirePermission permission="assignment.manage">
            <AssignmentsPage />
          </RequirePermission>
        ),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
