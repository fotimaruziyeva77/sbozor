import { z } from "zod";

import type { Role } from "@/lib/rbac";

/**
 * core-api HTTP kontraktining runtime sxemalari (01-06 / 01-07).
 *
 * NEGA `zod`, `interface` EMAS: TypeScript tipi kompilyatsiyadan keyin
 * yo'qoladi va noto'g'ri javob shakli faqat komponent ichida `undefined`
 * bo'lib chiqadi. `schema.parse()` esa chegarada, aniq xato bilan yiqiladi —
 * ya'ni backend kontrakti o'zgargani UI'da g'alati bo'shliq emas, xato
 * bo'lib ko'rinadi.
 */

/** Qo'llab-quvvatlanadigan tillar — `sbozor_core.enums.Locale` bilan AYNAN mos. */
export const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"] as const;

export const localeSchema = z.enum(LOCALES);
export type ApiLocale = z.infer<typeof localeSchema>;

/**
 * Til ENDONIMLARI — ataylab tarjima fayllarida emas (01-08 qarori).
 *
 * "Русский" ni o'zbekchaga o'girish tanlovni o'qib bo'lmas qiladi:
 * foydalanuvchi ro'yxatdan o'zi tushunadigan YAGONA so'zni izlaydi. Shu
 * sababli yorliqlar `next-intl` katalogidan tashqarida va bitta joyda
 * turadi — til almashtirgich ham, yangi foydalanuvchi formasi ham shu
 * ro'yxatni o'qiydi va ular ajralib keta olmaydi.
 */
export const LOCALE_LABELS: Readonly<Record<ApiLocale, string>> = {
  "uz-Latn": "O'zbekcha",
  "uz-Cyrl": "Ўзбекча",
  ru: "Русский",
};

/**
 * Pul yordamchisi (Pitfall 7).
 *
 * Backend so'mni `BIGINT` da saqlaydi va JSON'da `number` bo'lib keladi.
 * JavaScript'da butun sonning xavfsiz chegarasi 2^53-1; undan oshgan qiymat
 * JIMGINA yaxlitlanadi. Shuning uchun chegara SXEMADA tekshiriladi: 1-fazada
 * pul maydoni yo'q, lekin 5- va 6-fazalar shu yordamchini import qiladi va
 * chegarani qayta ixtiro qilmaydi.
 */
export const soumSchema = z.number().int().max(Number.MAX_SAFE_INTEGER);

/**
 * Bozor havolasi — auth javoblarida `id`, nom va BOZOR faolligi keladi.
 *
 * `is_active === false` — usta tugallanmagan QORALAMA bozor. Maydon
 * `MAJBURIY` va `.optional()` EMAS: bayroq yo'qolganda UI qoralamani
 * faoldan ajrata olmaydi va foydalanuvchi chala bozorni tayyor deb
 * o'ylaydi. Backend'dagi `MarketRef.is_active` ham aynan shu sababdan
 * standart qiymatsiz.
 */
export const marketRefSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  is_active: z.boolean(),
});
export type MarketSummary = z.infer<typeof marketRefSchema>;

/**
 * `GET /api/v1/markets` elementi (01-07) — `marketRefSchema` ning kengaytmasi.
 *
 * `is_active` bu yerda TAKRORLANMAYDI: u endi bazaviy sxemadan keladi.
 * Takror e'lon zarar qilmasdi, lekin ikki joyda yashagan maydon bir kun
 * ajralib ketardi (biri `optional`, ikkinchisi majburiy).
 */
export const marketListItemSchema = marketRefSchema.extend({
  timezone: z.string(),
});
export type MarketListItem = z.infer<typeof marketListItemSchema>;

export const marketListSchema = z.array(marketListItemSchema);

/**
 * `POST /api/v1/auth/login` javobi.
 *
 * `market === null` — bozor tanlanmagan (platforma admini yoki bir nechta
 * a'zolik). Bu holatda refresh cookie ham BERILMAYDI (01-06 qarori):
 * keyingi qadam majburiy ravishda `/auth/select-market`.
 */
export const loginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_in: z.number().int(),
  must_change_password: z.boolean(),
  locale: localeSchema,
  market: marketRefSchema.nullable(),
  markets: z.array(marketRefSchema),
  roles: z.array(z.string()),
  is_platform_admin: z.boolean(),
});
export type LoginResponse = z.infer<typeof loginResponseSchema>;

/**
 * `POST /auth/select-market` va `POST /auth/refresh` — AYNAN bir xil shakl.
 * Ikkalasi ham "sessiya bozor kontekstiga bog'landi" faktini qaytaradi.
 */
export const sessionResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_in: z.number().int(),
  roles: z.array(z.string()),
  market: marketRefSchema,
});
export type SessionResponse = z.infer<typeof sessionResponseSchema>;

