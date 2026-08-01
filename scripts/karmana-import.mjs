#!/usr/bin/env node
/**
 * Karmananing real ma'lumotini API orqali kiritish — BRAUZERSIZ, takrorlanadigan yo'l.
 *
 *   node scripts/karmana-import.mjs template --kind=stalls --out=./local/stalls.xlsx
 *   node scripts/karmana-import.mjs upload   --kind=stalls --file=./local/stalls.xlsx
 *
 * Yo'riqnoma: `ops/data/karmana/README.md` (tartib, ustunlar, xato kodlari).
 *
 * ---------------------------------------------------------------------------
 * PAROL VA TELEFON argv'DAN OLINMAYDI — FAQAT MUHIT O'ZGARUVCHILARIDAN.
 *
 * Buyruq qatoridagi argument protsess ro'yxatida (`ps aux`, Windows'da
 * Task Manager / `wmic process`) MASHINADAGI HAR QANDAY foydalanuvchiga
 * ko'rinadi va odatda shell tarixiga ham tushadi. Platforma adminining
 * paroli esa BARCHA bozorlarga kirish demakdir.
 *
 * Shuning uchun `process.argv` faqat BUYRUQ va FAYL YO'LLARINI o'qiydi;
 * maxfiy qiymatlar `process.env` dan keladi (T-02-129).
 * ---------------------------------------------------------------------------
 *
 * TASHQI npm BOG'LIQLIGI YO'Q. Node 24 da `fetch`, `FormData` va `Blob`
 * global; qolgani standart kutubxonadan. Skript `npm ci` bajarilmagan
 * mashinada ham, konteynerdan tashqarida ham ishlaydi — chunki u
 * ma'lumotni kiritish paytida, ya'ni eng nozik lahzada kerak bo'ladi.
 */
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const KINDS = ["stalls", "vendors"];

/** 422 javobida konsolga chiqariladigan qator soni (qolgani sanoq bilan). */
const MAX_PRINTED_ERRORS = 50;

const USAGE = `
Karmana import — SBOZOR

Buyruqlar:
  template   Import shablonini yuklab oladi (zona/toifa ro'yxati ichida)
  upload     To'ldirilgan .xlsx faylni yuklaydi

Bayroqlar:
  --kind=stalls|vendors   Qaysi reestr (standart: stalls)
  --out=<yo'l>            template: shablon qayerga yoziladi
  --file=<yo'l>           upload: qaysi fayl yuboriladi
  --help                  Shu matn

Muhit o'zgaruvchilari (parol va telefon FAQAT shu yerdan):
  API_BASE_URL       masalan http://localhost:8000
  SBOZOR_PHONE       +998XXXXXXXXX
  SBOZOR_PASSWORD    parol
  SBOZOR_MARKET_ID   bozorning UUID'i

Misollar:
  npm run karmana:template -- --kind=stalls --out=./ops/data/karmana/local/stalls.xlsx
  npm run karmana:upload   -- --kind=stalls --file=./ops/data/karmana/local/stalls.xlsx

Xato bo'lsa: kod bo'yicha guruhlangan sanoq, so'ng birinchi ${MAX_PRINTED_ERRORS}
xato "{qator}-qator: {sabab}" ko'rinishida chiqadi va exit kodi 1 bo'ladi.
`.trim();

/* -------------------------------------------------------------------------- */
/* argv                                                                        */
/* -------------------------------------------------------------------------- */

/**
 * `process.argv` dan BUYRUQ va BAYROQLARNI ajratadi.
 *
 * Bu yerda maxfiy qiymat O'QILMAYDI (yuqoridagi izoh) — funksiya faqat
 * buyruq nomi va fayl yo'llarini biladi.
 */
function parseArgs(argv) {
  const flags = new Map();
  const positional = [];

  for (const token of argv) {
    if (token.startsWith("--")) {
      const [name, ...rest] = token.slice(2).split("=");
      flags.set(name, rest.length > 0 ? rest.join("=") : "true");
    } else if (token === "-h") {
      flags.set("help", "true");
    } else {
      positional.push(token);
    }
  }

  return { command: positional[0] ?? null, flags };
}

