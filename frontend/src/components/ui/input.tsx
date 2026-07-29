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
        "flex h-10 w-full rounded-sm border border-border bg-surface px-3 py-2",
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
