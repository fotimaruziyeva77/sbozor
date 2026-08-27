---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
reviewed: 2026-08-01T00:00:00Z
depth: standard
files_reviewed: 55
files_reviewed_list:
  - services/core-api/app/security/rbac.py
  - services/core-api/app/security/audit.py
  - services/core-api/app/deps.py
  - services/core-api/app/main.py
  - services/core-api/app/settings.py
  - services/core-api/app/schemas.py
  - services/core-api/app/api/v1/markets.py
  - services/core-api/app/api/v1/stalls.py
  - services/core-api/app/api/v1/vendors.py
  - services/core-api/app/api/v1/assignments.py
  - services/core-api/app/api/v1/imports.py
  - services/core-api/app/api/v1/calendar.py
  - services/core-api/app/api/v1/tariffs.py
  - services/core-api/app/api/v1/auth.py
  - services/core-api/app/repositories/market_repo.py
  - services/core-api/app/repositories/stall_repo.py
  - services/core-api/app/repositories/vendor_repo.py
  - services/core-api/app/repositories/import_repo.py
  - services/core-api/app/services/xlsx_reader.py
  - services/core-api/app/services/xlsx_template.py
  - services/core-api/app/services/import_validator.py
  - migrations/entities/functions.py
  - migrations/entities/triggers.py
  - migrations/entities/policies.py
  - migrations/versions/0007_market_domain.py
  - migrations/versions/0008_temporal.py
  - migrations/versions/0009_vendors.py
  - migrations/versions/0010_calendar.py
  - packages/sbozor-core/sbozor_core/periods.py
  - packages/sbozor-core/sbozor_core/schema_contract.py
  - packages/sbozor-core/sbozor_core/timeutil.py
  - packages/sbozor-core/sbozor_core/money.py
  - frontend/src/lib/api-client.ts
  - frontend/src/lib/api-types.ts
  - frontend/src/lib/market-queries.ts
  - frontend/src/lib/market-errors.ts
  - frontend/src/lib/rbac.ts
  - frontend/src/lib/auth-queries.ts
  - frontend/src/lib/auth-store.ts
  - frontend/src/lib/query-provider.tsx
  - frontend/src/app/[locale]/(app)/layout.tsx
  - frontend/src/app/[locale]/(app)/markets/new/page.tsx
  - frontend/src/app/[locale]/(app)/markets/setup/page.tsx
  - frontend/src/components/wizard/wizard-shell.tsx
  - frontend/src/components/wizard/wizard-steps.ts
  - frontend/src/components/wizard/market-requisites-form.tsx
  - frontend/src/components/wizard/activation-panel.tsx
  - frontend/src/components/auth/market-picker.tsx
  - frontend/src/components/import/import-panel.tsx
  - frontend/src/components/shell/app-shell.tsx
  - frontend/messages/uz-Latn.json
  - frontend/messages/uz-Cyrl.json
  - frontend/messages/ru.json
  - scripts/karmana-import.mjs
  - tests/tenancy/test_cross_tenant.py
  - tests/tenancy/test_route_coverage.py
  - ops/data/karmana/.gitignore
  - ops/db/init/00-extensions.sql
findings:
  critical: 3
  warning: 10
  info: 5
  total: 18
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-08-01
**Depth:** standard
**Files Reviewed:** 55 (of 149 in scope — see Scope note)
**Status:** issues_found

## Summary

Phase 02 delivers the market domain: 5+5 tables across migrations 0007–0010, 43 routes,
RLS everywhere, Excel import, and a 7-step wizard. The **server-side** tenant story is
genuinely strong and I could not break it: every `SECURITY DEFINER` function pins
`search_path`, `NULLIF(...)` fail-closed is applied consistently, composite FKs make
cross-tenant references structurally impossible, money is `BIGINT`/`int` throughout with
no `float` anywhere, `date.today()` appears only in comments in production code, and the
cross-tenant test matrix (`tests/tenancy/`) is one of the more honest gate designs I have
reviewed — `FILE_FILLERS`, `BODY_FILLERS` and the OpenAPI cross-check all carry real
load-bearing assertions.

That is where the good news ends. Three defects are blocking:

1. **The client-side cache has no tenant boundary at all.** Every React Query key omits
   `market_id`, and neither market switch nor logout clears the cache. The phase's own
   headline invariant ("hamma jadvalda `market_id`") is enforced in Postgres and then
   discarded in the browser.
2. **Personal data (vendor name + phone) is served by three stall routes under a
   permission whose own docstring says it does not cover personal data, with no read
   audit.** The constants that would have wired that audit
   (`TABLE_STALLS`, `TABLE_TARIFFS`, `TABLE_MARKET_PROFILE`) exist, are exported, name
   these exact routes in their docstrings — and are referenced nowhere.
3. **The wizard cannot be reached.** `MARKET-01` — the phase's stated deliverable — is
   unreachable through the UI for a first market.

Items 2 and 3 were self-reported as OPEN by the executors. I am confirming both as real
and rating them; item 3 in particular is not a polish item, it is the feature not
shipping. Item 1 was not self-reported.

Beyond that: an unbounded request body on the error-report endpoint whose own docstring
claims it is bounded, a `SECURITY DEFINER` delete-cascade whose only tenant boundary is
one application-layer helper, an unvalidated-and-ignored `timezone` column, and a
BEFORE/AFTER trigger contradiction stated as fact in two files.

### Scope note

