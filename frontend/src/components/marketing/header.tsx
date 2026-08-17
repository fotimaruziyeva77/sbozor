import { getTranslations } from "next-intl/server";

import { MarketingLocaleSwitcher } from "@/components/marketing/locale-switcher";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

/*
 * Landing header — Server Component, ⛔ sticky EMAS (§17.2: sticky header
 * mobil ekranning ~12% ini yeydi va bu sahifada doimiy navigatsiya
 * zaruratini oqlaydigan chuqurlik yo'q).
 *
 * Tarkib (UI-SPEC §9.1, blok 0): brand · til almashtirgich · «Tizimga
 * kirish» havolasi. ⛔ Tema tugmasi KO'RSATILMAYDI (§6.4): tema — ish
 * qurolining sozlamasi, marketing yuzasiniki emas; landing temani FOUC
 * skripti orqali meros oladi.
 *
 * ⛔ Skip-link — sahifaning BIRINCHI fokuslanadigan elementi (§15.7,
 * majburiy: sahifa uzun va header'da til almashtirgichning 3 tugmasi bor).
 * Oddiy `<a href="#kontent">` — sahifa ichidagi anker navigatsiya emas,
 * shuning uchun locale prefiksli `Link` shart emas.
 *
 * Havolalar `@/i18n/navigation` ning `Link` idan (grep darvozasi) va
 * barchasi ≥44px nishon (§15.10) — `buttonVariants` ning `md` balandligi
 * 40px, shuning uchun `min-h-11` alohida qo'shiladi.
 */
export async function Header() {
  const t = await getTranslations("landing");
  const tCommon = await getTranslations("common");

  return (
    <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-6 py-4">
      <a
        className={cn(
          "sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-6 focus:z-50",
          "focus:inline-flex focus:min-h-11 focus:items-center focus:rounded-md",
          "focus:border focus:border-border focus:bg-surface focus:px-4",
          "focus:text-sm focus:text-text",
        )}
        href="#kontent"
      >
        {t("nav.skipToContent")}
      </a>
      {/* So'zbelgi — dizayn v2: bosh harf oq, qolgani aksent (S·BOZOR). */}
      <Link
        className="inline-flex min-h-11 items-center text-lg font-bold tracking-[0.08em] text-text"
        href="/"
      >
        {tCommon("appName").slice(0, 1)}
        <span className="text-accent-text">{tCommon("appName").slice(1)}</span>
      </Link>
      <div className="flex items-center gap-3">
        <MarketingLocaleSwitcher />
        <Link
          className={cn(
            buttonVariants({ variant: "ghost", size: "md" }),
            "min-h-11",
          )}
          href="/login"
        >
          {t("hero.ctaSecondary")}
        </Link>
      </div>
    </header>
  );
}
