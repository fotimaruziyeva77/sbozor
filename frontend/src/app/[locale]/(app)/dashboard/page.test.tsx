/**
 * BOSH EKRAN — BOZOR HOLATI KARTASINING **WIRING** O'LCHOVI (Topilma №H).
 *
 * =============================================================================
 * ⛔ BU FAYL KOMPONENTNI EMAS, DARVOZANI O'LCHAYDI.
 *
 *   `market-status-card.test.tsx` kartaning O'ZINI (holat qatori,
 *   hisoblagichlar, `—`) o'lchaydi. Bu yerdagi savol boshqa: KARTA KIMGA
 *   CHIZILADI. Topshiriq direktor va bozor admini bosh ekraniga tegishni
 *   TAQIQLAYDI (uni 8-faza boyitadi), ya'ni darvozaning o'zi da'voning
 *   bir qismi.
 *
 * ⚠ DARVOZA AYNAN `market_manage` VA TANLOV ASOSLANGAN:
 *     (a) `rbac.ts` matritsasida u FAQAT `platform_admin` da bor —
 *         direktorda ham, bozor adminida ham YO'Q;
 *     (b) kartaning birlamchi amali bozorni faollashtirishga olib boradi
 *         va u aynan `MARKET_MANAGE` ostidagi endpoint;
 *     (c) `market_data_view` bilan darvozalash DIREKTORNI ham qamrab,
 *         taqiqni buzardi.
 *
 * ⚠ H6 IKKI TOMONLAMA: karta chizilmasligi YETARLI EMAS — `setup-status`
 *   ga SO'ROV HAM ketmasligi kerak. Faqat matnni tekshirish «huquq
 *   tekshiruvi so'rovdan OLDIN» kontraktini o'lchamasdi va jurnalga
 *   ma'nosiz 403 lar yozilardi (`cameras/page.test.tsx` da o'rnatilgan
 *   naqsh).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
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
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

import messages from "../../../../../messages/uz-Latn.json";
import DashboardPage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const SETUP_STATUS = {
  zones: 4,
  categories: 5,
  tariffs_covered: 5,
  categories_total: 5,
  stalls: 312,
  stalls_with_category: 312,
  vendors: 187,
  calendar_configured: true,
  cameras: 6,
  can_activate: true,
  blocking: [],
};

/** 7 qatorli tushum javobi — `RevenueCard` sxemasi uchun to'liq shakl. */
const REVENUE_REPORT = {
  from_date: "2026-08-09",
  to_date: "2026-08-15",
  rows: Array.from({ length: 7 }, (_, index) => ({
    business_date: `2026-08-${String(9 + index).padStart(2, "0")}`,
    charged_soum: 700_000,
    collected_soum: 600_000 + index * 10_000,
    diff_soum: -100_000 + index * 10_000,
  })),
  total_collected_soum: 4_550_000,
  total_charged_soum: 5_000_000,
  row_count: 7,
  shown_count: 7,
};

/** KECHAgi yopilgan kun — `OccupancyDonut` sxemasi uchun to'liq shakl. */
const OCCUPANCY_DAY = {
  day: "2026-08-16",
  stalls: 100,
  occupied: 68,
  empty: 24,
  default_empty: 5,
  no_coverage: 3,
  human_confirmed: 12,
  items: [],
};

function routeFetch(): void {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.includes("/setup-status")) return Promise.resolve(SETUP_STATUS);
    if (path === "/users") return Promise.resolve({ items: [] });
    if (path === "/me/headline") {
      return Promise.resolve({ metric: "revenue_today", value: 1250000 });
    }
    if (path.startsWith("/reports/revenue")) {
      return Promise.resolve(REVENUE_REPORT);
    }
    if (path.startsWith("/occupancy")) return Promise.resolve(OCCUPANCY_DAY);
    return Promise.reject(new Error(`kutilmagan so'rov: ${path}`));
  });
}

function requestedPaths(): string[] {
  return apiClientMock.apiFetch.mock.calls.map((call) => String(call[0]));
}

let client: QueryClient;

