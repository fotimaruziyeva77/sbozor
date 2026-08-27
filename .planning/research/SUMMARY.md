# Project Research Summary

**Project:** SBOZOR
**Domain:** Multi-tenant AI-camera bazaar/market revenue-assurance SaaS (Uzbekistan) — CCTV occupancy detection → daily "patta" billing → cashier collection → leakage/mismatch reporting
**Researched:** 2026-07-28 – 2026-07-29
**Confidence:** MEDIUM-HIGH

## Executive Summary

SBOZOR is a revenue-assurance product, not a computer-vision product that happens to bill people — every one of the four research tracks converges on that framing. Experts build this class of system (municipal fee collection, parking enforcement, utility non-technical-loss detection, retail cash handling) as an **immutable ledger with an exception-queue workflow**: evidence-linked charges that are never edited, only reversed and re-entered; a human-in-the-loop review queue with an *honest*, randomly-sampled accuracy measurement (not one computed on the cases the model already flagged as uncertain); and cash-handling controls (shift reconciliation, instant receipts) that exist specifically because cash-based collection is documented worldwide to leak through the collector, not through the technology. The drafted MVP scope (`SBOZOR-MVP-texnik-topshiriq.md`) already gets the hard calls right — tariff-derived amounts, reason-coded overrides, evidence-linked billing, historical tariffs — but FEATURES.md identifies 16 P1-priority gaps (shift cash reconciliation, instant vendor push-receipts, dispute flow, mismatch case lifecycle, live collection worklist, blind random-sample accuracy audit, non-trading-day calendar, and more) that are not optional polish: several of them are the only thing that makes the product's own success criteria measurable or its core value claim true.

The recommended technical approach is a 3-service monorepo (core-api, cv-service, bot-service) sharing one PostgreSQL 18 database via a common `packages/sbozor-core` library — deliberately *not* a distributed system, because the real workload is tiny (25 cameras × 7 snapshots/day ≈ 175 frames/day, roughly 40× smaller than the spec assumed). That headroom should be spent on CV accuracy (a larger RF-DETR variant), not latency. Multi-tenancy is enforced by Postgres Row-Level Security as a backstop behind application-level scoping; billing is a two-phase pattern (live projection during the day, one immutable freeze at close-of-day, corrections only via `charge_adjustments`); and inter-service communication is deliberately just shared-database polling plus a transactional outbox for Telegram — not a message bus, because the volume doesn't justify one. Two stack findings should reshape the plan as written: **MinIO is archived/dead upstream** and must be replaced with SeaweedFS (Apache-2.0, same S3 API via boto3); and **`arq`, not Celery or bare APScheduler, is the right job-queue primitive** for the snapshot pipeline's durable-retry requirement — though ARCHITECTURE.md's own DB-materialized `capture_runs` + `SKIP LOCKED` pattern is a defensible alternative implementation of the same durability goal. This needs a single explicit decision during roadmap/Phase-4 planning (see Gaps).

The three biggest risk clusters, all avoidable if addressed structurally rather than patched later: **(1) CV correctness** — dark/IR morning frames from November onward, person-detection mistaken for goods-occupancy near busy aisles, and an accuracy metric that is invalid unless measured on a blind random sample rather than the review queue itself; **(2) financial integrity** — mutable charge rows, non-idempotent billing jobs, and UTC-vs-Asia/Tashkent boundary bugs, all cheap to prevent in the schema on day one and expensive to discover after payments have already been taken against wrong numbers; **(3) field/schedule risk** — NVR access is the single highest-variance dependency in a 12-week plan with zero buffer, and the pre-digitization revenue baseline (the entire ROI argument) can only be measured correctly in week 1, before collectors know the system is coming. All three are addressed by pulling field validation into a week-1 parallel track and by pre-agreeing, in writing, a cut list before pressure forces the wrong cuts in week 11.

## Key Findings

### Recommended Stack

Full detail: `.planning/research/STACK.md` (HIGH confidence — every version verified against PyPI/npm/GitHub APIs on 2026-07-29).

The stack is Python 3.13 + FastAPI 0.140 + SQLAlchemy 2.0 async + PostgreSQL 18 for `core-api` and `cv-service`; aiogram 3.30 for `bot-service`; Next.js 16 + React 19 + Tailwind 4 + next-intl for the frontend; Valkey (Redis-compatible, BSD-licensed) for cache/queue; SeaweedFS for S3-compatible snapshot storage; go2rtc for RTSP live view; RF-DETR + ONNX Runtime (CPU) for detection; Docker Compose + Nginx for deployment. Three findings override the drafted spec: MinIO's repo is archived with no further patches (→ replace with SeaweedFS, same S3 API); go2rtc already exposes a snapshot-capable endpoint so it can plausibly replace or supplement the planned per-shot ffmpeg spawn (see Gaps — this conflicts with a PITFALLS.md finding that favors Hikvision ISAPI instead); and the CV workload is roughly 175 frames/day, not "a few thousand," meaning the project is not latency-constrained and should spend its CPU budget on model accuracy.

