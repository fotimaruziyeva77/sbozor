"use client";

import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ApiError, apiFetch, errorMessageKey } from "@/lib/api-client";
import type { ErrorMessageKey } from "@/lib/api-client";
import type { ApiLocale } from "@/lib/api-types";
import {
  auditListResponseSchema,
  createUserResponseSchema,
  emptyResponseSchema,
  resetPasswordResponseSchema,
  userListResponseSchema,
} from "@/lib/api-types";
import { useAuthStore } from "@/lib/auth-store";
import { domainKey } from "@/lib/market-queries";

/*
 * =============================================================================
 * Ma'muriy ekranlarning server holati (01-07 kontrakti).
 *
 * Har bir endpoint FAQAT shu yerda chaqiriladi: komponent `apiFetch` ni
 * to'g'ridan-to'g'ri ishlatmaydi. Sabab — invalidatsiya. Bloklash yoki
 * parol tiklashdan keyin ro'yxat eskiradi va uni yangilashni komponentga
 * qoldirish "bir joyda esdan chiqadi" sinfidagi xatoni kafolatlaydi:
 * admin bloklagan foydalanuvchini ekranda hamon "faol" ko'rib turadi.
 * =============================================================================
 */

/** `/api/v1/users` — to'liq yo'l `API_BASE_URL` bilan quriladi. */
export const USERS_PATH = "/users";

/**
 * React Query kaliti — ⛔ BOZORGA DOIRALANGAN (WR-09).
 *
 * =============================================================================
 * ⛔⛔ NEGA GLOBAL `["users"]` OLIB TASHLANDI.
 *
 * `market-queries.ts` ning `domainKey` docstringi qoidani ochiq yozgan:
 * «HAR BIR domen kaliti `["m", marketId, ...]` bilan boshlanadi va ISTISNO
 * YO'Q». Xodimlar ro'yxati esa AYNAN shu istisno bo'lib qolgan edi va u
 * ikkita mustaqil zarar berardi:
 *
 *   1. ⛔ TENANT SIZIB CHIQISHI: bozor almashtirilganda `staleTime` (30 s)
 *      ichida oldingi bozorning xodimlari HECH QANDAY SO'ROVSIZ qayta
 *      chizilardi — va `useAssigneeLabels` orqali audit izidagi aktor
 *      ⛔ BEGONA BOZOR xodimining nomi bilan yorliqlanardi.
 *   2. ⛔ TOZALASH YETIB BORMASDI: `domainKey(marketId)` prefiksi bo'yicha
 *      bekor qilish global kalitni ⛔ UMUMAN ko'rmasdi.
 *
 * ⛔ `domainKey` `market-queries.ts` DAN IMPORT QILINADI, ikkinchi nusxa
 *    yozilmaydi: ikki fabrika bir muddat bir xil shakl berib, keyin
 *    JIMGINA ajralib ketardi.
 *
 * ⚠ ISTE'MOLCHILAR UCHUN BU O'ZGARISH KO'RINMAS: oltala chaqiruvchi
 *   (`audit-filters`, `audit-list`, `charge-detail-dialog`, `variance-list`,
 *   `user-list`, `vendor-labels`) hookni ARGUMENTSIZ chaqiradi va kalitni
 *   bilmaydi. Shuning uchun bozor `useMarketId()` dan SHU YERDA o'qiladi,
 *   chaqiruvchidan talab qilinmaydi.
 * =============================================================================
 */
export const usersKey = (marketId: string) => domainKey(marketId, "users");

/**
 * Joriy bozor — kalit qurish uchun YAGONA manba (eksport QILINMAYDI).
 *
 * ⚠ Nusxa `reconciliation-queries.ts`, `camera-queries.ts` va boshqa
 *   modullardagi bilan AYNI: har modul o'z bozorini o'zi o'qiydi va
 *   umumiy hook `auth-store` ga qo'shimcha bog'liqlik tugunini
 *   tug'dirmaydi (mavjud konvensiya).
 */
function useMarketId(): string | null {
  const { principal } = useAuthStore();
  return principal?.marketId ?? null;
}

export type CreateUserInput = {
  phone: string;
  fullName: string | null;
  roles: readonly string[];
  locale: ApiLocale;
};

/**
 * Joriy bozor a'zolari (`USER_VIEW`).
 *
 * Ro'yxat sahifalanmaydi — bu backend kontraktining holati (01-07): Karmana
 * bozorida xodimlar soni o'nlab. Ko'p bozorli platformada bu audit
 * ro'yxatidagi kursor mexanizmiga o'tkaziladi.
 */
