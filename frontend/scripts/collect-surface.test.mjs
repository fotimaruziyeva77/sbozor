#!/usr/bin/env node
/**
 * G-7 (frontend yarmi) · G-22 · G-28(d) — KASSIR YUZASINING STATIK CHEGARASI.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — UCH XIL NARSA, BITTA MEXANIZM.
 *
 * 1. ⛔ KO'R NAQD DEKLARATSIYASI (G-7, 06-RESEARCH; D-25, §10.3/§10.4).
 *    Kassir smenani yopganda o'z naqdini SANAB kiritadi va tizim unga
 *    o'z summasini ko'rsatmaydi. Farq (variance) ham ko'rsatilmaydi,
 *    chunki `tizim = deklaratsiya − farq` — bitta ayirish. Ya'ni farqni
 *    ko'rsatish tizim summasini ko'rsatish bilan MATEMATIK JIHATDAN
 *    bir xil.
 *
 * 2. ⛔ PUL ARIFMETIKASINING KIRISH MA'LUMOTI (G-22, 06-UI-SPEC; D-17,
 *    D-20). Proyeksiyada tarif identifikatori bo'lmasa, klient summani
 *    hisoblab chiqara OLMAYDI — taqiq IMKONSIZLIKKA aylanadi.
 *
 * 3. ⛔ SHAXSIY MA'LUMOT (G-22 ning ikkinchi yarmi; C-10, §5.5). Kassir
 *    yuzasida ism ham, telefon ham yo'q — va NOM BILAN AYLANIB O'TISH
 *    (`vendor_label`, `payer`, `who`) ham taqiqlanadi. Reyestr shu
 *    qoidaning uyi.
 * =============================================================================
 *
 * ⚠ BU DARVOZA `components/collect/` ALOHIDA KATALOG VA
 *   `lib/billing-pending-queries.ts` ALOHIDA MODUL BO'LGANI UCHUNGINA
 *   YOZILISHI MUMKIN (06-UI-SPEC §5.3, W0-F3). Proyeksiya va yozilgan
 *   hisob bitta modulda yashaganda taqiqlangan nomlar QONUNIY bo'lardi
 *   (DL-3 hisob identifikatorisiz ochilmaydi) va shart KONTEKSTGA
 *   BOG'LIQ holga aylanardi — ya'ni matn skani bilan tekshirib
 *   bo'lmaydigan, kod-ko'rikka qaytadigan shartga.
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (D-32). Katalog `readdirSync`
 *   bilan REKURSIV o'qiladi. 05-16 W-2 ning darsi: qo'lda yozilgan
 *   komponent ro'yxati yangi fayl paydo bo'lganda JIMGINA yashil qoladi.
 *
 * ⚠ TO'PLAM TENGLIGI, `not.toContain` EMAS (D-31). Inkor tasdiq FAQAT
 *   aynan o'sha nomni ushlaydi; maydon qayta nomlansa u o'tib ketardi
 *   (05-14 sabotaj S7). Shuning uchun natija `assert.deepEqual(hits, [])`
 *   bilan o'lchanadi.
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN QIDIRILADI. Filtrsiz bu darvoza
 *   o'z-o'ziga qarshi ishlardi: «bu maydonni bu yerga qo'yish
 *   taqiqlanadi» degan izohning O'ZI uni qizartirardi. 2 va 3-fazada
 *   aynan shu sinf 15+ marta yuz bergan.
 *
 * ⛔ FILTR `bulk-action-surface.test.mjs:163-225` DAN KO'CHIRILDI —
 *    UCHINCHI implementatsiya YOZILMAYDI (06-UI-SPEC W0-F4). Holat
 *    mashinasi bayt-ba-bayt bir xil; farq faqat JSDoc matnida.
 *
 * ⚠ SATRLAR (`"..."`, `'...'`, `` `...` ``) OLIB TASHLANMAYDI va bu
 *   ATAYIN: tarjima kaliti, kesh kaliti yoki `data-testid` ichidagi
 *   taqiqlangan nom ham BRAUZERGA yetib boradi, ya'ni u ham taqiq
 *   ostida.
 *
 * ⚠ REYESTR UZUNLIGI `assert` BILAN SANALADI va bu fayl SKANERLANADIGAN
 *   to'plamda YO'Q (`frontend/scripts/` — `frontend/src` daraxtidan
 *   tashqarida). Ya'ni darvoza o'z izlash satrlarini o'zi TOPMAYDI.
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

/** ⛔ Kassir komponentlari — ALOHIDA katalog (06-UI-SPEC §5.2). */
const COLLECT_COMPONENTS = path.join(SRC, "components", "collect");

/** ⛔ Proyeksiya so'rovlari — ALOHIDA modul (W0-F3, §5.3). */
const PENDING_QUERIES = path.join(SRC, "lib", "billing-pending-queries.ts");

/** Skanerlanadigan kengaytmalar. */
const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

