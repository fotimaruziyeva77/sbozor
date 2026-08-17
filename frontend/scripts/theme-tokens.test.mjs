#!/usr/bin/env node
/**
 * G-motion-4 (09-UI-SPEC §11.3, §16) — TEMA QATLAMINING MEXANIK DARVOZASI.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — «komponent kodi o'zgarmaydi» da'vosining o'zi.
 *
 * (a) `dark:` Tailwind varianti — `className=` / `cn(` argumentlari ichida
 *     0 marta. Token-scope varianti KERAKSIZ qiladi; bitta `dark:` yozilsa,
 *     tema almashishi «token almashtirish» bo'lishdan chiqadi. ⛔ Skan
 *     ATAYLAB segmentlar bilan chegaralangan: `components/snapshots/
 *     capture-cell.tsx:106` (`dark: {` — light_mode gistogramma kaliti) va
 *     `lib/api-types.ts:1400` (`dark: z.number()`) — obyekt kalitlari,
 *     variant emas. Sodda `grep "dark:"` bugundan yolg'on qizil berardi
 *     [09-RESEARCH Tuzoq 6]. `@custom-variant dark` ham 0 — u `dark:` ni
 *     qonuniylashtirardi.
 *
 * (b) `@theme inline` — 0 marta. ⛔ Bu bitta so'z butun tema qatlamini
 *     JIMGINA o'ldiradi: `inline` utilitani `var()` o'rniga QIYMATGA
 *     kompilyatsiya qiladi va `[data-theme]` scope override umuman
 *     ishlamay qoladi [Tailwind hujjati, 09-RESEARCH Naqsh 1].
 *
 * (c) Scope tokenlari `@theme` ning `--color-*` to'plamining QISM to'plami
 *     (scope'da e'lon qilinmagan token — imlo xatosi, jimgina standartga
 *     tushardi). `--color-*-text` oilasining TO'RTALASI ikkala scope'da
 *     HAM bor — M-18 darsining mexanik shakli (sketch tokenlari beshta AA
 *     buzilishi olib kelgan edi). Scope'lar `@layer` ICHIDA EMAS —
 *     qatlamga o'ralsa override kaskadda yutqazardi.
 *
 * (d) `data-theme` reyestri AYNAN 3 a'zo — uch MUSTAQIL manbadan
 *     (globals.css scope'lari, lib/theme.ts `THEMES`, messages `theme.*`)
 *     to'plam tengligi bilan. To'rtinchi tema qo'shilsa yoki birortasi
 *     yo'qolsa uchala manba ham darvozada uchrashadi.
 *
 * (e) `layout.tsx`: `suppressHydrationWarning` + `<head>` inline skripti,
 *     skript matnida `sbozor-theme` va uchala reyestr qiymati LITERAL
 *     qat'iy solishtiruvda — `localStorage` dagi ixtiyoriy satr
 *     `data-theme` ga o'ta OLMASLIGINING mexanik isboti (T-09-01).
 * =============================================================================
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (D-32): kataloglar `readdirSync`
 *   bilan REKURSIV o'qiladi, `.test.` fayllar chiqariladi.
 *
 * ⚠ TO'PLAM TENGLIGI, `not.toContain` EMAS (D-31): natijalar
 *   `assert.deepEqual(hits, [])` bilan o'lchanadi.
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN skanerlanadi — «`dark:` yozilmasin»
 *   degan izohning o'zi darvozani qizartirmasin. Filtr «yutib yubormadi»
 *   nazorati bilan juft (runaway nazorati).
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

const GLOBALS_CSS = path.join(SRC, "app", "globals.css");
const THEME_TS = path.join(SRC, "lib", "theme.ts");
const LAYOUT_TSX = path.join(SRC, "app", "[locale]", "layout.tsx");
const MESSAGES_DIR = path.join(FRONTEND_ROOT, "messages");

/** (a) skan doirasi — komponentlar va marshrutlar (lib/ ATAYLAB tashqarida:
 * u yerda `dark:` obyekt kaliti qonuniy — `api-types.ts:1400`). */
const SCAN_DIRS = [
  path.join(SRC, "components"),
  path.join(SRC, "app"),
];

/** Skanerlanadigan kengaytmalar. */
const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

