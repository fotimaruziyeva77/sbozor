"use client";

import { useEffect, useRef, useState } from "react";

/*
 * =============================================================================
 * SANALIB CHIQADIGAN SON (2026-08-26, buyurtmachi: «sonlar pastdan
 * o'zgarib xuddi raddomni aylanganday bo'ladi — unaqa bo'lmasin,
 * kreativ bo'lsin»).
 *
 * Slayd-kirish o'rniga QIYMAT O'ZI sanaladi: 0 dan (yoki avvalgi
 * qiymatdan) yakuniy songa ~700ms ichida ease-out bilan yetadi —
 * premium dashboardlarning tanish «pul jonlanishi».
 *
 * ⛔ BU CSS ANIMATSIYASI EMAS — matn yangilanishi (smena sekundomeri
 *    bilan bir sinf), ya'ni G-motion kadr-reyestriga tegmaydi.
 *
 * ⚠ `prefers-reduced-motion` HURMAT QILINADI: harakat cheklangan
 *   foydalanuvchi yakuniy sonni DARHOL ko'radi.
 *
 * ⚠ SON HAR DOIM HAQIQIY MANBADAN: tween faqat KO'RSATISH; oraliq
 *   kadrda ham format funksiyasi chaqiruvchiniki — pul formati bitta
 *   joyda qoladi (format-number.ts).
 * =============================================================================
 */
export function CountUp({
  value,
  format,
  durationMs = 700,
}: {
  /** Yakuniy qiymat — butun son (so'm/sanoq). */
  value: number;
  /** Ko'rsatish formati — chaqiruvchidan (formatSoum/formatAmount). */
  format: (value: number) => string;
  durationMs?: number;
}) {
  const [shown, setShown] = useState(value);
  const fromRef = useRef(value);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || fromRef.current === value) {
      fromRef.current = value;
      setShown(value);
      return;
    }

    const from = fromRef.current;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      /* ease-out cubic — oxirida sekinlashib «qo'nadi». */
      const eased = 1 - (1 - t) ** 3;
      setShown(Math.round(from + (value - from) * eased));
      if (t < 1) {
        frameRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = value;
      }
    };
    frameRef.current = requestAnimationFrame(tick);
    return () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      fromRef.current = value;
    };
  }, [value, durationMs]);

  return <>{format(shown)}</>;
}