**Core technologies:**
- **Python 3.13 / FastAPI 0.140 / SQLAlchemy 2.0 (async) / PostgreSQL 18** — only version combination where every required wheel exists today; SQLAlchemy 2.0's typed `Mapped[]` style plus native RLS support is the multi-tenant backbone.
- **RF-DETR (Apache-2.0, Nano→Large only) + ONNX Runtime CPU** — the only Apache-2.0-licensed, actively maintained, fine-tuning-friendly detector family; explicitly **never** Ultralytics YOLO (AGPL-3.0, forbidden by project constraint) and never RF-DETR XLarge/2XLarge (PML 1.0, easy to grab by accident).
- **SeaweedFS 4.40 (Apache-2.0)** — replaces MinIO, which is archived upstream (verified `archived: true`); accessed via `boto3`/`aioboto3`, never a vendor-specific SDK, so the storage backend stays a config change.
- **arq 0.28.0 (Valkey-backed)** — durable job queue + cron for the snapshot pipeline; rejected alternatives: APScheduler (no durable retry/history), Celery (three processes, massive overkill for 175 jobs/day).
- **go2rtc v1.9.14** — RTSP→WebRTC/HLS live view; also has a documented single-frame JPEG endpoint relevant to snapshot capture (see Gaps for the unresolved capture-method conflict).
- **Next.js 16 / React 19 / Tailwind 4 / next-intl 4 / react-konva** — admin panel, cashier flow, and the camera-zone polygon editor; `middleware.ts` is renamed to `proxy.ts` in Next 16 (breaks most existing tutorials/examples).
- **Postgres Row-Level Security + composite foreign keys** — the multi-tenant isolation mechanism, managed via `alembic-utils` so policies autogenerate instead of drifting from the schema.

### Expected Features

Full detail: `.planning/research/FEATURES.md` (MEDIUM-HIGH confidence — competitor data from marketing pages only; Uzbek legal findings via automated summarization, need specialist review; no primary user research with Karmana vendors/cashiers yet).

The drafted MVP spec covers the table-stakes registry/tariff/billing/reporting basics correctly. The research's central finding is that **because SBOZOR deliberately keeps cash in the loop (online payment deferred), the anti-fraud controls around the cashier are not optional extras — they are the product.** 16 P1 gaps were identified against the spec; all are recommended for the v1 launch date.

**Must have (table stakes, already in spec) — keep as-is:**
Stall registry, historically-versioned tariffs, ≤3-tap cashier flow, tariff-derived amounts with reason-coded overrides, evidence-linked billing, HITL review queue, immutable audit log, RBAC, 3 languages, multi-tenant wizard, live camera view, system monitoring alerts.

**Must have (P1 gaps missing from the drafted spec):**
- **Cashier shift lifecycle + blind cash reconciliation** (GAP-01) — closes the exact cash leak the product exists to close.
- **Instant vendor push-receipt on payment** (GAP-02) — cheapest, strongest anti-fraud control available; turns every vendor into a real-time auditor of every cashier.
- **Legally-correct receipt field set, labelled non-fiscal** (GAP-03).
- **Dispute/objection flow** (GAP-04) — no enforcement product survives without an appeal path.
- **Mismatch case lifecycle with owner/state/resolution** (GAP-05) — converts the flagship report from a PDF nobody opens into a process, and is the only source of an honest hit-rate metric.
- **Live same-day collection worklist for cashiers** (GAP-06) — the mechanism that actually raises revenue, not just reports on it.
- **Manual occupancy mode for the ~10% camera-blind stalls** (GAP-07).
- **Cashier↔zone assignment + per-cashier stats** (GAP-08) — prerequisite for GAP-01 and GAP-06, and answers "which cashier is the problem."
- **QR/bank-transfer payment method + mandatory reference** (GAP-09) — UzQR became mandatory for legal entities in trade/services on 2026-07-01, already in force.
- **Payment idempotency + reversal-only correction** (GAP-10).
- **Non-trading-day/holiday calendar per market** (GAP-11).
- **Notification governance: throttling, quiet hours, delivery tracking** (GAP-12) — Telegram's ~30 msg/s bulk ceiling is a hard limit, not advisory.
- **Frame quality gate** (GAP-13) — billing off a black/blurred frame is worse than not billing.
- **Role home screens with one headline number each** (GAP-14) — nearly free, sets perceived product quality.
- **Random-sample ground-truth audit queue** (GAP-15) — without it, the ≥90% accuracy success criterion is a correctness bug, not a nice-to-have.
- **Camera view-drift detection** (GAP-16) — otherwise a bumped camera silently and confidently bills the wrong vendors forever.

**Should have (differentiators):** evidence-linked billing (the strongest one), the same-day collection worklist, instant push-receipts, an honest published accuracy report, the mismatch hit-rate metric, per-stall QR stickers, bank-statement/UzQR reconciliation import (a merchant-contract-free path to cashless assurance).

