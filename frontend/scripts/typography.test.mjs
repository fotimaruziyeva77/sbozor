#!/usr/bin/env node
/**
 * G-motion-7(a,c,d,e) (09-UI-SPEC §16.4) — TIPOGRAFIYA SHKALASI VA SKELETON
 * GEOMETRIYASINING STATIK CHEGARASI.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — TO'RT NARSA, BITTA MEXANIZM.
 *
 * (a) ⛔ DISPLAY-XL YOPIQ QAMROVI (§7.1, L-9, T-09-19). `text-display`
 *     ishlatilgan mahsulot fayllari to'plami REYESTRGA TENG (deepEqual):
 *     `collect/pending-card.tsx` + `headline/headline-card.tsx` — va BOSHQA
 *     HECH QAYERDA. E'lon 5 o'lchamli ko'rinadi, lekin MATN rollari 4 ta
 *     (24/18/14/12); beshinchisi — raqamli display roli va u shu yopiq
 *     reyestr bilan qulflangan. Shkala tarqalishi mexanik ravishda IMKONSIZ.
 *
 * (c) ⛔⛔ GEOMETRIYA JUFTLIGI — CLS NING YAGONA MEXANIK O'LCHOVI (T-09-18,
 *     §16.6). Har reyestr faylida `isPending` shoxidagi `Skeleton` balandligi
 *     kontentning ENG KATTA shoxining qator qutisiga TENG:
 *     `text-display` -> `h-11` (40px x 1.1 = 44px), `text-2xl` -> `h-8`.
 *
 *     ⛔ NEGA ENG KATTA SHOX: `headline-card` da `isPending` paytida `unit`
 *        HALI MA'LUM EMAS — skeleton `h-8` olsa va kontent `text-display`
 *        (soum) kelsa, `h-8` -> `h-11` SAKRASH bo'ladi va bu CLS ning aynan
 *        sababi. Teskarisi (`h-11` -> `h-8` qisqarishi, count shoxi) layout
 *        siljishi emas — shunchaki bo'shliq (09-RESEARCH ochiq savol 5).
 *
 *     ⛔ Reyestr BIR marta yoziladi (`GEOMETRY_PAIRS`) va tasdiqlar undan
 *        HOSILA — testda qiymatlar qayta yozilmaydi.
 *
 * (d) ⛔ MEROS DEVIATSIYALAR O'SMAYDI (M-21): `text-base` <= 7, `text-xl`
 *     <= 4, `text-3xl` = 0, `text-[` = 0. Bu YUQORI chegara — u merosni
 *     TUZATMAYDI, faqat o'sishni to'xtatadi.
 *
 * (e) ⛔ `font-medium` <= 21 (M-22). Og'irliklar rasman 2 ta (400/600);
 *     500 — meros deviatsiya va u ham o'smaydi.
 *
 *     ⛔⛔ CHEGARANI KO'TARISH TAQIQ. Chegaradan oshib ketilsa tuzatish
 *        chegarada emas — YANGI KOMPONENTDA: 9-fazada tug'ilgan fayl
 *        (`theme-toggle`, `revenue-card`, `occupancy-donut`) `text-sm`/
 *        `text-xs` va `font-semibold`/`font-normal` ga o'tkaziladi.
 * =============================================================================
 *
 * ⚠ REYESTRNI `.planning/` DAGI MARKDOWN JADVALIDAN PARSE QILISH RAD ETILDI:
 *   `.planning/` kod darvozalaridan TASHQARIDA (02-22 darsi) va matn
 *   hujjatiga bog'langan darvoza hujjat qayta tahrirlanganda JIMGINA
 *   buziladi. Haqiqat manbai — shu fayldagi reyestr konstantalari.
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (D-32): `src/**` `readdirSync` bilan
 *   REKURSIV o'qiladi, `.test.` fayllar chiqariladi, fayl soni QUYI chegara
 *   bilan qo'riqlanadi. `scripts/` katalogi `src` daraxtidan tashqarida —
 *   darvoza o'z izlash satrlarini o'zi topmaydi.
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN QIDIRILADI — filtrsiz «bu yerga
 *   `text-3xl` yozilmaydi» degan izohning O'ZI darvozani qizartirardi.
 *   Holat mashinasi `collect-surface.test.mjs` dagi nusxa (u ham
 *   `bulk-action-surface.test.mjs:163-225` dan — W0-F4 konvensiyasi).
 *
 * ⚠ TASHQI PAKET YO'Q — sof matn skani, `gate:fast` (200 s) byudjetiga
 *   sezilmas qo'shiladi.
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

/** Skanerlanadigan kengaytmalar — utilita sinflari faqat TS/TSX'da yashaydi. */
const CODE_EXTENSIONS = [".ts", ".tsx"];

