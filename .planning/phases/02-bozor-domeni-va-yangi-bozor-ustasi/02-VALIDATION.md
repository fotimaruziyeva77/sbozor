---
phase: 2
slug: bozor-domeni-va-yangi-bozor-ustasi
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-30
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `02-RESEARCH.md` § Validation Architecture (lines 1243–1313).
> The **Per-Task Verification Map** below is a stub — the planner fills it from `02-01-PLAN.md` … `02-NN-PLAN.md`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`) + testcontainers 4.15.0 — **all present from Phase 1, no framework install needed** |
| **Config file** | `pyproject.toml` (repo root, `[tool.pytest.ini_options]`, `pythonpath = [".", "tests", "services/core-api"]`, marker: `tenancy`) |
| **Database** | **`postgres:18.4-trixie`, connected as `sbozor_app`** — `tests/conftest.py` |
| **Frontend** | vitest 4.1.10 + jsdom 30.0.1 + Testing Library; `node --test` for scripts |
| **Quick run command** | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Tenancy gate command** | `npm run test:tenancy` |
| **Full suite command** | `npm run test` → `docker compose --profile test run --rm tests pytest -q` |
| **Frontend suite command** | `npm --prefix frontend test` |
| **Phase gate command** | `npm run gate` (lint + mypy + backend + tenancy + i18n + typecheck + eslint + build) |
| **Estimated runtime** | Phase 1 measured: quick **8 s** · full **47 s** · tenancy **20 s**. Phase 2 adds ~9 tables and ~8 integration files — **re-measure at the phase gate task**, do not carry Phase 1 numbers forward as fact |

**Forbidden:** SQLite (RLS does not exist there). The test engine MUST connect as `sbozor_app`, never as a superuser — `FORCE ROW LEVEL SECURITY` does not constrain superusers, so a superuser fixture makes every RLS test falsely green.

**New infrastructure prerequisite (Pitfall 1):** `btree_gist` must exist before the first Phase 2 migration runs. `sbozor_owner` is `NOCREATEDB` and returns `permission denied to create extension` — the extension must be created by a superuser init step (`ops/db/init/00-extensions.sql`) and read by `tests/conftest.py`.

---

## Sampling Rate

- **After every task commit:** `docker compose --profile test run --rm tests pytest tests/unit -x -q` + the integration file for the changed module
- **After every plan wave:** `npm run test` + `npm run test:tenancy` + `npm --prefix frontend test`
- **Before `/gsd-verify-work`:** `npm run gate` fully green
- **Max feedback latency:** target ≤30 s at task level, ≤180 s at wave level (Phase 1 budgets; confirm by measurement)

---

## Per-Task Verification Map

> **Filled by the planner (2026-07-31).** 17 plans / 51 tasks. Every task carries an `<automated>` verify command; three tasks additionally carry `<human-check>` steps (real Karmana data, usability walkthrough, perceptual map check) which are recorded under **Manual-Only Verifications** below.
>
> Wave 0 work is **not** a separate wave here — it is plans `02-01` (backend gates) and `02-02` (frontend design-system gates), both in wave 1, plus the mandatory ordering chain in `02-03`. Every later plan depends on them transitively.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-01 | Sxema reyestrlari va RBAC matritsasini 2-faza uchun to'g'rilash | unit | `npm run test:unit` | ⬜ | ⬜ pending |
| 02-01-02 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-02 | `btree_gist` superuser init qadami, conftest ulanishi va `require_extension()` yordamchisi | tenancy | `npm run test:tenancy` | ⬜ | ⬜ pending |
| 02-01-03 | 01 | 1 | MARKET-01,MARKET-02,MARKET-03,MARKET-04 | T-02-03 | WR-02/WR-03 — `select-market` ni parol darvozasi ostiga olish va `is_platform_admin` ni DB'dan qayta o'qish | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-02-01 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-09 | Dizayn tokenlarini WCAG AA ga keltirish va boshqaruv elementlarini yangi tokenlarga ko'chirish | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-02-02 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-10 | Yetti `ui/` primitivini ajratish + tipografiya va bo'shliq panjarasini mexanik tozalash | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ⬜ | ⬜ pending |
| 02-02-03 | 02 | 1 | MARKET-01,MARKET-02,MARKET-06 | T-02-11 | Transliterator defektlarini yopish va frontend testlarini faza darvozasiga ulash | component | `npm --prefix frontend test && npm --prefix frontend run i18n:check` | ⬜ | ⬜ pending |
| 02-03-01 | 03 | 2 | MARKET-01 | T-02-15 | Zanjir 1–2-bandlari — `auth_memberships()` qaytish tipi va `Membership.is_active` | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ⬜ | ⬜ pending |
| 02-03-02 | 03 | 2 | MARKET-01 | T-02-16 | Zanjir 3–4-bandlari — `MarketRef.is_active` va serverdagi filtrni olib tashlash | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-03-03 | 03 | 2 | MARKET-01 | T-02-17 | Zanjir 5–6-bandlari — zod kontrakti, `Qoralama` belgisi va uzilgan ustaga qaytish | component | `npm --prefix frontend run test:component && npm --prefix frontend run i18…` | ⬜ | ⬜ pending |
| 02-04-01 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-20 | `StallStatus` enum'i va `[)` davr yordamchisi | unit | `npm run test:unit` | ⬜ | ⬜ pending |
| 02-04-02 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-21 | O'nta domen modeli (`models/market.py`) va barrel importi | gate | `docker compose --profile test run --rm tests sh -c "python -c 'from sbozo…` | ⬜ | ⬜ pending |
| 02-04-03 | 04 | 3 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-22 | DB funksiyalari, trigger funksiyalari va entity reyestrlari | gate | `docker compose --profile test run --rm tests sh -c "python -c 'from migra…` | ⬜ | ⬜ pending |
| 02-05-01 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-29 | `0007_market_domain.py` — yadro jadvallar, RLS, audit va rasta-kod kafolati | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ⬜ | ⬜ pending |
| 02-05-02 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-30 | `0008_temporal.py` — tarif va toifa tarixi + o'zgarmaslik triggerlari | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ⬜ | ⬜ pending |
| 02-05-03 | 05 | 4 | MARKET-01,MARKET-02,MARKET-03 | T-02-31 | Alembic ko'rmaydigan narsalar uchun meta-test darvozasi + bo'sh autogenerate diff | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_ma…` | ⬜ | ⬜ pending |
| 02-06-01 | 06 | 5 | MARKET-04,MARKET-05 | T-02-37 | `0009_vendors.py` — sotuvchilar va qoplanmaydigan biriktirish davrlari | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ⬜ | ⬜ pending |
| 02-06-02 | 06 | 5 | MARKET-04,MARKET-05 | T-02-38 | `0010_calendar.py` — ish kunlari istisnolari, `market_is_open()` va `market_delete_draft()` | gate | `docker compose --profile migrate run --rm migrate alembic upgrade head &&…` | ⬜ | ⬜ pending |
| 02-06-03 | 06 | 5 | MARKET-04,MARKET-05 | T-02-39 | Ikki bozorli domen seed'i va EXCLUDE/`market_is_open` darvozalari | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ⬜ | ⬜ pending |
| 02-07-01 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-46 | Tarif va toifa tarixi — SC#3 ning to'liq isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-07-02 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-47 | Sotuvchi biriktirish — D-09/D-10/D-11/D-12 isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-07-03 | 07 | 6 | MARKET-02,MARKET-03,MARKET-04,MARKET-05 | T-02-48 | Ish kunlari kalendari (SC#4) va rasta raqamining qayta ishlatilmasligi (SC#2/D-02) | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-08-01 | 08 | 7 | MARKET-02,MARKET-06 | T-02-54 | Domen DTO'lari, xato kodlari va oddiy reestrlar (zonalar, toifalar) | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ⬜ | ⬜ pending |
| 02-08-02 | 08 | 7 | MARKET-02,MARKET-06 | T-02-55 | `stall_repo.py` va `stalls.py` — reestr, keyset, filtrlar va xarita agregati | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ⬜ | ⬜ pending |
| 02-08-03 | 08 | 7 | MARKET-02,MARKET-06 | T-02-56 | Marshrutlarni ulash, cross-tenant matritsasiga qo'shish va SC#2 ning API isboti | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-09-01 | 09 | 8 | MARKET-03,MARKET-05 | T-02-62 | `tariff_repo.py` va `tariffs.py` — faqat qo'shadigan tarif API'si | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ⬜ | ⬜ pending |
| 02-09-02 | 09 | 8 | MARKET-03,MARKET-05 | T-02-63 | `calendar.py` — haftalik jadval va istisno kunlar | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-09-03 | 09 | 8 | MARKET-03,MARKET-05 | T-02-64 | Tarif va kalendar API'sining integratsiya testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-10-01 | 10 | 9 | MARKET-04 | T-02-70 | `vendor_repo.py` va `vendors.py` — reestr va shaxsiy ma'lumot o'qish auditi | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ⬜ | ⬜ pending |
| 02-10-02 | 10 | 9 | MARKET-04 | T-02-71 | `assignments.py` — biriktirish davrlari va almashinuv oqimi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-10-03 | 10 | 9 | MARKET-04 | T-02-72 | Sotuvchi va biriktirish API'sining integratsiya testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-11-01 | 11 | 10 | MARKET-01 | T-02-79 | `market_repo.py` va qoralama bozor yaratish / o'chirish | gate | `docker compose --profile test run --rm tests sh -c "ruff check . && mypy …` | ⬜ | ⬜ pending |
| 02-11-02 | 11 | 10 | MARKET-01 | T-02-80 | `setup-status` agregati va faollashtirish darvozasi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-11-03 | 11 | 10 | MARKET-01 | T-02-81 | SC#1 ning uchidan-uchiga testi va RBAC darvozasi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-12-01 | 12 | 11 | MARKET-02,MARKET-04 | T-02-87 | Xavfsiz `.xlsx` o'qish qatlami va uning hujum testlari | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_xlsx_…` | ⬜ | ⬜ pending |
| 02-12-02 | 12 | 11 | MARKET-02,MARKET-04 | T-02-88 | Validator (yozishdan oldin) va shablon/xato-hisoboti generatori | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_xlsx_…` | ⬜ | ⬜ pending |
| 02-12-03 | 12 | 11 | MARKET-02,MARKET-04 | T-02-89 | `imports.py` routeri va all-or-nothing / idempotentlik testlari | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-13-01 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-98 | Zod kontraktlari va xato-kod xaritasi | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ⬜ | ⬜ pending |
| 02-13-02 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-99 | TanStack Query hooklari va navigatsiya kengaytmasi | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-13-03 | 13 | 12 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-100 | To'qqizta namespace uchun uch tilli matnlar | component | `npm --prefix frontend run i18n:check && npm --prefix frontend test` | ⬜ | ⬜ pending |
| 02-14-01 | 14 | 13 | MARKET-02,MARKET-06 | T-02-105 | Rastalar reestri sahifasi — ro'yxat, filtrlar va tahrir dialoglari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-14-02 | 14 | 13 | MARKET-02,MARKET-06 | T-02-106 | Sxematik plan-xarita — grid, katak, tone kontrakti va legenda | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-14-03 | 14 | 13 | MARKET-02,MARKET-06 | T-02-107 | Rasta kartasi dialogi va xarita darvozasi (vitest) | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ⬜ | ⬜ pending |
| 02-15-01 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-112 | Sotuvchilar reestri va biriktirish oqimi | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ⬜ | ⬜ pending |
| 02-15-02 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-113 | Tarif tarixi, zona va toifa ro'yxatlari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-15-03 | 15 | 13 | MARKET-03,MARKET-04,MARKET-05 | T-02-114 | Ish kunlari kalendari | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-16-01 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-120 | Usta qobig'i, qadam relsi va marshrutlar | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ⬜ | ⬜ pending |
| 02-16-02 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-121 | Rekvizitlar formasi va faollashtirish paneli | component | `npm --prefix frontend run typecheck && npm --prefix frontend run lint && …` | ⬜ | ⬜ pending |
| 02-16-03 | 16 | 14 | MARKET-01,MARKET-02,MARKET-04 | T-02-122 | Excel import paneli va xato ro'yxati | component | `npm --prefix frontend run test:component && npm --prefix frontend run typ…` | ⬜ | ⬜ pending |
| 02-17-01 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-128 | Real ma'lumot yo'riqnomasi va takrorlanadigan import skripti | gate | `node scripts/karmana-import.mjs --help && node -e "const fs=require('node…` | ⬜ | ⬜ pending |
| 02-17-02 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-129 | Beshta faza mezonining uchidan-uchiga avtomatik tekshiruvi | integration | `docker compose --profile test run --rm tests pytest tests/integration/tes…` | ⬜ | ⬜ pending |
| 02-17-03 | 17 | 15 | MARKET-01,MARKET-02,MARKET-03,MARKET-04,MARKET-05,MARKET-06 | T-02-130 | Real ma'lumotni yuklash, solishtirish va faza darvozasi | gate + human-check | `npm run gate` | ⬜ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Coverage anchors the planner must not drop** (each already has a named command in RESEARCH.md):

