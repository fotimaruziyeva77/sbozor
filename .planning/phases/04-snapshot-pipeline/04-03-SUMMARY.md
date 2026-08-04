---
phase: 04-snapshot-pipeline
plan: 03
subsystem: database
tags: [postgres, rls, alembic, generated-columns, exclude-constraint, btree_gist, security-definer, sqlalchemy]

requires:
  - phase: 04-snapshot-pipeline
    provides: "`04-01` ning D-23 o'lchovi (`BILLABLE_ANCHOR_SUPPORTED = true`), `SNAPSHOT_TENANT_TABLES`/`SNAPSHOT_AUDITED_TABLES`/`SNAPSHOT_DELETE_ORDER` reyestrlari, `PENDING_AUDIT_TRIGGERS` qarzi, `ix_capture_runs_overdue` indeks istisnosi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`cameras`/`nvr_devices` (kompozit FK nishonlari), `market_delete_draft()` kaskadining `pg_catalog` to'liqlik darvozasi, `0012` -> `0013` migratsiya juftligi shabloni"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`market_activate()`, `market_is_open()`, `daterange` + `EXCLUDE USING gist` + `btree_gist` naqshi, `AUDITED_TABLES` reyestri"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`GENERATED STORED` + `UNIQUE` DDL yo'li, tenancy meta-darvozalari, `enable_tenant_rls`/`attach_audit_trigger` yordamchilari"
provides:
  - "Beshta tenant jadvali (`snapshot_schedules`, `snapshot_schedule_slots`, `capture_runs`, `snapshots`, `alert_events`) — RLS ENABLE+FORCE + tenant policy + owner bootstrap"
  - "`system_heartbeats` — global jadval (`market_id` YO'Q), `grant_app_dml()` bilan"
  - "`snapshots.is_billable` `GENERATED ... STORED` + `uq_snapshots_billable_anchor` — 5-fazaning `occupancy_events` FK ilgagi (D-16)"
  - "`sbozor_core.models.snapshot` — beshta model, indeks/CHECK konstantalari, `CAPTURE_BUSINESS_DATE_EXPR`, `DEFAULT_SNAPSHOT_SLOTS`"
  - "Olti yangi `StrEnum` (`CaptureRunStatus`, `SnapshotQuality`, `SnapshotLightMode`, `SnapshotTier`, `AlertSeverity`, `CaptureMethod`)"
  - "`capture_due_markets()` — tik uchun tor `SECURITY DEFINER` yuzasi (faqat `market_id` + `due_count`)"
  - "`market_activate()` standart 7 slotli profilni idempotent yozadi + mavjud faol bozorlarga backfill (D-01)"
  - "NVR/kamera kadr sozlamalari: `capture_method`, `max_concurrent_captures`, `capture_stagger_ms`, `observed_stream_limit`, `cameras.capture_stream`, `market_profile.capture_on_closed_days`"
  - "`tests/fixtures/snapshot_domain.py` — ikki bozorli seed, oltala holat, `ok`+`dark` kadr"
  - "Yetti `pg_catalog` meta-invarianti + ikki funksiya-xulq darvozasi"
affects: [04-05, 04-06, 04-07, 04-08, 04-09, 04-10, 04-11, 04-12, 05-cv-zonalar, 06-billing]

tech-stack:
  added: []
  patterns:
    - "Kompozit FK nishoni `market_id` siz bo'lishi MUMKIN — lekin faqat u so'rov yo'li BO'LMAGANDA; istisno `INDEX_EXCEPTIONS` ga sabab bilan yoziladi"
    - "`LANGUAGE sql` funksiya tanasi CREATE paytida PARSE qilinadi — kelajakdagi jadvalga havola qiladigan funksiya `plpgsql` bo'lishi SHART"
    - "Ikki jadvalning bir xil generated ifodasi ALIAS bilan bog'lanadi (nusxa emas) va tenglik `pg_get_expr()` dan o'lchanadi"
    - "63 baytdan uzun konstrayt nomi PostgreSQL tomonidan JIMGINA kesiladi — uzun kompozit FK'ga nom QO'LDA beriladi"
    - "Sabotaj o'lchovi darvozaning O'ZINI baholaydi: qaysi test qizarganini emas, QAYSI BIRI YAGONA ekanini ko'rsatadi"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/models/snapshot.py
    - migrations/versions/0014_snapshot_domain.py
    - migrations/versions/0015_market_delete_snapshots.py
    - tests/fixtures/snapshot_domain.py
    - tests/tenancy/test_snapshot_domain_meta.py
  modified:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/models/nvr.py
    - packages/sbozor-core/sbozor_core/models/ops.py
    - packages/sbozor-core/sbozor_core/models/market.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - migrations/entities/functions.py
    - migrations/entities/__init__.py
    - tests/tenancy/test_meta.py
    - tests/integration/test_market_delete_guard.py