/** Mahsulot fayli emas — qamrovdan chiqadi (u taqiqni O'LCHAYDI, buzmaydi). */
const TEST_FILE = /\.test\.[a-z]+$/u;

/* -------------------------------------------------------------------------- */
/* REYESTRLAR                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * G-motion-7(a) — Display-XL ning YOPIQ qamrovi (09-UI-SPEC §7.1).
 *
 * ⛔ AYNAN IKKI fayl: (1) kassir «Kutilayotgan patta» summasi — shartsiz;
 *    (2) direktor bosh ko'rsatkichi — FAQAT `unit === "soum"` shoxida
 *    (shartlilik `headline-card.test.tsx` G-motion-7(b) da o'lchanadi).
 *    Uchinchi fayl qo'shilsa bu deepEqual QIZARADI — chegara emas, TENGLIK.
 */
const DISPLAY_REGISTRY = [
  "components/collect/pending-card.tsx",
  "components/headline/headline-card.tsx",
];

/**
 * G-motion-7(c) — qator qutisi <-> skeleton balandligi JUFTLIK REYESTRI.
 *
 * ⛔ ENG KATTADAN KICHIKKA TARTIBLANGAN: fayldagi eng katta kontent shoxi
 *    shu tartibda birinchi topilgan kalit bo'ladi. `text-display` 40px x
 *    line-height 1.1 = 44px = `h-11`; `text-2xl` 24px qatori = 32px = `h-8`.
 * ⛔ BIR marta yoziladi — (c) tasdig'i shu jadvaldan HOSILA.
 */
const GEOMETRY_PAIRS = [
  ["text-display", "h-11"],
  ["text-2xl", "h-8"],
];

/**
 * G-motion-7(d,e) — meros deviatsiyalarning YUQORI chegaralari (M-21, M-22).
 *
 * ⛔ CHEGARANI KO'TARISH TAQIQ (pastdagi qulf testi). Oshsa — yangi
 *    komponent standart rollarga (`text-sm`/`text-xs`, `font-semibold`/
 *    `font-normal`) o'tkaziladi, chegara emas.
 */
const DEVIATION_CEILINGS = [
  // [nom, regex, yuqori chegara]
  ["text-base", /\btext-base\b/gu, 7],
  ["text-xl", /\btext-xl\b/gu, 4],
  ["text-3xl", /\btext-3xl\b/gu, 0],
  ["font-medium", /\bfont-medium\b/gu, 21],
];

/** `text-[` — ixtiyoriy o'lcham; regex emas, literal qidiruv (qavs belgisi). */
const ARBITRARY_TEXT_TOKEN = "text-[";

/** Skan yuzasi jimgina toraymasin — `motion-tokens.test.mjs` bilan bir xil. */
const MIN_SRC_FILES = 150; // bugun ~207 (.ts/.tsx)

/* -------------------------------------------------------------------------- */
/* IZOHLARNI OLIB TASHLASH — collect-surface.test.mjs holat mashinasi nusxasi */
/* -------------------------------------------------------------------------- */

/**
 * JS/TS izohlarini olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 * ⛔ `collect-surface.test.mjs` (u ham `bulk-action-surface.test.mjs:163-225`
 *    dan) holat mashinasining nusxasi — mustaqil implementatsiya YOZILMAYDI.
 *    Satrlar ataylab saqlanadi: `className` satri ichidagi utilita brauzerga
 *    yetib boradi, ya'ni u ham o'lchov ostida.
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

/** Faylning izohsiz kodi + «yutib yuborilmadi» nazorati. */
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

/* -------------------------------------------------------------------------- */
/* PARSE YORDAMCHILARI                                                        */
/* -------------------------------------------------------------------------- */

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

