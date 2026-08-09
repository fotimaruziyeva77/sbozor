"use client";

import {
  CircleCheckBig,
  CircleDashed,
  CircleSlash,
  EyeOff,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { parseAsBoolean, useQueryState } from "nuqs";

import { Badge } from "@/components/ui/badge";
import type { BadgeTone } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import type { OccupancyStallItem, OccupancyStatus } from "@/lib/api-types";

/*
 * =============================================================================
 * ZONA (D) — RASTALAR RO'YXATI (§11.7).
 *
 * ⛔ TARTIB SERVERDAN VA U KLIENTDA QAYTA HISOBLANMAYDI. `_DAY_STALLS`
 *    `ORDER BY z.name, s.code_sort, s.id` beradi va `code_sort` DB
 *    tomonda hisoblanadi (2-faza), ya'ni `/stalls` bilan AYNAN bir xil.
 *    Klientdagi `sort()` ikkinchi tartib qoidasi bo'lardi va ikki ekran
 *    bir kun boshqa-boshqa ro'yxat ko'rsatardi.
 *
 * ⛔ BU FAZADA FAQAT BITTA FILTR: «Faqat qamrovsizlarni ko'rsatish»
 *    (`?nocov=1`). Boshqalari 8-fazada (§16.1). Filtr RO'YXATNI
 *    kesadi, XULOSANI emas — hisoblagichlar har doim to'liq kunni
 *    ko'rsatadi.
 *
 * ⛔ HOLAT BADGE'LARI TO'LIQ MATN BILAN va QISQARTIRILMAYDI (§10.4):
 *    «Ko'rilmagani uchun bo'sh» ni «Bo'sh*» ga qisqartirish D-19 ning
 *    butun mazmunini yo'q qilardi. `Badge` hech qachon `truncate`
 *    qilinmaydi — konteyner o'sadi.
 *
 * ⛔ VIRTUALIZATSIYA KUTUBXONASI QO'SHILMAYDI [O'LCHANDI: M-12]: 1000
 *    `<li>` DOM uchun arzon. `content-visibility: auto` ekrandan
 *    tashqaridagi elementni render qilmaydi va `contain-intrinsic-size`
 *    skrollning sakrashiga yo'l qo'ymaydi — nol bog'liqlik, nol JS,
 *    ustiga klaviatura, skrinrider va brauzer qidiruvi ISHLAB TURADI
 *    (virtualizatsiya aynan shularni yo'qotardi).
 *
 *    ⚠ Uslub INLINE (Tailwind ixtiyoriy xossasi), `globals.css` ga
 *      yangi sinf QO'SHILMAYDI: mavjud `.zone-block` plan-xaritaning
 *      400px lik bloklari uchun o'lchangan va uning
 *      `contain-intrinsic-size` i bu yerdagi qatorga to'g'ri kelmaydi.
 *
 * ⛔ PATTA/SUMMA YO'Q — 6-faza (§16.1).
 * =============================================================================
 */

/** `?nocov=1` — ro'yxat filtri. Standart: o'chiq. */
export const NO_COVERAGE_PARAM = "nocov";

/**
 * Qamrovsizlik filtri — URL HOLATI (`day-picker.tsx::useIssuesOnly` naqshi).
 *
 * ⚠ HOLAT SAHIFANIKI: checkbox ham, ro'yxat ham BIR hookdan o'qiydi,
 *   ya'ni ular hech qachon ajralib qola olmaydi.
 */
export function useNoCoverageOnly(): [boolean, (next: boolean) => void] {
  const [value, setValue] = useQueryState(
    NO_COVERAGE_PARAM,
    parseAsBoolean.withDefault(false).withOptions({ history: "push" }),
  );
  return [value, (next: boolean) => void setValue(next ? true : null)];
}

/**
 * Holat -> badge ko'rinishi (§10.4).
 *
 * ⛔ `empty` va `default_empty` TURLI `tone` va TURLI ikonka oladi.
 *    Ikkalasi ham hisob-kitobda «bo'sh» ga olib keladi, lekin ma'nosi
 *    qarama-qarshi: biri O'LCHOV, ikkinchisi O'LCHOVNING YO'QLIGI.
 *    Rang YAGONA signal emas — badge MATNI ham, ikonka ham farq qiladi.
 */
const STATUS_VIEW: Record<
  OccupancyStatus,
  {
    Icon: typeof CircleCheckBig;
    labelKey:
      | "occupancy.occupied"
      | "occupancy.empty"
      | "occupancy.defaultEmpty"
      | "occupancy.noCoverage";
    tone: BadgeTone;
  }
> = {
  occupied: {
    Icon: CircleCheckBig,
    labelKey: "occupancy.occupied",
    tone: "success",
  },
  empty: { Icon: CircleDashed, labelKey: "occupancy.empty", tone: "muted" },
  default_empty: {
    Icon: EyeOff,
    labelKey: "occupancy.defaultEmpty",
    tone: "warning",
  },
  no_coverage: {
    Icon: CircleSlash,
    labelKey: "occupancy.noCoverage",
    tone: "neutral",
  },
};

export function StallStatusBadge({ status }: { status: OccupancyStatus }) {
  const t = useTranslations();
  const view = STATUS_VIEW[status];

  return (
    <Badge className="gap-1" tone={view.tone}>
      <view.Icon aria-hidden="true" className="size-3" />
      {t(view.labelKey)}
    </Badge>
  );
}

/**
 * Ko'rinadigan qatorlar — SOF FUNKSIYA (§S-13).
 *
 * ⚠ FILTR SARALAMAYDI, faqat KESADI: tartib serverdan keladi.
 */
export function visibleStalls(
  items: readonly OccupancyStallItem[],
  noCoverageOnly: boolean,
): readonly OccupancyStallItem[] {
  return noCoverageOnly
    ? items.filter((item) => item.status === "no_coverage")
    : items;
}

export function StallDayList({
  items,
  noCoverageOnly,
  onNoCoverageOnlyChange,
  onOpen,
}: {
  items: readonly OccupancyStallItem[];
  noCoverageOnly: boolean;
  onNoCoverageOnlyChange: (next: boolean) => void;
  onOpen: (item: OccupancyStallItem) => void;
}) {
  const t = useTranslations();
  const visible = visibleStalls(items, noCoverageOnly);

  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{t("occupancy.stallsTitle")}</h2>
        <label className="flex items-center gap-2 text-sm">
          <input
            checked={noCoverageOnly}
            className="size-4 accent-accent"
            onChange={(event) => onNoCoverageOnlyChange(event.target.checked)}
            type="checkbox"
          />
          {t("occupancy.showNoCoverage")}
        </label>
      </CardHeader>

      <CardContent>
        {visible.length === 0 ? (
          /*
           * ⚠ Bu «hammasi yaxshi» degani EMAS, u FILTR natijasi. Matn
           *   fakt aytadi, tabriklamaydi (§12.9 ning E-3 qoidasi).
           */
          <EmptyState
            action={
              <Button
                onClick={() => onNoCoverageOnlyChange(false)}
                size="sm"
                variant="secondary"
              >
                {t("occupancy.clearFilter")}
              </Button>
            }
            description={t("occupancy.emptyNoCoverageHint")}
            title={t("occupancy.emptyNoCoverage")}
          />
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {visible.map((item) => (
              <li
                className="[contain-intrinsic-size:auto_56px] [content-visibility:auto]"
                key={item.stall_id}
              >
                <button
                  className="flex w-full flex-wrap items-center gap-3 px-1 py-3 text-left hover:bg-surface-muted"
                  onClick={() => onOpen(item)}
                  type="button"
                >
                  <span className="min-w-16 text-sm font-semibold">
                    {item.stall_code}
                  </span>
                  <span className="min-w-24 text-sm text-text-muted">
                    {item.zone_name}
                  </span>
                  <StallStatusBadge status={item.status} />
                  {/*
                   * ⛔ SLOT SONI — NISBAT, FOIZ EMAS (§11.4 oxirgi
                   *    qatori): `3 / 7` yaxlitlanmaydi va u kunning
                   *    qancha vaqtida kadr olinganini ham aytadi.
                   */}
                  <span className="font-mono text-xs tabular-nums text-text-muted">
                    {t("occupancy.slotsLine", {
                      occupied: item.occupied_slots,
                      total: item.slots,
                    })}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