**Defer to v1.x/v2 (deliberately, per research):** day close/period lock, PII/image-access consent controls, arrears aging + write-off policy, snapshot gap recovery, full interactive plan-map, CV fine-tuning, shop rentals, parking/ANPR, OFD/fiscal integration, buyer super-app, heatmaps/footfall — all correctly out of scope per the existing PROJECT.md and corroborated by this research.

**Explicit anti-features to actively resist:** free-form cashier amounts, facial recognition/biometric ID, automatic AI-issued fines, a wallet/payment-rail product, full VMS/recording, continuous real-time inference, half-day proration, auto-billing unassigned stalls to a placeholder, full offline-first cashier mode, cashier leaderboards/gamification, editable payment records, a generic LLM chatbot for vendors.

### Architecture Approach

Full detail: `.planning/research/ARCHITECTURE.md` (MEDIUM-HIGH confidence — patterns confirmed against Context7/official docs; exact detector thresholds and NVR behavior require pilot measurement).

Exactly 3 services (`core-api`, `cv-service`, `bot-service`) share one PostgreSQL database and a common `packages/sbozor-core` library (models, enums, tenancy helpers — no business logic). Each table has exactly one writer service; everyone else reads. Services talk to each other almost entirely *through the database* (state tables + a transactional outbox for Telegram), not through a message bus or synchronous RPC — deliberately, because the load (175 frames/day) doesn't justify the operational cost of a "clean" event bus. Multi-tenancy is enforced by Postgres RLS set per-transaction (`SET LOCAL`, never session-level) plus composite foreign keys that make a cross-tenant reference structurally impossible, verified in CI by a meta-test that checks every table for `market_id` + RLS. Billing runs in two phases: a same-day read-only projection (never written to a table) and a single immutable freeze at close-of-day, with all later corrections going through `charge_adjustments` — never an `UPDATE`.

**Major components:**
1. **core-api (FastAPI)** — owns markets, users, zones, stalls, tariffs, vendors, stall_assignments, cameras, camera_zones, snapshot_schedules, occupancy_reviews, daily_charges, charge_adjustments, payments, billing_runs, reconciliation_reports, notifications (insert), audit_log. Runs the billing-close job, RBAC, RTSP-credential encryption.
2. **cv-service (FastAPI, internal-only)** — owns capture_runs, snapshots, occupancy_events, detector_runs, camera_health. Runs a single tick-scheduler job that materializes due capture slots into a DB table (not a hidden in-memory job store), plus capture and detect worker tasks claiming rows via `FOR UPDATE SKIP LOCKED`.
3. **bot-service (aiogram)** — owns notification delivery status and vendor↔Telegram links. An outbox poller with token-bucket throttling; two bot identities (vendor, director) in one process.
4. **packages/sbozor-core** — shared SQLAlchemy models/enums/tenancy/money/timeutil helpers, no runtime state, editable-installed into all three service images.
5. **PostgreSQL 18** — sole source of truth; also functions as the job queue (`capture_runs`) and message queue (`notifications` outbox) — no separate broker needed at this scale.
6. **SeaweedFS (S3-compatible)** — snapshot byte storage; object *keys* live in Postgres, never raw URLs; access only via boto3/aioboto3.
7. **Valkey (Redis-compatible)** — cache, rate-limit counters, SSE pub/sub fan-out only; explicitly never used for queue or business state (anything there can be lost).
8. **go2rtc** — sidecar for live view, sitting behind nginx `auth_request`; never directly internet-facing.

Eight architecturally-justified patterns worth carrying into the roadmap directly: (1) DB-materialized capture plan with a state machine, not a "smart" scheduler; (2) immutable AI predictions + a separate review-decision table, reconciled via `COALESCE`; (3) two-phase billing (live projection, then one immutable freeze); (4) RLS + composite FK + repository-layer tenant scoping, all three layers, because each catches a different class of bug; (5) DB-integration + outbox for cross-service communication, not pub/sub, for anything that must not be lost; (6) normalized (0..1) polygon coordinates with versioning, never raw pixels; (7) go2rtc isolated from the snapshot capture path as a separate failure domain (see Gaps — contested by STACK.md); (8) audit writes inside the same transaction as the business action, via a contextvar-carried actor.

### Critical Pitfalls

Full detail: `.planning/research/PITFALLS.md` (MEDIUM-HIGH confidence overall; several individual pitfalls HIGH confidence — astronomical data, FFmpeg source history, Telegram API docs).

