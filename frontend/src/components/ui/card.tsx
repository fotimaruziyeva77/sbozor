import type { ComponentPropsWithRef } from "react";

import { cn } from "@/lib/cn";

/*
 * Apple-uslub: jadval emas, karta va toza ro'yxatlar (topshiriq §7).
 * DIQQAT: matn yo'q — barcha mazmun `children` bo'lib keladi.
 */
export type CardProps = ComponentPropsWithRef<"div">;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        /*
         * ⛔⛔ KARTA SHAFFOF EMAS — VA BU O'LCHOVDAN KEYINGI QAROR (260819).
         *
         *   Avval bu yerda `app-surface` sinfi ham bor edi (ish yuzasi
         *   fonining ustida «suzsin» degan niyat bilan). Brauzerda
         *   o'lchanganda ma'lum bo'ldiki, u UMUMAN ISHLAMAYAPTI:
         *   `.app-scene .app-surface` qoidasi `@layer components` da,
         *   `bg-surface` esa utilita — kaskadda utilita yutadi va karta
         *   to'liq shaffofmas bo'lib qolardi. Ustiga `backdrop-filter:
         *   blur(8px)` HAMON hisoblanardi: sof narx, nol samara.
         *
         *   Bu ayniqsa telefonda muhim — kassirning ro'yxatlarida
         *   o'nlab karta bor va har biriga blur berish scroll'ni
         *   arzon Androidda sekinlashtiradi. Shuning uchun shaffoflik
         *   FAQAT sarlavha va pastki panelda qoldi (ular bittadan).
         */
        "rounded-lg border border-border bg-surface shadow-card",
        /*
         * Hover ko'tarilishi (09-UI-SPEC §12.3). Yumshoqlik `@theme` dagi
         * `--default-transition-*` juftligidan keladi (bare `transition`
         * utilitasi) — `transition-[...]` TAQIQ (G-motion-3(b)).
         *
         * ⛔ Sticky-hover yo'q [O'LCHANDI, 09-02 T1]: Tailwind 4.3.3 `hover:`
         * variantini `@media (hover: hover)` ichida kompilyatsiya qiladi
         * (postcss probe: `.hover\:-translate-y-0\.5` qoidasi media bloki
         * ichida chiqdi) — telefonda bu qoida umuman qo'llanmaydi, shuning
         * uchun `globals.css` fallback'i KERAK EMAS.
         */
        "transition hover:-translate-y-0.5 hover:shadow-raised",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: CardProps) {
  return (
    <div
      className={cn("flex flex-col gap-1 px-5 pt-5 pb-3", className)}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: CardProps) {
  return <div className={cn("px-5 pb-5", className)} {...props} />;
}
