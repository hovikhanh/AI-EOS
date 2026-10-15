// Trang chủ sau đăng nhập (T-111). Nội dung theo role (Briefing, chỉ số) thuộc T-513 và các task nghiệp vụ.
import { useMe } from "@/auth/session";

export function HomePage() {
  const me = useMe().data;
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">AI-EOS</h1>
      <p className="mt-2 text-muted-foreground">
        Xin chào{me ? `, ${me.display_name}` : ""}. Chức năng nghiệp vụ sẽ xuất hiện ở đây khi được triển khai.
      </p>
    </main>
  );
}
