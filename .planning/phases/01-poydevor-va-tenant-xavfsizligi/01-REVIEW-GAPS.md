---
phase: 01-poydevor-va-tenant-xavfsizligi
scope: gap-closure only (plans 01-11 … 01-15, diff base 1f36ae9)
reviewed: 2026-07-29T12:00:00Z
depth: standard
files_reviewed: 31
files_reviewed_list:
  - services/core-api/app/deps.py
  - services/core-api/app/api/v1/audit.py
  - services/core-api/app/api/v1/markets.py
  - services/core-api/app/api/v1/users.py
  - services/core-api/app/repositories/audit_repo.py
  - packages/sbozor-core/sbozor_core/logging.py
  - migrations/entities/functions.py
  - migrations/entities/policies.py
  - migrations/entities/__init__.py
  - migrations/versions/0005_platform_audit.py
  - compose.yaml
  - compose.override.yml
  - .env.example
  - frontend/src/components/auth/market-picker.tsx
  - frontend/src/components/auth/market-picker.test.tsx
  - frontend/src/lib/api-types.ts
  - frontend/scripts/role-gate.test.mjs
  - frontend/vitest.config.ts
  - frontend/vitest.setup.ts
  - frontend/package.json
  - tests/integration/test_password_gate.py
  - tests/integration/test_audit_platform.py
  - tests/integration/test_rate_limit_proxy.py
  - tests/integration/test_audit_read.py
  - tests/integration/test_users_api.py
  - tests/integration/test_me_locale.py
  - tests/tenancy/test_cross_tenant.py
  - tests/tenancy/test_login_bootstrap.py
  - tests/tenancy/test_meta.py
  - tests/fixtures/auth_users.py
  - tests/unit/test_logging.py
findings:
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 01 gap-closure: Code Review Report

**Reviewed:** 2026-07-29T12:00:00Z
**Depth:** standard
**Files Reviewed:** 31
**Status:** issues_found

## Summary

This is a focused adversarial review of the five gap-closure plans (01-11 … 01-15) against
`git diff 1f36ae9..HEAD`, restricted to source files (planning artifacts and
`frontend/package-lock.json` excluded).

Four of the five fixes hold up under tracing:

- **CR-03 (platform_admin as membership role)** is closed on both sides. `_assert_roles_assignable`
  rejects `Role.PLATFORM_ADMIN` unconditionally *before* any DB write, `list_markets` branches on the
  authoritative `principal.is_platform_admin` flag, `require_platform_admin` reads the same flag and
  never a derived role, and `hybrid_platform_role` is a genuine sabotage seed (I confirmed the hybrid
  account really does carry `market_view_all` and really is refused).
- **CR-02 (`isPending` → `isLoading`)** is correct for TanStack Query v5 semantics, and
  `market-picker.test.tsx` is a real regression lock: reverting to `isPending` fails it in both the
  `isBusy` and the early-return branch.
- **Gap 5 (platform audit)** is well-constructed. The `audit_read_platform` policy is `FOR SELECT
  TO sbozor_owner USING (market_id IS NULL)` — it opens no `UPDATE`/`DELETE` path, `sbozor_app`
  cannot use it, and the function's `WHERE market_id IS NULL` is literal, so tenant rows cannot be
  reached through it even if the policy set were widened. `LIMIT COALESCE(p_limit, 0)` is fail-closed
  as designed and `list_platform_audit`'s signature makes `None` unreachable from the endpoint.
- **CR-01 (`must_change_password`)** is enforced server-side and the state cache is invalidated on
  reset — but the wiring is not as total as the docstrings claim (WR-02, WR-03).

**CR-04 (proxy headers) is not fixed — it is inverted.** The shipped
`--forwarded-allow-ips *` combined with `ops/nginx/nginx.conf`'s `$proxy_add_x_forwarded_for` makes
`request.client.host` fully attacker-controlled. This is worse than the pre-fix state (an honest but
useless proxy IP): the login IP rate limiter can now be bypassed *and* weaponised against a specific
market's public IP, and `audit_log.ip` — the FOUND-03 evidence column the fix existed to repair —
becomes forgeable. The new `test_rate_limit_proxy.py` cannot see this because it writes the ASGI
`client` tuple directly and never exercises `ProxyHeadersMiddleware`.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: `--forwarded-allow-ips *` + nginx `$proxy_add_x_forwarded_for` makes the client IP attacker-controlled

