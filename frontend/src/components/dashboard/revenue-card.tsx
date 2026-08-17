"use client";

import { useFormatter, useNow, useTimeZone, useTranslations } from "next-intl";
import type { CSSProperties } from "react";
import { useEffect, useRef, useState } from "react";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/cn";
import { formatBusinessDay } from "@/lib/format-day";
import { useRevenueReport } from "@/lib/report-queries";
import { useCountUp } from "@/lib/use-count-up";

/*
 * =============================================================================
 * TUSHUM TRENDI — 7 KUNLIK SPARKLINE (Y-2, 09-UI-SPEC §10.4, SC#2).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. HUQUQ SHARTI BU YERDA EMAS — SAHIFADA (G-motion-6(c))
 * -----------------------------------------------------------------------
 * `/dashboard` — HAMMA rol kiradigan sahifa va kassir navigatsiyasi aynan
 * `/dashboard` + `/collect`. «Komponent o'zini o'zi himoya qiladi» degan
 * shox bu faylda YOZILMAYDI: shart `dashboard/page.tsx` da turadi va
 * huquqsiz sessiyada SO'ROV HAM ketmaydi. Haqiqiy nazorat serverda —
 * `GET /reports/revenue` `REPORT_VIEW` ostida [VERIFIED: reports.py:156].
 *
 * -----------------------------------------------------------------------
 * ⛔ 2. MAVJUD ENDPOINT, MAVJUD HOOK — HECH NIMA KENGAYMAYDI (§14.3)
 * -----------------------------------------------------------------------
 * `useRevenueReport` 8-fazadan holicha chaqiriladi. Davr — KECHA bilan
 * tugaydigan 7 kun (O-04 [ASSUMED]: 7 nuqta telefonda o'qiladi; oy —
 * hisobot savoli va u `/reports` da bor). ⛔ Davr matni esa javobning
 * `from_date`/`to_date` sidan — SERVER haqiqati, so'ralgan davr emas.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. «O'LCHANMAGAN SON CHIZILMAYDI» (08 D-10)
 * -----------------------------------------------------------------------
 * 7 kundan kam nuqta — chiziq YO'Q, `EmptyState`. Xato — karta UMUMAN
 * chizilmaydi (`headline-card` §10.2 naqshi): bosh ekranda foydalanuvchi
 * hech narsa qila olmaydigan qizil blok — shovqin.
 *
 * -----------------------------------------------------------------------
 * ⚠ 4. CHIZILISH — INLINE `transition`, `@keyframes` EMAS
 * -----------------------------------------------------------------------
 * 600ms/250ms — L-5 ning KOMPOZIT qiymatlari. `@keyframes` reyestri
 * `globals.css` da yashaydi va u bu rejaning fayl ro'yxatidan TASHQARIDA
 * (parallel wave egaligi) — shuning uchun chizilish FLIP-klon presedenti
 * (09-RESEARCH Kod namunalari 3) bilan inline `transition` orqali:
 * ease TOKENDAN (`var(--ease-out)`), reduced-motion esa global `@media`
 * bloki (`transition-duration: 0.01ms !important`) bilan o'chadi.
 *
 * ⚠ `stroke-dasharray: 220` — [ASSUMED] (09-05 reja): `getTotalLength()`
 *   jsdom'da yo'q; chiziq to'liq chizilmasa qiymat ko'z bilan sozlanadi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. REAL-VAQT [L-6] — POLL EMAS, INVALIDATSIYA
 * -----------------------------------------------------------------------
 * Qiymat MAVJUD holatdan o'zgargandagina 400ms yumshoq count + BIR
 * martalik yashil «nafas» (`.motion-breath`). Birinchi yuklanishda nafas
 * YO'Q. Avtomatik poll QO'SHILMAYDI — «men boshqa raqam ko'rgandim»
 * nizosining manbai jimgina o'zgaradigan raqam edi (§10.6).
 * `.motion-enter` va `.motion-breath` ATAYIN ikki elementda: ikkalasi ham
 * `animation` shorthand va bitta elementda biri ikkinchisini bosardi.
 * =============================================================================
 */

/** Sparkline viewBox — 220x56, 4px ichki maydon. */
const VIEW_W = 220;
const VIEW_H = 56;
const PAD = 4;

/** [ASSUMED] chiziq uzunligi — modul izohi 4-band. */
const SPARKLINE_DASH = "220";

/** O-04: 7 nuqta — bosh ekranning «shu hafta qanday ketyapti» savoli. */
const MIN_POINTS = 7;

/** Nuqtalar -> `M/L` yo'li. Geometriya — vizualizatsiya, pul arifmetikasi emas. */
function sparklinePath(values: readonly number[]): string {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;

  return values
    .map((value, index) => {
      const x = Math.round(
        PAD + (index * (VIEW_W - PAD * 2)) / (values.length - 1),
      );
      const y = Math.round(
        VIEW_H - PAD - ((value - min) * (VIEW_H - PAD * 2)) / span,
      );
      return `${index === 0 ? "M" : "L"}${x} ${y}`;
    })
    .join(" ");
}

