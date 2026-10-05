/**
 * =============================================================================
 * PLAN-XARITA DARVOZASI (MARKET-06 / SC#5).
 *
 * Bu fayl UCHTA jimgina buziladigan xulqni qulflaydi — ularning hech biri
 * typecheck, lint yoki build'da ko'rinmaydi va ekran ochilganda ham
 * "ishlayotgandek" turadi:
 *
 *   1. TARTIB (§7.3). Inson-raqamli tartib serverdan keladi (`code_sort`).
 *      Frontend uni qayta saralasa xarita ochiladi, chiroyli ko'rinadi va
 *      rasta TOPILMAYDI — 2, 10, 100 o'rniga 1, 10, 100, 2 chiqadi.
 *   2. QAYTA RENDER (Pitfall 8). Tanlangan ID katakning propiga tushsa
 *      har bosishda 1000 katak qayta render bo'ladi. Ekran ishlaydi,
 *      shunchaki sekin — ya'ni buni faqat O'LCHASH bilan ushlash mumkin.
 *   3. RANG YAGONA SIGNAL EMASLIGI (WCAG 1.4.1). "Sotuvchisiz" farqi uzuq
 *      chegara bilan beriladi; u yo'qolsa hech qanday test qizarmasdi.
 *
 * DIQQAT: bosish `fireEvent` bilan qilinadi — `@testing-library/user-event`
 * tasdiqlangan paket ro'yxatida yo'q va faqat shu fayl uchun yangi
 * bog'liqlik qo'shish mutanosib emas (01-12 naqshi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useCallback, useState } from "react";
import type { ComponentProps, ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

/*
 * ⛔ `@/i18n/navigation` MOCK'I — `StallCardDialog` -> `EvidenceLink`
 *    ZANJIRI TUFAYLI (quick 260816-75e).
 *
 * Karta dalil havolasini chizadi va u `Link` ni `@/i18n/navigation` dan
 * oladi; `next-intl/navigation` -> `next/navigation` zanjiri esa vitest
 * ESM ostida YECHILMAYDI. Mocksiz bu fayl «0 test» bilan yiqiladi —
 * `forbidden-notice.tsx` da hujjatlashgan o'lchovning aynan o'zi.
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

import messages from "../../../messages/uz-Latn.json";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

/*
 * KATAK RENDER SANOG'I.
 *
 * Josus HAQIQIY katakni chaqiradi va O'ZI ham `memo` bilan o'raladi.
 * `memo` siz o'ram komponentning O'ZI har ota-render'da yangilanardi va
 * o'lchov "proplar o'zgardimi?" degan savolga emas, "ota qayta render
 * bo'ldimi?" degan savolga javob berardi — ya'ni Pitfall 8 ni umuman
 * o'lchamasdi.
 *
 * O'ramning memoizatsiyasi HAQIQIY komponentnikini YASHIRISHI mumkin,
 * shuning uchun pastda MUSTAQIL nazorat testi bor: u `stall-cell.tsx`
 * eksporti chindan ham memoizatsiyalangan ekanini tekshiradi.
 */
const cellSpy = vi.hoisted(() => ({ onRender: vi.fn() }));

vi.mock("@/components/stalls/stall-cell", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("@/components/stalls/stall-cell")>();
  const { memo } = await import("react");
  const Real = actual.StallCell;

  // Sanoq `vi.fn()` CHAQIRUVLARI bilan olib boriladi, tashqi o'zgaruvchini
  // o'zgartirish bilan emas: oxirgisini React Compiler qoidasi taqiqlaydi
  // (`react-hooks/immutability`) va u to'g'ri qiladi — render paytida
  // tashqi holatni yozish haqiqiy kodda ham xato bo'lardi.
  const Counted = memo(function CountedStallCell(
    props: React.ComponentProps<typeof Real>,
  ) {
    cellSpy.onRender();
    return <Real {...props} />;
  });

  return { ...actual, StallCell: Counted };
});

/** Josus qayd qilgan katak renderlari soni. */
function cellRenderCount(): number {
  return cellSpy.onRender.mock.calls.length;
}

