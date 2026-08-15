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
import type { ComponentProps, ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { MarketPicker } from "@/components/auth/market-picker";
import { ACTIVATION_STEP } from "@/components/wizard/wizard-steps";
import { apiRequest, errorMessageKey } from "@/lib/api-client";
import type { MarketSummary } from "@/lib/api-types";
import {
  AuthProvider,
  clearSession,
  readSession,
  setSession,
} from "@/lib/auth-store";

/*
 * `useRouter` Next.js router kontekstini talab qiladi — u jsdom'da yo'q,
 * shuning uchun navigatsiya mock bilan almashtiriladi. Mock `vi.mock`
 * ko'tarilishidan (hoisting) OLDIN mavjud bo'lishi kerak, shuning uchun
 * `vi.hoisted`.
 *
 * `Link` 02-18 da qo'shildi: bo'sh ro'yxat holatida usta havolasi shu
 * komponentdan chiqadi va u oddiy `<a>` ga aylantiriladi (locale prefiksini
 * qo'yish `next-intl` ning zimmasida va bu yerda sinalmaydi).
 */
const routerMock = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
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
/** `wizard.createFirstMarket` va `auth.noMarkets` — uz-Latn qiymatlari. */
const CREATE_FIRST_MARKET = "Birinchi bozorni yaratish";
const NO_MARKETS_TEXT = "Sizga hech qanday bozor biriktirilmagan";
const LOGOUT_LABEL = "Chiqish";
const NEW_MARKET_PATH = "/markets/new";
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
  setupStatus?:
    | { blocking: { step: number }[]; can_activate?: boolean }
    | Error,
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

/**
 * Bozori UMUMAN yo'q sessiya — CR-03 ning asosiy holati (toza o'rnatish).
 *
 * `roles` ATAYIN haqiqiy: `auth.py::_session_roles` platforma adminiga
 * a'zolik qatorisiz ham `platform_admin` rolini beradi, ya'ni bozorsiz
 * login javobida ham `roles: ["platform_admin"]` keladi. Yuqoridagi
 * `seedSessionWithMarkets` dagi bo'sh `roles: []` — 1-fazadan qolgan
 * soddalashtirish va u bu yerda TAKRORLANMAYDI, aks holda test o'zi
 * tekshirmoqchi bo'lgan huquqni yo'q qilib qo'yardi.
 */
function seedSessionWithoutMarkets(
  roles: readonly string[] = ["platform_admin"],
): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: null,
      marketName: null,
      isPlatformAdmin: roles.includes("platform_admin"),
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
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
  vi.unstubAllGlobals();
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

/*
 * =============================================================================
 * TOPILMA №A — 7/7 BAJARILGAN QORALAMA «DAVOM ETISH» KARUSELIDA QOLARDI.
 *
 * Yuqoridagi blok CHALA qoralamani o'lchaydi (`blocking` to'la). Bu blok
 * uning YETISHMAYOTGAN yarmini o'lchaydi: `blocking` BO'SH bo'lganda, ya'ni
 * ustaning yettala qadami bajarilganda, foydalanuvchi qayerga tushadi.
 *
 * Nuqson: `fetchFirstIncompleteStep` bo'sh `blocking` uchun 1-qadamni
 * qaytarardi, ya'ni tugallangan bozor ham ustaning BOSHIGA tushardi va
 * faollashtirish paneliga (7-qadam) yetib borishning ishonchli yo'li yo'q
 * edi. Aynan shu sabab №B (bozorni jonlantirish) ni ham qulflab turardi.
 *
 * ⚠ QADAM RAQAMI KONSTANTADAN: URL `?step=7` deb literal yozilsa da'vo
 *   `ACTIVATION_STEP` o'zgargan kuni yolg'onga aylanardi.
 * =============================================================================
 */
describe("MarketPicker — 7/7 qoralama (Topilma №A)", () => {
  test("to'liq qoralama FAOLLASHTIRISH qadamiga marshrutlanadi", async () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    // Server «hech narsa qolmadi» dedi: `blocking` bo'sh, `can_activate` rost.
    mockSelectMarket(DRAFT, { blocking: [], can_activate: true });

    renderPicker();
    fireEvent.click(
      screen.getByRole("button", { name: `${DRAFT.name} ${DRAFT_BADGE}` }),
    );

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith(
        `/markets/setup?step=${ACTIVATION_STEP}`,
      );
    });

    /*
     * KARUSEL QAYTIB KELMASLIGI UCHUN ALOHIDA DA'VO: 1-qadam
     * `RequisitesSummary` ni ochadi va u yerdan yagona yo'l «Davom etish»
     * -> `?step=2` edi. Bironta marshrut o'sha boshlanish nuqtasiga
     * tegmasligi kerak.
     */
    for (const [path] of routerMock.replace.mock.calls as [string][]) {
      expect(path).not.toBe("/markets/setup?step=1");
    }
  });

  test("NAZORAT: faol bozorda `setup-status` UMUMAN so'ralmaydi", async () => {
    seedSessionWithMarkets([KARMANA, DRAFT]);
    mockSelectMarket(KARMANA);

    renderPicker();
    fireEvent.click(screen.getByRole("button", { name: KARMANA.name }));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/dashboard");
    });

    /*
     * SANOQ BILAN EMAS, YO'L BILAN: yuqoridagi blokdagi nazorat
     * `toHaveBeenCalledTimes(1)` ga tayanadi va u kelajakda qo'shiladigan
     * begona so'rovdan (masalan telemetriya) yolg'on-qizil bo'lardi. Bu
     * yerdagi da'vo AYNAN bitta narsani aytadi: faol bozorda usta holati
     * so'ralmaydi, chunki uning ma'nosi yo'q.
     */
    const paths = apiFetch.mock.calls.map((call) => call[0] as string);
    expect(paths).not.toContain(setupStatusPath(KARMANA.id));
    for (const path of paths) {
      expect(path).not.toContain("setup-status");
    }
  });
});

