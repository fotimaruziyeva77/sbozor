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
const BACKEND_SCHEMAS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "schemas.py",
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
