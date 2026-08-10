---
phase: 06-billing-va-kassir
plan: 03
subsystem: ui
tags: [react-query, zod, tanstack-query, next, testing, node-test, billing, cashier]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    provides: "domainKey() kalit fabrikasi (market-queries.ts), tenant-cache darvozasi"
  - phase: 05-cv-va-nazoratchi
    provides: "blind-audit-queries.ts (gcTime 0 + removeQueries juftligi), blind-payload.test.mjs va bulk-action-surface.test.mjs darvoza shablonlari, soumSchema"
provides:
  - "lib/billing-pending-queries.ts — GET /billing/pending proyeksiyasi, z.strictObject (7 kalit), juftlangan invariant, gcTime 0 + removeQueries"
  - "lib/billing-charge-queries.ts — GET /billing/charges, /charges/{id}, /anomalies; anomalyRowSchema da C-12 juftligi"
  - "lib/payment-queries.ts — POST /payments, /payments/{id}/reverse, GET /payments/recent (ARGUMENTSIZ)"
  - "lib/shift-queries.ts — POST /shifts, GET /shifts/open, POST /shifts/{id}/close (AYNAN 4 kalit), GET /shifts?day="
  - "scripts/collect-surface.test.mjs — G-7 (frontend yarmi) + G-22 + G-28(d) + ommaviy amal ikkinchi qatlami"
