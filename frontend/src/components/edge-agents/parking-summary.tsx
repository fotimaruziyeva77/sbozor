"use client";

import { useFormatter, useLocale, useTimeZone, useTranslations } from "next-intl";

import { EdgeFrameThumb } from "@/components/edge-agents/edge-frame";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatInstant } from "@/lib/format-day";
import { formatAmount, formatSoum } from "@/lib/format-number";
import { useEdgeParkingSummaryQuery } from "@/lib/edge-site-queries";

/** Bugungi avtoturargoh xulosasi (`parking` va `livestock` obyektlari). */
export function ParkingSummary({ siteId }: { siteId: string }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const timeZone = useTimeZone();
  const summary = useEdgeParkingSummaryQuery(siteId, { enabled: true });

  return (
    <Card>
      <CardHeader>
        <h2 className="text-lg font-semibold">{t("edgeAgents.parking.title")}</h2>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {summary.isPending ? (
          <div aria-busy="true" role="status">
            <span className="sr-only">{t("common.loading")}</span>
            <Skeleton className="h-20" />
          </div>
        ) : summary.isError ? (
          <p className="rounded-sm bg-danger/10 px-3 py-2 text-sm text-danger-text" role="alert">
            {t("errors.loadFailedBody")}
          </p>
        ) : (
          <>
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label={t("edgeAgents.parking.entries")}>
                {formatAmount(format, summary.data.entries, locale)}
              </Stat>
              <Stat label={t("edgeAgents.parking.exits")}>
                {formatAmount(format, summary.data.exits, locale)}
              </Stat>
              <Stat label={t("edgeAgents.parking.open")}>
                {formatAmount(format, summary.data.open_estimate, locale)}
              </Stat>
              <Stat label={t("edgeAgents.parking.cash")}>
                {formatSoum(format, summary.data.cash_total_soum, locale)}
                <span className="mt-1 block text-xs font-normal text-text-muted">
                  {t("edgeAgents.parking.byCash", {
                    amount: formatSoum(format, summary.data.cash_by_method.cash, locale),
                  })}
                </span>
                <span className="block text-xs font-normal text-text-muted">
                  {t("edgeAgents.parking.byTerminal", {
                    amount: formatSoum(format, summary.data.cash_by_method.terminal, locale),
                  })}
                </span>
              </Stat>
            </dl>

            <section aria-labelledby="edge-last-plates" className="flex flex-col gap-2">
              <h3 className="text-sm font-semibold" id="edge-last-plates">
                {t("edgeAgents.parking.lastPlates")}
              </h3>
              {summary.data.last_plates.length === 0 ? (
                <p className="text-sm text-text-muted">{t("edgeAgents.parking.noPlates")}</p>
              ) : (
                <ul className="flex flex-col divide-y divide-border">
                  {summary.data.last_plates.map((plate, index) => {
                    const at = new Date(plate.occurred_at);
                    return (
                      <li
                        className="flex items-center gap-3 py-2 text-sm"
                        key={`${plate.occurred_at}-${plate.plate}-${index}`}
                      >
                        {plate.file_id !== null ? (
                          <EdgeFrameThumb fileId={plate.file_id} siteId={siteId} />
                        ) : (
                          <span aria-hidden="true" className="h-12 w-16 shrink-0" />
                        )}
                        <span className="font-mono font-semibold">{plate.plate}</span>
                        <span className="text-text-muted">
                          {plate.direction === "in" || plate.direction === "out"
                            ? t(`edgeAgents.commands.direction.${plate.direction}`)
                            : plate.direction}
                          {` · ${plate.lane_id}`}
                        </span>
                        <span className="ml-auto whitespace-nowrap text-xs text-text-muted">
                          {Number.isNaN(at.getTime())
                            ? plate.occurred_at
                            : formatInstant(format, at, locale, timeZone, "short")}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs text-text-muted">{label}</dt>
      <dd className="m-0 text-lg font-semibold tabular-nums">{children}</dd>
    </div>
  );
}
