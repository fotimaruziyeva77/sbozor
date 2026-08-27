/*
 * =============================================================================
 * 4-QADAM — SUMMA RO'YXATGA UCHADI (09-UI-SPEC §8.1, sketch 001-B [QULF]).
 *
 * FLIP klon: «Kutilayotgan patta» summasi (`from`) dan to'lovlar ro'yxati
 * (`to`) gacha 400ms (`--motion-slow`) uchish. Ijro 09-RESEARCH «Kod
 * namunalari 3» dan KO'CHIRILGAN — qayta ixtiro yo'q.
 *
 * -----------------------------------------------------------------------
 * QAROR 1 — NEGA IMPERATIV: React komponenti EMAS, `useState` YO'Q, JSX YO'Q
 * -----------------------------------------------------------------------
 * (a) `setState` UMUMAN bo'lmagani uchun G-motion-2(d) («holat animatsiyaga
 *     bog'lanmaydi») tavtologiya emas, MEXANIK: buzish uchun avval holat
 *     kiritish kerak bo'ladi va AST darvozasi shu lahzada qizaradi.
 * (b) Klon React daraxtidan TASHQARIDA (`document.body` bolasi) — 6-qadam
 *     (M-9) `PendingCard`/`PaymentBar` ni DARHOL unmount qilganda ham klon
 *     omon qoladi va uchishni tugatadi. Test uni `document.body` da SANAY
 *     oladi — G-motion-1(c) ning aynan o'lchovi.
 *
 * ⛔ Nomi `ui/` ga ko'tarilmaydi (09-UI-SPEC §3.4): kontrakti — DOMEN
 *    qoidasi (bloklamaslik majburiyati), umumiy «muvaffaqiyat animatsiyasi»
 *    emas.
 *
 * -----------------------------------------------------------------------
 * QAROR 2 — NEGA HAMMA XOSSA INLINE (sinf emas)
 * -----------------------------------------------------------------------
 * jsdom Tailwind CSS'ni yuklamaydi: sinf orqali berilgan `pointer-events`
 * hisoblangan uslubda `"auto"` bo'lib qoladi [O'LCHANDI, 09-RESEARCH
 * Tuzoq 1]. Inline uslub esa o'qiladi — ya'ni T-09-05 («klon bosishni
 * yutmaydi») mitigatsiyasi FAQAT inline shaklda O'LCHANADIGAN bo'ladi.
 * Davomiylik va egri esa TOKENDAN: inline `transition` satrida
 * `var(--motion-slow) var(--ease-out)` — bu Tailwind `transition-[...]`
 * utilitasi EMAS, ya'ni G-motion-3(b) skaniga tushmaydi.
 *
 * -----------------------------------------------------------------------
 * QAROR 3 — NEGA BO'LISH AMALI YO'Q
 * -----------------------------------------------------------------------
 * jsdom'da `getBoundingClientRect()` hammasi 0 [O'LCHANDI] — masofaga
 * bo'lish testda `NaN` berardi. Farq (`b.left - a.left`) esa 0 bo'lib,
 * transform satri baribir yaroqli qoladi. Shu sabab progress/nisbat
 * hisoblanmaydi: uchish to'liq CSS transition zimmasida.
 *
 * -----------------------------------------------------------------------
 * QAROR 4 — `setTimeout` FAQAT TOZALASH (G-motion-2(d))
 * -----------------------------------------------------------------------
 * 450ms = `--motion-slow` (400ms) + 50ms zaxira. Callback ichida YAGONA
 * amal — `clone.remove()`. Holat o'zgartirish (`set[A-Z]…`) 0 marta va bu
 * AST bilan o'lchanadi (`success-choreography.test.tsx`). Reduced-motion
 * ostida klon UMUMAN yaratilmaydi — tozalash ham kerak emas.
 *
 * -----------------------------------------------------------------------
 * RAD ETILGAN MUQOBILLAR
 * -----------------------------------------------------------------------
 * - Web Animations API (`element.animate`) — jsdom'da `undefined`
 *   [O'LCHANDI]: o'lchab bo'lmaydigan mexanizm tanlanmaydi.
 * - `motion` kutubxonasi — L-8 talqini 0 KB (09-UI-SPEC §3.2): bu ~40
 *   qatorlik vanilla, kutubxona 0 ta noyob imkoniyat berardi.
 * - Bayram-zarra effektlari — YOZILMAYDI (09-UI-SPEC §9, deferred-items.md):
 *   tetikning haqiqat manbai serverda hali mavjud emas; G-motion-1(d)
 *   ta'rif skanida buni mexanik qo'riqlaydi.
 * =============================================================================
 */

import { prefersReducedMotion } from "@/lib/motion";

export type FlyAmountOptions = {
  /** Uchish MANBAI — «Kutilayotgan patta» summa elementi. */
  from: HTMLElement | null;
  /** Uchish NISHONI — to'lovlar ro'yxati konteyneri. */
  to: HTMLElement | null;
};

/**
 * Summani ro'yxatga «uchiradi» — bloklamaydigan, holatga tegmaydigan bezak.
 *
 * ⛔ Istisnoni O'ZI YUTMAYDI: himoya qatlami BITTA joyda —
 *    `collect-session.tsx::onWritten` dagi `try/catch` da yashaydi
 *    (G-motion-2(e)). Ikki joyda yashasa biri jimgina o'lik bo'lardi.
 */
export function flyAmountToList({ from, to }: FlyAmountOptions): void {
  /* ⛔ Reduced-motion: klon UMUMAN yaratilmaydi — natija esa AYNI (§8.4). */
  if (prefersReducedMotion()) return;
  if (from === null || to === null) return;

  const a = from.getBoundingClientRect();
  const b = to.getBoundingClientRect();

  const clone = from.cloneNode(true) as HTMLElement;
  clone.setAttribute("aria-hidden", "true");
  clone.style.pointerEvents = "none";
  clone.style.position = "fixed";
  clone.style.left = `${a.left}px`;
  clone.style.top = `${a.top}px`;
  clone.style.willChange = "transform";
  clone.style.transition =
    "transform var(--motion-slow) var(--ease-out), opacity var(--motion-slow) var(--ease-out)";
  document.body.appendChild(clone);

  requestAnimationFrame(() => {
    clone.style.transform = `translate(${b.left - a.left}px, ${b.top - a.top}px) scale(0.85)`;
    clone.style.opacity = "0";
  });

  /* ⛔ FAQAT TOZALASH — holat o'zgartirish yo'q (QAROR 4, AST o'lchaydi). */
  window.setTimeout(() => clone.remove(), 450);
}
