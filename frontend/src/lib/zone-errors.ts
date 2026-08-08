/*
 * =============================================================================
 * BANDLIK DOMENINING XATO TAKSONOMIYASI — kod -> {sabab, tuzatish, tone, SIRT}.
 *
 * NEGA ALOHIDA MODUL (`nvr-errors.ts` va `capture-errors.ts` ga qo'shilmaydi):
 *
 *   `nvrErrorView(code)`     -> `causeKey`, `fixKey`, `tone`, `retrySafe`, `authLocking`
 *   `captureErrorView(code)` -> `causeKey`, `fixKey`, `tone`, `actor`
 *   `zoneErrorView(code)`    -> `causeKey`, `fixKey`, `tone` — va ular
 *                               IKKI XIL NAMESPACE'dan kelishi mumkin.
 *
 *   Uchinchi shakl birinchi ikkitasining kengaytmasi EMAS: bu yerda
 *   yangi o'lcham `actor` ham, `retrySafe` ham emas, balki **SIRT** —
 *   xato QAYSI EKRANDA ko'rsatiladi. Turli shakl — turli modul
 *   (`market-errors.ts` ni `queries.ts` dan ajratish qarorining aynan
 *   bir xil mantiqi).
 *
 * ⚠ `actor` USTUNI BU YERDA ATAYIN YO'Q [05-UI-SPEC §12.7]. 4-fazada u
 *   kerak edi, chunki kadr olish xatolarining bir qismi bozor adminining
 *   ishi EMAS (platforma yoki hech kim). Bu fazada esa hamma xato
 *   foydalanuvchining O'Z AMALI bilan bog'liq — u chizyapti yoki javob
 *   beryapti — ya'ni «buni kim tuzatadi?» savoli HAR DOIM bir xil javobga
 *   ega. Uni ekranga chiqarish shovqin bo'lardi, ko'zguga ko'chirish esa
 *   hech qanday UI qarorini boshqarmagan holda drift manbai bo'lardi.
 *
 * ⚠ `retrySafe` HAM YO'Q va sabab boshqa: bu xatolarning birortasi ham
 *   tashqi qurilmaga urinish emas (NVR hisobi qulflanmaydi, tarmoq
 *   kutilmaydi). «Qayta urinish» ma'noli bo'lgan yagona holat —
 *   `review_image_unavailable` — va u yerda tugma `review.imageRetry`
 *   sifatida EKRANDA yashaydi, taksonomiyada emas.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi; uchala
 *   tildagi matn `frontend/messages/*.json` da. Backend ham shunday
 *   ishlaydi (`app/services/occupancy_errors.py` docstringi:
 *   «backend KOD beradi, matnni frontend uch tilda chizadi», D-02).
 *
 * D-02 NING MEXANIK SHAKLI: har kod uchun SABAB va TUZATISH matni uchala
 * tilda bo'lishi `scripts/error-codes.test.mjs` (G-17) da majburlanadi, va
 * o'sha darvoza SIRTNI HAM solishtiradi. Ya'ni «kod qo'shildi, matn
 * unutildi» ham, «kod boshqa namespace'ga ko'chdi» ham CI'da yiqiladi,
 * ekranda emas.
 * =============================================================================
 */

/**
 * Zona muharririning kodlari — matni `cameraZones.*` da.
 *
 * Manba: `app/services/occupancy_errors.py::ZONE_ERROR_CODES`.
 * Ikkisi QO'LDA sinxron saqlanadi (til chegarasi tufayli kompilyator
 * tekshiruvi yo'q — `nvr-errors.ts` va `rbac.ts` bilan aynan bir xil
 * holat) va drift `scripts/error-codes.test.mjs` da qulflangan.
 */
export type ZoneErrorCode =
  | "zone_polygon_too_few_points"
  | "zone_polygon_too_many_points"
  | "zone_polygon_out_of_range"
  | "zone_polygon_self_intersecting"
  | "zone_limit_reached"
  | "zone_stall_already_covered"
  | "zone_camera_has_no_frame"
  | "zone_aspect_mismatch";

