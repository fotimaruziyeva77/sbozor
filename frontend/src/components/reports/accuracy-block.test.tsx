/**
 * ⛔ G-40 (08-UI-SPEC) (a)–(d) — O'LCHANMAGAN SON CHIZILMAYDI (§9.3, §9.4).
 *
 * =============================================================================
 * ⛔⛔ 1. BU DARVOZA WR-05 NI YOPADI VA U IKKI SHOXNI BIRDAY QO'RIQLAYDI.
 *
 * 07 ko'rigining WR-05 bandi: «yiqilgan so'rov 0 % bo'lib chiziladi».
 * Uning yonida ikkinchi, AYNI SINFDAGI shox turadi: namuna kichik
 * bo'lganda ham foiz chizilmaydi. Ikkalasining ham nosozligi BIR XIL
 * shaklda ko'rinadi — ⛔ ekranda O'LCHANGANDEK ko'rinadigan son —
 * shuning uchun ikkalasi ham AYNI usulda o'lchanadi: ⛔ foiz BELGISI
 * DOM'da 0 marta.
 *
 * ⚠ Nega belgi, nega qiymat emas: «94,1 %» ni matn bilan izlash faqat
 *   O'SHA qiymatni ushlardi. Belgi esa foizning HAR QANDAY shaklini
 *   (nuqta baho, oraliq, bazaviy ulush) ushlaydi va `％` (to'liq kenglik)
 *   ham ro'yxatda, chunki `Intl` ba'zi locale'larda aynan uni chizadi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 2. «KO'RINADIGAN MATN» = `textContent` MINUS `.sr-only` [08-13 DARSI].
 *
 * 08-13 ning S-2b sabotaji o'lchadi: bevosita matn tugunlarini sanaydigan
 * assert `<span>` ichiga o'ralgan qiymatni KO'RMAYDI va yarim ishlamay
 * qoladi. Shuning uchun bu yerda ham ko'rinadigan matn ⛔ BUTUN
 * `textContent` dan `.sr-only` shajaralarini AYIRIB olinadi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ 3. NEGA `min_sample` NING O'ZI EMAS, U BILAN TAQQOSLASH TAQIQLANADI.
 *
 * §9.3 ikkita narsani BIRGA talab qiladi: (1) nomlangan sabab SERVERNING
 * chegarasini AYTSIN («kamida {min} kerak») va (2) klient `n >= 20` ni
 * QAYTA YOZMASIN. Birinchisi maydonni O'QISHNI, ikkinchisi u bilan QAROR
 * QABUL QILISHNI nazarda tutadi va ular ⛔ BIR XIL NARSA EMAS.
 *
 * ⛔ Shuning uchun darvoza TAQQOSLASH OPERATORINI va klientdagi ikkinchi
 *    chegara manbaini (`wilson.ts` konstantasi) o'lchaydi. Maydonni
 *    umuman taqiqlash `{min}` platsholderini to'ldirib bo'lmas holga
 *    keltirardi — G-43(d) esa uni UCHALA locale'da QULFLAGAN.
 * =============================================================================
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import { AccuracyBlock } from "@/components/reports/accuracy-block";
import { ApiError } from "@/lib/api-client";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";

const REQUESTED_FROM = "2026-08-01";
const SERVED_FROM = "2026-09-01";
const SERVED_TO = "2026-09-30";

/*
 * ⚠ Manba `process.cwd()` dan o'qiladi: `jsdom` da modul manzili `file:`
 *   sxemasida emas, vitest esa `frontend/` katalogidan yuguradi.
 */
const SOURCE = readFileSync(
  resolve(process.cwd(), "src/components/reports/accuracy-block.tsx"),
  "utf8",
);

/** ⛔ Foiz belgisining IKKALA shakli — `Intl` ikkinchisini ham chizadi. */
const PERCENT_SIGNS = /[%％]/gu;

/**
 * ⛔ O'LCHANMAGAN NAMUNA — foiz UMUMAN chizilmaydigan javob.
 *
 * ⚠ Hamma sanoq ATAYIN nolsiz: (a) testi «yakka `0`» ni taqiqlaydi va
 *   fixture'ning o'zidan kelgan nol o'sha da'voni MA'NOSIZ qilardi.
 */
const NOT_MEASURED = {
  from_date: SERVED_FROM,
  to_date: SERVED_TO,
  drawn: 9,
  answered: 7,
  unanswered: 1,
  dont_know: 1,
  matrix: {
    true_occupied: 4,
    false_occupied: 1,
    false_empty: 1,
    true_empty: 1,
  },
  n: 7,
  measured: false,
  /* ⛔ Chegara SERVERNIKI — klient uni qayta yozmaydi (§9.3). */
  min_sample: 20,
  base_rate: null,
  correct: { point: null, lower: null, upper: null },
  false_occupied: { point: null, lower: null, upper: null },
  false_empty: { point: null, lower: null, upper: null },
};