function renderPage(
  roles: readonly string[],
  options: { isPlatformAdmin?: boolean; marketIsActive?: boolean | null } = {},
) {
  setSession({
    accessToken: "test-access-token",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Foydalanuvchi",
      roles,
      marketId: MARKET_ID,
      marketName: "Karmana markaziy bozori",
      isPlatformAdmin: options.isPlatformAdmin ?? false,
      marketIsActive: options.marketIsActive,
      locale: "uz-Latn",
      mustChangePassword: false,
    },
  });

  return render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
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

/* ---------------------------------------------------------------------------
 * H7 — PLATFORMA ADMINI QORALAMA HOLATINI KO'RADI
 *
 * ⛔⛔ DA'VO O'ZGARDI, MAQSAD O'ZGARMADI (260820).
 *
 *   Ilgari bu test «Bozor holati» KARTASINI qidirardi. Karta to'rt
 *   hisoblagich berardi (rasta · sotuvchi · kamera · foydalanuvchi) va
 *   `AdminPanel` qo'shilgach ular BIR EKRANDA IKKI MARTA turib qoldi —
 *   panelning REESTR bo'limi aynan o'sha sonlarni ko'rsatadi. Karta
 *   panel chizilganda olib tashlandi.
 *
 *   MAQSAD esa o'sha: platforma admini bozor TIRIKMI yoki QORALAMAMI —
 *   bilishi kerak. Endi buni panel sarlavhasidagi «Qoralama» belgisi
 *   aytadi, shuning uchun test aynan shuni qidiradi.
 * ------------------------------------------------------------------------ */

