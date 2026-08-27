---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 07
subsystem: api
tags:
  [
    fastapi,
    rbac,
    rls,
    security-definer,
    audit,
    read-audit,
    keyset-pagination,
    multi-tenant,
    i18n,
    argon2,
    valkey,
    tdd,
  ]

# Dependency graph
requires:
  - "01-01 (compose `test` profili, `sbozor_owner`/`sbozor_app` rollari)"
  - "01-03 (sbozor_core: enums, phone.normalize_phone, security.hash_password, tenancy.TenantScopedRepository, timeutil)"
  - "01-04 (identifikatsiya sxemasi, `users` app-rolga yopiq, `SECURITY DEFINER` naqshi, `two_markets` fixture'i)"
  - "01-05 (`audit_log` + `audit_read`/`audit_append` policy'lari, `fn_audit_row()` triggeri, `business_date` generated column)"
  - "01-06 (Principal, require_permission, get_tenant_session, write_app_audit, invalidate_user_state, auth_repo, auth_seed fixture'i)"
provides:
  - "migrations 0004_user_admin — 4 `SECURITY DEFINER` funksiya (auth_create_user, auth_set_locale, auth_list_users, auth_list_markets_full)"
  - "`app.repositories.user_repo` — ikki qatlamli o'qish (RLS a'zolik -> definer profil) + `UserRepository(TenantScopedRepository)`"
  - "`app.repositories.audit_repo` — keyset sahifalash, `business_date` filtri, `mask_sensitive()`"
  - "`app.security.audit.audit_read()` — o'qish-auditi dependency fabrikasi (D-09) + `write_app_audit(track_changes=...)`"
  - "`app.api.v1.users` — 5 endpoint: ro'yxat, yaratish, bloklash, tiklash, parol tiklash"
  - "`app.api.v1.me` — `GET`/`PATCH /api/v1/me` (profil + til)"
  - "`app.api.v1.markets` — `GET /api/v1/markets` (D-06)"
  - "`app.api.v1.audit` — `GET /api/v1/audit` (D-11, D-12)"
  - "`app.schemas` — 11 yangi kontrakt shakli (`AuditQuery` query-model bilan)"
  - "tests/fixtures/admin_api.py — URL konstantalari, sessiya yordamchilari, `new_phone()`, `insert_audit_probe()`"
  - "53 ta yangi integratsiya testi (24 users + 10 me/markets + 19 audit)"
affects:
  - "01-08 (frontend: `GET /api/v1/me` va `locale` kontrakti; access token faqat xotirada)"
  - "01-09 (admin UI: foydalanuvchi boshqaruvi, audit ko'rish ro'yxati va filtrlar aynan shu shakllarga tayanadi)"
  - "01-10 (cross-tenant matritsa: users/markets/audit endpointlari uchun 404 va 0-qator da'volari tayyor)"
  - "2–7 fazalar (`audit_read()` dekoratori har bir yangi shaxsiy-ma'lumot endpointiga bir satr bilan ulanadi)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`users` ustidagi HAR QANDAY operatsiya (o'qish ham, yozish ham) `SECURITY DEFINER` yuzasidan o'tadi — GRANT berish naqshni buzardi"
    - "Ikki qatlamli o'qish: RLS ostidagi a'zolik ID'lari -> definer funksiyasi bilan profil boyitish (JOIN IMKONSIZ)"
    - "Rol berish DARAJASI matritsada emas, endpoint mantiqida — u permission emas, munosabat"
    - "COMMIT dan keyingi yon ta'sirlar `BackgroundTasks` orqali (kesh invalidatsiyasi, o'qish auditi)"
    - "O'qish auditi endpointda ANIQ e'lon qilinadi; blanket middleware ATAYIN yozilmaydi"
    - "Sahifalash kursor bilan — jurnal so'rovlar ORASIDA o'sadi, raqamli sahifalash qatorlarni takrorlardi"
    - "Cross-tenant javob HAR DOIM 404 va u mavjud bo'lmagan ID javobi bilan BAYT-BAYT bir xil"

key-files:
  created:
    - migrations/versions/0004_user_admin.py
    - services/core-api/app/api/v1/users.py
    - services/core-api/app/api/v1/me.py
    - services/core-api/app/api/v1/markets.py
    - services/core-api/app/api/v1/audit.py
    - services/core-api/app/repositories/user_repo.py
    - services/core-api/app/repositories/audit_repo.py
    - tests/fixtures/admin_api.py
    - tests/integration/test_users_api.py
    - tests/integration/test_me_locale.py
    - tests/integration/test_audit_read.py
  modified:
    - migrations/entities/functions.py
    - migrations/entities/__init__.py
    - packages/sbozor-core/sbozor_core/logging.py
    - services/core-api/app/deps.py
    - services/core-api/app/main.py
    - services/core-api/app/schemas.py
    - services/core-api/app/security/audit.py
    - tests/integration/conftest.py
    - tests/tenancy/test_meta.py
    - tests/tenancy/test_login_bootstrap.py

