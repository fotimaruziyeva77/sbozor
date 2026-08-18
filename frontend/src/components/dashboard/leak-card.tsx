"use client";

import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";
import type { CSSProperties } from "react";
import { AlertTriangle } from "lucide-react";

import { CardError } from "@/components/dashboard/card-error";
import { CardFreshness } from "@/components/dashboard/card-freshness";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { useReconciliationReport } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * «BAND, LEKIN TO'LOVSIZ» KARTASI — MAHSULOTNING ASOSIY QIYMATI.
 *
 * ⛔⛔ NEGA BU KARTA TUG'ILDI (260818 auditi, Topilma №5).
 *
 * PROJECT.md ning Core Value bandi so'zma-so'z shunday: «bozor
 * ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini
 * raqamlar va rasm-dalil bilan ko'radi — band, lekin to'lovsiz rastalar
 * kunlik hisobotda avtomatik fosh bo'ladi».
 *
 * Brauzerda o'lchandi: direktor panelida bu son UMUMAN yo'q edi. Panel
 * tushum, bandlik va sarlavha kartasini ko'rsatardi — ya'ni mahsulot
 * NIMA UCHUN sotib olinishini aytadigan yagona raqam ko'rinmasdi.
 * Tekshiruvchi ham, mijoz ham birinchi navbatda shunga qaraydi.
 *
 * ⛔ YANGI ENDPOINT QO'SHILMADI: `GET /reconciliation/report?day=`
 *    serverda ALLAQACHON `REPORT_VIEW` ostida va `unpaid_count` bilan
 *    `unpaid_expected_soum` ni qaytaradi. Karta faqat ULANMAGAN
 *    ma'lumotni ekranga chiqaradi.
 *
 * -----------------------------------------------------------------------
 * ⛔ KUN — KECHA, BUGUN EMAS (`occupancy-donut.tsx` bilan bir xil sabab).
 * -----------------------------------------------------------------------
 * Kunlik hisob kun yopilgandan keyin yoziladi. Bugungi kun uchun
 * so'ralsa, karta har doim nolga yaqin son ko'rsatib, «hammasi joyida»
 * degan YOLG'ON tasalli berardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ NOL — MUVAFFAQIYAT, «MA'LUMOT YO'Q» EMAS. IKKALASI AJRATILADI.
 * -----------------------------------------------------------------------
 * Javob kelmagan bo'lsa xato bloki chiziladi; javob kelib `unpaid_count`
 * nol bo'lsa, bu O'LCHANGAN natija va u shunday AYTILADI. Ikkalasini bir
 * xil ko'rsatish direktorga o'lchanmagan kunni «toza kun» deb o'qitardi
 * — bu mahsulotning butun va'dasini buzadigan yolg'on.
 * =============================================================================
 */

export function LeakCard() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const day = shiftIsoDay(todayIso, -1);

  const report = useReconciliationReport(day);
  const data = report.data;

  return (
    /* `--i: 2` — tushum va bandlik kartalaridan keyin kiradi. */
    <div className="motion-enter" style={{ "--i": 2 } as CSSProperties}>
      <Card aria-busy={report.isPending ? true : undefined}>
        <CardHeader className="flex flex-wrap items-start justify-between gap-2 pb-2">
          <div>
            <h2 className="text-lg font-semibold">{t("dashboard.leakTitle")}</h2>
            {data !== undefined ? (
              <p className="text-sm text-text-muted">
                {formatBusinessDay(format, data.day, locale)}
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
              <Skeleton className="h-9 w-40" />
              <Skeleton className="h-5 w-56" />
            </>
          ) : data === undefined ? null : data.unpaid_count === 0 ? (
            /* ⛔ O'LCHANGAN NOL — modul izohining oxirgi bandi. */
            <p className="text-sm">{t("dashboard.leakNone")}</p>
          ) : (
            <>
              <p className="flex items-center gap-2">
                <AlertTriangle
                  aria-hidden="true"
                  className="size-5 shrink-0 text-danger-text"
                />
                <span className="text-2xl font-semibold tabular-nums">
                  {t("dashboard.leakCount", { count: data.unpaid_count })}
                </span>
              </p>

              {/*
               * ⛔ SUMMA SERVERDAN (`unpaid_expected_soum`) — bu yerda
               *    ko'paytirilmaydi. Mijoz oldida ko'rsatiladigan pul
               *    raqamining ikkinchi hisoblanish yo'li bo'lishi mumkin
               *    emas.
               */}
              <p className="text-sm text-text-muted">
                {t("dashboard.leakAmount", {
                  amount: formatAmount(format, data.unpaid_expected_soum, locale),
                })}
              </p>

              {data.unregistered_count > 0 ? (
                <p className="text-sm text-text-muted">
                  {t("dashboard.leakUnregistered", {
                    count: data.unregistered_count,
                  })}
                </p>
              ) : null}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
