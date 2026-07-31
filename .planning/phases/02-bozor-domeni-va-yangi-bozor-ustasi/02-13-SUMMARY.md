---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 13
subsystem: ui
tags: [zod, tanstack-query, i18n, navigation, error-mapping, contract, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-08 — `app/schemas.py` ning butun DTO to'plami va `MARKET_ERROR_CODES`; 02-09 — tarif/kalendar marshrutlari va `min_valid_from` qiymati; 02-10 — sotuvchi/biriktirish marshrutlari va `invalid_period`; 02-11 — usta marshrutlari, `BlockingItem.code` va `market_is_active`; 02-12 — import marshrutlari, `ImportIssue.code` va `import_conflict`; 02-02 — yetti `ui/` primitivi (`dialog.sheetOnMobile`), WCAG AA tokenlari, transliteratsiya darvozasi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`api-client.ts` (`apiFetch`, `ApiError`, `errorMessageKey`), `queries.ts` naqshi, `rbac.ts` matritsasi, `global.ts` kalit xavfsizligi, `gen-cyrillic.mjs` + `check-messages.mjs`"
provides:
  - "`frontend/src/lib/api-types.ts` — 2-fazaning BUTUN javob shakli zod sxemalarida (42 sxema); `ERROR_CODES` 12 -> 35"
  - "`frontend/src/lib/market-queries.ts` — 35 hook + 4 funksiya, yagona so'rov qatlami va invalidatsiya grafi"
  - "`frontend/src/lib/market-errors.ts` — 23 backend kodi -> tarjima kaliti"
  - "`frontend/src/lib/auth-queries.ts` — `select-market` va `logout` komponentdan tashqarida"
  - "`frontend/src/lib/api-client.ts::apiRequest()` — xom javob, `FormData`, `ApiError.body`"
  - "`frontend/messages/*` — to'qqizta yangi namespace, 295 kalit x 3 til"
  - "`frontend/src/components/shell/app-shell.tsx` — 8 bo'lim, desktop 3 guruh, mobil 4 + Ko'proq"
  - "`frontend/src/components/shell/nav-more-sheet.tsx`"
  - "`frontend/scripts/error-codes.test.mjs` — backend kodlari -> ko'zgu -> tarjima darvozasi"
  - "`frontend/src/lib/market-queries.test.tsx` — invalidatsiya grafining o'lchov darvozasi"
affects: [02-14, 02-15, 02-16, 02-17, kassir-moduli, hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Domen so'rovlari `market-queries.ts` da, auth bootstrap `auth-queries.ts` da — komponent HTTP qatlamiga tegmaydi"
    - "Yon ta'sirlar nomlangan konstantada (`STALL_SIDE_EFFECTS`) — har `onSuccess` da qo'lda sanash «bittasini unutish» xatosini kafolatlardi"
    - "`apiRequest()` xom javob qaytaradi; `apiFetch()` uning ustidagi tiplangan qobiq — token/refresh mantiqi ikkinchi marta yozilmaydi"
    - "`ApiError.body` — javob tanasi bir marta o'qiladi va to'liq saqlanadi (import 422 sining `errors[]` i yo'qolmasin)"
    - "MA'LUMOTDAN keladigan i18n kalitlari (`wizard.blocking.*`, `import.errors.*`) backend ro'yxati bilan test orqali qulflanadi"
    - "Mexanik grep darvozasi bilan to'qnashadigan atama izohda ham yozilmaydi (02-08 dan meros)"

key-files:
  created:
    - frontend/src/lib/market-queries.ts
    - frontend/src/lib/market-errors.ts
    - frontend/src/lib/auth-queries.ts
    - frontend/src/lib/market-queries.test.tsx
    - frontend/src/components/shell/nav-more-sheet.tsx
    - frontend/scripts/error-codes.test.mjs
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/api-client.ts
    - frontend/src/components/shell/app-shell.tsx
    - frontend/src/components/shell/user-menu.tsx
    - frontend/src/components/auth/market-picker.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "`ERROR_CODES` 20 emas, 23 kodga kengaydi — backend ro'yxati reja yozilgandan keyin uchta kod qo'shgan"
  - "`setupStatusSchema` (tor) O'RNINI `setupStatusResponseSchema` (to'liq) egalladi — bitta endpoint uchun ikki shakl saqlanmadi"
  - "Yon ta'sirlar nomlangan konstantada, `onSuccess` ichida qo'lda sanalmaydi"
  - "Rasta mutatsiyalari `zones`/`categories` ni ham bekor qiladi — `stall_count` ularda yashaydi"
  - "`market-picker.tsx` va `user-menu.tsx` so'rov modullariga ko'chirildi; 1-fazaning qolgan uch auth komponenti ATAYIN tegilmadi"
  - "`import.insertedCount` matni «rasta» emas, neytral «yozuv» — bitta kalit ikki importga xizmat qiladi"
  - "`import.errors.*` matnlari ARGUMENTSIZ — komponent ularni faqat `code` dan quradi"

patterns-established:
  - "Pattern: uch bo'g'inli zanjir (backend kodi -> frontend ko'zgusi -> tarjima kaliti) BITTA test faylida qulflanadi"
  - "Pattern: invalidatsiya grafi renderlanган hook ustida o'lchanadi, grep bilan emas"
  - "Pattern: kuzatilmagan (untracked) fayl ustida sabotaj qilishdan oldin zaxira olinadi — `git checkout` uni tiklay olmaydi"

requirements-completed: []

# Metrics
duration: 95min
completed: 2026-08-01
---

# Phase 2 Plan 13: Kontrakt qatlami — zod, so'rovlar, xato xaritasi va matnlar Summary

**Uchta UI rejasining umumiy poydevori bir vaqtda qo'yildi: 42 zod sxemasi javob shaklini chegarada qulfladi, 35 hook har endpointni bitta joyga yig'di, 23 backend xato kodi uch tilli matnga aylandi va to'qqizta namespace 295 kalitga chiqdi — ustiga backend↔frontend↔tarjima zanjirining uchta yangi darvozasi qo'yilib, har biri sabotaj bilan o'lchandi.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3/3
- **Fayllar:** 14 (6 yaratildi, 8 o'zgartirildi), +3029 / −127
- **Testlar:** node 48 → **54**, vitest 7 → **18** (jami **72**)
- **i18n kalitlari:** 122 → **295** (x3 til)

## Accomplishments

- **Backend kod bazasi haqiqat manbai sifatida ishlatildi va reja bilan uch joyda ajralib ketgani topildi.** `MARKET_ERROR_CODES` reja yozilganda 20 ta edi; bugungi holati **23** (`invalid_period` 02-10 dan, `market_is_active` 02-11 dan, `import_conflict` 02-12 dan). Uchalasi ham ko'zguga va xato xaritasiga qo'shildi — aks holda ular jimgina `errors.generic` ga tushib, foydalanuvchi «Kutilmagan xato yuz berdi» dan boshqa hech nima ko'rmasdi.

- **Uchta yangi darvoza qo'yildi va HAR BIRI sabotaj bilan o'lchandi. To'rt sabotajning hech birida ortiqcha test yiqilmadi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | `MAP_KEY` `STALL_SIDE_EFFECTS` dan olib tashlandi | AYNAN 2: `useCreateStall …xarita…`, `useSetStallCategory …xarita…` | qolgan 16 test ✅ — jumladan **import yo'li yashil qoldi**, ya'ni uning o'z kalit ro'yxati rasta konstantasiga bog'lanib qolmagan |
  | `import_conflict` `ERROR_CODES` dan olib tashlandi | AYNAN 1: `ERROR_CODES … to'liq qamraydi` | `xaritalangan` va `UCHALA tilda` testlari ✅ — uch da'vo haqiqatan MUSTAQIL |
  | `case "invalid_period"` `market-errors.ts` dan olib tashlandi | AYNAN 1: `har bir backend kodi … xaritalangan` | qolgan 51 ✅ |
  | `wizard.blocking.calendar_missing` + `import.errors.row_too_short` `uz-Latn.json` dan olib tashlandi | AYNAN 2: blocking va import 1:1 darvozalari | qolgan 52 ✅; `i18n:check` ham MUSTAQIL ravishda qizardi |

- **Invalidatsiya grafi grep bilan emas, HAQIQATAN o'lchandi.** `market-queries.test.tsx` hook'ni `QueryClient` bilan render qiladi, `invalidateQueries` ni josuslaydi va bekor qilingan kalit ILDIZLARINI yig'adi. Bu sinf nosozligi (rasta yozildi, xarita eskirdi) typecheck, lint va build'dan bemalol o'tadi — uni faqat o'lchash bilan ushlash mumkin.

- **Reja ko'rmagan ikkita yon ta'sir topildi va yopildi:** rasta yaratish `ZoneItem.stall_count` va `CategoryItem.stall_count` ni eskirtiradi (usiz «bu zonani o'chira olamanmi?» tugmasi yolg'on holatda qolardi), tarif yozish esa `CategoryItem.current_tariff_soum` ni (usiz «tarif kiritilmagan» ogohlantirishi narx qo'shilgandan keyin ham turaverardi).

- **Import 422 sining `errors[]` massivi yo'qolib ketishi oldi olindi.** Mavjud `apiFetch` javob tanasini `detail` uchun bir marta o'qib, qolganini tashlab yuborardi — ya'ni «qaysi QATOR noto'g'ri» degan javob chegaradan o'tmasdi. `ApiError.body` qo'shildi va shakl chaqiruvchida `importErrorResponseSchema` bilan tahlil qilinadi.

- **Rejaning ikkita ichki ziddiyati 02-08 naqshi bilan hal qilindi** (grep darvozasi vs izoh talabi; qabul mezoni vs UI-SPEC kontrakti) — ikkalasida ham TAQIQ saqlandi, sabab to'liq yozildi, atama esa literal ko'chirilmadi.

## Task Commits

1. **Task 1: Zod kontraktlari va xato-kod xaritasi** — `41f0734` (feat)
2. **Task 2: TanStack Query hooklari va navigatsiya kengaytmasi** — `ccd369f` (feat)
3. **Task 3: To'qqizta namespace uchun uch tilli matnlar** — `a3f6a13` (feat)

## Files Created/Modified

**Yaratildi**

- `frontend/src/lib/market-queries.ts` (942 qator) — yo'l konstantalari, kalit fabrikalari, 35 hook, 4 funksiya. Yon ta'sirlar uchta nomlangan konstantada (`STALL_SIDE_EFFECTS`, `TARIFF_SIDE_EFFECTS`, `ASSIGNMENT_SIDE_EFFECTS`).
- `frontend/src/lib/market-errors.ts` — 23 `case` + `default` -> mavjud `errorMessageKey`.
- `frontend/src/lib/auth-queries.ts` — `useSelectMarket`, `useLogout`.
- `frontend/src/lib/market-queries.test.tsx` — 11 vitest (9 ijobiy + 2 nazorat).
- `frontend/src/components/shell/nav-more-sheet.tsx` — `ui/dialog.tsx` ning `sheetOnMobile` varianti ustida, yangi bog'liqliksiz.
- `frontend/scripts/error-codes.test.mjs` — 6 node-test.

**O'zgartirildi**

- `frontend/src/lib/api-types.ts` — 25 yangi sxema (jami 42), `STALL_STATUSES` + `isStallStatus`, `ERROR_CODES` 12 -> 35. `setupStatusSchema` (tor) o'rnini `setupStatusResponseSchema` egalladi.
- `frontend/src/lib/api-client.ts` — `apiRequest()` ajratildi, `FormData` yo'li, `ApiError.body`. `apiFetch()` imzosi O'ZGARMADI.
- `frontend/src/components/shell/app-shell.tsx` — 3 bo'lim -> 8; `NAV_GROUPS`, `MOBILE_PRIMARY_COUNT = 4`, bo'sh guruh sarlavhasiz tushib qoladi.
- `frontend/src/components/{shell/user-menu,auth/market-picker}.tsx` — so'rov modullariga ko'chirildi.
- `frontend/messages/*` — 9 namespace, 295 kalit; `uz-Cyrl.json` faqat `i18n:gen` bilan.

## Decisions Made

- **`ERROR_CODES` 20 emas, 23 taga oshdi.** Reja «aynan 20» deydi, backend esa 23 kod e'lon qiladi (docstringi ham «yigirma uchta» deb yozadi). Ko'zguni rejaga moslash ikkita HAQIQIY xato kodini (`invalid_period`, `import_conflict`) tashlab ketardi. Kod haqiqat manbai sifatida ustun turdi.
- **`setupStatusSchema` saqlanmadi.** 02-03 ataylab tor sxema yozgan edi («02-11 gacha endpoint yo'q, kengayishga chidamli bo'lsin»). Endpoint endi bor va shakli qotgan; ikki nomni saqlash bitta endpoint uchun ikki kontrakt yaratardi. Chaqiruvchining `try/catch` fail-safe xulqi o'zgarmadi — sxema qattiqroq bo'lgani uchun ham u 1-qadamga tushadi.
- **Yon ta'sirlar nomlangan konstantada.** Qabul mezoni `useCreateStall` ning `onSuccess` ida uchta kalitni KO'RISHNI kutadi; konstanta grep'da ko'rinmaydi. Lekin har `onSuccess` da ro'yxatni qo'lda takrorlash aynan «bittasini unutish» xatosini kafolatlardi — bu esa mezonning MAQSADI. Shuning uchun bog'lanish konstantada saqlandi va uning O'RNIGA renderlanган hook ustida o'lchandi (yuqoridagi sabotaj).
- **Desktop yon panelda ikkita guruh SARLAVHASI, uchta guruh.** Qabul mezoni «uch guruh sarlavhasi» deydi, UI-SPEC §12.3 esa birinchi guruhni aniq `*(guruhsiz)*` deb belgilaydi (Boshqaruv paneli yolg'iz turadi). Spetsifikatsiya ustun turdi: yolg'iz elementga sarlavha qo'yish yassi ro'yxatga qaraganda ko'proq shovqin qo'shardi.
- **`import.insertedCount` matni neytral.** UI-SPEC «{count} ta rasta qo'shildi» beradi, lekin AYNI kalit sotuvchi importida ham ishlatiladi — u yerda «rasta» yolg'on bo'lardi. «Yozuv/запись» ikkala oqimda ham to'g'ri.
- **`import.errors.*` matnlari ICU argumentsiz.** Ular `t('import.errors.' + code)` shaklida quriladi, ya'ni chaqiruvchida `{name}`/`{code}` qiymatlari yo'q. Aniq nom serverning `message` maydonida keladi va u xatolar hisoboti (`xlsx`) ga tushadi — bu ajratish `importErrorItemSchema` docstringida yozilgan.
- **`Ellipsis` ikonkasi, `MoreHorizontal` emas** — oxirgisi lucide-react 1.27 da faqat taxallus (alias re-export), kanonik nom `Ellipsis`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Backend xato kodlari rejadagidan uchta ko'p edi**

- **Found during:** Task 1
- **Issue:** Reja «yigirma yangi kod» deydi va qabul mezoni `ERROR_CODES` uzunligi «aynan 20 taga oshgan» bo'lishini talab qiladi. `schemas.py::MARKET_ERROR_CODES` da esa **23** kod bor: reja yozilgandan keyin 02-10 `invalid_period`, 02-11 `market_is_active`, 02-12 `import_conflict` qo'shgan. Ikkitasi (`invalid_period`, `import_conflict`) reja `market-errors.ts` uchun bergan xaritada ham yo'q.
- **Fix:** Uchalasi ham `ERROR_CODES` ga, ikkitasi `marketErrorMessageKey` ga qo'shildi (`vendors.invalidPeriod`, `import.conflict`) va ularga uch tilli matn yozildi. Yangi `error-codes.test.mjs` backend ro'yxatini O'QIB solishtiradi, ya'ni bu drift boshqa qaytmaydi.
- **Files modified:** `frontend/src/lib/api-types.ts`, `frontend/src/lib/market-errors.ts`, `frontend/messages/*`, `frontend/scripts/error-codes.test.mjs`
- **Verification:** `ERROR_CODES` 12 -> **35**; `market-errors.ts` da **23** `case`; sabotaj bilan darvoza tasdiqlandi
- **Committed in:** `41f0734`, `a3f6a13`

**2. [Rule 3 - Blocking] `apiFetch` ikkilik javobni ham, `FormData` ni ham qo'llab-quvvatlamasdi**

- **Found during:** Task 2
- **Issue:** Reja `useImportMutation` (`FormData`), `downloadTemplate` va `downloadErrorReport` (`.xlsx` bayt oqimi) ni talab qiladi. Mavjud `apiFetch` har doim `JSON.stringify` qiladi, `Content-Type: application/json` qo'yadi va javobni `schema.parse()` dan o'tkazadi — uchala talab ham bajarilmasdi. Ikkinchi, mustaqil `fetch` yozish esa token, single-flight refresh va cookie siyosatini IKKINCHI marta takrorlardi.
- **Fix:** `apiRequest()` ajratildi (xom `Response` qaytaradi, autentifikatsiya va 401-refresh mantiqi o'zgarmagan holda saqlanadi); `apiFetch()` uning ustidagi ingichka qobiqqa aylandi va IMZOSI O'ZGARMADI. `FormData` uchun `Content-Type` qo'yilmaydi (brauzer `boundary` ni o'zi qo'shadi).
- **Files modified:** `frontend/src/lib/api-client.ts`
- **Verification:** `FormData yuborilganda tana JSON ga aylantirilmaydi` testi; mavjud 7 ta market-picker testi o'zgarmasdan yashil qoldi
- **Committed in:** `ccd369f`

**3. [Rule 2 - Missing Critical] Import 422 sining `errors[]` massivi chegarada YO'QOLARDI**

- **Found during:** Task 2
- **Issue:** `ApiError` faqat `detail` satrini saqlaydi. Import 422 si esa `detail` bilan BIRGA `errors[]` va `error_counts` qaytaradi (D-14) va aynan o'sha ro'yxat foydalanuvchiga qaysi qator noto'g'ri ekanini aytadi. Javob tanasi bir marta o'qilgani uchun chaqiruvchi uni boshqa ololmasdi — ya'ni import ekranida xatolar ro'yxatini ko'rsatish IMKONSIZ bo'lardi.
- **Fix:** `ApiError.body` (`unknown`) qo'shildi va xato tanasi to'liq saqlanadi; `market-queries.ts::importErrorsOf(error)` uni `importErrorResponseSchema` bilan tahlil qiladi. Tip ataylab `unknown` — shakl chaqiruvchida, kutilgan sxema bilan ochiladi.
- **Files modified:** `frontend/src/lib/api-client.ts`, `frontend/src/lib/market-queries.ts`
- **Committed in:** `ccd369f`

**4. [Rule 1 - Bug] Rasta va tarif mutatsiyalari eskirgan SANOQLARNI qoldirardi**

- **Found during:** Task 2
- **Issue:** Reja rasta uchun `stalls`+`map`+`setup-status`, tarif uchun `tariffs`+`categories`+`setup-status` ni sanaydi. Lekin `ZoneItem.stall_count` va `CategoryItem.stall_count` ham rasta yozilganda o'zgaradi. Eskirgan sanoq «bu zonani o'chira olamanmi?» savoliga YOLG'ON javob berardi: UI o'chirish tugmasini ochiq qoldirardi, server esa 409 `zone_in_use` bilan rad etardi. Xuddi shunday, zona/toifa NOMI tahrirlanganda `zone_name`/`category_name` rasta ro'yxatida va xaritada eskirardi.
- **Fix:** `STALL_SIDE_EFFECTS` ga `ZONES_KEY` va `CATEGORIES_KEY` qo'shildi; nom tahriri esa o'z ro'yxatlariga `STALLS_KEY`/`MAP_KEY`/`TARIFFS_KEY` ni qo'shdi.
- **Files modified:** `frontend/src/lib/market-queries.ts`
- **Verification:** `useCreateStall zona va toifa SANOQLARINI ham bekor qiladi` testi
- **Committed in:** `ccd369f`

**5. [Rule 3 - Blocking] Navigatsiya kalitlari Task 3 da rejalashtirilgan, lekin Task 2 da KERAK edi**

- **Found during:** Task 2
- **Issue:** Reja `nav` namespace'ini Task 3 ga qo'yadi, `app-shell.tsx` ni esa Task 2 ga. Lekin `src/global.ts` `uz-Latn.json` ni `AppConfig.Messages` ga bog'laydi, ya'ni mavjud bo'lmagan kalit **kompilyatsiya vaqtida** xato beradi. Task 2 commit'i o'z-o'zicha QIZIL bo'lardi.
- **Fix:** `nav` ning sakkiz yangi kaliti (`map`, `stalls`, `vendors`, `tariffs`, `calendar`, `more`, `groupMarket`, `groupSystem`) Task 2 ga ko'chirildi; qolgan to'qqiz namespace Task 3 da qoldi. Rejaning yakuniy holati o'zgarmadi.
- **Files modified:** `frontend/messages/*`
- **Committed in:** `ccd369f`

**6. [Rule 1 - Bug] Rejaning ikkita bandi bir-biriga ZID edi**

- **Found during:** Task 1 va Task 2
- **Issue:** (a) Task 1 action «xarita katagining rang tipi bu yerda e'lon qilinmasligini IZOHDA ayt» deydi, qabul mezoni esa o'sha tipning nomini `api-types.ts` da grep qilib **0** talab qiladi — ikkalasini bir vaqtda bajarib bo'lmaydi. (b) Task 2 qabul mezoni «uch guruh SARLAVHASI» deydi, UI-SPEC §12.3 esa birinchi guruhni aniq `*(guruhsiz)*` deb belgilaydi.
- **Fix:** (a) 02-08 da o'rnatilgan qoida qo'llanildi: taqiq va uning to'liq sababi saqlandi, atamaning O'ZI literal yozilmadi, ustiga «bu qoida grep bilan qulflangan» ogohlantirishi qo'shildi — keyingi ishlovchi so'zni izohga qaytarib qo'ymaydi. (b) UI-SPEC ustun turdi: uch GURUH bor, ikkitasi sarlavhali.
- **Verification:** `grep -c StallTone api-types.ts` -> **0**; yon panelda `Bozor` va `Tizim` sarlavhalari
- **Committed in:** `41f0734`, `ccd369f`

**7. [Rule 2 - Missing Critical] `EmptyState` majburiy `description` talab qiladi, reja esa faqat sarlavha kaliti bergan**

- **Found during:** Task 3
- **Issue:** Reja har namespace uchun `emptyState` (bitta kalit) sanaydi. 02-02 dagi `EmptyState` primitivi esa `description` ni MAJBURIY qiladi (UI-SPEC §9.2 kontrakti) va UI-SPEC §10.4 to'qqizta bo'sh holatni sarlavha + tavsif JUFTLIGI sifatida beradi. Faqat sarlavha yozilsa, 02-14/02-15 tavsifni komponent ichida inline yozishga majbur bo'lardi — ya'ni matn i18n katalogidan chiqib ketardi.
- **Fix:** Har bir bo'sh holatga `emptyStateHint` (va filtr holati bor joylarda `emptyFiltered` + `emptyFilteredHint`) qo'shildi — 02-02 da `users.emptyStateHint` uchun o'rnatilgan konvensiyaning aynan takrori.
- **Files modified:** `frontend/messages/*`
- **Committed in:** `a3f6a13`

**8. [Rule 2 - Missing Critical] MA'LUMOTDAN keladigan kalitlar uchun darvoza yo'q edi**

- **Found during:** Task 3
- **Issue:** Qabul mezoni `wizard.blocking.*` va `import.errors.*` ning backend kodlari bilan «bir-birga mos» bo'lishini talab qiladi. Bu kalitlar KOD ichida yozilmaydi (`t('import.errors.' + code)`), ya'ni noto'g'ri nom hech qayerda ko'rinmaydi — ekranda tarjimasiz `duplicate_phone_in_file` paydo bo'lguncha. `i18n:check` bu sinfni umuman ushlamaydi (u parity'ni tekshiradi, TO'LIQLIKNI emas). Bir martalik o'lchov 3-fazada yangi kod qo'shilganda eskirardi.
- **Fix:** `error-codes.test.mjs` ga ikkita test qo'shildi — `markets.py` dagi `code="..."` va `import_validator.py` dagi `ImportIssue(...)` kodlari o'qilib, uchala tildagi kalit to'plami bilan `deepEqual` qilinadi. Naqsh 01-fazadagi `audit-actions.test.mjs` dan olindi (bir xil sinf: kalit ma'lumotdan keladi).
- **Files modified:** `frontend/scripts/error-codes.test.mjs`
- **Verification:** Sabotaj — ikkita kalit o'chirilganda AYNAN ikkita test yiqildi, qolgan 52 yashil
- **Committed in:** `a3f6a13`

**9. [Rule 2] Komponentlar HTTP qatlamiga to'g'ridan-to'g'ri tegishi — QISMAN yopildi**

- **Found during:** Task 2
- **Issue:** Qabul mezoni `frontend/src/components` bo'ylab `apiFetch` grep'ining **0** bo'lishini talab qiladi. O'lchangan boshlang'ich holat: **beshta** komponent, jami 8 chaqiruv (`market-picker`, `user-menu`, `login-form`, `change-password-form`, `locale-switcher`).
- **Fix:** Bu reja EGALIK QILADIGAN endpointlar ko'chirildi: `setup-status` va `GET /markets` -> `market-queries.ts`, `select-market` va `logout` -> yangi `auth-queries.ts`. `user-menu.tsx` ham `useLogout` ga o'tdi — aks holda `LOGOUT_PATH` ikki joyda yashardi.
- **NIMA QILINMADI va NEGA:** `login-form`, `change-password-form`, `locale-switcher` TEGILMADI. Ular 1-fazaning auth/profil yuzasi, bu rejaning `files_modified` ro'yxatida yo'q va ularning har birida xavfsizlikka daxldor xulq bor (`login-form` ning enumeratsiyaga qarshi TORROQ xato xaritasi — T-01-63; `change-password-form` ning fail-closed oqimi — T-01-64). Ularni ko'chirish 02-14…02-16 ga hech qanday foyda bermaydi (ular yangi ekran quradi, auth'ga tegmaydi) va qamrov chegarasini buzardi.
- **O'lchangan yakuniy holat:** 5 komponent / 8 chaqiruv -> **3 komponent / 4 chaqiruv**. Mezon TO'LIQ bajarilmadi va bu ataylab.
- **Files modified:** `frontend/src/lib/auth-queries.ts`, `frontend/src/components/{auth/market-picker,shell/user-menu}.tsx`
- **Verification:** market-picker'ning 7 testi o'zgarmasdan yashil qoldi
- **Committed in:** `ccd369f`

---

**Total deviations:** 9 auto-fixed (2 bug, 5 missing-critical, 2 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Yangi npm paketi QO'SHILMADI (UI-SPEC §1.4 saqlandi), yangi endpoint yoki backend o'zgarishi yo'q. #1, #5, #6 rejaning O'Z bandlari orasidagi yoki reja bilan bugungi kod bazasi orasidagi haqiqiy ziddiyatlar; #2, #3, #4, #7, #8 reja ko'rmagan beshta yo'lni yopadi; #9 — mezonning qamrovi rejaning fayl chegarasidan kengroq bo'lgani uchun ATAYIN qisman bajarildi va o'lchov bilan hujjatlashtirildi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `ERROR_CODES` uzunligi | ✅ 12 -> **35** (+23) |
| `ERROR_CODES` backend `MARKET_ERROR_CODES` ni qamraydi | ✅ 23/23 |
| `market-errors.ts` `case` soni + `default` | ✅ **23** + bor |
| `tariffListResponseSchema.min_valid_from` | ✅ mavjud, `.optional()`/`.nullable()` EMAS |
| `grep -c "StallTone" api-types.ts` | ✅ **0** |
| Yangi sxemalarda `.optional()` | ✅ **0** (uchala uchrash — «ishlatilmasin» izohida) |
| `grep "min_valid_from" market-queries.ts` — `??`/`\|\|` fallback | ✅ **0** (ikkala uchrash izohda) |
| `frontend/src/lib/queries.ts` o'zgardimi | ✅ **YO'Q** |
| `useStallsQuery` / `useVendorsQuery` | ✅ ikkalasi `useInfiniteQuery` |
| `useCreateStall` yon ta'siri | ✅ `stalls`, `map`, `setup-status` (+ `zones`, `categories`) — hook ustida o'lchandi |
| `useCreateTariff` yon ta'siri | ✅ `tariffs`, `categories`, `setup-status` |
| Mobil pastki panel elementlari | ✅ `slice(0, 4)` + `Ko'proq` = eng ko'pi **5** |
| Desktop yon panel guruhlari | ✅ **3** guruh (2 sarlavhali + guruhsiz), bo'sh guruh chizilmaydi |
| Komponentlarda to'g'ridan-to'g'ri HTTP chaqiruvi | ⚠ 5 fayl / 8 chaqiruv -> **3 fayl / 4 chaqiruv** (deviatsiya #9) |
| i18n kalitlari | ✅ 122 -> **295**, uchala tilda parity to'liq |
| `tariffs.initialHint` `{date}` uchala tilda | ✅ |
| `wizard.blocking.*` ↔ `BlockingItem.code` | ✅ **6/6**, uchala tilda |
| `import.errors.*` ↔ `ImportIssue.code` | ✅ **10/10**, uchala tilda |
| `grep "Excel'" messages/*.json` | ✅ **0** |
| `grep "\.xlsx" uz-Latn.json ru.json` | ✅ **0** |
| `uz-Cyrl.json` qo'lda tahrirlanganmi | ✅ YO'Q — faqat `i18n:gen` (192 qator qo'shildi) |
| Sabotaj o'lchovlari (4 ta) | ✅ har birida AYNAN kutilgan test(lar) yiqildi |
| Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

## Issues Encountered

- **`git checkout --` KUZATILMAGAN faylni tiklay olmaydi.** Birinchi sabotaj `market-queries.ts` ustida qilindi, lekin fayl hali commit qilinmagan edi — `git checkout` «not tracked» dedi va tiklash qo'lda bajarildi.
- **Ikkinchi, jiddiyroq holat: `git checkout -- ru.json` COMMIT QILINMAGAN ishni o'chirdi.** Fayl kuzatilgan edi, lekin Task 3 ning qo'shimchalari hali staged emasdi — `checkout` uni Task 2 holatiga qaytardi va to'qqiz namespace yo'qoldi. Darhol sezildi (`i18n:check` boshqa kalitdan shikoyat qildi) va matnlar qayta yozildi. **Xulosa (patterns'ga kiritildi):** sabotajdan oldin fayl scratchpad'ga nusxalanadi va tiklash o'sha nusxadan bajariladi — keyingi ikki sabotaj aynan shunday o'tkazildi.
- **`MoreHorizontal` lucide-react 1.27 da mustaqil eksport EMAS** — u `Ellipsis` ning taxallusi. Ikonka nomlari `node_modules/lucide-react/dist/lucide-react.d.ts` dan tekshirildi, taxminga tayanilmadi.
- **`frontend/node_modules` worktree'da bo'sh edi** — `npm ci` bilan `package-lock.json` dan tiklandi (yangi paket o'rnatilmadi).

## Known Stubs

Yo'q. Bu reja ekran QURMAYDI — u kontrakt qatlami, va uning har bir eksporti haqiqiy endpointga yoki haqiqiy tarjimaga ulanadi. Birorta hook `TODO` qoldirmaydi, birorta sxema bo'sh emas, birorta tarjima kaliti placeholder emas.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `/map`, `/stalls`, `/vendors`, `/tariffs`, `/calendar` marshrutlari hali YO'Q | 02-14, 02-15, 02-16 | Navigatsiya ularni ko'rsatadi va bosilganda 404 beradi. Bu rejaning ATAYIN tanlovi: navigatsiya kontrakti (UI-SPEC §12.3) ekranlardan oldin landi, aks holda uchala UI rejasi `app-shell.tsx` ga birgalikda tegib, ketma-ket bajarilishga majbur bo'lardi |
| `login-form`, `change-password-form`, `locale-switcher` HTTP qatlamiga to'g'ridan-to'g'ri tegadi | belgilanmagan (1-faza yuzasi) | Deviatsiya #9 da o'lchangan va sababi yozilgan. Bu yangi qarz emas — u 1-fazadan beri shunday |
| Ro'yxatlarning yuklanish holati hamon matnli `role="status"` | 02-14+ | 02-02 ning «Deferred Items» bandi. `Skeleton` primitivi tayyor; bu reja ekran qurmagani uchun uni qo'llash joyi ham yo'q edi |
| `errors.loadFailedTitle` / `loadFailedBody` (UI-SPEC §10.5) | 02-14+ | Rejaning kalit ro'yxatida yo'q; ekran rejalari ularni o'z xato holatlari bilan birga qo'shsin |

## Threat Flags

Yangi xavfsizlik yuzasi rejaning `<threat_model>` idan tashqarida paydo bo'lmadi: yangi endpoint, yangi auth yo'li, fayl kirishi yoki sxema o'zgarishi YO'Q. `apiRequest()` mavjud `apiFetch()` ning ICHIDAN ajratildi — token, single-flight refresh va cookie siyosati bayt-ba-bayt o'sha mantiq.

| Threat ID | Holat |
|-----------|-------|
| T-02-98 | mitigate — har `apiFetch` `schema` bilan; 25 yangi sxema chegarani qopladi. `apiRequest()` (sxemasiz) FAQAT ikkilik yuklab olishda ishlatiladi va uning natijasi DOM'ga matn sifatida tushmaydi |
| T-02-99 | mitigate — `marketErrorMessageKey()` 23 kodni tarjima kalitiga aylantiradi; `default` `errorMessageKey` ga tushadi. `ApiError.body` XOM holda saqlanadi, lekin u faqat `importErrorResponseSchema` orqali o'qiladi — xom `detail` hech qayerda render qilinmaydi |
| T-02-100 | accept (aniqlangan) — `rbac.ts` tepasidagi ogohlantirish saqlandi; `app-shell.tsx` da ham takrorlandi |
| T-02-101 | mitigate — nav elementlari `hasPermission` bo'yicha filtrlanadi; kassir/nazoratchida `market_data_view` ham, `vendor_view` ham yo'q, ya'ni ular faqat Boshqaruv panelini ko'radi. Bo'sh guruh sarlavhasi ham chizilmaydi (bo'lim NOMI ham sizmaydi) |
| T-02-102 | mitigate — `dangerouslySetInnerHTML` qo'shilmadi; DB kontenti (`zone_name`, `vendor_name`, `market.name`) faqat matn tugunlari |
| T-02-103 | mitigate — `import.showingFirst` / `remaining` kalitlari va `downloadErrorReport()` yo'li tayyor; ekrandagi chegarani 02-16 qo'llaydi |
| T-02-104 | mitigate — `saveBlob()` `revokeObjectURL` bilan tozalaydi. Bekor qilish keyingi makrotaskda: `click()` dan keyin darhol revoke qilish yuklashni bo'sh fayl bilan tugatardi (sabab kodda yozilgan) |
| T-02-104a | mitigate — `min_valid_from` sxemada MAJBURIY; `useTariffsQuery` javobni o'zgartirmaydi; `??`/`\|\|` fallback grep bilan **0** deb o'lchandi |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run typecheck` | ✅ exit 0 |
| 2 | `npm --prefix frontend run lint` | ✅ exit 0 |
| 3 | `npm --prefix frontend run i18n:check` | ✅ **295 kalit × 3 til**, drift yo'q |
| 4 | `npm --prefix frontend test` | ✅ **54 node + 18 vitest**, 0 fail |
| 5 | `npm --prefix frontend run build` | ✅ exit 0 |

## User Setup Required

Yo'q — tashqi xizmat sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja backend'ga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi) va yangi npm paketi o'rnatmaydi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-01…MARKET-06]` deb yozgan. Bu reja ularning birortasini foydalanuvchi ko'radigan qobiliyat sifatida YAKUNLAMAYDI — u kontrakt qatlami va ekranlar 02-14/02-15/02-16 da quriladi. Ularni bu yerda «bajarildi» deb belgilash traceability jadvalini yolg'on qilardi.

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md` — orkestrator egalik qiladigan umumiy artefaktlar.

## Next Phase Readiness

**02-14 va 02-15 PARALLEL ishlashi mumkin** — ikkalasi ham faqat o'z komponent papkasiga tegadi. Qotirilgan kontrakt:

- **Sxemalar:** `api-types.ts` dan import qiling, QAYTA E'LON QILMANG. Rasta, sotuvchi, tarif, kalendar, xarita, usta va import shakllarining hammasi tayyor.
- **So'rovlar:** `market-queries.ts` dan hook oling. Komponentda `apiFetch`/`apiRequest` YOZMANG — invalidatsiya grafi shu modulda va u test bilan qulflangan.
- **Xatolar:** `marketErrorMessageKey(error)` -> `t(kalit)`. Yangi kod qo'shilsa `error-codes.test.mjs` darhol qizaradi.
- **Matnlar:** to'qqiz namespace tayyor. Yangi kalit kerak bo'lsa `uz-Latn.json` + `ru.json` ga yozing va `npm run i18n:gen` bajaring — `uz-Cyrl.json` ga QO'L TEGIZMANG.
- **Navigatsiya:** 8 bo'lim allaqachon ko'rinadi. `app-shell.tsx` ga TEGISH SHART EMAS — yangi sahifa yaratish kifoya.

**02-14 uchun alohida eslatma:** xarita katagining rang tipi `components/stalls/stall-tone.ts` da tug'iladi, `api-types.ts` da EMAS (u yerda mexanik grep darvozasi bor va u qizaradi). Server `status` + `has_vendor` beradi, rang esa ulardan hosil bo'ladi.

**02-15 uchun alohida eslatma:** tarif dialogidagi sana maydonining `min` atributi `useTariffsQuery()` javobidagi `min_valid_from` dan TO'G'RIDAN-TO'G'RI olinadi. Ertangi kunni lokal hisoblash yoki `??` bilan fallback berish qoralama bozorda ustaning 4-qadamini bajarilmas qiladi (T-02-104a).

**02-16 uchun alohida eslatma:** import xatolari `importErrorsOf(error)` dan olinadi (`ApiError.body` da), `error.detail` dan emas — `detail` faqat `import_validation_failed` kodini beradi.

## Self-Check: PASSED

- Da'vo qilingan 6 yangi fayl diskda mavjud: `market-queries.ts`, `market-errors.ts`, `auth-queries.ts`, `market-queries.test.tsx`, `nav-more-sheet.tsx`, `error-codes.test.mjs`
- Da'vo qilingan 8 o'zgartirilgan fayl `git diff --stat 974d36c..HEAD` da ko'rinadi (14 fayl, +3029/−127)
- Uchala vazifa commit'i git tarixida mavjud: `41f0734`, `ccd369f`, `a3f6a13`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D` uchalasida ham bo'sh)
- To'rt sabotajdan keyin ishchi daraxt toza (`git status --short` bo'sh)
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
