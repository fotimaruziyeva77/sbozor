import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";
import { Card, CardContent } from "@/components/ui/card";

/*
 * Bosh dalil bloki (10-UI-SPEC §9.1 blok 4) — `surface` kartada.
 *
 * ⛔ SPEC O-07 [ASSUMED] qabul qilinadi: hero'da BIR QATORLI qulflangan
 *    da'vo (`hero.claimStrong`+`claim` — 10-05 ning fayli), bu yerda esa
 *    KENGAYTIRILGAN shakl: nima kerak (NVR login-paroli, avtokashfiyot —
 *    `proof.body`) va nima kerak EMAS (yangi kamera, server, muhandis
 *    tashrifi — `proof.note`). Hero copy'si TAKRORLANMAYDI — matn
 *    `landing.proof.*` dan.
 *
 * ⛔ Sarlavha `<h2>` (§15.11 — bu blok o'z seksiyasining sarlavhasi; 10-07
 *    `<Section>` ni `title` prop'siz o'raydi). Dekorativ yulduz/ikonka
 *    QO'YILMAYDI: aksent reyestri (§6.3) yangi aksent yuzasini taqiqlaydi,
 *    kartaning `surface`+soya farqi o'zi yetarli.
 *
 * ⛔ Avtomatik harakat YO'Q — faqat scroll-reveal (G-land-3(c)).
 */
export async function Proof() {
  const t = await getTranslations("landing");

  return (
    <Reveal>
      <Card className="landing-glow mx-auto w-full max-w-2xl">
        <CardContent className="flex flex-col gap-3 pt-5">
          <h2 className="text-2xl font-semibold tracking-tight">
            {t("proof.title")}
          </h2>
          <p className="max-w-[66ch] text-sm leading-relaxed text-text-muted">
            {t("proof.body")}
          </p>
          <p className="max-w-[66ch] text-sm leading-relaxed">
            {t("proof.note")}
          </p>
        </CardContent>
      </Card>
    </Reveal>
  );
}
