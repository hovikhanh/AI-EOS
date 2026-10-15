// Kiểu dữ liệu API (API_Specification §2, §3). Dữ liệu từ server là không tin cậy: chỉ render dạng văn bản.

export type Me = {
  id: string;
  email: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  mfa_enabled: boolean;
  must_enroll_mfa: boolean;
  csrf_token: string;
};

export type LoginResult = { mfa_required: boolean; mfa_enrolled: boolean; csrf_token: string };

export type User = {
  id: string;
  email: string;
  display_name: string;
  status: "INVITED" | "ACTIVE" | "LOCKED" | "DISABLED";
  roles: string[];
  mfa_enabled: boolean;
  created_at: string;
  version: number;
};

export type Page<T> = { items: T[]; next_cursor: string | null };

export type Invitation = { link: string; expires_at: string };

export type CreatedUser = { user: User; invitation: Invitation | null };

export type RoleInfo = { code: string; base: string[]; eligible: string[] };

export type Assignment = {
  id: string;
  user_id: string;
  permission: string;
  scope_type: "COMPANY" | "ORG_UNIT" | "DOCUMENT_TYPE" | "REVIEW_QUEUE";
  scope_id: string | null;
  valid_from: string;
  valid_to: string | null;
  granted_by: string;
  reason: string;
  created_at: string;
  revoked_at: string | null;
  revoked_by: string | null;
};
