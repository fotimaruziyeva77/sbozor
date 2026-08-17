import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * Yuklanish skeleti (UI-SPEC §9.1).
 *
 * NEGA SKELETON, matnli "Yuklanmoqda" EMAS: 1000 katakli xarita
 * sahifasida yalang'och matn layoutni yig'ib, keyin uni 1000 katak bilan
 * yoyadi — kuchli CLS. Skeleton balandlikni ushlab turadi.
 *
 * DIQQAT: bu faylda matn YO'Q. Skrinrider uchun e'lon KONTEYNER
 * darajasida beriladi va BIR MARTA eshitiladi, har blok uchun emas:
 *
 *   <div role="status" aria-busy="true">
 *     <span className="sr-only">{t("common.loading")}</span>
 *     <Skeleton className="h-24" />
 *     <Skeleton className="h-24" />
 *   </div>
 *
 * `motion-shimmer` (09-UI-SPEC §12.5) — pulsatsiya emas, shimmer:
 * `globals.css` dagi statik gradient + `background-position` animatsiyasi
 * (1.5s, kompozitor-do'st). `motion-reduce:animate-none` QOLADI — u
 * ikkinchi qatlam va global `@media (prefers-reduced-motion)` bloki bilan
 * birga ishlaydi (WCAG 2.3.3): harakat vestibulyar sezgir foydalanuvchi
 * uchun bezovta.
 */
export type SkeletonProps = ComponentPropsWithRef<"div">;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "motion-shimmer rounded-sm bg-surface-muted motion-reduce:animate-none",
        className,
      )}
      {...props}
    />
  );
}
