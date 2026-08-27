#!/usr/bin/env node
/**
 * FAZA DARVOZASI — ROADMAP Phase 9 ning BESHALA mezoni BITTA buyruqda
 * o'lchanadi (09-07, 08-20 `test_phase8_criteria.py` naqshining frontend
 * shakli).
 *
 * =============================================================================
 * BU MODUL NIMA VA NIMA EMAS.
 *
 * U MAVJUD DARVOZALARNI TAKRORLAMAYDI — u ularni ZANJIR sifatida bog'laydi
 * va yagona savol beradi: «ROADMAP dagi jumla bugun rostmi?» Har mezon
 * testida IKKI xil dalil bor:
 *
 *   (i)  MAHSULOT dalili — ROADMAP jumlasi da'vo qilgan narsaning kodda
 *        mavjudligi (`src/**` yoki `package.json`);
 *   (ii) ZANJIR dalili — o'sha da'voni O'LCHAYDIGAN test faylining
 *        mavjudligi VA uning CI glob'iga tushishi (`scripts/*.test.mjs`
 *        yoki `src/**​/*.test.tsx`).
 *
 * ⛔⛔ MAVJUD DARVOZALAR QAYTA YUGURTIRILMAYDI (`node --test` / `vitest`
 *    spawn YO'Q): `gate:fast` byudjeti 200 s — qayta ijro uni yeb
 *    qo'yardi. Spawn yo'qligi REYESTR NAZORATI testida MEXANIK
 *    tekshiriladi (o'z manbasida `child_process` 0).
 *
 * ⛔⛔ `.planning/` GA BOG'LANISH ATAYLAB VA FAQAT SHU MODULDA. Uning
 *    butun maqsadi — ROADMAP prozasi bilan kodni solishtirish. Boshqa
 *    darvozalar (`typography`, `motion-tokens`, …) `.planning/` ni
 *    O'QIMAYDI — kod darvozasini prozaga bog'lash uni hujjat tahririda
 *    jimgina buzardi (02-22 darsi). Bu modulda esa AYNAN o'sha bog'lanish
 *    mahsulot: ROADMAP jumlasi o'zgarsa, darvoza «qayta bog'la» deb
 *    qizarishi KERAK.
 *
 * ⛔ SOXTALASHTIRISH DARVOZASI: har mezon testining manbasida kamida
 *    bitta `src/` yoki `package.json` yo'li borligi modulning O'ZINI
 *    o'qib (`import.meta.filename`) tasdiqlanadi — «faqat konstantani
 *    qayta o'qib yashil bo'lish» mexanik imkonsiz (T-09-21).
 *
 * ⛔ CHEGARALAR IKKINCHI MARTA YOZILADI, IMPORT QILINMAYDI (05-15 darsi):
 *    `MIN_FORBIDDEN_NAMES` qiymati `collect-surface.test.mjs` MANBASIDAN
 *    regex bilan o'qiladi va SHU YERDAGI polga solishtiriladi — import
 *    darvozani o'zi tekshirayotgan qiymatga bog'lardi.
 *
 * ⚠ Tashqi paket YO'Q — sof matn skani (`node:` modullari xolos).
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const REPO_ROOT = path.join(FRONTEND_ROOT, "..");
const ROADMAP_PATH = path.join(REPO_ROOT, ".planning", "ROADMAP.md");

/* -------------------------------------------------------------------------- */
/* REYESTRLAR                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * SC#5 — `dependencies` TO'PLAM TENGLIGI reyestri (G-motion-3(d), L-8 0 KB).
 *
 * ⛔ `deepEqual`, SON EMAS: `length === 18` shakli paket ALMASHTIRILGANDA
 *    (biri chiqib, biri kirganda) yolg'on yashil qolardi. To'plam tengligi
 *    ikkalasini ham ushlaydi. Bu `motion-tokens.test.mjs` dagi tekshiruvning
 *    IKKINCHI, MUSTAQIL nusxasi (T-09-SC) — mahsulot konstantasidan import
 *    QILINMAYDI.
 */