/** O'lchangan namuna — 05-12 ning ishlangan misoli (tp/fp/fn/tn). */
const MEASURED = {
  from_date: SERVED_FROM,
  to_date: SERVED_TO,
  drawn: 640,
  answered: 612,
  unanswered: 28,
  dont_know: 14,
  matrix: {
    true_occupied: 401,
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

function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

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

async function renderBlock(outcome: {
  fails?: boolean;
  report?: unknown;
}): Promise<RenderResult> {
  const now = freezeClock("2026-10-15");

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/occupancy/accuracy")) {
      return outcome.fails === true
        ? Promise.reject(new ApiError(500, "internal_error"))
        : Promise.resolve(outcome.report);
    }
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
            <AccuracyBlock />
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
 * ⛔ KO'RINADIGAN MATN — `textContent` MINUS `.sr-only` shajaralari.
 *
 * ⚠ 08-13 ning S-2b darsi: bevosita matn tugunlarini sanash `<span>`
 *   ichiga o'ralgan qiymatni ko'rmaydi va assert yarim ishlaydi.
 */
function visibleText(view: RenderResult): string {
  return visibleRoot(view).textContent ?? "";
}

function visibleRoot(view: RenderResult): HTMLElement {
  const clone = view.container.cloneNode(true) as HTMLElement;
  for (const hidden of clone.querySelectorAll(".sr-only")) hidden.remove();
  return clone;
}

/**
 * ⛔⛔ YAKKA NOL — HAR MATN TUGUNIDA ALOHIDA IZLANADI, BIRLASHTIRILGAN
 *     SATRDA EMAS. VA BU O'LCHANGAN TUZATISH, DID EMAS.
 *
 * Dastlabki shakl butun `textContent` ustidan yurardi. Sabotaj (1c) uni
 * rad etdi: nol AYRIM elementga chizilganda undan oldingi jumla NUQTA
 * bilan tugaydi va `(?<![\d.,])` nuqtani ko'rib mosligni RAD ETADI —
 * ya'ni assert «nol yo'q» deb YASHIL qolardi, holbuki ekranda «0»
 * turardi.
 *
 * ⚠ Tugun bo'yicha yurish qo'shni matnning ta'sirini butunlay yo'q
 *   qiladi; `20` ichidagi nol esa hamon qonuniy, chunki lookbehind
 *   TUGUN ICHIDA ishlaydi.
 */
function hasLoneZero(view: RenderResult): boolean {
  const walker = document.createTreeWalker(
    visibleRoot(view),
    NodeFilter.SHOW_TEXT,
  );

  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    if (/(?<![\d.,])0(?![\d.,])/u.test(node.textContent ?? "")) return true;
  }

  return false;
}

/* -------------------------------------------------------------------------- */
/* (a) G-40(a) — O'LCHANMAGAN NAMUNA: FOIZ BELGISI DOM'DA 0 MARTA (§9.3)      */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (a): o'lchanmagan son chizilmaydi", () => {
  test("`measured: false` da foiz belgisi YO'Q, nomlangan sabab BOR", async () => {
    const view = await renderBlock({ report: NOT_MEASURED });
    const text = visibleText(view);

    /* ⛔ IKKALA shakl ham: `%` va to'liq kenglikdagi `％`. */
    expect(text.match(PERCENT_SIGNS) ?? []).toHaveLength(0);

    /* ⛔ NOMLANGAN SABAB — bo'sh joy emas (§9.3, D-10). */
    expect(
      screen.getByText(
        `Bu davrda javoblar soni o'lchov uchun yetarli emas: ${NOT_MEASURED.n} ta, kamida ${NOT_MEASURED.min_sample} kerak.`,
      ),
    ).toBeInTheDocument();

    /*
     * ⛔ O'LCHANMAGANNING ZAXIRA SHAKLLARI HAM TAQIQ: yakka `0`,
     *   `NaN`, `Infinity` va tireli foiz. Ular «o'lchandi va natija
     *   shu» degan YOLG'ON faktning arifmetik ko'rinishlari.
     *
     * ⚠ `0` YAKKA holda izlanadi: `20` ichidagi nol qonuniy — u
     *   SERVERNING chegarasi.
     */
    expect(hasLoneZero(view)).toBe(false);
    expect(text).not.toContain("NaN");
    expect(text).not.toContain("Infinity");
    expect(text).not.toContain("—%");

    /*
     * ⛔ MANBA YARMI: nolga tushiruvchi zaxira operatorlari (`?? 0` va
     *   `|| 0`) — o'sha yolg'onning KODDAGI shakli va ular sabotaj (1)
     *   bilan o'lchanadi.
     */
    expect(SOURCE).not.toMatch(/\?\?\s*0|\|\|\s*0/u);
  });
});

