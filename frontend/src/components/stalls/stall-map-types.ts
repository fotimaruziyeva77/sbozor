/*
 * =============================================================================
 * Plan-xaritaning RENDER kontrakti (UI-SPEC §7.2).
 *
 * NEGA `lib/api-types.ts` DA EMAS: bu API kontrakti emas. Server xom
 * faktlarni beradi (`status` + `has_vendor`), quyidagi `tone` esa ulardan
 * HOSIL QILINADI. Uni API tipiga qo'shish 6-fazada "to'langan/qarzdor"
 * manbasi qo'shilganda API kontraktini o'zgartirishni talab qilardi;
 * hosila funksiyada esa u bitta joyga qo'shiladi.
 * =============================================================================
 */

/**
 * Katakning rang/uslub sinfi.
 *
 * ⚠ SCOPE FENCE: 2-fazada FAQAT birinchi uchtasi HOSIL QILINADI (D-20).
 * Oxirgi uchtasi 6–7 fazalarda yonadi — tip HOZIR e'lon qilinadi, uslub
 * esa HOZIR yozilmaydi.
 *
 * Tipni oldindan e'lon qilishning aniq foydasi `stall-tone.ts` da:
 * `TONE_STYLES` to'liq `Record` bo'lgani uchun 6-fazada `debt` uslubini
 * yozish UNUTILSA kod umuman kompilyatsiya bo'lmaydi. Aks holda qarzdor
 * rasta jimgina "hammasi joyida" ko'rinishida chizilardi.
 */
export type StallTone =
  | "neutral" // faol
  | "muted" // ta'mirda
  | "off" // yopiq
  | "paid" // 6-faza — to'langan
  | "debt" // 6-faza — qarzdor
  | "mismatch"; // 7-faza — nomuvofiqlik

/**
 * Bitta katak.
 *
 * Koordinata YO'Q va qo'shilmaydi (D-19): joylashuv CSS Grid bilan hosil
 * bo'ladi, ya'ni saqlangan `x`/`y` bo'lmagani uchun ular eskirib ham
 * qolmaydi.
 */
export type StallCell = {
  id: string;
  code: string;
  tone: StallTone;
  hasVendor: boolean;
};

/** Zona bloki. `name` — DB KONTENTI va TARJIMA QILINMAYDI (D-16). */
export type ZoneBlock = {
  id: string;
  name: string;
  /**
   * Kataklar INSON-RAQAMLI tartibda (2 < 10 < 100) va bu tartib SERVERDAN
   * keladi (`code_sort`, §7.3). Frontend uni QAYTA SARALAMAYDI: klient
   * saralashi uchala tilda boshqa natija berardi va xarita bilan reestr
   * ajralib ketardi.
   */
  cells: StallCell[];
};
