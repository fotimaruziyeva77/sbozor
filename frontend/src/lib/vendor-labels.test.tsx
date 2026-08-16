/**
 * ⛔ 07 `deferred-items.md` №2 — ISM BO'SHLIG'I (D-08, §5.5).
 *
 * =============================================================================
 * ⛔⛔ NOSOZLIK: YORLIQ LUG'ATI REESTRNING ⛔ BIRINCHI SAHIFASI BILAN
 *     CHEKLANGAN EDI.
 *
 * `useVendorsQuery` — KEYSET sahifalangan so'rov (`PAGE_SIZE = 50`), lekin
 * lug'at ⛔ `fetchNextPage()` ni HECH QACHON chaqirmasdi. Ya'ni 50 dan
 * ortiq sotuvchili bozorda ro'yxatning quyi qismidagi HAR qator
 * «Ko'rsatilmagan» yorlig'ini olardi — va u ⛔ YOLG'ON emas, lekin
 * ⛔ FOYDASIZ edi: direktor «bu kim?» savoliga javob ololmasdi.
 *
 * ⛔ D-08 IKKI MEXANIKADAN BIRINI ruxsat beradi va tanlanganI —
 *    ⛔ MAVJUD, AUDIT QILINGAN `GET /vendors` MARSHRUTINI SAHIFALASH.
 *    Nomuvofiqlik marshrutiga `vendor_name` maydoni ⛔ QO'SHILMAYDI:
 *    07-10 buni SABOTAJ bilan o'lchagan — ism qo'shilganda to'rt tenancy
 *    testi qizaradi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ IKKI QO'RIQCHI VA ULAR MUZOKARASIZ
 * -----------------------------------------------------------------------
 *   (1) ⛔ SAHIFA SONI CHEGARASI — `GET /vendors` HAR chaqiruvda
 *       `audit_read` yozadi (D-09), ya'ni chegarasiz halqa audit
 *       jurnalini ma'nosiz yozuvlar bilan to'ldirardi va katta reestrda
 *       u ⛔ CHEKSIZ bo'lardi;
 *   (2) ⛔ CHEGARADAN KEYIN — ⛔ BO'SH KATAK. `labelOf()` `null`
 *       qaytaradi va lug'at ⛔ HECH NIMA TO'QIMAYDI (05-14 darsi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../messages/uz-Latn.json";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import { useVendorLabels } from "@/lib/vendor-labels";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/**
 * ⛔ SERVER SAHIFASINING O'LCHAMI VA LUG'AT CHEGARASI — ⛔ TESTDA QAYTA
 *    YOZILGAN, moduldan IMPORT QILINMAGAN.
 *
 * Darvoza o'zi tekshirayotgan qiymatni tekshirilayotgan moduldan olsa,
 * ikkalasi BIRGA o'zgarganda da'vo ⛔ JIMGINA yashil qolardi (05-13
 * darsi, `case-list.test.tsx` dagi `PAGE_SIZE` bilan AYNI naqsh).
 */
const PAGE_SIZE = 50;
const EXPECTED_MAX_PAGES = 20;

/** `p{index}` — kursorning UNUMSIZ shakli (klient uni PARSE QILMAYDI). */
function vendorId(index: number): string {
  return `33333333-3333-4333-8333-${String(index).padStart(12, "0")}`;
}

function vendorName(index: number): string {
  return `Sotuvchi ${index}`;
}

/**
 * `GET /vendors` ni `pages` sahifa bilan javob beradigan qilib sozlaydi.
 *
 * @param pages umumiy sahifalar soni; `Infinity` — server HECH QACHON
 *   tugamaydi (chegara qo'riqchisini o'lchash uchun).
 */
function routeVendors(pages: number): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (!path.startsWith("/vendors")) {
      return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
    }

    const cursor = new URL(`http://x${path}`).searchParams.get("cursor");
    const pageIndex = cursor === null ? 0 : Number(cursor.slice(1));

    const items = Array.from({ length: PAGE_SIZE }, (_, offset) => {
      const index = pageIndex * PAGE_SIZE + offset + 1;
      return {
        id: vendorId(index),
        full_name: vendorName(index),
        phone: `+99890${String(index).padStart(7, "0")}`,
        stall_count: 0,
        created_at: "2026-08-01T00:00:00Z",
      };
    });

    const hasNext = pageIndex + 1 < pages;
    return Promise.resolve({
      items,
      next_cursor: hasNext ? `p${pageIndex + 1}` : null,
    });
  });
}

/**
 * Lug'atning YAGONA iste'molchisi — ⛔ MATN TUGUNI yo'q bo'lsa katak BO'SH.
 *
 * ⛔ `?? "—"` kabi zaxira ATAYIN YOZILMAGAN: aynan shu to'qilgan qiymat
 *    o'lchanadigan nuqson (05-14). Katak bo'shligi `textContent === ""`
 *    bilan o'lchanadi.
 */
function Probe({ ids }: { ids: readonly string[] }) {
  const labels = useVendorLabels();

  return (
    <ul>
      {ids.map((id) => (
        <li data-vendor={id} key={id}>
          {labels.labelOf(id)}
        </li>
      ))}
    </ul>
  );
}

function renderProbe(ids: readonly string[]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <Probe ids={ids} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/** `/vendors` ga ketgan so'rovlar soni — AUDIT SHOVQININING o'lchovi. */
function vendorRequestCount(): number {
  return apiClientMock.apiFetch.mock.calls.filter((call) =>
    String(call[0]).startsWith("/vendors"),
  ).length;
}

function cellText(container: HTMLElement, id: string): string {
  const node = container.querySelector(`[data-vendor="${id}"]`);
  if (node === null) throw new Error(`katak topilmadi: ${id}`);
  return node.textContent ?? "";
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "44444444-4444-4444-8444-444444444444",
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
});

