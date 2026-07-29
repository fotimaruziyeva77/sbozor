---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 05
subsystem: data
tags:
  [
    audit,
    append-only,
    postgres,
    trigger,
    plpgsql,
    rls,
    generated-column,
    business-date,
    bigint-money,
    idempotency,
    tdd,
  ]

# Dependency graph
requires:
  - "01-01 (compose `test` profili, `sbozor_owner`/`sbozor_app` rollari, `tests/conftest.py`)"
  - "01-03 (sbozor_core: AuditAction/AuditSource/ActorKind, MAX_SAFE_SOUM, timeutil.business_date, schema_contract reyestrlari)"
  - "01-04 (Alembic + `alembic-utils` entity naqshi, `enable_rls()`, `0001_identity`, `two_markets` fixture'i, meta-testlar)"
provides:
  - "`audit_log` jadvali — 4 qatlamli o'zgarmaslik (GRANT/REVOKE + RLS + 2 trigger)"
  - "migrations.entities.triggers — `fn_audit_row()` (to'jsonb diff) va `audit_immutable()`"
  - "migrations.entities.policies — `audit_append_policy()` / `audit_read_policy()`"
  - "migrations.helpers — `attach_audit_trigger()` / `detach_audit_trigger()` / `audit_trigger_name()`"
  - "migrations.helpers — `financial_guards()` + `financial_guard_statements()` (sof yarmi)"
  - "migrations.helpers — `BUSINESS_DATE_EXPR` / `MARKET_TZ_LITERAL` konstantalari"
  - "sbozor_core.models.ops — `AuditLog` modeli + `AUDIT_BUSINESS_DATE_EXPR`"
  - "0002_audit migratsiyasi (`user_market_roles` ga audit triggeri ulangan)"
  - "tests/fixtures/financial.py — `FinancialProbe` + `create_financial_probe()`"
  - "tests/integration/ — 30 ta integratsiya testi (15 audit + 15 moliyaviy)"
  - "tenant_session fixture'i endi `actor_kind` va `request_id` ni uzatadi"
affects:
  - "01-06 (auth API: `login`/`logout`/`refresh_reuse_detected` hodisalari `source='app'` bilan shu jadvalga yoziladi)"
  - "01-07 (o'qish-auditi: `action='read'` yozuvlari va `market_id IS NULL` platforma-global yo'li)"
  - "2-faza (`stalls`, `tariffs`, `stall_assignments` — har biri `financial_guards()` + `attach_audit_trigger()` bilan tug'iladi)"
  - "6-faza (`daily_charges`, `payments`, `charge_adjustments` — mezon #5 darvozasi allaqachon o'rnida)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Audit — DB-trigger, ORM hook EMAS: xom SQL yo'li ham qamraladi (D-10, Pitfall 5)"
    - "Trigger funksiyasi ATAYIN `SECURITY DEFINER` EMAS — `WITH CHECK (true)` policy yetarli, escalation yuzasi ochilmaydi"
    - "O'zgarmaslik testi HOLAT bo'yicha yoziladi, exception bo'yicha emas (Pitfall 9)"
    - "`audit_append` — `WITH CHECK (true)`: jurnalga yozishni bloklash IMKONSIZ bo'lishi kerak"
    - "Yordamchining SOF yarmi (`*_statements()`) ajratiladi — testlar nusxani emas, aynan chiqadigan DDL'ni sinaydi"
    - "`AT TIME ZONE` ikki argumentli shakl — IMMUTABLE, generated column'da yagona ishlaydigan variant"
    - "Har bir 'rad etadi' testi yonida NAZORAT HOLATI bo'ladi (yolg'on-yashilni ochadi)"

key-files:
  created:
    - migrations/entities/triggers.py
    - migrations/versions/0002_audit.py
    - packages/sbozor-core/sbozor_core/models/ops.py
    - tests/fixtures/financial.py
    - tests/integration/__init__.py
    - tests/integration/conftest.py
    - tests/integration/test_audit_write.py
    - tests/integration/test_audit_immutable.py
    - tests/integration/test_business_date.py
    - tests/integration/test_money_constraints.py
    - tests/integration/test_idempotency.py
  modified:
    - migrations/entities/policies.py
    - migrations/entities/__init__.py
    - migrations/helpers.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - tests/conftest.py
    - tests/fixtures/__init__.py
    - tests/tenancy/test_meta.py

