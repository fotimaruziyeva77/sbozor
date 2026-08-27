#!/usr/bin/env node
/**
 * Audit hodisalari ro'yxati backend enum'i va UCHALA tarjima fayli bilan mos.
 *
 * NEGA KERAK: `audit.actions.*` — yagona namespace bo'lib, uning kalitlari
 * kod ichida emas, MA'LUMOTDAN (`audit_log.action` ustunidan) keladi.
 * Backend yangi hodisa qo'shsa (`sbozor_core.enums.AuditAction`), frontend
 * uni jimgina XOM identifikator sifatida ko'rsatib qo'yardi — masalan
 * "refresh_reuse_detected" degan qator o'zbekcha ekranda paydo bo'lardi.
 *
 * `i18n:check` bu holatni USHLAY OLMAYDI: u faqat uchala faylning bir-biriga
 * mosligini tekshiradi, ro'yxatning TO'LIQLIGINI emas — kalit uchala tilda
 * ham yo'q bo'lsa, parity baribir yashil.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

const API_TYPES = path.join(FRONTEND_ROOT, "src", "lib", "api-types.ts");
const CORE_ENUMS = path.join(
  REPO_ROOT,
  "packages",
  "sbozor-core",
  "sbozor_core",
  "enums.py",
);

function read(file) {
  return readFileSync(file, "utf8");
}

function readTsStringArray(source, name) {
  const match = new RegExp(
    `export const ${name}\\s*=\\s*\\[([^\\]]*)\\]`,
    "u",
  ).exec(source);
  assert.ok(match, `${name} TypeScript faylida topilmadi`);
  return [...match[1].matchAll(/"([^"]+)"/gu)].map((item) => item[1]);
}

function readPythonEnumValues(source, className) {
  const start = source.indexOf(`class ${className}(StrEnum):`);
  assert.ok(start !== -1, `${className} enum'i topilmadi`);
  const rest = source.slice(start);
  const end = rest.indexOf("\nclass ");
  const body = end === -1 ? rest : rest.slice(0, end);
  return [...body.matchAll(/^ {4}[A-Z_]+ = "([^"]+)"/gmu)].map(
    (item) => item[1],
  );
}

function loadMessages(locale) {
  return JSON.parse(
    readFileSync(path.join(FRONTEND_ROOT, "messages", `${locale}.json`), "utf8"),
  );
}

test("AUDIT_ACTIONS `sbozor_core.enums.AuditAction` bilan AYNAN mos", () => {
  const frontend = readTsStringArray(read(API_TYPES), "AUDIT_ACTIONS");
  const backend = readPythonEnumValues(read(CORE_ENUMS), "AuditAction");

  assert.deepEqual([...frontend].sort(), [...backend].sort());
});

test("Har bir audit hodisasi uchun uchala tilda tarjima bor", () => {
  const actions = readTsStringArray(read(API_TYPES), "AUDIT_ACTIONS");

  for (const locale of LOCALES) {
    const messages = loadMessages(locale);
    const labels = messages.audit?.actions ?? {};

    for (const action of actions) {
      assert.equal(
        typeof labels[action],
        "string",
        `${locale}.json da audit.actions.${action} yo'q`,
      );
    }
    assert.deepEqual(
      Object.keys(labels).sort(),
      [...actions].sort(),
      `${locale}.json da ortiqcha audit.actions kaliti bor`,
    );
  }
});

test("Har bir audit jadvali uchun uchala tilda tarjima bor", () => {
  const tables = readTsStringArray(read(API_TYPES), "AUDIT_TABLES");

  for (const locale of LOCALES) {
    const labels = loadMessages(locale).audit?.tables ?? {};
    assert.deepEqual(
      Object.keys(labels).sort(),
      [...tables].sort(),
      `${locale}.json da audit.tables ro'yxati AUDIT_TABLES bilan mos emas`,
    );
  }
});