/** `GET /api/v1/me` (01-07) — profil; sessiya tiklashda locale shu yerdan keladi (D-13). */
export const meResponseSchema = z.object({
  id: z.uuid(),
  phone: z.string(),
  full_name: z.string().nullable(),
  locale: localeSchema,
  roles: z.array(z.string()),
  market_id: z.uuid().nullable(),
  is_platform_admin: z.boolean(),
  must_change_password: z.boolean(),
});
export type MeResponse = z.infer<typeof meResponseSchema>;

/** `PATCH /api/v1/me` javobi — faqat saqlangan til. */
export const meLocaleResponseSchema = z.object({ locale: localeSchema });

/* ---------------------------------------------------------------------------
 * Foydalanuvchi boshqaruvi (01-07 `app/api/v1/users.py`)
 * ------------------------------------------------------------------------- */

/**
 * D-04 ning ikkinchi bosqichi — bozor admini bera oladigan rollar.
 *
 * Nomi backend'dagi `services/core-api/app/api/v1/users.py::
 * MARKET_ADMIN_ASSIGNABLE_ROLES` bilan AYNAN bir xil va qiymati ham
 * o'sha `frozenset({CASHIER, INSPECTOR})` ning nusxasi.
 *
 * DIQQAT: bu ro'yxat XAVFSIZLIK CHEGARASI EMAS. Haqiqiy darvoza serverda,
 * `_assert_roles_assignable()` ichida va u yaratishdan OLDIN 403
 * (`role_not_allowed`) qaytaradi. Bu yerdagi nusxa faqat "ko'rinmasin"
 * degan savolga javob beradi: bozor admini bera OLMAYDIGAN rolni forma
 * umuman ko'rsatmaydi, ya'ni u kutilgan rad javobini oldindan biladi.
 * Ikkisi ajralib qolsa foydalanuvchi 403 oladi — ma'lumot ochilmaydi.
 */
export const MARKET_ADMIN_ASSIGNABLE_ROLES = ["cashier", "inspector"] as const;

/**
 * Platforma admini bera oladigan rollar — TO'RTTA (CR-03).
 *
 * `platform_admin` bu ro'yxatda ATAYIN YO'Q va u yerga hech qachon
 * qo'shilmasligi kerak. Sabab: "platforma admini" `users.is_platform_admin`
 * BAYROG'I bilan aniqlanadi, `user_market_roles` dagi a'zolik roli bilan
 * emas. Ikkisi bir xil narsa emas va faqat bayroq haqiqiy hisoblanadi.
 *
 * Agar `platform_admin` a'zolik roli sifatida berilsa, hosil bo'lgan hisob
 * bir vaqtning o'zida HAM ortiqcha huquqli, HAM buzuq bo'ladi: token
 * `market_view_all` huquqini olib butun platformadagi bozorlar ro'yxatini
 * ochadi (tenant chegarasidan sizish), lekin `is_platform_admin` `false`
 * bo'lgani uchun `POST /auth/select-market` uni boshqa bozorga kiritmaydi —
 * ya'ni nomi aytgan ishni ham bajara olmaydi.
 *
 * HAQIQIY darvoza serverda: `users.py::_assert_roles_assignable()` bu rolni
 * so'ragan har qanday chaqiruvni 403 (`role_not_allowed`) bilan rad etadi.
 * Bu yerdagi ro'yxat faqat formada ortiqcha katakcha KO'RINMASLIGI uchun.
 */
export const PLATFORM_ADMIN_ASSIGNABLE_ROLES = [
  "director",
  "market_admin",
  "cashier",
  "inspector",
] as const;

/**
 * Yaratish formasida ko'rsatiladigan rollar (D-04 darajasi bo'yicha).
 *
 * Platforma admini — to'rt rol (`platform_admin` bundan MUSTASNO, u
 * membership roli emas); qolgan hamma (jumladan bozor admini) — faqat
 * `MARKET_ADMIN_ASSIGNABLE_ROLES`. Ro'yxat SHU YERDA quriladi, ya'ni
 * komponentda qattiq yozilgan rol nomlari bo'lmaydi va D-04 ni o'zgartirish
 * bitta joyni tahrirlash bilan cheklanadi.
 */
export function assignableRoles(isPlatformAdmin: boolean): readonly Role[] {
  return isPlatformAdmin
    ? PLATFORM_ADMIN_ASSIGNABLE_ROLES
    : MARKET_ADMIN_ASSIGNABLE_ROLES;
}

/**
 * `GET /api/v1/users` qatori.
 *
 * `password_hash` bu yerda YO'Q va bo'lishi ham mumkin emas —
 * `auth_list_users()` uni umuman qaytarmaydi (01-07).
 *
 * `locale` ATAYIN `z.string()`, `localeSchema` emas: backend uni `str`
 * sifatida qaytaradi va bir kun yangi til qo'shilsa, ro'yxat butunlay
 * yiqilmasligi kerak — bu maydon faqat ko'rsatish uchun.
 */
