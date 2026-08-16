/**
 * ⛔ G-37(b) — SOLISHTIRUV SAHIFASINING BLOK REYESTRI VA MAZMUN JUFTLIGI.
 *
 * =============================================================================
 * ⛔⛔ (b) UCH BLOK — `{day, ledger, comparison}` GA ⛔ TENG.
 *     To'plam tengligi, «bormi?» EMAS: qo'shimcha blok qo'shilsa ham,
 *     bittasi yo'qolsa ham darvoza qizaradi.
 *
 * ⛔⛔ MAZMUN JUFTLIGI — ENG QIMMAT BAND (06-faza G-25 ning o'lchangan
 *     ko'rligi): faqat blok atributlarini tekshiradigan darvozani ⛔ BO'SH
 *     O'RAM mukammal qondirardi va butun yuza ⛔ CHIZILMAGAN holda faza
 *     yashil qaytardi. Shuning uchun mazmun atributini ⛔ BLOKNING O'ZI
 *     chiqaradi va sahifa uni ⛔ HECH QACHON yozmaydi.
 *
 * ⛔ `CONTENT_EXEMPT = {"day"}` — kun tanlagichi BOSHQARUV, ro'yxat emas.
 *    To'plamning O'LCHAMI ⛔ ALOHIDA assert bilan qulflanadi: istisno
 *    qo'shish darvozani bo'shashtiradigan YAGONA yo'l, ya'ni u ko'zga
 *    tashlanishi kerak.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ G-40(d) — DAFTARSIZ KUNDA `<table>` ⛔ 0 MARTA.
 *     Bu fazadagi eng qimmat yolg'on-yashil: «hamma farq 0» jadvali
 *     MUVAFFAQIYATLI solishtiruv bo'lib ko'rinardi va u ⛔ IMZOLANARDI.
 *
 * ⛔ D-19 (§10.7): qog'ozdagi tasdiq amali tizimda ⛔ TAKRORLANMAYDI —
 *    manba skani buni mexanik o'lchaydi (tizim qog'ozda nima bo'lganini
 *    BILMAYDI va bilmagan narsasini ko'rsatmaydi).
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { NuqsTestingAdapter } from "nuqs/adapters/testing";
import { beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));
const toastMock = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

vi.mock("sonner", () => ({ toast: toastMock }));

import messages from "../../../../../../messages/uz-Latn.json";
import ComparePage from "./page";
import { AuthProvider, clearSession, setSession } from "@/lib/auth-store";

const TIME_ZONE = "Asia/Tashkent";
const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const DAY = "2026-10-10";

/**
 * ⛔ BLOK REYESTRI — kutilma SHU YERDA, mahsulot kodidan IMPORT
 *    QILINMAYDI (05-15 darsi): import qilingan reyestr darvozani o'zi
 *    tekshirayotgan qiymatga bog'lardi va blok o'chirilsa kutilma HAM
 *    o'chib, tenglik JIMGINA rost bo'lib qolardi.
 */
const BLOCKS = ["day", "ledger", "comparison"];

/** ⛔ Mazmun atributidan ozod bloklar — AYNAN BITTA (§10.1). */
const CONTENT_EXEMPT = new Set(["day"]);

/** ⛔ Uch xonali summalar — guruh ajratgichi DOM'da satrni buzmasin. */
const ROWS = [
  {
    stall_code: "14-C",
    ledger_soum: 411,
    system_soum: 402,
    ai_expected_soum: null,
    diff_class: "ledger_over",
  },
  {
    stall_code: "31-A",
    ledger_soum: 417,
    system_soum: 417,
    ai_expected_soum: 417,
    diff_class: null,
  },
];

