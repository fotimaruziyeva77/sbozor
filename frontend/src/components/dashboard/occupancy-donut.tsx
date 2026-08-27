"use client";

import { useFormatter, useLocale, useNow, useTimeZone, useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { useEffect, useState } from "react";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { CardError } from "@/components/dashboard/card-error";
import { CardFreshness } from "@/components/dashboard/card-freshness";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { useOccupancyDay } from "@/lib/occupancy-queries";

/*
 * =============================================================================
 * BANDLIK HALQASI — KECHAgi YOPILGAN KUN DONUTI (Y-2, 09-UI-SPEC §10.4, SC#2).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. HUQUQ SHARTI BU YERDA EMAS — SAHIFADA (G-motion-6(c))
 * -----------------------------------------------------------------------
 * `revenue-card.tsx` bilan AYNI taqsimot: shart `dashboard/page.tsx` da,
 * huquqsiz sessiyada so'rov HAM ketmaydi. Server tomonda `GET /occupancy`
 * `REPORT_VIEW` ostida [VERIFIED: occupancy.py:83,114].
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. NEGA AYNAN KECHA (09-RESEARCH Tuzoq 3 va 4 — ikkalasi o'lchangan)
 * -----------------------------------------------------------------------
 * (a) Bugungi javob odatda BO'SH: kunning materializatsiyasi ERTASI kuni
 *     03:40 da (`worker.py::DAY_CLOSE_CRON`) — direktor doim bo'sh halqa
 *     ko'rardi va «tizim ishlamayapti» deb xulosa qilardi.
 * (b) `day === todayIso` bo'lganda `occupancyPollInterval` avtomatik
 *     poll'ni YOQADI — §10.6 ning «poll QO'SHILMAYDI» qoidasi jimgina
 *     buzilardi. Kecha so'ralganda poll O'ZI o'chadi (`false`).
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. `stalls === 0` — «KUN HALI YOPILMAGAN», «HAMMA RASTA BO'SH» EMAS
 * -----------------------------------------------------------------------
 * Nol bilan halqa chizish TAQIQ (T-05-04 — o'lchanmagan son chizilmaydi):
 * halqa o'rniga `dashboard.occupancyEmpty` matni. Xato — karta UMUMAN
 * chizilmaydi (`headline-card` §10.2 naqshi).
 *
 * -----------------------------------------------------------------------
 * ⚠ 4. HOOK KONTRAKTI KENGAYMAYDI — `select` YO'Q (reja-kontrakt farqi)
 * -----------------------------------------------------------------------
 * Reja `select:` bilan javobni ikki songa qisqartirishni aytgan edi, LEKIN
 * `useOccupancyDay(day, todayIso, {enabled?})` imzosi `select` olmaydi va
 * «hook ichiga hech narsa qo'shilmaydi» sharti ustun (KONTRAKT yutadi).
 * Bu yerda `select` amalda hech narsa bermasdi ham: kun YOPIQ (poll yo'q,
 * bitta fetch) — qayta renderlar `items` diffidan tug'ilmaydi. Komponent
 * javobdan FAQAT uch hisoblagichni o'qiydi; `items[]` (1000 tagacha)
 * DOM'ga tushmaydi.
 *
 * -----------------------------------------------------------------------
 * ⚠ 5. CHIZILISH — INLINE `transition` (`revenue-card` 4-band bilan AYNI)
 * -----------------------------------------------------------------------
 * `stroke-dashoffset: 226 -> hisoblangan`, 600ms (L-5 kompoziti), ease
 * TOKENDAN. 226 — r=36 halqaning aylanasi (2π·36 ≈ 226.19, SPEC qiymati).
 * Yoy ulushi — chizish GEOMETRIYASI: ekranga FOIZ chiqarilmaydi, matnli
 * yig'indi xom serverdagi sonlar bilan (`{occupied} band · {empty} bo'sh`).
 * Rang reyestri `day-breakdown.tsx` dan: band — success, halqa izi —
 * border; yonida MATN bor — rang yolg'iz signal emas (§15).
 * =============================================================================
 */

/** Halqa geometriyasi — 96 kvadrat, r=36, yo'g'onlik 12. */
const RING_R = "36";
const RING_CENTER = "48";
const RING_WIDTH = "12";

/** Aylana uzunligi — SPEC qiymati (2π·36 ni yaxlitlagan). */
const RING_CIRCUMFERENCE = 226;

export function OccupancyDonut() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  /* ⛔ KECHA — modul izohi 2-band; yordamchilar 4-fazadan, yangi util YO'Q. */
  const todayIso = businessDayIn(timeZone, now);
  const day = shiftIsoDay(todayIso, -1);

  const occupancy = useOccupancyDay(day, todayIso);
  const summary = occupancy.data;
  const measured = summary !== undefined && summary.stalls > 0;

  /* Chizilish: bir kadr to'liq bo'sh halqa, keyin nishonga transition. */
  const [drawn, setDrawn] = useState(false);
  useEffect(() => {
    if (!measured) return;
    const frame = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(frame);
  }, [measured]);

  /* ⛔ Sabab `revenue-card.tsx` dagi bilan bir xil: karta o'rnida qoladi. */

  /* Yoy nishoni — vizualizatsiya geometriyasi (butun son, `Math.round`). */
  const target = measured
    ? Math.round(
        RING_CIRCUMFERENCE * (1 - summary.occupied / summary.stalls),
      )
    : RING_CIRCUMFERENCE;

  return (
    /* `.motion-enter` + `--i: 1` — tushum kartasidan 60ms keyin kiradi. */
    <div className="motion-enter" style={{ "--i": 1 } as CSSProperties}>
      <Card aria-busy={occupancy.isPending ? true : undefined}>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2 pb-2">
          <div>
            <h2 className="text-lg font-semibold">
            {t("dashboard.occupancyTitle")}
          </h2>
            {summary !== undefined ? (
              /* Qaysi KUN — javobning `day` maydonidan, yagona sana yo'li. */
              <p className="text-sm text-text-muted">
                {formatBusinessDay(format, summary.day, locale)}
              </p>
            ) : null}
          </div>
          <CardFreshness
            isRefreshing={occupancy.isFetching}
            onRefresh={() => {
              void occupancy.refetch();
            }}
            updatedAt={occupancy.dataUpdatedAt}
          />
        </CardHeader>

        <CardContent className="flex flex-col gap-3">
          {occupancy.isError ? (
            <CardError
              onRetry={() => {
                void occupancy.refetch();
              }}
            />
          ) : null}
          {occupancy.isPending ? (
            <>
              <span className="sr-only" role="status">
                {t("common.loading")}
              </span>
              {/* Shimmer skeleton — spinner TAQIQ (§10.2). */}
              <div className="flex items-center gap-4">
                <Skeleton className="size-24 rounded-full" />
                <Skeleton className="h-5 w-40" />
              </div>
            </>
          ) : !measured ? (
            /* ⛔ Kun hali yopilmagan — halqa CHIZILMAYDI (T-05-04). */
            <p className="text-sm text-text-muted">
              {t("dashboard.occupancyEmpty")}
            </p>
          ) : (
            <div className="flex items-center gap-4">
              <svg
                className="size-24 shrink-0"
                role="img"
                viewBox="0 0 96 96"
              >
                <title>{t("dashboard.occupancyTitle")}</title>
                {/* Halqa izi — o'lchangan TO'PLAM (band + bo'sh). */}
                <circle
                  cx={RING_CENTER}
                  cy={RING_CENTER}
                  fill="none"
                  r={RING_R}
                  stroke="var(--color-border)"
                  strokeWidth={RING_WIDTH}
                />
                {/* Band yoyi — success (occupancy rang reyestri). */}
                <circle
                  cx={RING_CENTER}
                  cy={RING_CENTER}
                  fill="none"
                  r={RING_R}
                  stroke="var(--color-success)"
                  strokeLinecap="round"
                  strokeWidth={RING_WIDTH}
                  transform={`rotate(-90 ${RING_CENTER} ${RING_CENTER})`}
                  style={{
                    strokeDasharray: String(RING_CIRCUMFERENCE),
                    strokeDashoffset: drawn
                      ? String(target)
                      : String(RING_CIRCUMFERENCE),
                    /* 600ms — L-5 kompoziti; modul izohi 5-band. */
                    transition: "stroke-dashoffset 600ms var(--ease-out)",
                  }}
                />
              </svg>

              {/*
               * Bandlik ulushi — «Sbozor Direktor» dizayni §4.
               * ⛔ Bu KLIENT ARIFMETIKASI EMAS degan qoidaning istisnosi
               *    emas: bo'linma PUL emas, ikkita SANOQ ustidagi
               *    vizualizatsiya nisbati va u allaqachon halqa yoyini
               *    chizish uchun hisoblanadi. Pul raqamlari baribir
               *    serverdan keladi.
               * ⛔ Nol bo'luvchidan himoya: `stalls === 0` shoxida bu blok
               *    umuman chizilmaydi (yuqoridagi shart).
               */}
              <p className="text-lg font-semibold" data-numeric>
                {Math.round((summary.occupied / summary.stalls) * 100)}%
              </p>
              <p className="text-sm text-text" data-numeric>
                {t("dashboard.occupancySummary", {
                  empty: summary.empty,
                  occupied: summary.occupied,
                })}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
