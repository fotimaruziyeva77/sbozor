---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 17
subsystem: ui
tags: [nextjs, app-router, navigation, nuqs, tdd, sabotage, source-scan, registry-gate]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-09: PeriodPicker + useReportPeriod() (from/to/isEmpty) va ExportButton"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-13: revenue-report / debtors-report — mazmun atributini ro'yxatning O'ZI chiqaradi"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-15: anomaly-archive / accuracy-block — katalogda oltinchi mahsulot fayli, G-38(a) chegarasi bajarildi"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-03: report-copy.test.mjs skeleti, stripComments(), REPORT_KINDS/PERIOD_PRESETS reyestrlari"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "reconciliation/page.tsx — huquq ko'zgusi + Suspense + blok reyestri naqshi; G-29(b) mazmun juftligi mexanikasi"
provides:
  - "app/[locale]/(app)/reports/page.tsx — besh blokli reyestr (data-report-block), uchala locale'da SSG"
  - "app/[locale]/(app)/reports/page.test.tsx — G-37(a)(c)(d)(e) darvozasi"
  - "app-shell.tsx da 17-nav yozuvi (/reports) va nav.reports uchala tilda"
  - "report-copy.test.mjs da G-38(a), G-41(b), G-42(a)–(g) manba skani (+23 test)"
  - "stripImports() — ko'p qatorli import jumlasini butunlay olib tashlovchi filtr"
affects:
  - 08-18
  - 08-20

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Blok darvozasi UCH qatlam: to'plam tengligi (a) + mazmun juftligi (c) + mock'dan hosila mazmun (e); majburiy sabotaj uchalasini AJRATADI (yashil/qizil/qizil)"
    - "Import filtri `^import` QATORI emas, BUTUN JUMLA bo'lishi shart — ko'p qatorli importning yopuvchi qatoridagi token aks holda ushlanmaydi"
    - "Kelajakda tug'iladigan fayl egalik qiladigan darvoza TOTAL FUNKSIYA bo'lib yoziladi: egasi yo'q -> aynan 0, egasi bor -> aynan 1 va faqat unda; darvoza o'zi qattiqlashadi"
    - "Darvoza istisnosi (`vendor_name`) YUK KO'TARISHI alohida assert bilan o'lchanadi — aks holda istisno o'lchanmagan da'vo bo'lib qolardi"
    - "Sanoq darvozasini oshirishda YANGI a'zoning JOYI ham qulflanadi — yalang'och sanoq bo'shatish bo'lardi"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/reports/page.tsx
    - frontend/src/app/[locale]/(app)/reports/page.test.tsx
  modified:
    - frontend/src/components/shell/app-shell.tsx
    - frontend/scripts/report-copy.test.mjs
    - frontend/scripts/reconciliation-copy.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "08-17: G-42(a) `variant=\"default\"` AYNAN 1 talabini SAHIFA bajara OLMAYDI va bu O'LCHANDI (S-6): sahifaga aksent qo'yilganda darvoza sanog'i 0 bo'lib qoldi, chunki `app/**` skan maydonidan TASHQARIDA; assert TOTAL funksiya bo'lib yozildi va 08-18 fayli kelgan zahoti O'ZI qattiqlashadi"
  - "08-17: (e) ning `business_date` da'vosi XOM ISO emas, CHIZILGAN satr bilan o'lchanadi — `formatBusinessDay` `dateStyle: \"medium\"` beradi va xom ISO qatorda HECH QACHON ko'rinmaydi; kutilma testda QAYTA quriladi, yordamchi import QILINMAYDI"
  - "08-17: (a) uchinchi render BO'SH javob bilan — «ma'lumot yo'q -> blokni yashirish» eng tabiiy noto'g'ri refleks va ikki xil DAVR uni umuman o'lchamasdi"
  - "08-17: nav sanoq darvozasi 16 -> 17 ga ko'tarilganda YANGI YOZUVNING JOYI ham qulflandi — yalang'och sanoqni oshirish darvozani bo'shatardi"
  - "08-17: import filtri BUTUN jumlani oladi (`^import` qatorini emas) va uning ZARURLIGI o'lchov testi bilan qulflandi — faraz eskirsa darvoza jimgina bo'shamaydi"
  - "08-17: sahifa sarlavhasining `text-2xl` i §7.2 dagi «aynan bitta Display» EMAS — u qobiq elementi va o'n oltita marshrutda aynan shu shaklda"

