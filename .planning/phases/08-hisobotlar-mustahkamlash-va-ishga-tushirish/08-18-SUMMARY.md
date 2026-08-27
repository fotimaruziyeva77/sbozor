---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 18
subsystem: ui
tags: [nextjs, app-router, nuqs, react-query, sonner, tdd, sabotage, registry-gate, wcag]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-03: threeWayReportSchema / DIFF_CLASSES / report-queries.ts (useThreeWayReport, useLedgerUpload, compareKey, downloadCompareReport)"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-14: POST /reports/compare/ledger + kind=ledger shabloni + uch ImportIssue kodi (uch tilda)"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-17: /reports sahifasi naqshi, /reports/compare havolasi, G-42(a) ikki shoxli total assert"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-09/08-13/08-15: ExportButton (kind=\"three-way\" shoxi), ro'yxatning O'ZI mazmun atributini chiqarish naqshi"
  - phase: 02-bozor-sozlash
    provides: "import-panel.tsx / import-errors.tsx — all-or-nothing import quvuri va 422 ro'yxati"
  - phase: 04-nvr-snapshot
    provides: "components/snapshots/day-picker.tsx — businessDayIn / isValidIsoDay / shiftIsoDay"
provides:
  - "components/reports/diff-cell.tsx — DIFF_VIEW reyestri (Record<DiffClassValue>), match uchun HECH NIMA, noma'lum sinf uchun zaxira yorliq"
  - "components/reports/compare-table.tsx — uch ustun + uch sanoq + maxraj; has_ledger=false da JADVAL YO'Q"
  - "components/reports/ledger-import.tsx — useCompareDay() (maksimum KECHA), CompareDayPicker, LedgerImport, DL-6, LEDGER_FILE_INPUT_ID"
  - "app/[locale]/(app)/reports/compare/page.tsx — uch blokli reyestr (data-compare-block), uchala locale'da SSG"
  - "lib/report-queries.ts::downloadLedgerTemplate() — ImportKind ga beshinchi a'zo QO'SHMASDAN"
  - "G-37(b), G-40(c)(d), G-41(c)(d) darvozalari (+30 test) va G-42(a) ning QATTIQLASHGAN holati"
affects:
  - 08-20
  - 09

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ICU platsholderi DOM tuguniga aylana olmaydi (next-intl qiymati `string|number|Date`) — «uch alohida tugun» talabi reyestrdan iteratsiya bilan bajariladi, kalit esa katalogda KANONIK jumla bo'lib qoladi"
    - "«Ko'rinadigan matn yo'q» da'vosi TUGUNMA-TUGUN yig'iladi: `textContent` qo'shni jumlalarni yopishtiradi (1 + 287 -> 1287) va da'vo yolg'on-qizil bo'lardi"
    - "Bo'sh holat payload'i ATAYIN QATORLI bo'lishi kerak: `rows: []` boshqa shoxga tushib sabotajni jimgina o'tkazardi"
    - "Nomlangan holat da'vosi BLOKKA doiralanadi — ayni matnni qo'shni blok chizsa, sahifa bo'yicha yozilgan assert yolg'on-yashil bo'ladi"
    - "Manba skani tokeni komponentning HAQIQIY prop nomiga moslanadi (`confirmVariant`), aks holda darvoza tip jihatidan bajarilmas talabga aylanadi"

key-files:
  created:
    - frontend/src/components/reports/diff-cell.tsx
    - frontend/src/components/reports/compare-table.tsx
    - frontend/src/components/reports/compare-table.test.tsx
    - frontend/src/components/reports/ledger-import.tsx
    - frontend/src/components/reports/ledger-import.test.tsx
    - frontend/src/app/[locale]/(app)/reports/compare/page.tsx
    - frontend/src/app/[locale]/(app)/reports/compare/page.test.tsx
  modified:
    - frontend/src/lib/report-queries.ts
    - frontend/src/components/import/import-errors.tsx
    - frontend/scripts/report-copy.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "08-18: `compare.diffCounts` CHAQIRILMAYDI va sabab O'LCHANGAN — next-intl ICU qiymati `string|number|Date` (`use-intl/.../TranslationValues.d.ts`), ya'ni uch sanoq BITTA matn tuguniga tushardi va G-41(c) mexanik jihatdan bajarilmas bo'lardi; kalit G-43(d) uchun katalogda qoldi va uch tugun aynan o'sha jumlani qayta quradi"
  - "08-18: «Sotuvchi» ustuni QO'YILMADI — `threeWayRowSchema` (08-03, MUZLATILGAN `strictObject`) da bunday maydon YO'Q; doimo bo'sh ustun imzolanadigan varaqda «300 rastaning egasi noma'lum» bo'lib o'qilardi (D-08 sinfi)"
  - "08-18: «Farq» ustuni SON emas, SINF badge'i — kontraktda `diff_soum` yo'q va uni klientda hisoblash D-03 ning bevosita buzilishi bo'lardi (05-14 darsi: qayta hisob IKKINCHI JAVOB bo'lib chiqadi)"
  - "08-18: G-42(a) darvozasi REGISTRSIZ qidiradigan qilindi — `ConfirmDialog` propi `confirmVariant` va registrga sezgir shakl tip jihatidan TO'G'RI yagona yozuvda ham Set(0) qaytarardi (08-17 ning S-5c simulyatsiyasi `tsc` dan o'tmagan sun'iy fayl edi)"
  - "08-18: `has_ledger=false` qarori SAHIFADA emas, `compare-table.tsx` ICHIDA — mazmun atributi HAR holatda chiqishi kerak, aks holda daftarsiz kun blok darvozasini qizartirardi"
  - "08-18: beshinchi eksport (`kind=\"three-way\"`) qo'shildi va daftarsiz kunda `aria-disabled` — §12.6 tasdiq qatorlari tufayli fayl «hamma farq 0» varaqasi bo'lib chop etilardi (T-08-79 ning FAYL yarmi)"
  - "08-18: `downloadLedgerTemplate()` alohida funksiya — `ImportKind` OQIM tavsifi (marshrut + panel matni + reestr yo'li) va daftarda ularning birortasi yo'q"

