#!/usr/bin/env node
/**
 * G-card-1 — `CardHeader` DA `justify-between` YOZILSA `flex-row` MAJBURIY.
 *
 * =============================================================================
 * NEGA BU DARVOZA BOR — 10 TA CHAQIRUVDAN 7 TASI XATO EDI (260819).
 *
 * `ui/card.tsx` dagi `CardHeader` ning asosi:
 *
 *     flex flex-col gap-1 px-5 pt-5 pb-3
 *
 * Ya'ni u USTUN. Kim `justify-between` yozsa, u QATOR kutadi —
 * «sarlavha chapda, tugma o'ngda». Ustunda esa:
 *
 *   · `justify-between` VERTIKAL taqsimlaydi (ko'pincha ta'sirsiz),
 *   · `items-end`       o'ng chekkaga tekislaydi (!), `items-start` esa
 *                       chapga — ya'ni tugma yonma-yon emas, PASTDA qoladi.
 *
 * Direktor panelidagi «Tushum trendi» kartasi aynan shu sabab
 * sarlavhasini o'ng chekkaga chiqarib qo'ygan edi — ekranga qaralganda
 * ko'rindi, kod o'qilganda emas: `flex flex-wrap items-end
 * justify-between` mutlaqo to'g'ri o'qiladi.
 *
 * ⛔ TUZOQ KOMPONENTDA, CHAQIRUVCHIDA EMAS — shuning uchun uni intizom
 *    bilan emas, DARVOZA bilan yopamiz. `flex-col` sukut bo'lib qoladi
 *    (uni o'zgartirish sinfsiz `CardHeader` larni buzardi), lekin
 *    `justify-between` yozilgan joyda `flex-row` TALAB qilinadi.
 * =============================================================================
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, "..", "src");

function sources(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) {
      out.push(...sources(path));
      continue;
    }
    if (!name.endsWith(".tsx")) continue;
    if (name.includes(".test.")) continue;
    out.push(path);
  }
  return out;
}

/** `<CardHeader className="…">` larning SINF SATRINI qaytaradi. */
export function cardHeaderClasses(text) {
  const out = [];
  const re = /<CardHeader\b[^>]*?className=\{?"([^"]*)"/g;
  let match;
  while ((match = re.exec(text)) !== null) out.push(match[1]);
  return out;
}

/** Qator kutayotgan, lekin qator qilinmagan sinf satrimi? */
export function isBrokenRow(classes) {
  const wantsRow =
    /\bjustify-between\b/.test(classes) || /\bitems-end\b/.test(classes);
  if (!wantsRow) return false;
  return !/\bflex-row\b/.test(classes);
}

test("G-card-1 — `justify-between` bo'lgan `CardHeader` larda `flex-row` bor", () => {
  const offenders = [];

  for (const path of sources(SRC)) {
    const rel = relative(SRC, path).split("\\").join("/");
    for (const classes of cardHeaderClasses(readFileSync(path, "utf8"))) {
      if (isBrokenRow(classes)) offenders.push(`${rel} — "${classes}"`);
    }
  }

  assert.deepEqual(
    offenders,
    [],
    "⛔ G-card-1 BUZILDI — `CardHeader` asosi `flex-col`. `justify-between` " +
      "yozilgan joyda `flex-row` ham yozilishi kerak, aks holda sarlavha va " +
      "tugma yonma-yon emas, ustma-ust chiziladi (`items-end` esa ularni " +
      "O'NG chekkaga tashlaydi):\n  " +
      offenders.join("\n  "),
  );
});

test("G-card-1(b) — NAZORAT: aniqlagich ikkala shoxni ham to'g'ri ajratadi", () => {
  /*
   * ⛔ Darvozaning O'ZI ishlashini isbotlaydi — usiz «0 ta buzilish»
   *    javobi «hech narsa topmadim» degani ham bo'lishi mumkin edi.
   */
  const broken = '<CardHeader className="flex flex-wrap items-end justify-between gap-4">';
  const fixed = '<CardHeader className="flex flex-row flex-wrap items-end justify-between gap-4">';
  const plain = '<CardHeader className="pb-2">';

  assert.equal(isBrokenRow(cardHeaderClasses(broken)[0]), true, "buzilgan shakl o'tkazib yuborildi");
  assert.equal(isBrokenRow(cardHeaderClasses(fixed)[0]), false, "to'g'ri shakl yolg'ondan ayblandi");
  assert.equal(isBrokenRow(cardHeaderClasses(plain)[0]), false, "oddiy ustun sarlavha yolg'ondan ayblandi");
});
