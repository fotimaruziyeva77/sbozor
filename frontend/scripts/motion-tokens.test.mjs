#!/usr/bin/env node
/**
 * G-motion-1(a,b,d) + G-motion-3(a,b,c,d) (09-UI-SPEC §16.4) — MOTION
 * QATLAMINING STATIK CHEGARASI.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — TO'RT XIL NARSA, BITTA MEXANIZM.
 *
 * 1. ⛔ REDUCED-MOTION HURMATI (G-motion-1(a,b), ROADMAP SC#4, T-09-06).
 *    (a) `globals.css` dagi `@media (prefers-reduced-motion: reduce)` bloki
 *    PARSE qilinadi (`grep` emas — izohdagi matn ham topilardi) va undan
 *    `animation-duration` HAM, `transition-duration` HAM `!important` bilan
 *    <=0.01ms ga tushirilgani o'lchanadi. (b) `components/**` dagi HAR bare
 *    `animate-*` utilitasi AYNI satrda `motion-reduce:` juftligiga ega.
 *    Vestibulyar buzilishi bo'lgan foydalanuvchi uchun bu a11y talabi,
 *    sozlama emas.
 *
 * 2. ⛔ KONFETTI IJRO ETILMAGANI (G-motion-1(d), 09-UI-SPEC §9).
 *    Tetikning haqiqat manbai (server bayrog'i) mavjud emas — shartnoma
 *    yozilgan, ijro YO'Q (sabab: deferred-items.md). `components/**` da
 *    `confetti`/`konfetti`/`burst`/`particle` ta'rifi 0 marta.
 *
 * 3. ⛔ FAQAT GPU XOSSALARI + BITTA HAQIQAT MANBAI (G-motion-3(a,b,c),
 *    ROADMAP SC#5, T-09-11, T-09-12). `@keyframes` bloklari faqat ruxsat
 *    etilgan (kompozitor-do'st) xossalarni ishlatadi — `width`/`height`
 *    animatsiyasi arzon Androidda har kadrda layout hisobini qo'zg'ab
 *    60fps ni o'ldiradi. Davomiyliklar komponentda takrorlanmaydi
 *    (`duration-<raqam>` 0), `@keyframes` FAQAT `globals.css` da.
 *
 * 4. ⛔ BOG'LIQLIK BYUDJETI 0 KB (G-motion-3(d), L-8, T-09-SC).
 *    `package.json` `dependencies` kalitlari 18 nomli reyestrga TO'PLAM
 *    TENGLIGI bilan teng. ⛔ SON bilan yozilmaydi (`length === N`): son
 *    paket ALMASHTIRILGANDA (biri chiqib, biri kirganda) yolg'on yashil
 *    qolardi. Bu fazada `npm install` bajarilmaydi — slopsquatting yuzasi
 *    nol.
 * =============================================================================
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (D-32): kataloglar `readdirSync`
 *   bilan REKURSIV o'qiladi, `.test.` fayllar chiqariladi, fayl soni QUYI
 *   chegara bilan qo'riqlanadi.
 *
 * ⚠ TO'PLAM TENGLIGI, `not.toContain` EMAS (D-31): taqiqlangan paket
 *   ro'yxati faqat XATO XABARIDA ishlatiladi — o'lchovning o'zi to'plam
 *   tengligi, ya'ni HAR QANDAY yangi nom (taqiq ro'yxatida bo'lmasa ham)
 *   darvozani qizartiradi.
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN QIDIRILADI — filtrsiz «bu yerda
 *   `duration-150` yozilmaydi» degan izohning O'ZI darvozani qizartirardi.
 *   JS filtri `collect-surface.test.mjs` dagi holat mashinasining nusxasi
 *   (u ham `bulk-action-surface.test.mjs:163-225` dan ko'chirilgan —
 *   06-UI-SPEC W0-F4 konvensiyasi); CSS filtri `contrast.test.mjs` dagi
 *   regeks bilan bir xil.
 *
 * ⚠ TASHQI PAKET YO'Q — `postcss` IMPORT QILINMAYDI: sof matn skani
 *   `gate:fast` byudjetiga (200 s) sezilmas qo'shiladi.
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");
const GLOBALS = path.join(SRC, "app", "globals.css");
const COMPONENTS = path.join(SRC, "components");
const PACKAGE_JSON = path.join(FRONTEND_ROOT, "package.json");

/** Skanerlanadigan kengaytmalar (komponent skani). */
const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

