---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 02
subsystem: data-model
tags: [reconciliation, notification, outbox, telegram-binding, rls, migration]
requires:
  - "0020_billing_domain — uq_billing_anomalies_market_id_id / uq_daily_charges_market_id_id (kompozit FK nishonlari)"
  - "0022_billing_late_review — down_revision"
  - "migrations/entities: tenant_policy / owner_bootstrap_policy generatsiyasi"
provides:
  - "ReconciliationCaseStatus / ReconciliationSubjectKind / OutboxKind / OutboxRecipientKind / OutboxStatus"
  - "reconciliation_cases / reconciliation_case_events / notification_outbox / vendor_telegram_bindings / market_notification_settings"
  - "NOTIFICATION_TENANT_TABLES / NOTIFICATION_AUDITED_TABLES / NOTIFICATION_DELETE_ORDER"
  - "case_event_immutable() — T-07-09 mitigatsiyasi"
affects:
  - "07-04 (sxema darvozalari), 07-05…07-13 (case oqimi, outbox jo'natuvchisi, bot)"
tech-stack:
  added: []
  patterns:
    - "yopiq StrEnum + enumdan HOSILA CHECK (0020 naqshi)"
    - "ikki mustaqil kompozit FK + XOR CHECK + yopiq diskriminator (DQ-5)"
    - "qisman UNIQUE indeks bilan strukturaviy idempotentlik (D-21)"
    - "kaskad kengaytmasi AYNI migratsiyada (juftlik EMAS)"
key-files:
  created:
    - packages/sbozor-core/sbozor_core/models/notification.py
    - migrations/versions/0023_notification_domain.py
    - tests/unit/test_reconciliation_enums.py
  modified:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - migrations/entities/__init__.py
    - migrations/entities/triggers.py
    - migrations/entities/functions.py
    - tests/unit/test_enums.py
    - tests/integration/test_market_delete_guard.py
decisions:
  - "Kaskad AYNI migratsiyada kengaytirildi — 0021 juftligi TAKRORLANMADI, ya'ni kaskad darvozasi hech qachon qizil bo'lmadi"
  - "case_event_immutable() qo'shildi — T-07-09 ni qo'riqchisiz ifodalab bo'lmasdi"
  - "KNOWN_TENANT_TABLE_COUNT 29 -> 34 — ko'tarilmasa yangi jadvallar FK'siz yaratilganda ham darvoza yashil qolardi"
  - "Taqiqlangan literal (qoldiq ustuni nomi, kasrli tip) izohda ham yozilmadi — 03-07 darsi"
metrics:
  duration: ~150 min
  completed: 2026-08-12
  tasks: 3
  files: 11
---

# Phase 7 Plan 02: Bildirishnoma domenining ma'lumot poydevori — Summary

Fazaning butun ma'lumot poydevori bitta migratsiyada tug'ildi: besh yopiq
enum, besh tiplangan model va `0023` — RLS, ikki mustaqil kompozit FK, XOR
diskriminatori va ikki strukturaviy idempotentlik cheklovi bilan.

## Nima qurildi

