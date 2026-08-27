import { getTranslations } from "next-intl/server";

import { MarketingLocaleSwitcher } from "@/components/marketing/locale-switcher";
import { MarketingNav } from "@/components/marketing/nav-menu";
import { MarketingThemeToggle } from "@/components/marketing/theme-toggle";
import { buttonVariants } from "@/components/ui/button";
import { Link } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

/*
 * Landing header — Server Component, ⛔ sticky EMAS (§17.2: sticky header
 * mobil ekranning ~12% ini yeydi va bu sahifada doimiy navigatsiya
 * zaruratini oqlaydigan chuqurlik yo'q).
 *
 * Tarkib (260819 da KENGAYDI, raqobatchi bilan solishtiruvdan):
 * brand · bo'limlar menyusi · til almashtirgich (bayroq bilan) ·
 * kun/tun tugmasi · «Tizimga kirish» TUGMASI.
 *
 * ⛔⛔ TO'RTTA O'ZGARISH VA HAR BIRINING SABABI:
 *
 *   1. MENYU — tashrifchi sahifani AYLANTIRMASDAN nima borligini
 *      ko'rsin. Ilgari mazmunga yetish uchun scroll SHART edi.
 *   2. KUN/TUN — landing kechqurun telefonda ham ochiladi. Oldingi
 *      qaror («tema ish qurolining sozlamasi») O'ZGARTIRILDI.
 *   3. BAYROQ — til tanlovi uzoqdan tanilsin (`locale-switcher.tsx`).
 *   4. KIRISH — `ghost` dan ASOSIY tugmaga. U sarlavhadagi yagona
 *      amal va u shunday ko'rinishi kerak; matn-havola sifatida u
 *      brand yonida yo'qolib ketardi.
 *
 * ⛔⛔ MOBIL — IKKI QATOR (`flex-wrap`), va bu MAJBURIY, bezak emas.
 *
 *   Yuqoridagi to'rtta qo'shimchadan keyin sarlavha 375px ekranga
 *   SIG'MAY qoldi: brend(83) + til(168) + tema(44) + kirish(131) +
 *   ichki bo'shliqlar = ~496px, ya'ni gorizontal scroll paydo bo'ldi.
 *   Bu Xromda O'LCHANDI (`scrollWidth 496 > clientWidth 375`), ko'z
 *   bilan emas — chunki overflow sahifaning eng past qismida sezilardi.
 *
 *   Yechim: 1-qator — brend + KIRISH (eng qimmat element ko'rinib
 *   turadi), 2-qator — til + tema. Hech narsa yashirilmaydi.
 *   ⛔ Ikki qator FAQAT 640px dan past: `sm:flex-nowrap` dan boshlab
 *     hammasi bitta qatorga sig'adi (o'lchangan ~500px).
 *   ⛔ Muqobil «tema tugmasini mobilda yashirish» RAD ETILDI: kun/tun
 *     aynan telefonda, kechqurun kerak bo'ladi.
 *
 * ⚠ Desktopda `nav` ning `md:mr-auto` si bo'sh joyni yeb, o'ng
 *   guruhni chekkaga suradi — `justify-between` o'rniga shu, chunki
 *   to'rtta bola bilan `justify-between` til/tema bilan kirish
 *   orasiga keraksiz ochiqlik solardi.
 *
 * ⚠ HARAKAT NOZIK (foydalanuvchi qoidasi): hover faqat fon rangini
 *   o'zgartiradi — sakrash, kattalashish va soya YO'Q. Sarlavha har
 *   sahifada ko'rinadi va u yerdagi «jonli» harakat charchatadi.
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
    <header className="relative mx-auto flex w-full landing-shell flex-wrap items-center gap-x-3 gap-y-3 px-6 py-4 sm:flex-nowrap lg:gap-4">
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
        className="mr-auto inline-flex min-h-11 shrink-0 items-center text-lg font-bold tracking-[0.08em] text-text lg:mr-4"
        href="/"
      >
        {tCommon("appName").slice(0, 1)}
        <span className="text-accent-text">{tCommon("appName").slice(1)}</span>
      </Link>
      <MarketingNav className="lg:mr-auto" />

      <Link
        className={cn(
          buttonVariants({ variant: "default", size: "md" }),
          "order-2 min-h-11 shrink-0 px-5 whitespace-nowrap sm:order-4",
        )}
        href="/login"
      >
        {t("hero.ctaSecondary")}
      </Link>

      <div className="order-3 flex w-full shrink-0 items-center justify-end gap-2 sm:order-3 sm:w-auto">
        <MarketingLocaleSwitcher />
        <MarketingThemeToggle />
      </div>
    </header>
  );
}
