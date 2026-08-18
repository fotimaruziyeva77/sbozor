"use client";

import { RotateCcw } from "lucide-react";
import { useFormatter, useNow, useTranslations } from "next-intl";

import { cn } from "@/lib/cn";

/*
 * MA'LUMOT YOSHI — «Sbozor Direktor» dizaynining qatlami (brief §9).
 *
 * ⛔ NEGA KERAK: hisobot bloklari 5 daqiqa keshda turadi va oyna fokusiga
 *    qайta so'ramaydi. Ya'ni ekrandagi 5 daqiqalik eski raqam yangi
 *    raqamdan HECH NIMA bilan farq qilmasdi. Tekshiruvchi uchun bu
 *    «bu son qachonlik?» degan javobsiz savol.
 *
 * ⛔ NEGA AVTOMATIK YANGILANISH EMAS: jimgina o'zgaradigan raqam «men
 *    boshqa son ko'rgandim» nizosining manbai (mahsulotning yozilgan
 *    qarori). To'g'ri yechim — yangilanish BORLIGINI aytish, bosishni
 *    foydalanuvchiga qoldirish.
 *
 * ⛔ YAGONA JOY: har kartada qo'lda takrorlanmaydi. Aks holda birida
 *    «Yangilandi», boshqasida «Oxirgi yangilanish» bo'lib ketardi.
 */

/** Ma'lumot shu muddatdan eski bo'lsa — yozuv ogohlantirish rangiga o'tadi. */
const STALE_AFTER_MS = 15 * 60 * 1000;

export type CardFreshnessProps = {
  /** `react-query` ning `dataUpdatedAt` qiymati (ms). 0 — hali yuklanmagan. */
  updatedAt: number;
  onRefresh: () => void;
  /** Qayta so'rov ketayotgan payt — tugma bloklanadi (⛔ `disabled` emas). */
  isRefreshing?: boolean;
};

export function CardFreshness({
  isRefreshing = false,
  onRefresh,
  updatedAt,
}: CardFreshnessProps) {
  const t = useTranslations();
  const format = useFormatter();
  /*
   * ⛔ `Date.now()` RENDERDA CHAQIRILMAYDI (react-hooks/purity).
   *
   * U har renderda boshqa qiymat qaytaradi, ya'ni render SOF EMAS va
   * React uni qayta o'ynatganda natija o'zgarardi. `useNow()` esa
   * `next-intl` provayderidan keladi va testda qotirilishi mumkin —
   * shu sababdan «eskirgan» chegarasi ham SINALADIGAN bo'ladi.
   */
  const now = useNow();

  if (updatedAt === 0) return null;

  const stale = now.getTime() - updatedAt > STALE_AFTER_MS;

  return (
    <div className="flex items-center gap-2">
      <span
        className={cn(
          "text-xs tabular-nums",
          stale ? "text-warning-text" : "text-text-muted",
        )}
        data-stale={String(stale)}
      >
        {t("dashboard.updatedAt", {
          time: format.dateTime(new Date(updatedAt), { timeStyle: "short" }),
        })}
      </span>
      <button
        aria-disabled={isRefreshing ? true : undefined}
        className="inline-flex min-h-8 cursor-pointer items-center gap-1 rounded-sm px-2 text-xs font-semibold text-accent-text hover:bg-surface-muted"
        onClick={() => {
          if (isRefreshing) return;
          onRefresh();
        }}
        type="button"
      >
        <RotateCcw aria-hidden="true" className="size-3" />
        {t("common.retry")}
      </button>
    </div>
  );
}
