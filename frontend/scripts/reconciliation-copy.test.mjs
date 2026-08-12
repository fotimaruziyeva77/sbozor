#!/usr/bin/env node
/**
 * NOMUVOFIQLIK YUZASINING MATN VA MANBA DARVOZASI — ⛔ TO'RT DARVOZA, BIR FAYL.
 *
 * =============================================================================
 * Bu fayl `07-UI-SPEC.md` ning to'rt bandini bitta MEXANIZMGA bog'laydi:
 *
 *   G7-3  (07-RESEARCH egaligida) — dalil-kadr bu yuzada BAYT bo'lib
 *                                   chizilmaydi; havola `/billing` ga boradi
 *   G-30  (07-UI-SPEC §16.6)      — ikki sinf HECH QACHON qo'shilmaydi
 *   G-35  (07-UI-SPEC §16.6)      — ikki xabar, ikki SIFATLOVCHI
 *   G-36  (07-UI-SPEC §16.6)      — taqiqlangan nomlar va aksent byudjeti
 *
 * ⛔ ID KETMA-KETLIGI BILAN YOZILADI: yangi frontend darvozalari `G-29`
 *   dan boshlanadi (oldingi ketma-ketlik `G-28` da tugagan); `G7-3` va
 *   `G7-9` esa 07-RESEARCH egaligida qoladi va bu fayl ularning FRONTEND
 *   yarmini aniqlashtiradi, YANGI ID bermaydi. ⚠ Yalang'och uch belgili
 *   ID yozilmaydi — u boshqa fazaning darvozasi.
 *
 * -----------------------------------------------------------------------
 * ⛔⛔ IKKI MUZOKARASIZ XOSSA (har darvozada)
 * -----------------------------------------------------------------------
 *   1. ⛔ HOSILA QAMROV — katalog `readdirSync` bilan REKURSIV o'qiladi
 *      va reyestrlardan ITERATSIYA qilinadi. Qo'lda yozilgan fayl
 *      ro'yxati bir kun ortda qolardi va buni hech nima aytmasdi.
 *
 *   2. ⛔ TO'PLAM TENGLIGI — inkor qiluvchi da'vo («bu nom yo'qmi?»)
 *      qo'shni yangi nomni KO'RMASDI. Tenglik esa HAR QANDAY yangi
 *      a'zoda qizaradi.
 *
 * ⛔ VA QUYI CHEGARA: skanerlanadigan fayl soni kamaysa darvoza QIZARADI.
 *   Bo'sh to'plamda «taqiqlangan token topilmadi» JIMGINA rost bo'ladi —
 *   bu kodbazada bir necha marta o'lchangan nosozlik sinfi.
 *
 * ⚠ IZOHLAR OLIB TASHLANADI va busiz darvoza BUGUN qizarardi: skanerlangan
 *   fayllarning izohlarida taqiqlarning O'ZI tushuntirilgan. `grep`
 *   asosidagi skan kodni izohdan ajratmaydi — shuning uchun `stripComments()`
 *   `bulk-action-surface.test.mjs` dan KO'CHIRILGAN (import EMAS: darvoza
 *   o'zi tekshirayotgan mexanizmga bog'lanib qolmasligi kerak).
 * =============================================================================
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

const RECON_DIR = path.join(SRC, "components", "reconciliation");
const RECON_QUERIES = path.join(SRC, "lib", "reconciliation-queries.ts");
const APP_SHELL = path.join(SRC, "components", "shell", "app-shell.tsx");
const RBAC = path.join(SRC, "lib", "rbac.ts");
const OUTBOX = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "jobs",
  "outbox.py",
);

const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];
const CODE_EXTENSIONS = [".ts", ".tsx"];
const TEST_FILE = /\.test\.tsx?$/;

/**
 * ⛔ QUYI CHEGARA — katalogda kamida shuncha MAHSULOT fayli.
 *
 * Bugun sakkizta bor. Chegara oltita: kutilgan yuzalar (kun tanlagichi,
 * ikki sinf, dalil havolasi, navbat, holat nishoni, aniqlik ulushi,
 * yetkazilganlik) shundan kam bo'lsa, skan JIMGINA torayган demakdir.
 */
const MIN_RECON_FILES = 6;