This is a 149-file phase. I budgeted by risk rather than reading uniformly: Tier 1
(security, tenancy, hostile file input, migrations) and Tier 2 (contracts, query layer,
wizard, import UI, tenancy gates) were read line by line — 55 files, listed in the
frontmatter. The remaining Tier 3 files (UI primitives, list/dialog components, remaining
integration tests) received a mechanical sweep only: dangerous DOM APIs
(`dangerouslySetInnerHTML`/`innerHTML`/`eval`), Web Storage usage, hardcoded credentials,
debug artifacts, and i18n key parity across all three locales. All four sweeps came back
clean (418/418/418 keys, zero drift; no storage API outside the documented ban; no
secrets; `console.log` only in the CLI script where it is the output channel). Tier 3
should not be assumed reviewed for logic.

---

## Critical Issues

### CR-01: React Query cache is not tenant-scoped and is never cleared on market switch or logout

**File:** `frontend/src/lib/market-queries.ts:89-116`
**Also:** `frontend/src/lib/query-provider.tsx:15-47`, `frontend/src/lib/auth-store.ts:110-113,137-156`, `frontend/src/components/wizard/market-requisites-form.tsx:193-204`, `frontend/src/components/auth/market-picker.tsx:88-100`, `frontend/src/components/shell/user-menu.tsx:33`

**Issue:**
Every domain query key omits the market identifier:

```ts
export const ZONES_KEY = ["zones"] as const;
export const STALLS_KEY = ["stalls"] as const;
export const VENDORS_KEY = ["vendors"] as const;
export const CALENDAR_KEY = ["calendar"] as const;
export const ASSIGNMENTS_KEY = ["assignments"] as const;
```

`setupStatusKey(marketId)` is the **only** key in the module that includes it.

`applySession()` (`auth-store.ts:137-156`) rewrites `accessToken`, `roles`, `marketId`
and `marketName` — and never touches the `QueryClient`. `clearSession()` (line 110-113)
resets the session object and likewise leaves the cache intact. A repo-wide search for
`queryClient.clear()`, `removeQueries` or `resetQueries` returns zero hits outside tests.
The default `staleTime` is 30 s and `gcTime` is the TanStack default 5 min.

Two reachable paths:

* **Market switch inside a live session.** A platform admin working in market A opens
  `/markets/new`, creates market B, and `MarketRequisitesForm` calls
  `selectMarket.mutateAsync(created.id)` → `applySession(...)` →
  `router.replace("/markets/setup?step=2")`. Step 2 renders `<ZoneList>` →
  `useZonesQuery()` → key `["zones"]` → **market A's zones are rendered instantly as
  market B's**, with no refetch at all inside the 30 s stale window. Step 5 and 6 do the
  same for `["stalls",...]` and `["vendors",...]` — and the vendor payload is
  `full_name` + `phone`, i.e. exactly the personal data D-09 governs.
* **Logout → login as a different user on the same tab.** `clearSession()` runs in
  `useLogout.onSettled`; the next user's first render is served the previous user's
  cached rows.

Server-side RLS still holds: a mutation carrying market A's `zone_id` under market B's
token gets a 404, and no cross-tenant write is possible. This is a client-side
**disclosure and wrong-data-displayed** defect, not a server bypass — but "usta 2-qadamda
boshqa bozorning zonalarini ko'rsatdi" is a tenant-isolation failure from the operator's
point of view, and the leaked payload includes personal data.