export const userListItemSchema = z.object({
  id: z.uuid(),
  phone: z.string(),
  full_name: z.string().nullable(),
  roles: z.array(z.string()),
  is_active: z.boolean(),
  must_change_password: z.boolean(),
  locale: z.string(),
  created_at: z.string(),
});
export type UserListItem = z.infer<typeof userListItemSchema>;

export const userListResponseSchema = z.object({
  items: z.array(userListItemSchema),
});

/**
 * `POST /api/v1/users` javobi (D-02).
 *
 * `temporary_password` BIR MARTA ochiq keladi va boshqa hech qachon
 * qaytarilmaydi (DB'da faqat Argon2id hash yashaydi). Shuning uchun uni
 * faqat dialog holatida ushlab turish mumkin — hech qanday keshga,
 * URL'ga yoki brauzer omboriga tushmasligi kerak (T-01-68).
 */
export const createUserResponseSchema = z.object({
  id: z.uuid(),
  temporary_password: z.string(),
});

/** `POST /api/v1/users/{id}/reset-password` javobi (D-02). */
export const resetPasswordResponseSchema = z.object({
  temporary_password: z.string(),
});

/* ---------------------------------------------------------------------------
 * Audit ko'rish (01-07 `app/api/v1/audit.py`, D-11 / D-12)
 * ------------------------------------------------------------------------- */

/**
 * `audit_log.action` qiymatlari — `sbozor_core.enums.AuditAction` nusxasi.
 *
 * Ro'yxat FILTR variantlarini quradi va har bir qiymat uchun
 * `audit.actions.<qiymat>` tarjima kaliti UCHALA tilda bo'lishi shart.
 * Ikkisining mosligi `frontend/scripts/audit-actions.test.mjs` da qulflangan:
 * backend yangi hodisa qo'shsa-yu kalit qo'shilmasa, jurnalda tarjimasiz
 * texnik identifikator ko'rinib qolardi.
 */
export const AUDIT_ACTIONS = [
  "insert",
  "update",
  "delete",
  "read",
  "login",
  "login_failed",
  "logout",
  "market_selected",
  "password_reset",
  "password_changed",
  "user_blocked",
  "user_unblocked",
  "refresh_reuse_detected",
] as const;
export type AuditActionValue = (typeof AUDIT_ACTIONS)[number];

export function isAuditAction(value: string): value is AuditActionValue {
  return (AUDIT_ACTIONS as readonly string[]).includes(value);
}

/**
 * 1-fazada auditga tushadigan jadvallar
 * (`services/core-api/app/security/audit.py` konstantalari + trigger
 * o'rnatilgan jadvallar).
 *
 * Ro'yxatda YO'Q nom xato emas: keyingi fazalar yangi jadval qo'shadi va
 * u tarjimasiz, xom nomi bilan ko'rinadi — bu jadval nomi texnik
 * identifikator bo'lgani uchun to'g'ri xulq (D-16 ruhida).
 */
export const AUDIT_TABLES = [
  "users",
  "user_market_roles",
  "markets",
  "refresh_tokens",
  "audit_log",
] as const;
export type AuditTableValue = (typeof AUDIT_TABLES)[number];

export function isAuditTable(value: string): value is AuditTableValue {
  return (AUDIT_TABLES as readonly string[]).includes(value);
}

/**
 * `GET /api/v1/audit` qatori (D-12: kim / qachon / nima / eski->yangi).
 *
 * `old_value`/`new_value` backend'da ALLAQACHON maskalangan
 * (`mask_sensitive()` sezgir kalitlarni `"***"` ga almashtiradi, T-01-52).
 * UI qiymatni o'zgartirmasdan ko'rsatadi va qo'shimcha maydon so'ramaydi.
 */
export const auditEntrySchema = z.object({
  id: z.number().int(),
  at: z.string(),
  business_date: z.string(),
  actor_user_id: z.uuid().nullable(),
  actor_label: z.string().nullable(),
  action: z.string(),
  table_name: z.string(),
  row_id: z.uuid().nullable(),
  changed_keys: z.array(z.string()).nullable(),
  old_value: z.record(z.string(), z.unknown()).nullable(),
  new_value: z.record(z.string(), z.unknown()).nullable(),
  request_id: z.string().nullable(),
  source: z.string(),
});
export type AuditEntry = z.infer<typeof auditEntrySchema>;

/** `next_cursor === null` — oxirgi sahifa (keyset, OFFSET yo'q). */
export const auditListResponseSchema = z.object({
  items: z.array(auditEntrySchema),
  next_cursor: z.string().nullable(),
});

