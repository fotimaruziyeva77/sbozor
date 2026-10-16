import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * SAHIFA XULOSASI — kichik ko'rsatkich kataklari (261016).
 *
 * Buyurtmachi bo'limlarni «tushunarsiz» va «juda oddiy» dedi. Har bo'lim
 * endi ro'yxatdan OLDIN bitta qator bilan boshlanadi: «nechta, qanchasi
 * joyida, qanchasi muammoli» — ro'yxatni o'qimasdan javob.
 *
 * ⛔ RANG MA'NO: `success` — joyida, `warning` — e'tibor, `danger` —
 *    muammo, `accent`/`neutral` — oddiy son. Rang yolg'iz emas: ikonka va
 *    yorliq har doim bor.
 *
 * ⛔ BOSILADIGAN KATAK — FILTR: `onClick` berilsa katak tugma bo'ladi va
 *    `aria-pressed` bilan tanlangan holatini aytadi («faqat sotuvchisiz
 *    rastalarni ko'rsat»). Boshqa sahifaga olib ketmaydi.
 * =============================================================================
 */

export type StatTone = "neutral" | "accent" | "success" | "warning" | "danger";

export function StatStrip({
  children,
  label,
  className,
}: {
  children: ReactNode;
  /** Skrinrider uchun guruh nomi. */
  label: string;
  className?: string;
}) {
  return (
    <div aria-label={label} className={cn("stat-strip", className)} role="group">
      {children}
    </div>
  );
}

export function StatTile({
  icon: Icon,
  label,
  value,
  unit,
  note,
  tone = "neutral",
  active,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  unit?: string;
  note?: ReactNode;
  tone?: StatTone;
  /** Filtr sifatida tanlanganmi (faqat `onClick` bilan ma'noli). */
  active?: boolean;
  onClick?: () => void;
}) {
  const body = (
    <>
      <span aria-hidden="true" className={cn("stat-tile-icon", `stat-tone-${tone}`)}>
        <Icon className="size-4" />
      </span>
      <span className="stat-tile-text">
        <span className="stat-tile-label">{label}</span>
        <span className="stat-tile-value">
          {value}
          {unit === undefined ? null : <span className="stat-tile-unit"> {unit}</span>}
        </span>
        {note === undefined ? null : <span className="stat-tile-note">{note}</span>}
      </span>
    </>
  );

  if (onClick === undefined) {
    return <div className="stat-tile">{body}</div>;
  }

  return (
    <button
      aria-pressed={active === true}
      className={cn("stat-tile stat-tile-button", active === true && "stat-tile-active")}
      onClick={onClick}
      type="button"
    >
      {body}
    </button>
  );
}
