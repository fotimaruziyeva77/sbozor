#!/usr/bin/env node
/**
 * HISOBOT YUZASINING REYESTR, MATN VA SO'ROV DARVOZASI (08-UI-SPEC §16.6).
 *
 * =============================================================================
 * Bu fayl 08-UI-SPEC ning uch bandini bitta MEXANIZMGA bog'laydi:
 *
 *   G-38(b) — `lib/report-queries.ts` da `apiRequest` YAGONA yo'l;
 *             yuklab olishning tokensiz shakllari NOLGA qulflanadi
 *   G-41(a) — uch farq sinfi × 3 locale, to'plam tengligi bilan
 *   G-43    — yopiq reyestrlar (`REPORT_KINDS`, `PERIOD_PRESETS`) × 3
 *             locale, taqiqlangan copy va ICU platsholderlari
 *
 * ⛔ ID KETMA-KETLIGI BILAN YOZILADI: 08-UI-SPEC ning yangi darvozalari
 *   `G-37` dan boshlanadi [M-14]. Yalang'och `G-3`/`G-4` YOZILMAYDI — u
 *   boshqa fazaning darvozasi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ BU BOSQICHDA FAQAT MANBASI MAVJUD BLOKLAR YOZILADI.
 * -----------------------------------------------------------------------
 * `components/reports/**` ni skanerlaydigan bloklar — G-38(a), G-41(b)
 * va G-42 — ⛔ 08-15 da SHU FAYLGA QO'SHILADI. Sabab MEXANIK va u
 * o'lchandi: G-38(a) o'z quyi chegarasida ⛔ ≥6 skanerlangan fayl talab
 * qiladi, bugun esa `src/components/reports/` katalogi UMUMAN YO'Q.
 *
 *   • Chegarani BUGUN pasaytirish (masalan ≥1 ga) darvozani ⛔ DOIMIY
 *     bo'shatardi: 08-15 katalogni to'ldirgach ham hech kim uni
 *     qaytarib ko'tarmasdi va skan «bo'sh to'plamda yashil» holatiga
 *     tushardi — bu kodbazada bir necha marta o'lchangan nosozlik sinfi.
 *   • Chegarani BUGUN yozib qoldirish esa uni ⛔ YOLG'ON-QIZIL qilardi:
 *     `npm run gate:fast` har commitda yiqilardi va keyingi ijrochi
 *     blokni «shovqin» deb O'CHIRARDI.
 *
 * ⛔ Shuning uchun uchinchi yo'l tanlandi: blok BUGUN YOZILMAYDI va
 *    uning egasi hamda tetigi SHU IZOHDA nomlanadi. Katalog tug'ilgan
 *    reja — 08-15 — o'sha bloklarni chegarasi bilan BIRGA qo'shadi.
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
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

const API_TYPES = path.join(SRC, "lib", "api-types.ts");
const REPORT_QUERIES = path.join(SRC, "lib", "report-queries.ts");

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