**File:** `compose.yaml:100-111`, `compose.override.yml:30-40`, `.env.example:37-47`, `ops/nginx/nginx.conf:22`, `services/core-api/app/api/v1/auth.py:116-137`

**Issue:**

The fix ships `--forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}"` with `*` as the default in all
three places (`compose.yaml`, `compose.override.yml`, `.env.example`). uvicorn's
`ProxyHeadersMiddleware` treats `*` as `always_trust` and then takes the **leftmost**
`X-Forwarded-For` entry — verified in the upstream source, unchanged across 0.30.6 / 0.31.0 / 0.35.0
(the project pins `uvicorn[standard]==0.51.0`, downstream of the same code):

```python
def get_trusted_client_host(self, x_forwarded_for: str) -> str:
    x_forwarded_for_hosts = _parse_raw_hosts(x_forwarded_for)
    if self.always_trust:
        return x_forwarded_for_hosts[0]        # <-- leftmost
    for host in reversed(x_forwarded_for_hosts):
        if host not in self:
            return host
```

`ops/nginx/nginx.conf:22` uses `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, which
expands to `"$http_x_forwarded_for, $remote_addr"` — it **appends** the real peer to whatever the
client sent. So the leftmost element is always the value the client supplied.

Attack, from the open internet, no authentication needed:

```
GET /api/v1/auth/login            (client sends)  X-Forwarded-For: 203.0.113.9
nginx forwards                                    X-Forwarded-For: 203.0.113.9, <real-client-ip>
uvicorn (always_trust) picks                      203.0.113.9
_client_ip() parses it fine (auth.py:132) ->      request.client.host == "203.0.113.9"
```

Three consequences, all of them the exact failures CR-04 was written to prevent:

1. **The IP-scope login rate limit is bypassed.** `check_login_rate(cache, phone=..., ip=ip)`
   (`auth.py:271`) keys on `rl:login:ip:<attacker-chosen>`. Rotating the header per request gives an
   unbounded IP budget; only the per-phone limit (10) survives, so credential stuffing across many
   phone numbers is unthrottled.
2. **Targeted denial of service.** An attacker can pin `X-Forwarded-For` to a market's known public
   IP and burn its 50-attempt budget on demand, locking every cashier, market admin and director at
   that site out with `429 too_many_attempts` for 15 minutes, repeatedly. The compose comment itself
   documents this as the failure mode being fixed; the fix as configured hands the trigger to the
   attacker.
3. **`audit_log.ip` becomes forged evidence.** `write_app_audit(..., ip=ip)` on `login`,
   `login_failed`, `logout`, `market_selected` and `refresh_reuse_detected` now stores an
   attacker-chosen address. A wrong-but-honest proxy IP is recoverable; a plausible-looking forged IP
   in the very log that `GET /api/v1/audit/platform` was just built to expose (Gap 5, FOUND-03) is
   actively misleading during a dispute.

Secondary: `always_trust` also accepts `X-Forwarded-Proto` from any peer, making `scope["scheme"]`
client-controlled. Low impact today (`COOKIE_SECURE` is settings-driven, not scheme-driven), but it
is part of the same over-broad trust grant.

The safety argument written into `compose.yaml:93-99` ("`*` is safe because core-api is not published
to the host") is the wrong argument even where it is true: with `*`, uvicorn does not stop at the
proxy — it walks past it to a client-supplied value. See also WR-08: that argument is additionally
false whenever `compose.override.yml` is auto-loaded.

**Fix:**

Two independent changes; apply both.

1. Never use `*`. uvicorn's `_TrustedHosts` accepts CIDR networks, so pin the proxy:

```yaml
# compose.yaml + compose.override.yml (command must be repeated in both — it is replaced, not merged)
      - "--forwarded-allow-ips"
      - "${FORWARDED_ALLOW_IPS:?set to the nginx address or the compose subnet, never *}"
