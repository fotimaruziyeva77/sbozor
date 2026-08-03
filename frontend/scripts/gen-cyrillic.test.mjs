import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, it, test } from "node:test";

import { generateCyrillic, transliterate } from "./gen-cyrillic.mjs";

const MESSAGES_DIR = path.join(import.meta.dirname, "..", "messages");

function readJson(name) {
  return JSON.parse(readFileSync(path.join(MESSAGES_DIR, name), "utf8"));
}

/*
 * HAQIQIY override fayli o'qiladi, sintetik lug'at EMAS.
 *
 * Sabab: bu bloklar `uz-Cyrl.overrides.json` ning SHU HOLATINI qulflaydi.
 * Sintetik lug'at bilan test "transliterator lug'atni qo'llay oladimi?"
 * degan savolga javob berardi (u allaqachon yuqorida tekshirilgan), bu
 * yerdagi savol esa boshqa: "yetkazilayotgan konfiguratsiya o'lchangan
 * to'rtta defektni yopadimi?".
 */
const OVERRIDE_WORDS = readJson("uz-Cyrl.overrides.json").words;

/** Lotin harfi qolib ketganini topadi — aralash yozuv defektining belgisi. */
function hasLatinLetters(text) {
  return /[A-Za-z]/u.test(text);
}

describe("transliterate — asosiy mapping", () => {
  it("bosh harf holatini saqlaydi", () => {
    assert.equal(transliterate("Rasta"), "Раста");
  });

  it("digraflarni bir harflilardan oldin qo'llaydi", () => {
    assert.equal(transliterate("shahar"), "шаҳар");
    assert.equal(transliterate("chorshanba"), "чоршанба");
    assert.equal(transliterate("g'isht"), "ғишт");
  });

  it("y-digraflarini ajratadi", () => {
    assert.equal(transliterate("yozuv"), "ёзув");
    assert.equal(transliterate("yuk"), "юк");
    assert.equal(transliterate("yangi"), "янги");
  });

  it("o'ziga xos undoshlarni to'g'ri beradi", () => {
    assert.equal(transliterate("qarz"), "қарз");
    assert.equal(transliterate("xato"), "хато");
    assert.equal(transliterate("hisob"), "ҳисоб");
  });
});

describe("transliterate — apostrof variantlari", () => {
  it("ASCII apostrofni ў ga aylantiradi", () => {
    assert.equal(transliterate("o'zbek"), "ўзбек");
  });

  it("U+02BB (ʻ) ni ASCII apostrof bilan bir xil ko'radi", () => {
    assert.equal(transliterate("oʻzbek"), "ўзбек");
  });

  it("U+2019 (’) ni ham bir xil ko'radi", () => {
    assert.equal(transliterate("o’zbek"), "ўзбек");
  });

  it("apostrofsiz o oddiy о bo'lib qoladi", () => {
    assert.equal(transliterate("ozbek"), "озбек");
  });

  it("qolgan apostrof tutuq belgisiga (ъ) aylanadi", () => {
    assert.equal(transliterate("ma'no"), "маъно");
  });

  it("apostrof-digraf `yo` dan kuchliroq bog'lanadi", () => {
    // `yo'q` = y + o' (ikkita harf), `yo` + ' EMAS.
    assert.equal(transliterate("yo'q"), "йўқ");
    assert.equal(transliterate("yo'l"), "йўл");
    assert.equal(transliterate("sho'r"), "шўр");
  });

  it("apostrofsiz `yo` odatdagidek ё beradi", () => {
    assert.equal(transliterate("yog'"), "ёғ");
    assert.equal(transliterate("yozuv"), "ёзув");
  });

  it("`ya` + apostrof tutuq belgisini saqlaydi", () => {
    assert.equal(transliterate("ya'ni"), "яъни");
  });
});

describe("transliterate — e / э noaniqligi", () => {
  it("so'z boshidagi e → э", () => {
    assert.equal(transliterate("Eslatma"), "Эслатма");
  });

  it("undoshdan keyingi e → е", () => {
    assert.equal(transliterate("kelmoq"), "келмоқ");
  });

  it("unlidan keyingi e → э", () => {
    assert.equal(transliterate("maest"), "маэст");
  });

  it("ye digrafi е beradi", () => {
    assert.equal(transliterate("yer"), "ер");
  });
});

