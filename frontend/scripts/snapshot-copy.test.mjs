#!/usr/bin/env node
/**
 * 4-FAZANING MATN VA YUZA DARVOZALARI — G-1, G-2, G-3, G-4, G-10.
 *
 * Beshala qoida ham FAQAT matn yoki import orqali yashaydi va aynan
 * shuning uchun ular eng oson jimgina buziladi: `<img>` qo'shish
 * typecheck'ni ham, lint'ni ham, birorta komponent testini ham
 * qizartirmaydi.
 *
 *   G-1  (§10.2)   «slot» — ORKESTRATSIYA MUHANDISINING atamasi, bozor
 *                  adminining emas. `capture_runs.slot_time` — DB ustuni;
 *                  foydalanuvchi uchun bu shunchaki VAQT.
 *
 *   G-10 (§10.2)   «kadrni o'chirish» — 04-RESEARCH §D.10: qator HECH
 *                  QACHON o'chirilmaydi, kadr faqat SIQILADI. So'z UI'ga
 *                  bir marta kirsa, tarjima orqali tarqaladi va D-18 ni
 *                  jimgina yolg'onga aylantiradi.
 *
 *   G-2  (§6.6)    Jurnalda thumbnail YO'Q — 175 rasm bir sahifada
 *                  tarmoqni ham, shaxsiy ma'lumot yuzasini ham portlatardi.
 *
 *   G-3  (D-19)    ⛔ Ogohlantirishda kadr rasmi HECH QACHON. Dalil-kadr
 *                  bozor tashrifchilarining shaxsiy ma'lumoti, Telegram
 *                  esa O'zR data-rezidentlik chegarasidan TASHQARIDA.
 *
 *   G-4  (§14.3)   ⛔ Ombor (SeaweedFS / S3) yuzasi brauzerga HECH QACHON
 *                  ochilmaydi. Audit, RLS va data-rezidentlik — uchalasi
 *                  shu BITTA chiziqqa tayanadi. Kadr `core-api` orqali
 *                  proxy qilinadi, presigned URL berilmaydi va so'ralmaydi.
 *
 * =============================================================================
 * ⚠ BU FAYL O'Z QOIDASINI O'ZI BUZMAYDI — VA BU TASODIF EMAS.
 *
 *   Darvoza `frontend/scripts/` da yashaydi; G-4 esa `frontend/src`
 *   daraxtini, G-1/G-10 esa `frontend/messages/` ni skanerlaydi. Ya'ni
 *   quyidagi taqiq ro'yxatlari o'z izlash satrlarini olib yuradi, LEKIN
 *   skanerlanadigan to'plamlardan TASHQARIDA.
 *
 *   Bu 2-fazada UCH MARTA takrorlangan sinf (`grep` kodni izohdan
 *   ajratmaydi) va 3-fazada u teskari yo'nalishda ham uchradi. Umumiy
 *   qoida: DARVOZA TANLAGAN MATN SINFINI OCHIQ BELGILASHI KERAK — har
 *   tekshiruvda chegara aniq yozilgan.
 *
 * ⚠ QAMROV CHEGARASI MAJBURIY (03-01 dan meros qoida).
 *
 *   Skaner bo'sh to'plamda ishlaganda HAR assert jimgina o'tib ketardi va
 *   darvoza mavjudligini yo'qotgan holda YASHIL bo'lib turaverardi. Shu
 *   sababdan: G-4 uchun fayllar soni >= 40; G-2/G-3 uchun katalog MAVJUD
 *   bo'lsa TO'RTALA fayl ham mavjud bo'lishi SHART. Katalog hali yo'q
 *   bo'lsa test o'tadi va SABABNI CHOP ETADI — «darvoza bor» degan da'vo
 *   shu bilan aniq chegaralanadi.
 * =============================================================================
 */
import assert from "node:assert/strict";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const MESSAGES_DIR = path.join(FRONTEND_ROOT, "messages");
const SRC_DIR = path.join(FRONTEND_ROOT, "src");
const SNAPSHOT_COMPONENTS_DIR = path.join(SRC_DIR, "components", "snapshots");

const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

/** Quyi chegara — bo'sh to'plam ustidagi sikl yashil bo'lmasin. */
const MIN_SCANNED_SOURCE_FILES = 40;

