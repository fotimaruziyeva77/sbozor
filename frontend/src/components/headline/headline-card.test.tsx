/**
 * BOSH EKRAN KO'RSATKICHI — G-33 (07-UI-SPEC): «BITTA SON, VA KASSIRNIKI
 * SUMMA EMAS».
 *
 * =============================================================================
 * ⛔ ID KETMA-KETLIGI BILAN YOZILADI (§16.1, 3-qoida). Frontend darvozalari
 *   6-fazada `G-28` da tugagan, ya'ni bu fazaning yangilari `G-29` dan
 *   boshlanadi va bu — o'sha ketma-ketlikning beshinchisi. Yalang'och qisqa
 *   shakl YOZILMAYDI: u `04-UI-SPEC` niki va ikki hujjat bitta belgini
 *   talashardi.
 *
 * ⛔ OLTITA BAND, HAR BIRI ALOHIDA TEST — VA BU BO'LINISH MA'NOLI.
 *   Bandlar UCH XIL qatlamni o'lchaydi: (a)/(f) DOM ni, (b)/(d)/(e)
 *   SHARTNOMANI, (c) esa MANBA MATNINI. Ular bitta testga qo'shilsa, biri
 *   yiqilganda qaysi qatlam buzilgani xabardan ko'rinmasdi va keyingi
 *   ijrochi butun testni «flaky» deb o'chirishga moyil bo'lardi.
 *
 * ⛔ TO'PLAM/SANOQ TENGLIGI, INKOR MATCHER EMAS (§16.2, D-31). «Ikkinchi son
 *   yo'q» degan inkor da'vo UCHINCHI son qo'shilganda JIM qolardi. `toBe(1)`
 *   esa har qanday yangi raqamli tugunda qizaradi.
 *   ⚠ Taqiqlangan inkor matcher nomi bu izohda LITERAL yozilmaydi: qabul
 *     mezoni uni `grep` bilan sanaydi (kodbaza konvensiyasi —
 *     `variance-list.test.tsx` da ham shunday).
 *
 * ⛔ QUYI CHEGARA MAJBURIY (§16.2). Bo'sh skanda «taqiqlangan token
 *   topilmadi» JIMGINA ROST bo'ladi: (c) bandi reyestr uzunligini ham,
 *   skanerlangan fayl sonini ham alohida assert qiladi.
 *
 * ⛔ SABOTAJ BILAN O'LCHANGAN (natijalar 07-05-SUMMARY.md da):
 *   1. kartaga ikkinchi raqamli element qo'shilganda (a) QIZARADI;
 *   2. komponentga sessiya do'koni chaqiruvi qo'shilganda (c) QIZARADI.
 * =============================================================================
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor, within } from "@testing-library/react";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const apiClientMock = vi.hoisted(() => ({ apiFetch: vi.fn() }));

vi.mock("@/lib/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api-client")>();
  return { ...actual, apiFetch: apiClientMock.apiFetch };
});

import messages from "../../../messages/uz-Latn.json";
import { HeadlineCard } from "@/components/headline/headline-card";
import { ApiError } from "@/lib/api-client";
import { HEADLINE_UNIT, headlineResponseSchema } from "@/lib/headline-queries";

const MARKET_ID = "11111111-1111-4111-8111-111111111111";
const LOCALE = "uz-Latn";

/* -------------------------------------------------------------------------- */
/* (c) BANDI UCHUN MANBA SKANERI                                              */
/* -------------------------------------------------------------------------- */

/**
 * Skanerlanadigan katalog.
 *
 * ⚠ `import.meta.url` ATAYIN ISHLATILMAYDI: vite transformidan keyin u
 *   `file:` sxemasida EMAS va `fileURLToPath` yiqiladi (o'lchandi). Yo'l
 *   `process.cwd()` dan quriladi — vitest ni `frontend/` dan ham, repo
 *   ildizidan ham yugurtirish mumkin.
 *
 * ⛔ TOPILMASA — `throw`, `skip` EMAS va bo'sh massiv ham EMAS. Ikkalasi
 *    ham darvozani JIMGINA o'chirardi: skanerlanadigan fayl bo'lmaganda
 *    «taqiqlangan token topilmadi» rost bo'lib qolardi (§16.2).
 */