key-decisions:
  - "D-16 TUZILMAVIY shaklda yozildi (`GENERATED ... STORED` + `UNIQUE (id, is_billable)`) — `04-01` o'lchovi `true` bergani uchun trigger varianti KERAK BO'LMADI"
  - "`market_activate()` `LANGUAGE sql` -> `plpgsql`: `sql` tanasi CREATE paytida parse qilinadi va `0007` uni modulning JORIY ta'rifidan yaratadi (o'lchandi — butun to'plam yiqildi)"
  - "`uq_snapshots_billable_anchor` `INDEX_EXCEPTIONS` ga qo'shildi: 5-fazaning FK nishoni `market_id` bilan boshlana OLMAYDI, aks holda FK qurilmasdi"
  - "`SNAPSHOT_FUNCTIONS`/`SNAPSHOT_GRANT_SIGNATURES` — yangi migratsiya-scope'li ro'yxat; `ALL_FUNCTIONS` MUZLATILGAN va unga qo'shish `0001` ni yiqitardi"
  - "`snapshots.camera_id` ga kompozit FK QO'SHILDI (rejada yo'q edi) — denormalizatsiya tenant chegarasini bo'shatish uchun bahona emas"
  - "`system_heartbeats` RLS tsikliga kirmaydi, lekin `grant_app_dml()` MAJBURIY — usiz worker yurak urishini yoza olmasdi"
  - "CAM-05 kalitiga yettinchi `pg_catalog` invarianti qo'shildi — sabotaj o'lchovi uni faqat `alembic check` qo'riqlayotganini ko'rsatdi"

patterns-established:
  - "Sabotaj o'lchovining ikkinchi ustuni («nima YASHIL qoldi») darvozaning YETARLILIGINI baholaydi va yetishmayotgan invariantni ochadi"
  - "Migratsiya-scope'li funksiya ro'yxati: har migratsiya O'Z to'plamini oladi, aggregat faqat `ALL_ENTITIES` kuzatuvi uchun"
  - "Nullable ustunda enum `CHECK` ga `IS NULL OR` shoxi KERAK EMAS — `NULL IN (...)` `NULL` beradi, `CHECK` esa faqat `FALSE` da rad etadi"

requirements-completed: [CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06]

duration: 1h 50m
completed: 2026-08-04
---

# Phase 4 Plan 03: Snapshot sxema qatlami Summary

**Besh tenant jadvali + global `system_heartbeats` `0014` bilan migratsiyalandi; D-16 ning billing kafolati `GENERATED STORED` + `UNIQUE (id, is_billable)` shaklida TUZILMAVIY bo'ldi (trigger varianti kerak bo'lmadi); `0015` kaskadni beshta jadval bilan kengaytirdi, `capture_due_markets()` tik uchun tor yuza berdi va `market_activate()` standart 7 slotli profilni idempotent yoza boshladi.**

## Performance