Note the design comment at `market-queries.ts:126-128` explicitly reasons *away* from
market-scoping (`setup-status` KENG bekor qilinadi ... `marketId` siz`) on the assumption
that "usta faqat BITTA bozor uchun ochiq bo'ladi". That assumption is false the moment a
platform admin creates a second market in one session — which is the wizard's whole
purpose.

**Fix:**

```ts
// 1) Scope every domain key by market.
export const domainKey = (marketId: string, ...rest: readonly unknown[]) =>
  ["m", marketId, ...rest] as const;

export const zonesKey = (marketId: string) => domainKey(marketId, "zones");
export const stallsKey = (marketId: string, filters: StallFilters) =>
  domainKey(marketId, "stalls", "list", filters);
// ...same for categories / map / tariffs / calendar / vendors / assignments
```

```ts
// 2) Hard-reset the cache whenever the session identity changes.
//    auth-store.ts cannot import QueryClient, so expose a hook:
export function useApplySessionAndReset() {
  const client = useQueryClient();
  return useCallback((next: Parameters<typeof applySession>[0]) => {
    client.clear();          // drops the previous market's rows outright
    applySession(next);
  }, [client]);
}
// use it in market-picker.tsx onSuccess and market-requisites-form.tsx onSubmit
// and call client.clear() alongside clearSession() in useLogout.onSettled.
```

Both halves are required: scoping alone leaves the old market's rows in memory until
`gcTime` expires (still reachable via devtools/back-navigation), and `clear()` alone
regresses the moment someone adds a market-switch UI.

---

### CR-02: Vendor name and phone are served under `MARKET_DATA_VIEW` with no personal-data read audit

**File:** `services/core-api/app/api/v1/stalls.py:238-317`
**Also:** `services/core-api/app/api/v1/assignments.py:317-340`, `services/core-api/app/repositories/stall_repo.py:594-596,637-641`, `services/core-api/app/security/rbac.py:72-83`, `services/core-api/app/security/audit.py:91-101`

**Issue:**
Three routes return vendor personal data behind `MARKET_DATA_VIEW` only, and none of them
declares `Depends(audit_read(...))`:

| Route | Guard | Personal data returned | Read audit |
|---|---|---|---|
| `GET /api/v1/stalls` | `MARKET_DATA_VIEW` | `vendor_name`, **plus free-text search over it** | none |
| `GET /api/v1/stalls/{id}` | `MARKET_DATA_VIEW` | `vendor_name` + `phone` | none |
| `GET /api/v1/stalls/{id}/assignments` | `MARKET_DATA_VIEW` | `vendor_name` (full history) | none |
| `GET /api/v1/vendors*` | `VENDOR_VIEW` | `full_name` + `phone` | ✅ `audit_read` |

The permission boundary is contradicted by its own definition. `rbac.py:72-76`:

> `MARKET_DATA_VIEW` — "Zona / toifa / rasta / tarif / kalendar O'QISH.
> **Shaxsiy ma'lumotni QAMRAMAYDI** — sotuvchi uchun alohida `VENDOR_VIEW`."

`stall_repo.py:637-641` goes further than mere display — it makes vendor names a
*queryable index* for `MARKET_DATA_VIEW` holders:

```sql
AND (
  :q_prefix IS NULL
  OR s.code   ILIKE :q_prefix
  OR v.full_name ILIKE :q_any     -- substring search over personal data
)
```

The audit gap is not an oversight of omission — the wiring was *declared and abandoned*.
`security/audit.py` exports three constants whose docstrings name these exact routes:

```python
TABLE_STALLS = "stalls"
"""`GET /stalls`, `GET /stalls/map`, `GET /stalls/{id}` — reestr resursi."""
TABLE_TARIFFS = "tariffs"
"""`GET /tariffs`, `POST /tariffs` — narx tarixi resursi (02-09)."""
TABLE_MARKET_PROFILE = "market_profile"
"""`PUT /calendar/weekdays` va usta rekvizitlari — bozor profili (02-09/02-11)."""
```

A repo-wide search shows `TABLE_STALLS`, `TABLE_TARIFFS` and `TABLE_MARKET_PROFILE` are
referenced **nowhere** outside their own definitions. `TABLE_VENDORS` is the only one of
the four that reached a call site. The module comment at `audit.py:75-88` asserts these
constants exist precisely because "`source='app'` yozuvi trigger KO'RA OLMAYDIGAN
hodisalar uchun yoziladi: shaxsiy ma'lumot O'QISHI (D-09)" — the rationale is written,
the code is not.

Impact against project constraints: CLAUDE.md lists "audit jurnali majburiy" as a hard
security constraint, and the data-residency constraint puts vendor name/phone under the
O'zR personal-data law. Today no role holds `MARKET_DATA_VIEW` without `VENDOR_VIEW`, so
the *authorization* half is latent; the *audit* half is live and failing on every
`GET /stalls` call.

**Fix:**

```python
# services/core-api/app/api/v1/stalls.py
from app.security.audit import TABLE_STALLS, AuditReadIntent, audit_read

StallReadIntentDep = Annotated[
    AuditReadIntent,
    Depends(audit_read(TABLE_STALLS, reason="stall_view")),
]

@router.get("/{stall_id}", response_model=StallDetail)
async def get_stall(
    stall_id: UUID,
    principal: MarketDataViewerDep,   # 1) permission first — 403 never reaches the audit
    intent: StallReadIntentDep,       # 2) intent second (see vendors.py module docstring)
    session: TenantSessionDep,        # 3) data last
) -> StallDetail:
    row = await StallRepository(session, _market_id(principal)).detail(stall_id, business_today())
    if row is None:
        raise _not_found()
    intent.filters = {"stall_id": str(stall_id)}
    intent.result_count = 1
    return _detail(row)
```

Apply the same three-argument ordering to `list_stalls` and `list_stall_assignments`
(`assignments.py:317`). Argument order is load-bearing — see the `vendors.py` module
docstring, lines 3-22.

Separately, decide the permission question explicitly: either require `VENDOR_VIEW` in
addition to `MARKET_DATA_VIEW` on the routes that expose `vendor_name`/`phone`, or amend
the `MARKET_DATA_VIEW` docstring so it stops claiming a boundary the code does not
enforce. Leaving both as-is means the next role added to the matrix silently inherits
personal-data access.

---

### CR-03: The market-creation wizard is unreachable — MARKET-01 cannot be completed through the UI

**File:** `frontend/src/app/[locale]/(app)/layout.tsx:52-62`
**Also:** `frontend/src/components/shell/app-shell.tsx:84-134`, `frontend/src/app/[locale]/(app)/markets/new/page.tsx:34-58`, `frontend/src/components/auth/market-picker.tsx:138-152`

**Issue:**
Two independent barriers, and together they close the route entirely.

**Barrier 1 — the layout bounces you out.** `/markets/new` lives under `(app)`, and that
layout redirects unconditionally:

```tsx
useEffect(() => {
  if (!checked || !principal) return;
  if (principal.mustChangePassword) { router.replace("/change-password"); return; }
  if (principal.marketId === null) { router.replace("/select-market"); }   // ← always
}, [checked, principal, router]);
```

and gates rendering on the same condition:

```tsx
const ready = checked && principal !== null
  && !principal.mustChangePassword
  && principal.marketId !== null;    // ← /markets/new can never render without a market
```

A platform admin whose platform has **zero** markets logs in with `marketId === null`,
is redirected to `/select-market`, and `MarketPicker` renders the empty-list branch
(lines 138-152) — a single logout button. There is no path from there to `/markets/new`.
The first market on a fresh deployment cannot be created through the product.

This is precisely the state `market-picker.tsx:29-33` describes as the recovery flow
("usta 1-qadamda qoralama bozor tug'diradi ... U qaytib kelganda AYNAN shu ekranni
ko'radi") — except the recovery screen has no entry point to the wizard it recovers into.

**Barrier 2 — no navigation entry.** `NAV_ITEMS` (`app-shell.tsx:84-134`) contains
`/dashboard`, `/map`, `/stalls`, `/vendors`, `/tariffs`, `/calendar`, `/users`, `/audit`.
There is no `/markets/new` item and no `market_manage`-gated entry anywhere. Even an admin
who already has a market — and therefore clears Barrier 1 — has no affordance to create a
second one; the URL must be typed by hand.

`NewMarketPage` itself is correct (it checks `market_manage` **and** `isPlatformAdmin`,
mirroring the server's two gates). The defect is entirely in reachability.

**Fix:**

```tsx
// 1) frontend/src/app/[locale]/(app)/layout.tsx — exempt the market-creation route,
//    which is the one screen that legitimately runs without a tenant context.
import { usePathname } from "@/i18n/navigation";

const WIZARD_NEW_PATH = "/markets/new";
const pathname = usePathname();
const needsMarket = pathname !== WIZARD_NEW_PATH;

useEffect(() => {
  if (!checked || !principal) return;
  if (principal.mustChangePassword) { router.replace("/change-password"); return; }
  if (needsMarket && principal.marketId === null) router.replace("/select-market");
}, [checked, needsMarket, principal, router]);

const ready = checked && principal !== null
  && !principal.mustChangePassword
  && (!needsMarket || principal.marketId !== null);
```

```tsx
// 2) frontend/src/components/shell/app-shell.tsx — add a permission-gated nav entry.
{ href: "/markets/new", labelKey: "newMarket", icon: Store,
  permission: "market_manage", group: "system" },
```

```tsx
// 3) frontend/src/components/auth/market-picker.tsx — give the empty state a way out.
{options.length === 0 && canCreate ? (
  <Link href="/markets/new">{t("wizard.createFirstMarket")}</Link>
) : null}
```

All three are needed: (1) unblocks the route, (2) makes it discoverable for admins who
already have a market, (3) makes it reachable on a fresh platform. New `labelKey`s must be
added to all three locale files — `frontend/scripts/error-codes.test.mjs` and the locale
parity check will otherwise catch it, which is the correct behaviour.

---

## Warnings

### WR-01: `POST /imports/errors.xlsx` bound is incomplete, and a legitimate 422 can exceed it

**File:** `services/core-api/app/schemas.py:1279-1335`
**Also:** `services/core-api/app/services/xlsx_template.py:242-249`, `services/core-api/app/services/import_validator.py:193-248`

**Issue:** Three related problems in the endpoint whose docstring claims to have solved
the self-DoS (T-02-97).

(a) **Only the list length is bounded.** `ImportErrorItem` declares `row: int`,
`code: str`, `message: str` with no `Field`/`StringConstraints` at all. The
`max_length=IMPORT_ERROR_REPORT_MAX` on the list caps element *count* at 5 000, but each
element can carry a multi-megabyte `message`. `_read_bounded()` protects the *file upload*
path; this JSON path has no equivalent — the docstring's claim that "ortiqcha massiv
umuman xotiraga to'liq yig'ilmaydi" is only true of the count.

(b) **The 5 000 cap is derived from a wrong premise.** `IMPORT_ERROR_REPORT_MAX`'s
docstring reasons: "`xlsx_reader.MAX_ROWS` bilan AYNAN bir xil: bitta fayl eng ko'pi bilan
shuncha qator beradi, ya'ni **har qatorda bittadan xato** bo'lgan holatda ham ro'yxat shu
chegaraga sig'adi." But `validate_stall_rows` emits up to **four** issues for a single
row (`empty_code` + `row_too_short` for zona + `row_too_short` for toifa +
`invalid_status`, lines 195-244 — they accumulate into `row_issues` rather than
short-circuiting, by design). A 5 000-row file of mostly-blank rows produces ~20 000
issues. The 422 response carries all of them (`_reject_if_invalid` sends `errors` in
full), and the client's own round-trip of that array is then rejected with a second 422 —
the user cannot download the report for the error they just received.

(c) **Over-long messages vanish silently.** `xlsx_template._write_text` →
`worksheet.write_string(...)`; XlsxWriter returns `-2` and writes nothing when a string
exceeds Excel's 32 767-character limit. No exception, no log — an empty cell.

**Fix:**

```python
# schemas.py
_ImportCodeStr = Annotated[str, StringConstraints(max_length=64)]
_ImportMessageStr = Annotated[str, StringConstraints(max_length=500)]

class ImportErrorItem(BaseModel):
    row: Annotated[int, Field(ge=0, le=IMPORT_ERROR_REPORT_MAX)]
    code: _ImportCodeStr
    message: _ImportMessageStr

# and raise the list cap to cover the real worst case, or cap it at the source:
IMPORT_ERROR_REPORT_MAX = 25_000  # MAX_ROWS x max issues per row
```

Whichever bound is chosen, add an assertion tying it to
`import_validator`'s per-row issue ceiling so the two cannot drift again. Separately,
check the `write_string` return value in `_write_text` and log when a cell is dropped.

---

### WR-02: `market_activate()` / `market_delete_draft()` carry no tenant predicate; the sole boundary is one application helper

**File:** `migrations/entities/functions.py:945-1041`
**Also:** `services/core-api/app/api/v1/markets.py:141-166`, `services/core-api/app/repositories/market_repo.py:318-360`

**Issue:** I verified the executors' claim (#3) and it holds *today*: `_own_market()`
returns `principal.market_id` rather than the path parameter, `MARKET_MANAGE` is
platform-admin-only, and every call site passes the principal's own market. No current
escalation exists.

But the guarantee is entirely review-dependent. Both functions are `SECURITY DEFINER`,
`GRANT EXECUTE ... TO sbozor_app`, and accept an arbitrary UUID with no internal check:

```sql
market_activate(p_market_id uuid) ... SECURITY DEFINER
  UPDATE public.markets SET is_active = true WHERE id = p_market_id;

market_delete_draft(p_market_id uuid) ... SECURITY DEFINER
  DELETE FROM public.stall_assignments WHERE market_id = p_market_id;
  ... 11 more tables ...
  DELETE FROM public.markets WHERE id = p_market_id;
```

`market_delete_draft` cascades across twelve tables including `vendors`,
`user_market_roles` and `refresh_tokens`. `_own_market()`'s docstring correctly identifies
this as the reason it returns `principal.market_id` — but it also states the consequence
plainly: "`SECURITY DEFINER` funksiya bilan ishlaganda ilova qatlami **YAGONA** tenant
chegarasi." That is a single point of failure guarding a twelve-table cascade delete, in a
codebase whose entire tenancy philosophy (`triggers.py:1-20`, `policies.py:128-153`) is
"the guarantee lives in the DB, the application only produces the readable message."

**Fix:** make the boundary structural. Two lines inside each function:

```sql
-- market_activate / market_rename / market_delete_draft
IF p_market_id IS DISTINCT FROM NULLIF(current_setting('app.market_id', true), '')::uuid THEN
  RAISE EXCEPTION 'market_id does not match the tenant context'
    USING ERRCODE = '42501';
END IF;
```

All three are only ever called from a `TenantSessionDep` transaction where `app.market_id`
is already set, so no call site changes. `market_create()` is correctly exempt — no
context exists at that point. Add a meta-test in `tests/tenancy/test_market_domain_meta.py`
asserting these three function bodies reference `app.market_id`, mirroring the existing
`test_security_definer_functions_pin_search_path` gate.

---

### WR-03: `markets.timezone` is unvalidated and then ignored by every business-day computation

**File:** `services/core-api/app/schemas.py:1188`
**Also:** `migrations/entities/functions.py:894-895`, `packages/sbozor-core/sbozor_core/timeutil.py:32`, `migrations/helpers.py` (`BUSINESS_DATE_EXPR`), `migrations/entities/triggers.py:238,299`

**Issue:**

```python
timezone: Annotated[str, StringConstraints(min_length=1, max_length=64)]
```

No IANA validation, and no `CHECK` constraint on the column either. `"Asia/Tashkennt"`,
`"Mars/Olympus"` or `"'; --"` are all accepted and stored (the value reaches the DB as a
typed bind parameter, so there is no injection — but it is silently wrong data).

More consequentially, the value is **never read by anything that computes a date**:

* `sbozor_core.timeutil.MARKET_TZ = ZoneInfo("Asia/Tashkent")` — module constant
* `BUSINESS_DATE_EXPR` — literal `'Asia/Tashkent'` in the generated column
* `tariff_past_immutable()` / `category_period_past_immutable()` — literal
  `(now() AT TIME ZONE 'Asia/Tashkent')::date`

`GET /api/v1/markets` returns `timezone` per market (`MarketListItem.timezone`), so the
API advertises per-market timezone support that does not exist. Under the project's stated
multi-tenant goal ("bitta kod bazasi, cheksiz bozor"), the first market outside UTC+5
gets wrong `valid_from` gates and wrong `business_date` boundaries with no error anywhere.

The frontend today offers exactly one option (`TIMEZONES = ["Asia/Tashkent"]`,
`market-requisites-form.tsx:48`), which masks the problem — but the field is a free string
on the API, not an enum.

**Fix:** at minimum, validate and constrain to the single supported value so the contract
stops lying:

```python
# schemas.py
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

timezone: Annotated[str, StringConstraints(min_length=1, max_length=64)] = "Asia/Tashkent"

@field_validator("timezone")
@classmethod
def _known_timezone(cls, value: str) -> str:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"noma'lum vaqt mintaqasi: {value!r}") from exc
    return value
