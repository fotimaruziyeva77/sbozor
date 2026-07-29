---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 04
subsystem: data
tags:
  [
    alembic,
    alembic-utils,
    rls,
    postgres,
    security-definer,
    multi-tenant,
    sqlalchemy,
    tdd,
  ]

# Dependency graph
requires:
  - "01-01 (compose `migrate`/`test` profillari, `sbozor_owner`/`sbozor_app` rollari, `tests/conftest.py`)"
  - "01-03 (sbozor_core: enums, tenancy GUC nomlari, schema_contract reyestrlari, db helperlari)"
provides:
  - "Alembic async infratuzilmasi: `alembic.ini` + `migrations/env.py` (`run_sync`, `MIGRATION_DATABASE_URL`)"
  - "migrations.helpers — enable_rls/enable_tenant_rls/grant_app_dml/revoke_app_all/disable_force_for_backfill/restore_force/create_entity/drop_entity"
  - "migrations.entities.policies — TENANT_PREDICATE (NULLIF), tenant_policy(), markets_policy(), owner_bootstrap_policy()"
  - "migrations.entities.functions — auth_find_login, auth_memberships, auth_list_markets, auth_user_state (SECURITY DEFINER)"
  - "0001_identity migratsiyasi: markets, users, user_market_roles, refresh_tokens + RLS + GRANT/REVOKE"
  - "sbozor_core.models — Base (naming convention), TimestampMixin, TenantMixin, uuid_pk(), Market/User/UserMarketRole/RefreshToken"
  - "tests/fixtures/two_markets.py — MarketSeed / TwoMarketSeed + seed/cleanup"
  - "conftest fixture'lari: migrated, sync_owner_conn, two_markets, app_sessionmaker, tenant_session"
  - "36 ta tenancy testi (5 rol + 10 sxema + 8 predikat + 3 composite FK + 10 login bootstrap)"
affects:
  - "01-05 (audit: `AUDITED_TABLES`, `user_market_roles` triggeri, `audit_log` jadvali shu migratsiya ustiga quriladi)"
  - "01-06 (auth API: to'rt `SECURITY DEFINER` funksiyasi login/refresh oqimining yagona DB kontrakti)"
  - "01-07..01-10 (har bir yangi jadval `test_every_table_is_tenant_scoped` darvozasidan o'tadi)"
  - "2-faza (bozor wizard'i: `markets` yozish yo'li va `UNIQUE(market_id, id)` composite FK maqsadi)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RLS policy predikati HAR DOIM `NULLIF(current_setting(...), '')::uuid` — fail-closed (0 qator), xato emas"
    - "ENABLE + FORCE + GRANT + policy — to'rttasi bitta migratsiyada, tartib bilan; `alembic-utils` faqat policy'ni biladi"
    - "Identifikatsiya a'zolikdan ajratilgan: `users` global va app-rolga yopiq, o'qish faqat `SECURITY DEFINER` orqali"
    - "`SECURITY DEFINER` da `SET search_path = pg_catalog, public` — har bir funksiyada LITERAL, meta-test bilan qulflangan"
    - "Sxema invariantlari `pg_catalog` dan o'qiladi, ro'yxat qo'lda yuritilmaydi — yangi jadval avtomatik qamraladi"
    - "CHECK ifodalari enum'dan HOSIL QILINADI, ko'chirilmaydi; drift meta-test bilan ushlanadi"

key-files:
  created:
    - alembic.ini
    - migrations/__init__.py
    - migrations/env.py
    - migrations/script.py.mako
    - migrations/helpers.py
    - migrations/entities/__init__.py
    - migrations/entities/policies.py
    - migrations/entities/functions.py
    - migrations/versions/0001_identity.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/models/base.py
    - packages/sbozor-core/sbozor_core/models/identity.py
    - tests/fixtures/__init__.py
    - tests/fixtures/two_markets.py
    - tests/tenancy/test_rls_predicate.py
    - tests/tenancy/test_composite_fk.py
    - tests/tenancy/test_login_bootstrap.py
  modified:
    - tests/conftest.py
    - tests/tenancy/test_meta.py
    - pyproject.toml

