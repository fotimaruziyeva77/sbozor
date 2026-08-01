/**
 * `(app)/layout.tsx` marshrut darvozasi — CR-03 ning BIRINCHI to'sig'i (02-18).
 *
 * NEGA AYNAN SHU FAYL: 02-VERIFICATION.md ning 1-bo'shlig'i bo'yicha
 * `principal.marketId === null` bo'lgan platforma admini SO'ZSIZ
 * `/select-market` ga haydalardi, u yerdan esa faqat "chiqish" mumkin edi.
 * Ya'ni TOZA o'rnatishda birinchi bozorni umuman yaratib bo'lmasdi: usta
 * (`/markets/new`) qurilgan, sinalgan va YETIB BO'LMAYDIGAN edi.
 *
 * Test qulflaydigan xulq:
 *   1. `/markets/new` — bozorsiz sessiyada OCHILADI (redirect ham yo'q,
 *      abadiy skelet ham yo'q).
 *   2. NAZORAT: `/stalls` — bozorsiz sessiyada HAMON `/select-market` ga
 *      yo'naltiriladi. Usiz 1-test "redirect butunlay o'chirildi" holatida
 *      ham yashil ko'rinardi.
 *   3. Parol darvozasi USTUN: `mustChangePassword` `/markets/new` da ham
 *      `/change-password` ga olib boradi (T-01-64 saqlanadi).
 *   4. T-02-140: istisno AYNAN BITTA literal yo'lga bog'langan —
 *      `/markets/new-anything` unga TUSHMAYDI (prefiks emas, tenglik).
 *
 * DIQQAT — `AppShell` MOCK qilingan. Bu qamrovni toraytirmaydi: bu faylning
 * da'volari faqat MARSHRUT qarori haqida (kim qayerga yo'naltiriladi va
 * bolalar render bo'ladimi). Qobiqning o'z da'volari — navigatsiya yozuvi va
 * huquq filtri — `app-shell.test.tsx` da, alohida o'lchanadi.
 */
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../../messages/uz-Latn.json";
import AppLayout from "./layout";
import type { Principal } from "@/lib/auth-store";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

/*
 * `useRouter`/`usePathname` Next.js router kontekstini talab qiladi — u
 * jsdom'da yo'q (`market-picker.test.tsx:32-37` bilan AYNI sabab). `pathname`
 * mock obyektining MAYDONI, chunki har test uni o'zi o'rnatadi; `vi.hoisted`
 * mock'ning ko'tarilishidan oldin mavjud bo'lishini kafolatlaydi.
 */
const navigationMock = vi.hoisted(() => ({
  replace: vi.fn(),
  pathname: "/dashboard",
}));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => ({ replace: navigationMock.replace }),
  usePathname: () => navigationMock.pathname,
}));

/*
 * Sessiya SEED bilan o'rnatiladi, ya'ni `restoreSession()` yo'li umuman
 * ishga tushmaydi. U baribir mock qilinadi: mock qilinmasa test haqiqiy
 * `fetch` ga chiqib ketish xavfini saqlab qolardi.
 */
const apiClientMock = vi.hoisted(() => ({
  restoreSession: vi.fn(),
  loadPrincipal: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    restoreSession: apiClientMock.restoreSession,
    loadPrincipal: apiClientMock.loadPrincipal,
  };
});

vi.mock("@/components/shell/app-shell", () => ({
  AppShell: ({ children }: { children: ReactNode }) => (
    <div data-testid="app-shell">{children}</div>
  ),
}));

/** Bolalar render bo'lganini isbotlaydigan nishon. */
const CHILD_MARKER = "usta-1-qadam";

const SELECT_MARKET_PATH = "/select-market";
const CHANGE_PASSWORD_PATH = "/change-password";

function seedSession(overrides: Partial<Principal> = {}): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998901234567",
      fullName: "Platforma Admini",
      roles: ["platform_admin"],
      // ASOSIY HOLAT: bozor hali TANLANMAGAN (yoki umuman mavjud emas).
      marketId: null,
      marketName: null,
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
      ...overrides,
    },
    markets: [],
  });
}

