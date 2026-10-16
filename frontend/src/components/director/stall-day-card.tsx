"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import {
  AlertCircle,
  Check,
  CircleDashed,
  Minus,
  Tent,
  TriangleAlert,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Cell, Pie, PieChart, Tooltip } from "recharts";
import type { TooltipContentProps } from "recharts";

import {
  STALL_DAY_ORDER,
  countStallDays,
  expectedStalls,
  zoneDayRows,
} from "@/components/director/chart-data";
import type { StallDayCounts } from "@/components/director/chart-data";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { ChartContainer, ChartTooltipBox } from "@/components/ui/chart";
import type { ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { formatBusinessDay } from "@/lib/format-day";
import { useStallMapQuery } from "@/lib/market-queries";
import type { MapDayState } from "@/lib/map-day-queries";
import { useMapDayStatusQuery } from "@/lib/map-day-queries";

/*
 * =============================================================================
 * BUGUNGI RASTALAR HOLATI — xaritaning bir qarashdagi xulosasi (261016).
 *
 * Savol: «hozir bozorda nechta rasta to'ladi, nechtasi to'lamadi?».
 *
 * ⛔⛔ HOLAT SERVERDAN (`GET /billing/map`) — xarita bo'yaladigan AYNI
 *     javob. Bu yerda faqat SANALADI: ustuvorlik (`_map_day_state`)
 *     serverda va ikkinchi marta yozilmaydi.
 *
 * ⛔ RANGLAR XARITA BILAN BIR XIL (`stall-tone.ts`, 261005 buyurtmachi
 *    qarori): to'langan — yashil, to'lanmagan — qizil, nomuvofiqlik —
 *    sariq. Direktor rangni BIR MARTA o'rganadi. Rang yolg'iz emas: har
 *    holatda ikonka va nom bor (rang ko'rligi va chop etish).
 *
 * ⛔ MAXRAJ — PATTA KUTILGAN RASTALAR (`expectedStalls`): yarmarka,
 *    sotuvchisiz va «bugun hisob yo'q» to'lashi kerak emas.
 * =============================================================================
 */

type StateView = {
  labelKey:
    | "director.stallPaid"
    | "director.stallMismatch"
    | "director.stallDue"
    | "director.stallFair"
    | "director.stallFree"
    | "director.stallNoBilling";
  color: string;
  Icon: LucideIcon;
};

export const STALL_STATE_VIEW: Record<MapDayState, StateView> = {
  paid: { labelKey: "director.stallPaid", color: "var(--color-success)", Icon: Check },
  mismatch: {
    labelKey: "director.stallMismatch",
    color: "var(--color-warning)",
    Icon: TriangleAlert,
  },
  due: { labelKey: "director.stallDue", color: "var(--color-danger)", Icon: AlertCircle },
  fair: { labelKey: "director.stallFair", color: "var(--color-info)", Icon: Tent },
  free: { labelKey: "director.stallFree", color: "var(--color-border-ui)", Icon: Minus },
  no_billing: {
    labelKey: "director.stallNoBilling",
    color: "var(--chart-quiet)",
    Icon: CircleDashed,
  },
};

export function StallDayCard() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const dayLayer = useMapDayStatusQuery();
  const map = useStallMapQuery({ enabled: dayLayer.isEnabled });

  /* ⛔ Huquqsiz sessiyada karta UMUMAN yo'q — so'rov ham ketmagan. */
  if (!dayLayer.isEnabled) return null;

  const status = dayLayer.status;
  const counts = countStallDays(status?.market_active === true ? status.rows : []);
  const expected = expectedStalls(counts);
  const zones =
    map.data === undefined ? [] : zoneDayRows(map.data.zones, dayLayer.byStallId);

  const day = status?.service_date ?? businessDayIn(timeZone, now);

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("director.stallTitle")}</h2>
        <p className="dir-tile-sub">
          {t("director.stallSub", { date: formatBusinessDay(format, day, locale) })}
        </p>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-5">
        {dayLayer.isPending ? (
          <div aria-busy="true" className="flex items-center gap-5">
            <Skeleton className="size-36 rounded-full" />
            <div className="flex flex-1 flex-col gap-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
        ) : dayLayer.isError || status === null ? (
          <p className="dir-tile-note" role="alert">
            {t("director.chartLoadError")}
          </p>
        ) : !status.market_active ? (
          <p className="dir-tile-note">{t("map.marketDraftNotice")}</p>
        ) : (
          <>
            {status.market_open === false ? (
              <p className="dir-tile-note">{t("map.marketClosedNotice")}</p>
            ) : null}

            <div className="dir-stall-overview">
              <StallDonut counts={counts} expected={expected} />
              <StallLegend counts={counts} />
            </div>

            {/*
             * ⛔ Zona kesimi FAQAT ikki va undan ortiq zonada: bitta zonali
             *    bozorda u yuqoridagi donutning aynan takrori bo'lardi.
             */}
            {zones.length >= 2 ? (
              <div className="flex flex-col gap-3">
                <p className="dir-group-label">{t("director.stallByZone")}</p>
                <ul className="flex flex-col gap-3">
                  {zones.map((zone) => (
                    <ZoneRow counts={zone.counts} key={zone.id} name={zone.name} />
                  ))}
                </ul>
              </div>
            ) : null}

            {/* Plan-xarita — xuddi shu holatlar rastalarning o'z joyida. */}
            <Link className="dir-tile-action mt-auto" href="/map">
              {t("director.stallOpenMap")} →
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */

function StallDonut({
  counts,
  expected,
}: {
  counts: StallDayCounts;
  expected: number;
}) {
  const t = useTranslations();

  const data = STALL_DAY_ORDER.filter((state) => counts[state] > 0).map((state) => ({
    state,
    label: t(STALL_STATE_VIEW[state].labelKey),
    value: counts[state],
  }));

  const config: ChartConfig = Object.fromEntries(
    STALL_DAY_ORDER.map((state) => [
      state,
      { label: t(STALL_STATE_VIEW[state].labelKey), color: STALL_STATE_VIEW[state].color },
    ]),
  );

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const entry = payload?.[0]?.payload as
      | { state: MapDayState; label: string; value: number }
      | undefined;
    if (!active || entry === undefined) return null;
    return (
      <ChartTooltipBox
        rows={[
          {
            key: entry.state,
            label: entry.label,
            value: t("director.stallCount", { count: entry.value }),
            color: STALL_STATE_VIEW[entry.state].color,
          },
        ]}
        title={t("director.stallTitle")}
      />
    );
  };

  return (
    <div className="dir-donut-wrap">
      {data.length === 0 ? (
        <div aria-hidden="true" className="dir-donut-empty" />
      ) : (
        <ChartContainer className="size-full" config={config}>
          <PieChart>
            <Tooltip content={renderTooltip} isAnimationActive={false} />
            <Pie
              cornerRadius={3}
              data={data}
              dataKey="value"
              innerRadius="68%"
              isAnimationActive={false}
              nameKey="label"
              outerRadius="100%"
              paddingAngle={data.length > 1 ? 2 : 0}
              startAngle={90}
              endAngle={-270}
              stroke="none"
            >
              {data.map((entry) => (
                <Cell fill={`var(--chart-${entry.state})`} key={entry.state} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
      )}

      {/*
       * ⛔ MARKAZDA «to'ladi / kutilgan» — foiz emas: «18 / 21» ikki
       *    o'tkazib yuborilgan rastani ko'zdan yashirmaydi.
       */}
      <div className="dir-donut-center">
        <p className="dir-donut-value">
          {expected === 0 ? "—" : `${counts.paid} / ${expected}`}
        </p>
        <p className="dir-donut-caption">{t("director.stallPaidCaption")}</p>
      </div>
    </div>
  );
}

function StallLegend({ counts }: { counts: StallDayCounts }) {
  const t = useTranslations();

  return (
    <ul className="dir-stall-legend">
      {STALL_DAY_ORDER.map((state) => {
        const view = STALL_STATE_VIEW[state];
        /* ⛔ Asosiy uchlik NOL bo'lsa ham ko'rinadi — nol ham javob. */
        if (counts[state] === 0 && !["paid", "due", "mismatch"].includes(state)) {
          return null;
        }
        return (
          <li className="dir-stall-legend-item" key={state}>
            <span
              aria-hidden="true"
              className="chart-key-rect"
              style={{ color: view.color }}
            />
            <view.Icon aria-hidden="true" className="size-3.5 text-text-muted" />
            <span className="min-w-0 flex-1 truncate">{t(view.labelKey)}</span>
            <span className="dir-stall-legend-count">{counts[state]}</span>
          </li>
        );
      })}
    </ul>
  );
}

function ZoneRow({ name, counts }: { name: string; counts: StallDayCounts }) {
  const t = useTranslations();
  const expected = expectedStalls(counts);
  const total = STALL_DAY_ORDER.reduce((sum, state) => sum + counts[state], 0);

  return (
    <li className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="min-w-0 truncate">{name}</span>
        <span className="shrink-0 text-xs text-text-muted">
          {expected === 0
            ? t("director.stallCount", { count: total })
            : t("director.stallZonePaid", { paid: counts.paid, expected })}
        </span>
      </div>
      {/*
       * ⛔ Bo'laklar orasida 2px oraliq — chegara chizig'i emas; bo'lak
       *    eni sanoqqa proporsional (`flex-grow`).
       */}
      <div
        aria-label={STALL_DAY_ORDER.filter((state) => counts[state] > 0)
          .map((state) => `${t(STALL_STATE_VIEW[state].labelKey)}: ${counts[state]}`)
          .join(", ")}
        className="dir-split dir-split-thin"
        role="img"
      >
        {STALL_DAY_ORDER.map((state) =>
          counts[state] === 0 ? null : (
            <span
              className="dir-split-part"
              key={state}
              style={{ background: STALL_STATE_VIEW[state].color, flexGrow: counts[state] }}
              title={`${t(STALL_STATE_VIEW[state].labelKey)}: ${counts[state]}`}
            />
          ),
        )}
      </div>
    </li>
  );
}
