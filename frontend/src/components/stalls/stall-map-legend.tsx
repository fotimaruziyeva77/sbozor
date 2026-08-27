"use client";

import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import type { StallTone } from "@/components/stalls/stall-map-types";
import {
  DAY_TONE_ICONS,
  INVENTORY_TONE_ICONS,
  TONE_STYLES,
} from "@/components/stalls/stall-tone";
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
 *
 * -----------------------------------------------------------------------
 * ⛔ IKKI GURUH, IKKI SHART (quick 260816-75e).
 *
 *   INVENTAR satrlari — HAR DOIM ko'rinadi (rasta reestri hammaga ochiq);
 *   TO'LOV satrlari   — FAQAT `showPaymentStates` bilan, ya'ni qatlam
 *                       chindan chizilganda. Huquqsiz ko'ruvchida ular
 *                       ⛔ UMUMAN chizilmaydi — o'chirilgan satr MAVJUD
 *                       imkoniyatni e'lon qilardi va foydalanuvchi
 *                       ko'rinmaydigan rangni izlab yurardi.
 * =============================================================================
 */

/** Namuna katak — DEKORATIV: barmoq nishoni emas, shuning uchun 24px. */
function LegendSwatch({
  className,
  icon: Icon,
}: {
  className: string;
  icon?: LucideIcon | null;
}) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "relative inline-flex size-6 shrink-0 items-center justify-center rounded-sm border border-border-ui",
        className,
      )}
    >
      {Icon ? <Icon className="size-3" /> : null}
    </span>
  );
}

/**
 * To'lov satrlari — ⛔ TARTIB D-C2 USTUVORLIGINING TESKARISI EMAS, LEKIN
 * O'QISH TARTIBI: eng ko'p uchraydigan holatdan (to'langan) eng kam
 * uchraydiganigacha. Ustuvorlik SERVERDA hal bo'ladi va legenda uni
 * ta'riflamaydi — u faqat «bu rang nima degani?» ga javob beradi.
 */
const PAYMENT_LEGEND: ReadonlyArray<{
  tone: StallTone;
  labelKey:
    | "map.legendPaid"
    | "map.legendDue"
    | "map.legendMismatch"
    | "map.legendFree"
    | "map.legendFairStall";
}> = [
  { tone: "paid", labelKey: "map.legendPaid" },
  { tone: "debt", labelKey: "map.legendDue" },
  { tone: "mismatch", labelKey: "map.legendMismatch" },
  { tone: "free", labelKey: "map.legendFree" },
  // 0028 — yarmarka: teal, chodir ikonkasi INVENTAR burchagidan keladi.
  { tone: "fair", labelKey: "map.legendFairStall" },
];

export function StallMapLegend({
  showPaymentStates = false,
}: {
  /** To'lov qatlami chizilyaptimi (huquq bor va javob keldi). */
  showPaymentStates?: boolean;
}) {
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
            icon={INVENTORY_TONE_ICONS.muted}
          />
          {t("map.legendMaintenance")}
        </li>

        <li className="flex items-center gap-2">
          <LegendSwatch
            className={cn(TONE_STYLES.off, "border-solid")}
            icon={INVENTORY_TONE_ICONS.off}
          />
          {t("map.legendClosed")}
        </li>
      </ul>

      {showPaymentStates ? (
        <ul className="flex flex-wrap gap-x-6 gap-y-2 border-t border-border pt-2 text-sm">
          {PAYMENT_LEGEND.map(({ tone, labelKey }) => (
            <li className="flex items-center gap-2" key={tone}>
              <LegendSwatch
                className={cn(TONE_STYLES[tone], "border-solid")}
                icon={DAY_TONE_ICONS[tone]}
              />
              {t(labelKey)}
            </li>
          ))}

          {/*
           * ⛔ «RANG YO'Q» SATRI MAJBURIY: `no_billing` katagi inventar
           *   tonida qoladi va legendasiz u «hali yuklanmadi» bilan
           *   ADASHTIRILARDI. Namuna katagi ATAYIN inventar tonida —
           *   u aynan shu ko'rinishni ko'rsatadi.
           */}
          <li className="flex items-center gap-2">
            <LegendSwatch className={cn(TONE_STYLES.neutral, "border-solid")} />
            {t("map.legendNoBilling")}
          </li>
        </ul>
      ) : null}
    </div>
  );
}
