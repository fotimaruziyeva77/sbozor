"use client";

import { Bar, BarChart, Cell, ResponsiveContainer } from "recharts";

/*
 * =============================================================================
 * KATAK MINI-GRAFIGI — har raqamning yonidagi shakl (260902).
 *
 * ⛔⛔ NEGA: raqam yolg'iz turganda u HOLATNI aytadi, YO'NALISHNI emas.
 *     «97 000 so'm qarz» — bu ko'p mi, kam mi? O'tgan haftaga nisbatan
 *     o'syaptimi? Katak yonidagi ustunlar shu savolga bir qarashda javob
 *     beradi va direktorga hisobotga kirishdan oldin qaror beradi.
 *
 * ⚠ O'QLAR VA TO'RLAR YO'Q — BU SPARKLINE, GRAFIK EMAS. Aniq qiymat
 *   katakning O'ZIDA katta shrift bilan yozilgan; bu yerdagi vazifa
 *   faqat shakl. Ustun tagida raqam chizish katakni ikkinchi grafikka
 *   aylantirardi va bosh sonning kuchini olardi.
 *
 * ⛔ OXIRGI USTUN URG'ULANADI (to'liq aksent), qolganlari susaytirilgan:
 *    «bugun qayerdamiz» — birinchi savol, qolgani kontekst.
 * =============================================================================
 */

export type SparkBar = { label: string; value: number };

export function TileSpark({
  bars,
  tone = "accent",
}: {
  bars: readonly SparkBar[];
  /**
   * Ohang katakning MA'NOSIGA bog'lanadi, chiroyiga emas: qarz va
   * yo'qotish — `danger`, tushum — `accent`, yig'ilish — `success`.
   */
  tone?: "accent" | "danger" | "success";
}) {
  if (bars.length < 2) return null;

  const stroke =
    tone === "danger"
      ? "var(--color-danger)"
      : tone === "success"
        ? "var(--color-success)"
        : "var(--color-accent)";

  const data = bars.map((b, i) => ({ ...b, last: i === bars.length - 1 }));

  return (
    <div className="dir-spark" data-testid="tile-spark">
      <ResponsiveContainer height="100%" width="100%">
        <BarChart barCategoryGap="18%" data={data}>
          <Bar dataKey="value" isAnimationActive={false} radius={[2, 2, 0, 0]}>
            {data.map((d) => (
              <Cell
                fill={stroke}
                fillOpacity={d.last ? 1 : 0.34}
                key={d.label}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
