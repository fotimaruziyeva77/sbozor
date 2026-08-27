---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 09
subsystem: ui
tags: [nuqs, next-intl, react, date-boundary, accessibility, tdd, registry-gate]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-03: PERIOD_PRESETS/REPORT_KINDS yopiq reyestrlari, REPORT_ERROR_CODES + reportErrorView(), downloadReport()/downloadCompareReport() yagona eksport zanjiri, reports.* matn katalogi"
  - phase: 04-kadr-olish-va-arxiv
    provides: "businessDayIn / isValidIsoDay / shiftIsoDay sof sana yordamchilari (snapshots/day-picker.tsx)"
  - phase: 06-kassir-va-tolovlar
    provides: "billing/day-picker.tsx — standart qiymat URL'ga yozilmasligi va yaroqsiz qiymatning jimgina standartga tushishi naqshi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "05-UI-SPEC §15 G-18 qatori — bulk-action-surface.test.mjs qamrovining YAGONA manbai"
provides:
  - "components/reports/period-picker.tsx — PeriodPicker komponenti va useReportPeriod() hooki (from/to/preset/isEmpty/maxDayIso)"
  - "components/reports/export-button.tsx — ExportButton, DISKRIMINATSIYALANGAN ITTIFOQ props bilan (oraliq yoki kun)"
  - "presetOf(from, to, todayIso) — oraliqdan presetning teskari hisobi"
  - "G-38(c) va G-38(d) darvozalarining komponent qatlami"
  - "05-UI-SPEC §15 G-18 qatorida BESHINCHI naqsh: components/reports/** (W0-F5)"
affects:
  - 08-13
  - 08-15
  - 08-17
  - 08-18

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "URL davri IKKI parametrda, lekin BITTA `useQueryStates` yozuvida — ikki alohida setter ikki URL yangilanishi berardi"
    - "Preset URL'da SAQLANMAYDI — reyestrdan iteratsiya qilib TESKARI hisoblanadi (presetOf)"
    - "Teskari oraliq QONUNIY bo'lgan YAGONA holat — preset oralig'iga AYNAN mos kelganda (thisMonth, oyning 1-kuni)"
    - "Poyga qulfi `useRef` da, `useState` da EMAS — farq O'LCHANDI (quyida)"
    - "Yo'qlik paragraf to'plamining TENGLIGI bilan o'lchanadi (D-31), inkor matcher bilan emas"

key-files:
  created:
    - frontend/src/components/reports/period-picker.tsx
    - frontend/src/components/reports/period-picker.test.tsx
    - frontend/src/components/reports/export-button.tsx
    - frontend/src/components/reports/export-button.test.tsx
  modified:
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-UI-SPEC.md
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "08-09: `?to=<bugun>` testi YOLG'ON-YASHIL edi va bu O'LCHOV bilan topildi — yolg'iz `to` uzatilganda oraliq `from` NING YO'QLIGI tufayli standartga tushardi, ya'ni chegara filtri hech qachon bosib o'tilmasdi; test `?from=` bilan tuzatildi va sabotaj ostida qizardi"
  - "08-09: `max` sabotaji (a) ni qizartirdi, (b) ni QIZARTIRMADI — ikki qatlam MUSTAQIL ekani o'lchandi; ikkinchi qatlam uchun alohida sabotaj o'tkazildi"
  - "08-09: poyga qulfi `useRef` da — `useState` qulfi `fireEvent`x3 ostida YASHIL, bitta `act` ichidagi 3 bosishda esa QIZIL (yolg'on-yashil o'lchandi)"
  - "08-09: eksport xatosi `role=\"alert\"` ichida — reja «role siz» deydi, 08-UI-SPEC §15 esa `role=\"alert\"` ni xato uchun NOMMA-NOM talab qiladi; test rolga TAYANMAY (getByText) o'lchaydi"
  - "08-09: `disabled` EMAS, `aria-disabled` — 08-UI-SPEC §12.2 jadvali `disabled` deydi, lekin O'SHA HUJJATNING §15 i uni ochiq TAQIQLAYDI; §15 tanlandi"
  - "08-09: bo'sh oy holatida chegara matni TAKRORLANMAYDI — u EmptyState tavsifi bo'lib turadi (ikki nusxa bir kun ajralib ketardi)"

