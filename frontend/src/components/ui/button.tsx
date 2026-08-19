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
    // ⛔⛔ `aria-disabled` HAM KO'RINADI (260819, Chromeda o'lchandi).
    //
    // §14.3 ataylab `disabled` o'rniga `aria-disabled` ishlatadi: o'chirilgan
    // tugma fokus olmaydi va skrinrider uni o'qimaydi, ya'ni «nega
    // bosilmayapti?» savoliga javob beradigan joy qolmaydi.
    //
    // LEKIN o'lchov shuni ko'rsatdi: `aria-disabled="true"` da `opacity: 1`,
    // fon esa FAOL tugmaniki bilan bir xil edi — ya'ni holat skrinriderga
    // aytilardi, KO'ZGA esa umuman aytilmasdi. Kassir to'liq «tirik»
    // ko'rinadigan pul tugmasini bosaverardi.
    //
    // ⛔ `pointer-events` OLIB TASHLANMAYDI: bosish HODISASI kerak —
    //    aynan o'shanda sabab matni chiqadi (`payment-bar.tsx`).
    "aria-disabled:opacity-60 aria-disabled:cursor-not-allowed",
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
        // `hero` — landing birlamchi CTA, AYNAN 2 joy: hero va yakuniy
        // demo-forma (10-UI-SPEC §7.4). 56px balandlik — 09-UI-SPEC §6
        // dagi MAVJUD bo'shliq istisnosi (mobil panel/tasdiq tugmasi),
        // yangi istisno emas; `text-lg` (18px) — chegarasiz rol (L-3).
        hero: "min-h-14 px-8 text-lg",
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
