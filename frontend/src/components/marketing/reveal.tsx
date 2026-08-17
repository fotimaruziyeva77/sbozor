"use client";

import type { CSSProperties, ReactNode } from "react";
import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/lib/motion";

/*
 * =============================================================================
 * SCROLL-REVEAL O'RAMASI — `IntersectionObserver` NING YAGONA UMUMIY TA'RIFI
 * (10-UI-SPEC §4.4 klient orollari reyestri; G-land-1(a) shu faylni kutadi).
 *
 * ⛔ Kodbazada `IntersectionObserver` BOSHQA HECH QAYERDA ishlatilmagan
 *    [O'LCHANDI: grep 0 natija] — vanilladan yozildi; yagona qisman ilhom
 *    `lib/motion.ts` ning bir martalik o'qish idiomasi.
 *
 * ⛔ BOSHLANG'ICH HOLAT — KO'RINADIGAN (Tuzoq 4 sinfi): `opacity: 0` bilan
 *    yashirish YO'Q. JS kelmasa yoki observer ishlamasa kontent yo'qolib
 *    qolmasligi shart — `.motion-enter` faqat KIRISH animatsiyasini QO'SHADI
 *    (mavjud sinf, L-10 — qayta yozilmaydi), ko'rinishni boshqarmaydi.
 *
 * ⛔ `prefersReducedMotion()` tekshiruvi effektning BIRINCHI qatorida:
 *    `true` bo'lsa observer UMUMAN QURILMAYDI va kontent darhol ko'rinadi.
 *
 * ⛔ Bir martalik guard: ochilgandan keyin `disconnect()` (takroriy kuzatuv
 *    yo'q — T-10-12 mitigatsiyasi) va `unmount` tozalashida ham `disconnect()`
 *    (ochilmagan holatda ham).
 *
 * ⛔ `setTimeout`/`setInterval` bu faylda 0 marta (G-land-3(c): sahifadagi
 *    yagona avtomatik harakat hero-scene'da).
 *
 * `onReveal` — step-line iste'moli uchun: 3-qadam seksiyasi har qadam
 * ko'ringanda `data-step` ni oshirishi kerak va bu qo'shimcha observer
 * ochmasdan shu callback orqali bo'ladi (10-06 Task 3).
 * =============================================================================
 */
export type RevealProps = {
  children: ReactNode;
  className?: string;
  /** Stagger indeksi — `.motion-enter` ning `--i` o'zgaruvchisi (60ms qadam). */
  delayIndex?: number;
  /** Ko'rinish chegarasi (`IntersectionObserver` threshold). */
  threshold?: number;
  /** Ochilish paytida BIR marta chaqiriladi (masalan, step-line `data-step`). */
  onReveal?: () => void;
};

export function Reveal({
  children,
  className,
  delayIndex = 0,
  threshold = 0.2,
  onReveal,
}: RevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const revealedRef = useRef(false);
  const onRevealRef = useRef(onReveal);
  const [entered, setEntered] = useState(false);

  /* Callback'ning oxirgi nusxasi — observer effekti qayta obuna bo'lmaydi. */
  useEffect(() => {
    onRevealRef.current = onReveal;
  });

  useEffect(() => {
    /* ⛔ BIRINCHI qator: reduced-motion'da observer QURILMAYDI (reja sharti). */
    if (prefersReducedMotion()) return;
    /* Observer yo'q muhit (juda eski brauzer) — kontent baribir ko'rinadi. */
    if (typeof IntersectionObserver === "undefined") return;
    const node = ref.current;
    if (node === null) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        /* Bir martalik guard — mock/qayta otishlarda ham ikkinchi ijro yo'q. */
        if (revealedRef.current) return;
        revealedRef.current = true;
        setEntered(true);
        onRevealRef.current?.();
        observer.disconnect();
      },
      { threshold },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold]);

  return (
    <div
      className={cn(entered ? "motion-enter" : null, className)}
      ref={ref}
      /* `--i` — revenue-card.tsx naqshi; inline geometriya YO'Q (G-land-3(b)). */
      style={{ "--i": delayIndex } as CSSProperties}
    >
      {children}
    </div>
  );
}
