---
phase: quick
plan: 260816-5mn
subsystem: ui
tags: [next-intl, react, tanstack-query, vitest, radix-dialog, pytest, billing, rls]

requires:
  - phase: "02 (bozor sozlash ustasi)"
    provides: "`POST /markets/{id}/activate`, `setup-status`, `fallbackStep()`, `ActivationPanel`"
  - phase: "06 (billing)"
    provides: "`billing_close` / `day_close` va ularning `WHERE is_active` filtri"
provides:
  - "7/7 bajarilgan qoralama bozor tanlanganda BEVOSITA faollashtirish qadamiga (`?step=7`) qo'nadi"
  - "Qo'nish qoidasi kod bazasida AYNAN BITTA joyda — `wizard-steps.ts::fallbackStep()`"
  - "Faollashtirishdan oldingi tasdiq dialogi: qaytarib bo'lmaslik + hisob qachondan boshlanishi"
  - "«Faollashgach billing kunlik hisob yozadi» zanjirining birinchi mexanik o'lchovi"
affects: [08-hisobotlar-mustahkamlash-va-ishga-tushirish, dashboard-holat-kartasi-№H, UI-polish]

tech-stack:
  added: []
  patterns:
    - "Navigatsiya qarori QAYTA HISOBLANMAYDI — domen moduli (`wizard-steps.ts`) yagona hakam; so'rov moduli faqat tarmoqni bajaradi"
    - "Qaytarib bo'lmaydigan amal oldidan ConfirmDialog 1-daraja + `confirmVariant=\"default\"` (qizil rang YO'QOTISH uchun ajratilgan)"
    - "Reyestr bandi ENDPOINT bilan emas, OQIBAT bilan yopiladi: allaqachon o'lchangan da'vo takrorlanmaydi"

key-files:
  created:
    - frontend/src/components/wizard/activation-panel.test.tsx
  modified:
    - frontend/src/lib/market-queries.ts
    - frontend/src/lib/market-queries.test.tsx
    - frontend/src/components/auth/market-picker.test.tsx
    - frontend/src/components/wizard/activation-panel.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - tests/integration/test_billing_close.py
    - KAMCHILIKLAR-REESTRI.md

key-decisions:
  - "Qo'nish qoidasining ikkinchi nusxasi TUZATILMADI, YO'Q QILINDI — `market-queries.ts` endi `fallbackStep()` ni import qiladi; nusxani «to'g'rilash» uchinchi nusxaga yo'l ochardi"
  - "`lib/` -> `components/wizard/wizard-steps` import yo'nalishi ONGLI: `wizard-steps.ts` sof domen moduli (JSX yo'q, `\"use client\"` yo'q, yagona importi `api-types`), ya'ni sikl yo'q"
  - "`FIRST_WIZARD_STEP` ning MA'NOSI toraydi: endi FAQAT «javob umuman kelmadi» holati; «javob keldi, `blocking` bo'sh» ma'nosi `fallbackStep()` ga o'tdi"
  - "Tasdiq dialogi 1-daraja (nom yozdirish YO'Q): primitivning docstringi 2-darajani ikki holatga ajratgan va faollashtirish ular orasida yo'q; panelning o'zi allaqachon oxirgi ko'z yugurtirish ro'yxati"
  - "`confirmVariant=\"default\"` — qizil YO'QOTISH signali, faollashtirish esa ustaning MAQSADI; qaytarib bo'lmaslik RANG bilan emas, TAVSIF matni bilan aytiladi"
  - "Dialog matni YANGI SIYOSAT IXTIRO QILMAYDI — ikkala jumlasi ham koddan o'qilgan (`markets.py:500-504` va `retention.py:162-164` + `billing_close.py:23`)"
  - "3-task ENDPOINTNI emas, OQIBATNI o'lchaydi: `POST /activate` uch da'vo bilan allaqachon qamralgan, o'lchanmagani billing zanjiri edi"
  - "Backend yuzasi TEGILMADI: yangi endpoint ham, yangi migratsiya ham, yangi npm/pip bog'liqligi ham yo'q"

patterns-established:
  - "Qadam raqami testda SONLI LITERAL bilan emas, KONSTANTA bilan kutiladi (`ACTIVATION_STEP` / `FIRST_WIZARD_STEP`) — literal konstanta o'zgarganda jimgina yolg'on bo'lardi"
  - "Tasdiq dialogi testida `within(dialog)`: tasdiq tugmasi O'Z FE'LI bilan yorliqlanadi, ya'ni panel tugmasi bilan bir xil matnga ega"
  - "Qoralama/faol juftligi BITTA testda: holatni o'lchash -> holatni o'zgartirish -> qayta o'lchash (`test_a_run_before_day_close_...` naqshi)"

