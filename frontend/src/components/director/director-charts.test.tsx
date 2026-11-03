/**
 * DIREKTOR PANELI GRAFIKLARI — nima ko'rinadi, nima ko'rinmaydi (261016).
 *
 * =============================================================================
 * ⛔ jsdom JOYLASHUVNI HISOBLAMAYDI: `ResponsiveContainer` 0×0 o'lchaydi va
 *    SVG ichini chizmaydi. Shuning uchun bu fayl SVG geometriyasini emas,
 *    grafik bilan BIRGA chiqadigan va o'qiladigan qismlarni o'lchaydi:
 *    legenda, markaz yozuvi, qatorlar va jadval egizagi. Geometriya
 *    brauzerda ko'zdan kechirildi.
 *
 * ⛔ SO'ROVLAR `apiFetch` darajasida yo'naltiriladi — kutilmagan yo'l RAD
 *    ETILADI, ya'ni komponent yangi so'rov qo'shsa test buni ko'rsatadi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
import { CaptureWeek } from "@/components/director/capture-week";
import { PaymentMix } from "@/components/director/payment-mix";
import { RevenueTrend } from "@/components/director/revenue-trend";
import { StallDayCard } from "@/components/director/stall-day-card";
import { TopDebtors } from "@/components/director/top-debtors";
import { liveRevenueSchema } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const D = messages.director;
/* 2026-10-16 12:00 Toshkent — biznes-kun 2026-10-16. */
const NOW = new Date("2026-10-16T07:00:00Z");
const TODAY = { kind: "today" as const, from: "2026-10-16", to: "2026-10-16" };

const uuid = (n: number) => `20000000-0000-4000-8000-${String(n).padStart(12, "0")}`;

type Routes = Record<string, unknown>;

