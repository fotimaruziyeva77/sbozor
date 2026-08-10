---
phase: 06-billing-va-kassir
plan: 04
subsystem: billing
tags: [postgres, alembic, rls, immutability-triggers, security-definer, schema-contract, meta-tests]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 01
    provides: "A2 o'lchovi va uning Variant A qarori (`service_date` domen ustuni + `business_date` `created_at` dan hosila); `ALLOCATION_RULE = FIFO_OLDEST_SERVICE_DATE_FIRST`"
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`sbozor_core/enums.py` ning yetti domen enumi — har `CHECK` shulardan HOSILA"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`occupancy_events` (shartsiz o'zgarmas — muzlatilgan dalil), `stall_slot_occupancy`, `0018` ning verbatim shabloni, `0019` ning muzlatilgan-nusxa naqshi"
  - phase: 02-bozor-domeni
    provides: "`migrations/helpers.py::BUSINESS_DATE_EXPR`, `financial_guard_statements()`, `0008_temporal.py` ning «`financial_guards()` chaqirilmaydi» presedenti"
provides:
  - "Olti tenant jadvali: `cashier_shifts`, `daily_charges`, `charge_adjustments`, `charge_evidence`, `payments`, `billing_anomalies` — RLS + tenant policy + kompozit FK bilan"
  - "Uch o'zgarmaslik qo'riqchisi: `charge_immutable()` / `payment_immutable()` (SHARTSIZ) va `shift_declaration_immutable()` (SHARTLI)"
  - "`stall_slot_occupancy` ga `uq_stall_slot_occupancy_market_id_id` — 5-fazadan qolgan yetishmayotgan FK nishoni (C-7/OP-11)"
  - "`market_delete_draft()` kaskadining TO'RTINCHI kengaytmasi (`0021`)"
  - "Orfan `SECURITY DEFINER` yuzasining YOPILISHI: `audit_draw_due_markets()` va `occupancy_day_close_markets()` DROP qilindi (C-11/G-10)"
  - "Umumlashtirilgan `DERIVED_ORDER_PATTERN` — har `*_DELETE_ORDER` avtomatik qamraladi (§5.8 yopildi)"
affects: [06-05, 06-06, 06-08, 06-09, 06-10, 06-12, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tarixiy migratsiyaga MUZLATILGAN REYESTR ko'chirish (`0019` ning muzlatilgan-TA'RIF naqshining teskarisi): reyestr bo'shatilganda eski migratsiya no-op bo'lib qolmasin VA `EXECUTE TO PUBLIC` oynasi ochilmasin"
    - "Xato-sinfi qo'riqchi SHAKLI bilan birga yuradi: SHARTSIZ append-only -> `P0001`, SHARTLI domen-qoidasi -> `23514`; test SQLSTATE ni OCHIQ o'lchaydi, ya'ni shaklning jimgina almashtirilishi ham ushlanadi"
    - "Domen darvozasining regeksi NOMGA emas, SHAKLGA yoziladi (`(\\w+)_DELETE_ORDER`) va naqshning O'ZI pozitiv/negativ nazorat bilan sinaladi — aks holda 'hech nima topilmadi' BO'SH rost bo'lardi"
    - "Ikki vaqt ustuni (DOMEN fakti + AUDIT fakti) — C-2 ning `cashier_shifts` dagi takrori: `opened_at` va `created_at`"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/models/billing.py
    - migrations/versions/0020_billing_domain.py
    - migrations/versions/0021_market_delete_billing.py
  modified:
    - packages/sbozor-core/sbozor_core/models/occupancy.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - migrations/entities/triggers.py
    - migrations/entities/functions.py
    - migrations/entities/__init__.py
    - migrations/versions/0018_occupancy_domain.py
    - tests/tenancy/test_meta.py
    - tests/tenancy/test_occupancy_domain_meta.py
    - tests/integration/test_market_delete_guard.py

