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

> **STUB — planner must fill.** One row per task across all Phase 2 plans. Every row needs an automated command or an explicit Wave 0 dependency. The requirement→test mapping to draw from is in `02-RESEARCH.md` § "Phase Requirements → Test Map" (35 rows, already written against SC#1–SC#5, D-02…D-20 and the six MARKET-* requirements).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | — | — | — | — | — | — | ⬜ pending |

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