function requireKind(flags) {
  const kind = flags.get("kind") ?? "stalls";
  if (!KINDS.includes(kind)) {
    fail(`--kind noma'lum: '${kind}' (mumkin: ${KINDS.join(", ")})`);
  }
  return kind;
}

function requireFlag(flags, name, hint) {
  const value = flags.get(name);
  if (!value || value === "true") {
    fail(`--${name} ko'rsatilmagan. ${hint}`);
  }
  return value;
}

/* -------------------------------------------------------------------------- */
/* Muhit                                                                       */
/* -------------------------------------------------------------------------- */

/**
 * Maxfiy va ulanish qiymatlarining YAGONA manbai.
 *
 * Hammasi BIR JOYDA tekshiriladi: chala sozlangan muhitda skript login
 * qadamidan keyin emas, ENG BOSHIDA to'xtaydi va foydalanuvchi to'liq
 * ro'yxatni bir marta ko'radi.
 */
function readEnv() {
  const env = {
    baseUrl: (process.env.API_BASE_URL ?? "").replace(/\/+$/, ""),
    phone: process.env.SBOZOR_PHONE ?? "",
    password: process.env.SBOZOR_PASSWORD ?? "",
    marketId: process.env.SBOZOR_MARKET_ID ?? "",
  };

  const missing = [];
  if (!env.baseUrl) missing.push("API_BASE_URL");
  if (!env.phone) missing.push("SBOZOR_PHONE");
  if (!env.password) missing.push("SBOZOR_PASSWORD");
  if (!env.marketId) missing.push("SBOZOR_MARKET_ID");

  if (missing.length > 0) {
    fail(
      `Muhit o'zgaruvchilari yetishmayapti: ${missing.join(", ")}\n` +
        "  Ularni argv orqali berish MUMKIN EMAS — parol protsess ro'yxatida ko'rinardi.",
    );
  }
  return env;
}

/* -------------------------------------------------------------------------- */
/* HTTP                                                                        */
/* -------------------------------------------------------------------------- */

async function postJson(url, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(url, { method: "POST", headers, body: JSON.stringify(body) });
}

/**
 * Javob tanasini xavfsiz o'qiydi: JSON bo'lsa obyekt, aks holda matn.
 *
 * Xato yo'lida `response.json()` ni to'g'ridan-to'g'ri chaqirish
 * proksidan kelgan HTML sahifada `SyntaxError` bilan qulardi va
 * HAQIQIY sabab (masalan 502) ko'rinmasdi.
 */
async function readBody(response) {
  const text = await response.text();
  try {
    return { json: JSON.parse(text), text };
  } catch {
    return { json: null, text };
  }
}

/**
 * `POST /auth/login` -> `POST /auth/select-market` -> tenant tokeni.
 *
 * Ikki qadam MAJBURIY: platforma adminining a'zoligi bir nechta, ya'ni
 * login javobidagi token `mid` siz keladi va u bilan har qanday tenant
 * endpointi `409 market_not_selected` beradi.
 */
async function authenticate(env) {
  const login = await postJson(`${env.baseUrl}/api/v1/auth/login`, {
    phone: env.phone,
    password: env.password,
  });
  if (!login.ok) {
    const { text } = await readBody(login);
    fail(`Kirish rad etildi (${login.status}). ${short(text)}`);
  }
  const { json: loginBody } = await readBody(login);

  const selected = await postJson(
    `${env.baseUrl}/api/v1/auth/select-market`,
    { market_id: env.marketId },
    loginBody.access_token,
  );
  if (!selected.ok) {
    const { text } = await readBody(selected);
    fail(
      `Bozor tanlanmadi (${selected.status}). ${short(text)}\n` +
        `  SBOZOR_MARKET_ID = ${env.marketId} — bu foydalanuvchi shu bozorning a'zosimi?`,
    );
  }
  const { json: selectedBody } = await readBody(selected);
  return selectedBody.access_token;
}

/* -------------------------------------------------------------------------- */
/* Buyruqlar                                                                   */
/* -------------------------------------------------------------------------- */

