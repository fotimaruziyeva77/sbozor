---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 05
subsystem: database
tags: [alembic, postgres, rls, trigger, generated-column, security-definer, autogenerate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-04 — `sbozor_core.models.market` (jadval/ustun/konstrayt nomlarining yagona manbai), `MARKET_DOMAIN_TENANT_TABLES`/`TEMPORAL_TENANT_TABLES`, `MARKET_DOMAIN_FUNCTIONS`, `MARKET_DOMAIN_TRIGGER_FUNCTIONS`; 02-01 — `AUDITED_TABLES`/`FINANCIAL_TABLES` reyestrlari va `PENDING_AUDIT_TRIGGERS` qulfi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`migrations/helpers.py` (`enable_tenant_rls`, `attach_audit_trigger`, `BUSINESS_DATE_EXPR`), `tenant_policy()`/`owner_bootstrap_policy()`, `fn_audit_row()`, `0001`–`0006` migratsiya zanjiri"
provides:
  - "`migrations/versions/0007_market_domain.py` — market_profile / zones / stall_categories / stalls / stall_code_registry + RLS + audit + `trg_stall_code_claim`"
  - "`migrations/versions/0008_temporal.py` — stall_category_periods / tariffs + RLS + audit + ikkita o'zgarmaslik triggeri"
  - "`market_create` / `market_activate` / `market_rename` bazada, `PUBLIC` dan yopiq, `sbozor_app` ga ochiq"
  - "`migrations.helpers.attach_immutability_trigger()` / `detach_immutability_trigger()`"
  - "`MARKET_CORE_FUNCTIONS` (0007) va `MARKET_CALENDAR_FUNCTIONS` (0010) — migratsiya-scope'li funksiya ro'yxatlari"
  - "`tests/tenancy/test_market_domain_meta.py` — Alembic ko'rmaydigan trigger/konstrayt/huquq-rejimi darvozasi (10 test)"
  - "`test_autogenerate_is_empty` + `PENDING_DOMAIN_TABLES` ikki tomonlama qulfi"
affects: [02-06, 02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 02-13, 02-14, 02-15, 02-16, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`compare_metadata()` mid-faza holatida `alembic_utils` reyestrini vaqtincha bo'shatishni talab qiladi — uning komparatori entity'ni HAQIQATAN yaratib ko'radi"
    - "Migratsiya-scope'li funksiya ro'yxati: `LANGUAGE sql` funksiya tanasi CREATE paytida validatsiya qilinadi, ya'ni u faqat barcha jadvallari mavjud bo'lgan migratsiyada tug'ilishi mumkin"
    - "Qarz reyestri (`PENDING_*`) ikki tomonlama `==` bilan qulflanadi — keyingi reja uni bo'shatmasa test qizaradi"
    - "Trigger darvozasi `pg_trigger.tgtype` bitlari bilan yoziladi, `pg_get_triggerdef()` matni bilan emas"

key-files:
  created:
    - migrations/versions/0007_market_domain.py
    - migrations/versions/0008_temporal.py
    - tests/tenancy/test_market_domain_meta.py
  modified:
    - migrations/helpers.py
    - migrations/entities/functions.py
    - tests/tenancy/test_meta.py

key-decisions:
  - "`0007` beshta funksiyadan FAQAT uchtasini yaratadi — `market_is_open()` `LANGUAGE sql` bo'lib tanasi CREATE paytida parse qilinadi va hali mavjud bo'lmagan `market_calendar_exceptions` da yiqilardi"
  - "`MARKET_DOMAIN_FUNCTIONS` `MARKET_CORE_*` (0007) va `MARKET_CALENDAR_*` (0010) ga bo'lindi — 02-04 dagi `AUDIT_TRIGGER_FUNCTIONS` naqshining aynan takrori"
  - "`test_autogenerate_is_empty` `alembic_utils` reyestrini vaqtincha bo'shatadi: to'liq `compare_metadata()` faza tugamaguncha texnik jihatdan MUMKIN EMAS (`CREATE POLICY ... ON public.vendors` bilan yiqiladi, o'lchandi)"
  - "`test_stall_code_claim_trigger_exists` `AFTER` ni talab qiladi, `BEFORE` ni EMAS — reja matni RESEARCH Pattern 8 dan kelgan, 02-04 esa uni o'lchov bilan bekor qilgan"
  - "`PENDING_AUDIT_TRIGGERS` ikki bosqichda qisqartirildi (Task 1 da 2 ta, Task 2 da 2 ta) — har bir vazifa o'z-o'zicha yashil bo'lishi uchun"
  - "`financial_guards(\"tariffs\")` chaqirilmadi va uchala qo'riqchi qo'lda yozildi (reja talabi, o'lchov bilan isbotlandi)"

patterns-established:
  - "Pattern: migratsiya `LANGUAGE sql` funksiyani faqat uning BARCHA havolalari mavjud bo'lgan revisionda yaratadi; plpgsql uchun bu cheklov yo'q, lekin ro'yxat baribir scope bo'yicha bo'linadi"
  - "Pattern: `compare_metadata()` darvozasi `include_object` filtri + `PENDING_*` ro'yxati bilan bosqichma-bosqich kengayadi va o'zi-o'zini escalate qiladi"
  - "Pattern: xulq testi va mavjudlik testi JUFTLIKDA yoziladi (trigger bor + trigger ishlaydi) — biri ikkinchisining yolg'on-yashilini yopadi"

requirements-completed: []

# Metrics
duration: 30min
completed: 2026-07-31
---

# Phase 2 Plan 05: Yadro sxema va temporal jadvallar Summary

**Yettita domen jadvali, uchta bozor funksiyasi va uchta domen triggeri `postgres:18.4-trixie` da qurildi; D-02 (rasta raqami qayta ishlatilmaydi) va D-07 (o'tgan tarif qulflanadi) kafolatlari ilova qatlamisiz, `sbozor_owner` ga qarshi ham o'lchov bilan isbotlandi.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-31T12:37Z
- **Completed:** 2026-07-31T13:07Z
- **Tasks:** 3/3
- **Files:** 6 (3 yaratildi, 3 o'zgartirildi)

## Accomplishments

- **Beshta invariant yettita yangi jadvalning har birida bajarildi va buni QO'LDA hech kim tekshirmadi** — `test_every_table_is_tenant_scoped` va `test_tenant_indexes_lead_with_market_id` `pg_catalog` dan o'qiydi, ya'ni reyestrga qo'shilmagan jadval ham qamraladi.
- **D-02 kafolati XULQ darajasida o'lchandi:** rasta `12` yaratildi → reyestrga tushdi → kod `99` ga o'zgartirildi → YANGI rastaga `12` berish `23505` bilan rad etildi → o'sha rasta o'z `12` sini QAYTARIB OLDI. Uch qadamning uchalasi ham kerak: ikkinchisisiz kafolat yo'q, uchinchisisiz "kodni umuman tahrirlab bo'lmaydi" degan boshqa qoida chiqib qolardi.
- **D-07 `sbozor_owner` ga qarshi ham ishlaydi.** O'tgan sanali tarifni `UPDATE` qilish ILOVA roli uchun ham, EGA roli uchun ham `23514` berdi — ya'ni kafolat RLS emas, trigger darajasida va xom SQL yo'lini ham qamraydi.
- **`financial_guards()` ni chaqirmaslik qarori isbotlandi:** bitta biznes-kunda `(market_id, category_id)` juftligiga UCHTA turli `valid_from` bilan tarif kiritildi. Helper chaqirilganda ikkinchisi `unique_violation` bilan rad etilardi va "sentabr + oktabr narxini bugun kiritish" imkonsiz bo'lardi.
- **`code_sort` tartibi nazorat holati bilan birga qulflandi:** `ORDER BY code_sort` → `2, 10, 100`; `ORDER BY code` → `10, 100, 2`. Ikkinchi assertion testning butun ma'nosi — usiz `code_sort` umuman ishlamasa ham test yashil bo'lishi mumkin edi.
- **Model va sxema AJRALMAGANI o'lchandi:** `compare_metadata()` mavjud 12 jadval uchun **0 element** qaytardi.
- **Migratsiyalar ikki yo'nalishda ham bajarildi:** `downgrade 0007` → `upgrade head` va `downgrade 0006` → `upgrade head`, ikkalasi ham exit 0.

## Task Commits

1. **Task 1: `0007_market_domain.py` — yadro jadvallar, RLS, audit va rasta-kod kafolati** — `ee2856e` (feat)
2. **Task 2: `0008_temporal.py` — tarif va toifa tarixi + o'zgarmaslik triggerlari** — `0eee6eb` (feat)
3. **Task 3: Alembic ko'rmaydigan narsalar uchun meta-test darvozasi** — `6453681` (test)

## Files Created/Modified

**Yaratildi**

- `migrations/versions/0007_market_domain.py` — beshta jadval + RLS/policy tsikli + ikkita audit triggeri + `trg_stall_code_claim` + uchta bozor funksiyasi. Fayl boshida "nega audit faqat ikki jadvalga ulanadi" izohi (aks holda keyingi ishlovchi uchinchisini qo'shib migratsiyani yiqitardi).
- `migrations/versions/0008_temporal.py` — ikkita voris-model jadvali + RLS/policy + ikkita audit triggeri + ikkita o'zgarmaslik triggeri. `financial_guards()` chaqirilmagani sababi jadval yonida to'liq yozilgan.
- `tests/tenancy/test_market_domain_meta.py` — 10 test. Fayl docstringi Alembic ko'rmaydigan uchta obyekt sinfini sanaydi va bu testlarning `test_autogenerate_is_empty` ni ALMASHTIRMASLIGINI, TO'LDIRISHINI yozadi.

**O'zgartirildi**

- `migrations/helpers.py` — `attach_immutability_trigger()` / `detach_immutability_trigger()` + `__all__`. Docstringda `attach_audit_trigger()` dan uchta ataylab qilingan farq (BEFORE vs AFTER, funksiya parametr, nom parametr) va Postgres trigger tartibi qoidasi.
- `migrations/entities/functions.py` — `MARKET_CORE_FUNCTIONS` / `MARKET_CORE_GRANT_SIGNATURES` (0007) va `MARKET_CALENDAR_FUNCTIONS` / `MARKET_CALENDAR_GRANT_SIGNATURES` (0010); `MARKET_DOMAIN_*` aggregatga aylandi.
- `tests/tenancy/test_meta.py` — `PENDING_AUDIT_TRIGGERS` dan to'rtta nom o'chirildi (`market_profile`, `stalls`, `stall_category_periods`, `tariffs`); `EXPECTED_DEFINER_FUNCTIONS` ga uchta bozor funksiyasi qo'shildi, `market_is_open` nega qo'shilmagani izoh bilan qayd etildi.

## Decisions Made

- **`0007` uchta funksiya yaratadi, beshta emas.** `market_is_open()` `LANGUAGE sql` va uning tanasi `CREATE FUNCTION` paytida validatsiya qilinadi (`check_function_bodies` standart `on`) — u `market_calendar_exceptions` ga murojaat qiladi va o'sha jadval `0010` da tug'iladi. Deviatsiya #1.
- **`test_autogenerate_is_empty` reyestrni vaqtincha bo'shatadi.** Deviatsiya #2 — o'lchangan zaruriyat.
- **`test_stall_code_claim_trigger_exists` `AFTER` ni talab qiladi.** Reja matni `tgtype` da "BEFORE bitlari" deb yozgan (u RESEARCH Pattern 8 dan kelgan), 02-04 esa `BEFORE` ni composite FK bilan ishlamasligini o'lchagan. Test 02-04 ning o'lchoviga qulflandi va assertion xabari sababni o'zi aytadi. Deviatsiya #3.
- **`PENDING_AUDIT_TRIGGERS` ikki bosqichda qisqardi.** Task 1 `market_profile`/`stalls` ni, Task 2 `stall_category_periods`/`tariffs` ni o'chirdi. Bitta qadamda qilinganda Task 1 commit'i o'z-o'zicha qizil bo'lardi (jadvallari hali yo'q trigger talab qilinardi), ya'ni har bir commit'ning yashil bo'lishi kafolati buzilardi.
- **`market_profile.tin` CHECK ifodasi migratsiyada LITERAL.** Model uni konstantaga chiqarmagan (`STALL_STATUS_CHECK` / `OPEN_WEEKDAYS_CHECK` dan farqli). Ifoda ikkala joyda bayt-ba-bayt bir xil yozildi; Alembic CHECK konstraytlarini baribir avtogeneratsiya qilmaydi, ya'ni drift faqat code review'da ko'rinadi — shuning uchun migratsiyada shu haqda izoh turadi.
- **`stall_code_registry` ga audit triggeri ULANMAYDI va bu fayl boshida ⚠ bilan yozilgan.** Uning PK'si `(market_id, code)`, `fn_audit_row()` esa `row_id` ni `uuid` ga keltiradi — trigger qo'shilsa HAR bir rasta yaratish yiqilardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `MARKET_DOMAIN_FUNCTIONS` ustidan tsikl qilish `0007` ni yiqitardi**

- **Found during:** Task 1
- **Issue:** 02-04 `MARKET_DOMAIN_FUNCTIONS` ni "`0007_market_domain` migratsiyasi yaratadigan to'plam" deb hujjatlashtirgan (beshta funksiya), 02-05 rejasining `<interfaces>` bo'limi esa `0007` faqat uchtasini yaratishini aytadi va sababini ham beradi ("`market_delete_draft` va `market_is_open` `0010` da, chunki ular hali mavjud bo'lmagan jadvallarga tegadi"). Ikkala hujjat bir-biriga zid. Texnik haqiqat rejaning tomonida va u qat'iy: `market_is_open()` `LANGUAGE sql`, ya'ni Postgres uning tanasini `CREATE FUNCTION` paytida parse qiladi va `relation "public.market_calendar_exceptions" does not exist` bilan yiqilardi. Ro'yxatni bo'lmasdan `0007` yozish MUMKIN EMAS edi.
- **Fix:** 02-04 ning O'Z naqshi (`AUDIT_TRIGGER_FUNCTIONS` / `MARKET_DOMAIN_TRIGGER_FUNCTIONS` / `ALL_TRIGGER_FUNCTIONS`) funksiyalarga ham qo'llandi: `MARKET_CORE_FUNCTIONS` + `MARKET_CORE_GRANT_SIGNATURES` (0007), `MARKET_CALENDAR_FUNCTIONS` + `MARKET_CALENDAR_GRANT_SIGNATURES` (0010), `MARKET_DOMAIN_*` esa aggregat bo'lib qoldi. Aggregatning MAZMUNI va TARTIBI o'zgarmadi — `ALL_ENTITIES` (autogenerate reyestri) aynan avvalgi beshta funksiyani ko'radi.
- **Files modified:** `migrations/entities/functions.py`
- **Verification:** `alembic upgrade head` nol holatdan yashil; `downgrade 0006 && upgrade head` ham
- **Committed in:** `ee2856e`

**2. [Rule 3 - Blocking] To'liq `compare_metadata()` yarim fazada YIQILADI (kod xatosi emas, `alembic_utils` mexanikasi)**

- **Found during:** Task 3
- **Issue:** Reja `test_autogenerate_is_empty` ni "`compare_metadata(connection, Base.metadata)` chaqirib natija bo'sh ekanini tasdiqlaydi" deb belgilaydi. Bu 02-05 dan keyingi holatda ISHLAMAYDI va sabab diff emas, ISTISNO: `alembic_utils` ning "schema" komparatori har bir ro'yxatdagi entity'ni solishtirish uchun HAQIQATAN yaratib ko'radi (`simulate_entity`). `ALL_ENTITIES` da `vendors` / `stall_assignments` / `market_calendar_exceptions` policy'lari bor, o'sha jadvallar esa `0009`/`0010` da tug'iladi. O'lchangan xato: `ProgrammingError: (psycopg.errors.UndefinedTable) relation "public.vendors" does not exist [SQL: CREATE POLICY tenant_isolation on public.vendors ...]`. Ya'ni test qanday yozilishidan qat'i nazar 02-06 gacha QIZIL bo'lardi — bu esa 02-01 deviatsiya #1 da hujjatlashtirilgan "buzilgan darvoza — darvoza emas" holatining aynan o'zi.
- **Fix:** Test ikki qismga bo'lindi va IKKALASI ham haqiqiy da'vo qiladi:
  1. **Reyestr qulfi (bugun ishlaydi):** `Base.metadata` da e'lon qilingan, lekin bazada yo'q jadvallar to'plami AYNAN `PENDING_DOMAIN_TABLES` ga teng bo'lishi shart, va bazada modelda bo'lmagan jadval bo'lmasligi kerak. Bu ikki tomonlama — 02-06 jadvalni yaratganda test qizaradi va muallifni ro'yxatni bo'shatishga majbur qiladi.
  2. **Haqiqiy diff (bugun ham ishlaydi):** `alembic_utils` reyestri `ReplaceableEntityRegistry.clear()` ommaviy API'si bilan VAQTINCHA bo'shatiladi, `include_object` esa hali tug'ilmagan jadvallarni chiqarib tashlaydi. Natija — mavjud 12 jadval uchun **0 element** (o'lchandi). `finally` da reyestr `env.py` dagi AYNAN o'sha `register_entities(ALL_ENTITIES, entity_types=[PGPolicy, PGFunction])` bilan tiklanadi. Komparator modul import paytida bir marta ro'yxatdan o'tadi (`@comparators.dispatch_for("schema")` dekoratori modul darajasida), ya'ni qayta `register_entities()` chaqirish dublikat komparator YARATMAYDI — bu manba o'qib tasdiqlandi.
- **Nega policy/funksiya qatlami qamrovsiz qolmaydi:** u `test_meta.py` da `pg_policies`/`pg_proc` dan o'qiladi (`test_app_role_policies_all_reference_tenant_guc`, `test_owner_bootstrap_policies_are_owner_only`, `test_security_definer_functions_pin_search_path`) va bu rejada qo'shilgan `test_market_write_functions_are_security_definer` da. Bo'shliq yo'q, faqat manba boshqa.
- **Files modified:** `tests/tenancy/test_market_domain_meta.py`
- **Verification:** `diff count = 0` o'lchandi; reyestr tiklanganidan keyin butun `pytest -q` (460 test) yashil — ya'ni bo'shatish keyingi testlarga sizib chiqmaydi
- **Committed in:** `6453681`

**3. [Rule 1 - Bug] Reja testi `tgtype` da BEFORE bitini kutgan, trigger esa AFTER**

- **Found during:** Task 3
- **Issue:** Reja `test_stall_code_claim_trigger_exists` ni "`tgtype` da BEFORE va INSERT/UPDATE bitlari" deb yozadi. Bu matn RESEARCH Pattern 8 dan ko'chgan, 02-04 esa o'sha naqshni O'LCHOV bilan bekor qilgan: `BEFORE INSERT` paytida `stalls` qatori hali yozilmagan va `fk_stall_code_registry_market_id_stall_id_stalls` darhol buziladi. Rejadagi shaklda yozilgan test to'g'ri migratsiyani QIZIL qilardi va keyingi ishlovchini triggerni `BEFORE` ga qaytarishga — ya'ni ishlaydigan kodni buzishga — undardi.
- **Fix:** Assertion teskarisiga o'zgartirildi (`not tgtype & TRIGGER_BEFORE`) va xabar sababni o'zi aytadi: "trigger `BEFORE` ga qaytarilgan — ... 02-04 da o'lchangan". Qolgan uchta bit (ROW / INSERT / UPDATE) reja aytganidek. Qo'shimcha `UPDATE OF code` tekshiruvi `pg_get_triggerdef()` dan.
- **Files modified:** `tests/tenancy/test_market_domain_meta.py`
- **Verification:** Sabotaj bilan — `CREATE TRIGGER` migratsiyadan olib tashlanganda `test_stall_code_claim_trigger_exists` VA `test_stall_code_registry_is_populated_by_trigger` ikkalasi ham yiqildi; migratsiya bit-ba-bit tiklandi (`git diff` bo'sh)
- **Committed in:** `6453681`

**4. [Rule 2 - Missing Critical] Trigger MAVJUDLIGI testi uning ISHLASHINI isbotlamaydi**

- **Found during:** Task 3
- **Issue:** Rejadagi ro'yxatda `trg_stall_code_claim` uchun faqat `pg_trigger` dan mavjudlik tekshiruvi bor. Trigger o'z joyida turib, funksiya tanasi buzilgan (masalan `ON CONFLICT DO NOTHING` dan keyingi `IF NOT EXISTS` bloki olib tashlangan) holat bu testdan BEMALOL o'tardi — ya'ni D-02 kafolati yo'qolgan bo'lardi va CI hech narsa demasdi. Bu aynan `test_financial_tables_have_guards` va `test_audited_tables_have_trigger` yopadigan "reyestr bor, xulq yo'q" sinfidagi bo'shliq.
- **Fix:** `test_stall_code_registry_is_populated_by_trigger` qo'shildi — uch qadamli xulq testi (yaratish → reyestr qatori; kodni chetlash → `23505`; o'z kodini qaytarib olish → ruxsat). `probe_market` fixture'i bozorni `market_create()` ORQALI yaratadi, `INSERT INTO markets` bilan emas — aks holda fixture o'zi `test_app_role_cannot_insert_markets` da'vosini buzardi.
- **Files modified:** `tests/tenancy/test_market_domain_meta.py`
- **Verification:** Sabotaj tekshiruvida bu test ham yiqildi (yuqoridagi #3 bilan birga)
- **Committed in:** `6453681`

**5. [Rule 2 - Missing Critical] O'zgarmaslik triggeri EGAGA qarshi ishlashi o'lchanmagan edi**

- **Found during:** Task 2
- **Issue:** Rejaning qabul mezoni "`sbozor_owner` bilan ham o'tgan sanali tarif qatorini `UPDATE` qilish `23514` bilan rad etiladi" deydi, lekin bu D-07 ning BUTUN ma'nosi: agar qo'riqchi faqat `sbozor_app` uchun ishlasa, u RLS'ning takrori bo'lib qolardi va migratsiya/`psql` yo'li ochiq qolardi.
- **Fix:** Probe ikkala rol bilan AYNI amalni bajardi va ikkalasida ham `23514` oldi. Bozor ataylab `market_activate()` bilan FAOL qilindi — qoralama istisnosi (02-04 deviatsiya #3) aks holda qo'riqchini o'chirib qo'yardi va test hech narsani isbotlamasdi.
- **Files modified:** — (o'lchov; kod o'zgarmadi)
- **Verification:** `app UPDATE past tariff: 23514` / `owner UPDATE past tariff: 23514`
- **Committed in:** `0eee6eb` (o'lchov natijasi; probe fayli commit'dan oldin o'chirildi)

---

**Total deviations:** 5 auto-fixed (2 blocking, 1 bug, 2 missing-critical). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaytmasi yo'q — birorta yangi jadval, funksiya yoki paket rejadan tashqari qo'shilmadi. #1 va #2 rejaning bajarilishini TEXNIK jihatdan imkonsiz qiladigan to'siqlar edi (ikkalasi ham `alembic`/`postgres` mexanikasi, kod xatosi emas). #3 rejaning O'Z hujjati (02-04 SUMMARY) bilan ziddiyatini 02-04 foydasiga hal qiladi. #4 va #5 darvozalarning yolg'on-yashil bo'lishini yopadi.

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` (compose `migrate` profili) ishlamaydi. Ekvivalent qamrov: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 460 testning har birida. `downgrade`/`upgrade` tsikli ham shu yo'l bilan (vaqtinchalik probe orqali) ikki marta o'lchandi.
- **Reja `stall_category_periods` uchun tarif bilan bir xil FK nomlash konvensiyasini nazarda tutadi**, amalda esa toifa FK'sining nomida `market_id` segmenti YO'Q (02-04 deviatsiya #6 — 63 baytlik chegara). Migratsiya modelning nomini oldi va sababni yoniga yozdi; `compare_metadata()` diff'i 0 ekani bu nomning to'g'riligini isbotlaydi.
- **`ruff format` uch marta uzun konstruksiyani qayta formatladi** (bitta tuple, ikkita assert). O'zgarish faqat qator uzunligiga tegishli.
- **`mypy --strict` `alembic_utils` ning `registry.clear()` ini `no-untyped-call` deb belgiladi.** Ignore `migrations/helpers.py::create_entity()` naqshida — bitta o'ram funksiyada, sababi bilan.

## Known Stubs

Yo'q. Bu rejadagi barcha DDL bajarildi, barcha testlar haqiqiy da'vo qiladi va birorta test `skip`/`xfail` bilan yozilmadi.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `vendors` / `stall_assignments` / `market_calendar_exceptions` jadvallari | 02-06 (`0009`, `0010`) | `PENDING_DOMAIN_TABLES` + `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulflaydi |
| `market_delete_draft()` / `market_is_open()` funksiyalari | 02-06 (`0010`) | `MARKET_CALENDAR_FUNCTIONS` ro'yxati tayyor; `EXPECTED_DEFINER_FUNCTIONS` ga `market_delete_draft` o'sha yerda qo'shiladi |
| `ExcludeConstraint` darvozasi | 02-06 | `test_market_domain_meta.py` docstringi uni nomma-nom kutayotganini yozadi |
| To'liq (entity qatlami bilan) autogenerate solishtiruvi | 02-06 | `test_autogenerate_is_empty` ro'yxat bo'shaganda AVTOMATIK kengayadi |

## Threat Flags

Yangi xavfsizlik yuzasi yo'q — yangi endpoint, fayl kirishi yoki tashqi bog'liqlik qo'shilmadi. Rejaning `<threat_model>` idagi dispozitsiyalar:

| Threat ID | Holat |
|-----------|-------|
| T-02-29 | mitigate — yettita jadvalning har birida `enable_tenant_rls()` + `tenant_policy()`; `relrowsecurity`/`relforcerowsecurity` ikkalasi ham `t` (o'lchandi) |
| T-02-30 | mitigate — `fk_stalls_market_id_zone_id_zones` composite FK; `compare_metadata()` diff 0 uning bazada aynan modeldagidek turganini isbotlaydi |
| T-02-31 | mitigate — `trg_tariff_past_immutable` `BEFORE UPDATE OR DELETE`; ILOVA va EGA rollari uchun ham `23514` (ikkalasi o'lchandi) |
| T-02-32 | mitigate — `stall_code_registry` + `trg_stall_code_claim`; xulq testi nazorat holati (o'z kodini qaytarib olish) bilan birga |
| T-02-33 | mitigate — `attach_audit_trigger("stalls")` va `("market_profile")`; `test_audited_tables_have_trigger` reyestr bilan solishtiradi va `PENDING_AUDIT_TRIGGERS` dan ikki nom o'chirildi |
| T-02-34 | mitigate — `test_market_domain_meta.py` `pg_trigger`/`pg_proc` dan tekshiradi; sabotaj bilan darvoza haqiqatan yopilishi isbotlandi |
| T-02-35 | mitigate — `test_app_role_cannot_insert_markets` (`42501`) + `test_market_write_functions_are_security_definer` (`prosecdef`, `search_path`, `PUBLIC` dan `REVOKE`) |
| T-02-36 | mitigate — `code_sort` generated STORED + `ix_stalls_market_id_code_sort`; ikki assertionli test (`code_sort` to'g'ri, `code` boshqa tartib) |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `alembic upgrade head` | ✅ nol holatdan `0001` → `0008` (`migrated` fixture'i orqali) |
| 2 | `alembic downgrade 0007 && upgrade head` | ✅ exit 0 |
| 2b | `alembic downgrade 0006 && upgrade head` | ✅ exit 0 |
| 3 | `npm run test:tenancy` | ✅ exit 0 (111 test — 02-01 dagi 101 + 10 yangi) |
| 4 | `pytest tests/tenancy/test_market_domain_meta.py -q` | ✅ 10 test |
| 5 | `npm run test` (`pytest -q`) | ✅ **460 passed** (02-04 dagi 450 + 10 yangi) |
| 6 | `npm run lint` (ruff + format + mypy strict) | ✅ exit 0 (95 fayl, 94 manba) |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| Beshta jadvalda `relrowsecurity` va `relforcerowsecurity` | ✅ `t`/`t` (5/5) |
| `stalls` da `trg_stall_code_claim` + audit triggeri | ✅ ikkalasi ham |
| `INSERT INTO stalls ... '12'` → reyestrda `(A,'12')` | ✅ |
| Chetlangan `'12'` ni YANGI rastaga berish | ✅ `23505` |
| O'z eski kodini qaytarib olish | ✅ ruxsat |
| `ORDER BY code_sort` | ✅ `2, 10, 100` (`ORDER BY code` → `10, 100, 2`) |
| `has_function_privilege('public', 'market_create(...)')` | ✅ `false` (`sbozor_app` uchun `true`) |
| `sbozor_app` bilan `INSERT INTO markets` | ✅ `42501 permission denied` |
| `down_revision = "0006"` | ✅ |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `tariffs` da `trg_tariff_past_immutable` | ✅ (+ `trg_audit_tariffs`) |
| `stall_category_periods` da `trg_category_period_past_immutable` | ✅ (+ audit) |
| O'tgan tarif `UPDATE` — ilova roli | ✅ `23514` |
| O'tgan tarif `UPDATE` — `sbozor_owner` | ✅ `23514` |
| Kelajakdagi tarif `UPDATE` + `DELETE` | ✅ ikkalasi ham o'tdi |
| O'tgan toifa davri `DELETE` | ✅ `23514` |
| `tariffs` da `valid_to` ustuni | ✅ YO'Q |
| Ikkala jadvalda `updated_at` | ✅ YO'Q |
| Bir `(market, category)` ga ikkita turli kelajak sanasi | ✅ ishladi (bir kunda 3 ta qator) |
| `business_date` STORED generated va `valid_from` dan ALOHIDA | ✅ `s`; `2026-07-31` vs `valid_from = 2026-07-21` |
| `0008_temporal.py` da `financial_guards(` chaqiruvi | ✅ YO'Q |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `test_market_domain_meta.py` test soni | ✅ 10 (talab: ≥8) |
| `test_autogenerate_is_empty` | ✅ `compare_metadata()` → 0 element |
| `test_stalls_human_numeric_order` ikkala assertion | ✅ ikkalasi ham |
| `test_app_role_cannot_insert_markets` `permission denied` kutadi | ✅ |
| `EXPECTED_DEFINER_FUNCTIONS` da uchta bozor funksiyasi | ✅ |
| Triggerni olib tashlash testni yiqitadimi | ✅ IKKITA test yiqildi, migratsiya bit-ba-bit tiklandi |
| `npm run test:tenancy` / `npm run lint` | ✅ ikkalasi ham exit 0 |

## User Setup Required

Yo'q — tashqi servis sozlamasi kerak emas.

**DEPLOY ESLATMASI (o'zgarmadi, 02-01 dan meros):** `ops/db/init/00-extensions.sql` faqat BO'SH data katalogida ishlaydi. Bu rejadagi ikkala migratsiya `btree_gist` ni TALAB QILMAYDI (u `0009` da kerak bo'ladi), ya'ni `0007`/`0008` mavjud bazada ham bemalol bajariladi.

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-01, MARKET-02, MARKET-03]` deb yozgan, lekin bu reja **sxemani** beradi, foydalanuvchi ko'radigan qobiliyatni emas: bozor ustasi (MARKET-01), rasta reestri UI/API'si (MARKET-02) va tarif boshqaruvi (MARKET-03) 02-07…02-17 rejalarida quriladi. Fazadagi hamma 17 reja ayni shu ID'larni deklaratsiya qiladi (02-01 SUMMARY'dagi bilan bir xil sabab) — ularni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi.

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt. Uni parallel rejada o'zgartirish to'lqin birlashtirilganda konfliktga olib kelardi.

## Next Phase Readiness

**02-06 (`0009_vendors` / `0010_calendar`) uchun aniq topshiriq:**

- `down_revision = "0008"` dan boshlanadi; `0009` `require_extension("btree_gist")` bilan ochiladi.
- `VENDOR_TENANT_TABLES` / `CALENDAR_TENANT_TABLES` tuple'lari tayyor; RLS tsikli `0007`/`0008` dagi bilan aynan bir xil (`enable_tenant_rls` → `tenant_policy` → `owner_bootstrap_policy`).
- Funksiyalarni `MARKET_CALENDAR_FUNCTIONS` va `MARKET_CALENDAR_GRANT_SIGNATURES` dan oling (`MARKET_DOMAIN_*` aggregatidan EMAS — u faqat autogenerate reyestri).
- `attach_audit_trigger()` uchtasiga ham (`vendors`, `stall_assignments`, `market_calendar_exceptions`), so'ng nomlarni `tests/tenancy/test_meta.py::PENDING_AUDIT_TRIGGERS` dan **O'CHIRING** — ro'yxat ikki tomonlama va o'chirilmasa test qizarib sababni o'zi aytadi.
- **`tests/tenancy/test_market_domain_meta.py::PENDING_DOMAIN_TABLES` ni ham BO'SHATING.** Uchala nom o'chgach `test_autogenerate_is_empty` avtomatik ravishda BUTUN sxemani qamrab oladi va `include_object` filtri hech nimani chiqarib tashlamaydi.
- ⚠ `test_autogenerate_is_empty` ichidagi `_clear_entity_registry()` bloki `0010` dan keyin ham KERAK BO'LMASLIGI mumkin (barcha jadvallar mavjud bo'lgach `alembic_utils` komparatori yiqilmaydi). O'sha paytda uni olib tashlash va to'g'ridan-to'g'ri `compare_metadata()` chaqirish — bir satrlik soddalashtirish. **Lekin avval o'lchang**: komparator entity'ni haqiqatan yaratib ko'radi, ya'ni `sbozor_owner` huquqi va `search_path` sozlamalari bilan aloqasi bor.
- `EXPECTED_DEFINER_FUNCTIONS` ga `market_delete_draft` qo'shiladi; `market_is_open` QO'SHILMAYDI (izoh `test_meta.py` da allaqachon turibdi).
- `market_is_open()` `LANGUAGE sql` — uni `market_calendar_exceptions` YARATILGANIDAN KEYIN yarating, aks holda `CREATE FUNCTION` parse bosqichida yiqiladi (bu rejada o'lchangan).

**02-07 va keyingi API rejalari uchun:**

- Bozor yaratishning YAGONA yo'li — `market_create(text, text, date, smallint[], text, text, text, text, text)`. `INSERT INTO markets` `sbozor_app` uchun `42501` beradi va bu test bilan qulflangan.
- Rasta ro'yxatining tartibi — `ORDER BY code_sort` (kursor `(code_sort, id)`), `ORDER BY code` EMAS.
- Chetlangan rasta kodi `23505` beradi, ya'ni ilova qatlami uni oddiy "kod band" holati bilan BIR XIL yo'lda `409` ga aylantiradi (ikkita alohida xato kodini ushlash shart emas).
- O'tgan sanali tarif/toifa davrini tahrirlash `23514` beradi → `403`. Kelajakdagi qator ochiq.
- Bir `(market_id, category_id)` ga bir kunda bir NECHTA kelajak tarifi kiritish mumkin — UI buni bloklashi SHART EMAS.

## Self-Check: PASSED

- Da'vo qilingan 3 yangi fayl diskda mavjud: `migrations/versions/0007_market_domain.py`, `migrations/versions/0008_temporal.py`, `tests/tenancy/test_market_domain_meta.py`
- Da'vo qilingan 3 o'zgartirilgan fayl `git diff --stat f69274f..HEAD` da ko'rinadi: `migrations/helpers.py`, `migrations/entities/functions.py`, `tests/tenancy/test_meta.py`
- Uchala vazifa commit'i git tarixida mavjud: `ee2856e`, `0eee6eb`, `6453681`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D` uchalasida ham bo'sh)
- To'rtta vaqtinchalik probe fayli commit'dan OLDIN o'chirildi; ishchi daraxtda kuzatilmagan fayl qolmadi
- `STATE.md` va `ROADMAP.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-07-31*
