import { CAPTURE_ERROR_CODES } from "@/lib/api-types";
import type { CaptureErrorCode } from "@/lib/api-types";

/*
 * =============================================================================
 * KADR OLISH XATO TAKSONOMIYASI — kod -> {sabab, tuzatish, tone, KIM}.
 *
 * NEGA `nvr-errors.ts` GA QO'SHILMAYDI (ALOHIDA MODUL, `04-UI-SPEC.md` §5.3):
 *
 *   `nvrErrorView(code)` BESHTA qiymat qaytaradi — `causeKey`, `fixKey`,
 *   `tone`, `retrySafe`, `authLocking`. Oxirgi ikkitasi UI'da BITTA
 *   qarorni boshqaradi: «Qayta urinish» tugmasi render qilinadimi va
 *   forma qulflanadimi.
 *
 *   `captureErrorView(code)` esa TO'RTTA qaytaradi va beshinchi-oltinchi
 *   o'rniga BUTUNLAY YANGI O'LCHAM turadi: **`actor` — buni KIM
 *   tuzatadi?**
 *
 *   Farq sabab bilan: kadr olish xatolarining bir qismi bozor
 *   adminining ishi EMAS (`capture_worker_lost`,
 *   `capture_storage_unavailable` — platforma ishi), bir qismi esa HECH
 *   KIMNING ishi emas (`capture_plan_created_late` — normal, tarixiy
 *   fakt). Aktorsiz xabar adminni soatlab NVR sozlamalarini titkilashga
 *   yuborardi — holbuki muammo VPS'da; yoki teskarisi, u platforma
 *   jamoasini kutib turardi — holbuki kabelni o'zi ulashi kerak edi.
 *
 *   3-fazada bunday bo'linish YO'Q edi, chunki u yerda har xato adminga
 *   tegishli bo'lgan. Turli shakl — turli modul (`market-errors.ts` ni
 *   `queries.ts` dan ajratish qarorining aynan bir xil mantiqi).
 *
 * ⚠ `retrySafe` BU YERDA ATAYIN YO'Q. Kadr olishda qayta urinish qarori
 *   UI'da emas, TIKDA qabul qilinadi (`capture_errors.py` ning
 *   `retry_safe`/`locks_account`/`defer` uchligi) va u foydalanuvchiga
 *   umuman ko'rinmaydi: «hozir kadr ol» tugmasi bu fazada QURILMAYDI
 *   (§16.2 — slot vaqti biznes identifikatori, kechikkan kadr «o'sha
 *   payt rasta band edimi?» savoliga javob bermaydi). Bayroqni ko'zguga
 *   ko'chirish hech qanday UI qarorini boshqarmagan holda drift manbai
 *   bo'lardi.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi;
 *   uchala tildagi matn `frontend/messages/*.json` da
 *   (`snapshots.errorCause.*` / `snapshots.errorFix.*` / `snapshots.actor.*`).
 *   Backend ham shunday ishlaydi (`app/services/capture_errors.py`
 *   docstringi: «backend KOD beradi, matnni frontend uch tilda chizadi»).
 *
 * D-02 NING MEXANIK SHAKLI: har kod uchun SABAB, TUZATISH va AKTOR matni
 * uchala tilda bo'lishi `scripts/error-codes.test.mjs` (G-5) da
 * majburlanadi. Ya'ni «kod qo'shildi, matn unutildi» holati CI'da
 * yiqiladi, ekranda emas.
 * =============================================================================
 */

/** Xato blokining ikkita ko'rinishi — uchinchisi YO'Q (§10.5). */
export type CaptureErrorTone = "danger" | "warning";

/**
 * ⛔ 4-FAZANING YANGI O'LCHAMI — «buni KIM tuzatadi?» (§10.5).
 *
 * `admin`    — bozor ma'muriyatining o'z ishi; u darhol harakat qiladi.
 * `platform` — bozor admini bu xatoni tuzata OLMAYDI (infratuzilma).
 * `none`     — harakat talab qilinmaydi; holat normal va o'zi o'tadi.
 *
 * `none` ATAYIN faqat BITTA kodda: uni kengaytirish «hech nima qilmang»
 * javobini arzonlashtirardi va admin qolgan xabarlarni ham shu ko'z bilan
 * o'qib ketardi.
 */
export type CaptureErrorActor = "admin" | "platform" | "none";

type CaptureErrorMeta = {
  /**
   * `danger` — kadr UMUMAN OLINMADI (C5, C6): kunning o'sha katagi
   * bo'sh qoladi va uni qaytarib bo'lmaydi.
   * `warning` — kadr olindi, lekin HISOBGA KIRMAYDI (C2, C3, C4), yoki
   * holat normal (C9). Bu nosozlik emas — filtr aynan shu ish uchun
   * qurilgan (D-16, §10.3).
   */
  readonly tone: CaptureErrorTone;
  /** Kim tuzatadi — §10.5 ning uchinchi qatori. */
  readonly actor: CaptureErrorActor;
};

