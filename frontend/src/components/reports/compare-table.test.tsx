/**
 * ⛔ G-40(c)(d) va G-41(c)(d) — UCH TOMONLAMA SOLISHTIRUV JADVALI.
 *
 * =============================================================================
 * ⛔⛔ BU FAYLDAGI HAR DA'VO IMZOLANADIGAN VARAQNI HIMOYA QILADI.
 *
 * (c) ⛔ `null` VA `0` IKKI XIL NARSA VA FARQ BITTA TESTDA O'LCHANADI.
 *     `null` = «o'sha kun uchun bandlik ma'lumoti YO'Q» (⛔ O'LCHANMAGAN);
 *     `0`    = «AI rastani BO'SH dedi»                  (⛔ O'LCHANGAN).
 *     Ikkalasini ikki testga ajratish ularning ZIDDIYATINI yashirardi:
 *     «bo'sh» testi chizilgan nolni ham bo'shlik deb, «nol» testi esa
 *     bo'sh katakni ham nol deb o'tkazishi mumkin edi (08-13 darsi).
 *
 * (d) ⛔ DAFTAR YO'Q -> JADVAL UMUMAN CHIZILMAYDI. Uch ustunli jadvalni
 *     «hamma farq 0» bilan chizish ⛔ MUVAFFAQIYATLI SOLISHTIRUV bo'lib
 *     ko'rinardi va u ⛔ IMZOLANARDI — parallel rejimning butun maqsadi
 *     (SC#5) jimgina yo'qolardi.
 *
 * (c-41) ⛔ UCH SANOQ UCH ALOHIDA TUGUNDA va ularni BIRLASHTIRGAN son
 *     YO'Q: uch sinf uch TURLI harakat talab qiladi («pulni qidiring» /
 *     «daftarni tuzating» / «detektorni tekshiring»).
 *
 * (d-41) ⛔ «MOS» QATORI JADVALDA QOLADI va BEZAK OLMAYDI: 287 ta yashil
 *     belgi 13 ta farqni KO'MIB yuborardi, maxrajsiz 13 qatorli varaq esa
 *     «bozorda 13 ta rasta bor» bo'lib o'qilardi (07 G-32 darsi).
 *
 * -----------------------------------------------------------------------
 * ⛔ «KO'RINADIGAN MATN YO'Q» DA'VOSI `sr-only` NI AYIRADI — 08-13/08-15
 *   DA IKKI MARTA O'LCHANGAN SINF. Bevosita matn tugunlarini sanaydigan
 *   shakl YOLG'ON-YASHIL edi: `<span>` ichiga o'ralgan to'qilgan qiymat
 *   bevosita tugun EMAS. Da'vo ⛔ KO'RINADIGAN matn haqida, razmetka
 *   chuqurligi haqida emas.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
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
import { CompareTable } from "@/components/reports/compare-table";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-10-10";

/**
 * ⛔ FARQ SINFLARI — KUTILMA SHU YERDA, `api-types.ts` DAN IMPORT
 *    QILINMAYDI (05-15 darsi): import qilingan reyestr darvozani o'zi
 *    tekshirayotgan qiymatga bog'lardi va a'zo o'chirilganda kutilma HAM
 *    o'chib, tenglik JIMGINA rost bo'lib qolardi.
 */
const DIFF_ORDER = ["ledger_over", "system_over", "ai_mismatch"];

/**
 * ⛔ SANOQLAR ATAYIN UCH XIL VA ULARNING YIG'INDISI (6) BOSHQA HECH
 *    QAYERDA UCHRAMAYDI — «birlashtirgan son yo'q» da'vosi shu bilan
 *    o'lchanadi.
 */
const LEDGER_OVER = 3;
const SYSTEM_OVER = 2;
const AI_MISMATCH = 1;
const MATCHED = 287;
const COMBINED = LEDGER_OVER + SYSTEM_OVER + AI_MISMATCH;

/**
 * ⛔ SUMMALAR UCH XONALI. Sabab MEXANIK: `Intl.NumberFormat` to'rt
 *   xonadan boshlab guruh AJRATGICHI (uzilmas bo'shliq) qo'yadi va u
 *   DOM'dagi satrni «400000» bo'lib topib bo'lmas qilardi.
 */
