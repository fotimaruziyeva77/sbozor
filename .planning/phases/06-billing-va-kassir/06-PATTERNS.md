# Phase 6: Billing va kassir — Pattern Map

**Mapped:** 2026-08-10
**Files analyzed:** ~70 (yangi yoki o'zgaradigan; §1 da guruhlangan)
**Analogs found:** 56 / 70 — **10 shakl uchun analog YO'Q yoki qisman** (§5)

> **Bu hujjatning maqsadi bitta:** ijrochi naqsh o'ylab topmasin — u aniq
> `fayl:qator` dan nusxa olsin, va **artefaktni ro'yxatga olishni unutmasin**.
>
> **5-FAZADAN FARQI.** 05-PATTERNS.md ning eng qimmat qismi §S-1 («yangi
> tenant jadvali — olti joy») edi. Bu fazada **artefakt turlari ko'p**
> (jadval · migratsiya · trigger · marshrut · cron · huquq · enum · xato
> kodi · komponent katalogi · so'rov moduli · i18n namespace · DROP
> qilinadigan funksiya) va ularning **har biri o'z reyestr to'plamiga**
> ega. Shuning uchun bu hujjatning yuragi — **§2 Ro'yxatga olish
> cheklistlari** va **§6 Tartib juftliklari**.
>
> ⛔ **ENG QIMMAT UCH BAND:**
> **§6 OP-1** (`0020` qo'ngan zahoti kaskad darvozasi qizaradi — `0021`
> BIR TO'LQINDA bo'lishi shart), **§6 OP-2** (orfan `SECURITY DEFINER`
> funksiyalarni DROP qilish **uchta reyestrni** bir commitda talab qiladi,
> aks holda `test_due_markets_functions_expose_only_identifiers` «bazada
> topilmadi» bilan qizaradi), **§2 R-1/7-band** (`ALL_TENANT_TABLES`
> splice AYNAN `0020` bilan bitta commitda — oldin ham, keyin ham qizil).
>
> ⚠ **UCH O'LCHOV REJANI DARHOL O'ZGARTIRADI** — §0.1.

---

## 0. Umumiy majburiy konventsiyalar

`04-PATTERNS.md` §0 va `05-PATTERNS.md` §0 jadvallari **to'liq,
o'zgarishsiz amal qiladi**. Quyida faqat **shu fazaga xos** yoki **shu
sessiyada o'lchangan** bandlar.

| Qoida | Manba (`path:line`) | Buzilsa nima bo'ladi |
|---|---|---|
| Har modul **fayl-darajasidagi docstring** bilan, «nega shunday» tushuntiriladi | `services/core-api/app/jobs/day_close.py:1-74` | Review'dan o'tmaydi |
| Izohlar, docstring, xato matnlari — **uz-Latn** | butun 1–5 faza kodi | Uslub ajraladi |
| `from __future__ import annotations`; `__all__`; `if TYPE_CHECKING:` | `day_close.py:76-108` | ruff/mypy shuni kutadi |
| Pul — **`BIGINT` so'm ↔ `int`**; `float`/`Decimal` **TAQIQ** | `packages/sbozor-core/sbozor_core/money.py:65-85` | `TypeError` chegarada + G-3 |
| Manfiy summa **YOZILMAYDI** — musbat kattalik + `kind`/`direction` | `money.py:65-85` + `tests/tenancy/test_meta.py:1346` | `ValueError` / meta-test qizil |
| PG `ENUM` tipi **ISHLATILMAYDI** — `text` + enum'dan **HOSILA** `CHECK` | `models/occupancy.py:60-64`, `:206-248` | Ikkinchi konventsiya tug'iladi |
| `timestamptz` + `ZoneInfo("Asia/Tashkent")`; naive `datetime` **TAQIQ** | `sbozor_core/timeutil.py:63-90` | `ValueError` |
| Biznes-kun **DB'da**, **ikki argumentli** `AT TIME ZONE` MAJBURIY | `migrations/helpers.py:324-332` | `generation expression is not immutable` |
| `market_id` ustunida inline `ForeignKey` **YOZILMAYDI** | `models/base.py::market_fk_column()` | Konventsiya buziladi |
| Har indeks/UNIQUE `market_id` bilan **boshlanadi**; istisno `INDEX_EXCEPTIONS` ga **sabab bilan** | `tests/tenancy/test_meta.py:45-160`, `:510` | `test_tenant_indexes_lead_with_market_id` qizil |
| Frontend: **Next.js 16 hujjatini `frontend/node_modules/next/dist/docs/` dan o'qing** yozishdan oldin | `frontend/AGENTS.md` | Eskirgan API |
| Vitest **faqat `.test.tsx`** ni yig'adi (`.ts` JIMGINA tushib qoladi) | `frontend/vitest.config.ts:34` (05-PATTERNS M-2) | Test hech qachon ishlamaydi |
| `node --test` **TypeScript'ni import qila olmaydi** — `scripts/*.test.mjs` fayllarni **MATN** sifatida o'qiydi | `frontend/package.json:14` (05-PATTERNS M-3) | Darvoza yozilmaydi |

### 0.1 — Uch o'lchov, uchalasi rejani darhol o'zgartiradi

| # | O'lchov (2026-08-10, kodni o'zim o'qidim) | Manba | Rejaga ta'siri |
|---|---|---|---|
| **M-A** | ⛔ **`test_due_markets_functions_expose_only_identifiers` funksiyaning MAVJUDLIGINI talab qiladi:** `assert row is not None, "bazada topilmadi"` | `tests/tenancy/test_occupancy_domain_meta.py:558-564` | C-11 ning DROP qarori **bu testni qizartiradi**. `DEFINER_SURFACES` (`:75-79`) **shu commitda** bo'shatilishi shart — §6 OP-2 |
| **M-B** | ⛔ **`error-codes.test.mjs` bandlik reyestri uchun ANIQ SON talab qiladi:** `assert.equal(occupancyConstants.size, 15)` va `ZONE_ERROR_CODES: expected 9`, `REVIEW_ERROR_CODES: expected 6` | `frontend/scripts/error-codes.test.mjs:795-818` | Yangi xato kodi `occupancy_errors.py` ga **QO'SHILMAYDI** — u **yangi** `billing_errors.py` ga tushadi va `error-codes.test.mjs` ga **yangi blok** yoziladi (§2 R-8) |
| **M-C** | ⛔ **`billing_close` yurak urishining yo'qligi bugun HECH QAYERDA ko'rinmaydi.** `EXPECTED_COMPONENTS` = `("capture_tick","alert_sweep","retention","backup","cv_detect")` — `day_close` u yerda **YO'Q**; `alert_sweep` faqat `backup` va `retention` ni kuzatadi | `app/api/internal/self_check.py:108-114`; `app/jobs/alerting.py:607-611` | ⚠ **06-RESEARCH Pitfall 10 ning da'vosi bugun ROST EMAS.** Agar yurak urishi ko'rinishi kerak bo'lsa, `EXPECTED_COMPONENTS` **va** `alerting.py::watched` **ikkalasiga** `billing_close` qo'shiladi. Aks holda «cron o'chib qolgan» holati jimgina qoladi (§5 G-10) |

---

## 1. File Classification

> **Rol** · **Data flow** · **Eng yaqin analog (`path:line`)** · **Moslik**.
> `MOD` = mavjud fayl kengaytiriladi.

### 1.1 Backend — sxema qatlami

| Yangi/o'zgaradigan fayl | Rol | Data flow | Eng yaqin analog | Moslik |
|---|---|---|---|---|
| `packages/sbozor-core/sbozor_core/models/billing.py` | model | CRUD + ledger (append-only) | `models/occupancy.py:1-1028` (**to'liq shablon**, 6 klass) | **exact** |
| `.../models/__init__.py` (MOD) | model-barrel | — | o'zi (`:1-8` docstring qoidasi) | **exact** |
| `.../enums.py` (MOD — `PaymentKind`, `PaymentMethod`, `AdjustmentDirection`, `AdjustmentReason`, `ReversalReason`, `AnomalyKind`, `ShiftStatus` + `AuditAction` a'zolari) | enum | — | o'zi (`enums.py:442-464`) | **exact** |
| `.../schema_contract.py` (MOD — `AUDITED_TABLES`; `FINANCIAL_TABLES` **tegilmaydi**) | registry | — | o'zi (`:128-252`) | **exact** |
| `.../billing.py` (SOF: `billable_from_slots()`, `variance()`) | utility | transform | `sbozor_core/occupancy.py:100-273` | **exact** |
| `migrations/entities/__init__.py` (MOD — `BILLING_TENANT_TABLES`, `BILLING_AUDITED_TABLES`, `BILLING_DELETE_ORDER`, `ALL_TENANT_TABLES`) | registry | — | o'zi (`:297-424`, 5-faza bloki) | **exact** |
| `migrations/entities/triggers.py` (MOD — `charge_immutable()`, `payment_immutable()`, `shift_declaration_immutable()`, `BILLING_TRIGGER_FUNCTIONS`) | db-trigger fn | — | `triggers.py:468-518` (`OCCUPANCY_EVENT_IMMUTABLE`) | **exact** |
| `migrations/entities/functions.py` (MOD — `OCCUPANCY_FUNCTIONS`/`OCCUPANCY_GRANT_SIGNATURES` **bo'shatiladi**) | registry | — | `functions.py:1771-1793` | **partial** (§5.9) |
| `migrations/versions/0020_billing_domain.py` | migration | DDL + RLS + audit + trigger | `0018_occupancy_domain.py:160-796` (**verbatim shablon**) | **exact** |
| `migrations/versions/0021_market_delete_billing.py` | migration | funksiya almashtirish | `0019_market_delete_occupancy.py:1-163` (**verbatim shablon**) | **exact** |
| `migrations/versions/0018_occupancy_domain.py` (MOD — muzlatilgan reyestr nusxasi) | migration | — | `0019:71-137` (`MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY` naqshi, **teskari yo'nalishda**) | **partial** (§5.9) |

### 1.2 Backend — `core-api` ilova qatlami

| Fayl | Rol | Data flow | Analog | Moslik |
|---|---|---|---|---|
| `app/jobs/billing_close.py` | job | batch | `app/jobs/day_close.py:1-354` (**verbatim**) | **exact** |
| `app/repositories/billing_repo.py` (`resolve_stall_day_money()`, hisob yozish, balans) | repository | CRUD + report | `occupancy_repo.py:364-448` (CTE) + `stall_repo.py:582-647` (LATERAL tarif) | **exact** |
| `app/repositories/payment_repo.py` (idempotent INSERT + qayta SELECT, storno) | repository | idempotent write | `capture_repo.py:270-378` (`ON CONFLICT ... RETURNING`) + `nvr_repo.py:506-532` («poyga DB ga») | **partial** — qayta `SELECT` shakli **repoda YO'Q** (§5.1) |
| `app/repositories/shift_repo.py` | repository | CRUD | `review_repo.py` + `alert_repo.py` | role-match |
| `app/api/v1/billing.py` (`GET /billing/pending`, `/charges`, `/anomalies`) | router | request-response | `app/api/v1/occupancy.py:1-269` (**REPORT_VIEW, kun bo'yicha, imzo aliasi**) | **exact** |
| `app/api/v1/payments.py` (`POST /payments`, `POST /payments/{id}/reverse`, `GET /payments/recent`) | router | request-response | `app/api/v1/reviews.py:419-503` (POST + 409) | role-match |
| `app/api/v1/shifts.py` (`POST /shifts`, `GET /shifts/open`, `POST /shifts/{id}/close`, `GET /shifts`) | router | CRUD | `reviews.py` + `schedules.py` | role-match |
| `app/schemas.py` (MOD) | schema | — | `schemas.py:2521-2570` (`BlindItemResponse` — **maydon E'LON QILINMAYDI** naqshi) | **exact** |
| `app/security/rbac.py` (MOD — 2 huquq) | matrix | — | o'zi (`:112-134`, `:196-218`) | **exact** |
| `app/services/billing_errors.py` | registry | — | `app/services/occupancy_errors.py:1-200` | **exact** |
| `app/worker.py` (MOD — `BILLING_CLOSE_CRON` + `billing_close_task`) | bootstrap | event-driven | `worker.py:410-440` (cron const) + `:860-878` (yupqa qobiq) | **exact** |
| `app/main.py` (MOD — 3 `include_router`) | bootstrap | — | `main.py:240-257` (izoh bilan prefiks qarori) | **exact** |

### 1.3 Frontend

| Fayl | Rol | Analog | Moslik |
|---|---|---|---|
| `app/[locale]/(app)/collect/page.tsx`, `collect/shift/page.tsx`, `billing/page.tsx` | page (client) | `app/[locale]/(app)/occupancy/page.tsx:1-40` | **exact** |
| `components/collect/collect-session.tsx` | component (flow) | — | **analog YO'Q** (§5.5) |
| `components/collect/stall-lookup.tsx` | component (navigator) | — | **analog YO'Q** (§5.6) |
| `components/collect/payment-bar.tsx` | component | `components/review/decision-bar.tsx:1-60` + `blind-audit/blind-session.tsx:85-137` | **exact** (qulf) |
| `components/collect/reason-dialog.tsx` | component (dialog) | `ui/dialog.tsx` + `ui/select.tsx` | role-match |
| `components/collect/pending-card.tsx`, `payment-row.tsx`, `shift-open-card.tsx`, `shift-close-form.tsx` | component | `components/occupancy/stall-day-list.tsx`, `round-summary.tsx` | role-match |
| `components/billing/charge-list.tsx`, `anomaly-list.tsx`, `variance-list.tsx`, `pending-summary.tsx`, `day-picker.tsx` | component (list) | `components/occupancy/day-breakdown.tsx`, `stall-day-list.tsx`; `components/snapshots/day-picker.tsx` (**qayta ishlatiladi**) | **exact** |
| `components/billing/charge-detail-dialog.tsx` | component (dialog) | — | **analog YO'Q** (§5.7) |
| `components/billing/variance-cell.tsx` | component | — | **analog YO'Q** (§5.4) |
| `lib/billing-pending-queries.ts` | data-access | `lib/blind-audit-queries.ts:80-208` (**`gcTime:0` + `removeQueries` juftligi**) | **exact** |
| `lib/billing-charge-queries.ts`, `lib/shift-queries.ts`, `lib/payment-queries.ts` | data-access | `lib/occupancy-queries.ts:41-210` | **exact** |
| `lib/billing-errors.ts` | registry | `lib/zone-errors.ts` | **exact** |
| `lib/api-types.ts` (MOD — 4 enum ko'zgusi, `soumSchema` qayta ishlatiladi) | schema | o'zi (`:45`, `:1552`, `:1632`) | **exact** |
| `lib/rbac.ts` (MOD — 2 huquq) | matrix | o'zi (`:50-113`) | **exact** |
| `components/shell/app-shell.tsx` (MOD — 2 `NAV_ITEMS`) | nav | o'zi (`:97-283`) | **exact** |
| `messages/uz-Latn.json` + `ru.json` (MOD — `collect.*`, `billing.*`) | i18n | o'zi (mavjud 23 namespace) | **exact** |
| `messages/uz-Cyrl.json` | i18n | ⛔ **GENERATSIYA** — `npm --prefix frontend run i18n:gen` | **exact** |

### 1.4 Testlar va darvozalar

| Fayl | Rol | Analog | Moslik |
|---|---|---|---|
| `tests/tenancy/test_idempotency_concurrency.py` (**A1 zondi**) | probe | `tests/tenancy/test_billable_anchor_probe.py:1-70` + `fixtures/billable_probe.py` | **exact** (shakl) / §5.1 (mazmun) |
| `tests/tenancy/test_generated_from_column_probe.py` (**A2 zondi**) | probe | o'sha | **exact** |
| `tests/fixtures/billing_domain.py` | fixture | `tests/fixtures/occupancy_domain.py:1-140` (**nomlash majburiyati**) | **exact** |
| `tests/tenancy/test_billing_domain_meta.py` | test (meta) | `tests/tenancy/test_occupancy_domain_meta.py:1-613` | **exact** |
| `tests/tenancy/test_meta.py` (MOD — `test_billing_registries_are_self_consistent`, `test_billing_delete_order_is_declared_not_derived`) | test (meta) | `test_meta.py:1088-1193` + `:1195-1207` | **exact** / §5.8 (regeks) |
| `tests/tenancy/test_cross_tenant.py` (MOD — `CASHIER_ROUTES`, `market_a_cashier_headers`, `PARAM_FILLERS`, `BODY_FILLERS`) | test (meta) | `test_cross_tenant.py:700-730` (`INSPECTOR_ROUTES`) + `:1078-1113` (`headers_for`) | **exact** |
| `tests/tenancy/test_route_coverage.py` (MOD — `MINIMUM_MATRIX_ROUTES`) | test (meta) | o'zi (`:49-139`) | **exact** |
| `tests/tenancy/test_occupancy_domain_meta.py` (MOD — `DEFINER_SURFACES` bo'shatiladi) | test (meta) | o'zi (`:75-79`, `:534-593`) | **exact** |
| `tests/integration/test_phase6_criteria.py` | faza darvozasi | `tests/integration/test_phase5_criteria.py:1118-1146` (**meta-test**) | **exact** |
| `tests/integration/test_billing_immutable.py` | integration | `tests/integration/test_occupancy_immutable.py:1-30` (**`sbozor_owner` bilan**) | **exact** |
| `tests/integration/test_billing_close.py` | integration | `tests/integration/test_day_close.py` | **exact** |
| `tests/integration/test_payments_api.py`, `test_shifts_api.py` | integration | `tests/integration/test_tariffs_api.py`, `test_snapshot_api.py` | **exact** |
| `tests/unit/test_billable_from_slots.py`, `tests/unit/test_variance.py` | test (unit) | `tests/unit/test_aggregate_stall_slot.py:1-60` (**LITERAL JADVAL**) | **exact** |
| `frontend/scripts/collect-surface.test.mjs` | gate (matn) | `frontend/scripts/blind-payload.test.mjs:1-469` (**to'liq shablon**) | **exact** |
| `frontend/scripts/billing-copy.test.mjs` | gate (matn) | `frontend/scripts/zone-copy.test.mjs`, `snapshot-copy.test.mjs` | **exact** |
| `frontend/scripts/error-codes.test.mjs` (MOD — `BILLING_*` bloki) | gate (matn) | o'zi (`:774-818`) | **exact** |
| `frontend/src/components/collect/*.test.tsx`, `billing/*.test.tsx` | component test | `components/review/review-session.test.tsx:376-429` (**SANOQ**) | **exact** |
| `.planning/phases/05-.../05-UI-SPEC.md` (MOD — G-18 qatoriga 3-naqsh) | gate declaration | — | **analog YO'Q** (bir martalik amal, §2 R-9) |

---

## 2. Ro'yxatga olish cheklistlari — artefakt turi bo'yicha

> **O'qish qoidasi:** «Joy» ustuni — **o'zgarishi SHART** bo'lgan fayl.
> «Ushlaydi» ustuni — unutilsa **qaysi test qizaradi**. Bo'sh «Ushlaydi»
> = **hech nima ushlamaydi** (bu ochiq xavf, rejada nomlanadi).

### R-1. Yangi tenant jadvali — **SAKKIZ JOY** (5-fazada oltita edi)

Manba: `05-PATTERNS.md` §S-1 + bu sessiyada qayta tekshirildi.

| # | Joy (`path`) | Nima yoziladi | Ushlaydi |
|---|---|---|---|
| 1 | `packages/sbozor-core/sbozor_core/models/billing.py` | `__tablename__`, `__table_args__`, ustunlar | `test_market_domain_meta.py::test_autogenerate_is_empty` |
| 2 | `packages/sbozor-core/sbozor_core/models/__init__.py` | barrel importi | `test_autogenerate_is_empty` (`op.drop_table` taklifi) |
| 3 | `migrations/entities/__init__.py::BILLING_TENANT_TABLES` | RLS tsikli manbai | `test_meta.py::test_every_table_is_tenant_scoped` (`pg_catalog` dan, reyestrga **tayanmaydi**) |
| 4 | `migrations/entities/__init__.py::ALL_TENANT_TABLES` | `*BILLING_TENANT_TABLES` splice | **yangi** `test_billing_registries_are_self_consistent` (`born <= ALL_TENANT_TABLES`) — `test_meta.py:1142-1153` naqshi |
| 5 | `migrations/versions/0020_billing_domain.py` | `op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy` | `test_meta.py::test_every_table_is_tenant_scoped`, `test_app_role_policies_all_reference_tenant_guc` |
| 6 | `sbozor_core/schema_contract.py::AUDITED_TABLES` | **faqat** trigger ulanadigan jadval (`charge_adjustments`, `cashier_shifts`) | `test_meta.py::test_audited_tables_have_trigger` (`:907`) — **ikki tomonlama** `PENDING_AUDIT_TRIGGERS` bilan (`:226`) |
| 7 | `migrations/entities/__init__.py::BILLING_DELETE_ORDER` + `0021` | kaskad tartibi (**bolalardan ota-onaga**) | `test_market_delete_guard.py::test_cascade_covers_every_table_referencing_markets` (`:163`) — **§6 OP-1** |
| 8 | `tests/fixtures/billing_domain.py` | seed (`occupancy_domain.py` naqshi) | — (hech nima; testlar o'zi ishlatadi) |

**Verbatim reyestr shakli** — `migrations/entities/__init__.py:297-304`:

```python
OCCUPANCY_TENANT_TABLES: tuple[str, ...] = (
    "camera_zones",
    "occupancy_events",
    "audit_rounds",
    "review_assignments",
    "zone_reviews",
    "stall_slot_occupancy",
)
"""`0018_occupancy_domain` yaratadigan tenant jadvallari (AI-01…AI-06).

TARTIB — FK bo'yicha OTA-ONADAN bolalarga, ...
"""
```

**Verbatim kompozit FK + `UNIQUE(market_id, id)`** — `0018_occupancy_domain.py:320-343`:

```python
        sa.PrimaryKeyConstraint("id", name="pk_camera_zones"),
        sa.ForeignKeyConstraint(
            ["market_id"], ["markets.id"], name="fk_camera_zones_market_id_markets"
        ),
        sa.ForeignKeyConstraint(
            ["market_id", "camera_id"],
            ["cameras.market_id", "cameras.id"],
            name="fk_camera_zones_market_id_camera_id_cameras",
        ),
        # KOMPOZIT FK NISHONI: `occupancy_events` `(market_id, camera_zone_id)` ga havola qiladi.
        sa.UniqueConstraint("market_id", "id", name="uq_camera_zones_market_id_id"),
```

⛔ **Tuzoq 1 — `BILLING_DELETE_ORDER` LITERAL yoziladi, hosila EMAS.**
`test_meta.py:1197-1207` `OCCUPANCY_DELETE_ORDER = tuple(reversed(...))`
shaklini **manba matnidan** izlaydi. Yangi ro'yxat uchun **jufti
yozilmagan** (§5.8) — D-32 bo'yicha yoziladi.

⛔ **Tuzoq 2 — `FINANCIAL_TABLES` GA HECH NIMA QO'SHILMAYDI.**
`schema_contract.py:69-80` da `daily_charges`, `charge_adjustments`,
`payments` **allaqachon** bor (1-fazadan). `cashier_shifts`,
`billing_anomalies`, `charge_evidence` **qo'shilmaydi** — sabab
`schema_contract.py:96-103` da o'lchangan (`stall_assignments` Pitfall 3):
test undan **nomi aynan `amount_soum`** bo'lgan ustun talab qilardi va
yagona «tuzatish» **soxta pul ustuni** bo'lardi. `cashier_shifts` da pul
bor (`declared_soum`, `system_soum`), lekin **`amount_soum` YO'Q** — shu
sabab `AUDITED_TABLES` docstringida yoziladi.

⛔ **Tuzoq 3 — kompozit FK nishoni yo'q bo'lsa migratsiya O'ZI yiqiladi.**
`stall_slot_occupancy` da **`UNIQUE (market_id, id)` YO'Q**
(`models/occupancy.py:972-1008` — faqat
`uq_stall_slot_occupancy_market_stall_day_slot`). Agar `charge_evidence`
unga kompozit FK qo'ysa, `0020` **`InvalidForeignKeyError`** bilan
yiqiladi. Naqsh **tayyor** — `0018_occupancy_domain.py:266-287` (0b bosqich):

```python
    op.create_unique_constraint("uq_snapshots_market_id_id", "snapshots", ["market_id", "id"])
```

⚠ Va uning jufti `downgrade()` da **xom SQL bilan** (`0018:791-796`).
⚠ `market_id` bilan boshlanadi → `INDEX_EXCEPTIONS` ga **tushmaydi**.

✅ **Mavjud nishonlar (qo'shish kerak emas):** `uq_stalls_market_id_id`
(`market.py:362`), `uq_vendors_market_id_id` (`:567`),
`uq_tariffs_market_id_id` (`:525`), `uq_occupancy_events_market_id_id`
(`occupancy.py:587`), `uq_snapshots_market_id_id` (`snapshot.py:699`).

### R-2. Yangi Alembic revizyasi — **BESH JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `migrations/versions/0020_billing_domain.py` | `revision="0020"`, `down_revision="0019"` | Alembik zanjiri (`alembic upgrade head` yiqiladi) |
| 2 | `migrations/versions/0021_market_delete_billing.py` | `revision="0021"`, `down_revision="0020"` | o'sha |
| 3 | `upgrade()` **tartibi** | (0b) yetishmayotgan UNIQUE → (1..N) `create_table` → qisman indekslar → RLS tsikli → audit tsikli → trigger funksiya→trigger → `_regrant` | `0018:254-758` naqshi; buzilsa DDL yiqiladi |
| 4 | `downgrade()` **teskari tartibi** | trigger yechish → funksiya `drop_entity` → audit detach → policy drop → indeks drop → `BILLING_DELETE_ORDER` bo'yicha `drop_table` → xom SQL konstrayt | `0018:761-796` |
| 5 | Modelda ham **`Index(...)`** e'loni | qisman UNIQUE/indeks **ikki tomonda** | `test_autogenerate_is_empty` → `remove_index` (`models/occupancy.py:350-358` da o'lchangan) |

**Verbatim RLS tsikli** — `0018_occupancy_domain.py:711-714`:

```python
    for table in OCCUPANCY_TENANT_TABLES:
        enable_tenant_rls(table)
        create_entity(tenant_policy(table))
        create_entity(owner_bootstrap_policy(table))
```

**Verbatim qisman indeks** — `0018:691-702` (nom va predikat **modeldan
import**, literal takrorlanmaydi):

```python
    op.create_index(
        CAMERA_ZONE_ACTIVE_INDEX,
        "camera_zones",
        ["market_id", "camera_id"],
        postgresql_where=sa.text(CAMERA_ZONE_ACTIVE_PREDICATE),
    )
```

**Modeldagi jufti (D-27 — bitta ochiq smena)** — `models/snapshot.py:859-866`:

```python
        Index(
            ALERT_OPEN_INDEX,
            "market_id",
            "alert_key",
            text(ALERT_OPEN_EXPR),
            unique=True,
            postgresql_where=text(ALERT_OPEN_PREDICATE),
        ),
```

⚠ `NULL` UNIQUE indeksda o'ziga teng emas (`snapshot.py:212-222`) — `cashier_shifts`
uchun predikat **`status = 'open'`** bo'ladi (enum'dan hosila), `COALESCE`
sentinel **kerak emas** (`cashier_id` `NOT NULL`).

### R-3. Yangi o'zgarmaslik triggeri — **BESH JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `migrations/entities/triggers.py` | `PGFunction` (har jadval uchun **o'z** funksiyasi) | `test_autogenerate_is_empty` (ta'rif drifti) |
| 2 | `triggers.py::BILLING_TRIGGER_FUNCTIONS` | scope'li ro'yxat | — |
| 3 | `triggers.py::ALL_TRIGGER_FUNCTIONS` | aggregat (`:625-630`) | `test_autogenerate_is_empty` |
| 4 | `0020` — `IMMUTABILITY_TRIGGERS` uchligi + `attach_immutability_trigger()` | `(jadval, funksiya, trigger)` | `test_billing_immutable.py` (xulq) |
| 5 | `0020` `downgrade()` | `detach_immutability_trigger` → `drop_entity` (**teskari**) | `alembic downgrade` yiqiladi |

**Verbatim shablon** — `migrations/entities/triggers.py:468-488`:

```python
OCCUPANCY_EVENT_IMMUTABLE = PGFunction(
    schema="public",
    signature="occupancy_event_immutable()",
    definition="""
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (
       SELECT 1 FROM public.markets AS m
       WHERE m.id = OLD.market_id AND m.is_active = false
     ) THEN
    RETURN OLD;
  END IF;

  RAISE EXCEPTION 'occupancy_events is append-only (attempted %)', TG_OP;
END $$
""",
)
```

**Ulash** — `0018:196-199` + `:743-746`:

```python
IMMUTABILITY_TRIGGERS: tuple[tuple[str, str, str], ...] = (
    ("occupancy_events", "occupancy_event_immutable", "trg_occupancy_event_immutable"),
    ("zone_reviews", "zone_review_immutable", "trg_zone_review_immutable"),
)
...
    create_entity(OCCUPANCY_EVENT_IMMUTABLE)
    create_entity(ZONE_REVIEW_IMMUTABLE)
    for table, function_name, trigger_name in IMMUTABILITY_TRIGGERS:
        attach_immutability_trigger(table, function_name, trigger_name)
```

**Gotcha'lar (hammasi o'lchangan):**
- ⛔ `RETURN OLD` **faqat** istisno shoxida: `BEFORE DELETE` `NULL` qaytarsa
  amal **jimgina** bekor bo'ladi va `market_delete_draft()` «o'chirdim» deb
  **yolg'on** gapirardi (`triggers.py:508-512`).
- ⛔ **Har jadval o'z funksiyasiga ega** — `TG_TABLE_NAME` bo'yicha
  shoxlanadigan umumiy funksiya **taqiqlangan** (`helpers.py:278-282`).
- ⛔ `SECURITY DEFINER` **YOZILMAYDI** — `markets` o'qish RLS ostida
  (fail-closed), va `test_meta.py` `pg_proc.prosecdef` bo'yicha qulflaydi
  (`triggers.py:464-466`).
- ⚠ `BEFORE` `AFTER` dan oldin yuradi → rad etilgan `UPDATE` `audit_log` ga
  qator **qoldirmaydi** (`helpers.py:295-298`). Bu **kutilgan** xulq va u
  `test_billing_immutable.py` ning 4-da'vosi bo'ladi (`test_occupancy_immutable.py:23-30`).
- ⚠ `cashier_shifts` da trigger **shartli** bo'lishi kerak (`status='open'`
  → `closed` o'tishi ruxsat, deklaratsiya maydonlari qayta yozilishi **YO'Q**).
  Bu `TARIFF_PAST_IMMUTABLE` sinfi (`triggers.py:233`), `OCCUPANCY_EVENT_IMMUTABLE`
  emas — **ikki shakl orasidagi tanlov rejada ochiq yoziladi** (`triggers.py:443-449`
  ikkalasini solishtiradi).

### R-4. Moliyaviy jadval qo'riqchilari — **`financial_guards()` CHAQIRILMAYDI**

C-2 ning presedenti — `0008_temporal.py:164-182` (verbatim izoh):

```
    #    ⚠ `financial_guards("tariffs", ...)` BU YERDA CHAQIRILMAYDI.
    #
    #    Yordamchi `UNIQUE(market_id, category_id, business_date)` beradi, ya'ni
    #    idempotentlik kalitini QATOR YOZILGAN KUNGA bog'laydi. Tarifda esa
    #    hukmron sana `valid_from` ...
    #    Shuning uchun uchala qo'riqchi ham QO'LDA yozilgan
```

Va **qo'lda yozilgan generated ustun** — `0008_temporal.py:201-206`:

```python
        sa.Column(
            "business_date",
            sa.Date(),
            sa.Computed(BUSINESS_DATE_EXPR, persisted=True),
            nullable=False,
        ),
```

**Darvozaning aniq talabi** — `tests/tenancy/test_meta.py:1327-1356`
(uchta shart, **har biri alohida**):

| Shart | Mexanizm | Qanday bajariladi |
|---|---|---|
| `business_date` `attgenerated = 's'` | `pg_attribute` | `sa.Computed(BUSINESS_DATE_EXPR, persisted=True)` — ifoda `migrations.helpers` dan **IMPORT** |
| `CHECK` ichida `amount_soum\s*>\s*0` regeksi | `pg_get_constraintdef` | ⛔ **ustun nomi aynan `amount_soum`** — `delta_soum` darvozani qizartiradi |
| `conkey[1]` attname `== 'market_id'` | `pg_constraint` | `UNIQUE (market_id, stall_id, service_date)` / `UNIQUE (market_id, idempotency_key)` |

⚠ **`financial_guard_statements()` (`helpers.py:335-372`) baribir o'qiladi** —
u ifodalarning **yagona manbai**; uchala DDL matni shundan **ko'chiriladi**,
funksiyaning o'zi chaqirilmaydi.

### R-5. Yangi API marshruti — **YETTI JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `app/api/v1/<domain>.py` | `router = APIRouter(tags=[...])` + handler | — |
| 2 | `app/main.py` | `app.include_router(..., prefix=f"{API_V1_PREFIX}/...")` + **prefiks qarori izohi** | marshrut umuman yo'q bo'ladi |
| 3 | `app/schemas.py` | `response_model` | FastAPI `PydanticUserError` |
| 4 | `tests/tenancy/test_cross_tenant.py::PARAM_FILLERS` | **har yo'l parametri** (`payment_id`, `shift_id`) uchun B bozorining HAQIQIY qiymati | ✅ `test_route_coverage.py::test_no_unclassified_routes` (`:143`), `test_all_path_params_have_fillers` (`:223`) |
| 5 | `test_cross_tenant.py::BODY_FILLERS` | `POST`/`PUT`/`PATCH` tanasi | ⚠ **HECH NIMA** — yo'qligi 422 beradi va da'vo **sinalmay** qoladi (`test_body_fillers_point_at_live_routes:1435` faqat **eskirgan** yozuvni ushlaydi) |
| 6 | `test_cross_tenant.py::CASHIER_ROUTES` + `market_a_cashier_headers` + `headers_for` | `payment_create` **faqat kassirda** | ✅ `test_cross_tenant_object_returns_404` **403 bilan qizaradi** |
| 7 | `test_route_coverage.py::MINIMUM_MATRIX_ROUTES` | chegarani **sabab bilan** ko'tarish | ⚠ **quyi chegara** (`>=`) — yangi marshrut uni **qizartirmaydi**; D-32 intizomi |

**`CASHIER_ROUTES` naqshi (verbatim)** — `test_cross_tenant.py:700-709`:

```python
INSPECTOR_ROUTES: frozenset[RouteSpec] = frozenset(
    {
        RouteSpec("GET", "/api/v1/review/uncertain/next"),
        RouteSpec("GET", "/api/v1/review/budget"),
        RouteSpec("POST", "/api/v1/review/{review_assignment_id}/answer"),
        # --- 05-11: ko'r audit ---
        RouteSpec("GET", "/api/v1/review/blind/next"),
        RouteSpec("POST", "/api/v1/review/blind/{review_assignment_id}/answer"),
    }
)
```

**Sessiya tanlagichi** — `test_cross_tenant.py:1106-1111` (uchinchi shox
qo'shiladi):

```python
    def _pick(route: RouteSpec) -> dict[str, str]:
        if route in PLATFORM_ADMIN_ROUTES:
            return market_a_admin_headers
        if route in INSPECTOR_ROUTES:
            return market_a_inspector_headers
        return market_a_headers
```

**Kassir seed'i TAYYOR** — `tests/fixtures/auth_users.py:75` (`AuthSeed.cashier`),
`tests/fixtures/two_markets.py:222` (`must_change_password = False`),
`:247` (`roles=["cashier"]`). **Yangi seed yozilmaydi**; fixture naqshi
`test_cross_tenant.py:1078-1089` (`market_a_inspector_headers`).

⚠ **Qaysi marshrut `CASHIER_ROUTES` ga tushadi:** UI-SPEC §5.6 bo'yicha
`billing_collect_view` va `shift_manage` **`market_admin` da ham bor**,
ya'ni ular odatdagi sessiyadan o'tadi. Faqat `payment_create` **yolg'iz
kassirda** → `POST /payments` va `POST /payments/{payment_id}/reverse`
`CASHIER_ROUTES` ga tushadi.

⛔ **Huquq QAYERDA e'lon qilinadi — ikki konventsiya bor va tanlov MEXANIK:**

| Holat | Shakl | Manba |
|---|---|---|
| Marshrutda `audit_read(...)` **BOR** | ⛔ dekoratorda: `dependencies=[Depends(require_permission(...))]` | `api/v1/cameras.py:24-42`, `assignments.py:93-99` — FastAPI dekorator bog'liqliklarini imzodan **OLDIN** hal qiladi, ya'ni 403 `audit_read` gacha **yetib bormaydi** |
| `audit_read` **YO'Q** | imzo aliasi: `ReportViewerDep = Annotated[Principal, Depends(require_permission(...))]` | `api/v1/occupancy.py:83`, `reviews.py:150`, `camera_zones.py:110-111` |

✅ **6-fazada `audit_read` KERAK EMAS** (UI-SPEC §5.5 — birorta yangi
marshrut `PERSONAL_FIELDS` qaytarmaydi) → **imzo aliasi shakli**,
`occupancy.py:83` naqshi.

⛔ **`require_any_permission()` ISHLATILMAYDI.**
`tests/tenancy/test_personal_data_coverage.py:691-706` — bu darvozani
ko'targan marshrutlar to'plami **`("/api/v1/snapshots/{snapshot_id}/image",)`
ga AYNAN teng** bo'lishi shart (`assert gated == sorted(...)`). Yangi
marshrutda ishlatilishi butun `npm run test:tenancy` ni qizartiradi.

### R-6. Yangi taskiq cron vazifasi — **TO'RT JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `app/jobs/billing_close.py` | sof `async def` — ⛔ `taskiq` **import qilinmaydi** | `tests/unit/test_no_sim_branching.py` sinfidagi darvoza; `day_close.py:51` qoidasi |
| 2 | `app/worker.py` — `BILLING_CLOSE_CRON: Final[str]` | cron **konstanta + docstringda sabab** | — |
| 3 | `app/worker.py` — `@broker.task(task_name="billing.close", schedule=[{"cron": ..., "cron_offset": MARKET_CRON_OFFSET}])` | **yupqa qobiq** | `tests/unit/test_scheduler_observability.py` |
| 4 | ⚠ **Deploy bandi**: `scheduler` konteyneri **qayta ishga tushiriladi** | jadval `import` paytida olinadi (`worker.py:55-58`) | ⛔ **HECH NIMA** — prodda vazifa hech qachon ishlamaydi, xato ham chiqmaydi (06-RESEARCH Pitfall 10) |
| 5 | (ixtiyoriy, M-C) `self_check.py::EXPECTED_COMPONENTS` + `alerting.py::watched` | yurak urishining **yo'qligi** ko'rinishi uchun | ⛔ bugun **hech nima** — §0.1 M-C |

**Verbatim yupqa qobiq** — `app/worker.py:860-878`:

```python
@broker.task(
    task_name="occupancy.day_close",
    schedule=[{"cron": DAY_CLOSE_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def day_close_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — kun yopilishi va rasta-slot materializatsiyasi (05-12, AI-05/AI-06).

    ⛔ KECHAGI KUN YOPILADI, BUGUNGISI EMAS (`DAY_CLOSE_CRON` docstringi): ...
    """
    state = context.state
    await day_close(state.sessionmaker, business_date=business_today() - timedelta(days=1))
```

**Verbatim cron konstantasi** — `app/worker.py:410` + docstring:

```python
DAY_CLOSE_CRON: Final[str] = "40 3 * * *"
"""Kun yopilishi — KECHASI 03:40 (Toshkent) va u KECHAGI kunni yopadi.
...
⚠ 03:40 — `RETENTION_CRON` (03:20) DAN KEYIN va u ataylab: ...
"""
```

⚠ C-3 bo'yicha `BILLING_CLOSE_CRON = "10 4 * * *"` — `DAY_CLOSE_CRON`
(03:40) dan **keyin**, `RETENTION_CRON`(03:20)→`DAY_CLOSE_CRON`(03:40)
farqi bilan **bir xil mulohaza**.

**Job tanasi (verbatim shablon)** — `app/jobs/day_close.py:153-205`:

```python
async def day_close(
    sessionmaker: async_sessionmaker[AsyncSession],
    *,
    business_date: date,
) -> DayCloseResult:
    request_id = f"job-day-close-{business_date.isoformat()}"
    result = DayCloseResult()

    try:
        market_ids = await active_market_ids(sessionmaker)
    except SQLAlchemyError:
        log.exception("day_close_market_list_failed")
        return result
    result.markets = len(market_ids)

    for market_id in market_ids:
        try:
            await _close_market(...)
        except SQLAlchemyError as exc:
            result.errors.append(f"day_close_failed:{type(exc).__name__}")
            log.warning("day_close_failed", market_id=str(market_id), error=type(exc).__name__)

    await _write_heartbeat(sessionmaker, result)
    ...
```

**Tenant sessiyasi (Pitfall 9 ning yechimi)** — `day_close.py:208-231`:

```python
@asynccontextmanager
async def _tenant_session(
    sessionmaker: async_sessionmaker[AsyncSession], *, market_id: UUID, request_id: str
) -> AsyncIterator[AsyncSession]:
    # SIM117 — ichki blok TRANZAKSIYA chegarasi (`audit_draw.py:466`).
    async with sessionmaker() as session:  # noqa: SIM117
        async with session.begin():
            await set_tenant_context(
                session, market_id=market_id, actor_id=None,
                request_id=request_id, actor_kind=ActorKind.SYSTEM,
            )
            yield session
```

⛔ **`market_is_open()` shu kontekst ostida chaqiriladi.** Funksiya
ATAYIN `SECURITY DEFINER` **emas** (`functions.py:1369-1376`) va
fail-closed: kontekstsiz 0 qator → `false` → **hamma kun yopiq**.

**Bozorlar ro'yxati** — `app/jobs/retention.py:162-164` (D-15, yagona
RLS-chetlab o'tuvchi yuza):

```python
_ACTIVE_MARKETS = text(
    "SELECT market_id FROM auth_list_markets_full() WHERE is_active ORDER BY market_id"
)
```

**Yurak urishi** — `day_close.py:321-353` (⛔ **alohida, qisqa
tranzaksiya**; xato **yutiladi**; ⛔ tenant konteksti **yo'q** —
`system_heartbeats` global, `detail` ga faqat **sanoqlar**).

### R-7. Yangi huquq — **UCH JOY, BITTA COMMIT**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `services/core-api/app/security/rbac.py::Permission` | `BILLING_COLLECT_VIEW = "billing_collect_view"`, `SHIFT_MANAGE = "shift_manage"` | `tests/unit/test_rbac_matrix.py::test_every_role_has_entry` (rol bo'yicha) |
| 2 | `rbac.py::ROLE_PERMISSIONS` | `cashier`/`market_admin`/`director` taqsimoti | o'sha |
| 3 | `frontend/src/lib/rbac.ts::PERMISSIONS` + `ROLE_PERMISSIONS` | ⛔ **matn sifatida solishtiriladi** | ✅ `frontend/scripts/role-gate.test.mjs:29-56` (`rbac.py` **va** `rbac.ts` ni **fayl sifatida** o'qiydi) — **§6 OP-6** |

⛔ **Kassirga `market_data_view` BERILMAYDI:**
`test_personal_data_coverage.py:761-787` — uning egasida `vendor_view`
ham **bo'lishi SHART**, `vendor_view` esa **butun shaxsiy-ma'lumot
yuzasini** ochadi (`rbac.py:90-110`).

### R-8. Yangi xato kodi / audit hodisasi / enum — **REYESTR ZANJIRLARI**

**(a) HTTP `detail` xato kodi — TO'RT JOY:**

| # | Joy | Analog | Ushlaydi |
|---|---|---|---|
| 1 | `services/core-api/app/services/billing_errors.py` (**YANGI fayl**) | `app/services/occupancy_errors.py:1-200` (`Final[str]` konstantalar + `frozenset` reyestrlari) | — |
| 2 | `frontend/src/lib/billing-errors.ts` (**YANGI**) | `frontend/src/lib/zone-errors.ts` (`kod: {tone, surface}` jadvali) | — |
| 3 | `frontend/scripts/error-codes.test.mjs` (MOD — `BACKEND_BILLING_ERRORS` yo'li + `BILLING_SURFACES` bloki + **aniq son nazorati**) | o'zi (`:774-818`) | ✅ zanjirni **o'zi** yopadi |
| 4 | `messages/uz-Latn.json` + `ru.json` (`collect.errorCause.*` / `errorFix.*`) + `uz-Cyrl.json` **generatsiya** | `cameras.errorCause.*` naqshi | ✅ `error-codes.test.mjs` (**ikkita** matn: sabab **va** tuzatish) |

⛔ **`occupancy_errors.py` GA KOD QO'SHILMAYDI** — `error-codes.test.mjs:801-805`
`occupancyConstants.size == 15` ni **aniq son** bilan talab qiladi (§0.1 M-B).

**(b) `AuditAction` a'zosi — UCH JOY, bitta commit:**

| # | Joy | Ushlaydi |
|---|---|---|
| 1 | `packages/sbozor-core/sbozor_core/enums.py::AuditAction` (`:442-464`) | — |
| 2 | `frontend/src/lib/api-types.ts::AUDIT_ACTIONS` (`:244-258`) | ✅ `audit-actions.test.mjs:63-68` — `deepEqual` (**ikki tomonlama**) |
| 3 | `messages/{uz-Latn,ru}.json` `audit.actions.<nom>` + `uz-Cyrl` generatsiya | ✅ `audit-actions.test.mjs:70-90` — ⛔ **kalitlar to'plami TENGLIGI** (ortiqcha kalit ham qizartiradi) |

✅ **`AUDIT_TABLES` (api-types.ts:274-280) TEGILMAYDI.** U audit
sahifasining **filtr ro'yxati** (1-fazadan 5 nom) va DB'ning
`AUDITED_TABLES` reyestri bilan **bog'lanmagan** — 2–5 fazalar unga
hech nima qo'shmagan. `audit-actions.test.mjs:92-103` faqat uning
**o'zi ↔ 3 locale** parity'sini tekshiradi.

**(c) Domen enum'i (`AnomalyKind`, `AdjustmentReason`, `ReversalReason`,
`PaymentMethod`) — IKKI JOY + BIR BO'SHLIQ:**

| # | Joy | Ushlaydi |
|---|---|---|
| 1 | `sbozor_core/enums.py` | — |
| 2 | `sbozor_core/models/billing.py` — enum'dan **HOSILA** `CHECK` (`_quoted()` naqshi, `models/occupancy.py:206-248`) | `test_billing_domain_meta.py` (yozilishi kerak) |
| 3 | `frontend/src/lib/api-types.ts` — `as const` massiv (`HUMAN_ANSWERS:1552` naqshi) | ⛔ **HECH NIMA** — `readPythonEnumValues` parity gate'i **faqat** `AuditAction` va `Role` uchun mavjud (§5.10) |
| 4 | `messages/*` `collect.adjustmentReason.*`, `billing.anomalyKind.*` | ✅ `billing-copy.test.mjs` (yangi, UI-SPEC G-24/G-26 — **reyestrdan iteratsiya**, to'plam tengligi) |

### R-9. Yangi frontend komponent katalogi — **BEsH JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `frontend/src/components/collect/` | ≥5 mahsulot fayli | ✅ `bulk-action-surface.test.mjs:293-308` (e'lon qilingan katalog **mavjud va bo'sh emas**) |
| 2 | ⛔ `.planning/phases/05-.../05-UI-SPEC.md` §15 **G-18 qatoriga** `` `components/collect/**` `` | **uchinchi** naqsh | ✅ `bulk-action-surface.test.mjs:127-138` (`globs.length >= 2`) — **§6 OP-5** |
| 3 | `frontend/scripts/collect-surface.test.mjs` (**YANGI**) | katalogni `readdirSync` bilan **rekursiv** + `stripComments()` | UI-SPEC G-7/G-22/G-28 |
| 4 | `app/[locale]/(app)/collect/` marshrut katalogi | `page.tsx` | locale routing **avtomatik** (`frontend/src/proxy.ts:15-18` matcher generik) |
| 5 | `components/shell/app-shell.tsx::NAV_ITEMS` | 2 yozuv (`/collect`, `/billing`) | ⚠ hech nima; `MOBILE_PRIMARY_COUNT = 4` (`:283`) tekshirilmaydi |

⛔⛔ **BU HUJJAT VA 06-UI-SPEC `| **G-18** |` BILAN BOSHLANADIGAN QATOR
YOZMAYDI.** `bulk-action-surface.test.mjs:112-125`:

```js
test("G-18(b): e'lonning O'ZI topildi — AYNAN bitta UI-SPEC va AYNAN bitta qator", () => {
  assert.equal(
    SPEC_FILES.length,
    1,
    `G-18 ni e'lon qilgan UI-SPEC soni ${SPEC_FILES.length} (kutilgan: 1): ...`
```

Ikkinchi e'lon **butun `npm run gate` ni** qizartirardi. Naqsh regeksi
`/`(components\/[A-Za-z0-9._-]+\/\*\*)`/g` (`:103`) — `components/collect/**`
mos keladi.

### R-10. Yangi so'rov moduli (`lib/*-queries.ts`) — **UCH QOIDA**

**Verbatim** — `frontend/src/lib/blind-audit-queries.ts:92-99`, `:126-137`,
`:189-208`:

```ts
export const blindPrefix = (marketId: string) =>
  domainKey(marketId, "blind-audit");
...
export function useBlindNext(options?: { enabled?: boolean }) {
  const marketId = useMarketId();
  return useQuery({
    queryKey: blindNextKey(marketId ?? ""),
    queryFn: () => apiFetch(`${BLIND_PATH}/next`, { schema: blindAuditItemSchema }),
    enabled: marketId !== null && (options?.enabled ?? true),
    retry: false,
    gcTime: 0,
    staleTime: 0,
    refetchOnWindowFocus: false,
  });
}
...
  return useMutation({
    ...
    retry: false,
    onSuccess: () => {
      client.removeQueries({ queryKey: blindPrefix(marketId) });
    },
  });
```

| Qoida | Sabab (`path:line`) |
|---|---|
| Kalit **`marketId` bilan boshlanadi** (`domainKey(...)`) | `blind-audit-queries.ts:92`; `tenant-cache.test.tsx` |
| ⛔ **`gcTime: 0` + `removeQueries` JUFTLIGI** — biri ikkinchisini almashtirmaydi | `blind-audit-queries.ts:47-62`; darvoza `blind-payload.test.mjs:442-468` |
| ⛔ Sxema **`z.strictObject`** | `api-types.ts:1632`; `blind-audit-queries.ts:118-122` |
| ⛔ **Alohida modul** — aks holda taqiqlangan nom skani **kontekstga bog'liq** bo'lardi | `blind-payload.test.mjs:20-25`; UI-SPEC §5.3 |

### R-11. i18n — **UCH FAYL, LEKIN BIRI GENERATSIYA**

| Fayl | Amal | Ushlaydi |
|---|---|---|
| `frontend/messages/uz-Latn.json` | ⛔ **kalitlarning YAGONA manbai** (`src/global.ts:1-16` tip augmentatsiyasi shundan) | TypeScript (`t('...')` kompilyatsiya xatosi) |
| `frontend/messages/ru.json` | qo'lda | ✅ `npm --prefix frontend run i18n:check` → `check-messages.mjs` |
| `frontend/messages/uz-Cyrl.json` | ⛔ **QO'LDA TAHRIRLANMAYDI** — `npm --prefix frontend run i18n:gen` | ✅ `gen-cyrillic.mjs --check` (`frontend/package.json:19`) |
| `frontend/messages/uz-Cyrl.overrides.json` | faqat transliterator xato qilsa | UI-SPEC M-5: 6-faza **birorta yozuv qo'shmaydi** |

⚠ Yangi **top-level namespace**: bugun 23 ta bor (`common`…`occupancy`);
6-faza `collect` va `billing` qo'shadi.

### R-12. Orfan `SECURITY DEFINER` funksiyani DROP qilish — **BESH JOY**

| # | Joy | Nima | Ushlaydi |
|---|---|---|---|
| 1 | `migrations/versions/0020_billing_domain.py` | `drop_entity(AUDIT_DRAW_DUE_MARKETS)`, `drop_entity(OCCUPANCY_DAY_CLOSE_MARKETS)` + **sabab docstringda** | — |
| 2 | `0020` `downgrade()` | `create_entity(...)` + `_regrant(...)` (`0018:242-251` naqshi) | `alembic downgrade` |
| 3 | `migrations/entities/functions.py::OCCUPANCY_FUNCTIONS` (`:1771-1774`) | **bo'shatiladi** (`PGFunction` ta'riflari **JOYIDA QOLADI** — `0018` ularni import qiladi) | ✅ `test_autogenerate_is_empty` (reyestrda qolgan funksiya **qayta yaratilishi** taklif qilinardi) |
| 4 | `functions.py::OCCUPANCY_GRANT_SIGNATURES` (`:1784-1787`) | **bo'shatiladi** | ⚠ `0018:757-758` tsikli bo'sh bo'lib qoladi → nol holatdan yugurishda funksiyalar **`EXECUTE TO PUBLIC`** bilan tug'ilib, `0020` gacha shunday qoladi. ⛔ Tavsiya: uchlik **`0018` ning O'ZIGA muzlatilgan konstanta** sifatida ko'chiriladi (`0019:71-137` `MARKET_DELETE_DRAFT_WITHOUT_OCCUPANCY` naqshining **teskari** qo'llanishi) |
| 5 | `tests/tenancy/test_occupancy_domain_meta.py::DEFINER_SURFACES` (`:75-79`) | **bo'shatiladi** (yoki qolgan nom **sabab bilan**) | ✅ **`test_due_markets_functions_expose_only_identifiers:558-564`** — `assert row is not None, "bazada topilmadi"` — **§6 OP-2** |

✅ `test_meta.py::EXPECTED_DEFINER_FUNCTIONS` (`:152-202`) **TEGILMAYDI** —
u ikkala funksiyani **umuman sanamaydi** va shart `found >= EXPECTED`
(quyi chegara, `:562`).

---

## 3. Pattern Assignments — fayl bo'yicha

### 3.1 `packages/sbozor-core/sbozor_core/models/billing.py` (model, CRUD + ledger)

**Analog:** `packages/sbozor-core/sbozor_core/models/occupancy.py` (1028
qator, 6 klass — **struktura, tartib va docstring uslubi to'liq
ko'chiriladi**).

**Enum'dan hosila `CHECK`** (`occupancy.py:206-221`):

```python
def _quoted(values: tuple[str, ...]) -> str:
    """SQL literal ro'yxati. Qiymatlar `StrEnum` a'zolari — tashqi kirish emas.
    ... ATAYIN BESHINCHI marta takrorlanadi ...
    """
    return ", ".join(f"'{value}'" for value in values)


OCCUPANCY_VERDICT_CHECK = f"verdict IN ({_quoted(OCCUPANCY_VERDICT_VALUES)})"
```

**Juftlangan invariant (C-12 uchun AYNAN shu shakl)** — `occupancy.py:333-336`:

```python
NO_COVERAGE_IS_PAIRED_CHECK = (
    f"(verdict = '{ResolutionSource.NO_COVERAGE.value}') "
    f"= (resolution_source = '{ResolutionSource.NO_COVERAGE.value}')"
)
```

⚠ **Ikki tomonlama tenglik (`=`, `->` emas)** — ikkala nosozlikni ham
yopadi (`occupancy.py:327-331`). `billing_anomalies` uchun:
`CHECK ( (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL) )`.

**Dalil langari (D-08/C-7 uchun)** — `occupancy.py:317-319`:

```python
SLOT_OCCUPIED_HAS_WINNER_CHECK = (
    f"(verdict = '{OccupancyVerdict.OCCUPIED.value}') = (winning_occupancy_event_id IS NOT NULL)"
)
```

**`users` ga FK (kassir/nazoratchi)** — `occupancy.py:892-894`:

```python
        # ⛔ `ondelete` YO'Q (NO ACTION): javobi bor foydalanuvchini o'chirish RAD ETILADI.
        ForeignKeyConstraint(
            ["reviewer_id"], ["users.id"], name="fk_zone_reviews_reviewer_id_users"
        ),
```

**Gotcha'lar:**
- ⛔ `TimestampMixin` **o'zgarmas jadvalga QO'YILMAYDI** — `updated_at`
  «tahrirlash mumkin» degan **yolg'on va'da** berardi (`occupancy.py:66-69`,
  `:964-967`).
- ⚠ `business_date` **NUSXALANADI**, `GENERATED` **emas**, `occupancy`
  zanjirida (`occupancy.py:1012-1015`); `daily_charges` da esa
  `business_date` **generated** (C-2) va domen ustuni **`service_date`**.
  ⛔ **Ikki ma'no ustun docstringida yonma-yon yoziladi.**
- ⚠ Konstrayt nomi **63 baytga** kesiladi — SQLAlchemy `IdentifierError`
  bilan **oldindan** to'xtatadi (`occupancy.py:997-1002`). `daily_charges`
  ning uzun UNIQUE nomlari qisqartirilishi mumkin.

### 3.2 `migrations/versions/0020_billing_domain.py` (migration)

**Analog:** `0018_occupancy_domain.py` — **verbatim shablon**. Yordamchilar
`0018:209-239` dan ko'chiriladi:

```python
def _uuid_pk() -> sa.Column[UUID]:
    """PG18 native `uuidv7()` — vaqt-tartiblangan, B-tree do'st."""
    return sa.Column(
        "id", pg.UUID(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False,
    )


def _market_id() -> sa.Column[UUID]:
    """Tenant kaliti — HAR BIR jadvalda birinchi ustun."""
    return sa.Column("market_id", pg.UUID(as_uuid=True), nullable=False)
```

**Fayl boshidagi ogohlantirish (ko'chiriladi)** — `0018:185-194`:

```
# ⚠ INDEKS NOMLARI, PREDIKATLARI VA `CHECK` IFODALARI SHU YERDA E'LON
#   QILINMAYDI — ular `sbozor_core.models.occupancy` dan IMPORT qilinadi
#   Sabab O'LCHANGAN (03-03, birinchi urinish): `op.create_index(...)`
#   yolg'iz o'zi yetarli emas. ... `test_autogenerate_is_empty` `remove_index`
#   bilan qizaradi.
```

**Idempotent hisob yozish (D-06)** — `app/jobs/day_close.py:89` +
`capture_repo.py:292-294`:

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert
```

```sql
    ON CONFLICT ON CONSTRAINT uq_capture_runs_market_id_camera_id_business_date_slot_time
    DO NOTHING
    RETURNING status
```

⚠ **`ON CONFLICT` NISHONI — KONSTRAYT NOMI, ustunlar ro'yxati emas**, agar
kalitda **hisoblanadigan ustun** bo'lsa (`capture_repo.py:338-341`).
`daily_charges` da kalit `(market_id, stall_id, service_date)` — hammasi
oddiy ustun, ya'ni `index_elements=[...]` ishlaydi.

### 3.3 `services/core-api/app/repositories/payment_repo.py` (repository, idempotent write)

**Analog:** ⚠ **qisman.** `capture_repo.py:270-378` `ON CONFLICT DO
NOTHING ... RETURNING` ni ko'rsatadi, lekin **qayta `SELECT` shakli
repoda YO'Q** (§5.1). `nvr_repo.py:506-521` esa `IntegrityError` ga
tayanadi:

```python
    async def create_run(self, nvr_id: UUID, triggered_by: UUID | None = None) -> UUID:
        """Yangi kashfiyot yugurishini `queued` holatida yozadi.

        ⚠ «Faol yugurish bormi?» TEKSHIRILMAYDI — bu ataylab.
          `0012` dagi QISMAN UNIQUE indeks ... ikkinchi faol yugurishni `23505`
          bilan rad etadi ... Oldindan tekshirish «tekshir-keyin-yoz» poygasini
          tug'dirardi
        """
```

⚠ **Uchinchi majburiyat (`capture_repo.py:363-368`)** — «bu tekshir-keyin-yoz
EMAS»: shart **so'rovning o'zi ichida**, alohida `SELECT` yo'q. 6-fazada
esa **ikkinchi bayonot MAJBURIY** (konfliktda `RETURNING` bo'sh) — ya'ni
bu **yangi shakl** va uni **A1 zondi** o'lchaydi.

**Zond naqshi (verbatim struktura)** — `tests/tenancy/test_billable_anchor_probe.py:1-70`
+ `tests/fixtures/billable_probe.py`; nomlash konventsiyasi
`BILLABLE_ANCHOR_SUPPORTED = true` (`migrations/entities/__init__.py:341`)
→ yangi nom `IDEMPOTENT_GET_OR_CREATE_SUPPORTED`.

**Xato sinfini aniqlash** — `stall_repo.py::sqlstate_of` (mavjud yordamchi,
`assignments.py:110` da import qilingan).

### 3.4 `services/core-api/app/repositories/billing_repo.py` (repository, CRUD + report)

**Analog A — D-04 predikati (C-6):** `occupancy_repo.py:364-384`:

```sql
    per_stall AS (
        SELECT sso.stall_id,
               count(*)                                        AS slots,
               count(*) FILTER (WHERE sso.verdict = :occupied)  AS occupied_slots,
               bool_or(sso.resolution_source = :human)          AS human_confirmed,
               ...
          FROM stall_slot_occupancy sso
         WHERE sso.market_id = :market_id
           AND sso.business_date = :business_date
         GROUP BY sso.stall_id
    )
```

⛔ **`human_confirmed` BILLINGDA ISHLATILMAYDI** (C-6): u `verdict` bilan
bog'lanmagan, ya'ni «boshqa slotda nazoratchi **bo'sh** dedi» holati ham
`true` beradi. Billing o'z predikatini yozadi:
`bool_or(sso.verdict = :occupied AND sso.resolution_source = :human)`.
G-6 sabotaji aynan shu almashtirishni o'lchaydi.

**Analog B — tarixiy tarif/toifa/biriktirish (D-09):** `stall_repo.py:602-629`
(**verbatim**, farqi: `:today` → `:service_date`, `t.amount_soum` yoniga
`t.id`):

```sql
    LEFT JOIN LATERAL (
      SELECT p.category_id
      FROM stall_category_periods p
      WHERE p.market_id = s.market_id
        AND p.stall_id = s.id
        AND p.valid_from <= :today
      ORDER BY p.valid_from DESC
      LIMIT 1
    ) cur ON true
    ...
    LEFT JOIN LATERAL (
      SELECT sa.vendor_id, sa.period
      FROM stall_assignments sa
      WHERE sa.market_id = s.market_id
        AND sa.stall_id = s.id
        AND sa.period @> :today
      LIMIT 1
    ) a ON true
```

⚠ `sa.period @> :day` — `[)` konventsiyasi **faqat**
`sbozor_core/periods.py:19-33` da yashaydi (OQ-5: almashinuv kuni **yangi**
sotuvchiga); `ex_stall_assignments_no_overlap` (`market.py:619-625`) bir
kunda ikki biriktirishni **strukturaviy imkonsiz** qiladi.

⚠ `stalls.code_sort` (`market.py:154-183`, `STALL_CODE_SORT_EXPR`) — kassir
qidiruvining tartibi; **serverda** (UI-SPEC §3.5).

### 3.5 `services/core-api/app/api/v1/billing.py` (router, request-response)

**Analog:** `app/api/v1/occupancy.py` — **exact** (`REPORT_VIEW`, `?day=`,
imzo aliasi, `business_today()` standarti).

**Huquq aliasi** — `occupancy.py:83-84`:

```python
ReportViewerDep = Annotated[Principal, Depends(require_permission(Permission.REPORT_VIEW))]
"""⛔ `OCCUPANCY_REVIEW` EMAS. Modul docstringidagi birinchi bandning mexanizmi."""
```

**Ish vaqtidagi import ogohlantirishi (MUHIM)** — `occupancy.py:70-75`:

```
# ⚠ `date` VA `UUID` ISH VAQTIDA IMPORT QILINADI, `TYPE_CHECKING` OSTIDA
#   EMAS — VA BU O'LCHANGAN ZARURIYAT (`reviews.py` da ham aynan shunday).
#   `from __future__ import annotations` ostida annotatsiyalar SATR bo'lib
#   qoladi va FastAPI ularni Pydantic uchun YECHA olmaydi:
#   `PydanticUserError: ... is not fully defined`.
```

**`market_id` yechimi** — `occupancy.py:100-107` (`market_not_selected` → 403).

**Nol — natija qoidasi** — `occupancy.py:122-124`:

```
    ⛔ BESHALA HISOBLAGICH HAM HAR DOIM QAYTADI — nol bo'lganda ham.
       «Bugun hech kim ko'rilmadi» bilan «hisoblagich ishlamayapti» bir
       xil ko'rinmasligi kerak
```

### 3.6 `services/core-api/app/schemas.py` (MOD — maydonni E'LON QILMASLIK)

**Analog:** `schemas.py:2521-2570` (`BlindItemResponse`) — D-25 ning
serverdagi yarmi **aynan shu shakl**:

```python
class BlindItemResponse(BaseModel):
    """`GET /review/blind/next` — KO'R audit bandi (AI-04, D-17.2).

    ⛔⛔ SAKKIZ MAYDONNING BIRORTASI HAM E'LON QILINMAGAN VA BU
        «YASHIRISH» EMAS.
    ...
    `None` qilib yuborish YETARLI EMAS bo'lardi: kalit javobda tursa uni
    to'ldirish BIR SATRLIK o'zgarish bo'lardi. Sxemadan YASHIRISH
    (`include_in_schema=False`) esa umuman himoya emas — u faqat
    hujjatni o'zgartiradi, baytlarni emas.
    """
```

⚠ `ShiftCloseResponse` maydonlari to'plami **`{id, status, declared_soum,
closed_at}`** (UI-SPEC G-7) — `system_*` **va** `variance*` **umuman
yo'q**. Variance **direktor yuzasida** (`GET /shifts`) qaytariladi.

⚠ `PendingStall` da `charge_id` **umuman yo'q** (D-17) va `tariff_id` ham
**yuborilmaydi** (D-20 — UI-SPEC G-22 klientda hisoblashni *imkonsiz*
qiladi).

### 3.7 `frontend/src/components/collect/payment-bar.tsx` (component)

**Analog A — `useRef` qulfi:** `frontend/src/components/blind-audit/blind-session.tsx:85-137`
(**verbatim**):

```tsx
  /*
   * Qulf BAND IDENTIFIKATORINI saqlaydi (`review-session.tsx` dagi bilan
   * bir xil sabab): `blocked` render paytida hisoblanadi, ya'ni bir
   * hodisa oqimidagi ikki bosish ikkalasi ham eski qiymatni ko'rardi.
   */
  const submittedRef = useRef<string | null>(null);
  ...
  const submit = useCallback(
    (value: HumanAnswer) => {
      if (item === null || submittedRef.current === item.assignment_id) return;
      submittedRef.current = item.assignment_id;
      answer.mutate(
        { assignmentId: item.assignment_id, answer: value },
        {
          onError: () => {
            submittedRef.current = null;
          },
          ...
```

⚠ 6-fazada qulf **`idempotencyKey`** ni saqlaydi (band `id` emas), va
`onError` da **nolga qaytadi** (qayta yuborish uchun) — G-21(c) aynan shuni
o'lchaydi.

**Analog B — `event.repeat` va `aria-disabled`:** `components/review/decision-bar.tsx:11-46`:

```
 * ⛔ `event.repeat` E'TIBORSIZ QOLDIRILADI — VA BU O'LCHANADIGAN QOIDA
 * Klaviatura yorliqlari ... tugmani BOSIB TURISH brauzerda `keydown` ni
 * sekundiga o'nlab marta qo'zg'atadi
 ...
 * ⚠ `aria-disabled`, `disabled` EMAS (§13.3)
 * `disabled` tugma fokus olmaydi va skrinrider uni umuman o'qimaydi
```

**Analog C — bosish SANOG'I testi:** `components/review/review-session.test.tsx:403-429`
(**verbatim**):

```tsx
  test("javob yuborilayotganda ikkinchi bosish YANGI so'rov qilmaydi", async () => {
    await readyFrame();

    fireEvent.click(answerButtons()[0]);
    fireEvent.click(answerButtons()[1]);
    fireEvent.click(answerButtons()[2]);

    await waitFor(() => expect(answerCalls().length).toBeGreaterThan(0));
    expect(answerCalls()).toHaveLength(1);
  });
```

**Pul ko'rsatish** — `components/tariffs/tariff-list.tsx:263,277` +
`api-types.ts:45`:

```ts
export const soumSchema = z.number().int().max(Number.MAX_SAFE_INTEGER);
```

⛔ Klientda pul kutubxonasi **YO'Q**: `useFormatter().number(...)` +
`t("<ns>.amountUnit")`.

### 3.8 `frontend/scripts/collect-surface.test.mjs` (gate, matn)

**Analog:** `frontend/scripts/blind-payload.test.mjs` — **to'liq shablon**
(469 qator, uchala qatlam: reyestr quyi chegarasi · izoh filtri IJOBIY va
SALBIY nazorat · katalog skani).

`stripComments()` — `blind-payload.test.mjs:144-206` **yoki**
`bulk-action-surface.test.mjs:163-225` (ikkalasi **bir xil** holat
mashinasi; UI-SPEC W0-F4 ikkinchisidan ko'chirishni buyuradi — **uchinchi
implementatsiya yozilmaydi**).

**Runaway nazorati (MAJBURIY)** — `blind-payload.test.mjs:208-227`:

```js
function readCode(file) {
  const raw = readFileSync(file, "utf8");
  const code = stripComments(raw);
  if (raw.includes("export")) {
    assert.ok(
      code.includes("export"),
      `${path.relative(FRONTEND_ROOT, file)}: izoh filtri faylni YUTIB YUBORDI ...`,
    );
  }
  return code;
}
```

**Quyi chegara (MAJBURIY)** — `blind-payload.test.mjs:104-121`:

```js
const MIN_FORBIDDEN_NAMES = 13;
...
const MIN_BLIND_COMPONENT_FILES = 3;
```

⚠ **Satr literallari SAQLANADI** va bu ATAYIN (`:37-39`): tarjima kaliti,
kesh kaliti yoki `data-testid` ichidagi taqiqlangan nom ham brauzerga
yetib boradi.

⚠ **Fayl mavjud bo'lmasa `skip` EMAS, OCHIQ QAYD** (`:339-351`): shunda
fayl tug'ilgan kuni shart **hech qanday tahrirsiz** ishlay boshlaydi.

### 3.9 `tests/unit/test_billable_from_slots.py` (test, jadval testi)

**Analog:** `tests/unit/test_aggregate_stall_slot.py:1-30` — **kutilgan
natija funksiyadan olinmaydi, LITERAL jadvalda yoziladi**:

```
KUTILGAN NATIJA FUNKSIYADAN OLINMAYDI — U LITERAL JADVALDA YOZILGAN.

`aggregate_stall_slot(...)` ni chaqirib natijani «kutilgan» deb saqlash
testni funksiyaning O'Z AKSIGA aylantirardi ...

  `ONE_AND_TWO_CAMERA_TABLE` — 1 va 2 kamerali BARCHA holat (3 + 9 = 12),
  `EXPECTED_BY_VERDICT_SET`  — yettita bo'sh bo'lmagan kichik to'plam

⚠ IKKI JADVAL BIR-BIRINI TEKSHIRADI
```

+ `test_the_combination_table_covers_every_case()` (`:127`) — `parametrize`
**jimgina bo'shab qolmasligi** uchun.

### 3.10 `tests/integration/test_phase6_criteria.py` (faza darvozasi)

**Analog:** `tests/integration/test_phase5_criteria.py:1118-1146` (**verbatim
meta-test**):

```python
def test_every_criterion_has_its_own_test() -> None:
    """Beshala mezon uchun AYNAN BITTA nomlangan test mavjud.
    ...
    ⚠ META-TESTNING O'Z NOMIDA `sc<raqam>` YO'Q va bu ataylab: darvoza
      `sc[1-5]` naqshini SANAYDI
    """
    module = sys.modules[__name__]
    names = sorted(
        name for name, obj in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and obj.__module__ == __name__
    )
    for number in range(1, 6):
        owned = [name for name in names if name.startswith(f"test_sc{number}_")]
        assert len(owned) == 1, ...
```

+ `test_criteria_module_uses_no_fakes()` (`:1148`) — **soxtalashtirishsiz
o'lchov** darvozasi (ikki mustaqil yo'l).

---

## 4. Shared Patterns — hamma faylga

### S-1. Xato **TURI** yoziladi, matni emas

`app/jobs/day_close.py:164-167` + `:191`:

```python
            result.errors.append(f"day_close_failed:{type(exc).__name__}")
```

> `retention.py::_swallow` qoidasi: istisno matni ombor manzilini yoki
> obyekt kalitini tashishi mumkin.

### S-2. «NOL — NATIJA» (`*Result` dataclass)

`day_close.py:130-150`:

```python
@dataclass(slots=True)
class DayCloseResult:
    """Bitta yugurishning O'LCHANADIGAN natijasi.

    ⛔ NOL — NATIJA, uning yo'qligi emas (`RetentionResult` qoidasi).
    """
    markets: int = 0
    ...
    errors: list[str] = field(default_factory=list)
```

`BillingCloseResult` da: `charged`, `skipped_unbilled`, `no_slot_rows`
(Pitfall 2!), `anomalies_unassigned`, `anomalies_closed_day`,
`anomalies_no_coverage`, `errors` — **hammasi har doim** qaytariladi.

### S-3. Audit yozuvi — `write_app_audit()`, qo'lda `INSERT` emas

`app/security/audit.py:253-315`. ⛔ `action: AuditAction` **enum bilan
tiplangan** — ya'ni yangi billing hodisasi **enum a'zosini** talab qiladi
(R-8b). `principal` berilsa `actor_user_id`/`market_id`/`request_id`/
`actor_label` **standart** olinadi (`:280-287`).

⚠ **Chaqiruvchi tranzaksiyani O'ZI yopadi** (`:291-294`): rad etish
yo'llarida audit qatori **commit qilinib**, KEYIN `HTTPException`
ko'tariladi.

### S-4. `market_is_open()` — kalendar mantig'i **TAKRORLANMAYDI**

`migrations/entities/functions.py:1345-1390` (uch qavatli `COALESCE`,
fail-closed, ⛔ **INVOKER**). Chaqiruv namunasi:
`capture_repo.py:334-336`.

### S-5. Pul chegarasi — `money.py`

`packages/sbozor-core/sbozor_core/money.py:65-85` (`assert_safe_soum` —
manfiy **rad**, `bool`/`float` **rad**) va `:87-100` (`format_soum` —
manfiyni **ko'rsatish uchun** qabul qiladi, NBSP ajratgich).

### S-6. Darvoza **quyi chegarasi** — bo'sh to'plam jimgina rost

Har darvozada `MIN_*` yoki `>=` nazorati:
`blind-payload.test.mjs:112`, `bulk-action-surface.test.mjs:72`,
`test_market_delete_guard.py:125` (`KNOWN_TENANT_TABLE_COUNT = 23`),
`test_route_coverage.py:49`, `error-codes.test.mjs:801`.

---

## 5. No Analog Found — ochiq bo'shliqlar

> Bu ro'yxat **planner uchun**: quyidagi shakllar uchun repoda nusxa
> olinadigan joy **yo'q**. Soxta analog berilmaydi.

| # | Shakl | Nima yo'q | Nima qilinadi |
|---|---|---|---|
| **5.1** | **Get-or-create: `ON CONFLICT DO NOTHING ... RETURNING` → bo'sh natija → ALOHIDA `SELECT`** | Repoda **birorta joyda** yo'q. `capture_repo.py:292-294` `RETURNING` ni oladi, lekin **qayta o'qimaydi**; `nvr_repo.py:506-521` `IntegrityError` ga tayanadi; `import_repo.py:148-156` `ON CONFLICT` ni **ataylab rad etadi** | ⛔ **A1 Wave 0 zondi** (`test_idempotency_concurrency.py`) — shakl `test_billable_anchor_probe.py` dan, **mazmun yangi**. READ COMMITTED oynasi rasmiy hujjatda **yozilmagan** (06-RESEARCH A1) |
| **5.2** | **`request_fingerprint` mos kelmasa 409** (Pitfall 4) | Repoda idempotentlik kaliti ↔ payload solishtiruvi **yo'q** | Stripe amaliyoti (06-RESEARCH § Secondary). ⚠ Bu D-21 ni **buzmaydi** — u faqat **aynan bir xil** so'rov uchun 200 talab qiladi |
| **5.3** | **`GENERATED ALWAYS AS (<plain column>) STORED`** (C-2 Variant B) | PG 18 da ruxsat etilishi **o'lchanmagan** | ⛔ **A2 Wave 0 zondi**. Variant A (tavsiya) baribir qoladi |
| **5.4** | `components/billing/variance-cell.tsx` — **ikki tomonlama ishora + tone + ikonka + yorliq** | Eng yaqini `ui/badge.tsx:28-43` tonlari; «delta katagi» domen qoidasi bilan **umumiy primitiv emas** | UI-SPEC §3.2/§3.3 da qaror yozilgan; §11.5 to'liq kontrakt beradi |
| **5.5** | `components/collect/collect-session.tsx` — **har takrorda nolga qaytadigan tranzaksiya oqimi** | `review-session.tsx` **navbatni** boshqaradi (band tugadi → keyingisi); bu esa **foydalanuvchi kiritgan** identifikatordan boshlanadi va **fokusni qaytaradi** | UI-SPEC §8.2–§8.7 to'liq yozadi (qadam mashinasi, `data-collect-step`, kalit hayot davri) |
| **5.6** | `components/collect/stall-lookup.tsx` — **navigator** (aynan bitta natijada darhol o'tadi) | `stall-filters.tsx` — **filtr** (ro'yxatni toraytiradi) | Kontrakt 2-fazada **allaqachon o'lchangan**: `02-UI-SPEC.md:503-513` (≤2 o'zaro ta'sir) |
| **5.7** | `components/billing/charge-detail-dialog.tsx` | `DL-5` (`05-UI-SPEC §11.7`) rasta **kunini** ko'rsatadi, hisobni emas — va u **slot qatorlarisiz** qurilgan | UI-SPEC §11.3 |
| **5.8** | `test_billing_delete_order_is_declared_not_derived` | `test_meta.py:1197` `DERIVED_ORDER_PATTERN` regeksi **`OCCUPANCY_DELETE_ORDER` ga qattiq yozilgan** — yangi ro'yxatni **qamramaydi** | Jufti yoziladi (D-32); regeks umumlashtirilishi **yoki** ikkinchi konstanta qo'shilishi mumkin — reja tanlaydi |
| **5.9** | `OCCUPANCY_GRANT_SIGNATURES` bo'shatilganda `0018` ning `_regrant` tsikli | `0019:71-137` **teskari** yo'nalishda presedent beradi (yangi migratsiyada muzlatilgan nusxa), lekin **eski migratsiyaga** muzlatilgan nusxa qo'yish presedenti **yo'q** | Reja tanlovni **ochiq yozadi**: (a) uchliklarni `0018` ga muzlatib ko'chirish, yoki (b) transient `EXECUTE TO PUBLIC` oynasini `0020` gacha **qabul qilib**, sababni yozish |
| **5.10** | Domen enum'lari uchun **backend↔frontend parity darvozasi** | `readPythonEnumValues` **faqat** `AuditAction` (`audit-actions.test.mjs:46-55`) va `Role` (`role-gate.test.mjs:174`) uchun; `HUMAN_ANSWERS` (`api-types.ts:1552`) hech qanday parity darvozasiga ega **emas** | ⛔ **Ochiq xavf.** Tavsiya: `billing-copy.test.mjs` ga `readPythonEnumValues(enums.py, "AnomalyKind")` **kabi to'rt solishtiruv** qo'shish (`audit-actions.test.mjs:63-68` naqshi). Aks holda backend a'zosi frontend ko'zgusisiz **jimgina** o'tadi |

---

## 6. ⛔ Tartib juftliklari — biri bo'lmasa suite QIZIL

> Planner bu juftliklarni **bir to'lqinda** rejalashtirishi shart. Aks
> holda to'lqinlar orasida `npm run test` / `npm run gate` **qizil**
> turadi va D-30 ning signali yo'qoladi («mening o'zgarishim buzdimi
> yoki bu o'sha ma'lum qizilmi?» — `test_meta.py:211-215` da o'lchangan).

| # | Artefakt A | Artefakt B | Nima qizaradi (A bor, B yo'q) | Manba |
|---|---|---|---|---|
| **OP-1** | `0020` 6 jadval yaratadi | `0021` kaskadni kengaytiradi | ⛔ `test_market_delete_guard.py::test_cascade_covers_every_table_referencing_markets` — **oltala nom bilan** (5-fazada aynan shunday bo'lgan) | `test_market_delete_guard.py:163-187`; `0019:10-21` |
| **OP-2** | `0020` `drop_entity(AUDIT_DRAW_DUE_MARKETS)` + `OCCUPANCY_DAY_CLOSE_MARKETS` | `DEFINER_SURFACES` bo'shatiladi **va** `OCCUPANCY_FUNCTIONS`/`OCCUPANCY_GRANT_SIGNATURES` bo'shatiladi | ⛔ `test_due_markets_functions_expose_only_identifiers` — `assert row is not None, "bazada topilmadi"`; **va** `test_autogenerate_is_empty` (reyestrda qolgan funksiya qayta yaratilishi taklif qilinadi) | `test_occupancy_domain_meta.py:558-564`, `:75-79`; `functions.py:1771-1793` |
| **OP-3** | `0020` jadvallarni yaratadi | `ALL_TENANT_TABLES` ga `*BILLING_TENANT_TABLES` splice | **IKKI TOMONLAMA:** splice **oldin** qilinsa → `alembic_utils` komparatori mavjud bo'lmagan jadvalga policy yaratib ko'radi → `test_autogenerate_is_empty` **`UndefinedTable`** (o'lchangan, 2026-08-04). **Keyin** qilinsa → `born <= ALL_TENANT_TABLES` qizil | `migrations/entities/__init__.py:433-472`; `test_meta.py:1135-1153` |
| **OP-4** | `schema_contract.py::AUDITED_TABLES` ga `charge_adjustments`/`cashier_shifts` | `0020` da `attach_audit_trigger(...)` | `test_meta.py::test_audited_tables_have_trigger` (`:907`). Muqobil: `PENDING_AUDIT_TRIGGERS` ga **ayni commitda** yozish — u **ikki tomonlama** (`missing == PENDING_AUDIT_TRIGGERS`), ya'ni trigger ulangach u yerdan **o'chirilishi** ham shart | `test_meta.py:204-247`; `schema_contract.py:177-186` |
| **OP-5** | `05-UI-SPEC.md` §15 G-18 qatoriga `` `components/collect/**` `` | birinchi `components/collect/*.tsx` **mahsulot** fayli (≥1, va tez orada ≥5) | ⛔ `bulk-action-surface.test.mjs:293-308` — «e'lon qilingan katalog mavjud va BO'SH EMAS»; `:314-318` `MIN_SCANNED_FILES = 5` | `bulk-action-surface.test.mjs:288-319`; UI-SPEC §15.4 |
| **OP-6** | `app/security/rbac.py` (2 huquq) | `frontend/src/lib/rbac.ts` (2 huquq) | ⛔ `role-gate.test.mjs:29-56` — ikkala faylni **matn sifatida** solishtiradi | `frontend/scripts/role-gate.test.mjs`; UI-SPEC W0-F1 |
| **OP-7** | `enums.py::AuditAction` yangi a'zo | `api-types.ts::AUDIT_ACTIONS` **va** `messages/{uz-Latn,ru,uz-Cyrl}.json` | ⛔ `audit-actions.test.mjs:63-68` (`deepEqual`) **va** `:84-89` (kalitlar **to'plami tengligi** — ortiqcha kalit ham qizartiradi) | `frontend/scripts/audit-actions.test.mjs` |
| **OP-8** | `POST /payments/{payment_id}/reverse`, `POST /shifts/{shift_id}/close` | `PARAM_FILLERS` ga `payment_id`, `shift_id` | ⛔ `test_route_coverage.py::test_no_unclassified_routes` (`:143-165`), `test_all_path_params_have_fillers` (`:223-237`) | `test_cross_tenant.py:252-395` |
| **OP-9** | `POST /payments`, `POST /payments/{id}/reverse` (`payment_create`) | `CASHIER_ROUTES` + `market_a_cashier_headers` + `headers_for` uchinchi shoxi | ⛔ `test_cross_tenant_object_returns_404` — **403** oladi va 404 asserti yiqiladi (`INSPECTOR_ROUTES` docstringida o'lchangan) | `test_cross_tenant.py:710-730`, `:1092-1113` |
| **OP-10** | `0020` qisman UNIQUE indeks yaratadi | Modelda ham `Index(..., unique=True, postgresql_where=...)` | ⛔ `test_autogenerate_is_empty` → **`remove_index`** (03-03 da o'lchangan) | `models/occupancy.py:350-358`; `0018:185-194` |
| **OP-11** | `charge_evidence` `(market_id, stall_slot_occupancy_id)` ga kompozit FK | `0020` **ayni migratsiyada, oldinroq** `uq_stall_slot_occupancy_market_id_id` | ⛔ Migratsiyaning **O'ZI** `asyncpg.exceptions.InvalidForeignKeyError` bilan yiqiladi (`0018:266-287` da o'lchangan) | `models/occupancy.py:972-1008` |
| **OP-12** | Yangi `billing_errors.py` kodlari | `billing-errors.ts` + `error-codes.test.mjs` bloki + 3 locale | ⛔ `error-codes.test.mjs` — zanjir uzilishi. ⚠ **Va teskari xavf:** `occupancy_errors.py` ga kod qo'shilsa `assert.equal(size, 15)` qizaradi | `error-codes.test.mjs:774-818` |

**Mexanik ravishda ushlanmaydigan (rejada ochiq nomlanadi):**

| Unutilsa | Nima bo'ladi | Nega ushlanmaydi |
|---|---|---|
| `BODY_FILLERS` yozuvi | Marshrut matritsada **422** oladi, tenant da'vosi **sinalmay** qoladi, darvoza **yashil** | `test_body_fillers_point_at_live_routes` faqat **eskirgan** yozuvni ushlaydi |
| `MINIMUM_MATRIX_ROUTES` ko'tarilmasa | Hech nima | Shart `>=` (quyi chegara) — `test_route_coverage.py:202` |
| `scheduler` konteyneri qayta ishga tushirilmasa | ⛔ `billing.close` **prodda hech qachon** ishlamaydi, xato ham chiqmaydi | Cron jadvali `import` paytida olinadi (`worker.py:55-58`) |
| `EXPECTED_COMPONENTS` / `alerting.py::watched` ga `billing_close` qo'shilmasa | Yurak urishining **yo'qligi** ko'rinmaydi | `day_close` uchun ham **bugun shunday** (§0.1 M-C) |
| Domen enum'i frontend ko'zgusisiz qolsa | UI eskirgan to'plamni ko'rsatadi | §5.10 — parity darvozasi **yo'q** |

---

## 7. Gotcha reyestri — «analog nima qiladi va uni o'tkazib yuborish qimmat»

| # | Gotcha | Manba (`path:line`) |
|---|---|---|
| 1 | `_MATERIALIZE_SLOT` **`DO UPDATE`** ishlatadi (hosila jadval); `daily_charges` esa **`DO NOTHING`** (o'zgarmas). Naqshni ko'chirish **teskari** qarorga olib boradi | `occupancy_repo.py:319-362` |
| 2 | `financial_guards()` `tariffs` uchun **ATAYIN chaqirilmagan** — uchala qo'riqchi qo'lda | `0008_temporal.py:164-182` |
| 3 | `business_date` **GENERATED** — unga aniq qiymat yozish **RAD ETILADI** | `tests/integration/test_business_date.py:134-145`; `migrations/helpers.py:357-361` |
| 4 | `require_any_permission()` — **yopiq to'plam** (`assert gated == sorted(SNAPSHOT_EVIDENCE_FRAME_ROUTES)`) | `test_personal_data_coverage.py:691-706` |
| 5 | `ON CONFLICT DO NOTHING ... RETURNING` konfliktda **hech nima qaytarmaydi** → `None` ni «xato» deb 500 qilish Pitfall 3 | `capture_repo.py:140`; PG 18 `INSERT` docs |
| 6 | `_PER_STALL_CTE.human_confirmed` `verdict` bilan **bog'lanmagan** → billingda ishlatilishi **jim noto'g'ri hisob** | `occupancy_repo.py:369` (C-6) |
| 7 | `stall_slot_occupancy` **MUTABLE** → `id` muzlatilgan dalil **emas**; dalil `occupancy_event_id` | `occupancy_repo.py:341-361` (C-7) |
| 8 | `stall_slot_occupancy` da `UNIQUE (market_id, id)` **YO'Q** → kompozit FK bugun **imkonsiz** | `models/occupancy.py:972-1008` |
| 9 | `NULL` UNIQUE indeksda **o'ziga teng emas** → qisman indeks predikat bilan | `models/snapshot.py:211-222` |
| 10 | `market_is_open()` **INVOKER** va fail-closed → tenant kontekstsiz **hamma kun yopiq** | `functions.py:1369-1376`; Pitfall 9 |
| 11 | Vitest `.ts` test faylini **jimgina tashlab ketadi** — `.test.tsx` shart | `frontend/vitest.config.ts:34` |
| 12 | `node --test` TS import qilmaydi → `scripts/*.test.mjs` fayllarni **matn** sifatida o'qiydi | `frontend/package.json:14` |
| 13 | `messages/uz-Cyrl.json` **generatsiya** — qo'lda tahrir `i18n:check` ni qizartiradi | `frontend/package.json:19` |
| 14 | `error-codes.test.mjs` bandlik reyestrida **aniq son** (`15`, `9`, `6`) | `error-codes.test.mjs:795-818` |
| 15 | `AUDIT_TABLES` (api-types.ts) — audit **filtr** ro'yxati, DB `AUDITED_TABLES` bilan **bog'lanmagan**; unga qo'shish **kerak emas** | `api-types.ts:274-280`; `audit-actions.test.mjs:92-103` |
| 16 | `BILLING_DELETE_ORDER` **LITERAL** yoziladi; `tuple(reversed(...))` shakli manba matnidan **skanerlanadi** (5-faza uchun) | `test_meta.py:1195-1207`; `migrations/entities/__init__.py:393-424` |
| 17 | Nomlar 63 baytga kesiladi → SQLAlchemy `IdentifierError` | `models/occupancy.py:997-1002` |
| 18 | `_regrant()` **MAJBURIY** — `CREATE FUNCTION` `EXECUTE TO PUBLIC` ni standart beradi | `0018:242-251`; `0019:154-163` |
| 19 | Snapshot bloki kaskadda **oldin** turishi kerak; billing bloki esa **snapshot/occupancy bloklaridan OLDIN** (agar `charge_evidence` `occupancy_events` ga tayansa) | `migrations/entities/__init__.py:412-417`; `0019:23-29` |
| 20 | `taskiq` **faqat `worker.py` da** import qilinadi | `day_close.py:51` |
| 21 | Faza darvozasi meta-testining o'z nomida `sc<raqam>` **bo'lmasligi** shart | `test_phase5_criteria.py:1125-1128` |
| 22 | Kassir seed'i **tayyor** (`AuthSeed.cashier`, `must_change_password=False`) — yangi seed **yozilmaydi** | `tests/fixtures/auth_users.py:75`; `two_markets.py:222,247` |

---

## 8. Metadata

**Analog qidiruv qamrovi:** `migrations/` (versions + entities + helpers),
`packages/sbozor-core/sbozor_core/` (models, enums, money, periods,
timeutil, occupancy, schema_contract), `services/core-api/app/`
(api/v1, jobs, repositories, security, services, worker, main, deps,
schemas), `tests/` (tenancy, integration, unit, fixtures),
`frontend/src/` (app, components, lib), `frontend/scripts/`,
`frontend/messages/`, `package.json`.

**Fayllar o'qildi (targeted, takrorsiz):** 41
**Reuse qilingan 06-RESEARCH § Sources sitatalari:** 24 (qayta
o'lchanmadi)
**Bu sessiyada QO'SHIMCHA o'lchangan va research'da YO'Q edi:** §0.1 M-A
(`assert row is not None`), §0.1 M-B (`size == 15`), §0.1 M-C
(`EXPECTED_COMPONENTS` da `day_close` yo'q), §5.10 (enum parity
darvozasining yo'qligi), §2 R-5 (huquq e'lonining **ikki** konventsiyasi va
tanlov mexanikasi), §6 OP-9 (`CASHIER_ROUTES` — mavjud bo'lmagan uchinchi
rol ro'yxati), §7/22 (kassir seed'i tayyor).

**Pattern extraction date:** 2026-08-10

---
*Phase: 06-billing-va-kassir*