key-decisions:
  - "A9 HAL QILINDI: `alembic-utils` autogenerate async env'da ISHLAYDI (6/6 `PGPolicy` `op.create_entity()` bo'lib chiqdi) — xom `op.execute()` fallback'iga o'tilmadi"
  - "`register_entities(..., entity_types=[PGPolicy, PGFunction])` MAJBURIY — busiz `PGGrantTable` komparatori har bir mavjud GRANT uchun `op.drop_entity()` chiqaradi"
  - "`owner_bootstrap` policy'si qo'shildi (rejada yo'q): FORCE egani ham bog'laydi, ya'ni `TO sbozor_app` policy'lari bilan `SECURITY DEFINER` funksiyalar 0 qator qaytarardi"
  - "`markets` uchun `enable_tenant_rls` emas, `enable_rls` + `grant_app_dml(ops=\"SELECT\")` — yozish `sbozor_owner` va 2-fazadagi ustadan"
  - "`REVOKE ALL ON TABLE users FROM sbozor_app` migratsiyada LITERAL yozilgan (yordamchi mavjud bo'lsa ham) — 01-03 dagi `algorithms=[\"HS256\"]` bilan bir xil qoida"
  - "`SET search_path = pg_catalog, public` to'rt funksiyada takrorlangan, umumiy konstantaga chiqarilmagan"
  - "`(market_id, user_id)` uchun alohida `CREATE INDEX` yozilmadi — `UNIQUE` konstraytining indeksi aynan shu"
  - "`RefreshToken` da `updated_at` yo'q — token qatori o'zgarmas hodisa yozuvi"

patterns-established:
  - "Pattern: migratsiya `sbozor_owner` (superuser EMAS) bilan bajariladi — FORCE ostida buziladigan narsa testda buziladi, prod'da birinchi marta emas"
  - "Pattern: har bir izolyatsiya da'vosi `sbozor_app` roli bilan isbotlanadi; `sbozor_owner` faqat seed uchun"
  - "Pattern: meta-test istisnolari sabab-izohi bilan kod ichida (`INDEX_EXCEPTIONS`, `GLOBAL_TABLES`) — istisno ko'rinadigan harakat"
  - "Pattern: composite FK maqsadi jadval tug'ilgan kuni test bilan isbotlanadi, iste'molchi jadval kelguncha kutilmaydi"
  - "Pattern: har bir 'himoya qiladi' degan test SABOTAJ bilan tekshiriladi (NULLIF olib tashlandi, enable_tenant_rls olib tashlandi)"

requirements-completed: [FOUND-01, FOUND-02]

# Metrics
duration: 45min
completed: 2026-07-29
---

# Phase 1 Plan 04: Alembic, RLS va identifikatsiya sxemasi Summary

**`alembic upgrade head` bilan quriladigan to'rt jadvalli identifikatsiya sxemasi — `NULLIF` shaklidagi fail-closed RLS policy'lari, `sbozor_app` ga butunlay yopiq `users` va to'rtta `SECURITY DEFINER` login funksiyasi — 36 ta tenancy testi bilan qulflangan va ikki sabotaj bilan sinaldi.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-07-29T05:30:00Z
- **Completed:** 2026-07-29T06:12:52Z
- **Tasks:** 3/3
- **Files created:** 17 (modifikatsiya: 3)
- **Tests:** 181 yashil (145 unit + 36 tenancy; oldin 150 edi)

## Accomplishments

- **A9 taxmini bekor qilindi — u endi o'lchangan fakt.** RESEARCH'da `alembic-utils` autogenerate'ning async env'da ishlashi "empirik tekshirilmadi" deb turardi. Tekshirildi: **ishlaydi** — oltita `PGPolicy` ning hammasi `op.create_entity()` bo'lib chiqdi. Fallback'ga (xom `op.execute()`) o'tilmadi.

- **A9 tekshiruvi rejalashtirilmagan minani ham topdi.** `register_entities()` ni filtrsiz chaqirganda `alembic-utils` `PGGrantTable` ni ham taqqoslaydi va bazadagi **har bir mavjud GRANT uchun `op.drop_entity()`** chiqaradi. Ya'ni "bo'sh" autogenerate migratsiyasi aslida `sbozor_owner` va `sbozor_app` ning barcha huquqlarini bekor qiladigan ~40 qatorli DDL bo'lib chiqadi va uni ko'z bilan ko'rmasdan qo'llagan odam prod'ni o'chiradi. `entity_types=[PGPolicy, PGFunction]` bilan yopildi.

