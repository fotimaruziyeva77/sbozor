import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * Holat yorlig'i. 1-fazada `user-list.tsx` ichidagi LOKAL funksiya edi;
 * 2-fazada rasta holati, import natijasi va usta qadami ham shuni
 * ishlatadi, shuning uchun bitta manbaga ko'chirildi.
 *
 * DIQQAT: bu faylda matn YO'Q — mazmun `children` bo'lib keladi.
 *
 * RANG YAGONA SIGNAL EMAS (WCAG 1.4.1): badge doim MATN tashiydi, ya'ni
 * rang faqat ikkinchi kanal. Shu sababli badge hech qachon `truncate`
 * qilinmaydi (UI-SPEC §5.1 qoida 3) — konteyner o'sadi.
 *
 * TONE'LARNING KONTRAST ASOSI (o'lchandi, §4.2):
 *   success  bg-success/12 + text-success-text -> 5.35:1
 *   danger   bg-danger/12  + text-danger-text  -> 5.54:1
 *   accent   bg-accent/10  + text-accent-text  -> 5.29:1
 *   warning  bg-warning/20 + text-text         -> 15.64:1
 *
 * `--color-warning` MATN sifatida oq fonda 2.03:1 — falokat. Shuning
 * uchun sariq tintdagi matn `text-text` bo'ladi va ogohlantirish rangi
 * matn uchun HECH QACHON ishlatilmaydi. Bu taqiq grep darvozasi bilan
 * qulflangan, shuning uchun taqiqlangan utilita nomi bu izohda literal
 * sifatida yozilmaydi (kodbaza konvensiyasi).
 */
export type BadgeTone =
  | "neutral"
  | "muted"
  | "accent"
  | "success"
  | "warning"
  | "danger";

const TONE: Record<BadgeTone, string> = {
  neutral: "bg-surface-muted text-text",
  muted: "bg-surface-muted text-text-muted",
  accent: "bg-accent/10 text-accent-text",
  success: "bg-success/12 text-success-text",
  warning: "bg-warning/20 text-text",
  danger: "bg-danger/12 text-danger-text",
};

export type BadgeProps = ComponentPropsWithRef<"span"> & {
  tone?: BadgeTone;
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        // `px-2 py-1` — 4-panjara (UI-SPEC §2). Eski qiymatlar (10px va
        // 2px) panjaradan tushib qolgan bir martalik qarorlar edi.
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold",
        TONE[tone],
        className,
      )}
      {...props}
    />
  );
}
