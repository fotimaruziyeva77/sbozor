---
phase: 06-billing-va-kassir
plan: 10
subsystem: billing
tags: [fastapi, postgres, rls, rbac, tenancy, audit, blind-declaration, sabotage, openapi]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 01
    provides: "`sbozor_core.billing.variance()` — belgili, ikki tomonlama sof funksiya (`abs` u yerda ham yo'q); `money.assert_safe_soum()` manfiyni rad etadi"
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`Permission.SHIFT_MANAGE` va `REPORT_VIEW` taqsimoti (D-07); `SHIFT_ALREADY_OPEN` / `SHIFT_ALREADY_CLOSED` xato kodlari"
  - phase: 06-billing-va-kassir
    plan: 03
    provides: "`frontend/src/lib/shift-queries.ts` — `shiftCloseResponseSchema` (AYNAN to'rt kalit), `shiftOpenSchema`, `shiftReportRowSchema`"
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "`cashier_shifts`: `SHIFT_OPEN_INDEX` qisman UNIQUE, uch juftlangan `CHECK`, `shift_declaration_immutable()` qo'riqchisi (`23514`)"
  - phase: 06-billing-va-kassir
    plan: 08
    provides: "`schemas.py` ning «E'LON QILMASLIK» naqshi, `main.py` router konventsiyasi, `_report_day()` shakli, `test_no_matrix_route_returns_422` darvozasi"
  - phase: 06-billing-va-kassir
    plan: 09
    provides: "`payment_repo.shift_system_total()` — tizim summasining YAGONA manbai va uning HTTP-taqig'i; `CASHIER_ROUTES` matritsa shoxi"
provides:
  - "`services/core-api/app/repositories/shift_repo.py` — `open_shift()` (oldindan tekshiruvsiz + SAVEPOINT), `open_shift_for()`, `close_shift()` (BITTA `UPDATE`), `shift_report()` (variance + ikki agregat)"
  - "`services/core-api/app/api/v1/shifts.py` — to'rt marshrut, ikki imzo aliasi, 200/201/403/404/409/422 to'liq"
  - "`app/schemas.py` — `ShiftOpenResponse` / `ShiftCloseRequest` / `ShiftCloseResponse` / `ShiftReportRow` / `ShiftReportResponse`"
  - "`PARAM_FILLERS[\"shift_id\"]` + ikki `BODY_FILLERS` yozuvi; `CASHIER_ROUTES` docstringida R-5 ⚠ bandi"
  - "`tests/integration/test_shifts_api.py` — 21 test; SC#5(d) IKKI TOMONLAMA, G-7 backend yarmi, D-32 OpenAPI hosila skani"
  - "O'LCHANGAN SABOTAJ: S-1 IKKALA QATLAMNI ham QIZARTIRDI · S-2 kamomad da'vosini QIZARTIRDI (storno testi to'g'ri yashil qoldi)"
