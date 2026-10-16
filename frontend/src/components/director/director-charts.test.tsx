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

describe("Tushum dinamikasi", () => {
  test("legenda davr YIG'INDISINI serverdan oladi, jadvalda har kun bor", async () => {
    route({
      "/reports/revenue": {
        from_date: "2026-10-09",
        to_date: "2026-10-15",
        rows: Array.from({ length: 7 }, (_, i) => ({
          business_date: `2026-10-${String(9 + i).padStart(2, "0")}`,
          charged_soum: 100_000,
          collected_soum: 90_000,
          diff_soum: -10_000,
        })),
        /* ⛔ Ataylab qatorlar yig'indisidan FARQLI: legenda serverni ko'rsatishi shart. */
        total_collected_soum: 777_000,
        total_charged_soum: 700_000,
        row_count: 7,
        shown_count: 7,
      },
    });
    renderWith(<RevenueTrend />);

    /* ⚠ Guruh ajratgichi NBSP; testing-library matnni oddiy bo'shliqqa keltiradi. */
    expect(await screen.findByText("777 000 so'm")).toBeInTheDocument();
    expect(screen.getByText("700 000 so'm")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(1 + 7);
    expect(requested()).toContain("/reports/revenue?from=2026-10-09&to=2026-10-15");
  });
});
