"use client";

import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import {
  Banknote,
  ReceiptText,
  ScanLine,
  Store,
  Target,
  TriangleAlert,
  Wallet,
} from "lucide-react";

import { PanelTile } from "@/components/panel/tile";
import { cn } from "@/lib/cn";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import type { Period } from "@/components/director/period";
import { compareNote, comparePeriod, includesToday } from "@/components/director/period";
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
import {
  useLiveRevenue,
  useReceivablesReport,
} from "@/lib/report-queries";
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

export function SixTiles({ period }: { period: Period }) {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  /*
   * ⛔⛔ DAVR ENDI TASHQARIDAN KELADI (260819). Avval bu yerda
   *     `day = today - 1` qotirilgan edi va butun panel kechagi kunni
   *     ko'rsatardi. Endi filtr direktorda: bugun · kecha · 7 kun ·
   *     30 kun · kalendardan oraliq (`period.ts`, `period-picker.tsx`).
   *
   * ⛔ Kun kesimidagi manbalar (nomuvofiqlik, bandlik, smenalar) BITTA
   *    kun bilan ishlaydi — ular uchun davrning OXIRGI kuni olinadi.
   *    Ko'p kunlik davrda ular «{sana} kesimida» deb belgilanadi, ya'ni
   *    ekranda qaysi kunniki ekani YASHIRILMAYDI.
   */
  const day = period.to;
  const prev = comparePeriod(period);
  const partial = includesToday(period, todayIso);
  const windowFrom = shiftIsoDay(day, -(WINDOW_DAYS - 1));

  /*
   * ⛔⛔ `/reports/live`, `/reports/revenue` EMAS (260819).
   *
   *     Hisobot marshruti bugungi kunni **422** bilan rad etadi
   *     (`daily_charges` D+1 04:10 da tug'iladi va o'sha javob
   *     imzolanadigan `.xlsx` ga tushadi). Panelning to'rt filtridan
   *     UCHTASI bugun bilan tugaydi — «Bugun», «7 kun», «30 kun» —
   *     ya'ni panel hech qachon pul ko'rsata olmasdi va buzuq bo'lib
   *     ko'rinardi [jonli o'lchandi].
   *
   *     `live` marshrutining `.xlsx` jufti YO'Q va u qo'shilmaydi;
   *     imzolanadigan hujjat hamon faqat yopilgan kunlardan quriladi.
   */
  const revenue = useLiveRevenue({ from: period.from, to: period.to });
  const revenuePrev = useLiveRevenue({ from: prev.from, to: prev.to });
  const leak = useReconciliationReport(day);
  const leakPrev = useReconciliationReport(shiftIsoDay(day, -7));
  const debtors = useReceivablesReport({ from: windowFrom, to: day });
  const occupancy = useOccupancyDay(day, todayIso);
  const accuracy = useAccuracyReport({ from: windowFrom, to: day });
  const shifts = useShiftReport(day);


  /* --- 1: tushum --------------------------------------------------------- */
  const revNow = revenue.data?.total_collected_soum ?? null;
  const revPrev = revenuePrev.data?.total_collected_soum ?? null;
  const dRev =
    revNow === null || revPrev === null
      ? null
      : deltaView(revNow, revPrev, { goodIsUp: true, bothClosed: true });

  /* --- 0: YIG'ILISH DARAJASI — panelning bosh savoli ---------------------- */
  /*
   * ⛔⛔ BU KO'RSATKICH MAHSULOTNING O'ZI: «har band rastadan patta
   *     TO'LIQ yig'ilyaptimi?». Yig'ilgan / hisoblangan.
   *
   * ⛔ HISOBLANGAN NOL BO'LSA FOIZ CHIZILMAYDI. Bugungi kun uchun
   *    `daily_charges` hali yaratilmagan bo'lishi mumkin va u holda
   *    `collected/0` cheksizlikka ketardi — ekranda esa u 0% yoki
   *    100% bo'lib ko'rinardi. Hokimga ko'rsatiladigan panelda soxta
   *    foizdan qimmatroq xato yo'q, shuning uchun bu holat OCHIQ
   *    aytiladi: «hali hisoblanmagan».
   */
  /*
   * ⛔⛔ DAVR BUGUNNI QAMRASA DARAJA CHIZILMAYDI — `charged_complete`.
   *
   *     Server javobning O'ZIDA maxraj to'liqligini aytadi. Bugungi
   *     patta hisobi ertaga 04:10 da tug'ilgani uchun bugungi
   *     `charged` KAM bo'ladi va undan chiqqan foiz 100% dan ham
   *     yuqori chiqishi mumkin — hokimga ko'rsatiladigan ekranda
   *     bundan qimmat yolg'on yo'q.
   *
   *     Yig'ilgan pul esa to'lovlardan real vaqtda o'qiladi va u
   *     HALOL — shuning uchun u BARIBIR ko'rsatiladi.
   */
  const chargedComplete = revenue.data?.charged_complete ?? false;
  const chargedNow = chargedComplete
    ? (revenue.data?.total_charged_soum ?? null)
    : null;
  const rate =
    revNow === null || chargedNow === null || chargedNow <= 0
      ? null
      : (revNow / chargedNow) * 100;
  const gapSoum =
    revNow === null || chargedNow === null || chargedNow <= 0
      ? null
      : Math.max(0, chargedNow - revNow);
  /*
   * ⛔ Ohang chegaralari: ≥95% yashil, ≥85% sariq, undan past qizil.
   *    Raqamlar TAXMIN emas — ular pilot maqsadidan olingan («to'liq
   *    yig'ilish» = 95% dan yuqori) va ular O'ZGARSA shu yerda,
   *    bitta joyda o'zgaradi.
   */
  const rateTone =
    rate === null ? "muted" : rate >= 95 ? "success" : rate >= 85 ? "warning" : "danger";

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

  const periodLabel =
    period.from === period.to
      ? formatBusinessDay(format, period.to, locale)
      : `${formatBusinessDay(format, period.from, locale)} — ${formatBusinessDay(format, period.to, locale)}`;

  return (
    <div className="dir-grid">
      {/* --- 0: YIG'ILISH DARAJASI — panelning bosh javobi ---------------- */}
      {/*
        ⛔ BIRINCHI O'RINDA VA BUTUN QATORNI EGALLAYDI (`dir-tile-hero`):
           kelgan tekshiruvchi yoki hokimlik vakili ekranga qaraganda
           BIRINCHI shu sonni ko'rishi kerak — «bozorda patta qanchalik
           to'liq yig'ilyapti». Qolgan beshta katak shu sonning IZOHI.
      */}
      <PanelTile
        action="Kunlar kesimi"
        className="dir-tile-hero"
        href="/reports"
        label="Patta yig'ilish darajasi"
        note={
          gapSoum === null ? undefined : (
            /* ⛔ «Yig'ilmagan» pastki qatorda, ajratgich ustida —
                 Stitch joylashuvi. U foizning MA'NOSI: 96.4% ni odam
                 «yaxshi» deb o'qiydi, «yig'ilmagan 900 000 so'm» esa
                 harakatga chaqiradi. */
            <span
              className={
                gapSoum > 0 ? "text-danger-text" : "text-text-muted"
              }
            >
              Yig&apos;ilmagan: {formatSoum(format, gapSoum, locale)}
            </span>
          )
        }
        step={0}
      >
        {/*
         * ⛔⛔ STITCH BOSH KATAGI — FOIZ HALQA ICHIDA (260819).
         *
         *     Avval halqa va foiz YONMA-YON turardi. Stitch maketida
         *     foiz halqaning MARKAZIDA va halqa yo'g'on — ekrandagi
         *     eng katta, eng birinchi o'qiladigan shakl. Yonma-yon
         *     turgan variantda ikkalasi ham kuchini yo'qotadi:
         *     halqa bezakka, foiz esa oddiy songa aylanadi.
         *
         * ⛔ Kompozitsiya IKKALA holatda ham BIR XIL, faqat qiymatlar
         *    «—» bo'ladi — panel ma'lumot kelganda sakramaydi.
         */}
        <div className="flex flex-wrap items-center gap-7">
          <div className="relative size-44 shrink-0">
            <svg aria-hidden="true" className="size-full -rotate-90" viewBox="0 0 40 40">
              <circle
                cx="20"
                cy="20"
                fill="none"
                r="16"
                stroke="var(--color-border)"
                strokeWidth="5"
              />
              {rate === null ? null : (
                <circle
                  className={
                    rateTone === "success"
                      ? "text-success"
                      : rateTone === "warning"
                        ? "text-warning"
                        : "text-danger"
                  }
                  cx="20"
                  cy="20"
                  fill="none"
                  r="16"
                  stroke="currentColor"
                  strokeDasharray={RING}
                  strokeDashoffset={RING * (1 - Math.min(1, rate / 100))}
                  strokeLinecap="round"
                  strokeWidth="5"
                />
              )}
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <p
                className={cn(
                  "dir-hero-stat",
                  rate === null && "text-text-muted",
                )}
              >
                {rate === null ? "—" : formatPercent(rate)}
              </p>
            </div>
          </div>

          <div className="flex min-w-0 flex-1 flex-col gap-4">
            <div>
              <Badge tone={rateTone}>
                {rate === null
                  ? partial
                    ? "Kun yopilmagan"
                    : "Hisoblanmagan"
                  : rate >= 95
                    ? "To'liq yig'ilmoqda"
                    : rate >= 85
                      ? "Bo'shliq bor"
                      : "Jiddiy bo'shliq"}
              </Badge>
            </div>

            {/*
             * ⛔ IKKI USTUN, UCHTA EMAS (Stitch): «Yig'ilgan» va
             *    «Hisoblangan» — o'lchov juftligi va ular yonma-yon
             *    solishtiriladi. «Yig'ilmagan» esa ularning FARQI va
             *    u pastki qatorda, qizil rangda turadi — chunki u
             *    o'lchov emas, XULOSA.
             */}
            <dl className="flex flex-wrap gap-x-14 gap-y-3">
              <div>
                <dt className="dir-tile-label">Yig&apos;ilgan</dt>
                <dd className="dir-tile-value mt-1">
                  {revNow === null ? "—" : formatSoum(format, revNow, locale)}
                </dd>
              </div>
              <div>
                <dt className="dir-tile-label">Hisoblangan</dt>
                <dd className="dir-tile-value mt-1 text-text-muted">
                  {chargedNow === null || chargedNow <= 0
                    ? "—"
                    : formatSoum(format, chargedNow, locale)}
                </dd>
              </div>
            </dl>

            {rate === null ? (
              <p className="dir-tile-note">
                {partial
                  ? "Bugungi patta hisobi hali yakunlanmagan — daraja kun yopilgach aniq bo'ladi."
                  : "Bu davr uchun hisoblangan patta topilmadi."}
              </p>
            ) : null}
          </div>
        </div>
      </PanelTile>

      {/*
        ⛔⛔ KATAKLAR ENDI MA'NO BO'YICHA GURUHLANGAN (Stitch tuzilmasi,
            260819): PUL -> NAZORAT. Oltita teng katakda ko'z qayerdan
            boshlashni bilmasdi; guruh sarlavhasi esa savolni oldindan
            aytadi. Guruh yorlig'i setka bo'ylab cho'ziladi
            (`dir-group-span`) — u katak EMAS, ajratgich.
      */}
      {/*
        ⛔⛔ TARTIB STITCH DIZAYNIDAN VA U MA'NOLI (260819 tuzatma).

            Birinchi ko'chirishda men faqat guruh YORLIG'INI qo'ygandim,
            kataklarni QAYTA TARTIBLAMAGANDIM — natijada «Qarz jami»
            NAZORAT guruhiga tushib qolgan, PULda esa bitta katak
            qolgan edi. Foydalanuvchi buni ekranda ko'rdi.

        ⛔ Guruh a'zolari SAVOL bo'yicha ajratiladi:
            PUL     — «qancha pul harakatlandi» (tushum · qarz · kassa)
            NAZORAT — «nima nazoratdan chetda» (to'lovsiz · bandlik · AI)
           Kataklarni ko'chirish IKKALA guruhni ham buzadi.
      */}
      <p className="dir-group-span dir-group-label">Pul</p>

      {/* --- 1 ------------------------------------------------------------ */}
      <PanelTile
        href="/reports"
        icon={Banknote}
        label="Tushum"
        note={dRev === null ? undefined : compareNote(period)}
        step={1}
      >
        {/*
         * ⛔ O'SISH YORLIG'I QIYMAT YONIDA (Stitch): «24 180 000 so'm
         *    +12.4%» bir qatorda o'qiladi. Alohida qatorda turganda u
         *    mustaqil fakt bo'lib ko'rinardi, holbuki u sonning
         *    IZOHI. Izoh matni esa kartaning pastiga tushdi.
         */}
        <div className="flex flex-wrap items-baseline gap-2.5">
          <p className="dir-tile-value">
            {revNow === null ? "—" : formatSoum(format, revNow, locale)}
          </p>
          {dRev === null ? null : <Badge tone={dRev.tone}>{dRev.text}</Badge>}
        </div>
      </PanelTile>

      {/* --- 3 ------------------------------------------------------------ */}
      <PanelTile
        href="/reports"
        icon={ReceiptText}
        label="Qarz jami"
        note={
          debtSum !== null && debtSum < 0 ? (
            "Ortiqcha to'lov — avans"
          ) : (
            /* ⛔ Chap/o'ng juftlik — Stitch «14 sotuvchi … eng eski:
                 12-avgust» qatori. Ikki fakt bir qatorda, lekin
                 ALOHIDA o'qiladi. */
            <span className="dir-tile-note-row">
              <span>
                {debtVendors === null ? "—" : debtVendors} sotuvchida
              </span>
              {oldestDebt === null ? null : (
                <span>
                  eng eski: {formatBusinessDay(format, oldestDebt, locale)}
                </span>
              )}
            </span>
          )
        }
        step={2}
        sub={`Reestr holati · ${formatBusinessDay(format, todayIso, locale)}`}
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
      </PanelTile>

      {/* --- 6 ------------------------------------------------------------ */}
      <PanelTile
        href="/reports"
        icon={Wallet}
        label="Kassirlar"
        note={
          shiftDiff === 0 ? undefined : (
            /* ⛔ Belgi MA'NOLI va `abs()` QILINMAYDI: kamomad bilan
                 ortiqcha bir xil ko'rsatilsa, ortiqcha naqdni jimgina
                 yutish kamomadni yashirish bilan teng bo'lardi. */
            <Badge tone="danger">
              {formatSoum(format, shiftDiff, locale)}{" "}
              {shiftDiff > 0 ? "tizim ortiq" : "kamomad"}
            </Badge>
          )
        }
        step={3}
        sub={`${formatBusinessDay(format, day, locale)} · smenalar`}
      >
        <div className="flex items-baseline gap-2.5">
          <p className="dir-tile-value">
            {formatAmount(format, closedShifts, locale)}
          </p>
          <span className="dir-tile-unit">
            smena yopildi · {shiftRows.length} dan
          </span>
        </div>
      </PanelTile>

      <p className="dir-group-span dir-group-label">Nazorat</p>

      {/* --- 2 ------------------------------------------------------------ */}
      <PanelTile
        dot="warning"
        href="/reports/compare"
        icon={TriangleAlert}
        label="Band, lekin to'lovsiz"
        note={
          leakCount === null || leakCount === 0 ? undefined : (
            <span className="dir-tile-note-row">
              <span>
                {leakSum === null
                  ? "Yo'qotish o'lchanmagan"
                  : `Yo'qotish: ${formatSoum(format, leakSum, locale)}`}
              </span>
              <Badge tone="warning">Diqqat talab</Badge>
            </span>
          )
        }
        step={4}
        sub={`${formatBusinessDay(format, day, locale)} · nazoratchi ko'rgan rastalar`}
      >
        {/*
         * ⛔ QIYMAT SARIQ — bu mahsulotning bosh nuqsoni va Stitch uni
         *    ataylab ajratadi. Rang YOLG'IZ signal emas: yorliq oldida
         *    nuqta, o'ngda ogohlantirish ikonkasi va pastda «Diqqat
         *    talab» yorlig'i bor.
         */}
        <div className="flex flex-wrap items-baseline gap-2.5">
          <p
            className={cn(
              "dir-tile-value",
              leakCount !== null && leakCount > 0 && "text-warning-text",
            )}
          >
            {leakCount === null ? "—" : formatAmount(format, leakCount, locale)}
          </p>
          <span className="dir-tile-unit">rasta</span>
          {dLeak === null ? null : <Badge tone={dLeak.tone}>{dLeak.text}</Badge>}
        </div>
      </PanelTile>

      {/* --- 4 ------------------------------------------------------------ */}
      <PanelTile
        href="/stalls"
        icon={Store}
        label="Bandlik"
        step={5}
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
      </PanelTile>

      {/* --- 5 ------------------------------------------------------------ */}
      <PanelTile
        href="/reports"
        icon={ScanLine}
        label="AI aniqligi"
        step={6}
        sub={
          acc === undefined
            ? "O'lchov yo'q"
            : `Oxirgi o'lchov · ${formatBusinessDay(format, acc.to_date, locale)}`
        }
      >
        {/* ⛔ Yashil FAQAT o'lchangan va yuqori bo'lganda — «yashil
               chunki yaxshi», «yashil chunki brend» emas. */}
        <p
          className={cn(
            "dir-tile-value",
            accPoint !== null && accPoint >= 0.95 && "text-success-text",
          )}
        >
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
      </PanelTile>

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
