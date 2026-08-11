/**
 * SMENA FARQI — ⛔ G-27: IKKI TOMONLAMA VA YOZUV YUZASI AYNAN NOL.
 *
 * =============================================================================
 * ⛔⛔ 1. «KAMOMAD» VA «ORTIQCHA» ⛔ BITTA TESTDA — VA BU MUZOKARASIZ.
 *
 *   D-26 so'zma-so'z: «Ortiqcha naqd ham signal — uni jimgina yutish
 *   kamomadni yashirish bilan BIR XIL xato.» Ikki yo'nalish ikki
 *   ALOHIDA testda bo'lsa, `> 0` shoxini `< 0` ga birlashtirgan
 *   regressiya BITTA testni qizartirardi va uni «shu ham yetadi» deb
 *   o'chirish oson bo'lardi. Bitta testda ular BIR-BIRINI ushlab turadi.
 *
 * ⛔ 2. HAR YO'NALISH ⛔ UCH KANALDA o'lchanadi (WCAG 1.4.1): MATN,
 *   IKONKA va rang. Faqat matnni tekshirish ikonkani almashtirgan
 *   o'zgarishni o'tkazardi; faqat ikonkani tekshirish esa matnsiz
 *   (ya'ni skrinriderga ko'rinmas) katakni.
 *
 * ⛔ 3. YOZUV YUZASI ⛔ TO'PLAM TENGLIGI bilan (D-31/D-32) — bitta nomni
 *   inkor qiladigan da'vo emas. «To'g'rilash» tugmasi yo'qligini
 *   tekshirgan test «Tasdiqlash» tugmasi qo'shilganda ⛔ JIM qolardi.
 *   To'plam tengligi esa ⛔ HAR QANDAY yangi tugmada qizaradi.
 *   ⚠ Taqiqlangan inkor matcher nomi bu izohda LITERAL yozilmaydi:
 *     qabul mezoni uni `grep` bilan sanaydi (kodbaza konvensiyasi).
 *
 * ⛔ 4. MUTLAQ QIYMAT OLINMAGANI EKRANDAN o'lchanadi: `-35 000` da
 *   MINUS ⛔ KO'RINADI. Ishora ma'no tashiydi (Pitfall 7).
 *
 * ⛔ 5. «Smenasiz to'lovlar» qatori `0` da ham ko'rinadi — nol NATIJA
 *   (D-14 ruhi: o'lchanadigan miqdor jimgina yo'qolmaydi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import { VarianceList } from "@/components/billing/variance-list";
import { varianceDirection } from "@/components/billing/variance-cell";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";
import type { ShiftReport, ShiftReportRow } from "@/lib/shift-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-08-09";
const CASHIER_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa";
const CASHIER_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb";
const CASHIER_C = "cccccccc-3333-4333-8333-cccccccccccc";

function row(overrides: Partial<ShiftReportRow> = {}): ShiftReportRow {
  return {
    id: "99999999-9999-4999-8999-999999999999",
    cashier_id: CASHIER_A,
    opened_at: "2026-08-09T03:00:00Z",
    closed_at: "2026-08-09T12:00:00Z",
    declared_soum: 100_000,
    system_soum: 100_000,
    variance_soum: 0,
    ...overrides,
  };
}

function report(overrides: Partial<ShiftReport> = {}): ShiftReport {
  return {
    day: DAY,
    rows: [],
    shiftless_payment_count: 0,
    shiftless_payment_soum: 0,
    ...overrides,
  };
}

function routeFetch(data: ShiftReport): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/shifts")) return Promise.resolve(data);
    if (path.startsWith("/users")) {
      return Promise.resolve({
        items: [CASHIER_A, CASHIER_B, CASHIER_C].map((id, index) => ({
          id,
          phone: `+99890000000${index}`,
          full_name: `Kassir ${index + 1}`,
          roles: ["cashier"],
          is_active: true,
          must_change_password: false,
          locale: "uz-Latn",
          created_at: "2026-08-01T05:00:00Z",
        })),
      });
    }
    return Promise.resolve({ items: [] });
  });
}

let client: QueryClient;

function renderList() {
  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <VarianceList day={DAY} />
        </AuthProvider>
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/** Blok ildizi — G-25 (b) atributi bo'yicha (sahifadan MUSTAQIL). */
function block(): HTMLElement {
  const node = document.querySelector('[data-billing-content="shifts"]');
  if (node === null) throw new Error("shifts bloki topilmadi");
  return node as HTMLElement;
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
});

