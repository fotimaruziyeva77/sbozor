---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 08
subsystem: api
tags: [fastapi, pydantic, keyset, lateral, rls, rbac, mass-assignment, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-07 — `market_today`/`market_scope` fixture'lari, xato xaritasi (`23505`/`23503`/`23514`), `trg_category_period_past_immutable` ning `BEFORE UPDATE OR DELETE` ekani; 02-06 — `market_domain` seed'i (`A_STALL_CODES_BY_SORT`, tarifsiz toifa), `alembic_version = 0010`; 02-05 — `stall_code_claim()` triggeri va uning xato matni; 02-04 — `Stall.code_sort`, `StallStatus`, `MarketProfile.operating_since`"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`TenantSessionDep`/`require_permission`, `TenantScopedRepository.scoped()`, `audit_repo` keyset naqshi, `test_cross_tenant.py` avtomatik matritsasi, `main.py` global RLS handleri"
provides:
  - "`app/schemas.py` — 2-fazaning BUTUN HTTP shartnomasi (30 DTO + `MARKET_ERROR_CODES`)"
  - "`app/repositories/stall_repo.py` — `ZoneRepository` / `CategoryRepository` / `StallRepository`"
  - "`app/api/v1/zones.py`, `categories.py`, `stalls.py` — 14 marshrut"
  - "`sbozor_core.timeutil.business_today()` — ilova darvozalarining sana manbai"
  - "`tests/integration/test_stall_registry.py` — SC#2 ning API isboti (18 test)"
  - "`tests/tenancy/test_cross_tenant.py::TenantSeed` + `BODY_FILLERS` — matritsaning 2-faza kengaytmasi"
  - "`fixtures.admin_api.ZONES_URL` / `CATEGORIES_URL` / `STALLS_URL`"
affects: [02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Butun fazaning DTO to'plami BITTA rejada e'lon qilinadi — keyingi to'rt reja shakl haqida qayta qaror qabul qilmaydi"
    - "Pydantic cheklovi `Annotated[str, StringConstraints(...)] | None` shaklida ICHKI tipga qo'yiladi, union ustiga EMAS"
    - "`LEFT JOIN LATERAL` so'rovi `text()` bilan yoziladi va tenant predikati QO'LDA, ko'rinadigan joyda turadi"
    - "Bitta SQL matni uch chaqiruvchiga xizmat qiladi (`:stall_id IS NULL` tarmog'i) — «joriy toifa» ta'rifi bir joyda qoladi"
    - "Cross-tenant matritsasi tana TALAB QILADIGAN marshrutlar uchun `BODY_FILLERS` oladi — aks holda 422 da to'xtab, 404 da'vosini sinamay qo'yadi"
    - "Mexanik grep darvozasi bilan to'qnashadigan atama izohda ham YOZILMAYDI (darvoza o'z-o'ziga qarshi turmasin)"

key-files:
  created:
    - services/core-api/app/repositories/stall_repo.py
    - services/core-api/app/api/v1/zones.py
    - services/core-api/app/api/v1/categories.py
    - services/core-api/app/api/v1/stalls.py
    - tests/integration/test_stall_registry.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/main.py
    - packages/sbozor-core/sbozor_core/timeutil.py
    - tests/fixtures/admin_api.py
    - tests/fixtures/market_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "`business_today()` `sbozor_core.timeutil` ga QO'SHILDI — reja unga tayanadi, lekin funksiya mavjud emas edi"
  - "`ZoneRepository`/`CategoryRepository` Task 1 ga ko'chirildi — aks holda Task 1 commit'i o'z-o'zicha QIZIL bo'lardi"
  - "`OFFSET` so'zi `stall_repo.py` da izohda ham yozilmaydi — qabul mezoni faylni o'sha so'z bo'yicha grep qiladi"
  - "`BODY_FILLERS` qo'shildi: tanasiz `PATCH`/`POST` matritsada 422 berardi va 404 da'vosi sinalmasdi (sabotaj bilan o'lchandi)"
  - "`POST /stalls/{id}/category` javobi TANASIZ 201 — yangi davr kelajakda, `StallDetail` (bugungi holat) uni ko'rsatmasdi"
  - "Profilsiz bozorda `create()` 409 `market_incomplete` beradi — `business_today()` ga tushish 02-11 faollashtirishini jimgina o'ldirardi"
  - "`ZoneListResponse`/`CategoryListResponse` da `next_cursor` YO'Q — `<interfaces>` dagi aniq shakl umumiy qoidadan ustun"

patterns-established:
  - "Pattern: darvoza sabotaj bilan o'lchanadi va o'lchov «nechta yiqildi» dan tashqari «QAYSILARI yashil qoldi» ni ham qayd etadi"
  - "Pattern: ikkita bir xil SQLSTATE xato MATNI bo'yicha ajratiladi va ajratish ALOHIDA test bilan qulflanadi"
  - "Pattern: kolatsiyaga bog'liq tartib kutilmasi Python'da qayta qurilmaydi — DB'dan olinadi; kolatsiyaga bog'liq BO'LMAGAN qism esa qo'lda yozilgan konstantadan"

requirements-completed: []

# Metrics
duration: 60min
completed: 2026-07-31
---

# Phase 2 Plan 08: Domen shartnomasi va rasta reestri Summary

**2-fazaning butun HTTP shartnomasi (30 DTO + yigirmata xato kodi) bir modulda qotirildi va reestrning yadrosi — zonalar, toifalar, rastalar hamda plan-xarita — 14 marshrut sifatida ochildi; T-02-61a ning ILOVA darajasidagi darvozasi (DB triggeri INSERT'da ishga tushmasligi tufayli almashtirib bo'lmaydigan) beshta sabotaj o'lchovi bilan tasdiqlandi va har birida AYNAN kutilgan test yiqilib, nazorat holatlari yashil qoldi.**

## Performance

- **Duration:** ~60 min
- **Tasks:** 3/3
- **Files:** 13 (5 yaratildi, 8 o'zgartirildi)
- **Testlar:** 517 → **606** (+89: tenancy +71, integratsiya +18)
- **Marshrutlar:** matritsa 7 → **21** (`EXEMPT_ROUTES` o'zgarmadi)

## Accomplishments

- **Beshta sabotaj o'lchovi darvozalarning KUCHINI aniq ko'rsatdi va hech birida ortiqcha test yiqilmadi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | `set_category()` chegarasi `<=` → `<` | AYNAN 1: `test_today_category_valid_from_returns_403` | `test_past_category_valid_from_returns_403` ✅ va `test_future_..._201` ✅ — chegara HARFI aynan bitta test bilan qulflangan |
  | O'tmish darvozasi BUTUNLAY olib tashlandi | AYNAN 2: `test_past_...` + `test_today_...` | `test_future_..._201` ✅ va `test_new_stall_gets_initial_category_period_at_operating_since` ✅ — **ya'ni DB triggeri INSERT'da ROSTDAN ishga tushmaydi va yaratish oqimi darvozadan o'tmaydi** |
  | `RETIRED_CODE_MARKER` tarmog'i o'chirildi | AYNAN 1: `test_code_edit_returns_409_when_retired` | `test_code_edit_returns_409_when_taken` ✅ — ikki xil `23505` haqiqatan AJRATILGAN |
  | `stall_id` filleri tasodifiy UUID ga almashtirildi | AYNAN 1: `test_param_fillers_point_at_the_other_market` | qolgan 193 tenancy testi ✅ — meta-darvoza matritsaning ma'nosini ushlab turadi |
  | `PATCH /stalls/{id}` uchun `BODY_FILLERS` yozuvi o'chirildi | AYNAN 1: `test_cross_tenant_object_returns_404[PATCH_/api/v1/stalls/{stall_id}]` (422 keldi) | qolgan 114 test ✅ — `BODY_FILLERS` bezak emas, YUK KO'TARUVCHI |

  Har beshtasidan keyin fayl `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza, `git diff --stat` bo'sh).

- **T-02-61a ning ikkinchi sabotaji fazaning eng qimmat faktini o'lchadi.** Darvoza olib tashlanganda o'tgan sanali `valid_from` **jimgina 201 bilan yozildi** — ya'ni `trg_category_period_past_immutable` (`BEFORE UPDATE OR DELETE`) bu yo'lda haqiqatan hech qanday himoya bermaydi. Reja buni nazariy jihatdan da'vo qilgan edi; endi u o'lchangan.

- **Yaratish oqimi darvozadan O'TMAYDI — bu ham o'sha sabotajda ko'rindi.** `test_new_stall_gets_initial_category_period_at_operating_since` ikkala sabotajda ham yashil qoldi, ya'ni boshlang'ich davr `create()` ichkarisida, server nazoratidagi `operating_since` bilan yoziladi va u `set_category()` ga umuman kirmaydi. Usiz darvoza rasta yaratishni ham bloklab qo'ygan bo'lardi (`operating_since` — o'tgan sana).

- **Inson-raqamli tartib uchala yuzada ham o'lchandi:** ro'yxat `2, 3, 7, 10, 55, 100` (matn tartibi `10, 100, 2, 3, 55, 7` bo'lardi), keyset uch sahifada ayni tartibni saqladi va xaritada `100` bilan `3` bir zonada bo'lgani uchun `3` **oldin** turdi — bu kolatsiyaga umuman bog'liq bo'lmagan, eng o'tkir isbot.

- **Mass-assignment darvozasi IKKI TOMONLAMA tekshirildi:** `{"market_id": "<B>"}` yuborilganda qator A bozorida yaratildi **va** B bozorida yo'qligi alohida assert qilindi. Faqat birinchisi tekshirilsa, qator ikkala bozorda ham paydo bo'lgan holatda test yashil qolardi.

- **Cross-tenant matritsasi 7 dan 21 marshrutga kengaydi va `EXEMPT_ROUTES` ga BIRORTA yozuv qo'shilmadi** — 2-fazaning barcha yangi marshrutlari tenant-scoped. Har bir yangi obyekt marshruti (`zone_id`, `category_id`, `stall_id`) B bozorining HAQIQIY ID'si bilan chaqiriladi.

- **Butun faza uchun DTO shartnomasi qotdi:** `StallListResponse`, `StallMapResponse`, `TariffListResponse` (majburiy `min_valid_from`), `CalendarResponse`, `VendorListResponse`, `AssignmentItem`, `MarketCreateRequest`, `SetupStatusResponse`, `ImportErrorResponse` — 02-09…02-13 ularni import qiladi va shakl haqida qayta qaror qabul qilmaydi.

## Task Commits

1. **Task 1: Domen DTO'lari, xato kodlari va oddiy reestrlar** — `d647d22` (feat)
2. **Task 2: `stall_repo.py` va `stalls.py` — reestr, keyset, filtrlar va xarita** — `d3f8df8` (feat)
3. **Task 3: Marshrutlarni ulash, cross-tenant matritsasi va SC#2 API isboti** — `b123c9e` (test)

## Files Created/Modified

**Yaratildi**

- `services/core-api/app/repositories/stall_repo.py` — uchta repozitoriy bitta modulda (sabab docstringda: «joriy toifa» ta'rifi uch joyda takrorlanmasin). `_STALL_ROWS` — uchta `LEFT JOIN LATERAL`, uch chaqiruvchi (ro'yxat / bitta rasta / yozuvdan keyingi javob), `(code_sort, id)` keyset va `limit + 1`.
- `services/core-api/app/api/v1/zones.py` / `categories.py` — `users.py` naqshining aniq nusxasi; `GET` uchun `MARKET_DATA_VIEW`, yozuv uchun `STALL_MANAGE`; `DELETE` ikki qavatli (ilova tekshiruvi + FK poyga holati).
- `services/core-api/app/api/v1/stalls.py` — `GET /map` `GET /{stall_id}` dan OLDIN; `23514` ning YO'QLIGI sababi `#` blokida (docstringda EMAS — grep darvozasi izoh qatorlarini filtrlaydi).
- `tests/integration/test_stall_registry.py` — 18 test (reja ≥13 talab qiladi).

**O'zgartirildi**

- `services/core-api/app/schemas.py` — ~30 DTO + `MARKET_ERROR_CODES` (20 kod) + `ISO_WEEKDAYS` + `STALL_PAGE_SIZE_MAX`. Bo'lim boshida mass-assignment qoidasi LITERAL yozilgan va `SelectMarketRequest` istisnosi nomma-nom tushuntirilgan (grep qiluvchi o'quvchi uchun).
- `services/core-api/app/security/audit.py` — beshta `TABLE_*` konstantasi; izohda «bu jadvallarda DB triggeri BOR, ya'ni `write_app_audit()` chaqirilmaydi» ogohlantirishi.
- `services/core-api/app/main.py` — uchta router; izohda «yangi marshrut matritsaga AVTOMATIK tushadi, yagona qo'lda qadam — `PARAM_FILLERS`».
- `packages/sbozor-core/sbozor_core/timeutil.py` — `business_today()` (deviatsiya #1).
- `tests/fixtures/market_domain.py` — `A_OPERATING_SINCE` va `A_ZONE_NAMES` `__all__` ga (deviatsiya #8).
- `tests/tenancy/test_cross_tenant.py` — `TenantSeed`, `BODY_FILLERS`, `call_route()`, kengaytirilgan `foreign_markers()`.
- `tests/tenancy/test_route_coverage.py` — `MINIMUM_MATRIX_ROUTES` 3 → 12 (amaldagi 21 dan ATAYIN past).

## Decisions Made

- **`ZoneListResponse` va `CategoryListResponse` da `next_cursor` YO'Q.** Reja «har bir `*ListResponse` da `next_cursor`» deydi, lekin `<interfaces>` bo'limi ikkalasini ham `{items: [...]}` shaklida qat'iy belgilaydi va action «keyset paginatsiya YO'Q va buni izohda ayt» deb talab qiladi. Aniqroq spetsifikatsiya ustun turdi; sabab ikkala docstringda ham yozilgan (zona soni o'nlab, kursor mexanikasi hech nimani hal qilmaydi).
- **`POST /stalls/{id}/category` javobi TANASIZ 201.** `<interfaces>` faqat `201` deydi, javob shaklini belgilamaydi. `StallDetail` qaytarish chalg'ituvchi bo'lardi: yangi davr KELAJAKDA kuchga kiradi, ya'ni bugungi holatni ko'rsatuvchi javob «yozildimi?» savoliga yo'q deb javob berardi.
- **Xato xaritasi IKKI mustaqil funksiyaga bo'lindi** (`_stall_conflict` va `_category_period_conflict`). Bir xil `23505` ikki yo'lda butunlay boshqa ma'no beradi (kod band/chetlangan ↔ shu sanaga davr bor); bitta umumiy xaritachi ikkalasiga ham noto'g'ri kod berardi.
- **Noma'lum SQLSTATE QAYTA KO'TARILADI** (`raise exc`), «har ehtimolga qarshi 409» EMAS. Global handler uni 500 ga aylantiradi va bu to'g'ri: yangi konstrayt jimgina noto'g'ri xabar bilan yashirinmasligi kerak.
- **Zona tartibi kutilmasi DB'DAN olinadi, Python `sorted()` dan emas.** `G'arbiy` dagi apostrof turli kolatsiyada turlicha joylashadi; kutilmani Python tomonda qayta qurish ikkinchi, ajralib ketadigan haqiqat manbai bo'lardi. Katak tartibi esa qo'lda yozilgan `A_STALL_CODES_BY_SORT` dan filtrlanadi — u kolatsiyaga bog'liq emas va eng muhim holatni (`3` `100` dan oldin) qulflaydi.
- **`business_today()` chaqiruvi har so'rovda BIR MARTA** va argument sifatida repozitoriyga beriladi. Repozitoriy ichida chaqirilsa, bitta HTTP so'rovidagi ikki so'rov (yozuv + javob uchun qayta o'qish) yarim tun atrofida BOSHQA-BOSHQA biznes-kunga tushishi mumkin edi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `business_today()` reja tayanadigan, lekin MAVJUD BO'LMAGAN funksiya edi**

- **Found during:** Task 2 (`read_first` bandini bajarishda)
- **Issue:** Reja Task 2 ning `read_first` ida `packages/sbozor-core/sbozor_core/timeutil.py` — `business_today()` deb yozadi, qabul mezoni esa `grep -c business_today` natijasi 0 dan katta bo'lishini talab qiladi. Faylda faqat `now_tz()` va `business_date(moment)` bor. 02-09 rejasi ham xuddi shu funksiyaga tayanadi (`add_tariff()` darvozasi), ya'ni bu yagona reja emas, ikkita rejaning umumiy taxmini.
- **Fix:** `business_today() -> date` qo'shildi (`business_date(now_tz())` kompozitsiyasi) va `__all__` ga kiritildi. Docstringda `date.today()` NEGA ishlatilmasligi yozilgan: konteyner UTC'da ishlaydi va mahalliy 00:00–04:59 oralig'ida u OLDINGI kunni beradi — o'shanda ilova darvozasi bilan DB triggeri bir-biriga ZID javob berardi. Modul docstringidagi «qamrov ogohlantirishi» ham takrorlandi (funksiya `business_date` USTUNINI hisoblashda ishlatilmaydi).
- **Files modified:** `packages/sbozor-core/sbozor_core/timeutil.py`
- **Verification:** `tests/unit/test_timeutil.py` (18 test) yashil qoldi; sabotaj #1 va #2 aynan shu funksiyaga tayanadigan darvozani o'lchadi
- **Committed in:** `d647d22`

**2. [Rule 3 - Blocking] `ZoneRepository`/`CategoryRepository` Task 2 da e'lon qilingan, lekin Task 1 routerlariga KERAK**

- **Found during:** Task 1
- **Issue:** Reja Task 1 da `zones.py`/`categories.py` yozishni buyuradi va «routerlar `stall_repo.py` dagi `ZoneRepository`/`CategoryRepository` sinflarini chaqiradi (2-taskda)» deb yozadi. Ya'ni Task 1 commit'i mavjud bo'lmagan sinflarni import qilardi va o'z-o'zicha **QIZIL** bo'lardi — «har bir vazifa yashil commit qoldiradi» kafolati buzilardi (02-05 va 02-06 da aynan shu ziddiyat ikki marta uchragan).
- **Fix:** 02-06 deviatsiya #2 ning naqshi takrorlandi: `stall_repo.py` Task 1 da tug'iladi va unda FAQAT `ZoneRepository` + `CategoryRepository` + umumiy yordamchilar (`sqlstate_of`, `DeleteOutcome`) bo'ladi; Task 2 unga `StallRepository`, kursor yordamchilari va domen istisnolarini qo'shadi. Rejaning yakuniy holati o'zgarmadi.
- **Files modified:** `services/core-api/app/repositories/stall_repo.py` (ikki commit'da)
- **Verification:** Har uchala commit'da `ruff check && ruff format --check && mypy` exit 0 va `pytest tests/tenancy` yashil
- **Committed in:** `d647d22`, `d3f8df8`

**3. [Rule 3 - Blocking] Qabul mezoni rejaning O'Z izoh talabiga zid edi (`OFFSET`)**

- **Found during:** Task 2
- **Issue:** Task 2 action «`OFFSET` ishlatilmaydi» qoidasini o'rnatadi va modul docstringida sahifalash qarorini tushuntirishni kutadi; qabul mezoni esa `grep -n "OFFSET\|\.offset(" stall_repo.py` natijasi **0** bo'lishini talab qiladi. Qoidani izohda tushuntirish grep'ni darhol qizartiradi — ya'ni ikkala talabni bir vaqtda bajarib bo'lmaydi. `23514` uchun reja bu ziddiyatni o'zi sezib, grep'ni izoh qatorlaridan filtrlagan; `OFFSET` uchun bunday filtr yo'q.
- **Fix:** Taqiq SAQLANDI va batafsil tushuntirildi, lekin atamaning O'ZI faylda hech qayerda yozilmadi («boshidan n qatorni tashlab yubor shaklidagi SQL bandi»). Docstringda taqiqning mexanik darvoza bilan qulflangani ham aytiladi, ya'ni keyingi ishlovchi so'zni izohga qaytarib qo'ymaydi. `23514` uchun rejaning O'Z yechimi ishlatildi: sabab `#` blokida (docstringda emas).
- **Files modified:** `services/core-api/app/repositories/stall_repo.py`, `services/core-api/app/api/v1/stalls.py`
- **Verification:** `grep -c "OFFSET\|\.offset(" stall_repo.py` → **0**; `grep -v "^\s*#" stalls.py \| grep -c 23514` → **0** (filtrsiz 1)
- **Committed in:** `d3f8df8`

**4. [Rule 2 - Missing Critical] Tanasiz matritsa yangi yozuv marshrutlarini UMUMAN sinamasdi**

- **Found during:** Task 3
- **Issue:** Reja «marshrutlar `app.routes` dan avtomatik olinadi, qo'lda qilinadigan yagona ish — `PARAM_FILLERS`» deydi. Lekin 1-fazadagi obyekt marshrutlarining hech birida so'rov TANASI yo'q edi (`block`, `unblock`, `reset-password`), 2-faza esa to'rtta tanali obyekt marshrutini qo'shadi (`PATCH /zones/{id}`, `PATCH /categories/{id}`, `PATCH /stalls/{id}`, `POST /stalls/{id}/category`). FastAPI dependency'larni tanadan OLDIN hal qiladi, tanani esa keyin tekshiradi — ya'ni tanasiz so'rov autentifikatsiyadan o'tib **422** bilan tugardi va matritsaning ASOSIY da'vosi («cross-tenant obyekt 404 beradi») bu to'rtta marshrut uchun HECH QACHON bajarilmasdi. Matritsa esa yashil bo'lib turardi.
- **Fix:** `BODY_FILLERS: dict[RouteSpec, ...]` qo'shildi (`RouteSpec` bo'yicha kalitlanadi, yo'l bo'yicha emas — bitta yo'lda `PATCH` va `DELETE` birga yashaydi) va barcha matritsa testlari yagona `call_route()` yordamchisidan o'tkazildi. `valid_from` KELAJAKDA (`date.today() + 30`), aks holda 403 kelib matritsa 404 kutayotgan joyda yiqilardi. Eskirgan yozuvga qarshi `test_body_fillers_point_at_live_routes` darvozasi qo'shildi (`EXEMPT_ROUTES` uchun mavjud darvozaning naqshi).
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** **Sabotaj E** — bitta `BODY_FILLERS` yozuvi o'chirilganda AYNAN `test_cross_tenant_object_returns_404[PATCH_/api/v1/stalls/{stall_id}]` yiqildi (422 keldi), qolgan 114 test yashil qoldi
- **Committed in:** `b123c9e`

**5. [Rule 2 - Missing Critical] Profilsiz bozorda `create()` uchun sana manbai YO'Q edi**

- **Found during:** Task 2
- **Issue:** Reja `create()` ning boshlang'ich toifa davrini `market_profile.operating_since` bilan yozishni talab qiladi, lekin profil qatori BO'LMAGAN holatni umuman ko'rmaydi. Eng tabiiy «tuzatish» — `business_today()` ga tushish — 02-11 ning faollashtirish darvozasini JIMGINA o'ldirardi: u har rastada `valid_from <= operating_since` bo'lgan davrni talab qiladi va qoralama bozorning `operating_since` i o'tmishda.
- **Fix:** `MarketProfileMissingError` domen istisnosi → router uni 409 `market_incomplete` ga aylantiradi (kod allaqachon `MARKET_ERROR_CODES` da). `create()` da `operating_since` qatorlar YOZILISHIDAN OLDIN o'qiladi, ya'ni xato sabab bilan birga keladi. Istisno docstringida `business_today()` ga tushish NEGA eng xavfli yechim ekani yozilgan.
- **Files modified:** `services/core-api/app/repositories/stall_repo.py`, `services/core-api/app/api/v1/stalls.py`
- **Verification:** `test_new_stall_gets_initial_category_period_at_operating_since` — `valid_from == A_OPERATING_SINCE` (2026-01-15, o'tgan sana) va qator AYNAN bitta
- **Committed in:** `d3f8df8`

**6. [Rule 2 - Missing Critical] `q` filtri `ILIKE` naqshiga xom uzatilardi**

- **Found during:** Task 2
- **Issue:** Reja `q` uchun «kod `ILIKE` prefiks yoki sotuvchi ismi `ILIKE`» deydi, lekin `%` va `_` belgilari `ILIKE` uchun MAXSUS. `q=%` so'rovi butun reestrni qaytarardi, `q=_` esa har qanday bir belgili kodga mos kelardi — ya'ni filtr jimgina ishlamay qolardi va foydalanuvchi buni «qidiruv topmadi» deb emas, «hammasi chiqdi» deb ko'rardi.
- **Fix:** `_LIKE_SPECIALS` translyatsiya jadvali (`\`, `%`, `_` qochiriladi) va `_like_term()` yordamchisi. `ESCAPE` bandi KERAK EMAS — PostgreSQL'da `LIKE` uchun standart qochirish belgisi teskari chiziq; bu sabab konstanta docstringida yozilgan.
- **Files modified:** `services/core-api/app/repositories/stall_repo.py`
- **Verification:** `test_stall_list_respects_filters` filtrlarning SONNI o'zgartirishini tekshiradi (nazorat: filtrsiz 6)
- **Committed in:** `d3f8df8`

**7. [Rule 1 - Bug] Pydantic cheklovi union ustiga qo'yilganda JIMGINA qo'llanmasligi mumkin edi**

- **Found during:** Task 1
- **Issue:** Reja «`min_length=1` + `strip_whitespace`» deb yozadi, bu esa `Field(strip_whitespace=True)` ni taklif qiladi — lekin Pydantic v2 `Field()` da bunday argument UMUMAN yo'q (u `StringConstraints` da). Ikkinchi, nozikroq xato: `Annotated[str | None, Field(max_length=...)]` shaklida cheklov UNION ustiga tushadi va uning qo'llanishi Pydantic versiyalari orasida farq qiladi — «uzunlik chegarasi bor» deb o'ylangan joyda hech qanday chegara bo'lmasligi mumkin.
- **Fix:** Qayta ishlatiladigan `Annotated[str, StringConstraints(...)]` taxalluslari (`_NameStr`, `_CodeStr`, `_NoteStr`, ...) va ixtiyoriy maydonlar `_NoteStr | None = None` shaklida — cheklov ICHKI `str` ga tushadi. Sabab taxalluslar ustidagi izoh blokida yozilgan.
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `VendorRequest(full_name='  Ali  ', ...)` → `'Ali'` (kesildi); `WeekdaysRequest` uchala manfiy holatni ham rad etdi
- **Committed in:** `d647d22`

**8. [Rule 3 - Blocking] Seed konstantalari `__all__` da yo'q edi**

- **Found during:** Task 3
- **Issue:** API testlari boshlang'ich toifa davrining sanasini (`A_OPERATING_SINCE`) va zona nomlarini (`A_ZONE_NAMES`) tekshiradi, lekin ikkalasi ham `fixtures/market_domain.__all__` da yo'q. Ularni test faylida qayta yozish 02-06 da o'rnatilgan qoidani buzardi («testlar kutilmani seed'dan oladi») va seed qiymati o'zgarganda test jimgina eski qiymatni kutib qolardi.
- **Fix:** Ikkala konstanta `__all__` ga qo'shildi va ro'yxat ostiga sabab izohi yozildi (02-07 deviatsiya #5 ning naqshi).
- **Files modified:** `tests/fixtures/market_domain.py`
- **Verification:** `test_new_stall_gets_initial_category_period_at_operating_since` va `test_map_groups_by_zone_in_code_order` yashil
- **Committed in:** `b123c9e`

---

**Total deviations:** 8 auto-fixed (4 blocking, 3 missing-critical, 1 bug). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, migratsiya, paket yoki endpoint rejadan tashqari qo'shilmadi. #1, #2, #3 va #8 rejaning O'Z bandlari orasidagi HAQIQIY ziddiyatlar (mavjud bo'lmagan funksiya, vazifa taqsimoti, grep va izoh, seed eksporti); #4, #5 va #6 reja ko'rmagan uchta yo'lni yopadi; #7 kutubxona API'sining haqiqiy cheklovi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `MARKET_ERROR_CODES` uzunligi | ✅ **20** |
| `TariffListResponse.min_valid_from` majburiy va `date` | ✅ (`is_required()` → `True`) |
| `grep "float\|Decimal" schemas.py` | ✅ **0** |
| `schemas.py` da `market_id` maydoni bor so'rov modeli | ✅ faqat `SelectMarketRequest` (auth bootstrap, D-06) |
| `VendorRequest(phone='901234567')` | ✅ `+998901234567` |
| `WeekdaysRequest([3,1,2])` | ✅ `[1,2,3]` (barqaror tartib) |
| `WeekdaysRequest` — takror / oraliqdan tashqari / bo'sh | ✅ uchalasi ham rad etildi |
| `grep "OFFSET\|\.offset(" stall_repo.py` | ✅ **0** |
| `grep -v '^\s*#' stall_repo.py \| grep -c business_today` | ✅ **4** (kodda, izohda emas) |
| `grep -v '^\s*#' stalls.py \| grep -c 23514` | ✅ **0** (filtrsiz 1 — `#` blokida) |
| `grep "payload.market_id\|body.market_id" stalls.py` | ✅ **0** |
| `@router.get("/map")` vs `@router.get("/{stall_id}")` | ✅ 267-qator vs 302-qator |
| OpenAPI'dagi yangi yo'llar | ✅ 8 yo'l / **14 marshrut** |
| `GET /stalls` tartibi | ✅ `2, 3, 7, 10, 55, 100` |
| `GET /stalls?limit=2` | ✅ 3 sahifa, takror YO'Q, oxirgi sahifada `next_cursor = null` |
| `?status=closed` / `?status=active` / `?zone=` | ✅ `1` / `5` / `2` (nazorat: filtrsiz `6`) |
| `GET /stalls/map` — zona tartibi | ✅ DB'ning `ORDER BY name` javobi bilan bayt-bayt teng |
| Xaritada `100` va `3` bir zonada | ✅ `3` OLDIN (kolatsiyaga bog'liq emas) |
| Xarita katagida `tone` | ✅ YO'Q; `has_vendor` BOR |
| A tokeni + B rastasi | ✅ **404**, `status != 403` alohida |
| B ning `zone_id` si bilan yaratish | ✅ **404** va noma'lum UUID bilan BAYT-BAYT bir xil |
| `{"market_id": "<B>"}` tanada | ✅ A da 1 qator, B da **0** qator |
| Kod tahriri: chetlangan / band | ✅ `stall_code_retired` / `stall_code_taken` |
| `active → maintenance → closed` auditi | ✅ 2 ta `update`, `old→new` zanjiri to'g'ri, `changed_keys` da `status` |
| Direktor `POST /stalls` / `GET /stalls` | ✅ **403** `forbidden` / **200** (nazorat) |
| Toifa davri: kelajak / bugun / o'tmish | ✅ **201** / **403** / **403** |
| Yangi rastaning boshlang'ich davri | ✅ AYNAN 1 qator, `valid_from = 2026-01-15` (`operating_since`) |
| Takroriy zona nomi / rastasi bor zona `DELETE` | ✅ 409 `zone_name_taken` / 409 `zone_in_use` (nazorat: bo'sh zona → **204**) |
| B bozorining tarifsiz toifasi | ✅ `current_tariff_soum = null` (nazorat: ikkinchisi `7000`) |
| Cross-tenant matritsasi | ✅ 7 → **21** marshrut; `EXEMPT_ROUTES` uzunligi O'ZGARMADI (14) |

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 606 testning har birida.
- **`docker compose run` ichida `python -c` uchun `app` paketi topilmaydi** — `pythonpath` faqat pytest konfiguratsiyasida (`pyproject.toml`). Bir martalik tekshiruvlar uchun `sys.path.insert(0, '/app/services/core-api')` ishlatildi; mahsulot kodiga ta'siri yo'q.
- **`ruff format` uchta faylni qayta formatladi** (uzun `Annotated[...]` va uzun `select(...)` konstruksiyalari) — hammasi qator uzunligi darajasida.
- **Toifa darvozasi to'rtligining ikkitasi ATAYIN parametrizatsiya QILINMADI.** Dastlab `test_category_valid_from_in_the_past_is_locked[past|today]` shaklida yozilgan edi, lekin `02-VALIDATION.md` dagi nomlar (`test_past_category_valid_from_returns_403`, `test_today_category_valid_from_returns_403`) traceability jadvalining kaliti — ularni parametr ichiga yashirish «test bor» da'vosini `grep` bilan tekshirib bo'lmaydigan holga keltirardi.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan va birorta DTO bo'sh qolmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `frontend/src/lib/api-types.ts::ERROR_CODES` da 2-fazaning 20 kodi YO'Q | 02-13 / 02-14 | `MARKET_ERROR_CODES` docstringida MAJBURIYAT sifatida yozilgan; ko'zguda yo'q kod xavfsizlik teshigi emas — `api-client` uni `errors.generic` ga tushiradi va aniq sabab yo'qoladi |
| `TariffListResponse.min_valid_from` — faqat SHAKL | 02-09 | Qiymat 02-09 da hisoblanadi (qoralama bozorda `operating_since`, faol bozorda `business_today() + 1`); maydon docstringida «bu DARVOZA EMAS» yozilgan |
| `TariffItem`, `CalendarResponse`, `VendorListItem`, `AssignmentItem`, `SetupStatusResponse`, `Import*` — faqat SHAKL | 02-09…02-12 | Endpointlar hali yo'q; DTO'lar ATAYIN oldindan qotirilgan (rejaning maqsadi) |
| Sotuvchi ma'lumotini O'QISH auditi (D-09, Pattern 10) | 02-10 | `TABLE_VENDORS` konstantasi tayyor, `audit_read()` dependency'si 1-fazadan mavjud |
| `POST /stalls` da `note` uzunligi 500 belgi — UI cheklovi bilan solishtirilmagan | 02-14 | Chegara serverda; UI matn maydonining `maxlength` i unga MOS bo'lishi kerak |

## Threat Flags

Yangi xavfsizlik yuzasi rejaning `<threat_model>` idan TASHQARIDA paydo bo'lmadi: qo'shilgan 14 marshrutning hammasi tenant-scoped, `require_permission` ostida va cross-tenant matritsasiga avtomatik tushgan. Fayl kirishi, tashqi bog'liqlik va sxema o'zgarishi YO'Q.

| Threat ID | Holat |
|-----------|-------|
| T-02-54 | mitigate — birorta domen so'rov modelida `market_id` maydoni yo'q; `test_market_id_in_body_is_ignored` IKKI TOMONLAMA (A da bor, B da yo'q) |
| T-02-55 | mitigate — `_not_found()` uchala routerda; `test_cross_tenant_stall_returns_404` da `status != 403` alohida; matritsa 10 obyekt marshrutini avtomatik qamraydi |
| T-02-56 | mitigate — composite FK → `23503` → **404**; `test_stall_with_foreign_zone_returns_404` javobni noma'lum UUID bilan BAYT-BAYT solishtiradi |
| T-02-57 | mitigate — `require_permission(STALL_MANAGE)`; `test_director_cannot_manage_stalls` nazorat holati (`GET` → 200) bilan |
| T-02-58 | mitigate — `IntegrityError` `sqlstate` bo'yicha aniq `detail` kodiga aylanadi; xom matn faqat log'ga; noma'lum SQLSTATE qayta ko'tariladi |
| T-02-59 | mitigate — `STALL_PAGE_SIZE_MAX = 200` (`Field(ge=1, le=...)`); qator tashlab yuboradigan SQL bandi umuman yo'q (grep bilan qulflangan) |
| T-02-60 | mitigate — kursor RLS predikatidan KEYIN qo'llanadi; buzuq kursor 422 `invalid_cursor`; `bindparam(type_=...)` bilan tiplangan solishtiruv |
| T-02-61 | mitigate — `fn_audit_row()` triggeri; `test_stall_status_transitions_are_audited` `old→new` zanjirini va `changed_keys` ni tekshiradi |
| T-02-61a | mitigate — `set_category()` ilova darvozasi; **ikki sabotaj bilan tasdiqlandi**: darvoza olib tashlanganda o'tgan sana JIMGINA 201 bilan yozildi (DB triggeri INSERT'da ishlamasligi o'lchandi), chegara `<` ga o'zgarganda esa AYNAN `bugun` holati yiqildi |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (108 fayl, 107 manba) |
| 2 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida) |
| 3 | `npm run test:tenancy` (`pytest tests/tenancy`) | ✅ **194 passed** (02-07 dagi 123 + 71) |
| 4 | `npm run test` (`pytest -q`) | ✅ **606 passed** (02-07 dagi 517 + 89) |
| 5 | `app.openapi()` da `/api/v1/stalls*` | ✅ 4 yo'l (`/stalls`, `/stalls/map`, `/stalls/{id}`, `/stalls/{id}/category`) |
| 6 | Sabotaj o'lchovlari (5 ta) | ✅ har birida AYNAN kutilgan test(lar) yiqildi, nazoratlar yashil qoldi |
| 7 | Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `StallListResponse`, `StallMapResponse`, `TariffListResponse`, `CalendarResponse`, `VendorListResponse`, `AssignmentItem`, `MarketCreateRequest`, `SetupStatusResponse`, `ImportErrorResponse` importi | ✅ |
| `TariffListResponse.min_valid_from` majburiy (`\| None` emas) | ✅ |
| `MARKET_ERROR_CODES` uzunligi 20 | ✅ |
| So'rov modelida `market_id` YO'Q | ✅ (yagona uchrash — `SelectMarketRequest`, 1-faza) |
| `float`/`Decimal` yo'q | ✅ 0 |
| `VendorRequest` da `normalize_phone` | ✅ |
| `POST /zones` takroriy nom → 409 `zone_name_taken` | ✅ |
| `DELETE /zones/{id}` rastasi bor zona → 409 `zone_in_use` | ✅ (nazorat: bo'sh zona → 204) |
| `GET /categories` tarifsiz toifa → `null` | ✅ (nazorat: tarifi bor toifa → 7000) |
| `ruff check && mypy` exit 0 | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `OFFSET`/`.offset(` grep → 0 | ✅ |
| Kursor `(code_sort, id)` + `limit + 1` | ✅ |
| `?limit=2` → 2 element + `next_cursor`; keyingi sahifa takrorlanmaydi | ✅ (3 sahifa) |
| Tartib `2, 3, 7, 10, 55, 100` | ✅ |
| `/stalls/map` da `tone` yo'q, `has_vendor` bor | ✅ |
| `@router.get("/map")` `{stall_id}` dan oldin | ✅ |
| Begona `zone_id` bilan `POST /stalls` → 404 | ✅ (403 EMAS, alohida assert) |
| Kelajakdagi `valid_from` → 201 | ✅ |
| O'tgan `valid_from` → 403 `category_period_past_locked` | ✅ |
| Bugungi `valid_from` → 403 | ✅ (sabotaj bilan chegara harfi tasdiqlandi) |
| `business_today` kodda (izohda emas) | ✅ 4 uchrash |
| `23514` kodda yo'q | ✅ 0 |
| `POST /stalls` dan keyin `valid_from = operating_since` | ✅ |
| `payload.market_id` grep → 0 | ✅ |
| `ruff check && mypy` exit 0 | ✅ |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| OpenAPI'da `/zones`, `/categories`, `/stalls`, `/stalls/map` | ✅ |
| `pytest tests/tenancy -q` exit 0; `EXEMPT_ROUTES` uzunligi o'zgarmagan | ✅ 194 passed, 14 istisno |
| `PARAM_FILLERS` da `zone_id`, `category_id`, `stall_id` — B bozorining haqiqiy ID'lari | ✅ (sabotaj D bilan tasdiqlandi) |
| `test_stall_registry.py` ≥13 test | ✅ **18** |
| Toifa davri to'rtligi mavjud va yashil | ✅ to'rttasi ham |
| `test_cross_tenant_stall_returns_404` da `status != 403` alohida | ✅ |
| `test_market_id_in_body_is_ignored` | ✅ (ikki tomonlama) |
| `test_director_cannot_manage_stalls` nazorat bilan | ✅ |
| `xfail`/`skip(` `test_route_coverage.py` da | ✅ 0 |
| `npm run test && npm run test:tenancy` exit 0 | ✅ |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja sxemaga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi).

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-02, MARKET-06]` deb yozgan. MARKET-02 (rastalar reestri) va MARKET-06 (plan-xarita) ning **backend yarmi** shu rejada tugadi, lekin ikkalasi ham foydalanuvchi ko'radigan qobiliyat sifatida UI'siz to'liq emas: reestr ekrani 02-14 da, xarita komponenti 02-16 da quriladi. Ularni bu yerda «bajarildi» deb belgilash traceability jadvalini yolg'on qilardi (02-04…02-07 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-09…02-13 uchun QOTIRILGAN shartnoma (import qiling, qayta e'lon QILMANG):**

- **DTO'lar:** `TariffItem`/`TariffCreateRequest`/`TariffListResponse`, `CalendarResponse`/`WeekdaysRequest`/`CalendarExceptionRequest`, `VendorListItem`/`VendorRequest`/`VendorListResponse`, `AssignmentItem`/`AssignmentCreateRequest`/`AssignmentCloseRequest`, `MarketCreateRequest`/`MarketCreateResponse`/`SetupStatusResponse`/`BlockingItem`, `ImportResultResponse`/`ImportErrorItem`/`ImportErrorResponse`.
- **Xato kodlari:** `MARKET_ERROR_CODES` — yigirmata. Yangi kod qo'shish shu ro'yxatni va `frontend/src/lib/api-types.ts::ERROR_CODES` ni BIRGA yangilashni talab qiladi.
- **Router naqshi:** `zones.py` — eng qisqa va to'liq namuna (`_market_id`, `_not_found`, `_conflict`, `StallManagerDep`/`MarketDataViewerDep`).
- **Xato xaritasi:** `sqlstate_of(exc)` + har endpoint uchun O'Z xaritachisi. Bitta umumiy xaritachi yozmang — bir xil `23505` turli yo'llarda turli ma'no beradi.
- **Sana darvozasi:** `business_today()` (`date.today()` EMAS). 02-09 `add_tariff()` uchun shakl `set_category()` da tayyor — farq faqat qoralama bozor istisnosida (`T-02-63a`).
- **Keyset:** `encode_stall_cursor`/`decode_stall_cursor` — `(text, uuid)` juftligi uchun namuna; `InvalidCursorError` → 422 `invalid_cursor`.

**02-14…02-16 (frontend) uchun:**

- `GET /stalls` — `next_cursor` bilan `useInfiniteQuery`; tartib SERVERDA, qayta saralamang.
- `GET /stalls/map` — `zones[].cells[]`, `tone` YO'Q: `toneOf(status)` frontendda (`status` + `has_vendor` dan).
- `POST /stalls/{id}/category` — 403 `category_period_past_locked` ni `stalls.categoryPastLocked` matniga aylantiring; sana maydonining `min` atributi QULAYLIK, darvoza emas.

**Yangi marshrut qo'shadigan HAR KIM uchun:**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si**;
3. marshrut TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana (aks holda matritsa 422 da to'xtab, 404 da'vosini sinamaydi).

Uchtasidan biri unutilsa `test_no_unclassified_routes` yoki `test_cross_tenant_object_returns_404` darhol qizaradi.

## Self-Check: PASSED

- Da'vo qilingan 5 yangi fayl diskda mavjud: `services/core-api/app/repositories/stall_repo.py`, `services/core-api/app/api/v1/zones.py`, `services/core-api/app/api/v1/categories.py`, `services/core-api/app/api/v1/stalls.py`, `tests/integration/test_stall_registry.py`
- Da'vo qilingan 8 o'zgartirilgan fayl `git diff --stat 6b64755..HEAD` da ko'rinadi
- Uchala vazifa commit'i git tarixida mavjud: `d647d22`, `d3f8df8`, `b123c9e`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only 6b64755 HEAD` bo'sh)
- Beshta sabotajdan keyin fayllar `git checkout -- <fayl>` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
