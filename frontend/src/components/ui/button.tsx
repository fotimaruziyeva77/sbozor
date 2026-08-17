import type { ComponentPropsWithRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/cn";

/*
 * DIQQAT: bu faylda foydalanuvchiga ko'rinadigan hech qanday matn yo'q.
 * Barcha matn `next-intl` orqali chaqiruvchi komponentdan `children` bo'lib keladi.
 */
const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap",
    "rounded-md font-semibold select-none",
    // `duration-(--motion-fast)` — Tailwind 4 `(--var)` sintaksisi: davomiylik
    // token reyestridan keladi, sehrli son yozilmaydi (G-motion-3(b)).
    "transition-colors duration-(--motion-fast)",
    // Bosish-masshtabi `stalls/stall-cell.tsx:127` naqshidan ko'tarildi —
    // reduced-motion bilan JUFT (G-motion-1, 09-UI-SPEC §12.1 / M-8).
    "active:scale-[0.97] motion-reduce:scale-100",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        /*
         * Hover soyasi FAQAT allaqachon `shadow-card` ko'targan variantlarda
         * (§12.1) — `ghost`/`secondary` ataylab yassi, ularga soya yo'q.
         */
        default:
          "bg-accent text-accent-fg shadow-card hover:bg-accent-hover hover:shadow-raised",
        secondary:
          "border border-border bg-surface text-text hover:bg-surface-muted",
        ghost: "bg-transparent text-text hover:bg-surface-muted",
        destructive:
          "bg-danger text-danger-fg shadow-card hover:bg-danger-hover hover:shadow-raised",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        // `lg` — kassir mobil oqimidagi barmoq nishoni: kamida 44px
        // balandlik (WCAG 2.5.5). O'lcham EMAS, nishon kattalashadi:
        // shkalada 16px yo'q, chunki 14px bilan ierarxiya bermaydi.
        lg: "min-h-11 px-6 py-3 text-sm",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  },
);

export type ButtonProps = ComponentPropsWithRef<"button"> &
  VariantProps<typeof buttonVariants>;

export function Button({
  className,
  variant,
  size,
  type = "button",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  );
}

export { buttonVariants };
