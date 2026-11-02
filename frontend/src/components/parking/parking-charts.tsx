"use client";

import { useId, useState } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";
import {
  Bar,
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
import { hourLabel, peakHour } from "@/components/parking/parking-data";
import { MONEY_COLORS } from "@/components/parking/parking-flow";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartTooltipBox,
} from "@/components/ui/chart";
import type { ChartConfig } from "@/components/ui/chart";
import type { EdgeParkingReport, EdgeParkingReportDay } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";

/*
 * =============================================================================
 * AVTOTURARGOH GRAFIKLARI — kunlar va soatlar (261102).
 *
 * ⛔ BITTA O'Q: kunlik kartada pul va mashina BIR GRAFIKKA chizilmaydi —
 *    ular almashinadigan ikki ko'rinish (`Tushum` / `Mashinalar`). Ikki
 *    o'qli grafik ikki o'lchov orasida yo'q bog'liqlik yasardi.
 *
 * ⛔ KIRISH — aksent ustun, CHIQISH — kulrang chiziq (kontekst). Ikkala
 *    grafikda bir xil: mohiyat rangini sahifa ichida almashtirmaydi.
 *
 * ⛔ Recharts'ning o'z JS animatsiyasi O'CHIQ (`isAnimationActive={false}`):
 *    u reduced-motion sozlamasini bilmaydi.
 *
 * ⛔ jsdom'da `ResponsiveContainer` 0×0 — testlar legenda va jadval
 *    egizagini o'lchaydi, geometriya brauzerda ko'rildi.
 * =============================================================================
 */

const GRID_LINES = 3;

const CARS_COLORS = {
  entries: "var(--color-accent)",
  exits: "var(--color-border-ui)",
} as const;