patterns-established:
  - "Sabotaj MANBA SKANI darvozalarida BIR shaklda yetarli bo'ladi (matn skani deterministik), DOM darvozalarida esa ikki-uch shakl kerak — farq o'lchandi"
  - "Kelajak egasi bo'lgan darvoza uchun uchinchi yo'l: chegarani pasaytirish ham, yolg'on-qizil qoldirish ham emas — IKKI SHOXLI TOTAL assert"

requirements-completed: [RECON-04, RECON-05]

# Metrics
duration: 60min
completed: 2026-08-16
---

# Phase 8 Plan 17: `/reports` sahifasi, blok darvozasi va manba skani Summary

**Beshala blok DAVRDAN QAT'I NAZAR chiziladi va buni uch qatlamli darvoza qo'riqlaydi — majburiy sabotaj (a) ni YASHIL, (c) va (e) ni QIZIL qildi, ya'ni uch qatlamning har biri BOSHQA narsani o'lchashi ISBOTLANDI; `components/reports/**` manba skani esa 08-03 da ochiq qoldirilgan tetikni yopdi va uning eng nozik bandi — G-42(a) — sahifadan bajarib bo'lmasligi O'LCHANDI, taxmin qilinmadi.**

## Performance

- **Duration:** ~60 min
- **Tasks:** 3/3
- **Commits:** 4 (1 × RED + 1 × GREEN + 2 × darvoza)
- **Files:** 8 (2 yangi, 6 o'zgargan)

## Accomplishments

- **`/reports` tug'ildi va uchala locale'da SSG:** `npm run build` → `/uz-Latn/reports`, `/uz-Cyrl/reports`, `/ru/reports`. 08-09, 08-13 va 08-15 qurgan **oltita** komponent bugundan boshlab HAQIQATAN chiziladi — bu fazadagi «qurilgan, lekin chaqirilmagan» holatning yopilishi.
- **Blok darvozasining uch qatlami sabotaj bilan AJRATILDI.** `<RevenueReport/>` → bo'sh o'ram: (a) **3/3 yashil**, (c) **2 ta qizil**, (e) **1 ta qizil**. Ya'ni to'plam tengligi bo'sh o'ramni haqiqatan **mukammal o'tkazadi** va (c)/(e) busiz yozilmagan bo'lardi — 06-faza G-25 ning o'lchangan ko'rligi shu bilan qaytarilmadi.
- **08-15 ning BESHTA literal topshirig'i bajarildi** (quyida nomma-nom) va ikkitasi **o'lchov bilan** tasdiqlandi: import filtrining zarurligi bugungi toza kodda o'lchandi, G-42(a) esa **bajarib bo'lmasligi** bilan.
- **Manba skani 23 ta yangi test bilan tirik:** `report-copy.test.mjs` 20 → **43**. To'rtta sabotaj to'rtta **turli** darvozani qizartirdi va hech biri qo'shnisiga tegmadi.
- **Navigatsiya byudjeti o'lchandi va darvoza KUCHAYTIRILDI:** `NAV_ITEMS` 16 → 17, `MOBILE_PRIMARY_COUNT` **4** o'zgarmadi, kassir/nazoratchi paneli **2 yozuv** bo'lib qoldi, `rbac.ts` **tegilmadi**.
- **Yangi npm paketi yo'q** (T-08-SC): `package.json` va lockfile **tegilmadi**; sahifa faqat mavjud komponentlardan quriladi.

## Task Commits

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | G-37 darvozasi — **RED** (sahifa hali yo'q) | `c7bdc44` |
| 2 | `/reports` sahifasi + nav yozuvi + `nav.reports` × 3 — **GREEN** | `cc635b7` |
| 3 | `components/reports/**` manba skani (G-38(a), G-41(b), G-42) | `01ce3f5` |
| 4 | Nav reyestri darvozasi 16 → 17 (§4.7 M-5) | `f1f46ae` |

## 08-15 ning BESH topshirig'i — nomma-nom holat

| # | Topshiriq | Holat |
|---|-----------|-------|
| **1** | `accuracy` blokiga **ikkinchi** `ExportButton` qo'yilmasin | ✅ Sahifa tugmani **faqat** `revenue`/`debtors`/`anomalies` ga qo'ydi; `accuracy` bo'limida sahifa hech qanday tugma chizmaydi (sabab kodda LITERAL) |
| **2** | G-42(d) `/snapshots/` tokeni **import jumlasini** istisno qilsin | ✅ `stripImports()` **butun jumlani** oladi (`^import` qatorini emas). ⛔ **O'lchandi:** filtrsiz bugun `period-picker.tsx` topiladi, filtr bilan **0** — va bu o'lchov **alohida test** bo'lib qulflandi |
| **3** | G-42(f) **TA'RIF** ni izlasin, yalang uchrashni emas | ✅ Naqsh `function\|class\|interface\|type\|const\|let\|var` + nom; import jumlasi olib tashlanadi. Nazorat testi qonuniy `<ConfusionMatrix report={data} />` **+ import** juftligini taqiq **DEB O'QIMASLIGINI** o'lchaydi |
| **4** | G-42(a) `variant="default"` **aynan 1** bo'lsin | ⚠ **BAJARIB BO'LMAYDI — O'LCHANDI.** Quyida Decisions №1 |
| **5** | G-38(a) toza qolsin — `components/reports/**` ga havola yozilmasin | ✅ Oltala token ham **0**. Solishtiruv havolasi **sahifa faylida** (skan maydonidan tashqarida) va u `href={` emas, **satr literali** |

## Sabotaj o'lchovlari (majburiy)

| # | Sabotaj | Kutilgan | **Natija** |
|---|---------|----------|------------|
| **S-1** | `<RevenueReport/>` → `<div data-report-block="revenue"/>` | (a) **yashil**, (c) va (e) **qizil** | ✅ **AYNAN SHUNDAY, uchala natija ham.** (a) **3/3 yashil** — to'plam o'zgarmadi; (c) **2 qizil**: `expected Set{'debtors','anomalies','accuracy'} to deeply equal Set{'revenue','debtors','anomalies','accuracy'}`; (e) **1 qizil**: `expected null not to be null` |
| **S-2** | `export-button.tsx` ga `<a download="hisobot.xlsx">` qatori | G-38(a) qizarsin | ✅ **QIZARDI, AYNAN BITTA darvoza:** `components/reports/export-button.tsx -> \`download=\`` |
| **S-3** | `debtors-report.tsx` ga `{row.phone}` katagi | G-42(g) qizarsin | ✅ **QIZARDI:** `components/reports/debtors-report.tsx -> \`phone\``. ⚠ Yon natija: `vendor_name` **qo'shimcha qizarish bermadi** — ikki ro'yxat qoidasi haqiqatan ajratilgan |
| **S-4** | `export-button.tsx` ga `<Button variant="default">` | G-42(a) qizarsin | ✅ **QIZARDI FAYL NOMI BILAN:** `actual Set(1){'export-button.tsx'}` vs `expected Set(0){}`. ⚠ Reja «**ikkinchi** tugma» degan edi; bugun **birinchisi** ham qizaradi, ya'ni darvoza rejadagidan qattiqroq |
| **S-5a** | 08-18 egasi (`ledger-import.tsx`) **simulyatsiya** qilindi: 1 aksent + `ConfirmDialog` ichida destruktiv | darvoza **yashil** qolsin | ✅ **43/43 YASHIL** — quyi chegara o'zi faollashdi va hech kim hech nima tahrirlamadi |
| **S-5b** | O'sha fayl, aksent `secondary` ga o'zgartirildi | quyi chegara qizarsin | ✅ **QIZARDI:** `actual Set(0){}` vs `expected Set(1){'ledger-import.tsx'}` |
| **S-5c** | Destruktiv `ConfirmDialog` dan `Button` ga ko'chirildi | teg egasi qizarsin | ✅ **QIZARDI:** `actual ['Button']` vs `expected ['ConfirmDialog']` — atributdagi `() => run()` ning `>` belgisiga **qaramay** |
| **S-6** | ⛔ **SAHIFAGA** `variant="default"` qo'yildi | (orkestrator: darvoza yashil bo'lsin) | ⚠⚠ **DARVOZA YASHIL QOLDI, LEKIN SANOQ 0 BO'LIB.** Ya'ni sahifadagi aksent darvozaga **UMUMAN KO'RINMAYDI** — «sahifa bajarsin» ko'rsatmasi **mexanik jihatdan imkonsiz**. Decisions №1 |

⛔ **Oltala sabotaj ham qaytarildi** va simulyatsiya fayli o'chirildi; qaytarishdan keyin `git status` **toza**, butun to'plam yashil (quyida).

⚠ **Kuzatilgan farq:** DOM darvozalarida (08-13/08-15) sabotaj **ikki-uch shaklda** o'tkazilishi kerak edi, chunki bir shakl assertning ko'r nuqtasidan o'tib ketardi. Manba skani darvozalarida (S-2…S-4) **bitta shakl yetdi** va sabab mexanik: matn skani DOM'ning shakl erkinligiga ega emas — token bor yoki yo'q. ⛔ Buning o'rniga bu yerda **boshqa** o'lchov turi kerak bo'ldi: darvozaning **ikkala shoxi** ham (egasi bor/yo'q) alohida sinovdan o'tdi.

## Decisions Made

### 1. ⛔⛔ G-42(a) ni SAHIFA bajara olmaydi — bu taxmin emas, O'LCHOV

08-15 topshirig'i «aynan 1 marta» talabini «sahifa **yoki** solishtiruv yuzasi (08-17/08-18)» ga qoldirgan, orkestrator esa uni «**SAHIFA** bajarishi kerak» deb toraytirgan. **Ikkala shakl ham bajarilmadi va sabab ikki qatlamli:**

| Qatlam | Dalil |
|--------|-------|
| **Dizayn** | §13.3 aksentni **to'rt elementli YOPIQ** to'plam qilib yozgan; to'rtinchisi — Y-3 dagi `[Daftarni yuklash]`. O'sha bandning o'zi to'rtta `[Excel bo'lib yuklab olish]` tugmasini **nomma-nom aksentsiz** deb yozgan. Sahifaga aksent qo'yish §13.3 ning **bevosita** buzilishi bo'lardi |
| ⛔ **Mexanika (O'LCHANDI — S-6)** | `app/[locale]/(app)/reports/page.tsx` — `components/reports/**` skan maydonidan **TASHQARIDA**. Sahifaga `variant="default"` qo'yilganda darvoza sanog'i **0 bo'lib qoldi** va test **yashil** ketdi. Ya'ni sahifadagi tugma talabni bajarmaydi — u darvozaga **ko'rinmaydi** |

⛔ **Va ikkinchi yarmi undan qat'iyroq:** G-42(a) ning IKKINCHI bandi — `variant="destructive"` **aynan 1 va `ConfirmDialog` chaqiruvida** — DL-6 (daftarni almashtirish tasdig'i, §4.6) ga tegishli. **Ikkala** tugmaning ham egasi bitta fayl: `ledger-import.tsx`, va u **08-18** (to'lqin 6) da tug'iladi.

**Qaror — 08-03 ning uchinchi yo'li, TOTAL ASSERT shaklida:**

| Muqobil | Nega rad etildi |
|---------|------------------|
| Shartsiz `=== 1` yozish | Bugun **yolg'on-qizil**: `npm run gate` har commitda yiqilardi va keyingi ijrochi blokni «shovqin» deb **o'chirardi** (08-03 izohida nomma-nom yozilgan sinf) |
| `<= 1` bilan yumshatish | Darvoza **doimiy** bo'shab qolardi — quyi chegarani hech kim qaytarib ko'tarmasdi |
| Sahifaga aksent qo'yish | §13.3 buziladi **va** S-6 ga ko'ra baribir **ishlamaydi** |

⛔ **Tanlangan shakl — ikki shoxli va HAR IKKALASIDA aniq da'vo bor** (ya'ni «jim teshik» yo'q):

```
egasi YO'Q  ->  sanoq AYNAN 0 va aksent chiqaradigan fayllar to'plami AYNAN bo'sh
egasi BOR   ->  sanoq AYNAN 1 va to'plam AYNAN {ledger-import.tsx}
```

⚠ **Darvoza o'zi qattiqlashadi:** 08-18 faylni keltirgan zahoti quyi chegara **faollashadi** va buni hech kim yodda tutishi shart emas. Bu **S-5a/S-5b** bilan o'lchandi: egasi mavjud + aksent bor → **yashil**; egasi mavjud + aksent yo'q → **qizil**.

### 2. `business_date` da'vosi XOM ISO bilan o'lchanmaydi

Reja (e) ni «`rows[0].business_date` DOM'da» deb yozgan. Lekin `revenue-report.tsx` qatorni `formatBusinessDay(format, …)` bilan chizadi va u `dateStyle: "medium"` beradi — uz-Latn'da `2026-09-05` → **`5-sen, 2026`**. Ya'ni xom ISO satri qatorda **hech qachon** ko'rinmaydi.

⚠ **Va «to'g'rilashning» ikki yo'li ham yomon bo'lardi:**

1. Javobning `from_date` ini `rows[0].business_date` ga tenglashtirish — u davr jumlasida **xom ISO** bo'lib chiziladi, ya'ni assert **qator chizilmasa ham** yashil qolardi (aynan (e) qaytarmoqchi bo'lgan yolg'on-yashil);
2. `formatBusinessDay` ni **import qilish** — 05-15 darsi: darvoza o'zi tekshirayotgan yordamchiga bog'lanardi va ikkalasi birga o'zgarganda jimgina yashil qolardi.

**Qaror:** kutilma testda `Intl.DateTimeFormat` bilan **qayta quriladi** (kun 12:00 UTC ga langarlanadi — `lib/format-day.ts` ning yozilgan kontrakti). Kirish qiymati baribir **mock'dan** keladi, ya'ni «mazmun mock'dan hosila» sharti buzilmaydi. Ikkinchi yarim — `tbody tr` soni — esa formatdan **butunlay mustaqil**.

### 3. (a) ning uchinchi renderi — BO'SH javob

Reja «ikki xil davr bilan ikki render» degan. Ikkalasi ham qo'shildi, lekin **uchinchisi** ham yozildi va u eng qimmati: `rows: []` bergan javob.

⚠ Sabab: «ma'lumot yo'q → blokni yashirish» — eng **tabiiy noto'g'ri refleks**, va ikki xil DAVR uni **umuman o'lchamasdi** (ikkala davrda ham ma'lumot bor edi). Chizilmagan «Qarzdorlik ro'yxati» direktorga «qarzdor yo'q» bo'lib o'qilardi — §8.1 ning aynan bandi: **bo'sh davr — bo'sh holat, yo'q blok emas**.

### 4. Nav sanoq darvozasini oshirishda JOY ham qulflandi

07-fazaning darvozasi `NAV_ITEMS` ni **16** ga qulflagan; 08-UI-SPEC §4.7 [M-5] esa **17** ni nomma-nom yozgan. Yalang'och sanoqni 17 ga oshirish darvozani **bo'shatardi**: «bittasi qo'shildi, lekin qayerga?» degan savol ochiq qolardi va mobil panelning birinchi to'rttasi (tartibdan chiqadi) o'lchanmay qolardi.

**Qaror:** sanoq bilan **birga** yangi yozuvning joyi ham assert qilindi (`reports === reconciliation + 1`), ya'ni darvoza avvalgisidan **kuchliroq**. Kassir paneli testi **tegilmadi** va u hamon 2 yozuv beradi.

### 5. Sahifa sarlavhasining `text-2xl` i §7.2 ni buzmaydi

§7.2 «sahifada **aynan bitta** Display» deydi va u — davr tushumi. Sahifa sarlavhasi esa **qobiq** elementi va kodbazadagi **o'n oltita** marshrutda aynan shu shaklda (`text-2xl font-semibold tracking-tight`). Uni kichraytirish sarlavhani blok sarlavhalari (`text-lg`) bilan **tenglashtirardi** va ierarxiyani yo'qotardi. ⚠ Sahifa fayli G-42(e) skan maydonida ham emas — qoida `components/reports/**` haqida.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] 07-fazaning nav darvozasi `NAV_ITEMS` ni 16 ga qulflagan edi**

- **Found during:** Task 1 dan keyingi to'liq `test:unit` yugurishi
- **Issue:** `reconciliation-copy.test.mjs:1272` — `assert.equal(entries.length, 16)`. Yangi yozuv qo'shilishi bilan **butun `npm run gate` yiqilardi**. Reja bu faylni `files_modified` da **nomlamagan**, lekin 08-UI-SPEC §4.7 [M-5] o'sishni nomma-nom yozgan (16→17).
- **Fix:** sanoq 17 ga; **qo'shimcha** — yangi yozuvning joyi ham qulflandi (Decisions №4). Kassir paneli testi tegilmadi.
- **Verification:** `npm run test:unit` → **295/295** (avval 294/295, bitta qizil).
- **Committed in:** `f1f46ae`

**2. [Rule 2 — Missing Critical] `nav.reports` kaliti uchala tilda YO'Q edi**

- **Found during:** Task 1
- **Issue:** `NAV_ITEMS` yozuvi `t(\`nav.${labelKey}\`)` ni chaqiradi va kalit `src/global.ts` augmentatsiyasi orqali **tiplangan** — ya'ni kalitsiz yozuv `tsc` ni yiqitardi (runtime'dagi `MISSING_MESSAGE` ga ham aylanmasdi). Reja matn ishini `<action>` da nomlamagan.
- **Fix:** `nav.reports` — uz-Latn va ru **qo'lda** (§14.2 jadvalidagi so'zma-so'z qiymatlar: «Hisobotlar» / «Отчёты»), uz-Cyrl `i18n:gen` bilan.
- **Verification:** `i18n:check` → **1349 kalit × 3 til** (avval 1348); hosil qilingan `Ҳисоботлар` §14.2 dagi qiymat bilan **aynan** mos, lotin harfi yo'q.
- **Committed in:** `cc635b7`