/** Mahsulot fayli emas — qamrovdan chiqadi (u taqiqni O'LCHAYDI, buzmaydi). */
const TEST_FILE = /\.test\.[a-z]+$/;

/* -------------------------------------------------------------------------- */
/* REYESTRLAR                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * G-motion-3(a) — `@keyframes` ichida RUXSAT ETILGAN xossalar (09-UI-SPEC
 * §16.4). Hammasi kompozitor-do'st: layout ham, paint-og'ir reflow ham yo'q.
 */
const ALLOWED_KEYFRAME_PROPS = [
  "transform",
  "opacity",
  "background",
  "background-color",
  "background-position",
  "box-shadow",
  "stroke-dashoffset",
  "stroke-dasharray",
];
const MIN_ALLOWED_KEYFRAME_PROPS = 8;

/**
 * G-motion-3(a) — ALOHIDA taqiq ro'yxati. Ruxsat to'plami buni allaqachon
 * qamraydi, TAKRORLANISHI ATAYIN (09-02 reja talabi): aynan shu xossalar
 * arzon Androidda layout-thrash beradi va ularning har biri NOMMA-NOM
 * 0 bo'lishi mustaqil o'lchanadi. `margin`/`padding` PREFIKS sifatida ham
 * tekshiriladi (`margin-top`, `padding-inline` va h.k.).
 */
const BANNED_KEYFRAME_PROPS = [
  "width",
  "height",
  "top",
  "left",
  "right",
  "bottom",
  "margin",
  "padding",
];

/** G-motion-3(a) — `@keyframes` bloklari sonining QUYI chegarasi. */
const MIN_KEYFRAMES_BLOCKS = 6;

/**
 * G-motion-1(b) — juftlangan bare `animate-*` uchrashlarining QUYI chegarasi.
 *
 * ⚠ Bugungi holat: beshta `animate-spin` (payment-bar, shift-close-form,
 *   shift-open-card, decision-bar, capture-cell) — chegara AYNAN to'ladi va
 *   bittasi olib tashlansa darvoza qizaradi. Bu ATAYLAB (09-02 reja):
 *   spinner butunlay o'chirilsa ham, juftliksiz qoldirilsa ham qizil.
 */
const MIN_PAIRED_ANIMATE = 5;

/** G-motion-1(d) — bayram-ijro identifikatorlari (ta'rif sifatida 0 marta). */
const CELEBRATION_IDENTIFIERS = ["confetti", "konfetti", "burst", "particle"];

/**
 * G-motion-3(d) — `dependencies` REYESTRI, NOMMA-NOM (18 nom).
 *
 * ⛔ 09-UI-SPEC avval «20 paket» degan edi — o'lchov 18 berdi (09-01
 *    tuzatishi). Haqiqat manbai — shu reyestr + `assert.deepEqual`.
 */
const EXPECTED_DEPENDENCIES = [
  "@hookform/resolvers",
  "@radix-ui/react-dialog",
  "@radix-ui/react-dropdown-menu",
  "@radix-ui/react-select",
  "@tanstack/react-query",
  "class-variance-authority",
  "clsx",
  "date-fns",
  "lucide-react",
  "next",
  "next-intl",
  "nuqs",
  "react",
  "react-dom",
  "react-hook-form",
  "sonner",
  "tailwind-merge",
  "zod",
];

