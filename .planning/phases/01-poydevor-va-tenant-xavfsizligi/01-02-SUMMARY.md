---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 02
subsystem: ui
tags:
  [
    nextjs,
    next-intl,
    i18n,
    tailwind,
    typescript,
    react,
    transliteration,
    docker,
    github-actions,
  ]

# Dependency graph
requires: []
provides:
  - "Next 16 frontend skeleti (App Router, src/, standalone build, Docker image)"
  - "Uch tilli locale routing: /uz · /uz-cyrl · /ru, `/` → `/uz` (D-15)"
  - "`src/i18n/{routing,navigation,request}.ts` kontraktlari — keyingi frontend rejalari shularga ulanadi"
  - "TypeScript kalit xavfsizligi (next-intl AppConfig augmentatsiyasi)"
  - "uz-Latn → uz-Cyrl build-time transliteratsiya + qo'lda tuzatish lug'ati (D-14)"
  - "i18n drift va kalit/ICU parity CI darvozalari"
  - "Apple-uslub dizayn primitivlari: Button · Input · Card (matnsiz)"
  - "Tailwind 4 CSS-first `@theme` token to'plami (semantik holat ranglari bilan)"
affects:
  - "01-08 (login/shell UI — routing, primitivlar va xabar namespace'laridan foydalanadi)"
  - "01-09 (audit ko'rish UI — `audit.*` namespace'iga matn qo'shadi)"
  - "02 (yangi bozor ustasi — wizard formalari shu dizayn tizimida)"
  - "06 (kassir mobil rejimi — `lg` tugma 44px barmoq nishoni)"

# Tech tracking
tech-stack:
  added:
    - "next@16.2.12, react@19.2.8, react-dom@19.2.8"
    - "next-intl@4.13.4"
    - "tailwindcss@4.3.3 + @tailwindcss/postcss@4.3.3"
    - "typescript@5.9.3 (aniq pin)"
    - "class-variance-authority, clsx, tailwind-merge, lucide-react, sonner"
    - "@tanstack/react-query, zod, react-hook-form, @hookform/resolvers"
    - "@radix-ui/react-{dialog,select,dropdown-menu}"
    - "eslint@9 + eslint-config-next@16.2.12 (flat config)"
  patterns:
    - "Next 16 `proxy.ts` (middleware.ts EMAS)"
    - "Tailwind 4 CSS-first `@theme` — `tailwind.config.*` yaratilmaydi"
    - "cva variantlari + `cn()` (twMerge∘clsx) dizayn primitivlari uchun"
    - "Generatsiya artefakti + `--check` drift darvozasi"
    - "node:test built-in runner — nol tashqi test bog'liqligi"

key-files:
  created:
    - "frontend/src/proxy.ts"
    - "frontend/src/i18n/routing.ts"
    - "frontend/src/i18n/navigation.ts"
    - "frontend/src/i18n/request.ts"
    - "frontend/src/global.ts"
    - "frontend/src/app/[locale]/layout.tsx"
    - "frontend/src/app/[locale]/page.tsx"
    - "frontend/src/lib/cn.ts"
    - "frontend/src/components/ui/{button,input,card}.tsx"
    - "frontend/src/app/globals.css"
    - "frontend/messages/{uz-Latn,ru,uz-Cyrl,uz-Cyrl.overrides}.json"
    - "frontend/scripts/gen-cyrillic.mjs"
    - "frontend/scripts/gen-cyrillic.test.mjs"
    - "frontend/scripts/check-messages.mjs"
    - "frontend/Dockerfile"
    - "frontend/.gitattributes"
    - ".github/workflows/ci-frontend.yml"
  modified:
    - "frontend/package.json"
    - "frontend/next.config.ts"
    - "frontend/tsconfig.json"