1. **The entire morning capture window is in darkness from November onward** (HIGH confidence, verified against sunrise data for Navoi). 5 of 7 snapshot slots are 06:00–08:00; by the time the ≥95% accuracy criterion is measured in December, 4–5 of those slots are dark/IR/twilight. Avoid by making the snapshot schedule a **seasonal, per-market data rule** from day one, classifying every frame's `light_mode` at ingest, and never letting a dark frame silently produce a billing-affecting result.
2. **ffmpeg RTSP capture hangs and silently deletes days of billing evidence** (HIGH confidence). A no-timeout `ffmpeg` blocks forever on NVR reboot/VPN flap; the deprecated `-stimeout` flag is now rejected by ffmpeg 8; a mid-GOP capture can return a grey "garbage" frame the detector confidently calls empty. Avoid by preferring the Hikvision ISAPI still-image endpoint (no RTSP session at all), and if ffmpeg is used, hard OS-level process-group kill plus a frame-validity gate before any capture is accepted.
3. **Person-detection used as the definition of occupancy** (MEDIUM-HIGH confidence). A passerby standing in front of a stall reads as "occupied"; perspective distortion means a person's body can fall inside the *neighbouring* stall's polygon. Avoid by defining occupancy as goods/structure presence (not human presence), requiring ≥2-snapshot corroboration for auto-charge, and drawing polygons tight on the counter surface with a front-edge line.
4. **Measuring AI accuracy from the nazoratchi (reviewer) queue is circular and biased** (HIGH confidence). Reviewing only `noaniq` (uncertain) cases measures the model exactly where it already knows it's unsure, and showing the reviewer the AI's answer first collapses independent judgment (automation bias, documented to crash reviewer accuracy in analogous domains). Avoid with two separate queues — an operational `noaniq` queue and a **blind, randomly-sampled** ground-truth audit queue — and report a confusion matrix, not "accuracy."
5. **Reviewer fatigue makes the HITL queue arithmetically impossible at scale** (HIGH confidence). 1000 rastalar × 7 snapshots × a realistic 15–25% uncertainty rate is 1,000–1,750 items/day against a human capacity of 150–250/hour; the rest get rubber-stamped, poisoning the fine-tuning dataset. Avoid with a hard daily queue budget, money/consequence-based prioritization, and instrumented reviewer latency — never a "bulk approve" button.
6. **Charges are mutable rows, making reconciliation and disputes unwinnable** (HIGH confidence). Avoid by making `daily_charges` append-only/immutable once finalized; all corrections are new `charge_adjustments` rows.
7. **The end-of-day billing job is not idempotent → double charges on day one** (HIGH confidence). A two-line `UNIQUE(market_id, stall_id, business_date)` constraint plus an advisory lock makes the failure mode structurally impossible — do it in the foundation phase, not the billing phase.

*(Additional HIGH/MEDIUM-HIGH pitfalls carried into the roadmap below: UTC-vs-Asia/Tashkent business-day bugs; multi-tenant leaks from a single missing `market_id` predicate; a bumped/drifted camera silently billing the wrong vendors at full confidence; a mis-measured revenue baseline making the whole ROI claim unfalsifiable; cashier resistance and data-entry sabotage; a parallel run that collapses into duplicate data entry by day three; NVR unreachability discovered too late in the schedule; and a 12-week plan with zero buffer that needs its cut list agreed now, not under week-11 pressure.)*

## Implications for Roadmap

Based on combined research — primarily ARCHITECTURE.md's dependency-driven build order (independently cross-checked against PITFALLS.md's phase-to-phase mapping and FEATURES.md's feature-dependency graph, which agree closely) — the following 8-phase structure is recommended for the 12-week build, plus two cross-cutting tracks that run outside the sequential dependency chain.

### Parallel Field Track (week 1 onward — not sequenced, runs alongside every phase)
**Rationale:** Two items in PITFALLS.md are explicitly "cannot be done retroactively": the pre-digitization revenue baseline (Pitfall 11) must be measured *before* collectors know the system is coming, and NVR access (Pitfall 14) has unpredictable external lead time (CGNAT device procurement, credential handoff) that must not be discovered in week 5.
**Delivers:** Signed daily baseline sheets (revenue-per-occupied-rasta, not just totals) from week 1; a remote-access feasibility call and camera-coverage audit with real frames; a WireGuard endpoint device ordered immediately if the market is behind CGNAT; "one real Karmana snapshot stored" as an explicit week-2 milestone.
**Avoids:** Pitfall 11 (unfalsifiable ROI claim), Pitfall 14 (NVR risk discovered too late — the single biggest schedule risk in the project per PITFALLS.md).

### Phase 1: Foundation & Tenant Safety (~weeks 1–2)
**Rationale:** Multi-tenant RLS, immutable-ledger schema constraints, `business_date`/timezone handling, and i18n scaffolding are called out by every research file as "not retrofittable" — 8 weeks of queries written against a missing constraint means a full audit, not a migration.
**Delivers:** Monorepo + Docker Compose skeleton, `packages/sbozor-core`, single Alembic migration history, 2 DB roles (owner/app, RLS-bypassing worker role), auth/RBAC, trigger-based audit log on financial tables, i18n scaffold (3 catalogs), CI including a cross-tenant test suite and a tenancy meta-test, Sentry/healthchecks. Also where the accuracy-criterion wording gets renegotiated and the cut list gets pre-agreed with the customer, in writing.
**Addresses:** Already-in-spec RBAC/audit/i18n table stakes; schema prerequisites for GAP-10 (idempotency) and GAP-11 (non-trading-day calendar column).
**Avoids:** Pitfalls 6 (mutable charges), 7 (non-idempotent billing), 8 (UTC vs Asia/Tashkent), 9 (multi-tenant leak), M10 (audit log holes), M11 (data residency raised now).

