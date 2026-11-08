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
import { DirectorKpis, daysWithoutFrames, revenueTotals } from "@/components/director/kpi-row";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const D = messages.director;
const NOW = new Date("2026-10-16T07:00:00Z");
const TODAY = { kind: "today" as const, from: "2026-10-16", to: "2026-10-16" };
const YESTERDAY = { kind: "yesterday" as const, from: "2026-10-15", to: "2026-10-15" };

const uuid = (n: number) => `30000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

const live = (
  from: string,
  collected: number,
  parts?: { stall: number; fee: number },
) => ({
  from_date: from,
  to_date: from,
  total_collected_soum: collected,
  total_charged_soum: 0,
  charged_complete: false,
  collected_cash_soum: collected,
  collected_terminal_soum: 0,
  ...(parts === undefined
    ? {}
    : { collected_stall_soum: parts.stall, collected_fee_soum: parts.fee }),
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

function route(opts: {
  liveToday: number;
  liveWeekAgo: number;
  liveYesterday?: number;
  parts?: { stall: number; fee: number };
}) {
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
      return Promise.resolve(
        live(from, value, from === "2026-10-16" ? opts.parts : undefined),
      );
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

function renderKpis(
  period: { kind: "today" | "yesterday"; from: string; to: string },
  now: Date = NOW,
  roles: readonly string[] = ["director"],
) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      marketIsActive: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} now={now} timeZone="Asia/Tashkent">
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

describe("buxgalter paneli: umumiy, patta va tarozi (261108)", () => {
  test("uchala son alohida katakda, ikkalasi ham serverdan", async () => {
    route({
      liveToday: 1_124_000,
      liveWeekAgo: 0,
      parts: { stall: 1_004_000, fee: 120_000 },
    });
    renderKpis(TODAY, NOW, ["accountant"]);

    expect(await screen.findByText("1 124 000")).toBeInTheDocument();
    expect(screen.getByText("1 004 000")).toBeInTheDocument();
    expect(screen.getByText("120 000")).toBeInTheDocument();
    expect(screen.getByText(D.kpiTotalMoney)).toBeInTheDocument();
    expect(screen.getByText(D.kpiStallMoney)).toBeInTheDocument();
    expect(screen.getByText(D.kpiFeeMoney)).toBeInTheDocument();
    expect(screen.queryByText(D.kpiRevenue)).toBeNull();
  });

  test("direktor paneli o'zgarmaydi", async () => {
    route({
      liveToday: 1_124_000,
      liveWeekAgo: 0,
      parts: { stall: 1_004_000, fee: 120_000 },
    });
    renderKpis(TODAY);

    expect(await screen.findByText("1 124 000")).toBeInTheDocument();
    expect(screen.getByText(D.kpiRevenue)).toBeInTheDocument();
    expect(screen.queryByText(D.kpiStallMoney)).toBeNull();
    expect(screen.queryByText(D.kpiFeeMoney)).toBeNull();
  });

  test("server bo'linishni bermasa nol emas, «—» yoziladi", async () => {
    route({ liveToday: 1_124_000, liveWeekAgo: 0 });
    renderKpis(TODAY, NOW, ["accountant"]);

    expect(await screen.findByText("1 124 000")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
  });
});

/* -------------------------------------------------------------------------- */
/* 261103: Tushum = rastalar + avtoturargoh                                   */
/* -------------------------------------------------------------------------- */

const PARKING_SITE_ID = "parking-karmana01";

const PARKING_SITES = {
  items: [
    {
      id: PARKING_SITE_ID,
      kind: "parking",
      name: "Karmana avtoturargohi",
      created_at: "2026-10-01T00:00:00Z",
      config_version: 1,
      setup: { devices: [], lanes: [] },
      agent: null,
    },
  ],
};

function parkingReport(day: string, total: number) {
  return {
    site_id: PARKING_SITE_ID,
    site_name: "Karmana avtoturargohi",
    from_date: day,
    to_date: day,
    days: [{ date: day, entries: 40, exits: 38, cash: total, terminal: 0, total, free_count: 2 }],
    total: { entries: 40, exits: 38, cash: total, terminal: 0, total, free_count: 2 },
    sessions: [],
    hours: Array.from({ length: 24 }, (_, hour) => ({ hour, entries: 0, exits: 0 })),
    stay: { measured: 0, median_minutes: null, buckets: [], unrecorded_entries: 0 },
    exit_reasons: [],
    inside: 2,
    paid_sessions: 30,
    average_check_soum: 5_000,
    regulars: [],
  };
}

/** Avtoturargoh marshrutlari `route()` ning USTIGA; `byDay` da yo'q kun — rad. */
function routeParking(byDay: Record<string, number>): void {
  const base = apiClientMock.apiFetch.getMockImplementation();
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path === "/edge-sites") return Promise.resolve(PARKING_SITES);
    if (path.startsWith(`/edge-sites/${PARKING_SITE_ID}/parking-report?`)) {
      const from = new URL(path, "http://x").searchParams.get("from") ?? "";
      const total = byDay[from];
      return total === undefined
        ? Promise.reject(new Error("422 report_period_too_long"))
        : Promise.resolve(parkingReport(from, total));
    }
    return base === undefined ? Promise.reject(new Error(path)) : base(path);
  });
}

function parkingRequests(): string[] {
  return apiClientMock.apiFetch.mock.calls
    .map((call) => String(call[0]))
    .filter((path) => path.includes("/parking-report"));
}

describe("tushum — rastalar + avtoturargoh", () => {
  test("katakda JAMI, ostida bo'linish; taqqoslash ham JAMI bilan", async () => {
    route({ liveToday: 357_000, liveWeekAgo: 1_245_000 });
    routeParking({ "2026-10-16": 150_000, "2026-10-09": 100_000 });
    renderKpis(TODAY);

    expect(await screen.findByText("507 000")).toBeInTheDocument();
    expect(screen.getByText("Rastalar 357 000")).toBeInTheDocument();
    expect(screen.getByText("Avtoturargoh 150 000")).toBeInTheDocument();
    /* O'tgan hafta shu kuni ham jami: 1 245 000 + 100 000. */
    expect(await screen.findByText("O'tgan hafta shu kuni: 1 345 000 so'm")).toBeInTheDocument();
    /* ⛔ Seanslarsiz yig'indi — panelga mashinalar ro'yxati kerak emas. */
    expect(parkingRequests()).toContain(
      `/edge-sites/${PARKING_SITE_ID}/parking-report?from=2026-10-16&to=2026-10-16&sessions=0`,
    );
  });

  test("avtoturargoh so'rovi yiqilsa — katak bugungi holicha (faqat rastalar)", async () => {
    route({ liveToday: 357_000, liveWeekAgo: 1_245_000 });
    routeParking({});
    renderKpis(TODAY);

    expect(await screen.findByText("357 000")).toBeInTheDocument();
    expect(screen.getByText("O'tgan hafta shu kuni: 1 245 000 so'm")).toBeInTheDocument();
    expect(screen.queryByText(/^Avtoturargoh/u)).toBeNull();
  });

  test("tunda (02:00) avtoturargoh kuni boshlanmagan: bugun uchun so'rov YO'Q, qismi 0", async () => {
    route({ liveToday: 357_000, liveWeekAgo: 1_245_000 });
    routeParking({ "2026-10-09": 100_000 });
    /* 2026-10-16 02:00 Toshkent — kalendar «bugun», avtoturargoh kuni hali 15-oktabr. */
    renderKpis(TODAY, new Date("2026-10-15T21:00:00Z"));

    expect(await screen.findByText("357 000")).toBeInTheDocument();
    expect(screen.getByText("Avtoturargoh 0")).toBeInTheDocument();
    expect(parkingRequests().some((path) => path.includes("from=2026-10-16"))).toBe(false);
  });
});

describe("jami tushum hisobi", () => {
  test("avtoturargoh yo'q (null) — bugungi holicha: faqat rastalar", () => {
    expect(revenueTotals(100, null, 80, 5)).toEqual({ current: 100, previous: 80 });
  });

  test("avtoturargoh bor — ikkala davr ham JAMI; oldingisi noma'lum bo'lsa taqqoslash yo'q", () => {
    expect(revenueTotals(100, 20, 80, 5)).toEqual({ current: 120, previous: 85 });
    expect(revenueTotals(100, 20, 80, null)).toEqual({ current: 120, previous: null });
    expect(revenueTotals(null, 20, 80, 5)).toEqual({ current: null, previous: 85 });
  });
});