const { apiFetch } = apiClientMock;

import { StallCardDialog } from "@/components/stalls/stall-card-dialog";
import { StallMap } from "@/components/stalls/stall-map";
import type { StallTone } from "@/components/stalls/stall-map-types";
import { TONE_STYLES } from "@/components/stalls/stall-tone";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { MAP_DAY_PATH } from "@/lib/map-day-queries";

const MAP_PATH = "/stalls/map";
const ZONE_ID = "11111111-1111-4111-8111-111111111111";

/**
 * Domen so'rovlari sessiyadagi bozorsiz UMUMAN ketmaydi (CR-01): kalit
 * `market_id` bilan doiralangan va `enabled` sharti `marketId !== null`.
 * Shuning uchun bu test ham haqiqiy sessiya bilan ishlaydi.
 */
const MARKET_ID = "99999999-9999-4999-8999-999999999999";

type MockCell = {
  id: string;
  code: string;
  status: "active" | "maintenance" | "closed";
  has_vendor: boolean;
  plan_x: number | null;
  plan_y: number | null;
};

function cell(
  code: string,
  overrides: Partial<MockCell> = {},
): MockCell {
  return {
    id: `cell-${code}`,
    code,
    status: "active",
    has_vendor: true,
    plan_x: null,
    plan_y: null,
    ...overrides,
  };
}

/*
 * ===========================================================================
 * TO'LOV QATLAMINING SOXTA JAVOBI (`GET /billing/map`, MARKET-06).
 *
 * ⚠ MAVJUD TESTLAR UCHUN STANDART — BO'SH `rows` BILAN FAOL BOZOR.
 *   Ular inventar ranglarini o'lchaydi va to'lov qatlami ularga TEGMASLIGI
 *   kerak. Standartni «so'rov rad etiladi» qilib qoldirish esa har testda
 *   xato bannerini chizardi va o'lchov nima haqidaligi noaniq bo'lardi.
 * ===========================================================================
 */
type MockDayState = "paid" | "due" | "mismatch" | "free" | "no_billing";

type MockDayRow = {
  stall_id: string;
  state: MockDayState;
  amount_soum: number | null;
  unavailable_reason: "market_closed" | "tariff_missing" | null;
  paid_soum: number;
  remaining_soum: number | null;
  open_case_id: string | null;
  open_case_service_date: string | null;
};

type MockDayStatus = {
  service_date: string;
  market_active: boolean;
  market_open: boolean | null;
  rows: readonly MockDayRow[];
};

const DAY_AMOUNT = 15_000;

function dayRow(
  stallId: string,
  state: MockDayState,
  overrides: Partial<MockDayRow> = {},
): MockDayRow {
  const noBilling = state === "no_billing";
  const paid = state === "paid" ? DAY_AMOUNT : 0;
  return {
    stall_id: stallId,
    state,
    amount_soum: noBilling ? null : DAY_AMOUNT,
    unavailable_reason: noBilling ? "tariff_missing" : null,
    paid_soum: paid,
    remaining_soum: noBilling ? null : DAY_AMOUNT - paid,
    open_case_id: null,
    open_case_service_date: null,
    ...overrides,
  };
}

function dayStatus(overrides: Partial<MockDayStatus> = {}): MockDayStatus {
  return {
    service_date: "2026-08-16",
    market_active: true,
    market_open: true,
    rows: [],
    ...overrides,
  };
}