```

and record the "single supported zone" limitation explicitly — either as a `CHECK
(timezone = 'Asia/Tashkent')` in a follow-up migration, or as a documented deferred item
naming the three literal sites above that must change together.

---

### WR-04: `stall_code_claim()` is documented as `BEFORE INSERT` in two files and created as `AFTER INSERT`

**File:** `services/core-api/app/services/import_validator.py:40-45`
**Also:** `services/core-api/app/repositories/import_repo.py:148-153`, `migrations/versions/0007_market_domain.py:317-321`, `migrations/entities/triggers.py:202-221`

**Issue:** The DDL is unambiguous:

```python
# 0007_market_domain.py:318-320
"CREATE TRIGGER trg_stall_code_claim "
"AFTER INSERT OR UPDATE OF code ON stalls "
```

and `triggers.py:202-221` documents the `AFTER` choice as a measured necessity plus its
import consequence: "`AFTER` bo'lgani uchun `INSERT ... ON CONFLICT (market_id, code) DO
NOTHING` da konflikt YUZAGA KELGAN qator uchun trigger UMUMAN ishga tushmaydi."

Two other files assert the exact opposite as established fact:

* `import_validator.py:41-42` — "`stall_code_claim()` **`BEFORE INSERT`** triggeri
  `ON CONFLICT DO NOTHING` da HAM ishga tushadi va `23505` bilan BUTUN TRANZAKSIYANI
  yiqitadi."
* `import_repo.py:148-150` — "`stall_code_claim()` **`BEFORE INSERT`** triggeri
  konfliktdan OLDIN ishga tushadi va `ON CONFLICT` bandi uni CHETLAB O'TA OLMAYDI."

This is not cosmetic. Both claims are the stated justification for load-bearing decisions
(the validator's pre-filter of `existing_codes`, and the deliberate absence of
`ON CONFLICT DO NOTHING`). A maintainer trusting either side will reach the wrong
conclusion about whether D-15 idempotency is enforced by the DB or by the validator —
and `triggers.py` says the answer changed.

**Fix:** correct both docstrings to `AFTER INSERT OR UPDATE OF code` and restate the
consequence per `triggers.py:215-221`. Keep the validator's pre-filter and keep
`ON CONFLICT` absent — both remain correct choices — but the recorded reason must match
the trigger that actually exists.

---

### WR-05: Vendor-import duplicate-stall detection keys on the raw file string while lookup is case-insensitive

**File:** `services/core-api/app/services/import_validator.py:346-372`
**Also:** `services/core-api/app/services/import_validator.py:446-486`

**Issue:** `_lookup()` resolves a stall code by exact match first, then falls back to the
casefolded index (`_fold_index`). So `"A1"` and `"a1"` in the same file both resolve to
the *same* `stall_id`. But the in-file duplicate guard keys on the raw string:

```python
stall_id = _lookup(stalls_by_code, stall_index, stall_code)
if stall_id is None:
    ...stall_not_found...
