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
const CAPTURE_ERRORS = path.join(FRONTEND_ROOT, "src", "lib", "capture-errors.ts");
const BACKEND_CAPTURE_ERRORS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "capture_errors.py",
);
const ZONE_ERRORS = path.join(FRONTEND_ROOT, "src", "lib", "zone-errors.ts");
const BACKEND_OCCUPANCY_ERRORS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "occupancy_errors.py",
);
const BILLING_ERRORS = path.join(
  FRONTEND_ROOT,
  "src",
  "lib",
  "billing-errors.ts",
);
const BACKEND_BILLING_ERRORS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "billing_errors.py",
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

/* ---------------------------------------------------------------------------
 * G-5 — 4-FAZA: DARVOZA IKKI NAMESPACE USTIDA ISHLAYDI.
 *
 * 3-fazada zanjir bitta reyestrdan (`NVR_ERROR_CODES`) boshlanardi.
 * 4-fazada IKKINCHI reyestr qo'shiladi (`snapshots.errorCause.*`,
 * 04-UI-SPEC §11.8 ning o'n bitta kodi) va u BOSHQA manbaga tayanadi:
 * kadr olish xatolari NVR ning ISAPI kodlari EMAS.
 *
 * ⚠ ⛔ `actor` USTUNI — 4-FAZANING YANGI TALABI (§10.5).
 *   Har xato uchun «BUNI KIM TUZATADI?» degan savolga javob bo'lishi
 *   shart: `admin` (bozor ma'muriyati), `platform` (platforma jamoasi)
 *   yoki `none` (hech kim — bu holat o'z-o'zidan tiklanadi). Usiz admin
 *   sababni va tuzatishni O'QIYDI, lekin bu ISH O'ZINIKIMI yoki
 *   qo'ng'iroq qilish kerakmi — BILMAYDI.
 *
 * ⚠ QUYI CHEGARA SHARTLI. `snapshots` copy'si `04-08…04-10` da keladi.
 *   Hozir u yo'q va test O'TADI — lekin SABABNI CHOP ETIB. Jimgina
 *   o'tish «darvoza bor» degan yolg'on da'voni qoldirardi, qattiq
 *   chegara esa bugundan qizil bo'lib, keyingi ijrochini uni «chetlab
 *   o'tishga» majbur qilardi.
 * ------------------------------------------------------------------------ */

/** Xato reyestri bo'lgan namespace'lar — 3-fazada bitta, 4-fazada ikkita. */
const ERROR_NAMESPACES = ["cameras", "snapshots"];

/** §11.8 — kadr olish xatolarining o'n bitta kodi. */
const MIN_SNAPSHOT_ERROR_CODES = 11;

/** §10.5 — `actor` ustunining AYNAN uchta qiymati. */
const SNAPSHOT_ACTORS = ["admin", "none", "platform"];

function snapshotCauses(locale) {
  return loadMessages(locale).snapshots?.errorCause ?? {};
}

function snapshotsCopyMissing() {
  return LOCALES.every((locale) => Object.keys(snapshotCauses(locale)).length === 0);
}

test("G-5: darvoza IKKALA xato namespace'ini biladi (nazorat)", () => {
  /*
   * Bu assert arzon, lekin u aynan W0-F7 bilan bir xil sinfdagi
   * xavfni yopadi: ro'yxat bitta namespace bilan qolib ketsa, ikkinchisi
   * hech qachon tekshirilmasdi va HECH BIR test qizarmasdi — «jim
   * qamrovsizlik».
   */
  assert.deepEqual(ERROR_NAMESPACES, ["cameras", "snapshots"]);
});

