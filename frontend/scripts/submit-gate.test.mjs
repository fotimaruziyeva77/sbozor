#!/usr/bin/env node
/**
 * G-SUBMIT — ⛔ «JIM-DISABLED SUBMIT» ANTI-NAQSHI QAYTMASLIGINING DARVOZASI.
 *
 * =============================================================================
 * ⛔ NIMA TAQIQLANADI VA NEGA.
 *
 * O'CHIRILGAN TUGMA VALIDATSIYANING O'RNINI BOSA OLMAYDI: u NIMA
 * yetishmayotganini AYTMAYDI. Foydalanuvchi uchun «so'rov ketmadi + xato
 * yo'q + dialog ochiq» uchligi «saqlandi, dialog yopilmadi» dan
 * farqlanmaydi — bu TEST-REPORT (2026-08-14) Topilma №4 ning aynan sinfi
 * va u bir vaqtning o'zida BESHTA joyda takrorlangan edi.
 *
 * Qoida bitta jumla: submit tugmasi FAQAT yuborish jarayoni davomida
 * yopiladi; domen sharti (maydon bo'sh, ro'yxat bo'sh, tanlov yo'q, javob
 * kelmagan) validatsiya xabari bo'lib EKRANGA chiqadi.
 *
 * Etalon — `src/components/users/create-user-dialog.tsx`.
 * =============================================================================
 *
 * ⛔ IKKI DETEKTOR, VA IKKINCHISI MAJBURIY.
 *
 *   D-1 YOLG'IZ qolganda undan qochish ARZON: tugmadan `type="submit"` ni
 *   olib tashlab, `onClick` + `aria-disabled` ga qaytish yetardi — va bu
 *   o'ylab topilgan xavf emas, aynan F-4 ning (kamera nomi dialogi)
 *   BUGUNGACHA yashagan shakli. Shuning uchun D-2 submit YO'LIDAN
 *   qochishni ham taqiqlaydi.
 *
 * ⚠ NEGA `aria-disabled` TAQIQLANMAYDI: u boshqa masala va boshqa
 *   qamrov. `Button` ning CSS'i faqat native `disabled` ni biladi
 *   (`disabled:pointer-events-none`), ya'ni `aria-disabled` bosilishni
 *   TO'XTATMAYDI — u ba'zi joylarda ATAYIN shunday ishlatilgan (sababni
 *   `role="status"` bilan e'lon qilib, tugmani fokusda saqlash;
 *   `camera-row.tsx` naqshi). Uni bu darvozaga qo'shish o'sha ONGLI
 *   naqshni ham qizartirardi.
 *
 * ⚠ IZOHLAR OLIB TASHLANADI va busiz darvoza BUGUN qizarardi: Task 1/2
 *   qo'shgan izohlar qoidani TUSHUNTIRADI va grep asosidagi skan kodni
 *   izohdan ajratmaydi (2–5 fazalarda 15+ marta takrorlangan sinf).
 *
 * ⚠ TEST FAYLLARI SKANDAN CHIQARILADI: taqiq MAHSULOT yuzasiga qo'yilgan.
 *   `stall-dialog.test.tsx` ning O'ZI tahrir rejimining tri-state
 *   holatlarini o'lchaydi — ya'ni u taqiqni BUZMAYDI, uni QO'RIQLAYDI.
 */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

/** Mahsulot fayli emas — qamrovdan chiqadi (yuqoridagi izohga qarang). */
const TEST_FILE = /\.test\.tsx?$/;

/**
 * ⛔ §S-10 QUYI CHEGARALARI — bo'sh skan JIMGINA rost bo'lardi.
 *
 * Katalog qayta nomlansa, kengaytma ro'yxati eskirsa yoki izoh filtri
 * faylni yutib yuborsa, «taqiq topilmadi» degan xulosa hech nimani
 * o'lchamay yashil qolardi. O'lchov (2026-08-16): 12 submit tugmasi,
 * 14 `onSubmit` fayli. Chegaralar biroz pastroq — bitta forma
 * o'chirilishi darvozani yolg'on-qizil qilmasin.
 */
