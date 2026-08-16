/*
 * =============================================================================
 * HISOBOT YUZASINING XATO TAKSONOMIYASI — kod -> {tone} (W0-F4, §14.9).
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ REYESTR FRONTENDDA LANGAR — `reconciliation-errors.ts` BILAN AYNI
 *     SABAB VA U O'LCHANGAN (07-10 SUMMARY, 3-band).
 * -----------------------------------------------------------------------
 * `billing_errors.py` ga qo'shish `error-codes.test.mjs` dagi
 * `billingConstants.size === 14` nazorat qiymatini DARHOL qizartirardi va
 * uni «tuzatish» yagona yo'li sonni oshirish, ya'ni nazoratning butun
 * ma'nosini yo'q qilish bo'lardi. Shuning uchun langar SHU YERDA:
 * darvoza bu reyestrdan ITERATSIYA qiladi va uchala locale'da
 * `reports.errorCause.{kod}` + `reports.errorFix.{kod}` juftligini talab
 * qiladi; teskari yo'nalishda esa O'LIK kalitni ushlaydi.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi; uchala
 *   tildagi matn `frontend/messages/*.json` da (D-02).
 *
 * ⛔ XOM ISTISNO MATNI HECH QACHON EKRANGA CHIQMAYDI (07 D-04): server
 *    xato KODINI beradi, UI uni shu reyestr orqali kalitga xaritalaydi.
 * =============================================================================
 */

/**
 * Hisobot va daftar yuzasining xato kodlari — §14.9 jadvali KOD sifatida.
 *
 * ⛔ HAR BIRI «SABAB + NIMA QILISH KERAK» juftligiga EGA. Yolg'iz sabab
 *    direktorni boshi berk ko'chaga qo'yardi: u nima bo'lganini biladi,
 *    lekin keyingi qadamni bilmaydi (D-02 ning butun mazmuni).
 *
 * =========================================================================
 * ⚠⚠ SAKKIZINCHI KOD (`report_period_too_long`) — REJALASHTIRUVCHINING
 *     QO'SHIMCHASI. UI-SPEC §14.9 YETTITASINI sanaydi; sababi bu yerda
 *     LITERAL yozilgan, chunki uni keyingi o'quvchi «ortiqcha» deb
 *     olib tashlashi mumkin edi.
 *
 *     UI-SPEC §4.4 davr tanlagichiga UZUNLIK chegarasi ATAYIN
 *     QO'YMAYDI («sun'iy chegara yillik hisobotni imkonsiz qilardi»),
 *     server esa `report_max_period_days = 366` ni MAJBURLAYDI
 *     (Pitfall 13). Ya'ni 400 kunlik davr so'ralganda rad javobi
 *     KELADI va u ekranda nomlanishi SHART.
 *
 *     ⛔ Uni `report_period_invalid` ga yig'ish ekranda «Boshlanish
 *        sanasi tugash sanasidan keyin bo'lmasin» degan YOLG'ON sababni
 *        ko'rsatardi — foydalanuvchi sanalarni joyini almashtirib
 *        ko'rardi, xato takrorlanardi va u tizim buzuq deb xulosa
 *        qilardi. Xato matni to'g'ri harakatni («davrni qisqartiring»)
 *        aytishi kerak, aks holda D-02 ning butun kontrakti bo'sh
 *        va'da bo'lib qoladi.
 * =========================================================================
 */
export const REPORT_ERROR_CODES = [
  "report_period_invalid",
  "report_period_future",
  "report_period_too_long",
  "report_too_large",
  "report_export_failed",
  "report_forbidden",
  "ledger_day_locked",
  "ledger_stall_unknown",
] as const;

export type ReportErrorCode = (typeof REPORT_ERROR_CODES)[number];

/**
 * Xato blokining uchta ko'rinishi — `reconciliation-errors.ts` bilan bir shkala.
 *
 * ⚠ `--color-warning` HECH QACHON matn rangi emas (§13.2) — bu qiymat
 *   blok ramkasi va ikonkasini boshqaradi, matnni emas.
 */
export type ReportErrorTone = "neutral" | "warning" | "danger";

/**
 * Kod -> tone. ⛔ `Record<ReportErrorCode, ...>` ATAYIN: yetishmagan kod ham,
 * ortiqcha kod ham TS xatosi.
 */