/* -------------------------------------------------------------------------- */
/* IZOH FILTRI — `bulk-action-surface.test.mjs:163-225` dan KO'CHIRILGAN      */
/* -------------------------------------------------------------------------- */

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * Satrlar ATAYIN saqlanadi: `className` qiymati, tarjima kaliti yoki
 * `href` ichidagi token ham brauzerga YETIB BORADI.
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

/* -------------------------------------------------------------------------- */
/* QAMROV — KATALOGDAN HOSILA                                                 */
/* -------------------------------------------------------------------------- */

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv). */
function listProductFiles(dir) {
  const found = [];
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

function read(file) {
  return readFileSync(file, "utf8");
}

function loadMessages(locale) {
  return JSON.parse(read(path.join(FRONTEND_ROOT, "messages", `${locale}.json`)));
}

/** `recon.*` ning barcha satr QIYMATLARI (ichma-ich obyektlar bilan). */
function reconValues(locale) {
  const found = [];
  (function walk(node) {
    for (const value of Object.values(node ?? {})) {
      if (typeof value === "string") found.push(value);
      else if (typeof value === "object" && value !== null) walk(value);
    }
  })(loadMessages(locale).recon);
  return found;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/* -------------------------------------------------------------------------- */

test("QAMROV: katalog MAVJUD va kamida olti MAHSULOT fayli bor", () => {
  assert.ok(
    existsSync(RECON_DIR),
    `${path.relative(REPO_ROOT, RECON_DIR)} YO'Q — katalog qayta nomlangan ` +
      "bo'lsa quyidagi darvozalarning HAMMASI jimgina bo'sh skan qilardi",
  );

  const files = listProductFiles(RECON_DIR);
  assert.ok(
    files.length >= MIN_RECON_FILES,
    `atigi ${files.length} ta mahsulot fayli skanerlandi (quyi chegara ` +
      `${MIN_RECON_FILES}) — qamrov jimgina qisqargan:\n  ` +
      files.map((f) => path.relative(SRC, f)).join("\n  "),
  );

  assert.ok(existsSync(RECON_QUERIES), "so'rov moduli YO'Q — G-36 ning yarmi ochiq");
});

test("QAMROV: skaner haqiqatan FAYL MAZMUNINI o'qiydi (nazorat)", () => {
  const code = SCANNED.map(({ code: c }) => c).join("\n");

  /* Nazorat: skanerlangan matnda mahsulot kodining izlari BOR. */
  assert.ok(code.includes("export"), "skanerlangan matnda `export` yo'q — skaner bo'sh");
  assert.ok(code.includes("data-recon-content"), "mazmun atributi skanga tushmadi");
});

test("IZOH FILTRI: kodni yutib yubormaydi va satr literalini saqlaydi", () => {
  const code = stripComments('const s = "/* izoh EMAS */";\nexport const keep = s;');

  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(code.includes("/* izoh EMAS */"), "satr literali izoh deb o'chirildi");
  assert.equal(stripComments("/* faqat izoh */\n").trim(), "");
});

/** Skanerlanadigan fayllar — izohsiz. Reyestr darvozalari shundan yuradi. */
const SCANNED = [...listProductFiles(RECON_DIR), RECON_QUERIES].map((file) => ({
  file: path.relative(SRC, file),
  code: stripComments(read(file)),
}));

/** Reyestrdagi har token uchun uni O'Z ICHIGA OLGAN fayllar. */
function hits(tokens) {
  const found = [];
  for (const token of tokens) {
    for (const { file, code } of SCANNED) {
      if (code.includes(token)) found.push(`${file} -> \`${token}\``);
    }
  }
  return found;
}

/* -------------------------------------------------------------------------- */
/* G7-3 — DALIL BAYT BO'LIB CHIZILMAYDI (07-RESEARCH egaligida)               */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ Kadrni sahifaga olib chiqishning BARCHA yo'llari (§16.3 b).
 *
 * ⚠ Ro'yxat ATAYIN QO'POL: nozikroq tahlil (JSX atributini ajratish,
 *   CSS qiymatini kuzatish) o'zi buzilishi mumkin bo'lgan kodga
 *   aylanardi. Bu katalog KICHIK va BIR MAQSADLI — unda bu tokenlarning
 *   qonuniy ishlatilishi YO'Q.
 */
const FRAME_TOKENS = [
  "<img",
  "next/image",
  "background-image",
  "backgroundImage",
  "useEvidenceImageHref",
  "URL.createObjectURL",
];

test("⛔ G7-3 (07-RESEARCH): dalil-kadrni chizishning BIRORTA yo'li yo'q", () => {
  assert.ok(FRAME_TOKENS.length >= 6, "taqiq reyestri qisqarib ketgan");

  assert.deepEqual(
    hits(FRAME_TOKENS),
    [],
    "⛔ dalil-kadr NOMUVOFIQLIK yuzasida BAYT bo'lib chizilmoqda:\n  " +
      hits(FRAME_TOKENS).join("\n  ") +
      "\n  Kadr `/billing` ning tafsilot dialogida, sessiya tokeni ostida " +
      "chiziladi. Bu yerda dalil — HAVOLA (D-03 + M-7).",
  );
});

test("⛔ G7-3 (07-RESEARCH): kadr marshrutining SATRI ham yo'q", () => {
  /*
   * ⛔ ENG QIMMAT BAND: marshrutga HECH QANDAY murojaat bo'lmasa, kadr
   *   marshrutlarining yopiq to'plami TEGILMAGAN qoladi. Ikkinchi kadr
   *   yuzasi o'sha to'plamni kengaytirish bosimini tug'dirardi.
   */
  assert.deepEqual(hits(["/snapshots/"]), []);
});

test("⛔ G7-3 (07-RESEARCH): dalil havolasi `/billing` GA boradi", () => {
  const link = SCANNED.find(({ file }) => file.endsWith("evidence-link.tsx"));

  assert.ok(link, "`evidence-link.tsx` topilmadi — dalil affordansi yo'qolgan");
  assert.match(
    link.code,
    /href=\{`\/billing\?day=\$\{[^}]+\}`\}/u,
    "dalil havolasining nishoni `/billing?day=` bo'lishi SHART: brauzer " +
      "o'zi ochadigan havola sessiya tokenini TASHIMAYDI va 401 olardi (M-7)",
  );
  assert.doesNotMatch(
    link.code,
    /_blank/u,
    "havola yangi oynada ochilmaydi: ilovaning yangi nusxasi auth holatini " +
      "qayta tiklaydi va foydalanuvchini login ekraniga tashlashi mumkin",
  );
});

/* -------------------------------------------------------------------------- */
/* G-30 — IKKI SINF HECH QACHON QO'SHILMAYDI (07-UI-SPEC §16.6)               */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ Birlashtirilgan jamining nomlari — ⛔ QUYI CHEGARA: ≥10 nom.
 *
 * Sinf A HOSILA (ertaga to'lov kelsa yo'qoladi), sinf B esa QATOR
 * (qolaveradi). Bitta songa qo'shish ikki xil UMR KO'RADIGAN narsani teng
 * qilardi; va sinf B da summa UMUMAN yo'q bo'lgani uchun yig'indi
 * ⛔ KAM KO'RSATILGAN YO'QOTISH bo'lardi.
 */
const COMBINED_TOTAL_NAMES = [
  "total_anomalies",
  "totalAnomalies",
  "combined_total",
  "combinedTotal",
  "total_discrepancies",
  "totalDiscrepancies",
  "grand_total",
  "grandTotal",
  "all_total",
  "allTotal",
  "overall_total",
  "overallTotal",
];

test("⛔ G-30 (07-UI-SPEC) (a): birlashtirilgan-jami NOMI kodda yo'q", () => {
  assert.ok(
    COMBINED_TOTAL_NAMES.length >= 10,
    `reyestrda atigi ${COMBINED_TOTAL_NAMES.length} nom (quyi chegara 10)`,
  );

  const problems = hits(COMBINED_TOTAL_NAMES);
  assert.deepEqual(
    problems,
    [],
    "⛔ ikki sinf bitta songa qo'shilmoqda (Pattern 4, §8.2):\n  " +
      problems.join("\n  "),
  );
});

test("⛔ G-30 (07-UI-SPEC) (a): NAZORAT — detektor sun'iy ijobiy nomni USHLAYDI", () => {
  /* Detektor sun'iy manbani ushlashi SHART — aks holda yuqoridagi bo'sh
   * natija «toza kod» emas, «ishlamayotgan skaner» degani bo'lardi. */
  const probe = "const grandTotal = unpaidCount + unregisteredCount;";
  const found = COMBINED_TOTAL_NAMES.filter((token) => probe.includes(token));

  assert.deepEqual(found, ["grandTotal"]);
});

/** ⛔ Uchala locale'da «birlashtirilgan jami» ning MATN shakli. */
const COMBINED_TOTAL_COPY = {
  "uz-Latn": ["jami nomuvofiqlik", "jami yo'qotish", "umumiy nomuvofiqlik"],
  "uz-Cyrl": ["жами номувофиқлик", "жами йўқотиш", "умумий номувофиқлик"],
  ru: ["всего расхождений", "общая потеря", "итого расхождений"],
};

test("⛔ G-30 (07-UI-SPEC) (c): `recon.*` copy'da birlashtirilgan jami yo'q", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const values = reconValues(locale).map((value) => value.toLowerCase());
    assert.ok(
      values.length >= 20,
      `${locale}: atigi ${values.length} ta \`recon.*\` qiymati skanerlandi ` +
        "— skan maydoni jimgina qisqargan",
    );

    for (const phrase of COMBINED_TOTAL_COPY[locale]) {
      for (const value of values) {
        if (value.includes(phrase)) {
          problems.push(`${locale}: «${phrase}» -> «${value}»`);
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ ikki sinf MATN darajasida qo'shilmoqda:\n  " + problems.join("\n  "),
  );
});

test("⛔ G-30 (07-UI-SPEC): ekran matnida «case» so'zi YO'Q (M-8)", () => {
  /*
   * ⛔ `transliterate("Case …")` lotin akronimini kirill o'zagi bilan
   *   ARALASHTIRIB yuboradi va `i18n:check` ni qizartiradi. Kodda va
   *   bazada nom O'Z JOYIDA qoladi; ekranda — «nomuvofiqlik».
   */
  const problems = [];

  for (const locale of LOCALES) {
    for (const value of reconValues(locale)) {
      if (/\bcase\b|кейс/iu.test(value)) problems.push(`${locale}: «${value}»`);
    }
  }

  assert.deepEqual(problems, [], "⛔ «case» so'zi ekran matniga kirdi:\n  " + problems.join("\n  "));
});

/* -------------------------------------------------------------------------- */
/* G-35 — IKKI XABAR, IKKI SIFATLOVCHI (07-UI-SPEC §16.6)                     */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ YOPIQ LUG'AT — aynan ikki a'zo (§12.2).
 *
 * ⛔ VA U TESTDA QAYTA YOZILADI, mahsulot kodidan IMPORT QILINMAYDI:
 *   darvoza o'zi tekshirayotgan qiymatni tekshirilayotgan manbadan olsa,
 *   ikkalasi BIRGA o'zgarganda JIMGINA yashil qolardi.
 */
const QUALIFIER_VOCAB = ["expected", "recorded"];

/** ⛔ Har dayjest matnida AYNAN BITTA sifatlovchi (§12.3). */
const QUALIFIER_EXPECTATION = {
  evening: ["expected"],
  morning: ["recorded"],
};

/** `outbox.py` dagi `NOM: { "locale": { "kalit": "matn" } }` jadvali. */
function readPythonLocaleTable(source, name) {
  const start = source.indexOf(`${name}: Final[dict[str, dict[str, str]]] = {`);
  assert.ok(start >= 0, `\`${name}\` topilmadi — parser sinigan`);
  const body = source.slice(start, source.indexOf("\n}", start));

  const table = {};
  for (const block of body.matchAll(
    /Locale\.([A-Z_]+)\.value:\s*\{([\s\S]*?)\n\s{4}\}/gu,
  )) {
    const locale = { UZ_LATN: "uz-Latn", UZ_CYRL: "uz-Cyrl", RU: "ru" }[block[1]];
    if (locale === undefined) continue;
    /*
     * ⚠ KALIT IKKI SHAKLDA KELADI va ikkalasi ham o'qilishi SHART:
     *   `"header": "…"`          — satr literali (yorliq jadvallari);
     *   `QUALIFIER_EXPECTED: "…"` — KONSTANTA (lug'at jadvali).
     * Faqat birinchisini o'qigan parser lug'atni JIMGINA bo'sh deb
     * qaytarardi va quyidagi to'plam tengliklari HECH NIMANI
     * tekshirmasdi — aynan shu «bo'sh skan» sinfi.
     */
    table[locale] = Object.fromEntries(
      [
        ...block[2].matchAll(
          /(?:"([a-z_]+)"|QUALIFIER_([A-Z]+)):\s*"([^"]*)"/gu,
        ),
      ].map((m) => [m[1] ?? m[2].toLowerCase(), m[3]]),
    );
  }
  return table;
}

const outboxSource = read(OUTBOX);
const qualifierWords = readPythonLocaleTable(outboxSource, "_QUALIFIER_WORDS");
const morningText = readPythonLocaleTable(outboxSource, "_MORNING_TEXT");
const eveningText = readPythonLocaleTable(outboxSource, "_EVENING_TEXT");

test("⛔ G-35 (07-UI-SPEC): lug'at AYNAN IKKI a'zo va uchala locale'da (nazorat)", () => {
  for (const locale of LOCALES) {
    assert.deepEqual(
      new Set(Object.keys(qualifierWords[locale] ?? {})),
      new Set(QUALIFIER_VOCAB),
      `${locale}: sifatlovchi lug'ati ikki a'zoli bo'lishi SHART`,
    );
    for (const key of QUALIFIER_VOCAB) {
      assert.ok(
        (qualifierWords[locale][key] ?? "").length > 3,
        `${locale}.${key} bo'sh — quyidagi to'plam tengligi JIMGINA rost bo'lardi`,
      );
    }
  }
});

test("⛔ G-35 (07-UI-SPEC): veb va bot AYNAN BIR SO'ZNI ishlatadi (D-30)", () => {
  /*
   * ⛔ FRONTEND YARMI SHU. Bot matni serverda quriladi, veb esa o'z
   *   katalogidan o'qiydi — ikkalasi AJRALIB KETSA, direktor Telegramda
   *   bir so'zni, ekranda boshqasini ko'rardi va «bu ikki xil hisobotmi?»
   *   degan savol AYNAN §12.1 dagi ishonchsizlikni tug'dirardi.
   */
  const problems = [];

  for (const locale of LOCALES) {
    const web = loadMessages(locale).recon?.qualifier ?? {};
    for (const key of QUALIFIER_VOCAB) {
      if (web[key] !== qualifierWords[locale][key]) {
        problems.push(
          `${locale}.${key}: veb «${web[key]}» ↔ bot «${qualifierWords[locale][key]}»`,
        );
      }
    }
  }

  assert.deepEqual(problems, [], "atama veb va bot orasida AJRALIB KETGAN:\n  " + problems.join("\n  "));
});

/**
 * Har dayjest QAYSI sifatlovchini QO'YADI — ⛔ RENDER KODIDAN HOSILA.
 *
 * ⛔ MAPPING QO'LDA YOZILMAYDI: `_evening_text()` / `_morning_text()` ning
 *   `.format(qualifier=_QUALIFIER_WORDS[locale][QUALIFIER_…])` chaqiruvi
 *   O'QILADI. Qo'lda yozilgan xarita kod bilan ajralib ketsa, darvoza
 *   O'ZINING taxminini tasdiqlab yashil qolardi.
 */
function readDigestQualifier(source, functionName) {
  const start = source.indexOf(`def ${functionName}(`);
  assert.ok(start >= 0, `\`${functionName}\` topilmadi — parser sinigan`);
  const body = source.slice(start, source.indexOf("\ndef ", start + 1));

  const used = [
    ...body.matchAll(/_QUALIFIER_WORDS\[locale\]\[QUALIFIER_([A-Z]+)\]/gu),
  ].map((m) => m[1].toLowerCase());

  return [...new Set(used)];
}

test("⛔ G-35 (07-UI-SPEC): har dayjest AYNAN BITTA sifatlovchini QO'YADI", () => {
  /*
   * ⛔ NEGA TO'PLAM TENGLIGI: oddiy «kutilayotgan bormi?» tekshiruvi
   *   kechki xabarga «yozilgan» HAM qo'shilganda YASHIL qolardi — va
   *   aynan o'sha aralashuv direktorni chalkashtiradi.
   */
  const used = {
    evening: readDigestQualifier(outboxSource, "_digest_evening_text"),
    morning: readDigestQualifier(outboxSource, "_digest_morning_text"),
  };

  for (const digest of Object.keys(QUALIFIER_EXPECTATION)) {
    assert.deepEqual(
      new Set(used[digest]),
      new Set(QUALIFIER_EXPECTATION[digest]),
      `${digest} dayjesti {${used[digest]}} sifatlovchisini qo'yyapti ` +
        `(kutilgan {${QUALIFIER_EXPECTATION[digest]}}) — ikkalasining ` +
        "aralashuvi direktorni AYNAN §12.1 dagi ssenariyda chalkashtiradi",
    );
  }
});

test("⛔ G-35 (07-UI-SPEC): sifatlovchi RAQAM BILAN BIR JUMLADA (§12.2)", () => {
  /*
   * ⛔ Sifatlovchi ALOHIDA sarlavhada qolsa, Telegram bildirishnomasining
   *   QISQARTIRILGAN ko'rinishida u KESILIB qoladi va foydalanuvchi
   *   FAQAT RAQAMNI ko'radi — ya'ni butun kontrakt jimgina yo'qoladi.
   *
   * ⛔ Va ikkinchi sifatlovchi matnga QOTIB YOZILMAGAN: qator faqat
   *   platsholderni oladi va u to'ldirilgandan keyin lug'atning IKKINCHI
   *   so'zi matnda UCHRAMASLIGI shart.
   */
  const texts = { evening: eveningText, morning: morningText };
  const lineKey = { evening: "expected", morning: "charged" };
  const problems = [];

  for (const [digest, table] of Object.entries(texts)) {
    for (const locale of LOCALES) {
      const line = table[locale]?.[lineKey[digest]];
      assert.ok(line, `${digest}/${locale}: sifatlovchili qator topilmadi`);

      assert.ok(
        line.includes("{qualifier}"),
        `${digest}/${locale}: sifatlovchi qatorda YO'Q — «${line}»`,
      );

      const chosen = QUALIFIER_EXPECTATION[digest][0];
      const rendered = line.replace("{qualifier}", qualifierWords[locale][chosen]);

      const found = QUALIFIER_VOCAB.filter((key) =>
        rendered.includes(qualifierWords[locale][key]),
      );

      if (found.length !== 1 || found[0] !== chosen) {
        problems.push(
          `${digest}/${locale}: topilgan {${found}} ≠ kutilgan {${chosen}} — «${rendered}»`,
        );
      }
    }
  }

  assert.deepEqual(problems, [], "⛔ ikki sifatlovchi ARALASHDI:\n  " + problems.join("\n  "));
});

/* -------------------------------------------------------------------------- */
/* G-36 — TAQIQLANGAN NOMLAR VA AKSENT BYUDJETI (07-UI-SPEC §16.6)            */
/* -------------------------------------------------------------------------- */

/**
 * ⛔ Taqiqlangan nomlar — ⛔ QUYI CHEGARA: ≥16 nom.
 *
 * Uch mustaqil sabab bitta reyestrda:
 *   * Telegram identifikatori — odamni TASHQI tizimda aniqlaydi va
 *     mavjud shaxsiy-ma'lumot darvozasi uni USHLAMAYDI (u reyestrda
 *     yo'q). Bo'shliq AYNAN SHU YERDA yopiladi;
 *   * saqlangan hosila (balans, nisbat) — ikkinchi haqiqat manbai;
 *   * xom istisno matni — Telegram istisnosi bot TOKENINI tashiydi;
 *   * shaxsiy maydon — moliyaviy javob ism qaytarmaydi.
 */
const FORBIDDEN_NAMES = [
  "chat_id",
  "chatId",
  "telegram_user_id",
  "telegramUserId",
  "telegram_username",
  "balance",
  "balance_soum",
  "hit_rate",
  "hitRate",
  "last_error",
  "lastError",
  "vendor_name",
  "vendorName",
  "phone",
  "full_name",
  "fullName",
];

test("⛔ G-36 (07-UI-SPEC) (a): taqiqlangan nomlarning BIRORTASI yo'q", () => {
  assert.ok(
    FORBIDDEN_NAMES.length >= 16,
    `reyestrda atigi ${FORBIDDEN_NAMES.length} nom (quyi chegara 16)`,
  );

  const problems = hits(FORBIDDEN_NAMES);
  assert.deepEqual(
    problems,
    [],
    "⛔ nomuvofiqlik yuzasiga taqiqlangan nom kirdi:\n  " +
      problems.join("\n  ") +
      "\n  Ism MAVJUD, AUDIT QILINGAN reestr marshrutidan olinadi va u shu " +
      "katalogdan TASHQARIDA o'qiladi (`lib/vendor-labels.ts`).",
  );
});

test("⛔ G-36 (07-UI-SPEC) (a): NAZORAT — detektor sun'iy ijobiy nomni USHLAYDI", () => {
  const probe = "const chatId = user.chat_id;";
  const found = FORBIDDEN_NAMES.filter((token) => probe.includes(token));

  assert.deepEqual(new Set(found), new Set(["chat_id", "chatId"]));
});

test("⛔ G-36 (07-UI-SPEC) (b): kasrli pul arifmetikasi yo'q (D-07)", () => {
  const problems = hits(["float(", "Decimal", ".toFixed(", "parseFloat("]);

  assert.deepEqual(
    problems,
    [],
    "⛔ pul BIGINT so'm ↔ butun son bo'lib qoladi; kasrli tip kunlik " +
      "agregatlarda drift beradi va u AYNAN shu mahsulot oldini oladigan " +
      "nizoga olib borardi:\n  " + problems.join("\n  "),
  );
});

test("⛔ G-36 (07-UI-SPEC) (c): aksent tugma byudjeti — DL-5 dan HOSILA", () => {
  /*
   * ⛔⛔ KUTILGAN SON HOSILA, QO'LDA YOZILGAN EMAS — VA BU ATAYIN.
   *
   * Dizayn kontrakti aksent fonli tugmani FAZADA AYNAN BIR JOYGA
   * beradi: tafsilot dialogidagi yakuniy `[Holatni saqlash]`. O'sha
   * dialog esa keyingi rejaning ishi (bu reja YOZUV yuzasini UMUMAN
   * qurmaydi).
   *
   * Shuning uchun kutilgan son dialog faylining MAVJUDLIGIDAN
   * hisoblanadi:
   *   * dialog YO'Q  -> aksent tugma ham ⛔ 0 bo'lishi SHART. Bugungi
   *     ro'yxat yuzasida aksent tugma paydo bo'lsa, u har qatorda
   *     takrorlanib 10% chegarasini buzardi;
   *   * dialog BOR   -> aksent tugma ⛔ AYNAN 1.
   *
   * ⛔ Ikkala holatda ham da'vo ANIQ SON bilan — «ko'pi bilan bitta»
   *   emas. Yumshoq da'vo dialog kelgan kuni tugmaning UMUMAN
   *   yozilmaganini o'tkazib yuborardi.
   */
  const hasDetailDialog = SCANNED.some(({ file }) =>
    file.endsWith("case-detail-dialog.tsx"),
  );
  const expected = hasDetailDialog ? 1 : 0;

  const count = SCANNED.reduce(
    (sum, { code }) => sum + (code.match(/variant="default"/gu) ?? []).length,
    0,
  );

  assert.equal(
    count,
    expected,
    `aksent fonli tugma ${count} marta ishlatilgan (kutilgan ${expected}; ` +
      `tafsilot dialogi ${hasDetailDialog ? "BOR" : "hali YO'Q"}).\n` +
      "  Aksent — fokus halqasi, faol maydon chegarasi, joriy mobil nav " +
      "elementi va DL-5 ning yakuniy amali bilan CHEKLANGAN (§13.3).",
  );
});

test("⛔ G-36 (07-UI-SPEC) (d): destruktiv variant 0 marta (§14.8)", () => {
  /*
   * ⛔ Bu fazada QAYTARIB BO'LMAYDIGAN amal YO'Q: holat o'zgarishi
   *   append-only va ORQAGA QAYTARILADI; qator o'chirilmaydi; xabar
   *   bekor qilinmaydi. Destruktiv variant «bu amalni qaytarib
   *   bo'lmaydi» deb YOLG'ON gapirardi.
   */
  const problems = hits(['variant="destructive"']);

  assert.deepEqual(problems, [], problems.join("\n  "));
});

/* -------------------------------------------------------------------------- */
/* NAVIGATSIYA — M-5 NING MEXANIK SHAKLI                                      */
/* -------------------------------------------------------------------------- */

test("⛔ NAV: reyestr AYNAN 16 yozuv va yangi huquq QO'SHILMAGAN", () => {
  const shell = stripComments(read(APP_SHELL));
  const block = shell.slice(
    shell.indexOf("const NAV_ITEMS"),
    shell.indexOf("\n];", shell.indexOf("const NAV_ITEMS")),
  );

  const entries = [...block.matchAll(/labelKey:\s*"([a-zA-Z]+)"/gu)].map((m) => m[1]);

  assert.equal(entries.length, 16, `NAV_ITEMS da ${entries.length} yozuv (kutilgan 16)`);
  assert.ok(entries.includes("reconciliation"), "«Nomuvofiqliklar» yozuvi yo'q");

  /* ⛔ `/billing` DAN KEYIN: nomuvofiqlik — patta hisobining NATIJASI. */
  assert.ok(
    entries.indexOf("reconciliation") === entries.indexOf("billing") + 1,
    "«Nomuvofiqliklar» `/billing` dan bevosita keyin turishi SHART",
  );
});

test("⛔ NAV: KASSIR PANELI O'ZGARMAYDI — aynan ikki yozuv (M-5)", () => {
  /*
   * ⛔ 6-fazaning kassir kontrakti: `/dashboard` + `/collect`, overflow
   *   NOL. Yangi bo'lim `report_view` ostida va u kassirda YO'Q, ya'ni
   *   panel o'zgarmaydi. Bu da'vo IKKALA faylni MATN sifatida o'qiydi —
   *   `rbac.ts` ↔ `app-shell.tsx` juftligi ajralib ketmasin.
   */
  const shell = stripComments(read(APP_SHELL));
  const block = shell.slice(
    shell.indexOf("const NAV_ITEMS"),
    shell.indexOf("\n];", shell.indexOf("const NAV_ITEMS")),
  );

  const permissions = [
    ...block.matchAll(/permission:\s*(null|"([a-z_]+)")/gu),
  ].map((m) => m[2] ?? null);

  const rbac = stripComments(read(RBAC));
  const cashierRow = /cashier:\s*\[([^\]]*)\]/u.exec(rbac);
  assert.ok(cashierRow, "`rbac.ts` da kassir qatori topilmadi");
  const cashierPermissions = [...cashierRow[1].matchAll(/"([a-z_]+)"/gu)].map((m) => m[1]);

  const visible = permissions.filter(
    (permission) => permission === null || cashierPermissions.includes(permission),
  );

  assert.equal(
    visible.length,
    2,
    `kassir ${visible.length} yozuv ko'radi (kutilgan 2 — O'ZGARMAGAN). ` +
      `Kassir huquqlari: ${cashierPermissions.join(", ")}`,
  );
});