async function commandTemplate(env, flags) {
  const kind = requireKind(flags);
  const out = requireFlag(flags, "out", "Masalan: --out=./ops/data/karmana/local/stalls.xlsx");

  const token = await authenticate(env);
  const response = await fetch(`${env.baseUrl}/api/v1/imports/template?kind=${kind}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    const { text } = await readBody(response);
    fail(`Shablon olinmadi (${response.status}). ${short(text)}`);
  }

  const bytes = Buffer.from(await response.arrayBuffer());
  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, bytes);

  console.log(`[karmana] shablon yozildi: ${out} (${bytes.length} bayt, kind=${kind})`);
  console.log("[karmana] ustunlar tartibi va to'ldirish qoidalari: ops/data/karmana/README.md");
}

async function commandUpload(env, flags) {
  const kind = requireKind(flags);
  const file = requireFlag(flags, "file", "Masalan: --file=./ops/data/karmana/local/stalls.xlsx");

  if (!file.toLowerCase().endsWith(".xlsx")) {
    fail(`Faqat .xlsx qabul qilinadi (kelgan: ${file}). .csv va .ods rad etiladi.`);
  }
  let bytes;
  try {
    bytes = readFileSync(file);
  } catch {
    fail(`Fayl o'qilmadi: ${file}`);
  }
  const sizeKb = Math.round(statSync(file).size / 1024);

  const token = await authenticate(env);
  const form = new FormData();
  form.append("file", new Blob([bytes]), basename(file));

  console.log(`[karmana] yuborilmoqda: ${file} (${sizeKb} KB) -> /api/v1/imports/${kind}`);
  const response = await fetch(`${env.baseUrl}/api/v1/imports/${kind}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: form,
  });
  const { json, text } = await readBody(response);

  if (response.ok) {
    console.log(`[karmana] TAYYOR — yozildi: ${json.inserted}, o'tkazib yuborildi: ${json.skipped}`);
    if (json.skipped > 0) {
      console.log(
        "[karmana] o'tkazib yuborilganlar — bazada ALLAQACHON bor qatorlar (D-15); " +
          "hech narsa o'zgartirilmadi.",
      );
    }
    console.log("[karmana] endi ops/data/karmana/README.md §7 dagi tekshiruv ro'yxatini bajaring.");
    return;
  }

  reportFailure(response.status, json, text);
}

/**
 * Muvaffaqiyatsiz importni O'QILADIGAN qilib chiqaradi va exit 1 beradi.
 *
 * TARTIB MUHIM: avval "hech narsa saqlanmadi" (D-14), so'ng GURUHLANGAN
 * sanoq, oxirida qatorlar. 300 qatorli ro'yxatni o'qib bo'lmaydi — uch
 * jumlalik sanoq esa darhol harakatga aylanadi.
 */
function reportFailure(status, json, text) {
  const detail = json && typeof json === "object" ? json.detail : null;

  if (detail && typeof detail === "object" && Array.isArray(detail.errors)) {
    console.error(`\n[karmana] IMPORT RAD ETILDI (${status}) — HECH NARSA SAQLANMADI (D-14).`);

    const counts = detail.error_counts ?? {};
    const grouped = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    if (grouped.length > 0) {
      console.error("\n  Xatolar (kod bo'yicha):");
      for (const [code, count] of grouped) console.error(`    ${code}: ${count}`);
    }

    console.error(`\n  Qatorlar (jami ${detail.errors.length}):`);
    for (const issue of detail.errors.slice(0, MAX_PRINTED_ERRORS)) {
      console.error(`    ${rowLine(issue)}`);
    }
    const rest = detail.errors.length - MAX_PRINTED_ERRORS;
    if (rest > 0) console.error(`    … va yana ${rest} ta xato`);

    console.error("\n  Kodlarning ma'nosi va tuzatish yo'li: ops/data/karmana/README.md §5");
    console.error("  Faylni tuzatib QAYTA yuklash xavfsiz (§6).");
    throw new CliError("import rad etildi", { printed: true });
  }

  if (typeof detail === "string") {
    fail(`Import rad etildi (${status}): ${detail}\n  Sabablari: ops/data/karmana/README.md §4–§5`);
  }
  fail(`Import rad etildi (${status}). ${short(text)}`);
}

