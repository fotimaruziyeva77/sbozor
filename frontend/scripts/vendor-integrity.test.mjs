#!/usr/bin/env node
/**
 * G-7 — VENDORED UCHINCHI TOMON KODINING YAXLITLIGI (UI-SPEC §14.2).
 *
 * NEGA BU DARVOZA MAVJUD: 3-fazada BIRINCHI marta uchinchi tomon kodi
 * bizning bundlga kiradi (go2rtc pleyeri). U foydalanuvchining sessiyasi
 * ICHIDA, bizning originimizda ishlaydi — ya'ni jimgina almashtirilgan
 * fayl access tokenni o'qib, uni istalgan joyga yubora oladi.
 *
 * Odatdagi himoya — shadcn registry darvozasi — bu loyihada QO'LLANMAYDI:
 * `components.json` yo'q va shadcn init ATAYIN bajarilmagan (UI-SPEC §1.3).
 * Shuning uchun unga EKVIVALENT darvoza qo'yiladi: yozib qo'yilgan
 * SHA-256 + har CI'da qayta hisoblash.
 *
 * ⚠ DARVOZA "FAYL BORMI?" DEGAN SAVOLGA JAVOB BERMAYDI, U "FAYL O'SHAMI?"
 *   DEGANIGA JAVOB BERADI. Shu sababdan uchta ALOHIDA da'vo bor:
 *
 *     1. har `.js` faylning `.sha256` jufti BOR (yangi fayl xeshsiz
 *        kirib kela olmaydi — aks holda darvoza yangi kodni umuman
 *        ko'rmasdi);
 *     2. hisoblangan xesh yozilganiga TENG;
 *     3. katalog BO'SH EMAS (quyi chegara) — bo'sh to'plam ustidagi
 *        sikl hech nimani tekshirmasdan yashil bo'lardi.
 *
 * ⚠ FAYLLAR TAHRIRLANMAYDI. Lint ham ularga tegmaydi
 *   (`eslint.config.mjs` -> `public/vendor/**`): har formatlash xeshni
 *   o'zgartirib, uni upstream tegi bilan solishtirib bo'lmaydigan holga
 *   keltirardi. Yangilash — faqat CLAUDE.md dagi versiya o'zgarganda va
 *   ALOHIDA PR bilan (UI-SPEC §14.2).
 */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const VENDOR_DIR = path.join(FRONTEND_ROOT, "public", "vendor", "go2rtc");

/** Vendored artefaktlar shu tegdan olinadi — `master` QABUL QILINMAYDI. */
const PINNED_TAG = "v1.9.14";

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

/** `<xesh>  <fayl>` qatoridan xeshni oladi (`sha256sum` formati). */
function readRecordedHash(file) {
  const line = readFileSync(file, "utf8").trim();
  const [hash] = line.split(/\s+/u);
  assert.match(
    hash ?? "",
    /^[0-9a-f]{64}$/u,
    `${path.basename(file)}: SHA-256 qatori o'qilmadi (kutilgan format: "<64 hex>  <fayl>")`,
  );
  return hash;
}

const jsFiles = readdirSync(VENDOR_DIR).filter((name) => name.endsWith(".js"));

test("vendored katalog BO'SH EMAS (quyi chegara)", () => {
  // Nazorat: fayllar o'chirilsa yoki yo'l o'zgarsa quyidagi sikl
  // hech nimani tekshirmasdan yashil qolardi.
  assert.ok(
    jsFiles.length >= 2,
    `public/vendor/go2rtc/ da atigi ${jsFiles.length} ta .js fayl topildi — ` +
      "kutilgan: video-stream.js VA uning bog'liqligi video-rtc.js",
  );
});

