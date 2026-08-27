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
const RBAC_PY = path.join(
  REPO_ROOT,
  "services",
  "core-api",
  "app",
  "security",
  "rbac.py",
);
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

/** `#` yoki `//` bilan boshlanadigan qatorlarni olib tashlaydi.
 *
 * MAJBURIY: ikkala matritsada ham izohlar huquq nomlarini MATN sifatida
 * eslatadi ("`camera_view` direktorda qoladi"). Izoh filtrlanmasa, o'sha
 * eslatma HUQUQ BERILGANDEK o'qilardi va darvoza jimgina yolg'on-yashil
 * bo'lardi — ya'ni u aynan o'zi ushlashi kerak bo'lgan xatoni yashirardi.
 */
function stripComments(block) {
  return block
    .split("\n")
    .filter((line) => {
      const trimmed = line.trim();
      return !trimmed.startsWith("#") && !trimmed.startsWith("//");
    })
    .join("\n");
}

/** `class Permission(StrEnum):` -> `{ CAMERA_VIEW: "camera_view", ... }` */
function readPythonPermissionValues(source) {
  const start = source.indexOf("class Permission(StrEnum):");
  assert.ok(start !== -1, "`Permission` enum'i `rbac.py` da topilmadi");
  const rest = source.slice(start);
  const end = rest.indexOf("\nROLE_PERMISSIONS");
  assert.ok(end !== -1, "`ROLE_PERMISSIONS` `rbac.py` da topilmadi");
  const body = rest.slice(0, end);

  const values = {};
  for (const match of body.matchAll(/^ {4}([A-Z_]+) = "([^"]+)"/gmu)) {
    values[match[1]] = match[2];
  }
  assert.ok(
    Object.keys(values).length > 5,
    "`Permission` enum'idan a'zo o'qilmadi — parser sxemasi eskirgan",
  );
  return values;
}

