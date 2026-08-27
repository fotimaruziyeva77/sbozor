/**
 * FAOLLASHTIRISH — ⛔ QAYTARIB BO'LMAYDIGAN AMAL TASDIQSIZ BAJARILMAYDI.
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI (TEST-REPORT 2026-08-15, Topilma №B):
 *
 *   BOZORNI JONLANTIRISH — BITTA BOSISHDA QAYTARIB BO'LMAYDIGAN AMAL, VA
 *   BUGUN U TASDIQ SO'RAMAYDI.
 *
 *   Amalning qaytarilmasligi TAXMIN emas, koddagi fakt: `market_deactivate()`
 *   funksiyasi ATAYIN yaratilmagan (`markets.py:500-504`) va faol bozorni
 *   o'chirish ham `market_delete_draft()` darvozasida rad etiladi. Ya'ni
 *   noto'g'ri bozorni faollashtirgan admin uchun UI'da ORQAGA YO'L YO'Q.
 *
 *   Buning ustiga amal PUL oqibatiga ega: faollashtirish kunidan boshlab
 *   `billing_close` o'sha bozorga kunlik patta hisobini yoza boshlaydi
 *   (`retention.py:162-164` — `WHERE is_active`, job yugurgan LAHZADA
 *   baholanadi). Foydalanuvchi buni bilib turib bosishi kerak.
 * =============================================================================
 *
 * TO'RT MUSTAQIL DA'VO — biri ikkinchisining o'rnini BOSMAYDI:
 *   T1  tugma bosildi        -> dialog OCHILADI va so'rov KETMAYDI;
 *   T2  dialogda tasdiqlandi -> `POST /activate` AYNAN BIR MARTA ketadi;
 *   T3  bekor qilindi        -> so'rov UMUMAN ketmaydi, panel joyida qoladi;
 *   T4  chala bozor          -> dialog OCHILMAYDI (nazorat, UI-SPEC §6.6).
 *
 * ⛔ T4 NAZORAT SIFATIDA MAJBURIY. Usiz «har bosishda dialog ochiladi»
 *    degan implementatsiya ham yashil bo'lardi — u esa §6.6 ning mavjud
 *    yo'lini (so'rov yo'q + fokus birinchi bajarilmagan bandga +
 *    `aria-live` e'loni) tasdiq oynasi bilan almashtirib, chala bozorni
 *    «tasdiqlab bo'ladigan» narsaga o'xshatib qo'yardi.
 *
 * ⚠ HAR TESTDA YANGI `QueryClient` VA `retry: false`: umumiy klient
 *   oldingi testning 409 javobini keyingisiga olib o'tardi va bu faylning
 *   holat almashinuvlari (409 -> ro'yxat almashadi) uni ayniqsa nozik
 *   qiladi.
 *
 * DIQQAT: bosish `fireEvent` bilan — loyihada `user-event` ishlatilmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ComponentProps, ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const routerMock = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("@/i18n/navigation", () => ({
  useRouter: () => routerMock,
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import messages from "../../../messages/uz-Latn.json";
import { ActivationPanel } from "@/components/wizard/activation-panel";
import type { SetupStatusResponse } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SETUP_STATUS_PATH = `/markets/${MARKET_ID}/setup-status`;
const ACTIVATE_PATH = `/markets/${MARKET_ID}/activate`;

/** uz-Latn kataloglaridagi AYNAN qiymatlar — literal yozilmaydi. */
const ACTIVATE_LABEL = messages.wizard.activate;
const CANCEL_LABEL = messages.common.cancel;
const CONFIRM_TITLE = messages.wizard.activateConfirmTitle;
const BLOCKED_REASON = messages.wizard.blockedReason;
const STEP_2_LABEL = messages.wizard.step["2"];

/** 7/7 bajarilgan qoralama — serverning «faollashtirsa bo'ladi» javobi. */
const READY_STATUS: SetupStatusResponse = {
  zones: 2,
  categories: 3,
  tariffs_covered: 3,
  categories_total: 3,
  stalls: 40,
  stalls_with_category: 40,
  vendors: 12,
  calendar_configured: true,
  cameras: 0,
  can_activate: true,
  blocking: [],
};

/** Chala bozor — 2-qadam to'ldirilmagan (UI-SPEC §6.6 ning kirishi). */
const BLOCKED_STATUS: SetupStatusResponse = {
  ...READY_STATUS,
  zones: 0,
  can_activate: false,
  blocking: [{ step: 2, code: "zones_missing", detail: "0" }],
};

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/**
 * Yo'lga qarab javob beradi — noma'lum yo'l TESTNI YIQITADI.
 *
 * Jimgina `{}` qaytarish testni yolg'on-yashil qilardi va qaysi yuza
 * qoplanmaganini yashirardi (`markets/setup/page.test.tsx` qoidasi).
 */
