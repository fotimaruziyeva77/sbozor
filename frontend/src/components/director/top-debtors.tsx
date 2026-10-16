"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";

import { topDebtors } from "@/components/director/chart-data";
import type { Period } from "@/components/director/period";
import { debtWindow } from "@/components/director/period";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatSoum } from "@/lib/format-number";
import { useReceivablesReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * ENG KATTA QARZDORLAR — gorizontal ustunlar (261016).
 *
 * Savol: «pul kimda qolib ketyapti?». «Qarz jami» katagi SONNI aytadi,
 * bu grafik esa uning KIMDA ekanini.
 *
 * ⛔ SO'ROV KATAK BILAN AYNI (`debtWindow`) — grafik va katak bir javobdan.
 *
 * ⛔ USTUNLAR HTML, SVG EMAS: sotuvchi ismi uzun va o'zbekcha; SVG o'q
 *    yorlig'i uni kesib tashlardi, HTML esa qatorga sig'dirib, kerak
 *    bo'lsa ko'p nuqta bilan qisqartiradi. Qiymat ustun uchida — har
 *    ustunga tooltip shart emas.
 *
 * ⛔ ISM YO'Q BO'LSA TO'QILMAYDI (D-08): na «Noma'lum», na «—». Qator
 *    rasta raqamlari bilan nomlanadi — u ham serverning fakti.
 * =============================================================================
 */

const LIMIT = 6;

export function TopDebtors({
  period,
  onShowAll,
}: {
  period: Period;
  /** «Sotuvchi kesimi» tabini ochadi — boshqa sahifaga olib ketmaydi. */
  onShowAll?: () => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();
  const todayIso = businessDayIn(timeZone, now);

  const debtors = useReceivablesReport(debtWindow(period, todayIso));
  const allRows = debtors.data?.rows ?? [];
  const rows = topDebtors(allRows, LIMIT);
  const peak = rows[0]?.outstanding_soum ?? 0;
  const hidden =
    allRows.filter((row) => row.outstanding_soum > 0).length - rows.length;

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("director.debtorsTitle")}</h2>
        <p className="dir-tile-sub">
          {t("director.registrySub", {
            date: formatBusinessDay(format, todayIso, locale),
          })}
        </p>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-4">
        {debtors.isLoading ? (
          <div aria-busy="true" className="flex flex-col gap-3">
            {Array.from({ length: 4 }, (_, index) => (
              <Skeleton className="h-8 w-full" key={index} />
            ))}
          </div>
        ) : debtors.isError || debtors.data === undefined ? (
          <p className="dir-tile-note" role="alert">
            {t("director.chartLoadError")}
          </p>
        ) : rows.length === 0 ? (
          <p className="dir-tile-note">{t("director.vaEmptyAll")}</p>
        ) : (
          <ol className="flex flex-col gap-3.5">
            {rows.map((row) => {
              const stalls = row.stall_codes.join(", ");
              return (
                <li className="flex flex-col gap-1.5" key={row.vendor_id ?? stalls}>
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate text-sm font-semibold">
                      {row.vendor_name ?? t("director.vaStalls", { codes: stalls })}
                    </span>
                    <span className="dir-split-value shrink-0">
                      {formatSoum(format, row.outstanding_soum, locale)}
                    </span>
                  </div>
                  {/*
                   * ⛔ Uzunlik ENG KATTA qarzga nisbatan: birinchi qator
                   *    to'liq, qolganlari uning ulushi. Ko'rinadigan matn
                   *    qiymatni allaqachon aytadi — chiziq faqat SHAKL.
                   */}
                  <div aria-hidden="true" className="dir-debt-track">
                    <span
                      className="dir-debt-bar"
                      style={{
                        width: `${Math.max(2, (row.outstanding_soum / peak) * 100)}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs text-text-muted">
                    {row.vendor_name === null
                      ? null
                      : `${t("director.vaStalls", { codes: stalls })} · `}
                    {row.oldest_debt_date === null
                      ? t("director.vaOldestUnknown")
                      : t("director.vaOldest", {
                          date: formatBusinessDay(format, row.oldest_debt_date, locale),
                        })}
                  </span>
                </li>
              );
            })}
          </ol>
        )}

        {/*
         * ⛔ «Yana N ta» — faqat MUSBAT qoldiqlar sanaladi: `row_count`
         *    avanslarni ham qamraydi va ular qarzdor emas.
         */}
        {hidden > 0 ? (
          <p className="dir-tile-note">
            {t("director.debtorsMore", { count: hidden })}
          </p>
        ) : null}

        {onShowAll === undefined ? null : (
          <button
            className="dir-tile-action mt-auto self-start"
            onClick={onShowAll}
            type="button"
          >
            {t("director.debtorsAll")} →
          </button>
        )}
      </CardContent>
    </Card>
  );
}