/** Mahsulot fayli emas — qamrovdan chiqadi (u taqiqni O'LCHAYDI, buzmaydi). */
const TEST_FILE = /\.test\.tsx?$/;

/* -------------------------------------------------------------------------- */
/* G-22 — TAQIQLANGAN NOMLAR REYESTRI (06-UI-SPEC §15.3)                      */
/* -------------------------------------------------------------------------- */

/**
 * Kassir yuzasida UCHRAMAYDIGAN nomlar — camelCase va snake_case JUFT.
 *
 * ⚠ JUFTLIK ATAYIN: server maydoni snake_case bo'ladi, klient
 *   o'zgaruvchisi esa camelCase — bittasini qoldirish taqiqni bitta
 *   qayta nomlash bilan chetlab o'tsa bo'ladigan qilardi.
 */
const FORBIDDEN_NAMES = [
  "charge_id",
  "chargeId",
  "tariff_id",
  "tariffId",
  "category_id",
  "categoryId",
  "valid_from",
  "vendor_name",
  "vendorName",
  "phone",
  "full_name",
  "fullName",
  "balance",
  "balance_soum",
  "occupied_slots",
  "is_billable",
];

/**
 * Reyestrning QUYI CHEGARASI.
 *
 * ⚠ Usiz reyestr bo'shatilsa darvoza BO'SH TO'PLAM ustida ishlab,
 *   abadiy yashil qolardi. Chegara QUYI: yangi nom qo'shilganda bu son
 *   o'zgarmaydi (06-UI-SPEC §15.3 «reyestrda ≥14 nom»).
 */
const MIN_FORBIDDEN_NAMES = 14;

/* -------------------------------------------------------------------------- */
/* G-7 (frontend yarmi) — KO'R DEKLARATSIYA YUZASI                            */
/* -------------------------------------------------------------------------- */

/**
 * Kassir yuzasida UCHRAMAYDIGAN «yig'indiga olib boradigan» tokenlar.
 *
 * ⛔ Ular BOSHQA yuzada (direktor, `lib/shift-queries.ts`) QONUNIY va bu
 *    ziddiyat emas: darvozaning qamrovi kassir YUZASI, «smena» DOMENI
 *    emas (06-UI-SPEC §15.3, G-7).
 */
const BLIND_DECLARATION_TOKENS = [
  "system_soum",
  "system_total_soum",
  "expected_soum",
  "variance",
  "varianceSoum",
  "variance_soum",
  "payment_count",
  "cash_count",
  "terminal_soum",
];

const MIN_BLIND_DECLARATION_TOKENS = 7;

/**
 * `components/collect/` katalogining QAMROV CHEGARASI.
 *
 * Katalog mavjud bo'lsa kamida shuncha MAHSULOT fayli bo'lishi SHART
 * (06-UI-SPEC §15.3, G-7(c)). §5.2 ga ko'ra bu yuzada yettita komponent
 * rejalashtirilgan, ya'ni beshta chegara QUYI va u jimgina torayishni
 * ushlaydi.
 */
const MIN_COLLECT_FILES = 5;

/* -------------------------------------------------------------------------- */
/* G-28(d) — DALIL KADRI KASSIR YUZASIDA YO'Q                                 */
/* -------------------------------------------------------------------------- */

/**
 * Dalil-kadr yuzasining izlari.
 *
 * ⛔ NEGA BU ENG ARZON XAVFSIZLIK YUTUG'I [O'LCHANDI: M-8]: kassir pul
 *    yig'adi, hukm chiqarmaydi — kadr uning ishida hech narsani
 *    o'zgartirmaydi. Lekin uni ko'rsatish `camera_view` ni kassirga
 *    berishni talab qilardi yoki, yomoni, `require_any_permission()`
 *    ning YOPIQ TO'PLAMINI kengaytirishni
 *    (`test_personal_data_coverage.py:674-706` uni AYNAN BITTA
 *    marshrutga qulflagan). Ya'ni C-9 ning eng qimmat to'sig'i shu
 *    KO'LAM QARORI bilan umuman TUG'ILMAYDI.
 */
const EVIDENCE_TOKENS = ["/snapshots/", "snapshot_id"];

/* -------------------------------------------------------------------------- */
/* OMMAVIY AMAL TO'SIG'INING IKKINCHI YARMI (§15.4)                           */
/* -------------------------------------------------------------------------- */

/**
 * Ko'p tanlovli yuzaning izlari.
 *
 * ⚠ Bu blok `bulk-action-surface.test.mjs` NI ALMASHTIRMAYDI — u §15.4
 *   bo'yicha `05-UI-SPEC` ning G-18 e'loni orqali kengayadi (06-11 T1)
 *   va uning qamrovi E'LONDAN hosila. Bu yerdagi blok IKKINCHI,
 *   MUSTAQIL qatlam: e'lon kengaytirilishi UNUTILSA ham kassir yuzasi
 *   qo'riqsiz qolmaydi.
 *
 * ⛔ Nega bu yerda ayniqsa qimmat: «Hammasini to'lash» yoki ko'p
 *    tanlovli rasta ro'yxati kassirga BIR BOSISHDA 50 rastani to'langan
 *    deb belgilash imkonini berardi — 5-fazadagi «hammasini tasdiqlash»
 *    dan qimmatroq xato, chunki natijasi PUL YOZUVI.
 */
