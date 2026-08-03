#!/usr/bin/env node
/**
 * Backend KODLARI -> frontend ko'zgusi -> tarjima kaliti zanjiri.
 *
 * NEGA KERAK: uch ro'yxat ham til chegarasi bilan ajralgan va kompilyator
 * ularni solishtira olmaydi. Backend yangi kod qo'shsa-yu ko'zgu
 * yangilanmasa, foydalanuvchi "Kutilmagan xato yuz berdi" ni ko'radi va
 * NIMA qilish kerakligini bilmaydi. Bu xavfsizlik teshigi emas, lekin
 * aynan shu kodlar mahsulotning eng ko'p uchraydigan rad javoblari (band
 * raqam, o'tgan sana, qoplanuvchi davr, chala usta, buzuq import qatori).
 *
 * `i18n:check` bu sinfni USHLAY OLMAYDI: u uchala faylning bir-biriga
 * mosligini tekshiradi, ro'yxatning TO'LIQLIGINI emas — kalit uchala tilda
 * ham yo'q bo'lsa, parity baribir yashil.
 *
 * Qamralgan uch ro'yxat:
 *   * `MARKET_ERROR_CODES`      -> `ERROR_CODES` + `marketErrorMessageKey`
 *   * `BlockingItem.code`       -> `wizard.blocking.*`
 *   * `ImportIssue.code`        -> `import.errors.*`
 *
 * Oxirgi ikkitasi MA'LUMOTDAN keladigan kalitlar (kod ichida yozilmaydi),
 * ya'ni ular aynan `audit.actions.*` bilan bir xil sinfda — o'sha yerdagi
 * darvoza naqshi shu yerda takrorlanadi.
 *
 * 3-FAZA (G-1 va G-2) — TO'RTINCHI ro'yxat va u BOSHQA SINFDAN:
 *   * `NVR_ERROR_CODES`  -> `lib/nvr-errors.ts` -> `cameras.errorCause.*`
 *                           VA `cameras.errorFix.*`
 *
 * Farqi shundaki, bu yerda har kod uchun IKKITA matn talab qilinadi.
 * D-02 aytadi: «xato hech qachon quruq "ulanmadi" bo'lmaydi — sababi VA
 * tuzatish yo'li ko'rsatiladi». Qoidaning mexanik shakli aynan shu:
 * `errorCause.{kod}` bor-u `errorFix.{kod}` yo'q bo'lsa test yiqiladi.
 * Usiz D-02 hujjatdagi niyat bo'lib qolardi va birinchi shoshilinch
 * PR'da jimgina buzilardi.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

const API_TYPES = path.join(FRONTEND_ROOT, "src", "lib", "api-types.ts");
const MARKET_ERRORS = path.join(FRONTEND_ROOT, "src", "lib", "market-errors.ts");
const NVR_ERRORS = path.join(FRONTEND_ROOT, "src", "lib", "nvr-errors.ts");
const BACKEND_SCHEMAS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "schemas.py",
);
const BACKEND_ISAPI_ERRORS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "isapi",
  "errors.py",
);

function read(file) {
  return readFileSync(file, "utf8");
}

function readTsStringArray(source, name) {
  const match = new RegExp(`export const ${name}\\s*=\\s*\\[([^\\]]*)\\]`, "u").exec(
    source,
  );
  assert.ok(match, `${name} TypeScript faylida topilmadi`);
  return [...match[1].matchAll(/"([^"]+)"/gu)].map((item) => item[1]);
}

/**
 * `MARKET_ERROR_CODES` frozenset'idagi kodlar.
 *
 * IZOH QATORLARI OLDIN TASHLANADI: blok ichidagi izohlarda qo'shtirnoqli
 * o'zbekcha matn bor va uni kod deb o'qish testni yolg'on qizartirardi.
 */
function readPythonFrozenset(source, name) {
  const start = source.indexOf(`${name}: Final[frozenset[str]] = frozenset(`);
  assert.ok(start !== -1, `${name} backend faylida topilmadi`);

  const rest = source.slice(start);
  const end = rest.indexOf("\n)");
  assert.ok(end !== -1, `${name} bloki yopilmagan`);

  return rest
    .slice(0, end)
    .split("\n")
    .filter((line) => !line.trim().startsWith("#"))
    .map((line) => /^\s*"([a-z_]+)",\s*$/u.exec(line))
    .filter(Boolean)
    .map((match) => match[1]);
}

