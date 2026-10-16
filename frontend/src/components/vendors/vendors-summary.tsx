"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import { HandCoins, ReceiptText, Store, Users } from "lucide-react";

import { debtWindow, periodRange } from "@/components/director/period";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { StatStrip, StatTile } from "@/components/ui/stat-tile";
import { useAuthStore } from "@/lib/auth-store";
import { formatSoum } from "@/lib/format-number";
import { useSetupStatusQuery, useStallMapQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";
import { useReceivablesReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * SOTUVCHILAR XULOSASI (261016) — «kim qarzdor, kim avans bergan».
 *
 * ⛔ QARZ BOSH PANELDAGI «Qarz» KATAGI BILAN AYNI SO'ROVDAN (`debtWindow`,
 *    bugungi davr): ikki ekran bir xil son ko'rsatadi. Jami — serverniki
 *    (`total_outstanding_soum`, avans ayirilgan), sanoq — musbat qoldiqli
 *    sotuvchilar (katakdagi «7 sotuvchida» bilan bir xil qoida).
 *
 * ⛔ Hisobot huquqi (`report_view`) bo'lmasa qarz kataklari YO'Q — so'rov
 *    ham ketmaydi (yangi bozor ustasida platforma admini).
 * =============================================================================
 */

/** Sotuvchi qarzdorlik oynasi — bosh panelning «Bugun» davri bilan bir xil. */
export function useVendorBalances() {
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const roles = useAuthStore().principal?.roles ?? [];
  const allowed = hasPermission(roles, "report_view");
  const todayIso = businessDayIn(timeZone, now);
  const report = useReceivablesReport(
    debtWindow(periodRange("today", todayIso), todayIso),
    { enabled: allowed },
  );
  return { allowed, report };
}

export function VendorsSummary() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const marketId = useAuthStore().principal?.marketId ?? null;

  const setup = useSetupStatusQuery(marketId);
  const map = useStallMapQuery();
  const { allowed, report } = useVendorBalances();

  const total = setup.data?.vendors ?? null;
  const freeStalls =
    map.data === undefined
      ? null
      : map.data.zones.flatMap((zone) => zone.cells).filter((cell) => !cell.has_vendor).length;

  const rows = report.data?.rows ?? [];
  const debtors = rows.filter((row) => row.outstanding_soum > 0).length;
  const advances = rows.filter((row) => row.outstanding_soum < 0);
  const advanceSum = advances.reduce((sum, row) => sum - row.outstanding_soum, 0);

  if (total === null && freeStalls === null && report.data === undefined) return null;

  return (
    <StatStrip label={t("vendors.summaryLabel")}>
      <StatTile
        icon={Users}
        label={t("vendors.summaryTotal")}
        tone="accent"
        unit={t("vendors.unit")}
        value={total ?? "—"}
      />
      {allowed && report.data !== undefined ? (
        <StatTile
          icon={ReceiptText}
          label={t("vendors.summaryDebtors")}
          note={t("vendors.summaryDebtSum", {
            sum: formatSoum(format, Math.max(report.data.total_outstanding_soum, 0), locale),
          })}
          tone={debtors > 0 ? "danger" : "success"}
          unit={t("vendors.unit")}
          value={debtors}
        />
      ) : null}
      {allowed && report.data !== undefined ? (
        <StatTile
          icon={HandCoins}
          label={t("vendors.summaryAdvance")}
          note={formatSoum(format, advanceSum, locale)}
          tone="neutral"
          unit={t("vendors.unit")}
          value={advances.length}
        />
      ) : null}
      {freeStalls === null ? null : (
        <StatTile
          icon={Store}
          label={t("vendors.summaryFreeStalls")}
          note={t("vendors.summaryFreeStallsNote")}
          tone={freeStalls > 0 ? "warning" : "success"}
          unit={t("map.unitStalls")}
          value={freeStalls}
        />
      )}
    </StatStrip>
  );
}
