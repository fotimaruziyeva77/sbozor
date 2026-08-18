"use client";

import { useId } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { useReportPeriod } from "@/components/reports/period-picker";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { AnomalyArchiveRow } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { useAnomalyArchive } from "@/lib/report-queries";

/*
 * =============================================================================
 * NOMUVOFIQLIK ARXIVI — ⛔ IKKI SINF, IKKI SANOQ, KADRSIZ DALIL (§8.5).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. BITTA JADVAL — LEKIN IKKITA YIG'INDI.
 * -----------------------------------------------------------------------
 * Qatorlar BITTA jadvalda, `kind` ustuni bilan chiziladi va sabab
 * ATAYIN yozib qoldiriladi: arxivda davr bo'ylab ⛔ XRONOLOGIYA muhim —
 * direktor «21-sentabrda nima bo'ldi?» deb qaraydi, «to'lovsizlar
 * ro'yxatini ko'rsat» deb emas. Ikki alohida jadval bir kunning
 * hodisalarini ⛔ IKKI JOYDA qidirtirardi va o'sha kunning umumiy
 * manzarasi hech qachon bir ekranda ko'rinmasdi.
 *
 * ⛔⛔ LEKIN YIG'INDI IKKITA VA ULAR HECH QACHON QO'SHILMAYDI [MEROS:
 *     07 Pattern 4, G-30]. Ikki sinf ⛔ IKKI XIL NARSANI o'lchaydi:
 *
 *       «band, lekin to'lovsiz» — ⛔ HOSILA: ertaga to'lov kelsa, qator
 *                                 arxivdan YO'QOLADI (u ayirmadan chiqadi);
 *       «ro'yxatga olinmagan savdo» — ⛔ QATOR: u yozilgan hodisa va
 *                                 QOLAVERADI.
 *
 *     Ularni bitta songa siqish «bugun 5 ta nomuvofiqlik» degan ⛔ SOXTA
 *     ko'rsatkich yaratardi: ertasi kuni to'lovlar kelib son 2 ga tushardi
 *     va direktor buni «tuzatildi» deb o'qirdi, holbuki yozilgan hodisalar
 *     joyida qolgan bo'lardi. Shuning uchun ikki sanoq ⛔ ALOHIDA atama
 *     bilan, ALOHIDA matn tugunida chiziladi va ularning yig'indisi bu
 *     yuzada ⛔ UMUMAN HISOBLANMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. DALIL — HAVOLA, KADR EMAS [MEROS: 07 D-03].
 * -----------------------------------------------------------------------
 * Dalil ustunida ⛔ RASM CHIZILMAYDI va bu katalogda rasm chizishning
 * ⛔ BIRORTA usuli ham yozilmaydi. Sabab ikki qatlamli:
 *
 *   1. ⛔ MEXANIK (M-7): sessiya tokeni so'rov SARLAVHASIDA yashaydi,
 *      cookie'da emas — ya'ni brauzerning o'zi ochadigan kadr manzili
 *      TOKENSIZ ketardi va `401` olardi. «Tuzatish» esa ijrochini kadrni
 *      SAHIFAGA qo'yishga undardi, ya'ni taqiqni AYLANIB O'TARDI;
 *   2. ⛔ CHEGARA (D-03): kadr baytlari hisobot yuzasidan CHIQMAYDI va
 *      ⛔ EKSPORTGA ham faqat IDENTIFIKATOR tushadi. Chop etilgan
 *      hisobotga kadr tushishi shaxsiy ma'lumot rejimini butunlay
 *      o'zgartirardi.
 *
 * ⛔ Shuning uchun ustun `EvidenceLink` ni QAYTA ISHLATADI: u
 *    ALLAQACHON mavjud `/billing` yuzasiga (kun bo'yicha) yo'naltiradi,
 *    huquqni O'ZI tekshiradi va yangi kadr marshruti ochmaydi. Ikkinchi
 *    dalil komponenti yozish M-11 ning bevosita buzilishi bo'lardi.
 *
 * ⚠ DALILSIZ QATORDA KATAK BO'SH QOLADI — platsholder ham, `sr-only` nom
 *   ham qo'yilmaydi, va bu 08-13 dagi «bo'sh katak NOMLANADI» qoidasidan
 *   ATAYIN farq qiladi. Farq mazmunda: u yerda bo'shlik MA'LUMOTNING
 *   yo'qligi edi (sotuvchi ismi — qatorning fakti), bu yerda esa
 *   AMALNING yo'qligi (ochiladigan yuza yo'q). Mavjud bo'lmagan amalni
 *   skrinriderda e'lon qilish foydalanuvchini yo'q havolani qidirishga
 *   yuborardi (07 D-03 ning 4-bandi).
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. CASE HOLATI — MAVJUD REYESTR, YANGI KALIT YO'Q.
 * -----------------------------------------------------------------------
 * Holat ustuni `CaseStatusBadge` ni qayta ishlatadi: yopiq 4 a'zo
 * (07 D-12), ularning rang/ikonka kanallari va ⛔ NOMA'LUM qiymat uchun
 * ZAXIRA YORLIG'I allaqachon o'sha komponentda. Sxema qiymatni
 * reyestr bilan qulflamagan, ya'ni server beshinchi a'zo qo'shsa u shu
 * yerga yetib keladi — qatorni chizmaslik uni ro'yxatdan ⛔ JIMGINA
 * yo'qotardi va davr sanog'i bilan jadval ajralib qolardi (WR-13 ning
 * shu yuzadagi takrori).
 *
 * ⚠ `case_status` `null` bo'lishi ham QONUNIY: nomuvofiqlik navbatga
 *   `overdue_days` chegarasidan keyin tushadi, ya'ni chegaragacha qator
 *   ATAYIN navbatsiz turadi. Bu «noma'lum holat» EMAS va badge ikkalasini
 *   AJRATADI.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. DAVR VA MAXRAJ — SERVERDAN (§8.6, §8.7).
 * -----------------------------------------------------------------------
 * Ekrandagi «{from} — {to}» javobning O'Z maydonlaridan; «{shown}
 * qatordan {total} tasi» esa MAJBURIY — usiz direktor ekrandagi 50
 * qatorni butun davr deb o'qirdi, ikki sanoq esa butun davrniki bo'lardi.
 * Ikkala sanoq ham shu ikki jumlaga `aria-describedby` bilan bog'lanadi.
 * =============================================================================
 */

