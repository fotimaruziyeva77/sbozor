"use client";

import { useState } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import type { RevenueReportRow } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { formatBusinessDay, formatBusinessWeekday } from "@/lib/format-day";
import { formatAmount, groupDigits } from "@/lib/format-number";

/*
 * =============================================================================
 * TUSHUM KALENDARI — kunlar BIR QARASHDA (261016).
 *
 * ⛔⛔ NEGA. Foydalanuvchi: «kunlarni ko'rish uchun scroll qilish kerak —
 *     telefonda bu juda ko'p vaqt oladi». O'ttiz qatorli jadval telefonda
 *     uch-to'rt ekran edi. Kalendarda butun oy BITTA ekranga sig'adi:
 *     hafta kunlari ustunda, haftalar qatorda — «qaysi kuni kam
 *     yig'ildi?» savoli ko'z bilan topiladi, aylantirib emas.
 *
 * ⛔ HAR SON SERVERDAN: katak `collected_soum` ni ko'rsatadi, belgilar esa
 *    `diff_soum` va `charged_soum` ning ISHORASIDAN. Klientda ayirish ham,
 *    yig'ish ham yo'q (D-03) — faqat ming so'mga yaxlitlab YOZISH.
 *
 * ⛔ RANG IKKI XIL ISHNI QILADI VA ULAR ARALASHMAYDI:
 *    · fon to'qligi — QANCHA yig'ilgani (bitta ohang, och -> to'q);
 *    · nuqta — HOLAT: qizil «hisobdan kam yig'ildi», kulrang «patta
 *      hisoblanmagan». Nuqta yolg'iz emas: legenda va katakning
 *      `aria-label` i so'z bilan aytadi.
 *
 * ⛔ ORTIQCHA TO'LOV YASHIL QILINMAYDI (jadvaldagi §8.2 qoidasi): u ham
 *    tekshiriladigan holat, «yaxshi natija» emas.
 * =============================================================================
 */

type Cell = { iso: string; row: RevenueReportRow | null };

/** ISO kunni UTC tushiga langarlaydi — mahalliy mintaqa kunni surmaydi. */
function isoDate(iso: string): Date {
  return new Date(`${iso}T12:00:00Z`);
}

