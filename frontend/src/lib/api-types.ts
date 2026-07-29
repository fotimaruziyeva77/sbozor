import { z } from "zod";

import { ROLES, type Role } from "@/lib/rbac";

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

/** Bozor havolasi — auth javoblarida faqat `id` va nom keladi. */
export const marketRefSchema = z.object({
  id: z.uuid(),
  name: z.string(),
});
export type MarketSummary = z.infer<typeof marketRefSchema>;

/** `GET /api/v1/markets` elementi (01-07) — `marketRefSchema` ning kengaytmasi. */
export const marketListItemSchema = marketRefSchema.extend({
  timezone: z.string(),
  is_active: z.boolean(),
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
 * Yaratish formasida ko'rsatiladigan rollar (D-04 darajasi bo'yicha).
 *
 * Platforma admini — beshala rol; qolgan hamma (jumladan bozor admini) —
 * faqat `MARKET_ADMIN_ASSIGNABLE_ROLES`. Ro'yxat SHU YERDA quriladi, ya'ni
 * komponentda qattiq yozilgan rol nomlari bo'lmaydi va D-04 ni o'zgartirish
 * bitta joyni tahrirlash bilan cheklanadi.
 */
export function assignableRoles(isPlatformAdmin: boolean): readonly Role[] {
  return isPlatformAdmin ? ROLES : MARKET_ADMIN_ASSIGNABLE_ROLES;
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
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];
