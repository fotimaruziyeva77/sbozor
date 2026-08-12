/*
 * =============================================================================
 * NOMUVOFIQLIK YUZASINING XATO TAKSONOMIYASI — kod -> {tone} (W0-F7, §14.9).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ NEGA BU REYESTR FRONTENDDA LANGAR VA BACKENDДА EMAS
 * -----------------------------------------------------------------------
 * `billing-errors.ts` backenddagi `billing_errors.py` ning ko'zgusi va
 * `scripts/error-codes.test.mjs` ikkalasini SOLISHTIRADI. Bu yerda esa
 * zanjir ATAYIN bir bo'g'inli va sabab 07-10 SUMMARY ning 3-ochiq
 * bandida O'LCHANGAN:
 *
 *   «Xato kodlari ... `app/services/billing_errors.py` ga QO'SHILMADI va
 *    bu ATAYIN: o'sha reyestrning soni `error-codes.test.mjs` tomonidan
 *    uchala locale'dagi juftlik bilan solishtiriladi, ya'ni yangi kod
 *    matn qo'shilmaguncha o'sha darvozani QIZARTIRARDI.»
 *
 * ⛔ Ya'ni: `billing_errors.py` ga qo'shish `billingConstants.size === 14`
 *    nazorat qiymatini darhol qizartirardi va uni «tuzatish» yagona yo'li
 *    — sonni oshirish, ya'ni nazoratning butun ma'nosini yo'q qilish
 *    bo'lardi (o'sha faylning `occupancyConstants.size === 15` bandida
 *    ochiq yozilgan sinf).
 *
 * ⛔ SHUNING UCHUN BU YERDAGI REYESTR — LANGARNING O'ZI. Darvoza undan
 *    ITERATSIYA QILADI va uchala locale'da `recon.errorCause.{kod}` +
 *    `recon.errorFix.{kod}` juftligini TALAB qiladi; teskari yo'nalishda
 *    esa o'lik kalitni ushlaydi.
 *
 * ⚠ MARSHRUT KODLARI SERVERDA ALLAQACHON QAYTADI (07-10): `not_found`,
 *   `status_unchanged`, `day_in_future`, `cursor_invalid`,
 *   `range_too_wide`, `range_invalid`, `market_not_selected`. Ular bu
 *   yerdagi EKRAN kodlariga xaritalanadi (`reconErrorView`), ya'ni
 *   «server nima qaytardi» va «direktor nima o'qiydi» IKKI BOSHQA
 *   ro'yxat bo'lib qoladi — birinchisi mexanik, ikkinchisi mazmunli.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi; uchala
 *   tildagi matn `frontend/messages/*.json` da (D-02).
 * =============================================================================
 */

/**
 * Nomuvofiqlik ekranining xato kodlari — §14.9 jadvali KOD sifatida.
 *
 * ⛔ HAR BIRI «SABAB + NIMA QILISH KERAK» juftligiga EGA. Yolg'iz sabab
 *    direktorni boshi berk ko'chaga qo'yardi: u nima bo'lganini biladi,
 *    lekin keyingi qadamni bilmaydi (D-02 ning butun mazmuni).
 */
export const RECON_ERROR_CODES = [
  "case_not_found",
  "case_status_conflict",
  "case_resolution_required",
  "case_forbidden",
] as const;

export type ReconErrorCode = (typeof RECON_ERROR_CODES)[number];

/**
 * Xato blokining uchta ko'rinishi — `billing-errors.ts` bilan bir xil shkala.
 *
 * ⚠ `--color-warning` HECH QACHON matn rangi emas (§13.2) — bu qiymat
 *   blok ramkasi va ikonkasini boshqaradi, matnni emas.
 */
export type ReconErrorTone = "neutral" | "warning" | "danger";

/**
 * Kod -> tone. ⛔ `Record<ReconErrorCode, ...>` ATAYIN: yetishmagan kod ham,
 * ortiqcha kod ham TS xatosi.
 */
const RECON_ERROR_TONE: Readonly<Record<ReconErrorCode, ReconErrorTone>> = {
  /* Qator boshqa kunga tegishli yoki o'chirilgan — ro'yxat eskirgan. */
  case_not_found: "warning",
  /*
   * ⛔ `warning`, `danger` EMAS: poyga NOSOZLIK emas — boshqa direktor
   *    o'z ishini qilgan. `danger` uni tizim buzilgandek ko'rsatardi va
   *    foydalanuvchi o'z o'zgarishini qayta yuborishga urinardi (D-14
   *    ning append-only tarixi buni ikki qator qilib yozardi).
   */
  case_status_conflict: "warning",
  /* Foydalanuvchi hech nimani buzmagan — maydon shunchaki to'ldirilmagan. */
  case_resolution_required: "neutral",
  case_forbidden: "danger",
};

export type ReconErrorView = {
  [C in ReconErrorCode]: {
    readonly code: C;
    readonly tone: ReconErrorTone;
    readonly causeKey: `recon.errorCause.${C}`;
    readonly fixKey: `recon.errorFix.${C}`;
  };
}[ReconErrorCode];

export function isReconErrorCode(value: string): value is ReconErrorCode {
  return Object.hasOwn(RECON_ERROR_TONE, value);
}

/**
 * Serverning MEXANIK kodi -> ekranning MAZMUNLI kodi.
 *
 * ⛔ IKKI RO'YXAT ATAYIN AJRATILGAN. Serverniki marshrut qatlamining
 *    haqiqati (`not_found` beshala marshrutda bir xil ma'noda); ekranniki
 *    esa foydalanuvchi o'qiydigan jumla. Ularni birlashtirish «Bu
 *    nomuvofiqlik topilmadi» matnini kun tanlagichning `day_in_future`
 *    javobiga ham berardi.
 *
 * ⚠ Xaritada YO'Q kod `null` qaytaradi va chaqiruvchi `errors.generic`
 *   ga tushadi: xom `detail`, stack izi yoki SQL matni foydalanuvchiga
 *   HECH QACHON chiqmaydi.
 */
const SERVER_CODE_MAP: Readonly<Record<string, ReconErrorCode>> = {
  not_found: "case_not_found",
  status_unchanged: "case_status_conflict",
  case_status_conflict: "case_status_conflict",
  case_resolution_required: "case_resolution_required",
  forbidden: "case_forbidden",
};

/** Kod -> sabab va tuzatish kalitlari; noma'lum kod -> `null`. */
export function reconErrorView(
  code: string | null | undefined,
): ReconErrorView | null {
  if (typeof code !== "string") return null;

  const mapped = isReconErrorCode(code) ? code : SERVER_CODE_MAP[code];
  if (mapped === undefined) return null;

  return {
    code: mapped,
    tone: RECON_ERROR_TONE[mapped],
    causeKey: `recon.errorCause.${mapped}`,
    fixKey: `recon.errorFix.${mapped}`,
  } as ReconErrorView;
}