function payload(over: Record<string, unknown> = {}) {
  return {
    day: DAY,
    has_ledger: true,
    rows: ROWS,
    ledger_over_count: 1,
    system_over_count: 0,
    ai_mismatch_count: 0,
    matched_count: 287,
    ...over,
  };
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

async function renderPage(response: unknown = payload()) {
  const now = new Date("2026-10-15T12:00:00+05:00");

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
            <ComparePage />
          </AuthProvider>
        </QueryClientProvider>
      </NuqsTestingAdapter>
    </NextIntlClientProvider>,
  );

  /*
   * ⚠ IKKI BOSQICHLI KUTISH va ikkalasi ham KERAK: (1) bloklar chizildi
   *   (`Suspense` chegarasi ochildi); (2) ⛔ birorta blok HAMON
   *   yuklanmayapti. Faqat (1) ni kutish mazmun juftligini
   *   TAVTOLOGIYAGA aylantirardi — skelet holatidagi blok ham mazmun
   *   atributini chiqaradi (u ATAYIN shunday).
   */
  await waitFor(() => {
    expect(
      view.container.querySelectorAll("[data-compare-block]").length,
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

async function pageSource(): Promise<string> {
  const { existsSync, readFileSync } = await import("node:fs");
  const { join } = await import("node:path");

  /*
   * ⚠ `import.meta.url` vite transformidan keyin `file:` sxemasida EMAS
   *   — yo'l `process.cwd()` dan quriladi (07-05 da o'lchangan).
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
    "compare",
    "page.tsx",
  );
  if (!existsSync(file)) throw new Error(`sahifa fayli topilmadi: ${file}`);
  return readFileSync(file, "utf8");
}

/* -------------------------------------------------------------------------- */
/* G-37(b) — BLOK TO'PLAMI TENG                                               */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (b): uch blok — TO'PLAM TENGLIGI", () => {
  test("⛔ daftar BOR kunda AYNAN uch blok", async () => {
    const { container } = await renderPage();

    expect(attrValues(container, "data-compare-block")).toEqual(
      new Set(BLOCKS),
    );
  });

  test("⛔ daftar YO'Q kunda ham AYNAN O'SHA to'plam", async () => {
    /*
     * ⛔ ENG QIMMAT YARMI: «ma'lumot yo'q -> blokni yashirish» eng tabiiy
     *   noto'g'ri refleks. Chizilmagan solishtiruv bloki adminga
     *   «solishtirish kerak emas» bo'lib o'qilardi — holbuki u
     *   «daftarni yuklang» degani.
     */
    const { container } = await renderPage(
      payload({
        has_ledger: false,
        rows: [],
        ledger_over_count: 0,
        matched_count: 0,
      }),
    );

    expect(attrValues(container, "data-compare-block")).toEqual(
      new Set(BLOCKS),
    );
  });
});

/* -------------------------------------------------------------------------- */
/* G-37(b) — MAZMUN JUFTLIGI VA ISTISNO O'LCHAMI                              */
/* -------------------------------------------------------------------------- */

describe("⛔ G-37 (08-UI-SPEC) (b): mazmun juftligi", () => {
  test("⛔ istisnolar to'plami AYNAN BITTA a'zoli (alohida assert)", () => {
    expect(CONTENT_EXEMPT.size).toBe(1);
    expect(CONTENT_EXEMPT.has("day")).toBe(true);
  });

  test("⛔ mazmun to'plami = bloklar \\ istisno", async () => {
    const { container } = await renderPage();

    const blocks = attrValues(container, "data-compare-block");
    const expected = new Set(
      [...blocks].filter((block) => !CONTENT_EXEMPT.has(block)),
    );

    /* ⛔ Da'vo (b) DAN HOSILA — qo'lda yozilgan ikkinchi ro'yxat emas. */
    expect(attrValues(container, "data-compare-content")).toEqual(expected);
  });

  test("⛔ daftarsiz kunda ham mazmun juftligi BUZILMAYDI", async () => {
    /*
     * ⛔ Nomlangan bo'sh holat ham MAZMUN: atribut jadval borligini emas,
     *   blokning javob berganini o'lchaydi. Aks holda daftarsiz kun butun
     *   darvozani qizartirardi va keyingi ijrochi uni bo'shatardi.
     */
    const { container } = await renderPage(
      payload({ has_ledger: false, rows: [], matched_count: 0 }),
    );

    const blocks = attrValues(container, "data-compare-block");
    const expected = new Set(
      [...blocks].filter((block) => !CONTENT_EXEMPT.has(block)),
    );

    expect(attrValues(container, "data-compare-content")).toEqual(expected);
  });

  test("⛔ `page.tsx` da mazmun atributi 0 marta", async () => {
    const source = await pageSource();

    /*
     * ⛔ Atribut sahifada bo'lsa, sahifa mazmun juftligini PLATSHOLDER
     *   bilan qondira olardi — o'zining false-green iga o'zi yo'l
     *   ochardi. Atributning NOMI ham manba faylda uchramaydi.
     */
    expect((source.match(/data-compare-content/gu) ?? []).length).toBe(0);
  });
});

/* -------------------------------------------------------------------------- */
/* G-37(e) NAQSHI — MAZMUN MOCK'DAN HOSILA                                    */
/* -------------------------------------------------------------------------- */

describe("⛔ mazmun MOCK'DAGI AYNAN QIYMATGA qadalgan", () => {
  test("⛔ jadval qatorlari soni mock massivining UZUNLIGIDAN", async () => {
    const { container } = await renderPage();
    const block = container.querySelector('[data-compare-content="comparison"]');

    expect(block).not.toBeNull();
    expect(block?.querySelectorAll("tbody tr").length).toBe(ROWS.length);
    expect(block?.textContent).toContain(ROWS[0].stall_code);
  });
});

/* -------------------------------------------------------------------------- */
/* G-40(d) — ⛔ DAFTARSIZ KUNDA JADVAL YO'Q                                   */
/* -------------------------------------------------------------------------- */

describe("⛔ G-40 (08-UI-SPEC) (d): daftarsiz kun «muvaffaqiyat» BERMAYDI", () => {
  test("⛔ `<table>` DOM'da 0 marta va nomlangan holat BOR", async () => {
    const { container } = await renderPage(
      payload({
        has_ledger: false,
        rows: [],
        ledger_over_count: 0,
        system_over_count: 0,
        ai_mismatch_count: 0,
        matched_count: 0,
      }),
    );

    expect(container.querySelectorAll("table")).toHaveLength(0);
    expect(container.textContent).toContain(messages.compare.ledgerMissing);
  });

  test("⛔ NAZORAT: daftar BOR kunda jadval HAQIQATAN chiziladi", async () => {
    /*
     * ⛔ Busiz yuqoridagi da'vo «jadval umuman qurilmagan» holatida ham
     *   yashil qolardi — ya'ni darvoza hech nimani o'lchamasdi.
     */
    const { container } = await renderPage();

    expect(container.querySelectorAll("table")).toHaveLength(1);
  });

  test("⛔ daftarsiz kunda EKSPORT ham taklif qilinmaydi", async () => {
    /*
     * ⛔ §12.6: fayl PASTIDA tasdiq qatorlari bor, ya'ni daftarsiz kunning
     *   `.xlsx` i «hamma farq 0» varaqasi bo'lib CHOP ETILARDI va
     *   ekrandagi taqiq faylda AYLANIB O'TILARDI (T-08-79 ning fayl
     *   yarmi).
     */
    const { container } = await renderPage(
      payload({ has_ledger: false, rows: [], matched_count: 0 }),
    );

    const exportButton = [...container.querySelectorAll("button")].find(
      (node) => node.textContent?.includes(messages.reports.export),
    );

    expect(exportButton).toBeDefined();
    expect(exportButton?.getAttribute("aria-disabled")).toBe("true");
  });
});

/* -------------------------------------------------------------------------- */
/* §10.7 / D-19 — ⛔ QOG'OZDAGI TASDIQ TIZIMDA TAKRORLANMAYDI                 */
/* -------------------------------------------------------------------------- */

describe("⛔ D-19 (§10.7): tasdiq tugmasi QURILMAYDI", () => {
  test("⛔ sahifa manbasida tasdiq amalining tokenlari 0 marta", async () => {
    const source = await pageSource();

    /*
     * ⛔ Tizim qog'ozda nima bo'lganini ⛔ BILMAYDI. Tugma uni BORDEK
     *   ko'rsatardi va «bu varaq tasdiqlangan» degan holat bazada
     *   yozilardi — holbuki uning ortida HECH QANDAY dalil yo'q.
     *
     * ⚠ Tokenlar bu yerda LITERAL yozilgan, mahsulot faylida esa ATAYIN
     *   uchramaydi (kodbaza konvensiyasi: darvoza xom `grep` bilan
     *   o'lchaydi, izohdagi nusxa uni o'ziga qarshi qo'yardi).
     */
    for (const token of [/imzola/giu, /\[Sign/giu, /signed/giu]) {
      expect((source.match(token) ?? []).length).toBe(0);
    }
  });
});

/* -------------------------------------------------------------------------- */
/* HUQUQ KO'ZGUSI — SO'ROVDAN OLDIN                                           */
/* -------------------------------------------------------------------------- */

describe("⛔ huquq ko'zgusi — `report_view`", () => {
  test("⛔ kassirda birorta so'rov UMUMAN ketmaydi", async () => {
    openSession(["cashier"]);

    apiClientMock.apiFetch.mockResolvedValue(payload());

    const view = render(
      <NextIntlClientProvider
        locale="uz-Latn"
        messages={messages}
        now={new Date("2026-10-15T12:00:00+05:00")}
        timeZone={TIME_ZONE}
      >
        <NuqsTestingAdapter searchParams={`?day=${DAY}`}>
          <QueryClientProvider
            client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
          >
            <AuthProvider>
              <ComparePage />
            </AuthProvider>
          </QueryClientProvider>
        </NuqsTestingAdapter>
      </NextIntlClientProvider>,
    );

    /*
     * ⚠ HAQIQIY NAZORAT SERVERDA (`require_permission`, 08-16). Bu ko'zgu
     *   faqat foydalanuvchini bajarilmas so'rovdan qaytaradi — u DevTools
     *   bilan olib tashlanadi va xavfsizlik chegarasi EMAS.
     */
    expect(view.container.querySelectorAll("[data-compare-block]")).toHaveLength(
      0,
    );
    expect(apiClientMock.apiFetch).not.toHaveBeenCalled();
  });
});
