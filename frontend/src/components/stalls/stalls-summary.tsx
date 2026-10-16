"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { AlertCircle, Store, UserCheck, Wrench } from "lucide-react";

import { StatStrip, StatTile } from "@/components/ui/stat-tile";
import { formatSoum } from "@/lib/format-number";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { useStallMapQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * RASTALAR XULOSASI (261016) — ro'yxatni o'qimasdan javob.
 *
 * Buyurtmachi: «Rastalar bo'limining UI qismini yaxshilash kerak». Ro'yxat
 * 50 tadan yuklanadi va jami sonni bilmaydi; xulosa esa butun bozordan:
 * `/stalls/map` (har rastaning holati va sotuvchisi bor-yo'qligi) va bugungi
 * to'lov holati — `/billing/map` (huquq bo'lsa).
 *
 * ⛔ YANGI SO'ROV YO'Q: ikkala javob ham xarita va rasta kartasi bilan AYNI
 *    kalitdan — ekranlar bir-biriga zid son ko'rsatmaydi.
 * =============================================================================
 */

export function StallsSummary() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const mapQuery = useStallMapQuery();
  const dayLayer = useMapDayStatusQuery();

  const cells = (mapQuery.data?.zones ?? []).flatMap((zone) => zone.cells);
  if (cells.length === 0) return null;

  const active = cells.filter((cell) => cell.status === "active").length;
  const withVendor = cells.filter((cell) => cell.has_vendor).length;
  const resting = cells.filter(
    (cell) => cell.status === "maintenance" || cell.status === "closed",
  ).length;

  const status = dayLayer.status;
  const rows = status !== null && status.market_active ? status.rows : null;
  const unpaid = rows?.filter((row) => row.state === "due" || row.state === "mismatch") ?? [];
  const remaining = unpaid.reduce((sum, row) => sum + (row.remaining_soum ?? 0), 0);

  return (
    <StatStrip label={t("stalls.summaryLabel")}>
      <StatTile
        icon={Store}
        label={t("stalls.summaryTotal")}
        note={t("stalls.summaryActive", { count: active })}
        tone="accent"
        unit={t("map.unitStalls")}
        value={cells.length}
      />
      <StatTile
        icon={UserCheck}
        label={t("stalls.summaryWithVendor")}
        note={t("stalls.summaryNoVendor", { count: cells.length - withVendor })}
        tone="success"
        unit={t("map.unitStalls")}
        value={withVendor}
      />
      <StatTile
        icon={Wrench}
        label={t("stalls.summaryResting")}
        note={t("stalls.summaryRestingNote")}
        tone={resting > 0 ? "warning" : "neutral"}
        unit={t("map.unitStalls")}
        value={resting}
      />
      {rows === null ? null : (
        <StatTile
          icon={AlertCircle}
          label={t("stalls.summaryUnpaid")}
          note={
            unpaid.length === 0
              ? t("stalls.summaryAllPaid")
              : t("map.noteRemaining", { sum: formatSoum(format, remaining, locale) })
          }
          tone={unpaid.length > 0 ? "danger" : "success"}
          unit={t("map.unitStalls")}
          value={unpaid.length}
        />
      )}
    </StatStrip>
  );
}