### Chetlanishlar (qamrov o'zgarmagan)

**3. G-42(a) ning assert shakli — Decisions №1 da to'liq yozilgan.** Rejaning «aynan 1 marta» mezoni **shartsiz** shaklda bajarilmadi (bugun 0 ta uchrash); o'rniga **ikki shoxli total assert** yozildi va u 08-18 fayli kelgan zahoti `=== 1` ga qulflanadi. Uchala shox ham sabotaj bilan o'lchandi (S-4, S-5a, S-5b).

**4. Test tartibi.** Reja sahifani Task 1 ga, uning darvozasini Task 2 ga bo'lgan, lekin Task 2 ni `tdd="true"` deb belgilagan — sahifa avval yozilsa, darvoza **hech qachon RED bo'lmasdi**. 08-09/08-13/08-15 dagi tanlov takrorlandi: **darvoza o'zidan oldin yozildi** (RED → GREEN), ya'ni Task 1 va Task 2 bitta juftlikka birlashdi. Task 3 esa rejaning o'zi ajratgan **uch majburiy sabotaj** bilan qoldi.

**5. `business_date` assertining shakli — Decisions №2.** Reja «`rows[0].business_date` DOM'da» degan; u **xom** ISO shaklida chizilmaydi va da'vo **chizilgan satr** bilan o'lchanadi.

