/**
 * ALOQA HOLATI — SERVER XATOSI MODEM AYBI EMAS (261004).
 *
 * =============================================================================
 * ⛔⛔ BU TEST IKKI YOLG'ON BANNERNI QO'RIQLAYDI.
 *
 *   1. SERVER XATOSI. `fetch` javob qaytargan bo'lsa, server TIRIK —
 *      status 500 bo'lsa ham. Agar `response.ok` tekshirilsa, backend
 *      xatosi «internet yo'q» bo'lib ko'rinardi va bozordagi operator
 *      modemni, kabelni, provayderni qidirib yurardi.
 *
 *   2. BEKOR QILISH. `AbortError` ham `fetch` ning `catch` iga tushadi,
 *      lekin u foydalanuvchi sahifadan chiqib ketgani degani. Hisoblansa,
 *      har tez navigatsiyada banner bir lahza chaqnab o'tardi.
 *
 * `navigator.onLine` bu yerda UMUMAN sinalmaydi va sabab `connectivity.ts`
 * sarlavhasida: bozor kompyuteri NVR bilan bitta LAN da va modem internetni
 * yo'qotsa ham brauzer «ulangan» deb turadi.
 * =============================================================================
 */
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const fetchMock = vi.hoisted(() => vi.fn());

vi.stubGlobal("fetch", fetchMock);

import { apiRequest } from "@/lib/api-client";
import { clearSession } from "@/lib/auth-store";
import {
  isAbortError,
  isUnreachable,
  resetConnectivity,
} from "@/lib/connectivity";

/** `fetch` javobi — tanasi muhim emas, faqat STATUS o'lchanadi. */
function javob(status: number): Response {
  return new Response(JSON.stringify({ detail: "x" }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function abortXatosi(): Error {
  const e = new Error("aborted");
  e.name = "AbortError";
  return e;
}

beforeEach(() => {
  clearSession();
  resetConnectivity();
  fetchMock.mockReset();
});

afterEach(() => {
  clearSession();
  resetConnectivity();
});

describe("aloqa holati", () => {
  test("boshlang'ich holat: aloqa BOR deb hisoblanadi", () => {
    // ⛔ QUYI CHEGARA: usiz quyidagi testlar «doim true» bo'lgan
    //    buzuq store bilan ham yashil bo'lardi.
    expect(isUnreachable()).toBe(false);
  });

  test("`fetch` yiqilsa — aloqa YO'Q", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(apiRequest("/health", { skipAuth: true })).rejects.toThrow();

    expect(isUnreachable()).toBe(true);
  });

  test("⛔ 500 KELSA — aloqa BOR (server tirik, modem aybdor emas)", async () => {
    // Avval holatni «yo'q» ga keltiramiz, keyin server xatosi uni
    // QAYTARIB tiklashi kerak.
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));
    await expect(apiRequest("/health", { skipAuth: true })).rejects.toThrow();
    expect(isUnreachable(), "sinov sharti bajarilmadi").toBe(true);

    /*
     * ⚠ 500 `ApiError` BO'LIB tashlanadi (`api-client.ts:290`), ya'ni
     *   chaqiruv baribir yiqiladi — va bu AYNAN da'voning kuchi:
     *   so'rov muvaffaqiyatsiz, lekin u SERVER xatosi, aloqa xatosi
     *   emas. `NetworkError` bilan `ApiError` ni ajratmagan kod
     *   bannerni shu yerda chiqarib yuborardi.
     */
    fetchMock.mockResolvedValueOnce(javob(500));
    await expect(apiRequest("/health", { skipAuth: true })).rejects.toThrow(
      /500/,
    );

    expect(isUnreachable()).toBe(false);
  });

  test("⛔ BEKOR QILINGAN so'rov aloqani YO'Q deb belgilamaydi", async () => {
    fetchMock.mockRejectedValue(abortXatosi());

    await expect(apiRequest("/health", { skipAuth: true })).rejects.toThrow();

    expect(isUnreachable()).toBe(false);
  });

  test("`isAbortError` faqat AbortError ni taniydi", () => {
    expect(isAbortError(abortXatosi())).toBe(true);
    expect(isAbortError(new TypeError("Failed to fetch"))).toBe(false);
    expect(isAbortError(null)).toBe(false);
    expect(isAbortError("AbortError")).toBe(false);
  });
});
