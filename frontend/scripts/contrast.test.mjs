#!/usr/bin/env node
/**
 * G-motion-5 (09-UI-SPEC §5.5, §16.4) — KONTRAST: DA'VO EMAS, O'LCHOV.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — UCH XIL NARSA, BITTA MEXANIZM.
 *
 * 1. ⛔ E'LON QILINGAN JUFTLIKLAR REYESTRI (b). `globals.css` dan `oklch()`
 *    qiymatlari PARSE qilinadi (qo'lda ko'chirilmaydi) va WCAG 2.x nisbati
 *    uchala temada hisoblanadi: matn juftliklari >=4.5:1, chegara
 *    juftliklari >=3:1. Tema scope'i hali tug'ilmagan bo'lsa, reyestr mavjud
 *    temalar ustida ishlaydi va TEMA SONI testi uni to'liqlikka majburlaydi.
 *
 * 2. ⛔ IZOHLAR — MASHINA O'QIYDIGAN DA'VO (c). `globals.css` izohlaridagi
 *    HAR `N.NN:1` soni topiladi va hisoblangan qiymat bilan ±0.01 da
 *    solishtiriladi. Eskirgan izoh keyingi ijrochiga YOLG'ON gapiradi —
 *    08-fazaning butun madaniyati shunga qarshi (T-09-09).
 *
 * 3. ⛔ M-19 REGRESSIYA QULFI (d). `bg-accent` bilan `text-accent-text`
 *    BITTA satr literalida — butun `src/` bo'ylab 0 marta. Bu juftlik
 *    o'lchandi: 1.28:1 — matn deyarli ko'rinmaydi (T-09-10).
 *
 * =============================================================================
 * ⛔⛔ GAMUT SIYOSATI — E'LON QILINGAN QAROR, ixtiyoriy detal EMAS.
 *
 *    OKLCH -> sRGB o'girishda qiymat GAMMA fazoda [0,1] ga KESILADI.
 *    `--color-accent` (0.56 0.19 255) sRGB gamutdan TASHQARIDA [O'LCHANDI:
 *    gamma -0.05] — siyosatsiz ikki implementatsiya ikki xil son berardi.
 *    Aynan shu siyosat M-19 ning ikkala da'vosini (1.28 va 4.72) AYNAN
 *    qaytardi [09-RESEARCH Tuzoq 2]. O'zgartirilsa, quyidagi SELF_CHECK
 *    jadvali qizaradi — ya'ni siyosat testning o'zida qulflangan.
 *
 * ⛔ ALFA-KOMPOZITSIYA GAMMA (sRGB) FAZODA: brauzer `bg-accent/10` ni shu
 *    fazoda aralashtiradi. Alfalar mahsulotdagi ishlatishdan: accent/10,
 *    success/12, warning/20, danger/12.
 *
 * -----------------------------------------------------------------------
 * NEGA RANG KUTUBXONASI (culori / colorjs.io) QO'SHILMAYDI
 * -----------------------------------------------------------------------
 * Kerak bo'lgan narsa — OKLab matritsalari + sRGB gamma + WCAG formulasi,
 * ~30 qator arifmetika. Paket uchta narxni olib kelardi: bundl, tranzitiv
 * daraxt, yangilanish yuki (C-6, `gate:fast` byudjeti 200 s). Formulaning
 * to'g'riligi paket obro'si bilan emas, quyidagi SELF_CHECK jadvalining
 * QO'LDA TASDIQLANGAN qiymatlari bilan ta'minlanadi (09-UI-SPEC ning 15
 * da'vosidan 13 tasi shu kod bilan AYNAN takrorlangan).
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (D-32): `src/` daraxti `readdirSync`
 *   bilan REKURSIV o'qiladi, `.test.` fayllar chiqariladi, fayl soni QUYI
 *   chegara bilan qo'riqlanadi.
 *
 * Ishlatish:
 *   node --test scripts/contrast.test.mjs        — darvoza
 *   node scripts/contrast.test.mjs --print       — izoh generatsiyasi:
 *     e'lon qilingan juftliklar reyestri tema bo'yicha hisoblanadi va
 *     `globals.css` ga tayyor izoh qatorlari («WCAG 1.4.3. juftlik: N.NN:1»
 *     shakli, CSS izohiga o'ralgan) chiqadi.
 *     ⛔ Izohdagi son SHU chiqishdan ko'chiriladi, 09-UI-SPEC jadvalidan
 *     EMAS (09-RESEARCH Tuzoq 2: SPEC raqamlari tasdiqlanmagan da'vo).
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";
import process from "node:process";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");
const GLOBALS = path.join(SRC, "app", "globals.css");

/* -------------------------------------------------------------------------- */
/* KALKULYATOR — 09-RESEARCH «Kod namunalari 5» dan KO'CHIRILGAN              */
/* (qayta ixtiro qilinmagan; OKLab matritsalari Björn Ottosson e'loni)        */
/* -------------------------------------------------------------------------- */