const MIN_SUBMIT_BUTTONS = 10;
const MIN_ONSUBMIT_FILES = 12;

/**
 * RUXSAT ETILGAN LUG'AT — faqat «yuborilyapti» ma'nosidagi identifikatorlar.
 *
 * Nuqtali tokenda OXIRGI segment baholanadi: `createMarket.isPending` ->
 * `isPending` ✅, `categories.length` -> `length` ⛔, `code.trim` -> `trim` ⛔.
 */
const SUBMITTING_TOKENS = new Set([
  "isSubmitting",
  "isPending",
  "isLoading",
  "busy",
  "saving",
  "submitting",
]);

/**
 * ISTISNOLAR — IZOHLI, VA ULAR MUZLAMAYDI.
 *
 * Har yozuv: fayl + KUTILGAN aynan qoldiq + sabab + yopilish tetigi.
 * Uchta meta-qoida darvozaning O'ZIDA bajariladi:
 *   1. istisno faylning MAVJUD holatiga AYNAN mos kelmasa (to'plam
 *      kengaysa ham, torayadi ham) -> darvoza QIZARADI;
 *   2. ESKIRGAN istisno (fayl tuzatilgan, hit yo'q) -> darvoza QIZARADI,
 *      ya'ni ro'yxat o'z-o'zini tozalashga majbur;
 *   3. yangi yozuv qo'shish — KO'RINADIGAN amal (diff'da izoh bilan).
 *
 * ⚠ QOLDIQ REJADAN KO'CHIRILMAGAN — u detektor CHIQARGAN qiymat
 *   (2026-08-16 o'lchovi).
 */
/**
 * ⛔ RO'YXAT BO'SH — VA U O'Z QOIDASI BILAN BO'SHATILDI.
 *
 * Yagona yozuv (`components/stalls/stall-dialog.tsx`, qoldiq
 * `["detail", "mode", "undefined"]`) 260816-5yz da YOPILDI: tahrir rejimi
 * endi tri-state guard zanjiriga ega, ya'ni batafsil javob kelmaguncha
 * forma UMUMAN chizilmaydi va jim-disabled shartning o'zi mantiqan
 * erishib bo'lmas holga keldi. Yozuv shundan keyin darvozaning
 * «ESKIRGAN ISTISNO» da'vosini qizartirdi — ro'yxat o'z-o'zini tozalashga
 * majbur qilgani AYNAN shu.
 *
 * ⚠ BO'SH RO'YXAT DARVOZANI BO'SHATMAYDI: `MIN_SUBMIT_BUTTONS` quyi
 *   chegarasi va ijobiy/salbiy meta-nazoratlar detektorning o'zini
 *   o'lchashda davom etadi; asosiy D-1 da'vosi esa endi ISTISNOSIZ
 *   butun `src/` ga qo'llanadi.
 */
const D1_EXCEPTIONS = [];

const D2_EXCEPTIONS = [
  {
    file: "components/collect/collect-session.tsx",
    why:
      "`onSubmit` bu yerda FORMA emas, `StallLookup` ga uzatilgan PROP " +
      "(qidiruv boshlash); `stall-lookup.tsx` da `<form>` elementi umuman " +
      "yo'q, ya'ni yopiladigan submit yo'li ham yo'q",
    closesWith:
      "qidiruv haqiqiy `<form>` ga aylantirilsa — o'shanda submit tugmasi " +
      "MAJBURIY bo'ladi va bu yozuv o'chadi",
  },
  {
    file: "components/stalls/stall-filters.tsx",
    why:
      "filtr formasi: `onSubmit` yagona mos keladigan rastani OCHADI, " +
      "hech narsa saqlamaydi — «Saqlash» tugmasi bu yerda ma'nosiz bo'lardi",
    closesWith: "filtr paneliga yozuv amali qo'shilsa",
  },
];

