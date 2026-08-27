---
phase: 01-poydevor-va-tenant-xavfsizligi
reviewed: 2026-07-29T10:17:18Z
depth: standard
files_reviewed: 130
files_reviewed_list:
  - .github/workflows/ci-backend.yml
  - .github/workflows/ci-frontend.yml
  - frontend/messages/ru.json
  - frontend/messages/uz-Cyrl.json
  - frontend/messages/uz-Cyrl.overrides.json
  - frontend/messages/uz-Latn.json
  - frontend/next.config.ts
  - frontend/package.json
  - frontend/scripts/audit-actions.test.mjs
  - frontend/scripts/check-messages.mjs
  - frontend/scripts/gen-cyrillic.mjs
  - frontend/scripts/gen-cyrillic.test.mjs
  - frontend/scripts/role-gate.test.mjs
  - frontend/src/app/[locale]/(app)/audit/page.tsx
  - frontend/src/app/[locale]/(app)/dashboard/page.tsx
  - frontend/src/app/[locale]/(app)/layout.tsx
  - frontend/src/app/[locale]/(app)/users/page.tsx
  - frontend/src/app/[locale]/(auth)/change-password/page.tsx
  - frontend/src/app/[locale]/(auth)/layout.tsx
  - frontend/src/app/[locale]/(auth)/login/page.tsx
  - frontend/src/app/[locale]/(auth)/select-market/page.tsx
  - frontend/src/app/[locale]/layout.tsx
  - frontend/src/app/[locale]/page.tsx
  - frontend/src/app/globals.css
  - frontend/src/components/audit/audit-diff.tsx
  - frontend/src/components/audit/audit-filters.tsx
  - frontend/src/components/audit/audit-list.tsx
  - frontend/src/components/auth/change-password-form.tsx
  - frontend/src/components/auth/login-form.tsx
  - frontend/src/components/auth/market-picker.tsx
  - frontend/src/components/shell/app-shell.tsx
  - frontend/src/components/shell/locale-switcher.tsx
  - frontend/src/components/shell/user-menu.tsx
  - frontend/src/components/users/create-user-dialog.tsx
  - frontend/src/components/users/temp-password-dialog.tsx
  - frontend/src/components/users/user-list.tsx
  - frontend/src/global.ts
  - frontend/src/i18n/navigation.ts
  - frontend/src/i18n/request.ts
  - frontend/src/i18n/routing.ts
  - frontend/src/lib/api-client.ts
  - frontend/src/lib/api-types.ts
  - frontend/src/lib/auth-store.ts
  - frontend/src/lib/cn.ts
  - frontend/src/lib/queries.ts
  - frontend/src/lib/query-provider.tsx
  - frontend/src/lib/rbac.ts
  - frontend/src/proxy.ts
  - frontend/tsconfig.json
  - migrations/__init__.py
  - migrations/entities/__init__.py
  - migrations/entities/functions.py
  - migrations/entities/policies.py
  - migrations/entities/triggers.py
  - migrations/env.py
  - migrations/helpers.py
  - migrations/script.py.mako
  - migrations/versions/0001_identity.py
  - migrations/versions/0002_audit.py
  - migrations/versions/0003_auth_support.py
  - migrations/versions/0004_user_admin.py
  - ops/db/init/01-roles.sql
  - ops/db/init/02-passwords.sh
  - ops/nginx/nginx.conf
  - packages/sbozor-core/pyproject.toml
  - packages/sbozor-core/sbozor_core/__init__.py
  - packages/sbozor-core/sbozor_core/db.py
  - packages/sbozor-core/sbozor_core/enums.py
  - packages/sbozor-core/sbozor_core/logging.py
  - packages/sbozor-core/sbozor_core/models/__init__.py
  - packages/sbozor-core/sbozor_core/models/base.py
  - packages/sbozor-core/sbozor_core/models/identity.py
  - packages/sbozor-core/sbozor_core/models/ops.py
  - packages/sbozor-core/sbozor_core/money.py
  - packages/sbozor-core/sbozor_core/phone.py
  - packages/sbozor-core/sbozor_core/schema_contract.py
  - packages/sbozor-core/sbozor_core/security.py
  - packages/sbozor-core/sbozor_core/tenancy.py
  - packages/sbozor-core/sbozor_core/timeutil.py
  - services/core-api/app/api/v1/audit.py
  - services/core-api/app/api/v1/auth.py
  - services/core-api/app/api/v1/markets.py
  - services/core-api/app/api/v1/me.py
  - services/core-api/app/api/v1/users.py
  - services/core-api/app/deps.py
  - services/core-api/app/main.py
  - services/core-api/app/repositories/audit_repo.py
  - services/core-api/app/repositories/auth_repo.py
  - services/core-api/app/repositories/user_repo.py
  - services/core-api/app/schemas.py
  - services/core-api/app/security/audit.py
  - services/core-api/app/security/ratelimit.py
  - services/core-api/app/security/rbac.py
  - services/core-api/app/security/tokens.py
  - services/core-api/app/settings.py
  - services/core-api/pyproject.toml
  - tests/conftest.py
  - tests/fixtures/admin_api.py
  - tests/fixtures/auth_api.py
  - tests/fixtures/auth_users.py
  - tests/fixtures/financial.py
  - tests/fixtures/two_markets.py
  - tests/integration/conftest.py
  - tests/integration/test_audit_immutable.py
  - tests/integration/test_audit_read.py
  - tests/integration/test_audit_write.py
  - tests/integration/test_auth_login.py
  - tests/integration/test_auth_refresh.py
  - tests/integration/test_business_date.py
  - tests/integration/test_idempotency.py
  - tests/integration/test_me_locale.py
  - tests/integration/test_money_constraints.py
  - tests/integration/test_user_block.py
  - tests/integration/test_users_api.py
  - tests/tenancy/test_composite_fk.py
  - tests/tenancy/test_cross_tenant.py
  - tests/tenancy/test_login_bootstrap.py
  - tests/tenancy/test_meta.py
  - tests/tenancy/test_rls_predicate.py
  - tests/tenancy/test_route_coverage.py
  - tests/unit/test_enums.py
  - tests/unit/test_jwt.py
  - tests/unit/test_logging.py
  - tests/unit/test_money.py
  - tests/unit/test_password.py
  - tests/unit/test_phone.py
  - tests/unit/test_rbac_matrix.py
  - tests/unit/test_tenancy.py
  - tests/unit/test_timeutil.py
  - compose.yaml
  - services/core-api/Dockerfile
