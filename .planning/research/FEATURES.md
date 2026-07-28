# Feature Research

**Domain:** Bazaar / market revenue-management SaaS (stall occupancy → daily fee "patta" → cash collection → leakage detection), Uzbekistan
**Researched:** 2026-07-28
**Confidence:** MEDIUM-HIGH (competitor + regulatory findings verified against primary sources; some adjacent-domain patterns inferred from analogous products)

---

## How to read this document

SBOZOR's MVP scope is already drafted in `SBOZOR-MVP-texnik-topshiriq.md` v1.1. This research does three things:

1. **Validates** that scope against how revenue-assurance products are actually built (POS/cash handling, municipal revenue collection, parking enforcement, utility loss detection, HITL computer vision).
2. **Names 20 gaps** — features that are table stakes in those domains and are missing or under-specified in the current MVP list. Each gap is marked **`GAP`** and carries a priority.
3. **Names anti-features** to keep out, including a few the strategy document actively wants.

**The single most important framing from the research:** in every documented cash-based municipal collection system, digitization that leaves the collector holding cash produces "cosmetic digitisation" — leakage persists because transactions can still originate outside the system. SBOZOR's MVP deliberately keeps cash in the loop (online payment is deferred). That is defensible for a district pilot, but it means **the anti-fraud controls around the cashier are not optional extras — they are the product**. Six of the P1 gaps below exist for exactly this reason.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that market administrations, cashiers, vendors and regulators assume exist. Missing = the product feels incomplete, untrustworthy, or illegal.

#### Already in the MVP spec — keep as-is

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Stall registry with number, zone/row, category, status | Regulation requires numbered trading places with a posted layout scheme (lex.uz 253/2012). Both competitors have it. | LOW | Already spec'd (§4.2). Stall number is the primary key humans use — make it searchable, sortable, and printable. |
| Product-category → daily tariff, historically versioned | Tariffs change by decision; charges must reproduce historically ("what was the rate on 12.09?") | LOW-MED | Already spec'd. Versioning is what makes retrospective disputes winnable. |
| Cashier records payment (cash / terminal) in ≤3 taps | Collection happens standing up, on a phone, hundreds of times a day | MED | Already spec'd (§4.4). The ≤3-tap constraint is correct and should be a hard acceptance criterion. |
| Amount auto-derived from tariff; manual override only with reason code | Free-form amounts are the classic corruption hole in fee collection | LOW | Already spec'd + logged in Key Decisions. Excellent. Do not weaken. |
| Per-vendor account: charges, payments, balance, debt | Regulation 2185 expects per-tenant accounting; every competitor has "shaxsiy hisob" | MED | Already spec'd. |
| Daily charge run tied to evidence snapshots | The whole value claim ("we can prove it") collapses without the image link | MED | Already spec'd (§4.3). |
| Mismatch report: occupied-but-unpaid + unregistered trading | This is the Core Value | MED | Already spec'd. See GAP-05 — it needs a lifecycle, not just a report. |
| HITL review queue for `noaniq` results | Nobody bills from an unreviewed model in year one | MED | Already spec'd (§4.5). See GAP-19 for the sampling flaw. |
| Image-evidence archive with retention policy | Evidence quality is what determines whether a disputed charge is upheld or voided (parking enforcement consensus) | MED | Already spec'd (90d full / 1y compressed). |
| Immutable audit log (who, when, what, old→new) | Anti-corruption product with no audit trail is not credible to a director or a prosecutor | MED | Already spec'd. |
| Role-based access (platform admin, director, market admin, cashier, controller, vendor) | Six distinct jobs, six distinct blast radii | MED | Already spec'd. See GAP-14 (role home screens) and GAP-18 (image visibility per role). |
| Reports + Excel export | Uzbek administrations run on Excel; the director will forward it to the hokimiyat | LOW-MED | Already spec'd. Ship 3 exports well, not 6 badly. |
| Vendor Telegram bot: balance, debt, payment history, reminders | Telegram is the default channel; competitors ship mobile apps, SBOZOR substitutes the bot | MED | Already spec'd. See GAP-02, GAP-03, GAP-12. |
| Director digest (morning) + mismatch report (evening) | Executives consume a push, not a dashboard | LOW-MED | Already spec'd. |
| 3 languages (uz-latin, uz-cyrillic, ru) | Mixed-generation users; the director may prefer Cyrillic | MED | Already spec'd, scaffolded week 1. Correct call. |
| Multi-tenant `market_id` + "New market" wizard | The business model is 500 markets, not 1 | HIGH | Already spec'd. The wizard *is* the product for everyone except the pilot. |
| Live camera view | Explicit customer demand (2026-07-28) | MED | Already spec'd via go2rtc. Keep it thin — see AF-05. |
| System monitoring alerts (camera offline, snapshot missed, backup failed) | Silent pipeline failure = silent revenue loss | LOW-MED | Already spec'd. |

#### GAPS — table stakes that the MVP list is missing or under-specifies

