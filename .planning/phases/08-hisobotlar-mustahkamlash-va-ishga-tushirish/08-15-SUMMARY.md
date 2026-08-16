---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 15
subsystem: ui
tags: [react, next-intl, tanstack-query, accessibility, tdd, sabotage, reuse]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-03: useAnomalyArchive / useAccuracyReport({from,to}), anomalyArchiveSchema, reports.* katalogi uchala tilda"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-09: useReportPeriod() (from/to/isEmpty) va ExportButton"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-13: blok naqshi — davr hookdan, mazmun atributi ro'yxatning O'ZIDA, «ko'rinadigan matn = textContent minus sr-only»"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "EvidenceLink (/billing?day= havolasi, kadrsiz) va CaseStatusBadge (yopiq 4 a'zo + zaxira yorliq)"
  - phase: 05-bandlik-va-aniqlik
    provides: "ConfusionMatrix — foiz SERVERDAN, davr javobdan, measured/min_sample serverniki"
provides:
  - "components/reports/anomaly-archive.tsx — bitta jadval, ikki sinf, IKKI alohida sanoq"
  - "components/reports/accuracy-block.tsx — ConfusionMatrix ustidagi o'ram + AI-02 jumlasi + eksport tugmasi"
  - "G-40(a)(b) darvozasi va uning (c)(d)(e)(f)(g) bandlari"
  - "reports.* ga 6 yangi kalit uchala tilda (arxiv ustunlari + bo'sh holat 3)"
  - "components/reports/** da 6 mahsulot fayli — G-38(a) ning ≥6 chegarasi endi bajarilgan"
affects:
  - 08-17

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ikki sinfni bitta songa siqishning YO'QLIGI IKKI QATLAM bilan o'lchanadi: sof sonli tugunlarning TO'PLAM tengligi (shakldan mustaqil) + yig'indi qiymatining butun matnda yo'qligi (joylashuvdan mustaqil)"
    - "«Yakka nol yo'q» da'vosi HAR MATN TUGUNIDA alohida izlanadi — birlashtirilgan satrda qo'shni jumlaning nuqtasi lookbehind'ni o'chiradi"
    - "Qo'shni katalogning PREZENTATSION komponentini qayta ishlatish (EvidenceLink, CaseStatusBadge) — matn kalitini ko'chirishdan farqli o'laroq, IN-05 ni buzmaydi"
    - "Sabotaj kutilgan darvozani emas, qo'shnisini qizartirsa — o'lchov SHAKLI noto'g'ri; sabotaj shakli almashtirilib qayta o'lchanadi"

key-files:
  created:
    - frontend/src/components/reports/anomaly-archive.tsx
    - frontend/src/components/reports/anomaly-archive.test.tsx
    - frontend/src/components/reports/accuracy-block.tsx
    - frontend/src/components/reports/accuracy-block.test.tsx
  modified:
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "08-15: `min_sample` maydoni AYNAN BIR MARTA o'qiladi va bu rejaning `grep -c → 0` mezonidan ONGLI chetlanish: G-43(d) `{min}` platsholderini UCHALA locale'da QULFLAGAN, §9.3 esa chegarani SERVERNIKI deb talab qiladi — mezon o'z maqsadidan (klientda ikkinchi chegara yo'q) OSHIB ketgan. O'rniga aniqroq darvoza yozildi: taqqoslash operatori 0, `wilson.ts` konstantasi 0"
  - "08-15: dalil `EvidenceLink` orqali HAVOLA sifatida chiziladi (rejaning «havola YOKI identifikator» tanlovidan havola) — chunki 08-17 ning G-38(a) darvozasi `components/reports/**` da `href={` ni 0 ga qulflaydi, EvidenceLink esa qo'shni katalogda yashaydi"
  - "08-15: dalilsiz katak `sr-only` nom OLMAYDI va bu 08-13 ning teskarisi — u yerda bo'shlik MA'LUMOTNING yo'qligi edi, bu yerda AMALNING yo'qligi; yo'q havolani skrinriderda e'lon qilish uni qidirishga yuborardi (07 D-03 ning 4-bandi)"
  - "08-15: `AccuracyBlock` prop OLMAYDI (`useReportPeriod()`) — UI-SPEC §9.2 diagrammasi `from`/`to` propini ko'rsatadi, lekin `isEmpty` ham kerak va u faqat hookda; ikkalasini olish uchinchi haqiqat manbaini tug'dirardi (08-13 naqshi)"
  - "08-15: `measured === false` da ConfusionMatrix ham chiziladi, hisobot yuzasining nomlangan sababi esa USTIGA qo'shiladi — `/occupancy` matni «umuman o'lchanmadi», bu yerda esa «BU DAVRDA yetmadi» (IN-05)"