const BULK_ACTION_TOKENS = [
  'type="checkbox"',
  "Array.isArray(selected",
  "selectAll",
  "hammasini",
];

/* -------------------------------------------------------------------------- */
/* IZOHLARNI OLIB TASHLASH                                                    */
/* -------------------------------------------------------------------------- */

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 *
 * ⛔ `bulk-action-surface.test.mjs:163-225` DAN KO'CHIRILGAN NUSXA —
 *    uchinchi implementatsiya yozilmaydi (06-UI-SPEC W0-F4).
 *
 * Satrlar ATAYIN saqlanadi: tarjima kaliti, kesh kaliti yoki
 * `data-testid` ichidagi taqiqlangan nom ham brauzerga yetib boradi.
 *
 * ⚠ MA'LUM CHEGARA: regeks literali (`/["']/`) satr boshlovchisi deb
 *   o'qilishi mumkin. Bu XAVFSIZ TOMONGA og'adi — matn saqlanib qoladi,
 *   ya'ni darvoza QATTIQROQ bo'ladi, bo'shroq emas. Teskari yo'nalish
 *   (butun faylni yutib yuborish) pastdagi nazorat bilan ushlanadi.
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

/** Faylning izohsiz kodi + «yutib yuborilmadi» nazorati. */
function readCode(file) {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);

  /*
   * RUNAWAY NAZORATI: holat mashinasi adashib butun faylni izoh deb
   * yutsa, keyingi hamma assert JIMGINA yashil bo'lardi — ya'ni darvoza
   * o'chib qolgan holda «o'tdi» deb hisobot berardi.
   */
  if (raw.includes("export")) {
    assert.ok(
      code.includes("export"),
      `${path.relative(FRONTEND_ROOT, file)}: izoh filtri faylni YUTIB YUBORDI ` +
        "(manbada `export` bor, filtrdan keyin yo'q) — darvoza o'chib qolgan bo'lardi",
    );
  }

  return code;
}

/** Berilgan reyestrdan kodda uchragan tokenlar (registrga sezgir EMAS). */
function hitsOf(code, tokens) {
  const lowered = code.toLowerCase();
  return tokens.filter((token) => lowered.includes(token.toLowerCase()));
}

/** Kodda uchragan taqiqlangan nomlar (G-22). */
function findForbidden(code) {
  return hitsOf(code, FORBIDDEN_NAMES);
}

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv, hosila qamrov). */
function listProductFiles(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full));
    } else if (
      CODE_EXTENSIONS.includes(path.extname(entry)) &&
      !TEST_FILE.test(entry)
    ) {
      found.push(full);
    }
  }
  return found;
}

/**
 * Kassir katalogining mahsulot fayllari — katalog yo'q bo'lsa `null`.
 *
 * ⛔ `null` — «hali tug'ilmagan», BO'SH MASSIV EMAS: bo'sh massivda skan
 *    hech nimani o'qimay yashil qolardi va bu farq chaqiruvchida OCHIQ
 *    qayd etiladi (pastdagi `skipUnlessCollectExists`).
 */
function collectFilesOrNull() {
  return existsSync(COLLECT_COMPONENTS)
    ? listProductFiles(COLLECT_COMPONENTS)
    : null;
}

/**
 * Katalog hali yo'qligini OCHIQ QAYD etadi — `skip` EMAS.
 *
 * ⛔ Naqsh `blind-payload.test.mjs:339-351` dan. `skip` bo'lsa shart
 *    jimgina o'tib ketardi va uni yoqishni hech kim eslamasdi. Bu shakl
 *    esa O'ZINI QUROLLANTIRADI: katalog tug'ilgan kuni (06-11) shart
 *    HECH QANDAY TAHRIRSIZ ishlay boshlaydi.
 */
function collectMissingIsRecorded() {
  assert.equal(
    existsSync(COLLECT_COMPONENTS),
    false,
    "kutilmagan holat: katalog bor, lekin shart bajarilmadi",
  );
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/*                                                                            */
/* ⚠ Bugun `components/collect/` HALI YO'Q (u 06-11 da tug'iladi).            */
/*   Shuning uchun darvozaning ISHLAYOTGANI uning MEXANIZMI ustida            */
/*   o'lchanadi — aks holda bu fayl «yashil» bo'lib, hech nimani              */
/*   tekshirmayotganini yashirardi.                                           */
/* -------------------------------------------------------------------------- */

test("reyestrlar uzunligi quyi chegaradan kam EMAS", () => {
  assert.ok(
    FORBIDDEN_NAMES.length >= MIN_FORBIDDEN_NAMES,
    `taqiqlangan nomlar reyestrida atigi ${FORBIDDEN_NAMES.length} ta nom bor ` +
      `(kutilgan: kamida ${MIN_FORBIDDEN_NAMES}) — 06-UI-SPEC §15.3 (G-22) ` +
      "ro'yxati qisqartirilgan",
  );

  assert.ok(
    BLIND_DECLARATION_TOKENS.length >= MIN_BLIND_DECLARATION_TOKENS,
    `ko'r deklaratsiya reyestrida atigi ${BLIND_DECLARATION_TOKENS.length} ta ` +
      `token bor (kutilgan: kamida ${MIN_BLIND_DECLARATION_TOKENS})`,
  );

  // Takror nom reyestrni «uzun» ko'rsatib, chegarani aldab o'tardi.
  assert.equal(
    new Set(FORBIDDEN_NAMES).size,
    FORBIDDEN_NAMES.length,
    "reyestrda takrorlangan nom bor — uzunlik chegarasi aldangan bo'lardi",
  );
  assert.equal(
    new Set(BLIND_DECLARATION_TOKENS).size,
    BLIND_DECLARATION_TOKENS.length,
    "ko'r deklaratsiya reyestrida takrorlangan token bor",
  );
});

