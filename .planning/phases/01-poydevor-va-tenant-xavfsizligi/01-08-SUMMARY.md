---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 08
subsystem: ui
tags:
  [
    nextjs,
    react,
    next-intl,
    i18n,
    auth,
    zod,
    react-hook-form,
    react-query,
    rbac,
    session-restore,
    tailwind,
  ]

# Dependency graph
requires:
  - "01-02 (Next 16 skeleti, `src/i18n/{routing,navigation,request}.ts`, `proxy.ts`, Button/Input/Card, xabar fayllari va i18n darvozalari)"
  - "01-06 (auth HTTP kontrakti: login / select-market / refresh / logout / change-password; refresh cookie semantikasi; ROLE_PERMISSIONS matritsasi)"
  - "01-07 (bir vaqtda ishlangan: `GET|PATCH /api/v1/me` va `GET /api/v1/markets` — kontrakt bo'yicha iste'mol qilinadi)"
provides:
  - "`frontend/src/lib/api-types.ts` — zod sxemalari (`LoginResponse`, `SessionResponse`, `MeResponse`, `MarketSummary`, `soumSchema`) va `ApiLocale`"
  - "`frontend/src/lib/api-client.ts` — `apiFetch<T>()`, single-flight `refreshSession()`, `restoreSession()`, `loadPrincipal()`, `errorMessageKey()`, `ApiError`/`NetworkError`"
  - "`frontend/src/lib/auth-store.ts` — xotira sessiyasi (`useSyncExternalStore`), `AuthProvider`, `useAuthStore()`"
  - "`frontend/src/lib/query-provider.tsx` — `QueryClient` (staleTime 30s, 4xx da retry yo'q)"
  - "`frontend/src/lib/rbac.ts` — `hasPermission()`, `roleLabelKey()` (UI ko'zgusi)"
  - "`(auth)` marshrut guruhi: login, change-password, select-market"
  - "`(app)` himoyalangan qatlam + `AppShell` + `LocaleSwitcher` + `UserMenu` + dashboard"
  - "22 yangi tarjima kaliti (`auth.*`, `shell.*`, `roles.*`, `common.languageLabel`, `errors.required`) uchala tilda"
affects:
  - "01-09 (users/audit UI — `(app)` qatlami, `AppShell` navigatsiyasi, `apiFetch` va `hasPermission` tayyor; `/users` va `/audit` yo'llari allaqachon menyuda)"
  - "02 (yangi bozor ustasi — wizard shu qobiq ichida ochiladi)"
  - "06 (kassir mobil rejimi — pastki navigatsiya paneli va 44px nishonlar shu yerda o'rnatildi)"
  - "Barcha keyingi frontend rejalari (`apiFetch` + zod sxemasi naqshini takrorlaydi)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Access token FAQAT xotirada; sessiya `POST /auth/refresh` bilan tiklanadi"
    - "Modul darajasidagi sessiya + `useSyncExternalStore` — React'siz kod (`api-client`) bilan bitta haqiqat manbai"
    - "Single-flight refresh navbati — rotatsiyani o'z-o'zini o'ldirishdan saqlaydi"
    - "Har javob chegarada `zod` sxemasi bilan parse qilinadi"
    - "Xato -> tarjima KALITI xaritasi; xom `detail` foydalanuvchiga hech qachon ko'rsatilmaydi"
    - "Login sahifasi umumiy xato xaritasidan ATAYIN foydalanmaydi (enumeration)"
    - "`client-only` importi sessiya modullarini Server Component grafidan uzadi"
    - "Til yorliqlari endonim sifatida literal qoladi, qolgan barcha matn `next-intl` orqali"

