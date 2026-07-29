---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 09
subsystem: ui
tags:
  [
    nextjs,
    react-query,
    nuqs,
    url-state,
    keyset-pagination,
    rbac,
    audit,
    i18n,
    zod,
    react-hook-form,
    radix,
    contract-test,
  ]

# Dependency graph
requires:
  - "01-02 (Next 16 skeleti, Button/Input/Card, i18n darvozalari va `uz-Cyrl` generatori)"
  - "01-07 (`GET|POST /users`, `POST /users/{id}/block|unblock|reset-password`, `GET /audit` kontrakti)"
  - "01-08 (`apiFetch` + zod naqshi, `auth-store`, `rbac.hasPermission`, `AppShell`, `(app)` himoyalangan qatlami)"
provides:
  - "`frontend/src/app/[locale]/(app)/users/page.tsx` — D-04 foydalanuvchi boshqaruv UI"
  - "`frontend/src/app/[locale]/(app)/audit/page.tsx` — D-12 filtrlanadigan audit ro'yxati"
  - "`frontend/src/components/users/*` — karta ro'yxati, yaratish dialogi, bir martalik parol oynasi"
  - "`frontend/src/components/audit/*` — filtr paneli, karta ro'yxati, eski/yangi farqi"
  - "`frontend/src/lib/queries.ts` — `useUsersQuery`, `useCreateUser`, `useBlockUser`, `useUnblockUser`, `useResetPassword`, `useAuditQuery`, `adminErrorMessageKey`"
  - "`api-types.ts` kengaytmasi — `MARKET_ADMIN_ASSIGNABLE_ROLES`, `assignableRoles()`, `AUDIT_ACTIONS`, `AUDIT_TABLES`, `LOCALE_LABELS` va 6 yangi zod sxemasi"
  - "`NuqsAdapter` ildiz layout'da — URL holati keyingi barcha filtr/hisobot ekranlari uchun tayyor"
  - "2 ta kontrakt testi (5 test): D-04 darvozasi va `AuditAction` <-> tarjima to'liqligi"
affects:
  - "01-10 (cross-tenant matritsa: UI endi `users` va `audit` endpointlarining har birini chaqiradi)"
  - "02 (bozor ustasi — `nuqs` va dialog naqshlari tayyor)"
  - "05/06 (hisobot va kassir ekranlari — `useInfiniteQuery` + keyset naqshi va URL filtr holati shu yerda o'rnatildi)"

# Tech tracking
tech-stack:
  added:
    - "nuqs 2.9.2 (MIT) — URL bilan sinxron filtr holati; CLAUDE.md stekida oldindan tasdiqlangan"
  patterns:
    - "Filtr holati URL'da, komponentda emas — panel ham, ro'yxat ham BITTA `useAuditFilters()` hookidan o'qiydi"
    - "Sahifalash kursor bilan (`useInfiniteQuery` + `next_cursor`) — jurnal so'rovlar ORASIDA o'sadi"
    - "Bir martalik sir `useMutation` bilan olinadi, `useQuery` bilan EMAS — kesh uni ushlab qolardi"
    - "Ikki tilda yozilgan kontrakt (Python enum + TS massiv) fayllarning O'ZINI o'qiydigan test bilan bog'lanadi"
    - "Sana/vaqt faqat `useFormatter` orqali — mintaqa `i18n/request.ts` da bitta joyda"
    - "URL qidiruv parametrini o'qiydigan daraxt `<Suspense>` chegarasi ichida — statik prerender saqlanadi"

key-files:
  created:
    - "frontend/src/app/[locale]/(app)/users/page.tsx"
    - "frontend/src/app/[locale]/(app)/audit/page.tsx"
    - frontend/src/components/users/user-list.tsx
    - frontend/src/components/users/create-user-dialog.tsx
    - frontend/src/components/users/temp-password-dialog.tsx
    - frontend/src/components/audit/audit-filters.tsx
    - frontend/src/components/audit/audit-list.tsx
    - frontend/src/components/audit/audit-diff.tsx
    - frontend/src/lib/queries.ts
    - frontend/scripts/role-gate.test.mjs
    - frontend/scripts/audit-actions.test.mjs
  modified:
    - frontend/src/lib/api-types.ts
    - "frontend/src/app/[locale]/layout.tsx"
    - frontend/src/components/shell/locale-switcher.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "D-04 ko'zgusi `api-types.ts` da, komponentda emas — va u BACKEND FAYLINI o'qiydigan test bilan qulflangan (sabotaj bilan o'lchandi)"
  - "Vaqtinchalik parol `useMutation` javobida qoladi va faqat sahifa holatida yashaydi — `useQuery` uni keshga tushirardi"
  - "Rol tanlovi `useWatch` bilan boshqariladi, `watch()` bilan emas (React Compiler `watch()` ni memoizatsiya qila olmaydi)"
  - "Filtr holati URL'da — panel va ro'yxat prop orqali emas, bitta hook orqali bog'langan"
  - "Aktor ismi `GET /users` dan qo'shiladi — `GET /audit` javobiga profil maydonlarini qo'shish shaxsiy ma'lumot yuzasini kengaytirardi (01-07 qarori saqlandi)"
  - "`actor_kind` maydoni javobda YO'Q — tizim aktori `actor_user_id === null` bilan aniqlanadi"
  - "Jadval filtri erkin matn emas, `AUDIT_TABLES` dan yopiq ro'yxat — tarjima qilinadi va xato yozilishi mumkin emas"
  - "Noma'lum `action`/`table_name` XOM ko'rinadi — u DB dagi texnik identifikator; yashirish jurnalda tushunarsiz bo'shliq qoldirardi"
  - "`LOCALE_LABELS` bitta manbada — til almashtirgich ham, yangi foydalanuvchi formasi ham shundan o'qiydi"