test("⚠ G-22: tarif kirish ma'lumoti reyestrda NOMMA-NOM bor (D-20)", () => {
  /*
   * Yuqoridagi uzunlik sharti buni allaqachon qamraydi. Takrorlanishi
   * ATAYIN: aynan shu ikki nom D-20 ni TAQIQDAN IMKONSIZLIKKA
   * aylantiradi. Ular payloadda bo'lmasa, klientda tarif KIRISH
   * MA'LUMOTINING O'ZI yo'q, ya'ni summani hisoblab bo'lmaydi — «klient
   * hisoblamasin» degan kod-ko'rik da'vosi kerak emas.
   */
  assert.ok(FORBIDDEN_NAMES.includes("tariff_id"));
  assert.ok(FORBIDDEN_NAMES.includes("tariffId"));
});

test("izoh filtri IJOBIY va SALBIY nazoratdan o'tadi", () => {
  /*
   * ⛔ DARVOZANING ENG NOZIK QISMI SHU YERDA O'LCHANADI.
   *
   * Filtr juda ko'p olib tashlasa darvoza JIMGINA bo'shaydi; juda kam
   * olib tashlasa o'z izohidan qizaradi va keyingi ijrochi uni
   * o'chirishga majbur bo'lardi. Ikkala yo'nalish ham qulflangan.
   */
  const cases = [
    // [manba, taqiqlangan nom topilishi kerakmi]
    ["const chargeId = 1;", true],
    ["// charge_id", false],
    ["  // bu yerga charge_id qo'yish taqiqlanadi", false],
    ["/* tariff_id */", false],
    ["/**\n * vendor_name\n */\nconst ok = 1;", false],
    ["const x = 1; // balance", false],
    ["const ok = 1;\n/* phone */\nconst fine = 2;", false],
    // Satr literali SAQLANADI — u ham brauzerga yetib boradi.
    ['const k = "charge_id";', true],
    ["const k = `occupied_slots`;", true],
    // Satr ichidagi `//` izoh EMAS.
    ['const u = "https://example.test"; const c = balance;', true],
    ['const u = "https://example.test"; const c = 1;', false],
  ];

  for (const [source, shouldFind] of cases) {
    const hits = findForbidden(stripComments(source));
    assert.equal(
      hits.length > 0,
      shouldFind,
      `izoh filtri xato ishladi.\n  manba: ${JSON.stringify(source)}\n` +
        `  kutilgan topilish: ${shouldFind}, topilgan: ${JSON.stringify(hits)}`,
    );
  }
});

test("izoh filtri faylni YUTIB YUBORMAYDI (runaway nazorati)", () => {
  const code = stripComments('const s = "/* bu izoh EMAS */";\nexport const keep = s;');

  assert.ok(code.includes("export"), "izoh filtri `export` ni yutib yubordi");
  assert.ok(
    code.includes("/* bu izoh EMAS */"),
    "satr literali ichidagi matn izoh deb o'chirildi",
  );
});

test("detektor sun'iy IJOBIY manbani USHLAYDI (uchala reyestr)", () => {
  /*
   * Usiz quyidagi hamma «topilmadi» xulosasi BO'SH DETEKTOR ustida ham
   * rost bo'lardi — `hitsOf` har doim bo'sh massiv qaytarsa, darvoza
   * abadiy yashil.
   */
  assert.deepEqual(hitsOf("const s = { system_soum: 1 };", BLIND_DECLARATION_TOKENS), [
    "system_soum",
  ]);
  assert.deepEqual(hitsOf('<img src="/snapshots/x/image" />', EVIDENCE_TOKENS), [
    "/snapshots/",
  ]);
  assert.deepEqual(hitsOf('<input type="checkbox" />', BULK_ACTION_TOKENS), [
    'type="checkbox"',
  ]);
  assert.deepEqual(hitsOf("const ok = 1;", BULK_ACTION_TOKENS), []);
});

