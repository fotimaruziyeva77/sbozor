---
phase: 9
slug: ui-polish-motion-qatlami
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-08-17
updated: 2026-08-17
human_only_verifications:
  - item: 60fps arzon Android qurilmada — 6-qadam xoreografiya va dashboard stagger jank bermaydi (ROADMAP SC#5)
    why_not_automatable: jsdom layout ham, kompozitsiya ham QILMAYDI — `getBoundingClientRect()` nol qaytaradi, `Element.animate` va `document.getAnimations()` UMUMAN yo'q [O'LCHANDI: jsdom 30.0.1 + vitest 4.1.10]. Ya'ni «kadr tushdimi?» savoliga test qatlamida javob beradigan sirt YO'Q. Mexanik proksi G-motion-3(a) — u `@keyframes` xossalari to'plamini `transform`/`opacity` bilan qulflaydi va `width`/`height`/`top`/`left` ni nolga tushiradi, ya'ni layout-thrash SABABINI yo'q qiladi. Lekin sabab yo'qligi natija borligini isbotlamaydi: to'g'ri xossalar bilan ham juda ko'p bir vaqtli animatsiya arzon GPU'ni to'ldiradi. Bu — o'lchov, kod emas
    owner: Ijrochi (dala qurilmasi bilan)
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 09-HUMAN-UAT.md #1; natija KADR/SONIYA raqami bilan yoziladi
  - item: Lighthouse Performance >= 90 va CLS < 0.05 (arzon Android profili, ROADMAP SC#5)
    why_not_automatable: Lighthouse CI'da YO'Q va bu fazada QO'SHILMAYDI (09-UI-SPEC §16.6, [QAROR]) — u headless Chrome + yangi ishlab chiqish bog'liqligini talab qiladi va `gate` byudjetiga daqiqalar qo'shardi. Bundan ham muhimi: mexanik qatlamning yashilligi bilan o'lchov qatlamining yo'qligini yopish TAQIQLANADI [MEROS: D-01, FOUND-07 va AI-02 darsi]. CLS uchun mexanik proksi bor va u TOR: G-motion-7(c) skeleton `h-N` sinfini kontent qator qutisiga tenglaydi — bu CLS ning AYNAN sababi [M-25: bugun 8–12px farq], lekin YAGONA sababi emas (shrift yuklanishi, kech kelgan karta va rasm ham siljitadi)
    owner: Ijrochi
    trigger: Birinchi deploy yoki /gsd-verify-work bosqichi — 09-HUMAN-UAT.md #2; natija SON bilan yopiladi, «ko'rinishi yaxshi» bilan EMAS
  - item: Iliq fon (rang 2.0), tungi va quyosh rejimlarining VIZUAL idroki — uch rol, real ekranlarda
    why_not_automatable: G-motion-5 kontrast NISBATINI o'lchaydi va u matematik jihatdan to'liq (12+ juftlik × 3 tema, izohlar ±0.01 da qulflangan). O'lchanMAGANI — o'sha nisbatlarning ODAM KO'ZIDA ishlashi. `text-muted` iliq fonda 5.06 nisbat bilan AA dan o'tadi, lekin ierarxiya hamon o'qiladimi; dark rejimda `border-ui` chegara talabini ushlaydi, lekin karta konturi quyuq fonda KO'RINADIMI; quyosh rejimida soya `none` qilingandan keyin karta yuzadan AJRALADIMI. Bu lug'at emas, IDROK savoli va u ekran yorqinligiga, burchagiga va foydalanuvchi yoshiga bog'liq — kassir ochiq havoda, direktor ofisda ishlaydi
    owner: Mahsulot egasi (kassir va direktor bilan)
    trigger: Pilot tayyorgarligi haftasi — 09-HUMAN-UAT.md #3
  - item: "Bayram BLOKLAMAGANINING dala tasdig'i: kassir 20 ketma-ket to'lov yozadi va bironta rasta kodi yo'qolmaydi"
    why_not_automatable: G-motion-2 buni SINTETIK ravishda o'lchaydi va o'lchovi halol — 150ms nuqtasida `userEvent.type` bilan yozilgan belgi input qiymatida to'liq turadi. Lekin u BITTA to'lovni, BITTA soxta taymer bilan, jsdom'da o'lchaydi. Dala sharoiti boshqacha: navbat turadi, kassir kodni YODDAN teradi, telefon issiq, tarmoq sekin va xoreografiya HAR to'lovda qayta ishga tushadi. Nosozlik shakli ham boshqacha — u «input bloklandi» emas, «kassir ikkilanib to'xtadi» bo'lib ko'rinadi va uni faqat kuzatish ko'radi. Bu fazaning eng qimmat nuqsoni aynan shu (09-UI-SPEC §1.2) va u sintetik testdan qochib qutula oladi
    owner: Mahsulot egasi (kassir bilan)
    trigger: Pilot tayyorgarligi haftasi — 09-HUMAN-UAT.md #4
  - item: Vestibulyar sezgir foydalanuvchi tasdig'i — OS darajasida reduced-motion yoqilganda ilova to'liq harakatsiz
    why_not_automatable: G-motion-1 `matchMedia` MOCK'i bilan o'lchaydi, ya'ni u «kod shoxi to'g'rimi?» degan savolga javob beradi. O'lchanMAGANI — brauzerning HAQIQIY `prefers-reduced-motion` signali bilan CSS `@media` blokining birgalikda ishlashi va uchinchi tomon xulqi (Radix dialog, `sonner` toast) o'sha rejimda TINCH qolishi. jsdom'da CSS umuman yuklanmaydi [O'LCHANDI: Tailwind sinfidan `getComputedStyle` «auto» qaytaradi], ya'ni `@media` blokining kuchga kirishi test qatlamida PRINSIPIAL ravishda ko'rinmaydi
    owner: Ijrochi (OS sozlamasi yoqilgan holda)
    trigger: Wave 3 yakuni — 09-HUMAN-UAT.md #5
automated_replacements:
  - was: Brauzerda tugmani bosib «animatsiya ishladimi?» deb ko'z bilan qarash
    now: "npx vitest run src/components/collect/success-choreography.test.tsx — klonning `pointer-events` INLINE qiymati «none», `aria-hidden` «true», 150ms nuqtasida input `activeElement` va yozilgan belgi to'liq turadi. ⛔ Sinf nomi YETARLI EMAS: jsdom Tailwind CSS ni yuklamaydi va `pointer-events-none` sinfidan `getComputedStyle` «auto» qaytaradi [O'LCHANDI]"
  - was: Tema tugmasini bosib uchala rejimni ko'z bilan aylantirib chiqish
    now: "node --test scripts/theme-tokens.test.mjs — `[data-theme=dark]` va `[data-theme=sun]` bloklaridagi o'zgaruvchi to'plamlari TENG va `--color-*-text` oilasi ikkalasida ham bor (M-18 ning besh AA buzilishi AYNAN shu tenglik bilan ushlanadi); `@theme inline` 0 marta; `dark:` varianti `className`/`cn(` argumentlari ichida 0 marta"
  - was: DevTools da rangni tanlab kontrast nisbatini qo'lda tekshirish
    now: "node --test scripts/contrast.test.mjs — `globals.css` dan `oklch()` qiymatlari PARSE qilinadi va WCAG 2.x nisbati hisoblanadi (12+ juftlik × 3 tema); izohdagi har `N.NN:1` da'vosi hisoblangan qiymat bilan ±0.01 da solishtiriladi. ⛔ Bog'liqlik YO'Q — ~30 qatorlik sof matematika, u 09-UI-SPEC ning 15 da'vosidan 13 tasini AYNAN takrorladi"
  - was: "`prefers-reduced-motion` ni OS da yoqib, sahifani qo'lda aylanib chiqish"
    now: "node --test scripts/motion-tokens.test.mjs — global `@media` bloki PARSE qilinadi (grep emas) va `animation-duration` HAM, `transition-duration` HAM `!important` bilan <=0.01ms ekani tekshiriladi; `animate-*` va `motion-reduce:` juftligi qamrovdan HOSILA. Klon shoxi esa `vi.stubGlobal(matchMedia, ...)` bilan komponent testida"
  - was: Kassir hisobi bilan kirib dashboard'da tushum kartasi ko'rinmasligini ko'z bilan tekshirish
    now: "npx vitest run src/app --dir src/app — `cashier` sessiyasida tushum kartasi DOM'da YO'Q VA `apiFetch` mock'ining chaqiruvlar soni 0; `director` sessiyasida BOR. ⛔ Ikki qatlam ataylab: `hidden` bilan yashirilgan karta so'rovni baribir yuborardi va summa tarmoq panelida ko'rinardi"
  - was: Yangi og'ir paket qo'shilmaganini `package.json` ga qarab eslab qolish
    now: "node --test scripts/motion-tokens.test.mjs — `dependencies` kalitlari TO'PLAM TENGLIGI bilan 18 ta nomdan iborat reyestrga solishtiriladi. ⛔ SON bilan emas: `length === N` shakli paket almashtirilganda (biri chiqib, biri kirganda) yolg'on yashil qolardi"
  - was: Skeleton kontentga almashganda karta «sakraydimi?» deb ko'z bilan kuzatish
    now: "node --test scripts/typography.test.mjs && npx vitest run src/components/headline/ — `isPending` shoxidagi `Skeleton` ning `h-N` sinfi kontent shoxining qator qutisiga TENG (reyestr jadvaldan o'qiladi, testda qayta yozilmaydi); `text-display` <=2 mahsulot faylida va `headline-card` da `unit === soum` shartiga bog'liq"
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Manba:** `09-RESEARCH.md` («Validation Architecture» bo'limi) va
> `09-UI-SPEC.md` §16 — bu fayl ulardan **HOSILA**, qayta yozilmaydi.
> Ziddiyat bo'lsa — 09-UI-SPEC.md §16 ustun (u `approved`).

---

## Bu fazaning validatsiyasi nimasi bilan boshqacha — buni birinchi o'qing

Bu faza `frontend/` dan tashqariga chiqmaydi va yangi endpoint ochmaydi.
Chegara boshqa joyda va u **ikki qavat**:

1. ⛔ **jsdom animatsiya haqida HECH NIMA bilmaydi** [O'LCHANDI: 09-RESEARCH
   Tuzoq 1]: `matchMedia` yo'q, `Element.animate` yo'q, `getBoundingClientRect`
   nol, Tailwind sinfidan `getComputedStyle` «auto». Shuning uchun barcha
   komponent tasdiqlari `matchMedia` STUBI + **inline uslub** ustida
   o'lchanadi; CSS darvozalari esa **fayl skani** (parse, grep emas).

2. ⛔ **Uchala CSS darvozasi bitta faylni o'qiydi** — `globals.css` 09-01 da
   TO'LIQ yopiladi (motion tokenlar + tema scope'lar + izohlar), aks holda
   har to'lqinda yarim-yashil darvoza qolardi [09-RESEARCH «Wave tartibi»].

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (birlamchi)** | vitest 4.1.10 + jsdom 30.0.1 + `@testing-library/react` 16.3.2 — React komponent qatlami (`src/**/*.test.tsx`) |
| **Framework (ikkilamchi)** | `node --test` (Node o'rnatilgan, ⛔ **nol bog'liqlik**) — CSS/JSON/matn skan darvozalari (`frontend/scripts/*.test.mjs`) |
| **Framework (uchlamchi)** | pytest 9.1.1 — ⛔ **bu fazada ISHLATILMAYDI**: yangi endpoint yo'q (09-UI-SPEC §14.3) |
| **Config — komponent** | `frontend/vitest.config.ts` (`environment: "jsdom"`, `include: ["src/**/*.test.tsx"]`) |
| **Config — global setup** | `frontend/vitest.setup.ts` — ⛔ `matchMedia` stubi bu yerga QO'YILMAYDI (global bo'lsa reduced-motion'ning teskari shoxi hech qachon o'lchanmasdi); stub HAR testda alohida |
| **Quick run command** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite command** | `npm run gate` (sim:up → backend → cv → bot → i18n:check → frontend test/typecheck/lint/build) |
| **Measured runtime** | ⛔ **09-07 da QAYTA O'LCHANDI (2026-08-17, tinch xost, IKKI o'lchov, ikkalasi exit 0):** `gate` **2259 / 2102 s** · byudjet **2300 s** (O'ZGARMADI) · zaxira **41 s (1,8 % — KRITIK TOR)** · `gate:fast` **189 / 171 s** · byudjet **200 s** (O'ZGARMADI) · zaxira 11 s. Oldingi (08-20): `gate` 1909/1842 s · `gate:fast` 155/152 s |
| **Kutilayotgan o'sish** | O'LCHANDI: A3 taxmini (~40–60 s) pastki yarmi ro'yobga chiqdi — `gate:fast` +34 s (155→189); skriptlar ~296→349, vitest 1110→1170. Ikki yaroqsiz urinish jurnali (dushanba-ko'rlik `11a4f3a` da tuzatilgan; meros flake №12 tegilmagan) `package.json //gate-budget` izohida |