| Requirement | Anchor behavior | Test file |
|-------------|-----------------|-----------|
| MARKET-01 / SC#1 | Wizard end-to-end reaches `is_active=true`; incomplete market → 409 with missing-step list | `tests/integration/test_wizard_flow.py` |
| MARKET-02 / SC#2 | Stall status transitions audited **including raw SQL**; closed stall code cannot be reused | `tests/integration/test_stall_registry.py`, `test_stall_code_reuse.py` |
| MARKET-03 / SC#3 | Past date keeps old price; effective day uses new price; past tariff immutable via raw SQL; existing row never touched | `tests/integration/test_tariff_history.py` |
| MARKET-04 | Overlapping assignment → 23P01; handover day boundary; vacancy gap → 0 rows; phone unique per market; vendor read audited | `tests/integration/test_stall_assignments.py`, `test_vendors.py` |
| MARKET-05 / SC#4 | Weekly closure + holiday + exception-open all resolve through `market_is_open()`; fail-closed on missing config | `tests/integration/test_market_calendar.py` |
| MARKET-06 / SC#5 | Map renders zone blocks in code order; stall click opens card; 1000 cells render without full re-render on select | `frontend/src/components/stalls/stall-map.test.tsx` |
| Import (D-13/D-14/D-15) | All-or-nothing with per-row line numbers; re-import idempotent; billion-laughs + zip-bomb rejected; formula injection escaped | `tests/integration/test_stall_import.py`, `tests/unit/test_xlsx_reader.py`, `test_xlsx_template.py` |
| FOUND-02 (regression) | All 9 new tables carry `market_id` + RLS ENABLE+FORCE + tenant policy + `market_id`-leading indexes | `tests/tenancy/test_meta.py` (**existing, automatic**) |
| Cross-tenant (regression) | Every new endpoint returns **404** for another tenant's object; uncovered routes fail CI | `tests/tenancy/test_cross_tenant.py`, `test_route_coverage.py` (**existing, automatic**) |