function oklchToLinear(L, C, Hdeg) {
  const h = (Hdeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const enc = (v) => (v <= 0.0031308 ? 12.92 * v : 1.055 * Math.pow(v, 1 / 2.4) - 0.055);
const dec = (v) => (v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4));

/* ⛔ GAMUT SIYOSATI: gamma fazoda [0,1] ga kesish (modul docstringiga qarang). */
const clamp01 = (v) => Math.min(1, Math.max(0, v));

/** OKLCH -> gamma-sRGB (kesilgan). Kompozitsiya SHU fazoda bo'ladi. */
function toGamma([L, C, H]) {
  return oklchToLinear(L, C, H).map(enc).map(clamp01);
}

function luminanceOfGamma(gamma) {
  const lin = gamma.map(dec);
  return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
}

function relativeLuminance(color) {
  return luminanceOfGamma(toGamma(color));
}

/** WCAG 2.x kontrast nisbati — ikkala argument [L, C, H]. */
function contrastRatio(fg, bg) {
  const a = relativeLuminance(fg);
  const b = relativeLuminance(bg);
  const hi = Math.max(a, b);
  const lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}

/** Tint: `alpha`·rang + (1−alpha)·ostki — GAMMA fazoda (brauzer kabi). */
function compositeGamma(topColor, alpha, underColor) {
  const top = toGamma(topColor);
  const under = toGamma(underColor);
  return top.map((v, i) => alpha * v + (1 - alpha) * under[i]);
}

/** Matnning kompozit (gamma) fon ustidagi nisbati. */
function contrastOnComposite(fg, compositeBg) {
  const a = relativeLuminance(fg);
  const b = luminanceOfGamma(compositeBg);
  const hi = Math.max(a, b);
  const lo = Math.min(a, b);
  return (hi + 0.05) / (lo + 0.05);
}

/* -------------------------------------------------------------------------- */
/* `globals.css` PARSE — token jadvali va tema scope'lari                     */
/* -------------------------------------------------------------------------- */

const OKLCH_RE = /^oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*[\d.%]+\s*)?\)$/u;

function stripCssComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//gu, "");
}

/**
 * `marker { ... }` blokining ICHKI matni — qavs sanog'i bilan.
 *
 * ⛔ `marker` dan keyin FAQAT bo'shliq va `{` kelishi shart (260819):
 *    aks holda `[data-theme="dark"] .sinf { … }` ko'rinishidagi BEZAK
 *    qoidasi token bloki o'rniga topilib, darvoza yolg'on qizil
 *    berardi (o'lchandi: ish yuzasi foni qo'shilganda).
 */
function extractBlock(source, marker) {
  const escaped = marker.replace(/[.*+?^${}()|[\]\\]/gu, "\\$&");
  const match = new RegExp(`${escaped}\\s*\\{`, "u").exec(source);
  if (match === null) return null;
  const start = match.index;
  const open = start + match[0].length - 1;
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  return null;
}

/** Blokdagi `--color-*: oklch(...)` deklaratsiyalari -> { qisqaNom: [L,C,H] }. */
function parseColorTokens(block) {
  const tokens = {};
  for (const m of block.matchAll(/--([a-zA-Z][\w-]*)\s*:\s*([^;]+);/gu)) {
    const value = m[2].trim();
    const parsed = OKLCH_RE.exec(value);
    if (parsed === null) continue; // soya/motion tokenlari rang emas
    const name = m[1].startsWith("color-") ? m[1].slice("color-".length) : m[1];
    tokens[name] = [Number(parsed[1]), Number(parsed[2]), Number(parsed[3])];
  }
  return tokens;
}

