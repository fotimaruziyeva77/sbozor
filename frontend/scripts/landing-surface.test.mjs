#!/usr/bin/env node
/**
 * G-land-1 + G-land-3 + G-land-4 + G-land-5 (10-UI-SPEC §16.4) — LANDING
 * YUZASINING STATIK CHEGARASI. To'rt darvoza BITTA sof matn/CSS parse
 * faylida (byudjet sababli qamrov ataylab tor — §16.4, O-01).
 *
 * =============================================================================
 * NIMA HIMOYA QILINADI — TO'RT XIL NARSA, BITTA MEXANIZM.
 *
 * 1. ⛔ G-land-1 — LCP YO'LI KLIENTGA BOG'LANMAGAN (ROADMAP SC#5).
 *    (a) Klient orollari to'plami REYESTRGA TENG (beshta fayl — B-1/C
 *    yechimi reyestrni 4 dan 5 ga chiqardi va bu ONGLI). (b) `hero.tsx`
 *    (h1 uyi) klient direktivasiz. (c) IKKI TOMONLAMA fazoviy nom quli:
 *    provayder to'plami VA komponent chaqiruvlari — bir tomonlama qulf
 *    `MISSING_MESSAGE` ni build'dan o'tkazib yuborardi (T-10-15).
 *    (d) L-7 regressiya qulfi: `[locale]/page.tsx` yo'q, `(marketing)`
 *    sahifasi bor — Next 16 «Conflicting paths» ning mexanik shakli.
 *
 * 2. ⛔ G-land-3 — GPU XOSSALARI, `transition` LARDA HAM (SC#5, T-10-21).
 *    ⛔⛔ Bu G-motion-3(a) ning O'LCHANGAN bo'shlig'i [L-8]: u faqat
 *    `@keyframes` bloklarini parse qiladi, ya'ni foydalanuvchi tasdiqlagan
 *    maket manbasining balandlik-tranzitsiyasi shakli bugungi darvozadan
 *    JIMGINA o'tardi. `extractClassBlocks` shu teshikni yopadi.
 *
 * 3. ⛔ G-land-4 — HALOLLIK (SC#4, K-7, T-10-10). Yolg'on da'vo tokenlari,
 *    pilot raqamlari, shartli namuna-belgisi va FAQ matnining ikkinchi
 *    manbasi — hammasi mexanik ravishda imkonsiz. Marketing matnini
 *    «kuchaytirish» refleksi bir commitda brendning yagona ustunligini
 *    (halollikni) yo'q qiladi — bu darvoza o'sha commitni qizartiradi.
 *
 * 4. ⛔ G-land-5 — TIPOGRAFIYA VA BO'SHLIQ KENGAYTMASI (§0.2, §7, §8.2).
 *    `typography.test.mjs` butun `src/**` ni skanerlaydi va chegaralari
 *    TO'LGAN [L-2] — landing'ning birinchi buzilishi butun zanjirni
 *    qizartirardi va faqat «7 dan oshdi» derdi. Bu darvoza xatoni landing
 *    faylida ushlaydi va SABABNI aytadi.
 * =============================================================================
 *
 * ⚠ QAMROV HOSILA, QO'LDA RO'YXAT YO'Q (§16.2): kataloglar `readdirSync`
 *   bilan REKURSIV o'qiladi, reyestrlardan iteratsiya qilinadi, fayl soni
 *   QUYI chegara bilan qo'riqlanadi.
 *
 * ⚠ TO'PLAM TENGLIGI (§16.2): `deepEqual`/`Set` — `not.toContain` YO'Q.
 *   «0 marta» o'lchovlari muammolar massivini yig'ib bo'sh massivga
 *   `deepEqual` qiladi (motion-tokens naqshi).
 *
 * ⚠ IZOHLAR OLIB TASHLANGANDAN KEYIN QIDIRILADI — xom faylda sanoq
 *   izohdagi so'zni sanaydi va darvoza o'z-o'zini bekor qiladi. Holat
 *   mashinasi `motion-tokens.test.mjs:185-258` dan AYNAN NUSXA (u ham
 *   `bulk-action-surface.test.mjs:163-225` zanjiridan) — mustaqil
 *   to'rtinchi mantiq YOZILMAYDI.
 *
 * ⚠ TASHQI PAKET YO'Q, `child_process` IMPORTI YO'Q — mavjud darvozalar
 *   qayta yugurtirilmaydi (`gate:fast` byudjeti; reyestr nazorati testi
 *   buni o'lchaydi). Sof matn skani `gate:fast` (200 s) byudjetiga
 *   sezilmas qo'shiladi (§16.4: kutilgan +0,5…1,0 s).
 */
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { test } from "node:test";

const FRONTEND_ROOT = path.join(import.meta.dirname, "..");
const SRC = path.join(FRONTEND_ROOT, "src");
const GLOBALS = path.join(SRC, "app", "globals.css");
const MESSAGES_DIR = path.join(FRONTEND_ROOT, "messages");
const MARKETING_COMPONENTS = path.join(SRC, "components", "marketing");
const MARKETING_APP = path.join(SRC, "app", "[locale]", "(marketing)");
const MARKETING_LAYOUT = path.join(MARKETING_APP, "layout.tsx");
const MARKETING_PAGE = path.join(MARKETING_APP, "page.tsx");
const LOCALE_ROOT_PAGE = path.join(SRC, "app", "[locale]", "page.tsx");
const HERO_FILE = path.join(MARKETING_COMPONENTS, "hero.tsx");
const HERO_SCENE_FILE = path.join(MARKETING_COMPONENTS, "hero-scene.tsx");
const TRUST_BLOCK_FILE = path.join(MARKETING_COMPONENTS, "trust-block.tsx");
const PILOT_FILE = path.join(MARKETING_COMPONENTS, "pilot.tsx");
const OVERRIDES_FILE = path.join(MESSAGES_DIR, "uz-Cyrl.overrides.json");

/** Skanerlanadigan kengaytmalar (utilita/direktiva TS/TSX'da yashaydi). */
const CODE_EXTENSIONS = [".ts", ".tsx"];

/** Mahsulot fayli emas — qamrovdan chiqadi (u taqiqni O'LCHAYDI, buzmaydi). */
const TEST_FILE = /\.test\.[a-z]+$/u;

/* -------------------------------------------------------------------------- */
/* REYESTRLAR                                                                 */
/* -------------------------------------------------------------------------- */

/**
 * G-land-1(a) — klient orollari, NOMMA-NOM (§4.4 + B-1/C yechimi).
 *
 * ⛔ OLTI fayl: 10-04 formasi, 10-05 sahnasi, 10-06 reveal/step-line,
 *    header'ning til almashtirgichi (B-1/C: 4 → 5) va Landing v2
 *    buyurtmasining yo'qotish kalkulyatori (claude.ai/design, 2026-08-18:
 *    5 → 6 — ONGLI, sof klient arifmetikasi, fetch 0). Yettinchi fayl
 *    paydo bo'lsa bu deepEqual QIZARADI — yangi orol dizayn/SPEC qaroriga
 *    qaytariladi, jimgina qo'shilmaydi.
 */
const CLIENT_ISLANDS = [
  "components/marketing/demo-form.tsx",
  "components/marketing/hero-scene.tsx",
  "components/marketing/locale-switcher.tsx",
  "components/marketing/loss-calc.tsx",
  "components/marketing/reveal.tsx",
  "components/marketing/step-line.tsx",
  // 260819 — beshinchi ORIGINAL orol (§4.4 5-qator). Tema tugmasi DOM
  // temasiga `useSyncExternalStore` bilan obuna bo'ladi; `nav-menu.tsx`
  // esa ATAYIN Server Component (anker havolalarda holat yo'q).
  "components/marketing/theme-toggle.tsx",
  // 260819 — oltinchi ORIGINAL orol. Anker siljishini O'ZIMIZ chizamiz
  // (brauzerning `smooth` i masofani hisobga olmaydi va uzoq siljishda
  // «qo'pol» chiqadi). Delegatsiya bo'lgani uchun `nav-menu.tsx` SERVER
  // Component bo'lib qoladi — LCP yo'li klientga bog'lanmaydi.
  "components/marketing/smooth-anchor.tsx",
];
const CLIENT_ISLANDS_COUNT = 8;

/**
 * G-land-1(c) — `(marketing)/layout.tsx` provayderiga uzatiladigan fazoviy
 * nomlar (§4.3). Chetga chiqish klientda `MISSING_MESSAGE` beradi — server
 * render O'TADI, ya'ni `next build` ham, vitest ham ko'rmaydi (T-10-15).
 */
const PROVIDER_NAMESPACES = ["common", "landing"];

/**
 * G-land-3(a) — `.landing-*`/`.motion-*` sinflarida `transition` uchun
 * RUXSAT ETILGAN xossalar (10-UI-SPEC §16.4). Hammasi kompozitor-do'st yoki
 * faqat paint — layout hisobini qo'zg'amaydi.
 */
const ALLOWED_TRANSITION_PROPS = [
  "transform",
  "opacity",
  "background",
  "background-color",
  "border-color",
  "box-shadow",
  "color",
];
const MIN_ALLOWED_TRANSITION_PROPS = 7;

/**
 * G-land-3(a) — ALOHIDA taqiq ro'yxati (motion-tokens naqshi: ruxsat
 * to'plami qamrasa ham, layout-thrash sinfi NOMMA-NOM 0 o'lchanadi).
 * `margin`/`padding` PREFIKS sifatida ham tekshiriladi; `all` — butun
 * ro'yxatni yashirincha qamrab yuborgani uchun taqiq.
 */
const BANNED_TRANSITION_PROPS = [
  "width",
  "height",
  "top",
  "left",
  "right",
  "bottom",
  "margin",
  "padding",
  "all",
];

/**
 * G-land-3(d) — `@keyframes` reyestri: mavjud SAKKIZ nom [L-9] + 10-fazaning
 * YAGONA yangi nomi `sweep` (§5.4). To'qqizinchi qo'shilsa yoki sakkiztadan
 * biri o'zgarsa bu deepEqual QIZARADI.
 */
