#!/usr/bin/env node
/**
 * G-12 va G-14 — KO'R AUDIT PAYLOADINING STATIK MODUL CHEGARASI.
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI: bu 4-fazadagi «ombor yuzasi» qoidasining
 * ekvivalenti, lekin maxfiy narsa boshqa — u TIZIMNING JAVOBI, va uni
 * ko'radigan odam BIZNING O'Z NAZORATCHIMIZ (05-UI-SPEC §14.3).
 *
 * Ko'r audit XOLIS bo'lishi uchun AI verdikti payloadda UMUMAN
 * BO'LMASLIGI kerak — YASHIRILGAN emas (D-17, 2-himoya). Sabab qat'iy:
 * brauzerga yetib borgan maydon O'QILADI. DevTools, React DevTools,
 * `JSON.stringify(props)` — uchalasi ham CSS bilan yashirishni yoki
 * shartli renderni bir bosishda chetlab o'tadi. Nazoratchi tizimning
 * javobini bir marta ko'rsa, uning o'z javobi endi mustaqil emas va
 * hisobotdagi aniqlik raqami YUQORIGA siljiydi — ya'ni o'lchov o'zi
 * o'lchayotgan narsani buzadi.
 * =============================================================================
 *
 * ⚠ BU DARVOZA `components/blind-audit/` ALOHIDA KATALOG BO'LGANI
 *   UCHUNGINA YOZILISHI MUMKIN (05-UI-SPEC §5.3). Ko'r audit kodi
 *   `review-queries.ts` ichida yashaganda shart «`verdict` faqat
 *   `uncertain` funksiyalarida uchraydi» degan KONTEKSTGA BOG'LIQ
 *   holga aylanardi — ya'ni mexanik tekshirib bo'lmaydigan, kod-ko'rikka
 *   qaytadigan shartga.
 *
 * ⚠ G-12 (bu fayl) STATIK, G-13 (`blind-session.test.tsx`, 05-13)
 *   DINAMIK. IKKALASI HAM KERAK: faqat G-12 bo'lsa `data["verd" + "ict"]`
 *   uni chetlab o'tardi; faqat G-13 bo'lsa u faqat TEST YOZILGAN
 *   payloadni tekshirardi.
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN QIDIRILADI. Filtrsiz bu darvoza
 *   o'z-o'ziga qarshi ishlardi: «bu maydonni bu yerga qo'yish
 *   taqiqlanadi» degan izohning O'ZI uni qizartirardi. 2 va 3-fazada
 *   aynan shu sinf 15+ marta yuz bergan.
 *
 * ⚠ SATRLAR (`"..."`, `'...'`, `` `...` ``) OLIB TASHLANMAYDI va bu
 *   ATAYIN: tarjima kaliti, kesh kaliti yoki `data-testid` ichidagi
 *   `verdict` ham brauzerga yetib boradi, ya'ni u ham taqiq ostida.
 *
 * ⚠ REYESTR UZUNLIGI `assert` BILAN SANALADI, `grep` bilan EMAS —
 *   shunda darvozaning o'z fayli tekshiruv maydoniga umuman kirmaydi.
 *   Bu fayl SKANERLANADIGAN to'plamda YO'Q (pastdagi `SCAN_TARGETS`).
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");

/** ⛔ Ko'r audit so'rovlari — ALOHIDA modul (05-UI-SPEC §5.3). */
const BLIND_QUERIES = path.join(SRC, "lib", "blind-audit-queries.ts");

/** ⛔ Ko'r audit komponentlari — ALOHIDA katalog. */
const BLIND_COMPONENTS = path.join(SRC, "components", "blind-audit");

/** ⛔ Ko'r audit marshruti — ALOHIDA yo'l, tab EMAS (§4.5). */
const BLIND_ROUTE = path.join(
  SRC,
  "app",
  "[locale]",
  "(app)",
  "review",
  "blind",
);

/* -------------------------------------------------------------------------- */
/* TAQIQLANGAN NOMLAR REYESTRI (05-UI-SPEC §14.3)                             */
/* -------------------------------------------------------------------------- */

/**
 * Ko'r audit yuzasida UCHRAMAYDIGAN nomlar.
 *
 * ⚠ `purpose` HAM RO'YXATDA VA BU ATAYIN (D-14): `eval`/`train` belgisi
 *   ko'rinsa, «bu baholash uchun ekan» degan e'tibor farqi tug'ilardi va
 *   70/30 bo'linishining butun ma'nosi yo'qolardi. Nisbat TORTISH
 *   paytida belgilanadi, ya'ni klient uni bilishi SHART EMAS.
 *
 * ⚠ `thresholds_version` ham shu yerda: chegara versiyasi ko'rinsa,
 *   nazoratchi «bu band chegaraga yaqin ekan» deb o'qirdi.
 */
