#!/usr/bin/env node
/**
 * HISOBOT YUZASINING REYESTR, MATN VA SO'ROV DARVOZASI (08-UI-SPEC §16.6).
 *
 * =============================================================================
 * Bu fayl 08-UI-SPEC ning OLTI bandini bitta MEXANIZMGA bog'laydi:
 *
 *   G-38(a) — `components/reports/**` + `lib/report-queries.ts` da
 *             tokensiz yuklab olish yo'llari NOLGA qulflanadi
 *   G-38(b) — `lib/report-queries.ts` da `apiRequest` YAGONA yo'l
 *   G-41(a) — uch farq sinfi × 3 locale, to'plam tengligi bilan
 *   G-41(b) — «birlashtirilgan farq» nomlari NOLGA qulflanadi
 *   G-42    — hisobot katalogining taqiqlangan nomlari, aksent byudjeti
 *             va ⛔ IKKI KATALOG IKKI RO'YXAT qoidasi
 *   G-43    — yopiq reyestrlar (`REPORT_KINDS`, `PERIOD_PRESETS`) × 3
 *             locale, taqiqlangan copy va ICU platsholderlari
 *
 * ⛔ ID KETMA-KETLIGI BILAN YOZILADI: 08-UI-SPEC ning yangi darvozalari
 *   `G-37` dan boshlanadi [M-14]. Yalang'och `G-3`/`G-4` YOZILMAYDI — u
 *   boshqa fazaning darvozasi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ KATALOG SKANI 08-03 DA ATAYIN OCHIQ QOLDIRILGAN EDI — TETIK
 *     BAJARILDI VA BLOKLAR 08-17 DA QO'SHILDI.
 * -----------------------------------------------------------------------
 * 08-03 kunida `src/components/reports/` katalogi UMUMAN yo'q edi,
 * G-38(a) esa o'z quyi chegarasida ⛔ ≥6 skanerlangan fayl talab qiladi:
 *
 *   • Chegarani O'SHANDA pasaytirish (masalan ≥1 ga) darvozani
 *     ⛔ DOIMIY bo'shatardi — keyin hech kim uni qaytarib ko'tarmasdi;
 *   • Chegarani o'shanda yozib qoldirish esa uni ⛔ YOLG'ON-QIZIL
 *     qilardi va keyingi ijrochi blokni «shovqin» deb O'CHIRARDI.
 *
 * ⛔ Shuning uchun uchinchi yo'l tanlangan edi: blok yozilmadi, egasi va
 *    tetigi izohda NOMLANDI. Tetik bajarildi — 08-09 ikkita, 08-13
 *    ikkita, 08-15 yana ikkita mahsulot faylini keltirdi, ya'ni katalog
 *    ALLAQACHON oltita fayl. Bloklar shu bilan (fayl OXIRIDA) qo'shildi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ BU FAYL OMMAVIY-AMAL DARVOZASINING UI-SPEC E'LONINI TAQLID
 *     QILMAYDI [M-4].
 * -----------------------------------------------------------------------
 * `bulk-action-surface.test.mjs` UI-SPEC fayllarini O'QIYDI va o'z
 * e'lonini `assert.equal(SPEC_FILES.length, 1)` bilan qulflaydi. Ya'ni
 * o'sha e'lon shaklidagi ikkinchi jadval qatori — qayerda yozilishidan
 * qat'i nazar — `npm run gate` ni BUTUNLAY qizartirardi.
 *
 * ⛔ Shuning uchun bu fayl na o'sha shakldagi jadval qatorini yozadi,
 *    na uni izlaydigan regeks qo'shadi. Hisobot katalogining o'sha
 *    skanga qo'shilishi 05-UI-SPEC §15 dagi MAVJUD qatorga beshinchi
 *    naqsh qo'shish bilan bajariladi (W0-F5) va u ham 08-15 ning ishi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ IKKI MUZOKARASIZ XOSSA (har darvozada, §16.2)
 * -----------------------------------------------------------------------
 *   1. ⛔ HOSILA QAMROV — reyestrlar `api-types.ts` ning MANBA MATNIDAN
 *      o'qiladi va ulardan ITERATSIYA qilinadi. Qo'lda yozilgan kalit
 *      ro'yxati bir kun ortda qolardi va buni hech nima aytmasdi.
 *
 *   2. ⛔ TO'PLAM TENGLIGI — inkor qiluvchi da'vo («bu kalit bormi?»)
 *      qo'shni YANGI kalitni ham, reyestrdan olib tashlangan a'zoning
 *      O'LIK kalitini ham KO'RMASDI. Tenglik ikkalasini ham ushlaydi.
 *
 * ⛔ VA QUYI CHEGARA (`MIN_*`): skanerlanadigan fayl yoki qiymat soni
 *   kamaysa darvoza QIZARADI. Bo'sh to'plamda «taqiqlangan token
 *   topilmadi» JIMGINA rost bo'ladi.
 *
 * ⚠ REYESTR IMPORT QILINMAYDI, MATN SIFATIDA O'QILADI (05-13 va 05-15
 *   darsi): darvoza o'zi tekshirayotgan qiymatni tekshirilayotgan
 *   moduldan olsa, ikkalasi BIRGA o'zgarganda JIMGINA yashil qolardi.
 *
 * ⚠ IZOHLAR OLIB TASHLANADI va busiz darvoza BUGUN qizarardi —
 *   O'LCHANDI: `lib/report-queries.ts` ning bosh izohida `fetch(`,
 *   `window.open`, `location.href` va `document.createElement("a")`
 *   MATN sifatida yozilgan, chunki izoh aynan o'sha taqiqni
 *   tushuntiradi. `stripComments()` `bulk-action-surface.test.mjs` dan
 *   KO'CHIRILGAN (import EMAS: darvoza o'zi tekshirayotgan mexanizmga
 *   bog'lanib qolmasligi kerak).
 * =============================================================================
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

const API_TYPES = path.join(SRC, "lib", "api-types.ts");
const REPORT_QUERIES = path.join(SRC, "lib", "report-queries.ts");
const REPORT_COMPONENTS = path.join(SRC, "components", "reports");

const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

/* -------------------------------------------------------------------------- */
/* QUYI CHEGARALAR — ⛔ HAR BLOKDA MAJBURIY (§16.2)                           */
/* -------------------------------------------------------------------------- */

/**
 * Har locale'da skanerlanadigan eng kam `reports.*` + `compare.*` qiymati.
 *
 * Bugun 64 ta. Chegara 30: matn katalogi shundan kam bo'lsa, skan
 * maydoni JIMGINA qisqargan demakdir va taqiqlangan copy darvozasi
 * bo'sh to'plamda yashil qolardi.
 */
const MIN_REPORT_VALUES = 30;

/** Taqiqlangan copy tokenlarining eng kam soni (uchala locale bo'yicha). */
const MIN_FORBIDDEN_COPY_TOKENS = 9;

/** So'rov modulida skanerlanadigan eng kam fayl soni. */
const MIN_SCANNED_QUERY_FILES = 1;

/** So'rov modulida tekshiriladigan eng kam taqiqlangan token soni. */
const MIN_SURFACE_TOKENS = 5;

/* -------------------------------------------------------------------------- */
/* IZOH FILTRI — `bulk-action-surface.test.mjs:163-225` dan KO'CHIRILGAN      */
/* -------------------------------------------------------------------------- */

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * Satrlar ATAYIN saqlanadi: yo'l konstantasi, tarjima kaliti yoki
 * `className` ichidagi token ham brauzerga YETIB BORADI.
 */
function stripComments(source) {
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
        // Qator raqamlari saqlanadi — xato xabarida foydali.
        if (c === "\n") out += c;
        i += 1;
      }
      continue;
    }

    // Satr literali ichida: `state` ochuvchi belgining O'ZI.
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

/* -------------------------------------------------------------------------- */
/* O'QUVCHILAR                                                                */
/* -------------------------------------------------------------------------- */

function read(file) {
  return readFileSync(file, "utf8");
}

function loadMessages(locale) {
  return JSON.parse(
    read(path.join(FRONTEND_ROOT, "messages", `${locale}.json`)),
  );
}

