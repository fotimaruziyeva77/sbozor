---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
verified: 2026-08-01T12:00:00Z
status: gaps_found
score: 4/8 must-haves verified
overrides_applied: 0
gaps:
  - truth: "SC#1 — Platforma admini ustadan o'tib yangi bozor yaratadi (rekvizit → zona → rasta → toifa → tarif) va oxirida bozor ishlashga tayyor holatda ko'rinadi — kod yozilmaydi"
    status: failed
    reason: "Server tomoni va usta ekranlari to'liq ishlaydi va sabotaj bilan sinalgan (test_wizard_flow.py, test_sc1), LEKIN mahsulot BIRORTA yo'l bilan foydalanuvchini ustaga olib bormaydi: bozori yo'q platforma admini murojaat qilganda mahsulot uni to'xtaydigan tor yo'lga (faqat 'chiqish') haydaydi, mavjud bozorli admin uchun ham menyuda havola yo'q. Bu 02-16/02-17 SUMMARY'larida ochiq qarz sifatida o'z-o'zidan e'tirof etilgan va 02-REVIEW.md da CR-03 sifatida tasdiqlangan."
    artifacts:
      - path: "frontend/src/app/[locale]/(app)/layout.tsx"
        issue: "51-61-qatorlar: `principal.marketId === null` bo'lsa SO'ZSIZ `/select-market` ga yo'naltiradi — `/markets/new` uchun istisno yo'q"
      - path: "frontend/src/components/auth/market-picker.tsx"
        issue: "138-152-qatorlar: bo'sh ro'yxat holatida faqat 'chiqish' tugmasi; `/markets/new` ga havola yo'q"
      - path: "frontend/src/components/shell/app-shell.tsx"
        issue: "`NAV_ITEMS` (84-134-qatorlar) da `/markets/new` yozuvi umuman yo'q — hech bir rol uchun"
    missing:
      - "`(app)/layout.tsx` da `/markets/new` marshrutini `marketId`-talab qiluvchi redirectdan ozod qilish"
      - "`app-shell.tsx` ga `market_manage`-himoyalangan `/markets/new` navigatsiya yozuvi qo'shish"
      - "`market-picker.tsx` bo'sh holatiga 'birinchi bozor yaratish' havolasini qo'shish"
      - "Tuzatilgandan keyin 02-VALIDATION.md Manual-Only #2 (foydalanuvchanlik kuzatuvi) ni qayta o'tkazish"
  - truth: "Karmananing real rasta/tarif/sotuvchi ma'lumoti tizimda yashaydi (ROADMAP Phase 2 maqsad jumlasining ikkinchi yarmi + Note: 'Karmananing real ma'lumoti aynan shu fazada kiritiladi')"
    status: failed
    reason: "Bozor ma'muriyatidan beshta manba hujjatning birortasi ham topshirilmagan; tizimda bironta real rasta, tarif yoki sotuvchi yozuvi yo'q. Import yo'li faqat o'z-o'ziga qaytadigan shablon fayli bilan sinalgan, real ma'lumot bilan emas. Bu ijrochining o'zi tomonidan ochiq e'tirof etilgan (`nyquist_compliant: false`)."
    artifacts:
      - path: ".planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-VALIDATION.md"
        issue: "frontmatter `nyquist_compliant: false`; 'Manual-Only Verifications' jadvalining 4/4 bandi BAJARILMAGAN"
      - path: "ops/data/karmana/README.md"
        issue: "Yo'l qurilgan va hujjatlashtirilgan, lekin real Karmana fayli bilan hech qachon ishlatilmagan"
    missing:
      - "Bozor ma'muriyatidan `ops/data/karmana/README.md` §1 dagi beshta hujjatni olish"
      - "`scripts/karmana-import.mjs` orqali real faylni yuklash va README §7 tekshiruv ro'yxati bilan solishtirish"
  - truth: "Klient tomonidagi ma'lumot bozor almashtirilganda yoki chiqishda boshqa bozorga sizib chiqmaydi (CLAUDE.md: 'hamma jadvalda market_id')"
    status: failed
    reason: "React Query kesh kalitlari `market_id` ni olib yurmaydi va sessiya identifikatori o'zgarganda (bozor almashtirish yoki logout) kesh hech qachon tozalanmaydi — bu 02-REVIEW.md da CR-01 sifatida qayd etilgan va birorta SUMMARY tomonidan o'z-o'zidan e'tirof etilmagan (ya'ni tekshirilmagan qolgan)."
    artifacts:
      - path: "frontend/src/lib/market-queries.ts"
        issue: "89-97-qatorlar: `ZONES_KEY`/`STALLS_KEY`/`VENDORS_KEY`/`CALENDAR_KEY`/`ASSIGNMENTS_KEY` — hech biri `market_id` ni o'z ichiga olmaydi"
      - path: "frontend/src/lib/auth-store.ts"
        issue: "`applySession()`/`clearSession()` `queryClient.clear()`/`removeQueries()`/`resetQueries()` ni hech qachon chaqirmaydi (repo bo'yicha qidiruv 0 natija berdi, testlardan tashqari)"
    missing:
      - "Har bir domen so'rov kalitini `market_id` bilan doiralash"
      - "Bozor almashtirilganda va logout'da kesh to'liq tozalanishi (`queryClient.clear()`)"
  - truth: "Shaxsiy ma'lumotni O'QISH ham auditda ko'rinadi (1-faza D-09 qarori: 'shaxsiy ma'lumot O'QISHI ham auditda'; CLAUDE.md: 'audit jurnali majburiy')"
    status: failed
    reason: "`GET /stalls`, `GET /stalls/{id}` (telefon qaytaradi) va `GET /stalls/{id}/assignments` (sotuvchi F.I.Sh. tarixi) faqat `MARKET_DATA_VIEW` ostida ishlaydi va `audit_read(...)` bog'liqligi YO'Q — holbuki `MARKET_DATA_VIEW` ning o'z docstringi 'shaxsiy ma'lumotni QAMRAMAYDI' deydi. Aynan shu marshrutlar uchun yozilgan audit konstantalari mavjud, lekin hech qayerda ishlatilmaydi. 02-REVIEW.md da CR-02 sifatida tasdiqlangan."
    artifacts:
      - path: "services/core-api/app/api/v1/stalls.py"
        issue: "`list_stalls` (239-qator) va `get_stall` (303-qator, `phone` qaytaradi) faqat `MarketDataViewerDep` ishlatadi"
      - path: "services/core-api/app/api/v1/assignments.py"
        issue: "`list_stall_assignments` (318-qator) faqat `MarketDataViewerDep` ishlatadi; sotuvchi nomi tarixini qaytaradi"
      - path: "services/core-api/app/security/audit.py"
        issue: "`TABLE_STALLS`, `TABLE_TARIFFS`, `TABLE_MARKET_PROFILE` (91-100-qatorlar) e'lon qilingan, lekin o'z ta'riflaridan tashqari hech qayerda ishlatilmaydi"
    missing:
      - "Uchala marshrutga `Depends(audit_read(TABLE_STALLS, ...))` qo'shish (yoki `MARKET_DATA_VIEW` ustiga `VENDOR_VIEW` ni ham talab qilish)"
      - "`MARKET_DATA_VIEW`/`VENDOR_VIEW` chegarasini docstring va kodda mos qilib aniq belgilash"
