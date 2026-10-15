// FL-01 — MFA (API-AUTH-02, 03, 04; SRS-IAM-05). Session chờ MFA chỉ gọi được API MFA và đăng xuất.
// Secret và mã khôi phục chỉ hiển thị trên màn hình, không lưu xuống storage. Chưa có mã QR (cần thư viện — để sau):
// người dùng nhập secret thủ công hoặc mở liên kết `otpauth://` trên thiết bị có ứng dụng xác thực.
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { apiFetch, hasCsrfToken } from "@/api/client";
import { ME_KEY, fetchMe } from "@/auth/session";
import { Card, ErrorNotice, Field, Loading } from "@/components/form";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";
import { formText } from "@/lib/utils";

type Enrollment = { secret: string; otpauth_uri: string };

function useFinish() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  return async () => {
    // Session đã xoay: lấy token CSRF mới qua /auth/me.
    queryClient.setQueryData(ME_KEY, await fetchMe());
    await navigate("/", { replace: true });
  };
}

export function MfaVerifyPage() {
  const finish = useFinish();
  const { t } = useI18n();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  if (!hasCsrfToken()) {
    return <Navigate to="/login" replace />;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = formText(new FormData(event.currentTarget), "code").trim();
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/auth/mfa/verify", { method: "POST", json: { code } });
      await finish();
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto mt-16 max-w-sm p-4">
      <h1 className="mb-6 text-2xl font-semibold">{t.mfa.verifyTitle}</h1>
      <Card>
        <form onSubmit={(e) => void submit(e)} className="space-y-4">
          <Field label={t.mfa.codeOrRecovery} id="code" name="code" autoComplete="one-time-code" required />
          <ErrorNotice error={error} />
          <Button type="submit" className="w-full" disabled={busy}>
            {t.mfa.verify}
          </Button>
        </form>
      </Card>
    </main>
  );
}

export function MfaEnrollPage() {
  const finish = useFinish();
  const { t } = useI18n();
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const allowed = hasCsrfToken();

  useEffect(() => {
    if (!allowed) {
      return;
    }
    let active = true;
    apiFetch("/auth/mfa/enroll", { method: "POST" })
      .then((result) => {
        if (active) {
          setEnrollment(result as Enrollment);
        }
      })
      .catch((failure: unknown) => {
        if (active) {
          setError(failure);
        }
      });
    return () => {
      active = false;
    };
  }, [allowed]);

  if (!allowed) {
    return <Navigate to="/login" replace />;
  }

  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = formText(new FormData(event.currentTarget), "code").trim();
    setBusy(true);
    setError(null);
    try {
      const result = (await apiFetch("/auth/mfa/enroll/confirm", { method: "POST", json: { code } })) as {
        recovery_codes: string[];
      };
      setCodes(result.recovery_codes);
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }

  if (codes) {
    return (
      <main className="mx-auto mt-16 max-w-md p-4">
        <h1 className="mb-6 text-2xl font-semibold">{t.mfa.recoveryTitle}</h1>
        <Card>
          <p className="mb-3 text-sm">
            {t.mfa.recoveryIntroBefore}
            <strong>{t.mfa.recoveryOnce}</strong>
            {t.mfa.recoveryIntroAfter}
          </p>
          <ul aria-label={t.mfa.recoveryCodes} className="mb-4 grid grid-cols-2 gap-2 font-mono text-sm">
            {codes.map((code) => (
              <li key={code} className="rounded bg-muted px-2 py-1">
                {code}
              </li>
            ))}
          </ul>
          <Button className="w-full" onClick={() => void finish()}>
            {t.mfa.recoverySaved}
          </Button>
        </Card>
      </main>
    );
  }

  return (
    <main className="mx-auto mt-16 max-w-md p-4">
      <h1 className="mb-6 text-2xl font-semibold">{t.mfa.enrollTitle}</h1>
      <Card>
        {enrollment ? (
          <form onSubmit={(e) => void confirm(e)} className="space-y-4">
            <p className="text-sm">{t.mfa.enrollIntro}</p>
            <p className="break-all rounded bg-muted p-2 font-mono text-sm" aria-label={t.mfa.secret}>
              {enrollment.secret}
            </p>
            <a className="text-sm text-primary underline" href={enrollment.otpauth_uri}>
              {t.mfa.openApp}
            </a>
            <Field
              label={t.mfa.sixDigits}
              id="code"
              name="code"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
            />
            <ErrorNotice error={error} />
            <Button type="submit" className="w-full" disabled={busy}>
              {t.common.confirm}
            </Button>
          </form>
        ) : error ? (
          <ErrorNotice error={error} />
        ) : (
          <Loading />
        )}
      </Card>
    </main>
  );
}