/** `rbac.py::ROLE_PERMISSIONS` -> `{ platform_admin: ["market_view_all", ...] }` */
function readPythonRoleMatrix(source, permissionValues) {
  const start = source.indexOf(
    "ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {",
  );
  assert.ok(start !== -1, "`ROLE_PERMISSIONS` e'loni `rbac.py` da topilmadi");
  const rest = source.slice(start);
  const end = rest.indexOf("\n}\n");
  assert.ok(end !== -1, "`ROLE_PERMISSIONS` lug'atining oxiri topilmadi");
  const block = stripComments(rest.slice(0, end));

  const heads = [...block.matchAll(/^ {4}Role\.([A-Z_]+): frozenset\(/gmu)];
  assert.ok(heads.length > 0, "`ROLE_PERMISSIONS` dan birorta rol o'qilmadi");

  const matrix = {};
  heads.forEach((head, index) => {
    const from = head.index;
    const to = index + 1 < heads.length ? heads[index + 1].index : block.length;
    const chunk = block.slice(from, to);

    matrix[head[1].toLowerCase()] = [
      ...chunk.matchAll(/Permission\.([A-Z_]+)/gu),
    ].map((item) => {
      const value = permissionValues[item[1]];
      assert.ok(value, `\`Permission.${item[1]}\` enum'da e'lon qilinmagan`);
      return value;
    });
  });
  return matrix;
}

/** `rbac.ts::ROLE_PERMISSIONS` -> `{ platform_admin: ["market_view_all", ...] }` */
function readTsRoleMatrix(source) {
  const start = source.indexOf("const ROLE_PERMISSIONS");
  assert.ok(start !== -1, "`ROLE_PERMISSIONS` `rbac.ts` da topilmadi");
  const rest = source.slice(start);
  const end = rest.indexOf("\n};");
  assert.ok(end !== -1, "`ROLE_PERMISSIONS` obyektining oxiri topilmadi");
  const block = stripComments(rest.slice(0, end));

  const matrix = {};
  for (const match of block.matchAll(/^ {2}([a-z_]+):\s*\[([^\]]*)\]/gmu)) {
    matrix[match[1]] = [...match[2].matchAll(/"([^"]+)"/gu)].map(
      (item) => item[1],
    );
  }
  assert.ok(
    Object.keys(matrix).length > 0,
    "`rbac.ts::ROLE_PERMISSIONS` dan birorta rol o'qilmadi",
  );
  return matrix;
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
 * =============================================================================
 * G-8: ROL-HUQUQ MATRITSASINING IKKI NUSXASI (3-fazada qo'shildi).
 *
 * NEGA BU DARVOZA SHU YERDA TUG'ILDI: `rbac.py` va `rbac.ts` matritsalari
 * "QO'LDA sinxron saqlanadi" deb IKKALA faylning boshida ham yozilgan
 * edi — lekin buni tekshiradigan HECH NIMA yo'q edi. Ya'ni majburiyat
 * hujjatda bor, mexanizmda yo'q: `rbac.py` ga huquq qo'shib `rbac.ts` ni
 * unutgan odam TO'LIQ YASHIL CI ko'rardi.
 *
 * Oqibati ma'lumot ochilishi EMAS (haqiqiy qaror serverda), lekin u
 * ikki tomonga ham buziladi:
 *   * faqat backend yangilansa  -> huquq bor, TUGMA KO'RINMAYDI;
 *   * faqat frontend yangilansa -> tugma ko'rinadi, bosilganda 403.
 * Ikkinchisi ayniqsa yomon: foydalanuvchi "tizim buzuq" deb xulosa
 * qiladi va sabab hech qaysi log'da ko'rinmaydi.
 *
 * 3-faza aynan shu xatoni takrorlash xavfi eng yuqori nuqta: `CAMERA_MANAGE`
 * ikkala matritsaga ham qo'shilishi kerak edi (W0-2/W0-3).
 * =============================================================================
 */
test("G-8: `PERMISSIONS` ro'yxati `rbac.py::Permission` enum'i bilan aynan mos", () => {
  const frontend = readTsStringArray(read(RBAC), "PERMISSIONS");
  const backend = Object.values(readPythonPermissionValues(read(RBAC_PY)));

  assert.deepEqual(
    [...frontend].sort(),
    [...backend].sort(),
    "UI huquqlar ro'yxati backend `Permission` enum'idan farq qiladi — " +
      "yangi huquq bir tomonda qo'shilib ikkinchisida unutilgan",
  );
});

test("G-8: rol-huquq matritsasi ikkala faylda AYNAN bir xil", () => {
  const permissionValues = readPythonPermissionValues(read(RBAC_PY));
  const backend = readPythonRoleMatrix(read(RBAC_PY), permissionValues);
  const frontend = readTsRoleMatrix(read(RBAC));

  assert.deepEqual(
    Object.keys(frontend).sort(),
    Object.keys(backend).sort(),
    "Matritsalardagi rollar to'plami farq qiladi",
  );

  const drift = [];
  for (const role of Object.keys(backend).sort()) {
    const expected = [...backend[role]].sort();
    const actual = [...(frontend[role] ?? [])].sort();

    const missing = expected.filter((item) => !actual.includes(item));
    const extra = actual.filter((item) => !expected.includes(item));
    if (missing.length > 0) {
      drift.push(`${role}: \`rbac.ts\` da YO'Q -> ${missing.join(", ")}`);
    }
    if (extra.length > 0) {
      drift.push(`${role}: \`rbac.ts\` da ORTIQCHA -> ${extra.join(", ")}`);
    }
  }

  assert.deepEqual(
    drift,
    [],
    `Ikki matritsa ajralib ketgan:\n  ${drift.join("\n  ")}\n` +
      "`services/core-api/app/security/rbac.py` va `frontend/src/lib/rbac.ts` " +
      "BIRGA o'zgarishi shart.",
  );

  // Nazorat holati: parser haqiqatan ham matritsani o'qidi. Bo'sh
  // to'plamlarda yuqoridagi solishtirish JIMGINA yashil qolardi.
  assert.equal(Object.keys(backend).length, 5, "backend matritsasida 5 rol");
  assert.ok(
    backend.platform_admin.includes("market_manage"),
    "nazorat qiymati yo'qoldi — parser matritsani o'qimayapti",
  );
});

test("G-8: kamera huquqlari D-15/D-07 chegarasiga mos (3-faza)", () => {
  const frontend = readTsRoleMatrix(read(RBAC));

  for (const role of ["platform_admin", "market_admin"]) {
    assert.ok(
      frontend[role].includes("camera_manage"),
      `\`${role}\` da \`camera_manage\` yo'q — NVR ulash tugmasi ko'rinmaydi (CAM-08)`,
    );
    assert.ok(frontend[role].includes("camera_view"), `\`${role}\`: camera_view`);
  }

  // D-07: direktor KO'RADI, lekin NVR sozlamasiga TEGMAYDI.
  assert.ok(frontend.director.includes("camera_view"));
  assert.ok(
    !frontend.director.includes("camera_manage"),
    "D-07 buzildi: direktorga `camera_manage` berilgan — o'qish roli NVR " +
      "sozlash tugmasini ko'radigan bo'lib qoldi",
  );

  for (const role of ["cashier", "inspector"]) {
    assert.ok(
      !frontend[role].some((item) => item.startsWith("camera_")),
      `\`${role}\` roliga kamera yuzasi ochilgan`,
    );
  }
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
