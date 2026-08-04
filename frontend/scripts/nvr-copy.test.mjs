#!/usr/bin/env node
/**
 * MAHSULOT QOIDALARINING MATN DARVOZASI — G-3, G-4, G-6.
 *
 * 3-fazaning uchta qat'iy qoidasi FAQAT MATN orqali yashaydi va aynan
 * shuning uchun ular eng oson jimgina buziladi: matnni o'zgartirish
 * typecheck'ni ham, lint'ni ham, birorta komponent testini ham
 * qizartirmaydi.
 *
 *   G-3 (D-05)  «Ehtimol» — o'n ikki koddan FAQAT bittasida. Hedging
 *               arzonlashsa ma'nosini yo'qotadi va admin har xabarga
 *               shubha bilan qaraydi.
 *
 *   G-4 (D-10)  Kamera yuzasida «o'chirish» FE'LI yo'q. Qattiq `DELETE`
 *               backendда UMUMAN yo'q (marshrut ham yozilmagan), lekin
 *               so'z bir marta matnga kirsa u tarjima orqali tarqaladi
 *               va admin arxivlashni o'chirish deb tushunadi.
 *
 *   G-6 (D-11)  Frontend go2rtc'ning HTTP API'siga hech qanday so'rov
 *               yubormaydi. `PUT /api/streams?src=exec:<buyruq>`
 *               konteynerda ixtiyoriy buyruq bajaradi
 *               (GHSA-wwww-5h25-jf98, CVSS 9.1).
 *
 * =============================================================================
 * ⚠ BU FAYL O'Z QOIDASINI O'ZI BUZMAYDI — VA BU TASODIF EMAS.
 *
 *   Darvoza `frontend/scripts/` da yashaydi, G-6 esa `frontend/src`
 *   daraxtini skanerlaydi. Ya'ni quyidagi `FORBIDDEN_GO2RTC_TOKENS`
 *   massivi o'z izlash satrlarini olib yuradi, LEKIN skanerlanadigan
 *   to'plamdan TASHQARIDA.
 *
 *   Bu 2-fazada UCH MARTA takrorlangan sinfdagi xato (`grep` kodni
 *   izohdan ajratmaydi) va 3-fazada u TESKARI yo'nalishda ham uchradi
 *   (`compose.yaml` izohi o'z taqig'ini tushuntirib, darvozani
 *   qizartirdi). Umumiy qoida: DARVOZA TANLAGAN MATN SINFINI OCHIQ
 *   BELGILASHI KERAK. Shu sababdan har uch tekshiruvda chegara aniq
 *   yozilgan.
 * =============================================================================
 */
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const MESSAGES_DIR = path.join(FRONTEND_ROOT, "messages");
const SRC_DIR = path.join(FRONTEND_ROOT, "src");
const CAMERA_COMPONENTS_DIR = path.join(SRC_DIR, "components", "cameras");

const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

/** Quyi chegaralar — bo'sh to'plam ustidagi sikl yashil bo'lmasin. */
const MIN_CAMERA_KEYS = 60;
const MIN_SCANNED_SOURCE_FILES = 1;

function loadMessages(locale) {
  return JSON.parse(
    readFileSync(path.join(MESSAGES_DIR, `${locale}.json`), "utf8"),
  );
}

