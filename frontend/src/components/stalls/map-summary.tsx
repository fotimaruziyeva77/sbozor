"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import {
  AlertCircle,
  Ban,
  Check,
  Minus,
  Store,
  TriangleAlert,
  UserX,
  Wrench,
} from "lucide-react";

import type { StallCell } from "@/components/stalls/stall-map-types";
import { StatStrip, StatTile } from "@/components/ui/stat-tile";
import type { StatTone } from "@/components/ui/stat-tile";
import { formatBusinessDay } from "@/lib/format-day";
import { formatSoum } from "@/lib/format-number";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";
import { useStallMapQuery } from "@/lib/market-queries";

/*
 * =============================================================================
 * PLAN-XARITA XULOSASI — «bugun bozorda nima bo'lyapti» (261016).
 *
 * Buyurtmachi: «plan-xarita juda oddiy bo'lib qolgan». Xaritaning ustida
 * endi to'rtta bosiladigan katak turadi: nechta rasta to'ladi, nechtasi
 * to'lamadi (va qancha qoldi), nechtasida nomuvofiqlik, nechtasi
 * sotuvchisiz. Katak bosilsa xaritada FAQAT o'sha rastalar yorqin qoladi,
 * qolganlari xiralashadi — joylashuv saqlanadi.
 *
 * ⛔ SON VA SUMMA SERVERNING O'Z QATORLARIDAN (`/billing/map`), xaritaning
 *    rangi qaysi javobdan bo'lsa AYNAN shundan: katak va xulosa bir-biriga
 *    zid kelmaydi. Summa — rasta darajasidagi bugungi qiymatlar yig'indisi
 *    (`paid_soum`, `remaining_soum`); sotuvchi kesimidagi qarz bu yerda
 *    YO'Q (D-C6).
 *
 * ⛔ TO'LOV QATLAMI BO'LMASA (huquq yo'q / qoralama bozor) — inventar
 *    xulosasi: faol, sotuvchisiz, ta'mirda, yopiq. Yolg'on yashil yo'q.
 * =============================================================================
 */

export type MapFilter =
  | "paid"
  | "due"
  | "mismatch"
  | "free"
  | "active"
  | "noVendor"
  | "maintenance"
  | "closed";

/** Katak tanlangan filtrga mos keladimi. */
export function matchesMapFilter(cell: StallCell, filter: MapFilter | null): boolean {
  switch (filter) {
    case null:
      return true;
    case "paid":
      return cell.dayTone === "paid";
    case "due":
      return cell.dayTone === "debt";
    case "mismatch":
      return cell.dayTone === "mismatch";
    case "free":
      return cell.dayTone === "free";
    case "active":
      return cell.tone === "neutral";
    case "noVendor":
      return !cell.hasVendor;
    case "maintenance":
      return cell.tone === "muted";
    case "closed":
      return cell.tone === "off";
  }
}

type TileView = {
  key: MapFilter;
  labelKey:
    | "map.tilePaid"
    | "map.tileDue"
    | "map.tileMismatch"
    | "map.tileFree"
    | "map.tileActive"
    | "map.tileNoVendor"
    | "map.tileMaintenance"
    | "map.tileClosed";
  icon: typeof Check;
  tone: StatTone;
  count: number;
  note?: string;
};

export function MapSummary({
  filter,
  onFilter,
}: {
  filter: MapFilter | null;
  onFilter: (next: MapFilter | null) => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const mapQuery = useStallMapQuery();
  const dayLayer = useMapDayStatusQuery();

  const cells = (mapQuery.data?.zones ?? []).flatMap((zone) => zone.cells);
  if (cells.length === 0) return null;

  const status = dayLayer.status;
  const payment = status !== null && status.market_active;

  let tiles: TileView[];
  if (payment) {
    const rows = status.rows;
    const count = (state: string) => rows.filter((row) => row.state === state).length;
    const paidSum = rows.reduce((sum, row) => sum + row.paid_soum, 0);
    const remainingSum = rows
      .filter((row) => row.state === "due" || row.state === "mismatch")
      .reduce((sum, row) => sum + (row.remaining_soum ?? 0), 0);
    tiles = [
      {
        key: "paid",
        labelKey: "map.tilePaid",
        icon: Check,
        tone: "success",
        count: count("paid"),
        note: t("map.notePaidSum", { sum: formatSoum(format, paidSum, locale) }),
      },
      {
        key: "due",
        labelKey: "map.tileDue",
        icon: AlertCircle,
        tone: "danger",
        count: count("due"),
        note: t("map.noteRemaining", { sum: formatSoum(format, remainingSum, locale) }),
      },
      {
        key: "mismatch",
        labelKey: "map.tileMismatch",
        icon: TriangleAlert,
        tone: "warning",
        count: count("mismatch"),
        note: t("map.noteMismatch"),
      },
      {
        key: "free",
        labelKey: "map.tileFree",
        icon: Minus,
        tone: "neutral",
        count: count("free"),
        note: t("map.noteFree"),
      },
    ];
  } else {
    tiles = [
      {
        key: "active",
        labelKey: "map.tileActive",
        icon: Store,
        tone: "accent",
        count: cells.filter((cell) => cell.status === "active").length,
      },
      {
        key: "noVendor",
        labelKey: "map.tileNoVendor",
        icon: UserX,
        tone: "neutral",
        count: cells.filter((cell) => !cell.has_vendor).length,
      },
      {
        key: "maintenance",
        labelKey: "map.tileMaintenance",
        icon: Wrench,
        tone: "warning",
        count: cells.filter((cell) => cell.status === "maintenance").length,
      },
      {
        key: "closed",
        labelKey: "map.tileClosed",
        icon: Ban,
        tone: "neutral",
        count: cells.filter((cell) => cell.status === "closed").length,
      },
    ];
  }

  const active = tiles.find((tile) => tile.key === filter);

  return (
    <div className="flex flex-col gap-3">
      {payment ? (
        <p className="text-sm text-text-muted">
          {t("map.stateDate", {
            date: formatBusinessDay(format, status.service_date, locale),
          })}
        </p>
      ) : null}

      <StatStrip label={t("map.summaryLabel")}>
        {tiles.map((tile) => (
          <StatTile
            active={filter === tile.key}
            icon={tile.icon}
            key={tile.key}
            label={t(tile.labelKey)}
            note={tile.note}
            onClick={() => onFilter(filter === tile.key ? null : tile.key)}
            tone={tile.tone}
            unit={t("map.unitStalls")}
            value={tile.count}
          />
        ))}
      </StatStrip>

      {/*
       * ⛔ Filtr yoqilganda buni AYTAMIZ: aks holda xiralashgan xarita
       *    «buzildi» deb o'qilardi.
       */}
      {active === undefined ? null : (
        <p className="flex flex-wrap items-center gap-2 text-sm" role="status">
          <span>{t("map.filterActive", { name: t(active.labelKey) })}</span>
          <button
            className="font-semibold text-accent-text underline-offset-2 hover:underline"
            onClick={() => onFilter(null)}
            type="button"
          >
            {t("map.filterClear")}
          </button>
        </p>
      )}
    </div>
  );
}