/** Xarita javobi + (ixtiyoriy) bitta rasta batafsil javobi. */
function mockMap(
  cells: readonly MockCell[],
  detail?: Record<string, unknown>,
  day: MockDayStatus = dayStatus(),
) {
  apiFetch.mockImplementation((path: string) => {
    if (path === MAP_PATH) {
      return Promise.resolve({
        zones: [{ id: ZONE_ID, name: "A zonasi", cells }],
      });
    }
    if (path === MAP_DAY_PATH) {
      return Promise.resolve(day);
    }
    if (path.startsWith("/stalls/") && detail) {
      return Promise.resolve(detail);
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

type MockZone = { id: string; name: string; cells: readonly MockCell[] };

/** Bir NECHTA zonali xarita javobi — miqyos testi uchun. */
function mockZones(zones: readonly MockZone[]) {
  apiFetch.mockImplementation((path: string) => {
    if (path === MAP_PATH) {
      return Promise.resolve({ zones });
    }
    if (path === MAP_DAY_PATH) {
      return Promise.resolve(dayStatus());
    }
    return Promise.reject(new Error(`kutilmagan yo'l: ${path}`));
  });
}

/**
 * Sinov qobig'i — SAHIFANING xulqini takrorlaydi: tanlangan ID SHU YERDA
 * yashaydi va xaritaga TUSHMAYDI (Pitfall 8).
 */
function Harness() {
  const [selectedStallId, setSelectedStallId] = useState<string | null>(null);
  const openStall = useCallback((stallId: string) => {
    setSelectedStallId(stallId);
  }, []);

  return (
    <>
      <StallMap focusCode="" onSelectStall={openStall} />
      <StallCardDialog
        onClose={() => setSelectedStallId(null)}
        stallId={selectedStallId}
      />
    </>
  );
}

function renderMap(): ReturnType<typeof render> {
  // `retry: false` — xato holatida test uch marta qayta urinishni kutmasin.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  const tree: ReactElement = (
    <NextIntlClientProvider locale="uz-Latn" messages={messages}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <Harness />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>
  );

  return render(tree);
}

/** Bozor admini — xarita va rasta kartasi shu kontekstda o'qiladi. */
function seedMarketAdminSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Admin",
      roles: ["market_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: false,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/** Platforma admini — unda `billing_collect_view` ⛔ YO'Q (D-C4). */
function seedPlatformAdminSession(): void {
  setSession({
    accessToken: "test-access-token",
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
      phone: "+998900000001",
      fullName: "Platforma admini",
      roles: ["platform_admin"],
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: true,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
    markets: [],
  });
}

/** Kataklar — DOM tartibida. Legendadagi namunalar tugma EMAS. */
function cellButtons(): HTMLButtonElement[] {
  return Array.from(
    document.querySelectorAll<HTMLButtonElement>("[data-stall-code]"),
  );
}

/** Kod bo'yicha bitta katak. */
function cellByCode(code: string): HTMLButtonElement {
  const button = document.querySelector<HTMLButtonElement>(
    `[data-stall-code="${code}"]`,
  );
  if (button === null) throw new Error(`${code} katagi topilmadi`);
  return button;
}

/**
 * Katak SHU tone uslubini oldimi?
 *
 * ⚠ TOKENMA-TOKEN, `className` SATRIDA `toContain` BILAN EMAS: `cn()`
 *   (tailwind-merge) ziddiyatli sinflarni olib tashlaydi va tartibni
 *   o'zgartirishi mumkin, ya'ni satr taqqoslash JIMGINA yolg'on-qizil
 *   bo'lardi. Kutilgan qiymat MAHSULOT konstantasidan olinadi, testda
 *   ikkinchi marta YOZILMAYDI.
 */
function hasTone(button: HTMLElement, tone: StallTone): boolean {
  return TONE_STYLES[tone]
    .split(" ")
    .every((token) => button.classList.contains(token));
}

/** Katakdagi TO'LOV ikonkasi (pastki-chap burchak). */
function dayIcon(button: HTMLElement): Element | null {
  return button.querySelector("[data-day-tone]");
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  seedMarketAdminSession();
});

afterEach(() => {
  clearSession();
});

describe("StallMap — tartib (§7.3)", () => {
  test("kataklar SERVER tartibida chiziladi (frontend saralamaydi)", async () => {
    // ⚠ Tartib ATAYIN "noto'g'ri": server `code_sort` bo'yicha nima bersa,
    // xarita AYNAN shuni chizishi kerak. Klient saralashi bu ro'yxatni
    // "10, 100, 2, 7" ga aylantirardi.
    mockMap([cell("2"), cell("10"), cell("100"), cell("7")]);
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(4));

    const codes = cellButtons().map((button) =>
      button.getAttribute("data-stall-code"),
    );
    expect(codes).toEqual(["2", "10", "100", "7"]);
  });

  test("`10` `2` dan KEYIN keladi — leksikografik tartib emas", async () => {
    /*
     * §7.3 ning jimgina buziladigan qismi. Yuqoridagi test butun
     * ketma-ketlikni tekshiradi; bu esa AYNAN o'sha juftlikni ajratib
     * oladi, chunki xato eng avval shu yerda ko'rinadi: matn ustunida
     * `"10" < "2"`.
     */
    mockMap([cell("2"), cell("10")]);
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(2));

    const codes = cellButtons().map((button) =>
      button.getAttribute("data-stall-code"),
    );
    expect(codes.indexOf("10")).toBeGreaterThan(codes.indexOf("2"));
  });
});

describe("StallMap — qayta render (Pitfall 8)", () => {
  test("1000 katak: tanlash gridni QAYTA RENDER QILMAYDI", async () => {
    const cells = Array.from({ length: 1000 }, (_, index) =>
      cell(String(index + 1)),
    );
    mockMap(cells, {
      id: "cell-1",
      code: "1",
      zone_id: ZONE_ID,
      zone_name: "A zonasi",
      category_id: null,
      category_name: null,
      status: "active",
      vendor_id: null,
      vendor_name: null,
      tariff_soum: 8000,
      created_at: "2026-08-01T00:00:00Z",
      phone: null,
      assignment_from: null,
      note: null,
    });

    renderMap();
    await waitFor(() => expect(cellButtons()).toHaveLength(1000));

    // Boshlang'ich render sanoqdan CHIQARILADI — o'lchanadigan narsa
    // faqat TANLASHDAN keyingi ish. Nazorat: u chindan ham 1000 edi.
    expect(cellRenderCount()).toBe(1000);
    cellSpy.onRender.mockClear();

    fireEvent.click(cellButtons()[0]);

    await waitFor(() =>
      expect(screen.getByRole("dialog")).toBeInTheDocument(),
    );

    /*
     * Chegara 2, 0 emas: roving tabindex bitta katakni tab-stop qilib,
     * boshqasini bo'shatishi mumkin, ya'ni ikkita katak qonuniy ravishda
     * yangilanadi. 1000 esa aynan Pitfall 8 ning imzosi.
     */
    expect(cellRenderCount()).toBeLessThanOrEqual(2);
  }, 30_000);

  test("NAZORAT: `stall-cell.tsx` eksporti HAQIQATAN memoizatsiyalangan", async () => {
    /*
     * Yuqoridagi o'lchov josus O'RAMINING memoizatsiyasi bilan
     * bajariladi, ya'ni u `stall-cell.tsx` dan `memo` olib tashlansa ham
     * yashil qolardi. Bu nazorat aynan o'sha bo'shliqni yopadi va
     * haqiqiy modulni (mock'siz) o'qiydi.
     */
    const actual = await vi.importActual<
      typeof import("@/components/stalls/stall-cell")
    >("@/components/stalls/stall-cell");

    expect(
      (actual.StallCell as unknown as { $$typeof: symbol }).$$typeof,
    ).toBe(Symbol.for("react.memo"));
  });
});

describe("StallMap — a11y va rang yagona signal emasligi", () => {
  test("katak TO'LIQ `aria-label` beradi va u KESILMAYDI", async () => {
    // Kod ATAYIN 6 belgidan uzun: vizual matn kesiladi, `aria-label` esa
    // to'liq qolishi shart (§7.4).
    mockMap([cell("A-1234567", { status: "maintenance", has_vendor: false })]);
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(1));

    const label = cellButtons()[0].getAttribute("aria-label") ?? "";

    // To'rt bo'lak: raqam, holat, toifa, sotuvchi.
    expect(label).toContain("A-1234567");
    expect(label).toContain(messages.stalls.status.maintenance);
    expect(label).toContain(messages.map.cellCategoryUnknown);
    expect(label).toContain(messages.stalls.noVendor);

    // Vizual matn kesiladi — lekin faqat VIZUAL.
    expect(cellButtons()[0].className).toContain("truncate");
    expect(cellButtons()[0].getAttribute("title")).toContain("A-1234567");
  });

  test("sotuvchisiz katak UZUQ-UZUQ chegara oladi (rang yagona signal emas)", async () => {
    mockMap([cell("1", { has_vendor: true }), cell("2", { has_vendor: false })]);
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(2));

    const [withVendor, withoutVendor] = cellButtons();
    expect(withVendor.className).toContain("border-solid");
    expect(withoutVendor.className).toContain("border-dashed");
  });
});