/** Uchala temaning HAL QILINGAN token jadvallari (scope YO'Q bo'lsa tema ham yo'q). */
function readThemes() {
  const raw = readFileSync(GLOBALS, "utf8");
  const source = stripCssComments(raw);

  const themeBlock = extractBlock(source, "@theme");
  assert.ok(themeBlock !== null, "`globals.css` da `@theme` bloki topilmadi — parser yoki fayl buzilgan");
  const base = parseColorTokens(themeBlock);

  const themes = { light: base };
  for (const scope of ["dark", "sun"]) {
    const block = extractBlock(source, `[data-theme="${scope}"]`);
    if (block !== null) {
      themes[scope] = { ...base, ...parseColorTokens(block) };
    }
  }
  return { raw, themes };
}

/* -------------------------------------------------------------------------- */
/* E'LON QILINGAN JUFTLIKLAR REYESTRI (G-motion-5(b) ning manbai)             */
/* -------------------------------------------------------------------------- */

const TEXT_AA = 4.5; // WCAG 1.4.3
const BORDER_AA = 3.0; // WCAG 1.4.11

/**
 * ⛔ Reyestr — matn/fon va chegara/fon juftliklari. `alpha` bor bo'lsa fon
 *    `bg` tokenining TEMA SURFACE'i ustidagi tinti (gamma-kompozitsiya).
 *    Alfalar mahsulotdagi ishlatishdan: `bg-accent/10`, `bg-success/12`,
 *    `bg-warning/20`, `bg-danger/12`.
 */
const PAIR_REGISTRY = [
  { fg: "text", bg: "bg", min: TEXT_AA },
  { fg: "text", bg: "surface", min: TEXT_AA },
  { fg: "text-muted", bg: "bg", min: TEXT_AA },
  { fg: "text-muted", bg: "surface-muted", min: TEXT_AA },
  { fg: "accent-fg", bg: "accent", min: TEXT_AA },
  { fg: "success-fg", bg: "success", min: TEXT_AA }, // M-20 — latent tuzoq ham reyestrda
  { fg: "warning-fg", bg: "warning", min: TEXT_AA },
  { fg: "danger-fg", bg: "danger", min: TEXT_AA },
  { fg: "accent-text", bg: "accent", alpha: 0.1, min: TEXT_AA },
  { fg: "success-text", bg: "success", alpha: 0.12, min: TEXT_AA },
  { fg: "warning-text", bg: "warning", alpha: 0.2, min: TEXT_AA },
  { fg: "danger-text", bg: "danger", alpha: 0.12, min: TEXT_AA },
  { fg: "border-ui", bg: "surface", min: BORDER_AA },
  { fg: "border-ui", bg: "bg", min: BORDER_AA },
  { fg: "border-ui", bg: "surface-muted", min: BORDER_AA },
];

/**
 * Reyestrning QUYI chegarasi (09-UI-SPEC G-motion-5(b): >=12 juftlik).
 * ⚠ Usiz reyestr bo'shatilsa darvoza bo'sh to'plam ustida abadiy yashil
 *   qolardi (collect-surface naqshi).
 */
const MIN_PAIRS = 12;

function pairId(pair) {
  return `${pair.fg}/${pair.bg}${pair.alpha ? `@${Math.round(pair.alpha * 100)}` : ""}`;
}

/**
 * Juftlik nisbati — istalgan tema jadvalida. `fg`/`bg` topilmasa xato
 * OTILADI (jimgina o'tkazib yuborilmaydi: yo'q token — yo'q o'lchov).
 */
function computePair(tokens, { fg, bg, alpha }) {
  for (const name of alpha ? [fg, bg, "surface"] : [fg, bg]) {
    assert.ok(
      tokens[name] !== undefined,
      `token topilmadi: \`--color-${name}\` — juftlik o'lchab bo'lmaydi (reyestr yoki scope buzilgan)`,
    );
  }
  if (alpha) {
    return contrastOnComposite(tokens[fg], compositeGamma(tokens[bg], alpha, tokens.surface));
  }
  return contrastRatio(tokens[fg], tokens[bg]);
}

/* -------------------------------------------------------------------------- */
/* --print REJIMI — izoh generatsiyasi (G-motion-5(c) ning YAGONA manbai)     */
/* -------------------------------------------------------------------------- */

/**
 * Reyestrdan TASHQARI, hujjatlash uchun foydali da'volar. Ular chegara
 * testiga KIRMAYDI (ba'zilari ataylab yiqiladi — taqiq dalili), lekin
 * izohda yozilsa (c) ularni ham ±0.01 da tekshiradi.
 */