/* ===========================================================================
 * 2-FAZA: BOZOR DOMENI — zona / toifa / rasta / tarif / kalendar / sotuvchi
 * ===========================================================================
 *
 * Manba — `services/core-api/app/schemas.py` ning shu nomli bo'limi. Maydon
 * nomlari backend'dagidek `snake_case` va ATAYIN camelCase ga o'girilmaydi:
 * o'girish qatlami har yangi maydonda yangilanishi kerak bo'lardi va
 * unutilgan joyda maydon jimgina `undefined` bo'lib chiqardi.
 *
 * SANA va VAQT `z.string()` bo'lib qoladi (`z.iso.date()` emas): backend
 * ularni ISO satr sifatida yuboradi va biz uni `Date` ga faqat KO'RSATISH
 * joyida (`next-intl` formatlagichi) aylantiramiz. Chegarada `Date` ga
 * aylantirish vaqt mintaqasi bo'yicha jimgina siljish kiritardi
 * (`2026-08-01` -> mahalliy yarim tunda oldingi kun).
 *
 * NULLABLE, OPTIONAL EMAS: backend maydonni TUSHIRMAYDI, u `null` yuboradi
 * (`category_id: UUID | None` -> `"category_id": null`). `.optional()`
 * ishlatilsa maydonning UMUMAN yo'qligi ham qonuniy bo'lib qolardi va
 * kontrakt buzilishi chegaradan o'tib ketardi.
 *
 * ⚠ XARITA KATAGINING RANG TIPI BU YERDA E'LON QILINMAYDI va bu qoida
 * mexanik darvoza bilan qulflangan (uning nomi shu fayl bo'ylab grep
 * qilinadi, shuning uchun izohda ham YOZILMAYDI — darvoza o'z-o'ziga
 * qarshi turmasin). Sabab: u API kontrakti emas, RENDER kontrakti
 * (UI-SPEC §7.2). Server `status` + `has_vendor` xom faktlarini beradi,
 * rang esa ulardan HOSIL QILINADI va uning uyi —
 * `components/stalls/stall-tone.ts`. Bu yerga ko'chirilsa, 6-fazada
 * "to'langan/qarzdor" manbai qo'shilishi API tipini o'zgartirishni talab
 * qilardi; hosila funksiyada esa u bitta `switch` ga qo'shiladi.
 * ------------------------------------------------------------------------- */

/**
 * `stalls.status` qiymatlari — `sbozor_core.enums.StallStatus` nusxasi.
 *
 * Qiymatlarning O'ZI DB kontenti va bitta tilda (D-16); UI ularni
 * `stalls.status.<qiymat>` kalitlari orqali uch tilda ko'rsatadi, ya'ni til
 * almashtirish DB qiymatiga hech qachon tegmaydi.
 */
export const STALL_STATUSES = ["active", "maintenance", "closed"] as const;
export type StallStatusValue = (typeof STALL_STATUSES)[number];

export function isStallStatus(value: string): value is StallStatusValue {
  return (STALL_STATUSES as readonly string[]).includes(value);
}

export const stallStatusSchema = z.enum(STALL_STATUSES);

/* --- Zonalar (D-03) ------------------------------------------------------ */

/**
 * `GET /zones` qatori.
 *
 * `stall_count` "bu zonani o'chira olamanmi?" savoliga oldindan javob
 * beradi — UI tugmani bloklash uchun ikkinchi so'rov qilmaydi.
 *
 * `name` — DB KONTENTI va tarjima QILINMAYDI (D-16).
 */
export const zoneItemSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  stall_count: z.number().int(),
});
export type ZoneItem = z.infer<typeof zoneItemSchema>;

/** `GET /zones` — TO'LIQ ro'yxat. `next_cursor` YO'Q (backend kontrakti). */
export const zoneListResponseSchema = z.object({
  items: z.array(zoneItemSchema),
});

/* --- Toifalar (D-05) ----------------------------------------------------- */

/**
 * `GET /categories` qatori.
 *
 * `current_tariff_soum === null` — MA'NOLI holat, nuqson emas (D-08): toifa
 * bor, narx yo'q. UI aynan shu holatni ogohlantirish bilan ko'rsatadi va
 * ustaning 4-qadami undan boshlanadi. Backend `0` qaytarMAYDI — u "bepul
 * toifa" degan yolg'on ma'no berardi.
 */
export const categoryItemSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  stall_count: z.number().int(),
  current_tariff_soum: soumSchema.nullable(),
});
export type CategoryItem = z.infer<typeof categoryItemSchema>;

/** `GET /categories` — sahifalashsiz (zonalar bilan bir xil sabab). */
export const categoryListResponseSchema = z.object({
  items: z.array(categoryItemSchema),
});

/* --- Rastalar (D-01/D-02/D-04) ------------------------------------------- */

/**
 * `GET /stalls` qatori — UI-SPEC §8.2 ustunlarining manbai.
 *
 * UCHTA maydon `null` bo'lishi mumkin va uchalasi HAR XIL holat:
 *   `category_id`/`category_name` — toifa davri yozilmagan (chala import);
 *   `vendor_id`/`vendor_name`     — bugun biriktirilgan sotuvchi yo'q
 *                                   (D-11 — anomaliya alomati, xato emas);
 *   `tariff_soum`                 — toifa bor, bugungi narxi yo'q (D-08).
 * Ularni aralashtirish 6-fazadagi anomaliya hisobini buzardi.
 */
