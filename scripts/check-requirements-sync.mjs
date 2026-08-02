#!/usr/bin/env node
/**
 * `.planning/REQUIREMENTS.md` ning IKKI joyi bir xil haqiqatni aytayotganini
 * tekshiradi.
 *
 * NEGA KERAK: fayl har talabning holatini IKKI marta yozadi — yuqorida
 * `- [ ] **REQ-ID**: ...` ro'yxati, pastda `| REQ-ID | Phase N | Status |`
 * Traceability jadvali. Bittasini yangilab ikkinchisini unutish faylni ikki
 * xil haqiqat manbaiga aylantiradi va keyingi tekshiruvchi qaysi biriga
 * ishonishni bilmaydi. Birorta mavjud test bu ajralishni ushlamaydi:
 * `.planning/` katalogi kod darvozalaridan butunlay tashqarida.
 *
 * NIMA TEKSHIRILADI (ikki yo'nalishda):
 *   (a) ro'yxatdagi har ID jadvalda bor VA jadvaldagi har ID ro'yxatda bor;
 *   (b) `[x]` <-> `Done`, `[ ]` <-> `Pending` yoki `Blocked (<sabab>)`.
 *
 * Holat lug'ati ATAYIN uchta qiymat bilan chegaralangan. Sinonim
 * ("Complete", "Ready", "OK") ruxsat etilsa, skriptning butun maqsadi —
 * ikki joyning MEXANIK solishtirilishi — sekin-asta yemirilardi; noma'lum
 * qiymat shuning uchun xato deb sanaladi va ID bilan ko'rsatiladi.
 *
 * NIMA TEKSHIRILMAYDI VA NEGA: `**Coverage:**` bloki va `Faza kesimida`
 * jadvalidagi SANOQLAR. Ular bugun eskirgan — fayl `46` deydi, mazmunidan
 * hisoblanganda esa boshqa son chiqadi, chunki 2026-08-01 da qo'shilgan
 * uchta yangi talab bilan sanoqlar yangilanmagan. Ularni qayta hisoblash
 * `02-24` rejasining zimmasida. Bu skript ularni XATO deb sanamaydi (aks
 * holda u bugundan boshlab har doim qizil bo'lardi va hech kim ishlatmasdi),
 * lekin farqni har ishga tushganda OGOHLANTIRISH bilan ko'rsatadi — ya'ni
 * eskirgan son jimgina yashab qolmaydi.
 *
 * QO'LDA ISHLATILADI, DOIMIY CI DARVOZASI EMAS. `node --test` to'plamiga
 * ATAYIN ulanmagan: u har commit'da hali yozilmagan fazalarning `Pending`
 * qatorlarini qayta o'qib, hech qanday yangi ma'lumot bermasdi. Chaqirish
 * joyi — har faza yopilishi (traceability yangilanadigan yagona payt).
 *
 * Ishlatish:  node scripts/check-requirements-sync.mjs [fayl]
 * Chiqish:    0 — mos; 1 — mos emas (sabab stderr'da, AYNAN qaysi ID bilan).
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import process from "node:process";

const DEFAULT_FILE = path.join(
  import.meta.dirname,
  "..",
  ".planning",
  "REQUIREMENTS.md",
);

/** `- [x] **MARKET-01**: matn` */
const CHECKBOX_RE = /^- \[( |x)\] \*\*([A-Z][A-Z0-9]*-\d+)\*\*/u;

/** `| MARKET-01 | Phase 2 | Done |` */
const TABLE_RE =
  /^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|\s*Phase\s+(\d+)\s*\|\s*([^|]+?)\s*\|\s*$/u;

/** `- v1 requirements: 46 total` */
const COVERAGE_RE = /^-\s*v1 requirements:\s*(\d+)\s*total/u;

const STATUS_DONE = "Done";
const STATUS_PENDING = "Pending";
const STATUS_BLOCKED_RE = /^Blocked \(.+\)$/u;