affects: [06-11, 06-12, 06-13, 06-14, 07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ikki ALOHIDA so'rov moduli — darvoza yozilishi mumkin bo'lishi uchun (W0-F3)"
    - "z.strictObject + zanjirlangan .refine() bilan juftlangan invariant (ikki yo'nalish, ikki xabar)"
    - "select() bilan moslik shartini HOSIL qilish (matchesRequestedCode) — kesh siyosatidan mustaqil qatlam"
    - "Darvoza qamrovi katalogdan HOSILA; fayl/katalog yo'q bo'lsa skip EMAS, OCHIQ QAYD"

key-files:
  created:
    - frontend/src/lib/billing-pending-queries.ts
    - frontend/src/lib/billing-charge-queries.ts
    - frontend/src/lib/payment-queries.ts
    - frontend/src/lib/shift-queries.ts
    - frontend/scripts/collect-surface.test.mjs
  modified: []

key-decisions:
  - "06-03: yordamchi nomi dropPendingAfterPayment (invalidatePendingAfterPayment EMAS) — nom AMALNI aytishi shart, `invalidate` esa yozuvni keshda QOLDIRADI"
  - "06-03: to'rt enum reyestri VAQTINCHA so'rov modullarida — 06-02 bir to'lqinda api-types.ts ni egallaydi va import qilish mumkin emas edi; api-types.ts ga tegilmadi (birlashuvda ikki ta'rif bo'lardi)"
  - "06-03: useMarketPending da refetchOnWindowFocus ATAYIN qo'yilmadi (§9.5 standart holida qoldiradi), usePendingStall da esa false — kassir bir rastada turadi, direktor sahifaga qaytadi"
  - "06-03: shiftCloseResponseSchema identifikatori faylda BIRINCHI marta o'z ta'rifida uchraydi — darvoza matn skani birinchi mosligni oladi va oldingi eslatma boshqa sxemani o'lchardi"
  - "06-03: variance_soum soumSchema EMAS, z.number().int() — kamomad manfiy va manfiylikni rad etish D-26 ning yarmini o'chirardi"
  - "06-03: gate:fast ning docker yarmi ATAYIN bajarilmadi (reja hech qanday Python kodiga tegmaydi; parallel to'lqinda alohida compose loyihasi C: diskini yeb qo'yardi) — frontend yarmi o'lchandi: 68 s"

patterns-established:
  - "Modul ajratish darvozani MUMKIN qiladi: taqiqlangan nom aralash faylda QONUNIY bo'lardi va shart kontekstga bog'liq bo'lib qolardi"
  - "Juftlangan invariant ikki alohida .refine() bilan — xato xabari ikki server nosozligini AJRATIB aytadi"
  - "stripComments() UCHINCHI marta yozilmaydi — mavjud nusxadan bayt-ba-bayt ko'chiriladi va o'lchanadi"
  - "Darvoza sabotaj bilan o'lchanadi: izohdagi taqiqlangan nom YASHIL, koddagi nom QIZIL"

requirements-completed: [BILL-05, CASH-01, CASH-03, CASH-04]

# Metrics
duration: 32min
completed: 2026-08-10
---

# Phase 06 Plan 03: Kontrakt-birinchi so'rov qatlami Summary

**To'rt `zod` so'rov moduli va ularni qo'riqlaydigan matn darvozasi — proyeksiya bilan yozilgan hisob ikki ALOHIDA faylga bo'lindi va G-22 shu tufayli komponentlardan OLDIN yozildi.**

## Performance

- **Duration:** ~32 min
- **Started:** 2026-08-10T09:08:00Z (14:08 +05)
- **Completed:** 2026-08-10T09:40:54Z (14:40 +05)
- **Tasks:** 3
- **Files created:** 5

## Accomplishments

- **W0-F3 bajarildi:** proyeksiya (`billing-pending-queries.ts`) va yozilgan hisob
  (`billing-charge-queries.ts`) ikki alohida modulda. Shu tufayli G-22
  taqiqlangan nomlarni **butun faylda** izlay oladi — aralash modulda shart
  kontekstga bog'liq bo'lib, matn skani bilan tekshirib bo'lmas edi.
- **D-17/D-20 imkonsizlik darajasida:** `pendingStallSchema` da hisob va tarif
  identifikatorlari **umuman yo'q**, ya'ni klientda pul arifmetikasining
  **kirish ma'lumotining o'zi** mavjud emas. Yig'indi ham serverdan
  (`total_due_soum`).
- **D-25 ning serializator yarmi sxemada:** `shiftCloseResponseSchema` kalitlari
  to'plami **aynan** `{id, status, declared_soum, closed_at}` — mexanik
  tekshiruv bilan tasdiqlandi.
- **§11.5 FLAG'i yopildi:** «smenasiz to'lovlar» agregatiga **nom berildi**
  (`shiftless_payment_count` + `shiftless_payment_soum`), ya'ni ular ekranda
  jimgina yo'qolmaydi.
- **Uch darvoza komponentlardan OLDIN joyida** va qamrovi **katalogdan hosila**:
  `collect-surface.test.mjs` 11 ta tasdiq bilan yashil, sabotaj ikki
  yo'nalishda ham o'lchandi.

## Task Commits

1. **Task 1: ikki ALOHIDA so'rov moduli (W0-F3)** — `9522168` (feat)
2. **Task 2: to'lov va KO'R smena kontrakti (D-21, D-25)** — `34a4f8b` (feat)
3. **Task 3: `collect-surface.test.mjs` darvozasi** — `e8de8a5` (test)

## Files Created

- `frontend/src/lib/billing-pending-queries.ts` — `GET /billing/pending`
  proyeksiyasi. `pendingStallSchema` (7 kalit, `z.strictObject`) + juftlangan
  invariant **ikki alohida** `.refine()` bilan; `pendingMarketSummarySchema`
  (bozor kesimi); `pendingPrefix/pendingStallKey/pendingMarketKey`
  fabrikalari (`domainKey`, birinchi argument `marketId`);
  `usePendingStall` (`staleTime: 0`, `gcTime: 0`, `retry: false`,
  `select` bilan `matchesRequestedCode`), `useMarketPending`,
  `dropPendingAfterPayment()`.
- `frontend/src/lib/billing-charge-queries.ts` — `chargeRow`/`chargeList`/
  `chargeAdjustment`/`chargeEvidence`/`chargeDetail`/`anomalyRow`/`anomalyList`
  sxemalari; `anomalyRowSchema` da C-12 juftligi
  (`(kind === "no_coverage_stall") === (snapshot_id === null)`);
  `useCharges`/`useChargeDetail`/`useAnomalies`, `staleTime: 60_000`.
- `frontend/src/lib/payment-queries.ts` — `paymentResponseSchema` (8 kalit;
  hisob identifikatori va shaxsiy maydon **yo'q**), `recentPaymentsSchema`;
  `usePayment` / `useReversePayment` (`retry: false`, `onSuccess` da ikki
  `removeQueries`), `useRecentPayments()` — **argumentsiz**.
- `frontend/src/lib/shift-queries.ts` — `shiftCloseResponseSchema` (**aynan 4
  kalit**), `shiftOpenSchema`, `shiftReportRowSchema`, `shiftReportSchema`
  (`shiftless_*` bilan); `useOpenShift`/`useOpenShiftMutation`/`useCloseShift`/
  `useShiftReport`.
- `frontend/scripts/collect-surface.test.mjs` — 11 tasdiq, to'rt blok
  (G-22 · G-7 frontend yarmi · G-28(d) · ommaviy amal ikkinchi qatlami) +
  izoh filtrining ijobiy/salbiy nazorati + runaway nazorati.

## Decisions Made

1. **`dropPendingAfterPayment`, `invalidatePendingAfterPayment` EMAS.** Reja
   ikkinchi nomni taklif qilib, «chalg'itsa o'zgartiriladi» degan yo'lni ochiq
   qoldirgan edi. Nom o'zgartirildi: TanStack'da `invalidate` yozuvni grafda
   **qoldiradi**, to'lovdan keyingi eski proyeksiya esa **yolg'on summa** va u
   brauzer xotirasida turishi ham kerak emas. Nom juftlikning (`gcTime: 0` +
   `removeQueries`) ikkinchi yarmini aytadi.
2. **`useMarketPending` da `refetchOnWindowFocus` qo'yilmadi.** Reja moduldagi
   hamma so'rov uchun `false` deydi, UI-SPEC §9.5 esa bozor kesimi uchun
   «standart holida qoladi» deb **ochiq qaror yozgan**. Kassir yuzasida
   `false` (kassir bir rastada turadi, fokus qaytishi so'rov tug'dirmasligi
   kerak), direktor kesimida standart (sahifaga qaytganda eng yangi raqam).
   **Avtomatik taymer ikkalasida ham yo'q** — bu §9.5 ning asosiy talabi.
3. **`variance_soum` — `z.number().int()`, `soumSchema` emas.** `soumSchema`
   manfiy qiymatni rad etmaydi, lekin u pul KATTALIGI uchun; farq esa
   **ishorali** va ishora ma'no tashiydi (kamomad `< 0`). `abs()` qilingan
   yoki manfiylikni rad etgan sxema D-26 ning «ortiqcha ham signal» yarmini
   o'chirardi.
4. **`shiftCloseResponseSchema` identifikatori faylda birinchi marta o'z
   ta'rifida uchraydi.** Darvoza matn skani (`s.match(/shiftCloseResponseSchema
   [\s\S]*?\}\)/)`) **birinchi** moslikni oladi; identifikatorni fayl
   sarlavhasida yoki JSDoc'da oldinroq yozish skanni **boshqa sxemaning**
   kalitlariga qaratardi. Shu sababdan sarlavha izohi «yopish javobining
   sxemasi» deb yozildi.
5. **`chargeListSchema` / `anomalyListSchema` / `recentPaymentsSchema`
   qo'shildi** (rejada nomlanmagan): `useCharges`/`useAnomalies`/
   `useRecentPayments` javob sxemasisiz yozilmaydi va G-25(c)
   `items[0].stall_code` hamda `items.length` ni **nom bilan** talab qiladi.
   Uchalasi ham `z.strictObject` va yig'indi maydoni **yo'q**.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Enum reyestrlari vaqtincha so'rov modullarida (06-02 bir to'lqinda)**
- **Found during:** Task 1 va Task 2
- **Issue:** Reja `PAYMENT_KINDS`, `PAYMENT_METHODS`, `REVERSAL_REASONS`,
  `ADJUSTMENT_REASONS`, `ANOMALY_KINDS` ni **`api-types.ts` dagi reyestrlardan
  hosila** qilishni buyuradi. Ammo bu ko'zgular **06-02 ning W0-F7 topshirig'i**
  va 06-02 **shu to'lqinda, alohida worktree'da** ishlaydi — ya'ni bu ijro
  paytida `api-types.ts` da ularning hech biri mavjud emas. Mavjud bo'lmagan
  eksportdan import qilish `typecheck` ni yiqitardi.
- **Fix:** Reyestrlar **o'z modullarida** `as const` massiv sifatida e'lon
  qilindi (`ANOMALY_KINDS` + `ADJUSTMENT_DIRECTIONS` + `ADJUSTMENT_REASONS` →
  `billing-charge-queries.ts`; `PAYMENT_KINDS` + `PAYMENT_METHODS` +
  `REVERSAL_REASONS` → `payment-queries.ts`; `AMOUNT_UNAVAILABLE_REASONS` →
  `billing-pending-queries.ts`; `SHIFT_STATUSES` → `shift-queries.ts`).
  `payment-queries.ts` `ADJUSTMENT_REASONS` ni **`billing-charge-queries.ts`
  dan import qiladi** — uchinchi nusxa yaratilmadi. Har reyestr ustida
  izoh: 06-02 ning ko'zgusi yetib kelganda import bilan almashtiriladi.
- **⛔ `api-types.ts` ATAYIN TEGILMADI.** U rejaning `files_modified`
  ro'yxatida yo'q va 06-02 unga aynan shu qatorlarni qo'shadi: ikkala
  worktree ham yozsa, birlashuvda **ikki ta'rif** (`Duplicate identifier`)
  paydo bo'lardi — matnli konflikt bermasdan, ya'ni JIMGINA.
- **Files modified:** `frontend/src/lib/billing-charge-queries.ts`,
  `frontend/src/lib/payment-queries.ts`
- **Verification:** `npm --prefix frontend run typecheck` va `lint` toza;
  qiymatlar 06-RESEARCH dagi `CHECK` ifodalaridan va UI-SPEC §13.5 dan
  so'zma-so'z olindi (`payments.kind IN ('payment','reversal')`,
  `method IN ('cash','terminal')`, `charge_adjustments.direction ∈
  {increase, decrease}`, `AnomalyKind` uchligi, besh `AdjustmentReason`,
  to'rt `ReversalReason`).
- **Committed in:** `9522168`, `34a4f8b`

**2. [Rule 3 - Blocking] Worktree'da `frontend/node_modules` yo'q edi**
- **Found during:** Task 1 verifikatsiyasi
- **Issue:** `node_modules` gitignore'da, ya'ni yangi worktree'da mavjud emas —
  `tsc`, `eslint`, `vitest` topilmadi va rejaning `<verify>` buyruqlari
  umuman bajarilmasdi.
- **Fix:** Asosiy checkout'ning `frontend/node_modules` katalogiga **NTFS
  junction** qo'yildi (`mklink /J`). `npm ci` o'rniga junction tanlandi:
  paketlar `package-lock.json` bilan **aynan bir xil** va parallel to'lqinda
  beshta worktree'ning har biriga alohida o'rnatish C: diskini (91 % to'la,
  STATE.md xavfi) yeb qo'yardi.
- **Files modified:** yo'q (artefakt, gitignore'da; `git status` toza)
- **Verification:** `git check-ignore -v frontend/node_modules` → ignore
  qilingan; `git status --short` commitlardan keyin bo'sh.
- **Committed in:** —

### Rejadan farqli, LEKIN ataylab

**3. Nom o'zgarishi:** `invalidatePendingAfterPayment` → `dropPendingAfterPayment`
(reja bu yo'lni ochiq qoldirgan: «agar nom darvozani chalg'itadigan bo'lsa,
nom o'zgartiriladi va sabab yoziladi»). Sabab yuqorida, «Decisions Made» 1-band.
Task 2 ham allaqachon shu nomga murojaat qilgan.

**4. `invalidateQueries` LITERALI faylda umuman yo'q.** Dastlabki nusxada u
izohda tushuntirish sifatida yozilgan edi (`blind-audit-queries.ts` da ham
shunday). Rejaning mezoni esa **xom `grep`** talab qiladi
(`grep -c "invalidateQueries" … → 0`), ya'ni izoh ham qizartirardi. Izoh
`invalidate*` oilasi shakliga qayta yozildi — ma'no saqlandi, mezon bajarildi.

---

**Total deviations:** 2 auto-fixed (ikkalasi ham Rule 3 — bloklovchi) + 2 ataylab
qilingan aniqlashtirish.
**Impact on plan:** Rejaning bironta qulflangan qarori (D-17, D-20, D-25, D-31,
D-32, C-4, C-10) o'zgarmadi. Ko'lam kengaymadi: birorta React komponenti
yozilmadi, birorta yangi paket qo'shilmadi (T-06-SC ning `accept` dispozitsiyasi
o'z kuchida).

## Sabotaj o'lchovi (majburiy, Task 3)

| # | Sabotaj | Kutilgan | O'lchangan |
|---|---------|----------|------------|
| S-1 | `billing-pending-queries.ts` oxiriga `// SABOTAJ-1 … charge_id …` **IZOHI** | Darvoza **YASHIL** (izoh filtri ishlaydi) | ✅ **11/11 yashil** |
| S-2 | O'sha faylga `const chargeId = 1; export const sabotaj2 = chargeId;` **KODI** | Darvoza **QIZIL** | ✅ **10/11**, aynan `G-22 … billing-pending-queries.ts` bloki yiqildi |

