import { ApiError, errorMessageKey } from "@/lib/api-client";
import type { ErrorMessageKey } from "@/lib/api-client";

/*
 * =============================================================================
 * 2-faza xato kodlari -> tarjima kaliti.
 *
 * NEGA ALOHIDA MODUL, `queries.ts::adminErrorMessageKey` ning kengaytmasi
 * EMAS: o'sha funksiya 1-fazaning uchta ma'muriy ekraniga xizmat qiladi va
 * ular shu holicha ishlaydi. Unga yigirma uchta domen kodini qo'shish
 * mavjud ekranlarni sababsiz o'zgartirardi (va ularning testlarini
 * qayta ko'rib chiqishga majburlardi), holbuki bu kodlar u yerda HECH
 * QACHON uchramaydi.
 *
 * ZANJIR: `marketErrorMessageKey` -> topa olmasa -> `errorMessageKey`.
 * Ya'ni tarmoq uzilishi, 403 va 404 uchun mantiq TAKRORLANMAYDI — u
 * bitta joyda (`api-client.ts`) qoladi va bu yerda faqat DOMEN kodlari
 * yashaydi.
 *
 * XAVFSIZLIK (T-02-99): ro'yxatda yo'q kod `errors.generic` ga tushadi —
 * xom `detail`, stack izi yoki SQL matni foydalanuvchiga HECH QACHON
 * ko'rsatilmaydi.
 *
 * TO'LIQLIK DARVOZASI: `frontend/scripts/error-codes.test.mjs` backend'dagi
 * `MARKET_ERROR_CODES` ni o'qib, (a) har bir kod uchun shu yerda `case`
 * borligini, (b) qaytarilgan kalit UCHALA tilda mavjudligini tekshiradi.
 * Usiz "kod qo'shildi, tarjima unutildi" holati jimgina `errors.generic`
 * ga aylanardi va sabab yo'qolardi.
 * =============================================================================
 */

/**
 * Domen ekranlariga XOS xato kalitlari.
 *
 * Union TypeScript'ga tarjima kalitining MAVJUDLIGINI tekshirtirmaydi
 * (`next-intl` kalitlari JSON'da) — lekin u kod ko'rigida noto'g'ri
 * yozilgan kalitni ko'rsatadi va yuqoridagi test uni mexanik ushlaydi.
 */
export type MarketErrorMessageKey =
  | "stalls.codeTaken"
  | "stalls.codeRetired"
  | "stalls.categoryPeriodExists"
  | "stalls.categoryPastLocked"
  | "zones.nameTaken"
  | "zones.inUse"
  | "categories.nameTaken"
  | "categories.inUse"
  | "tariffs.dateTaken"
  | "tariffs.pastLocked"
  | "tariffs.mustBeFuture"
  | "calendar.exceptionExists"
  | "vendors.phoneTaken"
  | "vendors.periodOverlaps"
  | "vendors.periodClosed"
  | "vendors.invalidPeriod"
  | "wizard.incomplete"
  | "wizard.cannotDeleteActive"
  | "import.validationFailed"
  | "import.fileTooLarge"
  | "import.fileTooComplex"
  | "cameras.nvrHostTaken"
  | "cameras.nvrHostPublicBlocked"
  | "cameras.nvrAddressInvalid"
  | "cameras.discoveryAlreadyRunning"
  | "cameras.nvrNotFound"
  | "import.unsupportedType"
  | "import.conflict"
  | "import.staffRosterTooLarge";

/**
 * `ApiError.detail` -> tarjima kaliti (2-faza domeni).
 *
 * Kod topilmasa umumiy xaritaga tushadi, ya'ni tarmoq/403/404 holatlari
 * mavjud xulqni saqlaydi.
 */
