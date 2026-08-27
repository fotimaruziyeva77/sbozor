---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 09
subsystem: api
tags: [fastapi, postgres, window-function, lead, trigger, rls, rbac, audit, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-08 — `app/schemas.py` DTO shartnomasi (`TariffItem`/`TariffListResponse.min_valid_from`/`CalendarResponse`/`WeekdaysRequest`), `MARKET_ERROR_CODES`, `sqlstate_of()`, `MarketProfileMissingError`, router naqshi (`_market_id`/`_not_found`/`_conflict`), `BODY_FILLERS` mexanikasi, `business_today()`; 02-07 — `market_today`/`market_scope` fixture'lari va `23514`/`23505` xato xaritasi; 02-06 — ikki bozorli domen seed'i, `market_is_open()`, `alembic_version = 0010`; 02-05 — `trg_tariff_past_immutable`; 02-04 — `Tariff`/`MarketProfile`/`MarketCalendarException` modellari"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`TenantSessionDep`/`require_permission`, `TenantScopedRepository.scoped()`, `fn_audit_row()` triggeri, cross-tenant matritsasi, `main.py` global RLS handleri"
provides:
  - "`app/repositories/tariff_repo.py` — `LEAD()` bilan hisoblanadigan `valid_to`, ikki tarmoqli `valid_from` darvozasi, `tariff_window()`"
  - "`app/repositories/calendar_repo.py` — `CalendarRepository` (haftalik jadval + istisnolar)"
  - "`app/api/v1/tariffs.py` — 4 marshrut (GET/POST/PATCH/DELETE)"
  - "`app/api/v1/calendar.py` — 4 marshrut (GET, PUT /weekdays, POST/DELETE /exceptions)"
  - "`app.schemas.TariffUpdateRequest` — 02-08 to'plamida yo'q edi"
  - "`tests/integration/test_tariffs_api.py` — MARKET-03 ning API isboti (15 test / 17 holat)"
  - "`tests/integration/test_calendar_api.py` — SC#4 ning API isboti (9 test / 11 holat)"
  - "Seed: B bozorining kalendar istisnosi (`B_HOLIDAY`) + `tariff_ids`/`calendar_exception_ids`"
  - "`fixtures.admin_api.TARIFFS_URL` / `CALENDAR_URL`"
affects: [02-10, 02-11, 02-12, 02-13, 02-15, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Oyna funksiyasi (`LEAD`) ichki so'rovda, FILTR tashqarida — aks holda yakka qator uchun `valid_to` har doim `NULL` bo'ladi"
    - "Ikki shartli darvoza BITTA yordamchida (`is_valid_from_allowed`) va u ikkala chaqiruvchiga (`POST` va `PATCH`) xizmat qiladi"
    - "DB triggeri FAQAT `OLD` ni ko'radigan joyda YANGI qiymat uchun ilova darvozasi MAJBURIY — bu takror emas, boshqa yo'l"
    - "Sana darvozasining chegara harfi IKKALA yo'nalishda parametrlashtiriladi (`±1`) — bitta tomon `<=` va `>=` sabotajlaridan birini o'tkazib yuboradi"
    - "Kalendar API'si `market_is_open()` ni CHAQIRMAYDI, unga YOZADI; test API orqali yozib, funksiya orqali o'qiydi"

key-files:
  created:
    - services/core-api/app/repositories/tariff_repo.py
    - services/core-api/app/repositories/calendar_repo.py
    - services/core-api/app/api/v1/tariffs.py
    - services/core-api/app/api/v1/calendar.py
    - tests/integration/test_tariffs_api.py
    - tests/integration/test_calendar_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/fixtures/admin_api.py
    - tests/fixtures/market_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "`_TARIFF_ROWS` IKKI QAVATLI: `LEAD()` ichkarida, `tariff_id`/`category_id` filtri tashqarida — sabotaj bilan o'lchandi"
  - "`update_future()` YANGI `valid_from` ni tekshiradi — trigger faqat `OLD` ni ko'radi va bu yo'l butunlay ochiq edi (sabotajda 200 bilan o'tdi)"
  - "`TariffUpdateRequest` DTO qo'shildi; `category_id` maydoni ATAYIN yo'q (tarif kaliti `(category_id, valid_from)`)"
  - "`CalendarRepository` alohida faylda — kod bazasidagi qoida: routerlar SQL bajarmaydi"
  - "`GET /calendar` istisnolarni JORIY YILDAN kesadi, yuqori chegara YO'Q — dekabrda belgilangan yanvar bayrami ro'yxatda qoladi"
  - "Seed B bozoriga BITTA kalendar istisnosi oldi; A ATAYIN toza qoldi — 02-07 uning istisnosiz holatini sinaydi"
  - "`test_other_past_date_is_rejected_on_draft_market` IKKI yo'nalishda parametrlashtirildi (`operating_since±1`) — rejadagi bitta holat `<=` sabotajini o'tkazib yuborardi"

patterns-established:
  - "Pattern: yozuv yo'lining javobi O'QISH yo'lidan quriladi va o'sha javob ALOHIDA assert bilan qulflanadi (aks holda ikki yo'l jimgina ajraladi)"
  - "Pattern: DB triggeri qamramaydigan tarmoq topilganda ilova darvozasi qo'yiladi va uning ZARURIYATI sabotaj bilan o'lchanadi"
  - "Pattern: chegara harfi ikkala tomondan parametrlashtiriladi; har bir parametr o'z sabotajini ushlaydi"

requirements-completed: []

# Metrics
duration: 55min
completed: 2026-07-31
---

# Phase 2 Plan 09: Tarif va kalendar API'si Summary

**Tarif yuzasi FAQAT QO'SHADIGAN holda ochildi — amal qilish oxiri `LEAD()` bilan hisoblanadi, o'tmish 403 bilan qulflanadi va qoralama bozordagi boshlang'ich narx istisnosi ikkala chegarasi bilan qamraldi; oltita sabotaj o'lchovi har bir darvozaning AYNAN bitta testni yiqitishini ko'rsatdi va ulardan biri rejada umuman ko'rilmagan teshikni fosh qildi: kelajakdagi tarifni `PATCH` bilan o'tmishga surish DB triggeri uchun butunlay qonuniy amal ekan (sabotajda 200 bilan o'tdi).**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3/3
- **Files:** 12 (6 yaratildi, 6 o'zgartirildi)
- **Testlar:** 606 → **672** (+66: tenancy +38, integratsiya +28)
- **Marshrutlar:** matritsa 21 → **29** (`EXEMPT_ROUTES` o'zgarmadi)

## Accomplishments

- **Oltita sabotaj o'lchovi darvozalarning KUCHINI aniq ko'rsatdi va hech birida ortiqcha test yiqilmadi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | `is_valid_from_allowed()` dan `window.is_draft` olib tashlandi | AYNAN 1: `test_operating_since_is_rejected_after_activation` | `..._accepted_on_draft_market` ✅ va `..._rejected_on_draft_market[ikkalasi]` ✅ — istisno FAOL bozorga sizib chiqqani faqat shu test bilan ko'rinadi |
  | `==` → `<=` (istisno kengaydi) | AYNAN 1: `test_other_past_date_is_rejected_on_draft_market[operating_since-1]` | `[operating_since+1]` ✅ — **ya'ni rejadagi yagona `+1` holati bu sabotajni O'TKAZIB YUBORARDI** |
  | `update_future()` dagi YANGI-sana darvozasi olib tashlandi | AYNAN 1: `test_patch_cannot_move_a_tariff_into_the_past` (**200** keldi, qator `2026-07-30` ga surildi, `is_past: true`) | `test_future_tariff_patch_and_delete_succeed` ✅ va `test_past_tariff_patch_returns_403` ✅ — **ya'ni DB triggeri bu yo'lda ROSTDAN hech qanday himoya bermaydi** |
  | `_TARIFF_ROWS` filtri oyna ICHIGA ko'chirildi | AYNAN 1: `test_valid_to_is_computed_from_next_row` (`valid_to` `None` keldi, `2026-09-29` kutilgan edi) | ro'yxat qismidagi assertlar o'sha testda keyinroq turadi; qolgan 27 holat ✅ — yakka qator javobi yagona darvoza |
  | `add_exception()` `is_open` ni e'tiborsiz qoldirdi | AYNAN 1: `test_holiday_exception_closes_the_day` | `test_exception_open_overrides_weekly_closure` ✅ — ikki yo'nalish HAQIQATAN mustaqil |
  | `BODY_FILLERS` dan `PATCH /tariffs/{id}` o'chirildi | AYNAN 1: `test_cross_tenant_object_returns_404[PATCH_/api/v1/tariffs/{tariff_id}]` (422 keldi) | qolgan 231 tenancy testi ✅ — filler yangi marshrutlarda ham YUK KO'TARUVCHI |

  Har oltitasidan keyin fayl `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza).

- **Fazaning eng qimmat topilmasi — `PATCH` orqali o'tmishga surish yo'li.** `trg_tariff_past_immutable` shartida faqat `OLD.valid_from` bor. Ya'ni "avval kelajakka narx yoz (ruxsat etilgan), so'ng uning sanasini kechagi kunga sur" ketma-ketligi T-02-63 darvozasini IKKI QADAMDA butunlay chetlab o'tardi. Sabotajda bu nazariy emas, o'lchangan: javob **200**, qator `2026-07-30` ga ko'chdi va `is_past: true` bo'lib qaytdi. Ilova darvozasi (`update_future`) shu teshikni yopadi va u DB triggeri bilan ALMASHTIRIB BO'LMAYDI.

- **Boshlang'ich narx istisnosi ikkala chegarasi bilan qulflandi.** Reja `operating_since + 1` ni yagona "tor" isboti sifatida belgilagan edi, lekin u faqat `>=` sabotajini ushlaydi; `<=` ga o'zgarish (istisno "har qanday o'tmish" ga aylanadi) undan bemalol o'tardi. Test `±1` bo'yicha parametrlashtirildi va sabotaj #2 aynan `-1` holatini yiqitdi.

- **`min_valid_from` server hisoblaydigan qiymat bo'lib qoldi va shart BITTA joyda yashaydi:** `window.operating_since` ifodasi butun kod bazasida bir marta uchraydi (`is_valid_from_allowed`, 294-qator). `add_tariff`, `update_future` va `GET /tariffs` uchalasi ham `tariff_window()` dan o'qiydi.

- **Kalendar API'si va `market_is_open()` bir xil haqiqatga tayanishi o'lchandi:** testlar API orqali YOZADI (`POST /calendar/exceptions`) va `SELECT market_is_open(:m, :d)` orqali O'QIYDI. Ikkala yo'nalish (bayram ochiq kunni yopadi / istisno yopiq kunni ochadi) hamda o'chirishdan keyin haftalik qoidaga qaytish — uchtasi ham tirik.

- **Cross-tenant matritsasi 21 dan 29 marshrutga kengaydi va `EXEMPT_ROUTES` ga BIRORTA yozuv qo'shilmadi.** Yangi ikkita yo'l parametri (`tariff_id`, `exception_id`) B bozorining HAQIQIY qatorlariga ishora qiladi.

## Task Commits

1. **Task 1: `tariff_repo.py` va `tariffs.py` — faqat qo'shadigan tarif API'si** — `521f1d9` (feat)
2. **Task 2: `calendar.py` — haftalik jadval, istisno kunlar va marshrutlar** — `7b89e83` (feat)
3. **Task 3: Tarif va kalendar API'sining integratsiya testlari** — `a4c93d2` (test)

## Files Created/Modified

**Yaratildi**

- `services/core-api/app/repositories/tariff_repo.py` — `TariffRepository`. `_TARIFF_ROWS` ikki qavatli (`LEAD()` ichkarida, filtrlar tashqarida) va uch chaqiruvchiga xizmat qiladi. `tariff_window()` `markets` + `market_profile` ni BITTA `SELECT` da o'qiydi (ikki so'rov orasida bozor faollashtirilishi mumkin edi). `add_tariff` ichida `UPDATE` YO'Q — `insert(Tariff)` 318-qatorda, `update(Tariff)` esa faqat `update_future` (377-qator) ichida.
- `services/core-api/app/repositories/calendar_repo.py` — `CalendarRepository`; xom faktlarni qaytaradi, "ochiqmi?" mantig'ini TAKRORLAMAYDI (u `market_is_open()` da).
- `services/core-api/app/api/v1/tariffs.py` — xato xaritasi `sqlstate` bo'yicha; `23514` → 403, `23505` → 409, `23503` → 404, domen istisnolari → 422/409. `write_app_audit` grep natijasi **0**.
- `services/core-api/app/api/v1/calendar.py` — `STALL_MANAGE` (yozuv) / `MARKET_DATA_VIEW` (o'qish); `_year_start()` `business_today()` dan (`date.today()` EMAS).
- `tests/integration/test_tariffs_api.py` — 15 test / 17 holat (reja ≥13 talab qiladi).
- `tests/integration/test_calendar_api.py` — 9 test / 11 holat (reja ≥8 talab qiladi).

**O'zgartirildi**

- `services/core-api/app/schemas.py` — `TariffUpdateRequest` (deviatsiya #1); cheklov `Annotated[int, Field(...)] | None` shaklida, union ustiga EMAS (02-08 qoidasi).
- `services/core-api/app/main.py` — ikkita router; izohda `BODY_FILLERS` qadami ham qo'shildi (ilgari faqat `PARAM_FILLERS` yozilgan edi).
- `tests/fixtures/market_domain.py` — `tariff_ids`, `calendar_exception_ids`, `B_HOLIDAY` (deviatsiya #2).
- `tests/tenancy/test_cross_tenant.py` — ikkita `PARAM_FILLERS`, to'rtta `BODY_FILLERS`, kengaytirilgan `foreign_markers()` va meta-test to'plami.
- `tests/tenancy/test_route_coverage.py` — `MINIMUM_MATRIX_ROUTES` 12 → 20 (amaldagi 29 dan ATAYIN past).
- `tests/fixtures/admin_api.py` — `TARIFFS_URL`, `CALENDAR_URL`.

## Decisions Made

- **`_TARIFF_ROWS` IKKI QAVATLI QILINDI.** Rejadagi bir qavatli so'rov `GET /tariffs` uchun to'g'ri, lekin `POST`/`PATCH` javobi BITTA qatorni o'qiydi — filtr oyna bilan bir joyda tursa `LEAD()` faqat o'sha qatorni ko'rib `NULL` qaytarardi. Natijada yozuv javobi "narx muddatsiz" deb yolg'on aytardi, `GET` esa aynan o'sha qator uchun to'g'ri sanani berardi. Sabotaj #4 buni o'lchadi.
- **`GET /calendar` istisnolarni JORIY YILDAN kesadi, yuqori chegara QO'YMAYDI.** Reja "faqat joriy yildan boshlab" deydi; ikki tomonlama kesish dekabrda belgilanadigan yanvar bayramini ro'yxatdan yashirardi (Karmanada odatiy holat).
- **`POST /calendar/exceptions` javobida `id` bor.** `<interfaces>` faqat `201` deydi. Tanasiz javob klientni endigina qo'shgan istisnoni o'chirish uchun butun ro'yxatni qayta so'rashga majburlardi.
- **`PATCH /tariffs/{id}` javobi `TariffItem`.** `<interfaces>` shaklni belgilamaydi; `zones.py`/`categories.py` naqshi (PATCH → element) saqlandi va u `valid_to` ni ham qayta hisoblaydi.
- **`CalendarRepository` alohida faylda.** Reja faqat `calendar.py` ni sanaydi, lekin bu fazadagi HAR BIR domen routeri SQL'ni repozitoriyga topshiradi (`zones`/`categories`/`stalls`/`tariffs`). Routerda xom `session.execute()` yozish `scoped()` ning ikki qatlamli kafolatini ham yo'qotardi.
- **Seed istisnosi FAQAT B bozorida.** A ga qo'shilsa 02-07 ning `test_weekly_closed_day_is_closed` va `test_exception_*` testlari boshlang'ich holatini yo'qotardi (ular "birorta istisno qatorisiz" holatni sinaydi). Sana ham ATAYIN martda — 02-07 ning ikkala kalendar sanasi avgustda.
- **`assert_safe_soum()` chaqiruvi qoldirildi**, garchi Pydantic (`gt=0, le=MAX_SAFE_SOUM`) uni amalda erishib bo'lmas qilsa ham: pul chegarasining ta'rifi `sbozor_core.money` da yashaydi va u DTO cheklovidan mustaqil o'zgarishi mumkin. Sabab izohda literal yozilgan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `PATCH /tariffs/{id}` uchun DTO 02-08 to'plamida YO'Q edi**

- **Found during:** Task 1
- **Issue:** Reja `<interfaces>` da `PATCH /api/v1/tariffs/{tariff_id}` uchun `{amount_soum?, valid_from?}` tanasini belgilaydi va `read_first` bandi "shakl 02-08 da qotirilgan" deydi. Amalda `app/schemas.py` da faqat `TariffCreateRequest` bor (uchala maydon ham MAJBURIY) — ya'ni marshrutni rejadagi shaklda umuman yozib bo'lmasdi. `TariffCreateRequest` ni qayta ishlatish `category_id` ni ham majburiy qilardi va tarif kalitini (`(category_id, valid_from)`, D-05) tahrirlanadigan qilib qo'yardi.
- **Fix:** `TariffUpdateRequest` qo'shildi (`amount_soum?`, `valid_from?`). `category_id` maydoni ATAYIN yo'q va sabab docstringda: uni o'zgartirish qatorni BOSHQA narx tarixiga ko'chirardi. Cheklov `Annotated[int, Field(...)] | None` shaklida — union ustiga emas (02-08 deviatsiya #7 ning qoidasi).
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `MARKET_ERROR_CODES` uzunligi O'ZGARMADI (20) — yangi xato kodi qo'shilmadi, ya'ni `frontend/src/lib/api-types.ts` qarzi ham o'smadi
- **Committed in:** `521f1d9`

**2. [Rule 3 - Blocking] `PARAM_FILLERS["exception_id"]` uchun HAQIQIY B qatori mavjud emas edi**

- **Found during:** Task 2
- **Issue:** Reja Task 2 da `PARAM_FILLERS` ga `exception_id` qo'shishni buyuradi va matritsaning meta-testi (`test_param_fillers_point_at_the_other_market`) har bir filler B bozorining HAQIQIY obyektiga ishora qilishini talab qiladi. Lekin `market_calendar_exceptions` seed'da BUTUNLAY bo'sh (02-06 uni ATAYIN shunday qoldirgan). Tasodifiy UUID qo'yish meta-testni darhol yiqitardi; uni "yumshatish" esa matritsaning butun ma'nosini yo'qotardi (404 "obyekt yo'q" degani bo'lardi, "boshqa bozorniki" emas).
- **Fix:** Seed'ga **faqat B bozorida** bitta istisno qo'shildi (`B_HOLIDAY = 2026-03-21`, `is_open=false`) va `MarketDomainRows` ga `calendar_exception_ids` hamda `tariff_ids` maydonlari kiritildi. A bozori ATAYIN toza qoldirildi: 02-07 ning uchta kalendar testi uning "birorta istisno qatorisiz" holatini sinaydi. Sana ham to'qnashmaydi — 02-07 ning `CLOSED_MONDAY`/`OPEN_TUESDAY` sanalari avgustda.
- **Files modified:** `tests/fixtures/market_domain.py`, `tests/tenancy/test_cross_tenant.py`
- **Verification:** 02-07 ning uchala kalendar testi (`test_weekly_closed_day_is_closed`, `test_exception_open_overrides_weekly_closure`, `test_calendar_is_fail_closed`) yashil qoldi; `test_param_fillers_point_at_the_other_market` yangi ikkala fillerni ham qabul qildi
- **Committed in:** `7b89e83`

**3. [Rule 2 - Missing Critical] `PATCH` orqali kelajakdagi tarifni O'TMISHGA surish yo'li OCHIQ edi**

- **Found during:** Task 1
- **Issue:** Reja `update_future()` uchun "qulflash mantig'i **DB triggerida**, repozitoriyda takrorlanmaydi" deb yozadi. Bu `OLD` qiymat uchun to'g'ri, lekin `trg_tariff_past_immutable` sharti AYNAN `OLD.valid_from <= bugun`, ya'ni u YANGI qiymatni umuman ko'rmaydi. Natijada T-02-63 darvozasi ("narx faqat kelajakdan boshlanadi") ikki qadamda butunlay chetlab o'tilardi: (1) kelajakka narx yoz — ruxsat etilgan; (2) uning `valid_from` ini kechagi kunga sur — trigger uchun qonuniy `UPDATE`. Bu 02-08 dagi `set_category()` bilan AYNAN bir xil strukturaviy holat (trigger `BEFORE UPDATE OR DELETE`, darvozasiz tarmoq esa boshqa yerda).
- **Fix:** `update_future()` `changes` da `valid_from` bo'lsa YANGI qiymatni AYNAN `add_tariff()` dagi ikki tarmoqli shartdan o'tkazadi (`is_valid_from_allowed`) va rad etilganda `ValidFromNotAllowedError` → 422 beradi. Shart yangi joyda TAKRORLANMADI — ikkala chaqiruvchi ham bitta yordamchidan o'tadi.
- **Files modified:** `services/core-api/app/repositories/tariff_repo.py`, `tests/integration/test_tariffs_api.py`
- **Verification:** **Sabotaj #3** — darvoza olib tashlanganda javob **200** bo'ldi va qator jimgina `2026-07-30` ga ko'chdi (`is_past: true`); nazorat holatlari (`..._patch_and_delete_succeed`, `..._past_tariff_patch_returns_403`) YASHIL qoldi, ya'ni trigger bu yo'lda rostdan hech nima qilmaydi
- **Committed in:** `521f1d9`, `a4c93d2`

**4. [Rule 1 - Bug] Yakka qator uchun `valid_to` HAR DOIM `null` bo'lardi**

- **Found during:** Task 1
- **Issue:** Rejadagi so'rov bir qavatli: `... WHERE t.market_id = :market_id ORDER BY ...`. `GET /tariffs` uchun u to'g'ri, lekin `POST`/`PATCH` javobi BITTA qatorni o'qiydi va filtr (`t.id = :tariff_id`) oyna funksiyasi bilan bir xil darajada tursa `LEAD()` faqat o'sha qatorni ko'radi — natija HAR DOIM `NULL`. Ya'ni yozuv javobi "bu narx muddatsiz" deb yolg'on aytardi, `GET` esa aynan o'sha qator uchun to'g'ri sanani qaytarardi; ikki javob bir-biriga zid bo'lardi va sabab kodga qarab umuman ko'rinmasdi.
- **Fix:** So'rov ikki qavatli qilindi — `LEAD()` ichki so'rovda (butun toifa tarixi ustida), `tariff_id`/`category_id` filtri esa TASHQARIDA. Sabab SQL matni ustidagi docstringda literal yozilgan.
- **Files modified:** `services/core-api/app/repositories/tariff_repo.py`, `tests/integration/test_tariffs_api.py`
- **Verification:** **Sabotaj #4** — filtr oyna ichiga ko'chirilganda AYNAN `test_valid_to_is_computed_from_next_row` yiqildi (`valid_to` `None` keldi, `2026-09-29` kutilgan edi); qolgan 27 holat yashil qoldi
- **Committed in:** `521f1d9`, `a4c93d2`

**5. [Rule 2 - Missing Critical] Istisno chegarasi FAQAT BIR yo'nalishda sinalardi**

- **Found during:** Task 3
- **Issue:** Reja `test_other_past_date_is_rejected_on_draft_market` ni "istisnoning TOR ekanining isboti" deb belgilaydi va sana sifatida `operating_since + 1 kun` ni beradi. Lekin bu holat faqat `>=` yo'nalishidagi xatoni ushlaydi. Rejaning O'ZI ogohlantirgan xato — `==` o'rniga `<=` yozish — bu testdan BEMALOL o'tardi: `operating_since + 1` `<= operating_since` shartini baribir qanoatlantirmaydi. Ya'ni "tenglik AYNAN" da'vosi amalda yarmigina qulflangan bo'lardi.
- **Fix:** Test `days_offset` bo'yicha parametrlashtirildi: `-1` (`<=` ni ushlaydi) va `+1` (`>=` ni ushlaydi). Funksiya NOMI o'zgarmadi — u `02-VALIDATION.md` traceability kaliti va grep bilan topiladigan bo'lib qoladi (02-08 da o'rnatilgan qoida).
- **Files modified:** `tests/integration/test_tariffs_api.py`
- **Verification:** **Sabotaj #2** — `==` `<=` ga o'zgartirilganda AYNAN `[operating_since-1]` yiqildi, `[operating_since+1]` esa YASHIL qoldi. Ya'ni rejadagi yagona holat bu sabotajni o'tkazib yuborardi
- **Committed in:** `a4c93d2`

**6. [Rule 3 - Blocking] `CalendarRepository` reja fayl ro'yxatidan tashqarida**

- **Found during:** Task 2
- **Issue:** Reja `<artifacts>` da faqat `app/api/v1/calendar.py` ni sanaydi va butun kalendar mantig'ini routerga qo'yishni nazarda tutadi. Lekin bu fazadagi HAR BIR domen routeri (`zones`, `categories`, `stalls`, `tariffs`) SQL'ni repozitoriyga topshiradi va `TenantScopedRepository.scoped()` orqali IKKI QATLAMLI tenant filtrini oladi. Routerda xom `session.execute(update(...))` yozish (a) o'sha kafolatni yo'qotardi, (b) 02-11 ning `setup-status` i uchun `open_weekdays` o'qishni router ichida qolgan kodga bog'lardi.
- **Fix:** `app/repositories/calendar_repo.py` yaratildi (`CalendarRepository`: `profile`, `set_weekdays`, `list_exceptions`, `add_exception`, `delete_exception`). Router faqat HTTP qatlami bo'lib qoldi. `MarketProfileMissingError` `stall_repo` dan QAYTA ISHLATILDI — ikkinchi, bir xil ma'noli istisno tipi yaratilmadi.
- **Files modified:** `services/core-api/app/repositories/calendar_repo.py` (yangi)
- **Verification:** `ruff check && ruff format --check && mypy` exit 0; `pytest` 672 passed
- **Committed in:** `7b89e83`

**7. [Rule 3 - Blocking] Task 1 ning `<verify>` bandi HALI MAVJUD BO'LMAGAN faylga tayanadi**

- **Found during:** Task 1
- **Issue:** Task 1 verifikatsiyasi `pytest tests/integration/test_tariffs_api.py` ni buyuradi, lekin o'sha fayl Task 3 da yaratiladi — ya'ni buyruq "file not found" bilan tugardi. Bu 02-08 deviatsiya #2 va 02-06 deviatsiya #2 bilan bir xil sinf: rejaning vazifa taqsimoti "har bir vazifa yashil commit qoldiradi" qoidasi bilan ziddiyatda.
- **Fix:** Task 1 uchun ekvivalent qamrov ishlatildi: `ruff check . && ruff format --check . && mypy .` (exit 0) va MAVJUD to'plam (`pytest -q`) yashilligi. Task 1 commit'i routerni `main.py` ga ULAMAYDI, ya'ni u o'z-o'zicha yashil: `test_no_unclassified_routes` yangi marshrutni ko'rmaydi va `PARAM_FILLERS` qarzi tug'ilmaydi. Ulash Task 2 da, `PARAM_FILLERS`/`BODY_FILLERS` bilan BIRGA bajarildi.
- **Files modified:** yo'q (bajarish tartibi)
- **Verification:** Uchala commit'da ham `ruff`/`mypy` exit 0 va `pytest tests/tenancy` yashil
- **Committed in:** `521f1d9`

---

**Total deviations:** 7 auto-fixed (4 blocking, 2 missing-critical, 1 bug). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, migratsiya, paket, xato kodi yoki rejadan tashqari endpoint qo'shilmadi (`alembic_version` `0010` bo'lib qoladi, `MARKET_ERROR_CODES` uzunligi 20). #1, #2, #6 va #7 rejaning O'Z bandlari orasidagi HAQIQIY ziddiyatlar (mavjud bo'lmagan DTO, mavjud bo'lmagan seed qatori, fayl ro'yxati va vazifa taqsimoti); #3 va #4 reja ko'rmagan ikkita yo'lni yopadi va ikkalasi ham sabotaj bilan o'lchandi; #5 rejaning O'Z ogohlantirishini (`<=` EMAS) tirik darvozaga aylantiradi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| OpenAPI'dagi yangi yo'llar | ✅ 6 yo'l / **8 marshrut** |
| `GET /tariffs` kelajak qator: `is_past` / `valid_to` | ✅ `false` / `null` |
| FAOL bozor + bugungi sana | ✅ **422** `valid_from_must_be_future` |
| FAOL bozor + kechagi sana | ✅ **422** |
| QORALAMA + `valid_from == operating_since` | ✅ **201**, `is_past = true`, qator DB'da |
| QORALAMA + `operating_since - 1` | ✅ **422** |
| QORALAMA + `operating_since + 1` | ✅ **422** |
| Faollashtirishdan keyin + `operating_since` | ✅ **422** (qoralamada o'sha sana 201 bergan edi) |
| `min_valid_from` — qoralama / faol | ✅ `2026-01-15` / `bugun + 1` |
| `min_valid_from` bo'sh ro'yxatda | ✅ mavjud (`items == []`) |
| Takroriy `(category_id, valid_from)` | ✅ **409** `tariff_already_set_for_date` |
| Uch qatorli tarix — tartib | ✅ `valid_from` KAMAYISH bo'yicha |
| O'rtadagi qatorning `valid_to` | ✅ keyingisining `valid_from` iga teng |
| Oxirgi qatorning `valid_to` | ✅ `null` |
| Yozuvdan keyingi javobda `valid_to` | ✅ hisoblangan (yakka qator yo'li) |
| Eski qator narxi yangi qator yozilgach | ✅ o'zgarmadi (`A_TARIFF_AMOUNTS[0]`) |
| Kelajakdagi qator `PATCH` / `DELETE` | ✅ **200** / **204** (nazorat) |
| O'tgan qator `PATCH` / `DELETE` | ✅ **403** `tariff_past_locked` (ikkalasi); qator JOYIDA qoldi |
| Kelajakdagi qatorni o'tmishga surish | ✅ **422**, sana O'ZGARMADI |
| A tokeni + B tarifi | ✅ **404**, `status != 403` alohida |
| Direktor `POST /tariffs` / `GET /tariffs` | ✅ **403** `forbidden` / **200** (nazorat) |
| Tarif yaratish auditi | ✅ AYNAN 1 qator, `insert`, `source = db_trigger` |
| `GET /calendar` — seed jadvali / istisnolar | ✅ `[2,3,4,5,6,7]` / `[]` |
| `PUT /weekdays` → `GET` | ✅ `[1..7]`; audit AYNAN 1 `update`, `old→new` to'g'ri |
| Yaroqsiz jadval: bo'sh / `[0,8]` / `[1,1,2]` | ✅ uchalasi **422**, DB'dagi jadval O'ZGARMADI |
| Bayram (`is_open=false`) ochiq kunga | ✅ `market_is_open()` `true → false` |
| Istisno (`is_open=true`) yopiq kunga | ✅ `false → true` |
| Istisno o'chirilgach | ✅ haftalik qoidaga qaytdi (`true → false`) |
| Takroriy istisno sanasi | ✅ **409** `calendar_exception_exists` |
| A tokeni + B istisnosi | ✅ **404**, `status != 403` alohida |
| Direktor `PUT /weekdays` va `POST /exceptions` | ✅ **403** ikkalasi; `GET /calendar` → 200 (nazorat) |
| `grep "update(Tariff)\|\.update("` (`add_tariff` ichida) | ✅ **0** (yagona uchrash — `update_future`, 377-qator) |
| `grep -c "operating_since"` (`tariff_repo.py`) | ✅ **14** |
| `window.operating_since` uchrashlari | ✅ **1** (shart BITTA yordamchida) |
| `grep -c "write_app_audit"` (`tariffs.py` / `calendar.py`) | ✅ **0** / **0** |
| `grep -c "23514"` (`tariffs.py`) | ✅ **6** (xato xaritasi tirik) |
| Cross-tenant matritsasi | ✅ 21 → **29** marshrut; `EXEMPT_ROUTES` uzunligi O'ZGARMADI (14) |

## Issues Encountered

- **`POST /markets/{id}/activate` endpointi hali yo'q** (u 02-11 da quriladi), lekin `test_operating_since_is_rejected_after_activation` unga tayanadi. Yechim: test faollashtirishning YAKUNIY HOLATINI (`markets.is_active = true`) `sbozor_owner` bilan qo'yadi. Darvoza aynan shu bayroqqa qaraydi, ya'ni qamrov o'zgarmaydi — 02-11 endpointi paydo bo'lganda u ham xuddi shu bayroqni ko'taradi. Sabab test konstantasining docstringida yozilgan.
- **Seed'ning uchala A toifasida ham `operating_since` sanasida tarif BOR**, ya'ni "boshlang'ich narx" testlari o'sha sanaga ikkinchi qator yozib 409 olardi va 422/201 farqi umuman sinalmasdi. Testlar `POST /categories` orqali TOZA toifa yaratadi — bu ayni paytda usta 4-qadamining haqiqiy boshlang'ich holatini ham takrorlaydi (D-13).
- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 672 testning har birida.
- **`ruff format` ikkita test faylini qayta formatladi** (uzun SQL satri va uzun chaqiruv) — ikkalasi ham qator uzunligi darajasida.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan va birorta DTO bo'sh qolmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `frontend/src/lib/api-types.ts::ERROR_CODES` da 2-fazaning 20 kodi YO'Q | 02-13 / 02-14 | Bu reja YANGI kod qo'shmadi (`MARKET_ERROR_CODES` uzunligi 20 bo'lib qoldi), ya'ni qarz o'smadi |
| `TariffRepository.current_amount()` hali CHAQIRILMAYDI | 06-hisob-kitob | 6-fazaning kunlik job'i va `categories.py` shu shakldan foydalanadi; hozircha `_LIST_CATEGORIES` o'z nusxasini ishlatadi (SQL bir xil) |
| Tarif tarixini O'QISH auditi | — | `tariffs` — shaxsiy ma'lumot EMAS (D-09 faqat `vendors` ga tegishli), ya'ni `audit_read` bu yerda ATAYIN yo'q |
| `POST /markets/{id}/activate` | 02-11 | Test bayroqni to'g'ridan-to'g'ri qo'yadi; darvoza allaqachon bayroqqa qaraydi |
| Kalendar UI (yopiq kun belgilashda ikkinchi darajali tasdiq, UI-SPEC §10.6) | 02-15 / 02-16 | Server tomonida hech qanday cheklov yo'q — destruktiv amal matni FRONTEND mas'uliyati |

## Threat Flags

Yangi xavfsizlik yuzasi rejaning `<threat_model>` idan TASHQARIDA paydo bo'lmadi: qo'shilgan 8 marshrutning hammasi tenant-scoped, `require_permission` ostida va cross-tenant matritsasiga avtomatik tushgan. Fayl kirishi, tashqi bog'liqlik va sxema o'zgarishi YO'Q.

| Threat ID | Holat |
|-----------|-------|
| T-02-62 | mitigate — `23514` → **403** `tariff_past_locked`; `PATCH` va `DELETE` ikkalasi ham sinaldi, `DELETE` da qator MAVJUDLIGI alohida tekshirildi |
| T-02-63 | mitigate — `valid_from <= business_today()` → 422; `bugun` holati alohida parametr. **Yon kanal topildi va yopildi** — deviatsiya #3 |
| T-02-63a | mitigate — istisno IKKI SHARTLI (`== operating_since` **va** `is_active = false`); uchala tarmoq ham test bilan, ikkalasi esa sabotaj bilan o'lchandi (#1 va #2) |
| T-02-64 | mitigate — `market_calendar_exceptions` DB-trigger auditi (02-06 da o'lchangan); `UNIQUE(market_id, exception_date)` → 409 |
| T-02-65 | mitigate — `test_weekdays_are_updated_and_audited` `old→new` farqini va `changed_keys` ni tekshiradi; qator AYNAN bitta (ikki marta yozuv darvozasi) |
| T-02-66 | mitigate — `require_permission(TARIFF_MANAGE / STALL_MANAGE)`; ikkala domenda ham direktor 403 oldi, nazorat `GET` → 200 |
| T-02-67 | mitigate — RLS + `market_id` bind parametri; A tokeni + B tarifi/istisnosi → **404**, `status != 403` alohida; matritsa ikkala yangi parametrni avtomatik qamraydi |
| T-02-67a | mitigate — `tariff_window()` `market_id` bind parametri bilan va RLS ostida; javob faqat joriy tenant uchun hisoblanadi |
| T-02-68 | mitigate — `GET /calendar` `limit` (standart 200, maksimum 500) + joriy yil filtri |
| T-02-69 | mitigate — Pydantic validatori uchala manfiy holatni rad etdi va DB'dagi jadval O'ZGARMAGANI alohida tekshirildi; DB `CHECK` ikkinchi qatlam |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (114 fayl, 113 manba) |
| 2 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida) |
| 3 | `npm run test:tenancy` (`pytest tests/tenancy`) | ✅ **232 passed** (02-08 dagi 194 + 38) |
| 4 | `npm run test` (`pytest -q`) | ✅ **672 passed** (02-08 dagi 606 + 66) |
| 5 | `app.openapi()` da `/api/v1/tariffs*` va `/api/v1/calendar*` | ✅ 6 yo'l / 8 marshrut |
| 6 | Sabotaj o'lchovlari (6 ta) | ✅ har birida AYNAN kutilgan test yiqildi, nazoratlar yashil qoldi |
| 7 | Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `add_tariff` ichida `UPDATE` YO'Q | ✅ (`insert` 318, `update` faqat 377 — `update_future` ichida) |
| Faol bozorda bugungi/o'tgan sana → 422 | ✅ ikkala holat |
| Qoralamada `valid_from == operating_since` → 201 | ✅ |
| Qoralamada boshqa o'tgan sana → 422 | ✅ `±1` ikkalasi |
| Faollashtirishdan keyin → 422 | ✅ |
| `min_valid_from` — bo'sh ro'yxatda ham | ✅ |
| `grep -c operating_since` > 0 va shart BITTA yordamchida | ✅ 14 / `window.operating_since` — 1 uchrash |
| Takroriy sana → 409 | ✅ |
| O'tgan qator `PATCH` → 403 | ✅ |
| Kelajak qator `DELETE` → 204 (nazorat) | ✅ |
| Oxirgi `valid_to` `null`, oldingisi keyingisiga teng | ✅ |
| Javobda `is_past` bor | ✅ |
| `grep write_app_audit` → 0 | ✅ |
| `ruff check && mypy` exit 0 | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| OpenAPI'da `/api/v1/tariffs` va `/api/v1/calendar` | ✅ |
| `{"open_weekdays": []}` → 422 | ✅ |
| `{"open_weekdays": [0,8]}` → 422 | ✅ |
| `{"open_weekdays": [1,1,2]}` → 422 | ✅ |
| `PUT` dan keyin `audit_log` da `market_profile` yozuvi | ✅ AYNAN 1 `update` (trigger yo'li) |
| `grep write_app_audit` (`calendar.py`) → 0 | ✅ |
| Takroriy istisno sanasi → 409 | ✅ |
| `pytest tests/tenancy -q` exit 0 (`test_no_unclassified_routes` yashil) | ✅ 232 passed |
| `ruff check && mypy` exit 0 | ✅ |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_tariffs_api.py` ≥13 test | ✅ **15 test / 17 holat** |
| `test_calendar_api.py` ≥8 test | ✅ **9 test / 11 holat** |
| Boshlang'ich narx uchtaligi mavjud va yashil | ✅ uchalasi ham (ikkinchisi `±1` bo'yicha parametrlashtirilgan) |
| `test_min_valid_from_matches_market_state` bo'sh ro'yxatni qamraydi | ✅ |
| Nazorat bandlari (`..._patch_and_delete_succeed`, direktor `GET`) | ✅ ikkalasi ham |
| `test_holiday_exception_closes_the_day` API'dan yozib, `market_is_open()` dan o'qiydi | ✅ |
| Cross-tenant testlarida `status != 403` alohida | ✅ ikkala faylda |
| `npm run test` exit 0 | ✅ 672 passed |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja sxemaga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi).

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-03, MARKET-05]` deb yozgan. Ikkalasining ham **backend yarmi** shu rejada tugadi, lekin ular foydalanuvchi ko'radigan qobiliyat sifatida UI'siz to'liq emas: tarif ekrani va kalendar boshqaruvi 02-15 da quriladi. Ularni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi (02-04…02-08 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-10…02-13 uchun QOTIRILGAN shartnoma:**

- **Router naqshi kengaydi:** `tariffs.py` — domen istisnosi (`ValidFromNotAllowedError`) + `IntegrityError` + `MarketProfileMissingError` uchlamasi bir joyda; yangi yozuv endpointi shu shakldan nusxa oladi.
- **`MarketProfileMissingError` YAGONA:** u `stall_repo` da e'lon qilinadi va `tariff_repo`/`calendar_repo` uni IMPORT qiladi. Yangi repozitoriy ham shu tipni qayta ishlatsin — ikkinchi, bir xil ma'noli istisno 409 xaritasini ikkiga bo'lardi.
- **Sana darvozasi:** `business_today()` HAR SO'ROVDA BIR MARTA olinadi va argument sifatida repozitoriyga beriladi (02-08 qarori). `TariffRepository.tariff_window(today)` — qoralama/faol farqini o'qish uchun tayyor namuna.
- **Oyna funksiyasi bo'lgan har qanday so'rovda filtr TASHQARIDA:** `_TARIFF_ROWS` naqshi (`SELECT ... FROM ( ... LEAD ... ) rows WHERE :id IS NULL OR ...`).

**02-11 (`setup-status` / `activate`) uchun:**

- `TariffRepository.tariff_window()` `operating_since` va `is_draft` ni bitta so'rovda beradi — faollashtirish darvozasi shu yordamchini qayta ishlatishi mumkin.
- `activate` bayroqni `true` qilganda QORALAMA tarmog'i AVTOMATIK yopiladi (test bilan qulflangan) va o'sha kundan boshlab `trg_tariff_past_immutable` boshlang'ich qatorlarni qulflaydi.
- `calendar_configured` sanog'i uchun `CalendarRepository.profile()` tayyor (profil yo'q bo'lsa istisno, bo'sh massiv EMAS).
- ⚠ `activate` amalga oshirilgach `tests/integration/test_tariffs_api.py::SET_MARKET_ACTIVE` ni endpoint chaqiruviga ALMASHTIRISH mumkin (lekin shart emas — darvoza bayroqqa qaraydi).

**02-15/02-16 (frontend) uchun:**

- `GET /tariffs` — `min_valid_from` ni sana maydonining `min` atributiga qo'ying, lekin uni DARVOZA deb qabul qilmang: qoralama bozorda `min` bilan bugun orasidagi sanalar ham 422 oladi (istisno AYNAN tenglik bo'yicha).
- `TariffItem.is_past` — tahrir tugmasini yashirish uchun, lekin server darvozasi BIRINCHI: 403 `tariff_past_locked` ni `tariffs.pastLocked` matniga aylantiring.
- `valid_to` — SERVERDA hisoblanadi; frontend uni keyingi qatordan qayta hisoblamaydi.
- `GET /calendar` — `open_weekdays` ISO raqamlari (1=dushanba); `exceptions[].is_open` IKKI TOMONLAMA va UI ikkala holatni ham ko'rsatishi kerak.
- Yopiq kun belgilash — destruktiv amal (UI-SPEC §10.6): ikkinchi darajali tasdiq FAQAT frontendda, serverda bunday cheklov yo'q.

**Yangi marshrut qo'shadigan HAR KIM uchun (02-08 dan meros, endi 8 marshrut bilan qayta tasdiqlangan):**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si** (kerak bo'lsa seed'ga qator qo'shib);
3. marshrut TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana.

Uchtasidan biri unutilsa `test_no_unclassified_routes` yoki `test_cross_tenant_object_returns_404` darhol qizaradi — ikkinchisi sabotaj #6 bilan qayta o'lchandi.

## Self-Check: PASSED

- Da'vo qilingan 6 yangi fayl diskda mavjud: `services/core-api/app/repositories/tariff_repo.py`, `services/core-api/app/repositories/calendar_repo.py`, `services/core-api/app/api/v1/tariffs.py`, `services/core-api/app/api/v1/calendar.py`, `tests/integration/test_tariffs_api.py`, `tests/integration/test_calendar_api.py`
- Da'vo qilingan 6 o'zgartirilgan fayl `git diff --stat b164707..HEAD` da ko'rinadi
- Uchala vazifa commit'i git tarixida mavjud: `521f1d9`, `7b89e83`, `a4c93d2`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only b164707 HEAD` bo'sh)
- Oltita sabotajdan keyin fayllar `git checkout -- <fayl>` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
