#!/usr/bin/env node
/**
 * 5-FAZANING MATN DARVOZALARI — G-11, G-15, G-16, G-18(a).
 *
 * To'rtala qoida ham FAQAT matn orqali yashaydi va aynan shuning uchun
 * ular kod-ko'rikda eng oson o'tkazib yuboriladi: `messages/*.json` ga
 * bitta so'z qo'shish na typecheck'ni, na lint'ni, na birorta komponent
 * testini qizartiradi.
 *
 *   G-11 (§12.10)  AKRONIM TAQIG'I. [O'LCHANDI: M-5] `CV` -> `CВ` —
 *                  bitta token IKKI ALIFBODA (lotin `C` U+0043 + kirill
 *                  `В` U+0412). Mavjud "lotin qoldi" detektori uni
 *                  USHLAMAYDI, chunki lotin `C` haqiqatan ham hali
 *                  o'sha yerda turibdi. Ya'ni bu defekt sinfi boshqa
 *                  HECH QANDAY darvozadan o'tmaydi.
 *
 *   G-15 (D-22)    ⛔ `no_coverage` ≠ «bo'sh». Farq DB'da bor, lekin u
 *                  MATN darajasida yo'qolsa hisobot jimgina noto'g'ri
 *                  o'qilardi va buni hech qanday sxema ushlamasdi.
 *
 *   G-16 (§12.10)  JARGON TAQIG'I. «Poligon» — muhandis so'zi;
 *                  foydalanuvchi uchun bu ZONA. Va D-12: tizim javobi
 *                  hech qachon O'ZGARTIRILMAYDI, ya'ni «tuzatish» so'zi
 *                  ustiga yozishni anglatib, D-12 ni jimgina yolg'onga
 *                  aylantirardi.
 *
 *   G-18 (D-18)    ⛔ OMMAVIY TASDIQ va QAYTA TORTISH taqig'i. Sabab
 *                  o'ziga xos: bu darvoza kodni emas, IMKONIYATNING
 *                  TUG'ILISHINI to'xtatadi. So'z copy'ga kirsa, keyingi
 *                  ijrochi uni AMALGA OSHIRISHGA urinardi — 2 va
 *                  3-fazada aynan shunday bo'lgan.
 *
 * =============================================================================
 * ⛔ BU FAYL O'Z QOIDASINI O'ZI BUZADI — VA BU ATAYIN.
 *
 *   Yuqoridagi izohlarda «poligon» ham, «hammasini tasdiqlash» ham,
 *   `CV` ham YOZILGAN: darvoza o'zi nimani taqiqlayotganini AYTISHI
 *   kerak, aks holda keyingi ishlovchi qoidani UI-SPEC'dan qidirib
 *   yurardi.
 *
 *   Shuning uchun SKANER MAYDONI QAT'IY: faqat `messages/*.json` ning
 *   QIYMATLARI. Bu faylning O'Z manbasi hech qachon o'qilmaydi va
 *   `grep` asosidagi tekshiruv BU YERDA UMUMAN ISHLATILMAYDI. 2-fazada
 *   uch marta, 3-fazada esa teskari yo'nalishda takrorlangan sinf:
 *   `grep` kodni izohdan ajratmaydi.
 *
 * ⚠ UCH QUYI CHEGARA MAJBURIY (§S-10 — bo'sh to'plamda hamma assert
 *   JIMGINA o'tardi):
 *
 *     (1) skanerlangan kalitlar soni har tilda >= 20;
 *     (2) har taqiq ro'yxati BO'SH EMAS;
 *     (3) ⛔ NAZORAT HOLATI — har taqiq uchun sun'iy IJOBIY satr
 *         detektorga berilib, u haqiqatan ushlanishi tasdiqlanadi, VA
 *         qonuniy satr ushlanMAsligi ham tasdiqlanadi. Ya'ni
 *         DETEKTORNING O'ZI ham o'lchanadi (03-08 dagi G-4 naqshi).
 *
 *   (3) siz darvoza «hech qachon qizarmaydigan» holatga tushishi
 *   mumkin edi va buni faqat sabotaj ko'rsatardi.
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const MESSAGES_DIR = path.join(import.meta.dirname, "..", "messages");
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

/** 5-fazaning matn namespace'lari — SKANER MAYDONINING chegarasi. */
const SCANNED_NAMESPACES = ["cameraZones", "review", "occupancy"];

