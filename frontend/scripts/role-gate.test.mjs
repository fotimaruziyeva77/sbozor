#!/usr/bin/env node
/**
 * D-04 rol darvozasining FRONTEND KO'ZGUSI backend bilan mos ekanini tekshiradi.
 *
 * NEGA KERAK: `MARKET_ADMIN_ASSIGNABLE_ROLES` ikki tilda, ikki faylda
 * yozilgan — `services/core-api/app/api/v1/users.py` (haqiqiy darvoza, 403
 * qaytaradi) va `frontend/src/lib/api-types.ts` (forma qaysi katakchalarni
 * ko'rsatishini hal qiladi). Ular ajralib ketsa hech bir mavjud test
 * qizarmasdi: backend testlari frontend faylini bilmaydi, frontend esa
 * backendni. Natija — bozor admini formada ko'rgan rolni tanlaydi va
 * tushunarsiz "ruxsat yo'q" xatosiga uriladi (yoki teskarisi: ruxsat
 * etilgan rol umuman ko'rinmaydi).
 *
 * Nusxa emas, FAYLLARNING O'ZI o'qiladi (01-07 da o'rnatilgan naqsh:
 * `test_locale_enum_matches_frontend_routing` shu usulda ishlaydi).
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");

const API_TYPES = path.join(FRONTEND_ROOT, "src", "lib", "api-types.ts");
const RBAC = path.join(FRONTEND_ROOT, "src", "lib", "rbac.ts");
const USERS_ROUTE = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "api",
  "v1",
  "users.py",
);
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

/** `NAME = ["a", "b"] as const;` -> `["a", "b"]` */
function readTsStringArray(source, name) {
  const match = new RegExp(
    `export const ${name}\\s*=\\s*\\[([^\\]]*)\\]`,
    "u",
  ).exec(source);
  assert.ok(match, `${name} TypeScript faylida topilmadi`);
  return [...match[1].matchAll(/"([^"]+)"/gu)].map((item) => item[1]);
}

/** `NAME = frozenset({Role.CASHIER, Role.INSPECTOR})` -> `["cashier", ...]` */
function readPythonRoleSet(source, name) {
  const match = new RegExp(
    `${name}\\s*=\\s*frozenset\\(\\{([^}]*)\\}\\)`,
    "u",
  ).exec(source);
  assert.ok(match, `${name} Python faylida topilmadi`);
  return [...match[1].matchAll(/Role\.([A-Z_]+)/gu)].map((item) =>
    item[1].toLowerCase(),
  );
}

/** `class Role(StrEnum):` tanasidagi `NAME = "value"` qiymatlari. */
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

test("D-04: bozor admini bera oladigan rollar backend bilan AYNAN mos", () => {
  const frontend = readTsStringArray(
    read(API_TYPES),
    "MARKET_ADMIN_ASSIGNABLE_ROLES",
  );
  const backend = readPythonRoleSet(
    read(USERS_ROUTE),
    "MARKET_ADMIN_ASSIGNABLE_ROLES",
  );

  assert.deepEqual(
    [...frontend].sort(),
    [...backend].sort(),
    "Forma ko'rsatadigan rollar server darvozasidan farq qiladi (D-04)",
  );
  assert.deepEqual([...frontend].sort(), ["cashier", "inspector"]);
});

test("Rollar ro'yxati `sbozor_core.enums.Role` bilan mos (platforma admini beshalasini ko'radi)", () => {
  const frontend = readTsStringArray(read(RBAC), "ROLES");
  const backend = readPythonEnumValues(read(CORE_ENUMS), "Role");

  assert.deepEqual([...frontend].sort(), [...backend].sort());
  assert.equal(frontend.length, 5);
});
