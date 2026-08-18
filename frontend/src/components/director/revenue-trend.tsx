"use client";

import { useState } from "react";
import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount, groupDigits } from "@/lib/format-number";
import { useRevenueReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * TUSHUM TRENDI — `Sbozor Direktor.dc.html` ning grafik kartasi.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-18).
 * Geometriya dizayndan AYNAN: viewBox 1000x240, chap chegara 128, yuqori
 * 16, past 44, o'ng 14; to'rt to'r chizig'i (max*k/3), max = eng katta
 * qiymatning 1.1 barobari.
 *
 * ⛔⛔ TUGAMAGAN DAVR UZUQ CHIZIQ BILAN — DIZAYNNING QAT'IY BANDI.
 *
 * Dizayn 12-bo'limi «to'liq bo'lmagan davr uchun foiz» ni TAQIQLAYDI.
 * Grafikda bu shunday bajariladi: oxirgi nuqta tugamagan bo'lsa u
 * ASOSIY chiziqqa KIRMAYDI — alohida uzuq chiziq bilan ulanadi, nuqtasi
 * bo'sh (ichi fon rangida) va o'qdagi yorlig'i ogohlantirish rangida.
 *
 * ⛔ Nega bu muhim: to'liq chiziq davom etsa, avgustning 18-kunidagi
 *    qiymat butun avgust deb o'qilardi va grafik har oy boshida
 *    «qulash» ko'rsatardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ SERVER 366 KUNDAN KO'PINI BERMAYDI (`report_max_period_days`).
 *    Shuning uchun «12 oy» oralig'i 365 kunlik so'rov bilan olinadi va
 *    oylarga KLIENTDA yig'iladi. Bu ikkinchi haqiqat manbai EMAS:
 *    yig'indi serverning kunlik qatorlaridan chiqadi, qayta
 *    hisoblanmaydi.
 * =============================================================================
 */

/** Dizayn geometriyasi — o'zgartirilmaydi. */
const VIEW_W = 1000;
const VIEW_H = 240;
const PAD_L = 128;
const PAD_T = 16;
const PAD_B = 44;
const PAD_R = 14;

/** To'r chiziqlari soni (dizayn: k = 0..3). */
const GRID_LINES = 3;

type RangeId = "7" | "30" | "12h" | "12o";

const RANGES: { id: RangeId; label: string; days: number }[] = [
  { id: "7", label: "7 kun", days: 7 },
  { id: "30", label: "30 kun", days: 30 },
  { id: "12h", label: "12 hafta", days: 84 },
  { id: "12o", label: "12 oy", days: 365 },
];

type Point = {
  label: string;
  full: string;
  value: number;
  /** Davr tugamagan — uzuq chiziq va bo'sh nuqta. */
  partial: boolean;
};

