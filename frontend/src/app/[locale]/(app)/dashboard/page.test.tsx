/**
 * BOSH EKRAN — BOZOR HOLATI KARTASINING **WIRING** O'LCHOVI (Topilma №H).
 *
 * =============================================================================
 * ⛔ BU FAYL KOMPONENTNI EMAS, DARVOZANI O'LCHAYDI.
 *
 *   `market-status-card.test.tsx` kartaning O'ZINI (holat qatori,
 *   hisoblagichlar, `—`) o'lchaydi. Bu yerdagi savol boshqa: KARTA KIMGA
 *   CHIZILADI. Topshiriq direktor va bozor admini bosh ekraniga tegishni
 *   TAQIQLAYDI (uni 8-faza boyitadi), ya'ni darvozaning o'zi da'voning
 *   bir qismi.
 *
 * ⚠ DARVOZA AYNAN `market_manage` VA TANLOV ASOSLANGAN:
 *     (a) `rbac.ts` matritsasida u FAQAT `platform_admin` da bor —
 *         direktorda ham, bozor adminida ham YO'Q;
 *     (b) kartaning birlamchi amali bozorni faollashtirishga olib boradi
 *         va u aynan `MARKET_MANAGE` ostidagi endpoint;
 *     (c) `market_data_view` bilan darvozalash DIREKTORNI ham qamrab,
 *         taqiqni buzardi.
 *
 * ⚠ H6 IKKI TOMONLAMA: karta chizilmasligi YETARLI EMAS — `setup-status`
 *   ga SO'ROV HAM ketmasligi kerak. Faqat matnni tekshirish «huquq
 *   tekshiruvi so'rovdan OLDIN» kontraktini o'lchamasdi va jurnalga
 *   ma'nosiz 403 lar yozilardi (`cameras/page.test.tsx` da o'rnatilgan
 *   naqsh).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("@/i18n/navigation", () => ({
  Link: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

import messages from "../../../../../messages/uz-Latn.json";
import DashboardPage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const SETUP_STATUS = {
  zones: 4,
  categories: 5,
  tariffs_covered: 5,
  categories_total: 5,
  stalls: 312,
  stalls_with_category: 312,
  vendors: 187,
  calendar_configured: true,
  cameras: 6,
  can_activate: true,
  blocking: [],
};

function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.includes("/setup-status")) return Promise.resolve(SETUP_STATUS);
    if (path === "/users") return Promise.resolve({ items: [] });
    if (path === "/me/headline") {
      return Promise.resolve({ metric: "revenue_today", value: 1250000 });
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function requestedPaths(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderPage(
  roles: readonly string[],
  options: { isPlatformAdmin?: boolean; marketIsActive?: boolean | null } = {},
) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: options.isPlatformAdmin ?? false,
      marketIsActive: options.marketIsActive,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* ---------------------------------------------------------------------------
 * H7 — PLATFORMA ADMINI KARTANI KO'RADI
 * ------------------------------------------------------------------------ */

describe("platforma admini", () => {
  test("bozor holati kartasi chiziladi", async () => {
    routeFetch();
    renderPage(["platform_admin"], {
      isPlatformAdmin: true,
      marketIsActive: false,
    });

    expect(
      await screen.findByText(messages.dashboard.marketStatus),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(messages.dashboard.statusDraft),
    ).toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * H6 — DIREKTOR BOSH EKRANI O'ZGARMAYDI
 * ------------------------------------------------------------------------ */

describe("direktor", () => {
  test("karta UMUMAN chizilmaydi VA `setup-status` ga so'rov ketmaydi", async () => {
    routeFetch();
    renderPage(["director"], { marketIsActive: false });

    // Sahifaning qolgani ishlaydi — bo'sh ekran EMAS.
    expect(screen.getByText(messages.nav.dashboard)).toBeInTheDocument();

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    expect(document.body.textContent).not.toContain(
      messages.dashboard.marketStatus,
    );
    expect(
      requestedPaths().filter((path) => path.includes("setup-status")),
    ).toEqual([]);
  });
});

/* ---------------------------------------------------------------------------
 * BOZOR ADMINI HAM — `market_manage` UNDA YO'Q
 * ------------------------------------------------------------------------ */

describe("bozor admini", () => {
  test("karta chizilmaydi (darvoza `market_manage`, unda YO'Q)", async () => {
    routeFetch();
    renderPage(["market_admin"], { marketIsActive: false });

    expect(screen.getByText(messages.nav.dashboard)).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(
      messages.dashboard.marketStatus,
    );
  });
});