/* -------------------------------------------------------------------------- */
/* G-22 — TAQIQLANGAN NOMLAR                                                  */
/* -------------------------------------------------------------------------- */

test("G-22 (06-UI-SPEC): `lib/billing-pending-queries.ts` da taqiqlangan nom YO'Q", () => {
  /*
   * ⛔ BU YERDA «OCHIQ QAYD» YO'LI YO'Q va bu ataylab: modul SHU
   *    REJADA (06-03) tug'ildi va u darvozaning skanerlanadigan
   *    yuzasining YARMI. Fayl qayta nomlansa yoki ko'chirilsa, skan
   *    jimgina toraymasligi kerak — u QIZARISHI kerak.
   */
  assert.ok(
    existsSync(PENDING_QUERIES),
    "`lib/billing-pending-queries.ts` TOPILMADI — G-22 ning skanerlanadigan " +
      "yuzasi yarmiga qisqargan (W0-F3 moduli ko'chirilgan yoki qayta nomlangan)",
  );

  const hits = findForbidden(readCode(PENDING_QUERIES));

  assert.deepEqual(
    hits,
    [],
    `G-22 BUZILDI: \`lib/billing-pending-queries.ts\` da taqiqlangan nom(lar): ${hits.join(", ")}.\n` +
      "  Payloadga tushgan maydon BRAUZERDA O'QILADI (DevTools, React DevTools,\n" +
      "  JSON.stringify) — CSS bilan yashirish yoki shartli render YETARLI EMAS.\n" +
      "  Tarif identifikatori bo'lsa klient summani HISOBLAB CHIQARARDI (D-20);\n" +
      "  hisob identifikatori bo'lsa proyeksiya KVITANSIYAGA aylanardi (D-17);\n" +
      "  ism yoki telefon bo'lsa C-10 ning shaxsiy-ma'lumot chegarasi buzilardi.",
  );
});