### Phase 2: Market Domain & Wizard Data (~weeks 3–4)
**Rationale:** Both CV and billing depend on stalls/tariffs/vendors existing; entering Karmana's real data early means every later phase tests against reality instead of fixtures.
**Delivers:** markets, zones, stalls, product_categories, historically-versioned tariffs, vendors, stall_assignments; the wizard's data-entry steps; a **schematic** (grid/list) plan-map — not the full interactive map.
**Addresses:** Stall registry, tariff versioning, per-vendor accounts (in-spec); GAP-11 (non-trading-day calendar).
**Avoids:** M2 (plan-map scope creep eating the frontend developer — enforce schematic-only now).

### Phase 3: Camera & Network Connectivity (~weeks 3–4, overlapping Phase 2)
**Rationale:** The highest external/unproven risk in the project — NVR credentials and reachability are outside the team's control. ARCHITECTURE.md explicitly ranks this ahead of CV work so failure surfaces in week 3–4, not week 5–6.
**Delivers:** WireGuard tunnel (outbound-from-market, split-tunnel scoped to the NVR subnet only), cameras CRUD with Fernet-encrypted RTSP credentials, a connectivity/test endpoint, go2rtc live view behind nginx `auth_request`.
**Uses:** go2rtc v1.9.14, host-level `wg-quick`, `cryptography`/Fernet.
**Avoids:** Pitfall 14 (NVR unreachable, discovered late); Anti-Pattern 9 (exposing go2rtc/storage directly to the internet).

### Phase 4: Snapshot Capture Pipeline (~weeks 5–6)
**Rationale:** Frames are a durable, reusable asset; detection is reprocessable at any time against a versioned model. Get real capture running before spending effort on the detector, so Phase 5 has real Karmana frames — including dark/IR ones — to tune against.
**Delivers:** `snapshot_schedules` (seasonal-profile capable from day one, not 7 hardcoded times), tick + `capture_runs` state machine (idempotent, jittered, `SKIP LOCKED` workers), snapshot capture (method TBD — see Gaps), frame quality/`light_mode` gate, SeaweedFS storage via `boto3`/`aioboto3`, retention lifecycle configured at bucket creation, missed-slot alerting.
**Addresses:** GAP-13 (frame quality gate); groundwork for GAP-20 (snapshot gap recovery, deferred to v1.x).
**Avoids:** Pitfall 1 (dark morning window — seasonal schedule + `light_mode` from day one), Pitfall 2 (ffmpeg hangs), M5 (duplicate scheduler across workers), M6 (NVR thundering-herd at 06:00), M8 (storage/retention arithmetic never computed).

### Phase 5: Camera Zones, CV Detection & HITL Review (~weeks 7–8)
**Rationale:** The heaviest frontend item (polygon editor) and the least certain technical item (detector accuracy/latency on real hardware) belong together, and only make sense once Phase 4 is producing real frames.
**Delivers:** `camera_zones` polygon editor (react-konva, normalized coordinates, versioned, autosave-per-polygon), RF-DETR + ONNX Runtime CPU detection worker, `supervision` `PolygonZone` occupancy logic with a front-edge/corroboration rule, two-threshold triage, a budgeted/prioritized nazoratchi review queue with no bulk-approve, the **blind random-sample ground-truth audit queue**, camera drift/tamper detection.
**Uses:** RF-DETR-Small→Large (Apache-2.0), ONNX Runtime CPU EP, `supervision`, react-konva/konva.
**Addresses:** GAP-15 (random-sample audit — must ship with the queue, not bolted on after), GAP-16 (camera drift detection), GAP-07 (manual occupancy mode for the ~10% blind stalls).
**Avoids:** Pitfalls 3 (person-as-occupancy), 4 (biased accuracy measurement), 5 (reviewer fatigue/rubber-stamping), 10 (camera drift silently mis-billing), M1 (polygon editor underestimated).

### Phase 6: Billing & Cashier (~weeks 9–10)
**Rationale:** Billing has no valid input until occupancy + review exist; the cashier's "expected patta" screen is a read-only projection over the same data, so it can only be meaningfully built after Phase 5.
**Delivers:** `close_day` job (advisory-locked, idempotent, `ON CONFLICT DO NOTHING`), `stall_day_occupancy` freeze, immutable `daily_charges` + `charge_adjustments`, payments with client-generated idempotency keys, cashier↔zone assignment, shift open/close with blind cash declaration + variance (GAP-01), live same-day collection worklist (GAP-06), QR/transfer payment method + mandatory reference (GAP-09), receipt field set (GAP-03), debt as a computed view (never a stored balance column).
**Addresses:** GAP-01, GAP-03, GAP-06, GAP-07 (billing side), GAP-08, GAP-09, GAP-10.
**Avoids:** Pitfalls 6/7 (reinforced at the write-path level), 12 (cashier sabotage — wire in the cross-check anomalies here: status=closed-but-AI-occupied, payment-on-AI-empty-stall).