elif stall_code in stall_first_seen:          # ← raw file value, not stall_id
    ...duplicate_code_in_file...
else:
    stall_first_seen[stall_code] = number
```

`"A1"` and `"a1"` are distinct keys, so both rows pass validation, both produce an open
assignment on the same stall, `ex_stall_assignments_no_overlap` fires (`23P01`), and the
user gets `409 import_conflict` with no row number.

That is the exact outcome the comment three lines above says the check exists to prevent:
"Usiz bu holat `ex_stall_assignments_no_overlap` ga urilib, QATOR RAQAMISIZ 409 berardi —
D-14 aynan shuni taqiqlaydi, va bu sotuvchi faylidagi eng ehtimolli xato."

**Fix:**

```python
stall_id = _lookup(stalls_by_code, stall_index, stall_code)
if stall_id is None:
    row_issues.append(ImportIssue(number, "stall_not_found", ...))
elif stall_id in stall_first_seen:            # key on the RESOLVED id
    row_issues.append(
        ImportIssue(
            number,
            "duplicate_code_in_file",
            f"{number}-qator: {stall_code} raqamli rasta "
            f"{stall_first_seen[stall_id]}-qatorda ham biriktirilgan",
        )
    )
else:
    stall_first_seen[stall_id] = number
```

with `stall_first_seen: dict[UUID, int]`. Add a unit test in
`tests/unit/` covering mixed-case codes for the same stall.

---

### WR-06: `calendar_missing` (blocking step 7) can never fire for wizard-created markets

**File:** `frontend/src/components/wizard/market-requisites-form.tsx:177-186`
**Also:** `migrations/entities/functions.py:905`, `services/core-api/app/api/v1/markets.py:219-220`, `services/core-api/app/repositories/market_repo.py:197-199`

**Issue:** `MarketRequisitesForm.onSubmit` builds the create payload without
`open_weekdays`:

```ts
await createMarket.mutateAsync({
  name, timezone, operating_since,
  address, tin, bank_account, bank_mfo, contact_phone,   // no open_weekdays
});
```

`MarketCreateRequest.open_weekdays` defaults to `None`, and `market_create()` coalesces it:

```sql
COALESCE(p_open_weekdays, ARRAY[1,2,3,4,5,6,7]::smallint[])
```

so `array_length(open_weekdays, 1) > 0` is **always true**, `calendar_configured` is
always `True`, and `_blocking()`'s step-7 branch is unreachable on the only code path that
creates markets. The gate survives only for rows inserted by hand or by a seed fixture.

Consequence: a market that is actually closed on, say, Mondays activates advertising
"open every day". Under D-17/D-18 that is the input to daily charge generation in phase 6 —
vendors get billed for a day the market was shut, which is the dispute class this product
exists to prevent. The wizard's step-7 checklist row renders `calendarSet` / "✓" for a
schedule nobody chose.

**Fix:** make the weekday choice explicit in step 1, or make it genuinely blocking:

```sql
-- Option A (preferred): stop defaulting; force the wizard through step 7.
VALUES (v_market_id, p_operating_since, p_open_weekdays, ...)   -- NOT NULL column
```
plus `open_weekdays: _WeekdayList` (required) on `MarketCreateRequest` and a
`<WeekdayPicker>` in `MarketRequisitesForm`.

```ts
// Option B (smaller): keep the default but surface it, so the operator confirms it.
//    Add a WeekdayPicker to step 1 pre-checked with all 7 days and send the value.
```

Either way, add a test asserting `calendar_missing` appears in `blocking[]` for a market
created without a weekday selection — that assertion is currently unwritable, which is
itself the signal.

---

### WR-07: `POST /imports/errors.xlsx` requires `STALL_MANAGE` even for vendor-import errors

**File:** `services/core-api/app/api/v1/imports.py:293-298`

**Issue:**

```python
@router.post("/errors.xlsx")
async def download_error_report(
    payload: ImportErrorReportRequest,
    principal: StallManagerDep,      # ← always STALL_MANAGE
    session: TenantSessionDep,
) -> StreamingResponse:
```

`POST /imports/vendors` requires `VENDOR_MANAGE`. A principal holding only
`VENDOR_MANAGE` can therefore trigger a 422 with 300 row errors and then get **403** when
trying to download the report for it.

The correct pattern already exists three functions above:
`require_template_access` (lines 157-178) branches on `?kind=` and picks
`STALL_MANAGE`/`VENDOR_MANAGE` accordingly, with a docstring explaining exactly why
collapsing the two would violate D-07's separation. That reasoning applies verbatim here
and was not carried over.

Today all roles that hold one hold the other, so this is latent — but D-07 keeps them
separate deliberately, and the matrix is explicitly designed to be extended.

**Fix:** reuse the existing dependency. Add `kind` to `ImportErrorReportRequest` (or accept
it as a query parameter, matching `/template`) and swap `StallManagerDep` for
`TemplateAccessDep`:

```python
@router.post("/errors.xlsx")
async def download_error_report(
    payload: ImportErrorReportRequest,
    principal: TemplateAccessDep,     # ?kind=stalls -> STALL_MANAGE, vendors -> VENDOR_MANAGE
    session: TenantSessionDep,
) -> StreamingResponse:
```

and pass `kind` from `downloadErrorReport()` in `market-queries.ts:959-967`.

---

### WR-08: `_check_zip()` materialises the full `infolist()` before applying the entry-count gate

**File:** `services/core-api/app/services/xlsx_reader.py:264-288`

**Issue:**

```python
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    entries = archive.infolist()          # ← every ZipInfo allocated here

