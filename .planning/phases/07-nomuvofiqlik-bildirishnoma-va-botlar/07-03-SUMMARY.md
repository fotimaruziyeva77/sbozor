---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, rbac, i18n, multi-tenant, postgres]

# Dependency graph
requires:
  - phase: 05-cv-va-nazoratchi
    provides: "`review_repo` navbat predikati (`queue_kind` + `NOT EXISTS (zone_reviews)`) — bosh ekran sanog'i undan NUSXA"
  - phase: 06-billing-va-kassir
    provides: "`payments` (kind/cashier_id/service_date) va kassir ko'rligining uch qatlami (T-06-53, T-06-59, `shifts.py:126`)"
  - phase: 01-poydevor
    provides: "`Permission`/`ROLE_PERMISSIONS` matritsasi, `PrincipalDep`, `TenantSessionDep` (409 `market_not_selected`)"
provides:
  - "`GET /api/v1/me/headline` — uch rol uchun BITTA marshrut, tanlov serverda (D-28)"
  - "`HeadlineResponse` — aynan `{metric, value}`, `extra=\"forbid\"` (D-29)"
  - "`HEADLINE_ORDER` — (huquq -> i18n kaliti) determinlashgan kortej"
  - "`headline_repo` — uchala ko'rsatkichning yagona so'rov manbai"
  - "Pitfall 1 xulqiy darvozasi: kassirning `value` i kun SUMMASIGA teng emas"
