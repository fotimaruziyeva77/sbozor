---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 10
subsystem: api
tags: [fastapi, postgres, lateral, keyset, daterange, exclude, rls, rbac, audit-read, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-09 — router/repozitoriy bo'linishi (`routerlar SQL bajarmaydi`), `MarketProfileMissingError` ning yagona manbai, `business_today()` argument sifatida; 02-08 — `app/schemas.py` DTO shartnomasi (`VendorListItem`/`VendorRequest`/`AssignmentItem`/`AssignmentCreateRequest`/`AssignmentCloseRequest`), `MARKET_ERROR_CODES`, `sqlstate_of()`, `_LIKE_SPECIALS`, `BODY_FILLERS` mexanikasi, `_STALL_ROWS` ning `period @> :today` ta'rifi; 02-07 — D-09…D-12 ning DB darajasidagi xulqi va `market_today`/`market_scope` fixture'lari; 02-06 — `ex_stall_assignments_no_overlap`, `lower_bound_required`, ikki bozorli domen seed'i; 02-04 — `sbozor_core.periods.assignment_period()`"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`audit_read()` fabrikasi + `AuditReadIntent` (D-09), `TABLE_VENDORS`, `TenantSessionDep`/`require_permission`, `TenantScopedRepository.scoped()`, `fn_audit_row()` triggeri, cross-tenant matritsasi"
provides:
  - "`app/repositories/vendor_repo.py` — `VendorRepository` (keyset `(full_name, id)` + ikki `LATERAL` agregat) va `AssignmentRepository`"
  - "`app/api/v1/vendors.py` — 4 marshrut; 1-fazadagi `audit_read` mexanizmining BIRINCHI haqiqiy iste'molchisi"
  - "`app/api/v1/assignments.py` — 3 marshrut (ikkita router, ikkita prefiks)"
  - "`app.schemas`: `VendorQuery`, `VendorUpdateRequest`, `AssignmentListResponse`, `VENDOR_PAGE_SIZE_MAX`, `VENDOR_STALL_CODES_MAX`, `invalid_period` xato kodi"
  - "`app.repositories.stall_repo.like_term()` — `ILIKE` qochirishning YAGONA manbai (ilgari `_like_term`)"
  - "`tests/integration/test_vendors_api.py` — MARKET-04 o'qish auditi va D-12 (12 test)"
  - "`tests/integration/test_assignments_api.py` — D-09/D-10/D-11 API isboti (12 test)"
  - "`fixtures.admin_api.VENDORS_URL` / `ASSIGNMENTS_URL`"
affects: [02-11, 02-12, 02-13, 02-15, 02-16, 02-17, 06-hisob-kitob, 07-telegram-botlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "O'qish auditi IKKI MUSTAQIL QATLAM bilan himoyalanadi va BITTASINI buzish testni QIZARTIRMAYDI — ikkalasini birga buzish kerak (o'lchandi)"
    - "Cheklanmagan agregat va cheklangan ro'yxat IKKI ALOHIDA `LATERAL` da — bitta `LATERAL` da sanoq kesilgan to'plam ustida hisoblanardi"
    - "`array_agg(... ORDER BY ...)` ichki so'rov tartiblangan bo'lsa ham QAYTA e'lon qilinadi (SQL tartibni agregatga o'tkazishni kafolatlamaydi)"
    - "Bo'sh ro'yxat qaytaradigan marshrutda mavjudlik ALOHIDA tekshiriladi — aks holda cross-tenant so'rov `200 {\"items\": []}` bilan tugab, 404 da'vosi jimgina bajarilmaydi"
    - "Bitta domenning yo'llari turli prefiksda yashasa IKKITA router e'lon qilinadi (bitta routerni ikki marta ulash marshrutlarni dublikat qilardi)"
    - "Seed'ning SOBIT biriktirish sanalari 'bugungi sanoq' testlariga yaramaydi — kalendar ular ustidan suriladi"

key-files:
  created:
    - services/core-api/app/repositories/vendor_repo.py
    - services/core-api/app/api/v1/vendors.py
    - services/core-api/app/api/v1/assignments.py
    - tests/integration/test_vendors_api.py
    - tests/integration/test_assignments_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/repositories/stall_repo.py
    - services/core-api/app/main.py
    - tests/fixtures/admin_api.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "`GET /stalls/{id}/assignments` uchun IKKINCHI router (`stall_router`) — bitta routerni ikki prefiksda ulash marshrutlarni dublikat qilardi"
  - "`stall_exists()` darvozasi qo'shildi: usiz cross-tenant so'rov `200 {items: []}` berardi (sabotajda o'lchandi)"
  - "`invalid_period` — `MARKET_ERROR_CODES` ga qo'shilgan YAGONA yangi kod (20 -> 21); usiz `assignment_period()` ning `ValueError` i 500 bo'lardi"
  - "`VendorUpdateRequest` va `VendorQuery` qo'shildi — 02-08 to'plamida `PATCH` va query shakllari YO'Q edi"
  - "`_like_term` -> `like_term` (ommaviy): `_LIKE_SPECIALS` ikkinchi nusxaga ega bo'lmasligi uchun"
  - "`GET /vendors/{id}` javobi `VendorListItem` — kartochka ro'yxat qatoridan ortiq hech nima ko'rsatmaydi"
  - "Almashinuv uchun qulaylik endpointi ATAYIN yo'q (T-02-72) — ikki amal, ikki audit izi"
  - "`test_two_stalls_can_share_one_vendor` TOZA sotuvchi yaratadi — seed sotuvchisining bugungi sanog'i kalendarga bog'liq (`3 != 2` bilan yiqildi)"

patterns-established:
  - "Pattern: ikki qatlamli himoyada sabotaj HAR IKKALASINI birga buzadi — bitta qatlamni buzish 'darvoza kuchsiz' emas, 'ikkinchisi ushladi' degani"
  - "Pattern: bo'sh natija QONUNIY bo'lgan marshrutda tenant darvozasi ALOHIDA mavjudlik so'rovi bilan qo'yiladi"
  - "Pattern: 'bugungi holat' testlari seed'ning sobit sanalariga TAYANMAYDI — ma'lumot testning o'zi tomonidan bugundan hisoblab yoziladi"

requirements-completed: []

# Metrics
duration: 75min
completed: 2026-08-01
---

# Phase 2 Plan 10: Sotuvchilar reestri va biriktirish davrlari Summary

**MARKET-04 endpoint sifatida ochildi va 1-fazada qurilgan `audit_read` mexanizmi birinchi haqiqiy iste'molchisini oldi; oltita sabotaj o'lchovi darvozalarning kuchini aniq ko'rsatdi va ikkitasi rejaning ko'rmagan narsasini fosh qildi — o'qish auditi HAR BIR qatlami alohida buzilganda ham yashil qoladi (faqat ikkalasi birga buzilganda `test_forbidden_read_is_not_audited` va `test_cross_tenant_vendor_returns_404` qizaradi), `GET /stalls/{id}/assignments` esa mavjudlik tekshiruvisiz begona bozorning rastasi uchun `200 {"items": []}` qaytarib, cross-tenant 404 da'vosini butunlay chetlab o'tardi.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 3/3
- **Files:** 11 (5 yaratildi, 6 o'zgartirildi)
- **Testlar:** 672 → **732** (+60: tenancy +36, integratsiya +24)
- **Marshrutlar:** matritsa 29 → **36** (`EXEMPT_ROUTES` uzunligi O'ZGARMADI — 14)

## Accomplishments

- **Oltita sabotaj o'lchovi va ularning aniq natijalari:**

  | Sabotaj | Yiqilgan test(lar) | Nazorat holati |
  |---|---|---|
  | `list_vendors()` imzosida `intent` `principal` dan OLDINGA ko'chirildi | **0 (hech biri)** — 12 test yashil qoldi | ⚠ Bu KUTILGAN: ikkinchi qatlam (`BackgroundTasks` javobga bog'lanadi) 403 yo'lida yozuvni baribir to'sadi. Ya'ni e'lon tartibi — `defence in depth`, yagona darvoza EMAS |
  | E'lon tartibi + `audit_read` ning fon vazifasi DARHOL bajariladigan qilindi (IKKALA qatlam) | AYNAN 4: `test_forbidden_read_is_not_audited` (403 dan keyin **1 != 0**), `test_cross_tenant_vendor_returns_404` (404 dan keyin **1 != 0**), `test_vendor_read_is_audited`, `test_vendor_detail_read_is_audited` | qolgan 8 test ✅ — ya'ni ikkala qatlam HAQIQATAN mustaqil (01-07 ning da'vosi 2-fazada qayta o'lchandi) |
  | `_describe()` dan `exclude={"cursor"}` olib tashlandi | AYNAN 1: `test_vendor_read_is_audited` | qolgan 11 test ✅ — kursorli so'rov bo'lmaganda bu darvoza umuman sinalmasdi (`exclude_none` uni baribir tashlab yuborardi) |
  | `list_stall_assignments()` dan `stall_exists()` darvozasi olib tashlandi | AYNAN 2: `test_cross_tenant_stall_or_vendor_returns_404` va matritsaning `GET_/api/v1/stalls/{stall_id}/assignments` holati (**`200 — {"items":[]}`**) | `test_cross_tenant_is_indistinguishable_from_unknown_id` ✅ YASHIL qoldi — chunki begona va noma'lum ID ikkalasi ham bir xil bo'sh 200 berardi, ya'ni faqat 404 da'vosi bu teshikni ushlaydi |
  | `PATCH /assignments/{id}` dagi `assignment_not_open` darvozasi o'chirildi | AYNAN 1: `test_closing_a_closed_period_returns_409` (**200** keldi, yopilgan davr `2026-08-21` ga surildi) | qolgan 11 test ✅ — DB bu yo'lda hech qanday himoya bermaydi, yagona qo'riqchi ilova darvozasi |
  | `array_agg(... ORDER BY code_sort)` -> `ORDER BY code` | AYNAN 1: `test_vendor_list_includes_stall_codes` (`'100' != '3'`) | qolgan 11 test ✅ — inson-raqamli tartib javobning O'ZIDA qulflangan |

  Har oltitasidan keyin fayllar `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza, `git diff --stat` bo'sh).

- **Fazaning eng qimmat topilmasi — bo'sh ro'yxat qaytaradigan marshrutdagi tenant teshigi.** `GET /stalls/{id}/assignments` uchun bo'sh javob QONUNIY (D-11: sotuvchisiz rasta xato emas), ya'ni RLS natijani bo'shatib qo'yganda javob strukturaviy jihatdan TO'G'RI ko'rinadi. Darvozasiz A bozorining admini B bozorining rasta ID'sini so'rab `200 {"items": []}` olardi — bu "obyekt yo'q" emas, "obyekt bor, lekin ko'rsatmadim" degani va u enumeratsiya signali. Sabotajda bu nazariy emas, o'lchangan; `test_cross_tenant_is_indistinguishable_from_unknown_id` esa uni UMUMAN ushlamadi (ikkala yo'lda ham bir xil bo'sh 200).

- **O'qish auditining ikki qatlami 2-fazada qayta o'lchandi va natija 01-07 ning da'vosini tasdiqladi.** Faqat e'lon tartibini buzish (`intent` birinchi) hech qanday testni yiqitmadi: `BackgroundTasks` endpoint MUVAFFAQIYATLI qaytargan javobga biriktiriladi, 403 esa yangi javob quradi. Ikkalasi birga buzilganda esa `test_forbidden_read_is_not_audited` **va** `test_cross_tenant_vendor_returns_404` ikkalasi ham qizardi — ya'ni cross-tenant 404 uchun qo'shilgan qo'shimcha assertion (rejada yo'q edi) haqiqiy yuk ko'taruvchi darvoza bo'lib chiqdi: usiz "A admini B ning sotuvchisini o'qidi" degan yolg'on dalil jurnalda qolardi.

- **Almashinuv oqimi BUGUNGI kunga qurildi va shu tufayli u foydalanuvchi ko'radigan yuzada o'lchandi.** `test_handover_flow_moves_the_day_to_the_new_vendor` almashinuv kunini AYNAN `market_today` qilib tanlaydi, so'ng uchta mustaqil da'voni tekshiradi: `GET /stalls/{id}` bugun YANGI sotuvchini ko'rsatadi, tarixdagi eski davrning `to_date` i almashinuv kuniga teng, va DB darajasida `period @> :almashinuv_kuni` AYNAN BITTA qator beradi. Uchinchisi ikkinchisidan mustaqil: `[]` chegarasi ishlatilganda kun IKKALA davrga tushardi, ro'yxat esa baribir to'g'ri ko'rinardi va xato faqat 6-fazada patta ikki marta yozilganda chiqardi.

- **Seed'ning sobit sanalari "bugungi holat" testlariga yaramasligi o'lchandi.** `test_two_stalls_can_share_one_vendor` dastlab seed sotuvchisini ishlatgan va `stall_count == 3 != 2` bilan yiqilgan: `A_VENDOR_PHONES[0]` egasining `HANDOVER_START` (2026-08-01) dan boshlanadigan davri bugunni qamrab turgan edi. Kalendar `HANDOVER_DAY` (2026-08-10) ga yetganda o'sha sanoq YANA o'zgaradi. Yechim — sotuvchini test O'ZI yaratadi; sabab `_new_vendor()` docstringida literal yozilgan.

- **Cross-tenant matritsasi 29 dan 36 marshrutga kengaydi va `EXEMPT_ROUTES` ga BIRORTA yozuv qo'shilmadi.** Ikkita yangi yo'l parametri (`vendor_id`, `assignment_id`) B bozorining HAQIQIY qatorlariga ishora qiladi; `assignment_id` uchun B ning YAGONA OCHIQ davri tanlandi (yopiq davr matritsani 404 o'rniga 409 bilan yiqitardi).

## Task Commits

1. **Task 1: `vendor_repo.py` va `vendors.py` — reestr va shaxsiy ma'lumot o'qish auditi** — `35e5436` (feat)
2. **Task 2: `assignments.py` — biriktirish davrlari va almashinuv oqimi** — `0df8137` (feat)
3. **Task 3: Sotuvchi va biriktirish API'sining integratsiya testlari** — `7d9c4cf` (test)
4. **Izoh gigiyenasi (grep darvozasi bilan to'qnashadigan atama)** — `3e3af21` (docs)

## Files Created/Modified

**Yaratildi**

- `services/core-api/app/repositories/vendor_repo.py` — `VendorRepository` + `AssignmentRepository`. `_VENDOR_ROWS` da IKKI alohida `LATERAL` (chegarasiz `count(*)` va `LIMIT :codes_limit` bilan kesilgan `array_agg`); keyset `(full_name, id)` juftligi ustida. `_ASSIGNMENT_ROWS` chegaralarni `lower()`/`upper()` bilan yoyadi — `Range` obyekti tashqariga chiqmaydi.
- `services/core-api/app/api/v1/vendors.py` — `audit_read(TABLE_VENDORS, reason="vendor_view")` faqat ikkala `GET` da; e'lon tartibi va uning SABABI modul docstringida literal yozilgan.
- `services/core-api/app/api/v1/assignments.py` — ikkita router (`router` va `stall_router`), xato xaritasi `23P01`/`23503`/`23514` + `ValueError`; qulaylik endpointining YO'QLIGI sababi bilan hujjatlangan.
- `tests/integration/test_vendors_api.py` — 12 test (reja ≥10 talab qiladi).
- `tests/integration/test_assignments_api.py` — 12 test (reja ≥9 talab qiladi).

**O'zgartirildi**

- `services/core-api/app/schemas.py` — `VendorQuery`, `VendorUpdateRequest`, `AssignmentListResponse`, `VENDOR_PAGE_SIZE_MAX`, `VENDOR_STALL_CODES_MAX`, `invalid_period` (deviatsiyalar #1–#3); `AssignmentCloseRequest` docstringi `PATCH` yo'liga to'g'rilandi.
- `services/core-api/app/repositories/stall_repo.py` — `_like_term` → `like_term` (deviatsiya #4).
- `services/core-api/app/main.py` — uchta `include_router` (ikkinchi router prefikssiz, sabab izohda).
- `tests/fixtures/admin_api.py` — `VENDORS_URL`, `ASSIGNMENTS_URL`.
- `tests/tenancy/test_cross_tenant.py` — ikkita `PARAM_FILLERS`, to'rtta `BODY_FILLERS`, `MATRIX_VENDOR_PHONE`, `_free_stall()`, kengaytirilgan `foreign_markers()` va meta-test to'plami.
- `tests/tenancy/test_route_coverage.py` — `MINIMUM_MATRIX_ROUTES` 20 → 28 (amaldagi 36 dan ATAYIN past).

## Decisions Made

- **`GET /stalls/{stall_id}/assignments` uchun IKKINCHI router.** Reja "marshrut `assignments_router` da e'lon qilinadi va prefiks `{API_V1_PREFIX}` bo'ladi" deydi, lekin bir xil router obyektini ikki prefiksda ulash `/assignments` marshrutlarini ham DUBLIKAT qilardi (`/api/v1/assignments` va `/api/v1/api/v1/...` emas — ikkalasi ham ro'yxatga tushib, matritsa ikki marta chaqirardi). `stall_router` alohida `APIRouter` sifatida e'lon qilindi va `{API_V1_PREFIX}` ga ulandi; `stalls_router` bilan to'qnashuv yo'q (yo'llarning segment soni har xil). Sabab ikkala faylda ham izohda.
- **`GET /vendors/{id}` javobi `VendorListItem`.** `<interfaces>` shaklni belgilamaydi. Alohida `VendorDetail` DTO yaratish ma'nosiz bo'lardi: kartochka ro'yxat qatoridan ortiq hech nima ko'rsatmaydi (telefon ikkalasida ham bor, biriktirish TARIXI esa alohida endpointdan keladi).
- **`intent.filters` yakka o'qishda `{"vendor_id": ...}`.** Reja `_describe(query)` deydi, lekin yakka endpointda `query` obyekti umuman yo'q. Bo'sh `{}` yozish jurnalni o'qiyotgan odamni "butun reestr varaqlandimi yoki bitta sotuvchi ochildimi?" savoli bilan qoldirardi — bu D-09 yozuvining butun maqsadiga zid.
- **`period_of()` va `close()` ALOHIDA metodlar.** Bitta shartli `UPDATE ... WHERE upper(period) IS NULL` ikkala rad etishni ham "0 qator" bo'lib qaytarardi va API "topilmadi" (404) bilan "allaqachon yopiq" (409) ni ajrata olmasdi.
- **`23514` xato xaritasida QOLDIRILDI**, garchi u amalda erishib bo'lmaydigan bo'lsa ham (`assignment_period(start: date, ...)` quyi chegarani majburiy qiladi). `stalls.py` dagi qarordan farqli, chunki u yerdagi xavf boshqa edi ("DB himoyasi bor" degan yolg'on ishonch); bu yerda esa konstrayt HAQIQATAN mavjud va xom SQL yo'lini qamraydi — sabab konstanta docstringida.
- **`GET /stalls/{id}/assignments` uchun `audit_read` QO'YILMADI.** Reja `<interfaces>` da uni `MARKET_DATA_VIEW` deb belgilaydi. Javobda `vendor_name` bor, ya'ni bu texnik jihatdan shaxsiy ma'lumot — lekin 02-08 dagi `GET /stalls/{id}` allaqachon `phone` ni ham auditsiz qaytaradi. Faqat yangi marshrutga audit qo'yish yuzani NOTEKIS qilardi. Qaror ATAYIN "Threat Flags" bo'limida ochiq qoldirildi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `GET /vendors` uchun query DTO'si 02-08 to'plamida YO'Q edi**

- **Found during:** Task 1
- **Issue:** Reja `<interfaces>` da `GET /api/v1/vendors?q&limit&cursor` ni belgilaydi va `intent.filters = _describe(query)` ni TALAB qiladi — ya'ni `model_dump()` chaqiriladigan query MODELI kerak. `app/schemas.py` da esa `VendorQuery` umuman yo'q (02-08 faqat `StallQuery` va `AuditQuery` ni qotirgan). Parametrlarni alohida `Query()` argumentlari qilish `_describe()` ni qo'lda yig'iladigan `dict` ga aylantirardi va u qo'shilgan har yangi filtr bilan jimgina eskirardi.
- **Fix:** `VendorQuery` qo'shildi (`q`, `limit`, `cursor`) — `StallQuery` ning aynan naqshi. `limit` chegarasi `VENDOR_PAGE_SIZE_MAX` (T-02-78).
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `test_vendor_read_is_audited` `filters.limit` ni jurnalda topadi; sabotaj #3 `cursor` ning chiqarib tashlanishini o'lchadi
- **Committed in:** `35e5436`

**2. [Rule 3 - Blocking] `PATCH /vendors/{id}` uchun DTO ikkala maydonni ham MAJBURIY qilardi**

- **Found during:** Task 1
- **Issue:** Reja `<interfaces>` da `PATCH /api/v1/vendors/{vendor_id} {full_name?, phone?}` deb yozadi, `VendorRequest` da esa ikkala maydon ham majburiy (u `POST` uchun to'g'ri). Uni qayta ishlatish ismni tuzatmoqchi bo'lgan klientni telefonni ham qayta yuborishga majburlardi — va u ekrandagi ESKIRGAN qiymatni yuborib, telefonni jimgina orqaga qaytarardi.
- **Fix:** `VendorUpdateRequest` qo'shildi (`full_name?`, `phone?`); telefon validatori `VendorRequest` dagi bilan bir xil, ya'ni ikkala yo'l ham bir xil E.164 shaklini yozadi. Cheklov `Annotated[str, StringConstraints(...)] | None` shaklida — union USTIGA emas (02-08 deviatsiya #7 qoidasi).
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `test_vendor_name_is_editable_without_resending_the_phone` — `PATCH {"full_name": ...}` dan keyin telefon O'ZGARMADI
- **Committed in:** `35e5436`

**3. [Rule 2 - Missing Critical] Mantiqsiz davr chegarasi uchun xato kodi YO'Q edi**

- **Found during:** Task 2
- **Issue:** Reja `23514` ni 422 ga xaritalashni buyuradi va "`to_date <= lower(period)` bo'lsa 422" deydi, lekin `MARKET_ERROR_CODES` da bu holat uchun kod YO'Q. Amalda bu yo'l `23514` gacha yetib ham bormaydi: `assignment_period()` Python darajasida `ValueError` ko'taradi (`[a, a)` — Postgres uchun BO'SH davr va `EXCLUDE` uni to'xtatmaydi, ya'ni rastada "sotuvchisi bor, lekin hech qaysi kunda emas" qatori paydo bo'lardi). Ushlanmagan `ValueError` global handler orqali **500** bo'lardi va foydalanuvchi "server xatosi" ko'rardi.
- **Fix:** `invalid_period` kodi `MARKET_ERROR_CODES` ga qo'shildi (20 → **21**) va router uni IKKALA yo'lda ham beradi: `POST` (tana sanalari) va `PATCH` (mavjud davrning quyi chegarasi bilan solishtirish). Xato MATNI javobga chiqmaydi — u ichki konvensiyani tushuntiradi va dasturchiga qaratilgan.
- **Files modified:** `services/core-api/app/schemas.py`, `services/core-api/app/api/v1/assignments.py`
- **Verification:** `test_invalid_period_returns_422` ikkala tarmoqni ham qamraydi (`to_date == from_date` va `to_date < lower(period)`)
- **⚠ Qarz:** `frontend/src/lib/api-types.ts::ERROR_CODES` ko'zgusi endi 21 kod kutadi (02-13/02-14 yopadi)
- **Committed in:** `35e5436`, `0df8137`

**4. [Rule 3 - Blocking] `ILIKE` qochirishning ikkinchi nusxasi tug'ilardi**

- **Found during:** Task 1
- **Issue:** `q` filtri sotuvchilar reestrida ham bor, ya'ni 02-08 deviatsiya #6 dagi xato bu yerda AYNAN takrorlanardi: qochirilmagan `q=%` butun reestrni qaytarardi va foydalanuvchi buni "qidiruv topmadi" emas, "hammasi chiqdi" deb ko'rardi. Yechim funksiyasi (`_like_term`) `stall_repo.py` da MODUL-PRIVATE edi, ya'ni yagona yo'l — nusxa ko'chirish, u esa `_LIKE_SPECIALS` ni ikkinchi haqiqat manbaiga aylantirardi.
- **Fix:** `_like_term` → `like_term` (ommaviy, `__all__` ga qo'shildi), yagona chaqiruv joyi yangilandi va docstringda NEGA ommaviy ekani yozildi.
- **Files modified:** `services/core-api/app/repositories/stall_repo.py`, `services/core-api/app/repositories/vendor_repo.py`
- **Verification:** `ruff check && mypy` exit 0; `test_stall_list_respects_filters` (02-08) yashil qoldi
- **Committed in:** `35e5436`

**5. [Rule 2 - Missing Critical] `GET /stalls/{id}/assignments` cross-tenant so'rovga `200 {"items": []}` qaytarardi**

- **Found during:** Task 2
- **Issue:** Reja bu marshrut uchun "sotuvchisiz rasta uchun bo'sh ro'yxat (D-11: bu xato emas)" deydi va cross-tenant holatini umuman ko'rmaydi. Lekin RLS begona bozorning qatorlarini baribir bo'shatadi — ya'ni A bozorining admini B ning rasta ID'sini so'rasa javob "obyekt yo'q" emas, `200 {"items": []}` bo'lardi. Bu enumeratsiya signali (T-02-74 ning bevosita buzilishi) va u JIMGINA sodir bo'lardi: javob strukturaviy jihatdan mutlaqo to'g'ri ko'rinadi.
- **Fix:** `AssignmentRepository.stall_exists()` qo'shildi va router uni `list_for_stall()` dan OLDIN chaqiradi; topilmasa 404 `not_found`. `StallRepository.detail()` ATAYIN chaqirilmadi — u uchta `LATERAL` bilan butun kartochkani yig'adi, bu yerda esa kerak bo'lgan yagona javob "bormi?".
- **Files modified:** `services/core-api/app/repositories/vendor_repo.py`, `services/core-api/app/api/v1/assignments.py`
- **Verification:** **Sabotaj #4** — darvoza olib tashlanganda AYNAN 2 test yiqildi (`test_cross_tenant_stall_or_vendor_returns_404` va matritsaning shu marshruti, xato matni literal `200 — {"items":[]}`); `test_cross_tenant_is_indistinguishable_from_unknown_id` esa YASHIL qoldi, ya'ni u bu teshikni umuman ushlamaydi
- **Committed in:** `0df8137`

**6. [Rule 2 - Missing Critical] Cross-tenant 404 ham o'qish auditiga tushishi mumkin edi**

- **Found during:** Task 3
- **Issue:** Reja `test_forbidden_read_is_not_audited` ni (403) belgilaydi, lekin CROSS-TENANT 404 holatini audit nuqtai nazaridan umuman ko'rmaydi. Ikkalasi bir xil sinfdagi yolg'on dalil: 404 olgan so'rov hech narsani o'qimagan, ya'ni jurnaldagi "A admini B ning sotuvchisini ko'rdi" yozuvi nizoni hal qilayotgan odamni chalg'itardi — va bu 403 holatidan ham nozikroq, chunki 404 yo'li huquq darvozasidan MUVAFFAQIYATLI o'tadi (A adminida `VENDOR_VIEW` bor).
- **Fix:** `test_cross_tenant_vendor_returns_404` ga to'rtinchi assertion qo'shildi — `read` yozuvlari soni O'ZGARMAGANI.
- **Files modified:** `tests/integration/test_vendors_api.py`
- **Verification:** **Sabotaj #2** (ikkala audit qatlami birga buzildi) — bu test AYNAN shu assertionda yiqildi (`assert 1 == 0`), ya'ni u haqiqiy yuk ko'taruvchi darvoza
- **Committed in:** `7d9c4cf`

**7. [Rule 1 - Bug] `PATCH /assignments/{id}` DTO docstringi mavjud bo'lmagan marshrutga ishora qilardi**

- **Found during:** Task 2
- **Issue:** `AssignmentCloseRequest` (02-08) docstringi `POST /assignments/{id}/close` deydi, reja `<interfaces>` esa `PATCH /api/v1/assignments/{assignment_id}` ni belgilaydi. Ikkinchisi aniqroq spetsifikatsiya va u amalga oshirildi; docstring esa mavjud bo'lmagan endpointga ishora qilib qolardi va keyingi o'qiyotgan odam uni qidirardi.
- **Fix:** Docstring `PATCH` yo'liga to'g'rilandi va `from_date` ning maydonlar orasida NEGA yo'qligi qo'shildi (uni tahrirlash o'tmishdagi qarz egaligini ko'chirardi).
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** OpenAPI'da `/api/v1/assignments/{assignment_id}` faqat `PATCH` bilan
- **Committed in:** `0df8137`

**8. [Rule 1 - Bug] Seed sotuvchisining "bugungi rastalar soni" KALENDARGA bog'liq edi**

- **Found during:** Task 3
- **Issue:** Reja `test_two_stalls_can_share_one_vendor` uchun manba belgilamaydi va tabiiy tanlov — seed sotuvchisi. Lekin `A_VENDOR_PHONES[0]` egasida `HANDOVER_START` (2026-08-01) dan boshlanadigan seed davri bor va u BUGUN ochiq: test ikkita rasta biriktirib `stall_count == 2` kutgan, javob esa **3** bo'lgan. Bundan tashqari `HANDOVER_DAY` (2026-08-10) kelganda o'sha sanoq yana o'zgaradi — ya'ni test kalendar bo'yicha ikki marta sinardi (02-07 deviatsiya #1 bilan bir xil sinf).
- **Fix:** `_new_vendor()` yordamchisi — test o'zi TOZA sotuvchi yaratadi; sabab docstringda literal yozilgan ("dastlabki yozuvda u aynan shunday `3 != 2` bilan yiqildi"). Boshqa testlar seed sotuvchisini ishlatishda davom etadi, chunki ular BOSHQA (bo'sh) rastalar ustida ishlaydi va sanoqqa qaramaydi.
- **Files modified:** `tests/integration/test_assignments_api.py`
- **Verification:** Test yashil; `test_vendor_list_includes_stall_codes` ham AYNAN shu yo'ldan (toza sotuvchi) yozilgan
- **Committed in:** `7d9c4cf`

---

**Total deviations:** 8 auto-fixed (3 blocking, 3 missing-critical, 2 bug). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Birorta yangi jadval, migratsiya yoki paket qo'shilmadi (`alembic_version` `0010` bo'lib qoladi) va rejadan tashqari endpoint ochilmadi. YAGONA qamrov kengaytmasi — `MARKET_ERROR_CODES` ga bitta kod (`invalid_period`, 20 → 21) va u frontend ko'zgusining qarzini bittaga oshiradi. #1, #2, #4 va #7 rejaning O'Z bandlari orasidagi ziddiyatlar (mavjud bo'lmagan DTO'lar, private yordamchi, eskirgan docstring); #3, #5 va #6 reja ko'rmagan uchta yo'lni yopadi va ikkitasi sabotaj bilan o'lchandi; #8 seed bilan kalendar orasidagi haqiqiy bog'liqlik.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| OpenAPI'dagi yangi yo'llar | ✅ 5 yo'l / **7 marshrut** |
| `GET /vendors` — o'qish auditi | ✅ AYNAN 1 qator, `source = app`, `reason = vendor_view` |
| `filters` ichida `cursor` / `limit` | ✅ YO'Q / BOR (so'rov ATAYIN kursor bilan yuborildi) |
| `result_count` javobdagi element soni bilan | ✅ teng |
| `GET /vendors/{id}` auditi | ✅ AYNAN 1 qator, `filters = {"vendor_id": ...}`, `result_count = 1` |
| Kassir `GET /vendors` | ✅ **403** `forbidden`, `read` yozuvlari soni O'ZGARMADI |
| A tokeni + B sotuvchisi | ✅ **404** `not_found`, `status != 403` alohida, `read` yozuvi YO'Q |
| Takroriy telefon (shu bozorda) | ✅ **409** `vendor_phone_taken` |
| AYNI telefon boshqa bozorda | ✅ **201**, ikkinchi ALOHIDA `id` (nazorat) |
| `"90 123 45 67"` | ✅ `+998901234567` — javobda ham, keyingi `GET` da ham |
| Yaroqsiz telefon (`"12345"`) | ✅ **422** |
| `GET /vendors?limit=1` uch sahifa | ✅ takror YO'Q, tartib to'liq ro'yxat bilan bir xil, oxirida `next_cursor = null` |
| `stall_codes` tartibi (4 rasta) | ✅ `3, 7, 55, 100` (matn tartibi `100, 3, 55, 7` bo'lardi) |
| `stall_count` | ✅ 4 (kodlar ro'yxati bilan mos) |
| `PATCH {"full_name": ...}` | ✅ telefon O'ZGARMADI |
| Direktor `GET /vendors` / `POST /vendors` | ✅ **200** (nazorat) / **403** `forbidden` |
| Qo'shni davrlar `[D, D+10)` + `[D+10, D+20)` | ✅ ikkalasi **201** (nazorat), tarixda 2 element |
| Qoplanuvchi davr | ✅ **409** `assignment_period_overlaps`; javobda `duplicate key` matni YO'Q |
| Bitta sotuvchi — ikkita rasta | ✅ ikkalasi **201**, `stall_count = 2` |
| Ochiq davrni yopish | ✅ **200**, `to_date` javobda VA `GET` da to'ldirilgan |
| Yopilgan davrni qayta yopish | ✅ **409** `assignment_not_open`, `status != 404` alohida |
| Almashinuv: `GET /stalls/{id}` bugun | ✅ YANGI sotuvchi |
| Almashinuv: tarix tartibi | ✅ yangi davr birinchi (`to_date = null`), eskisining `to_date` = almashinuv kuni |
| Almashinuv: DB `period @> :kun` | ✅ AYNAN **1** qator, yangi sotuvchiniki |
| Davr yopilishi auditi | ✅ AYNAN 1 `update`, `source = db_trigger`, `changed_keys` da `period`, `old != new` |
| Biriktirilmagan rasta tarixi | ✅ **200**, `items = []` |
| Bo'shliq kuni | ✅ `vendor_id = null`, LEKIN tarix bo'sh EMAS (1 element) |
| `to_date == from_date` / `to_date < lower(period)` | ✅ ikkalasi **422** `invalid_period` |
| Begona rasta / begona sotuvchi / begona rasta tarixi | ✅ uchalasi **404**, har birida `status != 403` alohida |
| Direktor `POST /assignments` / `GET .../assignments` | ✅ **403** / **200** (nazorat) |
| `grep -c 'daterange(\|"[)"'` (`assignments.py`) | ✅ **0** |
| `grep -c 'daterange(\|Range('` (`vendor_repo.py`) | ✅ **1** — faqat modul docstringidagi «bu yerda YO'Q» bandi |
| `grep -c write_app_audit` (`vendors.py` / `assignments.py`) | ✅ **0** / **0** |
| `grep -c 'payload.market_id\|body.market_id'` | ✅ **0** (ikkala routerda) |
| `audit_read` ishlatilishi | ✅ faqat `VendorReadIntentDep` (103-qator) va u faqat ikkala `GET` imzosida |
| `MARKET_ERROR_CODES` uzunligi | ✅ **21** (20 + `invalid_period`) |
| Cross-tenant matritsasi | ✅ 29 → **36** marshrut (17 obyekt marshruti); `EXEMPT_ROUTES` uzunligi O'ZGARMADI (**14**) |
| `PARAM_FILLERS` / `BODY_FILLERS` | ✅ 8 / 15 |
| `alembic_version` | ✅ **0010** (sxemaga tegilmadi) |

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 732 testning har birida.
- **`docker compose run` ichida `python -c` uchun `tests.tenancy` paketi topilmaydi** — `pythonpath` faqat pytest konfiguratsiyasida. Bir martalik o'lchovlar uchun `sys.path.insert(0, '/app')` qo'shildi; mahsulot kodiga ta'siri yo'q.
- **`ruff format` bitta manba faylini qayta formatladi** (ikkita uzun chaqiruv bir qatorga sig'di) — qator uzunligi darajasida.
- **`VENDOR_STALL_CODES_MAX` chegarasining O'ZI test bilan qamralmagan** (21 rasta yaratish talab qilinardi). Ro'yxat va sanoq mustaqilligi struktura darajasida (ikki `LATERAL`) va u docstringda hujjatlangan; chegaraning kesish xulqi esa faqat kod ko'rigi bilan tekshirilgan. Pastdagi "Known Stubs" jadvalida ochiq qarz sifatida qayd etilgan.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan va birorta DTO bo'sh qolmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `frontend/src/lib/api-types.ts::ERROR_CODES` da 2-fazaning **21** kodi YO'Q | 02-13 / 02-14 | Bu reja BITTA kod qo'shdi (`invalid_period`), ya'ni qarz 20 dan 21 ga o'sdi |
| `VENDOR_STALL_CODES_MAX` kesish xulqi test bilan qamralmagan | — | 21 rasta talab qiladi; ikki `LATERAL` strukturasi `stall_count` ni chegaradan MUSTAQIL qiladi va bu sabotaj #6 da bilvosita ko'rindi (sanoq o'zgarmadi) |
| `GET /stalls/{id}/assignments` va `GET /stalls/{id}` `vendor_name`/`phone` ni AUDITSIZ qaytaradi | 02-17 yoki keyingi faza qarori | Fazaning mavjud chegarasi: `audit_read` REESTRNI varaqlashni qamraydi, rasta kartochkasidagi yondosh sotuvchi ma'lumotini emas. Pastdagi "Threat Flags" da ochiq |
| Sotuvchi UI'si (reestr + biriktirish oqimi) | 02-15 | Server tomonidagi barcha darvozalar tayyor va qulflangan |
| `GET /vendors?q=` ning telefon bo'yicha qidiruvi test bilan qamralmagan | 02-15 | `q` ning ikkala tarmog'i ham bitta SQL shartida; ism prefiksи kursor testida bilvosita ishlatiladi |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA bitta yuza aniqlandi va u YANGI emas — mavjud chegaraning ochiq qayd etilishi:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: information_disclosure | `services/core-api/app/api/v1/assignments.py` | `GET /stalls/{stall_id}/assignments` javobida `vendor_name` bor (shaxsiy ma'lumot), lekin `audit_read` YO'Q — reja `<interfaces>` uni `MARKET_DATA_VIEW` deb belgilaydi. Bu 02-08 dagi `GET /stalls/{id}` bilan BIR XIL holat (u `phone` ni ham auditsiz qaytaradi), ya'ni yuza kengaymadi. Faqat yangi marshrutga audit qo'yish qamrovni NOTEKIS qilardi; qaror butun faza uchun bir marta ko'rib chiqilishi kerak |

| Threat ID | Holat |
|-----------|-------|
| T-02-70 | mitigate — `audit_read(TABLE_VENDORS, reason="vendor_view")` ikkala `GET` da; ro'yxat ham, yakka kartochka ham qamralgan (`test_vendor_detail_read_is_audited` — "bittalab varaqlash" yo'li) |
| T-02-71 | mitigate — IKKI mustaqil qatlam; **sabotaj bilan o'lchandi**: bittasini buzish testni qizartirmaydi, ikkalasini birga buzish `test_forbidden_read_is_not_audited` va `test_cross_tenant_vendor_returns_404` ni yiqitadi |
| T-02-72 | mitigate — `fn_audit_row()` `period` o'zgarishini `old→new` bilan yozadi (`test_assignment_change_is_audited`, AYNAN 1 qator, `source = db_trigger`); qulaylik endpointi ATAYIN yo'q; yopilgan davrni qayta ochish yo'li YO'Q (`assignment_not_open`, sabotaj #5 bilan o'lchandi) |
| T-02-73 | mitigate — `EXCLUDE USING gist` → `23P01` → 409; ilova tekshiruvi ATAYIN qo'shilmadi (parallel yozuvda yetarli emas); qo'shni davr NAZORAT holati bilan |
| T-02-74 | mitigate — composite FK → `23503` → **404** (yozuv yo'li) va `stall_exists()` → 404 (o'qish yo'li, deviatsiya #5); uchala yo'lda ham `status != 403` alohida |
| T-02-75 | mitigate — 409 javobida faqat `detail` kodi; `assert "duplicate key" not in response.text` alohida assertion bilan qulflangan |
| T-02-76 | mitigate — `require_permission(VENDOR_MANAGE)`; direktor ikkala domenda ham 403 oldi, nazorat `GET` → 200 |
| T-02-77 | accept (aniqlangan) — telefon javobda TO'LIQ va bu test bilan TALAB qilinadi (`test_phone_is_normalized_to_e164`); himoya RLS + `VENDOR_VIEW` + o'qish auditi |
| T-02-78 | mitigate — `VENDOR_PAGE_SIZE_MAX = 200` (`Field(ge=1, le=...)`) + `stall_codes` uchun `LIMIT 20`; sanoq chegaradan MUSTAQIL (ikki alohida `LATERAL`) |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (119 fayl, 118 manba) |
| 2 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida) |
| 3 | `npm run test:tenancy` (`pytest tests/tenancy`) | ✅ **268 passed** (02-09 dagi 232 + 36) |
| 4 | `npm run test` (`pytest -q`) | ✅ **732 passed** (02-09 dagi 672 + 60) |
| 5 | `app.openapi()` da yangi yo'llar | ✅ 5 yo'l / 7 marshrut |
| 6 | Sabotaj o'lchovlari (6 ta) | ✅ beshtasida AYNAN kutilgan test(lar) yiqildi; oltinchisi (yolg'iz e'lon tartibi) ATAYIN yashil qoldi va sabab hujjatlashtirildi |
| 7 | Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `require_permission` `Depends` i `audit_read` dan OLDIN | ✅ ikkala `GET` imzosida |
| `GET /vendors` dan keyin `read`/`vendors`/`vendor_view` yozuvi | ✅ |
| Kassir 403 → YANGI `read` yozuvi YO'Q | ✅ |
| `intent.filters` da `cursor` YO'Q, `limit` BOR | ✅ (so'rov kursor bilan yuborildi) |
| Takroriy telefon → 409 `vendor_phone_taken` | ✅ |
| Noto'g'ri telefon → 422 | ✅ |
| Bir xil telefon boshqa bozorda | ✅ 201 (nazorat) |
| `?limit=1` → `next_cursor` va takrorlanmaydigan keyingi sahifa | ✅ 3 sahifa |
| `grep audit_read` faqat `GET` larda | ✅ |
| `ruff check && mypy` exit 0 | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `grep 'daterange(\|"[)"'` (`assignments.py`) | ✅ **0** |
| Qoplanish → 409 `assignment_period_overlaps` | ✅ |
| Qo'shni davr → 201 (nazorat) | ✅ |
| Begona `vendor_id` → 404 (`status != 403`) | ✅ |
| Yopilgan davrni yopish → 409 `assignment_not_open` | ✅ |
| Ochiq davrni yopish → 200 va `GET` da `to_date` to'ldirilgan | ✅ |
| Almashinuv kuni `period @> :d` → yangi sotuvchi | ✅ AYNAN 1 qator |
| Biriktirilmagan rasta → 200 + bo'sh `items` | ✅ |
| OpenAPI'da uchala yo'l | ✅ |
| `pytest tests/tenancy -q` exit 0 | ✅ 268 passed |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_vendors_api.py` ≥10 test | ✅ **12** |
| `test_assignments_api.py` ≥9 test | ✅ **12** |
| `test_forbidden_read_is_not_audited` yashil | ✅ (va sabotaj #2 da AYNAN u qizardi) |
| `test_handover_flow_...` almashinuv kunini yangi sotuvchiga beradi | ✅ uchta mustaqil da'vo bilan |
| `test_two_stalls_can_share_one_vendor` yashil | ✅ (toza sotuvchi bilan — deviatsiya #8) |
| Nazorat holatlari juftidan OLDIN | ✅ `test_same_phone_in_another_market_is_accepted` va `test_adjacent_assignment_is_accepted` ikkalasi ham juftidan oldin |
| `npm run test` exit 0 | ✅ 732 passed |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja sxemaga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi).

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-04]` deb yozgan. MARKET-04 ning **backend yarmi** shu rejada tugadi, lekin u foydalanuvchi ko'radigan qobiliyat sifatida UI'siz to'liq emas: sotuvchilar reestri va biriktirish oqimi 02-15 da quriladi (`02-VALIDATION.md` 02-15-01). Uni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi (02-04…02-09 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-11 (`setup-status` / `activate`) uchun:**

- `AssignmentRepository.stall_exists()` — "rasta shu bozordami?" savolining yengil shakli; faollashtirish to'liqlik tekshiruvi undan foydalanishi mumkin.
- Sotuvchilar soni `SELECT count(*) FROM vendors` bilan olinadi — bu reja bunday agregat qo'shmadi (usta qadamining sanog'i 02-11 ning o'z qarori).

**02-12 (import) uchun:**

- `VendorRepository.create_vendor()` telefonni NORMALLASHTIRMAYDI — u chegarada bo'ladi. Import yo'li `normalize_phone()` ni O'ZI chaqirishi shart (u DTO'dan o'tmaydi), aks holda faylda `901234567` shaklida kelgan raqam boshqa qator sifatida yozilardi.
- `23505` → `vendor_phone_taken` xaritasi tayyor, lekin import D-14 bo'yicha xatolarni YOZISHDAN OLDIN topishi kerak (RLS `DETAIL` ni o'chiradi — Pitfall 4).

**02-13/02-15 (frontend) uchun:**

- `GET /vendors` — `next_cursor` bilan `useInfiniteQuery`; tartib SERVERDA (`full_name`), qayta saralamang.
- `stall_codes` — badge uchun, `stall_count` — haqiqat. Ular TENG BO'LMASLIGI mumkin (yigirmadan ortiq rasta) va UI buni ko'rsatishi kerak.
- Telefon MASKALANMAYDI — bu mahsulot qarori (UI-SPEC §8.6), klientda yulduzcha qo'shmang.
- `invalid_period` — YANGI xato kodi (21-chi). `errors.invalidPeriod` matni "davr oxiri boshidan keyin bo'lishi kerak" ma'nosini berishi kerak; `[)` konvensiyasini foydalanuvchiga tushuntirmang, sanani ERTASI kunga surishni taklif qiling.
- **Almashinuv UI'da IKKI QADAM** va uni bitta tugmaga siqmang: server ataylab ikkita amal talab qiladi (T-02-72). Sana maydoni ikkalasida ham BIR XIL kun bo'lishi kerak — `[)` chegarasi o'sha kunni yangi sotuvchiga beradi.
- `assignment_not_open` — yopilgan davrni tahrirlash tugmasini YASHIRING, lekin server darvozasi BIRINCHI.

**06-hisob-kitob uchun:**

- "Bugun kim biriktirilgan" ta'rifi UCH joyda AYNAN bir xil: `stall_repo._STALL_ROWS`, `stall_repo._MAP_ROWS` va `vendor_repo._VENDOR_ROWS` — hammasi `period @> :day`. Kunlik job to'rtinchi nusxa yozmasin.
- Almashinuv kuni YANGI sotuvchiniki — bu endi API darajasida ham, DB darajasida ham o'lchangan (`test_handover_flow_moves_the_day_to_the_new_vendor` uchala da'vo bilan).
- Bo'shliq kuni `vendor_id: null` beradi va bu ANOMALIYA signali, xato emas (D-11).

**Yangi marshrut qo'shadigan HAR KIM uchun (02-08/02-09 dan meros, endi 7 marshrut bilan qayta tasdiqlangan):**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si**;
3. marshrut TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana;
4. **YANGI (02-10):** marshrut BO'SH ro'yxat qaytarishi mumkin bo'lsa — tenant darvozasi ALOHIDA mavjudlik so'rovi bilan qo'yilsin. Bo'sh javob cross-tenant so'rovda ham "to'g'ri" ko'rinadi va matritsaning 404 da'vosi jimgina bajarilmay qoladi (sabotaj #4 bilan o'lchandi).

## Self-Check: PASSED

- Da'vo qilingan 5 yangi fayl diskda mavjud: `services/core-api/app/repositories/vendor_repo.py`, `services/core-api/app/api/v1/vendors.py`, `services/core-api/app/api/v1/assignments.py`, `tests/integration/test_vendors_api.py`, `tests/integration/test_assignments_api.py`
- Da'vo qilingan 6 o'zgartirilgan fayl `git diff --stat de3ebaf..HEAD` da ko'rinadi
- To'rtala commit git tarixida mavjud: `35e5436`, `0df8137`, `7d9c4cf`, `3e3af21`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only de3ebaf HEAD` bo'sh)
- Oltita sabotajdan keyin fayllar `git checkout -- <fayl>` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