describe("platforma admini", () => {
  test("qoralama bozorda «Qoralama» belgisi chiziladi", async () => {
    routeFetch();
    renderPage(["platform_admin"], {
      isPlatformAdmin: true,
      marketIsActive: false,
    });

    expect(
      await screen.findByText(messages.dashboard.panelDraft),
    ).toBeInTheDocument();
    /* Takroriy karta QAYTMAYDI — bu darvozaning ikkinchi yarmi. */
    expect(document.body.textContent).not.toContain(
      messages.dashboard.marketStatus,
    );
  });

  test("FAOL bozorda «Qoralama» belgisi chizilmaydi", async () => {
    routeFetch();
    renderPage(["platform_admin"], {
      isPlatformAdmin: true,
      marketIsActive: true,
    });

    expect(await screen.findByText("Admin paneli")).toBeInTheDocument();
    expect(
      screen.queryByText(messages.dashboard.panelDraft),
    ).not.toBeInTheDocument();
  });

  test("holat NOMA'LUM bo'lsa belgi chizilmaydi — to'qilgan da'vo yo'q", async () => {
    routeFetch();
    renderPage(["platform_admin"], { isPlatformAdmin: true });

    expect(await screen.findByText("Admin paneli")).toBeInTheDocument();
    expect(
      screen.queryByText(messages.dashboard.panelDraft),
    ).not.toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * H6 — DIREKTOR BOSH EKRANI O'ZGARMAYDI
 * ------------------------------------------------------------------------ */

describe("direktor", () => {
  test("karta UMUMAN chizilmaydi VA `setup-status` ga so'rov ketmaydi", async () => {
    routeFetch();
    renderPage(["director"], { marketIsActive: false });

    /*
     * Sahifaning qolgani ishlaydi — bo'sh ekran EMAS.
     *
     * ⛔ 260818: nishon `nav.dashboard` dan panel sarlavhasiga ko'chdi.
     * ⛔ 260819: sarlavha «Bugun paneli» -> «Bozor paneli». Sabab: panel
     *    endi FAQAT bugunni ko'rsatmaydi — davr tanlanadi (bugun · kecha ·
     *    7/30 kun · kalendardan oraliq), ya'ni eski nom yolg'on bo'lardi.
     *    Direktorda umumiy sarlavha ATAYIN chizilmaydi — `DirectorPanel`
     *    o'z sarlavhasini beradi va ikkalasi birga ikki marta yozilardi.
     *    DA'VO O'ZGARMADI: sahifa bo'sh emas.
     */
    expect(screen.getByText("Bozor paneli")).toBeInTheDocument();

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    expect(document.body.textContent).not.toContain(
      messages.dashboard.marketStatus,
    );

    /*
     * ⛔⛔ `setup-status` SO'ROVI ENDI KUTILADI — VA BU O'ZGARISH
     *     ASOSLANGAN (260820).
     *
     *     Ilgari bu yerda `toEqual([])` turardi va uning sababi
     *     «huquq tekshiruvi so'rovdan OLDIN» kontraktini o'lchash
     *     edi: karta `market_manage` bilan darvozalangan, direktorda
     *     esa u YO'Q.
     *
     *     Endi so'rov BOSHQA sabab bilan ketadi: `SixTiles` undan
     *     kamera sonini o'qib, KAMERASIZ REJIMni aniqlaydi. Pilot
     *     bozor kameralarni keyinroq ulaydi va usiz «Bandlik»
     *     katagida `—` turardi — direktor uni «tizim buzuq» deb
     *     o'qishi mumkin edi.
     *
     *     ⚠ Bu huquq buzilishi EMAS: `GET /markets/{id}/setup-status`
     *       `MARKET_DATA_VIEW` talab qiladi va u direktorda BOR
     *       (`markets.py` docstringi buni ochiq yozgan: «direktor
     *       bozorning to'liqligini KO'RADI, lekin faollashtira
     *       olmaydi»). Marshrut auditga ham yozmaydi.
     *
     *     DA'VONING ASL YARMI SAQLANDI: karta CHIZILMAYDI (yuqorida).
     */
    expect(
      requestedPaths().filter((path) => path.includes("setup-status")),
    ).toHaveLength(1);
  });
});

/* ---------------------------------------------------------------------------
 * BOZOR ADMINI HAM — `market_manage` UNDA YO'Q
 * ------------------------------------------------------------------------ */

describe("bozor admini", () => {
  test("karta chizilmaydi (darvoza `market_manage`, unda YO'Q)", async () => {
    routeFetch();
    renderPage(["market_admin"], { marketIsActive: false });

    /*
     * ⛔⛔ 260819: BOZOR ADMINI ENDI O'Z PANELINI OLADI.
     *
     *     Avval bu yerda «Bozor paneli» kutilardi — bozor adminida ham
     *     `report_view` bor va u DIREKTOR panelini ko'rardi. Ikkalasi
     *     boshqa savolga javob beradi:
     *
     *       direktor     -> «pul to'liq yig'ilyaptimi?»
     *       bozor admini -> «bozorim ishlashga tayyormi?»
     *
     *     Darvoza `tariff_manage` (bozorni KIM boshqarsa, o'sha admin
     *     panelini ko'radi) — `AdminPanel`.
     *
     *     DA'VO O'ZGARMADI: sahifa bo'sh emas VA bozor holati kartasi
     *     (`market_manage`, unda YO'Q) chizilmaydi.
     */
    expect(screen.getByText("Admin paneli")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain(
      messages.dashboard.marketStatus,
    );
  });

  /*
   * ⛔ IKKI PANEL BIR VAQTDA CHIZILMAYDI — bu darvozaning ikkinchi
   *    yarmi. Shartsiz `AdminPanel` qo'shilsa direktor paneli ham
   *    qolib, bozor admini ikkita sarlavha ko'rardi.
   */
  test("direktor paneli ham chizilmaydi — bitta panel, bitta sarlavha", async () => {
    routeFetch();
    renderPage(["market_admin"], { marketIsActive: false });

    expect(screen.getByText("Admin paneli")).toBeInTheDocument();
    expect(screen.queryByText("Bozor paneli")).not.toBeInTheDocument();
  });
});

/* ---------------------------------------------------------------------------
 * G-motion-6(b) — IKKI YANGI KARTA VA KO'R DEKLARATSIYA (09-05 T3)
 *
 * ⛔ IKKI QATLAM MAJBURIY (09-UI-SPEC §16.4): `hidden` sinfi bilan
 *   yashirilgan karta so'rovni BARIBIR yuborardi va summa tarmoq panelida
 *   ko'rinardi. Shuning uchun kassir shoxi IKKITA ALOHIDA test: DOM
 *   qatlami va SO'ROV qatlami — sabotaj (darvozani olib tashlash)
 *   IKKALASINI ham alohida qizartadi.
 *
 * ⛔ Darvoza AYNAN `report_view` (O-03): `director` + `market_admin` da
 *   bor, kassirda YO'Q [VERIFIED: rbac.ts]. `market_manage` bilan
 *   adashtirish DIREKTORNI ham yopardi — buni quyidagi «direktor» testi
 *   ushlaydi.
 * ------------------------------------------------------------------------ */

describe("G-motion-6(b) — kassir tushum va bandlikni KO'RMAYDI", () => {
  test("⛔ DOM qatlami: ikkala karta ham kassir sessiyasida UMUMAN chizilmaydi", async () => {
    routeFetch();
    renderPage(["cashier"]);

    /* Sahifaning qolgani ishlaydi — bo'sh ekran EMAS. */
    expect(screen.getByText(messages.nav.dashboard)).toBeInTheDocument();

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    expect(document.body.textContent).not.toContain(
      messages.dashboard.revenueTrendTitle,
    );
    expect(document.body.textContent).not.toContain(
      messages.dashboard.occupancyTitle,
    );
  });

  test("⛔ SO'ROV qatlami: `/reports/revenue` va `/occupancy` ga chaqiruv soni 0", async () => {
    routeFetch();
    renderPage(["cashier"]);

    await waitFor(() => {
      expect(requestedPaths().length).toBeGreaterThan(0);
    });

    /*
     * ⛔ Shart komponentdan TASHQARIDA bo'lgani uchun so'rov HAM ketmaydi:
     *    huquqsiz sessiyada summa tarmoq panelida ham ko'rinmaydi.
     */
    expect(
      requestedPaths().filter((path) => path.startsWith("/reports/revenue")),
    ).toEqual([]);
    expect(
      requestedPaths().filter((path) => path.startsWith("/occupancy")),
    ).toEqual([]);
  });
});

describe("G-motion-6(b) — direktor OLTI KATAKNI va trendni KO'RADI", () => {
  /*
   * ⛔⛔ DA'VO O'ZGARMADI, YUZA O'ZGARDI (260818, dizayn importi).
   *
   * Ilgari bu test ikkita kartaning SARLAVHASINI qidirardi
   * (`dashboard.revenueTrendTitle`, `dashboard.occupancyTitle`). Panel
   * `Sbozor Direktor.dc.html` bo'yicha qayta qurildi: endi u olti katak
   * va trend kartasidan iborat, sarlavhalar esa dizayndan keladi
   * (katalogda emas — dizayn matni o'zbek lotin tilida qat'iy).
   *
   * ⛔ Tekshiriladigan narsa BIR XIL qoladi va u eng muhimi: direktorda
   *    tushum va bandlik SO'ROVLARI HAQIQATAN ketadi (pastdagi teskari
   *    nazorat) — ya'ni bu test bo'sh detektor ustida yashil qolmaydi.
   */
  test("olti katak, trend va so'rovlar — hammasi BOR", async () => {
    routeFetch();
    renderPage(["director"], { marketIsActive: true });

    await waitFor(() => {
      /* Dizaynning olti katagidan uchtasi — ular birga chiziladi. */
      expect(document.body.textContent).toContain("Kechagi tushum");
      expect(document.body.textContent).toContain("Band, lekin to'lovsiz");
      expect(document.body.textContent).toContain("Qarz jami");
      /* Trend kartasi. */
      expect(document.body.textContent).toContain("Tushum trendi");
    });

    /* Teskari nazorat: so'rovlar HAQIQATAN ketgan — 0-so'rov holatida
     * yuqoridagi kassir testi bo'sh detektor ustida yashil qolardi. */
    expect(
      requestedPaths().some((path) => path.startsWith("/reports/revenue")),
    ).toBe(true);
    expect(
      requestedPaths().some((path) => path.startsWith("/occupancy")),
    ).toBe(true);
  });
});
