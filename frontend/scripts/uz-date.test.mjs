import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { test } from "node:test";

/*
 * =============================================================================
 * G-date — O'ZBEK LOTIN SANASI HECH QACHON ILDIZ SHABLONIGA TUSHMAYDI.
 *
 * ⛔ NEGA BU DARVOZA BOR (o'lchangan 2026-08-18, jonli Chrome'da):
 *    `Intl.DateTimeFormat("uz-Latn", …)` brauzerda «2026 M08 15» qaytaradi —
 *    bu yozuv uchun CLDR oy nomlari brauzer ICU'sida YO'Q. Node'da esa
 *    bor, ya'ni nosozlik testda ko'rinmay, FOYDALANUVCHIDA ko'rinardi.
 *    Butun ilova bo'ylab har sanada, jumladan direktor paneli va
 *    tekshiruvchi ko'radigan hisobotlarda.
 *
 * ⛔ Shuning uchun bu yerda IKKI narsa o'lchanadi:
 *    (a) yordamchining o'zi hech qanday kirishda `M0`/`M1` bermaydi;
 *    (b) mahsulot kodida `dateStyle` bilan XOM `Intl`/`format.dateTime`
 *        chaqiruvi qolmagan — ya'ni yangi kod yordamchini chetlab o'tmaydi.
 * =============================================================================
 */

/** Yordamchining o'zi — TS emas, shuning uchun jadval bu yerda qayta yoziladi
 *  emas, balki MANBADAN o'qiladi va shakli tekshiriladi. */
const SOURCE = readFileSync("src/lib/uz-latn-date.ts", "utf8");

test("G-date(a): oy jadvali AYNAN 12 a'zo va ildiz shakli yo'q", () => {
  const table = SOURCE.slice(
    SOURCE.indexOf("const MONTHS = ["),
    SOURCE.indexOf("] as const;"),
  );
  const months = [...table.matchAll(/"([a-z]+)"/gu)].map((m) => m[1]);
  assert.equal(
    months.length,
    12,
    `⛔ Oy jadvali 12 ta bo'lishi shart, topildi: ${months.length}`,
  );
  assert.deepEqual(months, [
    "yanvar",
    "fevral",
    "mart",
    "aprel",
    "may",
    "iyun",
    "iyul",
    "avgust",
    "sentabr",
    "oktabr",
    "noyabr",
    "dekabr",
  ]);
  /* ⛔ IZOHLAR OLIB TASHLANADI: modul sharhida nuqsonning MISOLI
     («2026 M08 15») ataylab yozilgan va u yolg'on ijobiy berardi. */
  const code = SOURCE.replace(/\/\*[\s\S]*?\*\//gu, "").replace(
    /\/\/.*/gu,
    "",
  );
  assert.equal(
    /M\d/u.test(code),
    false,
    "⛔ Kodda `M0`/`M1` naqshi — ildiz shabloni sizib kirgan",
  );
});

/**
 * ⛔ Mahsulot kodida `dateStyle` faqat SHU ikki faylda bo'lishi mumkin:
 *    yagona sana yordamchisi va uning uz-Latn bo'lmagan shoxi. Uchinchi
 *    joyda paydo bo'lishi — yordamchi chetlab o'tilgani, ya'ni o'sha
 *    ekranda sana yana «M08» bo'lib chiqishi demakdir.
 */
const DATESTYLE_MIGRATED = [
  "src/lib/format-day.ts",
  "src/lib/uz-latn-date.ts",
  "src/components/collect/shift-open-card.tsx",
];

/*
 * ⛔ MIGRATSIYA QARZI — 2026-08-18 da NOLGA TUSHDI (Topilma №3).
 *
 * Ro'yxat 17 ta fayldan iborat edi; ularning hammasi `formatBusinessDay`,
 * `formatInstant` yoki `formatInstantDay` ga o'tkazildi. Ro'yxat SAQLANADI
 * (o'chirilmaydi), chunki uning uzunligi pastdagi (c) darvozasida
 * QULFLANGAN: nol qolgani — endi xom `Intl` sanasi bilan yashil bo'lish
 * yo'li YO'Qligini bildiradi.
 *
 * ⛔ Ro'yxatga YANGI nom qo'shish TAQIQLANADI: bu qarzni qaytarish demak.
 */
const DATESTYLE_PENDING = [];