---

# Phase 2: Bozor domeni va "Yangi bozor" ustasi — Verification Report

**Phase Goal:** Platforma admini kod yozmasdan yangi bozorni tizimga kiritadi va Karmananing real rasta/tarif/sotuvchi ma'lumoti tizimda yashaydi
**Verified:** 2026-08-01
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

**Adversarial starting hypothesis applied:** all 17 plans are marked complete, 890 backend + 94 frontend tests pass, and code review's own summary confirms the server-side tenant story is "genuinely strong." Despite this, the phase goal is not achieved — both halves of the goal sentence, and two cross-cutting hard constraints from CLAUDE.md, fail independent verification below. Task completion is real; goal achievement is not.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC#1 — Admin builds a market through the wizard without code, ends with an active market | ✗ FAILED | Wizard works once reached (`test_wizard_flow.py`, 24 tests; `test_sc1_...` in `test_phase2_criteria.py`), but is **unreachable** for a platform admin with zero markets and has no nav entry for admins who already have one. CR-03. |
| 2 | Karmana's real stall/tariff/vendor data lives in the system (goal 2nd clause, ROADMAP Note) | ✗ FAILED | `02-VALIDATION.md` frontmatter `nyquist_compliant: false`; zero real records loaded; only a self-referential template round-trip was exercised. |
| 3 | SC#2 — Registry changes (status/category/assignment) are all audited | ✓ VERIFIED | `test_sc2_registry_changes_are_audited` passes, sabotage-tested (removing `fn_audit_row()` diff logic fails exactly this test). Write-path audit is real. *(See truth 8 for an adjacent, unresolved read-audit gap on the same routes.)* |
| 4 | SC#3 — Tariff change preserves the old price for past dates | ✓ VERIFIED | `test_sc3_past_charges_keep_the_old_price` sabotage-tested (removing `window.is_draft` from `is_valid_from_allowed` fails exactly this test); `tests/integration/test_tariff_history.py` (447 lines) DB-level proof. |
| 5 | SC#4 — Admin marks a holiday/non-working day and no charge basis exists for it | ✓ VERIFIED (mechanism); ⚠ WARNING on default path | `market_is_open()` fail-closed function (`migrations/versions/0010_calendar.py`), sabotage-tested. Caveat: the wizard never submits `open_weekdays` (`grep` for the string in `market-requisites-form.tsx` returns zero matches), so every market defaults to "open every day" unless the admin separately visits the calendar screen — WR-06 in `02-REVIEW.md`. |
| 6 | SC#5 — Schematic plan-map groups stalls by zone in a grid; clicking a stall opens its card | ✓ VERIFIED | `frontend/src/components/stalls/stall-map.tsx` (346 lines) + `stall-map.test.tsx` (365 lines); `test_sc5_map_groups_stalls_by_zone_in_code_order` sabotage-tested twice (ordering, `has_vendor` computation). |
| 7 | Client-side cache stays tenant-scoped across market switch / logout (CLAUDE.md: every table carries `market_id`) | ✗ FAILED | Query keys carry no `market_id`; cache never cleared on session-identity change. CR-01, not self-reported by any SUMMARY. |
| 8 | Personal-data reads are audited (D-09; CLAUDE.md: "audit jurnali majburiy") | ✗ FAILED | Three stall/assignment routes return vendor name/phone under `MARKET_DATA_VIEW` with no `audit_read` wiring; the audit constants written for exactly these routes are unused. CR-02. |

