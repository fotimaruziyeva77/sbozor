"use client";

import { Receipt } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import type { ReportRow } from "@/lib/reconciliation-queries";
import {
  isSubjectKind,
  useReconciliationMarketId,
  useReconciliationReport,
} from "@/lib/reconciliation-queries";
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
 * -----------------------------------------------------------------------
 * ⛔⛔ ARIFMETIKA YO'Q — VA ENDI BU ROST (WR-06)
 * -----------------------------------------------------------------------
 * Bu invariant bir muddat ⛔ FAQAT IZOHDA turgan edi: qator ostida
 * `expected − paid` ayirmasi bajarilardi va u «Qarz» ustunini to'ldirardi.
 * Ayirma `int` ustida ketgani uchun pul TURI buzilmasdi (D-07 saqlanardi),
 * lekin u ⛔ IKKINCHI HAQIQAT MANBAI edi: qarz serverda
 * `billing_repo.vendor_outstanding()` va kredit taqsimoti qoidalari bilan
 * chiqadi, bu yerda esa oddiy ayirma bilan. Serverga tuzatish
 * (`charge_adjustments`) yoki kredit taqsimoti qo'shilgan kuni ikki son
 * ⛔ JIMGINA ajralardi va nizo hujjatida (D-02) ikki xil raqam qolardi.
 *
 * ⛔⛔ NEGA UCHINCHI USTUN (server bergan «qoldiq») HAM QO'SHILMADI:
 *
 *   1. `ReportRowResponse` da `outstanding_soum` MAYDONI ⛔ UMUMAN YO'Q —
 *      ya'ni bugungi kontrakt bilan uni CHIZISHNING yagona yo'li
 *      klientda ayirish bo'lardi, ya'ni aynan olib tashlangan nuqson;
 *   2. `paid_soum` ning O'Z docstringi buni ochiq taqiqlaydi: «⛔
 *      HISOBLANMAYDI, BERILADI ... Uni bu yerda (yoki klientda) ayirish
 *      bilan chiqarish «to'landimi?» savolining IKKINCHI javobini
 *      tug'dirardi»;
 *   3. Sotuvchining qarzi — `billing_repo.vendor_outstanding()` ning
 *      javobi va u ⛔ SOTUVCHI kesimida (rasta-kun kesimida EMAS)
 *      yashaydi, ya'ni bu jadvalning qatori uchun u TA'RIFAN boshqa son.
 *      Uning uyi — qarzdorlik reestri yuzasi.
 *
 * ⚠⚠ DIZAYN KONTRAKTIDAN ⛔ ASOSLI CHETLANISH: 07-UI-SPEC §8.3 bu jadvalga
 *   «Qarz (`outstanding_soum`)» ustunini yozgan. Kontraktning O'ZI manbani
 *   ⛔ SERVER MAYDONI deb ko'rsatgan, server esa uni ⛔ BERMAYDI — ya'ni
 *   ustunni ROST chizishning yo'li YO'Q. Ikki sonni ko'rsatish direktorga
 *   «kutilgan va yig'ilgan» faktini beradi va ⛔ hech qanday yangi haqiqat
 *   manbai tug'dirmaydi. (`case-list.tsx` va `unregistered-list.tsx` da
 *   ayni sinfdagi chetlanishlar allaqachon yozilgan.)
 *
 * ⛔ `null` ⛔ NOLGA aylantirilmaydi — «yo'q summa» YO'Q SUMMA bo'lib
 *    qoladi va katak NOMLANGAN holat matnini oladi: nol yozish «qarz
 *    yo'q» degan YOLG'ON da'vo, bo'sh katak esa 4-fazada o'lchangan «jim
 *    xato» sinfi bo'lardi.
 * =============================================================================
 */

/** Sinf A ning diskriminatori — YOPIQ qiymat, «qaysi ustun bo'sh?» EMAS. */
const SUBJECT = "occupied_unpaid";

