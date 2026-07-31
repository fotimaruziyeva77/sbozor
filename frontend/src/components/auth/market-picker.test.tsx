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
import type { MarketSummary } from "@/lib/api-types";
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
  is_active: true,
};
const NAVOIY = {
  id: "22222222-2222-4222-8222-222222222222",
  name: "Navoiy dehqon bozori",
  is_active: true,
};
/** Usta yarim tashlab ketilgan bozor (`markets.is_active = false`, §6.4). */
const DRAFT = {
  id: "44444444-4444-4444-8444-444444444444",
  name: "Nurota yangi bozori",
  is_active: false,
};

/** `auth.marketDraft` — uz-Latn qiymati (test AYNAN shu katalogni yuklaydi). */
const DRAFT_BADGE = "Qoralama";
const SELECT_MARKET_PATH = "/auth/select-market";
const setupStatusPath = (marketId: string): string =>
  `/markets/${marketId}/setup-status`;

/**
 * `select-market` javobini beradigan mock (ixtiyoriy `setup-status` bilan).
 *
 * `mockResolvedValue` YETMAYDI: qoralama oqimida `apiFetch` IKKI marta
 * chaqiriladi (sessiya + usta holati) va bitta javob ikkalasiga ham
 * qaytarilsa test o'zi kutgan narsani emas, tasodifni tekshirardi.
 */
function mockSelectMarket(
  market: typeof KARMANA | typeof DRAFT,
  setupStatus?: { blocking: { step: number }[] } | Error,
): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === SELECT_MARKET_PATH) {
      return Promise.resolve({
        access_token: "new-token",
        token_type: "bearer",
        expires_in: 900,
        roles: ["platform_admin"],
        market,
      });
    }
    if (path === setupStatusPath(market.id)) {
      return setupStatus instanceof Error
        ? Promise.reject(setupStatus)
        : Promise.resolve(setupStatus);
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

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
function seedSessionWithMarkets(
  markets: readonly MarketSummary[] = [KARMANA, NAVOIY],
): void {
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
    markets,
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

describe("MarketPicker — qoralama bozor (§6.4 uzilishdan tiklanish)", () => {
  test("qoralama bozor ro'yxatda `Qoralama` belgisi bilan ko'rinadi", () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    renderPicker();

    // IKKALASI ham render bo'ladi — qoralama serverda ham, bu yerda ham
    // filtrlanmaydi (§12.1.1 6-band).
    expect(screen.getAllByRole("button")).toHaveLength(2);
    expect(screen.getByText(KARMANA.name)).toBeInTheDocument();
    expect(screen.getByText(DRAFT.name)).toBeInTheDocument();

    // Belgi AYNAN BITTA: faol bozor uni olmaydi. Sanoqsiz `getByText`
    // ikkala tugmada ham badge chiqqan holatni o'tkazib yuborardi.
    expect(screen.getAllByText(DRAFT_BADGE)).toHaveLength(1);
    expect(
      screen.getByRole("button", { name: `${DRAFT.name} ${DRAFT_BADGE}` }),
    ).toBeInTheDocument();
    // Rang YAGONA signal emas: belgi tugmaning hisoblangan nomiga kiradi,
    // ya'ni skrinrider foydalanuvchisi ham holatni eshitadi (WCAG 1.4.1).
    expect(
      screen.getByRole("button", { name: KARMANA.name }),
    ).toBeInTheDocument();
  });

  test("qoralama tanlanganda birinchi tugallanmagan qadamga marshrutlanadi", async () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    // Tartib ATAYIN o'sish bo'yicha emas: `blocking[]` dagi ENG KICHIK qadam
    // olinishi kerak, birinchi element emas (§6.4 qoida 4).
    mockSelectMarket(DRAFT, { blocking: [{ step: 5 }, { step: 3 }] });

    renderPicker();
    fireEvent.click(
      screen.getByRole("button", { name: `${DRAFT.name} ${DRAFT_BADGE}` }),
    );

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/markets/setup?step=3");
    });

    const paths = apiFetch.mock.calls.map((call) => call[0] as string);
    expect(paths).toEqual([SELECT_MARKET_PATH, setupStatusPath(DRAFT.id)]);
  });

  test("setup-status yiqilsa ham foydalanuvchi ustaga kiradi (1-qadam)", async () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    // T-02-19: endpoint 02-11 gacha umuman mavjud emas va keyin ham
    // yiqilishi mumkin. Fail-SAFE, fail-closed emas — bu navigatsiya,
    // xavfsizlik chegarasi emas.
    mockSelectMarket(DRAFT, new Error("setup-status mavjud emas"));

    renderPicker();
    fireEvent.click(
      screen.getByRole("button", { name: `${DRAFT.name} ${DRAFT_BADGE}` }),
    );

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/markets/setup?step=1");
    });
  });

  test("NAZORAT: faol bozor tanlanganda ustaga BORILMAYDI", async () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    mockSelectMarket(KARMANA);

    renderPicker();
    fireEvent.click(screen.getByRole("button", { name: KARMANA.name }));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/dashboard");
    });

    /*
     * NAZORAT HOLATI MAJBURIY: usiz yuqoridagi ikki test "hamma narsa
     * ustaga ketyapti" holatida ham yashil ko'rinardi — masalan `is_active`
     * tekshiruvi butunlay tushib qolsa. Bu yerda ikki da'vo bor:
     *   1. marshrutlarning HECH BIRI usta yo'liga tegmaydi;
     *   2. `setup-status` UMUMAN chaqirilmaydi (faol bozorda uning ma'nosi
     *      yo'q va ortiqcha so'rov o'zi ham defekt bo'lardi).
     */
    for (const [path] of routerMock.replace.mock.calls as [string][]) {
      expect(path).not.toContain("/markets/setup");
    }
    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(apiFetch.mock.calls[0]?.[0]).toBe(SELECT_MARKET_PATH);
  });
});