const FORBIDDEN_NAMES = [
  "verdict",
  "aiVerdict",
  "ai_verdict",
  "confidence",
  "aiConfidence",
  "ai_confidence",
  "modelVersion",
  "model_version",
  "effectiveVerdict",
  "effective_verdict",
  "resolutionSource",
  "resolution_source",
  "shownAiVerdict",
  "shown_ai_verdict",
  "purpose",
  "thresholdsVersion",
  "thresholds_version",
];

/**
 * Reyestrning QUYI CHEGARASI.
 *
 * ⚠ Usiz reyestr bo'shatilsa darvoza BO'SH TO'PLAM ustida ishlab,
 *   abadiy yashil qolardi — `test_sentry_processes.py` dagi `MIN_*`
 *   qoidasi (§S-10). Chegara QUYI: yangi nom qo'shilganda bu son
 *   o'zgarmaydi.
 */
const MIN_FORBIDDEN_NAMES = 13;

/**
 * `components/blind-audit/` katalogining QAMROV CHEGARASI.
 *
 * Katalog mavjud bo'lsa kamida shuncha fayl bo'lishi SHART, aks holda
 * G-12 bo'sh to'plam ustida yashil bo'lib turgan holda mavjudligini
 * yo'qotardi (05-UI-SPEC §14.3).
 */
const MIN_BLIND_COMPONENT_FILES = 3;

/** Skanerlanadigan kengaytmalar. */
const CODE_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs"];

/* -------------------------------------------------------------------------- */
/* Izohlarni olib tashlash                                                     */
/* -------------------------------------------------------------------------- */

/**
 * Manba matnidan `//` va `/* *\/` izohlarini olib tashlaydi.
 *
 * Satr literallari SAQLANADI (yuqoridagi sababga ko'ra). Holat mashinasi
 * qatorma-qator filtrdan ko'ra aniqroq: `const x = 1; // verdict`
 * kabi SATR ICHIDAGI izohni ham oladi, `"https://..."` kabi satrni esa
 * BUZMAYDI.
 *
 * ⚠ MA'LUM CHEGARA: regex literali (`/["']/`) satr boshlovchisi deb
 *   o'qilishi mumkin. Bu XAVFSIZ TOMONGA og'adi — matn olib tashlanmay,
 *   SAQLANIB qoladi, ya'ni darvoza qattiqroq bo'ladi, bo'shroq emas.
 *   Teskari yo'nalish (butun faylni «izoh» deb yutib yuborish) esa
 *   pastdagi `export` nazorati bilan ushlanadi.
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

    // Satr literali ichida: `state` ochuvchi belgining o'zi.
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
   * yutsa, keyingi hamma assert JIMGINA yashil bo'lardi — ya'ni
   * darvoza o'chib qolgan holda «o'tdi» deb hisobot berardi.
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

/** Kodda uchragan taqiqlangan nomlar. */
function findForbidden(code) {
  return FORBIDDEN_NAMES.filter((name) => code.includes(name));
}

/** Katalogdagi barcha kod fayllari (rekursiv). */
function listCodeFiles(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listCodeFiles(full));
    } else if (CODE_EXTENSIONS.includes(path.extname(entry))) {
      found.push(full);
    }
  }
  return found;
}

/** Katalogdagi barcha nomlar (rekursiv, papkalar ham). */
function listAllNames(dir) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    found.push(entry);
    if (statSync(full).isDirectory()) {
      found.push(...listAllNames(full));
    }
  }
  return found;
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/*                                                                            */
/* ⚠ Bugun skanerlanadigan to'plam BO'SH (fayllar 05-13 da tug'iladi).        */
/*   Shuning uchun darvozaning ISHLAYOTGANI uning MEXANIZMI ustida            */
/*   o'lchanadi — aks holda bu fayl «yashil» bo'lib, hech nimani              */
/*   tekshirmayotganini yashirardi (§S-10).                                   */
/* -------------------------------------------------------------------------- */

