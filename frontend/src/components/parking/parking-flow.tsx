"use client";

import {
  Banknote,
  ChevronRight,
  CreditCard,
  LogIn,
  LogOut,
  SquareParking,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";

import { hourLabel, peakHour, shareOf } from "@/components/parking/parking-data";
import { useParkingFormat } from "@/components/parking/use-parking-format";
import type { EdgeParkingReport } from "@/lib/api-types";
import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format-number";

/*
 * =============================================================================
 * DARVOZA OQIMI — hisobotning birinchi javobi (261102).
 *
 * Avtoturargoh bitta jarayon: mashina KIRADI -> ICHKARIDA turadi -> CHIQADI.
 * Uchta son shu tartibda, yo'l chizig'i bilan ulanib turadi; yonida —
 * tushum va uning naqd/terminal bo'linishi.
 *
 * ⛔ HAR SON SERVERDAN (`total`, `inside`, `stay`, `average_check_soum`):
 *    bu yerda faqat ulush (foiz) hisoblanadi.
 *
 * ⛔ Naqd — aksent, terminal — `info`: direktor panelidagi «To'lov usuli»
 *    kartasi bilan AYNAN bir xil (rang mavzuga emas, mohiyatga bog'lanadi).
 * =============================================================================
 */

export const MONEY_COLORS = {
  cash: "var(--color-accent)",
  terminal: "var(--color-info)",
} as const;

export function ParkingFlow({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const peak = peakHour(data.hours);
  const median = data.stay.median_minutes;

  return (
    <section aria-label={t("flow.label")} className="park-hero">
      <div className="park-flow">
        <FlowStation
          icon={LogIn}
          label={t("flow.entries")}
          note={
            peak === null
              ? undefined
              : t("flow.peak", { from: hourLabel(peak.hour), to: hourLabel(peak.hour + 1) })
          }
          road
          value={fmt.count(data.total.entries)}
        />
        <FlowStation
          icon={SquareParking}
          label={t("flow.inside")}
          note={t("flow.insideNote")}
          road
          tone="accent"
          value={fmt.count(data.inside)}
        />
        <FlowStation
          icon={LogOut}
          label={t("flow.exits")}
          note={
            median === null ? undefined : t("flow.medianStay", { duration: fmt.duration(median) })
          }
          value={fmt.count(data.total.exits)}
        />
      </div>

      <MoneyPanel data={data} />
    </section>
  );
}

function FlowStation({
  icon: Icon,
  label,
  value,
  note,
  tone = "neutral",
  road = false,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  note?: string;
  tone?: "neutral" | "accent";
  /** Keyingi bekatgacha yo'l chizig'i — bezak, skrinrider o'qimaydi. */
  road?: boolean;
}) {
  return (
    <div className="park-flow-station">
      <div className="park-flow-head">
        <span aria-hidden="true" className={cn("park-flow-icon", `stat-tone-${tone}`)}>
          <Icon className="size-5" />
        </span>
        {road ? (
          <span aria-hidden="true" className="park-flow-road">
            <ChevronRight className="park-flow-chevron size-4" />
          </span>
        ) : null}
      </div>
      <span className="park-flow-text">
        <span className="park-flow-label">{label}</span>
        <span className="park-flow-value text-2xl font-semibold">{value}</span>
        {note === undefined ? null : <span className="park-flow-note">{note}</span>}
      </span>
    </div>
  );
}

function MoneyPanel({ data }: { data: EdgeParkingReport }) {
  const t = useTranslations("parkingReport");
  const fmt = useParkingFormat();
  const { cash, terminal, total } = data.total;

  const parts = [
    { key: "cash", Icon: Banknote, label: t("money.cash"), value: cash, color: MONEY_COLORS.cash },
    {
      key: "terminal",
      Icon: CreditCard,
      label: t("money.terminal"),
      value: terminal,
      color: MONEY_COLORS.terminal,
    },
  ] as const;

  return (
    <div className="park-money">
      <p className="park-flow-label">{t("money.title")}</p>
      <p className="park-money-value">
        <span className="text-2xl font-semibold">{fmt.count(total)}</span>{" "}
        <span className="text-sm text-text-muted">{t("amountUnit")}</span>
      </p>

      {/* ⛔ Chiziq faqat pul bo'lganda — nol ulush ma'nosiz. */}
      {total > 0 ? (
        <div aria-hidden="true" className="dir-split">
          {parts.map((part) =>
            part.value <= 0 ? null : (
              <span
                className="dir-split-part"
                key={part.key}
                style={{ background: part.color, flexGrow: part.value }}
              />
            ),
          )}
        </div>
      ) : (
        <p className="text-sm text-text-muted">{t("money.none")}</p>
      )}

      <dl className="flex flex-col gap-2">
        {parts.map((part) => {
          const share = shareOf(part.value, total);
          return (
            <div className="dir-split-row" key={part.key}>
              <dt className="flex items-center gap-2 text-sm">
                <span
                  aria-hidden="true"
                  className="chart-key-rect"
                  style={{ color: part.color }}
                />
                <part.Icon aria-hidden="true" className="size-4 text-text-muted" />
                {part.label}
              </dt>
              <dd className="flex items-baseline gap-2">
                <span className="dir-split-value">{fmt.soum(part.value)}</span>
                {share === null ? null : (
                  <span className="text-xs text-text-muted">{formatPercent(share)}</span>
                )}
              </dd>
            </div>
          );
        })}
      </dl>

      <dl className="park-money-facts">
        <div>
          <dt>{t("money.averageCheck")}</dt>
          <dd>
            {data.average_check_soum === null ? t("unknown") : fmt.soum(data.average_check_soum)}
          </dd>
        </div>
        <div>
          <dt>{t("money.paidCars")}</dt>
          <dd>{fmt.count(data.paid_sessions)}</dd>
        </div>
        <div>
          <dt>{t("money.freeExits")}</dt>
          <dd>{fmt.count(data.total.free_count)}</dd>
        </div>
      </dl>
    </div>
  );
}