requirements-completed: [TOPILMA-A, TOPILMA-B, MARKET-01]

duration: 45min
completed: 2026-08-16
---

# Quick 260816-5mn: Topilma №B + №A — bozorni faollashtirish yo'li Summary

**Qoralama bozorni jonlantirish yo'li uchidan-uchiga ochildi: 7/7 bajarilgan bozor tanlanganda bevosita faollashtirish qadamiga qo'nadi, tugma so'rov o'rniga qaytarib bo'lmaslikni aytadigan tasdiq dialogini ochadi, va «faollashgach billing kunlik hisob yozadi» zanjiri birinchi marta mexanik ravishda o'lchandi.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-16T04:15Z (taxminiy)
- **Completed:** 2026-08-16T05:00Z (taxminiy)
- **Tasks:** 3/3
- **Files modified:** 9 (8 kod/katalog + 1 reyestr)

## Accomplishments

- **№A yopildi ILDIZIDAN:** «qaysi qadamga qo'namiz?» savoliga kod bazasi ikki marta javob berardi va javoblar ajralib ketgandi. Nusxa yo'q qilindi — `fetchFirstIncompleteStep()` endi `fallbackStep()` ni chaqiradi. 7/7 qoralama `?step=7` ga, chala qoralama hamon birinchi to'siqqa, faol bozor dashboardga.
- **№B yopildi:** faollashtirish tugmasi endi bevosita so'rov yubormaydi — tasdiq dialogini ochadi va u ikki faktni aytadi (amal qaytarib bo'lmaydi; hisob faollashtirish KUNIDAN boshlanadi). Chala bozorda dialog OCHILMAYDI — UI-SPEC §6.6 ning mavjud yo'li tegilmadi.
- **Reyestrning o'lchanmagan bandi yopildi:** `test_a_draft_market_is_skipped_and_activation_starts_the_daily_charge` qoralama/faol juftligini bitta testda o'lchaydi va sabotaj bilan tasdiqlandi.
- **Backend ishi NOL:** endpoint allaqachon bor edi va uning uchala bandi (draft->active, takror 409, audit) allaqachon o'lchangan — ikkinchi nusxa yozilmadi.

## Task Commits

1. **Task 1: №A — qo'nish qoidasi bitta manbaga qaytarildi** — `b90bb09` (fix)
2. **Task 2: №B — faollashtirishdan oldin tasdiq dialogi** — `9e52fd5` (feat)
3. **Task 3: ZANJIR — qoralama hisob yozmaydi, faollashgach yozadi** — `96171c1` (test)

## RED chiqishlari (test AVVAL qizarganining dalili)

### Task 1 — RED

```
FAIL  src/lib/market-queries.test.tsx > fetchFirstIncompleteStep — qo'nish qadami (Topilma №A)
      > 7/7 bajarilgan qoralama FAOLLASHTIRISH qadamiga qo'nadi
AssertionError: expected 1 to be 7 // Object.is equality

FAIL  src/components/auth/market-picker.test.tsx > MarketPicker — 7/7 qoralama (Topilma №A)
      > to'liq qoralama FAOLLASHTIRISH qadamiga marshrutlanadi
AssertionError: expected "vi.fn()" to be called with arguments: [ '/markets/setup?step=7' ]

Test Files  2 failed (2)
     Tests  2 failed | 29 passed (31)
```

**GREEN:** `Test Files 2 passed (2) · Tests 31 passed (31)`.

⚠ Qolgan ikki shox (`min(step)` va tarmoq xatosi) RED bosqichidayoq YASHIL edi va bu KUTILGAN: ular mavjud xulqning regressiya qulfi, tuzatilayotgan nuqson emas. Ularning yashilligi tuzatish eski xulqni buzmaganini isbotlaydi.

### Task 2 — RED

```
×  T1: tugma dialogni ochadi va so'rov TASDIQSIZ ketmaydi
×  T2: tasdiqdan keyin `POST /activate` AYNAN BIR MARTA ketadi
×  T3: [Bekor qilish] bosilsa so'rov UMUMAN ketmaydi
TestingLibraryElementError: Unable to find role="dialog"

Test Files  1 failed (1)
     Tests  3 failed | 1 passed (4)
```

