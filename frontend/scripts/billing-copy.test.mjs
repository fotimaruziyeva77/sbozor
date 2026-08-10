#!/usr/bin/env node
/**
 * 6-FAZANING REYESTR DARVOZALARI — G-24, G-26 va §5.10 NING YOPILISHI.
 *
 * Uch blok, uchtasi ham `zone-copy.test.mjs` shablonida (reyestrdan
 * iteratsiya · uchala locale · TO'PLAM TENGLIGI · quyi chegara):
 *
 *   G-24 (D-19)  ⛔ SABAB-KODLARNING YOPIQLIGI VA NARXI. `other`/`custom`
 *                erkin matnni QAYTARIB KELTIRARDI va hisobotda AMALDA eng
 *                katta guruh bo'lib qolardi — ya'ni D-19 ning butun maqsadi
 *                (summani o'zgartirishni ATAYIN qimmat qilish) bekor
 *                bo'lardi.
 *
 *   G-26 (C-12)  ANOMALIYA TURLARI, AKRONIM VA TAQIQLANGAN SO'ZLAR.
 *                `no_coverage_stall` «BO'SH» EMAS (D-05): farq DB'da bor,
 *                lekin MATN darajasida yo'qolsa hisobot jimgina noto'g'ri
 *                o'qilardi va buni HECH QANDAY sxema ushlamaydi.
 *
 *   §5.10        ⛔⛔ BACKEND <-> FRONTEND ENUM PARITY — TO'RT SOLISHTIRUV.
 *
 * =============================================================================
 * ⛔ UCHINCHI BLOK NIMA UCHUN BU FAYLDA TUG'ILDI — O'LCHOV BILAN.
 *
 *   `readPythonEnumValues()` loyihada 06-02 gacha AYNAN IKKI joyda
 *   ishlatilgan: `audit-actions.test.mjs:46-55` (`AuditAction`) va
 *   `role-gate.test.mjs:174-183` (`Role`). Ya'ni DOMEN enum'lari uchun
 *   parity darvozasi UMUMAN MAVJUD EMAS edi (06-PATTERNS §5.10).
 *
 *   Oqibati jim: backendga yangi `AnomalyKind` a'zosi qo'shilsa, u
 *   `api-types.ts` ko'zgusisiz o'tib ketardi — hech bir test qizarmasdi,
 *   chunki backend testlari frontend faylini bilmaydi, frontend esa
 *   backendni. Ekranda esa uchinchi anomaliya turi UMUMAN chizilmasdi va
 *   BILL-04 jimgina to'liq bo'lmagan hisobot berardi.
 *
 *   Shuning uchun bu blok TO'RT enum'ni birdan bog'laydi va u YAGONA joyda
 *   yashaydi: to'rt marta ko'chirilgan solishtirish bir kun uchtaga
 *   aylanardi.
 *
 * ⛔ BU FAYL O'Z QOIDASINI O'ZI BUZADI — VA BU ATAYIN (zone-copy naqshi).
 *
 *   Yuqoridagi va pastdagi izohlarda `variance`, `storno`, `proyeksiya`
 *   kabi TAQIQLANGAN tokenlar yozilgan bo'lishi mumkin: darvoza o'zi nimani
 *   taqiqlayotganini AYTISHI kerak. Shuning uchun SKANER MAYDONI QAT'IY —
 *   faqat `messages/*.json` ning `collect.*` va `billing.*` QIYMATLARI. Bu
 *   faylning O'Z manbasi hech qachon o'qilmaydi va `grep` asosidagi
 *   tekshiruv BU YERDA UMUMAN ISHLATILMAYDI.
 *
 * ⚠ QUYI CHEGARALAR MAJBURIY (`MIN_*`): bo'sh to'plamda «taqiqlangan token
 *   topilmadi» JIMGINA ROST bo'ladi (`blind-payload.test.mjs` qoidasi).
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const MESSAGES_DIR = path.join(FRONTEND_ROOT, "messages");
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

const API_TYPES = path.join(FRONTEND_ROOT, "src", "lib", "api-types.ts");
const CORE_ENUMS = path.join(
  REPO_ROOT,
  "packages",
  "sbozor-core",
  "sbozor_core",
  "enums.py",
);

/** 6-fazaning matn namespace'lari — SKANER MAYDONINING chegarasi (§13.2). */
const SCANNED_NAMESPACES = ["collect", "billing"];