key-files:
  created:
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/api-client.ts
    - frontend/src/lib/auth-store.ts
    - frontend/src/lib/query-provider.tsx
    - frontend/src/lib/rbac.ts
    - "frontend/src/app/[locale]/(auth)/layout.tsx"
    - "frontend/src/app/[locale]/(auth)/login/page.tsx"
    - "frontend/src/app/[locale]/(auth)/change-password/page.tsx"
    - "frontend/src/app/[locale]/(auth)/select-market/page.tsx"
    - "frontend/src/app/[locale]/(app)/layout.tsx"
    - "frontend/src/app/[locale]/(app)/dashboard/page.tsx"
    - frontend/src/components/auth/login-form.tsx
    - frontend/src/components/auth/change-password-form.tsx
    - frontend/src/components/auth/market-picker.tsx
    - frontend/src/components/shell/app-shell.tsx
    - frontend/src/components/shell/locale-switcher.tsx
    - frontend/src/components/shell/user-menu.tsx
  modified:
    - "frontend/src/app/[locale]/layout.tsx"
    - "frontend/src/app/[locale]/page.tsx"
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "Principal LOGIN javobidan quriladi, `/me` dan emas — login `/me` ishlamasa ham oxirigacha ishlaydi; `/me` faqat profil to'ldirishi (ism, telefon, `id`)"
  - "Sessiya tiklashda `/me` MAJBURIY va yiqilsa sessiya bekor qilinadi (fail-closed) — `must_change_password` ni taxmin qilish D-02 ni chetlab o'tish yo'li bo'lardi"
  - "Sessiya holati modul darajasida + `useSyncExternalStore`; `api-client` uni React'siz o'qiydi va 401 dan keyin yozadi"
  - "Bozorlar ro'yxati asosan login javobidan; `GET /markets` faqat zaxira — bozor tanlanmagan oddiy foydalanuvchini RLS kontekstisiz so'rovga bog'lab qo'ymaslik uchun"
  - "Login formasining xato xaritasi umumiy `errorMessageKey()` dan ALOHIDA — u `account_blocked` ni ko'rsatib enumeration signali berardi"
  - "`apiErrorSchema.detail` — `unknown`, `string` emas: FastAPI 422 da massiv qaytaradi va qattiq sxema xato yo'lining o'zini yiqitardi"
  - "`(app)` qatlami klient komponenti; `dashboard` ham klient — SSG saqlanib qoldi (18 sahifa prerender)"
  - "Til yorliqlari (`O'zbekcha`/`Ўзбекча`/`Русский`) tarjima fayllarida EMAS — endonim tarjima qilinmaydi"

patterns-established:
  - "Pattern: grep darvozasi bilan qulflangan taqiq izohda ham literal yozilmaydi"
  - "Pattern: `useEffect` ichida sinxron `setState` o'rniga holat DERIVATSIYA qilinadi"
  - "Pattern: logout/oqim uzilishida sessiya `onSettled` da tozalanadi — server javobiga bog'lanmaydi"
  - "Pattern: endpoint yo'llari komponent yuqorisida nomlangan konstanta sifatida e'lon qilinadi"

requirements-completed: [FOUND-04, FOUND-01]

# Metrics
duration: 40min
completed: 2026-07-29
---

# Phase 1 Plan 08: Auth qobig'i va bir bosishli til almashtirgich Summary

**Login → majburiy parol almashtirish → bozor tanlash → himoyalangan panel oqimi to'liq qurildi; access token brauzer omboriga umuman yozilmaydi va sahifa yangilanganda sessiya refresh cookie orqali tiklanadi; til bir bosishda almashadi, URL prefiksi ko'chadi va tanlov profilga yoziladi — 18 sahifa uchala tilda statik prerender bo'ladi va `MISSING_MESSAGE` hech qayerda ko'rinmaydi.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-29T13:10:00+05:00
- **Completed:** 2026-07-29T13:50:00+05:00
- **Tasks:** 3/3
- **Files created:** 17 (modifikatsiya: 5)
- **Yangi tarjima kalitlari:** 22 × 3 til (jami 63 kalit)

## Accomplishments

