// Xác thực lại cho thao tác `STEP-UP` (T-111, SRS-IAM-08, API-AUTH-05): API trả `401 REAUTH_REQUIRED` → hộp thoại
// nhập mật khẩu (+ mã MFA nếu đã bật) → gọi `/auth/reauth` → thử lại thao tác một lần. Mật khẩu/mã không lưu lại.
import { createContext, useCallback, useContext, useRef, useState, type FormEvent, type ReactNode } from "react";
import { apiFetch, isApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { formText } from "@/lib/utils";
import { ErrorNotice, Field } from "@/components/form";
import { useMe } from "./session";

type StepUp = <T>(action: () => Promise<T>) => Promise<T>;

const StepUpContext = createContext<StepUp | null>(null);

export function useStepUp(): StepUp {
  const value = useContext(StepUpContext);
  if (!value) {
    throw new Error("useStepUp phải nằm trong ReauthProvider");
  }
  return value;
}

export function ReauthProvider({ children }: { children: ReactNode }) {
  const me = useMe().data;
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const waiter = useRef<{ resolve: () => void; reject: (reason: unknown) => void } | null>(null);

  const stepUp: StepUp = useCallback(async (action) => {
    try {
      return await action();
    } catch (failure) {
      if (!isApiError(failure, "REAUTH_REQUIRED")) {
        throw failure;
      }
      await new Promise<void>((resolve, reject) => {
        waiter.current = { resolve, reject };
        setError(null);
        setOpen(true);
      });
      return action();
    }
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const code = formText(form, "code").trim();
    setBusy(true);
    try {
      await apiFetch("/auth/reauth", {
        method: "POST",
        json: { password: formText(form, "password"), ...(code ? { code } : {}) },
      });
      setOpen(false);
      waiter.current?.resolve();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  function cancel() {
    setOpen(false);
    waiter.current?.reject(new Error("Đã hủy xác thực lại"));
  }

  return (
    <StepUpContext.Provider value={stepUp}>
      {children}
      {open ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="reauth-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40 p-4"
        >
          <form
            onSubmit={(e) => void submit(e)}
            className="w-full max-w-sm space-y-4 rounded-lg bg-background p-6 shadow-lg"
          >
            <h2 id="reauth-title" className="text-lg font-semibold">
              Xác thực lại
            </h2>
            <p className="text-sm text-muted-foreground">Thao tác này cần xác nhận lại danh tính.</p>
            <Field
              label="Mật khẩu"
              id="reauth-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
            {me?.mfa_enabled ? (
              <Field
                label="Mã MFA hoặc mã khôi phục"
                id="reauth-code"
                name="code"
                autoComplete="one-time-code"
                required
              />
            ) : null}
            <ErrorNotice error={error} />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" onClick={cancel}>
                Hủy
              </Button>
              <Button type="submit" disabled={busy}>
                Xác nhận
              </Button>
            </div>
          </form>
        </div>
      ) : null}
    </StepUpContext.Provider>
  );
}