Ikkala sabotajdan keyin fayl `git checkout -- <fayl>` bilan qaytarildi
(`git status` toza).

**`stripComments()` qiyoslandi:** `bulk-action-surface.test.mjs:163-225` va
`collect-surface.test.mjs` dagi nusxa — **63 qator, `trim()` dan keyin
bayt-ba-bayt TENG** (dasturiy solishtirish bilan). Uchinchi implementatsiya
yozilmadi.

## Verification natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test frontend/scripts/collect-surface.test.mjs` | ✅ 11/11 (katalog yo'q — **ochiq qayd** yo'lidan o'tdi) |
| `npm --prefix frontend run typecheck` | ✅ toza |
| `npm --prefix frontend run lint` | ✅ toza |
| `npm --prefix frontend test` | ✅ `node --test` **163/163** + `vitest` **620/620** (43 fayl) |
| `npm run gate:fast` (frontend yarmi) | ✅ **68 s** — 180 s byudjetidan ancha past |

⚠ **`gate:fast` ning `test:fast` (docker) yarmi ATAYIN bajarilmadi.** Sabab
o'lchov bilan yozilgan: (a) bu reja **birorta Python fayliga tegmaydi**, ya'ni
`pytest tests/unit` ning natijasi asosiy tarmoqdagidan farq qila olmaydi;
(b) worktree'dan `docker compose` ishga tushirilsa **yangi compose loyihasi**
(`agent-a9f30d48570cd98e2`) va yangi image build'i tug'ilardi — STATE.md da
qayd etilgan «C: diski 91 % to'la» xavfi ostida, va bu parallel to'lqindagi
beshta agent uchun **beshga ko'payardi**. Frontend yarmi o'lchandi va yozildi.

