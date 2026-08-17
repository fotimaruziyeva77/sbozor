"use client";

import { useId } from "react";
import { useFormatter, useTranslations } from "next-intl";

import { useReportPeriod } from "@/components/reports/period-picker";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReceivablesReportRow } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { useReceivablesReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * QARZDORLIK RO'YXATI — ⛔ ISM SERVERDAN, BO'SHLIGI NOMLANGAN (§8.3, §8.4).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. SOTUVCHI ISMI BU KATALOGDA QONUNIY — VA BU QOIDA QO'SHNI
 *        KATALOGNIKIGA TESKARI (D-07, §5.5).
 * -----------------------------------------------------------------------
 * `components/reconciliation/**` da sotuvchi ismi maydonining O'ZI
 * ⛔ TAQIQ (G-36): u yerda qator sotuvchini IDENTIFIKATOR bilan aytadi
 * va yorliq alohida, audit qilingan reestr marshrutidan joinlanadi.
 *
 * ⛔ BU YERDA esa u RUXSAT — va sabab uchta:
 *   1. hisobot marshruti ⛔ OPERATIV emas, HUJJAT: qarzdorlik ro'yxati
 *      chop etiladi, imzolanadi va nizoda dalil bo'ladi — ismsiz varaq
 *      hech kimga tegishli bo'lmagan raqamlar ro'yxati bo'lardi;
 *   2. ism ⛔ SERVERDA joinlanadi, ya'ni klient IKKINCHI so'rov
 *      YUBORMAYDI;
 *   3. har hisobot so'rovi/eksporti ⛔ AYNAN BITTA `audit_read` yozadi —
 *      sotuvchi boshiga emas.
 *
 * ⚠⚠ IKKI KATALOG — IKKI RO'YXAT, va bu ochiq yozilishi SHART: ikkala
 *   katalogga bir xil taqiq ro'yxatini qo'llash D-07 ni BIRINCHI
 *   KUNIDAYOQ buzardi, teskarisi esa 7-fazaning himoyasini yumshatardi.
 *
 * ⛔ ALOQA MA'LUMOTI HAMON TAQIQ: telefon raqami, to'liq ism maydoni va
 *    Telegram identifikatori bu yuzaga ⛔ KIRMAYDI. Sabab: ro'yxatga
 *    faqat ISM kerak, aloqa ma'lumoti esa ⛔ EKSPORTGA tushib fayl bo'lib
 *    tarqalardi va qarz undirish oqimi allaqachon bot eslatmasida
 *    (BOT-03). ⚠ Taqiqlangan maydon NOMLARI bu izohda LITERAL
 *    yozilmaydi (kodbaza konvensiyasi — darvoza XOM `grep` bilan
 *    o'lchaydi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. TOPILMAGAN ISM — BO'SH KATAK (D-08).
 * -----------------------------------------------------------------------
 * ⛔ Na tire, na «tizim bilmaydi» degan to'qilgan yorliq, na raqamli
 *    o'rinbosar. Sabab (05-14 darsi): to'qilgan qiymat ⛔ MA'LUMOT
 *    BORDEK ko'rinadi va u ⛔ EKSPORTGA HAM TUSHADI — chop etilgan
 *    varaqdagi o'sha qator buxgalter uchun HAQIQIY sotuvchi nomi bo'lib
 *    o'qilardi va qarz ⛔ MAVJUD BO'LMAGAN odamga yozilardi. Bo'sh katak
 *    esa O'ZI SAVOL TUG'DIRADI va bu TO'G'RI natija.
 *
 * ⚠ LEKIN BO'SH `<td>` SKRINRIDERDA JIMGINA O'TADI — foydalanuvchi
 *   ustunni butunlay yo'qotardi. Shuning uchun katak ichida `sr-only`
 *   matn turadi: ⛔ VIZUAL jihatdan bo'sh, ⛔ SEMANTIK jihatdan
 *   NOMLANGAN. Bu 04-11 dagi «yo'q kadr uch kanalda» qarorining aynan
 *   sinfi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. JAMI QARZ Display OLMAYDI (§7.2).
 * -----------------------------------------------------------------------
 * U ⛔ SALBIY ko'rsatkich va uni davr tushumi bilan TENG kattalikda
 * chizish sahifani «ikki katta raqam, qaysi biri yaxshi?» qilardi.
 * Sahifada Display ⛔ AYNAN BITTA va u tushumniki.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. TARTIB VA YIG'INDI — SERVERNIKI.
 * -----------------------------------------------------------------------
 * Qatorlar qarz bo'yicha KAMAYISH tartibida keladi (direktorning
 * birinchi savoli — «eng kattasi kim?») va klient ularni ⛔ QAYTA
 * SARALAMAYDI. Yig'indi ham javobning O'Z maydoni: qatorlar ustidan
 * jamlash sahifalash tufayli ekrandagi 50 qatorni butun davr deb
 * ko'rsatardi (§8.6).
 * =============================================================================
 */

export function DebtorsReport() {
  const t = useTranslations();
  const format = useFormatter();

  const period = useReportPeriod();
  const report = useReceivablesReport(
    { from: period.from, to: period.to },
    { enabled: !period.isEmpty },
  );

  const periodId = useId();
  const rowsShownId = useId();

  const data = report.data;

  return (
    /* ⛔ Mazmun atributini ro'yxatning O'ZI chiqaradi (§8.1). */
    <div className="flex flex-col gap-3" data-report-content="debtors">
      <h2 className="text-lg font-semibold">{t("reports.debtorsTitle")}</h2>

      {report.isPending && !period.isEmpty ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
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
            <div className="flex flex-col gap-1">
              <dt className="text-xs text-text-muted">
                {t("reports.debtorsTotal")}
              </dt>
              {/*
               * ⛔ `text-lg`, ⛔ Display EMAS (§7.2). Rang kanali yolg'iz
               *   signal emas: ikkinchi kanal — «Qarz» ustun sarlavhasi
               *   (§13.4).
               */}
              <dd
                aria-describedby={`${periodId} ${rowsShownId}`}
                className="m-0 font-mono text-lg font-semibold text-danger-text tabular-nums"
              >
                {format.number(data.total_outstanding_soum)}{" "}
                <span className="font-sans text-sm font-normal text-text-muted">
                  {t("reports.amountUnit")}
                </span>
              </dd>
            </div>

            {/* ⛔ Davr JAVOBDAN (§8.7) — so'ralgan oraliqdan EMAS. */}
            <p className="text-xs text-text-muted" id={periodId}>
              {t("reports.periodShown", {
                from: data.from_date,
                to: data.to_date,
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
            <EmptyState
              description={t("reports.emptyDebtorsHint", {
                from: data.from_date,
                to: data.to_date,
              })}
              title={t("reports.emptyDebtors")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">
                  {t("reports.debtorsTitle")}
                </caption>
                <thead>
                  <tr className="border-b border-border text-left text-xs text-text-muted">
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.vendorColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.stallsColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.debtColumn")}
                    </th>
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.debtorsOldest")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, index) => (
                    <DebtorRow
                      key={row.vendor_id ?? `${row.stall_codes.join("-")}-${index}`}
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

/** Bitta qarzdor — ⛔ hamma qiymat javobning O'ZIDAN. */
function DebtorRow({ row }: { row: ReceivablesReportRow }) {
  const t = useTranslations();
  const format = useFormatter();

  return (
    /* Qator hover foni (§12.8) — davomiylik `--default-transition-*` dan. */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">
        {row.vendor_name === null ? (
          /*
           * ⛔ BO'SH KATAK — VIZUAL, LEKIN NOMLANGAN (§8.4). Bu yerda
           *   ko'rinadigan HECH QANDAY matn chizilmaydi: to'qilgan
           *   qiymat eksportga tushib, chop etilgan varaqda haqiqiy
           *   nom bo'lib o'qilardi.
           */
          <span className="sr-only">{t("reports.vendorUnknown")}</span>
        ) : (
          row.vendor_name
        )}
      </td>
      {/*
       * ⛔ RASTA KODLARI — javobdagi TARTIBDA. Klient saralamaydi:
       *   ekrandagi tartib eksportdagi tartibdan ajralsa, ikki hujjat
       *   solishtirib bo'lmas holga kelardi.
       */}
      <td className="p-3 font-mono tabular-nums">
        {row.stall_codes.join(", ")}
      </td>
      <td className="p-3 font-mono tabular-nums text-danger-text">
        {format.number(row.outstanding_soum)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {row.oldest_debt_date === null ? (
          /*
           * ⛔ O'LCHANMAGAN SANA HAM TO'QILMAYDI (D-10): «bugun» yoki
           *   davr boshini yozish o'lchanmagan faktni O'LCHANGAN qilib
           *   ko'rsatardi. Bo'sh katak — NOMLANGAN, ismnikidek.
           */
          <span className="sr-only">{t("reports.dateUnknown")}</span>
        ) : (
          formatBusinessDay(format, row.oldest_debt_date)
        )}
      </td>
    </tr>
  );
}