describe("Rasta kartasi (§7.6)", () => {
  test("katak bosilganda karta ochiladi va rasta raqami ko'rinadi", async () => {
    mockMap([cell("42")], {
      id: "cell-42",
      code: "42",
      zone_id: ZONE_ID,
      zone_name: "A zonasi",
      category_id: null,
      category_name: "Sabzavot",
      status: "active",
      vendor_id: null,
      vendor_name: "Karimov A.",
      tariff_soum: 8000,
      created_at: "2026-08-01T00:00:00Z",
      phone: "+998901234567",
      assignment_from: "2026-07-01",
      note: null,
    });

    renderMap();
    await waitFor(() => expect(cellButtons()).toHaveLength(1));

    fireEvent.click(cellButtons()[0]);

    const dialog = await screen.findByRole("dialog");
    await waitFor(() =>
      expect(dialog.textContent).toContain("Karimov A."),
    );

    // Sarlavhada rasta raqami; DB kontenti — tarjima qilinmaydi.
    expect(dialog.textContent).toContain("42");
    expect(dialog.textContent).toContain("Sabzavot");
  });

  test("tarifsiz rasta kartada XATO sifatida ko'rsatiladi (D-08)", async () => {
    mockMap([cell("7")], {
      id: "cell-7",
      code: "7",
      zone_id: ZONE_ID,
      zone_name: "A zonasi",
      category_id: null,
      category_name: "Sabzavot",
      status: "active",
      vendor_id: null,
      vendor_name: null,
      // ⚠ D-08 fail-closed: tarifsiz rasta kunlik patta hisobiga umuman
      // tushmaydi va anomaliyaga aylanadi, ya'ni bu HAQIQIY nosozlik.
      tariff_soum: null,
      created_at: "2026-08-01T00:00:00Z",
      phone: null,
      assignment_from: null,
      note: null,
    });

    renderMap();
    await waitFor(() => expect(cellButtons()).toHaveLength(1));

    fireEvent.click(cellButtons()[0]);

    const noTariff = await screen.findByText(messages.stalls.noTariff);
    // Ogohlantirish uslubi MAJBURIY — neytral matn adminni anomaliyadan
    // bexabar qoldirardi.
    expect(noTariff.className).toContain("text-danger-text");
  });
});