/** ⛔ ARXIVNING IKKI SINFI — `ANOMALY_KINDS` (hodisaning uch TURI) EMAS. */
const KIND_LABEL = {
  unpaid: "reports.anomaliesUnpaid",
  unregistered: "reports.anomaliesUnregistered",
} as const;

type ArchiveKind = keyof typeof KIND_LABEL;

function isArchiveKind(value: string): value is ArchiveKind {
  return Object.hasOwn(KIND_LABEL, value);
}

export function AnomalyArchive() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  /* ⚠ Davr HOOKDAN, propdan emas (08-13 naqshi): sahifa bilan blok
   *   orasida uchinchi haqiqat manbai tug'ilmaydi. */
  const period = useReportPeriod();
  const report = useAnomalyArchive(
    { from: period.from, to: period.to },
    { enabled: !period.isEmpty },
  );

  const periodId = useId();
  const rowsShownId = useId();

  const data = report.data;

  return (
    /* ⛔ Mazmun atributini ro'yxatning O'ZI chiqaradi (§8.1, G-29(b)). */
    <div className="flex flex-col gap-3" data-report-content="anomalies">
      <h2 className="text-lg font-semibold">{t("reports.anomaliesTitle")}</h2>

      {report.isPending && !period.isEmpty ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
        /*
         * ⛔ YIQILGAN SO'ROV BO'SH JADVAL BO'LIB CHIZILMAYDI (D-10,
         *   WR-05 sinfi): bo'sh arxiv «bu davrda nomuvofiqlik yo'q»
         *   degan YOLG'ON faktni berardi — ya'ni eng yaxshi natijaga
         *   O'XSHAGAN nosozlik.
         */
        <p
          className="flex flex-col gap-1 rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          <span>{t("errors.loadFailedTitle")}</span>
          <span>{t("errors.loadFailedBody")}</span>
        </p>
      ) : null}

      {data !== undefined ? (
        <>
          <dl className="flex flex-col gap-1">
            <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
              {/*
               * ⛔ IKKI ATAMA — IKKI QIYMAT. Ular ⛔ YONMA-YON turadi,
               *   lekin ⛔ HECH QACHON qo'shilmaydi (yuqoridagi 1-band).
               *   ⛔ Display ham OLMAYDI: sahifadagi yagona Display davr
               *   tushuminiki (§7.2).
               */}
              <div className="flex flex-col gap-1">
                <dt className="text-xs text-text-muted">
                  {t("reports.anomaliesUnpaid")}
                </dt>
                <dd
                  aria-describedby={`${periodId} ${rowsShownId}`}
                  className="m-0 font-mono text-sm font-semibold tabular-nums"
                >
                  {format.number(data.unpaid_count)}
                </dd>
              </div>

              <div className="flex flex-col gap-1">
                <dt className="text-xs text-text-muted">
                  {t("reports.anomaliesUnregistered")}
                </dt>
                <dd
                  aria-describedby={`${periodId} ${rowsShownId}`}
                  className="m-0 font-mono text-sm font-semibold tabular-nums"
                >
                  {format.number(data.unregistered_count)}
                </dd>
              </div>
            </div>

            {/* ⛔ Davr JAVOBDAN (§8.7) — so'ralgan oraliqdan EMAS. */}
            <p className="text-xs text-text-muted" id={periodId}>
              {t("reports.periodShown", {
                /*
                 * ⛔ XOM ISO EMAS (Topilma №2): `from_date`/`to_date`
                 *    javobda `YYYY-MM-DD` bo'lib keladi va to'g'ridan-
                 *    to'g'ri xabarga uzatilsa ekranda shundayligicha
                 *    chiqardi — o'sha bir sahifadagi jadval sanalari
                 *    esa «19-iyul, 2026» ko'rinishida edi.
                 */
                from: formatBusinessDay(format, data.from_date, locale),
                to: formatBusinessDay(format, data.to_date, locale),
              })}
            </p>

            <p className="text-xs text-text-muted" id={rowsShownId}>
              {t("reports.rowsShown", {
                shown: data.shown_count,
                total: data.row_count,
              })}
            </p>
          </dl>

          {data.rows.length === 0 ? (
            /*
             * ⛔ BO'SH DAVR — NOMLANGAN HOLAT (§14.7 bo'sh holat 3),
             *   sarlavhalari bor bo'sh jadval EMAS. ⛔ `action` YO'Q:
             *   davrni o'zgartirish keyingi QADAM emas, u allaqachon
             *   ekranda.
             */
            <EmptyState
              description={t("reports.emptyAnomaliesHint", {
                /* ⛔ XOM ISO EMAS — bu qator ekranda «2026-07-19 — 2026-08-17»
                 *    bo'lib chiqardi, holbuki yonidagi jadval sanalari
                 *    «19-iyul, 2026» edi. Bir sahifada ikki xil sana yo'li. */
                from: formatBusinessDay(format, data.from_date, locale),
                to: formatBusinessDay(format, data.to_date, locale),
              })}
              title={t("reports.emptyAnomalies")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">
                  {t("reports.anomaliesTitle")}
                </caption>
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.dateColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.kindColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.stallColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.evidenceColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.statusColumn")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, index) => (
                    <ArchiveRow
                      key={`${row.business_date}-${row.stall_code}-${index}`}
                      row={row}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

/** Arxivning bitta qatori — ⛔ hamma qiymat javobning O'ZIDAN. */
function ArchiveRow({ row }: { row: AnomalyArchiveRow }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    /* Qator hover foni (§12.8) — davomiylik `--default-transition-*` dan. */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">{formatBusinessDay(format, row.business_date, locale)}</td>

      {/*
       * ⛔ NOMA'LUM SINF QATORNI YO'QOTMAYDI: yorliq topilmasa XOM kod
       *   chiziladi. Qatorni tashlab yuborish jadval bilan sanoqni
       *   JIMGINA ajratardi — «12 qatordan 4 tasi» deyilgan joyda 3 ta
       *   qator ko'rinardi va farqni hech kim tushuntira olmasdi.
       */}
      <td className="p-3">
        {isArchiveKind(row.kind) ? t(KIND_LABEL[row.kind]) : row.kind}
      </td>

      <td className="p-3 font-mono tabular-nums">{row.stall_code}</td>

      {/*
       * ⛔ DALIL — MAVJUD YUZAGA HAVOLA (yuqoridagi 2-band). Identifikator
       *   massiv shaklida uzatiladi: `EvidenceLink` bo'sh ro'yxatda
       *   ⛔ HECH NIMA chizmaydi va bu ATAYIN.
       */}
      <td className="p-3">
        <EvidenceLink
          serviceDate={row.business_date}
          snapshotIds={row.snapshot_id === null ? [] : [row.snapshot_id]}
        />
      </td>

      <td className="p-3">
        <CaseStatusBadge status={row.case_status} />
      </td>
    </tr>
  );
}
