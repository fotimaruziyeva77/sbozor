import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/*
 * Bo'sh holat: sarlavha + tavsif + ixtiyoriy amal (UI-SPEC §9.2).
 *
 * DIQQAT: bu faylda matn YO'Q — uchala bo'lak ham tarjima qilingan holda
 * chaqiruvchidan keladi.
 *
 * KOMPONENT "NEGA BO'SH" DEGANINI BILMAYDI va bilishi ham shart emas.
 * Ikki xil bo'sh holat — "hech narsa yo'q" va "filtr hech narsa topmadi" —
 * ATAYIN ajratiladi, chunki ularning KEYINGI QADAMI boshqa:
 *
 *   hech narsa yo'q  -> amal: yaratish / import
 *   filtr topmadi    -> amal: filtrni tozalash
 *
 * Farq chaqiruvchining `title` / `description` / `action` tanloviga
 * tushadi; shu sababli bu yerda hech qanday shart yo'q.
 */
export type EmptyStateProps = {
  /** Ixtiyoriy amal tugmasi — keyingi qadamni ANIQ ko'rsatadi. */
  action?: ReactNode;
  className?: string;
  description: ReactNode;
  title: ReactNode;
};

export function EmptyState({
  action,
  className,
  description,
  title,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-2 px-4 py-12 text-center",
        className,
      )}
    >
      <p className="text-lg font-semibold">{title}</p>
      <p className="max-w-prose text-sm text-text-muted">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
