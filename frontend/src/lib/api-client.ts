"use client";

import "client-only";

import type { z } from "zod";

import type { SessionResponse } from "@/lib/api-types";
import {
  apiErrorSchema,
  meResponseSchema,
  sessionResponseSchema,
} from "@/lib/api-types";
import type { Principal } from "@/lib/auth-store";
import {
  applySession,
  clearSession,
  readSession,
  setSession,
} from "@/lib/auth-store";

/**
 * core-api bilan gaplashadigan yagona yo'l.
 *
 * Bitta domen topologiyasi (nginx, 01-01) tufayli bazaviy yo'l NISBIY:
 * frontend va API bir xil origin ostida, ya'ni `SameSite=Lax` refresh
 * cookie'si oddiy `fetch` bilan yuboriladi va CSRF yuzasi kengaymaydi
 * (T-01-61). Boshqa origin kerak bo'lsa `NEXT_PUBLIC_API_BASE_URL` bilan
 * o'zgartiriladi — u holda cookie siyosati qayta ko'rib chiqilishi SHART.
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api/v1";

/** Refresh endpointi — 401 javobda AVTOMATIK chaqiriladi (`/api/v1/auth/refresh`). */
const REFRESH_PATH = "/auth/refresh";

/**
 * Backend xatosi. `detail` — mashina o'qiydigan kod (`invalid_credentials`,
 * `too_many_attempts`, ...); UI uni tarjima kalitiga xaritalaydi va HECH
 * QACHON xom holda ko'rsatmaydi (T-01-65).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`api_error_${status}_${detail || "unknown"}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Tarmoq uzilishi / CORS — javob umuman kelmadi. */
export class NetworkError extends Error {
  constructor(cause?: unknown) {
    super("network_error");
    this.name = "NetworkError";
    this.cause = cause;
  }
}

export type ApiFetchOptions<T> = {
  schema: z.ZodType<T>;
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  /** Bearer qo'shilmaydi va 401 da refresh qilinmaydi (login, refresh). */
  skipAuth?: boolean;
  signal?: AbortSignal;
};

function buildUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

/**
 * Xato tanasidan `detail` kodini ajratadi.
 *
 * FastAPI 422 da `detail` MASSIV bo'ladi, 500 da esa tana umuman JSON
 * bo'lmasligi mumkin. Ikkala holatda ham bo'sh satr qaytariladi va UI
 * `errors.generic` ga tushadi — ichki tafsilot foydalanuvchiga chiqmaydi.
 */
async function readErrorDetail(response: Response): Promise<string> {
  try {
    const parsed = apiErrorSchema.safeParse(await response.json());
    if (parsed.success && typeof parsed.data.detail === "string") {
      return parsed.data.detail;
    }
  } catch {
    // JSON emas — kod bo'sh qoladi.
  }
  return "";
}

async function readBody<T>(
  response: Response,
  schema: z.ZodType<T>,
): Promise<T> {
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return schema.parse(undefined);
  }
  return schema.parse(await response.json());
}

/*
 * Single-flight refresh (T-01-67).
 *
 * Sahifada bir vaqtda bir nechta so'rov ketadi va token muddati tugaganda
 * ULARNING HAMMASI 401 oladi. Navbatsiz har biri alohida `/auth/refresh`
 * chaqirardi — bu esa refresh token ROTATSIYASI tufayli o'z-o'zini o'ldirar
 * edi: birinchisi tokenni aylantiradi, qolganlari eski `jti` bilan kelib
 * "o'g'irlik" signalini qo'zg'atadi va butun oila bekor qilinadi.
 * Shuning uchun bir vaqtda FAQAT BITTA refresh bo'ladi, qolganlari o'sha
 * promise'ni kutadi.
 */
let refreshInFlight: Promise<SessionResponse | null> | null = null;

async function performRefresh(): Promise<SessionResponse | null> {
  try {
    const response = await fetch(buildUrl(REFRESH_PATH), {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    });

    if (!response.ok) {
      clearSession();
      return null;
    }

    const session = sessionResponseSchema.parse(await response.json());
    applySession({
      accessToken: session.access_token,
      roles: session.roles,
      market: session.market,
    });
    return session;
  } catch {
    clearSession();
    return null;
  }
}

/**
 * Sessiyani refresh cookie orqali uzaytiradi. Bitta navbatda ishlaydi.
 * `null` qaytarsa — sessiya o'lgan, chaqiruvchi login'ga yo'naltiradi.
 */
