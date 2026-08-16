---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 13
subsystem: ui
tags: [react, next-intl, tanstack-query, nuqs, accessibility, tdd, sabotage]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-03: useRevenueReport / useReceivablesReport, revenueReportSchema / receivablesReportSchema, reports.* matn katalogi uchala tilda"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-09: useReportPeriod() (from/to/isEmpty/maxDayIso) va components/reports/** ning ommaviy-amal skaniga kirishi (W0-F5)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "unpaid-list.tsx ro'yxat naqshi — mazmun atributini ro'yxatning O'ZI chiqarishi (G-29(b) mexanikasi)"
  - phase: 06-billing-va-kassir
    provides: "pending-summary.tsx — pulni useFormatter().number() + *.amountUnit bilan chizishning yagona yo'li"
  - phase: 04-kadr-olish-va-arxiv
    provides: "formatBusinessDay() — sana-faqat qiymatni mintaqadan mustaqil chizish (WR-07)"
provides:
  - "components/reports/revenue-report.tsx — tushum jadvali + davr yig'indisi (sahifadagi yagona Display)"
  - "components/reports/debtors-report.tsx — qarzdorlik ro'yxati, ism serverdan, bo'shligi nomlangan"
  - "G-39(a) va G-39(b) darvozalarining DOM yarmi"
  - "reports.* ga 11 yangi kalit uchala tilda (ustun sarlavhalari, ikki bo'sh holat, ikki nomlangan bo'shliq)"
affects:
  - 08-15
  - 08-17

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Blok komponenti davrni PROPDAN emas, useReportPeriod() dan oladi — sahifa bilan blok orasida uchinchi haqiqat manbai tug'ilmaydi"
    - "Ekrandagi davr HAR DOIM javobning from_date/to_date idan; nuqs holati faqat SO'ROVGA ketadi"
    - "Yig'indi aria-describedby orqali IKKALA jumlaga (davr + maxraj) bog'lanadi"
    - "«Ko'rinadigan matn yo'q» da'vosi textContent minus sr-only shajaralari bilan o'lchanadi, bevosita matn tugunlari bilan EMAS"

key-files:
  created:
    - frontend/src/components/reports/revenue-report.tsx
    - frontend/src/components/reports/revenue-report.test.tsx
    - frontend/src/components/reports/debtors-report.tsx
    - frontend/src/components/reports/debtors-report.test.tsx
  modified:
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "08-13: sabotaj (2) ning IKKI SHAKLI o'lchandi va ikkinchisi MAVJUD assertdagi yolg'on-yashilni fosh qildi — `sr-only` saqlanib tire qo'shilganda «vizual bo'shlik» yarmi YASHIL qolardi; tuzatish TESTDA (ko'rinadigan matn = textContent minus sr-only)"
  - "08-13: davr jumlasi RAW ISO bilan chiziladi (period-picker bilan AYNI shakl) — mahalliylashtirilgan sana G-39(a) ning to'plam tengligini o'lchab bo'lmas holga keltirardi va ikki ekranda ikki xil davr yorlig'i paydo bo'lardi"
  - "08-13: `total_charged_soum` ham chiziladi, LEKIN Body o'lchamida — Pitfall 14 ikkala ta'rifni talab qiladi, §7.2 esa ikkinchi Display ni taqiqlaydi"
  - "08-13: `oldest_debt_date` `null` ham TO'QILMAYDI — u ham `sr-only` bilan nomlangan bo'sh katak (D-10 ning ism qoidasiga parallel sinfi)"
  - "08-13: so'rov yiqilganda bo'sh jadval yoki nol CHIZILMAYDI — nomlangan xato (sabab + tuzatish) `role=\"alert\"` ichida"

patterns-established:
  - "Bo'sh katak testi IKKI yarimdan iborat va ular MUSTAQIL sabotaj bilan o'lchanadi: «ko'rinadigan matn yo'q» va «sr-only nomi bor»"
  - "Sabotaj ikki shaklda o'tkaziladi — yalang va MAVJUD himoyani saqlab qolgan holda; ikkinchisi birinchisining ko'rmagan yuzasini ochadi"

requirements-completed: [RECON-04]

# Metrics
duration: 50min
completed: 2026-08-16
---