/** Mahsulot fayli emas — qamrovdan chiqadi. */
const TEST_FILE = /\.test\.tsx?$/;

/* -------------------------------------------------------------------------- */
/* REYESTRLAR — YOPIQ, QUYI CHEGARALI                                         */
/* -------------------------------------------------------------------------- */

/** ⛔ `data-theme` reyestri — AYNAN uch a'zo (09-UI-SPEC §11.1). */
const THEME_REGISTRY = ["light", "dark", "sun"];

/** ⛔ Scope selektorlari — `light` BAZA (`@theme` scope'siz amal qiladi),
 * shuning uchun scope FAQAT qolgan ikkitasiga yoziladi. */
const SCOPED_THEMES = ["dark", "sun"];

/** ⛔ `--color-*-text` oilasi — TO'RTALASI ikkala scope'da HAM (M-18). */
const TEXT_TOKEN_FAMILY = [
  "--color-accent-text",
  "--color-success-text",
  "--color-warning-text",
  "--color-danger-text",
];

/** `theme.*` copy kalitlari (SPEC §14.1) — label + uch tema nomi. */
const THEME_MESSAGE_KEYS = ["dark", "label", "light", "sun"];

/**
 * QUYI CHEGARALAR.
 *
 * ⚠ Usiz skan bo'sh to'plam ustida abadiy yashil qolardi: katalog ko'chsa
 *   yoki `@theme` bloki qisqarsa, darvoza qizarishi shart.
 *   [O'LCHANDI 2026-08-17]: components/ 136 + app/ 30 = 166 mahsulot fayli;
 *   `@theme` da 22 ta `--color-*` token.
 */
const MIN_SCANNED_FILES = 150;
const MIN_THEME_COLOR_TOKENS = 20;

/* -------------------------------------------------------------------------- */
/* FILTRLAR                                                                   */
/* -------------------------------------------------------------------------- */

/**
 * JS/TS izohlarini olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 * ⛔ `collect-surface.test.mjs:215-277` DAN KO'CHIRILGAN NUSXA — uchinchi
 *    implementatsiya yozilmaydi (06-UI-SPEC W0-F4 qoidasi shu naqshda).
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

/** CSS izohlarini olib tashlaydi (`/* ... *​/` bloklari). */
function stripCssComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, "");
}

/** Faylning izohsiz kodi + «yutib yuborilmadi» nazorati. */
function readCode(file) {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);

  if (raw.includes("export")) {
    assert.ok(
      code.includes("export"),
      `${path.relative(FRONTEND_ROOT, file)}: izoh filtri faylni YUTIB YUBORDI ` +
        "(manbada `export` bor, filtrdan keyin yo'q) — darvoza o'chib qolgan bo'lardi",
    );
  }

  return code;
}

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv, hosila qamrov). */
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

/* -------------------------------------------------------------------------- */
/* (a) — `dark:` VARIANT DETEKTORI: className= / cn( SEGMENTLARI              */
/* -------------------------------------------------------------------------- */

/**
 * `openIndex` dagi ochuvchi belgidan balanslangan segmentni qaytaradi.
 * Satr literallari ichidagi qavslar SANALMAYDI (aks holda `cn("a(b")`
 * segmentni buzardi). Balanslanmasa fayl oxirigacha olinadi — QATTIQ
 * tomonga og'ish: segment kattaroq bo'ladi, darvoza bo'shamaydi.
 */
function extractBalanced(code, openIndex, openChar, closeChar) {
  let depth = 0;
  let str = null;
  for (let i = openIndex; i < code.length; i++) {
    const c = code[i];
    if (str) {
      if (c === "\\") {
        i += 1;
        continue;
      }
      if (c === str) str = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") {
      str = c;
      continue;
    }
    if (c === openChar) depth += 1;
    else if (c === closeChar) {
      depth -= 1;
      if (depth === 0) return code.slice(openIndex, i + 1);
    }
  }
  return code.slice(openIndex);
}

/** Kavichkali satrni (boshlanish indeksi — kavichkaning o'zi) oxirigacha oladi. */
function extractString(code, quoteIndex) {
  const quote = code[quoteIndex];
  for (let i = quoteIndex + 1; i < code.length; i++) {
    if (code[i] === "\\") {
      i += 1;
      continue;
    }
    if (code[i] === quote) return code.slice(quoteIndex, i + 1);
  }
  return code.slice(quoteIndex);
}

