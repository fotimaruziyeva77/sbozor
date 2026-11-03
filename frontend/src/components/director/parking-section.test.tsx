/**
 * PANELDAGI AVTOTURARGOH BO'LIMI — kimga, qachon va nima ko'rinadi (261103).
 *
 * =============================================================================
 * ⛔ Bo'lim agentning «Statistika» ekranini panelga olib keladi: olti katak,
 *    soatlar bo'yicha oqim (06:00 dan), chiqish turlari va ko'p kunlik davrda
 *    kunlar bo'yicha tushum. Bu fayl uchta da'voni o'lchaydi:
 *
 *    1. HUQUQ VA OBYEKT SO'ROVDAN OLDIN: `camera_view` siz sessiyada so'rov
 *       ketmaydi; avtoturargohsiz bozorda bo'lim umuman chizilmaydi.
 *    2. SONLAR SERVERDAN, seanslarsiz yig'indidan (`sessions=0`).
 *    3. ISH KUNI 06:00 DA: soatlar 06 dan boshlanadi, tunda «bugun» uchun
 *       so'rov ketmaydi (server uni kelajak deb rad etardi).
 *
 * ⛔ jsdom'da `ResponsiveContainer` 0×0 — grafik geometriyasi brauzerda
 *    ko'rildi; bu yerda legenda, jadval egizagi va sonlar o'lchanadi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
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
    className,
  }: {
    children: ReactNode;
    href: string;
    className?: string;
  }) => (
    <a className={className} href={href}>
      {children}
    </a>
  ),
}));

import messages from "../../../messages/uz-Latn.json";
import { DirectorParking } from "@/components/director/parking-section";
import { parkingRange } from "@/components/director/use-panel-parking";
import { edgeParkingReportSchema } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const D = messages.director;
const P = messages.parkingReport;
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SITE_ID = "parking-karmana01";
/* 2026-11-03 12:00 Toshkent — avtoturargoh ish kuni ham 3-noyabr. */
const NOW = new Date("2026-11-03T07:00:00Z");
const TODAY = { kind: "today" as const, from: "2026-11-03", to: "2026-11-03" };
const YESTERDAY = { kind: "yesterday" as const, from: "2026-11-02", to: "2026-11-02" };
const WEEK = { kind: "week" as const, from: "2026-10-28", to: "2026-11-03" };

const SITES = {
  items: [
    {
      id: "market-camera01",
      kind: "market",
      name: "Rastalar kamerasi",
      created_at: "2026-09-01T00:00:00Z",
      config_version: 1,
      setup: { devices: [], lanes: [] },
      agent: null,
    },
    {
      id: SITE_ID,
      kind: "parking",
      name: "Karmana avtoturargohi",
      created_at: "2026-10-30T00:00:00Z",
      config_version: 3,
      setup: { devices: [], lanes: [] },
      agent: null,
    },
  ],
};

function report(from: string, to: string) {
  const days: string[] = [];
  for (let day = new Date(`${from}T00:00:00Z`); day.toISOString().slice(0, 10) <= to; ) {
    days.push(day.toISOString().slice(0, 10));
    day = new Date(day.getTime() + 86_400_000);
  }
  return {
    site_id: SITE_ID,
    site_name: "Karmana avtoturargohi",
    from_date: from,
    to_date: to,
    days: days.map((date) => ({
      date,
      entries: 42,
      exits: 38,
      cash: 126_000,
      terminal: 30_000,
      total: 156_000,
      free_count: 4,
    })),
    total: {
      entries: 42,
      exits: 38,
      cash: 126_000,
      terminal: 30_000,
      total: 156_000,
      free_count: 4,
    },
    sessions: [],
    /* Soat 07 — eng gavjum; 02:00 dagi bitta kirish ham bor (tun ish kunining oxiri). */
    hours: Array.from({ length: 24 }, (_, hour) => ({
      hour,
      entries: hour === 7 ? 12 : hour === 2 ? 1 : hour >= 8 && hour <= 16 ? 3 : 0,
      exits: hour >= 9 && hour <= 18 ? 3 : 0,
    })),
    stay: {
      measured: 38,
      median_minutes: 135,
      buckets: [
        { key: "under_15m", count: 2 },
        { key: "under_1h", count: 8 },
        { key: "under_2h", count: 8 },
        { key: "under_4h", count: 16 },
        { key: "under_8h", count: 4 },
        { key: "over_8h", count: 0 },
      ],
      unrecorded_entries: 0,
    },
    exit_reasons: [
      { reason: "paid", count: 30 },
      { reason: "online", count: 0 },
      { reason: "free", count: 4 },
      { reason: "exempt", count: 2 },
      { reason: "manual", count: 2 },
    ],
    inside: 4,
    paid_sessions: 30,
    average_check_soum: 5_200,
    regulars: [],
  };
}

type Routes = { sites?: unknown; report?: "ok" | "error" };

