/**
 * Y-4 — ⛔⛔ G-25: PROYEKSIYA VA YOZILGAN HISOB BIR EKRANDA UCHRASHMAYDI.
 *
 * =============================================================================
 * ⛔⛔ DARVOZA UCH QATLAMLI — VA UCHINCHISI O'LCHANGAN KO'RLIKDAN TUG'ILDI.
 *
 * (a) BLOK TO'PLAMI — D-17 ning strukturaviy shakli:
 *     `?day=bugun` -> {day, pending, shifts}
 *     `?day<bugun` -> {day, charges, anomalies, shifts}
 *     kesishma     -> {day, shifts}
 *
 * ⛔ (a) YOLG'IZ BO'SH O'RAMNI ⛔ MUKAMMAL O'TKAZARDI. Bo'sh
 *   `<div data-billing-block="charges" />` atribut to'plamini
 *   O'ZGARTIRMAYDI, ya'ni BILL-02/03/04 direktor ekranida ⛔ UMUMAN
 *   CHIZILMAGAN holda darvoza, task VA faza ⛔ YASHIL qaytardi. Bu
 *   05-15 ning ⛔ S-D SINFI: sabotaj sistemaga yetib boradi, lekin
 *   tanlangan YUZA ikkala shoxda ham bir xil javob beradi. O'sha
 *   darsning yechimi — ⛔ YUZANI KENGAYTIRISH, assertni almashtirish
 *   EMAS.
 *
 * (b) ⛔ MAZMUN JUFTLIGI — ro'yxat komponentining ⛔ O'ZI
 *     `data-billing-content="<blok>"` chiqaradi (⛔ `page.tsx` EMAS).
 *     Da'vo (a) ning to'plamidan ⛔ AYLANIB HOSILA qilinadi (D-32).
 *
 * (c) ⛔ HAQIQIY MAZMUN — kutilgan qiymat ⛔ MOCK JAVOB OBYEKTIDAN
 *     olinadi, testda literal ⛔ YOZILMAYDI. Bo'sh natija ham MAZMUN:
 *     `rows: []` bergan blok O'Z BO'SH-HOLAT MATNINI ko'rsatishi shart.
 *
 * ⛔ ENVELOPE `{items}` EMAS: `{day, rows, …}` (06-08 serveri, 06-11
 *   klienti). Mock ham shu shaklda va uchala anomaliya sanog'i
 *   ⛔ ALOHIDA (D-05) — bitta songa qo'shilmaydi.
 *
 * ⛔ D-31: yo'qlik ⛔ TO'PLAM TENGLIGI bilan o'lchanadi. Bitta nomni
 *   inkor qiladigan matcher bu faylda ISHLATILMAYDI — u faqat o'sha
 *   nomni ushlardi. ⚠ Matcher nomi izohda LITERAL yozilmaydi: qabul
 *   mezoni uni `grep` bilan sanaydi (kodbaza konvensiyasi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
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

import messages from "../../../../../messages/uz-Latn.json";
import BillingPage from "./page";
import {
  businessDayIn,
  shiftIsoDay,
} from "@/components/snapshots/day-picker";
import { ANOMALY_KINDS } from "@/lib/api-types";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/* ⛔ Sana SANALADI — literal YO'Q (`day-picker.test.tsx` bilan bir qoida). */
const NOW = new Date();
const TODAY = businessDayIn(TIME_ZONE, NOW);
const YESTERDAY = shiftIsoDay(TODAY, -1);

/* --- Mock javoblar — kutilma SHULARDAN hosila qilinadi --------------------- */

const PENDING = {
  service_date: TODAY,
  market_open: true,
  pending_amount_soum: 1_240_000,
  outstanding_soum: 380_000,
  pending_stall_count: 87,
  fetched_at: "2026-08-10T05:30:00Z",
};

const CHARGES = {
  day: YESTERDAY,
  rows: [
    {
      charge_id: "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa",
      stall_code: "14-C",
      vendor_id: "ffffffff-6666-4666-8666-ffffffffffff",
      service_date: YESTERDAY,
      tariff_amount_soum: 15_000,
      amount_soum: 15_000,
      outstanding_soum: 0,
    },
    {
      charge_id: "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb",
      stall_code: "15-A",
      vendor_id: "ffffffff-6666-4666-8666-ffffffffffff",
      service_date: YESTERDAY,
      tariff_amount_soum: 20_000,
      amount_soum: 20_000,
      outstanding_soum: 5_000,
    },
  ],
  charge_count: 2,
  charged_soum: 35_000,
};

