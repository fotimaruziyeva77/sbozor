"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import type { CSSProperties } from "react";

import { CardError } from "@/components/dashboard/card-error";
import { CardFreshness } from "@/components/dashboard/card-freshness";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { daysBetweenIsoDays, formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { useReceivablesReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * QARZDORLAR KARTASI — «QAYSI SOTUVCHI, QANCHA, QACHONDAN BERI».
 *
 * ⛔⛔ NEGA BU KARTA TUG'ILDI (260818 auditi, Topilma №5).
 *
 * Topshiriqda so'zma-so'z: «har bir sotuvchi tushumi qancha, to'lov
 * qilgan, qachon kechikkan». Panelda bu ma'lumot UMUMAN yo'q edi,
 * holbuki `GET /reports/debtors` uni ALLAQACHON beradi va u direktorning
 * `REPORT_VIEW` huquqi ostida.
 *
 * ⛔ YANGI ENDPOINT QO'SHILMADI — faqat ulanmagan javob ekranga chiqdi.
 *
 * -----------------------------------------------------------------------
 * ⛔ KECHIKISH KUNLARI — `oldest_debt_date` DAN, DAVR BOSHIDAN EMAS.
 * -----------------------------------------------------------------------
 * Server `oldest_debt_date` ni ATAYIN so'ralgan davrga QIRQMAYDI
 * (`schemas.py` izohi): qarz davrdan oldin boshlangan bo'lsa, haqiqiy
 * sana qaytadi. Shuning uchun «necha kundan beri» shu sanadan
 * hisoblanadi. Davr boshidan hisoblansa, uch oylik qarz «14 kun» bo'lib
 * ko'rinardi va aynan eng og'ir holat eng yengil ko'ringan bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ FAQAT UCHTA QATOR — VA QOLGANI SONI BILAN AYTILADI.
 * -----------------------------------------------------------------------
 * Bosh ekran ro'yxat sahifasi EMAS. Lekin qisqartirish JIM bo'lmaydi:
 * «yana N ta» qatori majburiy, aks holda direktor uchta qarzdorni butun
 * ro'yxat deb o'qirdi — kesilgan ro'yxat kesilganini aytmasa, u yolg'on
 * hisobotga aylanadi.
 *
 * ⚠ Sotuvchi ISMI ko'rinadi va bu HUQUQ bilan mos: endpoint `VENDOR_VIEW`
 *   ham talab qiladi (`reports.py`), direktorda u BOR. Kassirda yo'q —
 *   shuning uchun karta `report_view` darvozasi ortida turadi.
 * =============================================================================
 */

/** ⛔ Bosh ekranda ko'rinadigan qator soni — modul izohining 3-bandi. */
const TOP_ROWS = 3;

/** Qarzdorlik oynasi: oxirgi 30 kun (bosh ekran uchun «joriy holat»). */
const WINDOW_DAYS = 30;

export function DebtorsCard() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const to = shiftIsoDay(todayIso, -1);
  const from = shiftIsoDay(to, -(WINDOW_DAYS - 1));

  const report = useReceivablesReport({ from, to });
  const data = report.data;

  const rows = data?.rows.slice(0, TOP_ROWS) ?? [];
  const hidden = data === undefined ? 0 : data.row_count - rows.length;

  return (
    /* `--i: 3` — «band, lekin to'lovsiz» kartasidan keyin kiradi. */
    <div className="motion-enter" style={{ "--i": 3 } as CSSProperties}>
      <Card aria-busy={report.isPending ? true : undefined}>
        <CardHeader className="flex flex-wrap items-start justify-between gap-2 pb-2">
          <div>
            <h2 className="text-lg font-semibold">
              {t("dashboard.debtorsTitle")}
            </h2>
            {data !== undefined ? (
              <p className="text-sm text-text-muted">
                {formatBusinessDay(format, data.from_date, locale)} —{" "}
                {formatBusinessDay(format, data.to_date, locale)}
              </p>
            ) : null}
          </div>
          <CardFreshness
            isRefreshing={report.isFetching}
            onRefresh={() => {
              void report.refetch();
            }}
            updatedAt={report.dataUpdatedAt}
          />
        </CardHeader>

        <CardContent className="flex flex-col gap-3">
          {report.isError ? (
            <CardError
              onRetry={() => {
                void report.refetch();
              }}
            />
          ) : null}

          {report.isPending ? (
            <>
              <span className="sr-only" role="status">
                {t("common.loading")}
              </span>
              <Skeleton className="h-9 w-44" />
              <Skeleton className="h-16 w-full" />
            </>
          ) : data === undefined ? null : data.row_count === 0 ? (
            <p className="text-sm">{t("dashboard.debtorsNone")}</p>
          ) : (
            <>
              <p className="text-2xl font-semibold tabular-nums">
                {t("dashboard.debtorsTotal", {
                  amount: formatAmount(format, data.total_outstanding_soum, locale),
                })}
              </p>

              <ul className="flex flex-col gap-2">
                {rows.map((row) => {
                  /*
                   * ⛔ `null` — «qarz bor, lekin eng eski sanasi
                   *    aniqlanmagan». O'shanda kun SONI CHIZILMAYDI:
                   *    nol ko'rsatilsa, u «bugun boshlandi» degan
                   *    o'lchanmagan da'vo bo'lardi.
                   */
                  const days =
                    row.oldest_debt_date === null
                      ? null
                      : daysBetweenIsoDays(row.oldest_debt_date, todayIso);

                  return (
                    <li
                      className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5 border-b border-border pb-2 last:border-0 last:pb-0"
                      key={row.vendor_id}
                    >
                      {/*
                       * ⛔ `font-medium` QO'SHILMAYDI: G-motion-7(e) uning
                       *    sonini yuqoridan qulflaydi va u FAQAT qisqaradi.
                       *    Ism va summa pozitsiya bilan ajraladi —
                       *    og'irlik bilan emas.
                       */}
                      <span className="text-sm">{row.vendor_name}</span>
                      <span className="text-sm tabular-nums">
                        {formatAmount(format, row.outstanding_soum, locale)}
                      </span>
                      {/*
                       * ⛔⛔ BELGI MA'NOLI — MANFIY QOLDIQ QARZ EMAS.
                       *
                       * `report_repo` `outstanding_soum <> 0` bilan
                       * ishlaydi, ya'ni ORTIQCHA TO'LOV ham keladi.
                       * «N kundan beri kechikkan» ni avansga yozish
                       * to'lagan sotuvchini qarzdor deb ko'rsatardi.
                       */}
                      {row.outstanding_soum < 0 ? (
                        <span className="w-full text-xs text-text-muted">
                          {t("reports.overpaid")}
                        </span>
                      ) : days === null ? null : (
                        <span className="w-full text-xs text-text-muted">
                          {t("dashboard.debtorsLate", { days })}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>

              {/* ⛔ Kesilgan ro'yxat kesilganini AYTADI — modul izohi. */}
              {hidden > 0 ? (
                <p className="text-xs text-text-muted">
                  {t("dashboard.debtorsMore", { count: hidden })}
                </p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
