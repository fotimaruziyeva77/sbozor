---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 16
subsystem: ui
tags: [wizard, nuqs, a11y, aria-disabled, xlsx-import, all-or-nothing, sabotage, i18n]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-13 — `api-types.ts` sxemalari, `market-queries.ts` hooklari (`useSetupStatusQuery`, `useCreateMarket`, `useActivateMarket`, `useImportMutation`, `downloadTemplate`, `downloadErrorReport`, `importErrorsOf`), `wizard`/`import` namespace'lari; 02-15 — `ZoneList`, `CategoryList`, `TariffList` + `TariffDialog` (`min_valid_from` bilan), `WeekdayPicker`, `ExceptionList`, `ExceptionDialog`, `VendorList`; 02-14 — `StallList`, `StallDialog`, `StallCategoryDialog`, `StallCardDialog`; 02-12 — import endpointlari va 422 `errors[]` + `error_counts`; 02-11 — `POST /markets`, `setup-status`, `activate` (409 + `blocking[]`), `DELETE` qoralama; 02-02 — `ui/` primitivlari"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`rbac.ts`, `auth-store.ts`, `useSelectMarket`, nuqs, vitest + jsdom naqshi, `gen-cyrillic.mjs` + `check-messages.mjs`"
provides:
  - "`/[locale]/(app)/markets/new` — ustaning 1-qadami (qoralama bozor tug'iladi)"
  - "`/[locale]/(app)/markets/setup?step=N` — 2–7-qadamlar; 02-03 dagi bozor tanlash marshruti endi HAQIQIY sahifaga tushadi"
  - "`components/wizard/wizard-steps.ts` — yetti qadamning YAGONA manbai + `CAMERA_PLACEHOLDER` + `wizardStepViews()` / `fallbackStep()`"
  - "`components/wizard/wizard-stepper.tsx` — to'rt holat x uch kanal, bloklangan qadam SABABI bilan"
  - "`components/wizard/wizard-shell.tsx` — rels + kontent, holat serverdan"
  - "`components/wizard/market-requisites-form.tsx` — 1-qadam formasi (autosave YO'Q, sana chegarasi YO'Q)"
  - "`components/wizard/activation-panel.tsx` — §6.6 ning olti bandli kontrakti"
  - "`components/import/import-panel.tsx` — to'rt holatli import oqimi"
  - "`components/import/import-errors.tsx` — guruhlash + 50 qator + `.xlsx`"
  - "`lib/market-queries.ts::activationBlockingOf()` + `api-types.ts::marketIncompleteSchema` — 409 tanasi chegarada"
  - "`wizard-stepper.test.tsx` (5) va `import-errors.test.tsx` (6) — D-11, D-14, D-16 regressiya darvozalari"
