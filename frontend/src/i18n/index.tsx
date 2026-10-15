// i18n vi/en (T-607, SRS-NFR-05, ADR-003): tiếng Việt mặc định; lựa chọn của người dùng nhớ trong `localStorage`
// (chỉ mã ngôn ngữ — không phải token, ADR-003). `<html lang>` theo ngôn ngữ đang dùng để trình đọc màn hình đọc đúng.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { en } from "./en";
import { vi, type Messages } from "./vi";

export type Lang = "vi" | "en";
export const LANGS: readonly Lang[] = ["vi", "en"];
export const DICTIONARIES: Record<Lang, Messages> = { vi, en };
const STORAGE_KEY = "aieos.lang";

type I18n = { lang: Lang; t: Messages; setLang: (lang: Lang) => void };

// Ngoài provider (test thành phần lẻ): tiếng Việt, không đổi được.
const I18nContext = createContext<I18n>({ lang: "vi", t: vi, setLang: () => undefined });

function storedLang(): Lang {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "en" || value === "vi" ? value : "vi";
  } catch {
    return "vi";
  }
}

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => initial ?? storedLang());
  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Trình duyệt chặn storage: vẫn đổi ngôn ngữ trong phiên hiện tại.
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const value = useMemo(() => ({ lang, t: DICTIONARIES[lang], setLang }), [lang, setLang]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  return useContext(I18nContext);
}

export function LanguageSwitcher({ className }: { className?: string }) {
  const { lang, t, setLang } = useI18n();
  return (
    <label className={className}>
      <span className="sr-only">{t.language.label}</span>
      <select
        className="h-8 rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        value={lang}
        onChange={(e) => setLang(e.target.value as Lang)}
      >
        {LANGS.map((code) => (
          <option key={code} value={code} lang={code}>
            {t.language[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