patterns-established:
  - "Ikki qatlamli «yig'indi yo'q» darvozasi: to'plam tengligi + qiymat izi — ikkalasi bir-birining ko'r nuqtasini yopadi"
  - "Sabotaj UCH shaklda o'tkaziladi (yalang, o'ralgan, interpolyatsiyalangan) va uchinchisi odatda assertning haqiqiy chegarasini ochadi"

requirements-completed: [RECON-04, RECON-05]

# Metrics
duration: 60min
completed: 2026-08-16
---

# Phase 8 Plan 15: Nomuvofiqlik arxivi va aniqlik bloki Summary

**Arxivda ikki sinf bitta jadvalda ko'rinadi, lekin ikki sanoq HECH QAYERDA qo'shilmaydi va buni ikki mustaqil qatlam o'lchaydi; aniqlik bloki esa mavjud matritsani QAYTA ISHLATADI va o'lchanmagan namunada ham, yiqilgan so'rovda ham foiz belgisi DOM'da nol marta — WR-05 shu bilan yopildi.**

## Performance

- **Duration:** ~60 min
- **Tasks:** 3/3
- **Commits:** 5 (2 × RED + 2 × GREEN + 1 × sabotaj/mustahkamlash)
- **Files:** 7 (4 yangi, 3 matn katalogi)

## Accomplishments

- **«Ikki sanoq qo'shilmaydi» qoidasi ikki qatlam bilan qulflandi.** 1-qatlam — DOM'dagi **sof sonli matn tugunlari** to'plami aynan `{2, 3}` ga teng (shakldan mustaqil); 2-qatlam — yig'indi qiymati (`5`) butun matnda **raqam chegaralari bilan** izlanadi (joylashuvdan mustaqil). 2-qatlam **sabotaj 3c dan keyin** qo'shildi va sababi quyida nomma-nom yozilgan.
- **`ConfusionMatrix` qayta ishlatildi, ikkinchi aniqlik komponenti yozilmadi** (M-11): `accuracy-block.tsx` — 163 qator, shundan **~70 qatori kod**, qolgani sabab izohi. Faylda `confusion`/`percentView` **ta'rifi 0**, foiz arifmetikasi **0**.
- **Dalil chegarasi hurmat qilindi va u KELAJAKDAGI darvozani ham hisobga oldi:** kadr tokenlari `anomaly-archive.tsx` da **0**, dalil esa mavjud `EvidenceLink` orqali — ya'ni `href={` ham bu katalogga **kirmadi** (08-17 ning G-38(a) si uni 0 ga qulflaydi).
- **AI-02 jumlasi shartsiz va bezaksiz:** manbada **aynan 1 marta**, `tone="warning"` **0**, `role="alert"` ichida **emas** — va bu ikkala holatda ham (o'lchangan/o'lchanmagan) test bilan o'lchandi.
- **Uch sabotajning har biri IKKI-UCH shaklda o'tkazildi va ikkitasi testning O'ZIDAGI yolg'on-yashilni fosh qildi** (08-13 dagi S-2b topilmasining aynan sinfi).
- **Yangi npm paketi yo'q** (T-08-SC): `package.json` va lockfile tegilmadi; ikkala komponent ham mavjud primitivlar va mavjud hooklardan quriladi.

## Task Commits

| # | Vazifa | RED | GREEN |
|---|--------|-----|-------|
| 1 | `anomaly-archive.tsx` — ikki sinf, ikki sanoq, kadrsiz dalil | `b6b395b` | `75427a7` |
| 2 | `accuracy-block.tsx` — mavjud matritsa ustidagi o'ram | `5dc895b` | `7c09f23` |
| 3 | G-40 sabotaj o'lchovi va test mustahkamlashi | — | `50ee6b0` |

