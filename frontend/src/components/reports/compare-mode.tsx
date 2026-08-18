"use client";

import { useState } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { useReportPeriod } from "@/components/reports/period-picker";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { deltaView, formatAmount } from "@/lib/format-number";
import { daysBetweenIsoDays, isoDayToDate } from "@/lib/format-day";
import { useRevenueReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * SOLISHTIRISH REJIMI — `Sbozor Direktor - Hisobot.dc.html` bo'limi.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-19).
 *
 * Dizayn to'rtta rejim beradi: `Yo'q`, `Oldingi davr`, `O'tgan yilning
 * shu davri`, `Qo'lda tanlangan davr`. Jadval ustunlari:
 *   Ko'rsatkich | Joriy davr | Solishtirilgan davr | Farq | O'zgarish
 *
 * ⛔⛔ «QO'LDA TANLANGAN DAVR» QURILMADI VA BU ONGLI.
 *     U ikkinchi davr tanlagichini talab qiladi; ekranda allaqachon
 *     bitta davr tanlagichi bor va ikkinchisi qaysi biri «joriy»
 *     ekanini chalkashtirardi. Uch rejim (yo'q / oldingi / o'tgan yil)
 *     direktorning haqiqiy savoliga javob beradi. Qo'shilganda u shu
 *     yerga, o'sha reyestrga qo'shiladi.
 *
 * ⛔⛔ SERVER SOLISHTIRISH BERMAYDI — IKKINCHI SO'ROV YUBORILADI.
 *     Oyna TUTASH va TENG uzunlikda: `revenue-card.tsx` da o'rnatilgan
 *     va `six-tiles.tsx` da takrorlangan qoida. Aks holda 7 kun 5 kun
 *     bilan solishtirilib, pasayish «o'sish» bo'lib ko'rinardi.
 *
 * ⛔⛔ TUGAMAGAN DAVR UCHUN FOIZ HISOBLANMAYDI — dizayn 12-bo'limining
 *     taqiqi. `deltaView` ning `bothClosed` shoxi aynan shu; bu yerda u
 *     davr KECHAGI kundan oshib ketganda `false` bo'ladi.
 * =============================================================================
 */

type CompareMode = "none" | "prev" | "year";

const MODES: { id: CompareMode; key: string }[] = [
  { id: "none", key: "reports.compareNone" },
  { id: "prev", key: "reports.comparePrev" },
  { id: "year", key: "reports.compareYear" },
];

export function CompareMode() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const period = useReportPeriod();

  const [mode, setMode] = useState<CompareMode>("none");

  const current = useRevenueReport(
    { from: period.from, to: period.to },
    { enabled: !period.isEmpty },
  );

  const other = shiftedPeriod(period.from, period.to, mode);
  const compared = useRevenueReport(other ?? { from: period.from, to: period.to }, {
    enabled: other !== null && !period.isEmpty,
  });

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-end justify-between gap-4">
        <h2 className="dir-trend-title">{t("reports.compareTitle")}</h2>

        <div className="flex flex-wrap gap-1.5">
          {MODES.map((item) => (
            <Button
              aria-pressed={mode === item.id}
              key={item.id}
              onClick={() => setMode(item.id)}
              size="sm"
              variant={mode === item.id ? "secondary" : "ghost"}
            >
              {t(item.key as "reports.compareNone")}
            </Button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {mode === "none" ? (
          <p className="dir-tile-note">{t("reports.compareHint")}</p>
        ) : compared.isPending || current.isPending ? (
          <Skeleton className="dir-compare-skeleton" />
        ) : current.data === undefined || compared.data === undefined ? null : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-muted">
                  <th className="p-3 font-normal" scope="col">
                    {t("reports.compareIndicator")}
                  </th>
                  <th className="p-3 font-normal" scope="col">
                    {t("reports.compareCurrent")}
                  </th>
                  <th className="p-3 font-normal" scope="col">
                    {t("reports.compareOther")}
                  </th>
                  <th className="p-3 font-normal" scope="col">
                    {t("reports.compareDiff")}
                  </th>
                  <th className="p-3 font-normal" scope="col">
                    {t("reports.compareChange")}
                  </th>
                </tr>
              </thead>
              <tbody>
                <CompareRow
                  currentValue={current.data.total_collected_soum}
                  format={format}
                  label={t("reports.revenuePaid")}
                  locale={locale}
                  otherValue={compared.data.total_collected_soum}
                />
                <CompareRow
                  currentValue={current.data.total_charged_soum}
                  format={format}
                  label={t("reports.revenueCharged")}
                  locale={locale}
                  otherValue={compared.data.total_charged_soum}
                />
              </tbody>
            </table>

            {/* ⛔ Qaysi davrlar solishtirilgani AYNAN yoziladi. */}
            <p className="dir-tile-note dir-compare-foot">
              {formatBusinessDay(format, current.data.from_date, locale)} —{" "}
              {formatBusinessDay(format, current.data.to_date, locale)}
              {" · "}
              {formatBusinessDay(format, compared.data.from_date, locale)} —{" "}
              {formatBusinessDay(format, compared.data.to_date, locale)}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CompareRow({
  label,
  currentValue,
  otherValue,
  format,
  locale,
}: {
  label: string;
  currentValue: number;
  otherValue: number;
  format: ReturnType<typeof useFormatter>;
  locale: string;
}) {
  const t = useTranslations();
  const diff = currentValue - otherValue;
  const delta = deltaView(currentValue, otherValue, {
    goodIsUp: true,
    bothClosed: true,
  });

  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="p-3">{label}</td>
      <td className="p-3 font-mono tabular-nums">
        {formatAmount(format, currentValue, locale)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {formatAmount(format, otherValue, locale)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {formatAmount(format, diff, locale)}
      </td>
      <td className="p-3">
        {delta === null ? t("reports.compareIncomplete") : delta.text}
      </td>
    </tr>
  );
}

/**
 * Solishtiriladigan oyna.
 *
 * ⛔ `prev` — TUTASH va TENG uzunlikdagi oldingi oyna.
 * ⛔ `year` — AYNAN 365 kun orqaga: kabisa yilini hisobga olish uchun
 *    sanani qayta qurish kerak bo'lardi va u bir kunlik siljish berardi;
 *    365 kun esa «o'tgan yilning shu davri» ta'rifiga yetarli aniq.
 */
function shiftedPeriod(
  from: string,
  to: string,
  mode: CompareMode,
): { from: string; to: string } | null {
  if (mode === "none") return null;

  const length = daysBetweenIsoDays(from, to);
  if (length === null) return null;

  const shift = mode === "prev" ? length + 1 : 365;
  const shiftIso = (iso: string): string | null => {
    const date = isoDayToDate(iso);
    if (date === null) return null;
    date.setUTCDate(date.getUTCDate() - shift);
    return date.toISOString().slice(0, 10);
  };

  const nextFrom = shiftIso(from);
  const nextTo = shiftIso(to);
  if (nextFrom === null || nextTo === null) return null;

  return { from: nextFrom, to: nextTo };
}