affects: [06-11, 06-12, 06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Repository qatori (`ShiftRow`) va HTTP javobi (`ShiftCloseResponse`) ATAYIN har xil: farq IKKALA modulning docstringida yozib qo'yildi, chunki `response_model=ShiftRow` — D-25 ni buzadigan BIR SATRLIK o'zgarish"
    - "«E'lon qilmaslik» da'vosi IKKI MUSTAQIL qatlamda o'lchanadi: javob BAYTLARI (to'plam tengligi) va KONTRAKT (`app.openapi()` dan REKURSIV hosila skan). Ikkalasi boshqa-boshqa yo'llardan buziladi"
    - "OpenAPI skani `$ref` lar bo'ylab REKURSIV: sayoz skan ichma-ich modeldagi (`ShiftReportRow`) maydonni ko'rmasdi va «variance qaytarilmayapti» degan YOLG'ON yashil berardi"
    - "Sxema qo'riqchisi ilova shaklini BELGILAYDI: `shift_declaration_immutable()` ikkinchi `UPDATE` ni rad etgani uchun yopish AYNAN BITTA bayonot bo'lishi SHART — bu tanlov emas, yagona ifodalanadigan shakl"
    - "`23505` ni ushlash SAVEPOINT talab qiladi: `IntegrityError` tranzaksiyani ABORT qiladi va SAVEPOINT'siz 409 jimgina 500 ga aylanardi (`nvr.py:562-577` darsi)"
    - "Taqiqlangan token docstringda NOMLANMAY tushuntiriladi (`abs`, ogohlantirish kaliti): mexanik grep darvozasi va so'z bilan yozilgan sabab BIR VAQTDA saqlanadi"

key-files:
  created:
    - services/core-api/app/repositories/shift_repo.py
    - services/core-api/app/api/v1/shifts.py
    - tests/integration/test_shifts_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "06-10: `open_shift()` da SAVEPOINT (`begin_nested()`) — rejada NOMLANMAGAN, lekin MAJBURIY: `IntegrityError` tranzaksiyani abort qiladi va usiz 409 `shift_already_open` jimgina 500 ga aylanardi (03-06 da o'lchangan dars)"
  - "06-10: yopish `UPDATE` iga `AND status = :open` sharti qo'shildi — ikki bir vaqtdagi «Yopish» bosishining ikkinchisi 0 qator yozadi va ANIQ 409 oladi; usiz u sxema qo'riqchisiga urilib 500 berardi"
  - "06-10: `GET /shifts` standarti BUGUN (`billing.py` dagi KECHA dan atayin farqli) — smena bugun yopiladi va direktor variance ni SHU KUNI, naqd topshirilayotgan payt ko'radi (D-02 ning nizo modeli)"
  - "06-10: hisobot kuni `business_date` bo'yicha, `service_date` bo'yicha EMAS — kechagi qarzni bugun to'lagan pul BUGUNGI kassirning qutisiga tushadi; `service_date` bo'yicha guruhlash IKKALA kunning variance ini ham noto'g'ri chiqarardi"
  - "06-10: `ShiftReportRow` da `closed_at`/`declared_soum` NULLABLE EMAS — hisobot faqat yopilgan smenalarni qaytaradi va `closed_has_declaration` `CHECK` i juftlikni majburlaydi; ixtiyoriy qilish «ochiq smenani ham qo'shsak bo'ladi» taklifini kontraktga yozib qo'yardi"
  - "06-10: to'rtala smena marshruti ham `CASHIER_ROUTES` ga TUSHMADI (R-5) — `shift_manage` `market_admin` da HAM bor, `GET /shifts` esa kassirda 403 berib matritsani yiqitardi"
  - "06-10: `abs` va ogohlantirish kaliti docstringda NOM BILAN yozilmadi — sabab so'z bilan tushuntirildi, token esa yozilmadi; shunda reja matnining ikki talabi (docstringda sabab BOR + grep 0) BIR VAQTDA bajariladi (06-01 ning `variance()` docstringi bilan aynan bir xil yechim)"
  - "06-10: `REQUIREMENTS.md` TEGILMADI — CASH-04 ning frontend yarmi (06-12 ko'r deklaratsiya ekrani, 06-13 variance ro'yxati) hali yozilmagan, ya'ni uni «bajarildi» deb belgilash YOLG'ON bo'lardi; tarixan bu fayl faza yakunida (04-12, 05-15) yangilanadi"

patterns-established:
  - "Ikki mustaqil «yo'qlik» qatlami: (a) javob kalitlari to'plam TENGLIGI, (b) `app.openapi()` dan REKURSIV hosila skan — va skan IKKI YO'NALISHLI (bir marshrutda YO'Q, boshqasida BOR), aks holda «hamma joydan olib tashlash» uni yashil qilardi"
  - "Matritsaga yangi obyekt qo'shilganda UCH joy birga yangilanadi: `PARAM_FILLERS`, `MatrixBillingRows` maydoni va `test_param_fillers_point_at_the_other_market` dagi `foreign_values` ro'yxati — uchinchisi unutilsa darvoza DARHOL qizaradi (shu rejada aynan shunday qizardi)"
  - "Sabotaj natijasi «qizardi/yashil» dan ko'proq narsani beradi: S-2 da storno testining YASHIL qolishi TO'G'RI natija — u ortiqchani o'lchaydi va modul kattaligi uni o'zgartirmaydi, ya'ni uch test uch XIL xossani o'lchaydi"

requirements-completed: []

# Metrics
duration: 95min
completed: 2026-08-11
---

# Phase 6 Plan 10: Smena va ko'r naqd deklaratsiyasi Summary

**To'rt marshrut va D-25 ning serverdagi yarmi ikki mustaqil qatlamda qulflandi: `close` javobi AYNAN to'rt kalit (to'plam tengligi) va `app.openapi()` dan REKURSIV hosila skan — sabotaj IKKALASINI ham qizartirdi; SC#5(d) esa ikki tomonlama o'lchandi va `declared > system` holati ALOHIDA assert bilan qaytarilishi isbotlandi, `variance()` o'rniga modul kattaligini qo'yish kamomad da'vosini darhol qizartirdi.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-08-10T22:50:00Z
- **Completed:** 2026-08-11T00:25:00Z
- **Tasks:** 3
- **Files modified:** 6 (3 yangi, 3 kengaytirilgan) — **+2 459 / −5** qator

## Accomplishments

- **⛔ D-25 ning serverdagi yarmi IKKI MUSTAQIL QATLAMDA.** `POST /shifts/{id}/close` javobi kalitlari `assertEqual` bilan **AYNAN** `{id, status, declared_soum, closed_at}`; ikkinchi qatlam — `app.openapi()` dan **rekursiv** hosila skan. Skan `$ref` lar bo'ylab yuradi, ya'ni ichma-ich modeldagi maydonni ham ko'radi va **ikki yo'nalishli**: `close` da sakkiz nomning birortasi yo'q, `GET /shifts` da esa `system_soum` **va** `variance_soum` **bor**.
- **⛔ SC#5(d) IKKI TOMONLAMA o'lchandi va u `GET /shifts?day=` marshrutida.** Uchala holat (`<`, `>`, `==`) **bitta** testda va kattaliklari **atayin har xil** (5 000 va 7 000): teng kattaliklarda modul-sabotaji ikkala qatorni bir xil songa aylantirib farqni **ko'rsatmasdan** qolardi. `declared > system` holati **alohida** assert bilan — «ortiqcha naqd ham signal» (D-26).
- **⛔ D-27 STRUKTURAVIY va ilovada oldindan tekshiruv YO'Q.** `open_shift()` `INSERT` ni bajaradi va `23505` ni domen istisnosiga aylantiradi. **Nazorat holati** bilan o'lchandi: boshqa foydalanuvchi (bozor admini) **ayni vaqtda** o'z smenasini ochadi va **201** oladi — ya'ni test «409 har doim qaytadi» degan sababdan yashil bo'la olmaydi.
- **⛔ Deklaratsiya o'zgarmasligi IKKI DA'VO bilan.** Ikkinchi `close` → **409** va qator **bayt-bayt** o'zgarmagan (`env.shift(...) == before`). Faqat 409 ni tekshirish «javob rad etildi, lekin qator baribir o'zgardi» holatini o'tkazib yuborardi.
- **⛔ §11.5 FLAG'i IKKI YARIM bilan yopildi.** `shiftless_payment_count`/`_soum` **qaytariladi** (ular jimgina yo'qolmaydi) **va** o'sha to'lov smenaning `system_soum` iga **kirmaydi** (u kassir qutisiga tushmagan). Faqat birinchisi bo'lsa, o'sha pul ikki marta sanalishi mumkin bo'lardi.
- **⛔ Variance yuzasi HUQUQ darajasida yopildi.** Kassir `GET /shifts` ni chaqirsa **403** oladi (`report_view` unda yo'q) — bu marshrutni `SHIFT_MANAGE` ostiga qo'yish D-25 ni **bitta so'rov** bilan bekor qilardi.
- **⛔ Audit DB-triggerdan ekani XULQ bilan tasdiqlandi.** `write_app_audit()` chaqirilmaydi (grep → 0, chaqiruv/import yo'q), lekin smena ochilgach `audit_log` da `table_name='cashier_shifts'`, `action='insert'`, `source='db_trigger'` qatori **bor**. «Chaqiruv qo'shmadik» qarori shu test tufayli xavfsiz.
- **Yangi paket o'rnatilmadi** (T-06-SC), **migratsiyaga tegilmadi**, **frontendga tegilmadi** (`git diff --numstat frontend/` → **bo'sh**), **xato reyestri tegilmadi** (uchala faylning diffi **bo'sh**).

## Task Commits

1. **Task 1: `shift_repo.py` — smena ochish/yopish, tizim summasi va direktor hisoboti** — `277c675` (feat)
2. **Task 2: to'rt marshrut va KO'R serializator** — `e988f3a` (feat)
3. **Task 3: matritsa yozuvlari va SC#5(d)** — `d3a4df1` (test)

## Files Created/Modified

- `services/core-api/app/repositories/shift_repo.py` (**yangi**, 751 qator) — `open_shift()`, `open_shift_for()`, `close_shift()`, `shift_report()`, to'rt domen istisnosi, uch dataklass.
- `services/core-api/app/api/v1/shifts.py` (**yangi**, 455 qator) — to'rt marshrut, `ShiftManagerDep`/`ReportViewerDep`, `_report_day()` (standarti **bugun**).
- `tests/integration/test_shifts_api.py` (**yangi**, 884 qator) — **21 test**, to'rt guruh.
- `services/core-api/app/schemas.py` (+218) — besh model; `system_*` va `variance*` `close` javobida **umuman e'lon qilinmagan**.
- `services/core-api/app/main.py` (+31) — `/shifts` prefiksi va uning to'rt sababi.
- `tests/tenancy/test_cross_tenant.py` (+120/−5) — `shift_id` filleri, B bozorining ochiq smenasi, ikki tana, `CASHIER_ROUTES` ning R-5 bandi, `foreign_values` yozuvi, tozalash.

## Sabotaj (D-30) — IKKI URINISH, IKKALASI HAM KUTILGANICHA QIZARDI

| # | Sabotaj | Natija | Xulosa |
|---|---------|--------|--------|
| **S-1 (D-25, Pitfall 6)** | `ShiftCloseResponse` ga `variance_soum: int \| None = None` qo'shildi — ⛔ AYNAN «`null` bilan yuborish» stsenariysi | 🔴 **QIZARDI — IKKALA QATLAM HAM** | `test_the_close_response_has_exactly_four_keys` (javob **baytlari**: `['closed_at','declared_soum','id','status','variance_soum']`) **va** `test_the_openapi_schema_hides_...` (**kontrakt**). ⛔ Ikki mustaqil qatlam ekani shu bilan **o'lchandi**, e'lon qilinmadi |
| **S-2 (D-26, Pitfall 7)** | `shift_report()` da `variance(...)` o'rniga modul kattaligi (`abs(declared - system)`) | 🔴 **QIZARDI — kamomad da'vosi** | `AssertionError: ⛔ KAMOMAD manfiy bo'lishi SHART (D-26) ... assert 5000 == -5000`. ⛔ **`test_a_reversal_lowers_the_system_total_and_shows_up_as_a_surplus` YASHIL QOLDI VA BU TO'G'RI:** u **ortiqchani** o'lchaydi (`variance = +15 000`) va modul kattaligi uni **o'zgartirmaydi** — ya'ni uch test **uch xil** xossani o'lchaydi (06-09 ning S-3 bandi bilan aynan bir xil naqsh) |

⚠ Ikkala sabotaj ham qaytarib olindi; `git status` toza (`git diff` → `schemas.py` va `shift_repo.py` uchun **bo'sh**), `ruff`/`mypy` yashil, 29/29 test qayta yashil.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `open_shift()` da `SAVEPOINT` — usiz 409 jimgina 500 ga aylanardi**

- **Found during:** Task 1
- **Issue:** Reja `UniqueViolation` ni ushlab `ShiftAlreadyOpen` ga aylantirishni aytadi, lekin `IntegrityError` PostgreSQL tranzaksiyasini **ABORT** holatiga qo'yadi va undan keyingi har qanday bayonot `InFailedSqlTransaction` beradi. `TenantSessionDep` sessiyani `async with session.begin():` ichida beradi, ya'ni abort holatidagi tranzaksiya keyingi qadamda yiqilardi va kassir aniq «smena allaqachon ochiq» o'rniga **500 `internal_error`** ko'rardi — sabab esa butunlay yo'qolardi.
- **Fix:** `async with session.begin_nested():` — naqsh `nvr.py:562-577` dan **verbatim** (03-06 da o'lchangan dars). Sabab funksiya docstringida **so'z bilan** yozildi.
- **Files modified:** `services/core-api/app/repositories/shift_repo.py`
- **Verification:** `test_a_second_open_shift_for_the_same_cashier_is_rejected` — **409 `shift_already_open`** (500 emas).
- **Committed in:** `277c675`

**2. [Rule 2 - Missing Critical] Yopish `UPDATE` iga `AND status = :open` sharti**

- **Found during:** Task 1
- **Issue:** Reja «bitta `UPDATE`» ni talab qiladi, lekin poyga oynasini nomlamaydi: `SELECT` (uch darvoza) bilan `UPDATE` orasida boshqa so'rov smenani yopib ulgurishi mumkin. Shartsiz `UPDATE` o'shanda `shift_declaration_immutable()` ning birinchi shoxiga urilib **`23514`** berardi va u ilova qatlamida ushlanmagani uchun **500** bo'lardi — ya'ni ikki oynadan bir vaqtda «Yopish» bosgan kassir aniq 409 o'rniga server xatosini ko'rardi va nosozlik **faqat dala sinovida** chiqardi.
- **Fix:** Shart `UPDATE` ning `WHERE` iga qo'shildi (poyga **DB ga topshiriladi** — D-27 ning aynan o'sha mulohazasi); 0 qator → `ShiftAlreadyClosed` → **409**. Ilova qatlamidagi oldindan tekshiruv **saqlanadi**: u foydalanuvchiga aniq sabab beradi, bu esa poygani yopadi — **ikkalasi ham kerak** va farq docstringda yozilgan.
- **Files modified:** `services/core-api/app/repositories/shift_repo.py`
- **Verification:** `test_closing_a_shift_twice_is_rejected_and_the_declaration_is_untouched` — 409 **va** qator bayt-bayt o'zgarmagan.
- **Committed in:** `277c675`

**3. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da (06-01/06-04/06-05/06-06/06-08/06-09 dagi holatning **oltinchi** takrori).
- **Fix:** Ikkalasi asosiy repodan **NUSXALANDI**. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

**4. [Rule 3 - Blocking] `foreign_values` ro'yxati unutilsa matritsa darvozasi qizaradi**

- **Found during:** Task 3 (`pytest tests/tenancy` ning birinchi yugurishi)
- **Issue:** `PARAM_FILLERS["shift_id"]` qo'shilgach `test_param_fillers_point_at_the_other_market` qizardi: u fillerlar B bozoriga tegishli ekanini **mustaqil tuzilgan** ro'yxat bilan solishtiradi (`foreign_markers()` dan **atayin** ajratilgan) va yangi qiymat u yerda yo'q edi.
- **Fix:** `tenant_seed.billing.shift_id` o'sha ro'yxatga sabab izohi bilan qo'shildi. ⚠ Bu **darvozaning ishlagani**, nuqson emas — reja bandi «uchinchi joy» ni nomlamagan edi va u endi `patterns-established` da yozib qo'yildi.
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** `pytest tests/tenancy -q` — **to'liq yashil** (ikki mustaqil yugurish, exit 0).
- **Committed in:** `d3a4df1`

**5. [Rule 2 - Missing Critical] `close_shift` javobida `closed_at`/`declared_soum` uchun NAZORAT tekshiruvi**

- **Found during:** Task 2
- **Issue:** `ShiftRow` da ikkala maydon ham `... | None` (ochiq smenada `NULL`), `ShiftCloseResponse` da esa majburiy. `# type: ignore` bilan o'tkazib yuborish sxema drifti yuz berganda javobga jimgina `null` chiqarardi va klientning `z.strictObject` i **parse paytida** yiqilardi — sabab esa serverda emas, brauzerda ko'rinardi.
- **Fix:** Sxema kafolati buzilganda `RuntimeError` (`pragma: no cover` — u `closed_is_paired` / `closed_has_declaration` `CHECK` lari tufayli yuz bermaydi), sabab izohda.
- **Files modified:** `services/core-api/app/api/v1/shifts.py`
- **Verification:** `mypy` toza (`type: ignore` **ishlatilmadi**); 21/21 test yashil.
- **Committed in:** `e988f3a`

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **`grep -cE "\babs\(" shift_repo.py` → `0` VA sabab docstringda BOR.** Reja bir vaqtda «`abs()` olinmaydi» ni **docstringda tushuntirishni** va grep natijasini `0` bo'lishini talab qiladi — bu 06-08/06-09 dagi holatning aynan takrori. Yechim **06-01 dan olindi**: `sbozor_core/billing.py::variance()` docstringi tokenni **qavssiz** yozadi (`` `abs` funksiyasi bu modulda umuman uchramaydi ``). Shu yerda ham sabab «modul kattaligini oluvchi `abs` chaqiruvi» deb yozildi, ya'ni **ikkala talab ham** bajarildi.
- **`grep -cE "alert_key|shift_variance"` → `0` VA sabab modul docstringida BOR.** Ayni yechim: chegara va ogohlantirish **so'z bilan** tushuntirildi («ogohlantirish kaliti ham, uning reyestr yozuvi ham bu modulda YO'Q — egasi 8-faza»), token esa **yozilmadi**.
- **`grep -c "write_app_audit" shifts.py` → `4`, LEKIN TO'RTALASI HAM DOCSTRINGDA.** Reja `grep → 0` ni **va** «sabab docstringda **so'z bilan** bor» ni birga talab qiladi. Import ham, chaqiruv ham **yo'q** (`from app.security.audit import ...` satri faylda umuman yo'q); darvozaning yuk ko'taruvchi o'lchovi — `test_opening_a_shift_is_written_to_the_audit_log_by_the_database`, ya'ni jurnal qatori **DB triggeridan** kelishi **xulq bilan** tasdiqlanadi. `require_any_permission` uchun ham ayni holat (06-08/06-09 da ikki marta uchragan).
- **Task 1 va Task 2 ning `<verify>` bloklari hali mavjud bo'lmagan test faylini chaqiradi.** `tests/integration/test_shifts_api.py` — **Task 3** ning artefakti. Task 1 `ruff`/`mypy` bilan, Task 2 esa `test_route_coverage.py` bilan verifikatsiya qilindi — va u **aynan kutilganicha qizardi** (`PARAM_FILLERS` da yo'q parametrlar: `['shift_id']`), ya'ni darvoza ishladi va Task 3 uni yopdi. Reja tartibning o'zini shunday belgilagan (06-09 da ham ayni holat).
- **S608 (`ruff`) beshta so'rovda o'chirildi.** `_SHIFT_COLUMNS` — **modul konstantasi** va f-string ga tushadigan yagona qiymat; foydalanuvchi kiritmasi so'rovga faqat `bindparam()` orqali kiradi. Naqsh `billing_repo.py:1501` / `review_repo.py:231-237` dan, sabab konstantaning docstringida.

---

**Total deviations:** 5 auto-fixed (2 blocking, 3 missing-critical) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Qamrov kengaymadi. Yangi paket **o'rnatilmadi**, migratsiyaga **tegilmadi**, frontendga **tegilmadi**, xato reyestriga **hech nima qo'shilmadi**.

## Issues Encountered

- **To'liq to'plamda 34 qizil — hammasi UMUMIY KONTEYNER POYGASIDAN, birortasi ham bu rejaning o'zgarishlaridan emas.** Bu 06-08/06-09 SUMMARY laridagi holatning **uchinchi** takrori: `pytest -q` yugurayotgan paytda boshqa agentning `docker compose run` chaqiruvlari umumiy `sbozor-storage-1` / `nvr-sim` konteynerlarini **qayta yaratadi**.
  **O'LCHOV:** 33 tasi (NVR + live-view guruhi) izolyatsiyada qayta yugurtirildi → **99/99 yashil**; 34-chisi (`test_phase5_criteria.py::test_sc4_blind_audit_hides_the_system_answer_...`) ham izolyatsiyada → **9/9 yashil**. Bu reja birorta NVR/RTSP/kamera/ombor/ko'r-audit fayliga **tegmaydi**. Ops qadami bajarildi: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` **ishlatilmadi**).
- **5-fazadan meros flaky test (`test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`) bu yugurishda QIZARMADI.** U `deferred-items.md` ning 1-bandida va tegilmadi.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** (`frontend/node_modules` yo'q). ⛔ Junction/symlink **YARATILMADI**. Bu reja birorta frontend fayliga **tegmaydi** (`git diff --numstat frontend/` → **bo'sh**), ya'ni `gate` byudjetining (1250 s) to'liq o'lchovi keyingi to'lqinga qoladi. Band `deferred-items.md` ning 3-qatorida allaqachon bor.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_shifts_api.py -q` | ✅ **21/21** |
| `pytest tests/integration/test_shifts_api.py tests/tenancy/test_route_coverage.py -q` | ✅ **29/29** |
| `pytest tests/tenancy -q` | ✅ **to'liq yashil** (ikki mustaqil yugurish, exit 0) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**315** fayl formatlangan, **306** fayl tiplangan) |
| `pytest -q` (to'liq to'plam) | ⚠ 34 qizil — hammasi umumiy konteyner poygasidan (yuqoridagi bandga qarang) |
| O'sha 34 testning izolyatsiyada qayta yugurishi | ✅ **99/99** + **9/9** |
| `git diff --numstat frontend/` | ✅ **bo'sh** |
| `git diff --numstat billing_errors.py billing-errors.ts error-codes.test.mjs` | ✅ **bo'sh** (reyestr tegilmagan) |
| `git diff --stat <base>..HEAD -- frontend/ migrations/ packages/` | ✅ **bo'sh** |

**Qabul mezonlari (Task 1):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `open_shift()` ichida oldindan tekshiruv YO'Q | `grep -cE "SELECT.*FROM cashier_shifts.*status = 'open'"` → **0**; funksiya tanasi faqat `INSERT` | ✅ |
| `UniqueViolation\|sqlstate_of` ≥ 1 | **2** (`sqlstate_of` chaqiruvda, `UniqueViolation` konstanta docstringida) | ✅ |
| `grep -c "variance("` ≥ 1 | **3** (import + chaqiruv + docstring) | ✅ |
| `grep -cE "\babs\("` → 0 | **0** | ✅ |
| `shiftless_payment_count` / `_soum` ≥ 1 | **4** / **4** | ✅ |
| `grep -cE "alert_key\|shift_variance"` → 0 | **0** | ✅ |
| `grep -cE "def .*correct\|def .*fix_variance\|UPDATE cashier_shifts SET declared"` → 0 | **0** | ✅ |
| Xulq: ikkinchi `open_shift` → `ShiftAlreadyOpen` | `test_a_second_open_shift_...` (409) | ✅ |
| Xulq: `declared_soum=0` → o'tadi | `test_a_zero_declaration_is_accepted` | ✅ |
| Xulq: ikkinchi `close_shift` → `ShiftAlreadyClosed`, qator tegilmaydi | `test_closing_a_shift_twice_...` (bayt-bayt taqqoslash) | ✅ |
| Xulq: boshqa kassirning smenasi → `ShiftNotOwned` | `test_closing_another_cashiers_shift_is_forbidden` (403) | ✅ |
| `close_shift` **bitta** `UPDATE` bajaradi | Faylda `UPDATE cashier_shifts` → **1**; `close_shift` tanasida `session.execute(` → **2** (bitta `SELECT` darvozasi + bitta `UPDATE`). ⛔ Strukturaviy dalil: ikkinchi `UPDATE` `shift_declaration_immutable()` dan `23514` olardi, ya'ni **hamma yopish testi** 500 bilan qizarardi | ✅ |
| `ruff` va `mypy` toza | ✅ | ✅ |
| `min_lines: 240`; `contains: shift_system_total` | **751**; `grep -c` → **4** | ✅ |

**Qabul mezonlari (Task 2):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `set(ShiftCloseResponse.model_fields) == {id, status, declared_soum, closed_at}` | to'plam tengligi | ✅ |
| `ShiftCloseRequest` da `system_soum`/`variance_soum` yo'q | to'plam **AYNAN** `{declared_soum}` | ✅ |
| `set(ShiftReportResponse.model_fields) == {day, rows, shiftless_payment_count, shiftless_payment_soum}` | to'plam tengligi | ✅ |
| `openapi()` da `close` javob xossalari **AYNAN** to'rt kalit | `['closed_at','declared_soum','id','status']` | ✅ |
| `POST /shifts` ikkinchi marta → 409 `shift_already_open` | alohida test | ✅ |
| `GET /shifts/open` ochiq smena yo'q → **200** va `null` | alohida test (404 **emas**) | ✅ |
| `POST /shifts/{id}/close` ikkinchi marta → 409 `shift_already_closed` | alohida test | ✅ |
| Boshqa kassirning smenasini yopish → **403** | alohida test | ✅ |
| `GET /shifts?day=<ertaga>` → **422 `day_in_future`** | alohida test | ✅ |
| `GET /shifts?day=` javobida `system_soum` **va** `variance_soum` BOR | OpenAPI skanining (b) yo'nalishi + xulq testlari | ✅ |
| `grep -c write_app_audit shifts.py` → 0 va sabab docstringda | **4** — to'rtalasi ham docstringda; import/chaqiruv **yo'q** | ⚠ (aniqlashtirish bandiga qarang) |
| `audit_log` da `table_name='cashier_shifts'` qatori bor | `test_opening_a_shift_is_written_to_the_audit_log_by_the_database` (`source='db_trigger'`) | ✅ |

**Qabul mezonlari (Task 3):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `test_cross_tenant_object_returns_404` smena marshruti uchun **404** | tenancy yashil (`POST /shifts/{shift_id}/close`) | ✅ |
| `test_no_matrix_route_returns_422` yashil | tenancy yashil | ✅ |
| `test_all_path_params_have_fillers` yashil | `test_route_coverage.py` **8/8** | ✅ |
| `PARAM_FILLERS` da `shift_id` **haqiqiy** qiymat | `test_param_fillers_point_at_the_other_market` yashil | ✅ |
| `close` javobi kalitlari `assertEqual` bilan **AYNAN** to'rtta | `test_the_close_response_has_exactly_four_keys` | ✅ |
| OpenAPI skani **ikki yo'nalishni** ham tekshiradi | bitta testda ikkala assert | ✅ |
| SC#5(d): uchala holat bitta testda, `>` da `variance_soum > 0` | `test_the_variance_is_returned_in_both_directions_...` | ✅ |
| `shift_id IS NULL` to'lovi `system_soum` ga kirmaydi va `count == 1` | `test_shiftless_payments_are_counted_separately_...` (ikki assert) | ✅ |
| Bo'sh kunda uchala maydon qaytadi | `test_an_empty_day_still_returns_all_three_fields` | ✅ |
| Ikkala sabotaj natijasi SUMMARY da | yuqoridagi «Sabotaj» bo'limi | ✅ |
| `pytest tests/tenancy -q` va `pytest -q` | tenancy ✅ (ikki yugurish); to'liq to'plam ⚠ (konteyner poygasi, izolyatsiyada yashil) | ✅ |

## Known Stubs

Yo'q. Uchala yangi fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q, birorta funksiya qotirilgan bo'sh qiymat qaytarmaydi. `shift_repo` ning to'rtala funksiyasi ham marshrutlardan **chaqiriladi**, `payment_repo.shift_system_total()` esa (06-09 da «hech qayerdan chaqirilmaydi» deb qayd etilgan edi) endi **iste'molchisiga ega**.

## Threat Flags

Yangi xavfsizlik yuzasi **to'rt marshrut** bilan ochildi va threat register bo'yicha to'liq qoplandi:

- ⛔ Threat register: **sakkiz `mitigate` bandi bajarildi** — **T-06-58** (sakkiz maydon e'lon qilinmadi + to'plam tengligi **va** OpenAPI hosila skani + S-1 sabotaji), **T-06-59** (variance faqat `report_view` ostida; kassirga **403** — alohida test bilan), **T-06-60** (ikkinchi `close` → 409 **va** qator bayt-bayt o'zgarmagan; sxemada `shift_declaration_immutable()`), **T-06-61** (variance ikki tomonlama, modul kattaligi grep bilan taqiqlangan, `>` holati alohida assert + S-2 sabotaji), **T-06-62** (`cashier_id` so'rovchidan; begona kassir → **403**; tenant matritsasi → **404**), **T-06-63** (qisman `UNIQUE` + ilovada oldindan tekshiruv **yo'q** + nazorat holati), **T-06-64** (`shiftless_payment_*` alohida sanoq **va** ular `system_soum` ga kirmasligi — ikki yarim), **T-06-65** (`cashier_id` qaytadi, **ism emas** — to'plam tengligi bilan). T-06-SC (`accept`) — yangi paket o'rnatilmadi.
- ⛔ **Rejadan TASHQARIDA yopilgan ikki yuza:** `open_shift()` ning abort-tranzaksiya yo'li (500 → 409) va yopish `UPDATE` ining poyga oynasi (500 → 409). Ikkalasi ham «aniq domen javobi jimgina server xatosiga aylanadi» sinfida.
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**; migratsiyaga **tegilmadi**; yangi RLS policy **yozilmadi** (`cashier_shifts` 06-04 da allaqachon qoplangan).
- ⚠ **Yangi tenant yuzasi**: to'rtala marshrut ham `TenantSessionDep` ostida va cross-tenant matritsasiga **avtomatik** tushdi; `shift_id` filleri B bozorining **haqiqiy va ochiq** qatorini ko'rsatadi.
- Yangi rasm/fayl yuzasi **ochilmadi**; `SNAPSHOT_EVIDENCE_FRAME_ROUTES` va `PERSONAL_ROUTES` **tegilmadi** (javoblarda `PERSONAL_FIELDS` dan birortasi ham yo'q — to'plam tengligi bilan o'lchandi).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): parallel worktree'lar bir vaqtda `docker compose run` chaqirsa umumiy `storage`/`nvr-sim` konteynerlari **qayta yaratiladi** va boshqasining yugurayotgan to'plami qizaradi. Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` dan keyin qayta o'lchash (⛔ `-v` **ishlatilmaydi**).

## Next Phase Readiness

- **06-12 (ko'r deklaratsiya ekrani):** kontrakt **tayyor va o'lchangan**. `shiftCloseResponseSchema` (06-03) va server javobi **AYNAN** bir xil to'rt kalit; `shiftOpenSchema` ham mos. Klient uchun `GET /shifts/open` ochiq smena bo'lmasa **`null`** qaytaradi (404 emas), ya'ni `useOpenShift()` ning `retry: false` qarori to'g'ri.
- **06-13 (direktor variance bloki):** `GET /shifts?day=` **ikki tomonlama** variance va **ikki agregat** beradi; standart kun **bugun**. ⚠ **BITTA KALIT FARQI BOR:** klientning `shiftReportSchema` si `day` ni **bilmaydi** va u `z.strictObject` — band `deferred-items.md` ning **4-qatorida** (bu reja frontendga **tegmaydi**, `frontend/src/lib/*-queries.ts` shu to'lqinda **06-11 ning egaligida**).
- **06-14 (mezon darvozalari):** SC#5(d) ning mezon testi **shu rejada** yozildi va u **`GET /shifts?day=`** marshrutiga qaratilgan (UI-SPEC §10.4 ning qat'iylashtirishi) — 06-14 uni takrorlamasligi, balki **G-7 ning frontend yarmiga** (`collect-surface.test.mjs`) yo'naltirilishi kerak.
- **CASH-04 hali TO'LIQ EMAS:** backend yarmi bajarildi, ekran yarmi (06-12 formasi + 06-13 ro'yxati) qolmoqda — shuning uchun `REQUIREMENTS.md` **tegilmadi**.
- ⚠ **Ochiq band (bloklamaydi):** `deferred-items.md` ning 2-qatoridagi klient envelopelari (06-03 ning `chargeListSchema`/`anomalyListSchema`/`pendingLookupSchema`) hamon serverdan orqada — bu reja unga **tegmadi**.

## Self-Check: PASSED

**Fayllar (4/4 mavjud):** `services/core-api/app/repositories/shift_repo.py` (751 qator) · `services/core-api/app/api/v1/shifts.py` (455 qator) · `tests/integration/test_shifts_api.py` (884 qator) · `06-10-SUMMARY.md`

**Commitlar (3/3 topildi):** `277c675` · `e988f3a` · `d3a4df1`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `shift_repo.py` `min_lines: 240` | `wc -l` → **751** | ✅ |
| `shift_repo.py` `contains: shift_system_total` | `grep -c` → **4** | ✅ |
| `shift_repo.py` `provides`: to'rt funksiya | `open_shift()` · `close_shift()` · `open_shift_for()` · `shift_report()` | ✅ |
| `shifts.py` `provides`: to'rt marshrut | OpenAPI da `POST /shifts`, `GET /shifts/open`, `POST /shifts/{shift_id}/close`, `GET /shifts` | ✅ |
| `test_shifts_api.py` — SC#5(d) to'plam tengligi + ikki tomonlama variance | 21 test, to'rt guruh | ✅ |
| `key_links`: `close_shift` → `ShiftCloseResponse` (maydon E'LON QILINMAYDI) | `ShiftCloseResponse` `BlindItemResponse` naqshida; `system_soum` handlerda **ko'chirilmaydi** | ✅ |
| `key_links`: `shift_report` → `payments WHERE shift_id IS NULL` (`shiftless_payment*`) | `_SHIFTLESS_PAYMENTS` (belgili yig'indi, `COALESCE(...,0)`) | ✅ |
| `key_links`: `cashier_shifts` → `audit_log` (trigger, app-audit YO'Q) | `test_opening_a_shift_is_written_to_the_audit_log_by_the_database` (`source='db_trigger'`) | ✅ |

**`truths` (6/6):**
`close` javobi kalitlari **AYNAN** `{id, status, declared_soum, closed_at}`; `system_*` va `variance*` **umuman e'lon qilinmagan** (ikki qatlam + S-1 sabotaji) ·
variance **serverda** hisoblanadi va **faqat** `GET /shifts?day=` da qaytariladi (kassirga **403**) ·
variance **ikki tomonlama**, modul kattaligi **olinmaydi** (S-2 sabotaji bilan o'lchangan) ·
ikkinchi ochiq smena **409** — strukturaviy `UNIQUE` orqali (nazorat holati bilan) ·
ikkinchi `close` **409** va qator **bayt-bayt** tegilmagan ·
smenasiz to'lovlar **alohida sanoq** bilan qaytariladi va `system_soum` ga **kirmaydi**.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-11*
