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
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

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
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

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
    ...overrides,
  };
}

/** Xarita javobi + (ixtiyoriy) bitta rasta batafsil javobi. */
function mockMap(cells: readonly MockCell[], detail?: Record<string, unknown>) {
  apiFetch.mockImplementation((path: string) => {
    if (path === MAP_PATH) {
      return Promise.resolve({
        zones: [{ id: ZONE_ID, name: "A zonasi", cells }],
      });
    }
    if (path.startsWith("/stalls/") && detail) {
      return Promise.resolve(detail);
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

/** Kataklar — DOM tartibida. Legendadagi namunalar tugma EMAS. */
function cellButtons(): HTMLButtonElement[] {
  return Array.from(
    document.querySelectorAll<HTMLButtonElement>("[data-stall-code]"),
  );
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