/* -------------------------------------------------------------------------- */
/* 1-BOSQICH — IZOH FILTRI                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * ⚠ `bulk-action-surface.test.mjs` DAN KO'CHIRILGAN, import QILINMAGAN va
 *   bu ONGLI QAROR: `scripts/` da umumiy modul konvensiyasi yo'q, import
 *   qilinsa bu darvoza BOSHQA darvozaning ichki funksiyasiga bog'lanib
 *   qolardi — o'sha o'zgarganda bu jimgina siljirdi. Ikki darvoza
 *   bir-biridan MUSTAQIL yiqilishi kerak.
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

/** Satr literallarini bo'sh qiladi — tokenizator uchun (`"edit"` -> `""`). */
function stripStringLiterals(source) {
  let out = "";
  let quote = null;
  let i = 0;

  while (i < source.length) {
    const c = source[i];

    if (quote === null) {
      if (c === "'" || c === '"' || c === "`") {
        quote = c;
      } else {
        out += c;
      }
      i += 1;
      continue;
    }

    if (c === "\\") {
      i += 2;
      continue;
    }
    if (c === quote) quote = null;
    i += 1;
  }

  return out;
}

/* -------------------------------------------------------------------------- */
/* 2-BOSQICH — JSX OCHUVCHI TEGINI AJRATISH                                   */
/* -------------------------------------------------------------------------- */

/**
 * `start` dagi `<` dan boshlab ochuvchi tegni O'QIYDI.
 *
 * ⚠ `>` BELGISI IFODA ICHIDA HAM UCHRAYDI (`count > 0`, `a => b`), shuning
 *   uchun tegning oxiri jingalak-qavs CHUQURLIGI va satr holati bilan
 *   aniqlanadi — sodda `indexOf(">")` tegni yarmidan kesib, `disabled`
 *   ifodasini jimgina yo'qotardi.
 */
function readTag(source, start) {
  let depth = 0;
  let quote = null;

  for (let i = start; i < source.length; i += 1) {
    const c = source[i];

    if (quote !== null) {
      if (c === "\\") {
        i += 1;
      } else if (c === quote) {
        quote = null;
      }
      continue;
    }

    if (c === "'" || c === '"' || c === "`") {
      quote = c;
      continue;
    }
    if (c === "{") {
      depth += 1;
      continue;
    }
    if (c === "}") {
      depth -= 1;
      continue;
    }
    if (c === ">" && depth === 0) {
      return source.slice(start, i + 1);
    }
  }

  return null;
}

/** Berilgan NOMDAGI barcha ochuvchi teglar (izohsiz manbadan). */
function openingTags(code, names) {
  const tags = [];
  const re = /<([A-Za-z][A-Za-z0-9.]*)/g;
  let match;

  while ((match = re.exec(code)) !== null) {
    if (!names.includes(match[1])) continue;
    const tag = readTag(code, match.index);
    if (tag !== null) tags.push(tag);
  }

  return tags;
}

/* -------------------------------------------------------------------------- */
/* 3-BOSQICH — D-1 DETEKTORI                                                  */
/* -------------------------------------------------------------------------- */

