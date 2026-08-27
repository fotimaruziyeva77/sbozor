/**
 * BOZOR HOLATI KARTASI — PLATFORMA ADMINI BOSH EKRANI (Topilma №H).
 *
 * =============================================================================
 * BU FAYLNING MARKAZIY DA'VOSI: O'LCHANMAGAN QIYMAT O'RNIGA NOL YOZILMAYDI.
 *
 *   Bu loyihaning takrorlangan qoidasi (05-13, 05-14, 03-08 —
 *   «`—`, `0 ta` emas») va u bu yerda IKKI joyda ishlaydi:
 *
 *     * bozor holati NOMA'LUM bo'lsa — `—`, «Qoralama» EMAS. Noma'lumni
 *       qoralama deb talqin qilish faol bozorga «hali ishga
 *       tushmagansiz» degan yolg'on yorliq yopishtirardi va admin
 *       faollashtirish qadamiga borib, u yerda tushunarsiz 409 olardi.
 *     * so'rov YIQILSA sanoqlar `—`. Nol — O'LCHANGAN qiymat: «bozorda
 *       0 ta rasta bor» va «rastalar sonini bilmayman» butunlay boshqa
 *       ikki gap.
 *
 * ⚠ IKKI SO'ROV MUSTAQIL (H5). Biri yiqilganda ikkinchisining soni
 *   ekranda QOLADI — aks holda `GET /users` ning bir martalik nosozligi
 *   rastalar sonini ham o'chirib yuborardi.
 *
 * ⚠ HAVOLA MANZILI KONSTANTADAN (`ACTIVATION_STEP`), SONLI LITERALDAN
 *   EMAS. `market-picker.test.tsx:409` da o'rnatilgan qoida: qadam
 *   raqami o'zgargan kuni literal yozilgan da'vo JIMGINA yolg'onga
 *   aylanardi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactElement } from "react";
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

import messages from "../../../messages/uz-Latn.json";
import { MarketStatusCard } from "@/components/dashboard/market-status-card";
import { ACTIVATION_STEP } from "@/components/wizard/wizard-steps";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const DRAFT = messages.dashboard.statusDraft;
const ACTIVE = messages.dashboard.statusActive;
const ACTIVATE_HINT = messages.dashboard.activateHint;

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

const USERS = {
  items: [
    {
      id: "44444444-4444-4444-8444-444444444444",
      phone: "+998901234567",
      full_name: "Kassir",
      roles: ["cashier"],
      is_active: true,
      must_change_password: false,
      locale: "uz-Latn",
      created_at: "2026-08-01T05:00:00Z",
    },
    {
      id: "55555555-5555-4555-8555-555555555555",
      phone: "+998901234568",
      full_name: "Nazoratchi",
      roles: ["inspector"],
      is_active: true,
      must_change_password: false,
      locale: "uz-Latn",
      created_at: "2026-08-01T05:00:00Z",
    },
  ],
};

/** Ikkala so'rovni ham javoblaydi. */
function routeOk(): void {
  apiFetch.mockImplementation((path: string) => {
    if (path.includes("/setup-status")) return Promise.resolve(SETUP_STATUS);
    if (path === "/users") return Promise.resolve(USERS);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

/** `setup-status` YIQILADI, `GET /users` esa ishlaydi (H5). */
function routeSetupStatusFails(): void {
  apiFetch.mockImplementation((path: string) => {
    if (path.includes("/setup-status")) {
      return Promise.reject(new Error("setup-status yiqildi"));
    }
    if (path === "/users") return Promise.resolve(USERS);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function seedSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Platforma Admini",
      roles: ["platform_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

function renderCard(isActive: boolean | null | undefined): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <MarketStatusCard isActive={isActive} marketId={MARKET_ID} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  render(tree);
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedSession();
});

afterEach(() => {
  clearSession();
});

/* ---------------------------------------------------------------------------
 * H1/H2/H3 — HOLAT QATORI
 * ------------------------------------------------------------------------ */

describe("bozor holati", () => {
  test("H1: qoralama -> «Qoralama» + faollashtirish havolasi", async () => {
    routeOk();
    renderCard(false);

    expect(await screen.findByText(DRAFT)).toBeInTheDocument();

    const link = screen.getByRole("link", { name: ACTIVATE_HINT });
    // ⚠ Manzil KONSTANTADAN — sonli literal yozilmaydi.
    expect(link).toHaveAttribute(
      "href",
      `/markets/setup?step=${ACTIVATION_STEP}`,
    );
  });

  test("H2: faol -> «Faol», havola EKRANDA YO'Q", async () => {
    routeOk();
    renderCard(true);

    expect(await screen.findByText(ACTIVE)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: ACTIVATE_HINT })).toBeNull();
    expect(document.body.textContent).not.toContain(DRAFT);
  });

  test("H3: NOMA'LUM -> `—`, na «Qoralama», na «Faol», na havola", async () => {
    routeOk();
    renderCard(undefined);

    await screen.findByText(messages.dashboard.marketStatus);

    expect(document.body.textContent).not.toContain(DRAFT);
    expect(document.body.textContent).not.toContain(ACTIVE);
    expect(screen.queryByRole("link", { name: ACTIVATE_HINT })).toBeNull();
    expect(document.body.textContent).toContain("—");
  });

  test("H3b: `null` ham NOMA'LUM bilan bir xil (login javobida bozor yo'q)", async () => {
    routeOk();
    renderCard(null);

    await screen.findByText(messages.dashboard.marketStatus);

    expect(document.body.textContent).not.toContain(DRAFT);
    expect(screen.queryByRole("link", { name: ACTIVATE_HINT })).toBeNull();
  });
});

/* ---------------------------------------------------------------------------
 * H4/H5 — TO'RT HISOBLAGICH
 * ------------------------------------------------------------------------ */

describe("hisoblagichlar", () => {
  test("H4: to'rtala son SERVERDAN keladi", async () => {
    routeOk();
    renderCard(true);

    await waitFor(() => {
      expect(screen.getByText(String(SETUP_STATUS.stalls))).toBeInTheDocument();
    });
    expect(screen.getByText(String(SETUP_STATUS.vendors))).toBeInTheDocument();
    expect(screen.getByText(String(SETUP_STATUS.cameras))).toBeInTheDocument();
    expect(
      screen.getByText(String(USERS.items.length)),
    ).toBeInTheDocument();

    // ⛔ Yangi endpoint YO'Q — AYNAN ikki mavjud so'rov.
    const paths = apiFetch.mock.calls.map((call) => String(call[0]));
    expect(paths.some((path) => path.includes("/setup-status"))).toBe(true);
    expect(paths).toContain("/users");
  });

  test("H5: `setup-status` yiqilsa uchala sanoq `—`, NOL PAYDO BO'LMAYDI", async () => {
    routeSetupStatusFails();
    renderCard(true);

    // Foydalanuvchilar sanog'i O'Z so'rovidan keladi va KO'RINISHDA qoladi.
    await waitFor(() => {
      expect(
        screen.getByText(String(USERS.items.length)),
      ).toBeInTheDocument();
    });

    for (const label of [
      messages.dashboard.countStalls,
      messages.dashboard.countVendors,
      messages.dashboard.countCameras,
    ]) {
      const term = screen.getByText(label);
      const value = term.nextElementSibling;
      expect(value?.textContent).toBe("—");
    }

    expect(document.body.textContent).not.toContain("0");
  });
});