## Mezon qamrovi (talablar)

| Talab | Bu rejada nima bajarildi | Nima QOLDI |
|-------|---------------------------|------------|
| **BILL-05** | Proyeksiya kontrakti (`pendingStallSchema`, `pendingMarketSummarySchema`) va uning yo'qlik invariantlari | Komponent (06-11), server marshruti (06-06 oilasidan) |
| **CASH-01** | To'lov mutatsiyasi kontrakti, dublikat to'sig'ining klient shartlari (`retry: false`, kalit sahifada) | `useRef` qulfi va ≤3 bosish (06-11), G-20/G-21 |
| **CASH-03** | `useRecentPayments()` (argumentsiz) + `useReversePayment()` majburiy sabab-kod bilan | DL-2 dialogi (06-11) |
| **CASH-04** | Ko'r yopish sxemasi (4 kalit) + direktor hisobot sxemasi (`shiftless_*` bilan) | `shift-close-form.tsx` va `variance-list.tsx` (06-11/06-13), G-27 |

⛔ Talab **belgilanmadi** (`Pending` qoladi): bu reja kontrakt qatlami, ya'ni
mezon **uchidan-uchiga** 06-14 da o'lchanadi. `requirements-completed`
frontmatteri rejaning `requirements` maydonidan **so'zma-so'z** ko'chirildi;
`REQUIREMENTS.md` ni belgilash to'lqin birlashuvidan keyin orkestrator
zimmasida.

