---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 06
subsystem: api
tags:
  [
    fastapi,
    auth,
    jwt,
    rbac,
    argon2,
    refresh-rotation,
    reuse-detection,
    rate-limit,
    valkey,
    rls,
    security-definer,
    audit,
    tdd,
  ]

# Dependency graph
requires:
  - "01-01 (compose `test` profili, `app/settings.py`, `ops/nginx/nginx.conf` bitta domen topologiyasi)"
  - "01-03 (sbozor_core: security.py to'liq, phone.normalize_phone, tenancy.set_tenant_context, logging, enums)"
  - "01-04 (identifikatsiya sxemasi, `SECURITY DEFINER` login funksiyalari, `two_markets` fixture'i)"
  - "01-05 (audit_log jadvali + policy'lari, tenant_session ning actor_kind/request_id plumbing'i)"
provides:
  - "`app.security.rbac` — Permission (13) + ROLE_PERMISSIONS (kodda qat'iy, D-07) + permissions_for()"
  - "`app.security.tokens` — issue_access/issue_refresh/decode + refresh cookie atributlari (bitta joyda)"
  - "`app.security.audit` — write_app_audit (`source='app'`) + platform_admin_label (D-06)"
  - "`app.security.ratelimit` — Valkey sanagichi telefon (10/15daq) va IP (50/15daq) kesimida"
  - "`app.repositories.auth_repo` — 12 `SECURITY DEFINER` funksiyaga tiplangan o'ram"
  - "`app.deps` — Principal, get_current_principal (bloklash keshi), get_tenant_session, require_permission/require_roles"
  - "`app.schemas` — login/select-market/refresh/change-password/me kontraktlari"
  - "`app.api.v1.auth` — 6 endpoint: login, select-market, refresh, logout, change-password, me"
  - "`app.main` — CorrelationIdMiddleware, configure_logging, Sentry PII filtri, RLS -> 404 tarjimasi, app.state.sessionmaker"
  - "migrations 0003_auth_support — 8 ta `SECURITY DEFINER` funksiya (parol yozish + refresh_tokens lifecycle)"
  - "tests/fixtures/auth_users.py — AuthSeed (haqiqiy Argon2 hash, bloklangan va majburiy-almashtirish holatlari)"
  - "tests/fixtures/auth_api.py — URL konstantalari + audit/refresh o'qish yordamchilari"
  - "conftest: valkey_url/valkey_client (testcontainers), api_engine/api_sessionmaker, test_settings, api_app, api_client, sync_superuser_conn"
  - "53 ta yangi test (9 RBAC unit + 44 auth integratsiya)"
affects:
  - "01-07 (foydalanuvchi boshqaruvi: `auth_set_active` + `invalidate_user_state` tayyor; `require_permission` har yozuv endpointida)"
  - "01-08 (frontend: `<interfaces>` dagi HTTP kontrakti va `GET /auth/me` shu yerda qat'iylashtirildi)"
  - "01-09/01-10 (audit ko'rish UI va cross-tenant matritsa `Principal` + `get_tenant_session` ustiga quriladi)"
  - "2–7 fazalar (har bir yangi endpoint `require_permission(...)` + `get_tenant_session` naqshini takrorlaydi)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth endpointlari tenant kontekstisiz sessiyada — bozor login natijasida aniqlanadi (Pitfall 3)"
    - "`refresh_tokens` ham `SECURITY DEFINER` ortida: cookie kelganda bozor noma'lum, RLS `jti` qidiruvini 0 qatorga tushiradi"
    - "Rad etish yo'llarida audit COMMIT qilinib, KEYIN `HTTPException` — rollback jurnalni o'chirib yubormasin"
    - "`audit_log` ga INSERT xom `text()` bilan: ORM `RETURNING` SELECT policy'sini ishga tushiradi"
    - "`HTTPException(headers=...)` — cookie o'chirish istisno bilan BIRGA uzatiladi, `Response` obyektiga emas"
    - "Bitta o'g'irlik = bitta ogohlantirish: o'lik oilaga urinish yangi audit signali yozmaydi"
    - "Ilova resurslari `app.state` da; dependency'lar `request.app.state` dan oladi -> test prod kodini ishga tushiradi"
    - "Nazorat holati testi majburiy: keshning ishlayotgani 'stale' testi bilan isbotlanadi"

key-files:
  created:
    - services/core-api/app/deps.py
    - services/core-api/app/schemas.py
    - services/core-api/app/security/__init__.py
    - services/core-api/app/security/rbac.py
    - services/core-api/app/security/tokens.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/security/ratelimit.py
    - services/core-api/app/repositories/__init__.py
    - services/core-api/app/repositories/auth_repo.py
    - services/core-api/app/api/__init__.py
    - services/core-api/app/api/v1/__init__.py
    - services/core-api/app/api/v1/auth.py
    - migrations/versions/0003_auth_support.py
    - packages/sbozor-core/sbozor_core/py.typed
    - tests/unit/test_rbac_matrix.py
    - tests/integration/test_auth_login.py
    - tests/integration/test_auth_refresh.py
    - tests/integration/test_user_block.py
    - tests/fixtures/auth_users.py
    - tests/fixtures/auth_api.py
  modified:
    - services/core-api/app/main.py
    - migrations/entities/functions.py
    - migrations/entities/__init__.py
    - tests/conftest.py
    - tests/tenancy/test_meta.py
    - tests/tenancy/test_login_bootstrap.py
    - pyproject.toml

