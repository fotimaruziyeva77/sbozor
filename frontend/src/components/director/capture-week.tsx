"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import { Bar, BarChart, CartesianGrid, Tooltip, XAxis, YAxis } from "recharts";
import type { TooltipContentProps } from "recharts";

import { captureBuckets, niceMax } from "@/components/director/chart-data";
import type { CaptureBuckets } from "@/components/director/chart-data";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  ChartContainer,
  ChartLegend,
  ChartTooltipBox,
} from "@/components/ui/chart";
import type { ChartConfig } from "@/components/ui/chart";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { formatBusinessDay } from "@/lib/format-day";
import { useSetupStatusQuery } from "@/lib/market-queries";
import { hasPermission } from "@/lib/rbac";
import { useCaptureDays } from "@/lib/snapshot-queries";

/*
 * =============================================================================
 * KAMERA KADRLARI — OXIRGI 7 KUN (261016).
 *
 * Savol: «kameralar ishlayaptimi?». Patta hisobi kadrga tayanadi —
 * kadr kelmagan kun hisobsiz qoladi va buni direktor birinchi bo'lib
 * ko'rishi kerak, oy oxirida emas.
 *
 * ⛔ HISOBLAGICHLAR SERVERDAN (`GET /capture-runs?day=`), bu yerda faqat
 *    to'rt guruhga yig'iladi (`captureBuckets`). So'rov kaliti kadr
 *    sahifasi bilan bir xil — ikki ekran bir kun uchun bir xil son.
 *
 * ⛔ FOIZ YO'Q (kadr sahifasidagi §6.3 qoidasi): «96 / 128» ikki
 *    o'tkazib yuborilgan kadrni ko'zdan yashirmaydi, «75%» esa yashiradi.
 *
 * ⛔ Ranglar MA'NO: yaroqli — yashil, sifatsiz — sariq, olinmadi —
 *    qizil (kadr sahifasidagi hisoblagich ohanglari bilan bir xil).
 * =============================================================================
 */

const DAYS = 7;

type CaptureKey = "ok" | "poor" | "lost" | "pending";

const CAPTURE_VIEW: Record<
  CaptureKey,
  {
    labelKey:
      | "director.captureOk"
      | "director.capturePoor"
      | "director.captureLost"
      | "director.capturePending";
    color: string;
  }
> = {
  ok: { labelKey: "director.captureOk", color: "var(--color-success)" },
  poor: { labelKey: "director.capturePoor", color: "var(--color-warning)" },
  lost: { labelKey: "director.captureLost", color: "var(--color-danger)" },
  pending: { labelKey: "director.capturePending", color: "var(--chart-quiet)" },
};

const STACK: readonly CaptureKey[] = ["ok", "poor", "lost", "pending"];

type DayBar = CaptureBuckets & { day: string; label: string; done: number };