/**
 * Xato xabarida ALOHIDA ko'rsatiladigan taqiqlangan nomlar (L-8, §3.2).
 * ⛔ Bu o'lchov EMAS — o'lchov yuqoridagi to'plam tengligi; bu ro'yxat
 *    faqat «nega qizardi» ni tezroq tushuntiradi. `lottie-*` prefiks bilan.
 */
const FORBIDDEN_DEPENDENCY_NAMES = [
  "motion",
  "framer-motion",
  "recharts",
  "gsap",
  "canvas-confetti",
  "react-spring",
  "next-themes",
];

/** Qamrov chegaralari — skanerlanadigan fayl soni kamaysa darvoza qizaradi. */
const MIN_COMPONENT_FILES = 100; // bugun 135
const MIN_SRC_FILES = 150; // bugun 207 (.ts/.tsx/.css)

/* -------------------------------------------------------------------------- */
/* IZOHLARNI OLIB TASHLASH                                                    */
/* -------------------------------------------------------------------------- */

/**
 * JS/TS izohlarini olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 * ⛔ `collect-surface.test.mjs` (u ham `bulk-action-surface.test.mjs:163-225`
 *    dan) holat mashinasining nusxasi — mustaqil to'rtinchi mantiq
 *    YOZILMAYDI. Satrlar ataylab saqlanadi: `className` satri ichidagi
 *    utilita ham brauzerga yetib boradi.
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

/** CSS izohlari — `contrast.test.mjs` bilan bir xil regeks. */
function stripCssComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//gu, "");
}

/** Faylning izohsiz JS kodi + «yutib yuborilmadi» nazorati. */
function readCode(file) {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);

  /*
   * RUNAWAY NAZORATI: holat mashinasi adashib butun faylni izoh deb yutsa,
   * keyingi hamma assert JIMGINA yashil bo'lardi — darvoza o'chib qolgan
   * holda «o'tdi» deb hisobot berardi.
   */
  if (raw.includes("export")) {
    assert.ok(
      code.includes("export"),
      `${path.relative(FRONTEND_ROOT, file)}: izoh filtri faylni YUTIB YUBORDI ` +
        "(manbada `export` bor, filtrdan keyin yo'q) — darvoza o'chib qolgan bo'lardi",
    );
  }

  return code;
}

/** `globals.css` ning izohsiz matni + runaway nazorati. */
function readGlobalsCss() {
  const raw = readFileSync(GLOBALS, "utf8");
  const css = stripCssComments(raw);

  assert.ok(
    css.includes("@keyframes") && css.includes("@media (prefers-reduced-motion"),
    "CSS izoh filtri `globals.css` ni YUTIB YUBORDI — `@keyframes` yoki " +
      "reduced-motion bloki filtrdan keyin yo'qolgan",
  );

  return css;
}

/* -------------------------------------------------------------------------- */
/* PARSE YORDAMCHILARI                                                        */
/* -------------------------------------------------------------------------- */