key-decisions:
  - "`ts → ц` blanket transliteratsiya qoidasi RAD ETILDI — o'zbekcha `-tsa`/`-tsin` shakllari cheksiz ochiq to'plam; ц talab qiluvchi o'zlashmalar yopiq to'plam, shuning uchun ular `words` lug'atida"
  - "Apostrof-digraf (`o'`, `g'`) boshqa digraflardan kuchliroq bog'lanadi — `yo'q` = y + o' = `йўқ`"
  - "`uz-Cyrl.json` da `_generated` kaliti YO'Q — u kalit-parity ni buzardi; qo'lda tahrirlanmasligini `--check` darvozasi ta'minlaydi"
  - "Testlar `node:test` da — `gen-cyrillic.mjs` ning nol-bog'liqlik shartini test qatlamiga ham kengaytiradi"
  - "`.gitattributes` (eol=lf) — `--check` bayt taqqoslashi Windows va ubuntu CI da bir xil natija berishi uchun"
  - "next-intl plagini 1-taskda emas, 2-taskda ulandi — u `src/i18n/request.ts` ni konfiguratsiya yuklanish vaqtidayoq talab qiladi"
  - "`app/layout.tsx` mavjud emas — `app/[locale]/layout.tsx` ildiz layout rolini oladi (`<html lang>` locale'ga bog'liq)"

patterns-established:
  - "Pattern: locale URL prefiksi ≠ locale qiymati — `/uz` foydalanuvchiga, `uz-Latn` esa `[locale]` segmentiga tushadi"
  - "Pattern: dizayn primitivlarida matn hardcode qilinmaydi — barcha satr `next-intl` orqali `children`/prop bo'lib keladi"
  - "Pattern: xabar fayllarida bitta manba (uz-Latn) + qo'lda ru + generatsiya uz-Cyrl"
  - "Pattern: ICU platsholderlari rekursiv parser bilan ajratiladi, hech qachon regex bilan emas"

requirements-completed: [FOUND-04]

# Metrics
duration: 32min
completed: 2026-07-29
---

# Phase 1 Plan 02: Frontend skeleti va 3 tilli i18n poydevori Summary

**Next 16 + Tailwind 4 frontend `proxy.ts` locale routing bilan (`/uz` · `/uz-cyrl` · `/ru`), determinstik uz-Latn → uz-Cyrl transliteratsiya generatori va ICU-daxlsizligini CI'da bloklovchi ikki darvoza.**

## Performance

- **Duration:** 32 min
- **Started:** 2026-07-29T04:12:52Z
- **Completed:** 2026-07-29T04:44:39Z
- **Tasks:** 3 (4 commit — 3-task TDD sikli bo'yicha ikkiga bo'lindi)
- **Files modified:** 35

## Accomplishments

- **Uchala locale marshruti jonli tekshirildi:** `/` → 307 → `/uz` (hatto `Accept-Language: ru-RU` bilan ham — D-15 isbotlandi), `/ru` → `<html lang="ru">` ruscha matn bilan, `/uz-cyrl` → `<html lang="uz-Cyrl">` kirillcha matn bilan.
- **`proxy.ts` to'g'ri yuklandi:** `next build` chiqishida `ƒ Proxy (Middleware)` satri bor — T-01-08 (jimgina ishlamay qolish) yopildi.
- **Transliteratsiya generatori 32 ta test bilan qoplandi**, jumladan ICU plural/select strukturasi, `{name}` platsholderi, `#` belgisi, URL/e-mail/HTML teglari daxlsizligi.
- **Ikkala CI darvozasi soxta yashil bermasligi tasdiqlandi:** sun'iy nosozlik kiritilib, drift darvozasi ham, kalit-parity ham, ICU-parity ham exit 1 qaytarishi ko'rsatildi.
- **Dizayn tizimi matnsiz:** `Button`/`Input`/`Card` da bitta ham foydalanuvchiga ko'rinadigan literal yo'q — hammasi `next-intl` orqali.
- **Docker image quriladi:** `node:24-alpine`, ko'p bosqichli, non-root `nextjs` foydalanuvchisi, `output: standalone`.

## Task Commits

1. **Task 1: Next.js 16 skeleti, Tailwind 4 va dizayn primitivlari** — `f40076f` (feat)
2. **Task 2: next-intl locale routing — proxy.ts, uch locale, TS kalit xavfsizligi** — `86e4e56` (feat)
3. **Task 3: uz-Cyrl transliteratsiya, parity tekshiruvi va frontend CI** (TDD):
   - RED — `4823574` (test): 29 ta yiqiladigan test
   - GREEN — `5fda979` (feat): generator + checker + CI; sikl ichida topilgan `yo'q` xatosi uchun yana 3 test qo'shildi (32 ta)