const DEPENDENCY_REGISTRY = [
  "@hookform/resolvers",
  "@radix-ui/react-dialog",
  "@radix-ui/react-dropdown-menu",
  "@radix-ui/react-select",
  "@tanstack/react-query",
  "class-variance-authority",
  "clsx",
  "date-fns",
  "lucide-react",
  "next",
  "next-intl",
  "nuqs",
  "react",
  "react-dom",
  "react-hook-form",
  "sonner",
  "tailwind-merge",
  "zod",
];

/**
 * SC#5 — nomma-nom TAQIQLANGAN paketlar (dependencies HAM devDependencies).
 *
 * `deepEqual` qo'shilishni baribir ushlaydi; bu ro'yxat XATO XABARINI
 * aniq qiladi («qaysi vasvasa?») va dev-tomonni ham yopadi — animatsiya
 * kutubxonasi «faqat testda» ham kirmaydi.
 */
const FORBIDDEN_PACKAGES = [
  "motion",
  "framer-motion",
  "react-spring",
  "@react-spring/web",
  "gsap",
  "animejs",
  "lottie-react",
  "canvas-confetti",
  "react-confetti",
];

/**
 * SC#5 — regressiya nazorati chegaralari (POL, ko'chirma emas).
 *
 * ⛔ Qiymatlar `collect-surface.test.mjs` MANBASIDAN o'qiladi va shu
 *    pollarga solishtiriladi — chegarani tushirish (14 -> 10) AYNAN shu
 *    testni qizartiradi (T-09-04).
 */
const MIN_FORBIDDEN_NAMES_FLOOR = 14;
const MIN_BLIND_DECLARATION_TOKENS_FLOOR = 7;

/**
 * SC#5 — mavjud bo'lishi SHART bo'lgan darvoza fayllari («mavjud G-*
 * yashil qoladi» ning mavjudlik yarmi; yashilligini `gate` zanjirining
 * o'zi o'lchaydi — bu modul ularni qayta yugurtirmaydi).
 */
const SC5_GATE_FILES = [
  "scripts/motion-tokens.test.mjs",
  "scripts/collect-surface.test.mjs",
  "scripts/submit-gate.test.mjs",
  "scripts/role-gate.test.mjs",
  "scripts/forbidden-notice.test.mjs",
  "scripts/bulk-action-surface.test.mjs",
  "scripts/report-copy.test.mjs",
];

/**
 * META — mezon matni <-> test bog'lamining LANGARLARI. ROADMAP jumlasi
 * shu so'zni yo'qotadigan darajada o'zgarsa, bog'lam eskirgan — darvoza
 * qizaradi va odam qayta bog'laydi. Bu «jumla bugun rostmi?» savolining
 * teskari yo'nalishi.
 */
const CRITERION_ANCHORS = [
  /xoreografiya/iu,
  /skeleton/iu,
  /dark/iu,
  /prefers-reduced-motion/u,
  /transform/u,
];

/* -------------------------------------------------------------------------- */
/* YORDAMCHILAR                                                               */
/* -------------------------------------------------------------------------- */

/** Fayl MAVJUDLIGI alohida tasdiq — yo'q fayl «bo'sh satr» bo'lib yutilmaydi. */
function mustRead(absPath, label) {
  assert.ok(existsSync(absPath), `${label} TOPILMADI: ${absPath}`);
  return readFileSync(absPath, "utf8");
}

/** `frontend/` ildizidan nisbiy o'qish (mahsulot fayllari). */
function readProduct(rel) {
  return mustRead(path.join(FRONTEND_ROOT, rel), rel);
}

/**
 * ZANJIR dalili — vitest qatlami: fayl mavjud VA `src/**​/*.test.tsx`
 * glob'iga tushadi (`vitest.config.ts` include — 09-VALIDATION).
 */
