import { readdirSync } from "node:fs";
import path from "node:path";
import type { MetadataRoute } from "next";

/*
 * robots.txt — Next 16 fayl konventsiyasi (10-04 Task 3, T-10-09).
 *
 * ⛔ Fayl `src/app/` ILDIZIDA (`sitemap.ts` bilan bir xil sabab, L-24):
 * `proxy.ts` matcheri nuqtali yo'llarni chetlab o'tadi — locale prefiksi
 * qo'shilmaydi.
 *
 * ⛔⛔ Disallow ro'yxati KATALOGDAN HOSILA (Tuzoq 8): `(app)`/`(auth)`
 * guruhlarining birinchi darajali segmentlari o'qiladi. Qo'lda yozilgan
 * ro'yxat TAQIQ — 25-chi sahifa qo'shilganda u jimgina ochiq qolardi.
 * Sabab (T-10-09): app sahifalari `/login` ga redirect qiladi, lekin
 * indekslangan `/uz/collect` havolasi qidiruv natijasida ichki tuzilmani
 * oshkor qilib foydalanuvchini o'lik havolaga olib borardi.
 *
 * `readdirSync` BUILD vaqtida yuguradi: marshrut Request-time API
 * ishlatmagani uchun statik hosil bo'ladi — ishlab turgan serverda `src/`
 * ga murojaat YO'Q.
 */

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://sbozor.uz";

/** `(app)`/`(auth)` guruhlarining birinchi darajali segmentlari — HOSILA. */
function protectedSegments(): string[] {
  const localeDir = path.join(process.cwd(), "src", "app", "[locale]");
  const segments = new Set<string>();
  for (const group of ["(app)", "(auth)"]) {
    for (const entry of readdirSync(path.join(localeDir, group), {
      withFileTypes: true,
    })) {
      // Faqat kataloglar — `layout.tsx` kabi fayllar segment emas.
      if (entry.isDirectory()) {
        segments.add(entry.name);
      }
    }
  }
  return [...segments].sort();
}

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        // Landing ildizlari va `maxfiylik` ochiq qoladi (Disallow'ga
        // tushmagan hamma narsa) — indekslash SC#5 ning sharti.
        allow: "/",
        disallow: [
          "/api/",
          // `/*/dashboard` shakli uchala locale prefiksini bitta naqsh
          // bilan yopadi (`/uz/...`, `/uz-cyrl/...`, `/ru/...`).
          ...protectedSegments().map((segment) => `/*/${segment}`),
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
