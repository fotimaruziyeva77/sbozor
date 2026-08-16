---
quick_id: 260816-5yz
phase: quick
plan: 260816-5yz
subsystem: frontend
tags: [ux, a11y, tri-state, empty-state, i18n, tdd, refactor, gate]
requirements: [KR-01, KR-02, KR-03, KR-04]
dependency_graph:
  requires:
    - "frontend/src/components/snapshots/schedule-card.tsx (04-xx — guard-clause etaloni: isPending -> isError -> data)"
    - "frontend/src/components/billing/charge-detail-dialog.tsx (06-xx — DIALOG ICHIDAGI tri-state etaloni)"
    - "frontend/src/components/ui/empty-state.tsx (01-xx — sarlavha + tavsif + ixtiyoriy action)"
    - "frontend/src/components/ui/skeleton.tsx (01-xx — konteyner darajasidagi role=status e'loni)"
    - "frontend/scripts/submit-gate.test.mjs (quick 260816-5ys — D-1 istisno reyestri)"
  provides:
    - "stall-dialog tahrir rejimi: yuklanish (skeleton + sr-only common.loading) va xato (loadFailedTitle/Body + common.retry -> detailQuery.refetch) holatlari KO'RINADI"
    - "stall-dialog: jim-disabled submit sharti butunlay yo'q — G-SUBMIT ning D-1 istisno ro'yxati BO'SH"
    - "schedule-dialog: `items.length === 0` va `target === null` ikki BOSHQA fakt bilan ajratildi (scheduleNotFound / scheduleNotFoundHint)"
    - "schedule-dialog: renderBody() guard zanjiri (5 qavatli ternary yo'q)"
    - "ikkala jadval holati EmptyState ustida, action'siz (§10.4 ning mexanik shakli)"
  affects:
    - "har uch locale (snapshots.scheduleNotFound* — 2 yangi kalit x 3 til)"
    - "04-UI-SPEC §10.4 — DL-1 ning nosozlik holati endi IKKI qatorli jadval"
    - "kelajakdagi dialoglar: `isEdit && <holat>` prefiksi enabled:false tuzog'ining nomlangan yechimi"
tech_stack:
  added: []
  patterns:
    - "renderBody(): ReactNode — KOMPONENT EMAS (hook yo'q), ya'ni hooklar shartsiz tepada qoladi, guardlar esa erta qaytadi"
    - "`isEdit &&` prefiksi: enabled:false so'rov TanStack'da abadiy isPending — rejimga bog'lanmagan guard boshqa oqimni o'ldiradi"
    - "EmptyState + className=\"py-6\" — dialog ichidagi standart (py-12 twMerge bilan bosiladi)"
    - "xato bloki TARJIMA QILINGAN jumla chizadi, error.message O'QILMAYDI (T-02-99)"
    - "qarama-qarshi juft assert: bir matnni ikkinchisiga almashtirish IKKALA testni ham qizartiradi"
key_files:
  created: []
  modified:
    - frontend/src/components/stalls/stall-dialog.tsx
    - frontend/src/components/stalls/stall-dialog.test.tsx
    - frontend/src/components/snapshots/schedule-dialog.tsx
    - frontend/src/components/snapshots/schedule-dialog.test.tsx
    - frontend/scripts/submit-gate.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - .planning/phases/04-snapshot-pipeline/04-UI-SPEC.md
