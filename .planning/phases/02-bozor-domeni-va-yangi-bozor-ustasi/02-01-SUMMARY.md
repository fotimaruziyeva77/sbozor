---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 01
subsystem: infra
tags: [rbac, postgres, btree-gist, alembic, rls, fastapi, jwt, pytest]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "RBAC matritsasi, `schema_contract` reyestrlari, `migrations/helpers.py`, parol darvozasi (`CurrentPasswordDep`), `auth_repo.find_login_by_id`, tenancy meta-testlari"
provides:
  - "`Permission.MARKET_DATA_VIEW` va `Permission.VENDOR_VIEW` — bozor ma'lumotini O'QISH huquqlari (YOZISHdan ajratilgan)"
  - "`PLATFORM_ADMIN` da `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` — MARKET-01 ustasi endi to'liq bajariladi"
  - "`FINANCIAL_TABLES` = {daily_charges, charge_adjustments, payments, tariffs} — `stall_assignments` chiqarildi"
  - "`AUDITED_TABLES` — 2-fazaning 8 domen jadvali"
  - "`ops/db/init/00-extensions.sql` — `btree_gist` superuser init qadami (prod + test bir xil DDL)"
  - "`migrations/helpers.py::require_extension()` — migratsiya uchun kengaytma darvozasi"
  - "`POST /auth/select-market` parol darvozasi ostida va `is_platform_admin` ni DB'dan o'qiydi (WR-02/WR-03 yopildi)"
  - "`tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` — reyestr/migratsiya qarzining ikki tomonlama qulfi"
