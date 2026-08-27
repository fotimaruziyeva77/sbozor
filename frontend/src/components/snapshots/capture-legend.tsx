"use client";

import {
  CheckCircle2,
  CircleSlash,
  Clock,
  FileWarning,
  ImageOff,
  Loader2,
  Minus,
  MoonStar,
  XCircle,
} from "lucide-react";
import { useTranslations } from "next-intl";

import type { CaptureCellState } from "@/components/snapshots/capture-cell";
import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * LEGENDA — DOIMIY, YOPILMAYDIGAN, TO'LIQ (§6.5).
 *
 * Hujayrada matn yo'q [O'LCHANDI: M-4], ya'ni ikonka lug'ati BIRDAN-BIR
 * o'rgatuvchi yuza bo'lib qoladi. Shundan uchta qoida kelib chiqadi va
 * ularning har biri alohida sabab bilan:
 *
 * ⛔ TO'QQIZALA YOZUV DOIM KO'RINADI — o'sha kunda uchramasa ham.
 *    «Faqat mavjudlarini ko'rsatish» legendani KUNGA QARAB o'zgaruvchan
 *    qilardi: admin ikonkani hech qachon o'rganmasdi, chunki lug'at har
 *    kuni boshqa bo'lardi. Aynan `Olinmadi` esa eng kam uchraydigan va
 *    eng muhim yozuv — u faqat yomon kunda ko'rinardi.
 *
 * ⛔ LEGENDA YIG'ILADIGAN BLOK ICHIDA EMAS. Yopiq legenda — o'qilmagan
 *    legenda; foydalanuvchi uni ochish kerakligini bilmaydi va ikonka
 *    lug'ati taxminga qolardi.
 *
 * ⛔ HUJAYRA LEGENDAGA `aria-describedby` BILAN BOG'LANMAYDI (§6.5).
 *    175 hujayrada bu skrinriderni bo'g'ardi: har fokus ko'chishida
 *    to'qqiz yozuvli lug'at qayta o'qilardi. Hujayraning to'liq
 *    `aria-label` i yetarli. Yozuvlar baribir `id` oladi — kelajakdagi
 *    ishlovchi bog'lash uchun tayyor nuqtani ko'rsin va uni ATAYIN
 *    qo'ymaganimizni bu izohdan o'qisin.
 *
 * ⚠ MOBILDA HAM YASHIRILMAYDI (§13.2): `flex-wrap` bilan uch-to'rt
 *   qatorga tushadi. Yig'ib qo'yish yuqoridagi ikkinchi sababning aynan
 *   o'zi bo'lardi.
 * =============================================================================
 */

type LegendEntry = {
  Icon: typeof CheckCircle2;
  dashed: boolean;
  labelKey:
    | "snapshots.cell.ok"
    | "snapshots.cell.dark"
    | "snapshots.cell.blank"
    | "snapshots.cell.corrupt"
    | "snapshots.cell.failed"
    | "snapshots.cell.missed"
    | "snapshots.cell.pending"
    | "snapshots.cell.running"
    | "snapshots.cell.skipped";
  state: CaptureCellState;
  tint: string;
};

/** Tartib §6.4 jadvalidagi C1…C9 bilan AYNI — lug'at va jadval bir yo'lda o'qiladi. */
const ENTRIES: readonly LegendEntry[] = [
  {
    Icon: CheckCircle2,
    dashed: false,
    labelKey: "snapshots.cell.ok",
    state: "ok",
    tint: "border-border bg-success/12 text-success-text",
  },
  {
    Icon: MoonStar,
    dashed: false,
    labelKey: "snapshots.cell.dark",
    state: "dark",
    tint: "border-border bg-warning/20 text-text",
  },
  {
    Icon: ImageOff,
    dashed: false,
    labelKey: "snapshots.cell.blank",
    state: "blank",
    tint: "border-border bg-warning/20 text-text",
  },
  {
    Icon: FileWarning,
    dashed: false,
    labelKey: "snapshots.cell.corrupt",
    state: "corrupt",
    tint: "border-border bg-warning/20 text-text",
  },
  {
    Icon: XCircle,
    dashed: false,
    labelKey: "snapshots.cell.failed",
    state: "failed",
    tint: "border-border bg-danger/12 text-danger-text",
  },
  {
    Icon: CircleSlash,
    dashed: true,
    labelKey: "snapshots.cell.missed",
    state: "missed",
    tint: "border-danger/50 bg-danger/12 text-danger-text",
  },
  {
    Icon: Clock,
    dashed: false,
    labelKey: "snapshots.cell.pending",
    state: "pending",
    tint: "border-border bg-surface-muted text-text-muted",
  },
  {
    Icon: Loader2,
    dashed: false,
    labelKey: "snapshots.cell.running",
    state: "running",
    tint: "border-border bg-surface-muted text-text",
  },
  {
    Icon: Minus,
    dashed: true,
    labelKey: "snapshots.cell.skipped",
    state: "skipped",
    tint: "border-border bg-surface-muted text-text-muted",
  },
];

/** Legenda yozuvining `id` si — hujayradan bog'lanish uchun TAYYOR nuqta. */
export function legendEntryId(state: CaptureCellState): string {
  return `capture-legend-${state}`;
}

export function CaptureLegend({ className }: { className?: string }) {
  const t = useTranslations();

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <p className="text-xs text-text-muted">{t("snapshots.legend")}</p>
      <ul className="flex flex-wrap gap-x-4 gap-y-2">
        {ENTRIES.map((entry) => (
          <li
            className="flex items-center gap-1 text-xs"
            id={legendEntryId(entry.state)}
            key={entry.state}
          >
            <span
              aria-hidden="true"
              className={cn(
                "flex size-5 items-center justify-center rounded-sm border",
                entry.tint,
                entry.dashed ? "border-dashed" : "border-solid",
              )}
            >
              <entry.Icon className="size-3" />
            </span>
            {t(entry.labelKey)}
          </li>
        ))}
      </ul>
    </div>
  );
}