const EXTRA_PRINT_CLAIMS = [
  { fg: "border", bg: "surface", note: "dekorativ chegara — SC 1.4.11 QO'LLANMAYDI" },
  { fg: "warning", bg: "surface", note: "TAQIQ dalili: warning MATN sifatida o'tmaydi" },
  { fg: "text", bg: "warning", alpha: 0.2, note: "sariq tintdagi to'g'ri matn — text" },
];

function printClaims() {
  const { themes } = readThemes();
  const lines = [];
  for (const [themeName, tokens] of Object.entries(themes)) {
    const prefix = themeName === "light" ? "" : `[${themeName}] `;
    lines.push(`/* === tema: ${themeName} — reyestr juftliklari === */`);
    for (const pair of PAIR_REGISTRY) {
      const ratio = computePair(tokens, pair);
      const sc = pair.min === BORDER_AA ? "1.4.11" : "1.4.3";
      lines.push(`/* WCAG ${sc}. ${prefix}${pairId(pair)}: ${ratio.toFixed(2)}:1 */`);
    }
    if (themeName === "light") {
      lines.push(`/* === tema: ${themeName} — qo'shimcha hujjat da'volari === */`);
      for (const claim of EXTRA_PRINT_CLAIMS) {
        const ratio = computePair(tokens, claim);
        lines.push(`/* WCAG 1.4.3. ${pairId(claim)}: ${ratio.toFixed(2)}:1  (${claim.note}) */`);
      }
    }
  }
  process.stdout.write(lines.join("\n") + "\n");
}

if (process.argv.includes("--print")) {
  printClaims();
  process.exit(0);
}

/* -------------------------------------------------------------------------- */
/* (a) KALKULYATOR O'Z-O'ZINI TEKSHIRUVI — olti MA'LUM qiymat                 */
/* -------------------------------------------------------------------------- */

/**
 * Kutilgan qiymatlar QO'LDA TASDIQLANGAN o'lchovlar (09-UI-SPEC M-16/M-19,
 * 09-RESEARCH «Kod namunalari 5» jadvali). Tokenlar esa `globals.css` dan
 * PARSE qilinadi — ya'ni bu jadval ham kalkulyatorni, ham parserni, ham
 * gamut siyosatini BIR VAQTDA o'lchaydi. Token qiymati o'zgarsa jadval
 * `--print` chiqishidan QAYTA generatsiya qilinadi (Tuzoq 2).
 */
const SELF_CHECK = [
  ["accent-text", "accent", 1.28, "M-19 NUQSON — (d) qulflagan juftlik; tokenlar o'zgarmagan"],
  ["accent-fg", "accent", 4.72, "M-19 tuzatishi — to'g'ri token"],
  /* ⚠ Quyidagi ikkitasi 09-01 T3 da ILIQ BAZA uchun qayta generatsiya
   * qilindi (M-17): sovuq bazada 4.81 va 3.32 edi. Manba — `--print`. */
  ["text-muted", "surface-muted", 4.84, "M-16 -> M-17 (iliq surface-muted)"],
  ["border-ui", "surface", 3.64, "M-16 (surface o'zgarmagan)"],
  ["border-ui", "bg", 3.49, "M-16 -> M-17 (iliq bg — nisbat aynan saqlanadi)"],
  ["border-ui", "surface-muted", 3.34, "M-16 -> M-17 (iliq surface-muted)"],
];

const TOLERANCE = 0.01 + 1e-9;

test("G-motion-5(a): kalkulyator oltita ma'lum qiymatni ±0.01 da takrorlaydi (parse + matematika + gamut)", () => {
  const { themes } = readThemes();
  const tokens = themes.light;
  for (const [fg, bg, expected, why] of SELF_CHECK) {
    const actual = computePair(tokens, { fg, bg });
    assert.ok(
      Math.abs(actual - expected) <= TOLERANCE,
      `\`${fg}/${bg}\` kutilgan ${expected}, hisoblandi ${actual.toFixed(4)} (${why}).\n` +
        "  Farq >0.01 — yo token o'zgargan (izohlarni `--print` dan qayta generatsiya qiling),\n" +
        "  yo kalkulyator/gamut siyosati buzilgan.",
    );
  }
});