const LEGACY_KEYFRAMES = [
  "draw",
  "ringpulse",
  "landin",
  "enter",
  "shimmer",
  "breath",
  "attention",
  "shake",
];
const NEW_KEYFRAME = "sweep";
/**
 * ⛔ ONGLI KENGAYISH (2026-08-18): kirish sahifasi foydalanuvchining
 * «Sbozor Login» dizayni bo'yicha qayta qurildi va u to'rtta yangi kadr
 * talab qiladi — orqa fondagi xarita nafasi (`cellglow`), kamera nuri
 * (`scanbeam`), ko'tarilib yo'qoladigan yorliqlar (`floatup`) va kartaning
 * kirishi (`cardin`). To'rttasi ham GPU-toza (opacity/transform) va faqat
 * `(auth)` yuzasida ishlatiladi; landing reyestri (9 nom) TEGILMADI —
 * shuning uchun ular alohida ro'yxatda turadi va bu darvoza yangi
 * BESHINCHISI qo'shilsa yana qizaradi.
 */
const AUTH_KEYFRAMES = ["cellglow", "scanbeam", "floatup", "cardin"];
/**
 * ⛔ ONGLI KENGAYISH (2026-08-18, ikkinchi marta): direktor paneli
 * foydalanuvchining `Sbozor Direktor` dizayni bo'yicha qurildi.
 *
 * Dizayn MCP orqali o'qildi (claude.ai/design `7bb95baa…`) va u to'rtta
 * kadr nomini e'lon qiladi: `dirIn` (katakning kirishi), `dirFade`
 * (grafik nuqtalari), `dirDraw` (chiziqning chizilishi), `dirBreath`.
 *
 * ⛔ BU RO'YXATGA FAQAT ISHLATILAYOTGANI QO'SHILADI. `G-motion-3(c)`
 *    har bir kadr kamida bitta sinfda ishlatilishini talab qiladi, ya'ni
 *    «kelajak uchun» kadr qo'shib qo'yish darvozani qizartiradi — va bu
 *    to'g'ri: ishlatilmagan kadr o'lik CSS.
 *
 * ⚠ `dirBreath` dizaynda e'lon qilingan, lekin HECH QAYERDA
 *   ishlatilmagan (dizayn manbasida ham) — shuning uchun u KO'CHIRILMADI.
 */
/*
 * ⛔ `dirFlowDraw` — gero katagidagi pul oqimi chizig'i (260902).
 *    Chiziq chapdan o'ngga chiziladi: ma'lumot «kelayotgani» hissi.
 *    `.dir-flow-line` sinfida ishlatiladi, ya'ni G-motion-3(c)
 *    talabi bajarilgan.
 */
const DIRECTOR_KEYFRAMES = ["dirIn", "dirDraw", "dirFade", "dirFlowDraw"];
/**
 * ⛔ ONGLI KENGAYISH (2026-08-25, uchinchi marta): brend-loader — bozor
 * «rasta ustunlari» metaforasi (foydalanuvchi talabi: «Loader quy,
 * bozorga mos bulsin»). Spinner EMAS (masterplan §3.2 taqiqi) — uch
 * ustun scaleY+opacity bilan nafas oladi, GPU-toza, reduced-motion'da
 * statik. Ishlatilishi: `components/ui/brand-loader.tsx` -> sahifa
 * darajasidagi Suspense/sessiya kutishlari.
 */
const LOADER_KEYFRAMES = ["brandBar"];
const KEYFRAMES_REGISTRY = [
  ...LEGACY_KEYFRAMES,
  NEW_KEYFRAME,
  ...AUTH_KEYFRAMES,
  ...DIRECTOR_KEYFRAMES,
  ...LOADER_KEYFRAMES,
];
const KEYFRAMES_COUNT = 18;

/**
 * G-land-3(c) — avtomatik harakat manbai bo'lishga RUXSAT ETILGAN yagona
 * fayl (§5.6 mexanizm 4): hero sahnasi. Kechiktirish-chaqiruv shu fayldan
 * tashqarida topilsa darvoza qizaradi.
 */
const TIMER_FILES = ["components/marketing/hero-scene.tsx"];

/** Skan qilinadigan uchala locale (routing.ts bilan ayni ro'yxat). */
const LOCALES = ["uz-Latn", "uz-Cyrl", "ru"];

/**
 * G-land-4(e) — TAQIQLANGAN DA'VO TOKENLARI (K-7, brief §7.5). Marketing
 * matnini «kuchaytirish» refleksi eng oson buziladigan shartnoma: bitta
 * commit brendning yagona ustunligini (halollikni) yo'q qiladi. Foiz
 * belgisi ham shu yerda — «X foiz o'sish» sinfidagi har qanday da'vo pilot
 * o'lchovi yakunlanmagunicha yolg'on (K-7).
 */
const FORBIDDEN_CLAIM_TOKENS = [
  "jonli",
  "%",
  "martaga",
  "в разы",
  "гарантир",
  "kafolatlaymiz",
  "eng yaxshi",
  "лучший",
  "№1",
];
const MIN_FORBIDDEN_CLAIM_TOKENS = 8;

/**
 * G-land-4(b) — namuna-belgi O'ZAKLARI: sahna kontenti namunaviy ekani
 * skrinriderga ham yetishi shart (T-10-20). Har locale qiymatida shu
 * o'zaklardan kamida bittasi bo'ladi.
 */
const SAMPLE_ROOTS = ["namunaviy", "намунавий", "демонстрацион"];

/**
 * G-land-5(a) — hero-o'lcham utilitasining YAGONA uyi (§7.1.1). Qulf ikki
 * qatlamli: fayl-reyestr (deepEqual) + o'sha fayldagi uchrashuv sanog'i
 * (aynan 1) — faqat fayl qulfi bo'lsa hero ichida ikkinchi hero-o'lchamli
 * sarlavha jimgina paydo bo'lardi.
 */
const TEXT_HERO_FILES = ["components/marketing/hero.tsx"];

/**
 * G-land-5(c) — seksiya bo'shliq qiymatlarining YAGONA uyi (§8.2):
 * vertikal ritm faqat `<Section>` orqali.
 */
const SECTION_SPACING_FILES = ["components/marketing/section.tsx"];

/** Qamrov chegaralari — skanerlanadigan fayl soni kamaysa darvoza qizaradi. */
const MIN_MARKETING_COMPONENT_FILES = 12; // bugun 15
const MIN_MARKETING_APP_FILES = 3; // bugun 3 (layout, page, maxfiylik/page)
const MIN_SRC_FILES = 150; // bugun 200+ (motion-tokens bilan bir xil chegara)
const MIN_NAMESPACE_CALLS = 10; // bugun 17+ chaqiruv
const MIN_CLASS_BLOCKS = 10; // bugun 14 selektor-blok
const MIN_STYLE_BLOCKS = 2; // bugun 6+ (`--i` va transitionDelay)
const MIN_LANDING_KEYS = 100; // bugun ~130 landing.* kaliti har locale'da
const MIN_FAQ_TEXTS = 30; // 5 savol + 5 javob x 3 locale
const MIN_OVERRIDE_WORDS = 5; // uz-Cyrl.overrides.json words lug'ati
const MIN_RENDERABLE_PARTS = 20; // bugun 100+ JSX matn bo'lagi

/* -------------------------------------------------------------------------- */
/* IZOHLARNI OLIB TASHLASH — motion-tokens.test.mjs dan AYNAN NUSXA           */
/* -------------------------------------------------------------------------- */

/**
 * JS/TS izohlarini olib tashlaydi, SATR LITERALLARINI SAQLAYDI.
 * ⛔ `motion-tokens.test.mjs:185-258` holat mashinasining nusxasi (zanjir:
 *    `collect-surface` -> `bulk-action-surface:163-225`, W0-F4) — mustaqil
 *    yangi mantiq YOZILMAYDI. Satrlar ataylab saqlanadi: `className` satri
 *    ichidagi utilita ham brauzerga yetib boradi.
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
        // Qator raqamlari saqlanadi — xato xabarida foydali.
        if (c === "\n") out += c;
        i += 1;
      }
      continue;
    }

    // Satr literali ichida: `state` ochuvchi belgining O'ZI.
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

/** CSS izohlari — `contrast.test.mjs`/motion-tokens bilan bir xil regeks. */
function stripCssComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//gu, "");
}

/** Faylning izohsiz JS kodi + «yutib yuborilmadi» nazorati. */
function readCode(file) {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);

  /*
   * RUNAWAY NAZORATI: holat mashinasi adashib butun faylni izoh deb yutsa,
   * keyingi hamma assert JIMGINA yashil bo'lardi — darvoza o'chib qolgan
   * holda «o'tdi» deb hisobot berardi.
   */
  if (raw.includes("export")) {
    assert.ok(
      code.includes("export"),
      `${path.relative(FRONTEND_ROOT, file)}: izoh filtri faylni YUTIB YUBORDI ` +
        "(manbada `export` bor, filtrdan keyin yo'q) — darvoza o'chib qolgan bo'lardi",
    );
  }

  return code;
}

/** `globals.css` ning izohsiz matni + runaway nazorati. */
function readGlobalsCss() {
  const raw = readFileSync(GLOBALS, "utf8");
  const css = stripCssComments(raw);

  assert.ok(
    css.includes("@keyframes") && css.includes("@theme"),
    "CSS izoh filtri `globals.css` ni YUTIB YUBORDI — `@keyframes` yoki " +
      "`@theme` bloki filtrdan keyin yo'qolgan",
  );

  return css;
}

/* -------------------------------------------------------------------------- */
/* PARSE YORDAMCHILARI                                                        */
/* -------------------------------------------------------------------------- */

/** `marker` dan boshlangan `{ ... }` blokining ICHKI matni — qavs sanog'i. */
function extractBlock(source, marker) {
  const start = source.indexOf(marker);
  if (start === -1) return null;
  const open = source.indexOf("{", start);
  if (open === -1) return null;
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "{") depth += 1;
    else if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  return null;
}

/** Barcha `@keyframes <nom> { ... }` bloklari: [{ name, body }]. */
function extractKeyframes(source) {
  const blocks = [];
  for (const m of source.matchAll(/@keyframes\s+([A-Za-z_][\w-]*)/gu)) {
    const open = source.indexOf("{", m.index);
    if (open === -1) continue;
    let depth = 0;
    for (let i = open; i < source.length; i += 1) {
      if (source[i] === "{") depth += 1;
      else if (source[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          blocks.push({ body: source.slice(open + 1, i), name: m[1] });
          break;
        }
      }
    }
  }
  return blocks;
}

