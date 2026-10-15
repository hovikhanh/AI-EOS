// Quản trị người dùng (T-111; FL-02, FL-03; API-ADM-01…05, API-ADM-09). Thao tác ghi cần step-up (hộp thoại xác
// thực lại) và `If-Match` theo `version`. Không tự sửa chính mình (nút vô hiệu + giải thích — FL-03).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { apiFetch, newIdempotencyKey } from "@/api/client";
import type { CreatedUser, Invitation, Page, RoleInfo, User } from "@/api/types";
import { useStepUp } from "@/auth/reauth";
import { hasPermission, useMe } from "@/auth/session";
import { Card, ErrorNotice, Field, Loading } from "@/components/form";
import { Button } from "@/components/ui/button";
import { formText } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";

const USERS_KEY = ["admin", "users"] as const;
const STATUS_LABEL: Record<User["status"], string> = {
  INVITED: "Chờ kích hoạt",
  ACTIVE: "Hoạt động",
  LOCKED: "Đã khóa",
  DISABLED: "Vô hiệu",
};

export function useRoles() {
  return useQuery({
    queryKey: ["admin", "roles"],
    queryFn: async () => (await apiFetch("/admin/roles")) as RoleInfo[],
  });
}

function inviteUrl(link: string): string {
  return `${window.location.origin}${link}`;
}

function OneTimeLink({ invitation, onClose }: { invitation: Invitation; onClose: () => void }) {
  const url = inviteUrl(invitation.link);
  return (
    <div role="status" className="space-y-2 rounded-md border border-info/40 bg-info/5 p-3 text-sm">
      <p className="font-medium">Link mời — chỉ hiển thị một lần. Hết hạn: {formatDateTime(invitation.expires_at)}</p>
      <p className="break-all font-mono" aria-label="Link mời">
        {url}
      </p>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={() => void navigator.clipboard?.writeText(url)}>
          Sao chép
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Đóng
        </Button>
      </div>
    </div>
  );
}

function CreateUserForm({ roles, onCreated }: { roles: RoleInfo[]; onCreated: (result: CreatedUser) => void }) {
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const [key] = useState(newIdempotencyKey);
  const [selected, setSelected] = useState<string[]>([]);
  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      stepUp(() => apiFetch("/admin/users", { method: "POST", json: body, headers: { "Idempotency-Key": key } })),
    onSuccess: async (result) => {
      onCreated(result as CreatedUser);
      await queryClient.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
  const comboForbidden = selected.includes("ADMIN") && selected.includes("CFO");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    create.mutate({
      email: formText(form, "email"),
      display_name: formText(form, "display_name"),
      roles: selected,
      reason: formText(form, "reason"),
    });
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" aria-label="Tạo tài khoản">
      <Field label="Email" id="new-email" name="email" type="email" required />
      <Field label="Họ tên" id="new-name" name="display_name" required />
      <fieldset className="sm:col-span-2">
        <legend className="mb-1 text-sm font-medium">Role</legend>
        <div className="flex flex-wrap gap-3 text-sm">
          {roles.map((role) => (
            <label key={role.code} className="flex items-center gap-1">
              <input
                type="checkbox"
                checked={selected.includes(role.code)}
                onChange={(e) =>
                  setSelected((prev) => (e.target.checked ? [...prev, role.code] : prev.filter((r) => r !== role.code)))
                }
              />
              {role.code}
            </label>
          ))}
        </div>
        {comboForbidden ? (
          <p role="alert" className="mt-1 text-sm text-danger">
            Không được gán ADMIN và CFO cho cùng một tài khoản.
          </p>
        ) : null}
      </fieldset>
      <div className="sm:col-span-2">
        <Field label="Lý do" id="new-reason" name="reason" required />
      </div>
      <div className="sm:col-span-2">
        <ErrorNotice error={create.error} />
      </div>
      <Button
        type="submit"
        disabled={create.isPending || comboForbidden}
        className="sm:col-span-2 sm:justify-self-start"
      >
        Tạo và cấp lời mời
      </Button>
    </form>
  );
}

