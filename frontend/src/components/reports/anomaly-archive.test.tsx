/**
 * ⛔ G-40 (08-UI-SPEC) (e)(f)(g) — IKKI SINF, IKKI SANOQ, KADRSIZ DALIL (§8.5).
 *
 * =============================================================================
 * ⛔⛔ 1. NEGA «IKKI SANOQ QO'SHILMAYDI» DA'VOSI TO'PLAM TENGLIGI BILAN
 *     O'LCHANADI (D-31, 08-13 dagi S-1 darsining takrori).
 *
 * «Yig'indi DOM'da yo'q» da'vosini `queryByText("5")` bilan yozish
 * ⛔ IKKI TOMONDAN ko'r: (1) u faqat O'SHA sonni izlardi va boshqa
 * shakldagi birlashtirilgan qiymatni (masalan «5 ta nomuvofiqlik»)
 * ko'rmasdi; (2) BO'SH DOM'da ham YASHIL qolardi.
 *
 * Shuning uchun DOM'dagi BARCHA sof sonli matn tugunlari yig'iladi va
 * to'plam KUTILGAN juftlik bilan solishtiriladi. Uchinchi son paydo
 * bo'lishi bilanoq darvoza qizaradi va bu aynan sabotaj (3) ning
 * o'lchagan xulqi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. NEGA «KADR YO'Q» DA'VOSI IKKI QATLAMLI.
 *
 * DOM'da `<img>` yo'qligi ⛔ YETARLI EMAS: bugungi mock javobda kadr
 * identifikatori bor, ertaga esa ijrochi kadrni SHARTLI shoxda chizishi
 * mumkin va o'sha shox testning mockida umuman yugurmasdi. Shuning uchun
 * ikkinchi qatlam — ⛔ MANBA SKANI: taqiqlangan tokenlarning birortasi
 * ham faylda BO'LMASLIGI kerak (07 D-03, G-42(d) ning shu fayldagi
 * oldinlashtirilgan yarmi).
 *
 * -----------------------------------------------------------------------
 * ⛔ 3. SO'ROV YO'LI BO'YICHA MOCK QILINADI, HOOK EMAS (`revenue-report`
 *    naqshi): `useAnomalyArchive` ning O'ZI mock qilinsa kesh kaliti,
 *    `enabled` sharti va zod o'ramining hech biri o'lchanmay qolardi.
 * =============================================================================
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { RenderResult } from "@testing-library/react";
import type { ComponentProps } from "react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

/* `Link` — `unpaid-list.test.tsx` naqshi: marshrutlagichsiz oddiy anchor. */
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

import messages from "../../../messages/uz-Latn.json";
import { AnomalyArchive } from "@/components/reports/anomaly-archive";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const REQUESTED_FROM = "2026-08-01";
const SERVED_FROM = "2026-09-01";
const SERVED_TO = "2026-09-30";

/*
 * ⚠ MANBA `process.cwd()` DAN O'QILADI, `import.meta.url` DAN EMAS:
 *   `jsdom` muhitida modul manzili `file:` sxemasida EMAS va
 *   `readFileSync` uni rad etadi. Vitest esa `frontend/` katalogidan
 *   yuguradi, ya'ni nisbiy yo'l BARQAROR.
 */
const SOURCE = readFileSync(
  resolve(process.cwd(), "src/components/reports/anomaly-archive.tsx"),
  "utf8",
);

/**
 * ⛔ KADR TOKENLARI — 07 D-03 ning mexanik shakli.
 *
 * ⚠ Ro'yxat TESTDA qayta yoziladi, mahsulotdan import QILINMAYDI
 *   (05-15 darsi: import darvozani o'zi tekshirayotgan qiymatga
 *   bog'lardi).
 */
const FRAME_TOKENS = [
  "<img",
  "next/image",
  "useEvidenceImageHref",
  "URL.createObjectURL",
  "/snapshots/",
];