/**
 * ⛔⛔ YANGI PARSER — G-land-3(a) NING BUTUN ASOSI.
 *
 * `.landing-*` / `.motion-*` sinf selektorlarini topib blok tanasini
 * qaytaradi — `extractKeyframes` bilan BIR XIL qavs-balans texnikasi,
 * boshqa selektor. `[data-step="1"] .landing-step-fill { ... }` kabi
 * qo'shma selektorlar ham qamraladi (sinf tokeni `{` dan oldin turadi).
 *
 * Soxta uchrash himoyasi: token bilan `{` orasida `}` yoki `;` bo'lsa, bu
 * selektor emas (masalan, deklaratsiya qiymatidagi token) — tashlanadi.
 */
function extractClassBlocks(source) {
  const blocks = [];
  for (const m of source.matchAll(/\.((?:landing|motion)-[A-Za-z0-9_-]+)/gu)) {
    const open = source.indexOf("{", m.index);
    if (open === -1) continue;
    const between = source.slice(m.index + m[0].length, open);
    if (between.includes("}") || between.includes(";")) continue;
    let depth = 0;
    for (let i = open; i < source.length; i += 1) {
      if (source[i] === "{") depth += 1;
      else if (source[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          blocks.push({ body: source.slice(open + 1, i), name: m[1] });
          break;
        }
      }
    }
  }
  return blocks;
}

/** Matnni QAVS DARAJASI 0 bo'lgan ajratgichlar bo'yicha bo'ladi. */
function splitTopLevel(text, separator) {
  const parts = [];
  let depth = 0;
  let current = "";
  for (const ch of text) {
    if (ch === "(" || ch === "[" || ch === "{") depth += 1;
    else if (ch === ")" || ch === "]" || ch === "}") depth -= 1;
    if (ch === separator && depth === 0) {
      parts.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  if (current.trim() !== "") parts.push(current);
  return parts;
}

/**
 * Blok tanasidagi `transition:` / `transition-property:` deklaratsiyalaridan
 * XOSSA nomlari. Shorthand'da har vergul-segmentning BIRINCHI tokeni —
 * xossa (`transform 900ms var(--ease-out)` -> `transform`);
 * `transition-property` da esa har segment xossaning o'zi.
 * `transition-duration`/`-delay`/`-timing-function` ATAYIN qamralmaydi —
 * ularda xossa nomi yo'q.
 */
function transitionProps(body) {
  const props = [];
  for (const m of body.matchAll(
    /(?<![\w-])transition(-property)?\s*:\s*([^;{}]+)/gu,
  )) {
    const isPropertyForm = m[1] !== undefined;
    for (const segment of splitTopLevel(m[2], ",")) {
      const trimmed = segment.trim();
      if (trimmed === "") continue;
      const name = isPropertyForm
        ? trimmed.toLowerCase()
        : trimmed.split(/\s+/u)[0].toLowerCase();
      props.push(name);
    }
  }
  return props;
}

/** Xossa taqiq ro'yxatiga tushadimi (`margin*`/`padding*` — prefiks ham). */
function isBannedTransitionProp(prop) {
  return BANNED_TRANSITION_PROPS.some(
    (banned) =>
      prop === banned ||
      ((banned === "margin" || banned === "padding") &&
        prop.startsWith(`${banned}-`)),
  );
}

/** Katalogdagi barcha MAHSULOT kod fayllari (rekursiv, hosila qamrov). */
function listProductFiles(dir, extensions) {
  const found = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      found.push(...listProductFiles(full, extensions));
    } else if (
      extensions.includes(path.extname(entry)) &&
      !TEST_FILE.test(entry)
    ) {
      found.push(full);
    }
  }
  return found;
}

/** `src/` ga nisbatan POSIX yo'l — reyestrlar bilan solishtirish uchun. */
function relSrc(file) {
  return path.relative(SRC, file).split(path.sep).join("/");
}

/** Marketing yuzasining mahsulot fayllari (ikkala katalog, hosila qamrov). */
function marketingSurfaceFiles() {
  const componentFiles = listProductFiles(MARKETING_COMPONENTS, CODE_EXTENSIONS);
  const appFiles = listProductFiles(MARKETING_APP, CODE_EXTENSIONS);
  assert.ok(
    componentFiles.length >= MIN_MARKETING_COMPONENT_FILES,
    `\`components/marketing/\` da atigi ${componentFiles.length} ta mahsulot ` +
      `fayli bor (kutilgan: kamida ${MIN_MARKETING_COMPONENT_FILES}) — skan ` +
      "yuzasi jimgina toraygan",
  );
  assert.ok(
    appFiles.length >= MIN_MARKETING_APP_FILES,
    `\`(marketing)/\` da atigi ${appFiles.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_MARKETING_APP_FILES}) — skan yuzasi jimgina toraygan`,
  );
  return { appFiles, componentFiles, all: [...componentFiles, ...appFiles] };
}

/**
 * Klient DIREKTIVASI bormi — fayl BOSHIDAGI direktiv pozitsiyada (izohlar
 * olib tashlangandan keyin faqat bo'shliq oldin turishi mumkin). O'rtadagi
 * inert satr literali direktiva emas — React ham uni ko'rmaydi.
 */