affects: [07-05-frontend-headline, 07-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Modul yuzasini pastki chiziqli import bilan yopish (`dir()` = aynan uch funksiya)"
    - "Huquq bo'yicha determinlashgan tanlov kortej (`HEADLINE_ORDER`), rol nomi ISHLATILMAYDI"
    - "Dispatch `Permission` enum bo'yicha + oxirgi shox `raise` (jimgina noto'g'ri son o'rniga baland nosozlik)"

key-files:
  created:
    - services/core-api/app/repositories/headline_repo.py
    - tests/integration/test_headline.py
  modified:
    - services/core-api/app/api/v1/me.py
    - services/core-api/app/schemas.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "Kassir ko'rsatkichi — kvitansiyalar SONI (`count(*)`), summasi EMAS: summa CASH-04 ning ko'r deklaratsiyasini bir qatorda bekor qilardi"
  - "`review_queue` faqat `uncertain` navbatni sanaydi; `blind_audit` KIRMAYDI — namuna hajmi nazoratchiga oshkor bo'lmasligi kerak"
  - "Huquq mos kelmasa 403 `headline_unavailable` — 204 ham, `value: 0` ham emas (nol o'lchangan qiymat bo'lib ko'rinardi)"
  - "`_headline_value()` `Permission` enum bo'yicha tarmoqlanadi, i18n kaliti bo'yicha EMAS (kalit qayta nomlanganda jimgina kassir shoxiga tushib ketardi)"
  - "`platform_admin` 403 oladi — D-07 matritsasida uning uchala huquqning birortasi ham yo'q (reja A6 bandi noto'g'ri edi)"

patterns-established:
  - "Ommaviy yuzani import-alias bilan qulflash: begona funksiyaga yo'l STRUKTURAVIY yopiladi, intizom bilan emas"
  - "Predikat nusxasini XULQIY tenglik bilan qulflash: sanoq nolga tushgan payt `claim_next()` ning `None` payti bilan bir xil"
  - "Javob yuzasini kalitlar TO'PLAMINING literal tengligi bilan o'lchash (`len()` yoki `not in` emas)"

requirements-completed: [RECON-06]

# Metrics
duration: 71min
completed: 2026-08-12
---

# Phase 7 Plan 03: Bosh ekran ko'rsatkichi (RECON-06) Summary

**`GET /me/headline` — bitta marshrut, huquq bo'yicha serverda tanlanadigan bitta son va bitta i18n kaliti; kassirga SUMMA emas, kvitansiyalar SONI qaytadi va bu xulqiy darvoza bilan qulflangan.**

## Performance

- **Duration:** ~71 min faol ish (sessiya o'rtasida uzilish bo'lgan — pastdagi «Issues Encountered»)
- **Started:** 2026-08-12T00:42:00Z (taxminiy)
- **Completed:** 2026-08-12T01:53:52Z
- **Tasks:** 2/2
- **Files modified:** 5 (2 yangi, 3 tahrirlangan)

## Accomplishments

- **Fazaning eng qimmat talab TO'QNASHUVI hal qilindi (Pitfall 1).** RECON-06 kassirga «bugungi yig'im» ni va'da qiladi; CASH-04 esa kassir tizim summasini bilmasligiga tayanadi. Yechim — `headline.receipts_written` = `count(*)`, va u **xulqiy** o'lchanadi: test kassir sessiyasi bilan chaqirib, `value` ning o'sha kunning haqiqiy summasiga **teng emasligini** talab qiladi (repozitoriy va HTTP qatlamlarida alohida).
- **Uch rol uchun BITTA marshrut** (D-28): tanlov `HEADLINE_ORDER` bo'yicha, **huquqqa** tayanadi va rol nomini umuman ishlatmaydi — ikki rolli foydalanuvchi ham determinlashgan bitta javob oladi (test ikki chaqiruvda bir xil natijani talab qiladi).
- **Javob yuzasi strukturaviy ravishda tor** (D-29): `extra="forbid"` + testda kalitlar to'plamining **literal tengligi**. Server matn emas, **kalit** qaytaradi — i18n bitta joyda (klientda) qoladi.
- **`headline_repo` ning ommaviy yuzasi aynan uch funksiya** va bu kosmetika emas: bitta `from ... import shift_system_total` qatori 6-fazaning uch qatlamli ko'rligini chetlab o'tish yo'lini ochardi. Har bir import `_` bilan aliaslangan, `from __future__ import annotations` ham yo'q (u modulga `annotations` nomini bog'lardi — o'lchandi).
- **Navbat predikati ajralib keta olmaydi:** `review_queue_count` `review_repo._CLAIM_TEMPLATE` ning `WHERE` idan nusxa va tenglik **xulqiy** qulflangan — sanoq nolga tushgan payt `claim_next()` ning `None` qaytargan payti bilan bir xil.

## Task Commits

1. **Task 1: `headline_repo` — uchala ko'rsatkichning yagona so'rov manbai** — `3a2b823` (feat)
2. **Task 2: `GET /me/headline` — huquq bo'yicha determinlashgan tanlov** — `4bd1d15` (feat)
3. **Format darvozasi** — `bb422e2` (style, `ruff format --check` talabi)

## Files Created/Modified

- `services/core-api/app/repositories/headline_repo.py` *(yangi, 266 qator)* — uchta sof o'qish funksiyasi: `revenue_today_soum` (belgili yig'indi), `review_queue_count` (javobsiz `uncertain` topshiriqlar), `receipts_written_count` (`count(*)`, storno kirmaydi). Kesh yo'q, saqlangan ustun yo'q.
- `services/core-api/app/api/v1/me.py` — `HEADLINE_ORDER` konstantasi, `GET /headline` marshruti va `_headline_value()` dispetcheri.
- `services/core-api/app/schemas.py` — `HeadlineResponse` (`metric: str`, `value: int`, `extra="forbid"`).
- `tests/integration/test_headline.py` *(yangi, 932 qator)* — 21 test: 9 repozitoriy qatlamida (`-k repo`), 12 HTTP chegarasida.
- `tests/tenancy/test_route_coverage.py` — yangi marshrutning reyestrga tushishi hujjatlashtirildi; `MINIMUM_MATRIX_ROUTES` **ATAYIN ko'tarilmadi** (shart `>=`, ko'tarish D-32 bo'yicha faza oxirida).

## Decisions Made