key-decisions:
  - "`refresh_tokens` uchun 5 ta yangi `SECURITY DEFINER` funksiya — rejada yo'q edi, lekin usiz `/refresh` UMUMAN ishlamasdi (RLS `jti` qidiruvini 0 qatorga tushiradi)"
  - "Bozor tanlanmagan sessiyaga refresh cookie BERILMAYDI — `refresh_tokens.market_id` NOT NULL; cookie `/select-market` da beriladi"
  - "`GET /auth/me` qo'shildi (rejada yo'q): `get_tenant_session` aks holda ishlatilmagan va sinalmagan qolardi"
  - "`audit_log` ga INSERT xom `text()` + tiplangan bindparam bilan — ORM `insert()` `RETURNING` qo'shib SELECT policy'siga uriladi"
  - "Parol siyosati `schemas.validate_password_strength()` da, `field_validator` da EMAS — kontrakt 400 talab qiladi, Pydantic 422 berardi"
  - "`is_active` tekshiruvi parol tekshiruvidan KEYIN — bloklangan hisob tezroq javob qaytarmasligi uchun"
  - "Bitta o'g'irlik = bitta `refresh_reuse_detected`: o'lik oilaga keyingi urinishlar signal yozmaydi"
  - "`sync_superuser_conn` fixture'i faqat `market_id IS NULL` audit qatorlarini O'QISH uchun; hech qanday izolyatsiya da'vosi u bilan tekshirilmaydi"
  - "`sbozor_core/py.typed` qo'shildi — `mypy services/core-api` alohida chaqirilganda ham yashil bo'lishi uchun"

patterns-established:
  - "Pattern: enumeration testi javob TANASINI bayt-bayt taqqoslaydi, status kodini emas"
  - "Pattern: kesh testi yoniga 'stale' NAZORAT HOLATI yoziladi — keshning haqiqatan ishlayotganini isbotlaydi"
  - "Pattern: integratsiya testi `app.main.app` ning O'ZINI ishlatadi, faqat `app.state` ni almashtiradi"
  - "Pattern: test DB'ga mahsulot qila olmaydigan yo'l bilan tegmaydi (`set_user_active` -> `auth_set_active`)"
  - "Pattern: har bir xavfsizlik da'vosi SABOTAJ bilan sinaladi (3 ta bajarildi)"

requirements-completed: [FOUND-01, FOUND-03]

# Metrics
duration: 50min
completed: 2026-07-29
---

# Phase 1 Plan 06: Auth yuzasi — login, sessiya siyosati va RBAC Summary

**Telefon+parol login, bozor konteksti tanlash, refresh rotatsiyasi va o'g'irlik aniqlash, majburiy parol almashtirish hamda kodda qat'iy rol-huquq matritsasi — 53 ta yangi test bilan qoplangan va uchta sabotaj bilan sinalgan; yo'l-yo'lakay `/refresh` ni butunlay ishlamas qiladigan RLS qopqoni va login endpointini 404 qiladigan `RETURNING` teshigi ochilib yopildi.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-07-29T12:15:00Z
- **Completed:** 2026-07-29T13:05:00Z
- **Tasks:** 3/3
- **Files created:** 20 (modifikatsiya: 7)
- **Tests:** 270 yashil (154 unit + 42 tenancy + 74 integration; oldin 217 edi)

## Accomplishments

- **`/refresh` ni ishlamas qiladigan qopqon rejadan oldin topildi.** `refresh_tokens` tenant-scoped (RLS ENABLE+FORCE), refresh cookie kelganda esa bozor **hali noma'lum** — `mid` claim'i refresh tokenga 01-03 da ATAYIN yozilmagan. Ya'ni `jti` bo'yicha global qidiruv RLS ostida **0 qator** qaytaradi va sessiya uzaytirish HECH QACHON ishlamasdi. Bu Pitfall 3 ning aynan o'sha mexanizmi, faqat `users` emas, `refresh_tokens` ustida. Sxema buni allaqachon ko'zlagan edi (`uq_refresh_tokens_jti` — `market_id` bilan boshlanmaydigan yagona indeks, meta-testda "cookie kelganda bozor hali noma'lum" izohi bilan), lekin yechim qo'yilmagan edi. `0003_auth_support` beshta tor `SECURITY DEFINER` funksiya bilan yopdi.

- **Login endpointini butunlay o'chiradigan `RETURNING` teshigi.** `insert(AuditLog)` SQLAlchemy'da `RETURNING id` qo'shadi (`Identity(always=True)` kaliti shu yo'l bilan olinadi), PostgreSQL esa `INSERT ... RETURNING` da qaytariladigan qatorga **SELECT policy'sini** qo'llaydi. `audit_log` da u tenant-scoped, auth oqimida esa tenant konteksti yo'q → har bir login `new row violates row-level security policy` bilan yiqilib, global exception handler orqali **404** qaytarardi. Birinchi integratsiya yugurishida 36 test bir vaqtda qizarib buni ko'rsatdi.

- **Jimgina ishlamaydigan cookie tozalash.** `clear_refresh_cookie(response)` dan keyin `raise HTTPException(...)` — FastAPI istisno uchun **yangi javob** quradi va uzatilgan `Response` sarlavhalari unga ko'chmaydi. Ya'ni reuse aniqlanganda server tomonda token bekor qilinardi, brauzerda esa o'lik cookie qolib, foydalanuvchi har so'rovda 401 olardi va sababini tushunmasdi. `cleared_cookie_headers()` sarlavhani istisno bilan BIRGA uzatadi va test uni tekshiradi.

