---
phase: 06-billing-va-kassir
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 91
files_reviewed_list:
  - frontend/messages/ru.json
  - frontend/messages/uz-Cyrl.json
  - frontend/messages/uz-Latn.json
  - frontend/scripts/billing-copy.test.mjs
  - frontend/scripts/collect-surface.test.mjs
  - frontend/scripts/error-codes.test.mjs
  - frontend/src/app/[locale]/(app)/billing/page.test.tsx
  - frontend/src/app/[locale]/(app)/billing/page.tsx
  - frontend/src/app/[locale]/(app)/collect/page.tsx
  - frontend/src/app/[locale]/(app)/collect/shift/page.tsx
  - frontend/src/components/billing/anomaly-list.tsx
  - frontend/src/components/billing/charge-detail-dialog.test.tsx
  - frontend/src/components/billing/charge-detail-dialog.tsx
  - frontend/src/components/billing/charge-list.tsx
  - frontend/src/components/billing/day-picker.test.tsx
  - frontend/src/components/billing/day-picker.tsx
  - frontend/src/components/billing/pending-summary.tsx
  - frontend/src/components/billing/variance-cell.tsx
  - frontend/src/components/billing/variance-list.test.tsx
  - frontend/src/components/billing/variance-list.tsx
  - frontend/src/components/collect/collect-session.test.tsx
  - frontend/src/components/collect/collect-session.tsx
  - frontend/src/components/collect/payment-bar.test.tsx
  - frontend/src/components/collect/payment-bar.tsx
  - frontend/src/components/collect/payment-row.tsx
  - frontend/src/components/collect/pending-card.test.tsx
  - frontend/src/components/collect/pending-card.tsx
  - frontend/src/components/collect/reason-dialog.test.tsx
  - frontend/src/components/collect/reason-dialog.tsx
  - frontend/src/components/collect/shift-close-form.test.tsx
  - frontend/src/components/collect/shift-close-form.tsx
  - frontend/src/components/collect/shift-open-card.tsx
  - frontend/src/components/collect/stall-lookup.tsx
  - frontend/src/components/shell/app-shell.tsx
  - frontend/src/components/snapshots/alert-row.tsx
  - frontend/src/lib/api-types.ts
  - frontend/src/lib/billing-charge-queries.ts
  - frontend/src/lib/billing-errors.ts
  - frontend/src/lib/billing-pending-queries.ts
  - frontend/src/lib/payment-queries.ts
  - frontend/src/lib/rbac.ts
  - frontend/src/lib/shift-queries.ts
  - migrations/entities/__init__.py
  - migrations/entities/functions.py
  - migrations/entities/triggers.py
  - migrations/versions/0018_occupancy_domain.py
  - migrations/versions/0020_billing_domain.py
  - migrations/versions/0021_market_delete_billing.py
  - migrations/versions/0022_billing_late_review.py
  - packages/sbozor-core/sbozor_core/billing.py
  - packages/sbozor-core/sbozor_core/enums.py
  - packages/sbozor-core/sbozor_core/models/__init__.py
  - packages/sbozor-core/sbozor_core/models/billing.py
  - packages/sbozor-core/sbozor_core/models/occupancy.py
  - packages/sbozor-core/sbozor_core/schema_contract.py
  - services/core-api/app/api/internal/self_check.py
  - services/core-api/app/api/v1/billing.py
  - services/core-api/app/api/v1/payments.py
  - services/core-api/app/api/v1/shifts.py
  - services/core-api/app/jobs/alerting.py
  - services/core-api/app/jobs/billing_close.py
  - services/core-api/app/main.py
  - services/core-api/app/repositories/billing_repo.py
  - services/core-api/app/repositories/payment_repo.py
  - services/core-api/app/repositories/shift_repo.py
  - services/core-api/app/schemas.py
  - services/core-api/app/security/rbac.py
  - services/core-api/app/services/billing_errors.py
  - services/core-api/app/worker.py
  - tests/fixtures/billing_domain.py
  - tests/fixtures/idempotency_probe.py
  - tests/integration/test_alerting.py
  - tests/integration/test_billing_api.py
  - tests/integration/test_billing_close.py
  - tests/integration/test_billing_immutable.py
  - tests/integration/test_billing_repo.py
  - tests/integration/test_market_delete_guard.py
  - tests/integration/test_payments_api.py
  - tests/integration/test_phase6_criteria.py
  - tests/integration/test_shifts_api.py
  - tests/tenancy/test_billing_domain_meta.py
  - tests/tenancy/test_cross_tenant.py
  - tests/tenancy/test_generated_from_column_probe.py
  - tests/tenancy/test_idempotency_concurrency.py
  - tests/tenancy/test_meta.py
  - tests/tenancy/test_occupancy_domain_meta.py
  - tests/tenancy/test_route_coverage.py
  - tests/unit/test_billable_from_slots.py
  - tests/unit/test_payment_credit_rules.py
  - tests/unit/test_rbac_matrix.py
  - tests/unit/test_variance.py