/**
 * `export const NAME = [ "a", "b" ] as const;` — TS reyestrini o'qiydi.
 *
 * ⚠ NAQSH `[A-Za-z0-9_-]+` va bu ATAYIN KENG: `PERIOD_PRESETS` da
 *   `last30` (RAQAM aralashgan) va `thisMonth` (BOSH HARFLI) a'zolari
 *   bor. `reconciliation-copy.test.mjs` dagi `[a-z_]+` naqshi ularni
 *   JIMGINA tashlab ketardi va reyestr uch a'zoli bo'lib ko'rinardi —
 *   ya'ni «aynan besh a'zo» asserti yolg'on-qizil, to'plam tengligi esa
 *   yolg'on-yashil bo'lardi.
 *
 * ⛔ IZOH BLOKI QAMRALMAYDI: naqsh `export const NAME = [` dan
 *    boshlanadi, izohlar esa undan OLDIN turadi. Aks holda
 *    `REPORT_KINDS` ning izohidagi `"three-way"` va `"compare"`
 *    misollari reyestr a'zosi bo'lib o'qilardi.
 */
function readTsRegistry(source, name) {
  const block = new RegExp(
    `export const ${name}\\s*=\\s*\\[([\\s\\S]*?)\\]\\s*as const;`,
    "u",
  ).exec(source);
  assert.ok(block, `\`${name}\` topilmadi — parser sinigan`);
  return [...block[1].matchAll(/"([A-Za-z0-9_-]+)"/gu)].map((m) => m[1]);
}

/** `ledger_over` -> `ledgerOver` (reyestr a'zosi -> matn kaliti). */
function toCamel(value) {
  return value.replace(/_([a-z0-9])/gu, (_, ch) => ch.toUpperCase());
}

/** `reports.*` + `compare.*` ning barcha satr QIYMATLARI (ichma-ich ham). */
function surfaceValues(locale) {
  const messages = loadMessages(locale);
  const found = [];
  const walk = (node) => {
    for (const value of Object.values(node ?? {})) {
      if (typeof value === "string") found.push(value);
      else if (typeof value === "object" && value !== null) walk(value);
    }
  };
  walk(messages.reports);
  walk(messages.compare);
  return found;
}

/** Locale × namespace yo'li -> kalitlar to'plami. */
function messageKeys(locale, segments) {
  let node = loadMessages(locale);
  for (const segment of segments) node = node?.[segment];
  assert.ok(
    node && typeof node === "object",
    `${locale}: \`${segments.join(".")}\` topilmadi`,
  );
  return new Set(Object.keys(node));
}

const apiTypesSource = read(API_TYPES);

const reportKinds = readTsRegistry(apiTypesSource, "REPORT_KINDS");
const periodPresets = readTsRegistry(apiTypesSource, "PERIOD_PRESETS");
const diffClasses = readTsRegistry(apiTypesSource, "DIFF_CLASSES");

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/* -------------------------------------------------------------------------- */

test("QAMROV: uchala reyestr ham MANBA MATNIDAN o'qildi (nazorat)", () => {
  /*
   * Parser sinsa (masalan reyestr `Record` ga aylantirilsa) quyidagi
   * darvozalarning HAMMASI bo'sh to'plam bo'yicha aylanib, JIMGINA
   * yashil qolardi.
   */
  assert.ok(reportKinds.length > 0, "`REPORT_KINDS` bo'sh o'qildi");
  assert.ok(periodPresets.length > 0, "`PERIOD_PRESETS` bo'sh o'qildi");
  assert.ok(diffClasses.length > 0, "`DIFF_CLASSES` bo'sh o'qildi");
});

test("QAMROV: parser RAQAM va BOSH HARF aralashgan a'zoni ham o'qiydi", () => {
  /*
   * ⛔ O'LCHANGAN NAZORAT: `[a-z_]+` naqshi `last30` va `thisMonth` ni
   *   TASHLAB ketardi. Bu assert o'sha torayishni qizartiradi.
   */
  assert.ok(periodPresets.includes("last30"), "`last30` o'qilmadi — parser tor");
  assert.ok(
    periodPresets.includes("thisMonth"),
    "`thisMonth` o'qilmadi — parser tor",
  );
});

test("QAMROV: har locale'da kamida 30 ta yuza qiymati skanerlanadi", () => {
  for (const locale of LOCALES) {
    const values = surfaceValues(locale);
    assert.ok(
      values.length >= MIN_REPORT_VALUES,
      `${locale}: atigi ${values.length} ta \`reports.*\`/\`compare.*\` ` +
        `qiymati skanerlandi (quyi chegara ${MIN_REPORT_VALUES}) — skan ` +
        "maydoni jimgina qisqargan",
    );
  }
});

test("IZOH FILTRI: kodni yutib yubormaydi va satr literalini saqlaydi", () => {
  const code = stripComments('const s = "/* izoh EMAS */";\nexport const keep = s;');

  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(code.includes("/* izoh EMAS */"), "satr literali izoh deb o'chirildi");
  assert.equal(stripComments("/* faqat izoh */\n").trim(), "");
});

/* -------------------------------------------------------------------------- */
/* G-43(a) — `REPORT_KINDS` AYNAN TO'RT A'ZO (§12.1)                          */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ KUTILGAN TO'PLAM TESTDA QAYTA YOZILGAN, mahsulotdan IMPORT
 *    QILINMAGAN (05-15 darsi): import darvozani o'zi tekshirayotgan
 *    qiymatga bog'lardi va reyestrga qo'shilgan beshinchi a'zo
 *    JIMGINA o'tib ketardi.
 */
const EXPECTED_REPORT_KINDS = new Set([
  "revenue",
  "debtors",
  "anomalies",
  "accuracy",
]);

test("⛔ G-43 (08-UI-SPEC) (a): `REPORT_KINDS` — TO'PLAM TENGLIGI, aynan 4 a'zo", () => {
  assert.equal(
    reportKinds.length,
    4,
    `\`REPORT_KINDS\` da ${reportKinds.length} a'zo (kutilgan 4): ${reportKinds}`,
  );
  assert.equal(
    new Set(reportKinds).size,
    reportKinds.length,
    `takrorlangan a'zo: ${reportKinds}`,
  );

  assert.deepEqual(
    new Set(reportKinds),
    EXPECTED_REPORT_KINDS,
    "⛔ `REPORT_KINDS` yopiq to'plamdan AJRALDI. Reyestr «hisobot TURI» ni " +
      "bildiradi va uning HAR a'zosi `from`/`to` davrini MAJBURIY qiladi.",
  );
});

test("⛔ G-43 (08-UI-SPEC) (a): solishtiruv reyestr ICHIDA YO'Q", () => {
  /*
   * ⛔ ENG QIMMAT BAND. Solishtiruvning davri KUN, shakli esa IMZOLI
   *   varaq. Uni reyestrga tiqish `REPORT_KINDS` ni «yuklab olinadigan
   *   NARSA» ga aylantirardi va o'sha lahzada davr parametrlari
   *   IXTIYORIY bo'lib qolardi — ya'ni davrsiz eksport chaqiruvi tip
   *   tizimidan jimgina o'tib ketardi. Davrsiz fayl esa §1.2 qoida 2
   *   ning bevosita buzilishi.
   */
  const leaked = reportKinds.filter((kind) =>
    ["three-way", "threeWay", "three_way", "compare", "ledger"].includes(kind),
  );

  assert.deepEqual(
    leaked,
    [],
    `⛔ solishtiruv \`REPORT_KINDS\` ga kirdi: ${leaked}`,
  );
});

/* -------------------------------------------------------------------------- */
/* G-43(b) — `PERIOD_PRESETS` × 3 LOCALE (§4.4)                               */
/* -------------------------------------------------------------------------- */

test("⛔ G-43 (08-UI-SPEC) (b): `PERIOD_PRESETS` AYNAN 5 a'zo (4 preset + custom)", () => {
  assert.equal(
    periodPresets.length,
    5,
    `\`PERIOD_PRESETS\` da ${periodPresets.length} a'zo (kutilgan 5): ` +
      `${periodPresets}`,
  );

  /*
   * ⛔ `custom` — PRESET EMAS, uning YO'QLIGINING nomi. U reyestrda
   *   BO'LISHI shart: URL'da faqat `from`/`to` bor va preset ular
   *   qiymatidan TESKARI hisoblanadi; hech qaysi presetga mos
   *   kelmaganda natija `custom` bo'ladi. Reyestrdan chiqarilsa
   *   tanlagichda NOMSIZ oltinchi holat qolardi.
   */
  assert.ok(
    periodPresets.includes("custom"),
    "`custom` reyestrdan tushib qolgan — tanlagichda nomsiz holat qoladi",
  );
});

