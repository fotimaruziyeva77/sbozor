/*
 * =============================================================================
 * Demo-so'rov xato reyestri — backend `DEMO_ERROR_CODES` ning KO'ZGUSI.
 *
 * Manba: `services/core-api/app/schemas.py::DEMO_ERROR_CODES` (10-01).
 * Ikkisi QO'LDA sinxron saqlanadi (til chegarasi tufayli kompilyator
 * tekshiruvi yo'q — `nvr-errors.ts` bilan aynan bir xil holat) va drift
 * `scripts/error-codes.test.mjs` ning oltinchi juftligida qulflanadi (10-08).
 *
 * ⛔ BU MODUL ANONIM LANDING SAHIFASINING KLIENT GRAFIGA KIRADI, shuning
 *   uchun u HECH QANDAY og'ir modulni import qilmaydi — sxema kutubxonasini
 *   ham, HTTP mijoz o'ramini ham (10-RESEARCH B-2: o'sha graf 69 KB gzip
 *   va u anonim sahifada hech nima chizmaydi). Bu fayl — sof lug'at.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat `landing` fazoviy nomiga
 *   nisbiy KALIT qaytaradi; uchala tildagi matn `frontend/messages/*.json`
 *   da (`nvr-errors.ts` docstringidagi qaror bilan bir xil).
 * =============================================================================
 */

/**
 * To'rt kod — YOPIQ reyestr (`POST /api/v1/public/demo-requests`).
 *
 * `rate_limited` — IP kesimi 15 daqiqada 5 so'rovdan oshdi (429).
 * `invalid_phone` — server `phonenumbers` raqamni o'qiy olmadi (422,
 *   bitta satr `detail`). Klient qattiq regeks yozmaydi (T-10-11).
 * `validation_error` — Pydantic chegaralari (FastAPI standart 422 massivi;
 *   frontend uni SHU kodga o'zi xaritalaydi — server alohida handler
 *   qo'shmagan, 10-01 SUMMARY eslatmasi).
 * `delivery_failed` — Telegram xabarni qabul qilmadi (502); «yubordik»
 *   deb yolg'on aytilmaydi (SPEC §12.5).
 */
export const DEMO_ERROR_CODES = [
  "rate_limited",
  "invalid_phone",
  "validation_error",
  "delivery_failed",
] as const;

export type DemoErrorCode = (typeof DEMO_ERROR_CODES)[number];

/**
 * `demoErrorMessageKey` qaytaradigan kalitlar — `landing` fazoviy nomiga
 * NISBIY (chaqiruvchi `useTranslations("landing")` bilan bog'laydi).
 *
 * Union literal — `global.ts` dagi tiplangan `t()` dinamik satrni rad
 * etadi, literal ittifoqni esa qabul qiladi (login xato xaritasi naqshi).
 */
export type DemoErrorMessageKey =
  | "form.error.rateLimited"
  | "form.validation.phoneInvalid"
  | "form.error.validation"
  | "form.error.body";

/**
 * Kod -> tarjima kaliti.
 *
 * ⚠ `form.error.body` `{phone}` argumentini KUTADI — chaqiruvchi
 *   `NEXT_PUBLIC_CONTACT_PHONE` bo'lmasa `form.error.bodyNoPhone` ga
 *   o'zi tushadi (O-06: bo'sh qavs KO'RSATILMAYDI). Bu shox komponentda,
 *   chunki env o'qish lug'at modulining ishi emas.
 *
 * Noma'lum kod ham `form.error.body` ga tushadi: xom `detail` satri
 * foydalanuvchiga HECH QACHON ko'rsatilmaydi (T-02-99 qoidasi meros).
 */
export function demoErrorMessageKey(code: string): DemoErrorMessageKey {
  switch (code) {
    case "rate_limited":
      return "form.error.rateLimited";
    case "invalid_phone":
      return "form.validation.phoneInvalid";
    case "validation_error":
      return "form.error.validation";
    case "delivery_failed":
      return "form.error.body";
    default:
      return "form.error.body";
  }
}