findings:
  critical: 5
  warning: 9
  info: 0
  total: 14
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 91 (in scope; production code under `services/core-api/`, `packages/sbozor-core/`, `migrations/` and `frontend/src/` read in full, tests read as evidence of what is asserted)
**Status:** issues_found

## Summary

The schema layer of this phase is genuinely strong. RLS, composite FKs, the paired
`CHECK` constraints, the immutability triggers and their SQLSTATE split, the
`market_delete_draft()` cascade ordering, the FIFO allocation invariants, and the
`float`/`abs` lint gates all hold up under adversarial reading. I found no SQL
injection (every f-string interpolates only module-level constants; all external
values arrive through typed `bindparam`), no tenant-scoping bypass, no float in a
money path, and no missing `await`.

The defects are concentrated at **layer boundaries** — exactly where this phase's
own tests stop. Five of them are blocking:

1. The only production writer of `charge_adjustments` writes `actor_user_id = NULL`,
   but the response model declares it non-nullable → the director's charge-detail
   route returns **500** the first time a `late_review` adjustment exists (CR-01).
2. The idempotency guarantee (D-21) is evaluated *after* the quote/reason gates,
   and the quote set is derived from state the first request already mutated →
   retrying a debt-inclusive payment returns **422 `reason_required`** instead of
   the original payment (CR-02).
3. The cashier's payment failure block never renders on an actual network drop —
   which is the single scenario the whole idempotency mechanism exists for (CR-03).
4. `GET /billing/pending` sends a **dict** `detail`, which the client's `detailOf()`
   cannot read → the `not-found` state in the cashier's step machine is dead
   code (CR-04).
