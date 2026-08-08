#!/usr/bin/env node
/**
 * `02-VALIDATION.md` ning `nyquist_compliant` bayrog'i YOLG'ON GAPIRA
 * OLMASLIGINI mexanik ravishda majburlaydi.
 *
 * NEGA KERAK. Bayroqning butun qiymati uning HISOB-KITOB ekanida, kelishuv
 * emasligida. Ikkala yo'nalish ham zararli va ikkalasi ham jimgina sodir
 * bo'ladi:
 *
 *   `true` erta qo'yilsa  — isbotlanmagan shart «isbotlangan» bo'lib
 *                           ko'rinadi va keyingi faza uning ustiga quriladi;
 *   `false` abadiy qolsa  — bayroq ma'nosini yo'qotadi va hech kim uni
 *                           o'qimay qo'yadi.
 *
 * Shuning uchun bu skript bayroqqa qiymat BUYURMAYDI — u QOIDANI
 * majburlaydi va faylning o'zi aytgan qiymat hisob-kitobga mos
 * kelmasa exit 1 beradi.
 *
 * QOIDA. `nyquist_compliant: true` AGAR VA FAQAT AGAR:
 *
 *   (1) «Per-Task Verification Map» ning har bir ma'lumot qatorida
 *       `Automated Command` ustuni BO'SH EMAS va `Status` ustuni YASHIL;
 *   (2) faylda `BAJARILMADI` so'zi QOLMAGAN — ya'ni har bir qo'lda
 *       bajariladigan band yo avtomatlashtirilgan, yo `human_only_
 *       verifications` ga KO'CHIRILGAN;
 *   (3) frontmatter'da `human_only_verifications` ro'yxati bor, BO'SH
 *       EMAS, va har elementida to'rtala kalit to'ldirilgan:
 *       `item`, `why_not_automatable`, `owner`, `trigger`;
 *   (4) frontmatter'da `automated_replacements` ro'yxati bor va har
 *       elementida `was` hamda `now` (ISHLAYDIGAN buyruq) yozilgan.
 *
 * ⚠ (3) NING MA'NOSI: «avtomatlashtirib bo'lmaydi» degan da'vo HECH
 * QACHON BEPUL EMAS. U har doim ISM (`owner`) va SHART (`trigger`)
 * talab qiladi — aks holda band «keyinroq» degan bo'sh iborada
 * yo'qoladi va keyingi tekshiruv uni umuman ko'rmaydi (T-02-170).
 *
 * NIMA TEKSHIRILMAYDI VA NEGA: bandlarning MAZMUNI. Skript `owner`
 * ning haqiqiy odam ekanini ham, `now` dagi buyruqning yashil o'tishini
 * ham bila olmaydi — buni faqat odam yoki darvoza buyrug'ining o'zi
 * ayta oladi. Skriptning vazifasi torroq va shuning uchun ishonchli:
 * SHAKL to'liqligini majburlash.
 *
 * `check-requirements-sync.mjs` (02-22) uslubida: `node:` modullaridan
 * boshqa bog'liqlik YO'Q.
 *
 * Ishlatish:  node scripts/check-validation-signoff.mjs [fayl]
 * Chiqish:    0 — bayroq hisob-kitobga mos; 1 — mos emas (AYNAN qaysi
 *             qoida buzilgani stderr'da).
 */
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const PHASES_DIR = path.join(import.meta.dirname, "..", ".planning", "phases");

/**
 * ⛔ D-27 — MEROS BAND, 4-FAZADAN QOLGAN.
 *
 * Bu yerda ilgari `02-bozor-domeni-va-yangi-bozor-ustasi/02-VALIDATION.md`
 * QADALGAN edi. Nosozlik jimgina ishlaydi va aynan shuning uchun u ikki
 * faza davomida sezilmadi: argumentsiz chaqiruv (`npm run validation:check`)
 * HAR DOIM 2-fazani tekshirardi va YASHIL qaytardi. Ya'ni 3, 4 va 5-fazalar
 * uchun darvoza mavjud bo'lib KO'RINARDI, lekin ularning birorta qatorini
 * ham o'qimasdi.
 *
 * Tuzatish yo'nalishi (§3.11): `.planning/phases/` skanerlanadi va ENG
 * KATTA RAQAMLI fazadagi `*-VALIDATION.md` olinadi.
 *
 * ⚠ TAQQOSLASH SON BO'YICHA, MATN BO'YICHA EMAS. Leksikografik tartibda
 *   `10-...` `9-...` dan KICHIK bo'lardi, `02.1-...` esa `02-...` dan
 *   oldin turardi. O'nlik faza raqami (`02.1`) shu loyihada real
 *   ehtimol, shuning uchun `parseFloat` ishlatiladi.
 *
 * ⚠ «TOPILMADI = YIQILISH» (§S-10): faza katalogi yo'q bo'lsa yoki
 *   birorta `*-VALIDATION.md` topilmasa — `exit 1`. Jimgina o'tib ketish
 *   aynan yuqoridagi nosozlikning takrori bo'lardi.
 */