**6. Test soni.** `page.test.tsx` da **11** test: (a) **3** (reja: 2 — uchinchisi bo'sh javob, Decisions №3), (c) **3**, (d) **1**, (e) **4**. `report-copy.test.mjs` da **+23** (reja soni bermagan; har blokda taqiq + quyi chegara + **nazorat** testi).

**7. Sabotaj soni.** Reja **to'rtta** sabotaj buyurgan (G-37 + uchtasi); **oltitasi** o'tkazildi. Qo'shimcha ikkitasi — S-5 (kelajak egasining ikkala shoxi) va S-6 (orkestrator ko'rsatmasining mexanik tekshiruvi) — ikkalasi ham **qaror asoslash** uchun kerak edi va ularsiz Decisions №1 **o'lchanmagan da'vo** bo'lib qolardi.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing-critical) + 5 hujjatlashtirilgan chetlanish
**Impact on plan:** Qamrov kengaymadi. №1 — rejani umuman yakunlash uchun **zarur** (aks holda `gate` qizil); №2 — rejaning o'z `<action>` bandini bajarish uchun zarur; №3 — mezon bilan mexanika orasidagi ziddiyatning **o'lchov bilan** hal qilinishi.

## Verification Evidence

| Buyruq | Natija |
|--------|--------|
| `npm --prefix frontend run test:unit` | ✅ **295/295** (avval 272; **+23**) |
| `npx vitest run` (butun to'plam) | ✅ **1079/1079** (91 fayl) — avval 1068/90; **+11 test, +1 fayl** |
| `npx vitest run reports/page` | ✅ **11/11** |
| `node --test scripts/report-copy.test.mjs` | ✅ **43/43** (avval 20; **+23**) |
| `node --test scripts/role-gate.test.mjs` | ✅ **6/6** — RBAC juftligi tegilmagan |
| `npx vitest run app-shell` | ✅ **9/9** — mobil kontrakt va rol panellari o'zgarmagan |
| `npm --prefix frontend run typecheck` | ✅ EXIT 0 |
| `npm --prefix frontend run lint` | ✅ EXIT 0 |
| `npm --prefix frontend run i18n:check` | ✅ **1349 kalit × 3 til** (avval 1348; +1) |
| `npm --prefix frontend run build` | ✅ EXIT 0 — `/[locale]/reports` **uchala locale'da SSG** |

**Qabul mezonlari (mexanik):**

| Mezon | Talab | Natija |
|-------|-------|--------|
| `reports/page.tsx` mavjud va `Suspense` ishlatadi | ha | **ha** ✅ |
| `grep -c "data-report-content" reports/page.tsx` | 0 | **0** ✅ |
| `app-shell.tsx` da `"/reports"` (href union + `NAV_ITEMS`) | 2 | **2** ✅ |
| `app-shell.tsx` da `"reports"` (labelKey union + `NAV_ITEMS`) | 2 | **2** ✅ |
| `git diff --stat frontend/src/lib/rbac.ts` | bo'sh | **bo'sh** ✅ |
| `MOBILE_PRIMARY_COUNT` | 4 | **4** ✅ |
| `page.test.tsx` da `CONTENT_EXEMPT.size === 1` alohida assert | bor | **bor** ✅ |
| (a) testi IKKI xil davr bilan render qiladi | ha | **ha** (+ uchinchi: bo'sh javob) ✅ |
| (e) testi `tbody tr` ni `rows.length` bilan solishtiradi | ha | **ha** (revenue, debtors, anomalies) ✅ |
| `report-copy.test.mjs` da `MIN_SCANNED_FILES` | ≥6 | **6** ✅ |
| `vendor_name` taqiq ro'yxatida yo'q + to'plam tengligi | ha | **ha** ✅ (+ istisno **yuk ko'tarishi** alohida o'lchandi) |
| `variant="default"` sanog'i qulflangan | «aynan 1» | ⚠ **ikki shoxli total assert** (Decisions №1) |
| G-38(a) tokenlari `components/reports/**` da | har biri 0 | **0** ✅ (6 token, 7 fayl skanerlandi) |
| G-41(b) nomlari | har biri 0 | **0** ✅ (10 nom) |
| G-42(b)(c)(e)(g) tokenlari | har biri 0 | **0** ✅ |
| G-42(d) kadr tokenlari (import istisno) | 0 | **0** ✅ (filtrsiz **1** — o'lchandi) |
| G-42(f) aniqlik ta'riflari (import istisno) | 0 | **0** ✅ |

## Known Stubs

**Yo'q** — sahifaning beshala bloki ham HAQIQIY komponentlarni chizadi, birortasi platsholder emas va buni G-37(e) mock'dan hosila qilingan to'rtta da'vo bilan o'lchaydi.

⚠ **Lekin ikkita TO'LQIN TARTIBI bandi bor va ular stub EMAS:**

1. ⛔ **`/reports/compare` havolasi bugun 404 beradi** — o'sha marshrut **08-18** (to'lqin 6) da tug'iladi. Havola rejaning bevosita talabi (§4.7: solishtiruv navigatsiyaga **kirmaydi**, u `/reports` **ichidan** ochiladi), ya'ni uni bugun yozmaslik 08-18 ga «havolani ham qo'shishni unutma» degan **yozilmagan** topshiriq qoldirardi.
2. ⚠ **Server yarmi (`reports.py`, 08-12) shu to'lqinda PARALLEL ishlayapti** — hooklar real marshrutlarga qaraydi. Marshrut hali yo'q bo'lsa **to'rtala blok ham NOMLANGAN XATO** ko'rsatadi (`role="alert"`), bo'sh jadval ham, nol ham **emas** (08-13/08-15 qarori).

## Threat Flags

Yangi xavfsizlik yuzasi **topilmadi** — barcha o'zgarishlar rejaning `threat_model` reyestri ichida:

| Threat ID | Holat |
|-----------|-------|
| T-08-75 | ✅ **accept** — sahifa va `app-shell.tsx` izohlari ikkalasida ham LITERAL: huquq ko'zgusi menyuni **yashiradi**, haqiqiy nazorat **serverda** (`require_permission`) |
| T-08-76 | ✅ G-42(g) **ikki ro'yxat** + to'plam tengligi + `vendor_name` istisnosining **yuk ko'tarishi** o'lchandi; sabotaj **S-3** aynan `phone` ni fosh qildi |
| T-08-77 | ✅ G-38(a) oltala tokeni **0** (7 fayl); sabotaj **S-2** `<a download>` ni fosh qildi |
| T-08-78 | ✅ G-37 uch qatlami + majburiy sabotaj **S-1** ning uch xil natijasi (yashil/qizil/qizil) |
| T-08-SC | ✅ Yangi npm paketi **yo'q**; `package.json` va lockfile **tegilmadi** |

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi** (asosiy repo katalogi ham **bo'sh**). **Yechim:** worktree ichida `npm ci` — lockfile'dan, **yangi paketsiz**; `package.json` va `package-lock.json` **tegilmadi**, `git status` toza qoldi (T-08-SC buzilmagan).
- **Nazorat testlarining sun'iy yo'li platformaga bog'liq edi:** `path.relative(SRC, "/probe.ts")` disk ildizigacha `../` zanjirini bergan va uchta nazorat asserti qizargan. **Yechim:** sun'iy manba kaliti `SRC` **ichida** quriladi (`probe()` yordamchisi). ⚠ Bu **darvozaning o'zida emas, nazoratida** edi — haqiqiy uchala skan bloki birinchi yugurishdayoq to'g'ri natija bergan.
- ⚠ **`gate:fast` byudjeti bu yerda ham O'LCHANMADI** — 08-03/08-09/08-13/08-15 dagi ayni sabab bilan (`test:fast` `docker compose --profile test` ni ko'taradi va parallel ishlayotgan 08-12 agentining konteynerlariga aralashardi). **O'lchangan yarim:** `vitest run` → **122 s** (91 fayl, 1079 test) va `build` → **13,3 s** kompilyatsiya. ⛔ Byudjet **o'zgartirilmadi**.

## User Setup Required

Yo'q.

## Next Phase Readiness

**Tayyor:**
- **08-18** uchun sahifa naqshi to'liq: huquq ko'zgusi → `Suspense` → blok reyestri → mazmun atributi ro'yxatda. `/reports/compare` ning blok darvozasi (G-37(b), `{"day","ledger","comparison"}`) **shu shaklda** yoziladi va `CONTENT_EXEMPT = {"day"}` bo'ladi.
- **08-20** mezon testi uchun `/reports` marshruti uchala locale'da SSG va u blok atributi bilan o'lchanadigan holatda.

**⛔ 08-18 NING ZIMMASIDA (literal, o'lchangan):**

1. ⛔ **`ledger-import.tsx` AYNAN BITTA `variant="default"` VA AYNAN BITTA `variant="destructive"` chiqarishi SHART**, ikkinchisi esa **`ConfirmDialog` chaqiruvida** bo'lishi kerak. Darvoza **o'zi qattiqlashadi**: fayl paydo bo'lgan zahoti quyi chegara faollashadi (S-5a/S-5b/S-5c bilan o'lchangan). ⚠ **Aksentni boshqa faylga qo'yish ham qizaradi** — to'plam tengligi fayl **nomini** o'lchaydi.
2. ⛔ **`compare-table.tsx` / `diff-cell.tsx` da `href={` YOZILMAYDI** — G-38(a) endi **tirik** va `components/reports/**` ni to'liq skanerlaydi. Dalil yoki navigatsiya havolasi kerak bo'lsa: qo'shni katalogdagi mavjud komponent (08-15 qarori 2) yoki **sahifa faylining o'zi** (skan maydonidan tashqarida).
3. ⛔ **`total_diff`/`grandTotal` sinfidagi ONTA nom taqiqlangan** (G-41(b)) va u aynan solishtiruv yuzasiga qaratilgan — «Jami farq» ustuni yoki o'zgaruvchisi **birinchi yozilgan kunidayoq** qizaradi.
4. ⚠ **`/reports/compare` marshruti hali yo'q va sahifadagi havola bugun 404 beradi** — u 08-18 ning **birinchi** ishi bo'lishi kerak.
5. ⚠ **`text-base`/`text-xl`/`text-3xl`/`text-[` — 0** (G-42(e)) va solishtiruv jadvali ustunlari uchun **beshinchi o'lcham** o'ylab topilmaydi.

**Ochiq bandlar:**
- ⚠ `gate:fast` byudjeti to'liq o'lchanmadi (yuqoriga qarang).
- ⚠ Server yarmi (`GET /reports/*`) 08-12 da, shu to'lqinda parallel — birlashtirilgandan keyin `/reports` da **haqiqiy ma'lumot** ko'rinadi.

## Self-Check: PASSED

**Fayllar (7/7 topildi):**
- `frontend/src/app/[locale]/(app)/reports/page.tsx`
- `frontend/src/app/[locale]/(app)/reports/page.test.tsx`
- `frontend/src/components/shell/app-shell.tsx`
- `frontend/scripts/report-copy.test.mjs`
- `frontend/scripts/reconciliation-copy.test.mjs`
- `frontend/messages/uz-Latn.json` · `ru.json` · `uz-Cyrl.json`
- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-17-SUMMARY.md`

**Commitlar (4/4 topildi):** `c7bdc44` · `cc635b7` · `01ce3f5` · `f1f46ae`

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN tegilmadi** — worktree rejimida ular orkestratorning zimmasida (to'lqin merge qilingandan keyin markazlashgan holda yangilanadi).

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
