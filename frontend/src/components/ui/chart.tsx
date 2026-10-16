"use client";

import type { CSSProperties, ReactNode } from "react";
import { ResponsiveContainer } from "recharts";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * GRAFIK QOBIG'I — shadcn `chart.tsx` naqshi, Recharts ustida (261016).
 *
 * shadcn komponenti YUKLAB OLINMADI — u `--color-<kalit>` o'zgaruvchisini
 * yozadi va bizda o'sha nomlar fazosi TEMA TOKENLARINIKI (`--color-accent`,
 * `--color-danger`, …). `accent` nomli seriya butun pastki daraxtda tema
 * tokenini jimgina almashtirib qo'yardi. Shuning uchun seriya rangi
 * `--chart-<kalit>` da yashaydi.
 *
 * ⛔ RANG FAQAT TOKEN (`var(--color-*)`): yorug' / qorong'i / quyosh
 *    temalari tokenni almashtiradi va grafik o'zi qayta bo'yaladi.
 *    Xom hex yozilsa grafik bitta temada qolib ketardi.
 *
 * ⛔ MATN SERIYA RANGIDA YOZILMAYDI: yorliq va qiymat matn tokenida,
 *    seriyani esa yonidagi kichik belgi (chiziq yoki to'rtburchak)
 *    tanitadi — sariq va zangori matn oq fonda o'qilmaydi.
 * =============================================================================
 */

/** Bitta seriya — ko'rinadigan nom va rang tokeni. */
export type ChartSeries = {
  label: string;
  /** Faqat token: `var(--color-accent)`. */
  color: string;
};

export type ChartConfig = Record<string, ChartSeries>;

/** `--chart-<kalit>` o'zgaruvchilari — seriyalar `var(--chart-<kalit>)` bilan bo'yaladi. */
export function chartVars(config: ChartConfig): CSSProperties {
  const vars: Record<string, string> = {};
  for (const [key, series] of Object.entries(config)) {
    vars[`--chart-${key}`] = series.color;
  }
  return vars as CSSProperties;
}

/**
 * Grafik maydoni.
 *
 * ⛔ BALANDLIK `className` DA QAT'IY BERILADI (`h-56` va h.k.):
 *    `ResponsiveContainer` ota-element balandligini o'lchaydi va u `auto`
 *    bo'lsa NOL chiqadi — grafik jimgina chizilmasdi (`.dir-spark` izohi).
 *    Balandlik o'q yorliqlarini HAM o'z ichiga oladi — aks holda kartada
 *    kichik ichki aylantirish paydo bo'lardi.
 */
export function ChartContainer({
  config,
  className,
  children,
}: {
  config: ChartConfig;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("chart-frame", className)} style={chartVars(config)}>
      <ResponsiveContainer height="100%" width="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

/** Tooltip satri — qiymat KUCHLI, nom ikkinchi darajada. */
export type ChartTooltipRow = {
  key: string;
  label: string;
  value: string;
  color: string;
  /** `dashed` — tugamagan davr (uzuq chiziq). */
  kind?: "line" | "dashed";
};

/**
 * Tooltip qutisi — Recharts `content` funksiyasi shuni qaytaradi.
 *
 * ⛔ Seriya belgisi QUTI EMAS, QISQA CHIZIQ: tooltip zichligida to'ldirilgan
 *    quti ma'lumot og'irligidagi siyoh bo'lib, yorliq ishini qilardi.
 */
export function ChartTooltipBox({
  title,
  rows,
  note,
}: {
  title: ReactNode;
  rows: readonly ChartTooltipRow[];
  note?: ReactNode;
}) {
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip-title">{title}</p>
      <ul className="chart-tooltip-rows">
        {rows.map((row) => (
          <li className="chart-tooltip-row" key={row.key}>
            <span
              aria-hidden="true"
              className={
                row.kind === "dashed" ? "chart-key-dashed" : "chart-key-line"
              }
              style={{ color: row.color }}
            />
            <span className="chart-tooltip-label">{row.label}</span>
            <span className="chart-tooltip-value">{row.value}</span>
          </li>
        ))}
      </ul>
      {note === undefined ? null : <p className="chart-tooltip-note">{note}</p>}
    </div>
  );
}

/** Legenda bandi — belgi ma'lumot belgisini takrorlaydi (maydon/ustun -> to'rtburchak). */
export type ChartLegendItem = {
  key: string;
  label: ReactNode;
  color: string;
  kind: "rect" | "line";
  /** Ixtiyoriy qiymat — yorliqdan keyin, kuchli matnda. */
  value?: ReactNode;
};

/**
 * Legenda — ikki va undan ortiq seriyada HAR DOIM bor.
 *
 * ⛔ Rang yolg'iz identifikator emas: har bandda NOM yozilgan.
 */
export function ChartLegend({
  items,
  className,
}: {
  items: readonly ChartLegendItem[];
  className?: string;
}) {
  return (
    <ul className={cn("chart-legend", className)}>
      {items.map((item) => (
        <li className="chart-legend-item" key={item.key}>
          <span
            aria-hidden="true"
            className={item.kind === "line" ? "chart-key-line" : "chart-key-rect"}
            style={{ color: item.color }}
          />
          <span>{item.label}</span>
          {item.value === undefined ? null : (
            <span className="chart-legend-value">{item.value}</span>
          )}
        </li>
      ))}
    </ul>
  );
}