/** ⛔ Tarif va hisob summasi FARQ QILADI — ikkinchi ustun shoxi (D-09). */
const CHARGES_ADJUSTED = {
  ...CHARGES,
  rows: [{ ...CHARGES.rows[0], tariff_amount_soum: 15_000, amount_soum: 12_000 }],
  charge_count: 1,
  charged_soum: 12_000,
};

const ANOMALIES = {
  day: YESTERDAY,
  rows: [
    {
      anomaly_id: "cccccccc-3333-4333-8333-cccccccccccc",
      /* ⛔ Tur REYESTRDAN olinadi — literal yozilmaydi (D-32). */
      kind: ANOMALY_KINDS[0],
      stall_code: "22-B",
      service_date: YESTERDAY,
      snapshot_id: "dddddddd-4444-4444-8444-dddddddddddd",
    },
  ],
  unassigned_count: 1,
  closed_day_count: 0,
  no_coverage_count: 3,
};

const SHIFTS = {
  day: YESTERDAY,
  rows: [
    {
      id: "99999999-9999-4999-8999-999999999999",
      cashier_id: "eeeeeeee-5555-4555-8555-eeeeeeeeeeee",
      opened_at: "2026-08-09T03:00:00Z",
      closed_at: "2026-08-09T12:00:00Z",
      declared_soum: 940_000,
      system_soum: 975_000,
      variance_soum: -35_000,
    },
  ],
  shiftless_payment_count: 2,
  shiftless_payment_soum: 45_000,
};

const EMPTY_CHARGES = { ...CHARGES, rows: [], charge_count: 0, charged_soum: 0 };
const EMPTY_ANOMALIES = {
  ...ANOMALIES,
  rows: [],
  unassigned_count: 0,
  closed_day_count: 0,
  no_coverage_count: 0,
};
const EMPTY_SHIFTS = {
  ...SHIFTS,
  rows: [],
  shiftless_payment_count: 0,
  shiftless_payment_soum: 0,
};

type Responses = {
  charges?: typeof CHARGES;
  anomalies?: typeof ANOMALIES;
  shifts?: typeof SHIFTS;
};

function routeFetch(overrides: Responses = {}): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/billing/pending")) return Promise.resolve(PENDING);
    if (path.startsWith("/billing/charges")) {
      return Promise.resolve(overrides.charges ?? CHARGES);
    }
    if (path.startsWith("/billing/anomalies")) {
      return Promise.resolve(overrides.anomalies ?? ANOMALIES);
    }
    if (path.startsWith("/shifts")) {
      return Promise.resolve(overrides.shifts ?? SHIFTS);
    }
    if (path.startsWith("/users")) return Promise.resolve({ items: [] });
    return Promise.resolve({ items: [], next_cursor: null });
  });
}

let client: QueryClient;

function renderPage(searchParams: string) {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={searchParams}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <BillingPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );
}

/* --- G-25 ning o'lchov asboblari ------------------------------------------ */

/** DOM'dagi `data-billing-block` qiymatlari TO'PLAMI. */
function blockSet(): Set<string> {
  return new Set(
    [...document.querySelectorAll("[data-billing-block]")].map(
      (node) => node.getAttribute("data-billing-block") ?? "",
    ),
  );
}

/** DOM'dagi `data-billing-content` qiymatlari TO'PLAMI. */
function contentSet(): Set<string> {
  return new Set(
    [...document.querySelectorAll("[data-billing-content]")].map(
      (node) => node.getAttribute("data-billing-content") ?? "",
    ),
  );
}

function blockEl(name: string): HTMLElement {
  const node = document.querySelector(`[data-billing-block="${name}"]`);
  if (node === null) throw new Error(`«${name}» bloki topilmadi`);
  return node as HTMLElement;
}