/** `src` ga nisbatan POSIX ko'rinishdagi yo'l (Windows'da ham `/`). */
function relPosix(file) {
  return path.relative(SRC, file).split(path.sep).join("/");
}

/** Kodda `text-display` utilitasi ISHLATILGANMI. */
function usesTextDisplay(code) {
  return /\btext-display\b/u.test(code);
}

/**
 * Koddagi barcha `<Skeleton …className="…"…>` balandliklari (`h-N` -> N).
 *
 * ⚠ Butun fayl skanerlanadi — shox (branch) AST bilan ajratilmaydi: reyestr
 *   fayllarining har birida `Skeleton` FAQAT `isPending` shoxida yashaydi
 *   (kontent shoxi haqiqiy matn chizadi), ya'ni butun-fayl skani o'sha
 *   shoxning o'zini o'qiydi. Bu soddalik ATAYIN: AST bu darvozaga
 *   `typescript` importini olib kelardi (motion-tokens `postcss` importini
 *   rad etgani kabi rad etiladi).
 */
function skeletonHeights(code) {
  const heights = [];
  for (const tag of code.matchAll(/<Skeleton\b[\s\S]*?className="([^"]*)"/gu)) {
    for (const h of tag[1].matchAll(/\bh-(\d+)\b/gu)) {
      heights.push(Number(h[1]));
    }
  }
  return heights;
}