key-decisions:
  - "`audit_append` policy'si `TO` bandisiz (PUBLIC) — trigger `SECURITY DEFINER` emas, ya'ni DML qilayotgan rol nomidan yozadi (app ham, migratsiya paytida owner ham)"
  - "`audit_log` ga `owner_bootstrap` policy'si BERILMAYDI — u `FOR ALL USING (true)` bo'lgani uchun 2-qatlamni bir zarbada yo'q qilardi"
  - "`audit_log.market_id` da FK YO'Q — audit yozuvi u tasvirlagan qatordan uzoq yashashi kerak"
  - "Audit policy'lari `migrations/entities/policies.py` ga qo'shildi (rejada joyi ko'rsatilmagan) — u fayl `PGPolicy` ta'riflarining yagona joyi"
  - "`POLICY_TENANT_GUC_EXCEPTIONS` istisnosi test faylida, `INDEX_EXCEPTIONS` naqshi bilan bir xil joyda"
  - "`changed_keys` `ORDER BY` bilan yig'iladi — testlar tartibga tayanishi mumkin"
  - "`business_date` `NOT NULL` (generated bo'lsa-da) — `at`/`created_at` NOT NULL, ya'ni bu haqiqat"
  - "`financial_guard_statements()` sof funksiya sifatida ajratildi — testlar migratsiya konteksti tashqarisida aynan o'sha DDL'ni bajaradi"

patterns-established:
  - "Pattern: reyestr (`AUDITED_TABLES`/`FINANCIAL_TABLES`) + meta-test = kelajakdagi unutishni CI'da bloklaydigan darvoza"
  - "Pattern: hali mavjud bo'lmagan jadval uchun yordamchi PROBE jadvalda isbotlanadi (mezon #5 ni 6-fazadan oldin yopish)"
  - "Pattern: grep-darvozasi bo'lgan nom test docstringida LITERAL yozilmaydi (01-03 deviatsiya #3 bilan bir xil sinf)"
  - "Pattern: himoya qiladi degan har bir test SABOTAJ bilan sinaladi (trigger olib tashlandi, CHECK olib tashlandi)"

requirements-completed: [FOUND-03, FOUND-05]

# Metrics
duration: 40min
completed: 2026-07-29
---

# Phase 1 Plan 05: O'zgarmas audit jurnali va moliyaviy konstrayt asboblari Summary

**`audit_log` — to'rt qatlamli o'zgarmaslik bilan qurilgan append-only jurnal: xom SQL bilan qilingan o'zgarish ham DB-trigger orqali yoziladi, jadval egasi ham uni tahrirlay/o'chira/TRUNCATE qila olmaydi; yoniga `financial_guards()` asboblar to'plami qo'shildi va u biznes-kun chegarasi, BIGINT so'm musbatligi hamda `ON CONFLICT` idempotentligi bo'yicha 6-fazadan ancha oldin isbotlandi — jami 36 ta yangi test.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-29T11:20:00Z
- **Completed:** 2026-07-29T12:02:00Z
- **Tasks:** 3/3
- **Files created:** 11 (modifikatsiya: 8)
- **Tests:** 217 yashil (145 unit + 42 tenancy + 30 integration; oldin 181 edi)

## Accomplishments

- **M10 teshigi yopildi va o'lchandi.** `test_raw_sql_is_audited` ORM'ni butunlay chetlab o'tadi: hech qanday obyekt yaratilmaydi, `flush()` chaqirilmaydi — faqat `session.execute(text("UPDATE user_market_roles SET ..."))`. Audit qatori baribir yoziladi va `changed_keys` AYNAN `["roles"]` bo'ladi. Sabotaj bilan tekshirildi: `attach_audit_trigger()` chaqiruvi olib tashlanganda test aynan o'zi yozgan xabar bilan yiqildi ("xom SQL orqali qilingan o'zgarish AUDITSIZ qoldi").

- **Pitfall 9 haqiqatan sodir bo'ladi — va testlar unga tayyor.** Jadval egasiga qarshi `UPDATE audit_log SET action = 'tampered'` **xato tashlamaydi**: u `rowcount == 0` qaytaradi va muvaffaqiyatli tugaydi. Shu sababli `test_owner_update_changes_nothing` va `test_owner_delete_changes_nothing` `pytest.raises` ISHLATMAYDI — ular urinishdan oldin va keyin `(id, action, table_name)` snapshot'ini olib solishtiradi. `TRUNCATE` esa 4-qatlam triggeri bilan exception beradi, ya'ni bitta faylda ikki xil verifikatsiya uslubi bor va har birining sababi yozilgan.

- **Model ↔ migratsiya pariteti DESC-indeksli va generated ustunli jadvalda ham saqlandi.** `alembic revision --autogenerate` BO'SH diff beradi: `bigint GENERATED ALWAYS AS IDENTITY`, `Computed(..., persisted=True)`, `text("at DESC")` ifodali uchta indeks — hammasi model va DDL o'rtasida mos. `downgrade base` → `upgrade head` → `downgrade -1` → `upgrade head` zanjiri xatosiz takrorlanadi.