test("⛔ G-43 (08-UI-SPEC) (b): `reports.preset.*` UCHALA locale'da — TENGLIK", () => {
  const expected = new Set(periodPresets);

  for (const locale of LOCALES) {
    /*
     * ⛔ TO'PLAM TENGLIGI, «bormi?» EMAS: yetishmagan matnni ham,
     *   O'LIK kalitni ham AYNAN shu shakl ushlaydi.
     */
    assert.deepEqual(
      messageKeys(locale, ["reports", "preset"]),
      expected,
      `${locale}: \`reports.preset.*\` reyestrdan AJRALGAN`,
    );
  }
});

/* -------------------------------------------------------------------------- */
/* G-41(a) — UCH FARQ SINFI × 3 LOCALE (§10.5, §13.4)                         */
/* -------------------------------------------------------------------------- */

test("⛔ G-41 (08-UI-SPEC) (a): `DIFF_CLASSES` AYNAN 3 a'zo va `match` YO'Q", () => {
  assert.equal(
    diffClasses.length,
    3,
    `\`DIFF_CLASSES\` da ${diffClasses.length} a'zo (kutilgan 3): ${diffClasses}`,
  );

  /*
   * ⛔⛔ «MOS» BEZAK OLMAYDI VA SHUNING UCHUN SINF HAM OLMAYDI.
   *
   *   287 ta yashil belgi 13 ta farqni KO'MIB yuborardi — imzolanadigan
   *   varaqda ko'z FARQNI qidiradi, mos qatorlarni emas. Reyestrga
   *   `match` ni qo'shish `compare.diff.match` matnini tug'dirardi,
   *   matn esa komponentda ishlatilishni TALAB qilardi.
   */
  const decorated = diffClasses.filter((cls) =>
    ["match", "matched", "ok", "equal"].includes(cls),
  );
  assert.deepEqual(
    decorated,
    [],
    `⛔ «mos» sinfi reyestrga kirdi: ${decorated} — u bezak OLMAYDI (§13.4)`,
  );
});

test("⛔ G-41 (08-UI-SPEC) (a): `compare.diff.*` UCHALA locale'da — TENGLIK", () => {
  const expected = new Set(diffClasses.map(toCamel));

  for (const locale of LOCALES) {
    /*
     * ⛔ XATO XABARI LOCALE'NI NOMMA-NOM AYTADI: «kalit yetishmayapti»
     *   degan umumiy xabar uchala faylni qo'lda ochishga majburlardi.
     */
    assert.deepEqual(
      messageKeys(locale, ["compare", "diff"]),
      expected,
      `${locale}: \`compare.diff.*\` reyestrdan AJRALGAN — kutilgan ` +
        `{${[...expected].join(", ")}}`,
    );
  }
});

/* -------------------------------------------------------------------------- */
/* G-43(c) — TAQIQLANGAN COPY (§11, §14.1)                                    */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ UCH SINF, PER-LOCALE — ⛔ QUYI CHEGARA: ≥9 token.
 *
 * ⚠ PER-LOCALE VA BU MUHIM: `ru.json` MUSTAQIL tarjima fayli, lotin
 *   matnidan transliteratsiya hosilasi EMAS. Uni lotin tokeni bilan
 *   skanerlash MAZMUNIDAN QAT'I NAZAR har doim 0 qaytarardi — darvoza
 *   mavjud bo'lib ko'rinardi va HECH NIMANI o'lchamasdi (07 M-11 darsi).
 *
 * 1. ⛔ «Backup» — [M-13] `Backup` -> `Баcкуп` (ARALASH ALIFBO) va u
 *    overrides'da YO'Q. Yagona shakl — «Zaxira nusxa» va u katalogda
 *    ALLAQACHON bor.
 * 2. ⛔ «Jami farq» — uch farq sinfi HECH QACHON qo'shilmaydi (§10.5).
 * 3. ⛔ «Aniqlik ulushi» — u 07 §14.1 da CASE HIT-RATE ning nomi; bu
 *    ekranda esa «AI aniqligi» bor. Bir xil ibora ikki ekranda IKKI
 *    XIL miqdorni bildirardi.
 */
const FORBIDDEN_COPY = {
  "uz-Latn": ["backup", "jami farq", "umumiy farq", "aniqlik ulushi"],
  "uz-Cyrl": ["баcкуп", "баскуп", "жами фарқ", "умумий фарқ", "аниқлик улуши"],
  ru: ["общая разница", "итого разница", "суммарная разница", "доля точности"],
};

test("⛔ G-43 (08-UI-SPEC) (c): taqiq reyestri BO'SH EMAS (quyi chegara)", () => {
  const total = Object.values(FORBIDDEN_COPY).reduce(
    (sum, list) => sum + list.length,
    0,
  );

  assert.ok(
    total >= MIN_FORBIDDEN_COPY_TOKENS,
    `taqiq reyestrida atigi ${total} token (quyi chegara ` +
      `${MIN_FORBIDDEN_COPY_TOKENS}) — ro'yxat jimgina qisqargan`,
  );

  for (const locale of LOCALES) {
    assert.ok(
      Array.isArray(FORBIDDEN_COPY[locale]) &&
        FORBIDDEN_COPY[locale].length > 0,
      `${locale}: taqiq ro'yxati bo'sh — bu locale UMUMAN o'lchanmaydi`,
    );
  }
});

test("⛔ G-43 (08-UI-SPEC) (c): NAZORAT — detektor sun'iy ijobiy satrni USHLAYDI", () => {
  /*
   * Detektor sun'iy manbani ushlashi SHART — aks holda pastdagi bo'sh
   * natija «toza copy» emas, «ishlamayotgan skaner» degani bo'lardi.
   */
  const probe = "Backup yangilanmadi";
  const hit = FORBIDDEN_COPY["uz-Latn"].filter((token) =>
    probe.toLowerCase().includes(token),
  );

  assert.deepEqual(hit, ["backup"]);
});