**Task 1 — besh enum (`004a8ee`).** `ReconciliationCaseStatus` (yopiq
to'rtlik), `ReconciliationSubjectKind`, `OutboxKind`,
`OutboxRecipientKind`, `OutboxStatus`. Qiymatlar inglizcha, ko'rsatiladigan
matn i18n kaliti — `PaymentKind` / `AnomalyKind` bilan bir xil shakl.
`delivered` ning ma'nosi kodda so'z bilan yozilgan («Telegram 200 qaytardi
va `message_id` berdi»), «o'qildi»/«ko'rildi» esa **salbiy da'vo** bilan
taqiqlangan.

**Task 2 — besh model + sxema shartnomasi (`c119993`).** `models/billing.py`
uslubida; `reconciliation_cases` uchun beshta struktura sharti, outbox
uchun esa **yo'q ustunlar docstringda nomma-nom** sabablangan.
`reconciliation_cases` `AUDITED_TABLES` ga qo'shildi; qolgan to'rttasi
ATAYIN chiqarildi va har biri alohida sabab bilan yozildi.

**Task 3 — `0023_notification_domain` (`0597ffe`).** Besh jadval, RLS
`ENABLE`+`FORCE`+tenant policy, `case_event_immutable()` qo'riqchisi va
`market_delete_draft(uuid)` kaskadining kengaytmasi.

## O'lchangan dalillar

Quyidagilar HAQIQIY `postgres:18.4` da, bir martalik zond bilan o'lchandi
(zond repoga qo'shilmadi — xulq testlari `07-04` ning fayli):

| Da'vo | Natija |
|---|---|
| `anomaly_id` va `charge_id` ikkalasi `NULL` | `CheckViolation (subject_is_exclusive)` |
| `anomaly_id` VA `charge_id` birga | `CheckViolation (subject_is_exclusive)` |
| `subject_kind='anomaly'` + `charge_id` | `CheckViolation (subject_kind_matches_target)` |
| takroriy `(market_id, dedupe_key)` | `UniqueViolation` |
| `market_director` + `vendor_id` | `CheckViolation (recipient_matches_vendor)` |
| bir sotuvchida IKKINCHI FAOL bog'lanish | `UniqueViolation` |
| bekor qilingandan keyin qayta ulanish (D-26c) | **RUXSAT** (kutilganidek) |
| `overdue_days = 0` | `CheckViolation` |
| beshala jadvalda RLS | `ENABLE` + `FORCE` ✓ |
| `market_delete_draft()` beshala jadvalni qamradi | ✓ (chaqiruv xatosiz) |
| yangi `SECURITY DEFINER` funksiya | **YO'Q** (22 ta, o'zgarmadi) |
| `upgrade` / `downgrade -1` / `upgrade` | qaytariluvchan ✓ |

**Sabotaj (Task 1, reja talab qilgan).** `ReconciliationCaseStatus` ga
`OTHER = "other"` vaqtincha qo'shildi. Natija: AYNAN ikki test qizardi —
`test_case_status_is_a_closed_set_of_four` **va**
`test_case_status_has_no_escape_hatch`. Boshqa hech nima qizarmadi, ya'ni
ikkala darvoza ham mustaqil ishlaydi. Sabotaj o'lchovdan keyin olib
tashlandi.

**Darvozalar:** `pytest tests/tenancy -q` (672 test) yashil ·
`pytest tests/unit -q` yashil · `ruff check` + `ruff format --check` +
`mypy` (310 fayl) toza · grep darvozalari (`balance` / `float(` /
`Decimal` / `round(` / `other|custom` + `reconcil`) → hammasi **0**.

## Rejadan chetlanishlar

### Rule 2/3 — avtomatik qo'shilgan, zarur bo'lgani uchun

**1. [Rule 3] `migrations/entities/triggers.py` — `case_event_immutable()`**
- **Topildi:** Task 3 `reconciliation_case_events` uchun o'zgarmaslik
  triggerini talab qiladi, lekin trigger FUNKSIYASI `files_modified` da
  yo'q edi. `CREATE TRIGGER ... EXECUTE FUNCTION` mavjud funksiyani talab
  qiladi.
- **Yechim:** funksiya `triggers.py` ga qo'shildi (`CHARGE_IMMUTABLE`
  nusxasi) + `NOTIFICATION_TRIGGER_FUNCTIONS` reyestri va
  `ALL_TRIGGER_FUNCTIONS` ga splice (usiz `test_autogenerate_is_empty`
  qizarardi).
- **Commit:** `0597ffe`

**2. [Rule 3] `migrations/entities/functions.py` — kaskad tanasi**
- **Topildi:** Task 3 ochiq talab qiladi («`market_delete_draft(uuid)`
  tanasi qayta yoziladi»), lekin fayl `files_modified` da yo'q edi.
- **Yechim:** bildirishnoma bloki **billing blokidan OLDIN** qo'shildi —
  `reconciliation_cases` `billing_anomalies` va `daily_charges` ga
  tayanadi. Imzo TEGILMADI (T-06-22).
- **Commit:** `0597ffe`