function parse(source) {
  const list = new Map();
  const table = new Map();
  const duplicates = [];
  let coverage = null;

  source.split(/\r?\n/u).forEach((line, index) => {
    const lineNo = index + 1;

    const checkbox = CHECKBOX_RE.exec(line);
    if (checkbox) {
      const [, mark, id] = checkbox;
      if (list.has(id)) {
        duplicates.push(
          `${id}: ro'yxatda IKKI marta uchraydi (${list.get(id).lineNo} va ${lineNo}-qatorlar)`,
        );
      } else {
        list.set(id, { checked: mark === "x", lineNo });
      }
      return;
    }

    const row = TABLE_RE.exec(line);
    if (row) {
      const [, id, phase, status] = row;
      if (table.has(id)) {
        duplicates.push(
          `${id}: Traceability jadvalida IKKI marta uchraydi (${table.get(id).lineNo} va ${lineNo}-qatorlar)`,
        );
      } else {
        table.set(id, { phase, status, lineNo });
      }
      return;
    }

    const cov = COVERAGE_RE.exec(line);
    if (cov) {
      coverage = { total: Number(cov[1]), lineNo };
    }
  });

  return { list, table, duplicates, coverage };
}

function classify(status) {
  if (status === STATUS_DONE) return "done";
  if (status === STATUS_PENDING) return "pending";
  if (STATUS_BLOCKED_RE.test(status)) return "blocked";
  return "unknown";
}

function check(file) {
  const source = readFileSync(file, "utf8");
  const { list, table, duplicates, coverage } = parse(source);
  const errors = [...duplicates];

  if (list.size === 0) {
    errors.push(
      "Ro'yxatda birorta `- [ ] **REQ-ID**` bandi topilmadi — fayl formati o'zgargan bo'lishi mumkin",
    );
  }
  if (table.size === 0) {
    errors.push(
      "Traceability jadvalida birorta `| REQ-ID | Phase N | Status |` qatori topilmadi",
    );
  }

  // (a) ikki yo'nalishli mavjudlik
  for (const [id, entry] of list) {
    if (!table.has(id)) {
      errors.push(
        `${id}: ro'yxatda bor (${entry.lineNo}-qator), Traceability jadvalida YO'Q`,
      );
    }
  }
  for (const [id, entry] of table) {
    if (!list.has(id)) {
      errors.push(
        `${id}: Traceability jadvalida bor (${entry.lineNo}-qator), ro'yxatda YO'Q`,
      );
    }
  }

  // (b) checkbox <-> status
  const tally = { done: 0, pending: 0, blocked: 0 };
  for (const [id, entry] of list) {
    const row = table.get(id);
    if (!row) continue;

    const kind = classify(row.status);
    if (kind === "unknown") {
      errors.push(
        `${id}: jadvaldagi holat "${row.status}" tanilmadi (${row.lineNo}-qator) — ruxsat etilganlari: "${STATUS_DONE}", "${STATUS_PENDING}", "Blocked (<sabab>)"`,
      );
      continue;
    }
    tally[kind] += 1;

    if (entry.checked && kind !== "done") {
      errors.push(
        `${id}: ro'yxatda BELGILANGAN ([x], ${entry.lineNo}-qator), jadvalda esa "${row.status}" (${row.lineNo}-qator) — ikkisi bir xil narsani aytmayapti`,
      );
    }
    if (!entry.checked && kind === "done") {
      errors.push(
        `${id}: jadvalda "${STATUS_DONE}" (${row.lineNo}-qator), ro'yxatda esa BELGILANMAGAN ([ ], ${entry.lineNo}-qator) — ikkisi bir xil narsani aytmayapti`,
      );
    }
  }

  return { errors, total: list.size, tally, coverage };
}

const file = process.argv[2] ? path.resolve(process.argv[2]) : DEFAULT_FILE;
const { errors, total, tally, coverage } = check(file);

if (errors.length > 0) {
  process.stderr.write(
    `check-requirements-sync: ${errors.length} ta nomuvofiqlik — ${file}\n`,
  );
  for (const message of errors) {
    process.stderr.write(`  ✗ ${message}\n`);
  }
  process.exit(1);
}

/*
 * Sanoq FAYLNING O'Z MAZMUNIDAN olinadi, qattiq yozilgan sondan emas —
 * aks holda skriptning o'zi eskiradigan uchinchi haqiqat manbai bo'lardi.
 */
process.stdout.write(
  `check-requirements-sync: ${total} ta talab tekshirildi — ro'yxat va Traceability jadvali MOS.\n` +
    `  Done: ${tally.done} · Pending: ${tally.pending} · Blocked: ${tally.blocked}\n`,
);

if (coverage !== null && coverage.total !== total) {
  process.stdout.write(
    `  ⚠ OGOHLANTIRISH: "**Coverage:**" bloki ${coverage.total} deydi (${coverage.lineNo}-qator), ` +
      `mazmunidan hisoblanganda ${total} chiqdi. Bu XATO deb sanalmadi — sanoqlarni qayta hisoblash 02-24 rejasining zimmasida.\n`,
  );
}
