"use client";

import { useEffect, useRef, useState } from "react";
import { Minus, Plus, X } from "lucide-react";

import { cn } from "@/lib/cn";

/*
 * KO'RISH REJIMI — dalil kadrini haqiqatan kattalashtirish (N-1).
 *
 * ⛔ Nima uchun alohida qatlam, dialog emas: dialoglarimiz o'lchamga
 *    qulflangan (eng kattasi 480px) va ular QAROR so'raydigan oyna. Bu esa
 *    qaror emas — QARASH. Shuning uchun butun ekranni egallaydi.
 *
 * ⛔ Zona konturi rasm bilan BIR transformda: u rasmning ustidagi mustaqil
 *    qatlam emas, rasmning qismi. Alohida masshtablansa, kontur pikselga
 *    to'g'ri tushmay qolardi — bu esa noto'g'ri qarorga olib boradi.
 *
 * ⛔ Yuklab olish/ulashish YO'Q — dalil kadri ekrandan chiqmaydi
 *    (`evidence-frame.tsx` bilan bir xil qoida).
 */

const MIN_SCALE = 1;
const MAX_SCALE = 6;
const SCALE_STEP = 1;

export type ZoomLayerProps = {
  src: string;
  alt: string;
  title: string;
  closeLabel: string;
  polygon: readonly (readonly [number, number])[];
  onClose: () => void;
};

export function ZoomLayer({
  alt,
  closeLabel,
  onClose,
  polygon,
  src,
  title,
}: ZoomLayerProps) {
  const [scale, setScale] = useState(MIN_SCALE);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number } | null>(null);
  const layerRef = useRef<HTMLDivElement | null>(null);

  /* Ochilganda fokus qatlamga — Escape darhol ishlasin. */
  useEffect(() => {
    layerRef.current?.focus();
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  /* Masshtab 1 ga qaytsa surish ham nolga qaytadi — aks holda rasm
     ko'rinmaydigan joyda «qolib ketadi». */
  function changeScale(next: number) {
    const clamped = Math.min(MAX_SCALE, Math.max(MIN_SCALE, next));
    setScale(clamped);
    if (clamped === MIN_SCALE) setOffset({ x: 0, y: 0 });
  }

  return (
    <div
      aria-label={title}
      aria-modal="true"
      className="fixed inset-0 z-50 flex flex-col bg-black/90"
      ref={layerRef}
      role="dialog"
      tabIndex={-1}
    >
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <p className="text-sm font-semibold text-white">{title}</p>
        <div className="flex items-center gap-2">
          <button
            aria-label={`${title} −`}
            className="flex size-11 cursor-pointer items-center justify-center rounded-md border border-white/30 text-white"
            onClick={() => changeScale(scale - SCALE_STEP)}
            type="button"
          >
            <Minus aria-hidden="true" className="size-4" />
          </button>
          <span
            className="min-w-11 text-center font-mono text-sm text-white tabular-nums"
            data-numeric
          >
            ×{scale}
          </span>
          <button
            aria-label={`${title} +`}
            className="flex size-11 cursor-pointer items-center justify-center rounded-md border border-white/30 text-white"
            onClick={() => changeScale(scale + SCALE_STEP)}
            type="button"
          >
            <Plus aria-hidden="true" className="size-4" />
          </button>
          <button
            className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-white/30 px-4 text-sm font-semibold text-white"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" className="size-4" />
            {closeLabel}
          </button>
        </div>
      </div>

      <div
        className={cn(
          "flex flex-1 items-center justify-center overflow-hidden",
          scale > MIN_SCALE ? "cursor-grab active:cursor-grabbing" : null,
        )}
        onPointerDown={(event) => {
          if (scale === MIN_SCALE) return;
          dragRef.current = {
            x: event.clientX - offset.x,
            y: event.clientY - offset.y,
          };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const start = dragRef.current;
          if (start === null) return;
          setOffset({ x: event.clientX - start.x, y: event.clientY - start.y });
        }}
        onPointerUp={() => {
          dragRef.current = null;
        }}
      >
        {/* Rasm va kontur BITTA o'ramda — bitta transform, bitta haqiqat. */}
        <span
          className="relative inline-flex max-h-full max-w-full"
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            alt={alt}
            className="max-h-[80vh] max-w-full object-contain"
            draggable={false}
            src={src}
          />
          <svg
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 size-full"
            preserveAspectRatio="none"
            viewBox="0 0 1000 1000"
          >
            <polygon
              className="fill-accent/10 stroke-accent"
              points={polygon.map(([x, y]) => `${x * 1000},${y * 1000}`).join(" ")}
              strokeWidth={6}
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </span>
      </div>
    </div>
  );
}
