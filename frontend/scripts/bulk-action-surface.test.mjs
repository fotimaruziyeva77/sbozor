#!/usr/bin/env node
/**
 * G-18(b) — ⛔ OMMAVIY AMAL YUZASI: QAMROV UI-SPEC DAN HOSILA QILINADI.
 *
 * =============================================================================
 * ⛔ NEGA BU FAYL BOR — 05-VERIFICATION W-3 EMAS, W-2.
 *
 * UI-SPEC §15 ning G-18 qatori IKKI katalogni e'lon qiladi:
 * `components/review/**` VA `components/blind-audit/**`. Amalda esa
 * skan bitta katalogda edi — `review-session.test.tsx` faqat Y-2
 * sessiyasini render qilardi, `blind-session.test.tsx` da checkbox
 * skani UMUMAN yo'q edi.
 *
 * Bugun zarari yo'q, chunki ikkala sessiya BITTA `DecisionBar` ni
 * ishlatadi. Ertangi zarari aniq: to'g'ridan-to'g'ri `blind-session.tsx`
 * ga qo'shilgan checkbox birorta darvozani qizartirmasdi — ya'ni
 * e'lon qilingan kafolat o'z mexanizmidan KENG edi.
 * =============================================================================
 *
 * ⛔ TUZATISH SHAKLI MUHIM: KATALOG RO'YXATI BU YERDA QAYTA YOZILMAYDI.
 *
 *   «`blind-session.test.tsx` ga ham skan qo'shish» — bu W-2 ni bugun
 *   yopib, ertaga qayta ochardi: UI-SPEC ga UCHINCHI katalog qo'shilsa
 *   (masalan `components/occupancy/**`), qo'lda yozilgan ro'yxat yana
 *   ortda qolardi va buni hech nima aytmasdi.
 *
 *   Shuning uchun qamrov E'LONNING O'ZIDAN o'qiladi: bu fayl UI-SPEC
 *   §15 ning G-18 QATORINI tahlil qiladi va `components/.../**`
 *   naqshlarini O'SHA QATORDAN oladi. Spetsifikatsiya kengaysa, skan
 *   O'ZI kengayadi. 4-fazadagi `compose.yaml` dan hosila darvoza
 *   (`test_compose_sim_env.py`) shu naqshning birinchi qo'llanishi edi.
 *
 * ⚠ IZOHLAR OLIB TASHLANADI va busiz darvoza BUGUN qizarardi:
 *   `decision-bar.tsx:35` ning izohida `type="checkbox"` MATN sifatida
 *   yozilgan — qoidani tushuntirish uchun. `grep` asosidagi skan kodni
 *   izohdan ajratmaydi (2 va 3-fazada 15+ marta takrorlangan sinf).
 *
 * ⚠ TEST FAYLLARI SKANDAN CHIQARILADI va chegara ANIQ: taqiq MAHSULOT
 *   YUZASIGA qo'yilgan. `review-session.test.tsx:459` ning O'ZI
 *   `input[type="checkbox"]` ni YO'QLIGINI tekshiradi — ya'ni u taqiqni
 *   BUZMAYDI, uni O'LCHAYDI. Test fayllari qamrovda qolsa, darvoza o'z
 *   qo'riqchisini aybdor deb ko'rsatardi.
 *
 * ⚠ DETEKTOR ATAYIN QO'POL: `checkbox` va `Array.isArray` SUBSTRINGLARI.
 *   Nozikroq tahlil (JSX atributini ajratish, mutatsiya tanasini
 *   kuzatish) o'zi buzilishi mumkin bo'lgan kodga aylanardi — G-14(a)
 *   ning `[` sharti bilan bir xil mulohaza. Bu ikki katalog KICHIK va
 *   BIR MAQSADLI: ularda `checkbox` so'zining qonuniy ishlatilishi yo'q.
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const SRC = path.join(FRONTEND_ROOT, "src");
const PHASES_DIR = path.join(REPO_ROOT, ".planning", "phases");

const CODE_EXTENSIONS = [".ts", ".tsx"];

/** Mahsulot fayli emas — qamrovdan chiqadi (yuqoridagi izohga qarang). */
const TEST_FILE = /\.test\.tsx?$/;

/**
 * Skanerlanadigan eng kam fayl soni — ⛔ §S-10 QUYI CHEGARASI.
 *
 * Bo'sh to'plamda «taqiqlangan token topilmadi» JIMGINA rost bo'lardi:
 * katalog qayta nomlansa yoki kengaytmalar ro'yxati eskirsa, darvoza
 * hech nimani skanerlamay yashil qolardi.
 */
const MIN_SCANNED_FILES = 5;

