// Hiển thị ngày giờ theo chuẩn Việt Nam mặc định (SRS-GEN-06): 05/10/2026 14:30, múi giờ Việt Nam.
// Ráp từ `formatToParts` để thứ tự ngày trước giờ ổn định giữa các trình duyệt (Intl `vi-VN` có nơi đặt giờ trước).
const PARTS = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: "Asia/Ho_Chi_Minh",
});

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    PARTS.formatToParts(date).find((p) => p.type === type)?.value ?? "";
  return `${part("day")}/${part("month")}/${part("year")} ${part("hour")}:${part("minute")}`;
}