describe("transliterate — ts faqat lug'at orqali ц bo'ladi", () => {
  it("o'zlashma so'z lug'atdan keladi", () => {
    assert.equal(
      transliterate("protsent", { protsent: "процент" }),
      "процент",
    );
  });

  it("lug'atsiz ts blanket tarzda ц ga AYLANMAYDI", () => {
    // "aytsa", "ketsin" kabi o'zbekcha shakllar cheksiz ochiq to'plam —
    // blanket `ts → ц` ularni buzadi. Qarang: SUMMARY, Rule 1 chetlanish.
    assert.equal(transliterate("aytsa"), "айтса");
    assert.equal(transliterate("ketsin"), "кетсин");
  });

  it("lug'at bosh harf shaklini ko'chiradi", () => {
    assert.equal(
      transliterate("Protsent", { protsent: "процент" }),
      "Процент",
    );
  });

  it("xos ism lug'at orqali lotincha qoladi", () => {
    assert.equal(transliterate("SBOZOR", { SBOZOR: "SBOZOR" }), "SBOZOR");
  });
});

describe("transliterate — ICU daxlsizligi (Pitfall 8)", () => {
  it("oddiy platsholderni o'zgartirmaydi", () => {
    assert.equal(
      transliterate("{name} tomonidan yaratildi"),
      "{name} томонидан яратилди",
    );
  });

  it("plural strukturasini saqlab, faqat branch matnini o'giradi", () => {
    assert.equal(
      transliterate("{count, plural, one {# yozuv} other {# yozuv}} topildi"),
      "{count, plural, one {# ёзув} other {# ёзув}} топилди",
    );
  });

  it("select branch nomlarini o'zgartirmaydi", () => {
    assert.equal(
      transliterate("{role, select, admin {boshqaruvchi} other {xodim}}"),
      "{role, select, admin {бошқарувчи} other {ходим}}",
    );
  });

  it("argument turini (number/date) o'zgartirmaydi", () => {
    assert.equal(
      transliterate("Jami: {total, number} so'm"),
      "Жами: {total, number} сўм",
    );
  });
});

describe("transliterate — daxlsiz segmentlar", () => {
  it("URL o'zgarmaydi", () => {
    assert.equal(transliterate("https://sbozor.uz"), "https://sbozor.uz");
  });

  it("matn ichidagi URL o'zgarmaydi", () => {
    assert.equal(
      transliterate("Sayt: https://sbozor.uz/yordam"),
      "Сайт: https://sbozor.uz/yordam",
    );
  });

  it("e-mail o'zgarmaydi", () => {
    assert.equal(
      transliterate("Pochta: admin@sbozor.uz"),
      "Почта: admin@sbozor.uz",
    );
  });

  it("HTML teglari o'zgarmaydi", () => {
    assert.equal(
      transliterate("<b>Rasta</b> band"),
      "<b>Раста</b> банд",
    );
  });
});

/*
 * =============================================================================
 * T-01…T-04 — O'LCHANGAN TRANSLITERATOR DEFEKTLARI (UI-SPEC §5.2).
 *
 * NEGA ALOHIDA DARVOZA KERAK: `npm run i18n:check` kalit-parity va
 * ICU-argument parity'ni tekshiradi, lekin transliteratsiya SIFATINI
 * umuman tekshirmaydi. Ya'ni bu defektlar qaytsa, mavjud darvozalarning
 * hech biri qizarmaydi va buzuq kirillcha matn jimgina yetkaziladi.
 *
 * Har test AYNAN bitta defektni qulflaydi va ikki tomonlama tasdiqlaydi:
 * to'g'ri natija BOR va buzuq natija YO'Q.
 * =============================================================================
 */