- **Enumeration uchala yo'lda bayt darajasida yopildi.** Mavjud bo'lmagan telefon, noto'g'ri parol va **bloklangan foydalanuvchi** — uchalasi ham `401 {"detail":"invalid_credentials"}`. Test `response.json()` VA `response.content` ni taqqoslaydi. Vaqt farqi ham yopilgan: telefon topilmasa `dummy_verify()` chaqiriladi, `is_active` tekshiruvi esa parol tekshiruvidan KEYIN turadi (aks holda bloklangan hisob Argon2 ishisiz tezroq javob qaytarardi). **Sabotaj bilan sinaldi:** bloklash javobini `account_blocked` ga o'zgartirganda test darhol qizardi.

- **Reuse detection uchdan-uchiga isbotlandi.** O'g'irlangan (rotatsiya qilingan) token qaytib kelganda: (1) u 401 oladi, (2) **eng yangi, haqiqiy token ham** 401 oladi — oila bekor qilingan, (3) `audit_log` da `refresh_reuse_detected` yozuvi paydo bo'ladi, (4) brauzerdagi cookie tozalanadi. Rotatsiya `UPDATE ... WHERE revoked_at IS NULL` ichida bajariladi, ya'ni ikki parallel `/refresh` dan faqat bittasi g'olib chiqadi (oldin `SELECT`, keyin `UPDATE` qilish poyga oynasi qoldirardi). **Sabotaj bilan sinaldi.**

- **Bloklash uchta alohida da'vo bilan qoplandi.** (a) NAZORAT HOLATI: invalidatsiyasiz bloklash TTL tugagunicha kuchga kirmaydi — ya'ni kesh haqiqatan keshlaydi va keyingi ikki test ma'noli; (b) invalidatsiyadan keyin **birinchi** so'rovdayoq 401, hech qanday kutish yo'q; (c) kesh bo'shatilganda holat DB'dan o'qiladi (fail-open EMAS) va keshga qaytadan yoziladi. Bundan tashqari bloklangan foydalanuvchining 30 kunlik refresh sessiyasi ham keyingi `/refresh` da o'ladi. **Sabotaj bilan sinaldi.**

- **D-07 negativ da'volar bilan qulflandi.** `tests/unit/test_rbac_matrix.py` "direktorda `USER_MANAGE`/`STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` **YO'Q**" deb yozilgan — pozitiv da'vo matritsani kengaytirish yo'lini ochiq qoldirardi. Kassir aynan `{PAYMENT_CREATE}`, nazoratchi aynan `{OCCUPANCY_REVIEW}`, `MARKET_VIEW_ALL` faqat platforma adminida, `AUDIT_VIEW` aynan uch rolda (D-11).

- **`GET /auth/me` tenant kontekstini har chaqiruvda isbotlaydi.** So'rov ATAYIN filtrsiz (`SELECT id, name FROM markets`): `markets` policy'si `id = app.market_id` bo'lgani uchun u aynan bitta qator qaytaradi. Noto'g'ri o'rnatilgan kontekst bu yerda 0 qator bo'lib darhol ko'rinadi. Platforma admini A ni tanlab A ni, B ni tanlab B ni ko'radi — RLS bypass yo'li yo'qligi HTTP darajasida ham tasdiqlandi (D-06).

- **Model ↔ migratsiya pariteti 12 ta `SECURITY DEFINER` funksiya bilan ham saqlandi.** `alembic downgrade -1 → upgrade head → downgrade base → upgrade head` xatosiz takrorlanadi; `alembic revision --autogenerate` BO'SH diff beradi (`ALL_ENTITIES` ga sakkizta yangi `PGFunction` ro'yxatga olingan).

## Task Commits

1. **Task 1: RBAC matritsasi, principal va tenant sessiyasi (TDD)**
   - `a84533c` (test) — RED: `ModuleNotFoundError: No module named 'app.security'`
   - `afbc99b` (feat) — GREEN: 9 modul, `tests/unit` 154/154 yashil
2. **Task 2: Auth endpointlari, rate-limit va `0003_auth_support`** — `9a3bf10` (feat)
3. **Task 3: Auth integratsiya testlari (TDD)** — `d7193b6` (test) — 44 test + 3 tuzatilgan xato

## Files Created/Modified

**Xavfsizlik qatlami (`services/core-api/app/security/`)**

