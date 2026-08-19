import { FlaskConical } from "lucide-react";
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
    <div className="grid items-center gap-8 min-[841px]:grid-cols-2">
      <Reveal>
        <div className="flex flex-col gap-3">
          <div>
            <Badge tone="warning">{t("pilot.status")}</Badge>
          </div>
          <h2 className="landing-h2 tracking-tight">
            {t("pilot.title")}
          </h2>
          <p className="max-w-[56ch] landing-body text-text-muted">
            {t("pilot.body")}
          </p>
        </div>
      </Reveal>
      {/* v2: halollik — marketing kuchi sifatida alohida karta. */}
      <Reveal delayIndex={1}>
        <div className="landing-card rounded-lg border border-border bg-surface p-6 shadow-card">
          <span aria-hidden="true" className="landing-icon">
            <FlaskConical className="size-5" strokeWidth={1.75} />
          </span>
          <h3 className="mt-4 landing-h3">{t("pilot.whyTitle")}</h3>
          <p className="mt-2 max-w-[60ch] landing-body text-text-muted">
            {t("pilot.whyBody")}
          </p>
        </div>
      </Reveal>
    </div>
  );
}