decisions:
  - "stall-dialog.test.tsx YANGI EMAS, MAVJUD edi (260816-5ys yaratgan) — reja uni yangi deb hisoblagan; eski «tahrir rejimi (chegara)» testi (toBeDisabled da'vosi) yangi tri-state testlariga ALMASHTIRILDI, chunki u bevosita zid edi"
  - "submit-gate.test.mjs ning D-1 istisnosi O'CHIRILDI: darvozaning o'zi «ESKIRGAN ISTISNO» deb qizardi — ro'yxatni o'z-o'zini tozalashga majbur qilish mexanizmi ishladi"
  - "D1_EXCEPTIONS endi BO'SH massiv; darvoza bo'shab qolmadi — MIN_SUBMIT_BUTTONS quyi chegarasi va ijobiy/salbiy meta-nazoratlar detektorni o'lchashda davom etadi, D-1 esa endi ISTISNOSIZ butun src/ ga qo'llanadi"
  - "T7 (muvaffaqiyat nazorati) findBy EMAS, waitFor bilan yozildi: urug'lantirish maydon MONTAJIDAN KEYINGI effektda bo'ladi, ya'ni maydonning mavjudligi hali qiymati degani emas (RED paytida aynan shu sababdan qizargan edi)"
  - "Task 2 da kalitlar TESTDAN OLDIN qo'shildi: test qiymatlarni messages/uz-Latn.json dan o'qiydi (literal TAQIQ), ya'ni kalitsiz test kompilyatsiya ham qilinmasdi — RED da'vo hamon KOMPONENT xulqiga tegishli"
  - "gate:fast ning BACKEND yarmi (npm run test:fast, Docker) YURGIZILMADI — o'zgarishlar sof frontend; frontend yarmi to'liq yashil (913 vitest + barcha node script darvozalari)"
metrics:
  duration_min: 40
  tasks: 2
  files: 9
  commits: 2
  completed: 2026-08-16
---

# Quick 260816-5yz: tri-state va schedule-dialog tozalash Summary

Kod-review'ning to'rt CONFIRMED topilmasi yopildi: rasta dialogi tahrir
rejimida so'rov holatini (yuklanmoqda / xato + qayta urinish) endi
KO'RSATADI, jadval dialogi esa ro'yxat bo'sh bo'lmaganda «jadval
yozilmagan» degan faktik yolg'onni aytmaydi — ikkala dialog ham 5 qavatli
ternary o'rniga guard zanjiri ustida va ikkala holat matni `EmptyState`
bilan, `action` siz chiziladi.

## Nima qilindi

| # | Topilma | Natija | Commit |
|---|---------|--------|--------|
| 1 | **KR-01** `stall-dialog.tsx` — tahrir rejimida `detailQuery` faqat `.data` sifatida o'qilardi: sekin yoki yiqilgan so'rovda BO'SH FORMA + jim o'chirilgan «Saqlash» | `renderBody()` guard zanjiri: `isEdit && isPending` -> `role="status"` + `aria-busy` + `sr-only` `common.loading` + `Skeleton h-64`; `isEdit && isError` -> `role="alert"` + `errors.loadFailedTitle/Body` + `common.retry` (`detailQuery.refetch()`); aks holda forma. `disabled` ifodasidan `(mode === "edit" && detail === undefined)` OLIB TASHLANDI | `067a4dd` |
| 2 | **KR-02/03/04** `schedule-dialog.tsx` | Ikki holat ajratildi (`items.length === 0` -> `scheduleMissing`, `target === null` -> yangi `scheduleNotFound`); ternary -> `renderBody()`; ikkala holat `EmptyState` (`py-6`, `action` siz); UI-SPEC §10.4 yangilandi | `8c142a3` |

## RED chiqishi — MAJBURIY qayd

### Task 1 (KR-01) — 3 test qizil, 6 yashil

`npx vitest run src/components/stalls/stall-dialog.test.tsx` (implementatsiyadan OLDIN):

```
❯ src/components/stalls/stall-dialog.test.tsx (9 tests | 3 failed)

FAIL > tahrir rejimi: batafsil so'rov ketayotganda
     > ⛔ yuklanish holati KO'RINADI va forma CHIZILMAYDI
  TestingLibraryElementError: Unable to find role="status"

FAIL > tahrir rejimi: batafsil so'rov yiqilganda
     > ⛔ xato SABAB bilan ko'rinadi, xom matn EKRANGA CHIQMAYDI
  TestingLibraryElementError: Unable to find an element with the text:
  Ma'lumot yuklanmadi

FAIL > tahrir rejimi: batafsil so'rov yiqilganda
     > ⛔ «Qayta urinish» so'rovni QAYTA yuboradi
  TestingLibraryElementError: Unable to find an element with the text:
  Ma'lumot yuklanmadi

Tests  3 failed | 6 passed (9)
```

Ikkala qizil da'vo ham AYNAN kutilgan sababdan: bugungi dialog o'sha
holatlarda bo'sh formani chizardi, ya'ni na `role="status"` konteyneri,
na xato sarlavhasi mavjud edi. `vitest` chiqishidagi DOM dumpi buni
bevosita ko'rsatdi — `<button disabled type="submit">Saqlash</button>`
to'liq forma bilan birga render bo'lgan edi.