/**
 * Tizim JAVOBI ko'rsatiladigan sirtlar — «tuzatish» taqig'i FAQAT shu yerda.
 *
 * ⚠ CHEGARA ANIQ va u D-12 dan kelib chiqadi. `cameraZones.*` da tizimning
 *   javobi UMUMAN YO'Q: u yerda admin poligon chizadi va «tepani
 *   to'g'rilang» ma'nosidagi fe'l MUTLAQO qonuniy. Taqiq esa `review.*`
 *   va `occupancy.*` da ishlaydi — o'sha ikki ekranda tizim verdikti
 *   ko'rinadi va «tuzatish» so'zi uning USTIGA YOZISHNI anglatardi,
 *   holbuki nazoratchi qarori ALOHIDA yozuv.
 *
 *   Yassi (hamma namespace bo'yicha) taqiq zona muharririning to'g'ri
 *   matnini qizartirardi va ijrochi uni buzib «tuzatgan» bo'lardi — bu
 *   `ъ` diskriminatorining (S-15) aynan bir xil xatosi.
 */
const SYSTEM_VERDICT_NAMESPACES = ["review", "occupancy"];

/** G-15 ning skaner maydoni — kalit PREFIKSLARI (namespace bilan birga). */
const NO_COVERAGE_KEY_PREFIXES = [
  "occupancy.noCoverage",
  "cameraZones.uncovered",
];

/** Quyi chegara — bo'sh to'plam ustidagi sikl yashil bo'lmasin (§S-10). */
const MIN_SCANNED_KEYS = 20;

function loadMessages(locale) {
  return JSON.parse(readFileSync(path.join(MESSAGES_DIR, `${locale}.json`), "utf8"));
}

/** `{namespace}.{...}` -> qiymat juftliklari (faqat satrlar). */
function flatten(node, prefix, out = new Map()) {
  for (const [key, value] of Object.entries(node ?? {})) {
    const full = `${prefix}.${key}`;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flatten(value, full, out);
    } else if (typeof value === "string") {
      out.set(full, value);
    }
  }
  return out;
}

/** Bitta tildagi UCHALA namespace'ning yassilangan kalitlari. */
function scannedKeys(locale) {
  const messages = loadMessages(locale);
  const out = new Map();
  for (const namespace of SCANNED_NAMESPACES) {
    flatten(messages[namespace], namespace, out);
  }
  return out;
}

/* ---------------------------------------------------------------------------
 * QAMROV CHEGARASI — hamma qolgan testning SHARTI.
 * ------------------------------------------------------------------------ */

test("QAMROV: har tilda kamida 20 kalit skanerlanadi (§S-10)", () => {
  /*
   * Usiz quyidagi to'rtala darvoza ham BO'SH to'plam ustida aylanib,
   * jimgina yashil bo'lardi — aynan 04-13 ning eng qimmat darsi.
   * Namespace nomi o'zgarsa (`cameraZones` -> `zones`) bu test QIZARADI.
   */
  for (const locale of LOCALES) {
    const keys = scannedKeys(locale);
    assert.ok(
      keys.size >= MIN_SCANNED_KEYS,
      `${locale}.json: ${SCANNED_NAMESPACES.join("/")} dan atigi ${keys.size} kalit ` +
        `o'qildi (kutilgan >= ${MIN_SCANNED_KEYS}). Namespace nomi o'zgargan bo'lsa ` +
        "darvozalar bo'sh to'plam ustida ishlab, JIMGINA yashil qolardi.",
    );
  }
});

