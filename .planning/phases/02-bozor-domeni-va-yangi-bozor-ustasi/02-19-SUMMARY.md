---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 19
subsystem: security
tags: [audit-read, rbac, fastapi, dependency-graph, introspection, gap-closure, sabotage, d-09]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-08 — `GET /stalls` va `GET /stalls/{id}` marshrutlari, `StallQuery`/`StallListItem`/`StallDetail`; 02-10 — `vendors.py` dagi `audit_read` naqshi (`VendorReadIntentDep`), `GET /stalls/{id}/assignments` va uning `stall_exists()` darvozasi, `test_vendors_api.py` dagi audit uchligi; 02-09 — `tests/tenancy/test_route_coverage.py` dagi marshrut yurishi va `EXEMPT_ROUTES` naqshi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`audit_read()` fabrikasi + `AuditReadIntent` (D-09), `TABLE_STALLS` konstantasi, `require_permission()` fabrikasi, `ROLE_PERMISSIONS` matritsasi, `tests/tenancy/test_cross_tenant.py::all_routes()` yurishi"
provides:
  - "`app/api/v1/stalls.py` — `list_stalls`/`get_stall` uchun o'qish auditi (`reason='stall_view'`) + `VENDOR_VIEW` chegarasi"
  - "`app/api/v1/assignments.py` — `list_stall_assignments` uchun o'qish auditi (`reason='stall_assignments_view'`) + `VENDOR_VIEW`"
  - "`app/deps.py::require_permission` -> `_require.required_permission` introspektsiya tegi"
  - "`app/security/audit.py::audit_read` -> `_dependency.audit_resource` introspektsiya tegi"
  - "`tests/tenancy/test_personal_data_coverage.py` — butun `GET` yuzasini supuruvchi darvoza (8 test)"
  - "`tests/integration/test_personal_data_audit.py` — uchala marshrutning audit isboti + 4 nazorat holati (8 test)"
affects: [02-20, 05-kassir-va-tolovlar, 06-hisob-kitob, 07-telegram-botlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Huquq talabi MARSHRUT DEKORATORIDA (`dependencies=[...]`) — FastAPI uni imzo parametrlaridan OLDIN hal qiladi, ya'ni 403 audit yozuvidan oldin (o'lchandi: graf tartibi `vendor_view` -> `market_data_view`)"
    - "Dependency fabrikasi qaytargan yopilmaga INTROSPEKTSIYA TEGI qo'yiladi — darvoza testi marshrut GRAFINI o'qiydi, manba matnini regex bilan tirnamaydi"
    - "Darvoza testi javob modelini REKURSIV ochadi: shaxsiy maydon deyarli hech qachon yuqori darajada turmaydi (`StallListResponse.items[].vendor_name` — ikki qavat pastda)"
    - "Istisnolar ro'yxati IKKI TOMONLAMA qulflanadi: yo'l hamon mavjudmi VA istisno hamon kerakmi"
    - "Ikki mustaqil talab (audit + huquq) IKKI ALOHIDA testda — sabotaj bilan o'lchanganda ular haqiqatan mustaqil ekani ko'rinadi"
    - "Nusxa olingan marshrut yurishi asl yurish bilan solishtiriladi — nusxaning jimgina ajralib ketishi bloklanadi"

key-files:
  created:
    - tests/integration/test_personal_data_audit.py
    - tests/tenancy/test_personal_data_coverage.py
  modified:
    - services/core-api/app/api/v1/stalls.py
    - services/core-api/app/api/v1/assignments.py
    - services/core-api/app/security/rbac.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/deps.py

key-decisions:
  - "`VENDOR_VIEW` DEKORATORDA, `VendorViewerDep` aliasi orqali imzoda EMAS — dekorator darajasi FastAPI'da kuchliroq kafolat beradi va reja e'lon qilgan alias dead-code bo'lardi"
  - "`intent.filters` `_describe(query)` bilan quriladi (`vendors.py` naqshi), qo'lda yig'ilgan lug'at bilan emas — qo'lda variant yangi filtr qo'shilganda jimgina eskirardi"
  - "`GET /users` va `GET /me` darvozadan ISTISNO qilindi, sabab bilan — birinchisi xodim reestri (`USER_VIEW`), ikkinchisi subyektning O'Z profili; `VENDOR_VIEW` ni ikkinchisiga talab qilish har kassirni o'z ismidan mahrum qilardi"
  - "`PERSONAL_FIELDS` uch nomdan iborat (`vendor_name`/`phone`/`full_name`) — kengaytirish darvozani deyarli har marshrutga yoyib, istisnolar ro'yxatini shishirtirardi"
  - "Introspektsiya teglari `# type: ignore[attr-defined]` bilan — sinf (`__call__` li obyekt) bilan qayta yozish xavfsizlik-kritik darvozaning shaklini o'zgartirardi, `setattr()` esa ruff B010 ga tushardi"
  - "`assignments.py` audit resursi `TABLE_STALLS` (`TABLE_VENDORS` emas) — jurnalni o'qiyotgan odam 'qaysi RASTANING tarixi ko'rildi' savoliga javob izlaydi"
  - "`GET /stalls/map` ATAYIN tegilmadi va bu NAZORAT TESTI bilan qulflandi — darvozaning 'hamma GET ga audit' ga aylanib ketishi bloklangan"

requirements-completed: []

# Metrics
duration: 55min
completed: 2026-08-01
---

# Phase 2 Plan 19: Shaxsiy ma'lumot o'qishining auditi va GET yuzasi darvozasi Summary

