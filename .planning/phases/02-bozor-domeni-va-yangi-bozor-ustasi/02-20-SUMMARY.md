---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 20
subsystem: ui
tags: [tanstack-query, multi-tenant, cache-isolation, auth-store, sabotage, gap-closure]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-13 — `market-queries.ts` ning 35 hooki, invalidatsiya grafi va `market-queries.test.tsx` o'lchov darvozasi; 02-14/02-15/02-16 — o'sha hooklarni ishlatuvchi reestr, tarif va usta ekranlari"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`auth-store.ts` (modul darajasidagi `memorySession`, `listeners`/`emit`/`subscribe` uchligi, `applySession`/`clearSession`), `query-provider.tsx` (`useState` ichidagi `QueryClient`), `api-client.ts` ning refresh yo'li"
provides:
  - "`market-queries.ts::domainKey(marketId, ...rest)` — har bir domen kaliti `[\"m\", marketId, ...]` shaklida; global kalit konstantalari BUTUNLAY olib tashlangan"
  - "11 ta `market_id` oladigan kalit fabrikasi (`zonesKey`…`setupStatusKey`)"
  - "`auth-store.ts::subscribeSessionReset()` — sessiya identifikatori o'zgarganda ishlaydigan ALOHIDA obunachi kanali"
  - "`query-provider.tsx` — `subscribeSessionReset` -> `client.clear()` ulanishi"
  - "`market-queries.ts::importSideEffects(marketId, kind)` — WR-10 yopildi: sotuvchi importi biriktirish tarixini ham bekor qiladi"
  - "`frontend/src/lib/tenant-cache.test.tsx` — CR-01 ning ikkala yarmini ALOHIDA qulflaydigan 6 test"
affects: [02-VERIFICATION qayta tekshiruvi, kassir-moduli, hisobotlar, bozor-almashtirish-UI-v2]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kesh kaliti tenant chegarasining bir qismi: `domainKey(marketId, ...)` dan tashqari domen kaliti YO'Q"
    - "Doiralashni chetlab o'tish TS xatosisiz mumkin emas — global konstanta qoldirilmaydi, kalit fabrikasining birinchi argumenti majburiy"
    - "`auth-store` React/Query'dan mustaqil qoladi; kesh bilan aloqa obunachi reyestri orqali (`subscribeSessionReset`)"
    - "Sessiya-tozalash kanali render obunasidan (`useSyncExternalStore` ning `listeners`) ATAYIN ajratilgan"
    - "Sabotaj o'lchovi ikki himoya qatlamining MUSTAQILLIGINI isbotlaydi: har test faqat bitta yarimni o'lchaydi"

key-files:
  created:
    - frontend/src/lib/tenant-cache.test.tsx
  modified:
    - frontend/src/lib/market-queries.ts
    - frontend/src/lib/auth-store.ts
    - frontend/src/lib/query-provider.tsx
    - frontend/src/lib/market-queries.test.tsx
    - frontend/src/components/vendors/vendor-list.test.tsx
    - frontend/src/components/stalls/stall-map.test.tsx

