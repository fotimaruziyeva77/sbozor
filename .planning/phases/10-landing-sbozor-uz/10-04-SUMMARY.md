---
phase: 10-landing-sbozor-uz
plan: 04
subsystem: frontend-landing-conversion-seo
tags: [demo-form, honeypot, dwell, privacy, sitemap, robots, og-image, ssg]
requires:
  - "10-01 (POST /api/v1/public/demo-requests kontrakti + DEMO_ERROR_CODES)"
  - "10-02 (landing.form.*/landing.privacy.* kalitlari, Button size=hero)"
  - "10-03 ((marketing) qobiq: Header/Footer/Section, toraytirilgan provayder)"
provides:
  - "demo-errors.ts — DEMO_ERROR_CODES ko'zgusi + demoErrorMessageKey (zodsiz, og'ir modulsiz)"
  - "demo-form.tsx — yagona anonim yozuv oroli: literal yo'l + lokal zod + xom fetch"
  - "maxfiylik/page.tsx — K-8 majburiy sahifa, 7 bo'lim, 3 til SSG, hreflang metadata"
  - "sitemap.ts/robots.ts — src/app ILDIZIda; robots Disallow katalogdan HOSILA"
  - "public/og/sbozor-og.png — 1200×630 statik, til-neytral (next/og YO'Q)"
affects:
  - "10-07: page.tsx DemoForm'ni #demo seksiyasiga mount qiladi va OG'ni generateMetadata'ga ulaydi"
  - "10-08: error-codes.test.mjs oltinchi juftligi demo-errors.ts ko'zgusini backendga bog'laydi"
tech-stack:
  added: []
  patterns:
    - "Klient oroli import-byudjeti: skelet analogdan, og'ir modul chegarasi manba-skan testida (B-2)"
    - "Rich-text tegi tarjimada: <privacy> tegi transliterator PROTECTED_SEGMENT sinfi bilan omon qoladi"
    - "Robots Disallow ro'yxati (app)/(auth) kataloglaridan readdirSync bilan hosila (build vaqtida)"
key-files:
  created:
    - frontend/src/lib/demo-errors.ts
    - frontend/src/components/marketing/demo-form.tsx
    - frontend/src/components/marketing/demo-form.test.tsx
    - frontend/src/app/[locale]/(marketing)/maxfiylik/page.tsx
    - frontend/src/app/sitemap.ts
    - frontend/src/app/robots.ts
    - frontend/public/og/sbozor-og.png
  modified:
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/scripts/gen-cyrillic.test.mjs
    - .env.example
key-decisions:
  - "Rozilik havolasi yorliq ICHIDA (§15.4) — matn o'zgarmasdan <privacy> rich-tegi orqali; lotin-qoldiq darvozasi teg sinfini transliteratorning o'z daxlsizligi bilan tenglashtirdi"
  - "stall_count uchun maxsus kalit YO'Q (yopiq copy reyestri) — diapazon xatosi form.error.validation matni bilan ko'rinadi"
  - "Dwell muhri mount EFFEKTIDA (react-hooks/purity) — renderda Date.now yo'q; muhr yo'q bo'lsa ham jim shox"
  - "T-10-07 oshkoraligi s3.body MATNIga kiritildi (yangi kalit emas) — kalit-parity va 16-kalitlik privacy reyestri o'zgarmadi"
metrics:
  duration: "~35 min"
  completed: "2026-08-17T13:26:00Z"
  tasks: 3
  commits: 4
---

# Phase 10 Plan 04: Demo-forma, maxfiylik sahifasi va SEO infra Summary

**Bir qator:** Anonim demo-forma `login-form` skeletida, lekin 69 KB gz zod-grafisiz (literal yo'l + lokal sxema + xom fetch, B-2 quli manba-skan testida) + K-8 maxfiylik sahifasi (7 bo'lim, T-10-07 OSHKORA) + `sitemap.ts`/`robots.ts` (Disallow HOSILA) + 8.4 KB statik OG PNG — 350 skript-testi va 1186 vitest yashil, build 86 marshrut.

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 (RED) | Sakkiz xulq bandi + B-2 manba quli (yiqilgan holda) | `866824b` | demo-form.test.tsx |
| 1 (GREEN) | demo-errors ko'zgusi + demo-forma | `3532598` | demo-errors.ts, demo-form.tsx, consent rich-tegi (3 til + darvoza) |
| 2 | Maxfiylik siyosati sahifasi (K-8) | `cd61b58` | maxfiylik/page.tsx, s3 T-10-07 matni (3 til) |
| 3 | sitemap/robots/OG/env | `56c74af` | sitemap.ts, robots.ts, sbozor-og.png, .env.example |

