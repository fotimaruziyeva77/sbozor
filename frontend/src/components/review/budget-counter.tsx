import { useTranslations } from "next-intl";

/*
 * =============================================================================
 * BYUDJET HISOBLAGICHI — ⛔ PROGRESS BAR EMAS (UI-SPEC §7.3 [QAROR]).
 *
 * Bar navbatni TUGATILADIGAN O'YINGA aylantiradi: to'lgan chiziq
 * «bajarilmagan ish» ni ko'rsatadi va bu aynan shosha-pisha bosishning
 * rag'bati. Hisoblagich esa FAKT aytadi, MAQSAD qo'ymaydi — «bugun 12 ta
 * javob berdim» va «12/50 ni tugatishim kerak» ikki xil ish tuyg'usi.
 *
 * Byudjetning O'ZI ham kvota emas, DIQQAT CHEGARASI (§16.2): charchagan
 * holda berilgan javob ma'lumotni buzadi, ya'ni chegara nazoratchini
 * emas, O'LCHOVNI qo'riqlaydi.
 *
 * ⚠ `slot-editor.tsx` ning `7 / 12` naqshi qayta ishlatildi: `text-xs`,
 *   `font-mono`, `tabular-nums`. `font-mono` — HUJJATLASHTIRILGAN
 *   ISTISNO (§9.4): ustunlashgan sonlar hisoblagich almashganda
 *   SAKRAMAYDI.
 *
 * ⚠ MATN SHU YERDA YO'Q — u `review.today` kalitidan keladi va uchala
 *   tilda bir xil shaklda ({done} / {max}).
 * =============================================================================
 */
export function BudgetCounter({
  answered,
  budget,
}: {
  answered: number;
  budget: number;
}) {
  const t = useTranslations();

  return (
    <p className="font-mono text-xs tabular-nums text-text-muted">
      {t("review.today", { done: answered, max: budget })}
    </p>
  );
}
