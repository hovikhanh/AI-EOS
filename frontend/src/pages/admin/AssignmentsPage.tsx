// Quyền được giao (T-111; FL-03; API-ADM-06…09). Chỉ chọn được permission mà role của người nhận đủ điều kiện
// (cột "A" Architecture §6, đọc từ `/admin/roles`); backend vẫn kiểm tra (`422 ASSIGNMENT_NOT_ELIGIBLE`).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { apiFetch, newIdempotencyKey } from "@/api/client";
import type { Assignment, Page, User } from "@/api/types";
import { useStepUp } from "@/auth/reauth";
import { useMe } from "@/auth/session";
import { Card, ErrorNotice, Field, Loading } from "@/components/form";
import { Button } from "@/components/ui/button";
import { formText } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";
import { useRoles } from "./UsersPage";

const ASSIGNMENTS_KEY = ["admin", "assignments"] as const;
const SCOPES = ["COMPANY", "ORG_UNIT", "DOCUMENT_TYPE", "REVIEW_QUEUE"] as const;
const SCOPE_LABEL: Record<(typeof SCOPES)[number], string> = {
  COMPANY: "Toàn công ty",
  ORG_UNIT: "Đơn vị",
  DOCUMENT_TYPE: "Loại tài liệu",
  REVIEW_QUEUE: "Hàng chờ review",
};

function CreateAssignmentForm({ users }: { users: User[] }) {
  const me = useMe().data;
  const rolesData = useRoles().data;
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const [userId, setUserId] = useState("");
  const [scope, setScope] = useState<(typeof SCOPES)[number]>("COMPANY");
  const [key, setKey] = useState(newIdempotencyKey);
  const target = users.find((u) => u.id === userId);
  const eligible = useMemo(
    () =>
      [...new Set((rolesData ?? []).filter((r) => target?.roles.includes(r.code)).flatMap((r) => r.eligible))].sort(),
    [rolesData, target],
  );
  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      stepUp(() => apiFetch("/admin/assignments", { method: "POST", json: body, headers: { "Idempotency-Key": key } })),
    onSuccess: async () => {
      setKey(newIdempotencyKey());
      await queryClient.invalidateQueries({ queryKey: ASSIGNMENTS_KEY });
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const validTo = formText(form, "valid_to");
    create.mutate({
      user_id: userId,
      permission: formText(form, "permission"),
      scope_type: scope,
      scope_id: scope === "COMPANY" ? null : formText(form, "scope_id"),
      valid_to: validTo ? new Date(validTo).toISOString() : null,
      reason: formText(form, "reason"),
    });
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2" aria-label="Giao quyền">
      <label className="block text-sm">
        <span className="mb-1 block font-medium">Người nhận</span>
        <select
          className="h-9 w-full rounded-md border border-input bg-background px-2"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          required
        >
          <option value="">— Chọn —</option>
          {users
            .filter((u) => u.id !== me?.id && u.status !== "DISABLED")
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.display_name} ({u.roles.join(", ") || "chưa có role"})
              </option>
            ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="mb-1 block font-medium">Permission</span>
        <select name="permission" className="h-9 w-full rounded-md border border-input bg-background px-2" required>
          <option value="">
            {target
              ? eligible.length
                ? "— Chọn —"
                : "Role của người này không đủ điều kiện"
              : "Chọn người nhận trước"}
          </option>
          {eligible.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        <span className="mb-1 block font-medium">Phạm vi</span>
        <select
          className="h-9 w-full rounded-md border border-input bg-background px-2"
          value={scope}
          onChange={(e) => setScope(e.target.value as (typeof SCOPES)[number])}
        >
          {SCOPES.map((s) => (
            <option key={s} value={s}>
              {SCOPE_LABEL[s]}
            </option>
          ))}
        </select>
      </label>
      {scope !== "COMPANY" ? <Field label="Mã phạm vi" id="scope-id" name="scope_id" required /> : <div />}
      <Field label="Hiệu lực đến (tùy chọn)" id="valid-to" name="valid_to" type="datetime-local" />
      <Field label="Lý do" id="assign-reason" name="reason" required />
      <p className="text-sm text-muted-foreground sm:col-span-2">
        Lưu xong, mọi phiên đăng nhập của người nhận sẽ bị thu hồi.
      </p>
      <div className="sm:col-span-2">
        <ErrorNotice error={create.error} />
      </div>
      <Button type="submit" disabled={create.isPending || !target} className="sm:justify-self-start">
        Giao quyền
      </Button>
    </form>
  );
}

export function AssignmentsPage() {
  const stepUp = useStepUp();
  const queryClient = useQueryClient();
  const users = useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => (await apiFetch("/admin/users?limit=100")) as Page<User>,
  });
  const assignments = useQuery({
    queryKey: ASSIGNMENTS_KEY,
    queryFn: async () => (await apiFetch("/admin/assignments?limit=100")) as Page<Assignment>,
  });
  const revoke = useMutation({
    mutationFn: (id: string) => stepUp(() => apiFetch(`/admin/assignments/${id}`, { method: "DELETE" })),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ASSIGNMENTS_KEY }),
  });
  const names = new Map((users.data?.items ?? []).map((u) => [u.id, u.display_name]));

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <h1 className="text-2xl font-semibold">Quyền được giao</h1>
      <Card title="Giao quyền">{users.data ? <CreateAssignmentForm users={users.data.items} /> : <Loading />}</Card>
      <Card title="Danh sách">
        <ErrorNotice error={revoke.error} />
        {assignments.isPending ? (
          <Loading />
        ) : assignments.isError ? (
          <ErrorNotice error={assignments.error} />
        ) : assignments.data.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">Chưa có quyền nào được giao.</p>
        ) : (
          <ul aria-label="Danh sách quyền được giao">
            {assignments.data.items.map((a) => (
              <li
                key={a.id}
                className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-3 text-sm"
              >
                <div>
                  <p className="font-medium">
                    {names.get(a.user_id) ?? a.user_id} · {a.permission}
                  </p>
                  <p className="text-muted-foreground">
                    {SCOPE_LABEL[a.scope_type]}
                    {a.scope_id ? ` ${a.scope_id}` : ""} · đến {a.valid_to ? formatDateTime(a.valid_to) : "không hạn"} ·{" "}
                    {a.reason}
                    {a.revoked_at ? ` · đã thu hồi ${formatDateTime(a.revoked_at)}` : ""}
                  </p>
                </div>
                {a.revoked_at ? null : (
                  <Button size="sm" variant="outline" onClick={() => revoke.mutate(a.id)}>
                    Thu hồi
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </main>
  );
}