if sum(entry.file_size for entry in entries) > gates.uncompressed_bytes: ...
if len(entries) > gates.zip_entries: ...  # ← gate applied after the allocation
```

`MAX_ZIP_ENTRIES`'s own docstring states its purpose: "millionlab mayya faylli arxiv
metama'lumot bilan xotirani yeydi, garchi ochilgan hajm chegaradan past bo'lsa ham." The
check runs after the very allocation it is meant to prevent.

Bounded honestly: a central-directory record is ≥46 bytes plus filename, so a 5 MB upload
(`MAX_UPLOAD_BYTES`) can declare on the order of 50–100 k entries once local headers are
accounted for, producing tens of MB of `ZipInfo` objects per concurrent request. Not
fatal on an 8–16 GB VPS, but it is a real amplification factor and the gate does not do
what it says.

The rest of the module's ordering discipline is excellent — the `_load()` indirection so
`test_zip_bomb_is_rejected_before_parsing` can assert on call ordering is exactly right.
This one gate is out of order.

**Fix:** read the end-of-central-directory entry count before iterating, or bound the
iteration:

```python
with zipfile.ZipFile(io.BytesIO(raw)) as archive:
    entries: list[zipfile.ZipInfo] = []
    for entry in archive.infolist():
        entries.append(entry)
        if len(entries) > gates.zip_entries:
            log.warning("import_zip_entry_flood", limit=gates.zip_entries)
            raise ImportRejected(_FILE_TOO_COMPLEX)