findings:
  critical: 4
  warning: 10
  info: 5
  total: 19
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-29T10:17:18Z
**Depth:** standard
**Files Reviewed:** 130
**Status:** issues_found

## Summary

The database-side tenant isolation is the strongest part of this phase and I could not break it by reading. RLS `ENABLE`+`FORCE`+policy is applied consistently, the `NULLIF` fail-closed predicate is correct and proven by a `pool_size=1` test, `sbozor_app` is `NOSUPERUSER NOBYPASSRLS` with `REVOKE ALL` on `users`, every `SECURITY DEFINER` function pins `search_path`, and the four-layer `audit_log` immutability chain is real (grants, policy absence, row trigger, truncate trigger) with tests that measure *state* rather than exceptions. The tenancy meta-tests and the auto-discovered cross-tenant route matrix are genuinely load-bearing — they read `pg_catalog` and `app.routes` instead of hand-maintained lists, and they contain explicit anti-false-green guards. JWT handling matches the documented threat model (`alg` pinned literally, `typ` enforced, minimum key length raised to an error). None of the forbidden stack items (passlib, python-jose, float money, naive datetimes, `middleware.ts`) appear.

The defects are concentrated where the DB guarantees stop and the application/deploy layer takes over.

Four blockers:

1. **D-02 (forced temporary-password change) has no server-side enforcement at all.** The flag is read from the DB, returned in responses, and then never checked on any request path. Two source files explicitly claim a server-side layer exists; it does not. A holder of an admin-issued temporary password gets a full, market-scoped, cookie-backed session and can drive every endpoint their roles allow.
2. **The market-selection screen is non-functional** — a TanStack Query v5 `isPending` semantics mistake disables every market button on the normal path, so D-06 cannot complete in the browser.
3. **`platform_admin` is offered as an assignable market-level role in the UI and accepted by the API**, producing an account with `market_view_all` but without `users.is_platform_admin` — it leaks the full market list across tenants while being functionally broken.
4. **Login rate limiting keys on the reverse-proxy address**, because uvicorn is started without `--forwarded-allow-ips`. 51 unauthenticated requests lock out every user of the platform for 15 minutes, and `audit_log.ip` records the proxy on every row, which removes the forensic value the audit trail exists for.

Warnings cluster around claimed-but-absent controls (the "grep gate" referenced in six files does not exist anywhere in the repo), non-recursive log censoring, and a cross-tenant existence oracle in `POST /users`.

## Critical Issues

### CR-01: Forced password change (D-02) is enforced only in the browser

**Severity:** BLOCKER
**File:** `services/core-api/app/deps.py:198-233`, `services/core-api/app/deps.py:242-292`, `services/core-api/app/api/v1/auth.py:295-346`
**Issue:**
`must_change_password` is fetched everywhere and enforced nowhere. `auth_repo.UserState` carries the field (`app/repositories/auth_repo.py:93-99`), `_is_user_active()` reads the row at `deps.py:219` and then only inspects `state.is_active`. `get_current_principal()` (`deps.py:242-292`) never looks at the flag, `Principal` (`deps.py:110-128`) does not carry it, and no endpoint or dependency in `app/api/v1/` gates on it — a repo-wide search for `must_change` in `services/core-api/app/` returns only reads and writes, never a comparison.