function hasClientDirective(code) {
  return /^\s*["']use client["']/u.test(code);
}

/**
 * Fayldagi tarjima FAZOVIY NOMLARI: `useTranslations("x")`,
 * `getTranslations("x")` va obyekt shakli `namespace: "x"` — uchala kanal.
 */
function translationNamespaces(code) {
  const found = [];
  for (const m of code.matchAll(
    /\b(?:useTranslations|getTranslations)\(\s*["']([^"']+)["']\s*\)/gu,
  )) {
    found.push(m[1]);
  }
  for (const m of code.matchAll(/\bnamespace\s*:\s*["']([^"']+)["']/gu)) {
    found.push(m[1]);
  }
  return found;
}

/**
 * `NextIntlClientProvider` ga uzatilgan `messages={{ ... }}` obyektining
 * USTKI kalitlari. Spread (`...`) topilsa `null` — toraytirishni o'qib
 * bo'lmaydi va bu o'z-o'zidan qizil holat (jimgina kengayish mumkin).
 */
function providerNamespaces(code) {
  const attr = /messages=\{\s*\{/u.exec(code);
  if (attr === null) return { keys: null, reason: "messages={{ topilmadi" };
  // Ichki obyektning ochuvchi qavsi — attr ichidagi IKKINCHI `{`.
  const innerOpen = code.indexOf("{", code.indexOf("{", attr.index) + 1);
  if (innerOpen === -1) {
    return { keys: null, reason: "ichki obyekt qavsi topilmadi" };
  }
  let depth = 0;
  let body = null;
  for (let i = innerOpen; i < code.length; i += 1) {
    if (code[i] === "{") depth += 1;
    else if (code[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        body = code.slice(innerOpen + 1, i);
        break;
      }
    }
  }
  if (body === null) return { keys: null, reason: "obyekt yopilmagan" };
  const keys = [];
  for (const segment of splitTopLevel(body, ",")) {
    const trimmed = segment.trim();
    if (trimmed === "") continue;
    if (trimmed.startsWith("...")) {
      return {
        keys: null,
        reason: `spread (\`${trimmed.slice(0, 20)}…\`) — toraytirish o'qib bo'lmaydi`,
      };
    }
    const id = /^([A-Za-z_$][\w$]*)/u.exec(trimmed);
    if (id !== null) keys.push(id[1]);
  }
  return { keys, reason: null };
}

/** JSX ichidagi `style={{ ... }}` bloklarining ichki matnlari. */
function inlineStyleBlocks(code) {
  const blocks = [];
  let idx = 0;
  for (;;) {
    const start = code.indexOf("style={", idx);
    if (start === -1) break;
    const open = start + "style=".length;
    let depth = 0;
    let end = -1;
    for (let i = open; i < code.length; i += 1) {
      if (code[i] === "{") depth += 1;
      else if (code[i] === "}") {
        depth -= 1;
        if (depth === 0) {
          end = i;
          break;
        }
      }
    }
    if (end === -1) break;
    blocks.push(code.slice(open + 1, end));
    idx = end + 1;
  }
  return blocks;
}

/** Locale katalogi (JSON) — xom obyekt. */
function loadCatalog(locale) {
  return JSON.parse(
    readFileSync(path.join(MESSAGES_DIR, `${locale}.json`), "utf8"),
  );
}

/** Obyekt daraxtining SATR bargi yozuvlari: [["a.b.c", qiymat], ...]. */
function flatEntries(node, prefix) {
  const entries = [];
  for (const [key, value] of Object.entries(node)) {
    const full = prefix === "" ? key : `${prefix}.${key}`;
    if (typeof value === "string") entries.push([full, value]);
    else if (value !== null && typeof value === "object") {
      entries.push(...flatEntries(value, full));
    }
  }
  return entries;
}

/** `landing.*` yozuvlari + quyi chegara nazorati (katalog qisqarmasin). */
function landingEntries(locale) {
  const catalog = loadCatalog(locale);
  assert.ok(
    catalog.landing !== undefined,
    `${locale}.json da \`landing\` fazoviy nomi yo'q — katalog buzilgan`,
  );
  const entries = flatEntries(catalog.landing, "landing");
  assert.ok(
    entries.length >= MIN_LANDING_KEYS,
    `${locale}.json \`landing.*\` da atigi ${entries.length} ta satr kaliti bor ` +
      `(kutilgan: kamida ${MIN_LANDING_KEYS}) — skan yuzasi jimgina toraygan`,
  );
  return entries;
}

/**
 * ⛔ KOMPONENT-MATN KANALI (10-06 sabotaj darsi): katalog skani komponent
 * JSX'iga literal yozilgan da'voni KO'RMASDI — o'sha sinov o'lchagan bo'shliq.
 * Bu ekstraktor RENDER BO'LADIGAN matnni oladi: (1) JSX matn tugunlari
 * (`>matn<` — qavs va teg ichidagi kod chiqariladi), (2) JSX ifodasidagi
 * yalang'och satr literallari (`{"matn"}` shakli). `className` ichidagi
 * raqamlar (gap-3, text-2xl) teg ICHIDA — ular bu kanalga tushmaydi.
 */
function renderableTextParts(code) {
  const parts = [];
  for (const m of code.matchAll(/>([^<>{}]+)</gu)) {
    parts.push({ kind: "jsx-matn", text: m[1] });
  }
  for (const m of code.matchAll(/\{\s*(["'`])((?:\\.|(?!\1)[^\\])*)\1\s*\}/gu)) {
    parts.push({ kind: "satr-literal", text: m[2] });
  }
  return parts;
}

/**
 * G-land-4(g) — lotin so'z tokenlari (o'zbek apostroflari bilan).
 * `ts[iy]` naqshiga mos token kirill overrides lug'atida bo'lishi shart:
 * `demonstratsiya` -> «демонстратсия» defekti sof kirill chiqish bergani
 * uchun transliterator darvozalarining birortasi uni ko'rmaydi (B-3).
 */
function latinWordTokens(value) {
  return value.match(/[A-Za-z][A-Za-z'ʼ’]*/gu) ?? [];
}

/* -------------------------------------------------------------------------- */
/* 0-BOSQICH — DARVOZANING O'Z MEXANIZMI                                      */
/* -------------------------------------------------------------------------- */

test("reyestrlar quyi chegaradan kam EMAS, takrorsiz va o'zaro zid emas", () => {
  assert.equal(
    CLIENT_ISLANDS.length,
    CLIENT_ISLANDS_COUNT,
    `klient orollari reyestri ${CLIENT_ISLANDS.length} ta nom — kutilgan AYNAN ` +
      `${CLIENT_ISLANDS_COUNT} (B-1/C yechimi bilan qulflangan; o'zgartirishdan ` +
      "oldin 10-UI-SPEC §4.4 qayta ochilishi shart)",
  );
  assert.equal(
    KEYFRAMES_REGISTRY.length,
    KEYFRAMES_COUNT,
    `@keyframes reyestri ${KEYFRAMES_REGISTRY.length} ta nom — kutilgan AYNAN ` +
      `${KEYFRAMES_COUNT} (8 meros + \`${NEW_KEYFRAME}\`, L-9)`,
  );
  assert.ok(
    ALLOWED_TRANSITION_PROPS.length >= MIN_ALLOWED_TRANSITION_PROPS,
    `ruxsat etilgan transition xossalari reyestrida atigi ` +
      `${ALLOWED_TRANSITION_PROPS.length} ta nom (kutilgan: kamida ` +
      `${MIN_ALLOWED_TRANSITION_PROPS}) — §16.4 to'plami qisqartirilgan`,
  );

  // Takror nom reyestrni «uzun» ko'rsatib chegarani aldab o'tardi.
  for (const [name, list] of [
    ["CLIENT_ISLANDS", CLIENT_ISLANDS],
    ["PROVIDER_NAMESPACES", PROVIDER_NAMESPACES],
    ["ALLOWED_TRANSITION_PROPS", ALLOWED_TRANSITION_PROPS],
    ["BANNED_TRANSITION_PROPS", BANNED_TRANSITION_PROPS],
    ["KEYFRAMES_REGISTRY", KEYFRAMES_REGISTRY],
    ["TIMER_FILES", TIMER_FILES],
  ]) {
    assert.equal(
      new Set(list).size,
      list.length,
      `${name} reyestrida takrorlangan a'zo bor — uzunlik chegarasi aldangan bo'lardi`,
    );
  }

  // Ruxsat va taqiq to'plamlari kesishmasin — darvoza o'z-o'ziga zid bo'lardi.
  const banned = new Set(BANNED_TRANSITION_PROPS);
  assert.deepEqual(
    ALLOWED_TRANSITION_PROPS.filter((p) => banned.has(p)),
    [],
    "ruxsat etilgan va taqiqlangan transition xossalari kesishdi",
  );
});

test("detektorlar sun'iy IJOBIY manbani USHLAYDI (o'z-o'zini tekshiruv)", () => {
  /*
   * Usiz quyidagi hamma «topilmadi» xulosasi BO'SH DETEKTOR ustida ham rost
   * bo'lardi — detektor har doim bo'sh qaytarsa, darvoza abadiy yashil.
   */

  // extractClassBlocks: oddiy, qo'shma va ko'p-selektorli holatlar.
  const cssSample = [
    ".landing-step-fill { transform: scaleY(0); transition: transform 900ms var(--ease-out); }",
    '[data-step="1"] .landing-step-fill { transform: scaleY(0.3333); }',
    ".motion-enter { animation: enter 250ms both; }",
  ].join("\n");
  const sampleBlocks = extractClassBlocks(cssSample);
  assert.equal(sampleBlocks.length, 3, "extractClassBlocks blok sonini adashtirdi");
  assert.deepEqual(
    sampleBlocks.map((b) => b.name),
    ["landing-step-fill", "landing-step-fill", "motion-enter"],
  );

  // transitionProps: shorthand birinchi tokeni, vergulli ro'yxat,
  // transition-property shakli va cubic-bezier ichidagi vergul.
  assert.deepEqual(
    transitionProps("transition: transform 900ms var(--ease-out);"),
    ["transform"],
  );
  assert.deepEqual(
    transitionProps("transition: height 900ms, opacity 150ms;"),
    ["height", "opacity"],
    "sabotaj shakli (L-8) parserdan o'tib ketdi",
  );
  assert.deepEqual(
    transitionProps("transition-property: width, box-shadow;"),
    ["width", "box-shadow"],
  );
  assert.deepEqual(
    transitionProps(
      "transition: transform 300ms cubic-bezier(0.22, 1, 0.36, 1);",
    ),
    ["transform"],
    "cubic-bezier ichidagi vergul segmentni bo'lib yubordi",
  );
  // -duration/-delay xossa nomi tashimaydi — parser ularni sanamaydi.
  assert.deepEqual(transitionProps("transition-duration: 900ms;"), []);
  assert.equal(isBannedTransitionProp("margin-top"), true);
  assert.equal(isBannedTransitionProp("all"), true);
  assert.equal(isBannedTransitionProp("transform"), false);

  // Klient direktivasi: fayl boshida — ha; o'rtadagi inert literal — yo'q.
  assert.equal(hasClientDirective('"use client";\nexport const a = 1;'), true);
  assert.equal(hasClientDirective("\n  'use client';\nlet b;"), true);
  assert.equal(
    hasClientDirective('export const t = "use client";'),
    false,
    "o'rtadagi satr literali direktiva deb sanaldi",
  );

  // Fazoviy nomlar: uchala chaqiruv shakli.
  assert.deepEqual(
    translationNamespaces(
      'useTranslations("landing"); await getTranslations("common");' +
        ' await getTranslations({ locale, namespace: "landing" });',
    ),
    ["landing", "common", "landing"],
  );

  // Provayder kalitlari: oddiy obyekt o'qiladi, spread qizil holat.
  assert.deepEqual(
    providerNamespaces(
      "<NextIntlClientProvider messages={{ common: messages.common, landing: messages.landing }}>",
    ),
    { keys: ["common", "landing"], reason: null },
  );
  assert.equal(
    providerNamespaces(
      "<NextIntlClientProvider messages={{ ...messages }}>",
    ).keys,
    null,
    "spread orqali toraytirish o'qildi deb sanaldi",
  );

  // Inline style bloklari: geometriya topiladi, `--i` topilmaydi.
  const styleSample =
    'a style={{ "--i": 0 }} b style={{ height: "40px", transitionDelay: "70ms" }}';
  const styleBlocks = inlineStyleBlocks(styleSample);
  assert.equal(styleBlocks.length, 2);
  assert.equal(/(?<![\w-])height\s*:/u.test(styleBlocks[0]), false);
  assert.equal(/(?<![\w-])height\s*:/u.test(styleBlocks[1]), true);
});

test("izoh filtrlari faylni YUTIB YUBORMAYDI (runaway nazorati)", () => {
  const js = stripComments(
    'const s = "/* bu izoh EMAS */";\nexport const keep = s;',
  );
  assert.ok(js.includes("export"), "JS izoh filtri `export` ni yutib yubordi");
  assert.ok(
    js.includes("/* bu izoh EMAS */"),
    "satr literali ichidagi matn izoh deb o'chirildi",
  );

  const css = stripCssComments("/* izoh */ .a { color: red; } /* izoh 2 */");
  assert.ok(css.includes(".a { color: red; }"), "CSS filtri qoidani o'chirdi");
  assert.ok(!css.includes("izoh"), "CSS filtri izohni qoldirdi");

  // Haqiqiy fayl ustida ham — readGlobalsCss ichki assertlari ishlaydi.
  readGlobalsCss();
});

/* -------------------------------------------------------------------------- */
/* G-land-1 — LCP YO'LI KLIENTGA BOG'LANMAGAN (SC#5)                          */
/* -------------------------------------------------------------------------- */

test("G-land-1(a): klient orollari to'plami besh nomli reyestrga deepEqual", () => {
  const { all } = marketingSurfaceFiles();

  const directiveFiles = all
    .filter((file) => hasClientDirective(readCode(file)))
    .map((file) => relSrc(file));

  assert.deepEqual(
    [...directiveFiles].sort(),
    [...CLIENT_ISLANDS].sort(),
    "⛔ G-land-1(a) BUZILDI — klient orollari to'plami reyestrdan chetlandi.\n" +
      `  Topildi:  ${[...directiveFiles].sort().join(", ") || "(bo'sh)"}\n` +
      `  Reyestr:  ${[...CLIENT_ISLANDS].sort().join(", ")}\n` +
      "  Yangi orol JIMGINA qo'shilmaydi: LCP yo'lidagi har direktiva h1'ni\n" +
      "  hidratatsiya kutishiga bog'lash xavfi (ROADMAP SC#5) — avval\n" +
      "  10-UI-SPEC §4.4 reyestri ochiq qayta ko'riladi, keyin shu ro'yxat.",
  );
});

test("G-land-1(b): hero.tsx klient direktivasiz VA headline chaqirig'i bor", () => {
  const code = readCode(HERO_FILE);

  const directiveHits = code.split("use client").length - 1;
  assert.equal(
    directiveHits,
    0,
    "⛔ G-land-1(b) BUZILDI — `components/marketing/hero.tsx` da klient " +
      `direktivasi ${directiveHits} marta topildi (kutilgan: 0).\n` +
      "  h1 (LCP nomzodi) klient JS'ga bog'lansa sarlavha hidratatsiya\n" +
      "  kutadi va SC#5 jimgina yiqiladi — sahna alohida orolda\n" +
      "  (hero-scene.tsx), matn ustuni SERVERDA qoladi (§1.2 qoida 1).",
  );

  assert.ok(
    /\bt\(\s*["']hero\.headline["']\s*\)/u.test(code),
    "⛔ G-land-1(b) BUZILDI — `hero.tsx` da `landing.hero.headline` " +
      "chaqirig'i topilmadi: h1 matni tarjima katalogidan kelishi shart " +
      "(qulflangan copy [K-2]).",
  );
  assert.ok(
    /getTranslations\(\s*["']landing["']\s*\)/u.test(code),
    "G-land-1(b): `hero.tsx` `landing` fazoviy nomiga bog'lanmagan — " +
      "headline chaqirig'i boshqa katalogdan o'qiyapti.",
  );
});

test("G-land-1(c): provayder nomlari AYNAN reyestr VA chaqiriqlar uning QISMI", () => {
  // (i) Provayder to'plami — deepEqual.
  const layoutCode = readCode(MARKETING_LAYOUT);
  assert.ok(
    layoutCode.includes("NextIntlClientProvider"),
    "G-land-1(c): `(marketing)/layout.tsx` da NextIntlClientProvider yo'q — " +
      "provayder chegarasi (§4.3) o'chirilgan.",
  );
  const { keys, reason } = providerNamespaces(layoutCode);
  assert.ok(
    keys !== null,
    `⛔ G-land-1(c) BUZILDI — provayder \`messages\` obyektini o'qib bo'lmadi: ` +
      `${reason}. Toraytirish OSHKORA obyekt bilan yozilishi shart — aks holda` +
      " to'liq 1373 kalitli katalog klientga tushadi (L-5, ~27 KB gzip).",
  );
  assert.deepEqual(
    [...keys].sort(),
    [...PROVIDER_NAMESPACES].sort(),
    "⛔ G-land-1(c) BUZILDI — provayderga uzatilgan fazoviy nomlar reyestrdan " +
      `chetlandi.\n  Topildi:  ${[...keys].sort().join(", ")}\n` +
      `  Reyestr:  ${[...PROVIDER_NAMESPACES].sort().join(", ")}\n` +
      "  Har qo'shimcha nom klient payload'ini oshiradi (L-5) — avval\n" +
      "  10-UI-SPEC §4.3, keyin bu reyestr.",
  );

  // (ii) IKKINCHI YARIM (T-10-15): komponent chaqiriqlari reyestrning QISMI.
  // Chetga chiqilganda server render O'TADI (server kontekstda to'liq
  // katalog bor), klient esa MISSING_MESSAGE bilan faqat brauzerda,
  // hidratatsiyadan keyin yiqiladi — next build ham, vitest ham ko'rmaydi.
  const { all } = marketingSurfaceFiles();
  const registry = new Set(PROVIDER_NAMESPACES);
  const problems = [];
  let callCount = 0;
  for (const file of all) {
    for (const namespace of translationNamespaces(readCode(file))) {
      callCount += 1;
      if (!registry.has(namespace)) {
        problems.push(`${relSrc(file)} -> "${namespace}"`);
      }
    }
  }
  assert.ok(
    callCount >= MIN_NAMESPACE_CALLS,
    `G-land-1(c): marketing yuzasida atigi ${callCount} ta tarjima chaqirig'i ` +
      `topildi (kutilgan: kamida ${MIN_NAMESPACE_CALLS}) — detektor yoki yuza buzilgan`,
  );
  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-1(c) BUZILDI — reyestrdan tashqari fazoviy nom chaqirig'i:\n  " +
      problems.join("\n  ") +
      "\n  Bu xato next build'da KO'RINMAYDI: server to'liq katalog bilan\n" +
      "  render qiladi, klient esa MISSING_MESSAGE bilan faqat brauzerda\n" +
      "  yiqiladi (T-10-15). Nom kerak bo'lsa — provayder reyestri bilan\n" +
      "  BIRGA kengaytiriladi.",
  );
});

test("G-land-1(d): [locale]/page.tsx YO'Q va (marketing)/page.tsx BOR (L-7)", () => {
  assert.ok(
    !existsSync(LOCALE_ROOT_PAGE),
    "⛔ G-land-1(d) BUZILDI — `app/[locale]/page.tsx` QAYTA PAYDO BO'LDI.\n" +
      "  `(marketing)/page.tsx` bilan bir URL'ga tushadi — Next 16 build'i\n" +
      "  «Conflicting paths» bilan yiqiladi yoki redirect landing'ni yeydi (L-7).",
  );
  assert.ok(
    existsSync(MARKETING_PAGE),
    "⛔ G-land-1(d) BUZILDI — `(marketing)/page.tsx` YO'Q: ildiz URL 404 — " +
      "anonim tashrifchi landing o'rniga hech nima ko'radi (SC#1).",
  );
});

test("G-land-1(e): sarlavha nishonlari O'LCHANGAN breakpointlarda qoladi", () => {
  /*
   * ⛔⛔ BU DARVOZA — XROMDA O'LCHANGAN RAQAMNING QULFI, uslub qoidasi
   *     EMAS. 260819 da sarlavhaga menyu + tema + kirish tugmasi
   *     qo'shilgach, u planshetlarda gorizontal scroll berdi:
   *
   *       768px → 1051px   820px → 1051px
   *       900px → 1051px   1024px → 1142px   (scrollWidth > clientWidth)
   *
   *     Sabab: beshta menyu havolasi ~490px yeydi va `md:` (768px)
   *     chegarasida u til+tema+kirish bilan bir qatorga sig'maydi.
   *     Overflow sahifaning ENG PASTIDA sezilardi — skrinshotda ham,
   *     `next build` da ham ko'rinmaydi, faqat o'lchov ushlaydi.
   *
   *     Shuning uchun chegaralar qayta hisoblandi va SHU YERDA qulflandi:
   *       · menyu   — `lg:` (1024px)  [o'lchov: 1024 da 1003px talab]
   *       · to'liq til nomlari — `xl:` (1280px)  [1024 da +90px = 1142]
   *       · bitta qator — `sm:` (640px) dan; undan past — ikki qator
   *
   *     Kim bularni `md:` ga qaytarsa, o'sha uchta ekran o'lchamida
   *     scroll QAYTADI. Qaytarish kerak bo'lsa — avval o'lchov.
   */
  const nav = readCode(path.join(SRC, "components/marketing/nav-menu.tsx"));
  assert.ok(
    /className=\{cn\("hidden shrink-0 items-center gap-1 lg:flex/u.test(nav),
    "⛔ G-land-1(e) BUZILDI — menyu `lg:flex` EMAS. `md:flex` da u " +
      "768/820/900/1024px ekranlarning hammasida gorizontal scroll beradi " +
      "(o'lchangan: 1051px talab).",
  );

  const switcher = readCode(
    path.join(SRC, "components/marketing/locale-switcher.tsx"),
  );
  assert.ok(
    switcher.includes('"w-11 xl:w-auto xl:px-3"') &&
      switcher.includes('className="hidden xl:inline"'),
    "⛔ G-land-1(e) BUZILDI — to'liq til nomlari `xl:` dan past ochilyapti. " +
      "Ular +90px yeydi va 1024px da sarlavha 1142px ga chiqadi.",
  );

  const header = readCode(path.join(SRC, "components/marketing/header.tsx"));
  assert.ok(
    header.includes("flex-wrap") && header.includes("sm:flex-nowrap"),
    "⛔ G-land-1(e) BUZILDI — sarlavhaning ikki qatorli mobil rejimi " +
      "yo'qoldi: 375px da brend+til+tema+kirish 496px joy talab qiladi.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-land-3 — GPU XOSSALARI, `transition` LARDA HAM (SC#5)                    */
/* -------------------------------------------------------------------------- */

test("G-land-3(a): har .landing-*/.motion-* sinf transition'i ruxsat to'plamiga QISM", () => {
  const css = readGlobalsCss();
  const blocks = extractClassBlocks(css);

  assert.ok(
    blocks.length >= MIN_CLASS_BLOCKS,
    `\`globals.css\` da atigi ${blocks.length} ta .landing-*/.motion-* ` +
      `selektor-blok topildi (kutilgan: kamida ${MIN_CLASS_BLOCKS}) — parser ` +
      "yoki reyestr jimgina qisqargan",
  );

  const allowed = new Set(ALLOWED_TRANSITION_PROPS);
  const problems = [];
  const bannedHits = [];
  let transitionDeclarations = 0;

  for (const { body, name } of blocks) {
    const props = transitionProps(body);
    transitionDeclarations += props.length;
    for (const prop of props) {
      if (isBannedTransitionProp(prop)) {
        bannedHits.push(`.${name} -> transition \`${prop}\``);
      }
      if (!allowed.has(prop)) {
        problems.push(`.${name} -> transition \`${prop}\``);
      }
    }
  }

  // Parser degeneratsiyasi nazorati: bugun kamida bitta transition bor
  // (.landing-step-fill) — 0 chiqsa parser o'lgan, darvoza bo'sh halqa.
  assert.ok(
    transitionDeclarations >= 1,
    "G-land-3(a): birorta transition deklaratsiyasi topilmadi — " +
      "`.landing-step-fill` ning 900ms tranzitsiyasi bor edi, parser buzilgan",
  );

  assert.deepEqual(
    bannedHits,
    [],
    "⛔ G-land-3(a) BUZILDI — layout-thrash xossasi transition'da:\n  " +
      bannedHits.join("\n  ") +
      "\n  ⛔ Bu G-motion-3(a) ning O'LCHANGAN bo'shlig'i edi (L-8): u faqat\n" +
      "  @keyframes'ni parse qiladi va maket manbasining balandlik-\n" +
      "  tranzitsiyasi jimgina o'tardi. Geometriya xossasi har kadrda layout\n" +
      "  hisobini qo'zg'aydi — arzon Androidda 60fps IMKONSIZ (SC#5).\n" +
      "  Yechim: transform (scaleY/translate) yoki opacity.",
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-3(a) BUZILDI — ruxsat to'plamidan tashqari transition xossasi:\n  " +
      problems.join("\n  ") +
      "\n  Ruxsat etilgan to'plam (10-UI-SPEC §16.4): " +
      ALLOWED_TRANSITION_PROPS.join(", "),
  );
});

test("G-land-3(b): components/marketing/** da inline style geometriyasi 0", () => {
  const { componentFiles } = marketingSurfaceFiles();
  const geometry = /(?<![\w-])(height|width|left|top)\s*:/u;

  const problems = [];
  let styleBlockCount = 0;
  for (const file of componentFiles) {
    const code = readCode(file);
    for (const block of inlineStyleBlocks(code)) {
      styleBlockCount += 1;
      const hit = geometry.exec(block);
      if (hit !== null) {
        problems.push(`${relSrc(file)} -> style ichida \`${hit[1]}:\``);
      }
    }
    // DOM orqali yozish kanali ham yopiq: `node.style.height = ...`.
    for (const m of code.matchAll(/\.style\.(height|width|left|top)\b/gu)) {
      problems.push(`${relSrc(file)} -> \`.style.${m[1]}\` yozuvi`);
    }
  }

  assert.ok(
    styleBlockCount >= MIN_STYLE_BLOCKS,
    `G-land-3(b): marketing komponentlarida atigi ${styleBlockCount} ta inline ` +
      `style bloki topildi (kutilgan: kamida ${MIN_STYLE_BLOCKS} — \`--i\` va ` +
      "transitionDelay bor edi) — detektor buzilgan",
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-3(b) BUZILDI — komponentda inline geometriya:\n  " +
      problems.join("\n  ") +
      "\n  Geometriya komponent faylida UMUMAN yozilmaydi (§10.2 [QAROR],\n" +
      "  T-10-21): daraja deklarativ atribut (data-step) orqali, qiymatlar\n" +
      "  globals.css'da. Ruxsat etilgan inline style — faqat `--i` indeksi\n" +
      "  va transitionDelay stagger'i.",
  );
});

test("G-land-3(c): setInterval 0 · setTimeout faqat hero-scene.tsx da", () => {
  const { componentFiles } = marketingSurfaceFiles();

  const intervalFiles = [];
  const timeoutFiles = [];
  for (const file of componentFiles) {
    const code = readCode(file);
    if (/\bsetInterval\b/u.test(code)) intervalFiles.push(relSrc(file));
    if (/\bsetTimeout\b/u.test(code)) timeoutFiles.push(relSrc(file));
  }

  assert.deepEqual(
    intervalFiles,
    [],
    "⛔ G-land-3(c) BUZILDI — `setInterval` marketing komponentida:\n  " +
      intervalFiles.join("\n  ") +
      "\n  Sahifada avtomatik harakat AYNAN BITTA sahnada (§5.6 mexanizm 4)\n" +
      "  va u taymer REYESTRI bilan boshqariladi. Interval — to'xtatgichsiz\n" +
      "  halqa: ko'rinmas sahifada ham batareya yeydi (T-10-12 sinfi).",
  );

  assert.deepEqual(
    [...timeoutFiles].sort(),
    [...TIMER_FILES].sort(),
    "⛔ G-land-3(c) BUZILDI — kechiktirish-chaqiruv fayllari reyestrdan " +
      `chetlandi.\n  Topildi:  ${[...timeoutFiles].sort().join(", ") || "(bo'sh)"}\n` +
      `  Reyestr:  ${[...TIMER_FILES].sort().join(", ")}\n` +
      "  Avtomatik harakat faqat hero sahnasida (u IO + visibilitychange\n" +
      "  to'xtatgichlari va massiv-reyestr bilan o'lchangan — 10-05).\n" +
      "  Ikkinchi manba paydo bo'lsa — avval 10-UI-SPEC §5.6, keyin reyestr.",
  );
});

test("G-land-3(d): @keyframes reyestri 9 nom va yangisi AYNAN sweep (L-9)", () => {
  const css = readGlobalsCss();
  const definedNames = extractKeyframes(css).map(({ name }) => name);

  assert.equal(
    new Set(definedNames).size,
    definedNames.length,
    "G-land-3(d): bitta @keyframes nomi ikki marta ta'riflangan — " +
      "keyingisi jimgina g'olib bo'lardi",
  );

  const missingLegacy = LEGACY_KEYFRAMES.filter(
    (name) => !definedNames.includes(name),
  );
  assert.deepEqual(
    missingLegacy,
    [],
    "⛔ G-land-3(d) BUZILDI — meros @keyframes nom(lar)i yo'qoldi:\n  " +
      missingLegacy.join(", ") +
      "\n  Mavjud sakkiztasi O'ZGARMAGAN bo'lishi shart (L-9): landing o'z\n" +
      "  animatsiyasini qo'shadi, app'nikini qayta yozmaydi.",
  );

  assert.deepEqual(
    [...definedNames].sort(),
    [...KEYFRAMES_REGISTRY].sort(),
    "⛔ G-land-3(d) BUZILDI — @keyframes to'plami reyestrdan chetlandi.\n" +
      `  Ta'riflangan: ${[...definedNames].sort().join(", ")}\n` +
      `  Reyestr:      ${[...KEYFRAMES_REGISTRY].sort().join(", ")}\n` +
      `  10-fazaning yagona yangi nomi — \`${NEW_KEYFRAME}\` (§5.4); boshqa\n` +
      "  har qanday qo'shimcha avval 10-UI-SPEC ga qaytariladi.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-land-4 — HALOLLIK: YOLG'ON RAQAM VA YOLG'ON DA'VO YO'Q (SC#4, K-7)       */
/* -------------------------------------------------------------------------- */

test("G-land-4/5 detektorlari sun'iy IJOBIY manbani USHLAYDI (o'z-o'zini tekshiruv)", () => {
  // Renderable-matn: braced literal ham, JSX matn tuguni ham topiladi...
  const sabotageSample =
    '<p className="gap-3 text-2xl">{"30% o\'sish"}</p><span>30% foyda</span>';
  const parts = renderableTextParts(sabotageSample);
  assert.ok(
    parts.some((p) => p.kind === "satr-literal" && p.text.includes("30%")),
    "braced satr literali ({\"...\"} shakli — 10-06 sabotaj shakli) topilmadi",
  );
  assert.ok(
    parts.some((p) => p.kind === "jsx-matn" && p.text.includes("30% foyda")),
    "JSX matn tuguni topilmadi",
  );
  // ...className ichidagi raqam esa render matni EMAS (teg ichida qoladi).
  const classOnly = renderableTextParts('<div className="gap-3">{t("x")}</div>');
  assert.equal(
    classOnly.some((p) => /\d/u.test(p.text)),
    false,
    "className ichidagi raqam render matni deb sanaldi (soxta ijobiy)",
  );

  // ts[iy] tokenizatori: defekt sinfini topadi, oddiy so'zni tinch qo'yadi.
  const tokens = latinWordTokens("SBOZOR demonstratsiya sahnasi to'liq");
  assert.ok(tokens.includes("demonstratsiya"));
  assert.equal(/[a-z]+ts[iy]/iu.test("demonstratsiya"), true);
  assert.equal(/[a-z]+ts[iy]/iu.test("sahnasi"), false);

  // Shartli-render detektori: shartsiz shakl o'tadi, `&&` shakli ushlanadi.
  const unconditional = '{t("scene.sampleBadge")}';
  const conditional = '{isDemo && t("scene.sampleBadge")}';
  assert.equal(
    /\{\s*t\(\s*["']scene\.sampleBadge["']\s*\)\s*\}/u.test(unconditional),
    true,
  );
  assert.equal(
    /\{\s*t\(\s*["']scene\.sampleBadge["']\s*\)\s*\}/u.test(conditional),
    false,
    "shartli shakl shartsiz deb sanaldi",
  );
  assert.equal(
    /(?:&&|\?\?|\?)[^{}<>]*t\(\s*["']scene\.sampleBadge["']/u.test(conditional),
    true,
    "`cond && ` naqshi detektordan o'tib ketdi",
  );
});

test("G-land-4(a): sampleBadge chaqirig'i bor VA shartli render ichida EMAS", () => {
  const code = readCode(HERO_SCENE_FILE);

  assert.ok(
    /\bt\(\s*["']scene\.sampleBadge["']\s*\)/u.test(code),
    "⛔ G-land-4(a) BUZILDI — `hero-scene.tsx` da `scene.sampleBadge` " +
      "chaqirig'i YO'Q: namuna-belgisi sahnaning HAR fazasida ko'rinishi " +
      "shart (K-7) — belgisiz sahna real bozor ma'lumoti deb o'qiladi.",
  );

  assert.ok(
    /\{\s*t\(\s*["']scene\.sampleBadge["']\s*\)\s*\}/u.test(code),
    "⛔ G-land-4(a) BUZILDI — `hero-scene.tsx` dagi `scene.sampleBadge` " +
      "chaqirig'i SHARTSIZ `{t(...)}` shaklida emas: belgi oraliq ifoda " +
      "ichiga olingan — har fazada ko'rinish kafolati yo'qoldi (K-7).",
  );

  assert.equal(
    /(?:&&|\?\?|\?)[^{}<>]*t\(\s*["']scene\.sampleBadge["']/u.test(code),
    false,
    "⛔ G-land-4(a) BUZILDI — `scene.sampleBadge` SHARTLI render ichida " +
      "(`cond && ` / ternar naqshi): belgi ba'zi holatlarda yo'qoladi va " +
      "sahna o'sha paytda real ma'lumot taassurotini beradi (T-10-10).",
  );
});

test("G-land-4(b): a11yDescription'da namuna o'zagi uchala locale'da bor", () => {
  for (const locale of LOCALES) {
    const catalog = loadCatalog(locale);
    const value = catalog.landing?.scene?.a11yDescription;
    assert.ok(
      typeof value === "string" && value.length > 0,
      `⛔ G-land-4(b) BUZILDI — ${locale}.json da ` +
        "`landing.scene.a11yDescription` yo'q: skrinrider foydalanuvchisi " +
        "sahna tavsifisiz qoladi (§15.2).",
    );
    const lower = value.toLowerCase();
    assert.ok(
      SAMPLE_ROOTS.some((root) => lower.includes(root)),
      `⛔ G-land-4(b) BUZILDI — ${locale}.json \`a11yDescription\` da namuna ` +
        `o'zagi yo'q (kutilgan: ${SAMPLE_ROOTS.join(" / ")}). Sahna kontenti ` +
        "namunaviy ekani skrinriderga ham yetishi shart (T-10-20) — vizual " +
        "belgi ko'rinmaydigan foydalanuvchiga yolg'on bo'lib qolardi.",
    );
  }
});

test("G-land-4(c): residency.body uchala locale'da VA hero anchor bilan bog'langan", () => {
  for (const locale of LOCALES) {
    const catalog = loadCatalog(locale);
    const value = catalog.landing?.trustBlock?.residency?.body;
    assert.ok(
      typeof value === "string" && value.length > 0,
      `⛔ G-land-4(c) BUZILDI — ${locale}.json da ` +
        "`landing.trustBlock.residency.body` yo'q: rezidentlik bandi bu " +
        "fazaning huquqiy tuguni (§11.2, T-10-13) — qisqa hero yorlig'i " +
        "to'liq halol izohsiz qolardi.",
    );
  }

  const heroCode = readCode(HERO_FILE);
  assert.ok(
    /href="#ishonch"[\s\S]{0,500}?trust\.residency/u.test(heroCode),
    "⛔ G-land-4(c) BUZILDI — `hero.tsx` da `trust.residency` `#ishonch` " +
      "ankeriga BOG'LANMAGAN (§13.5): hero'dagi qisqa da'vo ishonch " +
      "blokidagi to'liq izohga olib borishi shart — havolasiz qisqa shakl " +
      "o'zi mustaqil (va to'liq bo'lmagan) da'voga aylanadi.",
  );
  const trustCode = readCode(TRUST_BLOCK_FILE);
  assert.ok(
    /id="ishonch"/u.test(trustCode),
    "⛔ G-land-4(c) BUZILDI — `trust-block.tsx` da `id=\"ishonch\"` yo'q: " +
      "hero havolasi o'lik ankerga aylanadi (10-06 shartnomasi: anchor " +
      "blokning O'ZIDA, Section'da emas).",
  );
});

test("G-land-4(d): FAQ matni FAQAT katalogdan — komponentda literal 0", () => {
  // (i) JSON-LD kanali: FAQPage page.tsx da va matn kalitlardan keladi.
  const pageCode = readCode(MARKETING_PAGE);
  assert.ok(
    pageCode.includes("application/ld+json"),
    "⛔ G-land-4(d) BUZILDI — `(marketing)/page.tsx` da JSON-LD skript " +
      "bloki yo'q: FAQPage qidiruv natijasida ko'rinmaydi (SC#5, §14.3).",
  );
  assert.ok(
    /FAQPage/u.test(pageCode) &&
      /faq\.q/u.test(pageCode) &&
      /faq\.a/u.test(pageCode),
    "⛔ G-land-4(d) BUZILDI — page.tsx JSON-LD'si `FAQPage` turini " +
      "`landing.faq.q*/a*` kalitlaridan qurmayapti: matn katalogdan " +
      "kelmasa ikkinchi manba tug'iladi (T-10-14).",
  );

  // (ii) Ikki manba mexanik imkonsiz: katalogdagi savol/javob matni birorta
  // marketing faylida LITERAL yozilmagan (uchala locale bo'ylab).
  const faqTexts = [];
  for (const locale of LOCALES) {
    const catalog = loadCatalog(locale);
    for (const n of [1, 2, 3, 4, 5]) {
      for (const kind of ["q", "a"]) {
        const value = catalog.landing?.faq?.[`${kind}${n}`];
        assert.ok(
          typeof value === "string" && value.length > 0,
          `G-land-4(d): ${locale}.json da \`landing.faq.${kind}${n}\` yo'q — ` +
            "FAQ reyestri qisqargan (§13.7: aynan 5 savol).",
        );
        faqTexts.push({ locale, key: `faq.${kind}${n}`, value });
      }
    }
  }
  assert.ok(
    faqTexts.length >= MIN_FAQ_TEXTS,
    `G-land-4(d): atigi ${faqTexts.length} ta FAQ matni yig'ildi (kutilgan: ` +
      `${MIN_FAQ_TEXTS}) — detektor buzilgan`,
  );

  const { all } = marketingSurfaceFiles();
  const problems = [];
  for (const file of all) {
    const code = readCode(file);
    for (const { locale, key, value } of faqTexts) {
      if (code.includes(value)) {
        problems.push(`${relSrc(file)} -> ${locale} ${key} matni LITERAL`);
      }
    }
  }
  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-4(d) BUZILDI — FAQ matni komponentga literal ko'chirilgan:\n  " +
      problems.join("\n  ") +
      "\n  Bitta manba, ikkita chiqish (§14.3): komponent ham, JSON-LD ham\n" +
      "  faqat `landing.faq.*` dan o'qiydi — literal nusxa katalog\n" +
      "  yangilanganda jimgina eskirib qolardi (T-10-14).",
  );
});

test("G-land-4(e): taqiqlangan da'vo tokenlari katalogda VA render matnida 0", () => {
  const problems = [];

  // (i) KATALOG kanali: `landing.*` qiymatlari, uchala locale.
  for (const locale of LOCALES) {
    for (const [key, value] of landingEntries(locale)) {
      const lower = value.toLowerCase();
      for (const token of FORBIDDEN_CLAIM_TOKENS) {
        if (lower.includes(token.toLowerCase())) {
          problems.push(`${locale}: ${key} -> «${token}»`);
        }
      }
    }
  }

  // (ii) KOMPONENT-MATN kanali (10-06 sabotaj darsi): JSX'ga literal
  // yozilgan da'vo katalog skanidan o'tib ketardi — render matni ham
  // skanerlanadi (jsx-matn tugunlari + braced satr literallari).
  const { all } = marketingSurfaceFiles();
  let partCount = 0;
  for (const file of all) {
    for (const { kind, text } of renderableTextParts(readCode(file))) {
      partCount += 1;
      const lower = text.toLowerCase();
      for (const token of FORBIDDEN_CLAIM_TOKENS) {
        if (lower.includes(token.toLowerCase())) {
          problems.push(
            `${relSrc(file)} (${kind}) -> «${token}»: ${JSON.stringify(text.trim().slice(0, 50))}`,
          );
        }
      }
    }
  }
  assert.ok(
    partCount >= MIN_RENDERABLE_PARTS,
    `G-land-4(e): render-matn ekstraktori atigi ${partCount} bo'lak topdi ` +
      `(kutilgan: kamida ${MIN_RENDERABLE_PARTS}) — detektor buzilgan`,
  );

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-4(e) BUZILDI — taqiqlangan da'vo tokeni:\n  " +
      problems.join("\n  ") +
      "\n  Reyestr (K-7, brief §7.5): " +
      FORBIDDEN_CLAIM_TOKENS.join(" · ") +
      "\n  Bu brendning yagona ustunligi — halollik: raqib «ishlab\n" +
      "  chiqilmoqda» deb do'kon badge'larini qo'yadi, biz kamroq va'da\n" +
      "  qilib ko'proq ishonch olamiz. O'lchov yakunlanmagunicha o'sish\n" +
      "  foizi ham, kafolat so'zi ham yozilmaydi.",
  );
});

test("G-land-4(f): landing.pilot.* da raqam 0 — katalogda VA komponentda", () => {
  const problems = [];

  // (i) KATALOG kanali: pilot kalitlari, uchala locale — ATAYLAB QATTIQ:
  // «taxminan 200 rasta» ham yozilmaydi (K-7).
  for (const locale of LOCALES) {
    for (const [key, value] of landingEntries(locale)) {
      if (!key.startsWith("landing.pilot.")) continue;
      if (/\d/u.test(value)) {
        problems.push(`${locale}: ${key} -> «${value.slice(0, 60)}»`);
      }
    }
  }

  // (ii) KOMPONENT kanali: pilot.tsx render matnida ham raqam 0 —
  // katalog toza turib komponentga literal raqam yozilishi mumkin edi
  // (10-06 sabotaji aynan shu shaklda hech narsani qizartirmagan).
  for (const { kind, text } of renderableTextParts(readCode(PILOT_FILE))) {
    if (/\d/u.test(text)) {
      problems.push(
        `pilot.tsx (${kind}) -> ${JSON.stringify(text.trim().slice(0, 50))}`,
      );
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-4(f) BUZILDI — pilot matnida raqam:\n  " +
      problems.join("\n  ") +
      "\n  Pilot bloki FAQAT HOLAT aytadi (K-7): «X% o'sish», «Y so'm\n" +
      "  topildi», «taxminan 200 rasta» — birortasi ham Karmana o'lchovi\n" +
      "  yakunlanmagunicha yozilmaydi. Raqam paydo bo'lishining yagona\n" +
      "  halol yo'li — o'lchov natijasi bilan birga UI-SPEC'ni yangilash.",
  );
});

test("G-land-4(g): landing.* dagi ts[iy] tokenlari kirill lug'atida (B-3)", () => {
  const overrides = JSON.parse(readFileSync(OVERRIDES_FILE, "utf8"));
  const words = overrides.words ?? {};
  assert.ok(
    Object.keys(words).length >= MIN_OVERRIDE_WORDS,
    `G-land-4(g): overrides \`words\` lug'atida atigi ` +
      `${Object.keys(words).length} ta yozuv (kutilgan: kamida ` +
      `${MIN_OVERRIDE_WORDS}) — fayl yoki parser buzilgan`,
  );

  const problems = [];
  for (const [key, value] of landingEntries("uz-Latn")) {
    for (const token of latinWordTokens(value)) {
      if (!/[a-z]+ts[iy]/iu.test(token)) continue;
      const candidates = [
        token,
        token.toLowerCase(),
        token[0].toUpperCase() + token.slice(1).toLowerCase(),
      ];
      if (!candidates.some((candidate) => candidate in words)) {
        problems.push(`${key} -> «${token}»`);
      }
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-4(g) BUZILDI — `ts[iy]` naqshli token kirill lug'atida yo'q:\n  " +
      problems.join("\n  ") +
      "\n  Sabab o'lchangan (B-3): «demonstratsiya» -> «демонстратсия»\n" +
      "  semantik defekti SOF KIRILL chiqish beradi — transliterator\n" +
      "  darvozalarining birortasi uni ko'rmaydi. Har bunday so'z\n" +
      "  `uz-Cyrl.overrides.json` `words` lug'atiga to'g'ri kirill shakli\n" +
      "  bilan qo'shilishi shart. ⛔ Qamrov `landing.*` bilan CHEGARALANGAN\n" +
      "  — meros defektlar (10-02 deferred-items) bu fazani bloklamasin.",
  );
});

/* -------------------------------------------------------------------------- */
/* G-land-5 — TIPOGRAFIYA VA BO'SHLIQ KENGAYTMASI (§0.2, §7, §8.2)            */
/* -------------------------------------------------------------------------- */

test("G-land-5(a): text-hero fayl-reyestrga TENG va faylda AYNAN 1 marta", () => {
  const srcFiles = listProductFiles(SRC, CODE_EXTENSIONS);
  assert.ok(
    srcFiles.length >= MIN_SRC_FILES,
    `\`src/**\` da atigi ${srcFiles.length} ta mahsulot fayli bor ` +
      `(kutilgan: kamida ${MIN_SRC_FILES}) — skan yuzasi jimgina toraygan`,
  );

  const hits = new Map();
  for (const file of srcFiles) {
    const count = [...readCode(file).matchAll(/(?<![-\w])text-hero\b/gu)]
      .length;
    if (count > 0) hits.set(relSrc(file), count);
  }

  // 1-qatlam: FAYL reyestri (deepEqual).
  assert.deepEqual(
    [...hits.keys()].sort(),
    [...TEXT_HERO_FILES].sort(),
    "⛔ G-land-5(a) BUZILDI — hero-o'lcham utilitasi fayl-reyestrdan " +
      `chetlandi.\n  Topildi:  ${[...hits.keys()].sort().join(", ") || "(bo'sh)"}\n` +
      `  Reyestr:  ${[...TEXT_HERO_FILES].sort().join(", ")}\n` +
      "  `text-hero` — bir martalik display registri (§7.1.1), matn\n" +
      "  shkalasining a'zosi EMAS: ikkinchi uy ikkinchi vizual ovoz demak.",
  );

  // 2-qatlam: ELEMENT sanog'i — faqat fayl qulfi bo'lsa hero faylining
  // ichida ikkinchi hero-o'lchamli sarlavha JIMGINA paydo bo'lardi.
  for (const registered of TEXT_HERO_FILES) {
    assert.equal(
      hits.get(registered),
      1,
      `⛔ G-land-5(a) BUZILDI — \`${registered}\` da hero-o'lcham utilitasi ` +
        `${hits.get(registered) ?? 0} marta (kutilgan: AYNAN 1). Sahifada ` +
        "bitta h1, bitta hero ovozi (§15.11/§7.1.1) — ikkinchi uchrashuv " +
        "ikkinchi sarlavha demak va u fayl qulfidan o'tib ketardi.",
    );
  }
});

test("G-land-5(b): --text-hero @theme'da bor va qiymati clamp( bilan", () => {
  const css = readGlobalsCss();
  const theme = extractBlock(css, "@theme");
  assert.ok(
    theme !== null,
    "G-land-5(b): `globals.css` da `@theme` bloki topilmadi — token " +
      "reyestri butunlay yo'qolgan",
  );
  assert.ok(
    /--text-hero\s*:\s*clamp\(/u.test(theme),
    "⛔ G-land-5(b) BUZILDI — `--text-hero` `@theme` blokida yo'q yoki " +
      "qiymati `clamp(` bilan boshlanmaydi. Suyuq o'lcham (§7.1.1: telefonda " +
      "28px, proyektorda 44px) qotib qolgan qiymatga almashsa mobil hero " +
      "ekranni yeydi yoki desktop hero mayda qoladi.",
  );
});

test("G-land-5(c): seksiya bo'shliq qiymatlari FAQAT section.tsx da", () => {
  const { all } = marketingSurfaceFiles();

  const spacingFiles = [];
  for (const file of all) {
    if (/\bpy-16\b|\bpy-24\b/u.test(readCode(file))) {
      spacingFiles.push(relSrc(file));
    }
  }

  assert.deepEqual(
    [...spacingFiles].sort(),
    [...SECTION_SPACING_FILES].sort(),
    "⛔ G-land-5(c) BUZILDI — seksiya bo'shlig'i reyestrdan chetlandi.\n" +
      `  Topildi:  ${[...spacingFiles].sort().join(", ") || "(bo'sh)"}\n` +
      `  Reyestr:  ${[...SECTION_SPACING_FILES].sort().join(", ")}\n` +
      "  Vertikal ritm FAQAT `<Section>` orqali (§8.2): qiymat ikkinchi\n" +
      "  faylda takrorlansa ritm ikki manbadan boshqarilib siljiydi.",
  );
});

test("G-land-5(d): marketing yuzasida text-base/3xl/ixtiyoriy/font-medium 0", () => {
  const { all } = marketingSurfaceFiles();

  const tokens = [
    ["text-base", /\btext-base\b/gu],
    ["text-3xl", /\btext-3xl\b/gu],
    ["font-medium", /\bfont-medium\b/gu],
  ];

  const problems = [];
  for (const file of all) {
    const code = readCode(file);
    for (const [name, pattern] of tokens) {
      for (const m of code.matchAll(pattern)) {
        problems.push(`${relSrc(file)} -> \`${m[0] ?? name}\``);
      }
    }
    if (code.includes("text-[")) {
      problems.push(`${relSrc(file)} -> \`text-[\` (ixtiyoriy o'lcham)`);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-5(d) BUZILDI — taqiqlangan tipografiya tokeni:\n  " +
      problems.join("\n  ") +
      "\n  SABAB (bu darvozaning butun qiymati): mavjud chegaralar TO'LGAN\n" +
      "  [L-2] — `text-base` 7/7, `font-medium` 21/21 butun src bo'ylab.\n" +
      "  Landing'ning birinchi 16px matni `typography.test.mjs` zanjirini\n" +
      "  qizartiradi va u faqat «7 dan oshdi» derdi. Yechim: matn rollari\n" +
      "  `text-sm`/`text-xs`/`text-lg`/`text-2xl`, og'irlik `font-semibold`/" +
      "\n  `font-normal` (§7.1).",
  );
});

test("G-land-5(e): text-display components/marketing/** da 0 (L-4)", () => {
  const { componentFiles } = marketingSurfaceFiles();

  const problems = [];
  for (const file of componentFiles) {
    for (const m of readCode(file).matchAll(/(?<![-\w])text-display\b/gu)) {
      problems.push(`${relSrc(file)} -> \`${m[0]}\``);
    }
  }

  assert.deepEqual(
    problems,
    [],
    "⛔ G-land-5(e) BUZILDI — displey-pul utilitasi marketing faylida:\n  " +
      problems.join("\n  ") +
      "\n  `text-display` — PUL ROLI va reyestri `typography.test.mjs` ning\n" +
      "  `TEXT_DISPLAY_FILES` bilan IKKI app fayliga deepEqual qulflangan\n" +
      "  [L-4]: uchinchi fayl o'sha darvozani ham qizartiradi. Hero o'lchami\n" +
      "  uchun alohida `--text-hero` roli bor (G-land-5(a,b)).",
  );
});

/* -------------------------------------------------------------------------- */
/* REYESTR NAZORATI — darvoza o'zini o'zi o'lchaydi                           */
/* -------------------------------------------------------------------------- */

test("REYESTR NAZORATI: child_process yo'q, reyestrlar jimgina qisqarmagan", () => {
  /*
   * (1) Bu modul MAVJUD darvozalarni qayta yugurtirmaydi (`gate:fast`
   * byudjeti, §16.4): subprocess kanallarining har uchalasi ham manbada
   * yo'qligi tekshiriladi. Regekslar o'z-o'ziga mos kelmaydi — ular
   * qidiradigan matn shakli regeks literalining o'zida uchramaydi.
   */
  const own = readFileSync(import.meta.filename, "utf8");
  assert.equal(
    /require\(\s*["'](?:node:)?child_process["']\s*\)/u.test(own),
    false,
    "REYESTR NAZORATI: modul `child_process` ni require qilyapti — mavjud " +
      "darvozalarni qayta yugurtirish gate:fast byudjetini (200 s) yeydi",
  );
  assert.equal(
    /from\s+["'](?:node:)?child_process["']/u.test(own),
    false,
    "REYESTR NAZORATI: modul `child_process` dan import qilyapti — " +
      "subprocess kanali bu faylda taqiq (§16.4 byudjet qarori)",
  );
  assert.equal(
    /\bexecSync\s*\(/u.test(own),
    false,
    "REYESTR NAZORATI: modul `execSync` chaqiryapti — sof matn/CSS parse " +
      "sharti buzilgan",
  );

  /*
   * (2) Reyestrlar jimgina qisqarsa darvoza BO'SH HALQA bo'lib yashil
   * qolardi — quyi chegaralar shu holatni qizartiradi (§16.3 ruhi).
   */
  assert.ok(
    FORBIDDEN_CLAIM_TOKENS.length >= MIN_FORBIDDEN_CLAIM_TOKENS,
    `taqiqlangan da'vo tokenlari reyestri ${FORBIDDEN_CLAIM_TOKENS.length} ta ` +
      `(kutilgan: kamida ${MIN_FORBIDDEN_CLAIM_TOKENS}) — G-land-4(e) qamrovi ` +
      "jimgina qisqargan",
  );
  assert.equal(
    KEYFRAMES_REGISTRY.length,
    KEYFRAMES_COUNT,
    `@keyframes reyestri ${KEYFRAMES_REGISTRY.length} ta nom (kutilgan: AYNAN ` +
      `${KEYFRAMES_COUNT}) — G-land-3(d) qamrovi o'zgargan`,
  );
  assert.equal(
    CLIENT_ISLANDS.length,
    CLIENT_ISLANDS_COUNT,
    `klient orollari reyestri ${CLIENT_ISLANDS.length} ta (kutilgan: AYNAN ` +
      `${CLIENT_ISLANDS_COUNT}) — G-land-1(a) qamrovi o'zgargan`,
  );

  for (const [name, list] of [
    ["FORBIDDEN_CLAIM_TOKENS", FORBIDDEN_CLAIM_TOKENS],
    ["SAMPLE_ROOTS", SAMPLE_ROOTS],
    ["TEXT_HERO_FILES", TEXT_HERO_FILES],
    ["SECTION_SPACING_FILES", SECTION_SPACING_FILES],
    ["LOCALES", LOCALES],
  ]) {
    assert.equal(
      new Set(list).size,
      list.length,
      `${name} reyestrida takrorlangan a'zo bor — chegara aldangan bo'lardi`,
    );
  }
});