describe("transliterate — T-01…T-04 o'lchangan defektlar (haqiqiy overrides)", () => {
  test("T-01: `Excel` transliteratsiya qilinmaydi va aralash yozuv hosil bo'lmaydi", () => {
    const out = transliterate("Excel fayldan yuklash", OVERRIDE_WORDS);

    assert.equal(out, "Excel файлдан юклаш");
    assert.ok(out.includes("Excel"), "`Excel` lotin holida qolishi kerak");
    assert.ok(
      !out.includes("Эхcэл"),
      "buzuq `Эхcэл` (ichida lotin `c`) qaytib kelgan",
    );
  });

  test("T-02: `xlsx` fayl kengaytmasi transliteratsiya qilinmaydi", () => {
    const out = transliterate("xlsx fayl", OVERRIDE_WORDS);

    assert.equal(out, "xlsx файл");
    assert.ok(out.includes("xlsx"), "`xlsx` lotin holida qolishi kerak");
    assert.ok(!out.includes("хлсх"), "buzuq `хлсх` qaytib kelgan");
  });

  test("T-03: `filtr` ning qo'shimchali shakllari ham `фильтр` beradi", () => {
    const out = transliterate("Filtrga mos rasta topilmadi", OVERRIDE_WORDS);

    assert.equal(out, "Фильтрга мос раста топилмади");
    assert.ok(out.includes("Фильтрга"), "kutilgan `Фильтрга` yo'q");
    assert.ok(
      !out.includes("Филтрга"),
      "yumshatish belgisiz `Филтрга` qaytib kelgan",
    );

    // O'zbekcha agglyutinativ: har qo'shimchali shakl ALOHIDA yozuv.
    assert.equal(
      transliterate("Filtrni tozalash", OVERRIDE_WORDS),
      "Фильтрни тозалаш",
    );
    assert.equal(
      transliterate("filtrdan chiqarish", OVERRIDE_WORDS),
      "фильтрдан чиқариш",
    );
  });

  test("T-04: `Excel` gap o'rtasida ham buzilmaydi", () => {
    const out = transliterate("Excel qilib yuklab olish", OVERRIDE_WORDS);

    assert.equal(out, "Excel қилиб юклаб олиш");
    assert.ok(out.includes("Excel"), "`Excel` lotin holida qolishi kerak");
    assert.ok(!out.includes("Эхcэл"), "buzuq `Эхcэл` qaytib kelgan");
  });

  test("IJOBIY NAZORAT: ICU platsholderi transliteratsiyadan buzilmasdan o'tadi", () => {
    const out = transliterate(
      "{count, plural, one {# ta xato} other {# ta xato}}",
      OVERRIDE_WORDS,
    );

    assert.equal(out, "{count, plural, one {# та хато} other {# та хато}}");
    // Struktura: argument nomi, turi, branch nomlari va `#` daxlsiz.
    assert.ok(out.startsWith("{count, plural, one {# "));
    assert.ok(out.includes("other {# "));
    assert.equal((out.match(/#/gu) ?? []).length, 2);
  });
});

/*
 * COPY QOIDASI — bu test override YETARLI EMASLIGINI hujjatlashtiradi.
 *
 * `Excel'dan` override bilan ham buziladi, chunki apostrofli shakl boshqa
 * token. Yechim kodda emas, MATNDA: `Excel fayldan`. Shu sababli darvoza
 * transliteratorni emas, tarjima fayllarini tekshiradi.
 */
describe("copy qoidasi — `Excel` apostrofli qo'shimcha bilan yozilmaydi", () => {
  test("apostrofli shakl HAMON buziladi — qoidaning mavjudlik sababi", () => {
    const out = transliterate("Excel'dan yuklash", OVERRIDE_WORDS);

    assert.ok(
      out.includes("Эхcэлъдан"),
      "agar bu shakl tuzalgan bo'lsa, copy qoidasi va bu test qayta ko'rib chiqilsin",
    );
  });

  for (const file of ["uz-Latn.json", "ru.json"]) {
    test(`${file} da apostrofli \`Excel'\` yoki \`.xlsx\` shakli yo'q`, () => {
      const raw = readFileSync(path.join(MESSAGES_DIR, file), "utf8");

      assert.ok(
        !/Excel['ʻʼ‘’]/u.test(raw),
        `${file}: \`Excel'…\` topildi — o'rniga \`Excel fayldan\` yozing (README Qoida 1)`,
      );
      assert.ok(
        !/\.xlsx/u.test(raw),
        `${file}: \`.xlsx\` topildi — o'rniga \`xlsx fayl\` yozing (README Qoida 1)`,
      );
    });
  }
});

/*
 * =============================================================================
 * G-5 — 3-FAZANING O'LCHANGAN TRANSLITERATSIYA HOLATLARI (UI-SPEC §11.7).
 *
 * Beshta holat `03-UI-SPEC.md` §0.2 da 53 ta nomzod matn ustida O'LCHANGAN
 * (M-1/M-2/M-10) va shu yerda kutilgan chiqishi bilan qulflanadi.
 *
 * ⚠ BU ASSERTION'LAR TAQIQNI EMAS, KUTILGAN CHIQISHNI YOZADI. Ya'ni
 *   transliterator yaxshilanganda (masalan `ts -> ц` qoidasi aniqroq
 *   bo'lganda) ular YANGILANADI va bu NORMAL. Ularning vazifasi —
 *   bugungi natijani tasodifiy o'zgarishdan saqlash, kelajakni
 *   muzlatib qo'yish emas.
 *
 * ⚠ HAQIQIY override fayli o'qiladi (yuqoridagi bloklar bilan bir xil
 *   sabab): savol "transliterator lug'atni qo'llay oladimi?" emas,
 *   "YETKAZILAYOTGAN konfiguratsiya shu beshta holatni yopadimi?".
 * =============================================================================
 */
describe("transliterate — G-5: 3-fazaning o'lchangan holatlari", () => {
  test("T-05: akronim + qo'shimchali so'z (`NVR qurilmasiga`)", () => {
    assert.equal(
      transliterate("NVR qurilmasiga ulanib bo'lmadi", OVERRIDE_WORDS),
      "NVR қурилмасига уланиб бўлмади",
    );
  });

  test("T-06: akronim gap o'rtasida (`NTP xizmatini`)", () => {
    assert.equal(
      transliterate("NTP xizmatini yoqing", OVERRIDE_WORDS),
      "NTP хизматини ёқинг",
    );
  });

  test("T-07: aralash registrli brend nomi (`WireGuard`)", () => {
    // Overridesiz natija `WиреГуард` edi — lotin va kirill ARALASHGAN
    // holda, ya'ni o'qib bo'lmaydigan shakl (§0.2 (1)).
    assert.equal(
      transliterate("WireGuard tunneli yoqilganini tekshiring", OVERRIDE_WORDS),
      "WireGuard туннели ёқилганини текширинг",
    );
  });

  test("T-08: kichik harfli texnik atama juftligi (`digest/basic`)", () => {
    // Overridesiz `дигест/басиc` chiqardi — oxirgi `c` LOTIN bo'lib
    // qolardi, chunki `c` o'zbek lotin alifbosida yakka harf emas.
    assert.equal(
      transliterate(
        "autentifikatsiya rejimini digest/basic qilib belgilang",
        OVERRIDE_WORDS,
      ),
      "аутентификация режимини digest/basic қилиб белгиланг",
    );
  });

  test("T-09: `ts` birikmali o'zlashma (`autentifikatsiyasini`)", () => {
    /*
     * SEMANTIK DEFEKT (§11.7 Qoida 2): overridesiz chiqish
     * `аутентификатсиясини` bo'ladi — u SOF KIRILL, ya'ni "lotin harfi
     * qolmagan" darvozasi uni KO'RMAYDI. To'g'ri shakl `ц` bilan va u
     * faqat lug'at orqali keladi.
     */
    assert.equal(
      transliterate(
        "digest autentifikatsiyasini qabul qilmayapti",
        OVERRIDE_WORDS,
      ),
      "digest аутентификациясини қабул қилмаяпти",
    );
  });
});

/*
 * COPY QOIDALARI — override YETARLI EMASLIGINI hujjatlashtiradi (§11.7).
 *
 * Ikkalasi ham `Excel'dan` qoidasining aynan davomi: yechim KODDA emas,
 * MATNDA. Shuning uchun darvoza transliteratorni emas, tarjima
 * fayllarini tekshiradi.
 */
describe("copy qoidasi — akronim va IANA identifikatori", () => {
  test("Qoida 1: apostrofli shakl HAMON buziladi — qoidaning mavjudlik sababi", () => {
    assert.equal(
      transliterate("NVR'ga ulanmadi", OVERRIDE_WORDS),
      "НВРъга уланмади",
    );
    assert.equal(
      transliterate("NTP'ni yoqing", OVERRIDE_WORDS),
      "НТПъни ёқинг",
    );
  });

  test("Qoida 2: IANA identifikatori buziladi, `Toshkent` esa to'g'ri chiqadi", () => {
    // Chiqish SOF KIRILL va shuning uchun skript tekshiruvidan O'TIB
    // KETADI — aynan shu sababdan qoida COPY darajasida yashaydi.
    assert.equal(transliterate("Asia/Tashkent", OVERRIDE_WORDS), "Асиа/Ташкент");
    assert.ok(!/[A-Za-z]/u.test(transliterate("Asia/Tashkent", OVERRIDE_WORDS)));

    assert.equal(transliterate("Toshkent", OVERRIDE_WORDS), "Тошкент");
  });

  for (const file of ["uz-Latn.json", "ru.json"]) {
    test(`${file} da akronimga apostrofli qo'shimcha ulanmagan`, () => {
      const raw = readFileSync(path.join(MESSAGES_DIR, file), "utf8");

      for (const acronym of ["NVR", "NTP", "RTSP", "ISAPI", "VPN", "GMT"]) {
        assert.ok(
          !new RegExp(`${acronym}['ʻʼ‘’]`, "u").test(raw),
          `${file}: \`${acronym}'…\` topildi — o'rniga \`${acronym} qurilmasiga\` / \`${acronym} xizmatini\` shaklini yozing (README Qoida 1)`,
        );
      }
    });

    test(`${file} da IANA vaqt mintaqasi identifikatori yo'q`, () => {
      const raw = readFileSync(path.join(MESSAGES_DIR, file), "utf8");

      assert.ok(
        !/Asia\//u.test(raw),
        `${file}: \`Asia/…\` topildi — o'rniga shahar nomini yozing (\`Toshkent\`), README Qoida 5`,
      );
    });
  }
});

/*
 * Hosil qilingan `uz-Cyrl.json` ning O'ZI tekshiriladi: yuqoridagi
 * testlar sof funksiyani qulflaydi, bu esa YETKAZILAYOTGAN faylni.
 */
describe("uz-Cyrl.json — yetkazilayotgan fayl toza", () => {
  test("buzuq transliteratsiya izlari yo'q", () => {
    const raw = readFileSync(path.join(MESSAGES_DIR, "uz-Cyrl.json"), "utf8");

    /*
     * Ro'yxat ikki avloddan iborat va ikkalasi ham O'LCHANGAN:
     *
     *   2-faza (T-01…T-04): `Эхcэл`, `хлсх`, `Филтр` — override
     *     yetishmasligi yoki lug'atdan tushib qolish.
     *
     *   3-faza (UI-SPEC §11.7): akronimning kirillga o'girilishi
     *     (`НВР`/`РТСП`/`НТП`), apostrofli qo'shimchaning tutuq
     *     belgisiga aylanishi (`ъга`/`ъни`), IANA identifikatorining
     *     buzilishi (`Асиа`) va `ts` birikmasining `тс` bo'lib
     *     qolishi (`аутентификатсия`).
     *
     * ⚠ OXIRGI IKKITASI SEMANTIK: chiqishda na lotin harfi, na `ъ` bor,
     *   ya'ni pastdagi "lotin harfi qolmagan" testi ularni KO'RMAYDI.
     *   Ular faqat shu ro'yxat orqali ushlanadi.
     */
    const broken = [
      "Эхcэл",
      "хлсх",
      "Филтр",
      "филтр",
      "НВР",
      "РТСП",
      "НТП",
      "ъга",
      "ъни",
      "Асиа",
      "аутентификатсия",
    ];

    for (const form of broken) {
      assert.ok(
        !raw.includes(form),
        `uz-Cyrl.json ichida buzuq shakl topildi: ${form}`,
      );
    }
  });

  test("lug'atdagi lotin so'zlardan tashqari lotin harfi qolmagan", () => {
    const tree = readJson("uz-Cyrl.json");
    // Lug'at ATAYIN lotin holida qoldiradigan so'zlar.
    //
    // ⚠ `csv` 02-24 da qo'shildi va sababi `xlsx` bilan AYNAN bir xil:
    // fayl formatining nomi harfma-harf o'girilganda (`цсв`) tanib
    // bo'lmas holga kelardi. Ro'yxat `uz-Cyrl.overrides.json` -> `words`
    // bilan JUFT yuritiladi — biri yangilanib, ikkinchisi unutilsa
    // AYNAN shu test qizaradi.
    //
    // ⚠ 3-FAZA: NVR domenining atamalari qo'shildi (UI-SPEC §11.7
    // Qoida 3). Akronimlar KIRILLGA O'GIRILMAYDI, chunki admin bu
    // satrni NVR qurilmasining O'Z interfeysi bilan solishtiradi va u
    // yerda ular lotin yozuvida turadi; `НВР` yangi, hech qayerda
    // uchramaydigan atama tug'dirardi. `\b` chegaralari ATAYIN: 2-faza
    // yozuvlari chegarasiz va ular so'z ICHIDA ham mos kelib, darvozani
    // sekin bo'shatib borardi.
    const allowed =
      /SBOZOR|Excel|xlsx|CSV|csv|https?:\/\/\S+|[\w.%+-]+@[\w.-]+|\b(?:Hikvision|WireGuard|WebRTC|ISAPI|RTSP|HLS|MSE|NVR|NTP|VPN|GMT|IP)\b|\b(?:firmware|digest|basic|https|http)\b/gu;

    const walk = (node, prefix) => {
      for (const [key, value] of Object.entries(node)) {
        const full = prefix ? `${prefix}.${key}` : key;
        if (value && typeof value === "object") {
          walk(value, full);
        } else if (typeof value === "string") {
          // ICU struktura qismlari ham lotin — ular olib tashlanadi.
          const stripped = value
            .replace(/\{[^{}]*,\s*(plural|select|selectordinal)\s*,/gu, "")
            .replace(/\{[^{}]*\}/gu, "")
            .replace(/\b(one|other|few|many|zero)\b/gu, "")
            .replace(allowed, "");
          assert.ok(
            !hasLatinLetters(stripped),
            `${full}: kutilmagan lotin harfi qoldi -> ${JSON.stringify(value)}`,
          );
        }
      }
    };

    walk(tree, "");
  });
});

describe("generateCyrillic — fayl darajasidagi generatsiya", () => {
  const source = {
    common: { appName: "SBOZOR", save: "Saqlash" },
    audit: {
      resultCount: "{count, plural, one {# yozuv} other {# yozuv}} topildi",
    },
  };

  it("kalit daraxtini aynan saqlaydi", () => {
    const out = generateCyrillic(source, { messages: {}, words: {} });
    assert.deepEqual(Object.keys(out), ["common", "audit"]);
    assert.deepEqual(Object.keys(out.common), ["appName", "save"]);
  });

  it("words lug'atini qo'llaydi", () => {
    const out = generateCyrillic(source, {
      messages: {},
      words: { SBOZOR: "SBOZOR" },
    });
    assert.equal(out.common.appName, "SBOZOR");
    assert.equal(out.common.save, "Сақлаш");
  });

  it("messages lug'ati butun xabarni almashtiradi (eng yuqori ustuvorlik)", () => {
    const out = generateCyrillic(source, {
      messages: { "common.save": "ҚЎЛДА ЁЗILGAN" },
      words: {},
    });
    assert.equal(out.common.save, "ҚЎЛДА ЁЗILGAN");
  });

  it("ICU platsholderlarini fayl darajasida ham buzmaydi", () => {
    const out = generateCyrillic(source, { messages: {}, words: {} });
    assert.match(out.audit.resultCount, /^\{count, plural, one \{# /);
    assert.ok(out.audit.resultCount.includes("#"));
  });
});