export const stallListItemSchema = z.object({
  id: z.uuid(),
  code: z.string(),
  zone_id: z.uuid(),
  zone_name: z.string(),
  category_id: z.uuid().nullable(),
  category_name: z.string().nullable(),
  status: stallStatusSchema,
  vendor_id: z.uuid().nullable(),
  vendor_name: z.string().nullable(),
  tariff_soum: soumSchema.nullable(),
  created_at: z.string(),
});
export type StallListItem = z.infer<typeof stallListItemSchema>;

/**
 * `GET /stalls/{id}` va yozuv endpointlarining javobi — qatorning KENGAYTMASI.
 *
 * `phone` — sotuvchining telefoni, ya'ni SHAXSIY MA'LUMOT (D-09). U
 * `vendor_id` bilan birga keladi yoki ikkalasi ham `null`. Ro'yxat qatorida
 * bu maydon ATAYIN yo'q: har qatorga telefon yuklash reestrni shaxsiy
 * ma'lumot ombori qilardi.
 */
export const stallDetailSchema = stallListItemSchema.extend({
  phone: z.string().nullable(),
  assignment_from: z.string().nullable(),
  note: z.string().nullable(),
});
export type StallDetail = z.infer<typeof stallDetailSchema>;

/**
 * `GET /stalls` — keyset sahifa (`next_cursor === null` bo'lsa oxirgisi).
 *
 * Tartib SERVERDA hal qilinadi (`code_sort` — inson-raqamli: 2 < 10 < 100)
 * va frontend uni QAYTA SARALAMAYDI (UI-SPEC §7.3): klient tomonda saralash
 * uchala tilda boshqa natija berardi va xarita bilan ro'yxat ajralib ketardi.
 */
export const stallListResponseSchema = z.object({
  items: z.array(stallListItemSchema),
  next_cursor: z.string().nullable(),
});

/* --- Plan-xarita (MARKET-06, D-19/D-20) ---------------------------------- */

/**
 * Xaritadagi bitta katak.
 *
 * `tone` ham, koordinata ham YO'Q va qo'shilmaydi (D-19/D-20): rang
 * frontendda hosil bo'ladi, joylashuv esa avtomatik (CSS Grid) — saqlangan
 * `x`/`y` bo'lmagani uchun ular eskirib ham qolmaydi.
 */
export const mapCellSchema = z.object({
  id: z.uuid(),
  code: z.string(),
  status: stallStatusSchema,
  has_vendor: z.boolean(),
});
export type MapCell = z.infer<typeof mapCellSchema>;

/** Zona bloki — kataklar `code_sort` tartibida. `name` tarjima qilinmaydi. */
export const mapZoneSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  cells: z.array(mapCellSchema),
});
export type MapZone = z.infer<typeof mapZoneSchema>;

/** `GET /stalls/map` — zonalar nom tartibida, sahifalashsiz. */
export const stallMapResponseSchema = z.object({
  zones: z.array(mapZoneSchema),
});

/* --- Tariflar (D-06/D-07) ------------------------------------------------ */

/**
 * Tarif tarixining bitta qatori.
 *
 * `valid_to` DB'da USTUN EMAS — u keyingi qatordan hisoblanadi va oxirgi
 * qator uchun `null` ("hozircha amalda").
 *
 * `is_past` — UI tahrir tugmasini ko'rsatmaslik uchun QULAYLIK; haqiqiy
 * darvoza serverda (`trg_tariff_past_immutable`, D-07).
 */
export const tariffItemSchema = z.object({
  id: z.uuid(),
  category_id: z.uuid(),
  category_name: z.string(),
  amount_soum: soumSchema,
  valid_from: z.string(),
  valid_to: z.string().nullable(),
  is_past: z.boolean(),
});
export type TariffItem = z.infer<typeof tariffItemSchema>;

/**
 * `GET /tariffs` — tarif tarixi + ruxsat etilgan ENG ERTA sana.
 *
 * `min_valid_from` MAJBURIY: `.optional()` ham, `.nullable()` ham EMAS. U
 * serverning ruxsat etgan eng erta `valid_from` i — qoralama bozorda
 * `operating_since`, faol bozorda ertangi kun (02-09). Ro'yxat BO'SH
 * bo'lganda ham keladi, chunki ustaning 4-qadami aynan bo'sh ro'yxatdan
 * boshlanadi.
 *
 * KLIENT BU SANANI O'ZI HISOBLAMAYDI. Ertangi kunni lokal hisoblash
 * qoralama bozorda server RUXSAT BERGAN boshlang'ich sanani (o'tmishdagi
 * `operating_since`) UI darajasida taqiqlab qo'yardi va ustaning 4-qadami
 * bajarilmas bo'lardi. Ixtiyoriy qilib qo'yish esa har chaqiruvchiga uni
 * "unutish" imkonini berardi.
 *
 * ⚠ BU DARVOZA EMAS — u sana maydonining `min` atributi (02-15). Haqiqiy
 * tekshiruv serverda va u DevTools bilan olib tashlanmaydi.
 *
 * `next_cursor` YO'Q: tarif ro'yxati sahifalanmaydi (backend kontrakti).
 */