**GREEN:** `Test Files 1 passed (1) · Tests 4 passed (4)`.

⚠ T4 (chala bozor — nazorat) RED bosqichida ham yashil edi: §6.6 ning mavjud yo'li ishlayotganini bildiradi va tuzatish uni buzmaganini keyin qulflaydi.

### Task 3 — RED

`is_active = false` flipi VAQTINCHA olib tashlanib yugurtirildi (ya'ni bozor FAOL qoldi):

```
tests/integration/test_billing_close.py:1102: AssertionError
E   assert {UUID('...'): (15000, 15000, ...), UUID('...'): (15000, 15000, ...)} == {}
E   Left contains 2 more items

[info] billing_close_done  business_date=2026-08-14 charged=2 errors=0 markets=2 no_slot_rows=0
FAILED tests/integration/test_billing_close.py::test_a_draft_market_is_skipped_and_activation_starts_the_daily_charge
```

**GREEN (flip qaytarilgach):** butun fayl — `9 passed` (mavjud 8 + yangi 1).

## Sabotaj o'lchovi (Task 3)

`services/core-api/app/jobs/retention.py:163` dagi `_ACTIVE_MARKETS` so'rovidan `WHERE is_active` OLIB TASHLANDI:

```python
# sabotaj
"SELECT market_id FROM auth_list_markets_full() ORDER BY market_id"
```

Natija — testning BIRINCHI yarmi qizardi, va AYNAN o'zining xabari bilan:

```
E   AssertionError: QORALAMA bozorga kunlik hisob yozildi — `WHERE is_active` filtri ishlamadi
E   assert {UUID('6a12e851-...'): (15000, 15000, ...),
E           UUID('c4bd6ac8-...'): (15000, 15000, ...)} == {}
tests/integration/test_billing_close.py:1102: AssertionError
FAILED ...::test_a_draft_market_is_skipped_and_activation_starts_the_daily_charge
```

Sabotaj qaytarildi; `git diff --stat services/core-api/app/jobs/retention.py` BO'SH (mahsulot kodi o'zgarmagan).

⚠ Ya'ni da'vo BO'SH EMAS: test filtrni haqiqatan o'lchaydi, «hech nima yozilmadi» holatini tasodifan kuzatmaydi.

## Biznes-savolning javobi va uning kod dalili

**Savol:** faollashgach billing qachondan hisob yozadi — `operating_since` dan retroaktivmi yoki faollashtirish kunidanmi?

**Javob: faollashtirish kunidan oldinga qarab. Retroaktiv hisob YO'Q.** Dalil zanjiri (dialog matni AYNAN shunga tayanadi va bir kalima ham ko'p aytmaydi):

1. `services/core-api/app/jobs/retention.py:162-164` — `_ACTIVE_MARKETS` so'rovi `WHERE is_active` va u **job yugurgan LAHZADA** baholanadi, bozorning tarixiga qaramaydi.
2. `billing_close.py:272` va `day_close.py:69` — ikkalasi ham AYNAN shu ro'yxatdan yuradi, ya'ni qoralama bozor uchun na slot materializatsiyasi, na hisob yoziladi.
3. `billing_close.py:23` — `BILLING_CLOSE_CRON = "10 4 * * *"` va qobiq KECHAGI kunni yopadi; o'tmishdagi boshqa kunni yopadigan mahsulot yo'li YO'Q (`business_date` argument sifatida faqat testda beriladi).
4. Demak faollashtirish kuni — birinchi yopiladigan kun (ertasi 04:10 da); undan oldingi kunlar hech qachon yopilmagan va yopilmaydi.
5. `operating_since` backfill'ni TETIKLAMAYDI — u faqat tarif/toifa davrlarining `min_valid_from` ini beradi (`markets.py:317`).

Qaytarib bo'lmaslikning dalili: `market_deactivate()` funksiyasi ATAYIN yaratilmagan va faol bozorni o'chirish `market_delete_draft()` darvozasida rad etiladi (`markets.py:500-504`).

## Files Created/Modified

