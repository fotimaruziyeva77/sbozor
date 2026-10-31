"use client";

import { useId } from "react";
import { Banknote, LogIn, LogOut, Ticket } from "lucide-react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import { parseAsString, useQueryStates } from "nuqs";

import { ParkingExportButton } from "@/components/parking/parking-export-button";
import {
  businessDayIn,
  isValidIsoDay,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { StatStrip, StatTile } from "@/components/ui/stat-tile";
import { ApiError } from "@/lib/api-client";
import type {
  EdgeParkingReport,
  EdgeParkingReportDay,
  EdgeSite,
} from "@/lib/api-types";
import {
  useEdgeParkingReportQuery,
  useEdgeSitesQuery,
} from "@/lib/edge-site-queries";
import type { ParkingReportPeriod } from "@/lib/edge-site-queries";
import { daysBetweenIsoDays, formatBusinessDay } from "@/lib/format-day";
import { formatAmount, formatSoum } from "@/lib/format-number";
import { reportErrorView } from "@/lib/report-errors";

/*
 * =============================================================================
 * AVTOTURARGOH DAVR HISOBOTI — `/parking` sahifasining ish maydoni.
 *
 * Direktorning savoli bitta: «shu kunlar orasida qancha mashina kirdi,
 * chiqdi va qancha pul tushdi?». Javob to'rt katak + kunlar jadvali;
 * mashinalar ro'yxati EKRANGA CHIZILMAYDI — u Excel faylning ikkinchi
 * varag'ida (oyiga minglab qator telefonda o'qilmaydi).
 *
 * ⛔ DAVR «MAKSIMUM KECHA» EMAS, BUGUNGACHA — `reports/period-picker.tsx`
 *    dan ATAYIN FARQ. U yerdagi chegara `daily_charges` D+1 yopilishidan
 *    (§1.2 qoida 1); avtoturargoh hodisalari esa real vaqtda keladi va
 *    «bugun qancha kirdi?» ma'noli savol. Shuning uchun o'sha tanlagich
 *    QAYTA ISHLATILMADI — unga `maxDate` propi qo'shish o'sha
 *    muzokarasiz chegarani chaqiruvchining tanloviga aylantirardi.
 *
 * ⛔ YIG'INDI KLIENTDA HISOBLANMAYDI: `total` serverdan (`05-14` darsi —
 *    klientdagi qayta hisob ikkinchi javob bo'lib chiqadi).
 *
 * ⛔ EKRANDAGI DAVR JAVOBDAN (`from_date`/`to_date`), URL holatidan emas.
 *
 * URL: `?site=&from=&to=` (`nuqs`) — havola ulashiladi; standart davr
 * (joriy oy boshidan bugungacha) uchun parametr YOZILMAYDI, toza havola
 * ertasiga ham o'sha kungi standartni beradi.
 * =============================================================================
 */

const SITE_PARAM = "site";
const FROM_PARAM = "from";
const TO_PARAM = "to";

/** Serverdagi `parking_report.MAX_PERIOD_DAYS` bilan AYNAN teng — bir chorak. */
export const PARKING_MAX_PERIOD_DAYS = 92;

export const PARKING_PRESETS = ["thisMonth", "lastMonth", "lastWeek"] as const;
export type ParkingPreset = (typeof PARKING_PRESETS)[number];

function monthStartIso(iso: string): string {
  return `${iso.slice(0, 7)}-01`;
}

export function parkingPresetRange(
  preset: ParkingPreset,
  todayIso: string,
): ParkingReportPeriod {
  switch (preset) {
    case "lastMonth": {
      const end = shiftIsoDay(monthStartIso(todayIso), -1);
      return { from: monthStartIso(end), to: end };
    }
    case "lastWeek":
      return { from: shiftIsoDay(todayIso, -6), to: todayIso };
    default:
      return { from: monthStartIso(todayIso), to: todayIso };
  }
}

/**
 * URL'dan kelgan davrni NORMALLASHTIRADI: yaroqsiz shakl, teskari oraliq,
 * kelajakdagi kun yoki 92 kundan uzun davr -> standart (joriy oy).
 * Eskirgan xatcho'pdan kelgan direktorga «URL noto'g'ri» deyish foydali
 * qadam bermaydi — jimgina standart ko'rsatiladi.
 */
export function normalizeParkingPeriod(
  rawFrom: string,
  rawTo: string,
  todayIso: string,
): ParkingReportPeriod {
  const fallback = parkingPresetRange("thisMonth", todayIso);
  if (!isValidIsoDay(rawFrom) || !isValidIsoDay(rawTo)) return fallback;
  if (rawFrom > rawTo || rawTo > todayIso) return fallback;
  const span = daysBetweenIsoDays(rawFrom, rawTo);
  if (span === null || span + 1 > PARKING_MAX_PERIOD_DAYS) return fallback;
  return { from: rawFrom, to: rawTo };
}

export function parkingPresetOf(
  period: ParkingReportPeriod,
  todayIso: string,
): ParkingPreset | null {
  for (const preset of PARKING_PRESETS) {
    const range = parkingPresetRange(preset, todayIso);
    if (range.from === period.from && range.to === period.to) return preset;
  }
  return null;
}

export function ParkingReportWorkspace() {
  const t = useTranslations();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const todayIso = businessDayIn(timeZone, now);

  const [raw, setRaw] = useQueryStates(
    {
      [SITE_PARAM]: parseAsString.withDefault(""),
      [FROM_PARAM]: parseAsString.withDefault(""),
      [TO_PARAM]: parseAsString.withDefault(""),
    },
    { history: "push" },
  );

  const period = normalizeParkingPeriod(raw.from, raw.to, todayIso);
  const fallback = parkingPresetRange("thisMonth", todayIso);

  function writePeriod(next: ParkingReportPeriod): void {
    const isDefault = next.from === fallback.from && next.to === fallback.to;
    void setRaw(
      isDefault
        ? { [FROM_PARAM]: null, [TO_PARAM]: null }
        : { [FROM_PARAM]: next.from, [TO_PARAM]: next.to },
    );
  }

  const sites = useEdgeSitesQuery();
  /* Faqat `parking` turidagi obyektlar — bittasi bo'lsa avtomatik tanlanadi. */
  const parkingSites: EdgeSite[] = (sites.data?.items ?? []).filter(
    (site) => site.kind === "parking",
  );
  const selectedSite =
    parkingSites.find((site) => site.id === raw.site) ?? parkingSites[0] ?? null;

  const report = useEdgeParkingReportQuery(selectedSite?.id ?? "", period, {
    enabled: selectedSite !== null,
  });

  if (sites.isPending) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4" role="status">
        <span className="sr-only">{t("common.loading")}</span>
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-24" />
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (sites.isError) {
    return (
      <div
        className="flex flex-col items-start gap-3 rounded-md bg-danger/10 p-4 text-danger-text"
        role="alert"
      >
        <p className="text-sm font-semibold">{t("errors.loadFailedTitle")}</p>
        <p className="text-sm">{t("errors.loadFailedBody")}</p>
        <Button onClick={() => void sites.refetch()} size="sm" variant="secondary">
          {t("common.retry")}
        </Button>
      </div>
    );
  }

  if (selectedSite === null) {
    /* ⛔ Bo'sh holat NOMLANADI va keyingi qadamni aytadi (§14.7). */
    return (
      <EmptyState
        description={t("parkingReport.noSitesHint")}
        title={t("parkingReport.noSitesTitle")}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PeriodControls
        onPeriod={writePeriod}
        onSite={(siteId) => void setRaw({ [SITE_PARAM]: siteId })}
        period={period}
        selectedSite={selectedSite}
        sites={parkingSites}
        todayIso={todayIso}
      />

      {report.isPending ? (
        <div aria-busy="true" className="flex flex-col gap-4" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
          <Skeleton className="h-64" />
        </div>
      ) : null}

      {report.isError ? <ReportError error={report.error} /> : null}

      {report.data !== undefined ? (
        <ReportBody
          data={report.data}
          period={period}
          siteId={selectedSite.id}
        />
      ) : null}
    </div>
  );
}

/* --- Boshqaruv: obyekt + davr -------------------------------------------- */

function PeriodControls({
  sites,
  selectedSite,
  period,
  todayIso,
  onSite,
  onPeriod,
}: {
  sites: EdgeSite[];
  selectedSite: EdgeSite;
  period: ParkingReportPeriod;
  todayIso: string;
  onSite: (siteId: string) => void;
  onPeriod: (next: ParkingReportPeriod) => void;
}) {
  const t = useTranslations();
  const siteFieldId = useId();
  const fromId = useId();
  const toId = useId();
  const activePreset = parkingPresetOf(period, todayIso);

  function setFrom(next: string): void {
    /* Ikkinchi qatlam: `max` atributi DevTools bilan olinadi. */
    if (isValidIsoDay(next) && next <= todayIso) onPeriod({ from: next, to: period.to });
  }

  function setTo(next: string): void {
    if (isValidIsoDay(next) && next <= todayIso) onPeriod({ from: period.from, to: next });
  }

  const dateInputClass =
    "h-10 rounded-sm border border-border-ui bg-surface px-3 text-sm text-text outline-none transition-colors focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25";

  return (
    <div className="flex flex-col gap-4">
      {sites.length > 1 ? (
        <div className="flex flex-col gap-1">
          <label className="text-sm text-text-muted" htmlFor={siteFieldId}>
            {t("parkingReport.siteLabel")}
          </label>
          <Select
            className="w-auto"
            id={siteFieldId}
            onChange={(event) => onSite(event.target.value)}
            value={selectedSite.id}
          >
            {/* D-16: obyekt nomi DB kontenti — tarjima qilinmaydi. */}
            {sites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name}
              </option>
            ))}
          </Select>
        </div>
      ) : (
        <p className="text-sm text-text-muted">
          {t("parkingReport.siteLabel")}:{" "}
          <span className="font-semibold text-text">{selectedSite.name}</span>
        </p>
      )}

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-text">
          {t("parkingReport.periodLabel")}
        </legend>

        <div
          aria-label={t("parkingReport.periodLabel")}
          className="flex flex-wrap gap-1.5"
          role="group"
        >
          {PARKING_PRESETS.map((preset) => (
            <Button
              aria-pressed={activePreset === preset}
              key={preset}
              onClick={() => onPeriod(parkingPresetRange(preset, todayIso))}
              size="sm"
              variant={activePreset === preset ? "secondary" : "ghost"}
            >
              {t(`parkingReport.preset.${preset}`)}
            </Button>
          ))}
        </div>

        <div className="flex flex-wrap items-end gap-2 gap-y-3">
          <div className="flex flex-col gap-1">
            <label className="text-sm text-text-muted" htmlFor={fromId}>
              {t("parkingReport.periodFrom")}
            </label>
            <input
              className={dateInputClass}
              id={fromId}
              max={todayIso}
              onChange={(event) => setFrom(event.target.value)}
              type="date"
              value={period.from}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-sm text-text-muted" htmlFor={toId}>
              {t("parkingReport.periodTo")}
            </label>
            <input
              className={dateInputClass}
              id={toId}
              max={todayIso}
              onChange={(event) => setTo(event.target.value)}
              type="date"
              value={period.to}
            />
          </div>
        </div>

        <p className="text-sm text-text-muted">{t("parkingReport.periodHint")}</p>
      </fieldset>
    </div>
  );
}

