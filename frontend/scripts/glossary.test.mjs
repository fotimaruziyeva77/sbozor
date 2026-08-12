#!/usr/bin/env node
/**
 * G7-9 — ATAMALAR IKKI MANBADA YAGONA (D-30, 07-UI-SPEC §16.4).
 *
 * Ikki manba bor va ular butunlay boshqa texnologiyada yozilgan:
 *
 *     frontend/messages/<locale>.json            (next-intl, JSON)
 *     services/bot-service/app/locales/<loc>/…    (gettext, .po)
 *
 * Ularni hech qanday kompilyator, tip tizimi yoki lint bog'lamaydi.
 * Bitta manbaga «yig'im» yozib qo'yish na typecheck'ni, na birorta
 * komponent testini qizartiradi — va sotuvchi bir ekranda «patta»,
 * boshqasida «yig'im» ko'radi. Aynan shuning uchun bu darvoza mavjud.
 *
 * =============================================================================
 * ⛔⛔ UCHINCHI BAND (TAQIQLANGAN SINONIMLAR) MAJBURIY.
 *
 * (a) va (b) bandlari «atama IKKALASIDA HAM BOR» ni tasdiqlaydi, lekin
 * IKKINCHI SO'ZNING PAYDO BO'LISHINI to'smaydi: «patta» ham, «yig'im» ham
 * bir vaqtda mavjud bo'lgan copy ikkala bandni ham qanoatlantiradi.
 *
 * =============================================================================
 * ⛔⛔ VA UCHINCHI BAND PER-LOCALE BO'LISHI SHART — BU FAZANING ENG NOZIK
 *    «JIMGINA YASHIL» TUZOG'I (07-UI-SPEC §14.5 / §16.4, M-11).
 *
 * Sabab MEXANIK: `ru.json` MUSTAQIL tarjima fayli, lotin matnidan
 * transliteratsiya HOSILASI EMAS (faqat `uz-Cyrl.json` hosila). Ya'ni
 * `ru.json` ni lotin `yig'im` tokeni bilan skanerlash ⛔ MAZMUNIDAN QAT'I
 * NAZAR har doim 0 qaytaradi: darvoza MAVJUD BO'LIB KO'RINADI va HECH
 * NIMANI O'LCHAMAYDI. O'sha mantiq `uz-Cyrl` ga ham tegishli.
 *
 * Shuning uchun `glossary.json` da taqiq HAR LOCALE UCHUN O'Z TOKENLARI
 * bilan yozilgan va (f) bandi UCHALA locale uchun ALOHIDA nazorat
 * sabotajini talab qiladi. Faqat lotin nazorati bo'lsa, aynan shu BLOKER
 * (ru va uz-Cyrl o'lchanmasligi) qaytarib bo'lmasdi.
 *
 * =============================================================================
 * ⛔ BU FAYL O'Z QOIDASINI O'ZI BUZADI — VA BU ATAYIN.
 *
 * Yuqoridagi izohlarda `yig'im`, `do'kon` va `магазин` YOZILGAN: darvoza
 * o'zi nimani taqiqlayotganini AYTISHI kerak, aks holda keyingi ishlovchi
 * qoidani UI-SPEC dan qidirib yurardi.
 *
 * Shuning uchun SKANER MAYDONI QAT'IY: faqat `messages/*.json` ning
 * QIYMATLARI va `.po` ning `msgstr` QIYMATLARI. Bu faylning O'Z manbasi
 * hech qachon o'qilmaydi. (`zone-copy.test.mjs` bilan aynan bir xil qaror.)
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const REPO_ROOT = path.join(import.meta.dirname, "..", "..");
const MESSAGES_DIR = path.join(REPO_ROOT, "frontend", "messages");
const BOT_LOCALES_DIR = path.join(
  REPO_ROOT,
  "services",
  "bot-service",
  "app",
  "locales",
);
const GLOSSARY_PATH = path.join(REPO_ROOT, "ops", "i18n", "glossary.json");

/**
 * (g) Frontend ↔ bot locale identifikatorlari xaritasi.
 *
 * ⚠ NOMLAR ATAYIN BOSHQACHA: gettext katalog KATALOGI POSIX ajratgichini
 *   (`uz_Latn`) talab qiladi, `next-intl` esa BCP-47 ni (`uz-Latn`).
 *   Xarita shu yerda, bitta joyda; to'liqligi quyida o'lchanadi.
 */
const LOCALE_MAP = {
  "uz-Latn": "uz_Latn",
  "uz-Cyrl": "uz_Cyrl",
  ru: "ru",
};

const LOCALES = Object.keys(LOCALE_MAP);