export function useUsersQuery(options?: { enabled?: boolean }) {
  const marketId = useMarketId();

  return useQuery({
    queryKey: usersKey(marketId ?? ""),
    /*
     * ⛔ `marketId !== null` — SHART, «har ehtimolga qarshi» EMAS: bozorsiz
     *   sessiyada so'rov `["m", "", "users"]` kalitiga yozilardi va o'sha
     *   yozuv keyingi bozorlarning HECH BIRIGA tegishli bo'lmagan holda
     *   keshda yashab qolardi.
     */
    enabled: marketId !== null && (options?.enabled ?? true),
    queryFn: () => apiFetch(USERS_PATH, { schema: userListResponseSchema }),
  });
}

/**
 * Mutatsiyalardan keyin xodimlar ro'yxatini bekor qiladi.
 *
 * ⛔ TO'RT MUTATSIYA UCHUN BITTA JOY: kalit fabrikasi va bozorni o'qish
 *    to'rt marta takrorlansa, ulardan bittasi kelajakda ortda qolardi va
 *    admin bloklagan foydalanuvchini ekranda hamon «faol» ko'rib turardi —
 *    faylning O'Z docstringi aynan shu sinfdagi xatoni sabab qilib
 *    ko'rsatgan.
 */
function useUsersInvalidator(): () => void {
  const queryClient = useQueryClient();
  const marketId = useMarketId();

  return () => {
    if (marketId === null) return;
    void queryClient.invalidateQueries({ queryKey: usersKey(marketId) });
  };
}

/**
 * Foydalanuvchi yaratish (D-04) — javobda bir martalik vaqtinchalik parol.
 *
 * `full_name` bo'sh bo'lsa `null` yuboriladi: backend uni ixtiyoriy deb
 * e'lon qilgan va bo'sh satr "ismi bor, lekin u bo'sh" degan ma'noni
 * bazaga yozib qo'yardi.
 */
export function useCreateUser() {
  const invalidateUsers = useUsersInvalidator();

  return useMutation({
    mutationFn: (input: CreateUserInput) =>
      apiFetch(USERS_PATH, {
        method: "POST",
        body: {
          phone: input.phone,
          full_name: input.fullName,
          roles: input.roles,
          locale: input.locale,
        },
        schema: createUserResponseSchema,
      }),
    onSuccess: () => {
      invalidateUsers();
    },
  });
}

/**
 * Mavjud a'zoning rollarini ALMASHTIRADI (Topilma №G).
 *
 * `PATCH`, `POST` EMAS: `/block` va `/reset-password` — HODISALAR,
 * rollar esa resursning MAYDONI (server tomonidagi sabab
 * `users.py::update_user_roles` docstringida).
 *
 * ⚠ TO'PLAM TO'LIQ YUBORILADI, DELTA EMAS: UI foydalanuvchiga butun
 *   to'plamni ko'rsatadi, ya'ni u ko'rgan narsa aynan yuboriladi. "Rol
 *   qo'sh"/"rolni olib tashla" shakli ikki admin bir vaqtda
 *   tahrirlaganda poyga oynasi tug'dirardi.
 *
 * ⚠ YANGI ROLLAR DARHOL KUCHGA KIRMAYDI va bu server qarori: rollar JWT
 *   da'volarida yashaydi, `/auth/refresh` esa ularni DB'dan qayta
 *   o'qiydi. Shuning uchun `usersKey` bekor qilinadi (RO'YXAT
 *   yangilanadi), lekin sessiyaga tegilmaydi — foydalanuvchiga buni
 *   `users.editRolesHint` AYTADI.
 */
export function useUpdateUserRoles() {
  const invalidateUsers = useUsersInvalidator();

  return useMutation({
    mutationFn: ({
      userId,
      roles,
    }: {
      userId: string;
      roles: readonly string[];
    }) =>
      apiFetch(`${USERS_PATH}/${userId}/roles`, {
        method: "PATCH",
        body: { roles },
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      invalidateUsers();
    },
  });
}

/** Bloklash — DARHOL kuchga kiradi (D-08). Javob 204, tanasi yo'q. */
export function useBlockUser() {
  const invalidateUsers = useUsersInvalidator();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/block`, {
        method: "POST",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      invalidateUsers();
    },
  });
}

/** Blokdan chiqarish (D-08). */
export function useUnblockUser() {
  const invalidateUsers = useUsersInvalidator();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/unblock`, {
        method: "POST",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      invalidateUsers();
    },
  });
}

/**
 * Admin orqali parol tiklash (D-02).
 *
 * Javobdagi parol ATAYIN keshga yozilmaydi (`useMutation`, `useQuery` emas):
 * kesh uni komponent almashgandan keyin ham xotirada ushlab turardi va
 * "bir marta ko'rsatiladi" kafolati jimgina yo'qolardi (T-01-68).
 */