/** `marker` dan boshlangan `{ ... }` blokining ICHKI matni — qavs sanog'i. */
function extractBlock(source, marker) {
  const start = source.indexOf(marker);
  if (start === -1) return null;
  const open = source.indexOf("{", start);
  if (open === -1) return null;
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

/** Barcha `@keyframes <nom> { ... }` bloklari: [{ name, body }]. */
function extractKeyframes(source) {
  const blocks = [];
  for (const m of source.matchAll(/@keyframes\s+([A-Za-z_][\w-]*)/gu)) {
    const open = source.indexOf("{", m.index);
    if (open === -1) continue;
    let depth = 0;
    for (let i = open; i < source.length; i += 1) {
      if (source[i] === "{") depth += 1;
      else if (source[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          blocks.push({ body: source.slice(open + 1, i), name: m[1] });
          break;
        }
      }
    }
  }
  return blocks;
}

/**
 * `@keyframes` tanasidagi XOSSA nomlari. Bosqich selektorlari (`from`,
 * `0%, 100%`) qavs OCHADI, ikki nuqta emas — regeksga tushmaydi.
 */
function keyframeProps(body) {
  const props = [];
  for (const m of body.matchAll(/([a-zA-Z-]+)\s*:\s*[^;{}]+;/gu)) {
    props.push(m[1].toLowerCase());
  }
  return props;
}

/**
 * Satrdagi BARE `animate-*` utilitalari — `motion-reduce:` prefiksli
 * uchrashlar bare emas (juftlikning o'zi hisobga olinmaydi).
 */
function bareAnimateUtilities(line) {
  return [...line.matchAll(/(?<!motion-reduce:)\banimate-[a-z][\w-]*/gu)].map(
    (m) => m[0],
  );
}

/** Bayram identifikatori TA'RIFLARI (funksiya, const/let/var, class). */
function celebrationDefinitions(code) {
  const pattern = new RegExp(
    String.raw`(?:function|const|let|var|class)\s+[$\w]*(?:` +
      CELEBRATION_IDENTIFIERS.join("|") +
      String.raw`)[$\w]*`,
    "giu",
  );
  return code.match(pattern) ?? [];
}

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv, hosila qamrov). */
function listProductFiles(dir, extensions) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full, extensions));
    } else if (
      extensions.includes(path.extname(entry)) &&
      !TEST_FILE.test(entry)
    ) {
      found.push(full);
    }
  }
  return found;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/* -------------------------------------------------------------------------- */

test("reyestrlar uzunligi quyi chegaradan kam EMAS va takrorsiz", () => {
  assert.ok(
    ALLOWED_KEYFRAME_PROPS.length >= MIN_ALLOWED_KEYFRAME_PROPS,
    `ruxsat etilgan xossalar reyestrida atigi ${ALLOWED_KEYFRAME_PROPS.length} ta ` +
      `nom bor (kutilgan: kamida ${MIN_ALLOWED_KEYFRAME_PROPS}) — 09-UI-SPEC §16.4 ` +
      "to'plami qisqartirilgan",
  );
  assert.equal(
    EXPECTED_DEPENDENCIES.length,
    18,
    "bog'liqlik reyestri 18 nomdan chetlandi — reyestrni o'zgartirishdan oldin " +
      "09-UI-SPEC G-motion-3(d) va L-8 (0 KB byudjeti) qayta ochilishi shart",
  );

  // Takror nom reyestrni «uzun» ko'rsatib, chegarani aldab o'tardi.
  for (const [name, list] of [
    ["ALLOWED_KEYFRAME_PROPS", ALLOWED_KEYFRAME_PROPS],
    ["BANNED_KEYFRAME_PROPS", BANNED_KEYFRAME_PROPS],
    ["CELEBRATION_IDENTIFIERS", CELEBRATION_IDENTIFIERS],
    ["EXPECTED_DEPENDENCIES", EXPECTED_DEPENDENCIES],
    ["FORBIDDEN_DEPENDENCY_NAMES", FORBIDDEN_DEPENDENCY_NAMES],
  ]) {
    assert.equal(
      new Set(list).size,
      list.length,
      `${name} reyestrida takrorlangan a'zo bor — uzunlik chegarasi aldangan bo'lardi`,
    );
  }

  // Ruxsat va taqiq to'plamlari kesishmasin — ikkalasi bir xossani da'vo
  // qilsa, darvoza o'z-o'ziga zid bo'lardi.
  const banned = new Set(BANNED_KEYFRAME_PROPS);
  assert.deepEqual(
    ALLOWED_KEYFRAME_PROPS.filter((p) => banned.has(p)),
    [],
    "ruxsat etilgan va taqiqlangan xossa to'plamlari kesishdi",
  );
});