## Files Created/Modified

### i18n yadrosi

- `frontend/src/i18n/routing.ts` — 3 locale, `localePrefix: {mode, prefixes}`, `localeDetection: false`
- `frontend/src/proxy.ts` — `createMiddleware(routing)`; **`middleware.ts` EMAS**
- `frontend/src/i18n/request.ts` — `hasLocale` guard, `timeZone: 'Asia/Tashkent'` (FOUND-05)
- `frontend/src/i18n/navigation.ts` — `Link`, `redirect`, `usePathname`, `useRouter`, `getPathname`
- `frontend/src/global.ts` — `AppConfig` augmentatsiyasi: noto'g'ri kalit = kompilyatsiya xatosi

### Xabarlar va generator

- `frontend/messages/uz-Latn.json` — asosiy manba (39 kalit, 6 namespace)
- `frontend/messages/ru.json` — qo'lda, ruscha `few`/`many` plural branchlari bilan
- `frontend/messages/uz-Cyrl.json` — **generatsiya artefakti**, qo'lda tegilmaydi
- `frontend/messages/uz-Cyrl.overrides.json` — yagona qo'lda tahrirlanadigan kirill fayli
- `frontend/scripts/gen-cyrillic.mjs` — transliterator + rekursiv ICU parser + `--check`
- `frontend/scripts/check-messages.mjs` — kalit-parity + ICU argument parity
- `frontend/scripts/gen-cyrillic.test.mjs` — 32 test (`node:test`)

### Dizayn tizimi va infra

- `frontend/src/app/globals.css` — `@theme` tokenlari (neytral shkala, aksent, semantik holatlar, radius, soya)
- `frontend/src/components/ui/{button,input,card}.tsx` — cva variantlari, `lg` ≥ 44px
- `frontend/src/lib/cn.ts` — `twMerge(clsx(...))`
- `frontend/Dockerfile`, `frontend/.dockerignore` — standalone runtime
- `frontend/.gitattributes` — `eol=lf`
- `.github/workflows/ci-frontend.yml` — lint · typecheck · test · i18n:check · build

## Decisions Made

1. **`ts → ц` blanket qoida rad etildi.** Reja `<action>` da uni digraf ro'yxatiga kiritgan, lekin `<behavior>` da `protsent → процент` ni **overrides lug'atidan** deb belgilagan. Blanket qoida `aytsa → айца`, `ketsin → кецин` kabi buzilishlar beradi va bu shakllar o'zbekchada cheksiz produktiv to'plam. `ц` talab qiluvchi o'zlashmalar esa sanab chiqiladigan yopiq to'plam. Shuning uchun mapping'dan olib tashlandi, `words` lug'atiga ko'chirildi. Ikki test bu qarorni qulflaydi.
2. **Apostrof-digraf ustuvorligi.** `o'`/`g'` — o'zbek lotin alifbosining alohida harflari, shuning uchun ular `yo`/`yu`/`ya`/`ye` dan kuchliroq bog'lanadi.
3. **`_generated` kaliti qo'shilmadi.** Reja uni yoki `check` skriptini taklif qilgan; `_generated` kaliti kalit-parity darvozasini buzardi, shuning uchun `--check` yo'li tanlandi.
4. **Xos ismlar:** brend `SBOZOR` lotincha qoladi (acceptance criteria), toponimlar (`Karmana`, `Navoiy`) kirillcha yoziladi — o'zbek kirill imlosiga mos.
5. **`localeCookie` standart holatda qoldirildi.** `localeDetection: false` allaqachon cookie'ni marshrutlashdan chiqaradi, D-13 (01-08) esa cookie'ni keyinroq ishlatishi mumkin.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] next-intl plagini 2-taskga ko'chirildi**

