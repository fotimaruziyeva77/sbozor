"use client";

import { useState } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Rectangle,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BarShapeProps, TooltipContentProps } from "recharts";

import { compactSoum, niceMax } from "@/components/director/chart-data";
import type { CompactUnits } from "@/components/director/chart-data";
import { usePanelParkingReport } from "@/components/director/use-panel-parking";
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
import { formatAmount, formatSoum } from "@/lib/format-number";
import { useRevenueReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * TUSHUM DINAMIKASI — BITTA SAVOL: «har kuni (hafta, oy) qancha pul
 * tushdi?» (261103 qayta qurildi, buyurtmachi: «tushunarsiz bo'lib qoldi»).
 *
 * ⛔⛔ NEGA QAYTA QURILDI. Kartada maydon + kulrang «Hisoblangan» chizig'i
 *     + uzuq dumlar + avtoturargoh qatlami bir vaqtda turardi — direktor
 *     to'rt xil belgini o'qishi kerak edi va birortasining javobini bir
 *     qarashda ololmasdi. Endi karta FAQAT yig'ilgan pulni ko'rsatadi:
 *
 *       tepada  — davr JAMI va «kuniga o'rtacha» (savolning javobi);
 *       grafik  — ustunlar: «Rastalar» (pastda) + «Avtoturargoh» (ustida);
 *       tooltip — sana, har qism so'mi va «Jami».
 *
 * ⛔ «HISOBLANGAN» (patta hisobi) BU YERDA YO'Q — u «Tekshiruv uchun»
 *    tabida, izohi bilan (`audit-sheet.tsx`). Hisob va yig'imni yonma-yon
 *    solishtirish nazorat savoli, «qancha tushdi» savoli emas.
 *
 * ⛔ TUGAMAGAN HAFTA/OY — OCH RANGLI USTUN, uzuq chiziq emas: oxirgi
 *    ustun hali to'lib bormoqda va to'liq davr bilan solishtirilmasligi
 *    tooltip va pastki izohda aytiladi. Aks holda avgustning 18-kunidagi
 *    qiymat butun avgust deb o'qilardi.
 *
 * ⛔ YIG'INDILAR SERVERDAN: tepadagi jami — `total_collected_soum` +
 *    avtoturargohning `total.total` i; o'rtacha — o'sha jamining kunlar
 *    (hafta, oy) soniga bo'linmasi. Ustunlar serverning KUNLIK qatorlaridan
 *    (to'lovsiz kun ham qator — nol natija), hafta/oyga klientda yig'iladi
 *    (server 366 kundan ko'pini bermaydi, `report_max_period_days`).
 *
 * ⛔ AVTOTURARGOH — ikkinchi qism, faqat bozorda avtoturargoh bo'lsa va
 *    javob kelsa (`use-panel-parking.ts`, seanslarsiz so'rov). So'rov
 *    yiqilsa (eski serverda 92 kundan uzun davr — 422) qism JIMGINA
 *    tushib qoladi, karta sinmaydi. Rangi — aksent va qizil aralashmasi:
 *    `info` (terminal), `success` (Payme), `warning` (Click) panelda band;
 *    juftlik CVD tekshiruvidan o'tgan (yorug' ΔE 9.4, tun ΔE 8.6).
 * =============================================================================
 */

/** To'r chiziqlari soni (0 dan tashqari). */
const GRID_LINES = 3;

/* `niceMax` — `chart-data.ts` da (kamera grafigi ham ishlatadi); trend testi shu yerdan o'qiydi. */
export { niceMax };

type RangeId = "7" | "30" | "12h" | "12o";

/*
 * Yorliqlar i18n KALIT: 7/30 kun direktor davr filtri bilan BIR kalit.
 * `perUnit` — «o'rtacha» ning maxraji: kunlik kesimda kunlar, 12 hafta va
 * 12 oyda — 12 (84 kun = 12 hafta, 365 kun ≈ 12 oy).
 */
const RANGES = [
  { id: "7", labelKey: "director.periodWeek", days: 7, avgKey: "director.trendAvgDay", perUnit: 7 },
  { id: "30", labelKey: "director.periodMonth", days: 30, avgKey: "director.trendAvgDay", perUnit: 30 },
  { id: "12h", labelKey: "director.range12w", days: 84, avgKey: "director.trendAvgWeek", perUnit: 12 },
  { id: "12o", labelKey: "director.range12m", days: 365, avgKey: "director.trendAvgMonth", perUnit: 12 },
] as const satisfies readonly {
  id: RangeId;
  labelKey: string;
  days: number;
  avgKey: string;
  perUnit: number;
}[];

export type TrendPoint = {
  /** O'qdagi qisqa yorliq. */
  label: string;
  /** Ustunning birinchi va oxirgi kuni (kunlik kesimda bir xil). */
  from: string;
  to: string;
  /** Rastalardan yig'ilgan pul. */
  collected: number;
  /** Avtoturargoh tushumi (naqd + terminal); avtoturargohsiz bozorda 0. */
  parking: number;
  /** Hafta/oy tugamagan — och rangli ustun. */
  partial: boolean;
};

const SERIES = {
  collected: { color: "var(--color-accent)" },
  parking: {
    color: "color-mix(in oklch, var(--color-accent) 50%, var(--color-danger))",
  },
} as const;

/** Tugamagan davr ustunining shaffofligi — «hali to'lib bormoqda». */
const PARTIAL_OPACITY = 0.42;

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
  const current = RANGES.find((item) => item.id === range) ?? RANGES[0];
  const from = shiftIsoDay(to, -(current.days - 1));

  const report = useRevenueReport({ from, to });
  const parking = usePanelParkingReport({ from, to });
  /* `null` — avtoturargoh yo'q yoki so'rov yiqildi: ustunlar faqat rastalar. */
  const parkingData = parking.data;
  const withParking = parkingData !== null;
  const points = buildTrendPoints(
    report.data?.rows ?? [],
    range,
    parkingData?.days ?? null,
  );

  const stallsTotal = report.data?.total_collected_soum ?? 0;
  const parkingTotal = parkingData?.total.total ?? 0;
  const total = stallsTotal + parkingTotal;

  return (
    <Card className="dir-chart-card dir-chart-wide hover:translate-y-0">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="dir-trend-title">{t("director.trendTitle")}</h2>
          <p className="dir-tile-sub">
            {report.data === undefined
              ? t(current.labelKey)
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
        {/*
         * ⛔ Avtoturargoh qismi kelguncha ham skeleton: jami va o'q avval
         *    faqat rastalar bo'yicha chizilib, keyin «sakramasin».
         */}
        {report.isPending || parking.pending ? (
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
             * ⛔ JAVOB TEPADA: davr jami va o'rtachasi. Ikki qism bo'lsa
             *    legenda qismlarning o'z yig'indisini ham aytadi — rang
             *    yolg'iz identifikator emas, har bandda nom bor.
             */}
            <div className="dir-trend-summary">
              <p className="dir-kpi-value">
                {formatAmount(format, total, locale)}{" "}
                <span className="dir-kpi-unit">{t("reports.amountUnit")}</span>
              </p>
              <div className="dir-trend-breakdown">
                {withParking ? (
                  <ChartLegend
                    items={[
                      {
                        key: "collected",
                        kind: "rect",
                        color: SERIES.collected.color,
                        label: t("director.trendStalls"),
                        value: formatSoum(format, stallsTotal, locale),
                      },
                      {
                        key: "parking",
                        kind: "rect",
                        color: SERIES.parking.color,
                        label: t("director.trendParking"),
                        value: formatSoum(format, parkingTotal, locale),
                      },
                    ]}
                  />
                ) : null}
                <p className="dir-trend-average">
                  {t(current.avgKey, {
                    sum: formatSoum(format, Math.round(total / current.perUnit), locale),
                  })}
                </p>
              </div>
            </div>
            <TrendChart key={range} points={points} withParking={withParking} />
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
/* USTUNLAR — serverning KUNLIK qatorlaridan                                  */
/* -------------------------------------------------------------------------- */

type RevenueRow = {
  business_date: string;
  collected_soum: number;
};

/** Avtoturargohning bitta kuni — hisobotning `days[]` qatori. */
type ParkingDay = { date: string; total: number };

/** `2026-10-16` -> `16.10`. */
function dayMonth(iso: string): string {
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;
}

/**
 * Ustunlar: rastalar (server qatorlari) + avtoturargoh (shu KUNNING
 * `days[].total` i; yo'q kun — 0).
 *
 * ⛔ O'q RASTALAR qatorlaridan: server davrning har kuni uchun qator
 *    beradi, avtoturargoh esa o'sha kunlarga BIRIKTIRILADI.
 */
export function buildTrendPoints(
  rows: readonly RevenueRow[],
  range: RangeId,
  parkingDays: readonly ParkingDay[] | null = null,
): TrendPoint[] {
  if (rows.length === 0) return [];

  const parkingByDay = new Map(
    (parkingDays ?? []).map((day) => [day.date, day.total]),
  );
  const parkingOf = (iso: string): number => parkingByDay.get(iso) ?? 0;

  if (range === "7" || range === "30") {
    /* Kunlik kesim — server qatorlari BEVOSITA ustun bo'ladi. */
    return rows.map((row) => ({
      label: dayMonth(row.business_date),
      from: row.business_date,
      to: row.business_date,
      collected: row.collected_soum,
      parking: parkingOf(row.business_date),
      partial: false,
    }));
  }

  if (range === "12h") {
    return bucketBy(rows, parkingOf, isoWeekKey, (from) => dayMonth(from));
  }
  return bucketBy(
    rows,
    parkingOf,
    (iso) => iso.slice(0, 7),
    (from) => `${from.slice(5, 7)}.${from.slice(0, 4)}`,
  );
}

/**
 * Kunlik qatorlarni haftaga yoki oyga yig'adi.
 *
 * ⛔ OXIRGI GURUH TUGAMAGAN deb belgilanadi: oraliq kecha bilan tugaydi,
 *    ya'ni joriy hafta/oy hali to'liq emas. Aynan shu bayroq grafikda
 *    och rangli ustun beradi.
 */
function bucketBy(
  rows: readonly RevenueRow[],
  parkingOf: (iso: string) => number,
  keyOf: (iso: string) => string,
  labelOf: (from: string) => string,
): TrendPoint[] {
  const order: string[] = [];
  const buckets = new Map<
    string,
    { from: string; to: string; collected: number; parking: number }
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
        parking: parkingOf(row.business_date),
      });
    } else {
      bucket.to = row.business_date;
      bucket.collected += row.collected_soum;
      bucket.parking += parkingOf(row.business_date);
    }
  }

  return order.map((key, index) => {
    const bucket = buckets.get(key);
    return {
      label: labelOf(bucket?.from ?? key),
      from: bucket?.from ?? key,
      to: bucket?.to ?? key,
      collected: bucket?.collected ?? 0,
      parking: bucket?.parking ?? 0,
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

/* -------------------------------------------------------------------------- */
/* GRAFIK                                                                     */
/* -------------------------------------------------------------------------- */

/*
 * Ustun bo'laklari: yumaloq uch FAQAT ustunning eng ustki bo'lagida
 * (ma'lumot uchi), tugamagan davr — och rangda.
 */

/** Rastalar bo'lagi — ustida avtoturargoh bo'lmasa, ustunning uchi o'zi. */
function stallsSegment(props: BarShapeProps) {
  const point = props.payload as TrendPoint | undefined;
  return (
    <Rectangle
      {...props}
      fillOpacity={point?.partial ? PARTIAL_OPACITY : 1}
      radius={(point?.parking ?? 0) > 0 ? 0 : [4, 4, 0, 0]}
    />
  );
}

/** Avtoturargoh bo'lagi — har doim ustunning uchi. */
function parkingSegment(props: BarShapeProps) {
  const point = props.payload as TrendPoint | undefined;
  return (
    <Rectangle
      {...props}
      fillOpacity={point?.partial ? PARTIAL_OPACITY : 1}
      radius={[4, 4, 0, 0]}
    />
  );
}

function TrendChart({
  points,
  withParking,
}: {
  points: readonly TrendPoint[];
  /** Avtoturargoh qismi chiziladi (bozorda avtoturargoh bor va javob kelgan). */
  withParking: boolean;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const units: CompactUnits = {
    thousand: t("director.unitThousand"),
    million: t("director.unitMillion"),
    billion: t("director.unitBillion"),
  };

  /*
   * ⛔ O'Q YOLG'ON GAPIRMAYDI: ticklar «chiroyli qadam» dan va har biri
   *    o'z chizig'ining HAQIQIY qiymati (`niceMax` testi). Shift — ustunning
   *    to'liq balandligi (rastalar + avtoturargoh).
   */
  const peak = Math.max(
    0,
    ...points.map((point) => point.collected + (withParking ? point.parking : 0)),
  );
  const max = niceMax(peak, GRID_LINES);
  const ticks = Array.from(
    { length: GRID_LINES + 1 },
    (_, k) => (max * k) / GRID_LINES,
  );

  const config: ChartConfig = {
    collected: { label: t("director.trendStalls"), color: SERIES.collected.color },
    ...(withParking
      ? { parking: { label: t("director.trendParking"), color: SERIES.parking.color } }
      : {}),
  };

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
            label: t("director.trendStalls"),
            value: formatSoum(format, point.collected, locale),
            color: SERIES.collected.color,
          },
          ...(withParking
            ? [
                {
                  key: "parking",
                  label: t("director.trendParking"),
                  value: formatSoum(format, point.parking, locale),
                  color: SERIES.parking.color,
                },
              ]
            : []),
        ]}
        title={titleOf(point)}
        total={
          withParking
            ? {
                label: t("director.trendTotal"),
                value: formatSoum(format, point.collected + point.parking, locale),
              }
            : undefined
        }
      />
    );
  };

  /* Ikki bo'lak orasida 2px sirt oralig'i (`stroke`) — chegara chizig'i emas. */
  const gap = withParking ? { stroke: "var(--color-surface)", strokeWidth: 2 } : {};

  return (
    <>
      <ChartContainer className="dir-chart-plot" config={config}>
        <BarChart
          data={points as TrendPoint[]}
          margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid stroke="var(--color-border)" vertical={false} />
          <XAxis
            axisLine={false}
            dataKey="label"
            minTickGap={12}
            tickLine={false}
            tickMargin={8}
          />
          <YAxis
            axisLine={false}
            domain={[0, max]}
            tickFormatter={(value: number) => compactSoum(value, units)}
            tickLine={false}
            ticks={ticks}
            width={64}
          />
          <Tooltip
            content={renderTooltip}
            cursor={{ fill: "var(--color-surface-muted)" }}
            isAnimationActive={false}
          />
          {/*
           * ⛔ Recharts'ning o'z JS animatsiyasi O'CHIQ: u reduced-motion
           *    sozlamasini bilmaydi.
           */}
          <Bar
            dataKey="collected"
            fill="var(--chart-collected)"
            isAnimationActive={false}
            maxBarSize={32}
            shape={stallsSegment}
            stackId="income"
            {...gap}
          />
          {withParking ? (
            <Bar
              dataKey="parking"
              fill="var(--chart-parking)"
              isAnimationActive={false}
              maxBarSize={32}
              shape={parkingSegment}
              stackId="income"
              {...gap}
            />
          ) : null}
        </BarChart>
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
              <th scope="col">{t("director.trendStalls")}</th>
              {withParking ? (
                <>
                  <th scope="col">{t("director.trendParking")}</th>
                  <th scope="col">{t("director.trendTotal")}</th>
                </>
              ) : null}
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
                {withParking ? (
                  <>
                    <td>{formatSoum(format, point.parking, locale)}</td>
                    <td>{formatSoum(format, point.collected + point.parking, locale)}</td>
                  </>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
