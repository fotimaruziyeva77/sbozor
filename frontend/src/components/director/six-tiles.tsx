"use client";

import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import { DirectorTile } from "@/components/director/tile";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import {
  deltaView,
  formatAmount,
  formatPercent,
  formatSoum,
} from "@/lib/format-number";
import { useAccuracyReport, useOccupancyDay } from "@/lib/occupancy-queries";
import { useReconciliationReport } from "@/lib/reconciliation-queries";
import { useReceivablesReport, useRevenueReport } from "@/lib/report-queries";
import { useShiftReport } from "@/lib/shift-queries";

/*
 * =============================================================================
 * OLTI KATAK — `Sbozor Direktor.dc.html` ning AYNAN tartibi va mazmuni.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-18).
 *
 *   1. Kechagi tushum        -> /reports          (Kunlar kesimi)
 *   2. Band, lekin to'lovsiz -> /reports/compare  (Kamera kadrlari)
 *   3. Qarz jami             -> /reports          (Qarzdorlar reestri)
 *   4. Bandlik               -> /stalls           (Rastalar ro'yxati)
 *   5. AI aniqligi           -> /reports          (O'lchov usuli)
 *   6. Kassirlar             -> /reports          (Smena yozuvlari)
 *
 * ⛔⛔ HAMMA SON KECHAGI KUNGA TEGISHLI — VA BU DIZAYNNING QARORI.
 *     Sarlavhada u OSHKORA yozilgan: «kechagi kun bo'yicha yopilgan
 *     raqamlar». Bugungi kun uchun so'ralsa, kunlik hisob hali
 *     yozilmagani uchun har katak nolga yaqin son ko'rsatib «hammasi
 *     joyida» degan YOLG'ON tasalli berardi.
 *
 *     ⚠ ISTISNO — 3-katak (qarz): u REESTR HOLATI, ya'ni bugungi kunga
 *       tegishli. Dizaynda ham «Reestr holati · 18-avgust» deb yozilgan.
 *
 * ⛔⛔ FOIZLAR IKKI SO'ROVDAN: server o'sish maydonini BERMAYDI. Har
 *     katak uchun oldingi davr ALOHIDA so'raladi va oyna TUTASH hamda
 *     TENG uzunlikda bo'ladi (`revenue-card.tsx` da o'rnatilgan qoida).
 *
 * ⛔ «to'liq emas» shoxi `deltaView` da bor va bu yerda `bothClosed`
 *    har doim `true`: kechagi kun ham, oldingi hafta shu kuni ham
 *    yopilgan. Shart QOLDIRILDI, chunki davr tanlanadigan hisobot
 *    sahifasida u `false` bo'ladi va ikki joyda ikki xil mantiq
 *    bo'lmasligi kerak.
 * =============================================================================
 */

/** Dizayn 5-katagi: o'lchov 15 daqiqadan eski bo'lsa ogohlantirish rangi. */
const STALE_AFTER_MS = 15 * 60 * 1000;

/** Bandlik donuti: `r=16` -> aylana uzunligi (dizayn qiymati). */
const RING = 2 * Math.PI * 16;

/** Qarzdorlik va aniqlik oynasi — oxirgi 30 kun. */
const WINDOW_DAYS = 30;

