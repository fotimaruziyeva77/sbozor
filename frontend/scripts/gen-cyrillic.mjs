#!/usr/bin/env node
/**
 * uz-Latn → uz-Cyrl build-time transliteratsiya (D-14).
 *
 *   node scripts/gen-cyrillic.mjs            # messages/uz-Cyrl.json ni yozadi
 *   node scripts/gen-cyrillic.mjs --check    # drift bo'lsa exit 1 (CI darvozasi)
 *
 * Tashqi npm paketiga bog'liq EMAS — faqat `node:fs` va `node:path`.
 * Tayyor kutubxonalar (`UzTransliterator`, `uzbek-latin-cyrillic-converter`,
 * `cyrillic-to-translit-js`) 2022 dan beri yangilanmagan va ruscha-yo'naltirilgan.
 */
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";

const MESSAGES_DIR = path.join(import.meta.dirname, "..", "messages");
const SOURCE_FILE = path.join(MESSAGES_DIR, "uz-Latn.json");
const OVERRIDES_FILE = path.join(MESSAGES_DIR, "uz-Cyrl.overrides.json");
const TARGET_FILE = path.join(MESSAGES_DIR, "uz-Cyrl.json");

/* -------------------------------------------------------------------------- */
/* Mapping                                                                     */
/* -------------------------------------------------------------------------- */

/** Apostrof variantlari — hammasi ASCII `'` ga keltiriladi. */
const APOSTROPHE_VARIANTS = /[ʻʼ‘’]/g;

/**
 * TARTIB KRITIK: uzun digraflar avval.
 *
 * `o'` va `g'` `yo`/`ya` dan OLDIN turishi shart — aks holda "yo'q"
 * `yo` bo'yicha bo'linib "ёъқ" bo'lib ketadi (to'g'risi "йўқ").
 */
const DIGRAPHS = [
  ["o'", "ў"],
  ["g'", "ғ"],
  ["sh", "ш"],
  ["ch", "ч"],
  ["yo", "ё"],
  ["yu", "ю"],
  ["ya", "я"],
  ["ye", "е"],
];

/** Unli bilan tugaydigan digraflar — keyingi `e` qoidasi uchun kerak. */
const VOWEL_DIGRAPHS = new Set(["o'", "yo", "yu", "ya", "ye"]);

/**
 * Apostrof bilan digraf hosil qila oladigan harflar (`o'` → ў, `g'` → ғ).
 *
 * Apostrof-digraf boshqa har qanday digrafdan KUCHLIROQ bog'lanadi, chunki
 * `o'` — o'zbek lotin alifbosining alohida HARFI. Busiz "yo'q" `yo` + `'`
 * bo'yicha bo'linib "ёъқ" chiqadi; to'g'risi `y` + `o'` = "йўқ".
 */
const APOSTROPHE_DIGRAPH_HEADS = new Set(["o", "g"]);

const SINGLES = new Map(
  Object.entries({
    a: "а",
    b: "б",
    d: "д",
    f: "ф",
    g: "г",
    h: "ҳ",
    i: "и",
    j: "ж",
    k: "к",
    l: "л",
    m: "м",
    n: "н",
    o: "о",
    p: "п",
    q: "қ",
    r: "р",
    s: "с",
    t: "т",
    u: "у",
    v: "в",
    x: "х",
    y: "й",
    z: "з",
    "'": "ъ", // tutuq belgisi (digraflardan keyin qolgan apostrof)
  }),
);

const LATIN_VOWELS = new Set(["a", "e", "i", "o", "u"]);

/*
 * DIQQAT — `ts → ц` ATAYIN blanket qoida QILINMAGAN.
 *
 * O'zbekchada `-tsa` / `-tsin` qo'shimchalari cheksiz ochiq to'plam hosil
 * qiladi ("aytsa", "ketsin", "sotsa"). Blanket qoida ularni "айца", "кецин"
 * ga aylantirib buzadi. `ц` talab qiladigan o'zlashmalar esa YOPIQ, sanab
 * chiqiladigan to'plam — shuning uchun ular `uz-Cyrl.overrides.json` ning
 * `words` bo'limida turadi.
 */

