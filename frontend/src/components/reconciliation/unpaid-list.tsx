"use client";

import { Receipt } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportRow } from "@/lib/reconciliation-queries";
import { useReconciliationReport } from "@/lib/reconciliation-queries";
import { useVendorLabels } from "@/lib/vendor-labels";

/*
 * =============================================================================
 * B BLOKI — ⛔ SINF A: «BAND, LEKIN TO'LOVSIZ».
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ IKKI SINF — IKKI KOMPONENT, IKKI BLOK VA ULAR HECH QACHON
 *     QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * Sinf A — ⛔ HOSILA (`daily_charges` − `payments`): ertaga to'lov kelsa
 * qator ⛔ YO'QOLADI. Sinf B — ⛔ QATOR (`billing_anomalies`): u
 * ⛔ QOLAVERADI.
 *
 * Bitta songa qo'shish ikki xil ⛔ UMR KO'RADIGAN narsani teng qilardi.
 * Va undan qimmatrog'i: sinf B da summa ⛔ UMUMAN YO'Q (biriktirilmagan
 * zonaning tarifi bilinmaydi), ya'ni yig'indi ⛔ NOL QO'SHIB hisoblanardi
 * va u ⛔ KAM KO'RSATILGAN YO'QOTISH bo'lardi — ya'ni hisobot direktorni
 * XOTIRJAM qilardi, holbuki yo'qotish kattaroq.
 *
 * ⛔ Shuning uchun bu faylda ham, qo'shni faylda ham «umumiy jami»
 *    ma'nosini beradigan BIRORTA nom yozilmaydi va uning yo'qligi
 *    mexanik skan bilan o'lchanadi. ⚠ Taqiqlangan nomlar bu izohda
 *    LITERAL yozilmaydi (kodbaza konvensiyasi).
 *
 * -----------------------------------------------------------------------
 * ⛔ HAR BLOK O'Z MAZMUN ATRIBUTINI O'ZI CHIQARADI, SAHIFA EMAS
 * -----------------------------------------------------------------------
 * Sabab O'LCHANGAN (06-fazaning darvozasi): faqat blok atributlarining
 * TO'PLAMINI tekshiradigan darvoza ⛔ BO'SH O'RAMNI MUKAMMAL o'tkazardi —
 * ya'ni butun yuza ⛔ CHIZILMAGAN holda darvoza, task VA faza YASHIL
 * qaytardi. Atribut sahifada bo'lsa, sahifa o'z false-green iga o'zi yo'l
 * ochardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ SOTUVCHI ISMI SERVERDAN KELMAYDI
 * -----------------------------------------------------------------------
 * Qator sotuvchini IDENTIFIKATOR bilan aytadi; yorliq esa MAVJUD va
 * AUDIT QILINGAN reestr marshrutidan, `lib/vendor-labels.ts` da
 * joinlanadi. Bu yerda shaxsiy maydonning NOMI ham uchramaydi.
 *
 * ⛔ ARIFMETIKA YO'Q: qarz serverdan KELGAN ikki sondan chiziladi va
 *    ularning birortasi ham klientda qayta hisoblanmaydi. `null` esa
 *    ⛔ NOLGA aylantirilmaydi — «yo'q summa» YO'Q SUMMA bo'lib qoladi.
 * =============================================================================
 */

/** Sinf A ning diskriminatori — YOPIQ qiymat, «qaysi ustun bo'sh?» EMAS. */
const SUBJECT = "occupied_unpaid";

