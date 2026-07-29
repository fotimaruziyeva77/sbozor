"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch, errorMessageKey } from "@/lib/api-client";
import type { ErrorMessageKey } from "@/lib/api-client";
import type { ApiLocale } from "@/lib/api-types";
import {
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
