import { routing } from "@/i18n/routing";

/*
 * =============================================================================
 * LOCALE PREFIKSLI MANZIL — `@/i18n/navigation` GA TEGMASDAN.
 *
 * ⚠⚠ NEGA `Link` HAM, `getPathname` HAM ISHLATILMAYDI — O'LCHANGAN.
 *
 *   `@/i18n/navigation` `next-intl/navigation` ni, u esa `next/navigation`
 *   ni import qiladi va o'sha zanjir VITEST OSTIDA UMUMAN YECHILMAYDI:
 *
 *     Error: Cannot find module '…/node_modules/next/navigation'
 *            imported from …/next-intl/dist/esm/development/navigation/
 *            react-client/createNavigation.js
 *
 *   Ya'ni muammo render paytidagi router konteksti EMAS, MODULNI IMPORT
 *   QILISHNING O'ZI. `app-shell.test.tsx` va `wizard-stepper.test.tsx`
 *   shu sababdan butun modulni mock qiladi.
 *
 *   O'lchangan narx (manba: `camera-row.tsx` ning eski izohi): import
 *   qo'shilgan holatda TO'RTTA test fayli «0 test» bilan yiqildi va 27
 *   test yo'qoldi. Endi bu modulning iste'molchilaridan biri —
 *   `ForbiddenNotice` — YIGIRMATA sahifada render qilinadi, ya'ni o'sha
 *   zanjirni bu yerga kiritish narxi yigirma test fayliga ko'tarilardi.
 *
 * ⚠ NEGA ENDI UMUMIY MODUL: bu funksiya YETTI MARTA nusxa ko'chirilgan
 *   edi (`collect`, `collect/shift`, `occupancy`, `review`,
 *   `review/blind`, `review/uncertain` sahifalari va `camera-row.tsx`).
 *   `review/page.tsx` izohi bu qadamni oldindan nomlagan: «uni umumiy
 *   modulga chiqarish TO'G'RI qadam, lekin o'sha modul bu rejaning fayl
 *   to'plamidan tashqarida». Endi to'plamning ICHIDA.
 *
 *   Yagona nusxa `scripts/forbidden-notice.test.mjs` (c) bandi bilan
 *   qulflangan: `src/` da `function localeHref` AYNAN BIR MARTA.
 *
 * ⚠ NARXI HALOL AYTILADI: oddiy `<a>` TO'LIQ sahifa yuklashini beradi,
 *   klient tomondagi o'tishni emas. Iste'molchilarning hammasi — sessiya
 *   chegarasi, zona muharriri va rad etish ekrani, ya'ni KUNLIK amal
 *   emas; farq sezilmaydi.
 *
 * ⚠ `"use client"` YO'Q va kerak emas: bu SOF FUNKSIYA, hook emas.
 *   Chaqiruvchi `useLocale()` ni o'zi o'qiydi va natijani shu yerga
 *   uzatadi.
 * =============================================================================
 */

/**
 * `localeHref("uz-Latn", "/dashboard")` -> `/uz/dashboard`.
 *
 * ⚠ PREFIKS XARITASI NUSXA KO'CHIRILMAYDI. Qiymat `routing.localePrefix`
 *   dan olinadi, ya'ni `/uz`, `/uz-cyrl` bir joyda qoladi. Prefiksi
 *   ko'rsatilmagan til uchun standart — `/{locale}` (`routing.ts` izohi:
 *   «`ru` uchun prefiks ko'rsatilmagan → standart `/ru`»).
 */
export function localeHref(locale: string, path: string): string {
  /*
   * `localePrefix` — BIRLASHMA tipi (`"always" | {mode, prefixes?}`),
   * shuning uchun `typeof` bilan toraytiriladi. `Partial<Record<string,…>>`
   * annotatsiyasi esa `useLocale()` ning `string` ini indeks sifatida
   * ishlatishga ruxsat beradi: ro'yxatda yo'q til (bo'lishi mumkin emas,
   * lekin tip buni bilmaydi) standart shoxga tushadi.
   */
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return `${prefixes[locale] ?? `/${locale}`}${path}`;
}