/**
 * Bitta xato qatori — `{qator}-qator: {sabab}` shaklida, IKKI MARTA EMAS.
 *
 * ⚠ SERVER `message` NI ALLAQACHON SHU PREFIKS BILAN YUBORADI
 * (`import_validator.ImportIssue` docstringi: "foydalanuvchi uchun, uz-Latn,
 * qator raqami BILAN"). Prefiksni ko'r-ko'rona qo'shish
 * `2-qator: 2-qator: '...' zonasi topilmadi` berardi — bu SKRIPTNI TIRIK
 * stek ustida ishga tushirib O'LCHANDI.
 *
 * Tekshiruv baribir qoldirilgan: prefiks server tomonda bir kun olib
 * tashlansa qator raqami YO'QOLMASLIGI kerak — u xatoni topishning yagona
 * yo'li.
 */
function rowLine(issue) {
  const prefix = `${issue.row}-qator:`;
  const message = String(issue.message ?? issue.code ?? "");
  return message.startsWith(prefix) ? message : `${prefix} ${message}`;
}

/* -------------------------------------------------------------------------- */
/* Yordamchilar                                                                */
/* -------------------------------------------------------------------------- */

function basename(value) {
  const parts = value.split(/[\\/]/);
  return parts[parts.length - 1] || "import.xlsx";
}

function short(text) {
  const flat = (text ?? "").replace(/\s+/g, " ").trim();
  return flat.length > 300 ? `${flat.slice(0, 300)}…` : flat;
}

/**
 * Foydalanuvchiga ko'rsatiladigan xato — stek IZI KERAK EMAS.
 *
 * `printed: true` — xabar ALLAQACHON chiqarilgan (xato hisoboti kabi ko'p
 * qatorli holatlar), ya'ni yuqori qatlam uni QAYTA chiqarmaydi.
 */
class CliError extends Error {
  constructor(message, { printed = false } = {}) {
    super(message);
    this.name = "CliError";
    this.printed = printed;
  }
}

function fail(message) {
  throw new CliError(message);
}

/* -------------------------------------------------------------------------- */
/* main                                                                        */
/* -------------------------------------------------------------------------- */

async function main() {
  const { command, flags } = parseArgs(process.argv.slice(2));

  if (flags.has("help")) {
    console.log(USAGE);
    return;
  }
  if (command === null) {
    console.error(USAGE);
    throw new CliError("buyruq ko'rsatilmagan.");
  }
  if (command !== "template" && command !== "upload") {
    fail(`noma'lum buyruq: '${command}' (mumkin: template, upload). --help bilan ko'ring.`);
  }

  const env = readEnv();
  if (command === "template") await commandTemplate(env, flags);
  else await commandUpload(env, flags);
}

main().catch((error) => {
  if (error instanceof CliError) {
    if (!error.printed) console.error(`[karmana] ${error.message}`);
  } else {
    // Tarmoq uzilishi va boshqa kutilmagan holatlar — steki BILAN, chunki
    // bu skript ishlab chiqarish bazasiga yozadi va "nimadir bo'ldi"
    // xabari bilan qoldirish qabul qilib bo'lmaydigan holat.
    console.error("[karmana] kutilmagan xato:");
    console.error(error);
  }

  // ⚠ `process.exit(1)` EMAS — VA BU O'LCHANGAN. Windows'da quvurga
  // (`|`, CI jurnali) yozilayotgan stdio hali bo'shatilmagan paytda
  // `process.exit()` chaqirilsa libuv `Assertion failed:
  // !(handle->flags & UV_HANDLE_CLOSING)` bilan qulaydi va protsess
  // **127** kodi bilan tugaydi, `1` bilan emas. Ya'ni xato hisobotining
  // oxirgi qatorlari YO'QOLARDI va `&&` zanjiri/CI noto'g'ri kodni
  // ko'rardi. `exitCode` esa Node'ga stdio'ni bo'shatib, so'ng tabiiy
  // tugashga imkon beradi.
  process.exitCode = 1;
});