key-decisions:
  - "`auth_list_markets_full()` — rejadagi uchta emas, TO'RTTA funksiya: `GET /markets` kontrakti `timezone` talab qiladi, `0001` dagi `auth_list_markets()` ning qaytish tipini esa `CREATE OR REPLACE` bilan o'zgartirib bo'lmaydi"
  - "`must_change_password` `auth_create_user` ichida LITERAL `true` — parametr bo'lganida chaqiruvchi uni bir kun `false` bilan chaqirib qo'yardi"
  - "`ON CONFLICT DO NOTHING` + `NULL` qaytarish — `unique_violation` istisnosi tranzaksiyani ABORT qilib audit qatorini ham yo'qotardi"
  - "Bloklash/tiklashdan keyingi kesh invalidatsiyasi `BackgroundTasks` da — dependency tranzaksiyani endpointdan KEYIN yopadi"
  - "`GET /api/v1/me` tenant kontekstisiz ishlaydi (`market_id: null`), `GET /api/v1/markets` esa tanlangan bozorni talab qiladi (409)"
  - "`write_app_audit(track_changes=False)` — o'qish yozuvida `changed_keys` bo'sh qoladi (hech narsa o'zgarmagan)"
  - "Audit yozuvidagi `old` qiymati TAXMIN QILINMAYDI — `auth_user_state()` bilan yozuvdan oldin o'qiladi"
  - "Kursor `(at, id)` juftligi ustida va `literal(..., type_)` bilan tiplangan — tipsiz `at` mintaqasiz `timestamp` ga tushib qatorlarni o'tkazib yuborardi"

patterns-established:
  - "Pattern: rad etish YOZISHDAN OLDIN — muvaffaqiyatsiz urinishdan keyin bazada qoldiq qolmasligi ALOHIDA test bilan tekshiriladi"
  - "Pattern: '403 emas, 404' da'vosi javob TANASINI mavjud bo'lmagan ID javobi bilan bayt-bayt taqqoslab isbotlanadi"
  - "Pattern: ikki mustaqil himoya qatlami bo'lsa, ularning HAR BIRI alohida sabotaj bilan o'lchanadi va natija hujjatlashtiriladi"
  - "Pattern: API yaratgan ma'lumot uchun autouse tozalash fixture'i — seed teardown'lari uni qamramaydi"
  - "Pattern: kontrakt IKKI tilda yozilgan bo'lsa (Python enum + TypeScript massiv), test nusxani emas, FAYLNING O'ZINI o'qiydi"

requirements-completed: [FOUND-01, FOUND-03, FOUND-04]

# Metrics
duration: 50min
completed: 2026-07-29
---

# Phase 1 Plan 07: Foydalanuvchi boshqaruvi, profil va audit ko'rish Summary

