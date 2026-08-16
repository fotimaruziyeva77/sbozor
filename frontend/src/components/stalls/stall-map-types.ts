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
 * ⚠ SCOPE FENCE (2-faza): FAQAT birinchi uchtasi INVENTAR holatidan hosil
 * qilinadi (D-20). Qolganlari — rasta ustiga qo'yiladigan TO'LOV qatlami
 * va ular `dayToneOf()` dan keladi.
 *
 * Tipni oldindan e'lon qilishning aniq foydasi `stall-tone.ts` da:
 * `TONE_STYLES` to'liq `Record` bo'lgani uchun `debt` uslubini yozish
 * UNUTILSA kod umuman kompilyatsiya bo'lmaydi. Aks holda qarzdor rasta
 * jimgina "hammasi joyida" ko'rinishida chizilardi.
 *
 * ⛔ `free` NING MA'NOSI — «SOTUVCHI BIRIKTIRILMAGAN», BANDLIK EMAS
 *    (quick 260816-75e, D-C3). MARKET-06 matni «yashil bo'sh» ni CV
 *    bandligi ma'nosida yozgan; CV modeli esa yo'q (AI-02 `Blocked`),
 *    ya'ni bandlik O'LCHANMAGAN va o'lchanmagan miqdorni rang bilan
 *    da'vo qilish TAQIQLANADI (D-01). Legenda ham AYNAN shu ma'noni
 *    yozadi — «bo'sh» so'zi bu tone atrofida ISHLATILMAYDI.
 */
export type StallTone =
  | "neutral" // faol
  | "muted" // ta'mirda
  | "off" // yopiq
  | "paid" // to'lov qatlami — bugungi patta to'liq yopilgan
  | "debt" // to'lov qatlami — bugungi patta kutilyapti
  | "free" // to'lov qatlami — sotuvchi biriktirilmagan (D-C3)
  | "mismatch"; // to'lov qatlami — ochiq nomuvofiqlik

/**
 * Katakning to'lov holati SO'Z bilan — `aria-label` va legenda uchun.
 *
 * ⛔ RANGDAN MUSTAQIL UCHINCHI KANAL (WCAG 1.4.1): kalit to'liq yozilgan
 *    va u yopiq birlashma, ya'ni tarjima kalitini noto'g'ri terish
 *    KOMPILYATSIYA XATOSI bo'ladi. Erkin `string` bo'lganda `t()`
 *    ish vaqtida `MISSING_MESSAGE` qaytarardi va katak jimgina kalit
 *    matnini o'qib berardi.
 */
export type StallDayStateKey =
  | "map.dayStatePaid"
  | "map.dayStateDue"
  | "map.dayStateMismatch"
  | "map.dayStateFree"
  | "map.dayStateNoBilling";

/**
 * Bitta katak.
 *
 * Koordinata YO'Q va qo'shilmaydi (D-19): joylashuv CSS Grid bilan hosil
 * bo'ladi, ya'ni saqlangan `x`/`y` bo'lmagani uchun ular eskirib ham
 * qolmaydi.
 *
 * ⛔ TO'LOV MAYDONLARI KATAK MA'LUMOTINING ICHIDA (Pitfall 8): ular
 *    `StallCell` obyektining bir qismi va `StallCellProps` ga ALOHIDA
 *    prop bo'lib CHIQMAYDI. Tanlangan rasta identifikatoriga bog'liq
 *    birorta prop bu yerga tushmaydi — aks holda har bosishda 1000 katak
 *    qayta render bo'lardi.
 */
export type StallCell = {
  id: string;
  code: string;
  tone: StallTone;
  hasVendor: boolean;
  /**
   * To'lov qatlamining toni. `null` — qatlam yo'q (huquq yo'q, qoralama
   * bozor, hali yuklanmadi) YOKI holat `no_billing`, ya'ni rang ATAYIN
   * qo'yilmaydi. Ikkala holatda ham katak INVENTAR tonida qoladi.
   */
  dayTone: StallTone | null;
  /** To'lov holatining so'zi; `null` — `aria-label` HOZIRGIDEK qoladi. */
  dayStateKey: StallDayStateKey | null;
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