/*
 * ===========================================================================
 * TO'LOV RANG QATLAMI (MARKET-06 / TEST-REPORT Topilma №C).
 *
 * 2-faza `stall-tone.ts` da uchta BO'SH tone (`paid`/`debt`/`mismatch`)
 * qoldirgan: «6–7 fazalar bu uchtasini TO'LDIRADI». Bu blok o'sha
 * to'ldirishni qulflaydi va u UCH KANALNI birdan o'lchaydi (WCAG 1.4.1):
 *
 *   1. RANG      — `TONE_STYLES` tokenlari katakning `classList` ida;
 *   2. IKONKA    — `[data-day-tone]` elementi va uning ichidagi `svg`;
 *   3. MATN      — `aria-label` ning ALOHIDA bo'lagi va legenda satri.
 *
 * ⛔ RANG YOLG'IZ O'LCHANSA darvoza rangdan mustaqil kanallar olib
 *    tashlanganda ham YASHIL qolardi — ya'ni u himoya qilishi kerak
 *    bo'lgan aynan o'sha qoidani (§4.4) o'lchamasdi.
 * ===========================================================================
 */
describe("StallMap — to'lov rang qatlami (MARKET-06)", () => {
  test("NAZORAT: to'rt to'lov toni BIR-BIRIDAN farq qiladi", () => {
    /*
     * Usiz quyidagi «paid ko'k, due qizil» da'volari ikkala tone bir xil
     * uslub bergan holatda ham yashil bo'lardi — aynan 2-fazadagi
     * platsholder holati (uchalasi `neutral` bilan bir xil edi).
     */
    const styles = [
      TONE_STYLES.paid,
      TONE_STYLES.debt,
      TONE_STYLES.mismatch,
      TONE_STYLES.free,
      TONE_STYLES.neutral,
    ];

    expect(new Set(styles).size).toBe(styles.length);
  });

  test("beshala holat RANG + IKONKA + `aria-label` bo'lagi bilan ajraladi", async () => {
    mockMap(
      [cell("1"), cell("2"), cell("3"), cell("4"), cell("5")],
      undefined,
      dayStatus({
        rows: [
          dayRow("cell-1", "paid"),
          dayRow("cell-2", "due"),
          dayRow("cell-3", "mismatch", {
            open_case_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            open_case_service_date: "2026-08-14",
          }),
          dayRow("cell-4", "free"),
          dayRow("cell-5", "no_billing"),
        ],
      }),
    );
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(5));
    await waitFor(() => expect(hasTone(cellByCode("1"), "paid")).toBe(true));

    const expected: ReadonlyArray<[string, StallTone, string]> = [
      ["1", "paid", messages.map.dayStatePaid],
      ["2", "debt", messages.map.dayStateDue],
      ["3", "mismatch", messages.map.dayStateMismatch],
      ["4", "free", messages.map.dayStateFree],
    ];

    for (const [code, tone, label] of expected) {
      const button = cellByCode(code);
      expect(hasTone(button, tone)).toBe(true);
      // 2-kanal: ikonka — HAQIQIY `svg`, faqat atribut emas.
      expect(dayIcon(button)?.getAttribute("data-day-tone")).toBe(tone);
      expect(dayIcon(button)?.querySelector("svg")).not.toBeNull();
      // 3-kanal: `aria-label` ning ALOHIDA bo'lagi.
      expect(button.getAttribute("aria-label")).toContain(label);
    }

    /*
     * ⛔ `no_billing` — RANG QO'YILMAYDIGAN YAGONA HOLAT: katak INVENTAR
     *    tonida qoladi. Unga kulrang «to'lanmagan» rangi berish yopiq
     *    kunni qarzdorlikdan ajratmasdi.
     */
    const noBilling = cellByCode("5");
    expect(hasTone(noBilling, "neutral")).toBe(true);
    expect(dayIcon(noBilling)).toBeNull();
  });

  test("qoralama bozorda banner ko'rinadi va BIRORTA katak to'lov rangini olmaydi", async () => {
    mockMap(
      [cell("1"), cell("2")],
      undefined,
      // ⛔ Server `market_active = false` deganda `rows` BO'SH keladi va
      //    `market_open` `null` — «o'lchanmadi», «yopiq» EMAS.
      dayStatus({ market_active: false, market_open: null, rows: [] }),
    );
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(2));
    await screen.findByText(messages.map.marketDraftNotice);

    for (const button of cellButtons()) {
      expect(hasTone(button, "neutral")).toBe(true);
      expect(dayIcon(button)).toBeNull();
    }
  });

  test("bugun bozor yopiq bo'lsa banner ko'rinadi (yolg'on qizil YO'Q)", async () => {
    mockMap(
      [cell("1")],
      undefined,
      dayStatus({
        market_open: false,
        rows: [dayRow("cell-1", "no_billing", { unavailable_reason: "market_closed" })],
      }),
    );
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(1));
    await screen.findByText(messages.map.marketClosedNotice);

    expect(hasTone(cellByCode("1"), "debt")).toBe(false);
    expect(dayIcon(cellByCode("1"))).toBeNull();
  });

  test("legenda to'lov satrlarini FAQAT qatlam yuklanganda ko'rsatadi", async () => {
    mockMap(
      [cell("1")],
      undefined,
      dayStatus({ rows: [dayRow("cell-1", "paid")] }),
    );
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(1));

    for (const line of [
      messages.map.legendPaid,
      messages.map.legendDue,
      messages.map.legendMismatch,
      messages.map.legendFree,
      messages.map.legendNoBilling,
    ]) {
      expect(await screen.findByText(line)).toBeInTheDocument();
    }

    // Inventar satrlari TEGILMAYDI — ular HAR DOIM ko'rinadi.
    expect(screen.getByText(messages.map.legendMaintenance)).toBeInTheDocument();
  });

  test("huquqsiz rolda `/billing/map` so'rovi UMUMAN yuborilmaydi", async () => {
    /*
     * ⛔ O'CHIRILGAN ELEMENT EMAS, PLATSHOLDER EMAS — YO'Q (D-C4).
     *
     * Platforma adminida `billing_collect_view` YO'Q va u SOZLASH roli.
     * Unda xarita INVENTAR rejimida qoladi: yolg'on yashil chizishdan
     * ko'ra qatlamni umuman ko'rsatmaslik halolroq.
     */
    clearSession();
    seedPlatformAdminSession();
    mockMap([cell("1")]);
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(1));

    const requested = apiFetch.mock.calls.map((call) => call[0] as string);
    expect(requested).toContain(MAP_PATH);
    expect(requested).not.toContain(MAP_DAY_PATH);

    // Legendada to'lov satrlari ham, banner ham YO'Q.
    expect(screen.queryByText(messages.map.legendPaid)).toBeNull();
    expect(screen.queryByText(messages.map.marketDraftNotice)).toBeNull();
    expect(dayIcon(cellByCode("1"))).toBeNull();
  });

  test("to'lov qatlami xato bersa xarita CHIZILADI, sabab esa aytiladi", async () => {
    /*
     * ⛔ XARITA BLOKLANMAYDI: inventar ma'lumoti KELGAN va uni to'lov
     *    qatlamining nosozligi sababli yashirish adminni butun ekrandan
     *    mahrum qilardi. Sabab BITTA `role="status"` qatorida aytiladi.
     */
    apiFetch.mockImplementation((path: string) => {
      if (path === MAP_PATH) {
        return Promise.resolve({
          zones: [{ id: ZONE_ID, name: "A zonasi", cells: [cell("1")] }],
        });
      }
      return Promise.reject(new Error("map-day so'rovi yiqildi"));
    });
    renderMap();

    await waitFor(() => expect(cellButtons()).toHaveLength(1));
    await screen.findByText(messages.map.dayLayerError);

    expect(dayIcon(cellByCode("1"))).toBeNull();
  });
});