export function marketErrorMessageKey(
  error: unknown,
): ErrorMessageKey | MarketErrorMessageKey {
  if (error instanceof ApiError) {
    switch (error.detail) {
      /* --- rasta reestri (02-08) --- */
      case "stall_code_taken":
        return "stalls.codeTaken";
      case "stall_code_retired":
        return "stalls.codeRetired";
      case "category_period_exists":
        return "stalls.categoryPeriodExists";
      case "category_period_past_locked":
        return "stalls.categoryPastLocked";

      /* --- zona / toifa reestrlari (02-08) --- */
      case "zone_name_taken":
        return "zones.nameTaken";
      case "zone_in_use":
        return "zones.inUse";
      case "category_name_taken":
        return "categories.nameTaken";
      case "category_in_use":
        return "categories.inUse";

      /* --- tarif (02-09) --- */
      case "tariff_already_set_for_date":
        return "tariffs.dateTaken";
      case "tariff_past_locked":
        return "tariffs.pastLocked";
      case "valid_from_must_be_future":
        return "tariffs.mustBeFuture";

      /* --- kalendar (02-09) --- */
      case "calendar_exception_exists":
        return "calendar.exceptionExists";

      /* --- sotuvchi va biriktirish (02-10) --- */
      case "vendor_phone_taken":
        return "vendors.phoneTaken";
      case "assignment_period_overlaps":
        return "vendors.periodOverlaps";
      case "assignment_not_open":
        return "vendors.periodClosed";
      // Yopish sanasi boshlanish sanasidan oldin (yoki teng emas) — bu
      // FORMA xatosi, "ruxsat yo'q" emas, shuning uchun umumiy 4xx
      // matniga tushirilmaydi.
      case "invalid_period":
        return "vendors.invalidPeriod";

      /* --- usta (02-11) --- */
      case "market_incomplete":
        return "wizard.incomplete";
      case "market_is_active":
        return "wizard.cannotDeleteActive";

      /* --- import (02-12) --- */
      case "import_validation_failed":
        return "import.validationFailed";
      case "file_too_large":
        return "import.fileTooLarge";
      case "file_too_complex":
        return "import.fileTooComplex";
      case "unsupported_file_type":
        return "import.unsupportedType";
      // Konstrayt buzilishi YOZISH paytida, ya'ni faqat poyga holati (ikki
      // admin bir vaqtda import qildi). Qator raqami YO'Q va bo'lishi ham
      // mumkin emas — yagona ma'noli harakat qayta urinish.
      case "import_conflict":
        return "import.conflict";

      /* --- xodimlar rosteri (02-24) --- */
      // `file_too_complex` DAN AJRATILGAN: u faylning tuzilishi haqida,
      // bu esa HUJUM YUZASINING chegarasi (bir so'rovda nechta hisob
      // yaratilishi mumkinligi). Adminga aytiladigan harakat ham boshqa:
      // "faylni soddalashtiring" emas, "ro'yxatni bo'laklarga bo'ling".
      case "staff_roster_too_large":
        return "import.staffRosterTooLarge";

      /* --- NVR qurilmalari va kashfiyot (03-06) --- */
      case "nvr_host_taken":
        return "cameras.nvrHostTaken";
      // `nvr_address_invalid` DAN AJRATILGAN va bu ataylab: birinchisi
      // TERISH xatosi (yechim — qayta yozish), ikkinchisi ARXITEKTURA
      // qoidasi (yechim — tunnel ichidagi manzilni topish). Bitta matn
      // ikkalasiga ham noto'g'ri maslahat berardi.
      case "nvr_host_public_blocked":
        return "cameras.nvrHostPublicBlocked";
      case "nvr_address_invalid":
        return "cameras.nvrAddressInvalid";
      // ⚠ UI BU HOLATNI XATO SIFATIDA KO'RSATMAYDI (UI-SPEC §5.6): javob
      // tanasidagi mavjud `run_id` qabul qilinadi va o'sha yugurish poll
      // qilinadi. Kalit shu sababdan FAQAT zaxira yo'l uchun — `run_id`
      // kutilmaganda bo'lmasa.
      case "discovery_already_running":
        return "cameras.discoveryAlreadyRunning";
      case "nvr_not_found":
        return "cameras.nvrNotFound";

      default:
        break;
    }
  }

  return errorMessageKey(error);
}