function renderLayout(pathname: string): void {
  navigationMock.pathname = pathname;

  render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <AuthProvider>
        <AppLayout>
          <p>{CHILD_MARKER}</p>
        </AppLayout>
      </AuthProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  clearSession();
  vi.resetAllMocks();
  navigationMock.pathname = "/dashboard";

  /*
   * `restoreSession` HAR DOIM promise qaytarishi SHART, garchi asosiy yo'lda
   * u umuman chaqirilmasa ham (sessiya seed qilingan -> `hasSession === true`).
   * Sabab: test tugaganda `clearSession()` sessiyani bo'shatadi, komponent
   * hali MONTAJDA turadi va effekt qayta ishga tushadi. Qiymatsiz `vi.fn()`
   * `undefined` qaytarib, `undefined.then` bilan butun faylni yiqitardi.
   */
  apiClientMock.restoreSession.mockResolvedValue(false);
});

afterEach(() => {
  clearSession();
});

describe("(app)/layout — usta marshruti istisnosi (CR-03)", () => {
  test("`/markets/new`: bozori YO'Q admin ushlab qolinmaydi va sahifa ochiladi", () => {
    seedSession();
    renderLayout("/markets/new");

    /*
     * IKKI DA'VO, IKKALASI HAM MAJBURIY va ular TAKROR EMAS:
     *   - redirect chaqirilmadi  -> `useEffect` tuzatilgan;
     *   - bolalar render bo'ldi  -> `ready` ham tuzatilgan.
     * Faqat bittasi tuzatilsa ikkinchi assert qizaradi: `ready` tuzatilmasa
     * ekranda abadiy skelet qolardi (redirect yo'q, lekin sahifa ham yo'q).
     */
    expect(navigationMock.replace).not.toHaveBeenCalled();
    expect(screen.getByText(CHILD_MARKER)).toBeInTheDocument();
  });

  test("NAZORAT: `/stalls` bozorsiz sessiyada HAMON `/select-market` ga yo'naltiriladi", () => {
    seedSession();
    renderLayout("/stalls");

    /*
     * NAZORAT HOLATI MAJBURIY: usiz yuqoridagi test "D-06 darvozasi
     * BUTUNLAY o'chirildi" holatida ham yashil ko'rinardi — ya'ni istisno
     * emas, regressiya qulflangan bo'lardi.
     */
    expect(navigationMock.replace).toHaveBeenCalledWith(SELECT_MARKET_PATH);
    expect(screen.queryByText(CHILD_MARKER)).not.toBeInTheDocument();
  });

  test("parol darvozasi USTUN: `/markets/new` da ham `/change-password` ga boradi", () => {
    seedSession({ mustChangePassword: true });
    renderLayout("/markets/new");

    expect(navigationMock.replace).toHaveBeenCalledWith(CHANGE_PASSWORD_PATH);
    // Istisno parol qoidasini CHETLAB O'TMAYDI — sahifa baribir ochilmaydi.
    expect(screen.queryByText(CHILD_MARKER)).not.toBeInTheDocument();
    expect(navigationMock.replace).not.toHaveBeenCalledWith(SELECT_MARKET_PATH);
  });

  test("T-02-140: istisno AYNAN bitta yo'l — `/markets/new-anything` unga tushmaydi", () => {
    seedSession();
    renderLayout("/markets/new-anything");

    /*
     * Agar istisno `startsWith` yoki `includes` bilan yozilsa, butun
     * `(app)` daraxti bozorsiz ochilib ketardi (huquq oshirish yuzasi).
     * Tenglik sharti buni bitta literal yo'l bilan cheklaydi.
     */
    expect(navigationMock.replace).toHaveBeenCalledWith(SELECT_MARKET_PATH);
    expect(screen.queryByText(CHILD_MARKER)).not.toBeInTheDocument();
  });

  test("bozori BOR admin uchun `/markets/new` ham, boshqa sahifalar ham ochiladi", () => {
    seedSession({
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Karmana markaziy bozori",
    });
    renderLayout("/markets/new");

    // Ikkinchi bozor yaratish yo'li bozorli sessiyada ham yopilmaydi.
    expect(navigationMock.replace).not.toHaveBeenCalled();
    expect(screen.getByText(CHILD_MARKER)).toBeInTheDocument();
  });
});
