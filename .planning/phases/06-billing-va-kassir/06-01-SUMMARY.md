---
phase: 06-billing-va-kassir
plan: 01
subsystem: billing
tags: [postgres, read-committed, idempotency, generated-columns, pure-functions, fifo, pytest]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`stall_slot_occupancy` materializatsiyasi, `OccupancyVerdict`/`ResolutionSource` enumlari, `sbozor_core/occupancy.py` ning ikki daraja chegarasi"
  - phase: 04-snapshot-pipeline
    provides: "`BILLABLE_ANCHOR_SUPPORTED` naqshi — o'lchov SUMMARY'da qolmaydi, KODDA qulflanadi"
  - phase: 02-bozor-domeni
    provides: "`migrations/helpers.py::BUSINESS_DATE_EXPR`, `financial_guard_statements()`, `money.py::assert_safe_soum()`"
provides:
  - "A1 o'lchovi: `IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True` — ikki bayonotli get-or-create READ COMMITTED ostida parallel yozuvda ishlaydi (D-21/G-12)"
  - "A2 o'lchovi: `GENERATED_FROM_COLUMN_SUPPORTED = True` — lekin `0020` BARIBIR Variant A ni ishlatadi, sabab markerda"
  - "`sbozor_core/billing.py` — besh sof funksiya: `billable_from_slots()`, `variance()`, `total_due_soum()`, `payment_quote_set()`, `allocate_charge_credit()`"
  - "`ALLOCATION_RULE = FIFO_OLDEST_SERVICE_DATE_FIRST` — D-24 ning nomlangan, saqlanmaydigan taqsimlash qoidasi"
  - "Uch jadval testi (132 ta yangi test) — D-04/D-05/C-6, D-26 va D-24 LITERAL jadvallar bilan qulflangan"
