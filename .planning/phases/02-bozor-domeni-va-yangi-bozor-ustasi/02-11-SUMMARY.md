---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 11
subsystem: api
tags: [fastapi, postgres, security-definer, rls, rbac, audit, wizard, fail-closed, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-10 — cross-tenant matritsasi mexanikasi (`PARAM_FILLERS`/`BODY_FILLERS`), `audit_read` ikki qatlami, 'bo'sh javob tenant teshigini yashiradi' darsi; 02-09 — `add_tariff()` ning boshlang'ich narx istisnosi (T-02-63a) va `CalendarRepository`, 'routerlar SQL bajarmaydi' konvensiyasi; 02-08 — `app/schemas.py` DTO shartnomasi (`MarketCreateRequest`/`MarketCreateResponse`/`BlockingItem`/`SetupStatusResponse`), `MARKET_ERROR_CODES`, `_market_id()` naqshi; 02-06 — `market_delete_draft()` + immutability triggerlaridagi qoralama istisnosi; 02-05 — `market_profile` audit triggeri; 02-04 — `market_create`/`market_activate`/`market_rename` `SECURITY DEFINER` funksiyalari; 02-03 — `MarketRef.is_active` va `setupStatusSchema` (`blocking[].step` kontrakti)"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`AuthSessionDep` (tenant kontekstisiz sessiya), `TenantSessionDep`, `require_permission`/`require_platform_admin`, `write_app_audit()` + `TABLE_MARKETS`, `auth_list_markets_full()`, `GET /audit/platform` (`market_id IS NULL`), cross-tenant matritsasi"
provides:
  - "`app/repositories/market_repo.py` — `MarketRepository` (`TenantScopedRepository` dan MEROS OLMAYDI) + `setup_status()` agregati"
  - "`POST /api/v1/markets` — qoralama bozor + profil BITTA amalda"
  - "`GET /api/v1/markets/{id}/setup-status` — hisoblanadigan (saqlanmaydigan) usta holati"
  - "`POST /api/v1/markets/{id}/activate` — 409 + `blocking[]` yo'l ko'rsatkichi"
  - "`DELETE /api/v1/markets/{id}` — faqat qoralama (A10, Pitfall 7)"
  - "`app.schemas.MARKET_ERROR_CODES`: `market_is_active` (21 -> 22)"
  - "`tests/tenancy/test_cross_tenant.py::PLATFORM_ADMIN_ROUTES` — huquq darvozasi tenant darvozasini yashiradigan marshrutlar uchun kuchaytirilgan sessiya"
  - "`tests/integration/test_wizard_flow.py` — SC#1 ning uchidan-uchiga isboti (24 test)"
  - "`fixtures.admin_api.SETUP_STATUS_URL` / `ACTIVATE_URL`"
  - "`tests/unit/test_rbac_matrix.py::test_market_manage_is_platform_admin_only`"
affects: [02-12, 02-13, 02-16, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`SECURITY DEFINER` chaqiruviga YO'L PARAMETRI emas, `principal.market_id` uzatiladi — funksiya RLS'ga bo'ysunmaydi, ya'ni ilova darvozasi yagona chegara"
    - "Huquq darvozasi tenant darvozasini YASHIRADI: matritsa `MARKET_MANAGE` marshrutlarini KUCHAYTIRILGAN sessiya bilan chaqiradi, aks holda 403 tenant tekshiruvigacha yetib bormaydi (o'lchandi)"
    - "Platforma darajasidagi hodisa (`bozor yaratish`) `market_id = NULL` bilan yoziladi — `principal` uzatilganda u tanlangan bozorning jurnaliga yolg'on dalil qoldiradi (o'lchandi)"
    - "To'liqlik qoidasi BITTA funksiyada (`_blocking`) va uni `setup-status` ham, `activate` ham iste'mol qiladi — javob tanalari test bilan TENGLIGI qulflangan"
    - "Agregat so'rovida profil qatori yo'q bo'lsa CTE `NULL` beradi va natija FAIL-CLOSED bo'ladi — istisno ko'tarish yo'l ko'rsatkichini yo'q qilardi"
    - "`blocking[].detail` FAQAT sonlarni tashiydi (`\"498/512\"`) — server matn yozmaydi, i18n chegarasi frontendda"

key-files:
  created:
    - services/core-api/app/repositories/market_repo.py
    - tests/integration/test_wizard_flow.py
  modified:
    - services/core-api/app/api/v1/markets.py
    - services/core-api/app/schemas.py
    - tests/fixtures/admin_api.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
    - tests/unit/test_rbac_matrix.py

key-decisions:
  - "`_own_market()` `principal.market_id` ni QAYTARADI, yo'l parametrini emas — `SECURITY DEFINER` funksiya RLS'ni ko'rmaydi"
  - "Bozor yaratish auditi PLATFORMA-GLOBAL (`market_id IS NULL`), `principal=` ATAYIN uzatilmaydi"
  - "Rekvizitlar auditga UMUMAN yozilmaydi (maskalash ham tanlanmadi — `***` savolga javob bermaydi, lekin signal qoldiradi)"
  - "`setup-status` profil qatori yo'q bozorda 409 EMAS, FAIL-CLOSED `blocking[]` qaytaradi"
  - "409 tanasi `JSONResponse` bilan quriladi — `HTTPException` `blocking` ni bir daraja pastga tushirardi"
  - "`MarketCreateResponse` `activate` javobi uchun ham ishlatiladi (ikkinchi, aynan bir xil DTO frontendga bitta shaklning ikki nomini berardi)"
  - "`PLATFORM_ADMIN_ROUTES` — matritsa mexanikasiga yangi tushuncha; usiz `MARKET_MANAGE` marshrutlarining tenant darvozasi UMUMAN sinalmasdi"
  - "`list_markets` SQL'i `market_repo` ga ko'chdi (02-09 konvensiyasi: routerlar SQL bajarmaydi)"
  - "`rename_market()` HTTP iste'molchisisiz qoldirildi va sabab docstringda (02-16 uni `PATCH /markets/{id}` ostiga qo'yadi)"

patterns-established:
  - "Pattern: `SECURITY DEFINER` funksiyaga uzatiladigan identifikator DARVOZANING NATIJASIDAN olinadi, kirish parametridan emas"
  - "Pattern: huquq darvozasi tenant darvozasidan OLDIN tursa, matritsa o'sha marshrutni huquqi YETADIGAN sessiya bilan chaqiradi (aks holda 403 tenant da'vosini yopib qo'yadi)"
  - "Pattern: 'qaysi jurnalga tushadi' savoli audit yozuvining SHAKLI qadar muhim — noto'g'ri `market_id` yolg'on dalil"

requirements-completed: []

# Metrics
duration: 65min
completed: 2026-08-01
---

# Phase 2 Plan 11: Yangi bozor ustasining server tomoni Summary

**MARKET-01 ning server yarmi yopildi va SC#1 endi bitta testda uchidan-uchiga o'tadi (yaratish → tanlash → to'ldirish → faollashtirish, birorta 403siz); oltita sabotaj o'lchovi darvozalarning kuchini aniq ko'rsatdi va ikkitasi rejaning ko'rmagan narsasini fosh qildi — `MARKET_MANAGE` ni faqat platforma adminida qoldirish cross-tenant matritsasini JIMGINA o'chirib qo'yardi (403 tenant tekshiruvigacha yetib bormaydi), `setup-status` ning tenant darvozasi olib tashlanganda esa begona bozor `200` bilan "bo'm-bo'sh qoralama" bo'lib ko'rinardi — strukturaviy jihatdan mutlaqo to'g'ri javob.**

## Performance

- **Duration:** ~65 min
- **Tasks:** 3/3
- **Files:** 8 (2 yaratildi, 6 o'zgartirildi), +2078 / −36
- **Testlar:** 732 → **778** (+46: tenancy +21, integratsiya +24, unit +1)
- **Marshrutlar:** matritsa 36 → **39** (`EXEMPT_ROUTES` uzunligi O'ZGARMADI — 14)

## Accomplishments

- **Oltita sabotaj o'lchovi va ularning aniq natijalari:**

  | Sabotaj | Yiqilgan test(lar) | Nazorat holati |
  |---|---|---|
  | `_own_market()` dagi solishtirish olib tashlandi (yo'l parametri qaytariladi) | AYNAN 3: `test_cross_tenant_object_returns_404` ning uchala usta marshruti. `setup-status` uchun javob **`200`** va tanasi `{"zones":0,...,"blocking":[zones_missing, categories_missing, stalls_missing, calendar_missing]}` | qolgan 286 tenancy testi ✅ — ya'ni begona bozor "bo'm-bo'sh qoralama" bo'lib ko'rinardi va bu **enumeratsiya signali**, strukturaviy jihatdan to'g'ri javob ichida |
  | `_blocking()` dan tarif qamrovi sharti olib tashlandi | AYNAN 2: `test_activate_rejects_incomplete_market[tariffs]` va `test_tariff_gap_reports_numbers_in_detail` | qolgan 22 usta testi ✅ — har shart o'z testiga ega |
  | `setup_status` dagi `COALESCE(..., 0)` → `COALESCE(..., 1)` (fail-closed buzildi) | AYNAN 1: `test_activate_rejects_incomplete_market[calendar]` | qolgan 23 ✅ — profilsiz bozor faollashtirila olardi va `market_is_open()` uni HAR KUNI yopiq deb turaverardi |
  | Yaratish auditida `principal=principal` (rejaning LITERAL ko'rsatmasi) | AYNAN 1: `test_market_creation_is_audited_at_the_platform_level` (**`assert 0 == 1`** — platforma jurnalida yozuv UMUMAN yo'q) | yozuv A bozorining jurnaliga tushardi: "A bozorida yangi bozor yaratildi" degan YOLG'ON dalil |
  | `PLATFORM_ADMIN_ROUTES` bo'shatildi | AYNAN 2: `DELETE /markets/{id}` va `POST /.../activate` uchun **`assert 403 != 403`** | `setup-status` ✅ YASHIL qoldi (u `MARKET_DATA_VIEW`, ya'ni bozor adminida bor) — farq aynan huquq darajasida |
  | `delete_draft()` natijasi e'tiborsiz qoldirildi | AYNAN 1: `test_active_market_cannot_be_deleted` (**204** keldi) | bozor qatori JOYIDA qoldi — DB darvozasi ushladi, LEKIN API yolg'on "o'chirildi" javobini berardi |

  Har oltitasidan keyin fayllar `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza, `git diff --stat` bo'sh).

- **Fazaning eng qimmat topilmasi — huquq darvozasi tenant darvozasini YASHIRADI.** `MARKET_MANAGE` D-07 matritsasida FAQAT `platform_admin` da; cross-tenant matritsasi esa har marshrutni **bozor admini** sessiyasi bilan chaqiradi. Ya'ni `DELETE /markets/{id}` va `POST /.../activate` so'rovlari `require_permission` da **403** olib to'xtardi va `_own_market()` gacha UMUMAN yetib bormasdi. "Test qizarmasin" deb 403 ni qabul qilish eng yomon yechim bo'lardi: o'shanda "begona bozorni faollashtirib bo'lmaydi" degan da'vo hech qachon sinalmasdi va matritsa YASHIL turaverardi. Yechim — o'sha ikkita marshrutni `MARKET_MANAGE` GA EGA sessiya (A bozorini tanlagan platforma admini) bilan chaqirish; `test_platform_admin_routes_really_need_the_elevated_session` esa ro'yxatning O'ZINI himoya qiladi (har bir yozuv uchun bozor admini ROSTDAN 403 olishi tekshiriladi, ya'ni oddiy marshrutni bu yerga qo'shib "yumshatib" bo'lmaydi).

- **`SECURITY DEFINER` funksiya bilan ishlashda ilova qatlami YAGONA tenant chegarasi.** `market_activate()` va `market_delete_draft()` RLS'ga umuman bo'ysunmaydi — ya'ni ularga **yo'l parametrini** uzatish darvozani yagona himoyaga aylantirardi va u bir kun olib tashlansa begona bozor faollashib (yoki o'chib) ketardi. Shuning uchun `_own_market()` solishtirish natijasi sifatida **`principal.market_id` ni qaytaradi**: eng yomon holatda ham amal chaqiruvchining O'Z bozoriga tegadi. Sabotaj #1 bu qarorning narxini o'lchadi — darvozasiz `setup-status` 200 berdi, lekin `activate`/`delete` baribir A bozori ustida ishlardi.

- **Audit yozuvining "qaysi jurnalga tushishi" shakli qadar muhim.** Reja `write_app_audit(..., principal=principal)` deydi; `principal` esa `market_id` ni ham beradi. Platforma admini A bozorini tanlab turib C bozorini yaratganda yozuv A ning jurnaliga tushardi — nizoni hal qilayotgan odam uchun bu "A bozorida yangi bozor yaratildi" degan tushunarsiz va YOLG'ON qator. `sbozor_core.models.ops.AuditLog` docstringi bu holatni ALLAQACHON nomlagan: "platforma darajasidagi harakatlar (**bozor yaratish**, ...) hech qaysi bozorga tegishli emas". Endpoint maydonlarni qo'lda uzatadi va yozuv `market_id IS NULL` bilan tushadi — u `GET /audit/platform` orqali ko'rinadi (darvozasi ham aynan `is_platform_admin`).

- **`setup-status` profil qatori yo'q bozorda FAIL-CLOSED javob beradi, 409 emas.** Kod bazasidagi qolgan uchta joy (`calendar_repo.profile`, `tariff_repo.tariff_window`, `stall_repo._operating_since`) `MarketProfileMissingError` → 409 `market_incomplete` beradi. Bu yerda qaror boshqacha va u mahsulot qarori: `setup-status` ning BUTUN vazifasi — "nima yetishmayapti" savoliga RO'YXAT bilan javob berish (UI-SPEC §6.6: "409 xato emas, yo'l ko'rsatkichi"). Profilsiz bozor uchun 409 qaytarish foydalanuvchini aynan o'sha yo'l ko'rsatkichisiz qoldirardi. CTE 0 qator berganda `operating_since` `NULL` bo'ladi, `valid_from <= NULL` esa `NULL` — ikkala qamrov sanog'i `0`, `calendar_configured` `false`. Qamrov TORAYMAYDI (faollashtirish baribir to'siladi), tushuntirish QO'SHILADI.

- **Ikkita bloklovchi shart API orqali ERISHIB BO'LMAYDIGAN ekan — va bu o'lchandi, taxmin qilinmadi.** `stalls_without_category`: `POST /stalls` boshlang'ich toifa davrini HAR DOIM o'zi yozadi (`StallRepository.create()`, `valid_from = operating_since`) va toifa davrini o'chiradigan endpoint umuman yo'q. `calendar_missing`: `open_weekdays` `NOT NULL` va `ck_market_profile_open_weekdays` bo'sh massivni rad etadi, ya'ni "jadval sozlanmagan" holatiga faqat PROFIL QATORISIZ bozor tushadi. Ikkala darvoza ham `market_create()` dan TASHQARIDA tug'ilgan qatorlar (migratsiya, 02-12 importi, qo'lda tuzatish) uchun mavjud, shuning uchun ularning testlari `sbozor_owner` bilan quriladi va sabab `INCOMPLETE_CASES` docstringida literal yozilgan.

- **Ustaning 5-qadami rejadagidan bitta chaqiruv KALTAROQ.** Reja "`POST /stalls` ×3, har rastaga `POST /stalls/{id}/category`" deydi, lekin ikkinchi chaqiruv (a) keraksiz — boshlang'ich davr `POST /stalls` ichida yoziladi, (b) FOYDASIZ — `set_category()` `valid_from` ni KELAJAKDA talab qiladi (T-02-61a), kelajakdagi davr esa `valid_from <= operating_since` qamroviga umuman tushmaydi. Ya'ni rejaga literal ergashish "qadam bajarildi" degan yolg'on tuyg'u berardi.

## Task Commits

1. **Task 1: `market_repo.py` va qoralama bozor yaratish / o'chirish** — `be6ada6` (feat)
2. **Task 2: `setup-status` agregati va faollashtirish darvozasi** — `ee244f6` (feat)
3. **Task 3: SC#1 ning uchidan-uchiga testi va RBAC darvozasi** — `accc2bf` (test)

## Files Created/Modified

**Yaratildi**

- `services/core-api/app/repositories/market_repo.py` — `MarketRepository` (`TenantScopedRepository` dan meros OLMAYDI; sababi ikki qavatli va modul docstringida). To'rtta `SECURITY DEFINER` chaqiruvi tiplangan `bindparams()` bilan; `_SETUP_STATUS` — `WITH profile AS (...)` + oltita skalyar subquery, fail-closed sharti SQL matni ustidagi docstringda.
- `tests/integration/test_wizard_flow.py` — 24 test (reja ≥7 talab qiladi). `created_markets` fixture'i tozalashni MAHSULOT funksiyasi (`market_delete_draft()`) bilan bajaradi va avval bayroqni tushiradi.

**O'zgartirildi**

- `services/core-api/app/api/v1/markets.py` — to'rtta yangi marshrut, `_own_market()`, `_blocking()`, `_setup_status_response()`. Modul docstringi kengaydi: `markets` ga yozish yo'li, `AuthSessionDep` sababi va app-qatlam auditining majburiyligi.
- `services/core-api/app/schemas.py` — `market_is_active` kodi (deviatsiya #1); `MarketCreateResponse` docstringi ikkala yo'lni qamraydi (deviatsiya #2).
- `tests/fixtures/admin_api.py` — `SETUP_STATUS_URL` / `ACTIVATE_URL` shablonlari.
- `tests/tenancy/test_cross_tenant.py` — `PARAM_FILLERS["market_id"]`, `PLATFORM_ADMIN_ROUTES` + `headers_for` fixture'i, ikkita meta-test, `/api/v1/markets` istisnosining sababi kengaytirildi.
- `tests/tenancy/test_route_coverage.py` — `MINIMUM_MATRIX_ROUTES` 28 → 31 va `POST /markets` ning qamrovi qayerda ekani qayd etildi.
- `tests/unit/test_rbac_matrix.py` — `test_market_manage_is_platform_admin_only` (deviatsiya #4).

## Decisions Made

- **`_own_market()` `principal.market_id` ni QAYTARADI.** Reja faqat "yo'ldagi `market_id` `principal.market_id` bilan mos kelmasa 404" deydi va keyin repozitoriyga NIMA uzatilishini belgilamaydi. Yo'l parametrini uzatish `SECURITY DEFINER` funksiyalar bilan ishlaganda darvozani YAGONA himoyaga aylantirardi (RLS ularni ko'rmaydi). Qaytariladigan qiymat aynan shuning uchun `principal` dan olinadi.
- **Yaratish auditi platforma-global.** Reja `principal=principal` deydi; bu esa yozuvni tanlangan bozorning jurnaliga tushirardi (sabotaj #4 bilan o'lchandi). `AuditLog` modelining O'Z docstringi "bozor yaratish" ni `market_id IS NULL` holatiga misol sifatida keltiradi.
- **Rekvizitlar auditga UMUMAN yozilmaydi.** Reja "maskalash yoki umuman yozmaslik" ni tanlashni SUMMARY'ga qoldiradi (T-02-84). Maskalash tanlanmadi: `***` hech qanday savolga javob bermaydi, lekin "bu yerda rekvizit bor" degan signalni qoldiradi. Jurnalning vazifasi — "kim qachon qaysi bozorni yaratdi"; rekvizitlarning O'ZGARISHI esa `market_profile` DB-trigger auditiga tushadi (02-05).
- **409 `market_incomplete` tanasi `JSONResponse` bilan quriladi.** `HTTPException(detail={...})` javobni `{"detail": {"detail": ..., "blocking": [...]}}` shaklida o'rardi — `blocking` bir daraja pastga tushib, 02-03 dagi `setupStatusSchema` va UI-SPEC §6.6 dagi "409 bir xil render yo'lidan o'tadi" kontrakti buzilardi.
- **"Allaqachon faol" tekshiruvi to'liqlikdan OLDIN.** Faollashtirilgandan keyin zonasi o'chirilgan bozor uchun javob "chala" emas, "allaqachon jonli" bo'lishi kerak — aks holda foydalanuvchi mavjud bo'lmagan ish qidirardi.
- **`MarketCreateResponse` `activate` javobiga ham xizmat qiladi.** `<interfaces>` ikkala yo'l uchun ham AYNAN bir xil uchlikni (`{id, name, is_active}`) belgilaydi. Ikkinchi DTO frontendga bitta shaklning ikki nomini berardi (02-10 dagi `GET /vendors/{id}` → `VendorListItem` qarori bilan bir xil mulohaza).
- **`list_markets` SQL'i repozitoriyga ko'chdi.** Reja buni so'ramaydi, lekin aks holda BITTA routerda ikkita SQL uyi bo'lardi: eskisi router ichida, yangisi repozitoriyda. 02-09 konvensiyasi ("routerlar SQL bajarmaydi") bu fayl uchun ham amal qiladi; ko'chirish mexanik (aynan o'sha `text()` obyektlari) va `test_me_locale.py` ning `MARKET_VIEW_ALL` regressiya testi yashil qoldi.
- **`rename_market()` HTTP iste'molchisisiz qoldirildi.** Reja uni `must_haves` da talab qiladi, lekin `<interfaces>` to'rtta endpointni belgilaydi va rename ular orasida yo'q. Metod qoldirildi (u `markets` ga yozishning to'rtta yo'lidan biri va `MARKET_CORE_GRANT_SIGNATURES` bilan bir ko'rinishda solishtiriladi), sabab va uning kelgusi egasi (02-16) docstringda.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `market_is_active` xato kodi `MARKET_ERROR_CODES` da YO'Q edi**

- **Found during:** Task 1
- **Issue:** Reja `<interfaces>` da `DELETE` uchun `409 market_is_active` va Task 2 da `activate` uchun aynan shu kodni belgilaydi, lekin 02-08 qotirgan to'plamda (`MARKET_ERROR_CODES`) u yo'q. Ro'yxatning O'ZI hujjat ("bu fazada nima noto'g'ri ketishi mumkin") va frontend ko'zgusining manbai — kodni unda qayd etmasdan qaytarish ro'yxatni jimgina eskirtirardi.
- **Fix:** `market_is_active` qo'shildi (21 → **22**) va `market_incomplete` dan NEGA ajratilgani izohda: birinchisi "yana nima kerak" deydi va `blocking[]` bilan keladi, ikkinchisi "amal umuman qo'llanmaydi" deydi va hech qanday yo'l ko'rsatmaydi.
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `test_active_market_cannot_be_deleted` va `test_activating_an_active_market_returns_409` javob tanasini AYNAN `{"detail": "market_is_active"}` bilan solishtiradi
- **⚠ Qarz:** `frontend/src/lib/api-types.ts::ERROR_CODES` endi 22 kod kutadi (02-13/02-14 yopadi)
- **Committed in:** `be6ada6`

**2. [Rule 1 - Bug] `MarketCreateResponse` docstringi `activate` javobiga ZID edi**

- **Found during:** Task 2
- **Issue:** DTO docstringi "`is_active` HAR DOIM `false` bo'ladi" deydi. `<interfaces>` esa `activate` uchun AYNAN bir xil uchlikni (`{id, name, is_active: true}`) belgilaydi. Reja shaklni belgilab, DTO nomini belgilamaydi — ya'ni yo ikkinchi (maydonlari bir xil) DTO yaratish, yo docstringni to'g'rilash kerak edi. Birinchisi frontendga bitta shaklning ikki nomini berardi va ular bir kun ajralib ketardi.
- **Fix:** DTO qayta ishlatildi, docstring ikkala yo'lni qamraydi va ikkinchi DTO NEGA yaratilmagani literal yozildi.
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** OpenAPI'da `/api/v1/markets` (`POST`) va `/api/v1/markets/{market_id}/activate` ikkalasi ham `MarketCreateResponse` ga ishora qiladi
- **Committed in:** `ee244f6`

**3. [Rule 2 - Missing Critical] `MARKET_MANAGE` marshrutlari cross-tenant matritsasida UMUMAN sinalmasdi**

- **Found during:** Task 1
- **Issue:** Reja `PARAM_FILLERS` ga `market_id` qo'shishni buyuradi va matritsa avtomatik qamraydi deb hisoblaydi. Amalda `DELETE /markets/{id}` va `POST /.../activate` `MARKET_MANAGE` talab qiladi, matritsa esa har marshrutni **bozor admini** sessiyasi bilan chaqiradi — o'sha rolda bu huquq YO'Q (D-07). Natijada so'rov `require_permission` da **403** olib to'xtardi va `test_cross_tenant_object_returns_404` ning birinchi assertion'i (`!= 403`) yiqilardi. "Tuzatish" uchun eng oson yo'l — o'sha marshrutlarni `EXEMPT_ROUTES` ga qo'shish yoki 403 ni qabul qilish — ikkalasi ham tenant darvozasini BUTUNLAY sinovsiz qoldirardi.
- **Fix:** `PLATFORM_ADMIN_ROUTES` + `headers_for` fixture'i: sanab o'tilgan marshrutlar A bozorini tanlagan PLATFORMA ADMINI sessiyasi bilan chaqiriladi (sessiya baribir **A bozoriga** tegishli, ya'ni "begona obyekt → 404" da'vosi o'zgarmaydi — farq faqat huquq darajasida). Ro'yxatning O'ZI ikkita meta-test bilan himoyalandi: `test_platform_admin_routes_point_at_live_routes` (eskirgan yozuv) va `test_platform_admin_routes_really_need_the_elevated_session` (har bir yozuv uchun bozor admini ROSTDAN 403 oladi — ya'ni oddiy marshrutni bu yerga qo'shib yumshatib bo'lmaydi).
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** **Sabotaj #5** — ro'yxat bo'shatilganda AYNAN 2 test `assert 403 != 403` bilan yiqildi; `setup-status` marshruti (u `MARKET_DATA_VIEW`) YASHIL qoldi
- **Committed in:** `be6ada6`, `ee244f6`

**4. [Rule 2 - Missing Critical] `MARKET_MANAGE` ning EGALIK doirasi hech qayerda qulflanmagan edi**

- **Found during:** Task 3
- **Issue:** Reja `test_rbac_matrix.py` ga faqat "`MARKET_MANAGE` ni ham kirit (agar hali yo'q bo'lsa)" deydi — u ALLAQACHON bor edi (`test_platform_admin_can_run_the_wizard`). Lekin POZITIV da'vo yetarli emas: huquq bozor adminiga ham berilsa test baribir yashil qolardi, holbuki o'shanda u (a) o'z bozorini platforma nazoratisiz faollashtira olardi, (b) qoralamani o'chira olardi, (c) `PLATFORM_ADMIN_ROUTES` mexanizmi ma'nosiz bo'lib qolardi. Bu 2-fazadagi "matritsa kengayishi" xavfining aynan shakli (`test_director_is_read_only_on_market_data` bilan bir sinf).
- **Fix:** `test_market_manage_is_platform_admin_only` — huquq EGALARI to'plami `{PLATFORM_ADMIN}` ga AYNAN teng bo'lishi tekshiriladi. Docstringda uchala oqibat va `PLATFORM_ADMIN_ROUTES` bilan bog'liqlik yozilgan.
- **Files modified:** `tests/unit/test_rbac_matrix.py`
- **Verification:** `pytest tests/unit/test_rbac_matrix.py -q` — 13 test
- **Committed in:** `accc2bf`

**5. [Rule 1 - Bug] Yaratish auditi TANLANGAN bozorning jurnaliga tushardi**

- **Found during:** Task 1
- **Issue:** Reja `write_app_audit(..., principal=principal, ...)` deb yozadi. `write_app_audit` esa `principal` dan `market_id` ni ham oladi. Ustaning odatiy oqimida (bozor tanlanmagan) bu zararsiz — `market_id` `NULL` bo'ladi. Lekin platforma admini A bozorini TANLAB turib yangi bozor yaratishi mumkin (endpoint buni taqiqlamaydi va taqiqlashi ham kerak emas), o'shanda yozuv A ning jurnaliga "yangi bozor yaratildi" bo'lib tushardi — nizoni hal qilayotgan odam uchun tushunarsiz va YOLG'ON dalil.
- **Fix:** `principal=` ATAYIN uzatilmaydi; `actor_user_id` / `actor_label` / `request_id` qo'lda beriladi va `market_id` `NULL` bo'lib qoladi. Yozuv `GET /audit/platform` orqali ko'rinadi (darvozasi ham aynan `is_platform_admin`). Sabab kod ichida sakkiz qatorli izohda va `AuditLog` docstringiga havola bilan.
- **Files modified:** `services/core-api/app/api/v1/markets.py`
- **Verification:** **Sabotaj #4** — `principal=principal` qaytarilganda `test_market_creation_is_audited_at_the_platform_level` `assert 0 == 1` bilan yiqildi (platforma jurnalida yozuv UMUMAN yo'q). Test ikkinchi da'voni ham tekshiradi: A bozorining jurnalida `markets` ustidagi DML yozuvi YO'Q
- **Committed in:** `be6ada6`, `accc2bf`

**6. [Rule 3 - Blocking] `POST /markets` matritsadan JIMGINA chiqib ketardi**

- **Found during:** Task 1
- **Issue:** `EXEMPT_ROUTES` YO'L bo'yicha kalitlanadi, metod bo'yicha emas. `/api/v1/markets` allaqachon istisno (`GET` — bozor tanlash yuzasi), ya'ni yangi `POST` ham AVTOMATIK ravishda matritsadan tushib qoldi va buni birorta test ko'rsatmasdi. `EXEMPT_ROUTES` docstringi bunday holat uchun aniq talab qo'yadi: "Istisno qo'shgan odam bu qamrovni ham ko'chirishi SHART — aks holda marshrut 'istisno' degan so'z bilan butunlay sinovsiz qolardi."
- **Fix:** (a) istisnoning SABABI kengaytirildi va `POST` ning nega global ekani (identifikator aynan javob natijasida tug'iladi, ya'ni "boshqa bozorning obyekti" tushunchasining o'zi yo'q) literal yozildi; (b) qamrov `test_wizard_flow.py` da qayta tiklandi — tokensiz → **401** (`test_market_creation_requires_a_token`), bozor admini → **403** (`test_market_admin_cannot_create_market`), platforma admini → **201**; (c) `test_route_coverage.py` da `POST /markets` ning qamrovi QAYERDA ekani qayd etildi.
- **Files modified:** `tests/tenancy/test_cross_tenant.py`, `tests/tenancy/test_route_coverage.py`, `tests/integration/test_wizard_flow.py`
- **Verification:** `test_no_route_is_both_exempt_and_in_the_matrix` va `test_exempt_routes_have_reason` yashil; uchala qamrov testi ham yashil
- **Committed in:** `be6ada6`, `ee244f6`, `accc2bf`

**7. [Rule 2 - Missing Critical] `setup-status` profilsiz bozorda 409 berib, yo'l ko'rsatkichini yo'qotardi**

- **Found during:** Task 2
- **Issue:** Reja `setup_status()` ni `FROM market_profile p WHERE p.market_id = :market_id` shaklida ta'riflaydi — bu 0 qator berganda `one()` istisno ko'taradi va kod bazasidagi konvensiya bo'yicha u 409 `market_incomplete` ga aylanardi. Lekin `market_incomplete` javobida `blocking[]` YO'Q, ya'ni foydalanuvchi "bozor chala" degan xabarni olib, QAYSI qadam ekanini bilmasdi — UI-SPEC §6.6 aynan shu tajribani taqiqlaydi. Bundan tashqari `activate` ham 409 `market_incomplete` berardi, lekin `blocking[]` siz — ikkita bir xil kod, ikki xil shakl.
- **Fix:** So'rov `WITH profile AS (...)` + skalyar subquerylar shaklida qayta yozildi va `FROM` bandisiz — ya'ni HAR DOIM aynan bitta qator qaytaradi. Profil yo'q bo'lsa `operating_since` `NULL`, ikkala qamrov sanog'i `0`, `calendar_configured` `false` (FAIL-CLOSED). Qamrov TORAYMAYDI: faollashtirish `calendar_missing` bilan baribir to'siladi. Sabab SQL matni ustidagi docstringda literal yozilgan.
- **Files modified:** `services/core-api/app/repositories/market_repo.py`
- **Verification:** **Sabotaj #3** — `COALESCE(..., 0)` `COALESCE(..., 1)` ga o'zgartirilganda AYNAN `test_activate_rejects_incomplete_market[calendar]` yiqildi
- **Committed in:** `ee244f6`

**8. [Rule 1 - Bug] `table_name = 'markets'` bo'yicha filtr `market_selected` ni ham ushlardi**

- **Found during:** Task 3
- **Issue:** Reja audit mezonini "`audit_log` da `table_name='markets'`, `action='update'` yozuvi bor" deb belgilaydi. Amalda D-06 bo'yicha bozor TANLASH hodisasi ham AYNAN `table_name = 'markets'` bilan yoziladi (`AuditAction.MARKET_SELECTED`), usta oqimi esa `select-market` ni HAR DOIM chaqiradi. Ya'ni "AYNAN bitta yozuv" da'vosi har doim `2 != 1` bilan yiqilardi (dastlabki yozuvda aynan shunday bo'ldi).
- **Fix:** `_market_dml()` yordamchisi — `action in {insert, update, delete}` bo'yicha ham filtrlaydi. Da'vo KUCHSIZLANMADI: bu uchlik "yaratildi / faollashtirildi / o'chirildi" hodisalarini boshqa hech nima bilan aralashtirmaydi. Sabab yordamchining docstringida literal yozilgan.
- **Files modified:** `tests/integration/test_wizard_flow.py`
- **Verification:** `test_activation_and_deletion_are_audited_in_the_market_journal` ikkala amalni ham AYNAN 1 qator bilan tekshiradi
- **Committed in:** `accc2bf`

**9. [Rule 1 - Bug] Rejaning 5-qadamidagi ikkinchi chaqiruv FOYDASIZ edi**

- **Found during:** Task 3
- **Issue:** Reja uchidan-uchiga oqim uchun "`POST /stalls` ×3, **har rastaga `POST /stalls/{id}/category`**" deydi. Ikkinchi chaqiruv (a) keraksiz — `StallRepository.create()` boshlang'ich toifa davrini `valid_from = operating_since` bilan O'ZI yozadi, (b) faollashtirish qamroviga HECH NIMA qo'shmaydi — `set_category()` `valid_from` ni KELAJAKDA talab qiladi (T-02-61a), kelajakdagi davr esa `valid_from <= operating_since` shartiga tushmaydi. Rejaga literal ergashish "5-qadam to'liq bajarildi" degan yolg'on tuyg'u berardi va `stalls_without_category` darvozasi sinalmagan bo'lib qolardi.
- **Fix:** Oqim `POST /stalls` bilan cheklandi (sabab `_fill_wizard()` izohida), `stalls_without_category` darvozasi esa ALOHIDA holat sifatida `sbozor_owner` bilan quriladi — u aynan `market_create()` dan tashqarida tug'ilgan qatorlar uchun mavjud.
- **Files modified:** `tests/integration/test_wizard_flow.py`
- **Verification:** `test_activate_rejects_incomplete_market[stall_categories]` yashil va sabotaj #2 sinfidagi o'lchovga tayyor (shart olib tashlansa AYNAN u yiqiladi)
- **Committed in:** `accc2bf`

---

**Total deviations:** 9 auto-fixed (2 blocking, 4 missing-critical, 4 bug — #6 ikki toifada). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Birorta yangi jadval, migratsiya yoki paket qo'shilmadi (`alembic_version` `0010` bo'lib qoladi; `migrations/` va `frontend/` UMUMAN teginilmadi) va rejadan tashqari endpoint ochilmadi. Qamrov kengaytmalari ikkita: `MARKET_ERROR_CODES` ga bitta kod (`market_is_active`, 21 → 22) va cross-tenant matritsasiga YANGI tushuncha (`PLATFORM_ADMIN_ROUTES`). #1, #2, #8 va #9 rejaning O'Z bandlari orasidagi ziddiyatlar; #3, #4, #6 va #7 reja ko'rmagan to'rtta yo'lni yopadi va uchtasi sabotaj bilan o'lchandi; #5 rejaning literal ko'rsatmasining oqibatini tuzatadi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| OpenAPI'dagi usta yo'llari | ✅ `/markets` (GET+POST), `/markets/{id}` (DELETE), `/{id}/activate` (POST), `/{id}/setup-status` (GET) |
| `POST /markets` platforma admini + bozor TANLANMAGAN | ✅ **201**, `is_active: false` |
| Yaratilgandan keyin `market_profile` qatori | ✅ BOR — `operating_since`, `open_weekdays = [1..7]`, `tin` |
| `POST /markets` bozor admini | ✅ **403** `forbidden` |
| `POST /markets` tokensiz | ✅ **401** (tana yuborilgan holda ham) |
| Yaratish auditi | ✅ AYNAN 1 qator, `market_id IS NULL`, `action=insert`, `source=app`, `row_id` = yangi bozor |
| Auditda rekvizitlar | ✅ STIR ham, bank hisobi ham YO'Q (`new_value` AYNAN uchta maydon) |
| A bozorining jurnalida yaratish yozuvi | ✅ YO'Q |
| Bo'sh qoralamada `blocking` | ✅ AYNAN `[zones_missing, categories_missing, stalls_missing]`; `calendar_configured: true` |
| `blocking` tartibi | ✅ `step` bo'yicha o'sish; `blocking[0].step == min(steps)` |
| To'liq bozorda `can_activate` | ✅ `true`, `blocking == []` |
| `cameras` javobda | ✅ `0`; `blocking` da kamera bandi YO'Q |
| Sotuvchisiz bozor | ✅ `can_activate: true`, faollashtirish **200** |
| Sotuvchi qo'shilganda (nazorat) | ✅ `vendors: 1`, `blocking` hamon bo'sh |
| Tarifsiz toifa | ✅ `tariff_missing_for_category`, `step: 4`, `detail: "0/2"` |
| Chala bozorda `activate` | ✅ **409**, tanasi `{"detail": "market_incomplete", "blocking": [...]}` |
| `activate` va `setup-status` ning `blocking` lari | ✅ AYNAN TENG (oltala holatda) |
| To'liq bozorda `activate` | ✅ **200**, `is_active: true`; `GET /markets` ham `true` |
| Faollashtirish auditi | ✅ AYNAN 1 qator, `update`, `source=app`, `old={"is_active": false}` → `new={"is_active": true}` |
| Faol bozorda `activate` | ✅ **409** `market_is_active` |
| `DELETE` qoralama | ✅ **204**; `markets`/`market_profile`/`zones`/`stalls`/`tariffs` — hammasi **0** qator |
| `DELETE` jonli bozor | ✅ **409** `market_is_active`, qator JOYIDA |
| `DELETE` tokensiz | ✅ **401** |
| O'chirish auditi | ✅ AYNAN 1 qator, `delete`, `old={"name": ..., "is_active": false}` — bozor qatori yo'q bo'lgandan KEYIN ham |
| Direktor `setup-status` / `activate` | ✅ **200** (nazorat) / **403** |
| Direktor + begona bozor `setup-status` | ✅ **404**, `status != 403` alohida |
| Qoralama login javobida | ✅ BOR, `is_active: false`; A bozori `true` (nazorat) |
| Usta oqimida 403 | ✅ **0** ta (oltala qadam chaqiruvi 200/201) |
| `grep "class MarketRepository"` | ✅ `class MarketRepository:` — bazasiz |
| `grep -c "bindparam("` (`market_repo.py`) | ✅ **14** |
| `MARKET_ERROR_CODES` uzunligi | ✅ **22** (21 + `market_is_active`) |
| Cross-tenant matritsasi | ✅ 36 → **39** marshrut (20 obyekt marshruti); `EXEMPT_ROUTES` uzunligi O'ZGARMADI (**14**) |
| `PARAM_FILLERS` / `BODY_FILLERS` / `PLATFORM_ADMIN_ROUTES` | ✅ 9 / 15 / 2 |
| `git diff --name-only -- migrations/ frontend/` | ✅ BO'SH |
| `alembic_version` | ✅ **0010** (sxemaga tegilmadi) |

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 778 testning har birida.
- **Task 1 va Task 2 ning `<verify>` bandlari HALI MAVJUD BO'LMAGAN faylga tayanadi** (`test_wizard_flow.py` Task 3 da yaratiladi) — 02-09 deviatsiya #7 bilan bir xil sinf. Ekvivalent qamrov ishlatildi: har ikkala commit'da `ruff check . && ruff format --check . && mypy .` exit 0 va MAVJUD to'plam (`pytest`) to'liq yashil. Task 1 commit'i `PLATFORM_ADMIN_ROUTES` ga faqat `DELETE` ni qo'ydi (`activate` marshruti hali yo'q edi), Task 2 esa ikkinchisini qo'shdi — ya'ni ikkala commit ham o'z-o'zicha yashil.
- **`docker compose run` ichida `python -c` uchun `app`/`tenancy` paketlari topilmaydi** — `pythonpath` faqat pytest konfiguratsiyasida. Bir martalik o'lchovlar uchun `sys.path.insert(...)` qo'shildi; mahsulot kodiga ta'siri yo'q (02-10 dagi bilan bir xil).
- **`ruff format` bitta test faylini qayta formatladi** (uzun `session_headers(...)` chaqiruvi bir qatorga sig'di) — qator uzunligi darajasida.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan va birorta DTO bo'sh qolmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `frontend/src/lib/api-types.ts::ERROR_CODES` da 2-fazaning **22** kodi YO'Q | 02-13 / 02-14 | Bu reja BITTA kod qo'shdi (`market_is_active`), qarz 21 dan 22 ga o'sdi |
| `MarketRepository.rename_market()` HTTP iste'molchisisiz | 02-16 | Metod, tiplangan bind parametrlari va docstring tayyor; `PATCH /markets/{id}` marshruti usta 1-qadamiga qaytish ekrani bilan birga quriladi |
| `/markets/setup?step=N` sahifasi | 02-16 | Server kontrakti (`blocking[].step`, `?step=` semantikasi) TO'LIQ; 02-03 dagi `firstIncompleteStep()` endi HAQIQIY endpointdan o'qiydi |
| `DELETE /markets/{id}` uchun ikkinchi darajali tasdiq (UI-SPEC §10.6) | 02-16 | Serverda bunday cheklov ATAYIN yo'q — destruktiv amal matni va tasdiq dialogi FRONTEND mas'uliyati; server darvozasi (`is_active`) BIRINCHI va u DB funksiyasining ichida |
| `cameras` sanog'i doimiy `0` | 3–5 fazalar | Maydon javobda BUGUNDAN bor, ya'ni haqiqiy sanoq qo'shilganda javob SHAKLI o'zgarmaydi (D-16 ilgagi) |
| `stalls_without_category` va `calendar_missing` API orqali erishib bo'lmaydi | — | Ikkalasi ham `market_create()` dan TASHQARIDA tug'ilgan qatorlar uchun; testlar `sbozor_owner` bilan quriladi va sabab `INCOMPLETE_CASES` docstringida |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA yangi xavfsizlik yuzasi paydo bo'lmadi: qo'shilgan to'rtta marshrutning uchtasi tenant-scoped va cross-tenant matritsasiga avtomatik tushdi, to'rtinchisi (`POST /markets`) esa ikkita mustaqil darvoza ostida va uning qamrovi `test_wizard_flow.py` da qayta tiklandi. Fayl kirishi, tashqi bog'liqlik va sxema o'zgarishi YO'Q.

| Threat ID | Holat |
|-----------|-------|
| T-02-79 | mitigate — `require_platform_admin` **va** `require_permission(MARKET_MANAGE)` ikkalasi ham; `test_market_admin_cannot_create_market` → 403. Huquqning EGALIK doirasi `test_market_manage_is_platform_admin_only` bilan qulflandi (deviatsiya #4) |
| T-02-80 | mitigate — `market_create()` `is_active` ni LITERAL `false` qiladi va parametr qabul qilmaydi; faollashtirish alohida funksiya, alohida GRANT, alohida darvoza. `POST /markets` javobi har doim `is_active: false` |
| T-02-81 | mitigate — to'liqlik tekshiruvi SERVERDA (`_blocking()`); `market_activate()` parametr qabul qilmaydi, ya'ni klientdagi tugmani DevTools bilan yoqish hech nima bermaydi. Oltita bloklovchi shartning har biri alohida test bilan |
| T-02-82 | mitigate — `_own_market()` → 404 **va** `SECURITY DEFINER` chaqiruvlariga `principal.market_id` uzatiladi (ikki qatlam). **Sabotaj #1 bilan o'lchandi**: darvozasiz `setup-status` begona bozor uchun `200 {"zones":0,...}` berardi |
| T-02-83 | mitigate — `write_app_audit(TABLE_MARKETS)` uchala amalda; `old` yozuvdan OLDIN o'qiladi. Yaratish yozuvi PLATFORMA-GLOBAL (deviatsiya #5, sabotaj #4 bilan o'lchandi) |
| T-02-84 | mitigate — bank rekvizitlari va STIR auditga UMUMAN yozilmaydi (maskalash ATAYIN tanlanmadi — sabab "Decisions Made" da); test javob matnida ikkala qiymatning YO'QLIGINI tekshiradi |
| T-02-85 | mitigate — `DELETE /markets/{id}` faqat qoralama uchun; `market_delete_draft()` bayroqni ENG BOSHIDA tekshiradi. **Sabotaj #6 bilan o'lchandi**: ilova darvozasi olib tashlanganda DB qatorni SAQLAB qoldi, lekin API yolg'on `204` berardi — ya'ni ikkala qatlam ham kerak |
| T-02-86 | mitigate — nazorat 02-09 da qoladi va bu reja unga TEGMADI (`git diff --stat` da `tariff_repo.py` / `tariffs.py` YO'Q). `test_wizard_end_to_end_reaches_active_market` uni uchidan-uchiga iste'mol qiladi: 5-qadamdagi `POST /tariffs` `valid_from = operating_since` (o'tgan sana) bilan ketadi va istisno yo'qolsa test 422 bilan qulaydi |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (121 fayl, 120 manba) |
| 2 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida) |
| 3 | `npm run test:tenancy` (`pytest tests/tenancy`) | ✅ **289 passed** (02-10 dagi 268 + 21) |
| 4 | `npm run test` (`pytest`) | ✅ **778 passed** (02-10 dagi 732 + 46) |
| 5 | `app.openapi()` da usta yo'llari | ✅ 4 yo'l / 5 marshrut |
| 6 | Sabotaj o'lchovlari (6 ta) | ✅ har birida AYNAN kutilgan test(lar) yiqildi, nazoratlar yashil qoldi |
| 7 | Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `POST /markets` platforma admini (bozor tanlanmagan) → 201, `is_active: false` | ✅ |
| Yaratilgandan keyin `market_profile` qatori BOR | ✅ (`test_market_profile_is_born_with_the_market`) |
| `POST /markets` bozor admini → 403 | ✅ |
| `audit_log` da `table_name='markets'`, `action='insert'` | ✅ (platforma jurnalida — deviatsiya #5) |
| `market_repo.py` da `text(...)` chaqiruvlari `bindparams(...)` bilan | ✅ 14 ta bind |
| `MarketRepository` `TenantScopedRepository` dan meros olmaydi | ✅ `class MarketRepository:` |
| `DELETE /markets/{faol}` → 409 `market_is_active` | ✅ |
| `DELETE /markets/{qoralama}` → 204 va domen qatorlari o'chgan | ✅ beshta jadval 0 qator |
| `create_market` `TenantSessionDep` ISHLATMAYDI | ✅ `AuthSessionDep` |
| `ruff check && mypy` exit 0 | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| Bo'sh qoralamada `can_activate: false` + bloklovchi bandlar | ✅ `zones_missing`, `categories_missing`, `stalls_missing` (`calendar_missing` YO'Q — `market_create()` standart jadval yozadi) |
| `blocking` `step` bo'yicha o'sish tartibida | ✅ alohida test bilan |
| Sotuvchisiz bozorda `can_activate: true` | ✅ (D-11) |
| `cameras` javobda `0` va `blocking` da kamera bandi yo'q | ✅ (D-16) |
| Tarifsiz toifada `tariff_missing_for_category` + sonlar | ✅ `detail: "0/2"` |
| Chala bozorda `activate` → 409 va tanasida `blocking` | ✅ oltala holatda |
| To'liq bozorda `activate` → 200 + audit `update` | ✅ |
| Faol bozorda `activate` → 409 `market_is_active` | ✅ |
| Begona bozor `setup-status` → 404 (`status != 403`) | ✅ |
| `pytest tests/tenancy -q` exit 0 | ✅ 289 passed |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_wizard_flow.py` ≥7 test | ✅ **24** |
| Oqim oxirida bozor `is_active: true` | ✅ (javobdan HAM, keyingi `GET /markets` dan HAM) |
| `operating_since` O'TMISHDAGI sana | ✅ `market_today - 180 kun` (sobit sana EMAS) |
| Oqim davomida 403 YO'Q | ✅ (`test_platform_admin_can_complete_every_step`) |
| `git diff --stat` da `tariff_repo.py` / `tariffs.py` YO'Q | ✅ |
| `test_activate_rejects_incomplete_market` ≥5 shart | ✅ **6** |
| `test_vendors_do_not_block_activation` / `..._cameras_never_...` | ✅ ikkalasi + `vendors` uchun NAZORAT holati |
| `test_draft_market_is_visible_to_its_creator` | ✅ (nazorat: faol bozor `true`) |
| `test_market_admin_cannot_create_market` → 403 | ✅ |
| `npm run test` exit 0 | ✅ 778 passed |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja sxemaga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi) va `migrations/` katalogiga birorta fayl qo'shilmadi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-01]` deb yozgan. MARKET-01 ning **server yarmi** shu rejada tugadi va SC#1 API darajasida uchidan-uchiga isbotlandi, lekin u foydalanuvchi ko'radigan qobiliyat sifatida UI'siz to'liq emas: usta qobig'i (`/markets/new`, `/markets/setup?step=N`, stepper, yakuniy panel) 02-16 da quriladi. Uni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi (02-04…02-10 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-12 (import) uchun:**

- `POST /imports/stalls` yozgan har bir rasta uchun toifa davri `operating_since` bilan yozilishi SHART — aks holda `setup-status` o'sha rastalarni `stalls_without_category` deb sanaydi va bozor faollashmaydi. `StallRepository.create()` allaqachon shunday qiladi; import boshqa yo'ldan borsa, uchinchi nusxa tug'iladi.
- Import qoralama bozorda ishlaydi, ya'ni `market_delete_draft()` import qilingan qatorlarni ham o'chirishi kerak — o'n uchta jadval ro'yxati shuni qamraydi; yangi jadval qo'shilsa u ham qo'shilishi SHART.

**02-13 / 02-16 (frontend) uchun:**

- `GET /markets/{id}/setup-status` — javob shakli 02-03 dagi `setupStatusSchema` bilan MOS; `blocking[].step` (1 dan) va `blocking[].code` bor, `detail` esa **faqat sonlar** (`"0"`, `"498/512"`). Matnni frontend quradi va uchala tilga tarjima qiladi.
- `can_activate` — SERVER qarori. Uni sanoqlardan QAYTA HISOBLAMANG: to'liqlik qoidasi shu holatda ikki joyda, ikki tilda yashab, bir kun ajralib ketardi.
- 409 javobi `{"detail": "market_incomplete", "blocking": [...]}` — `blocking` `setup-status` dagi bilan AYNAN bir xil shaklda (test bilan qulflangan), ya'ni UI-SPEC §6.6 dagi "409 ro'yxatni ALMASHTIRADI" kontrakti bajarilgan. Alohida xato UI'si yozmang.
- `market_is_active` — YANGI xato kodi (22-chi). `errors.marketIsActive` matni "bozor allaqachon faol" ma'nosini berishi kerak; u `market_incomplete` dan FARQLI va `blocking` bilan kelmaydi.
- `POST /markets` javobidan keyin **`POST /auth/select-market`** MAJBURIY: yangi bozorning `mid` i tokenda bo'lmasa 2-qadam `409 market_not_selected` beradi.
- `DELETE /markets/{id}` — destruktiv amal. Server ikkinchi darajali tasdiq TALAB QILMAYDI (UI-SPEC §10.6 buni frontendga qoldiradi), lekin faol bozorni o'chirish urinishi HAR DOIM 409 beradi va tugmani yashirish server darvozasining O'RNINI BOSMAYDI.
- Kamera bo'limi: `cameras` maydoni javobda BOR va qiymati `0`. D-16 bo'yicha unga ogohlantirish rangi/ikonkasi QO'YILMAYDI (UI-SPEC §6.7 dagi QAT'IY TAQIQ ro'yxati).

**06-hisob-kitob uchun:**

- Qoralama bozor endi MAHSULOT yo'lidan tug'iladi va u `auth_list_markets()` javoblarida ko'rinadi — ya'ni **har bir mahsulot oqimi `WHERE m.is_active` ni O'ZI yozishi SHART** (Pitfall 7). Bu reja o'sha kontraktni faqat kuchaytiradi: endi qoralama bozorlar test paytida ham, jonli ishlatishda ham HAQIQATAN paydo bo'ladi.
- Faollashtirish darvozasi "har toifada `valid_from <= operating_since` bo'lgan tarif" ni TALAB qiladi, ya'ni jonli bozorda tarifsiz kun bo'lishi mumkin emas — 6-fazaning kunlik job'i buni TAXMIN qilishi mumkin, lekin baribir tekshirsin (bozor faollashgandan KEYIN yangi toifa qo'shilishi mumkin va u darvozadan o'tmaydi).

**Yangi marshrut qo'shadigan HAR KIM uchun (02-08…02-10 dan meros, endi 39 marshrut bilan qayta tasdiqlangan):**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si**;
3. marshrut TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana;
4. **(02-10):** marshrut BO'SH ro'yxat qaytarishi mumkin bo'lsa — tenant darvozasi ALOHIDA mavjudlik so'rovi bilan qo'yilsin;
5. **YANGI (02-11):** marshrut BOZOR ADMINIDA YO'Q huquqni talab qilsa — `PLATFORM_ADMIN_ROUTES` ga qo'shing. Aks holda matritsa 403 da to'xtaydi va tenant darvozasi UMUMAN sinalmaydi (sabotaj #5 bilan o'lchandi). Ro'yxatga qo'shilgan har bir marshrut uchun `test_platform_admin_routes_really_need_the_elevated_session` bozor adminining 403 ini talab qiladi — ya'ni oddiy marshrutni u yerga "yashirib" bo'lmaydi.

## Self-Check: PASSED

- Da'vo qilingan 2 yangi fayl diskda mavjud: `services/core-api/app/repositories/market_repo.py`, `tests/integration/test_wizard_flow.py`
- Da'vo qilingan 6 o'zgartirilgan fayl `git diff --stat 8e6822e..HEAD` da ko'rinadi
- Uchala vazifa commit'i git tarixida mavjud: `be6ada6`, `ee244f6`, `accc2bf`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only 8e6822e HEAD` bo'sh)
- `migrations/` va `frontend/` UMUMAN teginilmadi (`git diff --name-only` bo'sh)
- Oltita sabotajdan keyin fayllar `git checkout -- <fayl>` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi va sabotajdan keyingi to'liq darvoza (`ruff` + `mypy` + `pytest`) **778 passed** bilan yashil
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