/** ⛔ IKKI SANOQNI BITTA SONGA SIQADIGAN SHAKLLAR (07 Pattern 4, G-30). */
const MERGE_TOKENS = ["unpaid_count +", "totalAnomal", "combined"];

function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

/**
 * ⛔ IKKI SINF — IKKI QATOR, BITTA JADVALDA.
 *
 * ⚠ Ikkinchi qatorda dalil identifikatori ATAYIN `null`: dalilsiz qator
 *   ham ro'yxatda QOLADI (uni tashlab yuborish davr sanog'ini jimgina
 *   kamaytirardi).
 */
const ARCHIVE_ROWS = [
  {
    business_date: "2026-09-11",
    kind: "unpaid",
    stall_code: "A-12",
    snapshot_id: "77777777-7777-4777-8777-777777777777",
    case_status: "justified",
  },
  {
    business_date: "2026-09-12",
    kind: "unregistered",
    stall_code: "B-07",
    snapshot_id: null,
    case_status: null,
  },
];

/**
 * ⛔ SANOQLAR ATAYIN KICHIK VA ULARNING YIG'INDISI (5) DOM'DA HECH QAYERDA
 *    UCHRAMASLIGI KERAK — (f) testining butun mazmuni shu.
 */
const ARCHIVE_RESPONSE = {
  from_date: SERVED_FROM,
  to_date: SERVED_TO,
  rows: ARCHIVE_ROWS,
  unpaid_count: 3,
  unregistered_count: 2,
  row_count: 12,
  shown_count: 4,
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

async function renderArchive(response: unknown): Promise<RenderResult> {
  const now = freezeClock("2026-10-15");

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reports/anomalies")) return Promise.resolve(response);
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
      <NuqsTestingAdapter
        searchParams={`?from=${REQUESTED_FROM}&to=${SERVED_TO}`}
      >
        <QueryClientProvider client={client}>
          <AuthProvider>
            <AnomalyArchive />
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

/**
 * DOM'dagi SOF SONLI matn tugunlari — to'plam sifatida.
 *
 * ⚠ «Sof sonli» = butun tugun faqat sondan iborat (ajratkichli guruh ham
 *   qabul qilinadi). Sana va rasta kodi harf yoki tire tutgani uchun bu
 *   filtrga TUSHMAYDI, ya'ni to'plamda faqat ATAYIN chizilgan sanoqlar
 *   qoladi.
 */
function numericTextNodes(view: RenderResult): string[] {
  const walker = document.createTreeWalker(view.container, NodeFilter.SHOW_TEXT);
  const found = new Set<string>();

  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    const text = (node.textContent ?? "").trim();
    if (/^\d{1,3}(?:[\s\u00A0\u202F]\d{3})*$/u.test(text)) found.add(text);
  }

  return [...found].sort();
}

/* -------------------------------------------------------------------------- */
/* (e) IKKI SINF — BITTA JADVAL, `kind` YORLIG'I BILAN AJRALGAN (§8.5)        */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (e): ikki sinf bitta jadvalda", () => {
  test("ikkala sinf qatori BITTA `<table>` da va yorliqlari FARQ QILADI", async () => {
    const view = await renderArchive(ARCHIVE_RESPONSE);

    /*
     * ⛔ AYNAN BITTA JADVAL: arxivda davr bo'ylab XRONOLOGIYA muhim va
     *   ikki alohida jadval bir hodisani ikki joyda qidirtirardi.
     */
    expect(view.container.querySelectorAll("table")).toHaveLength(1);

    const rows = [...view.container.querySelectorAll("tbody tr")];
    expect(rows).toHaveLength(ARCHIVE_ROWS.length);

    /* Sinf — ikkinchi ustun: sana · sinf · rasta · dalil · holat. */
    const kindLabels = rows.map((row) =>
      (row.querySelectorAll("td")[1].textContent ?? "").trim(),
    );

    expect(new Set(kindLabels)).toEqual(
      new Set([
        messages.reports.anomaliesUnpaid,
        messages.reports.anomaliesUnregistered,
      ]),
    );

    /* ⛔ Mazmun atributini ro'yxatning O'ZI chiqaradi (§8.1, G-29(b)). */
    expect(
      view.container.querySelector('[data-report-content="anomalies"]'),
    ).not.toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (f) IKKI SANOQ — ALOHIDA MATN TUGUNIDA, YIG'INDI YO'Q (07 Pattern 4)       */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (f): ikki sanoq hech qachon qo'shilmaydi", () => {
  test("sanoqlar ALOHIDA tugunda va DOM'dagi sonlar to'plami AYNAN {2, 3}", async () => {
    const view = await renderArchive(ARCHIVE_RESPONSE);

    /*
     * ⛔ HAR SANOQ O'Z ATAMASI BILAN: `<dt>` -> `<dd>`. Da'vo
     *   razmetkaning SEMANTIKASI haqida, sinf nomi haqida emas.
     */
    const unpaidTerm = screen.getByText(messages.reports.anomaliesUnpaid, {
      selector: "dt",
    });
    const unregisteredTerm = screen.getByText(
      messages.reports.anomaliesUnregistered,
      { selector: "dt" },
    );

    expect(unpaidTerm.parentElement?.querySelector("dd")?.textContent).toBe(
      "3",
    );
    expect(
      unregisteredTerm.parentElement?.querySelector("dd")?.textContent,
    ).toBe("2");

    /*
     * ⛔ TO'PLAM TENGLIGI: uchinchi son (masalan yig'indi 5) paydo
     *   bo'lishi bilanoq darvoza qizaradi. Inkor matcher esa faqat
     *   o'sha bitta shaklni ushlardi.
     */
    expect(numericTextNodes(view)).toEqual(["2", "3"]);

    /* ⛔ Manba yarmi: qo'shish shakli KODDA ham yozilmaydi. */
    for (const token of MERGE_TOKENS) {
      expect(SOURCE).not.toContain(token);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* (g) DALIL — IDENTIFIKATOR/HAVOLA, KADR EMAS (07 D-03, G-42(d))             */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (g): dalil kadri chegaradan chiqmaydi", () => {
  test("`<img>` DOM'da 0 marta VA kadr tokenlari manbada 0 marta", async () => {
    const view = await renderArchive(ARCHIVE_RESPONSE);

    expect(view.container.querySelectorAll("img")).toHaveLength(0);

    for (const token of FRAME_TOKENS) {
      expect(SOURCE).not.toContain(token);
    }

    /*
     * ⛔ SALBIY NAZORAT: «kadr yo'q» da'vosi dalil YUZASI umuman
     *   chizilmagan holatda ham yashil qolardi. Shuning uchun havolaning
     *   HAQIQATAN chizilgani alohida o'lchanadi.
     */
    expect(
      screen.getByRole("link", { name: messages.recon.evidenceOpen }),
    ).toBeInTheDocument();
  });
});

/* -------------------------------------------------------------------------- */
/* BO'SH DAVR — `EmptyState`, JADVAL YO'Q (§14.7 bo'sh holat 3)                */
/* -------------------------------------------------------------------------- */

describe("bo'sh davr", () => {
  test("⛔ qator bo'lmaganda `EmptyState` chiziladi va `<table>` ⛔ CHIZILMAYDI", async () => {
    const view = await renderArchive({
      ...ARCHIVE_RESPONSE,
      rows: [],
      unpaid_count: 0,
      unregistered_count: 0,
      row_count: 0,
      shown_count: 0,
    });

    expect(
      screen.getByText(messages.reports.emptyAnomalies),
    ).toBeInTheDocument();

    /*
     * ⛔ SARLAVHALARI BOR, TANASI BO'SH JADVAL «ma'lumot bor, hammasi
     *   nol» degan YOLG'ON taassurot berardi (08-13 ning aynan qoidasi).
     */
    expect(view.container.querySelector("table")).toBeNull();
  });
});
