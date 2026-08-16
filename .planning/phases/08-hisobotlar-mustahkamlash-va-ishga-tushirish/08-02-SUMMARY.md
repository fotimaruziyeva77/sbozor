---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 02
subsystem: schema/migrations
tags: [ledger, audit, rls, multi-tenant, reconciliation, migrations]
requires:
  - "0023_notification_domain (market_notification_settings, PK market_id)"
  - "0020_billing_domain (daily_charges, billing_anomalies)"
  - "stalls (market_id, id) UNIQUE — 2-faza"
provides:
  - "ledger_entries jadvali — SC#5 uch tomonlama solishtiruvining UCHINCHI manbasi"
  - "UNIQUE(market_id, business_date, stall_id) — takroriy import idempotentligi"
  - "market_notification_settings.id uuid PK + UNIQUE(market_id) SAQLANGAN"
  - "market_notification_settings AUDIT ostida — direktor chati tarixi row_id bilan"
affects:
  - "08-14 (daftar importi) — yozadigan jadval shu yerda tug'ildi"
  - "08-16 (uch tomonlama solishtiruv) — o'qiydigan manba shu yerda"
  - "binding_repo.bind_director() — endi DB triggeri audit qatorini yozadi"
tech-stack:
  added: []
  patterns:
    - "alembic 0024/0025 — jadval + kaskad AYNI migratsiyada (0023 naqshi)"
    - "PK ko'chirish + UNIQUE saqlash (ON CONFLICT inference tayanchi)"
    - "o'lchov markeri kodda (BILLABLE_ANCHOR_SUPPORTED naqshi)"
key-files:
  created:
    - migrations/versions/0024_ledger_entries.py
    - migrations/versions/0025_notification_settings_id.py
    - packages/sbozor-core/sbozor_core/models/ledger.py
    - tests/tenancy/test_ledger_domain_meta.py
    - tests/integration/test_notification_settings_audit.py
  modified:
    - migrations/entities/__init__.py
    - migrations/entities/functions.py
    - migrations/entities/triggers.py
    - migrations/helpers.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/models/notification.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - services/core-api/app/repositories/binding_repo.py
    - tests/integration/test_market_delete_guard.py
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md
decisions:
  - "ledger_entries FINANCIAL_TABLES ga QO'SHILMAYDI — daftar 0 summani ham yozadi"
  - "ledger_entries AUDITED_TABLES ga QO'SHILADI — ON CONFLICT DO UPDATE, iz yagona"
  - "market_notification_settings PK id ga ko'chdi, UNIQUE(market_id) saqlandi"
  - "«fn_audit_row() id ustunisiz yiqiladi» da'vosi O'LCHOV bilan RAD ETILDI"
metrics:
  duration: "~1s 15daq"
  completed: 2026-08-16
requirements: [RECON-04]
---

# Phase 8 Plan 02: Daftar reyestri va sozlama auditi — Summary

Ikkita migratsiya (`0024` daftar jadvali, `0025` sozlama `id uuid` PK) va
ular bilan bir commitdagi reyestr yozuvlari; yo'l-yo'lakay repo'ning besh
joyida takrorlangan o'lchanmagan da'vo o'lchov bilan rad etilib tuzatildi.

## Bajarilgan ishlar

| Vazifa | Nima qilindi | Commit |
| ------ | ------------ | ------ |
| T1 | Wave-0 zondi — `fn_audit_row()` `id` ustunisiz jadvalda o'lchandi | `f75e666` |
| T2 | `0024_ledger_entries` + model + reyestrlar + meta-testlar + kaskad | `58e139b` |
| T3 | `0025_notification_settings_id` + audit + uchta test + sabotaj | `711385b` |

## ⛔ ZOND NATIJASI (T1) — REPO HUJJATI YOLG'ON EDI

Reja bu o'lchovni ATAYIN talab qilgan edi: repo'ning uch joyi
«`fn_audit_row()` `id` ustunisiz jadvalda har DML da YIQILADI» degan, lekin
manba kodini o'qish buni tasdiqlamagan edi.