test("QAMROV: skaner haqiqatan QIYMATLARNI o'qiydi (nazorat)", () => {
  /*
   * Yuqoridagi test faqat kalitlar SONINI biladi. Agar `flatten` bir kun
   * qiymat o'rniga bo'sh satr qaytarsa, to'rtala taqiq ham hech nimani
   * ko'rmasdi. Shu sababdan: kamida bitta MA'LUM kalitning qiymati
   * bo'sh emasligi tekshiriladi.
   */
  const causes = scannedKeys("uz-Latn");
  const sample = causes.get("cameraZones.errorCause.zone_polygon_self_intersecting");
  assert.equal(
    typeof sample,
    "string",
    "nazorat kaliti topilmadi — skaner maydoni siljigan bo'lishi mumkin",
  );
  assert.ok(sample.length > 10, "skaner qiymat o'rniga bo'sh satr o'qiyapti");
});

/* ---------------------------------------------------------------------------
 * G-11 — AKRONIM TAQIG'I (§12.10) [O'LCHANDI: M-5]
 * ------------------------------------------------------------------------ */

/**
 * ⚠ REGISTRGA SEZGIR va SO'Z CHEGARALI — ikkalasi ham majburiy.
 *
 *   Registrsiz qidiruv o'zbekcha so'zlar ichidagi harf birikmalarini
 *   ushlab, darvozani yolg'on qizartirardi. Chegarasiz qidiruv esa
 *   `SVG` ni `...svg...` ichidan topib, o'sha natijani berardi.
 *
 * ⚠ `RF-DETR` da `\b` DEFISDAN keyin ham ishlaydi, shuning uchun u
 *   yaxlit satr sifatida qidiriladi.
 */
const FORBIDDEN_ACRONYMS = [
  /\bAI\b/u,
  /\bCV\b/u,
  /\bONNX\b/u,
  /RF-DETR/u,
  /\bJSON\b/u,
  /\bSVG\b/u,
];

/**
 * ⛔ M-5 NING ASL DEFEKTI: BITTA TOKEN IKKI ALIFBODA.
 *
 * `CV` -> `CВ` da lotin `C` (U+0043) va kirill `В` (U+0412) yonma-yon
 * turadi. `gen-cyrillic.test.mjs` ning "lotin qoldi" detektori bunga
 * KO'R: lotin harfi haqiqatan qolgan, ya'ni u nuqtai nazardan hech
 * narsa buzilmagan.
 *
 * ⚠ RO'YXAT EMAS, PREDIKAT (§S-10). Bu tekshiruv akronim NOMLARINI
 *   bilmaydi va bilishi ham kerak emas: yuqoridagi ro'yxatga tushmagan
 *   YANGI akronim ham (masalan `IoU`, `mAP`) transliteratsiyadan aynan
 *   shu shaklda chiqadi va shu yerda ushlanadi.
 */
function mixedAlphabetTokens(text) {
  const hits = [];
  for (const [token] of text.matchAll(/[A-Za-zА-Яа-яЁёҚқҒғҲҳЎў]+/gu)) {
    const hasLatin = /[A-Za-z]/u.test(token);
    const hasCyrillic = /[А-Яа-яЁёҚқҒғҲҳЎў]/u.test(token);
    if (hasLatin && hasCyrillic) hits.push(token);
  }
  return hits;
}