const ROWS = [
  {
    /* ⛔ (c) NING BIRINCHI YARMI — O'LCHANMAGAN bandlik. */
    stall_code: "14-C",
    ledger_soum: 411,
    system_soum: 402,
    ai_expected_soum: null,
    diff_class: "ledger_over",
  },
  {
    /* ⛔ (c) NING IKKINCHI YARMI — AI rastani BO'SH dedi (O'LCHANGAN). */
    stall_code: "15-C",
    ledger_soum: 0,
    system_soum: 413,
    ai_expected_soum: 0,
    diff_class: "system_over",
  },
  {
    stall_code: "21-B",
    ledger_soum: 415,
    system_soum: 415,
    ai_expected_soum: 425,
    diff_class: "ai_mismatch",
  },
  {
    /* ⛔ (d-41) — «MOS» QATORI JADVALDA QOLADI (maxraj). */
    stall_code: "31-A",
    ledger_soum: 417,
    system_soum: 417,
    ai_expected_soum: 417,
    diff_class: null,
  },
  {
    /* ⛔ NOMA'LUM SINF JIMGINA YO'QOLMAYDI — zaxira yorliq oladi. */
    stall_code: "42-D",
    ledger_soum: 419,
    system_soum: 421,
    ai_expected_soum: 421,
    diff_class: "kelajakdagi_sinf",
  },
];

function payload(over: Partial<Record<string, unknown>> = {}) {
  return {
    day: DAY,
    has_ledger: true,
    rows: ROWS,
    ledger_over_count: LEDGER_OVER,
    system_over_count: SYSTEM_OVER,
    ai_mismatch_count: AI_MISMATCH,
    matched_count: MATCHED,
    ...over,
  };
}

function freezeClock(dayIso: string): Date {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date(`${dayIso}T12:00:00+05:00`));
  return new Date();
}