### ⚠ T7 (muvaffaqiyat nazorati) — BIRINCHI yozilishida qizardi, LEKIN boshqa sababdan

Birinchi variant `const code = await screen.findByLabelText(CODE_LABEL);
expect(code).toHaveValue("17")` edi va u `Expected the element to have
value: 17 / Received: (bo'sh)` bilan qizardi. Bu **mahsulot nuqsoni
EMAS**, testning noto'g'ri kutilmasi: forma urug'lantirilishi maydon
MONTAJ QILINGANDAN keyingi effektda bo'ladi (`seededFor` naqshi), ya'ni
`findBy` maydonni qiymat yozilishidan OLDIN topadi. Assert `waitFor` ga
o'tkazildi va shundan keyin RED o'lchovida yashil bo'ldi (yuqoridagi
chiqish aynan tuzatilgan variantniki).

### ⛔ T8 (`create` nazorati) — RED paytida YASHIL boshladi

Reja bu savolni aniq so'ragan. Javob: **T8 RED paytida ham yashil edi va
implementatsiyadan keyin ham yashil qoldi.** Sabab mexanik: guard hali
yo'q edi, ya'ni `create` oqimi hech qachon skeletonga tushmasdi. Bu
**tuzoqning REAL emasligini isbotlamaydi** — u faqat tuzoq GUARD BILAN
BIRGA tug'ilishini ko'rsatadi. Testning qiymati oldinga qaragan: `isEdit
&&` prefiksi olib tashlansa, `useStallQuery(null)` -> `enabled: false` ->
TanStack'ning abadiy `isPending: true` i `create` rejimini mangu
skeletonga qamaydi va AYNAN T8 qizaradi. Prefikssiz variant ataylab
sinab ko'rilmadi (sabotaj o'lchovi bu rejaning qamrovida yo'q edi), lekin
guardning o'zi `isPending` ga tayangani uchun bog'liqlik zanjiri
to'g'ridan-to'g'ri.

### Task 2 (KR-02) — 2 test qizil, 7 yashil

`npx vitest run src/components/snapshots/schedule-dialog.test.tsx`
(implementatsiyadan OLDIN, kalitlar allaqachon qo'shilgan holda):

```
❯ src/components/snapshots/schedule-dialog.test.tsx (9 tests | 2 failed)

FAIL > DL-1: ro'yxat bo'sh emas, lekin so'ralgan profil topilmaganda
     > ⛔ «jadval yozilmagan» DEYILMAYDI — boshqa fakt aytiladi
  TestingLibraryElementError: Unable to find an element with the text:
  So'ralgan jadval topilmadi

FAIL > DL-1: ro'yxat bo'sh emas, lekin so'ralgan profil topilmaganda
     > ⛔ bu holatda ham tugma ham, havola ham YO'Q (§10.4)
  TestingLibraryElementError: Unable to find an element with the text:
  So'ralgan jadval topilmadi

Tests  2 failed | 7 passed (9)
```

**T6 (bo'sh ro'yxat nazorati) boshidanoq yashil** — kutilganidek: eski
xulq o'sha holatda ROST edi va u o'zgarmasligi kerak. Mavjud olti test
ham RED paytida ham, GREEN paytida ham yashil qoldi, ya'ni KR-03/KR-04
haqiqatan REFAKTORING bo'ldi.

## `EmptyState` ga o'tishning vizual ta'siri — `py-6` YETARLI

Reja bu savolni ham aniq so'ragan.

| O'lchov | Ilgari (qo'lda `div/p/p`) | Endi (`EmptyState className="py-6"`) |
|---------|---------------------------|--------------------------------------|
| Vertikal padding | 0 (`gap-2` dan boshqa hech nima) | **24 px** (`py-6`) |
| Gorizontal padding | 0 | 16 px (`px-4`) |
| Tekislash | chapga | **markazga** (`items-center text-center`) |
| Sarlavha | `text-sm font-semibold` | `text-lg font-semibold` |
| Izoh | `text-sm text-text-muted` | `text-sm text-text-muted max-w-prose` |

`py-12` bosilishi **mexanik tasdiqlandi**, uslub taxmini emas:

