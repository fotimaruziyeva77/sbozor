---
phase: 10
slug: landing-sbozor-uz
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
updated: 2026-08-18
human_only_verifications:
  - item: Lighthouse Performance >= 95 va LCP < 1.5 s (arzon Android profili, ROADMAP SC#5)
    why_not_automatable: Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI (10-UI-SPEC §16.5, [QAROR]) — headless Chrome + yangi ishlab chiqish bog'liqligi `gate` byudjetiga daqiqalar qo'shardi, byudjet esa o'lchangan holda 73 s zaxirada. Mexanik proksi TOR va u ATAYIN tor: G-land-1 LCP yo'lida `"use client"` yo'qligini qulflaydi, G-land-3 esa layout-thrash sababini yo'q qiladi. Sabab yo'qligi natija borligini isbotlamaydi — tadqiqotda o'lchangan uchinchi omil buni ko'rsatadi: `.motion-enter` `opacity:0` dan boshlanadi va Chrome LCP `opacity:0` elementni chizilgan deb hisoblamaydi, ya'ni `h1` ga `--i` kechikishi berilsa LCP mexanik darvoza KO'RMAYDIGAN yo'l bilan suriladi. Bu — o'lchov, kod emas
    owner: Ijrochi (arzon Android qurilmasi bilan)
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 10-HUMAN-UAT.md #1; natija SON bilan yoziladi, «tez ko'rinadi» bilan EMAS
  - item: "Payload farqi: `next build` route jadvali provayder ko'chirishidan OLDIN va KEYIN, farq gzip KB da"
    why_not_automatable: Bu o'lchov `next build` chiqishini talab qiladi va u `gate` ning oxirgi qadami — test qatlamida route-payload jadvali PRINSIPIAL ravishda ko'rinmaydi. Tadqiqotda bugungi chunk sonlari o'lchandi (zod+api-client 280 KB xom / 69 KB gz, rq+nuqs+sonner 71 KB / 21 KB gz, next-intl 39 KB / 12 KB gz, matn katalogi 21,7–26,9 KB gz), LEKIN refaktordan keyin Turbopack chunk chegaralarini QAYTA hisoblaydi va o'sha guruhlash saqlanishi kafolatlanmagan. Shuning uchun «~110 KB tejaladi» da'vosi BERILMADI va u o'lchovsiz BERILMADI (10-UI-SPEC §4.3 halollik bandi). ⛔ HOLAT — O'LCHANDI va YOPIQ: 10-03 (2026-08-17) refaktordan keyingi haqiqiy jadvalni oldi — ildiz 287,8 → 208,4 KB gz (−79,4); 10-HUMAN-UAT.md #2 SON bilan imzolangan
    owner: Ijrochi
    trigger: Provayder ko'chirishi to'lqini yakuni — 10-HUMAN-UAT.md #2; jadval ikki nusxada saqlandi va farq SON bilan yozildi (YOPIQ)
  - item: 60fps arzon Android qurilmada — hero 12s sikli va scroll-reveal jank bermaydi
    why_not_automatable: jsdom layout ham, kompozitsiya ham QILMAYDI — `getBoundingClientRect()` nol qaytaradi, `Element.animate` va `document.getAnimations()` UMUMAN yo'q (09-RESEARCH Tuzoq 1, o'lchangan jsdom 30.0.1 + vitest 4.1.10). Ya'ni «kadr tushdimi?» savoliga test qatlamida javob beradigan sirt YO'Q. G-land-3 `transition` va `@keyframes` xossalarini `transform`/`opacity` bilan qulflaydi, ya'ni layout-thrash SABABINI yo'q qiladi — lekin sabab yo'qligi natija borligini isbotlamaydi: 30 katak + sweep + count-up bir vaqtda ishlaganda arzon GPU baribir to'lishi mumkin. Ikkinchi o'lchanmagan omil — `container-type: inline-size` va `100cqw` ning maqsad qurilmalarda haqiqiy xulqi [A2]
    owner: Ijrochi (dala qurilmasi bilan)
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 10-HUMAN-UAT.md #3; natija KADR/SONIYA raqami bilan yoziladi
  - item: "Demo so'rovining uchidan-uchiga yetkazilishi: haqiqiy formadan haqiqiy admin Telegram chatiga"
    why_not_automatable: Integratsiya testi Telegram Bot API'ni `respx` bilan TUTADI va u to'g'ri qaror — haqiqiy tokenni CI'ga bermaslik `alerts.py` ning 2-taqig'ining bevosita talabi. Ya'ni test «biz to'g'ri so'rov yubordik» ni o'lchaydi, «xabar chatga tushdi» ni EMAS. O'lchanmagani: token/chat_id konfiguratsiyasining to'g'riligi, chatning bot tomonidan yozish huquqi, xabar formatining o'qilishi (uch tilda kelgan bozor nomi va ism), va admin uni haqiqatan sotuv signali sifatida ko'rishi. `alerts_enabled` False bo'lgan o'rnatmada tizim `delivery_failed` beradi va bu HALOL — lekin uni faqat inson farqlaydi. ⛔ PII intizomi (T-10-25, accept): sinov so'rovlari FAQAT SOXTA ism/telefon bilan
    owner: Mahsulot egasi (admin akkaunti bilan)
    trigger: Birinchi deploy — 10-HUMAN-UAT.md #4; natija «N ta sinov so'rovidan M tasi chatga tushdi» shaklida
  - item: Kirill va rus landing matnining davlat auditoriyasi tomonidan o'qilishi — hokimlik proyektorida va telefonda
    why_not_automatable: Transliteratsiya darvozasi lotin harfi qolmaganini o'lchaydi va glossariy taqiqlangan sinonimlarni ushlaydi — ikkalasi ham LUG'AT darajasi. O'lchanMAGANI ma'noning o'zi: tadqiqotda AYNAN shu bo'shliqdan ikki defekt chiqdi (`AI` -> `АИ` va `demonstratsiya` -> `демонстратсия`), ikkalasi ham sof kirill chiqish bergani uchun birorta darvoza ularni ko'rmasdi. Qolgan ~119 kalitda shunga o'xshash semantik siljish bo'lishi mumkin va uni faqat ona tilida o'qiydigan odam ko'radi. Rus matni esa transliteratsiya hosilasi EMAS — u mustaqil yozilgan va uning uslubi hech qanday mexanik o'lchov ostida turmaydi
    owner: Mahsulot egasi (kirill o'qiydigan davlat vakili bilan)
    trigger: Pilot tayyorgarligi haftasi — 10-HUMAN-UAT.md #5; natija «N ta tuzatish kiritildi» ro'yxati bilan
  - item: "`landing.trustBlock.residency.body` ning mahalliy yurist tasdig'i — ommaviy huquqiy da'vo"
    why_not_automatable: Rezidentlik bandi («ma'lumotlar O'zbekistonda…») O'zR shaxsiy ma'lumotlar qonuni ostidagi ommaviy majburiyat matni. Mexanik qatlam faqat kalitning uchala tilda MAVJUDLIGINI o'lchaydi (G-land-4(c)); matnning yuridik to'g'riligini, Telegram chegarasi (`alerts.py` 1-taqiq konteksti — xabar matni O'zR tashqarisidagi serverlar orqali o'tadi) bilan zid emasligini va maxfiylik sahifasi bilan izchilligini faqat mahalliy yurist tasdiqlaydi. STATE.md «Huquqiy ko'rik» blokeri (kvitansiya maydonlari, CCTV shaxsiy ma'lumot) bilan BIR tugunda
    owner: Mahsulot egasi (mahalliy yurist bilan)
    trigger: Go-live — 10-HUMAN-UAT.md #6; natija «N ta tahrir talab qilindi» ro'yxati bilan
automated_replacements:
  - was: Brauzerda `/uz` ni ochib «landing chiqyaptimi, login havolasi joyidami?» deb ko'z bilan qarash
    now: "node --test frontend/scripts/landing-surface.test.mjs — G-land-1(a–d): klient orollari reyestrga deepEqual (5 fayl), hero LCP faylida 'use client' 0 (substring-0), marketing provayder nomlari ['common','landing'] IKKI tomonlama, [locale]/page.tsx yo'qligi; phase10-criteria SC#1 esa prerender-manifest'da /uz-Latn·/uz-Cyrl·/ru uchalasini va header'dagi /login ni tasdiqlaydi"
  - was: Hero siklini 12 soniya kuzatib, OS'da reduced-motion yoqib qayta qarash
    now: "npx vitest run src/components/marketing/hero-scene.test.tsx — reduced-motion mock'ida setTimeout 0 marta VA DOM to'liq final-kadr; 0 ms da final-kadr (rewind yo'q), 13 500 ms da 1-fazaga qaytish; unmount'da clearTimeout soni = yaratilgan taymerlar; IntersectionObserver isIntersecting:false → yangi taymer 0"
  - was: Formani qo'lda to'ldirib 429/422/honeypot holatlarini ko'z bilan tekshirish
    now: "docker compose --profile test run --rm tests pytest tests/integration/test_demo_request.py -q — 7 band: anonim muvaffaqiyat + Set-Cookie yo'q + tenant izi yo'q; 429 rate_limited; 422 invalid_phone (normalize_phone — server yagona haqiqat); honeypot jim muvaffaqiyat + Telegram'ga 0 chaqiruv; delivery_failed + DB'da 0 yangi qator"
  - was: Demo xato matnlarini uch tilda qo'lda solishtirish
    now: "node --test frontend/scripts/error-codes.test.mjs — oltinchi juftlik: schemas.py::DEMO_ERROR_CODES (backend LANGAR, aynan 4 kod) → lib/demo-errors.ts ko'zgusi IKKI yo'nalishda → demoErrorMessageKey har kodni xaritalaydi → landing.form.* kaliti uchala tilda"
  - was: ROADMAP mezonlarini qo'lda o'qib «bajarildimi?» deb baholash
    now: "node --test frontend/scripts/phase10-criteria.test.mjs — beshala SC har biri MAHSULOT + ZANJIR dalili bilan; META: ROADMAP'dan AYNAN 5 mezon parse + 5 langar regex; SOXTALASHTIRISH: har SC bloki src/services/tests/package.json ga murojaat qiladi; REYESTR NAZORATI: spawn 0"
  - was: Pilot va ishonch matnlarida yolg'on raqam yo'qligini ko'z bilan qidirish
    now: "node --test frontend/scripts/landing-surface.test.mjs — G-land-4: taqiqlangan da'vo tokenlari landing.* da 0 (uchala locale), landing.pilot.* da raqam 0, sampleBadge shartli render TASHQARISIDA, residency.body uchala tilda; phase10-criteria SC#4 raqam-skanning MUSTAQIL ikkinchi qatlami"
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Manba:** `10-RESEARCH.md` («Validatsiya arxitekturasi» bo'limi) va
> `10-UI-SPEC.md` §16 — bu fayl ulardan **HOSILA**, qayta yozilmaydi.
> Ziddiyat bo'lsa — 10-UI-SPEC.md §16 ustun (u `approved`).

---

## Bu fazaning validatsiyasi nimasi bilan boshqacha — buni birinchi o'qing

9-fazadan farqli o'laroq bu faza `frontend/` dan TASHQARIGA chiqadi:
kodbazadagi **YAGONA autentifikatsiyasiz yozuv marshruti** ochiladi
(`POST /api/v1/public/demo-requests`). Shuning uchun:

1. ⛔ **pytest qatlami QAYTADI** (9-fazada yo'q edi): anonim endpoint
   `tests/integration/test_demo_request.py` bilan, `EXEMPT_ROUTES`
   qamrovi esa mavjud `tests/tenancy/test_route_coverage.py` bilan
   o'lchanadi. Mezon moduli buning uchun YANGI zanjir turini oldi —
   `assertChainPytest` (fayl `tests/integration/` ostida ekanini
   tasdiqlaydi, aks holda `gate` uni yugurtirmasdi).

2. ⛔ **Anonim yuzaning payload chegarasi o'lchov predmeti**: provayder
   ko'chirishi (10-03) `next build` jadvali bilan OLDIN/KEYIN o'lchandi
   (287,8 → 208,4 KB gz) — «tejaladi» da'vosi o'lchovdan keyin berildi,
   oldin emas.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (birlamchi)** | vitest 4.1.10 + jsdom 30.0.1 + `@testing-library/react` 16.3.2 — `src/**/*.test.tsx` |
| **Framework (ikkilamchi)** | `node --test` (Node o'rnatilgan, ⛔ **nol bog'liqlik**) — `frontend/scripts/*.test.mjs` |
| **Framework (uchlamchi)** | pytest 9.1.1 — ⛔ **BU FAZADA ISHLATILDI** (9-fazadan farq): anonim endpoint `tests/integration/test_demo_request.py` + `EXEMPT_ROUTES` qamrovi |
| **Config — komponent** | `frontend/vitest.config.ts` (`environment: "jsdom"`, `include: ["src/**/*.test.tsx"]`) |
| **Config — global setup** | `frontend/vitest.setup.ts` — ⛔ `matchMedia` va `IntersectionObserver` stublari bu yerga QO'YILMAGAN; teskari shox o'lchovsiz qolmasin deb stub HAR testda alohida |
| **Quick run command** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite command** | `npm run gate` (sim:up → backend → cv → bot → i18n:check → frontend test/typecheck/lint/build) |
| **Measured runtime** | ⛔ **10-08 da QAYTA O'LCHANDI (2026-08-17/18, tinch xost, UCH yaroqli o'lchov, uchalasi exit 0):** `gate` **2227 / 1856 / 1760 s** · byudjet **2300 s** (O'ZGARMADI) · zaxira **73 s (3,3 %)** · `gate:fast` **249 / 175 / 175 s** · byudjet **200 → 300 s** (KO'TARILDI: eng yomon 249 × 1,20 = 298,8 → 50 ga yaxlitlab 300; reja mo'ljallagan 250 o'lchov bilan bekor bo'ldi — 249 unga 0,4 % zaxira qoldirardi). Yana UCH YAROQSIZ urinish jurnalda (`package.json //gate-budget`): 2 ta fon-seans uzilishi + 1 ta meros flake №12 (1845 s exit 1) |
| **O'lchangan o'sish** | Oldingi (09-07): `gate` 2259/2102 · `gate:fast` 189/171. To'plam o'sdi: backend pytest 3101 → 3191 (+90), vitest 1170 → 1197 (+27), skript darvozalari 349 → 386 (+37), SSG 83 → 86 marshrut |

⛔ **Zanjir boshida majburiy nazorat:** `frontend/node_modules` mavjudligi
tekshirildi (bo'sh emas — `npm ci` KERAK BO'LMADI) [MEROS: 8-fazada
bo'shligi 29-daqiqada ko'ringan].

---

## Sampling Rate

- **After every task commit:** `npm run gate:fast` (byudjet **300 s** — 10-08 da qayta o'lchangan)
- **Tez mahalliy halqa (task ichida):** `node --test frontend/scripts/landing-surface.test.mjs` (<1 s) + `npx vitest run src/components/marketing/` — to'liq vitest KUTILMAYDI
- **i18n tahriridan keyin:** `npm --prefix frontend run i18n:gen && npm --prefix frontend run i18n:check` — MAJBURIY, drift'da exit 1
- **Backend tahriridan keyin:** `docker compose --profile test run --rm tests pytest tests/tenancy tests/integration/test_demo_request.py -q`
- **After every plan wave:** `npm run gate:fast` + `npm --prefix frontend run build` — build provayder ko'chirishidan keyin MAJBURIY
- **Before `/gsd-verify-work`:** `npm run gate` to'liq yashil bo'lishi SHART (10-08 da UCH marta exit 0)
- **Max feedback latency:** 300 s (`gate:fast`)

---

## Per-Task Verification Map

> ⚠ **GRANULYARLIK — REJA DARAJASIDA** (07/08/09-VALIDATION qoidasi): har
> taskning o'z `<automated>` bandi mos PLAN.md da yozilgan; bu jadval har
> rejaning **darvoza buyrug'ini** beradi.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P-01 | 10-01 | 1 | LAND-03 | T-10-01 / T-10-11 | Anonim POST muvaffaqiyat + `Set-Cookie` YO'Q + tenant izi YO'Q; 429 `rate_limited`; 422 `invalid_phone`; honeypot jim + Telegram 0; `delivery_failed` + DB 0 qator; `EXEMPT_ROUTES` qamrovi tiklangan | pytest | `docker compose --profile test run --rm tests pytest tests/integration/test_demo_request.py -q` | ✅ 10-01 da tug'ilgan | ✅ green |
| P-02 | 10-02 | 1 | LAND-04, LAND-05 | — | `--text-hero`/`sweep`/`.landing-step-fill` tokenlari `@theme` qatlamida; `landing.*` ~119 kalit 3 tilda; kontrast reyestri AA saqlanadi | node:test | `node --test frontend/scripts/contrast.test.mjs && npm --prefix frontend run i18n:check` | ✅ mavjud infra + 10-02 | ✅ green |
| P-03 | 10-03 | 2 | LAND-01 | — | Anonim `MarketingLocaleSwitcher` (api-client'siz, B-1/B-2); `AppProviders`/`AppGuard` ajratildi; `[locale]/page.tsx` O'CHIRILDI; `(marketing)` qobig'i ikki fazoviy nom bilan; payload OLDIN/KEYIN o'lchandi | vitest + build | `npx vitest run src/components/marketing/locale-switcher.test.tsx && npm --prefix frontend run build` | ✅ 10-03 da tug'ilgan | ✅ green |
| P-04 | 10-04 | 3 | LAND-03, LAND-05 | T-10-11 | Demo-forma og'ir grafsiz (literal marshrut); `demo-errors.ts` ko'zgusi; maxfiylik sahifasi; `sitemap.ts`/`robots.ts`; muvaffaqiyat `role="status"`, xato `role="alert"` | vitest | `npx vitest run src/components/marketing/demo-form.test.tsx` | ✅ 10-04 da tug'ilgan | ✅ green |
| P-05 | 10-05 | 3 | LAND-02 | — | Hero server yakuniy kadr (LCP) + 12s klient sikli: reduced-motion'da `setTimeout` 0 va final-kadr; 13 500 ms qaytish; unmount tozalash; IO tejash | vitest | `npx vitest run src/components/marketing/hero-scene.test.tsx` | ✅ 10-05 da tug'ilgan | ✅ green |
| P-06 | 10-06 | 3 | LAND-04 | — | `Reveal` primitivi (IO stub bilan); og'riq/dalil/rol kartalari; ishonch bloki; pilot (raqam 0); FAQ; 3-qadam chizig'i | vitest | `npx vitest run src/components/marketing/reveal.test.tsx` | ✅ 10-06 da tug'ilgan | ✅ green |
| P-07 | 10-07 | 4 | LAND-01, LAND-02, LAND-04, LAND-05 | T-10-08 | Sahifa 11-blok kompozitsiyasi + metadata OG/hreflang/canonical + JSON-LD (rasmiy escape); G-land-1/3/4/5 (20 band) bitta parse faylida; ENVIRONMENT_FALLBACK 4x → 0 | node:test | `node --test frontend/scripts/landing-surface.test.mjs` | ✅ 10-07 da tug'ilgan | ✅ green |
| P-08 | 10-08 | 5 | LAND-01…LAND-05 | T-10-22 / T-10-23 / T-10-24 / T-10-25 | Beshala ROADMAP mezoni BITTA buyruqda (mahsulot + zanjir dalili); `DEMO_ERROR_CODES` ikki yo'nalishli ko'zgu; byudjetlar W0-13 bilan qayta o'lchandi; `nyquist_compliant` shu rejada `true` | node:test | `node --test frontend/scripts/phase10-criteria.test.mjs frontend/scripts/error-codes.test.mjs` | ✅ 10-08 da tug'ilgan | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 fayllari to'lqinlar ichida tug'ildi (08/09-faza naqshi) — har biri
o'z rejasida, darvozalar komponentlardan OLDIN yoki ular bilan birga:

- [x] ⛔ `gate:fast`/`gate` byudjetlarining W0-13 qayta o'lchovi — **10-08** (gate:fast 200 → 300; gate 2300 QOLADI — uch yaroqli o'lchov, jurnal `package.json` da)
- [x] ⛔ B-1: `components/marketing/locale-switcher.tsx` (anonim, api-client'siz) provayder ko'chirishidan OLDIN — **10-03**
- [x] ⛔ B-3: `demonstratsiya` → `namoyish` copy tuzatishi; `AI` override juftligi — **10-02**
- [x] `frontend/scripts/landing-surface.test.mjs` — G-land-1, 3, 4, 5 (bitta fayl, sof matn/CSS parse) — **10-07**
- [x] `frontend/src/components/marketing/hero-scene.test.tsx` — G-land-2 (a…e) — **10-05**
- [x] `frontend/src/components/marketing/demo-form.test.tsx` — forma holatlari + a11y — **10-04**
- [x] `frontend/src/components/marketing/locale-switcher.test.tsx` — anonim til almashtirgich — **10-03**
- [x] `frontend/src/components/marketing/reveal.test.tsx` — scroll-reveal IO xulqi — **10-06**
- [x] `tests/integration/test_demo_request.py` — `EXEMPT_ROUTES` qamrovini tiklaydi (7 band) — **10-01**
- [x] `frontend/scripts/phase10-criteria.test.mjs` — beshala SC bitta buyruqda — **10-08**
- [x] `10-HUMAN-UAT.md` — olti band, SON bilan yopilish sharti — **10-08**
- [x] ⛔ `AppProviders` + `AppGuard` ajratish (Tuzoq 3) — **10-03**

⛔ Freymvork o'rnatish **kerak bo'lmadi** — vitest, jsdom, Testing
Library, `node --test`, pytest hammasi mavjud edi.

`nyquist_compliant` → `true` sharti: Wave 0 fayllari tug'ilib yashil VA
qo'lda bandlar `10-HUMAN-UAT.md` ga ega+tetik+SON bilan ko'chirilgan —
bu **10-08** ning ishi va bajarildi. `wave_0_complete` ham shu yerda
`true` bo'ldi.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Lighthouse ≥95 va LCP <1,5 s (uchala locale) | LAND-05 | Lighthouse CI'da yo'q va qo'shilmagan (§16.5); mexanik proksi (G-land-1(b), G-land-3) sababni yopadi, natijani emas | `10-HUMAN-UAT.md` #1 — 6 SON bilan (3 locale × perf/LCP) |
| Payload farqi OLDIN/KEYIN | LAND-05 | `next build` jadvali test qatlamida ko'rinmaydi | `10-HUMAN-UAT.md` #2 — ⛔ **O'LCHANDI va YOPIQ** (10-03: −79,4 KB gz ildiz) |
| 60fps arzon Androidda (hero 12s + reveal) | LAND-02 | jsdom layout/kompozitsiya qilmaydi; `100cqw` xulqi [A2] | `10-HUMAN-UAT.md` #3 — KADR/SONIYA bilan |
| Demo so'rovi haqiqiy admin chatiga tushishi | LAND-03 | `respx` tarmoq chegarasini tutadi — token/chat konfiguratsiyasi va o'qilish tashqarida | `10-HUMAN-UAT.md` #4 — «N dan M tasi tushdi», SOXTA PII bilan |
| Kirill/rus matnining davlat auditoriyasida o'qilishi | LAND-04, FOUND-04 | Semantik siljish (`АИ`/`демонстратсия` sinfi) lug'at darvozalaridan qochadi | `10-HUMAN-UAT.md` #5 — «N ta tuzatish» ro'yxati |
| `residency.body` yurist tasdig'i | LAND-04 | Ommaviy huquqiy da'vo — yuridik to'g'rilikni faqat mahalliy yurist o'lchaydi | `10-HUMAN-UAT.md` #6 — «N ta tahrir», go-live tetigi |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 300s (`gate:fast`, 10-08 da qayta o'lchangan byudjet)
- [x] `nyquist_compliant: true` set in frontmatter — 10-08 da qo'yildi: Wave 0 fayllari tug'ilgan va yashil (uch to'liq `gate` exit 0), oltala qo'lda band `10-HUMAN-UAT.md` ga ega+tetik+SON sharti bilan ko'chirilgan

**Approval:** 2026-08-18 — 10-08 faza darvozasida imzolandi. ⚠ HALOLLIK:
`human_only_verifications` oltala bandidan bittasi (№2 payload) 10-03
o'lchovi bilan SON asosida YOPIQ; qolgan beshtasi OCHIQ (birortasiga
raqam yozilmagan — o'lchovlar real qurilma, real deploy yoki inson
idrokini talab qiladi). Ochiqlik `nyquist_compliant` ga ZID EMAS —
bayroq «har o'lchanadigan xulq avtomat darvozaga yoki egali-tetikli
inson bandiga biriktirilgan» degan hisob-kitob va u bugun rost.