# Phase 8 Plan 13: Tushum va qarzdorlik ko'rinishlari Summary

**Y-1 ning ikki ro'yxati: ekrandagi davr SERVERNING javobidan chiziladi (so'ralganidan emas), yig'indi serverdan keladi va klientda birorta pul arifmetikasi yo'q; topilmagan sotuvchi ismi vizual jihatdan bo'sh, skrinriderda esa nomlangan — va bu ikkinchi qoida sabotajning IKKINCHI shakli bilan o'lchanganda testning o'zidagi yolg'on-yashilni fosh qildi.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3
- **Commits:** 5 (2 × RED + 2 × GREEN + 1 × sabotaj/mustahkamlash)
- **Files:** 7 (4 yangi, 3 matn katalogi)

## Accomplishments

- **«Davr serverniki» qoidasi mexanik darvoza bilan qulflandi.** Server `2026-09-01` qaytarganda `nuqs` esa `?from=2026-08-01` bo'lganda DOM'dagi ISO sanalar **to'plami** aynan `{2026-09-01, 2026-09-30}` — inkor matcher emas, to'plam tengligi (D-31).
- **Yig'indi hech qachon yolg'iz kelmaydi.** `aria-describedby` uni davr jumlasiga **va** maxraj jumlasiga bog'laydi; ikkalasining matni testda **to'plam** bilan solishtiriladi, ya'ni bittasi tushib qolsa darvoza qizaradi.
- **Klientda pul arifmetikasi NOL.** `reduce`/`toFixed`/`parseFloat` ikkala faylda ham 0; yig'indilar javobning o'z maydonlari.
- **Sabotaj MAVJUD testdagi yolg'on-yashilni fosh qildi** (quyida nomma-nom) — 08-09 dagi S-1b topilmasining aynan sinfi.
- **Yangi npm paketi yo'q** (T-08-SC): ikkala komponent ham mavjud `ui/` primitivlari va mavjud hooklardan quriladi.

## Task Commits

| # | Vazifa | RED | GREEN |
|---|--------|-----|-------|
| 1 | `revenue-report.tsx` — kunlik qatorlar, yagona Display | `21faebe` | `d6ba0fa` |
| 2 | `debtors-report.tsx` — ism serverdan, bo'shligi nomlangan | `4f3b14d` | `88b9503` |
| 3 | G-39 sabotaj o'lchovi va test mustahkamlashi | — | `44fe74d` |

## Sabotaj o'lchovlari (majburiy)