export function refreshSession(): Promise<SessionResponse | null> {
  refreshInFlight ??= performRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

/**
 * Tiplangan `fetch` o'rami.
 *
 * - `credentials: 'include'` — refresh cookie'ning yuborilishi uchun MAJBURIY.
 * - Bearer token XOTIRA store'idan olinadi (brauzer omboridan emas).
 * - 401 javobda BIR MARTA refresh qilib, asl so'rov qayta yuboriladi.
 *   Ikkinchi 401 — sessiya o'lgan, `ApiError` tashlanadi va store tozalanadi.
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions<T>,
): Promise<T> {
  const { schema, method = "GET", body, skipAuth = false, signal } = options;

  const send = async (token: string | null): Promise<Response> => {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      return await fetch(buildUrl(path), {
        method,
        headers,
        credentials: "include",
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (cause) {
      throw new NetworkError(cause);
    }
  };

  let response = await send(skipAuth ? null : readSession().accessToken);

  if (response.status === 401 && !skipAuth) {
    const session = await refreshSession();
    if (session) {
      response = await send(session.access_token);
    }
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (response.status === 401 && !skipAuth) clearSession();
    throw new ApiError(response.status, detail);
  }

  return readBody(response, schema);
}

/* ---------------------------------------------------------------------------
 * Sessiya oqimi
 * ------------------------------------------------------------------------- */

/**
 * `GET /api/v1/me` -> `Principal`.
 *
 * Bozor NOMI bu javobda yo'q (u faqat `id` beradi), shuning uchun nom
 * chaqiruvchidan (`login` yoki `refresh` javobidan) uzatiladi — D-16
 * bo'yicha u tarjima qilinmaydi va qanday kiritilgan bo'lsa shunday ko'rinadi.
 */
export async function loadPrincipal(
  marketName: string | null,
): Promise<Principal> {
  const me = await apiFetch("/me", { schema: meResponseSchema });
  return {
    userId: me.id,
    phone: me.phone,
    fullName: me.full_name,
    roles: me.roles,
    marketId: me.market_id,
    marketName,
    isPlatformAdmin: me.is_platform_admin,
    locale: me.locale,
    mustChangePassword: me.must_change_password,
  };
}

/**
 * Sahifa yangilangandan keyin sessiyani tiklaydi (D-03 — kassir telefonida
 * qayta login so'ralmaydi).
 *
 * Ikki qadam MAJBURIY: `/auth/refresh` yangi access token beradi, lekin uning
 * javobida na `locale`, na `must_change_password` bor. Ular `/api/v1/me` dan
 * keladi va ikkinchi qadam yiqilsa sessiya BEKOR qilinadi (fail-closed):
 * `must_change_password` ni "false" deb taxmin qilish majburiy parol
 * almashtirishni chetlab o'tish yo'lini ochib berardi (T-01-64).
 */
export async function restoreSession(): Promise<boolean> {
  const session = await refreshSession();
  if (!session) return false;

  try {
    const principal = await loadPrincipal(session.market.name);
    setSession({
      accessToken: session.access_token,
      principal,
      markets: readSession().markets,
    });
    return true;
  } catch {
    clearSession();
    return false;
  }
}

/**
 * Xatoni tarjima kalitiga xaritalaydi.
 *
 * Faqat MA'LUM kodlar xaritalanadi; qolgani `errors.generic` ga tushadi —
 * server tafsiloti (stack, SQL, ichki nom) foydalanuvchiga hech qachon
 * ko'rsatilmaydi (T-01-65).
 *
 * DIQQAT: bu xarita LOGIN sahifasida ishlatilmaydi. U yerda `account_blocked`
 * kabi kodlarni ko'rsatish "bu raqam mavjud" degan signal bo'lardi (T-01-63),
 * shuning uchun login formasining o'z, torroq xaritasi bor.
 */
export type ErrorMessageKey =
  | "errors.generic"
  | "errors.network"
  | "errors.forbidden"
  | "errors.notFound"
  | "auth.invalidCredentials"
  | "auth.tooManyAttempts"
  | "auth.accountBlocked"
  | "auth.passwordTooShort";

export function errorMessageKey(error: unknown): ErrorMessageKey {
  if (error instanceof NetworkError) return "errors.network";

  if (error instanceof ApiError) {
    switch (error.detail) {
      case "invalid_credentials":
        return "auth.invalidCredentials";
      case "too_many_attempts":
        return "auth.tooManyAttempts";
      case "account_blocked":
      case "user_blocked":
        return "auth.accountBlocked";
      case "weak_password":
        return "auth.passwordTooShort";
      case "role_not_allowed":
        return "errors.forbidden";
      default:
        break;
    }
    if (error.status === 403) return "errors.forbidden";
    if (error.status === 404) return "errors.notFound";
  }

  return "errors.generic";
}
