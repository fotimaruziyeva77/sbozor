"use client";

import "client-only";

import type { z } from "zod";

import { apiErrorSchema, sessionResponseSchema } from "@/lib/api-types";
import { applySession, clearSession, readSession } from "@/lib/auth-store";

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
let refreshInFlight: Promise<string | null> | null = null;

async function performRefresh(): Promise<string | null> {
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
    return session.access_token;
  } catch {
    clearSession();
    return null;
  }
}

/**
 * Sessiyani refresh cookie orqali tiklaydi. Bitta navbatda ishlaydi.
 * `null` qaytarsa — sessiya o'lgan, chaqiruvchi login'ga yo'naltiradi.
 */
export function refreshSession(): Promise<string | null> {
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
    const token = await refreshSession();
    if (token) {
      response = await send(token);
    }
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    if (response.status === 401 && !skipAuth) clearSession();
    throw new ApiError(response.status, detail);
  }

  return readBody(response, schema);
}