function route({ sites = SITES, report: mode = "ok" }: Routes = {}): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path === "/edge-sites") return Promise.resolve(sites);
    if (path.startsWith(`/edge-sites/${SITE_ID}/parking-report?`)) {
      if (mode === "error") return Promise.reject(new Error("tarmoq"));
      const params = new URL(path, "http://x").searchParams;
      return Promise.resolve(report(params.get("from") ?? "", params.get("to") ?? ""));
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function requested(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderSection(
  period: { kind: "today" | "yesterday" | "week"; from: string; to: string },
  { roles = ["director"], now = NOW }: { roles?: readonly string[]; now?: Date } = {},
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
      marketName: "Karmana bozor",
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
          <DirectorParking period={period} />
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

describe("avtoturargoh bo'limi", () => {
  test("fikstura serverning javob sxemasiga mos (zod)", () => {
    expect(edgeParkingReportSchema.safeParse(report("2026-11-03", "2026-11-03")).success).toBe(
      true,
    );
  });

  test("huquqsiz sessiyada (buxgalter) bo'lim YO'Q va so'rov KETMAYDI", async () => {
    route();
    const { container } = renderSection(TODAY, { roles: ["accountant"] });

    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(requested()).toEqual([]);
  });

  test("avtoturargohsiz bozorda bo'lim chizilmaydi, hisobot so'ralmaydi", async () => {
    route({ sites: { items: [SITES.items[0]] } });
    const { container } = renderSection(TODAY);

    await waitFor(() => expect(requested()).toContain("/edge-sites"));
    /* Javob KELGANDAN keyin ham bo'sh — so'rov paytidagi bo'shliq emas. */
    await waitFor(() => expect(client.isFetching()).toBe(0));
    expect(container).toBeEmptyDOMElement();
    expect(requested().some((path) => path.includes("/parking-report"))).toBe(false);
  });

  test("bugun: olti katak serverdan, seanslarsiz so'rov, to'liq hisobotga havola", async () => {
    route();
    renderSection(TODAY);

    const section = await screen.findByRole("region", { name: D.parkingTitle });
    expect(await within(section).findByText("Karmana avtoturargohi · 3-noyabr, 2026 · kun 06:00 da boshlanadi")).toBeInTheDocument();

    expect(within(section).getByText("42")).toBeInTheDocument();
    expect(within(section).getByText("38")).toBeInTheDocument();
    /* Davr joriy ish kuni bilan tugaydi — «Hozir ichkarida». */
    expect(within(section).getByText(D.parkingInsideNow)).toBeInTheDocument();
    expect(within(section).getByText("156 000")).toBeInTheDocument();
    expect(within(section).getByText("Naqd 126 000 · Terminal 30 000")).toBeInTheDocument();
    expect(within(section).getByText("5 200")).toBeInTheDocument();
    expect(within(section).getByText("30 ta to'lov")).toBeInTheDocument();
    expect(within(section).getByText("2 soat 15 daq")).toBeInTheDocument();
    expect(within(section).getByText("Eng gavjum: 07:00–08:00")).toBeInTheDocument();

    /* Bir kunlik davr: soatlar va chiqish turlari bor, kunlar grafigi YO'Q. */
    expect(within(section).getByRole("heading", { name: P.hourly.title })).toBeInTheDocument();
    expect(within(section).getByRole("heading", { name: P.exitReasons.title })).toBeInTheDocument();
    expect(within(section).queryByRole("heading", { name: P.daily.title })).toBeNull();

    const link = within(section).getByRole("link", { name: new RegExp(D.parkingOpen, "u") });
    expect(link).toHaveAttribute("href", "/parking?from=2026-11-03&to=2026-11-03");
    expect(requested()).toContain(
      `/edge-sites/${SITE_ID}/parking-report?from=2026-11-03&to=2026-11-03&sessions=0`,
    );
  });

  test("soatlar ish kuni tartibida: 06:00 birinchi, 05:00 oxirgi", async () => {
    route();
    renderSection(TODAY);

    const table = await screen.findByRole("table", { name: P.hourly.title });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(24);
    expect(rows[0]?.textContent).toContain("06:00–07:00");
    expect(rows[18]?.textContent).toContain("00:00–01:00");
    expect(rows[23]?.textContent).toContain("05:00–06:00");
  });

  test("7 kun: kunlar bo'yicha tushum grafigi qo'shiladi", async () => {
    route();
    renderSection(WEEK);

    const section = await screen.findByRole("region", { name: D.parkingTitle });
    expect(await within(section).findByRole("heading", { name: P.daily.title })).toBeInTheDocument();
    expect(requested()).toContain(
      `/edge-sites/${SITE_ID}/parking-report?from=2026-10-28&to=2026-11-03&sessions=0`,
    );
  });

  test("o'tgan kun: «Hozir» deyilmaydi — o'tgan davrda bu so'z yolg'on", async () => {
    route();
    renderSection(YESTERDAY);

    const section = await screen.findByRole("region", { name: D.parkingTitle });
    expect(await within(section).findByText(P.flow.inside)).toBeInTheDocument();
    expect(within(section).queryByText(D.parkingInsideNow)).toBeNull();
  });

  test("hisobot yiqilsa xato nomlanadi va qayta urinish tugmasi bor", async () => {
    route({ report: "error" });
    renderSection(TODAY);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages.common.retry })).toBeInTheDocument();
  });

  test("tunda (02:00) «bugun» boshlanmagan: sabab aytiladi, hisobot so'ralmaydi", async () => {
    route();
    /* 2026-11-03 02:00 Toshkent — avtoturargoh ish kuni hali 2-noyabr. */
    renderSection(TODAY, { now: new Date("2026-11-02T21:00:00Z") });

    expect(await screen.findByText(D.parkingNotStarted)).toBeInTheDocument();
    expect(requested().some((path) => path.includes("/parking-report"))).toBe(false);
  });
});

describe("panel davri -> avtoturargoh davri", () => {
  test("oxiri ish kunidan keyin bo'lsa qisqaradi; butunlay keyin bo'lsa — null", () => {
    expect(parkingRange({ from: "2026-10-28", to: "2026-11-03" }, "2026-11-02")).toEqual({
      from: "2026-10-28",
      to: "2026-11-02",
    });
    expect(parkingRange({ from: "2026-11-03", to: "2026-11-03" }, "2026-11-02")).toBeNull();
    expect(parkingRange({ from: "2026-11-01", to: "2026-11-02" }, "2026-11-03")).toEqual({
      from: "2026-11-01",
      to: "2026-11-02",
    });
  });
});
