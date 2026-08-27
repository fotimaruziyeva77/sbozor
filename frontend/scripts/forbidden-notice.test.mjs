#!/usr/bin/env node
/**
 * G-FORBIDDEN: rad etish ekrani BITTA komponentda yashaydi (Topilma №K).
 *
 * =============================================================================
 * NEGA MEXANIK DARVOZA KERAK:
 *
 *   Yalang'och blok `src/app/[locale]/(app)/**\/page.tsx` da AYNAN 20 marta
 *   nusxa ko'chirilgan edi. Nazoratchi ulardan YETTITASINI sinab ko'rgan;
 *   qolgan o'n uchtasi ham xuddi shunday boshi berk edi. Yettitasini
 *   tuzatib qo'yish reyestr bandini «yopilgan» qilib, nosozlikni
 *   ilovaning uchdan ikki qismida TIRIK qoldirardi — va buni hech bir
 *   mavjud test ko'rmasdi.
 *
 *   Ikkinchi vazifasi kelajakka qaraydi: yigirma birinchi sahifa yozgan
 *   odam eski naqshni nusxa ko'chirsa, u CI'da yiqiladi.
 *
 * ⛔⛔ DARVOZA O'Z QOIDASINI O'ZI BUZMAYDI — VA BU TASODIF EMAS:
 *
 *   Bu faylning O'ZIDA `errors.forbidden` literali bir necha marta
 *   uchraydi (izohda ham, naqshda ham). U skanlanadigan to'plamga
 *   TUSHMAYDI, chunki darvoza `frontend/scripts/` da yashaydi, skanlash
 *   maydoni esa `frontend/src/app` — ikki daraxt kesishmaydi. Bu
 *   kodbazada besh marta takrorlangan sinf (`03-07`: «taqiqlangan
 *   literal konfiguratsiya faylida IZOHDA ham yozilmaydi»), shuning
 *   uchun chegara bu yerda OCHIQ belgilanadi.
 *
 * ⛔ SKANLASH MAYDONINING CHEGARASI — FAQAT `page.tsx`:
 *
 *   `errors.forbidden` ning IKKI QONUNIY iste'molchisi bor va ikkalasi
 *   ham ATAYIN tegilmaydi:
 *     * `src/lib/api-client.ts` — HTTP 403 ni matn KALITIGA o'giradi.
 *       U matn emas, tarjima kaliti qaytaradi va uni toast ham,
 *       blok ham iste'mol qiladi.
 *     * `src/components/cameras/live-view-dialog.tsx` — DIALOG ICHIDAGI
 *       holat. U yerda «Boshqaruv paneliga qaytish» havolasi
 *       foydalanuvchini dialogdan tashqariga, boshqa sahifaga olib
 *       chiqib ketardi — ya'ni yechim emas, yangi nosozlik bo'lardi.
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");
const APP_ROOT = path.join(SRC, "app");

/**
 * Konvertatsiya qilingan sahifalarning QUYI CHEGARASI.
 *
 * O'lchangan qiymat 20 (`grep -rl 'errors.forbidden' src/app
 * --include='page.tsx' | wc -l`). Chegara sifatida yozilishi
 * MAJBURIY: usiz bo'sh to'plam ustidagi tekshiruv («birorta sahifada
 * yalang'och blok yo'q») darvozani MUKAMMAL YASHIL qaytarardi —
 * jumladan komponent umuman ishlatilmagan holatda ham.
 */
const MIN_CONVERTED_PAGES = 20;

/** `src/lib/locale-href.ts` — `localeHref` ning YAGONA joyi. */
const LOCALE_HREF_MODULE = path.join(SRC, "lib", "locale-href.ts");

function walk(dir, match) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      out.push(...walk(full, match));
    } else if (match(entry)) {
      out.push(full);
    }
  }
  return out;
}

function read(file) {
  return readFileSync(file, "utf8");
}

function relative(file) {
  return path.relative(FRONTEND_ROOT, file).split(path.sep).join("/");
}

/** `src/app/**` daraxtidagi HAR bir `page.tsx`. */
function appPages() {
  return walk(APP_ROOT, (name) => name === "page.tsx");
}

test("G-FORBIDDEN (a): birorta `page.tsx` da yalang'och rad etish bloki YO'Q", () => {
  const pages = appPages();

  // Nazorat: skaner haqiqatan fayl topdi. Bo'sh ro'yxat ustidagi
  // sikl jimgina yashil qolardi (05-15 darsi).
  assert.ok(
    pages.length >= MIN_CONVERTED_PAGES,
    `\`src/app\` da atigi ${pages.length} ta \`page.tsx\` topildi — skaner yo'li eskirgan`,
  );

  const bare = pages
    .filter((file) => /t\(\s*["']errors\.forbidden["']\s*\)/u.test(read(file)))
    .map(relative);

  assert.deepEqual(
    bare,
    [],
    "Bu sahifalar rad etish blokini O'ZI chizmoqda — " +
      "`<ForbiddenNotice />` ga o'tkazilsin (Topilma №K):\n  " +
      bare.join("\n  "),
  );
});

test("G-FORBIDDEN (b): kamida 20 ta sahifa `ForbiddenNotice` ni import qiladi", () => {
  const importers = appPages()
    .filter((file) => read(file).includes("ForbiddenNotice"))
    .map(relative);

  assert.ok(
    importers.length >= MIN_CONVERTED_PAGES,
    `\`ForbiddenNotice\` ni atigi ${importers.length} ta sahifa ishlatmoqda ` +
      `(kutilgan: >= ${MIN_CONVERTED_PAGES}). Topilganlari:\n  ` +
      importers.join("\n  "),
  );
});

test("G-FORBIDDEN (c): `localeHref` `src/` da AYNAN BIR MARTA e'lon qilingan", () => {
  const sources = walk(SRC, (name) => name.endsWith(".ts") || name.endsWith(".tsx"));

  const declarations = sources
    .filter((file) => /^\s*(export\s+)?function localeHref\b/mu.test(read(file)))
    .map(relative);

  assert.deepEqual(
    declarations,
    [relative(LOCALE_HREF_MODULE)],
    "`localeHref` bir necha joyda e'lon qilingan (yoki umumiy moduldan " +
      "ko'chib ketgan). Yagona manba — `src/lib/locale-href.ts`:\n  " +
      declarations.join("\n  "),
  );
});