/** Tegdagi `disabled` atributi: `{ifoda}` yoki shartsiz shakl. */
function disabledAttribute(tag) {
  /*
   * `aria-disabled` va `data-disabled` ATAYIN chetlab o'tiladi: ulardan
   * oldingi belgi `-`, ya'ni bu naqsh ularga mos kelmaydi.
   */
  const opener = /(^|[\s{])disabled=\{/.exec(tag);
  if (opener !== null) {
    const start = opener.index + opener[0].length;
    let depth = 1;
    let quote = null;

    for (let i = start; i < tag.length; i += 1) {
      const c = tag[i];
      if (quote !== null) {
        if (c === "\\") i += 1;
        else if (c === quote) quote = null;
        continue;
      }
      if (c === "'" || c === '"' || c === "`") {
        quote = c;
        continue;
      }
      if (c === "{") depth += 1;
      else if (c === "}") {
        depth -= 1;
        if (depth === 0) return { kind: "expression", text: tag.slice(start, i) };
      }
    }
    return { kind: "expression", text: tag.slice(start) };
  }

  // Shartsiz `disabled` (JSX shorthand) — «hech qachon bosilmaydi».
  if (/(^|[\s{])disabled(?![-A-Za-z0-9_$])\s*(?!=)/.test(tag)) {
    return { kind: "unconditional", text: "" };
  }

  return null;
}

/** Ifodadagi RUXSAT ETILMAGAN identifikatorlar (tartiblangan, takrorsiz). */
function residueTokens(expression) {
  const tokens = stripStringLiterals(expression).match(
    /[A-Za-z_$][A-Za-z0-9_$.]*/g,
  );
  const bad = new Set();

  for (const token of tokens ?? []) {
    const segments = token.split(".").filter((part) => part !== "");
    const last = segments.at(-1) ?? token;
    if (!SUBMITTING_TOKENS.has(last)) bad.add(last);
  }

  return [...bad].sort();
}

/** Fayldagi submit tugmalari va ularning qoldig'i. */
function scanSubmitButtons(code) {
  const found = [];

  for (const tag of openingTags(code, ["Button", "button"])) {
    if (!tag.includes('type="submit"')) continue;

    const attribute = disabledAttribute(tag);
    if (attribute === null) {
      found.push({ residue: [] });
      continue;
    }
    if (attribute.kind === "unconditional") {
      found.push({ residue: ["<shartsiz-disabled>"] });
      continue;
    }
    found.push({ residue: residueTokens(attribute.text) });
  }

  return found;
}

/* -------------------------------------------------------------------------- */
/* 4-BOSQICH — FAYL RO'YXATI                                                  */
/* -------------------------------------------------------------------------- */

function listProductFiles(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full));
    } else if (path.extname(entry) === ".tsx" && !TEST_FILE.test(entry)) {
      found.push(full);
    }
  }
  return found;
}

/** `src/` ga nisbatan POSIX yo'l — istisno ro'yxatining kaliti. */
function relKey(file) {
  return path.relative(SRC, file).split(path.sep).join("/");
}

const PRODUCT_FILES = listProductFiles(SRC).map((file) => ({
  key: relKey(file),
  code: stripComments(readFileSync(file, "utf8")),
}));

/* -------------------------------------------------------------------------- */
/* 5-BOSQICH — META-TESTLAR (busiz darvoza o'zini o'lchamaydi)                 */
/* -------------------------------------------------------------------------- */

test("G-SUBMIT meta: IJOBIY nazorat — domen-shartli `disabled` USHLANADI", () => {
  const cases = [
    ['<Button type="submit" disabled={categories.length === 0}>', ["length"]],
    ['<Button type="submit" disabled={code.trim() === ""}>', ["trim"]],
    ['<Button type="submit" disabled={detail === undefined}>', ["detail", "undefined"]],
    ['<Button type="submit" disabled>', ["<shartsiz-disabled>"]],
    // ⚠ `>` IFODA ICHIDA: sodda `indexOf(">")` tegni kesib tashlardi va
    //   bu holat JIMGINA o'tib ketardi.
    ['<Button type="submit" disabled={count > 0}>', ["count"]],
  ];

  for (const [source, expected] of cases) {
    assert.deepEqual(
      scanSubmitButtons(source).map((hit) => hit.residue),
      [expected],
      `detektor sun'iy ijobiy manbani o'tkazib yubordi: ${source}`,
    );
  }
});

test("G-SUBMIT meta: ⛔ SALBIY nazorat — etalon va `busy` O'TADI", () => {
  const clean = [
    '<Button className="sm:flex-1" disabled={isSubmitting} size="lg" type="submit">',
    "<Button disabled={busy} size=\"lg\" type='submit'>",
    '<Button disabled={rename.isPending} type="submit">',
    '<Button disabled={createMarket.isPending || isSubmitting} type="submit">',
    // Submit tugmasi EMAS — qamrovga umuman kirmaydi.
    '<Button disabled={categories.length === 0} onClick={run}>',
    // `aria-disabled` bu darvozaning masalasi emas (fayl boshidagi izoh).
    '<Button aria-disabled={blocked ? true : undefined} type="submit">',
  ];

  for (const source of clean) {
    assert.deepEqual(
      scanSubmitButtons(source).flatMap((hit) => hit.residue),
      [],
      `toza manba yolg'on-qizil berdi: ${source}`,
    );
  }
});

