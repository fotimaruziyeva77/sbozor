/**
 * Sotuvchining kunma-kun to'lov tarixi — EKRAN (261006).
 *
 * =============================================================================
 * ⛔⛔ NIMA O'LCHANADI VA NEGA.
 *
 *   Server holatni FIFO taqsimlashidan chiqaradi: kassir bugungi pattani va
 *   eski qarzni BITTA to'lov bilan oladi, ya'ni «shu kuni pul berilmagan»
 *   kun ham «to'landi» bo'lishi mumkin (birinchi versiya bunday kunlarni
 *   «to'lanmagan» deb ko'rsatgan va prod'da qarzi nolga tushirilgan bozorda
 *   261 kun qizil chiqqan edi).
 *
 *   Ekran shu ikki faktni ZIDDIYATSIZ ko'rsatishi kerak: belgi — holat
 *   (serverdan), qator tafsiloti — o'sha kuni kassaga tushgan pul. Bu test
 *   aynan shu kunni chizadi va ikkalasi bir qatorda turganini tekshiradi.
 *
 *   Javob `vendorHistorySchema` dan O'TKAZIB ekiladi: server maydon nomlari
 *   bilan klient sxemasi ajralib ketsa test shu yerda yiqiladi.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test } from "vitest";

import messages from "../../../messages/uz-Latn.json";
import { VendorDays } from "@/components/director/vendor-days";
import { vendorHistorySchema } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const VENDOR_ID = "55555555-5555-4555-8555-555555555555";
const FROM = "2026-09-26";
const TO = "2026-10-04";

const D = messages.director;

/** `{sum}` dan oldingi qism — summa formati (bo'sh joy belgisi) testga kirmaydi. */
function prefiks(matn: string): RegExp {
  return new RegExp(`^${matn.split("{sum}")[0]}`);
}

/**
 * Server javobi — FIFO'ga mos: eski kunlar yopilgan, qarz eng yangi kunda.
 * Kunlar server tartibida (eng yangisi birinchi).
 */
const JAVOB = vendorHistorySchema.parse({
  vendor_id: VENDOR_ID,
  from_date: FROM,
  to_date: TO,
  rows: [
    {
      service_date: "2026-10-04",
      charged_soum: 52_000,
      waived_soum: 0,
      covered_soum: 20_000,
      unpaid_soum: 32_000,
      paid_soum: 0,
      payment_count: 0,
      last_payment_at: null,
      stall_codes: "1, 2",
      status: "partial",
    },
    {
      service_date: "2026-10-03",
      charged_soum: 52_000,
      waived_soum: 0,
      covered_soum: 52_000,
      unpaid_soum: 0,
      paid_soum: 0,
      payment_count: 0,
      last_payment_at: null,
      stall_codes: "1, 2",
      status: "paid",
    },
    {
      service_date: "2026-10-01",
      charged_soum: 0,
      waived_soum: 0,
      covered_soum: 0,
      unpaid_soum: 0,
      paid_soum: 52_000,
      payment_count: 1,
      last_payment_at: "2026-10-01T06:10:00Z",
      stall_codes: null,
      status: "advance",
    },
    {
      service_date: "2026-09-30",
      charged_soum: 48_000,
      waived_soum: 40_000,
      covered_soum: 8_000,
      unpaid_soum: 0,
      paid_soum: 48_000,
      payment_count: 1,
      last_payment_at: "2026-09-30T05:40:00Z",
      stall_codes: "1, 2",
      status: "waived",
    },
  ],
  charged_total_soum: 152_000,
  paid_total_soum: 100_000,
  waived_total_soum: 40_000,
  unpaid_total_soum: 32_000,
  unpaid_days: 1,
  outstanding_soum: 32_000,
  advance_soum: 0,
});

function renderDays(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  // Kalit `useVendorHistory` dagi bilan AYNI — u o'zgarsa test bo'sh
  // holatga tushib yiqiladi, jimgina yashil qolmaydi.
  queryClient.setQueryData(
    ["reports", MARKET_ID, "vendor-history", VENDOR_ID, FROM, TO],
    JAVOB,
  );
  render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <VendorDays from={FROM} to={TO} vendorId={VENDOR_ID} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  clearSession();
  setSession({
    accessToken: "test-access-token",
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
    markets: [],
  });
});

afterEach(() => {
  clearSession();
});

describe("sotuvchi tarixi — ekran", () => {
  test("⛔ pul BOSHQA kuni berilgan kun: belgi «to'landi», tafsilot «shu kuni to'lov yo'q»", () => {
    renderDays();

    const kunlar = screen.getAllByRole("listitem");
    expect(kunlar).toHaveLength(4);
    const fifoYopgan = within(kunlar[1]);
    expect(fifoYopgan.getByText(D.vaDay_paid)).toBeInTheDocument();
    expect(fifoYopgan.getByText(D.vaRowNoCash)).toBeInTheDocument();
    expect(
      fifoYopgan.queryByText(prefiks(D.vaRowDebt)),
      "yopilgan kunda qarz yozilmasligi kerak",
    ).not.toBeInTheDocument();
  });

  test("qoidaning o'zi ekranda aytiladi — aks holda yuqoridagi qator ziddek o'qiladi", () => {
    renderDays();
    expect(screen.getByText(D.vaHistoryRule)).toBeInTheDocument();
  });

  test("qarzli kun: «qisman» belgisi va qolgan qarz qizil", () => {
    renderDays();

    const qarzli = within(screen.getAllByRole("listitem")[0]);
    expect(qarzli.getByText(D.vaDay_partial)).toBeInTheDocument();
    expect(qarzli.getByText(prefiks(D.vaRowDebt))).toHaveClass("text-danger-text");
  });

  test("hisobsiz kun va kechirilgan kun o'z belgisi bilan", () => {
    renderDays();

    const [, , hisobsiz, kechirilgan] = screen.getAllByRole("listitem");
    expect(within(hisobsiz).getByText(D.vaDay_advance)).toBeInTheDocument();
    expect(within(hisobsiz).getByText(D.vaRowNoCharge)).toBeInTheDocument();
    expect(within(kechirilgan).getByText(D.vaDay_waived)).toBeInTheDocument();
    expect(
      within(kechirilgan).getByText(prefiks(D.vaRowWaived)),
    ).toBeInTheDocument();
  });

  test("yig'indida qarz bor — u karta bilan bir xil son (`outstanding_soum`)", () => {
    renderDays();
    expect(
      screen.getByText(new RegExp(D.vaHistoryDebt.split("{sum}")[0])),
    ).toBeInTheDocument();
  });
});