/** Fayldagi ENG KATTA kontent shoxi juftligi — `GEOMETRY_PAIRS` tartibidan. */
function largestPairFor(code) {
  for (const [sizeClass, skeletonClass] of GEOMETRY_PAIRS) {
    if (new RegExp(String.raw`\b${sizeClass}\b`, "u").test(code)) {
      return { sizeClass, skeletonClass };
    }
  }
  return null;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/* -------------------------------------------------------------------------- */

test("reyestrlar qulflangan: Display AYNAN 2 fayl, chegaralar 7/4/0/0/21, takrorsiz", () => {
  /*
   * ⛔ (a) chegara emas — TENGLIK: reyestr uzunligi AYNAN 2. Uchinchi
   *    a'zo qo'shishdan oldin 09-UI-SPEC §7.1 qayta ochilishi shart.
   */
  assert.equal(
    DISPLAY_REGISTRY.length,
    2,
    "Display-XL reyestri 2 fayldan chetlandi — §7.1 yopiq qamrovi qayta " +
      "ochilishi shart (G-motion-7(a))",
  );
  assert.equal(
    new Set(DISPLAY_REGISTRY).size,
    DISPLAY_REGISTRY.length,
    "DISPLAY_REGISTRY da takrorlangan a'zo bor",
  );

  assert.equal(GEOMETRY_PAIRS.length >= 2, true, "juftlik reyestri qisqargan");
  assert.equal(
    new Set(GEOMETRY_PAIRS.map(([sizeClass]) => sizeClass)).size,
    GEOMETRY_PAIRS.length,
    "GEOMETRY_PAIRS da takrorlangan o'lcham bor",
  );

  /*
   * ⛔⛔ CHEGARA QULFI — KO'TARISH TAQIQ (G-motion-7(d,e)). Bu qiymatlar
   *     2026-08-17 o'lchovi (M-21/M-22): text-base 7 · text-xl 4 ·
   *     text-3xl 0 · font-medium 21. Chegaradan oshilsa tuzatish YANGI
   *     KOMPONENTDA (text-sm/text-xs, font-semibold/font-normal) —
   *     bu sonlarni tahrirlashda EMAS.
   */
  const locked = { "text-base": 7, "text-xl": 4, "text-3xl": 0, "font-medium": 21 };
  for (const [name, , ceiling] of DEVIATION_CEILINGS) {
    assert.equal(
      ceiling,
      locked[name],
      `\`${name}\` chegarasi ${locked[name]} dan ${ceiling} ga o'zgartirilgan — ` +
        "chegarani ko'tarish TAQIQ (09-UI-SPEC G-motion-7(d,e))",
    );
  }
});

test("detektorlar sun'iy IJOBIY manbani USHLAYDI (o'z-o'zini tekshiruv)", () => {
  /*
   * Usiz quyidagi «reyestrga teng» va «chegaradan oshmagan» xulosalari
   * BO'SH DETEKTOR ustida ham rost bo'lardi.
   */

  // (a) text-display: klassda topiladi, izohda (strip'dan keyin) topilmaydi.
  assert.equal(usesTextDisplay('className="font-mono text-display"'), true);
  assert.equal(usesTextDisplay(stripComments("/* text-display */ const a=1;")), false);
  // `--text-display` token nomi ham ushlanadi — bu ATAYIN qattiq shakl:
  // mahsulot .tsx faylida token nomining o'zi ham display yuzasi hisoblanadi.
  assert.equal(usesTextDisplay("var(--text-display)"), true);

  // (c) skeleton balandliklari: bir va ko'p atribut, ko'p qator.
  assert.deepEqual(skeletonHeights('<Skeleton className="h-11 w-40" />'), [11]);
  assert.deepEqual(
    skeletonHeights('<Skeleton className="h-11 w-28" />\n<Skeleton className="h-5 w-48" />'),
    [11, 5],
  );
  assert.deepEqual(
    skeletonHeights('<Skeleton\n  aria-hidden\n  className="h-8"\n/>'),
    [8],
  );
  assert.deepEqual(skeletonHeights('<div className="h-24" />'), []);

  // (c) eng katta shox: ikkalasi bor faylda text-display g'olib.
  assert.deepEqual(
    largestPairFor('cn("text-display", "text-2xl")'),
    { sizeClass: "text-display", skeletonClass: "h-11" },
  );
  assert.deepEqual(largestPairFor('className="text-2xl"'), {
    sizeClass: "text-2xl",
    skeletonClass: "h-8",
  });
  assert.equal(largestPairFor('className="text-sm"'), null);

  // (d) chegara regexlari: text-2xl `text-xl` ga TUSHMAYDI.
  assert.equal([...'"text-xl"'.matchAll(DEVIATION_CEILINGS[1][1])].length, 1);
  assert.equal([...'"text-2xl"'.matchAll(DEVIATION_CEILINGS[1][1])].length, 0);
  assert.equal([...'"text-3xl font-medium"'.matchAll(DEVIATION_CEILINGS[3][1])].length, 1);
  // text-[ literal qidiruvi.
  assert.equal('className="text-[13px]"'.includes(ARBITRARY_TEXT_TOKEN), true);
});

test("izoh filtri faylni YUTIB YUBORMAYDI (runaway nazorati)", () => {
  const code = stripComments(
    'const s = "/* bu izoh EMAS */";\nexport const keep = s;',
  );
  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(
    code.includes("/* bu izoh EMAS */"),
    "satr literali ichidagi matn izoh deb o'chirildi",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-7(a) — DISPLAY-XL YOPIQ QAMROVI                                   */
/* -------------------------------------------------------------------------- */

test("G-motion-7(a): `text-display` fayllari reyestrga TENG (deepEqual, <=2)", () => {
  const files = listProductFiles(SRC);
  assert.ok(
    files.length >= MIN_SRC_FILES,
    `\`src/**\` da atigi ${files.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_SRC_FILES}) — skan yuzasi jimgina toraygan`,
  );

  const actual = files
    .filter((file) => usesTextDisplay(readCode(file)))
    .map(relPosix);

  assert.deepEqual(
    [...actual].sort(),
    [...DISPLAY_REGISTRY].sort(),
    "⛔ G-motion-7(a) BUZILDI — Display-XL qamrovi reyestrdan chetlandi.\n" +
      `  Topilgan: ${[...actual].sort().join(", ") || "(bo'sh)"}\n` +
      `  Reyestr:  ${[...DISPLAY_REGISTRY].sort().join(", ")}\n` +
      "  `text-display` FAQAT ikki joyda yashaydi (09-UI-SPEC §7.1): kassir\n" +
      "  summasi (shartsiz) va direktor bosh ko'rsatkichi (faqat soum shoxi).\n" +
      "  Uchinchi ishlatish shkalani ochadi — 40px «34» direktorga «34 million»\n" +
      "  bo'lib o'qiladi. Reyestr kengaytirilishidan oldin §7.1 qayta ochiladi.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-motion-7(c) — SKELETON GEOMETRIYA JUFTLIGI (CLS PROKSI)                  */
/* -------------------------------------------------------------------------- */

test("G-motion-7(c): har reyestr faylida skeleton balandligi ENG KATTA shox juftligiga teng", () => {
  for (const rel of DISPLAY_REGISTRY) {
    const file = path.join(SRC, ...rel.split("/"));
    const code = readCode(file);

    const pair = largestPairFor(code);
    assert.ok(
      pair !== null,
      `${rel}: juftlik reyestridagi birorta o'lcham sinfi topilmadi — parser ` +
        "yoki fayl buzilgan (kutilgan edi: text-display yoki text-2xl)",
    );

    const heights = skeletonHeights(code);
    assert.ok(
      heights.length > 0,
      `${rel}: \`<Skeleton className="h-N ...">\` topilmadi — isPending shoxi ` +
        "skeletonsiz qolgan yoki parser buzilgan",
    );

    const maxHeight = Math.max(...heights);
    const expected = Number(/\d+/u.exec(pair.skeletonClass)[0]);

    assert.equal(
      maxHeight,
      expected,
      `⛔ G-motion-7(c) BUZILDI — ${rel}: qiymat skeletoni \`h-${maxHeight}\`, ` +
        `eng katta kontent shoxi esa \`${pair.sizeClass}\` (juftligi ` +
        `\`${pair.skeletonClass}\`).\n` +
        "  Skeleton kontentning ENG KATTA shoxiga teng bo'lishi shart: kichik\n" +
        "  skeleton kontent kelganda SAKRAYDI (CLS — T-09-18), katta skeleton\n" +
        "  qisqarishi esa shunchaki bo'shliq. To'liq CLS o'lchovi 09-HUMAN-UAT #2.",
    );
  }
});

/* -------------------------------------------------------------------------- */
/* G-motion-7(d,e) — DEVIATSIYALAR O'SMAYDI                                   */
/* -------------------------------------------------------------------------- */

test("G-motion-7(d,e): text-base<=7 · text-xl<=4 · text-3xl=0 · text-[=0 · font-medium<=21", () => {
  const files = listProductFiles(SRC);

  const counts = new Map(DEVIATION_CEILINGS.map(([name]) => [name, []]));
  const arbitraryHits = [];

  for (const file of files) {
    const code = readCode(file);
    const rel = relPosix(file);

    for (const [name, regex] of DEVIATION_CEILINGS) {
      const found = [...code.matchAll(regex)].length;
      if (found > 0) counts.get(name).push(`${rel} x${found}`);
    }

    let from = 0;
    let hits = 0;
    while ((from = code.indexOf(ARBITRARY_TEXT_TOKEN, from)) !== -1) {
      hits += 1;
      from += ARBITRARY_TEXT_TOKEN.length;
    }
    if (hits > 0) arbitraryHits.push(`${rel} x${hits}`);
  }

  for (const [name, , ceiling] of DEVIATION_CEILINGS) {
    const perFile = counts.get(name);
    const total = perFile.reduce(
      (sum, entry) => sum + Number(/x(\d+)$/u.exec(entry)[1]),
      0,
    );
    assert.ok(
      total <= ceiling,
      `⛔ G-motion-7(${name === "font-medium" ? "e" : "d"}) BUZILDI — \`${name}\` ` +
        `${total} marta (chegara ${ceiling}):\n  ` +
        perFile.join("\n  ") +
        "\n  ⛔ Chegarani KO'TARMANG: 9-fazada tug'ilgan faylni standart rolga\n" +
        "  (`text-sm`/`text-xs`, `font-semibold`/`font-normal`) o'tkazing —\n" +
        "  meros deviatsiya tuzatilmaydi, YANGISI esa tug'ilmaydi (M-21/M-22).",
    );
  }

  assert.deepEqual(
    arbitraryHits,
    [],
    "⛔ G-motion-7(d) BUZILDI — ixtiyoriy `text-[` o'lchami:\n  " +
      arbitraryHits.join("\n  ") +
      "\n  Shkala 4 matn roli + display (yopiq reyestr) — oraliq o'lcham yo'q.",
  );
});