test("G-SUBMIT meta: ⛔ IZOH nazorati — izohdagi anti-naqsh O'TADI", () => {
  /*
   * ⛔ BU HOLAT HAQIQIY VA U DARVOZANI BUGUN QIZARTIRARDI: Task 1/2
   *   qo'shgan izohlar qoidani tushuntiradi, `stall-dialog.tsx` esa
   *   istisnoning SABABINI yozadi. Izoh filtri ishlamasa, keyingi
   *   ijrochi bu darvozani «shovqin» deb o'chirardi.
   */
  const source = [
    "/* Ilgari bu yerda `disabled={code.trim() === \"\"}` turardi. */",
    '<Button disabled={isSubmitting} type="submit">Saqlash</Button>',
    "// TAQIQ: `disabled={categories.length === 0}` qaytmasin.",
  ].join("\n");

  assert.deepEqual(
    scanSubmitButtons(stripComments(source)).flatMap((hit) => hit.residue),
    [],
  );
});

test("G-SUBMIT meta: izoh filtri faylni YUTIB YUBORMAYDI", () => {
  const code = stripComments('const s = "/* bu izoh EMAS */";\nexport const keep = s;');

  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(
    code.includes("/* bu izoh EMAS */"),
    "satr literali ichidagi matn izoh deb o'chirildi",
  );
});

test("G-SUBMIT meta: satr literali soxta token bermaydi", () => {
  // `"edit"` ichidagi `edit` tokenizatorga YETIB BORMAYDI.
  assert.deepEqual(residueTokens('mode === "edit" && isSubmitting'), ["mode"]);
});

/* -------------------------------------------------------------------------- */
/* 6-BOSQICH — D-1: SUBMIT TUGMASIDA DOMEN-SHARTLI `disabled` TAQIQ           */
/* -------------------------------------------------------------------------- */

/** `key -> qoldiq` — faqat qoldig'i BO'SH BO'LMAGAN fayllar. */
function d1Violations() {
  const violations = new Map();

  for (const { key, code } of PRODUCT_FILES) {
    const residue = [
      ...new Set(scanSubmitButtons(code).flatMap((hit) => hit.residue)),
    ].sort();
    if (residue.length > 0) violations.set(key, residue);
  }

  return violations;
}

test("G-SUBMIT D-1: skan BO'SH EMAS — quyi chegara", () => {
  const total = PRODUCT_FILES.reduce(
    (sum, { code }) => sum + scanSubmitButtons(code).length,
    0,
  );

  assert.ok(
    total >= MIN_SUBMIT_BUTTONS,
    `atigi ${total} ta submit tugmasi topildi (quyi chegara ` +
      `${MIN_SUBMIT_BUTTONS}) — skan jimgina qisqargan yoki izoh filtri ` +
      "fayllarni yutib yuborgan; bunday holatda «taqiq topilmadi» xulosasi " +
      "hech nimani o'lchamaydi (§S-10)",
  );
});

test("G-SUBMIT D-1: istisnolar MUZLAMAYDI — eskirgani ham, siljigani ham qizil", () => {
  const violations = d1Violations();

  for (const exception of D1_EXCEPTIONS) {
    const actual = violations.get(exception.file);

    assert.ok(
      actual !== undefined,
      `ESKIRGAN ISTISNO: \`${exception.file}\` endi toza — yozuvni ` +
        "O'CHIRING.\n  Ro'yxat o'z-o'zini tozalashi SHART, aks holda u bir " +
        "kun haqiqiy nuqsonni yashiradi.\n  Yopilish tetigi edi: " +
        exception.closesWith,
    );
    assert.deepEqual(
      actual,
      exception.residue,
      `ISTISNO SILJIDI: \`${exception.file}\` qoldig'i o'zgardi.\n` +
        `  Kutilgan: ${JSON.stringify(exception.residue)}\n` +
        `  Haqiqiy:  ${JSON.stringify(actual)}\n` +
        "  Istisno AYNAN bitta ma'lum holatga berilgan — to'plam kengaysa " +
        "ham, torayadi ham, uni QAYTA KO'RIB CHIQISH kerak.\n" +
        `  Sabab: ${exception.why}\n  Tetik: ${exception.closesWith}`,
    );
  }
});