/* -------------------------------------------------------------------------- */
/* 1-BOSQICH — QAMROVNI E'LONDAN O'QISH                                       */
/* -------------------------------------------------------------------------- */

/** `.planning/phases/*` ichidan G-18 ni E'LON QILGAN UI-SPEC fayllari. */
function findSpecsDeclaringG18() {
  if (!existsSync(PHASES_DIR)) return [];

  const found = [];
  for (const phase of readdirSync(PHASES_DIR)) {
    const phaseDir = path.join(PHASES_DIR, phase);
    if (!statSync(phaseDir).isDirectory()) continue;

    for (const entry of readdirSync(phaseDir)) {
      if (!entry.endsWith("-UI-SPEC.md")) continue;
      const full = path.join(phaseDir, entry);
      if (g18Rows(readFileSync(full, "utf8")).length > 0) found.push(full);
    }
  }
  return found;
}

/** UI-SPEC matnidagi G-18 jadval qatorlari. */
function g18Rows(spec) {
  return spec.split("\n").filter((line) => /^\|\s*\*\*G-18\*\*\s*\|/.test(line));
}

/** G-18 qatorida NOM BILAN e'lon qilingan katalog naqshlari. */
function declaredDirectoryGlobs(row) {
  return [...row.matchAll(/`(components\/[A-Za-z0-9._-]+\/\*\*)`/g)].map((m) => m[1]);
}

const SPEC_FILES = findSpecsDeclaringG18();

/* -------------------------------------------------------------------------- */
/* 2-BOSQICH — DARVOZANING O'Z MEXANIZMI (e'lon o'qildimi?)                   */
/* -------------------------------------------------------------------------- */

test("G-18(b): e'lonning O'ZI topildi — AYNAN bitta UI-SPEC va AYNAN bitta qator", () => {
  assert.equal(
    SPEC_FILES.length,
    1,
    `G-18 ni e'lon qilgan UI-SPEC soni ${SPEC_FILES.length} (kutilgan: 1): ` +
      `${SPEC_FILES.map((f) => path.relative(REPO_ROOT, f)).join(", ")}\n` +
      "  Nolda — e'lon ko'chirilgan yoki qayta nomlangan va bu darvoza endi " +
      "QAMROVINI O'QIY OLMAYDI (jimgina bo'sh skan xavfi).\n" +
      "  Birdan ko'pda — qaysi e'lon bog'lovchi ekani noaniq.",
  );

  const rows = g18Rows(readFileSync(SPEC_FILES[0], "utf8"));
  assert.equal(rows.length, 1, `G-18 qatori ${rows.length} marta uchradi (kutilgan: 1)`);
});

test("G-18(b): qamrov E'LONDAN olindi — kamida IKKI katalog", () => {
  const globs = declaredDirectoryGlobs(g18Rows(readFileSync(SPEC_FILES[0], "utf8"))[0]);

  assert.ok(
    globs.length >= 2,
    `G-18 qatoridan atigi ${globs.length} ta katalog naqshi o'qildi: ` +
      `${JSON.stringify(globs)}\n  UI-SPEC §15 IKKITASINI e'lon qiladi ` +
      "(`components/review/**` va `components/blind-audit/**`). Naqsh " +
      "o'qilmasa, skan JIMGINA torayadi — aynan W-2 ning shakli.",
  );
  assert.equal(new Set(globs).size, globs.length, `takrorlangan katalog naqshi: ${globs}`);
});

test("G-18(b): e'lon HAMON shu ikki tokenni nomlaydi", () => {
  /*
   * ⛔ SKANER E'LONDAN AJRALIB KETMASIN. Qamrov hosila, TOKENLAR esa
   *   shu faylda yozilgan — ya'ni UI-SPEC taqiqni boshqa tokenga
   *   ko'chirsa, skaner eskirgan narsani qidirib yashil qolardi. Bu
   *   assert o'sha ajralishni qizartiradi.
   */
  const row = g18Rows(readFileSync(SPEC_FILES[0], "utf8"))[0];

  assert.ok(row.includes('type="checkbox"'), "G-18 qatori `type=\"checkbox\"` ni nomlamay qo'ydi");
  assert.ok(row.includes("Array.isArray"), "G-18 qatori `Array.isArray` ni nomlamay qo'ydi");
});

/* -------------------------------------------------------------------------- */
/* 3-BOSQICH — IZOH FILTRI (busiz darvoza BUGUN qizarardi)                    */
/* -------------------------------------------------------------------------- */

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * Satrlar ATAYIN saqlanadi: `role` qiymati, tarjima kaliti yoki
 * `data-testid` ichidagi `checkbox` ham brauzerga yetib boradi.
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
/* 4-BOSQICH — DETEKTOR                                                       */
/* -------------------------------------------------------------------------- */