**Score:** 4/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/app/[locale]/(app)/markets/new/page.tsx` | Wizard step 1 entry point | ⚠️ ORPHANED | Exists, functional, permission-gated correctly — but not reachable from any in-product navigation for its primary bootstrap audience |
| `frontend/src/app/[locale]/(app)/layout.tsx` | Route guard | ✗ Gap source | Unconditional `marketId === null → /select-market` redirect has no exemption for the wizard route |
| `frontend/src/components/shell/app-shell.tsx` | Nav shell | ✗ Gap source | `NAV_ITEMS` has no `/markets/new` entry |
| `frontend/src/components/wizard/wizard-shell.tsx`, `wizard-stepper.tsx`, `activation-panel.tsx` | Wizard steps 2-7 UI | ✓ VERIFIED | Substantive, wired to `useSetupStatusQuery`, sabotage-tested in 02-16 |
| `services/core-api/app/repositories/market_repo.py`, `app/api/v1/markets.py` | Wizard server API | ✓ VERIFIED | Substantive, wired, sabotage-tested (6 sabotages in 02-11) |
| `services/core-api/app/api/v1/stalls.py`, `assignments.py` | Registry API | ⚠️ Partially wired | Permission-gated correctly; NOT wired to `audit_read` for personal-data-bearing responses |
| `services/core-api/app/security/audit.py` | Read-audit registry | ⚠️ ORPHANED constants | `TABLE_STALLS`/`TABLE_TARIFFS`/`TABLE_MARKET_PROFILE` declared, never consumed |
| `frontend/src/lib/market-queries.ts` | Domain query hooks | ⚠️ Partially wired | Functional CRUD hooks; query keys not tenant-scoped |
| `migrations/versions/0007-0010` | Domain schema | ✓ VERIFIED | Present on disk, sequential, `alembic_version` confirmed at `0010` |
| `tests/integration/test_phase2_criteria.py` | Phase-criteria regression gate | ✓ VERIFIED | 5 tests, one per SC, each docstring carries the literal ROADMAP sentence |
| `ops/data/karmana/README.md`, `scripts/karmana-import.mjs` | Real-data import path | ⚠️ HOLLOW (Level 4) | Pipeline built, documented, and live-exercised (8 scenarios) — but never carried real Karmana data |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `(app)/layout.tsx` | `/markets/new` | route exemption | ✗ NOT_WIRED | No exemption exists; route inherits the blanket redirect |
| `app-shell.tsx` `NAV_ITEMS` | `/markets/new` | nav entry | ✗ NOT_WIRED | Entry absent for all roles |
| `market-picker.tsx` empty state | `/markets/new` | `<Link>` | ✗ NOT_WIRED | Only a logout button renders |
| `stalls.py` (`list_stalls`, `get_stall`) | `security/audit.py::audit_read` | `Depends(...)` | ✗ NOT_WIRED | Only `MarketDataViewerDep` present |
| `assignments.py::list_stall_assignments` | `security/audit.py::audit_read` | `Depends(...)` | ✗ NOT_WIRED | Same gap, vendor-name history |
| `market-queries.ts` query keys | `market_id` | key composition | ✗ NOT_WIRED | Keys are global (`["stalls"]`, not `["m", marketId, "stalls"]`) |
| `auth-store.ts` `applySession`/`clearSession` | `QueryClient` | `.clear()` | ✗ NOT_WIRED | Zero call sites outside tests |
| `market-requisites-form.tsx` | `open_weekdays` | form field → API param | ✗ NOT_WIRED | Field never collected or sent (WR-06) |
| `wizard-shell.tsx` | `GET /markets/{id}/setup-status` | `useSetupStatusQuery` | ✓ WIRED | Confirmed via 02-16 interfaces + sabotage tests |
| `scripts/karmana-import.mjs` | `POST /api/v1/imports/stalls` | multipart upload | ✓ WIRED (mechanically) | 8 live scenarios measured (template, insert, D-15 re-import skip, 422, missing-env) — but never fed real data |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `stall-map.tsx` grid | `zones`/stall cells | `GET /stalls/map` | Yes — joined query, sabotage-tested against ordering and `has_vendor` computation | ✓ FLOWING |
| `activation-panel.tsx` checklist | `setup-status` counts | `GET /markets/{id}/setup-status` (fail-closed CTE) | Yes — computed aggregate, not hardcoded | ✓ FLOWING |
| `ops/data/karmana/*` import pipeline | Karmana stall/tariff/vendor rows | Market administration's real files | **No** — only a self-generated template was ever uploaded | ✗ DISCONNECTED |

### Behavioral Spot-Checks

Not executed as live HTTP/process checks — no running instance was started for this verification (per workflow guidance: grep/file checks over running the app). Instead, claims were falsified/confirmed via direct source reads and independent greps (see Key Link Verification and Truths evidence above), all of which matched the SUMMARY/REVIEW claims exactly on every item spot-checked (CR-01, CR-02, CR-03, WR-06, migration file sequence, `test_phase2_criteria.py` test count/names, `market_is_open()` existence, `stall-map.tsx` substance).

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `test_phase2_criteria.py` contains exactly 5 SC-tests | `grep -c "async def test_"` | 5 (`test_sc1`...`test_sc5`) | ✓ PASS |
| Migration chain 0001-0010 present, no gaps | `ls migrations/versions` | 0001...0010, sequential | ✓ PASS |
| `market_is_open()` exists and is fail-closed | `grep` in `functions.py` / `0010_calendar.py` | Present, `COALESCE(...,false)` documented | ✓ PASS |
| Full `npm run gate` (890 backend + 94 frontend) | *(not re-run)* | Self-reported green 2026-08-01, 403s | ? SKIP — not independently re-executed; would require bringing up Docker services |

### Probe Execution

No `scripts/*/tests/probe-*.sh` files found and none declared in any PLAN/SUMMARY for this phase.

Step 7c: SKIPPED (no runnable probes for this phase).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| MARKET-01 | 02-01, 02-02, 02-11, 02-16 | Usta orqali bozor yaratish | ✗ BLOCKED | CR-03 — wizard unreachable for the primary bootstrap case |
| MARKET-02 | 02-01, 02-02, 02-08, 02-14 | Rasta reestri (holat/toifa/sotuvchi) | ✓ SATISFIED | Registry CRUD + write-audit sabotage-tested (SC#2); no blocker against registry management itself |
| MARKET-03 | 02-01, 02-07, 02-09, 02-15 | Tarixiy tarif | ✓ SATISFIED | SC#3 sabotage-tested, no review findings against it |
| MARKET-04 | 02-01, 02-07, 02-10, 02-15 | Sotuvchi reestri (F.I.Sh., telefon) + biriktirish | ✗ BLOCKED | CR-02 — the requirement's own subject matter (vendor name/phone) is exposed via stalls routes with no read audit |
| MARKET-05 | 02-06, 02-07, 02-09, 02-15 | Ish kunlari / bayram | ✓ SATISFIED (⚠ WARNING) | SC#4 mechanism sabotage-tested; WR-06 default-schedule gap noted, does not falsify the literal requirement |
| MARKET-06 | 02-02, 02-08, 02-14 | Sxematik plan-xarita | ✓ SATISFIED | SC#5 sabotage-tested, `stall-map.tsx`/test substantive |

**Orphaned requirements:** none — all 6 MARKET-IDs appear in at least one plan's `requirements:` frontmatter field, matching REQUIREMENTS.md's Phase 2 mapping.

**Traceability ruling (REQUIREMENTS.md):** No plan checked any MARKET-0X box in `REQUIREMENTS.md`, and 02-01/02-11 documented this as deliberate (marking early would have made the traceability table lie, since 16 later plans still claimed the same IDs). Independent verification confirms this caution was correct, and for a stronger reason than the originally-cited process one: `REQUIREMENTS.md`'s current "Pending" state for **all six** MARKET requirements should **remain unmarked**. MARKET-01 is genuinely blocked (CR-03) and MARKET-04 is genuinely blocked (CR-02, which concerns the exact personal-data fields MARKET-04 names). MARKET-02/03/05/06 have strong code + sabotage-test evidence and would likely clear on a narrow re-verification, but marking a subset complete while `02-VALIDATION.md` itself withholds sign-off (`nyquist_compliant: false`) would fragment a currently-honest record. Recommendation: leave all six `Pending` until a closure plan resolves CR-01/02/03 and real Karmana data is loaded (or the milestone owner explicitly overrides the real-data clause); re-verify MARKET-02/03/05/06 with a light regression pass at that point since no new evidence is expected to change their status.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/wizard/market-requisites-form.tsx` | n/a | Missing field wiring — `open_weekdays` never collected/sent | ⚠️ Warning | WR-06: `calendar_missing` blocking check can never fire on the wizard path; every market defaults to "open every day" |
| — | — | Debt-marker scan (`TBD`/`FIXME`/`XXX`) across all phase-touched backend/frontend/scripts/ops files | ℹ️ Info | Clean — the only `XXX` hits are phone-format placeholders (`+998XXXXXXXXX`), not debt markers |
| — | — | `TODO`/`HACK`/`PLACEHOLDER` scan across wizard/import/stalls/scripts | ℹ️ Info | Clean — only hit is the intentional, documented `CAMERA_PLACEHOLDER` constant (deliberate non-step design per D-16, not a stub) |

