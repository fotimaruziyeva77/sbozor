import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";

/*
 * Davlat ishonch bloki — 4 band (10-UI-SPEC §11.1, ROADMAP SC#4).
 * Server Component; `id="ishonch"` — hero'ning qisqa `trust.residency`
 * yorlig'i shu anchorga havola qiladi (G-land-4(c), 10-05/10-07 tomoni).
 *
 * ⛔⛔ REZIDENTLIK BANDI — BU FAZANING HUQUQIY TUGUNI (§11.2, T-10-13):
 *    «Ma'lumotlar O'zbekistonda» bugun TO'LIQ ROST EMAS (server Contabo'da,
 *    ko'chish davlat bosqichidan oldin rejalashtirilgan — CLAUDE.md
 *    «Data-rezidentlik»). Shuning uchun bu blok BUGUNGI mexanizmni aytadi
 *    (shifrlangan tunnel, O'zR qonunchiligiga muvofiq boshqaruv) va
 *    kelajakni va'da qilmaydi — «joylashuv talabi bo'lsa ko'chiriladi va
 *    shartnomada qayd etiladi» sharti bilan. Hero'dagi qisqa shakl
 *    qulflangan copy [K-2] va u shu blokka havola qiladi.
 *
 * ⚠ Bandning YAKUNIY huquqiy shakli mahalliy yurist tasdig'i ostida;
 *   tetigi — go-live, bandi — 10-08 dagi HUMAN-UAT (reja talabi).
 *
 * Qolgan uch band rost va o'lchangan: NVR faqat VPN orqali (3-faza),
 * har amal audit jurnalida (1-faza `audit_log`), 3 til — sahifaning o'zida
 * isbotlanadi (header'dagi til almashtirgich).
 *
 * ⛔ Sarlavha ierarxiyasi: blok o'z `<h2>` sini chizadi (10-07 `<Section>`
 *    ni `title` prop'siz va `id` siz o'raydi — anchor shu faylda).
 */
const TRUST_BANDS = ["residency", "vpn", "audit", "languages"] as const;

export async function TrustBlock() {
  const t = await getTranslations("landing");

  return (
    <div className="flex flex-col gap-6" id="ishonch">
      <Reveal>
        <p className="landing-kicker">{t("trustBlock.kicker")}</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight">
          {t("trustBlock.title")}
        </h2>
      </Reveal>
      {/* v2: to'rt ustun (yorug' fon) — davlat/yurist savollariga to'g'ridan. */}
      <div className="grid gap-x-6 gap-y-6 sm:grid-cols-2 min-[1100px]:grid-cols-4">
        {TRUST_BANDS.map((key, index) => (
          <Reveal delayIndex={index} key={key}>
            <div className="flex flex-col gap-1">
              <h3 className="text-lg font-semibold">
                {t(`trustBlock.${key}.title`)}
              </h3>
              <p className="max-w-[66ch] text-sm leading-relaxed text-text-muted">
                {t(`trustBlock.${key}.body`)}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  );
}