/**
 * Jurnal va ogohlantirish yuzalari qurilgan bo'lsa MAJBURIY fayllar.
 *
 * ⚠ NEGA RO'YXAT: fayl qayta nomlanganda (masalan `capture-cell.tsx` ->
 *   `capture-tile.tsx`) G-2 jimgina BO'SH to'plamda ishlab qolardi —
 *   darvoza yashil, tekshiruv esa yo'q. Ro'yxat buni qizil qiladi va
 *   keyingi ishlovchi darvozani ATAYIN yangilashi kerak bo'ladi.
 */
const REQUIRED_SNAPSHOT_COMPONENTS = [
  "capture-grid.tsx",
  "capture-cell.tsx",
  "alert-list.tsx",
  "alert-row.tsx",
];

/**
 * ⛔ TETIK KATALOG MAVJUDLIGI EMAS, MATN KATALOGI — 04-10 da O'LCHANGAN.
 *
 * Dastlabki shakl «`components/snapshots/` katalogi bor -> to'rtala fayl
 * ham bo'lsin» degan edi va u BITTA taxminga tayanardi: butun katalog
 * bitta rejada tug'iladi. Taxmin noto'g'ri chiqdi — `04-10` katalogni
 * zona A (jadval kartasi) bilan ochadi, jurnal va ogohlantirish yuzalari
 * esa `04-11` da keladi. O'lchov: `schedule-card.tsx` yaratilishi bilan
 * bu darvoza QIZARDI, holbuki hech narsa buzilmagan edi.
 *
 * Yangi tetik — `snapshots.cell.*` matn guruhi. U to'qqizta hujayra
 * holatining lug'ati (§11.6) va u AYNAN o'sha komponentlar bilan birga
 * keladi; ularsiz matnning iste'molchisi yo'q.
 *
 * ⚠ BU KUCHSIZLANTIRISH EMAS, KUCHAYTIRISH. Eski tetik katalog
 *   O'CHIRILGANDA jimgina yashil bo'lardi (katalog yo'q -> tekshiruv
 *   yo'q). Matn katalogi esa boshqa artefaktda yashaydi: to'rtala faylni
 *   birdaniga qayta nomlash yoki o'chirish `snapshots.cell.*` ni olib
 *   tashlamaydi, ya'ni darvoza baribir QIZARADI.
 */
const LOG_SURFACE_COPY_KEY = "cell";

/** Jurnal/ogohlantirish yuzalarining matni uchala tilda ham hali yo'qmi. */
function logSurfaceCopyMissing() {
  return LOCALES.every(
    (locale) =>
      Object.keys(loadMessages(locale).snapshots?.[LOG_SURFACE_COPY_KEY] ?? {})
        .length === 0,
  );
}

function loadMessages(locale) {
  return JSON.parse(readFileSync(path.join(MESSAGES_DIR, `${locale}.json`), "utf8"));
}

/** `snapshots` namespace'ini `kalit -> qiymat` juftliklariga yassilaydi. */
function flattenSnapshots(tree, prefix = "snapshots", out = new Map()) {
  for (const [key, value] of Object.entries(tree ?? {})) {
    const full = `${prefix}.${key}`;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flattenSnapshots(value, full, out);
    } else if (typeof value === "string") {
      out.set(full, value);
    }
  }
  return out;
}

function walkFiles(dir, extensions) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return []; // Katalog hali yaratilmagan (yuzalar 04-08…04-10 da keladi).
  }

  const files = [];
  for (const name of entries) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) {
      files.push(...walkFiles(full, extensions));
    } else if (extensions.some((ext) => name.endsWith(ext))) {
      files.push(full);
    }
  }
  return files;
}

/**
 * `snapshots` namespace'i uchala tilda ham hali yo'qmi.
 *
 * Yo'q bo'lsa G-1/G-10 tekshiradigan narsa yo'q — test O'TADI va sababni
 * CHOP ETADI. Jimgina o'tish «darvoza bor» degan yolg'on da'voni qoldirardi.
 */
function snapshotsNamespaceMissing() {
  return LOCALES.every((locale) => loadMessages(locale).snapshots === undefined);
}

/* ---------------------------------------------------------------------------
 * G-1 — «slot» SO'ZINING TAQIG'I (§10.2)
 * ------------------------------------------------------------------------ */