- **Found during:** Task 1
- **Issue:** Reja `createNextIntlPlugin()` ni 1-taskdagi `next.config.ts` ga qo'yishni talab qiladi, lekin plagin `src/i18n/request.ts` mavjudligini **konfiguratsiya yuklanish vaqtidayoq** tekshiradi. Bu fayl 2-taskda tug'iladi → 1-taskda `next build` yiqildi (`Could not locate request configuration module`).
- **Fix:** 1-taskda `next.config.ts` faqat `output: 'standalone'` bilan qoldirildi; plagin 2-taskda i18n fayllari bilan birga ulandi. Yakuniy holat rejadagi bilan aynan bir xil — faqat commit chegarasi siljidi, buning evaziga ikkala commit ham yashil build beradi.
- **Files modified:** `frontend/next.config.ts`
- **Verification:** 1-task build exit 0; 2-task build exit 0 va `ƒ Proxy (Middleware)` ro'yxatda.
- **Committed in:** `f40076f` va `86e4e56`

**2. [Rule 3 - Blocking] `uz-Cyrl.json` 2-taskda bootstrap qilindi**

- **Found during:** Task 2
- **Issue:** `routing.locales` uchta locale e'lon qilgani uchun `next build` uchala xabar faylini talab qiladi. `uz-Cyrl.json` esa 3-taskdagi generator artefakti → 2-task build `Cannot find module '../../messages/uz-Cyrl.json'` bilan yiqildi.
- **Fix:** 2-taskda `uz-Cyrl.json` qo'lda seed sifatida yozildi; 3-task uni generator chiqishi bilan almashtiradi. **Natija: generator chiqishi seed bilan bayt-bayt bir xil chiqdi** (3-task commitida `uz-Cyrl.json` o'zgarmagan) — bu mapping to'g'riligining mustaqil tasdig'i bo'ldi.
- **Files modified:** `frontend/messages/uz-Cyrl.json`
- **Verification:** 2-task build exit 0; 3-taskda `--check` drift bermadi.
- **Committed in:** `86e4e56`

**3. [Rule 3 - Blocking] `eslint.config.mjs` qo'shildi**

- **Found during:** Task 1
- **Issue:** Reja `lint` skriptini va `eslint`/`eslint-config-next` bog'liqliklarini talab qiladi, lekin Next 16 da **`next lint` OLIB TASHLANGAN** — lint faqat `eslint` CLI va flat config orqali ishlaydi. Konfiguratsiya fayli rejaning fayl ro'yxatida yo'q edi.
- **Fix:** `frontend/eslint.config.mjs` yaratildi (`eslint-config-next/core-web-vitals` + `globalIgnores`), `lint` skripti `eslint .` qilib belgilandi. Manba: `node_modules/next/dist/docs/01-app/03-api-reference/05-config/03-eslint.md`.
- **Files modified:** `frontend/eslint.config.mjs`, `frontend/package.json`
- **Verification:** `npm run lint` exit 0.
- **Committed in:** `f40076f`

**4. [Rule 1 - Bug] `yo'q` → `ёъқ` transliteratsiya xatosi**

- **Found during:** Task 3 (GREEN sikli, birinchi generatsiyadan keyin)
- **Issue:** Digraf tartibi bir POZITSIYA ichida to'g'ri edi, lekin pozitsiyalar aro emas: `yo'q` da `yo` 0-indeksda mos kelib, `o'` ning 1-indeksda mos kelishiga yo'l qo'ymadi → `ёъқ` (to'g'risi `йўқ`). Bu xato uchta jonli xabarga (`errors.network`, `errors.forbidden`, `audit.filterAction` atrofidagi `bo'yicha` emas — u to'g'ri edi) ta'sir qildi.
- **Fix:** Apostrof-digraf ustuvorligi qoidasi qo'shildi — digrafning oxirgi harfi `o`/`g` bo'lsa va undan keyin apostrof kelsa, digraf qabul qilinmaydi.
- **Files modified:** `frontend/scripts/gen-cyrillic.mjs`
- **Verification:** Avval 3 ta regressiya testi yozildi va yiqilishi tasdiqlandi, so'ng tuzatish qo'llandi → 32/32 test yashil; `yo'q → йўқ`, `yo'l → йўл`, `sho'r → шўр`, `yog' → ёғ`, `ya'ni → яъни`.
- **Committed in:** `5fda979`

**5. [Rule 2 - Missing Critical] `.gitattributes` (eol=lf)**