```

`ZipFile.infolist()` returns an already-built list, so this needs
`archive.NameToInfo`-free iteration or a pre-parse of the EOCD record; the simplest correct
form is to check `len(archive.namelist())` against the gate before touching `infolist()`,
or to cap `MAX_UPLOAD_BYTES` low enough that the worst case is provably bounded and say so
in the docstring instead of claiming a gate that runs too late.

---

### WR-09: A mid-session `password_change_required` renders as "ruxsat yo'q" with no redirect

**File:** `frontend/src/lib/api-client.ts:343-367`
**Also:** `frontend/src/app/[locale]/(app)/layout.tsx:52-62`, `services/core-api/app/deps.py:389-412`

**Issue:** `errorMessageKey()` has no `password_change_required` case, so it falls through:

```ts
if (error.status === 403) return "errors.forbidden";
```

The `(app)` layout's redirect keys off `principal.mustChangePassword`, which lives in the
in-memory store and is only written at login / `restoreSession()`. Nothing refreshes it in
response to a 403.

So when an admin resets a user's password mid-session (`must_change_password` flips to
`true` in the DB, and `invalidate_user_state()` drops the cache immediately), that user's
next request returns `403 password_change_required` — and the UI shows "ruxsat yo'q" on
every screen, forever, with no route to `/change-password`. `deps.py:390-399` documents
403-not-401 as the choice made specifically to avoid a redirect loop; here the absence of
any redirect produces a dead end instead.

`frontend/src/lib/api-types.ts:771` already reserves the `password_change_required` code —
it is listed and unhandled.

**Fix:**

```ts
// api-client.ts — map the code, and let the caller react to it.
export type ErrorMessageKey = ... | "auth.passwordChangeRequired";

case "password_change_required":
  return "auth.passwordChangeRequired";
```

```ts
// api-client.ts::apiRequest — keep the store in sync with the server's verdict.
if (!response.ok) {
  const errorBody = await readErrorBody(response);
  const detail = detailOf(errorBody);
  if (response.status === 401 && !skipAuth) clearSession();
  if (response.status === 403 && detail === "password_change_required") {
    updatePrincipal({ mustChangePassword: true });   // layout redirects on next render
  }
  throw new ApiError(response.status, detail, errorBody);
}
```

Add `auth.passwordChangeRequired` to all three locale files.

---

### WR-10: `useImportMutation` does not invalidate `ASSIGNMENTS_KEY`, but the vendor import writes `stall_assignments`

**File:** `frontend/src/lib/market-queries.ts:900-908`
**Also:** `services/core-api/app/repositories/import_repo.py:223-234`

**Issue:**

```ts
onSuccess: () =>
  invalidate(client, [
    kind === "stalls" ? STALLS_KEY : VENDORS_KEY,
    MAP_KEY, ZONES_KEY, CATEGORIES_KEY, SETUP_STATUS_KEY,
  ]),
