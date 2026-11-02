/**
 * AVTOTURARGOH HISOBOTI — nima ko'rinadi va qaysi so'rov ketadi (261102).
 *
 * =============================================================================
 * ⛔ jsdom JOYLASHUVNI HISOBLAMAYDI: `ResponsiveContainer` 0×0 va SVG ichi
 *    chizilmaydi. Shuning uchun grafik bilan BIRGA chiqadigan o'qiladigan
 *    qismlar o'lchanadi (legenda, jadval egizagi, sonlar); geometriya
 *    brauzerda ko'zdan kechirildi.
 *
 * ⛔ KADRLAR AUDITDA: galereya kadrni so'raydi (jsdom'da
 *    `IntersectionObserver` yo'q — darhol), jurnal esa FAQAT tugma
 *    bosilganda. So'rovlar `apiRequest` darajasida sanaladi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { ParkingReportWorkspace } from "@/components/parking/parking-report";
import { edgeParkingReportSchema } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn(), apiRequest: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

const P = messages.parkingReport;
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const SITE_ID = "parking-karmana01";
/* 2026-11-02 12:00 Toshkent. */
const NOW = new Date("2026-11-02T07:00:00Z");

const frame = (n: number) => n.toString(16).padStart(64, "0");

function session(n: number, over: Record<string, unknown> = {}) {
  const enteredAt = new Date(Date.UTC(2026, 10, 2, 2, n)).toISOString();
  return {
    session_id: `s-${n}`,
    plate: `01A${String(n).padStart(3, "0")}BC`,
    entered_at: enteredAt,
    exited_at: null,
    duration_minutes: null,
    amount_soum: 0,
    method: null,
    reason: null,
    entry_file_id: frame(n),
    opened_at_exit: false,
    ...over,
  };
}

/*
 * 30 seans: 1–10 to'langan, 11 qo'lda, 12 imtiyozli va CHIQISHDA ro'yxatga
 * olingan, qolganlari ichkarida; 30-chi kadrsiz.
 */
const SESSIONS = Array.from({ length: 30 }, (_, i) => {
  const n = i + 1;
  if (n <= 10) {
    return session(n, {
      exited_at: new Date(Date.UTC(2026, 10, 2, 4, n)).toISOString(),
      duration_minutes: 120,
      amount_soum: 8000,
      method: "cash",
      reason: "paid",
    });
  }
  if (n === 11) return session(n, { exited_at: "2026-11-02T05:00:00Z", reason: "manual" });
  if (n === 12) {
    return session(n, {
      entered_at: "2026-11-02T05:00:00Z",
      exited_at: "2026-11-02T05:00:00Z",
      duration_minutes: 0,
      reason: "exempt",
      opened_at_exit: true,
    });
  }
  if (n === 30) return session(n, { entry_file_id: null });
  return session(n);
});

const REPORT = {
  site_id: SITE_ID,
  site_name: "Karmana bozori avtoturargohi",
  from_date: "2026-11-01",
  to_date: "2026-11-02",
  days: [
    { date: "2026-11-01", entries: 0, exits: 0, cash: 0, terminal: 0, total: 0, free_count: 0 },
    {
      date: "2026-11-02",
      entries: 30,
      exits: 12,
      cash: 60_000,
      terminal: 20_000,
      total: 80_000,
      free_count: 1,
    },
  ],
  total: { entries: 30, exits: 12, cash: 60_000, terminal: 20_000, total: 80_000, free_count: 1 },
  sessions: SESSIONS,
  hours: Array.from({ length: 24 }, (_, hour) => ({
    hour,
    entries: hour === 7 ? 30 : 0,
    exits: hour === 9 ? 12 : 0,
  })),
  stay: {
    measured: 12,
    median_minutes: 120,
    buckets: [
      { key: "under_15m", count: 0 },
      { key: "under_1h", count: 2 },
      { key: "under_2h", count: 0 },
      { key: "under_4h", count: 10 },
      { key: "under_8h", count: 0 },
      { key: "over_8h", count: 0 },
    ],
    unrecorded_entries: 1,
  },
  exit_reasons: [
    { reason: "paid", count: 10 },
    { reason: "online", count: 0 },
    { reason: "free", count: 0 },
    { reason: "exempt", count: 1 },
    { reason: "manual", count: 1 },
  ],
  inside: 18,
  paid_sessions: 10,
  average_check_soum: 8000,
  regulars: [
    { plate: "01A001BC", visits: 3, amount_soum: 12_000, last_seen_at: "2026-11-02T04:01:00Z" },
  ],
};