test("⛔ G-43 (08-UI-SPEC) (c): `reports.*`/`compare.*` copy'da taqiq YO'Q", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const values = surfaceValues(locale).map((value) => value.toLowerCase());

    for (const token of FORBIDDEN_COPY[locale]) {
      for (const value of values) {
        if (value.includes(token)) {
          problems.push(`${locale}: «${token}» -> «${value}»`);
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ taqiqlangan copy hisobot yuzasiga kirdi:\n  " + problems.join("\n  "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-43(d) — ICU PLATSHOLDERLARI × 3 LOCALE (§8.6, §10.5)                     */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ MAXRAJ MATNDAN AJRALMAYDI.
 *
 * `rowsShown` usiz direktor ekrandagi 50 qatorni BUTUN DAVR deb
 * o'qirdi; `matched` usiz 13 qatorli varaq «bozorda 13 ta rasta bor»
 * bo'lib o'qilardi (07 G-32 darsi); `diffCounts` ning uch platsholderi
 * esa uch sanoqning ALOHIDA matn tugunida qolishini kafolatlaydi.
 */
const REQUIRED_PLACEHOLDERS = {
  "reports.rowsShown": ["shown", "total"],
  "reports.accuracyNotMeasured": ["n", "min"],
  "compare.matched": ["matched"],
  "compare.diffCounts": ["ledgerOver", "systemOver", "aiMismatch"],
};

test("⛔ G-43 (08-UI-SPEC) (d): to'rt kalit UCHALA locale'da ICU platsholderi bilan", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);

    for (const [key, args] of Object.entries(REQUIRED_PLACEHOLDERS)) {
      let node = messages;
      for (const segment of key.split(".")) node = node?.[segment];

      if (typeof node !== "string" || node.trim() === "") {
        problems.push(`${locale}.json: \`${key}\` YO'Q`);
        continue;
      }

      for (const arg of args) {
        if (!node.includes(`{${arg}}`)) {
          problems.push(`${locale}.json: \`${key}\` da \`{${arg}}\` YO'Q -> «${node}»`);
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ maxraj matndan AJRALDI — son platsholdersiz yozilsa u DOM'da " +
      "topilmaydi va imzolanadigan varaqda kontekstsiz qoladi:\n  " +
      problems.join("\n  "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-38(b) — `apiRequest` YAGONA YO'L (§0.2, §12.2)                           */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ YUKLAB OLISHNING TOKENSIZ SHAKLLARI — ⛔ QUYI CHEGARA: ≥5 token.
 *
 * =============================================================================
 * Access token XOTIRADA va SO'ROV SARLAVHASIDA ketadi [M-7]. Demak
 * quyidagilarning HAR BIRI brauzerni TOKENSIZ so'rovga majburlaydi va
 * javob 401 bo'ladi — brauzer esa 401 TANASINI `.xlsx` nomi bilan
 * diskka SAQLAYDI. Foydalanuvchi «fayl yuklandi» deb o'ylaydi, Excel
 * «fayl buzilgan» deydi va xato HECH QAYERDA ko'rinmaydi.
 *
 * ⛔ Ya'ni bu taqiq INTIZOM emas, MEXANIKA.
 * =============================================================================
 *
 * ⚠ `download=` — JSX atributining shakli (`download={true}` ham shu
 *   naqshga tushadi). Yalang'och `download` YOZILMAYDI: u `saveBlob`
 *   ni chaqiruvchi `downloadReport` funksiyasining O'Z nomini ushlab,
 *   darvozani birinchi kunidayoq yolg'on-qizil qilardi.
 */
const FORBIDDEN_SURFACE_TOKENS = [
  { token: "fetch(", why: "ikkinchi tarmoq yo'li — token va 401-refresh takrorlanardi" },
  { token: "download=", why: "`<a download>` — 401 tanasini .xlsx nomi bilan saqlardi" },
  { token: "window.open", why: "yangi oyna tokensiz ketadi" },
  { token: "location.href", why: "navigatsiya tokensiz ketadi" },
  { token: 'document.createElement("a")', why: "qo'lda qurilgan havola — saveBlob'ning ikkinchi nusxasi" },
];

/** Kodda uchragan taqiqlangan tokenlar. */
function surfaceHits(code) {
  return FORBIDDEN_SURFACE_TOKENS.filter(({ token }) =>
    code.includes(token),
  ).map(({ token }) => token);
}

test("⛔ G-38 (08-UI-SPEC) (b): so'rov moduli MAVJUD va skan BO'SH EMAS", () => {
  assert.ok(
    existsSync(REPORT_QUERIES),
    `${path.relative(SRC, REPORT_QUERIES)} YO'Q — modul qayta nomlangan ` +
      "bo'lsa bu darvoza JIMGINA bo'sh skan qilardi",
  );

  const scanned = [REPORT_QUERIES].filter((file) => existsSync(file));
  assert.ok(
    scanned.length >= MIN_SCANNED_QUERY_FILES,
    `atigi ${scanned.length} ta fayl skanerlandi (quyi chegara ` +
      `${MIN_SCANNED_QUERY_FILES})`,
  );
  assert.ok(
    FORBIDDEN_SURFACE_TOKENS.length >= MIN_SURFACE_TOKENS,
    `taqiq reyestrida atigi ${FORBIDDEN_SURFACE_TOKENS.length} token ` +
      `(quyi chegara ${MIN_SURFACE_TOKENS}) — ro'yxat jimgina qisqargan`,
  );
});

test("⛔ G-38 (08-UI-SPEC) (b): NAZORAT — detektor sun'iy ijobiy manbani USHLAYDI", () => {
  assert.deepEqual(surfaceHits('const r = await fetch("/api/v1/reports");'), [
    "fetch(",
  ]);
  assert.deepEqual(surfaceHits('<a href={url} download="x.xlsx">'), ["download="]);
  assert.deepEqual(surfaceHits("window.open(url);"), ["window.open"]);
});

test("⛔ G-38 (08-UI-SPEC) (b): ⛔ SALBIY NAZORAT — `apiFetch(` TAQIQ EMAS", () => {
  /*
   * ⛔⛔ ENG NOZIK BAND VA U REGISTRGA BOG'LIQ. `apiFetch(` ichida
   *   `Fetch(` BOSH harf bilan turadi, taqiq esa `fetch(` — ya'ni
   *   REGISTRGA SEZGIR solishtiruv ikkalasini AJRATADI.
   *
   *   Agar detektor bir kun `toLowerCase()` ga o'tkazilsa, u tiplangan
   *   va MUTLAQO QONUNIY `apiFetch()` chaqiruvlarini taqiq deb
   *   ko'rsatardi — darvoza yolg'on-qizil bo'lardi va keyingi ijrochi
   *   uni «shovqin» deb bo'shatardi. Bu assert o'sha o'zgarishni
   *   qizartiradi.
   */
  assert.deepEqual(surfaceHits('await apiFetch("/reports/revenue", { schema });'), []);
  assert.deepEqual(surfaceHits('await apiRequest(buildReportPath(kind, period));'), []);
});

test("⛔ G-38 (08-UI-SPEC) (b): `report-queries.ts` da `apiRequest(` BOR", () => {
  const code = stripComments(read(REPORT_QUERIES));

  assert.ok(
    code.includes("apiRequest("),
    "⛔ `apiRequest(` so'rov modulida YO'Q — eksport zanjiri uzilgan yoki " +
      "ikkinchi yo'lga ko'chirilgan (§12.2)",
  );
  assert.ok(
    code.includes("saveBlob("),
    "⛔ `saveBlob(` yo'q — blob diskka tushirilmayapti",
  );
});

test("⛔ G-38 (08-UI-SPEC) (b): so'rov modulida tokensiz yuklab olish yo'li YO'Q", () => {
  const code = stripComments(read(REPORT_QUERIES));
  const problems = surfaceHits(code).map((token) => {
    const why = FORBIDDEN_SURFACE_TOKENS.find((t) => t.token === token).why;
    return `${path.relative(SRC, REPORT_QUERIES)} -> \`${token}\` (${why})`;
  });

  assert.deepEqual(
    problems,
    [],
    "⛔ tokensiz yuklab olish yo'li tug'ildi (§0.2, M-7):\n  " +
      problems.join("\n  ") +
      "\n  Access token XOTIRADA va SARLAVHADA ketadi — bu yo'llar 401 " +
      "oladi va brauzer 401 TANASINI `.xlsx` nomi bilan diskka saqlaydi. " +
      "Nosozlik JIM bo'ladi: tugma ishlagandek ko'rinadi.",
  );
});

test("⛔ G-38 (08-UI-SPEC) (b): IZOH FILTRI shu faylda HAQIQATAN kerak (o'lchov)", () => {
  /*
   * ⛔ BU TEST DARVOZANING O'Z MEXANIZMINI O'LCHAYDI. `report-queries.ts`
   *   ning bosh izohi taqiqning O'ZINI tushuntiradi va unda `fetch(`,
   *   `window.open`, `location.href` MATN sifatida turibdi. Izoh filtri
   *   ishlamasa, yuqoridagi darvoza BUGUNGI TOZA KODDA qizarardi va
   *   keyingi ijrochi uni bo'shatardi.
   */
  const raw = read(REPORT_QUERIES);

  assert.ok(
    surfaceHits(raw).length > 0,
    "izohda taqiqlangan token qolmagan — bu testning farazi eskirgan",
  );
  assert.deepEqual(
    surfaceHits(stripComments(raw)),
    [],
    "izoh filtridan keyin token qolmasligi SHART",
  );
});

/* ========================================================================== */
/* HISOBOT KATALOGINING MANBA SKANI — G-38(a), G-41(b), G-42                 */
/* ========================================================================== */

/**
 * ⛔⛔ BU BLOKLAR 08-03 DA ATAYIN OCHIQ QOLDIRILGAN EDI (fayl boshidagi
 *     izoh) va ularning TETIGI o'sha yerda nomma-nom yozilgan: G-38(a)
 *     o'z quyi chegarasida ⛔ ≥6 skanerlangan fayl talab qiladi, 08-03
 *     kunida esa `src/components/reports/` katalogi UMUMAN yo'q edi.
 *
 * ⛔ Tetik BAJARILDI: 08-09 ikkita, 08-13 ikkita, 08-15 yana ikkita
 *    mahsulot faylini keltirdi — bugun katalogda AYNAN OLTITA fayl bor.
 *    Bloklar shu sababdan SHU REJADA (08-17) qo'shildi.
 */

/** Skanerlanadigan eng kam MAHSULOT fayli (bugun 6, §16.6 G-38(a)). */
const MIN_SCANNED_FILES = 6;

/** Tokensiz yuklab olish yo'llarining eng kam soni (G-38(a)). */
const MIN_DOWNLOAD_TOKENS = 6;

/** «Birlashtirilgan farq» nomlarining eng kam soni (G-41(b)). */
const MIN_COMBINED_NAMES = 10;

/** Shaxsiy maydon nomlarining eng kam soni (G-42(g)). */
const MIN_PERSONAL_NAMES = 8;

/**
 * `components/reports/**` — ⛔ REKURSIV va ⛔ TEST FAYLLARISIZ.
 *
 * ⚠ REKURSIV ATAYIN: bir kun `components/reports/compare/` ochilsa,
 *   yassi `readdirSync` uni JIMGINA tashlab ketardi va yangi fayllar
 *   butun skandan tashqarida qolardi.
 *
 * ⚠ TEST FAYLLARI CHIQARILADI: ular MAHSULOT emas va aynan taqiqlangan
 *   tokenlarni SUN'IY ijobiy sifatida yozadi (sabotaj o'lchovlari).
 *   Ularni skanga qo'shish darvozani DOIMIY yolg'on-qizil qilardi.
 */
function walkProductSources(dir) {
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkProductSources(full));
      continue;
    }
    if (!/\.tsx?$/u.test(entry.name)) continue;
    if (/\.test\.tsx?$/u.test(entry.name)) continue;
    out.push(full);
  }
  return out.sort();
}

/**
 * ⛔ IMPORT JUMLASINI BUTUNLAY OLIB TASHLAYDI — ⛔ `^import` QATORINI EMAS.
 *
 * =========================================================================
 * ⛔⛔ FARQ O'LCHANGAN VA U DARVOZANI BIRINCHI KUNIDAYOQ QIZARTIRARDI.
 *
 * `period-picker.tsx` (08-09) ⛔ KO'P QATORLI import yozadi:
 *
 *     import {
 *       businessDayIn,
 *       …
 *     } from "@/components/snapshots/day-picker";
 *
 * Ya'ni taqiqlangan yo'l tokeni importning ⛔ YOPUVCHI qatorida turadi
 * va u qator `import` bilan BOSHLANMAYDI. `^import` shaklidagi filtr
 * uni ⛔ UMUMAN ushlamaydi — G-42(d) esa o'sha tokenni 0 ga qulflaydi,
 * ya'ni darvoza ⛔ YOLG'ON-QIZIL bo'lardi va keyingi ijrochi uni
 * «shovqin» deb bo'shatardi (08-15 ning zimma bandi 2).
 *
 * ⛔ Shuning uchun naqsh BUTUN jumlani oladi: `import` dan boshlanib,
 *    qator OXIRIDAGI birinchi `;` da tugaydi (dangasa moslash).
 * =========================================================================
 */
function stripImports(code) {
  return code.replace(/^[ \t]*import\s[\s\S]*?;[ \t]*$/gmu, "");
}

const reportComponentFiles = walkProductSources(REPORT_COMPONENTS);

/** G-38(a) va G-41(b) maydoni: katalog + ⛔ yagona so'rov moduli. */
const reportScanFiles = [...reportComponentFiles, REPORT_QUERIES];

/** Fayl -> izohsiz manba. */
const componentSources = new Map(
  reportComponentFiles.map((file) => [file, stripComments(read(file))]),
);
const scanSources = new Map(
  reportScanFiles.map((file) => [file, stripComments(read(file))]),
);

/** Xato xabari uchun qisqa yo'l. */
function rel(file) {
  return path.relative(SRC, file).replace(/\\/gu, "/");
}

/**
 * NAZORAT testlari uchun SUN'IY manba.
 *
 * ⚠ Kalit `SRC` ICHIDA quriladi: `rel()` ni `src/` dan tashqaridagi yo'lga
 *   qo'llash disk ildizigacha `../` zanjirini berardi va nazoratning
 *   kutilmasi platformaga bog'liq bo'lib qolardi.
 */
function probe(name, code) {
  return new Map([[path.join(SRC, name), code]]);
}

/**
 * `sources` bo'yicha `tokens` ni izlaydi -> `["fayl -> `token`", …]`.
 *
 * ⚠ `transform` — ixtiyoriy ikkinchi filtr (masalan import jumlalarini
 *   olib tashlash). Standarti — o'zgartirishsiz.
 */
function tokenHits(sources, tokens, transform = (code) => code) {
  const problems = [];
  for (const [file, raw] of sources) {
    const code = transform(raw);
    for (const token of tokens) {
      if (code.includes(token)) problems.push(`${rel(file)} -> \`${token}\``);
    }
  }
  return problems;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — SKAN MAYDONINING O'ZI                                          */
/* -------------------------------------------------------------------------- */

test("QAMROV: `components/reports/**` da kamida 6 MAHSULOT fayli skanerlanadi", () => {
  /*
   * ⛔ BO'SH TO'PLAMDA «taqiqlangan token topilmadi» JIMGINA ROST bo'ladi.
   *   Katalog qayta nomlansa yoki fayllar ko'chirilsa quyidagi barcha
   *   darvozalar hech nimani o'lchamay yashil qaytardi.
   */
  assert.ok(
    reportComponentFiles.length >= MIN_SCANNED_FILES,
    `atigi ${reportComponentFiles.length} ta mahsulot fayli skanerlandi ` +
      `(quyi chegara ${MIN_SCANNED_FILES}): ${reportComponentFiles.map(rel)}`,
  );

  /* ⛔ Nomma-nom NAZORAT: yurgich haqiqatan SHU katalogni ko'ryaptimi. */
  const names = new Set(reportComponentFiles.map((file) => path.basename(file)));
  for (const expected of [
    "period-picker.tsx",
    "export-button.tsx",
    "revenue-report.tsx",
    "debtors-report.tsx",
    "anomaly-archive.tsx",
    "accuracy-block.tsx",
  ]) {
    assert.ok(names.has(expected), `\`${expected}\` skanga tushmadi`);
  }

  /* ⛔ Test fayllari MAHSULOT emas — ular skanda BO'LMASLIGI shart. */
  const leakedTests = [...names].filter((name) => name.includes(".test."));
  assert.deepEqual(leakedTests, [], `test fayli skanga kirdi: ${leakedTests}`);
});

test("IMPORT FILTRI: KO'P QATORLI jumlani oladi, kodni yutmaydi", () => {
  const multiline = [
    "import {",
    "  businessDayIn,",
    '} from "@/components/snapshots/day-picker";',
    'export const keep = "/snapshots/kept";',
  ].join("\n");

  const stripped = stripImports(multiline);

  assert.ok(
    !stripped.includes("@/components/snapshots/day-picker"),
    "ko'p qatorli import jumlasi OLIB TASHLANMADI — `^import` filtri sinfi",
  );
  assert.ok(
    stripped.includes('export const keep = "/snapshots/kept";'),
    "import filtri IMPORT BO'LMAGAN kodni yutib yubordi",
  );
});

test("⛔ IMPORT FILTRI shu katalogda HAQIQATAN kerak (o'lchov)", () => {
  /*
   * ⛔⛔ BU TEST DARVOZANING O'Z MEXANIZMINI O'LCHAYDI va u 08-15 ning
   *   zimma bandi 2 ning mexanik shakli. Filtrsiz G-42(d) BUGUNGI TOZA
   *   KODDA qizarardi (`period-picker.tsx` kadr katalogidan sof SANA
   *   yordamchilarini import qiladi), keyingi ijrochi esa darvozani
   *   «shovqin» deb bo'shatardi.
   *
   * ⚠ Faraz eskirsa (import olib tashlansa) bu assert QIZARADI va
   *   o'shanda filtrni saqlash sababi QAYTA baholanadi — jimgina
   *   qolib ketmaydi.
   */
  const withoutFilter = tokenHits(componentSources, ["/snapshots/"]);
  const withFilter = tokenHits(componentSources, ["/snapshots/"], stripImports);

  assert.ok(
    withoutFilter.length > 0,
    "import jumlasida taqiqlangan yo'l qolmagan — bu testning farazi eskirgan",
  );
  assert.deepEqual(
    withFilter,
    [],
    "import filtridan keyin yo'l tokeni qolmasligi SHART",
  );
});

/* -------------------------------------------------------------------------- */
/* G-38(a) — TOKENSIZ YUKLAB OLISH YO'LI YO'Q (§0.2, §12.2, M-7)              */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ QUYI CHEGARA: ≥6 token va ≥6 skanerlangan fayl.
 *
 * ⚠ Ro'yxat G-38(b) nikidan FARQ QILADI va bu ataylab: u yerda
 *   `fetch(` bor (so'rov modulida ikkinchi tarmoq yo'li), bu yerda esa
 *   `href={` (komponentda qo'lda qurilgan havola). Ikkalasini bitta
 *   ro'yxatga qo'shish `report-queries.ts` da `href={` ni ham
 *   taqiqlardi — u yerda muammo BOSHQA (§16.6 ikki bandni AJRATGAN).
 */
const FORBIDDEN_DOWNLOAD_TOKENS = [
  { token: "download=", why: "`<a download>` — 401 tanasini .xlsx nomi bilan saqlardi" },
  { token: "download}", why: "`download={true}` — yuqoridagining ikkinchi shakli" },
  { token: "window.open", why: "yangi oyna tokensiz ketadi" },
  { token: "location.href", why: "navigatsiya tokensiz ketadi" },
  { token: 'document.createElement("a")', why: "qo'lda qurilgan havola — saveBlob'ning nusxasi" },
  { token: "href={", why: "hisoblangan havola — yuklab olish yo'liga aylanishi mumkin" },
];

test("⛔ G-38 (08-UI-SPEC) (a): taqiq reyestri BO'SH EMAS (quyi chegara)", () => {
  assert.ok(
    FORBIDDEN_DOWNLOAD_TOKENS.length >= MIN_DOWNLOAD_TOKENS,
    `taqiq reyestrida atigi ${FORBIDDEN_DOWNLOAD_TOKENS.length} token ` +
      `(quyi chegara ${MIN_DOWNLOAD_TOKENS}) — ro'yxat jimgina qisqargan`,
  );
  assert.ok(
    scanSources.size >= MIN_SCANNED_FILES,
    `skan maydonida atigi ${scanSources.size} fayl`,
  );
});

test("⛔ G-38 (08-UI-SPEC) (a): NAZORAT — detektor sun'iy ijobiy manbani USHLAYDI", () => {
  const source = probe("probe.tsx", '<a href={url} download="x.xlsx">yuklash</a>');

  assert.deepEqual(
    tokenHits(source, FORBIDDEN_DOWNLOAD_TOKENS.map((t) => t.token)).sort(),
    ["probe.tsx -> `download=`", "probe.tsx -> `href={`"].sort(),
  );
});

test("⛔ G-38 (08-UI-SPEC) (a): hisobot katalogida tokensiz yuklab olish yo'li YO'Q", () => {
  const problems = tokenHits(
    scanSources,
    FORBIDDEN_DOWNLOAD_TOKENS.map((t) => t.token),
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ tokensiz yuklab olish yo'li tug'ildi (§0.2, M-7):\n  " +
      problems.join("\n  ") +
      "\n  Access token XOTIRADA va SARLAVHADA ketadi — bu yo'llar 401 " +
      "oladi va brauzer 401 TANASINI `.xlsx` nomi bilan diskka saqlaydi. " +
      "Nosozlik JIM bo'ladi: tugma ishlagandek ko'rinadi.\n" +
      "  ⚠ Dalil havolasi kerak bo'lsa — QO'SHNI katalogdagi `EvidenceLink` " +
      "(08-15 qarori 2), bu katalogda yangi havola YOZILMAYDI.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-41(b) — UCH FARQ SINFI HECH QACHON QO'SHILMAYDI (§10.5)                  */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ QUYI CHEGARA: ≥10 nom.
 *
 * Uch sinf uch TURLI harakat talab qiladi («pulni qidiring» /
 * «daftarni tuzating» / «detektorni tekshiring»). Bitta songa siqish
 * solishtiruvni ⛔ FOYDASIZ qilardi — 6-faza D-05 va 07 Pattern 4 ning
 * aynan sinfi.
 */
const FORBIDDEN_COMBINED_NAMES = [
  "total_diff",
  "totalDiff",
  "combined_diff",
  "combinedDiff",
  "total_variance",
  "totalVariance",
  "grand_total",
  "grandTotal",
  "diff_total",
  "diffTotal",
];

test("⛔ G-41 (08-UI-SPEC) (b): nomlar reyestri — TO'PLAM TENGLIGI va quyi chegara", () => {
  /*
   * ⛔ TENGLIK, «uzunligi yetarlimi?» EMAS: ro'yxatdan bitta nomni olib
   *   tashlab, o'rniga ikkinchi nusxa qo'shish uzunlikni SAQLARDI.
   */
  assert.deepEqual(
    new Set(FORBIDDEN_COMBINED_NAMES),
    new Set([
      "total_diff",
      "totalDiff",
      "combined_diff",
      "combinedDiff",
      "total_variance",
      "totalVariance",
      "grand_total",
      "grandTotal",
      "diff_total",
      "diffTotal",
    ]),
    "⛔ birlashtirilgan farq nomlari reyestri O'ZGARGAN",
  );
  assert.ok(
    FORBIDDEN_COMBINED_NAMES.length >= MIN_COMBINED_NAMES,
    `atigi ${FORBIDDEN_COMBINED_NAMES.length} nom (quyi chegara ` +
      `${MIN_COMBINED_NAMES})`,
  );
});

test("⛔ G-41 (08-UI-SPEC) (b): NAZORAT — detektor sun'iy ijobiy manbani USHLAYDI", () => {
  const source = probe("probe.ts", "const grandTotal = a + b;");

  assert.deepEqual(tokenHits(source, FORBIDDEN_COMBINED_NAMES), [
    "probe.ts -> `grandTotal`",
  ]);
});

test("⛔ G-41 (08-UI-SPEC) (b): hisobot katalogida birlashtirilgan farq YO'Q", () => {
  const problems = tokenHits(scanSources, FORBIDDEN_COMBINED_NAMES);

  assert.deepEqual(
    problems,
    [],
    "⛔ uch farq sinfini bitta songa siqadigan nom tug'ildi (§10.5):\n  " +
      problems.join("\n  "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-42(a) — AKSENT BYUDJETI VA YAGONA DESTRUKTIV AMAL (§13.3, §14.8)         */
/* -------------------------------------------------------------------------- */

/**
 * ⛔⛔ AKSENT VA DESTRUKTIV TUGMANING EGASI — BITTA FAYL VA U Y-3 NIKI.
 *
 * =========================================================================
 * §13.3 aksentni ⛔ TO'RT ELEMENTLI YOPIQ to'plam qilib yozgan va
 * to'rtinchisi — `[Daftarni yuklash]`, ya'ni Y-3 ning ⛔ YAGONA
 * yakunlovchi amali. §4.6 esa yagona dialogni (DL-6, daftarni
 * almashtirish tasdig'i) o'sha yuzaga biriktirgan. Ikkalasi ham
 * ⛔ `ledger-import.tsx` ning ichida tug'iladi (08-18).
 *
 * ⛔ SAHIFA BU TALABNI BAJARA OLMAYDI VA BU ⛔ O'LCHANGAN:
 *   1. §13.3 to'rtta `[Excel bo'lib yuklab olish]` tugmasini nomma-nom
 *      ⛔ AKSENTSIZ deb yozgan — sahifaga aksent qo'yish o'sha bandning
 *      bevosita buzilishi bo'lardi;
 *   2. ⛔ MEXANIK YARMI QAT'IY: `app/[locale]/(app)/reports/page.tsx`
 *      ⛔ `components/reports/**` skan maydonidan TASHQARIDA, ya'ni u
 *      yerdagi tugma bu darvozaga ⛔ UMUMAN KO'RINMASDI.
 *
 * ⛔ Shuning uchun assert ⛔ TOTAL FUNKSIYA bo'lib yozilgan — ikkala
 *    shoxda ham ANIQ da'vo bor, ya'ni «jim teshik» YO'Q:
 *
 *      egasi YO'Q  -> sanoq ⛔ AYNAN 0 (bugun);
 *      egasi BOR   -> sanoq ⛔ AYNAN 1 va u ⛔ FAQAT egasida.
 *
 *    Ya'ni darvoza 08-18 fayl kelgan zahoti ⛔ O'ZI qattiqlashadi va
 *    buni hech kim «yodda tutishi» shart emas. Bugun aksentni boshqa
 *    faylga qo'yish ham, ertaga egasiga QO'YMASLIK ham QIZARADI.
 * =========================================================================
 */
const ACCENT_OWNER = "ledger-import.tsx";

/** `variant="…"` ni CHIQARADIGAN JSX tegining nomi (eng yaqin ochuvchi `<`). */
function jsxOwnersOf(code, token) {
  const owners = [];
  let index = code.indexOf(token);

  while (index !== -1) {
    const before = code.slice(0, index);
    const open = before.lastIndexOf("<");
    const match = /^<\s*([A-Za-z][\w.]*)/u.exec(before.slice(open));
    owners.push(match === null ? "(noma'lum)" : match[1]);
    index = code.indexOf(token, index + token.length);
  }

  return owners;
}

/** `token` ni chiqaradigan fayllar va ularning sanog'i. */
function countByFile(sources, token) {
  const out = new Map();
  for (const [file, code] of sources) {
    const count = code.split(token).length - 1;
    if (count > 0) out.set(path.basename(file), count);
  }
  return out;
}

function totalOf(counts) {
  return [...counts.values()].reduce((sum, n) => sum + n, 0);
}

const accentOwnerPresent = reportComponentFiles.some(
  (file) => path.basename(file) === ACCENT_OWNER,
);

test('⛔ G-42 (08-UI-SPEC) (a): `variant="default"` — AYNAN BITTA va FAQAT egasida', () => {
  const counts = countByFile(componentSources, 'variant="default"');

  /*
   * ⛔ TO'PLAM TENGLIGI: qaysi FAYL aksent chiqarayotgani o'lchanadi.
   *   Sof sanoq «bittasi bor, lekin eksport tugmasida» holatini
   *   o'tkazib yuborardi — holbuki §13.3 bo'yicha aynan SHU eng qimmat
   *   xato bo'lardi.
   */
  assert.deepEqual(
    new Set(counts.keys()),
    accentOwnerPresent ? new Set([ACCENT_OWNER]) : new Set(),
    accentOwnerPresent
      ? `⛔ aksent \`${ACCENT_OWNER}\` dan TASHQARIDA (§13.3): ${[...counts.keys()]}`
      : "⛔ aksent egasi (`" +
          ACCENT_OWNER +
          "`) hali tug'ilmagan, ya'ni `variant=\"default\"` BO'LMASLIGI " +
          `shart: ${[...counts.keys()]}`,
  );

  /* ⛔ Byudjet: egasi kelganda ham AYNAN BITTA, ikkitasi emas. */
  assert.equal(
    totalOf(counts),
    accentOwnerPresent ? 1 : 0,
    "⛔ 10 % aksent byudjeti buzildi — to'rtta yuklab olish tugmasi TENG " +
      "og'irlikda (§13.3) va ularning birortasi aksent OLMAYDI",
  );
});

test('⛔ G-42 (08-UI-SPEC) (a): `variant="destructive"` — AYNAN BITTA va `ConfirmDialog` da', () => {
  const counts = countByFile(componentSources, 'variant="destructive"');

  assert.deepEqual(
    new Set(counts.keys()),
    accentOwnerPresent ? new Set([ACCENT_OWNER]) : new Set(),
    "⛔ destruktiv tugma noto'g'ri faylda (§14.8: hisobot O'CHIRILMAYDI, " +
      `daftar qatorlari TAHRIRLANMAYDI): ${[...counts.keys()]}`,
  );
  assert.equal(totalOf(counts), accentOwnerPresent ? 1 : 0);

  /*
   * ⛔ QAYSI TEGDA ekani ham o'lchanadi: `ConfirmDialog` dan tashqaridagi
   *   destruktiv tugma tasdiqsiz yakunlovchi amal bo'lardi (§14.8).
   */
  const owners = [...componentSources.values()].flatMap((code) =>
    jsxOwnersOf(code, 'variant="destructive"'),
  );
  assert.deepEqual(
    owners,
    accentOwnerPresent ? ["ConfirmDialog"] : [],
    `⛔ destruktiv variant \`ConfirmDialog\` dan tashqarida: ${owners}`,
  );
});

test("⛔ G-42 (08-UI-SPEC) (a): NAZORAT — teg egasi detektori ISHLAYDI", () => {
  /*
   * ⛔ SUN'IY MANBA `=>` NI ATAYIN O'Z ICHIGA OLADI: atribut ichidagi
   *   `>` belgisi `[^>]*` shaklidagi sodda naqshni sindirardi va
   *   detektor noto'g'ri teg nomini qaytarardi.
   */
  const probe =
    '<ConfirmDialog onConfirm={() => run()} variant="destructive" />\n' +
    '<Button variant="destructive" />';

  assert.deepEqual(jsxOwnersOf(probe, 'variant="destructive"'), [
    "ConfirmDialog",
    "Button",
  ]);
});

/* -------------------------------------------------------------------------- */
/* G-42(b)(c)(e) — KLIENT ARIFMETIKASI, NAVBAT FILTRI, BESHINCHI O'LCHAM      */
/* -------------------------------------------------------------------------- */

/** ⛔ D-03: klient HECH NIMA hisoblamaydi — server yig'indini beradi. */
const FORBIDDEN_ARITHMETIC = [
  "float(",
  "Decimal",
  ".toFixed(",
  "parseFloat(",
  ".reduce(",
];

/** ⛔ §9.1: `eval`/`train` filtri HECH QAYERDA qurilmaydi (D-14). */
const FORBIDDEN_QUEUE_TOKENS = [
  "queue_kind",
  "queueKind",
  "purpose",
  '"train"',
  '"eval"',
];

/** ⛔ §7.1: to'rt rol, beshinchi o'lcham QO'SHILMAYDI [M-15]. */
const FORBIDDEN_TYPE_SCALE = ["text-base", "text-xl", "text-3xl", "text-["];

test("⛔ G-42 (08-UI-SPEC) (b): klientda pul arifmetikasi YO'Q (D-03)", () => {
  const problems = tokenHits(componentSources, FORBIDDEN_ARITHMETIC);

  assert.deepEqual(
    problems,
    [],
    "⛔ klientdagi qayta hisob XATO bo'lib emas, ⛔ IKKINCHI JAVOB bo'lib " +
      "chiqadi (yaxlitlash, sahifalash, filtr — uchtasi ham ajratadi; " +
      "05-14 darsi):\n  " + problems.join("\n  "),
  );
});

test("⛔ G-42 (08-UI-SPEC) (c): `eval`/`train` filtri hisobot yuzasida YO'Q", () => {
  const problems = tokenHits(componentSources, FORBIDDEN_QUEUE_TOKENS);

  assert.deepEqual(
    problems,
    [],
    "⛔ navbat sinfini ajratadigan filtr 70/30 bo'linishining MA'NOSINI " +
      "yo'qotardi (D-14, §9.1) — bu MUZOKARASIZ:\n  " + problems.join("\n  "),
  );
});

test("⛔ G-42 (08-UI-SPEC) (e): beshinchi tipografik o'lcham YO'Q (§7.1)", () => {
  const problems = tokenHits(componentSources, FORBIDDEN_TYPE_SCALE);

  assert.deepEqual(
    problems,
    [],
    "⛔ [M-15] `text-base` (7) va `text-xl` (3) — MEROS deviatsiyalar va " +
      "ular hisobot yuzasida EMAS; 8-faza yangisini QO'SHMAYDI:\n  " +
      problems.join("\n  "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-42(d) — KADR CHEGARADAN CHIQMAYDI (07 D-03, §8.5)                        */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ EKSPORTGA RASM KIRMAYDI va ekranda ham kadr BAYTLARI yo'q — dalil
 *    ⛔ IDENTIFIKATOR yoki MAVJUD yuzaga havola bo'lib qoladi.
 *
 * ⚠⚠ `URL.createObjectURL` TAQIG'I ⛔ `saveBlob()` GA TEGMAYDI. U
 *    `lib/market-queries.ts` da yashaydi va bu skan maydonidan
 *    ⛔ TASHQARIDA. Bu LITERAL yozilishi shart (§16.6 talabi): aks holda
 *    keyingi ijrochi taqiqni «eksport ham buzilsin» deb o'qib, ishlaydigan
 *    yagona yuklab olish zanjirini SINDIRARDI.
 */
const FORBIDDEN_FRAME_TOKENS = [
  "<img",
  "next/image",
  "useEvidenceImageHref",
  "URL.createObjectURL",
  "/snapshots/",
];

test("⛔ G-42 (08-UI-SPEC) (d): kadr tokenlari YO'Q (import jumlasi ISTISNO)", () => {
  const problems = tokenHits(
    componentSources,
    FORBIDDEN_FRAME_TOKENS,
    stripImports,
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ dalil-kadr hisobot chegarasidan chiqdi (07 D-03, §8.5):\n  " +
      problems.join("\n  "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-42(f) — IKKINCHI ANIQLIK KOMPONENTI YOZILMAYDI (§9.2, M-11)              */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ TA'RIF izlanadi, ⛔ YALANG UCHRASH EMAS — va bu farq O'LCHANGAN.
 *
 * `accuracy-block.tsx` mavjud komponentni ⛔ IMPORT QILADI va uni JSX
 * bo'lib chizadi (`<ConfusionMatrix report={data} />`) — bu M-11 ning
 * bevosita TALABI. `/\b(confusion|matrix)\b/i` shaklidagi regeks import
 * yo'lidagi `confusion-matrix` ni ushlab, darvozani birinchi kunidayoq
 * ⛔ YOLG'ON-QIZIL qilardi (08-15 ning zimma bandi 3).
 *
 * ⛔ Shuning uchun IKKI mexanizm BIRGA: import jumlasi olib tashlanadi
 *    VA naqsh `function|class|interface|type|const|let|var` bilan
 *    boshlanadigan ⛔ TA'RIFNI izlaydi.
 */
const ACCURACY_DEFINITION =
  /\b(?:function|class|interface|type|const|let|var)\s+(confusion|matrix|wilson|percentView)\w*/giu;

test("⛔ G-42 (08-UI-SPEC) (f): aniqlik mantiqining TA'RIFI hisobot katalogida YO'Q", () => {
  const problems = [];

  for (const [file, raw] of componentSources) {
    for (const match of stripImports(raw).matchAll(ACCURACY_DEFINITION)) {
      problems.push(`${rel(file)} -> \`${match[0]}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ IKKINCHI aniqlik komponenti tug'ildi (§9.2, M-11) — ikki ekranda " +
      "IKKI XIL aniqlik ko'rsatilardi va ular bir kun JIMGINA ajralib " +
      "ketardi:\n  " + problems.join("\n  "),
  );
});

test("⛔ G-42 (08-UI-SPEC) (f): NAZORAT — ta'rif detektori import bilan JSX ni AJRATADI", () => {
  const definition = 'const matrixRows = [];\nfunction wilsonBound() {}';
  const legitimate =
    'import { ConfusionMatrix } from "@/components/occupancy/confusion-matrix";\n' +
    "export const Block = () => <ConfusionMatrix report={data} />;";

  assert.deepEqual(
    [...stripImports(definition).matchAll(ACCURACY_DEFINITION)].map((m) => m[0]),
    ["const matrixRows", "function wilsonBound"],
  );
  assert.deepEqual(
    [...stripImports(legitimate).matchAll(ACCURACY_DEFINITION)].map((m) => m[0]),
    [],
    "⛔ QONUNIY import + JSX chaqiruvi taqiq deb o'qildi — darvoza " +
      "yolg'on-qizil bo'lardi (M-11 ni buzardi)",
  );
});

/* -------------------------------------------------------------------------- */
/* G-42(g) — ⛔⛔ IKKI KATALOG, IKKI RO'YXAT (D-07 ↔ 07 G-36)                 */
/* -------------------------------------------------------------------------- */

/**
 * ⛔⛔ FAZANING ENG NOZIK DARVOZASI VA U IKKI TOMONGA HAM BUZILADI.
 *
 * =========================================================================
 * 7-fazaning ⛔ G-36 i `components/reconciliation/**` da `vendor_name`
 * ni ⛔ TAQIQLAYDI: u yerda ism KLIENTDA joinlanardi va ikkinchi so'rov
 * shaxsiy ma'lumot yuzasini kengaytirardi (C-10).
 *
 * ⛔ BU KATALOGDA QOIDA TESKARI (D-07, §5.5): «qarzdorlik ro'yxati»
 *    RECON-04 ning bevosita talabi va ism ⛔ SERVERDA joinlanadi.
 *
 *   • O'sha ro'yxatni BU KATALOGGA ko'chirish D-07 ni ⛔ BIRINCHI
 *     KUNIDAYOQ buzardi — qarzdorlik ro'yxati sotuvchi ismisiz
 *     buxgalter uchun MA'NOSIZ varaq bo'lardi;
 *   • Bu ro'yxatni O'SHA KATALOGGA ko'chirish esa 7-fazaning C-10
 *     himoyasini YUMSHATARDI.
 *
 * ⛔ IKKI KATALOG — IKKI RO'YXAT, va bu ⛔ ASSERT BILAN yozilgan:
 *    ro'yxatning O'ZI to'plam tengligi bilan qulflangan va `vendor_name`
 *    ning YO'QLIGI alohida o'lchanadi.
 *
 * ⚠ RO'YXAT TESTDA QAYTA YOZILGAN, mahsulotdan IMPORT QILINMAGAN
 *   (05-15 darsi): import darvozani o'zi tekshirayotgan qiymatga
 *   bog'lardi.
 * =========================================================================
 */
const FORBIDDEN_PERSONAL_NAMES = [
  "chat_id",
  "chatId",
  "telegram_user_id",
  "telegram_username",
  "balance",
  "phone",
  "full_name",
  "fullName",
];

/** ⛔ Bu katalogda QONUNIY (D-07) — taqiq ro'yxatida BO'LMASLIGI shart. */
const ALLOWED_VENDOR_NAMES = ["vendor_name", "vendorName"];

test("⛔ G-42 (08-UI-SPEC) (g): taqiq ro'yxati — TO'PLAM TENGLIGI va quyi chegara", () => {
  assert.deepEqual(
    new Set(FORBIDDEN_PERSONAL_NAMES),
    new Set([
      "chat_id",
      "chatId",
      "telegram_user_id",
      "telegram_username",
      "balance",
      "phone",
      "full_name",
      "fullName",
    ]),
    "⛔ shaxsiy maydon ro'yxati O'ZGARGAN",
  );
  assert.ok(
    FORBIDDEN_PERSONAL_NAMES.length >= MIN_PERSONAL_NAMES,
    `atigi ${FORBIDDEN_PERSONAL_NAMES.length} nom (quyi chegara ` +
      `${MIN_PERSONAL_NAMES})`,
  );
});

test("⛔ G-42 (08-UI-SPEC) (g): ⛔ `vendor_name` taqiq ro'yxatida YO'Q (D-07)", () => {
  /*
   * ⛔ TO'PLAM TENGLIGI bilan: kesishma AYNAN bo'sh. «Ro'yxatda bormi?»
   *   shaklidagi ikkita alohida assert bir kun uchinchi shaklni
   *   (`vendorFullName`) ko'rmasdi.
   */
  const leaked = FORBIDDEN_PERSONAL_NAMES.filter((name) =>
    ALLOWED_VENDOR_NAMES.includes(name),
  );

  assert.deepEqual(
    new Set(leaked),
    new Set(),
    "⛔ 7-fazaning G-36 ro'yxati BU KATALOGGA ko'chirildi — D-07 ning " +
      "bevosita buzilishi: qarzdorlik ro'yxati ismsiz MA'NOSIZ varaq " +
      `bo'lardi (§5.5, §8.3): ${leaked}`,
  );
});

test("⛔ G-42 (08-UI-SPEC) (g): ⛔ O'LCHOV — istisno HAQIQATAN yuk ko'taradi", () => {
  /*
   * ⛔⛔ BUSIZ YUQORIDAGI DA'VO BO'SH BO'LARDI. Agar `vendor_name` skan
   *   maydonida UMUMAN uchramasa, uni taqiq ro'yxatiga qo'shish HECH
   *   NIMANI o'zgartirmasdi — ya'ni «ikki katalog, ikki ro'yxat»
   *   qoidasi o'lchanmagan da'vo bo'lib qolardi.
   *
   * ⚠ Bu assert qizarsa (ism katalogdan yo'qolsa) — bu D-07 ning
   *   BUZILGANI degani: qarzdorlik ro'yxati sotuvchisiz qolgan.
   */
  const hits = tokenHits(componentSources, ALLOWED_VENDOR_NAMES);

  assert.ok(
    hits.length > 0,
    "⛔ `vendor_name` hisobot katalogida UMUMAN yo'q — D-07 buzilgan " +
      "(qarzdorlik ro'yxati SOTUVCHI kesimida bo'lishi shart, §8.3)",
  );
});

test("⛔ G-42 (08-UI-SPEC) (g): NAZORAT — detektor sun'iy ijobiy manbani USHLAYDI", () => {
  const source = probe(
    "probe.tsx",
    "const view = { phone: row.phone, chatId: row.chatId };",
  );

  assert.deepEqual(tokenHits(source, FORBIDDEN_PERSONAL_NAMES).sort(), [
    "probe.tsx -> `chatId`",
    "probe.tsx -> `phone`",
  ]);
});

test("⛔ G-42 (08-UI-SPEC) (g): hisobot katalogida shaxsiy maydon YO'Q", () => {
  const problems = tokenHits(componentSources, FORBIDDEN_PERSONAL_NAMES);

  assert.deepEqual(
    problems,
    [],
    "⛔ shaxsiy ma'lumot hisobot yuzasiga kirdi (T-08-76, D-09): aloqa " +
      "maydonlari va balans bu ekranda HECH QANDAY savolga javob " +
      "bermaydi, lekin ular `.xlsx` bo'lib TARQALARDI:\n  " +
      problems.join("\n  "),
  );
});