- `frontend/src/lib/market-queries.ts` — `fetchFirstIncompleteStep` endi `fallbackStep()` ni chaqiradi (`Math.min` hisobi o'chirildi); `FIRST_WIZARD_STEP` docstringi torroq ma'no bilan yangilandi; import yo'nalishi qarori izohda
- `frontend/src/lib/market-queries.test.tsx` — uchala shox + «uch qadam bir-biridan farq qiladi» nazorati
- `frontend/src/components/auth/market-picker.test.tsx` — 7/7 qoralama `?step=7` ga; faol bozorda `setup-status` YO'L bo'yicha so'ralmasligi
- `frontend/src/components/wizard/activation-panel.tsx` — `confirmOpen` holati, `onActivateClick()` ikki yo'li, `ConfirmDialog` (uchta parametr qarori izohda)
- `frontend/src/components/wizard/activation-panel.test.tsx` — YANGI, to'rt mustaqil da'vo
- `frontend/messages/uz-Latn.json`, `frontend/messages/ru.json` — `wizard.activateConfirmTitle` va `wizard.activateConfirmBody` (QO'LDA)
- `frontend/messages/uz-Cyrl.json` — `npm run i18n:gen` HOSILASI (qo'lda tahrirlanmadi)
- `tests/integration/test_billing_close.py` — 9-bo'lim: qoralama/faol juftligi
- `KAMCHILIKLAR-REESTRI.md` — 0-bo'limga №A/№B commit hashlari bilan, 1-bo'limda ✅, 7-bo'limning 1-bandi bajarilgan

## Nima ATAYIN QILINMADI

1. **№H — dashboard holat kartasi** («Qoralama — ishga tushirish uchun …» + hisoblagichlar). Reyestrning **3-bo'limida OCHIQ QOLDI** va bu ataylab: u alohida band, alohida ekran va alohida qamrov. Uni bu yerda bajarish reyestrning ikki bandini chalkashtirardi va bloker juftlikning qamrovini yoyib yubordi.
2. **Yorliq matni «Bozorni faollashtirish» (`wizard.activate`) O'ZGARTIRILMADI.** U uchala tilda mavjud, to'g'ri, va reyestrning qabul mezoni yorliq so'zlashuvi haqida emas. Sinonimga almashtirish uch faylda uch marta churn bo'lardi va tasdiq dialogining tugmasi ham AYNAN shu fe'lni qayta ishlatadi.
3. **Backend endpointi va uning mavjud uchta testi TEGILMADI** (`test_wizard_flow.py:354-366`, `:875-885`, `:1106-1132`) — ikkinchi nusxa yozish o'lchanmagan bandni o'lchangani bilan almashtirardi.
4. **`wizard-steps.ts` va `market-picker.tsx` ning MAHSULOT kodi tegilmadi** — ikkalasi ham allaqachon to'g'ri edi; ularga faqat regressiya qulflari qo'shildi.

## Decisions Made

Yuqoridagi frontmatter `key-decisions` ga qarang. Eng muhimi: **nusxa tuzatilmadi, YO'Q QILINDI.** `Math.min` shoxini «to'g'rilash» bugungi nuqsonni yopib, uchinchi nusxaga yo'l ochardi; import esa sikl hosil qilmaydi, chunki `wizard-steps.ts` sof domen moduli.

## Deviations from Plan

### 1. [Rule 3 - Blocking] Test fixture'lariga aniq tip berildi

- **Found during:** Task 2 (typecheck)
- **Issue:** `BLOCKED_STATUS` `typeof READY_STATUS` dan hosila edi va `blocking: []` ni `never[]` deb chiqarardi — `tsc` `TS2345` bilan yiqildi.
- **Fix:** `READY_STATUS`/`BLOCKED_STATUS` va ikkala yordamchi `SetupStatusResponse` tipiga langarlandi (mahsulot sxemasidan hosila — qo'lda yozilgan shakl EMAS).
- **Files modified:** `frontend/src/components/wizard/activation-panel.test.tsx`
- **Verification:** `npm run typecheck` yashil
- **Committed in:** `9e52fd5`

### 2. [Rule 3 - Blocking] `mockSelectMarket` yordamchisining tipi kengaytirildi

- **Found during:** Task 1
- **Issue:** Mavjud yordamchi `setupStatus` uchun faqat `{ blocking: { step: number }[] }` ni qabul qilardi; yangi test `can_activate` ni ham beradi va TS ortiqcha maydon tekshiruvida yiqilardi.
- **Fix:** `can_activate?: boolean` ixtiyoriy maydon sifatida qo'shildi (mavjud chaqiruvlar tegilmadi).
- **Files modified:** `frontend/src/components/auth/market-picker.test.tsx`
- **Committed in:** `b90bb09`

### 3. [Qaror] `KAMCHILIKLAR-REESTRI.md` yangilandi, LEKIN COMMIT QILINMADI

- **Found during:** Task 3
- **Issue:** Fayl repozitoriyada UMUMAN kuzatilmaydi (`git log --all -- KAMCHILIKLAR-REESTRI.md` bo'sh) va `.gitignore` da ham yo'q — ya'ni u boshqa ildiz hujjatlari (`TEST-REPORT.md`, `UI-UX-MASTERPLAN.md`) bilan bir sinfda, ataylab kuzatuvdan tashqarida saqlanadi. Oldingi quick vazifa (`260815-86p`) ham uni yangilagan, lekin commit qilmagan.
- **Fix:** Mazmun rejaga muvofiq yangilandi (0-bo'lim hashlari, 1-bo'limda ✅, 7-bo'limning 1-bandi), lekin `git add` QILINMADI — hujjat artefaktlari orkestratorning zimmasida (ijro cheklovi).
- **Impact:** Reyestr diskda to'liq va aniq; git tarixiga kirish qarori foydalanuvchi/orkestratorda qoladi.

---

**Total deviations:** 3 (2 × Rule 3 bloklovchi tip masalasi, 1 × kuzatilmaydigan hujjat qarori)
**Impact on plan:** Ikkalasi ham test qatlamida va tip xavfsizligi uchun zarur edi. Mahsulot yuzasiga ta'sir yo'q, qamrov kengaymadi.

## Issues Encountered

- Ijro davomida parallel agentlar boshqa quick vazifalarning docs commitlarini kiritdi (`9fe7ce4`, `64b490f`) va ular mening uch commitim orasiga tushdi. Zarar yo'q: fayl to'qnashuvi bo'lmadi, uchala commit ham atomik va faqat o'z fayllarini qamraydi.

## Verification

| Darvoza | Natija |
|---|---|
| `npx vitest run src/lib/market-queries.test.tsx src/components/auth/market-picker.test.tsx` | 31 passed |
| `npx vitest run src/components/wizard/activation-panel.test.tsx` | 4 passed |
| `cd frontend && npx vitest run` (to'liq) | 67 fayl / 888 test passed |
| `cd frontend && npm run typecheck` | yashil |
| `cd frontend && npm run lint` | yashil |
| `cd frontend && npm run i18n:check` | `1216 kalit × 3 til — kalit va ICU parity to'liq`, `drift yo'q` |
| `cd frontend && npm run test:unit` (skript darvozalari, glossariy) | 235 passed |
| `ruff check` + `ruff format --check` + `mypy` (o'zgargan test fayli) | yashil |
| `docker compose --profile test run --rm tests pytest tests/integration/test_billing_close.py -q` | 9 passed |
| `docker compose --profile test run --rm tests pytest test_billing_close.py test_wizard_flow.py -q` | 37 passed |
| `npm run gate:fast` | yashil (backend unit + frontend 888) |

`npm run gate` (to'liq, ~1400 s) ATAYIN yugurtirilmadi — reja uni bu quick vazifa uchun talab qilmaydi va o'zgarish yuzasi frontend + bitta integratsiya fayli bilan chegaralangan.

## Next Phase Readiness

- Bloker juftlik yopildi: qoralama holat endi butun direktor qatlamini qulflamaydi — admin bozorni mahsulot ichidan jonlantira oladi.
- **Keyingi navbat (reyestr 7-bo'lim, 2-band):** №J · №I · №L · №D · №C.
- **Ochiq qolgan qo'shni band:** №H (dashboard holat kartasi) — 3-bo'limda, ataylab.
- ⚠ Qo'lda tekshiruv (ixtiyoriy, bloklamaydi): qoralama bozor bilan tanlash -> faollashtirish qadami -> tugma -> dialog -> tasdiq -> dashboard.

## Self-Check: PASSED

- Da'vo qilingan 10 ta fayl diskda MAVJUD (11/11 `FOUND`, SUMMARY ning o'zi bilan birga).
- Uchala commit git tarixida MAVJUD: `b90bb09`, `9e52fd5`, `96171c1`.
- Rejaning mexanik darvozasi bajarildi: `grep -n "Math.min" frontend/src/lib/market-queries.ts` — BO'SH.
- `git diff --stat services/core-api/app/jobs/retention.py` — BO'SH (sabotaj to'liq qaytarilgan).

---
*Quick: 260816-5mn*
*Completed: 2026-08-16*