key-decisions:
  - "06-04: `models/billing.py` `migrations.helpers` ni IMPORT QILA OLMAYDI — `sbozor-core` ning `pyproject.toml` ida `alembic` YO'Q; ifoda mavjud `TARIFF_BUSINESS_DATE_EXPR` dan qayta ishlatiladi, migratsiya esa `BUSINESS_DATE_EXPR` ni import qiladi (to'rtinchi nusxa yozilmadi)"
  - "06-04: `charge_evidence` da `business_date` USTUNI YO'Q — kun `daily_charges` dan meros; ikkinchi hosila sana yarim tunda bir kun farq qilib dalilni 'yo'q' qilardi (Pitfall 3)"
  - "06-04: `cashier_shifts` da IKKI vaqt ustuni (`opened_at` DOMEN, `created_at` AUDIT) — C-2/Variant A ning aynan takrori; `business_date` faqat `created_at` dan hosila bo'lishi mumkin"
  - "06-04: `shift_declaration_immutable()` ning TO'RT shoxi ham `ERRCODE 23514` beradi — bitta funksiya ichida ikki xato-sinfini aralashtirish chaqiruvchini ikki `except` yozishga majburlardi"
  - "06-04: `DERIVED_ORDER_PATTERN` UMUMLASHTIRILDI, ikkinchi konstanta QO'SHILMADI — har domen darvozaga bitta qator qo'shishni talab qilardi (D-32)"
  - "06-04: `0018` ga MUZLATILGAN REYESTR ko'chirildi (§5.9 (a)); (b) varianti `0018`->`0020` oralig'ida `EXECUTE TO PUBLIC` oynasini ochardi"
  - "06-04: `payments` ning o'ziga havola qiluvchi kompozit FK'si AYNI `CREATE TABLE` da — PG `UNIQUE` ni (`AT_PASS_ADD_INDEX`) FK dan (`AT_PASS_ADD_CONSTR`) oldin bajaradi; alohida `op.create_foreign_key` kerak emas"

patterns-established:
  - "Yangi domen uchun `<DOMEN>_TENANT_TABLES` / `_AUDITED_TABLES` / `_DELETE_ORDER` uchligi + `test_<domen>_registries_are_self_consistent` + `test_<domen>_delete_order_is_declared_not_derived`"
  - "Kaskad testi HAR DOIM juftlik bo'ladi: qoralama bozor TO'LIQ o'chadi + JONLI bozorda o'sha amal RAD ETILADI (aks holda `RETURN OLD` shoxi hamma narsani ochib qo'yardi)"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04, CASH-03, CASH-04]

# Metrics
duration: 191min
completed: 2026-08-10
---

# Phase 6 Plan 04: Billing sxemasi va kaskad Summary

**Fazaning kafolatlari endi kodda emas, SXEMADA: olti jadval, uch o'zgarmaslik qo'riqchisi, kaskadning to'rtinchi kengaytmasi va ikki orfan `SECURITY DEFINER` funksiyaning DROP qilinishi — beshta contradiction (C-1, C-2, C-4, C-5, C-7) va C-11/C-12 bir joyda, har birining sabab-izohi migratsiya sarlavhasida qulflangan.**

## Performance

- **Duration:** 191 min
- **Started:** 2026-08-10T10:32:00Z
- **Completed:** 2026-08-10T14:23:00Z
- **Tasks:** 3
- **Files modified:** 13 (3 yangi, 10 kengaytirilgan)

## Accomplishments

- **SC#1 ning idempotentlik kaliti DB darajasida:** `UNIQUE (market_id, stall_id, service_date)` — kalit HISOBLANAYOTGAN kunda, yozilgan kunda emas. `financial_guards()` ATAYIN chaqirilmadi (`0008_temporal.py` presedenti) va uchala qo'riqchi qo'lda yozildi; `test_financial_tables_have_guards` uchala shartda ham yashil.
- **SC#2 ning o'zgarmasligi DB darajasida:** `daily_charges` va `payments` ustida SHARTSIZ, `cashier_shifts` ustida SHARTLI qo'riqchi. Uchalasi ham `BEFORE UPDATE OR DELETE FOR EACH ROW` (`pg_trigger.tgtype = 27` bilan o'lchandi).
- **C-7 ning ikkinchi topilmasi yopildi:** `stall_slot_occupancy` da `UNIQUE (market_id, id)` YO'Q edi va usiz `0020` **o'zi** yiqilardi. Nishon migratsiyaning **0b bosqichida**, `charge_evidence` dan oldin yaratiladi (OP-11).
- **G-10 bajarildi:** ikki chaqiruvchisiz `SECURITY DEFINER` funksiya DROP qilindi va `pg_proc` da 0 qator qoldi. `downgrade()` ularni `_regrant()` bilan qaytaradi — o'lchandi: `proacl` da PUBLIC yozuvi **yo'q**.
- **Kaskad to'rtinchi marta kengaydi** va bu safar tartib IKKI mustaqil zanjirni qamraydi (`charge_evidence`→`daily_charges`, `payments`→`cashier_shifts`), ya'ni `reversed(BILLING_TENANT_TABLES)` bilan **ustma-ust tushmaydi** — 5-fazadagi tasodifiy ustma-ustlikdan farqli.
- **§5.8 ning darvoza bo'shlig'i yopildi:** `DERIVED_ORDER_PATTERN` nomga emas, SHAKLGA yozildi.

