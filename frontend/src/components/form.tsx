// Thành phần biểu mẫu và thông báo dùng chung (T-111, UX_Flows §0.2). Nội dung từ server render dạng văn bản.
import type { ComponentProps, ReactNode } from "react";
import { ApiError } from "@/api/client";
import { errorMessage } from "@/lib/messages";
import { cn } from "@/lib/utils";

export function Field({ label, id, ...props }: ComponentProps<"input"> & { label: string; id: string }) {
  return (
    <label htmlFor={id} className="block text-sm">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        id={id}
        className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        {...props}
      />
    </label>
  );
}

/** Lỗi tạm thời: thông báo ngắn + mã tham chiếu `correlation_id` (UX_Flows §0.2). */
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) {
    return null;
  }
  const reference = error instanceof ApiError ? error.correlationId : null;
  return (
    <div role="alert" className="rounded-md border border-danger/40 bg-danger/5 p-3 text-sm text-danger">
      <p>{errorMessage(error)}</p>
      {reference ? <p className="mt-1 text-xs text-muted-foreground">Mã tham chiếu: {reference}</p> : null}
    </div>
  );
}

export function Card({ title, children, className }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border border-border bg-background p-6", className)}>
      {title ? <h2 className="mb-4 text-lg font-semibold">{title}</h2> : null}
      {children}
    </section>
  );
}

export function Loading({ label = "Đang tải…" }: { label?: string }) {
  return (
    <p role="status" className="p-6 text-sm text-muted-foreground">
      {label}
    </p>
  );
}