## Sabotaj o'lchovlari (majburiy)

| # | Sabotaj | Kutilgan | **Natija** |
|---|---------|----------|------------|
| **S-1a** | `accuracy-block` ning o'lchanmagan shoxiga `(data.correct.point ?? 0) * 100` + `%` qo'yildi | (a) qizarsin | ✅ **QIZARDI.** `expected [ '%' ] to have a length of +0 but got 1` |
| **S-1b** | O'sha zaxira, **foiz belgisisiz** (yalang `0`), nomlangan sabab bilan **bir tugunda** | (a) qizarsin | ⚠ **QIZARDI, LEKIN «NOTO'G'RI» YARMI ORQALI:** `Unable to find an element with the text: Bu davrda javoblar soni…` — ya'ni matn tugunining buzilgani uchun. «Yakka nol» asserti bu sabotajni **UMUMAN ko'rmadi** |
| **S-1c** | O'sha zaxira **ayrim elementda** (nomlangan sabab **butun** qoladi) | (a) qizarsin | ⚠⚠ **«YAKKA NOL» ASSERTI YASHIL QOLDI.** Sabab o'lchandi: birlashtirilgan `textContent` da noldan oldin qo'shni jumlaning **NUQTASI** turadi va `(?<![\d.,])` uni ko'rib mosligni RAD ETADI. Test faqat **manba skani** (`?? 0`) hisobiga qizardi — ya'ni DOM yarmi **ishlamayotgan edi** |
| **S-1c′** | O'sha sabotaj, **mustahkamlangan** assert ostida (nol HAR TUGUNDA alohida izlanadi) | DOM yarmi ham qizarsin | ✅ **QIZARDI TO'G'RIDAN-TO'G'RI:** `expected true to be false` (`hasLoneZero`) |
| **S-2a** | Xato shoxi olib tashlandi, `data` o'rniga nol-to'ldirilgan javob | (b) qizarsin | ⚠ **DEGENERAT SABOTAJ:** komponent `data.measured` da **yiqildi** (`An error occurred in the <AccuracyBlock> component`), ya'ni bo'sh matritsa **umuman chizilmadi** va foiz asserti bo'sh DOM ustida yashil qoldi. Test faqat `role="alert"` yo'qligi bilan qizardi |
| **S-2b** | O'sha sabotaj, **ikkala** shoxda ham zaxira javob (matritsa HAQIQATAN chiziladi) | (b) qizarsin | ✅ **QIZARDI KUTILGAN JOYDA:** `expected [ '%', '%', '%', '%' ] to have a length of +0 but got 4` — bo'sh matritsa **to'rtta** foiz belgisi chizadi. Bu WR-05 ning aynan shakli |
| **S-3a** | `anomaly-archive` ga ikki sanoqning yig'indisini chizadigan `<dd>` qo'shildi | (f) qizarsin | ✅ **QIZARDI:** `expected [ '2', '3', '5' ] to deeply equal [ '2', '3' ]` |
| **S-3b** | O'sha yig'indi «Jami {n} ta» **jumlasi** ichida (JSX bo'laklari bilan) | (f) qizarsin | ✅ **QIZARDI** — JSX matnni tugunlarga bo'ladi, ya'ni `5` baribir sof sonli tugun bo'lib qoldi |
| **S-3c** | O'sha yig'indi **bitta interpolyatsiyalangan** tugunda (`` {`Jami ${n} ta`} ``) | (f) qizarsin | ⚠⚠ **TO'PLAM TENGLIGI YASHIL QOLDI** (tugun sof sonli emas). Test faqat **manba skani** (`unpaid_count +`) hisobiga qizardi — ya'ni bo'shliq bor edi |
| **S-3c′** | O'sha sabotaj, **ikkinchi qatlam** qo'shilgandan keyin | DOM yarmi ham qizarsin | ✅ **QIZARDI TO'G'RIDAN-TO'G'RI:** `not to match /(?<!\d)5(?!\d)/u` |

⛔ **Uchala sabotaj ham qaytarildi**; qaytarishdan keyin `git status` toza va butun to'plam yashil (quyida).

## Decisions Made

### 1. `min_sample` — reja mezoni bilan reja xulqi ORASIDAGI ziddiyat va uning yechimi

Reja ikkita narsani BIRGA talab qiladi:

- `<behavior>`: «`reports.accuracyNotMeasured` matni (**{n}, {min} bilan**) BOR»;
- `<acceptance_criteria>`: «`grep -cE "min_sample|minSample" accuracy-block.tsx` → **0**».

Ular **birga bajarilmaydi** va buni uchinchi manba hal qiladi: `report-copy.test.mjs` dagi **G-43(d)** `reports.accuracyNotMeasured` uchun `{n}` **va** `{min}` platsholderlarini **uchala locale'da qulflagan** (`REQUIRED_PLACEHOLDERS`). Ya'ni matn qiymatsiz chizilmaydi, `{min}` esa **serverning** chegarasi bo'lishi shart (§9.3: «`min_sample` va `measured` SERVERDAN»). Yagona muqobil — `wilson.ts` dagi `MIN_SAMPLE_FOR_PERCENT` konstantasi — aynan **ikkinchi chegara** bo'lardi, ya'ni mezon o'zi himoya qilayotgan qoidani buzardi.

**Qaror:** maydon **aynan bir marta** o'qiladi (`min: data.min_sample`, 140-qator) va mezonning **maqsadi** aniqroq darvoza bilan qulflanadi:

| Nima | Qanday o'lchanadi | Natija |
|------|-------------------|--------|
| Klientda ikkinchi chegara (taqqoslash) | `/(min_sample\|minSample)\s*[<>]\|[<>]=?\s*[\w.]*(min_sample\|minSample)/` | **0** |
| Klientdagi ikkinchi chegara manbai | `MIN_SAMPLE_FOR_PERCENT`, `lib/wilson` | **0** |
| Nolga tushiruvchi zaxira | `?? 0` / `|| 0` | **0** |

⚠ Ya'ni **o'qish** qoldi, **qaror qabul qilish** ketdi — §9.3 ning ikkala jumlasi ham bajarildi. Bu 08-13 ning 1-qarori bilan **teskari** sinf: u yerda kod to'g'ri, **o'lchov** noto'g'ri edi; bu yerda **mezonning o'zi** o'z maqsadidan oshib ketgan edi.

### 2. Dalil — havola, va bu tanlov KELAJAKDAGI darvoza bilan tekshirildi

Reja «`/billing?day=…` **havolasi** yoki `snapshot_id` **identifikatori**» deb tanlov qoldirgan. Havola tanlandi, lekin **yangi havola yozilmadi**: 7-fazaning `EvidenceLink` i qayta ishlatildi. Sabab mexanik va o'lchandi: 08-17 ning **G-38(a)** darvozasi `components/reports/**` da `href={` ni **0** ga qulflaydi (tokensiz yuklab olish yo'llarini taqiqlash uchun). Havolani shu faylda yozish o'sha darvozani **birinchi kunidayoq** qizartirardi; `EvidenceLink` esa `components/reconciliation/**` da yashaydi va skan maydonidan **tashqarida**.

