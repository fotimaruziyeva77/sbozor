"use client";

import { useTranslations } from "next-intl";

import {
  barWidth,
  isStayBucketKey,
  reasonStatus,
  shareOf,
} from "@/components/parking/parking-data";
import { PlateBadge } from "@/components/parking/plate-badge";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { EdgeParkingReport } from "@/lib/api-types";
import { formatPercent } from "@/lib/format-number";

/*
 * =============================================================================
 * TAQSIMOTLAR — turish vaqti, chiqish turlari, doimiy mashinalar (261102).
 *
 * Gorizontal ustunlar ro'yxati (HTML): har qatorda NOM, ustun va SON —
 * qiymat yozib qo'yilgani uchun tooltip shart emas, telefonda ham o'qiladi.
 *
 * ⛔ Bitta o'lchov (mashina soni) — bitta rang (aksent). Qatorlar
 *    toifa, seriya emas: ularni ranglarga bo'lish ma'nosiz kamalak berardi.
 *
 * ⛔ Sanoqlar SERVERDAN (`stay.buckets`, `exit_reasons`, `regulars`);
 *    bu yerda faqat ulush va ustun eni hisoblanadi.
 * =============================================================================
 */

type BarRow = { key: string; label: string; count: number };

function BarList({ rows, total }: { rows: readonly BarRow[]; total: number }) {
  const fmt = useParkingFormat();
  const max = Math.max(0, ...rows.map((row) => row.count));

  return (
    <ul className="park-bars">
      {rows.map((row) => {
        const share = shareOf(row.count, total);
        return (
          <li className="park-bar-row" key={row.key}>
            <span className="park-bar-label">{row.label}</span>
            <span aria-hidden="true" className="park-bar-track">
              <span className="park-bar-fill" style={{ width: `${barWidth(row.count, max)}%` }} />
            </span>
            <span className="park-bar-value">
              {fmt.count(row.count)}
              {share === null ? null : (
                <span className="park-bar-share">{formatPercent(share)}</span>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

export function StayCard({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const { stay } = data;

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("stay.title")}</h2>
        <p className="dir-tile-sub">{t("stay.sub", { count: stay.measured })}</p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        {stay.median_minutes === null ? (
          <p className="text-sm text-text-muted">{t("stay.empty")}</p>
        ) : (
          <>
            <div className="park-callout">
              <p className="text-sm text-text-muted">{t("stay.median")}</p>
              <p className="park-callout-value text-2xl font-semibold">
                {fmt.duration(stay.median_minutes)}
              </p>
              <p className="text-xs text-text-muted">{t("stay.medianHint")}</p>
            </div>
            <BarList
              rows={stay.buckets.map((bucket) => ({
                key: bucket.key,
                /* Katalogda yo'q yangi guruh — xom kalit, yiqilish emas. */
                label: isStayBucketKey(bucket.key) ? t(`stay.bucket.${bucket.key}`) : bucket.key,
                count: bucket.count,
              }))}
              total={stay.measured}
            />
          </>
        )}
        {/* Kirishi yozilmaganlar yashirilmaydi — sababi va soni aytiladi. */}
        {stay.unrecorded_entries > 0 ? (
          <p className="dir-tile-note">
            {t("stay.unrecorded", { count: stay.unrecorded_entries })}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function ExitReasonsCard({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const manual = data.exit_reasons.find((item) => item.reason === "manual")?.count ?? 0;

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("exitReasons.title")}</h2>
        <p className="dir-tile-sub">{t("exitReasons.sub")}</p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-4">
        {data.total.exits === 0 ? (
          <p className="text-sm text-text-muted">{t("exitReasons.empty")}</p>
        ) : (
          <BarList
            rows={data.exit_reasons.map((item) => ({
              key: item.reason,
              label: t(`status.${reasonStatus(item.reason)}`),
              count: item.count,
            }))}
            total={data.total.exits}
          />
        )}
        {/* Qo'lda ochish — nazorat savoli: sabab va keyingi qadam aytiladi. */}
        {manual > 0 ? <p className="dir-tile-note">{t("exitReasons.manualNote")}</p> : null}
      </CardContent>
    </Card>
  );
}

export function RegularsCard({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("regulars.title")}</h2>
        <p className="dir-tile-sub">{t("regulars.sub")}</p>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col">
        {data.regulars.length === 0 ? (
          <p className="text-sm text-text-muted">{t("regulars.empty")}</p>
        ) : (
          <ol className="park-regulars">
            {data.regulars.map((item) => (
              <li className="park-regular" key={item.plate}>
                <PlateBadge plate={item.plate} size="sm" />
                <span className="park-regular-visits">
                  {t("regulars.visits", { count: item.visits })}
                </span>
                <span className="park-regular-meta">
                  <span className="dir-split-value">{fmt.soum(item.amount_soum)}</span>
                  <span className="text-xs text-text-muted">
                    {t("regulars.lastSeen", {
                      when: `${fmt.day(item.last_seen_at)} · ${fmt.time(item.last_seen_at)}`,
                    })}
                  </span>
                </span>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