const SITES = {
  items: [
    {
      id: SITE_ID,
      kind: "parking",
      name: "Karmana bozori avtoturargohi",
      created_at: "2026-10-30T00:00:00Z",
      config_version: 3,
      setup: { devices: [], lanes: [] },
      agent: null,
    },
  ],
};

let client: QueryClient;
let blobs = 0;

function route(report: unknown = REPORT): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path === "/edge-sites") return Promise.resolve(SITES);
    if (path.startsWith(`/edge-sites/${SITE_ID}/parking-report?`)) return Promise.resolve(report);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
  apiClientMock.apiRequest.mockImplementation((path: string) => {
    if (path.startsWith(`/edge-sites/${SITE_ID}/files/`)) {
      return Promise.resolve({ blob: () => Promise.resolve(new Blob(["jpeg"])) });
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function fileRequests(): string[] {
  return apiClientMock.apiRequest.mock.calls
    .map((call) => String(call[0]))
    .filter((path) => path.includes("/files/"));
}

function renderWorkspace() {
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
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} now={NOW} timeZone="Asia/Tashkent">
      <NuqsTestingAdapter searchParams="">
        <QueryClientProvider client={client}>
          <AuthProvider>
            <ParkingReportWorkspace />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  blobs = 0;
  URL.createObjectURL = vi.fn(() => `blob:kadr-${(blobs += 1)}`);
  URL.revokeObjectURL = vi.fn();
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("avtoturargoh hisoboti", () => {
  test("fikstura serverning javob sxemasiga mos (zod)", () => {
    expect(edgeParkingReportSchema.safeParse(REPORT).success).toBe(true);
  });

  test("darvoza oqimi: kirdi, ichkarida, chiqdi va tushum serverdan", async () => {
    route();
    renderWorkspace();
    const flow = await screen.findByRole("region", { name: P.flow.label });
    expect(within(flow).getByText(P.flow.entries)).toBeInTheDocument();
    expect(within(flow).getByText("30")).toBeInTheDocument();
    expect(within(flow).getByText("18")).toBeInTheDocument();
    expect(within(flow).getByText("12")).toBeInTheDocument();
    expect(within(flow).getByText("80 000")).toBeInTheDocument();
    expect(within(flow).getByText("Eng gavjum: 07:00–08:00")).toBeInTheDocument();
    expect(within(flow).getByText("Odatda 2 soat turadi")).toBeInTheDocument();
  });

  test("bepul ro'yxat kartasi bu sahifada yo'q", async () => {
    route();
    renderWorkspace();
    await screen.findByRole("region", { name: P.flow.label });
    expect(screen.queryByText(P.exempt.title)).toBeNull();
  });

  test("kunlik grafik: tushum va mashinalar ko'rinishi almashadi, legendada davr yig'indisi", async () => {
    route();
    renderWorkspace();
    const money = await screen.findByRole("button", { name: P.daily.money });
    expect(money).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByText("60 000 so'm").length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole("button", { name: P.daily.cars }));
    expect(screen.getByRole("button", { name: P.daily.cars })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("galereya: kadri bor eng yangi 8 ta seans, kadrlar so'raladi", async () => {
    route();
    renderWorkspace();
    await screen.findByRole("heading", { name: P.gallery.title });
    /* 30-chi kadrsiz — galereyada 29..22 bo'ladi. */
    expect(await screen.findByAltText("01A029BC — kirishdagi kadr")).toBeInTheDocument();
    await waitFor(() => expect(fileRequests()).toHaveLength(8));
    expect(fileRequests()[0]).toBe(`/edge-sites/${SITE_ID}/files/${frame(29)}`);
    expect(screen.queryByAltText("01A021BC — kirishdagi kadr")).toBeNull();
  });

  test("jurnal: raqam bo'yicha qidiruv (kirill harfi ham) va sahifalash", async () => {
    route();
    renderWorkspace();
    const journal = (await screen.findByRole("heading", { name: P.journal.title })).closest(
      ".dir-chart-card",
    ) as HTMLElement;
    expect(within(journal).getByText("25 / 30 ta mashina")).toBeInTheDocument();

    fireEvent.click(within(journal).getByRole("button", { name: "Yana 5 ta ko'rsatish" }));
    expect(within(journal).getByText("30 / 30 ta mashina")).toBeInTheDocument();

    fireEvent.change(within(journal).getByLabelText(P.journal.searchLabel), {
      target: { value: "01а007" },
    });
    expect(within(journal).getByText("1 / 1 ta mashina")).toBeInTheDocument();
    expect(within(journal).getByText("01A007BC")).toBeInTheDocument();

    /* Chiqishda ro'yxatga olingan: kirgan vaqti o'rniga sababi yoziladi. */
    fireEvent.change(within(journal).getByLabelText(P.journal.searchLabel), {
      target: { value: "01A012" },
    });
    expect(within(journal).getByText(P.journal.atExit)).toBeInTheDocument();
    expect(
      within(journal).getByRole("button", { name: "01A012BC — chiqish kadrini ochish" }),
    ).toBeInTheDocument();
  });

  test("turish vaqti: chiqishda ro'yxatga olinganlar alohida aytiladi", async () => {
    route();
    renderWorkspace();
    expect(
      await screen.findByText(
        "Yana 1 ta mashina chiqishda ro'yxatga olingan — kirgan vaqti noma'lum, shuning uchun hisobga kirmadi.",
      ),
    ).toBeInTheDocument();
  });

  test("jurnal filtri: «Qo'lda» faqat qo'lda chiqarilganlar", async () => {
    route();
    renderWorkspace();
    const journal = (await screen.findByRole("heading", { name: P.journal.title })).closest(
      ".dir-chart-card",
    ) as HTMLElement;
    fireEvent.click(within(journal).getByRole("button", { name: /Qo'lda/u }));
    expect(within(journal).getByText("1 / 1 ta mashina")).toBeInTheDocument();
    expect(within(journal).getByText("01A011BC")).toBeInTheDocument();
  });

  test("jurnal kadri faqat bosilganda so'raladi va oynada ochiladi", async () => {
    route();
    renderWorkspace();
    await waitFor(() => expect(fileRequests()).toHaveLength(8));

    const journal = (await screen.findByRole("heading", { name: P.journal.title })).closest(
      ".dir-chart-card",
    ) as HTMLElement;
    /*
     * 29-chi galereyada ham bor: jurnal oynasi o'z kesh doirasida so'raydi —
     * yopilganda galereya kartasining havolasini bekor qilib qo'ymaydi.
     */
    fireEvent.click(
      within(journal).getByRole("button", { name: "01A029BC — kirish kadrini ochish" }),
    );
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("01A029BC — kirish kadri")).toBeInTheDocument();
    await waitFor(() => expect(fileRequests()).toHaveLength(9));
    expect(fileRequests()[8]).toBe(`/edge-sites/${SITE_ID}/files/${frame(29)}`);
  });

  test("bo'sh davr — nomlangan holat, grafiklar chizilmaydi", async () => {
    route({
      ...REPORT,
      days: REPORT.days.map((day) => ({
        ...day,
        entries: 0,
        exits: 0,
        cash: 0,
        terminal: 0,
        total: 0,
        free_count: 0,
      })),
      total: { entries: 0, exits: 0, cash: 0, terminal: 0, total: 0, free_count: 0 },
      sessions: [],
      inside: 0,
      paid_sessions: 0,
      average_check_soum: null,
      regulars: [],
    });
    renderWorkspace();
    expect(await screen.findByText(P.emptyTitle)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: P.daily.title })).toBeNull();
    expect(fileRequests()).toHaveLength(0);
  });
});
