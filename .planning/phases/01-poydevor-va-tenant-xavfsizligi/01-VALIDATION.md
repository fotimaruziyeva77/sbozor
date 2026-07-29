---
phase: 1
slug: poydevor-va-tenant-xavfsizligi
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-29
updated: 2026-07-29
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Planner filled the map from `01-01-PLAN.md` … `01-10-PLAN.md`.
> Plan **01-10 / Task 2** finalizes measured runtimes, flips `wave_0_complete: true` and signs off.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 (real `postgres:18.4-trixie`) |
| **Config file** | `pyproject.toml` (repo root, `[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) — created by 01-01 / Task 2 |
| **Quick run command** | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| **Full suite command** | `docker compose --profile test run --rm tests pytest -q` |
| **Tenancy gate command** | `docker compose --profile test run --rm tests pytest tests/tenancy -q` |
| **Frontend gate command** | `npm --prefix frontend run i18n:check && npm --prefix frontend run typecheck && npm --prefix frontend run lint && npm --prefix frontend run build` |
| **Phase gate command** | `npm run gate` (created by 01-10 / Task 2) |
| **Estimated runtime** | quick < 30 s (no container) · full ~90–180 s (testcontainers) — **measured value filled by 01-10 / Task 2** |
| **CI escape hatch** | `TEST_DATABASE_URL` env — if set, `conftest.py` skips container startup and uses that DB |

**Forbidden:** SQLite (RLS does not exist there → the most dangerous code path would be untested). Test engine MUST connect as `sbozor_app`, never as `postgres` superuser — `FORCE ROW LEVEL SECURITY` does not constrain superusers, so a superuser fixture makes every RLS test falsely green.

---

## Sampling Rate

- **After every task commit:** `docker compose --profile test run --rm tests pytest tests/unit -x -q` (+ `ruff check .`)
- **After every plan wave:** full suite + `tests/tenancy` + frontend gate
- **Before `/gsd-verify-work`:** `npm run gate` — everything green, `tests/tenancy` mandatory
- **Max feedback latency:** < 30 s at task level, < 180 s at wave level — **measured value filled by 01-10 / Task 2**

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-T1 | 01-01 | 1 | FOUND-02 | T-01-01, T-01-03, T-01-04 | App DB role is `NOSUPERUSER NOBYPASSRLS`; no secrets in repo; DB port not published | integration (SQL) | `docker compose config --quiet && docker compose up -d db cache && docker compose exec -T db psql -U postgres -d sbozor -c "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='sbozor_app'"` | ❌ W0 | ⬜ pending |
| 01-01-T2 | 01-01 | 1 | FOUND-02 | T-01-07, T-01-SC | Pinned versions, `uv.lock` committed, non-root runtime, no `passlib`/`python-jose` | build + import | `docker compose --profile test build tests && docker compose --profile test run --rm tests python -c "import sbozor_core, fastapi, jwt, pwdlib"` | ❌ W0 | ⬜ pending |
| 01-01-T3 | 01-01 | 1 | FOUND-02 | T-01-02, T-01-05, T-01-06 | Test engine connects as `sbozor_app`; app cannot disable triggers; `CREATE` revoked from PUBLIC | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy/test_meta.py -x -q` | ❌ W0 | ⬜ pending |
| 01-02-T1 | 01-02 | 1 | FOUND-04 | T-01-SC | No `@eloqnt/cli` (unlicensed), no `react-leaflet` (Hippocratic-2.1), TS pinned 5.9.3 | build | `npm --prefix frontend run typecheck && npm --prefix frontend run build` | ❌ W0 | ⬜ pending |
| 01-02-T2 | 01-02 | 1 | FOUND-04 | T-01-08 | `proxy.ts` (not `middleware.ts`) — silent locale-routing loss prevented | build + HTTP | `npm --prefix frontend run build` + `curl -s -o /dev/null -w "%{redirect_url}" http://localhost:3000/` | ❌ W0 | ⬜ pending |
| 01-02-T3 | 01-02 | 1 | FOUND-04 | T-01-09, T-01-11 | ICU placeholders never transliterated; key + ICU-arg parity across 3 locales | unit (node) | `npm --prefix frontend run i18n:gen && npm --prefix frontend run i18n:check` | ❌ W0 | ⬜ pending |
| 01-03-T1 | 01-03 | 2 | FOUND-05 | T-01-19 | Money is `int` only (`float`/`bool` rejected); business day shifts at Tashkent midnight | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_money.py tests/unit/test_timeutil.py tests/unit/test_phone.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-T2 | 01-03 | 2 | FOUND-01 | T-01-12, T-01-13, T-01-14, T-01-15, T-01-18 | `alg=none` / alg-confusion / type-confusion / short-key rejected; Argon2id + dummy verify | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_jwt.py tests/unit/test_password.py -x -q` | ❌ W0 | ⬜ pending |
| 01-03-T3 | 01-03 | 2 | FOUND-05 | T-01-16, T-01-17 | Tenant GUC only inside an open transaction; secrets censored from logs | import + type | `docker compose --profile test run --rm tests sh -c "python -c 'from sbozor_core.tenancy import SET_TENANT_CONTEXT' && mypy packages/sbozor-core"` | ❌ W0 | ⬜ pending |
| 01-04-T1 | 01-04 | 3 | FOUND-02 | T-01-21, T-01-22 | RLS predicate uses `NULLIF(...)` (fail-closed); `enable_tenant_rls` covers ENABLE+FORCE+GRANT | unit (SQL gen) | `docker compose --profile test run --rm tests python -c "from migrations.entities.policies import tenant_policy; print(tenant_policy('x').to_sql_statement_create())"` | ❌ W0 | ⬜ pending |
| 01-04-T2 | 01-04 | 3 | FOUND-01, FOUND-02 | T-01-23, T-01-25, T-01-26 | `users` revoked from app role; login only via `SECURITY DEFINER` with pinned `search_path` | integration | `docker compose --profile test run --rm tests pytest tests/tenancy/test_login_bootstrap.py -x -q` | ❌ W0 | ⬜ pending |
| 01-04-T3 | 01-04 | 3 | FOUND-02 | T-01-20, T-01-24, T-01-27 | Every tenant table has `market_id` + RLS ENABLE **and** FORCE + policy; no `BYPASSRLS` role exists | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ❌ W0 | ⬜ pending |
| 01-05-T1 | 01-05 | 4 | FOUND-03 | T-01-30, T-01-31, T-01-32, T-01-35 | `audit_log` 4-layer immutability; trigger fn is NOT `SECURITY DEFINER` | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_immutable.py -x -q` | ❌ W0 | ⬜ pending |
| 01-05-T2 | 01-05 | 4 | FOUND-03 | T-01-29, T-01-33, T-01-34 | Raw SQL bypassing the ORM is still audited; no-op update writes nothing; cross-tenant audit read is empty | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_write.py tests/integration/test_audit_immutable.py tests/tenancy/test_meta.py -x -q` | ❌ W0 | ⬜ pending |
| 01-05-T3 | 01-05 | 4 | FOUND-05 | T-01-36, T-01-37, T-01-38 | `business_date` STORED generated column; `CHECK(amount_soum > 0)`; `ON CONFLICT DO NOTHING` idempotent | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_business_date.py tests/integration/test_money_constraints.py tests/integration/test_idempotency.py -x -q` | ❌ W0 | ⬜ pending |
| 01-06-T1 | 01-06 | 5 | FOUND-01 | T-01-45, T-01-48 | RBAC matrix hard-coded (director cannot manage — D-07); no f-string SQL | unit | `docker compose --profile test run --rm tests pytest tests/unit/test_rbac_matrix.py -x -q` | ❌ W0 | ⬜ pending |
| 01-06-T2 | 01-06 | 5 | FOUND-01, FOUND-03 | T-01-42, T-01-43, T-01-46, T-01-47, T-01-49 | httpOnly + SameSite=Lax + Path-scoped refresh cookie; no self-registration route; RLS error → 404 | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_auth_login.py -x -q` | ❌ W0 | ⬜ pending |
| 01-06-T3 | 01-06 | 5 | FOUND-01 | T-01-39, T-01-40, T-01-41, T-01-44 | No user enumeration (identical body); rate limit; refresh reuse revokes family; block is immediate | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_auth_login.py tests/integration/test_auth_refresh.py tests/integration/test_user_block.py -x -q` | ❌ W0 | ⬜ pending |
| 01-07-T1 | 01-07 | 6 | FOUND-01 | T-01-50, T-01-51, T-01-52, T-01-56, T-01-59 | Cross-tenant user op → 404 (not 403); temp password never logged/audited; cache invalidated on block | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_users_api.py -x -q` | ❌ W0 | ⬜ pending |
| 01-07-T2 | 01-07 | 6 | FOUND-04 | T-01-51 | Locale persisted in DB profile; `/markets` never uses BYPASSRLS | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_me_locale.py -x -q` | ❌ W0 | ⬜ pending |
| 01-07-T3 | 01-07 | 6 | FOUND-03 | T-01-53, T-01-54, T-01-55, T-01-57 | Audit visible only to D-11 roles; viewing audit writes a `read` record; keyset pagination, `limit ≤ 200` | integration | `docker compose --profile test run --rm tests pytest tests/integration/test_audit_read.py tests/integration/test_users_api.py -x -q` | ❌ W0 | ⬜ pending |
| 01-08-T1 | 01-08 | 6 | FOUND-01 | T-01-60, T-01-67 | Access token in memory only (no `localStorage`); single-flight refresh, one retry | build + grep | `npm --prefix frontend run typecheck && npm --prefix frontend run build && ! grep -rq "localStorage\|sessionStorage" frontend/src/` | ❌ W0 | ⬜ pending |
| 01-08-T2 | 01-08 | 6 | FOUND-01, FOUND-04 | T-01-63, T-01-64 | One generic `invalid_credentials` message; no register / forgot-password affordance | build + i18n | `npm --prefix frontend run i18n:check && npm --prefix frontend run build` | ❌ W0 | ⬜ pending |
| 01-08-T3 | 01-08 | 6 | FOUND-04 | T-01-61, T-01-65, T-01-66 | One-click locale switch (URL + `PATCH /me`); protected layer refreshes before redirecting | build + **manual** | `npm --prefix frontend run i18n:check && npm --prefix frontend run lint && npm --prefix frontend run build` + `<human-check>` (8 steps, see 01-08 Task 3) | ❌ W0 | ⬜ pending |
| 01-09-T1 | 01-09 | 7 | FOUND-01 | T-01-68 | Temp password shown once, never logged or stored; role picker is multi-select (D-05) | build + grep | `npm --prefix frontend run i18n:check && npm --prefix frontend run build && ! grep -rq "console.log" frontend/src/components/users/` | ❌ W0 | ⬜ pending |
| 01-09-T2 | 01-09 | 7 | FOUND-03, FOUND-04 | T-01-69, T-01-70, T-01-72, T-01-73, T-01-74 | Audit list is read-only, masked values preserved, no `dangerouslySetInnerHTML` | build + full suite + **manual** | `npm --prefix frontend run i18n:check && npm --prefix frontend run build && docker compose --profile test run --rm tests pytest -q` + `<human-check>` (15 steps = the 5 phase criteria) | ❌ W0 | ⬜ pending |
| 01-10-T1 | 01-10 | 7 | FOUND-02 | T-01-75, T-01-76, T-01-77, T-01-78, T-01-79 | Every tenant route: A-token + B-object → **404** (asserted not-403); unclassified route fails CI | tenancy | `docker compose --profile test run --rm tests pytest tests/tenancy -x -q` | ❌ W0 | ⬜ pending |
| 01-10-T2 | 01-10 | 7 | FOUND-02 | T-01-80, T-01-81 | Tenancy gate + SQL-injection gate are separate mandatory CI steps | gate | `docker compose --profile test run --rm tests pytest -q && docker compose --profile test run --rm tests sh -c "ruff check --select S608 . && mypy ."` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*
*File Exists: ❌ W0 = greenfield, file is created by the task itself (Wave 0 bootstrap in 01-01).*

**Sampling continuity check:** no run of 3 consecutive tasks lacks an `<automated>` command — every one of the 28 tasks above has one. The two manual verifications (01-08-T3, 01-09-T2) are **additive** to their automated gates, never a substitute.

---

## Wave 0 Requirements

Wave 0 is fully owned by **01-01 / Task 3** and must be green before any RLS claim is treated as verified.

- [ ] Test infrastructure installed: pytest 9.1.1 + pytest-asyncio 1.4.0 + testcontainers 4.15.0 in `services/core-api/pyproject.toml` (dev group), pytest config in root `pyproject.toml` with `asyncio_mode = "auto"`
- [ ] `tests/conftest.py` — `PostgresContainer("postgres:18.4-trixie", driver="asyncpg")` fixture, applies `ops/db/init/01-roles.sql` verbatim (single source of truth for role attributes), exposes `app_engine` connecting as **non-superuser `sbozor_app`** (NOT `postgres` — RLS tests are falsely green under a superuser), `pool_size=1, max_overflow=0`
- [ ] RLS meta-test: `tests/tenancy/test_meta.py::test_app_role_cannot_bypass_rls` asserts `NOT rolsuper AND NOT rolbypassrls` for `sbozor_app` (and `sbozor_owner`)
- [ ] Fixture self-protection: `test_app_engine_connects_as_sbozor_app` fails if the fixture is ever pointed back at the superuser
- [ ] `.github/workflows/ci-backend.yml` runs `ruff`, `mypy`, `pytest` on the runner (Docker available → testcontainers works natively)
- [ ] `alembic-utils` autogenerate compatibility with the async Alembic env verified (RESEARCH assumption A9) — checked in **01-04 / Task 1**; fallback is plain `op.execute()` at low cost

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Locale switch stays fully translated across every screen | FOUND-04 | No frontend browser-test framework in the locked stack (Playwright deferred to Phase 8 per RESEARCH Open Question 2 / assumption A6) | `tsc --noEmit` + `next build` + `i18n:check` gates, then the 8-step `<human-check>` in **01-08 / Task 3** |
| The five phase success criteria, demonstrated end-to-end | FOUND-01…FOUND-05 | Criterion #3 is explicitly "ko'rsatib isbotlanadi" (D-12); DB-owner immutability demo needs a real `psql` session | The 15-step `<human-check>` in **01-09 / Task 2** (roles + isolation, one-click locale, audit who/when/what/old→new, owner `UPDATE 0` + `TRUNCATE` rejection, Tashkent `business_date`, cross-tenant 404) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies — **planner: satisfied for all 28 tasks**
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify — **planner: satisfied**
- [ ] Wave 0 covers all MISSING references — **planner: satisfied (01-01 / Task 3)**
- [ ] No watch-mode flags — **planner: satisfied (no `--watch`, no `pytest-watch`, no `next dev` in any gate)**
- [ ] Feedback latency measured and recorded — *filled by 01-10 / Task 2*
- [ ] `wave_0_complete: true` set after 01-01 lands
- [ ] Every row in the Per-Task Verification Map is ✅ green

**Approval:** pending — final sign-off performed by **01-10 / Task 2**
