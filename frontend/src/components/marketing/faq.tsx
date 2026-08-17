import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";

/*
 * FAQ — 5 savol (10-UI-SPEC §13.7), NATIVE `<details>`/`<summary>` (§15.8):
 * klaviatura va skrinrider JS'siz ishlaydi, ARIA akkordeoni QURILMAYDI.
 *
 * ⛔ FAQ matni KOMPONENTDA LITERAL YOZILMAYDI (T-10-14, G-land-4(d)):
 *    savol/javob faqat `landing.faq.*` katalogidan — 10-07 dagi JSON-LD
 *    `FAQPage` AYNI manbadan o'qiydi, ya'ni ikki manba mexanik imkonsiz.
 *
 * ⛔ Halollik bandlari (K-7 sinfi, katalogda o'lchangan):
 *    - 4-savolda narx YO'Q (brief §2.8 — aniq taklif demo suhbatida);
 *    - 5-savolda «5 daqiqada ishga tushadi» YO'Q — brief §6 dagi
 *      «Login-parol, 5 daqiqa» ULANISH haqida, TO'LIQ SOZLASH haqida emas.
 *
 * ⛔ Sarlavha ierarxiyasi: blok o'z `<h2>` sini chizadi (10-07 `<Section>`
 *    ni `title` prop'siz o'raydi). Savol — `<summary>` ichida `text-lg`
 *    (§7.1 Subheading roli); daraja emas, chunki `summary` interaktiv
 *    element va sarlavha teg ichiga olinmaydi.
 *
 * ⛔ Avtomatik harakat YO'Q — ochish/yopish native, animatsiyasiz.
 */
const FAQ_ITEMS = [1, 2, 3, 4, 5] as const;

export async function Faq() {
  const t = await getTranslations("landing");

  return (
    <div className="flex flex-col gap-6">
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight">
          {t("faq.title")}
        </h2>
      </Reveal>
      <Reveal>
        <div className="flex flex-col gap-3">
          {FAQ_ITEMS.map((n) => (
            <details
              className="rounded-lg border border-border bg-surface px-5"
              key={n}
            >
              {/* Native marker saqlanadi (display o'zgartirilmaydi — JS'siz
                  affordans); ≥44px nishon (§15.10) `py-4` bilan: 28px satr +
                  32px padding = 60px qator. */}
              <summary className="cursor-pointer py-4 text-lg font-semibold">
                {t(`faq.q${n}`)}
              </summary>
              <p className="max-w-[66ch] pb-4 text-sm leading-relaxed text-text-muted">
                {t(`faq.a${n}`)}
              </p>
            </details>
          ))}
        </div>
      </Reveal>
    </div>
  );
}