patterns-established:
  - "Pattern: ikki tilda yozilgan kontrakt uchun test NUSXANI emas, FAYLNING O'ZINI o'qiydi (01-07 dan meros, endi teskari yo'nalishda ham)"
  - "Pattern: `i18n:check` ro'yxat TO'LIQLIGINI ushlay olmaydi — ma'lumotdan keladigan kalit to'plami alohida test bilan qulflanadi"
  - "Pattern: bir martalik sir bitta komponent holatida tug'iladi va bitta joyda tozalanadi"
  - "Pattern: huquq tekshiruvi so'rovdan OLDIN — huquqsiz sahifa `GET` ham yubormaydi (jurnalga ma'nosiz rad etilgan urinish yozilmaydi)"

requirements-completed: [FOUND-03, FOUND-01, FOUND-04]

# Metrics
duration: 26min
completed: 2026-07-29
---

# Phase 1 Plan 09: Foydalanuvchi boshqaruvi va audit jurnali ekranlari Summary

**Bozor admini endi foydalanuvchi yaratadi (rollar TO'PLAMI bilan, va formada faqat kassir/nazoratchi ko'rinadi — D-04 server darvozasining aynan ko'zgusi), bloklaydi, parolini tiklaydi va vaqtinchalik parolni bir marta ko'radi; audit jurnali esa kim/qachon/nima/eski-yangi ustunlari va beshta URL bilan sinxron filtr bilan ochiladi — 120 tarjima kaliti uchala tilda to'liq, 24 sahifa statik prerender bo'ladi va ikki yangi kontrakt testi backend enum'lari bilan ajralib ketishni imkonsiz qiladi.**

## Performance

- **Duration:** ~26 min
- **Started:** 2026-07-29T09:11:07Z
- **Completed:** 2026-07-29T09:37:13Z
- **Tasks:** 2/2
- **Files created:** 11 (modifikatsiya: 9)
- **Tarjima kalitlari:** 120 × 3 til (oldin 63 edi — +57)
- **Frontend testlar:** 37 (oldin 32; +5 kontrakt testi)
- **Statik sahifalar:** 24 (oldin 18; `/users` va `/audit` × 3 til)

## Accomplishments

- **D-04 darvozasining UI ko'zgusi endi TEST bilan bog'langan, izoh bilan emas.** `MARKET_ADMIN_ASSIGNABLE_ROLES` ikki tilda, ikki faylda yashaydi: `services/core-api/app/api/v1/users.py` (haqiqiy 403 darvozasi) va `frontend/src/lib/api-types.ts` (forma qaysi katakchalarni ko'rsatishi). Ular ajralib ketsa hech bir mavjud test qizarmasdi — backend testlari frontend faylini bilmaydi, frontend esa backendni. `scripts/role-gate.test.mjs` ikkala faylning O'ZINI o'qiydi va to'plamlarni solishtiradi. **Sabotaj bilan o'lchandi:** frontend ro'yxatiga `director` qo'shilganda test darhol qizardi, qaytarilgandan keyin yana yashil.

- **`i18n:check` ushlay olmaydigan bo'shliq yopildi.** Mavjud darvoza uchala faylning bir-biriga MOSLIGINI tekshiradi, ro'yxatning TO'LIQLIGINI emas: `audit.actions.refresh_reuse_detected` uchala tilda ham yo'q bo'lsa, parity baribir yashil qolardi va foydalanuvchi o'zbekcha ekranda `refresh_reuse_detected` degan xom qatorni ko'rardi. `scripts/audit-actions.test.mjs` `AUDIT_ACTIONS` ni `sbozor_core.enums.AuditAction` bilan, so'ng uchala xabar faylining `audit.actions` kalitlari bilan solishtiradi (ortiqcha kalit ham xato). Xuddi shu tekshiruv `AUDIT_TABLES` uchun ham bor.

- **Vaqtinchalik parolning umri ATAYIN qisqartirildi (T-01-68).** U faqat ikki joyda bo'ladi: HTTP javob tanasida va sahifa holatidagi bitta `useState` da. `useMutation` tanlovi shu yerda mazmunli — `useQuery` bo'lganida React Query javobni keshga yozardi va parol komponent almashgandan keyin ham xotirada qolardi, ya'ni "bir marta ko'rsatiladi" kafolati jimgina yo'qolardi. Dialogning yagona yopilish yo'li (`onOpenChange`) qiymatni `null` ga qaytaradi. Diagnostika chiqishi, URL va brauzer ombori umuman ishlatilmaydi va bu grep darvozalari bilan qulflangan.

- **Filtr holati URL'da — va bu ikki muammoni birdan hal qildi.** Birinchisi mahsulot talabi (D-12 havolasi ulashiladigan bo'lsin: nazoratchi topgan nomuvofiqlikni direktorga "shu havolaga qara" deb yuboradi). Ikkinchisi arxitektura: filtr paneli va ro'yxat BITTA `useAuditFilters()` hookidan o'qiydi, ya'ni holat prop bo'lib uzatilmaydi va ikkovi ajralib qola olmaydi. Bo'sh qiymat URL'dan butunlay chiqib ketadi, shuning uchun havola qisqa qoladi.

- **Sahifalash kursor bilan — va bu backend qarorining UI tomondagi natijasi.** Har `GET /audit` yangi `read` qatori qo'shadi (D-09), ya'ni "birinchi sahifa" har so'rovda boshqacha. Raqamli sahifalashda o'sha yangi qatorlar sahifalarni surib yuborardi va foydalanuvchi 2-sahifada 1-sahifadagi yozuvni qayta ko'rardi. `useInfiniteQuery` + `next_cursor` bu holatni tuzilma darajasida yo'q qiladi; `queryKey` filtrlarni to'liq o'z ichiga oladi, ya'ni filtr o'zgarganda kesh yangi zanjir boshlaydi.

- **`/audit` sahifasi statik prerender ro'yxatida QOLDI.** URL qidiruv parametrini o'qish daraxtning shu qismini klient tomonga o'tkazadi; `<Suspense>` chegarasisiz Next 16 butun sahifani ro'yxatdan chiqarardi. Chegara bilan build 24 sahifani prerender qildi (`/users` va `/audit` uchala tilda).

- **Uchala til jonli tekshirildi** (`next dev`, backendsiz): `/uz/audit`, `/uz-cyrl/audit`, `/ru/audit` va `/uz/users` — hammasi 200; `?action=login&from=2026-07-01` bilan ham; `MISSING_MESSAGE` va `IntlError` **0 ta**; dev server jurnalida xato yo'q.

- **Kirill imlosi bitta joyda tuzatildi.** Transliterator `Filtrlarni` ni `Филтрларни` qilib qo'yardi (yumshoq belgisiz). `uz-Cyrl.overrides.json` ning `words` bo'limiga `filtr` oilasi qo'shildi va natija `Фильтрларни` bo'ldi — qolgan barcha yangi matn (`аъзоликлари`, `сессия`, `триггери`, `муваффақиятсиз`) transliterator tomonidan to'g'ri hosil qilindi.

## Task Commits

1. **Task 1: Foydalanuvchi boshqaruv ekrani (D-04, D-02, D-05, D-08)** — `1cf842b` (feat)
2. **Task 2: Audit jurnali ekrani (D-11, D-12)** — `bff3c94` (feat)

## Files Created/Modified

### Foydalanuvchi boshqaruvi

| Fayl                      | Mazmuni                                                                                              |
| ------------------------- | ---------------------------------------------------------------------------------------------------- |
| `users/page.tsx`          | `USER_VIEW` darvozasi (`errors.forbidden`), sarlavha, qo'shish tugmasi (`USER_MANAGE`), parol dialogi |
| `user-list.tsx`           | Karta ro'yxati, holat nishonlari, amallar menyusi (`USER_MANAGE`), tasdiq dialogi                     |
| `create-user-dialog.tsx`  | `react-hook-form` + `zod`; rollar **checkbox** to'plami; til tanlovi; `assignableRoles()`              |
| `temp-password-dialog.tsx`| Monospace parol, nusxa olish, ogohlantirish; yopilganda holat tozalanadi                               |

### Audit ko'rish

| Fayl                 | Mazmuni                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| `audit/page.tsx`     | `AUDIT_VIEW` darvozasi, `<Suspense>` chegarasi                                                  |
| `audit-filters.tsx`  | 5 filtr (sana oralig'i, amal, aktor, jadval) + tozalash; `useAuditFilters()` eksporti            |
| `audit-list.tsx`     | Karta ro'yxati, D-12 ning to'rt ustuni, manba nishoni, "ko'proq yuklash"                          |
| `audit-diff.tsx`     | `changed_keys` bo'yicha eski/yangi ustunlar; `insert`/`delete` uchun bir tomonlama                |

### Kutubxona va infratuzilma

- `lib/queries.ts` — 6 hook + `adminErrorMessageKey()`; barcha endpoint chaqiruvlari SHU faylda
- `lib/api-types.ts` — `MARKET_ADMIN_ASSIGNABLE_ROLES`, `assignableRoles()`, `LOCALE_LABELS`, `AUDIT_ACTIONS`, `AUDIT_TABLES`, `isAuditAction/isAuditTable` + 6 zod sxemasi va 4 yangi xato kodi
- `[locale]/layout.tsx` — `NuqsAdapter` (i18n dan keyin, kesh va sessiyadan oldin)
- `shell/locale-switcher.tsx` — endonim ro'yxati `LOCALE_LABELS` dan o'qiydi (nusxa olib tashlandi)
- `scripts/role-gate.test.mjs` (2 test), `scripts/audit-actions.test.mjs` (3 test)

## Decisions Made

- **Aktor ismi `GET /users` dan qo'shiladi.** `GET /audit` javobi `actor_label` ni beradi, lekin ism/telefonni ATAYIN bermaydi (01-07: audit javobiga profil maydonlarini qo'shish shaxsiy ma'lumot yuzasini kengaytiradi). Shuning uchun "kim" ustuni ikki manbadan quriladi: `actor_user_id` bo'yicha `GET /users` ro'yxatidan ism, topilmasa `actor_label`, u ham bo'lmasa `audit.systemActor`. `AUDIT_VIEW` bo'lgan uchala rolda `USER_VIEW` ham bor (01-06 matritsasi), ya'ni bu qo'shimcha so'rov hech qachon 403 bermaydi.

- **`actor_kind` yo'q — tizim aktori `actor_user_id === null` bilan aniqlanadi.** Reja `actor_kind='system'` ni tekshirishni ko'rsatgan, lekin `AuditEntry` sxemasida (01-07) bunday maydon YO'Q. Uni "bo'lishi kerak" deb taxmin qilish zod sxemasini chegarada yiqitardi. `actor_user_id` ning `null` bo'lishi aynan shu ma'noni beradi va u kontraktda mavjud.

- **Jadval filtri yopiq ro'yxat, erkin matn emas.** Erkin matn uchta narsani beradi: xato yozilgan nom (jimgina bo'sh natija), tarjima qilib bo'lmaydigan yorliq va serverga ma'nosiz so'rov. `AUDIT_TABLES` esa tarjima qilinadi va noto'g'ri qiymat kiritishning iloji yo'q. Ro'yxatda yo'q jadval (keyingi fazalarniki) ro'yxatda XOM nomi bilan ko'rinadi — bu to'g'ri xulq, chunki jadval nomi texnik identifikator.

- **Noma'lum `action` va `table_name` yashirilmaydi.** 01-08 da noma'lum ROL uchun qarama-qarshi qaror qabul qilingan edi (`roleLabelKey()` `null` qaytaradi va xom `market_admin` hech qachon ko'rinmaydi). Farqi shundaki: rol — YOPIQ to'plam va undagi noma'lum qiymat eskirgan token belgisi; audit `action` esa MA'LUMOT va u keyingi fazalarda kengayadi. Uni yashirish jurnalda tushunarsiz bo'shliq qoldirardi, ko'rsatish esa eng yomon holatda texnik identifikator beradi. Ikkala qaror ham kodda sababi bilan yozilgan.

- **`useWatch`, `watch()` emas.** `useForm()` qaytaradigan `watch` — oddiy funksiya va React Compiler uni memoizatsiya qila olmaydi; Next 16 eslint konfiguratsiyasi buni ogohlantirish bilan belgilaydi. `useWatch` obunani hook sifatida e'lon qiladi va ogohlantirish yo'qoladi.

- **`LOCALE_LABELS` `api-types.ts` da.** Endonim yorliqlari 01-08 qarori bo'yicha tarjima fayllarida emas. Yangi foydalanuvchi formasiga ham xuddi shu uch qator kerak edi; nusxa olish ikki ro'yxatning bir kun ajralib ketishini kafolatlardi. Yorliq — til KODINING xossasi, komponentniki emas, shuning uchun u `LOCALES` bilan yonma-yon turadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `nuqs` bu worktree'da o'rnatilmagan edi**

- **Found during:** Task 2 (`audit-filters.tsx` loyihalash)
- **Issue:** Reja filtrlarni `nuqs` orqali URL'ga sinxronlashni talab qiladi, lekin 01-08 uni `frontend/package.json` ga qo'shmagan.
- **Fix:** `npm install --save-exact nuqs@2.9.2` — CLAUDE.md stekida AYNAN shu versiya bilan oldindan tasdiqlangan (MIT; "URL-synced filter state"). Paket npm reyestrida mavjud, litsenziyasi va `peerDependencies.next: >=14.2.0` tekshirildi. `NuqsAdapter` ildiz layout'iga qo'shildi (`[locale]/layout.tsx` rejaning fayl ro'yxatida yo'q edi).
- **Verification:** `npm run build` muvaffaqiyatli, `/audit` uchala tilda prerender bo'ladi
- **Committed in:** `bff3c94`

**2. [Rule 3 - Blocking] `<Suspense>` chegarasi rejada ko'rsatilmagan, lekin usiz statik render yo'qolardi**

- **Found during:** Task 2
- **Issue:** URL qidiruv parametrini o'qiydigan klient komponenti eng yaqin `Suspense` chegarasigacha bo'lgan daraxtni klient tomonda render qilishga majbur qiladi (Next 16 hujjati). Chegarasiz `/audit` statik prerender ro'yxatidan butunlay chiqib ketardi.
- **Fix:** Filtr paneli va ro'yxat `<Suspense>` ichida, `common.loading` fallback bilan. Sababi sahifa docstringida.
- **Verification:** build chiqishida `/audit` uchala til bilan `●  (SSG)` bo'limida
- **Committed in:** `bff3c94`

**3. [Rule 1 - Bug] `watch()` React Compiler ogohlantirishini keltirib chiqardi**

- **Found during:** Task 1 (`npm run lint`)
- **Issue:** `react-hooks/incompatible-library` — `useForm().watch` memoizatsiya qilinmaydi va komponent butunlay optimizatsiyadan chiqariladi ("stale UI" xavfi).
- **Fix:** `useWatch({ control, name: "roles" })`.
- **Verification:** `npm run lint` chiqishi butunlay toza (0 xato, 0 ogohlantirish)
- **Committed in:** `1cf842b`

**4. [Rule 2 - Missing Critical] D-04 ko'zgusining backend bilan mosligini hech narsa tekshirmasdi**

- **Found during:** Task 1 yakuniy tekshiruvi
- **Issue:** Rejaning qabul mezoni "`MARKET_ADMIN_ASSIGNABLE_ROLES` aynan `['cashier','inspector']`" — bu BIR MARTALIK tekshiruv. Backend bir kun ro'yxatni o'zgartirsa (yoki teskarisi), hech bir test qizarmasdi: ikki to'plam ikki tilda, ikki fayl daraxtida.
- **Fix:** `frontend/scripts/role-gate.test.mjs` — ikkala faylning O'ZINI o'qiydi (01-07 dagi `test_locale_enum_matches_frontend_routing` naqshi, endi teskari yo'nalishda). Ikkinchi test `rbac.ts` dagi `ROLES` ni `sbozor_core.enums.Role` bilan solishtiradi (platforma admini beshalasini ko'rishining kafolati).
- **Verification:** **Sabotaj** — frontend ro'yxatiga `director` qo'shilganda 1 test yiqildi; qaytarilgandan keyin 2/2 yashil
- **Committed in:** `1cf842b`

**5. [Rule 2 - Missing Critical] `audit.actions.*` ro'yxatining TO'LIQLIGINI hech narsa tekshirmasdi**

- **Found during:** Task 2
- **Issue:** `i18n:check` faqat uchala faylning bir-biriga mosligini tekshiradi. Kalit uchala tilda ham yo'q bo'lsa (aynan backend yangi hodisa qo'shganda shunday bo'ladi), parity yashil qoladi va UI xom `refresh_reuse_detected` satrini ko'rsatardi.
- **Fix:** `frontend/scripts/audit-actions.test.mjs` — 3 test: `AUDIT_ACTIONS` ↔ `AuditAction` enum'i; har bir hodisa uchun uchala tilda kalit (va ortiqcha kalit ham xato); `AUDIT_TABLES` ↔ `audit.tables.*`.
- **Committed in:** `bff3c94`

**6. [Rule 2 - Missing Critical] Rejaning kalit ro'yxati ekranlarni to'liq qoplamasdi**

- **Found during:** Task 1 va Task 2
- **Issue:** 12 ta kalit rejada nomlanmagan, lekin ularsiz UI'da tarjimasiz matn yoki nomsiz boshqaruv qolardi: `users.rolesRequired` (validatsiya xatosi), `users.actions` (menyu `aria-label`), `users.confirm` (tasdiq tugmasi), `users.confirmUnblock` (blokdan chiqarish savoli — rejada faqat `confirmBlock` bor), `users.createHint` (dialog tavsifi), `common.close`, `audit.filterActionAll` / `filterActorAll` / `filterTableAll` (ro'yxatlarning "hammasi" varianti), `audit.sourceLabel`, `audit.noValues` (qiymatsiz yozuv), `audit.tables.*` (5 kalit).
- **Fix:** Barchasi uchala tilda qo'shildi (`uz-Cyrl` generatsiya bilan).
- **Verification:** `i18n:check` — 120 kalit × 3 til
- **Committed in:** `1cf842b`, `bff3c94`

**7. [Rule 1 - Bug] Kirill transliteratsiyasi `Filtrlarni` ni yumshoq belgisiz hosil qilardi**

- **Found during:** Task 2 (generatsiya natijasini ko'z bilan tekshirish)
- **Issue:** `Филтрларни` — o'zbek kirill imlosida `Фильтрларни`. Bu aynan `uz-Cyrl.overrides.json` mavjud bo'lish sababi.
- **Fix:** `words` bo'limiga `filtr` oilasi (`filtr`, `filtrlar`, `filtrlarni`, `filtrlash`) qo'shildi.
- **Verification:** `audit.clearFilters` = `Фильтрларни тозалаш`
- **Committed in:** `bff3c94`

**8. [Rule 3 - Blocking] Reja `hasPermission(roles,'USER_MANAGE')` deb yozgan, haqiqiy API kichik harfda**

- **Found during:** Task 1
- **Issue:** `lib/rbac.ts` dagi `Permission` tipi `'user_manage' | 'user_view' | 'audit_view' | ...` — katta harfli variant kompilyatsiya xatosi berardi.
- **Fix:** Mavjud API ishlatildi (`'user_manage'`, `'user_view'`, `'audit_view'`).
- **Committed in:** `1cf842b`, `bff3c94`

**9. [Rule 2 - Missing Critical] `LOCALE_LABELS` ikki joyda takrorlanardi**

- **Found during:** Task 1
- **Issue:** Yangi foydalanuvchi formasidagi til tanlovi til almashtirgichdagi bilan AYNAN bir xil uch endonimni talab qiladi. Nusxa olish ikkovining bir kun ajralib ketishini kafolatlardi (masalan biri `Ўзбекча`, ikkinchisi `Ўзбекчa`).
- **Fix:** `LOCALE_LABELS` `api-types.ts` da (`LOCALES` yonida); `locale-switcher.tsx` o'z nusxasini olib tashlab shundan o'qiydi (fayl rejaning ro'yxatida yo'q edi).
- **Committed in:** `1cf842b`

### Kichik moslashtirishlar (xato emas, tanlov)

- **`users.create` matni o'zgardi** — "Yangi foydalanuvchi" tugma emas, DIALOG sarlavhasi bo'lib qoldi (`users.createTitle`); tugma esa rejadagi "Foydalanuvchi qo'shish".
- **`audit.filterAction` matni** — "Harakat bo'yicha saralash" (saralash ≠ filtr) o'rniga "Amal turi".
- **`audit.resultCount` tugashi** — "topildi" o'rniga "ko'rsatilmoqda": kursor sahifalashda son YUKLANGAN yozuvlarni bildiradi, umumiy sonni emas.
- **`audit.what`, `audit.who`, `audit.oldValue`, `audit.newValue`** ustun sarlavhalari karta ko'rinishida `sr-only` sifatida beriladi — vizual ravishda ustun sarlavhasi kerak emas, skrinrider uchun esa D-12 ning to'rt ustuni nomlanган bo'lishi shart.
- **Aktor filtri `GET /users` dan** — ro'yxatda faqat joriy bozor a'zolari bo'ladi. `market_id IS NULL` yozuvlarining aktori bu ro'yxatda yo'q, lekin ular baribir ko'rinmaydi (quyidagi "Known Stubs").

---

**Total deviations:** 9 auto-fixed — 2× Rule 1 (React Compiler ogohlantirishi, kirill imlosi), 4× Rule 2 (ikki kontrakt testi, yetishmayotgan kalitlar, `LOCALE_LABELS`), 3× Rule 3 (`nuqs`, `Suspense`, permission nomlari).
**Impact on plan:** Scope creep yo'q. Ikkitasi (#4, #5) rejaning O'Z qabul mezonlarini bir martalik tekshiruvdan doimiy darvozaga aylantirdi; bittasi (#2) rejada ko'rinmagan Next 16 xulqini ochdi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Issues Encountered

1. **`docker compose --profile test run --rm tests pytest -q` BAJARILMADI.** Muhit yo'riqnomasi docker'ni aniq taqiqlaydi (parallel agent — 01-10 — DB holatini ushlab turibdi). Bu qadam xavfsiz o'tkazib yuborildi, chunki **bu reja birorta backend faylga tegmagan**: `git diff --name-only` ning barcha 20 qatori `frontend/` ostida. Backend to'plamining holati 01-07 dagidek qoladi (323 test yashil). To'liq zanjir wave birlashgandan keyin orkestratorda ishga tushiriladi.
2. **Rejaning `<human-check>` ro'yxati (15 qadam) bajarilmadi** — u FAZA OXIRIGA mo'ljallangan (`human_verify_mode: end-of-phase`) va jonli backend + `.env` talab qiladi. Ro'yxat quyida o'zgarishsiz keltirilgan; verifikator uni birlashtirishdan keyin bajaradi.
3. **`npm audit` — 12 high (transitiv).** 01-02/01-08 da hujjatlashtirilgan holat o'zgarmadi. `nuqs` yangi ogohlantirish qo'shmadi.
4. **Audit UI backendsiz to'liq ko'rinmaydi.** `next dev` bilan `/uz/audit` 200 qaytaradi, lekin `(app)` qatlami sessiyani tiklay olmagani uchun skelet holatida qoladi — ya'ni ro'yxat va filtrlar JONLI ko'rilmadi. Kontraktdan chetlanish bo'lsa u `api-types.ts` dagi `auditEntrySchema` da bitta joyda tuzatiladi.

## Known Stubs

| Stub | Fayl | Sabab / qachon yopiladi |
|------|------|--------------------------|
| `market_id IS NULL` audit yozuvlari (masalan `login_failed`) HAMON hech kimga ko'rinmaydi | `audit-list.tsx` (UI aybdor emas) | **01-06 dan meros qolgan OCHIQ bo'shliq**, 01-07 SUMMARY buni aniq qayd etgan va yopmagan: `GET /audit` tenant-scoped, `market_id IS NULL` qatorlarini o'qish yo'li backend'da YO'Q. UI shu sababli "kim tizimga kirishga urinmoqda" savoliga javob bera olmaydi. Alohida endpoint (`GET /api/v1/audit/platform`) yoki `require_roles(PLATFORM_ADMIN)` ostidagi bayroq talab qiladi — 8-fazaga yoki 01-10 rejalashtiruvchisiga. |
| Audit ro'yxatida `request_id` ko'rsatilmaydi | `audit-list.tsx` | D-12 minimal to'plam belgilaydi (kim/qachon/nima/eski-yangi) va "keyingi fazalarda boyitiladi" deydi. `request_id` sxemada bor va qo'shish bitta qator. |
| `users.createdBy` tarjima kaliti ishlatilmaydi | `messages/*.json` | 01-02 dan qolgan; o'chirish bu rejaning doirasidan tashqarida. Zararsiz — `i18n:check` faqat parity'ni tekshiradi. |
| `GET /users` sahifalanmaydi | `queries.ts` | Backend kontraktining holati (01-07). Karmana bozorida xodimlar o'nlab. Audit ro'yxatining kursor mexanizmi qayta ishlatilishi mumkin. |

Boshqa stub yo'q: har bir dialog, filtr, mutatsiya va ro'yxat to'liq ishlaydi va e'lon qilingan kontraktga ulangan. Soxta raqam yoki namunaviy ma'lumot hech qayerda yo'q.

## Threat Model Coverage

| Threat ID | Holat | Dalil |
|-----------|-------|-------|
| T-01-68 (vaqtinchalik parolning saqlanib qolishi) | **Yopildi** | Parol `useMutation` javobida (kesh YO'Q) va bitta `useState` da; dialog yopilganda `null`. `grep -rn "console.log\|localStorage\|sessionStorage" frontend/src/` → bo'sh (izohda ham yo'q). URL'ga hech qachon qo'yilmaydi. Bufer — foydalanuvchining aniq harakati. |
| T-01-69 (audit `new_value` da sezgir qiymat) | **Yopildi** | `audit-diff.tsx` javobdagi qiymatni O'ZGARTIRMASDAN ko'rsatadi; maskalash backend'da (`mask_sensitive()`); UI qo'shimcha maydon so'ramaydi va `old_value`/`new_value` dan boshqa manba ishlatmaydi. |
| T-01-70 (kassir/nazoratchi audit sahifasini ochishi) | **Yopildi** | Uch qatlam: `AppShell` navigatsiyasi `audit_view` bo'yicha filtrlanadi (01-08); `audit/page.tsx` huquqni SO'ROVDAN OLDIN tekshiradi va `errors.forbidden` ko'rsatadi (ya'ni `GET /audit` ham ketmaydi); hal qiluvchi qatlam — backend `require_permission(AUDIT_VIEW)` → 403 (01-07 da `test_cashier_cannot_view_the_audit_log` bilan qulflangan). |
| T-01-71 (cross-tenant foydalanuvchiga amal) | **Yopildi** | Backend 404 qaytaradi; `adminErrorMessageKey()` uni `errors.notFound` ga xaritalaydi va mavjudlikni TASDIQLAMAYDI. UI ID'larni faqat `GET /users` ro'yxatidan oladi. |
| T-01-72 (audit yozuvini UI orqali tahrirlash) | **Yopildi** | `grep -rnE 'method:\s*"(POST\|PUT\|PATCH\|DELETE)"\|mutate\|useMutation' frontend/src/components/audit/` → **bo'sh**. Audit komponentlarida faqat o'qish bor. DB darajasidagi 4 qatlamli himoya (01-05) `human-check` 13-qadamida ko'rsatib isbotlanadi. |
| T-01-73 (juda katta audit sahifasi so'rash) | **Yopildi** | `AUDIT_PAGE_SIZE = 50` har so'rovda `limit` bo'lib ketadi (backend chegarasi 200); keyingi sahifa `next_cursor` bilan, sahifa raqami YO'Q. |
| T-01-74 (audit JSONB qiymatining HTML sifatida render qilinishi) | **Yopildi** | `grep -rn "dangerouslySetInnerHTML" frontend/src/` → **bo'sh**. `audit-diff.tsx` qiymatni `formatValue()` bilan satrga o'girib React matn tuguni sifatida chiqaradi. |

**Yangi threat flag: yo'q.** Yagona yangi brauzer yuzasi — `navigator.clipboard.writeText()` (vaqtinchalik parolni nusxa olish). U T-01-68 ning mavjud dispozitsiyasi ichida qoladi: yozuv foydalanuvchining ANIQ harakati bilan sodir bo'ladi, brauzerdan tashqariga chiqmaydi va rad javobi oqimni to'xtatmaydi (parol baribir ekranda). Ikkinchi kengayish — filtr qiymatlarining URL'ga chiqishi; ular sezgir emas (sana, UUID, hodisa nomi) va serverda `AuditQuery` bilan tekshiriladi, natija esa `audit_read` RLS policy'si bilan o'z bozoriga cheklangan (T-01-54).

## Faza oxiridagi uchidan-uchiga tekshiruv (bajarilmagan — verifikator uchun)

Reja `<human-check>` bloki 15 qadamdan iborat va **faza oxirida, wave birlashgandan keyin** bajariladi (`human_verify_mode: end-of-phase`). Talab qilinadi: `.env`, `npm run up`, `npm run migrate`, so'ng `docker compose --profile web --profile proxy up -d`.

- **Mezon #1 (rol va bozor izolyatsiyasi)** — 4 qadam: bozor admini formasida FAQAT kassir/nazoratchi; kassirda `Foydalanuvchilar`/`Audit` havolalari yo'q va `/uz/users` `errors.forbidden` beradi; direktorda yaratish/bloklash tugmalari yo'q; cross-tenant `block` → **404**.
- **Mezon #2 (til bir bosishda)** — 2 qadam: uchala til, butun ekran tarjimada, `MISSING_MESSAGE` yo'q; F5 dan keyin til saqlanadi.
- **Mezon #3 (audit jurnali — asosiy isbot)** — 7 qadam: yaratish/bloklash/parol tiklash yozuvlari; parol jurnalda YO'Q; `action` va sana filtrlari; `Audit` sahifasini yangilash `read` yozuvi hosil qiladi; `UPDATE audit_log` → `UPDATE 0`, `TRUNCATE` → `append-only` xatosi.
- **Mezon #4 (biznes-kun)** — 1 qadam: `business_date` Toshkent sanasi bo'yicha.
- **Mezon #5 (moliyaviy konstraytlar)** — 1 qadam: `pytest tests/integration/test_idempotency.py test_money_constraints.py test_business_date.py`.

Ushbu rejada bajarilgan qism: `next dev` bilan `/uz/audit`, `/uz-cyrl/audit`, `/ru/audit`, `/uz/users` — 200 va `MISSING_MESSAGE` 0 ta (backendsiz, ya'ni faqat marshrutlash va qobiq darajasida).

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi.

Frontend darvozalari (toza `npm --prefix frontend ci` dan keyin):

```
npm --prefix frontend run i18n:gen
npm --prefix frontend run i18n:check
npm --prefix frontend run typecheck
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
```

Uchidan-uchiga tekshiruv uchun (wave birlashgandan keyin):

```
cp .env.example .env
npm run up && npm run migrate
npm --prefix frontend run dev
```

## Next Phase Readiness

**Tayyor:**

- **01-10 (cross-tenant matritsa):** UI endi `users` va `audit` endpointlarining har birini chaqiradi; 404/403 javoblari `adminErrorMessageKey()` orqali tarjima kalitiga tushadi va mavjudlikni tasdiqlamaydi.
- **2-faza (bozor ustasi):** dialog + `react-hook-form` + `zod` naqshi ikki formada takrorlandi; `nuqs` va `NuqsAdapter` wizard qadamlarini URL'ga bog'lash uchun tayyor.
- **5/6-fazalar (hisobot va kassir):** `useInfiniteQuery` + keyset naqshi, URL filtr holati va `useFormatter` bilan sana ko'rsatish shu yerda o'rnatildi — hisobot ekranlari ularni takrorlaydi.

**Ochiq e'tibor nuqtalari:**

- **`market_id IS NULL` yozuvlari HAMON ko'rinmaydi** (yuqoridagi "Known Stubs"). Bu 01-06 → 01-07 → 01-09 zanjirida UCHINCHI marta qayd etilmoqda va hech bir reja uni o'z doirasiga olmadi. Rejalashtiruvchi e'tiboriga: bu backend ishi va u UI'da bir qator o'zgarish bilan yopiladi.
- **`rbac.ts` hamon backend matritsasining QO'LDA nusxasi.** 01-08 buni "01-09 da ko'rib chiqilsin" deb qoldirgan edi. Bu rejada YECHILMADI, lekin qisman qoplandi: `role-gate.test.mjs` endi ROLLAR ro'yxatini enum bilan bog'laydi. Qolgani — rol → huquq XARITASI — hamon bog'lanmagan; uzoq muddatda `GET /auth/me` javobidagi `permissions` ro'yxatidan foydalanish arzonroq.
- **Brauzer testlari hamon yo'q.** Rol bo'yicha ko'rinish (kassir menyusi, direktorning tugmalari), dialog oqimi va bir martalik parol xulqi faqat qo'lda tekshiriladi. VALIDATION.md bo'yicha bu 8-fazaga qoldirilgan; regressiyaga eng ochiq joy — `create-user-dialog` dagi D-04 ro'yxati (uning KONSTANTASI test bilan qoplangan, RENDER'i esa yo'q).
- **`nuqs` — 1-fazada qo'shilgan yagona yangi bog'liqlik.** MIT, CLAUDE.md stekida tasdiqlangan, `frontend/package.json` va `package-lock.json` mos ravishda yangilandi.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 20 ta artefaktning (11 yangi + 9 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda (`git diff --name-only 111e225..HEAD` aynan 20 qator).
- **Commitlar:** `1cf842b`, `bff3c94` — ikkalasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only` har ikkala commit uchun bo'sh.
- **Umumiy artefaktlarga tegilmadi:** o'zgargan 20 faylning HAMMASI `frontend/` ostida — `.planning/STATE.md`, `.planning/ROADMAP.md`, `tests/`, `.github/`, ildiz `package.json`, `services/`, `migrations/`, `packages/` diffda YO'Q (worktree rejimi; qo'shni agent domeni butunlay tegilmagan).
- **Darvozalar:** `i18n:gen --check` (drift yo'q) · `i18n:check` (120 kalit × 3 til, ICU parity) · `typecheck` exit 0 · `lint` exit 0 (0 xato, 0 ogohlantirish) · `test` 37/37 · `build` exit 0 (24 sahifa SSG).
- **Sabotaj tekshiruvi:** `MARKET_ADMIN_ASSIGNABLE_ROLES` ga `director` qo'shilganda `role-gate.test.mjs` yiqildi (1/2); o'zgarish qaytarilgandan keyin 2/2 yashil.
- **Grep darvozalari:** `console.log|localStorage|sessionStorage|<table|type="radio"` `components/users/` da → **0** · `<table|dangerouslySetInnerHTML|toLocaleString|toLocaleDateString` butun `src/` da → **0** · yozuv amallari `components/audit/` da → **0** · `MARKET_ADMIN_ASSIGNABLE_ROLES` va `assignableRoles` `api-types.ts` da → bor, `create-user-dialog.tsx` da qattiq yozilgan rol nomi → **0** · `useFormatter` ikkala ro'yxatda → bor.
- **Jonli tekshiruv (`next dev`, backendsiz):** `/uz/audit`, `/uz-cyrl/audit`, `/ru/audit`, `/uz/users` → 200; `?action=login&from=2026-07-01` → 200; `MISSING_MESSAGE` va `IntlError` → **0**; dev server jurnalida xato yo'q.
- **Backend to'plami ishga tushirilmadi** (muhit taqiqi) — lekin bu reja birorta backend fayliga tegmagani `git diff` bilan isbotlangan.

---

_Phase: 01-poydevor-va-tenant-xavfsizligi_
_Completed: 2026-07-29_
