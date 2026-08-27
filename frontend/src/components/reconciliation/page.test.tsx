/**
 * ⛔ G-29 (07-UI-SPEC) — BLOK TO'PLAMI VA ⛔ MAZMUN JUFTLIGI.
 *
 * =============================================================================
 * ⛔⛔ NEGA UCH BAND VA NEGA IKKINCHISI BIRINCHISIDAN QIMMATROQ.
 *
 * (a) BLOK TO'PLAMI — `?day=bugun` da to'rt blok ⛔ DOM'DA UMUMAN
 *     BO'LMASLIGI kerak: hisob D+1 04:10 da, navbat D+1 04:25 da
 *     tug'iladi, ya'ni ular bugun ⛔ MAVJUD EMAS. Bo'sh ro'yxat «bugun
 *     nomuvofiqlik yo'q» degan ⛔ SOXTA IJOBIY javob bo'lardi — bu eng
 *     yomon xato sinfi, chunki u direktorni XOTIRJAM qiladi.
 *
 * (b) ⛔⛔ MAZMUN JUFTLIGI — VA U 06-FAZANING O'LCHANGAN KO'RLIGIDAN
 *     OLINGAN DARS. Faqat blok atributlarini tekshiradigan darvoza
 *     ⛔ BO'SH `<div data-recon-block="unpaid" />` NI MUKAMMAL
 *     o'tkazardi: butun yuza ⛔ CHIZILMAGAN holda darvoza, task VA faza
 *     ⛔ YASHIL qaytardi. Shuning uchun mazmun atributini ⛔ RO'YXAT
 *     KOMPONENTINING O'ZI chiqaradi va sahifa uni ⛔ HECH QACHON
 *     yozmaydi — aks holda sahifa o'z false-green iga o'zi yo'l ochardi.
 *
 * (c) ⛔ HAQIQIY MAZMUN MOCK'DAN HOSILA — «biror matn bormi?» EMAS.
 *     Da'vo mock'dagi AYNAN o'sha qiymatga qadalgan, ya'ni komponentni
 *     platsholder bilan almashtirish uni qizartiradi.
 *
 * ⛔ SABOTAJ SHU FAYLNING KONTRAKTI: `<UnpaidList/>` -> bo'sh o'ram
 *   qo'yilganda (a) ⛔ YASHIL QOLISHI, (b) va (c) esa ⛔ QIZARISHI
 *   KUTILADI. Natija SUMMARY da qayd etilgan.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { beforeEach, describe, expect, test, vi } from "vitest";

/*
 * `@/i18n/navigation` Next.js router kontekstiga tayanadi va u jsdom'da
 * YO'Q (`app-shell.test.tsx:34-52` bilan AYNI sabab). Mock `Link` ni
 * oddiy `<a>` ga aylantiradi — ⛔ lekin `href` ni O'ZGARISHSIZ uzatadi,
 * ya'ni dalil havolasining NISHONI shu testda ham o'lchanadi.
 */
vi.mock("@/i18n/navigation", () => ({
  Link: ({ children, href, ...rest }: ComponentProps<"a">) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/reconciliation",
}));

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import ReconciliationPage from "@/app/[locale]/(app)/reconciliation/page";
import { businessDayIn, shiftIsoDay } from "@/components/snapshots/day-picker";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const CASE_ID = "22222222-2222-4222-8222-222222222222";
const VENDOR_ID = "33333333-3333-4333-8333-333333333333";
const SNAPSHOT_ID = "44444444-4444-4444-8444-444444444444";

/** ⛔ YAGONA LAHZA — literal sana YO'Q, ikkala kun ham undan HOSILA. */
const NOW = new Date();
const TODAY = businessDayIn(TIME_ZONE, NOW);
const YESTERDAY = shiftIsoDay(TODAY, -1);

/**
 * ⛔ BLOK REYESTRI — kutilma SHU YERDA, mahsulot kodidan IMPORT QILINMAYDI.
 *
 * Import qilingan reyestr darvozani o'zi tekshirayotgan qiymatga
 * bog'lab qo'yardi: blok o'chirilsa kutilma HAM o'chardi va tenglik
 * JIMGINA rost bo'lib qolardi.
 */