### Phase 7: Reconciliation, Notifications & Bots (~week 11)
**Rationale:** The mismatch report and both bots consume the billing run's output directly; the notification outbox writes inside the same transaction as `close_day`, so this is a direct downstream consumer of Phase 6, not a parallel track.
**Delivers:** Mismatch case lifecycle with owner/state/resolution (GAP-05 — yields the hit-rate metric), dispute/objection flow (GAP-04), notifications outbox with a token-bucket Telegram sender (quiet hours, blocked-user tracking — GAP-12), vendor bot (contact-ownership-verified registration, balance/debt, instant push-receipt — GAP-02, formatted per GAP-03), director bot (morning digest, evening mismatch report), role home screens (GAP-14).
**Avoids:** M3 (unverified contact-ownership registration), M4 (Telegram broadcast rate limits, blocked bots, ungated debt reminders).

### Phase 8: Reports, Hardening & Launch (~week 12)
**Rationale:** Reporting requires everything else to exist first; this is also the pre-agreed hardening week rather than a new-features week, since the underlying 12-week plan has zero schedule buffer.
**Delivers:** 3 Excel exports (revenue, arrears register, mismatch archive — not 6), AI accuracy report (confusion matrix sourced from the blind audit queue), 3-language polish, a backup + restore drill (Postgres **and** SeaweedFS objects, on a clean host), a go-live runbook, parallel-run comparison tooling (3-way: book vs app vs AI-expected, daily-signed).
**Avoids:** Pitfall 13 (parallel run collapsing into duplicate entry — the 3-way sheet is a Phase 8 deliverable, not an afterthought), Pitfall 15 (the wrong things get cut under week-11 pressure — this cut list was pre-agreed back in Phase 1).

### Post-Launch: Parallel Run (weeks 13–16, outside the 12-week build)
Not a build phase — an operating procedure designed in Phase 8 and executed after go-live: daily third-party reconciliation (nazoratchi or admin, not the cashier), a hard pre-announced cutover date, and entry-latency instrumentation to catch "reconstruction from memory" before it silently destroys the only independent measurement of the pilot's effect.

### Phase Ordering Rationale

- **Dependency chain drives the sequence:** tenant/audit/schema safety (1) → domain data (2) → external connectivity (3) → capture (4) → detection (5) → billing (6) → notifications (7) → reporting (8). This is ARCHITECTURE.md's own explicitly-reasoned "Build Order" table, independently corroborated by PITFALLS.md's phase-to-phase mapping and FEATURES.md's feature-dependency graph — three research tracks converging on the same order is a strong signal, not a coincidence.
- **The field track is deliberately pulled out of the sequential chain** and started in week 1 in parallel, because both its deliverables (baseline measurement, NVR access) have "cannot be done retroactively" cost profiles and long external lead times that are on nobody else's critical path but block Phases 3–5 if they slip.
- **Phase 5 groups the two highest-uncertainty items together** (polygon editor UX, detector accuracy/latency) precisely so they can be timeboxed and, if the pre-agreed cut list needs to be invoked, cut or descoped without touching the financial core in Phases 1, 6, and 7.
- **The boundary between Phase 5 and Phase 6 is pitfall-driven, not just dependency-driven:** the `uncertain → empty` default and the blind audit queue must exist *before* `daily_charges` are ever generated from occupancy data, or the accuracy number is meaningless from day one and billing has no valid, auditable input.

### Research Flags

Needs research during planning (recommend `/gsd-plan-phase --research-phase <N>`):
- **Phase 3 (Camera & Network):** NVR-model-specific ISAPI/Digest-auth behavior, concurrent RTSP session caps on this specific Hikvision unit, and the actual CGNAT/WireGuard topology at Karmana are all explicitly flagged LOW confidence / "verify in the field" across STACK.md and PITFALLS.md.
- **Phase 4 (Snapshot Capture Pipeline):** The snapshot-capture-method conflict (see Gaps below) must be resolved empirically against the real NVR; ffmpeg version-pinning behavior, seasonal-schedule implementation, and frame-quality/`light_mode` thresholds all need pilot-time tuning, not just code.
- **Phase 5 (CV + HITL):** Detector latency/accuracy benchmarks in STACK.md and PITFALLS.md are sourced from Intel hardware or community numbers, not the actual Contabo AMD EPYC box; threshold tuning, the tiling/SAHI decision for small stalls, and the polygon-editor UX are all explicitly marked "measure, don't assume."

