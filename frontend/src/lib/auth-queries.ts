"use client";

import { useMutation } from "@tanstack/react-query";
import type { UseMutationOptions } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api-client";
import type { SessionResponse } from "@/lib/api-types";
import { emptyResponseSchema, sessionResponseSchema } from "@/lib/api-types";

/*
 * =============================================================================
 * Sessiya BOOTSTRAP oqimining server holati (01-06 kontrakti).
 *
 * `market-queries.ts` dan ATAYIN ajratilgan: bu ikki endpoint bozor
 * DOMENIGA tegishli emas — ular tenant kontekstidan TASHQARIDA ishlaydi
 * (`select-market` uni O'RNATADI, `logout` esa BUZADI). Ularni domen
 * moduliga qo'shish "har endpoint bitta joyda" qoidasini "hamma narsa
 * bitta faylda" ga aylantirardi.
 *
 * Modulning MAVJUDLIK SABABI esa o'sha qoidaning o'zi: bu chaqiruvlar
 * ilgari komponent ichida turardi va 2-fazadan boshlab komponentlar HTTP
 * qatlamiga umuman tegmaydi (darvoza: `frontend/scripts/no-direct-fetch.test.mjs`).
 * =============================================================================
 */

export const SELECT_MARKET_PATH = "/auth/select-market";
export const LOGOUT_PATH = "/auth/logout";

/**
 * Bozorni tanlaydi va yangi access token oladi (D-06).
 *
 * Marshrut qarori chaqiruvchida qoladi (`options.onSuccess`): u SERVER
 * javobidagi `market.is_active` ga qarab hal qilinadi, bosilgan ro'yxat
 * elementiga emas — ro'yxat login paytida olingan va eskirgan bo'lishi
 * mumkin.
 */
export function useSelectMarket(
  options?: Omit<
    UseMutationOptions<SessionResponse, unknown, string>,
    "mutationFn"
  >,
) {
  return useMutation({
    mutationFn: (marketId: string) =>
      apiFetch(SELECT_MARKET_PATH, {
        method: "POST",
        body: { market_id: marketId },
        schema: sessionResponseSchema,
      }),
    ...options,
  });
}

/**
 * Sessiyani yopadi.
 *
 * Tozalash `onSettled` da bo'lishi SHART (chaqiruvchida): server javobi
 * kelmasa ham brauzerda o'lik token qolib ketmasligi kerak.
 */
export function useLogout(
  options?: Omit<
    UseMutationOptions<undefined, unknown, void>,
    "mutationFn"
  >,
) {
  return useMutation({
    mutationFn: () =>
      apiFetch(LOGOUT_PATH, { method: "POST", schema: emptyResponseSchema }),
    ...options,
  });
}