test("har `.js` faylning SHA-256 jufti bor va u MOS", () => {
  for (const name of jsFiles) {
    const filePath = path.join(VENDOR_DIR, name);
    const hashPath = `${filePath}.sha256`;

    let recorded;
    try {
      recorded = readRecordedHash(hashPath);
    } catch (error) {
      assert.fail(
        `${name}: \`${name}.sha256\` yo'q yoki o'qilmadi. Uchinchi tomon fayli ` +
          `XESHSIZ repozitoriyaga kira olmaydi (UI-SPEC §14.2). ${String(error)}`,
      );
    }

    const actual = sha256(readFileSync(filePath));

    assert.equal(
      actual,
      recorded,
      `${name}: SHA-256 MOS EMAS.\n` +
        `  yozilgan:    ${recorded}\n` +
        `  hisoblangan: ${actual}\n` +
        `  Fayl o'zgargan. Agar bu ATAYIN yangilash bo'lsa: diffni to'liq o'qing, ` +
        `\`sha256sum ${name} > ${name}.sha256\` bajaring va UI-SPEC §14.2 jadvaliga ` +
        "yangi qatorni yozing (alohida PR).",
    );
  }
});

test("`video-stream.js` bog'liqligi HAM vendored (D-11)", () => {
  const stream = readFileSync(path.join(VENDOR_DIR, "video-stream.js"), "utf8");

  /*
   * Fayl `import ... from './video-rtc.js'` bilan boshlanadi. Agar
   * bog'liqlik yonida bo'lmasa, brauzer uni topolmaydi va keyingi
   * "tuzatish" uni go2rtc'dan yuklashga (`/live/video-rtc.js`) olib
   * kelardi — bu D-11 ning butun chegarasini ochib yuborardi.
   */
  const imports = [...stream.matchAll(/from\s+['"](\.\/[^'"]+)['"]/gu)].map(
    (match) => match[1].replace("./", ""),
  );

  assert.ok(imports.length > 0, "import topilmadi — fayl kutilgan shaklda emas");

  for (const dependency of imports) {
    assert.ok(
      jsFiles.includes(dependency),
      `\`${dependency}\` vendored EMAS. Uni runtime'da go2rtc'dan yuklash ` +
        "TAQIQLANADI (D-11 / UI-SPEC §8.7) — faylni shu katalogga nusxalang " +
        "va `.sha256` ini yozing.",
    );
  }
});

test("MIT litsenziya matni yonida turadi", () => {
  /*
   * ⚠ LITSENZIYA ALOHIDA FAYLDA, `.js` NING ICHIDA EMAS.
   *
   *   Upstream `www/video-stream.js` va `www/video-rtc.js` fayllarining
   *   boshida litsenziya izohi YO'Q (o'lchandi: v1.9.14). Ularga izoh
   *   QO'SHISH faylni upstream nusxasidan farqli qilardi va yuqoridagi
   *   xesh endi `AlexxIT/go2rtc` tegi bilan solishtirib bo'lmasdi —
   *   ya'ni darvozaning eng qimmatli xususiyati yo'qolardi.
   *
   *   MIT ning talabi (litsenziya va mualliflik xabari tarqatmada
   *   bo'lishi) `LICENSE` fayli bilan bajariladi.
   */
  const license = readFileSync(path.join(VENDOR_DIR, "LICENSE"), "utf8");

  assert.match(license, /MIT License/u, "LICENSE faylida MIT matni yo'q");
  assert.match(license, /Copyright \(c\)/u, "mualliflik xabari yo'q");
});

test("provenans yozuvi qulflangan tegga ishora qiladi", () => {
  const readme = readFileSync(path.join(VENDOR_DIR, "README.md"), "utf8");

  assert.ok(
    readme.includes(PINNED_TAG),
    `README.md da qulflangan teg (${PINNED_TAG}) ko'rsatilmagan — ` +
      "manbasi noma'lum artefakt ko'rikdan o'ta olmaydi",
  );
  assert.ok(
    !/\bmaster\b/u.test(readme),
    "README.md `master` ga ishora qilyapti — UI-SPEC §14.2 faqat TEGni qabul qiladi",
  );
});
