import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Ghép class Tailwind, lớp sau ghi đè lớp trước (quy ước shadcn/ui). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Giá trị văn bản của trường biểu mẫu (file/không có → chuỗi rỗng). */
export function formText(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}
