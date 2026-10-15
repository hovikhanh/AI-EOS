// FL-02 — Chấp nhận lời mời (API-AUTH-08, công khai). Token nằm trong fragment `#token=…` (không gửi tới máy chủ khi
// tải trang); đọc một lần rồi xóa khỏi thanh địa chỉ để không còn trong lịch sử trình duyệt.
import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { apiFetch } from "@/api/client";
import { Card, ErrorNotice, Field } from "@/components/form";
import { Button } from "@/components/ui/button";
import { LanguageSwitcher, useI18n } from "@/i18n";
import { formText } from "@/lib/utils";

function takeToken(): string {
  const token = new URLSearchParams(window.location.hash.slice(1)).get("token") ?? "";
  if (window.location.hash) {
    window.history.replaceState(null, "", window.location.pathname);
  }
  return token;
}

export function InvitePage() {
  const { t } = useI18n();
  const [token] = useState(takeToken);
  const [error, setError] = useState<unknown>(null);
  const [mismatch, setMismatch] = useState(false);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = formText(form, "password");
    setMismatch(password !== formText(form, "confirm"));
    if (password !== formText(form, "confirm")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/auth/invitations/accept", { method: "POST", json: { token, password } });
      setDone(true);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-sm p-4">
      <LanguageSwitcher className="mb-4 flex justify-end" />
      <h1 className="mb-6 text-2xl font-semibold">{t.invite.title}</h1>
      <Card>
        {done ? (
          <div className="space-y-4">
            <p className="text-sm">{t.invite.activated}</p>
            <Button asChild className="w-full">
              <Link to="/login">{t.login.submit}</Link>
            </Button>
          </div>
        ) : !token ? (
          <p className="text-sm">{t.invite.invalid}</p>
        ) : (
          <form onSubmit={(e) => void submit(e)} className="space-y-4">
            <Field
              label={t.invite.newPassword}
              id="password"
              name="password"
              type="password"
              autoComplete="new-password"
              required
            />
            <Field
              label={t.invite.confirmPassword}
              id="confirm"
              name="confirm"
              type="password"
              autoComplete="new-password"
              required
            />
            {mismatch ? (
              <p role="alert" className="text-sm text-danger">
                {t.invite.mismatch}
              </p>
            ) : null}
            <ErrorNotice error={error} />
            <Button type="submit" className="w-full" disabled={busy}>
              {t.invite.submit}
            </Button>
          </form>
        )}
      </Card>
    </main>
  );
}