- **`business_date` chegarasi uchala nuqtada o'lchandi va kod-qatlami bilan solishtirildi.** `19:30Z → 2026-11-06` (kun suriladi), `18:30Z → 2026-11-05`, `01:00Z → 2026-11-05`. Har bir holat `sbozor_core.timeutil.business_date()` natijasi bilan taqqoslanadi — ikki qatlam ajralib ketsa test yiqiladi. Alohida test naive `(created_at)::date` aynan 19:30Z holatida **boshqa** javob berishini ko'rsatadi, ya'ni test o'zi nimani qo'riqlayotganini isbotlaydi. Va `GENERATED ALWAYS` ustunga to'g'ridan-to'g'ri yozish `GeneratedAlways` xatosi bilan rad etiladi — kod-qatlami ikkinchi haqiqat manbaini yarata olmaydi.

- **Mezon #5 6-fazadan oldin yopildi, "keyin qilamiz" deb qoldirilmadi.** `daily_charges` ni hozir yaratib bo'lmaydi (`stalls` 2-fazada), lekin `financial_guards()` yordamchisi tayyor va u PROBE jadvalda ishga tushirildi: takroriy `ON CONFLICT DO NOTHING` `rowcount == 0` beradi va summa o'zgarmaydi; `ON CONFLICT` siz ikkinchi INSERT unique buzilishi bilan rad etiladi; ertangi kun uchun yangi hisob esa QABUL QILINADI (nazorat holati); composite FK A bozorining hisobini B bozorining rastasiga bog'lashga yo'l bermaydi.

- **Test probe jadvali yordamchining NUSXASINI emas, o'zini sinaydi.** `financial_guard_statements()` sof funksiya sifatida ajratildi va fixture aynan uning chiqishini bajaradi. Sabotaj bilan tekshirildi: `CHECK` operatori ro'yxatdan olib tashlanganda `test_zero_amount_is_rejected` va `test_negative_amount_is_rejected` darhol qizardi.

- **Ikki yangi reyestr darvozasi kelajakni qo'riqlaydi.** `test_audited_tables_have_trigger` `AUDITED_TABLES` ni `pg_trigger` bilan solishtiradi; `test_financial_tables_have_guards` esa `FINANCIAL_TABLES` dan MAVJUD bo'lganlarini tekshiradi (1-fazada vakuum, 2- va 6-fazalarda darvoza). Ya'ni `payments` yaratilgan kuni `financial_guards()` unutilsa CI qizaradi.

## Task Commits

1. **Task 1: `audit_log`, trigger funksiyalari va 4 qatlamli o'zgarmaslik** — `6f9d4d8` (feat)
2. **Task 2: Audit yozuvi va o'zgarmaslik testlari (TDD)**
   - `7840cb1` (test) — RED: 3 test `unexpected keyword argument 'request_id'` bilan yiqiladi
   - `49728a5` (feat) — GREEN: `tenant_session` `actor_kind`/`request_id` ni uzatadi, 15/15 yashil
3. **Task 3: Moliyaviy konstrayt asboblar to'plami (TDD)**
   - `49afd86` (test) — RED: `cannot import name 'financial_guard_statements'`
   - `fba7110` (feat) — GREEN: `financial_guards()` + sof yarmi, 15/15 yashil

## Files Created/Modified

**Migratsiya qatlami**

