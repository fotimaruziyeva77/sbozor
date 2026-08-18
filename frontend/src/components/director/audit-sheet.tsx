"use client";

import { useFormatter, useLocale, useNow, useTimeZone } from "next-intl";

import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { sumByAge } from "@/lib/debt-aging";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount, formatPercent, formatSoum } from "@/lib/format-number";
import { useAccuracyReport } from "@/lib/occupancy-queries";
import { useReconciliationReport } from "@/lib/reconciliation-queries";
import {
  useReceivablesReport,
  useRevenueReport,
  useThreeWayReport,
} from "@/lib/report-queries";
import { useShiftReport } from "@/lib/shift-queries";

/*
 * =============================================================================
 * TEKSHIRUV UCHUN YIG'MA VARAQ — `Sbozor Direktor - Tekshiruv.dc.html`.
 *
 * Manba MCP orqali o'qildi (claude.ai/design `7bb95baa…`, 2026-08-19).
 *
 * ⛔⛔ VARAQNING BUTUN SHARTNOMASI BITTA JUMLADA (dizayndan AYNAN):
 *     «Bu varaqda YANGI RAQAM TUG'ILMAYDI — hammasi mavjud bloklardan
 *     yig'ilgan.»
 *
 *     Shuning uchun bu yerda hech narsa qayta hisoblanmaydi: har son
 *     o'zining endpointidan keladi va u qaysi blokdan olinganini
 *     «Batafsil →» havolasi ko'rsatadi. Yagona istisno — qarz yosh
 *     guruhlari (`debt-aging.ts`), va u ham mavjud maydonlardan
 *     GURUHLASH, yangi qiymat emas.
 *
 * ⛔⛔ CHOP ETISHGA TAYYOR: boshqaruv elementlari `data-noprint` bilan
 *     bosilmaydi, kartalar sahifa chegarasida bo'linmaydi
 *     (`.audit-break`), soya olib tashlanadi. Varaq tekshiruvchiga
 *     QOG'OZDA beriladi — ekran ko'rinishi yetarli emas.
 *
 * ⛔ DAVR TUGAMAGAN BO'LSA OGOHLANTIRISH CHIQADI va foizlar
 *    KO'RSATILMAYDI. Dizayn matni: «Varaqda faqat aniq summalar turadi».
 * =============================================================================
 */

/** Varaq davri — kechagi kun bilan tugaydigan oxirgi 30 kun. */
const WINDOW_DAYS = 30;