export function CaptureWeek() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const principal = useAuthStore().principal;
  const marketId = principal?.marketId ?? null;
  /* ⛔ Huquq tekshiruvi SO'ROVDAN OLDIN — huquqsiz sessiyada 403 yozilmaydi. */
  const allowed = hasPermission(principal?.roles ?? [], "camera_view");
  const setup = useSetupStatusQuery(marketId, { enabled: allowed });

  const todayIso = businessDayIn(timeZone, now);
  const days = Array.from({ length: DAYS }, (_, index) =>
    shiftIsoDay(todayIso, index - (DAYS - 1)),
  );
  const results = useCaptureDays(days, { enabled: allowed });

  /*
   * ⛔ KAMERASIZ BOZORDA KARTA YO'Q: u yerda kadr ATAYIN olinmaydi va
   *    «0 / 0» ni ko'rsatish ogohlantirishni qadrsizlantirardi
   *    (`six-tiles.tsx` dagi kamerasiz rejim qarori).
   */
  if (!allowed || setup.data?.cameras === 0) return null;

  const pending = results.some((result) => result.isLoading);
  const failed = results.some((result) => result.isError);

  const bars: DayBar[] = days.flatMap((day, index) => {
    const summary = results[index]?.data?.summary;
    if (summary === undefined) return [];
    return [
      {
        ...captureBuckets(summary),
        day,
        label: `${day.slice(8, 10)}.${day.slice(5, 7)}`,
        done: summary.done,
      },
    ];
  });

  const today = bars.find((bar) => bar.day === todayIso);
  const planned = bars.some((bar) => bar.planned > 0);
  /* ⛔ O'q «chiroyli qadam» da: 0 · 40 · 80 · 120 · 160, «35 · 70 · 105» emas. */
  const yMax = niceMax(Math.max(0, ...bars.map((bar) => bar.planned)), 4);
  const yTicks = Array.from({ length: 5 }, (_, k) => (yMax * k) / 4);

  const config: ChartConfig = Object.fromEntries(
    STACK.map((key) => [
      key,
      { label: t(CAPTURE_VIEW[key].labelKey), color: CAPTURE_VIEW[key].color },
    ]),
  );

  const renderTooltip = ({ active, payload }: TooltipContentProps) => {
    const bar = payload?.[0]?.payload as DayBar | undefined;
    if (!active || bar === undefined) return null;
    return (
      <ChartTooltipBox
        rows={STACK.filter((key) => key !== "pending" || bar.pending > 0).map(
          (key) => ({
            key,
            label: t(CAPTURE_VIEW[key].labelKey),
            value: String(bar[key]),
            color: CAPTURE_VIEW[key].color,
          }),
        )}
        title={`${formatBusinessDay(format, bar.day, locale)} · ${t("director.capturePair", {
          done: bar.done,
          planned: bar.planned,
        })}`}
      />
    );
  };

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("director.captureTitle")}</h2>
        <p className="dir-tile-sub">{t("director.captureSub", { days: DAYS })}</p>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4">
        {pending && bars.length === 0 ? (
          <Skeleton className="dir-chart-plot-sm" />
        ) : failed && bars.length === 0 ? (
          <p className="dir-tile-note" role="alert">
            {t("director.chartLoadError")}
          </p>
        ) : !planned ? (
          <p className="dir-tile-note">{t("director.captureNoPlan")}</p>
        ) : (
          <>
            {today === undefined || today.planned === 0 ? null : (
              <p className="text-sm">
                <span className="text-text-muted">{t("director.captureToday")} </span>
                <span className="dir-split-value">
                  {t("director.capturePair", {
                    done: today.done,
                    planned: today.planned,
                  })}
                </span>
              </p>
            )}

            <ChartLegend
              items={STACK.map((key) => ({
                key,
                kind: "rect" as const,
                color: CAPTURE_VIEW[key].color,
                label: t(CAPTURE_VIEW[key].labelKey),
              }))}
            />

            <ChartContainer className="dir-chart-plot-sm" config={config}>
              <BarChart data={bars} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="var(--color-border)" vertical={false} />
                <XAxis
                  axisLine={false}
                  dataKey="label"
                  tickLine={false}
                  tickMargin={8}
                />
                <YAxis
                  allowDecimals={false}
                  axisLine={false}
                  domain={[0, yMax]}
                  tickLine={false}
                  ticks={yTicks}
                  width={36}
                />
                <Tooltip
                  content={renderTooltip}
                  cursor={{ fill: "var(--color-surface-muted)" }}
                  isAnimationActive={false}
                />
                {/*
                 * ⛔ Bo'laklar orasidagi 2px — sirt rangidagi chiziq: chegara
                 *    emas, ORALIQ. Ustun eni 24px dan oshmaydi.
                 */}
                {STACK.map((key) => (
                  <Bar
                    dataKey={key}
                    fill={`var(--chart-${key})`}
                    isAnimationActive={false}
                    key={key}
                    maxBarSize={24}
                    stackId="day"
                    stroke="var(--color-surface)"
                    strokeWidth={2}
                  />
                ))}
              </BarChart>
            </ChartContainer>

            {/*
             * ⛔ `sr-only` O'RAMDA, JADVALNING O'ZIDA EMAS: jadval `width: 1px` ni
             *    tan olmaydi va matn kengligiga cho'zilib sahifada gorizontal
             *    aylantirish paydo qilardi (brauzerda o'lchandi).
             */}
            <div className="sr-only">
              <table>
                <caption>{t("director.captureTitle")}</caption>
                <thead>
                  <tr>
                    <th scope="col">{t("director.chartPeriodColumn")}</th>
                    {STACK.map((key) => (
                      <th key={key} scope="col">
                        {t(CAPTURE_VIEW[key].labelKey)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bars.map((bar) => (
                    <tr key={bar.day}>
                      <th scope="row">{formatBusinessDay(format, bar.day, locale)}</th>
                      {STACK.map((key) => (
                        <td key={key}>{bar[key]}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Link className="dir-tile-action mt-auto self-start" href="/snapshots">
              {t("director.captureOpen")} →
            </Link>
          </>
        )}
      </CardContent>
    </Card>
  );
}
