# Pitfalls Research

**Domain:** AI-camera revenue assurance / traditional-market (bozor) digitization SaaS — multi-tenant, CPU-only CV, cash-collection reconciliation
**Project:** SBOZOR (Karmana pilot, ~300–1000 rasta, ~20–25 Hikvision cameras, 12 weeks, 3 people)
**Researched:** 2026-07-29
**Confidence:** MEDIUM-HIGH (see per-pitfall confidence tags)

> **Til eslatmasi:** bu fayl texnik aniqlik uchun ingliz tilida yozilgan; domen atamalari (rasta, patta, nazoratchi, nomuvofiqlik, band/bo'sh/noaniq) o'zbekcha saqlangan.

## Phase Vocabulary Used Below

Mapped to the 12-week plan in `SBOZOR-MVP-texnik-topshiriq.md` §8:

| Label | Weeks | Content |
|-------|-------|---------|
| **P0 — Foundation** | 1–2 | Repo, Docker, CI, data model, auth/roles, design system, i18n scaffold |
| **P1 — Wizard & Master Data** | 3–4 | Bozor wizard, plan, rastalar, tariffs, camera zones (polygons) |
| **P2 — Capture Pipeline** | 5–6 | NVR/VPN, snapshots, MinIO, go2rtc live view |
| **P3 — CV + HITL** | 7–8 | Detector, occupancy events, nazoratchi queue |
| **P4 — Billing & Cashier** | 9–10 | daily_charges, adjustments, payments, debts, audit |
| **P5 — Bots** | 11 | Sotuvchi bot, direktor dayjest, nomuvofiqlik hisoboti |
| **P6 — Reports & Launch** | 12 | Reports, Excel, 3 languages, go-live |
| **P7 — Parallel Run** | +2–4 wks | Parallel rejim, accuracy proof, baseline comparison |
| **PF — Field Track** | 1 → ongoing | NVR credentials, VPN, coverage audit, **baseline revenue measurement** (runs in parallel with P0–P2) |

---

## Critical Pitfalls

### Pitfall 1: The entire morning capture window is in darkness from November onward

**Confidence:** HIGH (astronomical data verified)

**What goes wrong:**
The billing rule is "band in any snapshot → full daily patta", and 5 of the 7 snapshot slots are 06:00–08:00. Verified sunrise times for Navoi (40.11°N, 65.35°E, UTC+5):

| Month | Sunrise (Navoi) | Snapshot slots before sunrise |
|-------|-----------------|-------------------------------|
| October (go-live) | ~06:55 | 06:00, 06:30 (07:00 = at sunrise, low sun) |
| November | ~07:30 | 06:00, 06:30, 07:00 |
| December | ~07:58 | 06:00, 06:30, 07:00, 07:30 — and 08:00 is at sunrise |
| January | ~07:56 | same as December |

So the pilot goes live (18 Oct) with 2 dark slots and, by the time the "≥95% accuracy in month 2" criterion is measured (late November / December), **4–5 of the 5 morning slots are dark or deep twilight**. Frames will be IR-illuminated grayscale (or noisy near-black), where a COCO-pretrained RGB detector degrades severely — and market activity starts before sunrise regardless of the sun.

**Why it happens:**
The schedule was set on 2026-07-28 (summer, sunrise ~05:15) by observing actual market rhythm. Nobody projected the schedule against the seasonal solar curve. The spec's risk table mentions "early morning light in autumn/winter" but treats it as a minor mitigation ("check IR mode"), not as a structural problem that removes the majority of billing evidence for a third of the year.

**How to avoid:**
1. **Make the snapshot schedule seasonal per market, in the data model, from P0.** `snapshot_schedules` should be a set of rules with validity dates, not 7 hardcoded times. Winter profile: shift morning slots later (e.g. 07:00, 07:30, 08:00, 08:30, 09:00) and/or add an extra midday slot.
2. **Classify every frame at ingest as `day | twilight | ir | dark`** (mean luma + colour saturation ≈ 0 ⇒ IR/monochrome). Store on `snapshots.light_mode`. Never let a `dark` frame produce a `bo'sh` result that reduces someone's bill or a `band` result that raises it — route it to `noaniq` or exclude it.
3. **Verify IR range in P2, physically.** Bazaar cameras are often mounted 4–8 m up covering 20–40 m; typical NVR camera IR reaches 20–30 m and only lights the near field. Do a night walk-through with the market's camera before drawing 1000 polygons on frames that are useless half the year.
4. **Collect IR/twilight frames into the fine-tuning set from day one of P2** — they are the hardest and most valuable training data, and you only get October–December once before the accuracy review.

**Warning signs:**
- Occupancy % broken down by slot shows the 06:00 slot far below the 08:00 slot (in reality the market is fuller at 07:00 than at 08:00).
- `noaniq` rate for slot 1 climbing week-over-week through October–November.
- Detector confidence histogram for the first slot collapsing toward the threshold.

**Phase to address:** P0 (schedule as data, `light_mode` column), P2 (physical IR verification + frame classification), P3 (separate decision path per light mode), re-verified explicitly at P7.

---

### Pitfall 2: ffmpeg RTSP capture hangs and silently deletes days of billing evidence

**Confidence:** HIGH (FFmpeg source/mailing lists + Hikvision docs)

**What goes wrong:**
`ffmpeg -i rtsp://... -frames:v 1 out.jpg` with no timeout blocks **forever** when the NVR reboots, the VPN flaps, or the stream stalls. The process never returns, the scheduler slot is consumed, and no error is raised — snapshots simply don't exist. Missing snapshots = missing `band` evidence = under-billing = the "tushum o'sdi" ROI argument evaporates, and nobody notices because nothing errored.

Three compounding traps:
- **`-stimeout` no longer exists.** It was deprecated then removed (`stimeout` → `timeout`); FFmpeg 8 rejects it. Every StackOverflow answer and blog post from 2018–2022 uses `-stimeout`. If it's rejected, ffmpeg errors out; worse, if you put it after `-i`, it's silently ignored and you're back to infinite hang.
- **The RTSP demuxer's timeout only covers socket I/O**, not "stream connected but sending nothing". A half-open TCP session survives.
- **First-frame corruption.** Starting mid-GOP on an H.264/H.265 stream yields green/grey/partial frames until the first keyframe. `-frames:v 1` can capture exactly that garbage frame — a grey rectangle that the detector will confidently call `bo'sh`.

**How to avoid:**
1. **Prefer the Hikvision ISAPI still-image endpoint over RTSP for snapshots:**
   `GET http://<nvr>/ISAPI/Streaming/channels/<CH>01/picture` with **HTTP Digest** auth (channel numbering: `101` = cam 1 main, `102` = cam 1 sub, `201` = cam 2 main …). Optional `?videoResolutionWidth=…&videoResolutionHeight=…`.
   This returns a JPEG directly: no RTSP session, no GOP wait, no decode, no green frames, no session-limit pressure, and a plain HTTP timeout works. It is dramatically more reliable and cheaper on a CPU-only VPS. Verify it against the actual Karmana NVR firmware in **week 1–2 of PF**, not week 5.
2. **Keep ffmpeg as fallback only**, and make it uncrashable:
   - options *before* `-i`: `-rtsp_transport tcp -timeout 5000000 -analyzeduration 1000000 -probesize 500000`
   - discard broken frames: `-fflags +discardcorrupt`
   - hard OS-level kill: run via `subprocess` with `timeout=15`, `start_new_session=True`, and on timeout `os.killpg(...)` — a bare `proc.kill()` leaves ffmpeg children alive.
3. **Snapshot validity gate before the frame is accepted:** decoded size matches expected, file > N KB, colour variance > threshold, not a uniform grey/green plane. A rejected frame retries; a twice-rejected frame becomes an explicit `capture_failed` row, not silence.
4. **Every scheduled slot must produce a row** in `snapshots` — `ok` or `failed` with reason. "No row" is unrepresentable. Alert on any camera with 2 consecutive failures.

**Warning signs:**
- Zombie/defunct `ffmpeg` processes accumulating in the cv-service container.
- Capture job wall-clock time with high variance (p99 ≫ p50).
- Days where `count(snapshots) < cameras × slots`.
- Detector output for one camera flips to 100% `bo'sh` overnight.

**Phase to address:** PF (week 1–2 ISAPI feasibility test), P2 (implementation + validity gate + alerting).

---

### Pitfall 3: Person-detection used as the definition of occupancy

**Confidence:** MEDIUM-HIGH (retail CV literature + domain reasoning)

**What goes wrong:**
"Band" gets implemented as "a `person` box overlaps the polygon". Four failure modes, all of which cost money or trust:

| Situation | Detector says | Reality | Cost |
|---|---|---|---|
| Vendor stepped away for tea / praying / loading | bo'sh | band | Under-charge (mitigated by "any-snapshot" rule, but only if another slot catches them) |
| Buyer or passerby standing in the walkway in front of the stall | band | that stall may be empty | **Over-charge → dispute → the one outcome the spec explicitly wants to avoid** |
| Neighbouring vendor stands over the boundary | band (wrong stall) | wrong stall billed | Over-charge + wrong-person accusation |
| Goods laid out, vendor briefly out of frame | bo'sh | band | Under-charge |

**Perspective distortion makes this structurally worse.** Polygons are drawn in the image plane, but people stand on the ground plane. From a camera 5 m up looking down a row, a person standing in front of stall A occupies pixels that fall inside stall B's polygon (the person's body extends *upward* in the image, toward the stalls behind them). With 1000 stalls in tight rows this is not an edge case, it is the normal case.

