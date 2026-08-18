/*
 * =============================================================================
 * O'ZBEK LOTIN SANASI — ⛔ BRAUZER BERMAYDIGAN MA'LUMOTNING O'RNI.
 *
 * ⛔⛔ NIMANI TUZATADI (o'lchangan 2026-08-18, jonli Chrome'da):
 *
 *   new Intl.DateTimeFormat("uz-Latn", { dateStyle: "medium" }).format(d)
 *     -> "2026 M08 15"          ⛔ CLDR ILDIZ shabloni
 *
 *   Ayni chaqiruv `uz-Cyrl` da "15 авг, 2026", `ru` da "15 авг. 2026 г." —
 *   ya'ni nosozlik FAQAT o'zbek LOTIN yozuvida va u bizning ASOSIY tilimiz.
 *   Aniq shakl ham yordam bermaydi: { month: "long" } ham "M08" beradi,
 *   chunki brauzer ICU'sida bu yozuv uchun oy nomlari UMUMAN yo'q.
 *   Node'ning to'liq ICU'si ularni biladi — shuning uchun nosozlik SSR'da
 *   ko'rinmay, brauzerda ko'rinadi.
 *
 * ⛔ Shuning uchun oy nomlari SHU YERDA, kodda. Bu tarjima EMAS —
 *    brauzerda yetishmayotgan CLDR jadvalining o'rni. Tarjima katalogiga
 *    qo'yilsa, uchala tilda takrorlanib, ikkitasida hech qachon
 *    ishlatilmasdi va drift manbai bo'lardi.
 *
 * ⛔ FAQAT `uz-Latn` uchun. Qolgan tillar `Intl` da to'g'ri ishlaydi va
 *    ularga tegilmaydi — ikkinchi haqiqat manbai yaratmaymiz.
 * =============================================================================
 */

/** Ilova tili o'zbek lotin yozuvidami. */
export function isUzLatn(locale: string): boolean {
  return locale === "uz-Latn" || locale === "uz";
}

/**
 * Oy nomlari — bosh harfsiz (o'zbek tilida oy nomi jumla o'rtasida kichik
 * harf bilan yoziladi). Indeks `Date#getUTCMonth()` bilan bir xil: 0 = yanvar.
 */
const MONTHS = [
  "yanvar",
  "fevral",
  "mart",
  "aprel",
  "may",
  "iyun",
  "iyul",
  "avgust",
  "sentabr",
  "oktabr",
  "noyabr",
  "dekabr",
] as const;

/**
 * `2026-08-18` -> «18-avgust, 2026».
 *
 * ⛔ UTC qismlari o'qiladi: chaqiruvchi kunni TUSHGA langarlangan lahza
 *    sifatida beradi (`format-day.ts` sharti), ya'ni mahalliy mintaqa
 *    kunni surib yubormaydi.
 */
export function uzLatnDate(date: Date): string {
  const month = MONTHS[date.getUTCMonth()];
  return `${date.getUTCDate()}-${month}, ${date.getUTCFullYear()}`;
}

/** `2026-08-18 09:41` -> «18-avgust, 2026 · 09:41» (vaqt chaqiruvchidan). */
export function uzLatnDateTime(date: Date, timeText: string): string {
  return `${uzLatnDate(date)} · ${timeText}`;
}
