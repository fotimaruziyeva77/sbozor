"use client";

import { useId } from "react";
import type { ReactNode } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import {
  ArrowRight,
  Banknote,
  CarFront,
  Clock,
  LogIn,
  LogOut,
  ReceiptText,
  SquareParking,
} from "lucide-react";

import type { Period } from "@/components/director/period";
import { usePanelParkingReport } from "@/components/director/use-panel-parking";
import type { PanelParkingPeriod } from "@/components/director/use-panel-parking";
import { PanelTile } from "@/components/panel/tile";
import { ExitReasonsCard } from "@/components/parking/parking-breakdowns";
import { DailyCard, HourlyCard } from "@/components/parking/parking-charts";
import {
  hourLabel,
  parkingBusinessDay,
  peakHour,
} from "@/components/parking/parking-data";
import { MONEY_COLORS } from "@/components/parking/parking-flow";
import {
  DaysTable,
  PARKING_MAX_PERIOD_DAYS,
  ReportError,
} from "@/components/parking/parking-report";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "@/i18n/navigation";
import type { EdgeParkingReport } from "@/lib/api-types";
import { daysBetweenIsoDays, formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";

/*
 * =============================================================================
 * AVTOTURARGOH BO'LIMI — direktor panelida agentning «Statistika» ekrani
 * (261103, buyurtmachi: «avtoturargoh agentidagi statistikani panelga
 * qo'sh — barcha tushum va hammasi ko'rinsin»).
 *
 * Tartib agent ekrani bilan bir xil: olti katak (Kirdi · Chiqdi · Ichkarida
 * · Tushum naqd/terminal bilan · O'rtacha chek · Odatiy turish), keyin
 * soatlar bo'yicha oqim va chiqish turlari, ko'p kunlik davrda — kunlar
 * bo'yicha tushum. To'liq hisobot (jurnal, kadrlar, Excel) — `/parking`.
 *
 * ⛔ GRAFIKLAR QAYTA YOZILMADI: `/parking` sahifasining kartalari
 *    (`HourlyCard`, `DailyCard`, `ExitReasonsCard`) aynan shu yerda —
 *    ikki ekran bir davr uchun bir xil chizadi.
 *
 * ⛔ DAVR — PANELNIKI (tepadagi tanlagich), avtoturargoh ish kuniga
 *    qisqartirilgan (`use-panel-parking.ts`). Sarlavhadagi sana JAVOBDAN.
 *
 * ⛔ YASHIRINADI: `camera_view` yo'q (so'rov ham ketmaydi), bozorda
 *    avtoturargoh obyekti yo'q yoki ro'yxat hali kelmagan — bo'sh joyda
 *    skeleton miltillamaydi.
 * =============================================================================
 */

/** `/parking` havolasi — davr sig'sa o'sha davr bilan ochiladi. */
function parkingHref(range: PanelParkingPeriod | null): string {
  if (range === null) return "/parking";
  const span = daysBetweenIsoDays(range.from, range.to);
  if (span === null || span + 1 > PARKING_MAX_PERIOD_DAYS) return "/parking";
  const query = new URLSearchParams({ from: range.from, to: range.to });
  return `/parking?${query.toString()}`;
}

export function DirectorParking({ period }: { period: Period }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const titleId = useId();

  const parking = usePanelParkingReport(period);
  const site = parking.site;
  if (site === null) return null;

  const shown = parking.data ?? null;
  const from = shown?.from_date ?? parking.range?.from ?? period.from;
  const to = shown?.to_date ?? parking.range?.to ?? period.to;
  const periodLabel =
    from === to
      ? formatBusinessDay(format, from, locale)
      : `${formatBusinessDay(format, from, locale)} — ${formatBusinessDay(format, to, locale)}`;
  const href = parkingHref(parking.range);

  let body: ReactNode;
  if (parking.range === null) {
    /* Tunda «Bugun»: avtoturargoh kuni hali boshlanmagan — nol emas, sabab. */
    body = (
      <Card className="dir-chart-card hover:translate-y-0">
        <CardContent className="pt-5">
          <p className="dir-tile-note">{t("director.parkingNotStarted")}</p>
        </CardContent>
      </Card>
    );
  } else if (parking.pending) {
    body = (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <div className="dir-park-kpis">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton className="dir-park-skeleton" key={index} />
          ))}
        </div>
      </div>
    );
  } else if (parking.isError || shown === null) {
    body = (
      <div className="flex flex-col items-start gap-3">
        <ReportError error={parking.error} />
        <Button onClick={parking.refetch} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  } else {
    body = <ParkingBody data={shown} href={href} />;
  }

  return (
    /* `park-report` — qayta ishlatilgan kartalar shu blok kengligiga moslashadi. */
    <section aria-labelledby={titleId} className="dir-park park-report">
      <div className="dir-park-head">
        <div className="flex min-w-0 items-start gap-3">
          <SquareParking aria-hidden="true" className="dir-tile-icon" />
          <div className="min-w-0">
            <h2 className="dir-park-title" id={titleId}>
              {t("director.parkingTitle")}
            </h2>
            <p className="dir-tile-sub">
              {site.name} · {periodLabel} · {t("director.parkingDayStart")}
            </p>
          </div>
        </div>
        <Link className="dir-tab" href={href} prefetch={false}>
          {t("director.parkingOpen")}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </div>
      {body}
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* Kataklar va grafiklar                                                      */
/* -------------------------------------------------------------------------- */

function ParkingBody({ data, href }: { data: EdgeParkingReport; href: string }) {
  const t = useTranslations();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const fmt = useParkingFormat();

  const hasEvents = data.total.entries + data.total.exits + data.total.total > 0;
  const multiDay = data.from_date !== data.to_date;
  /* «Hozir» — faqat davr joriy ish kuni bilan tugasa; o'tgan davrda bu so'z yolg'on. */
  const insideNow = data.to_date === parkingBusinessDay(timeZone, now);
  const peak = peakHour(data.hours);
  const median = data.stay.median_minutes;
  const { cash, terminal, total } = data.total;

  return (
    <div className="flex flex-col gap-4">
      <div className="dir-park-kpis">
        <PanelTile
          href={href}
          icon={LogIn}
          label={t("parkingReport.flow.entries")}
          note={
            peak === null
              ? undefined
              : t("parkingReport.flow.peak", {
                  from: hourLabel(peak.hour),
                  to: hourLabel(peak.hour + 1),
                })
          }
          step={0}
        >
          <CarsValue value={data.total.entries} />
        </PanelTile>
        <PanelTile
          href={href}
          icon={LogOut}
          label={t("parkingReport.flow.exits")}
          note={t("director.parkingPaidCars", {
            count: fmt.count(data.paid_sessions),
          })}
          step={1}
        >
          <CarsValue value={data.total.exits} />
        </PanelTile>
        <PanelTile
          href={href}
          icon={CarFront}
          label={
            insideNow
              ? t("director.parkingInsideNow")
              : t("parkingReport.flow.inside")
          }
          note={t("parkingReport.flow.insideNote")}
          step={2}
        >
          <CarsValue value={data.inside} />
        </PanelTile>
        <PanelTile
          href={href}
          icon={Banknote}
          label={t("parkingReport.money.title")}
          note={t("director.parkingSplit", {
            cash: fmt.count(cash),
            terminal: fmt.count(terminal),
          })}
          step={3}
        >
          <div className="flex flex-col gap-2.5">
            <SoumValue value={total} />
            {/* ⛔ Ulush chizig'i faqat pul bo'lganda — nol ulush ma'nosiz. */}
            {total > 0 ? (
              <div aria-hidden="true" className="dir-split dir-split-thin">
                {cash > 0 ? (
                  <span
                    className="dir-split-part"
                    style={{ background: MONEY_COLORS.cash, flexGrow: cash }}
                  />
                ) : null}
                {terminal > 0 ? (
                  <span
                    className="dir-split-part"
                    style={{ background: MONEY_COLORS.terminal, flexGrow: terminal }}
                  />
                ) : null}
              </div>
            ) : null}
          </div>
        </PanelTile>
        <PanelTile
          href={href}
          icon={ReceiptText}
          label={t("parkingReport.money.averageCheck")}
          note={t("director.parkingPayments", { count: data.paid_sessions })}
          step={4}
        >
          {data.average_check_soum === null ? (
            <p className="dir-kpi-value text-text-muted">—</p>
          ) : (
            <SoumValue value={data.average_check_soum} />
          )}
        </PanelTile>
        <PanelTile
          href={href}
          icon={Clock}
          label={t("parkingReport.stay.median")}
          note={
            median === null
              ? t("director.parkingNoStay")
              : t("parkingReport.stay.medianHint")
          }
          step={5}
        >
          <p className={median === null ? "dir-kpi-value text-text-muted" : "dir-kpi-value"}>
            {median === null ? "—" : fmt.duration(median)}
          </p>
        </PanelTile>
      </div>

      {hasEvents ? (
        <>
          <div className="dir-charts-pair">
            <HourlyCard data={data} />
            <ExitReasonsCard data={data} />
          </div>
          {/* Bir kunlik davrda kunlar grafigi bitta ustun bo'lardi — chizilmaydi. */}
          {multiDay ? (
            <DailyCard data={data} table={<DaysTable data={data} />} />
          ) : null}
        </>
      ) : (
        /* Bo'sh davr — NOMLANGAN HOLAT, nollar bilan to'la grafiklar emas. */
        <Card className="dir-chart-card hover:translate-y-0">
          <EmptyState
            className="py-8"
            description={t("parkingReport.emptyHint")}
            title={t("parkingReport.emptyTitle")}
          />
        </Card>
      )}
    </div>
  );
}

/** Mashina soni — katta raqam, kichik birlik («42 mashina»). */
function CarsValue({ value }: { value: number }) {
  const t = useTranslations();
  const fmt = useParkingFormat();
  return (
    <p className="dir-kpi-value">
      {fmt.count(value)}
      <span className="dir-kpi-unit"> {t("director.parkingCarsUnit")}</span>
    </p>
  );
}

/** Pul — `kpi-row.tsx::KpiAmount` bilan bir xil shakl. */
function SoumValue({ value }: { value: number }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  return (
    <p className="dir-kpi-value">
      {formatAmount(format, value, locale)}{" "}
      <span className="dir-kpi-unit">{t("reports.amountUnit")}</span>
    </p>
  );
}