**02-VERIFICATION.md ning 4-bo'shlig'i (CR-02, D-09) yopildi: uchala marshrut endi `VENDOR_VIEW` talab qilib har muvaffaqiyatli o'qishni jurnalga yozadi, `TABLE_STALLS` konstantasi o'n yetti reja davomida birinchi marta haqiqiy chaqiruv joyiga ega bo'ldi — va rejadan tashqarida qurilgan qamrov darvozasi butun `GET` yuzasini supurib, `MARKET_DATA_VIEW` ostidagi UCHTA emas, BESHTA shaxsiy-ma'lumotli marshrutni aniqladi hamda ikkita boshqa sinfdagi yuzani (`GET /users`, `GET /me`) sabab bilan ochiq qayd etdi.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 3/3
- **Files:** 7 (2 yaratildi, 5 o'zgartirildi)
- **Testlar:** 890 → **906** (+16: integratsiya +8, tenancy +8)
- **Sabotaj o'lchovlari:** 3/3, uchalasi ham AYNAN kutilgan testni qizartirdi
- **Migratsiya / paket / endpoint:** 0 / 0 / 0 (`alembic_version` `0010` bo'lib qoldi)

## Accomplishments

- **Uchta sabotaj o'lchovi va ularning aniq natijalari:**

  | Sabotaj | Yiqilgan test(lar) | Nazorat |
  |---|---|---|
  | `stalls.py::get_stall` imzosidan `intent: StallReadIntentDep` va uning ikki ishlatilishi olib tashlandi | AYNAN 2: `test_stall_detail_read_is_audited` va `test_personal_data_coverage.py::test_personal_data_routes_declare_read_audit` | qolgan 904 test ✅ — jumladan `test_personal_data_routes_require_vendor_view` YASHIL qoldi (huquq dekoratorda turgani uchun) |
  | `assignments.py` marshrut dekoratoridan `VENDOR_VIEW` bog'liqligi olib tashlandi | AYNAN 1: `test_personal_data_coverage.py::test_personal_data_routes_require_vendor_view` | butun `test_personal_data_audit.py` (8 test) ✅ va `test_personal_data_routes_declare_read_audit` ✅ — audit hamon e'lon qilingan |
  | `PERSONAL_FIELDS` dan `vendor_name` olib tashlandi | AYNAN 1: `test_gate_covers_a_meaningful_number_of_routes` (`assert 3 >= 4`, xato xabarida qolgan uchta yo'l literal sanaladi) | qolgan 7 qamrov testi ✅ — ular kichrayган to'plamda ham to'g'ri ishlayverardi, ya'ni BO'SHASHISHNI faqat shu chegara ushlaydi |

  Uchalasidan keyin fayllar `git checkout -- <fayl>` bilan **bit-ba-bit** tiklandi (`git status` toza, kuzatilmagan fayl qolmadi).

  **Ikkinchi sabotaj bu rejaning eng qimmatli o'lchovi.** U ikki talab HAQIQATAN mustaqil ekanini ko'rsatdi: `VENDOR_VIEW` ni olib tashlash audit testlarining BIRORTASINI qizartirmadi (audit hamon yoziladi, faqat endi uni ko'proq odam ko'ra oladi), qamrov testining esa aynan huquq da'vosini yiqitdi. Agar ikkala talab bitta testda birlashtirilgan bo'lganda, bu farq umuman ko'rinmasdi va "bittasi ikkinchisini qamraydi" degan yolg'on xulosa qolardi.

- **Rejadagi uchta marshrut haqiqiy sonning yarmi bo'lib chiqdi.** Reja `GET /stalls`, `GET /stalls/{id}` va `GET /stalls/{id}/assignments` ni nomma-nom sanaydi va "supurish" ni talab qiladi. Supurish (`app.routes` bo'yicha yurib javob modelini rekursiv ochish) `GET` yuzasidagi **yettita** shaxsiy-maydonli marshrutni topdi:

  | Marshrut | Maydonlar | Holati |
  |---|---|---|
  | `GET /api/v1/stalls` | `vendor_name` | ✅ shu rejada yopildi |
  | `GET /api/v1/stalls/{stall_id}` | `vendor_name`, `phone` | ✅ shu rejada yopildi |
  | `GET /api/v1/stalls/{stall_id}/assignments` | `vendor_name` | ✅ shu rejada yopildi |
  | `GET /api/v1/vendors` | `full_name`, `phone` | ✅ 02-10 da allaqachon qamralgan |
  | `GET /api/v1/vendors/{vendor_id}` | `full_name`, `phone` | ✅ 02-10 da allaqachon qamralgan |
  | `GET /api/v1/users` | `full_name`, `phone` | ⚠ ISTISNO — xodim reestri, `USER_VIEW`; "Threat Flags" da |
  | `GET /api/v1/me` | `full_name`, `phone` | ⚠ ISTISNO — subyektning O'Z profili |

  `GET /api/v1/markets`, `GET /api/v1/audit`, `GET /api/v1/auth/me`, `GET /api/v1/calendar`, `GET /api/v1/categories`, `GET /api/v1/tariffs`, `GET /api/v1/zones`, `GET /api/v1/stalls/map`, `GET /api/v1/markets/{id}/setup-status` va `GET /api/v1/imports/template` — shaxsiy maydonsiz (`MarketListItem` da faqat `name`/`timezone`, `MeResponse` da esa `phone` UMUMAN yo'q, bozor rekvizitidagi maydon esa `contact_phone` deb ataladi va u tashkilotniki).

- **FastAPI ning e'lon tartibi grafda O'LCHANDI, taxmin qilinmadi.** Marshrut grafini yurgan o'lchov `GET /stalls` uchun huquq teglarini AYNAN shu tartibda qaytardi: `['vendor_view', 'market_data_view']` — ya'ni dekorator darajasidagi `dependencies=[...]` haqiqatan `dependant.dependencies` ning BOSHIGA qo'yiladi va imzo parametrlaridan oldin hal bo'ladi. Bu T-02-147 mitigatsiyasining bevosita dalili: 403 olgan so'rov `audit_read` gacha yetib bormaydi va u `test_forbidden_read_is_not_audited` bilan xulq darajasida ham qulflangan.

- **Darvoza o'zining bo'shab qolishiga qarshi UCH qavat bilan himoyalangan.** Bu sinf test (marshrut grafini avtomatik yuradigan meta-test) eng jimgina yolg'on-yashil manbai: u istisno ko'tarmasdan shunchaki kamroq narsa topadi va yashil qolaveradi. Uchta qulf: (1) `test_walk_matches_the_shared_route_walker` — nusxa olingan yurish `test_cross_tenant.all_routes()` bilan AYNAN bir xil (metod, yo'l) to'plamini berishi shart, u esa o'z navbatida `app.openapi()` bilan solishtirilgan; (2) `test_gate_covers_a_meaningful_number_of_routes` — kamida 4 marshrut topilishi shart (sabotaj #3 da o'lchandi); (3) `test_map_route_is_free_of_the_requirement` — nazorat marshruti hamon topilishi va talabdan ozod bo'lishi shart.

- **`ROLE_PERMISSIONS` invariantining O'ZI test bilan qulflandi.** Reja "matritsani o'zgartirmang, chunki `MARKET_DATA_VIEW` egasining hammasida `VENDOR_VIEW` bor" deydi — bu premissa bugun to'g'ri, lekin kelajakda kimdir yangi "faqat ko'rsin" rolini qo'shsa jimgina buzilardi va foydalanuvchi buni faqat 403 ko'rganda bilardi. `test_market_data_view_holders_already_have_vendor_view` shu holatni AYNAN matritsa faylida to'xtatadi va qarorni ONGLI qiladi. Bu reja `<action>` da yo'q edi.

- **`stall_map` ga tegilmagani NAZORAT TESTI bilan qulflandi (ikki joyda).** `test_map_read_is_not_audited` xulq darajasida (200 keladi, `read` yozuvlari soni O'ZGARMAYDI) va `test_map_route_is_free_of_the_requirement` struktura darajasida. Ularsiz butun ish "audit hamma joyda" holatidan ajralmasdi va `audit.py:240-245` da ATAYIN rad etilgan blanket-middleware jimgina qaytib kelgan bo'lardi.

## Task Commits

1. **Task 1: `stalls.py` — ikkala shaxsiy-ma'lumotli marshrutga o'qish auditi va `VENDOR_VIEW` chegarasi** — `3b9d5f9` (feat)
2. **Task 2: `assignments.py` marshruti, RBAC docstringlari va introspektsiya teglari** — `b1c2286` (feat)
3. **Task 3: Audit yozuvining isboti va butun `GET` yuzasini supuruvchi darvoza** — `4c72da2` (test)

## Files Created/Modified

**Yaratildi**

- `tests/integration/test_personal_data_audit.py` (8 test) — to'rtta ijobiy da'vo (`GET /stalls`, `q` bo'yicha qidiruv, `GET /stalls/{id}`, `GET /stalls/{id}/assignments`) va **to'rtta nazorat holati** (403 kassir, noma'lum ID 404, cross-tenant 404 — ikkala yo'l bilan, `GET /map`). Reja ≥7 talab qiladi.
- `tests/tenancy/test_personal_data_coverage.py` (8 test) — `app.routes` bo'yicha yurish, javob modelining REKURSIV ochilishi, bog'liqlik grafi bo'yicha introspektsiya teglarini o'qish, ikki mustaqil da'vo, matritsa invarianti va ikki tomonlama qulflangan istisnolar.

**O'zgartirildi**

- `services/core-api/app/api/v1/stalls.py` — `StallReadIntentDep`, `_describe()`, ikkala marshrut dekoratorida `VENDOR_VIEW`, modul docstringiga D-09 bandi va `GET /map` ning istisno sababi.
- `services/core-api/app/api/v1/assignments.py` — `AssignmentReadIntentDep`, marshrut dekoratorida `VENDOR_VIEW`, "AUDIT BU YERDA YOZILMAYDI" bandi ANIQLASHTIRILDI (o'chirilmadi): u hamon `POST`/`PATCH` haqida to'g'ri, `GET` esa endi alohida hodisa sifatida yoziladi.
- `services/core-api/app/security/rbac.py` — `MARKET_DATA_VIEW` va `VENDOR_VIEW` docstringlari kod bilan moslashtirildi; `ROLE_PERMISSIONS` matritsasining O'ZI o'zgarmadi.
- `services/core-api/app/security/audit.py` — `_dependency.audit_resource` introspektsiya tegi (+ nima uchun bor va nima uchun regex emasligi).
- `services/core-api/app/deps.py` — `_require.required_permission` introspektsiya tegi (+ tanlangan tiplash variantining sababi).

## Decisions Made

- **`VENDOR_VIEW` marshrut DEKORATORIDA, reja e'lon qilgan `VendorViewerDep` aliasi orqali imzoda EMAS.** Reja `<action>` da ikkalasini ham sanaydi, lekin ular bir-biriga zid: alias imzoda ishlatilsa u oddiy imzo parametri bo'lib qolardi va `audit_read` dan oldin turishi FAQAT e'lon tartibiga tayanardi. Dekorator darajasi kuchliroq — FastAPI ularni `dependant.dependencies` ning boshiga qo'yadi va bu qoida imzo qayta tartiblanganda ham buzilmaydi. Aliasni faqat e'lon qilib ishlatmaslik esa dead-code bo'lardi va uchta marshrut dekoratorida `Permission.VENDOR_VIEW` literal turgani qabul mezonining grep talabini ham bajaradi.
- **`intent.filters` `model_dump()` bilan quriladi.** Reja "`query` ning bo'sh bo'lmagan maydonlaridan `str` qiymatli lug'at" deydi va maydonlarni `zone_id`/`category_id` deb sanaydi — amaldagi `StallQuery` da ular `zone`/`category`. Qo'lda yig'ilgan lug'at aynan shunday jimgina eskirardi (02-10 deviatsiya #1 bilan bir xil sinf). `model_dump(mode="json", exclude_none=True, exclude={"cursor"})` `vendors.py` va `audit.py` dagi naqshning aynan o'zi va yangi filtr qo'shilganda o'zi ergashadi.
- **`GET /users` va `GET /me` istisno qilindi va sabab kodda yozildi.** Ikkalasi ham `phone` + `full_name` qaytaradi, ya'ni supurish ularni topadi. Lekin `/me` — subyektning O'Z profili (`VENDOR_VIEW` talab qilinsa kassir va nazoratchi o'z ismini ko'ra olmay qolardi — ikkalasida ham bu huquq yo'q), `/users` esa XODIM reestri boshqa huquq ostida. Istisnolar `test_route_coverage.py::EXEMPT_ROUTES` naqshi bo'yicha sabab bilan yoziladi va IKKI tomonlama qulflangan.
- **Audit resursi `TABLE_STALLS`, `TABLE_VENDORS` emas** — uchala marshrutda ham. Jurnal filtri `table_name = 'stalls'` bilan rasta yuzasidagi butun o'qish tarixi bitta so'rovda ko'rinadi. `reason` esa uchta qiymatni ajratadi: `stall_view`, `stall_assignments_view`, `vendor_view`.
- **Introspektsiya teglari `# type: ignore[attr-defined]` bilan tiplandi.** Uch variant ko'rildi: (a) `Protocol` + `cast` — baribir bitta `ignore` talab qilardi va qo'shimcha abstraksiya qo'shardi; (b) yopilmani `__call__` li sinfga aylantirish — tipni toza qilardi, lekin xavfsizlik-kritik darvozaning butun shaklini o'zgartirardi va `Depends` keshlash xulqiga tegib ketishi mumkin edi; (c) `setattr()` — ruff `B010` ga tushardi. Eng kichik va eng ko'rinadigan variant tanlandi; sabab ikkala chaqiruv joyida ham izohda.
- **Rejaning "≥7 test" talabi 8 ta bilan bajarildi** — qo'shimcha test cross-tenant 404 ni IKKALA yo'l bilan (`/{id}` va `/{id}/assignments`) tekshiradi, chunki ular 404 ni HAR XIL mexanizm bilan beradi (`detail() is None` va `stall_exists()`) va bittasi ikkinchisining isboti emas.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reja `VendorViewerDep` aliasini ham, dekorator `dependencies` ni ham talab qilardi — ikkalasi bir vaqtda ma'nosiz**

- **Found during:** Task 1
- **Issue:** Reja `<action>` "Aliaslar ... `VendorViewerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]`" deydi va o'sha xatboshida "Dekoratorga `dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))]` qo'shiladi" deydi. Alias imzoda ishlatilmasa u dead-code bo'lardi; ishlatilsa esa dekorator talabi ortiqcha bo'lib, T-02-147 kafolati kuchsiz mexanizmga (imzo tartibiga) ko'chardi.
- **Fix:** Alias e'lon qilinmadi; uchala marshrutda `dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))]` inline yozildi. Sabab ikkala modul docstringida.
- **Files modified:** `services/core-api/app/api/v1/stalls.py`, `services/core-api/app/api/v1/assignments.py`
- **Verification:** Graf o'lchovi huquq teglarini `['vendor_view', 'market_data_view']` tartibida qaytardi (dekorator BIRINCHI); `test_forbidden_read_is_not_audited` yashil
- **Committed in:** `3b9d5f9`, `b1c2286`

**2. [Rule 1 - Bug] Reja `StallQuery` ning mavjud bo'lmagan maydon nomlarini sanaydi**

- **Found during:** Task 1
- **Issue:** Reja `intent.filters` ni "`zone_id`, `category_id`, `status`, `q`, `limit`, `cursor` bor-yo'qligi" dan qurishni buyuradi. `app/schemas.py::StallQuery` da esa maydonlar `q`, **`zone`**, **`category`**, `status`, `limit`, `cursor`. Rejaning matnini so'zma-so'z bajarish `AttributeError` berardi yoki (qo'lda `dict` yig'ilganda) ikkita filtr jurnalga UMUMAN tushmasdi.
- **Fix:** `_describe()` yordamchisi `vendors.py` dagi naqsh bilan yozildi: `query.model_dump(mode="json", exclude_none=True, exclude={"cursor"})`. Nomlar modeldan o'zi keladi.
- **Files modified:** `services/core-api/app/api/v1/stalls.py`
- **Verification:** `test_stall_list_read_is_audited` `filters.limit` ni topadi; `test_search_text_is_recorded_in_the_read_row` `filters.q` ni topadi va `cursor` YO'Qligini alohida tekshiradi
- **Committed in:** `3b9d5f9`

**3. [Rule 2 - Missing Critical] Reja supurishning `GET /users` va `GET /me` ni topishini ko'rmagan**

- **Found during:** Task 3
- **Issue:** Reja `PERSONAL_FIELDS` ga `full_name` va `phone` ni kiritadi va "shaxsiy maydonli marshrutlar soni ≥ 4" deydi, lekin qaysi marshrutlar chiqishini sanamaydi. Amalda supurish YETTITA marshrut topadi: rejaning beshtasi ustiga `GET /users` (xodim reestri) va `GET /me` (o'z profili). Ularga `VENDOR_VIEW` talabini qo'yish `GET /me` ni **har kassir va nazoratchi uchun 403** qilardi — ya'ni reja so'zma-so'z bajarilganda mahsulot buzilardi va sabab test faylida ko'rinmasdi.
- **Fix:** `EXEMPT_ROUTES` (yo'l -> sabab) qo'shildi, ikkalasi uchun sabab literal yozildi. Istisno ro'yxati IKKI tomonlama qulflandi: `test_exempt_routes_still_exist_and_have_reasons` (eskirgan yozuv qolmasin) va `test_every_exemption_is_load_bearing` (ortiqcha yozuv qolmasin — marshrut shaxsiy maydonni qaytarishni to'xtatgan bo'lsa istisno olib tashlanishi shart).
- **Files modified:** `tests/tenancy/test_personal_data_coverage.py`
- **⚠ Qarz:** `GET /users` HAMON o'qish auditisiz xodim telefonlarini qaytaradi — pastdagi "Threat Flags" da ochiq qayd etilgan
- **Committed in:** `4c72da2`

**4. [Rule 2 - Missing Critical] `ROLE_PERMISSIONS` invarianti hech qayerda qulflanmagan edi**

- **Found during:** Task 3
- **Issue:** Butun rejaning xavfsizligi "bugungi matritsada `MARKET_DATA_VIEW` egasining hammasida `VENDOR_VIEW` ham bor" premissasiga tayanadi. Reja buni tekshirilgan fakt sifatida beradi va matritsani tegmaslikni buyuradi — lekin premissaning O'ZI hech qayerda qulflanmagan. Kelajakda kimdir `MARKET_DATA_VIEW` li yangi rol qo'shsa, `GET /stalls` o'sha rol uchun JIMGINA 403 bo'lardi va sabab `stalls.py` da ham, `rbac.py` da ham ko'rinmasdi.
- **Fix:** `test_market_data_view_holders_already_have_vendor_view` qo'shildi. U matritsani O'ZGARTIRMAYDI — faqat "o'zgartirish xavfsiz edi" da'vosini qulflaydi va kelajakdagi qarorni ongli qiladi (docstringda ikkala yo'l ham yozilgan).
- **Files modified:** `tests/tenancy/test_personal_data_coverage.py`
- **Verification:** Test yashil; matritsa `git diff` da o'zgarmagan
- **Committed in:** `4c72da2`

**5. [Rule 3 - Blocking] Marshrut yurishi hujjat marshrutlarida `AttributeError` berardi**

- **Found during:** Task 3
- **Issue:** `app.routes` da Starlette avtomatik qo'shadigan to'rtta marshrut bor (`/api/docs`, `/redoc`, `/api/openapi.json`, `/docs/oauth2-redirect`). Ular `starlette.routing.Route` va ularda na `response_model`, na `dependant` bor. Birinchi urinishda yurish ularni filtrlab tashladi — natijada nusxa `all_routes()` bilan solishtiruvchi test yiqildi (to'rtta yo'l "faqat u yerda" bo'lib chiqdi), ya'ni himoya qulfining O'ZI ishladi.
- **Fix:** `_walk()` FILTRSIZ qilindi (asl yurish bilan aynan bir xil), filtr chaqiruvchiga (`get_routes()`) ko'chirildi va `APIRoute` tekshiruvi qo'shildi. Sabab `get_routes()` docstringida literal yozilgan.
- **Files modified:** `tests/tenancy/test_personal_data_coverage.py`
- **Verification:** `test_walk_matches_the_shared_route_walker` yashil — ikkala yurish 43+ marshrutda AYNAN mos
- **Committed in:** `4c72da2`

**6. [Rule 1 - Bug] `rbac.py` docstringi qabul mezonining o'z grep darvozasiga tushardi**

- **Found during:** Task 2
- **Issue:** Yangi `MARKET_DATA_VIEW` docstringi eski da'voni TARIXIY kontekst sifatida keltirgan edi ("Ilgari bu docstring «...QAMRAMAYDI» deb yozgan"). Qabul mezoni esa `grep -v '^\s*#' rbac.py | grep -c "QAMRAMAYDI"` = 0 talab qiladi — ya'ni sabab yozilgan holda darvoza o'z-o'ziga qarshi turardi. Xuddi shu sinf muammo `ROLE_PERMISSIONS` mezonida ham chiqdi (docstring identifikatorni matnda tilga olgani uchun `git diff | grep -c` 1 berdi).
- **Fix:** Ikkala jumla ham ma'nosini saqlagan holda qayta yozildi (literal atama va literal identifikator olib tashlandi, mazmun qoldi). `stalls.py` dagi `# =====` izoh bloki naqshi (02-08 da o'rnatilgan qoida — grep darvozasi bilan to'qnashadigan atamani izoh bloki ichida saqlash) bu yerda ishlamasdi, chunki matn DOCSTRING ichida bo'lishi kerak edi.
- **Files modified:** `services/core-api/app/security/rbac.py`
- **Verification:** `grep -c "QAMRAMAYDI"` = **0**; `git diff --unified=0 | grep -c "^[+-].*ROLE_PERMISSIONS"` = **0**
- **Committed in:** `b1c2286`

---

**Total deviations:** 6 auto-fixed (2 blocking, 2 missing-critical, 2 bug). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Birorta jadval, migratsiya, paket yoki endpoint qo'shilmadi; `ROLE_PERMISSIONS` va `frontend/src/lib/rbac.ts` tegilmadi; birorta rolning amaldagi kirish darajasi o'zgarmadi. #1, #2 va #6 rejaning O'Z bandlari orasidagi ziddiyatlar (dead-code alias, mavjud bo'lmagan maydon nomlari, o'z grep darvozasiga tushadigan izoh); #3 va #4 reja ko'rmagan ikkita xavfni yopadi va ikkalasi ham mahsulotni buzilishdan saqladi; #5 — yangi meta-testning o'z qulfi ishlagan holat.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (134 fayl, 132 manba) |
| `npm run test` (`pytest -q`) | ✅ **906 passed** (890 + 16) |
| `npm run test:tenancy` (`pytest tests/tenancy`) | ✅ **317 passed** (309 + 8) |
| `pytest tests/integration/test_personal_data_audit.py` | ✅ **8 passed** (reja ≥7 talab qiladi) |
| `pytest tests/tenancy/test_personal_data_coverage.py` | ✅ **8 passed** |
| `pytest tests/integration/test_stall_registry.py` | ✅ 18 passed (mavjud reestr testlari qizarmadi) |
| `pytest tests/integration/test_assignments_api.py` | ✅ 12 passed |
| `pytest tests/unit/test_rbac_matrix.py` | ✅ 13 passed |
| Supurish topgan shaxsiy-maydonli `GET` marshrutlari | ✅ **7** (5 qamrovda + 2 istisno) |
| Darvoza QAMRAYDIGAN marshrutlar soni | ✅ **5** (chegara 4) |
| `GET /stalls` graf tartibi (huquq teglari) | ✅ `['vendor_view', 'market_data_view']` — dekorator BIRINCHI |
| `GET /stalls` audit tegi | ✅ `['stalls']` |
| `GET /stalls/map` audit tegi | ✅ **`[]`** (nazorat) |
| `GET /stalls` — o'qish auditi | ✅ AYNAN 1 qator, `source = app`, `reason = stall_view` |
| `GET /stalls?q=Karimova` | ✅ `filters.q = "Karimova"`, `cursor` YO'Q |
| `GET /stalls/{id}` auditi | ✅ `filters = {"stall_id": ...}`, `result_count = 1`, javobda `phone` bor |
| `GET /stalls/{id}/assignments` auditi | ✅ `reason = stall_assignments_view`, `result_count` = javob elementlari soni |
| Kassir `GET /stalls` | ✅ **403** `forbidden`, `read` yozuvlari soni O'ZGARMADI |
| Noma'lum `stall_id` (404) | ✅ `read` yozuvi YO'Q |
| A tokeni + B rastasi (`/{id}` va `/{id}/assignments`) | ✅ ikkalasi **404**, `status != 403` alohida, `read` yozuvi YO'Q |
| `GET /stalls/map` (200) | ✅ `read` yozuvi YO'Q (nazorat) |
| `grep -c "QAMRAMAYDI"` (`rbac.py`) | ✅ **0** |
| `git diff --unified=0 rbac.py \| grep -c "^[+-].*ROLE_PERMISSIONS"` | ✅ **0** |
| `git diff --exit-code frontend/src/lib/rbac.ts` | ✅ o'zgarish yo'q |
| `git diff --exit-code services/core-api/pyproject.toml` | ✅ o'zgarish yo'q (yangi paket YO'Q — T-02-SC) |
| Commit'larda fayl o'chirilishi | ✅ **0** (uchala commit'da ham) |
| `alembic_version` | ✅ **0010** (sxemaga tegilmadi) |

## Issues Encountered

- **`docker compose run` ichida `python -c` uchun heredoc ishlatib bo'lmadi** (worktree izolyatsiyasi murakkab buyruqlarni rad etadi). Bir martalik supurish o'lchovi vaqtinchalik `_probe_sweep.py` fayli bilan bajarildi, natija olingandan keyin fayl DARHOL o'chirildi va birorta commit'ga tushmadi (`git status` toza — tasdiqlangan).
- **Ketma-ket ikkita `docker compose run` bir vaqtda ishga tushirilganda daemon navbatga qo'ydi** va buyruq fon rejimiga o'tdi. Yakuniy natijaga ta'siri yo'q: `pytest -q` (`testpaths = ["tests"]`) tenancy to'plamini ham QAMRAYDI, ya'ni 906 testli to'liq yurish `tests/tenancy` ni allaqachon o'z ichiga oladi va u alohida ham yashil o'lchangan.
- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Qamrovga ta'siri yo'q: `migrated` fixture'i `alembic upgrade head` ni haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 906 testning har birida (02-10 dagi bilan bir xil holat).

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan, birorta javob maydoni qotirilgan qiymat olmagan.

**Ataylab ochiq qoldirilgan, KO'RINADIGAN qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `GET /api/v1/users` xodim telefoni va F.I.Sh. ni o'qish auditisiz qaytaradi | keyingi faza qarori | `EXEMPT_ROUTES` da SABAB bilan; pastdagi "Threat Flags" da; istisno `test_every_exemption_is_load_bearing` bilan qulflangan (marshrut shaxsiy maydonni qaytarishni to'xtatsa istisno olib tashlanishi SHART) |
| `GET /api/v1/me` o'z profilini auditsiz qaytaradi | — | ATAYIN va doimiy: subyektning o'z ma'lumoti oshkor bo'lish emas; `VENDOR_VIEW` talabi kassir/nazoratchini o'z ismidan mahrum qilardi |
| Frontend `GET /stalls` uchun `VENDOR_VIEW` ni menyu darajasida tekshirmaydi | 02-20 yoki keyingi faza | Amaliy ta'siri YO'Q — `MARKET_DATA_VIEW` egasining hammasida `VENDOR_VIEW` bor va bu invariant endi test bilan qulflangan |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA bitta yuza aniqlandi — u YANGI emas, mavjud chegaraning birinchi marta O'LCHANGAN va qayd etilgan holati:

| Flag | File | Description |
|------|------|-------------|
| threat_flag: repudiation | `services/core-api/app/api/v1/users.py` | `GET /api/v1/users` javobida `phone` va `full_name` bor (tizim foydalanuvchisining shaxsiy ma'lumoti, D-01 bo'yicha telefon — login identifikatori), lekin `audit_read` YO'Q. Bu D-09 ning rasta/sotuvchi yuzasidan BOSHQA sinf: ma'lumot xodimniki, huquq `USER_VIEW`, va qaror `VENDOR_VIEW` bilan bog'lanmasligi kerak. Darvozada SABAB bilan istisno qilindi va istisno "hamon kerakmi" testi bilan qulflandi. Qamrovni kengaytirish qarori butun faza uchun bir marta ko'rib chiqilishi kerak — aynan 02-10 dagi `GET /stalls/{id}` flagi qanday ko'rib chiqilgan bo'lsa (u ana shu reja bilan yopildi) |

| Threat ID | Holat |
|-----------|-------|
| T-02-145 | mitigate — uchala marshrutda `Depends(audit_read(TABLE_STALLS, ...))`; `intent.filters` va `intent.result_count` to'ldirilgan; **sabotaj #1 bilan o'lchandi** (AYNAN 2 test qizardi) |
| T-02-146 | mitigate — uchala marshrut dekoratorida `VENDOR_VIEW`; `rbac.py` docstringi chegarani tushuntiradi; matritsa o'zgarmadi va uning invarianti `test_market_data_view_holders_already_have_vendor_view` bilan QULFLANDI (deviatsiya #4); **sabotaj #2 bilan o'lchandi** (AYNAN 1 test qizardi) |
| T-02-147 | mitigate — dekorator darajasidagi `dependencies=[...]` FastAPI grafida imzo parametrlaridan OLDIN turishi O'LCHANDI (`['vendor_view', 'market_data_view']`); xulq darajasida `test_forbidden_read_is_not_audited`; 404 yo'llari uchun IKKITA alohida nazorat testi (noma'lum ID va cross-tenant); 422 yo'li `list_stalls` docstringida hujjatlashtirilgan |
| T-02-148 | mitigate — `GET /stalls/map` qamrovdan ATAYIN tashqarida va IKKI test bilan qulflangan (`test_map_read_is_not_audited` — xulq, `test_map_route_is_free_of_the_requirement` — struktura); `PERSONAL_FIELDS` uch nomdan iborat va docstringda asoslangan |
| T-02-149 | mitigate — `test_personal_data_coverage.py` marshrut GRAFINI o'qiydi (manba matnini emas), introspektsiya teglari orqali; darvozaning bo'shab qolishi UCH qulf bilan bloklangan; **sabotaj #3 bilan o'lchandi** (`assert 3 >= 4`) |
| T-02-SC | n/a — yangi paket o'rnatilmadi; `git diff --exit-code services/core-api/pyproject.toml` bo'sh |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 |
| 2 | `pytest tests/integration/test_personal_data_audit.py -q` | ✅ 8 passed |
| 3 | `pytest tests/tenancy/test_personal_data_coverage.py -q` | ✅ 8 passed |
| 4 | `npm run test` | ✅ **906 passed** |
| 5 | `npm run test:tenancy` | ✅ **317 passed** |
| 6 | `git diff --exit-code services/core-api/pyproject.toml frontend/src/lib/rbac.ts` | ✅ o'zgarish yo'q |
| 7 | Sabotaj o'lchovlari (3 ta) | ✅ uchalasi ham AYNAN kutilgan test(lar)ni qizartirdi |
| 8 | Sabotajdan keyin tiklash | ✅ `git status` toza, kuzatilmagan fayl yo'q |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `grep -c "audit_read"` (izohsiz) ≥ 2 | ✅ import + alias |
| `Permission.VENDOR_VIEW` kamida ikki marshrut dekoratorida | ✅ 2 |
| `intent.result_count` AYNAN ikki joyda | ✅ `list_stalls`, `get_stall` |
| `audit_read` `stall_map` imzosida YO'Q | ✅ (graf o'lchovi: `audit=[]`) |
| `ruff check` va `mypy` exit 0 | ✅ |
| `pytest tests/integration/test_stall_registry.py -q` | ✅ 18 passed |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `audit_read` + `reason="stall_assignments_view"` (`assignments.py`) | ✅ |
| `Permission.VENDOR_VIEW` marshrut dekoratorida | ✅ |
| `required_permission` (`deps.py`) | ✅ |
| `audit_resource` (`audit.py`) | ✅ |
| `git diff \| grep -c "ROLE_PERMISSIONS"` = 0 | ✅ (deviatsiya #6 dan keyin) |
| `git diff --exit-code frontend/src/lib/rbac.ts` | ✅ |
| `grep -c "QAMRAMAYDI"` = 0 | ✅ (deviatsiya #6 dan keyin) |
| `ruff check . && mypy .` exit 0 | ✅ |
| `pytest tests/unit/test_rbac_matrix.py -q` | ✅ 13 passed |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_personal_data_audit.py` ≥ 7 test | ✅ **8** (4 ijobiy + 4 nazorat) |
| `test_personal_data_coverage.py` exit 0 | ✅ 8 passed |
| Shaxsiy-maydonli `GET` marshrutlari ≥ 4 va assert bilan qulflangan | ✅ **5**, `MINIMUM_PERSONAL_ROUTES = 4` |
| `GET /stalls/map` ozod va alohida assert bilan tasdiqlangan | ✅ `test_map_route_is_free_of_the_requirement` |
| `npm run test` exit 0 | ✅ 906 passed |
| `npm run test:tenancy` exit 0 | ✅ 317 passed |
| SABOTAJ: `get_stall` dan `intent` | ✅ AYNAN 2 test (audit detali + qamrov auditi) |
| SABOTAJ: `assignments.py` dan `VENDOR_VIEW` | ✅ AYNAN 1 test (faqat qamrov huquqi) |
| SABOTAJ: `PERSONAL_FIELDS` dan `vendor_name` | ✅ AYNAN 1 test (`assert 3 >= 4`) |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja sxemaga umuman tegmaydi va yangi paket qo'shmaydi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-04, MARKET-02]` deb yozadi. Bu reja MARKET-04 ni bloklab turgan CR-02 ni yopadi, lekin uni "bajarildi" deb belgilash bu agentning ishi emas: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt (`STATE.md` va `ROADMAP.md` bilan bir xil). 02-VERIFICATION.md ning tavsiyasi ham "barcha oltita MARKET-ID qolgan bo'shliqlar yopilgunicha `Pending` qolsin" deydi — CR-01 (02-20) va CR-03 (02-18) shu to'lqinda yopilyapti, real Karmana ma'lumoti esa hamon kutilmoqda.

## Next Phase Readiness

**Yangi `GET` marshrut qo'shadigan HAR KIM uchun (02-08/02-09/02-10 dan meros, endi beshinchi band bilan):**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si**;
3. marshrut TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana;
4. marshrut BO'SH ro'yxat qaytarishi mumkin bo'lsa — tenant darvozasi ALOHIDA mavjudlik so'rovi bilan;
5. **YANGI (02-19):** javobda `vendor_name` / `phone` / `full_name` bo'lsa — dekoratorga `dependencies=[Depends(require_permission(Permission.VENDOR_VIEW))]` **va** imzoga `audit_read(...)` niyati. Unutish mumkin emas: `tests/tenancy/test_personal_data_coverage.py` marshrutni AVTOMATIK topadi va CI'ni qizartiradi. Marshrut haqiqatan boshqa sinfga tegishli bo'lsa — `EXEMPT_ROUTES` ga SABAB bilan, va sabab "hamon kerakmi" testi bilan qulflanadi.

**02-20 (frontend `lib/`) uchun:**

- `GET /stalls`, `GET /stalls/{id}` va `GET /stalls/{id}/assignments` endi `VENDOR_VIEW` ham talab qiladi. Amaliy ta'sir YO'Q (`MARKET_DATA_VIEW` egasining hammasida bu huquq bor va invariant test bilan qulflangan), lekin `rbac.ts` ko'zgusida rasta ekranini `market_data_view` bilan gate qilayotgan joy bo'lsa, u endi TO'LIQ emas — ikkala huquq ham kerak.
- Yangi xato kodi qo'shilmadi, `MARKET_ERROR_CODES` uzunligi o'zgarmadi.

**5- va 6-fazalar uchun:**

- Kassir oqimi rastani RAQAM bo'yicha topadi (`GET /stalls?q=`). Kassirda `MARKET_DATA_VIEW` ham, `VENDOR_VIEW` ham YO'Q — ya'ni o'sha oqim shu marshrutdan FOYDALANA OLMAYDI va u uchun alohida, tor yuza kerak bo'ladi (masalan faqat kod va tarif qaytaradigan, sotuvchi nomisiz endpoint). Buni 5-faza rejasi hisobga olsin: mavjud marshrutga kassirni qo'shish D-09 chegarasini buzardi.
- Har yangi hisobot marshruti sotuvchi nomini qaytarsa darvoza uni AVTOMATIK ushlaydi — hisobot rejalari `audit_read` uchun `reason` ni oldindan tanlab qo'ysin (`report_view` kabi), chunki `reason` jurnalning ajratuvchi o'lchovi.

**Audit jurnalini o'qiydigan UI uchun (D-11/D-12):**

- `table_name = 'stalls'` endi UCH xil `reason` bilan keladi: `stall_view` (reestr yoki kartochka), `stall_assignments_view` (bitta rastaning sotuvchi tarixi). `vendors` esa `vendor_view` bilan. Filtr UI'si `reason` ni ko'rsatmasa foydalanuvchi "rasta reestri ko'rildi" va "sotuvchilar reestri ko'rildi" ni ajrata olmaydi.
- `filters.q` da XOM qidiruv matni bor va u shaxsiy ma'lumot bo'lishi mumkin — audit ekrani uni ko'rsatishi KERAK (bu yozuvning butun maqsadi), lekin eksport qilinganda o'sha fayl ham shaxsiy ma'lumot sifatida muomala qilinishi kerak.

## Self-Check: PASSED

- Da'vo qilingan 2 yangi fayl diskda mavjud: `tests/integration/test_personal_data_audit.py`, `tests/tenancy/test_personal_data_coverage.py`
- Da'vo qilingan 5 o'zgartirilgan fayl `git diff --stat b26be53..HEAD` da ko'rinadi (7 fayl, +1069/-13)
- Uchala commit git tarixida mavjud: `3b9d5f9`, `b1c2286`, `4c72da2`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only` uchalasida ham bo'sh)
- Uchta sabotajdan keyin fayllar `git checkout -- <fayl>` bilan tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi (`_probe_sweep.py` o'chirildi va birorta commit'ga tushmadi)
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)
- `frontend/` va `services/core-api/pyproject.toml` TEGILMADI (`git diff --exit-code` bo'sh)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