test("G-date(b): `dateStyle` faqat migratsiya qilingan yoki qarz ro'yxatida", () => {
  const walk = (dir, acc = []) => {
    for (const entry of readdirSync(dir)) {
      const full = `${dir}/${entry}`;
      if (statSync(full).isDirectory()) walk(full, acc);
      else if (/\.tsx?$/u.test(entry) && !/\.test\./u.test(entry)) acc.push(full);
    }
    return acc;
  };
  /*
   * ⛔ IZOHLAR TASHLANADI (G-date(a) bilan bir naqsh). Aks holda
   *    `dateStyle` NI NEGA ISHLATMASLIK kerakligini tushuntirgan izoh
   *    faylni ayblanuvchiga aylantirardi — aynan shu sabab
   *    `delivery-list.tsx` qarz ro'yxatida yotgan edi, holbuki unda
   *    bitta ham xom chaqiruv yo'q.
   */
  const stripComments = (code) =>
    code.replaceAll(/\/\*[\s\S]*?\*\//gu, "").replaceAll(/\/\/.*$/gmu, "");
  const hits = walk("src")
    .filter((file) => stripComments(readFileSync(file, "utf8")).includes("dateStyle"))
    .sort();
  const known = [...DATESTYLE_MIGRATED, ...DATESTYLE_PENDING].sort();
  const unknown = hits.filter((file) => !known.includes(file));
  assert.deepEqual(
    unknown,
    [],
    "⛔ Yangi faylda xom `dateStyle` — o'sha ekranda sana o'zbek lotin " +
      "tilida «2026 M08 15» bo'lib chiqadi. `formatBusinessDay` ni ishlating.",
  );
});

test("G-date(c): migratsiya qarzi FAQAT qisqaradi", () => {
  const walk = (dir, acc = []) => {
    for (const entry of readdirSync(dir)) {
      const full = `${dir}/${entry}`;
      if (statSync(full).isDirectory()) walk(full, acc);
      else if (/\.tsx?$/u.test(entry) && !/\.test\./u.test(entry)) acc.push(full);
    }
    return acc;
  };
  const stillPending = walk("src").filter(
    (file) =>
      DATESTYLE_PENDING.includes(file) &&
      readFileSync(file, "utf8").includes("dateStyle"),
  );
  assert.ok(
    stillPending.length <= DATESTYLE_PENDING.length,
    "⛔ Qarz o'sdi — bu mumkin emas",
  );
  assert.equal(
    DATESTYLE_PENDING.length,
    0,
    "⛔ Qarz ro'yxati uzaydi. Yangi nom qo'shish TAQIQ — xom `Intl` " +
      "sanasi o'rniga `formatBusinessDay`/`formatInstant` ishlating.",
  );
});

/*
 * =============================================================================
 * G-date(d): XOM `weekday` — SANA BILAN BIR XIL NOSOZLIK (260818).
 * =============================================================================
 * `format.dateTime(d, { weekday: "long" })` o'zbek lotin yozuvida
 * brauzerda «Tue» beradi — ildiz shablonining INGLIZCHA qisqartmasi.
 * Nosozlik `review/page.tsx` da jonli topildi: nazoratchining birinchi
 * ekranida sana «2026-08-18 · Tue» bo'lib turgan.
 *
 * ⛔ Darvoza (b) BILAN BIR XIL SHAKLDA yozilgan (izohlar tashlanadi,
 *    faqat migratsiya ro'yxati o'tadi) — ikki xil naqsh bo'lsa, biri
 *    keyingi ijrochida e'tibordan qolardi.
 */
test("G-date(d): xom `weekday` faqat sana yordamchisida", () => {
  const walk = (dir, acc = []) => {
    for (const entry of readdirSync(dir)) {
      const full = `${dir}/${entry}`;
      if (statSync(full).isDirectory()) walk(full, acc);
      else if (/\.tsx?$/u.test(entry) && !/\.test\./u.test(entry)) acc.push(full);
    }
    return acc;
  };
  const stripComments = (code) =>
    code.replaceAll(/\/\*[\s\S]*?\*\//gu, "").replaceAll(/\/\/.*$/gmu, "");

  /* ⛔ `weekday:` — obyekt maydoni; `open_weekdays` kabi nomlar tushmasin. */
  const hits = walk("src")
    .filter((file) => /(?<![\w_])weekday:/u.test(stripComments(readFileSync(file, "utf8"))))
    .sort();

  assert.deepEqual(
    hits,
    ["src/lib/format-day.ts"],
    "⛔ Xom `weekday` — o'sha ekranda hafta kuni o'zbek lotin tilida " +
      "INGLIZCHA chiqadi. `formatBusinessWeekday` ni ishlating.",
  );
});

/*
 * =============================================================================
 * G-num: XOM `format.number` — PUL SONI UCHUN TAQIQ (260819).
 * =============================================================================
 * `new Intl.NumberFormat("uz-Latn").format(12480000)` brauzerda
 * «12,480,000» beradi — VERGUL bilan, CLDR ildiz shabloni. Node'ning
 * to'liq ICU'si «12 480 000» beradi. `uz-Cyrl` va `ru` da brauzer
 * to'g'ri ishlaydi, ya'ni nosozlik FAQAT asosiy tilimizda.
 *
 * ⛔ Bu sanadan qimmatroq: vergul ba'zi konvensiyalarda KASR belgisi.
 *
 * ⛔ RUXSAT ETILGAN ISHLATISH: opsiyali chaqiruvlar (foiz, kasr, birlik)
 *    — ular guruhlash mantig'iga tegmaydi va `formatAmount` dan
 *    o'tmaydi. Shuning uchun darvoza FAQAT opsiyasiz shaklni ushlaydi:
 *    `format.number(x)`.
 */
test("G-num: opsiyasiz `format.number(x)` faqat yordamchida", () => {
  const walk = (dir, acc = []) => {
    for (const entry of readdirSync(dir)) {
      const full = `${dir}/${entry}`;
      if (statSync(full).isDirectory()) walk(full, acc);
      else if (/\.tsx?$/u.test(entry) && !/\.test\./u.test(entry)) acc.push(full);
    }
    return acc;
  };
  const stripComments = (code) =>
    code.replaceAll(/\/\*[\s\S]*?\*\//gu, "").replaceAll(/\/\/.*$/gmu, "");

  /* ⛔ `format.number(` + qavs ichida `{` YO'Q -> opsiyasiz shakl. */
  const bare = /format\.number\([^(){}]+\)/u;

  const hits = walk("src")
    .filter((file) => bare.test(stripComments(readFileSync(file, "utf8"))))
    .sort();

  assert.deepEqual(
    hits,
    ["src/lib/format-number.ts"],
    "⛔ Xom `format.number(x)` — o'sha ekranda pul o'zbek lotin tilida " +
      "VERGUL bilan chiqadi. `formatAmount(format, x, locale)` ishlating.",
  );
});