export const tariffListResponseSchema = z.object({
  items: z.array(tariffItemSchema),
  min_valid_from: z.string(),
});

/* --- Ish kunlari kalendari (D-17/D-18) ----------------------------------- */

/**
 * Haftalik jadvaldan chiqadigan alohida kun.
 *
 * `is_open` IKKI TOMONLAMA: `false` — bayram/yopiq kun, `true` — jadvalda
 * dam olish bo'lgan, lekin ISHLAYDIGAN kun.
 */
export const calendarExceptionSchema = z.object({
  id: z.uuid(),
  exception_date: z.string(),
  is_open: z.boolean(),
  note: z.string().nullable(),
});
export type CalendarException = z.infer<typeof calendarExceptionSchema>;

/** `GET /calendar` — haftalik jadval (1=dushanba … 7=yakshanba) + istisnolar. */
export const calendarResponseSchema = z.object({
  open_weekdays: z.array(z.number().int().min(1).max(7)),
  exceptions: z.array(calendarExceptionSchema),
});

/* --- Sotuvchilar va biriktirishlar (D-09…D-12) --------------------------- */

/**
 * `GET /vendors` qatori — SHAXSIY MA'LUMOT (D-09: o'qish ham auditda).
 *
 * `stall_codes` ro'yxati SERVERDA cheklangan (20 ta), `stall_count` esa
 * to'liq son — ya'ni badge kesilganda ham "nechta?" savolining javobi
 * yo'qolmaydi.
 *
 * `full_name` va `phone` — DB kontenti, tarjima qilinmaydi (D-16).
 */
export const vendorListItemSchema = z.object({
  id: z.uuid(),
  full_name: z.string(),
  phone: z.string(),
  stall_count: z.number().int(),
  stall_codes: z.array(z.string()),
  created_at: z.string(),
});
export type VendorListItem = z.infer<typeof vendorListItemSchema>;

/** `GET /vendors` — keyset sahifa (sotuvchi soni rastalar bilan o'sadi). */
export const vendorListResponseSchema = z.object({
  items: z.array(vendorListItemSchema),
  next_cursor: z.string().nullable(),
});

/**
 * Rasta ↔ sotuvchi biriktirish DAVRI.
 *
 * `to_date === null` — davr OCHIQ (sotuvchi hozir ham shu rastada).
 * Chegara `[)`: almashinuv kuni YANGI sotuvchiga tegishli (D-10).
 * PUL MAYDONI YO'Q va bo'lmaydi — qarz eski sotuvchida qoladi.
 */
export const assignmentItemSchema = z.object({
  id: z.uuid(),
  stall_id: z.uuid(),
  stall_code: z.string(),
  vendor_id: z.uuid(),
  vendor_name: z.string(),
  from_date: z.string(),
  to_date: z.string().nullable(),
});
export type AssignmentItem = z.infer<typeof assignmentItemSchema>;

/** `GET /stalls/{id}/assignments` — sahifalashsiz to'liq tarix. */
export const assignmentListResponseSchema = z.object({
  items: z.array(assignmentItemSchema),
});

/* --- "Yangi bozor" ustasi (MARKET-01, D-16) ------------------------------ */

/**
 * `POST /markets` VA `POST /markets/{id}/activate` javobi — BITTA shakl.
 *
 * `is_active` yaratishda har doim `false` (yangi bozor QORALAMA),
 * faollashtirishda har doim `true`. Klient bayroqni taxmin qilmaydi — u
 * har javobda o'qiladi.
 */
export const marketCreateResponseSchema = z.object({
  id: z.uuid(),
  name: z.string(),
  is_active: z.boolean(),
});
export type MarketCreateResponse = z.infer<typeof marketCreateResponseSchema>;

/**
 * Faollashtirishni to'sib turgan bitta sabab (UI-SPEC §6.6).
 *
 * `step` aynan shu javobni "xato" emas, YO'L KO'RSATKICHI qiladi: UI
 * foydalanuvchini to'g'ridan-to'g'ri chala qadamga olib boradi.
 *
 * `code` — `wizard.blocking.<code>` tarjima kalitining kaliti. `detail`
 * esa XOM sanoq (masalan `"3/5"`) va u KO'RSATILMAYDI: matn tarjimadan
 * keladi, aks holda ekranda tarjimasiz texnik satr paydo bo'lardi.
 */
export const blockingItemSchema = z.object({
  step: z.number().int().min(1),
  code: z.string(),
  detail: z.string(),
});
export type BlockingItem = z.infer<typeof blockingItemSchema>;