- **Login qopqoni (Pitfall 3) haqiqatan ochildi va yopildi.** `FORCE ROW LEVEL SECURITY` jadval **egasini ham** policy'ga bo'ysundiradi. Policy'lar `TO sbozor_app` bilan cheklangani uchun ega uchun hech qanday policy qo'llanmasdi → `auth_memberships()` va `auth_list_markets()` **0 qator** qaytarardi va bozor seed qilish `new row violates row-level security policy` bilan yiqilardi. Bu reja yozilganda ko'rinmagan, chunki u faqat funksiyalar ishga tushganda paydo bo'ladi.

- **Model ↔ migratsiya pariteti isbotlandi.** Migratsiya qo'lda yozilgan, lekin `alembic revision --autogenerate` **bo'sh diff** beradi — ya'ni SQLAlchemy modellari, DDL, policy'lar va funksiyalar to'rttasi ham bir xil haqiqatni ko'rsatadi. Keyingi fazada kimdir modelga ustun qo'shsa, autogenerate darhol ko'rsatadi.

- **Testlar sabotaj bilan sinaldi, taxmin bilan emas.** (1) `TENANT_PREDICATE` dan `NULLIF` olib tashlandi → `test_same_connection_after_commit_is_still_fail_closed` aynan hujjatlashtirilgan `invalid input syntax for type uuid: ""` bilan yiqildi. (2) `enable_tenant_rls("refresh_tokens")` olib tashlandi → `test_every_table_is_tenant_scoped` `ENABLE` va `FORCE` ikkalasi yo'qligini nomma-nom aytdi. Ikkalasi ham qaytarildi.

- **Fail-closed uchdan-uchiga o'lchandi.** Tenant kontekstisiz `SELECT` → 0 qator, **xato yo'q**. Bir xil ulanishda (`pool_size=1`) COMMIT dan keyin yana 0 qator — GUC `''` bo'lib qolgani holda ham. A konteksti ostida B ga `INSERT` va A qatorini B ga ko'chiruvchi `UPDATE` — ikkalasi ham `WITH CHECK` bilan rad etildi. Kontekstsiz `UPDATE` esa xato bermay `rowcount == 0` qaytardi (yozish tomonidagi fail-closed).

- **D-06 bypass yo'qligi isbotlandi.** Platforma admini ikkala bozorga a'zo; A tanlanganda faqat A ning 3 qatorini, B tanlanganda faqat B ning 3 qatorini ko'radi. Klasterda superuser bo'lmagan `BYPASSRLS` roli yo'q va meta-test buni **butun klaster** bo'yicha tekshiradi.

## Task Commits

1. **Task 1: Alembic async infratuzilmasi, RLS asboblar to'plami va A9 tekshiruvi** — `825739f` (feat)
2. **Task 2: Identifikatsiya sxemasi + modellar + `SECURITY DEFINER` funksiyalari** — `9f0dd94` (feat)
3. **Task 3: Tenancy testlari (TDD)**
   - `dbe8ed3` (test) — RED: 29 ta test fixture'siz yiqiladi
   - `e4c0eba` (feat) — GREEN: conftest fixture'lari, 36/36 tenancy yashil

## Files Created/Modified

**Migratsiya infratuzilmasi**

- `alembic.ini` — `script_location=migrations`, `prepend_sys_path=.`, `file_template=%(rev)s_%(slug)s`, `sqlalchemy.url` ATAYIN bo'sh
- `migrations/env.py` — `run_sync(do_run_migrations)` async engine ustida; `MIGRATION_DATABASE_URL` yo'q bo'lsa aniq xato; `register_entities(..., entity_types=[PGPolicy, PGFunction])`
- `migrations/script.py.mako` — yangi tenant jadvali uchun uch qadamli eslatma bilan
- `migrations/helpers.py` — `alembic-utils` qoplamaydigan DDL + identifikator darvozasi (`_ident`) + `create_entity`/`drop_entity` tipli o'ramlari
- `migrations/entities/policies.py` — `PGPolicy` ta'riflarining yagona joyi
- `migrations/entities/functions.py` — to'rt `SECURITY DEFINER` funksiya + `GRANT_SIGNATURES`
- `migrations/versions/0001_identity.py` — sxema + RLS + GRANT/REVOKE, to'liq `downgrade()` bilan