function openSession(roles: string[] = ["director"]) {
  clearSession();
  setSession({
    accessToken: "t",
    markets: [],
    principal: {
      userId: "33333333-3333-4333-8333-333333333333",
      phone: "+998900000000",
      fullName: "Test Direktor",
      roles,
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

async function renderTable(
  response: unknown,
  roles?: string[],
): Promise<RenderResult> {
  /* ⛔ `beforeEach` dagi standart sessiyaning USTIGA yoziladi. */
  if (roles !== undefined) openSession(roles);

  const now = freezeClock("2026-10-15");

  apiClientMock.apiFetch.mockImplementation((path: string) => {
    if (path.startsWith("/reports/compare")) return Promise.resolve(response);
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
      <NuqsTestingAdapter searchParams={`?day=${DAY}`}>
        <QueryClientProvider client={client}>
          <AuthProvider>
            <CompareTable />
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

/** ⛔ `sr-only` shajaralari AYIRILGAN matn — «ko'rinadigan» ning ta'rifi. */
function visibleText(node: Element): string {
  const hidden = [...node.querySelectorAll(".sr-only")]
    .map((child) => child.textContent ?? "")
    .join("");
  let text = node.textContent ?? "";
  if (hidden !== "") text = text.replace(hidden, "");
  return text.trim();
}

/** Matndagi butun sonlar — ⛔ tinish belgisi ORTIDA ham topiladi. */
function numbersIn(text: string): number[] {
  return [...text.matchAll(/\d+/gu)].map((match) => Number(match[0]));
}

/**
 * ⛔ KO'RINADIGAN MATN BO'LAKLARI — chegaralari SAQLANGAN holda.
 *
 * =========================================================================
 * ⛔⛔ BU YORDAMCHI ⛔ O'LCHANGAN KO'R NUQTANI YOPADI (08-13/08-15 sinfi).
 *
 * Dastlabki shakl butun blokning `textContent` ini olardi va u
 * ⛔ QO'SHNI JUMLALARNI YOPISHTIRARDI: «… Bandlik farqi: 1» + «287 rasta
 * …» -> `…farqi: 1287 rasta…`, ya'ni regeks `1` va `287` o'rniga
 * ⛔ `1287` ni topardi. Da'vo shu sababdan yolg'on-qizil bo'lardi va
 * keyingi ijrochi uni «shovqin» deb bo'shatardi — holbuki mahsulotda
 * hech qanday nosozlik YO'Q (ikki `<p>` orasida ko'z uchun qator uzilishi
 * bor, matn oqimida esa yo'q).
 *
 * ⛔ Shuning uchun matn ⛔ TUGUNMA-TUGUN yig'iladi: har text tuguni
 *    alohida bo'lak bo'lib qoladi va qo'shnisi bilan yopishmaydi.
 *    `sr-only` shajaralari esa BUTUNLAY tashlab ketiladi — da'vo
 *    KO'RINADIGAN matn haqida.
 * =========================================================================
 */
function visibleChunks(root: Element): string[] {
  const chunks: string[] = [];

  const walk = (node: Node): void => {
    if (node.nodeType === Node.TEXT_NODE) {
      chunks.push(node.textContent ?? "");
      return;
    }
    if (node.nodeType !== Node.ELEMENT_NODE) return;
    if ((node as Element).classList.contains("sr-only")) return;
    for (const child of [...node.childNodes]) walk(child);
  };

  walk(root);
  return chunks;
}

/** ⛔ Ko'rinadigan sonlar — yopishgan qo'shnilardan MUSTAQIL. */
function visibleNumbers(root: Element): number[] {
  return visibleChunks(root).flatMap(numbersIn);
}

function bodyRows(view: RenderResult): Element[] {
  return [...view.container.querySelectorAll("tbody tr")];
}

/* -------------------------------------------------------------------------- */
/* G-40(c) — ⛔ `null` BO'SH, `0` CHIZILADI — VA FARQ ASSERT BILAN            */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (c): o'lchanmagan bandlik CHIZILMAYDI", () => {
  test("⛔ `null` katagi BO'SH, `0` katagi `0` chizadi — BITTA testda", async () => {
    const view = await renderTable(payload());
    const rows = bodyRows(view);
    expect(rows).toHaveLength(ROWS.length);

    /* AI-kutilgan — TO'RTINCHI ustun: rasta · daftar · tizim · AI · farq. */
    const measuredZero = rows[1].querySelectorAll("td")[3];
    const notMeasured = rows[0].querySelectorAll("td")[3];

    /*
     * ⛔ BIRINCHI YARIM — O'LCHANGAN NOL HAQIQATAN CHIZILADI. Busiz
     *   pastdagi «bo'sh» da'vosi ustun umuman chizilmagan holatda ham
     *   yashil qolardi.
     */
    expect(visibleText(measuredZero)).toBe("0");

    /*
     * ⛔ IKKINCHI YARIM — O'LCHANMAGAN qiymat KO'RINADIGAN matn bermaydi.
     *   ⛔ `sr-only` AYIRILADI: bo'sh `<td>` skrinriderda jimgina o'tardi,
     *   ya'ni katak SEMANTIK jihatdan NOMLANGAN bo'lishi SHART.
     */
    expect(visibleText(notMeasured)).toBe("");

    /* ⛔ FARQ ASSERT BILAN: ikki katak bir-biriga TENG EMAS. */
    expect(visibleText(notMeasured)).not.toBe(visibleText(measuredZero));

    /* ⛔ Va nomlangan sabab MAVJUD — «jimgina bo'shlik» emas. */
    expect(notMeasured.querySelector(".sr-only")?.textContent).toBe(
      messages.compare.aiNotMeasured,
    );
  });

  test("⛔ uch pul ustuni `font-mono` — ular VERTIKAL solishtiriladi", async () => {
    const view = await renderTable(payload());
    const cells = bodyRows(view)[0].querySelectorAll("td");

    for (const index of [1, 2, 3]) {
      expect(cells[index].className).toContain("font-mono");
    }
  });
});

/* -------------------------------------------------------------------------- */
/* G-40(d) — ⛔ DAFTARSIZ KUN JADVAL BERMAYDI                                 */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (d): daftar yo'q -> JADVAL YO'Q", () => {
  test("⛔ `<table>` 0 marta va NOMLANGAN holat bor", async () => {
    /*
     * ⛔⛔ QATORLAR ⛔ ATAYIN BO'SH EMAS — VA BU O'LCHANGAN QAROR.
     *
     * Dastlab bu da'vo `rows: []` bilan yozilgan edi va u ⛔ YOLG'ON-YASHIL
     * edi: bo'sh massiv «daftar bor, qator yo'q» shoxiga tushib jadvalni
     * baribir chizmasdi, ya'ni `has_ledger` ni butunlay E'TIBORSIZ
     * qoldiradigan sabotaj ⛔ O'TIB KETARDI (o'lchandi).
     *
     * ⛔ HAQIQIY XAVF AYNAN SHU SHAKLDA: server daftarsiz kunda ham
     *    tizim/AI qatorlarini qaytaradi (daftar ustuni 0 bo'lib) va
     *    ularni chizish «hamma farq 0» varaqasini beradi — §10.6 ning
     *    aynan nosozligi.
     */
    const view = await renderTable(
      payload({
        has_ledger: false,
        rows: ROWS,
        ledger_over_count: 0,
        system_over_count: 0,
        ai_mismatch_count: 0,
        matched_count: 0,
      }),
    );

    expect(view.container.querySelectorAll("table")).toHaveLength(0);
    expect(view.container.textContent).toContain(
      messages.compare.ledgerMissing,
    );

    /*
     * ⛔⛔ DIREKTORDA «Daftarni yuklash» TUGMASI YO'Q (260818, Chromeda
     *     jonli topildi).
     *
     * Yuklash yuzasi `STALL_MANAGE` ostida (`reports.py:164`), direktorda
     * u YO'Q. Ilgari bu tugma ko'rinardi va u shunchaki 403 bermasdi —
     * `focusLedgerUpload()` render QILINMAGAN fayl maydonini fokuslardi,
     * ya'ni tugma UMUMAN HECH NIMA qilmasdi.
     *
     * ⛔ Bo'sh holat `action` SIZ ham qonuniy: §14.7 «yagona action li
     *    bo'sh holat» qoidasi HUQUQI BOR foydalanuvchiga tegishli —
     *    keyingi qadami yo'q odamga tugma ko'rsatish yo'l ko'rsatish
     *    emas, yolg'on.
     */
    expect(view.container.textContent).not.toContain(
      messages.compare.ledgerUpload,
    );
    expect(view.container.textContent).toContain(
      messages.compare.ledgerReadOnly,
    );

    /*
     * ⛔ VA UCH SANOQ HAM CHIZILMAYDI: «Daftar ortiq: 0 · Tizim ortiq: 0»
     *   daftarsiz kunda MUVAFFAQIYATLI solishtiruv bo'lib o'qilardi.
     */
    expect(
      view.container.querySelectorAll("[data-diff-count]"),
    ).toHaveLength(0);
  });
});

/* -------------------------------------------------------------------------- */
/* G-41(c) — ⛔ UCH SANOQ UCH ALOHIDA TUGUNDA, BIRLASHTIRGAN SON YO'Q         */
/* -------------------------------------------------------------------------- */

describe("⛔ G-41 (08-UI-SPEC) (c): uch sanoq HECH QACHON qo'shilmaydi", () => {
  test("⛔ uch alohida tugun, uch qiymat, uch sinf nomi", async () => {
    const view = await renderTable(payload());

    const nodes = [...view.container.querySelectorAll("[data-diff-count]")];

    /* ⛔ TO'PLAM TENGLIGI: to'rtinchi sanoq ham, yo'qolgani ham qizaradi. */
    expect(nodes.map((node) => node.getAttribute("data-diff-count"))).toEqual(
      DIFF_ORDER,
    );

    /* ⛔ Har tugunda AYNAN BITTA son va u O'Z sinfiniki. */
    expect(numbersIn(visibleText(nodes[0]))).toEqual([LEDGER_OVER]);
    expect(numbersIn(visibleText(nodes[1]))).toEqual([SYSTEM_OVER]);
    expect(numbersIn(visibleText(nodes[2]))).toEqual([AI_MISMATCH]);

    /* ⛔ MATN KANALI (WCAG 1.4.1): son yolg'iz turmaydi. */
    expect(nodes[0].textContent).toContain(messages.compare.diff.ledgerOver);
    expect(nodes[1].textContent).toContain(messages.compare.diff.systemOver);
    expect(nodes[2].textContent).toContain(messages.compare.diff.aiMismatch);
  });

  test("⛔ BIRLASHTIRGAN SON YO'Q — yig'indi hech qayerda chizilmaydi", async () => {
    const view = await renderTable(payload());

    const summary = view.container.querySelector("[data-compare-summary]");
    expect(summary).not.toBeNull();

    /*
     * ⛔ DA'VO TINISH BELGISIDAN MUSTAQIL: sonlar regeks bilan
     *   AJRATILADI, ya'ni «· 6 ·» ham, «(6)» ham, «6.» ham ushlanadi.
     *   ⛔ VA QO'SHNI JUMLA BILAN YOPISHIB KETMAYDI — `visibleChunks`
     *   izohidagi o'lchangan ko'r nuqta.
     */
    const shown = visibleNumbers(summary as Element);

    expect(shown).toEqual([LEDGER_OVER, SYSTEM_OVER, AI_MISMATCH, MATCHED]);
    expect(shown).not.toContain(COMBINED);
  });

  test("⛔ O'LCHOV — sodda `textContent` shakli SHU YERDA yolg'on-qizil berardi", async () => {
    /*
     * ⛔⛔ BU TEST DARVOZANING O'Z MEXANIZMINI O'LCHAYDI (08-17 dagi
     *   «import filtri haqiqatan kerak» testining aynan sinfi).
     *
     * Sodda shakl butun blokning `textContent` ini olardi va ikki
     * qo'shni jumlani ⛔ YOPISHTIRARDI: «…farqi: 1» + «287 rasta…» ->
     * `1287`. Ya'ni yuqoridagi da'vo mahsulotda hech qanday nosozlik
     * BO'LMAGAN holda qizarardi va keyingi ijrochi uni «shovqin» deb
     * bo'shatardi.
     *
     * ⚠ Faraz eskirsa (razmetka o'zgarib jumlalar yopishmay qolsa) shu
     *   assert QIZARADI va `visibleChunks` ni saqlash sababi QAYTA
     *   baholanadi — jimgina qolib ketmaydi.
     */
    const view = await renderTable(payload());
    const summary = view.container.querySelector("[data-compare-summary]");

    const naive = numbersIn(visibleText(summary as Element));
    const chunked = visibleNumbers(summary as Element);

    expect(naive).not.toEqual(chunked);
    expect(naive).toContain(Number(`${AI_MISMATCH}${MATCHED}`));
  });
});

/* -------------------------------------------------------------------------- */
/* G-41(d) — ⛔ «MOS» QATORI QOLADI VA BEZAK OLMAYDI                          */
/* -------------------------------------------------------------------------- */

describe("⛔ G-41 (08-UI-SPEC) (d): «mos» qatori BEZAKSIZ", () => {
  test("⛔ qator jadvalda BOR, unda badge ham, `data-diff` ham YO'Q", async () => {
    const view = await renderTable(payload());
    const rows = bodyRows(view);

    /* ⛔ NAZORAT: farqli qator badge'ni HAQIQATAN oladi. */
    const differing = rows[0];
    expect(differing.querySelector("[data-diff]")).not.toBeNull();
    expect(differing.textContent).toContain(messages.compare.diff.ledgerOver);

    /* ⛔ «Mos» qatori — TO'RTINCHI (`31-A`) va u YASHIRILMAGAN. */
    const matchRow = rows[3];
    expect(matchRow.textContent).toContain("31-A");
    expect(matchRow.querySelector("[data-diff]")).toBeNull();

    /*
     * ⛔ Farq ustuni katagi BO'SH: 287 ta yashil belgi 13 ta farqni
     *   KO'MIB yuborardi (§13.4).
     */
    const diffCell = matchRow.querySelectorAll("td")[4];
    expect(visibleText(diffCell)).toBe("");
  });

  test("⛔ MAXRAJ jumlasi MAJBURIY (07 G-32 darsi)", async () => {
    const view = await renderTable(payload());

    expect(view.container.textContent).toContain(
      `${MATCHED} rasta uchala manbada mos`,
    );
  });

  test("⛔ NOMA'LUM sinf JIMGINA yo'qolmaydi — zaxira yorliq", async () => {
    const view = await renderTable(payload());
    const unknownRow = bodyRows(view)[4];

    /*
     * ⛔ 04-10 darsi: javob enumi `z.string()` va yangi backend a'zosi
     *   sahifani PARSE chegarasida yiqitmaydi. Lekin u ⛔ JIMGINA
     *   yo'qolmasligi ham SHART — imzolanadigan varaqda nomsiz farq
     *   «mos» bo'lib o'qilardi.
     */
    expect(unknownRow.querySelector("[data-diff]")?.getAttribute("data-diff")).toBe(
      "unknown",
    );
    expect(unknownRow.textContent).toContain(messages.compare.diffUnknown);
  });
});

/* -------------------------------------------------------------------------- */
/* NAZORAT — HUQUQI BOR FOYDALANUVCHIDA TUGMA BOR                             */
/* -------------------------------------------------------------------------- */

describe("⛔ daftar yuklash taklifi — `stall_manage` ko'zgusi", () => {
  test("⛔ NAZORAT: bozor adminida «Daftarni yuklash» BOR", async () => {
    const view = await renderTable(
      payload({
        has_ledger: false,
        rows: [],
        ledger_over_count: 0,
        system_over_count: 0,
        ai_mismatch_count: 0,
        matched_count: 0,
      }),
      ["market_admin"],
    );

    expect(view.container.textContent).toContain(messages.compare.ledgerUpload);
  });
});
