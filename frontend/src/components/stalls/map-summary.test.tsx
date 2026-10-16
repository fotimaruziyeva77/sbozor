/**
 * PLAN-XARITA XULOSASI VA FILTRI (261016).
 *
 * ⛔ Uch da'vo: (1) sonlar va summalar `/billing/map` qatorlaridan — xarita
 *    rangi bilan AYNI javob; (2) katak bosilsa filtr yoqiladi, ikkinchi
 *    bosishda o'chadi; (3) to'lov qatlami bo'lmasa inventar xulosasi —
 *    yolg'on «to'lagan» yo'q.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { MapSummary, matchesMapFilter } from "@/components/stalls/map-summary";
import type { MapFilter } from "@/components/stalls/map-summary";
import type { StallCell } from "@/components/stalls/stall-map-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const M = messages.map;
const MARKET_ID = "99999999-9999-4999-8999-999999999999";
const uuid = (n: number) => `40000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

const mapCell = (n: number, overrides: Record<string, unknown> = {}) => ({
  id: uuid(n),
  code: String(n),
  status: "active",
  has_vendor: true,
  plan_x: null,
  plan_y: null,
  ...overrides,
});

const dayRow = (n: number, state: string, paid: number, remaining: number | null) => ({
  stall_id: uuid(n),
  state,
  amount_soum: remaining === null ? null : 22_000,
  unavailable_reason: null,
  paid_soum: paid,
  remaining_soum: remaining,
  open_case_id: null,
  open_case_service_date: null,
});

function route(day: unknown) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path === "/stalls/map") {
      return Promise.resolve({
        zones: [
          {
            id: uuid(900),
            name: "Asosiy",
            cells: [
              mapCell(1),
              mapCell(2),
              mapCell(3),
              mapCell(4, { has_vendor: false }),
              mapCell(5, { status: "maintenance" }),
            ],
          },
        ],
      });
    }
    if (path === "/billing/map") return Promise.resolve(day);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

let client: QueryClient;

function renderSummary(
  roles: readonly string[],
  filter: MapFilter | null = null,
  onFilter: (next: MapFilter | null) => void = () => {},
) {
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test",
      roles,
      marketId: MARKET_ID,
      marketName: "Bozor",
      isPlatformAdmin: roles.includes("platform_admin"),
      marketIsActive: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  const wrap = (ui: ReactNode) => (
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <QueryClientProvider client={client}>
        <AuthProvider>{ui}</AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );
  return render(wrap(<MapSummary filter={filter} onFilter={onFilter} />));
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});

afterEach(() => {
  client.clear();
  clearSession();
});

const DAY = {
  service_date: "2026-10-16",
  market_active: true,
  market_open: true,
  rows: [
    dayRow(1, "paid", 22_000, 0),
    dayRow(2, "paid", 22_000, 0),
    dayRow(3, "due", 0, 22_000),
    dayRow(4, "free", 0, null),
    dayRow(5, "mismatch", 4_000, 18_000),
  ],
};

describe("filtr mosligi", () => {
  const cell = (overrides: Partial<StallCell>): StallCell => ({
    id: "x",
    code: "1",
    tone: "neutral",
    hasVendor: true,
    dayTone: null,
    dayStateKey: null,
    ...overrides,
  });

  test("filtrsiz hamma katak mos, to'lov va inventar filtrlari o'z belgisiga qaraydi", () => {
    expect(matchesMapFilter(cell({}), null)).toBe(true);
    expect(matchesMapFilter(cell({ dayTone: "debt" }), "due")).toBe(true);
    expect(matchesMapFilter(cell({ dayTone: "paid" }), "due")).toBe(false);
    expect(matchesMapFilter(cell({ hasVendor: false }), "noVendor")).toBe(true);
    expect(matchesMapFilter(cell({ tone: "muted" }), "maintenance")).toBe(true);
    expect(matchesMapFilter(cell({ tone: "off" }), "closed")).toBe(true);
  });
});

describe("xulosa kataklari", () => {
  test("sonlar va summalar `/billing/map` qatorlaridan, sana bilan", async () => {
    route(DAY);
    renderSummary(["market_admin"]);

    expect(await screen.findByText(M.tilePaid)).toBeInTheDocument();
    expect(screen.getByText("16-oktabr, 2026 holati")).toBeInTheDocument();
    /* To'landi: 22 000 + 22 000 + 4 000 (nomuvofiq rastaning qisman to'lovi). */
    expect(screen.getByText("To'landi: 48 000 so'm")).toBeInTheDocument();
    /* Qoldi: to'lamagan + nomuvofiq qoldiqlari (22 000 + 18 000). */
    expect(screen.getByText("Qoldi: 40 000 so'm")).toBeInTheDocument();
  });

  test("katak bosilsa filtr yoqiladi, tanlangan katak qayta bosilsa o'chadi", async () => {
    route(DAY);
    const onFilter = vi.fn();
    const { rerender } = renderSummary(["market_admin"], null, onFilter);

    fireEvent.click(await screen.findByRole("button", { name: /To'lamagan/u }));
    expect(onFilter).toHaveBeenLastCalledWith("due");

    rerender(
      <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <MapSummary filter="due" onFilter={onFilter} />
          </AuthProvider>
        </QueryClientProvider>
      </NextIntlClientProvider>,
    );
    const pressed = await screen.findByRole("button", { name: /To'lamagan/u });
    expect(pressed).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Faqat «To'lamagan» rastalar ajratib ko'rsatilmoqda.")).toBeInTheDocument();

    fireEvent.click(pressed);
    expect(onFilter).toHaveBeenLastCalledWith(null);
  });

  test("to'lov qatlami huquqi yo'q — inventar xulosasi, «To'lagan» katagi YO'Q", async () => {
    route(DAY);
    renderSummary(["platform_admin"]);

    expect(await screen.findByText(M.tileActive)).toBeInTheDocument();
    expect(screen.getByText(M.tileMaintenance)).toBeInTheDocument();
    expect(screen.queryByText(M.tilePaid)).toBeNull();
    expect(apiClientMock.apiFetch.mock.calls.map((call) => call[0])).not.toContain("/billing/map");
  });
});