key-decisions:
  - "Global kalit konstantalari (`ZONES_KEY`…`SETUP_STATUS_KEY`) saqlanmadi, butunlay o'chirildi — qolsa keyingi kod ularni qayta ishlatib bo'shliqni jimgina qaytarardi"
  - "`MARKETS_KEY` ATAYIN doiralanmagan: `GET /markets` bozor tanlashdan OLDIN, tenant konteksti yo'q paytda o'qiladi; uni logoutdagi `clear()` himoya qiladi"
  - "`useMarketId()` xususiy yordamchisi — 20+ hookda `principal?.marketId ?? null` ni takrorlash bittasini tushirib qoldirish xavfini tug'dirardi"
  - "`applySession()` da tozalash SHARTLI (`marketId` bo'yicha): u `/auth/refresh` da ham chaqiriladi va shartsiz tozalash har 15 daqiqada ekranni qayta yuklardi"
  - "`clear()` tanlandi, yumshoqroq `reset*`/`remove*` variantlari emas: `reset*` kalitlarni saqlab, A bozorining so'rovlarini B kontekstida QAYTA yuborardi"
  - "Sizib chiqish testi `updatePrincipal` orqali quriladi — u tozalash kanalini ishga tushirmaydi, ya'ni test FAQAT doiralashni o'lchaydi"
  - "Tozalash testlari QIYMAT bo'yicha o'lchaydi (zona nomi keshda qoldimi), kalit tuzilishi bo'yicha emas — shu sabab ular doiralash sabotajida yashil qoladi"
  - "`emitSessionReset` `const` sifatida e'lon qilindi: shunda chaqiruv shakli faylda aynan uchta haqiqiy chaqiruv joyida uchraydi va grep to'g'ri javob beradi"

patterns-established:
  - "Kalit doiralashi: `domainKey(marketId, ...rest)` -> `[\"m\", marketId, ...rest]`; prefiks bo'yicha bekor qilish `domainKey(marketId, \"stalls\")` bilan"
  - "Sessiya identifikatori kanali: `subscribeSessionReset(fn) -> unsubscribe`, `setSession`/`clearSession` shartsiz, `applySession` shartli"
  - "Ikki himoya qatlami alohida testlanadi: bir test bir yarimni o'lchaydi, aks holda biri ikkinchisini yopib turib testni yolg'on-yashil qilardi"

requirements-completed: [MARKET-02, MARKET-04]

# Metrics
duration: 35min
completed: 2026-08-01
---

# Phase 2 Plan 20: Klient keshining tenant chegarasi Summary

**Har bir domen so'rov kaliti `["m", marketId, ...]` bilan doiralandi va sessiya identifikatori o'zgarganda `QueryClient.clear()` ulandi — brauzer endi bozor almashtirilgandan yoki foydalanuvchi almashgandan keyin oldingi bozorning zonalari, rastalari va sotuvchi F.I.Sh. + telefonini ko'rsata olmaydi (CR-01 + WR-10).**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-01T06:37:00Z
- **Completed:** 2026-08-01T07:12:00Z
- **Tasks:** 3
- **Files modified:** 7 (1 yaratilgan, 6 o'zgartirilgan)

## Accomplishments

- **CR-01 ning birinchi yarmi (doiralash).** `domainKey(marketId, ...rest)` qo'shildi; `ZONES_KEY`/`CATEGORIES_KEY`/`STALLS_KEY`/`MAP_KEY`/`TARIFFS_KEY`/`CALENDAR_KEY`/`VENDORS_KEY`/`ASSIGNMENTS_KEY`/`SETUP_STATUS_KEY` global konstantalari **butunlay o'chirildi**. 11 ta kalit fabrikasi birinchi argument sifatida `marketId` oladi, ya'ni doiralashni chetlab o'tish endi TS xatosini beradi.
- **CR-01 ning ikkinchi yarmi (tozalash).** `auth-store.ts` ga `resetListeners` + `subscribeSessionReset()` kanali qo'shildi; `query-provider.tsx` unga `client.clear()` ni uladi. Repo bo'yicha `client.clear()` qidiruvi endi ishlab chiqarish chaqiruvini beradi — 02-VERIFICATION.md dagi "nol natija" holati tugadi.
- **Ortiqcha tozalashning oldi olindi.** `applySession()` faqat `marketId` o'zgarganda tozalaydi: u `/auth/refresh` javobida ham chaqiriladi (`api-client.ts:164`) va u yerda bozor o'zgarmaydi.
- **WR-10 yopildi.** Sotuvchi importi endi `assignments` prefiksini ham bekor qiladi (`ImportRepository.insert_vendors()` har rasta kodi ko'rsatilgan sotuvchi uchun `stall_assignments` qatori yozadi), shuningdek `stalls` va `map` ni ham (`has_vendor`/`vendor_name` o'zgaradi).
- **Ikkala yarim mustaqil qulflandi.** `tenant-cache.test.tsx` — 6 test; uchta sabotaj o'lchovi ikki qatlamning bir-birining o'rnini bosmasligini isbotladi.
- **Yashil darvoza saqlandi.** Frontend testlari 94 → **101** (54 node + 47 vitest), typecheck/lint/build/i18n:check hammasi 0.

## Task Commits

1. **Task 1 (RED): WR-10 regressiya da'vosi** — `06f900c` (test)
2. **Task 1 (GREEN): kalitlarni `market_id` bilan doiralash + WR-10 tuzatish** — `025634b` (feat)
3. **Task 2: sessiya identifikatori o'zgarganda keshni tozalash** — `940c505` (feat)
4. **Task 3: sizib chiqish regressiya testi va sabotaj o'lchovi** — `51ca6f3` (test)

_Task 1 `tdd="true"` bo'lgani uchun ikkita commit: RED (yiqiladigan da'vo) → GREEN (implementatsiya)._