```
twMerge("flex flex-col items-center gap-2 px-4 py-12 text-center", "py-6")
  -> "flex flex-col items-center gap-2 px-4 text-center py-6"
```

`py-12` chiqishda UMUMAN yo'q. `size="md"` dialogda 48 px vertikal
bo'shliq sarlavha bilan `Dialog.Footer` orasida ikki barobar ortiqcha
havo berardi; 24 px izohni dialog markazida ushlab turadi va sarlavhaning
`text-lg` ga kattalashuvi holatni dialogning ASOSIY mazmuni sifatida
o'qitadi (dokstringning uchinchi bandi aynan shuni talab qiladi — bu
chekka xabar emas).

## Deviations from Plan

### 1. [Rule 3 — bloklovchi nomuvofiqlik] `stall-dialog.test.tsx` MAVJUD edi

- **Topildi:** Task 1 boshida.
- **Muammo:** reja faylni `(YANGI)` deb belgilagan, lekin uni qo'shni
  quick task `260816-5ys` allaqachon yaratgan (9 test emas, 4 test bilan)
  va uning **oxirgi testi bevosita ZID** edi: «batafsil javob KELMAGUNCHA
  saqlash tugmasi YOPIQ qoladi» + `expect(...).toBeDisabled()`.
- **Yechim:** fayl ustiga yozilmadi. Mavjud uch test (F-1 submit
  validatsiyasi) O'ZGARISHSIZ saqlandi; zid bo'lgan «tahrir rejimi
  (chegara)» describe'i to'rt yangi tri-state testiga almashtirildi va
  fayl sarlavhasidagi izoh chegara YOPILGANINI yozadi.
- **Fayllar:** `frontend/src/components/stalls/stall-dialog.test.tsx`
- **Commit:** `067a4dd`

### 2. [Rule 3 — bloklovchi darvoza] `submit-gate.test.mjs` istisnosi o'chirildi

- **Topildi:** Task 1 ning GREEN bosqichidan keyin.
- **Muammo:** `disabled` disjunkti olib tashlangach `stall-dialog.tsx`
  ning qoldig'i bo'shab qoldi va darvoza ATAYIN qizardi:
  `ESKIRGAN ISTISNO: components/stalls/stall-dialog.tsx endi toza —
  yozuvni O'CHIRING. Yopilish tetigi edi: 260816-5yz`.
- **Yechim:** `D1_EXCEPTIONS` yozuvi o'chirildi, o'rniga nima uchun ro'yxat
  bo'sh ekanini va bo'sh ro'yxat darvozani bo'shatmasligini tushuntiruvchi
  izoh yozildi. Fayl sarlavhasidagi `stall-dialog.test.tsx` haqidagi jumla
  ham yangi haqiqatga moslandi.
- **Fayllar:** `frontend/scripts/submit-gate.test.mjs`
- **Commit:** `067a4dd`

### 3. [Reja tartibidan chetlanish] Task 2 da kalitlar testdan OLDIN qo'shildi

- **Sabab:** test matnlarni `messages/uz-Latn.json` dan O'QIYDI (literal
  yozish TAQIQ, reja shuni talab qiladi). Kalitsiz `messages.snapshots.
  scheduleNotFound` `undefined` bo'lardi — `tsc` qizarardi va
  `findByText(undefined)` RED ni **noto'g'ri sababdan** bergan bo'lardi.
