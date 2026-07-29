import { defineRouting } from "next-intl/routing";

/**
 * Locale marshrutlash konfiguratsiyasi (FOUND-04).
 *
 * DIQQAT — `localePrefix` ning custom shakli aynan `{mode, prefixes}` OBYEKTI.
 * Tekis `{locale: prefix}` obyekti (ba'zi manbalarda uchraydi) NOTO'G'RI.
 *
 * `ru` uchun prefiks ko'rsatilmagan → standart `/ru` ishlatiladi.
 *
 * Custom prefikslar faqat foydalanuvchiga ko'rinadi: ichkarida `/uz/...`
 * `/uz-Latn/...` ga rewrite qilinadi, ya'ni `app/[locale]/` segmenti
 * TO'LIQ locale qiymatini (`uz-Latn`) oladi, URL prefiksini (`uz`) emas.
 */
export const routing = defineRouting({
  locales: ["uz-Latn", "uz-Cyrl", "ru"],
  defaultLocale: "uz-Latn",
  localePrefix: {
    mode: "always",
    prefixes: {
      "uz-Latn": "/uz",
      "uz-Cyrl": "/uz-cyrl",
    },
  },
  // D-15: standart til HAR DOIM uz-Latn. Bu bayroq brauzerning
  // `Accept-Language` sarlavhasini HAM, cookie'ni HAM aniqlashdan chiqaradi.
  localeDetection: false,
});
