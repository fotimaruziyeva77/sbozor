---
phase: 1
slug: poydevor-va-tenant-xavfsizligi
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-29
updated: 2026-07-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Planner filled the map from `01-01-PLAN.md` … `01-10-PLAN.md`.
> Plan **01-10 / Task 2** finalized the measured runtimes, flipped `wave_0_complete: true` and signed off.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 (real `postgres:18.4-trixie` + `valkey:9.1.1-alpine`) |
| **Config file** | `pyproject.toml` (repo root, `[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) — created by 01-01 / Task 2 |
| **Quick run command** | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Full suite command** | `docker compose --profile test run --rm tests pytest -q` |
| **Tenancy gate command** | `docker compose --profile test run --rm tests pytest tests/tenancy -q` |
| **Frontend gate command** | `npm --prefix frontend run i18n:check && npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` |
| **Phase gate command** | `npm run gate` (created by 01-10 / Task 2) |
| **Estimated runtime** | **measured 2026-07-29** — quick **8 s** (154 unit tests) · full **47 s** (375 tests) · tenancy gate **20 s** (94 tests) · lint+types **7 s** |
| **CI escape hatch** | `TEST_DATABASE_URL` / `TEST_VALKEY_URL` env — if set, `conftest.py` skips container startup and uses those instances |

**Measurement conditions:** Windows 11 host, Docker Desktop 29.4.2 / Compose v5.1.3, **warm image** (`docker compose --profile test build tests` already done). Figures are wall-clock including container start; pytest itself reports 44.4 s (full) and 14.2 s (tenancy). The first-ever run additionally pays a one-off image pull/build (~3–5 min) — deliberately **excluded**, per the measurement rule in the plan.

**Forbidden:** SQLite (RLS does not exist there → the most dangerous code path would be untested). Test engine MUST connect as `sbozor_app`, never as `postgres` superuser — `FORCE ROW LEVEL SECURITY` does not constrain superusers, so a superuser fixture makes every RLS test falsely green.

---

## Sampling Rate

- **After every task commit:** `docker compose --profile test run --rm tests pytest tests/unit -x -q` (+ `ruff check .`)
- **After every plan wave:** full suite + `tests/tenancy` + frontend gate
- **Before `/gsd-verify-work`:** `npm run gate` — everything green, `tests/tenancy` mandatory
- **Max feedback latency:** **measured** — task level **8 s** (quick run), wave level **73 s** (backend chain `lint` → `test` → `test:tenancy`). Both sit far below the 30 s / 180 s budgets set at planning time, so the sampling rate never became a reason to skip a check.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | FOUND-02 | T-01-01, T-01-03, T-01-04 | App DB role is `NOSUPERUSER NOBYPASSRLS`; no secrets in repo; DB port not published | integration (SQL) | `docker compose config --quiet && docker compose up -d db cache --wait && docker compose exec -T db psql -U postgres -d sbozor -c "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='sbozor_app'"` | ✅ | ✅ green |
| 01-01-T2 | 01-01 | 1 | FOUND-02 | T-01-07, T-01-SC | Pinned versions, `uv.lock` committed, non-root runtime, no `passlib`/`python-jose` | build + import | `docker compose --profile test build tests && docker compose --profile test run --rm tests python -c "import sbozor_core, fastapi, jwt, pwdlib"` | ✅ | ✅ green |
| 01-01-T3 | 01-01 | 1 | FOUND-02 | T-01-02, T-01-05, T-01-06 | Test engine connects as `sbozor_app`; app cannot disable triggers; `CREATE` revoked from PUBLIC | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_meta.py -x -q` | ✅ | ✅ green |
| 01-02-T1 | 01-02 | 1 | FOUND-04 | T-01-SC | No `@eloqnt/cli` (unlicensed), no `react-leaflet` (Hippocratic-2.1), TS pinned 5.9.3 | build | `npm --prefix frontend run typecheck && npm --prefix frontend run build` | ✅ | ✅ green |
| 01-02-T2 | 01-02 | 1 | FOUND-04 | T-01-08 | `proxy.ts` (not `middleware.ts`) — silent locale-routing loss prevented | build + HTTP | `npm --prefix frontend run build` + `curl -s -o /dev/null -w "%{redirect_url}" http://localhost:3000/` | ✅ | ✅ green |
| 01-02-T3 | 01-02 | 1 | FOUND-04 | T-01-09, T-01-11 | ICU placeholders never transliterated; key + ICU-arg parity across 3 locales | unit (node) | `npm --prefix frontend run i18n:gen && npm --prefix frontend run i18n:check` | ✅ | ✅ green |
| 01-03-T1 | 01-03 | 2 | FOUND-05 | T-01-19 | Money is `int` only (`float`/`bool` rejected); business day shifts at Tashkent midnight | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_money.py tests/unit/test_timeutil.py tests/unit/test_phone.py -x -q` | ✅ | ✅ green |
| 01-03-T2 | 01-03 | 2 | FOUND-01 | T-01-12, T-01-13, T-01-14, T-01-15, T-01-18 | `alg=none` / alg-confusion / type-confusion / short-key rejected; Argon2id + dummy verify | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_jwt.py tests/unit/test_password.py -x -q` | ✅ | ✅ green |
| 01-03-T3 | 01-03 | 2 | FOUND-05 | T-01-16, T-01-17 | Tenant GUC only inside an open transaction; secrets censored from logs | import + type | `docker compose --profile test run --rm tests sh -c "python -c 'from sbozor_core.tenancy import SET_TENANT_CONTEXT' && mypy packages/sbozor-core"` | ✅ | ✅ green |
| 01-04-T1 | 01-04 | 3 | FOUND-02 | T-01-21, T-01-22 | RLS predicate uses `NULLIF(...)` (fail-closed); `enable_tenant_rls` covers ENABLE+FORCE+GRANT | unit (SQL gen) | `docker compose --profile test run --rm tests python -c "from migrations.entities.policies import tenant_policy; print(tenant_policy('x').to_sql_statement_create())"` | ✅ | ✅ green |
| 01-04-T2 | 01-04 | 3 | FOUND-01, FOUND-02 | T-01-23, T-01-25, T-01-26 | `users` revoked from app role; login only via `SECURITY DEFINER` with pinned `search_path` | integration | `docker compose --profile test run --rm tests pytest tests/tenancy/test_login_bootstrap.py -x -q` | ✅ | ✅ green |
| 01-04-T3 | 01-04 | 3 | FOUND-02 | T-01-20, T-01-24, T-01-27 | Every tenant table has `market_id` + RLS ENABLE **and** FORCE + policy; `markets` special case asserted explicitly (`test_markets_rls_and_policy`: ENABLE+FORCE and `id = GUC` policy); no `BYPASSRLS` role exists | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ✅ | ✅ green |
| 01-05-T1 | 01-05 | 4 | FOUND-03 | T-01-30, T-01-31, T-01-32, T-01-35 | `audit_log` 4-layer immutability; trigger fn is NOT `SECURITY DEFINER` | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_immutable.py -x -q` | ✅ | ✅ green |
| 01-05-T2 | 01-05 | 4 | FOUND-03 | T-01-29, T-01-33, T-01-34 | Raw SQL bypassing the ORM is still audited; no-op update writes nothing; cross-tenant audit read is empty | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_write.py tests/integration/test_audit_immutable.py tests/tenancy/test_meta.py -x -q` | ✅ | ✅ green |
| 01-05-T3 | 01-05 | 4 | FOUND-05 | T-01-36, T-01-37, T-01-38 | `business_date` STORED generated column; `CHECK(amount_soum > 0)`; `ON CONFLICT DO NOTHING` idempotent | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_business_date.py tests/integration/test_money_constraints.py tests/integration/test_idempotency.py -x -q` | ✅ | ✅ green |
| 01-06-T1 | 01-06 | 5 | FOUND-01 | T-01-45, T-01-48 | RBAC matrix hard-coded (director cannot manage — D-07); no f-string SQL | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_rbac_matrix.py -x -q` | ✅ | ✅ green |
| 01-06-T2 | 01-06 | 5 | FOUND-01, FOUND-03 | T-01-42, T-01-43, T-01-46, T-01-47, T-01-49 | httpOnly + SameSite=Lax + Path-scoped refresh cookie; no self-registration route; RLS error → 404 | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_auth_login.py -x -q` | ✅ | ✅ green |
| 01-06-T3 | 01-06 | 5 | FOUND-01 | T-01-39, T-01-40, T-01-41, T-01-44 | No user enumeration (identical body); rate limit; refresh reuse revokes family; block is immediate | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_auth_login.py tests/integration/test_auth_refresh.py tests/integration/test_user_block.py -x -q` | ✅ | ✅ green |
| 01-07-T1 | 01-07 | 6 | FOUND-01 | T-01-50, T-01-51, T-01-52, T-01-56, T-01-59 | Market admin may assign only `{cashier, inspector}` — `market_admin`/`director`/`platform_admin` → 403 `role_not_allowed` (D-04); cross-tenant user op → 404 (not 403); temp password never logged/audited; cache invalidated on block | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_users_api.py -x -q` | ✅ | ✅ green |
| 01-07-T2 | 01-07 | 6 | FOUND-04 | T-01-51 | Locale persisted in DB profile; `/markets` never uses BYPASSRLS | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_me_locale.py -x -q` | ✅ | ✅ green |
| 01-07-T3 | 01-07 | 6 | FOUND-03 | T-01-53, T-01-54, T-01-55, T-01-57 | Audit visible only to D-11 roles; viewing audit writes a `read` record; keyset pagination, `limit ≤ 200` | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_read.py tests/integration/test_users_api.py -x -q` | ✅ | ✅ green |
| 01-08-T1 | 01-08 | 6 | FOUND-01 | T-01-60, T-01-67 | Access token in memory only (no `localStorage`); single-flight refresh, one retry | build + grep | `npm --prefix frontend run typecheck && npm --prefix frontend run build && ! grep -rq "localStorage\|sessionStorage" frontend/src/` | ✅ | ✅ green |
| 01-08-T2 | 01-08 | 6 | FOUND-01, FOUND-04 | T-01-63, T-01-64 | One generic `invalid_credentials` message; no register / forgot-password affordance | build + i18n | `npm --prefix frontend run i18n:check && npm --prefix frontend run build` | ✅ | ✅ green |
| 01-08-T3 | 01-08 | 6 | FOUND-04 | T-01-61, T-01-65, T-01-66 | One-click locale switch (URL + `PATCH /me`); protected layer refreshes before redirecting | build + **manual** | `npm --prefix frontend run i18n:check && npm --prefix frontend run lint && npm --prefix frontend run build` + `<human-check>` (8 steps, see 01-08 Task 3) | ✅ | ✅ green |
| 01-09-T1 | 01-09 | 7 | FOUND-01 | T-01-68 | Temp password shown once, never logged or stored; role picker is multi-select (D-05) and lists only cashier/inspector for non-platform-admin creators (D-04) | build + grep | `npm --prefix frontend run i18n:check && npm --prefix frontend run build && ! grep -rq "console.log" frontend/src/components/users/` | ⏳ | ⏳ parallel |
| 01-09-T2 | 01-09 | 7 | FOUND-03, FOUND-04 | T-01-69, T-01-70, T-01-72, T-01-73, T-01-74 | Audit list is read-only, masked values preserved, no `dangerouslySetInnerHTML` | build + full suite + **manual** | `npm --prefix frontend run i18n:check && npm --prefix frontend run build && docker compose --profile test run --rm tests pytest -q` + `<human-check>` (15 steps = the 5 phase criteria) | ⏳ | ⏳ parallel |
| 01-10-T1 | 01-10 | 7 | FOUND-02 | T-01-75, T-01-76, T-01-77, T-01-78, T-01-79 | Every tenant route: A-token + B-object → **404** (asserted not-403); unclassified route fails CI | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ✅ | ✅ green |
| 01-10-T2 | 01-10 | 7 | FOUND-02 | T-01-80, T-01-81 | Tenancy gate + SQL-injection gate are separate mandatory CI steps | gate | `docker compose --profile test run --rm tests pytest -q && docker compose --profile test run --rm tests sh -c "ruff check --select S608 . && mypy ."` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky · ⏳ parallel (owned by a plan running in the same wave)*
*File Exists: ✅ = artefact confirmed present on disk at sign-off (`git ls-files`).*

**How each Status was established (01-10 / Task 2) — evidence, not assumption:**

- **Backend rows (01-01-T2/T3, 01-03…01-07, 01-10)** — re-measured at sign-off: `pytest -q` → **375 passed**; `ruff check .` + `ruff format --check .` + `mypy .` (strict, 83 source files) → clean; `ruff check --select S608 .` → clean. Every referenced test file confirmed present.
- **01-01-T1** — compose/role assertions were verified by 01-01 against a live `db` service; the same role invariant is additionally locked forever by `tests/tenancy/test_meta.py::test_app_role_cannot_bypass_rls`, which **is** in the re-measured 375.
- **Frontend rows (01-02, 01-08)** — green per their own plans' SUMMARY; artefacts (`frontend/src/proxy.ts`, `frontend/src/i18n/routing.ts`, `frontend/scripts/check-messages.mjs`, `frontend/scripts/gen-cyrillic.mjs`) confirmed present. **Not re-run by 01-10:** this plan executes in an isolated worktree with no `frontend/node_modules`; a `next build` there would measure that worktree's install rather than the phase artefact, and `frontend/` belongs to a concurrently-running plan.
- **01-09 rows** — ⏳ **by design, not a coverage gap.** 01-09 runs in the *same* wave 7 as 01-10, in a parallel worktree; its artefacts (`frontend/src/components/users/`, audit UI) do not exist in 01-10's tree. They are verified by 01-09's own `<verify>` block plus the 15-step `<human-check>`. **The phase verifier must confirm these two rows before closing the phase.**

**Sampling continuity check:** all 28 tasks carry an `<automated>` command — the longest run without automated verification is **0**, so the "no 3 consecutive tasks without automated verify" rule holds with margin. The two manual verifications (01-08-T3, 01-09-T2) are **additive** to their automated gates, never a substitute.

---

## Wave 0 Requirements

Wave 0 was fully owned by **01-01 / Task 3** and is green — every RLS claim in this phase rests on it. Each box below was re-confirmed on disk at sign-off.

- [x] Test infrastructure installed: pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 in `services/core-api/pyproject.toml` (dev group), pytest config in root `pyproject.toml` with `asyncio_mode = "auto"`
- [x] `tests/conftest.py` — `PostgresContainer("postgres:18.4-trixie", driver="asyncpg")` fixture, applies `ops/db/init/01-roles.sql` verbatim (single source of truth for role attributes), exposes `app_engine` connecting as **non-superuser `sbozor_app`** (NOT `postgres` — RLS tests are falsely green under a superuser), `pool_size=1, max_overflow=0`
- [x] RLS meta-test: `tests/tenancy/test_meta.py::test_app_role_cannot_bypass_rls` asserts `NOT rolsuper AND NOT rolbypassrls` for `sbozor_app` (and `sbozor_owner`)
- [x] Fixture self-protection: `test_app_engine_connects_as_sbozor_app` fails if the fixture is ever pointed back at the superuser
- [x] `.github/workflows/ci-backend.yml` runs `ruff`, `mypy`, `pytest` on the runner (Docker available → testcontainers works natively) — plus, since 01-10, a separate **SQL injection gate** and **Tenancy gate (FOUND-02)**
- [x] `alembic-utils` autogenerate compatibility with the async Alembic env verified (RESEARCH assumption A9) — checked in **01-04 / Task 1** and re-confirmed by 01-05/01-06/01-07 (`alembic revision --autogenerate` yields an empty diff with 16 `PGFunction` entities registered). The `op.execute()` fallback was never needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Locale switch stays fully translated across every screen | FOUND-04 | No frontend browser-test framework in the locked stack (Playwright deferred to Phase 8 per RESEARCH Open Question 2 / assumption A6) | `tsc --noEmit` + `next build` + `i18n:check` gates, then the 8-step `<human-check>` in **01-08 / Task 3** |
| The five phase success criteria, demonstrated end-to-end | FOUND-01…FOUND-05 | Criterion #3 is explicitly "ko'rsatib isbotlanadi" (D-12); the DB-owner immutability demo needs a real `psql` session | The 15-step `<human-check>` in **01-09 / Task 2** — that plan holds the authoritative step list, covering: roles + isolation, one-click locale, audit who/when/what/old→new, owner `UPDATE 0` + `TRUNCATE` rejection, Tashkent `business_date`, cross-tenant 404 |

Both manual checks are **additive**: each sits behind an automated gate that must already be green, so the human confirms presentation and end-to-end feel — never correctness that a test could have covered. Note that the cross-tenant 404 step of the 15-step check is now *also* covered automatically by `tests/tenancy/test_cross_tenant.py` (01-10), so a regression there fails CI long before anyone opens a browser.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies — **satisfied for all 28 tasks**
- [x] Sampling continuity: no 3 consecutive tasks without automated verify — **satisfied (zero gaps)**
- [x] Wave 0 covers all MISSING references — **satisfied (01-01 / Task 3), re-confirmed on disk at sign-off**
- [x] No watch-mode flags — **satisfied: no `--watch`, no `pytest-watch`, no `next dev` in any gate, including `npm run gate`**
- [x] Feedback latency measured and recorded — **task 8 s / wave 73 s** (see Test Infrastructure + Sampling Rate)
- [x] `wave_0_complete: true` set after 01-01 landed
- [x] Every row in the Per-Task Verification Map is ✅ green — **26 of 28 at sign-off**; the two 01-09 rows are ⏳ because that plan runs in the *same* wave and is verified by its own `<verify>` block. **This is the single item the phase verifier must re-check.**

**Approval:** approved — signed off by **01-10 / Task 2** on 2026-07-29, with the one carry-over noted above (01-09-T1, 01-09-T2).