/* -------------------------------------------------------------------------- */
/* Harf darajasidagi transliteratsiya                                          */
/* -------------------------------------------------------------------------- */

function normalizeApostrophes(text) {
  return text.replace(APOSTROPHE_VARIANTS, "'");
}

function isUpper(ch) {
  return ch === ch.toUpperCase() && ch !== ch.toLowerCase();
}

/** Manba bo'lagining bosh harf holatini natijaga ko'chiradi. */
function applyCase(latin, cyrillic) {
  if (latin.length > 1 && latin === latin.toUpperCase() && /[A-Za-z]/.test(latin)) {
    return cyrillic.toUpperCase();
  }
  if (isUpper(latin[0])) {
    return cyrillic.charAt(0).toUpperCase() + cyrillic.slice(1);
  }
  return cyrillic;
}

/** Sof lotin bo'lagini o'giradi (ICU/URL/lug'at bu bosqichga yetib kelmaydi). */
function transliterateRun(text) {
  let out = "";
  let i = 0;
  // "start" — so'z boshi yoki so'z chegarasidan keyingi holat.
  let prev = "start";

  while (i < text.length) {
    let matched = false;

    for (const [latin, cyrillic] of DIGRAPHS) {
      const candidate = text.slice(i, i + latin.length);
      if (candidate.toLowerCase() !== latin) continue;

      // Oxirgi harf aslida keyingi apostrof-digrafga tegishli bo'lsa
      // (masalan "yo'q" dagi `o`), bu digrafni qabul qilmaymiz.
      if (
        APOSTROPHE_DIGRAPH_HEADS.has(latin[latin.length - 1]) &&
        text[i + latin.length] === "'"
      ) {
        continue;
      }

      out += applyCase(candidate, cyrillic);
      prev = VOWEL_DIGRAPHS.has(latin) ? "vowel" : "consonant";
      i += latin.length;
      matched = true;
      break;
    }
    if (matched) continue;

    const ch = text[i];
    const lower = ch.toLowerCase();

    // Noaniqlik to'plami: `e` so'z boshida yoki unlidan keyin → э, aks holda → е.
    if (lower === "e") {
      out += applyCase(ch, prev === "consonant" ? "е" : "э");
      prev = "vowel";
      i += 1;
      continue;
    }

    if (SINGLES.has(lower)) {
      out += applyCase(ch, SINGLES.get(lower));
      prev = LATIN_VOWELS.has(lower) ? "vowel" : "consonant";
      i += 1;
      continue;
    }

    // Lotin alifbosidan tashqari belgi — daxlsiz, so'z chegarasi.
    out += ch;
    prev = "start";
    i += 1;
  }

  return out;
}

/* -------------------------------------------------------------------------- */
/* So'z lug'ati                                                                */
/* -------------------------------------------------------------------------- */

function buildWordLookup(words) {
  const exact = new Map();
  const lower = new Map();
  for (const [key, value] of Object.entries(words ?? {})) {
    exact.set(key, value);
    lower.set(normalizeApostrophes(key).toLowerCase(), value);
  }
  return { exact, lower };
}

function resolveWord(word, lookup) {
  const exact = lookup.exact.get(word);
  if (exact !== undefined) return exact;

  const insensitive = lookup.lower.get(word.toLowerCase());
  if (insensitive !== undefined) return applyCase(word, insensitive);

  return transliterateRun(word);
}

/* -------------------------------------------------------------------------- */
/* Daxlsiz segmentlar: URL, e-mail, HTML teglari                               */
/* -------------------------------------------------------------------------- */

const PROTECTED_SEGMENT =
  /https?:\/\/[^\s<]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|<\/?[A-Za-z][^>]*>/g;

