---
phase: 10-landing-sbozor-uz
plan: 07
subsystem: frontend-landing-composition-gates
tags: [landing, composition, json-ld, metadata, hreflang, gates, honesty, timezone]
requires:
  - "10-04 (DemoForm oroli, /og/sbozor-og.png, sitemap/robots)"
  - "10-05 (Hero server matn + HeroScene 12s sikl, text-hero yagona uyi)"
  - "10-06 (PainCards/Proof/RoleCards/TrustBlock/Pilot/Faq/StepLine/Reveal)"
provides:
  - "(marketing)/page.tsx — 11 blok yakuniy kompozitsiya + generateMetadata (OG/hreflang/canonical) + JSON-LD (Organization + FAQPage, rasmiy escape)"
  - "scripts/landing-surface.test.mjs — G-land-1/3/4/5 (20 band) bitta sof matn/CSS parse faylida, extractClassBlocks transition-parseri bilan"
  - "AppProviders timeZone kontrakti — klient provayder Asia/Tashkent'ni oshkora oladi (ENVIRONMENT_FALLBACK 4x -> 0)"
affects:
  - "10-08 (faza darvozasi: gate byudjeti +0,74s eng yomon; HUMAN-UAT LCP/Lighthouse/payload)"
tech-stack:
  added: []
  patterns:
    - "JSON-LD Server Component'da: JSON.stringify(...).replace(/</g, escape) — Next rasmiy naqshi (T-10-08)"
    - "extractClassBlocks — @keyframes qavs-balans texnikasi sinf selektorlariga ko'chirildi (L-8 bo'shlig'i)"
    - "Komponent-MATN kanali: renderableTextParts (JSX matn tugunlari + braced satr literallari) — katalog skanining ko'r nuqtasini yopadi"
    - "Klient provayderga timeZone oshkora: avtomatik meros faqat Server Component kontekstida ishlaydi"
key-files:
  created:
    - frontend/scripts/landing-surface.test.mjs
  modified:
    - frontend/src/app/[locale]/(marketing)/page.tsx
    - frontend/src/components/shell/app-providers.tsx
    - frontend/src/app/[locale]/(app)/layout.tsx
    - frontend/src/app/[locale]/(auth)/layout.tsx
decisions:
  - "OG locale ll_CC shaklida: uz-Latn/uz-Cyrl ikkalasi uz_UZ (OG protokoli yozuv subtag'ini bilmaydi) — yozuv farqini hreflang alternates ko'taradi"
  - "Organization.contactPoint faqat NEXT_PUBLIC_CONTACT_PHONE berilganda (O-06 presedenti — yolg'on kanal ochilmaydi)"
  - "Demo-seksiya h2/subtitle sahifada, Card ichida (Section title'siz — 10-06 shartnomasi buzilmadi); blok Reveal bilan o'raladi"
  - "G-land-1(a) direktiva-pozitsiya regeksi bilan (fayl boshida), (b) esa qattiqroq substring-0 — LCP-kritik faylga ikki xil qulf"
  - "G-land-4(e)/(f) IKKI kanalli: katalog qiymatlari + komponent render-matni (10-06 SUMMARY nuansi bo'yicha; nazorat B bilan isbotlandi)"
  - "Reja sarlavhasidagi «17 band» — rejalovchi arifmetikasi; sanab chiqilgan bandlar 4+4+7+5=20 va HAMMASI bajarildi (kamaytirilmadi)"
metrics:
  duration: "~85 min"
  completed: "2026-08-17T15:35:00Z"
  tasks: 3
  commits: 4
---

# Phase 10 Plan 07: Landing kompozitsiyasi va to'rt darvoza Summary