test("detektorlar sun'iy IJOBIY manbani USHLAYDI (o'z-o'zini tekshiruv)", () => {
  /*
   * Usiz quyidagi hamma «topilmadi» xulosasi BO'SH DETEKTOR ustida ham rost
   * bo'lardi — detektor har doim bo'sh massiv qaytarsa, darvoza abadiy yashil.
   */

  // bare animate: juftliksiz topiladi...
  assert.deepEqual(bareAnimateUtilities('className="animate-spin"'), [
    "animate-spin",
  ]);
  // ...juftlik prefiksining O'ZI bare emas...
  assert.deepEqual(bareAnimateUtilities('cn("motion-reduce:animate-none")'), []);
  // ...juft satrda bare utilita BARIBIR sanaladi (juftlik alohida tekshiriladi).
  assert.deepEqual(
    bareAnimateUtilities('className="animate-spin motion-reduce:animate-none"'),
    ["animate-spin"],
  );

  // keyframes xossalari: taqiqlangan `height` topiladi.
  assert.deepEqual(keyframeProps("from { height: 0; } to { height: 100%; }"), [
    "height",
    "height",
  ]);
  // bosqich selektorlari xossa emas.
  assert.deepEqual(
    keyframeProps("0%, 100% { transform: translateX(0); }"),
    ["transform"],
  );

  // bayram ta'riflari: uchala shakl ham ushlanadi.
  assert.equal(celebrationDefinitions("const confettiBurst = 1;").length > 0, true);
  assert.equal(celebrationDefinitions("function fireBurst() {}").length > 0, true);
  assert.equal(celebrationDefinitions("class ParticleField {}").length > 0, true);
  assert.deepEqual(celebrationDefinitions("const ok = 1;"), []);

  // duration-<raqam>: sehrli son topiladi, token sintaksisi topilmaydi.
  assert.equal(/duration-\d/u.test('className="duration-150"'), true);
  assert.equal(/duration-\d/u.test('className="duration-(--motion-fast)"'), false);
});

test("izoh filtrlari faylni YUTIB YUBORMAYDI (runaway nazorati)", () => {
  const js = stripComments(
    'const s = "/* bu izoh EMAS */";\nexport const keep = s;',
  );
  assert.ok(js.includes("export"), "JS izoh filtri `export` ni yutib yubordi");
  assert.ok(
    js.includes("/* bu izoh EMAS */"),
    "satr literali ichidagi matn izoh deb o'chirildi",
  );

  const css = stripCssComments("/* izoh */ .a { color: red; } /* izoh 2 */");
  assert.ok(css.includes(".a { color: red; }"), "CSS filtri qoidani o'chirdi");
  assert.ok(!css.includes("izoh"), "CSS filtri izohni qoldirdi");

  // Haqiqiy fayl ustida ham — readGlobalsCss ichki assertlari ishlaydi.
  readGlobalsCss();
});

/* -------------------------------------------------------------------------- */
/* G-motion-1(a) — REDUCED-MOTION BLOKI PARSE BILAN                           */
/* -------------------------------------------------------------------------- */

test("G-motion-1(a): reduced-motion bloki ikkala davomiylikni !important bilan <=0.01ms ga tushiradi", () => {
  const css = readGlobalsCss();

  const block = extractBlock(css, "@media (prefers-reduced-motion: reduce)");
  assert.ok(
    block !== null,
    "⛔ G-motion-1(a) BUZILDI: `globals.css` da " +
      "`@media (prefers-reduced-motion: reduce)` bloki YO'Q — vestibulyar " +
      "buzilishi bo'lgan foydalanuvchi uchun 700ms uchuvchi element jismoniy " +
      "noqulaylik (ROADMAP SC#4, T-09-06)",
  );

  for (const prop of ["animation-duration", "transition-duration"]) {
    const decl = new RegExp(String.raw`${prop}\s*:\s*([^;]+);`, "u").exec(block);
    assert.ok(
      decl !== null,
      `⛔ G-motion-1(a) BUZILDI: reduced-motion blokida \`${prop}\` ` +
        "deklaratsiyasi YO'Q — `motion-reduce:animate-none` utilitasi faqat " +
        "`animation` ga tegadi, bu blok esa BIRINCHI qatlam (09-RESEARCH Tuzoq 9)",
    );

    const value = decl[1].trim();
    assert.ok(
      value.includes("!important"),
      `G-motion-1(a): \`${prop}\` qiymatida \`!important\` yo'q — qatlam ` +
        `tartibidan qat'i nazar g'olib bo'lish kafolati yo'qoladi (qiymat: ${value})`,
    );

    const ms = /([\d.]+)\s*ms/u.exec(value);
    assert.ok(ms !== null, `G-motion-1(a): \`${prop}\` qiymati ms'da emas: ${value}`);
    assert.ok(
      Number(ms[1]) <= 0.01,
      `G-motion-1(a): \`${prop}\` ${ms[1]}ms — 0.01ms dan katta`,
    );
  }
});