/**
 * `NAME: Final[tuple[str, ...]] = ( ... )` ichidagi kodlar.
 *
 * `readPythonFrozenset` bilan bir xil naqsh, LEKIN alohida funksiya:
 * `NVR_ERROR_CODES` ATAYIN `tuple` (tartib ma'noli — guruhlar izohlar
 * bilan mos keladi), `MARKET_ERROR_CODES` esa `frozenset`. Bitta
 * "universal" parser ikkala e'lonni ham yumshoq o'qib, biri
 * o'zgarganda jimgina bo'sh ro'yxat qaytarardi.
 *
 * IZOH QATORLARI OLDIN TASHLANADI: blok ichidagi izohlarda qo'shtirnoqli
 * o'zbekcha matn bor va uni kod deb o'qish testni yolg'on qizartirardi.
 */
function readPythonTuple(source, name) {
  const start = source.indexOf(`${name}: Final[tuple[str, ...]] = (`);
  assert.ok(start !== -1, `${name} backend faylida topilmadi`);

  const rest = source.slice(start);
  const end = rest.indexOf("\n)");
  assert.ok(end !== -1, `${name} bloki yopilmagan`);

  return rest
    .slice(0, end)
    .split("\n")
    .filter((line) => !line.trim().startsWith("#"))
    .map((line) => /^\s*"([a-z_]+)",\s*$/u.exec(line))
    .filter(Boolean)
    .map((match) => match[1]);
}

/** `case "kod": return "namespace.kalit";` juftliklari. */
function readSwitchMap(source) {
  return new Map(
    [...source.matchAll(/case "([a-z_]+)":\s*\n\s*return "([^"]+)";/gu)].map(
      (item) => [item[1], item[2]],
    ),
  );
}

function loadMessages(locale) {
  return JSON.parse(
    readFileSync(path.join(FRONTEND_ROOT, "messages", `${locale}.json`), "utf8"),
  );
}

/** `"a.b.c"` kalitini ichma-ich obyektdan oladi. */
function lookup(tree, dottedKey) {
  return dottedKey
    .split(".")
    .reduce((node, part) => (node == null ? undefined : node[part]), tree);
}

/* -------------------------------------------------------------------------- */

const backendCodes = readPythonFrozenset(
  read(BACKEND_SCHEMAS),
  "MARKET_ERROR_CODES",
);

test("backend ro'yxati bo'sh emas (parser haqiqatan ishlayapti)", () => {
  // Nazorat: parser sinsa qolgan ikkala test ham JIMGINA yashil bo'lardi,
  // chunki bo'sh ro'yxat bo'yicha aylanish hech nimani tekshirmaydi.
  assert.ok(
    backendCodes.length >= 20,
    `MARKET_ERROR_CODES dan atigi ${backendCodes.length} kod o'qildi`,
  );
});

test("ERROR_CODES backend `MARKET_ERROR_CODES` ni to'liq qamraydi", () => {
  const mirrored = new Set(readTsStringArray(read(API_TYPES), "ERROR_CODES"));

  const missing = backendCodes.filter((code) => !mirrored.has(code));
  assert.deepEqual(
    missing,
    [],
    `api-types.ts::ERROR_CODES da yetishmaydi: ${missing.join(", ")}`,
  );
});

test("har bir backend kodi `marketErrorMessageKey` da xaritalangan", () => {
  const mapped = readSwitchMap(read(MARKET_ERRORS));

  const missing = backendCodes.filter((code) => !mapped.has(code));
  assert.deepEqual(
    missing,
    [],
    `market-errors.ts da \`case\` yo'q: ${missing.join(", ")}`,
  );
});

test("xaritalangan har bir kalit UCHALA tilda mavjud", () => {
  const mapped = readSwitchMap(read(MARKET_ERRORS));

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    for (const [code, key] of mapped) {
      assert.equal(
        typeof lookup(messages, key),
        "string",
        `${locale}.json da "${key}" yo'q (kod: ${code})`,
      );
    }
  }
});

/* ---------------------------------------------------------------------------
 * MA'LUMOTDAN keladigan kalitlar: ustaning to'siqlari va import xatolari.
 *
 * Ularni komponent `t('wizard.blocking.' + item.code)` shaklida quradi, ya'ni
 * kalit KOD ichida umuman yozilmaydi va noto'g'ri nom hech qayerda
 * ko'rinmaydi — ekranda tarjimasiz texnik identifikator paydo bo'lguncha.
 * ------------------------------------------------------------------------- */

const MARKETS_ROUTER = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "api",
  "v1",
  "markets.py",
);
const IMPORT_VALIDATOR = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "import_validator.py",
);

/** Backend'da `code="..."` shaklida yoziladigan qiymatlar. */
function readCodeLiterals(source) {
  return [...new Set([...source.matchAll(/code="([a-z_]+)"/gu)].map((m) => m[1]))];
}

/** `ImportIssue(...)` konstruktorining IKKINCHI pozitsion argumenti. */
function readImportIssueCodes(source) {
  return [
    ...new Set(
      [...source.matchAll(/ImportIssue\([^)]*?"([a-z_]+)"/gsu)].map((m) => m[1]),
    ),
  ];
}