test("G-motion-5(a): parser `@theme` ni yutib yubormaydi (quyi chegara)", () => {
  const { themes } = readThemes();
  const count = Object.keys(themes.light).length;
  const MIN_BASE_TOKENS = 20; // bugun 22 ta `--color-*` oklch tokeni bor
  assert.ok(
    count >= MIN_BASE_TOKENS,
    `\`@theme\` dan atigi ${count} ta rang tokeni o'qildi (kutilgan: >=${MIN_BASE_TOKENS}) — ` +
      "parser buzilgan bo'lsa, keyingi barcha o'lchov bo'sh to'plam ustida yashil qolardi",
  );
});

test("sun'iy-IJOBIY nazorat: bilib turib buzilgan juftlik chegaradan O'TMAYDI", () => {
  /*
   * ⛔ Usiz «hamma juftlik >=4.5» xulosasi HAR DOIM 10 qaytaradigan buzuq
   *    kalkulyator ustida ham rost bo'lardi. `accent-text`/`accent` (to'yingan
   *    fon ustida tint-matn tokeni) — o'lchangan 1.28, ya'ni reyestrga
   *    tushsa darvoza QIZARADI. Bu — detektorning tirikligi isboti.
   */
  const { themes } = readThemes();
  const broken = computePair(themes.light, { fg: "accent-text", bg: "accent" });
  assert.ok(
    broken < TEXT_AA,
    `buzilgan juftlik ${broken.toFixed(2)} berdi — u ${TEXT_AA} dan KICHIK bo'lishi shart edi; ` +
      "kalkulyator past nisbatni ko'rmayapti, ya'ni butun darvoza o'lchamayapti",
  );
});

test("reyestr tuzilishi: quyi chegara va takror nazorati", () => {
  assert.ok(
    PAIR_REGISTRY.length >= MIN_PAIRS,
    `juftliklar reyestrida atigi ${PAIR_REGISTRY.length} ta juftlik bor (kutilgan: >=${MIN_PAIRS})`,
  );
  const ids = PAIR_REGISTRY.map(pairId);
  assert.equal(
    new Set(ids).size,
    ids.length,
    "reyestrda takrorlangan juftlik bor — uzunlik chegarasi aldangan bo'lardi",
  );
});

/* -------------------------------------------------------------------------- */
/* (d) M-19 REGRESSIYA QULFI — `bg-accent` + `text-accent-text` birga 0 marta */
/* -------------------------------------------------------------------------- */

const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];
const TEST_FILE = /\.test\.(?:ts|tsx|js|jsx|mjs)$/u;

/**
 * Qamrovning QUYI chegarasi: skanerlanadigan mahsulot fayllari soni.
 * Bugun ~180 [09-01 PLAN]; kamaysa skan jimgina toraygan — darvoza qizaradi.
 */
const MIN_SCANNED_FILES = 150;

/** Satr literallari MAZMUNI — izohlar tashlanadi, escape hisobga olinadi. */
function stringLiterals(source) {
  const found = [];
  let state = "code";
  let current = "";
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
        current = "";
        i += 1;
      } else {
        i += 1;
      }
      continue;
    }
    if (state === "line") {
      if (c === "\n") state = "code";
      i += 1;
      continue;
    }
    if (state === "block") {
      if (c === "*" && next === "/") {
        state = "code";
        i += 2;
      } else {
        i += 1;
      }
      continue;
    }
    // satr ichida: `state` — ochuvchi belgi
    if (c === "\\") {
      current += next ?? "";
      i += 2;
      continue;
    }
    if (c === state) {
      found.push(current);
      state = "code";
      i += 1;
      continue;
    }
    current += c;
    i += 1;
  }
  return found;
}

/**
 * ⛔ TOKEN-ANIQ tekshiruv: `bg-accent/10` (qonuniy tint, badge/stall-tone)
 *    `bg-accent` EMAS — shuning uchun satr bo'shliq bo'yicha tokenlarga
 *    bo'linadi va AYNAN `bg-accent` qidiriladi.
 */
function hasForbiddenCombo(literal) {
  const tokens = literal.split(/\s+/u);
  return tokens.includes("bg-accent") && tokens.includes("text-accent-text");
}

function listProductFiles(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full));
    } else if (CODE_EXTENSIONS.includes(path.extname(entry)) && !TEST_FILE.test(entry)) {
      found.push(full);
    }
  }
  return found;
}

