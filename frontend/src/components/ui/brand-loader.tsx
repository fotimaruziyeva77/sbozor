"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * BREND-LOADER — bozorga mos yuklanish belgisi (2026-08-25, foydalanuvchi).
 *
 * ⛔⛔ BU SPINNER EMAS — VA BU LOYIHA QOIDASI (masterplan §3.2 «Hech
 *     qachon: aylanuvchi spinner»). Aylanish o'rniga UCH RASTA USTUNI
 *     navbat bilan «nafas oladi» — bozor rastalarining metaforasi va u
 *     faqat `opacity`/`transform` bilan ishlaydi (G-motion-3(a) ruxsat
 *     to'plami).
 *
 * ⛔ SKELETONNING O'RNINI BOSMAYDI: kontent SHAKLI ma'lum joyda skeleton
 *    afzal (karta joyida karta ko'rinishi). Bu komponent SAHIFA/BO'LIm
 *    darajasidagi kutish uchun — Suspense fallback, sessiya tiklanishi,
 *    dastlabki yuklanish. Ikkalasi bitta savolga ikki javob emas: biri
 *    «shu joyda nima bo'ladi», ikkinchisi «tizim ishlayapti».
 *
 * ⚠ `prefers-reduced-motion` da ustunlar QIMIRLAMAYDI — statik uch ustun
 *   + matn qoladi (globals.css dagi media qoidasi).
 *
 * ⚠ `role="status"` + ko'rinadigan/sr-only matn: skrinrider kutishni
 *   eshitadi (WCAG 4.1.3).
 * =============================================================================
 */
export function BrandLoader({
  label,
  className,
  compact = false,
}: {
  /** Ko'rinadigan izoh; berilmasa `common.loading` sr-only bo'ladi. */
  label?: string;
  className?: string;
  /** Ixcham shakl — karta ichidagi kichik joylar uchun. */
  compact?: boolean;
}) {
  const t = useTranslations();

  return (
    <div
      aria-busy="true"
      className={cn(
        "flex flex-col items-center justify-center gap-3",
        compact ? "py-6" : "py-16",
        className,
      )}
      role="status"
    >
      <span
        aria-hidden="true"
        className={cn(
          "brand-loader",
          compact ? "brand-loader-compact" : null,
        )}
      >
        <span className="brand-loader-bar" />
        <span className="brand-loader-bar" />
        <span className="brand-loader-bar" />
      </span>
      {label === undefined ? (
        <span className="sr-only">{t("common.loading")}</span>
      ) : (
        <span className="text-sm font-semibold text-text-muted">{label}</span>
      )}
    </div>
  );
}
