// FL-01 — Đăng nhập (API-AUTH-01). Lỗi chung, không phân biệt sai email/mật khẩu; khóa tạm chỉ báo sau mật khẩu đúng.
import { useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";
import { apiFetch, setCsrfToken } from "@/api/client";
import type { LoginResult } from "@/api/types";
import { ME_KEY } from "@/auth/session";
import { Card, ErrorNotice, Field } from "@/components/form";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher, useI18n } from "@/i18n";
import { formText } from "@/lib/utils";

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { t } = useI18n();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusy(true);
    setError(null);
    try {
      const result = (await apiFetch("/auth/login", {
        method: "POST",
        json: { email: formText(form, "email"), password: formText(form, "password") },
      })) as LoginResult;
      setCsrfToken(result.csrf_token);
      queryClient.removeQueries({ queryKey: ME_KEY });
      if (result.mfa_required) {
        await navigate(result.mfa_enrolled ? "/mfa/verify" : "/mfa/enroll", { replace: true });
      } else {
        await navigate("/", { replace: true });
      }
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-sm p-4">
      <LanguageSwitcher className="mb-4 flex justify-end" />
      <h1 className="mb-6 text-2xl font-semibold">{t.login.title}</h1>
      <Card>
        <form onSubmit={(e) => void submit(e)} className="space-y-4">
          <Field label={t.common.email} id="email" name="email" type="email" autoComplete="username" required />
          <Field
            label={t.common.password}
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
          />
          <ErrorNotice error={error} />
          <Button type="submit" className="w-full" disabled={busy}>
            {t.login.submit}
          </Button>
        </form>
      </Card>
    </main>
  );
}
