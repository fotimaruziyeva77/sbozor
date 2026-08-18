import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";

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
      {/* v2: och ko'k gradient banner, markazda — ⭐ dalil bayonot sifatida. */}
      <div className="landing-proof rounded-2xl px-8 py-12 text-center">
        <p aria-hidden="true" className="text-lg text-warning-text">
          ★
        </p>
        <h2 className="mx-auto mt-3 max-w-[32ch] landing-h2 tracking-tight text-balance">
          {t("proof.title")}
        </h2>
        <p className="mx-auto mt-3 max-w-[52ch] text-lg leading-relaxed text-text-muted">
          {t("proof.body")}
        </p>
        <p className="mx-auto mt-2 max-w-[52ch] text-sm leading-relaxed text-text-muted">
          {t("proof.note")}
        </p>
      </div>
    </Reveal>
  );
}
