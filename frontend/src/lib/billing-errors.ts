/*
 * =============================================================================
 * BILLING VA KASSIR DOMENINING XATO TAKSONOMIYASI — kod -> {tone, SIRT}.
 *
 * NEGA ALOHIDA MODUL (`zone-errors.ts` ga qo'shilmaydi):
 *
 *   `zoneErrorView(code)`    -> `cameraZones.*` yoki `review.*`
 *   `billingErrorView(code)` -> `collect.*` yoki `billing.*`
 *
 *   Ikki modul IKKI BACKEND REYESTRINI ko'zguladi va ular alohida
 *   fayllarda yashaydi (`occupancy_errors.py` / `billing_errors.py`).
 *   Bittasiga qo'shish `error-codes.test.mjs:795-821` dagi ANIQ SONNI
 *   (`occupancyConstants.size === 15`) buzardi — ya'ni bo'linish uslub
 *   emas, DARVOZANING SHARTI (§0.1 M-B).
 *
 * ⚠ `network_unreachable` — YAGONA kod, u serverdan HECH QACHON kelmaydi.
 *   U `api-client` ning tarmoq xatosidan tug'iladi (§13.8 toast №6) va
 *   shuning uchun backendда `CLIENT_ONLY_ERROR_CODES` reyestrida turadi.
 *   Bu yerda esa u qolganlaridan farq QILMAYDI: ekran uchun u ham «sabab +
 *   nima qilish kerak» juftligiga ega bo'lgan xato bloki.
 *
 * ⚠ MATN BU YERDA YO'Q va bo'lmaydi. Modul faqat KALIT qaytaradi; uchala
 *   tildagi matn `frontend/messages/*.json` da. Backend ham shunday ishlaydi
 *   (`billing_errors.py` docstringi: «backend KOD beradi, matnni frontend
 *   uch tilda chizadi», D-02).
 *
 * D-02 NING MEXANIK SHAKLI: har kod uchun SABAB va TUZATISH matni uchala
 * tilda bo'lishi `scripts/error-codes.test.mjs` (G-17) da majburlanadi, va
 * o'sha darvoza SIRTNI HAM solishtiradi.
 * =============================================================================
 */

/**
 * Kassir yig'ish ekranining kodlari — matni `collect.*` da.
 *
 * Manba: `app/services/billing_errors.py::COLLECT_ERROR_CODES`.
 * Ikkisi QO'LDA sinxron saqlanadi (til chegarasi tufayli kompilyator
 * tekshiruvi yo'q — `zone-errors.ts` va `rbac.ts` bilan aynan bir xil
 * holat) va drift `scripts/error-codes.test.mjs` da qulflangan.
 */
export type CollectErrorCode =
  | "stall_not_found"
  | "tariff_missing"
  | "amount_unavailable"
  | "market_closed"
  | "fair_stall"
  | "stall_closed"
  | "stall_maintenance"
  | "stall_already_paid"
  | "stall_not_assigned"
  | "override_not_applicable"
  | "reason_required"
  | "idempotency_key_reused"
  | "payment_already_reversed";

/**
 * Smena ekranining kodlari — matni HAM `collect.*` da.
 *
 * Manba: `app/services/billing_errors.py::SHIFT_ERROR_CODES`.
 *
 * ⚠ ALOHIDA TIP, LEKIN BIR XIL SIRT: `/collect/shift` — `/collect` ning
 *   bolasi (§4.2), ya'ni matn namespace'i bir xil. Tiplarning ajratilishi
 *   backend reyestrlarining bo'linishini takrorlaydi va 06-09 ning router
 *   bo'linishiga mos keladi.
 */
export type ShiftErrorCode =
  | "no_open_shift"
  | "shift_already_open"
  | "shift_already_closed";

/**
 * Direktor yuzasining kodlari — matni `billing.*` da.
 *
 * Manba: `app/services/billing_errors.py::BILLING_ERROR_CODES`.
 */
export type BillingSurfaceErrorCode = "charge_immutable";

/**
 * Serverdan HECH QACHON kelmaydigan kod — matni `collect.*` da.
 *
 * Manba: `app/services/billing_errors.py::CLIENT_ONLY_ERROR_CODES`.
 */
export type ClientOnlyErrorCode = "network_unreachable";