**Modellar (`sbozor_core.models`)**

- `base.py` — `Base` (naming convention), `TimestampMixin` (ikkala ustun `timestamptz`), `TenantMixin`, `uuid_pk()` (`uuidv7()`)
- `identity.py` — `Market`, `User`, `UserMarketRole`, `RefreshToken`; `ROLES_SUBSET_CHECK` va `LOCALE_CHECK` enum'dan hosil qilinadi

**Testlar**

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `test_meta.py` | 15 | rol invariantlari (5, oldingi) + sxema invariantlari (10) |
| `test_rls_predicate.py` | 8 | fail-closed, GUC sizishi, `WITH CHECK`, tranzaksiya darvozasi |
| `test_composite_fk.py` | 3 | cross-tenant havola + NAZORAT holati + konstrayt mavjudligi |
| `test_login_bootstrap.py` | 10 | `users` yopiqligi, to'rt funksiya, D-06 bypass yo'qligi |

**Fixture'lar**

- `tests/fixtures/two_markets.py` — `MarketSeed`, `TwoMarketSeed`, `seed_two_markets()`, `cleanup_two_markets()`
- `tests/conftest.py` — `migrated`, `sync_owner_conn`, `two_markets`, `app_sessionmaker`, `tenant_session`

## Decisions Made

- **A9: autogenerate ishlaydi.** RESEARCH Open Question 1 ning "ishlamasa xom `op.execute()` ga o'tiladi" tarmog'i ishlatilmadi. `PGPolicy` ta'riflari baribir bitta faylda jamlangan, ya'ni ko'chish narxi past bo'lib qoladi.

- **`entity_types` filtri — xavfsizlik qarori, optimizatsiya emas.** Huquqlar bu loyihada `migrations/helpers.py` orqali ATAYIN aniq boshqariladi. Autogenerate ularga "yordam berishga" urinsa, u faqat zarar keltiradi.

- **`owner_bootstrap` policy'sining chegarasi qayerda.** Haqiqiy xavfsizlik chegarasi — `sbozor_app`: ilova faqat o'sha rol bilan ulanadi va u `NOSUPERUSER NOBYPASSRLS`. `sbozor_owner` esa jadvallarning **egasi** — u xohlagan payt `ALTER TABLE ... NO FORCE` qila oladi, ya'ni FORCE unga qarshi hech qachon xavfsizlik nazorati bo'lmagan, u faqat **tasodifiy** ega-tomon kirishning oldini olgan. Bu policy o'sha kirishni yashirin emas, aniq va greplanadigan qiladi — va u kengayib ketmasligi uchun `test_owner_bootstrap_policies_are_owner_only` rollar ro'yxatini `{sbozor_owner}` ga qulflaydi.