function addDays(iso: string, days: number): string {
  const date = isoDate(iso);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** Dushanba = 0 … yakshanba = 6. */
function weekdayIndex(iso: string): number {
  return (isoDate(iso).getUTCDay() + 6) % 7;
}

/**
 * Haftalar to'ri: birinchi kun haftasining dushanbasidan oxirgi kun
 * haftasining yakshanbasigacha. Davrdan tashqaridagi kataklar `row: null`.
 */
export function calendarWeeks(rows: readonly RevenueReportRow[]): Cell[][] {
  if (rows.length === 0) return [];
  const byDay = new Map(rows.map((row) => [row.business_date, row]));
  const first = rows[0].business_date;
  const last = rows[rows.length - 1].business_date;

  const start = addDays(first, -weekdayIndex(first));
  const end = addDays(last, 6 - weekdayIndex(last));

  const weeks: Cell[][] = [];
  let week: Cell[] = [];
  for (let iso = start; iso <= end; iso = addDays(iso, 1)) {
    week.push({ iso, row: byDay.get(iso) ?? null });
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  return weeks;
}

/**
 * Fon to'qligi — 0 (pul yo'q) va 1–4 (eng katta kunga nisbatan chorak).
 *
 * ⛔ Manfiy yoki nol tushum — 0: storno kuni «och» ko'rinadi, to'q emas.
 */
export function heatLevel(value: number, peak: number): number {
  if (value <= 0 || peak <= 0) return 0;
  return Math.min(4, Math.max(1, Math.ceil((value / peak) * 4)));
}

/** Katakdagi yozuv — ming so'mda; noldan katta, lekin mingdan kichik — «<1». */
export function thousands(value: number): string {
  if (value === 0) return "0";
  if (value > 0 && value < 1000) return "<1";
  return groupDigits(Math.round(value / 1000));
}

export function RevenueCalendar({ rows }: { rows: readonly RevenueReportRow[] }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const weeks = calendarWeeks(rows);
  const peak = Math.max(0, ...rows.map((row) => row.collected_soum));
  const [selected, setSelected] = useState<string | null>(null);
  const active =
    rows.find((row) => row.business_date === selected) ?? rows[rows.length - 1];

  const weekdays = t("reports.calWeekdays").split(",");
  const shortDays = rows.filter((row) => row.diff_soum < 0).length;
  const unchargedDays = rows.filter(
    (row) => row.charged_soum === 0 && row.collected_soum > 0,
  ).length;

  return (
    <div className="flex flex-col gap-3">
      {/*
       * ⛔ Xulosa — kalendarning o'qish kaliti: nechta kun muammoli. Sanoq
       *    qatorlardan, pul emas — summa yuqoridagi yig'indida.
       */}
      <p className="text-sm">
        <span className={cn(shortDays > 0 && "text-danger-text")}>
          {t("reports.calShortDays", { count: shortDays })}
        </span>
        {" · "}
        <span className="text-text-muted">
          {t("reports.calUnchargedDays", { count: unchargedDays })}
        </span>
      </p>

      <div className="rev-cal" role="group" aria-label={t("reports.calLabel")}>
        <div aria-hidden="true" className="rev-cal-row">
          {weekdays.map((name) => (
            <span className="rev-cal-weekday" key={name}>
              {name}
            </span>
          ))}
        </div>
        {weeks.map((week) => (
          <div className="rev-cal-row" key={week[0]?.iso}>
            {week.map((cell) => {
              if (cell.row === null) {
                return <span aria-hidden="true" className="rev-cal-pad" key={cell.iso} />;
              }
              const row = cell.row;
              const short = row.diff_soum < 0;
              const uncharged = row.charged_soum === 0 && row.collected_soum > 0;
              const day = Number(cell.iso.slice(8, 10));
              const status = short
                ? t("reports.calShort")
                : uncharged
                  ? t("reports.calUncharged")
                  : null;
              return (
                <button
                  aria-label={`${formatBusinessDay(format, cell.iso, locale)}: ${t("reports.revenuePaid")} ${formatAmount(format, row.collected_soum, locale)} ${t("reports.amountUnit")}${status === null ? "" : ` — ${status}`}`}
                  aria-pressed={active?.business_date === cell.iso}
                  className={cn(
                    "rev-cal-cell",
                    `rev-cal-heat-${heatLevel(row.collected_soum, peak)}`,
                  )}
                  key={cell.iso}
                  onClick={() => setSelected(cell.iso)}
                  type="button"
                >
                  <span className="rev-cal-day">
                    {day === 1 || cell.iso === rows[0].business_date
                      ? `${day}.${cell.iso.slice(5, 7)}`
                      : day}
                  </span>
                  <span className="rev-cal-sum">{thousands(row.collected_soum)}</span>
                  {short ? (
                    <span aria-hidden="true" className="rev-cal-dot rev-cal-dot-short" />
                  ) : uncharged ? (
                    <span aria-hidden="true" className="rev-cal-dot rev-cal-dot-uncharged" />
                  ) : null}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Legenda — rang yolg'iz signal emas (WCAG 1.4.1). */}
      <ul className="rev-cal-legend">
        <li>
          <span aria-hidden="true" className="rev-cal-scale">
            <span className="rev-cal-heat-1" />
            <span className="rev-cal-heat-2" />
            <span className="rev-cal-heat-3" />
            <span className="rev-cal-heat-4" />
          </span>
          {t("reports.calScale")}
        </li>
        <li>
          <span aria-hidden="true" className="rev-cal-dot rev-cal-dot-short" />
          {t("reports.calShort")}
        </li>
        <li>
          <span aria-hidden="true" className="rev-cal-dot rev-cal-dot-uncharged" />
          {t("reports.calUncharged")}
        </li>
      </ul>

      {active === undefined ? null : (
        /*
         * ⛔ TANLANGAN KUN — uchala son serverdan kelganicha (jadval
         *    qatorining aynan o'zi). Kun bosilganda shu yerda ochiladi:
         *    boshqa sahifaga o'tish ham, aylantirish ham yo'q.
         */
        <section aria-live="polite" className="rev-cal-detail">
          <p className="text-sm font-semibold">
            {formatBusinessDay(format, active.business_date, locale)}
            <span className="font-normal text-text-muted">
              {" · "}
              {formatBusinessWeekday(format, active.business_date, locale)}
            </span>
          </p>
          <dl className="rev-cal-detail-grid">
            <div>
              <dt>
                {t("reports.revenuePaid")}
                <span className="block">{t("reports.revenuePaidHint")}</span>
              </dt>
              <dd>
                {formatAmount(format, active.collected_soum, locale)} {t("reports.amountUnit")}
              </dd>
            </div>
            <div>
              <dt>
                {t("reports.revenueCharged")}
                <span className="block">{t("reports.revenueChargedHint")}</span>
              </dt>
              <dd>
                {formatAmount(format, active.charged_soum, locale)} {t("reports.amountUnit")}
              </dd>
            </div>
            <div>
              <dt>{t("reports.revenueDiff")}</dt>
              <dd className={cn(active.diff_soum < 0 && "text-danger-text")}>
                {formatAmount(format, active.diff_soum, locale)} {t("reports.amountUnit")}
              </dd>
            </div>
          </dl>
        </section>
      )}
    </div>
  );
}