export type BillingErrorCode =
  | CollectErrorCode
  | ShiftErrorCode
  | BillingSurfaceErrorCode
  | ClientOnlyErrorCode;

/**
 * Xato bloki ko'rsatiladigan EKRAN — matn kalitining namespace'i.
 *
 * ⚠ AYNAN IKKITA, backenddagi TO'RT reyestrga qaramay: reyestr EKRANNI
 *   bildiradi, `surface` esa YUZANI va ular 1:1 emas (smena kodlari ham,
 *   tarmoq kodi ham `collect.*` da yashaydi).
 */
export type BillingErrorSurface = "collect" | "billing";

/**
 * Xato blokining uchta ko'rinishi — `zone-errors.ts` dagi ikkitadan FARQ QILADI.
 *
 * ⚠ `neutral` BU YERDA KERAK va u vasvasa emas, D-19 ning talabi:
 *   `override_not_applicable` — foydalanuvchi HECH NIMANI buzmagan holat
 *   («sabab kerak emas ekan»). Uni `warning` qilish kassirga xato qilgandek
 *   tuyulardi va u keyingi safar sababni umuman yubormaslikka o'rganardi —
 *   ya'ni ton tanlovi xulqni o'zgartirardi.
 *
 * ⚠ `--color-warning` HECH QACHON matn rangi emas [MEROS: §12.2] — bu
 *   qiymat blok ramkasi va ikonkasini boshqaradi, matnni emas.
 */
export type BillingErrorTone = "neutral" | "warning" | "danger";

type BillingErrorMeta = {
  /**
   * `danger`  — amal BAJARILMADI va sabab TIZIMDA yoki ma'lumotda;
   * `warning` — holat NORMAL yoki chegara: ish davom etadi, faqat boshqa
   *             yo'l bilan (boshqa rasta, biriktirishlar sahifasi, ertaga);
   * `neutral` — hech nima buzilmagan, so'rov shunchaki ortiqcha edi.
   */
  readonly tone: BillingErrorTone;
  /** Matn qaysi namespace'dan olinadi. Backend reyestri bilan solishtiriladi. */
  readonly surface: BillingErrorSurface;
};

/**
 * 06-UI-SPEC §13.7 jadvali — KOD sifatida (o'n to'rt yozuv).
 *
 * ⚠ `Record<BillingErrorCode, ...>` ATAYIN: yetishmagan kod ham, ortiqcha
 *   kod ham TS xatosi. Bu KOMPILYATOR darajasidagi birinchi qatlam;
 *   ikkinchisi — backend bilan solishtiruvchi G-17 darvozasi.
 *
 * ⚠ `tone` va `surface` MUSTAQIL o'lchamlar va ularning birini
 *   ikkinchisidan hosil qilib bo'lmaydi.
 */
