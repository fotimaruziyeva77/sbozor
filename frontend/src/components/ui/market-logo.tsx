"use client";

import { useState } from "react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

/*
 * =============================================================================
 * BOZOR LOGOTIPI — `public/markets/<bozor id>.webp` (261103, buyurtmachi:
 * «Karmana bozorining o'z logosini qo'y»).
 *
 * ⛔ BOZOR -> FAYL XARITASI YO'Q: fayl nomi bozor identifikatorining O'ZI.
 *    Yangi bozorga logo qo'shish — bitta fayl, kod o'zgarmaydi.
 *
 * ⛔ FAYL BO'LMASA (404) YOKI YUKLANMASA — buzilgan rasm belgisi EMAS,
 *    bozor NOMI matn bo'lib chiqadi (yoki chaqiruvchining `fallback` i).
 *    Logosiz bozor bugungidek ko'rinadi.
 *
 * ⛔ FON VA SOYA QO'SHILMAYDI: rasm shaffof va o'z oq hoshiyasi bilan
 *    yorug' ham, qorong'i temada ham ajralib turadi.
 *
 * ⚠ `next/image` EMAS: kichik statik fayl, o'lchami CSS da; optimizator
 *   `standalone` obrazda alohida jarayon va keshni talab qilardi.
 *   Bozor sessiyadan (klientda) ma'lum bo'ladi — rasm serverda
 *   chizilmaydi, ya'ni `onError` gidratatsiyadan oldin yo'qolmaydi.
 * =============================================================================
 */

export function marketLogoSrc(marketId: string): string {
  return `/markets/${encodeURIComponent(marketId)}.webp`;
}

export function MarketLogo({
  marketId,
  marketName,
  className,
  fallbackClassName,
  fallback,
  decorative = false,
}: {
  marketId: string;
  /** D-16: DB kontenti, tarjima qilinmaydi — `alt` va zaxira matn. */
  marketName: string;
  /** Rasmning o'lchami (balandlik) — chaqiruvchining sinfi. */
  className?: string;
  /** Zaxira matnning sinfi (standart zaxira uchun). */
  fallbackClassName?: string;
  /** Logo yo'q bo'lsa nima chiziladi; `null` — hech narsa. Standart: bozor nomi. */
  fallback?: ReactNode;
  /** Yonida bozor nomi matn bo'lib turibdi — rasm skrinriderga o'qilmaydi. */
  decorative?: boolean;
}) {
  const src = marketLogoSrc(marketId);
  /*
   * ⛔ Xato MANZIL bilan eslab qolinadi, bayroq bilan emas: platforma
   *    admini bozorni almashtirsa yangi bozorning logosi qayta so'raladi.
   */
  const [failedSrc, setFailedSrc] = useState<string | null>(null);

  if (failedSrc === src) {
    if (fallback !== undefined) return <>{fallback}</>;
    return (
      <span className={cn("market-logo-text", fallbackClassName)}>{marketName}</span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- kichik statik fayl, yuqoridagi izoh
    <img
      alt={decorative ? "" : marketName}
      className={cn("market-logo", className)}
      decoding="async"
      onError={() => setFailedSrc(src)}
      src={src}
    />
  );
}