- `migrations/entities/triggers.py` — `fn_audit_row()` (`to_jsonb` diff, `jsonb_each` + `IS DISTINCT FROM`, no-op UPDATE'da `RETURN NULL`) va `audit_immutable()`; ikkalasi ham `SET search_path = pg_catalog, public`, ikkalasi ham `SECURITY DEFINER` EMAS
- `migrations/entities/policies.py` — `audit_append_policy()` (`FOR INSERT WITH CHECK (true)`) va `audit_read_policy()` (`FOR SELECT` + `TENANT_PREDICATE`)
- `migrations/helpers.py` — `audit_trigger_name()` / `attach_audit_trigger()` / `detach_audit_trigger()` + `financial_guards()` / `financial_guard_statements()` / `BUSINESS_DATE_EXPR` / `MARKET_TZ_LITERAL`
- `migrations/versions/0002_audit.py` — jadval, 3 indeks, GRANT/REVOKE, `enable_rls`, 2 policy, 2 immutability triggeri, `attach_audit_trigger("user_market_roles")`; to'liq `downgrade()` bilan

**Model**

- `packages/sbozor-core/sbozor_core/models/ops.py` — `AuditLog` (append-only docstring, `TimestampMixin`/`TenantMixin` ATAYIN ishlatilmagan, FK yo'qligining sababi yozilgan)

**Testlar** — 36 ta yangi

| Fayl | Testlar | Nima qulflangan |
| ---- | ------- | --------------- |
| `tests/integration/test_audit_write.py` | 8 | ORM yo'li, xom SQL yo'li (M10), no-op bosilishi, DELETE nusxasi, cross-tenant, `system` aktor, aktorsiz yozuv |
| `tests/integration/test_audit_immutable.py` | 7 | 1-qatlam (3 ta app-rol), 2/3-qatlam (2 ta holat bo'yicha), 4-qatlam TRUNCATE, `session_replication_role` |
| `tests/integration/test_business_date.py` | 6 | uch chegara holati, DB↔kod pariteti, naive kast farqi, `GENERATED ALWAYS` yozishni rad etishi |
| `tests/integration/test_money_constraints.py` | 5 | 0 va -1 rad etiladi, nazorat holati, `MAX_SAFE_SOUM` round-trip, tip `bigint` |
| `tests/integration/test_idempotency.py` | 4 | `ON CONFLICT` no-op, `ON CONFLICT` siz unique buzilishi, ertangi kun nazorat holati, cross-tenant FK |
| `tests/tenancy/test_meta.py` (+6) | 21 | audit policy to'plami, grantlar, `prosecdef`, `attgenerated`, ikki reyestr darvozasi |

**Test infratuzilmasi**

- `tests/fixtures/financial.py` — `FinancialProbe`, `create_financial_probe()`, `drop_financial_probe()`, umumiy SQL konstantalari
- `tests/integration/conftest.py` — `financial_probe` fixture'i (faqat reyestr; DDL `fixtures` da)
- `tests/conftest.py` + `tests/fixtures/__init__.py` — `tenant_session(market_id, actor_id, *, actor_kind, request_id)`

## Decisions Made

- **`audit_append` policy'si `TO` bandisiz (ya'ni `PUBLIC`).** `fn_audit_row()` `SECURITY DEFINER` bo'lmagani uchun u DML qilayotgan rol nomidan yozadi — bu `sbozor_app` ham, seed/migratsiya paytida `sbozor_owner` ham bo'lishi mumkin. Policy'ni bitta rolga bog'lash ikkinchisining audit yozuvini JIMGINA yo'qotardi. Bu — `test_app_role_policies_all_reference_tenant_guc` dagi yagona hujjatlashtirilgan istisno va uning chegarasi `test_audit_read_policy_is_tenant_scoped` bilan alohida qulflangan (o'qish to'liq tenant-scoped bo'lib qoladi).

- **`audit_log` ga `owner_bootstrap` policy'si BERILMADI.** 01-04 da u uchala RLS jadvaliga qo'yilgan edi, lekin bu yerda u zarar keltirardi: `FOR ALL ... USING (true)` egaga `UPDATE`/`DELETE` da qatorlarni ko'rsatib qo'yardi va o'zgarmaslikning 2-qatlamini yo'q qilardi. Sabab `migrations/entities/__init__.py` dagi `RLS_TABLES` docstringida yozilgan, chunki keyingi jadval qo'shgan odam ro'yxatni ko'rib "audit_log ham shu yerda bo'lishi kerak" deb o'ylashi mumkin.

- **`market_id` da FOREIGN KEY yo'q.** `ON DELETE CASCADE` audit izini o'chirardi, `RESTRICT` esa bozorni o'chirishni umuman imkonsiz qilardi. Bundan tashqari DELETE audit qatori aynan o'chirilayotgan qator bilan bir tranzaksiyada yoziladi. Sabab modelda hujjatlashtirilgan.

- **`financial_guard_statements()` sof funksiya sifatida ajratildi.** Reja "aynan bir xil SQL" ni talab qildi; nusxa yozish o'rniga yordamchining SOF yarmi ajratildi va testlar aynan uni bajaradi. Endi migratsiya yordamchisi o'zgarsa test avtomatik yangi DDL'ni sinaydi — drift imkonsiz.

- **`business_date` `NOT NULL` deb e'lon qilindi.** Generated ustun uchun bu majburiy emas, lekin `at`/`created_at` `NOT NULL` bo'lgani uchun u haqiqat — va model `Mapped[date]` (`date | None` emas) bo'lib qoladi, ya'ni chaqiruvchi kodda keraksiz `None` tekshiruvi paydo bo'lmaydi.

- **`changed_keys` `array_agg(... ORDER BY n.k)` bilan yig'iladi.** RESEARCH namunasida tartib yo'q edi. Tartibsiz massiv testlarni flaky qilardi va hisobotda ustunlar har safar boshqa tartibda ko'rinardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `audit_append` policy'si mavjud meta-test darvozasini yiqitardi**

- **Found during:** Task 1
- **Issue:** `test_app_role_policies_all_reference_tenant_guc` (01-04) `sbozor_app` yoki `PUBLIC` ga tegishli HAR BIR policy `app.market_id` ga murojaat qilishini talab qiladi. `audit_append` esa ataylab `WITH CHECK (true)` — ya'ni migratsiya qo'llanishi bilan butun tenancy darvozasi qizarardi.
- **Fix:** `POLICY_TENANT_GUC_EXCEPTIONS` istisno to'plami (`INDEX_EXCEPTIONS` naqshi bilan bir xil joyda va shaklda), sababi kod ichida yozilgan. Istisno KENGAYIB ketmasligi uchun `test_audit_read_policy_is_tenant_scoped` qo'shildi: u `audit_log` da AYNAN ikkita policy (`a` va `r`) borligini va `audit_read` tenant GUC'iga tayanishini talab qiladi.
- **Files modified:** `tests/tenancy/test_meta.py`, `packages/sbozor-core/sbozor_core/schema_contract.py`
- **Committed in:** `6f9d4d8`

**2. [Rule 2 - Missing Critical] Rejadagi qabul mezonlarining yarmi avtomatik tekshiruvsiz qolardi**

- **Found during:** Task 1
- **Issue:** Task 1 ning qabul mezonlari (`has_table_privilege` to'rtligi, `prosecdef = f`, `proconfig`, `attgenerated = 's'`) faqat qo'lda SQL bilan tekshiriladigan qilib yozilgan edi — ya'ni bir marta tasdiqlanib, keyin regressiyaga ochiq qolardi.
- **Fix:** To'rtta meta-test: `test_audit_log_is_read_only_for_app_role`, `test_audit_trigger_function_is_not_security_definer`, `test_audit_log_business_date_is_stored_generated`, `test_audit_read_policy_is_tenant_scoped`.
- **Files modified:** `tests/tenancy/test_meta.py`
- **Committed in:** `6f9d4d8`

**3. [Rule 1 - Bug] Test grep-darvozasi o'z docstringi bilan buzilardi**

- **Found during:** Task 2 (qabul mezonini tekshirishda)
- **Issue:** Qabul mezoni: `grep -c 'pytest.raises' ...::test_owner_update_changes_nothing` → 0. Mening docstringim esa "`pytest.raises` ATAYIN ISHLATILMAGAN" deb yozilgan edi → grep 1 qaytardi. Bu 01-01 va 01-03 dagi bilan AYNAN bir xil sinf xato (literal token izohda).
- **Fix:** Funksiya docstringi ma'nosini saqlagan holda qayta yozildi ("istisno kutuvchi kontekst-menejer"). To'liq tushuntirish modul docstringida qoladi — u yerda grep darvozasi yo'q va faylda `pytest.raises` baribir ISHLATILADI (app-rol testlari), ya'ni fayl bo'yicha nol talab qilish mumkin emas.
- **Files modified:** `tests/integration/test_audit_immutable.py`
- **Verification:** `sed -n '/def test_owner_update_changes_nothing/,/^def test_owner_delete/p' ... | grep -c 'pytest.raises'` → `0`
- **Committed in:** `49728a5`

**4. [Rule 1 - Bug] Audit testlari seed qoldirgan qatorni o'ziniki deb hisoblardi**

- **Found during:** Task 2 (RED)
- **Issue:** `two_markets` seed'i a'zolik qatorini `sbozor_owner` bilan yozadi va trigger o'sha yerda `insert` audit qatorini qo'yadi. Testlar esa `row_id` bo'yicha filtrlab "bitta qator" kutardi → `assert 2 == 1`. `test_noop_update_writes_nothing` esa seed qatorini "no-op UPDATE yaratdi" deb ko'rsatardi — ya'ni yolg'on-qizil.
- **Fix:** `_audit_rows(..., action=...)` filtri. `test_noop_update_writes_nothing` esa endi IKKI narsani tekshiradi: yangi `update` qatori yo'q VA to'liq ro'yxat aynan `[insert]` bo'lib qolgan.
- **Files modified:** `tests/integration/test_audit_write.py`
- **Committed in:** `7840cb1` (RED to'g'ri sabab bilan yiqilishi uchun RED dan oldin tuzatildi)

**5. [Rule 3 - Blocking] `tests.integration.conftest` dan import ikki marta yuklanish xavfini tug'dirardi**

- **Found during:** Task 3
- **Issue:** Probe jadvali konstantalarini `tests/integration/conftest.py` da saqlab, testlardan `from tests.integration.conftest import ...` qilish rejalashtirilgandi. `tests/` da `__init__.py` yo'q (namespace paket), conftest'ni esa pytest o'zi ALOHIDA modul sifatida yuklaydi — natijada `FinancialProbe` klassi ikki xil obyekt bo'lib qolardi.
- **Fix:** Konstantalar va fabrika `tests/fixtures/financial.py` ga ko'chirildi (01-04 da o'rnatilgan naqsh: conftest — fixture REYESTRI, ma'lumot fabrikasi emas). `tests/integration/conftest.py` faqat yupqa fixture bo'lib qoldi.
- **Files modified:** `tests/fixtures/financial.py` (yangi), `tests/integration/conftest.py`
- **Committed in:** `49afd86`

**6. [Rule 3 - Blocking] mypy `AsyncSession.execute()` natijasida `rowcount` ni ko'rmadi**

- **Found during:** Task 2 (GREEN)
- **Issue:** `AsyncSession.execute()` umumiy `Result[Any]` e'lon qiladi, `rowcount` esa `CursorResult` da → uchta `attr-defined` xatosi.
- **Fix:** `_rowcount(result)` yordamchisi — `isinstance(result, CursorResult)` tekshiruvi tipni ham to'g'rilaydi, kutilmagan natija turini ham ushlaydi.
- **Files modified:** `tests/integration/test_audit_write.py`
- **Committed in:** `49728a5`

**7. [Rule 3 - Blocking] ruff `S608` probe SQL'ini injection deb bildi**

- **Found during:** Task 3 (GREEN)
- **Issue:** Jadval nomi konstantasidan f-string bilan qurilgan `SELECT`/`INSERT` matnlari 6 ta `S608` berdi.
- **Fix:** Jadval nomlari SQL matnlarida LITERAL yozildi — `tests/tenancy/test_composite_fk.py` da 01-04 da o'rnatilgan qoida. `PARENT_TABLE`/`CHILD_TABLE` konstantalari faqat jadval NOMI kerak bo'lgan joyda qoldi (`financial_guard_statements()` argumenti, `information_schema` so'rovi).
- **Files modified:** `tests/fixtures/financial.py`, uchala moliyaviy test fayli
- **Committed in:** `fba7110`

**8. [Rule 3 - Blocking] `E501` / `I001` / formatlash**

- **Found during:** Task 1 va 3
- **Issue:** Migratsiya docstringidagi jadval 124 belgi; `migrations` importi noto'g'ri blokda (ruff uchun u first-party emas).
- **Fix:** Jadval torroq yozildi; import bloklari `ruff format` bilan tartibga solindi.
- **Committed in:** `6f9d4d8`, `fba7110`

### Kichik moslashtirishlar (xato emas, tanlov)

- **Audit policy'lari `migrations/entities/policies.py` ga qo'shildi.** Reja ularni migratsiya ichida yaratishni ko'rsatgan, joyini aniqlamagan. O'sha fayl docstringi o'zini "`PGPolicy` ta'riflarining YAGONA joyi" deb e'lon qiladi va `alembic-utils` faqat ro'yxatdan o'tgan entity'ni kuzatadi — ya'ni policy'ni migratsiya ichida qoldirish autogenerate nazoratidan chiqarardi.
- **`tests/fixtures/financial.py` va `tests/integration/conftest.py`** rejaning fayl ro'yxatida yo'q — ular test infratuzilmasi (yuqoridagi deviatsiya #5).
- **`tests/conftest.py` va `tests/fixtures/__init__.py`** ham ro'yxatda yo'q — `actor_kind`/`request_id` siz `<behavior>` dagi ikki holatni umuman yozib bo'lmasdi.
- **`test_app_cannot_disable_triggers` takrorlanmadi** — u 01-01 dan beri `test_meta.py` da bor. Uning o'rniga `test_app_cannot_bypass_trigger_via_replication_role` yozildi: u huquq xatosidan tashqari sozlamaning `origin` bo'lib qolganini ham tekshiradi.
- **`test_app_role_cannot_truncate_audit_log` qo'shildi** (rejada yo'q): 1-qatlam `TRUNCATE` ni ham qamrashini ko'rsatadi, ya'ni 4-qatlam AYNAN egaga qarshi kerakligi aniq bo'ladi.
- **`test_next_business_day_is_a_separate_charge` qo'shildi** (rejada yo'q): unique kalitdan `business_date` tushib qolsa idempotentlik testlari baribir o'tardi — bu nazorat holati o'sha teshikni yopadi.

---

**Total deviations:** 8 auto-fixed — 2× Rule 1 (grep darvozasi, seed qatori), 2× Rule 2 (meta-test darvozasi, isbotsiz qabul mezonlari), 4× Rule 3 (import topologiyasi, mypy, ruff S608, formatlash).
**Impact on plan:** Scope creep yo'q. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi; ikkitasi (#1 va #2) rejada ko'rinmagan holatni yopdi — birinchisisiz migratsiya mavjud tenancy darvozasini yiqitardi, ikkinchisisiz Task 1 ning yarim qabul mezoni bir martalik qo'l tekshiruvi bo'lib qolardi.

## Issues Encountered

- **`.env` fayli yo'q edi** (gitignore'da, worktree bilan kelmaydi). `compose --profile migrate` bilan tekshirish uchun mahalliy `.env` hosil qilindi, lekin mavjud `pgdata` volume'i eski parollar bilan initsializatsiya qilingan ekan (`password authentication failed for user "sbozor_owner"`). Foydalanuvchining dev bazasini buzmaslik uchun volume'ga TEGILMADI: `.env` va vaqtinchalik `db` konteyneri o'chirildi, migratsiya tekshiruvlari esa `tests` profilidagi testcontainers orqali bajarildi (u har safar toza `postgres:18.4-trixie` ko'taradi va `migrated` fixture'i aynan prod migratsiyasini ishga tushiradi).
- **Round-trip va autogenerate tekshiruvlari vaqtinchalik test fayli bilan bajarildi** (`downgrade base` → `upgrade head` → `downgrade -1` → `upgrade head` va bo'sh autogenerate diff). Fayl tekshiruvdan keyin o'chirildi va commit qilinmadi. `alembic_utils` komparatori `include_schemas` opsiyasini talab qiladi — bu faqat qo'lda `MigrationContext.configure()` chaqirilganda ahamiyatli, `env.py` uni allaqachon beradi.
- **Audit qatorlari test sessiyasi davomida to'planadi** va ularni o'chirib bo'lmaydi (RLS egani ham bloklaydi — bu aynan kutilgan xulq). `two_markets` har testda yangi UUID'lar hosil qilgani uchun testlar bir-biriga ta'sir qilmaydi.

## Known Stubs

Yo'q. Bu rejada yozilgan har bir jadval, policy, funksiya, yordamchi va test to'liq ishlaydi va haqiqiy `postgres:18.4-trixie` ga qarshi tekshirilgan.

Atayin **keyingi fazalarga** qoldirilgan (stub emas, hali navbati kelmagan):

- **`actor_label` ustuni hozircha hech kim tomonidan to'ldirilmaydi.** Trigger uni yozmaydi (D-06 "platforma admini X bozorida" matni ilova qatlamining ishi) — u 01-06/01-07 da auth oqimi bilan to'ladi.
- **`ip` ustuni ham bo'sh.** IP faqat HTTP so'rovi kontekstida ma'lum; DB-trigger uni bilmaydi. `source='app'` yozuvlari uchun 01-06 da to'ldiriladi.
- **`source='app'` yo'li hali yo'q** — `login`, `logout`, `read` hodisalari 01-06 va 01-07 rejalarida yoziladi. Jadval va model ularni allaqachon qo'llab-quvvatlaydi.
- **`market_id IS NULL` (platforma-global) yozuvlarni o'qish yo'li yo'q.** `audit_read` policy'si tenant-scoped, ya'ni ular hech kimga ko'rinmaydi. Bu ataylab: platforma admini uchun alohida tor `SECURITY DEFINER` funksiya 01-07 da qo'shiladi.
- **`FINANCIAL_TABLES` dagi beshta jadvalning hech biri hali mavjud emas.** `test_financial_tables_have_guards` shu sababli hozircha vakuum — u 2- va 6-fazalarda darvoza bo'lib ishlaydi.
- **`financial_guards()` hali birorta HAQIQIY migratsiyada chaqirilmagan.** U probe jadvalda isbotlangan; birinchi haqiqiy chaqiruv 2-fazada (`tariffs`, `stall_assignments`).

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Reyestrdagi 10 ta dispozitsiya bajarildi va har biri test bilan qoplandi:

| Threat  | Qanday yopildi | Tekshiruv |
| ------- | -------------- | --------- |
| T-01-29 | `fn_audit_row()` DB-triggeri (ORM hook EMAS) | `test_raw_sql_is_audited` (SABOTAJ bilan sinaldi) |
| T-01-30 | `REVOKE UPDATE, DELETE, TRUNCATE ... FROM sbozor_app` | `test_app_role_cannot_update_audit_log`, `..._delete_...`, `test_audit_log_is_read_only_for_app_role` |
| T-01-31 | UPDATE/DELETE uchun policy YO'Q + `audit_no_mutate` triggeri | `test_owner_update_changes_nothing`, `test_owner_delete_changes_nothing` (HOLAT bo'yicha) |
| T-01-32 | `audit_no_truncate` `BEFORE TRUNCATE FOR EACH STATEMENT` | `test_owner_truncate_is_rejected_and_changes_nothing`, `test_app_role_cannot_truncate_audit_log` |
| T-01-33 | App-rolga `session_replication_role` huquqi yo'q | `test_app_cannot_bypass_trigger_via_replication_role` |
| T-01-34 | `audit_read` policy'si `NULLIF` predikati bilan | `test_audit_row_is_invisible_to_other_market`, `test_audit_read_policy_is_tenant_scoped` |
| T-01-35 | `fn_audit_row()` ataylab `SECURITY DEFINER` EMAS | `test_audit_trigger_function_is_not_security_definer` |
| T-01-36 | `financial_guards()` `CHECK (amount_soum > 0)`, ustun `bigint` | `test_zero_amount_is_rejected`, `test_negative_amount_is_rejected`, `test_amount_column_type_is_bigint` (SABOTAJ bilan sinaldi) |
| T-01-37 | `UNIQUE(market_id, ..., business_date)` + `ON CONFLICT DO NOTHING` | `test_second_insert_with_on_conflict_is_a_no_op`, `test_next_business_day_is_a_separate_charge` |
| T-01-38 | `business_date` generated STORED ustuni | `test_after_local_midnight_rolls_to_the_next_day`, `test_db_matches_code_layer_business_date`, `test_naive_date_cast_disagrees_at_the_boundary` |

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi.

```
docker compose --profile test run --rm tests pytest -q
```

## Next Phase Readiness

**Tayyor:**

- **01-06 (auth API):** `audit_log` da `login`/`logout`/`login_failed`/`refresh_reuse_detected` uchun ustunlar tayyor (`action`, `actor_label`, `ip`, `request_id`, `source='app'`). `set_tenant_context()` allaqachon `app.actor_id` va `app.actor_kind` ni o'rnatadi, ya'ni har qanday DML avtomatik to'g'ri aktor bilan yoziladi — endpoint kodida qo'shimcha ish yo'q.
- **01-07 (o'qish auditi):** `action='read'` va `source='app'` qiymatlari `sbozor_core.enums` da bor; `market_id IS NULL` yo'li uchun policy dizayni allaqachon hujjatlashtirilgan.
- **2- va 6-fazalar:** yangi moliyaviy jadval uchun retsept uch satr — `enable_tenant_rls(t)` + `attach_audit_trigger(t)` + `financial_guards(t, unique_cols=[...], parent=(...))`, hamda `AUDITED_TABLES` reyestriga bir satr. Uni unutish CI'da bloklanadi.

**Ochiq e'tibor nuqtalari:**

- **`fn_audit_row()` `row_id` ni `uuid` ga keltiradi**, ya'ni triggerni birlamchi kaliti `uuid` bo'lmagan jadvalga ulab bo'lmaydi (`audit_log` ning o'ziga ham). Bu cheklov `attach_audit_trigger()` docstringida yozilgan; bigint-kalitli jadval paydo bo'lsa funksiya `row_id` ni `text` ga o'tkazishi kerak bo'ladi.
- **Audit jurnalining o'sishi va saqlash muddati boshqarilmaydi.** 90 kun / 1 yil siyosati (spec §5) snapshot arxiviga tegishli, `audit_log` uchun esa hali qaror yo'q. Jurnal o'zgarmas bo'lgani uchun keyinchalik partitsiyalash (`business_date` bo'yicha `PARTITION BY RANGE`) tabiiy yo'l — ustun allaqachon o'rnida.
- **`markets.timezone` ustuni hali hech kim tomonidan o'qilmaydi.** `financial_guards()` da mintaqa literal `'Asia/Tashkent'`; per-market mintaqa kerak bo'lganda `timezone` ni moliyaviy qatorning O'ZIGA denormalizatsiya qilish kerak (generated column boshqa jadvalga murojaat qila olmaydi). Cheklov yordamchi docstringida yozilgan.
- **`.github/workflows/ci-backend.yml` bu ishni hali ko'rmadi.** Mahalliy zanjir (`ruff` + `format` + `mypy` + 217 test) yashil; CI'da testcontainers uchun Docker sozlamasi birinchi ishga tushishda kuzatilishi kerak.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 19 ta artefaktning (11 yangi + 8 modifikatsiya) hammasi mavjud (`ls -1` bilan tekshirildi) va git'da kuzatilmoqda.
- **Commitlar:** `6f9d4d8`, `7840cb1`, `49728a5`, `49afd86`, `fba7110` — beshtasi ham `git log` da mavjud.
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D --name-only 0f030e1..HEAD` bo'sh.
- **Umumiy artefaktlarga tegilmadi:** `git diff --name-only 0f030e1..HEAD` da `STATE.md` ham, `ROADMAP.md` ham YO'Q (worktree rejimi — ularni orkestrator yangilaydi).
- **Darvozalar:** `ruff check .` + `ruff format --check .` + `mypy .` (strict, 51 fayl) + `pytest -q` (217 test: 145 unit + 42 tenancy + 30 integration) — hammasi yashil.
- **Migratsiya:** `alembic downgrade base` → `upgrade head` → `downgrade -1` → `upgrade head` xatosiz takrorlanadi; `alembic revision --autogenerate` BO'SH diff beradi (model ↔ migratsiya pariteti `Identity`, `Computed` va `DESC` ifodali indekslar bilan ham saqlangan).
- **Sabotaj tekshiruvlari (3 ta):** (1) `attach_audit_trigger()` olib tashlanganda `test_audited_tables_have_trigger` VA `test_raw_sql_is_audited` yiqildi; (2) `financial_guard_statements()` dan `CHECK` operatori olib tashlanganda `test_zero_amount_is_rejected` va `test_negative_amount_is_rejected` yiqildi. Ikkalasi ham qaytarildi va to'plam yana yashil.
- **Grep darvozasi:** `test_owner_update_changes_nothing` va `test_owner_delete_changes_nothing` doirasida `pytest.raises` → 0 ta.
- **Ishchi katalog toza:** `git status --short` bo'sh; vaqtinchalik `.env` va scratch test fayllari o'chirildi.