---

## Wave 0 Requirements

Two of these are **inherited landmines from Phase 1** and must land before the first Phase 2 migration — otherwise the existing meta-tests go red on the first table created.

- [ ] `packages/sbozor-core/sbozor_core/schema_contract.py` — remove `stall_assignments` from `FINANCIAL_TABLES` (with a reason comment); extend `AUDITED_TABLES` to the 6 domain tables — **Pitfall 3**
- [ ] `services/core-api/app/security/rbac.py` — grant `PLATFORM_ADMIN` the `STALL_MANAGE` / `TARIFF_MANAGE` / `VENDOR_MANAGE` permissions; add the two new `Permission` members — **Pitfall 6** (without this, the person running the wizard cannot enter stalls or tariffs into the market they are building)
- [ ] `ops/db/init/00-extensions.sql` + read it from `tests/conftest.py` — `btree_gist` — **Pitfall 1**
- [ ] `tests/fixtures/market_domain.py` — two-market seed (zone / category / stall / tariff / vendor / assignment), layered on the existing `two_markets.py`
- [ ] `tests/tenancy/test_market_domain_meta.py` — asserts the EXCLUDE constraint exists, `tariff_past_immutable` trigger exists, `stall_code_claim` trigger exists, and `market_is_open` is **NOT** `SECURITY DEFINER` — **Pitfall 2** (Alembic cannot see `ExcludeConstraint` drift in either direction; this meta-test is the only guard)
- [ ] `tests/integration/test_{tariff_history,stall_assignments,market_calendar,stall_import,wizard_flow,stall_registry,stall_code_reuse,vendors}.py` — stubs
- [ ] `tests/unit/test_{xlsx_reader,xlsx_template}.py` — parser limits, billion-laughs smoke test, formula injection
- [ ] `frontend/src/components/stalls/stall-map.test.tsx` — vitest + jsdom (infrastructure ready from Phase 1)
- [ ] `tests/tenancy/test_route_coverage.py` — register the new routes (CI goes red until done — **this is deliberate**)

**Framework install:** not required — every tool is present from Phase 1.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real Karmana data actually loads (~300–1000 stalls) and the numbers match the administration's own register | MARKET-01, MARKET-02 | Requires the real spreadsheet from the market administration; cannot be fixtured | Run the import against the real file; compare stall count and per-zone totals with the administration's paper register; record deltas |
| The wizard is completable by a non-developer without code | MARKET-01 / SC#1 | "No code written" is a usability claim, not a source assertion | Platform admin walks the wizard start→finish on a clean market; observe without assisting; record every point they get stuck |
| Schematic map is readable at real scale on the admin's actual screen | MARKET-06 / SC#5 | Perceptual — jsdom cannot judge legibility | Open the map with real Karmana zone/stall counts on the target device; confirm zone blocks and stall numbers are readable without zooming |
| Business-requisite formats (STIR, address fields) match the customer's real documents | MARKET-01 | Research confidence is **LOW** here (assumptions A1/A2 — official regulation not read) | Show the market-requisites form to the customer; confirm STIR digit count and required fields before the form is frozen |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (9 items above)
- [ ] No watch-mode flags
- [ ] Feedback latency measured and recorded (do not carry Phase 1 numbers forward)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
