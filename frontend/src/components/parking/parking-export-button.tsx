"use client";

import { useRef, useState } from "react";
import { Download } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { downloadParkingReport } from "@/lib/edge-site-queries";
import type { ParkingReportPeriod } from "@/lib/edge-site-queries";
import { reportErrorView } from "@/lib/report-errors";

/*
 * Avtoturargoh hisobotining Excel tugmasi — `reports/export-button.tsx`
 * NAQSHI, lekin nishoni boshqa (obyekt + davr), shuning uchun o'sha
 * komponentning diskriminatsiyalangan ittifoqiga qo'shilmadi: u
 * `REPORT_KINDS` reyestri bilan qulflangan va avtoturargoh u reyestrga
 * kirmaydi (manbasi `daily_charges` emas, agent hodisalari).
 *
 * ⛔ Brauzerning o'z yuklab olish yo'li YO'Q (anchor/`window.open`/
 *    `location.href`): access token sarlavhada ketadi, tokensiz so'rov
 *    401 tanasini `.xlsx` nomi bilan diskka yozardi. Yagona zanjir
 *    `edge-site-queries.ts::downloadParkingReport` da.
 *
 * ⛔ XATO — INLINE, toast emas: toast g'oyib bo'ladi va foydalanuvchi
 *    og'ir eksportni qayta-qayta bosardi. Sabab va keyingi qadam matni
 *    `reports.errorCause.*` / `reports.errorFix.*` dan — server kodlari
 *    (`report_period_*`, `report_too_large`) hisobot marshrutlariniki
 *    bilan AYNAN bir xil.
 */

const FALLBACK_ERROR_CODE = "report_export_failed";

export function ParkingExportButton({
  siteId,
  period,
  unavailable,
}: {
  siteId: string;
  period: ParkingReportPeriod;
  /** Hozir yuklab olib bo'lmaydi (hisobot hali kelmagan) — `aria-disabled`. */
  unavailable?: boolean;
}) {
  const t = useTranslations();
  const [busy, setBusy] = useState(false);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  /* Poyga qulfi — `useRef`: uch tez bosish bitta render oralig'ida keladi. */
  const running = useRef(false);

  async function run(): Promise<void> {
    if (unavailable === true || running.current) return;
    running.current = true;
    setErrorCode(null);
    setBusy(true);
    try {
      await downloadParkingReport(siteId, period);
    } catch (error) {
      setErrorCode(error instanceof ApiError ? error.detail : FALLBACK_ERROR_CODE);
    } finally {
      running.current = false;
      setBusy(false);
    }
  }

  const view = errorCode === null ? null : reportErrorView(errorCode);
  const causeKey = view?.causeKey ?? `reports.errorCause.${FALLBACK_ERROR_CODE}`;
  const fixKey = view?.fixKey ?? `reports.errorFix.${FALLBACK_ERROR_CODE}`;

  return (
    <div className="flex flex-col gap-2">
      <Button
        aria-busy={busy}
        aria-disabled={unavailable === true}
        onClick={() => void run()}
        size="md"
        variant="secondary"
      >
        <Download aria-hidden="true" />
        {t("parkingReport.export")}
      </Button>
      {errorCode !== null ? (
        <p className="flex flex-col gap-1 text-sm text-text-muted" role="alert">
          <span>{t(causeKey)}</span>
          <span>{t(fixKey)}</span>
        </p>
      ) : null}
    </div>
  );
}