/*
 * =============================================================================
 * CR-03 ning UCHINCHI to'sig'i — bo'sh ro'yxatdagi chiqish yo'li (02-18).
 *
 * NEGA MUHIM: toza platformada birinchi bozorni yaratish yo'li AYNAN shu
 * ekrandan o'tadi. Bozori yo'q platforma admini login qilgach `(app)/layout`
 * uni bu yerga yuboradi va bu yerda faqat "Chiqish" tugmasi turardi —
 * ya'ni mahsulot o'z-o'zini bootstrap qila olmasdi.
 *
 * `apiFetch` bu blokda `[]` qaytaradi: ro'yxat bo'sh bo'lgani uchun
 * `useMarketsQuery` YOQILADI (`enabled: markets.length === 0`) va u
 * yakunlanmaguncha komponent yuklanish holatida turadi. Ya'ni bo'sh holat
 * tarmog'iga faqat serverning "bozor yo'q" javobidan KEYIN tushiladi —
 * bu haqiqiy oqimning o'zi.
 * =============================================================================
 */
describe("MarketPicker — bo'sh ro'yxat: ustaga chiqish yo'li (CR-03)", () => {
  test("`market_manage` huquqli admin «Birinchi bozorni yaratish» havolasini ko'radi", async () => {
    seedSessionWithoutMarkets();
    apiFetch.mockResolvedValue([]);

    renderPicker();

    expect(await screen.findByText(NO_MARKETS_TEXT)).toBeInTheDocument();

    const link = screen.getByRole("link", { name: CREATE_FIRST_MARKET });
    expect(link).toHaveAttribute("href", NEW_MARKET_PATH);

    /*
     * "Chiqish" OLIB TASHLANMAYDI va bu alohida da'vo: havola qo'shilishi
     * mavjud yagona chiqish yo'lini yo'q qilib yubormasligi kerak.
     */
    expect(
      screen.getByRole("button", { name: LOGOUT_LABEL }),
    ).toBeInTheDocument();
  });

  test("NAZORAT: `market_manage` YO'Q foydalanuvchida havola ko'rinmaydi", async () => {
    // Noto'g'ri a'zolik bilan qolgan bozor admini: bozori yo'q, yaratish
    // huquqi ham yo'q. Unga havola ko'rsatish 403 ga olib boradigan yolg'on
    // signal bo'lardi (T-02-142), shuning uchun faqat "Chiqish" qoladi.
    seedSessionWithoutMarkets(["market_admin"]);
    apiFetch.mockResolvedValue([]);

    renderPicker();

    expect(await screen.findByText(NO_MARKETS_TEXT)).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: CREATE_FIRST_MARKET }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: LOGOUT_LABEL }),
    ).toBeInTheDocument();
  });

  test("NAZORAT: ro'yxat bo'sh EMAS — havola bo'sh holat tarmog'ida qoladi", () => {
    seedSessionWithMarkets();
    renderPicker();

    /*
     * Usiz havola butun ekranga chiqib ketgan (bo'sh holat tarmog'idan
     * tashqariga) holat ham yashil ko'rinardi — ya'ni bozori BOR admin
     * tanlash o'rniga yangi bozor yaratishga undalgan bo'lardi.
     */
    expect(
      screen.queryByRole("link", { name: CREATE_FIRST_MARKET }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(2);
  });
});