const BLOCKS_TODAY = ["day", "delivery"];
const BLOCKS_PAST = [
  "day",
  "unpaid",
  "unregistered",
  "cases",
  "hitrate",
  "delivery",
];

/**
 * ⛔ MAZMUN ATRIBUTIDAN OZOD BLOKLAR — AYNAN BITTA.
 *
 * Kun tanlagichi — BOSHQARUV, ro'yxat emas. ⛔ To'plamning O'LCHAMI
 * alohida assert bilan qulflanadi: istisnolar ro'yxati o'sib ketsa,
 * mazmun juftligi darvozasi asta-sekin BO'SHASHARDI va oxirida hech
 * nimani tekshirmasdi.
 */
const CONTENT_EXEMPT = new Set(["day"]);

type Row = {
  subject_kind: string;
  case_id: string | null;
  status: string | null;
  service_date: string;
  stall_code: string;
  vendor_id: string | null;
  expected_soum: number | null;
  paid_soum: number | null;
  evidence_snapshot_ids: string[];
};

function unpaidRow(overrides: Partial<Row> = {}): Row {
  return {
    subject_kind: "occupied_unpaid",
    case_id: CASE_ID,
    status: "new",
    service_date: YESTERDAY,
    stall_code: "14-C",
    vendor_id: VENDOR_ID,
    expected_soum: 30_000,
    paid_soum: 10_000,
    evidence_snapshot_ids: [SNAPSHOT_ID],
    ...overrides,
  };
}

function unregisteredRow(overrides: Partial<Row> = {}): Row {
  return unpaidRow({
    subject_kind: "anomaly",
    case_id: `${CASE_ID.slice(0, -1)}9`,
    stall_code: "31-A",
    vendor_id: null,
    expected_soum: null,
    paid_soum: null,
    ...overrides,
  });
}

/**
 * ⚠ `case_id` HOLATDAN hosila: bir testda bir nechta qator bo'lganda
 *   ular ⛔ TURLI kalit olishi kerak. Bir xil kalit React'ga qatorlarni
 *   birlashtirish erkinligini berardi va «qator soni o'sdi» da'vosi
 *   o'zi o'lchamoqchi bo'lgan narsani emas, React'ning ichki qarorini
 *   o'lchardi.
 */
function caseRow(status: string) {
  const slot = ["new", "in_review", "justified", "unjustified"].indexOf(status);
  const id = `${CASE_ID.slice(0, -1)}${slot < 0 ? 0 : slot}`;
  return {
    case_id: id,
    subject_kind: "occupied_unpaid",
    anomaly_id: null,
    charge_id: id,
    service_date: YESTERDAY,
    status,
    assignee_user_id: null,
    created_at: `${YESTERDAY}T04:25:00Z`,
  };
}

const OUTBOX_ID = "55555555-5555-4555-8555-555555555555";

function deliveryRow(status: string) {
  return {
    outbox_id: OUTBOX_ID,
    kind: "payment_receipt",
    recipient_kind: "vendor",
    vendor_id: VENDOR_ID,
    status,
    attempt_count: 1,
    created_at: `${TODAY}T09:15:00Z`,
    updated_at: `${TODAY}T09:15:02Z`,
    error_type: null,
    error_status_code: null,
  };
}

/** Navbatning IKKINCHI sahifasi — serverning UNUMSIZ kursori ortida. */
const CASE_CURSOR = `${YESTERDAY}T04:25:00+00:00|${CASE_ID}`;

/**
 * Marshrutlarni mock'laydi — har blok O'Z ma'lumotini oladi.
 *
 * ⚠ `nextCaseRows` — IXTIYORIY va standarti `null`: busiz mavjud
 *   da'volarning HAMMASI bir sahifali javob ustida yuguradi va ular
 *   ⛔ SUSAYTIRILMAYDI. Sahifalash da'vosi uni ATAYIN yoqadi.
 */