test("G-22 (06-UI-SPEC): `components/collect/**` da taqiqlangan nom YO'Q", () => {
  const files = collectFilesOrNull();
  if (files === null) {
    collectMissingIsRecorded();
    return;
  }

  const problems = [];
  for (const file of files) {
    for (const name of findForbidden(readCode(file))) {
      problems.push(`${path.relative(SRC, file)} -> \`${name}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-22 BUZILDI — kassir yuzasida taqiqlangan nom tug'ildi:\n  " +
      problems.join("\n  ") +
      "\n  Nomni o'zgartirib aylanib o'tish ham TAQIQLANADI (§5.5): `vendor_label`,\n" +
      "  `payer`, `who` — hech biri. To'g'ri tuzatish — maydonni MARSHRUTDAN\n" +
      "  olib tashlash, klientda yashirish emas.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-7 (frontend yarmi) — KO'R DEKLARATSIYA YUZASI                            */
/* -------------------------------------------------------------------------- */

test("G-7 (06-RESEARCH): `components/collect/**` da tizim summasi va farq YO'Q", () => {
  const files = collectFilesOrNull();
  if (files === null) {
    collectMissingIsRecorded();
    return;
  }

  const problems = [];
  for (const file of files) {
    for (const token of hitsOf(readCode(file), BLIND_DECLARATION_TOKENS)) {
      problems.push(`${path.relative(SRC, file)} -> \`${token}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-7 BUZILDI — ko'r naqd deklaratsiyasi yuzasida tizim summasi izi bor:\n  " +
      problems.join("\n  ") +
      "\n  `tizim = deklaratsiya − farq` — bitta ayirish, ya'ni FARQNI ko'rsatish\n" +
      "  tizim summasini ko'rsatish bilan MATEMATIK JIHATDAN bir xil (D-25, §10.4).\n" +
      "  Farq direktorga `GET /shifts?day=` orqali ko'rsatiladi va SC#5(d) mezoni\n" +
      "  AYNAN o'sha marshrutda o'lchanadi.",
  );
});

test("⚠ G-7(c) QAMROV CHEGARASI: katalog mavjud bo'lsa kamida 5 mahsulot fayli", () => {
  const files = collectFilesOrNull();
  if (files === null) {
    /*
     * O'Z-O'ZINI QUROLLANTIRADIGAN SHART. Bugun katalog yo'q va holat
     * OCHIQ qayd etiladi. Katalog paydo bo'lgan kuni (06-11) quyidagi
     * chegara AVTOMATIK ishlaydi — bu faylga tegilmaydi.
     */
    collectMissingIsRecorded();
    return;
  }

  assert.ok(
    files.length >= MIN_COLLECT_FILES,
    `\`components/collect/\` da atigi ${files.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_COLLECT_FILES}) — yuqoridagi darvozalar bo'sh ` +
      "to'plam ustida ishlab, yashil bo'lib turgan holda mavjudligini yo'qotardi",
  );
});

/* -------------------------------------------------------------------------- */
/* G-28(d) — DALIL KADRI KASSIR YUZASIDA YO'Q                                 */
/* -------------------------------------------------------------------------- */

test("G-28(d) (06-UI-SPEC): `components/collect/**` da dalil kadri YO'Q", () => {
  const files = collectFilesOrNull();
  if (files === null) {
    collectMissingIsRecorded();
    return;
  }

  const problems = [];
  for (const file of files) {
    for (const token of hitsOf(readCode(file), EVIDENCE_TOKENS)) {
      problems.push(`${path.relative(SRC, file)} -> \`${token}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-28(d) BUZILDI — kassir yuzasida dalil kadri tug'ildi:\n  " +
      problems.join("\n  ") +
      "\n  Kassir pul yig'adi, HUKM CHIQARMAYDI. Kadrni ko'rsatish `camera_view` ni\n" +
      "  kassirga berishni yoki `require_any_permission()` ning YOPIQ TO'PLAMINI\n" +
      "  kengaytirishni talab qilardi — C-9 ning eng qimmat to'sig'i shu ko'lam\n" +
      "  qarori bilan UMUMAN TUG'ILMAYDI [O'LCHANDI: M-8].",
  );
});

/* -------------------------------------------------------------------------- */
/* OMMAVIY AMAL — IKKINCHI, MUSTAQIL QATLAM (§15.4)                           */
/* -------------------------------------------------------------------------- */

test("§15.4: `components/collect/**` da ommaviy amal yuzasi YO'Q", () => {
  const files = collectFilesOrNull();
  if (files === null) {
    collectMissingIsRecorded();
    return;
  }

  const problems = [];
  for (const file of files) {
    for (const token of hitsOf(readCode(file), BULK_ACTION_TOKENS)) {
      problems.push(`${path.relative(SRC, file)} -> \`${token}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ Kassir yuzasida ko'p tanlovli amal tug'ildi:\n  " +
      problems.join("\n  ") +
      "\n  «Hammasini to'lash» bir bosishda 50 rastani to'langan deb belgilardi —\n" +
      "  natijasi PUL YOZUVI, ya'ni 5-fazadagi «hammasini tasdiqlash» dan qimmatroq.\n" +
      "  Kassir HAR rastaga ALOHIDA to'lov yozadi (D-18 ning pul shakli).",
  );
});

/* ========================================================================== */
/* G-motion-6 (09-UI-SPEC §16.4) — KO'R DEKLARATSIYA MOTION QATLAMIDA HAM     */
/*                                                                            */
/* ⛔ (a) MAVJUD QISM O'ZGARMAYDI: `FORBIDDEN_NAMES`/`BLIND_DECLARATION_*`    */
/*    reyestrlari va ularning quyi chegaralari yuqorida QANDAY bo'lsa,        */
/*    SHUNDAY qoladi — bu bo'lim ularga TEGMAYDI, faqat qulflaydi.            */
/* ⛔ (c) `/dashboard` ning ikki yangi kartasi (09-05) uchun huquq sharti      */
/*    SAHIFADA — komponent «o'zini o'zi himoya qiladi» degan yolg'on          */
/*    xotirjamlik tug'ilmasligi uchun komponent manbasida `hasPermission(`    */
/*    0 marta bo'lishi mexanik o'lchanadi.                                    */
/* ⛔ (d) Bayram copy'si kassir yuzasiga KIRMAYDI: mavjud `collect.written`   */
/*    toasti FAKTNI aytadi va u yetarli — bayram matni ma'noni suyultirardi.  */
/* ⛔ (e) Konfetti bu fazada QURILMAYDI (09-UI-SPEC §9): tetigining haqiqat   */
/*    manbai (`market_day_cleared`) mavjud emas, klientdagi har qanday        */
/*    hosila ko'rlikni buzadi. «Ijro yo'q» — o'lchanadigan da'vo.             */
/* ========================================================================== */

/* --- (a) Chegara qulflari ------------------------------------------------- */

/**
 * ⛔ 2026-08-17 dagi qiymatlar — KAMAYTIRISH TAQIQ (09-UI-SPEC §16.5).
 *
 * Yuqoridagi «uzunlik quyi chegaradan kam EMAS» testi reyestrni MIN_* ga
 * solishtiradi, LEKIN MIN_* ning O'ZI pasaytirilsa jim qolardi. Bu ikki
 * konstanta o'sha teshikni yopadi: chegara konstantasi bugungi qiymatdan
 * PASAYSA — darvoza qizaradi.
 */
const LOCKED_MIN_FORBIDDEN_NAMES = 14;
const LOCKED_MIN_BLIND_DECLARATION_TOKENS = 7;

test("G-motion-6(a): mavjud chegara konstantalari PASAYTIRILMAGAN", () => {
  assert.ok(
    MIN_FORBIDDEN_NAMES >= LOCKED_MIN_FORBIDDEN_NAMES,
    `MIN_FORBIDDEN_NAMES = ${MIN_FORBIDDEN_NAMES} < ${LOCKED_MIN_FORBIDDEN_NAMES} — ` +
      "mavjud chegarani kamaytirish TAQIQ (09-UI-SPEC §16.5)",
  );
  assert.ok(
    MIN_BLIND_DECLARATION_TOKENS >= LOCKED_MIN_BLIND_DECLARATION_TOKENS,
    `MIN_BLIND_DECLARATION_TOKENS = ${MIN_BLIND_DECLARATION_TOKENS} < ` +
      `${LOCKED_MIN_BLIND_DECLARATION_TOKENS} — kamaytirish TAQIQ`,
  );
});

/* --- (c) Dashboard komponentlarida huquq sharti YO'Q ---------------------- */

/** `/dashboard` kartalari — huquq sharti SAHIFADA turadigan yuza. */
const DASHBOARD_COMPONENTS = path.join(SRC, "components", "dashboard");

/** Chaqiruv shakli — import nomi emas: `hasPermission(` AYNAN chaqiruv. */
const PERMISSION_CALL_TOKENS = ["hasPermission("];

/**
 * ⛔ Bo'sh skanda «topilmadi» jimgina rost bo'lardi: 09-05 dan keyin
 *    katalogda kamida 3 mahsulot fayli bor (market-status-card,
 *    revenue-card, occupancy-donut).
 */
const MIN_DASHBOARD_FILES = 3;

test("G-motion-6(c): `components/dashboard/**` da `hasPermission(` — 0 marta", () => {
  assert.ok(
    existsSync(DASHBOARD_COMPONENTS),
    "`components/dashboard/` TOPILMADI — (c) skan yuzasi yo'qolgan " +
      "(katalog ko'chirilgan yoki qayta nomlangan)",
  );

  const files = listProductFiles(DASHBOARD_COMPONENTS);
  assert.ok(
    files.length >= MIN_DASHBOARD_FILES,
    `\`components/dashboard/\` da atigi ${files.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_DASHBOARD_FILES}) — skan jimgina toraygan`,
  );

  const problems = [];
  for (const file of files) {
    for (const token of hitsOf(readCode(file), PERMISSION_CALL_TOKENS)) {
      problems.push(`${path.relative(SRC, file)} -> \`${token}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-6(c) BUZILDI — huquq sharti komponent ICHIGA kirdi:\n  " +
      problems.join("\n  ") +
      "\n  Shart BITTA joyda — `dashboard/page.tsx` da — qoladi: komponent ichidagi\n" +
      "  shart «o'zini o'zi himoya qiladi» degan yolg'on xotirjamlik tug'dirardi\n" +
      "  va sahifadagi darvoza olib tashlanganda so'rov BARIBIR ketardi.",
  );
});

/* --- (d) Bayram copy'si — 3 locale'da 0 ----------------------------------- */

/**
 * Bayram matnining izlari — lotin, kirill va rus shakllari JUFT.
 *
 * ⚠ Apostrofning IKKI varianti ataylab (U+2019 va U+0027): kodbaza
 *   `’` ishlatadi, lekin qo'lda kiritilgan matn oddiy `'` bilan kelishi
 *   mumkin — bittasini qoldirish taqiqni bitta belgi bilan chetlab
 *   o'tiladigan qilardi.
 */
const CELEBRATION_TOKENS = [
  "Ajoyib",
  "Zo'r",
  "Zo’r",
  "Tabrik",
  "Ажойиб",
  "Зўр",
  "Табрик",
  "Отлично",
  "Поздравля",
];

/** 09-UI-SPEC §16.4 (d): reyestr quyi chegarasi. */
const MIN_CELEBRATION_TOKENS = 5;

/** Uchala locale — qamrov HOSILA emas, YOPIQ reyestr (i18n:check bilan teng). */
const LOCALE_FILES = ["uz-Latn.json", "uz-Cyrl.json", "ru.json"];

/** JSON qiymat daraxtidagi barcha satrlar (kalit yo'li bilan). */
function collectStringValues(node, prefix, out) {
  if (typeof node === "string") {
    out.push([prefix, node]);
    return out;
  }
  if (node !== null && typeof node === "object") {
    for (const [key, value] of Object.entries(node)) {
      collectStringValues(value, `${prefix}.${key}`, out);
    }
  }
  return out;
}

test("G-motion-6(d): `collect.*` qiymatlarida bayram copy'si — 0 (3 locale)", () => {
  assert.ok(
    CELEBRATION_TOKENS.length >= MIN_CELEBRATION_TOKENS,
    `bayram reyestri atigi ${CELEBRATION_TOKENS.length} token ` +
      `(kutilgan: kamida ${MIN_CELEBRATION_TOKENS})`,
  );
  assert.equal(
    new Set(CELEBRATION_TOKENS).size,
    CELEBRATION_TOKENS.length,
    "bayram reyestrida takrorlangan token bor",
  );

  const problems = [];
  for (const localeFile of LOCALE_FILES) {
    const fullPath = path.join(FRONTEND_ROOT, "messages", localeFile);
    assert.ok(
      existsSync(fullPath),
      `\`messages/${localeFile}\` TOPILMADI — (d) skan yuzasi toraygan`,
    );

    const parsed = JSON.parse(readFileSync(fullPath, "utf8"));
    /* `collect` bo'limi yo'q bo'lsa — skan bo'sh to'plamda «yashil» qolardi. */
    assert.ok(
      parsed.collect !== undefined && typeof parsed.collect === "object",
      `\`messages/${localeFile}\` da \`collect\` bo'limi YO'Q — skan bo'shab qoldi`,
    );

    const values = collectStringValues(parsed.collect, "collect", []);
    assert.ok(
      values.length > 0,
      `\`messages/${localeFile}\` ning \`collect\` bo'limi BO'SH — skan bo'shab qoldi`,
    );

    for (const [keyPath, value] of values) {
      for (const token of hitsOf(value, CELEBRATION_TOKENS)) {
        problems.push(`${localeFile}: ${keyPath} -> \`${token}\``);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-6(d) BUZILDI — kassir yuzasiga bayram matni kirdi:\n  " +
      problems.join("\n  ") +
      "\n  Mavjud `collect.written` toasti FAKTNI aytadi va u yetarli (09-UI-SPEC\n" +
      "  §14.1): bayram matni ma'noni suyultirardi va C variantining («har\n" +
      "  to'lovda bayram») niqoblangan shakliga eshik ochardi.",
  );
});

/* --- (e) Konfetti ijrosi YO'Q --------------------------------------------- */

/**
 * Konfetti identifikatorlari (09-UI-SPEC §16.4 G-motion-1(d)/6(e)).
 *
 * Sabab `deferred-items.md` da: tetikning haqiqat manbai
 * (`market_day_cleared`) hali mavjud emas — shartnoma §9 da to'liq turadi,
 * ijro esa YO'Q va bu yo'qlik shu yerda o'lchanadi.
 */
const CONFETTI_TOKENS = ["confetti", "burst", "particle"];

const MIN_CONFETTI_TOKENS = 3;

test("G-motion-6(e): `components/collect/**` da konfetti identifikatori — 0", () => {
  assert.ok(
    CONFETTI_TOKENS.length >= MIN_CONFETTI_TOKENS,
    `konfetti reyestri atigi ${CONFETTI_TOKENS.length} token ` +
      `(kutilgan: kamida ${MIN_CONFETTI_TOKENS})`,
  );
  assert.equal(
    new Set(CONFETTI_TOKENS).size,
    CONFETTI_TOKENS.length,
    "konfetti reyestrida takrorlangan token bor",
  );

  const files = collectFilesOrNull();
  if (files === null) {
    collectMissingIsRecorded();
    return;
  }

  const problems = [];
  for (const file of files) {
    for (const token of hitsOf(readCode(file), CONFETTI_TOKENS)) {
      problems.push(`${path.relative(SRC, file)} -> \`${token}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-motion-6(e) BUZILDI — kassir yuzasida konfetti izi tug'ildi:\n  " +
      problems.join("\n  ") +
      "\n  Konfetti bu fazada QURILMAYDI (09-UI-SPEC §9): yagona halol tetigi —\n" +
      "  server beradigan mantiqiy bayroq — hali mavjud emas; klientdagi har\n" +
      "  qanday hosila ko'r deklaratsiyani buzadi. Soxta tetik («har 50-to'lov»)\n" +
      "  foydalanuvchi rad etgan variantning niqoblangan shakli bo'lardi.",
  );
});

/* --- G-motion-6 sun'iy-ijobiy nazorati ------------------------------------ */

test("detektor sun'iy IJOBIY manbani USHLAYDI (G-motion-6 yangi reyestrlari)", () => {
  /*
   * Usiz (c)/(d)/(e) ning «topilmadi» xulosalari BO'SH detektor ustida
   * ham rost bo'lardi (mavjud fayldagi 451-467 naqshining davomi).
   */
  assert.deepEqual(
    hitsOf('const ok = hasPermission(r, "x");', PERMISSION_CALL_TOKENS),
    ["hasPermission("],
  );
  assert.deepEqual(hitsOf('{"cheer":"Ajoyib!"}', CELEBRATION_TOKENS), [
    "Ajoyib",
  ]);
  /* Kirill va rus shakllari ham ushlanadi (registrga sezgir EMAS). */
  assert.deepEqual(hitsOf("отлично!", CELEBRATION_TOKENS), ["Отлично"]);
  assert.deepEqual(hitsOf("зўр иш", CELEBRATION_TOKENS), ["Зўр"]);
  assert.deepEqual(hitsOf("burstConfetti(particleCount)", CONFETTI_TOKENS), [
    "confetti",
    "burst",
    "particle",
  ]);
  assert.deepEqual(hitsOf("const ok = 1;", CELEBRATION_TOKENS), []);
  assert.deepEqual(hitsOf("const ok = 1;", CONFETTI_TOKENS), []);
});