No `🛑 Blocker`-classified debt markers found. The four BLOCKER findings in this report (Observable Truths #1, #2, #7, #8) are architectural/wiring gaps, not marker-based debt.

### Gaps Summary

Four must-haves fail independent verification, and none are addressed by a later milestone phase (checked Phases 3-8: none mention wizard reachability, client cache scoping, personal-data read audit, or Karmana data loading — see Step 9b reasoning, no deferrals apply):

1. **SC#1 (wizard reachability) — CR-03.** The wizard is fully built and passes 24+ sabotage-verified tests once reached, but the product has no path into it for a platform admin bootstrapping their first market, and no menu entry for subsequent markets. This is not a polish gap — per the code review, "it is the feature not shipping." Self-reported as open debt in both 02-16-SUMMARY.md and 02-17-SUMMARY.md, explicitly left out of scope by both.
2. **Real Karmana data — goal clause 2 / ROADMAP Note.** Zero real stall/tariff/vendor records exist in the system. The import mechanism is built, documented, and live-exercised, but the market administration never supplied the five source documents. Self-admitted (`nyquist_compliant: false`).
3. **Client-side tenant cache boundary — CR-01.** Not self-reported by any executor; found independently by code review and confirmed here by direct grep. Server-side RLS remains intact (no cross-tenant write/read bypass at the DB layer), but the browser can render a previous market's zones/stalls/vendor names+phones after a market switch or user switch within the same tab.
4. **Personal-data read audit — CR-02.** Not self-reported. `MARKET_DATA_VIEW`'s own docstring claims it excludes personal data, but three routes under exactly that permission return vendor name and/or phone with the wiring for read-audit already written and connected nowhere.

Two further items are worth carrying into a closure plan without blocking the verdict further: **WR-06** (wizard never asks for `open_weekdays`, so markets default silently to "open every day") and the **four outstanding VALIDATION.md Manual-Only Verifications** (real-data reconciliation, usability walkthrough, perceptual map check on a real device, requisites-format sign-off with the customer) — none of these are re-testable until gaps 1 and 2 above are closed.

The 890 backend / 94 frontend green test suite and the sabotage-based methodology used throughout this phase (SUMMARY files document 60+ deliberate code sabotages, each correlated to an expected, and only that, test failure) are genuinely strong evidence of *what was tested* — SC#2, SC#3, SC#4, and SC#5 hold up under that scrutiny and are VERIFIED here independently. But a green gate is not proof the phase goal was reached: the goal's own two-clause sentence and two CLAUDE.md hard constraints (tenant isolation extending to the client, mandatory audit trail) fail on inspection the test suite was never asked to perform.

---

_Verified: 2026-08-01_
_Verifier: Claude (gsd-verifier)_
