// Trang chủ sau đăng nhập (T-111). Nội dung theo role (Briefing, chỉ số) thuộc T-513 và các task nghiệp vụ.
import { useMe } from "@/auth/session";
import { useI18n } from "@/i18n";

export function HomePage() {
  const me = useMe().data;
  const { t } = useI18n();
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">{t.common.appName}</h1>
      <p className="mt-2 text-muted-foreground">{t.home.greeting(me ? me.display_name : null)}</p>
    </main>
  );
}