export function RevenueCard() {
  const t = useTranslations();
  const format = useFormatter();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  /* Davr chegaralari MAVJUD biznes-kun yordamchilaridan — yangi util YO'Q. */
  const todayIso = businessDayIn(timeZone, now);
  const to = shiftIsoDay(todayIso, -1);
  const from = shiftIsoDay(to, -(MIN_POINTS - 1));

  const report = useRevenueReport({ from, to });
  const total = report.data?.total_collected_soum ?? null;

  /*
   * [L-6] «nafas» faqat MAVJUD qiymat o'zgarganda; birinchi yuklanishda
   * YO'Q. `hadValueRef` count davomiyligini ham tanlaydi: birinchi
   * ko'rinish 600ms, yangilanish 400ms.
   */
  const hadValueRef = useRef(false);
  const prevTotalRef = useRef<number | null>(null);
  const cardRef = useRef<HTMLDivElement | null>(null);
  const [breathing, setBreathing] = useState(false);
  const [drawn, setDrawn] = useState(false);

  useEffect(() => {
    const prev = prevTotalRef.current;
    prevTotalRef.current = total;
    if (total === null) return;
    if (prev !== null && prev !== total) setBreathing(true);
    hadValueRef.current = true;
  }, [total]);

  /*
   * Nafas tugashi — NATIVE `animationend` tinglovchisi. React'ning
   * sintetik varianti jsdom'da yetib bormaydi [O'LCHANDI: proba,
   * `AnimationEvent` jsdom'da yo'q] — native tinglovchi ikkala muhitda
   * ham ishlaydi. Sinf olib tashlanishi KEYINGI yangilanishda nafasni
   * qayta qurollantiradi (remove -> add restart qiladi).
   */
  useEffect(() => {
    if (!breathing) return;
    const card = cardRef.current;
    if (card === null) return;
    const settle = (): void => setBreathing(false);
    card.addEventListener("animationend", settle);
    return () => card.removeEventListener("animationend", settle);
  }, [breathing]);

  const shownTotal = useCountUp(total, hadValueRef.current ? 400 : 600);

  const rows = report.data?.rows;
  const enough = rows !== undefined && rows.length >= MIN_POINTS;

  /* Chizilish: bir kadr 220 offset bilan bo'yaladi, keyin 0 ga transition. */
  useEffect(() => {
    if (!enough) return;
    const frame = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(frame);
  }, [enough]);

  /* Xato — karta UMUMAN chizilmaydi (modul izohi 3-band). */
  if (report.isError) return null;

  const lineD = enough
    ? sparklinePath(rows.map((row) => row.collected_soum))
    : null;

  return (
    /* `.motion-enter` alohida o'ramda — `.motion-breath` bilan to'qnashmasin. */
    <div className="motion-enter" style={{ "--i": 0 } as CSSProperties}>
      <Card
        aria-busy={report.isPending ? true : undefined}
        className={cn(breathing ? "motion-breath" : null)}
        ref={cardRef}
      >
        <CardHeader className="pb-2">
          <h2 className="text-lg font-semibold">
            {t("dashboard.revenueTrendTitle")}
          </h2>
          <p className="text-sm text-text-muted">
            {t("dashboard.revenueTrendPeriod")}
          </p>
        </CardHeader>

        <CardContent className="flex flex-col gap-3">
          {report.isPending ? (
            <>
              <span className="sr-only" role="status">
                {t("common.loading")}
              </span>
              {/* Shimmer skeleton — spinner TAQIQ (§10.2). */}
              <Skeleton className="h-8 w-40" />
              <Skeleton className="h-14 w-full" />
            </>
          ) : !enough ? (
            /* ⛔ 7 kundan kam nuqta — chiziq CHIZILMAYDI (08 D-10). */
            <EmptyState
              className="py-6"
              description={t("dashboard.revenueTrendEmptyHint")}
              title={t("dashboard.revenueTrendEmpty")}
            />
          ) : (
            <>
              <p className="text-2xl font-semibold tracking-tight">
                {/*
                 * A11y (§10.3): yakuniy qiymat `sr-only` bo'lib DARHOL
                 * to'liq; sanayotgan span `aria-hidden` — `aria-live` YO'Q.
                 */}
                <span className="sr-only">
                  {format.number(report.data.total_collected_soum)}
                </span>
                <span aria-hidden="true" className="font-mono" data-numeric>
                  {format.number(
                    shownTotal ?? report.data.total_collected_soum,
                  )}
                </span>{" "}
                <span className="text-sm font-normal text-text-muted">
                  {t("reports.amountUnit")}
                </span>
              </p>

              {/* ⛔ Davr — javobning `from_date`/`to_date` si (server haqiqati). */}
              <p className="text-sm text-text-muted">
                {t("reports.periodShown", {
                  from: formatBusinessDay(format, report.data.from_date),
                  to: formatBusinessDay(format, report.data.to_date),
                })}
              </p>

              <svg
                className="w-full"
                preserveAspectRatio="none"
                role="img"
                viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
              >
                <title>{t("dashboard.revenueTrendTitle")}</title>
                {/* Ostki maydon — aksent TINTI (0.08), to'yingan fon EMAS (§5.4). */}
                <path
                  d={`${lineD} L${VIEW_W - PAD} ${VIEW_H - PAD} L${PAD} ${VIEW_H - PAD} Z`}
                  fill="var(--color-accent)"
                  fillOpacity="0.08"
                  stroke="none"
                />
                <path
                  d={lineD ?? ""}
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  style={{
                    strokeDasharray: SPARKLINE_DASH,
                    strokeDashoffset: drawn ? "0" : SPARKLINE_DASH,
                    /* 600ms/250ms — L-5 kompoziti; modul izohi 4-band. */
                    transition:
                      "stroke-dashoffset 600ms var(--ease-out) 250ms",
                  }}
                />
              </svg>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