export function SixTiles() {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const day = shiftIsoDay(todayIso, -1);
  /* Oldingi hafta SHU kuni — dizayndagi «o'tgan hafta shu kuniga nisbatan». */
  const prevWeekday = shiftIsoDay(day, -7);
  const windowFrom = shiftIsoDay(day, -(WINDOW_DAYS - 1));

  const revenue = useRevenueReport({ from: day, to: day });
  const revenuePrev = useRevenueReport({ from: prevWeekday, to: prevWeekday });
  const leak = useReconciliationReport(day);
  const leakPrev = useReconciliationReport(prevWeekday);
  const debtors = useReceivablesReport({ from: windowFrom, to: day });
  const occupancy = useOccupancyDay(day, todayIso);
  const accuracy = useAccuracyReport({ from: windowFrom, to: day });
  const shifts = useShiftReport(day);

  const time = format.dateTime(now, { timeStyle: "short" });
  const updated = `Yangilandi: ${time}`;

  /* --- 1: kechagi tushum ------------------------------------------------- */
  const revNow = revenue.data?.total_collected_soum ?? null;
  const revPrev = revenuePrev.data?.total_collected_soum ?? null;
  const dRev =
    revNow === null || revPrev === null
      ? null
      : deltaView(revNow, revPrev, { goodIsUp: true, bothClosed: true });

  /* --- 2: band, lekin to'lovsiz ------------------------------------------ */
  const leakCount = leak.data?.unpaid_count ?? null;
  const leakSum = leak.data?.unpaid_expected_soum ?? null;
  const leakPrevCount = leakPrev.data?.unpaid_count ?? null;
  const dLeak =
    leakCount === null || leakPrevCount === null
      ? null
      : deltaView(leakCount, leakPrevCount, {
          goodIsUp: false,
          bothClosed: true,
        });

  /* --- 3: qarz jami ------------------------------------------------------ */
  const debtSum = debtors.data?.total_outstanding_soum ?? null;
  const debtVendors = debtors.data?.row_count ?? null;
  /*
   * ⛔ Eng eski qarz sanasi — qatorlardagi MINIMUM. Server yig'ma maydon
   *    bermaydi, lekin har qatorda `oldest_debt_date` bor va u `null`
   *    bo'lishi mumkin — o'shalar TASHLANADI. To'qilgan sana chizilmaydi
   *    (`debtors-report.tsx` dagi D-10 qoidasi).
   */
  const oldestDebt =
    debtors.data?.rows
      .map((row) => row.oldest_debt_date)
      .filter((value): value is string => value !== null)
      .sort()[0] ?? null;

  /* --- 4: bandlik -------------------------------------------------------- */
  const occ = occupancy.data;
  const occMeasured = occ !== undefined && occ.stalls > 0;
  const occPct = occMeasured ? (occ.occupied / occ.stalls) * 100 : null;

  /* --- 5: AI aniqligi ---------------------------------------------------- */
  const acc = accuracy.data;
  const accPoint = acc?.measured === true ? acc.correct.point : null;
  const accStale =
    accuracy.dataUpdatedAt > 0 &&
    now.getTime() - accuracy.dataUpdatedAt > STALE_AFTER_MS;

  /* --- 6: kassirlar ------------------------------------------------------ */
  const shiftRows = shifts.data?.rows ?? [];
  const closedShifts = shiftRows.filter((row) => row.closed_at !== null).length;
  /*
   * ⛔ Farqlar YIG'ILADI, ⛔ `abs()` OLINMAYDI: ishora ma'no tashiydi
   *    (`shift-queries.ts` izohi). Ikki kassirning teng va qarama-qarshi
   *    farqi nolga aylanishi — HAQIQAT, yashirish emas.
   */
  const shiftDiff = shiftRows.reduce((sum, row) => sum + row.variance_soum, 0);

  const loading =
    revenue.isPending ||
    leak.isPending ||
    debtors.isPending ||
    occupancy.isPending;

  if (loading) return <TilesSkeleton />;

  return (
    <div className="dir-grid">
      {/* --- 1 ------------------------------------------------------------ */}
      <DirectorTile
        action="Kunlar kesimi"
        href="/reports"
        index={1}
        label="Kechagi tushum"
        step={0}
        sub={formatBusinessDay(format, day, locale)}
        updatedAt={updated}
      >
        <p className="dir-tile-value">
          {revNow === null
            ? "—"
            : formatSoum(format, revNow, locale)}
        </p>
        {dRev === null ? null : (
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={dRev.tone}>{dRev.text}</Badge>
            <span className="dir-tile-note">
              o&apos;tgan hafta shu kuniga nisbatan
            </span>
          </div>
        )}
      </DirectorTile>

      {/* --- 2 ------------------------------------------------------------ */}
      <DirectorTile
        action="Kamera kadrlari"
        href="/reports/compare"
        index={2}
        label="Band, lekin to'lovsiz"
        step={1}
        sub={`${formatBusinessDay(format, day, locale)} · nazoratchi ko'rgan rastalar`}
        updatedAt={updated}
      >
        <div className="flex flex-wrap items-baseline gap-2.5">
          <p className="dir-tile-value">
            {leakCount === null ? "—" : formatAmount(format, leakCount, locale)}
          </p>
          <span className="dir-tile-unit">rasta</span>
          {leakSum === null ? null : (
            <p className="dir-tile-value-aside">
              {formatSoum(format, leakSum, locale)}
            </p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {leakCount !== null && leakCount > 0 ? (
            <Badge tone="warning">Hisob yozilmagan</Badge>
          ) : null}
          {dLeak === null ? null : <Badge tone={dLeak.tone}>{dLeak.text}</Badge>}
        </div>
      </DirectorTile>

      {/* --- 3 ------------------------------------------------------------ */}
      <DirectorTile
        action="Qarzdorlar reestri"
        href="/reports"
        index={3}
        label="Qarz jami"
        step={2}
        sub={`Reestr holati · ${formatBusinessDay(format, todayIso, locale)}`}
        updatedAt={updated}
      >
        {/*
         * ⛔⛔ BELGI MA'NOLI — MANFIY QOLDIQ QARZ EMAS, AVANS.
         *
         * `report_repo` `outstanding_soum <> 0` filtri bilan ishlaydi,
         * ya'ni ORTIQCHA TO'LOV ham qaytadi. Dizayn bu qiymatni HAR DOIM
         * qizil chizadi — uning namuna ma'lumotida qarz musbat. Real
         * ma'lumotda manfiy bo'lishi mumkin va o'shanda qizil rang
         * to'lab bo'lgan bozorni qarzdor deb ko'rsatardi.
         */}
        <p
          className={
            debtSum !== null && debtSum > 0
              ? "dir-tile-value dir-tile-value-danger"
              : "dir-tile-value"
          }
        >
          {debtSum === null
            ? "—"
            : formatSoum(format, debtSum, locale)}
        </p>
        <span className="dir-tile-note">
          {debtSum !== null && debtSum < 0
            ? "Ortiqcha to'lov — avans"
            : `${debtVendors === null ? "—" : debtVendors} sotuvchida${
                oldestDebt === null
                  ? ""
                  : ` · eng eski qarz ${formatBusinessDay(format, oldestDebt, locale)}`
              }`}
        </span>
      </DirectorTile>

      {/* --- 4 ------------------------------------------------------------ */}
      <DirectorTile
        action="Rastalar ro'yxati"
        href="/stalls"
        index={4}
        label="Bandlik"
        step={3}
        sub={formatBusinessDay(format, day, locale)}
        updatedAt={updated}
      >
        <div className="flex items-center gap-4">
          <svg
            aria-label="Bandlik ulushi"
            className="dir-donut"
            role="img"
            viewBox="0 0 42 42"
          >
            <circle
              cx="21"
              cy="21"
              fill="none"
              r="16"
              stroke="var(--color-border)"
              strokeWidth="6"
            />
            {/*
             * ⛔ Yoy `rotate(-90)` bilan yuqoridan boshlanadi va
             *    `stroke-linecap="butt"` — dizayn qiymati. Yumaloq uch
             *    nol foizda ham ko'rinadigan nuqta qoldirardi.
             */}
            <circle
              cx="21"
              cy="21"
              fill="none"
              r="16"
              stroke="var(--color-accent)"
              strokeDasharray={`${(((occPct ?? 0) / 100) * RING).toFixed(2)} ${RING.toFixed(2)}`}
              strokeLinecap="butt"
              strokeWidth="6"
              transform="rotate(-90 21 21)"
            />
          </svg>
          <div>
            <p className="dir-tile-value-sm">
              {occPct === null ? "—" : formatPercent(occPct)}
            </p>
            <p className="dir-tile-note">
              {occMeasured
                ? `${formatAmount(format, occ.occupied, locale)} / ${formatAmount(format, occ.stalls, locale)} rasta band`
                : "Bandlik hali o'lchanmagan"}
            </p>
          </div>
        </div>
      </DirectorTile>

      {/* --- 5 ------------------------------------------------------------ */}
      <DirectorTile
        action="O'lchov usuli"
        href="/reports"
        index={5}
        label="AI aniqligi"
        stale={accStale}
        step={4}
        sub={
          acc === undefined
            ? "O'lchov yo'q"
            : `Oxirgi o'lchov · ${formatBusinessDay(format, acc.to_date, locale)}`
        }
        updatedAt={accStale ? `${updated} · 15 daqiqadan eski` : updated}
      >
        <p className="dir-tile-value">
          {accPoint === null ? "—" : formatPercent(accPoint * 100)}
        </p>
        <div className="flex flex-col gap-1">
          {/*
           * ⛔ NAMUNA HAJMI VA ORALIQ BIRGA: yolg'iz foiz o'lchovning
           *    ishonchliligi haqida hech nima aytmaydi. `n < min_sample`
           *    bo'lsa server `measured: false` beradi va foiz UMUMAN
           *    chizilmaydi (`accuracy_report.py` chegarasi).
           */}
          <span className="dir-tile-note">
            {acc === undefined
              ? "Namuna yo'q"
              : `Namuna: ${formatAmount(format, acc.n, locale)} · qo'lda tekshirilgan`}
          </span>
          {acc === undefined ||
          acc.correct.lower === null ||
          acc.correct.upper === null ? (
            <span className="dir-tile-note">
              Ishonch oralig&apos;i o&apos;lchanmagan
            </span>
          ) : (
            <span className="dir-tile-note">
              Ishonch oralig&apos;i: {formatPercent(acc.correct.lower * 100)} —{" "}
              {formatPercent(acc.correct.upper * 100)}
            </span>
          )}
        </div>
      </DirectorTile>

      {/* --- 6 ------------------------------------------------------------ */}
      <DirectorTile
        action="Smena yozuvlari"
        href="/reports"
        index={6}
        label="Kassirlar"
        step={5}
        sub={`${formatBusinessDay(format, day, locale)} · smenalar`}
        updatedAt={updated}
      >
        <div className="flex items-baseline gap-2.5">
          <p className="dir-tile-value">
            {formatAmount(format, closedShifts, locale)}
          </p>
          <span className="dir-tile-unit">
            smena yopildi · {shiftRows.length} dan
          </span>
        </div>
        {shiftDiff === 0 ? null : (
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="warning">Deklaratsiya farqi</Badge>
            <span className="dir-tile-value-aside dir-tile-diff">
              {formatSoum(format, shiftDiff, locale)}
            </span>
            <span className="dir-tile-note">
              {shiftDiff > 0 ? "tizim ortiq" : "deklaratsiya ortiq"}
            </span>
          </div>
        )}
      </DirectorTile>
    </div>
  );
}

/** Yuklanish holati — dizayndagi olti skeleton kartasi. */
function TilesSkeleton() {
  const titles = [
    "Kechagi tushum",
    "Band, lekin to'lovsiz",
    "Qarz jami",
    "Bandlik",
    "AI aniqligi",
    "Kassirlar",
  ];

  return (
    <div className="dir-grid">
      {titles.map((title) => (
        <Card className="dir-tile" key={title}>
          <CardHeader className="dir-tile-head">
            <p className="dir-tile-label">{title}</p>
          </CardHeader>
          <CardContent className="dir-tile-body">
            <div aria-busy="true" className="flex flex-col gap-3">
              <Skeleton className="h-9 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-3.5 w-1/3" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