affects: [02-02, 02-03, 02-04, 02-05, 02-06, 02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "O'QISH huquqi YOZISH huquqidan alohida `Permission` a'zosi (D-07 ni matritsa kengayishidan himoyalaydi)"
    - "Kengaytma DDL'i superuser init faylida, migratsiyada esa faqat `require_extension()` darvozasi"
    - "Reyestr migratsiyadan OLDIN to'ldiriladi; qarz `PENDING_*` ro'yxati bilan ikki tomonlama qulflanadi"
    - "Tokendan token yasaydigan endpoint identifikatsiya haqiqatini DB'dan qayta o'qiydi"

key-files:
  created:
    - ops/db/init/00-extensions.sql
  modified:
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - services/core-api/app/security/rbac.py
    - services/core-api/app/api/v1/auth.py
    - services/core-api/app/api/v1/me.py
    - services/core-api/app/deps.py
    - migrations/helpers.py
    - frontend/src/lib/rbac.ts
    - tests/conftest.py
    - tests/tenancy/test_meta.py
    - tests/unit/test_rbac_matrix.py
    - tests/integration/test_password_gate.py
    - tests/integration/test_auth_login.py

key-decisions:
  - "`tariffs` `FINANCIAL_TABLES` da qoldi (haqiqiy pul ustuni bor), `stall_assignments` chiqarildi (D-10 bo'yicha pul ustuni bo'lmasligi kerak)"
  - "Direktorga `MARKET_DATA_VIEW` + `VENDOR_VIEW` berildi, birorta `*_MANAGE` berilmadi — D-07 testda qulflandi"
  - "`GRANT CREATE ON DATABASE` muqobili rad etildi: u migratsiya roliga baza darajasida sxema yaratish huquqini berardi"
  - "`select-market` a'zoligi bo'lmagan bozor uchun 403 `market_forbidden` qoldi (404 EMAS) — T-01-47 anti-enumeration siyosati buzilmadi"
  - "WR-03 da'vosi `pa` claim'i bo'yicha tekshiriladi, `roles` bo'yicha emas — seed'dagi platforma adminining a'zolik roli aynan `platform_admin`"
  - "`PATCH /api/v1/me` ham darvoza ostiga olindi (yozadi); `GET /api/v1/me` ATAYIN ochiq qoldi (D-13 til)"

patterns-established:
  - "Pattern: yangi `Permission` qo'shilganda `frontend/src/lib/rbac.ts` ko'zgusi QO'LDA sinxronlanadi; ikkala faylda ham eslatma izohi turadi"
  - "Pattern: `ops/db/init/*.sql` fayllari testda VERBATIM o'qib bajariladi — DDL testda takrorlanmaydi"
  - "Pattern: qulflangan sessiya testi ikki tomonlama (yopiq yo'l + ochiq yo'l), aks holda 403 ning sababi noaniq qoladi"

requirements-completed: [MARKET-01, MARKET-02, MARKET-03, MARKET-04]

# Metrics
duration: 62min
completed: 2026-07-31
---

# Phase 2 Plan 01: Darvozalarni to'g'rilash Summary

**2-fazaning birinchi migratsiyasidan oldin uchta meros minasi zararsizlantirildi (moliyaviy reyestr, RBAC matritsasi, `btree_gist` huquqi) va 1-faza ko'rigi ochiq qoldirgan WR-02/WR-03 avtorizatsiya teshiklari yopildi.**

## Performance

- **Duration:** ~62 min
- **Started:** 2026-07-31T15:18:00Z
- **Completed:** 2026-07-31T16:20:00Z
- **Tasks:** 3/3
- **Files modified:** 12 (1 yaratilgan, 11 o'zgartirilgan)

## Accomplishments

- **MARKET-01 endi texnik jihatdan bajariladi.** `PLATFORM_ADMIN` da `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` yo'q edi — usta 3-qadamda 403 bilan to'xtardi va sabab endpoint kodida ko'rinmasdi. Uchtasi ham berildi va `test_platform_admin_can_run_the_wizard` bilan qulflandi.
- **`stall_assignments` jadvali tug'ilgan kuni CI qizarmaydi.** U `FINANCIAL_TABLES` dan chiqarildi: meta-test undan `CHECK (amount_soum > 0)` talab qilardi, biriktirish jadvalida esa pul ustuni yo'q va D-10 bo'yicha bo'lmasligi ham kerak.
- **`btree_gist` prod va testda bir xil yo'ldan keladi.** `sbozor_owner` uni o'rnata olmaydi (`permission denied to create extension` — empirik), shuning uchun DDL superuser init faylida; migratsiya esa `require_extension()` bilan baland ovozda yiqiladi.
- **WR-02/WR-03 yopildi.** `select-market` — tokendan token yasaydigan yagona yo'l — endi parol darvozasi ostida va `is_platform_admin` ni `users` jadvalidan qayta o'qiydi. Bu 2-fazada (usta oqimi + lavozim boshqaruvi) jonli avtorizatsiya chetlab o'tishiga aylanardi.
- **D-07 kafolati kengayish ostida ham saqlandi.** Matritsa ikkita yangi huquq bilan kengaydi, lekin direktorga birorta `*_MANAGE` tushmadi — `test_director_is_read_only_on_market_data` ikkala tomonni bitta testda qulflaydi.

## Task Commits

1. **Task 1: Sxema reyestrlari va RBAC matritsasi** — `ab4ed09` (feat)
2. **Task 2: `btree_gist` init qadami + `require_extension()`** — `28b337b` (feat)
3. **Task 3: WR-02/WR-03 — `select-market` darvozasi va DB haqiqati** — `17142af` (fix)

## Files Created/Modified

- `ops/db/init/00-extensions.sql` — **yangi.** `CREATE EXTENSION IF NOT EXISTS btree_gist`; izohda rad etilgan `GRANT CREATE ON DATABASE` muqobili va kengaytmaning nima uchun kerakligi.
- `packages/sbozor-core/sbozor_core/schema_contract.py` — `FINANCIAL_TABLES` dan `stall_assignments` olib tashlandi; `AUDITED_TABLES` 8 jadvalga kengaydi; kirmagan uchta jadval uchun sabab yozildi.
- `services/core-api/app/security/rbac.py` — ikkita yangi `Permission`; `PLATFORM_ADMIN`, `DIRECTOR`, `MARKET_ADMIN` qatorlari yangilandi.
- `frontend/src/lib/rbac.ts` — backend matritsasining qo'lda sinxronlangan ko'zgusi.
- `migrations/helpers.py` — `require_extension()` + `__all__` ga kiritildi.
- `tests/conftest.py` — `EXTENSIONS_SQL_PATH` va `_bootstrap_extensions` fixture'i; `_bootstrap_roles` unga bog'landi.
- `services/core-api/app/api/v1/auth.py` — `select_market`: `CurrentPasswordDep`, `find_login_by_id()` bilan qayta o'qish, `_platform_admin_market()` imzosi o'zgardi.
- `services/core-api/app/api/v1/me.py` — `update_profile` darvoza ostiga olindi.
- `services/core-api/app/deps.py` — modul docstringidagi noto'g'ri da'vo to'g'rilandi.
- `tests/unit/test_rbac_matrix.py` — 3 yangi test.
- `tests/tenancy/test_meta.py` — `PENDING_AUDIT_TRIGGERS`, ikki tomonlama trigger qulfi, `btree_gist` mavjudligi testi.
- `tests/integration/test_password_gate.py` — 3 yangi test (select-market yopiq, `PATCH /me` yopiq, `GET /me` ochiq).
- `tests/integration/test_auth_login.py` — 3 yangi test (bayroqni qayta o'qish, nazorat holati, kesh oynasida bloklash).

## `app.main` marshrut auditi (WR-02 talabi)

Har bir marshrut ko'rildi. **Yozuv** (`POST`/`PATCH`/`PUT`/`DELETE`) qiladigan yoki sessiya yaratadigan endpointlar:

| Marshrut | Metod | Darvoza (avval) | Darvoza (keyin) | Izoh |
|---|---|---|---|---|
| `/api/v1/auth/login` | POST | — | — | Principal umuman yo'q (parol bilan kiradi) |
| `/api/v1/auth/refresh` | POST | — | — | Principal yo'q (cookie); bergan tokeni har so'rovda qayta tekshiriladi |
| `/api/v1/auth/select-market` | POST | ❌ `PrincipalDep` | ✅ `CurrentPasswordDep` | **WR-02 — tuzatildi.** Sessiya yaratadi |
| `/api/v1/auth/logout` | POST | ❌ (hujjatlashtirilgan) | ❌ o'zgarmadi | Qulflangan sessiyani tark etish |
| `/api/v1/auth/change-password` | POST | ❌ (hujjatlashtirilgan) | ❌ o'zgarmadi | Darvozadan chiqish yo'lining o'zi |
| `/api/v1/me` | PATCH | ❌ `PrincipalDep` | ✅ `CurrentPasswordDep` | **WR-02 — tuzatildi.** `users.locale` yozadi + audit qatori |
| `/api/v1/users` | POST | ✅ `require_permission` | o'zgarmadi | |
| `/api/v1/users/{id}/block`, `/unblock`, `/reset-password` | POST | ✅ `require_permission` | o'zgarmadi | |

**O'qish** endpointlari: `/api/v1/auth/me` (GET) va `/api/v1/markets` (GET) `TenantSessionDep` orqali darvoza ostida; `/api/v1/users` (GET) va `/api/v1/audit*` (GET) `require_permission`/`require_platform_admin` orqali. `/api/v1/me` (GET) ATAYIN ochiq qoldi.

**Xulosa:** darvozadan tashqarida qolgan yozuv endpointlari AYNAN ikkita edi va ikkalasi ham yopildi. `deps.py` dagi "yangi endpoint darvozani qo'shishni unutishi mumkin emas" da'vosi noto'g'ri edi — u to'g'rilandi va o'rniga aniq qoida yozildi (`PrincipalDep` faqat o'qish uchun).

## Decisions Made

- **`tariffs` `FINANCIAL_TABLES` da qoldi.** Unda haqiqiy `amount_soum` bor, ya'ni uchala qo'riqchi ham ma'noga ega. Qo'riqchilari 02-05 da qo'lda yoziladi (tarif qatorida `created_at` emas, `valid_from` hukmron).
- **`GRANT CREATE ON DATABASE` rad etildi.** U ham ishlaydi (o'lchangan), lekin `sbozor_owner` ga baza darajasida sxema yaratish huquqini berardi — RLS meta-testlari umuman ko'rmaydigan sxemada jadval yaratish yo'li ochilardi.
- **`select-market` 403 `market_forbidden` bo'lib qoldi.** Reja testda 404 kutgan edi; mavjud kod va ikkita mavjud test (`test_member_cannot_select_foreign_market`, `test_unknown_market_is_also_403`) 403 ni T-01-47 anti-enumeration qarori sifatida ataylab qulflagan. 404 ga o'tish o'sha qarorni sababsiz bekor qilardi.
- **WR-03 tekshiruvi `pa` claim'i bo'yicha.** Reja "rollar to'plamida `platform_admin` yo'q" deb yozgan edi, lekin seed'dagi platforma adminining **a'zolik roli** aynan `platform_admin` (`two_markets.py`), ya'ni bayroq o'chirilsa ham rol a'zolikdan kelaveradi. Haqiqiy da'vo `pa` claim'ida: `require_platform_admin` va `markets.list_markets` aynan unga qaraydi (CR-03 darsi).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_audited_tables_have_trigger` darvozani 16 reja davomida signalsiz qoldirardi**

- **Found during:** Task 2 (`npm run test:tenancy` verifikatsiyasi)
- **Issue:** Task 1 `AUDITED_TABLES` ni 8 jadvalga kengaytirdi va o'zi "oraliqda test qizil turadi, bu ataylab" deb yozdi. Lekin Task 2 ning ham, reja darajasidagi verifikatsiyaning ham talabi — `npm run test:tenancy` exit 0. Ziddiyat haqiqiy: qizil test 02-05/02-06 gacha, ya'ni **16 ta rejaning har birida** turardi va o'sha rejalar uchun "mening o'zgarishim tenancy'ni buzdimi yoki bu o'sha ma'lum qizilmi?" savoliga javob yo'q edi. Buzilgan darvoza — darvoza emas.
- **Fix:** `PENDING_AUDIT_TRIGGERS` ro'yxati qo'shildi (sabab bilan, `INDEX_EXCEPTIONS`/`POLICY_TENANT_GUC_EXCEPTIONS` naqshida) va test `not missing` o'rniga **ikki tomonlama** solishtiruvga o'tkazildi: trigger ULANSA ham (ro'yxatdan o'chirish majburiy bo'ladi), mavjudi YO'QOLSA ham test qizaradi. Qarz ko'rinib turadi va jimgina yopilib ketolmaydi; darvoza esa 16 reja uchun ishlaydi.
- **Files modified:** `tests/tenancy/test_meta.py`
- **Verification:** `npm run test:tenancy` exit 0 (99 test)
- **Committed in:** `28b337b`

**2. [Rule 2 - Missing Critical] `btree_gist` init qadami uchun regressiya qo'riqchisi yo'q edi**

- **Found during:** Task 2
- **Issue:** `_bootstrap_extensions` fixture'i o'chirilsa yoki bog'liqligi uzilsa, nosozlik faqat 02-05 migratsiyasi yozilganda — bir necha reja keyin — ko'rinardi. Bu aynan `require_extension()` bartaraf etmoqchi bo'lgan "kechiktirilgan, sababsiz xato" turi.
- **Fix:** `test_btree_gist_extension_is_installed` qo'shildi — `pg_extension` dan ilova roli bilan o'qiydi.
- **Files modified:** `tests/tenancy/test_meta.py`
- **Verification:** `pytest tests/tenancy/test_meta.py -q` exit 0
- **Committed in:** `28b337b`

**3. [Rule 2 - Missing Critical] `PATCH /api/v1/me` darvozadan tashqarida qolgandi**

- **Found during:** Task 3 (rejadagi "har bir marshrutni aylanib chiq" qadami)
- **Issue:** Reja aniq aytadi: "qolgan har biri darvoza ostiga olinadi". Marshrut auditi `PATCH /api/v1/me` ni topdi — u `users.locale` ni yozadi va qurbon nomidan `update` audit qatori chiqaradi, ya'ni "qulflangan sessiya hech narsa yoza olmaydi" da'vosini buzardi. Fayl Task 3 ning `<files>` ro'yxatida yo'q edi.
- **Fix:** `update_profile` `CurrentPasswordDep` ga o'tkazildi; `read_profile` ATAYIN `PrincipalDep` da qoldirildi (D-13: parol almashtirish ekrani tilni bilishi kerak). UI buzilmaydi — `locale-switcher.tsx` interfeys tilini darhol o'zgartiradi va yozuv xatosini o'zi yutadi.
- **Files modified:** `services/core-api/app/api/v1/me.py`, `tests/integration/test_password_gate.py`
- **Verification:** `test_profile_write_requires_current_password` (403) va `test_profile_read_stays_open` (200) — juftlik
- **Committed in:** `17142af`

**4. [Rule 1 - Bug] `_platform_admin_market()` hamon tokendagi bayroqqa qarardi**

- **Found during:** Task 3
- **Issue:** Reja faqat `_session_roles(...)` va `issue_access(...)` ni DB qiymatiga o'tkazishni aytadi. Lekin `_platform_admin_market(session, principal, market_id)` ham `principal.is_platform_admin` ni o'qiydi — ya'ni lavozimi olib tashlangan hisob **a'zoligi bo'lmagan bozorni tanlashda davom etardi**. WR-03 ning yarmi ochiq qolardi.
- **Fix:** Funksiya imzosi `(session, market_id, *, is_platform_admin: bool)` ga o'zgartirildi; bayroq chaqiruvchida DB'dan o'qiladi.
- **Files modified:** `services/core-api/app/api/v1/auth.py`
- **Verification:** `test_select_market_rereads_platform_admin_flag` ning ikkinchi yarmi (403 `market_forbidden`)
- **Committed in:** `17142af`

**5. [Rule 1 - Bug] Audit yorlig'i eskirgan bayroqdan qurilardi**

- **Found during:** Task 3
- **Issue:** `label = principal.actor_label` tokendagi (ehtimol eskirgan) bayroqdan hisoblangan, ya'ni lavozimi olib tashlangan odam auditda hamon "platforma admini" deb yozilardi. FOUND-03 (dalil sifati) va D-09 buzilardi.
- **Fix:** Yorliq DB haqiqatidan quriladi: `platform_admin_label(who.phone_e164, market.name)` yoki `actor_label_for(roles, is_platform_admin=False)`.
- **Files modified:** `services/core-api/app/api/v1/auth.py`
- **Verification:** `test_select_market_audit_carries_platform_admin_label` (mavjud) yashil qoldi
- **Committed in:** `17142af`

**6. [Rule 2 - Missing Critical] Bloklangan hisob kesh oynasida 30 kunlik oila ocha olardi**

- **Found during:** Task 3
- **Issue:** Reja `is_active` tekshiruvini so'ragan, lekin uni **nima uchun** kerakligini test bilan isbotlash yo'lini bermagan. `get_current_principal` ham `is_active` ni ko'radi, LEKIN Valkey keshidan (`USER_STATE_TTL_SECONDS = 30`). Bloklash mahsulot endpointidan tashqari yo'ldan kelganda 30 soniyalik oyna ochiq qoladi va `select-market` o'sha oynada yangi 30 kunlik refresh oila ocha olardi.
- **Fix:** Test keshni ataylab AVVAL isitadi (`GET /auth/me` → 409), so'ng bayroqni keshni bekor qilmasdan o'chiradi. Shu tartibsiz javob `account_blocked` bo'lardi, ya'ni test boshqa qatlamni sinagan bo'lardi (green-for-wrong-reason).
- **Files modified:** `tests/integration/test_auth_login.py`
- **Verification:** `test_select_market_rejects_blocked_user_inside_the_cache_window` → 401 `invalid_credentials`
- **Committed in:** `17142af`

---

**Total deviations:** 6 auto-fixed (1 blocking, 3 missing-critical, 2 bug)
**Impact on plan:** Hammasi to'g'rilik/xavfsizlik uchun zarur edi. Deviatsiya #1 rejaning ikki qismi orasidagi haqiqiy ziddiyatni hal qildi; #3–#6 rejaning O'Z talabini (WR-02/WR-03 ni to'liq yopish) oxiriga yetkazdi. Scope creep yo'q — birorta yangi funksiya qo'shilmadi.

## Issues Encountered

- **Reja testi 404 kutgan, mavjud kontrakt 403 beradi.** `select-market` a'zoligi bo'lmagan bozor uchun 403 `market_forbidden` qaytaradi va bu T-01-47 ostida ataylab qulflangan (mavjudlik oshkor qilinmasin). 404 ga o'tish ikkita mavjud testni buzib, hujjatlashtirilgan anti-enumeration qarorini sababsiz bekor qilardi. 403 saqlandi.
- **Reja "rollar to'plamida `platform_admin` yo'q" deb kutgan.** Seed'dagi platforma adminining a'zolik roli aynan `platform_admin` (`two_markets.py:256-263`), ya'ni bayroq o'chirilsa ham rol a'zolikdan keladi — bu CR-03 hujjatlashtirgan gibrid holat. Da'vo `pa` claim'iga ko'chirildi; aynan unga `require_platform_admin` va `markets.list_markets` qaraydi.
- **Worktree'da `frontend/node_modules` yo'q edi** (gitignore). Asosiy repodagi katalogga junction qilindi — commit'ga hech narsa tushmadi, `npm ci` bilan yangi paket o'rnatilmadi.
- **Verifikatsiya #6 (`alembic upgrade head` compose orqali) worktree'da bajarilmadi:** `.env` fayli gitignore ostida va worktree'ga ko'chmagan. Ekvivalent qamrov ta'minlandi — `migrated` session fixture'i aynan `alembic upgrade head` ni `sbozor_owner` roli bilan haqiqiy `postgres:18.4-trixie` konteynerida bajaradi va undan 99 tenancy + 171 integration testi kelib chiqadi. 0001–0005 zanjiri buzilmagan.

## Known Stubs

Yo'q. Bu reja yangi funksiya bermaydi — u faqat mavjud darvozalarni to'g'ri holatga keltiradi. Barcha o'zgarishlar to'liq ulangan va testlar bilan qoplangan.

**Ataylab ochiq qoldirilgan qarz (stub emas):** `AUDITED_TABLES` dagi 7 domen jadvali hali mavjud emas va ularning audit triggerlari 02-05/02-06 da ulanadi. Bu `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` da nomma-nom qayd etilgan va ikki tomonlama qulflangan.

## Verification Results

| # | Buyruq | Natija |
|---|---|---|
| 1 | `npm run test:unit` | ✅ exit 0 (164 test) |
| 2 | `npm run test:tenancy` | ✅ exit 0 (99 test) |
| 3 | `pytest tests/integration -q` | ✅ exit 0 (171 test) |
| — | `pytest -q` (to'liq) | ✅ exit 0 (435 test) |
| 4 | `npm run lint` (ruff + format + mypy) | ✅ exit 0 (87 fayl) |
| 5 | `npm --prefix frontend run typecheck` | ✅ exit 0 |
| 5 | `npm --prefix frontend run lint` | ✅ exit 0 |
| — | `npm --prefix frontend run test:unit` | ✅ exit 0 (38 test) |
| — | `npm --prefix frontend run i18n:check` | ✅ 120 kalit × 3 til |
| 6 | `alembic upgrade head` | ✅ `migrated` fixture'i orqali (yuqoriga qarang) |

## User Setup Required

Yo'q — tashqi servis sozlamasi kerak emas.

**DIQQAT (deploy eslatmasi):** `ops/db/init/00-extensions.sql` faqat **bo'sh data katalogida** ishlaydi (`docker-entrypoint-initdb.d` konvensiyasi). MAVJUD bazada kengaytma qo'lda o'rnatiladi:

```bash
docker compose exec db psql -U postgres -d sbozor -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
```

Unutilsa 02-05 migratsiyasi `require_extension()` bilan aynan shu buyruqni ko'rsatib yiqiladi — jimgina buzilish yo'q.

## Next Phase Readiness

- **02-02 dan 02-17 gacha bo'lgan rejalar uchun darvozalar tayyor:** RBAC matritsasi usta oqimini bloklamaydi, reyestrlar 2-faza sxemasi bilan mos, `npm run test:tenancy` yashil va signal beradi.
- **02-05/02-06 uchun aniq topshiriq:** `stall_assignments` migratsiyasi `require_extension("btree_gist")` bilan boshlanadi; har bir domen jadvaliga `attach_audit_trigger()` ulangach nomi `PENDING_AUDIT_TRIGGERS` dan o'chiriladi (aks holda test qizaradi va sababni o'zi aytadi).
- **1-faza ko'rigining WR-02/WR-03 punktlari yopildi.** WR-01 va WR-04 bu rejaning qamrovida emas edi va ochiq qoladi.
- **Tavsiya (bu rejada bajarilmadi):** WR-02 ning 2-tuzatishi — `app.routes` ni aylanib chiqadigan marshrut-qamrov darvozasi (`PASSWORD_GATE_EXEMPT` xaritasi bilan) — hali yozilmagan. Hozircha darvoza qamrovi qo'lda auditlanadi, ya'ni 5-marshrut yana jimgina teshik bo'lishi mumkin. `tests/tenancy/test_cross_tenant.py::all_routes` naqshi tayyor.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-01, MARKET-02, MARKET-03, MARKET-04]` deb yozgan,
lekin bu to'rttasi **bu rejada bajarilmadi va `REQUIREMENTS.md` da `Pending` bo'lib qoldi.**

Sabab: rejaning o'z maqsadi shunday yozilgan — *"bu reja yangi funksiya bermaydi; u keyingi
16 rejaning har biri tayanadigan darvozalarni to'g'ri holatga keltiradi"*. Usta (MARKET-01),
rasta reestri (MARKET-02), tariflar (MARKET-03) va sotuvchilar (MARKET-04) 02-02…02-17
rejalarida quriladi. Fazadagi **hamma 17 reja** ayni shu ID'larni deklaratsiya qiladi, ya'ni
ularni birinchi rejadayoq "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi —
`/gsd-transition` va faza verifikatori esa aynan o'sha jadvalga qaraydi.

Belgilash o'rniga bu reja ularni **bloklashdan chiqardi**: MARKET-01 uchun RBAC to'sig'i
(Pitfall 6), MARKET-04 uchun `btree_gist` huquqi (Pitfall 1) va MARKET-02/03 uchun reyestr
nomuvofiqligi (Pitfall 3) olib tashlandi.

## Self-Check: PASSED

- Da'vo qilingan 7 fayl diskda mavjud (`00-extensions.sql`, `02-01-SUMMARY.md`,
  `schema_contract.py`, `rbac.py`, `helpers.py`, `rbac.ts`, `conftest.py`)
- Da'vo qilingan 3 vazifa commit'i git tarixida mavjud: `ab4ed09`, `28b337b`, `17142af`
  (to'rtinchisi — shu SUMMARY'ni olib keladigan `docs(02-01)` commit'ining o'zi)
- Birorta commit'da kutilmagan fayl o'chirilishi yo'q (`git diff --diff-filter=D` bo'sh)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