- **Duration:** ~1h 50m
- **Tasks:** 3/3
- **Files modified:** 14 (5 yangi, 9 o'zgartirilgan)
- **Commits:** 4 ta task commiti (Task 3 — RED/GREEN juftligi) + 1 qo'shimcha darvoza commiti

## Accomplishments

- **D-16 TUZILMAVIY bo'ldi.** `04-01` ning `BILLABLE_ANCHOR_SUPPORTED = true` o'lchovi o'qildi va `0014` trigger variantida EMAS, `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED` + `UNIQUE (id, is_billable)` shaklida yozildi. Bazadan tasdiqlandi: `attgenerated = 's'`, `pg_get_constraintdef` -> `UNIQUE (id, is_billable)`. ~15 qator trigger kodi tejaldi.
- **`04-01` qoldirgan IKKALA qarz ham `0014` BILAN BIR COMMITDA yopildi.** `ALL_TENANT_TABLES` ga splice va `PENDING_AUDIT_TRIGGERS` ning bo'shatilishi — ikkalasi ham `dea1128` da. Ikki tomonlama qulf ikkinchi yo'nalishda ham o'lchandi (2-sabotaj).
- **3-fazaning kaskad darvozasi AYTGANIDEK qizardi va `0015` uni yopdi.** Xato xabarida beshala nom ham turdi. Tartib TALABI dinamik darvoza bilan alohida o'lchandi: `capture_runs` -> `cameras` FK'si snapshot blokini NVR blokidan OLDIN turishga majbur qiladi (RED bosqichida `ForeignKeyViolation` bilan tasdiqlandi).
- **Reja ochiq qoldirgan darvoza topildi va yopildi.** 1-sabotaj CAM-05 idempotentlik kalitini faqat `alembic check` qo'riqlayotganini ko'rsatdi — yettinchi `pg_catalog` invarianti qo'shildi (pastda, «Sabotaj o'lchovlari» va 6-deviatsiya).
- **Ikki yashirin nosozlik ish paytidan OLDIN topildi:** `LANGUAGE sql` funksiyaning CREATE-paytidagi parse qilinishi (butun to'plamni yiqitgan) va 63 baytlik konstrayt nomi chegarasi.

## Task Commits

1. **Task 1: Beshta model, `system_heartbeats`, NVR/kamera ustunlari va enumlar** — `93efb20` (feat)
2. **Task 2: `0014_snapshot_domain` + ikkala reyestr qarzi** — `dea1128` (feat)
3. **Task 3: kaskad, `capture_due_markets()`, standart profil** — `4dd5170` (test, RED) -> `9ad73c5` (feat, GREEN)
4. **Qo'shimcha darvoza (sabotaj natijasi):** `85d2b66` (test)

**Plan metadata:** quyidagi `docs(04-03)` commiti.

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `packages/.../models/snapshot.py` | Beshta model (866 qator), indeks/CHECK konstantalari enum'dan hosila, ikkala `business_date` ifodasi, `DEFAULT_SNAPSHOT_SLOTS` |
| `packages/.../enums.py` | Olti `StrEnum`; `missed`/`failed` farqi va `SnapshotTier.PURGED` ning sababi docstringda |
| `packages/.../models/ops.py` | `SystemHeartbeat` — `market_id` YO'Q, `component` PK, `/healthz` ga ulanmaslik ogohlantirishi |
| `packages/.../models/nvr.py` | `NvrDevice` +4 ustun (D-06/D-07/D-08), `Camera.capture_stream` (D-09), `CAPTURE_STREAM_CHECK` |
| `packages/.../models/market.py` | `MarketProfile.capture_on_closed_days` (D-10) — **rejada yo'q edi, migratsiya talab qildi** |
| `packages/.../models/__init__.py` | Barrel: 5 model + `SystemHeartbeat` + 20 konstanta |
| `migrations/versions/0014_snapshot_domain.py` | Olti-bandli qaror bloki, `require_extension("btree_gist")`, 6 jadval, 3 qisman indeks, ALTER'lar, RLS/audit tsikllari |
| `migrations/versions/0015_market_delete_snapshots.py` | Uch funksiya almashtirish + backfill; ikkita muzlatilgan eski ta'rif `downgrade()` uchun |
| `migrations/entities/functions.py` | `CAPTURE_DUE_MARKETS`, `MARKET_DELETE_DRAFT` +5 `DELETE`, `MARKET_ACTIVATE` +profil, `SNAPSHOT_FUNCTIONS` |
| `migrations/entities/__init__.py` | `ALL_TENANT_TABLES` splice + `SNAPSHOT_FUNCTIONS` ni `ALL_ENTITIES` ga |
| `tests/tenancy/test_meta.py` | `PENDING_AUDIT_TRIGGERS` -> bo'sh; `INDEX_EXCEPTIONS` +`uq_snapshots_billable_anchor` |
| `tests/tenancy/test_snapshot_domain_meta.py` | 7 `pg_catalog` invarianti + 2 funksiya-xulq darvozasi (9 test) |
| `tests/fixtures/snapshot_domain.py` | Ikki bozorli seed; A da oltala holat va `ok`+`dark` kadr, B da nazorat qatorlari |
| `tests/integration/test_market_delete_guard.py` | `test_draft_market_deletion_covers_the_snapshot_domain`; quyi chegara 12 -> 17 |

## Sabotaj o'lchovlari — nima qizardi VA nima YASHIL QOLDI

Bu loyihada ikkinchi ustun birinchisidan ko'ra ko'proq ma'lumot bergan — va bu safar u **rejada yo'q darvozani** ochdi.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Xulosa |
|---|---|---|---|---|
| 1 | `CaptureRun` dan `UniqueConstraint(market_id, camera_id, business_date, slot_time)` (faqat MODELDAN) | **Faqat `alembic check`**: «Detected removed unique constraint `uq_capture_runs_market_id_camera_id_business_date_slot_time` on `capture_runs`» | Task 1 ning BARCHA metadata mezonlari; `test_snapshot_domain_meta.py` ning oltala invarianti (reja ularning qizarishini kutgan edi) | ⚠ **Reja noto'g'ri bashorat qilgan.** CAM-05 kafolati faqat MODEL/BAZA DRIFTI orqali qo'riqlanardi — konstrayt ikkalasidan birdan olib tashlansa jimgina yashil qolardi. **Yettinchi invariant qo'shildi** (`85d2b66`) |
| 2 | `PENDING_AUDIT_TRIGGERS` ga ikkala nomni qaytarish | `test_audited_tables_have_trigger` — AYNAN `closed` assertida; xabar ikkala nomni ham aytdi va «ro'yxatdan O'CHIRING» dedi | `test_snapshot_domain_meta.py` ning 8 testi | Ikki tomonlama qulfning `closed` yo'nalishi HAQIQIY sxemada o'lchandi (`04-01` da u faqat sun'iy RED bosqichida o'lchangan edi) |
| 3 | `MARKET_DELETE_DRAFT` dan `DELETE FROM public.alert_events` | `test_cascade_covers_every_table_referencing_markets` — xabarda AYNAN `['alert_events']` | `test_snapshot_domain_meta.py` (9/9) | Kaskad darvozasi meta-darvozadan mustaqil; bitta jadval tushib qolsa ham nomma-nom aytiladi |
| 4 | `MARKET_ACTIVATE` dan slot `INSERT` bloki | `test_activation_writes_the_default_schedule_idempotently` — «profilda 0 ta slot bor, kutilgani 7» | Kaskad testlari; qolgan 8 invariant | ⚠ Reja bu assertni `test_wizard_flow.py` da kutgan edi — u yerda bunday assert YO'Q (pastda, 5-deviatsiya). Darvoza `test_snapshot_domain_meta.py` ga qo'yildi va u AYNAN kutilgan joyda qizardi |

## Bazaviy holat

| O'lchov | Baza (`04-01` dan keyin) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1570 (`04-02` bilan) | **1580** | ✅ +10 (9 yangi test + 1 sabotaj natijasi) |
| tenancy | 417 | **426** | ✅ +9 |
| `ruff` + `ruff format` + `mypy` | toza | **toza** (207 fayl) | ✅ |
| `alembic check` | farq yo'q | **farq yo'q** | ✅ |
| `alembic downgrade 0013 && upgrade head` | — | **exit 0** (ikkala migratsiya uchun ham) | ✅ |
| `git diff services/core-api/pyproject.toml frontend/package.json` | — | **o'zgarish yo'q** | ✅ (T-04-SC) |

## Decisions Made

1. **D-16 tuzilmaviy shaklda** — `04-01` ning o'lchovi (`BILLABLE_ANCHOR_SUPPORTED = true`) o'qildi, taxmin qilinmadi. Trigger varianti kerak bo'lmadi.
2. **`market_activate()` `plpgsql` bo'ldi.** `LANGUAGE sql` tanasi `CREATE FUNCTION` paytida parse qilinadi (`check_function_bodies` standart `on`), bu funksiyani esa `0007_market_domain` MODULNING JORIY ta'rifidan yaratadi. `sql` variantida `0007` `relation "public.snapshot_schedules" does not exist` bilan yiqildi va NOL HOLATDAN qilingan har bir migratsiya to'xtadi. `MARKET_DELETE_DRAFT` `0010` dan beri AYNAN shu xususiyatga tayanadi — ya'ni bu yangi nayrang emas, mavjud konventsiya.
3. **`uq_snapshots_billable_anchor` `INDEX_EXCEPTIONS` da.** U `market_id` bilan boshlana OLMAYDI: 5-fazaning `FOREIGN KEY (snapshot_id, snapshot_is_billable)` i nishonning AYNAN `(id, is_billable)` bo'lishini talab qiladi. Farqi boshqa ikki istisnodan: ular so'rov yo'li, bu esa umuman so'rov yo'li EMAS — `snapshots` ni `market_id` bo'yicha izlaydigan har bir so'rov ikkita boshqa UNIQUE'dan foydalanadi.
4. **`SNAPSHOT_FUNCTIONS` — yangi migratsiya-scope'li ro'yxat.** Reja `capture_due_markets()` ni `ALL_FUNCTIONS`/`GRANT_SIGNATURES` ga qo'shishni aytgan, lekin o'sha ikkalasi `0001_identity` ning MUZLATILGAN to'plami va `0001` ular ustidan tsikl qiladi — qo'shish nol holatdan qilingan migratsiyani mavjud bo'lmagan obyektga `GRANT` berishga majburlab yiqitardi (`ALL_FUNCTIONS` ning O'Z docstringi buni taqiqlaydi).
5. **`snapshots.camera_id` ga kompozit FK qo'shildi** — rejada faqat `capture_run_id` FK'si bor edi. Sabab: `capture_runs.nvr_id` (u ham denormalizatsiya) FK oladi, ya'ni denormalizatsiya tenant chegarasini bo'shatish uchun bahona emas. Kaskad tartibiga ta'sir qilmaydi (`snapshots` `cameras` dan oldin o'chiriladi).
6. **`system_heartbeats` ga RLS QO'YILMADI, lekin `grant_app_dml()` berildi.** Jadvalda `market_id` yo'q, ya'ni tenant predikatini yozib bo'lmaydi; grantsiz esa worker yurak urishini yoza olmasdi va FOUND-06 ning eng pastki qatlami jimgina ishlamay qolardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `market_activate()` `LANGUAGE sql` da butun migratsiya zanjirini yiqitdi**
- **Found during:** Task 3 (GREEN bosqichi)
- **Issue:** Reja `market_activate()` ga snapshot jadvallariga `INSERT` qo'shishni talab qiladi, lekin funksiya `LANGUAGE sql` va uning tanasi `CREATE FUNCTION` PAYTIDA parse qilinadi. `0007_market_domain` esa uni `MARKET_CORE_FUNCTIONS` ustidan tsikl qilib, MODULNING JORIY ta'rifidan yaratadi — ya'ni `0007` da `relation "public.snapshot_schedules" does not exist`. O'lchandi: `tests/tenancy` va `tests/integration` ning HAMMASI `ERROR at setup` bilan tushdi.
- **Fix:** Tana `LANGUAGE plpgsql` ga o'tkazildi (`INSERT ... RETURNING INTO` + `IF v_schedule_id IS NOT NULL`). `plpgsql` tanasi CREATE paytida tekshirilmaydi — bu YANGI nayrang emas: `MARKET_DELETE_DRAFT` `0010_calendar` dan beri aynan shu xususiyatga tayanadi (uning tanasi `cameras`/`snapshots` ga havola qiladi, o'sha jadvallar esa `0012`/`0014` da tug'iladi). Narxi docstringda HALOL yozildi: `0007`–`0015` oynasida tana hali mavjud bo'lmagan jadvallarga havola qiladi va o'sha oynada uni hech kim chaqirmaydi.
- **Verification:** `pytest tests/tenancy tests/integration/...` 100% yashil; nol holatdan `alembic upgrade head` exit 0.
- **Committed in:** `9ad73c5`