## Files Created/Modified

- `frontend/src/lib/market-queries.ts` — `domainKey` va 11 kalit fabrikasi; global konstantalar o'chirildi; `useMarketId()` yordamchisi; barcha `use*Query` da `enabled: marketId !== null`; yon ta'sir to'plamlari funksiyaga aylandi (`stallSideEffects`, `tariffSideEffects`, `assignmentSideEffects`, `calendarSideEffects`, `importSideEffects`); modul docstringi CR-01 sababi bilan yangilandi
- `frontend/src/lib/auth-store.ts` — `resetListeners` to'plami, `subscribeSessionReset()`, xususiy `emitSessionReset`; `setSession`/`clearSession` shartsiz, `applySession` shartli chaqiradi; docstringga kesh-chegara bandi
- `frontend/src/lib/query-provider.tsx` — `useEffect(() => subscribeSessionReset(() => client.clear()), [client])` va nega aynan `clear()` ekanini tushuntiruvchi izoh
- `frontend/src/lib/tenant-cache.test.tsx` *(yangi)* — CR-01 ning ikkala yarmini alohida o'lchaydigan 6 test; docstringda 02-VERIFICATION.md ning 7-haqiqati so'zma-so'z
- `frontend/src/lib/market-queries.test.tsx` — josus endi kalitning DOMEN segmentini (indeks 2) va bozor prefiksini alohida yig'adi; `AuthProvider` bilan o'ralgan; WR-10 juftlik testi; "bekor qilingan HAR domen kaliti joriy bozorga doiralangan" nazorat testi
- `frontend/src/components/vendors/vendor-list.test.tsx` — `vendorsKey(MARKET_ID, {q:""})` yangi imzosi; ekilgan kalit va sessiyadagi bozor bitta konstantadan
- `frontend/src/components/stalls/stall-map.test.tsx` — `AuthProvider` + sessiya urug'i (xarita so'rovi endi bozorsiz umuman ketmaydi)

## Decisions Made

- **`market-queries.ts:126-128` dagi eski qaror bekor qilindi.** U `setup-status` ni `marketId` siz keng bekor qilishni "usta faqat BITTA bozor uchun ochiq bo'ladi" taxmini bilan asoslagan edi. Izoh o'chirilmadi — **sababi bilan almashtirildi**: platforma admini bitta sessiyada ikkinchi bozor yaratishi ustaning butun maqsadi va aynan shu yo'l A bozorining zonalarini B ning 2-qadamida ko'rsatgan.
- **`useActivateMarket` / `useDeleteDraftMarket` kaliti store'dan emas, mutatsiya argumentidan olinadi** — faollashtirilayotgan/o'chirilayotgan bozor store'dagi joriy bozordan farq qilishi mumkin.
- **`useCreateMarket` store'dagi (hali eski) bozorni ishlatadi va bu zarar qilmaydi** — undan keyin darhol `applySession(...)` butun keshni bo'shatadi; `MARKETS_KEY` esa doiralanmagan va to'g'ri bekor qilinadi. Sabab kodda izohlangan.
- **Deferred (v2) chegarasi saqlandi:** sessiya ichida bozor almashtirish UI'si qurilmadi (`market-picker.tsx:35-37`). Bu reja mavjud yo'llarni xavfsiz qildi, yangi yo'l ochmadi.