/** `cameras` namespace'ini `kalit -> qiymat` juftliklariga yassilaydi. */
function flattenCameras(tree, prefix = "cameras", out = new Map()) {
  for (const [key, value] of Object.entries(tree ?? {})) {
    const full = `${prefix}.${key}`;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flattenCameras(value, full, out);
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
    return []; // Katalog hali yaratilmagan (yuzalar 03-10 da keladi).
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

/* ---------------------------------------------------------------------------
 * G-3 — HEDGING YAGONALIGI (D-05, UI-SPEC §7.5)
 * ------------------------------------------------------------------------ */

/**
 * Har tildagi hedge so'zi.
 *
 * `uz-Cyrl` qiymati HOSILA (`npm run i18n:gen`) va u shu yerda ham
 * yozilgan: transliterator `Ehtimol` -> `Эҳтимол` beradi va bu
 * `gen-cyrillic.test.mjs` da alohida qulflangan.
 */
const HEDGE_WORD = {
  "uz-Latn": "Ehtimol",
  "uz-Cyrl": "Эҳтимол",
  ru: "Возможно",
};

/*
 * =============================================================================
 * ⛔ W0-F7 — DARVOZA IKKI XATO REYESTRI USTIDA UMUMLASHTIRILDI (4-faza).
 *
 * O'LCHANGAN FAKT (2026-08-04) va u `04-UI-SPEC.md` W0-F7 ning tavsifidan
 * FARQ QILADI — farq shu yerda ochiq yoziladi.
 *
 * UI-SPEC shunday deydi: 4-faza `snapshots.errorCause.capture_stream_limit`
 * ni aynan o'sha hedge so'zi bilan qo'shganda «darvoza birinchi kunning
 * o'zida QIZARADI».
 *
 * U QIZARMAYDI. Darvozaning ikkala testi ham `cameras.errorCause` ni
 * QATTIQ QADAGAN edi (`loadMessages(locale).cameras?.errorCause`), ya'ni
 * `snapshots.*` ni umuman KO'RMASDI. Haqiqiy xavf — qizil darvoza emas,
 * **JIM QAMROVSIZLIK**: 4-fazaning xato reyestrida hedging invarianti
 * hech qachon o'lchanmagan bo'lib qolardi va uni HECH BIR test
 * oshkor qilmasdi.
 *
 * Shuning uchun darvoza «tuzatilmadi» — u UMUMLASHTIRILDI:
 *   * `HEDGED_NAMESPACES` — skanerlanadigan reyestrlar ro'yxati,
 *   * `HEDGED_KEYS`       — to'liq kalitli allowlist (namespace bilan).
 *
 * ⛔ HEDGING ARZONLASHSA, MA'NOSINI YO'QOTADI. 23 ta xato kodidan faqat
 *    IKKITASI hedged va ikkalasi ham AYNAN BIR XIL fizik hodisani
 *    tasvirlaydi: NVR sessiya chegarasiga yetish — bu HEURISTIKA,
 *    qurilma javobidan tasdiqlanmaydi (A.5 ning LOW ishonchi).
 *    Uchinchi kalit qo'shilsa, darvoza qayta ko'rib chiqilishi SHART.
 * =============================================================================
 */

/** Hedging invarianti qo'llanadigan xato reyestrlari. */
const HEDGED_NAMESPACES = ["cameras", "snapshots"];

/**
 * Hedge so'zi RUXSAT ETILGAN kalitlar — TO'LIQ nom bilan.
 *
 * ⚠ To'liq nom (namespace bilan) ATAYIN: qisqa kod (`nvr_stream_limit`)
 *   bilan yozilgan allowlist ikki namespace'da bir xil nomli kod paydo
 *   bo'lganda ikkalasini ham jimgina oqlab yuborardi.
 */
const HEDGED_KEYS = new Set([
  "cameras.errorCause.nvr_stream_limit",
  "snapshots.errorCause.capture_stream_limit",
]);

/** `{namespace}.errorCause` — mavjud bo'lsa, aks holda bo'sh obyekt. */
function errorCauses(locale, namespace) {
  return loadMessages(locale)[namespace]?.errorCause ?? {};
}

test("G-3: `HEDGED_KEYS` dagi MAVJUD har bir kalit hedge so'zi bilan BOSHLANADI", () => {
  const checked = [];

  for (const locale of LOCALES) {
    for (const namespace of HEDGED_NAMESPACES) {
      const causes = errorCauses(locale, namespace);
      for (const code of Object.keys(causes)) {
        const full = `${namespace}.errorCause.${code}`;
        if (!HEDGED_KEYS.has(full)) continue;

        assert.ok(
          causes[code].startsWith(HEDGE_WORD[locale]),
          `${locale}.json: ${full} «${HEDGE_WORD[locale]}» bilan boshlanishi SHART ` +
            `(D-05). Hozirgi boshi: ${JSON.stringify(causes[code].slice(0, 40))}`,
        );
        checked.push(`${locale}:${full}`);
      }
    }
  }

  // QUYI CHEGARA: `cameras` kaliti UCHALA tilda ham mavjud bo'lishi SHART
  // (u 3-fazada yetkazilgan). `snapshots` kaliti hali yo'q — u qo'shilgan
  // kunning o'zida bu sikl uni AVTOMATIK qamrab oladi.
  const cameraChecks = checked.filter((item) => item.includes("cameras.")).length;
  assert.equal(
    cameraChecks,
    LOCALES.length,
    `cameras.errorCause.nvr_stream_limit uchala tilda ham tekshirilishi kerak edi, ` +
      `tekshirilgani: ${cameraChecks} (${checked.join(", ")})`,
  );

  const snapshotChecks = checked.filter((item) => item.includes("snapshots.")).length;
  if (snapshotChecks === 0) {
    console.log(
      "[G-3] `snapshots.errorCause.capture_stream_limit` hali yo'q (copy 04-08…04-10 da " +
        "keladi) — allowlist uni OLDINDAN biladi, ya'ni kalit qo'shilgan kuni " +
        "darvoza uni avtomatik qamrab oladi va yolg'on-qizil BERMAYDI.",
    );
  }
});

test("G-3: `HEDGED_KEYS` dan tashqari HECH BIR `errorCause.*` hedge so'zini ishlatmaydi", () => {
  /*
   * ⚠ TEKSHIRUV FAQAT `{namespace}.errorCause.*` USTIDA ishlaydi va bu
   *   chegara O'LCHANGAN, taxmin emas: `cameras.errorFix.
   *   nvr_isapi_unavailable` ning ruscha matni «Возможно, введён адрес
   *   камеры или роутера» deydi va u TO'G'RI — u sababni emas,
   *   TUZATISH yo'lidagi ehtimolni bildiradi. `cameras.runTimeout` va
   *   `cameras.liveNotFound` da ham shunday.
   *
   *   Darvozani butun `cameras.*` ga kengaytirish uni o'sha uchta
   *   to'g'ri satr ustida qizartirardi — ya'ni keyingi ishlovchi
   *   darvozani "chetlab o'tishga" majbur bo'lardi. D-05 ning qoidasi
   *   SABAB matni haqida va tekshiruv ham aynan shu yerda turadi.
   *
   * ⚠ 4-FAZA (W0-F7): sikl endi IKKALA namespace ustidan yuradi.
   *   `cameras` uchun quyi chegara (>= 12) SAQLANADI; `snapshots` uchun
   *   u SHARTLI, chunki copy `04-08…04-10` da keladi.
   */
  for (const locale of LOCALES) {
    const word = HEDGE_WORD[locale].toLowerCase();
    const offenders = [];

    for (const namespace of HEDGED_NAMESPACES) {
      const causes = errorCauses(locale, namespace);
      const codes = Object.keys(causes);

      if (namespace === "cameras") {
        assert.ok(
          codes.length >= 12,
          `${locale}.json: cameras.errorCause da atigi ${codes.length} kod bor`,
        );
      }

      for (const code of codes) {
        const full = `${namespace}.errorCause.${code}`;
        if (!HEDGED_KEYS.has(full) && causes[code].toLowerCase().includes(word)) {
          offenders.push(full);
        }
      }
    }

    assert.deepEqual(
      offenders,
      [],
      `${locale}.json: hedge so'zi («${HEDGE_WORD[locale]}») allowlist'dan tashqari ` +
        `kodlarda ham ishlatilgan: ${offenders.join(", ")}. Hedging arzonlashsa ` +
        "ma'nosini yo'qotadi (UI-SPEC §7.5) — bu kodlar ANIQ gapirishi kerak.",
    );
  }
});

/* ---------------------------------------------------------------------------
 * G-4 — «O'CHIRISH» FE'LINING TAQIG'I (D-10, UI-SPEC §9.1)
 * ------------------------------------------------------------------------ */

/**
 * Taqiqlangan AMAL FE'LLARI — UI-SPEC §9.1 jadvalidan AYNAN.
 *
 * ⚠ CHEGARA ANIQ: qidiruv BUYRUQ SHAKLI ustida (`o'chirish` /
 *   `удалить` / `delete`), o'zak ustida EMAS.
 *
 *   Sabab o'lchangan: `cameras.archiveBody` ning o'zi «Kamera va uning
 *   tarixi o'chirilmaydi» deydi (ru: «не удаляются») — bu taqiqning
 *   AYNAN TESKARISI va u matnda BO'LISHI kerak, chunki admin nima
 *   saqlanishini bilishi shart. O'zak bo'yicha qidiruv (`o'chir`,
 *   `удал`) shu satrni qizartirardi va darvoza o'z himoya qilayotgan
 *   matnini o'zi taqiqlagan bo'lardi.
 *
 *   Apostrof variantlari (`'`, `ʻ`, `ʼ`, `'`, `’`) qamraladi — matn
 *   fayllarida uchalasi ham uchraydi.
 *
 * ⚠ CHAP SO'Z CHEGARASI (`\b`) MAJBURIY — 03-09 da O'LCHANGAN.
 *   Usiz naqsh `ko'chirish` («ko'chirmoq», «nusxa ko'chirish») ni ham
 *   ushlaydi, chunki u `o'chirish` ni SO'Z ICHIDA topadi. Bu D-10 ga
 *   umuman aloqasi yo'q, kundalik o'zbekcha fe'l va u izohda ham,
 *   matnda ham muqarrar uchraydi. Chegarasiz darvoza keyingi
 *   ishlovchini uni «chetlab o'tishga» majbur qilardi — bu esa G-4 ning
 *   o'z docstringi ogohlantirgan sinf (darvoza o'zi himoya qilayotgan
 *   matn ustida qizaradi).
 *
 *   Chegara HECH NARSANI BO'SHASHTIRMAYDI: u faqat `o'chirish` dan
 *   OLDIN so'z belgisi turgan hollarni chiqarib tashlaydi, ya'ni
 *   BOSHQA so'zning oxirini. Buyruq fe'lining o'zi («Kamerani
 *   o'chirish», «O'chirish») baribir ushlanadi va bu quyidagi ijobiy
 *   VA salbiy nazorat testida qulflangan.
 */
const FORBIDDEN_DELETE_VERBS = [
  /\bo['ʻʼ‘’]chirish/iu,
  /удалить/iu,
  /\bdelete\b/iu,
];

/** Matnda taqiqlangan fe'l bormi. */
function hasDeleteVerb(text) {
  return FORBIDDEN_DELETE_VERBS.some((pattern) => pattern.test(text));
}

test("G-4: matcher AYNAN buyruq shaklini ushlaydi (nazorat)", () => {
  // Ijobiy nazorat: darvoza haqiqatan bir narsani ushlaydi.
  assert.ok(hasDeleteVerb("Kamerani o'chirish"));
  assert.ok(hasDeleteVerb("Kamerani o‘chirish"));
  assert.ok(hasDeleteVerb("Удалить камеру"));
  assert.ok(hasDeleteVerb("Delete camera"));

  // Salbiy nazorat: chegara. Bular MATNDA BO'LISHI kerak.
  assert.ok(!hasDeleteVerb("Kamera va uning tarixi o'chirilmaydi"));
  assert.ok(!hasDeleteVerb("Камера и её история не удаляются"));
  assert.ok(!hasDeleteVerb("onDelete"));
  assert.ok(!hasDeleteVerb("useDeleteZone"));

  /*
   * CHAP CHEGARANING salbiy nazorati (03-09 da o'lchandi): `ko'chirish`
   * — «ko'chirmoq», D-10 ga aloqasi yo'q. Chegarasiz naqsh uni ushlab,
   * darvozani `nvr-form.tsx` ning izohi ustida qizartirgan edi.
   */
  assert.ok(!hasDeleteVerb("Fokus parol maydoniga ko'chirish"));
  assert.ok(!hasDeleteVerb("nusxa ko'chirish"));
  assert.ok(!hasDeleteVerb("Ko'chirish"));

  // …lekin buyruq fe'lining O'ZI baribir ushlanadi.
  assert.ok(hasDeleteVerb("O'chirish"));
  assert.ok(hasDeleteVerb("«O'chirish» tugmasi"));
});

test("G-4: `cameras.*` QIYMATLARIDA «o'chirish» fe'li yo'q", () => {
  for (const locale of LOCALES) {
    const entries = flattenCameras(loadMessages(locale).cameras);

    assert.ok(
      entries.size >= MIN_CAMERA_KEYS,
      `${locale}.json: cameras namespace'ida atigi ${entries.size} kalit bor ` +
        `(kutilgan >= ${MIN_CAMERA_KEYS}) — darvoza bo'sh to'plamni skanerlayapti`,
    );

    for (const [key, value] of entries) {
      assert.ok(
        !hasDeleteVerb(value),
        `${locale}.json: "${key}" da taqiqlangan fe'l bor (D-10). ` +
          `Fe'l «Arxivlash» / «Архивировать» bo'lishi SHART. Matn: ${JSON.stringify(value)}`,
      );
    }
  }
});

test("G-4: kamera komponentlarining KO'RINADIGAN matnida ham yo'q", () => {
  /*
   * ⚠ CHEGARA: bu tekshiruv KOD IDENTIFIKATORLARINI qamramaydi.
   *   `onDelete`, `handleDelete`, `useDeleteZone` — ularda `\bdelete\b`
   *   uchun so'z chegarasi YO'Q (`e` va `D` ikkalasi ham so'z belgisi),
   *   ya'ni ular jimgina o'tadi va bu ATAYIN: qoida foydalanuvchi
   *   KO'RADIGAN fe'l haqida, o'zgaruvchi nomi haqida emas.
   *
   * Katalog 03-10 da yaratiladi; hozir u yo'q va tekshiruv bo'sh
   * to'plam ustida ishlaydi — shuning uchun quyi chegara BU YERDA
   * QO'YILMAYDI (u yuqoridagi matn testida).
   */
  for (const file of walkFiles(CAMERA_COMPONENTS_DIR, [".ts", ".tsx"])) {
    const source = readFileSync(file, "utf8");
    assert.ok(
      !hasDeleteVerb(source),
      `${path.relative(FRONTEND_ROOT, file)}: taqiqlangan fe'l topildi (D-10)`,
    );
  }
});

/* ---------------------------------------------------------------------------
 * G-6 — go2rtc YUZASINING TAQIG'I (D-11, UI-SPEC §8.7)
 * ------------------------------------------------------------------------ */

/**
 * Frontend kodida BO'LMASLIGI shart bo'lgan satrlar.
 *
 * `/api/streams` — go2rtc ning oqim boshqaruvi (RCE yuzasi);
 * `exec:` / `ffmpeg:` — o'sha API qabul qiladigan manba sxemalari.
 *
 * ⚠ RO'YXAT SHU FAYLDA YASHAYDI va shu fayl `frontend/scripts/` da —
 *   skanerlanadigan `frontend/src` daraxtidan TASHQARIDA. Ya'ni
 *   darvoza o'z izlash satrlarini o'zi TOPMAYDI.
 */
const FORBIDDEN_GO2RTC_TOKENS = ["/api/streams", "exec:", "ffmpeg:"];

test("G-6: `frontend/src` da go2rtc API yuzasining izlari yo'q", () => {
  const files = walkFiles(SRC_DIR, [".ts", ".tsx"]);

  assert.ok(
    files.length >= MIN_SCANNED_SOURCE_FILES,
    `frontend/src da atigi ${files.length} fayl skanerlandi — yo'l noto'g'ri bo'lishi mumkin`,
  );

  const hits = [];
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    for (const token of FORBIDDEN_GO2RTC_TOKENS) {
      if (source.includes(token)) {
        hits.push(`${path.relative(FRONTEND_ROOT, file)}: ${token}`);
      }
    }
  }

  assert.deepEqual(
    hits,
    [],
    "go2rtc ning HTTP yuzasi frontend kodiga kirib qoldi (D-11).\n" +
      `  ${hits.join("\n  ")}\n` +
      "  Jonli ko'rish YAGONA yo'li: `POST /cameras/{id}/live-token` -> opaque `url`.",
  );
});

test("G-6: skaner haqiqatan fayl mazmunini o'qiydi (nazorat)", () => {
  /*
   * Usiz yuqoridagi test `walkFiles` bo'sh massiv qaytarganda ham
   * yashil bo'lardi (quyi chegara buni ushlaydi), yoki `readFileSync`
   * bo'sh satr bergan taqdirda ham — bu esa chegaradan o'tib ketardi.
   */
  const files = walkFiles(SRC_DIR, [".ts", ".tsx"]);
  const known = files.find((file) => file.endsWith("camera-queries.ts"));

  assert.ok(known, "camera-queries.ts skanerlangan to'plamda topilmadi");
  assert.ok(
    readFileSync(known, "utf8").includes("live-token"),
    "skaner fayl mazmunini o'qimayapti — yuqoridagi darvoza ma'nosiz",
  );
});
