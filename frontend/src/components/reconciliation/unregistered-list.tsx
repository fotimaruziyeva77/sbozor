"use client";

import { UserX } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { CaseStatusBadge } from "@/components/reconciliation/case-status-badge";
import { EvidenceLink } from "@/components/reconciliation/evidence-link";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import type { ReportRow } from "@/lib/reconciliation-queries";
import { useReconciliationReport } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * C BLOKI — ⛔ SINF B: «RO'YXATGA OLINMAGAN SAVDO».
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ ASOSIY SON — ⛔ RASTA SONI. SUMMA ⛔ UMUMAN YO'Q
 * -----------------------------------------------------------------------
 * Biriktirilmagan rastaning tarifi ⛔ BILINMAYDI, ya'ni bu sinfda
 * «kutilgan summa» degan miqdor ⛔ MAVJUD EMAS — nol ham emas,
 * noma'lum ham emas: u ⛔ YO'Q.
 *
 * Aynan shu sababdan bu blok qo'shni blok bilan ⛔ HECH QACHON
 * qo'shilmaydi: yig'indi nol qo'shib hisoblanardi va u
 * ⛔ KAM KO'RSATILGAN YO'QOTISH bo'lardi.
 *
 * ⛔ Shuning uchun bu faylda pul formatlagichi ham, «umumiy jami»
 *    ma'nosini beradigan birorta nom ham yozilmaydi.
 *
 * -----------------------------------------------------------------------
 * ⚠⚠ USTUNLAR — DIZAYN KONTRAKTIDAN ⛔ ASOSLI CHETLANISH (SUMMARY da)
 * -----------------------------------------------------------------------
 * Kontrakt bu blok uchun «kamera/zona + slot vaqti» ustunlarini va
 * ⛔ «rasta ustuni YO'Q» qoidasini yozgan. Ikkalasi ham 07-10 ning
 * SHIPLANGAN javobi bilan to'qnashadi va ⛔ HAQIQAT USTUN TURADI:
 *
 *   1. Javobda kamera ham, zona ham, slot vaqti ham ⛔ UMUMAN YO'Q —
 *      qator `stall_code` va `service_date` bilan keladi. Ularni
 *      to'qish ⛔ TO'QILGAN QIYMAT bo'lardi (05-14 darsi).
 *
 *   2. «Rasta ustuni yo'q» qoidasining SABABI kontraktda ochiq
 *      yozilgan: bo'sh «—» ustuni jim xato bo'lardi. Lekin maydon
 *      ⛔ BO'SH EMAS: `unassigned_occupied` ning ta'rifi — «rasta band,
 *      lekin ⛔ SOTUVCHI biriktirilmagan», ya'ni RASTA aniq va uning
 *      kodi bor. 6-faza ham aynan shu qatorni `stall_code` bilan
 *      ko'rsatadi va ⛔ IKKI FAZADA IKKI XIL YORLIQ bo'lmasligi
 *      kontraktning O'Z talabi.
 *
 * ⛔ SOTUVCHI USTUNI ESA HAQIQATAN YO'Q va bu sinfning butun mazmuni:
 *    biriktirilgan sotuvchi ⛔ MAVJUD EMAS. Bo'sh ustun bu yerda haqiqiy
 *    jim xato bo'lardi.
 * =============================================================================
 */

/** Sinf B ning diskriminatori — YOPIQ qiymat, «qaysi ustun bo'sh?» EMAS. */
const SUBJECT = "anomaly";

export function UnregisteredList({ day }: { day: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const report = useReconciliationReport(day);

  const rows = (report.data?.rows ?? []).filter(
    (row) => row.subject_kind === SUBJECT,
  );

  return (
    /* ⛔ Atribut ENG TASHQI elementda va HAR holatda — yuklanishda ham. */
    <div className="flex flex-col gap-3" data-recon-content="unregistered">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-semibold">
          {t("recon.unregisteredTitle")}
        </h2>
        {/* ⛔ Badge matni TO'LIQ, qisqartirilmagan (WCAG 1.4.1, 3-kanal). */}
        <Badge className="gap-1" tone="warning">
          <UserX aria-hidden="true" className="size-3" />
          {t("recon.unregisteredTitle")}
        </Badge>
      </div>
      <p className="text-sm text-text-muted">{t("recon.unregisteredHint")}</p>

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
        /* ⛔ AYNAN BITTA SON — RASTA SONI. Summa yo'q (yuqoriga qarang). */
        <dl className="flex flex-wrap gap-x-6 gap-y-2 text-sm" role="status">
          <div className="flex items-center gap-2">
            <dt className="text-text-muted">
              {t("recon.unregisteredCountLabel")}
            </dt>
            <dd className="m-0 font-mono tabular-nums">
              {report.data.unregistered_count}
            </dd>
          </div>
        </dl>
      ) : null}

      {report.data !== undefined && rows.length === 0 ? (
        <EmptyState
          description={t("recon.emptyUnregisteredHint", { date: day })}
          title={t("recon.emptyUnregistered")}
        />
      ) : null}

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">
              {t("recon.unregisteredTitle")}
            </caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-text-muted">
                <th className="p-3 font-normal">{t("recon.stallColumn")}</th>
                <th className="p-3 font-normal">{t("recon.dayColumn")}</th>
                <th className="p-3 font-normal">{t("recon.evidenceColumn")}</th>
                <th className="p-3 font-normal">{t("recon.statusColumn")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <UnregisteredRow
                  format={format}
                  key={row.case_id ?? `${row.stall_code}-${index}`}
                  row={row}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

function UnregisteredRow({
  format,
  row,
}: {
  format: ReturnType<typeof useFormatter>;
  row: ReportRow;
}) {
  return (
    <tr className="border-b border-border last:border-b-0">
      <td className="p-3">{row.stall_code}</td>
      {/*
       * ⛔ ABSOLUT SANA, NISBIY VAQT EMAS: nizoda «2 kun oldin» ni
       *   o'qib aytib bo'lmaydi va u har ochilishda boshqacha o'qilardi.
       */}
      <td className="p-3">
        {format.dateTime(new Date(`${row.service_date}T00:00:00`), {
          dateStyle: "medium",
        })}
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