const BILLING_ERROR_META: Readonly<Record<BillingErrorCode, BillingErrorMeta>> =
  {
    /* 1-sirt — KASSIR YIG'ISH EKRANI (CASH-01…CASH-03). */
    stall_not_found: { tone: "danger", surface: "collect" },
    tariff_missing: { tone: "danger", surface: "collect" },
    amount_unavailable: { tone: "danger", surface: "collect" },
    /*
     * ⛔ `warning`, `danger` EMAS — va bu §9.4 ning `bg-warning/20` qatori
     *   bilan AYNAN mos. Yopiq kun NOSOZLIK emas, NORMAL kalendar holati:
     *   `danger` kassirni tizim buzilgan deb o'ylashga majburlardi va u
     *   eski qarzni olishdan (yagona qonuniy amaldan) voz kechardi.
     */
    market_closed: { tone: "warning", surface: "collect" },
    /*
     * ⛔ `neutral` (0028): yarmarka -- ma'muriyat QARORI, nosozlik ham,
     *   ogohlantirish ham emas. `warning` kassirni «nimadir noto'g'ri»
     *   deb o'ylashga majburlardi, holbuki hammasi rejadagidek.
     */
    fair_stall: { tone: "neutral", surface: "collect" },
    /*
     * 2026-08-25 (buyurtmachi): yopiq/ta'mirdagi rastadan patta
     * olinmaydi — `fair_stall` bilan bir sinf, ohang ham bir xil
     * `neutral`: hech nima buzilmagan, bu ma'muriyat qarori.
     */
    stall_closed: { tone: "neutral", surface: "collect" },
    stall_maintenance: { tone: "neutral", surface: "collect" },
    /*
     * 2026-08-25 №10: bu ODATDA adashish — «warning»: kassir to'xtaydi,
     * lekin «buzildi» deb qo'rqmaydi; ataylab yo'l fix matnida ochiq.
     */
    stall_already_paid: { tone: "warning", surface: "collect" },
    /*
     * ⛔ `warning`: rasta BOR, muammo boshqa EKRANDA hal bo'ladi
     *   (biriktirishlar sahifasi). `danger` uni `stall_not_found` bilan bir
     *   xil ko'rinishga solib, kassirni yana raqam terishga qaytarardi.
     */
    stall_not_assigned: { tone: "warning", surface: "collect" },
    /* ⛔ `neutral`: hech nima buzilmagan — sabab shunchaki ortiqcha edi. */
    override_not_applicable: { tone: "neutral", surface: "collect" },
    reason_required: { tone: "warning", surface: "collect" },
    idempotency_key_reused: { tone: "danger", surface: "collect" },
    payment_already_reversed: { tone: "warning", surface: "collect" },
    /* 2-sirt — SMENA (CASH-04). Namespace ham `collect.*`. */
    no_open_shift: { tone: "warning", surface: "collect" },
    shift_already_open: { tone: "warning", surface: "collect" },
    shift_already_closed: { tone: "warning", surface: "collect" },
    /* 3-sirt — DIREKTOR YUZASI (BILL-02). */
    charge_immutable: { tone: "warning", surface: "billing" },
    /* 4-sirt — MIJOZ TOMONI (§13.8 toast №6). */
    network_unreachable: { tone: "danger", surface: "collect" },
  };

/**
 * Kod -> uning namespace'i. `BILLING_ERROR_META` DAN HOSILA.
 *
 * Qo'lda ikkinchi ro'yxat yozilsa u jadval bilan bir kun ajralib ketardi
 * (`zone-errors.ts::SurfaceOf` bilan aynan bir xil qaror).
 */
type SurfaceOf<C extends BillingErrorCode> = C extends BillingSurfaceErrorCode
  ? "billing"
  : "collect";

/**
 * Kod -> xato blokining butun kontrakti (SABAB + NIMA QILISH KERAK).
 *
 * ⚠ Bu TAQSIMLANGAN BIRLASHMA (`{[C in ...]: ...}[...]`), oddiy obyekt tipi
 *   emas. Sabab amaliy: shundagina `causeKey` ning tipi FAQAT haqiqatan
 *   mavjud kalitlarni o'z ichiga oladi. Yassi yozuv
 *   `billing.errorCause.no_open_shift` kabi HECH QACHON mavjud
 *   bo'lmaydigan kalitni ham qonuniy qilardi va `t()` ning kalit
 *   xavfsizligi (`src/global.ts`) shu joyda yo'qolardi.
 */
export type BillingErrorView = {
  [C in BillingErrorCode]: {
    readonly code: C;
    readonly tone: BillingErrorTone;
    readonly surface: SurfaceOf<C>;
    readonly causeKey: `${SurfaceOf<C>}.errorCause.${C}`;
    readonly fixKey: `${SurfaceOf<C>}.errorFix.${C}`;
  };
}[BillingErrorCode];

export function isBillingErrorCode(value: string): value is BillingErrorCode {
  return Object.hasOwn(BILLING_ERROR_META, value);
}

/**
 * Kod -> sabab va tuzatish kalitlari.
 *
 * `null` — NOMA'LUM kod. Chaqiruvchi u holda `errors.generic` ga tushadi va
 * xom `detail` ni KO'RSATMAYDI: `detail`, stack izi yoki SQL matni
 * foydalanuvchiga HECH QACHON chiqmaydi (T-06-09).
 */
export function billingErrorView(
  code: string | null | undefined,
): BillingErrorView | null {
  if (typeof code !== "string" || !isBillingErrorCode(code)) return null;

  const meta = BILLING_ERROR_META[code];
  return {
    code,
    tone: meta.tone,
    surface: meta.surface,
    causeKey: `${meta.surface}.errorCause.${code}`,
    fixKey: `${meta.surface}.errorFix.${code}`,
  } as BillingErrorView;
}
