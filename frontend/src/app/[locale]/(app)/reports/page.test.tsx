/**
 * ⛔ G-37 (08-UI-SPEC) — BLOK TO'PLAMI, ⛔ MAZMUN JUFTLIGI VA HAQIQIY MAZMUN.
 *
 * =============================================================================
 * ⛔⛔ DARVOZA UCH QATLAMLI VA UCHALASI HAR XIL NARSANI O'LCHAYDI.
 *     Bu bo'linish 06-fazadagi G-25 ning ⛔ O'LCHANGAN KO'RLIGIDAN olingan.
 *
 * (a) ⛔ BLOK TO'PLAMI — beshala blok ⛔ DAVRDAN QAT'I NAZAR chiziladi.
 *     Sabab §8.1 da: maksimum ALLAQACHON kecha (§4.4), ya'ni «ma'lumot
 *     hali tug'ilmagan» holati ⛔ UMUMAN YUZAGA KELMAYDI. Blokni bo'sh
 *     davrda yashirish esa bo'sh natijani ⛔ MUVAFFAQIYAT kabi
 *     ko'rsatardi — direktor «bu oyda qarzdorlik bo'limi chiqmadi» ni
 *     «qarzdor yo'q» deb o'qirdi. ⛔ Bo'sh davr — BO'SH HOLAT, yo'q blok
 *     emas.
 *
 * (c) ⛔⛔ MAZMUN JUFTLIGI — ENG QIMMAT BAND. (a) YOLG'IZ bo'sh
 *     `<div data-report-block="revenue" />` ni ⛔ MUKAMMAL o'tkazardi:
 *     butun hisobot yuzasi ⛔ CHIZILMAGAN holda darvoza, task VA faza
 *     ⛔ YASHIL qaytardi. Shuning uchun mazmun atributini ⛔ RO'YXAT
 *     KOMPONENTINING O'ZI chiqaradi.
 *
 * (d) ⛔ SAHIFA MAZMUN ATRIBUTINI HECH QACHON YOZMAYDI. Agar yozsa,
 *     sahifa (c) ni platsholder bilan qondira olardi — ya'ni o'zining
 *     false-green iga o'zi yo'l ochardi.
 *
 * (e) ⛔ HAQIQIY MAZMUN MOCK'DAN HOSILA — «biror matn bormi?» EMAS.
 *     Har da'vo mock javobidagi AYNAN o'sha qiymatga qadalgan.
 *
 * ⛔ SABOTAJ SHU FAYLNING KONTRAKTI (reja Task 2): `<RevenueReport/>` ->
 *   `<div data-report-block="revenue"/>` qo'yilganda (a) ⛔ YASHIL
 *   QOLISHI, (c) ⛔ VA (e) esa ⛔ QIZARISHI kutiladi. Uchala natija ham
 *   SUMMARY da qayd etilgan — bu darvozaning nima uchun uch qatlamdan
 *   iboratligining ISBOTI.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { beforeEach, describe, expect, test, vi } from "vitest";

/*
 * `@/i18n/navigation` Next.js router kontekstiga tayanadi va u jsdom'da
 * YO'Q (`app-shell.test.tsx` va `reconciliation/page.test.tsx` bilan AYNI
 * sabab). Mock `Link` ni oddiy `<a>` ga aylantiradi va `href` ni
 * O'ZGARISHSIZ uzatadi.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/reports",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../../../messages/uz-Latn.json";
import ReportsPage from "./page";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const USER_ID = "33333333-3333-4333-8333-333333333333";

/** ⛔ YAGONA LAHZA — literal sana YO'Q, ikkala davr ham undan HOSILA. */
const NOW = new Date();
const TODAY = businessDayIn(TIME_ZONE, NOW);
const YESTERDAY = shiftIsoDay(TODAY, -1);

