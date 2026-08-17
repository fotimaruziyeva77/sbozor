"use client";

/*
 * =============================================================================
 * COUNT-UP — SON SANALADIGAN 600ms JONLANISH (09-UI-SPEC §10.3, L-5).
 *
 * rAF halqasi + kubik ease (`1 - (1 - p)³`). Boshlang'ich kadr — 0 (yangi
 * qiymatda — oldingi ko'rsatilgan son), oxirgi kadr — ⛔ QIYMATNING O'ZI,
 * ease natijasi EMAS: chaqiruvchi `useFormatter().number()` bilan
 * formatlaganda ekranda AYNAN server bergan son turadi (08 D-03).
 *
 * -----------------------------------------------------------------------
 * ⛔ NEGA KUTUBXONA EMAS (09-UI-SPEC §3.2 «Qo'lda yozilmasin» jadvali)
 * -----------------------------------------------------------------------
 * Oxirgi kadr `next-intl` formatterining natijasi bo'lishi SHART —
 * sanoq kutubxonasi (masalan `react-countup`) o'z formatlagichini olib
 * keladi va u locale kontekstini BILMAYDI. Bundan tashqari L-8 byudjeti
 * 0 KB: bu modul ~40 qator va u testda O'LCHANADI, kutubxona esa faqat
 * ishonch talab qilardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ PUL — BUTUN SO'M (CLAUDE.md «What NOT to Use»)
 * -----------------------------------------------------------------------
 * Oraliq kadrlar `Math.round()` bilan yaxlitlanadi; kasr formatlagich
 * yo'llarining nomi bu faylda LITERAL ham yozilmaydi — manba skani
 * (`headline-card.test.tsx`) ularning yo'qligini o'lchaydi.
 *
 * -----------------------------------------------------------------------
 * ⛔ `value === null` — HALQA UMUMAN BOSHLANMAYDI (T-05-04)
 * -----------------------------------------------------------------------
 * «O'lchanmagan son chizilmaydi»: `null` da hook `null` qaytaradi va
 * birorta kadr sanalmaydi — nol YOZILMAYDI.
 *
 * -----------------------------------------------------------------------
 * ⛔ REDUCED-MOTION — HALQASIZ OXIRGI HOLAT (09-UI-SPEC §4.4 qoida 5)
 * -----------------------------------------------------------------------
 * Global CSS `@media` bloki (G-motion-1(a)) FAQAT CSS animatsiyalarini
 * o'chiradi — rAF halqasi JS va u o'zini o'zi to'xtatishi shart. Guard
 * `stall-map.tsx:46,56` naqshi: jsdom'da `matchMedia` YO'Q [O'LCHANDI,
 * 09-RESEARCH Tuzoq 1] — funksiya yo'qligida animatsiya YOQILGAN deb
 * hisoblanadi (mavjud bo'lmagan API «cheklov yo'q» degani).
 *
 * Qanday tekshiriladi: `headline-card.test.tsx` («useCountUp — son
 * kontrakti») — soxta taymerlar rAF'ni patch qiladi [O'LCHANDI] va har
 * kadr deterministik o'lchanadi.
 * =============================================================================
 */

import { useEffect, useRef, useState } from "react";

/** Standart davomiylik — L-5 (600ms); real-vaqt yangilanishi 400ms beradi. */
const DEFAULT_DURATION_MS = 600;

/** Kubik ease-out — sketch 001-B tasdiqlagan egri (L-2 bilan uyg'un). */
function easeOutCubic(progress: number): number {
  return 1 - (1 - progress) ** 3;
}

/** jsdom-xavfsiz guard — `matchMedia` yo'q bo'lsa animatsiya YOQILGAN. */
function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  if (typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Sonni 0 dan (yoki oldingi ko'rsatilgan qiymatdan) `value` gacha sanaydi.
 *
 * ⛔ Hook FAQAT SONNI qaytaradi — formatlash chaqiruvchida
 *    (`useFormatter().number()`): shunda oxirgi kadr formatterniki bo'ladi.
 * ⛔ `durationMs` KEYINGI animatsiyaga qo'llanadi — yugurayotgan halqa
 *    o'z boshlang'ich davomiyligida tugaydi (revenue kartasi birinchi
 *    ko'rinishda 600ms, yangilanishda 400ms beradi).
 */
export function useCountUp(
  value: number | null,
  durationMs: number = DEFAULT_DURATION_MS,
): number | null {
  const [shown, setShown] = useState<number | null>(() =>
    value !== null && prefersReducedMotion() ? value : null,
  );
  const shownRef = useRef<number | null>(shown);
  const durationRef = useRef(durationMs);

  /* Davomiylik sinxroni ANIMATSIYADAN OLDIN turadi (e'lon tartibi ma'noli). */
  useEffect(() => {
    durationRef.current = durationMs;
  }, [durationMs]);

  useEffect(() => {
    if (value === null) return;

    if (prefersReducedMotion()) {
      /* Halqa o'rniga darhol oxirgi holat — §4.4 qoida 5. */
      shownRef.current = value;
      setShown(value);
      return;
    }

    const from = shownRef.current ?? 0;
    const to = value;
    if (from === to) {
      shownRef.current = to;
      setShown(to);
      return;
    }

    const duration = durationRef.current;
    let start: number | null = null;
    let frame: number | null = null;

    const step = (now: number): void => {
      if (start === null) start = now;
      const progress = Math.min((now - start) / duration, 1);

      if (progress >= 1) {
        /* ⛔ Oxirgi kadr — qiymatning O'ZI, ease natijasi emas. */
        shownRef.current = to;
        setShown(to);
        frame = null;
        return;
      }

      const next = Math.round(from + (to - from) * easeOutCubic(progress));
      shownRef.current = next;
      setShown(next);
      frame = requestAnimationFrame(step);
    };

    frame = requestAnimationFrame(step);

    return () => {
      if (frame !== null) cancelAnimationFrame(frame);
    };
  }, [value]);

  if (value === null) return null;
  return shown ?? 0;
}