Meanwhile `POST /auth/login` issues a **complete** session for such a user: `auto_select` (`auth.py:311`) picks the single membership, `issue_access()` mints a token with `mid` + `roles`, and `_issue_session_cookie()` (`auth.py:322-330`) sets the 30-day refresh cookie. The access token is in the login response body, so the client-side redirect in `frontend/src/app/[locale]/(app)/layout.tsx:53-56` is the only barrier and is bypassed by not using the browser.

Two source comments assert a control that does not exist:
- `frontend/src/components/auth/change-password-form.tsx:20-22` — *"(2) server yozuv endpointlarini parol almashtirilmaguncha rad etadi"*
- `frontend/src/app/[locale]/(app)/layout.tsx:21` — *"Server tomonda ham yozuv endpointlari yopiq."*

`frontend/src/lib/api-types.ts:297` even reserves the error code `password_change_required`, which the backend never emits — the gate was designed and then dropped without the comments being corrected.

Impact: an admin-issued temporary password (12 chars from `secrets.token_urlsafe(9)`, transmitted out-of-band, known to whoever issued it) is a permanent, full-privilege credential. A market admin created this way can create users, block users and read the audit log without ever rotating it, which is exactly the failure D-02 exists to prevent (ASVS V6.2 / V7).

**Fix:**
```python
# services/core-api/app/deps.py — carry the flag into Principal and gate on it.

@dataclass(frozen=True)
class Principal:
    user_id: UUID
    market_id: UUID | None
    roles: frozenset[str]
    is_platform_admin: bool
    request_id: str
    actor_label: str
    must_change_password: bool = False   # <- new


async def _user_state(request: Request, cache: Redis, user_id: UUID) -> tuple[bool, bool]:
    """(is_active, must_change_password) — cache both, they come from one row."""
    ...


async def get_current_principal(...) -> Principal:
    ...
    is_active, must_change = await _user_state(request, cache, claims.user_id)
    if not is_active:
        raise HTTPException(401, detail="account_blocked", headers={"WWW-Authenticate": "Bearer"})
    return Principal(..., must_change_password=must_change)


async def require_password_current(principal: PrincipalDep) -> Principal:
    """Blocks every route except `/auth/change-password` and `/auth/logout` (D-02)."""
    if principal.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="password_change_required",   # code already reserved by the frontend
        )
    return principal


# Make it the base of the two composite dependencies so nothing can be forgotten:
#   get_tenant_session -> depends on require_password_current (not PrincipalDep)
#   require_permission(...) -> depends on require_password_current
```
Add integration tests: `must_change` user gets 403 `password_change_required` on `GET /api/v1/users`, `GET /api/v1/audit`, `POST /api/v1/users`, and 200 on `POST /auth/change-password`. Then delete the now-true comments' "server side" claim only if you decide *not* to implement it.

---

### CR-02: Market-selection buttons are permanently disabled — D-06 flow cannot complete

**Severity:** BLOCKER
**File:** `frontend/src/components/auth/market-picker.tsx:51-55`, `frontend/src/components/auth/market-picker.tsx:93`, `frontend/src/components/auth/market-picker.tsx:126-128`
**Issue:**
```ts
const marketsQuery = useQuery({
  queryKey: ["markets"],
  queryFn: () => apiFetch(MARKETS_PATH, { schema: marketListSchema }),
  enabled: accessToken !== null && markets.length === 0,   // disabled on the normal path
});
...
const isBusy = selectMarket.isPending || marketsQuery.isPending;
...
<button disabled={isBusy} onClick={() => selectMarket.mutate(market.id)}>
```
In `@tanstack/react-query` **5.101.4** (confirmed in `node_modules`), a *disabled* query stays in `status: 'pending'`, so `marketsQuery.isPending === true` whenever `enabled` is false. `isPending` means "no data yet", not "a request is in flight" — that is `isFetching` / `isLoading`.

On the primary path the login response fills `markets`, so `markets.length > 0` → the query is disabled → `marketsQuery.isPending === true` → the early return at line 95 (`isPending && markets.length === 0`) is skipped → the list renders with `isBusy === true` → **every market button is `disabled`**. A platform admin or multi-market user can log in and then cannot proceed past the market picker.

**Fix:**
```ts
const marketsQueryEnabled = accessToken !== null && markets.length === 0;

const marketsQuery = useQuery({
  queryKey: ["markets"],
  queryFn: () => apiFetch(MARKETS_PATH, { schema: marketListSchema }),
  enabled: marketsQueryEnabled,
});

// `isLoading` === isPending && isFetching -> false for a disabled query.
const isBusy = selectMarket.isPending || marketsQuery.isLoading;

if (marketsQuery.isLoading) {
  return <p role="status">{t("common.loading")}</p>;
}
```
Add a component test (or a Playwright smoke) that renders `MarketPicker` with a non-empty `markets` list and asserts the buttons are enabled — this class of bug is invisible to typecheck, lint and the existing node:test suite.