5. The shift-close confirmation screen (§10.3's "exactly three things") is
   unmounted by its own parent before it can be seen (CR-05).

The pattern behind all five is the same and worth naming: **every one of them is
invisible to the current test suite because the test exercises one side of the
boundary in isolation** (WR-09). The heavy in-file documentation is accurate about
intent, but in four places it asserts a protection that the code does not actually
deliver (CR-03, CR-04, WR-05, WR-07).

---

## Critical Issues

### CR-01: `charge_detail` returns 500 as soon as a system-written adjustment exists

**File:** `services/core-api/app/schemas.py:3140`
(also `services/core-api/app/repositories/billing_repo.py:1664`)

**Issue:**
`ChargeAdjustmentRow.actor_user_id` is declared `UUID` (non-nullable):

```python
adjustment_id: UUID
direction: AdjustmentDirection
amount_soum: int
reason_code: AdjustmentReason
actor_user_id: UUID          # <-- not Optional
created_at: datetime
```

But migration `0022_billing_late_review.py:95-100` deliberately makes the column
nullable, and the **only** producer of `charge_adjustments` in this phase writes
`NULL`:

```python
# billing_repo.py:933  (write_late_review_adjustment)
actor_user_id=None,
```

`billing_close.py::_late_review()` calls that function on every convergent re-run
where a reviewer has since answered "empty". The moment one such row exists,
`GET /api/v1/billing/charges/{charge_id}` raises
`ResponseValidationError` → **500**, and the director's evidence dialog (DL-3, the
product's core-value surface) becomes unopenable for exactly the charges that were
adjusted — i.e. the disputed ones.

The client already anticipates the null; the drift is one-sided:

```ts
// frontend/src/lib/billing-charge-queries.ts:177
actor_user_id: z.uuid().nullable(),
```

`billing_repo.ChargeAdjustmentItem.actor_user_id: UUID` (line 1664) carries the same
wrong annotation — it does not fail at runtime (plain dataclass) but it is what made
the Pydantic model look correct.

**Fix:**
```python
# services/core-api/app/schemas.py
    actor_user_id: UUID | None
    """⛔ `NULL` = TIZIM (0022): `late_review` tuzatishini `billing_close`
       job'i yozadi va unga odam biriktirish YOLG'ON javob bo'lardi."""

# services/core-api/app/repositories/billing_repo.py:1664
    actor_user_id: UUID | None
```
Add an integration assertion that `GET /billing/charges/{id}` returns 200 for a
charge that carries a `late_review` adjustment (see WR-09).

---

### CR-02: Retrying a debt-inclusive payment returns 422, not the original payment (D-21 broken)

**File:** `services/core-api/app/api/v1/payments.py:286-309`

**Issue:**
`create_payment()` recomputes the quote set on every request from live state, and
the idempotency check happens two steps later (step 6). But the first request
**mutates the state the quote set is derived from**: `vendor_outstanding()`
subtracts *all* payments and is deliberately not filtered by `as_of`
(`billing_repo.py:969-973`).

Trace the `[Qarzni ham olish]` flow (tariff 15 000, debt 45 000):

| | outstanding | `payment_quote_set()` | `amount_soum` | result |
|---|---|---|---|---|
| request 1 | 45 000 | `(15000, 45000, 60000)` | 60 000 | in quotes → **201** |
| retry (same key) | **−15 000** | `(15000,)` | 60 000 | not in quotes, `reason_code is None` → **422 `reason_required`** |

The "pay only the outstanding" flow fails the same way: after paying 45 000 the
outstanding is 0, the quote set collapses to `(15000,)`, and 45 000 is no longer a
quote.

Consequences, in order of severity:

* The payment **was** written, but the cashier sees a hard failure. `PaymentBar`
  renders the `reason_required` block with a `[Qayta yuborish]` button that
  re-submits the same key and gets 422 again — an inescapable dead end in the
  money path.
* If the client ever supplied a `reason_code` on the retry, `quote_soum` would be
  `quotes[0]` instead of the original value → different fingerprint → **409
  `idempotency_key_reused`**. Either way the retry is not idempotent.
* This is the exact "tarmoq uzildi" scenario D-21 names, and
  `payments.py:261-266` promises **200 + the same `payment_id`**.

The existing test (`test_payments_api.py:379`) retries only the zero-debt case,
where the quote set happens to be stable — which is why this is green today.

**Fix:** resolve idempotency *before* the pricing gates. Look the key up first and
short-circuit on a fingerprint match:

```python
    # ---- 0-QADAM: takror so'rov PUL QAYTA HISOBLANMASDAN yopiladi (D-21).
    existing = await payment_repo.find_by_key(
        session, market_id=market_id, idempotency_key=payload.idempotency_key
    )
    if existing is not None:
        if existing.request_fingerprint != payment_repo.request_fingerprint(
            stall_id=existing.stall_id,
            service_date=existing.service_date,
            amount_soum=payload.amount_soum,
            quote_soum=existing.quote_soum,   # ⛔ ASL kvota, qayta hisoblanmagan
            method=payload.method,
            override_reason=None if payload.reason_code is None
                            else payload.reason_code.value,
        ):
            raise _reject(IDEMPOTENCY_KEY_REUSED, status.HTTP_409_CONFLICT)
        response.status_code = status.HTTP_200_OK
        return PaymentResponse(...)  # o'sha qator
```

The fingerprint must be compared against the **stored** `quote_soum`, not a freshly
computed one — otherwise the same drift reappears. Add a regression test that
retries `test_paying_the_total_due_needs_no_reason_code` and asserts 200 + the same
`payment_id`.

---

### CR-03: A network drop during payment produces a completely silent UI failure

**File:** `frontend/src/components/collect/payment-bar.tsx:87-89, 192-196`

**Issue:**
```ts
function billingErrorCodeOf(error: unknown): string | null {
  return error instanceof ApiError ? error.detail : null;
}
...
const failureView =
  failureCode === null
    ? null
    : (billingErrorView(failureCode) ?? billingErrorView("network_unreachable"));
```

`api-client.ts` throws `NetworkError` (line 69: `class NetworkError extends Error`)
for transport failures — it is **not** a subclass of `ApiError`. So a real network
drop gives `failureCode === null`, which takes the first branch: `failureView` is
`null`, the error block is not rendered, no `[Qayta yuborish]` button appears, and
no toast fires. The `?? billingErrorView("network_unreachable")` fallback is
reachable *only* for an `ApiError` whose detail is unrecognised — i.e. never for an
actual network error.

Net effect: the cashier taps [Tasdiqlash], the spinner stops, and **nothing else
happens**. The payment may or may not have been written. `collect.retrySafe`,
`collect.errorCause.network_unreachable` and `collect.errorFix.network_unreachable`
exist in all three locales and are dead on this path. This is the precise failure
mode the file's own header calls "KECHIKKAN yolg'on" — a cashier who sees nothing
will re-collect cash.

`payment-bar.test.tsx:291` passes because it injects
`new ApiError(500, "internal_error")`, never a `NetworkError`.

**Fix:**
```ts
const failureView =
  failureCode === null
    ? (failed ? billingErrorView("network_unreachable") : null)
    : (billingErrorView(failureCode) ?? billingErrorView("network_unreachable"));
```
with a `failed` boolean set in `onError` alongside `setFailureCode`. Add a test that
rejects with `new NetworkError(new Error("offline"))` and asserts the retry button
renders with the same idempotency key.

---

### CR-04: `GET /billing/pending` sends a dict `detail`, so the cashier's `not-found` state is unreachable

**File:** `services/core-api/app/api/v1/billing.py:252-255`

**Issue:**
```python
    if not projection.matches:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail={"error_code": STALL_NOT_FOUND}
        )
```

`api-client.ts::detailOf()` reads `detail` **only** when it is a string
(`typeof parsed.data.detail === "string"`), otherwise it returns `""`. So
`ApiError.detail` is `""`, and:

```ts
// collect-session.tsx:185
const notFound = lookupErrorCodeOf(pending.error) === "stall_not_found";  // always false
```

Downstream, `collectState()` can never return `"not-found"`; `StallLookup`'s
`notFound` branch (`stall-lookup.tsx:169-177`) never renders; and because
`pending.isError && !notFound` is now `true`, `PendingCard` shows the generic
`errors.loadFailedTitle` + `[Qayta urinish]` block instead. Every retry re-issues
the same 404 — another dead end. A cashier who mistypes a stall code gets "yuklab
bo'lmadi" instead of "Rasta topilmadi / raqamni qayta kiriting".

`payments.py::_reject()` documents this exact contract and gets it right
(`detail=code` as a bare string); this route and the `_market_id()` helpers do not
(see WR-06).

**Fix:**
```python
    if not projection.matches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=STALL_NOT_FOUND)
```
Assert in `test_billing_api.py` that the 404 body's `detail` is the string
`"stall_not_found"`, and in `collect-session.test.tsx` that a 404 renders the
`stall_not_found` cause/fix pair.

---

### CR-05: The shift-close confirmation screen is unmounted before it can be seen

**File:** `frontend/src/app/[locale]/(app)/collect/shift/page.tsx` (final ternary)
and `frontend/src/lib/shift-queries.ts:313-315`

**Issue:**
```tsx
{closing && openShift !== null ? <ShiftCloseForm onReopen={reopen} shiftId={openShift.id} /> : <ShiftOpenCard onRequestClose={requestClose} />}
```

`useCloseShift()`'s `onSuccess` runs `client.removeQueries({ queryKey: shiftPrefix(marketId) })`,
and `shiftPrefix` is a prefix of `openShiftKey`. The mutation-level `onSuccess`
fires **before** the per-call `onSuccess` that sets `result`, so:

1. `removeQueries` evicts the open-shift query; the active observer resets to
   `data === undefined` and refetches.
2. `openShift = data ?? null` becomes `null`.
3. `closing && openShift !== null` becomes `false` → `ShiftCloseForm` unmounts and
   its local `result` state is destroyed.
4. Even after the refetch resolves it returns `null` (the shift *is* closed), so the
   form never comes back.

The §10.3 result screen — the `data-shift-result` badge, the declared figure, and
`[Yangi smena ochish]` — is therefore unreachable in production. The cashier writes
a financial declaration and is dropped straight back to "open a shift" with only a
toast as evidence. `shift-close-form.test.tsx` renders `ShiftCloseForm` directly, so
it is green.

**Fix:** keep the form mounted for the whole close flow; `openShift` is only needed
to obtain the id, so capture it once:

```tsx
const [closingShiftId, setClosingShiftId] = useState<string | null>(null);
const requestClose = useCallback(() => setClosingShiftId(openShift?.id ?? null), [openShift]);
const reopen = useCallback(() => setClosingShiftId(null), []);
...
{closingShiftId !== null
  ? <ShiftCloseForm onReopen={reopen} shiftId={closingShiftId} />
  : <ShiftOpenCard onRequestClose={requestClose} />}
```
Add a page-level test that closes a shift and asserts the three `data-shift-result`
children survive the query eviction.

---

## Warnings

### WR-01: `no_open_shift` is registered as a 409 but never enforced — and shift-less payments can never be reversed

**File:** `services/core-api/app/services/billing_errors.py:214-220`,
`services/core-api/app/api/v1/payments.py:313-316`

**Issue:** The registry entry states the rule explicitly — *"To'lov yozish uchun
ochiq smena yo'q (**409**) … ochiq smenasiz yozilgan to'lov keyin hech qaysi ko'r
deklaratsiyaga tushmasdi va variance o'z maxrajini yo'qotardi."* No route ever
raises it; `create_payment()` simply writes `shift_id = NULL`
(`test_payments_api.py:994` locks this in).

The stated justification for the nullable column is OQ-6/A5 — "direktor smenasiz
kiritishi mumkin" — but `PAYMENT_CREATE` is **cashier-only** (`rbac.py:287-293`;
the director row explicitly omits it). So that path is unreachable through the API,
and *every* shift-less payment in practice is a cashier's payment that escapes the
blind-declaration/variance mechanism entirely.

