"use client";

import { Equal, TrendingDown, TrendingUp } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { formatAmount } from "@/lib/format-number";

/*
 * =============================================================================
 * FARQ KATAGI — ⛔ IKKI TOMONLAMA VA UCH KANALLI (§11.5, §12.4, D-26).
 *
 * ⛔ ANALOGI YO'Q (§5.4) — soxta analog berilmadi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ D-26 SO'ZMA-SO'Z: «ORTIQCHA NAQD HAM SIGNAL — UNI JIMGINA YUTISH
 *    KAMOMADNI YASHIRISH BILAN BIR XIL XATO.»
 * -----------------------------------------------------------------------
 * Shuning uchun `> 0` shoxi `= 0` ga QO'SHILMAYDI va «hammasi joyida»
 * deb ko'rsatilmaydi. Uchala yo'nalish HAR BIRI ⛔ UCH KANALDA
 * (WCAG 1.4.1 — rang HECH QACHON yagona signal emas):
 *
 *   | qiymat | RANG                            | IKONKA       | ⛔ MATN     |
 *   |--------|---------------------------------|--------------|-------------|
 *   | `< 0`  | `bg-danger/12 text-danger-text` | TrendingDown | «Kamomad»   |
 *   | `> 0`  | `bg-warning/20 text-text`       | TrendingUp   | «Ortiqcha»  |
 *   | `= 0`  | `Badge tone="success"`          | Equal        | «Mos keldi» |
 *
 * ⛔ MUTLAQ QIYMAT OLINMAYDI — ISHORA MA'NO TASHIYDI (Pitfall 7).
 *    Manfiy qiymat ekranda MINUS bilan ko'rinadi. Ishorani yo'qotib,
 *    ma'noni faqat rangga yuklash — ranggi ko'rmaydigan foydalanuvchi
 *    uchun kamomad bilan ortiqchani BIR XIL qilardi.
 *    ⚠ Taqiqlangan funksiya nomi bu izohda LITERAL yozilmaydi: qabul
 *      mezoni uni `grep` bilan sanaydi (kodbaza konvensiyasi,
 *      `badge.tsx:24-26`).
 *
 * ⛔ OGOHLANTIRISH RANGI MATN SIFATIDA ISHLATILMAYDI (§12.2): u oq fonda
 *    2,03:1 — falokat. Sariq tint FAQAT `bg-warning/20 text-text` shaklida
 *    va u o'lchangan 15,64:1 beradi [KOD: `badge.tsx:17-25`].
 *
 * ⛔ `font-mono` — qiymat TIK SOLISHTIRILADI (§7.2): jadval ustunida
 *    razryadlar bir-birining ustida turishi kerak.
 * =============================================================================
 */

/** Uch yo'nalish — to'rtinchisi YO'Q. */
export type VarianceDirection = "short" | "over" | "match";

/**
 * Qiymat -> yo'nalish — SOF FUNKSIYA (§S-13).
 *
 * ⚠ `0` ALOHIDA shox va u `> 0` ga qo'shilmaydi: «mos keldi» — HUKM,
 *   «ortiqcha» esa ANOMALIYA. Ikkisini birlashtirish ortiqchani
 *   muvaffaqiyat rangi bilan bo'yardi.
 */
export function varianceDirection(soum: number): VarianceDirection {
  if (soum < 0) return "short";
  if (soum > 0) return "over";
  return "match";
}

export function VarianceCell({ soum }: { soum: number }) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const direction = varianceDirection(soum);

  const view = {
    short: {
      Icon: TrendingDown,
      className: "bg-danger/12 text-danger-text",
      label: t("billing.varianceShort"),
    },
    over: {
      Icon: TrendingUp,
      /* ⛔ Matn `text-text` — ogohlantirish rangi matn sifatida EMAS. */
      className: "bg-warning/20 text-text",
      label: t("billing.varianceOver"),
    },
    match: {
      Icon: Equal,
      className: "",
      label: t("billing.varianceMatch"),
    },
  }[direction];

  const content = (
    <>
      <view.Icon aria-hidden="true" className="size-3" />
      {/* ⛔ ISHORA SAQLANADI: `-35 000` ekranda MINUS bilan chiziladi. */}
      <span className="font-mono tabular-nums">{formatAmount(format, soum, locale)}</span>
      <span>{t("billing.amountUnit")}</span>
      {/* ⛔ UCHINCHI KANAL — MATN. Rang va ikonka yolg'iz yetmaydi. */}
      <span className="font-semibold">{view.label}</span>
    </>
  );

  if (direction === "match") {
    return (
      <Badge className="gap-1 whitespace-nowrap" tone="success">
        {content}
      </Badge>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold whitespace-nowrap ${view.className}`}
    >
      {content}
    </span>
  );
}