**Bir qator:** `page.tsx` 11 blokni yig'di (metadata OG/hreflang/canonical + Organization/FAQPage JSON-LD rasmiy escape bilan, matn faqat katalogdan) + `landing-surface.test.mjs` to'rt darvozaning 20 bandini bitta 0,74s (eng yomon) parse faylida o'lchaydi — 6 sabotaj + 2 nazorat har biri mo'ljallangan bandni qizartirdi, ENVIRONMENT_FALLBACK tashxis qilinib timeZone tuzatishi bilan 4x -> 0 ga tushdi.

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 | page.tsx — 11 blok, generateMetadata, JSON-LD | `fc1fa5b` | (marketing)/page.tsx |
| — | ENVIRONMENT_FALLBACK tashxisi + tuzatish (orkestrator bandi) | `3982344` | app-providers.tsx, (app)/layout.tsx, (auth)/layout.tsx |
| 2 | landing-surface.test.mjs — infra, G-land-1, G-land-3 | `0c9c61a` | scripts/landing-surface.test.mjs |
| 3 | G-land-4, G-land-5, reyestr nazorati, sabotajlar | `63b8088` | scripts/landing-surface.test.mjs |

## Nima qurildi

- **`page.tsx`** — skelet o'zgarmagan (hasLocale -> notFound -> setRequestLocale BIRINCHI -> getTranslations); `cookies()`/`headers()`/`searchParams` 0. Bloklar §9.1 tartibida: Header · Section(Hero) · surface-muted(PainCards) · Section(StepLine) · Section(Proof) · surface-muted(RoleCards) · Section(TrustBlock — id'siz, anchor blokda) · surface-muted(Pilot) · Section(Faq) · Section id="demo" (Reveal > Card > h2 form.title + subtitle + DemoForm) · Footer. `<main id="kontent">`; sahifada bitta h1 (hero); `py-16`/`py-24`/`text-hero`/taqiq tipografiya bu faylda 0.
- **`generateMetadata`** — `metadataBase` (NEXT_PUBLIC_SITE_URL ?? sbozor.uz), title/description `landing.meta.*` dan (brend VA va'da), canonical joriy locale prefiksi, `alternates.languages` uchala locale (prefikslar routing.ts'dan HOSILA — maxfiylik sahifasi funksiyasi ayni), openGraph (url, siteName=common.appName, locale ll_CC, statik 1200x630 PNG + locale bo'yicha `ogAlt`), twitter `summary_large_image`.
- **JSON-LD** — ikki tur, Server Component ichida: `Organization` (nom, logotip, contactPoint faqat env telefon berilganda) va `FAQPage` (5 savol `t(\`faq.q${n}\`)` dan — komponent bilan BITTA manba). Har skript `JSON.stringify(data).replace(/</g, "\\u003c")` — Next rasmiy naqshi (T-10-08); `Product`/`AggregateRating`/`Review` 0 (T-10-13).
- **`landing-surface.test.mjs` (1645 qator, 25 test)** — `stripComments`/`extractKeyframes`/`listProductFiles` motion-tokens'dan AYNAN NUSXA; YANGI `extractClassBlocks` (sinf selektori + qavs-balans) va `transitionProps` (shorthand birinchi token + `transition-property`, `-duration/-delay` chetlab); `renderableTextParts` (JSX matn + braced literal); `providerNamespaces` (spread = qizil holat); barcha sanoqlar izohlar olib tashlangandan KEYIN; har assert xabari band nomi + aniq fayl bilan; qamrov HOSILA (readdirSync + quyi chegaralar), to'plamlar deepEqual.

## Darvoza bandlari (20 = 4+4+7+5; reja sarlavhasidagi «17» — arifmetik xato, qamrov KAMAYTIRILMADI)

- **G-land-1:** (a) klient orollari to'plami 5 nomga deepEqual (direktiva-pozitsiya); (b) hero.tsx direktiva-substring 0 VA `hero.headline` chaqirig'i bor; (c) IKKI TOMONLAMA — provayder kalitlari aynan {common, landing} VA barcha useTranslations/getTranslations/namespace argumentlari shu to'plamning qismi (≥10 chaqiruv guard, T-10-15); (d) `[locale]/page.tsx` yo'q + `(marketing)/page.tsx` bor (L-7).
- **G-land-3:** (a) har `.landing-*`/`.motion-*` blokining transition xossalari {transform, opacity, background, background-color, border-color, box-shadow, color} ga QISM; width/height/top/left/right/bottom/margin*/padding*/all nomma-nom 0 (L-8 bo'shlig'i yopiq); (b) inline style geometriyasi 0 (style-blok parse + `.style.prop` kanali); (c) setInterval 0, setTimeout fayl-to'plami == {hero-scene.tsx}; (d) @keyframes 9 nom deepEqual, meros 8 o'zgarmagan, yangisi aynan `sweep`.
- **G-land-4:** (a) sampleBadge chaqirig'i bor + shartsiz `{t(...)}` + shartli naqsh 0; (b) a11yDescription'da namuna o'zagi 3 locale; (c) residency.body 3 locale + hero `#ishonch` anchor + trust-block id; (d) FAQPage kalitlardan + 30 katalog matni birorta faylda literal emas; (e) 9 taqiq tokeni katalogda 0 VA render-matnida 0 (ikki kanal); (f) pilot.* da `\d` 0 katalogda VA pilot.tsx render-matnida; (g) `landing.*` dagi `ts[iy]` tokenlari kirill overrides lug'atida (bugun 0 token — qulf kelajakka).
- **G-land-5:** (a) text-hero fayl-reyestr deepEqual {hero.tsx} VA uchrashuv sanog'i AYNAN 1 (ikki qatlam); (b) `--text-hero` @theme'da `clamp(` bilan; (c) py-16/py-24 fayl-to'plami == {section.tsx}; (d) text-base/text-3xl/`text-[`/font-medium marketing yuzasida 0; (e) text-display components/marketing'da 0.
- **REYESTR NAZORATI:** o'z manbasida child_process require/import 0, execSync 0 (regekslar o'z-o'ziga mos kelmaydi); taqiq tokenlar ≥8, keyframes = 9, klient orollari = 5; reyestrlarda takror 0.

## Sabotaj o'lchovlari (§16.3 — har biri alohida, modul import qilinadigan holda, har biri qaytarildi)

| # | Sabotaj | Kutilgan band | Natija |
|---|---------|---------------|--------|
| 1 | hero.tsx boshiga klient direktivasi | G-land-1(b) | **exit 1**, xatoda «G-land-1(b) BUZILDI — ... 1 marta topildi»; (a) ham qizardi (to'g'ri: fayl reyestrsiz to'plamga kirdi); 23 test yashil |
| 2 | components/marketing'da oltinchi `"use client"` fayl | G-land-1(a) | **exit 1**, xatoda `sabotage-probe.tsx` nomi; 24 yashil |
| 3 | `.landing-step-fill` -> `transition: height 900ms` | G-land-3(a) | **exit 1**, xatoda `.landing-step-fill -> transition \`height\`` — bu AYNAN L-8 ning 10-06 gacha jim o'tadigan holati; 24 yashil |
| 4 | role-cards.tsx'ga `setInterval` (modul darajasida) | G-land-3(c) | **exit 1**, xatoda `role-cards.tsx`; 24 yashil — 10-06 sabotaj-1 da HECH NIMA qizarmagan teshik yopildi |
| 5 | `landing.pilot.body` += «Pilotda 30% o'sish» (katalog) | G-land-4(e) VA (f) | **exit 1**, IKKALA band qizardi; 23 yashil |
| 6a | `text-hero` ikkinchi faylga (role-cards.tsx) | G-land-5(a) fayl-qatlam | **exit 1**, xatoda «fayl-reyestrdan chetlandi»; 24 yashil |
| 6b | `text-hero` hero.tsx ICHIDA ikkinchi marta | G-land-5(a) sanoq-qatlam | **exit 1**, xatoda «2 marta (kutilgan: AYNAN 1)» — faqat fayl qulfi buni o'tkazib yuborardi; 24 yashil |
| A | sampleBadge shartli renderga olindi (`phase === 5 &&`) | G-land-4(a) | **exit 1**, band nomi xatoda; 24 yashil |
| B | pilot.tsx JSX'iga `{"30% o'sish"}` literal (katalog TOZA) | G-land-4(e)+(f) komponent kanali | **exit 1**, xatoda `pilot.tsx (satr-literal)` — 10-06 SUMMARY o'lchagan bo'shliq komponent-MATN kanali bilan yopildi; 23 yashil |

Har o'lchovdan keyin `git checkout -- <fayl>` (2/probe uchun `rm`), qaytarish 25/25 yashil bilan tasdiqlandi.

## ENVIRONMENT_FALLBACK tashxisi va tuzatishi (orkestrator bandi)

- **Reproduktsiya (bazada o'lchandi):** `next build` stderr'ida `Error: ENVIRONMENT_FALLBACK` **4 marta** (exit 0, 86/86 marshrut), stek `app-guard.tsx` SSR chunk'iga ishora.
- **Sabab (manba darajasida topildi):** `use-intl` `useTranslations` ichida — kontekstda `timeZone` bo'lmasa serverda (`typeof window === "undefined"`) har modul-instansiyada bir marta `IntlError(ENVIRONMENT_FALLBACK)` ogohlantirishi loglanadi. `i18n/request.ts` da `Asia/Tashkent` BOR, lekin `AppProviders` KLIENT moduli — next-intl'ning avtomatik konfiguratsiya merosi faqat Server Component kontekstida ishlaydi, klient zanjirida `NextIntlClientProvider` faqat oshkora proplarni oladi (locale+messages uzatilardi, timeZone yo'q). Prerender 7 worker'da — 4 worker app-sahifa render qilib bittadan loglagan. `(marketing)` provayderi server kontekstda — u meros oladi, shuning uchun faqat app-guard chunk'i ko'ringan.
- **Xavf bahosi:** faqat log shovqini emas — timeZone'siz klient-daraxtdagi sana/vaqt formatlash serverda build-mashina mintaqasida, brauzerda foydalanuvchi mintaqasida ketadi (gidratatsiya nomuvofiqlik sinfi + biznes-kun chegarasi, CLAUDE.md «naive datetimes» taqiqi bilan bir oila).
- **Tuzatish (arzon, 3 fayl, commit `3982344`):** `AppProviders` ga majburiy `timeZone` prop; `(app)`/`(auth)` layoutlari `getTimeZone()` bilan request-config'dan o'qib uzatadi — qiymat manbai BITTA joyda qoladi (request.ts, FOUND-05).
- **O'lchov:** to'liq build tuzatishdan keyin — **0x** ENVIRONMENT_FALLBACK, exit 0, 86/86 marshrut; `(app)/layout.test.tsx` 5/5; typecheck/lint exit 0.

## Reja bo'yicha o'lchovlar (verification)

| O'lchov | Natija |
|---------|--------|
| `node --test scripts/landing-surface.test.mjs` | **25/25 yashil**; ijro vaqti uch o'lchov: **0,51 / 0,59 / 0,74 s** (kutilgan +0,5…1,0 s byudjet ichida) |
| `npm run test:unit` (23 skript darvoza fayli) | **375/375 yashil** (350 meros + 25 yangi), 1,7 s |
| `vitest run src/components/marketing` | **4 fayl / 27 test yashil** |
| `(app)/layout.test.tsx` (timeZone tuzatishidan keyin) | **5/5 yashil** |
| `next build` | **exit 0**, prerender **86/86** marshrut, ENVIRONMENT_FALLBACK **0** (avval 4) |
| `npm run i18n:check` | **exit 0** — 1494 kalit x 3 til parity |
| `typecheck` / `lint` (page.tsx, darvoza fayli, 3 tuzatilgan fayl) | exit 0 / exit 0 |
| Task 1 verify skripti (11 blok + escape + taqiq JSON-LD) | OK |

**Halol qayd:** to'liq vitest to'plami (101 fayl) yakuniy nuqtada qayta yugurtirilmadi — fon konteyneri o'ldi (orkestrator spot-check tasdig'i). O'lchangan qatlamlar: barcha 23 skript-darvoza (375/375), shu reja yuzasiga tegadigan 5 vitest fayli (marketing 4 + layout 1), to'liq `next build` + typecheck. Qolgan vitest fayllari bu rejaning fayllariga import zanjiri orqali bog'lanmagan (timeZone prop'ining yagona iste'molchilari — ikki layout, ikkalasi o'lchandi); to'liq to'plam 10-08 faza darvozasida baribir majburiy yuguradi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Orkestrator bandi / Rule 1] ENVIRONMENT_FALLBACK — timeZone klient provayderiga uzatildi**
- **Found during:** bazaviy build reproduktsiyasi (reja tashqarisidagi majburiy tashxis bandi)
- **Issue/Fix/O'lchov:** yuqoridagi alohida bo'limda
- **Files modified:** app-providers.tsx, (app)/layout.tsx, (auth)/layout.tsx (reja `files_modified` dan tashqari — orkestrator bandi ruxsati bilan)
- **Commit:** `3982344`

**2. [Rule 2 - 10-06 SUMMARY nuansi] G-land-4(e)/(f) komponent-MATN kanali**
- **Found during:** Task 3 loyihalash (10-06 sabotaj-2 darsi: pilot.tsx JSX literali hech narsani qizartirmagan)
- **Fix:** `renderableTextParts` ekstraktori (JSX matn tugunlari + braced satr literallari; className teg ichida — kanalga tushmaydi, joriy 18 faylda soxta ijobiy 0 — empirik o'lchandi); (e) barcha marketing fayllarga, (f) pilot.tsx'ga qo'llanadi
- **Isbot:** nazorat B — katalog toza turib komponent literali ikkala bandni qizartirdi
- **Commit:** `63b8088`

**3. [Hujjat aniqligi] «17 band» arifmetikasi**
- Reja objective/success_criteria «17 band» deydi, lekin Task 2/3 da sanab chiqilgan bandlar 4+4+7+5 = **20**. Hammasi bajarildi — son kamaytirilmadi; farq rejalovchi arifmetikasi sifatida qayd etildi.

Boshqa jihatlarda reja aynan yozilganidek bajarildi.

## Known Stubs

Yo'q — 11 blokning barchasi haqiqiy katalog matni bilan ulangan; DemoForm `#demo` seksiyasiga mount qilindi (10-04 stub'i yopildi), OG rasm `generateMetadata`ga ulandi (10-04 ikkinchi stub'i yopildi).

## Threat Flags

Yangi qamrovlanmagan yuza yo'q. Reja threat-registri qo'llandi va sabotaj bilan isbotlandi: **T-10-08** (JSON-LD escape — verify skripti + naqsh manbada), **T-10-13** (Product/AggregateRating/Review 0 — verify regeks), **T-10-10** (sampleBadge shartsiz — nazorat A qizardi), **T-10-15** (ikki tomonlama namespace quli — G-land-1(c)), **T-10-21** (transition skani — sabotaj 3 qizardi).

## Keyingi bosqichga eslatmalar

- 10-08 gate byudjeti: yangi fayl eng yomon o'lchovda **0,74 s** qo'shadi (W0-13 formulasi bilan 0,74x1,2 ≈ 0,9 s) — 41 s zaxira yetadi, lekin to'liq `gate` o'lchovi 10-08 da majburiy.
- HUMAN-UAT (10-08): LCP soni, Lighthouse ≥95, payload farqi (demo-forma orollari endi klient grafida — `next build` route jadvali OLDIN/KEYIN son bilan).
- `sitemap.ts`/`robots.ts` allaqachon 10-04 dan mavjud; bu reja ularga tegmadi.

## Self-Check: PASSED

- [x] `frontend/src/app/[locale]/(marketing)/page.tsx` — 11 blok, JSON-LD escape naqshi, verify skripti OK
- [x] `frontend/scripts/landing-surface.test.mjs` — mavjud, 25/25 yashil, child_process importi 0
- [x] Commitlar tarixda: `fc1fa5b`, `0c9c61a`, `3982344`, `63b8088`
- [x] Ish daraxti toza (barcha sabotajlar qaytarilgan — yakuniy 25/25 bilan tasdiqlandi)
- [x] STATE.md / ROADMAP.md / REQUIREMENTS.md TEGILMADI