/**
 * `className=` va `cn(` ARGUMENT segmentlari — (a) skanining chegarasi.
 * ⛔ Butun faylni emas, AYNAN klass beriladigan joylarni qamraydi —
 *    yolg'on-ijobiy manbai (obyekt kaliti `dark:`) shu chegara bilan
 *    kesiladi [09-RESEARCH Tuzoq 6].
 */
function extractClassSegments(code) {
  const segments = [];

  for (const m of code.matchAll(/\bcn\(/g)) {
    const openIndex = m.index + m[0].length - 1;
    segments.push(extractBalanced(code, openIndex, "(", ")"));
  }

  for (const m of code.matchAll(/className=/g)) {
    const at = m.index + m[0].length;
    const c = code[at];
    if (c === "{") {
      segments.push(extractBalanced(code, at, "{", "}"));
    } else if (c === '"' || c === "'") {
      segments.push(extractString(code, at));
    }
  }

  return segments;
}

/** Segment ichidagi satr literallarining MAZMUNI (kavichkasiz). */
function stringLiteralsOf(segment) {
  const out = [];
  let str = null;
  let current = "";
  for (let i = 0; i < segment.length; i++) {
    const c = segment[i];
    if (str) {
      if (c === "\\") {
        current += c + (segment[i + 1] ?? "");
        i += 1;
        continue;
      }
      if (c === str) {
        out.push(current);
        str = null;
        current = "";
        continue;
      }
      current += c;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") str = c;
  }
  // Yopilmagan satr — qattiq tomonga: mazmuni baribir tekshiriladi.
  if (str) out.push(current);
  return out;
}

/**
 * Kodda `dark:` VARIANTI ishlatilgan satr literallari.
 * Obyekt kaliti `dark:` (satrdan TASHQARIDA) — ushlanmaydi; satr ICHIDAGI
 * `dark:` (ya'ni Tailwind klassi sifatida brauzerga yetib boradigan shakl) —
 * ushlanadi.
 */
function findDarkVariants(code) {
  const hits = [];
  for (const segment of extractClassSegments(code)) {
    for (const literal of stringLiteralsOf(segment)) {
      if (/dark:/.test(literal)) hits.push(literal);
    }
  }
  return hits;
}

/* -------------------------------------------------------------------------- */
/* CSS PARSE — @theme bloki, scope bloklari, @layer oraliqlari                */
/* -------------------------------------------------------------------------- */

const cssRaw = readFileSync(GLOBALS_CSS, "utf8");
const css = stripCssComments(cssRaw);

// Runaway nazorati: CSS izoh filtri faylni yutib yubormadi.
assert.ok(
  css.includes("@theme"),
  "globals.css: CSS izoh filtri `@theme` ni yutib yubordi — parse o'chib qolgan bo'lardi",
);

/** `startIndex` — blokning `{` indeksi; balanslangan CSS blokini qaytaradi. */
function extractCssBlock(source, startIndex) {
  let depth = 0;
  for (let i = startIndex; i < source.length; i++) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(startIndex, i + 1);
    }
  }
  assert.fail("globals.css: balanslanmagan CSS blok — fayl buzilgan");
  return "";
}