- **Found during:** Task 3
- **Issue:** Windows'da git barcha fayllarni CRLF bilan checkout qiladi (`LF will be replaced by CRLF` ogohlantirishlari). `gen-cyrillic.mjs --check` esa bayt taqqoslash qiladi → ubuntu CI (LF) va Windows ish stoli o'rtasida soxta drift.
- **Fix:** `frontend/.gitattributes` da `* text=auto eol=lf`; qo'shimcha himoya sifatida `--check` taqqoslashdan oldin CRLF normallashtiradi.
- **Files modified:** `frontend/.gitattributes`, `frontend/scripts/gen-cyrillic.mjs`
- **Verification:** `npm run i18n:check` Windows'da exit 0.
- **Committed in:** `5fda979`

**6. [Rule 2 - Missing Critical] CI workflow least-privilege va `test` qadami**

- **Found during:** Task 3
- **Issue:** Reja `ci-frontend.yml` uchun `permissions` bloki va transliterator testlari qadamini ko'rsatmagan.
- **Fix:** `permissions: contents: read` (least-privilege), `concurrency` (eski runlarni bekor qilish) va `npm test` qadami qo'shildi.
- **Files modified:** `.github/workflows/ci-frontend.yml`
- **Verification:** Barcha qadamlar mahalliy ravishda alohida ishga tushirilib, exit 0 berdi.
- **Committed in:** `5fda979`

---