test("⛔ G-SUBMIT D-1: submit tugmasida domen-shartli `disabled` YO'Q", () => {
  const violations = d1Violations();
  for (const exception of D1_EXCEPTIONS) violations.delete(exception.file);

  const problems = [...violations.entries()].map(
    ([key, residue]) => `${key} -> ${JSON.stringify(residue)}`,
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ submit tugmasi domen sharti bilan yopilgan:\n  " +
      problems.join("\n  ") +
      "\n  O'CHIRILGAN TUGMA VALIDATSIYANING O'RNINI BOSA OLMAYDI — u NIMA " +
      "yetishmayotganini aytmaydi. Shartni tugmadan OLIB TASHLANG va zod " +
      "xabarini ekranga chiqaring (etalon: " +
      "`components/users/create-user-dialog.tsx`).\n  Ruxsat etilgan " +
      `lug'at: ${[...SUBMITTING_TOKENS].sort().join(", ")}.`,
  );
});

/* -------------------------------------------------------------------------- */
/* 7-BOSQICH — D-2: SUBMIT YO'LIDAN QOCHISH TAQIQI                            */
/* -------------------------------------------------------------------------- */

/** `onSubmit` ishlatadigan, lekin submit tugmasi YO'Q fayllar. */
function d2Violations() {
  return PRODUCT_FILES.filter(
    ({ code }) => code.includes("onSubmit={") && !code.includes('type="submit"'),
  ).map(({ key }) => key);
}

test("G-SUBMIT D-2: skan BO'SH EMAS — quyi chegara", () => {
  const total = PRODUCT_FILES.filter(({ code }) =>
    code.includes("onSubmit={"),
  ).length;

  assert.ok(
    total >= MIN_ONSUBMIT_FILES,
    `atigi ${total} ta \`onSubmit\` fayli topildi (quyi chegara ` +
      `${MIN_ONSUBMIT_FILES}) — skan jimgina qisqargan (§S-10)`,
  );
});

test("G-SUBMIT D-2: istisnolar MUZLAMAYDI — eskirgani qizil", () => {
  const violations = new Set(d2Violations());

  for (const exception of D2_EXCEPTIONS) {
    assert.ok(
      violations.has(exception.file),
      `ESKIRGAN ISTISNO: \`${exception.file}\` endi submit tugmasiga ega ` +
        "(yoki `onSubmit` dan voz kechgan) — yozuvni O'CHIRING.\n" +
        `  Yopilish tetigi edi: ${exception.closesWith}`,
    );
  }
});

test("⛔ G-SUBMIT D-2: `onSubmit` bor joyda submit tugmasi ham bor", () => {
  const excepted = new Set(D2_EXCEPTIONS.map((item) => item.file));
  const problems = d2Violations().filter((key) => !excepted.has(key));

  assert.deepEqual(
    problems,
    [],
    "⛔ forma `onSubmit` ni ishlatadi, lekin `type=\"submit\"` tugmasi " +
      "yo'q:\n  " +
      problems.join("\n  ") +
      "\n  Bu D-1 dan QOCHISHNING eng arzon yo'li: tugmani `onClick` +" +
      " `aria-disabled` ga qaytarish domen shartini yana ko'rinmas " +
      "qilardi (F-4 ning aynan shakli). Klaviatura foydalanuvchisi uchun " +
      "esa Enter yo'li umuman yo'qoladi.",
  );
});