⚠ Yon foyda: `EvidenceLink` huquqni (`camera_view`/`occupancy_review`) **o'zi** tekshiradi va dalilsiz qatorda **hech nima** chizmaydi — ya'ni ikkala qoida ham tekinga keldi.

### 3. Dalilsiz katak `sr-only` nom OLMAYDI — 08-13 ning ONGLI teskarisi

08-13 «bo'sh katak NOMLANADI» qoidasini o'rnatdi (sotuvchi ismi, eng eski qarz sanasi). Bu yerda katak **nomlanmaydi** va farq mazmunda: u yerda bo'shlik **ma'lumotning** yo'qligi edi (qatorning fakti — skrinrider uni ustun tushib qolgan deb o'qirdi), bu yerda esa **amalning** yo'qligi. Mavjud bo'lmagan havolani e'lon qilish foydalanuvchini **yo'q affordansni qidirishga** yuborardi — bu 07 D-03 ning 4-bandida allaqachon yozilgan qaror.

### 4. `AccuracyBlock` prop olmaydi

UI-SPEC §9.2 diagrammasi `<AccuracyBlock from={from} to={to}/>` ko'rsatadi. Lekin blokka **uchinchi** qiymat ham kerak — `isEmpty` (§4.4: bo'sh oraliqda so'rov yuborilmaydi, aks holda server `400` qaytaradi va ekranda **mahsulot qarori** o'rniga **xato** ko'rinardi) — va u faqat `useReportPeriod()` da bor. Ikkalasini olish (ikki prop + bitta hook) sahifa bilan blok orasida **uchinchi haqiqat manbai** tug'dirardi, ya'ni 08-13 ning naqshini buzardi. Shuning uchun uchala qiymat ham **bitta manbadan**.