/**
 * Ko'rib chiqish sirtining kodlari — matni `review.*` da.
 *
 * Manba: `app/services/occupancy_errors.py::REVIEW_ERROR_CODES`.
 *
 * ⚠ `blind_answer_locked` `review_` prefiksi bilan BOSHLANMAYDI va bu
 *   ataylab: u ko'rmasdan tekshirishning O'Z qoidasi (D-17, 4-himoya),
 *   navbatning umumiy xulqi emas. Shuning uchun sirt PREFIKSDAN
 *   TAXMIN QILINMAYDI — u pastdagi jadvalda OCHIQ yoziladi.
 */
export type ReviewErrorCode =
  | "review_queue_empty"
  | "review_budget_exhausted"
  | "review_sample_not_drawn"
  | "review_image_unavailable"
  | "blind_answer_locked"
  | "review_already_answered";

export type OccupancyErrorCode = ZoneErrorCode | ReviewErrorCode;

/**
 * Xato bloki ko'rsatiladigan EKRAN — matn kalitining namespace'i.
 *
 * Backend juftisi: `ZONE_ERROR_CODES` / `REVIEW_ERROR_CODES` reyestrlari
 * (u yerda reyestr NOMI sirtning o'zi).
 */
export type OccupancyErrorSurface = "cameraZones" | "review";

/**
 * Xato blokining ikkita ko'rinishi — uchinchisi YO'Q [MEROS: 03-UI-SPEC §7.2].
 *
 * ⚠ `neutral` ATAYIN QO'SHILMADI. `review_sample_not_drawn` («namuna hali
 *   tortilmagan») uchun u vasvasa qiladi, lekin uchinchi tone butun
 *   taksonomiyani ikki emas, uch tarmoqli qilardi va «bu qanchalik
 *   jiddiy?» savoli har yangi kodda qaytadan ochilardi. To'g'ri uy —
 *   `warning`: 4-fazada `capture_plan_created_late` (u ham NORMAL
 *   holat, xato emas) aynan shu tone'ni olgan.
 */
export type OccupancyErrorTone = "danger" | "warning";

type OccupancyErrorMeta = {
  /**
   * `danger` — amal BAJARILMADI va foydalanuvchi uni o'zi tuzatadi
   * (poligon qoidasi buzilgan, dalil rasmi ochilmagan).
   * `warning` — holat NORMAL yoki chegara: ish davom etadi, faqat
   * boshqa yo'l bilan (boshqa kamera, ertaga, keyingi band).
   *
   * ⚠ `--color-warning` HECH QACHON matn rangi emas [MEROS: §10.2] —
   *   bu qiymat blok ramkasi va ikonkasini boshqaradi, matnni emas.
   */
  readonly tone: OccupancyErrorTone;
  /** Matn qaysi namespace'dan olinadi. Backend reyestri bilan solishtiriladi. */
  readonly surface: OccupancyErrorSurface;
};

/**
 * 05-UI-SPEC §12.7 jadvali — KOD sifatida.
 *
 * ⚠ `Record<OccupancyErrorCode, ...>` ATAYIN: yetishmagan kod ham,
 *   ortiqcha kod ham TS xatosi. Bu KOMPILYATOR darajasidagi birinchi
 *   qatlam; ikkinchisi — backend bilan solishtiruvchi G-17 darvozasi.
 *
 * ⚠ `tone` va `surface` MUSTAQIL o'lchamlar: `zone_limit_reached` —
 *   `warning` + `cameraZones`, `review_image_unavailable` — `danger` +
 *   `review`. Ularning birini ikkinchisidan hosil qilib bo'lmaydi.
 */
const OCCUPANCY_ERROR_META: Readonly<
  Record<OccupancyErrorCode, OccupancyErrorMeta>