/** `@theme` blokining tanasi (birinchi va yagona bo'lishi kutiladi). */
function themeBlock() {
  const m = css.match(/@theme[^{]*\{/);
  assert.ok(m, "globals.css: `@theme` bloki topilmadi");
  return extractCssBlock(css, m.index + m[0].length - 1);
}

/** `[data-theme="X"]` scope bloki va uning fayldagi boshlanish indeksi. */
function scopeBlock(theme) {
  const selector = `[data-theme="${theme}"]`;
  const at = css.indexOf(selector);
  assert.ok(at >= 0, `globals.css: ${selector} scope bloki topilmadi`);
  const open = css.indexOf("{", at);
  assert.ok(open > at, `globals.css: ${selector} dan keyin '{' topilmadi`);
  return { start: at, body: extractCssBlock(css, open) };
}

/** Blok tanasida E'LON QILINGAN `--color-*` nomlari (takrorsiz, tartiblangan). */
function colorTokenNames(blockBody) {
  const names = [...blockBody.matchAll(/(--color-[a-z-]+)\s*:/g)].map(
    (m) => m[1],
  );
  return [...new Set(names)].sort();
}

/** `@layer ... { ... }` bloklarining [start, end] oraliqlari. */
function layerRanges() {
  const ranges = [];
  for (const m of css.matchAll(/@layer\b[^{;]*\{/g)) {
    const open = m.index + m[0].length - 1;
    const block = extractCssBlock(css, open);
    ranges.push([m.index, open + block.length]);
  }
  return ranges;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — REYESTRLAR VA DETEKTOR MEXANIZMI                               */
/* -------------------------------------------------------------------------- */

test("reyestrlar: uzunlik, takrorsizlik, quyi chegara", () => {
  assert.deepEqual([...THEME_REGISTRY].sort(), ["dark", "light", "sun"]);
  assert.equal(new Set(THEME_REGISTRY).size, THEME_REGISTRY.length);
  assert.deepEqual([...SCOPED_THEMES].sort(), ["dark", "sun"]);
  assert.equal(TEXT_TOKEN_FAMILY.length, 4);
  assert.equal(new Set(TEXT_TOKEN_FAMILY).size, TEXT_TOKEN_FAMILY.length);
});

test("(a-nazorat) detektor sun'iy IJOBIY manbani USHLAYDI, obyekt kalitini USHLAMAYDI", () => {
  // Haqiqiy variant — cn( ichida: USHLANISHI SHART.
  assert.deepEqual(findDarkVariants(`const a = cn("bg-bg dark:bg-black");`), [
    "bg-bg dark:bg-black",
  ]);
  // Haqiqiy variant — className satri: USHLANISHI SHART.
  assert.deepEqual(
    findDarkVariants(`<div className="p-2 dark:text-white" />`),
    ["p-2 dark:text-white"],
  );
  // Shartli obyekt KALITI satr sifatida (clsx uslubi) — bu ham brauzerga
  // yetib boradigan klass: USHLANISHI SHART.
  assert.deepEqual(
    findDarkVariants(`cn({ "dark:bg-black": active })`),
    ["dark:bg-black"],
  );
  // Obyekt kaliti KOD sifatida (gistogramma/schema) — variant EMAS:
  // capture-cell.tsx:106 / api-types.ts:1400 sinfi USHLANMAYDI.
  assert.deepEqual(findDarkVariants(`const chart = { dark: 1 };`), []);
  assert.deepEqual(findDarkVariants(`const s = { dark: z.number() };`), []);
  // `className=` dan tashqaridagi satr ham ushlanmaydi (chegara isboti).
  assert.deepEqual(findDarkVariants(`const label = "dark:ish-matn";`), []);
});

/* -------------------------------------------------------------------------- */
/* (a) — `dark:` VARIANTI 0 MARTA                                             */
/* -------------------------------------------------------------------------- */

test("G-motion-4(a): `dark:` varianti className=/cn( ichida 0 marta — butun components/ va app/", () => {
  const files = SCAN_DIRS.flatMap((dir) => listProductFiles(dir));
  assert.ok(
    files.length >= MIN_SCANNED_FILES,
    `skan qamrovida atigi ${files.length} fayl (kutilgan: >=${MIN_SCANNED_FILES}) — ` +
      "katalog ko'chganmi? Darvoza bo'sh to'plam ustida ishlayapti",
  );

  const hits = [];
  for (const file of files) {
    const found = findDarkVariants(readCode(file));
    if (found.length > 0) {
      hits.push(`${path.relative(SRC, file)}: ${found.join(" · ")}`);
    }
  }
  assert.deepEqual(
    hits,
    [],
    "`dark:` Tailwind varianti topildi — tema TOKEN-SCOPE bilan almashadi, " +
      "variant bilan emas (09-UI-SPEC §11.3)",
  );
});

test("G-motion-4(a): `@custom-variant dark` globals.css'da 0 marta", () => {
  assert.deepEqual(
    [...css.matchAll(/@custom-variant\s+dark/g)].map((m) => m[0]),
    [],
    "`@custom-variant dark` topildi — u `dark:` variantini qonuniylashtirardi",
  );
});

/* -------------------------------------------------------------------------- */
/* (b) — `@theme inline` 0 MARTA                                              */
/* -------------------------------------------------------------------------- */

test("G-motion-4(b): `@theme inline` 0 marta — scope override tirikligining sharti", () => {
  assert.deepEqual(
    [...css.matchAll(/@theme\s+inline/g)].map((m) => m[0]),
    [],
    "`@theme inline` topildi — `inline` utilitani var() o'rniga QIYMATGA " +
      "kompilyatsiya qiladi va [data-theme] override JIMGINA o'lardi " +
      "(09-RESEARCH Naqsh 1)",
  );
});

/* -------------------------------------------------------------------------- */
/* (c) — SCOPE TOKENLARI: QISM TO'PLAM + *-text OILASI + QATLAMSIZLIK         */
/* -------------------------------------------------------------------------- */

test("G-motion-4(c): scope'lardagi --color-* nomlari @theme to'plamining QISM to'plami", () => {
  const themeTokens = colorTokenNames(themeBlock());
  assert.ok(
    themeTokens.length >= MIN_THEME_COLOR_TOKENS,
    `@theme'da atigi ${themeTokens.length} ta --color-* token ` +
      `(kutilgan: >=${MIN_THEME_COLOR_TOKENS}) — blok qisqarganmi?`,
  );

  for (const theme of SCOPED_THEMES) {
    const scopeTokens = colorTokenNames(scopeBlock(theme).body);
    const unknown = scopeTokens.filter((name) => !themeTokens.includes(name));
    assert.deepEqual(
      unknown,
      [],
      `[data-theme="${theme}"] scope'ida @theme'da YO'Q token bor — imlo ` +
        "xatosi: u hech qanday utilitaga ulanmagan, jimgina bezak bo'lib qoladi",
    );
  }
});

test("G-motion-4(c): --color-*-text oilasi TO'RTALASI ikkala scope'da HAM (M-18)", () => {
  for (const theme of SCOPED_THEMES) {
    const scopeTokens = colorTokenNames(scopeBlock(theme).body);
    assert.deepEqual(
      TEXT_TOKEN_FAMILY.filter((name) => scopeTokens.includes(name)),
      TEXT_TOKEN_FAMILY,
      `[data-theme="${theme}"] scope'ida *-text oilasi TO'LIQ emas — ` +
        "yetishmagan token bazaga tushib, tint fonida AA'dan yiqiladi " +
        "(09-01 buni uch marta O'LCHAB ko'rsatdi)",
    );
  }
});

test("G-motion-4(c): ikkala scope ham @layer TASHQARISIDA — kaskad g'olibligi", () => {
  const ranges = layerRanges();
  assert.ok(
    ranges.length >= 2,
    "globals.css'da @layer bloklari topilmadi — parse buzilgan " +
      "(base va components bo'lishi kutiladi)",
  );

  for (const theme of SCOPED_THEMES) {
    const { start } = scopeBlock(theme);
    const inside = ranges.filter(([from, to]) => start > from && start < to);
    assert.deepEqual(
      inside,
      [],
      `[data-theme="${theme}"] scope'i @layer ICHIDA — qatlamli CSS ` +
        "qatlamsizdan yutqazadi va override JIMGINA o'lardi (09-RESEARCH Naqsh 1)",
    );
  }
});

/* -------------------------------------------------------------------------- */
/* (d) — REYESTR UCH MANBADAN: CSS + THEMES + MESSAGES                        */
/* -------------------------------------------------------------------------- */

test("G-motion-4(d): CSS scope selektorlari reyestri — baza light + scope'lar = 3 a'zo", () => {
  const scopeNames = [
    ...new Set([...css.matchAll(/\[data-theme="([a-z]+)"\]/g)].map((m) => m[1])),
  ].sort();
  assert.deepEqual(
    scopeNames,
    [...SCOPED_THEMES].sort(),
    "globals.css scope selektorlari {dark, sun} emas — to'rtinchi tema " +
      "qo'shilgan yoki birortasi yo'qolgan",
  );
  // `light` — bazaviy holat: @theme scope'siz amal qiladi, alohida scope
  // yozilsa u ORTIQCHA ikkinchi manba bo'lardi. To'liq reyestr:
  assert.deepEqual(
    ["light", ...scopeNames].sort(),
    [...THEME_REGISTRY].sort(),
  );
});

test("G-motion-4(d): lib/theme.ts THEMES massivi — aynan {light, dark, sun}", () => {
  const code = readCode(THEME_TS);
  const m = code.match(/THEMES\s*=\s*\[([^\]]*)\]/);
  assert.ok(m, "lib/theme.ts: `THEMES = [...]` e'loni topilmadi");
  const themes = [...m[1].matchAll(/"([a-z]+)"/g)].map((x) => x[1]);
  assert.deepEqual(
    themes,
    THEME_REGISTRY,
    "lib/theme.ts THEMES reyestri {light, dark, sun} emas",
  );
});

test("G-motion-4(d): theme.* kalitlari UCHALA locale'da to'plam tengligi bilan", () => {
  for (const locale of ["uz-Latn", "uz-Cyrl", "ru"]) {
    const messages = JSON.parse(
      readFileSync(path.join(MESSAGES_DIR, `${locale}.json`), "utf8"),
    );
    assert.ok(
      messages.theme,
      `messages/${locale}.json: \`theme\` fazoviy nomi yo'q`,
    );
    assert.deepEqual(
      Object.keys(messages.theme).sort(),
      THEME_MESSAGE_KEYS,
      `messages/${locale}.json: theme.* kalitlari {label, light, dark, sun} emas`,
    );
  }
});

/* -------------------------------------------------------------------------- */
/* (e) — LAYOUT: suppressHydrationWarning + <head> INLINE SKRIPT              */
/* -------------------------------------------------------------------------- */

test("G-motion-4(e): layout.tsx — suppressHydrationWarning va <head> inline skripti", () => {
  const code = readCode(LAYOUT_TSX);

  assert.ok(
    code.includes("suppressHydrationWarning"),
    "layout.tsx: `suppressHydrationWarning` yo'q — inline skript atributni " +
      "React'dan oldin o'zgartiradi va React nomuvofiqlikni «tuzatib» " +
      "temani qayta light'ga qaytarardi",
  );
  assert.ok(
    code.includes("<head>"),
    "layout.tsx: `<head>` elementi yo'q — skript bloklovchi bo'lishi uchun " +
      "head ichida turishi shart (body'da kech — FOUC ko'rinadi)",
  );
  assert.ok(
    code.includes("dangerouslySetInnerHTML"),
    "layout.tsx: inline skript yo'q — saqlangan tema birinchi bo'yashda " +
      "qo'llanmaydi (FOUC)",
  );
});

test("G-motion-4(e): skriptda `sbozor-theme` va uchala reyestr qiymati LITERAL qat'iy solishtiruvda", () => {
  const code = readCode(LAYOUT_TSX);

  assert.ok(
    code.includes(`"sbozor-theme"`),
    "layout.tsx: `sbozor-theme` kaliti literal ko'rinmaydi — skript " +
      "boshqa kalitdan o'qiyapti (lib/theme.ts bilan ajralgan)",
  );

  // Skriptdagi qat'iy solishtiruv qiymatlari TO'PLAM sifatida reyestrga teng:
  // to'rtinchi qiymat qo'shilsa ham, birortasi olib tashlansa ham qizaradi.
  // Bu «localStorage'dagi ixtiyoriy satr data-theme'ga o'ta olmaydi»ning
  // mexanik isboti (T-09-01): atribut FAQAT shu uch literal orqali yoziladi.
  const comparisons = [
    ...new Set([...code.matchAll(/t==="([a-z]+)"/g)].map((m) => m[1])),
  ].sort();
  assert.deepEqual(
    comparisons,
    [...THEME_REGISTRY].sort(),
    "layout.tsx skriptidagi qat'iy solishtiruv qiymatlari reyestr bilan " +
      "TENG EMAS — validatsiya bo'shagan yoki reyestrdan chetlangan",
  );
});

test("G-motion-4(e): lib/theme.ts ham AYNAN shu localStorage kalitini ishlatadi", () => {
  const code = readCode(THEME_TS);
  assert.ok(
    code.includes(`"sbozor-theme"`),
    "lib/theme.ts: `sbozor-theme` literal yo'q — skript va hook har xil " +
      "kalitga yozsa, tanlov saqlanib «tiklanmaydigan» bo'lib qolardi",
  );
});
