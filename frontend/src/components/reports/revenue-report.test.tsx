/**
 * ⛔ G-39 (08-UI-SPEC) (a)(b) DOM YARMI — DAVR SERVERNIKI (§8.2, §8.6, §8.7).
 *
 * =============================================================================
 * ⛔⛔ 1. NEGA BU TESTNING ENG QIMMAT DA'VOSI — «DAVR SERVERNIKI».
 *
 * Server so'ralgan davrni ⛔ QISQARTIRISHI mumkin (maksimum kecha,
 * ma'lumot boshlanish sanasi, chegara). So'ralgan davrni chizish «men
 * oktyabrni so'radim, oktyabr ko'rsatildi» degan ⛔ YOLG'ON TASDIQ
 * berardi — holbuki javob sentyabrning yarmidan boshlangan bo'lishi
 * mumkin.
 *
 * ⛔ Bu ekranda tuzatiladigan, FAYLDA esa TARQALADIGAN xato: direktor
 *    raqamni `.xlsx` qilib yuklab oladi, chop etadi va yig'ilishga olib
 *    boradi. O'sha varaqda davr bilan raqam BOSHQA-BOSHQA savolga javob
 *    berardi va buni HECH KIM sezmasdi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. YO'QLIK ⛔ TO'PLAM TENGLIGI bilan o'lchanadi (D-31).
 *
 * «`2026-08-01` DOM'da yo'q» da'vosi bitta qiymatni izlaydigan inkor
 * matcher bilan yozilsa, u FAQAT o'sha qiymatni ushlardi va yonidagi
 * IKKINCHI so'ralgan sanani ko'rmasdi. Shuning uchun DOM'dagi BARCHA ISO
 * kunlari yig'iladi va to'plam KUTILGAN juftlik bilan solishtiriladi.
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. SO'ROV YO'LI BO'YICHA MOCK QILINADI, HOOK EMAS.
 *
 * `useRevenueReport` ning O'ZI mock qilinsa, kesh kaliti, `enabled`
 * sharti va zod o'ramining hech biri ⛔ O'LCHANMAY qolardi — ya'ni test
 * komponentni emas, o'zining mockini o'lchardi. Shuning uchun chegara
 * `apiFetch` da: bu yerdan yuqorisi HAQIQIY kod.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { RevenueReport } from "@/components/reports/revenue-report";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

/**
 * ⛔ SO'RALGAN DAVR — URL'da; ⛔ KO'RSATILGAN DAVR — javobda. Ular ATAYIN
 *    FARQ QILADI: `from` bir oy oldinroq so'ralgan, server esa uni
 *    qisqartirgan. Aynan shu farq (a) testining butun mazmuni.
 */
const REQUESTED_FROM = "2026-08-01";
const SERVED_FROM = "2026-09-01";
const SERVED_TO = "2026-09-30";

/**
 * Soatni qotiradi (`period-picker.test.tsx` naqshi).
 *
 * ⚠ FAQAT `Date` soxtalashtiriladi: `setTimeout` haqiqiy qoladi, aks
 *   holda `waitFor` (so'rovning yakunlanishini kutadi) uyg'onmasdi.
 *
 * ⚠ Toshkent yarim kuni: yarim tunga yaqin qiymat UTC↔UTC+5 chegarasida
 *   biznes-kunni bir kunga siljitardi va test O'ZI o'lchayotgan xulqni
 *   emas, chegarani o'lchab qolardi.
 */
function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

const REVENUE_ROWS = [
  {
    business_date: "2026-09-05",
    charged_soum: 400_000,
    collected_soum: 350_000,
    /* ⛔ MANFIY — kam yig'ilgan kun. `text-danger-text` OLADI. */
    diff_soum: -50_000,
  },
  {
    business_date: "2026-09-06",
    charged_soum: 400_000,
    collected_soum: 430_000,
    /*
     * ⛔ MUSBAT — ortiqcha to'lov. U ⛔ YASHIL EMAS: ortiqcha to'lov
     *   YAXSHILIK emas, u ham tekshiriladigan holat (§8.2).
     */
    diff_soum: 30_000,
  },
];

