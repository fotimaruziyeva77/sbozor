"use client";

import { HandCoins, ReceiptText, ScanSearch, Wallet } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { varianceDirection } from "@/components/billing/variance-cell";
import { StatStrip, StatTile } from "@/components/ui/stat-tile";
import { useAnomalies, useCharges } from "@/lib/billing-charge-queries";
import { formatAmount } from "@/lib/format-number";
import { useShiftReport } from "@/lib/shift-queries";

/*
 * =============================================================================
 * KUN XULOSASI — o'tgan kun uchun to'rtta javob (261016).
 *
 * Buyurtmachi: «Patta hisobi tushunarsiz». Sahifa uchta jadvaldan iborat
 * edi va «kecha qancha patta yozildi, qanchasi to'lanmadi, kassa mos
 * keldimi?» degan savolga javob berish uchun uchalasini o'qib chiqish
 * kerak edi. Kataklar shu savollarga ko'z yugurtirishda javob beradi.
 *
 * ⛔ FAQAT O'TGAN KUN UCHUN (`page.tsx` shu shartda chizadi): bugun
 *    yozilgan hisob yo'q — kutilayotgan summa bilan yozilgan hisob bir
 *    ekranda UCHRASHMAYDI (G-25). Shu sabab katak bloklar to'plamiga
 *    KIRMAYDI: unda `data-billing-block` ham, `data-billing-content` ham
 *    yo'q — u pastdagi bloklarning XULOSASI, alohida blok emas.
 *
 * ⛔ Sonlar pastdagi bloklar bilan AYNI so'rovlardan (React Query keshi):
 *    katak va jadval hech qachon ikki xil son ko'rsatmaydi. Qoldiq —
 *    jadvaldagi «Qoldiq» ustunining yig'indisi (server qatorlarni
 *    cheklamaydi: `charge_count === rows.length`).
 * =============================================================================
 */
export function BillingDaySummary({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const charges = useCharges(day);
  const anomalies = useAnomalies(day);
  const shifts = useShiftReport(day);

  const amount = (value: number) => formatAmount(format, value, locale);

  const unpaid = (charges.data?.rows ?? []).filter((row) => row.outstanding_soum > 0);
  const outstanding = unpaid.reduce((sum, row) => sum + row.outstanding_soum, 0);

  /* Ochiq smenada deklaratsiya yo'q — farq faqat YOPILGANLARDAN. */
  const closedShifts = (shifts.data?.rows ?? []).filter((row) => row.declared_soum !== null);
  const variance = closedShifts.reduce((sum, row) => sum + row.variance_soum, 0);
  const direction = varianceDirection(variance);

  return (
    <StatStrip label={t("billing.summaryLabel")}>
      <StatTile
        icon={ReceiptText}
        label={t("billing.summaryCharged")}
        note={
          charges.data === undefined
            ? undefined
            : t("billing.summaryChargedNote", { count: charges.data.charge_count })
        }
        tone="accent"
        unit={charges.data === undefined ? undefined : t("billing.amountUnit")}
        value={charges.data === undefined ? "—" : amount(charges.data.charged_soum)}
      />
      <StatTile
        icon={HandCoins}
        label={t("billing.summaryOutstanding")}
        note={
          charges.data === undefined
            ? undefined
            : unpaid.length === 0
              ? t("billing.summaryAllPaid")
              : t("billing.summaryOutstandingNote", { count: unpaid.length })
        }
        tone={charges.data === undefined ? "neutral" : outstanding > 0 ? "danger" : "success"}
        unit={charges.data === undefined ? undefined : t("billing.amountUnit")}
        value={charges.data === undefined ? "—" : amount(outstanding)}
      />
      {/*
       * ⛔ UCH SANOQ QO'SHILMAYDI (D-05): «kamera ko'rmadi» ≠ «ro'yxatsiz
       *    savdo». Katak qiymati — pulga taalluqli turi, qolgan ikkitasi
       *    izohda ALOHIDA.
       */}
      <StatTile
        icon={ScanSearch}
        label={t("billing.anomalyKind.unassigned_occupied")}
        note={
          anomalies.data === undefined
            ? undefined
            : t("billing.summaryAnomaliesNote", {
                closed: anomalies.data.closed_day_count,
                uncovered: anomalies.data.no_coverage_count,
              })
        }
        tone={
          anomalies.data === undefined || anomalies.data.unassigned_count === 0
            ? "neutral"
            : "warning"
        }
        value={anomalies.data === undefined ? "—" : amount(anomalies.data.unassigned_count)}
      />
      <StatTile
        icon={Wallet}
        label={t("billing.summaryShifts")}
        note={
          shifts.data === undefined
            ? undefined
            : closedShifts.length === 0
              ? t("billing.summaryNoShifts")
              : t("billing.summaryShiftsNote", {
                  count: closedShifts.length,
                  state:
                    direction === "short"
                      ? t("billing.varianceShort")
                      : direction === "over"
                        ? t("billing.varianceOver")
                        : t("billing.varianceMatch"),
                })
        }
        tone={
          shifts.data === undefined || closedShifts.length === 0
            ? "neutral"
            : direction === "short"
              ? "danger"
              : direction === "over"
                ? "warning"
                : "success"
        }
        unit={
          shifts.data === undefined || closedShifts.length === 0
            ? undefined
            : t("billing.amountUnit")
        }
        value={
          shifts.data === undefined || closedShifts.length === 0 ? "—" : amount(variance)
        }
      />
    </StatStrip>
  );
}