**Why it happens:**
`person` is the class every pretrained COCO model gives you for free, and the demo works beautifully on a clean test frame with one person. The failure only appears at density, at oblique angles, and in a crowded bazaar with occlusion.

**How to avoid:**
1. **Define occupancy as goods/structure presence, not human presence.** The physical signal that a rasta is trading is: covered counter surface, boxes/crates/produce, umbrella/tarp deployed. That is the thing that persists across all 7 snapshots. Person presence becomes a *supporting* signal, not the definition.
2. **Draw polygons on the counter/table surface, not on the walkway** — a wizard rule and an onboarding instruction, enforced by an editor hint. Keep polygons tight; do not include the aisle.
3. **Require corroboration for auto-charge.** The spec's "any snapshot band → full day" is safe against under-detection but *maximally* exposed to a single false positive. Change to: auto-charge if **≥2 snapshots** say `band`, OR 1 snapshot with high confidence *and* goods signal. A single isolated `band` in an otherwise empty day → `noaniq` queue, not a bill.
4. **Use the counter-line trick for perspective:** for each zone, also store a "front edge" line; a person box whose *feet* (box bottom centre) fall outside the zone but whose body overlaps it should not count as occupancy for that zone. This is cheap and removes most cross-row bleed.
5. **Small-object reality check.** At 640×360 substream, a stall 30 m away is a handful of pixels. Capture main stream and, if the smallest zones are < ~32 px on a side after resize, use tiled/sliced inference (SAHI-style: overlapping crops at native resolution, merge with NMS) — reported to add ~5–7 AP for small objects. Budget the CPU: RT-DETR-class models measure ~70 ms @320px to ~285 ms @960px on Intel CPU; tiling multiplies that by the tile count. 25 cams × 7 slots × 9 tiles × 0.3 s ≈ 8 minutes/day — fine. Live/real-time inference is *not* fine, and is not required. Do not drift into it.