/*
 * ===========================================================================
 * KARMANA MIQYOSI (02-23).
 *
 * Miqyos raqamlari `tests/fixtures/karmana_seed.py` dagi
 * `KARMANA_ZONE_COUNT = 8` va `KARMANA_STALL_COUNT = 600` bilan bir xil.
 * Ular BU YERDA qayta yozilgan va boshqa iloji yo'q — Python konstantasini
 * vitest'ga import qilib bo'lmaydi. Ajralib ketish xavfi ochiq qoldiriladi
 * va u `02-VALIDATION.md` da nomlangan.
 *
 * ⚠ BU TEST O'QILISHNI BAHOLAMAYDI. jsdom shrift, kontrast va skroll
 * masofasini o'lchay olmaydi, ya'ni «xarita real miqyosda O'QILADIMI?»
 * degan savol PERSEPTUAL bo'lib qoladi va u `02-VALIDATION.md` ning
 * `human_only_verifications` bandi sifatida, egasi va ishga tushish
 * sharti bilan yuritiladi. Bu yerda MEXANIK yarmi yopiladi: real
 * miqyosda birorta rasta TUSHIB QOLMAYDI.
 * ===========================================================================
 */
const KARMANA_ZONE_COUNT = 8;
const KARMANA_STALL_COUNT = 600;
const CELLS_PER_ZONE = KARMANA_STALL_COUNT / KARMANA_ZONE_COUNT;