### 5. O'lchanmagan namunada IKKI jumla ko'rinadi — va bu takror emas

`measured === false` da ekranda ikkita jumla turadi:

- `occupancy.notMeasuredYet` — mavjud komponentniki, «Aniqlik **hali** o'lchanmadi»;
- `reports.accuracyNotMeasured` — bu blokniki, «**Bu davrda** javoblar soni yetarli emas».

⚠ Farq **ma'noda**: `/occupancy` da davr tanlanmaydi (server standarti 30 kun), ya'ni u yerdagi jumla «umuman o'lchanmadi» degani. `/reports` da davrni **foydalanuvchi** tanlagan — «hali o'lchanmadi» ni o'qigan direktor «tizim hech qachon tekshirilmagan» degan **noto'g'ri xulosaga** kelardi va davrni kengaytirib ko'rish xayoliga kelmasdi. §9.3 aynan shu ikkalasini talab qiladi: «namuna holati jumlasi ko'rinadi (**mavjud xulq**) **+** nomlangan sabab».

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] Arxiv jadvalining olti matni katalogda yo'q edi**

- **Found during:** Task 1
- **Issue:** Reja `<action>` da «bitta jadval, `kind` ustuni bilan» va «bo'sh davr → `EmptyState` (bo'sh holat 3)» deydi, lekin `reports.*` da jadvalning **birorta ustun sarlavhasi** ham, bo'sh holat matni ham yo'q edi. UI-SPEC §14.7 bo'sh holat 3 ni **matn bilan** yozgan, §14.3 esa uni katalogga kiritmagan.
- **Nega qo'shni namespace'dan olinmadi:** `recon.stallColumn`/`evidenceColumn`/`statusColumn` **aynan mos** matnga ega, lekin ular **boshqa yuza** ning kalitlari (IN-05) — bir kun `recon` matni o'zgarganda hisobot varag'i **jimgina** o'zgarardi. ⚠ **Komponent** qayta ishlatilishi esa boshqa sinf: `EvidenceLink`/`CaseStatusBadge` — prezentatsion mexanizm, matn emas, va rejaning o'zi `recon.caseStatus.*` ni qayta ishlatishni **buyurgan**.
- **Fix:** `reports.*` ga 6 kalit — `kindColumn`, `stallColumn`, `evidenceColumn`, `statusColumn`, `emptyAnomalies`, `emptyAnomaliesHint`. uz-Latn va ru **qo'lda**, uz-Cyrl `i18n:gen` bilan.
- **Verification:** `i18n:check` → **1348 kalit × 3 til** (avval 1342); hosil qilingan kirill satrlarida lotin harfi **yo'q**; glossariy o'zaklari saqlangan (ru `emptyAnomaliesHint` da «мест»), taqiqlangan sinonimlar (`лавк`, `магазин`) ishlatilmadi.
- **Committed in:** `75427a7`

**2. [Rule 1 — Bug] `accuracy-block.test.tsx` dagi «yakka nol» asserti yolg'on-yashil edi**

- **Found during:** Task 3 (sabotaj S-1c)
- **Issue:** Assert birlashtirilgan `textContent` ustidan yurardi; noldan oldingi jumla **nuqta** bilan tugaganda `(?<![\d.,])` mosligni rad etadi va «nol yo'q» da'vosi **yashil** qolardi.
- **Fix:** nol endi **har matn tugunida alohida** izlanadi (`hasLoneZero`), ya'ni qo'shni matnning ta'siri butunlay yo'q; `20` ichidagi nol hamon qonuniy, chunki lookbehind **tugun ichida** ishlaydi.
- **Verification:** o'sha sabotaj mustahkamlangandan keyin **to'g'ridan-to'g'ri** qizardi (`expected true to be false`).
- **Committed in:** `50ee6b0`

