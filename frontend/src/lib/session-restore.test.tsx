/**
 * SESSIYA TIKLASH — BOZOR HOLATI YO'QOLMAYDI (260820).
 *
 * =============================================================================
 * ⛔⛔ BU TEST JONLI NUQSONDAN TUG'ILGAN.
 *
 *   `loadPrincipal()` Principal ni `/me` javobidan quradi va
 *   `restoreSession()` uni `setSession()` bilan YOZADI — ya'ni
 *   `applySession()` qo'ygan qiymatlarni ustidan yozadi. Unga faqat
 *   bozor NOMI uzatilardi, `is_active` esa jimgina tushib qolardi.
 *
 *   Natija ekranda ko'rindi: sahifa YANGILANGANDAN keyin platforma
 *   adminining bosh ekranida bozor holati «Qoralama» emas, «—» bo'lib
 *   qolar va «Faollashtirish» havolasi UMUMAN yo'qolardi. Havola
 *   ataylab `isActive === false` da chiziladi (`!isActive` da emas —
 *   u noma'lum holatni ham qamrab olardi), shuning uchun `undefined`
 *   uni o'chiradi.
 *
 *   Ya'ni platforma adminining ASOSIY amali bir yangilanishdan keyin
 *   g'oyib bo'lardi. Kod diff'ida bu ko'rinmasdi: `loadPrincipal`
 *   mutlaqo to'g'ri o'qilardi.
 * =============================================================================
 */
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const fetchMock = vi.hoisted(() => vi.fn());

vi.stubGlobal("fetch", fetchMock);

import { loadPrincipal, restoreSession } from "@/lib/api-client";
import { clearSession, readSession } from "@/lib/auth-store";

const ME = {
  id: "33333333-3333-4333-8333-333333333333",
  phone: "+998901112233",
  full_name: "Bosh Admin",
  roles: ["platform_admin"],
  market_id: "11111111-1111-4111-8111-111111111111",
  is_platform_admin: true,
  locale: "uz-Latn",
  must_change_password: false,
};

/** `/auth/refresh` javobi — `market.is_active` SHU YERDA keladi. */
function refreshBody(isActive: boolean) {
  return {
    access_token: "test-access-token",
    token_type: "bearer",
    expires_in: 900,
    roles: ["platform_admin"],
    market: {
      id: ME.market_id,
      name: "Nurota sinov bozori",
      is_active: isActive,
    },
  };
}

function jsonResponse(body: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    headers: new Headers({ "content-type": "application/json" }),
  };
}

beforeEach(() => {
  fetchMock.mockReset();
  clearSession();
});

afterEach(() => {
  clearSession();
});

describe("loadPrincipal", () => {
  test("bozor holatini SAQLAYDI — qoralama `false` bo'lib qoladi", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(ME));

    const principal = await loadPrincipal({
      name: "Nurota sinov bozori",
      isActive: false,
    });

    expect(principal.marketName).toBe("Nurota sinov bozori");
    /*
     * ⛔ `false` — `undefined` EMAS. Farq hal qiluvchi: «Faollashtirish»
     *    havolasi `isActive === false` da chiziladi.
     */
    expect(principal.marketIsActive).toBe(false);
  });

  test("faol bozorda `true` bo'lib qoladi", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(ME));

    const principal = await loadPrincipal({
      name: "Karmana test bozori",
      isActive: true,
    });

    expect(principal.marketIsActive).toBe(true);
  });

  test("bozor tanlanmagan sessiyada nom ham, holat ham yo'q", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(ME));

    const principal = await loadPrincipal(null);

    expect(principal.marketName).toBeNull();
    expect(principal.marketIsActive).toBeUndefined();
  });
});

describe("restoreSession", () => {
  test("sahifa yangilangandan keyin QORALAMA holati saqlanadi", async () => {
    /* 1) `/auth/refresh` 2) `/me` */
    fetchMock
      .mockResolvedValueOnce(jsonResponse(refreshBody(false)))
      .mockResolvedValueOnce(jsonResponse(ME));

    const ok = await restoreSession();

    expect(ok).toBe(true);
    expect(readSession().principal?.marketIsActive).toBe(false);
  });

  test("faol bozor ham saqlanadi", async () => {
    fetchMock
      .mockResolvedValueOnce(jsonResponse(refreshBody(true)))
      .mockResolvedValueOnce(jsonResponse(ME));

    await restoreSession();

    expect(readSession().principal?.marketIsActive).toBe(true);
  });
});