**3. [Rule 2] `KNOWN_TENANT_TABLE_COUNT` 29 → 34**
- **Topildi:** quyi chegara ko'tarilmasa beshala yangi jadval `markets` ga
  FK'siz yaratilgan taqdirda ham
  `test_reference_query_actually_finds_the_tenant_tables` yashil qolardi.
  Faylning O'Z izohi buni MAJBURIY deb yozgan (`06-04` / T3 presedenti).
- **Commit:** `0597ffe`

**4. [Rule 1] Taqiqlangan literal izohdan olib tashlandi**
- **Topildi:** `models/notification.py` ning docstringi taqiqni
  TUSHUNTIRISH uchun qoldiq ustuni nomini va kasrli tip nomlarini literal
  yozgan edi — natijada rejaning O'Z grep darvozasi (`→ 0`) **2** va **1**
  qaytardi.
- **Yechim:** matn qayta yozildi (03-07 darsi: sodda grep izohni koddan
  ajratmaydi). Ro'yxatning o'zi `07-04` ning
  `FORBIDDEN_OUTBOX_COLUMN_TOKENS` reyestrida `information_schema` to'plam
  tengligi bilan o'lchanadi — da'vo susaymadi, o'lchanadigan joyga ko'chdi.
- **Commit:** `c119993`

### Rejadan ongli chetlanish (struktura)

**Kaskad AYNI migratsiyada kengaytirildi — juftlik EMAS.** `0012`→`0013`,
`0014`→`0015`, `0018`→`0019`, `0020`→`0021` naqshida ikkinchi migratsiya
faqat funksiya tanasini almashtiradi va **oradagi holatda kaskad darvozasi
ataylab qizil turadi**. `0023` ikkala qadamni ham o'z oynasida bajaradi,
ya'ni `test_cascade_covers_every_table_referencing_markets` **hech qachon
qizil bo'lmadi** — `06-04` / T2 ning splice qarori (OP-3) bilan bir xil
mulohaza. Reja `0024` ni talab qilmagan, shuning uchun bu kengaytma emas,
soddalashtirish.

## Ochiq bandlar

**1. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Node yarmi (`npm run test:fast`) **182/182 yashil, 1.4 s** (byudjet 200 s).
Frontend yarmi (`npm --prefix frontend test`, vitest) **umuman ishga
tushmadi**: worktree'da `node_modules` YO'Q (gitignored, `npm install`
qilinmagan). Bu **muhit bo'shlig'i, kod nuqsoni emas** va u bu rejaning
o'zgarishlaridan MUSTAQIL: `git diff --name-only` bo'yicha reja **birorta
frontend faylga tegmagan** (11 fayl — hammasi Python, migratsiya yoki
Python testi). Egasi: orkestrator (merge'dan keyin asosiy repoda
`node_modules` mavjud).

**2. `market_notification_settings` auditsiz va bu OCHIQ QARZ.** Sabab
texnik: PK `market_id`, ya'ni `id uuid` ustuni yo'q va `fn_audit_row()`
unda har DML da yiqilardi. Quiet hours ni kengaytirish eslatmani AMALDA
o'chirish yo'li, ya'ni u bir kun audit talab qilishi mumkin. O'shanda
yechim `id uuid` ustuni qo'shish bo'ladi, audit funksiyasini o'zgartirish
EMAS. Sabab `schema_contract.AUDITED_TABLES` docstringida yozib qo'yildi.

**3. Case tarixining o'zgarmasligi XULQ bo'yicha o'lchanmadi.** Trigger
ULANGANI tekshirildi (`trg_case_event_immutable` mavjud), lekin `UPDATE`
ning haqiqatan rad etilishi o'lchanmadi — u haqiqiy case qatorini talab
qiladi, u esa `daily_charges` / `billing_anomalies` seed'ini (kompozit FK).
O'sha fixture `07-04` ning fayli (`tests/fixtures/notification_domain.py`).

## Known Stubs

Yo'q. Bu reja faqat sxema va tiplangan ta'riflar beradi; birorta UI yoki
API yuzasi qurilmagan va birorta bo'sh qiymat renderga oqmaydi.

## Threat Flags

Yo'q. Yangi tashqi yuza (endpoint, auth yo'li, fayl kirishi) ochilmadi;
beshala jadval RLS ostida va yangi `SECURITY DEFINER` funksiya qo'shilmadi.