Second-order consequence, not documented anywhere: such a payment is
**permanently unreversible**. `reverse_payment` requires
`owner.shift_id == shift_id` where `shift_id` is the requester's *open* shift
(`payments.py:429`); `None != <uuid>` is always true → 403. `payments` is
append-only and phase 6 builds no other reversal surface, so a wrong-stall payment
recorded without an open shift can never be corrected.

**Fix:** either enforce the documented rule —
```python
    shift_id = await payment_repo.open_shift_id(session, market_id=market_id,
                                                cashier_id=principal.user_id)
    if shift_id is None:
        raise _reject(NO_OPEN_SHIFT, status.HTTP_409_CONFLICT)
```
(the frontend already gates on `no-shift`, so this closes the DevTools/curl path) —
or, if shift-less payments must stay legal, delete `NO_OPEN_SHIFT` from the registry
and document the reversal dead-end. The current state is the worst of both: a
declared control that isn't applied.

### WR-02: Market-level `outstanding_soum` nets one vendor's advance against another's debt

**File:** `services/core-api/app/repositories/billing_repo.py:1412, 1417`

**Issue:**
```python
    balances = await vendor_outstanding(session, market_id=market_id, as_of=as_of)
    ...
    outstanding_soum=sum(balances.values()),
```
`vendor_outstanding()` returns *signed* per-vendor balances and deliberately allows
negatives (advance payments, OQ-4/A4). Summing them makes an overpaying vendor
cancel out a debtor: a market where vendor A owes 500 000 and vendor B has paid
500 000 in advance reports `outstanding_soum = 0` on the director's §9.5 panel.
The debt is understated by the total advance across the market, silently.