> = {
  /* 1-sirt — ZONA MUHARRIRI (AI-01). */
  zone_polygon_too_few_points: { tone: "danger", surface: "cameraZones" },
  zone_polygon_too_many_points: { tone: "danger", surface: "cameraZones" },
  zone_polygon_out_of_range: { tone: "danger", surface: "cameraZones" },
  zone_polygon_self_intersecting: { tone: "danger", surface: "cameraZones" },
  zone_limit_reached: { tone: "warning", surface: "cameraZones" },
  zone_stall_already_covered: { tone: "warning", surface: "cameraZones" },
  zone_camera_has_no_frame: { tone: "warning", surface: "cameraZones" },
  zone_aspect_mismatch: { tone: "warning", surface: "cameraZones" },
  /* 2-sirt — KO'RIB CHIQISH va KO'RMASDAN TEKSHIRISH (AI-03, AI-04). */
  review_queue_empty: { tone: "warning", surface: "review" },
  review_budget_exhausted: { tone: "warning", surface: "review" },
  review_sample_not_drawn: { tone: "warning", surface: "review" },
  review_image_unavailable: { tone: "danger", surface: "review" },
  blind_answer_locked: { tone: "warning", surface: "review" },
  review_already_answered: { tone: "warning", surface: "review" },
};

/**
 * Kod -> uning namespace'i. `OCCUPANCY_ERROR_META` DAN HOSILA.
 *
 * Qo'lda ikkinchi ro'yxat yozilsa u jadval bilan bir kun ajralib ketardi
 * (`nvr-errors.ts::AUTH_LOCKING_CODES` va `capture-errors.ts::
 * PLATFORM_ACTOR_CODES` bilan aynan bir xil qaror).
 */
type SurfaceOf<C extends OccupancyErrorCode> = C extends ZoneErrorCode
  ? "cameraZones"
  : "review";

/**
 * Kod -> xato blokining butun kontrakti (SABAB + NIMA QILISH KERAK).
 *
 * ⚠ Bu TAQSIMLANGAN BIRLASHMA (`{[C in ...]: ...}[...]`), oddiy obyekt
 *   tipi emas. Sabab amaliy: shundagina `causeKey` ning tipi FAQAT
 *   haqiqatan mavjud kalitlarni o'z ichiga oladi. Yassi
 *   `` `${OccupancyErrorSurface}.errorCause.${OccupancyErrorCode}` ``
 *   yozuvi `review.errorCause.zone_limit_reached` kabi HECH QACHON
 *   mavjud bo'lmaydigan kalitni ham qonuniy qilardi va `t()` ning kalit
 *   xavfsizligi (`src/global.ts`) shu joyda yo'qolardi.
 */
export type OccupancyErrorView = {
  [C in OccupancyErrorCode]: {
    readonly code: C;
    readonly tone: OccupancyErrorTone;
    readonly surface: SurfaceOf<C>;
    readonly causeKey: `${SurfaceOf<C>}.errorCause.${C}`;
    readonly fixKey: `${SurfaceOf<C>}.errorFix.${C}`;
  };
}[OccupancyErrorCode];

export function isOccupancyErrorCode(
  value: string,
): value is OccupancyErrorCode {
  return Object.hasOwn(OCCUPANCY_ERROR_META, value);
}

/**
 * Kod -> sabab va tuzatish kalitlari.
 *
 * `null` — NOMA'LUM kod. Chaqiruvchi u holda `errors.generic` ga tushadi
 * va xom `detail` ni KO'RSATMAYDI: `detail`, stack izi yoki SQL matni
 * foydalanuvchiga HECH QACHON chiqmaydi (T-05-13, T-02-99).
 */
export function zoneErrorView(
  code: string | null | undefined,
): OccupancyErrorView | null {
  if (typeof code !== "string" || !isOccupancyErrorCode(code)) return null;

  const meta = OCCUPANCY_ERROR_META[code];
  return {
    code,
    tone: meta.tone,
    surface: meta.surface,
    causeKey: `${meta.surface}.errorCause.${code}`,
    fixKey: `${meta.surface}.errorFix.${code}`,
  } as OccupancyErrorView;
}