/**
 * ⛔⛔ (d) BANDINING BUTUN MAZMUNI — KUTILGAN TO'PLAM SHU YERDA QAYTA YOZILGAN.
 *
 * `glossary.json` dan IMPORT QILINMAYDI (05-15 darsi): import darvozani
 * o'zi tekshirayotgan qiymatga bog'lardi va fayldan JIMGINA o'chirilgan
 * token darvozadan O'TIB KETARDI.
 *
 * To'plam tengligi IKKI TOMONLAMA ishlaydi:
 *   * oltala tokenning BORLIGINI majburlaydi;
 *   * har qanday YANGI tokenning (jumladan `сбор` ning) YO'QLIGINI
 *     majburlaydi — alohida «yo'q» da'vosi yozilmaydi.
 */
const EXPECTED_BANNED_TOKENS = {
  "uz-Latn": ["do'kon", "yig'im"],
  "uz-Cyrl": ["дўкон", "йиғим"],
  ru: ["лавк", "магазин"],
};

/** ⛔ Quyi chegara (§16.4 c) — bo'sh reyestr ustida sikl JIMGINA yashil bo'lardi. */
const MIN_TERMS = 4;
const LOCALES_PER_TERM = 3;

/* ---------------------------------------------------------------------------
 * Normalizatsiya va o'qish
 * ------------------------------------------------------------------------ */

/**
 * Apostrof variantlari ASCII `'` ga keltiriladi.
 *
 * ⚠ `gen-cyrillic.mjs::APOSTROPHE_VARIANTS` bilan AYNI ro'yxat. Nusxa
 *   ATAYIN: bu skript `frontend/` ning ichki moduliga bog'lanmasligi kerak
 *   (u `services/bot-service` ni ham o'qiydi), lekin qoida bir xil bo'lishi
 *   shart — aks holda `yig’im` (tipografik apostrof) taqiqdan o'tib ketardi.
 */
function normalize(text) {
  return text.replace(/[ʻʼ‘’]/g, "'").toLowerCase();
}

function loadGlossary() {
  return JSON.parse(readFileSync(GLOSSARY_PATH, "utf8"));
}

/** `{a: {b: "x"}}` -> `["a.b", "x"]` juftliklari (faqat satrlar). */
function flattenMessages(node, prefix = "", out = []) {
  for (const [key, value] of Object.entries(node ?? {})) {
    const full = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flattenMessages(value, full, out);
    } else if (typeof value === "string") {
      out.push([full, value]);
    }
  }
  return out;
}

function messageValues(locale) {
  const file = path.join(MESSAGES_DIR, `${locale}.json`);
  return flattenMessages(JSON.parse(readFileSync(file, "utf8")));
}