**Total deviations:** 6 auto-fixed (3× Rule 3 blocking, 1× Rule 1 bug, 2× Rule 2 missing critical)
**Impact on plan:** Yakuniy holat reja belgilagan holat bilan bir xil. Ikkita blocking chetlanish faqat commit chegarasini siljitdi (har bir commit yashil bo'lishi uchun). `ts → ц` qarori — yagona mazmunli farq, u `<behavior>` spetsifikatsiyasiga sodiq qoladi va `<action>` dagi digraf ro'yxatidan chetga chiqadi; sabab yuqorida asoslangan. Scope creep yo'q.

## Issues Encountered

1. **`node --test scripts/` katalogni modul deb hal qildi** (`Cannot find module .../scripts`). Yechim: `node --test scripts/*.test.mjs` glob shakli.
2. **Eskirgan `.next/types/validator.ts`** — 2-taskda `app/layout.tsx` o'chirilgandan keyin `tsc --noEmit` avvalgi buildning generatsiya qilingan tiplariga ishora qildi. Qayta `next build` tiplarni yangiladi. Toza muhitda (CI) bu holat yuzaga kelmaydi, chunki `.next/` yo'q.
3. **`aria-invalid:` variantining mavjudligi tasdiqlanmagan** edi. Kafolatlangan `aria-[invalid=true]:` arbitrar varianti ishlatildi; kompilyatsiya qilingan CSS'da mavjudligi grep bilan tekshirildi.

## Known Stubs

| Stub | Fayl | Sabab / qachon yopiladi |
|------|------|--------------------------|
| Vaqtinchalik ildiz sahifa (faqat `common.appName` + `common.appTagline` ko'rsatadi) | `frontend/src/app/[locale]/page.tsx` | Reja bo'yicha atayin — uchala locale marshrutini isbotlash uchun. Login sahifasi **01-08** rejasida keladi va bu sahifani almashtiradi. |
| `messages/*.json` dagi `auth.*`, `users.*`, `audit.*` namespace'lari hali hech qayerda ishlatilmaydi | `frontend/messages/` | Atayin — 01-08 va 01-09 shu daraxtga UI qo'shadi. Kalitlar oldindan e'lon qilinishi `AppConfig` tipini barqaror qiladi. |
| `public/` bo'sh (`.gitkeep`) | `frontend/public/` | Next.js shablon SVG'lari (Vercel/Next brendi) olib tashlandi; SBOZOR statik aktivlari dizayn bosqichida qo'shiladi. Dockerfile `COPY public` uchun katalog mavjud bo'lishi shart. |

Rejaning maqsadiga (`FOUND-04` — 3 tilli i18n poydevori) hech bir stub to'sqinlik qilmaydi.

## Deferred Issues

**npm audit: 12 high severity (transitiv, tuzatib bo'lmaydi).** Uchala zanjir ham CLAUDE.md da QULFLANGAN versiyalarning transitiv bog'liqliklari:

| Advisory | Zanjir | Nega tuzatilmadi |
|----------|--------|------------------|
| `brace-expansion` DoS | eslint 9 → @eslint/config-array → minimatch | `npm audit fix --force` **eslint@10** ni o'rnatadi (breaking); reja `eslint@9` ni belgilagan. Faqat dev-vaqt. |
| `postcss` XSS / path traversal | next 16.2.12 ichiga birlashtirilgan | `audit fix --force` **next@9.3.3** ni taklif qiladi — aql bovar qilmas downgrade. Build-vaqt. |
| `sharp` → libvips CVE | next 16.2.12 bog'liqligi | Yuqoridagi bilan bir xil. Runtime, lekin faqat `next/image` optimizatsiyasi ishlatilganda — hozircha ishlatilmaydi. |

**Tavsiya:** upstream (Next.js / eslint-config-next) patch relizini kuzatish; qayta baholash Phase 8 (xavfsizlik ko'rigi) da. Bu chetlanish emas — locked stack doirasida hal qilib bo'lmaydigan out-of-scope topilma.

## Threat Model Coverage

| Threat ID | Holat | Dalil |
|-----------|-------|-------|
| T-01-08 (`proxy.ts` yo'qolishi) | **Yopildi** | `frontend/src/middleware.ts` mavjud emas; build chiqishida `ƒ Proxy (Middleware)`; `curl /` → 307 `/uz` |
| T-01-09 (ICU platsholderlarining buzilishi) | **Yopildi** | Rekursiv ICU parser + `check-messages.mjs`; sun'iy `{имя}` nosozligi bilan darvozaning exit 1 berishi tasdiqlandi |
| T-01-10 (`NEXT_PUBLIC_*` orqali sir sizishi) | **Amal qilmaydi** | Bu rejada birorta `NEXT_PUBLIC_*` o'zgaruvchisi kiritilmadi |
| T-01-11 (tarjima matnining XSS'i) | **Yopildi** | `dangerouslySetInnerHTML` va `rich()` HTML string rejimi ishlatilmagan — barcha xabar React matn tuguni |
| T-01-SC (npm supply chain) | **Yopildi** | Barcha versiyalar registryda oldindan tekshirildi; `package-lock.json` commit qilindi; `@eloqnt/cli` va `react-leaflet` YO'Q |

**Yangi threat flag:** yo'q. `.github/workflows/ci-frontend.yml` yangi yuza qo'shadi, lekin `permissions: contents: read`, `pull_request_target` ishlatilmaydi va hech qanday secret o'qilmaydi.

## User Setup Required

None — tashqi servis konfiguratsiyasi talab qilinmaydi.

## Next Phase Readiness

**Tayyor:**

- 01-08 (auth/login UI) `src/i18n/navigation.ts` dagi `Link`/`redirect`/`useRouter` va `auth.*` xabar namespace'ini bevosita ishlatishi mumkin.
- 01-09 (audit UI) uchun `audit.*` kalitlari va `Card`/`Input`/`Button` primitivlari joyida.
- Til almashtirgich (D-13) uchun kontrakt tayyor: `router.replace(pathname, {locale})` + `PATCH /api/v1/me`. Komponentning o'zi 01-08 da quriladi.

**Diqqat qiladigan joylar:**

- Yangi xabar kaliti qo'shgan har bir reja `npm run i18n:gen` ni ishlatib `uz-Cyrl.json` ni **birga commit qilishi shart** — aks holda CI qizil bo'ladi. Bu README'da hujjatlashtirilgan.
- `frontend/next.config.ts` da `NEXT_PUBLIC_API_BASE_URL` hali yo'q — core-api'ga ulanish 01-08 da qo'shiladi.
- `uz-Cyrl.overrides.json` `words` lug'ati boshlang'ich holatda (8 ta yozuv). Kontent o'sgani sayin o'zlashma so'zlar qo'shilishi kerak; noto'g'ri transliteratsiya faqat ko'z bilan ko'rinadi — 01-08 dan keyin kirill sahifalarini bir marta ko'zdan kechirish tavsiya etiladi.

---

_Phase: 01-poydevor-va-tenant-xavfsizligi_
_Completed: 2026-07-29_