/**
 * ⛔ IKKI XIL DAVR — (a) ning MUZOKARASIZ sharti.
 *
 * Ikkalasi ham `normalizePeriod` dan O'ZGARISHSIZ o'tadi: shakli to'g'ri,
 * `from <= to` va `to <= kecha`. Aks holda ikkala render ham AYNI
 * standart oraliqqa tushardi va «davrdan qat'i nazar» da'vosi
 * ⛔ TAVTOLOGIYAGA aylanardi.
 */
const PERIOD_A = { from: shiftIsoDay(YESTERDAY, -9), to: YESTERDAY };
const PERIOD_B = { from: shiftIsoDay(YESTERDAY, -59), to: shiftIsoDay(YESTERDAY, -30) };

/**
 * ⛔ BLOK REYESTRI — kutilma SHU YERDA, mahsulot kodidan IMPORT QILINMAYDI.
 *
 * Import qilingan reyestr darvozani o'zi tekshirayotgan qiymatga bog'lab
 * qo'yardi: blok o'chirilsa kutilma HAM o'chardi va tenglik JIMGINA rost
 * bo'lib qolardi (05-15 darsi).
 */
const BLOCKS = ["period", "revenue", "debtors", "anomalies", "accuracy"];

/**
 * ⛔ MAZMUN ATRIBUTIDAN OZOD BLOKLAR — AYNAN BITTA.
 *
 * Davr tanlagichi — ⛔ BOSHQARUV, ro'yxat emas. To'plamning O'LCHAMI
 * alohida assert bilan qulflanadi: istisnolar ro'yxati o'sib ketsa,
 * mazmun juftligi darvozasi asta-sekin BO'SHASHARDI va oxirida hech
 * nimani tekshirmasdi.
 */
const CONTENT_EXEMPT = new Set(["period"]);

/* -------------------------------------------------------------------------- */
/* MOCK JAVOBLAR — (e) ning KUTILMALARI SHULARDAN HOSILA QILINADI            */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ SUMMALAR UCH XONALI. Sabab MEXANIK: `Intl.NumberFormat` to'rt
 *   xonadan boshlab guruh AJRATGICHI (uzilmas bo'shliq) qo'yadi va
 *   Testing Library uni normalizatsiya qiladi — ya'ni «400000» satri
 *   DOM'da hech qachon topilmasdi. Uch xonali qiymat AYNAN o'zi bo'lib
 *   chiziladi.
 */
const REVENUE_ROWS = [
  {
    business_date: "2026-09-05",
    charged_soum: 411,
    collected_soum: 402,
    diff_soum: -9,
  },
  {
    business_date: "2026-09-06",
    charged_soum: 413,
    collected_soum: 413,
    diff_soum: 0,
  },
];

const DEBTOR_ROWS = [
  {
    vendor_id: "44444444-4444-4444-8444-444444444444",
    vendor_name: "Olimjon Karimov",
    stall_codes: ["14-C"],
    outstanding_soum: 421,
    oldest_debt_date: "2026-09-05",
  },
];

const ANOMALY_ROWS = [
  {
    business_date: "2026-09-05",
    kind: "unregistered",
    stall_code: "31-A",
    snapshot_id: null,
    case_status: null,
  },
];

/** ⛔ Matritsa katagi — uch xonali va shu sababdan DOM'da AYNAN o'zi. */
const MATRIX_CELL = 401;

function revenuePayload(rows = REVENUE_ROWS) {
  return {
    from_date: "2026-09-01",
    to_date: "2026-09-30",
    rows,
    total_collected_soum: 815,
    total_charged_soum: 824,
    row_count: rows.length,
    shown_count: rows.length,
  };
}

function debtorsPayload(rows = DEBTOR_ROWS) {
  return {
    from_date: "2026-09-01",
    to_date: "2026-09-30",
    rows,
    total_outstanding_soum: 421,
    row_count: rows.length,
    shown_count: rows.length,
  };
}

function anomaliesPayload(rows = ANOMALY_ROWS) {
  return {
    from_date: "2026-09-01",
    to_date: "2026-09-30",
    rows,
    unpaid_count: 0,
    unregistered_count: rows.length,
    row_count: rows.length,
    shown_count: rows.length,
  };
}

function accuracyPayload(matrixCell = MATRIX_CELL) {
  return {
    from_date: "2026-09-01",
    to_date: "2026-09-30",
    drawn: 700,
    answered: 612,
    unanswered: 88,
    dont_know: 0,
    matrix: {
      true_occupied: matrixCell,
      false_occupied: 23,
      false_empty: 38,
      true_empty: 150,
    },
    n: 612,
    measured: true,
    min_sample: 20,
    base_rate: 0.717,
    correct: { point: 0.9004, lower: 0.8747, upper: 0.9215 },
    false_occupied: { point: 0.0542, lower: 0.0364, upper: 0.08 },
    false_empty: { point: 0.0866, lower: 0.0637, upper: 0.1165 },
  };
}

/**
 * Marshrutlarni mock'laydi — ⛔ HAR BLOK O'Z ma'lumotini oladi.
 *
 * Mock'lanmagan marshrut ATAYIN `reject` qiladi: jimgina `undefined`
 * qaytarish blokni «yuklanmoqda» holatida abadiy qoldirardi va (c)
 * bo'sh DOM ustida yugurardi.
 */
function routeFetch({
  revenue = revenuePayload(),
  debtors = debtorsPayload(),
  anomalies = anomaliesPayload(),
  accuracy = accuracyPayload(),
} = {}) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reports/revenue")) return Promise.resolve(revenue);
    if (path.startsWith("/reports/debtors")) return Promise.resolve(debtors);
    if (path.startsWith("/reports/anomalies")) return Promise.resolve(anomalies);
    if (path.startsWith("/occupancy/accuracy")) return Promise.resolve(accuracy);
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });
}

