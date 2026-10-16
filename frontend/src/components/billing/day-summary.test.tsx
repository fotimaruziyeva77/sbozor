/**
 * Patta hisobi — o'tgan kun xulosasi (261016).
 *
 * ⛔ Uch shubhali holat sanog'i BITTA SONGA QO'SHILMAYDI (D-05):
 *    «kamera ko'rmadi» ≠ «ro'yxatsiz savdo».
 * ⛔ Qoldiq — jadvaldagi «Qoldiq» ustunining yig'indisi; kassa farqi —
 *    faqat YOPILGAN smenalardan (ochiq smenada deklaratsiya yo'q).
 * ⛔ Xulosa blok EMAS: G-25 atributlarini olmaydi.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({
  apiFetch: vi.fn(),
  apiRequest: vi.fn(),
}));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return {
    ...actual,
    apiFetch: apiClientMock.apiFetch,
    apiRequest: apiClientMock.apiRequest,
  };
});

import messages from "../../../messages/uz-Latn.json";
import { BillingDaySummary } from "@/components/billing/day-summary";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const DAY = "2026-10-11";
const VENDOR = "ffffffff-6666-4666-8666-ffffffffffff";

const CHARGES = {
  day: DAY,
  rows: [
    { stall: "1", amount: 22_000, outstanding: 22_000 },
    { stall: "2", amount: 12_000, outstanding: 0 },
    { stall: "3", amount: 12_000, outstanding: 5_000 },
  ].map((row, index) => ({
    charge_id: `aaaaaaaa-1111-4111-8111-00000000000${index}`,
    stall_code: row.stall,
    vendor_id: VENDOR,
    service_date: DAY,
    tariff_amount_soum: row.amount,
    amount_soum: row.amount,
    outstanding_soum: row.outstanding,
  })),
  charge_count: 3,
  charged_soum: 46_000,
};

const ANOMALIES = {
  day: DAY,
  rows: [],
  unassigned_count: 2,
  closed_day_count: 0,
  no_coverage_count: 7,
};

const SHIFTS = {
  day: DAY,
  rows: [
    {
      id: "99999999-9999-4999-8999-999999999991",
      cashier_id: "eeeeeeee-5555-4555-8555-eeeeeeeeeeee",
      opened_at: "2026-10-11T03:00:00Z",
      closed_at: "2026-10-11T12:00:00Z",
      declared_soum: 95_000,
      system_soum: 100_000,
      corrected_soum: null,
      correction_reason: null,
      corrected_at: null,
      variance_soum: -5_000,
    },
    {
      /* Ochiq smena — farq hisobga KIRMAYDI. */
      id: "99999999-9999-4999-8999-999999999992",
      cashier_id: "eeeeeeee-5555-4555-8555-eeeeeeeeeeee",
      opened_at: "2026-10-11T13:00:00Z",
      closed_at: null,
      declared_soum: null,
      system_soum: 40_000,
      corrected_soum: null,
      correction_reason: null,
      corrected_at: null,
      variance_soum: -40_000,
    },
  ],
  shiftless_payment_count: 0,
  shiftless_payment_soum: 0,
};

function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/billing/charges")) return Promise.resolve(CHARGES);
    if (path.startsWith("/billing/anomalies")) return Promise.resolve(ANOMALIES);
    if (path.startsWith("/shifts")) return Promise.resolve(SHIFTS);
    return Promise.resolve({ items: [], next_cursor: null });
  });
}

function renderSummary() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages} timeZone="Asia/Tashkent">
      <QueryClientProvider client={client}>
        <AuthProvider>
          <BillingDaySummary day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/** Katak qiymati — yorlig'i bo'yicha topiladi (NBSP oddiy bo'shliqqa keltiriladi). */
function tileText(label: string): string {
  const tile = screen.getByText(label).closest(".stat-tile");
  return (tile?.textContent ?? "").replace(/ /gu, " ");
}

beforeEach(() => {
  vi.resetAllMocks();
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles: ["director"],
      marketId: "11111111-1111-4111-8111-111111111111",
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });
  routeFetch();
});

afterEach(() => {
  clearSession();
});

describe("BillingDaySummary", () => {
  test("yozilgan patta — serverning jami summasi va rastalar soni", async () => {
    renderSummary();
    await screen.findByText(messages.billing.summaryChargedNote.replace("{count}", "3"));
    expect(tileText(messages.billing.summaryCharged)).toContain("46 000");
  });

  test("to'lanmagan qoldiq — jadvaldagi «Qoldiq» ustunining yig'indisi", async () => {
    renderSummary();
    await screen.findByText(messages.billing.summaryOutstandingNote.replace("{count}", "2"));
    expect(tileText(messages.billing.summaryOutstanding)).toContain("27 000");
  });

  test("⛔ uch sanoq QO'SHILMAYDI: qiymat — faqat ro'yxatsiz savdo", async () => {
    renderSummary();
    const label = messages.billing.anomalyKind.unassigned_occupied;
    await screen.findByText(
      messages.billing.summaryAnomaliesNote.replace("{closed}", "0").replace("{uncovered}", "7"),
    );
    const text = tileText(label);
    expect(text).toContain("2");
    /* 2 + 0 + 7 = 9 — yig'indi ekranga CHIQMAYDI. */
    expect(text).not.toMatch(/(^|\D)9(\D|$)/u);
  });

  test("kassa farqi — faqat yopilgan smenadan", async () => {
    renderSummary();
    await screen.findByText(
      messages.billing.summaryShiftsNote
        .replace("{state}", messages.billing.varianceShort)
        .replace("{count}", "1"),
    );
    const text = tileText(messages.billing.summaryShifts);
    expect(text).toContain("−5 000");
    expect(text).not.toContain("45 000");
  });

  test("⛔ xulosa G-25 bloki EMAS — atributlarsiz", async () => {
    const { container } = renderSummary();
    await screen.findByText(messages.billing.summaryChargedNote.replace("{count}", "3"));
    expect(container.querySelector("[data-billing-block]")).toBeNull();
    expect(container.querySelector("[data-billing-content]")).toBeNull();
  });
});
