#!/usr/bin/env node
/**
 * FAZA DARVOZASI — ROADMAP Phase 10 ning BESHALA mezoni BITTA buyruqda
 * o'lchanadi (10-08; naqsh manbai `phase9-criteria.test.mjs`, u esa 09-07
 * va 08-20 `test_phase8_criteria.py` presedentlaridan).
 *
 * =============================================================================
 * BU MODUL NIMA VA NIMA EMAS.
 *
 * U MAVJUD DARVOZALARNI TAKRORLAMAYDI — u ularni ZANJIR sifatida bog'laydi
 * va yagona savol beradi: «ROADMAP dagi jumla bugun rostmi?» Har mezon
 * testida IKKI xil dalil bor:
 *
 *   (i)  MAHSULOT dalili — ROADMAP jumlasi da'vo qilgan narsaning kodda
 *        mavjudligi (`src/**`, `services/**`, `tests/**` yoki
 *        `package.json`);
 *   (ii) ZANJIR dalili — o'sha da'voni O'LCHAYDIGAN test faylining
 *        mavjudligi VA uning CI glob'iga tushishi (`scripts/*.test.mjs`,
 *        `src/**​/*.test.tsx` yoki backend `tests/integration/*.py` —
 *        oxirgisi 10-fazaning YANGILIGI: anonim endpoint pytest bilan
 *        o'lchanadi, 9-fazada backend yuzasi umuman yo'q edi).
 *
 * ⛔⛔ MAVJUD DARVOZALAR QAYTA YUGURTIRILMAYDI (`node --test` / `vitest` /
 *    `pytest` spawn YO'Q): `gate:fast` byudjeti chegaralangan — qayta ijro
 *    uni yeb qo'yardi. Spawn yo'qligi REYESTR NAZORATI testida MEXANIK
 *    tekshiriladi (o'z manbasida `child_process` 0).
 *
 * ⛔⛔ `.planning/` GA BOG'LANISH ATAYLAB VA FAQAT SHU SINF MODULLARIDA
 *    (`phase9-criteria` bilan birga). Butun maqsad — ROADMAP prozasi bilan
 *    kodni solishtirish. Boshqa darvozalar (`landing-surface`,
 *    `motion-tokens`, …) `.planning/` ni O'QIMAYDI — kod darvozasini
 *    prozaga bog'lash uni hujjat tahririda jimgina buzardi (02-22 darsi).
 *    Bu modulda esa AYNAN o'sha bog'lanish mahsulot: ROADMAP jumlasi
 *    o'zgarsa, darvoza «qayta bog'la» deb qizarishi KERAK.
 *
 * ⛔ SOXTALASHTIRISH DARVOZASI: har mezon testining manbasida kamida
 *    bitta `src/`, `services/`, `tests/` yoki `package.json` yo'li borligi
 *    modulning O'ZINI o'qib (`import.meta.filename`) tasdiqlanadi —
 *    «faqat konstantani qayta o'qib yashil bo'lish» mexanik imkonsiz
 *    (T-09-21 sinfi; bu fazada T-10-22 ning mexanik yarmi).
 *
 * ⛔ LIGHTHOUSE VA LCP SONLARI BU MODULDA O'LCHANMAYDI va bu YASHIRILMAYDI:
 *    SC#5 testi SEO mexanikasini (sitemap/robots/OG/JSON-LD/tipografiya
 *    tokeni) o'lchaydi, Lighthouse ≥95 va LCP <1,5 s esa `10-HUMAN-UAT.md`
 *    #1 da ega va tetik bilan turadi. Mexanik qatlamning yashilligi bilan
 *    o'lchov qatlamining yo'qligini yopish TAQIQ (D-01, FOUND-07, AI-02
 *    darslari) — shu sabab SC#5 xato matni buni LITERAL aytadi.
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
 * META — mezon matni <-> test bog'lamining LANGARLARI. ROADMAP jumlasi
 * shu so'zni yo'qotadigan darajada o'zgarsa, bog'lam eskirgan — darvoza
 * qizaradi va odam qayta bog'laydi. Bu «jumla bugun rostmi?» savolining
 * teskari yo'nalishi.
 */
const CRITERION_ANCHORS = [
  /anonim|SSG/iu,
  /12s|jonli|reduced-motion/iu,
  /Telegram|demo-forma/iu,
  /halol|yolg'on|ishonch/iu,
  /Lighthouse|LCP|SEO/iu,
];