function routeFetch(status: SetupStatusResponse): void {
  apiFetch.mockImplementation((path: string) => {
    if (path === SETUP_STATUS_PATH) return Promise.resolve(status);
    if (path === ACTIVATE_PATH) {
      return Promise.resolve({
        id: MARKET_ID,
        name: "Karmana markaziy bozori",
        is_active: true,
      });
    }
    return Promise.reject(
      new Error(`Mock qoplamagan yo'l — testning ko'r nuqtasi: ${path}`),
    );
  });
}

async function renderPanel(status: SetupStatusResponse): Promise<void> {
  routeFetch(status);

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <ActivationPanel />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
  // `setup-status` kelmaguncha panel skeleton holatida — tugma hali yo'q.
  await screen.findByRole("button", { name: ACTIVATE_LABEL });
}

/** `POST /activate` yo'liga ketgan chaqiruvlar soni. */
function activateCalls(): number {
  return apiFetch.mock.calls.filter((call) => call[0] === ACTIVATE_PATH).length;
}

beforeEach(() => {
  clearSession();
  vi.resetAllMocks();
  seedSession();
});

afterEach(() => {
  clearSession();
});

describe("ActivationPanel — tasdiq dialogi (Topilma №B)", () => {
  test("T1: tugma dialogni ochadi va so'rov TASDIQSIZ ketmaydi", async () => {
    await renderPanel(READY_STATUS);

    fireEvent.click(screen.getByRole("button", { name: ACTIVATE_LABEL }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(CONFIRM_TITLE)).toBeInTheDocument();

    /*
     * DIALOGNING MATNI IKKI FAKTNI AYTISHI SHART va ikkalasi ham koddan
     * o'qilgan: qaytarib bo'lmaslik (`markets.py:500-504`) va hisob qachondan
     * boshlanishi (`retention.py:162-164` + `billing_close.py:23`). Ular
     * `activateConfirmBody` da yashaydi; bu yerda uning EKRANDA ekani
     * tasdiqlanadi — matnni testda qayta yozish uni katalogdan uzardi.
     */
    expect(
      within(dialog).getByText(messages.wizard.activateConfirmBody),
    ).toBeInTheDocument();

    /*
     * ⛔ ENG MUHIM DA'VO: dialog ochilgani YETARLI EMAS. Agar so'rov
     * dialog bilan BIR VAQTDA ketsa, tasdiq oynasi bezakka aylanardi —
     * bozor allaqachon jonlangan bo'lardi.
     */
    expect(activateCalls()).toBe(0);
    expect(routerMock.replace).not.toHaveBeenCalled();
  });

  test("T2: tasdiqdan keyin `POST /activate` AYNAN BIR MARTA ketadi", async () => {
    await renderPanel(READY_STATUS);

    fireEvent.click(screen.getByRole("button", { name: ACTIVATE_LABEL }));
    const dialog = await screen.findByRole("dialog");

    /*
     * Tasdiq tugmasi O'Z FE'LI bilan yorliqlanadi (generic «Tasdiqlash»
     * TAQIQ — `confirm-dialog.tsx:33-35`), ya'ni u panel tugmasi bilan
     * BIR XIL matnga ega. `within(dialog)` chalkashlikni yo'q qiladi.
     */
    fireEvent.click(within(dialog).getByRole("button", { name: ACTIVATE_LABEL }));

    await waitFor(() => {
      expect(routerMock.replace).toHaveBeenCalledWith("/dashboard");
    });
    // Takroriy yuborish 409 `market_is_active` bilan qaytardi va
    // foydalanuvchi «xato» ekranini ko'rardi — sanoq shuning qulfi.
    expect(activateCalls()).toBe(1);
  });

  test("T3: [Bekor qilish] bosilsa so'rov UMUMAN ketmaydi", async () => {
    await renderPanel(READY_STATUS);

    fireEvent.click(screen.getByRole("button", { name: ACTIVATE_LABEL }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: CANCEL_LABEL }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    expect(activateCalls()).toBe(0);
    expect(routerMock.replace).not.toHaveBeenCalled();
    // Panel o'z holatida qoladi: ro'yxat ham, tugma ham joyida.
    expect(
      screen.getByRole("button", { name: ACTIVATE_LABEL }),
    ).toBeInTheDocument();
  });

  test("T4 NAZORAT: chala bozorda dialog OCHILMAYDI (§6.6 yo'li)", async () => {
    await renderPanel(BLOCKED_STATUS);

    fireEvent.click(screen.getByRole("button", { name: ACTIVATE_LABEL }));

    /*
     * MAVJUD YO'L TEGILMAYDI: so'rov yuborilmaydi va sabab `role="status"`
     * konteynerida e'lon qilinadi. Dialogning YO'QLIGI shu yerda ijobiy
     * da'vo — u chala bozorni «tasdiqlab bo'ladigan» narsaga aylantirardi.
     */
    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(BLOCKED_REASON);
    });
    expect(screen.getByRole("status")).toHaveTextContent(STEP_2_LABEL);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(activateCalls()).toBe(0);
  });
});