function resolveLatestValidationFile() {
  let entries;
  try {
    entries = readdirSync(PHASES_DIR, { withFileTypes: true });
  } catch {
    return { error: `faza katalogi o'qilmadi: ${PHASES_DIR}` };
  }

  const phases = [];
  const withoutValidation = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const match = /^(\d+(?:\.\d+)?)-/u.exec(entry.name);
    if (!match) continue;

    const number = Number.parseFloat(match[1]);
    if (!Number.isFinite(number)) continue;

    const dir = path.join(PHASES_DIR, entry.name);
    const found = readdirSync(dir)
      .filter((name) => name.endsWith("-VALIDATION.md"))
      .sort();

    if (found.length === 0) {
      withoutValidation.push({ number, name: entry.name });
      continue;
    }
    phases.push({ number, name: entry.name, file: path.join(dir, found.at(-1)) });
  }

  if (phases.length === 0) {
    return {
      error:
        `${PHASES_DIR} da birorta \`*-VALIDATION.md\` topilmadi ` +
        `(${entries.length} yozuv ko'rildi)`,
    };
  }

  phases.sort((a, b) => b.number - a.number);
  const chosen = phases[0];

  /*
   * ⚠ HUJJATSIZ FAZA JIMGINA O'TKAZIB YUBORILMAYDI. Yangi faza katalogi
   *   yaratilib, `*-VALIDATION.md` hali yozilmagan bo'lsa skript ESKI
   *   fazani tekshirardi va natija «yashil» ko'rinardi — bu aynan D-27
   *   nosozligining yangi shakli. Shuning uchun ogohlantirish stderr'ga
   *   chiqadi (chiqish kodi o'zgarmaydi: hujjat hali yozilmagani
   *   XATO emas).
   */
  const newerWithout = withoutValidation.filter((item) => item.number > chosen.number);

  return { file: chosen.file, phase: chosen.name, skipped: newerWithout };
}

const FLAG = "nyquist_compliant";
const HUMAN_KEY = "human_only_verifications";
const REPLACEMENT_KEY = "automated_replacements";
const OPEN_MARKER = "BAJARILMADI";
const MAP_HEADING = "## Per-Task Verification Map";

const HUMAN_FIELDS = ["item", "why_not_automatable", "owner", "trigger"];
const REPLACEMENT_FIELDS = ["was", "now"];

/** `key: value` — frontmatter'ning yagona qabul qilinadigan shakli. */
const PAIR_RE = /^(\s*)([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/u;
/** `- ...` — ro'yxat elementi. */
const ITEM_RE = /^(\s*)-\s+(.*)$/u;

/** `"matn"` yoki `'matn'` -> `matn`. */
function unquote(raw) {
  const value = raw.trim();
  if (value.length >= 2) {
    const first = value[0];
    const last = value[value.length - 1];
    if ((first === '"' && last === '"') || (first === "'" && last === "'")) {
      return value.slice(1, -1);
    }
  }
  return value;
}

/**
 * Frontmatter'ni YAML'ning ATAYIN TOR qism to'plamida o'qiydi:
 * skalyar `key: value`, satrlar ro'yxati va `- key: value` shaklidagi
 * mappinglar ro'yxati.
 *
 * To'liq YAML parseri QO'SHILMAYDI (bu tashqi bog'liqlik bo'lardi va
 * 02-22 uslubini buzardi). Tor to'plam esa hujjatning shaklini ham
 * barqaror ushlab turadi: qo'llanmaydigan konstruksiya yozilsa skript
 * uni `null` deb ko'radi va qoida buzilgani sifatida chiqadi — ya'ni
 * jimgina o'tib ketmaydi.
 */
function parseFrontmatter(source) {
  const lines = source.split(/\r?\n/u);
  if (lines[0] !== "---") return null;
  const end = lines.indexOf("---", 1);
  if (end === -1) return null;

  const body = lines.slice(1, end);
  const result = {};
  let index = 0;

  while (index < body.length) {
    const line = body[index];
    if (line.trim() === "" || line.trimStart().startsWith("#")) {
      index += 1;
      continue;
    }

    const pair = PAIR_RE.exec(line);
    if (!pair || pair[1] !== "") {
      index += 1;
      continue;
    }

    const [, , key, rawValue] = pair;
    if (rawValue.trim() !== "") {
      result[key] = unquote(rawValue);
      index += 1;
      continue;
    }

    // Blok ro'yxat: keyingi chekingan qatorlar shu kalitga tegishli.
    const block = [];
    index += 1;
    while (index < body.length && (body[index].trim() === "" || /^\s/u.test(body[index]))) {
      block.push(body[index]);
      index += 1;
    }
    result[key] = parseList(block);
  }

  return result;
}

/** Blok satrlarini ro'yxatga aylantiradi (satr yoki mapping elementlari). */
function parseList(block) {
  const entries = [];
  let current = null;

  for (const line of block) {
    if (line.trim() === "") continue;

    const item = ITEM_RE.exec(line);
    if (item) {
      const rest = item[2];
      const pair = PAIR_RE.exec(rest);
      if (pair && pair[1] === "") {
        current = { [pair[2]]: unquote(pair[3]) };
        entries.push(current);
      } else {
        current = null;
        entries.push(unquote(rest));
      }
      continue;
    }

    const pair = PAIR_RE.exec(line);
    if (pair && current !== null && typeof current === "object") {
      current[pair[2]] = unquote(pair[3]);
    }
  }

  return entries;
}

/** `## Per-Task Verification Map` bo'limining jadval qatorlari. */
function taskRows(source) {
  const lines = source.split(/\r?\n/u);
  const start = lines.findIndex((line) => line.trim() === MAP_HEADING);
  if (start === -1) return null;

  const rows = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.startsWith("## ")) break;
    if (!line.trimStart().startsWith("|")) continue;

    const cells = line
      .trim()
      .replace(/^\|/u, "")
      .replace(/\|$/u, "")
      .split("|")
      .map((cell) => cell.trim());

    if (cells.length < 10) continue;
    if (cells[0] === "Task ID") continue;
    if (/^:?-{3,}:?$/u.test(cells[0])) continue;

    rows.push({ id: cells[0], command: cells[7], status: cells[9], lineNo: index + 1 });
  }

  return rows;
}

