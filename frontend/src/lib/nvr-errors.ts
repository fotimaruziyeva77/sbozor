/*
 * =============================================================================
 * NVR xato taksonomiyasi — kod -> {sabab, tuzatish, tone, retry, qulf}.
 *
 * NEGA `market-errors.ts` GA QO'SHILMAYDI (ALOHIDA MODUL):
 *
 *   `marketErrorMessageKey` BITTA kalit qaytaradi — u domen rad javobini
 *   bitta jumlaga aylantiradi va shu bilan tugaydi. NVR xatosi esa
 *   BESHTA qiymat qaytaradi (`causeKey`, `fixKey`, `tone`, `retrySafe`,
 *   `authLocking`) va ularning har biri UI'da BOSHQA qarorni boshqaradi:
 *   qaysi matn chiziladi, blok qanday ko'rinadi, tugma umuman
 *   RENDER QILINADIMI. Turli shakl — turli modul.
 *
 *   Bu 02-fazada `market-errors.ts` ni `queries.ts` dan ajratish
 *   qarorining AYNAN bir xil mantiqi (`market-errors.ts:4-30`).
 *
 * D-02 NING MEXANIK SHAKLI: har kod uchun SABAB va TUZATISH matni
 * uchala tilda bo'lishi `scripts/error-codes.test.mjs` (G-1) da
 * majburlanadi; shu jadvaldagi har kod uchun backendda mos yozuv
 * borligi esa G-2 da. Ya'ni "kod qo'shildi, matn unutildi" holati
 * CI'da yiqiladi, ekranda emas.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi;
 *   uchala tildagi matn `frontend/messages/*.json` da. Backend ham
 *   shunday ishlaydi (`app/services/isapi/errors.py` docstringi).
 * =============================================================================
 */

/**
 * O'n ikki kod — backend reyestrining KO'ZGUSI.
 *
 * Manba: `services/core-api/app/services/isapi/errors.py::NVR_ERROR_CODES`.
 * Ikkisi QO'LDA sinxron saqlanadi (til chegarasi tufayli kompilyator
 * tekshiruvi yo'q — `rbac.ts` dagi matritsa bilan aynan bir xil holat)
 * va drift `scripts/error-codes.test.mjs` da qulflangan.
 *
 * ⚠ BU RO'YXAT `api-types.ts::ERROR_CODES` GA QO'SHILMAYDI va bu
 *   ataylab: u yerdagi kodlar HTTP `detail` sifatida keladi (to'g'ridan-
 *   to'g'ri 4xx), bulari esa javob TANASIDAGI `error_code` maydoni
 *   (`test-connection` 200 bilan javob beradi, kashfiyot yugurishi esa
 *   `error_code` ustunini to'ldiradi). Ikkalasini bitta ro'yxatga yig'ish
 *   "ulanmadi" xatosini oddiy toast sifatida ko'rsatib, D-02 ning butun
 *   mazmunini yo'qotardi (`api-types.ts:837-845` dagi izoh).
 */
export const NVR_ERROR_CODES = [
  /* 1-guruh — AUTENTIFIKATSIYA. Qayta urinish HOLATNI O'ZGARTIRADI. */
  "nvr_bad_credentials",
  "nvr_account_locked",
  "nvr_user_no_permission",
  /* 2-guruh — SOZLAMA. Qayta urinish XAVFSIZ va foydali. */
  "nvr_clock_drift",
  "nvr_digest_stale",
  "nvr_auth_mode_basic_only",
  /* 3-guruh — TARMOQ va QURILMA. */
  "nvr_unreachable",
  "nvr_isapi_unavailable",
  "nvr_tls_untrusted",
  "device_not_supported",
  "nvr_stream_limit",
  "channel_offline",
] as const;

export type NvrErrorCode = (typeof NVR_ERROR_CODES)[number];

/** Xato blokining ikkita ko'rinishi — uchinchisi YO'Q (UI-SPEC §7.2). */
export type NvrErrorTone = "danger" | "warning";