Standard patterns (well-documented, skip `--research-phase`):
- **Phase 1 (Foundation):** RLS + composite-FK multi-tenancy, SQLAlchemy 2.0 async, and Alembic setup are fully coded out with working examples in ARCHITECTURE.md, sourced from official docs/Context7.
- **Phase 2 (Market Domain & Wizard):** Standard CRUD plus a well-precedented historically-versioned tariff pattern.
- **Phase 6 (Billing & Cashier):** The two-phase billing pattern (live projection → one immutable freeze → adjustment-only correction) is fully coded out in ARCHITECTURE.md's Pattern 3 with working SQL, sourced from ledger/reconciliation industry practice.
- **Phase 7 (Notifications & Bots):** The outbox pattern and aiogram throttling are fully documented with code, sourced from official aiogram docs and the Telegram Bot API FAQ.
- **Phase 8 (Reports & Launch):** Mostly export/polish work using already-selected, well-documented libraries (XlsxWriter).

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every version verified against PyPI/npm/GitHub APIs and Docker Hub on 2026-07-29; licensing verified against upstream repos. A handful of items (RF-DETR CPU latency on AMD EPYC, exact NVR ISAPI channel behavior) are explicitly self-flagged LOW confidence, pending pilot measurement. |
| Features | MEDIUM-HIGH | Uzbek legal/regulatory findings (receipt fields, UzQR mandate, data-localization law) are read via automated summarization of primary lex.uz sources — directionally reliable but need a local legal specialist's sign-off before launch. Competitor feature claims come from marketing pages (both competitor portals are login-gated). No primary user research yet with Karmana vendors, cashiers, or controllers — the GAP-01 through GAP-08 cash-handling gaps are inferred from analogous domains (municipal fee collection, retail cash SOPs, parking enforcement) and should be validated during the parallel-run period. |
| Architecture | MEDIUM-HIGH | Patterns are corroborated against Context7/official docs (go2rtc, APScheduler, Frigate, Telegram, Shapely) with working code examples. Exact detector thresholds, JPEG frame sizes, and Hikvision session limits are explicitly self-flagged as pilot-time measurements, not assumptions. |
| Pitfalls | MEDIUM-HIGH | Several individual pitfalls are HIGH confidence with primary-source verification (sunrise/sunset astronomical data for Navoi; FFmpeg's own devel-list history removing `-stimeout`; Telegram's documented rate limits). The rollout/sabotage/baseline-measurement pitfalls are MEDIUM confidence, reasoned by analogy from Tanzania/Kenya/Ghana revenue-digitization case studies rather than SBOZOR-specific data. |

**Overall confidence:** MEDIUM-HIGH — the technical foundation (stack choices, schema patterns, service boundaries) is unusually well-verified for a pre-build research pass. The gaps that remain are the ones no amount of desk research can close: real-hardware CV performance, actual NVR behavior, and Uzbek legal specifics requiring a licensed local reviewer.

### Gaps to Address

