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
  "assignee_not_in_market",
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
  /*
   * ⛔ `warning`, `danger` EMAS: direktor ro'yxatdan tanladi va tanlov
   *    NOTO'G'RI chiqdi — bu KIRISH xatosi, nosozlik emas (server ham uni
   *    `422` bilan, `403` bilan EMAS rad etadi). `danger` uni «ruxsat
   *    yo'q» bilan bir shkalaga qo'yardi va direktor o'z huquqidan
   *    shubhalanardi, holbuki tuzatish bir bosishlik: boshqa xodimni
   *    tanlash.
   */
  assignee_not_in_market: "warning",
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
  /*
   * 07-20 ochgan `422` (`reconciliation.py:736`, T-07-109).
   *
   * ⛔ SERVER KODI VA EKRAN KODI BIR XIL NOM BILAN ATALGAN, LEKIN IKKI
   *    RO'YXAT AJRATILGAN HOLICHA QOLADI (modulning mavjud qarori). Bu
   *    yozuvni «ortiqcha» deb olib tashlash `isReconErrorCode()` ning
   *    tasodifiy yordamiga tayanardi: ekran kodlarining nomi kelajakda
   *    o'zgarsa (masalan `case_assignee_foreign`), xarita JIMGINA
   *    uzilardi va begona-bozor rad etishi yana `errors.generic` ga
   *    tushardi.
   *
   * ⚠ MAVJUD BO'LMAGAN `user_id` ham AYNAN shu kodni oladi (T-07-110) —
   *   ya'ni matn «bunday xodim yo'q» DEMASLIGI kerak, aks holda javob
   *   kodi bo'yicha identifikatorlarni sanab chiqish yo'li ochilardi.
   */
  assignee_not_in_market: "assignee_not_in_market",
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

/* -------------------------------------------------------------------------- */
/* YETKAZILMASLIK TURLARI — §14.9 ning IKKINCHI jadvali (BOT-04)              */
/* -------------------------------------------------------------------------- */

/*
 * =============================================================================
 * ⛔⛔ NEGA XOM ISTISNO SINFI EKRANGA CHIQMAYDI VA U SHU YERDA XARITALANADI.
 *
 * Server javobda ⛔ ISTISNO SINFINING NOMINI beradi (`ConnectTimeout`,
 * `HTTPStatusError`, `UnresolvedRecipient`, …) va bu ⛔ TO'G'RI: D-04
 * bo'yicha istisnoning MATNI hech qachon saqlanmaydi, chunki Telegram
 * Bot API ning URL'i BOT TOKENINI tashiydi.
 *
 * Lekin `RemoteProtocolError` direktorga ⛔ HECH NIMA AYTMAYDI. Shuning
 * uchun sinf nomi bu yerda ⛔ YOPIQ TO'RT A'ZOLI to'plamga xaritalanadi
 * va ekranda faqat o'sha to'rttadan biri ko'rinadi.
 *
 * ⛔ XARITA NOMUVOFIQLIK YUZASIDA EMAS, SHU MODULDA: `components/
 *    reconciliation/**` taqiqlangan nomlar skanidan o'tadi va sinf
 *    nomlarining ro'yxati o'sha katalogda ⛔ TAQIQLANGAN TOKENNI olib
 *    kirishi mumkin edi. Bu modul esa xato TAKSONOMIYASINING uyi.
 *
 * ⚠ NOMA'LUM SINF `unknown` GA TUSHADI, EKRANDAN YO'QOLMAYDI: qatorni
 *   izohsiz qoldirish «xato bor, lekin qanaqa — bilinmaydi» degan
 *   holatni «xato yo'q» dan AJRATIB BO'LMAYDIGAN qilardi.
 * =============================================================================
 */

/** §14.9 — yetkazilmaslikning TO'RT turi. ⛔ Beshinchisi yo'q. */
export const DELIVERY_ERROR_CODES = [
  "telegram_unreachable",
  "chat_not_found",
  "rate_limited",
  "unknown",
] as const;

export type DeliveryErrorCode = (typeof DELIVERY_ERROR_CODES)[number];

/**
 * Tarmoq qatlamida uzilgan istisnolar — ⛔ Telegram JAVOB BERMADI.
 *
 * ⚠ Ro'yxat `httpx` ning transport istisnolaridan olingan; u bu yerda
 *   QAYTA YOZILADI, kutubxonadan import qilinmaydi — import qilingan
 *   ro'yxat kutubxona versiyasi bilan JIMGINA o'zgarardi.
 */
const UNREACHABLE_CLASSES: ReadonlySet<string> = new Set([
  "ConnectTimeout",
  "ReadTimeout",
  "WriteTimeout",
  "PoolTimeout",
  "ConnectError",
  "ReadError",
  "WriteError",
  "RemoteProtocolError",
  "TransportError",
  "TimeoutException",
]);

/**
 * Xato TURI -> ekranning yopiq kodi.
 *
 * ⛔ IKKI KIRISH BIRGA: status kodi sinf nomidan KUCHLIROQ signal.
 *    Telegram `429` ni ham, `400` ni ham AYNAN BIR sinf bilan
 *    (`HTTPStatusError`) beradi — faqat sinfga qarash ikkalasini bir
 *    xil ko'rsatardi va «chegara oshdi» bilan «chat topilmadi» ni
 *    ajratib bo'lmasdi.
 *
 * @param errorType istisno sinfining nomi (server bergan) yoki `null`.
 * @param statusCode HTTP status kodi yoki `null`.
 * @returns Yopiq to'plamning a'zosi; `errorType === null` bo'lsa `null`.
 */
export function deliveryErrorCode(
  errorType: string | null,
  statusCode: number | null,
): DeliveryErrorCode | null {
  if (errorType === null) return null;
  if (statusCode === 429) return "rate_limited";
  if (statusCode === 400 || errorType === "UnresolvedRecipient") {
    return "chat_not_found";
  }
  if (UNREACHABLE_CLASSES.has(errorType)) return "telegram_unreachable";
  return "unknown";
}