/**
 * ⛔ MAZMUN ATRIBUTIDAN OZOD BLOKLAR — AYNAN BITTA.
 *
 * Kun tanlagichi ⛔ BOSHQARUV, ro'yxat emas: uning o'z da'volari
 * `components/billing/day-picker.test.tsx` da o'lchanadi. Istisno
 * ro'yxati ⛔ JIMGINA O'SMASLIGI uchun uning hajmi ALOHIDA assert
 * qilinadi — aks holda keyingi ijrochi qizargan blokni shu yerga
 * qo'shib darvozani bo'shatib qo'yardi.
 */
const CONTENT_EXEMPT = new Set(["day"]);

function difference(left: Set<string>, right: Set<string>): Set<string> {
  return new Set([...left].filter((value) => !right.has(value)));
}

function intersection(left: Set<string>, right: Set<string>): Set<string> {
  return new Set([...left].filter((value) => right.has(value)));
}

beforeEach(() => {
  vi.resetAllMocks();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
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
  globalThis.URL.createObjectURL = vi.fn(() => "blob:evidence");
  globalThis.URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* (a) BLOK TO'PLAMI — DISJUNKTLIK                                            */
/* -------------------------------------------------------------------------- */

describe("⛔ G-25 (a): blok to'plamlari DISJUNKT", () => {
  test("⛔ `?day=bugun` -> AYNAN {day, pending, shifts}", async () => {
    routeFetch();
    renderPage(`?day=${TODAY}`);

    await screen.findByText(messages.billing.pendingTitle);
    expect(blockSet()).toEqual(new Set(["day", "pending", "shifts"]));
  });

  /*
   * ⛔ (a) NING KUTISH LANGARI ⛔ `shiftsTitle` — `chargesTitle` EMAS.
   *
   *   S-E sabotaji (`<ChargeList/>` -> bo'sh o'ram) o'lchandi va u
   *   `chargesTitle` langari bilan (a) ni ham qizartirardi — ya'ni
   *   qatlamlar ARALASHIB ketardi va «eski darvoza ko'r edi» degan
   *   FAKT o'lchanmay qolardi. (a) ning da'vosi FAQAT blok to'plami
   *   haqida, shuning uchun langar ikkala shoxda ham mavjud blokdan
   *   («smena») olinadi.
   */
  test("⛔ `?day=kecha` -> AYNAN {day, charges, anomalies, shifts}", async () => {
    routeFetch();
    renderPage(`?day=${YESTERDAY}`);

    await screen.findByText(messages.billing.shiftsTitle);
    expect(blockSet()).toEqual(
      new Set(["day", "charges", "anomalies", "shifts"]),
    );
  });

  test("⛔ kesishma AYNAN {day, shifts} — to'plam AMALI bilan hisoblanadi", async () => {
    routeFetch();
    const today = renderPage(`?day=${TODAY}`);
    await screen.findByText(messages.billing.shiftsTitle);
    const todayBlocks = blockSet();
    today.unmount();

    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.shiftsTitle);
    const pastBlocks = blockSet();

    /*
     * ⛔ KESISHMA QO'LDA YOZILGAN RO'YXATDAN EMAS, TO'PLAM AMALIDAN
     *   hosila (D-32): `pending` va `charges` HECH QACHON birga
     *   chiqmasligi shu yerda isbotlanadi.
     */
    expect(intersection(todayBlocks, pastBlocks)).toEqual(
      new Set(["day", "shifts"]),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* (b) MAZMUN JUFTLIGI — BO'SH O'RAM O'TMAYDI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-25 (b): har blok O'Z mazmunini o'z ichiga oladi", () => {
  test("⛔ istisno ro'yxati AYNAN BITTA a'zoli — jimgina o'smaydi", () => {
    expect(CONTENT_EXEMPT.size).toBe(1);
  });

  test("⛔ `?day=kecha`: har blok ichida O'Z `data-billing-content` i bor", async () => {
    routeFetch();
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.chargesTitle);

    const blocks = blockSet();
    /* ⛔ DA'VO (a) NING TO'PLAMIDAN AYLANIB HOSILA QILINADI. */
    for (const name of blocks) {
      if (CONTENT_EXEMPT.has(name)) continue;
      expect(
        blockEl(name).querySelector(`[data-billing-content="${name}"]`),
      ).not.toBeNull();
    }

    expect(contentSet()).toEqual(difference(blocks, CONTENT_EXEMPT));
  });

  test("⛔ `?day=bugun`: mazmun to'plami = bloklar \\ istisno", async () => {
    routeFetch();
    renderPage(`?day=${TODAY}`);
    await screen.findByText(messages.billing.pendingTitle);

    const blocks = blockSet();
    for (const name of blocks) {
      if (CONTENT_EXEMPT.has(name)) continue;
      expect(
        blockEl(name).querySelector(`[data-billing-content="${name}"]`),
      ).not.toBeNull();
    }

    expect(contentSet()).toEqual(difference(blocks, CONTENT_EXEMPT));
  });
});

/* -------------------------------------------------------------------------- */
/* (c) HAQIQIY MAZMUN — MOCK JAVOBIDAN HOSILA                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-25 (c): har blok ro'yxatining KUZATILADIGAN chiqishi bor", () => {
  test("⛔ `pending` bloki formatlangan kutilayotgan summani ko'rsatadi", async () => {
    routeFetch();
    renderPage(`?day=${TODAY}`);
    await screen.findByText(messages.billing.pendingTitle);

    /* ⛔ Kutilma MOCK OBYEKTIDAN — literal raqam yozilmaydi. */
    const expected = new Intl.NumberFormat("uz-Latn").format(
      PENDING.pending_amount_soum,
    );
    await waitFor(() =>
      expect(
        (blockEl("pending").textContent ?? "").includes(expected),
      ).toBe(true),
    );
  });

  test("⛔ `charges` bloki: birinchi rasta kodi VA qatorlar soni javobdan", async () => {
    routeFetch();
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.chargesTitle);

    const block = blockEl("charges");
    await waitFor(() =>
      expect(
        (block.textContent ?? "").includes(CHARGES.rows[0].stall_code),
      ).toBe(true),
    );
    expect(block.querySelectorAll("tbody tr").length).toBe(CHARGES.rows.length);
  });

  test("⛔ `anomalies` bloki: `kind` ning REYESTRDAN olingan yorlig'i", async () => {
    routeFetch();
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.anomaliesTitle);

    /* Yorliq ham mock'dagi `kind` dan hosila — literal matn yozilmaydi. */
    const label = messages.billing.anomalyKind[ANOMALIES.rows[0].kind];
    await waitFor(() =>
      expect((blockEl("anomalies").textContent ?? "").includes(label)).toBe(
        true,
      ),
    );
  });

  test("⛔ `shifts` bloki: formatlangan deklaratsiya javobdan", async () => {
    routeFetch();
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.shiftsTitle);

    const expected = new Intl.NumberFormat("uz-Latn").format(
      SHIFTS.rows[0].declared_soum,
    );
    await waitFor(() =>
      expect((blockEl("shifts").textContent ?? "").includes(expected)).toBe(
        true,
      ),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* BO'SH NATIJA HAM MAZMUN                                                    */
/* -------------------------------------------------------------------------- */

describe("⛔ bo'sh natija — NATIJA, bo'sh `<div>` EMAS", () => {
  test("⛔ uchala ro'yxat bo'sh bo'lganda ham (b) va (c) YASHIL qoladi", async () => {
    routeFetch({
      charges: EMPTY_CHARGES,
      anomalies: EMPTY_ANOMALIES,
      shifts: EMPTY_SHIFTS,
    });
    renderPage(`?day=${YESTERDAY}`);

    /* ⛔ Har blok O'Z BO'SH-HOLAT MATNINI ko'rsatadi (§13.8 №5/№6/№7). */
    expect(
      await screen.findByText(messages.billing.emptyCharges),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.billing.emptyAnomalies)).toBeInTheDocument();
    expect(screen.getByText(messages.billing.emptyShifts)).toBeInTheDocument();

    const blocks = blockSet();
    expect(blocks).toEqual(new Set(["day", "charges", "anomalies", "shifts"]));
    expect(contentSet()).toEqual(difference(blocks, CONTENT_EXEMPT));
  });

  test("⛔ uchala anomaliya sanog'i NOL bo'lganda ham chiziladi (D-05)", async () => {
    routeFetch({ anomalies: EMPTY_ANOMALIES });
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.anomaliesTitle);

    /* ⛔ UCH YORLIQ — reyestrdan aylanib, bittasi ham tushib qolmaydi. */
    const block = blockEl("anomalies");
    await waitFor(() => {
      for (const kind of ANOMALY_KINDS) {
        expect(
          (block.textContent ?? "").includes(messages.billing.anomalyKind[kind]),
        ).toBe(true);
      }
    });
  });
});