- **Kassir uchun `count(*)`, `sum()` emas** — Pitfall 1. Taqiq kodda docstring sifatida yozilgan va grep bilan tekshiriladigan holatda (`receipts_written_count` tanasida `sum(`/`amount_soum` yo'q).
- **`review_queue` faqat `uncertain`** — ko'r audit navbati sanoqqa kirmaydi. Sabab: «bugun 30 ta band bor» degan son ko'r auditni ko'r bo'lmagan qilardi (05-RESEARCH §C.8, javob ankorlanishi). Nazoratchining bosh ekrandagi soni — uning asosiy ishi.
- **Huquqsiz foydalanuvchiga 403, `204`/`value: 0` emas** — nol klientda o'lchangan qiymat bo'lib ko'rinardi. Bu 05-14 ning «o'lchanmagan sonning o'rniga NOL yozilmaydi» darsi.
- **Dispatch `Permission` enum bo'yicha, i18n kaliti bo'yicha emas** — reja kalit satrini nazarda tutgan edi; satr bo'yicha solishtiruv kalit qayta nomlanganda boshqaruvni **oxirgi shoxga (kassirnikiga)** tushirardi va direktor 200 javobi bilan noto'g'ri son olardi. Oxirgi shox `raise`, yopiqligi `test_every_headline_order_entry_has_a_resolver` bilan CI'ga ko'chirilgan.
- **`shift_id = NULL` seed to'lovlarida** — bosh ko'rsatkichning uchala so'rovi smenani umuman o'qimaydi; seed'dagi ochiq smena esa boshqa foydalanuvchiga tegishli bo'lishi mumkin (pastdagi deviatsiya 2).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reja A6 bandi `platform_admin` ni `REPORT_VIEW` egasi deb ko'rsatgan — matritsa buni rad etadi**
- **Found during:** Task 2 (`HEADLINE_ORDER` docstringini yozishda)
- **Issue:** Reja «`market_admin` va `platform_admin` `REPORT_VIEW` orqali direktornikiga tushadi (A6)» deydi. O'lchandi (`ROLE_PERMISSIONS` ustida): `platform_admin` da uchala huquqning **birortasi ham yo'q** — na `REPORT_VIEW`, na `OCCUPANCY_REVIEW`, na `PAYMENT_CREATE`. Reja bo'yicha yozilgan docstring **yolg'on da'vo** bo'lardi va keyingi ijrochi uni fakt deb o'qirdi.
- **Fix:** `ROLE_PERMISSIONS` **TEGILMADI** (D-07 matritsasi bu rejaning qamrovidan tashqarida va xulq to'g'ri: platforma admini bozorni sozlaydi, kundalik boshqarmaydi). Docstring o'lchangan faktga to'g'rilandi va sabab yozildi; `platform_admin` 403 darvozasining **realistik test subyektiga** aylandi («rolsiz foydalanuvchi» degan sun'iy holat o'rniga).
- **Files modified:** `services/core-api/app/api/v1/me.py`
- **Verification:** `test_a_user_without_any_headline_permission_is_refused` — platforma admini sessiyasi 403 va `headline_unavailable` oladi
- **Committed in:** `4bd1d15`

**2. [Rule 1 - Bug] Test fixture'i seedlar kesishuvi tufayli noto'g'ri kassirni tanlardi (tasodifiy yashil/qizil)**
- **Found during:** Task 2 (HTTP testlari birinchi yugurishda ikkita nosozlik berdi)
- **Issue:** `billing_domain._cashier_of()` kassirni `WHERE 'cashier' = ANY(roles) ORDER BY user_id LIMIT 1` bilan izlaydi. `test_payments_api.py` da bu bir ma'noli, chunki u yerda A bozorida `cashier` rolli **bitta** foydalanuvchi bor. Bu faylda esa `auth_seed` ham kerak (nazoratchi undan keladi) va u A bozoriga **ikkinchi** `cashier` rolli qator yozadi — `blocked` foydalanuvchisi. Ikki tasodifiy UUID orasidan tanlov **tasodif**, ya'ni `billing.market_a.cashier_id` login qila olmaydigan hisobga tushardi; marshrut esa sanoqni `principal.user_id` bo'yicha oladi va HTTP javobi `0` chiqardi.
- **Fix:** `Env.cashier_id` endi **sessiya egasining o'zi** (`base.market_a.cashier_user_id`) — yagona manba. Seed to'lovlari `shift_id = NULL` bilan yoziladi (ustun NULLABLE, OQ-6/A5; bosh ko'rsatkich smenani o'qimaydi), aks holda begona kassirning smenasi begona to'lovga ulanib qator ichdan zid bo'lardi. Sabab ikkala joyda ham docstring bilan yozildi.
- **Files modified:** `tests/integration/test_headline.py`
- **Verification:** 21/21 test yashil; nosozlik takrorlanmaydi (tanlov endi tasodifga bog'liq emas)
- **Committed in:** `4bd1d15`

**3. [Rule 3 - Blocking] `zone_reviews` dan `DELETE` append-only trigger bilan rad etildi**
- **Found during:** Task 1 (ko'r audit testi)
- **Issue:** Test seed'dagi javobni olib tashlashi kerak edi; `trg_zone_review_immutable` `DELETE` ni `P0001` bilan rad etadi (va bu **to'g'ri** — insonning moliyaviy oqibatli qarori o'chirilmaydi).
- **Fix:** Loyihada allaqachon mavjud **qoralama bozor** istisnosidan foydalanildi (`test_uncertain_queue.py::_delete_review` va `cleanup_occupancy_domain()` bilan aynan bir xil mexanizm): bayroq vaqtincha tushiriladi, qator o'chiriladi, bayroq darhol qaytariladi. Yangi mexanizm **yozilmadi**.
- **Files modified:** `tests/integration/test_headline.py`
- **Verification:** `test_repo_review_queue_ignores_the_blind_audit_queue` yashil
- **Committed in:** `3a2b823`

---

**Total deviations:** 3 auto-fixed (2 bug, 1 blocking)
**Impact on plan:** Uchalasi ham to'g'rilik uchun zarur edi. Birinchisi hujjatning yolg'on da'vosini oldini oldi va matritsaga tegmadi; ikkinchisi tasodifiy qizaradigan (flaky) testni tuzatdi; uchinchisi mavjud mexanizmni qayta ishlatdi. Qamrov kengaymadi — `ROLE_PERMISSIONS`, `PERSONAL_ROUTES` va `RECENT_PAYMENT_WINDOW` **tegilmagan**.

## Issues Encountered

- **Ijro sessiyasi o'rtasida uzildi (foydalanuvchi mashinasi o'chdi).** O'sha paytda `headline_repo.py` diskda yozilgan, lekin **commit qilinmagan** edi. Tiklashda HEAD tekshiruvi qayta bajarildi, `reset --hard` **ishlatilmadi** (u aynan o'sha commit qilinmagan ishni yo'q qilardi), fayl butunligi qayta o'lchandi va ish davom ettirildi. Shundan keyin har vazifa darhol commit qilindi.
- **`docker compose` worktree'da yangi loyiha sifatida ko'tarildi va `storage` konteyneri «unhealthy» berdi.** Sabab: `ops/seaweedfs/s3.json` (`.env` kabi gitignore'da) worktree'da yo'q edi va Docker uning o'rniga **katalog** yaratib qo'ygan. Ikkala fayl ham asosiy repodan nusxalandi (ikkalasi ham gitignore'da — commit'ga tushmaydi).

## User Setup Required

None — yangi tashqi xizmat ham, yangi paket ham qo'shilmadi (T-07-SC: `pip`/`npm` o'rnatilmadi).

## Verification Evidence

| Darvoza | Buyruq | Natija |
|---------|--------|--------|
| Reja Task 1 | `pytest tests/integration/test_headline.py -q -k repo` | 9 passed |
| Reja Task 2 | `pytest test_headline.py test_route_coverage.py test_personal_data_coverage.py -q` | 47 passed |
| To'liq fayl | `pytest tests/integration/test_headline.py -q` | 21 passed |
| Tenant darvozasi | `pytest tests/tenancy -q` | to'liq yashil (exit 0) |
| Birlik to'plami | `pytest tests/unit -q` | to'liq yashil |
| Lint/tip | `ruff check . && ruff format --check . && mypy .` | All checks passed / 309 fayl toza |
| Yuza (qo'lda) | `dir(headline_repo)` | aynan 3 nom |

## Next Phase Readiness

- **07-05 (frontend) uchun tayyor:** marshrut `GET /api/v1/me/headline`, javob `{metric, value}`. Klient `z.strictObject({metric, value})` bilan qulflashi va `HEADLINE_UNIT` reyestrini uch a'zoli qilishi kerak (G-33). Server tomonidagi ustun — `test_the_headline_metric_keys_are_the_three_registered_ones`.
- **Klient rolni O'QIMASLIGI shart** (UI-SPEC §10.2): tanlov allaqachon serverda va uni klientda takrorlash uchinchi haqiqat manbai yaratadi.
- **403 — normal holat, xato emas:** platforma admini (va kelajakdagi «faqat ko'rsin» rollari) 403 oladi; UI kartani umuman chizmasligi kerak (`null`), qizil blok emas.
- **Ochiq savol (bloklovchi emas):** platforma adminiga bosh ko'rsatkich kerak bo'lsa, `HEADLINE_ORDER` ga to'rtinchi yozuv qo'shiladi (masalan `MARKET_VIEW_ALL` -> bozorlar soni) va o'sha payt tartib savoli qaytadan beriladi.

## Self-Check: PASSED

- Fayllar mavjud: `headline_repo.py`, `test_headline.py`, `07-03-SUMMARY.md`
- Commit'lar mavjud: `3a2b823`, `4bd1d15`, `bb422e2`, `1066a0e`
- STATE.md / ROADMAP.md **tegilmagan** (worktree rejimi — orkestrator markazlashgan holda yangilaydi)

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
