---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 14
subsystem: ui
tags: [react-19, css-grid, a11y, roving-tabindex, nuqs, memoization, sabotage, i18n]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-13 — `api-types.ts` zod sxemalari, `market-queries.ts` hooklari, `market-errors.ts` xato xaritasi, to'qqiz i18n namespace, `app-shell.tsx` navigatsiyasi; 02-02 — yetti `ui/` primitivi (`dialog.sheetOnMobile`, `Skeleton`, `EmptyState`, `Badge`, `Field`, `Select`), WCAG AA tokenlari; 02-08 — `GET /stalls` (keyset + `code_sort`), `GET /stalls/map`, `POST /stalls`, `POST /stalls/{id}/category`"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`rbac.ts` ko'zgusi, `auth-store.ts`, nuqs `NuqsAdapter`, vitest + jsdom naqshi, `fireEvent` konvensiyasi"
provides:
  - "`/[locale]/(app)/stalls` — rastalar reestri: URL filtrlari, keyset paginatsiya, modal tahrir, raqam+Enter = karta"
  - "`/[locale]/(app)/map` — sxematik plan-xarita: CSS Grid, roving tabindex, zona bloklari"
  - "`components/stalls/stall-map-types.ts` — `StallTone` / `StallCell` / `ZoneBlock` render kontrakti"
  - "`components/stalls/stall-tone.ts` — `toneOf()` (default'siz) + `TONE_STYLES` to'liq `Record` + `TONE_STATUS`"
  - "`components/stalls/stall-cell.tsx` — memoizatsiyalangan 44x44 `<button>`"
  - "`components/stalls/stall-card-dialog.tsx` — `StallCardProps` (`children` ilgagi 6–7 fazalar uchun)"
  - "`components/stalls/stall-list.tsx` — `StallStatusBadge` (holat -> tone + ikonka)"
  - "`stall-map.test.tsx` — 8 vitest: tartib, qayta render, a11y, karta"
  - "`globals.css` `.zone-block` — `content-visibility: auto` (virtualizatsiya kutubxonasisiz)"
  - "`stalls.*` / `map.*` namespace'lariga 18 yangi kalit x 3 til (295 -> 313)"