function resolveHeadlineDir(): string {
  const relative = path.join("src", "components", "headline");
  for (const base of [process.cwd(), path.join(process.cwd(), "frontend")]) {
    const candidate = path.resolve(base, relative);
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(
    `components/headline katalogi topilmadi (cwd: ${process.cwd()}) — ` +
      "(c) bandi skanersiz qolardi va darvoza yolg'on-yashil bo'lardi",
  );
}

const HEADLINE_COMPONENTS = resolveHeadlineDir();

const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

/** Mahsulot fayli emas — u taqiqni O'LCHAYDI, buzmaydi. */
const TEST_FILE = /\.test\.tsx?$/;

/**
 * ⛔ ROL O'QISHNING IZLARI — HAR BIRI `components/headline/**` DA 0.
 *
 * ⚠ Nega SATR LITERALI ham reyestrda (`"cashier"` va hokazo, qo'shtirnoq
 *   BILAN): rol nomini import qilmasdan ham `metric === "cashier"` yoki
 *   `data-role="cashier"` yozib bo'lardi. Qo'shtirnoq ATAYIN — usiz token
 *   `cashier_id` kabi begona nomlarda ham uchrab, darvozani shovqinli
 *   qilardi.
 *
 * ⛔ Bu taqiq INTIZOM EMAS, IMKONSIZLIK: `if (isCashier) { ... }` shoxini
 *    yozish uchun avval shu tokenlardan biri kerak bo'ladi (D-28, §10.2).
 */
const ROLE_TOKENS = [
  "useAuthStore",
  "principal",
  "roles",
  "hasPermission",
  '"cashier"',
  '"director"',
  '"market_admin"',
  '"platform_admin"',
  '"inspector"',
];

/** ⛔ Reyestr qisqartirilsa darvoza JIMGINA bo'shardi (§16.2). */
const MIN_ROLE_TOKENS = 9;

/** ⛔ Bo'sh skanda «token topilmadi» jimgina rost bo'lardi (§16.2). */
const MIN_HEADLINE_FILES = 1;

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * ⚠ Holat mashinasi `collect-surface.test.mjs:215-277` dan ko'chirilgan —
 *   kodbazada har darvoza o'z NUSXASINI olib yuradi (`blind-payload`,
 *   `bulk-action-surface`, `collect-surface`, `role-gate`) va farq faqat
 *   JSDoc matnida. Umumiy modul yozish darvozani boshqa darvoza bilan
 *   bog'lab qo'yardi: bittasini «soddalashtirish» qolganini jimgina
 *   bo'shatardi.
 *
 * Satrlar ATAYIN saqlanadi: tarjima kaliti yoki `data-*` atributi ichidagi
 * taqiqlangan nom ham brauzerga yetib boradi.
 */
function stripComments(source: string): string {
  let out = "";
  let state = "code";
  let i = 0;

  while (i < source.length) {
    const c = source[i];
    const next = source[i + 1];

    if (state === "code") {
      if (c === "/" && next === "/") {
        state = "line";
        i += 2;
      } else if (c === "/" && next === "*") {
        state = "block";
        i += 2;
      } else if (c === "'" || c === '"' || c === "`") {
        state = c;
        out += c;
        i += 1;
      } else {
        out += c;
        i += 1;
      }
      continue;
    }

    if (state === "line") {
      if (c === "\n") {
        state = "code";
        out += c;
      }
      i += 1;
      continue;
    }

    if (state === "block") {
      if (c === "*" && next === "/") {
        state = "code";
        i += 2;
      } else {
        if (c === "\n") out += c;
        i += 1;
      }
      continue;
    }

    if (c === "\\") {
      out += c + (next ?? "");
      i += 2;
      continue;
    }
    if (c === state) {
      state = "code";
    }
    out += c;
    i += 1;
  }

  return out;
}

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv — HOSILA qamrov). */
function listProductFiles(dir: string): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full));
    } else if (
      CODE_EXTENSIONS.includes(path.extname(entry)) &&
      !TEST_FILE.test(entry)
    ) {
      found.push(full);
    }
  }
  return found;
}

/** Faylning izohsiz kodi + «filtr faylni yutib yubormadi» nazorati. */
function readCode(file: string): string {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);

  /*
   * RUNAWAY NAZORATI: holat mashinasi butun faylni izoh deb yutsa, keyingi
   * hamma assert JIMGINA yashil bo'lardi — darvoza o'chgan holda «o'tdi»
   * deb hisobot berardi.
   */
  if (raw.includes("export")) {
    expect(
      code.includes("export"),
      `${path.basename(file)}: izoh filtri faylni YUTIB YUBORDI`,
    ).toBe(true);
  }

  return code;
}

