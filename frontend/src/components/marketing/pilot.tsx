import { getTranslations } from "next-intl/server";

import { Reveal } from "@/components/marketing/reveal";
import { Badge } from "@/components/ui/badge";

/*
 * Pilot holati bloki (10-UI-SPEC §11.4, ROADMAP SC#4, K-7; T-10-13).
 * Server Component; holat rozetkasi — `Badge tone="warning"`.
 *
 * ⛔⛔ RAQAM NOL: «X% o'sish», «Y so'm topildi», «taxminan 200 rasta» —
 *    BIRORTASI ham yozilmaydi. G-land-4(f) (10-07) `landing.pilot.*`
 *    qiymatlarida `\d` ni 0 ga qulflaydi — matn katalogda (10-02) va u
 *    raqamsiz o'lchangan. Komponentda literal copy YO'Q.
 *
 * ⛔ Copy'ning oxirgi jumlasi («oldindan raqam yozmaymiz») ATAYIN va u
 *    pozitsiyalash quroli: raqib «ishlab chiqilmoqda» deb yozib do'kon
 *    badge'larini qo'ygan — biz kamroq va'da qilib ko'proq ishonch olamiz
 *    (brief §7.5 «Halollik»).
 *
 * ⛔ Sarlavha ierarxiyasi: blok o'z `<h2>` sini chizadi (10-07 `<Section>`
 *    ni `title` prop'siz o'raydi).
 */
export async function Pilot() {
  const t = await getTranslations("landing");

  return (
    <Reveal>
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-2xl font-semibold tracking-tight">
            {t("pilot.title")}
          </h2>
          <Badge tone="warning">{t("pilot.status")}</Badge>
        </div>
        <p className="max-w-[66ch] text-sm leading-relaxed text-text-muted">
          {t("pilot.body")}
        </p>
      </div>
    </Reveal>
  );
}