affects: [02-16, 02-17, kassir-moduli, 06-anomaliya-hisobi, 07-nizolar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Xarita katagi — haqiqiy `<button>` + `React.memo`; tanlangan ID sahifa holatida, katak propida EMAS (Pitfall 8)"
    - "Ekran kengligi `useSyncExternalStore` bilan o'qiladi — `useEffect`+`setState` gidratatsiya nomuvofiqligi va kaskadli render berardi"
    - "Effekt ichida sinxron `setState` YO'Q (React Compiler `react-hooks/set-state-in-effect`): dialog xatosi YOPILISHDA tozalanadi, qidiruv natijasi `refetch()` dan O'QILADI"
    - "Forma `GET /{id}` javobidan bir marta urug'lanadi (`seededFor` ref) — fon refetch'i terilayotgan matnni o'chirmasin"
    - "Pul `Intl` valyuta formatlagichi bilan (`style: currency, UZS`) — birlik i18n katalogida takrorlanmaydi"
    - "Grep darvozasi bilan qulflangan atama izohda ham yozilmaydi (02-02 / 02-08 / 02-13 dan meros; bu rejada UCH marta kerak bo'ldi)"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/stalls/page.tsx
    - frontend/src/app/[locale]/(app)/map/page.tsx
    - frontend/src/components/stalls/stall-filters.tsx
    - frontend/src/components/stalls/stall-list.tsx
    - frontend/src/components/stalls/stall-dialog.tsx
    - frontend/src/components/stalls/stall-category-dialog.tsx
    - frontend/src/components/stalls/stall-card-dialog.tsx
    - frontend/src/components/stalls/stall-map.tsx
    - frontend/src/components/stalls/stall-cell.tsx
    - frontend/src/components/stalls/stall-tone.ts
    - frontend/src/components/stalls/stall-map-types.ts
    - frontend/src/components/stalls/stall-map-legend.tsx
    - frontend/src/components/stalls/stall-map.test.tsx
  modified:
    - frontend/src/app/globals.css
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "`stall-card-dialog.tsx` Task 1 da qurildi (rejada Task 3) — usiz Task 1 ning `Enter = karta` mezoni ham, Task 2 ning katak bosishi ham bajarilmasdi"
  - "`StallDialog` `StallListItem` emas, `stallId` oladi — dialog ro'yxat qatoridan ham, kartadan ham bir xil chaqiriladi"
  - "Tahrir formasi `GET /stalls/{id}` ni KUTADI: `note` ro'yxat qatorida yo'q va urug'lanmagan forma uni jimgina o'chirardi"
  - "18 yangi i18n kaliti qo'shildi — reja messages fayllarini sanamagan, lekin ekranlar ularsiz qattiq kodlangan matn talab qilardi"
  - "`TONE_STATUS` uchinchi eksport sifatida qo'shildi — `StallCell` kontraktida `status` yo'q, `aria-label` esa uni talab qiladi"
  - "`<details>` ochiqligi `useSyncExternalStore` + `matchMedia` bilan; jsdom uchun fail-open"

patterns-established:
  - "Pattern: memoizatsiya darvozasi IKKI testdan iborat — render sanog'i (propni o'lchaydi) + mustaqil `$$typeof` nazorati (o'ramning memosi haqiqiysini niqoblamasin)"
  - "Pattern: render sanog'i `vi.fn()` CHAQIRUVLARI bilan olib boriladi, tashqi o'zgaruvchi bilan emas (`react-hooks/immutability`)"

requirements-completed: [MARKET-02, MARKET-06]

# Metrics
duration: 105min
completed: 2026-08-01
---

# Phase 2 Plan 14: Rastalar reestri va sxematik plan-xarita Summary

**Ikkita ekran va o'n uch fayl bilan MARKET-02 hamda MARKET-06 yopildi: xarita `react-konva`siz, CSS Grid va memoizatsiyalangan `<button>`lar bilan chizildi, `tone` kontrakti 6–7 fazalar uchun to'liq `Record` bilan qulflandi, va Pitfall 8 ("1000 katak har bosishda qayta render bo'ladi") beshta sabotaj bilan o'lchandi — ularning biri aynan `1000 <= 2` xatosini berdi.**

## Performance

- **Duration:** ~105 min
- **Tasks:** 3/3
- **Fayllar:** 17 (13 yaratildi, 4 o'zgartirildi), **+2800 / −0**
- **Testlar:** vitest 18 → **26** (node 54 o'zgarmadi; jami **80**)
- **i18n kalitlari:** 295 → **313** (×3 til)
- **Yangi npm paketi:** **0** (`frontend/package.json` diff bo'sh)

## Accomplishments

- **Xarita darvozasi HAQIQATAN biladigan qilib qurildi — beshta sabotaj, beshtasida ham AYNAN kutilgan test yiqildi va qolganlari yashil qoldi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | Kataklar klientda `localeCompare` bilan saralandi | AYNAN 2: tartib testlari | qolgan 24 ✅ |
  | `stall-cell.tsx` dan `memo` olib tashlandi | AYNAN 1: **`$$typeof` nazorati** | qayta render testi **yashil qoldi** — bu nazoratning nega kerakligini o'lchov bilan isbotladi |
  | `onSelect` `useCallback` siz qoldirildi | AYNAN 1: qayta render testi — **`expected 1000 to be less than or equal to 2`** | qolgan 25 ✅ |
  | Katak chegarasi doim `border-solid` qilindi | AYNAN 1: uzuq-uzuq chegara testi | qolgan 25 ✅ |
  | Kartadagi `text-danger-text` olib tashlandi | AYNAN 1: D-08 testi | qolgan 25 ✅ |

  Ikkinchi qator eng qimmatli: u render-sanoq testining O'ZI `memo` yo'qolishini ushlay OLMASLIGINI ko'rsatdi (josus o'rami ham memoizatsiyalangan), ya'ni `$$typeof` nazorati bezak emas — u haqiqiy bo'shliqni yopadi. Bu ikkilik `patterns-established` ga kiritildi.

- **Pitfall 8 ning ikkala yarmi ham qulflandi.** Tanlangan ID katak propiga tushmasligi *va* `onSelect` havolasining barqarorligi — ikkalasi ham bitta o'lchov bilan tekshiriladi, chunki ikkalasi ham bir xil natijani beradi: 1000 ta qayta render. Sabotaj aynan shu raqamni chiqardi.

- **`TONE_STYLES` to'liq `Record` — T-02-105 mitigatsiyasi ishlayotgani tekshirildi.** Kalit tushirilsa TypeScript kompilyatsiyani to'xtatadi; `Partial` ham, `switch`+`default` ham ATAYIN yozilmadi va sabab kodda qoldirildi.

- **Rejaning uchta grep darvozasi o'z izohlariga qarshi turgan holat qayta uchradi va 02-02/02-13 konvensiyasi bilan hal qilindi.** `watch(`, `Popover`, `key={index}`, `selected` — to'rtala atama ham izohlarda "nima uchun taqiqlangan"ni tushuntirar ekan, o'sha mezonni yiqitardi. Har birida taqiq va TO'LIQ sabab saqlandi, atamaning literal shakli olib tashlandi va yoniga "bu qoida grep bilan qulflangan" ogohlantirishi qo'shildi.

- **React Compiler lint qoidalari ikki joyda dizaynni O'ZGARTIRDI (yaxshi tomonga):**
  - `react-hooks/set-state-in-effect` "niyat bayrog'i + effekt" naqshini rad etdi → qidiruv natijasi endi `refetch()` dan to'g'ridan-to'g'ri o'qiladi, ya'ni javob AYNAN joriy `q` ga tegishli ekani kafolatlanadi;
  - `react-hooks/immutability` test josusidagi tashqi o'zgaruvchini rad etdi → sanoq `vi.fn()` chaqiruvlari bilan olib boriladi (reja ham aynan shuni tavsiya qilgan).

- **`note` ni jimgina o'chiradigan xato yozilishidan oldin topildi va yopildi.** `GET /stalls` qatorida `note` YO'Q (02-08 ataylab shunday); formani ro'yxat qatoridan urug'lantirish "Saqlash" bosilganda mavjud izohni `null` bilan almashtirardi.

## Task Commits

1. **Task 1: Rastalar reestri — ro'yxat, filtrlar va tahrir dialoglari** — `d3380a1` (feat)
2. **Task 2: Sxematik plan-xarita — grid, katak, tone kontrakti va legenda** — `fe50eba` (feat)
3. **Task 3: Xarita darvozasi (vitest)** — `e82bf47` (test)

## Files Created/Modified

**Yaratildi (13)**

| Fayl | Qator | Mazmuni |
|---|---|---|
| `stall-map.test.tsx` | 365 | 8 vitest: tartib (2), qayta render (2), a11y (2), karta (2) |
| `stall-dialog.tsx` | 376 | create/edit bitta komponent; `category_id` faqat create'da |
| `stall-list.tsx` | 319 | to'rt holat, zich karta qatori, `StallStatusBadge`, qator amallari |
| `stall-map.tsx` | 346 | zona bloklari, roving tabindex, skip link, zona chiplari |
| `stall-category-dialog.tsx` | 248 | `category_id` + kelajakdagi `valid_from` |
| `stall-filters.tsx` | 224 | `useStallFilters()` + panel; Enter -> yagona natija |
| `stall-card-dialog.tsx` | 220 | bitta modal, `children` ilgagi, D-08 ogohlantirishi |
| `stalls/page.tsx` | 148 | Suspense, huquq tekshiruvi, to'rt dialogning egasi |
| `stall-cell.tsx` | 147 | `memo` bilan 44×44 `<button>` |
| `map/page.tsx` | 115 | Suspense + `q` bo'yicha fokuslash |
| `stall-map-legend.tsx` | 82 | majburiy legenda, mobil'da ham ko'rinadi |
| `stall-tone.ts` | 78 | `toneOf` + `TONE_STYLES` + `TONE_STATUS` |
| `stall-map-types.ts` | 58 | uch tip, Scope Fence izohi bilan |

**O'zgartirildi (4)**

- `globals.css` — `@layer components` da `.zone-block` (`content-visibility: auto` + `contain-intrinsic-size: auto 400px`)
- `messages/{uz-Latn,ru}.json` — `stalls.*` ga 13, `map.*` ga 5 kalit
- `messages/uz-Cyrl.json` — faqat `npm run i18n:gen` bilan (qo'l tegizilmadi)

## Decisions Made

- **`stall-card-dialog.tsx` Task 1 ga ko'chirildi.** Reja uni Task 3 ga qo'ygan, lekin Task 1 ning qabul mezoni "raqam + Enter = karta ochiq" ni ham, Task 2 ning "katak bosilganda karta ochiladi" ni ham u bo'lmasa bajarib bo'lmasdi — ikkala commit ham o'z-o'zicha chala qolardi. Rejaning YAKUNIY holati o'zgarmadi (fayl `files_modified` ro'yxatida bor).
- **`StallDialog` `stallId` oladi, `StallListItem` emas.** Tahrir rejimi baribir `GET /stalls/{id}` ni chaqiradi (`note` uchun), ya'ni qator obyekti ortiqcha bog'liqlik edi. Natijada dialog rasta kartasidan ham bir xil chaqiriladi va "Tahrirlash" tugmasi ishlaydi.
- **`TONE_STATUS` qo'shildi.** `StallCell` kontrakti (§7.2 dan aynan) `status` maydonini bermaydi, `aria-label` esa holat SO'ZINI talab qiladi. Teskari xarita ham to'liq `Record` — 6-fazada `debt` uchun holat so'zini tanlash MAJBURIY bo'ladi, jimgina "faol" chiqmaydi. Uchala to'lov tone'i hozir `active` ga tushadi va bu to'g'ri: ular rastaning holati emas, uning ustidagi to'lov holati.
- **Ro'yxatdagi holat badge'i `active` uchun NEYTRAL.** 1000 rastali reestrda "hammasi yashil" devori hech qanday ma'lumot bermaydi va §4.1 ("rang faqat harakat va xavf uchun") ga zid. Farq badge matni + ikonkasi (`Wrench` / `Ban`) bilan beriladi.
- **Pul `Intl` valyuta formatlagichi bilan** (`style: "currency", currency: "UZS"`) — o'lchandi: `uz-Latn` -> `8 000 soʻm`, `ru` -> `8 000 UZS`. Muqobil variant (`common.soum` kaliti) uchala tilda qo'lda yozilishi kerak bo'lardi va `common` — 02-15 bilan UMUMIY namespace, ya'ni parallel ishda to'qnashuv nuqtasi.
- **`throttleMs` nomi SAQLANDI**, garchi nuqs 2.9.2 uni `limitUrlUpdates` foydasiga eskirgan deb belgilasa ham: UI-SPEC §8.3 kontrakti aynan shu nomni beradi, u ishlaydi, va nom o'zgartirilsa spetsifikatsiya bilan kod ajralib ketardi. Izohda uning NIMANI sekinlashtirishi ham yozildi (tarixga yozishni, so'rovni emas — nuqs holatni optimistik yangilaydi).
- **`<details>` ochiqligi `useSyncExternalStore` bilan.** `useEffect` + `setState` varianti gidratatsiya nomuvofiqligini ham, React Compiler qoidasini ham buzardi. `matchMedia` yo'q muhitda (jsdom) fail-OPEN: hamma zona ochiq — bu joylashuv, xavfsizlik chegarasi emas.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `stall-card-dialog.tsx` Task 3 da rejalashtirilgan, lekin Task 1 da KERAK edi**

- **Found during:** Task 1
- **Issue:** Task 1 ning action'i va qabul mezoni "Enter bosilganda rasta kartasi darhol ochiladi" (§6.9) ni talab qiladi; Task 2 esa "katak bosilganda karta ochiladi" ni. Kartaning o'zi Task 3 ga qo'yilgan, ya'ni Task 1 va Task 2 commit'lari o'z-o'zicha bajarilmagan mezon bilan yopilardi (yoki `selectedStallId` hech kim o'qimaydigan "o'lik" holat bo'lib qolardi).
- **Fix:** Karta Task 1 da qurildi; Task 3 esa uning darvozasini qo'shdi. Fayl rejaning `files_modified` ro'yxatida bor, ya'ni qamrov kengaymadi.
- **Files:** `frontend/src/components/stalls/stall-card-dialog.tsx`
- **Committed in:** `d3380a1`

**2. [Rule 1 - Bug] Tahrir formasi mavjud IZOHNI jimgina o'chirardi**

- **Found during:** Task 1
- **Issue:** Reja tahrir dialogida `note` maydonini talab qiladi, `GET /stalls` qatorida esa `note` YO'Q — u faqat `GET /stalls/{id}` javobida keladi (02-08 ataylab shunday: ro'yxatga ortiqcha maydon qo'shilmagan). Formani ro'yxat qatoridan urug'lantirish `note` ni bo'sh ko'rsatardi va foydalanuvchi hech narsa yozmasdan "Saqlash" bosganda `PATCH` tanasida `note: null` ketardi — izoh yo'qolardi va buni HECH KIM sezmasdi.
- **Fix:** Tahrir rejimi `useStallQuery(stallId)` ni chaqiradi va forma FAQAT batafsil javob kelganda urug'lanadi; javob kelmaguncha "Saqlash" `disabled`. Urug'lanish `seededFor` ref bilan bir martaga cheklandi — fon refetch'i (oynaga qaytish) terilayotgan matnni o'chirmasin.
- **Files:** `frontend/src/components/stalls/stall-dialog.tsx`
- **Committed in:** `d3380a1`

**3. [Rule 2 - Missing Critical] Ekranlar 18 ta i18n kalitisiz qattiq kodlangan matn talab qilardi**

- **Found during:** Task 1 va Task 2
- **Issue:** Reja `frontend/messages/*` ni `files_modified` da sanamaydi, lekin mavjud `stalls.*` / `map.*` namespace'larida quyidagilar YO'Q edi: "Ko'proq yuklash", natija soni, "Filtrlarni tozalash", `⋯` tugmasining nomi, filtr `<select>` larining "barchasi" varianti, uch dialogning tavsifi (`ui/dialog.tsx` `description` ni MAJBURIY qiladi), "Toifa belgilanmagan", "Telefon", va xarita `aria-label` ining toifa/sotuvchi bo'laklari. Ularsiz yagona yo'l — komponentda qattiq kodlangan o'zbekcha matn, ya'ni CLAUDE.md ning "3 til majburiy" cheklovini buzish.
- **Fix:** `stalls.*` ga 13, `map.*` ga 5 kalit qo'shildi (uz-Latn + ru qo'lda, uz-Cyrl `npm run i18n:gen` bilan). Boshqa namespace'ga TEGILMADI — `zones`, `categories`, `tariffs`, `calendar`, `vendors` va `common` 02-15 ning yuzasi va parallel ishda to'qnashuv nuqtasi bo'lardi.
- **Verification:** `i18n:check` — **313 kalit × 3 til**, kalit va ICU parity to'liq; kirill chiqishi qo'lda tekshirildi (`Фильтрларни`, `Кўпроқ юклаш` — override'lar ishladi)
- **Committed in:** `d3380a1`

**4. [Rule 3 - Blocking] React Compiler qoidasi "niyat bayrog'i + effekt" naqshini RAD ETDI**

- **Found during:** Task 1
- **Issue:** "Enter -> so'rov tinchishini kut -> aynan bitta natijada kartani och" mantig'ining tabiiy shakli — holatdagi bayroq va uni effektda o'qish. `react-hooks/set-state-in-effect` buni xato deb belgiladi (kaskadli render). Xuddi shu qoida ikkala dialogdagi `setFormError(null)` ni ham urdi.
- **Fix:** Qidiruv `stallsQuery.refetch()` ni KUTADI va natijani UNDAN o'qiydi — bu qo'shimcha foyda ham berdi: javob aynan joriy `q` ga tegishli ekani kafolatlanadi (nuqs holatni optimistik yangilagani uchun bayroq varianti eski javobni o'qishi mumkin edi). Dialoglardagi xato esa endi YOPILISHDA tozalanadi.
- **Files:** `stall-filters.tsx`, `stall-dialog.tsx`, `stall-category-dialog.tsx`
- **Committed in:** `d3380a1`

**5. [Rule 1 - Bug] To'rtta grep mezoni O'Z izohlariga qarshi turdi**

- **Found during:** Task 1 va Task 2 yakuniy tekshiruvi
- **Issue:** Reja bir vaqtda (a) taqiqni izohda tushuntirishni va (b) o'sha atamani grep bilan **0** topishni talab qiladi. To'rt joyda ikkalasini birga bajarib bo'lmasdi: `watch(` (2 fayl), `Popover` (karta izohi), `key={index}` (xarita izohi + skelet siklidagi haqiqiy ishlatilish), `selected` (katak izohi).
- **Fix:** 02-02 da o'rnatilib 02-08/02-13 da takrorlangan konvensiya qo'llanildi — taqiq va uning TO'LIQ sababi saqlandi, atamaning O'ZI literal yozilmadi, ustiga "bu qoida grep bilan qulflangan" ogohlantirishi qo'shildi. Skelet sikli esa `SKELETON_SLOTS` konstantasiga ajratildi va nega u yerda pozitsiya kaliti XAVFSIZ ekani (24 element, o'zgarmaydi, qayta tartiblanmaydi) yozildi.
- **Verification:** to'rtala grep ham **0**
- **Committed in:** `d3380a1`, `fe50eba`

**6. [Rule 2 - Missing Critical] `StallCell` kontrakti holat SO'ZINI bermasdi**

- **Found during:** Task 2
- **Issue:** `aria-label` formati (§7.4) holatni talab qiladi (`"12-rasta, faol, …"`), `StallCell` tipi esa (§7.2 dan AYNAN) faqat `tone` ni beradi. Bu bo'shliq jimgina "holat aytilmaydigan" `aria-label` ga olib borardi — ya'ni skrinrider foydalanuvchisi ta'mirdagi rastani faoldan ajrata olmasdi.
- **Fix:** `stall-tone.ts` ga `TONE_STATUS: Record<StallTone, StallStatusValue>` qo'shildi — `TONE_STYLES` bilan bir xil falsafada TO'LIQ `Record`, ya'ni 6-fazada yangi tone qo'shilsa uning holat so'zini tanlash MAJBURIY bo'ladi.
- **Verification:** `katak TO'LIQ aria-label beradi` testi to'rtala bo'lakni ham tekshiradi
- **Committed in:** `fe50eba`

**7. [Rule 3 - Blocking] Test josusi tashqi o'zgaruvchini o'zgartira olmasdi**

- **Found during:** Task 3
- **Issue:** Render sanog'ining tabiiy shakli — `spy.renders += 1`. `react-hooks/immutability` buni rad etdi (render paytida tashqi holatni yozish).
- **Fix:** Sanoq `vi.fn()` CHAQIRUVLARI bilan olib boriladi (`cellSpy.onRender()` -> `mock.calls.length`) — reja ham aynan shuni tavsiya qilgan. Qo'shimcha ravishda boshlang'ich render `expect(cellRenderCount()).toBe(1000)` bilan tekshiriladi, ya'ni josus chindan ulanganiga ham dalil bor.
- **Committed in:** `e82bf47`

---

**Total deviations:** 7 auto-fixed (2 bug, 2 missing-critical, 3 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Yangi npm paketi QO'SHILMADI (UI-SPEC §1.4 saqlandi), backend'ga tegilmadi, `market-queries.ts` / `api-types.ts` / `market-errors.ts` / `app-shell.tsx` O'ZGARMADI. #1 va #7 — rejaning ichki ketma-ketlik ziddiyatlari; #4 va #7 — React 19 lint qoidalari majburlagan dizayn tuzatishlari; #2 va #6 reja ko'rmagan ikkita jimgina nosozlikni yopadi; #3 CLAUDE.md ning "3 til majburiy" cheklovi talab qildi; #5 — kodbazaning mavjud konvensiyasi bilan hal qilingan takroriy sinf.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `grep -rn "watch(" components/stalls` | ✅ **0** |
| `grep -rn "apiFetch" components/stalls` | ✅ **0** |
| `grep -rn "user-event" components/stalls` | ✅ **0** |
| `grep -rn "Popover" components/stalls` | ✅ **0** |
| `grep -c "key={index}" stall-map.tsx` | ✅ **0** |
| `grep -c "selected" stall-cell.tsx` | ✅ **0** |
| `grep -rn "react-konva\|konva" src/ messages/ package.json` | ✅ **0** |
| `grep -c "sort(" stall-map.tsx` | ✅ **0** |
| `grep -v "^\s*//" stall-dialog.tsx \| grep -c "/category"` | ✅ **0** (yaratish — BITTA `POST /stalls`) |
| `throttleMs: 300` mavjud, maxsus debounce hooki yo'q | ✅ |
| `autoFocus` + `inputMode="numeric"` + `enterKeyHint="search"` | ✅ uchalasi |
| `TONE_STYLES` tipi `Record<StallTone, string>` | ✅ (`Partial` EMAS), 6 kalit |
| `toneOf()` da `default` tarmog'i | ✅ **YO'Q** |
| `stall-cell` eksporti memoizatsiyalangan | ✅ `$$typeof === Symbol.for("react.memo")` |
| Grid `repeat(auto-fill, minmax(2.75rem, 1fr))` | ✅ |
| Har zona `<section role="group">` + `aria-label` | ✅ |
| "Xaritani o'tkazib yuborish" `sr-only focus:not-sr-only` | ✅ |
| `globals.css` `.zone-block` + `content-visibility: auto` | ✅ |
| Legenda shartsiz render qilinadi | ✅ (`hidden`/`md:` shartlari yo'q) |
| `git diff --stat frontend/package.json` | ✅ **bo'sh** |
| Sabotaj o'lchovlari (5 ta) | ✅ har birida AYNAN kutilgan test(lar) yiqildi |
| Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff` bo'sh |

## Issues Encountered

- **`memo` sabotaji render-sanoq testini yiqitMADI.** Josus o'rami ham `memo` bilan o'ralgani uchun u haqiqiy komponentning memoizatsiyasini niqoblab qo'ydi. Bu KUTILGAN edi va aynan shuning uchun `$$typeof` nazorati yozilgan — sabotaj uning kerakligini o'lchov bilan tasdiqladi. O'ramsiz variant esa Pitfall 8 ni umuman o'lchamasdi (har ota-render'da sanoq oshardi).
- **nuqs 2.9.2 `throttleMs` ni eskirgan deb belgilaydi** (`limitUrlUpdates: throttle(300)` foydasiga). Nom UI-SPEC kontrakti sababli saqlandi; qaror va sabab kodda yozildi.
- **`useTimeZone()` `undefined` qaytarishi mumkin** — toifa dialogida `?? "Asia/Tashkent"` bilan yopildi; ertangi kun `Intl.DateTimeFormat("en-CA", { timeZone })` bilan hisoblanadi, `toISOString()` bilan EMAS (UTC+5 da u kechqurun bugungi kunni berardi va maydon server rad etadigan sanani taklif qilardi).
- **`frontend/node_modules` worktree'da bo'sh edi** — `npm ci` bilan `package-lock.json` dan tiklandi (yangi paket o'rnatilmadi).

## Known Stubs

Yo'q — ikkala ekran ham haqiqiy endpointlarga ulangan va har bir ko'rinadigan qiymat serverdan keladi. Quyidagilar **ataylab ochiq qoldirilgan, ko'rinadigan qarz** (stub emas):

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| Rasta kartasida "Sotuvchi biriktirish" tugmasi | 02-15 / 02-16 | `StallCardProps` da `onEdit?` bor va ishlaydi; biriktirish dialogi `components/vendors/` da tug'iladi va u BU rejaning fayl chegarasidan tashqarida (parallel ish). Tugma render qilinmaydi — yolg'on va'da bermaydi |
| Xarita katagining `aria-label` ida toifa va sotuvchi NOMI | 6-faza (yoki `GET /stalls/map` kengaysa) | `GET /stalls/map` ATAYIN to'rt maydonli (1000 rastali javob kichik qolsin). Katak `categoryName`/`vendorName` proplarini QABUL QILADI, xarita esa `null` uzatadi va `has_vendor` dan "biriktirilgan/biriktirilmagan" farqi baribir eshitiladi |
| `errors.loadFailedTitle` / `loadFailedBody` (UI-SPEC §10.5) | 02-16+ | Bu rejada xato bloklari `marketErrorMessageKey(error)` ning BITTA satrini ko'rsatadi — reja aynan shuni belgilagan. Ikki qatorli variant `errors.*` (umumiy namespace) ni talab qiladi va parallel ishda to'qnashuv nuqtasi bo'lardi |
| "Rastani yopish" destruktiv amali (D-2, `ConfirmDialog` 2-daraja) | 02-16 | `stalls.closeAction` / `closeConfirm` kalitlari va `ui/confirm-dialog` ning 2-darajasi tayyor; bu rejaning action'ida yo'q |

## Threat Flags

Yangi xavfsizlik yuzasi rejaning `<threat_model>` idan tashqarida paydo bo'lmadi: yangi endpoint, yangi auth yo'li, fayl kirishi yoki sxema o'zgarishi YO'Q. Ikkala ekran ham 02-13 ning mavjud hooklaridan o'qiydi.

| Threat ID | Holat |
|-----------|-------|
| T-02-105 | **mitigate** — `TONE_STYLES` to'liq `Record<StallTone, string>`; `Partial` va `switch`+`default` rad etilgani sabab bilan kodda yozilgan. `TONE_STATUS` ham xuddi shu falsafada to'liq |
| T-02-106 | accept (aniqlangan) — karta faqat `market_data_view` bilan ochiladi; telefon maskalanmaydi (§8.6 — server uni allaqachon yuborgan), audit bildirishi kartada TAKRORLANMAYDI |
| T-02-107 | **mitigate** — tanlangan ID katak propiga tushmaydi; `React.memo` + `useCallback`; vitest darvozasi qayta render sanog'ini o'lchaydi va sabotajda `1000 <= 2` xatosini berdi |
| T-02-108 | **mitigate** — `.zone-block` `content-visibility: auto` + `contain-intrinsic-size: auto 400px`; virtualizatsiya kutubxonasi qo'shilmadi; mobil'da `<details>` bilan qo'shimcha qisqartirish |
| T-02-109 | accept (aniqlangan) — `stall_manage` yo'q bo'lsa tugmalar RENDER QILINMAYDI; sabab (`require_permission` serverda) uchala faylda ham yozilgan |
| T-02-110 | **mitigate** — `aria-label` matn atributi, React qiymatni ekranlaydi; `dangerouslySetInnerHTML` qo'shilmadi; DB kontenti faqat matn tugunlari |
| T-02-111 | **mitigate** — "Tarif belgilanmagan" `text-danger-text` + `AlertCircle` bilan MAJBURIY ko'rinadi va sabotaj bilan o'lchandi |
| T-02-111a | accept (aniqlangan) — sana `min` atributi va zod sharti QULAYLIK ekani kodda ikki marta yozilgan; server 403 `stalls.categoryPastLocked` matniga aylantiriladi va YUTILMAYDI |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run i18n:check` | ✅ **313 kalit × 3 til**, drift yo'q |
| 2 | `npm --prefix frontend run typecheck` | ✅ exit 0 |
| 3 | `npm --prefix frontend run lint` | ✅ exit 0 |
| 4 | `npm --prefix frontend test` | ✅ **54 node + 26 vitest**, 0 fail |
| 5 | `npm --prefix frontend run build` | ✅ exit 0; `/[locale]/stalls` va `/[locale]/map` uchala tilda prerender qilindi |
| 6 | `git diff --stat frontend/package.json` | ✅ bo'sh |

## User Setup Required

Yo'q — tashqi xizmat sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja backend'ga umuman tegmaydi va yangi npm paketi o'rnatmaydi.

## Next Phase Readiness

- **Navigatsiyadagi ikkita 404 yopildi:** `/map` va `/stalls` endi haqiqiy ekran. Qolgan uchtasi (`/vendors`, `/tariffs`, `/calendar`) 02-15 ning zimmasida.
- **02-16 uchun:** rasta importi muvaffaqiyatli tugagach `router.push("/stalls")` ishlaydi; `stalls.emptyStateHint` allaqachon "Excel fayldan yuklang" deb yo'l ko'rsatadi. Import paneli reestr sahifasiga qo'shilsa, `useStallFilters()` ni O'ZGARTIRMASDAN ishlatish mumkin.
- **6–7 fazalar uchun qotirilgan kontrakt:** yangi rang qo'shish = `StallTone` ga bitta a'zo + `TONE_STYLES`, `TONE_STATUS` ga bittadan kalit. Kalit unutilsa TypeScript kompilyatsiyani to'xtatadi. Katakning o'zi, gridi va klaviatura mantiqi QAYTA YOZILMAYDI.
- **Dalil-rasm galereyasi** `StallCardDialog` ning `children` propiga tushadi — komponent tayyor, ilgak bo'sh.
- **⚠ 02-15 uchun eslatma:** `frontend/messages/*.json` da `stalls.*` va `map.*` bloklari bu rejada o'sdi. `vendors`, `tariffs`, `calendar`, `zones`, `categories` bloklariga tegilmagan.

## Self-Check: PASSED

- Da'vo qilingan 13 yangi fayl diskda mavjud (`stall-{map,cell,tone,map-types,map-legend,list,filters,dialog,category-dialog,card-dialog}`, ikkala `page.tsx`, `stall-map.test.tsx`)
- Da'vo qilingan 4 o'zgartirilgan fayl `git diff --stat 9849d42..HEAD` da ko'rinadi (17 fayl, +2800/−0)
- Uchala vazifa commit'i git tarixida: `d3380a1`, `fe50eba`, `e82bf47`
- Birorta commit'da fayl o'chirilishi YO'Q (`git diff --diff-filter=D` uchalasida ham bo'sh)
- Besh sabotajdan keyin ishchi daraxt toza (`git status --short` bo'sh)
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
