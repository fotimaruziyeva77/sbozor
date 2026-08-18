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
 * ⛔ MIGRATSIYA QARZI — RO'YXAT FAQAT QISQARADI.
 *
 * Bu fayllar sanani hali ham xom `Intl` bilan chizadi, ya'ni o'zbek lotin
 * tilida ular «2026 M08 15» ko'rsatadi. Qarz YASHIRILMAYDI: u shu yerda
 * sanab turadi va darvoza uzunligini yuqoridan qulflaydi — yangi fayl
 * qo'shilsa test QIZARADI, migratsiya qilingani o'chirilsa YASHIL qoladi.
 *
 * ⛔ Ro'yxatga YANGI nom qo'shish TAQIQLANADI. Yangi kod `formatBusinessDay`
 *    ni ishlatadi.
 */
const DATESTYLE_PENDING = [
  "src/components/audit/audit-list.tsx",
  "src/components/billing/charge-detail-dialog.tsx",
  "src/components/calendar/exception-dialog.tsx",
  "src/components/calendar/exception-list.tsx",
  "src/components/cameras/discovery-result.tsx",
  "src/components/cameras/nvr-card.tsx",
  "src/components/reconciliation/case-detail-dialog.tsx",
  "src/components/reconciliation/case-list.tsx",
  "src/components/reconciliation/delivery-list.tsx",
  "src/components/snapshots/alert-row.tsx",
  "src/components/snapshots/day-summary.tsx",
  "src/components/snapshots/schedule-card.tsx",
  "src/components/snapshots/schedule-dialog.tsx",
  "src/components/tariffs/tariff-dialog.tsx",
  "src/components/tariffs/tariff-list.tsx",
  "src/components/users/user-list.tsx",
  "src/components/vendors/assignment-dialog.tsx",
];

test("G-date(b): `dateStyle` faqat migratsiya qilingan yoki qarz ro'yxatida", () => {
  const walk = (dir, acc = []) => {
    for (const entry of readdirSync(dir)) {
      const full = `${dir}/${entry}`;
      if (statSync(full).isDirectory()) walk(full, acc);
      else if (/\.tsx?$/u.test(entry) && !/\.test\./u.test(entry)) acc.push(full);
    }
    return acc;
  };
  const hits = walk("src")
    .filter((file) => readFileSync(file, "utf8").includes("dateStyle"))
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
    17,
    "⛔ Qarz ro'yxati uzaydi. Yangi nom qo'shish TAQIQ; migratsiya " +
      "qilinganda nomni O'CHIRING va bu sonni kamaytiring.",
  );
});