```

```dotenv
# .env.example — Docker's default bridge pool; narrow further to nginx's fixed IP if you assign one.
FORWARDED_ALLOW_IPS=172.16.0.0/12
```

With a non-`*` value uvicorn walks the chain right-to-left and skips trusted hops, so a client that
prepends junk is ignored and the real peer as seen by nginx is used.

2. Make the header non-spoofable at the proxy regardless of uvicorn's algorithm — overwrite instead
   of append (SBOZOR has exactly one proxy hop, so there is no chain to preserve):

```nginx
        proxy_set_header X-Forwarded-For   $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
```

3. Add an end-to-end regression test that actually runs `ProxyHeadersMiddleware` (see WR-01),
   otherwise this class of defect stays invisible to CI a second time.

## Warnings

### WR-01: `test_rate_limit_proxy.py` cannot detect a CR-04 regression — it bypasses the layer under test

**File:** `tests/integration/test_rate_limit_proxy.py:61-69, 127-148`

**Issue:** The file's docstring states its purpose as turning "deploy-only folklore into a test", but
`_client_at()` sets `httpx.ASGITransport(app=api_app, client=(host, CLIENT_PORT))` — it writes the
*result* that a correctly configured `ProxyHeadersMiddleware` would produce, and then asserts that
result. `test_forwarded_header_alone_does_not_move_the_counter` proves only that *application code*
ignores `X-Forwarded-For`, which was never in question (`_client_ip` reads `request.client`). The
middleware, the `--forwarded-allow-ips` value and the nginx header directive — the three things that
actually decide the outcome — have zero coverage. This is why CR-01 above shipped green.

**Fix:** Wrap the app in the real middleware with the real configured value and assert the untrusted
case:

```python
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

def _proxied(api_app, trusted: str) -> httpx.AsyncClient:
    wrapped = ProxyHeadersMiddleware(api_app, trusted_hosts=trusted)
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=wrapped, client=(NGINX_IP, 9000)),
        base_url="http://testserver",
    )

async def test_client_cannot_forge_its_own_ip_through_the_proxy(api_app, valkey_client):
    """nginx appends: XFF == '<client claim>, <real peer>'. The counter must key on the REAL peer."""
    async with _proxied(api_app, NGINX_IP) as client:      # never "*"
        await client.post(LOGIN_URL, json={...},
                          headers={"X-Forwarded-For": f"{SPOOFED_IP}, {CLIENT_A_IP}"})
    assert await _counter(valkey_client, SPOOFED_IP) is None
    assert await _counter(valkey_client, CLIENT_A_IP) == 1
```

Also assert the deployed value itself, so a future edit to `compose.yaml` fails a test rather than
production: parse `compose.yaml` / `compose.override.yml` and assert `--forwarded-allow-ips` is
present in both and is not `*` (same pattern already used by `test_locale_enum_matches_frontend_routing`
and `role-gate.test.mjs`, which read source files directly).

### WR-02: two write endpoints skip `require_password_current`, and one of them defeats reset-password's session revocation

**File:** `services/core-api/app/api/v1/auth.py:429-500`, `services/core-api/app/api/v1/me.py:79-125`, `services/core-api/app/deps.py:22-27`

**Issue:** The gate is wired into `get_tenant_session`, `require_permission` and `require_roles` — but
not into `get_auth_session`, and `PrincipalDep + AuthSessionDep` is a legitimate, already-used
pattern. Walking every route in `app.main`:

| Route | Gated by `require_password_current`? |
|---|---|
| `POST /api/v1/auth/change-password` | no — intentional, documented |
| `POST /api/v1/auth/logout` | no — intentional, documented |
| `GET /api/v1/me` | no — intentional, documented |
| `PATCH /api/v1/me` | **no — undocumented, and it writes** |
| `POST /api/v1/auth/select-market` | **no — undocumented, and it mints a session** |
| everything else | yes |

The `deps.py:22-26` docstring enumerates exactly three exempt endpoints and claims a new endpoint
"cannot forget to add" the gate. Both statements are inaccurate: `POST /auth/select-market` is not in
the list at all, and any future endpoint built on `PrincipalDep + AuthSessionDep` inherits the same
hole silently.

`select-market` is the one with security consequence. `reset_password`'s docstring claims
"foydalanuvchining BARCHA refresh sessiyalari bekor qilinadi (ASVS V7)". An attacker holding the
victim's still-valid access token (≤15 min — precisely the CR-01 threat model spelled out in that
same docstring) can call `POST /auth/select-market` after the reset: `_issue_session_cookie` writes a
**new** refresh family and sets a fresh 30-day cookie, which `refresh_revoke_user` has already run
past. `/auth/refresh` never checks `must_change_password`, so the family can be rotated indefinitely.
The attacker gains no tenant data (every data endpoint still returns `password_change_required`), so
this is not privilege escalation — but the documented revocation guarantee is false, and the residual
session survives until the victim actually performs a password change.

`PATCH /api/v1/me` lets a gated session write `users.locale` and emit an `update` audit row under the
victim's identity. Minor by itself, but it contradicts the "no write endpoint" claim.

**Fix:**

1. Gate `select-market` (it is a session operation, not the escape hatch):

```python
# services/core-api/app/api/v1/auth.py
from app.deps import CurrentPasswordDep