test("⛔ ID KONVENSIYASI: yalang'och boshqa-faza ID si yozilmagan (§16.1)", () => {
  const source = read(path.join(FRONTEND_ROOT, "scripts", "reconciliation-copy.test.mjs"));

  /*
   * ⛔ Bu faylning O'ZI tekshiriladi: ID manba bilan yoziladi.
   *
   * ⚠⚠ NAQSH BO'LAKLARDAN QURILADI va bu ATAYIN: taqiqlangan ID ni
   *   regeks literali sifatida yozish faylni O'Z DARVOZASIGA qarshi
   *   qo'yardi — skan o'z qo'riqchisini aybdor deb ko'rsatardi. Bu
   *   kodbazada bir necha marta o'lchangan sinf va u shu yerda ham
   *   TAKRORLANDI (birinchi yugurishda darvoza aynan shundan qizardi).
   */
  const barePriorPhaseId = new RegExp(`\\bG${"-"}3\\b`, "gu");

  assert.equal(
    (source.match(barePriorPhaseId) ?? []).length,
    0,
    "yalang'och oldingi-faza ID si yozilgan — u BOSHQA fazaning darvozasi " +
      "va o'quvchini noto'g'ri hujjatga yuborardi",
  );
  assert.ok(source.includes("G-30 (07-UI-SPEC)"), "ID manba bilan yozilishi SHART");
  assert.ok(source.includes("G7-3 (07-RESEARCH)"), "G7-3 egaligi bilan yozilishi SHART");
});