- **Access token brauzer omboriga UMUMAN yozilmaydi.** `grep -rn "localStorage\|sessionStorage" frontend/src/` bo'sh — na kodda, na izohda. Sessiya modul darajasidagi obyektda yashaydi va React unga `useSyncExternalStore` orqali obuna bo'ladi. Bu shakl ataylab tanlandi: `api-client` React hook'i emas, lekin u 401 dan keyin yangi tokenni O'SHA joyga yozishi kerak — ikkita nusxa (React state + modul o'zgaruvchisi) bo'lganda ular albatta bir kun ajralib ketardi.

- **Single-flight refresh navbati rotatsiyani o'z-o'zini o'ldirishdan saqlaydi.** Token muddati tugaganda sahifadagi hamma so'rov bir vaqtda 401 oladi. Navbatsiz har biri alohida `/auth/refresh` chaqirardi; 01-06 dagi rotatsiya esa birinchi chaqiruvdan keyin eski `jti` ni bekor qiladi — ya'ni qolganlari "o'g'irlangan token" sifatida kelib, **butun oilani** bekor qildirardi va foydalanuvchi sababsiz chiqib ketardi. Endi bir vaqtda faqat bitta refresh ketadi.

- **Majburiy parol almashtirishni chetlab o'tishga ikki qarama-qarshi javob berildi.** `(app)` qatlami `mustChangePassword` ni har render'da tekshiradi VA sessiya tiklashda `/me` yiqilsa sessiya **bekor qilinadi** (fail-closed). Ikkinchisi muhimroq: `must_change_password` ni "false" deb taxmin qilish tarmoq xatosini D-02 ni chetlab o'tish yo'liga aylantirardi.

- **Login sahifasi umumiy xato xaritasidan ATAYIN foydalanmaydi.** `errorMessageKey()` `account_blocked` ni alohida xabarga aylantiradi — bu kirish sahifasida "bu raqam mavjud va bloklangan" degan ochiq signal bo'lardi va 01-06 bayt darajasida yopgan enumeration teshigini UI tomondan qayta ochardi. Login formasining o'z, torroq xaritasi bor: `invalid_credentials` va `too_many_attempts` dan boshqa hamma narsa `errors.generic`.

- **Uchala til jonli tekshirildi (dev server).** `/` → 307 → `/uz` → 307 → `/uz/dashboard`; `/uz/login` lotincha, `/uz-cyrl/login` kirillcha (`Телефон рақами`, `Кириш`), `/ru/login` ruscha (`Номер телефона`, `Войти`), `/ru/change-password` da `MISSING_MESSAGE` **0 ta**. Himoyalangan `/uz/dashboard` skelet holatida ham tarjimada (`Sessiya tiklanmoqda`).

- **18 sahifa statik prerender bo'ladi** (`/[locale]` + 4 marshrut × 3 til), garchi `(app)` qatlami va dashboard klient komponentlari bo'lsa ham — `setRequestLocale` ildiz layout'ida va `(auth)` sahifalarida chaqiriladi.

- **`docker compose --profile web build frontend` muvaffaqiyatli** — `sbozor-frontend:latest` obrazi standalone chiqish bilan yig'ildi, hech qanday yangi bog'liqlik qo'shilmadi.

## Task Commits

1. **Task 1: API klient, zod tiplari, xotira auth store va provayderlar** — `2889f16` (feat)
2. **Task 2: Login, majburiy parol almashtirish va bozor tanlash ekranlari** — `e78835a` (feat)
3. **Task 3: Himoyalangan qatlam, app shell va til almashtirgich** — `57cf283` (feat)

## Files Created/Modified

### Kutubxona qatlami (`frontend/src/lib/`)

- `api-types.ts` — har javob uchun `zod` sxemasi; `localeSchema` aynan `['uz-Latn','uz-Cyrl','ru']` (backend `Locale` enum'i bilan mos); `soumSchema` keyingi fazalar uchun oldindan e'lon qilingan (Pitfall 7)
- `api-client.ts` — `apiFetch<T>()` (`credentials:'include'`, Bearer, 401 da bir marta refresh), `refreshSession()` (single-flight), `restoreSession()`, `loadPrincipal()`, `errorMessageKey()`, `ApiError`/`NetworkError`
- `auth-store.ts` — modul sessiyasi + `AuthProvider` + `useAuthStore()`; `client-only` importi bilan Server Component grafidan uzilgan
- `query-provider.tsx` — `staleTime` 30 s, 4xx va 401 da retry yo'q, mutatsiyalarda retry yo'q
- `rbac.ts` — `ROLE_PERMISSIONS` ning UI ko'zgusi + `roleLabelKey()`; fayl boshida "bu xavfsizlik chegarasi emas" izohi

### Marshrutlar

- `(auth)/layout.tsx` — markazlashtirilgan tor ustun (matnsiz)
- `(auth)/login/page.tsx`, `(auth)/change-password/page.tsx`, `(auth)/select-market/page.tsx` — server komponentlari, `setRequestLocale` bilan
- `(app)/layout.tsx` — sessiya tiklash + uchta majburiy yo'naltirish + skelet
- `(app)/dashboard/page.tsx` — bozor nomi, rollar, bo'lim havolalari; **soxta raqam yo'q**
- `[locale]/page.tsx` — 01-02 dagi vaqtinchalik sahifa `/dashboard` ga yo'naltirishga almashtirildi
- `[locale]/layout.tsx` — `QueryProvider` + `AuthProvider` qo'shildi

### Komponentlar

- `auth/login-form.tsx` — telefon (`type="tel"`, `inputMode="tel"`, `+998` namunasi) + parol; yo'naltirish tartibi `must_change_password` → `market === null` → `/dashboard`, har doim `{locale: response.locale}` bilan
- `auth/change-password-form.tsx` — uch maydon, `zod` bilan uzunlik/moslik/farq tekshiruvlari
- `auth/market-picker.tsx` — karta ro'yxati, `POST /api/v1/auth/select-market`, bo'sh holatda `auth.noMarkets` + chiqish
- `shell/app-shell.tsx` — desktop yon panel + mobil pastki panel (≥44px), huquq bo'yicha filtrlanadi
- `shell/locale-switcher.tsx` — segment tugmalar, bir bosishda `router.replace(pathname,{locale})` + `PATCH /api/v1/me`
- `shell/user-menu.tsx` — Radix dropdown, tarjima qilingan rol yorliqlari, chiqish

## Decisions Made

- **Principal LOGIN javobidan quriladi.** Login javobida foydalanuvchi `id` si yo'q, lekin marshrutlash uchun kerak bo'lgan HAMMA narsa bor (`locale`, `must_change_password`, `market`, `roles`, `is_platform_admin`). Agar principal `/me` dan qurilganda, `/me` ishlamagan holatda **login umuman ishlamasdi**. Endi `/me` faqat "eng yaxshi harakat" bilan ism/telefon/`id` ni to'ldiradi va yiqilsa menyu rol yorlig'ini ko'rsatadi.

- **Sessiya tiklashda esa `/me` MAJBURIY.** `POST /auth/refresh` javobida na `locale`, na `must_change_password` bor — ular faqat `/me` da. Bu yerda yumshoq qulash XAVFLI bo'lardi, shuning uchun `restoreSession()` fail-closed: `/me` yiqilsa sessiya tozalanadi va foydalanuvchi login'ga tushadi.

- **Bozorlar ro'yxati asosan login javobidan olinadi.** `GET /markets` faqat zaxira. Sabab: bozor tanlanmagan ODDIY foydalanuvchi (platforma admini emas) uchun serverda tenant konteksti yo'q va `markets` RLS ostida bo'sh qaytishi mumkin — login javobidagi ro'yxat esa har doim to'g'ri.

- **`(app)` qatlami klient komponenti.** `setRequestLocale` u yerda chaqirilmaydi (klient komponentida mumkin emas), lekin ildiz `[locale]/layout.tsx` uni chaqiradi va build 18 sahifani statik prerender qildi — ya'ni statik render yo'qolmadi.

- **Til yorliqlari tarjima fayllarida emas.** `Русский` ni o'zbekchaga "tarjima qilish" tanlovni o'qib bo'lmas qiladi: foydalanuvchi o'zi tushunadigan yagona so'zni izlaydi. Bu qoida `<action>` dagi "hech qanday matn hardcode qilinmaydi" talabidan ATAYIN chetga chiqadi va sababi kodda yozilgan.

- **`emptyResponseSchema = z.undefined()`** — 204 javoblar (logout, change-password) uchun. Alternativa (`schema` ni ixtiyoriy qilish) tip xavfsizligini yo'qotardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Izohlardagi literal matnlar grep darvozalarini yiqitardi**

- **Found during:** Task 1 va Task 3 yakuniy tekshiruvlari
- **Issue:** Uchta izohda qabul mezoni TAQIQLAGAN aynan o'sha literal bor edi: `auth-store.ts` da brauzer ombori API nomlari ("bularni ishlatmaymiz" degan izohda), `login/page.tsx` va `login-form.tsx` da yangi hisob ochish iborasi, `locale-switcher.tsx` da Next navigatsiya modulining nomi ("bu yerdan olmang" izohida). Uchalasi ham `grep` ni 0 dan boshqa qiymatga chiqarardi. Bu 01-01/01-03/01-05/01-06 dagi bilan **aynan bir xil sinf xato**.
- **Fix:** Izohlar ma'nosini to'liq saqlagan holda literal tokensiz qayta yozildi va har biriga "bu qoida grep darvozasi bilan qulflangan" eslatmasi qo'shildi.
- **Files modified:** `frontend/src/lib/auth-store.ts`, `frontend/src/app/[locale]/(auth)/login/page.tsx`, `frontend/src/components/auth/login-form.tsx`, `frontend/src/components/shell/locale-switcher.tsx`
- **Verification:** uchala grep ham exit 1 (natija yo'q)
- **Committed in:** `2889f16`, `e78835a`, `57cf283`

**2. [Rule 1 - Bug] `react-hooks/set-state-in-effect` — effekt ichida sinxron `setState`**

- **Found during:** Task 3 (`npm run lint`)
- **Issue:** `(app)/layout.tsx` da "sessiya allaqachon bor" holati effekt ichida `setChecked(true)` bilan belgilanardi. Bu kaskadli render beradi va Next 16 eslint konfiguratsiyasida **xato** (ogohlantirish emas) — ya'ni CI qizil bo'lardi.
- **Fix:** Holat derivatsiya qilindi: `const hasSession = accessToken !== null && principal !== null; const checked = hasSession || restoreAttempted;`. `setState` faqat asinxron `.then()` ichida qoldi.
- **Verification:** `npm run lint` exit 0
- **Committed in:** `57cf283`

**3. [Rule 2 - Missing Critical] `apiErrorSchema.detail` qattiq `string` bo'lsa xato yo'lining O'ZI yiqilardi**

- **Found during:** Task 1 (xato o'qish yo'lini yozishda)
- **Issue:** Reja `ApiErrorSchema = z.object({ detail: z.string() })` ni ko'rsatgan. FastAPI esa 422 da `detail` ni **massiv** qaytaradi (validatsiya xatolari ro'yxati). Qattiq sxema `parse()` da otilib, foydalanuvchi haqiqiy xato o'rniga tushunarsiz `ZodError` olardi.
- **Fix:** `detail: z.unknown()` + `readErrorDetail()` yumshoq o'qiydi: satr bo'lsa kod sifatida ishlatiladi, aks holda bo'sh qoladi va UI `errors.generic` ga tushadi (T-01-65 bilan mos).
- **Committed in:** `2889f16`

**4. [Rule 2 - Missing Critical] Sessiya tiklashda fail-closed xulq**

- **Found during:** Task 2 (`restoreSession` dizayni)
- **Issue:** `/auth/refresh` javobida `must_change_password` YO'Q. Uni `/me` dan olish kerak, `/me` yiqilsa esa "false" deb taxmin qilish oson yo'l edi — va bu D-02 ni chetlab o'tishning tayyor retsepti (T-01-64): vaqtinchalik parolli foydalanuvchi sahifani yangilab, tarmoq uzilishi paytida panelga kirib qolardi.
- **Fix:** `/me` yiqilsa `clearSession()` va `false` qaytariladi — foydalanuvchi login'ga tushadi. Sabab kod izohida yozilgan.
- **Committed in:** `e78835a`

**5. [Rule 2 - Missing Critical] Chiqishda sessiya server javobiga bog'lanmaydi**

- **Found during:** Task 2 va Task 3
- **Issue:** `POST /auth/logout` tarmoq xatosi bilan yiqilsa, `onSuccess` da tozalash hech qachon bajarilmasdi va brauzerda ISHLAYDIGAN access token qolib ketardi.
- **Fix:** `onSettled` — sessiya har qanday natijada tozalanadi va `/login` ga o'tiladi.
- **Files modified:** `market-picker.tsx`, `user-menu.tsx`
- **Committed in:** `e78835a`, `57cf283`

**6. [Rule 3 - Blocking] `[locale]/page.tsx` rejaning fayl ro'yxatida yo'q edi**

- **Found during:** Task 2
- **Issue:** 01-02 qoldirgan vaqtinchalik ildiz sahifa faqat `appName` + `appTagline` ko'rsatardi. Rejaning `human-check` ro'yxati esa "1. `/` ochilsin → `/uz` ga; 2. **Login sahifasida** ... kir" deb boshlanadi — ya'ni `/uz` dan login'ga yo'l bo'lishi SHART, aks holda tekshiruv ikkinchi qadamda to'xtardi. 01-02 SUMMARY ham bu sahifani "01-08 almashtiradi" deb belgilagan.
- **Fix:** Ildiz sahifa `/dashboard` ga yo'naltiradi; "kirganmi yoki yo'qmi" qarori `(app)` qatlamida BITTA joyda qoladi.
- **Verification:** `curl /` → 307 `/uz`; `curl /uz` → 307 `/uz/dashboard`
- **Committed in:** `e78835a`

**7. [Rule 3 - Blocking] `(auth)/layout.tsx` qo'shildi (rejada yo'q)**

- **Found during:** Task 2
- **Issue:** Uchala kirish sahifasi bir xil markazlashtirilgan qobiqni talab qiladi. Uni har sahifada takrorlash uch nusxa Tailwind sinf zanjiri berardi va ular albatta ajralib ketardi.
- **Fix:** Matnsiz `(auth)/layout.tsx` (01-02 dagi "primitivlarda matn hardcode qilinmaydi" naqshiga sodiq).
- **Committed in:** `e78835a`

**8. [Rule 2 - Missing Critical] Rejada nomlanmagan besh tarjima kaliti**

- **Found during:** Task 2 va Task 3
- **Issue:** Rejaning kalit ro'yxati formalarni to'liq qoplamasdi: bo'sh maydon xatosi, telefon formati xatosi, parol almashtirish sahifasining sarlavhasi, "yangi parol joriysidan farq qilsin" xatosi va navigatsiya bloklarining `aria-label` i uchun kalit yo'q edi. Ularsiz UI'da tarjimasiz matn yoki nomsiz navigatsiya qolardi.
- **Fix:** `errors.required`, `auth.invalidPhone`, `auth.changePasswordTitle`, `auth.passwordSameAsCurrent`, `shell.sections` qo'shildi (uchala tilda; `uz-Cyrl` generatsiya bilan).
- **Verification:** `npm run i18n:check` → 63 kalit × 3 til, kalit va ICU parity to'liq
- **Committed in:** `e78835a`, `57cf283`

**9. [Rule 3 - Blocking] `auth.passwordTooShort` dagi ICU parametri olib tashlandi**

- **Found during:** Task 2
- **Issue:** Kalit dastlab `{min}` platsholderi bilan yozilgandi, lekin umumiy `errorMessageKey()` xaritasi `weak_password` kodini shu kalitga xaritalaydi va u yerda ARGUMENT uzatib bo'lmaydi — natijada `next-intl` xato beradi.
- **Fix:** Matn parametrsiz yozildi (`kamida 10 ta belgi`), qiymat `MIN_PASSWORD_LENGTH` konstantasi bilan bir xil va u backend `schemas.py` ga havola bilan izohlangan.
- **Committed in:** `e78835a`

**10. [Rule 2 - Missing Critical] `Principal` rejadagidan kengroq**

- **Found during:** Task 1
- **Issue:** Reja `{userId, roles, marketId, isPlatformAdmin, locale, mustChangePassword}` ni ko'rsatgan, lekin `user-menu.tsx` ism/telefonni, `app-shell.tsx` esa bozor NOMINI ko'rsatishi kerak. Ularsiz menyuda bo'sh tugma va sarlavhada `uuid` chiqardi.
- **Fix:** `phone`, `fullName`, `marketName` qo'shildi; `userId` `string | null` qilindi (login javobida `id` yo'q).
- **Committed in:** `2889f16`, `e78835a`

