#!/usr/bin/env node
/**
 * G-dir-1 — DIREKTOR PANELIDAGI KATAK TARTIBI RAQAMLARGA MOS.
 *
 * =============================================================================
 * NEGA BU DARVOZA BOR — U JONLI NUQSONDAN TUG'ILGAN (260819).
 *
 * `tile.tsx` o'ng yuqorida tartib raqamini chizadi va uning izohida
 * VA'DA yozilgan: «direktor telefonda `uchinchi katakka qara` deb
 * aytishi mumkin bo'lishi kerak».
 *
 * Kataklar ma'no bo'yicha guruhlanganda (GURUH: PUL / NAZORAT) ular
 * ko'chirildi, raqamlar esa eski joyida qoldi. Ekranda ular
 * «1 · 3 · 6 · 2 · 4 · 5» bo'lib o'qildi — ya'ni belgi o'z va'dasini
 * BAJARMAY, shovqinga aylandi. Bu brauzerda o'lchandi, kodni o'qib
 * emas: `six-tiles.tsx` diff'i mukammal ko'rinardi.
 *
 * IKKINCHI, KO'ZGA KAM TASHLANADIGAN TOMONI — `step`. U kirish
 * animatsiyasining kechikishi (`--i` × 60ms). U ham eski joyida
 * qolgani uchun kataklar setka bo'ylab SAKRAB paydo bo'lardi:
 * Tushum -> Band -> Qarz -> Bandlik -> AI -> Kassirlar. Foydalanuvchi
 * qo'ygan doimiy qoida esa aniq: «animatsiya insonni charchatmasin».
 * Ko'z bo'ylab OQADIGAN navbat tinchlantiradi, sakraydigani qitiqlaydi.
 *
 * ⛔ SHUNING UCHUN DARVOZA IKKALASINI HAM O'LCHAYDI va ular BIR XIL
 *    bo'lishini talab qiladi: raqam nima desa, harakat ham shuni deydi.
 * =============================================================================
 *
 * ⚠ NEGA MANBA MATNI, DOM EMAS: bu faylda JSX tartibi = setka tartibi
 *   (tekis grid, `order` xossasi ishlatilmaydi, bosh katak esa butun
 *   qatorni egallaydi). Ya'ni manbadagi ketma-ketlik ko'rinadigan
 *   ketma-ketlikning O'ZI. Darvoza arzon, aniq va `npm run test:unit`
 *   ichida sekundning ulushida ishlaydi.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

const HERE = dirname(fileURLToPath(import.meta.url));
const TILES = join(HERE, "..", "src", "components", "director", "six-tiles.tsx");
const TILE = join(HERE, "..", "src", "components", "panel", "tile.tsx");

const source = readFileSync(TILES, "utf8");

/**
 * `<PanelTile … />` ochilish teglarini FAYL TARTIBIDA qaytaradi.
 * Har biri uchun `index` (bo'lmasa `null`) va `step` olinadi.
 */
function tiles() {
  const found = [];
  const re = /<PanelTile\b([\s\S]*?)>/g;
  let match;
  while ((match = re.exec(source)) !== null) {
    const props = match[1];
    const index = /\bindex=\{(\d+)\}/.exec(props);
    const step = /\bstep=\{(\d+)\}/.exec(props);
    const label = /\blabel="([^"]+)"/.exec(props);
    found.push({
      index: index === null ? null : Number(index[1]),
      step: step === null ? null : Number(step[1]),
      label: label === null ? null : label[1],
    });
  }
  return found;
}

test("G-dir-1(a) — panelda bosh katak + aynan olti raqamli katak bor", () => {
  const list = tiles();
  assert.equal(list.length, 7, `kutilgan 7 ta katak, topildi ${list.length}`);

  const hero = list[0];
  assert.equal(
    hero.index,
    null,
    "bosh katakda tartib raqami BO'LMASLIGI kerak — u ro'yxatning " +
      "a'zosi emas, ro'yxat javob beradigan savol",
  );

  const numbered = list.slice(1);
  assert.equal(numbered.length, 6, "raqamli kataklar soni 6 bo'lishi kerak");
  for (const tile of numbered) {
    assert.notEqual(
      tile.index,
      null,
      `«${tile.label}» katagida tartib raqami yo'q`,
    );
  }
});

test("G-dir-1(b) — raqamlar O'QISH TARTIBIDA 1..6", () => {
  const numbered = tiles().slice(1);
  const actual = numbered.map((tile) => tile.index);
  const expected = [1, 2, 3, 4, 5, 6];

  assert.deepEqual(
    actual,
    expected,
    "kataklar ekranda yuqoridan pastga, chapdan o'ngga o'qiladi — " +
      `raqamlar shu tartibda bo'lishi kerak. Topildi: ${actual.join(" · ")} ` +
      `(${numbered.map((tile) => tile.label).join(" · ")})`,
  );
});

test("G-dir-1(c) — animatsiya navbati raqam bilan BIR XIL", () => {
  const list = tiles();

  assert.equal(list[0].step, 0, "bosh katak birinchi paydo bo'ladi (step 0)");

  for (const tile of list.slice(1)) {
    assert.equal(
      tile.step,
      tile.index,
      `«${tile.label}»: raqam ${tile.index}, harakat navbati ${tile.step} — ` +
        "ular ajralsa kataklar setka bo'ylab sakrab chiqadi",
    );
  }
});

test("G-dir-1(d) — `index` IXTIYORIY bo'lib qoladi va berilmasa belgi chizilmaydi", () => {
  /*
   * ⛔ Bu shart `tile.tsx` da: `index` majburiy qilib qaytarilsa, bosh
   *    katak yana raqam olishga majbur bo'lardi va u ekranda «0» bo'lib
   *    ko'rinardi — aynan foydalanuvchi ko'rgan holat.
   */
  const tile = readFileSync(TILE, "utf8");

  assert.match(
    tile,
    /index\?:\s*number/,
    "`panel/tile.tsx` da `index` ixtiyoriy (`index?: number`) bo'lishi kerak",
  );
  assert.match(
    tile,
    /index === undefined \? null :/,
    "`panel/tile.tsx` `index` berilmaganda belgini UMUMAN chizmasligi kerak",
  );
});