/** Ustun to'ldirilganmi? `—` va `-` BO'SH deb sanaladi. */
function filled(cell) {
  const value = cell.replaceAll("`", "").trim();
  return value !== "" && value !== "—" && value !== "-" && value !== "n/a";
}

function check(file) {
  const source = readFileSync(file, "utf8");
  const front = parseFrontmatter(source);
  const problems = [];

  if (front === null) {
    return { fatal: `${file}: frontmatter (\`---\` bloki) topilmadi` };
  }

  const declaredRaw = front[FLAG];
  if (declaredRaw !== "true" && declaredRaw !== "false") {
    return {
      fatal:
        `${FLAG} frontmatter'da yo'q yoki qiymati \`true\`/\`false\` emas ` +
        `(o'qilgani: ${JSON.stringify(declaredRaw ?? null)})`,
    };
  }
  const declared = declaredRaw === "true";

  // --- (1) Per-Task Verification Map
  const rows = taskRows(source);
  if (rows === null) {
    return { fatal: `\`${MAP_HEADING}\` bo'limi topilmadi` };
  }
  if (rows.length === 0) {
    problems.push("(1) «Per-Task Verification Map» da birorta ma'lumot qatori yo'q");
  }
  for (const row of rows) {
    if (!filled(row.command)) {
      problems.push(
        `(1) ${row.id}: \`Automated Command\` ustuni BO'SH (${row.lineNo}-qator)`,
      );
    }
    if (!row.status.includes("✅")) {
      problems.push(
        `(1) ${row.id}: \`Status\` yashil emas — "${row.status}" (${row.lineNo}-qator)`,
      );
    }
  }

  // --- (2) ochiq bandlar
  const openLines = source
    .split(/\r?\n/u)
    .map((line, index) => ({ line, lineNo: index + 1 }))
    .filter((entry) => entry.line.includes(OPEN_MARKER));
  for (const entry of openLines) {
    problems.push(`(2) \`${OPEN_MARKER}\` hamon faylda (${entry.lineNo}-qator)`);
  }

  // --- (3) inson tekshiruvlari
  const humans = front[HUMAN_KEY];
  if (!Array.isArray(humans) || humans.length === 0) {
    problems.push(
      `(3) \`${HUMAN_KEY}\` frontmatter'da yo'q yoki BO'SH — ` +
        "«hammasi avtomatlashtirilgan» degan da'vo alohida isbot talab qiladi",
    );
  } else {
    humans.forEach((entry, index) => {
      const label =
        typeof entry === "object" && entry !== null && typeof entry.item === "string"
          ? entry.item
          : `#${index + 1}`;
      if (typeof entry !== "object" || entry === null) {
        problems.push(`(3) ${HUMAN_KEY}[${index + 1}]: element mapping emas`);
        return;
      }
      for (const field of HUMAN_FIELDS) {
        if (typeof entry[field] !== "string" || entry[field].trim() === "") {
          problems.push(
            `(3) ${HUMAN_KEY} «${label}»: \`${field}\` yo'q yoki bo'sh — ` +
              "«avtomatlashtirib bo'lmaydi» da'vosi ism va shart talab qiladi",
          );
        }
      }
    });
  }

  // --- (4) avtomatlashtirilgan almashtirishlar
  const replacements = front[REPLACEMENT_KEY];
  if (!Array.isArray(replacements) || replacements.length === 0) {
    problems.push(`(4) \`${REPLACEMENT_KEY}\` frontmatter'da yo'q yoki BO'SH`);
  } else {
    replacements.forEach((entry, index) => {
      if (typeof entry !== "object" || entry === null) {
        problems.push(`(4) ${REPLACEMENT_KEY}[${index + 1}]: element mapping emas`);
        return;
      }
      const label = typeof entry.was === "string" ? entry.was : `#${index + 1}`;
      for (const field of REPLACEMENT_FIELDS) {
        if (typeof entry[field] !== "string" || entry[field].trim() === "") {
          problems.push(`(4) ${REPLACEMENT_KEY} «${label}»: \`${field}\` yo'q yoki bo'sh`);
        }
      }
    });
  }

  const computed = problems.length === 0;
  return {
    declared,
    computed,
    problems,
    rows: rows.length,
    humans: Array.isArray(humans) ? humans.length : 0,
    file,
  };
}