/** Quyi chegaralar — bo'sh to'plam ustidagi sikl yashil bo'lmasin. */
const MIN_SCANNED_KEYS = 60;
const MIN_ACRONYM_TOKENS = 5;
const MIN_FORBIDDEN_WORDS = 8;

function read(file) {
  return readFileSync(file, "utf8");
}

/** `export const NAME = ["a", "b"] as const;` -> `["a", "b"]` */
function readTsStringArray(source, name) {
  const match = new RegExp(
    `export const ${name}\\s*=\\s*\\[([^\\]]*)\\]`,
    "u",
  ).exec(source);
  assert.ok(match, `${name} TypeScript faylida topilmadi`);
  const values = [...match[1].matchAll(/"([^"]+)"/gu)].map((item) => item[1]);
  assert.ok(values.length > 0, `${name} BO'SH o'qildi — parser sinigan`);
  return values;
}

/**
 * `class X(StrEnum):` tanasidagi `NAME = "value"` qiymatlari.
 *
 * ⚠ SHAKLI `audit-actions.test.mjs:46-55` DAN NUSXA OLINDI va bu ataylab:
 *   umumiy yordamchi modul yozish uchala darvozani BITTA parserga bog'lardi
 *   va uning sinishi uchalasini birdan JIMGINA yashil qilardi.
 */
function readPythonEnumValues(source, className) {
  const start = source.indexOf(`class ${className}(StrEnum):`);
  assert.ok(start !== -1, `${className} enum'i topilmadi`);
  const rest = source.slice(start);
  const end = rest.indexOf("\nclass ");
  const body = end === -1 ? rest : rest.slice(0, end);
  const values = [...body.matchAll(/^ {4}[A-Z_]+ = "([^"]+)"/gmu)].map(
    (item) => item[1],
  );
  assert.ok(values.length > 0, `${className} enum'i BO'SH o'qildi`);
  return values;
}