**2. [Rule 3 - Blocking] `uq_snapshots_billable_anchor` tenant-indeks invariantini qizartirdi**
- **Found during:** Task 2
- **Issue:** `test_tenant_indexes_lead_with_market_id` qizardi: «`snapshots.uq_snapshots_billable_anchor`: birinchi ustun `id`, `market_id` emas». Reja bu to'qnashuvni ko'rmagan, lekin u TUZILMAVIY: konstrayt 5-fazaning kompozit FK NISHONI va nishon havola qiluvchi ustunlar bilan AYNAN mos kelishi shart — `market_id` qo'shish uni FK uchun yaroqsiz qilardi, ya'ni yagona «tuzatish» yo'li D-16 ning butun kafolatini olib tashlash bo'lardi.
- **Fix:** Nom `INDEX_EXCEPTIONS` ga to'liq sabab bilan qo'shildi, jumladan boshqa ikki istisnodan FARQI (ular so'rov yo'li, bu esa emas) va P9 da'vosining susaymasligi.
- **Verification:** `pytest tests/tenancy` 426/426 yashil; `snapshots` ni `market_id` bo'yicha izlaydigan yo'llar ikkita boshqa `market_id`-bilan-boshlanuvchi UNIQUE'dan foydalanadi.
- **Committed in:** `dea1128`

