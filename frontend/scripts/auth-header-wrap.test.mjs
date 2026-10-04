#!/usr/bin/env node
/**
 * Kirish sahifasi sarlavhasi 375px da KESILMAYDI.
 *
 * =============================================================================
 * ⛔⛔ BRAUZERDA O'LCHANGAN NUQSON (261004, 375px — iPhone SE kengligi):
 *
 *     header (px-6 ichida)             327px
 *     ichki guruh (til + «qaytish»)    251px, o'ng chekkasi 383px
 *     => «Saytga qaytish» AYNAN 8px KESILGAN
 *
 *     `flex-wrap: wrap` dan keyin: o'ng chekka 346px, ya'ni 29px zaxira.
 *
 * ⛔ NEGA BU NUQSON KO'ZGA TASHLANMAGAN VA NEGA AVTOTEST QIYIN:
 *
 *   1. Sahifa SILJIMAYDI. Tashqi `.login-scene` da `overflow: hidden`,
 *      ya'ni toshgan matn scrollbar bermasdan shunchaki qirqiladi.
 *      `scrollWidth === clientWidth === 375` — demak "gorizontal siljish
 *      bormi" degan har qanday tekshiruv buni TOPMAYDI.
 *
 *   2. jsdom TARTIBNI HISOBLAMAYDI: `vitest` ichida har elementning
 *      kengligi 0, ya'ni kesilishni u yerda o'lchab bo'lmaydi.
 *
 * Shuning uchun darvoza MANBA darajasida: sarlavha `flex-wrap` siz
 * qolsa — qizaradi. Bu kesilishning O'ZINI o'lchamaydi, lekin uni
 * tuzatgan YAGONA sinfni qo'riqlaydi.
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const LAYOUT = path.join(
  FRONTEND_ROOT,
  "src",
  "app",
  "[locale]",
  "(auth)",
  "layout.tsx",
);

test("kirish sahifasi sarlavhasi `flex-wrap` bilan", () => {
  const manba = readFileSync(LAYOUT, "utf8");

  /*
   * ⛔ QUYI CHEGARA — USIZ TEST TRIVIAL O'TARDI.
   *   Fayl ko'chirilsa yoki markup qayta yozilsa `<header` umuman
   *   topilmasdi va "flex-wrap bor" tekshiruvi hech narsa ustida
   *   ishlamasdi. Avval SARLAVHA borligini isbotlaymiz.
   */
  const satr = manba
    .split("\n")
    .find((s) => s.includes("<header") && s.includes("className="));

  assert.ok(
    satr !== undefined,
    "`(auth)/layout.tsx` da className'li `<header>` topilmadi — " +
      "markup ko'chirilgan bo'lsa, bu darvoza ham ko'chirilsin.",
  );

  assert.ok(
    satr.includes("flex-wrap"),
    "Kirish sahifasi sarlavhasida `flex-wrap` YO'Q.\n" +
      "375px da «Saytga qaytish» 8px kesiladi va `overflow: hidden` " +
      "tufayli sahifa SILJIMAYDI — ya'ni buni ko'z ham, scroll " +
      "tekshiruvi ham sezmaydi.\n" +
      `Hozirgi satr: ${satr.trim()}`,
  );
});