/** `2026-10-16` -> `16.10`. */
function dayMonth(iso: string): string {
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}`;
}

function ticksFor(max: number): number[] {
  return Array.from({ length: GRID_LINES + 1 }, (_, k) => (max * k) / GRID_LINES);
}

/* -------------------------------------------------------------------------- */
/* Kunlar                                                                     */
/* -------------------------------------------------------------------------- */

const DAILY_VIEWS = ["money", "cars"] as const;
type DailyView = (typeof DAILY_VIEWS)[number];

type DayPoint = EdgeParkingReportDay & { label: string };

export function DailyCard({
  data,
  table,
}: {
  data: EdgeParkingReport;
  /** Jadval egizagi — `<details>` ichida (grafikning matnli ko'rinishi). */
  table: React.ReactNode;
}) {
  const t = useTranslations("parkingReport");
  const format = useFormatter();
  const locale = useLocale();
  const fmt = useParkingFormat();
  const [view, setView] = useState<DailyView>("money");

  const points: DayPoint[] = data.days.map((day) => ({ ...day, label: dayMonth(day.date) }));

  const legend =
    view === "money"
      ? [
          {
            key: "cash",
            kind: "rect" as const,
            color: MONEY_COLORS.cash,
            label: t("money.cash"),
            value: fmt.soum(data.total.cash),
          },
          {
            key: "terminal",
            kind: "rect" as const,
            color: MONEY_COLORS.terminal,
            label: t("money.terminal"),
            value: fmt.soum(data.total.terminal),
          },
        ]
      : [
          {
            key: "entries",
            kind: "rect" as const,
            color: CARS_COLORS.entries,
            label: t("flow.entries"),
            value: fmt.count(data.total.entries),
          },
          {
            key: "exits",
            kind: "line" as const,
            color: CARS_COLORS.exits,
            label: t("flow.exits"),
            value: fmt.count(data.total.exits),
          },
        ];

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="dir-trend-title">{t("daily.title")}</h2>
          <p className="dir-tile-sub">
            {formatBusinessDay(format, data.from_date, locale)} —{" "}
            {formatBusinessDay(format, data.to_date, locale)}
          </p>
        </div>
        {/* ⛔ Tanlangan ko'rinish faqat rang bilan emas — `aria-pressed`. */}
        <div aria-label={t("daily.viewLabel")} className="flex gap-1.5" role="group">
          {DAILY_VIEWS.map((item) => (
            <Button
              aria-pressed={view === item}
              key={item}
              onClick={() => setView(item)}
              size="sm"
              variant={view === item ? "secondary" : "ghost"}
            >
              {t(`daily.${item}`)}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        <ChartLegend items={legend} />
        {view === "money" ? <DailyMoneyChart points={points} /> : <DailyCarsChart points={points} />}
        <details className="park-details">
          <summary>{t("daily.table")}</summary>
          {table}
        </details>
      </CardContent>
    </Card>
  );
}

function useCompactUnits(): CompactUnits {
  const t = useTranslations("director");
  return {
    thousand: t("unitThousand"),
    million: t("unitMillion"),
    billion: t("unitBillion"),
  };
}

function DailyMoneyChart({ points }: { points: readonly DayPoint[] }) {
  const t = useTranslations("parkingReport");
  const format = useFormatter();
  const locale = useLocale();
  const fmt = useParkingFormat();
  const units = useCompactUnits();

  const max = niceMax(Math.max(0, ...points.map((point) => point.total)), GRID_LINES);
  const config: ChartConfig = {
    cash: { label: t("money.cash"), color: MONEY_COLORS.cash },
    terminal: { label: t("money.terminal"), color: MONEY_COLORS.terminal },
  };

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const point = payload?.[0]?.payload as DayPoint | undefined;
    if (!active || point === undefined) return null;
    return (
      <ChartTooltipBox
        rows={[
          {
            key: "cash",
            label: t("money.cash"),
            value: fmt.soum(point.cash),
            color: MONEY_COLORS.cash,
          },
          {
            key: "terminal",
            label: t("money.terminal"),
            value: fmt.soum(point.terminal),
            color: MONEY_COLORS.terminal,
          },
        ]}
        title={`${formatBusinessDay(format, point.date, locale)} · ${fmt.soum(point.total)}`}
      />
    );
  };

  return (
    <ChartContainer className="park-chart-plot" config={config}>
      <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--color-border)" vertical={false} />
        <XAxis axisLine={false} dataKey="label" minTickGap={14} tickLine={false} tickMargin={8} />
        <YAxis
          axisLine={false}
          domain={[0, max]}
          tickFormatter={(value: number) => compactSoum(value, units)}
          tickLine={false}
          ticks={ticksFor(max)}
          width={72}
        />
        <Tooltip
          content={renderTooltip}
          cursor={{ fill: "var(--color-surface-muted)" }}
          isAnimationActive={false}
        />
        {/* ⛔ Bo'laklar orasida 2px sirt oralig'i; yumaloq uch faqat ustki bo'lakda. */}
        <Bar
          dataKey="cash"
          fill="var(--chart-cash)"
          isAnimationActive={false}
          maxBarSize={28}
          stackId="money"
          stroke="var(--color-surface)"
          strokeWidth={2}
        />
        <Bar
          dataKey="terminal"
          fill="var(--chart-terminal)"
          isAnimationActive={false}
          maxBarSize={28}
          radius={[4, 4, 0, 0]}
          stackId="money"
          stroke="var(--color-surface)"
          strokeWidth={2}
        />
      </ComposedChart>
    </ChartContainer>
  );
}

function DailyCarsChart({ points }: { points: readonly DayPoint[] }) {
  const t = useTranslations("parkingReport");
  const format = useFormatter();
  const locale = useLocale();
  const fmt = useParkingFormat();

  const max = niceMax(
    Math.max(0, ...points.map((point) => Math.max(point.entries, point.exits))),
    GRID_LINES,
  );
  const config: ChartConfig = {
    entries: { label: t("flow.entries"), color: CARS_COLORS.entries },
    exits: { label: t("flow.exits"), color: CARS_COLORS.exits },
  };

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const point = payload?.[0]?.payload as DayPoint | undefined;
    if (!active || point === undefined) return null;
    return (
      <ChartTooltipBox
        rows={[
          {
            key: "entries",
            label: t("flow.entries"),
            value: fmt.count(point.entries),
            color: CARS_COLORS.entries,
          },
          {
            key: "exits",
            label: t("flow.exits"),
            value: fmt.count(point.exits),
            color: CARS_COLORS.exits,
          },
        ]}
        title={formatBusinessDay(format, point.date, locale)}
      />
    );
  };

  return (
    <ChartContainer className="park-chart-plot" config={config}>
      <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--color-border)" vertical={false} />
        <XAxis axisLine={false} dataKey="label" minTickGap={14} tickLine={false} tickMargin={8} />
        <YAxis
          allowDecimals={false}
          axisLine={false}
          domain={[0, max]}
          tickLine={false}
          ticks={ticksFor(max)}
          width={40}
        />
        <Tooltip
          content={renderTooltip}
          cursor={{ fill: "var(--color-surface-muted)" }}
          isAnimationActive={false}
        />
        <Bar
          dataKey="entries"
          fill="var(--chart-entries)"
          isAnimationActive={false}
          maxBarSize={28}
          radius={[4, 4, 0, 0]}
        />
        <Line
          activeDot={{
            r: 4,
            fill: "var(--chart-exits)",
            stroke: "var(--color-surface)",
            strokeWidth: 2,
          }}
          dataKey="exits"
          dot={false}
          isAnimationActive={false}
          stroke="var(--chart-exits)"
          strokeWidth={2}
          type="monotone"
        />
      </ComposedChart>
    </ChartContainer>
  );
}

/* -------------------------------------------------------------------------- */
/* Soatlar                                                                    */
/* -------------------------------------------------------------------------- */

type HourPoint = { hour: number; label: string; entries: number; exits: number };

export function HourlyCard({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const captionId = useId();

  const points: HourPoint[] = data.hours.map((row) => ({
    ...row,
    label: String(row.hour).padStart(2, "0"),
  }));
  const peak = peakHour(data.hours);
  const max = niceMax(
    Math.max(0, ...points.map((point) => Math.max(point.entries, point.exits))),
    GRID_LINES,
  );
  const config: ChartConfig = {
    entries: { label: t("flow.entries"), color: CARS_COLORS.entries },
    exits: { label: t("flow.exits"), color: CARS_COLORS.exits },
  };

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const point = payload?.[0]?.payload as HourPoint | undefined;
    if (!active || point === undefined) return null;
    return (
      <ChartTooltipBox
        rows={[
          {
            key: "entries",
            label: t("flow.entries"),
            value: fmt.count(point.entries),
            color: CARS_COLORS.entries,
          },
          {
            key: "exits",
            label: t("flow.exits"),
            value: fmt.count(point.exits),
            color: CARS_COLORS.exits,
          },
        ]}
        title={`${hourLabel(point.hour)}–${hourLabel(point.hour + 1)}`}
      />
    );
  };

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title" id={captionId}>
          {t("hourly.title")}
        </h2>
        <p className="dir-tile-sub">{t("hourly.sub")}</p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        <ChartLegend
          items={[
            { key: "entries", kind: "rect", color: CARS_COLORS.entries, label: t("flow.entries") },
            { key: "exits", kind: "line", color: CARS_COLORS.exits, label: t("flow.exits") },
          ]}
        />
        <ChartContainer className="park-chart-plot" config={config}>
          <ComposedChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="var(--color-border)" vertical={false} />
            <XAxis axisLine={false} dataKey="label" interval={2} tickLine={false} tickMargin={8} />
            <YAxis
              allowDecimals={false}
              axisLine={false}
              domain={[0, max]}
              tickLine={false}
              ticks={ticksFor(max)}
              width={40}
            />
            <Tooltip
              content={renderTooltip}
              cursor={{ fill: "var(--color-surface-muted)" }}
              isAnimationActive={false}
            />
            <Bar
              dataKey="entries"
              fill="var(--chart-entries)"
              isAnimationActive={false}
              maxBarSize={18}
              radius={[4, 4, 0, 0]}
            />
            <Line
              activeDot={{
                r: 4,
                fill: "var(--chart-exits)",
                stroke: "var(--color-surface)",
                strokeWidth: 2,
              }}
              dataKey="exits"
              dot={false}
              isAnimationActive={false}
              stroke="var(--chart-exits)"
              strokeWidth={2}
              type="monotone"
            />
          </ComposedChart>
        </ChartContainer>
        <p className="dir-tile-note">
          {peak === null
            ? t("hourly.noPeak")
            : t("hourly.peak", {
                from: hourLabel(peak.hour),
                to: hourLabel(peak.hour + 1),
                count: peak.entries,
              })}
        </p>

        {/* Jadval egizagi — `sr-only` O'RAMDA (jadvalning o'zida emas, `capture-week` darsi). */}
        <div className="sr-only">
          <table aria-labelledby={captionId}>
            <thead>
              <tr>
                <th scope="col">{t("hourly.colHour")}</th>
                <th scope="col">{t("flow.entries")}</th>
                <th scope="col">{t("flow.exits")}</th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.hour}>
                  <th scope="row">
                    {hourLabel(point.hour)}–{hourLabel(point.hour + 1)}
                  </th>
                  <td>{point.entries}</td>
                  <td>{point.exits}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
