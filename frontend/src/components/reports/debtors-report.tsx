"use client";

import { useId } from "react";
import {
  useFormatter,
  useLocale,
  useNow,
  useTimeZone,
  useTranslations,
} from "next-intl";

import { useReportPeriod } from "@/components/reports/period-picker";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReceivablesReportRow } from "@/lib/api-types";
import { businessDayIn } from "@/components/snapshots/day-picker";
import { Badge } from "@/components/ui/badge";
import { type AgeBucket, bucketOf } from "@/lib/debt-aging";
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

/** Guruh -> matn kaliti. ⛔ YOPIQ to'plam: beshinchi guruh yo'q. */
const AGE_LABEL = {
  b0: "reports.ageBucket0",
  b31: "reports.ageBucket31",
  b61: "reports.ageBucket61",
  b90: "reports.ageBucket90",
} as const satisfies Record<AgeBucket, string>;

export function DebtorsReport() {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

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
              {/*
               * ⛔⛔ BELGI MA'NOLI — MANFIY QOLDIQ QARZ EMAS (260818).
               *
               * `report_repo` `outstanding_soum <> 0` filtri bilan
               * ishlaydi, ya'ni ORTIQCHA TO'LOV ham qaytadi. Har qanday
               * qiymatni qizil chizish direktorga avansni qarz deb
               * o'qitardi va «jami qarz» sof qoldiq bo'lgani holda
               * qarz deb nomlanardi.
               */}
              <dd
                aria-describedby={`${periodId} ${rowsShownId}`}
                className={
                  data.total_outstanding_soum > 0
                    ? "m-0 font-mono text-lg font-semibold text-danger-text tabular-nums"
                    : "m-0 font-mono text-lg font-semibold tabular-nums"
                }
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
                /* ⛔ Xom ISO EMAS — `anomaly-archive.tsx` bilan bir qoida. */
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
            <EmptyState
              description={t("reports.emptyDebtorsHint", {
                /* ⛔ XOM ISO EMAS — bu qator ekranda «2026-07-19 — 2026-08-17»
                 *    bo'lib chiqardi, holbuki yonidagi jadval sanalari
                 *    «19-iyul, 2026» edi. Bir sahifada ikki xil sana yo'li. */
                from: formatBusinessDay(format, data.from_date, locale),
                to: formatBusinessDay(format, data.to_date, locale),
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
                    {/*
                     * ⛔⛔ YOSH USTUNI — DIZAYN TALABI (Hisobot ekrani).
                     *
                     * Server yosh guruhlarini BERMAYDI; guruh qatorning
                     * `oldest_debt_date` idan chiqadi (`debt-aging.ts`).
                     * Ustun «shu yoshdagi qarzdorning JAMI qarzi» ni
                     * bildiradi — qarzni sanalar bo'yicha taqsimlash
                     * ma'lumoti bizda YO'Q va uni to'qish mumkin emas.
                     */}
                    <th className="p-3 font-normal" scope="col">
                      {t("reports.debtAge")}
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
  const locale = useLocale();

  const timeZone = useTimeZone() ?? "Asia/Tashkent";
  const todayIso = businessDayIn(timeZone, useNow());
  const bucket = bucketOf(row, todayIso);

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
      <td className="p-3">
        {/*
         * ⛔ O'LCHANMAGAN YOSH — BO'SH KATAK, «0–30 kun» EMAS: eng yosh
         *    guruhga qo'yish o'lchanmagan qarzni yangi deb ko'rsatardi.
         */}
        {bucket === null ? (
          <span className="sr-only">{t("reports.dateUnknown")}</span>
        ) : (
          <Badge tone={bucket === "b90" ? "danger" : bucket === "b61" ? "warning" : "muted"}>
            {t(AGE_LABEL[bucket])}
          </Badge>
        )}
      </td>
      <td
        className={
          row.outstanding_soum > 0
            ? "p-3 font-mono tabular-nums text-danger-text"
            : "p-3 font-mono tabular-nums"
        }
      >
        {format.number(row.outstanding_soum)}
        {/* ⛔ Rang yolg'iz signal EMAS (§13.4) — belgi MATN bilan ham. */}
        {row.outstanding_soum < 0 ? (
          <span className="sr-only"> {t("reports.overpaid")}</span>
        ) : null}
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
          formatBusinessDay(format, row.oldest_debt_date, locale)
        )}
      </td>
    </tr>
  );
}