async function renderPage(period: { from: string; to: string }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={NOW}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={`?from=${period.from}&to=${period.to}`}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <ReportsPage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  /*
   * ⚠ IKKI BOSQICHLI KUTISH va ikkalasi ham KERAK:
   *   (1) bloklar chizildi (`Suspense` chegarasi ochildi);
   *   (2) ⛔ birorta blok HAMON yuklanmayapti.
   *
   * Faqat (1) ni kutish (c) va (e) ni TAVTOLOGIYAGA aylantirardi: skelet
   * holatidagi blok ham mazmun atributini chiqaradi (u ATAYIN shunday —
   * atribut HAR holatda eng tashqi elementda), ya'ni mazmun da'vosi hali
   * kelmagan ma'lumot ustida yugurardi.
   */
  await waitFor(() => {
    expect(
      view.container.querySelectorAll("[data-report-block]").length,
    ).toBeGreaterThan(0);
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

function attrValues(container: HTMLElement, attribute: string): Set<string> {
  return new Set(
    [...container.querySelectorAll(`[${attribute}]`)].map(
      (node) => node.getAttribute(attribute) ?? "",
    ),
  );
}

/**
 * `YYYY-MM-DD` -> ekranda ko'rinadigan satr.
 *
 * ⛔ `formatBusinessDay` ⛔ IMPORT QILINMAYDI (05-15 darsi): darvoza o'zi
 *    tekshirayotgan yordamchiga bog'lanib qolsa, ikkalasi BIRGA
 *    o'zgarganda JIMGINA yashil qolardi. Shakl `lib/format-day.ts` ning
 *    yozilgan kontraktidan QAYTA quriladi: kun ⛔ 12:00 UTC ga
 *    langarlanadi va `dateStyle: "medium"` bilan chiziladi.
 */
/*
 * ⛔ MUSTAQIL QAYTA QURISH SAQLANADI — bu jadval `lib/uz-latn-date.ts` dan
 *    IMPORT QILINMAYDI. Import qilinsa, u yerdagi xato bu yerda ham
 *    takrorlanib, test jimgina yashil qolardi.
 * Shakl: «D-oy, YYYY», kun 12:00 UTC ga langarlangan.
 */
const UZ_MONTHS = [
  "yanvar",
  "fevral",
  "mart",
  "aprel",
  "may",
  "iyun",
  "iyul",
  "avgust",
  "sentabr",
  "oktabr",
  "noyabr",
  "dekabr",
];

function shownDay(iso: string): string {
  const [year, month, day] = iso.split("-").map(Number);
  const at = new Date(Date.UTC(year, month - 1, day, 12));
  return `${at.getUTCDate()}-${UZ_MONTHS[at.getUTCMonth()]}, ${at.getUTCFullYear()}`;
}

beforeEach(() => {
  vi.resetAllMocks();
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: USER_ID,
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
  routeFetch();
});

/* -------------------------------------------------------------------------- */
/* (a) BLOK TO'PLAMI — ⛔ DAVRDAN QAT'I NAZAR TENG                            */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (a): blok to'plami DAVRDAN MUSTAQIL", () => {
  test("⛔ birinchi davr -> AYNAN beshala blok", async () => {
    const { container } = await renderPage(PERIOD_A);

    /*
     * ⛔ TENGLIK, «bormi?» EMAS: qo'shimcha blok qo'shilsa «aniqlik bor»
     *   da'vosi YASHIL qolardi. Tenglik HAR QANDAY chetlanishda qizaradi.
     */
    expect(attrValues(container, "data-report-block")).toEqual(new Set(BLOCKS));
  });

  test("⛔ IKKINCHI davr -> AYNAN O'SHA to'plam", async () => {
    const { container } = await renderPage(PERIOD_B);

    expect(attrValues(container, "data-report-block")).toEqual(new Set(BLOCKS));
  });

  test("⛔ BO'SH javob ham to'plamni O'ZGARTIRMAYDI (§8.1)", async () => {
    /*
     * ⛔ BU BAND (a) NING ENG QIMMAT YARMI. «Ma'lumot yo'q -> blokni
     *   yashirish» eng tabiiy noto'g'ri refleks, va u bo'sh davrni
     *   MUVAFFAQIYAT kabi ko'rsatardi: chizilmagan «Qarzdorlik ro'yxati»
     *   direktorga «qarzdor yo'q» bo'lib o'qilardi. Bo'sh davr —
     *   BO'SH HOLAT, yo'q blok EMAS.
     */
    routeFetch({
      revenue: revenuePayload([]),
      debtors: debtorsPayload([]),
      anomalies: anomaliesPayload([]),
    });

    const { container } = await renderPage(PERIOD_A);

    expect(attrValues(container, "data-report-block")).toEqual(new Set(BLOCKS));
  });
});

/* -------------------------------------------------------------------------- */
/* (c) MAZMUN JUFTLIGI — BO'SH O'RAM O'TMAYDI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (c): mazmun juftligi", () => {
  test("⛔ istisnolar to'plami AYNAN BITTA a'zoli (alohida assert)", () => {
    /*
     * ⛔ ALOHIDA DA'VO va u MUZOKARASIZ: istisno qo'shish darvozani
     *   BO'SHASHTIRADIGAN yagona yo'l, ya'ni u ko'zga tashlanishi kerak.
     */
    expect(CONTENT_EXEMPT.size).toBe(1);
    expect(CONTENT_EXEMPT.has("period")).toBe(true);
  });

  test("⛔ birinchi davr: mazmun to'plami = bloklar \\ istisno", async () => {
    const { container } = await renderPage(PERIOD_A);

    const blocks = attrValues(container, "data-report-block");
    const expected = new Set(
      [...blocks].filter((block) => !CONTENT_EXEMPT.has(block)),
    );

    /* ⛔ Da'vo (a) DAN HOSILA — qo'lda yozilgan ikkinchi ro'yxat emas. */
    expect(attrValues(container, "data-report-content")).toEqual(expected);
  });

  test("⛔ IKKINCHI davr: mazmun to'plami = bloklar \\ istisno", async () => {
    const { container } = await renderPage(PERIOD_B);

    const blocks = attrValues(container, "data-report-block");
    const expected = new Set(
      [...blocks].filter((block) => !CONTENT_EXEMPT.has(block)),
    );

    expect(attrValues(container, "data-report-content")).toEqual(expected);
  });
});