---

### CR-03: `platform_admin` assignable as a market role → cross-tenant market disclosure + broken account

**Severity:** BLOCKER
**File:** `services/core-api/app/api/v1/users.py:120-136`, `services/core-api/app/repositories/user_repo.py:169-194`, `frontend/src/lib/api-types.ts:140-142`, `frontend/src/components/users/create-user-dialog.tsx:75`
**Issue:**
"Platform admin" has two independent representations and only one of them is writable through the API:

- `users.is_platform_admin` — the real flag. `UserRepository.create_user()` hard-codes `"is_platform_admin": False` (`user_repo.py:191`) and there is no endpoint that ever sets it.
- `user_market_roles.roles` may contain `'platform_admin'` — `Role.PLATFORM_ADMIN` is a legal value of `ROLES_SUBSET_CHECK`, `CreateUserRequest.roles` accepts it, and `_assert_roles_assignable()` returns early for a platform-admin caller without restricting the requested set (`users.py:127-128`).

The frontend actively offers it: `assignableRoles(true)` returns `ROLES` (which includes `"platform_admin"`, `frontend/src/lib/rbac.ts:19-25`) and `CreateUserDialog` renders a checkbox per entry (`create-user-dialog.tsx:194-206`). So the documented D-04 first-stage UI produces this state.

The resulting account behaves as follows:
1. `_session_roles()` (`auth.py:179-194`) takes roles from the membership → the access token carries `roles: ["platform_admin"]`, `pa: false`.
2. `permissions_for()` (`app/security/rbac.py:121-139`) maps `Role.PLATFORM_ADMIN` → `{MARKET_VIEW_ALL, MARKET_MANAGE, USER_MANAGE, USER_VIEW, AUDIT_VIEW}`.
3. `GET /api/v1/markets` (`app/api/v1/markets.py:76-78`) branches on `Permission.MARKET_VIEW_ALL in principal.permissions` → serves `auth_list_markets_full()`, i.e. **`id`, `name`, `timezone`, `is_active` for every market in the platform**, to a user scoped to one market.
4. Yet `POST /auth/select-market` still rejects other markets (`_platform_admin_market()` checks `principal.is_platform_admin`, which is `False` → 403 `market_forbidden`), and `_assert_roles_assignable()` also treats them as non-platform-admin. The account is both over-privileged (cross-tenant listing) and broken (cannot do what its name says).

This route is not covered by `tests/tenancy/test_cross_tenant.py` because `/api/v1/markets` is in `EXEMPT_ROUTES` with the reason *"global — platforma admini uchun BOZORLAR RO'YXATI"* — an exemption that is only true if `MARKET_VIEW_ALL` really implies platform admin.

**Fix:**
```python
# services/core-api/app/api/v1/users.py — never let a market role mint a platform admin.
_MARKET_LEVEL_ROLES = frozenset(Role) - {Role.PLATFORM_ADMIN}

def _assert_roles_assignable(principal: Principal, roles: Sequence[Role]) -> None:
    requested = set(roles)
    if Role.PLATFORM_ADMIN in requested:
        # Platform admin is `users.is_platform_admin`, not a membership row.
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_ROLE_NOT_ALLOWED)
    if principal.is_platform_admin:
        return
    if not requested <= MARKET_ADMIN_ASSIGNABLE_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=_ROLE_NOT_ALLOWED)
```
```ts
// frontend/src/lib/api-types.ts — mirror the server gate.
const PLATFORM_ADMIN_ASSIGNABLE_ROLES = ["director", "market_admin", "cashier", "inspector"] as const;

export function assignableRoles(isPlatformAdmin: boolean): readonly Role[] {
  return isPlatformAdmin ? PLATFORM_ADMIN_ASSIGNABLE_ROLES : MARKET_ADMIN_ASSIGNABLE_ROLES;
}
```
And decouple the market listing from the role matrix in `app/api/v1/markets.py` — branch on `principal.is_platform_admin` (the authoritative flag) rather than `MARKET_VIEW_ALL`, or keep the permission check *and* add `and principal.is_platform_admin`. Extend `frontend/scripts/role-gate.test.mjs` to assert `platform_admin` is absent from both assignable lists.

---

### CR-04: Rate limiting and audit IP resolve to the reverse proxy — unauthenticated platform-wide login lockout

**Severity:** BLOCKER
**File:** `compose.yaml:78-79`, `ops/nginx/nginx.conf:17-25`, `services/core-api/app/api/v1/auth.py:116-137`, `services/core-api/app/security/ratelimit.py:54`, `services/core-api/app/security/ratelimit.py:83-97`
**Issue:**
`_client_ip()` deliberately does not read `X-Forwarded-For` and delegates the trust decision to the deploy layer:

> *"Nginx `proxy_set_header` bilan haqiqiy IP'ni uzatadi va uvicorn `--proxy-headers` bilan uni `request.client` ga qo'yadi — ya'ni ishonch qarori DEPLOY qatlamida, kodda emas."* (`auth.py:120-123`)

The deploy layer does not hold up its end. `compose.yaml:78-79` starts:
```yaml
command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```
uvicorn's `--proxy-headers` is on by default but only honours forwarded headers from `--forwarded-allow-ips`, which defaults to `127.0.0.1`. nginx runs in a separate container on the compose bridge network with a different address, so its `X-Forwarded-For` is **discarded** and `request.client.host` is always nginx's container IP.

Consequences:

1. **Auth DoS.** Every login request on the platform shares one counter `rl:login:ip:<nginx-ip>` with `IP_LIMIT = 50` per 15-minute window (`ratelimit.py:54`). `check_login_rate()` raises `TooManyAttempts("ip")` *before* any password verification (`auth.py:270-276` → 429), so once the counter passes 50 **no successful login can occur to reset it** — `reset_login_rate()` is only reached after a valid credential check. An unauthenticated attacker locks out every cashier, admin and director for the remainder of the window with ~51 HTTP requests. The per-phone counter (10) makes this worse, not better: 6 distinct phones × 10 attempts is enough.
2. **Audit evidence destroyed.** `audit_log.ip` is written from the same value on `login`, `login_failed`, `market_selected`, `logout`, `password_changed` and `refresh_reuse_detected`. Every row records the proxy. For a product whose stated purpose is producing defensible evidence in vendor disputes, "who, from where" is permanently unanswerable.

This is not caught by tests because `httpx.ASGITransport` bypasses the proxy entirely — `test_login_rate_limit` (`tests/integration/test_auth_login.py:198-206`) exercises the phone counter only.

**Fix:**
```yaml
# compose.yaml — core-api is only reachable through nginx on the compose network.
command:
  - uvicorn
  - app.main:app
  - --host
  - 0.0.0.0
  - --port
  - "8000"
  - --workers
  - "1"
  - --proxy-headers
  - --forwarded-allow-ips
  - ${FORWARDED_ALLOW_IPS:-*}   # `*` is safe only because the port is not published
```
Publish nothing for `core-api` (already the case) so `*` cannot be reached directly; if the port is ever published, pin to the nginx service address instead. Also:
- Add `proxy_set_header X-Forwarded-Host $host;` is not needed, but do keep `X-Real-IP`/`X-Forwarded-For` as they are.
- Add a regression test that sends two logins with different `X-Forwarded-For` values through an ASGI scope carrying distinct `client` tuples and asserts two independent `rl:login:ip:*` keys, so the invariant stops being deploy-only folklore.
- Consider lowering the blast radius regardless: on IP-limit breach, still run `dummy_verify()` and return 429 *after* the phone counter, and exempt already-authenticated refresh flows.

## Warnings

### WR-01: `censor_secrets` is not recursive — nested secrets reach stdout and Sentry

**Severity:** WARNING
**File:** `packages/sbozor-core/sbozor_core/logging.py:67-82`
**Issue:** The processor iterates `event_dict` keys only at the top level. `log.info("x", payload={"password": "..."} )` or `log.warning("y", body={"credentials": {"token": "..."}})` passes straight through to `JSONRenderer` and then to stdout and Sentry. The sibling masker for audit JSONB (`app/repositories/audit_repo.py:100-115`) *is* recursive and explicitly documents why ("Ichma-ich obyekt ham qamraladi"), so the two layers disagree about the same threat (T-01-16). `tests/unit/test_logging.py` exists but the module docstring promises "sir sizishining oldini olish", which nesting defeats.
**Fix:**
```python
def _censor(value: object) -> object:
    if isinstance(value, dict):
        return {
            k: CENSORED if isinstance(k, str) and k.lower() in SENSITIVE_KEYS else _censor(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_censor(item) for item in value]
    return value


def censor_secrets(logger, method_name, event_dict):
    for key in list(event_dict):
        if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
            event_dict[key] = CENSORED
        else:
            event_dict[key] = _censor(event_dict[key])
    return event_dict
```
Add a unit test with a two-level nested dict and a list-of-dicts.

---

### WR-02: `409 phone_taken` is a cross-tenant user-existence oracle

**Severity:** WARNING
**File:** `services/core-api/app/api/v1/users.py:203-204`, `migrations/entities/functions.py:527-561`
**Issue:** `auth_create_user` uses `ON CONFLICT (phone_e164) DO NOTHING` against the **global** `users` table, so `NULL` (→ `409 phone_taken`) is returned whenever the phone exists *anywhere on the platform*, including in a different market. A market admin can therefore probe arbitrary phone numbers and learn whether they belong to a registered SBOZOR user in another tenant.