| # | Sabotaj | Kutilgan | **Natija** |
|---|---------|----------|------------|
| **S-1** | Davr jumlasi `data.from_date`/`to_date` o'rniga `period.from`/`period.to` dan chizildi | (a) qizarsin | ✅ **QIZARDI — 3 test.** Xabar: `expected [ '2026-08-01', '2026-09-30' ] to deeply equal [ '2026-09-01', '2026-09-30' ]`. Ya'ni **so'ralgan** sana DOM'ga chiqishi bilanoq to'plam tengligi buziladi; (b) ham qizardi, chunki `aria-describedby` ko'rsatgan matn ham o'zgardi |
| **S-2a** | `vendor_name: null` uchun `<span>—</span>` (yalang tire) | (e) qizarsin | ⚠ **QIZARDI, LEKIN «NOTO'G'RI» YARMI ORQALI.** Xabar: `expected undefined to be 'Sotuvchi ko'rsatilmagan'` — ya'ni `sr-only` **yo'qolgani** uchun. «Vizual bo'shlik» asserti bu sabotajni **UMUMAN ko'rmadi** |
| **S-2b** | `sr-only` **SAQLANDI**, yoniga `<span>—</span>` qo'shildi | (e) qizarsin | ⚠⚠ **«Vizual bo'shlik» asserti YASHIL QOLDI** (bevosita matn tugunlarini sanardi, `<span>` ichiga o'ralganini emas). Test faqat uchinchi assert (`textContent` tengligi) hisobiga qizardi — ya'ni **yarim ishlamayotgan edi** |
| **S-2b′** | O'sha sabotaj, **mustahkamlangan** assert ostida | birinchi yarim ham qizarsin | ✅ **QIZARDI TO'G'RIDAN-TO'G'RI.** Xabar: `expected '—' to be ''` — endi ikkala yarim **mustaqil** o'lchaydi |

⛔ **Uchala sabotaj ham qaytarildi**; qaytarishdan keyin `reports` yuzasining 21 komponent testi va butun to'plam yashil, `git status` toza.

## Decisions Made

### 1. «Bo'sh katak» testining ikki yarmi MUSTAQIL bo'lishi shart — va u dastlab mustaqil emas edi

Dastlabki assert katakning **bevosita** matn tugunlarini sanardi. Bu shakl «tire qo'shildi» sabotajini ko'radi degan **da'vo** edi, lekin o'lchov uni rad etdi: haqiqiy kodda to'qilgan qiymat deyarli har doim `<span className="text-text-muted">` ichiga o'raladi (rang uchun), ya'ni u bevosita tugun **emas**.

Tuzatish testda: ko'rinadigan matn = `textContent` **minus** barcha `.sr-only` shajaralari. Endi:

| Sabotaj | Yarim 1 (vizual bo'shlik) | Yarim 2 (`sr-only` nomi) |
|---------|---------------------------|---------------------------|
| yalang tire | ✅ qizil | ✅ qizil |
| `sr-only` + tire | ✅ qizil | yashil (to'g'ri — nom joyida) |

⚠ Bu 08-UI-SPEC §16.3 ning aynan bandi: sabotaj kutilgan joyni qizartirmasa, tuzatish **testda emas, HOLATDA** — bu yerda esa holat (kod) to'g'ri edi, **o'lchov shakli** noto'g'ri edi va u shu bilan aniqlandi.

### 2. Davr jumlasi RAW ISO bilan chiziladi

`reports.periodShown` = `{from} — {to}` va u `period-picker.tsx` da ham **xom ISO** bilan to'ldiriladi. Mahalliylashtirilgan sana ikki narsani buzardi: (1) G-39(a) ning to'plam tengligini o'lchab bo'lmas holga keltirardi (uch locale — uch shakl); (2) tanlagichdagi davr yorlig'i bilan blokdagi davr yorlig'i **boshqacha** ko'rinardi va foydalanuvchi ularni ikki xil davr deb o'qishi mumkin edi. Jadval **qatorlari** esa mahalliylashtiriladi (`formatBusinessDay`) — u yerda solishtiruv emas, **o'qish** talab qilinadi.

### 3. `total_charged_soum` chiziladi, lekin Display OLMAYDI

Pitfall 14 «ikkalasi ham ko'rsatilsin» deydi, §7.2 esa sahifada **aynan bitta** Display ni talab qiladi. Yechim: `total_collected_soum` — Display (`text-2xl`), `total_charged_soum` — Body (`text-sm font-semibold`). Ikkalasini teng kattalikda chizish «qaysi biri davr tushumi?» degan javobsiz savol tug'dirardi.

### 4. `oldest_debt_date: null` ham to'qilmaydi

Sxema uni `nullable` qilgan. «Bugun» yoki davr boshini yozish o'lchanmagan faktni **o'lchangan** qilib ko'rsatardi va u eksportga tushardi. Shuning uchun u ham ism bilan **ayni sinf**: bo'sh katak + `sr-only` nom (`reports.dateUnknown`).

### 5. So'rov yiqilganda bo'sh jadval CHIZILMAYDI

Ikkala blokda ham `isError` shoxi **nomlangan xato** beradi (`errors.loadFailedTitle` + `errors.loadFailedBody`, `role="alert"`). Nol yoki bo'sh jadval «bu davrda tushum yo'q» / «qarzdor yo'q» degan **yolg'on faktni** berardi — bu WR-05 ning aynan sinfi va u D-10 ning bevosita talabi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Missing Critical] O'nta ustun/holat matni katalogda yo'q edi**

- **Found during:** Task 1 va Task 2
- **Issue:** Reja «matn 08-03 da yozilgan» deydi va bu **qisman** rost: `revenueCharged`/`revenuePaid`/`revenueDiff`/`debtorsTotal`/`debtorsOldest`/`vendorUnknown`/`rowsShown` bor. Lekin jadvalni chizish uchun **yetishmaydi**: sana ustuni sarlavhasi, sotuvchi va rasta ustunlari, qarz ustuni, ikki bo'sh holat (§14.7 bandlari 1 va 2 — ular UI-SPEC da **matn bilan** yozilgan, katalogda esa **yo'q**) va o'lchanmagan sananing nomi.
- **Nega qo'shni namespace'dan olinmadi:** `recon.dayColumn`/`recon.vendorColumn` mos matnga ega, lekin ular **boshqa yuza** ning kalitlari (IN-05 qoidasi) — bir kun `recon` matni o'zgarganda hisobot varag'i **jimgina** o'zgarardi.
- **Fix:** `reports.*` ga 11 kalit — `dateColumn`, `revenueChargedHint`, `revenuePaidHint`, `emptyRevenue(+Hint)`, `debtColumn`, `vendorColumn`, `stallsColumn`, `emptyDebtors(+Hint)`, `dateUnknown`. uz-Latn va ru **qo'lda**, uz-Cyrl `i18n:gen` bilan.
- **Verification:** `i18n:check` → **1342 kalit × 3 til** (avval 1331); hosil qilingan kirill satrlarida lotin harfi **yo'q** (nomma-nom o'lchandi); glossariy o'zaklari saqlangan (`патт`, `мест`, `долг`), taqiqlangan sinonimlar (`лавк`, `магазин`, `do'kon`) ishlatilmadi.
- **Committed in:** `21faebe` (revenue), `4f3b14d` (debtors)

**2. [Rule 2 — Missing Critical] Ustun sarlavhalari Pitfall 14 farqini AYTMAS edi**

- **Found during:** Task 1
- **Issue:** Reja «ustun sarlavhalari farqni AYTADI (Pitfall 14)» deydi, 08-RESEARCH esa uni ochiq talab qiladi: «Ustun sarlavhalari uchala tilda farqni AYTSIN». Lekin UI-SPEC §14.3 dagi **shipping matn** — «Hisoblangan» va «To'langan» — qaysi sana bo'yicha ekanini **aytmaydi**. Ikkisi ham bir savolning ikki javobi bo'lib o'qilardi, holbuki ular ikki **xil** savolga javob beradi (`payments.business_date` va `daily_charges.service_date`).
- **Nega shipping matn O'ZGARTIRILMADI:** UI-SPEC §14.3 dagi qiymatlar `reports.revenueCharged`/`revenuePaid` uchun **so'zma-so'z** berilgan; ularni qayta yozish 08-03 ning qulflangan copy'siga tegishi bo'lardi.
- **Fix:** `<th>` ichida ikkinchi qator — `revenueChargedHint` («patta kuni bo'yicha») va `revenuePaidHint` («to'lov kuni bo'yicha»). Ya'ni **sarlavhaning o'zi** farqni aytadi, mavjud matn esa tegilmagan.
- **Committed in:** `21faebe` / `d6ba0fa`

**3. [Rule 1 — Bug] `debtors-report.test.tsx` dagi «vizual bo'shlik» asserti yolg'on-yashil edi**

- **Found during:** Task 3 (sabotaj S-2b)
- **Issue:** Yuqorida to'liq yozilgan (Decisions Made №1).
- **Fix:** ko'rinadigan matn = `textContent` minus `.sr-only` shajaralari
- **Verification:** o'sha sabotaj mustahkamlangandan keyin **to'g'ridan-to'g'ri** qizardi (`expected '—' to be ''`)
- **Committed in:** `44fe74d`

### Ordering deviation (qamrov o'zgarmagan)

Reja test fayllarini **Task 3** ga biriktirgan, lekin Task 1 va Task 2 ni ham `tdd="true"` deb belgilagan — ikkisi bir vaqtda bajarilmasdi. 08-09 dagi tanlov takrorlandi: **har vazifa o'z testini o'zidan oldin yozadi** (RED → GREEN), Task 3 ga esa rejaning o'zi ajratib ko'rsatgan **ikki majburiy sabotaj** qoldirildi. Natijada yettala test ham haqiqiy RED bosqichini o'tdi.

⚠ **Test soni rejadagidan bitta ko'p:** `revenue-report.test.tsx` da **5** (reja: 4). Qo'shimcha test — **salbiy nazorat**: davr jumlasining haqiqatan chizilgani alohida o'lchanadi. Usiz (a) ning «yo'qlik» da'vosi **bo'sh DOM** holatida ham yashil qolardi. `debtors-report.test.tsx` da **3** (rejadagidek).

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing-critical) + 1 ordering
**Impact on plan:** Hech biri qamrovni kengaytirmaydi. №1 va №2 — rejaning o'z `<action>` bandlarini bajarish uchun **zarur** bo'lgan matn; №3 — rejaning o'zi buyurgan sabotajning natijasi.

## Verification Evidence

| Buyruq | Natija |
|--------|--------|
| `npm --prefix frontend run test:unit` | ✅ **272/272** |
| `npx vitest run` | ✅ **1060/1060** (88 fayl) — avval 1052/86; **+8 test, +2 fayl** |
| `npx vitest run reports` | ✅ **21/21** (period-picker 6 · export-button 7 · revenue 5 · debtors 3) |
| `node --test scripts/bulk-action-surface.test.mjs` | ✅ **8/8** — ikkala yangi fayl ommaviy-amal skanidan o'tdi |
| `npm --prefix frontend run typecheck` | ✅ EXIT 0 |
| `npm --prefix frontend run lint` | ✅ EXIT 0 |
| `npm --prefix frontend run i18n:check` | ✅ **1342 kalit × 3 til** (avval 1331; +11) |

**Qabul mezonlari (mexanik):**

| Fayl | Mezon | Talab | Natija |
|------|-------|-------|--------|
| `revenue-report.tsx` | `data-report-content="revenue"` | ≥1 | **1** ✅ |
| `revenue-report.tsx` | `\.reduce\(\|\.toFixed\(\|parseFloat\(` | 0 | **0** ✅ |
| `revenue-report.tsx` | `text-base\|text-xl\|text-3xl\|text-\[` | 0 | **0** ✅ |
| `revenue-report.tsx` | ARIA panjara roli | 0 | **0** ✅ |
| `debtors-report.tsx` | ikkinchi so'rov hooki | 0 | **0** ✅ |
| `debtors-report.tsx` | `Noma'lum\|«—»\|>—<` | 0 | **0** ✅ |
| `debtors-report.tsx` | `sr-only` | ≥1 | **5** ✅ |
| `debtors-report.tsx` | `\bphone\b\|full_name\|chat_id` | 0 | **0** ✅ |
| `debtors-report.tsx` | `text-2xl` | 0 | **0** ✅ |
| ikkalasi | `checkbox\|Array.isArray` | 0 | **0** ✅ |

⚠ **Taqiqlangan tokenlar IZOHLARDA HAM yozilmadi** (08-09 dagi ogohlantirishning davomi): qabul mezoni **xom** `grep`, ya'ni «nega bu maydon taqiqlangan» izohi maydon **nomini** yozsa mezon qizarardi. Izohlar ularni **tavsif** bilan nomlaydi («telefon raqami, to'liq ism maydoni va Telegram identifikatori»). ⚠ Keyingi ijrochiga: G-42(g) (08-15) `stripComments()` bilan skanerlaydi, ya'ni **u yerda** izoh matni erkin bo'ladi — lekin bu rejaning mezoni xom edi.

## Known Stubs

**Yo'q.** Ikkala komponent ham to'liq ishlaydi: yuklanish, xato, bo'sh holat va to'la ro'yxat — to'rtala shox ham chizilgan.

⚠ **Lekin ular hali HECH QAYERDAN chaqirilmaydi:** `app/[locale]/(app)/reports/page.tsx` **08-17** da tug'iladi. Bu **stub emas, to'lqin tartibi** — 08-03 kontraktni, 08-09 boshqaruvlarni, bu reja ikki ro'yxatni, 08-17 esa sahifani beradi.

⚠ **Eksport tugmasi bu komponentlar ICHIDA emas** va bu ataylab: §8.1 bo'yicha har blokda o'z `[Excel bo'lib yuklab olish]` tugmasi bor, lekin blokni **sahifa** quradi (`data-report-block`) va tugmani ham u joylashtiradi. Rejaning `files_modified` bandi ham `export-button` ni bu ikki faylga bog'lamagan. ⛔ **08-17 ning zimmasida:** har blokka `<ExportButton kind="revenue|debtors" period={{from, to}} unavailable={period.isEmpty}/>` qo'shish.

⚠ **Server yarmi hali yo'q** (`reports.py`, M-18) — hooklar real marshrutlarga qaraydi va bugun `404` oladi. Bu holatda ikkala blok ham **nomlangan xato** ko'rsatadi, bo'sh jadval emas.

## Threat Flags

Yangi xavfsizlik yuzasi **topilmadi** — barcha o'zgarishlar rejaning `threat_model` reyestri ichida:

| Threat ID | Holat |
|-----------|-------|
| T-08-54 | ✅ Davr javobdan; G-39(a) **va** sabotaj S-1 bilan qulflandi (3 test qizardi) |
| T-08-55 | ✅ `reduce`/`toFixed`/`parseFloat` ikkala faylda **0**; yig'indilar javobning maydonlari |
| T-08-56 | ✅ Aloqa maydonlari **0** — kodda ham, izohda ham; `vendor_name` esa bu katalogda **qonuniy** (D-07) va sabab izohda literal |
| T-08-57 | ✅ Bo'sh katak + `sr-only`; sabotaj **ikki shaklda** o'lchandi va ikkinchisi testning o'zidagi bo'shliqni topdi |
| T-08-SC | ✅ Yangi npm paketi **yo'q**; `package.json` tegilmadi |

## Issues Encountered

- **Worktree'da `node_modules` yo'q edi** (gitignored). **Yechim:** asosiy repo katalogiga **junction** (`mklink /J`) — `package.json` ham, lockfile ham tegilmadi, tarmoqdan hech nima olinmadi (T-08-SC buzilmagan).
- ⚠ **`gate:fast` byudjeti bu yerda ham O'LCHANMADI** — 08-03/08-09 dagi ayni sabab bilan: `test:fast` `docker compose --profile test` ni ko'taradi va u asosiy repo bilan **bir xil compose loyihasini** ishlatadi, ya'ni parallel ishlayotgan boshqa ijrochi agentlarning konteynerlariga aralashardi. **O'lchangan yarim:** `npx vitest run` → **127 s** (88 fayl, 1060 test). ⛔ Byudjet **o'zgartirilmadi** va o'zgartirish taklif qilinmaydi (§16.4: tinch xost, uch o'lchov, eng yomon × 1,20 — egasi fazani yopuvchi reja).

## User Setup Required

Yo'q.

## Next Phase Readiness

**Tayyor:**
- 08-17 uchun ikki blok mazmuni tayyor va ikkalasi ham `data-report-content` ni **o'zi** chiqaradi (G-37(c)(d)(e) ning DOM yarmi shu bilan bajariladigan bo'ldi)
- 08-15 uchun `components/reports/**` da **to'rt** mahsulot fayli bor (G-38(a) ning ≥6 fayl chegarasi uchun yana ikkitasi kerak — ular 08-15/08-18 da tug'iladi)

**08-17 ning zimmasida (bu faylda literal yozilgan):**
- Har ikki blokka `<ExportButton/>` qo'shish (yuqorida, Known Stubs)
- `<PeriodPicker/>` ni sahifada **aynan bir marta** chizish; bloklar oraliqni hookdan oladi

**Ochiq bandlar:**
- ⚠ `gate:fast` byudjeti to'liq o'lchanmadi (yuqoriga qarang)
- ⚠ Server yarmi (`reports.py`) hali yo'q — kontrakt ataylab oldinda

## Self-Check: PASSED

**Fayllar (5/5 topildi):**
- `frontend/src/components/reports/revenue-report.tsx`
- `frontend/src/components/reports/revenue-report.test.tsx`
- `frontend/src/components/reports/debtors-report.tsx`
- `frontend/src/components/reports/debtors-report.test.tsx`
- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-13-SUMMARY.md`

**Commitlar (5/5 topildi):** `21faebe` · `d6ba0fa` · `4f3b14d` · `88b9503` · `44fe74d`

⚠ `STATE.md` va `ROADMAP.md` **ATAYIN tegilmadi** — worktree rejimida ular orkestratorning zimmasida (to'lqin merge qilingandan keyin markazlashgan holda yangilanadi).

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