describe("StallMap — Karmana miqyosi", () => {
  test("8 zona × 75 katak: DOM'da AYNAN 600 katak va 8 zona bloki", async () => {
    const zones: MockZone[] = Array.from(
      { length: KARMANA_ZONE_COUNT },
      (_, zoneIndex) => ({
        id: `zone-${zoneIndex}`,
        name: `${zoneIndex + 1}-qator`,
        cells: Array.from({ length: CELLS_PER_ZONE }, (_, cellIndex) =>
          cell(String(zoneIndex * CELLS_PER_ZONE + cellIndex + 1)),
        ),
      }),
    );

    mockZones(zones);
    renderMap();

    await waitFor(() =>
      expect(cellButtons()).toHaveLength(KARMANA_STALL_COUNT),
    );

    // Zona bloklari — har zona uchun BITTA `<section class="zone-block">`.
    expect(document.querySelectorAll(".zone-block")).toHaveLength(
      KARMANA_ZONE_COUNT,
    );

    /*
     * Sanoq YOLG'IZ o'zi yetarli emas: bitta katak IKKI marta, boshqasi
     * esa umuman chizilmagan holatda ham u 600 bo'lardi. Shuning uchun
     * KODLAR to'plami serverdan kelgan to'plam bilan AYNAN solishtiriladi.
     */
    const codes = cellButtons().map((button) =>
      button.getAttribute("data-stall-code"),
    );
    const expected = zones.flatMap((zone) => zone.cells.map((c) => c.code));
    expect(codes).toEqual(expected);
    expect(new Set(codes).size).toBe(KARMANA_STALL_COUNT);
  }, 30_000);
});