## Sabotaj o'lchovlari

Uchala sabotaj ham AYNAN kutilgan testni — va faqat o'shani — qizartirdi. Bu ikki himoya qatlamining bir-birining o'rnini bosmasligini isbotlaydi:

| # | Sabotaj | Qizargan testlar | Yashil qolgan |
|---|---------|------------------|---------------|
| 1 | `domainKey` → `(_marketId, ...rest) => [...rest]` (doiralash olib tashlanadi) | **3**: "ikki bozorning `zones` kaliti TENG EMAS", "A bozorining zonalari B kontekstida KO'RINMAYDI", "bekor qilingan HAR domen kaliti joriy bozorga doiralangan" | Barcha tozalash testlari (`clearSession`, `applySession`-identifikator, token yangilash, obunani bekor qilish) |
| 2 | `client.clear()` → bo'sh funksiya (tozalash olib tashlanadi) | **2**: "`clearSession()` A bozorining qatorlarini keshda QOLDIRMAYDI", "`applySession()` boshqa bozor bilan chaqirilganda kesh bo'shaydi" | Barcha kalit testlari |
| 3 | `applySession` dagi shart olib tashlanadi (tozalash SHARTSIZ) | **1**: "token yangilash (BIR XIL bozor) keshni SAQLAYDI" | Qolgan 46 test |

Sabotaj 1 va 2 ning natijalari o'zaro **kesishmaydi** — reja talab qilgan mustaqillik shu bilan o'lchandi. Uchala sabotaj ham `git checkout --` bilan qaytarildi va tiklangan daraxt qayta yashil ekani tasdiqlandi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `vendor-list.test.tsx` kalit imzosi o'zgarishidan yiqildi**
- **Found during:** Task 1 (GREEN bosqichi)
- **Issue:** `vendorsKey(filters)` → `vendorsKey(marketId, filters)` imzosi o'zgargach, `vendor-list.test.tsx:79` typecheck'ni yiqitdi (`TS2554: Expected 2 arguments, but got 1`). Bu fayl rejaning `files_modified` ro'yxatida yo'q edi, lekin o'zgarish TO'G'RIDAN-TO'G'RI shu taskning natijasi.
- **Fix:** `MARKET_ID` konstantasi ajratildi va ekilgan kesh kaliti ham, sessiyadagi `marketId` ham AYNAN shu qiymatdan oladi — ikkalasi ajralib ketsa test bo'sh holat chiqarib yiqiladi, ya'ni doiralash bu faylda ham o'lchanadi.
- **Files modified:** `frontend/src/components/vendors/vendor-list.test.tsx`
- **Verification:** `npm --prefix frontend run typecheck` exit 0; test yashil
- **Committed in:** `025634b` (Task 1 GREEN commit)

