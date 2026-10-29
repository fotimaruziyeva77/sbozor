"use client";

import { useFormatter, useLocale, useTranslations } from "next-intl";
import { Banknote, CreditCard, Smartphone } from "lucide-react";

import { methodShares } from "@/components/director/chart-data";
import type { Period } from "@/components/director/period";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatBusinessDay } from "@/lib/format-day";
import { formatPercent, formatSoum } from "@/lib/format-number";
import { useLiveRevenue } from "@/lib/report-queries";

/*
 * =============================================================================
 * TO'LOV TURLARI — naqd va terminal (261016, buyurtmachi maketi).
 *
 * ⛔⛔ DONUT EMAS — IKKI SON VA BITTA BO'LINGAN CHIZIQ.
 *     Ikki bo'lakli doira raqamdan ko'p joy oladi va kam narsa aytadi:
 *     65% va 35% ni burchakdan o'qish qiyin, son esa o'zi javob. Shuning
 *     uchun ikki qism SON bilan yoziladi, chiziq esa ulushni bir qarashda
 *     ko'rsatadi.
 *
 * ⛔ SO'ROV YANGI EMAS: `useLiveRevenue(period)` — bosh katak bilan AYNI
 *    kalit, ya'ni javob keshdan olinadi va panel bir davr uchun ikki xil
 *    tushum ko'rsatmaydi.
 *
 * ⛔ Naqd ulushi — nazorat savoli: terminal puli bankda iz qoldiradi,
 *    naqd esa kassirning qo'lidan o'tadi.
 * =============================================================================
 */

export function PaymentMix({ period }: { period: Period }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();

  const live = useLiveRevenue({ from: period.from, to: period.to });

  const periodLabel =
    period.from === period.to
      ? formatBusinessDay(format, period.to, locale)
      : `${formatBusinessDay(format, period.from, locale)} — ${formatBusinessDay(format, period.to, locale)}`;

  const cash = live.data?.collected_cash_soum ?? null;
  const terminal = live.data?.collected_terminal_soum ?? null;
  // 0035: Payme — maydon yo'q (eski server) yoki 0 bo'lsa qator chizilmaydi.
  const payme = live.data?.collected_payme_soum ?? 0;
  const click = live.data?.collected_click_soum ?? 0;
  const shares =
    cash === null || terminal === null ? null : methodShares(cash, terminal, payme, click);

  const parts = [
    {
      key: "cash",
      Icon: Banknote,
      label: t("director.methodCash"),
      value: cash,
      share: shares?.cash ?? null,
      color: "var(--color-accent)",
    },
    {
      key: "terminal",
      Icon: CreditCard,
      label: t("director.methodTerminal"),
      value: terminal,
      share: shares?.terminal ?? null,
      color: "var(--color-info)",
    },
    ...(payme === 0
      ? []
      : [
          {
            key: "payme",
            Icon: Smartphone,
            label: t("director.methodPayme"),
            value: payme,
            share: shares?.payme ?? null,
            color: "var(--color-success)",
          },
        ]),
    ...(click === 0
      ? []
      : [
          {
            key: "click",
            Icon: Smartphone,
            label: t("director.methodClick"),
            value: click,
            share: shares?.click ?? null,
            color: "var(--color-warning)",
          },
        ]),
  ];

  return (
    <Card className="dir-chart-card hover:translate-y-0">
      <CardHeader>
        <h2 className="dir-trend-title">{t("director.methodTitle")}</h2>
        <p className="dir-tile-sub">{periodLabel}</p>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col gap-5">
        {live.isLoading ? (
          <div aria-busy="true" className="flex flex-col gap-3">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-8 w-1/2" />
          </div>
        ) : live.isError || cash === null || terminal === null ? (
          <p className="dir-tile-note" role="alert">
            {t("director.chartLoadError")}
          </p>
        ) : (
          <>
            {/*
             * ⛔ Chiziq FAQAT ulush ma'noli bo'lganda: davrda pul bor va
             *    ikkala qism ham manfiy emas (`methodShares`). Aks holda
             *    sonlar o'zi qoladi va sabab yoziladi.
             */}
            {shares === null ? (
              <p className="dir-tile-note">
                {cash === 0 && terminal === 0 && payme === 0 && click === 0
                  ? t("director.methodEmpty")
                  : t("director.methodNoShare")}
              </p>
            ) : (
              <div aria-hidden="true" className="dir-split">
                {parts.map((part) =>
                  part.share === null || part.share <= 0 ? null : (
                    <span
                      className="dir-split-part"
                      key={part.key}
                      style={{ background: part.color, flexGrow: part.share }}
                    />
                  ),
                )}
              </div>
            )}

            <dl className="flex flex-col gap-3">
              {parts.map((part) => (
                <div className="dir-split-row" key={part.key}>
                  <dt className="flex items-center gap-2">
                    <span
                      aria-hidden="true"
                      className="chart-key-rect"
                      style={{ color: part.color }}
                    />
                    <part.Icon aria-hidden="true" className="size-4 text-text-muted" />
                    <span className="text-sm">{part.label}</span>
                  </dt>
                  <dd className="flex items-baseline gap-2">
                    <span className="dir-split-value">
                      {formatSoum(format, part.value ?? 0, locale)}
                    </span>
                    {part.share === null ? null : (
                      <span className="text-xs text-text-muted">
                        {formatPercent(part.share)}
                      </span>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </>
        )}
      </CardContent>
    </Card>
  );
}