- **Ikki yangi meta-test rejadan tashqarida qo'shildi**, chunki ular dizaynning eng qimmat qismini qulflaydi:
  - `test_app_role_policies_all_reference_tenant_guc` — `sbozor_app` ga tegishli HAR BIR policy `app.market_id` ga tayanishi shart. `USING (true)` bergan bitta policy butun izolyatsiyani bir zarbada yo'q qiladi va boshqa hech qanday test buni ko'rmaydi (hamma so'rov "muvaffaqiyatli" qaytadi, faqat begona qatorlar bilan).
  - `test_role_check_constraint_matches_enum` / `test_locale_check_constraint_matches_enum` — DB dagi `CHECK` ro'yxati `sbozor_core.enums` bilan aynan mos.

- **`ck` konvensiyasi qisqa nom kutadi.** `ck_%(table_name)s_%(constraint_name)s` naqshi berilgan nomni **prefikslaydi**, shuning uchun `CheckConstraint(..., name="roles_allowed")` → `ck_user_market_roles_roles_allowed`. To'liq nom yozilsa u ikki marta prefikslanadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `SECURITY DEFINER` login funksiyalari 0 qator qaytarardi**

- **Found during:** Task 2 (`auth_memberships` / `auth_list_markets` loyihalashda)
- **Issue:** `FORCE ROW LEVEL SECURITY` jadval EGASINI ham policy'ga bo'ysundiradi (bu Pitfall 4 ning aynan o'sha mexanizmi, faqat `UPDATE` emas, `SELECT` tomonida). Policy'lar `TO sbozor_app` bilan cheklangani uchun `sbozor_owner` ga hech qanday policy qo'llanmaydi → natija deny-all. Oqibati: (a) funksiyalar `user_market_roles`/`markets` dan 0 qator qaytaradi, ya'ni **hech kim tizimga kira olmaydi**; (b) `INSERT INTO markets` seed/migratsiya yo'lida `new row violates row-level security policy` bilan yiqiladi.
- **Fix:** `owner_bootstrap_policy(table)` — `AS PERMISSIVE FOR ALL TO sbozor_owner USING (true) WITH CHECK (true)`, uchala RLS jadvalida. Sababi `policies.py` da batafsil hujjatlashtirilgan.
- **Files modified:** `migrations/entities/policies.py`, `migrations/entities/__init__.py`, `migrations/versions/0001_identity.py`
- **Verification:** `auth_memberships()` platforma adminining ikkala a'zoligini qaytaradi; `test_owner_bootstrap_policies_are_owner_only` policy'ni `{sbozor_owner}` ga qulflaydi; `test_app_role_policies_all_reference_tenant_guc` uning `sbozor_app` ga kengayib ketmasligini kafolatlaydi
- **Committed in:** `9f0dd94`

**2. [Rule 2 - Missing Critical] Autogenerate barcha GRANT'larni bekor qiladigan migratsiya chiqarardi**

- **Found during:** Task 1 (A9 tekshiruvi)
- **Issue:** `register_entities(ALL_ENTITIES)` filtrsiz chaqirilganda `alembic-utils` `PGGrantTable` komparatorini ham yoqadi. Model o'zgarmagan holatda ham autogenerate `alembic_version`, `markets`, `user_market_roles`, `refresh_tokens` ustidagi **har bir mavjud GRANT uchun `op.drop_entity()`** chiqardi — jami ~40 qator. Bunday migratsiyani o'qimasdan qo'llagan odam ilovani va migratsiya rolini bir zarbada huquqsiz qoldiradi.
- **Fix:** `register_entities(ALL_ENTITIES, entity_types=[PGPolicy, PGFunction])`, sababi `env.py` da izohda.
- **Files modified:** `migrations/env.py`
- **Verification:** takroriy A9 probe'da `PGGrantTable` soni 0, `op.create_entity` soni 8 (6 policy + 2 yo'nalish)
- **Committed in:** `825739f`

**3. [Rule 1 - Bug] `ck` konstrayt nomlari ikki marta prefikslanardi**

- **Found during:** Task 2 (birinchi `alembic upgrade head` dan keyingi `pg_constraint` tekshiruvi)
- **Issue:** Bazada `ck_user_market_roles_ck_user_market_roles_roles_allowed` paydo bo'ldi. Sabab: `MetaData(naming_convention)` dagi `ck` naqshi `%(constraint_name)s` tokenini ishlatadi, ya'ni berilgan nomni **prefikslaydi**. Nom 63 baytdan oshmagani uchun xato bermadi — jimgina xunuk nom bo'lib qoldi va uzunroq jadval nomida kesilib ketardi.
- **Fix:** `CheckConstraint(..., name="roles_allowed" / "roles_not_empty" / "locale_allowed")` — qisqa mantiqiy nomlar; model va migratsiyada bir xil, sababi izohda.
- **Files modified:** `packages/sbozor-core/sbozor_core/models/identity.py`, `migrations/versions/0001_identity.py`
- **Verification:** `pg_get_constraintdef` → `ck_users_locale_allowed`, `ck_user_market_roles_roles_allowed`, `ck_user_market_roles_roles_not_empty`
- **Committed in:** `9f0dd94`

**4. [Rule 3 - Blocking] `migrations` va `fixtures` paketlari testlardan import bo'lmasdi**

- **Found during:** Task 3 (RED)
- **Issue:** `ModuleNotFoundError: No module named 'migrations'` — pytest `sys.path` ga faqat test modulining bazaviy katalogini qo'shadi, repo ildizini emas.
- **Fix:** `[tool.pytest.ini_options] pythonpath = [".", "tests"]` va `[tool.mypy] mypy_path = "tests"`. Bu ATAYIN aniq yozildi: pytest'ning rootdir'ga qarab yo'lni o'zi to'ldirishi test faylining joylashuviga bog'liq va jimgina o'zgaradi.
- **Files modified:** `pyproject.toml`
- **Committed in:** `dbe8ed3`

**5. [Rule 1 - Bug] `markets` policy testi hech qachon o'ta olmasdi**

- **Found during:** Task 3 (GREEN)
- **Issue:** `assert "market_id" not in quals` — lekin GUC nomining O'ZI `app.market_id`, ya'ni satr har doim mavjud. Test noto'g'ri narsani tekshirardi.
- **Fix:** Tekshiruv USTUN havolasi bo'yicha: `re.search(r"\bid\s*=", quals)` bor va `re.search(r"\bmarket_id\s*=", quals)` yo'q.
- **Files modified:** `tests/tenancy/test_meta.py`
- **Committed in:** `e4c0eba`

**6. [Rule 1 - Bug] `child_table` fixture teardown tartibi seed tozalashni yiqitardi**

- **Found during:** Task 3 (GREEN)
- **Issue:** pytest fixture'larni teskari tartibda yopadi. Test signaturasida `child_table` birinchi bo'lgani uchun `two_markets` undan keyin qurilardi va **oldin** tozalanardi — probe jadvali hali `user_market_roles` ga havola qilib turganda. Natija: `ForeignKeyViolation` teardown'da.
- **Fix:** `child_table` fixture'i `two_markets` ni o'zi so'raydi → seed avval quriladi, probe keyin; yopilish tartibi to'g'ri bo'ladi. Sabab fixture docstringida.
- **Files modified:** `tests/tenancy/test_composite_fk.py`
- **Committed in:** `e4c0eba`

**7. [Rule 3 - Blocking] `pg_catalog` da `name[] = text[]` operatori yo'q**

- **Found during:** Task 3 (GREEN)
- **Issue:** `array_agg(a.attname)` `name[]` qaytaradi, `ARRAY['id','market_id']` esa `text[]`.
- **Fix:** `::name[]` kasti.
- **Files modified:** `tests/tenancy/test_composite_fk.py`
- **Committed in:** `e4c0eba`

**8. [Rule 3 - Blocking] ruff `S608` funksiya ta'riflarini SQL injection deb bildi**

- **Found during:** Task 2 (`ruff check`)
- **Issue:** `SET search_path` bloki umumiy konstantaga chiqarilib f-string bilan qo'yilgandi → to'rtta `S608`.
- **Fix:** Konstanta olib tashlandi, atributlar to'rt joyda LITERAL yozildi. Bu **kod sifati jihatidan ham to'g'riroq**: xavfsizlik uchun kritik satr har bir funksiya ta'rifida o'z ko'zi bilan ko'rinishi va `grep` bilan topilishi kerak (01-03 dagi `algorithms=["HS256"]` bilan bir xil qoida). Nusxalar orasidagi drift fail-closed emas, shuning uchun `test_security_definer_functions_pin_search_path` uni butun baza bo'yicha qulflaydi.
- **Files modified:** `migrations/entities/functions.py`
- **Committed in:** `9f0dd94`

**9. [Rule 3 - Blocking] mypy `op.create_entity` ni ko'rmasdi**

- **Found during:** Task 2 (`mypy .`)
- **Issue:** `alembic-utils` operatsiyalarni import paytida DINAMIK ro'yxatdan o'tkazadi → `Module has no attribute "create_entity"` (8 ta xato).
- **Fix:** `migrations/helpers.py` da tipli o'ramlar (`create_entity`/`drop_entity`) — bitta hujjatlashtirilgan `type: ignore`, sakkizta emas. Migratsiya fayllari `attr-defined` tekshiruvini yo'qotmaydi.
- **Files modified:** `migrations/helpers.py`, `migrations/versions/0001_identity.py`
- **Committed in:** `9f0dd94`

### Kichik moslashtirishlar (xato emas, tanlov)

- **`migrations/__init__.py` qo'shildi** (rejada yo'q): `migrations.helpers` haqiqiy paket importi bo'lishi kerak, aks holda mypy `helpers` va `entities.policies` ni turli modul nomlari bilan ko'radi.
- **`enable_rls()` va `create_entity`/`drop_entity` qo'shildi** — rejadagi yordamchilar ro'yxatidan tashqari, lekin `markets` maxsus holati va mypy uchun zarur.
- **`(market_id, user_id)` uchun alohida indeks yaratilmadi** — `UNIQUE(market_id, user_id)` konstraytining indeksi aynan shu; dublikat indeks yozish/joy narxini ikki barobar qilardi.
- **`GRANT_SIGNATURES` argument TIPLARI bilan** (`auth_find_login(text)`), parametr nomlari bilan emas — `GRANT`/`REVOKE` uchun Postgres shakli.