const REVENUE_RESPONSE = {
  from_date: SERVED_FROM,
  to_date: SERVED_TO,
  rows: REVENUE_ROWS,
  total_collected_soum: 780_000,
  total_charged_soum: 800_000,
  /* ⛔ Maxraj: BUTUN davr 45 qator, ekranda esa 2 tasi (§8.6). */
  row_count: 45,
  shown_count: 2,
};

function openSession() {
  clearSession();
  setSession({
    accessToken: "t",
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
}

beforeEach(() => {
  vi.resetAllMocks();
  openSession();
});

afterEach(() => {
  vi.useRealTimers();
});

async function renderRevenue(
  response: unknown,
  searchParams = `?from=${REQUESTED_FROM}&to=${SERVED_TO}`,
): Promise<RenderResult> {
  /* ⛔ Bugun — so'ralgan `to` dan KEYIN, aks holda davr chegaraga urilib
   *   standartga tushardi va test O'ZI qurgan holatni yo'qotardi. */
  const now = freezeClock("2026-10-15");

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reports/revenue")) return Promise.resolve(response);
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });

  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const view = render(
    <NextIntlClientProvider
      locale="uz-Latn"
      messages={messages}
      now={now}
      timeZone={TIME_ZONE}
    >
      <NuqsTestingAdapter searchParams={searchParams}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <RevenueReport />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  await waitFor(() => {
    expect(view.container.querySelector('[aria-busy="true"]')).toBeNull();
  });

  return view;
}

/** DOM matnida uchragan BARCHA ISO kunlari — to'plam sifatida (D-31). */
function isoDaysInDom(view: RenderResult): string[] {
  const text = view.container.textContent ?? "";
  return [...new Set(text.match(/\d{4}-\d{2}-\d{2}/gu) ?? [])].sort();
}

/* -------------------------------------------------------------------------- */
/* (a) G-39(a) — DAVR JAVOBDAN, `nuqs` HOLATIDAN EMAS (§8.7)                  */
/* -------------------------------------------------------------------------- */

describe("⛔ G-39 (08-UI-SPEC) (a): davr SERVERNIKI", () => {
  test("javobdagi `from_date` chiziladi, URL'dagi so'ralgan `from` ⛔ CHIZILMAYDI", async () => {
    const view = await renderRevenue(REVENUE_RESPONSE);

    /*
     * ⛔ TO'PLAM TENGLIGI: «so'ralgan sana yo'q» da'vosini inkor matcher
     *   bilan yozish YONIDAGI ikkinchi sanani ko'rmasdi. Bu shakl esa
     *   kutilgan JUFTLIKDAN har qanday chetlanishda qizaradi.
     */
    expect(isoDaysInDom(view)).toEqual([SERVED_FROM, SERVED_TO]);
  });

  test("davr jumlasi javobning IKKALA chegarasini ham chizadi", async () => {
    await renderRevenue(REVENUE_RESPONSE);

    /*
     * ⛔ SALBIY NAZORAT YUQORIDAGI DA'VOGA: bo'sh DOM'da ISO to'plami ham
     *   bo'sh bo'lardi va (a) «yo'qlik» ni MUKAMMAL o'tkazardi. Shuning
     *   uchun davr jumlasining HAQIQATAN chizilgani alohida o'lchanadi.
     */
    expect(
      screen.getByText(`${SERVED_FROM} — ${SERVED_TO}`),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* (b) G-39(b) — YIG'INDI DAVR VA MAXRAJ JUMLASIGA BOG'LANGAN (§8.6, §15)     */
/* -------------------------------------------------------------------------- */

describe("⛔ G-39 (08-UI-SPEC) (b): yig'indi yolg'iz kelmaydi", () => {
  test("`aria-describedby` davr jumlasi VA `rowsShown` jumlasi id'lariga ishora qiladi", async () => {
    await renderRevenue(REVENUE_RESPONSE);

    /*
     * ⚠ YIG'INDI ATAMA–QIYMAT JUFTLIGIDAN topiladi (`<dt>` -> `<dd>`),
     *   sinf nomi yoki test atributi bilan EMAS: da'vo razmetkaning
     *   SEMANTIKASI haqida.
     */
    const term = screen.getByText(messages.reports.revenueTotal);
    const value = term.parentElement?.querySelector("dd");
    expect(value).not.toBeNull();

    const ids = (value?.getAttribute("aria-describedby") ?? "")
      .split(/\s+/u)
      .filter((id) => id !== "");

    /* ⛔ AYNAN IKKITA: bittasi qolsa, yig'indi yo davrsiz, yo maxrajsiz qolardi. */
    expect(ids).toHaveLength(2);

    const described = new Set(
      ids.map((id) => document.getElementById(id)?.textContent ?? ""),
    );

    expect(described).toEqual(
      new Set([
        `${SERVED_FROM} — ${SERVED_TO}`,
        `${REVENUE_RESPONSE.shown_count} qatordan ${REVENUE_RESPONSE.row_count} tasi ko'rsatilmoqda`,
      ]),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* (c) BO'SH DAVR — `EmptyState`, JADVAL YO'Q (§14.7 bo'sh holat 1)           */
/* -------------------------------------------------------------------------- */

describe("bo'sh davr", () => {
  test("⛔ qator bo'lmaganda `EmptyState` chiziladi va `<table>` ⛔ CHIZILMAYDI", async () => {
    const view = await renderRevenue({
      ...REVENUE_RESPONSE,
      rows: [],
      total_collected_soum: 0,
      total_charged_soum: 0,
      row_count: 0,
      shown_count: 0,
    });

    expect(screen.getByText(messages.reports.emptyRevenue)).toBeInTheDocument();

    /*
     * ⛔ SARLAVHALARI BOR, TANASI BO'SH JADVAL — «ma'lumot bor, hammasi
     *   nol» degan YOLG'ON taassurot berardi. Bo'sh davr NOMLANGAN
     *   holat, bo'sh jadval EMAS.
     */
    expect(view.container.querySelector("table")).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (d) FARQ USTUNI — MANFIY QIZIL, MUSBAT ⛔ YASHIL EMAS (§8.2, §13.4)        */
/* -------------------------------------------------------------------------- */

describe("⛔ farq ustunining rang kanali", () => {
  test("manfiy farq `text-danger-text` oladi, musbat farq ⛔ OLMAYDI", async () => {
    const view = await renderRevenue(REVENUE_RESPONSE);

    const rows = [...view.container.querySelectorAll("tbody tr")];
    expect(rows).toHaveLength(REVENUE_ROWS.length);

    /* Farq — oxirgi ustun: sana · hisoblangan · to'langan · farq. */
    const diffCells = rows.map((row) => {
      const cells = row.querySelectorAll("td");
      return cells[cells.length - 1];
    });

    expect(diffCells[0].className).toContain("text-danger-text");

    /*
     * ⛔ MUSBAT FARQ BEZAK OLMAYDI: ortiqcha to'lovni yashil qilish uni
     *   «yaxshi natija» deb ko'rsatardi, holbuki u ham tekshiriladigan
     *   holat. Da'vo qizil rangning YO'QLIGI haqida — ya'ni ikkinchi
     *   shox ATAYIN o'lchanadi, aks holda birinchi da'vo «hamma katak
     *   qizil» holatida ham yashil qolardi.
     */
    expect(diffCells[1].className).not.toContain("text-danger-text");
    expect(diffCells[1].className).not.toContain("success");
  });
});