**3. [Rule 1 — Bug] `anomaly-archive.test.tsx` dagi «yig'indi yo'q» asserti bir shaklga ko'r edi**

- **Found during:** Task 3 (sabotaj S-3c)
- **Issue:** Sof sonli tugunlarning to'plam tengligi **shakldan mustaqil**, lekin **joylashuvga ko'ra ko'r**: yig'indi bitta interpolyatsiyalangan tugunga («Jami 5 ta») yozilsa, tugun sof sonli bo'lmagani uchun to'plam o'zgarmaydi.
- **Fix:** ikkinchi qatlam — yig'indi **qiymati** butun matnda raqam chegaralari bilan izlanadi. ⚠ Bu qatlam ataylab **qiymatga bog'liq** va yolg'iz turganda zaif bo'lardi (08-13 ning «inkor matcher» darsi), shuning uchun u 1-qatlamning **o'rniga emas, ustiga** qo'yildi.
- **Verification:** S-3c′ — `not to match /(?<!\d)5(?!\d)/u`.
- **Committed in:** `50ee6b0`

### Chetlanishlar (qamrov o'zgarmagan)

**4. `min_sample` mezoni — Decisions Made №1 da to'liq yozilgan.** Rejaning `grep → 0` mezoni bajarilmadi (**1 ta uchrash**), o'rniga uchta aniqroq mezon yozildi va ular testda **mexanik** o'lchanadi.

**5. Test tartibi.** Reja test fayllarini Task 3 ga biriktirgan, lekin Task 1 va 2 ni ham `tdd="true"` deb belgilagan — 08-13 dagi tanlov takrorlandi: **har vazifa o'z testini o'zidan oldin yozadi** (RED → GREEN), Task 3 ga esa rejaning o'zi ajratgan **uch majburiy sabotaj** qoldirildi. Sakkizala test ham haqiqiy RED bosqichini o'tdi.