- **Ta'sir:** RED da'vosining o'zi o'zgarmadi — u hamon KOMPONENT
  xulqiga tegishli (dialog o'sha holatda `scheduleMissing` chizardi).
- **Fayllar:** `frontend/messages/uz-Latn.json`, `ru.json`, `uz-Cyrl.json`

### 4. [Qamrov qarori] `gate:fast` ning backend yarmi yurgizilmadi

- **Sabab:** `npm run gate:fast` = `npm run test:fast && npm --prefix
  frontend test`, birinchi yarmi Docker konteynerida pytest yurgizadi.
  Bu vazifada birorta backend fayli tegilmagan, xostdagi `C:` diski esa
  91 % to'la (STATE.md dagi ochiq xavf).
- **Bajarilgani:** ikkinchi yarmi TO'LIQ — `npm --prefix frontend test`
  (barcha `scripts/*.test.mjs` darvozalari + **913 vitest testi**,
  71 fayl) yashil.

## Kuzatilgan (tuzatilmagan) — QAMROVDAN TASHQARI

⚠ **`case-list.test.tsx:209` FLAKE.** To'liq vitest to'plamining birinchi
yurgizilishida bitta test yiqildi (`reconciliation/case-list.test.tsx`,
`const { container } = await renderList()` qatori). Keyingi IKKI to'liq
yurgizishda 910/910 va 913/913 yashil. Bu 7-fazaning fayli, bu vazifaning
o'zgarishlariga umuman bog'liq emas (rasta va jadval dialoglari uni
import qilmaydi) va **ataylab tuzatilmadi** — qamrov chegarasi.

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npx vitest run src/components/stalls/stall-dialog.test.tsx` | **9/9 yashil** |
| 2 | `npx vitest run src/components/snapshots/schedule-dialog.test.tsx src/components/snapshots/schedule-card.test.tsx` | **24/24 yashil** (9 dialog + 15 karta) |
| 3 | `npm run i18n:check` | `drift yo'q` · **1218 kalit × 3 til** — kalit va ICU parity to'liq |
| 4 | `node --test scripts/snapshot-copy.test.mjs scripts/glossary.test.mjs` | **22/22 yashil** (G-1 «slot», G-10 «kadrni o'chirish», G7-9 glossariy) |
| 5 | `node --test scripts/submit-gate.test.mjs` | **11/11 yashil** (istisno ro'yxati bo'sh, D-1 istisnosiz qo'llanadi) |
| 6 | `npm run lint` | toza |
| 7 | `npm run typecheck` | toza |
| 8 | `npm test` (frontend to'liq) | **71 fayl / 913 test yashil** + barcha node darvozalari |
| 9 | `git diff HEAD~2 HEAD -- frontend/package.json frontend/package-lock.json` | **BO'SH** — yangi bog'liqlik yo'q |
| 10 | `git log --oneline -2` | AYNAN ikki commit, har task uchun bittadan |

## Success Criteria

- [x] Tahrir rejimidagi rasta dialogi so'rov ketayotganda va yiqilganda jim turmaydi — holat ko'rinadi, sabab aytiladi, qayta urinish beriladi
- [x] `create` oqimi regressiyasiz (`enabled: false` -> `isPending: true` tuzog'i test bilan qulflangan)
- [x] Jadval dialogi ro'yxat bo'sh bo'lmaganda «jadval yozilmagan» demaydi
- [x] `ScheduleDialog` tanasi guard zanjiri; xulq o'zgarmagan (mavjud olti test yashil)
- [x] Ikkala holat matni `EmptyState` bilan, `action` siz; «nega CTA yo'q» asosnomasi kodda saqlangan (ikkala funksiya ustidagi umumiy dokstring)
- [x] Uchala locale mos; yangi kalitlar copy darvozalaridan o'tgan
- [x] Ikki atomik commit; yangi bog'liqlik yo'q

## Known Stubs

Yo'q — bu vazifa yangi ma'lumot yo'li ochmadi, mavjud so'rov holatlarini
ko'rinadigan qildi.

## Self-Check: PASSED

Uchala tekshiruv mexanik bajarildi:

- **Fayllar (9/9 FOUND):** `stall-dialog.tsx`, `stall-dialog.test.tsx`,
  `schedule-dialog.tsx`, `schedule-dialog.test.tsx`,
  `submit-gate.test.mjs`, `uz-Latn.json`, `ru.json`, `uz-Cyrl.json`,
  `04-UI-SPEC.md`.
- **Commitlar (2/2 FOUND):** `067a4dd`, `8c142a3`.
- **`must_haves` naqshlari:** `detailQuery\.refetch` ✓ va
  `errors\.loadFailedBody` ✓ (`stall-dialog.tsx`); `renderBody` ✓,
  `EmptyState` ✓ va `scheduleNotFound` ✓ (`schedule-dialog.tsx`);
  `scheduleNotFound` ✓ (`uz-Latn.json`); test fayli 120 dan ancha uzun
  (468 qator).
- **O'chirilgan fayl YO'Q:** `git diff --diff-filter=D HEAD~2 HEAD` bo'sh.