- **Snapshot capture method is unresolved across the research files — the single most important open technical question.** STACK.md recommends go2rtc's `/api/frame.jpeg` endpoint as the *primary* snapshot source (ffmpeg only as last-resort diagnostics), reasoning from the RTSP-handshake latency it eliminates. PITFALLS.md's own top mitigation for its highest-severity capture pitfall instead recommends the **Hikvision ISAPI still-image endpoint** as primary (no RTSP session at all — no GOP wait, no session-limit pressure, plain HTTP timeout works), with ffmpeg as fallback only. ARCHITECTURE.md's Pattern 7 defaults to a **direct ffmpeg subprocess** as primary, keeping go2rtc scoped to live view only, specifically to isolate capture's failure domain from live-view's CPU load, and treats go2rtc-as-capture-source as a documented per-camera fallback rather than the default. **Recommended resolution for Phase 4 planning:** field-test ISAPI availability against the actual Karmana NVR firmware first (matches PITFALLS.md's reliability argument and requires no persistent session); fall back to go2rtc's frame endpoint per-camera if ISAPI isn't exposed (reuses the session already required for live view); keep raw ffmpeg as last-resort/diagnostic only. This is explicitly still an open, unmeasured question per STACK.md's own LOW-confidence notes.
- **Job-orchestration mechanism for the snapshot pipeline is stated two ways.** STACK.md recommends `arq` (Valkey-backed durable queue + cron) as the concrete implementation. ARCHITECTURE.md's Pattern 1 instead hand-rolls a single-job APScheduler tick that materializes rows into `capture_runs`, processed by `FOR UPDATE SKIP LOCKED` workers — and its own Anti-Pattern 3 explicitly warns against treating a scheduler's job store as the source of truth. These aren't necessarily incompatible (arq could sit underneath the DB-materialized pattern for execution/retry plumbing), but no single document reconciles them. Resolve during Phase 4 planning; the DB-materialized approach is likely preferable for its free auditability ("which snapshot was skipped yesterday" becomes a query), with `arq` as an optional implementation detail underneath rather than the primary durability mechanism.
- **MinIO naming is stale in two of the four research files.** STACK.md's core recommendation is to replace MinIO with SeaweedFS (MinIO's repo is archived upstream), but ARCHITECTURE.md and PITFALLS.md were researched referencing "MinIO" throughout as the object-store name. The architectural patterns described (object *keys* — not URLs — stored in Postgres, presigned short-TTL URLs, lifecycle rules configured at bucket creation, S3 access exclusively via `boto3`/`aioboto3`) apply unchanged to SeaweedFS; treat every "MinIO" reference in ARCHITECTURE.md/PITFALLS.md as "the S3-compatible object store (SeaweedFS)" during planning.
- **PROJECT.md's Constraints section says "RT-DETR/D-FINE/YOLOX family"; STACK.md's actual pick is RF-DETR specifically** (Roboflow's actively-maintained, fine-tuning-oriented evolution of the RT-DETR lineage — RT-DETR itself is evaluated in STACK.md and correctly noted as "superseded"). Not a real conflict — RF-DETR is Apache-2.0 and within the spirit and letter of the licensing constraint — but PROJECT.md's Key Decisions table should be updated to name RF-DETR specifically once the roadmap is approved, alongside the SeaweedFS/MinIO substitution above.
- **Uzbek legal specifics need a licensed local reviewer before launch.** Receipt field requirements (lex.uz 2185/253), the personal-data-localization scope for CCTV imagery containing identifiable faces (plausibly biometric-adjacent under a 2026 amendment), and KKM/fiscal obligations were all read via automated summarization of primary sources, not confirmed by a specialist. This should happen in parallel with Phases 1–2, before the evidence archive grows large enough to make a compliance-driven migration painful.
- **Seven open customer questions from FEATURES.md are unresolved** and materially affect scope for GAP-01, GAP-05, and GAP-09: whether Karmana already runs an online KKM/virtual kassa; whether the market already has a UzQR code and at which bank; who physically holds cash between collection and banking today; whether fee exemptions or day-of-week rates exist; whether one stall can be traded by different vendors at different times; what share of vendors have Telegram-capable smartphones; and who owns mismatch-item resolution (controller, admin, or director). Resolve these in week 1, ideally before Phase 2 (Market Domain) and Phase 6 (Billing & Cashier) are planned in detail.
- **CV performance on the actual target hardware is unverified.** RF-DETR ONNX latency figures are from Intel hardware or community benchmarks, not Contabo's AMD EPYC; the Hikvision NVR's concurrent-RTSP-session cap for this specific model is unmeasured; actual IR range of Karmana's cameras (mounted 4–8m, covering 20–40m) is unverified. All are explicitly flagged for pilot-time measurement in STACK.md and PITFALLS.md — budget time for this in Phases 3–5 rather than assuming the desk-research numbers hold.

## Sources

### Primary (HIGH confidence)
- PyPI JSON API, npm registry API, GitHub REST API, Docker Hub API, endoflife.date API — exact versions, release dates, license classifiers, archived/activity status for every technology named in STACK.md (verified 2026-07-29)
- Official docs: rfdetr.roboflow.com, go2rtc.org, nextjs.org (middleware→proxy, Next 16 upgrade guide), apscheduler.readthedocs.io, supervision.roboflow.com, aiogram docs via Context7 (`/websites/aiogram_dev_en`)
- Context7 official-doc mirrors used in ARCHITECTURE.md: go2rtc API (`/alexxit/go2rtc`), APScheduler (`/agronholm/apscheduler`), Frigate zone docs, Telegram Bot API FAQ, Shapely docs, next-intl (`/websites/next-intl_dev`)
- Astronomical sunrise/sunset data for Navoi (40.11°N, 65.35°E, UTC+5) — gaisma.com
- FFmpeg devel/cvslog history confirming `-stimeout` → `-timeout` rename and removal in FFmpeg 8
- lex.uz 2185 and 253 (Uzbek market-fee regulation, primary legal text); Central Bank of Uzbekistan UzQR press releases

### Secondary (MEDIUM confidence)
- MinIO archival timeline and RustFS pre-release status — corroborated across multiple independent trade-press sources and directly confirmed by GitHub's `archived: true` flag
- Hikvision ISAPI endpoint behavior, Digest-auth clock-drift sensitivity — IPCamTalk, Visiotech, Hikvision Europe integration docs, community best-practices repos
- RF-DETR CPU ONNX latency benchmarks — community repos and the D-FINE paper, explicitly flagged as order-of-magnitude only, not Contabo-specific
- Postgres RLS multi-tenant pattern (`SET LOCAL`, `FORCE ROW LEVEL SECURITY`) — Crunchy Data and multiple 2026 practitioner write-ups
- Competitor analysis (raqamli-bozor.uz / eBazaar) — marketing pages only, both portals login-gated as of re-check on 2026-07-28
- Revenue-digitization field literature — The Chanzo (Tanzania), The Star (Kenya), Adomonline (Ghana), IMF *Digital Revolutions in Public Finance*, WEF corruption/digital-payments research
- HITL/automation-bias literature — radiology-reader studies, MIT Sloan Management Review, arXiv uncertainty-sampling-bias paper

### Tertiary (LOW confidence — flagged for pilot validation)
- Exact RF-DETR-Small vs -Large latency/accuracy on Karmana imagery — must be measured, not assumed
- Whether the Karmana Hikvision NVR firmware exposes ISAPI `/picture` on all 20–25 channels, and its concurrent-RTSP-session limit — verify in week 1–2 of the field track
- JPEG frame size and resulting disk/retention arithmetic — recompute against Karmana's actual camera resolutions
- `alembic-utils` long-term maintenance — low switching cost if it lags (raw `op.execute()` migrations), worth a glance before committing

---
*Research completed: 2026-07-29*
*Ready for roadmap: yes*