test("skaner sun'iy IJOBIY va SALBIY nazoratdan o'tadi", () => {
  /* Detektor tirikligi — bo'sh detektor bilan «0 marta» abadiy rost bo'lardi. */
  assert.equal(hasForbiddenCombo("rounded-md bg-accent px-4 text-accent-text"), true);
  assert.equal(
    hasForbiddenCombo("bg-accent/10 text-accent-text font-semibold"),
    false,
    "qonuniy tint (`bg-accent/10`) noto'g'ri ushlandi — token-aniqlik buzilgan",
  );
  assert.equal(hasForbiddenCombo("bg-accent text-accent-fg"), false);

  /* Izohdagi juftlik satr EMAS — skan uni ko'rmaydi. */
  const strings = stringLiterals('// "bg-accent text-accent-text"\nconst ok = "bg-surface";');
  assert.deepEqual(strings, ["bg-surface"]);

  /* Escape satrni erta yopmaydi. */
  assert.deepEqual(stringLiterals('const s = "a\\"bg-accent text-accent-text";'), [
    'a"bg-accent text-accent-text',
  ]);
});

test("G-motion-5(d): `bg-accent` + `text-accent-text` bitta satr literalida — butun `src/` da 0 marta", () => {
  const files = listProductFiles(SRC);

  assert.ok(
    files.length >= MIN_SCANNED_FILES,
    `skan atigi ${files.length} ta mahsulot faylini ko'rdi (kutilgan: >=${MIN_SCANNED_FILES}) — ` +
      "qamrov toraygan, «0 marta» xulosasi endi butun yuzani anglatmaydi",
  );

  const problems = [];
  for (const file of files) {
    for (const literal of stringLiterals(readFileSync(file, "utf8"))) {
      if (hasForbiddenCombo(literal)) {
        problems.push(`${path.relative(SRC, file)} -> "${literal.trim()}"`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-5(d) BUZILDI — to'yingan aksent fonida tint-matn tokeni:\n  " +
      problems.join("\n  ") +
      "\n  Bu juftlik O'LCHANGAN: 1.28:1 — matn deyarli ko'rinmaydi (M-19).\n" +
      "  To'g'ri token — `text-accent-fg` (oq, 4.72:1). `text-accent-text` FAQAT\n" +
      "  tint (`bg-accent/10`) ustida yashaydi.",
  );
});

/* -------------------------------------------------------------------------- */
/* (b) E'LON QILINGAN JUFTLIKLAR — UCHALA TEMADA CHEGARADAN O'TADI            */
/* -------------------------------------------------------------------------- */

test("G-motion-5(b): tema reyestri TO'LIQ — light · dark · sun", () => {
  const { themes } = readThemes();
  assert.deepEqual(
    Object.keys(themes).sort(),
    ["dark", "light", "sun"],
    "`globals.css` da uchala tema scope'i bo'lishi shart — yo'q scope'ning " +
      "tokenlari standartga tushib, jimgina noto'g'ri rang berardi (G-motion-4(c) sinfi)",
  );
});

test("G-motion-5(b): >=12 juftlik × 3 tema — matn >=4.5:1, chegara >=3:1", () => {
  const { themes } = readThemes();
  const problems = [];
  let measured = 0;

  for (const [themeName, tokens] of Object.entries(themes)) {
    for (const pair of PAIR_REGISTRY) {
      const ratio = computePair(tokens, pair);
      measured += 1;
      if (ratio < pair.min) {
        problems.push(`[${themeName}] ${pairId(pair)}: ${ratio.toFixed(2)} < ${pair.min}`);
      }
    }
  }

  assert.ok(
    measured >= MIN_PAIRS * 3,
    `atigi ${measured} ta o'lchov bajarildi (kutilgan: >=${MIN_PAIRS * 3} — ` +
      ">=12 juftlik × 3 tema) — reyestr yoki tema to'plami toraygan",
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-5(b) BUZILDI — juftlik(lar) chegaradan tushdi:\n  " +
      problems.join("\n  ") +
      "\n  ⛔ Chegara PASAYTIRILMAYDI va juftlik reyestrdan CHIQARILMAYDI —\n" +
      "  TOKEN sozlanadi va sabab `globals.css` izohida yoziladi (09-01 T3\n" +
      "  presedenti: dark accent-fg/success-text/warning-text).",
  );
});

/* -------------------------------------------------------------------------- */
/* (c) IZOHLAR — MASHINA O'QIYDIGAN DA'VO (±0.01)                             */
/* -------------------------------------------------------------------------- */

/**
 * Kanonik da'vo grammatikasi (izoh ichida):
 *   `[dark] fg/bg: N.NN:1` · `fg/bg@AA: N.NN:1`
 * `[tema]` yo'q bo'lsa — light. `@AA` — bg tokenining 0.AA alfali tinti,
 * ostki qatlam HAR DOIM o'sha temaning surface'i.
 */
const CLAIM_RE =
  /(?:\[(dark|sun)\]\s+)?([a-z][a-z-]*)\/([a-z][a-z-]*)(?:@(\d+))?:\s*(\d+\.\d{2}):1/gu;
const BARE_RATIO_RE = /\d+\.\d{2}:1/gu;

/**
 * Izohlardagi da'volar QUYI chegarasi. ⚠ Usiz barcha izoh o'chirilsa (c)
 * bo'sh to'plam ustida abadiy yashil qolardi — izohlar bu loyihada
 * hujjat emas, DA'VO (T-09-09).
 */
const MIN_CLAIMS = 4;

function commentClaims(raw) {
  const comments = [...raw.matchAll(/\/\*[\s\S]*?\*\//gu)].map((m) => m[0]);
  const claims = [];
  let bareCount = 0;
  for (const comment of comments) {
    bareCount += [...comment.matchAll(BARE_RATIO_RE)].length;
    for (const m of comment.matchAll(CLAIM_RE)) {
      claims.push({
        theme: m[1] ?? "light",
        fg: m[2],
        bg: m[3],
        alpha: m[4] === undefined ? undefined : Number(m[4]) / 100,
        claimed: Number(m[5]),
        text: m[0],
      });
    }
  }
  return { claims, bareCount };
}

test("(c) da'vo detektori sun'iy IJOBIY nazoratdan o'tadi", () => {
  const probe = commentClaims(
    "/* WCAG 1.4.3. accent-fg/accent: 4.72:1 */\n" +
      "/* WCAG 1.4.3. [dark] warning-text/warning@20: 4.63:1 */",
  );
  assert.equal(probe.claims.length, 2);
  assert.equal(probe.bareCount, 2);
  assert.deepEqual(probe.claims[1], {
    theme: "dark",
    fg: "warning-text",
    bg: "warning",
    alpha: 0.2,
    claimed: 4.63,
    text: "[dark] warning-text/warning@20: 4.63:1",
  });

  /* Kanonik bo'lmagan da'vo — bareCount > claims: (c) buni qizartiradi. */
  const loose = commentClaims("/* shunchaki 9.99:1 raqam */");
  assert.equal(loose.claims.length, 0);
  assert.equal(loose.bareCount, 1);
});

test("G-motion-5(c): izohlardagi HAR `N.NN:1` da'vosi hisoblangan qiymat bilan ±0.01 da teng", () => {
  const { raw, themes } = readThemes();
  const { claims, bareCount } = commentClaims(raw);

  assert.ok(
    claims.length >= MIN_CLAIMS,
    `izohlarda atigi ${claims.length} ta kanonik da'vo bor (kutilgan: >=${MIN_CLAIMS}) — ` +
      "izohlar o'chirilgan yoki kanonik shakldan chiqqan",
  );

  assert.equal(
    bareCount,
    claims.length,
    `izohlarda ${bareCount - claims.length} ta KANONIK BO'LMAGAN \`N.NN:1\` soni bor — ` +
      "mashina o'qiy olmaydigan da'vo tekshirilmaydigan da'vo; shakl: " +
      "`[tema] fg/bg@AA: N.NN:1` (`--print` chiqishi)",
  );

  const problems = [];
  for (const claim of claims) {
    const tokens = themes[claim.theme];
    if (tokens === undefined) {
      problems.push(`«${claim.text}» — \`${claim.theme}\` temasi topilmadi`);
      continue;
    }
    const actual = computePair(tokens, claim);
    if (Math.abs(actual - claim.claimed) > TOLERANCE) {
      problems.push(
        `«${claim.text}» — da'vo ${claim.claimed}, hisob ${actual.toFixed(2)} (farq >0.01)`,
      );
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-5(c) BUZILDI — izoh yolg'on gapiryapti:\n  " +
      problems.join("\n  ") +
      "\n  Izohdagi son KALKULYATORNING CHIQISHI bo'lishi shart: " +
      "`node scripts/contrast.test.mjs --print` yugurtiring va qiymatni ko'chiring.",
  );
});