**2. [Rule 3 - Blocking] `stall-map.test.tsx` `AuthProvider` siz yiqildi**
- **Found during:** Task 1 (GREEN bosqichi)
- **Issue:** `useStallMapQuery` endi `useAuthStore()` ni o'qiydi. `stall-map.test.tsx` `StallMap` ni faqat `QueryClientProvider` ostida render qilardi → 7 test `useAuthStore() faqat <AuthProvider> ichida ishlaydi` xatosi bilan yiqildi. Bu fayl ham `files_modified` da yo'q edi, lekin sabab aynan shu taskning o'zgarishi (fayl `market-queries` ni to'g'ridan-to'g'ri import qilmaydi, shuning uchun dastlabki grep uni ko'rsatmagan edi).
- **Fix:** `AuthProvider` bilan o'raldi va `beforeEach` da bozor admini sessiyasi urug'landi (`afterEach` da tozalanadi).
- **Files modified:** `frontend/src/components/stalls/stall-map.test.tsx`
- **Verification:** `npm --prefix frontend run test:component` exit 0 (o'sha 7 test qayta yashil)
- **Committed in:** `025634b` (Task 1 GREEN commit)

**3. [Rule 1 - Bug] Rejaning uchta mexanik qabul mezoni o'z izohlarim tufayli yolg'on-qizil edi**
- **Found during:** Task 2
- **Issue:** Uchta grep mezoni izoh matnining o'zi tufayli buzilardi: (a) `grep -c "emitSessionReset()" auth-store.ts` = 4 (mening izohim shu matnni o'z ichiga olgan), (b) `grep "resetQueries\|removeQueries" query-provider.tsx` natija berardi (rejaning O'ZI shu ikkisi haqida izoh yozishni talab qiladi), (c) `grep "QueryClient" auth-store.ts` natija berardi (docstringda eslatilgan).
- **Fix:** Izohlar mazmunini saqlagan holda qayta yozildi: `emitSessionReset` `const` sifatida e'lon qilindi (ta'rif qatori endi chaqiruv shakliga mos kelmaydi); `reset*`/`remove*` oilasidagi `*Queries` metodlari deb yozildi; `QueryClient` o'rniga "so'rov keshi kutubxonasi" deyildi. Mezonlarning NIYATI (ishlab chiqarish kodida bu API'lar yo'q) buzilmadi, izohlarning ma'nosi ham yo'qolmadi.
- **Files modified:** `frontend/src/lib/auth-store.ts`, `frontend/src/lib/query-provider.tsx`
- **Verification:** uchala grep endi kutilgan natijani beradi (3 / 0 / 0)
- **Committed in:** `940c505` (Task 2 commit)

**4. [Rule 3 - Blocking] `tenant-cache.test.tsx` lint qoidasini buzdi**
- **Found during:** Task 3
- **Issue:** `QueryProvider` klientni o'z ichida quradi, shuning uchun test uni render paytida modul o'zgaruvchisiga yozib olardi → `react-hooks/globals`: "Cannot reassign variables declared outside of the component/hook".
- **Fix:** Yozish `useEffect` ichiga ko'chirildi.
- **Files modified:** `frontend/src/lib/tenant-cache.test.tsx`
- **Verification:** `npm --prefix frontend run lint` exit 0
- **Committed in:** `51ca6f3` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (3 blocking, 1 bug)
**Impact on plan:** Hech qanday scope creep yo'q. 1 va 2 — imzo o'zgarishining bevosita to'lqini (rejaning `files_modified` ro'yxati ularni oldindan ko'rmagan, lekin ular shu taskning ajralmas qismi). 3 — rejaning o'z mezonlarini bajariladigan holga keltirish. 4 — lint qoidasiga moslashish.

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi.** Avval asosiy repodagi `node_modules` ga junction qo'yildi va typecheck/lint/test shu bilan ishladi, lekin `next build` Turbopack panikasi berdi (`Symlink [project]/node_modules is invalid, it points out of the filesystem root`). Junction `rmdir` bilan olib tashlandi (asosiy repo tegilmadi, tekshirildi) va worktree ichida haqiqiy `npm ci --prefer-offline` bajarildi → `npm run build` exit 0. **Bu kod nuqsoni emas, sinov muhiti artefakti edi.**
- **`getQueryCache().getAll()` ning uzunligi 0 bo'lmasligi.** `clearSession()` dan keyin React qayta render qiladi va bozorsiz sessiyada `enabled: false` kuzatuvchi bo'sh yozuvni qayta ro'yxatdan o'tkazadi. Shuning uchun test yozuv SONINI emas, keshda qolgan MA'LUMOTNI (zona nomlarini) o'lchaydi — bu ham aniqroq, ham sabotajga sezgirroq. Sabab test faylida izohlangan.

