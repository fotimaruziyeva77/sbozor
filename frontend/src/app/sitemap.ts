import type { MetadataRoute } from "next";

import { routing } from "@/i18n/routing";

/*
 * sitemap.xml — Next 16 fayl konventsiyasi (10-04 Task 3, ROADMAP SC#5).
 *
 * ⛔ Fayl `src/app/` ILDIZIDA, `[locale]/` ichida EMAS: `proxy.ts:17`
 * matcheri (`"/((?!api|_next|_vercel|.*\\..*).*)"`) nuqtali yo'llarni
 * chetlab o'tadi, ya'ni `/sitemap.xml` ga locale prefiksi qo'shilmaydi —
 * `[locale]/` ichida u umuman topilmasdi (L-24, o'lchangan).
 *
 * ⛔ `headers()`/`cookies()` ISHLATILMAYDI — Request-time API'siz bu marshrut
 * build vaqtida statik hosil bo'ladi va keshlanadi (SSG sharti).
 *
 * Yozuvlar: uchala locale ildizi + uchala `maxfiylik` sahifasi, har birida
 * `alternates.languages` (hreflang) — qidiruv tizimi til variantlarini
 * bitta guruh sifatida ko'radi.
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sbozor.uz";

/**
 * URL prefiksi — `i18n/routing.ts` dan HOSILA (qo'lda takrorlanmaydi):
 * custom prefiks bo'lmagan locale (ru) standart `/{locale}` oladi —
 * next-intl'ning o'z qoidasi bilan bir xil.
 */
function urlPrefix(locale: string): string {
  // `localePrefix` ittifoqida `prefixes`siz rejimlar ham bor — `in` sharti.
  const config = routing.localePrefix;
  const prefixes: Partial<Record<string, string>> =
    typeof config === "object" && "prefixes" in config
      ? (config.prefixes ?? {})
      : {};
  return prefixes[locale] ?? `/${locale}`;
}

export default function sitemap(): MetadataRoute.Sitemap {
  // Ommaviy sahifalar reyestri: ildiz (landing) va maxfiylik siyosati.
  // App marshrutlari bu yerga KIRMAYDI — ular robots.ts da Disallow.
  const pages = ["", "/maxfiylik"];

  return pages.flatMap((page) => {
    const languages = Object.fromEntries(
      routing.locales.map((locale) => [
        locale,
        `${SITE_URL}${urlPrefix(locale)}${page}`,
      ]),
    );

    return routing.locales.map((locale) => ({
      url: `${SITE_URL}${urlPrefix(locale)}${page}`,
      alternates: { languages },
    }));
  });
}