This directly contradicts the enumeration discipline enforced everywhere else in the phase: `/auth/login` returns byte-identical bodies for unknown-phone / wrong-password / blocked (`test_login_no_user_enumeration`), and `/users/{id}` returns 404 for cross-tenant IDs specifically so that "403 would confirm the object exists" (`users.py:29-33`). Here the same information is handed over by design.
**Fix:** Decide explicitly and document it. Either (a) accept it and record it in `EXEMPT_ROUTES`-style prose plus a note in the threat model, or (b) close it — have `auth_create_user` return a discriminated result (`created uuid`, `conflict_scope text`) so the endpoint can answer `409 phone_taken` only when the existing user is a member of the caller's market, and otherwise attach the existing global user to the current market as a new `user_market_roles` row (which is the behaviour a multi-market platform needs anyway, and which today is impossible).

---

### WR-03: Deactivating a market does not lock out its members

**Severity:** WARNING
**File:** `services/core-api/app/api/v1/auth.py:311`, `services/core-api/app/api/v1/auth.py:447-455`, `services/core-api/app/api/v1/auth.py:517-518`
**Issue:** `markets.is_active` is checked inconsistently:
- `_visible_markets()` filters on `market.is_active` — but only for platform admins (`auth.py:384-389`).
- `_platform_admin_market()` requires `market.is_active` (`auth.py:518`).
- `login`'s `auto_select` (`auth.py:311`) and `select_market`'s membership branch (`auth.py:448-450`) **never** consult it.

So an ordinary member of a deactivated market logs in, gets a market-scoped token and refresh cookie, and operates normally; only platform admins are blocked from entering it. If `is_active=false` is meant to represent "contract ended / market suspended" (the only reading that makes the platform-admin check meaningful), this is a live authorization gap.
**Fix:** Resolve the membership through a single helper that enforces the invariant, and add tests for both paths:
```python
async def _selectable_market(session, memberships, market_id) -> Membership | None:
    active = {m.market_id for m in await auth_repo.list_markets(session) if m.is_active}
    return next((m for m in memberships if m.market_id == market_id and m.market_id in active), None)
```
If `is_active` is *not* meant to gate access, remove the check from `_platform_admin_market()` and say so in the model docstring — one meaning, one place.

---

### WR-04: `GET /api/v1/markets` cannot be called during market selection, so the picker's fallback is dead

**Severity:** WARNING
**File:** `services/core-api/app/api/v1/markets.py:58-62`, `frontend/src/components/auth/market-picker.tsx:51-62`
**Issue:** `list_markets` depends on `TenantSessionDep`, which raises `409 market_not_selected` when `principal.market_id is None` (`deps.py:308-312`). `MarketPicker` calls that endpoint precisely when no market has been selected (`enabled: accessToken !== null && markets.length === 0`). The request therefore always fails; `marketsQuery.data` stays `undefined`, `options` is `[]`, and the user is shown `auth.noMarkets` ("no markets") plus a logout button instead of the market list. The fallback documented as *"`GET /markets` faqat ZAXIRA"* can never fire successfully.

The endpoint's own docstring acknowledges the 409 as intentional, which means the frontend and backend disagree about what this endpoint is for.
**Fix:** Either drop the fallback from `MarketPicker` (login response is the only source, and refresh-restored sessions always have a market), or split the endpoint: keep `GET /api/v1/markets` tenant-scoped for the admin panel and expose the selection list where it already lives — the `markets` array of the `/auth/login` response — via a small `GET /api/v1/auth/markets` on `AuthSessionDep`. Do not weaken `TenantSessionDep`.

---

### WR-05: The "grep gate" security control cited by six source files does not exist

**Severity:** WARNING
**File:** `frontend/src/lib/auth-store.ts:23-25`, `frontend/src/components/auth/login-form.tsx:22-23`, `frontend/src/components/users/temp-password-dialog.tsx:21-27`, `frontend/src/components/audit/audit-diff.tsx:21-24`, `frontend/src/components/shell/locale-switcher.tsx:30-32`, `tests/tenancy/test_route_coverage.py:27-29`
**Issue:** Multiple files state that a forbidden pattern is *"grep darvozasi bilan qulflangan"* and then deliberately avoid writing the forbidden identifier — browser storage APIs, the HTML-injecting React prop, `next/navigation` imports, `pytest.mark.xfail`/`skip` markers, self-registration and password-reset link text. No such gate exists: there is no grep step in `.github/workflows/ci-frontend.yml`, no script in `frontend/scripts/` (only `audit-actions.test.mjs`, `check-messages.mjs`, `gen-cyrillic.mjs`, `gen-cyrillic.test.mjs`, `role-gate.test.mjs`), and no entry in `frontend/package.json` or the root `package.json`. A repo-wide search for those patterns outside `.next/` build output returns only these comments.