export function useResetPassword() {
  const invalidateUsers = useUsersInvalidator();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/reset-password`, {
        method: "POST",
        schema: resetPasswordResponseSchema,
      }),
    onSuccess: () => {
      invalidateUsers();
    },
  });
}

/* ---------------------------------------------------------------------------
 * Audit ko'rish (D-11, D-12)
 * ------------------------------------------------------------------------- */

/** `/api/v1/audit`. */
export const AUDIT_PATH = "/audit";

/**
 * Bitta sahifadagi yozuvlar soni.
 *
 * Backend chegarasi 200 (`AUDIT_PAGE_SIZE_MAX`); 50 — o'qish uchun qulay
 * sahifa va "ko'proq yuklash" tugmasi qolganini kursor bilan olib keladi.
 */
export const AUDIT_PAGE_SIZE = 50;

/** Filtrlar (D-12 minimal to'plami). Bo'sh satr — "filtr qo'yilmagan". */
export type AuditFilters = {
  from: string;
  to: string;
  actorUserId: string;
  action: string;
  tableName: string;
};

export const EMPTY_AUDIT_FILTERS: AuditFilters = {
  from: "",
  to: "",
  actorUserId: "",
  action: "",
  tableName: "",
};

function buildAuditPath(filters: AuditFilters, cursor: string | null): string {
  const params = new URLSearchParams();
  // Backend nomlari `AuditQuery` dan: `from`/`to` alias, qolgani snake_case.
  if (filters.from) params.set("from", filters.from);
  if (filters.to) params.set("to", filters.to);
  if (filters.actorUserId) params.set("actor_user_id", filters.actorUserId);
  if (filters.action) params.set("action", filters.action);
  if (filters.tableName) params.set("table_name", filters.tableName);
  params.set("limit", String(AUDIT_PAGE_SIZE));
  if (cursor) params.set("cursor", cursor);
  return `${AUDIT_PATH}?${params.toString()}`;
}

/**
 * Filtrlanadigan audit ro'yxati — KURSOR bilan sahifalanadi.
 *
 * Sahifa RAQAMI ishlatilmaydi va bu backend qarori (01-07): auditni ko'rish
 * o'zi yangi `read` qatorini yozadi (D-09), ya'ni jurnal so'rovlar ORASIDA
 * o'sadi. Raqamli sahifalashda o'sha yangi qatorlar sahifalarni surib
 * yuborardi va foydalanuvchi 2-sahifada 1-sahifadagi yozuvni qayta ko'rardi.
 * `next_cursor` esa `(at, id)` juftligi ustidagi qat'iy chegara.
 *
 * `queryKey` filtrlarni to'liq o'z ichiga oladi: filtr o'zgarganda kesh
 * yangi zanjir boshlaydi va eski sahifalar aralashib ketmaydi.
 */
export function useAuditQuery(filters: AuditFilters) {
  return useInfiniteQuery({
    queryKey: ["audit", filters],
    queryFn: ({ pageParam }) =>
      apiFetch(buildAuditPath(filters, pageParam), {
        schema: auditListResponseSchema,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}

/* ---------------------------------------------------------------------------
 * Xato kodi -> tarjima kaliti
 * ------------------------------------------------------------------------- */

/** Ma'muriy ekranlarga XOS xato kalitlari (`users.*` namespace'i). */
export type AdminErrorMessageKey =
  | "users.phoneTaken"
  | "users.roleNotAllowed"
  | "users.cannotBlockSelf"
  | "users.cannotChangeOwnRoles";

/**
 * `ApiError.detail` -> tarjima kaliti.
 *
 * Uchta kod umumiy `errorMessageKey()` dan ANIQROQ xabar talab qiladi:
 *   `phone_taken`      — "bu raqam band" (409, forma maydoniga tegishli)
 *   `role_not_allowed` — D-04 darvozasi (403; umumiy xarita buni faqat
 *                        "ruxsat yo'q" deb ko'rsatardi va admin nima
 *                        noto'g'ri ekanini bilmasdi)
 *   `cannot_block_self`— o'zini bloklash rad etildi (400)
 *   `cannot_change_own_roles` — o'z rollarini tahrirlash rad etildi (400;
 *                        `cannot_block_self` bilan bir xil sinf va shu
 *                        sababdan qo'shni tarmoq)
 *
 * Qolgan hamma narsa umumiy xaritaga tushadi, ya'ni server tafsiloti
 * foydalanuvchiga hech qachon xom holda ko'rsatilmaydi (T-01-65).
 */
export function adminErrorMessageKey(
  error: unknown,
): ErrorMessageKey | AdminErrorMessageKey {
  if (error instanceof ApiError) {
    switch (error.detail) {
      case "phone_taken":
        return "users.phoneTaken";
      case "role_not_allowed":
        return "users.roleNotAllowed";
      case "cannot_block_self":
        return "users.cannotBlockSelf";
      case "cannot_change_own_roles":
        return "users.cannotChangeOwnRoles";
      default:
        break;
    }
  }
  return errorMessageKey(error);
}