/*
 * Argument berilgan holat O'ZGARMAYDI — u ataylab eng ustuvor yo'l:
 * darvoza buyrug'i aniq faylni ko'rsatib chaqirilishi mumkin.
 */
let file;
if (process.argv[2]) {
  file = path.resolve(process.argv[2]);
} else {
  const resolved = resolveLatestValidationFile();
  if (resolved.error) {
    process.stderr.write(`check-validation-signoff: ${resolved.error}\n`);
    process.exit(1);
  }
  file = resolved.file;
  for (const item of resolved.skipped) {
    process.stderr.write(
      `check-validation-signoff: OGOHLANTIRISH — \`${item.name}\` fazasida ` +
        "`*-VALIDATION.md` YO'Q, shuning uchun u tekshirilmadi\n",
    );
  }
}

/*
 * ⛔ TANLANGAN FAYL BIRINCHI SATRDA CHOP ETILADI.
 *
 * Usiz «qaysi fayl tekshirildi?» savoli javobsiz qolardi va darvozaning
 * TO'G'RI faylni tanlaganini tashqaridan o'lchab bo'lmasdi — ya'ni D-27
 * nosozligi tuzatilgandan keyin ham ko'rinmas bo'lib qolaverardi.
 */
process.stdout.write(`check-validation-signoff: fayl — ${file}\n`);

const outcome = check(file);

if (outcome.fatal) {
  process.stderr.write(`check-validation-signoff: ${outcome.fatal}\n`);
  process.exit(1);
}

const { declared, computed, problems, rows, humans } = outcome;

if (declared !== computed) {
  process.stderr.write(
    `check-validation-signoff: \`${FLAG}: ${declared}\` HISOB-KITOBGA MOS EMAS ` +
      `(hisoblangani: ${computed}) — ${file}\n`,
  );
  if (problems.length > 0) {
    process.stderr.write(`  ${problems.length} ta qoida buzilishi:\n`);
    for (const problem of problems) {
      process.stderr.write(`  ✗ ${problem}\n`);
    }
  } else {
    process.stderr.write(
      "  Birorta qoida buzilmadi, ya'ni bayroq `true` bo'lishi kerak edi.\n" +
        "  `false` ni SAQLAB QOLISH uchun sabab `open_items` da nomlanishi va\n" +
        "  qoidalardan biri haqiqatan bajarilmasligi kerak.\n",
    );
  }
  process.exit(1);
}

/*
 * Bayroq `false` bo'lgan holat ham MUVAFFAQIYAT: qoida buzilgan va fayl
 * buni ochiq aytgan. Skript baribir sabablarni bosadi — «nima yopilishi
 * kerak?» savoliga javob hujjatni qayta o'qimasdan olinadi.
 */
process.stdout.write(
  `check-validation-signoff: ${FLAG}: ${declared} — hisob-kitob bilan MOS.\n` +
    `  Per-Task qatorlari: ${rows} · inson bandlari: ${humans}\n`,
);

if (!computed) {
  process.stdout.write(`  Ochiq qoidalar (${problems.length}):\n`);
  for (const problem of problems) {
    process.stdout.write(`  · ${problem}\n`);
  }
}