**Warning signs:**
- Disputes cluster on stalls adjacent to busy walkways.
- Occupancy % > 95% for a whole camera (you're detecting shoppers).
- Zones with `band` at 06:00 and `bo'sh` at 07:00 and 07:30 (a passerby, not a vendor).
- Detected `band` for stalls the market admin knows are permanently closed.

**Phase to address:** P1 (polygon-drawing rules, front-edge line in `camera_zones`), P3 (occupancy definition, corroboration rule, tiling).

---

### Pitfall 4: Measuring AI accuracy from the nazoratchi queue (selection bias + circular validation)

**Confidence:** HIGH (ML evaluation literature + automation-bias studies)

**What goes wrong:**
The MVP success criterion is "AI bandlik aniqligi ≥ 90% (nazoratchi tasdiqlariga nisbatan)". As specified, the only items a nazoratchi sees are the `noaniq` ones. So:

- **Selection bias:** you compute accuracy on the hardest ~10% of cases and on nothing else. The confident-but-wrong cases — the ones that actually generate wrong bills — are *never measured*. Uncertainty-sampled evaluation is documented to invert conclusions relative to reality.
- **Circular validation / automation bias:** the reviewer sees the AI's answer before forming their own. Radiology studies found inexperienced reviewers' accuracy collapsed from ~80% to under 20% when the AI was wrong; experienced reviewers fell from 82% to 45%. Your "AI vs human" number becomes "AI vs a human anchored on AI" — it converges to ~100% and means nothing.
- **Base-rate illusion:** if 75% of rastalar are occupied on a working day, a model that always answers "band" scores 75% accuracy. 90% is barely above trivial. Accuracy is the wrong metric.

You can pass the contractual criterion with a system that is systematically wrong, and only find out when vendors revolt.

**How to avoid:**
1. **Two separate queues.** (a) `noaniq` operational queue — for resolving today's billing. (b) **Blind random audit queue** — N items/day (e.g. 50) sampled uniformly from *all* results including high-confidence ones, presented **with the AI answer hidden** until the reviewer commits. Accuracy is reported *only* from queue (b).
2. **Report a confusion matrix, not accuracy.** Precision and recall for `band`, and the two error counts that map directly to money: *false band* (over-charge, causes disputes) and *false bo'sh* (revenue leak). Track them as separate KPIs with separate targets — they have completely different business costs.
3. **Gold-standard items.** ~2% of both queues are pre-labelled items with a known answer, injected invisibly. Reviewer accuracy on gold items is the reviewer-quality metric.
4. **Stratify the audit sample** by light_mode, camera, and time slot. Otherwise the December IR collapse (Pitfall 1) hides inside an average.
5. **Renegotiate the success wording now, in P0**, to "≥90% recall on `band` and ≥95% precision on `band`, measured on a blind random audit sample" — before it's a contractual number attached to the wrong statistic.

**Warning signs:**
- Accuracy report reads > 98% in the first week.
- Reviewer–AI agreement rate = 100%.
- The accuracy report's denominator equals the size of the `noaniq` queue.

**Phase to address:** P3 (both queues, blind mode, confusion matrix), P6 (accuracy report), P0 (renegotiate the criterion wording).

---

### Pitfall 5: Reviewer fatigue — the HITL queue is arithmetically impossible

**Confidence:** HIGH (HITL/oversight-fatigue literature)

**What goes wrong:**
1000 rastalar × 7 snapshots = **7 000 zone decisions per day**. At a realistic early-model uncertainty rate of 15–25%, the `noaniq` queue is **1 000–1 750 items/day**. A nazoratchi working 60 focused minutes can honestly judge maybe 150–250. The rest get bulk-approved.

Documented consequence: reviewers anchor on the first few items, scrutiny decays as the queue grows, and "approve" becomes the path of least resistance — while the audit log records a human decision on every single one. You end up with a legally defensible paper trail attached to labels nobody actually looked at, and a fine-tuning dataset poisoned with rubber-stamped noise (which then makes the model worse, permanently).

**How to avoid:**
1. **Cap the queue by design.** The queue has a daily budget (e.g. 200 items). Items above the budget do not silently pass — they fall to the safe default (`bo'sh`, per the spec's own rule) and are counted in a visible "unreviewed" number on the director's report. The unreviewed count is the honest signal that the model needs work; hiding it is the failure.
2. **Prioritise by money and consequence, not by chronology.** Rank the queue: (a) uncertain + assigned vendor + would-create-a-charge, (b) uncertain + would-create an "unregistered trade" anomaly, (c) everything else. A nazoratchi reviewing 200 well-chosen items beats one reviewing 1 000 random ones.
3. **Design the review UI for 3–5 seconds per item**: crop + context frame side by side, keyboard `1/2/3` = band/bo'sh/skip, no mouse, no page reload, grouped by camera so the eye stays calibrated.
4. **Instrument the reviewers.** Log per-item decision latency. Alert if a reviewer's median drops below ~2 s or if they produce a run of >30 identical decisions. Show each reviewer their own gold-item accuracy — visibility alone reduces rubber-stamping.
5. **Never bulk-approve.** No "confirm all on this page" button. It is the single feature that converts HITL into theatre.
6. **Only reviewed-and-disagreed items enter the fine-tuning set** with high weight; rubber-stamp-suspect items (latency < 1 s) are excluded from training.

**Warning signs:** median review latency falling; queue depth growing monotonically; a nazoratchi clearing 800 items in 20 minutes; fine-tuned model performing *worse* than the base model.

**Phase to address:** P3 (queue budget, prioritisation, latency instrumentation, no bulk-approve).

---

### Pitfall 6: Charges are mutable rows — reconciliation and disputes become unwinnable

**Confidence:** HIGH (ledger/reconciliation practice)

**What goes wrong:**
`daily_charges` is treated as "today's computed amount" and gets `UPDATE`d when a nazoratchi confirms late, when a tariff is corrected, when CV is re-run, or when a bug is fixed. Consequences:
- A payment already taken against the old amount no longer reconciles.
- The vendor's Telegram bot showed 15 000 so'm yesterday and 20 000 today with no explanation → trust destroyed.
- "Why do I owe this?" has no answer, because the row that generated the debt no longer exists in its original form.
- Any re-run of CV over historical snapshots silently rewrites months of financial history.

**Why it happens:**
The daily charge *feels* like a derived value, so recomputing it feels natural — especially when the spec says the day's final bill is produced at end of day. The trap is that it stops being derived the moment a human sees it or pays against it.

**How to avoid:**
1. **`daily_charges` is append-only and immutable once `status = finalized`.** Corrections are new rows in `charge_adjustments` (signed delta, reason code, actor, timestamp) — the spec already has this table; enforce that it is the *only* write path after finalisation.
2. **Balance is always computed:** `SUM(charges) + SUM(adjustments) − SUM(payments)`. Never a stored mutable `balance` column that can drift. If you need speed, cache it in a materialised view refreshed transactionally, never hand-maintained.
3. **Payments are never deleted or edited** — a mistaken payment is voided by a reversal payment row referencing the original.
4. **Freeze the inputs into the charge.** The charge row stores `tariff_amount` and `tariff_id` **as of that day** (not a join to the current tariff), `model_version`, `zone_polygon_version`, `decision_source` (auto / nazoratchi-confirmed / manual), and the list of evidence snapshot IDs. A tariff change next month must not rewrite last month's reports.
5. **Re-running CV over past days produces a *proposal*, never a mutation** — an admin reviews and applies it as adjustments.

**Warning signs:** any `UPDATE daily_charges SET amount` in the codebase; a report for last month whose totals change between two runs; a vendor's debt figure differing between the bot and the panel.

**Phase to address:** P0 (schema: immutability, versioned tariff snapshot on the charge), P4 (adjustment-only write path, computed balance).

---

### Pitfall 7: The end-of-day billing job is not idempotent → double charges on day one

**Confidence:** HIGH (billing idempotency practice)

**What goes wrong:**
The nightly job runs twice — container restarted mid-run, the ops person re-triggered it after an error, a retry fired, two cv-service replicas both scheduled it. Every occupied rasta gets billed twice. Vendors see doubled debt in the bot the next morning. In a project whose entire premise is "trust the numbers", this is a one-shot credibility kill.

**How to avoid:**
1. `UNIQUE (market_id, stall_id, business_date)` on `daily_charges`. This is a two-line schema change that makes the failure impossible; do it in **P0**, not P4.
2. A `billing_runs` table: `(market_id, business_date, started_at, finished_at, status, actor)` with a unique partial index preventing two concurrent runs for the same market/date. The job takes an advisory lock (`pg_advisory_xact_lock`) on `(market_id, business_date)`.
3. Insert with `ON CONFLICT DO NOTHING` and report the conflict count — a non-zero count is the alarm that something re-ran.
4. Same discipline for snapshots: `UNIQUE (camera_id, slot_ts)`.
5. Same for cashier payments: an idempotency key generated client-side per payment attempt, so a double-tap on a flaky mobile connection cannot record two payments.

**Warning signs:** `count(daily_charges) > count(distinct stall)` for a date; vendor debt doubling exactly; the cashier's "3-tap" flow occasionally recording 2 payments.

**Phase to address:** P0 (constraints), P4 (advisory lock, billing_runs, client idempotency key).

---

### Pitfall 8: UTC container clock vs Asia/Tashkent business day

**Confidence:** HIGH (timezone aggregation literature + Docker defaults)

**What goes wrong:**
Uzbekistan is UTC+5 with **no DST** — which lulls people into thinking timezones are safe here. They are not. Docker containers default to `TZ=UTC`. The concrete failures:

- **A `cron: 0 0 * * *` "end of day" job runs at 05:00 Asia/Tashkent** — i.e. one hour *before* the market opens and the first snapshot is taken. It closes the wrong day and finalises it as empty. This is the single most likely timezone bug in this project and it silently zeroes revenue.
- **The 06:00 snapshot slot scheduled in UTC fires at 11:00 local.** All seven slots land in the afternoon.
- **`date_trunc('day', created_at)` in reports** buckets by UTC date. Anything logged between 00:00 and 04:59 local (a late cashier reconciliation, a night-shift adjustment, an automated reminder) lands in the *previous* day's bucket. Payments and charges then disagree about which day they belong to — exactly the reconciliation the product exists to produce.
- **Excel exports** carry naive timestamps that Excel renders in the viewer's locale.

**How to avoid:**
1. **`business_date DATE` is a first-class stored column** on `snapshots`, `occupancy_events`, `daily_charges`, `charge_adjustments`, `payments` — computed once at write time as `(ts AT TIME ZONE market.timezone)::date`. Every aggregation, index, and unique constraint uses `business_date`. Never `date_trunc` a UTC timestamp in a report.
2. **`markets.timezone TEXT NOT NULL DEFAULT 'Asia/Tashkent'`** from P0. This is multi-tenant; a future market may be elsewhere, and retrofitting per-market timezone into finished reports is expensive.
3. **The scheduler is configured with an explicit timezone** (`AsyncIOScheduler(timezone=ZoneInfo("Asia/Tashkent"))` or per-market). Set `TZ=Asia/Tashkent` in compose *as well*, but do not rely on it — be explicit in code.
4. **Define the day-close time as a market setting** (e.g. 22:00 local), not "midnight". A cashier who takes a payment at 20:30 must land in that day; the close job must run after the market is genuinely done.
5. Store all timestamps as `timestamptz`, never naive `timestamp`.

**Warning signs:** revenue report shows a systematic dip on one day and a spike on the next; snapshot slot times in the DB are 5 hours off the configured schedule; the day-close job's log timestamps are in the morning.

**Phase to address:** P0 (schema + scheduler timezone — cheapest to fix here by an order of magnitude), verified in P2 (slot times) and P4 (close job).

---

### Pitfall 9: Multi-tenant leak — one missing `market_id` predicate

**Confidence:** HIGH (multi-tenant SaaS literature)

**What goes wrong:**
A single query written as `WHERE id = $1` instead of `WHERE market_id = $tenant AND id = $1` exposes one market's revenue, vendor registry, or camera credentials to another market's director. In this domain the blast radius is unusual: markets in the same region compete, the data is effectively financial-oversight data, and a leak involving a government-adjacent programme is not a "sorry, patched" incident.

Cross-tenant leaks in practice come from three places, not from the obvious CRUD endpoints:
- **Background jobs** (billing, CV, bot broadcasts) run with no request context and therefore no tenant context.
- **Fetch-by-primary-key** helpers (`get_by_id`) used inside services.
- **Aggregate/report queries** written ad hoc in raw SQL near a deadline.

**How to avoid:**
1. **Postgres RLS as a backstop, not as the only defence.** Enable RLS on every tenant table; the app sets context with `SET LOCAL app.current_market = …` **inside the transaction** — never session-level, because a pooled connection carries session GUCs to the next, unrelated request. (Note the known limits: RLS has had CVEs around subquery handling and optimiser statistics leakage; it is defence-in-depth, not a licence to skip application filters.)
2. **Application layer: a single `TenantScopedRepository` base** that injects `market_id` into every query. Ban bare `session.get(Model, id)` via a lint rule / code review checklist.
3. **Background jobs take `market_id` as an explicit required argument.** No job may query "all rows"; it iterates markets.
4. **An automated cross-tenant test suite** in CI: seed two markets, then for every registered API route, call it with market A's token and market B's object IDs, asserting 404 (not 403 — 403 confirms existence). Make it a CI gate. This test catches the class of bug permanently and costs a day.
5. **Composite indexes lead with `market_id`:** `(market_id, business_date)`, `(market_id, stall_id, business_date)`, `(market_id, camera_id, slot_ts)`, `(market_id, vendor_id)`. Without a leading tenant column the planner picks the wrong index once one market dominates the table, and a report that ran in 40 ms in the pilot takes 8 s at market #5.

**Warning signs:** any raw SQL without `market_id`; a report endpoint that doesn't take market from the auth context; query plans showing seq scans on `daily_charges`.

**Phase to address:** P0 (RLS, repository base, indexes, cross-tenant CI test) — retrofitting after P4 means auditing every query written in 8 weeks.

---

### Pitfall 10: A camera gets bumped and every polygon silently points at the wrong rasta

**Confidence:** MEDIUM-HIGH (surveillance/PTZ drift research)

**What goes wrong:**
Someone re-aims a camera, a mount slips, a camera is replaced during maintenance, or the stream resolution changes after an NVR firmware update. The frame shifts by 40 px. Every polygon on that camera now covers the neighbouring stall. **The system keeps billing — confidently, at full accuracy, the wrong vendors.** Physical interference with a camera silently invalidates everything downstream of image acquisition, and there is no error anywhere in the pipeline.

Related silent killers on the same axis: a spider web or dust on the lens; an awning/tarp erected in front of the camera in summer; a truck parked in the view; the camera's day/night mode stuck.

**How to avoid:**
1. **Store a reference frame per camera** at the moment zones are drawn, plus `camera_zones.reference_width/height`.
2. **Cheap drift check on every capture:** compare a few fixed background patches (or a global ECC/ORB alignment, or a perceptual hash) against the reference. If displacement exceeds a threshold → set `cameras.status = needs_recalibration`, **suspend auto-charging for that camera's stalls** (route to `noaniq`), and Telegram-alert the admin. This costs ~10 ms per frame and prevents the worst possible outcome: confidently billing the wrong people.
3. **Tamper/quality checks in the same pass:** mean intensity (blackout), Laplacian variance (defocus/dirty lens), fraction of frame unchanged vs reference (obstruction).
4. **Store polygon coordinates normalised (0..1) or with an explicit `reference_resolution`.** If you store raw pixels and the substream resolution changes, everything breaks in a way that looks like a CV bug.
5. **Version `camera_zones`.** A re-draw creates version N+1 with a validity start date; historical charges reference the version they were computed with, so re-calibrating today does not invalidate last month's evidence.

**Warning signs:** all stalls on one camera flip state on the same day; occupancy for one camera jumps or collapses discontinuously; a whole camera's stalls suddenly appear in the "band, lekin to'lovsiz" report.

**Phase to address:** P1 (reference frame, versioned zones, normalised coordinates), P2/P3 (drift + tamper checks, auto-suspend, alert).

---

### Pitfall 11: Baseline revenue measured wrong — the whole ROI argument becomes unfalsifiable

**Confidence:** MEDIUM-HIGH (public-revenue digitization studies + measurement design)

**What goes wrong:**
The product's core claim is "formal daily revenue increased after SBOZOR". Four ways to destroy that claim before it's made:

1. **Announcement effect.** The moment collectors know cameras+AI are coming, behaviour changes. A baseline measured *after* the announcement already contains part of the improvement — you then attribute your own effect to nothing, or worse, the effect is spent before you measure.
2. **Measuring the reported number, not the collected number.** The administration's existing figure *is* the leaked-through figure. Taking it as baseline and comparing to your (also reported) figure compares two reported numbers with different reporting incentives.
3. **Seasonality.** Comparing October (harvest, peak bazaar) to December (cold, thin) — or the reverse — attributes an agricultural cycle to the product. Karmana revenue in November is not comparable to September for reasons that have nothing to do with software.
4. **Baseline collected as "one number for last month."** Unusable: no variance, no day-of-week structure, no denominator.

Evidence that the effect is real and worth measuring properly: Tanzania national-park entrance-fee digitization cut leakage ~40%; Rwanda bus-fare digitization raised revenue 140%. But the same literature is blunt that digitization alone does not remove discretion — Tanzania's receipt-book control lost 30% of books and 35% of expected revenue. Your measurement has to be able to detect *no effect*, or it proves nothing.

**How to avoid:**
1. **Start baseline collection in week 1 of PF, before the system is visible to collectors**, with a written, pre-agreed daily format: date, cashier, cash total, terminal total, **number of occupied stalls that day**, number of stalls billed. Signed daily by the administration.
2. **Track revenue-per-occupied-rasta, not just total revenue.** This is the seasonality-robust metric and it is the number that actually proves leakage reduction. Total revenue mixes in weather, harvest, and holidays.
3. **Get historical monthly totals from the administration** for the previous 12–24 months if any records exist — gives you a seasonality curve for free.
4. **Design a within-market control if at all possible:** roll out zone by zone (zone A on the system, zone B not, for 2–3 weeks). A same-market, same-week comparison is worth more than a before/after comparison and immunises you against every seasonal objection.
5. **Write down, before launch, what result would count as failure.** If no number can disprove the claim, the claim is marketing.

**Warning signs:** baseline arrives as a single figure; the format changes mid-collection; the administration offers to "give you the numbers later"; baseline collection starts in week 10.

**Phase to address:** **PF, week 1.** This is the highest-value, lowest-effort, most-commonly-skipped item in the whole project, and it cannot be done retroactively.

---

### Pitfall 12: Cashier resistance and data-entry sabotage

**Confidence:** MEDIUM-HIGH (revenue-digitization field literature + domain reasoning)

**What goes wrong:**
The system's purpose is to reveal that cash is being skimmed. The people entering the data are exactly the people it exposes. The Tanzania case is instructive: a vendor pays cash, the collector pockets it and promises to enter it later; when receipt books were used as a control, 30% of the books and 35% of expected revenue simply went missing.

Predictable sabotage vectors in *this* system, ranked by ease:

| Vector | Effect | Detection |
|---|---|---|
| Mark occupied rastalar as `ta'mirda` / `yopiq` | No charge generated at all | AI says band + status says closed → anomaly |
| Never assign a vendor to a stall | Debt cannot accrue (spec: unassigned → no charge) | "Ro'yxatga olinmagan savdo" count rises — already in the spec, make it a director KPI |
| Manual amount override with a stock reason code | Under-collection | Override rate per cashier |
| Record payment against a different (empty) stall | Books balance, wrong vendor credited | Payment on a stall the AI saw as bo'sh all day |
| "The camera is broken" | Camera excluded, zone unbilled | Camera offline rate per camera, compared across cameras |
| Delay entry to end of day, reconstruct from memory | Destroys the parallel-run comparison | Payment timestamps clustering in the last hour |

**How to avoid:**
1. **Every action that reduces billable amount is a reason-coded, audited event with a per-user rate visible in a standing report.** Not buried in `audit_log` — a first-class report the director reads: "stall status changes by user", "manual overrides by user", "unassign events by user", "payments recorded on AI-empty stalls by user". Visibility is the control; the audit log alone is not.
2. **Cross-checks are features, not analytics:**
   - status = `yopiq` but AI = `band` → anomaly row (this is the sabotage detector, and it costs nothing because you already compute both sides)
   - payment recorded on a stall with zero `band` snapshots → anomaly
   - vendor assignment count trending down → alert
3. **Make "ro'yxatga olinmagan savdo" someone's KPI.** The spec already surfaces it; if it isn't assigned to a person with a target, it becomes the universal loophole ("just don't register anyone").
4. **The 3-tap flow and auto-computed amount are anti-corruption controls, not UX niceties.** Do not let "the cashier asked for a free-amount field" reintroduce the hole. The spec is right; hold the line.
5. **The director must visibly own the rollout.** Field literature is unanimous: digitization without leadership backing produces cosmetic compliance. Get the director to announce it, personally, before go-live.
6. **Don't design a system that can only accuse.** Give cashiers something: faster shifts, no end-of-day arithmetic, no arguments with vendors about "how much do I owe", a defensible record when *they* are accused. A tool that only surveils gets sabotaged; a tool that also helps gets used.

**Warning signs:** spike in `ta'mirda`/`yopiq` status changes in week 1 of go-live; one cashier with 10× the override rate; vendor registrations flatlining; camera-offline reports concentrated on the highest-revenue rows.

**Phase to address:** P4 (reason codes, override controls, anomaly cross-checks), P6 (the "behaviour" report), P7 (rollout with director backing).

---

### Pitfall 13: Parallel run designed as duplicate data entry — it collapses in four days

**Confidence:** MEDIUM (domain reasoning + change-management practice)

**What goes wrong:**
"2–4 hafta parallel rejim: kassir eski usulda ham yozadi" as written means the cashier does everything twice. In practice, on day 3 the cashier fills the old book at end of day *from the app* (or from memory). The two records now agree perfectly and prove nothing — you have destroyed the only independent measurement you had, and you won't know it.

The second failure: nobody reconciles daily, so at week 4 you have two piles of paper and a database, and the comparison never happens.

**How to avoid:**
1. **Frame it as independent measurement, not duplicate entry.** The old book remains the source of truth for money during the parallel run (removes the cashier's risk and resistance). The app entry happens *at the same moment as the transaction*, not later.
2. **Reconcile daily, by a third party** — the nazoratchi or market admin, not the cashier — on a one-page signed sheet: book total vs app total vs AI-expected total, with discrepancies explained the same day. A four-week unreconciled parallel run is worthless.
3. **Hard cutover date announced in advance.** Parallel mode has an end date agreed before it starts. Open-ended parallel mode never ends.
4. **Instrument entry latency in the app** (time between the cashier arriving at the stall and the payment record). Rising latency = reconstruction from memory = the parallel run is already broken.
5. **Three-way comparison, not two-way.** book vs app vs AI-expected. The interesting cell is "AI says band, book says paid, app has nothing" — that's a process gap. "AI says band, book says nothing" is the money.

**Warning signs:** payment timestamps clustering into a 30-minute window at end of day; book and app agreeing to the som on every single day (real independent records never agree perfectly); reconciliation sheets not signed for 3 days.

**Phase to address:** P7, designed in P6 (the reconciliation sheet and the three-way report are deliverables, not afterthoughts).

---

### Pitfall 14: NVR is unreachable from the VPS and it's discovered in week 5

**Confidence:** MEDIUM (network practice; CGNAT prevalence should be verified for the market's ISP)

**What goes wrong:**
The plan assumes the VPS can reach the Karmana NVR via WireGuard. Three common blockers, each with real lead time:
- **CGNAT / dynamic IP on the market's connection.** No inbound reachability at all. WireGuard needs one endpoint to be reachable; if the market side is behind CGNAT, the *market* side must dial out to the VPS — which means something at the market must run the WireGuard client 24/7. If that's not the NVR itself (most NVRs can't), you need a small always-on device (mini-PC / router with WireGuard) — procurement + shipping + on-site install in Karmana.
- **The market's IT person offers to "just forward the port"** — exposing a Hikvision NVR to the open internet is how these devices end up in botnets, and the spec correctly forbids it. Have the alternative ready before the conversation.
- **Credentials arrive late or are viewer-level** without ISAPI/RTSP permission.

The schedule puts camera work at weeks 5–6. If it slips two weeks, P3 (CV) has no real Karmana images, and the back half of a 12-week plan with zero buffer compresses onto three people.

**How to avoid:**
1. **Make "one real Karmana snapshot stored in MinIO" a week-2 milestone, not week 5.** It can be crude — a laptop on site, a manual ffmpeg/ISAPI call, a file uploaded by hand. What matters is that the *access path* is proven and the images exist for CV work.
2. **Do a remote-access feasibility call in week 1** (PF): what ISP, public IP or CGNAT, who owns the router, is there an always-on PC. Order the WireGuard endpoint device in week 1 if needed.
3. **Camera coverage audit in week 1–2** with actual frames, not with the administration's description. Confirm: which rows are visible, at what pixel size, what the smallest stall looks like, does IR reach, is the view obstructed. The "~90% coverage" figure is currently unverified by anyone technical.
4. **Design the tunnel outbound-from-market** by default. It works behind CGNAT, it requires no port forwarding, and it never exposes the NVR.

**Warning signs:** week 3 arrives and nobody has an NVR IP; "we'll get the password next week" repeated twice; the coverage figure has no frames behind it.

**Phase to address:** PF week 1–2. This is the biggest single schedule risk in the project.

---

## Moderate Pitfalls

### M1: Polygon editor underestimated (the spec already flags it — it's worse than flagged)

1000 rastalar need polygons on ~25 camera frames. At 30 s each that is **8+ hours of continuous drawing**, on 4 MP frames, on a laptop. The editor needs: zoom/pan on a large image, per-vertex drag, vertex insert/delete, undo/redo, snap, duplicate-and-nudge (stall rows are repetitive — this alone halves the work), overlap warning, stall-number assignment, and **autosave per polygon**. Save-all-at-once means one failed request loses hours of work, and no human will re-do it.

**Prevention:** build the camera-zone editor first (spec says P1 — correct). Use a mature canvas library (Konva/react-konva or Fabric) rather than raw `<canvas>` — the ecosystem has solved drag bounds, hit testing, and transform stacks. Store coordinates normalised. Version zones. Provide JSON import/export so polygons can be bulk-generated or repaired outside the UI. **Budget the drawing labour as a project task with a named owner** — it is a person-day, not a side effect of the wizard.

### M2: Plan-map editor eats the frontend developer

The colourful bozor map is the demo-winning screen and can absorb unbounded effort. The spec already says "schematic version can start" — enforce it. MVP plan map = grid/list with colour states + optional background image with simple point markers. Draggable/resizable polygon plan editing is post-MVP. The *camera zones* are load-bearing; the *plan map* is presentation.

### M3: Telegram phone-number registration

- **`request_contact` does not prove ownership.** The user can pick any contact from their address book. **Always check `message.contact.user_id == message.from_user.id`** and reject otherwise. Without this, a vendor can register someone else's number, or see someone else's debt.
- **Normalise phone numbers to E.164 at write** (`+998901234567`). Uzbek numbers arrive as `998901234567`, `901234567`, `90 123-45-67`, `+998 (90) 123-45-67`. Store normalised + raw. `UNIQUE (market_id, phone_e164)`.
- **After first bind, `telegram_user_id` is the identity key**, not the phone. Vendors change SIMs; the chat stays.
- **Decide the cardinality now:** one Telegram account ↔ one vendor ↔ many stalls? Family stalls sharing a phone are common in bazaars. The spec implies 1:1; make it explicit in the schema or you'll discover it at go-live.

### M4: Telegram broadcast: rate limits and blocked bots

- Limits are ~30 messages/second globally and ~1 message/second per chat. A `for vendor in vendors: await bot.send_message(...)` loop over 600 vendors triggers HTTP 429 with `retry_after`; ignoring `retry_after` makes the next 429 arrive sooner. Send through a **Redis-backed queue with a token-bucket limiter**, honour `TelegramRetryAfter.retry_after`.
- **`TelegramForbiddenError`** = user blocked the bot. Mark `vendors.bot_blocked_at`, stop retrying that chat, and surface the count in the director's report ("N sotuvchi bot orqali xabar ololmaydi"). Silently swallowing this is how the "≥60% of vendors on the bot" KPI quietly becomes fiction.
- **Debt reminders are a reputational hazard.** An AI-derived debt pushed to a vendor's phone before any human verified it is exactly the dispute the project is trying to avoid. Gate reminders: charge finalised **and** not disputed **and** age > N days **and** amount > threshold.
- **Webhook vs polling on the VPS:** you already run Nginx + Let's Encrypt, so webhook is the right production choice — use `secret_token` and verify the `X-Telegram-Bot-Api-Secret-Token` header; put the token in the header, not the URL path (reverse proxies log URLs). Only one polling process may exist per token; a developer running the bot locally against the production token silently steals updates. **Rule: webhook in prod, polling in dev, never both, and `drop_pending_updates=True` on deploy** so a restart after downtime doesn't replay a backlog of stale commands. Set `allowed_updates` explicitly.

### M5: In-process scheduler duplicated across uvicorn workers

`cv-service` with an APScheduler started in FastAPI's lifespan, run as `uvicorn --workers 4`, gives you **4 schedulers → 4× snapshots**, 4× NVR session pressure, 4× storage, and 4× the chance of hitting the NVR's stream limit. This is a well-known APScheduler/Gunicorn failure.

**Prevention:** the scheduler runs in its own process/container (or cv-service runs with `--workers 1`), *plus* a Redis lock keyed on `(market_id, camera_id, slot_ts)`, *plus* the `UNIQUE(camera_id, slot_ts)` constraint. Three layers, because this one is easy to reintroduce during a deploy-config change.

### M6: NVR concurrent-session limits and thundering-herd capture

25 cameras all captured at exactly `06:00:00` is a burst of 25 simultaneous sessions against one NVR, on top of whatever live viewers exist. Hikvision NVRs cap remote connections (commonly cited ~128 total, but it's a shared budget across streaming, playback, and web UI, and per-model limits are lower in practice).

**Prevention:** jitter each camera's capture by ±60 s within the slot, cap concurrency to 4–6 simultaneous captures, and use ISAPI stills (which don't hold a streaming session) rather than RTSP where possible. Record the slot's *nominal* time on the row and the *actual* capture time separately.

### M7: Live camera view (go2rtc) costs more than it looks

Hikvision NVRs frequently default to **H.265**, which browsers cannot reliably play over WebRTC/MSE. go2rtc then **transcodes**, which on a CPU-only 4–6 vCPU Contabo box is expensive **per viewer** and directly competes with the CV service and core-api for CPU. Two directors watching four cameras each can starve the billing job. Streams also traverse the WireGuard tunnel from Karmana to Contabo — sustained 2–4 Mbps per stream on the market's uplink, which also carries the snapshot captures.

**Prevention:** force the **substream in H.264** for live view (reconfigure the NVR — this is a commissioning task, not a code task); hard-limit concurrent viewers; run go2rtc with explicit CPU limits in compose so it cannot starve `core-api`/`cv-service`; measure at week 6. Live view is a customer *want*, not the core value — see the cut list (Pitfall 15).

### M8: Storage and retention arithmetic never actually computed

Full frames are cheap: 25 cams × 7 slots × ~1.2 MB ≈ 210 MB/day ≈ 19 GB per 90-day window. Fine on 400 GB. The trap is **per-zone evidence crops**: 1000 stalls × 7 slots × ~40 KB ≈ 280 MB/day ≈ 25 GB/90 days **per market**, growing linearly with tenants.

**Prevention:** do not store crops as objects. Store `(snapshot_id, zone_polygon_version)` and crop on demand with a cache. Configure MinIO lifecycle rules **when the bucket is created**, not later — retrofitting lifecycle onto millions of objects is slow and error-prone. Alert at 70% disk, not 90%.

### M9: Backup exists, restore has never been attempted

The spec says a restore drill happens "at least once". Make it a **dated phase-exit criterion with a named owner**, and make it include **MinIO objects**, not just the Postgres dump. The evidence images *are* the product's defence in a dispute; a DB-only backup leaves you with charges you cannot justify.

### M10: Audit log with holes

An `audit_log` written only from an ORM `after_update` hook misses bulk operations, raw SQL, and migrations — precisely the paths a technically-capable insider would use. It also typically records nothing about *reads* (who looked at which vendor's debt), which matters under Uzbek personal-data law.

**Prevention:** decide the scope explicitly in P0 — which tables, which operations, and whether reads of personal data are logged. Prefer database-level triggers for the financial tables (`daily_charges`, `charge_adjustments`, `payments`, `stall_assignments`, `tariffs`) so no code path can bypass them.

### M11: Data residency assumed to be a later problem

Uzbek law requires personal data of citizens to be processed on technical means located in Uzbekistan and registered in the State Register of personal-data bases. A 2026 amendment relaxed this for much data (with conditions) while keeping a hard domestic-storage mandate for **biometric** data and for telecom-subscriber data. **CCTV frames containing identifiable faces are plausibly biometric-adjacent** — this is a legal question, not an engineering one, and it directly affects whether snapshots may sit on Contabo at all.

**Prevention:** get a written legal opinion during P0–P2, before the archive is large enough to make migration painful. Keep the personal-data tables (vendors: F.I.Sh., phone) separable from the rest so they can be relocated independently. Deploy the "video kuzatuv olib borilmoqda" signage and the written data-use agreement with the administration **before** the first snapshot, not before go-live.

### M12: Tariff history joined instead of snapshotted

`daily_charges` joining to the current `tariffs` row at report time means a tariff change in November rewrites October's reports and every vendor's historical debt. The spec correctly says tariffs are historical — enforce it by **copying the amount and `tariff_id` onto the charge row** at creation, and never joining to the live tariff in a report.

---

## Minor Pitfalls

- **NVR clock drift.** DVR/NVR clocks drift routinely (dead CMOS battery, no NTP, manual time-setting), sometimes by minutes. If you ever key a snapshot to the camera's OSD/RTSP timestamp, frames land in the wrong slot and the wrong `business_date`. **Always use server capture time as authoritative**; verify NVR NTP during commissioning and record the observed offset.
- **RTSP credentials "encrypted at rest" with the key in the same `.env`.** That is obfuscation, not encryption. It still helps against a DB dump leak — say so honestly rather than claiming more. Also note that go2rtc's config file will contain plaintext RTSP URLs; treat it as a secret and exclude it from unencrypted backups.
- **i18n retrofit.** Three languages must cover: UI strings, Excel column headers, Telegram bot messages, notification templates, report titles, and enum labels (reason codes, statuses). It is tempting to auto-transliterate Latin↔Cyrillic Uzbek — it breaks on numerals, proper nouns, and borrowed terms. Maintain three catalogs. The spec is right that scaffolding must start week 1.
- **Excel export with string-formatted money** (`"1 200 000"`) breaks `SUM` in Excel and is the first thing an accountant will notice. Write numbers as numbers with a display format.
- **Reason codes as free text.** A free-text "sabab" field on overrides and adjustments is unanalysable. Use a fixed enum + optional free-text note.
- **`noaniq` → `bo'sh` default is safe but must be visible.** The spec's choice (under-count rather than over-count) is right, but if the count of "defaulted to empty because nobody reviewed" isn't on the director's report, it silently becomes the main revenue leak.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| Store `market_id` but filter only in application code (no RLS) | Saves ~1 day in P0 | One missed filter = cross-tenant financial leak; retrofitting after 8 weeks of queries is a full audit | Never — RLS is a day, the audit is a week and never complete |
| `UPDATE daily_charges` instead of adjustment rows | Simpler recompute logic | Reconciliation impossible, disputes unwinnable, history unstable | Never after any charge is shown to a human |
| Skip `business_date` column, use `date_trunc` on timestamps | One less column | Every report and every unique constraint is subtly wrong; fixing it means re-deriving history | Never |
| Person-detection-only occupancy for v1 | Ships CV in P3 | Over-charges create disputes in the first week — the exact failure that kills adoption | Acceptable *only* if paired with the ≥2-snapshot corroboration rule and a hard `noaniq` fallback |
| Draw polygons on raw pixel coordinates | Faster editor | Any resolution or stream change invalidates all 1000 polygons | Never — normalising is 20 lines |
| Scheduler inside the API process | One less container | Duplicate snapshots the day someone adds `--workers` | Only with `--workers 1` pinned in compose *and* a Redis lock *and* a DB unique constraint |
| Skip the drift/tamper check on captures | Saves ~2 days in P2/P3 | Billing the wrong vendors, undetectably, for weeks | Only if manual weekly frame review is scheduled and actually happens |
| Free-amount field for the cashier | Makes one cashier happy | Reopens the corruption hole the product exists to close | Never |
| Live view via transcoding | Satisfies the customer request quickly | Starves CV/billing on a CPU-only box | Only with H.264 substream + viewer cap + CPU limits |
| Store evidence crops as files | Fast evidence rendering | 25 GB/90 days/market, growing per tenant | Only with a lifecycle rule set at bucket creation |
| Baseline revenue "we'll collect it later" | No week-1 work | The ROI claim becomes unprovable — permanently | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| **Hikvision NVR — snapshots** | `ffmpeg -i rtsp://... -frames:v 1` with no timeout | Prefer ISAPI `GET /ISAPI/Streaming/channels/<CH>01/picture` with **Digest** auth; ffmpeg only as fallback with `-rtsp_transport tcp -timeout 5000000` + OS-level `killpg` timeout |
| **Hikvision NVR — stream choice** | Substream (`102`) because it's lighter | Substream is often 640×360 — distant rastalar become a few pixels. Use main stream for analysis, substream for live view |
| **Hikvision NVR — sessions** | 25 simultaneous connections at exactly 06:00:00 | Jitter ±60 s, cap concurrency at 4–6, prefer stateless ISAPI stills |
| **Hikvision NVR — auth** | Basic auth assumed | Device must be set to Digest; ISAPI requires Digest on most firmware |
| **FFmpeg** | Copy-pasted `-stimeout` from a 2019 blog post | `stimeout` was renamed to `timeout` and removed; FFmpeg 8 rejects it. Verify options against the actual installed binary in CI |
| **FFmpeg** | Placing `-timeout` after `-i` | Input options must precede `-i` or they're silently ignored |
| **WireGuard / market network** | Assuming the NVR side is inbound-reachable | Assume CGNAT: the market side dials out to the VPS. Verify ISP and public-IP status in week 1; order an always-on endpoint device if needed |
| **go2rtc** | Default NVR H.265 stream to the browser | Reconfigure the NVR substream to H.264; avoid transcoding entirely on a CPU-only VPS |
| **Telegram — registration** | Trusting `message.contact.phone_number` | Verify `message.contact.user_id == message.from_user.id`; normalise to E.164 |
| **Telegram — broadcast** | `for v in vendors: await send()` | Redis queue + token bucket (≤30/s global, ≤1/s per chat); honour `retry_after`; mark blocked chats on `TelegramForbiddenError` |
| **Telegram — deployment** | Webhook in prod while a dev laptop polls the same token | Webhook only in prod with `secret_token`; separate dev bot token; `drop_pending_updates=True` on deploy |
| **MinIO** | Lifecycle rules "later" | Configure at bucket creation; per-market prefixes; verify the backup sync actually copies objects, not just the DB |
| **PostgreSQL / RLS** | `SET app.current_market` at session level with a connection pool | `SET LOCAL` inside the transaction — session GUCs survive into the next request's borrowed connection |
| **APScheduler** | Scheduler in the FastAPI app with multiple workers | Dedicated scheduler process + Redis lock + DB unique constraint |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| Reports without `(market_id, business_date)` composite indexes | A report that took 40 ms in the pilot takes seconds | Lead every index with `market_id`; index `business_date`, not raw timestamps | Market #3–5, or ~1M `occupancy_events` rows |
| `occupancy_events` unpartitioned | Slow scans, bloated indexes, painful vacuum | 7 000 rows/day/market ≈ 2.5M/year/market. Plan monthly partitioning by `business_date` before market #5 | ~10M rows total |
| Tiled/sliced CV inference treated as real-time | CPU pegged, snapshots queue up | Batch-process the whole slot asynchronously; 25×7×9 tiles ≈ minutes, which is fine. Never put inference on a request path | Immediately, if anyone adds a "analyse now" button |
| go2rtc transcoding per viewer | CV jobs and API latency degrade together | H.264 substream, viewer cap, container CPU limits | 2–3 concurrent viewers on 4 vCPU |
| Loading all 1000 stalls with their state into the map view in one payload | Slow first paint on the director's phone | Paginate/viewport-load; pre-aggregate the day's state into one row per stall | ~500 stalls on mobile |
| N+1 queries in the debt/report views (charge → adjustments → payments per stall) | Report generation takes tens of seconds | Compute balances in a single aggregate query or a materialised view | ~300 stalls |
| Excel export built in-process synchronously | Request timeouts, worker blocked | Generate to MinIO in a background job, return a download link | ~10k rows |
| Storing evidence crops as objects | Disk fills; MinIO listing slows | Crop on demand + cache | ~3 months × 2 markets |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Port-forwarding the NVR to the internet "temporarily" | Hikvision devices are actively scanned and botnetted; also full video access to a public market | Outbound-only WireGuard from the market side; NVR never routable from the internet. Have this answer ready before the market's IT person suggests forwarding |
| Missing `market_id` in one query | Cross-tenant financial data exposure between competing markets | RLS + scoped repository + automated cross-tenant CI test on every route |
| RTSP credentials "encrypted" with the key in the same `.env` on the same host | A DB dump leak is contained; a host compromise is not | Be explicit about the threat model; consider a KMS/secret store before multi-market; never commit `.env`; exclude go2rtc config from plaintext backups |
| Snapshot URLs served without authorization | Evidence images (faces, vendors, goods) become publicly enumerable | Presigned, short-TTL MinIO URLs issued per authenticated request; never a public bucket |
| Bot token in the webhook URL path | Reverse proxies and access logs record URLs | Random path + `secret_token` header verification |
| Cashier session on a shared phone with no timeout | Payments recorded under the wrong cashier; audit trail meaningless | Short session TTL, explicit device binding, cashier re-auth for overrides |
| Personal data (F.I.Sh., phone) + face imagery on foreign hosting | Uzbek personal-data localization; biometric data has a hard domestic mandate even after the 2026 relaxation | Legal opinion in P0–P2; keep personal-data tables separable; signage + written data-use agreement before the first snapshot |
| Audit log writable/deletable by the application role | An insider erases their own trail | Append-only audit table; `REVOKE UPDATE, DELETE`; separate role for migrations |
| Director/admin able to edit finalized charges directly | The system's own numbers become negotiable | Adjustments only, reason-coded, audited, with the original preserved and shown |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---|---|---|
| Nomuvofiqlik report presented as an accusation | Cashiers and vendors treat the system as an enemy; sabotage follows | Present as "to be verified today" with a resolution workflow, not "N people stole money" |
| Vendor sees an AI-derived debt in the bot before any human confirms it | Disputes arrive at the bot, not at the market office; the vendor's first experience is a false accusation | Bot shows only finalized, undisputed charges; a dispute button that freezes the amount and opens a case |
| Nazoratchi queue with no end and no progress indicator | Fatigue → rubber-stamping → poisoned training data | Fixed daily budget, visible progress ("47/200 bugun"), and honest reporting of what wasn't reviewed |
| AI answer shown before the reviewer decides | Automation bias; measured accuracy becomes meaningless | Blind mode for the audit queue; the operational queue may show it, but that queue must not be the accuracy source |
| Manual amount override that's easy and quick | Reopens the corruption hole | Override requires a reason code from a fixed list, is visibly logged, and appears on a per-cashier report |
| Wizard as one long linear flow that must be finished in one sitting | Onboarding a 1000-stall market is days of work; a session timeout loses it | Every wizard step saves independently; the wizard is resumable; polygons autosave individually |
| Bozor map as the primary navigation before data exists | Empty impressive screen; the useful work (search a rasta by number) is buried | Cashier flow is search-first; the map is a director/overview tool |
| Evidence shown as a full 4 MP frame | On a phone, the director can't tell which stall is meant | Show the cropped zone with the polygon highlighted, plus a "see full frame" toggle |
| Three languages with untranslated fallbacks appearing as keys (`stall.status.repair`) | Looks broken; destroys the "Apple-uslub" credibility | Fallback chain uz-latn → ru → key, plus a CI check for missing keys |

---

## "Looks Done But Isn't" Checklist

- [ ] **Snapshot pipeline:** often missing a failure row for skipped slots — verify `count(snapshots) == cameras × slots` for every day, and that failures produce rows, not silence.
- [ ] **Snapshot pipeline:** often missing frame validation — verify a corrupted/green/black frame is rejected before it reaches the detector.
- [ ] **Snapshot pipeline:** often missing a hard process kill — verify a hung ffmpeg is actually killed (test by black-holing the NVR IP with a firewall rule).
- [ ] **Snapshot schedule:** often tested only in summer — verify slot times against the seasonal profile and confirm what happens in December.
- [ ] **CV service:** often missing camera-drift detection — verify by nudging a camera 50 px and confirming the system flags it rather than billing the neighbour.
- [ ] **CV service:** often missing per-light-mode behaviour — verify an IR frame does not silently produce a `bo'sh` that suppresses a charge.
- [ ] **HITL:** often missing the blind random audit queue — verify the accuracy report's denominator is the audit sample, not the `noaniq` queue.
- [ ] **HITL:** often missing reviewer instrumentation — verify per-item latency is recorded and gold items exist.
- [ ] **Billing:** often missing idempotency — verify running the day-close job twice changes nothing (test it, in CI).
- [ ] **Billing:** often missing evidence linkage — verify every charge row can render its snapshots, polygon version, model version, and decision source months later.
- [ ] **Billing:** often missing the adjustment path — verify there is no code path that mutates a finalized charge.
- [ ] **Billing:** often missing tariff snapshotting — verify changing a tariff today does not change last month's report totals.
- [ ] **Timezone:** often missing `business_date` — verify a payment at 23:30 Tashkent lands on the same business date as that morning's snapshots.
- [ ] **Multi-tenancy:** often missing background-job scoping — verify the billing job, the CV job, and the bot broadcast all take an explicit `market_id`.
- [ ] **Multi-tenancy:** often missing a cross-tenant test — verify the CI suite calls every route with tenant A's token and tenant B's IDs.
- [ ] **Telegram:** often missing contact-ownership verification — verify sending a *different* contact is rejected.
- [ ] **Telegram:** often missing blocked-user handling — verify a blocked vendor doesn't break the broadcast and appears in a report.
- [ ] **Zones:** often missing normalised coordinates and versioning — verify changing the capture resolution does not break existing zones or historical charges.
- [ ] **Backup:** often missing MinIO objects and an actual restore — verify by restoring to a clean VPS and opening a charge's evidence image.
- [ ] **Audit:** often missing the financial tables' trigger coverage — verify a direct SQL update to `payments` still produces an audit row.
- [ ] **Baseline:** often missing entirely — verify signed daily baseline sheets exist from week 1 with occupied-stall counts, not just revenue totals.
- [ ] **Parallel run:** often missing daily reconciliation — verify a signed three-way sheet exists for every day of the run.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Missing `business_date` discovered after P4 | **HIGH** | Add column; backfill by converting timestamps (correct only if all timestamps are `timestamptz`); re-derive every daily aggregate; reconcile against payments; re-issue any report already sent to the director |
| Cross-tenant leak found in production | **HIGH** | Contain (disable endpoint), quantify from access logs, notify the affected market, add RLS + cross-tenant tests, then audit every query written to date |
| Double-charged a day | **MEDIUM** | Issue compensating `charge_adjustments` (never delete), notify affected vendors via the bot with an explanation, publish the corrected report. Trust cost is far higher than the technical cost — respond within hours, not days |
| Camera moved, weeks of wrong-stall billing | **MEDIUM-HIGH** | Identify the drift date from stored frames; re-draw zones as a new version; recompute the affected range as *proposals*; apply as adjustments with a documented reason; personally explain to affected vendors |
| Accuracy criterion measured on the biased queue, real accuracy is much lower | **MEDIUM** | Stand up the blind audit queue immediately; publish the honest number to the customer before they discover it; re-plan fine-tuning. Discovering this yourself is survivable; the customer discovering it is not |
| HITL queue rubber-stamped, training data poisoned | **MEDIUM** | Discard labels with latency < 1 s; re-label a clean sample; retrain from the base model, not from the poisoned checkpoint; cap the queue |
| Baseline never measured | **HIGH / unrecoverable** | Fall back to revenue-per-occupied-rasta trend within the system's own data plus any historical administration records; accept that the causal claim is weakened. No technical fix exists |
| Cashier sabotage discovered | **MEDIUM** | The cross-check reports are the evidence; escalate to the director (it is a personnel matter, not a software matter); tighten reason codes; do not attempt to solve it in code alone |
| December accuracy collapse from dark frames | **MEDIUM** | Shift the winter snapshot profile; exclude dark frames from auto-charge; fine-tune on the IR frames collected since October (which is why collecting them from day one matters) |
| NVR unreachable in week 5 | **HIGH (schedule)** | Ship a WireGuard endpoint device (lead time); in the meantime run CV development against a manually-collected frame set; cut live view and reports to protect the billing path |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| 1. Dark morning window (Nov–Jan) | P0 (schedule as data, `light_mode`), P2 (physical IR test), P3 (per-mode path) | Night walk-through frames exist; occupancy-by-slot chart shows no slot-1 collapse; winter profile switch tested |
| 2. ffmpeg hang / lost snapshots | PF wk1–2 (ISAPI test), P2 | Firewall-blackhole test kills the capture in <20 s; every slot has a row |
| 3. Person-detection-as-occupancy | P1 (polygon rules, front-edge), P3 (corroboration, tiling) | Manual review of 100 `band` results: <5% are passersby; disputes not clustered on aisle-adjacent stalls |
| 4. Biased accuracy measurement | P0 (criterion wording), P3 (blind audit queue), P6 (report) | Accuracy report denominator = audit sample; confusion matrix present; blind mode demonstrable |
| 5. Reviewer fatigue / rubber-stamping | P3 | Queue budget enforced; median review latency > 3 s; no bulk-approve button exists; gold-item accuracy tracked |
| 6. Mutable charges | P0 (schema), P4 (adjustment-only) | Grep: zero `UPDATE daily_charges SET amount`; last month's report total identical across two runs |
| 7. Non-idempotent billing | P0 (constraints), P4 (lock, run table) | CI test: run the day-close job twice, assert no change |
| 8. UTC vs Asia/Tashkent | P0 | Test: payment at 23:30 local groups with that morning's snapshots; scheduler fires 06:00 local |
| 9. Multi-tenant leak | P0 | Cross-tenant CI suite green on 100% of routes; RLS enabled on all tenant tables; `EXPLAIN` shows index scans led by `market_id` |
| 10. Camera drift | P1 (reference frame, versioned zones), P2/P3 (drift check) | Nudge test: camera moved 50 px → `needs_recalibration` + alert + auto-charge suspended |
| 11. Baseline measurement | **PF week 1** | Signed daily baseline sheets with occupied-stall counts exist by end of week 2 |
| 12. Cashier sabotage | P4 (reason codes, cross-checks), P6 (behaviour report), P7 | "Status = yopiq but AI = band" anomaly report exists and is reviewed daily |
| 13. Parallel-run collapse | P6 (design the reconciliation sheet), P7 | Signed three-way sheets for every day; payment timestamps spread across the day, not clustered |
| 14. NVR unreachable | **PF week 1–2** | One real Karmana snapshot in MinIO by end of week 2 |
| M1. Polygon editor | P1 (built first) | 50 polygons drawn end-to-end by a non-developer in under 30 min; autosave verified by killing the tab |
| M3/M4. Telegram | P5 | Foreign-contact rejected; broadcast to 600 simulated chats respects rate limits; blocked user handled |
| M5. Duplicate scheduler | P2 | Deliberately start 2 workers → snapshots still exactly one per slot |
| M7. go2rtc CPU | P2 | Load test with 3 viewers while a CV batch runs; billing job unaffected |
| M9. Restore drill | P2 or P4 (dated) | A charge's evidence image opens from a restored environment on a clean host |
| M11. Data residency | P0–P2 | Written legal opinion on file; signage installed before the first snapshot |

---

## Pitfall 15: 12-week scope — decide the cut list now, not in week 11

**Confidence:** MEDIUM (schedule analysis of the spec's own plan)

**What goes wrong:**
The plan has **zero buffer** and no integration/hardening week. Week 12 contains reports + Excel + three languages + go-live. When (not if) something slips, the cut happens under pressure in week 11 and it will be the wrong thing — teams cut the audit log, the adjustment flow, and the evidence linkage, because those are invisible in a demo. Those three are precisely the things that make the product defensible and are the most expensive to retrofit.

Additional structural risk: P3 (CV) depends on real Karmana frames that only exist after P2. A two-week slip in camera access compresses CV, billing, bots, and reports into five weeks for three people.

**How to avoid — the pre-agreed cut list, in order:**

| Rank | Cut candidate | Why it's cuttable | Fallback |
|---|---|---|---|
| 1 | **Live camera view (go2rtc)** | Customer *want*, not core value; highest CPU cost; competes with billing | Latest snapshot with a refresh button (already have the images) |
| 2 | **Plan-map polygon editor** | Presentation layer; camera zones carry the function | Grid/list view with colour states |
| 3 | **Third language (uz-Cyrl or ru)** | Scaffold is in place from week 1; catalogs can land post-launch | uz-Latn + one other at launch |
| 4 | **Excel export for secondary reports** | The two reports that matter (nomuvofiqlik, qarzdorlik) are the ones directors use | CSV, or Excel for two reports only |
| 5 | **Fine-tuning** | Explicitly a 1–2 month post-launch activity in the spec | Base model + zone rules + HITL |
| 6 | **Director morning digest** | The evening nomuvofiqlik report is the valuable one | Evening report only |
| — | **Never cut** | Audit log · `charge_adjustments` · evidence linkage on charges · `business_date` · multi-tenant scoping · idempotency constraints · the dispute flow | — |

Additional protections:
- **Move the two highest-uncertainty items earlier**: NVR access (to week 1–2) and the camera-zone editor (already week 3–4). Both are on the critical path and both have long tails.
- **Declare week 11 a hardening week** and move the Telegram bot into weeks 9–10 alongside billing (the bot is thin once billing exists). Launch with a week of stabilisation rather than a week of new features.
- **Go-live is a date for the billing path only.** Reports and exports can land in the parallel-run window; a director will accept a report a week late but will not accept a wrong charge.

**Warning signs:** week 6 arrives with no snapshot in MinIO; the polygon editor is still "almost done" in week 5; anyone proposes deferring the audit log.

**Phase to address:** P0 (agree the cut list with the customer in writing, in week 1).

---

## Sources

**Capture / Hikvision / FFmpeg**
- FFmpeg documentation — RTSP demuxer and TCP protocol options (`timeout`, `listen_timeout`, `buffer_size`) — via Context7 `/websites/ffmpeg_ffmpeg-all` — HIGH
- FFmpeg devel/cvslog: "avformat/rtsp: Remove deprecated old options, rename stimeout->timeout" (Apr 2021); homebridge-camera-ui issue #1081 "RTSP option stimeout is deprecated in ffmpeg v8" — HIGH
- FFmpeg-user mailing list: `rw_timeout` for RTSP (Feb 2025); "How do I set a timeout for an RTSP source?" — MEDIUM
- Hikvision support: "How to see the number of streams from an NVR — error maximum number of streams"; "How do I get my RTSP stream?" — MEDIUM
- Hikvision Europe: "How to use API to capture picture" (ISAPI `/ISAPI/Streaming/channels/<ch>/picture`); IPCamTalk "Get still image through URL from Hikvision NVR [SOLVED]"; `uchkunr/hikvision-best-practices` (ISAPI + HTTP Digest) — MEDIUM-HIGH
- go2rtc docs (hardware acceleration / transcoding); Frigate discussion #16651 "how to reduce go2rtc's CPU consumption" — MEDIUM
- IPVM "NTP / Network Time Guide for Video Surveillance"; Amped "Timestamps: not always showing the right time" — MEDIUM

**Computer vision / HITL**
- Roboflow / RidgeRun / Encord on SAHI slicing-aided hyper inference (+6.8/5.1/5.3 AP; +12.7–14.5 AP with slicing-aided fine-tuning); arXiv 2202.06934 — MEDIUM-HIGH
- Nature Sci. Reports "Review of large YOLOv8 and RT-DETR energy efficiency on edge devices"; D-FINE paper CPU benchmarks (RT-DETR-L ≈ 285 ms @960 px, ≈ 67 ms @320 px on Intel CPU) — MEDIUM
- Roboflow model licensing pages: D-FINE (Apache-2.0), RT-DETR (Apache-2.0), YOLOX (Apache-2.0); HuggingFace `ustc-community/dfine-*` — HIGH (confirms the project's licence constraint is satisfiable)
- arXiv 2607.14760 "Clean-Reference Streaming Detection of Lens Occlusion and Photometric Transitions for Camera Tamper Monitoring"; *Future Transportation* 4(4) "Methodology for Automatically Detecting PTZ CCTV Camera Drift" — MEDIUM
- MDPI Sensors 20(1):34 "CNN-Based Person Detection Using Infrared Images"; Axis "IR in surveillance" white paper — MEDIUM
- MIT Sloan Management Review "AI Explainability: How to Avoid Rubber-Stamping Recommendations"; HackerNoon "The Oversight Fatigue Problem"; tianpan.co "The HITL Rubber Stamp Problem"; radiology automation-bias study cited therein (inexperienced readers 80% → <20%; experienced 82% → 45.5% when AI wrong) — MEDIUM-HIGH
- arXiv 2207.07723 "More Data Can Lead Us Astray: Active Data Acquisition in the Presence of Label Bias" (uncertainty-sampled evaluation inverts conclusions) — MEDIUM
- MachineLearningMastery / PMC4349800 on precision-recall vs accuracy under class imbalance — HIGH

**Billing / data**
- prachub "Payment Systems: Ledgers, Idempotency, and Reconciliation"; Stripe idempotency-key writeups; DZone "Preventing Double Charges and Duplicate Actions" — MEDIUM-HIGH
- LiteLLM issue #29568 (~2× over-counting on single-day queries in non-UTC timezones); ccusage issue #349 (incorrect day grouping vs UTC); Microsoft Monetize "Dates and Times in Reporting" — MEDIUM
- Sunrise/sunset data for Navoi (40.11°N, 65.35°E, UTC+5): gaisma.com — October ~06:55, November ~07:30, December ~07:58, January ~07:56 — HIGH

**Multi-tenant / platform**
- Multiple 2026 write-ups on PostgreSQL RLS for multi-tenant SaaS (session vs `SET LOCAL` with pooling; `tenant_id` as leading index column; CVE-2024-10976, CVE-2025-8713 as RLS limitations) — MEDIUM-HIGH
- APScheduler discussion #1088 and FastAPI issue #12010 (duplicate jobs with multiple workers) — HIGH

**Telegram**
- aiogram docs — `setWebhook` (`secret_token`, `drop_pending_updates`, `allowed_updates`, ports 443/80/88/8443), long-polling ("one polling process per token"), errors — via Context7 `/websites/aiogram_dev_en` — HIGH
- grammY "Scaling Up IV: Flood Limits"; aiogram discussion #1489 "Strategy to deal with TelegramRetryAfter" (~30 msg/s global, ~1 msg/s per chat, honour `retry_after`) — MEDIUM-HIGH
- python-telegram-bot discussion #2963 and community threads on `request_contact` returning a third party's contact — MEDIUM

**Rollout / revenue digitization**
- The Chanzo (May 2026) "Cosmetic Digitisation? How Cash and Discretion Undermine Tanzania's Revenue Systems" (receipt books: 30% of books and 35% of expected revenue missing) — MEDIUM
- IMF *Digital Revolutions in Public Finance*, ch. 13; WEF (2018) on digital payments and corruption (Tanzania parks −40% leakage; Rwanda bus fares +140% revenue) — MEDIUM
- Adu et al. (2020), *EJISDC* — "Digitization of local revenue collection in Ghana: AMA evaluation" (POS did not prevent other corruption forms) — MEDIUM

**Legal / residency**
- Library of Congress (2021) Uzbekistan personal-data localization; kun.uz (Mar 2026) amendments; legal500 / settleadvisory / cerberus.legal summaries — biometric and telecom-subscriber data must remain on domestic servers; databases must be registered with UzComNazorat — MEDIUM-HIGH

**Project documents**
- `E:\bozor\SBOZOR-MVP-texnik-topshiriq.md` v1.1 (2026-07-28)
- `E:\bozor\.planning\PROJECT.md`

---
*Pitfalls research for: AI-camera revenue assurance / bozor digitization SaaS (SBOZOR)*
*Researched: 2026-07-29*