function assertChainTsx(rel) {
  assert.ok(
    existsSync(path.join(FRONTEND_ROOT, rel)),
    `zanjir fayli TOPILMADI: ${rel}`,
  );
  assert.ok(
    rel.startsWith("src/") && rel.endsWith(".test.tsx"),
    `${rel} vitest glob'iga (src/**\u200b/*.test.tsx) tushmaydi — CI'da yugurmasdi`,
  );
}

/**
 * ZANJIR dalili — node:test qatlami: fayl mavjud VA `scripts/*.test.mjs`
 * glob'iga tushadi (bitta daraja — `frontend/package.json::test`).
 */
function assertChainMjs(rel) {
  assert.ok(
    existsSync(path.join(FRONTEND_ROOT, rel)),
    `zanjir fayli TOPILMADI: ${rel}`,
  );
  assert.match(
    rel,
    /^scripts\/[^/]+\.test\.mjs$/u,
    `${rel} node:test glob'iga (scripts/*.test.mjs) tushmaydi — CI'da yugurmasdi`,
  );
}

/**
 * Izohlarni olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 * ⛔ `bulk-action-surface.test.mjs:163-225` dan KO'CHIRILGAN NUSXA (W0-F4) —
 *    izohda yozilgan taqiq nomi darvozani qizartirmasin, satrdagisi esa
 *    qizartirsin.
 */
function stripComments(source) {
  let out = "";
  let state = "code";
  let i = 0;

  while (i < source.length) {
    const c = source[i];
    const next = source[i + 1];

    if (state === "code") {
      if (c === "/" && next === "/") {
        state = "line";
        i += 2;
      } else if (c === "/" && next === "*") {
        state = "block";
        i += 2;
      } else if (c === "'" || c === '"' || c === "`") {
        state = c;
        out += c;
        i += 1;
      } else {
        out += c;
        i += 1;
      }
      continue;
    }

    if (state === "line") {
      if (c === "\n") {
        state = "code";
        out += c;
      }
      i += 1;
      continue;
    }

    if (state === "block") {
      if (c === "*" && next === "/") {
        state = "code";
        i += 2;
      } else {
        if (c === "\n") out += c;
        i += 1;
      }
      continue;
    }

    if (c === "\\") {
      out += c + (next ?? "");
      i += 2;
      continue;
    }
    if (c === state) {
      state = "code";
    }
    out += c;
    i += 1;
  }

  return out;
}

/**
 * CSS scope blokini qavs balansi bilan ajratadi (`[data-theme="sun"] { … }`).
 * Selektor topilmasa yoki undan keyin `{` kelmasa `null` — chaqiruvchi
 * tasdiq XATO XABARI bilan yiqiladi. Izohda tilga olingan selektor blok
 * ochmagani uchun o'tkazib yuboriladi (keyingi haqiqiy scope izlanadi).
 */
function cssScopeBlock(css, selector) {
  let from = 0;
  for (;;) {
    const at = css.indexOf(selector, from);
    if (at === -1) return null;
    let i = at + selector.length;
    while (i < css.length && /\s/u.test(css[i])) i += 1;
    if (css[i] === "{") {
      let depth = 0;
      for (let j = i; j < css.length; j += 1) {
        if (css[j] === "{") depth += 1;
        if (css[j] === "}") {
          depth -= 1;
          if (depth === 0) return css.slice(i + 1, j);
        }
      }
      return null;
    }
    from = at + selector.length;
  }
}