export function AuditSheet() {
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const now = useNow();

  const todayIso = businessDayIn(timeZone, now);
  const to = shiftIsoDay(todayIso, -1);
  const from = shiftIsoDay(to, -(WINDOW_DAYS - 1));

  const revenue = useRevenueReport({ from, to });
  const debtors = useReceivablesReport({ from, to });
  const leak = useReconciliationReport(to);
  const ledger = useThreeWayReport(to);
  const accuracy = useAccuracyReport({ from, to });
  const shifts = useShiftReport(to);

  const loading =
    revenue.isPending || debtors.isPending || leak.isPending || ledger.isPending;

  const periodTitle =
    revenue.data === undefined
      ? ""
      : `${formatBusinessDay(format, revenue.data.from_date, locale)} — ${formatBusinessDay(format, revenue.data.to_date, locale)}`;

  const money = (value: number): string => formatSoum(format, value, locale);

  /* --- Uchlik: hisoblangan / yig'ilgan / farq ---------------------------- */
  const charged = revenue.data?.total_charged_soum ?? 0;
  const collected = revenue.data?.total_collected_soum ?? 0;
  const diff = charged - collected;

  /* --- Farq tarkibi ------------------------------------------------------ */
  const debtTotal = debtors.data?.total_outstanding_soum ?? 0;
  const leakSum = leak.data?.unpaid_expected_soum ?? 0;
  const leakCount = leak.data?.unpaid_count ?? 0;

  /* --- Qarz yoshi -------------------------------------------------------- */
  const aging = sumByAge(debtors.data?.rows ?? [], todayIso);
  const oldest =
    debtors.data?.rows
      .map((row) => row.oldest_debt_date)
      .filter((value): value is string => value !== null)
      .sort()[0] ?? null;

  /* --- Smenalar ---------------------------------------------------------- */
  const shiftRows = shifts.data?.rows ?? [];
  const closedShifts = shiftRows.filter((row) => row.closed_at !== null).length;
  const shiftDiff = shiftRows.reduce((sum, row) => sum + row.variance_soum, 0);

  /* --- AI aniqligi ------------------------------------------------------- */
  const acc = accuracy.data;
  const accPoint = acc?.measured === true ? acc.correct.point : null;

  if (loading) {
    return (
      <div aria-busy="true" className="flex flex-col gap-4">
        <div className="audit-trio">
          <Skeleton className="dir-compare-skeleton" />
          <Skeleton className="dir-compare-skeleton" />
          <Skeleton className="dir-compare-skeleton" />
        </div>
        <Skeleton className="dir-trend-skeleton" />
      </div>
    );
  }

  return (
    <div className="audit-sheet flex flex-col gap-4">
      <header className="audit-head flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="dir-eyebrow">Tekshiruv uchun yig&apos;ma varaq</div>
          <h1 className="audit-title">{periodTitle}</h1>
          <p className="dir-tile-note">
            Tuzilgan: {formatBusinessDay(format, todayIso, locale)} ·{" "}
            {format.dateTime(now, { timeStyle: "short" })} (Toshkent) · direktor
            hisobidan
          </p>
        </div>

        <div className="flex flex-wrap justify-end gap-2" data-noprint="1">
          <Button
            onClick={() => {
              window.print();
            }}
            size="sm"
            variant="secondary"
          >
            Chop etish / PDF
          </Button>
        </div>
      </header>

      {/*
       * ⛔ MANBA BANNERI — varaqning shartnomasi. U olib tashlansa,
       *    tekshiruvchi bu raqamlar qayerdan kelganini so'rardi va
       *    javob varaqda bo'lmasdi.
       */}
      <div className="audit-source">
        <Badge tone="neutral">Manba</Badge>
        <p className="dir-tile-note">
          Bu varaqda yangi raqam tug&apos;ilmaydi — hammasi mavjud bloklardan
          yig&apos;ilgan. Har band yonidagi «Batafsil» dalil zanjiriga olib
          boradi: kun → rasta → to&apos;lov → kamera kadri → audit yozuvi.
        </p>
      </div>

      {/* --- Uchlik --------------------------------------------------------- */}
      <div className="audit-trio audit-break">
        <Card>
          <CardContent>
            <p className="audit-label">Hisoblangan</p>
            <p className="audit-value">{money(charged)}</p>
            <p className="dir-tile-note">Tarif × band rasta-kun</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <p className="audit-label">Yig&apos;ilgan</p>
            <p className="audit-value audit-value-ok">{money(collected)}</p>
            <p className="dir-tile-note">To&apos;lov yozuvlari · naqd va terminal</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            {/*
             * ⛔⛔ BELGI MA'NOLI — dizayn namunasida qarz DOIM musbat va
             *     shuning uchun farq qizil chiziladi. Real ma'lumotda
             *     yig'ilgan hisoblangandan KO'P bo'lishi mumkin (avans)
             *     va o'shanda qizil rang «yo'qotish» degan yolg'on
             *     xabar berardi.
             */}
            <p className="audit-label">Farq</p>
            <p
              className={
                diff > 0 ? "audit-value audit-value-diff" : "audit-value"
              }
            >
              {money(diff)}
            </p>
            <p className="dir-tile-note">
              {diff > 0
                ? "Tarkibi: qarzga yozilgan + band, to'lovsiz"
                : diff < 0
                  ? "Yig'ilgan hisoblangandan ko'p — avans"
                  : "Farq yo'q"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* --- Farq tarkibi --------------------------------------------------- */}
      <Card className="audit-break">
        <CardHeader>
          <h2 className="dir-trend-title">Farq nimadan tashkil topgan</h2>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <tbody>
                <tr className="border-b border-border">
                  <td className="p-3">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <Badge tone="danger">Qarz</Badge>
                      <span className="font-semibold">
                        Qarzga yozilgan hisoblar
                      </span>
                      <span className="dir-tile-note">
                        sotuvchi bo&apos;yicha reestrda ochiq
                      </span>
                    </div>
                  </td>
                  <td className="p-3 text-right font-mono font-semibold tabular-nums">
                    {money(debtTotal)}
                  </td>
                </tr>
                <tr className="border-b border-border">
                  <td className="p-3">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <Badge tone="warning">Band, to&apos;lovsiz</Badge>
                      <span className="font-semibold">
                        Nazoratchi ko&apos;rgan, hisob yozilmagan
                      </span>
                      <span className="dir-tile-note">
                        {formatAmount(format, leakCount, locale)} rasta
                      </span>
                    </div>
                  </td>
                  <td className="p-3 text-right font-mono font-semibold tabular-nums">
                    {money(leakSum)}
                  </td>
                </tr>
                <tr>
                  <td className="p-3 font-semibold">Farq jami</td>
                  <td className="p-3 text-right font-mono font-semibold tabular-nums text-danger-text">
                    {money(diff)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* --- Ikki ustun: daftar solishtiruvi va AI --------------------------- */}
      <div className="audit-cols2">
        <Card className="audit-break">
          <CardHeader>
            <h2 className="dir-trend-title">Qog&apos;oz daftar bilan solishtiruv</h2>
          </CardHeader>
          <CardContent>
            {ledger.data === undefined || !ledger.data.has_ledger ? (
              <p className="dir-tile-note">
                Bu kun uchun daftar kiritilmagan — solishtiruv o&apos;tkazilmadi.
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                <LedgerRow
                  count={ledger.data.matched_count}
                  format={format}
                  locale={locale}
                  name="daftar va tizim bir xil"
                  tag="Mos"
                  tone="success"
                />
                <LedgerRow
                  count={ledger.data.ledger_over_count}
                  format={format}
                  locale={locale}
                  name="tizimda yo'q yozuv"
                  tag="Daftar ortiq"
                  tone="warning"
                />
                <LedgerRow
                  count={ledger.data.system_over_count}
                  format={format}
                  locale={locale}
                  name="daftarda yo'q yozuv"
                  tag="Tizim ortiq"
                  tone="danger"
                />
              </div>
            )}
            <p className="dir-tile-note dir-compare-foot">
              Farqlar yashirilmaydi: daftar ortiq va tizim ortiq yozuvlar
              nomuvofiqlik navbatiga tushadi va nizo qarori bilan yopiladi.
            </p>
          </CardContent>
        </Card>

        <Card className="audit-break">
          <CardHeader>
            <h2 className="dir-trend-title">AI aniqligi va dalillar</h2>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap items-baseline gap-3">
                <p className="audit-value">
                  {accPoint === null ? "—" : formatPercent(accPoint * 100)}
                </p>
                <span className="dir-tile-note">
                  {acc === undefined ||
                  acc.correct.lower === null ||
                  acc.correct.upper === null
                    ? "ishonch oralig'i o'lchanmagan"
                    : `ishonch oralig'i ${formatPercent(acc.correct.lower * 100)} — ${formatPercent(acc.correct.upper * 100)}`}
                </span>
              </div>

              <StatRow
                label="Namuna hajmi"
                value={
                  acc === undefined
                    ? "—"
                    : `${formatAmount(format, acc.n, locale)} kadr`
                }
              />
              <StatRow
                label="Javobsiz qolgan"
                value={
                  acc === undefined
                    ? "—"
                    : formatAmount(format, acc.unanswered, locale)
                }
              />
              <StatRow
                label="Aniq ayta olmadi"
                value={
                  acc === undefined
                    ? "—"
                    : formatAmount(format, acc.dont_know, locale)
                }
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* --- Qarz holati va kassirlar --------------------------------------- */}
      <Card className="audit-break">
        <CardHeader>
          <h2 className="dir-trend-title">Qarz holati va kassirlar</h2>
        </CardHeader>
        <CardContent>
          <div className="audit-stats">
            <div>
              <p className="audit-label">Qarz jami</p>
              <p className="audit-value-sm audit-value-diff">
                {money(debtTotal)}
              </p>
              <p className="dir-tile-note">
                {debtors.data?.row_count ?? 0} sotuvchi
              </p>
            </div>

            <div>
              <p className="audit-label">90+ kunlik qarz</p>
              <p className="audit-value-sm audit-value-diff">
                {money(aging.b90)}
              </p>
              <p className="dir-tile-note">
                {oldest === null
                  ? "Eng eski sana o'lchanmagan"
                  : `Eng eski: ${formatBusinessDay(format, oldest, locale)}`}
              </p>
            </div>

            <div>
              <p className="audit-label">Yopilgan smenalar</p>
              <p className="audit-value-sm">
                {formatAmount(format, closedShifts, locale)}
              </p>
              <p className="dir-tile-note">
                {shiftRows.length - closedShifts === 0
                  ? "Ochiq qolgan smena yo'q"
                  : `${shiftRows.length - closedShifts} ta ochiq qolgan`}
              </p>
            </div>

            <div>
              <p className="audit-label">Deklaratsiya farqi</p>
              <p className="audit-value-sm dir-tile-diff">{money(shiftDiff)}</p>
              <p className="dir-tile-note">
                {shiftDiff === 0
                  ? "Farq yo'q"
                  : shiftDiff > 0
                    ? "Tizim ortiq"
                    : "Deklaratsiya ortiq"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function LedgerRow({
  tag,
  tone,
  name,
  count,
  format,
  locale,
}: {
  tag: string;
  tone: "success" | "warning" | "danger";
  name: string;
  count: number;
  format: ReturnType<typeof useFormatter>;
  locale: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border pb-2">
      <span className="flex items-center gap-2 text-sm">
        <Badge tone={tone}>{tag}</Badge>
        {name}
      </span>
      <span className="font-mono font-semibold tabular-nums">
        {formatAmount(format, count, locale)} yozuv
      </span>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3 border-b border-border pb-2 text-sm">
      <span className="text-text-muted">{label}</span>
      <span className="font-mono font-semibold tabular-nums">{value}</span>
    </div>
  );
}
