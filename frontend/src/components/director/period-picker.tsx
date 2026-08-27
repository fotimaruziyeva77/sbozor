"use client";

import { CalendarRange } from "lucide-react";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";
import type { Period, PeriodKind } from "@/components/director/period";
import { PERIOD_LABEL_KEY, periodRange } from "@/components/director/period";

/*
 * =============================================================================
 * DAVR FILTRI — panelning yagona boshqaruvi (260819).
 *
 * ⛔⛔ NEGA KERAK BO'LDI: panel kechagi kunga qotirilgan edi va direktor
 *     «bugun qanday ketyapti» degan savoliga javob ololmasdi.
 *     Foydalanuvchi to'g'ridan-to'g'ri shuni so'radi: bugungi ma'lumot,
 *     kechagisi va kalendardan tanlangan oraliq.
 *
 * ⛔ TO'RT TAYYOR TUGMA + ORALIQ: tayyor tugmalar bir bosishda javob
 *    beradi (kunlik ish), kalendar esa tekshiruv yoki hisobot uchun
 *    (kamdan-kam, lekin zarur). Faqat kalendar qoldirilsa har kirishda
 *    ikki sana tanlash kerak bo'lardi.
 *
 * ⛔ `<input type="date">` — QO'SHIMCHA KUTUBXONASIZ. Telefonda u
 *    tizimning O'Z kalendarini ochadi (barmoqqa mos, o'zbek lokali
 *    bilan), desktopda esa brauzernikini. Uchinchi tomon kalendari
 *    ~40 KB qo'shardi va mobil tajribani YOMONLASHTIRARDI.
 *
 * ⛔ `max` — bugundan keyingi sana TANLANMAYDI: kelajakdagi kun uchun
 *    ma'lumot bo'lishi mumkin emas va bo'sh ekran «tizim ishlamayapti»
 *    degan taassurot berardi.
 *
 * ⚠ Nishonlar 44px (§15.10): bu boshqaruvni direktor telefonda ham
 *   bosadi.
 * =============================================================================
 */

/** Tayyor rejimlar — chapdan o'ngga, kundalik ishlatilish tartibida. */
const QUICK: readonly Exclude<PeriodKind, "custom">[] = [
  "today",
  "yesterday",
  "week",
  "month",
];

export function PeriodPicker({
  onChange,
  period,
  todayIso,
}: {
  onChange: (next: Period) => void;
  period: Period;
  todayIso: string;
}) {
  const t = useTranslations();
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div
        aria-label={t("director.periodAria")}
        className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border bg-surface p-1"
        role="group"
      >
        {QUICK.map((kind) => {
          const isActive = period.kind === kind;
          return (
            <button
              aria-current={isActive ? "true" : undefined}
              className={cn(
                "inline-flex min-h-11 items-center rounded-md px-3 text-sm font-semibold",
                "transition-colors",
                isActive
                  ? "bg-accent text-accent-fg"
                  : "text-text-muted hover:bg-surface-muted hover:text-text",
              )}
              key={kind}
              onClick={() => onChange(periodRange(kind, todayIso))}
              type="button"
            >
              {t(PERIOD_LABEL_KEY[kind])}
            </button>
          );
        })}
      </div>

      {/*
       * ⛔ Oraliq HAR DOIM ko'rinadi (yashirilgan «Ko'proq» ostida emas):
       *    hokimlik yoki soliq so'rovi aynan ANIQ oraliq bo'yicha keladi
       *    va u paytda qidirib o'tirish mumkin emas.
       */}
      <div
        className={cn(
          "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-lg border px-3",
          period.kind === "custom"
            ? "border-accent bg-accent/10"
            : "border-border bg-surface",
        )}
      >
        <CalendarRange
          aria-hidden="true"
          className="size-4 shrink-0 text-text-muted"
        />
        <input
          aria-label={t("director.periodFromAria")}
          className="min-h-11 bg-transparent text-sm text-text outline-none"
          max={period.to}
          onChange={(event) => {
            const from = event.target.value;
            if (from === "") return;
            onChange({ kind: "custom", from, to: period.to });
          }}
          type="date"
          value={period.from}
        />
        <span aria-hidden="true" className="text-text-muted">
          —
        </span>
        <input
          aria-label={t("director.periodToAria")}
          className="min-h-11 bg-transparent text-sm text-text outline-none"
          max={todayIso}
          min={period.from}
          onChange={(event) => {
            const to = event.target.value;
            if (to === "") return;
            onChange({ kind: "custom", from: period.from, to });
          }}
          type="date"
          value={period.to}
        />
      </div>
    </div>
  );
}
