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
 * NIMA TEKSHIRILADI:
 *   (a) ro'yxatdagi har ID jadvalda bor VA jadvaldagi har ID ro'yxatda bor;
 *   (b) `[x]` <-> `Done`, `[ ]` <-> `Pending` yoki `Blocked (<sabab>)`;
 *   (c) `ROADMAP.md` ning FAZA ro'yxati <-> uning O'Z holat jadvali;
 *   (d) YOPILGAN faza <-> o'sha fazaning talablarida `Pending` YO'Q;
 *   (e) `STATE.md` ning `completed_phases` sanog'i <-> ROADMAP'da
 *       HAQIQATAN yopilgan fazalar soni.
 *
 * ⛔⛔ (c) VA (d) 2026-08-20 DA QO'SHILDI VA SABABI O'LCHANGAN NUQSON.
 *
 *   `FOUND-01…05` REQUIREMENTS'da `Pending`, ROADMAP'da esa fazasi
 *   `[x] completed` edi — ikki fayl BIR YIL davomida ikki xil haqiqat
 *   aytishi mumkin edi. Bu skript uni USHLAMAGAN va ushlay olmasdi:
 *   u faqat REQUIREMENTS'ning ichini ko'rardi, ikkalasida ham
 *   `Pending` turgan — **izchil, lekin izchil ravishda NOTO'G'RI**.
 *
 *   O'sha kuni ROADMAP'ning O'Z ichida ham uchta yolg'on qator topildi
 *   (1-faza «Planned 0/10», 2-faza «Planned 0/17», 3-faza «11/11»
 *   o'rniga 14/14) va 9 bilan 10-faza jadvalda umuman yo'q edi.
 *
 *   ⛔ SHUNING UCHUN (d) `Pending` NI TAQIQLAYDI, `Blocked` NI EMAS:
 *      `Blocked` — «dalil to'liq emas va yetishmayotgani NOMLANGAN»,
 *      ya'ni ONGLI hukm. `Pending` esa «hukm umuman yozilmagan» —
 *      yopilgan fazada bu holat mumkin emas.
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
 * ⚠ (d) FAQAT YOPILGAN FAZALARNI tekshiradi. Ochiq fazaning `Pending`
 *   talabi — normal holat va u XATO deb sanalmaydi, aks holda skript
 *   loyihaning boshidan oxirigacha qizil bo'lardi.
 *
 * ⛔⛔ 2026-08-20 DA (c)/(d)/(e) QO'SHILGACH BU SKRIPT «har faza
 *     yopilishida» dan «har hujjat tegilganda» ga o'tdi: u endi
 *     TO'RT faylni solishtiradi va uchtasida ham o'sha kuni haqiqiy
 *     yolg'on topildi. Chaqirish: `npm run requirements:check`.
 *
 * QO'LDA ISHLATILADI, DOIMIY CI DARVOZASI EMAS. `node --test` to'plamiga
 * ATAYIN ulanmagan: u har commit'da hali yozilmagan fazalarning `Pending`
 * qatorlarini qayta o'qib, hech qanday yangi ma'lumot bermasdi. Chaqirish
 * joyi — har faza yopilishi (traceability yangilanadigan yagona payt).
 *
 * Ishlatish:  node scripts/check-requirements-sync.mjs [fayl] [roadmap]
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

const DEFAULT_ROADMAP = path.join(
  import.meta.dirname,
  "..",
  ".planning",
  "ROADMAP.md",
);

const DEFAULT_STATE = path.join(
  import.meta.dirname,
  "..",
  ".planning",
  "STATE.md",
);

/**
 * `  completed_phases: 10` — `STATE.md` frontmatter'idan.
 *
 * ⛔ FAQAT SHU BITTA MAYDON tekshiriladi, butun `progress` bloki emas.
 *   `total_plans`/`completed_plans` reja fayllarini SANASHNI talab
 *   qiladi va u boshqa savol; bu skriptning mavzusi — «nechta faza
 *   yopilgan?» degan savolga to'rt fayl BIR XIL javob beryaptimi.
 */
const STATE_COMPLETED_RE = /^\s*completed_phases:\s*(\d+)\s*$/u;

/** `- [x] **MARKET-01**: matn` */
const CHECKBOX_RE = /^- \[( |x)\] \*\*([A-Z][A-Z0-9]*-\d+)\*\*/u;

/** `| MARKET-01 | Phase 2 | Done |` */
const TABLE_RE =
  /^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|\s*Phase\s+(\d+)\s*\|\s*([^|]+?)\s*\|\s*$/u;

/** `- [x] **Phase 3: NVR ...** - matn` */
const PHASE_CHECKBOX_RE = /^- \[( |x)\] \*\*Phase (\d+):/u;

/**
 * `| 3. NVR ... | 14/14 | Complete | 2026-08-03 |`
 *
 * ⚠ Holat ustuni ERKIN matn: 4 va 5-fazalar «Tekshirildi (human_needed
 *   — …)» deb yozilgan va bu ATAYIN — ular yopilgan, lekin qo'lda
 *   bajariladigan bandlari bor. Shuning uchun bu yerda «yopilganmi?»
 *   savoli ochiq ro'yxat bilan emas, YOPILMAGAN qiymatlar ro'yxati
 *   bilan hal qilinadi (pastdagi `OPEN_PHASE_STATUSES`).
 */
const PHASE_ROW_RE =
  /^\|\s*(\d+)\.\s[^|]*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$/u;

/** Faza HALI YOPILMAGAN degan holatlar — qolgani yopilgan deb o'qiladi. */
const OPEN_PHASE_STATUSES = new Set(["Not started", "Planned", "In Progress"]);

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

/**
 * `ROADMAP.md` dan fazalarni o'qiydi — IKKI manbadan.
 *
 * ⛔ Ikkalasi ham qaytariladi va SOLISHTIRILADI: ro'yxat («- [x] **Phase
 *    N**») odam yozadigan joy, jadval esa hisobot uchun. Ular ajralib
 *    ketishi 2026-08-20 da o'lchandi — uchta qatorda.
 */
function parseRoadmap(source) {
  const checkboxes = new Map();
  const rows = new Map();

  source.split(/\r?\n/u).forEach((line, index) => {
    const lineNo = index + 1;

    const box = PHASE_CHECKBOX_RE.exec(line);
    if (box) {
      const [, mark, phase] = box;
      if (!checkboxes.has(phase)) {
        checkboxes.set(phase, { checked: mark === "x", lineNo });
      }
      return;
    }

    const row = PHASE_ROW_RE.exec(line);
    if (row) {
      const [, phase, plans, status, completed] = row;
      /*
       * ⛔ Sarlavha qatori (`| Phase | Plans Complete | ... |`) va
       *   ajratgich (`|---|`) bu regexga TUSHMAYDI, chunki birinchi
       *   ustun `<son>.` bilan boshlanishi SHART. Boshqa jadvallardagi
       *   raqamli qatorlar esa `phases` to'plamida takrorlanmaydi.
       */
      if (!rows.has(phase)) {
        rows.set(phase, { plans, status, completed, lineNo });
      }
    }
  });

  return { checkboxes, rows };
}

/** `STATE.md` dan `completed_phases` ni o'qiydi (topilmasa `null`). */
function parseState(source) {
  for (const [index, line] of source.split(/\r?\n/u).entries()) {
    const match = STATE_COMPLETED_RE.exec(line);
    if (match) return { completed: Number(match[1]), lineNo: index + 1 };
  }
  return null;
}

function phaseIsClosed(status) {
  return !OPEN_PHASE_STATUSES.has(status.trim());
}

function classify(status) {
  if (status === STATUS_DONE) return "done";
  if (status === STATUS_PENDING) return "pending";
  if (STATUS_BLOCKED_RE.test(status)) return "blocked";
  return "unknown";
}

function check(file, roadmapFile, stateFile) {
  const source = readFileSync(file, "utf8");
  const { list, table, duplicates, coverage } = parse(source);
  const { checkboxes, rows } = parseRoadmap(readFileSync(roadmapFile, "utf8"));
  const state = parseState(readFileSync(stateFile, "utf8"));
  const errors = [...duplicates];

  if (checkboxes.size === 0) {
    errors.push(
      "ROADMAP'da birorta `- [ ] **Phase N:**` bandi topilmadi — fayl formati o'zgargan bo'lishi mumkin",
    );
  }

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

  // (c) ROADMAP ning O'Z ichidagi izchillik: ro'yxat <-> holat jadvali
  for (const [phase, box] of checkboxes) {
    const row = rows.get(phase);
    if (!row) {
      errors.push(
        `Phase ${phase}: ro'yxatda bor (${box.lineNo}-qator), ROADMAP holat jadvalida YO'Q`,
      );
      continue;
    }
    const closed = phaseIsClosed(row.status);
    if (box.checked && !closed) {
      errors.push(
        `Phase ${phase}: ro'yxatda YOPILGAN ([x], ${box.lineNo}-qator), holat jadvalida esa "${row.status}" (${row.lineNo}-qator)`,
      );
    }
    if (!box.checked && closed) {
      errors.push(
        `Phase ${phase}: holat jadvalida "${row.status}" (${row.lineNo}-qator), ro'yxatda esa BELGILANMAGAN ([ ], ${box.lineNo}-qator)`,
      );
    }
  }

  /*
   * (d) YOPILGAN FAZADA `Pending` TALAB QOLMASIN.
   *
   * ⛔⛔ AYNAN SHU TEKSHIRUV 2026-08-20 GACHA YO'Q EDI va `FOUND-01…05`
   *     shu teshikdan o'tib ketgan: fazasi `[x] completed`, talablari
   *     esa `Pending` — ikki fayl ikki xil haqiqat aytardi.
   *
   * ⛔ `Blocked` bu yerda XATO EMAS: u «dalil to'liq emas va
   *    yetishmayotgani NOMLANGAN» degan ONGLI hukm. `Pending` esa
   *    «hukm umuman yozilmagan».
   */
  const closedPhases = new Set(
    [...checkboxes]
      .filter(([, box]) => box.checked)
      .map(([phase]) => phase),
  );
  for (const [id, row] of table) {
    if (!closedPhases.has(row.phase)) continue;
    if (classify(row.status) !== "pending") continue;
    const box = checkboxes.get(row.phase);
    errors.push(
      `${id}: Phase ${row.phase} ROADMAP'da YOPILGAN (${box.lineNo}-qator), talab esa "Pending" (${row.lineNo}-qator) — ` +
        "yopilgan fazada hukm yozilmagan talab qolmasligi kerak (`Done` yoki `Blocked (<sabab>)`)",
    );
  }

  /*
   * (e) `STATE.md` ning sanog'i ROADMAP bilan mos kelsin.
   *
   * ⛔⛔ 2026-08-20 da o'lchandi: `STATE.md` «Phase 10 · Not started ·
   *     Ready to execute» deb turgan, holbuki o'sha fazaning sakkizala
   *     rejasi ham uch kun oldin `SUMMARY` bilan yopilgan. Sanoq esa
   *     TASODIFAN to'g'ri edi (10) — ya'ni bu tekshiruv o'shanda
   *     qizarmasdi va u yolg'iz YETARLI emas. Shunga qaramay qoladi:
   *     u eng ARZON va eng tez eskiradigan raqamni qo'riqlaydi.
   */
  if (state === null) {
    errors.push("STATE.md da `completed_phases:` maydoni topilmadi");
  } else {
    const closedCount = [...checkboxes].filter(([, box]) => box.checked).length;
    if (state.completed !== closedCount) {
      errors.push(
        `STATE.md: \`completed_phases: ${state.completed}\` (${state.lineNo}-qator), ` +
          `ROADMAP'da esa ${closedCount} ta faza yopilgan`,
      );
    }
  }

  return { errors, total: list.size, tally, coverage, phases: checkboxes.size };
}

const file = process.argv[2] ? path.resolve(process.argv[2]) : DEFAULT_FILE;
const roadmap = process.argv[3] ? path.resolve(process.argv[3]) : DEFAULT_ROADMAP;
const stateFile = process.argv[4] ? path.resolve(process.argv[4]) : DEFAULT_STATE;
const { errors, total, tally, coverage, phases } = check(file, roadmap, stateFile);

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
  `check-requirements-sync: ${total} ta talab · ${phases} ta faza — to'rtala manba MOS.\n` +
    `  Done: ${tally.done} · Pending: ${tally.pending} · Blocked: ${tally.blocked}\n`,
);

if (coverage !== null && coverage.total !== total) {
  process.stdout.write(
    `  ⚠ OGOHLANTIRISH: "**Coverage:**" bloki ${coverage.total} deydi (${coverage.lineNo}-qator), ` +
      `mazmunidan hisoblanganda ${total} chiqdi. Bu XATO deb sanalmadi — sanoqlarni qayta hisoblash 02-24 rejasining zimmasida.\n`,
  );
}