test("G-5: har `snapshots.errorCause.{kod}` uchun `errorFix.{kod}` UCHALA tilda bor", () => {
  if (snapshotsCopyMissing()) {
    console.log(
      "[G-5] `snapshots.errorCause.*` hali uchala tilda ham yo'q (copy 04-08…04-10 da " +
        `keladi) — darvoza kodlar qo'shilishi bilan >= ${MIN_SNAPSHOT_ERROR_CODES} ` +
        "kodni va sabab↔tuzatish juftligini TALAB qiladi.",
    );
    return;
  }

  const problems = [];
  for (const locale of LOCALES) {
    const snapshots = loadMessages(locale).snapshots ?? {};
    const causes = snapshots.errorCause ?? {};
    const fixes = snapshots.errorFix ?? {};
    const codes = Object.keys(causes);

    assert.ok(
      codes.length >= MIN_SNAPSHOT_ERROR_CODES,
      `${locale}.json: snapshots.errorCause da atigi ${codes.length} kod bor ` +
        `(kutilgan >= ${MIN_SNAPSHOT_ERROR_CODES}, 04-UI-SPEC §11.8)`,
    );

    for (const code of codes) {
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(`${locale}.json: snapshots.errorFix.${code} YO'Q`);
      }
    }
    // Teskari yo'nalish: tuzatish bor, sabab yo'q — o'lik kalit.
    for (const code of Object.keys(fixes)) {
      if (!(code in causes)) {
        problems.push(`${locale}.json: snapshots.errorCause.${code} YO'Q (tuzatish bor)`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — sabab va tuzatish JUFT bo'lishi SHART:\n  " + problems.join("\n  "),
  );
});

/* ---------------------------------------------------------------------------
 * ⛔ G-5 NING BACKEND LANGARI — 04-10 da QO'SHILDI.
 *
 * Yuqoridagi ikki test `Object.keys(causes)` ga, ya'ni MATN KATALOGINING
 * O'ZIGA tayanadi. Bu to'plamning ICHKI izchilligini o'lchaydi, lekin
 * TO'LIQLIGINI emas: backend o'n ikkinchi kodni qo'shsa-yu, uchala
 * tilda ham matn yozilmasa — sabab↔tuzatish parity BUZILMAYDI va
 * `>= 11` sharti ham o'tadi. Ya'ni darvoza YASHIL qolardi, admin esa
 * yangi xato uchun «Kutilmagan xato» ni ko'rardi (§S-5 sinfi).
 *
 * Aynan shu sinf 04-09 da HAQIQATAN ro'y berdi: olti yangi
 * `MARKET_ERROR_CODES` kodi qo'shildi, `ERROR_CODES` ko'zgusi esa
 * unutildi. U yerda darvoza ushladi, chunki `MARKET_ERROR_CODES`
 * uchun langar BOR edi. `capture_*` reyestrida u YO'Q edi.
 *
 * Zanjir to'rt bo'g'inli va har bo'g'in boshqa tilda:
 *
 *   capture_errors.py::CAPTURE_ERROR_META   (Python — kod + AKTOR)
 *     -> lib/api-types.ts::CAPTURE_ERROR_CODES  (TypeScript — reyestr)
 *     -> lib/capture-errors.ts::CAPTURE_ERROR_META (TypeScript — tone + aktor)
 *     -> messages/*.json                      (JSON — sabab, tuzatish, aktor)
 *
 * ⚠ AKTOR HAM SOLISHTIRILADI, faqat kodlar emas: `actor` xato matnining
 *   UCHINCHI qatori (§10.5) va u ikki tomonda mustaqil yozilgan. Backend
 *   `platform` deb, frontend `admin` deb hisoblasa admin soatlab NVR
 *   sozlamalarini titkilardi — kod nomi esa ikkalasida ham bir xil
 *   bo'lgani uchun hech qanday darvoza qizarmasdi.
 * ------------------------------------------------------------------------ */

/** `NAME: Final[str] = "kod"` konstantalari -> `{NAME: kod}`. */
function readPythonStrConstants(source) {
  return new Map(
    [...source.matchAll(/^([A-Z_0-9]+): Final\[str\] = "([a-z_]+)"/gmu)].map(
      (match) => [match[1], match[2]],
    ),
  );
}

/**
 * `CaptureErrorMeta(NAME, ..., "actor")` qatorlari -> `{kod: aktor}`.
 *
 * ⚠ Konstruktor POZITSION chaqiriladi va `actor` — OXIRGI argument.
 *   Shuning uchun naqsh oxirgi qo'shtirnoqli qiymatni oladi; ikkinchi
 *   qo'shtirnoqli argument bu chaqiruvda umuman yo'q (qolganlari
 *   `True`/`False`).
 */
function readCaptureActors(source, constants) {
  const out = new Map();
  for (const match of source.matchAll(
    /CaptureErrorMeta\(\s*([A-Z_0-9]+),[^)]*"([a-z]+)"\s*\)/gu,
  )) {
    const code = constants.get(match[1]);
    if (code !== undefined) out.set(code, match[2]);
  }
  return out;
}

/** `kod: { tone: "...", actor: "..." },` — `capture-errors.ts` ning jadvali. */
function readTsCaptureMeta(source) {
  return new Map(
    [
      ...source.matchAll(
        /^\s{2}([a-z_]+):\s*\{\s*tone:\s*"([a-z]+)",\s*actor:\s*"([a-z]+)"\s*\}/gmu,
      ),
    ].map((match) => [match[1], { tone: match[2], actor: match[3] }]),
  );
}

const backendCaptureActors = readCaptureActors(
  read(BACKEND_CAPTURE_ERRORS),
  readPythonStrConstants(read(BACKEND_CAPTURE_ERRORS)),
);

test("G-5: kadr olish reyestri o'qildi va AYNAN o'n bitta kod (nazorat)", () => {
  /*
   * Nazorat: parser sinsa (masalan `CaptureErrorMeta` kalit-so'zli
   * chaqiruvga o'tsa) quyidagi uchala darvoza ham JIMGINA yashil
   * bo'lardi — bo'sh to'plam bo'yicha aylanish hech nimani tekshirmaydi.
   */
  assert.equal(
    backendCaptureActors.size,
    MIN_SNAPSHOT_ERROR_CODES,
    `capture_errors.py dan ${backendCaptureActors.size} kod o'qildi, kutilgan ` +
      `${MIN_SNAPSHOT_ERROR_CODES} (04-UI-SPEC §11.8)`,
  );
});

test("G-5: `api-types.ts::CAPTURE_ERROR_CODES` backend reyestrining TO'LIQ ko'zgusi", () => {
  const mirrored = readTsStringArray(read(API_TYPES), "CAPTURE_ERROR_CODES");
  const backend = [...backendCaptureActors.keys()];

  assert.deepEqual(
    backend.filter((code) => !mirrored.includes(code)),
    [],
    "api-types.ts::CAPTURE_ERROR_CODES da yetishmaydi — kod backendда bor, " +
      "frontendда esa u `errors.generic` ga tushadi va admin NIMA qilishni bilmaydi (D-02)",
  );
  // Teskari yo'nalish: ko'zguda ORTIQCHA kod — hech qachon kelmaydigan
  // xato uchun matn va qoida saqlab yurish.
  assert.deepEqual(
    mirrored.filter((code) => !backendCaptureActors.has(code)),
    [],
    "api-types.ts::CAPTURE_ERROR_CODES da backendда YO'Q kod bor",
  );
});

test("G-5: `capture-errors.ts` har kodga tone BERADI va AKTOR backend bilan MOS", () => {
  const meta = readTsCaptureMeta(read(CAPTURE_ERRORS));

  assert.ok(
    meta.size >= MIN_SNAPSHOT_ERROR_CODES,
    `capture-errors.ts dan atigi ${meta.size} yozuv o'qildi — parser sinigan bo'lishi mumkin`,
  );

  const problems = [];
  for (const [code, actor] of backendCaptureActors) {
    const view = meta.get(code);
    if (view === undefined) {
      problems.push(`capture-errors.ts: ${code} uchun yozuv YO'Q`);
      continue;
    }
    if (view.actor !== actor) {
      problems.push(
        `${code}: aktor backendда «${actor}», frontendда «${view.actor}»`,
      );
    }
    if (!SNAPSHOT_ACTORS.includes(view.actor)) {
      problems.push(`${code}: noma'lum aktor «${view.actor}»`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "«BUNI KIM TUZATADI?» javobi ikki tomonda AJRALIB KETGAN (§10.5):\n  " +
      problems.join("\n  "),
  );
});

test("G-5: HAR BACKEND kodi uchun sabab va tuzatish UCHALA tilda bor", () => {
  if (snapshotsCopyMissing()) {
    console.log(
      "[G-5] `snapshots.errorCause.*` hali uchala tilda ham yo'q — langar " +
        "copy qo'shilishi bilan AVTOMATIK kuchga kiradi.",
    );
    return;
  }

  const problems = [];
  for (const locale of LOCALES) {
    const snapshots = loadMessages(locale).snapshots ?? {};
    const causes = snapshots.errorCause ?? {};
    const fixes = snapshots.errorFix ?? {};

    for (const code of backendCaptureActors.keys()) {
      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(`${locale}.json: snapshots.errorCause.${code} YO'Q`);
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(`${locale}.json: snapshots.errorFix.${code} YO'Q`);
      }
    }
    // Teskari yo'nalish: matn bor, kod yo'q — o'lik kalit.
    for (const code of Object.keys(causes)) {
      if (!backendCaptureActors.has(code)) {
        problems.push(
          `${locale}.json: snapshots.errorCause.${code} backend reyestrida YO'Q`,
        );
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "kadr olish xatosining matni backend reyestri bilan ajralib ketgan:\n  " +
      problems.join("\n  "),
  );
});

test("G-5: `snapshots.actor.*` uchala tilda va AYNAN uchta qiymat (§10.5)", () => {
  const present = LOCALES.filter(
    (locale) => Object.keys(loadMessages(locale).snapshots?.actor ?? {}).length > 0,
  );

  if (present.length === 0) {
    console.log(
      "[G-5] `snapshots.actor.*` hali uchala tilda ham yo'q — darvoza copy qo'shilishi " +
        `bilan AYNAN uchta qiymatni TALAB qiladi: ${SNAPSHOT_ACTORS.join(", ")}.`,
    );
    return;
  }

  // ⚠ QISMAN mavjudlik ALOHIDA nosozlik: bir tilda bor, ikkinchisida
  //   yo'q holat `i18n:check` dan O'TADI (u parity'ni tekshiradi, lekin
  //   bu kalitlar MA'LUMOTDAN quriladi va uchala faylda ham bo'lmasa
  //   parity baribir yashil).
  assert.deepEqual(
    present.sort(),
    [...LOCALES].sort(),
    `\`snapshots.actor.*\` faqat ${present.join(", ")} da bor — QISMAN tarjima ` +
      "qolgan tillarda tarjimasiz texnik identifikator ko'rsatardi",
  );

  for (const locale of LOCALES) {
    assert.deepEqual(
      Object.keys(loadMessages(locale).snapshots.actor).sort(),
      SNAPSHOT_ACTORS,
      `${locale}.json: snapshots.actor ro'yxati §10.5 bilan mos emas. Har xato ` +
        "«BUNI KIM TUZATADI?» savoliga javob berishi SHART.",
    );
  }
});

/* ---------------------------------------------------------------------------
 * G-17 — 5-FAZA: OLTINCHI REYESTR va IKKI NAMESPACE USTIDAGI PARITY.
 *
 * Zanjir uch bo'g'inli va har bo'g'in boshqa tilda:
 *
 *   occupancy_errors.py::ZONE_ERROR_CODES / REVIEW_ERROR_CODES
 *     -> lib/zone-errors.ts::OCCUPANCY_ERROR_META   (kod + SIRT + tone)
 *     -> messages/*.json                            (sabab va tuzatish)
 *
 * ⛔ NEGA LANGAR BACKENDDA, MATN KATALOGIDA EMAS — 04-10 NING DARSI.
 *
 *   G-5 ning dastlabki shakli `Object.keys(causes)` ga, ya'ni MATN
 *   KATALOGINING O'ZIGA tayanardi. U to'plamning ICHKI izchilligini
 *   o'lchardi, TO'LIQLIGINI emas: backend yangi kod qo'shsa-yu uchala
 *   tilda ham matn yozilmasa, sabab<->tuzatish parity BUZILMASDI va
 *   `>= N` sharti ham o'tardi. Darvoza YASHIL qolardi, admin esa
 *   «Kutilmagan xato» ni ko'rardi. Aynan shu sinf 04-09 da HAQIQATAN
 *   ro'y bergan.
 *
 *   Shuning uchun bu yerdagi HAR SIKL backend reyestridan boshlanadi.
 *
 * ⛔ SIRT HAM SOLISHTIRILADI, faqat kodlar emas — 04-10 dagi `actor`
 *   ustunining aynan bir xil sinfi. Kod QAYSI EKRANDA ko'rsatilishi ikki
 *   tomonda MUSTAQIL yozilgan fakt: backendda u REYESTR NOMI bilan
 *   (`ZONE_ERROR_CODES` / `REVIEW_ERROR_CODES`), frontendda esa
 *   `surface` maydoni bilan ifodalanadi. Ular ajralib ketsa, matn
 *   MAVJUD BO'LMAGAN namespace'dan qidirilardi va foydalanuvchi
 *   tarjimasiz texnik satrni ko'rardi — kod nomi esa ikkala tomonda ham
 *   BIR XIL bo'lgani uchun hech qanday darvoza qizarmasdi.
 * ------------------------------------------------------------------------ */

/**
 * `NAME: Final[frozenset[str]] = frozenset({ ... })` ichidagi KONSTANTA
 * NOMLARI -> ular ko'rsatayotgan kodlar.
 *
 * ⚠ NEGA MAVJUD `readPythonFrozenset` ISHLATILMAYDI. U qo'shtirnoqli
 *   LITERALLARNI o'qiydi, `occupancy_errors.py` ning reyestrlari esa
 *   KONSTANTALARDAN yig'ilgan — chunki §S-7 har kod uchun ALOHIDA
 *   docstring talab qiladi va docstringni frozenset ichiga yozib
 *   bo'lmaydi. Literal ro'yxat + konstantalar IKKI NUSXA bo'lardi.
 *
 *   Bu 04-10 dagi qarorning aynan takrori: u yerda ham `CAPTURE_ERROR_META`
 *   uchun `readPythonStrConstants` + `readCaptureActors` YOZILGAN, chunki
 *   umumiy parser reyestrni jimgina BO'SH deb o'qigan bo'lardi.
 *
 * ⚠ «TOPILMADI = YIQILISH» (§S-10): blok topilmasa yoki bo'sh chiqsa
 *   `assert` yiqiladi, `[]` qaytarilmaydi.
 */
function readPythonFrozensetRefs(source, name, constants) {
  const start = source.indexOf(`${name}: Final[frozenset[str]] = frozenset(`);
  assert.ok(start !== -1, `${name} backend faylida topilmadi`);

  const rest = source.slice(start);
  const end = rest.indexOf("\n)");
  assert.ok(end !== -1, `${name} bloki yopilmagan`);

  const refs = rest
    .slice(0, end)
    .split("\n")
    .filter((line) => !line.trim().startsWith("#"))
    .map((line) => /^\s*([A-Z_0-9]+),\s*$/u.exec(line))
    .filter(Boolean)
    .map((match) => match[1]);

  assert.ok(refs.length > 0, `${name} bloki BO'SH o'qildi — parser sinigan`);

  return refs.map((ref) => {
    const code = constants.get(ref);
    assert.ok(code !== undefined, `${name}: ${ref} konstantasi topilmadi`);
    return code;
  });
}

/** `kod: { tone: "...", surface: "..." },` — `zone-errors.ts` ning jadvali. */
function readTsZoneMeta(source) {
  return new Map(
    [
      ...source.matchAll(
        /^\s{2}([a-z_]+):\s*\{\s*tone:\s*"([a-z]+)",\s*surface:\s*"([A-Za-z]+)"\s*\}/gmu,
      ),
    ].map((match) => [match[1], { tone: match[2], surface: match[3] }]),
  );
}

/** Reyestr nomi -> matn namespace'i. Backendda SIRT aynan shu tarzda yashaydi. */
const OCCUPANCY_SURFACES = [
  { registry: "ZONE_ERROR_CODES", surface: "cameraZones", expected: 9 },
  { registry: "REVIEW_ERROR_CODES", surface: "review", expected: 6 },
];

const occupancySource = read(BACKEND_OCCUPANCY_ERRORS);
const occupancyConstants = readPythonStrConstants(occupancySource);

/** kod -> sirt (backend haqiqati). */
const backendOccupancySurface = new Map();
for (const { registry, surface } of OCCUPANCY_SURFACES) {
  for (const code of readPythonFrozensetRefs(
    occupancySource,
    registry,
    occupancyConstants,
  )) {
    backendOccupancySurface.set(code, surface);
  }
}

test("G-17: bandlik reyestri o'qildi va AYNAN o'n besh kod (nazorat)", () => {
  /*
   * Nazorat: parser sinsa (masalan reyestr `tuple` ga aylantirilsa)
   * quyidagi uchala darvoza ham JIMGINA yashil bo'lardi — bo'sh to'plam
   * bo'yicha aylanish hech nimani tekshirmaydi.
   */
  assert.equal(
    occupancyConstants.size,
    15,
    `occupancy_errors.py dan ${occupancyConstants.size} konstanta o'qildi, kutilgan 15`,
  );

  for (const { registry, surface, expected } of OCCUPANCY_SURFACES) {
    const codes = readPythonFrozensetRefs(
      occupancySource,
      registry,
      occupancyConstants,
    );
    assert.equal(
      codes.length,
      expected,
      `${registry} dan ${codes.length} kod o'qildi, kutilgan ${expected} (sirt: ${surface})`,
    );
  }

  assert.equal(backendOccupancySurface.size, 15, "ikki sirt reyestri kesishib qolgan");
});

test("G-17: `OCCUPANCY_ERROR_CODES` ikki reyestrdan HOSILA (uchinchi ro'yxat yo'q)", () => {
  /*
   * ⛔ Bu assert §S-5 ni MEXANIK qiladi. `OCCUPANCY_ERROR_CODES` qo'lda
   *   uchinchi marta yozilsa, u ikki sirt reyestri bilan bir kun ajralib
   *   ketardi va `app/schemas.py` ning allowlist'i reyestrdan KICHIK
   *   bo'lib qolardi — router kod bilan `HTTPException` ko'tarardi,
   *   allowlist esa uni tanimay `errors.generic` ga tushirardi.
   *
   *   Bu holatni yuqoridagi testlar KO'RMASDI: ular ikki sirt reyestrini
   *   o'qiydi va uchinchi e'londan umuman bexabar.
   */
  assert.match(
    occupancySource,
    /OCCUPANCY_ERROR_CODES: Final\[frozenset\[str\]\] =\s*ZONE_ERROR_CODES \| REVIEW_ERROR_CODES/u,
    "`OCCUPANCY_ERROR_CODES` ikki sirt reyestrining BIRLASHMASI bo'lishi SHART — " +
      "qo'lda yozilgan uchinchi ro'yxat ikkinchi haqiqat manbai bo'lardi (§S-5)",
  );
});

test("G-17: `lib/zone-errors.ts` backend reyestrining TO'LIQ ko'zgusi va SIRT MOS", () => {
  const meta = readTsZoneMeta(read(ZONE_ERRORS));

  assert.ok(
    meta.size >= 14,
    `zone-errors.ts dan atigi ${meta.size} yozuv o'qildi — parser sinigan bo'lishi mumkin`,
  );

  const problems = [];
  for (const [code, surface] of backendOccupancySurface) {
    const view = meta.get(code);
    if (view === undefined) {
      problems.push(
        `zone-errors.ts: ${code} uchun yozuv YO'Q — kod backendда bor, frontendда ` +
          "esa u `errors.generic` ga tushadi (D-02)",
      );
      continue;
    }
    if (view.surface !== surface) {
      problems.push(
        `${code}: sirt backendда «${surface}», frontendда «${view.surface}» — ` +
          "matn mavjud bo'lmagan namespace'dan qidirilardi",
      );
    }
    if (view.tone !== "danger" && view.tone !== "warning") {
      problems.push(`${code}: noma'lum tone «${view.tone}» (uchinchisi YO'Q)`);
    }
  }

  // Teskari yo'nalish: ko'zguda ORTIQCHA kod — hech qachon kelmaydigan
  // xato uchun matn va qoida saqlab yurish.
  for (const code of meta.keys()) {
    if (!backendOccupancySurface.has(code)) {
      problems.push(`zone-errors.ts: ${code} backend reyestrida YO'Q`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "bandlik xato taksonomiyasi ikki tomonda AJRALIB KETGAN:\n  " +
      problems.join("\n  "),
  );
});

test("G-17: HAR BACKEND kodi uchun sabab va tuzatish UCHALA tilda bor", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);

    // OLDINGA: backend reyestridan boshlanadi (LANGAR).
    for (const [code, surface] of backendOccupancySurface) {
      const causes = messages[surface]?.errorCause ?? {};
      const fixes = messages[surface]?.errorFix ?? {};

      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(`${locale}.json: ${surface}.errorCause.${code} YO'Q`);
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(`${locale}.json: ${surface}.errorFix.${code} YO'Q`);
      }
    }

    // TESKARI: matn bor, kod yo'q — o'lik kalit. Sirt ham tekshiriladi:
    // kod TO'G'RI namespace'da bo'lishi shart.
    for (const { surface } of OCCUPANCY_SURFACES) {
      for (const group of ["errorCause", "errorFix"]) {
        for (const code of Object.keys(messages[surface]?.[group] ?? {})) {
          const actual = backendOccupancySurface.get(code);
          if (actual === undefined) {
            problems.push(
              `${locale}.json: ${surface}.${group}.${code} backend reyestrida YO'Q`,
            );
          } else if (actual !== surface) {
            problems.push(
              `${locale}.json: ${surface}.${group}.${code} NOTO'G'RI namespace'da ` +
                `(backend sirti: ${actual})`,
            );
          }
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — sabab va tuzatish JUFT va TO'G'RI SIRTDA bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});

/* ---------------------------------------------------------------------------
 * G-17 — 6-FAZA: YETTINCHI REYESTR va UCH SIRT USTIDAGI PARITY (OP-12).
 *
 * Zanjir yana uch bo'g'inli va har bo'g'in boshqa tilda:
 *
 *   billing_errors.py::{COLLECT,SHIFT,BILLING,CLIENT_ONLY}_ERROR_CODES
 *     -> lib/billing-errors.ts::BILLING_ERROR_META   (kod + SIRT + tone)
 *     -> messages/*.json                             (sabab va tuzatish)
 *
 * ⛔⛔ NEGA YANGI BLOK VA YANGI BACKEND FAYLI — O'LCHOV BILAN (§0.1 M-B).
 *
 *   Yuqoridagi bandlik bloki `occupancyConstants.size` ni ANIQ SON (15)
 *   bilan talab qiladi. 6-fazaning kodlarini `occupancy_errors.py` ga
 *   qo'shish o'sha nazorat qiymatini DARHOL qizartirardi va uni
 *   "tuzatish" yagona yo'li — sonni oshirish, ya'ni nazoratning butun
 *   ma'nosini yo'q qilish bo'lardi.
 *
 *   Shuning uchun bandlik bloki TEGILMAYDI va bu blok o'z aniq soniga
 *   ega: `billingConstants.size === 14`.
 *
 * ⚠ REYESTR NOMI EKRANNI, `surface` esa MATN NAMESPACE'ini bildiradi va
 *   ular 1:1 EMAS — bu bandlik blokidan FARQ QILADIGAN yagona joy.
 *   `/collect/shift` `/collect` ning bolasi, ya'ni SMENA kodlari ham
 *   `collect.*` da yashaydi; `network_unreachable` esa serverdan hech
 *   qachon kelmaydi, lekin ekranda AYNI xato bloki bo'lib chiziladi.
 * ------------------------------------------------------------------------ */

/** Reyestr nomi -> matn namespace'i + kutilgan kod soni. */
const BILLING_SURFACES = [
  { registry: "COLLECT_ERROR_CODES", surface: "collect", expected: 9 },
  { registry: "SHIFT_ERROR_CODES", surface: "collect", expected: 3 },
  { registry: "BILLING_ERROR_CODES", surface: "billing", expected: 1 },
  { registry: "CLIENT_ONLY_ERROR_CODES", surface: "collect", expected: 1 },
];

/** `BILLING_SURFACES` dagi TAKRORLANMAS namespace'lar (teskari skan uchun). */
const BILLING_NAMESPACES = [
  ...new Set(BILLING_SURFACES.map((item) => item.surface)),
];

/**
 * `kod: { tone: "...", surface: "..." },` — `billing-errors.ts` ning jadvali.
 *
 * ⚠ MAVJUD `readTsZoneMeta` ISHLATILMAYDI: u `^\s{2}` ga, ya'ni AYNAN ikki
 *   bo'shliqqa qadalgan. `billing-errors.ts` da jadval `Readonly<Record<…>>`
 *   e'lonidan keyin bir daraja pastroqda turadi — umumiy parser uni jimgina
 *   BO'SH deb o'qib, quyidagi uchala testni ham yashil qilib qo'yardi.
 */
function readTsBillingMeta(source) {
  return new Map(
    [
      ...source.matchAll(
        /^\s{2,8}([a-z_]+):\s*\{\s*tone:\s*"([a-z]+)",\s*surface:\s*"([a-z]+)"\s*\}/gmu,
      ),
    ].map((match) => [match[1], { tone: match[2], surface: match[3] }]),
  );
}

const billingSource = read(BACKEND_BILLING_ERRORS);
const billingConstants = readPythonStrConstants(billingSource);

/** kod -> sirt (backend haqiqati). */
const backendBillingSurface = new Map();
for (const { registry, surface } of BILLING_SURFACES) {
  for (const code of readPythonFrozensetRefs(
    billingSource,
    registry,
    billingConstants,
  )) {
    backendBillingSurface.set(code, surface);
  }
}

test("G-17: billing reyestri o'qildi va AYNAN o'n to'rt kod (nazorat)", () => {
  /*
   * Nazorat: parser sinsa (masalan reyestr `tuple` ga aylantirilsa)
   * quyidagi darvozalar ham JIMGINA yashil bo'lardi — bo'sh to'plam
   * bo'yicha aylanish hech nimani tekshirmaydi.
   */
  assert.equal(
    billingConstants.size,
    14,
    `billing_errors.py dan ${billingConstants.size} konstanta o'qildi, kutilgan 14`,
  );

  for (const { registry, surface, expected } of BILLING_SURFACES) {
    const codes = readPythonFrozensetRefs(
      billingSource,
      registry,
      billingConstants,
    );
    assert.equal(
      codes.length,
      expected,
      `${registry} dan ${codes.length} kod o'qildi, kutilgan ${expected} (sirt: ${surface})`,
    );
  }

  assert.equal(
    backendBillingSurface.size,
    14,
    "to'rt reyestr kesishib qolgan — bitta kod ikki sirtda bo'lolmaydi",
  );
});

test("G-17: `ALL_BILLING_ERROR_CODES` reyestrlardan HOSILA (qo'lda ro'yxat yo'q)", () => {
  /*
   * ⛔ `OCCUPANCY_ERROR_CODES` bilan aynan bir xil sabab (§S-5): qo'lda
   *   yozilgan aggregat bir kun reyestrlardan kichik bo'lib qolardi va
   *   `app/schemas.py` allowlist'i router ko'targan kodni tanimasdi.
   *
   * ⛔ IKKI POG'ONA ATAYIN: `SERVER_…` — allowlist uchun (u
   *   `network_unreachable` ni O'Z ICHIGA OLMAYDI, chunki allowlist
   *   «server nima qaytarishi mumkin» degan savolga javob beradi);
   *   `ALL_…` — frontend darvozasi uchun.
   */
  assert.match(
    billingSource,
    /SERVER_BILLING_ERROR_CODES: Final\[frozenset\[str\]\] = \(\s*COLLECT_ERROR_CODES \| SHIFT_ERROR_CODES \| BILLING_ERROR_CODES\s*\)/u,
    "`SERVER_BILLING_ERROR_CODES` UCH sirt reyestrining BIRLASHMASI bo'lishi SHART",
  );
  assert.match(
    billingSource,
    /ALL_BILLING_ERROR_CODES: Final\[frozenset\[str\]\] = \(\s*SERVER_BILLING_ERROR_CODES \| CLIENT_ONLY_ERROR_CODES\s*\)/u,
    "`ALL_BILLING_ERROR_CODES` HOSILA bo'lishi SHART — qo'lda yozilgan " +
      "ro'yxat ikkinchi haqiqat manbai bo'lardi (§S-5)",
  );
});

test("G-17: `AMOUNT_UNAVAILABLE_REASONS` ALOHIDA va u KOD REYESTRI EMAS", () => {
  /*
   * ⛔ BU TO'PLAM YUZA REYESTRI EMAS: uning ikkala kodi ham allaqachon
   *   `COLLECT_ERROR_CODES` da. Vazifasi boshqa — u proyeksiya javobidagi
   *   `unavailable_reason` maydonining YOPIQ qiymat to'plami (§9.4) va
   *   `resolve_stall_day_money()` (06-06) uni IMPORT qiladi, ya'ni
   *   `"market_closed"` satri kodda IKKINCHI marta yozilmaydi.
   *
   * ⛔ SHUNING UCHUN U `billingConstants` SANOG'IGA TUSHMASLIGI KERAK:
   *   `readPythonStrConstants` faqat `Final[str]` konstantalarini oladi,
   *   `Final[frozenset[str]]` e'lonlarini emas. Yuqoridagi `size === 14`
   *   asserti aynan shu qoidaga tayanadi — yangi frozenset qo'shish uni
   *   buzmasligi kerak.
   */
  const reasons = readPythonFrozensetRefs(
    billingSource,
    "AMOUNT_UNAVAILABLE_REASONS",
    billingConstants,
  );

  assert.deepEqual(
    [...reasons].sort(),
    ["market_closed", "tariff_missing"],
    "`AMOUNT_UNAVAILABLE_REASONS` §9.4 dagi ikki sababdan iborat bo'lishi SHART",
  );

  // Ikkalasi ham kassir yuzasining kodi — ya'ni to'plam yangi kod KIRITMAYDI.
  for (const code of reasons) {
    assert.equal(
      backendBillingSurface.get(code),
      "collect",
      `${code} kassir yuzasining kodi bo'lishi kerak edi`,
    );
  }
});

test("G-17: `lib/billing-errors.ts` backend reyestrining TO'LIQ ko'zgusi va SIRT MOS", () => {
  const meta = readTsBillingMeta(read(BILLING_ERRORS));

  assert.ok(
    meta.size >= 13,
    `billing-errors.ts dan atigi ${meta.size} yozuv o'qildi — parser sinigan bo'lishi mumkin`,
  );

  const problems = [];
  for (const [code, surface] of backendBillingSurface) {
    const view = meta.get(code);
    if (view === undefined) {
      problems.push(
        `billing-errors.ts: ${code} uchun yozuv YO'Q — kod backendда bor, ` +
          "frontendда esa u `errors.generic` ga tushadi (D-02)",
      );
      continue;
    }
    if (view.surface !== surface) {
      problems.push(
        `${code}: sirt backendда «${surface}», frontendда «${view.surface}» — ` +
          "matn mavjud bo'lmagan namespace'dan qidirilardi",
      );
    }
    if (!["neutral", "warning", "danger"].includes(view.tone)) {
      problems.push(`${code}: noma'lum tone «${view.tone}» (to'rtinchisi YO'Q)`);
    }
  }

  // Teskari yo'nalish: ko'zguda ORTIQCHA kod — hech qachon kelmaydigan
  // xato uchun matn va qoida saqlab yurish.
  for (const code of meta.keys()) {
    if (!backendBillingSurface.has(code)) {
      problems.push(`billing-errors.ts: ${code} backend reyestrida YO'Q`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "billing xato taksonomiyasi ikki tomonda AJRALIB KETGAN:\n  " +
      problems.join("\n  "),
  );
});

test("G-17: HAR BILLING kodi uchun sabab va tuzatish UCHALA tilda bor", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);

    // OLDINGA: backend reyestridan boshlanadi (LANGAR).
    for (const [code, surface] of backendBillingSurface) {
      const causes = messages[surface]?.errorCause ?? {};
      const fixes = messages[surface]?.errorFix ?? {};

      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(`${locale}.json: ${surface}.errorCause.${code} YO'Q`);
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(`${locale}.json: ${surface}.errorFix.${code} YO'Q`);
      }
    }

    // TESKARI: matn bor, kod yo'q — o'lik kalit. Sirt ham tekshiriladi.
    for (const surface of BILLING_NAMESPACES) {
      for (const group of ["errorCause", "errorFix"]) {
        for (const code of Object.keys(messages[surface]?.[group] ?? {})) {
          const actual = backendBillingSurface.get(code);
          if (actual === undefined) {
            problems.push(
              `${locale}.json: ${surface}.${group}.${code} backend reyestrida YO'Q`,
            );
          } else if (actual !== surface) {
            problems.push(
              `${locale}.json: ${surface}.${group}.${code} NOTO'G'RI namespace'da ` +
                `(backend sirti: ${actual})`,
            );
          }
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — billing sabab/tuzatish JUFT va TO'G'RI SIRTDA bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});

test("G-17: `market_closed` matni §9.4 dagi EKRAN matni bilan AYNAN bir xil", () => {
  /*
   * ⛔ BU KOD IKKI JOYDA KO'RINADI: proyeksiya kartasidagi «summa yo'q»
   *   sababi (`collect.marketClosed`, §9.4) va 422 javobining xato bloki
   *   (`collect.errorCause.market_closed`). Ikki xil jumla kassirga IKKI
   *   XIL HODISA bo'lib tuyulardi — u ekranda bir narsani o'qib, so'rov
   *   yuborgach boshqasini ko'rardi va tizim beqaror deb xulosa qilardi.
   *
   * ⚠ Tenglik UCHALA locale'da talab qilinadi: `uz-Cyrl` generatsiya
   *   bo'lgani uchun u avtomatik mos keladi, `ru` esa QO'LDA yoziladi —
   *   aynan u ajralib ketishi mumkin bo'lgan yarim.
   */
  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    assert.equal(
      messages.collect?.errorCause?.market_closed,
      messages.collect?.marketClosed,
      `${locale}.json: collect.errorCause.market_closed va collect.marketClosed ` +
        "AJRALIB KETGAN (§9.4)",
    );
    assert.ok(
      (messages.collect?.marketClosed ?? "").length > 10,
      `${locale}.json: collect.marketClosed bo'sh — tenglik jimgina rost bo'lardi`,
    );
  }
});

/* ---------------------------------------------------------------------------
 * G-17 — 7-FAZA: SAKKIZINCHI REYESTR va u ⛔ FRONTENDДА LANGAR.
 *
 * Zanjir bu safar IKKI bo'g'inli va bu ATAYIN:
 *
 *   lib/reconciliation-errors.ts::RECON_ERROR_CODES   (TypeScript — LANGAR)
 *     -> messages/*.json::recon.errorCause/errorFix   (sabab va tuzatish)
 *
 * ⛔⛔ NEGA BACKEND BO'G'INI YO'Q — O'LCHOV BILAN (07-10 SUMMARY, 3-band).
 *
 *   07-10 marshrut kodlarini (`status_unchanged`, `range_too_wide`,
 *   `cursor_invalid`, `day_in_future`, …) `billing_errors.py` ga ATAYIN
 *   QO'SHMAGAN: yuqoridagi billing bloki `billingConstants.size === 14`
 *   nazorat qiymatini talab qiladi va yangi kod uni DARHOL qizartirardi.
 *   Uni «tuzatish» yagona yo'li sonni oshirish, ya'ni nazoratning butun
 *   ma'nosini yo'q qilish bo'lardi — o'sha faylning
 *   `occupancyConstants.size === 15` bandida ochiq yozilgan sinf.
 *
 * ⛔ SHUNING UCHUN LANGAR FRONTENDДА: `RECON_ERROR_CODES` — EKRAN
 *    kodlarining ro'yxati, marshrut kodlariniki EMAS. Ikkinchisi
 *    `reconciliation-errors.ts::SERVER_CODE_MAP` da xaritalanadi va u
 *    quyida ALOHIDA o'lchanadi: xaritaning har NATIJASI reyestrda
 *    bo'lishi shart, aks holda server kod qaytarib, ekran `errors.generic`
 *    ga tushardi va D-02 ning «sabab + nima qilish kerak» kontrakti
 *    JIMGINA buzilardi.
 * ------------------------------------------------------------------------ */

const RECON_ERRORS = path.join(
  FRONTEND_ROOT,
  "src",
  "lib",
  "reconciliation-errors.ts",
);

/** `recon.*` — nomuvofiqlik yuzasining YAGONA matn namespace'i (§14.2). */
const RECON_NAMESPACE = "recon";

/**
 * §14.9 — nomuvofiqlik ekranining kodlari soni.
 *
 * ⛔ 4 -> 5 (07-23): 07-20 serverda `422 assignee_not_in_market` ni ochdi va
 *    u klientda xaritalanmagan edi — begona bozor xodimini biriktirish
 *    urinishi direktorga `errors.generic` bo'lib chiqardi.
 *
 * ⛔ BU SON — O'LCHAM QULFI, «yangilanadigan raqam» EMAS. Uni oshirish
 *    FAQAT uchala locale'ga matn qo'shilgandan keyin mumkin: quyidagi
 *    darvoza reyestrdan ITERATSIYA qiladi va yetishmagan tilni nomma-nom
 *    ko'rsatadi. Parser sinsa (masalan reyestr `Record` ga aylantirilsa)
 *    sikllar BO'SH to'plamda jimgina yashil bo'lardi — G-36 ning aynan
 *    darsi.
 */
const RECON_ERROR_CODE_COUNT = 5;

/**
 * ⛔ ZAXIRA KALIT — `recon.errorCause.*` GURUHIDAN TASHQARIDA.
 *
 * `case-detail-dialog.tsx` xaritada YO'Q har qanday kodni shu kalitga
 * tushiradi (B-5). Ya'ni u reyestrning a'zosi EMAS, lekin reyestrning
 * butun zaxira mexanizmi unga SUYANADI: kalit yo'qolsa `t()` chegarada
 * yiqilardi yoki xato bloki BO'SH chiqardi — va yiqilgan hukm yana
 * muvaffaqiyatlisidan farq qilmasdi.
 *
 * ⛔ SHUNING UCHUN U ALOHIDA O'LCHANADI: `recon.errorCause` guruhiga
 *    qo'shilsa TESKARI skan uni «reyestrda YO'Q o'lik kalit» deb
 *    ushlab, darvozani ifloslantirardi.
 */
const RECON_FALLBACK_KEY = ["errors", "generic"];

const reconSource = read(RECON_ERRORS);
const reconCodes = readTsStringArray(reconSource, "RECON_ERROR_CODES");

/** `xom_kod: "ekran_kodi",` — `SERVER_CODE_MAP` ning natijalari. */
function readServerCodeMap(source) {
  const block = /const SERVER_CODE_MAP[^{]*\{([\s\S]*?)\n\};/u.exec(source);
  assert.ok(block, "`SERVER_CODE_MAP` topilmadi — parser sinigan");
  return [...block[1].matchAll(/^\s+([a-z_]+):\s*"([a-z_]+)"/gmu)].map(
    (match) => [match[1], match[2]],
  );
}

test("G-17: nomuvofiqlik reyestri o'qildi va AYNAN besh kod (nazorat)", () => {
  /*
   * Nazorat: parser sinsa (masalan reyestr `Record` ga aylantirilsa)
   * quyidagi darvozalar ham JIMGINA yashil bo'lardi — bo'sh to'plam
   * bo'yicha aylanish hech nimani tekshirmaydi.
   */
  assert.equal(
    reconCodes.length,
    RECON_ERROR_CODE_COUNT,
    `RECON_ERROR_CODES dan ${reconCodes.length} kod o'qildi, kutilgan ` +
      `${RECON_ERROR_CODE_COUNT} (07-UI-SPEC §14.9)`,
  );
  assert.equal(
    new Set(reconCodes).size,
    reconCodes.length,
    `takrorlangan kod: ${reconCodes}`,
  );
});

test("G-17: `SERVER_CODE_MAP` ning HAR natijasi reyestrda bor", () => {
  /*
   * ⛔ ENG QIMMAT BAND. Server 07-10 da yetti xil mexanik kod qaytaradi
   *   (`not_found`, `status_unchanged`, …) va ular ekran kodlariga
   *   xaritalanadi. Xarita reyestrdan AJRALIB KETSA, marshrut kod
   *   qaytarib turadi, `reconErrorView()` esa mavjud bo'lmagan matn
   *   kalitini qurardi — `t()` chegarada yiqilardi yoki xato bloki
   *   BO'SH chiqardi.
   */
  const pairs = readServerCodeMap(reconSource);

  assert.ok(
    pairs.length >= 4,
    `SERVER_CODE_MAP dan atigi ${pairs.length} juftlik o'qildi — parser sinigan`,
  );

  const unknown = pairs
    .filter(([, screen]) => !reconCodes.includes(screen))
    .map(([raw, screen]) => `${raw} -> ${screen} (reyestrda YO'Q)`);

  assert.deepEqual(
    unknown,
    [],
    "xarita reyestrdan AJRALIB KETGAN — server kod qaytarardi, ekran esa " +
      "mavjud bo'lmagan matn kalitini qurardi:\n  " + unknown.join("\n  "),
  );
});

test("G-17: HAR NOMUVOFIQLIK kodi uchun sabab va tuzatish UCHALA tilda bor", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    const causes = messages[RECON_NAMESPACE]?.errorCause ?? {};
    const fixes = messages[RECON_NAMESPACE]?.errorFix ?? {};

    // OLDINGA: reyestrdan boshlanadi (LANGAR).
    for (const code of reconCodes) {
      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(
          `${locale}.json: ${RECON_NAMESPACE}.errorCause.${code} YO'Q`,
        );
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(
          `${locale}.json: ${RECON_NAMESPACE}.errorFix.${code} YO'Q`,
        );
      }
    }

    // TESKARI: matn bor, kod yo'q — O'LIK KALIT.
    for (const group of ["errorCause", "errorFix"]) {
      for (const code of Object.keys(
        messages[RECON_NAMESPACE]?.[group] ?? {},
      )) {
        if (!reconCodes.includes(code)) {
          problems.push(
            `${locale}.json: ${RECON_NAMESPACE}.${group}.${code} reyestrda YO'Q`,
          );
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — nomuvofiqlik sabab/tuzatish JUFT bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});

test("G-17: ZAXIRA kalit (`errors.generic`) UCHALA tilda bor", () => {
  /*
   * ⛔ ENG JIM NOSOZLIK SHU YERDA YASHIRINADI. Reyestr to'liq bo'lishi
   *   mumkin va yuqoridagi uchala darvoza yashil qolaverardi, lekin
   *   xaritada YO'Q kod (`NetworkError`, `422` massiv detali, `429`,
   *   `5xx`, `market_not_selected`) ZAXIRA matnga tushadi. Kalit
   *   yo'qolsa, direktor saqlash tugmasini bosib YANA hech nima
   *   ko'rmasdi — ya'ni B-5 aynan o'sha shaklda qaytardi.
   *
   * ⛔ DA'VO REYESTRDAN MUSTAQIL: u `recon` namespace'ida ham emas,
   *    `RECON_ERROR_CODES` da ham yo'q — shuning uchun teskari skanga
   *    tegmaydi va uni ifloslantirmaydi.
   */
  const problems = [];

  for (const locale of LOCALES) {
    let node = loadMessages(locale);
    for (const segment of RECON_FALLBACK_KEY) {
      node = node?.[segment];
    }

    if (typeof node !== "string" || node.trim() === "") {
      problems.push(`${locale}.json: ${RECON_FALLBACK_KEY.join(".")} YO'Q`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ xaritada YO'Q kod uchun ZAXIRA matn yo'q — yiqilgan hukm yana " +
      "muvaffaqiyatlisidan farq qilmaydi (B-5):\n  " + problems.join("\n  "),
  );

  /*
   * ⛔ NAZORAT: zaxira kaliti reyestr a'zosi BO'LMASLIGI kerak. Aks holda
   *   u `recon.errorCause.generic` juftligini ham talab qilardi va ikki
   *   mexanizm bir-birini yeb qo'yardi.
   */
  assert.ok(
    !reconCodes.includes("generic"),
    "`generic` reyestrga kirib qolgan — zaxira mexanizmi reyestr bilan " +
      "ARALASHDI",
  );
});

/* ---------------------------------------------------------------------------
 * G-17 — 8-FAZA: TO'QQIZINCHI REYESTR (HISOBOT YUZASI, W0-F4).
 *
 * Zanjir yuqoridagi nomuvofiqlik bloki bilan AYNI shaklda — IKKI bo'g'inli:
 *
 *   lib/report-errors.ts::REPORT_ERROR_CODES         (TypeScript — LANGAR)
 *     -> messages/*.json::reports.errorCause/errorFix (sabab va tuzatish)
 *
 * ⛔⛔ NEGA BU BLOK BOR — 08-UI-SPEC §5.1 (W0-F4) UNI NOMMA-NOM TALAB
 *     QILADI: «`REPORT_ERROR_CODES` … `error-codes.test.mjs` (G-17)
 *     UCHALA TILDA talab qiladi».
 *
 *     Usiz sakkiz kod × 3 locale × 2 guruh = 48 matn O'LCHANMAGAN qolardi.
 *     `i18n:check` bu sinfni USHLAY OLMAYDI (shu faylning bosh izohi):
 *     u uchala faylning bir-biriga mosligini ko'radi, ro'yxatning
 *     TO'LIQLIGINI emas — kalit uchala tilda ham yo'q bo'lsa, parity
 *     baribir yashil. Ya'ni `reportErrorView()` mavjud bo'lmagan kalit
 *     qurardi va xato bloki BO'SH chiqardi.
 *
 * ⛔ BACKEND BO'G'INI YO'Q va sabab `reconciliation-errors.ts` nikiga
 *    AYNAN teng: `billing_errors.py` ga qo'shish o'sha faylning
 *    `billingConstants.size === 14` nazorat qiymatini DARHOL qizartirardi.
 * ------------------------------------------------------------------------ */

const REPORT_ERRORS = path.join(
  FRONTEND_ROOT,
  "src",
  "lib",
  "report-errors.ts",
);

/** `reports.*` — hisobot yuzasining matn namespace'i (08-UI-SPEC §14.2). */
const REPORT_NAMESPACE = "reports";

/**
 * §14.9 — hisobot va daftar yuzasining kodlari soni.
 *
 * ⛔ SAKKIZ, YETTI EMAS. 08-UI-SPEC §14.9 jadvali YETTITASINI sanaydi;
 *    sakkizinchisi (`report_period_too_long`) 08-03 rejasining ONGLI
 *    qo'shimchasi va sababi `lib/report-errors.ts` da LITERAL yozilgan:
 *    §4.4 davr tanlagichiga uzunlik chegarasi ATAYIN qo'ymaydi, server
 *    esa `report_max_period_days = 366` ni majburlaydi. O'sha rad
 *    javobini `report_period_invalid` ga yig'ish ekranda «Boshlanish
 *    sanasi tugash sanasidan keyin bo'lmasin» degan YOLG'ON sababni
 *    ko'rsatardi.
 *
 * ⛔ BU SON — O'LCHAM QULFI, «yangilanadigan raqam» EMAS. Uni oshirish
 *    FAQAT uchala locale'ga matn qo'shilgandan keyin mumkin.
 */
const REPORT_ERROR_CODE_COUNT = 8;

const reportSource = read(REPORT_ERRORS);
const reportCodes = readTsStringArray(reportSource, "REPORT_ERROR_CODES");

test("G-17: hisobot reyestri o'qildi va AYNAN sakkiz kod (nazorat)", () => {
  /*
   * Nazorat: parser sinsa (masalan reyestr `Record` ga aylantirilsa)
   * quyidagi darvozalar BO'SH to'plam bo'yicha aylanib, JIMGINA yashil
   * qolardi — bu kodbazada bir necha marta o'lchangan nosozlik sinfi.
   */
  assert.equal(
    reportCodes.length,
    REPORT_ERROR_CODE_COUNT,
    `REPORT_ERROR_CODES dan ${reportCodes.length} kod o'qildi, kutilgan ` +
      `${REPORT_ERROR_CODE_COUNT} (08-UI-SPEC §14.9 + 08-03 qo'shimchasi)`,
  );
  assert.equal(
    new Set(reportCodes).size,
    reportCodes.length,
    `takrorlangan kod: ${reportCodes}`,
  );
});

test("G-17: hisobot `SERVER_CODE_MAP` ining HAR natijasi reyestrda bor", () => {
  /*
   * ⛔ Xarita reyestrdan AJRALIB KETSA, marshrut kod qaytarib turadi,
   *   `reportErrorView()` esa mavjud bo'lmagan matn kalitini qurardi —
   *   `t()` chegarada yiqilardi yoki xato bloki BO'SH chiqardi. Eksport
   *   tugmasi yonidagi jim xato esa foydalanuvchini tugmani qayta-qayta
   *   bosishga majburlardi (§12.2 — xato INLINE, toast emas).
   */
  const pairs = readServerCodeMap(reportSource);

  assert.ok(
    pairs.length >= 4,
    `SERVER_CODE_MAP dan atigi ${pairs.length} juftlik o'qildi — parser sinigan`,
  );

  const unknown = pairs
    .filter(([, screen]) => !reportCodes.includes(screen))
    .map(([raw, screen]) => `${raw} -> ${screen} (reyestrda YO'Q)`);

  assert.deepEqual(
    unknown,
    [],
    "hisobot xaritasi reyestrdan AJRALIB KETGAN:\n  " + unknown.join("\n  "),
  );
});

test("G-17: HAR HISOBOT kodi uchun sabab va tuzatish UCHALA tilda bor", () => {
  const problems = [];

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    const causes = messages[REPORT_NAMESPACE]?.errorCause ?? {};
    const fixes = messages[REPORT_NAMESPACE]?.errorFix ?? {};

    // OLDINGA: reyestrdan boshlanadi (LANGAR).
    for (const code of reportCodes) {
      if (typeof causes[code] !== "string" || causes[code].trim() === "") {
        problems.push(
          `${locale}.json: ${REPORT_NAMESPACE}.errorCause.${code} YO'Q`,
        );
      }
      if (typeof fixes[code] !== "string" || fixes[code].trim() === "") {
        problems.push(
          `${locale}.json: ${REPORT_NAMESPACE}.errorFix.${code} YO'Q`,
        );
      }
    }

    // TESKARI: matn bor, kod yo'q — O'LIK KALIT.
    for (const group of ["errorCause", "errorFix"]) {
      for (const code of Object.keys(
        messages[REPORT_NAMESPACE]?.[group] ?? {},
      )) {
        if (!reportCodes.includes(code)) {
          problems.push(
            `${locale}.json: ${REPORT_NAMESPACE}.${group}.${code} reyestrda YO'Q`,
          );
        }
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — hisobot sabab/tuzatish JUFT bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});

/* ---------------------------------------------------------------------------
 * 10-FAZA: OLTINCHI BACKEND-LANGARLI JUFTLIK — ANONIM DEMO SO'ROVI (LAND-03).
 *
 * Zanjir yana uch bo'g'inli va har bo'g'in boshqa tilda:
 *
 *   schemas.py::DEMO_ERROR_CODES              (Python — LANGAR, frozenset)
 *     -> lib/demo-errors.ts::DEMO_ERROR_CODES (TypeScript — ko'zgu)
 *     -> demoErrorMessageKey -> landing.form.* (JSON — uch tildagi matn)
 *
 * ⛔⛔ NEGA LANGAR BACKENDDA (RESEARCH ochiq savol №3, «Variant A»
 *     tavsiyasi qabul qilindi): mahalliy `switch` (variant B) darvozada
 *     KO'R NUQTA qoldirardi — backend beshinchi kodni qo'shsa yoki
 *     mavjudini qayta nomlasa, forma jim «Xatolik» ga tushib D-02 ning
 *     «sabab VA tuzatish yo'li» kontrakti buzilardi va HECH BIR darvoza
 *     qizarmasdi. Bu 04-09 da HAQIQATAN ro'y bergan sinf (olti yangi
 *     `MARKET_ERROR_CODES` kodi, unutilgan `ERROR_CODES` ko'zgusi).
 *
 * ⚠ FARQI: `demoErrorMessageKey` NISBIY kalit qaytaradi (`form.error.*`),
 *   chunki chaqiruvchi `useTranslations("landing")` bilan bog'laydi —
 *   katalog qidiruvida `landing.` prefiksi shu yerda qo'shiladi.
 *
 * ⚠ Xarita in'ektiv EMAS va bu ATAYIN: `delivery_failed` ham, noma'lum
 *   kod ham `form.error.body` ga tushadi (xom `detail` foydalanuvchiga
 *   HECH QACHON ko'rsatilmaydi — T-02-99 merosi). Shuning uchun bu yerda
 *   «har kod alohida kalit» talab qilinmaydi — talab «har kod XARITADA
 *   bor va har natija kalit uchala tilda mavjud».
 * ------------------------------------------------------------------------ */

const DEMO_ERRORS = path.join(FRONTEND_ROOT, "src", "lib", "demo-errors.ts");

/** `landing` — anonim yuzaning YAGONA matn namespace'i (10-UI-SPEC). */
const DEMO_NAMESPACE = "landing";

/**
 * §12.5 — anonim endpoint kodlari soni.
 *
 * ⛔ BU SON — O'LCHAM QULFI, «yangilanadigan raqam» EMAS. Parser sinsa
 *    (masalan frozenset `tuple` ga aylantirilsa) quyidagi darvozalar
 *    BO'SH to'plam bo'yicha aylanib JIMGINA yashil qolardi — shu faylda
 *    bir necha marta o'lchangan nosozlik sinfi (G-36 darsi).
 */
const DEMO_ERROR_CODE_COUNT = 4;

const demoBackendCodes = readPythonFrozenset(
  read(BACKEND_SCHEMAS),
  "DEMO_ERROR_CODES",
);
const demoMirrorSource = read(DEMO_ERRORS);
const demoMirrorCodes = readTsStringArray(demoMirrorSource, "DEMO_ERROR_CODES");
const demoKeyMap = readSwitchMap(demoMirrorSource);

test("LAND-03: demo reyestri o'qildi va AYNAN to'rt kod (nazorat)", () => {
  assert.equal(
    demoBackendCodes.length,
    DEMO_ERROR_CODE_COUNT,
    `DEMO_ERROR_CODES dan ${demoBackendCodes.length} kod o'qildi, kutilgan ` +
      `${DEMO_ERROR_CODE_COUNT} (schemas.py §12.5 reyestri)`,
  );
  assert.equal(
    new Set(demoBackendCodes).size,
    demoBackendCodes.length,
    `takrorlangan kod: ${demoBackendCodes}`,
  );
});

test("LAND-03: `lib/demo-errors.ts` backend reyestrining TO'LIQ ko'zgusi (IKKI yo'nalish)", () => {
  const problems = [];

  // OLDINGA: backendда bor, ko'zguda yo'q — forma jim «Xatolik» ga tushardi.
  for (const code of demoBackendCodes) {
    if (!demoMirrorCodes.includes(code)) {
      problems.push(
        `demo-errors.ts: ${code} YO'Q — kod backendда bor, frontendда esa u ` +
          "zaxira matnga tushadi va admin NIMA bo'lganini bilmaydi (D-02)",
      );
    }
  }
  // TESKARI: ko'zguda ORTIQCHA kod — hech qachon kelmaydigan xato uchun
  // matn va qoida saqlab yurish (NVR_ERROR_CODES bloki naqshi).
  for (const code of demoMirrorCodes) {
    if (!demoBackendCodes.includes(code)) {
      problems.push(`demo-errors.ts: ${code} backend reyestrida YO'Q`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "demo xato reyestri ikki tomonda AJRALIB KETGAN:\n  " + problems.join("\n  "),
  );
});

test("LAND-03: har backend kodi `demoErrorMessageKey` da xaritalangan va kaliti UCHALA tilda bor", () => {
  const problems = [];

  // Har backend kodi switch xaritasida bor (default'ga suyanib qolmaydi).
  const unmapped = demoBackendCodes.filter((code) => !demoKeyMap.has(code));
  assert.deepEqual(
    unmapped,
    [],
    `demo-errors.ts::demoErrorMessageKey da \`case\` yo'q: ${unmapped.join(", ")}`,
  );

  // Har natija kaliti `landing.` prefiksi bilan uchala tilda mavjud.
  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    for (const [code, relativeKey] of demoKeyMap) {
      const fullKey = `${DEMO_NAMESPACE}.${relativeKey}`;
      if (typeof lookup(messages, fullKey) !== "string") {
        problems.push(`${locale}.json da "${fullKey}" yo'q (kod: ${code})`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "D-02 buzilgan — demo xato matni uchala tilda bo'lishi SHART:\n  " +
      problems.join("\n  "),
  );
});