/**
 * `GET /markets/{id}/setup-status` — ustaning to'liqlik holati.
 *
 * SANOQLAR XOM: UI ularni "3/5 toifada tarif bor" shaklida ko'rsatadi.
 * `can_activate` esa SERVER qarori va klient uni sanoqlardan QAYTA
 * HISOBLAMAYDI — aks holda to'liqlik qoidasi ikki joyda yashab, bir kun
 * `activate` darvozasi bilan ajralib ketardi.
 *
 * `calendar_configured` — `bool`, sanoq emas: haftalik jadval BOR yoki
 * YO'Q, "yarim sozlangan" holati yo'q.
 *
 * Bozor tanlash ekrani shu javobdan FAQAT `blocking[].step` ni oladi
 * (§6.4) — qolgan maydonlar ustaning o'zi uchun.
 */
export const setupStatusResponseSchema = z.object({
  zones: z.number().int(),
  categories: z.number().int(),
  tariffs_covered: z.number().int(),
  categories_total: z.number().int(),
  stalls: z.number().int(),
  stalls_with_category: z.number().int(),
  vendors: z.number().int(),
  calendar_configured: z.boolean(),
  cameras: z.number().int(),
  can_activate: z.boolean(),
  blocking: z.array(blockingItemSchema),
});
export type SetupStatusResponse = z.infer<typeof setupStatusResponseSchema>;

/**
 * `POST /markets/{id}/activate` ning 409 `market_incomplete` javobi.
 *
 * `blocking` AYNAN `setup-status` dagi bilan bir xil shaklda keladi (02-11
 * uni test bilan qulflagan) va UI uni AYNI ro'yxat komponentiga uzatadi:
 * chala bozor XATO emas, yo'l ko'rsatkichi (UI-SPEC §6.6). Shuning uchun bu
 * yerda alohida "xato" tipi yo'q — faqat to'siqlarning yangi nusxasi.
 *
 * ⚠ `market_is_active` (boshqa 409) bu shaklga TUSHMAYDI: unda `blocking`
 * yo'q va u hech qanday qadamga yo'l ko'rsatmaydi. `safeParse` uni rad
 * etadi va chaqiruvchi odatdagi xato matniga tushadi.
 */
export const marketIncompleteSchema = z.object({
  detail: z.string(),
  blocking: z.array(blockingItemSchema),
});
export type MarketIncomplete = z.infer<typeof marketIncompleteSchema>;

/* --- Excel import (D-13/D-14/D-15) --------------------------------------- */

/**
 * `POST /imports/*` muvaffaqiyatli javobi.
 *
 * `skipped` ALOHIDA maydon: "10 qator yozildi" javobi 12 qatorli fayl uchun
 * foydalanuvchini chalg'itardi — u qolgan ikkitasi qayerga ketganini
 * bilishi kerak.
 */
export const importResultSchema = z.object({
  inserted: z.number().int(),
  skipped: z.number().int(),
});
export type ImportResult = z.infer<typeof importResultSchema>;

/**
 * Bitta qatordagi validatsiya xatosi.
 *
 * `row` — FAYLDAGI qator raqami (sarlavha bilan birga), ya'ni foydalanuvchi
 * jadvalda o'sha raqamga to'g'ridan-to'g'ri o'ta oladi. `code` —
 * `import.errors.<code>` tarjima kalitining kaliti; `message` esa
 * SERVERNING tayyor matni va u faqat xatolar hisobotiga (xlsx) tushadi.
 */
export const importErrorItemSchema = z.object({
  row: z.number().int(),
  code: z.string(),
  message: z.string(),
});
export type ImportErrorItem = z.infer<typeof importErrorItemSchema>;

/**
 * `POST /imports/*` ning 422 javobi — D-14: validatsiya YOZISHDAN OLDIN,
 * ya'ni bu javob kelgan bo'lsa bazaga HECH NARSA yozilmagan.
 *
 * `error_counts` — `{kod: soni}`. 500 qatorli faylda 480 ta bir xil xato
 * bo'lishi mumkin va ularning hammasini ro'yxatda ko'rsatish ekranni
 * foydasiz qilardi; sanoq esa "asosiy muammo nima" savoliga bitta qatorda
 * javob beradi (`errors` — cheklangan namuna).
 */
export const importErrorResponseSchema = z.object({
  detail: z.string(),
  errors: z.array(importErrorItemSchema),
  error_counts: z.record(z.string(), z.number().int()),
});
export type ImportErrorResponse = z.infer<typeof importErrorResponseSchema>;

/**
 * Yaratilgan bitta hisob va uning BIR MARTALIK paroli (MARKET-07, D-02).
 *
 * ⚠ BU SHAKL ALOHIDA VA U `importResultSchema` GA QO'SHILMAYDI. `staff`
 * javobi maxfiy (`Cache-Control: no-store`, keshlanmaydi), `stalls` va
 * `vendors` javoblari esa emas — bitta sxemaga siqish parol maydonini
 * ularga ham "ixtiyoriy" qilib olib kirardi va bir kun kimdir uni
 * ko'rsatib qo'yardi.
 *
 * `full_name` NULLABLE: backend uni ixtiyoriy deb e'lon qilgan.
 */
