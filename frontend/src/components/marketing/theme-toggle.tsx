"use client";

import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";

import { setTheme, useTheme } from "@/lib/theme";

/*
 * =============================================================================
 * LANDING TEMA TUGMASI — kun/tun (260819).
 *
 * ⛔⛔ NEGA QO'SHILDI VA NEGA AVVAL YO'Q EDI.
 *
 * `header.tsx` izohi temani ATAYIN chiqarmagan edi: «tema — ish
 * qurolining sozlamasi, marketing yuzasiniki emas». Bu qaror
 * O'ZGARTIRILDI (foydalanuvchi, raqobatchi bilan solishtiruvdan):
 * raqobatchining sarlavhasida kun/tun tugmasi bor va u tashrifchiga
 * darhol ko'rinadi. Landing kechqurun telefonda ham ochiladi.
 *
 * ⛔ IKKI HOLAT, UCH EMAS. Ish yuzasida uchta tema bor (`light`/`dark`/
 *    `sun`), lekin «quyosh ostida» — KASSIRNING dala rejimi va u
 *    landingda ma'nosiz. Uchinchi tugma tanlovni og'irlashtirardi.
 *
 * ⛔ HARAKAT NOZIK: faqat `background-color` va ikonka almashuvi.
 *    Aylanish, kattalashish va sakrash YO'Q — tugma sarlavhada turadi
 *    va har sahifa ochilganda ko'zga tashlanadi; u yerdagi «jonli»
 *    harakat charchatadi.
 * =============================================================================
 */

export function MarketingThemeToggle() {
  const theme = useTheme();
  const t = useTranslations("landing");

  const isDark = theme === "dark";

  return (
    <button
      aria-label={t("nav.theme")}
      aria-pressed={isDark}
      className="inline-flex size-11 items-center justify-center rounded-md border border-border bg-surface text-text-muted transition-colors hover:bg-text/10 hover:text-text"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      type="button"
    >
      {isDark ? (
        <Sun aria-hidden="true" className="size-4" />
      ) : (
        <Moon aria-hidden="true" className="size-4" />
      )}
    </button>
  );
}
