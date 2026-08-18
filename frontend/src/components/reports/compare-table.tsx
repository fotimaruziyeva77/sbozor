"use client";

import { Fragment } from "react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { DIFF_ORDER, DIFF_VIEW, DiffCell } from "@/components/reports/diff-cell";
import {
  LEDGER_FILE_INPUT_ID,
  useCompareDay,
} from "@/components/reports/ledger-import";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { DiffClassValue, ThreeWayReport, ThreeWayRow } from "@/lib/api-types";
import { formatBusinessDay } from "@/lib/format-day";
import { useThreeWayReport } from "@/lib/report-queries";

/*
 * =============================================================================
 * UCH TOMONLAMA SOLISHTIRUV JADVALI (§10.4–§10.6, §13.4, §7.3).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 1. DAFTAR YO'Q -> JADVAL ⛔ UMUMAN CHIZILMAYDI (§10.6, D-10)
 * -----------------------------------------------------------------------
 * ⛔ BU FAYLDAGI ENG QIMMAT BAND. Daftar yuklanmagan kunda uch ustunli
 *    jadvalni «hamma farq 0» bilan chizish ⛔ MUVAFFAQIYATLI SOLISHTIRUV
 *    bo'lib ko'rinardi va u ⛔ IMZOLANARDI — ya'ni parallel rejimning
 *    butun maqsadi (SC#5) ⛔ JIMGINA yo'qolardi. Bu WR-05 sinfining eng
 *    qimmat ko'rinishi: o'lchanmagan holat o'lchangan bo'lib qog'ozga
 *    chiqadi va nizoda dalil bo'lib ishlatiladi.
 *
 * ⛔ Shuning uchun `has_ledger === false` shoxida jadval ham, uch sanoq
 *    ham, maxraj jumlasi ham chizilmaydi — faqat ⛔ NOMLANGAN HOLAT va
 *    keyingi qadam (bo'sh holat 6, §14.7 dagi YAGONA `action` li holat).
 *
 * ⚠ Mazmun atributi (`data-compare-content`) esa ⛔ HAR HOLATDA eng
 *   tashqi elementda: blok darvozasi (G-37(b)) blokning MAZMUNI borligini
 *   o'lchaydi, jadval borligini emas. Aks holda daftarsiz kun butun
 *   darvozani qizartirardi va keyingi ijrochi uni bo'shatardi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. `null` VA `0` — IKKI XIL NARSA (§10.4, D-10)
 * -----------------------------------------------------------------------
 *     `null` = «o'sha kun uchun bandlik ma'lumoti YO'Q» (⛔ O'LCHANMAGAN)
 *     `0`    = «AI rastani BO'SH dedi»                  (⛔ O'LCHANGAN)
 *
 * ⛔ Ularni tenglashtirish D-10 ning ⛔ BEVOSITA buzilishi: o'lchanmagan
 *    miqdor o'lchangan bo'lib chizilardi va imzolanadigan varaqqa
 *    tushardi. Ekranda `null` — ⛔ BO'SH katak, `0` — chizilgan nol.
 *
 * ⚠ LEKIN BUTUNLAY BO'SH `<td>` SKRINRIDERDA JIMGINA O'TADI —
 *   foydalanuvchi ustunni butunlay yo'qotardi. Shuning uchun katak
 *   ichida `sr-only` NOM turadi: ⛔ VIZUAL jihatdan bo'sh, ⛔ SEMANTIK
 *   jihatdan NOMLANGAN (08-13 dagi `vendor_name` qarorining aynan
 *   sinfi).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. UCH SANOQ ⛔ HECH QACHON QO'SHILMAYDI (§10.5)
 * -----------------------------------------------------------------------
 * Uch sinf uch ⛔ TURLI harakat talab qiladi: «pulni qidiring» /
 * «daftarni tuzating» / «detektorni tekshiring». Bitta «jami farq»
 * soniga siqish solishtiruvni ⛔ FOYDASIZ qilardi — 6-faza D-05 va
 * 07 Pattern 4 ning aynan sinfi.
 *
 * ⛔ Shuning uchun har sanoq ⛔ O'Z TUGUNIDA (`data-diff-count`) va u
 *    reyestrdan (`DIFF_CLASSES`) ITERATSIYA bilan chiziladi.
 *
 * ⚠⚠ NEGA `compare.diffCounts` CHAQIRILMAYDI — ⛔ O'LCHANGAN SABAB:
 *   `next-intl` da ICU platsholderining qiymati `string | number | Date`
 *   (`use-intl/…/TranslationValues.d.ts`), ⛔ `ReactNode` EMAS. Ya'ni
 *   `t("compare.diffCounts", …)` uch sanoqni ⛔ BITTA matn tuguniga
 *   qo'yardi va «uch alohida tugun» sharti (G-41(c)) ⛔ MEXANIK
 *   jihatdan bajarilmas bo'lardi. Kalitning O'ZI katalogda QOLADI: u
 *   G-43(d) da uchala locale bo'yicha qulflangan ⛔ KANONIK jumla va shu
 *   yerdagi uch tugun aynan o'sha jumlani (ayni yorliqlar, ayni `·`
 *   ajratgich) qayta quradi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 4. «MOS» QATORI QOLADI (§10.5) VA MAXRAJ MAJBURIY
 * -----------------------------------------------------------------------
 * «300 rastadan 287 tasi mos» — maxraj imzolanadigan hujjatda majburiy:
 * usiz 13 qatorli varaq ⛔ «bozorda 13 ta rasta bor» bo'lib o'qilardi
 * (07 G-32 darsi). Bezakni esa u OLMAYDI — `diff-cell.tsx` ning izohi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 5. UCH PUL USTUNI VA RASTA KODI — `font-mono` (§7.3)
 * -----------------------------------------------------------------------
 * Ular ⛔ VERTIKAL solishtiriladi: proporsional shriftda «411» va «14»
 * turli kenglikda chiziladi va ko'z ustunni skanerlay olmasdi.
 *
 * ⛔ KLIENT HECH NIMA HISOBLAMAYDI (D-03): sanoqlar ham, maxraj ham
 *    javobning O'Z maydonlari. Qatorlar ustidan yurib jamlash
 *    sahifalash tufayli ekrandagi qatorlarni butun kun deb ko'rsatardi.
 * =============================================================================
 */

