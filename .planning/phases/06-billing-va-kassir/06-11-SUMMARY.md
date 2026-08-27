---
phase: 06-billing-va-kassir
plan: 11
subsystem: ui
tags: [nextjs, react, tanstack-query, zod, idempotency, a11y, i18n, vitest]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`api-types.ts` dagi to'rt reyestr ko'zgusi, `billing-errors.ts` (14 kod), `rbac.ts` da `payment_create`, uchala locale'dagi `collect.*` matni, `NAV_ITEMS` ning ikki yozuvi"
  - phase: 06-billing-va-kassir
    plan: 03
    provides: "`billing-pending-queries.ts` (`pendingStallSchema`, `usePendingStall`, `dropPendingAfterPayment`), `payment-queries.ts` (`usePayment`, `useReversePayment`, `useRecentPayments`), `shift-queries.ts` (`useOpenShift`), `collect-surface.test.mjs`"
  - phase: 06-billing-va-kassir
    plan: 08
    provides: "`GET /billing/pending` ning IKKI shakli (tekis `PendingStallResponse` / ko'p moslikda `PendingLookupResponse`), `{day, rows, hisoblagichlar}` o'ramlari"
  - phase: 06-billing-va-kassir
    plan: 09
    provides: "`POST /payments` kontrakti — so'rov maydoni `reason_code`, `shift_id` SO'ROVDA YO'Q (server o'zi yechadi)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`blind-session.tsx` ning `useRef` qulfi, `decision-bar.tsx` ning `event.repeat` qoidasi, `bulk-action-surface.test.mjs` ning e'londan hosila qamrovi"
provides:
  - "`app/[locale]/(app)/collect/page.tsx` — Y-1 sahifasi, RBAC ko'zgusi va `<CollectSession />` ning HAQIQIY render'i"
  - "`components/collect/` — olti mahsulot komponenti (`collect-session`, `stall-lookup`, `pending-card`, `payment-bar`, `reason-dialog`, `payment-row`)"
  - "G-20 (`collect-session.test.tsx`) — DOM'dan HOSILA qadam sanog'i: 3 / 4 / 3"
  - "G-21 (`payment-bar.test.tsx`) — dublikat qulfining uchala kanali + kalit almashuvi"
  - "G-23(a) (`pending-card.test.tsx`) va G-24 ning DOM yarmi (`reason-dialog.test.tsx`)"
  - "⛔ G-18 e'loni kengaydi: `05-UI-SPEC.md` §15 ga uchinchi naqsh (`components/collect/**`) — birinchi mahsulot fayli bilan BITTA commitda"
  - "⛔ 06-03 ning uchta klient sxemasi serverga MOSLANDI (`deferred-items.md` 2-qatori yopildi) va to'rt reyestr nusxasi `api-types.ts` ga yig'ildi"