export function UnpaidList({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const marketId = useReconciliationMarketId();
  const hasMarket = marketId !== null;
  const report = useReconciliationReport(day, { enabled: hasMarket });
  const vendors = useVendorLabels({ enabled: hasMarket });

  const allRows = report.data?.rows ?? [];
  const rows = allRows.filter((row) => row.subject_kind === SUBJECT);
  /*
   * ⛔⛔ UCHINCHI SHOX — NOMA'LUM SINF (WR-13).
   *
   * Sxema `subject_kind` ni ⛔ ATAYIN qulflamaydi (`z.string()`), ya'ni
   * server uchinchi sinf qo'shsa u BU YERGA yetib keladi. Ikki sinfli
   * filtr uni ⛔ IKKALA blokdan ham JIMGINA yo'qotardi, `unpaid_count` /
   * `unregistered_count` esa SERVERDA hisoblanadi — ya'ni ekranda
   * ⛔ SANOQ BILAN RO'YXAT AJRALARDI va bu `case-status-badge.tsx` da
   * o'rnatilgan «NOMA'LUM QIYMAT YASHIRILMAYDI» qoidasining aynan
   * teskarisi bo'lardi.
   *
   * ⛔ QATOR QO'SHNI JADVALGA TIQILMAYDI: uni `anomaly` ro'yxatiga
   *    qo'shish sinf ta'rifini buzardi va sanoqni ro'yxatdan yana
   *    ajratardi. Fakt NOMLANGAN JUMLA bilan e'lon qilinadi.
   *
   * ⛔ `isSubjectKind()` AYNAN SHU EHTIYOJ UCHUN yozilgan edi va bir
   *    muddat ⛔ 0 iste'molchisi bor edi — ya'ni qoida kodda bor, kuchi
   *    yo'q edi.
   */
  const unknownKindCount = allRows.filter(
    (row) => !isSubjectKind(row.subject_kind),
  ).length;

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

      {/*
       * ⛔ BOZORSIZ SESSIYA — NOMLANGAN HOLAT, ⛔ CHEKSIZ SKELET EMAS
       *   (IN-08). O'chirilgan so'rov TanStack v5 da `isPending` da
       *   QOLADI, ya'ni skelet abadiy turardi va sabab hech qayerda
       *   yozilmasdi (`HeadlineCard` bu shoxni allaqachon qo'riqlaydi).
       */}
      {hasMarket ? null : (
        <div className="flex flex-col gap-1">
          <p className="text-sm">{t("recon.marketMissing")}</p>
          <p className="text-xs text-text-muted">
            {t("recon.marketMissingHint")}
          </p>
        </div>
      )}

      {hasMarket && report.isPending ? (
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
        /*
         * ⛔ `role` YO'Q (WR-08): u `<dl>` ning implicit rolini
         *   ALMASHTIRIB, `<dt>`/`<dd>` juftligining atama–qiymat
         *   bog'lanishini yo'q qilardi. Jonli hudud ham YO'Q — bu blokda
         *   foydalanuvchi boshlaydigan yangilash mavjud emas.
         */
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <div className="flex items-center gap-2">
            <dt className="text-text-muted">{t("recon.unpaidCountLabel")}</dt>
            <dd className="m-0 font-mono tabular-nums">
              {report.data.unpaid_count}
            </dd>
          </div>
          <div className="flex items-center gap-2">
            <dt className="text-text-muted">{t("recon.unpaidSoumLabel")}</dt>
            {/* ⛔ Birlik O'Z namespace'idan (IN-05): `headline.*` — BOSHQA yuza. */}
            <dd className="m-0 font-mono tabular-nums">
              {format.number(report.data.unpaid_expected_soum)}{" "}
              {t("recon.amountUnit")}
            </dd>
          </div>
        </dl>
      ) : null}

      {/*
       * ⛔ NOMA'LUM SINFNING SANOQ FARQI — JIMGINA YO'QOLISH O'RNIGA
       *   NOMLANGAN JUMLA (WR-13). Nol bo'lganda jumla ⛔ CHIZILMAYDI:
       *   har kuni turadigan «noma'lum qator bor» yozuvi shovqin bo'lardi.
       */}
      {unknownKindCount > 0 ? (
        <p className="rounded-sm bg-surface-muted px-3 py-2 text-sm text-text">
          {t("recon.subjectUnknownNotice", { count: unknownKindCount })}
        </p>
      ) : null}

      {report.data !== undefined && rows.length === 0 ? (
        /* ⛔ Bo'sh holatda AMAL yo'q — kutish qadam emas. */
        <EmptyState
          description={t("recon.emptyUnpaidHint", {
            date: formatBusinessDay(format, day),
          })}
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
                {/*
                 * ⛔ IKKI USTUN, UCHTA EMAS: «qarz» ustuni SERVER
                 *   maydonisiz ROST chizilmaydi (modul izohi).
                 */}
                <th className="p-3 font-normal">{t("recon.expectedColumn")}</th>
                <th className="p-3 font-normal">{t("recon.paidColumn")}</th>
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
   * ⛔⛔ IKKI SON — SERVERDAN KELGANICHA. Klient ularni ⛔ QO'SHMAYDI,
   *   ⛔ AYIRMAYDI va ⛔ QAYTA HISOBLAMAYDI: u FORMATLAYDI, XOLOS.
   *
   * ⛔ `null` — NOMLANGAN holat: «qancha ekanini tizim BILMAYDI». Nol
   *   yozish «to'lov yo'q» degan YOLG'ON da'vo, bo'sh katak esa jim xato
   *   bo'lardi.
   */
  const expected = row.expected_soum;
  const paid = row.paid_soum;

  return (
    /* Qator hover foni (§12.8) — davomiylik `--default-transition-*` dan. */
    <tr className="border-b border-border transition-colors last:border-b-0 hover:bg-surface-muted">
      <td className="p-3">{row.stall_code}</td>
      <td className="p-3">
        {vendorLabel ?? (
          <span className="text-text-muted">{t("recon.vendorUnknown")}</span>
        )}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {expected === null ? (
          <span className="font-sans text-text-muted">
            {t("recon.amountUnknown")}
          </span>
        ) : (
          format.number(expected)
        )}
      </td>
      <td className="p-3 font-mono tabular-nums">
        {paid === null ? (
          <span className="font-sans text-text-muted">
            {t("recon.amountUnknown")}
          </span>
        ) : (
          format.number(paid)
        )}
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