| # | Feature | Why Expected | Complexity | Priority |
|---|---------|--------------|------------|----------|
| **GAP-01** | **Cashier shift lifecycle + cash reconciliation** (open shift with float → close shift → **blind** declared count → system-expected vs declared → variance → handover signed off by admin/director; Z-report per shift) | Universal retail cash-handling SOP. More importantly: without it, cash collected ≠ cash banked, and the exact leak the product claims to close stays wide open. Nairobi/Tanzania case studies show collectors holding cash and "entering it later". Blind counting matters — showing the expected total first produces confirmation bias. | MED | **P1** |
| **GAP-02** | **Instant payment confirmation pushed to the vendor** (Telegram message the moment the cashier saves: stall no., date, amount, cashier name, receipt no.) | This is the cheapest, strongest anti-fraud control available inside MVP scope: it turns 300–1000 vendors into auditors of 5 cashiers. Ghana's fake-collector fraud (forged paper receipts) and Kenya's "pocket now, key in later" pattern both die instantly against a real-time push receipt. | LOW | **P1** |
| **GAP-03** | **Digital receipt with the legally-required field set** (market name, STIR/TIN, date+time, payment type, amount, **stall number**, **product name**, cashier, reference no.) — explicitly labelled *not a fiscal receipt* while OFD is out of scope | Uzbek rules define exactly what a market fee receipt must contain, and for markets on online KKM/virtual kassa it must also carry a QR + fiscal mark. Mirroring the field set costs nothing and makes the eventual OFD integration a swap, not a redesign. Mislabelling it as fiscal is a legal risk. | LOW | **P1** |
| **GAP-04** | **Dispute / objection flow (nizo)** — vendor (bot) or controller (panel) contests a charge → case with reason code → evidence snapshot attached → decision by market admin/director → writes a `charge_adjustment` → outcome pushed back to vendor | Parking-enforcement products treat the appeal path as core lifecycle, not an add-on, and the evidence record is what decides the outcome. The spec has `charge_adjustments` (the *effect*) but no intake channel and no case state (the *process*). Without it, every dispute becomes a phone call to the director and the audit trail says "admin changed a number". | MED | **P1** |
| **GAP-05** | **Mismatch → action lifecycle (case management)** — every "occupied but unpaid" and "unregistered trading" item gets an owner, a state (new → assigned → resolved: *collected* / *registered* / *false positive* / *waived*), a resolution reason, and a closure timestamp | Revenue-assurance practice is exception queues with owners and SLAs, not reports. Utility loss-detection field inspections hit ~60% — meaning ~40% of AI flags are wasted trips unless outcomes are tracked. Tracking outcomes also yields **the only honest precision metric for the flagship feature**. A report with no closure loop becomes a PDF nobody opens by week three. | MED | **P1** |
| **GAP-06** | **Live collection worklist for cashiers** — "today, in your rows: 84 occupied, 61 paid, **23 outstanding**", ordered by row, tap-to-collect | The current cashier flow is *search stall by number*, which means the AI only ever accuses people after the money is gone. A same-day worklist converts detection into **collection** — this is the mechanism by which revenue actually rises, and it is the feature neither competitor advertises. All data already exists at 06:30. | LOW-MED | **P1** |
| **GAP-07** | **Manual occupancy mode for camera-blind stalls (~10% at Karmana)** — controller mobile checklist walk; per-stall `coverage` flag; reports separate AI-covered from manual stalls | The spec acknowledges ~10% blind stalls only in the risk table (§10), with no module. Without it, 10% of stalls are silently unbillable and the occupancy % is quietly wrong. | LOW-MED | **P1** |
| **GAP-08** | **Cashier ↔ zone/row assignment + per-cashier collection stats** (collected, coverage %, variance history, override count) | Prerequisite for GAP-06 and GAP-01, and it is how a director answers "which cashier is the problem?" — the question that sells this product. | LOW | **P1** |
| **GAP-09** | **Payment method: add QR / bank transfer + mandatory reference number for non-cash** | **UzQR, the Central Bank's unified national QR code, became mandatory for legal entities in trade and services on 2026-07-01** — i.e. already in force. Vendors will pay by QR whether or not SBOZOR supports it; if the cashier can't record it, the ledger diverges from the bank account on day one. Receipt/reference number should be mandatory for terminal and QR, optional only for cash. | LOW | **P1** |
| **GAP-10** | **Payment integrity: idempotency key on submit, duplicate detection, reversal-only correction (no edit/delete)** | Mobile network hiccup + impatient double-tap = double charge = a furious vendor and a broken trust story. Financial records must be append-only; corrections are reversals with reason. | LOW | **P1** |
| **GAP-11** | **Non-trading day / holiday calendar per market** (market closed → no charges generated regardless of occupancy) | A stray occupancy detection on Eid or a closed Monday generates charges nobody owes. One such incident in week one costs more trust than the AI earns in a month. | LOW | **P1** |
| **GAP-12** | **Notification governance: throttled send queue, quiet hours, per-user language + opt-in, delivery-failure tracking** | Telegram Bot API limits are hard: **~1 message/second per chat and ~30 messages/second for bulk broadcast**, with 429 + `retry_after` beyond that. A 1000-vendor debt-reminder run is not a `for` loop. Quiet hours: a debt reminder at 23:40 is how a bot gets blocked and a director gets a complaint. | LOW-MED | **P1** |
| **GAP-13** | **Frame quality gate** — reject/flag too-dark, blurred, or obstructed frames before inference (auto-`noaniq`, excluded from accuracy stats) | The spec names dawn darkness as risk #1 (§10) but places the mitigation in "check IR mode" rather than in the pipeline. Billing off a black frame is worse than not billing. | LOW | **P1** |
| **GAP-14** | **Role home screens with one headline number each** — director: *collected vs expected vs leakage today*; market admin: *registry health* (unassigned occupied stalls, stalls without camera zones); cashier: *my shift*; controller: *my queue* | The spec lists reports but no landing screens. Perceived product quality in this segment is set by the first screen after login, and it is nearly free once the reports exist. | LOW | **P1** |
| **GAP-15** | **Random-sample ground-truth audit of confident predictions** — each day, N randomly-chosen *confident* predictions are injected into the controller queue for blind verification | **This is a correctness bug in the current design, not a nice-to-have.** If controllers only review `noaniq` cases, the "AI accuracy ≥90%" success criterion (§9) is computed on a biased sample and can never detect confident-but-wrong predictions — the exact failure mode that produces false charges. Random sampling is the only way the ≥90% number means anything. | LOW | **P1** |
| **GAP-16** | **Camera view-drift detection** — compare each snapshot against a stored reference frame; alert when the scene shifts beyond threshold (camera bumped, re-aimed, lens fouled) | If a camera moves 15°, every polygon silently points at the wrong stalls and billing breaks with no error anywhere. Classic silent failure mode of zone-based occupancy systems. Cheap version: daily thumbnail contact-sheet for the controller + pixel-difference alert. | MED | **P1** |
| **GAP-17** | **Day close (kun yopish)** — after the nightly charge run and director acknowledgement, the day is locked; later changes only via `charge_adjustments` | Basic accounting hygiene and the thing that makes yesterday's number quotable. Without a close, every historical report is provisional forever. | LOW-MED | **P2** |
| **GAP-18** | **PII and image-access controls surfaced as features** — vendor consent record, role-gated access to camera images/live view, retention timer enforcement, per-vendor data export | Vendor PII (name, phone) falls under Uzbek personal-data localization law (already flagged in §5). Live camera view is the highest-sensitivity surface in the product and should not be visible to every role by default. | LOW-MED | **P2** |
| **GAP-19** | **Arrears aging + escalation ladder + write-off with approval** — buckets (0–7 / 8–30 / 30+ days), automatic escalation (reminder → formal warning → director action list), write-off requires director approval and lands in the audit log | The debt register exists; the *policy engine* does not. Debt with no escalation path and no write-off route becomes a permanently growing fake receivable that discredits the whole ledger. | MED | **P2** |
| **GAP-20** | **Snapshot gap recovery** — list of missed capture slots + retro-pull from NVR recorded footage for the missed timestamp | Named as a mitigation in §10 but not as a feature. A missed 06:30 slot across a whole market is a day of under-billing that nobody can reconstruct later. | MED | **P2** |

