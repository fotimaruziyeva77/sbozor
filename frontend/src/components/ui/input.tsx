import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * DIQQAT: matn yo'q — `placeholder` / `aria-label` chaqiruvchi tomondan
 * `next-intl` orqali beriladi.
 *
 * Xato holati `aria-invalid={true}` bilan belgilanadi (ASVS/WCAG): bitta
 * atribut ham vizual, ham skrinrider uchun ishlaydi.
 */
export type InputProps = ComponentPropsWithRef<"input">;

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        // `border-ui`, `border` EMAS: chegara bu elementni boshqaruv
        // elementi sifatida tanitadigan YAGONA signal, ya'ni WCAG 2.2
        // SC 1.4.11 (≥3:1) qo'llanadi. `--color-border` o'lchangan 1.28:1
        // — dekorativ chegara uchun; `--color-border-ui` 3.64:1.
        "flex h-10 w-full rounded-sm border border-border-ui bg-surface px-3 py-2",
        "text-sm text-text placeholder:text-text-muted",
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