function RoleEditor({ user, roles, onDone }: { user: User; roles: RoleInfo[]; onDone: () => void }) {
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>(user.roles);
  const [reason, setReason] = useState("");
  const save = useMutation({
    mutationFn: () =>
      stepUp(() =>
        apiFetch(`/admin/users/${user.id}/roles`, {
          method: "PUT",
          json: { roles: selected, reason },
          headers: { "If-Match": `"${user.version}"` },
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: USERS_KEY });
      onDone();
    },
  });
  const comboForbidden = selected.includes("ADMIN") && selected.includes("CFO");
  return (
    <div className="space-y-2 rounded-md bg-muted p-3 text-sm" aria-label={`Sửa role của ${user.email}`}>
      <div className="flex flex-wrap gap-3">
        {roles.map((role) => (
          <label key={role.code} className="flex items-center gap-1">
            <input
              type="checkbox"
              checked={selected.includes(role.code)}
              onChange={(e) =>
                setSelected((prev) => (e.target.checked ? [...prev, role.code] : prev.filter((r) => r !== role.code)))
              }
            />
            {role.code}
          </label>
        ))}
      </div>
      {comboForbidden ? (
        <p role="alert" className="text-danger">
          Không được gán ADMIN và CFO cho cùng một tài khoản.
        </p>
      ) : null}
      <Field label="Lý do" id={`reason-${user.id}`} value={reason} onChange={(e) => setReason(e.target.value)} />
      <p className="text-muted-foreground">Lưu xong, mọi phiên đăng nhập của người này sẽ bị thu hồi.</p>
      <ErrorNotice error={save.error} />
      <div className="flex gap-2">
        <Button size="sm" disabled={!reason.trim() || comboForbidden || save.isPending} onClick={() => save.mutate()}>
          Lưu role
        </Button>
        <Button size="sm" variant="ghost" onClick={onDone}>
          Hủy
        </Button>
      </div>
    </div>
  );
}

function UserRow({
  user,
  roles,
  self,
  canAssign,
}: {
  user: User;
  roles: RoleInfo[];
  self: boolean;
  canAssign: boolean;
}) {
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [link, setLink] = useState<Invitation | null>(null);
  const action = useMutation({
    mutationFn: (run: () => Promise<unknown>) => stepUp(run),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: USERS_KEY }),
  });
  const setStatus = (status: User["status"]) =>
    action.mutate(() =>
      apiFetch(`/admin/users/${user.id}`, {
        method: "PATCH",
        json: { status },
        headers: { "If-Match": `"${user.version}"` },
      }),
    );
  const reissue = () =>
    action.mutate(async () => {
      setLink((await apiFetch(`/admin/users/${user.id}/invitations`, { method: "POST" })) as Invitation);
    });

  return (
    <li className="space-y-2 border-b border-border py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="font-medium">
            {user.display_name} <span className="text-muted-foreground">· {user.email}</span>
          </p>
          <p className="text-sm text-muted-foreground">
            {STATUS_LABEL[user.status]} · {user.roles.join(", ") || "chưa có role"} · tạo{" "}
            {formatDateTime(user.created_at)}
          </p>
        </div>
        {self ? (
          <p className="text-sm text-muted-foreground">Không thể tự sửa tài khoản của mình.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {user.status === "INVITED" ? (
              <Button size="sm" variant="outline" onClick={reissue}>
                Cấp lại lời mời
              </Button>
            ) : null}
            {user.status === "ACTIVE" ? (
              <Button size="sm" variant="outline" onClick={() => setStatus("LOCKED")}>
                Khóa
              </Button>
            ) : null}
            {user.status === "LOCKED" || user.status === "DISABLED" ? (
              <Button size="sm" variant="outline" onClick={() => setStatus("ACTIVE")}>
                Mở khóa
              </Button>
            ) : null}
            {user.status !== "DISABLED" && user.status !== "INVITED" ? (
              <Button size="sm" variant="destructive" onClick={() => setStatus("DISABLED")}>
                Vô hiệu
              </Button>
            ) : null}
            {canAssign ? (
              <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>
                Sửa role
              </Button>
            ) : null}
          </div>
        )}
      </div>
      <ErrorNotice error={action.error} />
      {link ? <OneTimeLink invitation={link} onClose={() => setLink(null)} /> : null}
      {editing ? <RoleEditor user={user} roles={roles} onDone={() => setEditing(false)} /> : null}
    </li>
  );
}

export function UsersPage() {
  const me = useMe().data;
  const users = useQuery({
    queryKey: USERS_KEY,
    queryFn: async () => (await apiFetch("/admin/users?limit=100")) as Page<User>,
  });
  const roles = useRoles();
  const [created, setCreated] = useState<CreatedUser | null>(null);
  const [formKey, setFormKey] = useState(0);
  const canAssign = hasPermission(me, "role.assign");

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Người dùng</h1>
      <Card title="Tạo tài khoản">
        {created?.invitation ? (
          <OneTimeLink
            invitation={created.invitation}
            onClose={() => {
              setCreated(null);
              setFormKey((n) => n + 1);
            }}
          />
        ) : roles.data ? (
          <CreateUserForm key={formKey} roles={canAssign ? roles.data : []} onCreated={setCreated} />
        ) : (
          <ErrorNotice error={roles.error} />
        )}
      </Card>
      <Card title="Danh sách">
        {users.isPending ? (
          <Loading />
        ) : users.isError ? (
          <ErrorNotice error={users.error} />
        ) : users.data.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Chưa có tài khoản nào.</p>
        ) : (
          <ul aria-label="Danh sách người dùng">
            {users.data.items.map((user) => (
              <UserRow
                key={user.id}
                user={user}
                roles={roles.data ?? []}
                self={user.id === me?.id}
                canAssign={canAssign}
              />
            ))}
          </ul>
        )}
      </Card>
    </main>
  );
}