/** ROADMAP `### Phase 9` bo'limidan Success Criteria ro'yxatini oladi. */
function parseCriteria() {
  const roadmap = mustRead(ROADMAP_PATH, ".planning/ROADMAP.md");
  const start = roadmap.indexOf("### Phase 9");
  assert.ok(start !== -1, "ROADMAP'da `### Phase 9` bo'limi topilmadi");

  const rest = roadmap.slice(start);
  const nextHeading = rest.indexOf("\n### ", 1);
  const section = nextHeading === -1 ? rest : rest.slice(0, nextHeading);

  const marker = section.indexOf("**Success Criteria**");
  assert.ok(marker !== -1, "`**Success Criteria**` sarlavhasi topilmadi");

  const lines = section.slice(marker).split(/\r?\n/u).slice(1);
  const criteria = [];
  for (const line of lines) {
    const m = /^\s*(\d+)\.\s+(.+)$/u.exec(line);
    if (m) {
      criteria.push({ n: Number(m[1]), text: m[2].trim() });
      continue;
    }
    /* Ro'yxat boshlanmasidan oldingi bo'sh qatordan o'tiladi; boshlangach
     * BIRINCHI bo'sh/begona qator ro'yxatni yopadi — pastdagi «Chegaralar»
     * bo'limining raqamli bandlari mezon emas va yutilmaydi. */
    if (criteria.length === 0 && line.trim() === "") continue;
    break;
  }
  return criteria;
}

/* -------------------------------------------------------------------------- */
/* BESH MEZON                                                                 */
/* -------------------------------------------------------------------------- */

test("SC#1 — kassir 6-qadam xoreografiyasi bloklamaydi: mexanika mahsulotda, o'lchov zanjirda", () => {
  /* (i) MAHSULOT: xoreografiya moduli — imperativ, holatga tegmaydigan. */
  const choreo = stripComments(
    readProduct("src/components/collect/success-choreography.tsx"),
  );
  assert.ok(
    !/\buseState\b/u.test(choreo),
    "success-choreography.tsx da `useState` paydo bo'lgan — imperativ (holatsiz) shartnoma buzilgan (G-motion-2(d) asosi)",
  );
  assert.ok(
    !choreo.includes("</") && !choreo.includes("/>"),
    "success-choreography.tsx da JSX paydo bo'lgan — klon React daraxtidan TASHQARIDA yashashi shart (M-9 unmount'idan omon qolish)",
  );
  assert.match(
    choreo,
    /style\.pointerEvents\s*=\s*"none"/u,
    "klonning `pointer-events` INLINE berilmagan — jsdom sinfni o'qimaydi, T-09-05 (klon bosishni yutmaydi) o'lchovsiz qolardi",
  );

  /* (i) MAHSULOT: ulanish tartibi — focus()dan KEYIN va await'siz. */
  const session = stripComments(
    readProduct("src/components/collect/collect-session.tsx"),
  );
  const focusAt = session.indexOf("inputRef.current?.focus()");
  const flyAt = session.indexOf("flyAmountToList({");
  assert.ok(focusAt !== -1, "collect-session.tsx da `inputRef.current?.focus()` topilmadi");
  assert.ok(flyAt !== -1, "collect-session.tsx da xoreografiya chaqiruvi (`flyAmountToList({`) topilmadi");
  assert.ok(
    flyAt > focusAt,
    "xoreografiya `focus()`dan OLDIN chaqirilgan — fixed klon scroll-anchoring'ni buzib inputni ekrandan chiqarishi mumkin (09-UI-SPEC §8.3 tartib SHARTNOMA)",
  );
  assert.ok(
    !/await\s+flyAmountToList/u.test(session),
    "xoreografiya `await` bilan chaqirilgan — bayram oqimni KUTDIRMAYDI (G-motion-2(a,b))",
  );

  /* (ii) ZANJIR: bloklamaslikni o'lchaydigan testlar mavjud va CI glob'ida. */
  assertChainTsx("src/components/collect/success-choreography.test.tsx");
  assertChainTsx("src/components/collect/collect-session.test.tsx");
});