export const staffCredentialSchema = z.object({
  row: z.number().int(),
  phone: z.string(),
  full_name: z.string().nullable(),
  roles: z.array(z.string()),
  temporary_password: z.string(),
});
export type StaffCredential = z.infer<typeof staffCredentialSchema>;

/** `POST /imports/staff` muvaffaqiyatli javobi (MARKET-07). */
export const staffImportResultSchema = z.object({
  inserted: z.number().int(),
  skipped: z.number().int(),
  credentials: z.array(staffCredentialSchema),
});
export type StaffImportResult = z.infer<typeof staffImportResultSchema>;

/**
 * Xato tanasi. FastAPI validatsiya xatosida (`422`) `detail` MASSIV bo'ladi,
 * shuning uchun `z.string()` emas, `z.unknown()`: shaklni `api-client`
 * yumshoq o'qiydi va noma'lum shaklda `errors.generic` ga tushadi.
 */
export const apiErrorSchema = z.object({ detail: z.unknown() });

/** 204 javoblar uchun (`logout`, `change-password`) — tana yo'q. */
export const emptyResponseSchema = z.undefined();

/**
 * Backend qaytaradigan `detail` kodlari (01-06).
 * Tarjima xaritasi shu ro'yxat ustiga quriladi; ro'yxatda yo'q kod
 * `errors.generic` ga tushadi (T-01-65 — ichki tafsilot ko'rsatilmaydi).
 *
 * ⚠ JUFTINI YANGILASHNI UNUTMANG: 2-faza qismining manbai
 * `services/core-api/app/schemas.py::MARKET_ERROR_CODES` va u QO'LDA
 * sinxron saqlanadi (til chegarasi tufayli kompilyator tekshiruvi yo'q —
 * `rbac.ts` dagi matritsa bilan aynan bir xil holat). Ko'zguda yo'q kod
 * xavfsizlik teshigi EMAS: `api-client` uni `errors.generic` ga tushiradi,
 * ya'ni foydalanuvchi umumiy xato matnini ko'radi va ANIQ SABAB yo'qoladi.
 *
 * Drift `frontend/scripts/error-codes.test.mjs` da qulflangan: u backend
 * ro'yxatini o'qib, shu massiv uni to'liq qamrashini tekshiradi.
 */
export const ERROR_CODES = [
  "invalid_credentials",
  "too_many_attempts",
  "account_blocked",
  "user_blocked",
  "market_not_selected",
  "weak_password",
  "role_not_allowed",
  "password_change_required",
  // 01-07 foydalanuvchi boshqaruvi va audit ko'rish kodlari.
  "phone_taken",
  "cannot_block_self",
  "not_found",
  "invalid_cursor",
  // --- 2-faza: zona / toifa reestrlari (02-08) ---
  "zone_name_taken",
  "zone_in_use",
  "category_name_taken",
  "category_in_use",
  // --- 2-faza: rasta reestri (02-08) ---
  "stall_code_taken",
  "stall_code_retired",
  "category_period_exists",
  "category_period_past_locked",
  // --- 2-faza: tarif (02-09) ---
  "tariff_already_set_for_date",
  "tariff_past_locked",
  "valid_from_must_be_future",
  // --- 2-faza: kalendar (02-09) ---
  "calendar_exception_exists",
  // --- 2-faza: sotuvchi va biriktirish (02-10) ---
  "vendor_phone_taken",
  "assignment_period_overlaps",
  "assignment_not_open",
  "invalid_period",
  // --- 2-faza: usta (02-11) ---
  "market_incomplete",
  "market_is_active",
  // --- 2-faza: import (02-12) ---
  "import_validation_failed",
  "file_too_large",
  "file_too_complex",
  "unsupported_file_type",
  "import_conflict",
  // --- 2-faza: xodimlar rosteri (02-24) ---
  "staff_roster_too_large",
  // --- 3-faza: NVR qurilmalari va kashfiyot (03-06) ---
  //
  // ⚠ ISAPI TAKSONOMIYASINING O'N IKKI KODI BU YERDA ATAYIN YO'Q.
  //   Ular boshqa yuzada yashaydi: `error_code` maydoni sifatida
  //   kelib, `cameras.errorCause.*` kalitlari orqali sabab + tuzatish
  //   yo'li bloki bo'lib chiziladi (UI-SPEC §7). Bu massiv esa
  //   `detail` KODLARI uchun — ya'ni to'g'ridan-to'g'ri 4xx javobi.
  //   Ikkalasini aralashtirish "ulanmadi" xatosini oddiy toast
  //   sifatida ko'rsatib, D-02 ning butun mazmunini yo'qotardi.
  "nvr_host_taken",
  "nvr_host_public_blocked",
  "nvr_address_invalid",
  "discovery_already_running",
  "nvr_not_found",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];
