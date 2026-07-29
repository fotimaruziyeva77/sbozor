import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { generateCyrillic, transliterate } from "./gen-cyrillic.mjs";

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
