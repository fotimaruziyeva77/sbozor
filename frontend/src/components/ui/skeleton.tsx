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
 * `motion-reduce:animate-none` — `prefers-reduced-motion` hurmat qilinadi
 * (WCAG 2.3.3): pulsatsiya vestibulyar sezgir foydalanuvchi uchun bezovta.
 */
export type SkeletonProps = ComponentPropsWithRef<"div">;

export function Skeleton({ className, ...props }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-sm bg-surface-muted motion-reduce:animate-none",
        className,
      )}
      {...props}
    />
  );
}