**D-04 ning ikki bosqichli foydalanuvchi boshqaruvi (bozor admini o'ziga teng yoki undan yuqori rol yarata OLMAYDI — server 403 bilan majburlaydi), admin orqali parol tiklash, darhol kuchga kiradigan bloklash, DB'da saqlanadigan til tanlovi va filtrlanadigan audit ro'yxati — hamda auditni ko'rishning O'ZINI jurnalga yozadigan `audit_read()` dependency'si; 53 ta yangi test va uchta sabotaj bilan qulflangan.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-07-29T08:10:00Z
- **Completed:** 2026-07-29T09:02:00Z
- **Tasks:** 3/3
- **Files created:** 11 (modifikatsiya: 10)
- **Tests:** 323 yashil (154 unit + 42 tenancy + 127 integration; oldin 270 edi)

## Accomplishments

- **D-04 darvozasi uchta ALOHIDA rad etish bilan qulflandi va sabotaj bilan o'lchandi.** `MARKET_ADMIN_ASSIGNABLE_ROLES = frozenset({CASHIER, INSPECTOR})` qism to'plam tekshiruvi: `["cashier", "director"]` kabi ARALASH ro'yxat ham rad etiladi ("ro'yxatda bittasi ruxsat etilgan" shaklidagi tekshiruv buni o'tkazib yuborardi). Rad etish `auth_create_user` chaqirilishidan OLDIN sodir bo'ladi va alohida test bazada qoldiq yo'qligini uchala rol uchun tasdiqlaydi. **Sabotaj:** darvoza chaqiruvi olib tashlanganda 7 ta test darhol qizardi.

- **`users` jadvalining yopiqligi to'liq saqlandi — JOIN yozishning iloji ham yo'q edi.** `sbozor_app` ga `REVOKE ALL` (01-04) tufayli "a'zolik + profil" bitta so'rovda olinmaydi: har qanday JOIN `permission denied for table users` beradi. Shuning uchun o'qish IKKI qadamda — `user_market_roles` dan RLS OSTIDA ID'lar, so'ng `auth_list_users(ids)` bilan profil. Bu bo'linish yuzani ham qulflaydi: funksiya ixtiyoriy `WHERE` qabul qilmaydi, ID'lar esa birinchi qadamda RLS bilan filtrlangan — ya'ni "hamma foydalanuvchini bering" so'roviga aylantirib bo'lmaydi.

- **`TenantScopedRepository` nihoyat mahsulot yo'lida ishlatildi.** 01-03 dan beri ochiq turgan e'tibor nuqtasi (01-06 SUMMARY'da "birinchi ko'p jadvalli ORM so'rovi paydo bo'lganda hal qilinishi kerak") shu rejada hal bo'ldi — lekin kutilgandan boshqacha yo'l bilan: `column_descriptions[0]` cheklovi bu yerda UMUMAN paydo bo'lmaydi, chunki ikkinchi jadval baribir `SECURITY DEFINER` ortida va JOIN yozib bo'lmaydi. `UserRepository` va `AuditRepository` — ikkalasi ham bitta entity ustida ishlaydi, ya'ni `scoped()` to'liq ishonchli.

- **Bloklash endi MAHSULOT yo'lidan darhol kuchga kiradi.** 01-06 da kesh invalidatsiyasi testda qo'lda bajarilardi; endi uni endpointning o'zi qiladi — va aynan COMMIT dan KEYIN (`BackgroundTasks`). Teskari tartibda parallel so'rov hali commit bo'lmagan "faol" holatni qaytadan keshlab qo'yardi va bloklash TTL tugagunicha (30 s) kuchga kirmasdi. Nazorat holati sifatida `unblock` ham sinaladi: usiz "block" testi kesh butunlay o'chirilgan holatda ham yashil bo'lardi.

- **O'qish auditining "yolg'on dalil yozmaslik" kafolati IKKI mustaqil qatlamdan iborat ekani O'LCHANDI.** Dastlab kod izohi buni faqat dependency e'lon tartibi bilan tushuntirgan edi. Sabotaj buni rad etdi: tartibni almashtirganda test **baribir yashil** qoldi — chunki `BackgroundTasks` endpoint MUVAFFAQIYATLI qaytargan javobga biriktiriladi va 403/422 uchun FastAPI yangi javob quradi. Ikkalasini birga buzganda `test_rejected_request_writes_no_read_row` va `test_invalid_query_writes_no_read_row` darhol qizardi. Izoh haqiqatga moslashtirildi — ikkala mexanizm ham nomma-nom yozildi.

- **Sahifalash jurnalning O'ZI o'sib borishini hisobga oladi.** Har `GET /audit` yangi `read` qatori qo'shadi (D-09), ya'ni "birinchi sahifa" har so'rovda boshqacha. Raqamli sahifalashda bu qatorlar sahifalarni surib yuborardi va foydalanuvchi 2-sahifada 1-sahifadagi yozuvni yana ko'rardi. Kursor `(at, id)` juftligi ustida qat'iy yuqori chegara bo'lgani uchun undan keyin qo'shilgan qatorlar natijaga umuman tushmaydi — test aynan shu invariantni tekshiradi (takrorlanish yo'q, tartib buzilmaydi).

- **Til kontrakti IKKI TILDAGI ikki fayl o'rtasida test bilan bog'landi.** `sbozor_core.enums.Locale` (Python) va `frontend/src/i18n/routing.ts` (TypeScript) ajralib qolsa, `PATCH /me {"locale":"uz-Cyrl"}` 200 qaytaradi-yu, frontend o'sha qiymat uchun marshrutga ega bo'lmaydi — nosozlik backend testlarida umuman ko'rinmasdi. `test_locale_enum_matches_frontend_routing` frontend faylining O'ZINI o'qiydi, nusxasini emas.

- **Model ↔ migratsiya pariteti to'rt yangi funksiya bilan ham saqlandi.** `alembic downgrade -1 → upgrade head → downgrade base → upgrade head` xatosiz takrorlanadi; `alembic revision --autogenerate` BO'SH diff beradi (16 `PGFunction` bilan ham). Runtime image (non-root, dev bog'liqliklarsiz) qurildi va unda 13 ta API marshruti OpenAPI'da ko'rinadi — `/api/v1/auth/register` esa YO'Q.

## Task Commits

1. **Task 1: Foydalanuvchi boshqaruvi API (D-04, D-02, D-08)** — `59f6cd5` (feat)
2. **Task 2: Profil/til va bozor konteksti API (D-13, D-06)** — `8f8ce34` (feat)
3. **Task 3: Audit ko'rish API va o'qish-audit dependency'si (TDD)**
   - `7142863` (test) — RED: 19 test yiqiladi (`/api/v1/audit` marshruti yo'q)
   - `23b41a0` (feat) — GREEN: 43/43 yashil
4. **Kontrakt havolalarini kod ichida aniq nomlash** — `a92a2de` (docs)

## Files Created/Modified

**Migratsiya**

- `0004_user_admin.py` — 4 funksiya + `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`; sxemaga TEGMAYDI
- `entities/functions.py` — `USER_ADMIN_FUNCTIONS` / `USER_ADMIN_GRANT_SIGNATURES` (0001 va 0003 ro'yxatlaridan ALOHIDA)

**Marshrutlar**

| Fayl         | Endpointlar                                                     |
| ------------ | --------------------------------------------------------------- |
| `users.py`   | `GET`/`POST /users`, `POST /users/{id}/block|unblock|reset-password` |
| `me.py`      | `GET`/`PATCH /api/v1/me`                                          |
| `markets.py` | `GET /api/v1/markets`                                             |
| `audit.py`   | `GET /api/v1/audit`                                               |

**Repozitoriylar**

- `user_repo.py` — `UserRepository(TenantScopedRepository)` + modul funksiyalari (`list_profiles`, `set_locale`) bozor kontekstisiz oqim uchun
- `audit_repo.py` — `AuditRepository`, `encode_cursor`/`decode_cursor`, `mask_sensitive()`, `SENSITIVE_AUDIT_KEYS`

**Xavfsizlik qatlami**

- `security/audit.py` — `AuditReadIntent`, `audit_read()` fabrikasi, `_write_read_audit()` (yangi sessiya + alohida tranzaksiya), `write_app_audit(track_changes=...)`, `TABLE_AUDIT_LOG`

**Testlar** — 53 ta yangi

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `tests/integration/test_users_api.py` | 24 | D-04 uchta rad etish + aralash ro'yxat, qoldiqsizlik, 409, D-02 oqimi, D-08 (block/unblock), cross-tenant 404 (bayt-bayt), D-07, T-01-52 |
| `tests/integration/test_me_locale.py` | 10 | profil, til doimiyligi, 422, audit eski→yangi, D-06 ro'yxat, frontend↔backend locale pariteti |
| `tests/integration/test_audit_read.py` | 19 | D-11 (kassir/nazoratchi 403), 5 filtr, kursor davomiyligi, `limit` chegarasi, maskalash, D-09 (4 da'vo) |
| `tests/tenancy/test_meta.py` (+0) | 21 | `EXPECTED_DEFINER_FUNCTIONS` 12 → 16 |
| `tests/tenancy/test_login_bootstrap.py` (+0) | 10 | grant darvozasi endi uchala funksiya to'plamini qamraydi |

## Decisions Made

- **To'rtinchi funksiya (`auth_list_markets_full`) — tarixni qayta yozmaslik uchun.** `GET /markets` kontrakti `timezone` talab qiladi, `0001` dagi `auth_list_markets()` esa uni qaytarmaydi. Uni kengaytirish `RETURNS TABLE` imzosini o'zgartirishni bildiradi va PostgreSQL buni `CREATE OR REPLACE` bilan qabul QILMAYDI — ya'ni allaqachon qo'llangan migratsiyani qayta yozish yoki `DROP`+`CREATE` bilan `downgrade()` ga eski ta'rifni saqlab qo'yish kerak bo'lardi. Additiv funksiya ikkala narxni ham to'laydi. Ikkalasining vazifasi ham boshqacha: biri LOGIN oqimidagi bozor tanlash ro'yxati, ikkinchisi boshqaruv panelining ro'yxati.

- **`must_change_password` funksiya ichida literal.** `auth_create_user` uni parametr sifatida qabul QILMAYDI. Parametr bo'lganida bir kun kimdir uni `false` bilan chaqirib qo'yardi va "admin bergan parol har doim vaqtinchalik" (D-02) kafolati jimgina yo'qolardi. Bunday teshikning yagona kafolatlangan yopilishi — uni umuman mavjud qilmaslik.

- **`GET /api/v1/me` tenant kontekstisiz, `GET /api/v1/markets` esa kontekst bilan.** Birinchisi PROFIL (telefon, ism, til) — u bozorga tegishli emas va platforma admini uni bozor tanlashdan OLDIN ham ko'rishi kerak, aks holda til almashtirgich tanlash ekranida ishlamas edi. Ikkinchisi boshqaruv panelining ro'yxati; bozor tanlash ekranining manbai esa `POST /auth/login` javobidagi `markets` (01-06), ya'ni 409 hech qanday oqimni bloklamaydi.

- **`old` qiymati hech qachon taxmin qilinmaydi.** Dastlabki amalga oshirishda `block` audit yozuvi `old={"is_active": not is_active}` yozardi — allaqachon bloklangan foydalanuvchi uchun bu YOLG'ON eski qiymat bo'lardi. Endi holat `auth_user_state()` bilan yozuvdan oldin o'qiladi. Jurnal aynan nizoni hal qilish uchun bor, ya'ni undagi har bir qiymat o'lchangan bo'lishi kerak.

- **`changed_keys` o'qish yozuvida bo'sh.** `write_app_audit` uni `new` kalitlaridan hosil qiladi; o'qish yozuvida `new_value` da filtr TAVSIFI turadi va hech narsa o'zgarmaydi. `track_changes=False` bayrog'i mavjud xulqni saqlab, faqat shu holatni ajratadi — D-12 ning ko'rish UI'si o'sha ustunni "nima o'zgardi" deb ko'rsatadi.

- **Kursor qiymatlari `literal(..., type_)` bilan tiplangan.** Bu mypy talabi bo'lib boshlandi, lekin haqiqiy xato ekani ma'lum bo'ldi: tipsiz `datetime` `tuple_()` ichida mintaqasiz `timestamp` ga tushardi va Toshkent yarim tuni atrofida kursor bir necha qatorni o'tkazib yuborardi.

- **Maskalash ro'yxati `sbozor_core.logging.SENSITIVE_KEYS` dan ALOHIDA.** Ikkalasining mantiqi bir xil, qamrovi boshqa: biri log satrlari uchun (HTTP sarlavhalari ham bor), ikkinchisi DB USTUNLARI uchun. Ularni birlashtirish bir ro'yxatga ikkita boshqa-boshqa mas'uliyat yuklardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `GET /markets` kontraktini rejadagi uchta funksiya bilan bajarib bo'lmasdi**

- **Found during:** Task 2 (`markets.py` loyihalash)
- **Issue:** `<interfaces>` `GET /api/v1/markets` javobida `timezone` talab qiladi. Platforma admini uchun yagona manba `auth_list_markets()` (0001), u esa faqat `(market_id, market_name, is_active)` qaytaradi. `markets` jadvalidan RLS ostida o'qish faqat TANLANGAN bozorni beradi.
- **Fix:** `auth_list_markets_full()` — additiv to'rtinchi funksiya (`market_timezone` ustuni bilan; `timezone` nomi `pg_catalog` funksiyasi bilan to'qnashmasligi uchun prefikslangan).
- **Files modified:** `migrations/entities/functions.py`, `migrations/versions/0004_user_admin.py`
- **Verification:** `test_markets_list_depends_on_market_view_all` `timezone == "Asia/Tashkent"` ni tekshiradi; `test_login_bootstrap` grant darvozasi yangi to'plamni avtomatik qamradi
- **Committed in:** `8f8ce34` (funksiya `59f6cd5` da yaratilgan)

**2. [Rule 2 - Missing Critical] O'qish yozuvi YOLG'ON `changed_keys` olardi**

- **Found during:** Task 3 (GREEN)
- **Issue:** `write_app_audit` `changed_keys` ni `sorted(new)` dan hosil qiladi. O'qish yozuvida `new_value = {reason, filters, result_count}`, ya'ni jurnalda "o'zgargan ustunlar: filters, reason, result_count" degan ma'nosiz (va noto'g'ri) qator paydo bo'lardi.
- **Fix:** `track_changes: bool = True` parametri; o'qish yo'li uni `False` bilan chaqiradi. Mavjud chaqiruvchilarning xulqi O'ZGARMADI.
- **Committed in:** `23b41a0`

**3. [Rule 1 - Bug] Grep darvozasi o'z izohi bilan yiqilardi (ikki fayl)**

- **Found during:** yakuniy tekshiruv
- **Issue:** Qabul mezonlari: "`markets.py` da `BYPASSRLS` yoki superuser ishlatilmaydi", "`audit_repo.py` da `OFFSET` ishlatilmaydi", "`audit_repo.py` da `date_trunc` ishlatilmaydi". Mening docstringlarim aynan shu literal tokenlarni tushuntirish uchun ishlatgandi → grep 1 qaytarardi. Bu 01-01/01-03/01-05/01-06 dagi bilan AYNAN bir xil sinf xato (to'rtinchi takrori).
- **Fix:** Uchala izoh ma'nosini saqlagan holda literal tokensiz qayta yozildi ("qator himoyasini chetlab o'tish atributiga ega rol", "boshidan n ta qatorni tashlab yuborish shaklidagi band", "vaqt tamg'asini kunga yaxlitlovchi ifoda").
- **Verification:** `grep -ci "bypassrls|superuser" markets.py` → 0; `grep -ci "offset|date_trunc" audit_repo.py` → 0
- **Committed in:** `a92a2de` (audit_repo qismi `23b41a0` da)

**4. [Rule 2 - Missing Critical] Must-have `key_links` naqshlari kodda ko'rinmasdi**

- **Found during:** yakuniy tekshiruv
- **Issue:** Reja `users.py` → Valkey keshi bog'lanishini `user:state:` naqshi bilan, `me.py` → `users.locale` bog'lanishini `auth_set_locale` naqshi bilan e'lon qiladi. Kod ikkalasini ham ORQALI chaqiradi (`invalidate_user_state()`, `user_repo.set_locale()`), ya'ni bog'lanish fayllarda KO'RINMASDI — na greplab, na o'qib topib bo'lardi.
- **Fix:** Ikkala joyda ham haqiqiy mexanizm izohda/docstringda aniq nomlandi (Valkey kalitining to'liq shakli va `SECURITY DEFINER` funksiyasining nomi). Bu hujjat sifatida ham to'g'ri: o'qiyotgan odam "bu chaqiruv nimaga tegadi" savoliga fayldan chiqmasdan javob oladi.
- **Committed in:** `a92a2de`

**5. [Rule 1 - Bug] `block` audit yozuvi eski qiymatni TAXMIN qilardi**

- **Found during:** Task 1
- **Issue:** `old={"is_active": not is_active}` — allaqachon bloklangan foydalanuvchini qayta bloklaganda jurnalga "faol edi → bloklandi" degan yolg'on yozilardi.
- **Fix:** `auth_user_state()` bilan yozuvdan OLDIN o'qiladi; qator topilmasa `old` umuman yozilmaydi.
- **Committed in:** `59f6cd5`

**6. [Rule 3 - Blocking] mypy `tuple_()` ga xom Python qiymatini qabul qilmadi — va u haqiqiy xato edi**

- **Found during:** Task 3 (GREEN)
- **Issue:** `tuple_(AuditLog.at, AuditLog.id) < tuple_(at, row_id)` — mypy ikkita `arg-type` xatosi berdi.
- **Fix:** `literal(at, DateTime(timezone=True))` va `literal(row_id, BigInteger())`. Tekshirishda ma'lum bo'ldiki, bu faqat tip emas: tipsiz `datetime` mintaqasiz `timestamp` ga tushib, Toshkent yarim tuni atrofida kursor qatorlarni o'tkazib yuborardi.
- **Committed in:** `23b41a0`

**7. [Rule 1 - Bug] Starlette `HTTP_422_UNPROCESSABLE_ENTITY` eskirgan**

- **Found during:** Task 3 (GREEN — test chiqishida `StarletteDeprecationWarning`)
- **Issue:** Yangi kod eskirgan konstantani ishlatardi va u har `invalid_cursor` javobida ogohlantirish chiqarardi.
- **Fix:** `HTTP_422_UNPROCESSABLE_CONTENT` (RFC 9110 dagi joriy nom, bir xil 422), sabab izohda.
- **Committed in:** `23b41a0`

**8. [Rule 2 - Missing Critical] API yaratgan foydalanuvchilar testlar orasida QOLIB KETARDI**

- **Found during:** Task 1
- **Issue:** `two_markets` va `auth_seed` teardown'lari faqat O'Z seed'ini biladi. `POST /users` yaratgan `users` qatori bazada qolardi va uning telefoni keyingi testda kutilmagan `409 phone_taken` berardi (flaky, sababi ko'rinmaydigan).
- **Fix:** Testlar uchun alohida telefon diapazoni (`+99893…`, seed diapazonlaridan ajratilgan) + `tests/integration/conftest.py` da autouse tozalash fixture'i.
- **Committed in:** `59f6cd5`

**9. [Rule 3 - Blocking] Tozalash fixture'i migratsiyasiz testda yiqilardi**

- **Found during:** Task 2
- **Issue:** Autouse fixture `DELETE FROM users` ni BARCHA integratsiya testlaridan keyin bajarardi, `test_locale_enum_matches_frontend_routing` esa faqat faylni o'qiydi va bazaga umuman tegmaydi → `relation "users" does not exist`.
- **Fix:** `to_regclass('public.users')` darvozasi — sxema yo'q bo'lsa jimgina qaytiladi. Fixture'ni `migrated` ga bog'lash tozalash uchun butun bazani ko'tarishga majbur qilardi.
- **Committed in:** `8f8ce34`

**10. [Rule 1 - Bug] Kod izohi ikki qatlamdan faqat bittasini nomlagandi**

- **Found during:** yakuniy sabotaj tekshiruvi
- **Issue:** `audit.py` docstringi "rad etilgan so'rov iz qoldirmasligi dependency E'LON TARTIBI bilan ta'minlanadi" deb yozgandi. Sabotaj buni RAD ETDI: tartib almashtirilganda test baribir yashil qoldi. Ya'ni izoh haqiqatning yarmini aytardi va keyingi tahrirlovchi `BackgroundTasks` ni "oddiy optimizatsiya" deb o'zgartirib qo'yishi mumkin edi.
- **Fix:** Ikkala mexanizm ham nomma-nom yozildi, o'lchov natijasi (bittasi buzilsa test yashil, ikkalasi buzilsa qizil) hujjatlashtirildi.
- **Committed in:** `a92a2de` (izoh `23b41a0` da ham yangilangan)

### Kichik moslashtirishlar (xato emas, tanlov)

- **`tests/fixtures/admin_api.py`** rejaning fayl ro'yxatida yo'q — test infratuzilmasi (01-05 deviatsiya #5 da o'rnatilgan qoida: ulashilgan test kodi `fixtures` paketida yashaydi).
- **`tests/tenancy/test_meta.py` va `test_login_bootstrap.py`** ham ro'yxatda yo'q — to'rt yangi funksiya mavjud grant/`search_path` darvozalaridan o'tishi uchun reyestrlar kengaytirildi (aks holda ular tekshiruvdan TASHQARIDA qolardi).
- **`packages/sbozor-core/sbozor_core/logging.py`** — `temporary_password` `SENSITIVE_KEYS` ga qo'shildi (rejaning `<action>` matni buni aniq talab qiladi, lekin fayl ro'yxatida yo'q).
- **`services/core-api/app/deps.py`** — `get_auth_session` docstringi yangilandi: u endi "faqat `/api/v1/auth/*`" emas, "bozorga bog'liq bo'lmagan oqimlar" (`/api/v1/me` ham). Kod o'zgarmadi.
- **Testlar rejadagi minimumdan ko'p:** 24 (12 talab qilingan) users, 19 (12 talab qilingan) audit. Qo'shimchalari: aralash rol ro'yxati, bo'sh/noma'lum rol 422, `unblock` nazorat holati, mavjud bo'lmagan ID bilan bayt-bayt taqqoslash, kursor davomiyligi, buzuq kursor 422, 422 dan keyin o'qish yozuvi yo'qligi.
- **`PATCH /me` javobi faqat `{locale}`** — `<interfaces>` da shunday e'lon qilingan; to'liq profil kerak bo'lsa `GET /me` chaqiriladi.
- **`reset-password` dan keyin kesh invalidatsiyasi QILINMAYDI** — `user:state` keshi faqat `is_active` bayrog'ini saqlaydi, parol unga tegishli emas. Ortiqcha chaqiruv "bu yerda kesh bilan bog'liq nimadir bor" degan noto'g'ri signal berardi.

---

**Total deviations:** 10 auto-fixed — 4× Rule 1 (grep darvozasi, taxminiy `old`, eskirgan konstanta, chala izoh), 3× Rule 2 (`changed_keys`, `key_links` ko'rinmasligi, test qoldiqlari), 3× Rule 3 (`timezone` kontrakti, mypy/kursor tipi, tozalash darvozasi).
**Impact on plan:** Scope creep yo'q — barcha o'zgarishlar rejaning o'z qabul mezonlari va tahdid reyestri doirasida. Bittasi (#1) rejada ko'rinmagan cheklovni ochdi (`CREATE OR REPLACE` qaytish tipini o'zgartira olmaydi), ikkitasi (#6, #10) esa dastlab tip/hujjat muammosi bo'lib ko'ringan, lekin haqiqiy nosozlik chiqdi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Issues Encountered

- **`.env` fayli yo'q** (gitignore'da, worktree bilan kelmaydi) va mavjud `pgdata` volume'i eski parollar bilan initsializatsiya qilingan (01-05/01-06 da qayd etilgan). Foydalanuvchining dev bazasiga TEGILMADI: barcha tekshiruvlar `tests` profilidagi testcontainers orqali bajarildi. Rejaning 5-verifikatsiya qadami (`curl` bilan qo'lda) o'rniga **runtime image** qurildi va unda 13 ta marshrut OpenAPI'da tasdiqlandi.
- **Migratsiya round-trip va autogenerate pariteti vaqtinchalik test fayli bilan tekshirildi**, fayl tekshiruvdan keyin o'chirildi va commit qilinmadi (01-05/01-06 dagi bilan bir xil usul). Birinchi urinishda tekshiruv YOLG'ON-QIZIL berdi: `migrations/script.py.mako` shablonining docstringida namuna `op.create_table(...)` satrlari bor va ular "yangi operatsiya" deb hisoblanardi. Tekshiruv alembic markerlari orasidagi blokka toraytirildi.
- **Windows Git Bash yo'l konversiyasi** — `docker run` argumentlarida `MSYS_NO_PATHCONV=1` kerak bo'ldi (faqat qo'lda tekshiruvda, kodga ta'sir qilmaydi).

## Known Stubs

Yo'q. Bu rejadagi har bir endpoint, funksiya, dependency va migratsiya to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` + `valkey:9.1.1-alpine` ga qarshi tekshirilgan.

Atayin **keyingi rejalarga** qoldirilgan (stub emas, hali navbati kelmagan):

- **`market_id IS NULL` audit qatorlari HAMON hech kimga ko'rinmaydi.** 01-06 SUMMARY bu bo'shliqni 01-07 ga havola qilgandi, lekin reja `<interfaces>` da `GET /audit` ni FAQAT tenant-scoped qilib e'lon qildi va tor `SECURITY DEFINER` funksiyani task ro'yxatiga kiritmadi. `login_failed` yozuvlari to'planmoqda va ularni faqat test superuseri o'qiydi. Bu 01-09/01-10 yoki 8-fazada hal qilinishi kerak — aks holda "kim tizimga kirishga urinmoqda" savoli javobsiz qoladi. **Bu ochiq bo'shliq, qasddan qoldirilgan qaror emas.**
- **`audit_read()` ning yagona iste'molchisi — audit ko'rish UI'ning o'zi.** `vendors` va boshqa shaxsiy-ma'lumot jadvallari 2- va 7-fazalarda tug'iladi; mexanizm ularga bir satr bilan ulanadi.
- **Ko'p-bozorli foydalanuvchi UI va bozor almashtirgich** — v2 (D-05 sxemasi tayyor, UI yo'q).
- **`is_platform_admin=true` bilan foydalanuvchi yaratish yo'li yo'q** — `user_repo.create_user()` uni har doim `false` bilan yozadi. Platforma admini yaratish D-04 ning ikki bosqichli modelidan tashqarida va 1-fazada UI'si yo'q; hozircha u faqat seed/migratsiya orqali paydo bo'ladi.
- **Audit jurnalining saqlash muddati (retention)** — huquqiy ko'rik kutilmoqda (RESEARCH Open Question 5). Jurnalda o'chirish yo'li ATAYIN yo'q.

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Bitta **kutilgan** kengayish bor va u mavjud dispozitsiya ichida qoladi: `auth_list_markets_full()` — T-01-59 (`users` ga to'g'ridan-to'g'ri yozuv) doirasidagi bir xil naqsh, `search_path` pin bilan va `PUBLIC` dan yopiq; u faqat bozor KONFIGURATSIYASINI (nom, mintaqa, faollik) ochadi.

Reyestrdagi 10 ta dispozitsiya bajarildi va har biri test bilan qoplandi:

| Threat  | Qanday yopildi | Tekshiruv |
| ------- | -------------- | --------- |
| T-01-50 | `MARKET_ADMIN_ASSIGNABLE_ROLES` qism to'plam darvozasi, yaratishdan OLDIN | 3 nomlangan + 3 parametrlangan + aralash ro'yxat testi (SABOTAJ bilan sinaldi) |
| T-01-51 | A'zolik `user_market_roles` da RLS ostida tekshiriladi → 404 | `test_cross_tenant_block_and_reset_return_404`, `test_unknown_user_id_and_cross_tenant_are_indistinguishable` (bayt-bayt) |
| T-01-52 | Auditga parol/hash yozilmaydi; javobda sezgir kalitlar rekursiv maskalanadi; `censor_secrets` ga `temporary_password` | `test_temp_password_not_in_audit`, `test_sensitive_values_are_masked_in_the_response`, `test_created_user_is_visible_in_the_audit_api` |
| T-01-53 | `require_permission(AUDIT_VIEW)` — matritsada aynan uch rol | `test_cashier_cannot_view_the_audit_log`, `test_inspector_cannot_view_the_audit_log` |
| T-01-54 | `audit_read` policy'si + `AuditRepository.scoped()` ikkinchi qatlami | `test_cross_tenant_rows_are_invisible_under_every_filter` (3 filtr kombinatsiyasi) |
| T-01-55 | `audit_read()` dependency'si — endpointda aniq e'lon, alohida tranzaksiyada | `test_viewing_the_audit_log_writes_a_read_row`, `test_read_row_records_reason_filters_and_result_count`, `test_reading_does_not_recurse` |
| T-01-56 | `block`/`unblock` dan keyin `user:state:{id}` COMMIT dan KEYIN o'chiriladi | `test_block_takes_effect_on_next_request` + `test_unblock_restores_access` (nazorat holati) |
| T-01-57 | `limit <= 200` validatsiyasi + kursor sahifalash + `(market_id, at DESC)` indeksi | `test_limit_above_the_maximum_is_rejected`, `test_keyset_pagination_continues_without_gaps_or_repeats` |
| T-01-58 | `cannot_block_self` tekshiruvi | `test_cannot_block_self` |
| T-01-59 | Barcha `users` yozuvlari `SECURITY DEFINER` orqali, `search_path` pin bilan | `tests/tenancy/test_meta.py` (butun baza bo'yicha), `test_login_bootstrap.py` (grant darvozasi) |

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi.

Testlar `.env` siz ishlaydi (testcontainers Postgres + Valkey ko'taradi):

```
docker compose --profile test run --rm tests pytest -q
```

Compose stekiga qarshi ishga tushirish uchun `.env` kerak (`JWT_SECRET` kamida 32 bayt):

```
cp .env.example .env
npm run up
npm run migrate
```

## Next Phase Readiness

**Tayyor:**

- **01-09 (admin UI):** `GET/POST /users`, `POST /users/{id}/block|unblock|reset-password`, `GET/PATCH /me`, `GET /markets`, `GET /audit` — beshtasi ham OpenAPI'da va shakllari `<interfaces>` bilan aynan mos. Audit ro'yxati kursor bilan sahifalanadi (`next_cursor: null` — oxirgi sahifa).
- **01-08 (frontend):** `GET /api/v1/me` sessiya tiklash va til almashtirgich uchun; u bozor tanlanmagan holatda ham ishlaydi. `PATCH /me` dan keyin cookie'ni FRONTEND qo'yadi — server qo'ymaydi (bitta haqiqat manbai DB'da).
- **2–7 fazalar:** yangi shaxsiy-ma'lumot endpointi `Depends(audit_read("<resurs>", reason="..."))` bilan bir satrda qamraladi; yangi tenant jadvali uchun `TenantScopedRepository` naqshi ikki repozitoriyda ishlaydigan namuna bilan tayyor.

**Ochiq e'tibor nuqtalari:**

- **`market_id IS NULL` yozuvlarini o'qish yo'li HAMON YO'Q** (yuqoridagi "Known Stubs" ga qarang). Bu 01-06 dan meros qolgan bo'shliq va u shu rejada ham yopilmadi, chunki reja `GET /audit` ni tenant-scoped qilib e'lon qildi. Rejalashtiruvchi e'tiboriga: bu alohida endpoint (`GET /api/v1/audit/platform`) yoki `require_roles(PLATFORM_ADMIN)` ostidagi bayroq talab qiladi.
- **`GET /users` sahifalanmaydi.** Karmana bozorida xodimlar soni o'nlab, ya'ni MVP uchun muammo yo'q; lekin ko'p bozorli platformada bu ro'yxat o'sib boradi. Audit ro'yxatining kursor mexanizmi qayta ishlatilishi mumkin.
- **`GET /audit` javobi `actor_label` ni qaytaradi, lekin ism/telefonni EMAS.** UI "kim" ustunini `actor_user_id` orqali `GET /users` bilan bog'lashi kerak — yoki 01-09 da javobga `actor_phone` qo'shilishi kerak bo'ladi. Hozirgi shakl ataylab tor: audit javobiga profil maydonlarini qo'shish shaxsiy ma'lumot yuzasini kengaytiradi.
- **Rate-limit faqat `/auth/login` da.** `POST /users` va `POST /users/{id}/reset-password` cheklanmagan; `USER_MANAGE` huquqi bo'lgan hisob buzilgan bo'lsa u cheksiz foydalanuvchi yaratishi mumkin. Audit uni qayd etadi, lekin to'xtatmaydi. 8-fazada (mustahkamlash) ko'rib chiqilsin.
- **`.github/workflows/ci-backend.yml` bu ishni hali ko'rmadi.** Mahalliy zanjir yashil (323 test); CI'da testcontainers ikki konteyner ko'taradi.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 21 ta artefaktning (11 yangi + 10 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda.
- **Commitlar:** `59f6cd5`, `8f8ce34`, `7142863`, `23b41a0`, `a92a2de` — beshtasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only ca542f7..HEAD` bo'sh.
- **Umumiy artefaktlarga tegilmadi:** `.planning/STATE.md` va `.planning/ROADMAP.md` diffda YO'Q (worktree rejimi — ularni orkestrator yangilaydi). `frontend/` ostidagi birorta fayl ham o'zgartirilmadi (parallel agent egaligida).
- **Ishchi katalog toza:** `git status --short` bo'sh; vaqtinchalik round-trip test fayli o'chirildi.
- **Darvozalar:** `ruff check .` + `ruff format --check .` + `mypy .` (strict, 81 fayl) + `mypy services/core-api` (alohida, 21 fayl) + `pytest -q` (323 test) — hammasi yashil.
- **Migratsiya:** `downgrade -1` → `upgrade head` → `downgrade base` → `upgrade head` xatosiz; `alembic revision --autogenerate` BO'SH diff beradi (16 `PGFunction` bilan ham).
- **Runtime image:** `docker compose build core-api` muvaffaqiyatli; non-root konteynerda `app.main` import bo'ladi va 13 ta API marshruti OpenAPI'da ko'rinadi (`/api/v1/auth/register` YO'Q).
- **Sabotaj tekshiruvlari (3 ta):** (1) `_assert_roles_assignable()` chaqiruvi olib tashlanganda D-04 ning 7 ta testi yiqildi; (2) `audit.py` da dependency tartibi almashtirilganda testlar YASHIL qoldi — bu ikkinchi qatlam borligini ko'rsatdi; (3) `BackgroundTasks` o'rniga darhol yozishga o'tkazilganda (tartib buzilgan holatda) `test_rejected_request_writes_no_read_row` va `test_invalid_query_writes_no_read_row` yiqildi. Uchala o'zgarish ham qaytarildi va to'plam yana yashil.
- **Grep darvozalari:** `markets.py` da taqiqlangan tokenlar → 0; `audit_repo.py` da sahifa-o'tkazish va sana-yaxlitlash tokenlari → 0; `users.py` da `user:state:` → bor; `me.py` da `auth_set_locale` → bor; `audit.py` da `Depends(audit_read` → bor; `security/audit.py` da `def audit_read` → bor; `users.py` da `reset-password` → bor.