export function UnpaidList({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const report = useReconciliationReport(day);
  const vendors = useVendorLabels();

  const rows = (report.data?.rows ?? []).filter(
    (row) => row.subject_kind === SUBJECT,
  );

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <div className="flex flex-col gap-3" data-recon-content="unpaid">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">{t("recon.unpaidTitle")}</h2>
        <Badge className="gap-1" tone="danger">
          <Receipt aria-hidden="true" className="size-3" />
          {t("recon.unpaidBadge")}
        </Badge>
      </div>
      <p className="text-sm text-text-muted">{t("recon.unpaidHint")}</p>

      {report.isPending ? (
        <div aria-busy="true" role="status">
          <span className="sr-only">{t("common.loading")}</span>
          <Skeleton className="h-24" />
        </div>
      ) : null}

      {report.isError ? (
        <p
          className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text"
          role="alert"
        >
          {t("errors.loadFailedBody")}
        </p>
      ) : null}

      {report.data !== undefined ? (
        /*
         * ⛔ SINFNING O'Z SANOG'I VA O'Z SUMMASI — BLOK ICHIDA. Ular
         *   qo'shni blokning soni bilan HECH QACHON bir qatorda turmaydi.
         */
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm" role="status">
          <div className="flex items-center gap-2">
            <dt className="text-text-muted">{t("recon.unpaidCountLabel")}</dt>
            <dd className="m-0 font-mono tabular-nums">
              {report.data.unpaid_count}
            </dd>
          </div>
          <div className="flex items-center gap-2">
            <dt className="text-text-muted">{t("recon.unpaidSoumLabel")}</dt>
            <dd className="m-0 font-mono tabular-nums">
              {format.number(report.data.unpaid_expected_soum)}{" "}
              {t("headline.amountUnit")}
            </dd>
          </div>
        </dl>
      ) : null}

      {report.data !== undefined && rows.length === 0 ? (
        /* ⛔ Bo'sh holatda AMAL yo'q — kutish qadam emas. */
        <EmptyState
          description={t("recon.emptyUnpaidHint", { date: day })}
          title={t("recon.emptyUnpaid")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{t("recon.unpaidTitle")}</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-3 font-normal">{t("recon.stallColumn")}</th>
                <th className="p-3 font-normal">{t("recon.vendorColumn")}</th>
                <th className="p-3 font-normal">{t("recon.expectedColumn")}</th>
                <th className="p-3 font-normal">{t("recon.paidColumn")}</th>
                <th className="p-3 font-normal">
                  {t("recon.outstandingColumn")}
                </th>
                <th className="p-3 font-normal">{t("recon.evidenceColumn")}</th>
                <th className="p-3 font-normal">{t("recon.statusColumn")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <UnpaidRow
                  key={row.case_id ?? `${row.stall_code}-${index}`}
                  row={row}
                  vendorLabel={vendors.labelOf(row.vendor_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function UnpaidRow({
  row,
  vendorLabel,
}: {
  row: ReportRow;
  vendorLabel: string | null;
}) {
  const t = useTranslations();
  const format = useFormatter();

  /*
   * ⛔ QARZ — SERVERDAN KELGAN IKKI SONDAN. Ikkalasidan biri `null`
   *   bo'lsa ayirma ⛔ CHIZILMAYDI: nol yozish «qarz yo'q» degan
   *   YOLG'ON da'vo bo'lardi, holbuki haqiqat «qancha ekanini tizim
   *   BILMAYDI».
   */
  const expected = row.expected_soum;
  const paid = row.paid_soum;
  const outstanding =
    expected === null || paid === null ? null : expected - paid;

  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="p-3">{row.stall_code}</td>
      <td className="p-3">
        {vendorLabel ?? (
          <span className="text-text-muted">{t("recon.vendorUnknown")}</span>
        )}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {expected === null ? "—" : format.number(expected)}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {paid === null ? "—" : format.number(paid)}
      </td>
      <td className="p-3 font-mono tabular-nums text-danger-text">
        {outstanding === null ? "—" : format.number(outstanding)}
      </td>
      <td className="p-3">
        <EvidenceLink
          serviceDate={row.service_date}
          snapshotIds={row.evidence_snapshot_ids}
        />
      </td>
      <td className="p-3">
        <CaseStatusBadge status={row.status} />
      </td>
    </tr>
  );
}