affects: [02-17, kassir-moduli, 03-kamera, hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Qadam holati SOF FUNKSIYADA (`wizardStepViews`) — komponentdan tashqarida, ya'ni stepper, qobiq va panel bitta qoidani ko'radi"
    - "Qadamning bajarilganlik shartini QADAMNING O'ZI olib yuradi (`isFilled`) — `switch` + `default` yozilmaydi, yangi qadam qo'shilsa qoidani tanlash MAJBURIY"
    - "Fokusni ko'chirish `useEffect` bilan emas, CALLBACK REF bilan: element montaj bo'lgan lahzada chaqiriladi va `set-state-in-effect` sinfiga tushmaydi"
    - "Birinchi bajarilmagan band RENDER'DAN OLDIN aniqlanadi — sikl ichidagi o'zgaruvchan bayroqni React Compiler rad etadi"
    - "Yashirin (`<details>` ichidagi) maydonda validatsiya xatosi bo'lsa bo'lim MAJBURAN ochiladi — aks holda xato jimgina yo'qoladi"
    - "MA'LUMOTDAN keladigan tarjima kaliti LITERAL xarita orqali (`ERROR_LABEL_KEYS`, `WizardStepLabelKey`) — 02-15 konvensiyasi"
    - "Mexanik grep darvozasi bilan to'qnashadigan atama IZOHDA ham yozilmaydi (02-08 dan meros; bu rejada bir marta kerak bo'ldi)"

key-files:
  created:
    - frontend/src/components/wizard/wizard-steps.ts
    - frontend/src/components/wizard/wizard-stepper.tsx
    - frontend/src/components/wizard/wizard-shell.tsx
    - frontend/src/components/wizard/wizard-stepper.test.tsx
    - frontend/src/components/wizard/market-requisites-form.tsx
    - frontend/src/components/wizard/activation-panel.tsx
    - frontend/src/components/import/import-panel.tsx
    - frontend/src/components/import/import-errors.tsx
    - frontend/src/components/import/import-errors.test.tsx
    - frontend/src/app/[locale]/(app)/markets/new/page.tsx
    - frontend/src/app/[locale]/(app)/markets/setup/page.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/market-queries.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "Sahifa fayllari o'z komponentlari bilan BIR commit'da — har uch commit mustaqil ravishda yashil"
  - "409 `blocking[]` chegarada ochiladi (`activationBlockingOf`), komponentda emas — `importErrorsOf` bilan AYNI naqsh"
  - "Import qator matni `code` TARJIMASIDAN; serverning `message` i faqat uz-Latn va u `.xlsx` ga tushadi"
  - "`fallbackStep()` to'liq bozorda 2 ga emas, FAOLLASHTIRISH qadamiga tushadi"
  - "1-qadam `/markets/setup` da forma emas, XULOSA — rekvizitlarni yangilaydigan endpoint hali yo'q"
  - "Notanish `blocking` kodi alohida qator bo'lib chiqadi — jimgina yo'qolmaydi"
  - "`ActivationPanel` `setup-status` ni O'ZI o'qiydi (ayni `queryKey`, ikkinchi so'rov yo'q)"

patterns-established:
  - "Pattern: qadam ta'rifi o'z bajarilganlik shartini olib yuradi — ro'yxatga qo'shish qoidani tanlashni MAJBURIY qiladi"
  - "Pattern: 'birinchi bajarilmagan element' render'dan oldin hisoblanadi, sikl ichida bayroq bilan emas"
  - "Pattern: yashirin bo'limdagi xato bo'limni majburan ochadi (fokus ko'rinmaydigan maydonga ketmasin)"

requirements-completed: [MARKET-01]

# Metrics
duration: 140min
completed: 2026-08-01
---

# Phase 2 Plan 16: "Yangi bozor" ustasi va Excel import paneli Summary

**SC#1 ning "kod yozilmaydi" da'vosi endi foydalanuvchi yuzasiga ega: ikki marshrut, o'n bitta komponent va o'n bitta yangi test bilan usta holatsiz qurildi — qadam raqami URL'da, bajarilganlik esa faqat `setup-status` javobida yashaydi; faollashtirish tugmasi hech qachon `disabled` bo'lmaydi va chala bozorda fokusni yetishmayotgan bandga ko'chiradi, 300 xatoli import esa uch jumlaga siqiladi. Olti sabotaj o'lchovining har biri AYNAN kutilgan test(lar)ni yiqitdi va eng nozigi — "Hech narsa saqlanmadi" jumlasini faqat KO'P xatoda ko'rsatish — bitta xatoli holat testi bilan ushlandi.**

## Performance

- **Duration:** ~140 min
- **Tasks:** 3/3
- **Fayllar:** 16 (11 yaratildi, 5 o'zgartirildi), **+2808 / −1**
- **Testlar:** vitest 29 → **40** (+11); node 54 (o'zgarmadi) — jami **94**
- **i18n kalitlari:** 384 → **418** (×3 til)
- **Yangi npm paketi:** **0** (`git diff --stat frontend/package.json` bo'sh)

## Accomplishments

- **Olti sabotaj o'lchovi va ularning aniq natijalari:**

  | Sabotaj | Yiqilgan test(lar) | Nazorat holati |
  |---|---|---|
  | Bloklangan qadamdan `aria-describedby` olib tashlandi | AYNAN 1: `bloklangan qadam SABABINI ko'rsatadi va havola EMAS` | qolgan 33 ✅ |
  | Joriy qadamdan `aria-current="step"` olib tashlandi | AYNAN 1: `joriy qadamda aria-current…` | qolgan 33 ✅ |
  | Kamera ko'rsatkichiga «chala» so'zi qo'shildi (D-16) | AYNAN 1: `kamera ko'rsatkichi NEYTRAL…` | qolgan 33 ✅ |
  | Qator chegarasi 50 → 1000 (T-02-122) | AYNAN 2: `300 xatodan… 50 qator` va `qolgan xatolar soni` | qolgan 38 ✅ — ikkalasi bitta chegaradan kelib chiqadi, ya'ni JUFT yiqilishi to'g'ri |
  | `role="alert"` har qatorga qo'yildi | AYNAN 1: `shoshilinch e'lon roli AYNAN bitta` | qolgan 39 ✅ |
  | «Hech narsa saqlanmadi» faqat `total > 5` da ko'rsatildi | AYNAN 1: `…DOIM birinchi — bitta xatoda ham` | qolgan 39 ✅ |

  Oxirgisi eng qimmatli: u D-14 ning eng ehtimolli buzilish shaklini — jumlani "kichik xatolarda ortiqcha" deb shartlash — modellashtiradi va aynan «bitta xatoda ham» degan da'vo uni ushladi. «300 xato» fixture'i bilan yozilgan test bu buzilishni UMUMAN ko'rmasdi.

  Har oltitasidan keyin fayllar `git checkout` bilan tiklandi (`git status` toza).

- **Usta HAQIQATAN holatsiz — va bu o'lchandi.** `grep -rn "localStorage\|sessionStorage" frontend/src/components/wizard` → **0**. Qadam holati sof funksiyada (`wizardStepViews`) hisoblanadi va uning yagona kirishi — `setup-status` javobi hamda URL'dagi raqam. Natijada sahifa yangilash, boshqa qurilmadan davom ettirish va uzilishdan tiklanish qo'shimcha kodsiz ishlaydi.

- **02-03 ning qarzi yopildi.** `market-picker.tsx` allaqachon `/markets/setup?step=N` ga yo'naltirardi va uning `try/catch` fail-safe'i `?step=1` beradi. Ikkala manzil ham endi HAQIQIY: `?step=1` bo'sh ekran emas, rekvizitlar xulosasi va oldinga havola beradi (deviatsiya #8).

- **4-qadam server qoidasidan ajralmadi (T-02-127a).** `ls frontend/src/components/wizard | grep -i tariff` → **bo'sh**; `grep -rniE "new Date\(\)|addDays|tomorrow" frontend/src/components/wizard` → **0**. Sana chegarasi faqat `min_valid_from` dan keladi, ya'ni qoralama bozorda boshlang'ich narxni o'tmishdagi sanaga yozish yo'li ochiq va faollashtirish paneli havolasi cheksiz siklga olib bormaydi.

- **D-16 ikki joyda ham qulflandi.** `grep -rniE "AlertTriangle|AlertCircle|bg-warning|bg-danger|role=\"alert\"" activation-panel.tsx` → **0**; stepperda kamera ko'rsatkichi regressiya testi bilan himoyalangan. Kamera bo'limi qadam massiviga umuman kirmaydi, ya'ni u progress sanog'iga ham, `blockedBy` grafiga ham tushmaydi — bozor kamerasiz ham "to'liq" ko'rinadi.

- **Faollashtirish tugmasida `disabled` atributi YO'Q** (faqat `aria-disabled`), ya'ni u fokuslanadi va skrinrider uni o'qiydi; chala bozorda bosilganda so'rov YUBORILMAYDI va fokus birinchi bajarilmagan bandga ko'chadi.

## Task Commits

1. **Task 1: Usta qobig'i, qadam relsi va yagona qadam manbai** — `c50862a` (feat)
2. **Task 2: Rekvizitlar formasi, faollashtirish paneli va 1-qadam marshruti** — `4a58d8a` (feat)
3. **Task 3: Excel import paneli, xato ro'yxati va 2–7-qadam marshruti** — `7a7b47b` (feat)

## Files Created/Modified

**Yaratildi (11)**

| Fayl | Qator | Mazmuni |
|---|---|---|
| `markets/setup/page.tsx` | 375 | Suspense + nuqs; yetti qadamning kontenti mavjud komponentlardan |
| `wizard/activation-panel.tsx` | 423 | §6.6 olti bandi; 409 ayni ro'yxatga tushadi |
| `wizard/market-requisites-form.tsx` | 397 | ikki bo'lim; `<details>` xatoda majburan ochiladi |
| `wizard/wizard-steps.ts` | 258 | yetti qadam + `CAMERA_PLACEHOLDER` + holat hisoblagichi |
| `import/import-panel.tsx` | 233 | to'rt holat; progress ko'rsatkichi ATAYIN yo'q |
| `wizard/wizard-stepper.tsx` | 227 | to'rt holat × uch kanal |
| `import/import-errors.tsx` | 218 | yetti qoidali kontrakt |
| `wizard/wizard-stepper.test.tsx` | 206 | 5 vitest (D-11 va D-16 darvozalari) |
| `import/import-errors.test.tsx` | 178 | 6 vitest (D-14 darvozasi) |
| `wizard/wizard-shell.tsx` | 88 | rels + kontent; `marketId === null` da so'rov yo'q |
| `markets/new/page.tsx` | 59 | ikki huquq darvozasi; `?step` yo'q |

**O'zgartirildi (5)**

- `lib/api-types.ts` — `marketIncompleteSchema` (+18 qator)
- `lib/market-queries.ts` — `activationBlockingOf()` (+27/−1)
- `messages/{uz-Latn,ru}.json` — 34 yangi kalit; `uz-Cyrl.json` faqat `i18n:gen` bilan

## Decisions Made

- **Sahifa fayllari o'z komponentlari bilan bir commit'da.** Reja ikkala sahifani Task 1 ga qo'yadi, lekin ular Task 2 va Task 3 dagi komponentlarni import qiladi — ya'ni Task 1 commit'i typecheck'da QIZIL bo'lardi. Rejaning yakuniy holati o'zgarmadi (ikkala fayl ham `files_modified` da). Bu 02-14 deviatsiya #1 bilan aynan bir xil sinf.
- **409 tanasi CHEGARADA ochiladi.** `activationBlockingOf(error)` — `importErrorsOf` bilan aynan bir xil naqsh. Muqobil variant komponentga `ApiError` ni ham, zod sxemasini ham olib kirardi va 02-13 ning "komponent HTTP qatlamiga tegmaydi" qoidasini buzardi.
- **Import qator matni `code` tarjimasidan.** Serverning `message` maydoni FAQAT uz-Latn (`ImportIssue` docstringi buni literal aytadi). Uni ekranga chiqarish rus tilidagi adminni tarjimasiz qoldirardi va CLAUDE.md ning "3 til majburiy" cheklovini buzardi. Aniq qiymat ("qaysi zona") yo'qolmaydi — u `.xlsx` hisobotiga tushadi va bu §8.5 ning 4-qoidasining maqsadi.
- **`ActivationPanel` `setup-status` ni o'zi o'qiydi.** Reja qobiq natijani panelga UZATISHINI aytadi. Amalda panelga 409 dan keyin ro'yxatni ALMASHTIRISH kerak — bu uning o'z holati, va uni propga bog'lash haqiqat manbaini ikkiga bo'lardi. `queryKey` bir xil, ya'ni ikkinchi tarmoq so'rovi ketmaydi (02-14 dagi "panel va ro'yxat bir xil hookdan o'qiydi" konvensiyasi).
- **`TariffDialog` ga TRANZITIV kirish.** Qabul mezoni 4-qadamdan tarif dialogiga importni kutadi. `TariffList` uni ALLAQACHON import qiladi (`tariff-list.tsx:15`) va create/edit dialoglarini o'zi boshqaradi hamda `minValidFrom` ni javobdan uzatadi. Sahifadan uni IKKINCHI marta render qilish ikkita dialog nusxasini berardi. Mezonning maqsadi — "usta uchun alohida forma yozilmasin" — to'liq bajarildi (`wizard/` ostida tarif fayli **yo'q**).
- **`<details>` xatoda majburan ochiladi.** Yashirin maydondagi xato — jimgina yo'qolgan xato: react-hook-form fokusni ko'rinmaydigan `<input>` ga ko'chirardi va foydalanuvchi "nega saqlanmayapti?" deb qolardi. Shart RENDER paytida hisoblanadi.
- **Bank MFO ning besh raqamli qoidasi — QULAYLIK, darvoza emas.** Server bu maydonni ATAYIN formatlamaydi (A1 tasdiqlanmagan). Sabab va "haqiqiy rekvizit rad etilsa nima qilish kerak" ko'rsatmasi kodda yozildi: tuzatish klientdagi qoidani OLIB TASHLASH bo'ladi, serverga cheklov qo'shish EMAS.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ikkala sahifa fayli Task 1 da qurilsa, commit typecheck'da qizil bo'lardi**

- **Found during:** Task 1
- **Issue:** Reja `markets/new/page.tsx` va `markets/setup/page.tsx` ni Task 1 ga qo'yadi. Birinchisi Task 2 dagi `market-requisites-form` ni, ikkinchisi Task 2 dagi `activation-panel` va Task 3 dagi `import-panel` ni import qiladi. Task 1 ning `<verify>` bandi esa `typecheck` ni talab qiladi — ya'ni commit o'z-o'zicha bajarilmas edi.
- **Fix:** Sahifalar o'z bog'liqliklari bilan bir commit'ga ko'chirildi: `markets/new` → Task 2, `markets/setup` → Task 3. Qamrov kengaymadi (ikkalasi ham `files_modified` da) va rejaning yakuniy holati o'zgarmadi.
- **Committed in:** `4a58d8a`, `7a7b47b`

**2. [Rule 3 - Blocking] §6.6 ning 5-bandi `market-queries.ts` ga tegmasdan bajarilmas edi**

- **Found during:** Task 2
- **Issue:** "Server 409 qaytarsa javob tanasidagi `blocking[]` shu ro'yxatni almashtiradi" — massiv `ApiError.body` da yashaydi va uni ochish uchun zod sxemasi kerak. Ikkala modul ham (`api-types.ts`, `market-queries.ts`) rejaning `files_modified` ro'yxatida YO'Q. Muqobil variant — komponentda `ApiError` va sxemani ochish — 02-13 ning "komponent HTTP qatlamiga tegmaydi" qoidasini buzardi.
- **Fix:** `marketIncompleteSchema` (`api-types.ts`) + `activationBlockingOf()` (`market-queries.ts`) — mavjud `importErrorResponseSchema` / `importErrorsOf` juftining AYNAN nusxasi. Ikkalasi ham QO'SHIMCHA (additive): mavjud eksportlarning birortasi o'zgarmadi.
- **Files modified:** `frontend/src/lib/api-types.ts`, `frontend/src/lib/market-queries.ts`
- **Verification:** `market-queries.test.tsx` ning 11 testi va `error-codes.test.mjs` o'zgarmasdan yashil qoldi
- **Committed in:** `4a58d8a`

**3. [Rule 2 - Missing Critical] Reja `frontend/messages/*` ni sanamagan, lekin ekranlar 34 kalitsiz qurilmasdi**

- **Found during:** Task 1, 2 va 3
- **Issue:** `wizard` va `import` namespace'lari 02-13 dan mavjud, lekin ularda stepper ARIA yorliqlari, bloklanish sababi, rekvizit maydonlarining nomlari va validatsiya matnlari, to'liqlik ro'yxatining bandlari, sanoq formatlari hamda import qator formati YO'Q edi. `src/global.ts` `uz-Latn.json` ni `AppConfig.Messages` ga bog'laydi, ya'ni mavjud bo'lmagan kalit — **kompilyatsiya xatosi**: ekranni "kalitsiz" yozish MUMKIN emas, yagona muqobil — qattiq kodlangan o'zbekcha matn, ya'ni CLAUDE.md ning "3 til majburiy" cheklovini buzish.
- **Fix:** 34 kalit qo'shildi, FAQAT shu reja egalik qiladigan namespace'larga: `wizard` (+30), `import` (+4). `common`, `errors` va boshqa ekranlarning namespace'lariga TEGILMADI. Ro'yxat bandlarining yorliqlari uchun yangi kalit YOZILMADI — mavjud `wizard.step.*` qayta ishlatildi (panel foydalanuvchini o'sha qadamga yuboradi va u yerda boshqa nomni ko'rmasligi kerak).
- **Verification:** `i18n:check` — **418 kalit × 3 til**, kalit va ICU parity to'liq; `uz-Cyrl.json` faqat `i18n:gen` bilan
- **Committed in:** `c50862a`, `4a58d8a`, `7a7b47b`

**4. [Rule 1 - Bug] Grep darvozasi O'Z izohiga qarshi turdi**

- **Found during:** Task 2 yakuniy tekshiruvi
- **Issue:** `wizard-shell.tsx` izohida "klientda … xotira YO'Q" degan tushuntirish taqiqlangan brauzer-xotira API'larining nomlarini LITERAL o'z ichiga olardi; qabul mezoni esa aynan shu atamalarni `components/wizard` bo'ylab grep qilib **0** talab qiladi.
- **Fix:** 02-08 da o'rnatilib 02-13/02-14/02-15 da takrorlangan konvensiya: TAQIQ va uning TO'LIQ sababi saqlandi, atamalarning O'ZI literal yozilmadi, ustiga "bu qoida grep bilan qulflangan" ogohlantirishi qo'shildi.
- **Verification:** oltala wizard fayli uchun grep **0**
- **Committed in:** `4a58d8a`

**5. [Rule 1 - Bug] React Compiler qoidasi "birinchi bajarilmagan band" bayrog'ini rad etdi**

- **Found during:** Task 2
- **Issue:** Fokus ko'chiriladigan bandni topishning tabiiy shakli — sikl ichida "ko'rildi" bayrog'ini o'zgartirish. `react-hooks/immutability` buni xato deb belgiladi va u HAQ: bayroq render tugagandan keyin ham o'zgarib, keyingi renderda BOSHQA bandga fokus berardi.
- **Fix:** `firstUnmetKey` render'dan OLDIN, sof derivatsiya bilan hisoblanadi (`unmetRows[0]?.labelKey ?? extras[0]?.code ?? null`) va sikl ichida faqat solishtirish qoladi.
- **Files modified:** `activation-panel.tsx`
- **Committed in:** `4a58d8a`

**6. [Rule 2 - Missing Critical] Import qatori serverning uz-Latn matnini ekranga chiqarardi**

- **Found during:** Task 3
- **Issue:** Reja qator formatini `{row}-qator: {message}` deb belgilaydi va `message` — javobdagi maydonning nomi. Manba o'qildi: `ImportIssue` docstringi bu maydonni AYNAN "foydalanuvchi uchun, **uz-Latn**" deb ta'riflaydi, ya'ni u server tomonda bitta tilda yaratiladi. Uni to'g'ridan-to'g'ri render qilish rus tilidagi admin uchun butun xato ro'yxatini tarjimasiz qoldirardi.
- **Fix:** Ekrandagi matn `code` ning TARJIMASIDAN quriladi (`import.errors.*`, 02-13 da backend bilan 1:1 qulflangan); format `import.rowError` kaliti bilan uchala tilda saqlanadi va uz-Latn'da AYNAN `{row}-qator: {message}` bo'lib chiqadi. Serverning aniq matni (`'Sabzavot' zonasi topilmadi`) YO'QOLMAYDI — u `downloadErrorReport(errors)` orqali `.xlsx` ga tushadi, ya'ni §8.5 ning 4-qoidasi bajariladi.
- **Verification:** `qator formati AYNAN {row}-qator: {matn}` testi
- **Committed in:** `7a7b47b`

**7. [Rule 2 - Missing Critical] Notanish `blocking` kodi ro'yxatdan JIMGINA tushib qolardi**

- **Found during:** Task 2
- **Issue:** Panel bandlari server kodlariga qo'lda bog'langan. 3-fazada yangi to'siq qo'shilsa va u xaritaga tushmasa, foydalanuvchi "hammasi bajarilgan" ro'yxatini ko'rib turib, tugmadan hech qanday javob ololmasdi — ya'ni FAIL-OPEN, va aynan §6.6 to'sishga urinayotgan tajriba.
- **Fix:** Xaritada yo'q kodlar alohida qatorlar bo'lib chiqadi (`extras`) va har biri o'z `blocking[].step` iga havola qiladi. Ro'yxat hech qachon serverdan kambag'alroq bo'lmaydi.
- **Committed in:** `4a58d8a`

**8. [Rule 1 - Bug] `/markets/setup?step=1` boshi berk ko'cha bo'lardi**

- **Found during:** Task 3
- **Issue:** `fetchFirstIncompleteStep` (02-13) `blocking[]` bo'sh bo'lganda va xato holatida **1** qaytaradi, `market-picker.tsx` esa uni to'g'ridan-to'g'ri `?step=1` ga uzatadi (02-03 ning testi buni aniq talab qiladi). Reja esa bu marshrutni "2–7-qadamlar" deb belgilaydi — ya'ni 1-qadam uchun kontent umuman yo'q edi. Rekvizitlar formasini u yerda ko'rsatish esa YOLG'ON va'da bo'lardi: ularni yangilaydigan endpoint 02-11 da ATAYIN ochilmagan (`rename_market()` HTTP iste'molchisisiz).
- **Fix:** 1-qadam bu marshrutda XULOSA bo'lib chiziladi — bozor nomi, rekvizitlar yaratilishda saqlangani haqidagi izoh va 2-qadamga havola. Hech qanday "Saqlash" tugmasi yo'q, ya'ni bajarilmaydigan va'da ham yo'q.
- **Committed in:** `7a7b47b`

**9. [Rule 1 - Bug] To'liq qoralama bozor faollashtirish tugmasidan UZOQQA tushardi**

- **Found during:** Task 3
- **Issue:** Reja yaroqsiz `?step` uchun "`blocking[0].step` ga (yoki **2** ga)" tushishni belgilaydi. Lekin `blocking` BO'SH bo'lgan holat — bu "bozor tayyor, faollashtirish qoldi" degani. 2-qadamga (Zonalar) tushirish foydalanuvchini tayyor bozor bilan zona ro'yxatiga olib borardi va "endi nima?" savolini javobsiz qoldirardi.
- **Fix:** `fallbackStep()` uch tarmoqli: `blocking` bor → birinchi to'siqning qadami; javob kelmagan → statik **2**; javob kelgan va bo'sh → **7** (faollashtirish). Sabab funksiya docstringida.
- **Committed in:** `7a7b47b`

**10. [Rule 2 - Missing Critical] `<details>` ichidagi validatsiya xatosi ko'rinmasdan qolardi**

- **Found during:** Task 2
- **Issue:** STIR va MFO maydonlari yig'ilgan `<details>` ichida. Noto'g'ri STIR kiritilib bo'lim yopilsa, react-hook-form fokusni KO'RINMAYDIGAN `<input>` ga ko'chirardi: forma yuborilmaydi, xato esa ekranda yo'q — foydalanuvchi "nega saqlanmayapti?" deb qolardi.
- **Fix:** `hasOfficialError` render paytida hisoblanadi va `<details open>` shundan ham to'ladi. Effekt ishlatilmadi (kaskad render).
- **Committed in:** `4a58d8a`

**11. [Rule 3 - Blocking] Vitest `@/i18n/navigation` ni yecha olmaydi**

- **Found during:** Task 1
- **Issue:** `next-intl` ning `createNavigation` i `next/navigation` ni import qiladi va vitest ESM yechimida u topilmaydi (`Cannot find module .../next/navigation`) — butun test fayli montaj bo'lmasdan yiqildi.
- **Fix:** 01-12 dagi `market-picker.test.tsx` naqshi: `vi.mock("@/i18n/navigation")` va `Link` oddiy `<a>` ga aylantiriladi. Qamrov TORAYMAYDI — bu faylning da'volari relsning strukturasi haqida (havolami yoki emas, `href` qaysi qadamga ketadi, ARIA nima deydi); locale prefiksini qo'yish `next-intl` ning o'z zimmasida.
- **Committed in:** `c50862a`

---

**Total deviations:** 11 auto-fixed (4 bug, 4 missing-critical, 3 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Yangi npm paketi QO'SHILMADI, backend'ga UMUMAN tegilmadi (`alembic_version` `0010` bo'lib qoladi), yangi endpoint yo'q. #1 va #11 rejaning ichki ketma-ketlik/muhit ziddiyatlari; #4, #5, #10 darvozalar (grep, lint, dizayn) ushlagan haqiqiy defektlar; #2, #3, #6 reja ko'rmagan uchta majburiy yo'lni ochadi; #7, #8, #9 esa uchta BOSHI BERK KO'CHANI yopadi va uchalasi ham §6.6 ning "yo'l ko'rsatkichi" tamoyilining bevosita natijasi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `grep -rn "localStorage\|sessionStorage" components/wizard` | ✅ **0** (oltala fayl) |
| `grep -rniE "new Date\(\)\|addDays\|tomorrow" components/wizard` | ✅ **0** |
| `ls components/wizard \| grep -i tariff` | ✅ **bo'sh** |
| `grep -rniE "AlertTriangle\|AlertCircle\|bg-warning\|bg-danger\|role=\"alert\"" activation-panel.tsx` | ✅ **0** |
| `grep -rn "role=\"alert\"" wizard-stepper.tsx` | ✅ **0** |
| `grep -rniE "bg-(warning\|danger)" wizard-stepper.tsx` | ✅ **0** |
| `grep -rn "apiFetch" components/import` | ✅ **0** (test fayli bilan birga) |
| Faollashtirish tugmasida `disabled` atributi | ✅ **YO'Q** (faqat `aria-disabled`) |
| `can_activate === false` da mutatsiya chaqiruvi | ✅ erta qaytish (`if (!canActivate) { … return; }`) |
| Ro'yxat `can_activate === true` da ham render qilinadi | ✅ shartsiz `<ul>` |
| `tariff_missing_for_category` → 4-qadam havolasi | ✅ |
| `wizard-steps.ts` eksportlari | ✅ 7 qadam; kamera massivda **YO'Q**, alohida konstanta |
| Progress qatori | ✅ `role="status"`, stepper ustida |
| Stepper to'rt holat | ✅ `completed` / `current` / `blocked` / `pending` |
| Bloklangan qadam | ✅ `aria-disabled="true"` + `aria-describedby` → mavjud element |
| `markets/setup` — `Suspense` + `nuqs` | ✅ `parseAsInteger.withDefault(2)` |
| `import-panel` fayl maydoni | ✅ `accept=".xlsx"`, `sr-only`, `<label htmlFor>` bilan bog'langan |
| Progress bar komponenti import panelda | ✅ **YO'Q** (yagona grep uchrashi — uning YO'QLIGINI e'lon qiluvchi izoh) |
| 300 xatoda DOM'dagi `<li>` (`<ol>` ichida) | ✅ **50** |
| `role="alert"` elementlari soni | ✅ **1** (`<h3>`) |
| Qator formati | ✅ `2-qator: Zona topilmadi` |
| `skipped > 0` tushuntirishi | ✅ sanoq bilan BIR joyda |
| Sabotaj o'lchovlari (6 ta) | ✅ har birida AYNAN kutilgan test(lar) yiqildi |
| Sabotajdan keyin tiklash | ✅ `git status` toza |
| Commit'larda fayl o'chirilishi | ✅ **0** (`git diff --diff-filter=D` bo'sh) |
| `git diff --stat frontend/package.json` | ✅ **bo'sh** |

## Issues Encountered

- **`getByRole("list")` ekranda IKKI ro'yxat bo'lganda noaniqlik bilan yiqiladi.** Import xato ekranida guruhlar `<ul>`, qatorlar `<ol>` — ikkalasi ham `role="list"`. Test tegi bo'yicha ajratadigan yordamchiga (`listByTag`) o'tkazildi va bu ajratmaning o'zi ham kontrakt: §8.5 ning 7-qoidasi qator ro'yxatini AYNAN `<ol>` qilib belgilaydi.
- **`toHaveAttribute("aria-disabled", null)` — noto'g'ri shakl.** Atributning YO'QLIGI `not.toHaveAttribute(...)` bilan tekshiriladi; birinchi shakl `null` ni kutilgan QIYMAT deb talqin qiladi va har doim yiqiladi.
- **jsdom `scrollIntoView` ni umuman ta'riflamaydi.** Mobil relsdagi markazlashtirish `typeof node.scrollIntoView === "function"` tekshiruvi bilan o'raldi — usiz butun stepper testda `TypeError` bilan qulardi.
- **`ReturnType<typeof useTranslations>` un-namespaced tarjimonni BERMAYDI.** Ro'yxat qurish tashqi funksiyadan komponent ichiga ko'chirildi — bu qo'shimcha foyda ham berdi: kalitlar endi to'liq tip xavfsizligi ostida.
- **`frontend/node_modules` worktree'da bo'sh edi** — `npm ci` bilan `package-lock.json` dan tiklandi (yangi paket o'rnatilmadi).

## Known Stubs

Yo'q. Ikkala marshrutning ham har bir tugmasi haqiqiy endpointga ulangan; birorta komponent `TODO`, qattiq yozilgan bo'sh massiv yoki "keyinroq" placeholder'i qoldirmaydi. Kamera bo'limi stub EMAS — u D-16 bo'yicha ATAYIN qadam emas va uning neytralligi test bilan qulflangan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| Rekvizitlarni TAHRIRLASH (`PATCH /markets/{id}`) | belgilanmagan | Server metodi (`rename_market()`) tayyor, HTTP marshruti ATAYIN ochilmagan (02-11 qarori). `/markets/setup?step=1` forma emas, XULOSA ko'rsatadi — bajarilmaydigan va'da berilmaydi |
| Ustaga NAVIGATSIYA havolasi (`/markets/new` yon panelda yo'q) | 02-17 yoki keyingi to'lqin | Marshrut mavjud va ishlaydi; unga bugun faqat to'g'ridan-to'g'ri URL bilan yoki bozor tanlash ekrani orqali (qoralama uchun) kiriladi. `app-shell.tsx` bu rejaning fayl chegarasidan tashqarida va unga tegish uchta parallel reja bilan to'qnashuv nuqtasi bo'lardi |
| Platforma admini BIRORTA bozorsiz ustaga kira olmaydi | belgilanmagan | `(app)/layout.tsx` `marketId === null` da `/select-market` ga yuboradi, bozor tanlash ekrani esa bo'sh ro'yxatda faqat "chiqish" beradi. Bu 1-fazadan beri shunday va bu reja `layout.tsx` ga tegmadi (uning `files_modified` da yo'q) |
| `?step` yaroqsiz bo'lganda URL TUZATILMAYDI | — | Kontent to'g'ri qadamdan chiziladi (`fallbackStep`), lekin manzil qatori o'zgarmaydi. Ataylab: `?step` — faqat ko'rinish va uni qayta yozish effekt ichida `setState` talab qilardi |
| `market-requisites-form` va `activation-panel` uchun komponent testi yo'q | 02-17 (tekshiruv to'lqini) | Reja aynan ikkita test faylini talab qildi va ikkalasi ham yozildi. Bu ikki komponent typecheck + lint + build bilan qoplangan; ularning kontrakti esa grep o'lchovlari bilan (yuqoridagi jadval) |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA yangi xavfsizlik yuzasi paydo bo'lmadi: yangi endpoint, yangi auth yo'li yoki sxema o'zgarishi YO'Q. Fayl kirishi mavjud `useImportMutation` orqali va u 02-12 ning server darvozalariga tushadi.

| Threat ID | Holat |
|-----------|-------|
| T-02-120 | mitigate — `?step` FAQAT ko'rinish: u hech qanday so'rov parametriga aylanmaydi va `market_activate()` klientdan parametr olmaydi. Klientdagi tugma holati faqat qulaylik; darvoza `_blocking()` da |
| T-02-121 | avoid — `components/import` da parse ham, validatsiya ham YO'Q (fayl `FormData` bo'lib o'zgarmagan holda ketadi). `accept=".xlsx"` — brauzer dialogining filtri, tekshiruv emas |
| T-02-122 | **mitigate** — `MAX_VISIBLE_ROWS = 50`; qolgani `.xlsx`. **Sabotaj bilan o'lchandi**: chegara 1000 ga ko'tarilganda AYNAN 2 test qizardi |
| T-02-123 | **mitigate** — "Hech narsa saqlanmadi" BIRINCHI va SHARTSIZ; `skipped > 0` tushuntirishi sanoq bilan bir joyda. **Sabotaj bilan o'lchandi**: jumla shartga o'ralganda bitta-xato testi qizardi |
| T-02-124 | mitigate — qoralama `Qoralama` badge'i bilan bozor tanlash ekranida (02-03); usta oxirida `activate` serverdagi tekshiruvdan o'tadi va 409 ro'yxatga aylanadi |
| T-02-125 | mitigate — beshala rekvizit maydonida `autoComplete="off"`; ular ixtiyoriy va `<details>` ichida |
| T-02-126 | mitigate — `market_manage` **va** `is_platform_admin` klientda; server tomonda `require_platform_admin` + `require_permission` (02-11) va `test_market_admin_cannot_create_market`. Klientdagi tekshiruv serverdagining o'rnini BOSMAYDI — sabab kodda yozilgan |
| T-02-127 | **mitigate** — kamera ko'rsatkichi regressiya testi bilan: matn, rol va fon sinfi UCHALASI alohida tekshiriladi. **Sabotaj bilan o'lchandi** |
| T-02-127a | **mitigate** — 4-qadam 02-15 dagi dialogni TRANZITIV (`TariffList` orqali) ishlatadi; `wizard/` ostida tarif fayli **yo'q** va sana hisobi grep bilan **0**. Faollashtirish panelidagi havola aynan shu sababdan ishlaydigan yo'lga olib boradi |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run i18n:check` | ✅ **418 kalit × 3 til**, drift yo'q |
| 2 | `npm --prefix frontend run typecheck` | ✅ exit 0 |
| 3 | `npm --prefix frontend run lint` | ✅ exit 0 |
| 4 | `npm --prefix frontend run test:unit` | ✅ **54** node test, 0 fail |
| 5 | `npm --prefix frontend run test:component` | ✅ **40** vitest, 0 fail |
| 6 | `npm --prefix frontend run build` | ✅ exit 0; `/markets/new` va `/markets/setup` uchala tilda SSG |
| 7 | `git diff --stat frontend/package.json` | ✅ bo'sh |

## User Setup Required

Yo'q — tashqi xizmat sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja backend'ga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi) va yangi npm paketi o'rnatmaydi.

## REQUIREMENTS.md holati

Frontmatter `requirements: [MARKET-01, MARKET-02, MARKET-04]` deb yozgan.

- **MARKET-01** — shu rejada YAKUNLANDI: server yarmi 02-11 da, foydalanuvchi yuzasi shu yerda. SC#1 ning "kod yozilmaydi" da'vosi endi ekran bilan isbotlanadi.
- **MARKET-02** va **MARKET-04** — ular 02-14 va 02-15 da ALLAQACHON yopilgan (o'sha SUMMARY'larning `requirements-completed` ida). Bu reja ularning ekranlarini faqat QAYTA ISHLATADI, ya'ni ularni ikkinchi marta belgilash traceability jadvaliga qo'shimcha ma'lumot bermaydi.

Bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md`, `STATE.md`, `ROADMAP.md` — orkestrator egalik qiladigan umumiy artefaktlar; ularga TEGILMADI.

## Next Phase Readiness

- **Usta uchidan-uchiga ishlaydi:** `/markets/new` → `POST /markets` → `select-market` → `?step=2` → … → 7-qadamdagi faollashtirish → `/dashboard`. Har qadamning kontenti 02-14/02-15 komponentlaridan, ya'ni reestr ekranlaridagi har qanday tuzatish ustada ham AVTOMATIK ko'rinadi.
- **02-17 (tekshiruv to'lqini) uchun:** `wizard-steps.ts` sof funksiya va u brauzersiz sinaladi — `wizardStepViews()` / `fallbackStep()` uchun unit test yozish eng arzon qamrov kengaytmasi. `market-requisites-form` va `activation-panel` ning xulq testlari ham shu yerda yopiladi.
- **3–5 fazalar (kamera) uchun:** kamera bo'limining ilgagi `CAMERA_PLACEHOLDER` da. Kamera QADAMGA aylanганда u `WIZARD_STEPS` ga o'z `isFilled` i bilan qo'shiladi va stepper, progress hamda faollashtirish paneli uni AVTOMATIK oladi — uchala joyda alohida tahrir kerak emas. `setup-status` javobida `cameras` maydoni allaqachon bor.
- **Yangi bloklovchi shart qo'shadigan HAR KIM uchun:** `activation-panel.tsx` dagi `rows` massiviga kodni bog'lang. Bog'lamasangiz ham ro'yxat FAIL-VISIBLE qoladi (notanish kod alohida qator bo'lib chiqadi), lekin u umumiy matn bilan ko'rinadi. `wizard.blocking.<code>` tarjimasi esa `error-codes.test.mjs` bilan majburiy.
- **⚠ Konflikt e'tibori:** bu reja `frontend/messages/{uz-Latn,ru}.json` ga 34 kalit qo'shdi — FAQAT `wizard` va `import` namespace'lariga. `api-types.ts` va `market-queries.ts` ga esa faqat QO'SHIMCHA (additive) o'zgarish kirdi: `marketIncompleteSchema` va `activationBlockingOf()`. Mavjud eksportlarning birortasi o'zgarmadi.

## Self-Check: PASSED

- Da'vo qilingan 11 yangi fayl diskda mavjud (`ls` bilan tekshirildi: oltita `wizard/`, uchta `import/`, ikkita `page.tsx`)
- Da'vo qilingan 5 o'zgartirilgan fayl `git diff --stat b5b8f0d..HEAD` da ko'rinadi (16 fayl, +2808/−1)
- Uchala vazifa commit'i git tarixida mavjud: `c50862a`, `4a58d8a`, `7a7b47b`
- Birorta commit'da fayl o'chirilishi YO'Q (`git diff --diff-filter=D --name-only b5b8f0d HEAD` bo'sh)
- Olti sabotajdan keyin ishchi daraxt toza (`git status --short` bo'sh)
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