/* -------------------------------------------------------------------------- */
/* G-motion-1(b) — `animate-*` ↔ `motion-reduce:` JUFTLIGI                    */
/* -------------------------------------------------------------------------- */

test("G-motion-1(b): har bare `animate-*` AYNI satrda `motion-reduce:` juftligiga ega (>=5)", () => {
  const files = listProductFiles(COMPONENTS, CODE_EXTENSIONS);
  assert.ok(
    files.length >= MIN_COMPONENT_FILES,
    `\`components/**\` da atigi ${files.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_COMPONENT_FILES}) — skan yuzasi jimgina toraygan`,
  );

  const problems = [];
  let paired = 0;

  for (const file of files) {
    const lines = readCode(file).split("\n");
    lines.forEach((line, index) => {
      const bare = bareAnimateUtilities(line);
      if (bare.length === 0) return;
      if (line.includes("motion-reduce:animate-")) {
        paired += bare.length;
      } else {
        problems.push(
          `${path.relative(SRC, file)}:${index + 1} -> ${bare.join(", ")}`,
        );
      }
    });
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-1(b) BUZILDI — `motion-reduce:` juftligisiz `animate-*`:\n  " +
      problems.join("\n  ") +
      "\n  Har bare `animate-*` yonida AYNI satrda `motion-reduce:animate-none`\n" +
      "  turishi shart (namuna: `snapshots/capture-cell.tsx`). Global blok\n" +
      "  0.01ms qatlami — ikkinchi to'r, birinchisining o'rnini bosmaydi.",
  );

  assert.ok(
    paired >= MIN_PAIRED_ANIMATE,
    `G-motion-1(b): juftlangan \`animate-*\` ${paired} ta — quyi chegara ` +
      `${MIN_PAIRED_ANIMATE}. Spinner o'chirilgan bo'lsa, chegara ONGLI ravishda ` +
      "qayta ko'rilishi kerak (09-02 reja: chegara ataylab aynan to'la)",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-1(d) — KONFETTI IJROSI YO'Q                                       */
/* -------------------------------------------------------------------------- */

test("G-motion-1(d): `components/**` da confetti/burst/particle ta'rifi 0", () => {
  const files = listProductFiles(COMPONENTS, CODE_EXTENSIONS);

  const problems = [];
  for (const file of files) {
    for (const hit of celebrationDefinitions(readCode(file))) {
      problems.push(`${path.relative(SRC, file)} -> \`${hit.trim()}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-1(d) BUZILDI — bayram-ijro ta'rifi tug'ildi:\n  " +
      problems.join("\n  ") +
      "\n  Konfetti 09-UI-SPEC §9 bo'yicha SHARTNOMA sifatida yozilgan, IJRO\n" +
      "  ETILMAGAN: yagona halol tetik (server bayrog'i) mavjud emas, klientdagi\n" +
      "  har qanday hosila ko'r deklaratsiyani buzadi (deferred-items.md).",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-3(a) — @KEYFRAMES FAQAT GPU XOSSALARI                             */
/* -------------------------------------------------------------------------- */

test("G-motion-3(a): har `@keyframes` faqat ruxsat etilgan xossalarni ishlatadi (>=6 blok)", () => {
  const css = readGlobalsCss();
  const blocks = extractKeyframes(css);

  assert.ok(
    blocks.length >= MIN_KEYFRAMES_BLOCKS,
    `\`globals.css\` da atigi ${blocks.length} ta \`@keyframes\` bloki bor ` +
      `(kutilgan: kamida ${MIN_KEYFRAMES_BLOCKS}) — reyestr jimgina qisqargan`,
  );

  const allowed = new Set(ALLOWED_KEYFRAME_PROPS);
  const problems = [];
  const bannedHits = [];

  for (const { body, name } of blocks) {
    const props = keyframeProps(body);
    assert.ok(
      props.length > 0,
      `@keyframes ${name}: birorta xossa topilmadi — parser yoki blok buzilgan`,
    );

    for (const prop of props) {
      if (!allowed.has(prop)) {
        problems.push(`@keyframes ${name} -> \`${prop}\``);
      }
      for (const banned of BANNED_KEYFRAME_PROPS) {
        if (prop === banned || prop.startsWith(`${banned}-`)) {
          bannedHits.push(`@keyframes ${name} -> \`${prop}\``);
        }
      }
    }
  }

  assert.deepEqual(
    bannedHits,
    [],
    "⛔ G-motion-3(a) BUZILDI — layout-thrash xossasi animatsiyada:\n  " +
      bannedHits.join("\n  ") +
      "\n  `width`/`height`/`top`/`left`/`margin*`/`padding*` har kadrda layout\n" +
      "  hisobini qo'zg'aydi — arzon Androidda 60fps IMKONSIZ (ROADMAP SC#5).",
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-3(a) BUZILDI — reyestrdan tashqari xossa:\n  " +
      problems.join("\n  ") +
      "\n  Ruxsat etilgan to'plam (09-UI-SPEC §16.4): " +
      ALLOWED_KEYFRAME_PROPS.join(", "),
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-3(b) — KOMPONENTDA SEHRLI SON YO'Q                                */
/* -------------------------------------------------------------------------- */

test("G-motion-3(b): `components/**` da `duration-<raqam>` 0 · `transition-[` 0 · inline `animation:` 0", () => {
  const files = listProductFiles(COMPONENTS, CODE_EXTENSIONS);

  const problems = [];
  for (const file of files) {
    const code = readCode(file);
    const rel = path.relative(SRC, file);

    for (const m of code.matchAll(/duration-\d[\w.]*/gu)) {
      problems.push(`${rel} -> \`${m[0]}\` (sehrli son — token reyestri chetlab o'tilgan)`);
    }
    if (code.includes("transition-[")) {
      problems.push(`${rel} -> \`transition-[\` (ixtiyoriy transition — G-motion-3(b) taqiqi)`);
    }
    for (const m of code.matchAll(/\banimation\s*:/gu)) {
      problems.push(`${rel} -> \`${m[0]}\` (inline animatsiya — @keyframes faqat globals.css da)`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-3(b) BUZILDI — davomiylikning ikkinchi haqiqat manbai:\n  " +
      problems.join("\n  ") +
      "\n  Davomiyliklar FAQAT token reyestridan: `duration-(--motion-fast|base|slow)`\n" +
      "  yoki `globals.css` dagi `.motion-*` sinflari (T-09-12).",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-3(c) — @KEYFRAMES FAQAT `globals.css` DA, NOMLAR IZCHIL           */
/* -------------------------------------------------------------------------- */

test("G-motion-3(c): `@keyframes` faqat `globals.css` da va har biri kamida bitta sinfda ishlatiladi", () => {
  // (1) src/** ning boshqa faylida @keyframes 0 (hosila qamrov).
  const srcFiles = listProductFiles(SRC, [...CODE_EXTENSIONS, ".css"]);
  assert.ok(
    srcFiles.length >= MIN_SRC_FILES,
    `\`src/**\` da atigi ${srcFiles.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_SRC_FILES}) — skan yuzasi jimgina toraygan`,
  );

  const strayDefinitions = [];
  for (const file of srcFiles) {
    if (path.resolve(file) === path.resolve(GLOBALS)) continue;
    const content =
      path.extname(file) === ".css"
        ? stripCssComments(readFileSync(file, "utf8"))
        : readCode(file);
    if (content.includes("@keyframes")) {
      strayDefinitions.push(path.relative(SRC, file));
    }
  }

  assert.deepEqual(
    strayDefinitions,
    [],
    "⛔ G-motion-3(c) BUZILDI — `@keyframes` `globals.css` dan tashqarida:\n  " +
      strayDefinitions.join("\n  ") +
      "\n  Bitta haqiqat manbai: barcha animatsiya ta'riflari `globals.css` ning\n" +
      "  reyestr blokida yashaydi (09-UI-SPEC §4.3).",
  );

  // (2) Nomlar izchilligi: ta'riflar to'plami == ishlatilgan nomlar to'plami.
  const css = readGlobalsCss();
  const definedNames = extractKeyframes(css).map(({ name }) => name);
  assert.equal(
    new Set(definedNames).size,
    definedNames.length,
    "bitta nom ikki marta ta'riflangan — keyingisi jimgina g'olib bo'lardi",
  );

  const usedNames = [
    ...new Set(
      [...css.matchAll(/\banimation\s*:\s*([A-Za-z_][\w-]*)/gu)].map((m) => m[1]),
    ),
  ];

  assert.deepEqual(
    [...usedNames].sort(),
    [...definedNames].sort(),
    "⛔ G-motion-3(c) BUZILDI — `@keyframes` nomlari va `animation:` " +
      "ishlatishlari MOS EMAS.\n" +
      `  Ta'riflangan: ${[...definedNames].sort().join(", ")}\n` +
      `  Ishlatilgan:  ${[...usedNames].sort().join(", ")}\n` +
      "  Har ta'rif kamida bitta `.motion-*` sinfida ishlatilishi shart (o'lik\n" +
      "  ta'rif yo'q) va har ishlatish mavjud ta'rifga ishora qilishi shart.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-3(d) — `dependencies` TO'PLAM TENGLIGI (18 NOM)                   */
/* -------------------------------------------------------------------------- */

test("G-motion-3(d): `package.json` `dependencies` 18 nomli reyestrga deepEqual", () => {
  const pkg = JSON.parse(readFileSync(PACKAGE_JSON, "utf8"));
  const actual = Object.keys(pkg.dependencies ?? {});

  const forbiddenFound = actual.filter(
    (name) =>
      FORBIDDEN_DEPENDENCY_NAMES.includes(name) || name.startsWith("lottie-"),
  );

  assert.deepEqual(
    [...actual].sort(),
    [...EXPECTED_DEPENDENCIES].sort(),
    "⛔ G-motion-3(d) BUZILDI — `dependencies` reyestrdan chetlandi (L-8: 0 KB byudjeti).\n" +
      (forbiddenFound.length > 0
        ? `  ⛔⛔ TAQIQLANGAN nom(lar): ${forbiddenFound.join(", ")} — motion/diagramma\n` +
          "  kutubxonalari bu fazada UI-SPEC §3.2 bilan rad etilgan (0 KB tanlovi).\n"
        : "") +
      "  Har qulflangan animatsiya sof CSS + ~40 qator vanilla JS bilan chiqadi\n" +
      "  [M-14]. Yangi paket zarur bo'lsa, u UI-SPEC ga QAYTARILADI — jimgina\n" +
      "  `npm install` qilinmaydi (08-UI-SPEC §3.5).",
  );
});
