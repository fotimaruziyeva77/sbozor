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
    "transition-colors duration-150",
    "disabled:pointer-events-none disabled:opacity-50",
    "[&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  ],
  {
    variants: {
      variant: {
        default: "bg-accent text-accent-fg shadow-card hover:bg-accent-hover",
        secondary:
          "border border-border bg-surface text-text hover:bg-surface-muted",
        ghost: "bg-transparent text-text hover:bg-surface-muted",
        destructive:
          "bg-danger text-danger-fg shadow-card hover:bg-danger-hover",
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