test("wizard.blocking.* backend `BlockingItem.code` bilan BIR-BIRGA mos", () => {
  const codes = readCodeLiterals(read(MARKETS_ROUTER));
  assert.ok(codes.length >= 6, `atigi ${codes.length} blocking kod o'qildi`);

  for (const locale of LOCALES) {
    const labels = loadMessages(locale).wizard?.blocking ?? {};
    assert.deepEqual(
      Object.keys(labels).sort(),
      [...codes].sort(),
      `${locale}.json da wizard.blocking ro'yxati backend bilan mos emas`,
    );
  }
});

test("import.errors.* backend `ImportIssue.code` bilan BIR-BIRGA mos", () => {
  const codes = readImportIssueCodes(read(IMPORT_VALIDATOR));
  assert.ok(codes.length >= 10, `atigi ${codes.length} import kodi o'qildi`);

  for (const locale of LOCALES) {
    const labels = loadMessages(locale).import?.errors ?? {};
    assert.deepEqual(
      Object.keys(labels).sort(),
      [...codes].sort(),
      `${locale}.json da import.errors ro'yxati backend bilan mos emas`,
    );
  }
});

/* ---------------------------------------------------------------------------
 * G-1 va G-2 — NVR XATO TAKSONOMIYASI (3-faza).
 *
 * Zanjir uch bo'g'inli va har bo'g'in BOSHQA TILDA yozilgan:
 *
 *   errors.py::NVR_ERROR_CODES   (Python, reyestr)
 *        -> lib/nvr-errors.ts    (TypeScript, ko'zgu + tone/retry qarori)
 *        -> messages/*.json      (JSON, uch tildagi SABAB va TUZATISH)
 *
 * Kompilyator bu bo'g'inlarni solishtira olmaydi va `i18n:check` ham
 * ushlamaydi: u uchala faylning bir-biriga mosligini tekshiradi, TO'PLAM
 * TO'LIQLIGINI emas — kalit uchala tilda ham yo'q bo'lsa parity baribir
 * yashil.
 * ------------------------------------------------------------------------ */

const nvrCodes = readPythonTuple(read(BACKEND_ISAPI_ERRORS), "NVR_ERROR_CODES");

test("NVR reyestri bo'sh emas (parser haqiqatan ishlayapti)", () => {
  // Nazorat: `readPythonTuple` sinsa (masalan e'lon `list` ga
  // aylantirilsa) quyidagi ikkala darvoza ham JIMGINA yashil bo'lardi.
  assert.equal(
    nvrCodes.length,
    12,
    `NVR_ERROR_CODES dan ${nvrCodes.length} kod o'qildi, kutilgan 12`,
  );
});

test("G-2: har backend NVR kodi `lib/nvr-errors.ts` da mavjud", () => {
  const source = read(NVR_ERRORS);
  const mirrored = new Set(
    [...source.matchAll(/^\s{2}"?([a-z_]+)"?:\s*\{\s*tone:/gmu)].map(
      (match) => match[1],
    ),
  );

  assert.ok(
    mirrored.size >= 12,
    `nvr-errors.ts dan atigi ${mirrored.size} yozuv o'qildi — parser sinigan bo'lishi mumkin`,
  );

  const missing = nvrCodes.filter((code) => !mirrored.has(code));
  assert.deepEqual(
    missing,
    [],
    `lib/nvr-errors.ts da yozuv yo'q: ${missing.join(", ")}. ` +
      "Kod backendда bor, frontendda esa u `errors.generic` ga tushadi va " +
      "admin NIMA qilishni bilmaydi (D-02).",
  );

  // Teskari yo'nalish ham muhim: ko'zguda ORTIQCHA kod bo'lsa, u hech
  // qachon kelmaydigan xato uchun matn va qoida saqlab yurardi.
  const extra = [...mirrored].filter((code) => !nvrCodes.includes(code));
  assert.deepEqual(
    extra,
    [],
    `lib/nvr-errors.ts da backendда YO'Q kod bor: ${extra.join(", ")}`,
  );
});

test("G-1: har kod uchun SABAB va TUZATISH matni UCHALA tilda bor (D-02)", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const cameras = loadMessages(locale).cameras ?? {};
    const causes = cameras.errorCause ?? {};
    const fixes = cameras.errorFix ?? {};

    for (const code of nvrCodes) {
      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(`${locale}.json: cameras.errorCause.${code} YO'Q`);
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(`${locale}.json: cameras.errorFix.${code} YO'Q`);
      }
    }

    // Teskari yo'nalish: matn bor, kod yo'q — o'lik kalit.
    for (const code of Object.keys(causes)) {
      if (!nvrCodes.includes(code)) {
        problems.push(
          `${locale}.json: cameras.errorCause.${code} backend reyestrida YO'Q`,
        );
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — sabab va tuzatish JUFT bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});