/* -------------------------------------------------------------------------- */
/* (d) SAHIFA MAZMUN ATRIBUTINI YOZMAYDI                                      */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (d): sahifa MANBASI toza", () => {
  test("⛔ `page.tsx` da mazmun atributi 0 marta", async () => {
    const { existsSync, readFileSync } = await import("node:fs");
    const { join } = await import("node:path");

    /*
     * ⚠ `import.meta.url` vite transformidan keyin `file:` sxemasida
     *   EMAS — yo'l `process.cwd()` dan quriladi (07-05 da o'lchangan).
     *   ⛔ Fayl topilmasa test `throw` qiladi: `skip` ham, jim o'tish ham
     *   darvozani JIMGINA o'chirardi.
     */
    const file = join(
      process.cwd(),
      "src",
      "app",
      "[locale]",
      "(app)",
      "reports",
      "page.tsx",
    );
    if (!existsSync(file)) throw new Error(`sahifa fayli topilmadi: ${file}`);

    const source = readFileSync(file, "utf8");

    /*
     * ⛔ Atribut sahifada bo'lsa, sahifa (c) ni PLATSHOLDER bilan
     *   qondira olardi — ya'ni o'zining false-green iga o'zi yo'l
     *   ochardi. Atributning NOMI ham manba faylda uchramaydi.
     */
    expect((source.match(/data-report-content/gu) ?? []).length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* (e) HAQIQIY MAZMUN — MOCK'DAN HOSILA                                       */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (e): mazmun MOCK'DAGI AYNAN QIYMATGA qadalgan", () => {
  test("⛔ `revenue` — mock'dagi kun VA qator SONI", async () => {
    const { container } = await renderPage(PERIOD_A);
    const block = container.querySelector('[data-report-content="revenue"]');

    expect(block).not.toBeNull();
    expect(block?.textContent).toContain(shownDay(REVENUE_ROWS[0].business_date));

    /*
     * ⛔ QATOR SONI — mock'dagi massiv UZUNLIGIDAN hosila. Bu «biror
     *   jadval bormi?» dan kuchliroq: qatorlarni jimgina tashlab
     *   ketadigan filtr aynan shu yerda qizaradi.
     */
    expect(block?.querySelectorAll("tbody tr").length).toBe(REVENUE_ROWS.length);
  });

  test("⛔ `debtors` — mock'dagi sotuvchi ISMI", async () => {
    const { container } = await renderPage(PERIOD_A);
    const block = container.querySelector('[data-report-content="debtors"]');

    expect(block?.textContent).toContain(DEBTOR_ROWS[0].vendor_name);
    expect(block?.querySelectorAll("tbody tr").length).toBe(DEBTOR_ROWS.length);
  });

  test("⛔ `anomalies` — mock'dagi `kind` ning YORLIG'I", async () => {
    const { container } = await renderPage(PERIOD_A);
    const block = container.querySelector('[data-report-content="anomalies"]');

    /*
     * ⛔ Da'vo YORLIQQA qadalgan, xom `kind` ga emas: xom qiymat ekranda
     *   HECH QACHON ko'rinmaydi (u ikki sinfning MEXANIK nomi), yorliq
     *   esa arxivning butun ma'nosi.
     */
    expect(block?.textContent).toContain(messages.reports.anomaliesUnregistered);
    expect(block?.querySelectorAll("tbody tr").length).toBe(ANOMALY_ROWS.length);
  });

  test("⛔ `accuracy` — mock'dagi matritsa KATAGI", async () => {
    const { container } = await renderPage(PERIOD_A);
    const block = container.querySelector('[data-report-content="accuracy"]');

    expect(block?.textContent).toContain(String(MATRIX_CELL));
  });
});
