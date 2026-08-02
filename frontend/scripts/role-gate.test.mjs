#!/usr/bin/env node
/**
 * D-04 rol darvozasining FRONTEND KO'ZGUSI backend bilan mos ekanini tekshiradi.
 *
 * NEGA KERAK: `MARKET_ADMIN_ASSIGNABLE_ROLES` ikki tilda, ikki faylda
 * yozilgan — `services/core-api/app/services/staff_accounts.py` (haqiqiy
 * darvozaning YAGONA manbai) va `frontend/src/lib/api-types.ts` (forma
 * qaysi katakchalarni ko'rsatishini hal qiladi). Ular ajralib ketsa hech
 * bir mavjud test qizarmasdi: backend testlari frontend faylini bilmaydi,
 * frontend esa backendni. Natija — bozor admini formada ko'rgan rolni
 * tanlaydi va tushunarsiz "ruxsat yo'q" xatosiga uriladi (yoki teskarisi:
 * ruxsat etilgan rol umuman ko'rinmaydi).
 *
 * ⚠ MANBA 02-24 DA KO'CHDI: `users.py` -> `services/staff_accounts.py`,
 * chunki darajaning endi IKKITA chaqiruvchisi bor (`POST /users` va
 * `POST /imports/staff`). Bu darvoza ko'chishni O'ZI ushladi — eski yo'l
 * bo'yicha o'qish "Python faylida topilmadi" bilan qizardi, ya'ni u
 * "sukut bilan yashil qolish" sinfidan xoli.
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
const STAFF_ACCOUNTS = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "services",
  "staff_accounts.py",
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
    read(STAFF_ACCOUNTS),
    "MARKET_ADMIN_ASSIGNABLE_ROLES",
  );

  assert.deepEqual(
    [...frontend].sort(),
    [...backend].sort(),
    "Forma ko'rsatadigan rollar server darvozasidan farq qiladi (D-04)",
  );
  assert.deepEqual([...frontend].sort(), ["cashier", "inspector"]);
});

/*
 * DIQQAT: `rbac.ts::ROLES` — bu YORLIQ (label) ro'yxati, ya'ni "tizimda
 * qanday rollar bor" degan savolga javob beradi. U BERILISHI MUMKIN bo'lgan
 * rollar ro'yxati EMAS.
 *
 * Bu testning eski sarlavhasi "platforma admini beshalasini ko'radi" degan
 * ma'noni yuklardi va shu bilan CR-03 zaifligini "to'g'ri xulq" sifatida
 * qulflab qo'ygan edi. Aslida beshinchi rol — `platform_admin` — hech qachon
 * a'zolik roli sifatida BERILMAYDI (pastdagi testga qarang).
 */
test("`rbac.ts::ROLES` yorliq ro'yxati `sbozor_core.enums.Role` bilan aynan mos", () => {
  const frontend = readTsStringArray(read(RBAC), "ROLES");
  const backend = readPythonEnumValues(read(CORE_ENUMS), "Role");

  assert.deepEqual([...frontend].sort(), [...backend].sort());
  assert.equal(frontend.length, 5);
});

/*
 * CR-03 qulfi: `platform_admin` HECH BIR beriladigan rollar ro'yxatida
 * bo'lmasligi kerak.
 *
 * NEGA: "platforma admini" `users.is_platform_admin` BAYROG'I bilan
 * aniqlanadi, `user_market_roles` qatori bilan emas. A'zolik roli sifatida
 * berilgan `platform_admin` hisobni ayni paytda ham ortiqcha huquqli
 * (`market_view_all` -> butun platforma bozorlari ro'yxati), ham buzuq
 * (`select-market` uni boshqa bozorga kiritmaydi) qilib qo'yadi.
 *
 * Bu test formaning O'ZINI tekshirmaydi — u ro'yxat manbasini tekshiradi;
 * `create-user-dialog.tsx` katakchalarni aynan shu ro'yxatdan quradi.
 */
test("CR-03: `platform_admin` beriladigan rollar ro'yxatlarida YO'Q", () => {
  const source = read(API_TYPES);
  const platformAdminAssignable = readTsStringArray(
    source,
    "PLATFORM_ADMIN_ASSIGNABLE_ROLES",
  );
  const marketAdminAssignable = readTsStringArray(
    source,
    "MARKET_ADMIN_ASSIGNABLE_ROLES",
  );

  assert.ok(
    !platformAdminAssignable.includes("platform_admin"),
    "`platform_admin` platforma admini bera oladigan rollar ro'yxatiga tushib qolgan — u bayroq, a'zolik roli emas (CR-03)",
  );
  assert.ok(
    !marketAdminAssignable.includes("platform_admin"),
    "`platform_admin` bozor admini bera oladigan rollar ro'yxatiga tushib qolgan (CR-03)",
  );

  assert.deepEqual(
    [...platformAdminAssignable].sort(),
    ["cashier", "director", "inspector", "market_admin"],
  );

  /*
   * Ro'yxat `Role` enum'iga BOG'LANADI: platforma admini `platform_admin`
   * dan tashqari HAR BIR rolni bera oladi. Backend'ga yangi rol qo'shilsa
   * shu assert qizaradi va ro'yxatni yangilash esdan chiqmaydi — ya'ni test
   * qattiq yozilgan to'rtlikni takrorlab qo'ymaydi, qoidani qulflaydi.
   */
  const enumRoles = readPythonEnumValues(read(CORE_ENUMS), "Role");
  assert.deepEqual(
    [...platformAdminAssignable].sort(),
    enumRoles.filter((role) => role !== "platform_admin").sort(),
    "Platforma admini bera oladigan rollar = `Role` enum'i minus `platform_admin`",
  );
});
