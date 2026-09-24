"use client";

import { FileWarning } from "lucide-react";
import { useFormatter, useLocale, useTranslations } from "next-intl";

import { formatBusinessDay } from "@/lib/format-day";
import { useOpenCaseDays } from "@/lib/reconciliation-queries";

/*
 * =============================================================================
 * BOSHQA KUNLARDAGI HAL QILINMAGAN ISHLAR — kun tanlagichi yonida (260924-hpm).
 *
 * ⛔⛔ NEGA KERAK: navbat KUN kesimida va standart kun KECHA, «band, lekin
 *     to'lovsiz» ishi esa kamida 4 kun oldingi sana bilan tug'iladi. Prod'da
 *     5 ta ish 4 hafta ko'rilmadi: ular mavjud edi, xarita ularni sariq
 *     qilib turardi, lekin bu sahifa ularning KUNINI aytmasdi.
 *
 * ⛔ KUN TANLAGICHI BLOKI ICHIDA, alohida blok EMAS: sahifaning blok
 *    to'plami G-29 darvozasi bilan qulflangan va bu e'lon ro'yxat emas —
 *    u tanlagichning YORDAMCHISI (qaysi kunni tanlash kerak). Shu sababli
 *    mazmun atributi ham chiqarilmaydi.
 *
 * ⛔ TANLANGAN KUN RO'YXATDA YO'Q: uning ishlari pastdagi navbatda allaqachon
 *    ko'rinib turibdi. Boshqa ochiq kun bo'lmasa e'lon UMUMAN chizilmaydi —
 *    bo'sh «hammasi joyida» ogohlantirishi ko'zni bo'sh javobga o'rgatardi.
 *
 * ⚠ So'rov xatosi JIM: e'lon qo'shimcha yordam, sahifaning asosiy mazmuni
 *   emas — uning xatosi navbat bloklarining o'z xato holatlarini
 *   takrorlamaydi.
 * =============================================================================
 */
export function OpenCaseDays({
  day,
  onSelect,
}: {
  day: string;
  onSelect: (next: string) => void;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const locale = useLocale();
  const query = useOpenCaseDays();

  const others = (query.data?.days ?? []).filter((item) => item.day !== day);
  if (others.length === 0) return null;

  return (
    /*
     * ⚠ JONLI HUDUD ROLI YO'Q (G-38): e'lon sahifa bilan birga chiziladi
     *   va hech kim kutmagan paytda skrinriderda gapirmasligi kerak.
     */
    <div className="mt-3 flex gap-3 rounded-md bg-warning/20 p-4 text-text">
      <FileWarning aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
      <div className="flex min-w-0 flex-1 flex-col gap-2">
        <p className="text-sm font-semibold">{t("recon.openDaysTitle")}</p>
        <ul className="flex flex-wrap gap-2">
          {others.map((item) => (
            <li key={item.day}>
              <button
                className="inline-flex min-h-11 items-center rounded-md border border-border-ui bg-surface px-3 text-sm font-semibold tabular-nums transition-colors hover:bg-surface-muted focus-visible:ring-2 focus-visible:ring-accent/25 focus-visible:outline-none"
                onClick={() => onSelect(item.day)}
                type="button"
              >
                {formatBusinessDay(format, item.day, locale)}
                {" · "}
                {t("recon.openDaysCount", { count: item.open_count })}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
