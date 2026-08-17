"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import { setTheme, THEMES, useTheme } from "@/lib/theme";

/*
 * Bir bosishli tema almashtirgich (09-UI-SPEC §11.2, ROADMAP SC#3).
 *
 * `locale-switcher.tsx` ning AYNAN naqshi: `role="group"` + `aria-label`,
 * faol tugmada `aria-current="true"` (§15). IKKI ATAYLAB FARQ:
 *
 *   1. ⛔ Marshrut ham, server ham YO'Q: `useTransition`/`router.replace`
 *      KO'CHIRILMAGAN (tema URL'ga tegmaydi) va `apiFetch(ME_PATH, ...)`
 *      ham YO'Q — tema QURILMA xossasi, profil emas (D-15 farqi §11.2).
 *      Butun amal sinxron: `setTheme` DOM atributi + `localStorage`.
 *   2. ⛔ Tugmalar `min-h-11` (≥44px barmoq nishoni, §15) — switcher'ning
 *      `py-1` kichik nishoni EMAS: bu tugmani kassir quyoshda, qo'lqopda
 *      ham bosadi.
 *
 * ⛔ Tema o'zgarishida toast CHIQMAYDI (§15) — natija ekranning o'zida
 *    ko'rinadi; qo'shimcha signal ma'noni suyultirardi.
 */

export function ThemeToggle() {
  const t = useTranslations("theme");
  const active = useTheme();

  return (
    <div
      aria-label={t("label")}
      className="inline-flex items-center gap-1 rounded-md border border-border bg-surface p-1"
      role="group"
    >
      {THEMES.map((theme) => {
        const isActive = theme === active;
        return (
          <button
            aria-current={isActive ? "true" : undefined}
            className={cn(
              "min-h-11 rounded-sm px-2 text-xs font-semibold transition-colors",
              isActive
                ? "bg-accent text-accent-fg"
                : "text-text-muted hover:bg-surface-muted hover:text-text",
            )}
            key={theme}
            onClick={() => setTheme(theme)}
            type="button"
          >
            {t(theme)}
          </button>
        );
      })}
    </div>
  );
}