function acronymHits(text) {
  return FORBIDDEN_ACRONYMS.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

test("G-11: taqiq ro'yxati BO'SH EMAS", () => {
  assert.ok(FORBIDDEN_ACRONYMS.length > 0, "akronim ro'yxati bo'shab qolgan");
});

test("G-11: NAZORAT — detektor sun'iy ijobiy satrni USHLAYDI", () => {
  assert.ok(acronymHits("AI javobini ko'rsatadi").length > 0);
  assert.ok(acronymHits("CV xizmati kadrni o'qidi").length > 0);
  assert.ok(acronymHits("ONNX sessiyasi").length > 0);
  assert.ok(acronymHits("RF-DETR modeli").length > 0);
  assert.ok(acronymHits("JSON javobi").length > 0);
  assert.ok(acronymHits("SVG yuzasi").length > 0);

  // Salbiy nazorat: TO'G'RI matn ushlanMAsligi kerak (§12.1 — «tizim»).
  assert.deepEqual(acronymHits("Tizim javobini ko'rmaysiz."), []);
  assert.deepEqual(acronymHits("Система не смогла ответить точно."), []);
  // `\b` chegarasi: so'z ICHIDAGI birikma taqiq EMAS.
  assert.deepEqual(acronymHits("Aniqlik va aivalar"), []);
});

test("G-11: NAZORAT — aralash alifbo detektori M-5 defektini USHLAYDI", () => {
  // Lotin `C` (U+0043) + kirill `В` (U+0412) — aynan o'lchangan chiqish.
  assert.deepEqual(mixedAlphabetTokens("CВ xizmati"), ["CВ"]);
  assert.deepEqual(mixedAlphabetTokens("АИ javobi"), []); // sof kirill — G-11 emas
  assert.deepEqual(mixedAlphabetTokens("Тизим жавоби"), []);
  assert.deepEqual(mixedAlphabetTokens("SBOZOR"), []);
});

test("G-11: `cameraZones.*` / `review.*` / `occupancy.*` da akronim YO'Q", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      for (const hit of acronymHits(value)) {
        problems.push(`${locale}.json: ${key} -> ${hit}`);
      }
      for (const token of mixedAlphabetTokens(value)) {
        problems.push(`${locale}.json: ${key} -> ARALASH ALIFBO «${token}»`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "akronim copy'ga kirdi (§12.10, G-11):\n  " +
      problems.join("\n  ") +
      "\n  Transliteratorda u buziladi (`CV` -> `CВ` — aralash alifbo) VA " +
      "foydalanuvchi uchun ma'no tashimaydi. O'rniga «tizim» yozing.\n" +
      "  ⛔ TO'G'RI JAVOB `uz-Cyrl.overrides.json` GA YOZUV QO'SHISH EMAS — " +
      "matnni akronimsiz qayta yozish (§12.11 Qoida 2).",
  );
});

/* ---------------------------------------------------------------------------
 * G-15 — ⛔ `no_coverage` ≠ «BO'SH» (D-22)
 * ------------------------------------------------------------------------ */

/**
 * ⛔ SPEK BILAN TO'QNASHUV VA UNING YECHIMI — O'QING.
 *
 * §15 (G-15) aytadi: `occupancy.noCoverage*` qiymatlarida `bo'sh` BO'LMASIN.
 * §12.6 esa o'sha kalitning matnini VERBATIM beradi:
 *
 *     «Bu rastalarni birorta kamera ko'rmaydi. Ular BO'SH EMAS — ular
 *      haqida ma'lumot yo'q.»
 *
 * Ya'ni sodda «`bo'sh` bormi?» qoidasi D-22 ni AMALGA OSHIRADIGAN
 * jumlaning O'ZINI qizartirardi va uni "tuzatgan" ijrochi aynan
 * farqni tushuntiruvchi so'zlarni o'chirib tashlagan bo'lardi — matn
 * himoya qilinish o'rniga BUZILARDI.
 *
 * Bu `gen-cyrillic.test.mjs` dagi `ъ` diskriminatorining (S-15) aynan
 * bir xil sinfi va yechim ham o'sha: INKOR SHAKLI oldin OLIB TASHLANADI,
 * qolganida esa `bo'sh` topilsa — bu HAQIQIY defekt, ya'ni qamrovsiz
 * rasta «bo'sh» deb TASDIQLANGAN.
 *
 * Uchala shakl ham o'lchandi (`npm run i18n:gen` chiqishi bo'yicha):
 *   uz-Latn  `bo'sh emas`     uz-Cyrl  `бўш эмас`     ru  `не свободны`
 */
/*
 * ⚠ `\b` BU YERDA ISHLATILMAYDI va bu O'LCHANGAN QAROR.
 *
 *   JavaScript'da `\b` `\w` ga, ya'ni `[A-Za-z0-9_]` ga tayanadi — u
 *   FAQAT ASCII. `u` bayrog'i buni O'ZGARTIRMAYDI. Natijada `/\bбўш/u`
 *   «Улар бўш эмас» ichida HECH QACHON mos kelmaydi: `б` ning o'zi
 *   `\w` emas va undan oldin ham bo'shliq turadi, ya'ni chegara yo'q.
 *
 *   Bu birinchi yozuvda AYNAN shunday bo'ldi va o'lchandi: uz-Latn
 *   o'tdi (u yerda `b` — ASCII), uz-Cyrl va ru esa YOLG'ON QIZARDI.
 *   Xuddi shu sababdan `свободн\w*` ham `свободны` ni to'liq yutmasdi.
 */
const EMPTINESS_NEGATIONS = [
  /bo['ʻʼ‘’]sh\s+emas/giu,
  /бўш\s+эмас/giu,
  /бо['ʻʼ‘’]ш\s+эмас/giu,
  /не\s+свободн[а-яё]*/giu,
];

const EMPTINESS_WORDS = [
  /bo['ʻʼ‘’]sh/iu,
  /бўш/iu,
  /бо['ʻʼ‘’]ш/iu,
  /свободн/iu,
];

function affirmsEmptiness(text) {
  let stripped = text;
  for (const negation of EMPTINESS_NEGATIONS) {
    stripped = stripped.replace(negation, " ");
  }
  return EMPTINESS_WORDS.some((pattern) => pattern.test(stripped));
}

test("G-15: taqiq ro'yxatlari BO'SH EMAS", () => {
  assert.ok(EMPTINESS_WORDS.length > 0, "«bo'sh» ro'yxati bo'shab qolgan");
  assert.ok(EMPTINESS_NEGATIONS.length > 0, "inkor ro'yxati bo'shab qolgan");
});

test("G-15: NAZORAT — detektor TASDIQNI ushlaydi, INKORNI ushlamaydi", () => {
  // IJOBIY nazorat — D-22 ning buzilishi.
  assert.ok(affirmsEmptiness("Qamrovsiz rastalar bo'sh deb hisoblanadi."));
  assert.ok(affirmsEmptiness("Улар бўш."));
  assert.ok(affirmsEmptiness("Эти места свободны."));

  /*
   * ⛔ SALBIY NAZORAT — ENG MUHIMI. Bu uch jumla D-22 ni AMALGA
   * OSHIRADI va ular MATNDA BO'LISHI KERAK. Detektor ularni
   * qizartirsa, u himoya qilayotgan narsani o'zi buzardi.
   */
  assert.ok(
    !affirmsEmptiness("Ular bo'sh emas — ular haqida ma'lumot yo'q."),
    "detektor D-22 ni tushuntiruvchi INKOR jumlasini qizartirdi",
  );
  assert.ok(
    !affirmsEmptiness(
      "Улар бўш эмас — маълумот йўқ.",
    ),
  );
  assert.ok(
    !affirmsEmptiness(
      "Они не свободны — по ним просто нет данных.",
    ),
  );
});

test("G-15: qamrov kalitlari BO'SH EMAS (skaner maydoni mavjud)", () => {
  /*
   * ⚠ Bu assert G-15 ning O'ZINI himoya qiladi: `noCoverage*` kalitlari
   *   umuman bo'lmasa quyidagi test HECH NIMANI tekshirmagan holda
   *   yashil bo'lardi — ya'ni «darvoza bor» degan yolg'on da'vo.
   */
  for (const locale of LOCALES) {
    const matched = [...scannedKeys(locale).keys()].filter((key) =>
      NO_COVERAGE_KEY_PREFIXES.some((prefix) => key.startsWith(prefix)),
    );
    assert.ok(
      matched.length > 0,
      `${locale}.json: ${NO_COVERAGE_KEY_PREFIXES.join(" / ")} prefiksli birorta ` +
        "kalit yo'q — G-15 bo'sh to'plam ustida ishlardi",
    );
  }
});

test("G-15: qamrovsiz rasta «bo'sh» deb ATALMAYDI (D-22)", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      if (!NO_COVERAGE_KEY_PREFIXES.some((prefix) => key.startsWith(prefix))) continue;
      if (affirmsEmptiness(value)) {
        problems.push(`${locale}.json: ${key} -> ${JSON.stringify(value)}`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "qamrovsiz rasta «bo'sh» deb yozilgan (D-22, G-15):\n  " +
      problems.join("\n  ") +
      "\n  Qamrovsiz rasta BO'SH EMAS — u haqida MA'LUMOT YO'Q. Farq DB'da " +
      "bor, lekin matnda yo'qolsa hisobot jimgina noto'g'ri o'qilardi va buni " +
      "hech qanday sxema ushlamasdi.",
  );
});

/* ---------------------------------------------------------------------------
 * G-16 — JARGON TAQIG'I (§12.10)
 * ------------------------------------------------------------------------ */

const FORBIDDEN_JARGON = [
  /poligon/iu,
  /полигон/iu,
  /dataset/iu,
  /датасет/iu,
  /konfidens/iu,
  /конфиденс/iu,
];

/**
 * «Tuzatish» — FAQAT tizim javobi ko'rinadigan sirtlarda taqiqlanadi.
 *
 * D-12: tizim javobi hech qachon o'zgartirilmaydi; nazoratchi qarori —
 * ALOHIDA yozuv. To'g'ri so'z: «javob berish».
 */
const FORBIDDEN_CORRECTION = [/tuzat/iu, /тузат/iu, /исправ/iu];

function jargonHits(text) {
  return FORBIDDEN_JARGON.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

function correctionHits(text) {
  return FORBIDDEN_CORRECTION.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

test("G-16: taqiq ro'yxatlari BO'SH EMAS", () => {
  assert.ok(FORBIDDEN_JARGON.length > 0, "jargon ro'yxati bo'shab qolgan");
  assert.ok(FORBIDDEN_CORRECTION.length > 0, "«tuzatish» ro'yxati bo'shab qolgan");
});

test("G-16: NAZORAT — detektor sun'iy ijobiy satrni USHLAYDI", () => {
  assert.ok(jargonHits("Poligon tepalari").length > 0);
  assert.ok(jargonHits("Полигон вершины").length > 0);
  assert.ok(jargonHits("dataset eksporti").length > 0);
  assert.ok(jargonHits("konfidens qiymati").length > 0);
  assert.ok(correctionHits("Tizim javobini tuzating").length > 0);
  assert.ok(
    correctionHits("Исправьте ответ").length > 0,
  );

  // Salbiy nazorat: TO'G'RI atamalar ushlanMAsligi kerak (§12.1).
  assert.deepEqual(jargonHits("Kamera zonasi tepalari"), []);
  assert.deepEqual(jargonHits("Зона камеры"), []);
  assert.deepEqual(correctionHits("Javob berish"), []);
});

test("G-16: uchala namespace'da jargon YO'Q", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      for (const hit of jargonHits(value)) {
        problems.push(`${locale}.json: ${key} -> ${hit}`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "muhandis atamasi copy'ga kirdi (§12.10, G-16):\n  " +
      problems.join("\n  ") +
      "\n  Foydalanuvchi uchun bu «kamera zonasi». Trening ma'lumoti esa bu " +
      "fazada foydalanuvchi yuzasi EMAS (D-25).",
  );
});

test("G-16: tizim javobiga nisbatan «tuzatish» YO'Q (D-12)", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      const namespace = key.split(".")[0];
      if (!SYSTEM_VERDICT_NAMESPACES.includes(namespace)) continue;
      for (const hit of correctionHits(value)) {
        problems.push(`${locale}.json: ${key} -> ${hit}`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "«tuzatish» tizim javobi ko'rinadigan sirtga kirdi (D-12, G-16):\n  " +
      problems.join("\n  ") +
      "\n  Tizim javobi HECH QACHON o'zgartirilmaydi; nazoratchi qarori — " +
      "ALOHIDA yozuv. «Tuzatish» ustiga yozishni anglatib, D-12 ni jimgina " +
      "yolg'onga aylantirardi. To'g'ri so'z — «javob berish».",
  );
});

/* ---------------------------------------------------------------------------
 * G-18(a) — ⛔ OMMAVIY TASDIQ va QAYTA TORTISH TAQIG'I (D-18, D-17)
 * ------------------------------------------------------------------------ */

/**
 * ⚠ TAQIQ SO'ZGA EMAS, MA'NOGA qo'yilgan — shuning uchun BIRIKMALAR.
 *
 *   Yakka `tasdiqlash` QONUNIY: bitta javobni tasdiqlash — normal amal.
 *   Taqiqlangani — OMMAVIYLIK: «hammasini» / «barchasini» / «все».
 *
 *   Xuddi shunday, yakka `qayta` ham qonuniy: «Qayta urinish» — rasm
 *   ochilmaganda ko'rsatiladigan tugma (§12.4). Taqiqlangani —
 *   NAMUNANI qayta tortish (D-17, 1-himoya).
 *
 *   Yassi so'z taqig'i ikkala qonuniy matnni ham qizartirardi.
 */
const FORBIDDEN_BULK_CONFIRM = [
  /hammasini\s+tasdiq/iu,
  /barchasini\s+tasdiq/iu,
  /ҳаммасини\s+тасдиқ/iu,
  /барчасини\s+тасдиқ/iu,
  /подтвердить\s+вс[её]/iu,
  /подтверди(?:те)?\s+вс[её]/iu,
];

const FORBIDDEN_RESAMPLE = [
  /namunani\s+qayta/iu,
  /qayta\s+tortish/iu,
  /намунани\s+қайта/iu,
  /қайта\s+тортиш/iu,
  /пересобрать\s+выборк/iu,
  /перетянуть\s+выборк/iu,
  /выборку\s+заново/iu,
];

function bulkConfirmHits(text) {
  return FORBIDDEN_BULK_CONFIRM.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

function resampleHits(text) {
  return FORBIDDEN_RESAMPLE.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

test("G-18(a): taqiq ro'yxatlari BO'SH EMAS", () => {
  assert.ok(FORBIDDEN_BULK_CONFIRM.length > 0, "ommaviy tasdiq ro'yxati bo'shab qolgan");
  assert.ok(FORBIDDEN_RESAMPLE.length > 0, "qayta tortish ro'yxati bo'shab qolgan");
});

test("G-18(a): NAZORAT — detektor sun'iy ijobiy satrni USHLAYDI", () => {
  assert.ok(bulkConfirmHits("Hammasini tasdiqlash").length > 0);
  assert.ok(bulkConfirmHits("Barchasini tasdiqlang").length > 0);
  assert.ok(
    bulkConfirmHits("Ҳаммасини тасдиқлаш").length > 0,
  );
  assert.ok(
    bulkConfirmHits("Подтвердить все").length > 0,
  );

  assert.ok(resampleHits("Namunani qayta tortish").length > 0);
  assert.ok(
    resampleHits("Намунани қайта тортиш").length > 0,
  );
  assert.ok(
    resampleHits("Пересобрать выборку").length > 0,
  );
  assert.ok(
    resampleHits("Перетянуть выборку").length > 0,
  );

  /*
   * ⛔ SALBIY NAZORAT — bu matnlar EKRANDA BO'LISHI KERAK.
   *   «Qayta urinish» — rasm ochilmaganda yagona to'g'ri amal (§12.4);
   *   yakka «tasdiqlash» — bitta javobning normal tasdig'i.
   */
  assert.deepEqual(bulkConfirmHits("Javobni tasdiqlash"), []);
  assert.deepEqual(resampleHits("«Qayta urinish» ni bosing."), []);
  assert.deepEqual(resampleHits("Qo'lda tortish mumkin emas."), []);
  assert.deepEqual(
    resampleHits("Қўлда тортиш мумкин эмас."),
    [],
  );
});

test("G-18(a): «hammasini tasdiqlash» va «namunani qayta tortish» copy'da YO'Q", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      for (const hit of bulkConfirmHits(value)) {
        problems.push(`${locale}.json: ${key} -> OMMAVIY TASDIQ (${hit})`);
      }
      for (const hit of resampleHits(value)) {
        problems.push(`${locale}.json: ${key} -> QAYTA TORTISH (${hit})`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ taqiqlangan IMKONIYAT matnda tug'ildi (D-18 / D-17, G-18):\n  " +
      problems.join("\n  ") +
      "\n  Bu darvoza kodni emas, IMKONIYATNING TUG'ILISHINI to'xtatadi: so'z " +
      "copy'ga kirsa, keyingi ijrochi uni AMALGA OSHIRISHGA urinardi — 2 va " +
      "3-fazada aynan shunday bo'lgan (§16.2).",
  );
});