patterns-established:
  - "Darvozaning ko'r nuqtasi sabotaj bilan TOPILADI va darvoza QATTIQLASHADI — mahsulot emas, assert tuzatiladi (bu yerda ikki marta: bo'sh payload va doiralanmagan matn)"
  - "Sabotajning IKKI-UCH SHAKLI DOM darvozalarida majburiy: bir shakl bir qatlamni, boshqasi ikkinchisini qizartiradi (G-41(c) ning ikki yarmi shu bilan ajratildi)"

requirements-completed: [RECON-04]

# Metrics
duration: 55min
completed: 2026-08-16
---

# Phase 8 Plan 18: Uch tomonlama solishtiruv ekrani Summary

**Parallel rejimning kunlik asbobi tug'ildi: daftar `.xlsx` bo'lib ekrandan yuklanadi (bitta tasdiq, maksimum KECHA), uch farq sinfi uch ALOHIDA sanoqda ko'rinadi va ularni qo'shish mexanik ravishda imkonsiz, daftarsiz kunda esa jadval UMUMAN chizilmaydi — uchala da'vo ham sabotaj bilan o'lchandi va ikkitasi darvozaning O'Z ko'r nuqtasini fosh qildi.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3/3 (hammasi TDD: RED -> GREEN)
- **Commits:** 10 (3 × RED, 3 × GREEN, 4 × fix/hardening)
- **Files:** 13 (7 yangi, 6 o'zgargan)

## Accomplishments

- **`/reports/compare` marshruti tug'ildi va uchala locale'da SSG.** 08-17 qoldirgan 404 havola yopildi; `ExportButton` ning `kind="three-way"` shoxi (08-09 dan beri o'lik) endi HAQIQATAN chaqiriladi.
- **§10.6 — fazaning eng qimmat bandi mexanik bo'ldi.** Daftar yo'q kunda `comparison` bloki jadval ham, uch sanoq ham chizmaydi; faqat nomlangan holat va keyingi qadam. **Sabotaj bu da'voning ikkita ko'r nuqtasini fosh qildi** (quyida S-1) va ikkalasi ham darvozada tuzatildi.
- **§10.5 — uch sanoq uch ALOHIDA `data-diff-count` tugunida** va ularni birlashtirgan son yo'q. Ikki xil sabotaj darvozaning ikki yarmini ALOHIDA qizartirdi, ya'ni ular bir-birini takrorlamasligi isbotlandi.
- **G-42(a) ikkala shoxi ham EGASINI TOPDI:** `variant="default"` **aynan 1** (`[Daftarni yuklash]`, `size="lg"`) va destruktiv variant **aynan 1 va `ConfirmDialog` chaqiruvida**. ⚠ Lekin darvozaning O'ZI tuzatilishi kerak bo'ldi — Decisions №4.
- **G-38(a) toza qoldi:** `components/reports/**` mahsulot fayllarida oltala havola tokeni ham **0**. Bo'sh holatning amali havola emas, **fokus ko'chirish** (a11y jihatidan ham to'g'riroq).
- **Yangi npm paketi yo'q** (T-08-SC): `package.json` va lockfile **tegilmadi**.

## Task Commits

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | Solishtiruv jadvalining darvozalari — **RED** | `bdd78cd` |
| 2 | Daftar importi darvozalari + 10 yangi kalit — **RED** | `60aae1c` |
| 3 | `ledger-import.tsx` + `useCompareDay` — **GREEN** | `e04e5d6` |
| 4 | `diff-cell.tsx` + `compare-table.tsx` — **GREEN** | `835f56d` |
| 5 | `/reports/compare` blok darvozasi — **RED** | `6a7522f` |
| 6 | G-42(a) darvozasi registrsiz qidiradi (Rule 3) | `20516b7` |
| 7 | Copy qoidasi: `.xlsx` matnda yozilmaydi (Rule 3) | `35a9ac4` |
| 8 | `/reports/compare` sahifasi — **GREEN** | `647ec99` |
| 9 | G-40(d) sabotajdan keyin QATTIQLASHTIRILDI | `6d698e6` |
| 10 | Rad etilgan daraja nomi izohdan olib tashlandi | `adf5d99` |

## Sabotaj o'lchovlari (majburiy — reja Task 3)

| # | Sabotaj | Kutilgan | **Natija** |
|---|---------|----------|------------|
| **S-1a** | `has_ledger` butunlay e'tiborsiz qoldirildi (jadval doim chiziladi) | G-40(d) qizarsin | ⚠⚠ **KOMPONENT darvozasi qizardi, SAHIFA darvozasi YASHIL QOLDI.** Ikkala assert ham ko'r edi: `rows: []` «daftar bor, qator yo'q» shoxiga tushardi (jadval baribir chizilmasdi), sahifadagi `compare.ledgerMissing` da'vosini esa **`ledger` bloki** o'z holat qatori bilan qondirardi |
| **S-1b** | O'sha sabotaj, **qattiqlashtirilgan** darvozaga qarshi | ikkalasi ham qizarsin | ✅ **IKKALASI HAM QIZARDI:** `expected <table …> to have a length of +0 but got 1` — ham `compare-table.test.tsx`, ham `page.test.tsx` |
| **S-2a** | `ai_expected: null` -> `format.number(… ?? 0)` | G-40(c) qizarsin | ✅ **QIZARDI:** `expected '0' to be ''` |
| **S-2b** | `null` -> `"—"` (to'qilgan tire) | G-40(c) qizarsin | ✅ **QIZARDI:** `expected '—' to be ''` |
| **S-2c** | `null` -> `<span>0</span>` (bevosita tugun EMAS) | G-40(c) qizarsin | ✅ **QIZARDI:** `expected '0' to be ''` — ya'ni 08-13 dagi razmetka-chuqurligi ko'rligi bu yerda **takrorlanmadi** |
| **S-3a** | Uch sanoq bitta songa qo'shildi | G-41(c) qizarsin | ✅ **IKKALA YARIM HAM QIZARDI:** `expected [] to deeply equal ['ledger_over','system_over','ai_mismatch']` **va** `expected [6, 287] to deeply equal [3, 2, 1, 287]` |
| **S-3b** | Uch tugun QOLDI, **to'rtinchi «Jami» qatori** qo'shildi | faqat ikkinchi yarim qizarsin | ✅ **AYNAN SHUNDAY:** «uch alohida tugun» **yashil** (uchtasi joyida), «birlashtirgan son yo'q» **qizil**: `expected [3, 2, 1, 6, 287] to deeply equal [3, 2, 1, 287]`. Ya'ni ikki assert **boshqa-boshqa** narsani o'lchaydi |

⛔ **Yettala sabotaj ham QAYTARILDI**; qaytarishdan keyin `git status` mahsulot fayllari bo'yicha **toza** va butun to'plam yashil (quyida).

⚠ **Eng qimmat topilma S-1:** sabotaj darvozani emas, **darvozaning ko'rligini** fosh qildi. Ikkala tuzatish ham `6d698e6` da va ikkalasi ham kodda LITERAL izohlangan — «`rows: []` boshqa shoxga tushadi» va «ayni matnni qo'shni blok chizadi».

## Files Created/Modified

- `frontend/src/components/reports/diff-cell.tsx` — farq sinfining uch kanali (rang + ikonka + matn); `match` uchun **hech nima**, noma'lum sinf uchun zaxira yorliq
- `frontend/src/components/reports/compare-table.tsx` — uch sanoq + maxraj + besh ustunli jadval; `has_ledger=false` va `rows=[]` uchun **ikki xil** nomlangan holat
- `frontend/src/components/reports/ledger-import.tsx` — `useCompareDay()` (maksimum **kecha**), `CompareDayPicker`, `LedgerImport` (shablon -> fayl -> DL-6 -> toast/422)
- `frontend/src/app/[locale]/(app)/reports/compare/page.tsx` — uch blok, `Suspense`, huquq ko'zgusi, beshinchi eksport
- `frontend/src/lib/report-queries.ts` — `downloadLedgerTemplate()` (`ImportKind` **kengaytirilmadi**)
- `frontend/src/components/import/import-errors.tsx` — uch daftar kodi tarjima xaritasiga qo'shildi
- `frontend/scripts/report-copy.test.mjs` — `matchIndexes()` (satr **yoki** regeks) + G-42(a) registrsiz + yangi o'lchov testi
- `frontend/messages/*.json` — **10 yangi kalit** × 3 til (uz-Cyrl `i18n:gen` bilan)
- Uch test fayli — **30 yangi test**

## Decisions Made

### 1. ⛔⛔ «Sotuvchi» ustuni QO'YILMADI — kontraktda bunday maydon YO'Q

Reja `<action>` da ustunlarni «rasta kodi · **sotuvchi** · daftar · tizim · AI-kutilgan · farq · sinf» deb sanagan va «sotuvchi ismi topilmasa bo'sh katak + `sr-only`» talabini qo'ygan. Lekin **`threeWayRowSchema` (08-03, 1-to'lqinda MUZLATILGAN `z.strictObject`)** aynan besh maydondan iborat: `stall_code`, `ledger_soum`, `system_soum`, `ai_expected_soum`, `diff_class`. **Sotuvchi maydoni YO'Q.**

| Muqobil | Nega rad etildi |
|---------|------------------|
| Kontraktga maydon qo'shish | ⛔ 08-16 SHU TO'LQINDA o'sha kontraktga yozyapti — `strictObject` ga maydon qo'shish ikkala tomonni ham sindirardi |
| Ikkinchi so'rov (sotuvchi reestri) | ⛔ D-07/08-13 qarori: hisobot yuzasi **ikkinchi so'rov yubormaydi**, aks holda audit sotuvchi boshiga yozilardi |
| Doimo bo'sh ustun + `sr-only` | ⛔ **Eng yomoni:** 300 qatorlik varaqda har qatorda «Sotuvchi ko'rsatilmagan» — bu D-08 ning teskarisi: **o'lchanmagan** narsa **o'lchangan yo'qlik** bo'lib o'qilardi |

**Qaror:** ustun qo'yilmadi. ⚠ UI-SPEC §10.4 ham aynan **uch manba ustunini** sanaydi va §14.3 da sotuvchi ustuni uchun **kalit yo'q** — ya'ni reja bandi 08-13 (qarzdorlik ro'yxati) naqshidan meros bo'lib qolgan.

### 2. «Farq» ustuni — SINF badge'i, SON emas

Reja «farq» va «sinf badge'i» ni **ikki** ustun qilib sanagan. Kontraktda `diff_soum` **yo'q** va uni klientda `ledger - system` bilan hisoblash ⛔ D-03 ning bevosita buzilishi bo'lardi (05-14 darsi: klientdagi qayta hisob xato bo'lib emas, **ikkinchi javob** bo'lib chiqadi — ikkalasi ham arifmetik to'g'ri, lekin boshqa savolga javob). §7.3 ning «uch ustun va farq ustuni `font-mono`» bandi uch pul ustuni bilan bajarildi (`font-mono` sanog'i: **6**).

### 3. ⛔ `compare.diffCounts` chaqirilmaydi — mexanik sabab, did emas

`next-intl` da ICU platsholderining qiymati `string | number | Date` (`use-intl/dist/types/core/TranslationValues.d.ts`), **`ReactNode` emas**. Ya'ni `t("compare.diffCounts", …)` uch sanoqni **bitta matn tuguniga** qo'yardi va G-41(c) ning «uch alohida tugun» sharti **bajarilmas** bo'lardi.

**Qaror:** uch sanoq `DIFF_CLASSES` reyestridan **iteratsiya** bilan chiziladi (`compare.diff.*` yorliqlari + `·` ajratgich), ya'ni ekrandagi jumla `compare.diffCounts` bilan **so'zma-so'z bir xil**. Kalitning o'zi katalogda **qoladi**: G-43(d) uni uchala locale'da platsholderlari bilan qulflaydi va u shu jumlaning **kanonik** shakli.

### 4. ⛔⛔ G-42(a) DARVOZASINING O'ZI bajarilmas edi — O'LCHANDI

08-17 darvozani «egasi kelganda `variant="destructive"` **aynan 1** va u `ConfirmDialog` chaqiruvida» deb yozgan va S-5c simulyatsiyasi bilan o'lchagan. ⚠ Lekin o'sha simulyatsiya **`tsc` dan o'tmaydigan sun'iy fayl** edi.

**Haqiqiy `ConfirmDialog` ning propi — `confirmVariant`** (`ui/confirm-dialog.tsx`: `confirmVariant?: ButtonProps["variant"]`). Ya'ni:

- `confirmVariant="destructive"` -> token **katta harf** bilan (`Variant=`) uchraydi, registrga sezgir qidiruv uni **topmaydi** (o'lchandi: `Set(0)` vs kutilgan `Set(1)`);
- `<ConfirmDialog variant="destructive">` -> ⛔ **`tsc` xatosi**, bunday prop **yo'q**.

**Qaror (Rule 3 — bloklovchi):** `matchIndexes()` yordamchisi qo'shildi (satr **yoki** regeks) va destruktiv token `/variant="destructive"/giu` bo'ldi. ⚠ Bu darvozani **bo'shatmaydi, kengaytiradi**: registrsiz shakl `<Button variant="destructive">` ni ham ushlaydi (o'shanda teg egasi `Button` bo'lib qizaradi). Qo'shimcha **o'lchov testi** registrga sezgir shakl bugun **0** topishini qulflaydi — faraz eskirsa (prop nomi o'zgarsa) u qizaradi.

### 5. `has_ledger` qarori SAHIFADA emas, komponent ICHIDA

Reja bandini so'zma-so'z bajarish («`comparison` bloki jadval chizmaydi» — sahifada) mazmun atributini yo'qotardi: `data-compare-content="comparison"` ni **komponentning o'zi** chiqarishi kerak (reja Task 1), ya'ni daftarsiz kunda blok umuman mazmun bermasdi va **G-37(b) ning juftlik yarmi qizarardi**. Qaror `compare-table.tsx` ning ichida yashaydi; sahifa u yerga **ikkinchi shart yozmaydi**.

### 6. Beshinchi eksport qo'shildi (Rule 2) va daftarsiz kunda o'chirilgan

Reja sahifa uchun eksport tugmasini nomlamagan, lekin §12.1 uni **beshinchi eksport** deb sanaydi, `ExportButton` da `kind: "three-way"` shoxi **08-09 dan beri mavjud va chaqirilmagan**, 08-16 esa `/reports/compare.xlsx` ni shu to'lqinda quryapti. ⛔ Muhimi: §12.6 ga ko'ra faylning **pastida ikki bo'sh tasdiq qatori** bor, ya'ni daftarsiz kunning fayli «hamma farq 0» varaqasi bo'lib **chop etilardi** — ekrandagi taqiq faylda aylanib o'tilardi. Shuning uchun nishon `has_ledger` ga bog'landi va bu **alohida test** bilan o'lchandi.

### 7. Vazifalar tartibi almashtirildi (Task 2 -> Task 1)

`compare-table.tsx` `useCompareDay()` va `LEDGER_FILE_INPUT_ID` ni `ledger-import.tsx` dan oladi (reja `useCompareDay` ni **Task 2** ga bergan). Fayllarni butun holda commit qilish uchun GREEN qadamlar shu tartibda bajarildi: ledger-import -> compare-table -> sahifa. Har vazifaning **RED testi o'z GREEN idan oldin** qoldi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] G-42(a) darvozasi tip jihatidan bajarilmas edi**

- **Found during:** Task 3 dan keyingi `test:unit` yugurishi
- **Issue:** `report-copy.test.mjs:1163` registrga sezgir `'variant="destructive"'` izlaydi; haqiqiy chaqiruv esa `confirmVariant="destructive"` — ya'ni `Set(0)` vs kutilgan `Set(1)`. `<ConfirmDialog variant="destructive">` yozish `tsc` xatosi bo'lardi (bunday prop yo'q), ya'ni darvoza **hech qanday to'g'ri yozuvda** bajarilmasdi.
- **Fix:** `matchIndexes()` (satr yoki regeks) + `DESTRUCTIVE_VARIANT = /variant="destructive"/giu`; `countByFile` va `jsxOwnersOf` shundan foydalanadi. Qo'shimcha o'lchov testi farazni qulfladi.
- **Verification:** `node --test scripts/report-copy.test.mjs` -> **44/44** (avval 43; +1 o'lchov testi)
- **Committed in:** `20516b7`

**2. [Rule 3 — Blocking] `.xlsx` matn ichida yozib bo'lmaydi**

- **Found during:** Task 3 dan keyingi `test:unit` yugurishi
- **Issue:** `gen-cyrillic.test.mjs` Qoida 1: `uz-Latn.json` va `ru.json` da `.xlsx` shakli **taqiq** (transliteratsiyada buziladi). Yangi `compare.ledgerFile` kaliti «(.xlsx)» bilan yozilgan edi va **ikki test qizardi**.
- **Fix:** «(.xlsx)» -> «(Excel)» (uz-Latn va ru), uz-Cyrl `i18n:gen` bilan qayta hosil qilindi.
- **Verification:** `npm run test:unit` -> **296/296**; `i18n:check` -> **1362 kalit × 3 til**
- **Committed in:** `35a9ac4`

**3. [Rule 2 — Missing Critical] Uch daftar xato kodi komponentda tarjimasiz edi**

- **Found during:** Task 2 (422 shoxini yozish)
- **Issue:** 08-14 uchta yangi `ImportIssue` kodini (`ledger_stall_unknown`, `ledger_amount_invalid`, `ledger_duplicate_stall`) uchala `messages/*.json` ga qo'shgan, lekin `import-errors.tsx` dagi `ERROR_LABEL_KEYS` **xaritasiga** qo'shmagan. Xaritasiz kod **zaxira shoxga** tushib serverning `message` maydonini chizardi — u esa **faqat uz-Latn** (`ImportIssue` docstringi buni literal aytadi), ya'ni rus tilidagi admin tarjimasiz matn ko'rardi va «3 til majburiy» cheklovi **jimgina** buzilardi.
- **Fix:** uchala kalit xaritaga qo'shildi.
- **Verification:** `ledger-import.test.tsx` da alohida test — ekranda **tarjima** bor, server matni (`"server matni"`) **yo'q**.
- **Committed in:** `e04e5d6`

**4. [Rule 2 — Missing Critical] Beshinchi eksport va uning daftarsiz kundagi taqig'i**

- **Found during:** Task 3
- **Issue:** Reja sahifa uchun eksport tugmasini nomlamagan; §12.1 esa solishtiruv eksportini **beshinchi** deb sanaydi va §12.6 faylning pastiga **tasdiq qatorlarini** qo'yadi. Tugmasiz butun qog'oz jarayon (D-19) **erishib bo'lmas** bo'lardi; shartsiz tugma esa daftarsiz kunning «hamma farq 0» varaqasini **chop etishga** ruxsat berardi.
- **Fix:** `comparison` blokiga `<ExportButton day kind="three-way" unavailable={has_ledger !== true}/>`.
- **Verification:** `page.test.tsx` — «daftarsiz kunda eksport ham taklif qilinmaydi» (`aria-disabled="true"`).
- **Committed in:** `647ec99`

**5. [Rule 1 — Bug] `level: 2` tokeni izohlarda LITERAL yozilgan edi**

- **Found during:** Qabul mezonlarini mexanik tekshirish
- **Issue:** `grep -c 'level: 2\|level={2}'` -> **4** (hammasi izohda). Mezon **0** talab qiladi va kodbaza konvensiyasi taqiqlangan tokenni izohda literal yozishni ta'qiqlaydi — aks holda darvoza o'ziga qarshi ishlaydi (07/08 fazalarda ayni sinf).
- **Fix:** izohlar «ikkinchi daraja» so'zi bilan qayta yozildi; sabab mulohazasi **to'liq saqlandi**.
- **Verification:** `grep -c` -> **0**; `ledger-import` testlari **10/10**
- **Committed in:** `adf5d99`

**6. [Rule 1 — Bug] Sahifa izohida taqiqlangan tasdiq tokeni bor edi**

- **Found during:** Task 3 GREEN
- **Issue:** `page.tsx` izohida «IMZOLANARDI» so'zi bor edi va D-19 manba skani (`/imzola/giu`) uni topdi.
- **Fix:** ibora «qog'ozga chiqardi va TASDIQLANARDI» ga o'zgartirildi + konvensiya izohi qo'shildi.
- **Verification:** `grep -ci "imzolash\|\[Sign"` -> **0**; test yashil.
- **Committed in:** `647ec99`

### Chetlanishlar (qamrov o'zgarmagan)

**7. Sotuvchi ustuni va farq SONI qo'yilmadi** — Decisions №1 va №2 (muzlatilgan kontraktda maydon yo'q; klientda hisoblash D-03 buzilishi).

**8. `ledger-import.test.tsx` yaratildi** — reja uni `files_modified` da nomlamagan, lekin Task 2 ning `<verify>` i aynan `test:component -- ledger-import` ni buyuradi (fayl bo'lmasa vitest «test topilmadi» bilan yiqilardi) va TDD ham uni talab qiladi. **10 test.**

**9. `report-queries.ts` va `import-errors.tsx` o'zgardi** — ikkalasi ham `files_modified` da yo'q; sabablari Deviations №1/№3 da (shablon yo'li va uch tilli xato matni).

**10. Vazifalar tartibi** — Decisions №7 (bog'liqlik yo'nalishi: `compare-table` -> `ledger-import`).

**11. 422 ro'yxatida 50 qator, reja aytgan 5 emas.** `import-errors.tsx` ning `MAX_VISIBLE_ROWS = 50` konstantasi **2-fazaning** qarori (T-02-122) va uni 5 ga tushirish rasta/sotuvchi/xodim importlarini ham o'zgartirardi. §10.3 ning talabi — «ikkinchi oqim qurilmaydi» — bajarildi; qolgani baribir `.xlsx` bo'lib yuklab olinadi.

---

**Total deviations:** 6 auto-fixed (2 blocking, 2 missing-critical, 2 bug) + 5 hujjatlashtirilgan chetlanish
**Impact on plan:** Qamrov kengaymadi. №1 va №2 rejani umuman yakunlash uchun **zarur** edi (aks holda `npm run gate` qizil); №3 va №4 mahsulotning e'lon qilingan kontraktini (3 til, D-19 qog'oz jarayoni) bajaradi; №5/№6 mexanik mezonlarning o'zini tiklaydi.

## Verification Evidence

| Buyruq | Natija |
|--------|--------|
| `npm --prefix frontend test` | ✅ **296 unit + 1110 vitest** (94 fayl) |
| `npx vitest run compare` | ✅ **21/21** (`compare-table` 9, `compare/page` 12) |
| `npx vitest run ledger-import` | ✅ **10/10** |
| `node --test scripts/report-copy.test.mjs` | ✅ **44/44** (avval 43) |
| `npm --prefix frontend run typecheck` | ✅ EXIT 0 |
| `npm --prefix frontend run lint` | ✅ EXIT 0 |
| `npm --prefix frontend run i18n:check` | ✅ **1362 kalit × 3 til** (avval 1352; +10) |
| `npm --prefix frontend run build` | ✅ EXIT 0 — `/[locale]/reports/compare` **uchala locale'da SSG** |

**Qabul mezonlari (mexanik):**

| Mezon | Talab | Natija |
|-------|-------|--------|
| `diff-cell.tsx` `DIFF_CLASSES` dan hosila | ha | **ha** ✅ (`Record<DiffClassValue>` + `DIFF_ORDER`) |
| `grep -cE "total_diff\|totalDiff\|combined\|grand_total" compare-table.tsx` | 0 | **0** ✅ |
| `compare.matched` ishlatilgan | ha | **1** ✅ |
| `grep -c "font-mono" compare-table.tsx` | ≥1 | **6** ✅ |
| `useCompareDay` ishlatilgan + maksimum `shiftIsoDay(todayIso, -1)` | ha | **ha** ✅ (3 + 1 uchrash) |
| `grep -c "removeQueries" ledger-import.tsx` | 0 | **0** ✅ |
| `grep -c 'level: 2\|level={2}' ledger-import.tsx` | 0 | **0** ✅ (avval 4 — Deviations №5) |
| `grep -c 'variant="default"' ledger-import.tsx` | 1 | **1** ✅ |
| `compare/page.tsx` mavjud va `Suspense` ishlatadi | ha | **ha** ✅ (4 uchrash) |
| `grep -c "data-compare-content" compare/page.tsx` | 0 | **0** ✅ |
| `grep -ci "imzolash\|\[Sign" compare/page.tsx` | 0 | **0** ✅ |
| `page.test.tsx` da `CONTENT_EXEMPT.size === 1` alohida assert | bor | **bor** ✅ |
| G-40(c) `null` va `0` ni BITTA testda ajratadi | ha | **ha** ✅ (uchinchi assert farqni o'lchaydi) |
| G-38(a) tokenlari `components/reports/**` mahsulot fayllarida | har biri 0 | **0** ✅ |
| Uchala sabotaj o'lchandi | ha | **yettita shakl** ✅ |

## Known Stubs

**Yo'q** — uchala blok ham haqiqiy komponentlarni chizadi va mazmun juftligi buni mock'dan hosila da'volar bilan o'lchaydi.

⚠ **Ikkita TO'LQIN TARTIBI bandi bor va ular stub EMAS:**

1. ⛔ **`GET /reports/compare` va `GET /reports/compare.xlsx` (08-16) shu to'lqinda PARALLEL ishlayapti** va mening bazamda **yo'q**. Ikkala tomon ham 08-03 da muzlatilgan `threeWayReportSchema` ga qarab yozildi; birlashtirilgandan keyin ekranda haqiqiy ma'lumot ko'rinadi. Marshrut hali yo'q bo'lsa `comparison` bloki **nomlangan xato** (`role="alert"`) ko'rsatadi — bo'sh jadval ham, nol ham emas.
2. ⚠ **Kun tanlagichida oldinga/orqaga tugmalari YO'Q** — faqat `<input type="date">`. §10.2 tanlagichning shaklini belgilamagan (u «6-fazanikini qayta ishlatadi» deydi, lekin `useBillingDay` ning **hooki** rad etilgan); `/billing` dagi tanlagichda ham faqat maydon bor.

## Threat Flags

Yangi xavfsizlik yuzasi **topilmadi** — barcha o'zgarishlar rejaning `threat_model` reyestri ichida:

| Threat ID | Holat |
|-----------|-------|
| T-08-79 | ✅ **mitigate** — G-40(d) **ikki qatlamda** (komponent + sahifa) va **sabotaj S-1b** bilan o'lchandi; qo'shimcha: **fayl yarmi** ham yopildi (daftarsiz kunda eksport `aria-disabled`) |
| T-08-80 | ✅ **mitigate** — G-40(c) + **uch xil** sabotaj (S-2a/b/c) |
| T-08-81 | ✅ **mitigate** — G-41(c) ikki yarmi + **ikki xil** sabotaj (S-3a/b); `total_diff` sinfidagi o'nta nom **0** |
| T-08-82 | ✅ **mitigate** — `ConfirmDialog` birinchi daraja; tasdiqdan **oldin** so'rov 0 ekani alohida assert bilan |
| T-08-83 | ✅ **mitigate** — tasdiq tugmasi qurilmadi; manba skani `/imzola/`, `/\[Sign/`, `/signed/` ni **0** ga qulflaydi |
| T-08-84 | ✅ **mitigate** — `report_view` ko'zgusi; kassirda **birorta so'rov ketmasligi** o'lchandi |
| T-08-SC | ✅ Yangi npm paketi **yo'q**; `package.json` va lockfile **tegilmadi** |

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi** (asosiy repo katalogi ham bo'sh). **Yechim:** worktree ichida `npm ci` — lockfile'dan, yangi paketsiz; `package.json` va `package-lock.json` **tegilmadi**.
- **Sabotaj darvozaning ko'rligini fosh qildi** (S-1) — tuzatish **testda**, mahsulotda emas. Ikkala ko'r nuqta ham kodda LITERAL izohlangan.
- **`compare-table.test.tsx` dagi `visibleChunks` yordamchisi** ham o'lchov bilan asoslandi: sodda `textContent` shakli `1` va `287` ni **`1287`** qilib yopishtiradi va da'vo mahsulotda hech qanday nosozliksiz qizarardi. Bu **alohida test** bilan qulflandi (faraz eskirsa qizaradi).
- ⚠ **`gate:fast` byudjeti bu yerda ham O'LCHANMADI** — 08-03/08-09/08-13/08-15/08-17 dagi ayni sabab (`test:fast` `docker compose --profile test` ni ko'taradi va parallel ishlayotgan 08-16 agentiga aralashardi). **O'lchangan yarim:** `vitest run` -> **88–142 s** (94 fayl, 1110 test) va `build` -> **15,2 s** kompilyatsiya. ⛔ Byudjet **o'zgartirilmadi**.

## User Setup Required

Yo'q.

## Next Phase Readiness

**Tayyor:**
- **08-20** (mezon testi) uchun `/reports/compare` uchala locale'da SSG va blok atributi bilan o'lchanadigan holatda.
- **Parallel rejim (hafta 13–16)** uchun kunlik oqim to'liq: kun tanlash -> shablon -> daftar yuklash -> uch ustunli solishtiruv -> `.xlsx` eksport -> qog'ozda tasdiq.

**⛔ KEYINGI IJROCHINING ZIMMASIDA:**

1. ⛔ **08-16 birlashtirilgandan keyin uchidan-uchiga tekshiruv:** klient `GET /reports/compare?day=` va `GET /reports/compare.xlsx?day=` ga boradi (`report-queries.ts:253`, `:383`), 08-14 esa server tomonda `/three-way` nomini **eskirgan** deb belgilagan. Marshrut nomlari mos kelmasa nosozlik **faqat jonli ekranda** ko'rinadi — komponent testlari mock bilan yashil qoladi.
2. ⛔ **`ImportKind` ga «ledger» QO'SHILMASIN** — `downloadLedgerTemplate()` ataylab alohida (Decisions/`report-queries.ts` izohi): `ImportKind` marshrut + panel matni + reestr yo'liga bog'langan va daftarda ularning birortasi yo'q.
3. ⚠ **G-42(a) endi TO'LIQ QATTIQ:** `ledger-import.tsx` dan `variant="default"` yoki `confirmVariant="destructive"` ni olib tashlash darvozani **darhol** qizartiradi; ularni boshqa faylga ko'chirish ham (to'plam tengligi fayl **nomini** o'lchaydi).
4. ⚠ **`compare.diffCounts` kaliti ATAYIN chaqirilmaydi** — uni «o'lik kalit» deb o'chirish G-43(d) ni qizartiradi va ekrandagi jumlaning kanonik manbasini yo'qotardi (sabab `compare-table.tsx` izohida LITERAL).

**Ochiq bandlar:**
- ⚠ `gate:fast` byudjeti to'liq o'lchanmadi (yuqoriga qarang).
- ⚠ Kun tanlagichida navigatsiya tugmalari yo'q (Known Stubs 2) — parallel rejim tajribasi ko'rsatsa qo'shiladi.

## Self-Check: PASSED

**Fayllar (13/13 topildi):**
- `frontend/src/components/reports/diff-cell.tsx` · `compare-table.tsx` · `compare-table.test.tsx`
- `frontend/src/components/reports/ledger-import.tsx` · `ledger-import.test.tsx`
- `frontend/src/app/[locale]/(app)/reports/compare/page.tsx` · `page.test.tsx`
- `frontend/src/lib/report-queries.ts` · `frontend/src/components/import/import-errors.tsx`
- `frontend/scripts/report-copy.test.mjs`
- `frontend/messages/uz-Latn.json` · `ru.json` · `uz-Cyrl.json`

**Commitlar (10/10 topildi):** `bdd78cd` · `60aae1c` · `e04e5d6` · `835f56d` · `6a7522f` · `20516b7` · `35a9ac4` · `647ec99` · `6d698e6` · `adf5d99`

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN tegilmadi** — worktree rejimida ular orkestratorning zimmasida (to'lqin merge qilingandan keyin markazlashgan holda yangilanadi).

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