@router.post("/select-market", response_model=SessionResponse)
async def select_market(
    payload: SelectMarketRequest,
    request: Request,
    response: Response,
    principal: CurrentPasswordDep,   # was PrincipalDep
    ...
```
   and the same for `update_profile` in `me.py` if locale changes are not meant to be reachable
   pre-change (leave `read_profile` on `PrincipalDep`).

2. Close the structural hole the same way the cross-tenant matrix is closed: add a route-coverage
   gate to `tests/integration/test_password_gate.py` that walks `app.routes` (reuse
   `tests/tenancy/test_cross_tenant.py::all_routes`) and asserts every route not in an explicit,
   reasoned `PASSWORD_GATE_EXEMPT` map returns `403 password_change_required` for
   `auth_seed.must_change`. Today the file hard-codes four routes, so route #5 is a silent hole.

3. Correct the enumeration in `deps.py:22-27` and `app/api/v1/audit.py` once the wiring matches.

### WR-03: `select_market` re-signs `is_platform_admin` from the caller's token instead of re-reading the DB

**File:** `services/core-api/app/api/v1/auth.py:455, 490-496`

**Issue:** `require_platform_admin` (`deps.py:486-522`) and `list_markets` (`markets.py:98`) both
depend on `principal.is_platform_admin` being *authoritative*. That flag reaches the `Principal` from
the JWT claim (`deps.py:359`), and every issuer re-reads `users.is_platform_admin` from the
database — `login` uses `row.is_platform_admin` (auth.py:318) and `refresh` uses
`who.is_platform_admin` (auth.py:628) — **except** `select_market`, which copies it from the
presented token:

```python
    roles = _session_roles(membership, is_platform_admin=principal.is_platform_admin)
    ...
        access_token=issue_access(..., is_platform_admin=principal.is_platform_admin, ...)
```

Because `select-market` accepts any market the flag permits and requires only a live access token,
`token -> select-market -> new token -> select-market -> ...` renews `pa=true` forever without ever
touching `users`. Combined with WR-02 (select-market is also outside the password gate), a demoted or
must-change platform admin retains the flag indefinitely.

Note this is *not* a way to obtain the flag — `_assert_roles_assignable` and `require_platform_admin`
correctly refuse derived roles, and `test_hybrid_platform_role_is_forbidden` proves it. It is a way to
*retain* it past revocation. There is no revocation API in phase 1, which is the only reason this is
not already exploitable; the moment one is added (market wizard / platform admin management) this
becomes a live authorization bypass.

**Fix:** Re-read the flag on the one path that mints tokens from a token:

```python
    who = await auth_repo.find_login_by_id(session, principal.user_id)
    if who is None or not who.is_active:
        raise _invalid_credentials()
    is_platform_admin = who.is_platform_admin        # DB, not the incoming claim
    roles = _session_roles(membership, is_platform_admin=is_platform_admin)
```
`find_login_by_id` is already called a few lines below for the audit label, so this costs nothing —
hoist it. Add a test that seeds `is_platform_admin=true`, mints a token, flips the column to `false`
directly, and asserts `select-market` no longer returns a `pa=true` session.

### WR-04: a crafted cursor with an out-of-`bigint` row id returns 500 instead of 422

**File:** `services/core-api/app/repositories/audit_repo.py:136-149, 328-339`, `services/core-api/app/api/v1/audit.py:245-251`

**Issue:** `decode_cursor` catches `binascii.Error | UnicodeDecodeError | ValueError`, but
`int("99999999999999999999")` succeeds in Python — it is only Postgres/asyncpg that rejects it. The
value is then bound as `BigInteger` (`_PLATFORM_AUDIT` bindparam, and `literal(row_id, BigInteger())`
on the tenant path), asyncpg raises a `DataError`, and SQLAlchemy surfaces it as a `DBAPIError`. The
global handler in `main.py:129-150` does not match the RLS marker, so it logs
`log.error("database_error", ...)` and returns `500 {"detail": "internal_error"}`.

So a malformed cursor is 422 for most shapes and 500 for this one — an authenticated user can emit
ERROR-level log lines and Sentry events at will, and the API contract (`invalid_cursor`, already
reserved in `frontend/src/lib/api-types.ts:331`) is not honoured. Both audit endpoints are affected;
`test_malformed_cursor_is_rejected` only exercises `"not-a-cursor"`, which decodes into a
`ValueError` and is therefore caught.

Related: `datetime.fromisoformat("2026-01-01T00:00:00")` (no offset) yields a naive datetime bound to
`timestamptz`; asyncpg interprets it in the process's local zone rather than rejecting it, so a
hand-built cursor silently shifts the page boundary. Not a leak (the boundary is applied after
`market_id IS NULL` / RLS) but it undercuts the `timezone=True` rationale in the bindparam docstring.

**Fix:** Validate range and awareness inside `decode_cursor`, where the error already has a home:

```python
_BIGINT_MAX = 2**63 - 1

def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
        raw_at, raw_id = decoded.split("|", maxsplit=1)
        at = datetime.fromisoformat(raw_at)
        row_id = int(raw_id)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise InvalidCursorError(str(exc)) from exc
    if not 0 < row_id <= _BIGINT_MAX:
        raise InvalidCursorError("row id out of bigint range")
    if at.tzinfo is None:
        raise InvalidCursorError("cursor timestamp must carry an offset")
    return at, row_id
```
Extend `test_malformed_cursor_is_rejected` in both `test_audit_read.py` and `test_audit_platform.py`
to cover an oversized id and a naive timestamp.

### WR-05: exempting `/api/v1/audit/platform` silently dropped two of the three token-rejection matrices

**File:** `tests/tenancy/test_cross_tenant.py:101-135`, `tests/integration/test_audit_platform.py:275-280`

**Issue:** The exemption is legitimate (the route is deliberately not a tenant resource), and the
docstring correctly warns that an exemption removes the route from the token matrices too — then
claims the coverage was "AYNAN qayta tiklangan" (exactly restored) in `test_audit_platform.py`. It was
not. `MATRIX_ROUTES` drives three parametrized tests:

- `test_missing_token_is_rejected` — restored (`test_audit_platform.py:275`)
- `test_malformed_token_is_rejected` — **not restored**
- `test_expired_token_is_rejected` — **not restored**

The expired-token case is the one worth having: it is the only test in the suite that proves `exp` is
enforced with a genuinely valid signature, and it is exactly the check a future refactor of
`decode()`/`get_current_principal` could break. Low residual risk today (all routes share
`get_current_principal`), but the file's own rule was not followed, and the docstring now asserts a
coverage level that does not exist.

**Fix:** Add the two missing cases next to the existing one:

```python
async def test_malformed_token_is_rejected(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get(PLATFORM_AUDIT_URL, headers=bearer("buzilgan.token.qiymati"))
    assert response.status_code == 401


async def test_expired_token_is_rejected(
    api_client: httpx.AsyncClient, auth_seed: AuthSeed, test_settings: Settings
) -> None:
    expired = encode_access(
        user_id=auth_seed.platform_admin.user_id, market_id=auth_seed.market_a_id,
        roles=["platform_admin"], is_platform_admin=True,
        secret=test_settings.jwt_secret, issuer=test_settings.jwt_issuer,
        audience=test_settings.jwt_audience, ttl_minutes=-5,
    )
    response = await api_client.get(PLATFORM_AUDIT_URL, headers=bearer(expired))
    assert response.status_code == 401
```

### WR-06: recursive `censor_secrets` rewrites tuples to lists, breaking explicit `exc_info` payloads

**File:** `packages/sbozor-core/sbozor_core/logging.py:82-113, 127-138`

**Issue:** The WR-01 recursion fix added `tuple` handling to `_censor`, which converts tuples to lists
(documented as harmless because JSON has no tuples). It is not harmless for one structlog key.
`censor_secrets` runs at processor position 4, *before* `format_exc_info` at position 6, and it
rewrites **every** key including `exc_info`. structlog's `_figure_out_exc_info` special-cases tuples:

```python
if isinstance(v, tuple):
    return v                 # (type, exc, tb) used as-is
if v:
    return sys.exc_info()    # a LIST lands here
```

So `log.error("failed", exc_info=sys.exc_info())` — a supported structlog call form — arrives at
`format_exc_info` as a list, falls through to `sys.exc_info()`, and outside an active `except` block
that is `(None, None, None)`: the traceback is lost or replaced by an unrelated one. Nothing in the
current tree passes `exc_info` explicitly (only `structlog.processors.format_exc_info` is referenced),
so this is latent — but it is a trap planted in the one module every service logs through, and the new
`test_censor_secrets_masks_nested_tuple` locks the converting behaviour in.

**Fix:** Skip the structlog-reserved keys, which are not user payload and can never carry a secret:

```python
_RESERVED_KEYS = frozenset({"exc_info", "stack_info", "exception", "_record", "_from_structlog"})

def censor_secrets(logger, method_name, event_dict):
    for key in list(event_dict):
        if key in _RESERVED_KEYS:
            continue
        event_dict[key] = CENSORED if _is_sensitive(key) else _censor(event_dict[key])
    return event_dict
```

### WR-07: `Permission.MARKET_VIEW_ALL` now has no enforcement point, but is still documented and advertised as if it did

**File:** `services/core-api/app/security/rbac.py:52, 68-77`, `frontend/src/lib/rbac.ts:44-53`, `services/core-api/app/api/v1/auth.py:798`

**Issue:** The CR-03 fix moved `list_markets` off the permission and onto the flag. Grepping the whole
tree confirms `MARKET_VIEW_ALL` / `market_view_all` is now referenced **only** by the matrix
definitions, tests and comments — no `require_permission(Permission.MARKET_VIEW_ALL)`, no
`hasPermission(roles, "market_view_all")` in any component. It is a permission that grants nothing.

Two problems follow. First, both matrices still document it as live: `rbac.py:69-70` and
`rbac.ts:45-46` say "u faqat bozor tanlash ekranini ochadi", which is now false in both languages.
Second, `GET /api/v1/auth/me` keeps returning `market_view_all` in `permissions` for anyone holding
the `platform_admin` role string — the hybrid seed relies on this — so a future developer reading
either the matrix or an `/auth/me` response will reasonably wire a new "all markets" endpoint to the
permission and reintroduce CR-03 verbatim.

**Fix:** Make the reintroduction impossible rather than merely discouraged. Either delete the
permission from both matrices (and from `PERMISSIONS` in `rbac.ts`), or keep it and add a unit gate
that fails if it ever reappears in a `require_permission(...)` call:

```python
# tests/unit/test_rbac_matrix.py
def test_market_view_all_is_never_used_as_an_endpoint_gate() -> None:
    """CR-03: cross-market scope is decided by `users.is_platform_admin`, never by a role-derived
    permission. A `require_permission(MARKET_VIEW_ALL)` anywhere re-opens the hybrid-account hole."""
    api_dir = Path(__file__).resolve().parents[2] / "services" / "core-api" / "app"
    offenders = [
        path for path in api_dir.rglob("*.py")
        if "MARKET_VIEW_ALL" in path.read_text(encoding="utf-8")
        and "require_permission" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"MARKET_VIEW_ALL used as a gate again (CR-03): {offenders}"
```
At minimum, rewrite the two docstrings to state that the permission is inert and that
`is_platform_admin` is the only cross-market authority.

### WR-08: the "`*` is safe because core-api is not published" justification is void under the auto-loaded dev override

**File:** `compose.yaml:93-99`, `compose.override.yml:1-45`, `package.json:8-12`

**Issue:** `compose.override.yml:1` states plainly that Docker Compose loads it **automatically**.
Nothing in the repository pins a production invocation — `package.json`'s `up`, `migrate`, `test` and
`logs` scripts all call bare `docker compose`, and there is no `-f compose.yaml` anywhere. Any
deployment that runs `docker compose up` on the VPS therefore gets, in production:

- `build.target: dev` instead of `runtime`
- `--reload` (file-watching autoreload)
- the whole repository bind-mounted at `/app`
- core-api published on `127.0.0.1:8000`

The last item directly contradicts the safety argument written into `compose.yaml:93-96`, and
combined with CR-01 it means anything that can reach loopback on the host (another container using
`network_mode: host`, an SSH user, a compromised sidecar) can set its own client IP with no proxy in
the path at all. In the default dev flow (`npm run up` starts only `db`, `cache`, `core-api` —
`nginx` is behind the `proxy` profile) there is no proxy in the path either way.

**Fix:** Give production an explicit, non-overridable entry point and stop relying on prose:

```json
  "up": "docker compose up -d db cache core-api --wait",
  "up:prod": "docker compose -f compose.yaml --profile proxy --profile web up -d --wait"
```
and add a comment at the top of `compose.override.yml` stating that any deployment must pass
`-f compose.yaml` explicitly. Independently, fix `FORWARDED_ALLOW_IPS` per CR-01 so the override's
presence stops being a security-relevant question.

## Info

### IN-01: `list_platform_audit(limit=0)` raises `IndexError`

**File:** `services/core-api/app/repositories/audit_repo.py:359-363`

**Issue:** With `limit=0` the function requests `p_limit=1`, gets one row, evaluates `len(rows) > 0`,
slices to `rows[:0] == []`, then indexes `rows[-1]`. Unreachable from the endpoint
(`Query(ge=1, le=AUDIT_PAGE_SIZE_MAX)`), but the docstring already anticipates future callers and the
function is exported in `__all__`.

**Fix:** `if limit < 1: raise ValueError("limit must be >= 1")` at the top, or guard the branch with
`if len(rows) > limit and rows[:limit]:`. Same shape exists in `AuditRepository.list_audit:206-209`.

### IN-02: `require_roles()` is still dead code, but the gate wiring inside it is reported as verified

**File:** `services/core-api/app/deps.py:464-483`

**Issue:** No endpoint calls `require_roles`; 01-15 explicitly considered and rejected it for
`require_platform_admin`. Its `CurrentPasswordDep` binding is therefore exercised by nothing, while
`01-VERIFICATION.md` lists it as "WIRED". Carrying an unused authorization primitive is how the
role-vs-flag confusion behind CR-03 got written in the first place.

**Fix:** Delete it (and its `__all__` entry), or add a unit test that builds the dependency and
asserts both the 403-on-missing-role and the `password_change_required` ordering, so the branch is not
merely present.

### IN-03: `clear_request_context()` is documented as mandatory per request but never called in production

**File:** `packages/sbozor-core/sbozor_core/logging.py:145-166`

**Issue:** `bind_request_context` is called from `get_current_principal` (`deps.py:352`);
`clear_request_context` appears only in `tests/unit/test_logging.py`. The docstring says
"har so'rov boshida `clear_request_context()` chaqirilishi kerak". Benign in practice — asyncio gives
each request its own task and therefore its own contextvar copy — but the file states a requirement
the codebase does not meet, so a future non-asyncio consumer (arq worker in the cv-service) will
inherit a stale `market_id` in its log lines.

**Fix:** Either call it from a middleware in `main.py` (before `CorrelationIdMiddleware` completes),
or soften the docstring to state that per-task isolation makes it optional for the ASGI path and
mandatory for long-lived worker loops.

### IN-04: `MarketPicker` has no error branch — a failed `GET /markets` renders "you have no markets"

**File:** `frontend/src/components/auth/market-picker.tsx:51-132`

**Issue:** When the fallback query fails, `isLoading` goes false, `data` stays `undefined`, `options`
is empty, and the component renders `auth.noMarkets` plus a logout button. A transient network or
5xx error is presented to the user as a permanent account condition, and the offered action is to log
out — which discards the session that would have worked on retry.

**Fix:** Branch on `marketsQuery.isError` before the empty-list branch and show a retry:

```tsx
  if (marketsQuery.isError) {
    return (
      <p className="text-sm text-danger" role="alert">
        {t(errorMessageKey(marketsQuery.error))}
      </p>
    );
  }
```

### IN-05: vitest only collects `*.test.tsx`, and the root `gate` script omits the frontend suite

**File:** `frontend/vitest.config.ts:32`, `package.json:15`

**Issue:** `include: ["src/**/*.test.tsx"]` means a component or hook test written as `*.test.ts` (no
JSX — e.g. a `useAuthStore` test) is collected by neither runner: `node --test scripts/*.test.mjs`
only looks in `scripts/`, and vitest only looks for `.tsx`. Separately, the repo's own quality gate
(`npm run gate`) runs backend lint/tests plus frontend `i18n:check`/`typecheck`/`lint`/`build`, but
**not** `npm --prefix frontend run test` — so neither the new CR-02 component lock nor the re-locked
CR-03 `role-gate.test.mjs` runs locally. CI (`ci-frontend.yml`, step "Transliterator testlari") does
run `npm --prefix frontend test`, so this is a local-gate gap only. That step's name is also stale now
that it runs three suites.

**Fix:** `include: ["src/**/*.test.{ts,tsx}"]`; append `&& npm --prefix frontend run test` to the root
`gate` script; rename the CI step to something like "Frontend testlari (node:test + vitest)".

### IN-06: `_censor` recursion is unbounded

**File:** `packages/sbozor-core/sbozor_core/logging.py:72-88`

**Issue:** A self-referential or very deep value in an event dict now raises `RecursionError` inside
the structlog pipeline, which propagates to the caller of `log.info(...)` — i.e. a logging statement
can abort a request handler. Before the WR-01 fix only the top level was touched, so this failure mode
is new. All current call sites pass scalars, so it is theoretical today.

**Fix:** Carry a depth budget and stop rather than raise:

```python
_MAX_CENSOR_DEPTH = 6

def _censor(value: object, depth: int = 0) -> object:
    if depth >= _MAX_CENSOR_DEPTH:
        return CENSORED
    if isinstance(value, dict):
        return {k: CENSORED if _is_sensitive(k) else _censor(v, depth + 1) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_censor(item, depth + 1) for item in value]
    return value
```

### IN-07: `/api/v1/audit/platform` also exposes successful logins, and those logins are invisible to tenant audit viewers

**File:** `services/core-api/app/api/v1/auth.py:311, 340`, `services/core-api/app/api/v1/audit.py:208-217`

**Issue:** `auto_select` is `None` whenever the user is a platform admin *or* holds more than one
membership, and the login audit row is then written with `market_id=None` (`auth.py:340`). So the
`market_id IS NULL` set is not just `login_failed`: it also contains successful `login` rows for every
platform admin and every multi-market user. Two consequences worth recording: the new endpoint's
docstring under-describes what it returns ("birinchi navbatda `login_failed`"), and — the more
important half — a market admin querying `GET /api/v1/audit` can never see that a director with
memberships in two markets logged in, because that event carries no `market_id`. D-11's "who accessed
this market" story has a hole that Gap 5 closes only for platform admins.

**Fix:** No code change required for phase 1, but record the decision explicitly: either accept it
(document in `audit.py` that market-less login rows are platform-scoped by design) or write a second,
market-scoped `login` row once `select-market` resolves the market — `select_market` already writes
`market_selected` with `market_id` set, so tenant viewers arguably have the equivalent signal and the
docstring should say so.

---

_Reviewed: 2026-07-29T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