`charge_list()` avoids this by reporting per-vendor balances in each row; only the
market aggregate collapses them.

**Fix:** decide and name the aggregate. If §9.5 means "money owed", clamp per
vendor before summing (`sum(max(v, 0) for v in balances.values())`) and expose the
advance separately, or keep the signed sum but rename it (`net_balance_soum`) so it
cannot be read as debt. Whichever is chosen, assert it in
`test_billing_repo.py` with one debtor and one advance-holder.

### WR-03: `billing_close` anomaly counters count attempts, not writes

**File:** `services/core-api/app/jobs/billing_close.py:437, 468, 548`

**Issue:** `write_anomaly()` returns `None` on conflict (job re-run) and
`_write_anomaly_with_evidence()` returns early after appending an error when no
winning event exists. All three counters increment unconditionally anyway:

```python
        await write_anomaly(..., kind=AnomalyKind.NO_COVERAGE_STALL, ...)
        result.anomalies_no_coverage += 1          # yozildimi — tekshirilmaydi
```

The job is explicitly convergent ("qayta yugurish NORMAL holat"), so on the second
run of the same day every anomaly is counted again. `charged` gets this right
(`if charge_id is None: skipped_existing += 1`). The numbers land in
`system_heartbeats.detail`, which `/internal/self-check` and the daily digest read —
so the phase's only external observability for BILL-04 over-reports.

