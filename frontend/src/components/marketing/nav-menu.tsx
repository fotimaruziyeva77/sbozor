import { getTranslations } from "next-intl/server";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * LANDING MENYUSI — «yuqoridan turib hammasini ko'rish» (260819).
 *
 * ⛔⛔ NEGA QO'SHILDI: raqobatchining sarlavhasida beshta bo'lim havolasi
 *     turibdi va tashrifchi sahifani AYLANTIRMASDAN nima borligini
 *     biladi. Bizda esa faqat brand va kirish bor edi — mazmunni
 *     ko'rish uchun scroll qilish shart edi.
 *
 * ⛔ HAVOLALAR — SAHIFA ICHIDAGI ANKER (`#muammo`), marshrut EMAS.
 *    Shuning uchun `@/i18n/navigation` ning `Link` i ISHLATILMAYDI: u
 *    locale prefiksini qo'shib `/uz#muammo` qilardi va sahifani qayta
 *    yuklardi. Oddiy `<a href="#…">` brauzerning o'z silliq siljishini
 *    ishlatadi.
 *
 * ⛔ SERVER COMPONENT — `"use client"` YO'Q va bu ONGLI (§4.4 yopiq
 *    reyestri): menyuda holat ham, hodisa ham yo'q — beshta anker
 *    havola, xolos. Brauzerning o'z anker siljishi JS'siz ishlaydi,
 *    demak orol ochish LCP yo'lini bejiz hidratatsiyaga bog'lardi.
 *
 * ⛔ 1024px DAN PASTDA YASHIRILADI (`hidden lg:flex`) va chegara AYNAN
 *    shu yerda — chunki O'LCHANDI: `md` (768px) da menyu ochilganda
 *    sarlavha 1051px joy talab qilib, planshetlarning HAMMASIDA
 *    gorizontal scroll berardi (768/820/900/1024 — to'rttasi ham).
 *    Beshta havolaning o'zi ~490px, ya'ni 768px ekranning uchdan
 *    ikkisi. Eski izoh «375px» deb yozilgan edi — u faqat eng tor
 *    holatni ko'rgan.
 *
 * ⛔ MOBILDA YASHIRILADI va bu ONGLI: 375px da beshta
 *    havola brand bilan kirish tugmasini siqib qo'yardi. Mobil
 *    tashrifchi baribir scroll qiladi — u yerda menyu yutuq bermaydi,
 *    aksincha eng qimmat element (kirish tugmasi) joyini yeydi.
 *
 * ⚠ Bo'limlar `(marketing)/page.tsx` dagi `id` lar bilan JUFT: biri
 *   o'zgarsa havola o'lik bo'ladi. Shuning uchun ro'yxat shu yerda,
 *   BITTA joyda.
 * =============================================================================
 */

const SECTIONS = [
  { id: "muammo", key: "problem" },
  { id: "qanday", key: "how" },
  { id: "rollar", key: "who" },
  { id: "ishonch", key: "trust" },
  { id: "demo", key: "demo" },
] as const;

export async function MarketingNav({ className }: { className?: string }) {
  const t = await getTranslations("landing");

  return (
    <nav
      aria-label={t("nav.sections")}
      className={cn("hidden shrink-0 items-center gap-1 lg:flex", className)}
    >
      {SECTIONS.map((section) => (
        <a
          /* ⚠ `whitespace-nowrap` — sarlavha `flex-wrap` bo'lgani uchun
             (mobil ikki qatori) havolalar siqilib IKKI SATRGA bo'linib
             ketardi: «Qanday / ishlaydi». Xromda ko'rindi. */
          className="inline-flex min-h-11 items-center whitespace-nowrap rounded-md px-2 text-sm text-text-muted transition-colors hover:bg-text/10 hover:text-text"
          href={`#${section.id}`}
          key={section.id}
        >
          {t(`nav.${section.key}`)}
        </a>
      ))}
    </nav>
  );
}