/* -------------------------------------------------------------------------- */
/* (a)/(f) BANDLARI UCHUN DOM YORDAMCHILARI                                   */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ RAQAM TUTUVCHI MATN TUGUNLARI — `Skeleton` CHIQARILGAN.
 *
 * `Skeleton` `aria-hidden="true"` bilan chiziladi va unda matn umuman
 * yo'q, lekin istisno OCHIQ yozilgan: yuklanish holati bir kun raqamli
 * platsholder chizsa (masalan «0»), bu funksiya uni sanamasligi kerak —
 * §10.2 aynan shu «soxta nol» ni taqiqlaydi.
 */
function numericTextNodes(root: HTMLElement): string[] {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const found: string[] = [];

  let node = walker.nextNode();
  while (node !== null) {
    const text = node.textContent ?? "";
    const hidden =
      node.parentElement?.closest('[aria-hidden="true"]') != null;
    if (!hidden && /\d/u.test(text)) found.push(text);
    node = walker.nextNode();
  }
  return found;
}

/** `headline.amountUnit` matnining DOM'dagi UCHRASH SONI. */
function unitOccurrences(root: HTMLElement): number {
  const text = root.textContent ?? "";
  return text.split(messages.headline.amountUnit).length - 1;
}

/* -------------------------------------------------------------------------- */
/* RENDER                                                                     */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ HAR RENDER O'Z KLIENTINI OLADI — VA BU O'LCHANGAN ZARURAT.
 *
 * Kesh kaliti `["m", marketId, "headline"]`, ya'ni u METRIKANI o'z ichiga
 * OLMAYDI (olishi ham mumkin emas: qaysi metrika kelishini server hal
 * qiladi). Bitta test ichida ikki metrikani ketma-ket render qilganda
 * ikkinchisi birinchisining KESHLANGAN javobini darhol chizadi va
 * `aria-busy` umuman paydo bo'lmaydi — natijada (a) va (f) bandlari
 * BIRINCHI javob ustida o'lchanardi (o'lchandi: «47» kutilgan
 * «1 200 000» o'rniga).
 */
let clients: QueryClient[] = [];

function renderCard(marketId: string | null = MARKET_ID) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  clients.push(client);

  return render(
    <NextIntlClientProvider
      locale={LOCALE}
      messages={messages}
      timeZone="Asia/Tashkent"
    >
      <QueryClientProvider client={client}>
        <HeadlineCard marketId={marketId} />
      </QueryClientProvider>
    </NextIntlClientProvider>,
  );
}

/**
 * Javob KELGAN holat — karta chizilgunga qadar kutiladi.
 *
 * ⚠ KUTISH SIGNALI `aria-busy` NING YO'QOLISHI, matn EMAS — va bu
 *   ATAYIN. `findByText(formatlangan son)` ISHLAMAYDI: `Intl` ming
 *   ajratgichi sifatida UZILMAS BO'SHLIQ qo'yadi, Testing Library'ning
 *   standart normalizatori esa uni oddiy bo'shliqqa aylantiradi va
 *   solishtiruv mos kelmaydi (o'lchandi). Xuddi shu sabab bilan
 *   `variance-list.test.tsx` ham xom `textContent` bilan ishlaydi.
 *
 * ⚠ Sanoq bo'yicha kutish (masalan «raqamli tugun 1 ta bo'lguncha») HAM
 *   RAD ETILDI: u (a) bandini TAVTOLOGIYAGA aylantirardi — sabotaj
 *   toza nosozlik o'rniga taymaut bilan qizarardi.
 */
async function renderLoaded(metric: string, value: number) {
  apiClientMock.apiFetch.mockResolvedValue({ metric, value });
  const view = renderCard();

  await waitFor(() => {
    const node = view.container.querySelector("[data-headline]");
    expect(node?.getAttribute("aria-busy") ?? null).toBeNull();
    expect(node?.querySelector("p")).toBeTruthy();
  });

  const root = view.container.querySelector("[data-headline]");
  if (root === null) throw new Error("[data-headline] topilmadi");

  return { ...view, root: root as HTMLElement };
}

beforeEach(() => {
  vi.resetAllMocks();
  clients = [];
});

afterEach(() => {
  for (const client of clients) client.clear();
});