**Fix:**
```python
        anomaly_id = await write_anomaly(...)
        if anomaly_id is not None:
            result.anomalies_no_coverage += 1
```
and have `_write_anomaly_with_evidence()` return `bool`/`UUID | None` so callers can
do the same for `anomalies_unassigned` / `anomalies_closed_day`.

### WR-04: The phase's two money inputs use two different, non-equivalent parsers

**File:** `frontend/src/components/collect/reason-dialog.tsx:88-92` vs
`frontend/src/components/collect/shift-close-form.tsx:113-120`

**Issue:** `parseDeclaredSoum()` is strict and documents why:
```ts
  if (!/^\d+$/.test(trimmed)) return null;   // ⛔ filtrlab tashlash YARAMAYDI
```
`parseAmount()` on the override dialog — the input that directly determines
`payments.amount_soum` — uses bare `Number()`:
```ts
function parseAmount(raw: string): number | null {
  const value = Number(raw);
  if (!Number.isInteger(value) || value <= 0) return null;
```
This accepts `"1e5"` → 100 000, `"0x10"` → 16, `" 15000 "` → 15 000 and
`"+15000"` → 15 000. None of these are what a cashier meant to type, and the
override path is by design the *only* place a cashier can name an arbitrary sum.
Two contradictory validation rules for the same domain concept in the same phase is
also exactly the "ikki haqiqat manbai" class this codebase polices elsewhere.

**Fix:** reuse the strict form (extract it once, e.g. `parsePositiveSoum` in
`api-types.ts`, and have both call sites use it with `>= 0` / `> 0` as the only
difference).

### WR-05: `matchesRequestedCode` is computed, exported and documented as a protection layer — but no caller reads it

**File:** `frontend/src/lib/billing-pending-queries.ts:222-253, 315-320`

**Issue:** The hook docstring claims:
> "⛔ MOSLIK SHARTI KESH SIYOSATIDAN MUSTAQIL (§9.4, 2-qatlam). `select` har javobga
> `matchesRequestedCode` ni HOSIL QILADI: summa FAQAT `data.stall_code === stallCode`
> bo'lganda chizilishi mumkin."

`CollectSession` destructures `matches` and `stall` from the query result and never
touches `matchesRequestedCode` (`collect-session.tsx:182-184`). `PendingCard`
independently re-derives `pending.stall_code === enteredCode` (`pending-card.tsx:100`),
which is what actually enforces §9.4 — and it guards only the *card*, not
`PaymentBar`, which is rendered on `stall !== null` alone.

Today this is safe because the query key includes `stallCode` and `gcTime: 0`
prevents cross-code cache reuse, so `stall` cannot belong to another code. But the
documented "layer 2" does not exist in the render path, and the exported field is
dead — a future reader will trust the comment.

**Fix:** either consume it (`{stall !== null && lookup.matchesRequestedCode ? <PaymentBar .../> : null}`)
or delete the field and correct the docstring to say the guarantee comes from the
query key plus `PendingCard`'s own comparison.

### WR-06: `_market_id()` raises 403 with a dict `detail` in all three new routers

**File:** `services/core-api/app/api/v1/billing.py:141-143`,
`services/core-api/app/api/v1/payments.py:168-170`,
`services/core-api/app/api/v1/shifts.py:173-175`

**Issue:** Same defect class as CR-04, three more instances:
```python
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail={"error_code": "market_not_selected"}
        )
```
`detailOf()` returns `""` for a dict, so the client falls through to
`errors.generic`. All three files carry a `_reject()` helper whose docstring
explains precisely why `detail` must be a string, and then bypass it here. The
comments call the path "unreachable in the client flow" — CR-04 is the proof that
this reasoning is not reliable, and `market_not_selected` *is* in the
`ERROR_CODES` mirror, so it is expected to be recognisable.

