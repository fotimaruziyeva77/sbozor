#!/usr/bin/env node
/**
 * Xabar fayllari darvozasi (CI).
 *
 *   node scripts/check-messages.mjs
 *
 * Ikki tekshiruv:
 *   (a) KALIT-PARITY  — uchala faylning tekislangan kalit to'plamlari AYNAN teng
 *   (b) ICU-PARITY    — har bir kalitdagi ICU argument NOMLARI to'plami teng
 *
 * (b) aynan Pitfall 8 ni ushlaydi: transliterator `{stallNumber}` ni
 * `{сталлНумбер}` ga aylantirib qo'ysa, argument to'plami farq qiladi va
 * bu yerda bloklanadi — runtime'dagi `IntlError: MISSING_ARGUMENT` gacha
 * yetib bormaydi.
 *
 * Tashqi npm paketiga bog'liq EMAS.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { findMatchingBrace, splitTopLevel } from "./gen-cyrillic.mjs";

const MESSAGES_DIR = path.join(import.meta.dirname, "..", "messages");
const REFERENCE = "uz-Latn";
const LOCALES = [REFERENCE, "uz-Cyrl", "ru"];

/* -------------------------------------------------------------------------- */

function flatten(node, prefix = "", out = new Map()) {
  for (const [key, value] of Object.entries(node)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      flatten(value, fullKey, out);
    } else {
      out.set(fullKey, value);
    }
  }
  return out;
}

/**
 * Xabardagi barcha ICU argument nomlarini yig'adi (ichma-ich ham).
 * Branch NOMLARI (`one`, `other`, `=0`) argument emas — ular yig'ilmaydi.
 */
function collectIcuArguments(text, into = new Set()) {
  if (typeof text !== "string") return into;

  let i = 0;
  while (i < text.length) {
    if (text[i] !== "{") {
      i += 1;
      continue;
    }

    const end = findMatchingBrace(text, i);
    if (end === -1) break;

    const parts = splitTopLevel(text.slice(i + 1, end));
    into.add(parts[0].trim());

    if (parts.length >= 3) {
      const type = parts[1].trim();
      if (type === "plural" || type === "select" || type === "selectordinal") {
        // Branch matnlari ichidagi ichki argumentlarni ham hisobga olamiz.
        const body = parts.slice(2).join(",");
        let j = 0;
        while (j < body.length) {
          if (body[j] === "{") {
            const branchEnd = findMatchingBrace(body, j);
            if (branchEnd === -1) break;
            collectIcuArguments(body.slice(j + 1, branchEnd), into);
            j = branchEnd + 1;
          } else {
            j += 1;
          }
        }
      }
    }

    i = end + 1;
  }

  return into;
}

function load(locale) {
  const file = path.join(MESSAGES_DIR, `${locale}.json`);
  try {
    return flatten(JSON.parse(readFileSync(file, "utf8")));
  } catch (error) {
    console.error(`[i18n:check] ${locale}.json o'qib bo'lmadi: ${error.message}`);
    process.exit(1);
  }
}

/* -------------------------------------------------------------------------- */

const catalogues = new Map(LOCALES.map((locale) => [locale, load(locale)]));
const reference = catalogues.get(REFERENCE);
const problems = [];

/* (a) Kalit-parity ------------------------------------------------------- */

for (const locale of LOCALES) {
  if (locale === REFERENCE) continue;
  const current = catalogues.get(locale);

  for (const key of reference.keys()) {
    if (!current.has(key)) {
      problems.push(`[KALIT] ${locale}.json da YETISHMAYDI: ${key}`);
    }
  }
  for (const key of current.keys()) {
    if (!reference.has(key)) {
      problems.push(
        `[KALIT] ${locale}.json da ORTIQCHA (${REFERENCE}.json da yo'q): ${key}`,
      );
    }
  }
}

/* (b) ICU argument parity ------------------------------------------------ */

for (const [key, value] of reference) {
  const expected = collectIcuArguments(value);

  for (const locale of LOCALES) {
    if (locale === REFERENCE) continue;
    const current = catalogues.get(locale);
    if (!current.has(key)) continue; // (a) da allaqachon xabar berilgan

    const actual = collectIcuArguments(current.get(key));

    const missing = [...expected].filter((arg) => !actual.has(arg));
    const extra = [...actual].filter((arg) => !expected.has(arg));

    if (missing.length > 0) {
      problems.push(
        `[ICU] ${locale}.json "${key}" — argument YETISHMAYDI: ${missing.join(", ")}`,
      );
    }
    if (extra.length > 0) {
      problems.push(
        `[ICU] ${locale}.json "${key}" — kutilmagan argument: ${extra.join(", ")}`,
      );
    }
  }
}

/* -------------------------------------------------------------------------- */

if (problems.length > 0) {
  console.error(`[i18n:check] ${problems.length} ta muammo topildi:\n`);
  for (const problem of problems) console.error(`  ${problem}`);
  console.error(
    `\n  Tuzatish: ${REFERENCE}.json ni asos qilib ru.json ni to'ldiring,` +
      " so'ng `npm run i18n:gen` bilan uz-Cyrl.json ni qayta hosil qiling.",
  );
  process.exit(1);
}

console.log(
  `[i18n:check] ${reference.size} kalit × ${LOCALES.length} til — kalit va ICU parity to'liq`,
);