type NvrErrorMeta = {
  /**
   * `danger` — sabab REKVIZIT yoki QURILMADA: admin uni saytda tuzata
   * olmaydi va amal bajarilmadi.
   * `warning` — sabab SOZLAMADA: admin uni NVR interfeysida yoki
   * tarmog'ida tuzatadi; yoki tashxis TAXMINIY.
   */
  readonly tone: NvrErrorTone;
  /**
   * Qayta urinish affordansi ko'rsatiladimi.
   *
   * QOIDA BITTA JUMLADA: *tugma faqat qayta urinish HOLATNI
   * O'ZGARTIRMAYDIGAN hollarda ko'rinadi.* Autentifikatsiya urinishi
   * holatni o'zgartiradi — u qurilmadagi qulflash hisoblagichini
   * oshiradi — shuning uchun u yerda tugma YO'Q.
   *
   * `device_not_supported` da `false` boshqa sababdan: qayta urinish
   * hech narsani o'zgartirmaydi, ya'ni tugma FOYDASIZ va u adminni
   * "yana bosib ko'ray" sikliga tashlardi.
   */
  readonly retrySafe: boolean;
  /**
   * Kod `AUTH_LOCKING_CODES` ga tegishlimi (UI-SPEC §4.4).
   *
   * `true` bo'lganda UI ikkala tugmani ham bloklaydi va qulf FAQAT
   * login yoki parol QIYMATI o'zgarganda ochiladi — `use-nvr-auth-lock.ts`.
   */
  readonly authLocking: boolean;
};

/**
 * UI-SPEC §7.3 jadvali — KOD sifatida.
 *
 * ⚠ `channel_offline` bu jadvalda BOR, lekin u BLOK EMAS: u qator
 *   badge'i (§6.4/§7.2) va kashfiyotni TO'XTATMAYDI. Yozuv baribir
 *   kerak — matni uchala tilda chiziladi va G-2 uni backend reyestri
 *   bilan solishtiradi.
 */
const NVR_ERROR_META: Readonly<Record<NvrErrorCode, NvrErrorMeta>> = {
  nvr_bad_credentials: { tone: "danger", retrySafe: false, authLocking: true },
  nvr_account_locked: { tone: "danger", retrySafe: false, authLocking: true },
  nvr_user_no_permission: {
    tone: "danger",
    retrySafe: false,
    authLocking: true,
  },
  nvr_clock_drift: { tone: "warning", retrySafe: true, authLocking: false },
  nvr_digest_stale: { tone: "warning", retrySafe: true, authLocking: false },
  nvr_auth_mode_basic_only: {
    tone: "warning",
    retrySafe: true,
    authLocking: false,
  },
  nvr_unreachable: { tone: "danger", retrySafe: true, authLocking: false },
  nvr_isapi_unavailable: { tone: "danger", retrySafe: true, authLocking: false },
  nvr_tls_untrusted: { tone: "warning", retrySafe: true, authLocking: false },
  device_not_supported: { tone: "danger", retrySafe: false, authLocking: false },
  nvr_stream_limit: { tone: "warning", retrySafe: true, authLocking: false },
  channel_offline: { tone: "warning", retrySafe: true, authLocking: false },
};

/**
 * Autentifikatsiya urinishini SANAYDIGAN kodlar (D-03).
 *
 * Yagona manbadan hosil qilinadi — qo'lda ikkinchi ro'yxat yozilsa u
 * jadval bilan bir kun ajralib ketardi va qoida BITTA yuzada
 * qolardi.
 *
 * Backend juftisi: `app/services/isapi/errors.py::AUTH_LOCKING_CODES`.
 */
export const AUTH_LOCKING_CODES: readonly NvrErrorCode[] =
  NVR_ERROR_CODES.filter((code) => NVR_ERROR_META[code].authLocking);