test("reyestr uzunligi quyi chegaradan kam EMAS", () => {
  assert.ok(
    FORBIDDEN_NAMES.length >= MIN_FORBIDDEN_NAMES,
    `taqiqlangan nomlar reyestrida atigi ${FORBIDDEN_NAMES.length} ta nom bor ` +
      `(kutilgan: kamida ${MIN_FORBIDDEN_NAMES}) — 05-UI-SPEC §14.3 ro'yxati qisqartirilgan`,
  );

  // Takror nom reyestrni «uzun» ko'rsatib, chegarani aldab o'tardi.
  assert.equal(
    new Set(FORBIDDEN_NAMES).size,
    FORBIDDEN_NAMES.length,
    "reyestrda takrorlangan nom bor — uzunlik chegarasi aldangan bo'lardi",
  );
});

test("⚠ G-14(c) `shownAiVerdict` reyestrda NOMMA-NOM bor (D-17.3)", () => {
  /*
   * Yuqoridagi reyestr buni allaqachon qamraydi. Takrorlanishi ATAYIN:
   * bu maydon D-17 ning 3-himoyasining YAGONA klient tomondagi izi.
   * Klient uni HECH QACHON yubormaydi — u SERVERDA hisoblanadi. Klient
   * yuborsa, u YOLG'ON GAPIRA OLARDI va DB `CHECK` i aldangan bo'lardi
   * («ko'r, lekin ko'rsatilgan» holati ifodalanmaydigan qilingan).
   */
  assert.ok(FORBIDDEN_NAMES.includes("shownAiVerdict"));
  assert.ok(FORBIDDEN_NAMES.includes("shown_ai_verdict"));
});

