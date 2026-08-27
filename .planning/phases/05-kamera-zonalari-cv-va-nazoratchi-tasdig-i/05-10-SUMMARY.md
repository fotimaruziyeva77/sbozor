---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 10
subsystem: api
tags: [fastapi, skip-locked, openapi-gate, rbac, valkey, rls, uncertainty-sampling, ai-03]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 05
    provides: "`review_assignments` / `zone_reviews` sxemasi, `UNIQUE (occupancy_event_id)`, `UNIQUE (review_assignment_id)`, `fk_zone_reviews_queue_kind_anchor` langari, shartsiz o'zgarmaslik triggeri; `tests/fixtures/occupancy_domain.py` seed'i"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 08
    provides: "`occupancy_events` ga `uncertain` qatorlar yozadigan `detect` jobi va `OCCUPANCY_UNCERTAIN_INDEX` ning issiq yo'li"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 06
    provides: "Router konventsiyalari (huquq imzoda, cross-tenant 404, `_market_id(principal)`) va matritsaning O'LCHANGAN ikki ko'rlik nuqtasi (huquq kuchsizlanishi, query parametridagi tenant kaliti)"
  - phase: 04-snapshot-pipeline
    provides: "`GET /snapshots/{id}/image` proxysi va uning `audit_read` i (dalil kadrining YAGONA yuzasi); `capture_repo.claim_due()` ning `FOR UPDATE ... SKIP LOCKED` naqshi va `duo_sessionmaker` o'lchov uskunasi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`Permission.OCCUPANCY_REVIEW` (2026-yildan beri ishlatilmay turgan), `AuthSeed.inspector`, cross-tenant matritsasi"
provides:
  - "`app/repositories/review_repo.py` — `build_uncertain_queue()`, `claim_next()`, `daily_answered_count()`, `record_answer()` va YAGONA `_PRIORITY_ORDER` ta'rifi"
  - "`app/api/v1/reviews.py` — `GET /review/uncertain/next`, `GET /review/budget`, `POST /review/{review_assignment_id}/answer`"
  - "`ReviewItemResponse` / `AnswerRequest` / `AnswerResponse` / `QueueBudget` / `ReviewBudgetResponse` — tizim javobi payloadda UMUMAN e'lon qilinmagan"
  - "`Settings.review_uncertain_daily_budget` (50), `review_blind_daily_budget` (30), `review_uncertain_midpoint` (0,45)"
  - "`test_no_bulk_approve_endpoint` — OpenAPI sxemasidan HOSILA ikki predikat (D-18 ning API darvozasi)"
  - "`INSPECTOR_ROUTES` + `market_a_inspector_headers` — matritsaning UCHINCHI sessiya darajasi"
  - "`add_zone_with_event()` / `has_active_vendor_on()` / `CONFIDENCE_0_45|0_55|0_59` — seed kengaytmasi"