/*
 * ===========================================================================
 * TO'LANGAN = YASHIL, TO'LANMAGAN = QIZIL (261005, buyurtmachi qarori).
 *
 * ILGARI TESKARI EDI: `paid` binafsha (`accent`), yashil esa `free` —
 * ya'ni «sotuvchi biriktirilmagan» — degani edi. Bozorda ishlaydigan odam
 * yashil katakni ko'rib «to'landi» deb o'qirdi, holbuki o'sha rastada
 * umuman sotuvchi yo'q edi. Rang eng muhim savolga TESKARI javob berardi.
 *
 * Bu darvoza rang MA'NOSINI qulflaydi, aniq sinf matnini emas: tint
 * zichligi yoki halqa qalinligi dizayn qarori va u o'zgarishi mumkin.
 * ===========================================================================
 */
describe("to'lov ranglari — ma'nosi (261005)", () => {
  test("⛔ TO'LANGAN rasta YASHIL (`success`)", () => {
    expect(TONE_STYLES.paid).toContain("bg-success");
  });

  test("⛔ TO'LANMAGAN rasta QIZIL (`danger`)", () => {
    expect(TONE_STYLES.debt).toContain("bg-danger");
  });

  test("⛔ YASHIL BOSHQA HECH NARSANI anglatmaydi", () => {
    /*
     * ASOSIY DA'VO. Usiz `paid` ni yashil qilib, `free` ni ham yashil
     * qoldirish mumkin edi — va o'shanda xaritada ikki xil holat bir xil
     * ko'rinardi, ya'ni tuzatish hech narsani hal qilmasdi.
     */
    const yashillar = Object.entries(TONE_STYLES)
      .filter(([, cls]) => cls.includes("bg-success"))
      .map(([tone]) => tone);

    expect(yashillar).toEqual(["paid"]);
  });

  test("⚠ sotuvchisi yo'q rasta to'lov rangini OLMAYDI", () => {
    // U na to'lagan, na qarzdor — «o'yindan tashqarida», ya'ni neytral.
    expect(TONE_STYLES.free).not.toContain("bg-success");
    expect(TONE_STYLES.free).not.toContain("bg-danger");
    expect(TONE_STYLES.free).not.toContain("bg-accent");
  });

  test("QUYI CHEGARA: reyestr haqiqatan o'qildi", () => {
    /*
     * `TONE_STYLES` bo'sh yoki import buzilgan bo'lsa yuqoridagi
     * `.not.toContain` lar TRIVIAL o'tardi.
     */
    expect(Object.keys(TONE_STYLES).length).toBeGreaterThanOrEqual(8);
    expect(TONE_STYLES.debt.length).toBeGreaterThan(10);
  });
});