test("izoh filtri IJOBIY va SALBIY nazoratdan o'tadi", () => {
  /*
   * ⛔ DARVOZANING ENG NOZIK QISMI SHU YERDA O'LCHANADI.
   *
   * Filtr juda ko'p olib tashlasa darvoza JIMGINA bo'shaydi; juda kam
   * olib tashlasa o'z izohidan qizaradi va keyingi ijrochi uni
   * o'chirishga majbur bo'lardi. Ikkala yo'nalish ham shu yerda
   * qulflangan.
   */
  const cases = [
    // [manba, taqiqlangan nom topilishi kerakmi]
    ["const verdict = 1;", true],
    ["// verdict", false],
    ["  // bu yerga verdict qo'yish taqiqlanadi", false],
    ["/* verdict */", false],
    ["/**\n * verdict\n */\nconst ok = 1;", false],
    ["const x = 1; // verdict", false],
    ["const ok = 1;\n/* confidence */\nconst fine = 2;", false],
    // Satr literali SAQLANADI — u ham brauzerga yetib boradi.
    ['const k = "verdict";', true],
    ["const k = `ai_verdict`;", true],
    // Satr ichidagi `//` izoh EMAS.
    ['const u = "https://example.test"; const c = confidence;', true],
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

/* -------------------------------------------------------------------------- */
/* G-12 — MODUL CHEGARASI                                                     */
/* -------------------------------------------------------------------------- */

test("G-12: `lib/blind-audit-queries.ts` da taqiqlangan nom YO'Q", () => {
  if (!existsSync(BLIND_QUERIES)) {
    /*
     * ⚠ `skip` EMAS, OCHIQ QAYD. Fayl 05-13 da tug'iladi va o'sha kuni
     *   bu shart HECH QANDAY TAHRIRSIZ ishlay boshlaydi. `skip` bo'lsa
     *   u jimgina o'tib ketardi va hech kim uni yoqishni eslamasdi.
     */
    assert.equal(
      existsSync(BLIND_QUERIES),
      false,
      "kutilmagan holat: fayl bor, lekin shart bajarilmadi",
    );
    return;
  }

  const hits = findForbidden(readCode(BLIND_QUERIES));

  assert.deepEqual(
    hits,
    [],
    `G-12 BUZILDI: \`lib/blind-audit-queries.ts\` da taqiqlangan nom(lar): ${hits.join(", ")}.\n` +
      "  Payloadga tushgan maydon BRAUZERDA O'QILADI (DevTools, React DevTools,\n" +
      "  JSON.stringify) — CSS bilan yashirish yoki shartli render YETARLI EMAS.\n" +
      "  AI maydonlari ko'r audit javobida UMUMAN bo'lmasligi SHART (D-17.2).",
  );
});

test("G-12: `components/blind-audit/**` da taqiqlangan nom YO'Q", () => {
  if (!existsSync(BLIND_COMPONENTS)) {
    assert.equal(
      existsSync(BLIND_COMPONENTS),
      false,
      "kutilmagan holat: katalog bor, lekin shart bajarilmadi",
    );
    return;
  }

  for (const file of listCodeFiles(BLIND_COMPONENTS)) {
    const hits = findForbidden(readCode(file));
    assert.deepEqual(
      hits,
      [],
      `G-12 BUZILDI: \`${path.relative(SRC, file)}\` da taqiqlangan nom(lar): ${hits.join(", ")}`,
    );
  }
});

test("⚠ QAMROV CHEGARASI: katalog mavjud bo'lsa kamida 3 fayl", () => {
  const exists = existsSync(BLIND_COMPONENTS);

  if (!exists) {
    /*
     * O'Z-O'ZINI QUROLLANTIRADIGAN SHART. Bugun katalog yo'q va holat
     * OCHIQ qayd etiladi. Katalog paydo bo'lgan kuni (05-13) quyidagi
     * chegara AVTOMATIK ishlaydi — bu faylga tegilmaydi.
     */
    assert.equal(exists, false, "kutilmagan holat");
    return;
  }

  const files = listCodeFiles(BLIND_COMPONENTS);

  assert.ok(
    files.length >= MIN_BLIND_COMPONENT_FILES,
    `\`components/blind-audit/\` da atigi ${files.length} ta kod fayli bor ` +
      `(kutilgan: kamida ${MIN_BLIND_COMPONENT_FILES}) — G-12 bo'sh to'plam ustida ishlab, ` +
      "yashil bo'lib turgan holda mavjudligini yo'qotardi",
  );
});

/* -------------------------------------------------------------------------- */
/* G-14 — KO'R JAVOBNING O'ZGARMASLIGI                                        */
/* -------------------------------------------------------------------------- */

test("G-14(a): `review/blind/` da DINAMIK SEGMENT yo'q", () => {
  if (!existsSync(BLIND_ROUTE)) {
    assert.equal(existsSync(BLIND_ROUTE), false, "kutilmagan holat");
    return;
  }

  /*
   * ⚠ SHART QO'POL VA U ATAYIN QO'POL: `[` bilan boshlanadigan nom
   *   yo'qligi «URL'da identifikator bo'lmasin» degan niyatni FAYL
   *   TIZIMI darajasida ifodalaydi. Nozikroq tekshiruv (URL
   *   parametrlarini tahlil qilish) yozilishi mumkin edi, lekin u o'zi
   *   buzilishi mumkin bo'lgan KODGA aylanardi.
   *
   * Nega muhim: identifikator URL'da bo'lsa, nazoratchi javob
   * berganidan keyin o'sha manzilga QAYTIB, javobini o'zgartira olardi
   * — D-17 ning 4-himoyasi (o'zgarmas javoblar) shu bilan yo'qolardi.
   */
  const dynamic = listAllNames(BLIND_ROUTE).filter((name) =>
    name.startsWith("["),
  );

  assert.deepEqual(
    dynamic,
    [],
    `G-14(a) BUZILDI: \`review/blind/\` ostida dinamik segment(lar): ${dynamic.join(", ")}.\n` +
      "  URL'da band identifikatori bo'lsa, berilgan javobga QAYTIB uni\n" +
      "  o'zgartirish yo'li ochilardi (D-17, 4-himoya).",
  );
});

test("G-14(b): kesh `removeQueries` bilan tozalanadi, `invalidateQueries` bilan EMAS", () => {
  if (!existsSync(BLIND_QUERIES)) {
    assert.equal(existsSync(BLIND_QUERIES), false, "kutilmagan holat");
    return;
  }

  const code = readCode(BLIND_QUERIES);

  /*
   * ⚠ FARQ MA'NOLI, uslubiy emas: `invalidate` yozuvni keshda QOLDIRIB
   *   uni «eskirgan» deb belgilaydi — ya'ni ko'rilgan band ma'lumoti
   *   brauzer xotirasida turaveradi va React Query DevTools'da
   *   o'qiladi. `remove` esa uni GRAFDAN CHIQARADI.
   */
  assert.ok(
    !code.includes("invalidateQueries"),
    "G-14(b) BUZILDI: `blind-audit-queries.ts` da `invalidateQueries` bor — " +
      "u yozuvni keshda QOLDIRADI va ko'rilgan band brauzer xotirasida o'qiladigan " +
      "bo'lib qolardi. `removeQueries` ishlatilishi SHART.",
  );

  assert.ok(
    code.includes("removeQueries"),
    "G-14(b) BUZILDI: `blind-audit-queries.ts` da `removeQueries` YO'Q — " +
      "javob yozilgach ko'r so'rov keshdan CHIQARILISHI shart (05-UI-SPEC §14.3, 4-qatlam)",
  );
});