/* ========================================================================== */
/* (a) RAQAMLI TUGUN AYNAN BITTA                                              */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (a) — bitta son, ikkinchisi IMKONSIZ", () => {
  test("⛔ `[data-headline]` ichidagi raqamli matn tugunlari soni AYNAN 1", async () => {
    /*
     * IKKALA BIRLIK ham o'lchanadi va bu ataylab: `"soum"` metrikasida
     * karta QO'SHIMCHA matn tugunlari («so'm», bo'shliq) chizadi va aynan
     * o'sha yo'lda ikkinchi raqam paydo bo'lishi eng oson edi.
     */
    const counted = await renderLoaded("headline.receipts_written", 47);
    expect(numericTextNodes(counted.root)).toHaveLength(1);
    counted.unmount();

    const soum = await renderLoaded("headline.revenue_today", 1_200_000);
    expect(numericTextNodes(soum.root)).toHaveLength(1);

    /* NAZORAT: to'plam bo'sh emas — karta haqiqatan CHIZILGAN. */
    expect(numericTextNodes(soum.root)[0]).toBe(
      new Intl.NumberFormat(LOCALE).format(1_200_000),
    );
  });
});

/* ========================================================================== */
/* (b) SHARTNOMA — KALITLAR TO'PLAMI VA `strictObject`                        */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (b) — javob yuzasi JIMGINA kengaya olmaydi", () => {
  test("⛔ kalitlar to'plami `{metric, value}` ga TENG va ortiqcha maydon THROW qiladi", () => {
    expect(new Set(Object.keys(headlineResponseSchema.shape))).toEqual(
      new Set(["metric", "value"]),
    );

    /* Toza javob — nazorat: sxema qonuniy shaklni RAD ETMAYDI. */
    const clean = { metric: "headline.revenue_today", value: 1 };
    expect(headlineResponseSchema.parse(clean)).toEqual(clean);

    /*
     * ⛔ T-07-23: server `secondary_value` qo'shsa klient PARSE PAYTIDA
     *    yiqiladi. `z.object` bo'lganda maydon jimgina olib tashlanardi va
     *    yuzaning kengayishi hech qayerda ko'rinmasdi.
     */
    expect(() =>
      headlineResponseSchema.parse({ ...clean, secondary_value: 1 }),
    ).toThrow();
  });
});

/* ========================================================================== */
/* (c) IMKONSIZLIK BANDI — MANBA MATNIDA ROL TOKENLARI 0                      */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (c) — komponent ROLNI O'QIY OLMAYDI", () => {
  test("⛔ `components/headline/**` da rol tokenlari HAR BIRI 0", () => {
    /* --- Quyi chegaralar OLDIN: bo'sh skan «yashil» bo'lib qolmasin --- */
    expect(ROLE_TOKENS.length).toBeGreaterThanOrEqual(MIN_ROLE_TOKENS);
    expect(new Set(ROLE_TOKENS).size).toBe(ROLE_TOKENS.length);

    const files = listProductFiles(HEADLINE_COMPONENTS);
    expect(files.length).toBeGreaterThanOrEqual(MIN_HEADLINE_FILES);

    /* Bu darvozaning O'ZI skanerlanmaydi — aks holda u o'z reyestridan
     * qizarardi va uni o'chirishga majbur bo'lardik. */
    expect(files.filter((file) => TEST_FILE.test(path.basename(file)))).toEqual(
      [],
    );

    /* --- TO'PLAM TENGLIGI: topilgan tokenlar to'plami BO'SH --- */
    const hits = files.flatMap((file) => {
      const code = readCode(file).toLowerCase();
      return ROLE_TOKENS.filter((token) =>
        code.includes(token.toLowerCase()),
      ).map((token) => `${path.basename(file)}: ${token}`);
    });

    expect(hits).toEqual([]);
  });
});

/* ========================================================================== */
/* (d) BIRLIK REYESTRI — 3 A'ZO, KASSIRNIKI `count`                           */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (d) — `HEADLINE_UNIT` reyestri", () => {
  test("⛔ kalitlar to'plami AYNAN 3 a'zo va kassirniki `count`", () => {
    /*
     * ⛔ KUTILGAN TO'PLAM SHU YERDA QAYTA YOZILADI, reyestrdan hosila
     *    QILINMAYDI: `Object.keys(HEADLINE_UNIT)` ni o'ziga solishtirish
     *    har qanday o'zgarishda yashil qolardi (05-13 darsi).
     */
    expect(new Set(Object.keys(HEADLINE_UNIT))).toEqual(
      new Set([
        "headline.revenue_today",
        "headline.review_queue",
        "headline.receipts_written",
      ]),
    );
    expect(Object.keys(HEADLINE_UNIT)).toHaveLength(3);

    /*
     * ⛔⛔ PITFALL 1 — QIYMAT BO'YICHA QULFLANGAN. Bu bitta qator CASH-04
     *     ning uch qatlamli ko'rligini (T-06-53, T-06-59, `shifts.py:126`)
     *     bosh ekrandan himoya qiladi: `"soum"` bo'lgan kunda kassir
     *     ekranda tizim summasini ko'rardi va smena yopishda AYNAN SHU
     *     SONNI deklaratsiya qilib, variance'ni HAR DOIM NOLGA aylantirardi.
     */
    expect(HEADLINE_UNIT["headline.receipts_written"]).toBe("count");
    expect(HEADLINE_UNIT["headline.review_queue"]).toBe("count");
    expect(HEADLINE_UNIT["headline.revenue_today"]).toBe("soum");
  });
});