## Verification natijalari

| Tekshiruv | Natija |
|---|---|
| `npm --prefix frontend run typecheck` | exit 0 |
| `npm --prefix frontend run lint` | exit 0 |
| `npm --prefix frontend test` (node + vitest) | exit 0 — **54 + 47 = 101** test (baza 94) |
| `npm --prefix frontend run i18n:check` | exit 0 — 418 kalit × 3 til, drift yo'q |
| `npm --prefix frontend run build` | exit 0 |
| `git diff --exit-code frontend/package.json` | o'zgarish yo'q (yangi paket o'rnatilmadi) |
| `grep -rn "client.clear" frontend/src \| grep -v ".test."` | `query-provider.tsx:73` — ishlab chiqarish chaqiruvi bor |
| `git diff --exit-code market-picker.tsx market-requisites-form.tsx api-client.ts` | tegilmagan — mexanizm ularning ostida ishlaydi |

**`npm run gate` TO'LIQ ishga tushirilmadi (ochiq qarz).** Uning backend qismlari (`ruff`/`mypy`, `pytest`, `pytest tests/tenancy`) Docker Compose talab qiladi va bu reja shu to'lqinda `services/core-api/` ustida ishlayotgan 02-19 ijrochisi bilan bir vaqtda konteyner/port ulashardi. Bu reja **birorta backend fayliga tegmagan**, ya'ni backend natijasi o'zgarishi mumkin emas. Darvozaning frontend qismi (i18n:check, test, typecheck, lint, build) to'liq va yashil ishga tushirildi; to'liq `npm run gate` ni birlashtirilgandan keyin orkestrator o'tkazishi kerak.

## Known Stubs

Yo'q — bu rejada stub, placeholder yoki qattiq kodlangan bo'sh qiymat yaratilmadi.

## Threat Flags

Yo'q — yangi tarmoq endpointi, auth yo'li, fayl kirishi yoki ishonch chegarasidagi sxema o'zgarishi kiritilmadi. Reja mavjud ishonch chegarasini (klient keshi) mustahkamladi, yangisini ochmadi.

## User Setup Required

Yo'q — tashqi xizmat sozlamasi talab qilinmaydi.

## Next Phase Readiness

- **02-VERIFICATION.md ning 3-bo'shlig'i (7-haqiqat / CR-01) yopilgan va qayta tekshirishga tayyor.** Ikkala `missing[]` bandi bajarildi: (1) har bir domen so'rov kaliti `market_id` bilan doiralandi, (2) bozor almashtirilganda va logoutda kesh `client.clear()` bilan to'liq tozalanadi.
- **WR-10 ham yopildi** — u rejaning yo'l-yo'lakay maqsadi edi.
- **Ochiq qarz:** to'liq `npm run gate` (backend Docker qismi) birlashtirilgandan keyin bir marta o'tkazilishi kerak.
- **Kelajakdagi bozor-almashtirish UI'si (v2) uchun poydevor tayyor:** kalitlar doiralangan va tozalash kanali mavjud, ya'ni UI qo'shilganda yangi tenant-izolyatsiya ishi talab qilinmaydi — faqat `applySession` chaqiruvi kerak bo'ladi.

## Self-Check: PASSED

Barcha da'vo qilingan artefaktlar diskda va barcha commit'lar git tarixida mavjud:

- Fayllar (6/6): `tenant-cache.test.tsx`, `market-queries.ts`, `auth-store.ts`, `query-provider.tsx`, `market-queries.test.tsx`, `02-20-SUMMARY.md`
- Commit'lar (5/5): `06f900c`, `025634b`, `940c505`, `51ca6f3`, `aecc812`

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