afterEach(() => {
  client.clear();
  clearSession();
});

/* -------------------------------------------------------------------------- */
/* 0. SOF FUNKSIYA                                                            */
/* -------------------------------------------------------------------------- */

describe("varianceDirection — uch shox, to'rtinchisi yo'q", () => {
  test("manfiy -> kamomad, musbat -> ortiqcha, nol -> mos keldi", () => {
    expect(varianceDirection(-1)).toBe("short");
    expect(varianceDirection(1)).toBe("over");
    expect(varianceDirection(0)).toBe("match");
  });
});

/* -------------------------------------------------------------------------- */
/* 1. (a) + (b) — IKKI YO'NALISH BITTA TESTDA                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-27: farq IKKI TOMONLAMA ko'rsatiladi (D-26)", () => {
  test("⛔ «Kamomad» VA «Ortiqcha» — ikkalasi ham MATN va IKONKA bilan", async () => {
    routeFetch(
      report({
        rows: [
          row({
            id: "11111111-aaaa-4aaa-8aaa-111111111111",
            cashier_id: CASHIER_A,
            declared_soum: 65_000,
            system_soum: 100_000,
            variance_soum: -35_000,
          }),
          row({
            id: "22222222-bbbb-4bbb-8bbb-222222222222",
            cashier_id: CASHIER_B,
            declared_soum: 112_000,
            system_soum: 100_000,
            variance_soum: 12_000,
          }),
        ],
      }),
    );
    renderList();

    /* --- MATN kanali — IKKALA yo'nalish ham --- */
    expect(
      await screen.findByText(messages.billing.varianceShort),
    ).toBeInTheDocument();
    expect(screen.getByText(messages.billing.varianceOver)).toBeInTheDocument();

    /*
     * --- IKONKA kanali — `lucide` sinf nomlari bo'yicha ---
     *
     * ⛔ IKKALASI ALOHIDA: `> 0` shoxini `< 0` ga birlashtirgan sabotaj
     *   (S-F) aynan shu yerda qizaradi — «tushish» ikonkasi ikki marta
     *   chiqib, «o'sish» ikonkasi umuman yo'qoladi.
     */
    const icons = new Set(
      [...block().querySelectorAll("svg")].flatMap((node) =>
        [...node.classList].filter((name) => name.startsWith("lucide-trending")),
      ),
    );
    expect(icons).toEqual(
      new Set(["lucide-trending-down", "lucide-trending-up"]),
    );
  });

  test("(c) farq NOL bo'lganda «Mos keldi»", async () => {
    routeFetch(report({ rows: [row({ variance_soum: 0 })] }));
    renderList();

    expect(
      await screen.findByText(messages.billing.varianceMatch),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 2. (e) — MUTLAQ QIYMAT OLINMAYDI                                           */
/* -------------------------------------------------------------------------- */

describe("⛔ ishora MA'NO TASHIYDI (Pitfall 7)", () => {
  test("⛔ `-35 000` ekranda MINUS bilan ko'rinadi", async () => {
    routeFetch(
      report({
        rows: [
          row({ declared_soum: 65_000, system_soum: 100_000, variance_soum: -35_000 }),
        ],
      }),
    );
    renderList();

    await screen.findByText(messages.billing.varianceShort);

    /*
     * ⛔ FORMATLANGAN QIYMAT — literal yozilmaydi: kutilma AYNAN
     *   komponent ishlatadigan formatlagichdan hosila qilinadi, ya'ni
     *   locale ajratgichi o'zgarsa test qizarmaydi, LEKIN minus
     *   yo'qolsa qizaradi.
     */
    const expected = new Intl.NumberFormat("uz-Latn").format(-35_000);
    const text = block().textContent ?? "";
    expect(text.includes(expected)).toBe(true);
  });
});

/* -------------------------------------------------------------------------- */
/* 3. (d) — YOZUV YUZASI AYNAN NOL                                            */
/* -------------------------------------------------------------------------- */

describe("⛔ G-27(d): yozuv yuzasi AYNAN NOL (D-26)", () => {
  test("⛔ blokdagi interaktiv elementlar to'plami AYNAN BO'SH", async () => {
    routeFetch(
      report({
        rows: [
          row({ id: "11111111-aaaa-4aaa-8aaa-111111111111", variance_soum: -35_000 }),
          row({
            id: "22222222-bbbb-4bbb-8bbb-222222222222",
            cashier_id: CASHIER_B,
            variance_soum: 12_000,
          }),
          row({
            id: "33333333-cccc-4ccc-8ccc-333333333333",
            cashier_id: CASHIER_C,
            variance_soum: 0,
          }),
        ],
      }),
    );
    renderList();

    /* NAZORAT: jadval CHIZILDI — «bo'sh to'plam» bo'sh ekrandan emas. */
    await screen.findByText(messages.billing.varianceShort);
    expect(block().querySelectorAll("tbody tr").length).toBe(3);

    const interactive = new Set(
      [
        ...block().querySelectorAll("button, a, input, select, textarea"),
      ].map((node) => (node.textContent ?? "").trim()),
    );

    /*
     * ⛔ TO'PLAM TENGLIGI: [To'g'rilash], [Tasdiqlash], [Izoh qo'shish],
     *   [Kechirish] — har qanday YANGI tugma ham shu yerda qizaradi.
     */
    expect(interactive).toEqual(new Set());
  });
});

/* -------------------------------------------------------------------------- */
/* 4. (f) — SMENASIZ TO'LOVLAR                                                */
/* -------------------------------------------------------------------------- */

describe("⛔ smenasiz to'lovlar JIM YO'QOLMAYDI", () => {
  test("sanoq `2` bo'lganda qator ko'rinadi", async () => {
    routeFetch(
      report({
        rows: [row()],
        shiftless_payment_count: 2,
        shiftless_payment_soum: 45_000,
      }),
    );
    renderList();

    await screen.findByText(new RegExp(messages.billing.shiftlessPayments, "u"));
    const text = block().textContent ?? "";
    expect(text.includes(new Intl.NumberFormat("uz-Latn").format(45_000))).toBe(
      true,
    );
  });

  test("⛔ sanoq `0` bo'lganda HAM ko'rinadi — nol NATIJA", async () => {
    routeFetch(
      report({
        rows: [row()],
        shiftless_payment_count: 0,
        shiftless_payment_soum: 0,
      }),
    );
    renderList();

    expect(
      await screen.findByText(new RegExp(messages.billing.shiftlessPayments, "u")),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* 5. BO'SH HOLAT №7 — BO'SH `<div>` EMAS                                     */
/* -------------------------------------------------------------------------- */

describe("bo'sh holat №7", () => {
  test("⛔ smena yo'q kunda blok O'Z MATNINI ko'rsatadi", async () => {
    routeFetch(report({ rows: [] }));
    renderList();

    expect(
      await screen.findByText(messages.billing.emptyShifts),
    ).toBeInTheDocument();
    /* Blok o'rami HAMON o'z mazmun atributini chiqaradi (G-25 b). */
    await waitFor(() => expect(block()).toBeInTheDocument());
  });

  test("kassir ismi KLIENTDA joinlanadi (§5.5)", async () => {
    routeFetch(report({ rows: [row({ cashier_id: CASHIER_A })] }));
    renderList();

    expect(await screen.findByText("Kassir 1")).toBeInTheDocument();
    /* Ism `GET /users` dan keldi — moliyaviy javobdan emas. */
    const paths = (apiClientMock.apiFetch.mock.calls as [string][]).map(
      ([path]) => path,
    );
    expect(paths.some((path) => path.startsWith("/users"))).toBe(true);
  });
});

/* -------------------------------------------------------------------------- */
/* 6. NAZORAT — `within` ishlatilgani (blok ildizi HAQIQIY)                    */
/* -------------------------------------------------------------------------- */

describe("nazorat", () => {
  test("blok ildizi topiladi va u jadvalning ONASI", async () => {
    routeFetch(report({ rows: [row()] }));
    renderList();

    await screen.findByText(messages.billing.varianceMatch);
    expect(within(block()).getAllByRole("row").length).toBeGreaterThan(1);
  });
});