/**
 * §11.8 jadvali — KOD sifatida.
 *
 * ⚠ `Record<CaptureErrorCode, ...>` ATAYIN: `CAPTURE_ERROR_CODES`
 *   `api-types.ts` da (HTTP kontraktining ko'zgusi) yashaydi va bu
 *   e'lon ikki modulni KOMPILYATOR darajasida bog'laydi — yetishmagan
 *   kod ham, ortiqcha kod ham TS xatosi. Ya'ni bu yerdagi bo'linish
 *   `nvr-errors.ts` dagi «hammasi bitta faylda» yechimidan farq qiladi,
 *   lekin drift xavfi qo'shmaydi.
 *
 * ⚠ `tone` va `actor` MUSTAQIL: `capture_stream_limit` — `warning` +
 *   `admin` (oqim bo'shasa kadr keladi, lekin oqimni admin yopadi),
 *   `capture_plan_created_late` — `warning` + `none`. Ularni bittasidan
 *   ikkinchisini hosil qilish uchinchi holatni ifodalab bo'lmas qilardi.
 *
 * Backend juftisi: `app/services/capture_errors.py::CAPTURE_ERROR_META`
 * (u yerda `actor` maydoni AYNAN shu nom bilan).
 */
export const CAPTURE_ERROR_META: Readonly<
  Record<CaptureErrorCode, CaptureErrorMeta>
> = {
  /* 1-guruh — ORKESTRATSIYA. */
  capture_slot_missed: { tone: "danger", actor: "platform" },
  capture_worker_lost: { tone: "danger", actor: "platform" },
  capture_plan_created_late: { tone: "warning", actor: "none" },
  /* 2-guruh — TARMOQ va QURILMA. */
  capture_source_unreachable: { tone: "danger", actor: "admin" },
  capture_camera_offline: { tone: "danger", actor: "admin" },
  capture_timeout: { tone: "danger", actor: "admin" },
  capture_invalid_response: { tone: "danger", actor: "admin" },
  /* 3-guruh — AUTENTIFIKATSIYA. */
  capture_bad_credentials: { tone: "danger", actor: "admin" },
  /* 4-guruh — RESURS. */
  capture_stream_limit: { tone: "warning", actor: "admin" },
  /* 5-guruh — PLATFORMA NOSOZLIGI. */
  capture_storage_unavailable: { tone: "danger", actor: "platform" },
  capture_credential_unreadable: { tone: "danger", actor: "platform" },
};

export type CaptureErrorView = CaptureErrorMeta & {
  readonly code: CaptureErrorCode;
  readonly causeKey: `snapshots.errorCause.${CaptureErrorCode}`;
  readonly fixKey: `snapshots.errorFix.${CaptureErrorCode}`;
  readonly actorKey: `snapshots.actor.${CaptureErrorActor}`;
};

export function isCaptureErrorCode(value: string): value is CaptureErrorCode {
  return (CAPTURE_ERROR_CODES as readonly string[]).includes(value);
}

/**
 * Kod -> xato blokining butun kontrakti (SABAB + NIMA QILISH + KIM).
 *
 * `null` — NOMA'LUM kod. Chaqiruvchi u holda `errors.generic` ga tushadi
 * va `error_detail` ni KO'RSATMAYDI: xom `detail`, stack izi yoki SQL
 * matni foydalanuvchiga HECH QACHON chiqmaydi (T-02-99, §10.5 oxirgi
 * qatori).
 */
export function captureErrorView(
  code: string | null | undefined,
): CaptureErrorView | null {
  if (typeof code !== "string" || !isCaptureErrorCode(code)) return null;

  const meta = CAPTURE_ERROR_META[code];
  return {
    code,
    causeKey: `snapshots.errorCause.${code}`,
    fixKey: `snapshots.errorFix.${code}`,
    actorKey: `snapshots.actor.${meta.actor}`,
    ...meta,
  };
}

/**
 * Aktor bo'yicha guruhlangan kodlar — METADAN HOSILA.
 *
 * Qo'lda ikkinchi ro'yxat yozilsa u jadval bilan bir kun ajralib ketardi
 * (`nvr-errors.ts::AUTH_LOCKING_CODES` bilan aynan bir xil qaror).
 * Iste'molchisi bugun ogohlantirish zonasi emas — 04-11 dagi kadr detali
 * va kelajakdagi dayjest: «platforma tuzatadigan» xatolarni bir joyda
 * sanash uchun ikkinchi ro'yxat qurilmasin.
 */
export const PLATFORM_ACTOR_CODES: readonly CaptureErrorCode[] =
  CAPTURE_ERROR_CODES.filter(
    (code) => CAPTURE_ERROR_META[code].actor === "platform",
  );