function route(routes: Routes): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    for (const [prefix, body] of Object.entries(routes)) {
      if (path.startsWith(prefix)) {
        return typeof body === "function"
          ? Promise.resolve((body as (p: string) => unknown)(path))
          : Promise.resolve(body);
      }
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function requested(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderWith(ui: ReactNode, roles: readonly string[] = ["director"]) {
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
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>{ui}</AuthProvider>
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

/* -------------------------------------------------------------------------- */

const liveRevenue = (cash: number, terminal: number) => ({
  from_date: "2026-10-16",
  to_date: "2026-10-16",
  total_collected_soum: cash + terminal,
  total_charged_soum: 0,
  charged_complete: false,
  collected_cash_soum: cash,
  collected_terminal_soum: terminal,
});

describe("To'lov turlari", () => {
  test("ikki qism SON bilan va ulushi bilan — foizlar yig'indisi 100", async () => {
    route({ "/reports/live": liveRevenue(31_400_000, 17_200_000) });
    renderWith(<PaymentMix period={TODAY} />);

    expect(await screen.findByText(D.methodCash)).toBeInTheDocument();
    expect(screen.getByText(D.methodTerminal)).toBeInTheDocument();
    expect(screen.getByText("64.6%")).toBeInTheDocument();
    expect(screen.getByText("35.4%")).toBeInTheDocument();
  });

  test("storno qismni MANFIY qilsa ulush chizilmaydi, sabab yoziladi", async () => {
    route({ "/reports/live": liveRevenue(12_000, -4_000) });
    renderWith(<PaymentMix period={TODAY} />);

    expect(await screen.findByText(D.methodNoShare)).toBeInTheDocument();
    expect(screen.queryByText(/%$/)).not.toBeInTheDocument();
  });

  test("eski server (maydonlarsiz) — karta «yuklanmadi» deydi, javob rad etilmaydi", async () => {
    const old: Record<string, unknown> = { ...liveRevenue(1_000, 0) };
    delete old.collected_cash_soum;
    delete old.collected_terminal_soum;
    /* ⛔ Sxema eski javobni RAD ETMAYDI — aks holda bosh katak ham sinardi. */
    expect(liveRevenueSchema.safeParse(old).success).toBe(true);

    route({ "/reports/live": old });
    renderWith(<PaymentMix period={TODAY} />);

    expect(await screen.findByText(D.chartLoadError)).toBeInTheDocument();
  });

  test("davrda pul yo'q — «to'lov yozilmagan», nol foiz emas", async () => {
    route({ "/reports/live": liveRevenue(0, 0) });
    renderWith(<PaymentMix period={TODAY} />);

    expect(await screen.findByText(D.methodEmpty)).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */

const mapRow = (n: number, state: string) => ({
  stall_id: uuid(n),
  state,
  amount_soum: state === "no_billing" ? null : 4000,
  unavailable_reason: null,
  paid_soum: state === "paid" ? 4000 : 0,
  remaining_soum: state === "no_billing" ? null : state === "paid" ? 0 : 4000,
  open_case_id: null,
  open_case_service_date: null,
});

const BILLING_MAP = {
  service_date: "2026-10-16",
  market_active: true,
  market_open: true,
  rows: [
    mapRow(1, "paid"),
    mapRow(2, "paid"),
    mapRow(3, "due"),
    mapRow(4, "mismatch"),
    mapRow(5, "free"),
  ],
};

const cell = (n: number) => ({
  id: uuid(n),
  code: String(n),
  status: "active",
  has_vendor: true,
  plan_x: null,
  plan_y: null,
});

describe("Bugungi rastalar holati", () => {
  test("markazda «to'langan / kutilgan», sotuvchisiz rasta maxrajga KIRMAYDI", async () => {
    route({
      "/billing/map": BILLING_MAP,
      "/stalls/map": { zones: [{ id: uuid(90), name: "Asosiy", cells: [1, 2, 3, 4, 5].map(cell) }] },
    });
    renderWith(<StallDayCard />);

    expect(await screen.findByText("2 / 4")).toBeInTheDocument();
    expect(screen.getByText(D.stallPaidCaption)).toBeInTheDocument();

    const legend = screen.getByText(D.stallFree).closest("li");
    expect(legend).not.toBeNull();
    expect(within(legend as HTMLElement).getByText("1")).toBeInTheDocument();
  });

  test("bitta zonali bozorda zona kesimi CHIQMAYDI (donutning takrori bo'lardi)", async () => {
    route({
      "/billing/map": BILLING_MAP,
      "/stalls/map": { zones: [{ id: uuid(90), name: "Asosiy", cells: [1, 2, 3, 4, 5].map(cell) }] },
    });
    renderWith(<StallDayCard />);

    await screen.findByText("2 / 4");
    expect(screen.queryByText(D.stallByZone)).not.toBeInTheDocument();
  });

  test("ikki zonada har zonaning o'z sanog'i ko'rinadi", async () => {
    route({
      "/billing/map": BILLING_MAP,
      "/stalls/map": {
        zones: [
          { id: uuid(90), name: "Oziq-ovqat", cells: [1, 2, 3].map(cell) },
          { id: uuid(91), name: "Kiyim-kechak", cells: [4, 5].map(cell) },
        ],
      },
    });
    renderWith(<StallDayCard />);

    expect(await screen.findByText(D.stallByZone)).toBeInTheDocument();
    expect(screen.getByText("Oziq-ovqat")).toBeInTheDocument();
    expect(screen.getByText("2 / 3 to'langan")).toBeInTheDocument();
    expect(screen.getByText("0 / 1 to'langan")).toBeInTheDocument();
  });

  test("huquqsiz sessiyada karta YO'Q va so'rov KETMAYDI", async () => {
    route({});
    const { container } = renderWith(<StallDayCard />, ["inspector"]);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
    expect(requested()).toEqual([]);
  });
});

/* -------------------------------------------------------------------------- */

const debtorRow = (n: number, outstanding: number, name: string | null) => ({
  vendor_id: uuid(100 + n),
  vendor_name: name,
  stall_codes: [String(n)],
  outstanding_soum: outstanding,
  oldest_debt_date: "2026-10-10",
});

describe("Eng katta qarzdorlar", () => {
  test("katta qarz birinchi, avans ro'yxatga TUSHMAYDI, ortgani sanaladi", async () => {
    const rows = [
      debtorRow(1, 40_000, "Alisher"),
      debtorRow(2, -90_000, "Avansli"),
      ...Array.from({ length: 7 }, (_, i) => debtorRow(10 + i, 10_000 + i, `Sotuvchi ${i}`)),
    ];
    route({
      "/reports/debtors": {
        from_date: "2026-09-16",
        to_date: "2026-10-15",
        rows,
        total_outstanding_soum: 0,
        row_count: rows.length,
        shown_count: rows.length,
      },
    });
    renderWith(<TopDebtors period={TODAY} />);

    const items = await screen.findAllByRole("listitem");
    expect(items).toHaveLength(6);
    expect(within(items[0] as HTMLElement).getByText("Alisher")).toBeInTheDocument();
    expect(screen.queryByText("Avansli")).not.toBeInTheDocument();
    /* 8 ta musbat qarzdor, 6 tasi ko'rinadi. */
    expect(screen.getByText("Yana 2 ta qarzdor bor.")).toBeInTheDocument();
    /* Oyna oxiri KECHA — bugun 422 bilan rad etilardi. */
    expect(requested()).toContain("/reports/debtors?from=2026-09-17&to=2026-10-15");
  });

  test("ismsiz sotuvchi rasta raqami bilan nomlanadi — «Noma'lum» to'qilmaydi", async () => {
    route({
      "/reports/debtors": {
        from_date: "2026-09-17",
        to_date: "2026-10-15",
        rows: [debtorRow(3, 8_000, null)],
        total_outstanding_soum: 8_000,
        row_count: 1,
        shown_count: 1,
      },
    });
    renderWith(<TopDebtors period={TODAY} />);

    expect(await screen.findByText("Rastalar: 3")).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */

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

describe("Kamera kadrlari", () => {
  test("bugungi «olindi / reja» va yetti kunlik jadval egizagi", async () => {
    route({
      "/markets/": { cameras: 16, zones: 1, categories: 1, tariffs_covered: 1, categories_total: 1, stalls: 26, stalls_with_category: 26, vendors: 20, calendar_configured: true, can_activate: true, blocking: [] },
      "/capture-runs": (path: string) => {
        const day = new URL(path, "http://x").searchParams.get("day") ?? "";
        return {
          day,
          summary: day === "2026-10-16" ? summary(128, 96, 0) : summary(128, 0, 128),
          rows: [],
          archived_present: false,
        };
      },
    });
    renderWith(<CaptureWeek />);

    expect(await screen.findByText("96 / 128 kadr")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 7);
  });

  test("kamerasiz bozorda karta YO'Q", async () => {
    route({
      "/markets/": { cameras: 0, zones: 1, categories: 1, tariffs_covered: 1, categories_total: 1, stalls: 26, stalls_with_category: 26, vendors: 20, calendar_configured: true, can_activate: true, blocking: [] },
      "/capture-runs": { day: "2026-10-16", summary: summary(0, 0, 0), rows: [], archived_present: false },
    });
    const { container } = renderWith(<CaptureWeek />);

    await waitFor(() =>
      expect(requested().some((path) => path.includes("/setup-status"))).toBe(true),
    );
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

/* -------------------------------------------------------------------------- */

/*
 * ⛔ 261103: karta qayta qurildi (buyurtmachi: «tushunarsiz bo'lib qoldi»).
 *    Endi u BITTA savolga javob beradi — «qancha pul tushdi?»: tepada davr
 *    jami va o'rtacha, ustunlar «Rastalar» + «Avtoturargoh». «Hisoblangan»
 *    chizig'i bu kartada YO'Q (u «Tekshiruv uchun» tabida).
 */
const PARKING_SITE_ID = "parking-karmana01";

const REVENUE_WEEK = {
  from_date: "2026-10-09",
  to_date: "2026-10-15",
  rows: Array.from({ length: 7 }, (_, i) => ({
    business_date: `2026-10-${String(9 + i).padStart(2, "0")}`,
    charged_soum: 100_000,
    collected_soum: 90_000,
    diff_soum: -10_000,
  })),
  /* ⛔ Ataylab qatorlar yig'indisidan FARQLI: tepadagi jami serverni ko'rsatishi shart. */
  total_collected_soum: 777_000,
  total_charged_soum: 700_000,
  row_count: 7,
  shown_count: 7,
};

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

const parkingDay = (date: string, cash: number, terminal: number) => ({
  date,
  entries: 40,
  exits: 38,
  cash,
  terminal,
  total: cash + terminal,
  free_count: 3,
});

const PARKING_WEEK = {
  site_id: PARKING_SITE_ID,
  site_name: "Karmana avtoturargohi",
  from_date: "2026-10-09",
  to_date: "2026-10-15",
  days: Array.from({ length: 7 }, (_, i) =>
    parkingDay(`2026-10-${String(9 + i).padStart(2, "0")}`, 120_000, 30_000),
  ),
  /* ⛔ Bu ham qatorlar yig'indisidan FARQLI — legenda serverni ko'rsatadi. */
  total: { entries: 280, exits: 266, cash: 840_000, terminal: 210_000, total: 1_050_500, free_count: 21 },
  sessions: [],
  hours: Array.from({ length: 24 }, (_, hour) => ({ hour, entries: 0, exits: 0 })),
  stay: { measured: 0, median_minutes: null, buckets: [], unrecorded_entries: 0 },
  exit_reasons: [],
  inside: 2,
  paid_sessions: 240,
  average_check_soum: 4_377,
  regulars: [],
};

describe("Tushum dinamikasi", () => {
  test("avtoturargohsiz: tepada SERVER jami va kuniga o'rtacha, jadvalda har kun", async () => {
    route({ "/reports/revenue": REVENUE_WEEK });
    renderWith(<RevenueTrend />);

    /* ⚠ Guruh ajratgichi NBSP; testing-library matnni oddiy bo'shliqqa keltiradi. */
    expect(await screen.findByText("777 000")).toBeInTheDocument();
    expect(screen.getByText("Kuniga o'rtacha: 111 000 so'm")).toBeInTheDocument();
    /* Bitta qism — legenda yo'q (sarlavha nomlaydi), «Hisoblangan» ham yo'q. */
    expect(screen.queryByText(D.trendParking)).not.toBeInTheDocument();
    expect(screen.queryByText(D.charged)).not.toBeInTheDocument();
    expect(screen.queryByText("700 000 so'm")).not.toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 7);
    expect(within(table).getAllByRole("columnheader")).toHaveLength(2);
    expect(requested()).toContain("/reports/revenue?from=2026-10-09&to=2026-10-15");
    /* Direktorda avtoturargoh obyektlari so'raladi — ro'yxat rad etildi, karta sinmadi. */
    expect(requested()).toContain("/edge-sites");
  });

  test("avtoturargohli: jami = rastalar + avtoturargoh, legendada qismlar, jadvalda «Jami»", async () => {
    route({
      "/reports/revenue": REVENUE_WEEK,
      "/edge-sites/": PARKING_WEEK,
      "/edge-sites": PARKING_SITES,
    });
    renderWith(<RevenueTrend />);

    /* 777 000 + 1 050 500 — ikkala yig'indi ham SERVERDAN. */
    expect(await screen.findByText("1 827 500")).toBeInTheDocument();
    /* Legenda — qism nomi VA uning server yig'indisi (rang yolg'iz emas). */
    const legend = screen.getByRole("list");
    expect(within(legend).getByText(D.trendStalls)).toBeInTheDocument();
    expect(within(legend).getByText(D.trendParking)).toBeInTheDocument();
    expect(within(legend).getByText("777 000 so'm")).toBeInTheDocument();
    expect(within(legend).getByText("1 050 500 so'm")).toBeInTheDocument();
    /* 1 827 500 / 7 = 261 071,4 -> 261 071. */
    expect(screen.getByText("Kuniga o'rtacha: 261 071 so'm")).toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(4);
    const firstDay = within(table).getAllByRole("row")[1] as HTMLElement;
    expect(within(firstDay).getByText("150 000 so'm")).toBeInTheDocument();
    expect(within(firstDay).getByText("240 000 so'm")).toBeInTheDocument();

    /* ⛔ Panel seanslarsiz yig'indini so'raydi — mashinalar ro'yxati kerak emas. */
    expect(requested()).toContain(
      `/edge-sites/${PARKING_SITE_ID}/parking-report?from=2026-10-09&to=2026-10-15&sessions=0`,
    );
  });

  test("avtoturargoh so'rovi yiqilsa (422) — qism JIMGINA tushadi, karta sinmaydi", async () => {
    apiClientMock.apiFetch.mockImplementation((path: string) => {
      if (path.startsWith("/reports/revenue")) return Promise.resolve(REVENUE_WEEK);
      if (path === "/edge-sites") return Promise.resolve(PARKING_SITES);
      return Promise.reject(new Error("422 report_period_too_long"));
    });
    renderWith(<RevenueTrend />);

    expect(await screen.findByText("777 000")).toBeInTheDocument();
    expect(screen.queryByText(D.trendParking)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  test("12 hafta: oxirgi (tugamagan) hafta jadvalda «davom etmoqda» va izoh aytiladi", async () => {
    const days = Array.from({ length: 84 }, (_, i) => {
      const date = new Date(Date.UTC(2026, 6, 24 + i)).toISOString().slice(0, 10);
      return { business_date: date, charged_soum: 0, collected_soum: 10_000, diff_soum: 0 };
    });
    route({
      "/reports/revenue": {
        from_date: days[0]?.business_date,
        to_date: days[83]?.business_date,
        rows: days,
        total_collected_soum: 840_000,
        total_charged_soum: 0,
        row_count: 84,
        shown_count: 84,
      },
    });
    renderWith(<RevenueTrend />);

    fireEvent.click(await screen.findByRole("button", { name: D.range12w }));
    /* 840 000 / 12 hafta = 70 000. */
    expect(await screen.findByText("Haftasiga o'rtacha: 70 000 so'm")).toBeInTheDocument();
    expect(screen.getByText(D.trendFootPartial)).toBeInTheDocument();
    const rows = within(screen.getByRole("table")).getAllByRole("row");
    expect(rows[rows.length - 1]?.textContent).toContain(`(${D.trendPartialTip})`);
  });

  test("huquqsiz sessiyada (buxgalter) avtoturargoh SO'RALMAYDI", async () => {
    route({ "/reports/revenue": REVENUE_WEEK });
    renderWith(<RevenueTrend />, ["accountant"]);

    expect(await screen.findByText("777 000")).toBeInTheDocument();
    expect(requested().some((path) => path.startsWith("/edge-sites"))).toBe(false);
  });
});