---

**Total deviations:** 9 auto-fixed — 3× Rule 1 (`ck` nomlari, `markets` test predikati, fixture tartibi), 1× Rule 2 (autogenerate GRANT minasi), 5× Rule 3 (owner policy, pytest yo'llari, `name[]` kasti, ruff S608, mypy `attr-defined`).
**Impact on plan:** Scope creep yo'q — barcha o'zgarishlar rejaning o'z qabul mezonlari va tahdid reyestri doirasida. Ikkitasi (#1 va #2) rejada ko'rinmagan bloklovchini yopdi: birinchisisiz login umuman ishlamasdi, ikkinchisisiz kelajakdagi autogenerate prod huquqlarini o'chirardi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Issues Encountered

- **`.env` fayli yo'q edi** (gitignore'da, worktree bilan kelmaydi). `compose --profile migrate` tekshiruvlari uchun `.env.example` dan mahalliy `.env` hosil qilindi (tasodifiy sirlar bilan, xost portlari 55432/56379/58000/58080 ga surildi). Fayl gitignore'da qoladi va commit qilinmadi.
- **A9 tekshiruvi uchun vaqtinchalik migratsiya kerak bo'ldi.** `alembic-utils` entity'larini taqqoslash uchun jadvallar mavjud bo'lishi shart, 1-taskda esa ular hali yo'q edi. Minimal `a9check_scratch` migratsiyasi yozilib, tekshiruvdan keyin `downgrade base` bilan qaytarildi va o'chirildi — repo'ga tushmadi.
- **Test konteyneridan Docker'ni boshqarish (`docker-outside-of-docker`)** 01-01 dagi sozlama bilan muammosiz ishladi; testcontainers har sessiyada toza `postgres:18.4-trixie` ko'taradi, shuning uchun `migrated` fixture'i har doim bo'sh bazadan boshlanadi.