patterns-established:
  - "Sana chegarasining IKKI qatlami ikki ALOHIDA sabotaj bilan o'lchanadi — bitta sabotaj ikkalasini ham qamramaydi"
  - "Poyga qulfi testi bitta `act` ichida native `click()` bilan yoziladi; `fireEvent` ni takrorlash React'ning oraliq render'i tufayli poygani QAYTA TIKLAMAYDI"

requirements-completed: [RECON-04]

# Metrics
duration: 65min
completed: 2026-08-16
---

# Phase 8 Plan 09: Davr tanlagichi va eksport tugmasi Summary

**Hisobot yuzasining ikki boshqaruvi: davr tanlagichi (maksimum KECHA, ikki mustaqil qatlamda) va eksport tugmasi (yagona `apiRequest`+`saveBlob` yo'li, `useRef` poyga qulfi) — ikkalasi ham to'rt sabotaj bilan o'lchandi va ulardan biri MAVJUD testdagi yolg'on-yashilni fosh qildi.**

## Performance

- **Duration:** ~65 min
- **Tasks:** 3/3
- **Commits:** 6 (3 × RED + 3 × GREEN)
- **Files:** 8 (+1146 / −1)

## Accomplishments

- **Yuqori chegara IKKI QATLAMDA va ikkala qatlam ham MUSTAQIL o'lchandi.** `max` atributi va URL normallashtirish filtri — sabotaj ko'rsatdiki, birini buzish ikkinchisining testini qizartirmaydi. Ya'ni ular haqiqatan ikki himoya, bitta himoyaning ikki nomi emas.
- **Mavjud testdagi YOLG'ON-YASHIL fosh qilindi.** `?to=<bugun>` testi chegara filtrini umuman bosib o'tmasdi (`from` yo'qligi tufayli oraliq baribir standartga tushardi). Tuzatilgandan keyin sabotaj ostida qizardi.
- **Poyga qulfining `useRef` bo'lishi O'LCHOV bilan asoslandi** — `useState` qulfi test ostida yashil, brauzer semantikasida esa buzuq.
- **`components/reports/**` ommaviy-amal skaniga kirdi** (W0-F5) — 05-UI-SPEC §15 ga beshinchi naqsh birinchi mahsulot fayli bilan **bir commitda** landi.
- **Yangi npm paketi yo'q** (T-08-SC): sana tanlagichi native `<input type="date">`.

## Task Commits

| # | Vazifa | RED | GREEN |
|---|--------|-----|-------|
| 1 | Davr tanlagichi + W0-F5 | `064c128` | `a3331e9` |
| 2 | Eksport tugmasi | `b17d2fa` | `814dced` |
| 3 | G-38(d) va poyga qulfi | `ea70d18` | `2aea20d` |

## Sabotaj o'lchovlari (majburiy)

| # | Sabotaj | Kutilgan | **Natija** |
|---|---------|----------|------------|
| **S-1** | `period-picker` da `max={maxDayIso}` → `max={todayIso}` | (a) **va** (b) qizarsin | ⚠ **(a) QIZARDI, (b) YASHIL QOLDI.** Reja ikkalasini kutgan edi; o'lchov ko'rsatdiki (b) `max` atributiga UMUMAN tegishli emas — u **ikkinchi qatlamni** (URL filtri) o'lchaydi |
| **S-1b** | URL filtri `rawTo > kecha` → `rawTo > bugun` | (b) qizarsin | ⚠ **AVVAL YASHIL QOLDI** — testning o'zi nuqsonli edi (quyida). Test tuzatilgandan keyin **QIZARDI**: DOM'da `2026-08-16` (bugun) paydo bo'ldi — aynan T-08-37 ning shakli |
| **S-2** | `export-button` dan poyga qulfi olib tashlandi | (g) qizarsin | ✅ **QIZARDI** — `expected 1 times, but got 3 times` |
| **S-3** | Qulf `useRef` o'rniga `useState` ga o'tkazildi | — (qo'shimcha nazorat) | ⚠⚠ **`fireEvent`×3 ostida YASHIL (yolg'on-yashil), bitta `act` ichidagi 3 bosishda QIZARDI.** Ya'ni testning `act` shakli **yuk ko'taruvchi**, va qulfning `useRef` bo'lishi shu bilan asoslandi |

⛔ **To'rttasi ham qaytarildi**; qaytarishdan keyin 13/13 komponent testi va butun to'plam yashil.

## Decisions Made

### 1. `?to=<bugun>` testi YOLG'ON-YASHIL edi — S-1b buni fosh qildi

Boshlang'ich test `?to=<bugun>` ni **yolg'iz** uzatardi. Lekin `from` bo'lmagach, normallashtirish **birinchi** qoidaga (yaroqsiz shakl) tushadi va standartni qaytaradi — ya'ni «kelajakdagi `to` rad etiladi» qatori **hech qachon bajarilmasdi**. Test yashil edi, lekin u **boshqa narsani** o'lchardi.

O'lchandi: chegara filtri olib tashlanganda test **yashil qoldi**. Tuzatish — `?from=<yaroqli>&to=<bugun>`; shundan keyin sabotaj **qizardi** va DOM'da bugungi sana ko'rindi.

⚠ Bu 08-UI-SPEC §16.3 ning aynan bandi: «sabotaj hech nima qizartirmasa, tuzatish **testda emas, HOLATDA**» — bu yerda o'lchov tanlagan **kirish ma'lumoti** ikkala shoxda bir xil natija berayotgan edi.

### 2. `max` sabotaji ikkala testni qizartirmadi — va bu YAXSHI xabar

Reja S-1 dan «(a) va (b) qizarsin» degan edi. O'lchov boshqacha: (a) — `max` atributining o'zi, (b) — **URL filtri**. Ular bir-birini almashtirmaydi, ya'ni «ikki qatlam» da'vosi **haqiqatan ikki qatlam**. Agar bitta sabotaj ikkalasini ham qizartirganda, bu qatlamlardan biri ikkinchisining **ko'zgusi** ekanini bildirardi.

Shuning uchun S-1b **qo'shildi**: har qatlam **o'z** sabotaji bilan o'lchanadi.

### 3. Poyga qulfi `useRef` da — `useState` qulfi test ostida ko'rinmaydi

| Qulf | Test shakli | Natija |
|------|-------------|--------|
| yo'q | `act` ichida 3 bosish | ✅ QIZIL (3 chaqiruv) |
| `useState` | `fireEvent`×3 | ⛔ **YASHIL — yolg'on** |
| `useState` | `act` ichida 3 bosish | ✅ QIZIL (3 chaqiruv) |
| `useRef` | `act` ichida 3 bosish | ✅ YASHIL (1 chaqiruv) |

Sabab: har `fireEvent` **o'z `act` ini yopadi**, ya'ni React bosishlar orasida qayta chizadi va ikkinchi bosish allaqachon yangi holatni ko'radi. Brauzerda esa uch tez bosish **bitta vazifada** yetib keladi. `busy` holati baribir kerak — u `aria-busy` ni boshqaradi; ref esa **mexanizmni** qulflaydi.

### 4. Teskari oraliq QONUNIY bo'lgan yagona holat — preset oralig'iga aynan mos kelish

§4.4 ikki qoidani beradi va ular **ziddek ko'rinadi**: «`from > to` → standartga tushadi» **va** «`thisMonth` oyning 1-kunida `lastMonth` ga tushmaydi, jimgina ham o'zgarmaydi». Yechim mexanik: normallashtirish **avval** reyestrdan iteratsiya qilib oraliqning biror **preset oralig'iga** mos kelishini tekshiradi va mos kelsa **shartsiz qabul qiladi** — teskari bo'lsa ham.

⛔ Busiz nomlangan holat sahifa yangilanishida **jimgina yo'qolardi** va URL ulashib bo'lmasdi.

### 5. Xato `role="alert"` ichida — reja bilan UI-SPEC o'rtasidagi ziddiyat

Reja test (h) ni «inline matn **`role` siz** chiziladi» deb yozgan. Lekin:

1. **08-UI-SPEC §15** jonli hududlar qatori nomma-nom: «⛔ `role="alert"`: **faqat** xato»;
2. Rejaning O'ZI naqsh sifatida `import-errors.tsx:221` ni ko'rsatadi — **u yerda `role="status"` bor**, ya'ni «rolsiz» naqsh emas;
3. Faqat ko'z bilan ko'rinadigan xato — skrinrider foydalanuvchisi uchun **yo'q** xato.

Tanlov: `role="alert"`, **lekin test uni ROLGA TAYANMAY** (`getByText`) o'lchaydi — ya'ni rejaning «role siz chiziladi» bandi **qidiruv uslubi** sifatida bajarildi. Da'vo matnning **ko'rinishi** haqida, uning e'lon mexanizmi haqida emas.

### 6. `disabled` EMAS, `aria-disabled` — bitta hujjat ichidagi ziddiyat

08-UI-SPEC **§12.2** jadvali «Tugma `disabled` + `aria-busy`» deydi; **§15** esa o'sha hujjatda «⛔ `aria-disabled`, `disabled` **emas** — Eksport tugmasi» deb **sababi bilan** yozadi. §15 tanlandi (reja ham shuni talab qiladi): o'chirilgan tugma fokusni yo'qotadi va foydalanuvchi «tugma qayerga ketdi?» holatida qoladi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `?to=<bugun>` testi chegara filtrini o'lchamasdi**

- **Found during:** Task 3 (sabotaj S-1b)
- **Issue:** Test yolg'iz `?to=` uzatardi; `from` yo'qligi tufayli normallashtirish **birinchi** shoxga tushardi va chegara qoidasi hech qachon bajarilmasdi. Chegara filtri butunlay olib tashlanganda ham test **yashil** qolgan.
- **Fix:** `?from=<yaroqli>&to=<bugun>` — endi oraliq shakl jihatidan to'liq va **yagona** rad sababi `to > kecha` bo'ladi
- **Verification:** Sabotaj ostida **qizardi** (`+2026-08-16` DOM'da paydo bo'ldi), tiklashdan keyin yashil
- **Committed in:** `2aea20d`

**2. [Rule 2 — Missing Critical] Bo'sh oy holati uchun matn kaliti yo'q edi**

- **Found during:** Task 1
- **Issue:** §14.7 bo'sh holat 5 («Joriy oyda hali yopilgan kun yo'q») 08-03 katalogida **yo'q** edi, lekin rejaning test (d) si uni nomma-nom talab qiladi. Preset `<select>` uchun yorliq kaliti ham yo'q edi (§14.1: har boshqaruvda `<label htmlFor>`).
- **Fix:** `reports.emptyMonth` va `reports.presetLabel` — uz-Latn va ru **qo'lda**, uz-Cyrl `i18n:gen` bilan
- **Verification:** `i18n:check` → **1331 kalit × 3 til**; hosil qilingan kirill satrlarida lotin harfi yo'q (`Жорий ойда ҳали ёпилган кун йўқ`, `Тайёр оралиқ`)
- **Committed in:** `064c128`

**3. [Rule 2 — Missing Critical] Ikkinchi qatlam uchun ALOHIDA sabotaj**

- **Found during:** Task 3
- **Issue:** Reja bitta sabotaj (`max` → bugun) ikkala testni ham qizartirishini kutgan. O'lchov buni rad etdi — ya'ni **ikkinchi qatlam sabotaj bilan umuman o'lchanmagan** qolardi.
- **Fix:** S-1b qo'shildi (URL filtri sabotaji), va u №1 dagi test nuqsonini fosh qildi
- **Committed in:** `2aea20d` (o'lchov commit xabarida)

### Ordering deviation (qamrov o'zgarmagan)

Reja test fayllarini **Task 3** ga biriktirgan, lekin Task 1 va Task 2 ni ham `tdd="true"` deb belgilagan. Bu ikkisi bir vaqtda bajarilmasdi. Tanlangan yechim: **har vazifa o'z testini o'zidan oldin yozadi** (RED → GREEN, ikki commit), Task 3 ga esa rejaning o'zi ajratib ko'rsatgan **eng qiyin ikki darvoza** — G-38(d) va poyga qulfi — qoldirildi. Natijada uchala vazifa ham haqiqiy RED bosqichini o'tdi va yakuniy test soni rejadagidek: `period-picker.test.tsx` **6**, `export-button.test.tsx` **7** (reja: ≥5 va ≥4).

⚠ Shu sababdan `thisMonth` ning nomlangan holati Task 1 commitida hali **yo'q** edi — u Task 3 da o'z RED darvozasi bilan qo'shildi. Qamrov kengaymadi.

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing-critical) + 1 ordering

## Verification Evidence

| Buyruq | Natija |
|--------|--------|
| `npm --prefix frontend run test:unit` (`node --test scripts/*.test.mjs`) | ✅ **272/272** |
| `npx vitest run` | ✅ **1052/1052** (86 fayl) |
| `npx vitest run reports` | ✅ **13/13** (6 + 7) |
| `node --test scripts/bulk-action-surface.test.mjs` | ✅ **8/8** — beshinchi katalog e'loni bilan |
| `npm --prefix frontend run typecheck` | ✅ EXIT 0 |
| `npm --prefix frontend run lint` | ✅ EXIT 0 |
| `npm --prefix frontend run i18n:check` | ✅ **1331 kalit × 3 til** (avval 1325; +6) |

**Qabul mezonlari (mexanik):**

| Mezon | Talab | Natija |
|-------|-------|--------|
| `businessDayIn\|shiftIsoDay\|isValidIsoDay` (period-picker.tsx) | ≥1 | **13** ✅ |
| `text-base\|text-xl\|text-3xl\|text-[` (period-picker.tsx) | 0 | **0** ✅ |
| `| **G-18** |` bilan boshlanadigan qator (05-UI-SPEC.md) | aynan 1 | **1** ✅ (M-4 buzilmagan) |
| `components/reports/**` (05-UI-SPEC.md) | mavjud | **1** ✅ |
| `download=\|download}\|window.open\|location.href\|createElement("a")\|href={` (export-button.tsx) | 0 | **0** ✅ |
| `variant="default"` (`components/reports/**`) | 0 | **0** ✅ |
| `aria-busy` (export-button.tsx) | ≥1 | **2** ✅ |
| `checkbox` / `Array.isArray` (`components/reports/**`) | 0 | **0** ✅ |

⚠ **Taqiqlangan tokenlar IZOHLARDA HAM yozilmadi.** Qabul mezoni **xom** `grep` (izoh filtri yo'q), ya'ni «nega bu yo'l ishlatilmaydi» izohi tokenning O'ZINI yozsa, mezon qizarardi. Izohlar ularni **tavsif** bilan nomlaydi («anchor atributi bilan bo'ladimi, yangi oyna ochish bilanmi, manzil satrini almashtirish bilanmi»). ⚠ Keyingi ijrochiga: G-38(a) (08-15) izohlarni `stripComments()` bilan tashlaydi, ya'ni **u yerda** izoh matni erkin — lekin bu rejaning mezoni **xom** edi.

## Known Stubs

**Yo'q.** Ikkala komponent ham to'liq ishlaydi.

⚠ **Lekin ular hali HECH QAYERDAN chaqirilmaydi:** `app/[locale]/(app)/reports/page.tsx` **08-15** da tug'iladi. Bu **stub emas, to'lqin tartibi** — 08-03 kontraktni, bu reja boshqaruvlarni, 08-15 esa sahifani beradi. Bugun foydalanuvchiga ko'rinadigan yuza **yo'q**.

⚠ **Server yarmi ham hali yo'q** (`reports.py`, M-18) — `downloadReport` real marshrutga qaraydi va `404` oladi. Eksport tugmasi bu holatda **nomlangan xato** ko'rsatadi (`report_export_failed` zaxira juftligi), jim qolmaydi.

## Iste'molchilar uchun kontrakt (08-13/08-15/08-17/08-18)

```ts
const period = useReportPeriod();   // {from, to, preset, isEmpty, todayIso, maxDayIso, set*}
useRevenueReport({ from: period.from, to: period.to }, { enabled: !period.isEmpty });
<ExportButton kind="revenue" period={{ from: period.from, to: period.to }} />
<ExportButton kind="three-way" day={day} />
```

⛔ **`isEmpty` NI HURMAT QILISH SHART:** bo'sh oraliqda so'rov yuborilsa server `400 range_invalid` qaytarardi va ekranda **mahsulot qarori** o'rniga **xato** ko'rinardi.

⛔ **`<PeriodPicker/>` sahifada AYNAN BIR MARTA** chiziladi (`data-report-block="period"`, G-37 da `CONTENT_EXEMPT`); qolgan bloklar oraliqni **hookdan** oladi.

## Threat Flags

Yangi xavfsizlik yuzasi **topilmadi** — barcha o'zgarishlar rejaning `threat_model` reyestri ichida:

| Threat ID | Holat |
|-----------|-------|
| T-08-35 | ✅ Brauzerning o'z yuklab olish yo'llari kodda **0** marta; xulqiy test bosishni `downloadReport` ga bog'laydi |
| T-08-36 | ✅ Yaroqsiz/teskari davr jimgina standartga tushadi; haqiqiy chegara **serverda** (08-07) |
| T-08-37 | ✅ Maksimum KECHA **ikki mustaqil qatlamda**, ikkalasi ham **alohida** sabotaj bilan o'lchandi; `reports.maxDayHint` sababni aytadi |
| T-08-38 | ✅ Poyga qulfi `useRef` da; sabotaj **va** `useState` muqobili o'lchandi |
| T-08-SC | ✅ Yangi npm paketi **yo'q**; `package.json` tegilmadi (native `<input type="date">`) |

## Next Phase Readiness

**Tayyor:**
- 08-13/08-15/08-17/08-18 uchun davr tanlovi va eksport tugmasi joyida; ikkalasi ham reyestrlardan iteratsiya qiladi
- `components/reports/**` ommaviy-amal skanida — **bu commitdan boshlab** har yangi fayl avtomatik qamrab olinadi

**08-15 ning zimmasida (o'zgarmadi):**
- `report-copy.test.mjs` ga `components/reports/**` bloklari — **G-38(a), G-41(b), G-42** o'z quyi chegaralari bilan (≥6 fayl; bugun **2** ta bor)

**Ochiq bandlar:**
- ⚠ `gate:fast` byudjeti bu yerda ham **o'lchanmadi** (08-03 dagi sabab bilan bir xil: `test:fast` Docker compose loyihasini parallel agentlar bilan **ulashardi**). O'lchangan yarim: `npx vitest run` → **116 s** (86 fayl, 1052 test) — 08-03 dagi 162 s dan past, lekin **issiq** worktree'da (`node_modules` junction) va shu sababdan u bilan ham **to'g'ridan-to'g'ri solishtirilmaydi**. ⛔ Byudjet **o'zgartirilmadi** va o'zgartirish taklif qilinmaydi (§16.4: tinch xost, uch o'lchov, eng yomon × 1,20 — egasi fazani yopuvchi reja)
- ⚠ `reports.exporting` kaliti **hech qayerda ishlatilmadi** — §12.2 tugma matnining **o'zgarmasligini** talab qiladi. Kalit 08-03 da tug'ilgan; uni o'chirish yoki `sr-only` e'lon sifatida ishlatish — **08-15** ning qarori

## User Setup Required

Yo'q.

## Self-Check: PASSED

**Fayllar (5/5 topildi):**
- `frontend/src/components/reports/period-picker.tsx`
- `frontend/src/components/reports/period-picker.test.tsx`
- `frontend/src/components/reports/export-button.tsx`
- `frontend/src/components/reports/export-button.test.tsx`
- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-09-SUMMARY.md`

**Commitlar (6/6 topildi):** `064c128` · `a3331e9` · `b17d2fa` · `814dced` · `ea70d18` · `2aea20d`

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN tegilmadi** — worktree rejimida ular orkestratorning zimmasida (to'lqin merge qilingandan keyin markazlashgan holda yangilanadi).

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
