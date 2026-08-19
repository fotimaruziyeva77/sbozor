#!/usr/bin/env node
/**
 * G-dir-1 — KATAKLARNING KIRISH NAVBATI O'QISH TARTIBIDA.
 *
 * =============================================================================
 * NEGA BU DARVOZA BOR — U JONLI NUQSONDAN TUG'ILGAN (260819).
 *
 * `step` — kirish animatsiyasining kechikishi (`--i` × 60ms). Kataklar
 * ma'no bo'yicha guruhlanganda (PUL / NAZORAT) ular ko'chirildi, `step`
 * esa eski joyida qoldi. Natijada kataklar setka bo'ylab SAKRAB paydo
 * bo'lardi: Tushum -> Band -> Qarz -> Bandlik -> AI -> Kassirlar.
 *
 * Foydalanuvchi qo'ygan doimiy qoida esa aniq: «animatsiya insonni
 * charchatmasin». Ko'z bo'ylab OQADIGAN navbat tinchlantiradi,
 * sakraydigani qitiqlaydi. Bu brauzerda o'lchandi, kodni o'qib emas:
 * `six-tiles.tsx` diff'i mukammal ko'rinardi.
 *
 * ⛔⛔ TARTIB RAQAMI (`index`) ENDI O'LCHANMAYDI — U UMUMAN YO'Q.
 *
 *     Darvozaning birinchi shakli katak burchagidagi 1–6 raqamini ham
 *     tekshirardi. Stitch maketiga solishtirilganda ma'lum bo'ldiki,
 *     u yerda raqam UMUMAN yo'q — va Stitch haq: raqam hech qanday
 *     savolga javob bermaydi, kartani YORLIQ va IKONKA nomlaydi.
 *     Raqam olib tashlandi; darvoza esa kuchini saqlagan ikki da'voga
 *     qisqartirildi — navbat to'g'ri, va raqam QAYTMAYDI.
 * =============================================================================
 *
 * ⚠ NEGA MANBA MATNI, DOM EMAS: bu faylda JSX tartibi = setka tartibi
 *   (tekis grid, `order` xossasi ishlatilmaydi, bosh katak esa butun
 *   qatorni egallaydi). Ya'ni manbadagi ketma-ketlik ko'rinadigan
 *   ketma-ketlikning O'ZI.
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
 * `<PanelTile … >` ochilish teglarining PROPS MATNINI fayl tartibida
 * qaytaradi.
 *
 * ⛔ Qavs sanagichi bilan, lazy regex bilan EMAS: props ichida `{…}`
 *    va ichma-ich JSX bor, lazy shakl esa birinchi `>` da to'xtab,
 *    kataklarni o'tkazib yuborardi (aynan shu xato `uz-latn-date`
 *    darvozasida sabotaj sinovida topilgan).
 */
function tiles() {
  const found = [];
  const opener = /<PanelTile\b/g;
  let match;
  while ((match = opener.exec(source)) !== null) {
    let depth = 0;
    let i = opener.lastIndex;
    while (i < source.length) {
      const ch = source[i];
      if (ch === "{") depth += 1;
      else if (ch === "}") depth -= 1;
      else if (ch === ">" && depth === 0) break;
      i += 1;
    }
    const props = source.slice(opener.lastIndex, i);
    const step = /\bstep=\{(\d+)\}/.exec(props);
    const label = /\blabel="([^"]+)"/.exec(props);
    found.push({
      step: step === null ? null : Number(step[1]),
      label: label === null ? null : label[1],
    });
  }
  return found;
}

test("G-dir-1(a) — panelda bosh katak + oltita katak bor", () => {
  const list = tiles();
  assert.equal(list.length, 7, `kutilgan 7 ta katak, topildi ${list.length}`);
  for (const tile of list) {
    assert.notEqual(tile.step, null, `«${tile.label}» katagida \`step\` yo'q`);
  }
});

test("G-dir-1(b) — kirish navbati O'QISH TARTIBIDA 0..6", () => {
  const list = tiles();
  const actual = list.map((tile) => tile.step);
  const expected = [0, 1, 2, 3, 4, 5, 6];

  assert.deepEqual(
    actual,
    expected,
    "kataklar ekranda yuqoridan pastga, chapdan o'ngga o'qiladi — " +
      "kirish animatsiyasi ham AYNAN shu navbatda bo'lishi kerak, aks " +
      "holda ular setka bo'ylab sakrab chiqadi. Topildi: " +
      `${actual.join(" · ")} (${list.map((tile) => tile.label).join(" · ")})`,
  );
});

test("G-dir-1(c) — katak burchagidagi tartib raqami QAYTMAYDI", () => {
  assert.doesNotMatch(
    source,
    /\bindex=\{/,
    "`six-tiles.tsx` da `index` propi qaytdi — Stitch maketida katak " +
      "burchagida raqam YO'Q",
  );

  assert.doesNotMatch(
    readFileSync(TILE, "utf8"),
    /\bindex\??:\s*number/,
    "`panel/tile.tsx` da `index` propi qaytdi",
  );
});