function loadMessages(locale) {
  return JSON.parse(read(path.join(MESSAGES_DIR, `${locale}.json`)));
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

/** Bitta tildagi IKKALA namespace'ning yassilangan kalitlari. */
function scannedKeys(locale) {
  const messages = loadMessages(locale);
  const out = new Map();
  for (const namespace of SCANNED_NAMESPACES) {
    flatten(messages[namespace], namespace, out);
  }
  return out;
}

/** `"a.b.c"` kalitini ichma-ich obyektdan oladi. */
function lookup(tree, dottedKey) {
  return dottedKey
    .split(".")
    .reduce((node, part) => (node == null ? undefined : node[part]), tree);
}

/* ---------------------------------------------------------------------------
 * QAMROV CHEGARASI — hamma qolgan testning SHARTI.
 * ------------------------------------------------------------------------ */

test("QAMROV: har tilda kamida 60 kalit skanerlanadi", () => {
  /*
   * Usiz pastdagi taqiqlar BO'SH to'plam ustida aylanib, JIMGINA yashil
   * bo'lardi. Namespace nomi o'zgarsa (`collect` -> `cashier`) QIZARADI.
   */
  for (const locale of LOCALES) {
    const keys = scannedKeys(locale);
    assert.ok(
      keys.size >= MIN_SCANNED_KEYS,
      `${locale}.json: ${SCANNED_NAMESPACES.join("/")} dan atigi ${keys.size} ` +
        `kalit o'qildi (kutilgan >= ${MIN_SCANNED_KEYS}). Namespace nomi ` +
        "o'zgargan bo'lsa darvozalar hech nimani tekshirmasdi.",
    );
  }
});

test("QAMROV: skaner haqiqatan QIYMATLARNI o'qiydi (nazorat)", () => {
  const keys = scannedKeys("uz-Latn");
  const sample = keys.get("collect.pendingNotice");
  assert.equal(
    typeof sample,
    "string",
    "nazorat kaliti topilmadi — skaner maydoni siljigan bo'lishi mumkin",
  );
  assert.ok(sample.length > 10, "skaner qiymat o'rniga bo'sh satr o'qiyapti");
});

/* ---------------------------------------------------------------------------
 * G-24 — ⛔ SABAB-KODLARNING YOPIQLIGI VA NARXI (D-19)
 * ------------------------------------------------------------------------ */

/** Reyestr -> matn kalitining prefiksi. Ikkalasi ham `collect.*` da (§13.2). */
const REASON_REGISTRIES = [
  { registry: "ADJUSTMENT_REASONS", prefix: "collect.adjustmentReason" },
  { registry: "REVERSAL_REASONS", prefix: "collect.reversalReason" },
];

/** ⛔ Erkin matnni qaytarib keltiradigan a'zolar (D-19). */
const OPEN_ENDED_MEMBERS = ["other", "custom"];

test("G-24: sabab-kod reyestrlari BO'SH EMAS va ular AYNAN ikkita", () => {
  assert.equal(REASON_REGISTRIES.length, 2, "sabab-kod reyestrlari soni");
  for (const { registry } of REASON_REGISTRIES) {
    const codes = readTsStringArray(read(API_TYPES), registry);
    assert.ok(codes.length >= 4, `${registry} dan atigi ${codes.length} kod`);
  }
});

test("G-24: reyestrda `other`/`custom` YO'Q — erkin matn qaytib kelmadi", () => {
  /*
   * ⛔ Bu G-24 ning ENG MUHIM banди. `other` a'zosi hisobotda AMALDA eng
   *   katta guruh bo'lib qolardi va tuzatishlarning haqiqiy sababi hech
   *   qachon o'lchanmasdi — ya'ni D-19 hujjatdagi niyat bo'lib qolardi.
   */
  const problems = [];
  for (const { registry } of REASON_REGISTRIES) {
    for (const code of readTsStringArray(read(API_TYPES), registry)) {
      if (OPEN_ENDED_MEMBERS.includes(code)) {
        problems.push(`${registry}: ${code}`);
      }
    }
  }
  assert.deepEqual(
    problems,
    [],
    "yopiq ro'yxatga erkin-matn a'zosi kirdi (D-19, G-24):\n  " +
      problems.join("\n  "),
  );
});

test("G-24: har sabab-kod UCHALA locale'da — TO'PLAM TENGLIGI (D-31)", () => {
  /*
   * ⛔ `not.toContain` EMAS, `deepEqual`: ortiqcha kalit ham qizartiradi.
   *   05-14 sabotaj S7 o'lchagan — inkor tasdiq faqat AYNAN o'sha nomni
   *   ushlaydi va maydon qayta nomlansa o'tib ketardi.
   *
   * ⛔ SIKL REYESTRDAN boshlanadi, matn katalogidan EMAS (04-10 darsi):
   *   katalogdan boshlangan sikl to'plamning ICHKI izchilligini o'lchardi,
   *   TO'LIQLIGINI emas.
   */
  const problems = [];
  for (const { registry, prefix } of REASON_REGISTRIES) {
    const codes = [...readTsStringArray(read(API_TYPES), registry)].sort();
    for (const locale of LOCALES) {
      const node = lookup(loadMessages(locale), prefix);
      if (node == null || typeof node !== "object") {
        problems.push(`${locale}.json: ${prefix} bloki UMUMAN yo'q`);
        continue;
      }
      const actual = Object.keys(node).sort();
      if (JSON.stringify(actual) !== JSON.stringify(codes)) {
        problems.push(
          `${locale}.json: ${prefix} -> [${actual.join(", ")}], ` +
            `reyestr (${registry}) -> [${codes.join(", ")}]`,
        );
        continue;
      }
      for (const code of codes) {
        if (typeof node[code] !== "string" || node[code].trim() === "") {
          problems.push(`${locale}.json: ${prefix}.${code} BO'SH`);
        }
      }
    }
  }
  assert.deepEqual(
    problems,
    [],
    "sabab-kod ro'yxati matn katalogi bilan AJRALIB KETGAN (G-24):\n  " +
      problems.join("\n  "),
  );
});

/* ---------------------------------------------------------------------------
 * G-26 — ANOMALIYA TURLARI, AKRONIM VA TAQIQLANGAN SO'ZLAR
 * ------------------------------------------------------------------------ */

test("G-26: har anomaliya turi UCHALA locale'da — TO'PLAM TENGLIGI", () => {
  const kinds = [...readTsStringArray(read(API_TYPES), "ANOMALY_KINDS")].sort();
  assert.equal(kinds.length, 3, "uch `kind` — uch yorliq (C-12, BILL-04)");

  const problems = [];
  for (const locale of LOCALES) {
    const node = lookup(loadMessages(locale), "billing.anomalyKind");
    if (node == null || typeof node !== "object") {
      problems.push(`${locale}.json: billing.anomalyKind bloki UMUMAN yo'q`);
      continue;
    }
    const actual = Object.keys(node).sort();
    if (JSON.stringify(actual) !== JSON.stringify(kinds)) {
      problems.push(
        `${locale}.json: billing.anomalyKind -> [${actual.join(", ")}], ` +
          `ANOMALY_KINDS -> [${kinds.join(", ")}]`,
      );
    }
  }
  assert.deepEqual(
    problems,
    [],
    "anomaliya turlari matn katalogi bilan AJRALIB KETGAN (G-26):\n  " +
      problems.join("\n  "),
  );
});

/*
 * ⚠ `\b` BU YERDA ISHLATILMAYDI va bu 05-16 da O'LCHANGAN QAROR: JavaScript
 *   `\b` `[A-Za-z0-9_]` ga tayanadi (`u` bayrog'i buni O'ZGARTIRMAYDI), ya'ni
 *   kirill so'zining boshida chegara UMUMAN yo'q va naqsh HECH QACHON mos
 *   kelmasdi — darvoza jimgina yashil bo'lardi.
 */
const EMPTINESS_WORDS = [
  /bo['ʻʼ‘’]sh/iu,
  /бўш/iu,
  /бо['ʻʼ‘’]ш/iu,
  /свободн/iu,
];

function affirmsEmptiness(text) {
  return EMPTINESS_WORDS.some((pattern) => pattern.test(text));
}

test("G-26: NAZORAT — «bo'sh» detektori uchala alifboda ishlaydi", () => {
  assert.ok(affirmsEmptiness("Bu rasta bo'sh"));
  assert.ok(affirmsEmptiness("Бу раста бўш"));
  assert.ok(affirmsEmptiness("Место свободно"));
  // Salbiy nazorat: TO'G'RI matn ushlanMAsligi kerak.
  assert.ok(!affirmsEmptiness("Qamrovsiz rasta"));
  assert.ok(!affirmsEmptiness("Қамровсиз раста"));
  assert.ok(!affirmsEmptiness("Место вне зоны обзора"));
});

test("G-26: `no_coverage` yorlig'i «BO'SH» deb ATALMAYDI (D-05)", () => {
  /*
   * ⛔ Qamrov HOSILA: skaner maydoni kalit NOMIDAN chiqadi (`no_coverage`
   *   bo'lagi), qo'lda yozilgan kalit ro'yxatidan EMAS (D-32). Yangi
   *   `no_coverage_*` kaliti darvozaga O'ZI kiradi.
   */
  const matchedTotal = [];
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      if (!key.includes("no_coverage")) continue;
      matchedTotal.push(`${locale}:${key}`);
      if (affirmsEmptiness(value)) {
        problems.push(`${locale}.json: ${key} -> ${JSON.stringify(value)}`);
      }
    }
  }

  // Quyi chegara: kalit umuman topilmasa yuqoridagi sikl JIMGINA yashil.
  assert.ok(
    matchedTotal.length >= LOCALES.length,
    `\`no_coverage\` bo'lagi bo'lgan kalit topilmadi (${matchedTotal.length}) — ` +
      "G-26 bo'sh to'plam ustida ishlardi",
  );
  assert.deepEqual(
    problems,
    [],
    "qamrovsiz rasta «bo'sh» deb yozilgan (D-05, G-26):\n  " +
      problems.join("\n  ") +
      "\n  «Ko'ra olmadik» ≠ «bo'sh». Farq DB'da bor, lekin matnda yo'qolsa " +
      "hisobot jimgina noto'g'ri o'qilardi va buni HECH QANDAY sxema ushlamaydi.",
  );
});

/**
 * ⚠ REGISTRGA SEZGIR va SO'Z CHEGARALI (zone-copy G-11 naqshi).
 *
 *   [O'LCHANDI: 05-UI-SPEC M-5] `CV` -> `CВ` — bitta token IKKI ALIFBODA
 *   (lotin `C` U+0043 + kirill `В` U+0412). «Lotin qoldi» detektori bunga
 *   KO'R, chunki lotin harfi haqiqatan ham hali o'sha yerda turibdi.
 */
const FORBIDDEN_ACRONYMS = [
  /\bAI\b/u,
  /\bCV\b/u,
  /\bONNX\b/u,
  /RF-DETR/u,
  /\bJSON\b/u,
];

function acronymHits(text) {
  return FORBIDDEN_ACRONYMS.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

/**
 * §13.9 ning taqiqlangan so'zlari — ATAMA QARORLARINING mexanik shakli.
 *
 * ⚠ Oxirgi ikkitasi SO'ZGA emas, MA'NOGA qo'yilgan:
 *   * «hammasini to'lash» — §15.4: so'z copy'ga kirsa, keyingi ijrochi uni
 *     AMALGA OSHIRISHGA urinardi (2 va 3-fazada aynan shunday bo'lgan);
 *   * `to'g'rila*` / `исправить` — D-26: variance HECH QACHON
 *     to'g'rilanmaydi, so'z ekranda bo'lsa tugma ham talab qilinardi.
 *     ⚠ Naqsh `to'g'ri` ni EMAS, `to'g'rila` ni izlaydi: «Noto'g'ri summa»
 *     — QONUNIY storno sababi (§13.5) va uni qizartirish darvozani o'zi
 *     himoya qilayotgan matnga qarshi qo'yardi.
 */
const FORBIDDEN_WORDS = [
  /storno/iu,
  /сторно/iu,
  /variance/iu,
  /варианс/iu,
  /idempotent/iu,
  /идемпотент/iu,
  /proyeksiya/iu,
  /проекция/iu,
  /balans/iu,
  /баланс/iu,
  /hammasini\s+to['ʻʼ‘’]la/iu,
  /ҳаммасини\s+тўла/iu,
  /оплатить\s+вс[её]/iu,
  /to['ʻʼ‘’]g['ʻʼ‘’]rila/iu,
  /тўғрила/iu,
  /исправ/iu,
];

function forbiddenWordHits(text) {
  return FORBIDDEN_WORDS.filter((pattern) => pattern.test(text)).map(
    (pattern) => pattern.source,
  );
}

test("G-26: taqiq reyestrlari quyi chegaradan katta", () => {
  assert.ok(
    FORBIDDEN_ACRONYMS.length >= MIN_ACRONYM_TOKENS,
    `akronim reyestri ${FORBIDDEN_ACRONYMS.length} ta (kutilgan >= ${MIN_ACRONYM_TOKENS})`,
  );
  assert.ok(
    FORBIDDEN_WORDS.length >= MIN_FORBIDDEN_WORDS,
    `taqiqlangan so'z reyestri ${FORBIDDEN_WORDS.length} ta (kutilgan >= ${MIN_FORBIDDEN_WORDS})`,
  );
});

test("G-26: NAZORAT — detektorlar sun'iy ijobiy satrni USHLAYDI", () => {
  assert.ok(acronymHits("AI javobini ko'rsatadi").length > 0);
  assert.ok(acronymHits("CV xizmati kadrni o'qidi").length > 0);
  assert.ok(acronymHits("ONNX sessiyasi").length > 0);
  assert.ok(acronymHits("RF-DETR modeli").length > 0);
  assert.ok(acronymHits("JSON javobi").length > 0);

  assert.ok(forbiddenWordHits("Storno qilish").length > 0);
  assert.ok(forbiddenWordHits("Сторно платежа").length > 0);
  assert.ok(forbiddenWordHits("Variance: 12 000").length > 0);
  assert.ok(forbiddenWordHits("Idempotent so'rov").length > 0);
  assert.ok(forbiddenWordHits("Proyeksiya summasi").length > 0);
  assert.ok(forbiddenWordHits("Проекция суммы").length > 0);
  assert.ok(forbiddenWordHits("Balans: 0").length > 0);
  assert.ok(forbiddenWordHits("Баланс продавца").length > 0);
  assert.ok(forbiddenWordHits("Hammasini to'lash").length > 0);
  assert.ok(forbiddenWordHits("Ҳаммасини тўлаш").length > 0);
  assert.ok(forbiddenWordHits("Оплатить всё").length > 0);
  assert.ok(forbiddenWordHits("Farqni to'g'rilash").length > 0);
  assert.ok(forbiddenWordHits("Фарқни тўғрилаш").length > 0);
  assert.ok(forbiddenWordHits("Исправить разницу").length > 0);

  /*
   * ⛔ SALBIY NAZORAT — ENG MUHIMI. Bu satrlar EKRANDA BO'LISHI KERAK va
   *   detektor ularni qizartirsa, u himoya qilayotgan matnni O'ZI buzardi.
   */
  assert.deepEqual(acronymHits("Tizim summasi"), []);
  assert.deepEqual(acronymHits("Далил кадрлари"), []);
  assert.deepEqual(forbiddenWordHits("Noto'g'ri summa"), []);
  assert.deepEqual(forbiddenWordHits("Нотўғри раста"), []);
  assert.deepEqual(forbiddenWordHits("Qoldiq"), []);
  assert.deepEqual(forbiddenWordHits("Farq"), []);
  assert.deepEqual(forbiddenWordHits("Qayta yuborish dublikat yaratmaydi"), []);
  assert.deepEqual(forbiddenWordHits("Взять и долг"), []);
});

test("G-26: `collect.*` / `billing.*` da akronim va taqiqlangan so'z YO'Q", () => {
  const problems = [];
  for (const locale of LOCALES) {
    for (const [key, value] of scannedKeys(locale)) {
      for (const hit of acronymHits(value)) {
        problems.push(`${locale}.json: ${key} -> AKRONIM (${hit})`);
      }
      for (const hit of forbiddenWordHits(value)) {
        problems.push(`${locale}.json: ${key} -> TAQIQLANGAN SO'Z (${hit})`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ taqiqlangan atama copy'ga kirdi (§13.1/§13.9, G-26):\n  " +
      problems.join("\n  ") +
      "\n  Akronim transliteratsiyada buziladi (`CV` -> `CВ` — aralash " +
      "alifbo) VA foydalanuvchi uchun ma'no tashimaydi. Atamalar esa " +
      "§13.1 jadvalidagi ekran shakliga o'giriladi: «Bekor qilish», " +
      "«Farq», «Kutilayotgan», «Qoldiq».",
  );
});

/* ---------------------------------------------------------------------------
 * §5.10 — ⛔⛔ BACKEND <-> FRONTEND ENUM PARITY (TO'RT SOLISHTIRUV)
 * ------------------------------------------------------------------------ */

/** Python enum'i -> uning `api-types.ts` dagi `as const` ko'zgusi. */
const ENUM_MIRRORS = [
  { enumName: "AnomalyKind", mirror: "ANOMALY_KINDS" },
  { enumName: "AdjustmentReason", mirror: "ADJUSTMENT_REASONS" },
  { enumName: "ReversalReason", mirror: "REVERSAL_REASONS" },
  { enumName: "PaymentMethod", mirror: "PAYMENT_METHODS" },
];

test("§5.10 NAZORAT: to'rtala enum ham backenddan O'QILDI (parser tirik)", () => {
  /*
   * Bo'sh to'plam ustidagi `deepEqual([], [])` JIMGINA yashil bo'lardi —
   * ya'ni parser sinsa darvoza «hech qachon qizarmaydigan» holatga tushardi.
   */
  assert.equal(ENUM_MIRRORS.length, 4, "§5.10 AYNAN to'rt solishtiruv");
  const source = read(CORE_ENUMS);
  for (const { enumName } of ENUM_MIRRORS) {
    const values = readPythonEnumValues(source, enumName);
    assert.ok(values.length >= 2, `${enumName}: ${values.length} a'zo o'qildi`);
  }
});

test("§5.10: domen enumlari `api-types.ts` ko'zgusi bilan AYNAN mos", () => {
  const enumsSource = read(CORE_ENUMS);
  const typesSource = read(API_TYPES);

  const drift = [];
  for (const { enumName, mirror } of ENUM_MIRRORS) {
    const backend = [...readPythonEnumValues(enumsSource, enumName)].sort();
    const frontend = [...readTsStringArray(typesSource, mirror)].sort();

    const missing = backend.filter((item) => !frontend.includes(item));
    const extra = frontend.filter((item) => !backend.includes(item));
    if (missing.length > 0) {
      drift.push(`${mirror}: ko'zguda YO'Q -> ${missing.join(", ")}`);
    }
    if (extra.length > 0) {
      drift.push(`${mirror}: ko'zguda ORTIQCHA -> ${extra.join(", ")}`);
    }
  }

  assert.deepEqual(
    drift,
    [],
    "domen enum'i va uning frontend ko'zgusi AJRALIB KETGAN (§5.10):\n  " +
      drift.join("\n  ") +
      "\n  `packages/sbozor-core/sbozor_core/enums.py` va " +
      "`frontend/src/lib/api-types.ts` BIRGA o'zgaradi. Ko'zgusiz a'zo UI'da " +
      "UMUMAN chizilmaydi va hisobot jimgina to'liq bo'lmaydi.",
  );
});