/*
 * =============================================================================
 * WR-09 — sessiya o'rtasidagi parol darvozasi (02-REVIEW.md).
 *
 * SENARIY: admin boshqa odamning parolini u ISHLAYOTGAN paytda tiklaydi.
 * Server o'sha zahoti har yozuv so'roviga 403 `password_change_required`
 * qaytara boshlaydi, klientdagi `principal.mustChangePassword` esa hamon
 * `false` — natijada foydalanuvchi har ekranda "ruxsat yo'q" ko'radi va
 * `/change-password` ga BIRORTA yo'l yo'q.
 *
 * NEGA `apiRequest` MOCK QILINMAYDI: bu blok aynan uning xato tarmog'ini
 * o'lchaydi. Fayl boshidagi mock faqat `apiFetch` ni almashtiradi
 * (`importOriginal` bilan), ya'ni `apiRequest` HAQIQIY kod bo'lib qoladi va
 * `fetch` global darajada almashtiriladi.
 * =============================================================================
 */
describe("apiRequest — 403 `password_change_required` (WR-09)", () => {
  function stubResponse(status: number, detail: string): void {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail }), {
          status,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  }

  test("store server verdiktiga moslashadi: `mustChangePassword` `true` bo'ladi", async () => {
    seedSessionWithoutMarkets();
    stubResponse(403, "password_change_required");

    await expect(apiRequest("/stalls")).rejects.toThrow();

    /*
     * `clearSession()` ATAYIN chaqirilmaydi: server 401 EMAS, 403 ni
     * tanlagan (`deps.py:389-412`) — 401 sessiyani uzib redirect siklini
     * tug'dirardi. Shuning uchun sessiya YASHAYDI va faqat bayroq mos
     * qilinadi; qolganini `(app)/layout.tsx` ning mavjud qoidasi qiladi.
     */
    expect(readSession().principal?.mustChangePassword).toBe(true);
    expect(readSession().accessToken).not.toBeNull();
  });

  test("NAZORAT: boshqa 403 (`role_not_allowed`) bayroqqa TEGMAYDI", async () => {
    seedSessionWithoutMarkets();
    stubResponse(403, "role_not_allowed");

    await expect(apiRequest("/stalls")).rejects.toThrow();

    /*
     * NAZORAT MAJBURIY: usiz "har 403 da `mustChangePassword = true`"
     * degan implementatsiya ham yashil ko'rinardi — u esa oddiy huquq
     * xatosini parol almashtirish ekraniga aylantirib yuborardi.
     */
    expect(readSession().principal?.mustChangePassword).toBe(false);
  });

  test("xato kodi tarjima kalitiga xaritalanadi (xom `detail` ko'rsatilmaydi)", async () => {
    seedSessionWithoutMarkets();
    stubResponse(403, "password_change_required");

    const error = await apiRequest("/stalls").catch((cause: unknown) => cause);

    // T-01-65: xom kod emas, tarjima kaliti — va u uchala tilda mavjud.
    expect(errorMessageKey(error)).toBe("auth.passwordChangeRequired");
    expect(messages.auth.passwordChangeRequired).toBeTruthy();
  });
});