function unescapePo(raw) {
  return raw
    .replace(/\\n/g, "\n")
    .replace(/\\t/g, "\t")
    .replace(/\\"/g, '"')
    .replace(/\\\\/g, "\\");
}

/**
 * `.po` faylning `msgstr` QIYMATLARI (`msgid` bo'sh bo'lgan SARLAVHASIZ).
 *
 * ⚠ Sarlavha bloki (`msgid ""`) ATAYIN chiqarib tashlanadi: unda
 *   `Plural-Forms`, `Language` va `Content-Type` yozilgan va ular matn
 *   emas, metama'lumot. Ularni skanerga qo'shish (a) bandini
 *   tasodifiy tokenlar bilan «qanoatlantirib» qo'yishi mumkin edi.
 *
 * ⚠ Izoh satrlari (`#`) ham o'qilmaydi — `.po` fayllar taqiqning
 *   SABABINI o'z izohlarida yozadi (yuqoridagi «o'z qoidasini buzadi»
 *   bandining aynan o'zi).
 */
function poMsgstrValues(locale) {
  const file = path.join(
    BOT_LOCALES_DIR,
    LOCALE_MAP[locale],
    "LC_MESSAGES",
    "bot.po",
  );
  const lines = readFileSync(file, "utf8").split(/\r?\n/);

  const entries = [];
  let currentId = null;
  let target = null; // "id" | "str" | null
  let buffer = "";

  const flush = () => {
    if (target === "id") currentId = (currentId ?? "") + buffer;
    else if (target === "str") entries.push([currentId ?? "", buffer]);
    buffer = "";
    target = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (line === "" || line.startsWith("#")) {
      flush();
      if (line === "") currentId = null;
      continue;
    }
    const idMatch = /^msgid(?:_plural)?\s+"(.*)"$/.exec(line);
    if (idMatch) {
      flush();
      // ⚠ `msgid_plural` ID ni ALMASHTIRMAYDI: birinchi `msgid` yetarli.
      if (line.startsWith("msgid ")) currentId = "";
      target = line.startsWith("msgid ") ? "id" : null;
      buffer = line.startsWith("msgid ") ? unescapePo(idMatch[1]) : "";
      if (target === null) buffer = "";
      continue;
    }
    const strMatch = /^msgstr(?:\[\d+\])?\s+"(.*)"$/.exec(line);
    if (strMatch) {
      flush();
      target = "str";
      buffer = unescapePo(strMatch[1]);
      continue;
    }
    const contMatch = /^"(.*)"$/.exec(line);
    if (contMatch && target !== null) {
      buffer += unescapePo(contMatch[1]);
      continue;
    }
    flush();
  }
  flush();

  // ⛔ Sarlavha bloki (`msgid ""`) tashlanadi.
  return entries.filter(([id]) => id !== "").map(([id, value]) => [id, value]);
}

/* ---------------------------------------------------------------------------
 * Predikatlar — ⛔ sun'iy matnlarda ham AYNAN shu funksiyalar ishlaydi
 * ------------------------------------------------------------------------ */

/**
 * O'zak `entries` qiymatlarida necha marta uchraydi.
 *
 * ⚠ QIDIRUV O'ZAK BO'YICHA va bu ONGLI QAROR (07-UI-SPEC §14.5): o'zbek
 *   affikslari (`pattani`, `pattaning`) va rus kelishiklari (`места`,
 *   `местами`) to'liq so'z qidiruvini yolg'on-qizil qilardi.
 */
function countStem(entries, stem) {
  const needle = normalize(stem);
  return entries.filter(([, value]) => normalize(value).includes(needle)).length;
}

/** Taqiqlangan tokenlarning uchrashlari — `locale: key -> token` shaklida. */
function bannedHits(entries, tokens, label) {
  const problems = [];
  for (const token of tokens) {
    const needle = normalize(token);
    for (const [key, value] of entries) {
      if (normalize(value).includes(needle)) {
        problems.push(`${label}: ${key} -> «${token}»`);
      }
    }
  }
  return problems;
}

/** Bir locale'ning BARCHA taqiqlangan tokenlari (atamalar bo'yicha tekislangan). */
function flattenBannedTokens(glossary, locale) {
  const tokens = new Set();
  for (const perLocale of Object.values(glossary.banned_synonyms)) {
    for (const token of perLocale[locale] ?? []) tokens.add(token);
  }
  return [...tokens].sort();
}

/* ---------------------------------------------------------------------------
 * (e) QUYI CHEGARA — hamma qolgan bandning SHARTI
 * ------------------------------------------------------------------------ */

test("G7-9 (e): reyestrda >= 4 atama va har birida AYNAN 3 locale", () => {
  const glossary = loadGlossary();

  assert.ok(
    Object.keys(glossary.terms).length >= MIN_TERMS,
    `glossary.json: ${Object.keys(glossary.terms).length} atama (kutilgan >= ${MIN_TERMS}) — ` +
      "bo'sh yoki qisqargan reyestr ustida quyidagi bandlar JIMGINA yashil bo'lardi",
  );

  for (const [term, perLocale] of Object.entries(glossary.terms)) {
    assert.deepEqual(
      Object.keys(perLocale).sort(),
      [...LOCALES].sort(),
      `terms.${term} da aynan 3 locale kaliti bo'lishi shart`,
    );
  }
  for (const [term, perLocale] of Object.entries(glossary.banned_synonyms)) {
    assert.deepEqual(
      Object.keys(perLocale).sort(),
      [...LOCALES].sort(),
      `banned_synonyms.${term} da aynan 3 locale kaliti bo'lishi shart ` +
        "(bo'sh ro'yxat QONUNIY, kalitning YO'QLIGI emas)",
    );
  }
  assert.deepEqual(
    Object.keys(glossary.terms).sort(),
    Object.keys(glossary.banned_synonyms).sort(),
    "`terms` va `banned_synonyms` atamalari mos kelmayapti — biriga qo'shilgan " +
      "atama ikkinchisida jimgina taqiqsiz qolardi",
  );
});

test("G7-9 (e): skaner maydoni HAQIQATAN o'qiladi (nazorat)", () => {
  /*
   * Yuqoridagi test faqat reyestrni biladi. Agar o'quvchilar bir kun bo'sh
   * ro'yxat qaytarsa, (a)-(c) bandlari hech nimani ko'rmasdi.
   */
  for (const locale of LOCALES) {
    assert.ok(messageValues(locale).length > 500, `${locale}.json bo'sh o'qildi`);
    assert.ok(
      poMsgstrValues(locale).length >= 10,
      `${LOCALE_MAP[locale]}/bot.po dan atigi ${poMsgstrValues(locale).length} msgstr o'qildi`,
    );
  }
});

/* ---------------------------------------------------------------------------
 * (a) FRONTEND — atama har locale'da >= 1 marta
 * ------------------------------------------------------------------------ */

test("G7-9 (a): har atama `messages/<locale>.json` da >= 1 marta", () => {
  const glossary = loadGlossary();
  const problems = [];
  for (const locale of LOCALES) {
    const entries = messageValues(locale);
    for (const [term, perLocale] of Object.entries(glossary.terms)) {
      const count = countStem(entries, perLocale[locale]);
      if (count === 0) {
        problems.push(`${locale}.json: «${term}» (o'zak «${perLocale[locale]}») -> 0`);
      }
    }
  }
  assert.deepEqual(
    problems,
    [],
    "glossariy atamasi veb copy'sida UMUMAN yo'q (D-30, G7-9 a):\n  " +
      problems.join("\n  "),
  );
});

/* ---------------------------------------------------------------------------
 * (b) BOT — o'sha atama `.po` ning `msgstr` qiymatlarida >= 1 marta
 * ------------------------------------------------------------------------ */

test("G7-9 (b): har atama bot `.po` ning `msgstr` larida >= 1 marta", () => {
  const glossary = loadGlossary();
  const problems = [];
  for (const locale of LOCALES) {
    const entries = poMsgstrValues(locale);
    for (const [term, perLocale] of Object.entries(glossary.terms)) {
      const count = countStem(entries, perLocale[locale]);
      if (count === 0) {
        problems.push(
          `${LOCALE_MAP[locale]}/bot.po: «${term}» (o'zak «${perLocale[locale]}») -> 0`,
        );
      }
    }
  }
  assert.deepEqual(
    problems,
    [],
    "glossariy atamasi bot copy'sida UMUMAN yo'q (D-30, G7-9 b):\n  " +
      problems.join("\n  ") +
      "\n  Ikki yuza bir xil atamani ishlatishi SHART: sotuvchi bir ekranda " +
      "bir so'zni, ikkinchisida boshqasini ko'rsa, u ikki xil to'lov deb o'ylardi.",
  );
});

/* ---------------------------------------------------------------------------
 * (c) ⛔⛔ PER-LOCALE TAQIQ — ikkala manbada ham 0
 * ------------------------------------------------------------------------ */

test("G7-9 (c): taqiqlangan sinonim IKKALA manbada ham 0 (per-locale)", () => {
  const glossary = loadGlossary();
  const problems = [];
  for (const locale of LOCALES) {
    const tokens = flattenBannedTokens(glossary, locale);
    problems.push(...bannedHits(messageValues(locale), tokens, `${locale}.json`));
    problems.push(
      ...bannedHits(poMsgstrValues(locale), tokens, `${LOCALE_MAP[locale]}/bot.po`),
    );
  }
  assert.deepEqual(
    problems,
    [],
    "⛔ taqiqlangan sinonim copy'ga kirdi (D-30, G7-9 c):\n  " +
      problems.join("\n  ") +
      "\n  Atama YAGONA bo'lishi kerak: «patta» va «yig'im» bir vaqtda mavjud " +
      "bo'lsa (a) va (b) bandlari ikkalasi ham yashil qolardi va aynan shuning " +
      "uchun uchinchi band bor.",
  );
});

/* ---------------------------------------------------------------------------
 * (d) ⛔⛔ `сбор` ISTISNOSINING QULFI — TO'PLAM TENGLIGI
 * ------------------------------------------------------------------------ */

test("G7-9 (d): tekislangan taqiq to'plami LITERAL ro'yxat bilan TENG", () => {
  /*
   * ⛔ Kutilgan ro'yxat SHU FAYLDA qayta yozilgan va `glossary.json` dan
   *   IMPORT QILINMAYDI (05-15 darsi). Import darvozani o'zi tekshirayotgan
   *   qiymatga bog'lardi: fayldan jimgina o'chirilgan token o'tib ketardi.
   *
   * ⛔ `сбор` ning YO'QLIGI shu tenglikdan HOSILA — alohida `not.toContain`
   *   YOZILMAYDI. Tenglik ikki tomonlama ishlaydi: oltala tokenning
   *   borligini ham, har qanday YANGI tokenning yo'qligini ham majburlaydi.
   */
  const glossary = loadGlossary();
  for (const locale of LOCALES) {
    assert.deepEqual(
      flattenBannedTokens(glossary, locale),
      [...EXPECTED_BANNED_TOKENS[locale]].sort(),
      `${locale}: taqiq ro'yxati kutilganidan farq qiladi. Token QO'SHILGAN ` +
        "bo'lsa uni shu faylga ham yozing; O'CHIRILGAN bo'lsa — sabab " +
        "`glossary.json` ning `_sbor_exception` bandi kabi SO'Z BILAN yozilsin.",
    );
  }
  const total = LOCALES.reduce(
    (sum, locale) => sum + flattenBannedTokens(glossary, locale).length,
    0,
  );
  assert.equal(total, 6, `jami 6 token kutilgan, topildi ${total}`);
});

/* ---------------------------------------------------------------------------
 * (f) ⛔⛔ NAZORAT — UCHALA LOCALE UCHUN ALOHIDA
 * ------------------------------------------------------------------------ */

test("G7-9 (f): NAZORAT — ekilgan sinonim UCHALA locale'da ham USHLANADI", () => {
  /*
   * ⛔ UCHALASI HAM MAJBURIY. Faqat lotin nazorati bo'lsa, aynan bu
   *   BLOKERNING o'zi (ru va uz-Cyrl O'LCHANMASLIGI) qaytarib bo'lmasdi:
   *   `ru.json` mustaqil tarjima, ya'ni lotin token u yerda HECH QACHON
   *   uchramaydi va band mazmunidan qat'i nazar yashil bo'lardi.
   */
  const glossary = loadGlossary();
  const planted = {
    "uz-Latn": [["x", "bugungi yig'im"]],
    "uz-Cyrl": [["x", "бугунги йиғим"]],
    ru: [["x", "магазин № 5"]],
  };

  for (const locale of LOCALES) {
    const tokens = flattenBannedTokens(glossary, locale);
    const hits = bannedHits(planted[locale], tokens, `${locale}(sun'iy)`);
    assert.ok(
      hits.length > 0,
      `${locale}: ekilgan sinonim USHLANMADI — bu locale uchun taqiq ` +
        "MAZMUNIDAN QAT'I NAZAR yashil bo'lardi",
    );
  }

  // ⛔ SALBIY NAZORAT — qonuniy matn qizarmasligi shart.
  //    «Yig'ish» (nav.collect) AMAL va u taqiqlanmagan; token aynan
  //    «yig'im» bo'lgani uchun bu satr o'tadi.
  assert.deepEqual(
    bannedHits(
      [["nav.collect", "Yig'ish"]],
      flattenBannedTokens(glossary, "uz-Latn"),
      "uz-Latn(sun'iy)",
    ),
    [],
    "«Yig'ish» (AMAL) qonuniy — token «yig'» ga qisqartirilgan bo'lsa kerak",
  );
  assert.deepEqual(
    bannedHits([["nav.collect", "Сбор"]], flattenBannedTokens(glossary, "ru"), "ru"),
    [],
    "«сбор» taqiq ro'yxatida BO'LMASLIGI kerak (M-11 istisnosi)",
  );
});

test("G7-9 (f): NAZORAT — apostrof shakli taqiqdan o'tkazmaydi", () => {
  /*
   * ⚠ Tipografik apostrof (U+2019) bilan yozilgan «yig’im» ham
   *   USHLANISHI shart: aks holda darvozani chetlab o'tish uchun bitta
   *   belgi almashtirish yetardi va u ko'zga ham tashlanmasdi.
   */
  const tokens = flattenBannedTokens(loadGlossary(), "uz-Latn");
  assert.ok(bannedHits([["x", "bugungi yig’im"]], tokens, "x").length > 0);
  assert.ok(bannedHits([["x", "bugungi yigʻim"]], tokens, "x").length > 0);
});

/* ---------------------------------------------------------------------------
 * (g) LOCALE IDENTIFIKATORLARI — xarita TO'LIQ
 * ------------------------------------------------------------------------ */

test("G7-9 (g): frontend va bot locale identifikatorlari xaritalangan", () => {
  /*
   * Bir tomonga qo'shilgan til ikkinchisida JIMGINA yo'q bo'lardi va
   * yuqoridagi bandlar uni umuman ko'rmasdi.
   */
  for (const [webLocale, botLocale] of Object.entries(LOCALE_MAP)) {
    assert.ok(
      messageValues(webLocale).length > 0,
      `messages/${webLocale}.json topilmadi`,
    );
    assert.ok(
      poMsgstrValues(webLocale).length > 0,
      `bot katalogi ${botLocale} topilmadi`,
    );
  }
  assert.equal(Object.keys(LOCALE_MAP).length, 3, "uchala locale majburiy (D-31)");
});