function routeFetch({
  reportRows,
  caseRows,
  deliveryRows = [deliveryRow("delivered")],
  nextCaseRows = null,
}: {
  reportRows: Row[];
  caseRows: ReturnType<typeof caseRow>[];
  deliveryRows?: ReturnType<typeof deliveryRow>[];
  nextCaseRows?: ReturnType<typeof caseRow>[] | null;
}) {
  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (
      nextCaseRows !== null &&
      path.startsWith("/reconciliation/cases") &&
      path.includes("cursor=")
    ) {
      return Promise.resolve({
        day: YESTERDAY,
        rows: nextCaseRows,
        /*
         * ⛔ SANOQLAR IKKINCHI SAHIFADA HAM BUTUN KUNNIKI (server
         *   kontrakti) — klient ularni YIG'MASLIGI shu yerda o'lchanadi.
         */
        new_count: caseRows.filter((row) => row.status === "new").length,
        in_review_count: 0,
        justified_count: 3,
        unjustified_count: 1,
        next_cursor: null,
      });
    }
    if (path.startsWith("/reconciliation/report")) {
      return Promise.resolve({
        day: YESTERDAY,
        rows: reportRows,
        unpaid_count: reportRows.filter(
          (row) => row.subject_kind === "occupied_unpaid",
        ).length,
        unregistered_count: reportRows.filter(
          (row) => row.subject_kind === "anomaly",
        ).length,
        unpaid_expected_soum: 30_000,
      });
    }
    if (path.startsWith("/reconciliation/cases")) {
      return Promise.resolve({
        day: YESTERDAY,
        rows: caseRows,
        new_count: caseRows.filter((row) => row.status === "new").length,
        in_review_count: 0,
        justified_count: 3,
        unjustified_count: 1,
        next_cursor: nextCaseRows === null ? null : CASE_CURSOR,
      });
    }
    /*
     * ⛔ YETKAZILGANLIK MARSHRUTI HAR IKKALA KUNDA HAM SO'RALADI —
     *   `delivery` bloki KESISHMANING a'zosi (§4.4). Uni mock'lamaslik
     *   blokni XATO holatiga tushirardi va (c) bandining bo'sh-holat
     *   da'vosi BOSHQA sababdan qizarardi.
     */
    if (path.startsWith("/reconciliation/delivery")) {
      return Promise.resolve({
        day: path.includes(TODAY) ? TODAY : YESTERDAY,
        rows: deliveryRows,
        pending_count: deliveryRows.filter((row) => row.status === "pending")
          .length,
        sent_count: 0,
        delivered_count: deliveryRows.filter(
          (row) => row.status === "delivered",
        ).length,
        failed_count: 0,
        blocked_count: 0,
        next_cursor: null,
      });
    }
    if (path.startsWith("/vendors")) {
      return Promise.resolve({ items: [], next_cursor: null });
    }
    return Promise.reject(new Error(`kutilmagan marshrut: ${path}`));
  });
}