/**
 * `error_detail` dan UI iste'mol qiladigan YAGONA kalitlar (UI-SPEC §7.4).
 *
 * ⚠ BU FILTR EMAS, ISTE'MOL RO'YXATI. Maskalash va cheklash BACKENDNING
 *   kafolati (`NvrError` konstruktori + `mask_sensitive`); klientda
 *   ikkinchi maskalash qatlami qurish "backend nima yozsa ham xavfsiz"
 *   degan yolg'on xotirjamlik berardi. Bu ro'yxatning vazifasi boshqa:
 *   noma'lum kalit UI'da RENDER QILINMAYDI, ya'ni kutilmagan qiymat
 *   ekranga tarjimasiz texnik satr bo'lib chiqmaydi.
 */
export const ERROR_DETAIL_KEYS = [
  "drift_seconds",
  "device_time",
  "server_time",
  "unlock_at",
  "channel_no",
  "channel_name",
  "model",
  "raw",
] as const;
export type ErrorDetailKey = (typeof ERROR_DETAIL_KEYS)[number];

/** `<details>` ichidagi xom javobning yuqori chegarasi (UI-SPEC §7.4). */
export const MAX_RAW_DETAIL_CHARS = 2000;

export type NvrErrorView = NvrErrorMeta & {
  readonly code: NvrErrorCode;
  readonly causeKey: `cameras.errorCause.${NvrErrorCode}`;
  readonly fixKey: `cameras.errorFix.${NvrErrorCode}`;
};

export function isNvrErrorCode(value: string): value is NvrErrorCode {
  return (NVR_ERROR_CODES as readonly string[]).includes(value);
}

/**
 * Kod -> xato blokining butun kontrakti.
 *
 * `null` — NOMA'LUM kod. Chaqiruvchi u holda `errors.generic` ga tushadi
 * va `error_detail` ni KO'RSATMAYDI (UI-SPEC §7.3 oxirgi qatori): xom
 * `detail`, stack izi yoki SQL matni foydalanuvchiga HECH QACHON
 * ko'rsatilmaydi (T-02-99).
 */
export function nvrErrorView(
  code: string | null | undefined,
): NvrErrorView | null {
  if (typeof code !== "string" || !isNvrErrorCode(code)) return null;

  return {
    code,
    causeKey: `cameras.errorCause.${code}`,
    fixKey: `cameras.errorFix.${code}`,
    ...NVR_ERROR_META[code],
  };
}

/**
 * `error_detail` dan FAQAT ruxsat etilgan kalitlarni ajratadi.
 *
 * Noma'lum kalit jimgina tashlanadi — u UI'da render qilinmaydi
 * (UI-SPEC §7.4 [TALAB]).
 */
export function pickErrorDetail(
  detail: Record<string, unknown> | null | undefined,
): Partial<Record<ErrorDetailKey, unknown>> {
  if (detail == null) return {};

  const out: Partial<Record<ErrorDetailKey, unknown>> = {};
  for (const key of ERROR_DETAIL_KEYS) {
    if (Object.hasOwn(detail, key)) out[key] = detail[key];
  }
  return out;
}

/**
 * `<details>` ichida chiziladigan xom matn; `null` — blok RENDER
 * QILINMAYDI (bo'sh `<details>` — shovqin, UI-SPEC §7.4).
 *
 * Uzunlik 2000 belgidan KESILADI: uzun XML javobi sahifani yeb qo'yardi.
 * Backend chegarasi kattaroq (4000) va bu ataylab — u yerda kontekst
 * texnik yordam uchun saqlanadi.
 */
export function rawDetailText(
  detail: Record<string, unknown> | null | undefined,
): string | null {
  const raw = detail?.raw;
  if (typeof raw !== "string" || raw.length === 0) return null;
  return raw.length > MAX_RAW_DETAIL_CHARS
    ? `${raw.slice(0, MAX_RAW_DETAIL_CHARS)}…`
    : raw;
}