**O'lchov:** 2026-08-16, `PostgreSQL 18.4 (Debian trixie)`, testcontainer.
`market_notification_settings` ga (o'sha paytdagi holatida — PK `market_id`,
`id` ustuni YO'Q) `fn_audit_row()` qo'lda ulandi va bitta
`UPDATE ... SET overdue_days = 7` bajarildi.

**NATIJA — VARIANT (b), LITERAL:**

```
DML O'TDI (istisno YO'Q).
audit_log qatorlari : 1
row_id              : NULL
action              : 'update'
changed_keys        : ['overdue_days']
```

Mexanika: `jsonb ->> '<yo'q kalit>'` `NULL` beradi, `NULL::uuid` istisno
ko'tarmaydi, `audit_log.row_id` esa `nullable` (`0002_audit.py:111`).

⚠ **O'LCHOVNING SHARTI — bir marta tuzoqqa tushildi va u qayd etilgan:**
birinchi urinishda `audit_log` sanog'i `0` chiqdi va bu «qator yozilmadi»
degan YOLG'ON xulosaga olib borardi. Sabab: `audit_read` policy'si
tenant-scoped va u jadval EGASIGA ham qo'llanadi (`FORCE`).
`set_config('app.market_id', ...)` dan keyin qator KO'RINDI.

**Oqibat:** «yiqiladi» shaklidagi test YOZILMADI. Haqiqiy nuqson yomonroq
edi — `row_id IS NULL` bo'lgan audit qatori QAYSI QATORGA tegishli ekanini
aytmaydi; yiqilish darhol ko'rinardi, `NULL` esa jimgina yozilib turardi.
Natija SUMMARY da qolmadi, **kodda qulflandi**
(`tests/integration/test_notification_settings_audit.py::
AUDIT_ROW_WITHOUT_ID_COLUMN_RAISES = False`).

## ⛔ SABOTAJ NATIJASI (T3) — `UNIQUE(market_id)`

`0025` dan `op.create_unique_constraint(...)` satri vaqtincha olib
tashlandi va `test_bind_director_is_idempotent_across_two_calls` ishga
tushirildi.

**NATIJA — test QIZARDI, xato LITERAL:**

```
asyncpg.exceptions.InvalidColumnReferenceError: there is no unique or
exclusion constraint matching the ON CONFLICT specification
```

Ya'ni darvoza HAQIQATAN o'sha bandni o'lchaydi. Cheklov qaytarildi va test
yashil. ⚠ Istisno tipi `asyncpg.*` (`psycopg.*` EMAS) — `bind_director()`
ilovaning async yo'lidan o'tadi; bu farq test docstringida qayd etilgan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `market_delete_draft()` kaskadi kengaytirildi**
- **Found during:** Task 2
- **Issue:** `ledger_entries` `markets` ga FK bilan bog'lanadi, ya'ni
  `test_cascade_covers_every_table_referencing_markets` (integration)
  QIZARARDI. Reja bu qadamni ko'rsatmagan, lekin `0023` uni AYNI
  migratsiyada bajarish precedentini o'rnatgan.
- **Fix:** `LEDGER_DELETE_ORDER` reyestri + `MARKET_DELETE_DRAFT` tanasiga
  daftar bloki (kaskadning ENG BOSHIDA — `ledger_entries` `stalls` ga
  tayanadi va undan OLDIN o'chirilishi shart) + `0024` da
  `drop_entity`/`create_entity`/`_regrant` (0023 naqshi) +
  `KNOWN_TENANT_TABLE_COUNT` 34 → 35.
- **Files:** `migrations/entities/functions.py`, `migrations/entities/__init__.py`,
  `migrations/versions/0024_ledger_entries.py`, `tests/integration/test_market_delete_guard.py`
- **Commit:** `58e139b`

**2. [Rule 1 - Bug] `bind_director()` docstringi `0025` dan keyin YOLG'ON bo'lardi**
- **Found during:** Task 3
- **Issue:** Docstring «⛔ AUDIT QATORI YOZILMAYDI VA BU TEXNIK TO'SIQ»
  der edi. `0025` triggerni ulagandan keyin audit qatori HAQIQATAN
  yoziladi — ya'ni hujjat kodning xulqiga ZID bo'lib qolardi (aynan
  `revoke()` da topilgan WR-03 sinfidagi nomuvofiqlik).
- **Fix:** Docstring o'lchovga muvofiq qayta yozildi; «ilova darajasida
  qo'lda audit yozilmaydi» qoidasi (WR-03) ATAYIN saqlandi — iz DB
  triggeridan keladi.
- **Files:** `services/core-api/app/repositories/binding_repo.py`
- **Commit:** `711385b`

**3. [Rule 1 - Bug] O'lchanmagan da'vo yana UCH joyda tuzatildi**
- **Found during:** Task 3
- **Issue:** Reja faqat `schema_contract.py` ni ko'rsatgan, lekin aynan
  o'sha yolg'on mexanizm da'vosi `migrations/helpers.py::attach_audit_trigger`
  («TALAB» izohi), `migrations/entities/triggers.py::FN_AUDIT_ROW`
  («ulash mumkin emas») va `migrations/entities/__init__.py::
  NOTIFICATION_AUDITED_TABLES` da ham yozilgan edi. Ularni qoldirish
  o'lchovni bir joyda tuzatib, to'rt joyda saqlab qolardi.
- **Fix:** To'rtalasi ham o'lchov natijasiga muvofiq tuzatildi. Chiqarish
  QARORLARI (`stall_code_registry`, `nvr_credentials`) KUCHDA qoldi —
  faqat sabablari to'g'ri nomlandi (`nvr_credentials` da Fernet
  argumenti allaqachon mustaqil va yetarli edi).
- **Commit:** `711385b`

**4. [Reja hujjati] 07 `deferred-items.md` №4 yopiq deb belgilandi**
- **Reason:** Bandning EGASI ochiq matnda «8-faza» deb yozilgan va faylda
  `## 5. ✅ YOPILDI (07-21)` precedenti bor. Bandning eski «texnik to'siq»
  matni ATAYIN o'chirilmadi — u tarix sifatida, rad etilgan mulohaza
  bilan birga qoldirildi.
- **Commit:** `711385b`

### Acceptance criteria — literal bajarilmagan uchtasi va sababi

⛔ Uchalasi ham GREP shaklida yozilgan va uchalasining ham NIYATI
bajarilgan; grep esa repo'ning o'z hujjatlashtirilgan darsiga
(`03-07`/`07-02`: «darvoza sanoq emas, manbadan hosila») tayanmaydi.

| Mezon | Holat | Sabab |
| ----- | ----- | ----- |
| `grep -c "SECURITY DEFINER" 0024` → `0` | **4** | `0023` da ham AYNAN `4`. Kaskadni kengaytirish `downgrade()` uchun ESKI funksiya tanasini migratsiyada MUZLATISHNI talab qiladi (`0023` ning `MARKET_DELETE_DRAFT_WITHOUT_NOTIFICATIONS` naqshi) — usiz `downgrade()` YANGI tanani qaytarardi. NIYAT (yangi DEFINER yuzasi yo'q) `test_no_new_security_definer_function_was_added` da TO'PLAM TENGLIGI bilan o'lchandi va YASHIL. |
| `grep -c "financial_guards" 0024` → `0` | **3** | Uchalasi ham DOCSTRING/IZOH — `financial_guards(` CHAQIRUVI YO'Q. Uchalasi aynan «nega chaqirilmaydi» ni tushuntiradi, ya'ni grep darvozasi faylni O'Z SABABI uchun jazolardi va yagona «tuzatish» yo'li sababni O'CHIRISH bo'lardi (03-07 da bir marta haqiqatan sodir bo'lgan). |
| `0024` da `uq_ledger_entries_market_day_stall` nomli `UniqueConstraint` | **semantik ✅** | Nom `LEDGER_DAY_STALL_UNIQUE` sifatida MODELDAN import qilinadi — bu rejaning O'ZI boshqa joyda talab qilgan qoida (OP-10: nom BITTA manbadan). Cheklovning BAZADA aynan shu nom bilan mavjudligi `test_repeated_import_is_idempotent_by_a_database_constraint` da o'lchandi va YASHIL — grepdan kuchliroq dalil. |

## Verification

| Tekshiruv | Natija |
| --------- | ------ |
| `pytest tests/tenancy` (to'liq) | ✅ exit 0 |
| `pytest tenancy + notification_settings_audit + bot_internal_api + market_delete_guard + notifications` | ✅ exit 0 (~615 test) |
| `alembic downgrade 0023` → `upgrade head` | ✅ xatosiz (ikki marta) |
| `ruff check` + `ruff format --check` (migrations/packages/tests/services) | ✅ 346 fayl toza |
| `grep -c "yiqilardi" schema_contract.py` | ✅ `0` |
| `AUDITED_TABLES` da `ledger_entries` va `market_notification_settings` | ✅ ikkalasi bor |
| `test_notification_settings_audit.py` da `def test_` soni | ✅ `3` (biri `row_id` tengligini o'lchaydi) |
| `DEFINER_SURFACES` / definer to'plami o'smagani | ✅ tenglik bilan yashil |

## Success criteria

- ✅ `ledger_entries` mavjud, RLS/FORCE/policy/GRANT to'liq, kompozit FK va ikki UNIQUE o'rnida
- ✅ `market_notification_settings` da `id uuid` PK va `UNIQUE(market_id)` birga
- ✅ `bind_director()` ikki shoxda ham ishlaydi va audit qatori `row_id` bilan yoziladi
- ✅ `DEFINER_SURFACES` bo'sh qoldi (to'plam tengligi bilan o'lchandi)
- ✅ Ikki sabotaj/zond natijasi SUMMARY da RAQAM va LITERAL xabar bilan

## Known Stubs

Yo'q — bu reja sxema qatlamini yopadi va birorta simulyatsiya qilingan
qiymat qoldirmaydi. `ledger_entries` ga YOZUVCHI yo'l (import) ATAYIN
08-14 ning ishi, O'QUVCHI (uch tomonlama solishtiruv) esa 08-16 niki —
bu «stub» emas, rejalashtirilgan ketma-ketlik (reja `<objective>` da
ochiq yozilgan).

## Threat Flags

Yangi tahdid yuzasi topilmadi. `<threat_model>` dagi `mitigate` bandlari
bajarildi: T-08-04 (RLS+FORCE+policy+kompozit FK), T-08-05 (UNIQUE
idempotentlik), T-08-06 (audit trigger + `row_id IS NOT NULL`), T-08-07
(UNIQUE(market_id) sabotaj bilan), T-08-08 (yangi DEFINER yaratilmadi).

## Self-Check: PASSED

Yaratilgan besh fayl ham diskda mavjud; uchala commit ham `git log` da
(`f75e666`, `58e139b`, `711385b`).