export function RevenueTrend() {
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

  const points = buildPoints(report.data?.rows ?? [], range, format, locale);

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="dir-trend-title">Tushum trendi</h2>
          <p className="dir-tile-sub">
            {report.data === undefined
              ? RANGES.find((item) => item.id === range)?.label
              : `${formatBusinessDay(format, report.data.from_date, locale)} — ${formatBusinessDay(format, report.data.to_date, locale)}`}
          </p>
        </div>

        {/*
         * ⛔ Oraliq tugmalari — dizaynda `secondary`/`ghost` juftligi va
         *    `aria-pressed`. Tanlanganini FAQAT rang bilan bildirmaydi:
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
              {item.label}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {report.isPending ? (
          <Skeleton className="dir-trend-skeleton" />
        ) : report.isError ? (
          <div className="dir-trend-state" role="alert">
            <p className="dir-trend-state-title">Trend yuklanmadi</p>
            <p className="dir-tile-note">
              Hisobot xizmati javob bermadi. Raqamlar eski emas — ular umuman
              kelmadi.
            </p>
            <div>
              <Button
                onClick={() => void report.refetch()}
                size="sm"
                variant="secondary"
              >
                Qayta urinish
              </Button>
            </div>
          </div>
        ) : points.length === 0 ? (
          <div className="dir-trend-state">
            <EmptyState
              description="Tanlangan oraliqda bironta to'lov qayd etilmagan. Nol ham javob — bu xato emas."
              title="Bu kesimda yozuv yo'q"
            />
          </div>
        ) : (
          <TrendChart
            format={format}
            key={range}
            locale={locale}
            points={points}
          />
        )}
      </CardContent>
    </Card>
  );
}

/* -------------------------------------------------------------------------- */
/* NUQTALAR — serverning KUNLIK qatorlaridan                                  */
/* -------------------------------------------------------------------------- */

type RevenueRow = { business_date: string; collected_soum: number };

function buildPoints(
  rows: readonly RevenueRow[],
  range: RangeId,
  format: ReturnType<typeof useFormatter>,
  locale: string,
): Point[] {
  if (rows.length === 0) return [];

  if (range === "7" || range === "30") {
    /* Kunlik kesim — server qatorlari BEVOSITA nuqta bo'ladi. */
    return rows.map((row) => ({
      label: row.business_date.slice(8),
      full: formatBusinessDay(format, row.business_date, locale),
      value: row.collected_soum,
      partial: false,
    }));
  }

  if (range === "12h") return bucketBy(rows, isoWeekKey, "hafta");
  return bucketBy(rows, (iso) => iso.slice(0, 7), "oy");
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
  unit: string,
): Point[] {
  const order: string[] = [];
  const sums = new Map<string, number>();

  for (const row of rows) {
    const key = keyOf(row.business_date);
    if (!sums.has(key)) order.push(key);
    sums.set(key, (sums.get(key) ?? 0) + row.collected_soum);
  }

  return order.map((key, index) => ({
    label: key.slice(-2),
    full: `${key} · ${unit}`,
    value: sums.get(key) ?? 0,
    partial: index === order.length - 1,
  }));
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
/* SVG — dizayn geometriyasining AYNAN o'zi                                   */
/* -------------------------------------------------------------------------- */

function TrendChart({
  points,
  format,
  locale,
}: {
  points: Point[];
  format: ReturnType<typeof useFormatter>;
  locale: string;
}) {
  const max = Math.max(...points.map((point) => point.value)) * 1.1 || 1;
  const count = points.length;

  const x = (index: number): number =>
    PAD_L +
    (count === 1 ? 0 : (index * (VIEW_W - PAD_L - PAD_R)) / (count - 1));
  const y = (value: number): number =>
    PAD_T + (1 - value / max) * (VIEW_H - PAD_T - PAD_B);

  /* ⛔ Yorliq zichligi dizayndan: 7 kun -> har biri, 30 kun -> har 5-si. */
  const every = count > 20 ? 5 : count > 12 ? 2 : 1;

  const solid = points.filter((point) => !point.partial);
  const line = solid
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"}${x(index).toFixed(1)} ${y(point.value).toFixed(1)}`,
    )
    .join(" ");

  return (
    <div>
      <svg
        aria-label="Tushum trendi"
        className="dir-trend-svg"
        role="img"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      >
        {/* To'r chiziqlari va ularning yorliqlari. */}
        {Array.from({ length: GRID_LINES + 1 }, (_, k) => {
          const value = (max * k) / GRID_LINES;
          const gy = y(value);
          return (
            <g key={k}>
              <line
                stroke="var(--color-border)"
                strokeWidth={1}
                x1={PAD_L}
                x2={VIEW_W - PAD_R}
                y1={gy}
                y2={gy}
              />
              <text
                className="dir-trend-grid-label"
                textAnchor="end"
                x={PAD_L - 12}
                y={gy + 4}
              >
                {groupDigits(Math.round(value / 10_000) * 10_000)}
              </text>
            </g>
          );
        })}

        {/* Asosiy chiziq — chizilib chiqadi (`pathLength=1` + dirDraw). */}
        <path
          className="dir-trend-line"
          d={line}
          fill="none"
          pathLength={1}
          stroke="var(--color-accent)"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2.5}
        />

        {/*
         * ⛔ TUGAMAGAN DAVRGA ULANISH — ALOHIDA UZUQ CHIZIQ. Asosiy
         *    chiziqqa qo'shilsa, u to'liq davr bilan bir xil ko'rinardi.
         */}
        {count > solid.length && solid.length > 0 ? (
          <path
            className="dir-trend-tail"
            d={`M${x(solid.length - 1).toFixed(1)} ${y(points[solid.length - 1].value).toFixed(1)} L${x(solid.length).toFixed(1)} ${y(points[solid.length].value).toFixed(1)}`}
            fill="none"
            stroke="var(--color-text-muted)"
            strokeDasharray="6 6"
            strokeWidth={2.5}
          />
        ) : null}

        {points.map((point, index) => (
          <g key={point.full}>
            <circle
              className="dir-trend-dot"
              cx={x(index)}
              cy={y(point.value)}
              fill={point.partial ? "var(--color-bg)" : "var(--color-accent)"}
              r={count > 14 ? 2.6 : 4}
              stroke={point.partial ? "var(--color-text-muted)" : "none"}
              strokeWidth={1.5}
              style={{ animationDelay: `${Math.round((index / count) * 600)}ms` }}
            >
              {/*
               * ⛔ `<title>` — nuqtaning ANIQ qiymati. Grafik o'zi
               *    taqribiy, aniq son esa hover/fokusda ochiladi va u
               *    skrinriderga ham yetadi.
               */}
              <title>
                {point.full} — {formatAmount(format, point.value, locale)} so
                &apos;m
                {point.partial ? " (davr tugamagan)" : ""}
              </title>
            </circle>
            {index % every === 0 || index === count - 1 ? (
              <text
                className={
                  point.partial ? "dir-trend-axis-partial" : "dir-trend-axis"
                }
                textAnchor="middle"
                x={x(index)}
                y={VIEW_H - 22}
              >
                {point.label}
              </text>
            ) : null}
          </g>
        ))}

        <text
          className="dir-trend-axis"
          textAnchor="end"
          x={PAD_L - 12}
          y={VIEW_H - 22}
        >
          so&apos;m
        </text>
      </svg>

      <div className="dir-trend-foot">
        <span className="dir-tile-note">
          {points.some((point) => point.partial)
            ? "Oxirgi nuqta tugamagan davr — uzuq chiziq bilan va u to'liq davr bilan solishtirilmaydi."
            : "Har nuqta — o'sha davrning yozilgan to'lovlari yig'indisi."}
        </span>
      </div>
    </div>
  );
}