affects: [06-12, 06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Qadam identifikatori (`data-collect-step`) EGASI ota-komponentda hal qilinadi (`ownsStep` propi), atribut esa bolada chiziladi — DOM'da har lahzada AYNAN BITTA element"
    - "Sanoq testi DOM'dan HOSILA: element O'ZI qanday ta'sir kutayotganini `[data-collect-option]` bilan aytadi, test esa turlar ro'yxatini YOZMAYDI"
    - "Sikl oraliq holatda harakat qilmaydi: `isFetching`/`isMutating` nolga tushguncha kutiladi — aks holda ko'p moslikda ro'yxat yopilib, kod QAYTA terilardi"
    - "Idempotentlik kaliti URUG'DAN hosila (`rasta|summa|tur`) va render fazasida sinxronlanadi — §8.7 jadvalining yettala hodisasi bitta ifodadan chiqadi"
    - "Ixtiyoriy callback = affordansning MAVJUDLIK sharti: prop berilmasa tugma UMUMAN chizilmaydi (`disabled` emas), ya'ni keyingi taskda ulanadigan yuza oldindan yolg'on gapirmaydi"
    - "Mutatsiya QULF bilan bir joyda yashaydi: `useRef` qulfi ota-komponent orqali render aylanishiga bog'lanmaydi"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/collect/page.tsx
    - frontend/src/components/collect/collect-session.tsx
    - frontend/src/components/collect/stall-lookup.tsx
    - frontend/src/components/collect/pending-card.tsx
    - frontend/src/components/collect/payment-bar.tsx
    - frontend/src/components/collect/reason-dialog.tsx
    - frontend/src/components/collect/payment-row.tsx
    - frontend/src/components/collect/collect-session.test.tsx
    - frontend/src/components/collect/payment-bar.test.tsx
    - frontend/src/components/collect/pending-card.test.tsx
    - frontend/src/components/collect/reason-dialog.test.tsx
  modified:
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-UI-SPEC.md
    - frontend/src/lib/billing-pending-queries.ts
    - frontend/src/lib/billing-charge-queries.ts
    - frontend/src/lib/payment-queries.ts
    - .planning/phases/06-billing-va-kassir/deferred-items.md

key-decisions:
  - "06-11: §8.2 FLAG'i YOPILDI — ko'p moslikda qadam IDENTIFIKATORI `\"stall\"` bo'lib qoladi va sanoq 4 ni ko'rsatadi; qo'shimcha o'zaro ta'sir yashirilmaydi, SON bilan aytiladi"
  - "06-11: qadam elementining EGASI shart bilan almashadi — `fieldset` faqat to'lov turi tanlanmaganda, tasdiq tugmasi faqat tanlangandan keyin `data-collect-step` oladi; aks holda DOM'da ikkita element bo'lardi va §8.2 invarianti buzilardi"
  - "06-11: `payment-bar` mutatsiyani O'ZI egallaydi (qulf va `onError` bir joyda); spinner ALOHIDA lokal bayroqdan chiziladi va so'rov holatining bayrog'i bu faylda umuman o'qilmaydi (05-13 darsi)"
  - "06-11: G-21 ning (c) va (d) kanallari `CollectSession` orqali o'lchanadi — qotirilgan kalit propiga qarshi «kalit saqlanadimi?» degan da'vo TAVTOLOGIYA bo'lardi"
  - "06-11: `[Qarzni ham olish]` va DL-1 summani SESSIYA holatiga qaytaradi; klientda `bugungi + qarz` HISOBLANMAYDI — `total_due_soum` serverdan"
  - "06-11: yangi tarjima kaliti QO'SHILMADI (06-02 egaligi) — «Rasta topilmadi» e'loni `collect.errorCause.stall_not_found` dan, `no-shift` bo'sh holati esa `errorCause/errorFix.no_open_shift` juftligidan chiziladi"
  - "06-11: 06-03 ning uchala eskirgan klient sxemasi serverga MOSLANDI (server yarmi 06-08 da testlar bilan qulflangan va uni `{items}` ga qaytarish D-05 ni buzardi)"

patterns-established:
  - "Ko'p bosiladigan yuzada affordans BERILGANDA chiziladi, `disabled` holida turmaydi — prop ixtiyoriyligi kompozitsiya tartibini ham mexanik qiladi"
  - "Xulq testida `role` bo'yicha izlash MATN bo'yicha izlashdan ustun: ayni satr dialog tavsifida ham bo'lishi mumkin va da'vo KANAL haqida edi"
  - "Reyestrdan iteratsiya + to'plam tengligi: `<option>` lar `api-types.ts` dan chiqadi, test esa `Set` tengligi bilan o'lchaydi (D-31/D-32 juftligi)"

requirements-completed: [BILL-05, CASH-01, CASH-02, CASH-03]

# Metrics
duration: 80min
completed: 2026-08-11
---

# Phase 6 Plan 11: Kassir yig'ish ekrani Summary

**Yetti fayl, uch commit va bitta son: sahifa ochilishidan `POST /payments` gacha AYNAN 3 o'zaro ta'sir — ikkinchi takrorda ham 3, ko'p moslikda esa 4, ya'ni §8.2 ning ochiq FLAG'i «qadam turini ko'paytirish» bilan emas, SANOQNI KO'RINADIGAN qilish bilan yopildi; uch tez bosish esa bitta so'rov yuboradi va 5xx dan keyingi qayta yuborish AYNI kalit bilan ketadi.**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-08-11T03:46:00Z
- **Completed:** 2026-08-11T05:05:00Z
- **Tasks:** 3 (+ 1 kechiktirilgan bandlar commit'i)
- **Files modified:** 16 (11 yangi, 5 kengaytirilgan)

## Accomplishments

- **D-18 SON bilan o'lchandi va sanoq DOM'DAN HOSILA.** `collect-session.test.tsx` ning sikli har iteratsiyada `[data-collect-step]` uzunligini **1** deb tasdiqlaydi, elementning O'ZIDAN qaysi qadam ekanini o'qiydi va unga `[data-collect-option]` bo'yicha ta'sir qiladi. Natija: baxtli yo'l **3**, ko'p moslik **4**, ikkinchi takror yana **3**. Kutilgan ro'yxat testda yozilgan, kuzatilgan ro'yxat esa **DOM'dan** yig'ilgan.
- **§8.2 ning ochiq FLAG'i rejadagi qaror bilan yopildi va u xulqda o'lchandi.** Ko'p moslikda qadam **identifikatori** `"stall"` bo'lib qoladi (atribut ro'yxat konteyneriga ko'chadi), ya'ni `new Set(visited)` ikkala yo'lda ham **AYNAN** `{stall, method, confirm}`.
- **D-22 uchala kanalda o'lchandi** — uch tez bosish → **1** so'rov; `Enter` ni bosib turish (`repeat: true` ×3) → **0** so'rov (yonida NAZORAT: bir marta bosilgan `Enter` → **1** so'rov); 5xx → `[Qayta yuborish]` → **2-chi** so'rov va **AYNI** `idempotency_key`. To'rtinchi kanal — summa o'zgargach kalit **boshqa** bo'lishi — ham qo'shildi.
- **§9.4 ning uch qatlami qurildi va ikkinchisi XULQ bilan o'lchandi.** Server javobidagi kod kiritilgan koddan farq qilsa summa **chizilmaydi** (`Skeleton`) — bu shart kesh siyosatidan mustaqil, ya'ni `gcTime` bir kun oshirilsa ham tirik qoladi.
- **D-19 DOM darajasida bajarildi.** DL-1/DL-2 da `<textarea>` **0**, `input[type="text"]` **0**; `<option>` qiymatlari to'plami `api-types.ts` reyestriga **TENG** (`Set` tengligi bilan), `other`/`custom` **yo'q**.
- **⛔ OP-5 bajarildi va TUZOQQA TUSHILMADI.** `05-UI-SPEC.md` §15 ning G-18 qatoriga uchinchi naqsh **birinchi `components/collect/*.tsx` bilan bitta commitda** qo'shildi (`61a8853`); `06-UI-SPEC.md` ga G-18 qatori **yozilmadi** (`grep -cE "^\| \*\*G-18\*\* \|"` → **0**), ya'ni `SPEC_FILES.length === 1` sharti buzilmadi.
- **§8.8 ning ikonka FLAG'i yopildi:** to'lov turi **ikki kanalda** — ikonka **va** ko'rinadigan matn. `aria-label` yetarli deb qabul qilinmadi va sabab komponent docstringida: to'lov turi — **ma'lumot**, holat emas, ya'ni ko'zi ojiz bo'lmagan foydalanuvchi uchun `aria-label` **mavjud emas**.
- **⛔ KOMPOZITSIYA KONTRAKTI BAJARILDI.** `page.tsx` T2 da `<CollectSession />` ni **haqiqatan** chizdi, `collect-session.tsx` T2 da uchta, T3 da ikkita bolasini ulandi. **Oldinga murojaat hech qayerda yo'q** (T1 da `CollectSession` → 0; T2 da `ReasonDialog`/`PaymentRow` → 0).
- **Uchala kechiktirilgan band bajarildi** (pastdagi alohida bo'limga qarang), shu jumladan `deferred-items.md` ning **2-qatori yopildi**.
- **Yangi paket o'rnatilmadi** (T-06-SC): `crypto.randomUUID()` native, native `<select>`, `useFormatter().number()`. Yangi `ui/` primitivi ham **qurilmadi** (M-2).

## Task Commits

1. **Kechiktirilgan bandlar: reyestr ko'zgulari va klient o'ramlari** — `66aa7dc` (refactor)
2. **Task 1: sahifa qobig'i, navigator, proyeksiya kartasi va G-18 e'loni** — `61a8853` (feat)
3. **Task 2: qadam mashinasi, `useRef` qulfi va sahifa kompozitsiyasi** — `8c1447a` (feat)
4. **Task 3: DL-1/DL-2, to'lov qatori va ikkala bolaning ulanishi** — `273a9c0` (feat)

## Files Created/Modified

**Yangi (11):**

- `frontend/src/app/[locale]/(app)/collect/page.tsx` (126) — RBAC ko'zgusi, sarlavha, `/collect/shift` havolasi, `Suspense` ichida `<CollectSession />`.
- `frontend/src/components/collect/collect-session.tsx` (442) — to'qqiz holat (`collectState()` sof funksiya), kalit urug'i, §8.5 fokus qaytishi, beshala bolaning kompozitsiyasi.
- `frontend/src/components/collect/stall-lookup.tsx` (182) — navigator: `enterKeyHint="go"`, `inputMode="numeric"`, matn turi, 56px, ko'p moslik ro'yxati.
- `frontend/src/components/collect/pending-card.tsx` (299) — §9.3 ning 1–5 kanali, moslik sharti, nomlangan sabablar, avans, `[Qarzni ham olish]`.
- `frontend/src/components/collect/payment-bar.tsx` (296) — radiogroup, 56px aksent tasdiq, `useRef` qulfi, `event.repeat`, xato bloki + `[Qayta yuborish]`.
- `frontend/src/components/collect/reason-dialog.tsx` (259) — DL-1 va DL-2 bitta komponentda, reyestrdan iteratsiya, erkin matn yuzasi **nol**.
- `frontend/src/components/collect/payment-row.tsx` (136) — §8.8: ikki kanalli to'lov turi, `[Bekor qilish]`, yig'indi **yo'q**.
- To'rt test fayli (`collect-session` 370, `payment-bar` 358, `pending-card` 346, `reason-dialog` 212).

**Kengaytirilgan (5):**

- `.planning/phases/05-.../05-UI-SPEC.md` — G-18 qatoriga **bitta** naqsh (+ sabab jumlasi).
- `frontend/src/lib/billing-pending-queries.ts` (+~90) — `pendingLookupSchema`, `pendingLookupResponseSchema`, `normalizePendingLookup()`.
- `frontend/src/lib/billing-charge-queries.ts` — reyestr importlari + ikki o'ramning serverga moslanishi.
- `frontend/src/lib/payment-queries.ts` — reyestr importlari (tip aliaslari saqlandi).
- `.planning/phases/06-billing-va-kassir/deferred-items.md` — 2-qator **yopildi**, uchta yangi band (4, 5, 6).

## ⛔ Kechiktirilgan uchala band — BAJARILDI

| # | Band | Natija |
|---|------|--------|
| **1** | Enum ko'zgulari 06-03 ning so'rov modullaridan `api-types.ts` ga ko'chsin | ✅ `PAYMENT_METHODS`, `REVERSAL_REASONS` (`payment-queries.ts`) va `ANOMALY_KINDS`, `ADJUSTMENT_REASONS` (`billing-charge-queries.ts`) ning **vaqtinchalik `as const` nusxalari o'chirildi**; qiymat manbai endi AYNAN G-24/G-26 o'lchaydigan fayl. ⛔ Tip aliaslari (`PaymentMethod`, `ReversalReason`, `AnomalyKind`, `AdjustmentReason`) **saqlandi** — modullarning omma yuzasi o'zgarmadi, ya'ni iste'molchilar qayta yozilmadi. `billing-copy.test.mjs` **yashil** (§5.10 to'plam tengligi) |
| **2** | W0-F6 — `05-UI-SPEC.md` §15 ning G-18 qatoriga `components/collect/**` | ✅ **`61a8853` da**, birinchi `components/collect/*.tsx` bilan **BITTA commitda**. ⚠ Birinchi urinishda naqsh **ikki marta** yozildi (izohda ham backtick bilan) va `bulk-action-surface.test.mjs` ni **darhol qizartirdi** («takrorlangan katalog naqshi: 4 ≠ 3») — ya'ni darvoza o'z ishini qildi; izoh backticksiz qayta yozildi |
| **3** | Klient envelopelari server kontraktidan orqada | ✅ Uchalasi ham moslandi: `chargeListSchema` → `{day, rows, charge_count, charged_soum}`, `anomalyListSchema` → `{day, rows, unassigned_count, closed_day_count, no_coverage_count}`, va **yangi** `pendingLookupSchema` + `pendingLookupResponseSchema` (birlashma) + `normalizePendingLookup()`. ⛔ Server **TEGILMADI** (`git diff --numstat services/` → bo'sh). ⚠ 06-13 uchun aniq eslatma `deferred-items.md` ning **4-qatorida** |

⚠ **Nega uchinchi band 06-13 ga qoldirilmadi:** 06-13 ning `files_modified` ida `billing-charge-queries.ts` **yo'q**, ya'ni u o'z rejasi doirasida bu faylni tuzata olmasdi va `{items}` bilan yozilgan komponentlar birinchi so'rovdayoq parse xatosi berardi. Kontrakt qatlami shu yerda yopildi, iste'mol qatlami 06-13 da qoladi.

## Decisions Made

- **Qadam elementining egasi shart bilan almashadi.** `fieldset` `data-collect-step="method"` ni FAQAT to'lov turi tanlanmaganda, tasdiq tugmasi `"confirm"` ni FAQAT tanlangandan keyin oladi. Aks holda `payment-bar` ning o'zida ikkita qadam elementi bo'lardi va §8.2 invarianti (`toHaveLength(1)`) **birinchi iteratsiyadayoq** yiqilardi.
- **`payment-bar` mutatsiyani o'zi egallaydi.** Reja `onError` da qulfni ochishni TALAB qiladi, ya'ni mutatsiya va qulf bir joyda bo'lishi shart. Spinner esa **lokal bayroqdan** chiziladi va so'rov holatining bayrog'i bu faylda **umuman o'qilmaydi** — nom bilan aylanib o'tish (`status === "pending"`) ham **ATAYIN** ishlatilmadi, chunki 05-13 ning darsi mexanizm haqida, token haqida emas.
- **Tasdiq tugmasidagi `keydown` yuborishni O'ZI bajaradi** va `preventDefault()` bilan brauzer sintez qiladigan `click` ni yopadi. Aks holda `repeat` filtri ikkinchi yo'lni umuman ko'rmasdi va (b) kanali **bo'sh da'vo** bo'lardi.
- **Sikl oraliq holatda harakat qilmaydi.** Faqat «qiyofa o'zgardimi?» deb kutish ko'p moslik yo'lida siklni **10 qadamga** cho'zdi (o'lchandi: birinchi yugurishda `posted === false`): ro'yxat bosilgan zahoti yo'qoladi va qadam bir lahzaga qidiruv maydoniga qaytadi. Sikl endi `isFetching`/`isMutating` **nolga tushguncha** kutadi.
- **Yangi tarjima kaliti qo'shilmadi.** `<verification>` bandi shuni talab qiladi va `i18n:check` **1095 kalit × 3 til** bo'lib qoldi. E'lonlar mavjud kalitlardan quriladi (`errorCause`/`errorFix` juftliklari) — bu §13.7 ning o'z naqshi.
- **`/collect` da `Suspense` chegarasi BOSHQA sababga ko'ra turibdi** (`occupancy` dagi `useSearchParams` sababi bu yerda **yo'q** — URL holati taqiqlangan): u ish maydonini sarlavhadan ajratadi, ya'ni sessiya yuklanayotganda ham `[Smena]` havolasi bosiladigan bo'lib qoladi. Sabab `page.tsx` docstringida yozilgan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `usePendingStall` ko'p moslik javobini PARSE QILA OLMASDI**

- **Found during:** Kechiktirilgan bandlar (Task 1 dan oldin)
- **Issue:** `stall-lookup.tsx` ning ko'p moslik ro'yxati serverning `{matches, stall}` javobiga tayanadi, 06-03 ning `usePendingStall` i esa FAQAT tekis shaklni biladi (`schema: pendingStallSchema`). Ya'ni G-20 ning ko'p moslik yo'li (`steps === 4`) **umuman qurib bo'lmasdi**: javob parse paytida yiqilib, ekran «rasta topilmadi» deb yolg'on aytardi.
- **Fix:** `pendingLookupSchema` (juftlangan invariant bilan) + `pendingLookupResponseSchema` (birlashma) + `normalizePendingLookup()` qo'shildi; `usePendingStall` ning `select` i ikkala shoxni **bitta** shaklga keltiradi va `matchesRequestedCode` ni saqlab qoladi.
- **Files modified:** `frontend/src/lib/billing-pending-queries.ts`
- **Verification:** `collect-session.test.tsx` ning ko'p moslik testi (`steps === 4`); `collect-surface.test.mjs` (G-22) shu fayl ustida **yashil**.
- **Committed in:** `66aa7dc`

**2. [Rule 1 - Bug] G-18 naqshi ikki marta e'lon qilindi va darvoza qizardi**

- **Found during:** Task 1
- **Issue:** Naqsh jadval katagida **va** unga qo'shilgan izoh jumlasida ham backtick bilan yozildi. `declaredDirectoryGlobs()` ikkalasini ham o'qidi va `assert.equal(new Set(globs).size, globs.length)` **qizardi** (4 ≠ 3).
- **Fix:** Izohdagi backticklar olib tashlandi — katalog nomi izohda **oddiy matn** bo'lib qoldi.
- **Files modified:** `.planning/phases/05-.../05-UI-SPEC.md`
- **Verification:** `node --test frontend/scripts/bulk-action-surface.test.mjs` → **8/8 yashil**.
- **Committed in:** `61a8853`

**3. [Rule 1 - Bug] `pending-card.test.tsx` da `{ exact: false }` yolg'on natija berardi**

- **Found during:** Task 1
- **Issue:** «Summa chizilmadi» da'vosi `collect.todayAmount` («Bugungi patta») ni **registrga sezgir bo'lmagan qism-satr** sifatida izlardi. `collect.marketClosed` matni («Bugun bozor yopiq — **bugungi patta** hisoblanmaydi») ham shu satrni o'z ichiga oladi, ya'ni `market_closed` testi **yolg'on qizil** berdi.
- **Fix:** Da'vo Display elementining `sr-only` yorlig'iga (`"Bugungi patta:"`, aniq moslik) bog'landi va sabab test faylida yozildi.
- **Files modified:** `frontend/src/components/collect/pending-card.test.tsx`
- **Verification:** `pending-card` → **15/15 yashil**.
- **Committed in:** `61a8853`

**4. [Rule 1 - Bug] Sikl ko'p moslik yo'lida ORALIQ holatda harakat qilardi**

- **Found during:** Task 2
- **Issue:** Sikl faqat `stepKey` o'zgarishini kutardi. Ro'yxatdan kod tanlangach ro'yxat **darhol** yo'qoladi va qadam bir lahzaga qidiruv maydoniga qaytadi (yangi so'rov hali ketmagan) — sikl o'sha lahzada kodni **qayta terib** ro'yxatni qayta ochardi. O'lchov: `steps` 10 ga yetdi, `posted === false`.
- **Fix:** Kutish shartiga `client.isFetching() === 0` va `client.isMutating() === 0` qo'shildi; sabab test faylida ochiq yozildi.
- **Files modified:** `frontend/src/components/collect/collect-session.test.tsx`
- **Verification:** `collect-session` → **6/6 yashil**; ikkinchi takror testi ham shu shart ostida.
- **Committed in:** `8c1447a`

**5. [Rule 3 - Blocking] Kutish kaliti dialog TAVSIFIDA ham bor edi**

- **Found during:** Task 3
- **Issue:** `reason-dialog.test.tsx` ning §14.3 da'vosi matn bo'yicha izlardi, ayni satr esa dialogning `aria-describedby` tavsifida ham turibdi → `getByText` **«multiple elements»** bilan yiqildi.
- **Fix:** Da'vo `getByRole("status")` ga o'tkazildi — u KANALNI (jonli hudud) o'lchaydi va aynan §14.3 ning matni shu.
- **Files modified:** `frontend/src/components/collect/reason-dialog.test.tsx`
- **Verification:** `reason-dialog` → **8/8 yashil**.
- **Committed in:** `273a9c0`

**6. [Rule 3 - Blocking] T2 test mock'lari `/payments/recent` ni bilmasdi**

- **Found during:** Task 3
- **Issue:** Task 3 `collect-session.tsx` ga `useRecentPayments()` qo'shdi, T2 ning mock'lari esa noma'lum yo'lni **rad etardi** — ya'ni T2 testlarida ushlanmagan rad etish paydo bo'lardi.
- **Fix:** Ikkala test faylining marshrut mock'iga `/payments/recent` → `{items: []}` qo'shildi.
- **Files modified:** `collect-session.test.tsx`, `payment-bar.test.tsx`
- **Verification:** `npm --prefix frontend test` — **to'liq yashil**.
- **Committed in:** `273a9c0`

**7. [Rule 3 - Blocking] Worktree'da `frontend/node_modules` yo'q edi**

- **Found during:** Boshlanish
- **Issue:** Frontend darvozalari umuman yugurmasdi (06-07/06-08/06-09 SUMMARY'laridagi holatning to'rtinchi takrori).
- **Fix:** `npm ci` **shu worktree ichida** yugurtirildi (530 paket). ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning nusxasini yo'q qilgan.
- **Files modified:** yo'q (`node_modules` gitignored)
- **Committed in:** — (repoga tegmaydi)

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **⛔ `grep -cE "\bdisabled=" payment-bar.tsx` → 0 mezoni O'ZIGA ZID.** `\b` — so'z chegarasi, `aria-disabled=` dagi `-` esa so'z belgisi EMAS, ya'ni ifoda `aria-disabled=` ni **ham ushlaydi**. Bir vaqtda `grep -c "aria-disabled" ≥ 1` talab qilingan, ya'ni ikkala mezonni birga bajarish **imkonsiz**. O'lchov niyatga ko'ra qayta yozildi: `grep -cE "(^|[^-])\bdisabled=" payment-bar.tsx` → **0** (yalang'och `disabled=` yo'q), `grep -c "aria-disabled"` → **2**. Bu 06-08/06-09 dagi grep aniqlashtirishlarining aynan bir sinfi.
- **`grep -cE "charge_id|chargeId|tariff_id|vendor_name|balance" components/collect/*.tsx` → 0 — MAHSULOT fayllari uchun.** Glob `*.test.tsx` ni ham qamraydi, `pending-card.test.tsx` esa G-23(a) bo'yicha AYNAN o'sha maydonlar bilan sabotaj payloadini parse qilishi **shart** (reja shuni buyuradi). Darvozaning o'zi (`collect-surface.test.mjs`) test fayllarini **chiqarib tashlaydi** (`TEST_FILE` regeksi). O'lchov: oltala mahsulot faylida **0**.
- **`type="number"` va `toBeLessThanOrEqual` mezonlari IZOH matnidan qizargan edi.** Ikkala token ham dastlab «bu shakl ishlatilmaydi» degan izohda **literal** sifatida turgan edi. Izohlar qayta yozildi (ma'no saqlandi, literal olib tashlandi), chunki mezonlar xom `grep` bilan o'lchanadi. Yakuniy o'lchov: ikkalasi ham **0**.
- **`must_haves` da `collect-session.tsx` `contains: "data-collect-step"`** — bajarildi (**1** satr), lekin atributning O'ZI bolalarda chiziladi. Sessiya **egalikni** hal qiladi (`ownsStep={stall === null}` va `payment-bar` ichidagi shart) — bu §8.2 invariantining haqiqiy mexanizmi va u docstringda yozilgan.
- **§8.1 ning `submitting` va `error` holatlari `payment-bar.tsx` da yashaydi.** `collectState()` qolgan yettitasini qaytaradi. Sabab ochiq yozilgan: ularni sessiyaga ko'tarish qulfni ota-komponent orqali render aylanishiga bog'lardi — 05-13 o'lchagan nuqsonning aynan o'zi. To'qqizala nom `CollectState` birlashmasida.

---

**Total deviations:** 7 auto-fixed (4 blocking, 3 bug) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Qamrov kengaymadi. Yangi paket **o'rnatilmadi**, yangi `ui/` primitivi **qurilmadi**, yangi tarjima kaliti **qo'shilmadi**, backendga **tegilmadi** (`git diff --numstat services/` → bo'sh), 06-10 ning birorta fayliga **tegilmadi**.

## Issues Encountered

- **⚠ OCHIQ YOZILGAN QIZIL OYNA — KUTILGAN VA YOPILGAN.** `collect-surface.test.mjs` ning `MIN_COLLECT_FILES = 5` chegarasi T1 dan keyin (katalogda **2** fayl) va T2 dan keyin (**4** fayl) **QIZIL** edi; T3 da (**6** fayl) **YASHIL** bo'ldi. Bu reja o'zi ogohlantirgan holat va u **shu reja ichida yopildi** — keyingi ijrochi «ma'lum qizil» ni «mening qizilim» dan ajrata olsin.
- **⛔ `npm test -- <filtr>` TUZOG'IGA TUSHILMADI.** Reja o'lchagan mexanika kuzatildi: T1/T2 ning `<verify>` i `npm --prefix frontend run test:component -- <filtr>` bilan yugurtirildi (**bitta** buyruq — filtr yetadi), `node --test` darvozalari esa **nomi bilan** chaqirildi. To'liq zanjir (`npm --prefix frontend test`) faqat **T3 dan keyin** — chegara bajarilgandan **keyin** — yugurtirildi.
- **`gate` ning backend yarmi yugurmadi** (docker; qo'shni 06-10 worktree'i bilan umumiy konteynerlar). Bu reja frontend-only. Frontend segmenti **o'lchandi: 231 s**. Band `deferred-items.md` ning 6-qatorida.
- **`collect.recentEmpty` matn kaliti yo'q** — oxirgi to'lovlar bloki bo'sh bo'lganda umuman chizilmaydi (yolg'on matn to'qilmadi). Band `deferred-items.md` ning 5-qatorida.

## Verification

| Buyruq | Natija |
|---|---|
| `npm --prefix frontend test` (to'liq zanjir) | ✅ `node --test` **182/182** + vitest **656/656** (bazadan **+36**) |
| `npm --prefix frontend run test:component -- pending-card` | ✅ **15/15** |
| `npm --prefix frontend run test:component -- collect-session` | ✅ **6/6** |
| `npm --prefix frontend run test:component -- payment-bar` | ✅ **7/7** |
| `npm --prefix frontend run test:component -- reason-dialog` | ✅ **8/8** |
| `node --test .../collect-surface.test.mjs .../bulk-action-surface.test.mjs .../billing-copy.test.mjs .../error-codes.test.mjs` | ✅ **58/58** |
| `npm --prefix frontend run typecheck` | ✅ toza |
| `npm --prefix frontend run lint` | ✅ toza |
| `npm --prefix frontend run build` | ✅ `✓ Compiled successfully in 17.0s`; `/[locale]/collect` uchala locale'da prerender qilindi |
| `npm --prefix frontend run i18n:check` | ✅ **1095 kalit × 3 til** — yangi kalit **qo'shilmagan** |
| `gate` frontend segmenti (i18n + test + typecheck + lint + build) | ⏱ **231 s** (tinch xost) |
| `git diff --numstat services/` | ✅ **bo'sh** (backendga tegilmadi) |

**Qabul mezonlari (Task 1):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `bulk-action-surface.test.mjs` yashil, `SPEC_FILES.length === 1` | 8/8 | ✅ |
| `grep -c "components/collect/\*\*" 05-UI-SPEC.md` → 1 | **1** | ✅ |
| `grep -cE "^\| \*\*G-18\*\* \|" 06-UI-SPEC.md` → 0 | **0** | ✅ |
| `stall-lookup` da beshala xossa; `type="number"` yo'q | **9** moslik / **0** | ✅ |
| `grep -c "min-h-14" stall-lookup.tsx` ≥ 1 | **1** | ✅ |
| `data-collect-step="stall"` shartli, ikki joyda | **2** | ✅ |
| `pendingStallSchema.parse({...toza, charge_id})` throw | vitest | ✅ |
| Juftlangan invariantning IKKI yo'nalishi (ikki alohida assert) | vitest | ✅ |
| Mos kelmagan kodda summa chizilmaydi | vitest (`Skeleton`) | ✅ |
| Taqiqlangan nomlar mahsulot fayllarida | **0** | ✅ (yuqoridagi aniqlashtirishga qarang) |
| `grep -c "CollectSession" collect/page.tsx` → 0 (T1 da) | **0** | ✅ |
| `onRequestOverride` berilmasa tugma DOM'da 0; `disabled` tugma ham 0 | vitest | ✅ |
| ⚠ `collect-surface.test.mjs` QIZIL (2 fayl) | kutilgan | ⚠ |

**Qabul mezonlari (Task 2):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `expect(steps).toBe(3)` bor; `toBeLessThanOrEqual` → 0 | **3** ta `toBe(3)` / **0** | ✅ |
| Ko'p moslik: `toBe(4)` + tartib + `new Set(visited)` | vitest | ✅ |
| Ikkinchi takror `toBe(3)` | vitest | ✅ |
| Uch tez bosish → **1** chaqiruv | vitest | ✅ |
| `keyDown{repeat:true}` ×3 → **0** (+ NAZORAT: bitta `Enter` → 1) | vitest | ✅ |
| 5xx → `[Qayta yuborish]` → 2-chi chaqiruv, **bir xil** kalit | vitest | ✅ |
| `grep -c "submittedRef" payment-bar.tsx` ≥ 3; `isPending` → 0 | **4** / **0** | ✅ |
| `aria-disabled` ≥ 1; yalang'och `disabled=` → 0 | **2** / **0** | ✅ (mezon ifodasi tuzatildi) |
| `crypto.randomUUID` ≥ 1; `from "uuid"` → 0 | **1** / **0** | ✅ |
| `dropPendingAfterPayment` ≥ 1 | **2** | ✅ |
| `type="checkbox"`/`selectAll`/`Array.isArray(selected` → 0 | **0** (oltala fayl) | ✅ |
| `grep -c "CollectSession" page.tsx` ≥ 2; `<CollectSession` ≥ 1 | **2** / **1** | ✅ |
| `collect-session` uchala bolasini import qiladi | **6** moslik | ✅ |
| Oldindan murojaat (`ReasonDialog`/`PaymentRow`/...) → 0 | **0** | ✅ |
| ⚠ `collect-surface.test.mjs` hamon QIZIL (4 fayl) | kutilgan | ⚠ |

**Qabul mezonlari (Task 3):**

| Mezon | O'lchov | Natija |
|---|---|---|
| ⛔ `collect-surface.test.mjs` **YASHIL** (≥5 mahsulot fayli) | **6** fayl, 11/11 | ✅ |
| `billing-copy.test.mjs` yashil | 13/13 | ✅ |
| `textarea` → 0; `input[type="text"]` → 0 (+ to'plam tengligi) | vitest | ✅ |
| `<option>` to'plami `ADJUSTMENT_REASONS` ga TENG; `other`/`custom` yo'q | `Set` tengligi | ✅ |
| Sabab tanlanmasa `aria-disabled="true"` va `onConfirm` chaqirilmaydi | vitest (ikkala rejim) | ✅ |
| `payment-row` da to'lov turi IKKI kanalda | `methodCash\|methodTerminal` → **3**, ikonkalar → **3** | ✅ |
| `\.reduce\(\|\bsum\b\|total` — `payment-row.tsx` | **0** | ✅ |
| `\.reduce\(\|\bsum\b\|total` — `collect-session.tsx` | **0** | ✅ |
| `Tahrirlash\|O'chirish\|editPayment\|deletePayment` | **0** (oltala fayl) | ✅ |
| `system_soum\|variance\|payment_count` | **0** (oltala fayl) | ✅ |
| `ReasonDialog` ≥ 2; `PaymentRow` ≥ 2; `onRequestOverride` ≥ 1 | **2** / **2** / **1** | ✅ |
| `collect-session.test.tsx` hamon yashil, `steps` AYNAN 3 | 6/6 | ✅ |
| `npm --prefix frontend run build` | ✅ | ✅ |
| `npm --prefix frontend test` to'liq yashil | 182 + 656 | ✅ |

## Known Stubs

Yo'q. Oltala mahsulot komponenti ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q va birorta komponent qotirilgan bo'sh qiymat chizmaydi.

⚠ **Oxirgi to'lovlar bloki BO'SH ro'yxatda umuman chizilmaydi** va bu **stub EMAS**: §13.8 ning 3-bo'sh holati uchun matn kaliti mavjud emas va yangi kalit qo'shish `<verification>` bandiga zid (06-02 copy egaligi). Yolg'on matn to'qish yoki boshqa ma'nodagi kalitni qayta ishlatish RAD ETILDI — 05-14 ning darsi. Band `deferred-items.md` ning **5-qatorida**, egasi bilan.

⚠ **`collectState()` ning `submitting` va `error` shoxlari qaytarilmaydi** va bu ham stub emas: ikkala holat `payment-bar.tsx` da yashaydi (mutatsiya egasida), sabab docstringda ochiq yozilgan.

## Threat Flags

Yangi **server** yuzasi ochilmadi — reja frontend-only. Threat register bo'yicha:

- **T-06-66** (uch tez bosish / `Enter` bosib turish) — ✅ **ikki qatlam**: server kaliti (06-09) va `useRef` qulfi; so'rov holatining bayrog'i **ishlatilmaydi**; `event.repeat` e'tiborsiz; G-21 **uchala kanalda** o'lchandi.
- **T-06-67** (eski summa yangi rasta ostida) — ✅ **uch qatlam**: `gcTime: 0`/`staleTime: 0` (06-03), moslik sharti (**xulq bilan** o'lchandi), `data-collect-step="method"` faqat rasta yechilgach DOM'da.
- **T-06-68** (klientda pul arifmetikasi) — ✅ `total_due_soum` **serverdan**; tarif kirish ma'lumoti payloadda **yo'q**; G-22 skani oltala faylda **0** topdi.
- **T-06-69** (sabab-kodsiz summa o'zgarishi) — ✅ DL-1 **ataylab qimmat**; erkin matn yuzasi DOM'da **bo'sh to'plam**; server 422 (06-09) — ikki qatlam.
- **T-06-70** (yig'indi orqali tizim summasi) — ✅ `payment-row.tsx` va `collect-session.tsx` da yig'uvchi amal **yo'q** (grep bilan o'lchandi); oyna serverda 5 va marshrutda parametr yo'q.
- **T-06-71** (kassir ekranida shaxsiy maydon) — ✅ G-22 reyestri oltala faylda **0**; nom bilan aylanib o'tish ham yo'q.
- **T-06-72** (to'lovni tahrirlash/o'chirish) — ✅ affordanslar **umuman yozilmadi** (grep → 0); yagona amal — bekor qilish, u **yangi qator** yozadi.
- **T-06-73** (ommaviy to'lov) — ✅ `components/collect/**` G-18 skaniga **kirdi** (OP-5) va ikkinchi, mustaqil qatlam (`collect-surface.test.mjs` ning `BULK_ACTION_TOKENS`) ham **yashil**.
- **T-06-SC** (`accept`) — yangi paket **o'rnatilmadi**.

⚠ **Yangi klient yuzasi:** `/collect` marshruti RBAC ko'zgusi bilan (`payment_create`). Bu **himoya emas**, foydalanuvchi tajribasi — haqiqiy nazorat serverda (`require_permission(PAYMENT_CREATE)`, 06-09).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): parallel worktree'da frontend darvozalarini yugurtirish uchun `npm ci` **shu worktree ichida** bajariladi. ⛔ Junction/symlink **YARATILMAYDI** — o'sha xatolik ilgari asosiy checkout'ning `node_modules` ini yo'q qilgan.

## Next Phase Readiness

- **06-12 (darvozalar):** `components/collect/**` da **6** mahsulot fayli bor, ya'ni `MIN_COLLECT_FILES = 5` chegarasi **bajarilgan** — 06-12 o'z `<verify>` ida `collect-surface.test.mjs` ni yashil ko'radi va katalogga ikki fayl qo'shsa ham chegara buzilmaydi.
- **06-13 (direktor yuzasi):** ⛔ **Kontrakt o'zgardi va u `deferred-items.md` ning 4-qatorida yozilgan:** `chargeListSchema`/`anomalyListSchema` endi `{day, rows, hisoblagichlar}`. Komponentlar qatorlarni **`.rows`** dan o'qishi shart; `tsc` `items` ga murojaatni **qizartiradi**, ya'ni band jimgina o'tib keta olmaydi. G-25 uchun kerak bo'ladigan `[data-billing-block]` kontrakti bu rejada **tegilmadi**.
- **06-14 (faza darvozasi):** `gate` ning frontend segmenti **231 s** (o'lchandi); backend yarmi bu worktree'da yugurmadi. Byudjet (1250 s) va uning qayta o'lchovi 06-14 ning ishi — band `deferred-items.md` ning 6-qatorida.
- **Ochiq band (bloklamaydi):** `collect.recentEmpty` matn kaliti (5-qator).

## Self-Check: PASSED

**Fayllar (12/12 mavjud):** `collect/page.tsx` (126) · `collect-session.tsx` (442) · `stall-lookup.tsx` (182) · `pending-card.tsx` (299) · `payment-bar.tsx` (296) · `reason-dialog.tsx` (259) · `payment-row.tsx` (136) · `collect-session.test.tsx` (370) · `payment-bar.test.tsx` (358) · `pending-card.test.tsx` (346) · `reason-dialog.test.tsx` (212) · `06-11-SUMMARY.md`

**Commitlar (4/4 topildi):** `66aa7dc` · `61a8853` · `8c1447a` · `273a9c0`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `collect-session.tsx` `min_lines: 200` | `wc -l` → **442** | ✅ |
| `collect-session.tsx` `contains: data-collect-step` | `grep -c` → **1** (egalik mantig'i `ownsStep` da) | ✅ |
| `payment-bar.tsx` `contains: submittedRef` | `grep -c` → **4** | ✅ |
| `collect-session.test.tsx` `contains: toBe(3)` | `grep -c` → **3** | ✅ |
| `key_links`: `payment-bar` → `useRef` qulfi (`submittedRef.current`) | mavjud, `onError` da nolga qaytadi | ✅ |
| `key_links`: `05-UI-SPEC` §15 G-18 → `components/collect/**` | **1** naqsh, bitta commitda | ✅ |
| `key_links`: `collect-session` → `dropPendingAfterPayment` | `grep -c` → **2** | ✅ |
| `key_links`: `page.tsx` → `<CollectSession />` | import **va** render | ✅ |
| `key_links`: `collect-session` → beshala bola | `StallLookup`/`PendingCard`/`PaymentBar` + `ReasonDialog`/`PaymentRow` | ✅ |

**`truths` (7/7):**
sahifadan `POST /payments` gacha AYNAN **3** o'zaro ta'sir ·
ikkinchi takror ham **3** — fokus qidiruvga avtomatik qaytadi ·
uch tez bosish **1** so'rov; `Enter` bosib turish **0** qo'shimcha ·
eski rastaning summasi yangi kod ostida **ko'rinmaydi** (uch qatlam, ikkinchisi xulq bilan) ·
sabab tanlanmasa tasdiq `aria-disabled`, erkin matn maydoni DOM'da **yo'q** ·
`pendingStallSchema.parse({...toza, charge_id})` **throw** ·
kompozitsiya kontrakti: yettala komponentni render qiladigan fayl **birorta taskning `<files>` ida**.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-11*