const REPORT_ERROR_TONE: Readonly<Record<ReportErrorCode, ReportErrorTone>> = {
  /*
   * ⛔ `neutral`, `danger` EMAS: foydalanuvchi hech nimani buzmagan — u
   *    ikki sanani noto'g'ri tartibda tanladi va tuzatish bir bosishlik.
   *    `danger` uni nosozlik bilan bir shkalaga qo'yardi.
   */
  report_period_invalid: "neutral",
  /*
   * ⛔ `neutral`: «kechagi kungacha» — MAHSULOT QOIDASI (§1.2 qoida 1),
   *    nosozlik emas. Ogohlantirish bezagi uni har ochilishda shovqin
   *    qilardi, holbuki tanlagich maksimumni ALLAQACHON kecha qilib
   *    qo'ygan va bu holat faqat eskirgan xatcho'pdan keladi.
   */
  report_period_future: "neutral",
  /* Chegara serverniki (`report_max_period_days`) — kirish xatosi. */
  report_period_too_long: "neutral",
  /*
   * ⛔ `warning`: fayl QURILMADI, lekin ma'lumot joyida. Bu «tizim
   *    buzildi» emas, «bu davr faylga sig'maydi» — va foydalanuvchi
   *    davrni qisqartirib DARHOL natija oladi.
   */
  report_too_large: "warning",
  /*
   * ⛔ `danger`: bu YAGONA holat, unda foydalanuvchi to'g'ri ish qildi
   *    va tizim uddalay olmadi. Kesilgan faylni jimgina berish bu
   *    fazadagi eng qimmat nosozlik sinfi (§8.6), shuning uchun
   *    muvaffaqiyatsizlik BALAND ovozda ko'rsatiladi.
   */
  report_export_failed: "danger",
  report_forbidden: "danger",
  /* Kun yopilgan — ma'muriy holat, foydalanuvchining xatosi emas. */
  ledger_day_locked: "warning",
  /*
   * ⛔ `warning`, `danger` EMAS: fayldagi rasta kodi tizimda yo'q — bu
   *    KIRISH xatosi va server uni `422` bilan rad etadi. Import
   *    all-or-nothing (§10.3), ya'ni hech nima yozilmagan va tuzatish
   *    yo'li aniq: kodlarni shablon bilan solishtirish.
   */
  ledger_stall_unknown: "warning",
};

export type ReportErrorView = {
  [C in ReportErrorCode]: {
    readonly code: C;
    readonly tone: ReportErrorTone;
    readonly causeKey: `reports.errorCause.${C}`;
    readonly fixKey: `reports.errorFix.${C}`;
  };
}[ReportErrorCode];

export function isReportErrorCode(value: string): value is ReportErrorCode {
  return Object.hasOwn(REPORT_ERROR_TONE, value);
}

/**
 * Serverning MEXANIK kodi -> ekranning MAZMUNLI kodi.
 *
 * ⛔ IKKI RO'YXAT ATAYIN AJRATILGAN (`reconciliation-errors.ts` naqshi).
 *    Serverniki marshrut qatlamining haqiqati — `range_invalid` uchala
 *    hisobot marshrutida bir xil ma'noga ega; ekranniki esa
 *    foydalanuvchi o'qiydigan jumla.
 *
 * ⚠ Xaritada YO'Q kod `null` qaytaradi va chaqiruvchi `errors.generic`
 *   ga tushadi: xom `detail`, stack izi yoki SQL matni foydalanuvchiga
 *   HECH QACHON chiqmaydi.
 */
const SERVER_CODE_MAP: Readonly<Record<string, ReportErrorCode>> = {
  range_invalid: "report_period_invalid",
  day_in_future: "report_period_future",
  /*
   * ⛔ `range_too_wide` `report_period_invalid` GA EMAS, sakkizinchi
   *    kodga boradi — yuqoridagi blok izohida o'lchangan sabab.
   */
  range_too_wide: "report_period_too_long",
  forbidden: "report_forbidden",
  day_locked: "ledger_day_locked",
  stall_not_found: "ledger_stall_unknown",
};

/** Kod -> sabab va tuzatish kalitlari; noma'lum kod -> `null`. */
export function reportErrorView(
  code: string | null | undefined,
): ReportErrorView | null {
  if (typeof code !== "string") return null;

  const mapped = isReportErrorCode(code) ? code : SERVER_CODE_MAP[code];
  if (mapped === undefined) return null;

  return {
    code: mapped,
    tone: REPORT_ERROR_TONE[mapped],
    causeKey: `reports.errorCause.${mapped}`,
    fixKey: `reports.errorFix.${mapped}`,
  } as ReportErrorView;
}
