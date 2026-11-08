"use client";

import type { LucideIcon } from "lucide-react";
import { Scale, Ticket } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import type { Period } from "@/components/director/period";
import { PERIOD_LABEL_KEY } from "@/components/director/period";
import { PanelTile } from "@/components/panel/tile";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatAmount } from "@/lib/format-number";
import { useLiveRevenue } from "@/lib/report-queries";

/*
 * =============================================================================
 * BUXGALTER PANELI: PATTA PULI VA TAROZI PULI ALOHIDA (261108, buyurtmachi:
 * «umumiy pul, patta puli alohida, tarozi puli alohida bo'ladi»).
 *
 * ⛔ IKKI SON HAM SERVERDAN (`/reports/live`) va bosh katak bilan AYNI kalitda
 *    o'qiladi. Klientda bo'lish ham, qo'shish ham yo'q: qoida
 *    `sbozor_core.billing.payment_fee_part` da.
 *
 * ⛔ MAYDON KELMASA (eski server yoki xato) «—» yoziladi, nol EMAS: «tarozi
 *    puli 0» buxgalter uchun haqiqiy son bo'lib o'qilardi.
 * =============================================================================
 */

/** Katakning davr yozuvi: «Bugun» yoki «1-oktabr, 2026 — 7-oktabr, 2026». */
export function usePeriodSub(period: Period): string {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  return period.kind === "custom"
    ? `${formatBusinessDay(format, period.from, locale)} — ${formatBusinessDay(format, period.to, locale)}`
    : t(PERIOD_LABEL_KEY[period.kind]);
}

function PartTile({
  icon,
  label,
  loading,
  step,
  sub,
  value,
}: {
  icon: LucideIcon;
  label: string;
  loading: boolean;
  step: number;
  sub: string;
  value: number | undefined;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  return (
    <PanelTile href="/reports" icon={icon} label={label} step={step} sub={sub}>
      {loading ? (
        <Skeleton className="dir-kpi-skeleton" />
      ) : value === undefined ? (
        <p className="dir-kpi-value text-text-muted">—</p>
      ) : (
        <p className="dir-kpi-value">
          {formatAmount(format, value, locale)}{" "}
          <span className="dir-kpi-unit">{t("reports.amountUnit")}</span>
        </p>
      )}
    </PanelTile>
  );
}

export function CollectedPartTiles({ period }: { period: Period }) {
  const t = useTranslations();
  const sub = usePeriodSub(period);
  const live = useLiveRevenue({ from: period.from, to: period.to });

  return (
    <>
      <PartTile
        icon={Ticket}
        label={t("director.kpiStallMoney")}
        loading={live.isLoading}
        step={1}
        sub={sub}
        value={live.data?.collected_stall_soum}
      />
      <PartTile
        icon={Scale}
        label={t("director.kpiFeeMoney")}
        loading={live.isLoading}
        step={2}
        sub={sub}
        value={live.data?.collected_fee_soum}
      />
    </>
  );
}