**3. [Rule 3 - Blocking] `models/market.py` rejaning `files_modified` ida yo'q edi, lekin migratsiya uni talab qildi**
- **Found during:** Task 1
- **Issue:** Task 2 `market_profile` ga `capture_on_closed_days` ustunini qo'shishni talab qiladi (D-10), lekin `models/market.py` `files_modified` da YO'Q. Modelga qo'shilmasa `alembic check` har safar `remove_column` taklif qilardi (§S-2 ning aynan o'sha sinfi) va kimdir uni «tozalash» deb qabul qilishi mumkin edi.
- **Fix:** Ustun modelga ham qo'shildi, D-10 ning ikkala yuzi (kadr olishni boshqaradi, BILLINGNI emas) va UI'da tahrirlanmasligi docstringda yozildi. Fayl parallel ijrochining (`04-04`) to'plamida yo'q — to'qnashuv xavfi nol.
- **Verification:** `alembic check` -> «No new upgrade operations detected».
- **Committed in:** `93efb20`

**4. [Rule 3 - Blocking] `capture_due_markets()` ni `ALL_FUNCTIONS`/`GRANT_SIGNATURES` ga qo'shib bo'lmaydi**
- **Found during:** Task 3
- **Issue:** Reja «`GRANT_SIGNATURES` va `ALL_FUNCTIONS` ro'yxatlariga qo'shiladi» deydi. Lekin ikkalasi ham `0001_identity` ning MUZLATILGAN to'plami va `0001` ular ustidan tsikl qiladi — `ALL_FUNCTIONS` ning O'Z docstringi buni ochiq taqiqlaydi («Keyingi migratsiyalarda qo'shilgan funksiyalar bu ro'yxatga TUSHMAYDI — aks holda `0001` mavjud bo'lmagan obyektga `GRANT` berishga urinardi»).
- **Fix:** `SNAPSHOT_FUNCTIONS` + `SNAPSHOT_GRANT_SIGNATURES` — yangi migratsiya-scope'li juftlik (`AUTH_SUPPORT_FUNCTIONS`/`USER_ADMIN_FUNCTIONS`/`PLATFORM_AUDIT_FUNCTIONS` bilan bir xil naqsh). Autogenerate kuzatuvi uchun `ALL_ENTITIES` ga `*SNAPSHOT_FUNCTIONS` qo'shildi.
- **Verification:** nol holatdan `alembic upgrade head` exit 0; `alembic check` toza; `test_security_definer_functions_pin_search_path` yangi funksiyani avtomatik qamradi.
- **Committed in:** `9ad73c5`

**5. [Rule 2 - Missing Critical] Reja `test_wizard_flow.py` da mavjud bo'lmagan assertga tayangan**
- **Found during:** Task 3 (SABOTAJ 2 ni bajarishga urinilganda)
- **Issue:** Rejaning qabul mezoni va sabotaji «`test_wizard_flow.py` dagi 'faollashtirishdan keyin 7 slot' assertini qizartiradi» deydi. Bunday assert MAVJUD EMAS (fayl 2-fazadan va u `files_modified` da ham yo'q). Ya'ni D-01 ning butun mahsulot qoidasi — «admin hech nima kiritmaydi» — HECH QANDAY darvoza bilan qo'riqlanmasdi: slot `INSERT` i tushib qolsa profil bor-u, kadr olinmasdi va UI «jadval sozlangan» deb ko'rsatardi.
- **Fix:** Ikki xulq darvozasi `tests/tenancy/test_snapshot_domain_meta.py` ga qo'shildi (rejaning O'Z fayli): `test_activation_writes_the_default_schedule_idempotently` (7 slot + idempotentlik) va `test_capture_due_markets_exposes_only_identifiers` (tor yuza + predikatning uch holati). Fayl docstringi «olti invariant» -> «yetti invariant + ikki xulq darvozasi» deb yangilandi.
- **Verification:** 4-sabotaj AYNAN kutilgan assertda qizardi («profilda 0 ta slot bor, kutilgani 7»); `test_wizard_flow.py` esa TEGILMADI va 31/31 yashil qoldi.
- **Committed in:** `9ad73c5`

**6. [Rule 2 - Missing Critical] CAM-05 kaliti hech qanday `pg_catalog` darvozasi bilan qo'riqlanmagan edi**
- **Found during:** Yakuniy sabotaj o'lchovi (1-sabotaj)
- **Issue:** Reja «`CaptureRun` dan `UniqueConstraint(...)` ni olib tashlash `test_snapshot_domain_meta.py` ni AYNAN qizartiradi» deb bashorat qilgan. O'lchov TESKARI natija berdi: oltala invariant ham YASHIL qoldi va yagona qizargan darvoza `alembic check` bo'ldi. Ya'ni fazaning ikkinchi eng qimmat da'vosi (must_haves truth #2 — «bir slot uchun ikkinchi qator MUMKIN EMAS») faqat MODEL/BAZA DRIFTI orqali qo'riqlanardi: konstrayt migratsiya va modeldan BIRDAN olib tashlansa `alembic check` ham jim qolardi.
- **Fix:** Yettinchi invariant qo'shildi — `test_capture_runs_key_makes_a_slot_unrepeatable`, `pg_catalog` dan ustunlar TARTIBI bilan o'qiydi. Docstringda o'lchovning o'zi va `alembic check` ning nega yetarli emasligi yozildi.
- **Verification:** Test bazadagi HAQIQIY konstraytni aynan `['market_id','camera_id','business_date','slot_time']` tartibida topdi (vakuum emas); `pytest tests/tenancy` 426/426.
- **Committed in:** `85d2b66`

**7. [Rule 1 - Bug] Kompozit FK nomi 63 baytdan uzun bo'lib, jimgina kesilardi**
- **Found during:** Task 1
- **Issue:** `snapshot_schedule_slots` ning `(market_id, schedule_id)` FK'si uchun `NAMING_CONVENTION` 67 belgilik nom beradi. PostgreSQL identifikatorni 63 baytga JIMGINA kesadi — natijada model metadata'sidagi nom va bazadagi nom farq qilib, `alembic check` HAR SAFAR soxta diff berardi.
- **Fix:** Nom qo'lda berildi (`fk_snapshot_schedule_slots_schedule` — `04-RESEARCH.md` §A.1 dagi bilan bir xil) va sabab ikkala tomonda ham izohda yozildi. Qolgan barcha konstrayt nomlari uzunligi oldindan sanab chiqildi.
- **Verification:** `alembic check` -> farq yo'q.
- **Committed in:** `93efb20` (model) / `dea1128` (migratsiya)

**8. [Rule 3 - Blocking] Ruff `S608` yolg'on-musbati ikki joyda**
- **Found during:** Task 3
- **Issue:** `MARKET_ACTIVATE` ning ta'rifi va `0015` ning backfill'i f-satr bilan quriladi (slot literallari `DEFAULT_SNAPSHOT_SLOTS` dan hosil qilinadi) va ruff ularni «string-based query construction» deb belgiladi.
- **Fix:** `# noqa: S608` + sabab izohi (`tuple[time, ...]` modul konstantasi, tashqi kirish EMAS). `test_meta.py` dagi «matnni konstantaga ko'chirish» yo'li bu yerda ishlamaydi — SQL literallar HAQIQATAN interpolatsiya qilinadi va ular `DEFAULT_SNAPSHOT_SLOTS` bilan bitta manbada qolishi kerak.
- **Verification:** `ruff check .` -> «All checks passed!».
- **Committed in:** `9ad73c5`

**9. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**
- **Found during:** Boshlanish
- **Issue:** Ikkala fayl ham `.gitignore` da, ya'ni ular worktree'ga ko'chmaydi. Usiz `docker compose` barcha sirlarni bo'sh satr bilan almashtirardi va `npm run migrate` autentifikatsiyasiz yiqilardi.
- **Fix:** `.env` asosiy repodan nusxalandi; `s3.json` `.example` dan yaratildi (aks holda Docker bind-mount o'sha yo'lda KATALOG yaratardi).
- **Verification:** `git check-ignore -v` ikkalasini ham tasdiqladi — repoga tushmaydi; `npm run migrate` exit 0.
- **Committed in:** commit qilinmadi (ataylab — ikkalasi ham gitignore ostida)

---

**Total deviations:** 9 auto-fixed (1× Rule 1 bug, 2× Rule 2 missing-critical, 6× Rule 3 blocking)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Uchtasi (1, 4, 5) rejaning O'ZIDAGI bajarib bo'lmaydigan yoki mavjud kodga zid bandlarini NIYATI bo'yicha bajardi. Ikkitasi (5, 6) rejaning bashoratlari noto'g'ri bo'lgan joyda YETISHMAYOTGAN DARVOZANI qo'shdi — ya'ni o'lchov reja matnidan ustun qo'yildi. Qolgani bo'lmasa migratsiya yoki `alembic check` jimgina buzilardi.

### TDD tartibi

Task 3 `tdd="true"` va u TO'LIQ RED -> GREEN juftligida berildi (`4dd5170` -> `9ad73c5`). RED o'lchovi ikki mustaqil darvozani ko'rsatdi: statik (kaskadda beshta nom yo'q) va dinamik (`ForeignKeyViolation`, `capture_runs` -> `cameras`) — ikkinchisi tartib talabining YAGONA dalili. Task 1 ham `tdd="true"` edi, lekin u model qatlami (yangi xulq emas, sxema e'loni) bo'lgani uchun bitta commitda berildi; uning darvozalari Task 2/Task 3 da tug'ildi va sabotaj bilan o'lchandi.

## Issues Encountered

- **Reja `DATABASE_URL_SYNC` muhit o'zgaruvchisiga tayangan qabul mezonlarini bergan** (Task 2/Task 3). Bunday o'zgaruvchi loyihada UMUMAN yo'q — testlar `testcontainers` bilan o'z Postgres'ini ko'taradi. Mezonlarning NIYATI bajarildi: konstraytlar migratsiyalangan bazadan `migrate` konteyneri orqali `MIGRATION_DATABASE_URL` bilan o'lchandi (`uq_snapshots_billable_anchor`, `attgenerated='s'`, `EXCLUDE` soni, audit triggerlari, `system_heartbeats` grantlari) VA bir martalik tekshiruv DOIMIY darvozaga aylantirildi (`test_snapshot_domain_meta.py`).
- **`db` konteyneri worktree'dan birinchi `npm run migrate` da qayta yaratildi** (compose bind-mount yo'llari farq qilgani uchun) va baza `0011` dan qayta migratsiyalandi. Parallel ijrochi (`04-04`) faqat `tests/unit` bilan ishlaydi va bazaga tegmaydi, ya'ni shovqin xavfi nol — lekin fakt shu yerda qayd etiladi.
- **`ruff format` uch marta o'z tuzatishini kiritdi** (satr uzunligi/`with` birlashtirish). Har safar `ruff check` + `mypy` qayta yugurtirildi.

## Known Stubs

Yo'q. Bu reja sxema qatlamini beradi va har bir kafolat o'z darvozasi bilan birga keldi.

⚠ **Stub bo'lmagan, lekin ochiq qolgan ikki band (ikkalasining ham egasi bor):**
1. `capture_due_markets()` HALI CHAQIRILMAYDI — tik `04-07` da tug'iladi. Funksiya va uning darvozalari tayyor turibdi.
2. `system_heartbeats` ga HALI YOZILMAYDI — `/internal/self-check` va yurak urishi `04-07`/`04-11` da. Jadval, grantlar va `GLOBAL_TABLES` yozuvi tayyor.

## Threat Flags

Yo'q — bu reja yangi tarmoq endpointi yoki auth yo'li qo'shmadi. Aksincha, u to'rtta tuzilmaviy mitigatsiyani o'rnatdi va uchalasi `pg_catalog` dan o'lchanadi: T-04-17 (`UNIQUE (id, is_billable)` + `attgenerated='s'`), T-04-18 (CAM-05 kaliti), T-04-19 (`EXCLUDE`), T-04-20 (kaskad to'liqligi). T-04-16 (`SECURITY DEFINER` yuzasi) `pg_get_functiondef()` ustidan tekshiriladi.

⚠ **Bitta yangi `SECURITY DEFINER` funksiya qo'shildi** (`capture_due_markets()`) — u RLS'ni chetlab o'tadi. Yuzasi ikki ustun bilan cheklandi, `SET search_path` qadaldi, `PUBLIC` dan `REVOKE` qilindi va uchala shart ham testda qulflandi.

## Next Phase Readiness

**`04-05`/`04-09`/`04-10` uchun:** `snapshot_schedules`/`snapshot_schedule_slots` RLS ostida; `market_activate()` standart profilni yozadi, ya'ni `today_and_tomorrow()` bo'sh jadval holatiga tushmaydi. `market_profile.capture_on_closed_days` mavjud (`ScheduleView` uni o'qiydi).

**`04-06`/`04-07`/`04-08` uchun:** `capture_runs` (lease ustunlari, ikkala qisman indeks), `snapshots` (sifat o'lchovlari, `object_key`, `storage_tier`) va `capture_due_markets()` tayyor. `nvr_devices.capture_method`/`max_concurrent_captures`/`capture_stagger_ms`/`observed_stream_limit` va `cameras.capture_stream` — fan-out sozlamalari.

**`04-11` uchun:** `alert_events` (debounce indeksi bilan) va `system_heartbeats` tayyor.

**5-faza uchun:** `uq_snapshots_billable_anchor` — `occupancy_events` ning `FOREIGN KEY (snapshot_id, snapshot_is_billable) REFERENCES snapshots (id, is_billable)` i uchun. Nishonning shakli, ustunlar tartibi va `is_billable` ning hosila ekanligi uchta alohida test bilan qulflangan.

**Bloklovchi yo'q.**

## Self-Check: PASSED

Yaratilgan beshala fayl diskda tekshirildi; commit hashlari `git log` da tasdiqlandi (`93efb20`, `dea1128`, `4dd5170`, `9ad73c5`, `85d2b66`); yakuniy `pytest -q` exit 0 (1580 test); `ruff check . && ruff format --check . && mypy .` toza (207 fayl); `alembic check` farq topmadi; ikkala migratsiya uchun ham `downgrade` -> `upgrade` aylanmasi exit 0.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-04*