/* ========================================================================== */
/* (e) SXEMADA `_soum` MAYDONI YO'Q                                           */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (e) — pul birligi JAVOBDA emas", () => {
  test("⛔ javob sxemasida `_soum` bilan tugaydigan maydon YO'Q", () => {
    const keys = Object.keys(headlineResponseSchema.shape);

    /* NAZORAT: sxema haqiqatan o'qildi (bo'sh ro'yxatda shart jimgina rost). */
    expect(keys.length).toBeGreaterThan(0);

    expect(keys.filter((key) => key.endsWith("_soum"))).toEqual([]);
  });
});

/* ========================================================================== */
/* (f) `count` METRIKADA BIRLIK MATNI CHIZILMAYDI                             */
/* ========================================================================== */

describe("G-33 (07-UI-SPEC) (f) — kassirning sonida «so'm» YO'Q", () => {
  test("⛔ `receipts_written` da birlik 0 marta; NAZORAT: `revenue_today` da bor", async () => {
    const cashier = await renderLoaded("headline.receipts_written", 47);
    expect(unitOccurrences(cashier.root)).toBe(0);
    cashier.unmount();

    /*
     * ⛔ NAZORAT HOLATI MAJBURIY: usiz «birlik yo'q» da'vosi «birlik HECH
     *    QACHON chizilmaydi» holatidan ajralmasdi va `amountUnit` ni
     *    butunlay o'chirgan regressiya JIM o'tardi.
     */
    const director = await renderLoaded("headline.revenue_today", 1_200_000);
    expect(unitOccurrences(director.root)).toBe(1);
  });
});

/* ========================================================================== */
/* G-33 DAN TASHQARI — `403` NOLGA AYLANMAYDI (T-05-04, §10.2)                */
/* ========================================================================== */

describe("⛔ ko'rsatkich yo'q bo'lsa KARTA CHIZILMAYDI", () => {
  test("⛔ `403` da `container.firstChild` NULL — na nol, na tire", async () => {
    apiClientMock.apiFetch.mockRejectedValue(
      new ApiError(403, "headline_unavailable"),
    );
    const view = renderCard();

    await waitFor(() => expect(view.container.firstChild).toBeNull());

    /*
     * ⛔ NOL O'LCHANGAN QIYMAT bo'lardi: «bugun hech narsa yig'ilmadi»
     *    degan ma'noni berardi va u YOLG'ON edi (05-14 darsi).
     */
    expect(view.container.textContent).toBe("");
  });

  test("⛔ tarmoq xatosida ham karta chizilmaydi (qizil blok YO'Q, §10.2)", async () => {
    apiClientMock.apiFetch.mockRejectedValue(new Error("network_error"));
    const view = renderCard();

    await waitFor(() => expect(view.container.firstChild).toBeNull());
  });

  test("bozor tanlanmaganda so'rov ham yuborilmaydi", () => {
    const view = renderCard(null);

    expect(view.container.firstChild).toBeNull();
    expect(apiClientMock.apiFetch.mock.calls).toEqual([]);
  });
});

/* ========================================================================== */
/* NOMA'LUM METRIKA — JIMGINA YASHIRILMAYDI (04-10 darsi)                     */
/* ========================================================================== */

describe("noma'lum metrika ZAXIRA yorliq bilan ko'rsatiladi", () => {
  test("noma'lum kalitda son chiziladi, birlik esa QO'SHILMAYDI", async () => {
    const view = await renderLoaded("headline.brand_new_metric", 12);

    expect(within(view.root).getByText(messages.headline.unknown))
      .toBeInTheDocument();
    /* ⛔ Zaxira birlik — eng KAM da'vo qiladigan `"count"`. */
    expect(unitOccurrences(view.root)).toBe(0);
    /* Son hamon AYNAN BITTA: zaxira yo'l (a) bandini buzmaydi. */
    expect(numericTextNodes(view.root)).toHaveLength(1);
  });
});
