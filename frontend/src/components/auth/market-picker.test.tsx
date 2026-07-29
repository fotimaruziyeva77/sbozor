/**
 * MarketPicker — 1-fazadagi BIRINCHI React render testi (01-12, CR-02).
 *
 * NEGA AYNAN SHU KOMPONENT: bu yerda "tugma abadiy `disabled`" xatosi
 * yashiringan edi va u typecheck'dan ham, lint'dan ham, mavjud 37 ta sof
 * funksiya testidan ham BEMALOL o'tgan. Bunday xatoni faqat komponentni
 * HAQIQATAN render qilib, tugmaning holatini o'qib ushlash mumkin.
 *
 * Test qulflaydigan xulq:
 *   1. `markets` to'la bo'lsa (asosiy yo'l) tugmalar BOSILADI — bu CR-02 ning
 *      to'g'ridan-to'g'ri regressiya qulfi.
 *   2. Tugma bosilganda `POST /auth/select-market` aynan tanlangan `market_id`
 *      bilan ketadi.
 *   3. So'rov ketayotganda tugmalar bloklanadi — ya'ni tuzatish `disabled`
 *      mantiqini shunchaki O'CHIRIB tashlamagan, uni TO'G'RILAGAN.
 *
 * DIQQAT: bosish `fireEvent` bilan qilinadi, `@testing-library/user-event`
 * bilan EMAS — oxirgisi 01-12 da tasdiqlangan olti paket ro'yxatiga kirmaydi
 * va faqat shu test uchun yangi bog'liqlik qo'shish mutanosib emas.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { MarketPicker } from "@/components/auth/market-picker";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

/*
 * `useRouter` Next.js router kontekstini talab qiladi — u jsdom'da yo'q,
 * shuning uchun navigatsiya mock bilan almashtiriladi. Mock `vi.mock`
 * ko'tarilishidan (hoisting) OLDIN mavjud bo'lishi kerak, shuning uchun
 * `vi.hoisted`.
 */
const routerMock = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
}));

/*
 * Faqat `apiFetch` mock qilinadi; `errorMessageKey` ASL holida qoladi, ya'ni
 * xato -> tarjima kaliti xaritasi ham haqiqiy kod bilan ishlaydi.
 */
const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

const { apiFetch } = apiClientMock;

const KARMANA = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Karmana markaziy bozori",
};
const NAVOIY = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "Navoiy dehqon bozori",
};

function renderPicker(): ReturnType<typeof render> {
  // `retry: false` — xato holatida test 3 marta qayta urinishni kutmasligi uchun.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MarketPicker />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}

/** Login javobi bozorlarni to'ldirgan holat — D-06 ning ASOSIY yo'li. */
function seedSessionWithMarkets(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Foydalanuvchi",
      roles: [],
      marketId: null,
      marketName: null,
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [KARMANA, NAVOIY],
  });
}

beforeEach(() => {
  clearSession();
  // Chaqiruv tarixi VA implementatsiyani tozalaydi — har test o'z javobini
  // o'zi o'rnatadi va oldingi testning chaqiruvlari sanoqqa qo'shilmaydi.
  vi.resetAllMocks();
});

afterEach(() => {
  clearSession();
});

describe("MarketPicker — bozor tanlash (D-06)", () => {
  test("markets to'la bo'lsa tugmalar BOSILADI (CR-02 regressiya qulfi)", () => {
    seedSessionWithMarkets();
    renderPicker();

    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);

    /*
     * ANIQ SABAB: `enabled: markets.length === 0` -> so'rov O'CHIQ ->
     * `marketsQuery.isPending` ABADIY true. Agar `isBusy` yana `isPending`
     * ga qaytarilsa, quyidagi assertlar qizaradi.
     */
    for (const button of buttons) {
      expect(button).not.toBeDisabled();
    }

    expect(
      screen.getByRole("button", { name: KARMANA.name }),
    ).not.toBeDisabled();
    expect(screen.getByRole("button", { name: NAVOIY.name })).not.toBeDisabled();

    // Ro'yxat to'la bo'lgani uchun `GET /markets` UMUMAN chaqirilmaydi.
    expect(apiFetch).not.toHaveBeenCalled();
  });

  test("tugma bosilganda tanlangan bozor `market_id` bilan yuboriladi", async () => {
    seedSessionWithMarkets();
    apiFetch.mockResolvedValue({
      access_token: "new-token",
      token_type: "bearer",
      expires_in: 900,
      roles: ["market_admin"],
      market: NAVOIY,
    });

    renderPicker();

    fireEvent.click(screen.getByRole("button", { name: NAVOIY.name }));

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledTimes(1);
    });

    const [path, options] = apiFetch.mock.calls[0] as [
      string,
      { method: string; body: { market_id: string } },
    ];
    expect(path).toBe("/auth/select-market");
    expect(options.method).toBe("POST");
    expect(options.body).toEqual({ market_id: NAVOIY.id });

    // Muvaffaqiyatdan keyin panelga o'tiladi.
    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/dashboard");
    });
  });

  test("so'rov ketayotganda tugmalar bloklanadi (ikki marta yuborilmaydi)", async () => {
    seedSessionWithMarkets();
    // Hech qachon yakunlanmaydigan promise — mutatsiya `isPending` da qoladi.
    apiFetch.mockReturnValue(new Promise(() => {}));

    renderPicker();

    fireEvent.click(screen.getByRole("button", { name: KARMANA.name }));

    await waitFor(() => {
      for (const button of screen.getAllByRole("button")) {
        expect(button).toBeDisabled();
      }
    });

    expect(apiFetch).toHaveBeenCalledTimes(1);
  });
});