/* --- Hisobot tanasi -------------------------------------------------------- */

function ReportBody({
  data,
  period,
  siteId,
}: {
  data: EdgeParkingReport;
  period: ParkingReportPeriod;
  siteId: string;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const periodId = useId();

  const hasEvents = data.total.entries + data.total.exits + data.total.total > 0;

  return (
    <div className="flex flex-col gap-6">
      {/* ⛔ Davr jumlasi JAVOBDAN, URL holatidan emas. */}
      <p className="text-sm text-text-muted" id={periodId}>
        {t("parkingReport.periodShown", {
          from: formatBusinessDay(format, data.from_date, locale),
          to: formatBusinessDay(format, data.to_date, locale),
        })}
      </p>

      <StatStrip label={t("parkingReport.summaryLabel")}>
        <StatTile
          icon={LogIn}
          label={t("parkingReport.entries")}
          value={formatAmount(format, data.total.entries, locale)}
        />
        <StatTile
          icon={LogOut}
          label={t("parkingReport.exits")}
          value={formatAmount(format, data.total.exits, locale)}
        />
        <StatTile
          icon={Banknote}
          label={t("parkingReport.revenue")}
          note={`${t("parkingReport.byCash", {
            amount: formatSoum(format, data.total.cash, locale),
          })} · ${t("parkingReport.byTerminal", {
            amount: formatSoum(format, data.total.terminal, locale),
          })}`}
          tone="accent"
          unit={t("parkingReport.amountUnit")}
          value={formatAmount(format, data.total.total, locale)}
        />
        <StatTile
          icon={Ticket}
          label={t("parkingReport.free")}
          value={formatAmount(format, data.total.free_count, locale)}
        />
      </StatStrip>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-text-muted">
          {t("parkingReport.sessionsCount", { count: data.sessions.length })}
        </p>
        <div className="flex flex-col gap-1">
          <ParkingExportButton period={period} siteId={siteId} />
          <p className="text-xs text-text-muted">{t("parkingReport.exportHint")}</p>
        </div>
      </div>

      <section aria-labelledby={`${periodId}-days`} className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold" id={`${periodId}-days`}>
          {t("parkingReport.daysTitle")}
        </h2>
        {hasEvents ? (
          <DaysTable data={data} />
        ) : (
          /* Bo'sh davr — NOMLANGAN HOLAT, nollar bilan to'la jadval emas. */
          <EmptyState
            description={t("parkingReport.emptyHint")}
            title={t("parkingReport.emptyTitle")}
          />
        )}
      </section>
    </div>
  );
}

function DaysTable({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    <div className="overflow-x-auto">
      {/* Native `<table>` + `<caption class="sr-only">` + `<th scope>` (§15). */}
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{t("parkingReport.daysTitle")}</caption>
        <thead>
          <tr className="border-b border-border text-left text-xs text-text-muted">
            <th className="p-3 font-normal" scope="col">
              {t("parkingReport.colDate")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colEntries")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colExits")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colCash")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colTerminal")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colTotal")}
            </th>
            <th className="p-3 text-right font-normal" scope="col">
              {t("parkingReport.colFree")}
            </th>
          </tr>
        </thead>
        <tbody>
          {data.days.map((row) => (
            <DayRow key={row.date} row={row} />
          ))}
        </tbody>
        <tfoot>
          {/* ⛔ Yig'indi SERVERDAN (`total`) — qatorlar ustida qayta sanalmaydi. */}
          <tr className="border-t border-border font-semibold">
            <th className="p-3 text-left" scope="row">
              {t("parkingReport.totalRow")}
            </th>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.entries, locale)}
            </td>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.exits, locale)}
            </td>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.cash, locale)}
            </td>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.terminal, locale)}
            </td>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.total, locale)}
            </td>
            <td className="p-3 text-right font-mono tabular-nums">
              {formatAmount(format, data.total.free_count, locale)}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function DayRow({ row }: { row: EdgeParkingReportDay }) {
  const format = useFormatter();
  const locale = useLocale();

  return (
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">{formatBusinessDay(format, row.date, locale)}</td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.entries, locale)}
      </td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.exits, locale)}
      </td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.cash, locale)}
      </td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.terminal, locale)}
      </td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.total, locale)}
      </td>
      <td className="p-3 text-right font-mono tabular-nums">
        {formatAmount(format, row.free_count, locale)}
      </td>
    </tr>
  );
}

/* --- Xato -------------------------------------------------------------------- */

function ReportError({ error }: { error: unknown }) {
  const t = useTranslations();
  /* Server kodlari (`report_period_*`) hisobot marshrutlariniki bilan bir xil. */
  const view = error instanceof ApiError ? reportErrorView(error.detail) : null;

  return (
    /* ⛔ Yiqilgan so'rov NOL bo'lib chizilmaydi — xato nomlanadi (D-10). */
    <p
      className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
      role="alert"
    >
      {view !== null ? (
        <>
          <span>{t(view.causeKey)}</span>
          <span>{t(view.fixKey)}</span>
        </>
      ) : (
        <>
          <span>{t("errors.loadFailedTitle")}</span>
          <span>{t("errors.loadFailedBody")}</span>
        </>
      )}
    </p>
  );
}