const FORBIDDEN_TOKENS = [
  { token: "checkbox", why: "ko'p tanlash yuzasi — ommaviy tasdiqning JSX shakli (D-18)" },
  { token: "Array.isArray", why: "massiv tanali mutatsiya — ommaviy javobning tarmoq shakli (D-18)" },
];

/** Kodda uchragan taqiqlangan tokenlar. */
function forbiddenHits(code) {
  const lowered = code.toLowerCase();
  return FORBIDDEN_TOKENS.filter(({ token }) => lowered.includes(token.toLowerCase())).map(
    ({ token }) => token,
  );
}

test("G-18(b): NAZORAT — detektor sun'iy IJOBIY manbani USHLAYDI", () => {
  assert.deepEqual(forbiddenHits('<input type="checkbox" />'), ["checkbox"]);
  assert.deepEqual(forbiddenHits("if (Array.isArray(body)) submitAll(body);"), ["Array.isArray"]);
});

test("G-18(b): ⛔ SALBIY NAZORAT — toza manba va IZOHDAGI eslatma o'tadi", () => {
  /*
   * ⛔ IKKINCHI HOLAT ENG MUHIMI VA U HAQIQIY: `decision-bar.tsx:35`
   *   izohida `type="checkbox"` MATN sifatida turibdi. Izoh filtri
   *   ishlamasa, bu darvoza BUGUNGI TOZA KODDA qizarardi va keyingi
   *   ijrochi uni «shovqin» deb o'chirardi.
   */
  assert.deepEqual(forbiddenHits('<button onClick={submit}>Band</button>'), []);
  assert.deepEqual(
    forbiddenHits(stripComments('/* G-18(b) `type="checkbox"` ni skanerlaydi. */\nexport const a = 1;')),
    [],
  );
});

test("G-18(b): izoh filtri faylni YUTIB YUBORMAYDI", () => {
  const code = stripComments('const s = "/* bu izoh EMAS */";\nexport const keep = s;');

  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(code.includes("/* bu izoh EMAS */"), "satr literali ichidagi matn izoh deb o'chirildi");
});

/* -------------------------------------------------------------------------- */
/* 5-BOSQICH — ASOSIY DA'VO                                                   */
/* -------------------------------------------------------------------------- */

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv). */
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

/** E'londan o'qilgan naqshni haqiqiy katalogga aylantiradi. */
function globToDir(glob) {
  return path.join(SRC, ...glob.replace(/\/\*\*$/, "").split("/"));
}

test("G-18(b): e'lon qilingan HAR katalog mavjud va BO'SH EMAS", () => {
  const globs = declaredDirectoryGlobs(g18Rows(readFileSync(SPEC_FILES[0], "utf8"))[0]);

  for (const glob of globs) {
    const dir = globToDir(glob);
    assert.ok(
      existsSync(dir),
      `UI-SPEC \`${glob}\` ni e'lon qiladi, lekin ${path.relative(REPO_ROOT, dir)} YO'Q — ` +
        "e'lon bilan fayl tizimi ajralib ketgan",
    );
    assert.ok(
      listProductFiles(dir).length > 0,
      `\`${glob}\` da birorta mahsulot fayli yo'q — skan bu katalogda BO'SH`,
    );
  }
});

test("⛔ G-18(b): e'lon qilingan KATALOGLARDA ommaviy amal yuzasi YO'Q", () => {
  const globs = declaredDirectoryGlobs(g18Rows(readFileSync(SPEC_FILES[0], "utf8"))[0]);
  const files = globs.flatMap((glob) => listProductFiles(globToDir(glob)));

  assert.ok(
    files.length >= MIN_SCANNED_FILES,
    `atigi ${files.length} ta fayl skanerlandi (quyi chegara ${MIN_SCANNED_FILES}) — ` +
      "qamrov jimgina qisqargan",
  );

  const problems = [];
  for (const file of files) {
    const code = stripComments(readFileSync(file, "utf8"));
    for (const token of forbiddenHits(code)) {
      const why = FORBIDDEN_TOKENS.find((t) => t.token === token).why;
      problems.push(`${path.relative(FRONTEND_ROOT, file)} -> \`${token}\` (${why})`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ ommaviy amal yuzasi e'lon qilingan katalogda tug'ildi (D-18, G-18b):\n  " +
      problems.join("\n  ") +
      "\n  Nazoratchi HAR bandga ALOHIDA javob beradi — bu AI-03 ning matni " +
      "emas, uning MEXANIZMI. Ommaviy tasdiq «ko'rmasdan tasdiqlash» ni " +
      "bir bosishga arzonlashtiradi va hisobotdagi aniqlik raqamini soxta " +
      "qiladi.",
  );
});