/**
 * ⚠ CHEGARA ANIQ: taqiq QIYMATLARGA tegishli, KALIT NOMLARIGA emas.
 *
 *   `snapshots.slotDuplicate` — QONUNIY kalit nomi: kod, DB, API va
 *   texnik hujjatlarda «slot» QOLADI (§10.2 ning oxirgi bandi). Taqiq
 *   faqat foydalanuvchi KO'RADIGAN matnga tegishli.
 *
 *   Kalitlarni ham taqiqlash keyingi ishlovchini kod atamasini o'zgartirishga
 *   majbur qilardi va u DB ustuni bilan ajralib ketardi.
 */
const FORBIDDEN_SLOT_WORDS = [/\bslot/iu, /слот/iu];

function hasSlotWord(text) {
  return FORBIDDEN_SLOT_WORDS.some((pattern) => pattern.test(text));
}

test("G-1: matcher AYNAN «slot» so'zini ushlaydi (nazorat)", () => {
  assert.ok(hasSlotWord("Har slot uchun bitta kadr"));
  assert.ok(hasSlotWord("Slot vaqti"));
  assert.ok(hasSlotWord("Для каждого слота"));
  assert.ok(hasSlotWord("слот"));

  // Salbiy nazorat: to'g'ri atamalar MATNDA BO'LISHI kerak.
  assert.ok(!hasSlotWord("Kadr olish vaqti"));
  assert.ok(!hasSlotWord("Kuniga 7 marta"));
  assert.ok(!hasSlotWord("Время съёмки"));
});

test("G-1: `snapshots.*` QIYMATLARIDA «slot» yo'q", () => {
  if (snapshotsNamespaceMissing()) {
    console.log(
      "[G-1] `snapshots` namespace'i hali uchala tilda ham yo'q — tekshiriladigan " +
        "matn yo'q. Darvoza copy qo'shilishi bilan AVTOMATIK kuchga kiradi.",
    );
    return;
  }

  for (const locale of LOCALES) {
    for (const [key, value] of flattenSnapshots(loadMessages(locale).snapshots)) {
      assert.ok(
        !hasSlotWord(value),
        `${locale}.json: "${key}" da «slot» bor (§10.2). Bu orkestratsiya ` +
          `muhandisining atamasi — «vaqt» / «kadr olish vaqti» yozing. Matn: ${JSON.stringify(value)}`,
      );
    }
  }
});

/* ---------------------------------------------------------------------------
 * G-10 — «KADRNI O'CHIRISH» TAQIG'I (§10.2, 04-RESEARCH §D.10)
 * ------------------------------------------------------------------------ */

/**
 * ⚠ CHEGARA ANIQ: taqiq «kadr» + «o'chirish» BIRIKMASIGA tegishli, yakka
 *   `o'chirish` fe'liga emas.
 *
 *   Sabab 3-fazada o'lchangan (`nvr-copy.test.mjs` G-4): matnda
 *   «Kadr … o'chirilmaydi» degan jumla BO'LISHI kerak — u aynan
 *   taqiqning TESKARISI va admin nima saqlanishini bilishi shart.
 *   Yakka o'zak bo'yicha qidiruv o'sha jumlani qizartirardi va darvoza
 *   o'zi himoya qilayotgan matnni o'zi taqiqlagan bo'lardi.
 *
 *   Apostrof variantlari (`'`, `ʻ`, `ʼ`, `‘`, `’`) qamraladi.
 */