**11. [Rule 3 - Blocking] `api-client.ts` rejadagidan kengroq yuza beradi**

- **Found during:** Task 2
- **Issue:** Reja `api-client.ts` da faqat `apiFetch` ni ko'rsatgan. Lekin `restoreSession()` (refresh + `/me`) va `loadPrincipal()` ni komponentga qo'yish ularni ikki joyda (login va `(app)` qatlami) takrorlashga majbur qilardi; `auth-store.ts` ga qo'yish esa **aylanma import** hosil qilardi (`auth-store` → `api-client` → `auth-store`).
- **Fix:** Sessiya oqimi funksiyalari `api-client.ts` da alohida bo'limda (`refreshSession` allaqachon shu yerda edi). Import yo'nalishi bir tomonlama qoldi: `api-client` → `auth-store`.
- **Committed in:** `e78835a`

---

**Total deviations:** 11 auto-fixed — 2× Rule 1 (grep darvozalari, effekt ichidagi `setState`), 5× Rule 2 (xato sxemasi, fail-closed tiklash, `onSettled` tozalash, yetishmayotgan kalitlar, `Principal` maydonlari), 4× Rule 3 (ildiz sahifa, `(auth)` layout, ICU parametri, `api-client` yuzasi).
**Impact on plan:** Scope creep yo'q. Barcha o'zgarishlar rejaning O'Z qabul mezonlari va tahdid reyestri doirasida; ikkitasi (#4, #5) rejada ko'rinmagan xavfsizlik teshigini yopdi, bittasi (#6) rejaning `human-check` ro'yxatining birinchi ikki qadamini umuman bajarib bo'lmaydigan holatdan chiqardi.

## Issues Encountered

1. **01-07 endpointlari bu worktree'da hali yo'q.** `GET|PATCH /api/v1/me` va `GET /api/v1/markets` bir vaqtda, qo'shni agent tomonidan quriladi (01-07, Task 2). Frontend ularni rejaning `<interfaces>` bo'limida e'lon qilingan kontrakt bo'yicha iste'mol qiladi va **jonli birlashtirilgan tekshiruv wave birlashgandan keyin bajarilishi kerak**. Kontraktdan chetlanish bo'lsa, u `zod` sxemasida (`meResponseSchema`, `marketListItemSchema`) bitta joyda tuzatiladi.
2. **Uchidan-uchiga qo'lda tekshiruv (3-taskdagi `human-check`) to'liq bajarilmadi.** Sabab: backendni ko'tarish uchun `docker compose up` kerak, muhit yo'riqnomasi esa uni taqiqlaydi (qo'shni agent DB holatini ushlab turibdi) va `.env` fayli yo'q (01-05/01-06 da qayd etilgan). O'rniga `next dev` bilan **backendsiz** qismi to'liq tekshirildi: marshrutlash (`/` → `/uz` → `/uz/dashboard`), uchala tilning to'liq tarjimasi va himoyalangan qatlamning skelet holati. Qolgan qadamlar (haqiqiy login, F5 dan keyin sessiya tiklanishi, vaqtinchalik parol oqimi, platforma admini oqimi) **birlashtirishdan keyin bajarilishi kerak**.
3. **`npm audit` — 12 high (transitiv).** 01-02 da hujjatlashtirilgan holat o'zgarmadi: uchala zanjir ham CLAUDE.md da qulflangan versiyalarning transitiv bog'liqliklari. Bu rejada birorta yangi bog'liqlik qo'shilmadi (`package.json` tegilmadi).

## Known Stubs

| Stub | Fayl | Sabab / qachon yopiladi |
|------|------|--------------------------|
| `/users` va `/audit` yo'llari navigatsiyada va dashboard'da bor, lekin sahifalar hali yo'q | `app-shell.tsx`, `dashboard/page.tsx` | Sahifalarni **01-09** (wave 7, `depends_on: [01-07, 01-08]`) yaratadi. Havolalar rejaning `<action>` talabi bo'yicha hozirdan qo'yildi va huquq bo'yicha filtrlanadi; 01-09 birlashgunicha ular 404 beradi. Rejaning maqsadiga (FOUND-04 til almashtirish + FOUND-01 login oqimi) to'sqinlik qilmaydi. |
| Dashboard'da metrika bloki yo'q | `dashboard/page.tsx` | ATAYIN: soxta raqam ko'rsatish taqiqlangan (qabul mezoni). Haqiqiy metrikalar 5- va 6-fazalarda keladi. |

Boshqa stub yo'q: har bir forma, store, klient va qobiq komponenti to'liq ishlaydi va e'lon qilingan kontraktga ulangan.

## Threat Model Coverage

| Threat ID | Holat | Dalil |
|-----------|-------|-------|
| T-01-60 (XSS orqali token o'g'irlash) | **Yopildi** | `grep -rn "localStorage\|sessionStorage" frontend/src/` → bo'sh (izohda ham yo'q). Token modul xotirasida; `client-only` importi uni Server Component grafidan uzadi; refresh `httpOnly` cookie'da |
| T-01-61 (CSRF `/auth/refresh` ga) | **Yopildi** | Bazaviy yo'l NISBIY (`/api/v1`) — bitta origin; barcha so'rovlar `credentials:'include'` bilan o'sha origin'ga ketadi; cookie `SameSite=Lax` + `Path=/api/v1/auth` (01-06) |
| T-01-62 (yashirilgan tugmani chaqirish) | **Qabul qilindi (hujjatlashtirilgan)** | `rbac.ts` fayl boshida "bu xavfsizlik chegarasi emas" izohi; `app-shell.tsx` da ham takrorlangan; qaror serverda `require_permission` bilan |
| T-01-63 (login xatosida foydalanuvchini oshkor qilish) | **Yopildi** | `login-form.tsx` da ALOHIDA, tor xarita: faqat `invalid_credentials` va `too_many_attempts`; `account_blocked` ATAYIN xaritalanmagan va sababi kodda yozilgan |
| T-01-64 (majburiy parol almashtirishni chetlab o'tish) | **Yopildi** | `(app)/layout.tsx` har render'da tekshiradi; `restoreSession()` `/me` yiqilsa sessiyani BEKOR qiladi (fail-closed) — taxmin qilinmaydi |
| T-01-65 (xatoning ichki tafsilotini ko'rsatish) | **Yopildi** | `errorMessageKey()` faqat ma'lum kodlarni xaritalaydi; qolgani `errors.generic`; `readErrorDetail()` JSON bo'lmagan tanani jimgina yutadi |
| T-01-66 (tarjima matnining HTML sifatida render qilinishi) | **Yopildi** | `grep -rn "dangerouslySetInnerHTML" frontend/src/` → bo'sh; barcha xabar React matn tuguni |
| T-01-67 (401 tsiklida cheksiz refresh) | **Yopildi** | `refreshInFlight` navbati + har so'rov uchun BITTA qayta urinish; muvaffaqiyatsizlikda `clearSession()`; react-query 401 va 4xx da retry qilmaydi |

**Yangi threat flag:** yo'q. Yagona yangi tashqi yuza — `NEXT_PUBLIC_API_BASE_URL` muhit o'zgaruvchisi. U sir emas (compose'da `/api/v1` standarti bilan keladi), lekin uni boshqa origin'ga o'zgartirish cookie siyosatini (`SameSite`) qayta ko'rib chiqishni talab qiladi — bu shart kod izohida yozilgan (T-01-61 doirasida qoladi).

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi.

Frontend darvozalari (worktree'da toza `npm ci` dan keyin):

```
npm --prefix frontend run i18n:gen
npm --prefix frontend run i18n:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

Uchidan-uchiga tekshiruv uchun (wave birlashgandan keyin) `.env` kerak:

```
cp .env.example .env
npm run up && npm run migrate
npm --prefix frontend run dev
```

## Next Phase Readiness

**Tayyor:**

- **01-09 (users/audit UI):** `(app)` qatlami, `AppShell`, `apiFetch` + zod naqshi, `hasPermission()` va `roles.*` yorliqlari joyida. `/users` va `/audit` yo'llari navigatsiyada allaqachon bor va huquq bo'yicha filtrlanadi — 01-09 faqat sahifalarni qo'shadi. Yangi javob shakllari `api-types.ts` ga qo'shiladi (reja shuni ko'zlagan).
- **2-faza (bozor ustasi):** wizard shu qobiq ichida ochiladi; `react-hook-form` + `zodResolver` naqshi uch formada o'rnatildi.
- **6-faza (kassir mobil rejimi):** pastki navigatsiya paneli va 44px barmoq nishonlari shu rejada qurildi.

**Ochiq e'tibor nuqtalari:**

- **`GET|PATCH /api/v1/me` va `GET /api/v1/markets` bilan jonli integratsiya hali sinalmagan** — 01-07 bilan bir vaqtda ishlangan. Wave birlashgandan keyin BIRINCHI ish: login → dashboard → til almashtirish → F5 zanjirini haqiqiy backend bilan bosib chiqish. Kontrakt farqi bo'lsa u `api-types.ts` dagi ikki sxemada tuzatiladi.
- **`rbac.ts` backend matritsasining QO'LDA nusxasi.** Ikkalasi ajralib ketsa UI noto'g'ri menyu ko'rsatadi (xavfsizlik teshigi emas, lekin chalkashlik). Uzoq muddatda OpenAPI'dan generatsiya qilish yoki `GET /auth/me` javobidagi `permissions` ro'yxatidan foydalanish mumkin — ikkinchisi arzonroq va 01-09 da ko'rib chiqilishi kerak.
- **Brauzer testlari yo'q.** ROADMAP mezoni #2 (til bir bosishda) hozircha faqat qo'lda va `curl` bilan tasdiqlanadi; avtomatik brauzer testi 8-fazaga qoldirilgan (VALIDATION.md bo'yicha). Til almashtirgichning `PATCH` qismi regressiyaga eng ochiq joy.
- **`uz-Cyrl` matnlari ko'z bilan ko'rildi**, lekin `Ҳисоб`/`маъмурият` kabi so'zlar o'zbek kirill imlosi bo'yicha bir marta mutaxassis ko'rigidan o'tishi foydali (01-02 SUMMARY ham buni tavsiya qilgan).

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 22 ta artefaktning (17 yangi + 5 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda (`git diff --stat` 22 fayl ko'rsatadi).
- **Commitlar:** `2889f16`, `e78835a`, `57cf283` — uchtasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only ca542f7..HEAD` bo'sh.
- **Umumiy artefaktlarga tegilmadi:** `git diff --name-only ca542f7..HEAD -- .planning/STATE.md .planning/ROADMAP.md services/ migrations/ packages/ tests/` bo'sh — worktree rejimi, qo'shni agentning domeni butunlay tegilmagan.
- **Darvozalar:** `i18n:gen --check` (drift yo'q) · `i18n:check` (63 kalit × 3 til) · `typecheck` exit 0 · `lint` exit 0 · `test` 32/32 · `build` exit 0 (18 sahifa SSG + Proxy) · `docker compose --profile web build frontend` muvaffaqiyatli.
- **Grep darvozalari:** `localStorage|sessionStorage` → 0 · `type="email"|yangi hisob ochish iborasi|forgot` `(auth)/` da → 0 · `next/navigation` `components/shell/` da → 0 · `dangerouslySetInnerHTML` → 0 · `/api/v1/me` `locale-switcher.tsx` da → bor · `router.replace` `locale-switcher.tsx` da → bor · `credentials` `api-client.ts` da → bor.
- **Jonli tekshiruv (`next dev`, backendsiz):** `/` → 307 `/uz` · `/uz` → 307 `/uz/dashboard` · `/uz/login` 200 lotincha · `/uz-cyrl/login` kirillcha · `/ru/login` va `/ru/change-password` ruscha, `MISSING_MESSAGE` 0 ta · `/uz/dashboard` skeleti tarjimada.

---

_Phase: 01-poydevor-va-tenant-xavfsizligi_
_Completed: 2026-07-29_
