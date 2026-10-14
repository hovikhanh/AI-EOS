import { Link } from "react-router";
import { Button } from "@/components/ui/button";

// Thông điệp chung cho đường dẫn không tồn tại hoặc không có quyền, không lộ sự tồn tại (UX_Flows §0.2, SRS-ACC-02).
export function NotFoundPage() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-semibold">Không tìm thấy hoặc bạn không có quyền</h1>
      <Button asChild variant="link" className="mt-4 px-0">
        <Link to="/">Về Trang chủ</Link>
      </Button>
    </main>
  );
}