test("SC#2 — direktor jonlanishi: skeleton/stagger/count-up/sparkline-donut mahsulotda, zanjiri mavjud", () => {
  /* (i) MAHSULOT: ikkala karta skeleton bilan ochiladi, spinner YO'Q,
   *     stagger kirish sinfi bor. */
  for (const rel of [
    "src/components/dashboard/revenue-card.tsx",
    "src/components/dashboard/occupancy-donut.tsx",
  ]) {
    const src = stripComments(readProduct(rel));
    assert.ok(/\bSkeleton\b/u.test(src), `${rel}: \`Skeleton\` ishlatilmagan — pending holat spinner emas, skeleton (ROADMAP SC#2)`);
    assert.ok(
      !src.includes("animate-spin"),
      `${rel}: \`animate-spin\` topildi — dashboard'da spinner TAQIQ (skeleton o'rnini bosadi)`,
    );
    assert.ok(
      src.includes("motion-enter"),
      `${rel}: \`.motion-enter\` stagger kirish sinfi yo'q — kartalar stagger bilan kirmaydi`,
    );
  }

  /* (i) MAHSULOT: count-up hook'i mavjud va bosh ko'rsatkich uni ishlatadi. */
  assert.ok(
    existsSync(path.join(FRONTEND_ROOT, "src/lib/use-count-up.ts")),
    "src/lib/use-count-up.ts TOPILMADI — tushum count-up bilan sanamaydi",
  );
  const headline = stripComments(
    readProduct("src/components/headline/headline-card.tsx"),
  );
  assert.ok(
    /\buseCountUp\(/u.test(headline),
    "headline-card.tsx `useCountUp(` ni chaqirmaydi — ROADMAP «tushum count-up bilan sanaydi» da'vosi uzilgan",
  );

  /* (ii) ZANJIR: dashboard huquq darvozasi va headline testlari. */
  assertChainTsx("src/app/[locale]/(app)/dashboard/page.test.tsx");
  assertChainTsx("src/components/headline/headline-card.test.tsx");
});

test("SC#3 — uch tema token-almashtirish bilan: scope'lar, FOUC skripti, ThemeToggle; zanjiri mavjud", () => {
  /* (i) MAHSULOT: uchala tema `globals.css` da — bazaviy @theme (iliq fon,
   *     :root ga kompilyatsiya bo'ladi) + dark + sun scope'lari, har birida
   *     o'z `--color-bg` i (token-almashtirish = komponent kodi o'zgarmaydi). */
  const css = readProduct("src/app/globals.css");
  assert.ok(css.includes("@theme"), "globals.css da `@theme` bazaviy token bloki yo'q");
  const themeAt = css.indexOf("@theme");
  const themeBlock = cssScopeBlock(css.slice(themeAt), "@theme");
  assert.ok(
    themeBlock !== null && themeBlock.includes("--color-bg:"),
    "bazaviy @theme blokida `--color-bg` yo'q — iliq fon manbasiz",
  );
  for (const scope of ['[data-theme="dark"]', '[data-theme="sun"]']) {
    const block = cssScopeBlock(css, scope);
    assert.ok(block !== null, `globals.css da \`${scope}\` scope bloki TOPILMADI`);
    assert.ok(
      block.includes("--color-bg:"),
      `\`${scope}\` bloki \`--color-bg\` ni almashtirmaydi — tema token-almashtirish emas`,
    );
  }

  /* (i) MAHSULOT: FOUC'siz yuklanish — bloklovchi inline skript. */
  const layout = stripComments(readProduct("src/app/[locale]/layout.tsx"));
  assert.ok(
    layout.includes("suppressHydrationWarning"),
    "layout.tsx da `suppressHydrationWarning` yo'q — inline skript o'zgartirgan atributni React qaytarib qo'yardi",
  );
  assert.ok(
    layout.includes("dangerouslySetInnerHTML"),
    "layout.tsx da inline tema skripti yo'q — saqlangan tema birinchi bo'yashdan keyin qo'llanardi (FOUC)",
  );
  assert.ok(
    layout.includes("sbozor-theme"),
    "inline skript `sbozor-theme` localStorage kalitini o'qimaydi",
  );

  /* (i) MAHSULOT: tugma foydalanuvchiga chiqarilgan (import emas — JSX mount). */
  const shell = stripComments(readProduct("src/components/shell/app-shell.tsx"));
  assert.ok(
    shell.includes("<ThemeToggle"),
    "app-shell.tsx da `<ThemeToggle` mount qilinmagan — tema tugmasi foydalanuvchiga ko'rinmaydi",
  );

  /* (ii) ZANJIR: scope tengligi va kontrast reyestri darvozalari. */
  assertChainMjs("scripts/theme-tokens.test.mjs");
  assertChainMjs("scripts/contrast.test.mjs");
});

test("SC#4 — reduced-motion va ≤150ms testda o'lchanadi: global blok mahsulotda, o'lchovlar zanjirda", () => {
  /* (i) MAHSULOT: global reduced-motion bloki (G-motion-1(a) birinchi qatlami). */
  const css = readProduct("src/app/globals.css");
  assert.ok(
    css.includes("@media (prefers-reduced-motion: reduce)"),
    "globals.css da global `@media (prefers-reduced-motion: reduce)` bloki yo'q",
  );

  /* (ii) ZANJIR: G-motion-1 — CSS blokni PARSE qiladigan darvoza. */
  assertChainMjs("scripts/motion-tokens.test.mjs");
  const motionGate = mustRead(
    path.join(FRONTEND_ROOT, "scripts/motion-tokens.test.mjs"),
    "scripts/motion-tokens.test.mjs",
  );
  assert.ok(
    motionGate.includes("prefers-reduced-motion"),
    "motion-tokens.test.mjs `prefers-reduced-motion` ni tasdiqlamaydi — G-motion-1 zanjiri uzilgan",
  );

  /* (ii) ZANJIR: G-motion-2 — matchMedia stubi (klon shoxi) va 150ms o'lchovi.
   * ⚠ 150ms o'lchovi `collect-session.test.tsx` da yashaydi (G-motion-2(a,b)
   *   egasi, 09-04) — reja matni `success-choreography.test.tsx` degan edi,
   *   haqiqiy joy SUMMARY'da deviatsiya sifatida yozilgan. */
  const choreoTest = readProduct(
    "src/components/collect/success-choreography.test.tsx",
  );
  assert.ok(
    choreoTest.includes('stubGlobal("matchMedia"'),
    "success-choreography.test.tsx da `matchMedia` stubi yo'q — reduced-motion shoxi o'lchovsiz",
  );
  const sessionTest = readProduct(
    "src/components/collect/collect-session.test.tsx",
  );
  assert.ok(
    sessionTest.includes("advanceTimersByTimeAsync(150)"),
    "collect-session.test.tsx da 150ms nuqtasi o'lchovi yo'q — «input ~150ms da tayyor» da'vosi zanjirisiz",
  );
});

test("SC#5 — GPU-only motion va 0 KB byudjet: dependencies reyestrga TENG, regressiya chegaralari kamaymagan", () => {
  /* (i) MAHSULOT: `package.json` dependencies TO'PLAM TENGLIGI (T-09-SC). */
  const pkg = JSON.parse(
    mustRead(path.join(FRONTEND_ROOT, "package.json"), "frontend/package.json"),
  );
  assert.deepEqual(
    Object.keys(pkg.dependencies ?? {}).sort(),
    [...DEPENDENCY_REGISTRY].sort(),
    "frontend dependencies 18 nomli reyestrga teng emas — motion 0 KB da'vosi (L-8) buzilgan",
  );
  const installed = { ...pkg.dependencies, ...pkg.devDependencies };
  for (const name of FORBIDDEN_PACKAGES) {
    assert.ok(
      !(name in installed),
      `TAQIQLANGAN paket o'rnatilgan: \`${name}\` — motion faqat CSS/vanilla (09-UI-SPEC §3.2)`,
    );
  }

  /* (ii) ZANJIR + REGRESSIYA NAZORATI: ko'r deklaratsiya chegaralari
   *     KAMAYMAGAN — qiymatlar collect-surface MANBASIDAN o'qiladi
   *     (import EMAS — 05-15 darsi). */
  const surface = mustRead(
    path.join(FRONTEND_ROOT, "scripts/collect-surface.test.mjs"),
    "scripts/collect-surface.test.mjs",
  );
  const forbidden = /const MIN_FORBIDDEN_NAMES = (\d+);/u.exec(surface);
  assert.ok(
    forbidden !== null && Number(forbidden[1]) >= MIN_FORBIDDEN_NAMES_FLOOR,
    `collect-surface.test.mjs::MIN_FORBIDDEN_NAMES ${forbidden ? `= ${forbidden[1]}` : "topilmadi"} — ` +
      `${MIN_FORBIDDEN_NAMES_FLOOR} dan KAMAYTIRISH TAQIQ (T-09-04: ko'r deklaratsiya regressiyasi)`,
  );
  const blind = /const MIN_BLIND_DECLARATION_TOKENS = (\d+);/u.exec(surface);
  assert.ok(
    blind !== null && Number(blind[1]) >= MIN_BLIND_DECLARATION_TOKENS_FLOOR,
    `collect-surface.test.mjs::MIN_BLIND_DECLARATION_TOKENS ${blind ? `= ${blind[1]}` : "topilmadi"} — ` +
      `${MIN_BLIND_DECLARATION_TOKENS_FLOOR} dan KAMAYTIRISH TAQIQ`,
  );

  /* (ii) ZANJIR: «mavjud G-* yashil qoladi» ning mavjudlik yarmi — yettala
   *     darvoza fayli joyida (yashilligini `gate` zanjirining o'zi beradi). */
  for (const rel of SC5_GATE_FILES) assertChainMjs(rel);
});

/* -------------------------------------------------------------------------- */
/* META-TEST — ROADMAP <-> MODUL BOG'LAMI                                     */
/* -------------------------------------------------------------------------- */

test("META — ROADMAP'dan AYNAN 5 mezon parse bo'ladi, modulda AYNAN 5 mezon testi bor va zanjir CI'da yuguradi", () => {
  const criteria = parseCriteria();
  assert.equal(
    criteria.length,
    5,
    `ROADMAP Phase 9 Success Criteria ${criteria.length} band — reyestr AYNAN 5 bo'lishi shart (to'rttasi ham, oltitasi ham qizil)`,
  );
  assert.deepEqual(
    criteria.map((c) => c.n),
    [1, 2, 3, 4, 5],
    "mezonlar 1..5 raqamlangan bo'lishi shart",
  );

  /* Har mezon jumlasi o'z langar so'zini tashiydi — jumla shu darajada
   * o'zgarsa, test-bog'lam ESKIRGAN va qayta bog'lash odamniki. */
  criteria.forEach((criterion, index) => {
    assert.match(
      criterion.text,
      CRITERION_ANCHORS[index],
      `SC#${criterion.n} jumlasi langarini yo'qotgan (${CRITERION_ANCHORS[index]}) — test-bog'lamni qayta ko'rib chiqing`,
    );
  });

  /* Modulning o'zida AYNAN 5 mezon testi — har mezon uchun bittadan. */
  const self = readFileSync(import.meta.filename, "utf8");
  const scTests = [...self.matchAll(/^test\("SC#(\d)/gmu)].map((m) => Number(m[1]));
  assert.equal(
    scTests.length,
    criteria.length,
    `modulda ${scTests.length} mezon testi bor, ROADMAP esa ${criteria.length} mezon aytadi — har mezonga AYNAN bitta test`,
  );
  assert.deepEqual(
    [...scTests].sort(),
    [1, 2, 3, 4, 5],
    "SC#1..SC#5 ning har biri AYNAN bir marta — takror ham, tuynuk ham yo'q",
  );

  /* ZANJIR CI'DA YUGURADI: root `gate` frontend testini chaqiradi, frontend
   * `test` esa shu modul yashaydigan globni yuguradi. */
  const rootPkg = JSON.parse(
    mustRead(path.join(REPO_ROOT, "package.json"), "root package.json"),
  );
  assert.ok(
    rootPkg.scripts.gate.includes("npm --prefix frontend test"),
    "root `gate` zanjirida `npm --prefix frontend test` yo'q — bu modul CI'da yugurmasdi",
  );
  const fePkg = JSON.parse(
    mustRead(path.join(FRONTEND_ROOT, "package.json"), "frontend/package.json"),
  );
  assert.ok(
    fePkg.scripts.test.includes("node --test scripts/*.test.mjs"),
    "frontend `test` skripti `scripts/*.test.mjs` globini yugurtirmaydi",
  );
  assert.ok(
    fePkg.scripts.test.includes("vitest run"),
    "frontend `test` skripti vitest'ni yugurtirmaydi — .test.tsx zanjiri CI'dan tushib qolardi",
  );
});

/* -------------------------------------------------------------------------- */
/* SOXTALASHTIRISH DARVOZASI                                                  */
/* -------------------------------------------------------------------------- */

test("SOXTALASHTIRISH — har mezon testi kamida bitta MAHSULOT yo'liga murojaat qiladi", () => {
  const self = readFileSync(import.meta.filename, "utf8");
  for (const n of [1, 2, 3, 4, 5]) {
    const startIdx = self.indexOf(`test("SC#${n}`);
    assert.ok(startIdx !== -1, `SC#${n} test bloki topilmadi`);
    const nextIdx = self.indexOf('\ntest("', startIdx + 1);
    const block = nextIdx === -1 ? self.slice(startIdx) : self.slice(startIdx, nextIdx);
    assert.ok(
      block.includes("src/") || block.includes("package.json"),
      `SC#${n} bloki mahsulot fayliga (src/ yoki package.json) murojaat qilmaydi — ` +
        "«faqat konstantani qayta o'qib yashil bo'lish» taqiqlangan (T-09-21)",
    );
  }
});

/* -------------------------------------------------------------------------- */
/* REYESTR NAZORATI                                                           */
/* -------------------------------------------------------------------------- */

test("REYESTR NAZORATI — takror yo'q, quyi chegaralar joyida, modul hech narsani spawn qilmaydi", () => {
  const registries = {
    DEPENDENCY_REGISTRY,
    FORBIDDEN_PACKAGES,
    SC5_GATE_FILES,
    CRITERION_ANCHORS: CRITERION_ANCHORS.map(String),
  };
  for (const [name, list] of Object.entries(registries)) {
    assert.equal(
      new Set(list).size,
      list.length,
      `${name} da takror bor — reyestr to'plam bo'lishi shart`,
    );
    assert.ok(list.length > 0, `${name} bo'sh — reyestr ma'nosiz`);
  }
  assert.equal(
    DEPENDENCY_REGISTRY.length,
    18,
    "dependencies reyestri aynan 18 nom (09-UI-SPEC §3.2 holati) — o'zgargan bo'lsa, sabab bilan yangilang",
  );
  assert.equal(CRITERION_ANCHORS.length, 5, "langar reyestri mezon soniga teng");
  assert.ok(
    MIN_FORBIDDEN_NAMES_FLOOR >= 14 && MIN_BLIND_DECLARATION_TOKENS_FLOOR >= 7,
    "pol qiymatlarini tushirish TAQIQ — regressiya nazorati bo'shashtirildi",
  );

  /* ⛔ Modul mavjud darvozalarni QAYTA YUGURTIRMAYDI — spawn moduli
   * umuman import qilinmaydi. Token dinamik quriladi, aks holda shu
   * satrning o'zi (satr literallari saqlanadi) darvozani qizartirardi. */
  const spawnModule = ["child", "process"].join("_");
  const execToken = ["exec", "Sync"].join("");
  const selfStripped = stripComments(readFileSync(import.meta.filename, "utf8"));
  assert.ok(
    !selfStripped.includes(spawnModule),
    "modul spawn modulini import qilmoqda — darvozalarni qayta yugurtirish TAQIQ (gate:fast byudjeti)",
  );
  assert.ok(
    !selfStripped.includes(`${execToken}(`),
    "modul sinxron spawn chaqirmoqda — darvozalarni qayta yugurtirish TAQIQ",
  );
});