/* -------------------------------------------------------------------------- */
/* (a) BIRINCHI SAHIFADAN KEYINGI ISM HAM KO'RINADI                           */
/* -------------------------------------------------------------------------- */

describe("⛔ 07 №2: lug'at BIRINCHI sahifa bilan CHEKLANMAYDI", () => {
  test("⛔ 120 sotuvchili bozorda 51-chi va 120-chi ism KO'RINADI", async () => {
    /* 120 sotuvchi = 3 sahifa (50 + 50 + 20 -> mock 50 beradi, muhimi CHEGARA). */
    routeVendors(3);

    const ids = [vendorId(1), vendorId(51), vendorId(120)];
    const { container } = renderProbe(ids);

    await waitFor(() => {
      expect(vendorRequestCount()).toBe(3);
    });

    await waitFor(() => {
      /*
       * ⛔ 51-CHI — NOSOZLIKNING AYNAN CHEGARASI: eski lug'at faqat
       *   birinchi sahifani o'qirdi va bu katak «Ko'rsatilmagan» bo'lardi.
       */
      expect(cellText(container, vendorId(51))).toBe(vendorName(51));
    });

    expect(cellText(container, vendorId(1))).toBe(vendorName(1));
    expect(cellText(container, vendorId(120))).toBe(vendorName(120));
  });

  test("bitta sahifali bozorda AYNAN BITTA so'rov ketadi (audit shovqini)", async () => {
    /*
     * ⛔ AUDIT SHOVQINI O'LCHANADI, taxmin QILINMAYDI: `GET /vendors`
     *   HAR chaqiruvda `audit_read` yozadi (D-09). Kichik bozorda
     *   sahifalash ⛔ HECH QANDAY qo'shimcha yozuv tug'dirmasligi kerak.
     */
    routeVendors(1);

    const { container } = renderProbe([vendorId(1)]);

    await waitFor(() => {
      expect(cellText(container, vendorId(1))).toBe(vendorName(1));
    });

    expect(vendorRequestCount()).toBe(1);
  });
});

/* -------------------------------------------------------------------------- */
/* (b) CHEGARA VA UNDAN KEYINGI BO'SH KATAK                                   */
/* -------------------------------------------------------------------------- */

describe("⛔ 07 №2: sahifa soni CHEGARALANGAN va chegaradan keyin BO'SH", () => {
  test("⛔ server tugamasa ham so'rovlar soni CHEGARADA to'xtaydi", async () => {
    /*
     * ⛔⛔ CHEKSIZ HALQA — ⛔ ENG QIMMAT XATO: u audit jurnalini
     *     ma'nosiz «ko'rildi» yozuvlari bilan to'ldirardi va server
     *     tomonda hech qanday xato ham bermasdi (har so'rov `200`).
     *
     * ⛔ SERVER BU YERDA HECH QACHON TUGAMAYDI (`next_cursor` doim bor),
     *    ya'ni to'xtatuvchi YAGONA narsa — klientdagi chegara.
     */
    routeVendors(Number.POSITIVE_INFINITY);

    renderProbe([vendorId(1)]);

    await waitFor(() => {
      expect(vendorRequestCount()).toBe(EXPECTED_MAX_PAGES);
    });

    /* ⛔ VA U O'SMAYDI: keyingi tiklarda ham AYNI son. */
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(vendorRequestCount()).toBe(EXPECTED_MAX_PAGES);
  });

  test("⛔ chegaradan KEYINGI ism — BO'SH KATAK, to'qilgan qiymat EMAS", async () => {
    routeVendors(Number.POSITIVE_INFINITY);

    /* Chegaradan keyingi sahifada turadigan sotuvchi. */
    const beyond = vendorId(EXPECTED_MAX_PAGES * PAGE_SIZE + 7);
    const { container } = renderProbe([vendorId(1), beyond]);

    await waitFor(() => {
      expect(vendorRequestCount()).toBe(EXPECTED_MAX_PAGES);
    });

    /* NAZORAT: chegara ICHIDAGI ism KELDI — lug'at umuman ishlayapti. */
    expect(cellText(container, vendorId(1))).toBe(vendorName(1));

    /*
     * ⛔ BO'SH KATAK: na «—», na «Noma'lum», na identifikator bo'lagi.
     *   Yorliqni TO'QISH nizo hujjatiga (D-02) YOLG'ON ism kiritardi.
     */
    expect(cellText(container, beyond)).toBe("");
  });

  test("⛔ MANBA SKANI: lug'atda TO'QILGAN qiymat yo'q", async () => {
    /*
     * ⛔ DOM da'vosi FAQAT o'lchangan holatni ko'radi; manba skani esa
     *   zaxira qiymatning KODDA borligini ko'rsatadi — u boshqa shoxda
     *   ham chizilishi mumkin.
     */
    const { existsSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");

    const file = join(process.cwd(), "src", "lib", "vendor-labels.ts");
    if (!existsSync(file)) throw new Error(`modul topilmadi: ${file}`);

    const source = readFileSync(file, "utf8");
    const code = source
      .split("\n")
      /* ⛔ IZOHLAR CHIQARILADI: sabab matnida «—» belgisi QONUNIY. */
      .filter((line) => !/^\s*(\*|\/\*|\/\/)/u.test(line))
      .join("\n");

    expect(code).not.toContain("—");
    expect(code).not.toContain("Noma'lum");
  });
});