const FORBIDDEN_DELETE_PHRASES = [
  /kadrni\s+o['ʻʼ‘’]chir/iu,
  /kadrlarni\s+o['ʻʼ‘’]chir/iu,
  /удалить\s+кадр/iu,
  /удалить\s+снимок/iu,
  // Kirill build'i hosila: `kadrni o'chirish` -> `кадрни ўчириш`.
  /кадрни\s+ўчир/iu,
  /кадрларни\s+ўчир/iu,
];

function hasFrameDeletePhrase(text) {
  return FORBIDDEN_DELETE_PHRASES.some((pattern) => pattern.test(text));
}

test("G-10: matcher AYNAN birikmani ushlaydi (nazorat)", () => {
  assert.ok(hasFrameDeletePhrase("Kadrni o'chirish"));
  assert.ok(hasFrameDeletePhrase("Kadrlarni o‘chirish"));
  assert.ok(hasFrameDeletePhrase("Удалить кадр"));
  assert.ok(hasFrameDeletePhrase("Удалить снимок"));
  assert.ok(hasFrameDeletePhrase("Кадрни ўчириш"));

  // Salbiy nazorat: bu jumlalar MATNDA BO'LISHI kerak (D-18).
  assert.ok(!hasFrameDeletePhrase("Kadr hech qachon o'chirilmaydi, faqat siqiladi"));
  assert.ok(!hasFrameDeletePhrase("Кадры никогда не удаляются, только сжимаются"));
  assert.ok(!hasFrameDeletePhrase("Filtrni tozalash"));
});

test("G-10: `snapshots.*` QIYMATLARIDA «kadrni o'chirish» yo'q", () => {
  if (snapshotsNamespaceMissing()) {
    console.log(
      "[G-10] `snapshots` namespace'i hali uchala tilda ham yo'q — tekshiriladigan " +
        "matn yo'q. Darvoza copy qo'shilishi bilan AVTOMATIK kuchga kiradi.",
    );
    return;
  }

  for (const locale of LOCALES) {
    for (const [key, value] of flattenSnapshots(loadMessages(locale).snapshots)) {
      assert.ok(
        !hasFrameDeletePhrase(value),
        `${locale}.json: "${key}" da «kadrni o'chirish» birikmasi bor. 04-RESEARCH ` +
          "§D.10: qator HECH QACHON o'chirilmaydi, kadr faqat SIQILADI (D-18). " +
          `Matn: ${JSON.stringify(value)}`,
      );
    }
  }
});

/* ---------------------------------------------------------------------------
 * G-2 va G-3 — RASM YUZASINING TAQIG'I
 * ------------------------------------------------------------------------ */

/** Jurnal matritsasi — thumbnail YO'Q (§6.6). */
const GRID_FILES = ["capture-grid.tsx", "capture-cell.tsx"];
const FORBIDDEN_GRID_TOKENS = ["<img", "next/image", "background-image"];

/** Ogohlantirish ro'yxati — dalil-kadr YO'Q (D-19). */
const ALERT_FILES = ["alert-list.tsx", "alert-row.tsx"];
const FORBIDDEN_ALERT_TOKENS = ["<img", "next/image", "/image"];

test("G-2/G-3 QAMROVI: jurnal matni bor bo'lsa TO'RTALA fayl ham mavjud", () => {
  if (logSurfaceCopyMissing()) {
    console.log(
      "[G-2/G-3] `snapshots.cell.*` hali uchala tilda ham yo'q (jurnal va " +
        "ogohlantirish yuzalari 04-11 da keladi) — tekshiriladigan komponent yo'q. " +
        "Matn qo'shilishi bilan bu test to'rtala faylni TALAB qiladi.",
    );
    return;
  }

  assert.ok(
    existsSync(SNAPSHOT_COMPONENTS_DIR),
    "`snapshots.cell.*` matni bor, lekin `src/components/snapshots/` katalogi YO'Q — " +
      "matnning iste'molchisi yo'qolgan, ya'ni G-2/G-3 bo'sh to'plam ustida ishlardi",
  );

  const present = new Set(readdirSync(SNAPSHOT_COMPONENTS_DIR));
  const missing = REQUIRED_SNAPSHOT_COMPONENTS.filter((name) => !present.has(name));

  assert.deepEqual(
    missing,
    [],
    `\`components/snapshots/\` katalogi bor, lekin quyidagi fayl(lar) yo'q: ${missing.join(", ")}. ` +
      "Fayl qayta nomlangan bo'lsa G-2/G-3 jimgina BO'SH to'plamda ishlab qolardi — " +
      "darvoza yashil, tekshiruv esa yo'q. Ro'yxatni ATAYIN yangilang.",
  );
});

test("G-2: jurnal matritsasida rasm yuzasi yo'q (§6.6)", () => {
  const hits = [];
  for (const name of GRID_FILES) {
    const file = path.join(SNAPSHOT_COMPONENTS_DIR, name);
    if (!existsSync(file)) continue;
    const source = readFileSync(file, "utf8");
    for (const token of FORBIDDEN_GRID_TOKENS) {
      if (source.includes(token)) hits.push(`${name}: ${token}`);
    }
  }

  assert.deepEqual(
    hits,
    [],
    "jurnal matritsasiga rasm yuzasi kirib qoldi (G-2):\n  " +
      `${hits.join("\n  ")}\n` +
      "  Bir sahifada 175 thumbnail tarmoqni ham, shaxsiy ma'lumot yuzasini ham " +
      "portlatardi. Kadr FAQAT o'z detalida ochiladi (§6.6).",
  );
});

test("G-3: ⛔ ogohlantirish qatorida dalil-kadr yo'q (D-19)", () => {
  const hits = [];
  for (const name of ALERT_FILES) {
    const file = path.join(SNAPSHOT_COMPONENTS_DIR, name);
    if (!existsSync(file)) continue;
    const source = readFileSync(file, "utf8");
    for (const token of FORBIDDEN_ALERT_TOKENS) {
      if (source.includes(token)) hits.push(`${name}: ${token}`);
    }
  }

  assert.deepEqual(
    hits,
    [],
    "ogohlantirish qatoriga kadr rasmi kirib qoldi (D-19):\n  " +
      `${hits.join("\n  ")}\n` +
      "  Dalil-kadr bozor tashrifchilarining SHAXSIY MA'LUMOTI, Telegram serverlari " +
      "esa loyiha zimmasiga olgan O'zR data-rezidentlik chegarasidan TASHQARIDA. " +
      "Ogohlantirishda FAQAT matn va sonlar bo'ladi.",
  );
});

/* ---------------------------------------------------------------------------
 * G-4 — ⛔ OMBOR YUZASINING TAQIG'I (§14.3)
 * ------------------------------------------------------------------------ */

/**
 * `frontend/src` da BO'LMASLIGI shart bo'lgan satrlar.
 *
 * `presign` — presigned URL (auditni buzadi, RLS'ni chetlab o'tadi);
 * `X-Amz`   — S3 imzo sarlavhalari;
 * `seaweed` — ombor serverining nomi;
 * `:8333`   — SeaweedFS S3 API porti.
 *
 * ⚠ RO'YXAT SHU FAYLDA YASHAYDI va shu fayl `frontend/scripts/` da —
 *   skanerlanadigan `frontend/src` daraxtidan TASHQARIDA. Ya'ni darvoza
 *   o'z izlash satrlarini o'zi TOPMAYDI.
 *
 * ⚠ Tekshiruv REGISTRGA SEZGIR EMAS: `X-AMZ-Date` ham, `x-amz-date` ham
 *   bir xil tutiladi (HTTP sarlavhalari registrsiz).
 */
const FORBIDDEN_STORAGE_TOKENS = ["presign", "X-Amz", "seaweed", ":8333"];

test("G-4: ⛔ `frontend/src` da ombor yuzasining izlari yo'q (§14.3)", () => {
  const files = walkFiles(SRC_DIR, [".ts", ".tsx"]);

  assert.ok(
    files.length >= MIN_SCANNED_SOURCE_FILES,
    `frontend/src da atigi ${files.length} fayl skanerlandi (kutilgan >= ` +
      `${MIN_SCANNED_SOURCE_FILES}) — yo'l noto'g'ri bo'lsa bu darvoza bo'sh to'plam ` +
      "ustida ishlab, jimgina yashil qolardi",
  );

  const hits = [];
  for (const file of files) {
    const source = readFileSync(file, "utf8").toLowerCase();
    for (const token of FORBIDDEN_STORAGE_TOKENS) {
      if (source.includes(token.toLowerCase())) {
        hits.push(`${path.relative(FRONTEND_ROOT, file)}: ${token}`);
      }
    }
  }

  assert.deepEqual(
    hits,
    [],
    "ombor yuzasi frontend kodiga kirib qoldi (§14.3):\n  " +
      `${hits.join("\n  ")}\n` +
      "  Presigned URL auditni BUZADI (havola muddati tugagunicha `audit_read` siz " +
      "ishlaydi), RLS'ni CHETLAB O'TADI (rol o'zgarsa ham havola tirik) va ombor " +
      "manzilini OSHKOR QILADI. Kadrning YAGONA yo'li: " +
      "`GET /api/v1/snapshots/{id}/image` — core-api orqali proxy.",
  );
});

test("G-4: skaner haqiqatan fayl mazmunini o'qiydi (nazorat)", () => {
  /*
   * Usiz yuqoridagi test `readFileSync` bo'sh satr qaytargan taqdirda ham
   * yashil bo'lardi — quyi chegara faqat fayllar SONINI tekshiradi,
   * ularning O'QILGANINI emas.
   */
  const files = walkFiles(SRC_DIR, [".ts", ".tsx"]);
  const known = files.find((file) => file.endsWith(path.join("lib", "api-client.ts")));

  assert.ok(known, "api-client.ts skanerlangan to'plamda topilmadi");
  assert.ok(
    readFileSync(known, "utf8").includes("fetch"),
    "skaner fayl mazmunini o'qimayapti — yuqoridagi darvoza ma'nosiz",
  );
});

/* ---------------------------------------------------------------------------
 * G-36 — `ALERT_TITLE_KEYS` REYESTRI UCHALA LOCALE BILAN MEXANIK BOG'LANADI.
 *
 * ⛔⛔ NEGA BU BAND MAVJUD — VA U «YAXSHI BO'LARDI» EMAS, BO'SHLIQ EDI.
 *
 *   `deferred-items.md` ning 1-bandi (07-15 da o'lchangan): reyestrning
 *   o'n beshala a'zosi bugun uchala tilda ham matnga ega — buni 07-15
 *   ⛔ QO'LDA sanagan. Lekin `frontend/scripts/*.test.mjs` ichida
 *   reyestrni `messages/*.json` bilan bog'laydigan BIRORTA darvoza yo'q
 *   edi. Ya'ni holat bugun TOZA, uni ushlab turadigan mexanizm esa
 *   YO'Q: o'n oltinchi a'zo matnsiz qo'shilsa ekranda zaxira yorlig'i
 *   chiqardi va buni HECH NIMA aytmasdi.
 *
 *   Bu `error-codes.test.mjs` ning G-17 bloki allaqachon yopgan sinfning
 *   AYNAN O'ZI, faqat boshqa reyestr ustida. Shakl ham o'sha yerdan
 *   ko'chiriladi: reyestrdan OLDINGA (tur -> matn) va TESKARI
 *   (matn -> tur).
 *
 * ⛔ ZAXIRA YORLIQ (`errors.generic`) — REYESTRDAN TASHQARIDA VA BU
 *    ATAYIN. `alert-row.tsx` noma'lum `alert_key` uchun uni chizadi,
 *    ya'ni u `snapshots.alertKey.*` guruhiga KIRMAYDI va teskari skanni
 *    ifloslantirmaydi. Uning MAVJUDLIGI esa alohida o'lchanadi: zaxira
 *    yo'lning o'zi buzilgan bo'lsa noma'lum ogohlantirish ekranni BO'SH
 *    qoldirardi.
 *
 * ⚠ O'LCHAM QULFLANGAN (`ALERT_TITLE_KEY_COUNT`): parser sinsa yoki
 *   reyestr boshqa shaklga o'tkazilsa quyidagi sikllar BO'SH to'plamda
 *   yugurib jimgina yashil bo'lardi. Yangi a'zo qo'shgan ijrochi bu
 *   sonni ATAYIN yangilaydi va o'shanda uchala matnni ham yozadi.
 * ------------------------------------------------------------------------ */

const ALERT_ROW = path.join(SNAPSHOT_COMPONENTS_DIR, "alert-row.tsx");

/** §11.7 — bugungi ogohlantirish turlarining soni (07-08 + 07-14 + Topilma №I). */
const ALERT_TITLE_KEY_COUNT = 16;

/** `snapshots.alertKey.*` — ogohlantirish sarlavhalarining YAGONA guruhi. */
const ALERT_KEY_GROUP = "alertKey";

/** Noma'lum `alert_key` uchun chiziladigan zaxira yorliq (`alert-row.tsx`). */
const ALERT_FALLBACK_TRAIL = ["errors", "generic"];

/** `alert_kind: "snapshots.alertKey.xxx",` juftliklarini o'qiydi. */
function readAlertTitleKeys() {
  const source = readFileSync(ALERT_ROW, "utf8");
  const block = /const ALERT_TITLE_KEYS[^{]*\{([\s\S]*?)\n\} as const;/u.exec(source);
  assert.ok(block, "`ALERT_TITLE_KEYS` topilmadi — parser sinigan");
  return [
    ...block[1].matchAll(/^\s+([a-z_]+):\s*"snapshots\.alertKey\.([A-Za-z]+)"/gmu),
  ].map((match) => [match[1], match[2]]);
}

function lookupTrail(tree, trail) {
  return trail.reduce((node, step) => (node ?? {})[step], tree);
}

test("G-36: `ALERT_TITLE_KEYS` o'qildi va AYNAN o'n besh a'zo (nazorat)", () => {
  const pairs = readAlertTitleKeys();

  assert.equal(
    pairs.length,
    ALERT_TITLE_KEY_COUNT,
    `ALERT_TITLE_KEYS dan ${pairs.length} a'zo o'qildi, kutilgan ` +
      `${ALERT_TITLE_KEY_COUNT}. Yangi tur qo'shgan bo'lsangiz — bu sonni ` +
      "yangilang VA uchala locale'ga matn yozing, aks holda ekranda zaxira " +
      "yorlig'i chiqadi va buni hech nima aytmaydi.",
  );
  assert.equal(
    new Set(pairs.map(([kind]) => kind)).size,
    pairs.length,
    "takrorlangan `alert_key`",
  );
  assert.equal(
    new Set(pairs.map(([, leaf]) => leaf)).size,
    pairs.length,
    "ikki tur BITTA matn kalitiga ishora qilyapti — biri o'zgarsa ikkinchisi " +
      "jimgina noto'g'ri sarlavha chizardi",
  );
});

test("G-36: HAR reyestr a'zosining matni UCHALA tilda bor (OLDINGA)", () => {
  const pairs = readAlertTitleKeys();
  const problems = [];

  for (const locale of LOCALES) {
    const group = loadMessages(locale).snapshots?.[ALERT_KEY_GROUP] ?? {};
    for (const [kind, leaf] of pairs) {
      if (typeof group[leaf] !== "string" || group[leaf].trim() === "") {
        problems.push(
          `${locale}.json: snapshots.${ALERT_KEY_GROUP}.${leaf} YO'Q ` +
            `(\`${kind}\` turi uchun)`,
        );
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "reyestrda tur bor, matn YO'Q — ekranda zaxira yorlig'i chiziladi:\n  " +
      problems.join("\n  "),
  );
});

test("G-36: HAR matn kaliti reyestrda bor — O'LIK KALIT yo'q (TESKARI)", () => {
  const leaves = new Set(readAlertTitleKeys().map(([, leaf]) => leaf));
  const problems = [];

  for (const locale of LOCALES) {
    const group = loadMessages(locale).snapshots?.[ALERT_KEY_GROUP] ?? {};
    for (const leaf of Object.keys(group)) {
      if (!leaves.has(leaf)) {
        problems.push(
          `${locale}.json: snapshots.${ALERT_KEY_GROUP}.${leaf} reyestrda YO'Q`,
        );
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "matn bor, uni chizadigan tur YO'Q — o'lik kalit tarjimonni ham, keyingi " +
      "ijrochini ham chalg'itadi:\n  " + problems.join("\n  "),
  );
});

test("G-36: zaxira yorliq UCHALA tilda bor (reyestrdan TASHQARIDA)", () => {
  /*
   * ⛔ NEGA ALOHIDA: `errors.generic` `snapshots.alertKey.*` guruhida
   *   EMAS, ya'ni yuqoridagi ikki darvoza uni UMUMAN ko'rmaydi. Lekin
   *   AYNAN u noma'lum `alert_key` kelganda chiziladi — u yo'q bo'lsa
   *   yangi backend turi ekranni BO'SH qoldirardi.
   */
  const missing = LOCALES.filter(
    (locale) =>
      typeof lookupTrail(loadMessages(locale), ALERT_FALLBACK_TRAIL) !== "string",
  );

  assert.deepEqual(
    missing,
    [],
    `zaxira yorliq (${ALERT_FALLBACK_TRAIL.join(".")}) yo'q: ${missing.join(", ")} — ` +
      "noma'lum ogohlantirish turi ekranni BO'SH qoldirardi",
  );
});