Net effect is worse than having no rule: the ban is enforced by nothing, *and* the identifiers were removed from the comments so a human cannot grep for them either.
**Fix:** Implement the gate (a `frontend/scripts/forbidden-patterns.test.mjs` under `node --test` is the cheapest option, so it runs in both `npm test` and CI):
```js
const FORBIDDEN = [
  { pattern: /\blocalStorage\b|\bsessionStorage\b/u, why: "T-01-60 — token faqat xotirada" },
  { pattern: /dangerouslySetInnerHTML/u,             why: "T-01-74 — XSS yuzasi" },
  { pattern: /from "next\/navigation"/u,             why: "locale prefiksini bilmaydi" },
];
// walk frontend/src/**/*.{ts,tsx}, assert no match, print `why` on failure
```
Add the Python equivalent for `xfail`/`skip` in `tests/tenancy/`. Wire it into `.github/workflows/ci-frontend.yml` and the root `gate` script. Until then, correct the comments so they do not claim protection that is absent.

---

### WR-06: nginx sends `Connection: upgrade` on every frontend request

**Severity:** WARNING
**File:** `ops/nginx/nginx.conf:32-34`
**Issue:**
```nginx
proxy_set_header Upgrade    $http_upgrade;
proxy_set_header Connection "upgrade";
```
`Upgrade` is dropped when `$http_upgrade` is empty (nginx omits empty headers), but `Connection: upgrade` is a literal and is sent on **every** proxied request. That is an HTTP/1.1 protocol violation for non-upgrade requests, disables upstream keep-alive, and makes some servers close connections after each response. The standard idiom is a `map`.
**Fix:**
```nginx
# at http{} level (a separate conf.d file or the main nginx.conf)
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''      close;
}

# in location / {}
proxy_set_header Upgrade    $http_upgrade;
proxy_set_header Connection $connection_upgrade;
```

---

### WR-07: The local `gate` script skips the frontend test suite that guards D-04 parity

**Severity:** WARNING
**File:** `package.json` (root, `scripts.gate`)
**Issue:** `gate` chains `lint → test → test:tenancy → i18n:check → typecheck → fe:lint → fe:build` but never runs `npm --prefix frontend test`. That suite contains `role-gate.test.mjs` (asserts `MARKET_ADMIN_ASSIGNABLE_ROLES` matches the Python gate and that `ROLES` matches `sbozor_core.enums.Role`) and `audit-actions.test.mjs` (audit action/table translation completeness). CI runs them (`ci-frontend.yml:45-46`), so a developer running the documented pre-push gate gets a green result on a change CI will reject — and, worse, `gate` is the artifact people trust when CI is slow.
**Fix:** `"gate": "... && npm --prefix frontend test && npm --prefix frontend run i18n:check && ..."`.

---

### WR-08: Refresh-family revocation trusts the cookie's `fam` without binding it to the authenticated user

**Severity:** WARNING
**File:** `services/core-api/app/api/v1/auth.py:523-544`, `services/core-api/app/api/v1/auth.py:697-717`
**Issue:** `_revoke_cookie_family()` and `logout()` decode the presented cookie and call `auth_repo.refresh_revoke_family(UUID(claims.family_id))` with no check that the family belongs to the caller. In `logout` the owning row is already fetched (`row = await auth_repo.refresh_find(session, claims.jti)`) and then used only for `market_id` — the free ownership check is discarded. In `select_market` the caller is authenticated as `principal.user_id` via the bearer token while the family comes from a *separate* credential (the cookie), and the two are never compared.

Today the JWT signature makes this safe, but the safety is implicit and undocumented. Any future change — accepting a family id from the request body, adding a second issuer, relaxing `typ` checks, or a token-format migration — turns this into a "revoke any session family" primitive, and no test would notice.
**Fix:**
```python
# logout — the row is already in hand.
row = await auth_repo.refresh_find(session, claims.jti)
if row is None or row.user_id != claims.user_id:
    log.info("logout_with_foreign_cookie")
else:
    await auth_repo.refresh_revoke_family(session, row.family_id)
    ...

# _revoke_cookie_family — take the expected owner explicitly.
async def _revoke_cookie_family(session, refresh_token, settings, *, expected_user_id: UUID) -> UUID | None:
    ...
    row = await auth_repo.refresh_find(session, claims.jti)
    if row is None or row.user_id != expected_user_id:
        return None
    await auth_repo.refresh_revoke_family(session, row.family_id)
    return row.family_id
```

---

### WR-09: `client-only` is imported but not declared in `frontend/package.json`