affects: [06-02, 06-03, 06-06, 06-09, 06-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave 0 zondi -> KOD MARKERI: o'lchov natijasi `migrations/entities/__init__.py` da `Final[bool]` bo'lib yashaydi va test uni O'QIB solishtiradi (qo'lda yozib qo'yish imkonsiz)"
    - "Determinlashtirilgan konkurentlik zondi: interleaving `pg_stat_activity.wait_event_type` bo'yicha kutiladi, `sleep()` bilan taxmin QILINMAYDI"
    - "Jadval testi KUN KESIMI bo'yicha: jamlar jadvali yolg'iz o'zi tartib qoidasini o'lchamaydi"
    - "Mahsulot kodida invariant `raise AssertionError` bilan (`assert` bayonoti `python -O` da yo'qoladi va ruff S101 uni taqiqlaydi)"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/billing.py
    - tests/fixtures/idempotency_probe.py
    - tests/tenancy/test_idempotency_concurrency.py
    - tests/tenancy/test_generated_from_column_probe.py
    - tests/unit/test_billable_from_slots.py
    - tests/unit/test_variance.py
    - tests/unit/test_payment_credit_rules.py
  modified:
    - migrations/entities/__init__.py

key-decisions:
  - "06-01: A1 zondi `app_engine` ni ISHLATA OLMAYDI — `pool_size=1` ikki korutinani ketma-ket yugurtirardi va poyga hech qachon yuz bermasdi; zond o'z engine'ini quradi"
  - "06-01: CTE + `UNION ALL` bir bayonotli get-or-create shakli O'LCHANDI va RAD ETILDI — parallel yozilgan qatorni TOPMAYDI (bayonot snapshoti), ya'ni ikkinchi ALOHIDA `SELECT` majburiy"
  - "06-01: `GENERATED_FROM_COLUMN_SUPPORTED = True` bo'lsa ham `0020` Variant A da qoladi — Variant B `attgenerated` talabini shakl uchun bajarib, «qator qachon yozilgan» audit faktini butunlay yo'qotardi (D-02)"
  - "06-01: `stall_repo.sqlstate_of()` A2 zondida ATAYIN ishlatilmadi — u `exc.orig` o'ramini kutadi, xom `psycopg.Error` da u yo'q va yordamchi JIMGINA `None` qaytarib o'lchovni soxtalashtirardi"
  - "06-01: mahsulot kodidagi invariantlar `assert` bayonoti bilan EMAS, `raise AssertionError` bilan — `python -O` da yo'qolmaydi va ruff `S101` ni ham qanoatlantiradi"
  - "06-01: `(verdict = no_coverage) = (resolution_source = no_coverage)` juftlik invarianti `billable_from_slots()` da TAKRORLANMAYDI — u sxemaning `CHECK` ida va ikkinchi nusxa undan ajralib ketardi"
  - "06-01: LIFO sabotaji o'lchandi — jamlar jadvali (`EXPECTED_BY_TOTALS`, 23 test) UMUMAN QIZARMADI; D-24 ni faqat KUN KESIMI qatorlari ushlaydi (05-15 S-D darsining tasdig'i)"

patterns-established:
  - "Zond marker juftligi: `<NOM>_SUPPORTED: Final[bool]` + `<NOM>_MEASURED_AT: Final[str]`, docstringda o'lchov sanasi, o'lchaydigan test va `False` shoxining oqibati"
  - "Ikki literal jadval bir-birini tekshiradi, kesishma TO'PLAM TENGLIGI bilan qulflanadi (D-31)"
  - "Har jadval uchun `test_the_*_table_covers_every_case()` — `parametrize` jimgina bo'shab qolmasligi uchun"

requirements-completed: [BILL-01, BILL-03, CASH-03, CASH-04]

# Metrics
duration: 68min
completed: 2026-08-10
---

# Phase 6 Plan 01: Zondlar va sof funksiyalar Summary

**Ikki Wave 0 zondi HAQIQIY `postgres:18.4` da o'lchandi va natija kod markerlarida qulflandi; `sbozor_core/billing.py` esa D-04 predikatini (C-6 tuzatilgan shaklda), ikki tomonlama `variance()` ni va D-24 ning `FIFO_OLDEST_SERVICE_DATE_FIRST` taqsimlash qoidasini 132 ta jadval testi bilan migratsiya va marshrutlardan OLDIN qulfladi.**

## Performance

- **Duration:** 68 min
- **Started:** 2026-08-10T09:10:00Z
- **Completed:** 2026-08-10T10:18:00Z
- **Tasks:** 3
- **Files modified:** 8 (7 yangi, 1 kengaytirilgan)

## Accomplishments

- **A1 javobi YOZILDI:** parallel ikki sessiya bir xil `idempotency_key` bilan yozganda natija BITTA qator va IKKALA chaqiruv ham AYNAN BIR XIL `id` oladi. `IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True` — 06-09 endi taxmin qilmaydi, o'qiydi.
- **Bonus o'lchov:** bir bayonotli CTE + `UNION ALL` shakli parallel yozilgan qatorni **TOPMAYDI** — «ikki bayonot ortiqcha emasmi?» savoli o'lchov bilan yopildi.
- **A2 javobi YOZILDI:** `GENERATED ALWAYS AS (service_date) STORED` PG 18 da **ishlaydi** (`attgenerated = 's'`, qiymat ko'chiriladi), **lekin `0020` baribir Variant A da qoladi** va sabab markerda so'z bilan yozilgan.
- **D-04 predikati C-6 tuzatilgan shaklda:** `human_confirmed_occupied` AYNI slotda `occupied` VA `human` bo'lishini talab qiladi. `occupancy_repo.py:369` ning `bool_or(resolution_source = 'human')` ustuni sabotaj sifatida qo'llanildi va nomlangan test **qizardi**.
- **D-24 ning MEXANIZMI qulflandi:** `ALLOCATION_RULE = "FIFO_OLDEST_SERVICE_DATE_FIRST"` — saqlanmaydigan hosila ko'rinish; `payment_allocations` jadvali **yo'q** va taqiq kodda yozilgan.
- **Ikki invariant funksiyaning O'ZIDA:** kredit yo'qolmaydi va `unpaid_soum` `vendor_outstanding()` (BILL-03) bilan **bir xil son** beradi.

## Task Commits

1. **Task 1: A1 zondi — parallel get-or-create oynasi** — `c82b4e1` (test)
2. **Task 2: A2 zondi — `GENERATED ALWAYS AS (<oddiy ustun>) STORED`** — `46a53d9` (test)
3. **Task 3: `sbozor_core/billing.py` + uch jadval testi** — `c16bd7d` (feat)

## Files Created/Modified

- `packages/sbozor-core/sbozor_core/billing.py` (**yangi**, 586 qator) — besh sof funksiya, `ALLOCATION_RULE`, to'rt `dataclass(frozen=True, slots=True)`
- `tests/fixtures/idempotency_probe.py` (**yangi**) — `probe_idempotent_writes` xom DDL + `sbozor_app` ga `GRANT` + DML SQL konstantalari
- `tests/tenancy/test_idempotency_concurrency.py` (**yangi**, 3 test) — A1 ning uch o'lchovi
- `tests/tenancy/test_generated_from_column_probe.py` (**yangi**, 2 test) — A2 + nazorat o'lchovi
- `tests/unit/test_billable_from_slots.py` (**yangi**, 44 test) — `SLOT_COMBINATION_TABLE` (22) + `EXPECTED_BY_SLOT_SET` (14)
- `tests/unit/test_variance.py` (**yangi**, 18 test) — `VARIANCE_TABLE` (7), ikki yo'nalish
- `tests/unit/test_payment_credit_rules.py` (**yangi**, 65 test) — `FIFO_ALLOCATION_TABLE` (11) + `EXPECTED_BY_TOTALS` + `QUOTE_SET_TABLE` (9)
- `migrations/entities/__init__.py` (**kengaytirildi**) — to'rt marker konstanta + `__all__` + `Final` importi

## O'lchov natijalari (keyingi rejalar SHU SATRLARNI o'qiydi)

```
IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True     (2026-08-10 · PostgreSQL 18.4)
GENERATED_FROM_COLUMN_SUPPORTED    = True     (2026-08-10 · PostgreSQL 18.4)
```

**A1 — nima o'lchandi:**
- `ON CONFLICT DO NOTHING ... RETURNING` konfliktda `None` qaytaradi (Gotcha 5 ning **xulqiy** isboti — repoda bugungacha hech qayerda yozilmagan edi).
- Ikki mustaqil `AsyncSession` `asyncio.Barrier` bilan bir vaqtda yozadi: jadvalda **1 qator**, ikkala korutina ham **bir xil `id`**, **istisno yo'q**, aynan **bitta** korutina `inserted`.
- `SHOW transaction_isolation` → `read committed` (ochiq assert; `REPEATABLE READ` ga o'tish shu yerda ushlanadi).
- ⛔ **CTE + `UNION ALL` shakli RAD ETILDI:** determinlashtirilgan interleavingda (holder qulfni ushlab turadi → challenger `pg_stat_activity.wait_event_type = 'Lock'` bo'ladi → holder commit qiladi) CTE **bo'sh** javob berdi, keyingi **alohida** bayonot esa qatorni **ko'rdi**. Ya'ni 06-09 da ikkinchi `SELECT` **majburiy**.

**06-09 uchun kirish sharti:** marker `True` bo'lgani uchun `payment_repo` **ikki bayonotli** get-or-create yo'lidan yuradi. `IntegrityError` + `SAVEPOINT` zaxira varianti **kerak emas** (shox marker docstringida saqlanadi).

**A2 — nima o'lchandi:** DDL qabul qilindi, `business_date` qiymati `service_date` dan **ko'chirildi**, `attgenerated = 's'`. Nazorat o'lchovi (`BUSINESS_DATE_EXPR` dan hosila) ham o'tdi — ya'ni birinchi natija PG imkoniyati haqida ma'no tashiydi.

**`0020` uchun tanlov (marker docstringida so'z bilan):** **Variant A** — `service_date date NOT NULL` domen ustuni + `business_date` `created_at` dan hosila. Variant B `attgenerated` talabini **shakl uchun** bajarardi, lekin backfill bilan normal `billing_close` ni **farqlab bo'lmas** qilardi (ikkalasida ham `business_date == service_date`) va D-02 ning nizo modeli aynan shu audit faktiga tayanadi.

## Sabotaj (D-30) — IKKI SABOTAJ, IKKALA NATIJA HAM YOZILDI

### S-1 (rejada talab qilingan): `allocate_charge_credit` ning `sorted()` kaliti LIFO ga

**Qizardi (kutilgandek):**
- `test_allocation_rows_match_the_literal_table[bir to'lov N kunga]` — 1-holat ✓
- `test_allocation_rows_match_the_literal_table[qisman — N kun ustida]` — 2-holat ✓
- `test_allocation_rows_match_the_literal_table[storno netlashadi]`
- `test_allocation_rows_match_the_literal_table[bir kunda ikki rasta — tenglik uzilishi]`
- `test_one_payment_settles_the_oldest_days_first` — `['3b']` ≠ `['12a']`
- `test_a_partial_payment_names_the_day_it_stopped_at`
- `test_the_tie_break_is_deterministic_and_input_order_does_not_matter`

⛔ **YASHIL QOLGAN QISM VA U ENG QIMMAT TOPILMA:** `-k "totals or invariants"` ostidagi **23 ta test butunlay yashil qoldi**. Ya'ni `EXPECTED_BY_TOTALS` (Σ paid / advance / unpaid) va ikkala invariant **LIFO da ham AYNAN BIR XIL son beradi** — tartib jamlarni umuman o'zgartirmaydi.

**Xulosa:** agar bu reja faqat jamlar jadvalini yozganida, D-24 **umuman o'lchanmagan** bo'lardi va sabotaj sistemaga yetib borgani holda hech nima qizarmasdi — bu `05-15` ning S-D darsining aynan takrori. Tuzatish testda emas, **jadvalning O'LCHAMIDA** bo'ldi: `FIFO_ALLOCATION_TABLE` kutilgan natijani **kun kesimida, qator-qator** yozadi (`(kun, rasta, to'langan, yopildimi)`), jam sifatida emas. Bu majburiyat fayl docstringida yozib qo'yilgan.

### S-2 (qo'shimcha, C-6 uchun): `human_confirmed_occupied` ni `verdict` dan ajratish

`occupancy_repo.py:369` ning `bool_or(resolution_source = 'human')` shakli aynan ko'chirildi.

**Qizardi (kutilgandek):**
- `test_human_empty_on_another_slot_does_not_make_it_billable` — `billable=True` bo'lib qoldi (rejada nomi qattiq yozilgan test) ✓
- `test_slot_combinations_match_the_literal_table[slots9]` — `((occupied, ai), (empty, human))`
- `test_slot_combinations_match_the_literal_table[slots18]` — uch slotli varianti
- `test_the_answer_depends_on_the_slot_set_not_on_the_order[slot_set8]`

Sabotaj ikkala sabab bilan ham to'g'ri sinaldi: predikat **sistemaga yetib bordi** va **testlar ikki holatni ajrata oldi** (jadvalda `((occupied, ai), (empty, human))` bilan `((occupied, human), (empty, ai))` **ikkalasi ham** bor).

Ikkala sabotaj ham **qaytarib olindi**; oxirgi holatda `pytest tests/unit`, `pytest tests/tenancy`, `ruff check`, `ruff format --check`, `mypy` — hammasi yashil.

## Decisions Made

Yuqoridagi `key-decisions` blokiga qarang. Eng qimmat uchtasi:

1. **Zond `app_engine` ni ishlata olmaydi.** `tests/conftest.py::app_engine` ATAYIN `pool_size=1, max_overflow=0` (GUC sizishini ochib berish uchun). Bitta ulanishli pulda ikki korutina **ketma-ket** yugurardi — poyga hech qachon yuz bermasdi va zond «hammasi joyida» degan **bo'sh** javob berardi. Zond o'z engine'ini quradi (`pool_size=5`: yozuvchi + raqib + kuzatuvchi), rol baribir `sbozor_app`.
2. **Interleaving `sleep()` bilan taxmin qilinmaydi.** `asyncio.sleep(0.2)` yozish vasvasasi aniq va u rad etildi: sekin xostda raqib hali qulfga yetmagan bo'lardi va o'lchov «CTE qatorni KO'RDI» degan **teskari** natija berardi — flaky test emas, **yolg'on javob**. Kutish `pg_stat_activity.wait_event_type = 'Lock'` bo'yicha, kuzatuvchi sessiya ham `sbozor_app` bilan (boshqa rol backendlarining ustunlari niqoblanadi).
3. **`raise AssertionError`, `assert` bayonoti emas.** `assert` `python -O` da butunlay olib tashlanadi — nazorat aynan ishlab chiqarish rejimida yo'qolardi; ruff `S101` uni mahsulot kodida taqiqlaydi ham. Tip esa ATAYIN `AssertionError`: bu kirish sharti emas, funksiyaning **o'z arifmetikasining** nazorati.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**
- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da; worktree ularsiz yaratilgan. `docker compose` `${DATABASE_URL}` ni yechа olmadi va `storage` konteyneri `read /etc/seaweedfs/s3.json: is a directory` bilan **unhealthy** bo'ldi (Docker yo'q fayl o'rniga **katalog** yaratgan).
- **Fix:** Bo'sh katalog `rmdir` bilan olib tashlandi; ikkala fayl ham asosiy repodan nusxalandi. ⚠ Ikkalasi ham gitignored — **commit qilinmadi**.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Verification:** `docker compose --profile test run --rm tests pytest ...` ishga tushdi
- **Committed in:** — (repoga tegmaydi)

**2. [Rule 1 - Bug] `stall_repo.sqlstate_of()` A2 zondida JIMGINA `None` qaytarardi**
- **Found during:** Task 2
- **Issue:** Reja SQLSTATE ni `stall_repo.sqlstate_of()` bilan o'qishni aytgan. Yordamchi `getattr(exc.orig, "sqlstate", None)` qiladi — u SQLAlchemy `IntegrityError` **o'ramini** kutadi. Zond esa xom `psycopg.Error` bilan ishlaydi (`sync_owner_conn`), unda `.orig` **yo'q** → yordamchi jimgina `None` qaytarib, «rad etishning sababi o'lchanmadi» degan **yolg'on** natija berardi.
- **Fix:** SQLSTATE `error.sqlstate` dan **to'g'ridan-to'g'ri** o'qiladi; sabab `GeneratedColumnProbe` docstringida yozildi. Test `sqlstate is not None` ni rad etish shoxida assert qiladi.
- **Files modified:** `tests/tenancy/test_generated_from_column_probe.py`
- **Verification:** `pytest tests/tenancy/test_generated_from_column_probe.py -q` → 2 test yashil
- **Committed in:** `46a53d9`

**3. [Rule 3 - Blocking] Mahsulot kodida `assert` ruff `S101` ni qizartirdi**
- **Found during:** Task 3 (`ruff check .`)
- **Issue:** Reja ikki invariantni `assert` bilan majburlashni aytgan. `pyproject.toml` `S101` istisnosini faqat `tests/**` ga beradi, ya'ni `billing.py` dagi ikki `assert` `ruff check` ni qizartirdi. Qo'shimcha (rejada yozilmagan) muammo: `assert` `python -O` da butunlay olib tashlanadi — nazorat prodda yo'qolardi.
- **Fix:** `if <shart buzilgan>: raise AssertionError(...)` shakliga o'tkazildi; ikkala sabab ham funksiya docstringida yozildi. Semantika o'zgarmadi (`AssertionError` — o'sha tip).
- **Files modified:** `packages/sbozor-core/sbozor_core/billing.py`
- **Verification:** `ruff check .` toza; invariant testlari (`test_the_two_invariants_hold_for_every_row`, 11 holat) yashil
- **Committed in:** `c16bd7d`

**4. [Rule 3 - Blocking] A2 zondining uchinchi testi qabul mezoniga zid edi**
- **Found during:** Task 2
- **Issue:** Reja bir vaqtda **ikki** shartni qo'ygan: «AYNAN 2 ta test bajariladi» **va** «zond jadvali test oxirida qolmaydi (`to_regclass` → `NULL`)». Uchinchi test yozish birinchi shartni buzardi.
- **Fix:** `to_regclass` tekshiruvi `_drop_probes()` ning **ichiga** ko'chirildi, ya'ni u **har** testdan keyin bajariladi (alohida test faqat o'zidan oldingisini ko'rardi). Test soni 2 bo'lib qoldi va da'vo **kuchayd**i.
- **Files modified:** `tests/tenancy/test_generated_from_column_probe.py`
- **Verification:** `pytest ... -q` → 2 test; `to_regclass` asserti ikkala jadval uchun ham ishlaydi
- **Committed in:** `46a53d9`

---

**Total deviations:** 4 auto-fixed (2 blocking-infra, 1 bug, 1 blocking-lint)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. #2 va #4 rejaning ichki ziddiyatlarini **o'lchov foydasiga** hal qildi; #3 rejaning talabini (invariant funksiyaning o'zida) **kuchliroq** shaklda bajardi. Yangi paket **o'rnatilmadi** (T-06-SC bandi buzilmadi).

## Issues Encountered

- **`docker compose down -v` dev volumelarni o'chirdi.** Storage konteynerining nosozligini tozalash paytida `-v` bayrog'i ishlatildi va u `sbozor_pgdata` bilan `sbozor_seaweed` volumelarini **o'chirdi**. Test to'plami `testcontainers` bilan **o'z** Postgres'ini ko'taradi, ya'ni birorta o'lchov ta'sirlanmadi; lekin xostdagi dev bazasi bo'shadi va uni tiklash uchun `npm run migrate` kerak bo'ladi. Qolgan barcha yugurishlarda `-v` **ishlatilmadi**.
- **`gate:fast` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q va uni o'rnatish paket-menejer amali (ijrochi qoidasi bo'yicha avto-tuzatishdan **chiqarilgan**). Backend yarmi o'lchandi: **29 s** (butun `gate:fast` byudjeti 180 s, tarixiy o'lchov 87 s). Bu reja **birorta frontend faylga tegmaydi**, ya'ni frontend yarmiga ta'sir yo'q. Byudjet **o'zgartirilmadi**.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/tenancy/test_idempotency_concurrency.py -q` | ✅ 3 test |
| `pytest tests/tenancy/test_generated_from_column_probe.py -q` | ✅ 2 test |
| `pytest tests/unit -q` | ✅ (127 tasi shu rejadan) |
| `pytest tests/tenancy -q` | ✅ mavjud to'plam buzilmagan (exit 0) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (286 fayl) |
| `grep -nE "\babs\(\|float\(\|Decimal" billing.py \| grep -v '^[0-9]*: *#' \| wc -l` | ✅ `0` |
| `grep -c "from migrations.helpers import" test_generated_from_column_probe.py` | ✅ `1`; `AT TIME ZONE` literali `0` |
| `grep -n "payment_allocations" billing.py` | ✅ **1 ta** — faqat taqiq docstringida (`:479`) |
| `grep "probe_idempotent_writes" migrations/entities/__init__.py` | ✅ **0** — `ALL_TENANT_TABLES` da yo'q |
| `npm run gate:fast` (backend yarmi) | ✅ 29 s |

**Reja qabul mezonlarining bevosita tasdig'i** (`python -c` bilan bajarildi, hammasi o'tdi):
`billable_from_slots([(O,AI)]).billable is False` · `[(O,AI),(O,AI)] is True` · `[(O,HUMAN)] is True` · ⛔ `[(O,AI),(E,HUMAN)] is False` · `[(E,NC),(E,NC)].no_coverage_only is True` · `[].slots == 0 and no_coverage_only is False` · `variance(1_200_000, 1_235_000) == -35_000` · `variance(1_235_000, 1_200_000) == 35_000` · `payment_quote_set(None, 45000) == (45000,)` · `payment_quote_set(None, 0) == ()` · `payment_quote_set(15000, 0) == (15000,)` · `payment_quote_set(15000, 45000) == (15000, 45000, 60000)` · `ALLOCATION_RULE == "FIFO_OLDEST_SERVICE_DATE_FIRST"`.

## Known Stubs

Yo'q. Modul to'liq implementatsiya qilingan; birorta funksiya qotirilgan bo'sh qiymat qaytarmaydi, `TODO`/`FIXME`/placeholder matn yo'q (grep bilan tekshirildi).

## Threat Flags

Yangi xavfsizlik yuzasi **ochilmadi**: yangi tarmoq endpointi, autentifikatsiya yo'li, fayl kirishi yoki ishonch chegarasidagi sxema o'zgarishi yo'q. Ikkala zond jadvali ham `sbozor_owner` bilan yaratilib har testdan keyin `DROP` qilinadi va `pg_catalog` da qolmasligi mexanik o'lchanadi. Yangi paket o'rnatilmadi (T-06-SC bandi bajarildi).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): xostdagi dev bazasi `docker compose down -v` tufayli bo'shadi — `npm run migrate` bilan tiklanadi. Test o'lchovlariga ta'siri **yo'q** (testcontainers).

## Next Phase Readiness

- **06-02 (xato kodlari reyestri):** `payment_quote_set() == ()` → **422** ning yagona sharti aniqlangan; `stall_not_assigned` → 409 kodi shu reyestrda tug'iladi.
- **06-03 (`0020` migratsiyasi):** A2 tanlovi (Variant A) sabab bilan qulflangan — `service_date` domen ustuni + `business_date` `created_at` dan hosila.
- **06-06 (`billing_repo`):** `billable_from_slots()` predikatini SQL da **takrorlamaydi**; `vendor_charge_allocation()` `allocate_charge_credit()` ni chaqiradi va `ALLOCATION_RULE` nomini qaytaradi. G-14 ning arifmetik tengligi (`Σ unpaid == vendor_outstanding()`) invariant (b) bilan oldindan majburlangan.
- **06-09 (`POST /payments`):** `IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True` → **ikki bayonotli** get-or-create; `SAVEPOINT` shoxi kerak emas. `total_due_soum()` va `payment_quote_set()` — yagona arifmetika manbai.
- ⚠ **Ochiq band (bloklamaydi):** `stall_slot_occupancy` da `UNIQUE (market_id, id)` **yo'q** (C-7/Gotcha 8), ya'ni `charge_evidence` unga kompozit FK qo'ysa `0020` **o'zi yiqiladi**. Bu 06-03 ning OP-11 juftligi va u bu rejada hal qilinmadi.

## Self-Check: PASSED

Har bir da'vo mexanik tekshirildi:

**Fayllar (9/9 mavjud):** `billing.py` · `idempotency_probe.py` ·
`test_idempotency_concurrency.py` · `test_generated_from_column_probe.py` ·
`test_billable_from_slots.py` · `test_variance.py` ·
`test_payment_credit_rules.py` · `migrations/entities/__init__.py` ·
`06-01-SUMMARY.md`

**Commitlar (4/4 topildi):** `c82b4e1` · `46a53d9` · `c16bd7d` · `012245b`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `billing.py` `min_lines: 190` | `wc -l` → **586** | ✅ |
| `billing.py` `contains: FIFO_OLDEST_SERVICE_DATE_FIRST` | `grep -c` → **2** | ✅ |
| `test_billable_from_slots.py` `contains: EXPECTED_BY_SLOT_SET` | `grep -c` → **9** | ✅ |
| `test_payment_credit_rules.py` `contains: FIFO_ALLOCATION_TABLE` | `grep -c` → **14** | ✅ |
| `key_links`: marker `IDEMPOTENT_GET_OR_CREATE_SUPPORTED` | `grep -c` → **3** (e'lon + `__all__` + import) | ✅ |
| `key_links`: `from sbozor_core.enums import` (yangi enum yaratilmadi) | mavjud | ✅ |
| `key_links`: `ALLOCATION_RULE` / `total_due_soum` eksport qilingan | `__all__` da | ✅ |

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
