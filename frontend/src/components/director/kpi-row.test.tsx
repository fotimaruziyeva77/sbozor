/**
 * PANELNING BOSH QATORI — TO'RTTA ODDIY SAVOL (261016).
 *
 * ⛔ Buyurtmachi: «buni hech kim tushunmayapti». Bu fayl har katak oddiy
 *    gap bilan javob berishini o'lchaydi: son + uning ma'nosi. Va eski
 *    xatoning qaytmasligini: tugamagan kun FOIZ bilan solishtirilmaydi
 *    (kun boshidagi «−100%» yolg'on xavotiri).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href }: { children: ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import messages from "../../../messages/uz-Latn.json";
import { DirectorKpis, daysWithoutFrames } from "@/components/director/kpi-row";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const D = messages.director;
const NOW = new Date("2026-10-16T07:00:00Z");
const TODAY = { kind: "today" as const, from: "2026-10-16", to: "2026-10-16" };
const YESTERDAY = { kind: "yesterday" as const, from: "2026-10-15", to: "2026-10-15" };

const uuid = (n: number) => `30000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

const live = (from: string, collected: number) => ({
  from_date: from,
  to_date: from,
  total_collected_soum: collected,
  total_charged_soum: 0,
  charged_complete: false,
  collected_cash_soum: collected,
  collected_terminal_soum: 0,
});

const mapRow = (n: number, state: string) => ({
  stall_id: uuid(n),
  state,
  amount_soum: 22_000,
  unavailable_reason: null,
  paid_soum: state === "paid" ? 22_000 : 0,
  remaining_soum: state === "paid" ? 0 : 22_000,
  open_case_id: null,
  open_case_service_date: null,
});

const summary = (planned: number, ok: number, missed: number) => ({
  planned,
  done: ok,
  ok,
  dark: 0,
  blank: 0,
  corrupt: 0,
  failed: 0,
  missed,
});

const SETUP = {
  zones: 1, categories: 1, tariffs_covered: 1, categories_total: 1, stalls: 26,
  stalls_with_category: 26, vendors: 20, calendar_configured: true, cameras: 16,
  can_activate: true, blocking: [],
};

function route(opts: { liveToday: number; liveWeekAgo: number; liveYesterday?: number }) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    const url = new URL(path, "http://x");
    if (path.startsWith("/reports/live")) {
      const from = url.searchParams.get("from") ?? "";
      const value =
        from === "2026-10-16"
          ? opts.liveToday
          : from === "2026-10-15"
            ? (opts.liveYesterday ?? 0)
            : opts.liveWeekAgo;
      return Promise.resolve(live(from, value));
    }
    if (path.startsWith("/billing/map")) {
      return Promise.resolve({
        service_date: "2026-10-16",
        market_active: true,
        market_open: true,
        rows: [mapRow(1, "paid"), mapRow(2, "paid"), mapRow(3, "due"), mapRow(4, "mismatch"), mapRow(5, "free")],
      });
    }
    if (path.startsWith("/reports/debtors")) {
      return Promise.resolve({
        from_date: "2026-09-17",
        to_date: "2026-10-15",
        rows: [
          { vendor_id: uuid(50), vendor_name: "Alisher", stall_codes: ["3"], outstanding_soum: 40_000, oldest_debt_date: "2026-10-02" },
          { vendor_id: uuid(51), vendor_name: "Avans", stall_codes: ["7"], outstanding_soum: -10_000, oldest_debt_date: null },
        ],
        total_outstanding_soum: 30_000,
        row_count: 2,
        shown_count: 2,
      });
    }
    if (path.startsWith("/markets/")) return Promise.resolve(SETUP);
    if (path.startsWith("/capture-runs")) {
      const day = url.searchParams.get("day") ?? "";
      /* 12-oktabrdan beri kadr kelmaydi; bugun ertalabki slotlar ham yo'qoldi. */
      const down = day >= "2026-10-12";
      return Promise.resolve({
        day,
        summary: down ? summary(128, 0, day === "2026-10-16" ? 48 : 128) : summary(128, 120, 2),
        rows: [],
        archived_present: false,
      });
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

let client: QueryClient;

function renderKpis(period: { kind: "today" | "yesterday"; from: string; to: string }) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: ["director"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      marketIsActive: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} now={NOW} timeZone="Asia/Tashkent">
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DirectorKpis period={period} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("kadr kelmagan ketma-ket kunlar", () => {
  const day = (planned: number, ok: number, lost: number) => ({ planned, ok, poor: 0, lost });

  test("bugun va undan oldingi kunlar sanaladi, kadr kelgan kunda to'xtaydi", () => {
    expect(daysWithoutFrames([day(8, 8, 0), day(8, 0, 8), day(8, 0, 8), day(8, 0, 3)])).toBe(3);
  });

  test("bugun hali hech narsa yo'qolmagan bo'lsa (kun boshi) — bugun SANALMAYDI", () => {
    expect(daysWithoutFrames([day(8, 8, 0), day(8, 0, 8), day(8, 0, 0)])).toBe(1);
  });

  test("jadval qoplamagan kun zanjirni uzadi, hammasi joyida — 0", () => {
    expect(daysWithoutFrames([day(8, 0, 8), day(0, 0, 0), day(8, 0, 8)])).toBe(1);
    expect(daysWithoutFrames([day(8, 7, 1), day(8, 8, 0)])).toBe(0);
  });
});

describe("to'rt katak", () => {
  test("BUGUN: summa va o'tgan hafta shu kuni — FOIZSIZ (kun tugamagan)", async () => {
    route({ liveToday: 357_000, liveWeekAgo: 1_245_000 });
    renderKpis(TODAY);

    expect(await screen.findByText("O'tgan hafta shu kuni: 1 245 000 so'm")).toBeInTheDocument();
    expect(screen.getByText("357 000")).toBeInTheDocument();
    /* ⛔ Kun boshidagi «−71.3%» yolg'on xavotiri qaytmaydi. */
    expect(screen.queryByText(/%$/)).toBeNull();
  });

  test("KECHA (yopilgan kun): foiz ko'rinadi", async () => {
    route({ liveToday: 0, liveWeekAgo: 1_000_000, liveYesterday: 1_200_000 });
    renderKpis(YESTERDAY);

    expect(await screen.findByText("↑ +20.0%")).toBeInTheDocument();
  });

  test("rastalar: «to'lagan / kutilgan» va to'lamaganlar oddiy gap bilan", async () => {
    route({ liveToday: 0, liveWeekAgo: 0 });
    renderKpis(TODAY);

    expect(await screen.findByText("2 / 4")).toBeInTheDocument();
    expect(screen.getByText("2 ta rasta hali to'lamagan")).toBeInTheDocument();
  });

  test("qarz: server jami, faqat haqiqiy qarzdorlar sanaladi", async () => {
    route({ liveToday: 0, liveWeekAgo: 0 });
    renderKpis(TODAY);

    expect(await screen.findByText("30 000")).toBeInTheDocument();
    expect(screen.getByText(/^1 sotuvchida · eng eski: 2-oktabr, 2026$/u)).toBeInTheDocument();
  });

  test("kameralar: «0 / 128 kadr» va necha kundan beri kadr yo'q", async () => {
    route({ liveToday: 0, liveWeekAgo: 0 });
    renderKpis(TODAY);

    expect(await screen.findByText("5 kundan beri kadr kelmayapti")).toBeInTheDocument();
    expect(screen.getByText(D.kpiCamera)).toBeInTheDocument();
  });
});