/* -------------------------------------------------------------------------- */
/* BO'SH HOLAT №4 — C-3 NI OCHIQ TUSHUNTIRADI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ bo'sh holat №4 (`day = bugun`)", () => {
  test("⛔ tushuntirish jumlasi ko'rinadi va u BLOK ATRIBUTINI OLMAYDI", async () => {
    routeFetch();
    renderPage(`?day=${TODAY}`);

    expect(
      await screen.findByText(messages.billing.chargesLaterNotice),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.billing.emptyToday)).toBeInTheDocument();

    /*
     * ⛔ Jumla BLOK EMAS — blokning YO'QLIGINI tushuntiruvchi matn. Agar
     *   u atribut olsa, `day = bugun` to'plami {day, pending, shifts}
     *   bo'lmay qolardi va (a) NOTO'G'RI SABABDAN qizarardi.
     */
    expect(blockSet()).toEqual(new Set(["day", "pending", "shifts"]));
  });
});

/* -------------------------------------------------------------------------- */
/* D-09 — SUMMA USTUNLARI (jadval darajasidagi qaror)                         */
/* -------------------------------------------------------------------------- */

describe("⛔ D-09: tarif va hisob summasi ustunlari", () => {
  test("hamma qatorda TENG bo'lsa — BITTA summa ustuni", async () => {
    routeFetch({ charges: CHARGES });
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.chargesTitle);

    const block = blockEl("charges");
    await waitFor(() =>
      expect(block.querySelectorAll("tbody tr").length).toBe(
        CHARGES.rows.length,
      ),
    );

    const headers = new Set(
      [...block.querySelectorAll("thead th")].map((node) =>
        (node.textContent ?? "").trim(),
      ),
    );
    expect(headers.has(messages.billing.amount)).toBe(true);
    expect(headers.has(messages.billing.tariffAmount)).toBe(false);
  });

  test("⛔ birorta qatorda FARQ bo'lsa — IKKITA ustun", async () => {
    routeFetch({ charges: CHARGES_ADJUSTED });
    renderPage(`?day=${YESTERDAY}`);
    await screen.findByText(messages.billing.chargesTitle);

    const block = blockEl("charges");
    await waitFor(() =>
      expect(block.querySelectorAll("tbody tr").length).toBe(1),
    );

    const headers = new Set(
      [...block.querySelectorAll("thead th")].map((node) =>
        (node.textContent ?? "").trim(),
      ),
    );
    expect(headers.has(messages.billing.tariffAmount)).toBe(true);
    expect(headers.has(messages.billing.chargeAmount)).toBe(true);
  });
});

/* -------------------------------------------------------------------------- */
/* HUQUQ KO'ZGUSI                                                             */
/* -------------------------------------------------------------------------- */

describe("huquq ko'zgusi", () => {
  test("⛔ `report_view` yo'q sessiyada sahifa CHIZILMAYDI va so'rov KETMAYDI", () => {
    routeFetch();
    setSession({
      accessToken: "test-access-token",
      markets: [],
      principal: {
        userId: "44444444-4444-4444-8444-444444444444",
        phone: "+998900000001",
        fullName: "Kassir",
        roles: ["cashier"],
        marketId: MARKET_ID,
        marketName: "Karmana markaziy bozori",
        isPlatformAdmin: false,
        locale: "uz-Latn",
        mustChangePassword: false,
      },
    });

    renderPage(`?day=${YESTERDAY}`);

    expect(screen.getByText(messages.errors.forbidden)).toBeInTheDocument();
    expect(blockSet()).toEqual(new Set());
    expect(apiClientMock.apiFetch.mock.calls.length).toBe(0);
  });
});
