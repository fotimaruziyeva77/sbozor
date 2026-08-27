"use client";

import { Contrast, Moon, Sun } from "lucide-react";
import type { LucideIcon } from "lucide-react";
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
 *
 * ⛔⛔ 260819: YORLIQ -> IKONKA (foydalanuvchi talabi + o'lchov).
 *
 *     Uchta so'z («Yorug'» · «Tungi» · «Quyosh ostida») guruhni 208px
 *     qilardi va 375px ekranda sarlavha ekrandan yorib chiqardi
 *     (Xromda o'lchandi: sarlavha ichki kengligi 625px). Ikonkali
 *     guruh 132px — 76px tejaldi va tanlov UZOQDAN taniladi.
 *
 * ⛔ MATN YO'QOLMAYDI: har tugmada `aria-label` VA `title` — skrinrider
 *    ham, sichqoncha ostidagi maslahat ham o'sha tarjimani beradi.
 *    Ikonka yolg'iz signal EMAS (§15.12).
 *
 * ⛔ IKONKA TANLOVI MA'NOLI: quyosh — yorug', oy — tungi, KONTRAST
 *    doirasi — «quyosh ostida». Uchinchisiga yana quyosh qo'yish
 *    («SunMedium») birinchisi bilan bir xil o'qilardi; kontrast belgisi
 *    esa rejimning MAZMUNINI aytadi — maksimal kontrast.
 */

/** Tema -> ikonka. Reyestr `THEMES` bilan bir xil tartibda o'qiladi. */
const THEME_ICONS: Readonly<Record<(typeof THEMES)[number], LucideIcon>> = {
  light: Sun,
  dark: Moon,
  sun: Contrast,
};

export function ThemeToggle() {
  const t = useTranslations("theme");
  const active = useTheme();

  return (
    <div
      aria-label={t("label")}
      className="inline-flex shrink-0 items-center gap-0.5 rounded-full bg-surface-muted p-1"
      role="group"
    >
      {THEMES.map((theme) => {
        const isActive = theme === active;
        const Icon = THEME_ICONS[theme];
        return (
          <button
            aria-current={isActive ? "true" : undefined}
            aria-label={t(theme)}
            className={cn(
              "inline-flex size-10 items-center justify-center rounded-full transition-colors",
              isActive
                ? "bg-accent text-accent-fg shadow-card"
                : "text-text-muted hover:bg-surface hover:text-text",
            )}
            key={theme}
            onClick={() => setTheme(theme)}
            title={t(theme)}
            type="button"
          >
            <Icon aria-hidden="true" className="size-4.5" strokeWidth={2} />
          </button>
        );
      })}
    </div>
  );
}