**6. Test soni.** `accuracy-block.test.tsx` da **4** (rejadagidek). `anomaly-archive.test.tsx` da **4** (reja: 3) — qo'shimcha test **bo'sh davr** uchun: rejaning `<behavior>` bandi uni talab qiladi («Bo'sh davr → `EmptyState`, jadval chizilmaydi»), lekin (e)(f)(g) ning birortasi ham u shoxga kirmasdi.

**7. Sabotaj (2) ning literal shakli o'lchov bermadi.** «Xato shoxini olib tashlash» ning to'g'ridan-to'g'ri bajarilishi komponentni **yiqitdi** (`data.measured` — `undefined` ustida), ya'ni bo'sh matritsa **chizilmadi** va (b) ning foiz asserti bo'sh DOM ustida yashil qoldi. Sabotaj **haqiqiy shaklga** keltirildi (ikkala shoxda ham zaxira javob) va shundan keyin kutilgan joyda qizardi. ⚠ Bu §16.3 ning bandi: sabotaj **o'lchayotgan narsasini** chizishi shart.

**8. Rejaning `verify` buyrug'i ishlamaydi.** `npm --prefix frontend run test:component -- "accuracy-block|anomaly-archive"` → `No test files found`: vitest 4 filtrni **regeks emas, substring** deb o'qiydi. Ishlaydigan shakl — ikki argument: `... -- accuracy-block anomaly-archive` (**8/8 yashil**).

---

**Total deviations:** 3 auto-fixed (2 test bug, 1 missing-critical) + 5 hujjatlashtirilgan chetlanish
**Impact on plan:** Qamrov kengaymadi. №1 — rejaning o'z `<action>` bandini bajarish uchun **zarur** matn; №2/№3 — rejaning o'zi buyurgan sabotajlarning natijasi; №4 — mezon bilan xulq orasidagi ziddiyatning hal qilinishi.

## Verification Evidence

| Buyruq | Natija |
|--------|--------|
| `npm --prefix frontend run test:component` (butun to'plam) | ✅ **1068/1068** (90 fayl) — avval 1060/88; **+8 test, +2 fayl** |
| `npm --prefix frontend run test:component -- accuracy-block anomaly-archive` | ✅ **8/8** |
| `npx vitest run reports` | ✅ **29/29** (6 fayl: period-picker 6 · export-button 7 · revenue 5 · debtors 3 · anomaly 4 · accuracy 4) |
| `npx vitest run occupancy` | ✅ **70/70** — `ConfusionMatrix` va `/occupancy` yuzasida **regressiya yo'q** |
| `npm --prefix frontend run test:unit` | ✅ **272/272** |
| `npm --prefix frontend run typecheck` | ✅ EXIT 0 |
| `npm --prefix frontend run lint` | ✅ EXIT 0 |
| `npm --prefix frontend run i18n:check` | ✅ **1348 kalit × 3 til** (avval 1342; +6) |

**Qabul mezonlari (mexanik):**

| Fayl | Mezon | Talab | Natija |
|------|-------|-------|--------|
| `anomaly-archive.tsx` | `<img\|next/image\|useEvidenceImageHref\|URL.createObjectURL\|/snapshots/` | 0 | **0** ✅ |
| `anomaly-archive.tsx` | `unpaid_count \+\|totalAnomal\|combined` | 0 | **0** ✅ |
| `anomaly-archive.tsx` | `data-report-content="anomalies"` | ≥1 | **1** ✅ |
| `accuracy-block.tsx` | `ConfusionMatrix` importi; unga `from`/`to`/`period`/`label` propi | import bor, prop yo'q | ✅ (test (d) da assert) |
| `accuracy-block.tsx` | `\?\? 0\|\|\| 0` | 0 | **0** ✅ |
| `accuracy-block.tsx` | `accuracyDisclaimer` | 1 va shartsiz | **1** ✅ |
| `accuracy-block.tsx` | `function (confusion\|percentView)\|const (confusion\|percentView)` | 0 | **0** ✅ |
| `accuracy-block.tsx` | `min_sample\|minSample` | reja: 0 | **1** ⚠ (Decisions №1 — o'rniga 3 aniqroq mezon) |
| `accuracy-block.tsx` | chegara bilan taqqoslash operatori | 0 | **0** ✅ |
| `accuracy-block.tsx` | `MIN_SAMPLE_FOR_PERCENT` / `lib/wilson` | 0 | **0** ✅ |

## Known Stubs

**Yo'q.** Ikkala komponentda ham to'rtala shox chizilgan: yuklanish, xato, bo'sh holat va to'la ro'yxat.

⚠ **Lekin ular hali HECH QAYERDAN chaqirilmaydi** — `/reports` sahifasi **08-17** da tug'iladi. Bu **stub emas, to'lqin tartibi**.

⚠ **Server yarmi hali yo'q** (`reports.py`, 08-12) — hooklar real marshrutlarga qaraydi va bugun `404` oladi. Bu holatda ikkala blok ham **nomlangan xato** ko'rsatadi: bo'sh jadval ham, bo'sh matritsa ham, nol ham **emas**.

## Threat Flags

Yangi xavfsizlik yuzasi **topilmadi** — barcha o'zgarishlar rejaning `threat_model` reyestri ichida:

| Threat ID | Holat |
|-----------|-------|
| T-08-64 | ✅ `?? 0` **0**; chegara bilan taqqoslash **0**; G-40(a) + sabotaj S-1a/S-1c′ bilan qulflandi |
| T-08-65 | ✅ Xato shoxi `role="alert"` ichida; sabotaj S-2b **to'rtta** foiz belgisini fosh qildi |
| T-08-66 | ✅ Disclaimer **shartsiz**, manbada 1 marta, ikkala holatda ham DOM'da (test (c)) |
| T-08-67 | ✅ Kadr tokenlari **0**; dalil — mavjud yuzaga havola; eksportga faqat identifikator (server yarmi 08-12 da) |
| T-08-68 | ✅ Yig'indi DOM'da **yo'q** — ikki qatlam bilan; sabotaj S-3a/S-3c′ |
| T-08-SC | ✅ Yangi npm paketi **yo'q**; `package.json` va lockfile tegilmadi |

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi va 08-13 dagi junction retsepti ham ishlamadi:** asosiy repo katalogidagi `frontend/node_modules` **bo'sh** (0 element), npm keshi ham bo'sh. **Yechim:** worktree ichida `npm ci` (lockfile'dan, **yangi paketsiz**) — `package.json` va `package-lock.json` **tegilmadi**, `git status` toza qoldi (T-08-SC buzilmagan).
- ⚠ **`gate:fast` byudjeti bu yerda ham O'LCHANMADI** — 08-03/08-09/08-13 dagi ayni sabab bilan (`test:fast` `docker compose --profile test` ni ko'taradi va parallel ishlayotgan agentlarning konteynerlariga aralashardi). **O'lchangan yarim:** `vitest run` → **136 s** (90 fayl, 1068 test). ⛔ Byudjet **o'zgartirilmadi**.

## User Setup Required

Yo'q.

## Next Phase Readiness

**Tayyor:**
- 08-17 uchun **to'rtala blok mazmuni** ham tayyor va har biri `data-report-content` ni **o'zi** chiqaradi (G-37(c)(d)(e) ning DOM yarmi).
- `components/reports/**` da endi **aynan 6 mahsulot fayli** bor — G-38(a) ning `MIN_SCANNED_FILES ≥ 6` chegarasi bajarildi.

**⛔ 08-17 NING ZIMMASIDA (literal, o'lchangan):**

1. ⛔ **`accuracy` blokiga IKKINCHI `ExportButton` QO'YILMAYDI** — u `accuracy-block.tsx` ning **ichida** (UI-SPEC §9.2 diagrammasi). Sahifa tugmani faqat `revenue`, `debtors` va `anomalies` bloklariga qo'yadi.
2. ⛔ **G-42(d) ning `/snapshots/` tokeni IMPORT JUMLASINI ISTISNO QILISHI SHART.** O'lchandi: `period-picker.tsx` (08-09) `@/components/snapshots/day-picker` dan import qiladi va yo'l **ko'p qatorli import**ning **yopuvchi qatorida** turadi — ya'ni `^import` qatori bo'yicha filtr uni **ushlamaydi** va darvoza birinchi kunidayoq qizarardi. Skan **butun import jumlasini** chiqarishi kerak.
3. ⛔ **G-42(f) `TA'RIF` ni izlashi shart, yalang uchrashni emas:** `accuracy-block.tsx` da `<ConfusionMatrix report={data} />` **JSX chaqiruvi** bor va u M-11 ning talabi. `/\b(confusion|matrix)\b/i` shaklidagi regeks uni qizartirardi; to'g'ri shakl — `function|const|class` bilan boshlanadigan ta'rif.
4. ⚠ **G-42(a):** bugun `components/reports/**` da `variant="default"` **0 marta**. «Aynan 1 marta» talabini **sahifa yoki solishtiruv yuzasi** bajarishi kerak (08-17/08-18) — aks holda darvoza quyi chegarada qizaradi.
5. ⚠ **G-38(a) bugun toza:** `href={`, `download=`, `window.open`, `location.href` — oltitasi ham **0**. Dalil havolasi ataylab qo'shni katalogdagi komponentga topshirilgan (Decisions №2) — sahifa uni **buzmasin**.

**Ochiq bandlar:**
- ⚠ `gate:fast` byudjeti to'liq o'lchanmadi (yuqoriga qarang).
- ⚠ Server yarmi (`reports/anomalies`) hali yo'q — kontrakt ataylab oldinda (08-12).

## Self-Check: PASSED

**Fayllar (5/5 topildi):**
- `frontend/src/components/reports/anomaly-archive.tsx`
- `frontend/src/components/reports/anomaly-archive.test.tsx`
- `frontend/src/components/reports/accuracy-block.tsx`
- `frontend/src/components/reports/accuracy-block.test.tsx`
- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-15-SUMMARY.md`

**Commitlar (5/5 topildi):** `b6b395b` · `75427a7` · `5dc895b` · `7c09f23` · `50ee6b0`

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN tegilmadi** — worktree rejimida ular orkestratorning zimmasida (to'lqin merge qilingandan keyin markazlashgan holda yangilanadi).

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
