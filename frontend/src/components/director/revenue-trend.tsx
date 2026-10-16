"use client";

import { useId, useState } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TooltipContentProps } from "recharts";

import { compactSoum, niceMax } from "@/components/director/chart-data";
import type { CompactUnits } from "@/components/director/chart-data";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartTooltipBox,
} from "@/components/ui/chart";
import type { ChartConfig } from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatSoum } from "@/lib/format-number";
import { useRevenueReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * TUSHUM DINAMIKASI — Recharts maydon grafigi (261016, buyurtmachi:
 * «chartslar ishlat, direktor bittada nima bo'layotganini tushunsin»).
 *
 * ⛔⛔ IKKI SERIYA, BITTA O'Q: «Yig'ilgan» (aksent maydon) va «Hisoblangan»
 *     (kulrang chiziq). Ular bir xil birlikda (so'm) va bitta o'qda —
 *     ikki o'qli grafik ikki seriya orasida mavjud bo'lmagan bog'liqlik
 *     yasardi. Urg'u bitta: yig'ilgan pul; hisoblangan patta — uning
 *     KONTEKSTI, shuning uchun kulrang.
 *
 * ⛔⛔ TUGAMAGAN DAVR UZUQ CHIZIQ BILAN — DIZAYNNING QAT'IY BANDI.
 *     Oxirgi hafta/oy tugamagan bo'lsa u asosiy chiziqqa KIRMAYDI —
 *     alohida uzuq chiziq bilan ulanadi. Aks holda avgustning 18-kunidagi
 *     qiymat butun avgust deb o'qilardi va grafik har oy boshida «qulash»
 *     ko'rsatardi.
 *
 * ⛔ SERVER 366 KUNDAN KO'PINI BERMAYDI (`report_max_period_days`).
 *    «12 oy» oralig'i 365 kunlik so'rov bilan olinadi va oylarga KLIENTDA
 *    yig'iladi. Bu ikkinchi haqiqat manbai EMAS: yig'indi serverning
 *    kunlik qatorlaridan chiqadi, qayta hisoblanmaydi.
 *
 * ⛔ Server davrning HAR kuni uchun qator beradi (to'lovsiz kun ham,
 *    `report_repo._REVENUE_BY_DAY` — `generate_series`): nol — natija,
 *    grafikdagi «chuqurlik» haqiqiy.
 * =============================================================================
 */

/** To'r chiziqlari soni (0 dan tashqari). */
const GRID_LINES = 3;

/* `niceMax` — `chart-data.ts` da (kamera grafigi ham ishlatadi); trend testi shu yerdan o'qiydi. */
export { niceMax };

type RangeId = "7" | "30" | "12h" | "12o";

/* Yorliqlar i18n KALIT: 7/30 kun direktor davr filtri bilan BIR kalit. */
const RANGES = [
  { id: "7", labelKey: "director.periodWeek", days: 7 },
  { id: "30", labelKey: "director.periodMonth", days: 30 },
  { id: "12h", labelKey: "director.range12w", days: 84 },
  { id: "12o", labelKey: "director.range12m", days: 365 },
] as const satisfies readonly { id: RangeId; labelKey: string; days: number }[];

export type TrendPoint = {
  /** O'qdagi qisqa yorliq. */
  label: string;
  /** Nuqtaning birinchi va oxirgi kuni (kunlik kesimda bir xil). */
  from: string;
  to: string;
  collected: number;
  charged: number;
  /** Davr tugamagan — uzuq chiziq. */
  partial: boolean;
};

const SERIES = {
  collected: { color: "var(--color-accent)" },
  charged: { color: "var(--color-border-ui)" },
} as const;

export function RevenueTrend() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const [range, setRange] = useState<RangeId>("7");

  const todayIso = businessDayIn(timeZone, now);
  /* ⛔ Kecha bilan tugaydi: bugungi kun hali yopilmagan. */
  const to = shiftIsoDay(todayIso, -1);
  const days = RANGES.find((item) => item.id === range)?.days ?? 7;
  const from = shiftIsoDay(to, -(days - 1));

  const report = useRevenueReport({ from, to });
  const points = buildTrendPoints(report.data?.rows ?? [], range);

  return (
    <Card className="dir-chart-card dir-chart-wide hover:translate-y-0">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="dir-trend-title">{t("director.trendTitle")}</h2>
          <p className="dir-tile-sub">
            {report.data === undefined
              ? t(
                  RANGES.find((item) => item.id === range)?.labelKey ??
                    "director.periodWeek",
                )
              : `${formatBusinessDay(format, report.data.from_date, locale)} — ${formatBusinessDay(format, report.data.to_date, locale)}`}
          </p>
        </div>

        {/*
         * ⛔ Tanlangan oraliq FAQAT rang bilan bildirilmaydi:
         *    `aria-pressed` skrinriderga ham aytadi.
         */}
        <div className="flex flex-wrap gap-1.5">
          {RANGES.map((item) => (
            <Button
              aria-pressed={range === item.id}
              key={item.id}
              onClick={() => setRange(item.id)}
              size="sm"
              variant={range === item.id ? "secondary" : "ghost"}
            >
              {t(item.labelKey)}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col">
        {report.isPending ? (
          <Skeleton className="dir-trend-skeleton" />
        ) : report.isError ? (
          <div className="dir-trend-state" role="alert">
            <p className="dir-trend-state-title">
              {t("director.trendErrorTitle")}
            </p>
            <p className="dir-tile-note">{t("director.trendErrorNote")}</p>
            <div>
              <Button
                onClick={() => void report.refetch()}
                size="sm"
                variant="secondary"
              >
                {t("common.retry")}
              </Button>
            </div>
          </div>
        ) : points.length === 0 ? (
          <div className="dir-trend-state">
            <EmptyState
              description={t("director.trendEmptyNote")}
              title={t("director.trendEmptyTitle")}
            />
          </div>
        ) : (
          <div className="flex flex-1 flex-col gap-3">
            {/*
             * ⛔ LEGENDA IKKI SERIYADA MAJBURIY va unda davr YIG'INDISI:
             *    yig'indi SERVERDAN (`total_*_soum`), nuqtalarni qo'shib
             *    chiqarilmaydi.
             */}
            <ChartLegend
              items={[
                {
                  key: "collected",
                  kind: "rect",
                  color: SERIES.collected.color,
                  label: t("director.collected"),
                  value: formatSoum(
                    format,
                    report.data?.total_collected_soum ?? 0,
                    locale,
                  ),
                },
                {
                  key: "charged",
                  kind: "line",
                  color: SERIES.charged.color,
                  label: t("director.charged"),
                  value: formatSoum(
                    format,
                    report.data?.total_charged_soum ?? 0,
                    locale,
                  ),
                },
              ]}
            />
            <TrendChart key={range} points={points} />
            <p className="dir-tile-note">
              {points.some((point) => point.partial)
                ? t("director.trendFootPartial")
                : t("director.trendFootFull")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* NUQTALAR — serverning KUNLIK qatorlaridan                                  */
/* -------------------------------------------------------------------------- */

type RevenueRow = {
  business_date: string;
  collected_soum: number;
  charged_soum: number;
};

/** `2026-10-16` -> `16.10`. */
function dayMonth(iso: string): string {
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;
}

export function buildTrendPoints(
  rows: readonly RevenueRow[],
  range: RangeId,
): TrendPoint[] {
  if (rows.length === 0) return [];

  if (range === "7" || range === "30") {
    /* Kunlik kesim — server qatorlari BEVOSITA nuqta bo'ladi. */
    return rows.map((row) => ({
      label: dayMonth(row.business_date),
      from: row.business_date,
      to: row.business_date,
      collected: row.collected_soum,
      charged: row.charged_soum,
      partial: false,
    }));
  }

  if (range === "12h") return bucketBy(rows, isoWeekKey, (from) => dayMonth(from));
  return bucketBy(
    rows,
    (iso) => iso.slice(0, 7),
    (from) => `${from.slice(5, 7)}.${from.slice(0, 4)}`,
  );
}

/**
 * Kunlik qatorlarni haftaga yoki oyga yig'adi.
 *
 * ⛔ OXIRGI GURUH TUGAMAGAN deb belgilanadi: oraliq kecha bilan tugaydi,
 *    ya'ni joriy hafta/oy hali to'liq emas. Aynan shu bayroq grafikda
 *    uzuq chiziq beradi.
 */
function bucketBy(
  rows: readonly RevenueRow[],
  keyOf: (iso: string) => string,
  labelOf: (from: string) => string,
): TrendPoint[] {
  const order: string[] = [];
  const buckets = new Map<
    string,
    { from: string; to: string; collected: number; charged: number }
  >();

  for (const row of rows) {
    const key = keyOf(row.business_date);
    const bucket = buckets.get(key);
    if (bucket === undefined) {
      order.push(key);
      buckets.set(key, {
        from: row.business_date,
        to: row.business_date,
        collected: row.collected_soum,
        charged: row.charged_soum,
      });
    } else {
      bucket.to = row.business_date;
      bucket.collected += row.collected_soum;
      bucket.charged += row.charged_soum;
    }
  }

  return order.map((key, index) => {
    const bucket = buckets.get(key);
    return {
      label: labelOf(bucket?.from ?? key),
      from: bucket?.from ?? key,
      to: bucket?.to ?? key,
      collected: bucket?.collected ?? 0,
      charged: bucket?.charged ?? 0,
      partial: index === order.length - 1,
    };
  });
}

/** ISO hafta kaliti — `2026-W33` shaklida. */
function isoWeekKey(iso: string): string {
  const date = new Date(`${iso}T12:00:00Z`);
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(
    ((date.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7,
  );
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

/**
 * Chiziladigan qatorlar: to'liq qism va tugamagan «dum».
 *
 * ⛔ Dum OXIRGI IKKI nuqtadan iborat — u to'liq chiziqning uchidan
 *    tugamagan nuqtaga ulanadi. To'liq qismda tugamagan nuqta `null`:
 *    Recharts `null` da chiziqni uzadi.
 */
export function trendSeries(points: readonly TrendPoint[]) {
  const last = points.length - 1;
  const hasTail = last >= 1 && points[last]?.partial === true;

  return points.map((point, index) => {
    const inSolid = !hasTail || index < last;
    const inTail = hasTail && index >= last - 1;
    return {
      ...point,
      collectedSolid: inSolid ? point.collected : null,
      chargedSolid: inSolid ? point.charged : null,
      collectedTail: inTail ? point.collected : null,
      chargedTail: inTail ? point.charged : null,
    };
  });
}

/* -------------------------------------------------------------------------- */
/* GRAFIK                                                                     */
/* -------------------------------------------------------------------------- */

function TrendChart({ points }: { points: readonly TrendPoint[] }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  /* Gradient identifikatori — bir sahifada ikki grafik bo'lsa TO'QNASHMASIN. */
  const gradientId = `trend-fill-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  const units: CompactUnits = {
    thousand: t("director.unitThousand"),
    million: t("director.unitMillion"),
    billion: t("director.unitBillion"),
  };

  /*
   * ⛔ O'Q YOLG'ON GAPIRMAYDI: ticklar «chiroyli qadam» dan va har biri
   *    o'z chizig'ining HAQIQIY qiymati (`niceMax` testi).
   */
  const peak = Math.max(
    0,
    ...points.map((point) => Math.max(point.collected, point.charged)),
  );
  const max = niceMax(peak, GRID_LINES);
  const ticks = Array.from(
    { length: GRID_LINES + 1 },
    (_, k) => (max * k) / GRID_LINES,
  );

  const config: ChartConfig = {
    collected: { label: t("director.collected"), color: SERIES.collected.color },
    charged: { label: t("director.charged"), color: SERIES.charged.color },
  };

  const data = trendSeries(points);

  const titleOf = (point: TrendPoint): string =>
    point.from === point.to
      ? formatBusinessDay(format, point.from, locale)
      : `${formatBusinessDay(format, point.from, locale)} — ${formatBusinessDay(format, point.to, locale)}`;

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const point = payload?.[0]?.payload as TrendPoint | undefined;
    if (!active || point === undefined) return null;
    return (
      <ChartTooltipBox
        note={point.partial ? t("director.trendPartialTip") : undefined}
        rows={[
          {
            key: "collected",
            label: t("director.collected"),
            value: formatSoum(format, point.collected, locale),
            color: SERIES.collected.color,
            kind: point.partial ? "dashed" : "line",
          },
          {
            key: "charged",
            label: t("director.charged"),
            value: formatSoum(format, point.charged, locale),
            color: SERIES.charged.color,
            kind: point.partial ? "dashed" : "line",
          },
        ]}
        title={titleOf(point)}
      />
    );
  };

  return (
    <>
      <ChartContainer className="dir-chart-plot" config={config}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-collected)" stopOpacity={0.22} />
              <stop offset="100%" stopColor="var(--chart-collected)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="label"
            minTickGap={18}
            tickLine={false}
            tickMargin={8}
          />
          <YAxis
            axisLine={false}
            domain={[0, max]}
            tickFormatter={(value: number) => compactSoum(value, units)}
            tickLine={false}
            ticks={ticks}
            width={72}
          />
          <Tooltip
            content={renderTooltip}
            cursor={{ stroke: "var(--color-border-ui)", strokeWidth: 1 }}
            isAnimationActive={false}
          />

          {/* Kontekst seriyasi OLDIN — urg'u seriyasi uning ustida chiziladi. */}
          <Line
            activeDot={{ r: 4, fill: "var(--chart-charged)", stroke: "var(--color-surface)", strokeWidth: 2 }}
            className="dir-trend-line"
            connectNulls={false}
            dataKey="chargedSolid"
            dot={false}
            isAnimationActive={false}
            pathLength={1}
            stroke="var(--chart-charged)"
            strokeWidth={2}
            type="monotone"
          />
          <Line
            activeDot={false}
            connectNulls={false}
            dataKey="chargedTail"
            dot={false}
            isAnimationActive={false}
            stroke="var(--chart-charged)"
            strokeDasharray="5 5"
            strokeWidth={2}
            type="monotone"
          />
          {/*
           * ⛔ Chiziladigan chiziq — FAQAT to'liq qism (`.dir-trend-line`,
           *    `dirDraw`). Recharts'ning o'z JS animatsiyasi o'chiq: u
           *    reduced-motion sozlamasini bilmaydi, CSS kadri esa biladi.
           */}
          <Area
            activeDot={{ r: 4, fill: "var(--chart-collected)", stroke: "var(--color-surface)", strokeWidth: 2 }}
            className="dir-trend-line"
            connectNulls={false}
            dataKey="collectedSolid"
            fill={`url(#${gradientId})`}
            isAnimationActive={false}
            pathLength={1}
            stroke="var(--chart-collected)"
            strokeWidth={2}
            type="monotone"
          />
          <Line
            activeDot={false}
            connectNulls={false}
            dataKey="collectedTail"
            dot={false}
            isAnimationActive={false}
            stroke="var(--chart-collected)"
            strokeDasharray="5 5"
            strokeWidth={2}
            type="monotone"
          />
        </ComposedChart>
      </ChartContainer>

      {/*
       * ⛔ JADVAL — GRAFIKNING EGIZAGI: tooltip qiymatni yolg'iz
       *    ko'rsatadigan joy bo'lmasligi kerak. Skrinrider shu jadvalni
       *    o'qiydi.
       *
       * ⛔ `sr-only` O'RAMDA, JADVALNING O'ZIDA EMAS: jadval `width: 1px` ni
       *    tan olmaydi va matn kengligiga cho'zilib sahifada gorizontal
       *    aylantirish paydo qilardi (brauzerda o'lchandi).
       */}
      <div className="sr-only">
        <table>
          <caption>{t("director.trendTitle")}</caption>
          <thead>
            <tr>
              <th scope="col">{t("director.chartPeriodColumn")}</th>
              <th scope="col">{t("director.collected")}</th>
              <th scope="col">{t("director.charged")}</th>
            </tr>
          </thead>
          <tbody>
            {points.map((point) => (
              <tr key={point.from}>
                <th scope="row">
                  {titleOf(point)}
                  {point.partial ? ` (${t("director.trendPartialTip")})` : ""}
                </th>
                <td>{formatSoum(format, point.collected, locale)}</td>
                <td>{formatSoum(format, point.charged, locale)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