- `rbac.py` — `Permission` (13 a'zo) + `ROLE_PERMISSIONS` + `permissions_for()`. Fayl yuqorisida ikki izoh: matritsa DB'ga ko'chirilmaydi (v2 nomzodi) va `USER_MANAGE` "istalgan rolni berish" huquqi EMAS
- `tokens.py` — cookie atributlari jadvali sababi bilan; `IssuedRefresh` (token + `jti` + `family_id` + `expires_at`); `cleared_cookie_headers()`
- `audit.py` — `write_app_audit()` (`principal` yoki aniq argumentlar bilan), `platform_admin_label()`, uchta jadval nomi konstantasi
- `ratelimit.py` — ikki kesim (telefon/IP) va ularning har biri qaysi hujumni yopishi

**Marshrutlar va dependency'lar**

- `api/v1/auth.py` — olti endpoint; `POST /auth/register` yo'qligi modul docstringida va testda qulflangan
- `deps.py` — `Principal`, `get_current_principal`, `get_auth_session`, `get_tenant_session`, `require_permission`, `require_roles`, `invalidate_user_state`
- `schemas.py` — kontrakt shakllari; telefon `field_validator` da normallashadi
- `repositories/auth_repo.py` — 12 funksiyaga tiplangan o'ram, faqat nomlangan bind parametrlari
- `main.py` — `CorrelationIdMiddleware`, `configure_logging`, Sentry `before_send` PII filtri, `app.state.sessionmaker`, RLS → 404 handler

**Migratsiya**

- `0003_auth_support.py` — 8 funksiya + `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`
- `entities/functions.py` — `AUTH_SUPPORT_FUNCTIONS` / `AUTH_SUPPORT_GRANT_SIGNATURES` (0001 ning ro'yxatidan ALOHIDA)

**Testlar** — 53 ta yangi

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `tests/unit/test_rbac_matrix.py` | 9 | D-07 negativ da'volar, D-05 birlashma, D-11 audit ko'rish, `frozenset` o'zgarmasligi |
| `tests/integration/test_auth_login.py` | 25 | enumeration (tana bo'yicha), rate-limit, telefon normalizatsiyasi (3 shakl), audit yozuvlari, D-06 bozor tanlash, parol almashtirish |
| `tests/integration/test_auth_refresh.py` | 10 | rotatsiya, sliding muddat, reuse detection (4 da'vo), logout, tur almashtirish |
| `tests/integration/test_user_block.py` | 6 | kesh nazorat holati, darhol bloklash, kesh promahi, refresh yo'li |
| `tests/tenancy/test_login_bootstrap.py` (+0) | 10 | grant darvozasi endi ikkala funksiya to'plamini qamraydi |
| `tests/tenancy/test_meta.py` (+0) | 21 | `EXPECTED_DEFINER_FUNCTIONS` 4 → 12 |

## Decisions Made

- **`refresh_tokens` lifecycle'i `SECURITY DEFINER` ortiga olindi.** Alternativalar ko'rib chiqildi va rad etildi: (a) `mid` ni refresh tokenga yozish — 01-03 dagi `test_refresh_does_not_carry_roles_or_market` ni buzardi va bloklangan foydalanuvchi 30 kun eski kontekst bilan yashardi; (b) `market_id` ni nullable qilish — RLS ostida bunday qator baribir ko'rinmasdi va sxema surgeriyasi talab qilardi. Yuza qasddan tor: har funksiya bitta operatsiya, aniq kalit bo'yicha filtr, ixtiyoriy `WHERE` qabul qilmaydi.

- **Bozor tanlanmagan sessiyaga refresh cookie berilmaydi.** `refresh_tokens.market_id` `NOT NULL` va bozorsiz sessiyaning ma'nosi ham yo'q — u hech qanday ma'lumotga kira olmaydi. Platforma admini `/select-market` da cookie oladi va o'sha yerda eski oila bekor qilinadi (bozor almashtirilganda oldingi bozorga bog'langan sessiya yashab qolmaydi).

- **`GET /auth/me` qo'shildi.** Rejada olti emas, besh endpoint bor edi. `get_tenant_session` esa hech qayerda ishlatilmagan bo'lardi — ya'ni rejaning must-have artefaktlaridan biri **sinalmagan kod** bo'lib qolardi. `/me` uni har chaqiruvda isbotlaydi va 01-08 frontendiga baribir kerak bo'ladi.

- **Parol siyosati `field_validator` da EMAS.** Reja `schemas.py` da `field_validator` ni ko'rsatgan, lekin e'lon qilingan kontrakt zaif parol uchun `400 {"detail":"weak_password"}` talab qiladi — Pydantic esa 422 berardi. Qoida `validate_password_strength()` sof funksiyasida qoldi, endpoint uni 400 ga aylantiradi.

- **`is_active` tekshiruvi parol tekshiruvidan KEYIN.** Teskarisi tezroq bo'lardi, lekin aynan o'sha tezlik "bu raqam bor va bloklangan" degan yon kanal signali bo'lardi.

- **Bitta o'g'irlik = bitta ogohlantirish.** Dastlabki amalga oshirishda o'lik oilaga kelgan HAR bir cookie yangi `refresh_reuse_detected` yozardi (test 2 ta qator topib qizardi). Bitta o'g'irlik jurnalda o'nlab signalga aylanardi va nazoratchi haqiqiy hodisani shovqin ichida yo'qotardi. Endi audit faqat `refresh_revoke_family()` haqiqatan qator bekor qilganda yoziladi; logout'dan keyingi eski cookie ham noto'g'ri "o'g'irlik" signali bermaydi.

- **`sync_superuser_conn` — ataylab tor qochish yo'li.** `login_failed` yozuvlari `market_id IS NULL` va `audit_read` policy'si ostida na ilova, na ega roliga ko'rinadi (bu 01-05 da hujjatlashtirilgan qaror). Ularni tekshirishning boshqa yo'li hozircha yo'q. Fixture docstringida "hech qanday izolyatsiya da'vosi bu ulanish bilan tekshirilmaydi" deb yozilgan.

- **API testlari uchun alohida engine.** `app_engine` ataylab `pool_size=1` (GUC sizishini ochib berish uchun), lekin bitta HTTP so'rovi ba'zan ikki sessiya ochadi (bloklash keshi promahi + tenant sessiyasi) va bir ulanishli pulda bu deadlock berardi — testlar timeout bilan yiqilib, sabab tenant izolyatsiyasi kabi ko'rinardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `POST /auth/refresh` RLS ostida umuman ishlamasdi**

- **Found during:** Task 2 (auth_repo dizayni)
- **Issue:** `refresh_tokens` RLS ENABLE+FORCE ostida; refresh cookie kelganda `app.market_id` noma'lum (`mid` refresh tokenda ATAYIN yo'q). `jti` bo'yicha qidiruv 0 qator qaytaradi → sessiya uzaytirish hech qachon ishlamasdi. Reja `0003` da faqat `auth_update_password_hash` va `auth_set_active` ni ko'rsatgan edi.
- **Fix:** `0003_auth_support` ga beshta funksiya qo'shildi: `auth_refresh_issue`, `auth_refresh_find`, `auth_refresh_rotate`, `auth_refresh_revoke_family`, `auth_refresh_revoke_user`. Hammasi `search_path` pin bilan, `REVOKE ALL FROM PUBLIC` + `GRANT EXECUTE TO sbozor_app`.
- **Files modified:** `migrations/entities/functions.py`, `migrations/versions/0003_auth_support.py`, `migrations/entities/__init__.py`
- **Verification:** `tests/integration/test_auth_refresh.py` 10/10; `test_definer_functions_are_executable_by_app_role` ikkala to'plamni qamraydi
- **Committed in:** `9a3bf10`

**2. [Rule 3 - Blocking] `change-password` uchun `user_id` bo'yicha login qatorini olish yo'li yo'q edi**

- **Found during:** Task 2
- **Issue:** `auth_find_login` telefon bo'yicha ishlaydi, access tokenda esa telefon yo'q (u shaxsiy ma'lumot va tokenga kerak emas). Joriy parol hash'ini olishning yo'li qolmagan edi.
- **Fix:** `auth_find_login_by_id(p_user_id uuid)` — telefonni ham qaytaradi, shuning uchun D-06 `actor_label` matni ham shundan quriladi.
- **Committed in:** `9a3bf10`

**3. [Rule 1 - Bug] `insert(AuditLog)` `RETURNING` qo'shib login endpointini 404 qilardi**

- **Found during:** Task 3 (birinchi integratsiya yugurishi — 36 test bir vaqtda qizardi)
- **Issue:** SQLAlchemy mapped klass ustidagi `insert()` `Identity` kalitini olish uchun `RETURNING id` qo'shadi; PostgreSQL `INSERT ... RETURNING` da qaytariladigan qatorga SELECT policy'sini qo'llaydi. `audit_log` da u tenant-scoped, auth oqimida esa kontekst yo'q → `new row violates row-level security policy` → global handler 404 qaytarardi.
- **Fix:** Xom `text()` INSERT + `bindparam(type_=...)` bilan tiplangan parametrlar (`uuid`, `jsonb`, `text[]`), `CAST(:ip AS inet)`. Sababi kod ichida to'liq yozilgan.
- **Files modified:** `services/core-api/app/security/audit.py`
- **Verification:** 44 auth integratsiya testi yashil
- **Committed in:** `d7193b6`

**4. [Rule 1 - Bug] Cookie tozalash jimgina ishlamasdi**

- **Found during:** Task 3
- **Issue:** `clear_refresh_cookie(response)` dan keyin `raise HTTPException(...)` — FastAPI istisno uchun yangi javob quradi va uzatilgan `Response` sarlavhalari ko'chmaydi. Reuse aniqlanganda server tomonda token o'ladi, brauzerda o'lik cookie qoladi.
- **Fix:** `tokens.cleared_cookie_headers()` — sarlavha `Response` ustida hosil qilinib, `HTTPException(headers=...)` bilan uzatiladi. `_invalid_refresh(clear_cookie=True)` uni uch yo'lda ishlatadi.
- **Verification:** `test_refresh_reuse_detection` javobda `Set-Cookie` borligini tekshiradi
- **Committed in:** `d7193b6`

**5. [Rule 1 - Bug] Bitta o'g'irlik jurnalda ko'p signal yozardi**

- **Found during:** Task 3 (`assert 2 == 1`)
- **Issue:** Oila bekor qilingandan keyin ham eski cookie'lar kelib turadi (o'g'irlangan nusxa, haqiqiy foydalanuvchi brauzeri, logout'dan keyingi tab) va har biri yangi `refresh_reuse_detected` yozardi.
- **Fix:** Audit yozuvi faqat `refresh_revoke_family()` haqiqatan qator bekor qilganda; aks holda `log.info("refresh_on_dead_family")`.
- **Committed in:** `d7193b6`

**6. [Rule 2 - Missing Critical] Yaroqsiz IP butun login oqimini o'chira olardi**

- **Found during:** Task 3
- **Issue:** `audit_log.ip` ustuni `inet`; `request.client.host` `inet` ga tushmaydigan qiymat bo'lsa (g'alati ASGI serveri, noto'g'ri proxy sozlamasi) INSERT yiqilib, u bilan birga login ham yiqilardi.
- **Fix:** `_client_ip()` `ipaddress.ip_address()` bilan tekshiradi va yaroqsiz qiymatda `None` qaytaradi (sabab `log.info` da).
- **Committed in:** `d7193b6`

**7. [Rule 2 - Missing Critical] O'qib bo'lmaydigan parol hash'i enumeration signali bo'lardi**

- **Found during:** Task 2
- **Issue:** `two_markets` seed'i `password_hash` ga o'rinbosar satr yozadi. Bunday qatorda `pwdlib` istisno ko'taradi va u ushlanmasa BITTA buzuq qator butun login endpointini 500 bilan yiqitardi — hujumchi uchun esa bu ochiq signal ("bu telefon uchun 500, boshqasi uchun 401").
- **Fix:** `_verify_password_safe()` — istisno `log.warning` ga yoziladi, javob esa odatdagi 401.
- **Committed in:** `9a3bf10`

**8. [Rule 3 - Blocking] `app` paketi testlardan import bo'lmasdi**

- **Found during:** Task 1 (RED)
- **Issue:** Testlar repo ildizida, servis kodi `services/core-api/app` da. `pythonpath = [".", "tests"]` bilan `import app.security.rbac` topilmasdi.
- **Fix:** `pythonpath` va `mypy_path` ga `services/core-api` qo'shildi (sababi izohda).
- **Committed in:** `a84533c`

**9. [Rule 3 - Blocking] `mypy services/core-api` `sbozor_core` ni tipsiz deb bilardi**

- **Found during:** Task 1 (rejaning qabul mezoni)
- **Issue:** `sbozor-core` strict mypy ostida yozilgan, lekin PEP 561 markeri yo'q edi → alohida chaqirilgan `mypy services/core-api` 10 ta `import-untyped` xatosi berardi.
- **Fix:** `packages/sbozor-core/sbozor_core/py.typed` (bo'sh marker fayl).
- **Committed in:** `afbc99b`

**10. [Rule 1 - Bug] `select(User)` izohi grep darvozasini yiqitardi**

- **Found during:** Task 1 yakuniy tekshiruvi
- **Issue:** Qabul mezoni: `auth_repo.py` da `select(User)` ISHLATILMAYDI. Mening modul docstringimda "NEGA BU YERDA BIRORTA `select(User)` YO'Q" deb yozilgandi → grep 1 qaytardi. Bu 01-01/01-03/01-05 dagi bilan AYNAN bir xil sinf xato.
- **Fix:** Docstring ma'nosini saqlagan holda literal tokensiz qayta yozildi.
- **Verification:** `grep -c "select(User)" ...` → `0`
- **Committed in:** `afbc99b`

**11. [Rule 3 - Blocking] `ruff` SIM117 tranzaksiya blokini birlashtirib qo'yardi**

- **Found during:** Task 1
- **Issue:** `ruff format` `async with sessionmaker() as session:` va `async with session.begin():` ni bitta qatorga birlashtirdi. Semantikasi bir xil, lekin "kontekst tranzaksiya ichida o'rnatiladi" degan fakt ko'zdan yo'qoladi va rejaning qabul mezoni aynan o'sha shaklni talab qiladi.
- **Fix:** TASHQI `async with` ga `# noqa: SIM117` (ruff diagnostikasi o'sha satrda) + sabab izohi.
- **Committed in:** `afbc99b`

**12. [Rule 3 - Blocking] `token_type = "bearer"` `S105` berdi; Sentry `before_send` tipi mos kelmadi**

- **Found during:** Task 1 va 2
- **Issue:** ruff `S105` RFC 6750 token TURINI parol deb bildi; mypy `before_send` uchun `sentry_sdk.types.Event` kutdi.
- **Fix:** Ikki satrga sabab bilan `# noqa: S105`; `_scrub_event(event: Event, _hint: Hint) -> Event`.
- **Committed in:** `afbc99b`, `9a3bf10`

### Kichik moslashtirishlar (xato emas, tanlov)

- **`tests/fixtures/auth_api.py` va `auth_users.py`** rejaning fayl ro'yxatida yo'q — ular test infratuzilmasi. `tests/integration/helpers.py` shakli ATAYIN tanlanmadi: `tests/` namespace paket va ulashilgan kod uchun yagona xavfsiz joy `fixtures` paketi (01-05 deviatsiya #5 da o'rnatilgan qoida).
- **`tests/tenancy/test_login_bootstrap.py` va `test_meta.py`** ham ro'yxatda yo'q — yangi sakkiz funksiya mavjud darvozalardan o'tishi uchun ro'yxatlar kengaytirildi (aks holda ular grant/`search_path` tekshiruvidan tashqarida qolardi).
- **`test_rbac_matrix.py` da 8 emas, 9 test** — to'qqizinchisi (`test_unknown_role_contributes_nothing`) eski tokendagi o'chirilgan rol `KeyError` bermasligini qulflaydi.
- **`GET /auth/me` javobida `permissions` ro'yxati ham bor** — frontend (01-08) menyuni shu asosda quradi va matritsani takrorlamaydi.
- **`RefreshResponse = SessionResponse` taxallusi** — ikkala javob ham "sessiya bozor kontekstiga bog'landi" degan bir xil faktni qaytaradi.

---

**Total deviations:** 12 auto-fixed — 5× Rule 1 (`RETURNING`, cookie tozalash, ko'p signal, grep darvozasi, SIM117 shakli), 2× Rule 2 (yaroqsiz IP, o'qib bo'lmaydigan hash), 5× Rule 3 (refresh RLS qopqoni, `find_login_by_id`, pythonpath, `py.typed`, lint/tip).
**Impact on plan:** Scope creep yo'q — barcha o'zgarishlar rejaning o'z qabul mezonlari va tahdid reyestri doirasida. Uchtasi (#1, #3, #4) rejada ko'rinmagan bloklovchini yopdi: birinchisisiz `/refresh` umuman ishlamasdi, ikkinchisisiz login endpointi 404 qaytarardi, uchinchisi esa jimgina ishlamaydigan kod edi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi; qo'shimcha `GET /auth/me` endpointi `get_tenant_session` ni sinalmagan qoldirmaslik uchun kiritildi.

## Issues Encountered

- **`.env` fayli yo'q** (gitignore'da, worktree bilan kelmaydi) va mavjud `pgdata` volume'i eski parollar bilan initsializatsiya qilingan (01-05 da qayd etilgan). Foydalanuvchining dev bazasiga TEGILMADI: barcha tekshiruvlar `tests` profilidagi testcontainers orqali bajarildi. Rejaning 5-verifikatsiya qadami (`docker compose up -d core-api` + `curl`) o'rniga **runtime image** qurildi va unda ilova import qilinib, oltala marshrut ro'yxatda ekani tasdiqlandi — ya'ni dev bog'liqliklarisiz, non-root konteynerda ham ishlaydi.
- **Windows Git Bash yo'l konversiyasi.** `docker run --workdir /app/...` xost yo'liga aylanib ketadi; `MSYS_NO_PATHCONV=1` bilan hal qilindi (faqat qo'lda tekshiruvda, kodga ta'sir qilmaydi).
- **Migratsiya round-trip va autogenerate pariteti vaqtinchalik test fayli bilan tekshirildi**, fayl tekshiruvdan keyin o'chirildi va commit qilinmadi (01-05 dagi bilan bir xil usul).

## Known Stubs

Yo'q. Bu rejadagi har bir endpoint, funksiya, dependency va migratsiya to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` + `valkey:9.1.1` ga qarshi tekshirilgan.

Atayin **keyingi rejalarga** qoldirilgan (stub emas, hali navbati kelmagan):

- **`Permission` a'zolarining yarmi hali hech qayerda tekshirilmaydi** (`STALL_MANAGE`, `TARIFF_MANAGE`, `VENDOR_MANAGE`, `PAYMENT_CREATE`, `OCCUPANCY_REVIEW`, `DISPUTE_DECIDE`). Ular ATAYIN hozirdan bor: D-07 ning mazmuni — "direktor nima qila OLMAYDI" — aynan shu huquqlarning yo'qligi bilan ifodalanadi va ularsiz D-07 ni test bilan qulflab bo'lmasdi.
- **`auth_set_active` ni chaqiradigan endpoint yo'q** — bloklash UI'si 01-07 da. Funksiya va `invalidate_user_state()` tayyor va testlar ularni mahsulot yo'lidan ishlatadi.
- **O'qish-auditi dekoratori (`audit_read`)** — 01-07; bu yerda faqat yozuv funksiyasi.
- **`market_id IS NULL` audit qatorlarini mahsulot yo'lidan o'qish** — 01-07 dagi tor `SECURITY DEFINER` funksiya. Hozircha faqat test superuser bilan o'qiydi.
- **`require_permission()` hali birorta HAQIQIY resurs endpointida ishlatilmagan** — 1-fazada auth'dan boshqa yozuv endpointi yo'q. Matritsa va dependency tayyor; birinchi haqiqiy foydalanuvchi 01-07 (`POST /users`).
- **`TenantScopedRepository`** bu rejada ishlatilmadi: barcha so'rovlar `SECURITY DEFINER` funksiyalari yoki `/me` dagi bitta `text()` orqali ketdi. Uning `column_descriptions[0]` cheklovi (01-03 da qayd etilgan) hamon ochiq va birinchi ko'p jadvalli ORM so'rovi paydo bo'lganda hal qilinishi kerak — ehtimol 01-07 da.

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Ikkita **kutilgan** kengayish bor va ikkalasi ham mavjud dispozitsiyalar ichida qoladi:

1. **`0003` dagi 8 ta yangi `SECURITY DEFINER` funksiya** — T-01-23 (`search_path` hijacking) doirasida; hammasi `SET search_path = pg_catalog, public` bilan va `test_security_definer_functions_pin_search_path` butun bazani skanerlaydi. `PUBLIC` dan `REVOKE ALL` `test_definer_functions_are_not_granted_to_public` bilan qulflangan.
2. **`GET /auth/me`** — yangi endpoint, lekin yangi TRUST BOUNDARY emas: u `get_current_principal` + `get_tenant_session` ostida va faqat allaqachon tokenda bo'lgan ma'lumotni + tanlangan bozor nomini qaytaradi.

Reyestrdagi 11 ta dispozitsiya bajarildi va har biri test bilan qoplandi:

| Threat  | Qanday yopildi | Tekshiruv |
| ------- | -------------- | --------- |
| T-01-39 | `ratelimit.py` — telefon 10/15daq, IP 50/15daq + Argon2id sekinligi | `test_login_rate_limit`, `test_successful_login_clears_rate_counter` |
| T-01-40 | `dummy_verify()`; uchala rad etish AYNAN bir xil 401; `is_active` paroldan KEYIN | `test_login_no_user_enumeration`, `test_blocked_user_is_indistinguishable_from_wrong_password` (SABOTAJ bilan sinaldi) |
| T-01-41 | Har `/refresh` da rotatsiya; bekor qilingan `jti` -> BUTUN oila + audit | `test_refresh_reuse_detection` (4 da'vo, SABOTAJ bilan sinaldi) |
| T-01-42 | Refresh `httpOnly` cookie'da; access faqat javob tanasida | `test_refresh_cookie_attributes` |
| T-01-43 | `SameSite=Lax` + `Path=/api/v1/auth` | `test_refresh_cookie_attributes` |
| T-01-44 | Har so'rovda `user:state:{id}` (TTL 30 s) + yozuvda invalidatsiya | `test_block_takes_effect_on_the_first_request_after_invalidation` + 2 nazorat holati (SABOTAJ bilan sinaldi) |
| T-01-45 | `ROLE_PERMISSIONS` kodda qat'iy; `require_permission` fabrikasi | `tests/unit/test_rbac_matrix.py` (9 invariant) |
| T-01-46 | `select-market` `app.market_id` ni o'rnatadi; `BYPASSRLS` roli yo'q | `test_platform_admin_can_select_each_market` (`/me` orqali uchdan-uchiga) |
| T-01-47 | RLS xatosi -> 404; mavjud bo'lmagan va ruxsatsiz bozor AYNAN bir xil 403 | `rls_violation_handler`, `test_unknown_market_is_also_403` |
| T-01-48 | Faqat nomlangan bind parametrlari; `ruff S608` yoqilgan | `ruff check --select S608 auth_repo.py` -> toza |
| T-01-49 | `login`, `login_failed`, `logout`, `market_selected`, `password_changed`, `refresh_reuse_detected` | `test_login_writes_audit_row`, `test_failed_login_writes_login_failed_audit`, `test_logout_kills_the_family`, `test_select_market_audit_carries_platform_admin_label` |

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

- **01-07 (foydalanuvchi boshqaruvi):** `require_permission(Permission.USER_MANAGE)` dependency'si, `auth_set_active` funksiyasi va `invalidate_user_state()` tayyor; `write_app_audit()` ma'muriy o'zgarishlar uchun ishlatiladi. Rol berish DARAJASI (kim qaysi rolni yarata oladi) matritsaga EMAS, `POST /users` servis mantiqiga tushishi rbac.py da hujjatlashtirilgan.
- **01-08 (frontend):** HTTP kontrakti qat'iy va OpenAPI'da ko'rinadi; `GET /auth/me` sessiya tiklash uchun; `permissions` ro'yxati menyuni qurish uchun. Access token faqat xotirada saqlanishi kerak (`localStorage` TAQIQ) — refresh `httpOnly` cookie'da.
- **01-09/01-10:** `Principal`, `get_tenant_session` va `require_permission` naqshi audit ko'rish UI va cross-tenant matritsasi uchun tayyor.

**Ochiq e'tibor nuqtalari:**

- **`market_id IS NULL` audit qatorlarini hech kim o'qiy olmaydi.** `login_failed` yozuvlari to'planmoqda, lekin ularni ko'rish yo'li yo'q (test superuser bilan o'qiydi). 01-07 dagi tor `SECURITY DEFINER` funksiya bu bo'shliqni yopishi kerak, aks holda "kim tizimga kirishga urinmoqda" savoli javobsiz qoladi.
- **Rate-limit oynasi TTL asosida** (`INCR` + `EXPIRE NX`), sof sirpanuvchi oyna emas: oyna boshida 10 urinish qilgan hujumchi 15 daqiqadan keyin darhol yana 10 ta qila oladi. Argon2 narxi bilan birga bu MVP uchun yetarli; aniqroq shakl kerak bo'lsa sorted-set asosidagi variant bir soatlik ish.
- **`X-Forwarded-For` O'QILMAYDI.** Prod'da haqiqiy IP nginx `proxy_set_header` + uvicorn `--proxy-headers` orqali kelishi kerak; hozirgi compose buyrug'ida `--proxy-headers` YO'Q, ya'ni nginx ortida `audit_log.ip` va IP rate-limit proxy konteynerining IP'sini ko'radi. Bu 01-09/8-fazada deploy sozlamasi sifatida hal qilinadi.
- **`sbozor_core/py.typed` qo'shildi** — endi `sbozor_core` ni import qiladigan har qanday yangi servis (cv-service, bot-service) uning tiplarini avtomatik oladi. Bu `sbozor_core` ning ommaviy API'sini de-fakto barqaror kontraktga aylantiradi.
- **`.github/workflows/ci-backend.yml` bu ishni hali ko'rmadi.** Mahalliy zanjir yashil; CI'da testcontainers endi IKKI konteyner (Postgres + Valkey) ko'taradi — birinchi ishga tushishda kuzatilishi kerak.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 27 ta artefaktning (20 yangi + 7 modifikatsiya) hammasi mavjud va git'da kuzatilmoqda.
- **Commitlar:** `a84533c`, `afbc99b`, `9a3bf10`, `d7193b6` — to'rttasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only 50f6b84..HEAD` bo'sh.
- **Umumiy artefaktlarga tegilmadi:** `git diff --name-only 50f6b84..HEAD -- .planning/STATE.md .planning/ROADMAP.md` bo'sh (worktree rejimi — ularni orkestrator yangilaydi).
- **Ishchi katalog toza:** `git status --short` bo'sh; vaqtinchalik round-trip test fayli o'chirildi.
- **Darvozalar:** `ruff check .` + `ruff format --check .` + `mypy .` (strict, 70 fayl) + `mypy services/core-api` (alohida, 11 fayl) + `pytest` (270 test) — hammasi yashil.
- **Migratsiya:** `downgrade -1` → `upgrade head` → `downgrade base` → `upgrade head` xatosiz; `alembic revision --autogenerate` BO'SH diff beradi (12 `PGFunction` bilan ham).
- **Runtime image:** `docker compose build core-api` muvaffaqiyatli; konteyner ichida `app.main` import bo'ladi va oltala auth marshruti OpenAPI'da ko'rinadi.
- **Sabotaj tekshiruvlari (3 ta):** (1) bloklash javobi `account_blocked` ga o'zgartirilganda `test_blocked_user_is_indistinguishable_from_wrong_password` yiqildi; (2) `refresh_revoke_family()` chaqiruvi olib tashlanganda `test_refresh_reuse_detection` yiqildi; (3) `_is_user_active` tekshiruvi o'chirilganda `test_user_block` dan ikkita test yiqildi. Uchalasi ham qaytarildi va to'plam yana yashil.
- **Grep darvozalari:** `select(User)` → 0; `ruff --select S608 auth_repo.py` → toza; `sbozor_rt` `auth.py` da bor; `passlib|jose|ultralytics` → 0; `/api/v1/auth/register` `app.openapi()` da YO'Q.
