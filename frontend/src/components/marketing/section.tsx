import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * Marketing seksiya ritmi — `py-16` (64px, mobil) / `py-24` (96px, desktop)
 * qiymatlarining YAGONA uyi (10-UI-SPEC §8.2, G-land-5(c) shu faylga
 * `deepEqual` bilan qulflaydi — ikkinchi marketing faylida ishlatilishi
 * darvozada qizaradi).
 *
 * NEGA 48px EMAS: 48px — admin ro'yxatining ritmi; marketing sahifasida u
 * bloklarni bir-biriga yopishtirib hikoyaning nafasini o'ldiradi. 64 va 96 —
 * ikkalasi ham 4 ning VA 16 ning karrasi, ya'ni panjara arifmetikasidan
 * chiqmaydi; ular ATAYLAB reference to'plamiga (4..48) kiritilmagan —
 * bu seksiyalararo MAKRO-ritm, komponent ichi bo'shlig'i emas.
 *
 * Naqsh: `ui/card.tsx` — `cn()` bilan `className` uzatish, matn yo'q.
 * `id` standart proplar orqali keladi (ankerlar: `#kontent`, `#ishonch`,
 * `#demo`); `title` (§15.11) seksiya sarlavhasini `<h2>` sifatida chizadi —
 * sahifada bitta `<h1>` (hero), har seksiya `<h2>`.
 *
 * Ichki konteyner: fon (`className` orqali) to'liq kenglikda yoyiladi,
 * kontent esa markazlashgan ustunda qoladi.
 */
export type SectionProps = ComponentPropsWithRef<"section"> & {
  /** Seksiya sarlavhasi — `<h2>` (ierarxiya darajasi o'tkazib yuborilmaydi). */
  title?: string;
};

export function Section({ className, title, children, ...props }: SectionProps) {
  return (
    <section className={cn("py-16 md:py-24", className)} {...props}>
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6">
        {title ? (
          <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        ) : null}
        {children}
      </div>
    </section>
  );
}