---

### Differentiators (Competitive Advantage)

Against raqamli-bozor.uz (RealSoft: brand + AI + mobile app) and eBazaar (EverbestLab: transparent pricing + speed + modules).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Evidence-linked billing** — every charge opens onto the exact snapshot that justified it | Turns "the system says you owe" into "here is your stall at 07:00". This is what wins the argument with a vendor, the director, and an inspector. RealSoft advertises AI detection; nobody advertises *evidence attached to the invoice*. | MED (in spec) | The single most defensible feature. Make the snapshot one tap from every charge row, every debt line, every mismatch item. |
| **Same-day collection worklist driven by AI** (GAP-06) | Competitors' AI produces oversight. This produces **money today**. The pitch changes from "you'll see the leakage" to "you'll collect 23 more stalls before noon". | LOW-MED | Highest revenue-per-engineering-hour item in this document. |
| **Instant vendor push-receipt** (GAP-02) | Converts every vendor into a real-time auditor of every cashier — the control that cash-based municipal systems worldwide are documented to lack. | LOW | Also the cheapest way to hit the "≥60% vendors on the bot" success criterion: vendors join to get proof of payment, not to read reports. |
| **Honest AI accuracy report with random-sample ground truth** (GAP-15) | An accuracy number a customer can trust, published inside the product. Competitors claim AI; SBOZOR can *show precision and recall by camera, by hour*. Decisive in a tender where the buyer has been burned before. | LOW-MED | Requires GAP-15 to be meaningful. |
| **Mismatch hit-rate metric** (of flagged stalls, % confirmed on the ground) — from GAP-05 | Directly answers the buyer's real fear: "will your AI accuse honest vendors?" Utility fraud-detection programs live and die on this number. | LOW (given GAP-05) | Publish it. It is a trust artifact, not just an ops metric. |
| **Per-stall QR sticker** (cashier scans → payment screen; vendor scans → binds Telegram + sees own debt; controller scans → paid/unpaid today) | Kills stall-number typos, shortens the ≤3-tap flow further, and solves vendor bot onboarding at the point of payment. UzQR has already trained the entire country to scan codes at the point of sale. | LOW (+ printing ops) | Strong value per unit cost. Physical sticker production/lamination is a real onboarding task — put it in the wizard checklist. |
| **3-day market onboarding via wizard, with a published checklist** | eBazaar competes on speed; SBOZOR can make speed *measurable* and contractual (§9: ≤3 working days). | HIGH (in spec) | The wizard is the moat for the 500-market program, not the pilot. |
| **Transparent, modular pricing published on the site** | eBazaar's main marketing advantage; RealSoft's main weakness. Costs nothing to copy. | LOW (non-engineering) | Not a product feature but belongs in the same competitive frame. |
| **Bank-statement reconciliation import (v1.x)** — upload/ingest the market's bank/UzQR settlement file, auto-match to charges | Reaches cashless-collection assurance **without any merchant contract**, using the UzQR rail that is already legally mandatory and settles to the market's account within one business day with real-time data in the bank portal. Neither competitor advertises this path. | MED | See GAP-09. This is the cheapest credible answer to the state's "stop accepting cash" directive. |
| **Data-residency-ready deployment story** | Uzbek personal-data localization is a tender gate for the state phase. Docker Compose migration path is already the plan. | LOW (in spec) | Sales artifact more than code. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| # | Feature | Why Requested | Why Problematic | Alternative |
|---|---------|---------------|-----------------|-------------|
| **AF-01** | Free-form cashier amounts / ad-hoc discounts | "Every stall is a special case" | The single largest corruption vector in fee collection; destroys the reconciliation baseline the entire product rests on | Tariff-derived amount; override requires a reason code + audit entry (**already the spec's decision — defend it in every review**) |
| **AF-02** | Facial recognition / biometric vendor ID | Chorsu deployed face recognition; it demos impressively | Biometric data under Uzbek personal-data law, near-zero incremental revenue signal, and it reframes the product from "fee assurance" to "surveillance" in front of the people who must adopt it | Zone occupancy + phone-number identity + stall assignment. Detect *stalls*, not *faces*. |
| **AF-03** | Automatic fines / penalties issued straight from AI output | "Automate enforcement end-to-end" | AI flags in analogous domains confirm at roughly 60% on inspection. Auto-penalizing at that precision creates mass false accusations and one viral complaint ends the pilot | HITL confirmation → controller field check → recorded outcome (GAP-05). Humans issue consequences; AI issues *candidates*. |
| **AF-04** | Building a wallet / vendor balance top-up / own payment rails | "Then we own the money flow" | Regulated activity, merchant onboarding, KYC, float liability, reconciliation burden — for a 12-week MVP it is a project-killer | Record payments made on existing rails (cash / terminal / UzQR); reconcile from the bank statement (GAP-09) |
| **AF-05** | Full VMS: 24/7 recording, playback, PTZ, video search | "We already have cameras — put everything in one panel" | Duplicates the NVR the market already owns, and imports its storage, bandwidth and liability into the SaaS. Bandwidth over WireGuard from a district market is the binding constraint | Thin live-view proxy (go2rtc) + snapshot archive only. The NVR stays the system of record for video. |
| **AF-06** | Continuous / real-time occupancy inference | "Real-time is better" | Daily patta needs 7 frames, not 86,400. Continuous inference multiplies CPU cost on a GPU-less VPS and adds zero billing signal | Scheduled snapshots (per-market configurable), plus on-demand capture when a controller or cashier requests one |
| **AF-07** | Half-day / hourly proration of patta | "The vendor only traded 2 hours" | Creates an unbounded dispute surface and an obvious gaming strategy (arrive after the last snapshot). The market's own practice is full-day | Full daily patta on any occupied snapshot (**already decided**); handle genuine edge cases through the dispute flow (GAP-04) |
| **AF-08** | Auto-billing unassigned occupied stalls to a placeholder vendor | "Don't lose the revenue" | Creates uncollectible phantom receivables that poison every arrears report and every revenue number | "Unregistered trading" anomaly + on-the-spot vendor registration (**already decided — good**) |
| **AF-09** | Full offline-first cashier (local DB + bidirectional sync) | "What if the internet drops?" | Sync conflict resolution, duplicate payments, and stale tariffs — a large project that also breaks the real-time push receipt (GAP-02), the live worklist (GAP-06) and duplicate prevention (GAP-10). Karmana's internet is confirmed stable | **Offline-lite**: idempotency key + retry queue + explicit "pending / confirmed" state in the UI, so a payment is never lost or doubled during a 30-second dropout. Full offline stays in phase 2. |
| **AF-10** | Cashier leaderboard / gamified collection targets | "Motivate the cashiers" | Incentivizes pressure on vendors and inflated or coerced collection — the opposite of the product's stated purpose, and politically radioactive in an anti-corruption program | Neutral operational metrics: coverage %, variance history, override count, dispute rate |
| **AF-11** | Editable/deletable payment records | "The cashier made a typo" | Any editable money record makes the audit log decorative | Reversal + re-entry, both retained, both attributed (GAP-10) |
| **AF-12** | Generic AI chatbot / LLM assistant for vendors | "It's an AI product" | Vendors want four facts: what do I owe, did my payment land, when, and who took it. A chatbot adds latency, cost, hallucination risk and translation problems in three languages | Fixed bot commands + push notifications. No free-text LLM in v1. |
| **AF-13** | Heatmaps, footfall analytics, people-counting dashboards | Visually impressive in demos; the strategy doc lists them | Not tied to a billable event; consumes the same scarce CV effort that occupancy accuracy needs | Deferred (**already out of scope — keep it that way until occupancy is ≥95%**) |
| **AF-14** | Buyer-facing super-app in MVP | Named in the strategy doc as the leapfrog | Different user, different funnel, different retention problem. Ships nothing for "is patta fully collected?" and would consume the entire 12 weeks | Deferred (**already out of scope**). Revisit only after the pilot proves revenue lift. |
| **AF-15** | Dynamic / demand-based stall pricing, auctions | "Optimize revenue" | Fee rates in this segment are administratively set and politically sensitive; algorithmic pricing invites a scandal, not a tender win | Historical tariff versioning; optional day-of-week rates set by the administration (see v1.x) |
| **AF-16** | SMS as the primary vendor channel | "Not every vendor uses Telegram" | Per-message cost across 1000 vendors × daily reminders, plus aggregator contracts | Telegram first (**already decided**). Cover non-Telegram vendors with an assisted flow: cashier binds the vendor at the cash point, prints/hands the KKM receipt as before. Reconsider SMS only if bot adoption stalls below ~40%. |

---

## Feature Dependencies

```
Multi-tenant core + auth/roles
    └──requires──> nothing (foundation)

"New market" wizard (stalls, categories, tariffs, cameras)
    └──requires──> Multi-tenant core + auth/roles

Camera zones (polygons)
    └──requires──> Wizard (cameras registered) ──> Snapshot pipeline (reference frame)

Occupancy events
    └──requires──> Camera zones + detector + Frame quality gate [GAP-13]
    └──guarded by──> Camera view-drift detection [GAP-16]

HITL review queue
    └──requires──> Occupancy events
    └──must include──> Random-sample ground truth [GAP-15]  ← else accuracy report is invalid

AI accuracy report (§9 success criterion)
    └──requires──> HITL review queue + Random-sample ground truth [GAP-15]

Daily charge run
    └──requires──> Occupancy events + Tariffs + Stall→vendor assignment
    └──requires──> Non-trading day calendar [GAP-11]
    └──completed by──> Manual occupancy mode [GAP-07]   (covers the ~10% camera-blind stalls)

Payments (cashier)
    └──requires──> Stall registry + Tariffs + Payment integrity [GAP-10]
    └──requires──> Cashier↔zone assignment [GAP-08]

Live collection worklist [GAP-06]
    └──requires──> Same-day occupancy events + Payments + Cashier↔zone assignment [GAP-08]

Instant vendor push-receipt [GAP-02]
    └──requires──> Payments + Vendor Telegram binding + Notification governance [GAP-12]
    └──formatted by──> Digital receipt field set [GAP-03]

Shift reconciliation [GAP-01]
    └──requires──> Payments attributed to cashier + Shift entity
    └──enables────> Cash-handover accountability (closes the cash leak)

Mismatch report
    └──requires──> Daily charge run + Payments
    └──becomes useful via──> Mismatch case lifecycle [GAP-05]
    └──yields──────> Hit-rate metric (differentiator)

Dispute flow [GAP-04]
    └──requires──> Charges + Evidence snapshots + charge_adjustments + Audit log
    └──intake from──> Vendor bot AND Controller panel

Debt / arrears register
    └──requires──> Charges + Payments + Stall→vendor assignment
    └──policy from──> Aging + escalation + write-off [GAP-19]

Day close [GAP-17]
    └──requires──> Daily charge run
    └──enables────> Quotable historical reports, non-revisable ledger

Director digest + Mismatch report (bot)
    └──requires──> Daily charge run + Mismatch report + Notification governance [GAP-12]

Bank-statement reconciliation (v1.x)
    └──requires──> Payment method = QR/transfer + reference no. [GAP-09]
```

### Dependency Notes

- **AI accuracy report requires random-sample ground truth (GAP-15):** reviewing only `noaniq` cases measures the model exactly where it already knows it is unsure. The ≥90% / ≥95% success criteria in §9 are unverifiable without a random sample of *confident* predictions. Build this into the queue from day one — retrofitting it means the first two months of accuracy data are unusable.
- **Daily charge run requires the non-trading-day calendar (GAP-11):** charge generation must be suppressed at the source, not filtered out in reports afterwards, or reversals will litter the ledger.
- **Live worklist (GAP-06) requires cashier↔zone assignment (GAP-08):** an unsegmented list of 400 outstanding stalls is not a worklist, it is a wall.
- **Instant receipt (GAP-02) requires notification governance (GAP-12):** at 1000 vendors, unthrottled sends hit Telegram's ~30 msg/s bulk ceiling and start returning 429s — receipts would silently fail exactly when volume is highest (morning peak).
- **Dispute flow (GAP-04) requires evidence snapshots:** an appeal process with no evidence to show is a complaints inbox. The snapshot must be viewable by the vendor for their own stall and only their own stall (ties to GAP-18).
- **Shift reconciliation (GAP-01) conflicts with full offline mode (AF-09):** offline-created payments arriving after a shift close corrupt the variance calculation. Another reason to keep offline out of v1.
- **Half-day proration (AF-07) conflicts with "any occupied snapshot = full day":** the two billing rules cannot coexist; the full-day rule is already decided and the snapshot schedule is designed around it.
- **Manual occupancy (GAP-07) must be visibly separated from AI occupancy in every report:** mixing them makes the AI accuracy number meaningless and hides coverage regressions.

---

## MVP Definition

### Launch With (v1) — by 2026-10-18

Everything already in the §2 MVP scope, **plus these P1 gaps**:

- [ ] **GAP-01** Cashier shift open/close + blind cash declaration + variance + handover — *closes the cash leak the product exists to close*
- [ ] **GAP-02** Instant vendor push-receipt on payment — *highest anti-fraud value per hour of work; also drives bot adoption*
- [ ] **GAP-03** Receipt field set matching Uzbek market-receipt rules, labelled non-fiscal — *cheap now, expensive later*
- [ ] **GAP-04** Dispute flow (minimal: reason code, evidence, decision, adjustment, notify) — *no enforcement product survives without an appeal path*
- [ ] **GAP-05** Mismatch case lifecycle with owner, state, resolution reason — *converts the flagship report from a PDF into a process, and produces the hit-rate metric*
- [ ] **GAP-06** Live collection worklist by zone/row — *the mechanism that actually raises revenue*
- [ ] **GAP-07** Manual occupancy mode for camera-blind stalls — *~10% of Karmana is otherwise unbillable*
- [ ] **GAP-08** Cashier↔zone assignment + per-cashier stats — *accountability and prerequisite for GAP-01/06*
- [ ] **GAP-09** QR/bank-transfer payment method + mandatory reference for non-cash — *UzQR is already mandatory as of 2026-07-01*
- [ ] **GAP-10** Idempotent payments, duplicate detection, reversal-only corrections — *financial hygiene*
- [ ] **GAP-11** Non-trading day / holiday calendar — *one false holiday charge costs more trust than a month of accuracy*
- [ ] **GAP-12** Notification throttling, quiet hours, per-user language, delivery tracking — *Telegram limits are hard, not advisory*
- [ ] **GAP-13** Frame quality gate (darkness/blur → auto-`noaniq`) — *risk #1 in the spec's own risk table*
- [ ] **GAP-14** Role home screens with one headline number each — *nearly free, sets perceived quality*
- [ ] **GAP-15** Random-sample ground-truth audit — *without it the §9 accuracy criterion cannot be honestly measured*
- [ ] **GAP-16** Camera view-drift detection (at minimum: daily reference-frame diff + alert) — *silent total billing failure otherwise*

**Where to find the time.** Most of these are LOW complexity, but not free. Recommended trades inside the existing scope:

1. **Ship the plan-map schematically.** The spec's own risk table (§10) already flags the plan/polygon editor as the heaviest frontend work. The **camera-zone polygon editor is essential** (AI depends on it); the decorative uploaded-plan map with coloured stalls can ship as a grid/list view in v1 and become a real map in v1.1. Frees roughly a week of frontend.
2. **Ship 3 Excel exports, not 6.** Revenue, arrears register, mismatch archive. Occupancy dynamics, cashier breakdown and the AI accuracy report can be on-screen only in v1.
3. **No fine-tuning before launch.** Off-the-shelf detector + zone rules + HITL is the v1 plan already; treat fine-tuning as a post-launch activity fed by the HITL dataset (this is already the §4.5 intent — just don't let it slip into the 12 weeks).
4. **Live camera view stays** (customer-demanded) but strictly as a go2rtc proxy with role gating — no recording, no playback, no PTZ (AF-05).

### Add After Validation (v1.x) — weeks 13–24

- [ ] **GAP-17** Day close / period lock — *trigger: first month-end where a historical number gets questioned*
- [ ] **GAP-18** PII & image-access controls, consent records, per-vendor data export — *trigger: before the second market, mandatory before the state phase*
- [ ] **GAP-19** Arrears aging buckets, escalation ladder, write-off with approval — *trigger: when 30+ day debt exceeds ~10% of monthly charges*
- [ ] **GAP-20** Snapshot gap recovery from NVR recordings — *trigger: first multi-hour NVR outage*
- [ ] Per-stall QR stickers (cashier scan-to-collect, vendor scan-to-bind) — *trigger: cashier flow measured >3 taps or stall-number typos appear in the audit log*
- [ ] Bank-statement / UzQR settlement import + auto-matching — *trigger: non-cash share exceeds ~20%, or the administration is instructed to stop taking cash*
- [ ] Vendor self-registration request via bot with admin approval — *trigger: second market onboarding (registry entry is the bottleneck at 300–1000 stalls)*
- [ ] Day-of-week / seasonal tariff variants and exemption categories (imtiyoz) — *trigger: first market whose fee schedule isn't flat*
- [ ] Thermal receipt printing for vendors without Telegram — *trigger: bot adoption below ~40% at week 8 of the pilot*
- [ ] Full interactive plan-map with colour-coded stall states — *trigger: after v1 stabilizes; high demo value, low operational value*
- [ ] CV fine-tuning on Karmana data + per-camera accuracy breakdown — *trigger: baseline accuracy measured over 2–4 weeks*
- [ ] Sandbox/demo market with synthetic data for sales — *trigger: first competitive tender*

### Future Consideration (v2+)

- [ ] Shop rentals / annual contracts (do'kon ijarasi) — *parity module both competitors sell; different billing model (monthly, due by the 25th), needs contract lifecycle. Defer: the pilot's question is about patta.*
- [ ] Parking / ANPR, livestock market, toilets — *parity modules; each is a separate CV problem and a separate revenue stream. Defer: they dilute the one number the pilot must move.*
- [ ] Online payment via Payme/Click merchant or direct UzQR-linked settlement — *defer merchant contracts; the statement-import path (v1.x) delivers most of the assurance value with none of the contracting delay*
- [ ] OFD / fiscal receipt integration (online KKM / virtual kassa) — *strategically important and eventually mandatory-adjacent; a state-phase gate rather than a pilot feature. Design GAP-03's field set so this is a swap.*
- [ ] E-bozor / tax authority data exchange — *tender-decisive at the state phase; requires published integration specs*
- [ ] Offline cashier mode — *only if a second market has genuinely poor connectivity; see AF-09*
- [ ] Buyer super-app, loyalty, pre-orders — *strategic leapfrog, but an entirely different product; see AF-14*
- [ ] Heatmaps, footfall, price monitoring — *see AF-13; price monitoring may become a state requirement, watch it*
- [ ] Stall booking / allocation transparency + waitlist — *the Chorsu review specifically flagged favouritism in stall allocation, so there is real demand here*

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Instant vendor push-receipt (GAP-02) | HIGH | LOW | **P1** |
| Live collection worklist (GAP-06) | HIGH | LOW-MED | **P1** |
| Cashier shift + cash reconciliation (GAP-01) | HIGH | MED | **P1** |
| Mismatch case lifecycle + hit rate (GAP-05) | HIGH | MED | **P1** |
| Random-sample ground truth (GAP-15) | HIGH | LOW | **P1** |
| Payment integrity: idempotency/reversal (GAP-10) | HIGH | LOW | **P1** |
| Non-trading day calendar (GAP-11) | HIGH | LOW | **P1** |
| Manual occupancy for blind stalls (GAP-07) | HIGH | LOW-MED | **P1** |
| Dispute flow (GAP-04) | HIGH | MED | **P1** |
| Notification governance (GAP-12) | MED-HIGH | LOW-MED | **P1** |
| Frame quality gate (GAP-13) | MED-HIGH | LOW | **P1** |
| Camera view-drift detection (GAP-16) | HIGH | MED | **P1** |
| Cashier↔zone assignment + stats (GAP-08) | MED-HIGH | LOW | **P1** |
| QR/transfer payment method + reference (GAP-09) | MED-HIGH | LOW | **P1** |
| Receipt field set (GAP-03) | MED | LOW | **P1** |
| Role home screens (GAP-14) | MED | LOW | **P1** |
| Day close / period lock (GAP-17) | MED | LOW-MED | P2 |
| Arrears aging + escalation (GAP-19) | MED-HIGH | MED | P2 |
| PII / image access controls (GAP-18) | MED | LOW-MED | P2 |
| Per-stall QR stickers | MED-HIGH | LOW (+ops) | P2 |
| Bank-statement reconciliation import | HIGH (state phase) | MED | P2 |
| Vendor self-registration via bot | MED | LOW | P2 |
| Snapshot gap recovery (GAP-20) | MED | MED | P2 |
| Day-of-week / seasonal tariffs, exemptions | MED | LOW-MED | P2 |
| Thermal receipt printing | LOW-MED (conditional) | MED | P2 |
| Full interactive plan-map | LOW (demo: HIGH) | HIGH | P2 |
| CV fine-tuning + per-camera accuracy | MED | MED-HIGH | P2 |
| Shop rentals module | HIGH (market parity) | HIGH | P3 |
| Parking / ANPR, livestock, toilets | MED (parity) | HIGH | P3 |
| OFD / fiscal integration | HIGH (state phase) | HIGH | P3 |
| E-bozor integration | HIGH (tenders) | HIGH | P3 |
| Buyer super-app | LOW (now) | VERY HIGH | P3 |
| Heatmaps / footfall / price monitoring | LOW | MED | P3 |

**Priority key:** P1 = must ship by 2026-10-18 · P2 = weeks 13–24 · P3 = after product-market fit / state phase

---

## Competitor Feature Analysis

| Feature | raqamli-bozor.uz (RealSoft) | eBazaar (EverbestLab) | SBOZOR approach |
|---------|------------------------------|------------------------|-----------------|
| Stall occupancy detection | Advertised: cameras detect stall occupancy **and product type** — headline differentiator | Not advertised (ML engineer on team, no CV claim) | Core product, with **evidence snapshot attached to every charge** and a published accuracy report |
| Daily patta billing | Yes | Yes ("Rastalar" module, 16.25M so'm setup / 4M so'm per month) | Yes + occupancy-derived expected-vs-collected reconciliation |
| Shop rental / contracts | Yes, incl. **automatic contract generation** and per-tenant accounts | Yes ("Do'konlar" module) | **Deferred to v2** — deliberate narrowing |
| Parking / ANPR | Yes (camera entry/exit, e-payments, reports) | Yes (module, 9.75M / 1M) | Deferred to v2 |
| Livestock market / toilets | Not broken out publicly | Yes, separately priced modules | Deferred to v2 |
| Vendor mobile app | Yes, iOS + Android; online payment by card/mobile/QR; balance, debt, auto-reminders | Not emphasized (web-first) | **Telegram bot instead of an app** — faster to ship, no store review, matches local channel habits; app only if the pilot demands it |
| Online payment | Yes (card, mobile, QR) | Implied via modules | **Deferred**; cashier records cash/terminal/QR. Bridge via bank-statement reconciliation (v1.x) rather than merchant contracts |
| Pricing transparency | Closed (on request) | **Published per module** | Publish per-module pricing — neutralize eBazaar's main advantage at zero engineering cost |
| Interface language | Cyrillic-dominant (+ latin/ru/en) | Latin-dominant (+ ru), dark mode | uz-latin primary + uz-cyrillic + ru, one-tap switch |
| Reference customers | Large projects, generically stated | Named: Olot, Romitan, Jondor (Buxoro), Saxovat (Navoiy) | Karmana pilot with a **measured pre-digitization revenue baseline** — a stronger reference than a logo |
| Cashier cash accountability | Not advertised | Not advertised | **Shift reconciliation + instant vendor receipt (GAP-01, GAP-02)** — an unclaimed gap in both competitors, and the one the state cares about most |
| Dispute / appeal handling | Not advertised | Not advertised | Explicit dispute flow (GAP-04) — required once you accuse people with a camera |
| AI accuracy transparency | Claimed, not quantified publicly | n/a | Published precision/recall + mismatch hit rate — verifiable claims beat louder claims |

**Competitive read.** Feature parity across the module grid is *not* achievable in 12 weeks and should not be attempted. Both competitors are broad and shallow on assurance; SBOZOR should be narrow and deep: one market, one question, provable numbers, and the cash-accountability controls neither advertises. Module breadth is a v2 sales problem, and the wizard is what makes it cheap when it arrives.

---

## Regulatory constraints that behave like features

These are not optional product decisions — they shape the feature set and belong in requirements. **Legal review by an Uzbek specialist is required before launch; the findings below are from primary legal-portal sources read through automated summarization (MEDIUM-HIGH confidence).**

| Constraint | Source | Feature implication |
|------------|--------|---------------------|
| Market fee receipts must carry: market name, date/time, payment name, amount, **stall number**, **product name**, KKM/terminal number; on online-KKM markets also **QR code + fiscal mark** | lex.uz 2185 (27.01.2011, in force); tax guidance on online NKM/virtual kassa | GAP-03: mirror the field set in the digital receipt; label it non-fiscal until OFD integration exists |
| Vendors must be able to present a payment receipt during inspections and keep it through the trading day | lex.uz 2185, art. 14 | Vendor-side receipt must be retrievable offline-ish (a Telegram message satisfies this in practice); consider a per-stall "paid today" QR check for controllers |
| Payments must be taken via fiscal-memory KKM, online KKM or virtual kassa; terminal receipt accompanies card payments | lex.uz 253 (28.08.2012) + tax rules | The cashier will run **two systems in parallel** (KKM + SBOZOR) until OFD integration. Design for it: mandatory receipt-number capture, and a later KKM-vs-SBOZOR reconciliation report |
| **UzQR unified national QR is mandatory for legal entities in trade/services from 2026-07-01**; absence = trading-rules violation. Static QR, UZCARD/HUMO only, 0.65% commission, settles to merchant account within ~1 business day, transaction data visible in the bank portal in real time | Central Bank of Uzbekistan; press coverage Dec 2025 / Jul 2026 | GAP-09 (record QR payments) now; statement reconciliation in v1.x. This is a **cheaper path to cashless assurance than Payme/Click merchant contracts** |
| Markets with 100+ permanent stalls were required to collect one-time fees and rent through the banking system in real time; tax authorities verify daily | Draft/regulation coverage on the unified E-BOZOR platform | Karmana (~300–1000 stalls) is in scope. Cash-first collection is a **compliance-risk story to raise with the customer explicitly**, not a silent assumption |
| Anti-corruption review of Chorsu recommended **discontinuing acceptance of cash payments** | anticorruption.uz review of Chorsu digitization | The strategic direction is cashless. Position MVP cash handling as a transitional phase with a dated migration plan — do not let it become the product's identity |
| Vendor PII (name, phone) + camera imagery fall under Uzbek personal-data localization law | Already noted in spec §5 | GAP-18; plus the on-site "video surveillance in progress" signage and a data-use agreement with the administration (already in spec) |

---

## Open Questions for the Customer

Answering these changes feature scope, so they should be resolved before roadmapping:

1. **Does Karmana currently operate an online KKM / virtual kassa for patta?** If yes, the double-entry burden on the cashier is real from day one and receipt-number capture must be mandatory. If no, the market may be non-compliant already and SBOZOR is walking into that conversation.
2. **Does the market already have a UzQR code, and at which bank?** Determines how soon statement-import reconciliation becomes possible.
3. **Who physically holds the cash between collection and banking today, and how often is it banked?** Determines the shape of GAP-01 (per-shift handover vs daily drop).
4. **Are there fee exemptions (imtiyoz) or day-of-week rates at Karmana?** Determines whether the flat category→tariff model is sufficient for v1.
5. **Can one stall be traded by different vendors at different times (morning/evening, day-sharing)?** If yes, the single `stall_assignment` model needs a time dimension, and "unregistered trading" false positives will spike.
6. **What share of vendors have a smartphone with Telegram?** Directly determines whether the ≥60% adoption target and the push-receipt control (GAP-02) are achievable, or whether printed receipts (v1.x) become P1.
7. **Who owns the resolution of a mismatch item — controller, market admin, or director?** Determines the default assignment rule in GAP-05.

---

## Sources

**Primary / high confidence**
- Telegram Bot API FAQ — rate limits: ~1 msg/s per chat, 20 msg/min in groups, ~30 msg/s bulk broadcast, 429 beyond — https://core.telegram.org/bots/faq (HIGH)
- lex.uz 2185 (27.01.2011, current version) — order for collecting one-time fees, rental and service payments in markets; receipt content; trader obligations — https://www.lex.uz/ru/docs/-1737637 (HIGH for existence; MEDIUM-HIGH for detail via summarization)
- lex.uz 253 (28.08.2012) — additional measures regulating markets and trade complexes; numbered trading places, posted layout scheme, KKM requirements — https://lex.uz/docs/-2045196 (HIGH / MEDIUM-HIGH)
- Central Bank of Uzbekistan — UzQR unified national QR system, commission structure — https://cbu.uz/uz/press_center/news/4038001/ (HIGH)
- Spot.uz — UzQR mandatory from 2026-07-01, static QR, UZCARD/HUMO only, 0.65%, ~1 business day settlement, real-time data in merchant bank portal — https://www.spot.uz/oz/2026/07/02/qr-code/ (MEDIUM-HIGH)
- Anticorruption.uz — review of Chorsu market digitization: Click bozor app, LPR + facial recognition cameras, recommendation to discontinue cash acceptance, concern over stall-allocation favouritism — https://anticorruption.uz/oz/article/chorsu-dehqon-bozorida-raqamlashtirish-jarayonlari-organildi (MEDIUM-HIGH)
- Norma.uz — unified E-BOZOR platform: markets with 100+ permanent stalls, banking-system collection in real time, daily tax verification — https://www.norma.uz/oz/nhh_loyihalari/yagona_e-bozor_elektron_platformasini_joriy_qilish_rejalashtirilmoqda (MEDIUM-HIGH)

**Competitor analysis**
- `Raqamli-bozor_vs_eBazaar_tahlil.docx` (in-repo, live site review 2026-06-28) — feature and pricing breakdown for both competitors (MEDIUM-HIGH; competitor sites are login-gated, so features come from marketing pages)
- `Golib-strategiya_va_yol-xaritasi.docx` (in-repo) — four-pillar differentiation strategy (used here as input, and partly challenged: super-app and full-module parity are anti-features for this MVP)
- ebazaar.everbestlab.uz — re-checked 2026-07-28: public site now shows only a login page; feature/pricing detail no longer publicly verifiable (LOW — relying on the June review)
- raqamli-bozor.uz — re-checked 2026-07-28: no fetchable public content (LOW — relying on the June review)

**Adjacent-domain patterns**
- Manage My Market — market-manager feature set: vendor applications with approve/decline/**waitlist**, stall assignments, invoicing, payment receipts, per-vendor accounts, financial reports, license compliance tracking, targeted email with delivery history — https://managemymarket.com/ (MEDIUM)
- MarketWurks, MarketSpread, VIBEPro — farmers-market software: live visual layout map with conflict detection, reusable weekly layouts, integrated fee/deposit/refund processing, "who paid / who owes" dashboards (MEDIUM, via search summaries)
- CountyERP Revenue Collection System — municipal analog: revenue-stream management, arrears & collections, **market & parking fee management**, instant receipts for every transaction, compliance & audit module, real-time dashboards, role-based access — https://countyerp.com/products/revenue-collection-system/ (MEDIUM)
- The Chanzo (Tanzania) — "cosmetic digitisation": leakage persists wherever officers collect cash and transactions can originate outside the platform — https://thechanzo.com/2026/05/05/cosmetic-digitisation-how-cash-and-discretion-undermine-tanzanias-revenue-systems (MEDIUM)
- The Star (Kenya) — Muthurwa Market: collectors take daily fees in cash, promise to key them in later — https://www.the-star.co.ke/news/2023-12-19-how-nairobi-is-losing-revenue-collected-at-muthurwa-market (MEDIUM)
- Adomonline (Ghana) — fake revenue collectors issuing forged receipts to traders — https://www.adomonline.com/fake-tax-collectors-bleed-accra-traders-dry/ (MEDIUM)
- Retail cash-handling SOPs — opening float verification, drawer drops, **blind counting to avoid confirmation bias**, signed Z-report per shift, variance investigation via transaction/drop/audit logs, flagging voids and no-sales without manager override — https://www.xenia.team/daily-ops-checklists/cash-handling-procedures-retail, https://nrsplus.com/blog/cash-drawer-reconciliation/ (MEDIUM)
- Parking enforcement / citation lifecycle — digital issuance, auto-attached photo/time/GPS evidence, structured appeal with full evidence record, collections and repeat-offender tracking; "evidence quality determines whether disputed violations are upheld or voided" — https://operationscommander.com/blog/parking-enforcement-software-what-actually-matters/, https://parkingprofessional.com/technology/parking-citation-management-software/ (MEDIUM)
- Revenue assurance practice — exception queues with named owners, SLAs per queue, case lifecycle with required evidence and communication templates, leakage-trend dashboards — https://umbrex.com/resources/frameworks/pricing-frameworks/revenue-assurance-frameworks/, https://www.subex.com/revenue-assurance/ (MEDIUM)
- Human-in-the-loop CV practice — confidence thresholds as the review trigger, queue sizing and SLAs, giving reviewers full context (image + prediction + confidence + alternatives), corrections feeding retraining, active learning on decision-boundary samples — https://www.docsumo.com/blog/human-in-the-loop-systems, https://encord.com/blog/human-in-the-loop-ai/, https://www.sciencedirect.com/science/article/abs/pii/S0952197623005602 (MEDIUM)
- Utility non-technical-loss detection — AI-flagged sites confirmed on inspection in roughly 60% of cases; false positives impose real field-inspection cost and customer-trust cost — https://www.mdpi.com/1996-1073/13/18/4727 (MEDIUM)
- Offline field-collection apps — offline capability described as non-negotiable where connectivity is absent for days; store-and-sync patterns — https://principa.co.za/mobile-collector-apps-with-offline-capability-for-field-collectors-in-africa-are-a-non-negotiable/ (MEDIUM; **not** applicable to Karmana, where internet is confirmed stable — cited as the counter-evidence behind AF-09)
- Click SuperApp — offline QR acceptance (Tez QR / Click Sado); "Click bozor" used at Chorsu for stall rental and cashless payment — https://click.uz/uz/system-description-and-capabilities (MEDIUM)

**Confidence caveats**
- Competitor feature lists come from marketing pages, not product access; both portals are login-gated. Treat the parity table as directional.
- Uzbek legal requirements were read via automated summarization of lex.uz pages. Directionally reliable, but **exact receipt fields and fiscal obligations must be confirmed by a local specialist before launch.**
- No primary user research with Karmana vendors, cashiers or controllers was available. Gaps GAP-01 through GAP-08 are inferred from analogous domains and should be validated in the 2–4 week parallel-run period — that period is the cheapest possible test of every assumption in this document.

---
*Feature research for: bazaar / market revenue-management SaaS (Uzbekistan)*
*Researched: 2026-07-28*