async function renderPage(day: string) {
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
      <NuqsTestingAdapter searchParams={`?day=${day}`}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <ReconciliationPage />
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
   * Faqat (1) ni kutish (c) bandini TAVTOLOGIYAGA aylantirardi: skelet
   * holatidagi blok ham `data-recon-content` ni chiqaradi (u ATAYIN
   * shunday — atribut HAR holatda eng tashqi elementda), ya'ni mazmun
   * da'vosi hali kelmagan ma'lumot ustida yugurardi.
   *
   * ⚠ KUTISH SIGNALI `aria-busy`, formatlangan son EMAS: `Intl` uzilmas
   *   bo'shliq qo'yadi va Testing Library uni normalizatsiya qiladi.
   */
  await waitFor(() => {
    expect(view.container.querySelectorAll("[data-recon-block]").length).toBeGreaterThan(0);
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

beforeEach(() => {
  vi.resetAllMocks();
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
  routeFetch({ reportRows: [unpaidRow(), unregisteredRow()], caseRows: [caseRow("new")] });
});

/* -------------------------------------------------------------------------- */
/* (a) BLOK TO'PLAMI — TO'PLAM TENGLIGI                                       */
/* -------------------------------------------------------------------------- */

describe("⛔ G-29 (a): blok to'plami KUNGA QARAB", () => {
  test("⛔ `?day=bugun` -> AYNAN {kun tanlagichi, yetkazilganlik}", async () => {
    const { container } = await renderPage(TODAY);

    /*
     * ⛔ TENGLIK, «bormi?» EMAS: qo'shimcha blok qo'shilsa «unpaid yo'q»
     *   da'vosi YASHIL qolardi. Tenglik HAR QANDAY o'zgarishda qizaradi.
     */
    expect(attrValues(container, "data-recon-block")).toEqual(new Set(BLOCKS_TODAY));
  });

  test("⛔ `?day=kecha` -> OLTALA blok", async () => {
    const { container } = await renderPage(YESTERDAY);

    expect(attrValues(container, "data-recon-block")).toEqual(new Set(BLOCKS_PAST));
  });

  test("kesishma AYNAN {kun tanlagichi, yetkazilganlik}", () => {
    const intersection = BLOCKS_PAST.filter((block) => BLOCKS_TODAY.includes(block));

    /*
     * ⛔ Hisobot bloklari va YO'Q-HISOBOT hech qachon uchrashmaydi:
     *   yetkazilganlik BUGUN kerak (kvitansiya HOZIR ketadi), hisobot
     *   esa bugun MAVJUD EMAS.
     */
    expect(new Set(intersection)).toEqual(new Set(["day", "delivery"]));
  });
});

/* -------------------------------------------------------------------------- */
/* (b) MAZMUN JUFTLIGI — BO'SH O'RAM O'TMAYDI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-29 (b): mazmun juftligi", () => {
  test("⛔ istisnolar to'plami AYNAN BITTA a'zoli (alohida assert)", () => {
    /*
     * ⛔ ALOHIDA DA'VO va u MUZOKARASIZ: istisno qo'shish darvozani
     *   BO'SHASHTIRADIGAN yagona yo'l, ya'ni u ko'zga tashlanishi kerak.
     */
    expect(CONTENT_EXEMPT.size).toBe(1);
    expect(CONTENT_EXEMPT.has("day")).toBe(true);
  });

  test("⛔ `?day=kecha`: mazmun to'plami = bloklar \\ istisno", async () => {
    const { container } = await renderPage(YESTERDAY);

    const blocks = attrValues(container, "data-recon-block");
    const expected = new Set([...blocks].filter((block) => !CONTENT_EXEMPT.has(block)));

    /* ⛔ Da'vo (a) DAN HOSILA — qo'lda yozilgan ikkinchi ro'yxat emas. */
    expect(attrValues(container, "data-recon-content")).toEqual(expected);
  });

  test("⛔ `?day=bugun`: mazmun to'plami = bloklar \\ istisno", async () => {
    const { container } = await renderPage(TODAY);

    const blocks = attrValues(container, "data-recon-block");
    const expected = new Set([...blocks].filter((block) => !CONTENT_EXEMPT.has(block)));

    expect(attrValues(container, "data-recon-content")).toEqual(expected);
  });

  test("⛔ SAHIFA mazmun atributini HECH QACHON yozmaydi", async () => {
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
      "reconciliation",
      "page.tsx",
    );
    if (!existsSync(file)) throw new Error(`sahifa fayli topilmadi: ${file}`);

    const source = readFileSync(file, "utf8");

    /*
     * ⛔ Atribut sahifada bo'lsa, sahifa darvozani PLATSHOLDER bilan
     *   qondira olardi — ya'ni o'zining false-green iga o'zi yo'l
     *   ochardi. Atributning NOMI ham manba faylda uchramaydi.
     */
    expect((source.match(/data-recon-content/gu) ?? []).length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* (c) HAQIQIY MAZMUN — MOCK'DAN HOSILA                                       */
/* -------------------------------------------------------------------------- */

describe("⛔ G-29 (c): mazmun MOCK'DAGI AYNAN QIYMATGA qadalgan", () => {
  test("⛔ `unpaid` bloki mock'dagi rasta kodini VA qator SONINI beradi", async () => {
    const rows = [unpaidRow(), unpaidRow({ case_id: null, status: null, stall_code: "02-B" })];
    routeFetch({ reportRows: rows, caseRows: [caseRow("new")] });

    const { container } = await renderPage(YESTERDAY);
    const block = container.querySelector('[data-recon-content="unpaid"]');

    expect(block).not.toBeNull();
    expect(block?.textContent).toContain("14-C");
    expect(block?.textContent).toContain("02-B");

    /*
     * ⛔ QATOR SONI — mock'dagi massiv UZUNLIGIDAN hosila. Bu «biror
     *   jadval bormi?» dan kuchliroq: qatorlarni jimgina tashlab
     *   ketadigan filtr aynan shu yerda qizaradi.
     */
    expect(block?.querySelectorAll("tbody tr").length).toBe(rows.length);
  });

  test("⛔ `cases` bloki mock'dagi holat YORLIG'INI beradi", async () => {
    routeFetch({ reportRows: [unpaidRow()], caseRows: [caseRow("justified")] });

    const { container } = await renderPage(YESTERDAY);
    const block = container.querySelector('[data-recon-content="cases"]');

    expect(block?.textContent).toContain(messages.recon.caseStatus.justified);
    expect(block?.querySelectorAll("tbody tr").length).toBe(1);
  });

  test("⛔ `delivery` bloki mock'dagi holat YORLIG'INI beradi", async () => {
    routeFetch({
      reportRows: [unpaidRow()],
      caseRows: [caseRow("new")],
      deliveryRows: [deliveryRow("delivered")],
    });

    const { container } = await renderPage(YESTERDAY);
    const block = container.querySelector('[data-recon-content="delivery"]');

    /*
     * ⛔ MOCK'DAGI AYNAN QIYMATGA QADALGAN: platsholder bilan
     *   almashtirilgan blok bu da'voni QIZARTIRADI.
     */
    expect(block?.textContent).toContain(messages.recon.deliveryState.delivered);
    expect(block?.querySelectorAll("tbody tr").length).toBe(1);
  });

  test("⛔ IKKI SAHIFALI navbatda [Yana yuklash] KO'RINADI va qator soni O'SADI", async () => {
    /*
     * ⛔⛔ B-6 NING SAHIFA DARAJASIDAGI YARMI. Blok testi komponentni
     *   YOLG'IZ render qiladi; bu yerda esa u O'Z sahifasida, qo'shni
     *   bloklar bilan BIRGA turadi — ya'ni «Yana yuklash» boshqa blokning
     *   tugmasi bilan ADASHMASLIGI ham o'lchanadi.
     */
    const first = [caseRow("new"), caseRow("in_review")];
    const second = [caseRow("justified")];
    routeFetch({ reportRows: [unpaidRow()], caseRows: first, nextCaseRows: second });

    const { container } = await renderPage(YESTERDAY);
    const block = container.querySelector(
      '[data-recon-content="cases"]',
    ) as HTMLElement;

    expect(block.querySelectorAll("tbody tr").length).toBe(first.length);

    /* ⛔ Tugma AYNAN navbat blokining ICHIDA — sahifa darajasida emas. */
    const more = within(block).getByRole("button", {
      name: messages.recon.loadMore,
    });

    fireEvent.click(more);

    await waitFor(() => {
      expect(block.querySelectorAll("tbody tr").length).toBe(
        first.length + second.length,
      );
    });

    /* ⛔ Oxirgi sahifadan keyin tugma UMUMAN yo'q (o'chirilgan emas). */
    expect(
      within(block).queryByRole("button", { name: messages.recon.loadMore }),
    ).toBeNull();
  });

  test("⛔ BO'SH javob bergan blok O'Z bo'sh-holat matnini ko'rsatadi", async () => {
    routeFetch({ reportRows: [], caseRows: [], deliveryRows: [] });

    const { container } = await renderPage(YESTERDAY);

    /*
     * ⛔ HAR BLOK O'Z matnini beradi: umumiy «ma'lumot yo'q» jumlasi
     *   uch xil holatni bir xil ko'rsatardi va direktor qaysi sinf
     *   bo'shligini bilmasdi.
     */
    expect(
      container.querySelector('[data-recon-content="unpaid"]')?.textContent,
    ).toContain(messages.recon.emptyUnpaid);
    expect(
      container.querySelector('[data-recon-content="unregistered"]')?.textContent,
    ).toContain(messages.recon.emptyUnregistered);
    expect(
      container.querySelector('[data-recon-content="cases"]')?.textContent,
    ).toContain(messages.recon.emptyCases);
    expect(
      container.querySelector('[data-recon-content="delivery"]')?.textContent,
    ).toContain(messages.recon.emptyDelivery);
  });
});
