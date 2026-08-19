#!/usr/bin/env node
/**
 * G-date-1 — SANA XOM `Intl` BILAN YOZILMAYDI.
 *
 * =============================================================================
 * NEGA BU DARVOZA BOR — U IKKI MARTA TISHLAGAN NUQSONDAN TUG'ILGAN.
 *
 * O'zbek LOTIN yozuvi uchun brauzer ICU'sida oy nomlari YO'Q. Shuning
 * uchun `Intl.DateTimeFormat("uz-Latn-UZ", { month: "long" })` chiroyli
 * «19-avgust» emas, ildiz shablonini beradi:
 *
 *     2026 M08 19
 *
 * Bu ekranda hokim va tekshiruvchi ko'radigan qator. `lib/format-day.ts`
 * dagi `formatBusinessDay()` aynan shu uchun bor va u FAQAT shu til
 * uchun jadval bilan yozadi.
 *
 * ⛔⛔ MUAMMO SHUKI, XATO KO'RINMAYDI: `format.dateTime(...)` chaqiruvi
 *     kodda mutlaqo to'g'ri o'qiladi, tiplar o'tadi, testlar yashil
 *     bo'ladi — va faqat brauzerda, faqat uz-Latn da buziladi. Admin
 *     paneli qurilganda u AYNAN shunday qaytdi (260819).
 *
 * SHUNING UCHUN: `month: "long"` bilan `format.dateTime` chaqirig'i
 * taqiqlanadi. Sana kerak bo'lsa — `formatBusinessDay()`.
 * =============================================================================
 *
 * ⚠ `timeStyle` (soat) TAQIQLANMAYDI: soat formatida oy nomi yo'q va
 *   `Intl` uni uch tilda ham to'g'ri beradi.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "..", "src");

/** `.tsx`/`.ts` fayllarni REKURSIV yig'adi; testlar chiqariladi. */
function sources(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      out.push(...sources(path));
      continue;
    }
    if (!/\.tsx?$/.test(name)) continue;
    if (name.includes(".test.")) continue;
    out.push(path);
  }
  return out;
}

/*
 * ⛔ ISTISNO — `lib/format-day.ts` NING O'ZI. U aynan shu muammoni hal
 *    qiladigan fayl va uning ichida `Intl` ga murojaat BO'LISHI kerak.
 *    Istisno ro'yxati QISQA va u shu yerda, bitta joyda turadi.
 */
const ALLOWED = new Set(["lib/format-day.ts", "lib/uz-latn-date.ts"]);

/*
 * ⛔ FAQAT OY NOMI TAQIQLANADI — `"long"` va `"short"`.
 *
 *   `month: "numeric"` va `month: "2-digit"` RAQAM beradi va u uchala
 *   tilda ham to'g'ri chiqadi; ICU bo'shlig'i faqat oy NOMLARIDA.
 *   Darvozaning birinchi shakli har qanday `month:` ni belgilagan va
 *   `zone-editor.tsx` dagi mutlaqo to'g'ri `"2-digit"` ni ham qizil
 *   qilgan edi — yolg'on ayblov darvozani o'chirishga olib keladi.
 */
const MONTH_NAME = /\bmonth\s*:\s*[\"'](?:long|short)[\"']/;

/**
 * `*.dateTime(...)` chaqiruvlarining ARGUMENT MATNINI qaytaradi.
 *
 * ⛔⛔ QAVS SANAGICHI BILAN, REGEX BILAN EMAS — VA BU SABOTAJ SINOVIDA
 *     TOPILGAN. Avvalgi shakl `([\s\S]{0,240}?)\)` edi va u BIRINCHI
 *     yopuvchi qavsda to'xtardi. Ya'ni
 *
 *         format.dateTime(new Date(), { month: "long" })
 *
 *     chaqirig'ida argument matni `new Date(` bo'lib qolar, `month:`
 *     esa undan TASHQARIDA qolardi. Darvoza yashil turib, aynan
 *     ushlashi kerak bo'lgan yozuvni o'tkazib yuborardi.
 *
 *     Sun'iy buzilish kiritib tekshirilmaganda bu topilmasdi.
 */
function dateTimeCalls(text) {
  const out = [];
  const opener = /\b\w*[Ff]ormat(?:ter)?\.dateTime\(/g;
  let match;
  while ((match = opener.exec(text)) !== null) {
    let depth = 1;
    let i = opener.lastIndex;
    while (i < text.length && depth > 0) {
      const ch = text[i];
      if (ch === "(") depth += 1;
      else if (ch === ")") depth -= 1;
      i += 1;
    }
    out.push(text.slice(opener.lastIndex, i - 1));
  }
  return out;
}

test("G-date-1 — `month: \"long\"` xom `Intl` bilan yozilmaydi", () => {
  const offenders = [];

  for (const path of sources(SRC)) {
    const rel = relative(SRC, path).split("\\").join("/");
    if (ALLOWED.has(rel)) continue;

    const text = readFileSync(path, "utf8");
    for (const args of dateTimeCalls(text)) {
      if (MONTH_NAME.test(args)) {
        offenders.push(`${rel} — ${args.replace(/\s+/g, " ").slice(0, 70)}`);
      }
    }
  }

  assert.deepEqual(
    offenders,
    [],
    "⛔ G-date-1 BUZILDI — sana xom `Intl` bilan yozilgan. uz-Latn da " +
      "u «2026 M08 19» bo'lib chiqadi. `formatBusinessDay(format, " +
      "isoDay, locale)` ishlating:\n  " +
      offenders.join("\n  "),
  );
});

test("G-date-1(b) — NAZORAT: aniqlagich sun'iy buzilishni USHLAYDI", () => {
  /*
   * ⛔ Darvozaning O'ZI ishlashini isbotlaydi. Usiz «0 ta buzilish»
   *    javobi «hech narsa topmadim» degani ham bo'lishi mumkin edi.
   */
  /*
   * ⛔ Namunada ICHKI QAVS (`new Date()`) ATAYIN bor — aynan shu shakl
   *    avvalgi regex-versiyani aldab o'tgan edi.
   */
  const sample = `
    const a = format.dateTime(new Date(), { day: "numeric", month: "long" });
    const b = format.dateTime(now, { timeStyle: "short" });
  `;
  const calls = dateTimeCalls(sample);

  assert.equal(calls.length, 2, "ikkala chaqiruv ham topilishi kerak");
  assert.match(calls[0], MONTH_NAME, "ichki qavsli chaqiruv o'tkazib yuborildi");
  assert.doesNotMatch(calls[1], MONTH_NAME, "soat chaqirig'i noto'g'ri belgilandi");

  /* ⛔ Raqamli oy — TO'G'RI shakl, u qizil bo'lmasligi kerak. */
  const numeric = dateTimeCalls(
    'format.dateTime(d, { day: "2-digit", month: "2-digit" })',
  );
  assert.doesNotMatch(numeric[0], MONTH_NAME, "raqamli oy noto'g'ri taqiqlandi");
});
