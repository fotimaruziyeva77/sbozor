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

/** React Query kaliti — barcha mutatsiyalar shu kalitni invalidatsiya qiladi. */
export const USERS_QUERY_KEY = ["users"] as const;

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
  return useQuery({
    queryKey: USERS_QUERY_KEY,
    queryFn: () => apiFetch(USERS_PATH, { schema: userListResponseSchema }),
    enabled: options?.enabled ?? true,
  });
}

/**
 * Foydalanuvchi yaratish (D-04) — javobda bir martalik vaqtinchalik parol.
 *
 * `full_name` bo'sh bo'lsa `null` yuboriladi: backend uni ixtiyoriy deb
 * e'lon qilgan va bo'sh satr "ismi bor, lekin u bo'sh" degan ma'noni
 * bazaga yozib qo'yardi.
 */
export function useCreateUser() {
  const queryClient = useQueryClient();

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
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
    },
  });
}

/** Bloklash — DARHOL kuchga kiradi (D-08). Javob 204, tanasi yo'q. */
export function useBlockUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/block`, {
        method: "POST",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
    },
  });
}

/** Blokdan chiqarish (D-08). */
export function useUnblockUser() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/unblock`, {
        method: "POST",
        schema: emptyResponseSchema,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
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
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      apiFetch(`${USERS_PATH}/${userId}/reset-password`, {
        method: "POST",
        schema: resetPasswordResponseSchema,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
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
  | "users.cannotBlockSelf";

/**
 * `ApiError.detail` -> tarjima kaliti.
 *
 * Uchta kod umumiy `errorMessageKey()` dan ANIQROQ xabar talab qiladi:
 *   `phone_taken`      — "bu raqam band" (409, forma maydoniga tegishli)
 *   `role_not_allowed` — D-04 darvozasi (403; umumiy xarita buni faqat
 *                        "ruxsat yo'q" deb ko'rsatardi va admin nima
 *                        noto'g'ri ekanini bilmasdi)
 *   `cannot_block_self`— o'zini bloklash rad etildi (400)
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
      default:
        break;
    }
  }
  return errorMessageKey(error);
}
