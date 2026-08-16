/**
 * =============================================================================
 * RASTA KARTASI — «BUGUNGI HOLAT» BO'LIMI (MARKET-06, Topilma №C).
 *
 * -----------------------------------------------------------------------
 * ⛔ ENG QIMMAT DA'VO — BO'LIMNING **YO'QLIGI** (05-14 darsi)
 * -----------------------------------------------------------------------
 * Ma'lumot kelmagan holatda (huquq yo'q, qoralama bozor, qator yo'q)
 * bo'lim ⛔ UMUMAN chizilmaydi: na platsholder, na tire, na nol. Va bu
 * SARLAVHANING YO'QLIGI bilan o'lchanadi, alohida qiymatlarning
 * inkori bilan EMAS — `queryByText("0")` sahifadagi boshqa nolni topib
 * yolg'on-yashil bo'lardi.
 *
 * -----------------------------------------------------------------------
 * ⛔ DALIL — HAVOLA, KADR EMAS (D-C7, M-7)
 * -----------------------------------------------------------------------
 * Kartada MAVJUD `EvidenceLink` QAYTA ISHLATILADI va u
 * `scripts/reconciliation-copy.test.mjs` bilan mexanik qulflangan. Bu
 * fayl uning MATNINI izlaydi, rasm elementini emas — «kadr chizilmadi»
 * degan da'vo o'sha statik darvozaning zimmasida qoladi va bu yerda
 * TAKRORLANMAYDI.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

/*
 * ⛔ `@/i18n/navigation` MOCK'I MAJBURIY — VA SABAB O'LCHANGAN.
 *
 * `EvidenceLink` (dalil havolasi, D-C7) `Link` ni `@/i18n/navigation`
 * dan oladi; u esa `next-intl/navigation` -> `next/navigation` zanjiriga
 * tayanadi va bu zanjir vitest ESM ostida YECHILMAYDI. Mocksiz butun
 * fayl «0 test» bilan yiqiladi (`forbidden-notice.tsx` da hujjatlashgan
 * o'lchov: to'rtta fayl, 27 test). Shakl `case-detail-dialog.test.tsx`
 * dagi bilan AYNAN bir xil — kodbazada bu naqshning BITTA shakli bor.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/map",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { MAP_DAY_PATH } from "@/lib/map-day-queries";

const { apiFetch } = apiClientMock;

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const ZONE_ID = "22222222-2222-4222-8222-222222222222";
const STALL_ID = "33333333-3333-4333-8333-333333333333";
const CASE_ID = "55555555-5555-4555-8555-555555555555";
const SNAPSHOT_ID = "66666666-6666-4666-8666-666666666666";

const AMOUNT_SOUM = 15_000;
const PAID_SOUM = 5_000;
const CASE_DATE = "2026-08-14";

const STALL_DETAIL = {
  id: STALL_ID,
  code: "42",
  zone_id: ZONE_ID,
  zone_name: "A zonasi",
  category_id: null,
  category_name: "Sabzavot",
  status: "active",
  vendor_id: null,
  vendor_name: "Karimov A.",
  tariff_soum: AMOUNT_SOUM,
  created_at: "2026-08-01T00:00:00Z",
  phone: null,
  assignment_from: "2026-07-01",
  note: null,
};

type DayRow = {
  stall_id: string;
  state: "paid" | "due" | "mismatch" | "free" | "no_billing";
  amount_soum: number | null;
  unavailable_reason: "market_closed" | "tariff_missing" | null;
  paid_soum: number;
  remaining_soum: number | null;
  open_case_id: string | null;
  open_case_service_date: string | null;
};

const CASE_DETAIL = {
  case_id: CASE_ID,
  subject_kind: "occupied_unpaid",
  anomaly_id: null,
  charge_id: "77777777-7777-4777-8777-777777777777",
  service_date: CASE_DATE,
  status: "new",
  assignee_user_id: null,
  created_at: "2026-08-15T04:25:00Z",
  resolution_note: null,
  events: [],
  evidence_snapshot_ids: [SNAPSHOT_ID],
};

/** ⛔ Mock YO'L bo'yicha marshrutlanadi; noma'lum yo'l RAD ETILADI. */
function routeFetch(rows: readonly DayRow[], caseDetail: unknown = CASE_DETAIL) {
  apiFetch.mockImplementation((path: string) => {
    if (path === `/stalls/${STALL_ID}`) return Promise.resolve(STALL_DETAIL);
    if (path === MAP_DAY_PATH) {
      return Promise.resolve({
        service_date: "2026-08-16",
        market_active: true,
        market_open: true,
        rows,
      });
    }
    if (path.startsWith("/reconciliation/cases/")) {
      return Promise.resolve(caseDetail);
    }
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

let client: QueryClient;

function renderCard(roles: readonly string[]) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={client}>
        <AuthProvider>
          <StallCardDialog onClose={() => {}} stallId={STALL_ID} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

function dayRow(overrides: Partial<DayRow> = {}): DayRow {
  return {
    stall_id: STALL_ID,
    state: "due",
    amount_soum: AMOUNT_SOUM,
    unavailable_reason: null,
    paid_soum: PAID_SOUM,
    remaining_soum: AMOUNT_SOUM - PAID_SOUM,
    open_case_id: null,
    open_case_service_date: null,
    ...overrides,
  };
}

/** Bo'limning `<dt>` yorliqlari — matn bo'yicha. */
function definitionTerms(): string[] {
  return Array.from(document.querySelectorAll("dt")).map(
    (node) => node.textContent ?? "",
  );
}

/**
 * Sahifa matni — ⛔ AJRALMAS BO'SHLIQ ODDIY BO'SHLIQQA keltirilgan.
 *
 * `Intl.NumberFormat('uz-Latn', { currency: 'UZS' })` guruh ajratkichi
 * sifatida `U+00A0` beradi (o'lchandi: `"7 777 so'm"`). Testda
 * oddiy bo'shliq bilan yozilgan kutilma usiz HECH QACHON mos kelmasdi va
 * nosozlik «summa umuman chizilmadi» kabi ko'rinardi.
 */
function normalizedBody(): string {
  return (document.body.textContent ?? "").replaceAll(" ", " ");
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
});

afterEach(() => {
  client.clear();
  clearSession();
});

describe("Bugungi holat bo'limi", () => {
  test("to'rtala qatori ham ko'rinadi va summalar SERVERDAN keladi", async () => {
    routeFetch([dayRow()]);
    renderCard(["market_admin"]);

    await screen.findByText(messages.map.dayStatusTitle);

    const terms = definitionTerms();
    expect(terms).toContain(messages.map.dayStatusState);
    expect(terms).toContain(messages.map.dayStatusAmount);
    expect(terms).toContain(messages.map.dayStatusPaid);
    expect(terms).toContain(messages.map.dayStatusRemaining);

    // Holat yorlig'i — xarita katagining `aria-label` bo'lagi bilan
    // AYNI kalitdan (`map.dayState*`), ikkinchi lug'at yozilmaydi.
    expect(screen.getByText(messages.map.dayStateDue)).toBeInTheDocument();
  });

  test("QOLDIQ SERVERNIKI — klient uni QAYTA HISOBLAMAYDI", async () => {
    /*
     * Sabotajga chidamli shakl: server ATAYIN «nomuvofiq» qoldiq
     * yuboradi (15 000 − 5 000 ≠ 7 777). Klientdagi har qanday ikkinchi
     * ayirish ekranga 10 000 chizardi va bu assert qizarardi.
     */
    routeFetch([dayRow({ remaining_soum: 7_777 })]);
    renderCard(["market_admin"]);

    await screen.findByText(messages.map.dayStatusTitle);

    const body = normalizedBody();
    expect(body).toContain("7 777");
    expect(body).not.toContain("10 000");
  });

  test("hisob yo'q kunda SABAB so'z bilan, summa esa UMUMAN yozilmaydi", async () => {
    routeFetch([
      dayRow({
        state: "no_billing",
        amount_soum: null,
        remaining_soum: null,
        unavailable_reason: "market_closed",
        paid_soum: 0,
      }),
    ]);
    renderCard(["market_admin"]);

    await screen.findByText(messages.map.dayStatusTitle);

    expect(screen.getByText(messages.map.dayReasonMarketClosed)).toBeInTheDocument();
    // ⛔ «Qolgan qarz» qatori UMUMAN yo'q: hisob yo'q kunda u MA'NOSIZ
    //   va nol uni «to'liq to'langan» bilan bir xil ko'rsatardi.
    expect(definitionTerms()).not.toContain(messages.map.dayStatusRemaining);
  });

  test("qator kelmasa bo'lim SARLAVHASI ham chizilmaydi", async () => {
    // ⛔ Boshqa rastaning qatori — indeksda bu rasta YO'Q.
    routeFetch([dayRow({ stall_id: "99999999-9999-4999-8999-999999999999" })]);
    renderCard(["market_admin"]);

    await screen.findByText(STALL_DETAIL.zone_name, { exact: false });

    expect(screen.queryByText(messages.map.dayStatusTitle)).toBeNull();
  });

  test("huquqsiz rolda bo'lim YO'Q va `/billing/map` so'rovi YUBORILMAYDI", async () => {
    /*
     * `platform_admin` da `billing_collect_view` YO'Q (D-C4). Karta
     * ochiladi (`market_data_view` + `vendor_view` bor), lekin bugungi
     * holat bo'limi UMUMAN chizilmaydi.
     */
    routeFetch([dayRow()]);
    renderCard(["platform_admin"]);

    await screen.findByText(STALL_DETAIL.zone_name, { exact: false });

    expect(screen.queryByText(messages.map.dayStatusTitle)).toBeNull();
    const requested = apiFetch.mock.calls.map((call) => String(call[0]));
    expect(requested).not.toContain(MAP_DAY_PATH);
  });
});

describe("Dalil havolasi (D-C7)", () => {
  test("ochiq case'da HAVOLA va case SANASI ko'rinadi", async () => {
    routeFetch([
      dayRow({
        state: "mismatch",
        open_case_id: CASE_ID,
        open_case_service_date: CASE_DATE,
      }),
    ]);
    renderCard(["director"]);

    await screen.findByText(messages.map.dayStatusTitle);
    await screen.findByText(messages.recon.evidenceOpen);

    /*
     * ⛔ CASE SANASI MAJBURIY: «ochiq nomuvofiqlik» bugungi kunniki
     *   bo'lmasligi mumkin va uni bugungi deb ko'rsatish YOLG'ON
     *   bo'lardi (server uni kun bo'yicha filtrlamaydi).
     */
    expect(definitionTerms()).toContain(messages.map.dayStatusCaseDate);
    expect(normalizedBody()).toContain(CASE_DATE);
  });

  test("case YO'Q bo'lsa dalil havolasi CHIZILMAYDI", async () => {
    routeFetch([dayRow()]);
    renderCard(["director"]);

    await screen.findByText(messages.map.dayStatusTitle);

    expect(screen.queryByText(messages.recon.evidenceOpen)).toBeNull();
    expect(definitionTerms()).not.toContain(messages.map.dayStatusCaseDate);
  });

  test("dalil identifikatorlari bo'sh bo'lsa havola CHIZILMAYDI", async () => {
    /*
     * ⛔ `EvidenceLink` NING O'Z QOIDASI (04-band): marshrut bermagan
     *   qator uchun affordans ham, platsholder ham qo'yilmaydi. Bu yerda
     *   u O'ZGARTIRILMASDAN qayta ishlatiladi, ya'ni qoida BEPUL keladi
     *   — test faqat uning haqiqatan kuchda ekanini o'lchaydi.
     */
    routeFetch(
      [
        dayRow({
          state: "mismatch",
          open_case_id: CASE_ID,
          open_case_service_date: CASE_DATE,
        }),
      ],
      { ...CASE_DETAIL, evidence_snapshot_ids: [] },
    );
    renderCard(["director"]);

    await screen.findByText(messages.map.dayStatusTitle);
    // Case sanasi qatori KELADI (u xarita javobidan), havola esa YO'Q.
    await waitFor(() =>
      expect(definitionTerms()).toContain(messages.map.dayStatusCaseDate),
    );
    expect(screen.queryByText(messages.recon.evidenceOpen)).toBeNull();
  });
});
