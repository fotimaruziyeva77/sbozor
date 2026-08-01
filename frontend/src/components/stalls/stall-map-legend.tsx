"use client";

import { Ban, Wrench } from "lucide-react";
import { useTranslations } from "next-intl";

import { TONE_STYLES } from "@/components/stalls/stall-tone";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * Xarita legendasi — MAJBURIY (UI-SPEC §7.4).
 *
 * Katak holati rangdan tashqari uchta kanal bilan ham beriladi: chegara
 * turi (uzuq-uzuq = sotuvchisiz), ikonka va matn uslubi. Bularning hech
 * biri O'Z-O'ZIDAN tushunarli emas — legendasiz "uzuq-uzuq chegara nima
 * degani?" savoliga hech kim javob topa olmaydi va rangdan mustaqil
 * kanallar (WCAG 1.4.1) foydasiz bo'lib qolardi.
 *
 * ⚠ Legenda MOBIL'DA HAM ko'rinadi va yig'ilmaydi: aynan telefonda
 * ishlaydigan bozor admini uchun u eng kerak.
 * =============================================================================
 */

/** Namuna katak — DEKORATIV: barmoq nishoni emas, shuning uchun 24px. */
function LegendSwatch({
  className,
  icon,
}: {
  className: string;
  icon?: "wrench" | "ban";
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative inline-flex size-6 shrink-0 items-center justify-center rounded-sm border border-border-ui",
        className,
      )}
    >
      {icon === "wrench" ? <Wrench className="size-3" /> : null}
      {icon === "ban" ? <Ban className="size-3" /> : null}
    </span>
  );
}

export function StallMapLegend() {
  const t = useTranslations();

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-surface p-4">
      <h2 className="text-sm font-semibold">{t("map.legendTitle")}</h2>

      <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <li className="flex items-center gap-2">
          <LegendSwatch className={cn(TONE_STYLES.neutral, "border-solid")} />
          {t("map.legendActive")}
        </li>

        <li className="flex items-center gap-2">
          <LegendSwatch className={cn(TONE_STYLES.neutral, "border-dashed")} />
          {t("map.legendNoVendor")}
        </li>

        <li className="flex items-center gap-2">
          <LegendSwatch
            className={cn(TONE_STYLES.muted, "border-solid")}
            icon="wrench"
          />
          {t("map.legendMaintenance")}
        </li>

        <li className="flex items-center gap-2">
          <LegendSwatch
            className={cn(TONE_STYLES.off, "border-solid")}
            icon="ban"
          />
          {t("map.legendClosed")}
        </li>
      </ul>
    </div>
  );
}