/**
 * SC#5 — mavjud bo'lishi SHART bo'lgan darvoza fayllari («mavjud G-*
 * yashil qoladi» ning mavjudlik yarmi; yashilligini `gate` zanjirining
 * o'zi o'lchaydi — bu modul ularni qayta yugurtirmaydi). Oltala fayl
 * 10-RESEARCH «Mezon → o'lchov xaritasi» LAND-04/LAND-05 qatorlaridan:
 * landing-surface (G-land-1/3/4/5), typography (repo chegaralari),
 * motion-tokens (dependencies 18 nom + reduced-motion), contrast (uch
 * tema AA), glossary (patta/rasta sinonimlari), submit-gate (forma
 * `disabled` faqat `isSubmitting` da).
 */
const LANDING_GATE_FILES = [
  "scripts/landing-surface.test.mjs",
  "scripts/typography.test.mjs",
  "scripts/motion-tokens.test.mjs",
  "scripts/contrast.test.mjs",
  "scripts/glossary.test.mjs",
  "scripts/submit-gate.test.mjs",
];

/**
 * SC#1 — SSG dalili: prerender-manifest kalitlari ICHKI locale segmenti
 * bilan yoziladi (`/uz-Latn`, `/uz-Cyrl`, `/ru`), URL prefikslari bilan
 * EMAS (`/uz`, `/uz-cyrl` — ular `routing.ts::localePrefix.prefixes` da
 * xaritalanadi). ⚠ Reja matni URL shaklini aytgan edi; o'lchov manifest
 * kalitlarining ichki shaklini ko'rsatdi — reyestr O'LCHANGAN haqiqatga
 * qadalgan (10-08 SUMMARY deviatsiyasi).
 */
const PRERENDER_LOCALE_ROUTES = ["/uz-Latn", "/uz-Cyrl", "/ru"];

/** Uchala locale katalogi — SC#4 ning halollik skani shu ro'yxat ustida. */
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

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

/** Repo ildizidan nisbiy o'qish (backend mahsulot fayllari — 10-faza yangiligi). */
function readRepo(rel) {
  return mustRead(path.join(REPO_ROOT, rel), rel);
}

/**
 * ZANJIR dalili — vitest qatlami: fayl mavjud VA `src/**​/*.test.tsx`
 * glob'iga tushadi (`vitest.config.ts` include).
 */