⛔ **Zanjir boshida majburiy nazorat:** `frontend/node_modules` mavjudligi
(`npm ci --prefix frontend`) tekshirilsin [MEROS: STATE.md — 8-fazada
bo'shligi **29-daqiqada** ko'ringan].

---

## Sampling Rate

- **After every task commit:** `npm run gate:fast` (byudjet **200 s**)
- **After every plan wave:** `npm --prefix frontend test` + `npm --prefix frontend run i18n:check` + `npm --prefix frontend run typecheck`
- **Wave 1 dan keyin qo'shimcha:** `npm --prefix frontend run build` — tema qatlami `layout.tsx` + `<head>` skriptiga tegadi; SSG (3 locale × ~27 sahifa) build paytida yiqilishi mumkin va uni vitest ko'rmaydi
- **Before `/gsd-verify-work`:** `npm run gate` to'liq yashil bo'lishi SHART
- **Max feedback latency:** 200 s (`gate:fast`)

⛔ 9-fazada `npm run test:tenancy` va `cv:test`/`bot:test` alohida
chaqirilmaydi — faza `frontend/` dan tashqariga chiqmaydi; ular `gate`
zanjirida regressiya nazorati sifatida qoladi.

---

## Per-Task Verification Map

> ⚠ **GRANULYARLIK — REJA DARAJASIDA** (07/08-VALIDATION qoidasi): har
> taskning o'z `<automated>` bandi mos PLAN.md da yozilgan; bu jadval har
> rejaning **darvoza buyrug'ini** beradi.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P-01 | 09-01 | 1 | SC-3, SC-4, SC-5 | T-09-07 / T-09-09 / T-09-10 | G-motion-5: oklch parse + WCAG reyestri ≥12 juftlik × 3 tema (matn ≥4.5, chegara ≥3.0); izoh da'volari ±0.01; `bg-accent`+`text-accent-text` butun `src/` da 0 | node:test | `node --test frontend/scripts/contrast.test.mjs` | ✅ 09-01 da tug'ilgan | ✅ green |
| P-02 | 09-02 | 2 | SC-4, SC-5 | T-09-06 / T-09-SC | G-motion-1(a,b) + G-motion-3(a–d): global reduced-motion bloki PARSE bilan (`animation-duration` HAM `transition-duration` HAM ≤0.01ms `!important`); `@keyframes` xossalari to'plam tengligi; `duration-<raqam>` 0; `dependencies` 18 nom `deepEqual` | node:test | `node --test frontend/scripts/motion-tokens.test.mjs` | ✅ 09-02 da tug'ilgan | ✅ green |
| P-03 | 09-03 | 2 | SC-3, FOUND-04 | — | G-motion-4(a–e): `dark:` varianti `className`/`cn(` ichida 0; `@theme inline` 0; scope token to'plamlari va `--color-*-text` oilasi; `data-theme` reyestri 3 a'zo; `theme.*` uchala locale'da; `suppressHydrationWarning` + `<head>` skripti | node:test | `node --test frontend/scripts/theme-tokens.test.mjs` | ✅ 09-03 da tug'ilgan | ✅ green |
| P-04 | 09-04 | 3 | SC-1, SC-4, CASH-01 | — | G-motion-1(c) + G-motion-2(a–e): 150ms da input `activeElement` + bo'sh + `disabled`/`readOnly` false; yozilgan belgi to'liq turadi; klon INLINE `pointer-events: none` + `aria-hidden`; reduced mock'da klon YARATILMAYDI; `setTimeout` ichida `set[A-Z]` 0 (AST) | vitest | `npm --prefix frontend run test:component -- collect` | ✅ 09-04 da tug'ilgan | ✅ green |
| P-05 | 09-05 | 3 | SC-2, RECON-06 | — | G-motion-6(b,c) + G-motion-7(b,c): `cashier` sessiyasida tushum kartasi DOM'da YO'Q VA so'rov 0 chaqiruv, `director` da BOR; komponentda `hasPermission(` 0; count-up oxirgi kadri `format.number`; skeleton `h-11` geometriya juftligi | vitest | `npm --prefix frontend run test:component -- dashboard headline` | ✅ 09-05 da tug'ilgan | ✅ green |
| P-06 | 09-06 | 4 | SC-5 | — | G-motion-7(a,d,e): `text-display` ≤2 mahsulot faylida va reyestrga teng; `text-base` ≤7 · `text-xl` ≤4 · `text-3xl` 0 · `text-[` 0; `font-medium` ≤21; `animate-*` ↔ `motion-reduce:` juftligi ≥5 | node:test | `node --test frontend/scripts/typography.test.mjs` | ✅ 09-06 da tug'ilgan | ✅ green |
| P-07 | 09-07 | 5 | SC-1, SC-2, SC-3, SC-4, SC-5 | — | Beshala ROADMAP mezoni BITTA buyruqda o'lchanadi; 09-HUMAN-UAT bandlari SON bilan yopiladi; `nyquist_compliant` shu rejada `true` ga o'tadi | node:test + vitest | `node --test frontend/scripts/phase9-criteria.test.mjs` | ✅ 09-07 da tug'ilgan | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Wave 0 fayllari to'lqinlar ichida tug'iladi (08-faza naqshi) — har biri o'z
rejasida, darvozalar komponentlardan OLDIN tirik bo'ladi:

- [x] `frontend/scripts/contrast.test.mjs` — G-motion-5(a–d) + `--print` rejimi (izohlarni generatsiya qilish uchun) — **09-01**
- [x] `frontend/scripts/motion-tokens.test.mjs` — G-motion-1(a,b,d) + G-motion-3(a–d) — **09-02**
- [x] `frontend/scripts/theme-tokens.test.mjs` — G-motion-4(a–e) — **09-03**
- [x] `frontend/scripts/typography.test.mjs` — G-motion-7(a,d,e) — **09-06**
- [x] `frontend/src/components/collect/success-choreography.test.tsx` — G-motion-1(c) + G-motion-2(a–e) — **09-04**
- [x] `frontend/src/app/[locale]/(app)/dashboard/page.test.tsx` kengaytmasi — G-motion-6(b) — **09-05**
- [x] `frontend/scripts/phase9-criteria.test.mjs` — beshala mezon bitta buyruqda — **09-07**

⛔ Freymvork o'rnatish **kerak emas** — vitest, jsdom, Testing Library,
`node --test` hammasi mavjud. ⛔ `vitest.setup.ts` ga `matchMedia` stubi
**QO'SHILMAYDI** — stub har testda alohida.

`nyquist_compliant` → `true` sharti: yettala Wave 0 fayli tug'ilgach VA
beshala qo'lda band `09-HUMAN-UAT.md` ga ko'chirilgach — bu **09-07** ning
ishi. `wave_0_complete` ham o'sha yerda `true` bo'ladi.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| 60fps arzon Androidda (xoreografiya + stagger) | SC-5 | jsdom layout/kompozitsiya qilmaydi; «kadr tushdimi?» ga test sirti YO'Q | `09-HUMAN-UAT.md` #1 — natija KADR/SONIYA bilan |
| Lighthouse ≥90 va CLS <0.05 | SC-5 | Lighthouse CI'da yo'q va qo'shilmaydi (§16.6); mexanik proksi G-motion-7(c) TOR | `09-HUMAN-UAT.md` #2 — ikki SON bilan |
| Uch temaning vizual idroki (uch rol) | SC-3 | Nisbat o'lchangan, IDROK o'lchanmagan — ekran/yorug'lik/yosh omillari | `09-HUMAN-UAT.md` #3 — 3 tema × 3 rol jadvali |
| Bayram bloklamagani — dala (20 ketma-ket to'lov) | SC-1, SC-4 | Sintetik o'lchov bitta to'lov/soxta taymer; dala nosozligi «kassir ikkilanib to'xtadi» bo'lib ko'rinadi | `09-HUMAN-UAT.md` #4 — 20/20 va yo'qolgan belgi 0 |
| Vestibulyar tasdiq (OS reduced-motion) | SC-4 | Haqiqiy media-signal + uchinchi tomon xulqi jsdom'da PRINSIPIAL ko'rinmaydi | `09-HUMAN-UAT.md` #5 — 0 harakat / sahifa ro'yxati |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 200s (`gate:fast`)
- [x] `nyquist_compliant: true` set in frontmatter — 09-07 da qo'yildi: yettala Wave 0 fayli tug'ilgan va yashil, beshala qo'lda band `09-HUMAN-UAT.md` ga ega+tetik+kutilgan SON bilan ko'chirilgan

**Approval:** 2026-08-17 — 09-07 faza darvozasida imzolandi. ⚠ HALOLLIK: `human_only_verifications` dagi beshala band OCHIQ (birortasiga raqam yozilmagan — o'lchovlar real qurilma/inson idrokini talab qiladi); ularning ochiqligi `nyquist_compliant` ga ZID EMAS — bayroq «har o'lchanadigan xulq avtomat darvozaga yoki egali-tetikli inson bandiga biriktirilgan» degan hisob-kitob va u bugun rost