## Known Stubs

Yo'q. To'rt modulda ham qattiq kodlangan bo'sh qiymat, «placeholder» matni
yoki simsiz komponent yo'q — bu reja **birorta React komponentini yozmaydi**
(ataylab: kontrakt avval, iste'molchi keyin). Modullar hali **chaqirilmaydi**
va bu rejaning ochiq yozilgan xossasi (objective, ⚠ bandi).

`billing-charge-queries.ts:152` dagi «placeholder» so'zi — **taqiqni
tushuntiruvchi izoh** (`snapshot_id` bo'lmasa qator umuman chizilmaydi, na
placeholder na «yuklanmadi»), stub emas.

## Threat Flags

Yo'q. Reja **yangi tarmoq marshrutini, yangi auth yo'lini, yangi fayl kirish
naqshini va sxema o'zgarishini kiritmaydi** — u mavjud (rejalashtirilgan)
marshrutlarning **klient tomonidagi kontrakti**. Reja `<threat_model>` idagi
beshala `mitigate` dispozitsiyasi bajarildi:

| Threat ID | Qanday yopildi | Qayerda |
|-----------|----------------|---------|
| T-06-10 | `z.strictObject` + kalitlar to'plami **aynan** `{id,status,declared_soum,closed_at}`; `system_*`/`variance*` e'lon qilinmaydi va `null` ham yozilmaydi | `shift-queries.ts:103-108` |
| T-06-11 | Hisob va tarif identifikatorlari proyeksiyada **umuman yo'q**; statik darvoza + `strictObject` — ikki qatlam | `billing-pending-queries.ts`, `collect-surface.test.mjs` |
| T-06-12 | `gcTime: 0` + `staleTime: 0` + `removeQueries` **juftligi**; plus hook darajasidagi `matchesRequestedCode` | `billing-pending-queries.ts` |
| T-06-13 | `useRecentPayments()` **argumentsiz** va URL'ga so'rov parametri qo'shilmaydi — yig'indi yo'lini **marshrutning imkoniyati** to'sadi | `payment-queries.ts` |
| T-06-14 | Ism/telefon maydonlari G-22 reyestrida (16 nom), aylanib o'tuvchi nomlar taqiqi reyestr izohida | `collect-surface.test.mjs` |
| T-06-SC | `accept` — **yangi paket qo'shilmadi** (`package.json` tegilmadi) | — |

## Issues Encountered

1. **Rejadagi `grep -c "z.strictObject"` mezoni kod SHAKLINI boshqardi.**
   Dastlab `pendingStallSchema` va `anomalyRowSchema` `z\n  .strictObject({`
   ko'rinishida yozilgan edi (`.refine()` zanjiri uchun tabiiy formatlash) —
   `grep` esa **qatorma-qator** ishlaydi va bu shaklni **umuman ko'rmasdi**.
   Ikkala ta'rif `z.strictObject({` bitta qatorda bo'ladigan qilib qayta
   formatlandi. Bu 05-13 ning darsining takrori: **darvozaning o'zi kod
   shaklini boshqaradi**, va bu yaxshi — chunki keyingi o'quvchi ham
   `grep` bilan izlaydi.
2. **Zod 4 da `.refine()` semantikasi o'lchandi, taxmin qilinmadi.**
   `z.strictObject(...).refine().refine()` zanjirining (a) ortiqcha kalitni
   rad etishi, (b) ikkala invariant yo'nalishini ham ushlashi va (c)
   `apiFetch` ning `z.ZodType<T>` imzosiga mos kelishi alohida runtime
   zondida tasdiqlandi.

## User Setup Required

None — tashqi xizmat sozlanmasi talab qilinmaydi.

## Next Phase Readiness

**Tayyor:**
- 06-11 (kassir komponentlari) payload shaklini **o'ylab topmaydi** — u tayyor
  `pendingStallSchema` / `paymentResponseSchema` / `shiftCloseResponseSchema`
  ni iste'mol qiladi.
- 06-11 birinchi `components/collect/*.tsx` faylini qo'shgan zahoti
  `collect-surface.test.mjs` **hech qanday tahrirsiz** ishlay boshlaydi
  (G-22 · G-7 · G-28(d) · ommaviy amal) va `MIN_COLLECT_FILES = 5` chegarasi
  yoqiladi.
- 06-12/06-13 (direktor yuzasi) uchun `chargeList`/`anomalyList`/`shiftReport`
  sxemalari `items` va `rows` nomlari bilan G-25(c) ga tayyor.

**Bloklamaydi, LEKIN nomlangan:**
- ⚠ **Enum ko'zgulari birlashuvda birlashtirilishi kerak.** 06-02 `api-types.ts`
  ga `PAYMENT_METHODS`, `ADJUSTMENT_REASONS`, `REVERSAL_REASONS`,
  `ANOMALY_KINDS` ni qo'shadi. To'lqin birlashgach **birinchi iste'molchi reja
  (06-11)** bu to'rt reyestrni so'rov modullaridan `api-types.ts` importiga
  almashtirishi lozim — aks holda G-24/G-26 `api-types.ts` ning nusxasini
  o'lchab, so'rov modullaridagi nusxa **jimgina ajralib ketardi**. Har reyestr
  ustida shu eslatma **kodda ham** yozilgan.
- ⚠ **`PAYMENT_KINDS` 06-02 ning ro'yxatida yo'q** (`{payment, reversal}`) — u
  faqat shu rejada tug'ildi va ko'zgusi kerak bo'lsa 06-11 qo'shadi.
- ⚠ **`ADJUSTMENT_DIRECTIONS`** (`{increase, decrease}`) ham shu rejada
  tug'ildi; u 06-RESEARCH C-5 dan olingan va DL-3 ning 4-bo'limi uchun kerak.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
