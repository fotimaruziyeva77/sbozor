"use client";

import type { CSSProperties } from "react";
import { useTransition } from "react";
import { useLocale, useTranslations } from "next-intl";

import { usePathname, useRouter } from "@/i18n/navigation";
import { cn } from "@/lib/cn";

/*
 * ANONIM til almashtirgich — marketing (landing) sahifasi uchun (10-03, B-1/C).
 *
 * `shell/` dagi almashtirgichdan MUSTAQIL variant. Farq bitta va u butun
 * faylning mavjudlik sababi: anonim tashrifchida PROFIL YO'Q — bosish faqat
 * URL prefiksini almashtiradi (`/uz` -> `/uz-cyrl` -> `/ru`), hech qanday
 * yozuv so'rovi ketmaydi va sessiya do'koni o'qilmaydi. Shu tufayli:
 *   1. Komponent sessiya provayderisiz render bo'ladi — `(marketing)`
 *      guruhida provayder yo'q va `next build` SSG prerender'i yiqilmaydi
 *      (10-RESEARCH B-1).
 *   2. Import grafi zod'li kutubxona qatlamini TORTMAYDI — o'lchangan
 *      69 KB gzip chunk anonim sahifaga umuman kelmaydi (10-RESEARCH B-2).
 *      Bu qulf `locale-switcher.test.tsx` da manba satr skani bilan
 *      MEXANIK o'lchanadi, shuning uchun o'sha modullarning nomi bu faylda
 *      (izohda ham) literal yozilmaydi.
 *
 * DIQQAT: `usePathname`/`useRouter` FAQAT `@/i18n/navigation` dan olinadi —
 * Next'ning o'z navigatsiya moduli locale prefiksini bilmaydi va
 * `replace(pathname, {locale})` shakli unda umuman yo'q (grep darvozasi
 * bilan qulflangan qoida; taqiqlangan modul nomi literal yozilmaydi).
 *
 * ⛔ Bu fayl `G-land-1(a)` klient orollari reyestrining BESHINCHI a'zosi
 * (10-07 da yoziladi): hero-scene, step-line, reveal, demo-form va SHU fayl.
 */

/*
 * Ro'yxat va yorliqlar SHU faylda literal — bu takror EMAS (10-RESEARCH A8):
 * endonimlar tarjima qilinmaydi (§9.2 qoidasi) va locale ro'yxati routing
 * kontraktining o'zi, ya'ni ikkinchi manba drift bera olmaydi. Umumiy
 * kutubxona faylidan import qilish esa zod grafini anonim sahifaga
 * qaytarib olib kelardi (B-2) — aynan shu importni kesish uchun fayl
 * tug'ilgan.
 */
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"] as const;

type MarketingLocale = (typeof LOCALES)[number];

/** Endonimlar: til nomi har doim O'Z tilida (01-08 qarori, meros). */
const LOCALE_LABELS: Readonly<Record<MarketingLocale, string>> = {
  "uz-Latn": "O'zbekcha",
  "uz-Cyrl": "Ўзбекча",
  ru: "Русский",
};

/*
 * Sirg'anuvchi faol indikator — `shell/` variantidan AYNAN ko'chirilgan naqsh
 * (09-UI-SPEC §12.9): uchala tugma bir xil `w-20`, indikator `translateX`
 * bilan siljiydi, o'lchov (`getBoundingClientRect`) ISHLATILMAYDI.
 * `width`/`left` animatsiya qilinmaydi (G-motion-3(a) ruhi).
 */

/** Tugma VA indikatorning umumiy kenglik sinfi — bitta haqiqat manbai. */
const BUTTON_WIDTH_CLASS = "w-20";

export function MarketingLocaleSwitcher() {
  const t = useTranslations("common");
  const active = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function change(next: MarketingLocale) {
    if (next === active) return;

    startTransition(() => {
      // Anonim oqim: FAQAT URL almashadi. Profil yozuvi yo'q — tanlov
      // sessiyaga bog'lanmaydi (D-15: brauzer tili ham so'ralmaydi).
      router.replace(pathname, { locale: next });
    });
  }

  /* Faol indeks — indikatorning yagona kirishi (`--idx`). */
  const activeIndex = LOCALES.findIndex((code) => code === active);

  return (
    <div
      aria-label={t("languageLabel")}
      className="relative inline-flex items-center gap-1 rounded-md border border-border bg-surface p-1"
      role="group"
    >
      {/*
        * Indikator tugmalardan OLDIN chiziladi: absolut element bir xil
        * stacking kontekstda keyingi `relative` tugmalar OSTIDA qoladi —
        * matn kontrasti (`text-accent-fg` faol tugmada) buzilmaydi.
        * `aria-hidden` + `pointer-events-none` — bu bezak, bosishni yutmaydi.
        */}
      {activeIndex >= 0 ? (
        <span
          aria-hidden="true"
          className={cn(
            "pointer-events-none absolute inset-y-1 left-1 rounded-sm bg-accent",
            "transition-transform",
            BUTTON_WIDTH_CLASS,
          )}
          data-active-index={activeIndex}
          style={
            {
              "--idx": String(activeIndex),
              transform: "translateX(calc(var(--idx) * (100% + 0.25rem)))",
            } as CSSProperties
          }
        />
      ) : null}
      {LOCALES.map((code) => {
        const isActive = code === active;
        return (
          <button
            aria-current={isActive ? "true" : undefined}
            className={cn(
              "relative rounded-sm px-2 py-1 text-xs font-semibold transition-colors",
              "disabled:pointer-events-none disabled:opacity-50",
              BUTTON_WIDTH_CLASS,
              /* Faol fon INDIKATORDA — tugma faqat matn rangini oladi. */
              isActive
                ? "text-accent-fg"
                : "text-text-muted hover:bg-surface-muted hover:text-text",
            )}
            disabled={isPending}
            key={code}
            lang={code}
            onClick={() => change(code)}
            type="button"
          >
            {LOCALE_LABELS[code]}
          </button>
        );
      })}
    </div>
  );
}