/* -------------------------------------------------------------------------- */
/* (b) G-40(b) — YIQILGAN SO'ROV: NA «0 %», NA BO'SH MATRITSA (WR-05)         */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (b): yiqilgan so'rov nol bo'lib chizilmaydi", () => {
  test("xato holatida foiz belgisi YO'Q va xato `role=\"alert\"` ichida", async () => {
    const view = await renderBlock({ fails: true });
    const text = visibleText(view);

    expect(text.match(PERCENT_SIGNS) ?? []).toHaveLength(0);

    /*
     * ⛔ XATO JONLI HUDUDDA E'LON QILINADI (§14.9): `role="alert"` bu
     *   yerda QONUNIY, chunki bu HAQIQATAN xato — qo'shni bloklarning
     *   yuklanish platsholderi emas.
     */
    const alert = screen.getByRole("alert");
    expect(alert.textContent).toContain(messages.errors.loadFailedBody);

    /* ⛔ Bo'sh matritsa ham chizilmaydi — jadval UMUMAN yo'q. */
    expect(view.container.querySelector("table")).toBeNull();
  });
});

/* -------------------------------------------------------------------------- */
/* (c) AI-02 HOLATI — SHARTSIZ, BEZAKSIZ (§9.4, D-11)                         */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (c): AI-02 holati yashirilmaydi", () => {
  test("jumla IKKALA holatda ham BOR va `role=\"alert\"` ichida EMAS", async () => {
    for (const report of [NOT_MEASURED, MEASURED]) {
      const view = await renderBlock({ report });

      const sentence = screen.getByText(messages.reports.accuracyDisclaimer);
      expect(sentence).toBeInTheDocument();

      /*
       * ⛔ BU HOLAT, XATO EMAS (07 D-22 sinfi): ogohlantirish bezagi uni
       *   har ochilishda SHOVQIN qilardi va uch kundan keyin o'qilmay
       *   qolardi.
       */
      expect(sentence.closest('[role="alert"]')).toBeNull();
      expect(sentence.className).not.toContain("warning");

      view.unmount();
    }

    /*
     * ⛔ MANBA YARMI: jumla AYNAN BIR MARTA yoziladi — ikki nusxa
     *   («o'lchangan» va «o'lchanmagan» shoxlarida) bir kun ajralib,
     *   bittasi jimgina yo'qolardi.
     */
    expect(SOURCE.match(/accuracyDisclaimer/gu) ?? []).toHaveLength(1);
    expect(SOURCE).not.toContain('tone="warning"');
  });
});

/* -------------------------------------------------------------------------- */
/* (d) MAVJUD MATRITSA QAYTA ISHLATILADI (§9.2, M-11)                         */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (d): `ConfusionMatrix` qayta ishlatiladi", () => {
  test("`measured: true` da matritsa kataklari DOM'da va davr JAVOBDAN", async () => {
    const view = await renderBlock({ report: MEASURED });

    const table = view.container.querySelector("table");
    expect(table).not.toBeNull();

    /* ⛔ TO'RT XOM SON — matritsaning O'ZI (foizlar emas). */
    const cells = new Set(
      [...(table?.querySelectorAll("td") ?? [])].map((cell) =>
        (cell.textContent ?? "").trim(),
      ),
    );
    for (const value of Object.values(MEASURED.matrix)) {
      expect(cells).toContain(String(value));
    }

    /*
     * ⛔ DAVR MATRITSANING O'ZIDA, PROPDAN EMAS (§8.7, G-39(c)): o'ram
     *   unga `from`/`to`/`period`/`label` UZATMAYDI.
     */
    /*
     * ⛔ 260818: matritsa davrni endi `formatBusinessDay` bilan chizadi
     *    (xom ISO sahifadagi qolgan sanalardan ajralib turardi). Da'vo
     *    O'ZGARMADI — davr MATRITSANING O'ZIDA, propdan emas; faqat
     *    qidiriladigan shakl mahalliylashtirilgan.
     *
     * ⚠ Kutilgan matn `uzLatnDate` dan MUSTAQIL quriladi: yordamchiga
     *   bog'lansa, ikkalasi birga siljib test jimgina yashil qolardi.
     */
    const uzDay = (iso: string): string => {
      const months = [
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
      const [year, month, day] = iso.split("-").map(Number);
      return `${day}-${months[month - 1]}, ${year}`;
    };

    expect(
      within(view.container).getByText(
        new RegExp(`${uzDay(SERVED_FROM)}.*${uzDay(SERVED_TO)}`, "u"),
      ),
    ).toBeInTheDocument();

    const usage = /<ConfusionMatrix[^>]*>/u.exec(SOURCE)?.[0] ?? "";
    expect(usage).not.toBe("");
    for (const prop of ["from", "to", "period", "label"]) {
      expect(usage).not.toMatch(new RegExp(`\\b${prop}=`, "u"));
    }

    /*
     * ⛔ KLIENTDA IKKINCHI CHEGARA YO'Q: server maydoni bilan
     *   TAQQOSLASH ham, `wilson.ts` konstantasini import qilish ham
     *   yozilmaydi — ikkinchi chegara ikkinchi javob bo'lardi (§9.3).
     */
    expect(SOURCE).not.toMatch(
      /(min_sample|minSample)\s*[<>]|[<>]=?\s*[\w.]*(min_sample|minSample)/u,
    );
    expect(SOURCE).not.toContain("MIN_SAMPLE_FOR_PERCENT");
    expect(SOURCE).not.toContain("lib/wilson");
  });
});