**Severity:** WARNING
**File:** `frontend/src/lib/api-client.ts:3`, `frontend/src/lib/auth-store.ts:3`, `frontend/package.json:18-37`
**Issue:** Both modules do `import "client-only";` and `auth-store.ts:40-41` describes it as the mechanism that *"bu faylning Server Component grafiga tortilishini butunlay bloklaydi"* — i.e. it is treated as a security-relevant boundary (keeping the in-memory access token out of the server graph). The package is not a declared dependency; it resolves only because `next` depends on it and npm hoists it into `frontend/node_modules/client-only`. A dependency-tree change, a nested install strategy, or a different package manager silently removes the guard, and the build succeeds without it.
**Fix:** `npm --prefix frontend install --save-exact client-only@0.0.1` and add it to `dependencies`. Same treatment for `server-only` if it is introduced later.

---

### WR-10: Sentry scrubbing drops body and cookies but keeps the query string

**Severity:** WARNING
**File:** `services/core-api/app/main.py:63-84`
**Issue:** `_scrub_event()` pops `request["data"]` and `request["cookies"]` and masks `authorization`/`cookie` headers, but leaves `request["query_string"]` and `request["url"]` untouched. `GET /api/v1/audit?actor_user_id=<uuid>&action=...` and the audit cursor therefore leave the trust boundary in full on any 500. The module docstring claims *"so'rov tanasi va cookie'lar u yerga umuman bormasligi kerak"* — the query string carries the same class of identifiers.
**Fix:**
```python
    if isinstance(request, dict):
        request.pop("data", None)
        request.pop("cookies", None)
        request.pop("query_string", None)
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = url.split("?", 1)[0]
        ...
```

## Info

### IN-01: `require_roles()` is dead code

**File:** `services/core-api/app/deps.py:358-373` (exported at `deps.py:71`)
**Issue:** Defined, documented, exported in `__all__`, and never referenced anywhere in `services/`, `tests/` or `packages/`. Its own docstring says `require_permission()` is preferred. Dead auth helpers are a liability — the next person reaches for it precisely in the "faqat platforma admini" case where CR-03 shows the role/flag distinction is already confused.
**Fix:** Delete it, or use it for the platform-admin-only surface once CR-03 is resolved.

---

### IN-02: Unused frontend dependencies and exports

**File:** `frontend/package.json:22,24`, `frontend/src/lib/api-types.ts:45,289-304`, `frontend/src/lib/rbac.ts:28-42`
**Issue:** `@radix-ui/react-select` and `date-fns` are declared but never imported (`src/` uses native `<select>` and `next-intl`'s formatter). `ERROR_CODES`/`ErrorCode` and `PERMISSIONS` are exported and never consumed; `soumSchema` is unused but explicitly documented as forward-looking for phases 5–6, so leave that one.
**Fix:** Drop the two packages; either wire `ERROR_CODES` into `errorMessageKey()`'s switch as an exhaustiveness check or remove it (note that it currently lists `password_change_required`, which is the ghost gate from CR-01).

---

### IN-03: CI action version drift between the two workflows

**File:** `.github/workflows/ci-backend.yml:20`, `.github/workflows/ci-frontend.yml:28-30`
**Issue:** Backend pins `actions/checkout@v7`; frontend uses `actions/checkout@v4` and `actions/setup-node@v4`. Two workflows checking out the same repo with different tooling generations invites "works in one job, not the other" surprises (line endings, sparse checkout defaults).
**Fix:** Align both on the same major, and add `concurrency`/`cancel-in-progress` to `ci-backend.yml` to match the frontend workflow.

---

### IN-04: The locale-parity gate silently skips when the frontend file moves

**File:** `tests/unit/test_enums.py:44`
**Issue:** `pytest.skip("frontend/src/i18n/routing.ts topilmadi (backend-only checkout)")` — if `routing.ts` is ever renamed or relocated, the `Locale` ↔ `routing.locales` parity check turns green instead of red. This is the exact "test exists but checks nothing" failure mode that `tests/tenancy/test_route_coverage.py` was written to prevent, and that file explicitly bans skip markers.
**Fix:** Gate on an env flag (`SBOZOR_BACKEND_ONLY=1`) rather than file existence, so a missing file in a full checkout fails loudly.

---

### IN-05: The `tests` compose service mounts the host Docker socket

**File:** `compose.yaml:148-150`
**Issue:** `- /var/run/docker.sock:/var/run/docker.sock` grants root-equivalent host control to anything running in that container. It is behind the `test` profile and needed for docker-outside-of-docker testcontainers, so this is accepted rather than wrong — but it should be an explicit, documented decision rather than an inline volume, since the same compose file is the deployment artifact.
**Fix:** Add a comment stating the trust assumption (developer machines and CI runners only, never the Contabo host), and confirm the `test` profile is never enabled in the production compose invocation.

---

_Reviewed: 2026-07-29T10:17:18Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
