import { EyeOff, FileSearch, NotebookPen } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";
import { Card, CardContent, CardHeader } from "@/components/ui/card";

/*
 * Og'riq seksiyasi — 3 karta (10-UI-SPEC §9.1 blok 2). Server Component;
 * har karta `Reveal` bilan o'raladi (stagger 60ms — `delayIndex` -> `--i`).
 *
 * ⛔ «Patta» glossi — `landing.pain.a.body` da, BIR MARTA va «kunlik savdo
 *    to'lovi» shaklida (§13.3; `yig'im` — glossariy TAQIG'I, G7-9). Matnning
 *    o'zi katalogda (10-02) — komponentda literal copy yo'q.
 *
 * ⛔ Sarlavha ierarxiyasi (§15.11): blok o'z `<h2>` sini chizadi — 10-07
 *    kompozitsiyasi `<Section>` ni `title` PROP'SIZ o'raydi (aks holda h2
 *    ikkilanadi). Karta sarlavhalari — `<h3>` (`text-lg`).
 *
 * ⛔ Avtomatik harakat YO'Q — taymer chaqiruvlari bu faylda 0 marta
 *    (G-land-3(c); taqiqlangan chaqiruv nomlari izohda ham literal
 *    yozilmaydi — badge.tsx dagi kodbaza konvensiyasi).
 */
/*
 * ⛔ IKONKALAR (260819) — dekoratsiya EMAS, TANIB OLISH belgisi. Uchtasi
 *    ham og'riqning O'ZINI ko'rsatadi: daftar · qidiruv (dalil yo'q) ·
 *    yopiq ko'z (hamma joyni ko'rib bo'lmaydi). Har biri `aria-hidden` —
 *    ma'no sarlavhada, ikonka uni FAQAT tezroq topishga yordam beradi.
 */
const PAIN_CARDS = [
  { key: "a", Icon: NotebookPen },
  { key: "b", Icon: FileSearch },
  { key: "c", Icon: EyeOff },
] as const;

export async function PainCards() {
  const t = await getTranslations("landing");

  return (
    <div className="flex flex-col gap-6">
      <Reveal>
        <p className="landing-kicker">{t("pain.kicker")}</p>
        <h2 className="mt-3 landing-h2 tracking-tight">
          {t("pain.title")}
        </h2>
      </Reveal>
      <div className="grid gap-5 md:grid-cols-3">
        {PAIN_CARDS.map(({ key, Icon }, index) => (
          <Reveal className="h-full" delayIndex={index} key={key}>
            <Card className="landing-card h-full">
              <CardHeader>
                <span aria-hidden="true" className="landing-icon">
                  <Icon className="size-5" strokeWidth={1.75} />
                </span>
                <h3 className="mt-4 landing-h3">
                  {t(`pain.${key}.title`)}
                </h3>
              </CardHeader>
              <CardContent>
                <p className="max-w-[66ch] landing-body text-text-muted">
                  {t(`pain.${key}.body`)}
                </p>
              </CardContent>
            </Card>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