## Known Stubs

Yo'q. Bu rejada yozilgan har bir jadval, policy, funksiya va test to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` ga qarshi tekshirilgan.

Atayin **keyingi rejalarga** qoldirilgan (stub emas, hali navbati kelmagan):

- `disable_force_for_backfill()` / `restore_force()` — 1-fazada backfill yo'q; yordamchilar Pitfall 4 naqshini hujjatlashtirish uchun yozilgan va `enable_tenant_rls` bilan bir xil `_ident()` darvozasidan o'tadi.
- `revoke_app_all()` — `users` holati migratsiyada literal yozilgani uchun hozircha chaqirilmaydi; kelajakdagi global jadvallar uchun qayta ishlatiladigan shakl sifatida qoldi.
- `markets` ga YOZISH yo'li — 2-fazadagi bozor wizard'i (hozircha faqat `sbozor_owner`).
- `business_date` generated column — 2-faza; `markets.timezone` ustuni shu sababli hozirdan sxemada (Pitfall 6).
- `audit_log` va `user_market_roles` triggeri — 01-05; `AUDITED_TABLES` reyestri uni kutmoqda.

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Reyestrdagi 9 ta dispozitsiya bajarildi va har biri test bilan qoplandi:

| Threat  | Qanday yopildi | Tekshiruv |
| ------- | -------------- | --------- |
| T-01-20 | `enable_tenant_rls()` + `tenant_policy()` uchala RLS jadvalida | `test_every_table_is_tenant_scoped`, `test_markets_rls_and_policy` |
| T-01-21 | `NULLIF(current_setting('app.market_id', true), '')::uuid` | `test_same_connection_after_commit_is_still_fail_closed` (SABOTAJ bilan sinaldi) |
| T-01-22 | `ENABLE` + `FORCE` xom DDL bilan, policy'dan ALOHIDA | `test_every_table_is_tenant_scoped` (SABOTAJ bilan sinaldi) |
| T-01-23 | Har funksiyada `SET search_path = pg_catalog, public` (literal) | `test_security_definer_functions_pin_search_path` |
| T-01-24 | `BYPASSRLS` roli yaratilmadi; login yuzasi 4 funksiya bilan cheklangan | `test_no_bypassrls_role_exists`, `test_platform_admin_sees_only_the_selected_market` |
| T-01-25 | `REVOKE ALL ON TABLE users FROM sbozor_app` | `test_app_role_cannot_select_users`, `test_users_table_is_closed_to_app_role` |
| T-01-26 | `UNIQUE(market_id, id)` + composite FK | `test_cross_tenant_reference_is_rejected` (+ nazorat holati) |
| T-01-27 | Policy `WITH CHECK` predikati | `test_insert_into_other_market_violates_with_check`, `test_update_cannot_move_row_to_other_market` |
| T-01-28 | `disable_force_for_backfill()`/`restore_force()` naqshi hujjatlashtirilgan | (accept — 1-fazada backfill yo'q) |

Qo'shimcha ravishda ikkita yangi qulf qo'shildi: `test_app_role_policies_all_reference_tenant_guc` (ilova roliga `USING (true)` bergan policy paydo bo'lishini bloklaydi) va `test_owner_bootstrap_policies_are_owner_only`.

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi.

Testlar `.env` siz ishlaydi (testcontainers):

```
docker compose --profile test run --rm tests pytest -q
```

Compose stekiga qarshi migratsiya qilish uchun `.env` kerak:

```
cp .env.example .env      # POSTGRES_PASSWORD / SBOZOR_*_PASSWORD / JWT_SECRET ni to'ldiring
npm run up
npm run migrate           # docker compose --profile migrate run --rm migrate alembic upgrade head
```

## Next Phase Readyness

**Tayyor:**

- **01-05 (audit):** `user_market_roles` jadvali va uning RLS'i mavjud; `PGTrigger` uchun `migrations/entities/` naqshi tayyor; yangi `audit_log` jadvali `test_every_table_is_tenant_scoped` darvozasidan avtomatik o'tadi (yoki `GLOBAL_TABLES` ga ataylab qo'shilishi kerak bo'ladi).
- **01-06 (auth API):** to'rt funksiyaning imzolari va qaytaradigan ustunlari qat'iy; `refresh_tokens` da `family_id`/`jti`/`replaced_by_jti` reuse-detect uchun tayyor va `sbozor_core.security.TokenClaims.family_id` bilan mos.
- **01-07+:** `TenantScopedRepository` endi haqiqiy modellar ustida ishlatilishi mumkin; `tenant_session` fixture'i integratsiya testlari uchun tayyor namuna.

**Ochiq e'tibor nuqtalari:**

- **`TenantScopedRepository.scoped()` hali `stmt.column_descriptions[0]` ga tayanadi** (01-03 da qayd etilgan). Bu rejada ORM JOIN'lari ishlatilmadi (testlar xom `text()` bilan), shuning uchun cheklov o'z kuchida qoladi. `auth_memberships` ichidagi JOIN SQL tomonda va bu sinfga kirmaydi. Birinchi ko'p jadvalli ORM so'rovi 01-06 yoki 01-07 da paydo bo'ladi — o'sha yerda hal qilinishi kerak.
- **`owner_bootstrap` policy'si `sbozor_owner` uchun FORCE ni amalda neytrallaydi.** Bu ataylab va hujjatlashtirilgan, lekin `disable_force_for_backfill()` naqshining ahamiyati kamayadi: ega endi `UPDATE` qila oladi. Kelajakda ega uchun policy'siz jadval paydo bo'lsa, Pitfall 4 qaytadan kuchga kiradi — shuning uchun yordamchilar saqlab qolindi.
- **`markets.timezone` ustuni bor, lekin hech kim o'qimaydi.** 2-fazadagi `business_date` generated column IMMUTABLE ifoda talab qiladi va boshqa ustunga havola qila olmaydi, shuning uchun u literal `'Asia/Tashkent'` bilan boshlanadi. Bozorga xos mintaqa kerak bo'lganda ifoda o'zgaradi — bu migratsiya bilan jadvalni qayta yozishni talab qiladi.
- **`.github/workflows/ci-backend.yml` bu ishni hali ko'rmadi.** Mahalliy zanjir (`ruff` + `format` + `mypy` + `pytest`) yashil; CI'da `migrated` fixture'i uchun Docker-in-Docker sozlamasi birinchi ishga tushishda kuzatilishi kerak.