/**
 * Sinf -> javobdagi sanoq maydoni.
 *
 * ⛔ `Record<DiffClassValue, …>` ATAYIN: reyestrga a'zo qo'shilsa bu
 *    jadval `tsc` da qizaradi va yangi sinf ⛔ SANOQSIZ ekranga chiqa
 *    olmaydi (ya'ni «uchala sanoq bor» da'vosi jimgina to'rttaga
 *    aylanmaydi).
 */
const COUNT_OF: Record<DiffClassValue, (report: ThreeWayReport) => number> = {
  ledger_over: (report) => report.ledger_over_count,
  system_over: (report) => report.system_over_count,
  ai_mismatch: (report) => report.ai_mismatch_count,
};

/**
 * Bo'sh holat 6 ning amali — ⛔ FOKUSNI daftar maydoniga ko'chiradi.
 *
 * ⛔ HAVOLA EMAS: `components/reports/**` da havola tokenlari 0
 *    (G-38(a)) va sabab §12.2 da — bu yuzada brauzerning O'Z navigatsiya
 *    yo'llari tokensiz ketadi. ⚠ Fokus ko'chirish bu yerda ⛔ YAXSHIROQ
 *    javob ham: skrinrider sakrashni E'LON qiladi, sahifa esa jimgina
 *    siljib qolmaydi (brauzer fokuslangan elementni o'zi ko'rinishga
 *    keltiradi).
 */
function focusLedgerUpload(): void {
  document.getElementById(LEDGER_FILE_INPUT_ID)?.focus();
}