/** Apostrof normallashtirilgani uchun so'z ichida faqat ASCII `'` bo'ladi. */
const WORD = /[A-Za-z']+/g;

function transliterateWords(text, lookup) {
  if (!text) return text;
  let out = "";
  let last = 0;
  for (const match of text.matchAll(WORD)) {
    out += text.slice(last, match.index);
    out += resolveWord(match[0], lookup);
    last = match.index + match[0].length;
  }
  return out + text.slice(last);
}

function transliterateFreeText(text, lookup) {
  if (!text) return text;
  let out = "";
  let last = 0;
  for (const match of text.matchAll(PROTECTED_SEGMENT)) {
    out += transliterateWords(text.slice(last, match.index), lookup);
    out += match[0]; // URL / e-mail / teg — aynan o'zi
    last = match.index + match[0].length;
  }
  return out + transliterateWords(text.slice(last), lookup);
}

/* -------------------------------------------------------------------------- */
/* ICU parser (Pitfall 8 — platsholderlar daxlsiz)                             */
/* -------------------------------------------------------------------------- */

/**
 * `{` dan boshlab mos keluvchi `}` indeksini qaytaradi (-1 — muvozanatsiz).
 * `check-messages.mjs` ham shu grammatikadan foydalanadi.
 */
export function findMatchingBrace(text, start) {
  let depth = 0;
  for (let i = start; i < text.length; i += 1) {
    if (text[i] === "{") depth += 1;
    else if (text[i] === "}") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/** ICU argument tanasini yuqori darajadagi vergullar bo'yicha bo'ladi. */
export function splitTopLevel(inner) {
  const parts = [];
  let depth = 0;
  let current = "";
  for (const ch of inner) {
    if (ch === "{") depth += 1;
    else if (ch === "}") depth -= 1;

    if (ch === "," && depth === 0) {
      parts.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  parts.push(current);
  return parts;
}

/**
 * `plural` / `select` tanasi: branch NOMLARI (`one`, `other`, `=0`, `few`)
 * va `#` daxlsiz qoladi, faqat `{...}` ichidagi branch MATNI o'giriladi.
 */
function transliterateBranches(body, lookup) {
  let out = "";
  let i = 0;
  while (i < body.length) {
    if (body[i] === "{") {
      const end = findMatchingBrace(body, i);
      if (end === -1) {
        out += body.slice(i);
        break;
      }
      out += `{${transliterateMessage(body.slice(i + 1, end), lookup)}}`;
      i = end + 1;
    } else {
      out += body[i];
      i += 1;
    }
  }
  return out;
}

function transliterateArgument(block, lookup) {
  const parts = splitTopLevel(block.slice(1, -1));

  // `{name}` yoki `{total, number}` — matn bloki yo'q, butunlay daxlsiz.
  if (parts.length < 3) return block;

  const [argName, argType, ...rest] = parts;
  const type = argType.trim();

  // `{date, date, short}` kabi format qismlari ham matn emas.
  if (type !== "plural" && type !== "select" && type !== "selectordinal") {
    return block;
  }

  const body = transliterateBranches(rest.join(","), lookup);
  return `{${argName},${argType},${body}}`;
}

function transliterateMessage(text, lookup) {
  let out = "";
  let plainStart = 0;
  let i = 0;

  while (i < text.length) {
    if (text[i] === "{") {
      const end = findMatchingBrace(text, i);
      if (end === -1) break; // muvozanatsiz qavs — qolgani oddiy matn
      out += transliterateFreeText(text.slice(plainStart, i), lookup);
      out += transliterateArgument(text.slice(i, end + 1), lookup);
      i = end + 1;
      plainStart = i;
    } else {
      i += 1;
    }
  }

  return out + transliterateFreeText(text.slice(plainStart), lookup);
}

/* -------------------------------------------------------------------------- */
/* Ommaviy API                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * Bitta xabarni o'giradi. Sof funksiya — test qilinadigan yagona birlik.
 *
 * @param {string} text  uz-Latn xabar (ICU sintaksisi bilan bo'lishi mumkin)
 * @param {Record<string, string>} [words]  so'z darajasidagi lug'at
 * @returns {string} uz-Cyrl xabar
 */
export function transliterate(text, words = {}) {
  return transliterateMessage(normalizeApostrophes(text), buildWordLookup(words));
}

/**
 * Butun xabar daraxtini o'giradi.
 *
 * Ustuvorlik: `overrides.messages[to'liq.kalit]` > `overrides.words` > mapping.
 *
 * @param {Record<string, unknown>} source  uz-Latn.json mazmuni
 * @param {{messages?: Record<string,string>, words?: Record<string,string>}} [overrides]
 */
export function generateCyrillic(source, overrides = {}) {
  const messages = overrides.messages ?? {};
  const lookup = buildWordLookup(overrides.words ?? {});

  const walk = (node, prefix) => {
    const out = {};
    for (const [key, value] of Object.entries(node)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      if (value && typeof value === "object" && !Array.isArray(value)) {
        out[key] = walk(value, fullKey);
      } else if (typeof value === "string") {
        out[key] =
          messages[fullKey] !== undefined
            ? messages[fullKey]
            : transliterateMessage(normalizeApostrophes(value), lookup);
      } else {
        out[key] = value;
      }
    }
    return out;
  };

  return walk(source, "");
}

/* -------------------------------------------------------------------------- */
/* CLI                                                                         */
/* -------------------------------------------------------------------------- */

function serialize(tree) {
  // LF bilan yoziladi — `.gitattributes` (eol=lf) bilan birga CI (ubuntu) va
  // Windows'da bir xil bayt natija beradi.
  return `${JSON.stringify(tree, null, 2)}\n`;
}

function normalizeEol(text) {
  return text.replace(/\r\n/g, "\n");
}

function printDiff(expected, actual) {
  const left = expected.split("\n");
  const right = actual.split("\n");
  const max = Math.max(left.length, right.length);
  let shown = 0;
  for (let i = 0; i < max && shown < 20; i += 1) {
    if (left[i] !== right[i]) {
      console.error(`  ${i + 1} - kutilgan: ${left[i] ?? "(satr yo'q)"}`);
      console.error(`  ${i + 1} + commit:   ${right[i] ?? "(satr yo'q)"}`);
      shown += 1;
    }
  }
}

function main() {
  const check = process.argv.includes("--check");
  const source = JSON.parse(readFileSync(SOURCE_FILE, "utf8"));
  const overrides = JSON.parse(readFileSync(OVERRIDES_FILE, "utf8"));
  const generated = serialize(generateCyrillic(source, overrides));

  if (!check) {
    writeFileSync(TARGET_FILE, generated, "utf8");
    console.log("[i18n:gen] messages/uz-Cyrl.json qayta hosil qilindi");
    return;
  }

  let committed;
  try {
    committed = readFileSync(TARGET_FILE, "utf8");
  } catch {
    console.error("[i18n:gen --check] messages/uz-Cyrl.json topilmadi.");
    console.error("  Tuzatish: npm run i18n:gen && git add messages/uz-Cyrl.json");
    process.exit(1);
  }

  if (normalizeEol(committed) !== normalizeEol(generated)) {
    console.error(
      "[i18n:gen --check] DRIFT: commit qilingan uz-Cyrl.json generatsiya natijasiga mos emas.",
    );
    printDiff(normalizeEol(generated), normalizeEol(committed));
    console.error("  Tuzatish: npm run i18n:gen && git add messages/uz-Cyrl.json");
    process.exit(1);
  }

  console.log("[i18n:gen --check] drift yo'q");
}

const invokedDirectly =
  process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename);

if (invokedDirectly) main();