## Task Commits

1. **Task 1: Olti model, `AUDITED_TABLES` va yetishmayotgan UNIQUE nishoni** — `f04702e` (feat)
2. **Task 2: Uch qo'riqchi, `0020_billing_domain` va orfan DEFINER DROP** — `78a0c6f` (feat)
3. **Task 3: `0021` kaskad, ikki yangi meta test va kaskad xulqi** — `a92e8f4` (feat)

## Files Created/Modified

- `packages/sbozor-core/sbozor_core/models/billing.py` (**yangi**, 1057 qator) — olti model, 15 ta enum'dan hosila `CHECK` konstantasi, 8 indeks nomi, `BILLING_BUSINESS_DATE_EXPR`
- `migrations/versions/0020_billing_domain.py` (**yangi**, 814 qator) — sakkiz qaror sarlavhada; 0b bosqich + 6 jadval + 8 indeks + RLS + audit + 3 trigger + 2 DROP
- `migrations/versions/0021_market_delete_billing.py` (**yangi**, 177 qator) — `0019` shabloni, `MARKET_DELETE_DRAFT_WITHOUT_BILLING` muzlatilgan nusxasi
- `packages/sbozor-core/sbozor_core/models/occupancy.py` — `StallSlotOccupancy` ga BITTA `UniqueConstraint` (+ sabab izohi)
- `packages/sbozor-core/sbozor_core/models/__init__.py` — barrelga 6 klass + 36 konstanta
- `packages/sbozor-core/sbozor_core/schema_contract.py` — `AUDITED_TABLES` ga ikki nom; `FINANCIAL_TABLES` ga **hech nima**; har «YO'Q» uchun sabab docstringda
- `migrations/entities/triggers.py` — uch `PGFunction` + `BILLING_TRIGGER_FUNCTIONS` + aggregat
- `migrations/entities/functions.py` — `MARKET_DELETE_DRAFT` ga 6 `DELETE`; `OCCUPANCY_FUNCTIONS` va `OCCUPANCY_GRANT_SIGNATURES` **bo'shatildi**
- `migrations/entities/__init__.py` — uch yangi reyestr + `ALL_TENANT_TABLES` splice
- `migrations/versions/0018_occupancy_domain.py` — **faqat** muzlatilgan nusxa bloklari va tsikl chaqiruvlari (`git diff --numstat` → `62 / 6`; jadval/trigger DDL'i tegilmagan)
- `tests/tenancy/test_meta.py` — umumlashtirilgan regeks + 2 yangi meta test; `PENDING_AUDIT_TRIGGERS` T1 da to'ldi, T2 da bo'shadi
- `tests/tenancy/test_occupancy_domain_meta.py` — `DEFINER_SURFACES` bo'shatildi (sabab bilan)
- `tests/integration/test_market_delete_guard.py` — billing seed, kaskad testi, jonli-bozor nazorati, `KNOWN_TENANT_TABLE_COUNT` 23 → 29

## Qizil oynalar — HECH BIRI OCHILMADI

Reja to'rtta tartib juftligini ayni rejada saqlagan edi va vazifalar orasida «vaqtincha qizil» kutilgan edi. **Amalda birorta darvoza qizil bo'lmadi**, chunki har juftlikning ikki yarmi AYNI COMMITGA tushdi:

| Juftlik | Ikki yarmi | Commit |
|---|---|---|
| **OP-1** | `0020` (6 jadval) ↔ `0021` (kaskad) | ayni **rejada**, T2 → T3 |
| **OP-2** | `drop_entity(...)` ↔ `DEFINER_SURFACES`/`OCCUPANCY_*` bo'shatildi | `78a0c6f` |
| **OP-3** | `0020` ↔ `ALL_TENANT_TABLES` splice | `78a0c6f` |
| **OP-4** | `AUDITED_TABLES` ↔ `PENDING_AUDIT_TRIGGERS` (to'ldi/bo'shadi) | `f04702e` → `78a0c6f` |
| **OP-10** | `0020` indekslari ↔ modeldagi `Index(...)` | `f04702e` + `78a0c6f` |
| **OP-11** | `charge_evidence` FK ↔ `uq_stall_slot_occupancy_market_id_id` | `f04702e` (model) + `78a0c6f` (DDL) |

⚠ **OP-1 ning oynasi** (T2 va T3 orasida `test_cascade_covers_every_table_referencing_markets` oltala nom bilan qizil bo'lishi) **kuzatilmadi**, chunki T2 dan keyin to'liq to'plam ishga tushirilmadi — o'sha bosqichda faqat `tests/tenancy` o'lchandi va u kaskad testini qamramaydi. Ya'ni qizil oyna MAVJUD edi, lekin u hech qachon o'lchanmadi va T3 uni yopdi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `models/billing.py` `migrations.helpers` ni import qila olmaydi**

- **Found during:** Task 1
- **Issue:** Reja «`business_date` ifodasi `migrations.helpers` dan IMPORT qilinadi» deb yozgan. `migrations/helpers.py` esa `alembic.op` ni import qiladi, `packages/sbozor-core/pyproject.toml` da esa `alembic` **umuman yo'q** — bunday import `cv-service` va `bot-service` da `ModuleNotFoundError` bilan yiqilardi. Bog'liqlik yo'nalishi `models/market.py:188-196` da 2-fazadan beri yozilgan.
- **Fix:** `BILLING_BUSINESS_DATE_EXPR = TARIFF_BUSINESS_DATE_EXPR` — mavjud oyna nusxasi QAYTA ISHLATILADI, yangi literal yozilmaydi (to'rtinchi nusxa paydo bo'lmaydi). Migratsiya esa rejadagidek `migrations.helpers.BUSINESS_DATE_EXPR` ni import qiladi.
- **Files modified:** `packages/sbozor-core/sbozor_core/models/billing.py`
- **Verification:** `grep -c BUSINESS_DATE_EXPR billing.py` → 13; `grep -c "AT TIME ZONE" billing.py` → **0**; `mypy` toza
- **Committed in:** `f04702e`

**2. [Rule 1 - Bug] `shift_declaration_immutable()` bir funksiya ichida ikki xato-sinfini aralashtirardi**

- **Found during:** Task 3 (kaskad nazorat testi qizardi)
- **Issue:** Funksiyaning shartli shoxlari `ERRCODE = '23514'` bilan yozilgan edi (`TARIFF_PAST_IMMUTABLE` sinfi), `DELETE` shoxi esa ERRCODE'siz — ya'ni `P0001`. Chaqiruvchi bitta jadval uchun IKKI xil `except` yozishga majbur bo'lardi va `MARKETS_DELETE_GUARD` docstringidagi «Yangi konvensiya KIRITILMAYDI» qoidasi buzilardi.
- **Fix:** `DELETE` shoxiga ham `USING ERRCODE = '23514'` qo'shildi; taksonomiya (SHARTSIZ → `P0001`, SHARTLI → `23514`) funksiya docstringida jadval bilan yozildi.
- **Files modified:** `migrations/entities/triggers.py`
- **Verification:** `test_billing_rows_are_immutable_on_a_live_market` SQLSTATE ni OCHIQ solishtiradi (`daily_charges`/`payments` → `P0001`, `cashier_shifts` → `23514`), ya'ni shaklning jimgina almashtirilishi ham ushlanadi
- **Committed in:** `a92e8f4`

**3. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi (06-01 dagi holatning takrori)**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da; worktree ularsiz yaratilgan va Docker yo'q fayl o'rniga **katalog** yaratgan (`read /etc/seaweedfs/s3.json: is a directory`).
- **Fix:** Bo'sh katalog `rmdir` bilan olib tashlandi, ikkala fayl asosiy repodan **nusxalandi** (⛔ junction/symlink YARATILMADI — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan). Eskirgan konteyner `docker compose rm -sf storage` bilan qayta yaratildi (⛔ `-v` **ishlatilmadi**).
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

### Plan-ichidagi ziddiyat — jadval foydasiga hal qilindi

**`charge_evidence` da `business_date` ustuni YO'Q.** Reja matni «`business_date` **har jadvalda** `sa.Computed(...)`» deydi, jadval spetsifikatsiyasi esa `ChargeEvidence` uchun uni **sanamaydi**. Jadval tanlandi va sabab yozildi: dalil qatori kunni `daily_charges` dan (`charge_id` orqali) meros qiladi; ikkinchi hosila sana yarim tunda bir kun farq qilishi mumkin (Pitfall 3) va o'shanda o'sha hisobning dalili hisobotda «yo'q» bo'lib qolardi. `charge_evidence` `FINANCIAL_TABLES` da emas, ya'ni darvoza undan `business_date` talab qilmaydi.

### Rejadagi kutilgan xato sinfi tuzatildi

Reja qabul mezoni `cashier_shifts` ning `DELETE`/`UPDATE` rad etishini `RaiseException` deb yozgan. Amalda SHARTLI qo'riqchi `23514` (`CheckViolation`) beradi — bu repodagi mavjud taksonomiya (`TARIFF_PAST_IMMUTABLE`, `MARKETS_DELETE_GUARD`) va reja o'zi tanlagan SHAKL bevosita talab qiladigan natija. Test kuchliroq shaklda yozildi: u **SQLSTATE ni** solishtiradi, istisno klassining nomini emas.

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug) + 1 plan-ichidagi ziddiyat + 1 mezon tuzatilishi
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Yangi paket **o'rnatilmadi** (T-06-SC bandi buzilmadi), yangi `SECURITY DEFINER` funksiya **qo'shilmadi** (T-06-22 — yuza faqat KAMAYDI).

## Issues Encountered

- **`sbozor-snapshots` bucket'i yo'q edi** — 06-01 da qayd etilgan `docker compose down -v` ning oqibati: `sbozor_seaweed` volumi o'chirilgan va SeaweedFS bo'sh holatdan ko'tarilgan. `tests/integration/test_storage_layout.py`, `test_retention.py`, `test_snapshot_quality.py` `AccessDenied (403)` bilan yiqilardi. **Bu rejaning o'zgarishlariga umuman aloqasi yo'q** (u faqat DB qatlamiga tegadi), lekin to'liq to'plamni o'lchashni bloklardi. `ops/seaweedfs/README.md:108-109` dagi buyruq bilan tiklandi: `s3.bucket.create -name sbozor-snapshots`. Repoga birorta o'zgarish kiritilmadi.
- **`test_live_view_e2e.py` `sim` profilini talab qiladi.** Yalang'och `pytest -q` (profilsiz) ikki testni `httpx.ConnectError` bilan yiqitadi — `npm run gate` skripti aynan shuning uchun `npm run sim:up` bilan boshlanadi. Profil ko'tarilgach ikkalasi ham yashil.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q. ⛔ Junction/symlink **YARATILMADI** (bu ilgari asosiy checkout'ni buzgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. **Bu reja birorta frontend fayliga tegmaydi.**

## Verification

| Buyruq | Natija |
|---|---|
| `alembic upgrade head` (**nol holatdan**) | ✅ `0001` → `0021` |
| `alembic downgrade 0019 && alembic upgrade head` | ✅ |
| `alembic downgrade 0020 && alembic upgrade head` | ✅ `alembic current` → `0021 (head)` |
| `pytest tests/unit -q` | ✅ |
| `pytest tests/tenancy -q` | ✅ (yangi ikki meta test bilan) |
| `pytest tests/integration/test_market_delete_guard.py -q` | ✅ |
| `pytest -q` (to'liq to'plam) | ✅ |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (290 fayl) |
| **Backend gate** (`lint` + `pytest -q`, `sim` profili ko'tarilgan) | ✅ **854 s** (butun `gate` byudjeti 1250 s) |

**DB darajasidagi o'lchovlar** (`pg_catalog` dan, `0021` head holatida):

| Da'vo | O'lchov |
|---|---|
| Orfan DEFINER funksiyalar DROP qilindi (G-10) | `pg_proc` → **0 qator** |
| `downgrade 0020` ularni qaytaradi va PUBLIC EXECUTE bermaydi | `proacl` = `{sbozor_owner=X/…,sbozor_app=X/…}` — PUBLIC yozuvi **yo'q** |
| Uch qo'riqchi `BEFORE UPDATE OR DELETE FOR EACH ROW` | `tgtype = 27` (uchalasida) |
| `daily_charges`/`payments` da audit trigger **YO'Q** | ✅ |
| `charge_adjustments`/`cashier_shifts` da audit trigger **BOR** | ✅ |
| Qisman UNIQUE indeks (D-27) | `CREATE UNIQUE INDEX … WHERE (status = 'open'::text)` |
| Kasrli pul ustuni yo'q (D-11) | `information_schema` da `double precision`/`numeric` → **0 qator** |
| Uch funksiyada `prosecdef = false` + `search_path` | ✅ (uchalasida `search_path=pg_catalog, public`) |

**Reja qabul mezonlarining bevosita tasdig'i** (`python -c` bilan bajarildi):
`Payment.__table__.c` da `charge_id` **yo'q**, `service_date` va `quote_soum` **bor** · `DailyCharge/Payment/ChargeEvidence/CashierShift` da `updated_at` **yo'q** · `amount_soum`/`tariff_amount_soum` `BIGINT` · `uq_stall_slot_occupancy_market_id_id` mavjud · `AUDITED_TABLES` da ikki yangi nom, `daily_charges`/`payments` **yo'q**, `FINANCIAL_TABLES` da `cashier_shifts` **yo'q**.

**Grep mezonlari:**
`grep -cE "^[A-Z_]+_CHECK = f\"" billing.py` → **15** (≥ 8) ·
`grep -c FIFO_OLDEST_SERVICE_DATE_FIRST billing.py` → **2** ·
`grep -nE "\bfloat\b|Numeric|Decimal|balance|AT TIME ZONE" billing.py` → **0** ·
⛔ `grep -nE "allocated_|payment_allocations" billing.py` → **1 ta**, va u FAQAT `payments` docstringidagi **taqiq izohida** (`:829` — «`payment_allocations` jadvali ham, `allocated_*` ustuni ham YO'Q»), ya'ni ustun ham, jadval ham mavjud emas (D-24) ·
`git diff --numstat tests/tenancy/test_meta.py` T1 da faqat `PENDING_AUDIT_TRIGGERS` bloki (`18 / 4`) ·
`git diff --numstat 0018_occupancy_domain.py` → `62 / 6`, faqat muzlatilgan nusxa bloklari va tsikl chaqiruvlari ·
`DERIVED_ORDER_PATTERN` regeks literalida `OCCUPANCY_DELETE_ORDER` **yo'q** (`(\w+)_DELETE_ORDER` shaklida) ·
`KNOWN_TENANT_TABLE_COUNT` 23 → **29**, sabab izohda.

## Known Stubs

Yo'q. Uchala yangi fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn **yo'q** (grep bilan tekshirildi). Sxema qatlami to'liq — keyingi rejalar (`06-05` xulq testlari, `06-06` repo, `06-09` marshrutlar) yangi kafolat mexanizmi **o'ylab topmaydi**.

## Threat Flags

Yangi xavfsizlik yuzasi **ochilmadi va u faqat KAMAYDI**:

- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**, ikkitasi esa **DROP qilindi** (T-06-22, G-10) — RLS'ni chetlab o'tadigan chaqiruvchisiz yuza yopildi.
- Yangi tarmoq endpointi, autentifikatsiya yo'li yoki fayl kirishi **yo'q** (bu reja faqat sxema qatlamiga tegadi).
- Ishonch chegarasidagi sxema o'zgarishlari **mitigatsiya tomonda**: oltala jadvalda RLS `ENABLE`+`FORCE` + tenant policy + kompozit FK (T-06-21); `quote_soum` juftlangan `CHECK` D-19 ni ilova qatlamidan sxemaga ko'chirdi (T-06-18); uch o'zgarmaslik triggeri xom SQL yo'lini ham qamraydi (T-06-15/16/19).
- Yangi paket **o'rnatilmadi** (T-06-SC bandi bajarildi).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): `sbozor-snapshots` bucket'i xost dev stekida qayta yaratildi (`ops/seaweedfs/README.md:108`). Agar boshqa muhitda `sbozor_seaweed` volumi o'chirilgan bo'lsa, o'sha buyruqni takrorlash kerak.

## Next Phase Readiness

- **06-05 (xulq testlari):** uchala qo'riqchining SQLSTATE taksonomiyasi qulflangan (`P0001` = shartsiz, `23514` = shartli) — `test_billing_immutable.py` shu farqni o'lchashi mumkin va u `test_market_delete_guard.py` da allaqachon bir marta isbotlangan.
- **06-06 (`billing_repo`):** sxema to'liq; `daily_charges` ↔ `charge_evidence` ↔ `occupancy_events` zanjiri kompozit FK bilan yopiq, ya'ni repo dalilni `JOIN` bilan oladi va yangi tekshiruv yozmaydi.
- **06-09 (`POST /payments`):** `uq_payments_market_id_idempotency_key` + `request_fingerprint` joyida; 06-01 ning A1 markeri `True`, ya'ni **ikki bayonotli** get-or-create yo'li ochiq.
- **06-12/06-14 (darvozalar):** `test_billing_registries_are_self_consistent` va `test_billing_delete_order_is_declared_not_derived` allaqachon yashil; `KNOWN_TENANT_TABLE_COUNT = 29`.
- ⚠ **Ochiq band (bloklamaydi):** `tests/fixtures/billing_domain.py` YOZILMADI (`06-PATTERNS.md` §2 R-1 ning 8-bandi). Kaskad darvozasi uchun minimal seed `test_market_delete_guard.py` ning O'ZIDA yashaydi va sabab u yerda izohda: to'liq seed (`billing_close` xulqi, FIFO taqsimlash, variance) 06-05/06-06 rejalarining talablariga ega. Keyingi reja uni o'sha talablar bilan yozadi.

## Self-Check: PASSED

Har bir da'vo mexanik tekshirildi.

**Fayllar (13/13 mavjud):** `models/billing.py` · `0020_billing_domain.py` · `0021_market_delete_billing.py` · `models/occupancy.py` · `models/__init__.py` · `schema_contract.py` · `entities/triggers.py` · `entities/functions.py` · `entities/__init__.py` · `0018_occupancy_domain.py` · `test_meta.py` · `test_occupancy_domain_meta.py` · `test_market_delete_guard.py`

**Commitlar (3/3 topildi):** `f04702e` · `78a0c6f` · `a92e8f4`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `billing.py` `min_lines: 450` | `wc -l` → **1057** | ✅ |
| `billing.py` `contains: uq_daily_charges_market_id_stall_id_service_date` | `grep -c` → **1** | ✅ |
| `0020` — DDL + RLS + audit + 3 trigger + orfan DROP | fayl mavjud, `alembic upgrade head` o'tdi | ✅ |
| `0021` — kaskadning to'rtinchi kengaytmasi | `alembic current` → `0021 (head)` | ✅ |
| `key_links`: `charge_evidence` → `occupancy_events (market_id, id)` | `occupancy_event_id` `grep -c` → **10** | ✅ |
| `key_links`: `charge_evidence` → `uq_stall_slot_occupancy_market_id_id` | `0020` ning 0b bosqichida yaratiladi | ✅ |
| `key_links`: `daily_charges` → `trg_charge_immutable` | `pg_trigger` da mavjud, `tgtype = 27` | ✅ |
| `key_links`: `cashier_shifts` → `postgresql_where` | `grep -c` → **1**; indeks predikati `WHERE (status = 'open'::text)` | ✅ |

**`truths` (8/8):**
bir rasta-kunga ikkinchi hisob **yo'q** (`UNIQUE … service_date`) ·
hisobni tahrirlash/o'chirish DB darajasida **rad etiladi** ·
to'lovni tahrirlash/o'chirish **rad etiladi**, storno — yangi qator ·
bir kassirda ikki ochiq smena **yo'q** (qisman UNIQUE) ·
dalilsiz anomaliya ham, dalilli qamrovsizlik ham **ifodalab bo'lmaydi** ·
saqlangan qoldiq ustuni **hech qayerda yo'q** ·
D-24 ustun bilan emas, **nomlangan qoida** bilan javob oldi — ettinchi jadval **yo'q** ·
chaqiruvchisiz `SECURITY DEFINER` funksiya **qolmadi**.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