export function CompareTable() {
  const t = useTranslations();

  const { day } = useCompareDay();
  const report = useThreeWayReport(day);

  const data = report.data;

  return (
    /* ⛔ Mazmun atributini jadvalning O'ZI chiqaradi (§10.1, G-37(b)). */
    <div className="flex flex-col gap-3" data-compare-content="comparison">
      <h2 className="text-lg font-semibold">{t("compare.title")}</h2>

      {report.isPending ? (
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

      {data === undefined ? null : data.has_ledger ? (
        <LedgerDay data={data} />
      ) : (
        /*
         * ⛔ NOMLANGAN HOLAT — «hamma farq 0» EMAS (yuqoridagi 1-band).
         *   Bu §14.7 dagi ⛔ YAGONA `action` li bo'sh holat: qolgan
         *   beshtasida foydalanuvchi qiladigan keyingi qadam YO'Q.
         */
        <EmptyState
          action={
            <Button onClick={focusLedgerUpload} variant="secondary">
              {t("compare.ledgerUpload")}
            </Button>
          }
          description={t("compare.ledgerMissingHint")}
          title={t("compare.ledgerMissing")}
        />
      )}
    </div>
  );
}

/** Daftar YUKLANGAN kun — sanoqlar, maxraj va jadval. */
function LedgerDay({ data }: { data: ThreeWayReport }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  if (data.rows.length === 0) {
    /*
     * ⛔ «Daftar bor, qator yo'q» — ⛔ UCHINCHI holat (§10.6) va u
     *   daftarsiz kundan FARQ QILADI: bu yerda admin faylni yuklagan,
     *   lekin fayl bo'sh chiqqan. Ikkalasini bir xil matn bilan
     *   ko'rsatish adminni faylni qayta yuklashga majburlardi — holbuki
     *   muammo faylning ICHIDA.
     */
    return (
      <EmptyState
        description={t("compare.ledgerEmptyHint", {
          day: formatBusinessDay(format, data.day, locale),
        })}
        title={t("compare.ledgerEmpty")}
      />
    );
  }

  return (
    <>
      {/*
       * ⛔ UCH SANOQ + MAXRAJ — BIR JOYDA. Ajratilsa direktor sanoqlarni
       *   ko'rib maxrajni O'QIMASDAN xulosa chiqarardi (07 G-32 darsi).
       */}
      <div className="flex flex-col gap-1" data-compare-summary="">
        <p className="text-xs text-text-muted">
          {DIFF_ORDER.map((cls, index) => (
            <Fragment key={cls}>
              {index > 0 ? " · " : null}
              <span data-diff-count={cls}>
                {t(DIFF_VIEW[cls].labelKey)}:{" "}
                <span className="font-mono tabular-nums">
                  {format.number(COUNT_OF[cls](data))}
                </span>
              </span>
            </Fragment>
          ))}
        </p>

        {/* ⛔ MAXRAJ MAJBURIY — «13 ta farq» varaqda «13 ta rasta» emas. */}
        <p className="text-xs text-text-muted">
          {t("compare.matched", { matched: data.matched_count })}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">{t("compare.title")}</caption>
          <thead>
            <tr className="border-b border-border text-left text-xs text-text-muted">
              <th className="p-3 font-normal" scope="col">
                {t("reports.stallColumn")}
              </th>
              <th className="p-3 font-normal" scope="col">
                {t("compare.ledger")}
              </th>
              <th className="p-3 font-normal" scope="col">
                {t("compare.system")}
              </th>
              <th className="p-3 font-normal" scope="col">
                {t("compare.aiExpected")}
              </th>
              <th className="p-3 font-normal" scope="col">
                {t("compare.diffColumn")}
              </th>
            </tr>
          </thead>
          <tbody>
            {/*
             * ⛔ TARTIB SERVERNIKI — klient QAYTA SARALAMAYDI: ekrandagi
             *   tartib eksportdagidan ajralsa, ikki hujjatni yonma-yon
             *   solishtirib bo'lmasdi (§12.6: ular BIRGA imzolanadi).
             */}
            {data.rows.map((row) => (
              <CompareRow key={row.stall_code} row={row} />
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/** Bitta rasta — ⛔ hamma qiymat javobning O'ZIDAN (D-03). */
function CompareRow({ row }: { row: ThreeWayRow }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  return (
    /*
     * Qator hover foni (§12.8). `DiffCell` badge'i inline element — o'z
     * fonini hover USTIDA saqlaydi, farq signali bosilmaydi.
     */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3 font-mono tabular-nums">{row.stall_code}</td>
      <td className="p-3 font-mono tabular-nums">
        {format.number(row.ledger_soum)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {format.number(row.system_soum)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {row.ai_expected_soum === null ? (
          /*
           * ⛔ O'LCHANMAGAN BANDLIK — VIZUAL BO'SH, SEMANTIK NOMLANGAN
           *   (yuqoridagi 2-band). ⛔ Nol YOZILMAYDI: u «AI rastani bo'sh
           *   dedi» degan BOSHQA, O'LCHANGAN faktning belgisi.
           */
          <span className="sr-only">{t("compare.aiNotMeasured")}</span>
        ) : (
          format.number(row.ai_expected_soum)
        )}
      </td>
      <td className="p-3">
        {/* ⛔ «Mos» qatorida bu katak BO'SH qoladi — `diff-cell.tsx`. */}
        <DiffCell diffClass={row.diff_class} />
      </td>
    </tr>
  );
}