function assertChainTsx(rel) {
  assert.ok(
    existsSync(path.join(FRONTEND_ROOT, rel)),
    `zanjir fayli TOPILMADI: ${rel}`,
  );
  assert.ok(
    rel.startsWith("src/") && rel.endsWith(".test.tsx"),
    `${rel} vitest glob'iga (src/**​/*.test.tsx) tushmaydi — CI'da yugurmasdi`,
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
 * ZANJIR dalili — pytest qatlami (10-fazaning YANGILIGI, 9-fazada yo'q
 * edi): fayl repo ildizidan mavjud VA `tests/integration/` ostida turadi.
 *
 * ⛔ NEGA AYNAN `tests/integration/`: root `gate` zanjiri `npm run test`
 *    orqali `pytest -q` ni butun `tests/` ustida yuguradi, ya'ni
 *    integratsiya katalogidagi har `test_*.py` fayli CI'da AVTOMATIK
 *    yuguradi. Katalogdan tashqaridagi fayl esa jimgina o'lik bo'lardi.
 */
function assertChainPytest(rel) {
  assert.ok(
    existsSync(path.join(REPO_ROOT, rel)),
    `zanjir fayli TOPILMADI: ${rel}`,
  );
  assert.match(
    rel,
    /^tests\/integration\/test_[^/]+\.py$/u,
    `${rel} pytest integratsiya katalogida emas — root \`gate\` zanjiri (npm run test) uni yugurtirmasdi`,
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

/** ROADMAP `### Phase 10` bo'limidan Success Criteria ro'yxatini oladi. */
function parseCriteria() {
  const roadmap = mustRead(ROADMAP_PATH, ".planning/ROADMAP.md");
  const start = roadmap.indexOf("### Phase 10");
  assert.ok(start !== -1, "ROADMAP'da `### Phase 10` bo'limi topilmadi");

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

/** JSON katalogini yuklaydi (SC#4 halollik skani uchun). */
function loadMessages(locale) {
  return JSON.parse(
    readFileSync(path.join(FRONTEND_ROOT, "messages", `${locale}.json`), "utf8"),
  );
}

/* -------------------------------------------------------------------------- */
/* BESH MEZON                                                                 */
/* -------------------------------------------------------------------------- */

test("SC#1 — anonim root uchala tilda SSG, «Kirish» loginga: mahsulot (marketing) qobig'ida, zanjiri mavjud", () => {
  /* (i) MAHSULOT: eski himoyalangan root O'CHIRILGAN — anonim tashrifchi
   *     endi redirect'ga emas, landing'ga tushadi (10-03, G-land-1(d)). */
  assert.ok(
    !existsSync(path.join(FRONTEND_ROOT, "src/app/[locale]/page.tsx")),
    "src/app/[locale]/page.tsx HAMON MAVJUD — anonim root (marketing) sahifasi bilan raqobatlashadi (10-03 uni O'CHIRGAN edi)",
  );
  for (const rel of [
    "src/app/[locale]/(marketing)/page.tsx",
    "src/app/[locale]/(marketing)/layout.tsx",
  ]) {
    assert.ok(
      existsSync(path.join(FRONTEND_ROOT, rel)),
      `${rel} TOPILMADI — anonim landing qobig'i yo'q`,
    );
  }

  /* (i) MAHSULOT: uchala locale SSG bo'lib chizilgan — prerender-manifest
   *     kalitlari ICHKI locale segmenti bilan (reyestr izohiga qarang).
   * ⚠ Manifest — build ARTEFAKTI: `npm --prefix frontend run build` dan
   *   keyingina mavjud. Yo'q bo'lsa jimgina o'tilmaydi — sabab CHOP
   *   ETILADI va SSG da'vosining o'lchovi `gate` zanjirining build
   *   qadamida qolganini o'quvchi ko'radi. */
  const manifestPath = path.join(FRONTEND_ROOT, ".next", "prerender-manifest.json");
  if (existsSync(manifestPath)) {
    const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
    const routes = Object.keys(manifest.routes ?? {});
    for (const route of PRERENDER_LOCALE_ROUTES) {
      assert.ok(
        routes.includes(route),
        `prerender-manifest.json da \`${route}\` YO'Q — locale root SSG bo'lib chizilmagan (ROADMAP SC#1 «uchala tilda SSG»)`,
      );
    }
  } else {
    console.log(
      "[SC#1] .next/prerender-manifest.json YO'Q — build artefakti hali " +
        "yaratilmagan. SSG da'vosi bu yugurishda O'LCHANMADI; uni `npm run gate` " +
        "zanjirining `npm --prefix frontend run build` qadami o'lchaydi. " +
        "Bu band jimgina o'tkazib yuborilmadi — sabab shu satrda.",
    );
  }

  /* (i) MAHSULOT: header'dagi «Kirish» app loginiga olib boradi. */
  const header = stripComments(
    readProduct("src/components/marketing/header.tsx"),
  );
  assert.ok(
    header.includes('"/login"'),
    "header.tsx da `/login` havolasi yo'q — ROADMAP «Kirish app loginiga olib boradi» da'vosi uzilgan",
  );

  /* (i) MAHSULOT: ENVIRONMENT_FALLBACK regressiya quli (10-07 tuzatishi,
   *     build'da fallback 0) — klient provayder `timeZone` ni MAJBURIY
   *     prop sifatida oladi va uzatadi. Prop ixtiyoriy bo'lsa yoki
   *     uzatilmasa, next-intl har klient formatlashda muhit zonasiga
   *     jim tushardi va build jurnali yana 4x ogohlantirardi. */
  const providers = stripComments(
    readProduct("src/components/shell/app-providers.tsx"),
  );
  assert.ok(
    providers.includes("timeZone: string;"),
    "app-providers.tsx da `timeZone: string;` MAJBURIY prop emas — ENVIRONMENT_FALLBACK (10-07 da 4x -> 0) regressiyasi ochiq qolardi",
  );
  assert.ok(
    providers.includes("timeZone={timeZone}"),
    "app-providers.tsx `timeZone={timeZone}` ni provayderga uzatmaydi — fallback 0 kafolati yo'qoladi",
  );

  /* (ii) ZANJIR: anonim yuzaning to'rt darvozasi bitta faylda (10-07). */
  assertChainMjs("scripts/landing-surface.test.mjs");
});

test("SC#2 — hero 12s jonli sikl, video emas, reduced-motion'da final-kadr: mexanika mahsulotda, o'lchov zanjirda", () => {
  /* (i) MAHSULOT: sikl VIDEO EMAS — taymer massivi bilan boshqariladigan
   *     DOM sahnasi; reduced-motion shoxi, IntersectionObserver va
   *     visibilitychange tejash shoxlari mavjud (10-05, G-land-2). */
  const scene = stripComments(
    readProduct("src/components/marketing/hero-scene.tsx"),
  );
  assert.ok(
    /prefersReducedMotion|prefers-reduced-motion/u.test(scene),
    "hero-scene.tsx da reduced-motion shoxi yo'q — ROADMAP «reduced-motion'da statik final-kadr» da'vosi uzilgan",
  );
  assert.ok(
    scene.includes("timersRef"),
    "hero-scene.tsx da taymer massivi (`timersRef`) yo'q — 12s sikl taymerlarsiz boshqarilmaydi yoki tozalanmaydi",
  );
  assert.ok(
    scene.includes("clearTimeout"),
    "hero-scene.tsx `clearTimeout` chaqirmaydi — unmount'da taymerlar oqib qolardi (G-land-2(d))",
  );
  assert.ok(
    scene.includes("IntersectionObserver"),
    "hero-scene.tsx da `IntersectionObserver` yo'q — ekrandan chiqqan hero sikl aylantirib batareya yeyaverardi (G-land-2(e))",
  );
  assert.ok(
    scene.includes("visibilitychange"),
    "hero-scene.tsx da `visibilitychange` tinglovchisi yo'q — yashirin tabda sikl to'xtamasdi",
  );
  assert.ok(
    !/<video[\s>]/u.test(scene),
    "hero-scene.tsx da `<video>` topildi — ROADMAP SC#2 «video EMAS» deydi",
  );

  /* (i) MAHSULOT: LCP yo'li klientga bog'lanmagan — server hero'da
   *     "use client" YO'Q (G-land-1(b) ning mahsulot yarmi). */
  const hero = stripComments(readProduct("src/components/marketing/hero.tsx"));
  assert.ok(
    !hero.includes("use client"),
    "hero.tsx da `use client` paydo bo'lgan — LCP matni klient grafiga bog'lanib qolardi (10-05 server/klient ajratish shartnomasi)",
  );

  /* (ii) ZANJIR: 12s sikl xulqini o'lchaydigan vitest fayli CI glob'ida. */
  assertChainTsx("src/components/marketing/hero-scene.test.tsx");
});

test("SC#3 — demo-forma admin Telegram'ga yetadi: marshrut mahsulotda, pytest zanjiri integratsiyada", () => {
  /* (i) MAHSULOT: forma anonim endpoint'ga LITERAL yo'l bilan yozadi —
   *     og'ir api-client o'ramisiz (10-04, B-2 payload qarori). */
  const form = stripComments(
    readProduct("src/components/marketing/demo-form.tsx"),
  );
  assert.ok(
    form.includes('"/api/v1/public/demo-requests"'),
    "demo-form.tsx da `/api/v1/public/demo-requests` literal yo'li yo'q — forma qaysi marshrutga yozishi noma'lum",
  );

  /* (i) MAHSULOT: backend marshrut moduli mavjud (10-01). */
  assert.ok(
    existsSync(path.join(REPO_ROOT, "services/core-api/app/api/v1/public.py")),
    "services/core-api/app/api/v1/public.py TOPILMADI — anonim demo endpoint'i yo'q",
  );

  /* (i) MAHSULOT: marshrut tenant-qamrov istisnosida SABAB bilan e'lon
   *     qilingan — `EXEMPT_ROUTES` yozuvi `global` bilan boshlanadi
   *     (aks holda cross-tenant darvozasi uni «unutilgan marshrut» deb
   *     sanardi). */
  const crossTenant = readRepo("tests/tenancy/test_cross_tenant.py");
  const exemptAt = crossTenant.indexOf('"/api/v1/public/demo-requests"');
  assert.ok(
    exemptAt !== -1,
    "tests/tenancy/test_cross_tenant.py::EXEMPT_ROUTES da `/api/v1/public/demo-requests` yozuvi YO'Q",
  );
  assert.match(
    crossTenant.slice(exemptAt, exemptAt + 200),
    /"global/u,
    "EXEMPT_ROUTES dagi demo-requests sababi `global` bilan boshlanmaydi — istisno sinfi noto'g'ri e'lon qilingan",
  );

  /* (ii) ZANJIR: anonim endpoint'ning 7 bandli integratsiya testi (10-01)
   *     va forma holatlarining vitest testi (10-04) — ikkala qatlam ham
   *     CI glob'ida. */
  assertChainPytest("tests/integration/test_demo_request.py");
  assertChainTsx("src/components/marketing/demo-form.test.tsx");
});

test("SC#4 — ishonch bloki va pilot holati halol: copy'da yolg'on raqam 0, namunaviy belgi mahsulotda", () => {
  /* (i) MAHSULOT: ishonch bloki katalogdan chizadi (residency bandi bilan)
   *     va pilot holati rozetka bilan ko'rsatiladi. */
  const trust = stripComments(
    readProduct("src/components/marketing/trust-block.tsx"),
  );
  assert.ok(
    trust.includes("trustBlock."),
    "trust-block.tsx `landing.trustBlock.*` katalogidan o'qimaydi — ishonch bloki matni manbasiz",
  );
  const pilot = stripComments(readProduct("src/components/marketing/pilot.tsx"));
  assert.ok(
    /pilot\.status/u.test(pilot) && /<Badge/u.test(pilot),
    "pilot.tsx da `pilot.status` rozetkasi yo'q — «Karmana sinovda» holati ko'rsatilmaydi",
  );

  /* (i) MAHSULOT: hero sahnasi «namunaviy ma'lumot» belgisini tashiydi —
   *     jonli sikldagi raqamlar haqiqiy deb o'qilmasin (K-7, G-land-4(a)). */
  const scene = stripComments(
    readProduct("src/components/marketing/hero-scene.tsx"),
  );
  assert.ok(
    scene.includes("sampleBadge"),
    "hero-scene.tsx da `sampleBadge` yo'q — sahna raqamlari haqiqiy ko'rsatkich deb o'qilardi (halollik buzilgan)",
  );

  /* (i) MAHSULOT: pilot copy'sida YOLG'ON RAQAM YO'Q — uchala locale'da
   *     `landing.pilot.*` qiymatlarida birorta raqam belgisi uchramaydi
   *     (ROADMAP SC#4 «yolg'on raqam YO'Q» ning mexanik shakli). */
  for (const locale of LOCALES) {
    const pilotCopy = loadMessages(locale).landing?.pilot ?? {};
    assert.ok(
      Object.keys(pilotCopy).length > 0,
      `${locale}.json da landing.pilot.* BO'SH — halollik skani o'lchaydigan narsa yo'q`,
    );
    const digits = JSON.stringify(pilotCopy).match(/\d/gu) ?? [];
    assert.equal(
      digits.length,
      0,
      `${locale}.json landing.pilot.* ichida ${digits.length} ta raqam bor — pilot holati SONSIZ halol matn bo'lishi shart (G-land-4(f))`,
    );
    assert.equal(
      typeof loadMessages(locale).landing?.trustBlock?.residency?.body,
      "string",
      `${locale}.json da landing.trustBlock.residency.body YO'Q — «ma'lumotlar O'zbekistonda» da'vosi matnsiz`,
    );
  }

  /* (ii) ZANJIR: G-land-4 (halollik darvozasi — taqiq tokenlar, raqam
   *     skani, residency uchala tilda) landing-surface faylida yashaydi. */
  assertChainMjs("scripts/landing-surface.test.mjs");
});

test("SC#5 — SEO meta/OG/structured data to'liq: mexanika mahsulotda; Lighthouse/LCP soni BU YERDA O'LCHANMAYDI (10-HUMAN-UAT #1)", () => {
  /* (i) MAHSULOT: SEO fayl-konventsiyalari mavjud. ⛔ XATO MATNI LITERAL
   *     AYTADI: bu test SEO MEXANIKASINI o'lchaydi — Lighthouse ≥95 va
   *     LCP <1,5 s sonlari BU YERDA O'LCHANMAYDI, ular 10-HUMAN-UAT.md
   *     #1 da (ega: ijrochi, tetik: birinchi deploy). Mexanik yashillikni
   *     o'sha ikki raqamning o'lchovi deb O'QIMANG. */
  for (const rel of ["src/app/sitemap.ts", "src/app/robots.ts"]) {
    assert.ok(
      existsSync(path.join(FRONTEND_ROOT, rel)),
      `${rel} TOPILMADI — SEO fayl-konventsiyasi yo'q. ⛔ Eslatma: Lighthouse/LCP sonlari bu modulda O'LCHANMAYDI — ular 10-HUMAN-UAT.md #1 da`,
    );
  }

  /* (i) MAHSULOT: sahifada OG metadata va JSON-LD (rasmiy escape naqshi
   *     bilan 10-07 da qurilgan). */
  const page = readProduct("src/app/[locale]/(marketing)/page.tsx");
  assert.ok(
    page.includes("openGraph"),
    "(marketing)/page.tsx da `openGraph` yo'q — OG metadata da'vosi uzilgan",
  );
  assert.ok(
    page.includes("application/ld+json"),
    "(marketing)/page.tsx da `application/ld+json` yo'q — structured data da'vosi uzilgan",
  );

  /* (i) MAHSULOT: hero tipografiya tokeni @theme qatlamida (10-02). */
  const css = readProduct("src/app/globals.css");
  assert.ok(
    css.includes("--text-hero"),
    "globals.css da `--text-hero` tokeni yo'q — hero tipografiyasi token qatlamidan chiqib ketgan (G-land-5)",
  );

  /* (ii) ZANJIR: «mavjud G-* yashil qoladi» ning mavjudlik yarmi — oltala
   *     darvoza fayli joyida (yashilligini `gate` zanjirining o'zi beradi). */
  for (const rel of LANDING_GATE_FILES) assertChainMjs(rel);
});

/* -------------------------------------------------------------------------- */
/* META-TEST — ROADMAP <-> MODUL BOG'LAMI                                     */
/* -------------------------------------------------------------------------- */

test("META — ROADMAP'dan AYNAN 5 mezon parse bo'ladi, modulda AYNAN 5 mezon testi bor va zanjir CI'da yuguradi", () => {
  const criteria = parseCriteria();
  assert.equal(
    criteria.length,
    5,
    `ROADMAP Phase 10 Success Criteria ${criteria.length} band — reyestr AYNAN 5 bo'lishi shart (to'rttasi ham, oltitasi ham qizil)`,
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
   * `test` esa shu modul yashaydigan globni yuguradi. Backend yarmi —
   * `npm run test` (pytest butun tests/ ustida) ham gate zanjirida. */
  const rootPkg = JSON.parse(
    mustRead(path.join(REPO_ROOT, "package.json"), "root package.json"),
  );
  assert.ok(
    rootPkg.scripts.gate.includes("npm --prefix frontend test"),
    "root `gate` zanjirida `npm --prefix frontend test` yo'q — bu modul CI'da yugurmasdi",
  );
  assert.ok(
    rootPkg.scripts.gate.includes("npm run test"),
    "root `gate` zanjirida `npm run test` (backend pytest) yo'q — SC#3 pytest zanjiri CI'da yugurmasdi",
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
      block.includes("src/") ||
        block.includes("services/") ||
        block.includes("tests/") ||
        block.includes("package.json"),
      `SC#${n} bloki mahsulot fayliga (src/, services/, tests/ yoki package.json) murojaat qilmaydi — ` +
        "«faqat konstantani qayta o'qib yashil bo'lish» taqiqlangan (T-10-22 mexanik yarmi)",
    );
  }
});

/* -------------------------------------------------------------------------- */
/* REYESTR NAZORATI                                                           */
/* -------------------------------------------------------------------------- */

test("REYESTR NAZORATI — takror yo'q, reyestrlar bo'sh emas, modul hech narsani spawn qilmaydi", () => {
  const registries = {
    CRITERION_ANCHORS: CRITERION_ANCHORS.map(String),
    LANDING_GATE_FILES,
    PRERENDER_LOCALE_ROUTES,
    LOCALES,
  };
  for (const [name, list] of Object.entries(registries)) {
    assert.equal(
      new Set(list).size,
      list.length,
      `${name} da takror bor — reyestr to'plam bo'lishi shart`,
    );
    assert.ok(list.length > 0, `${name} bo'sh — reyestr ma'nosiz`);
  }
  assert.equal(CRITERION_ANCHORS.length, 5, "langar reyestri mezon soniga teng");
  assert.equal(
    PRERENDER_LOCALE_ROUTES.length,
    3,
    "SSG reyestri aynan uch locale (uz-Latn, uz-Cyrl, ru) — FOUND-04 uch til sharti",
  );
  assert.equal(
    LANDING_GATE_FILES.length,
    6,
    "darvoza reyestri aynan olti fayl (10-RESEARCH LAND-04/05 xaritasi) — o'zgargan bo'lsa, sabab bilan yangilang",
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