```

`ImportRepository.insert_vendors()` writes `stall_assignments` rows for every imported
vendor that carried a stall code. `ASSIGNMENTS_KEY` is not in the list, so a
`GET /stalls/{id}/assignments` panel opened before the import keeps rendering the empty
pre-import history until `staleTime` expires.

The module docstring (lines 46-52) states the invalidation contract precisely — "Rasta
yaratilgandan keyin ro'yxat ham, xarita ham, ustaning to'liqlik holati ham eskiradi; uch
joyni yangilashni komponentga qoldirish 'bir joyda esdan chiqadi' sinfidagi xatoni
KAFOLATLAYDI" — and every other mutation in the file honours it via a named
`*_SIDE_EFFECTS` constant. This one hand-rolls the list and drops a table.

**Fix:**

```ts
const IMPORT_SIDE_EFFECTS = {
  stalls:  [STALLS_KEY, MAP_KEY, ZONES_KEY, CATEGORIES_KEY, SETUP_STATUS_KEY],
  vendors: [VENDORS_KEY, ASSIGNMENTS_KEY, STALLS_KEY, MAP_KEY, SETUP_STATUS_KEY],
} as const;

onSuccess: () => invalidate(client, IMPORT_SIDE_EFFECTS[kind]),
```

(`STALLS_KEY` and `MAP_KEY` belong in the vendor branch too: `has_vendor` and
`vendor_name` on stall rows change when assignments are created.)
`market-queries.test.tsx` already spies on `invalidateQueries` — extend it to cover the
vendor branch.

---

## Info

### IN-01: Header row counts against `MAX_ROWS`, so the effective data limit is 4 999

**File:** `services/core-api/app/services/xlsx_reader.py:331-340`
**Issue:** `seen` is incremented for every row including the header, and `declared_rows`
comes from `max_row` which is also header-inclusive. A file with exactly 5 000 data rows
declares 5 001 and is rejected as `file_too_complex`, contradicting `MAX_ROWS`' own
documentation and `IMPORT_ERROR_REPORT_MAX`'s stated equivalence.
**Fix:** compare `declared_rows - HEADER_ROW > gates.rows` and start `seen` at 0 after the
header is skipped; update `test_default_limits_match_the_documented_values` accordingly.

### IN-02: Two calendar write endpoints build responses from the request payload instead of a read-back

**File:** `services/core-api/app/api/v1/calendar.py:232-235, 265-270`
**Issue:** `PUT /calendar/weekdays` returns `payload.open_weekdays` and
`POST /calendar/exceptions` returns the request's `exception_date` / `is_open` / `note`
rather than the stored row. Every other write path in the phase (`stalls.py::_detail_or_404`,
`vendors.py::_row_or_404`, `tariffs.py::_row_or_404`, `assignments.py::_row_or_404`) routes
its response through the read path with an explicit "javob AYNAN o'qish yo'lidan quriladi"
rationale so clients never see a shape that a subsequent `GET` would contradict.
**Fix:** have `CalendarRepository.add_exception()` return the inserted row (or re-read it)
and build the response from that, matching the established pattern.

### IN-03: `activate.mutateAsync(marketId ?? "")` converts a null market into a malformed URL

**File:** `frontend/src/components/wizard/activation-panel.tsx:273`
**Issue:** With `marketId === null` this issues `POST /api/v1/markets//activate`.
Unreachable today (the panel returns a permanent skeleton because
`useSetupStatusQuery(null)` is `enabled: false` and therefore never leaves `isPending`),
but the `?? ""` turns a programming error into a silently malformed request instead of a
loud failure — and the permanent-skeleton behaviour is itself a hang with no message.
**Fix:** guard explicitly — `if (marketId === null) { setFailure(t("errors.generic")); return; }`
— and render an explanatory state rather than an indefinite skeleton when `marketId` is null.

### IN-04: `tests/tenancy/test_cross_tenant.py` uses the banned `date.today()`

**File:** `tests/tenancy/test_cross_tenant.py:~222`
**Issue:** `_future_date()` calls `date.today()`. Production code correctly bans it
(`timeutil.py:65-90` — the container runs UTC, so 00:00–04:59 Tashkent yields the previous
day). The +30-day margin makes it harmless here, but the tenancy suite is precisely where
the project's own timezone rule should be modelled, and a grep-based gate on `date.today()`
would flag it.
**Fix:** `from sbozor_core.timeutil import business_today` and use
`business_today() + timedelta(days=FUTURE_DAYS)`.

### IN-05: OpenAPI and interactive docs are exposed unconditionally

**File:** `services/core-api/app/main.py:119-125`
**Issue:** `docs_url="/api/docs"`, `openapi_url="/api/openapi.json"` and the default
`/redoc` are enabled with no environment gate, publishing the complete route inventory and
every request/response schema in production. Pre-existing from phase 1 rather than
introduced here, and `EXEMPT_ROUTES` documents them as intentional — but the phase added
43 routes to that surface, including the market-lifecycle and import endpoints.
**Fix:** gate on an environment flag —
`docs_url="/api/docs" if settings.expose_docs else None` (likewise `openapi_url`,
`redoc_url`) — defaulting to off, and update the two `EXEMPT_ROUTES` entries to note the
gate.

---

_Reviewed: 2026-08-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
