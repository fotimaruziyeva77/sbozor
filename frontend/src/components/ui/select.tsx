import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * NATIVE `<select>` — Radix Select ATAYIN ishlatilmaydi.
 *
 * Sabab did emas: telefonda native element tizimning o'z tanlagichini
 * ochadi (iOS'da g'ildirak, Android'da to'liq ekranli ro'yxat) va u
 * barmoq bilan har qanday maxsus qurilmadan qulayroq. Bozor admini va
 * kassir bu ilovani telefonda ishlatadi (PROJECT.md).
 *
 * DIQQAT: bu faylda matn YO'Q — `<option>` lar `children` bo'lib keladi.
 *
 * `border-ui`, `border` EMAS: chegara bu elementni boshqaruv elementi
 * sifatida tanitadi, ya'ni WCAG 2.2 SC 1.4.11 (>=3:1) qo'llanadi.
 */
export type SelectProps = ComponentPropsWithRef<"select">;

export function Select({ className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        "h-10 w-full rounded-sm border border-border-ui bg-surface px-3",
        "text-sm text-text",
        "outline-none transition-colors",
        "focus-visible:border-accent focus-visible:ring-2 focus-visible:ring-accent/25",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-[invalid=true]:border-danger",
        "aria-[invalid=true]:focus-visible:border-danger",
        "aria-[invalid=true]:focus-visible:ring-danger/25",
        className,
      )}
      {...props}
    />
  );
}