## Nima qurildi

- **`demo-errors.ts`** — `nvr-errors.ts` naqshi, lekin bitta-kalit shakli: `DEMO_ERROR_CODES` (4 kod, literal massiv) + `demoErrorMessageKey` switch (`rate_limited`→rateLimited, `invalid_phone`→phoneInvalid, `validation_error`→validation, `delivery_failed` va noma'lum→body). Zod ham, sxema katalogi ham import qilinmaydi — sof lug'at.
- **`demo-form.tsx`** — `login-form.tsx` skeleti (react-hook-form + zodResolver + bitta alert + `disabled={isSubmitting}`), lekin: yo'l LITERAL (`/api/v1/public/demo-requests`), sxema LOKAL, so'rov XOM `fetch` (`res.ok`/`res.status` + `detail`ni ehtiyotkor o'qish: satr→kod, massiv→`validation_error`, zaxira holat-kod xaritasi). Telefon: faqat raqam sanog'i ≥9 (qattiq regeks YO'Q, T-10-11). Honeypot `website` (sr-only + aria-hidden + tabIndex −1) va dwell ≥3s — ikkalasi ham `fetch`siz JIM muvaffaqiyat. Muvaffaqiyat forma O'RNIDA (`role="status"` + `aria-live="polite"` + `.motion-enter`), xatoda forma SAQLANADI (`role="alert"` + fokus). `delivery_failed`da `NEXT_PUBLIC_CONTACT_PHONE` shoxi: bor→`{phone}` bilan, yo'q→`bodyNoPhone` (bo'sh qavs YO'Q, O-06).
- **Rozilik yorlig'i** — maxfiylik havolasi yorliq ICHIDA: `form.consent` matniga `<privacy>` rich-tegi qo'shildi (ko'rinadigan matn AYNAN o'zgarishsiz); transliterator teglarni `PROTECTED_SEGMENT` bilan o'zi asraydi, lotin-qoldiq darvozasiga o'sha sinf naqshi qo'shildi.
- **`maxfiylik/page.tsx`** — Server Component, `(marketing)` skeleti ayna; `generateMetadata`: `canonical` + uchala `hreflang` (prefikslar `i18n/routing.ts`dan hosila) + `robots: {index: true}`. Yetti bo'lim `landing.privacy.s1..s7`dan; s3 endi T-10-07 ni OSHKORA aytadi (Telegram serverlari O'zR hududidan tashqarida; faqat matn, rasm/fayl hech qachon). Cookie-banner YO'Q [QAROR].
- **`sitemap.ts`** — 6 yozuv (3 ildiz + 3 maxfiylik), har birida `alternates.languages`; Request-time API yo'q → statik.
- **`robots.ts`** — `Allow /` + `Disallow`: `/api/` + `(app)`/`(auth)` kataloglaridan HOSILA 19 segment (`/*/dashboard`, `/*/collect`, `/*/login`, …); `Sitemap:` havolasi. `readdirSync` build vaqtida yuguradi (marshrut statik).
- **OG PNG** — o'z PNG-yozuvchisi bilan (nol yangi bog'liqlik): 1200×630, 8 381 bayt, token ranglar oklch→sRGB matematikasi bilan (iliq fon, accent belgi, BITTA amber katak), til-neytral.
- **`.env.example`** — `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_CONTACT_PHONE` (ixtiyoriy, O-06 izohi bilan), `DEMO_REQUEST_CHAT_ID` (bo'sh→`TELEGRAM_CHAT_ID`ga tushadi).

## Tekshiruv natijalari

| O'lchov | Natija |
|---|---|
| `demo-form.test.tsx` | 11/11 yashil (8 xulq bandi + 3 qo'shimcha: 6b/6c telefon shoxlari, B-2 skan) |
| `npm test` (to'liq) | skript darvozalari 350/350 + vitest **101 fayl / 1186 test** yashil |
| `next build` | exit 0; prerender **86** marshrut = 84 sahifa (81 + 3 `maxfiylik`) + `robots.txt` + `sitemap.xml` |
| `maxfiylik` prerender | `/uz-Latn`, `/uz-Cyrl`, `/ru` — 3/3; HTML'da h1=1, h2=7, canonical + 3 hreflang + `robots index` |
| `typecheck` / `lint` (to'liq) | exit 0 / exit 0 |
| `robots.txt` tanasi | 19 hosila segment + `/api/`, `Allow /`, `Sitemap:` — build chiqishida o'lchandi |
| `sitemap.xml` tanasi | 6 `<url>`, har birida 3 `xhtml:link hreflang` (`/uz`, `/uz-cyrl`, `/ru` prefikslari) |
| OG PNG | IHDR **1200×630** o'qib tasdiqlandi; `next/og`/`ImageResponse` — 0 uchrashuv |
| Yangi npm paketi | **0** (`package.json` tegilmagan) |

## Sabotaj o'lchovlari

**1. (reja #4a) `demo-form.tsx` tugmasiga rozilik sharti qo'shildi** (`disabled={isSubmitting || !watch("consent")}`, modul import qilinadigan holda):
- **O'lchandi:** `submit-gate.test.mjs` **QIZARDI** — `components/marketing/demo-form.tsx -> ["watch"]` (D-1 qoldiq detektori). Qaytarildi, darvoza yana yashil.

**2. (reja #4b) `import { apiFetch } from "@/lib/api-client"` qo'shildi** (`void apiFetch` bilan ishlatilgan, modul import qilinadigan holda):
- **O'lchandi:** `demo-form.test.tsx` B-2 quli **QIZARDI** («taqiqlangan token demo-form.tsx da: api-client»), qolgan 10 test yashil — ya'ni sabotaj yig'ilishni emas, mezonni o'lchadi. Qaytarildi.
- **Chunk jadvali haqida halol qayd:** reja «bugun `next build` chunk jadvalida farq KO'RINADI» degan edi — bu BUGUN o'lchab bo'lmaydi: `demo-form.tsx` hali birorta marshrutga mount qilinmagan (10-07 ishi), toza buildning `.next/static` chunklarida `public/demo-requests` literali **0 marta** (grep bilan o'lchandi) — orol klient grafida umuman yo'q, ya'ni sabotaj importi ham jadvalga tushmasdi. Bugungi BOG'LOVCHI o'lchov — B-2 manba quli (yuqorida, qizardi); chunk-farq o'lchovi 10-07 da orol mount bo'lganda `landing-surface.test.mjs` B-2 regressiya quliga o'tadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - §15.4 talabi] Rozilik havolasi uchun tarjima fayllari va lotin-qoldiq darvozasi**
- **Found during:** Task 1
- **Issue:** §15.4 havolani checkbox yorlig'i ICHIDA talab qiladi; `form.consent` yalpi matn edi — havolani matn ichiga faqat rich-teg bilan qo'yish mumkin, teg esa lotin-qoldiq darvozasida qizarardi.
- **Fix:** `form.consent`ga `<privacy>` tegi (uz-Latn/ru, ko'rinadigan matn o'zgarishsiz; `form.consent` K-2 qulf ro'yxatida EMAS), `uz-Cyrl.json` regeneratsiya, `gen-cyrillic.test.mjs` `allowed` regeksiga teg-sinf naqshi (`<\/?[A-Za-z][^>]*>`) — bu akronim yozuvi emas, transliteratorning O'Z `PROTECTED_SEGMENT` sinfini (URL/e-mail/teg) darvozada tenglashtirish; darvoza 67/67 yashil.
- **Files modified:** frontend/messages/{uz-Latn,ru,uz-Cyrl}.json, frontend/scripts/gen-cyrillic.test.mjs
- **Commit:** 3532598

**2. [Rule 2 - Reja Task 2 talabi] s3 bo'limiga T-10-07 oshkoralik matni**
- **Found during:** Task 2
- **Issue:** Reja s3 bo'limidan T-10-07 ni OSHKORA e'lon qilishni talab qiladi; 10-02 kiritgan `privacy.s3.body` chegara oshkoraligini o'z ichiga olmagan edi.
- **Fix:** `s3.body` MATNI kengaytirildi (yangi kalit emas — kalit-parity va 16-kalitlik reyestr o'zgarmadi): «Telegram serverlari O'zbekiston hududidan tashqarida… faqat so'rov matni boradi; rasm yoki fayl hech qachon» (uz/ru + regen uz-Cyrl).
- **Files modified:** frontend/messages/{uz-Latn,ru,uz-Cyrl}.json
- **Commit:** cd61b58

**3. [Rule 1 - Lint] React Compiler qoidalari (`react-hooks/purity`, `react-hooks/refs`)**
- **Found during:** Task 1 (eslint)
- **Issue:** `useRef(Date.now())` renderda nopok chaqiruv; `handleSubmit(onSubmit)` JSX'da render paytida chaqirilib, ref o'qiydigan `onSubmit`ni render yo'liga bog'lagan.
- **Fix:** mount muhri `useEffect`ga (`mountedAtRef.current ??= Date.now()`), `handleSubmit(onSubmit)(event)` hodisa o'rovchisi ichiga; muhr `null` bo'lsa dwell «juda tez» jim shoxiga tushadi.
- **Files modified:** frontend/src/components/marketing/demo-form.tsx
- **Commit:** 3532598

**4. [Rule 1 - Build tip xatosi] `routing.localePrefix` ittifoq tipi**
- **Found during:** Task 2 (`next build` type check)
- **Issue:** `localePrefix` tipi `{mode:"never"}`ni ham qamraydi — `.prefixes`ga to'g'ridan-to'g'ri murojaat build'ni yiqitdi.
- **Fix:** `typeof config === "object" && "prefixes" in config` toraytirish (maxfiylik page + sitemap.ts, ikkalasida bir xil hosila funksiya).
- **Files modified:** maxfiylik/page.tsx, sitemap.ts
- **Commit:** cd61b58, 56c74af

**5. [Rule 1 - Test infratuzilma] jsdom'da Next navigatsiya moduli**
- **Found during:** Task 1 GREEN (birinchi vitest yugurishi)
- **Issue:** `@/i18n/navigation` jsdom'da `next/navigation`ni hal qila olmaydi (`locale-switcher.test.tsx` bilan ayni holat).
- **Fix:** Testda `vi.mock("@/i18n/navigation")` — `Link` oddiy `<a>` sifatida (mavjud naqsh ko'chirildi).
- **Files modified:** frontend/src/components/marketing/demo-form.test.tsx
- **Commit:** 3532598

Boshqa jihatlarda reja aynan yozilganidek bajarildi.

## Known Stubs

| Stub | Fayl | Sabab |
|------|------|-------|
| `DemoForm` hali sahifaga mount qilinmagan | `(marketing)/page.tsx` | ATAYIN — 10-07 page.tsx'ni qayta yozib formani `#demo` seksiyasiga qo'yadi (reja frontmatter `affects`); orol o'zi to'liq ishlaydi va 11 test bilan o'lchangan |
| OG rasm `generateMetadata`ga ulanmagan | `(marketing)/page.tsx` | `landing.meta.ogAlt` bilan ulash — 10-07 `generateMetadata` ishi (reja Task 3 matni buni ochiq aytadi) |

## Threat Flags

Yangi qamrovlanmagan yuza YO'Q. Reja threat-registri qo'llandi: **T-10-01** (honeypot `sr-only`+`aria-hidden`+`tabIndex -1`, dwell ≥3s — ikkala shox `fetch`siz, testda o'lchandi), **T-10-09** (`robots.ts` Disallow katalogdan hosila — build chiqishida 19 segment), **T-10-11** (klientda qattiq regeks YO'Q — faqat raqam sanog'i), **T-10-19** (uchinchi tomon so'rovi 0 — CAPTCHA/analitika/shrift yo'q; maxfiylik s5 shuni e'lon qiladi), **T-10-07** (accept+disclose — s3 matni chegara faktini OSHKORA yozadi), **T-10-10** (maxfiylik sahifasi tenant so'rovisiz SSG).

## Keyingi bosqichga eslatmalar

- 10-07: `DemoForm`ni `#demo` seksiyasiga mount qilganda payload jadvalini o'lchash kerak — react-hook-form+zod arzon chunki (~11 KB gz) BIRINCHI marta klient grafiga qo'shiladi; B-2 regressiya quli (`landing-surface.test.mjs`) og'ir grafni bloklashda davom etadi.
- 10-07 `generateMetadata`: `openGraph.images: [{url: "/og/sbozor-og.png", width: 1200, height: 630, alt: t("meta.ogAlt")}]` — rasm shu rejada tayyor.
- 10-08 `error-codes.test.mjs`: oltinchi juftlik `schemas.py::DEMO_ERROR_CODES` ↔ `demo-errors.ts::DEMO_ERROR_CODES` ↔ `landing.form.*` kalitlari (frontmatter `affects`).
- `robots.txt`da `markets` segmenti Disallow — bu `(app)` katalogidan hosila va to'g'ri (wizard app ichida); landing ochiq qoladi.

## Self-Check: PASSED

- [x] 7 yaratilgan fayl mavjud: demo-errors.ts, demo-form.tsx, demo-form.test.tsx, maxfiylik/page.tsx, sitemap.ts, robots.ts, sbozor-og.png
- [x] To'rtala commit tarixda: 866824b, 3532598, cd61b58, 56c74af
- [x] `git status` toza (sabotajlar to'liq qaytarilgan)
- [x] STATE.md / ROADMAP.md / REQUIREMENTS.md TEGILMADI