affects: [05-11-kor-audit, 05-12-agregatsiya, 05-13-frontend-sessiya, 05-14-hisobot, 05-15-faza-darvozasi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DARVOZA IKKI MUSTAQIL PREDIKATDAN: «yuza» (router MODULIDAN hosila) va «lug'at» (`AnswerRequest` maydonidan hosila) — birinchisi bulk yo'lni O'Z yuzasida, ikkinchisi BOSHQA routerga ko'chirilganda ushlaydi"
    - "Rekursiv payload skani IKKI QATLAMLI: kalit reyestri (bilingan nomlar) + XOM MATNDA verdikt so'zining o'zi (nomdan mutlaqo mustaqil)"
    - "`SKIP LOCKED` NIMANI QOPLAMASLIGI ham kod ichida yoziladi: qulf `COMMIT` da tushadi, ya'ni yagona haqiqiy kafolat `UNIQUE` va u 409 ga aylanadi"
    - "Byudjet navbat bo'shligidan OLDIN tekshiriladi — «ish tugadi» yolg'oni «xabar noaniq» dan qimmatroq"
    - "Matritsaning uchinchi sessiya darajasi (`INSPECTOR_ROUTES`) va uning O'Z nazorat testi (`..._really_need_the_review_permission`)"
    - "Yo'l parametri nomi TO'QNASHUV YUZASI: `assignment_id` band bo'lgani uchun `review_assignment_id`, aks holda `PARAM_FILLERS` marshrutga begona OBYEKT TURINI berardi"

key-files:
  created:
    - services/core-api/app/repositories/review_repo.py
    - services/core-api/app/api/v1/reviews.py
    - tests/integration/test_uncertain_queue.py
  modified:
    - services/core-api/app/settings.py
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/fixtures/occupancy_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
  deleted: []

key-decisions:
  - "⚠ O'LCHANDI: `src.queue_kind` -> `:queue_kind` sabotaji 28 testni YASHIL qoldirdi va sabab MANTIQIY — `WHERE ra.queue_kind = :queue_kind` filtri ikkala ifodani teng qiladi. Da'vo o'lchanadigan shaklga TORAYTIRILDI («yozilgan qiymat konstanta emas») va u sabotaj D′ bilan qizartirildi"
  - "Byudjet KUNI `zone_reviews.decided_at` dan olinadi, `occupancy_events.business_date` dan EMAS: byudjet INSON diqqatiga qo'yilgan, ya'ni kechagi qoldiqni bugun ko'rish BUGUNGI byudjetni yeyishi kerak"
  - "`decision_ms` Valkey'dagi `monotonic_ns()` belgisidan hisoblanadi; manfiy yoki mantiqsiz katta farq `None` ga aylanadi — DIAGNOSTIKA nosozligi `decision_ms_non_negative` `CHECK` i orqali MAHSULOTNI yiqitmasin"
  - "`locked` HAR DOIM `true`: UI-SPEC §7.1 noaniq javobni «o'zgartirish mumkin» deydi, 05-05 SXEMASI esa buni IMKONSIZ qilgan (`UNIQUE` + shartsiz `BEFORE UPDATE`). Sxema ustun — ziddiyat SUMMARY da ochiq"
  - "`record_answer()` `queue_kind` ni FILTR sifatida oladi: ko'r audit topshirig'i bu marshrutda 404 (403/409 EMAS — ular navbat a'zoligini oshkor qilardi)"
  - "`claim_next()` da `reviewer_id` ARGUMENTI YO'Q (reja imzosidan farq): u ishlatilmasdi va «nazoratchiga biriktirilgan navbat» degan yolg'on va'da berardi"
  - "Yo'l parametri `review_assignment_id` — `assignment_id` `PATCH /assignments/{assignment_id}` tomonidan BAND va to'qnashuv matritsani jimgina bo'shatardi"
  - "`build_uncertain_queue()` da `NOT EXISTS` predikati BOR, lekin u POYGANI emas `LIMIT` NING MA'NOSINI qo'riqlaydi; poyga hamon `ON CONFLICT DO NOTHING` da"
  - "Yangi `Permission` QO'SHILMADI (M-8): `rbac.py` ham, `frontend/src/lib/rbac.ts` ham TEGILMAGAN"
  - "Yangi xato kodi QO'SHILMADI: `REVIEW_QUEUE_EMPTY`/`REVIEW_BUDGET_EXHAUSTED`/`REVIEW_ALREADY_ANSWERED` reyestrda 05-04 dan beri bor, ya'ni frontend va i18n TEGILMAGAN"

patterns-established:
  - "«Metodning yo'qligi — STRUKTURA» endi OpenAPI darajasida ham o'lchanadi: sxema skani + ikki predikat + quyi chegara"
  - "Sabotaj «yashil qoldi» degan natija ham QIYMAT: u da'voni o'lchanadigan shaklga toraytirishga majbur qiladi (sabotaj D -> D′)"
  - "Fixture qo'shimchasi SEED'GA emas, FUNKSIYAGA: `stall_ids[2]` ning zonasizligi 05-06 ning qamrov testini oziqlantiradi, ya'ni seed darajasida zona qo'shish uni JIMGINA trivial qilardi"

requirements-completed: []
requirements-advanced: [AI-03]
# ⚠ ATAYIN BO'SH — 05-05/05-06 dagi bilan AYNAN bir xil qaror.
# Bu reja AI-03 ning SERVER yuzasini to'liq yetkazadi, lekin talabni
# YOPMAYDI: AI-03 «nazoratchi noaniq javoblarni tasdiqlaydi» deydi va
# tasdiqlash EKRANI 05-13 da (`review-session.tsx`). Bugungi holatda
# navbatni faqat `curl` bilan ko'rish mumkin. `05-15` fazani DALIL bilan
# yopadi.

# Metrics
metrics:
  duration_minutes: 111
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 3
  files_modified: 6
  commits: 3
---

# Phase 5 Plan 10: Noaniq navbat — byudjet, ustuvorlik va OMMAVIY ENDPOINTNING YO'QLIGI — Summary

**Nazoratchi endi kunlik byudjet doirasidagi ustuvorlashtirilgan navbatni bitta-bittadan ko'radi va tizim javobini javobdan OLDIN ko'rmaydi; «hammasini tasdiqlash» yo'lining yo'qligi OpenAPI skani bilan o'lchandi va to'rt sabotajdan biri YASHIL qolib, da'voning o'zini toraytirishga majbur qildi.**

## Performance

- **Duration:** ~111 daqiqa (12:18 → 14:09 + tekshiruv)
- **Tasks:** 3/3
- **Files:** 3 yaratildi, 6 o'zgartirildi

## Task Commits

1. **Task 1 — `review_repo.py`, sozlamalar va seed kengaytmasi** — `1b3c61e` (feat)
2. **Task 2 — `reviews.py`, sxemalar, router va matritsa** — `4a6542e` (feat)
3. **Task 3 — SC#3 darvozalari va sabotajlar** — `67e48b3` (test)

## Bajarilgan ishlar

### Task 1 — Navbat serverda yuradi va ustuvorlik OCHIQ tanlangan

| Metod | Holat |
|---|---|
| `build_uncertain_queue(business_date, *, limit)` | ✅ `INSERT ... SELECT ... ON CONFLICT (occupancy_event_id) DO NOTHING RETURNING id` |
| `claim_next(*, queue_kind)` | ✅ `FOR UPDATE OF ra SKIP LOCKED`, olti jadvalli `INNER JOIN` |
| `daily_answered_count(reviewer_id, day, *, queue_kind)` | ✅ `decided_at AT TIME ZONE 'Asia/Tashkent'` |
| `record_answer(...)` | ✅ BITTA `WITH src ... INSERT ... RETURNING` — javob va oshkor verdikt bir so'rovda |

**Ustuvorlik bitta konstantada** (`_PRIORITY_ORDER`) va uni IKKALA so'rov ham ishlatadi:

```
ORDER BY <billing ta'siri> DESC,
         abs(ev.confidence - :midpoint) ASC,
         ev.id
```

Ikki nusxa yozilganda navbatga TUSHADIGAN bandlar bilan navbatdan OLINADIGAN
bandlar boshqa tartibda saralanardi — kunlik chegara eng qimmat bandlarni
kesib tashlardi, nazoratchi esa ularni umuman ko'rmasdi.

`Settings`: `review_uncertain_daily_budget` (50), `review_blind_daily_budget`
(30, D-13), `review_uncertain_midpoint` (0,45).

Seed: `add_zone_with_event()`, `has_active_vendor_on()` va uchta
`CONFIDENCE_0_*` konstantasi. **Seed'ning O'ZIGA qo'shilmadi** — sabab
deviatsiya #4 da.

### Task 2 — Uchta marshrut, ankorlash yo'li yopiq

`ReviewItemResponse` — o'n bir maydon va ularning hammasi ekranda bor.
`verdict`, `confidence`, `model_version`, `thresholds_version`, `purpose`,
`queue_kind`, `shown_ai_verdict` — **kalitlarining o'zi e'lon qilinmagan**.

`AnswerRequest` — **aynan bitta maydon** (`human_verdict`). `market_id` ham,
`shown_ai_verdict` ham, `decision_ms` ham yo'q.

`AnswerResponse` — `{system_answer, human_answer, matched, locked}`; nomlar
`verdict`/`confidence` dan ATAYIN farq qiladi, chunki G-12 darvozasi
(05-13) o'sha nomlarni `components/blind-audit/**` da taqiqlaydi.

Matritsa: `INSPECTOR_ROUTES` + nazoratchi sessiyasi + `review_assignment_id`
filleri + tana filleri; `MINIMUM_MATRIX_ROUTES` 52 → 55.

### Task 3 — SC#3 ning darvozalari

`test_no_bulk_approve_endpoint` **ikki mustaqil predikat**:

1. **YUZA** — nazoratchi routerining (`endpoint.__module__` bo'yicha hosila)
   birorta yozuv marshruti massiv ko'taradigan tana qabul qilmaydi;
2. **LUG'AT** — butun API'da `AnswerRequest` ning maydoni MASSIV ICHIDA
   uchramaydi.

Marshrut nomlari ro'yxati **yozilmagan**; quyi chegara `>= 20` skanerlangan
yozuv marshruti (bugun **44**).

## Sabotaj o'lchovlari — nima QIZARDI va **nima YASHIL QOLDI**

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --` **ishlatilmadi**);
oxirida `git status` toza.

| # | Sabotaj | NATIJA |
|---|---|---|
| **A** | `claim_next` dan `SKIP LOCKED` olib tashlandi | 🔴 `test_two_concurrent_claims_get_different_items` — `statement_timeout` `QueryCanceled` ga aylandi. ⚠ Timeoutsiz test **osilib qolardi**, qizarmasdan |
| **B** | `_PRIORITY_ORDER` da mezonlar joyi almashtirildi (avval yaqinlik) | 🔴 `test_claim_next_prefers_the_stall_with_a_vendor`<br>⚠ **`test_closer_confidence_wins_within_the_same_billing_impact` YASHIL QOLDI** va bu TO'G'RI: u yerda billing ta'siri TENG, ya'ni tartibni almashtirish natijani o'zgartirmaydi. Ikki test ikki xil YARIMNI o'lchaydi |
| **C** | `POST /review/answer-many` (massiv) nazoratchi routeriga qo'shildi | 🔴 predikat (1): `['POST /api/v1/review/answer-many']` |
| **C′** | O'sha endpoint **`camera_zones.py` ga ko'chirildi** (yuza predikatidan yashirish) | 🔴 predikat (2): `` `human_verdict` massiv ichida qabul qilinmoqda: ['POST /api/v1/camera-zones/approve-all'] ``. Ikkinchi predikatning butun qiymati shu qatorda |
| **D** | `INSERT` ga `src.queue_kind` o'rniga `:queue_kind` | ⚠⚠ **28 TESTNING HAMMASI YASHIL QOLDI** (pastga qarang) |
| **D′** | `INSERT` ga `'uncertain'` literali | 🔴 `test_record_answer_copies_the_queue_kind_from_the_assignment` — `fk_zone_reviews_queue_kind_anchor` `23503` bilan rad etdi |

### D — bu rejaning eng qimmatli natijasi

Sabotaj D **test nosozligi emas**: `_RECORD_ANSWER` ning
`WHERE ra.queue_kind = :queue_kind` filtri parametr bilan qator qiymatini
**teng qilib qo'yadi**, ya'ni ularni ajratadigan holat **mavjud emas** —
birorta test uni ajrata olmaydi.

Ikki xulosa:

1. **Da'vo toraytirildi.** «Server qiymatni qatordan o'qiydi» — bugun
   **o'lchanmaydigan** da'vo; o'lchanadigani esa **kuchliroq**: yozilgan
   qiymat **konstanta emas** va u topshiriqning turiga ergashadi (D′ bilan
   qizartirildi). Test docstringi va SQL izohi ikkalasi ham shu shaklga
   keltirildi va o'lchov **kod ichida yozib qo'yildi**.
2. **`src.queue_kind` shakli QOLDIRILDI** — uning qiymati bugungi kafolatda
   emas, **filtr bo'shatilgan kunga chidamlilikda**: o'shanda parametr
   shakli denormalizatsiya manbaini chaqiruvchiga ko'chirardi.

Bu 05-05 sabotaj D ning davomi (u langar bo'lmasa `CHECK` o'z nusxasiga
ishonishini o'lchagan edi) va 05-08 sabotaj E/F bilan bir sinf: **testning
da'vosi kodning shaklidan emas, o'lchanadigan farqdan chiqishi kerak**.

## Deviations from Plan

### 1. `[Rule 2 - Correctness]` `record_answer()` `queue_kind` ni FILTR sifatida oladi

- **Muammo:** Reja imzosi `record_answer(assignment_id, reviewer_id, human_verdict, shown_ai_verdict, decision_ms)`. Bu shaklda `POST /review/{id}/answer` **ko'r audit** topshirig'iga ham javob yozardi. 05-11 esa o'sha topshiriq uchun ALOHIDA marshrut va ALOHIDA xato kodi (`blind_answer_locked`, D-17.4 ning UI shakli) belgilaydi — ya'ni ikkinchi javob noto'g'ri kod bilan qaytardi va nazoratchi «qayta urinish» tugmasini ko'rardi.
- **Tuzatish:** `WHERE ra.queue_kind = :queue_kind` va chaqiruvchida `ReviewQueueKind.UNCERTAIN`. Ko'r audit topshirig'i bu marshrutda **404** (begona bozor bilan AYNAN bir xil) — 403 yoki 409 navbat a'zoligini oshkor qilardi va D-14 ni buzardi.
- **Fayllar:** `review_repo.py`, `reviews.py`; `test_answer_on_a_blind_assignment_is_not_found`
- **Commit:** `4a6542e`

### 2. `[Rule 3 - Blocking]` Yo'l parametri `review_assignment_id`, `assignment_id` EMAS

- **Topildi:** Task 2, cross-tenant matritsasining fillerlarini yozayotganda
- **Muammo:** `assignment_id` kaliti `PATCH /assignments/{assignment_id}` (RASTA-SOTUVCHI biriktirishi) tomonidan **band**. Bitta kalitni bo'lishish `PARAM_FILLERS` ni yangi marshrutga **begona obyekt TURINI** berishga majburlardi: javob 404 bo'lardi-yu, sababi tenant chegarasi emas, «bunday topshiriq umuman yo'q» bo'lardi — ya'ni matritsa **yashil turib hech nimani o'lchamasdi** (05-06 sabotaj S5 ning aynan sinfidagi ko'rlik).
- **Tuzatish:** `POST /review/{review_assignment_id}/answer`. Klient ko'radigan URL **o'zgarmaydi** (`/api/v1/review/<uuid>/answer`); farq faqat OpenAPI'dagi parametr nomida. Sabab `main.py` va `reviews.py` ning ikkalasida ham yozilgan.
- **Commit:** `4a6542e`

### 3. `[Rule 3 - Blocking]` Matritsaga UCHINCHI sessiya darajasi kerak bo'ldi

- **Topildi:** Task 2, `tests/tenancy` birinchi ijrosida
- **Muammo:** Uchala yangi marshrut ham `OCCUPANCY_REVIEW` talab qiladi, u esa D-07 matritsasida **faqat `inspector`** da. Matritsa esa bozor admini sessiyasidan yuradi → javob **403**, `test_cross_tenant_object_returns_404` esa aynan 403 ga qarshi yozilgan. «Yiqilmasin» deb 403 ni ruxsat etish HUQUQ darvozasini TENANT darvozasi ustiga yopib qo'yardi.
- **Tuzatish:** `INSPECTOR_ROUTES` + `market_a_inspector_headers` (`PLATFORM_ADMIN_ROUTES` naqshining aynan takrori) + ro'yxatning O'Z nazorat testi `test_inspector_routes_really_need_the_review_permission` (bozor admini ROSTDAN 403 oladi) + `test_inspector_routes_point_at_live_routes`.
- **⚠ `TenantSeed` ga OLTINCHI qatlam** (`auth: AuthSeed`) qo'shildi: nazoratchi `two_markets` da yo'q va uni o'sha seed'ga qo'shish o'nlab testning a'zolik manzarasini o'zgartirardi.
- **Fayllar:** `tests/tenancy/test_cross_tenant.py`, `test_route_coverage.py` (`MINIMUM_MATRIX_ROUTES` 52 → 55)
- **Commit:** `4a6542e`

### 4. `[Rule 2 - Correctness]` Seed kengaytmasi FUNKSIYA, seed'ning o'zi EMAS

- **Muammo:** Reja «`tests/fixtures/occupancy_domain.py` kengaytiriladi: turli confidence bilan `uncertain` hodisalar, biriktirilgan va biriktirilmagan sotuvchili rastalar» deydi. Ularni **seed'ga** qo'yish `stall_ids[2]` ga zona qo'shishni talab qilardi — o'sha rasta esa `camera_zone_repo.coverage().uncovered` ning YAGONA manbai (05-06 sabotaj S4). `uncovered` bir kamayib **noldan farq qilib turardi**, ya'ni test yashil qolardi va u JIMGINA trivial bo'lardi.
- **Tuzatish:** `add_zone_with_event()` — so'ralganda yozadi, faqat so'ragan testda mavjud. Sabab modul ichida yozilgan.
- **⚠ `verdict` ARGUMENT:** faqat `uncertain` yozadigan yordamchi «navbat faqat `uncertain` ni oladi» testini **yozib bo'lmas** qilardi (nomzod `NOT EXISTS` bilan ham chiqarib tashlanardi va filtr ajratilmay qolardi).
- **Commit:** `1b3c61e`

### 5. `[Rule 2 - Correctness]` `build_uncertain_queue()` da `NOT EXISTS` predikati

- **Muammo:** Reja «oldindan tekshirilmaydi, kolliziya `ON CONFLICT DO NOTHING` bilan hal bo'ladi» deydi. Faqat `ON CONFLICT` bilan `LIMIT` **allaqachon navbatda turgan** bandlarni ham sanardi: birinchi chaqiruv chegarani «yeb» qo'yardi va kun davomida kelgan YANGI `uncertain` hodisalar navbatga **hech qachon** tushmasdi (7 slot — bandlar kun bo'yi qo'shiladi).
- **Tuzatish:** `NOT EXISTS` **qo'shildi**, lekin poyga kafolatiga **tegilmadi**: `ON CONFLICT DO NOTHING` joyida. Farq docstringda ochiq — predikat **poygani emas, `LIMIT` NING MA'NOSINI** qo'riqlaydi. `test_build_uncertain_queue_respects_the_limit` chegaradan chiqib qolgan nomzod keyingi chaqiruvda tushishini o'lchaydi.
- **Commit:** `1b3c61e`

### 6. `[Qaror]` `claim_next()` da `reviewer_id` argumenti YO'Q

Reja imzosi `claim_next(market_id, reviewer_id)`. `market_id` `camera_zone_repo.coverage()` da o'rnatilgan qoida bo'yicha olib tashlandi (T-05-24). `reviewer_id` esa **ishlatilmasdi**: saralash unga tayanmaydi va tayanishi ham kerak emas — navbat BOZORNIKI. Ishlatilmaydigan argument «nazoratchiga biriktirilgan navbat bor» degan **yolg'on va'da** berardi, holbuki bir band ikki nazoratchiga ham berilishi mumkin va bu **ataylab** (qulf `COMMIT` da tushadi).

### 7. `[Qaror]` `locked` HAR DOIM `true` — UI-SPEC bilan O'LCHANGAN ZIDDIYAT

⚠ **UI-SPEC §7.1 jadvali noaniq navbat javobi uchun «Javob o'zgartiriladimi? — Ha, yangi yozuv ustiga qo'yiladi» deydi.** 05-05 sxemasi esa buni **imkonsiz** qilgan:

- `uq_zone_reviews_review_assignment_id` — ikkinchi qator yozib bo'lmaydi;
- `trg_zone_review_immutable` — `UPDATE` **shartsiz** rad etiladi.

Reja ham (`Ikkinchi POST .../answer → 409`) sxema tomonda. **Sxema ustun
olindi** va `AnswerResponse.locked` har doim `true`. Bu bezak emas: ikkala
mexanizm ham test bilan o'lchanadi (`test_second_answer_returns_409`,
`test_answered_row_is_immutable`).

**Ochiq band:** UI-SPEC §7.1 ning o'sha katagi **eskirgan** va 05-13 uni
o'qiydigan ijrochi «tahrirlash tugmasi kerak ekan» degan xulosaga kelishi
mumkin. Tuzatish `05-15` ning bandi (bu reja spetsifikatsiya faylini
tahrirlamaydi).

### 8. `[Rule 2 - Correctness]` `decision_ms` — `monotonic_ns()` va uch qatlamli himoya

- **Muammo:** `time.time()` bilan o'lchash NTP sakrashida **manfiy** farq berardi va `decision_ms_non_negative` `CHECK` i **butun javobni** rad etardi — ya'ni diagnostika nosozligi mahsulotni yiqitardi.
- **Tuzatish:** `monotonic_ns()`; manfiy yoki TTL dan katta farq `None` ga aylanadi; Valkey `RedisError` yutiladi. `zone_reviews.decision_ms` `nullable` bo'lgani (05-05) shu yo'lni qonuniy qiladi.
- **⚠ Cheklov kodda yozilgan:** `monotonic_ns()` boshlanish nuqtasi HAR JARAYONDA boshqa, ya'ni `core-api` ko'p worker bilan ishga tushirilsa (bugun bitta) o'lchov ma'nosiz bo'lardi — shuning uchun mantiqsiz qiymat `None` ga aylanadi.
- **Commit:** `4a6542e`

### 9. `[Qaror]` `extra="forbid"` QO'YILMADI

`AnswerRequest` noma'lum maydonni **jimgina tashlaydi** (Pydantic standarti).
`extra="forbid"` uni 422 bilan rad etardi — ya'ni eskirgan klient
nazoratchini **javob berishdan** to'sib qo'yardi. Javob — MAHSULOT,
`decision_ms` esa DIAGNOSTIKA: nosozlikning narxi ikkalasida bir xil emas.
`ScheduleCreateIn` dagi `extra="forbid"` boshqa sinf (usta formasining
kontrakti). Tashlanish `test_decision_ms_is_server_measured` bilan
o'lchanadi.

### 10. `[Rule 3 - Blocking]` `duo_sessionmaker` — pool chegarasi o'lchandi

Birinchi ijroda `test_two_concurrent_claims_get_different_items`
`QueuePool limit of size 1 ... timed out` bilan yiqildi: `app_engine`
`pool_size=1` (GUC sizishini ochib berish uchun, ATAYIN). `SKIP LOCKED`
o'lchovi esa IKKI OCHIQ tranzaksiyani talab qiladi.
`test_capture_repo.py::duo_sessionmaker` ning nusxasi olindi (`conftest.py`
ga **ko'chirilmadi** — u parallel to'lqinning umumiy fayli).

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| Yangi to'plam | `pytest tests/integration/test_uncertain_queue.py` | ✅ **28** |
| `core-api` to'liq to'plami | `pytest -q` | ✅ **exit 0**, **2081** yig'ildi (bazaviy 2043 + 38) |
| `core-api` tenancy | `pytest tests/tenancy` | ✅ **524** (bazaviy 506 + 18) |
| `core-api` lint/tiplar | `ruff check . && ruff format --check . && mypy .` | ✅ toza (**267** fayl) |
| `npm run gate` | to'liq zanjir | ✅ **exit 0** |
| `vitest run` | frontend | ✅ **494 (35 fayl)** — o'zgarmadi |
| `npm run i18n:check` | | ✅ **879 × 3** — o'zgarmadi |
| `cv-tests` | gate ichida | ✅ o'tdi — bu reja `cv-service` ga tegmadi |
| Skanerlangan yozuv marshrutlari | `test_no_bulk_approve_endpoint` | ✅ **44** (chegara ≥ 20) |
| `git diff --name-only` da `security/rbac.py` / `frontend/**` | | ✅ **YO'Q** (M-8: RBAC va frontend tegilmagan) |

**Frontend to'plamlari ALOHIDA ham yuritildi** (`i18n:check`, `vitest`) va
ikkalasi ham bazaviy sonlarda qoldi — bu reja birorta frontend fayliga
tegmadi.

## Known Stubs

**Yo'q** — soxta ma'lumot manbai ham, placeholder matn ham yaratilmadi.
Ikki band ATAYIN «hozircha chaqiruvchisiz» va ular stub EMAS:

| Nima | Nega stub emas |
|---|---|
| `build_uncertain_queue()` — mahsulot chaqiruvchisi yo'q | Reja uni ATAYIN shu yerga qo'yadi, jobi esa **05-11** da (`audit_draw` dan KEYIN chaqirilishi §C.8.3 ning talabi). Metod to'liq ishlaydi va **beshta test** bilan o'lchangan |
| `GET /review/budget` da `blind_audit` hisoblagichi `0 / 30` | Ko'r audit tortish 05-11 da. Nol qiymat **fakt**: namuna tortilmagan bo'lsa javob ham yo'q. UI-SPEC §7.2 kartani nol bilan ham ko'rsatishni TALAB qiladi |

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-43 (ommaviy tasdiqlash) | mitigate | Endpoint **yozilmagan**; `test_no_bulk_approve_endpoint` ikki predikat bilan; sabotaj C **va** C′ ikkalasini ham alohida qizartirdi |
| T-05-44 (`shown_ai_verdict`) | mitigate | `AnswerRequest` da maydon **e'lon qilinmagan**; server `SHOWN_AI_VERDICT` konstantasidan yozadi; DB `CHECK` ikkinchi qatlam; `test_answer_is_recorded_once` bazadan o'qiydi |
| T-05-45 (ankorlash) | mitigate | Payloadda kalitlar **yo'q**; test **rekursiv** skanerlaydi VA javob matnida verdikt so'zining o'zini ham qidiradi |
| T-05-46 («shoshib bosish») | mitigate | `decision_ms` serverda; klient qiymati Pydantic tomonidan tashlanadi; natija UI'da **ko'rsatilmaydi** (marshrut uni qaytarmaydi) |
| T-05-47 (dalil kadri) | **qisman** | Payload faqat `snapshot_id` beradi; presigned URL yo'q. Kadrning O'ZI `GET /snapshots/{id}/image` proxysidan (u `audit_read` yozadi) — ⚠ **ochiq band**, pastga qarang |
| T-05-48 (boshqa rol) | mitigate | `OCCUPANCY_REVIEW` + RLS; `test_director_cannot_reach_the_queue` 403 ni VA soxta audit qatorining yo'qligini o'lchaydi; matritsaning `INSPECTOR_ROUTES` nazorat testi ro'yxatni halol saqlaydi |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authorization-gap | `services/core-api/app/api/v1/snapshots.py` | ⚠⚠ **NAZORATCHI DALIL KADRINI OLA OLMAYDI.** `GET /snapshots/{id}/image` `CAMERA_VIEW` talab qiladi (`snapshots.py:408`), `ROLE_PERMISSIONS[INSPECTOR]` esa **aynan `{OCCUPANCY_REVIEW}`** (`rbac.py:217`). Ya'ni sof `inspector` roli bilan kirgan foydalanuvchi navbat bandini oladi, lekin rasmni **403** bilan ko'ra olmaydi — UI-SPEC §7.4 esa rasmni QARORNING DARVOZASI qiladi |

**Nega bu rejada TUZATILMADI (ongli qaror, Rule 4):**

1. `snapshots.py` ham, `rbac.py` ham bu rejaning fayl ro'yxatida **yo'q**;
2. UI-SPEC **M-8** bu fazada RBAC **tegilmasligini** yozadi va uni o'lchov bilan qo'yadi;
3. Tuzatishning har ikki shakli ham **mahsulot qarori**, texnik tanlov emas:
   - `INSPECTOR` ga `CAMERA_VIEW` berish — unga jonli ko'rish, kamera ro'yxati, kun jurnali va ogohlantirishlarni ham ochadi;
   - rasm marshrutini «`CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW`» ga o'tkazish — `require_permission()` ning **yagona** `required_permission` tegini ko'plikka aylantirishni talab qiladi, `tests/tenancy/test_personal_data_coverage.py:462` esa aynan o'sha tegdan `CAMERA_VIEW` ni talab qiladi. Ya'ni xavfsizlik darvozasining SEMANTIKASI qayta loyihalanadi.

**Bu O-03 bilan bir sinfda** (UI-SPEC §16.4: `platform_admin` da `report_view`
yo'q — «rollar to'plam, tekshirish uchun ikkinchi rol beriladi»). Xuddi shu
javob bu yerda ham amal qiladi: Karmanada nazoratchiga `market_admin` roli
ham berilsa oqim ishlaydi. Lekin UI-SPEC §4.6 **sof** nazoratchini real
foydalanuvchi deb ta'riflaydi («5-fazadan keyin u 2 yozuv ko'radi va
`/review` uning uyiga aylanadi»), ya'ni qaror **ochiq qolishi kerak emas**.

**Qaror kimda:** `05-13` (u `inspector` roli bilan qo'lda kirishni talab
qiladi — bu bosqichda kamdan-kam sezilmay qolmaydi) yoki `05-15`.

## Keyingi rejalar uchun ochiq bandlar

1. **⚠⚠ `05-13`/`05-15` uchun — yuqoridagi `threat_flag`.** Sof `inspector`
   dalil kadrini ko'ra olmaydi. `05-13` ning `<how-to-verify>` 1-qadami
   (`inspector` roli bilan kiring) buni **darhol** ko'rsatadi.
2. **`05-11` uchun:** `build_uncertain_queue()` **tayyor** va u
   `audit_draw` DAN KEYIN chaqirilishi shart (§C.8.3). Chaqiruv tartibining
   darvozasi o'sha rejada; `review_repo` modul docstringi sababni yozib
   qo'ygan.
3. **`05-11` uchun:** `AnswerResponse` ning to'rt maydoni **allaqachon**
   05-11 talab qilgan shaklda (`{system_answer, human_answer, matched,
   locked}`), ya'ni ko'r audit marshruti uni QAYTA ISHLATADI. Ikkinchi
   sxema yozilmasin.
4. **`05-11` uchun:** `record_answer()` `queue_kind` ni FILTR sifatida
   oladi — ko'r audit marshruti `ReviewQueueKind.BLIND_AUDIT` beradi va
   `IntegrityError` ni **`blind_answer_locked`** ga aylantiradi
   (`review_already_answered` emas — farq `occupancy_errors.py` da).
5. **`05-13` uchun:** `GET /review/uncertain/next` javob **`ReviewItemResponse`**
   shaklida; `snapshot_id` dan `GET /api/v1/snapshots/{id}/image` URL'i
   klientda quriladi. Poligon **normalangan (0..1)** — uni `<img>` ning
   RENDER o'lchamiga ko'paytirish kerak, `frame_width`/`frame_height` ga
   EMAS (ular bu javobda umuman yo'q).
6. **`05-13` uchun — ⚠ UI-SPEC §7.1 ESKIRGAN:** noaniq navbat javobi ham
   **o'zgarmas** (deviatsiya #7). Ikkinchi `POST` **409** beradi va UI
   «qayta urinish» tugmasi bermasligi kerak.
7. **`05-14` (Y-4) uchun:** `zone_reviews.decision_ms` endi to'ladi, lekin
   u `NULL` ham bo'lishi mumkin (Valkey uzilishi, TTL, ko'p worker).
   Hisobot **`NULL` ni «tez javob» deb sanamasligi** shart.
8. **⚠ OCHIQ BAND — `review_uncertain_midpoint` (0,45) ning HAQIQIY
   qiymati.** U `cv-service` dagi `UNCERTAIN_THRESHOLDS = (0.30, 0.60)`
   dan **hisob** bo'lib chiqarilgan va ikki kod bazasini bog'laydigan
   mexanizm ATAYIN yo'q (son faqat `ORDER BY` ga kiradi). Chegaralar
   `thresholds_version` bilan sozlanganda bu qiymat ham `.env` dan
   yangilanishi kerak — darvoza emas va bo'lmasligi ham kerak.
9. **`05-15` uchun:** `MINIMUM_MATRIX_ROUTES` endi **55**; 05-11 ikki
   marshrut qo'shadi va uni **57** ga ko'taradi. `INSPECTOR_ROUTES` ga ham
   o'sha ikkitasi qo'shilishi shart, aks holda matritsa ularni bozor
   admini sessiyasi bilan chaqirib **403** oladi va `test_cross_tenant_
   object_returns_404` yiqiladi.

## Self-Check: PASSED

- E'lon qilingan **3 yaratilgan + 6 o'zgartirilgan** fayl — hammasi diskda
  (`git diff --name-only 94e98ab..HEAD` → **9 fayl**);
- `1b3c61e`, `4a6542e`, `67e48b3` — **uchala commit ham `git log` da**;
- Sabotajlardan keyin to'liq to'plamlar qayta yugurtirildi: `pytest -q`
  **exit 0** (2081 yig'ildi), `tests/tenancy` **524**, `ruff`+`mypy` toza,
  `npm run gate` **exit 0**;
- `git status` toza — birorta sabotaj artefakti qolmadi (har biri `cp`
  bilan snapshotdan tiklandi, `git checkout --` **ishlatilmadi**).

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