**Fix:** `raise _reject("market_not_selected", status.HTTP_403_FORBIDDEN)` in all
three, and add an assertion in `test_route_coverage.py` that every `HTTPException`
raised by the phase's routers uses a `str` detail.

### WR-07: `shift_report` groups by shift *open* day while claiming to group by cash-count day

**File:** `services/core-api/app/repositories/shift_repo.py:441-472`

**Issue:** The query filters `cashier_shifts.business_date = :day`, and
`business_date` is `GENERATED ALWAYS AS (BUSINESS_DATE_EXPR)` over `created_at` —
i.e. the moment the shift row was **inserted** (opened). The docstring asserts the
opposite:
> "⛔ **KUN — `business_date`, `service_date` EMAS** (C-2). Savol «qaysi kunda kassa
> hisobi olindi»…"

A shift opened before Asia/Tashkent midnight and closed after it is reported under
the opening day, while its payments are split across two `payments.business_date`
values by their own `created_at`. `_SHIFTLESS_PAYMENTS` in the same function *does*
filter on `payments.business_date`, so the two halves of one report row already use
different day definitions.

Practical exposure is low (markets close in the evening), but nothing in the schema
or the code enforces that, and the comment will mislead the next reader.

**Fix:** either filter on the closing day —
`(closed_at AT TIME ZONE 'Asia/Tashkent')::date = :day`, which matches the stated
intent and the `status = :closed` filter already applied — or correct the docstring
to say "smena OCHILGAN kun" and state the overnight caveat explicitly.

### WR-08: Two of the fourteen registered billing error codes can never be returned

**File:** `services/core-api/app/services/billing_errors.py:214, 243`

**Issue:** `no_open_shift` (see WR-01) and `charge_immutable` are both in
`SERVER_BILLING_ERROR_CODES`, mirrored in `frontend/src/lib/billing-errors.ts`, and
carry `errorCause`/`errorFix` pairs in all three locales. No route raises either —
there is no charge-mutating endpoint at all in phase 6, so `charge_immutable` (a
`P0001` trigger violation, which would surface as a 500 anyway, not a 409) has no
producer.

This matters because `frontend/scripts/error-codes.test.mjs` gates on the **count**
(14) and on locale coverage. That gate therefore proves nothing about reachability:
a code can be added, translated, mirrored, and still be unreachable — which is
exactly what happened twice here.

**Fix:** raise `NO_OPEN_SHIFT` (WR-01) and either wire `charge_immutable` to a real
handler for `P0001` from `charge_immutable()` or move it to a
`FUTURE_ERROR_CODES` set excluded from `SERVER_BILLING_ERROR_CODES`. Consider
extending the route-coverage test to assert every code in
`SERVER_BILLING_ERROR_CODES` appears in at least one `raise` in `app/api/v1/`.

### WR-09: Three load-bearing claims are asserted only on one side of the boundary

**Files:** `tests/integration/test_billing_api.py:670-702`,
`tests/integration/test_payments_api.py:379-397`,
`frontend/src/components/collect/shift-close-form.test.tsx`

**Issue:** Each of CR-01, CR-02 and CR-05 is a boundary defect that the existing
test asserts *around*:

* `test_the_charge_detail_never_declares_the_tariff_id` asserts
  `body["adjustments"] == []`. No test ever serialises a charge that **has** an
  adjustment, so the non-nullable `actor_user_id` (CR-01) is never exercised. The
  only fixture that inserts an adjustment (`test_billing_repo.py:1200-1229`) passes
  a real `admin_user_id` — the opposite of what production writes.
* `test_the_same_key_twice_writes_one_row_and_returns_the_same_payment` retries only
  the zero-debt case, where the quote set is coincidentally stable. The two
  debt-inclusive tests (`test_paying_the_total_due_needs_no_reason_code`,
  `test_paying_only_the_outstanding_needs_no_reason_code`) never retry (CR-02).
* `shift-close-form.test.tsx` renders the component directly, so the parent's
  unmount (CR-05) is invisible. There is no `shift/page.test.tsx`.

**Fix:** add the three assertions named in CR-01, CR-02 and CR-05. All three are
cheap and each converts a currently-silent production failure into a red test.

---

_Reviewed: 2026-08-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
