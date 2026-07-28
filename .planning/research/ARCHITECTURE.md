# Architecture Research

**Domain:** Multi-tenant bozor raqamlashtirish SaaS — rejalashtirilgan CCTV snapshot → CV bandlik aniqlash → kunlik billing/rekonsiliatsiya → hisobot/bot
**Researched:** 2026-07-28
**Confidence:** MEDIUM-HIGH (pattern'lar Context7/rasmiy manbalardan tasdiqlangan; aniq detektor ostonalari va NVR xatti-harakati pilotda o'lchanadi)

> Hujjat tili: PROJECT.md konvensiyasi bo'yicha — sarlavhalar inglizcha (shablon strukturasi), matn o'zbek-lotin, texnik atamalar inglizcha.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────── Foydalanuvchi qatlami ─────────────────────────────┐
│  Next.js panel (admin · direktor · kassir · nazoratchi)  │  Telegram mijozlari  │
└─────────────────────┬────────────────────────────────────┴──────────┬──────────┘
                      │ HTTPS (nginx + Let's Encrypt)                 │ Bot API (chiquvchi)
┌─────────────────────▼───────────────────────────────────────────────▼──────────┐
│                          Servis qatlami — aynan 3 ta                            │
│  ┌─────────────────────┐  ┌────────────────────────┐  ┌─────────────────────┐  │
│  │ core-api (FastAPI)  │  │ cv-service (FastAPI)   │  │ bot-service         │  │
│  │  · auth / RBAC      │  │  · tick-scheduler      │  │  (aiogram)          │  │
│  │  · wizard, rasta,   │  │  · capture worker      │  │  · outbox poller    │  │
│  │    tarif, kamera    │  │  · detect worker       │  │  · sotuvchi bot     │  │
│  │  · review API       │  │  · retention worker    │  │  · direktor bot     │  │
│  │  · billing close    │  │  · /internal API       │  │  · admin alert      │  │
│  │  · to'lov, hisobot  │  │    (test/capture-now)  │  │                     │  │
│  │  · audit            │  │                        │  │                     │  │
│  └──────────┬──────────┘  └───────────┬────────────┘  └──────────┬──────────┘  │
└─────────────┼─────────────────────────┼──────────────────────────┼─────────────┘
              │                         │                          │
┌─────────────▼─────────────────────────▼──────────────────────────▼─────────────┐
│              Umumiy kutubxona paketi:  packages/sbozor-core                     │
│  SQLAlchemy modellar · enum'lar · tenant session · settings · S3 klient ·       │
│  pul (BIGINT so'm) va business_date yordamchilari · structured logging          │
└─────────────┬─────────────────────────┬──────────────────────────┬─────────────┘
              │                         │                          │
┌─────────────▼───────────┐ ┌───────────▼────────┐ ┌───────────────▼────────────┐
│ PostgreSQL              │ │ MinIO              │ │ Redis                       │
│ · integratsiya bazasi   │ │ · kadr arxivi      │ │ · kesh (tarif, zona geom.)  │
│ · RLS tenant izolyatsiya│ │ · 90 kun full +    │ │ · rate-limit / lock         │
│ · capture_runs navbati  │ │   1 yil siqilgan   │ │ · SSE fan-out (pub/sub)     │
│ · notifications outbox  │ │                    │ │ · YO'Q: biznes holati       │
└─────────────────────────┘ └────────────────────┘ └─────────────────────────────┘
              ▲
              │  Servislar bir-birini deyarli chaqirmaydi — integratsiya PostgreSQL orqali
┌─────────────┴─────────────────────────────────────────────────────────────────┐
│  Sidecar / tashqi:  go2rtc (live view)  ·  WireGuard (host)  ·  Hikvision NVR  │
│                     Sentry  ·  Telegram Bot API  ·  backup (dump + mc mirror)  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Nimaga egalik qiladi (write ownership) | Odatiy implementatsiya |
|-----------|----------------------------------------|------------------------|
| **core-api** | `markets, users, zones, stalls, product_categories, tariffs, vendors, stall_assignments, cameras, camera_zones, snapshot_schedules, occupancy_reviews, daily_charges, charge_adjustments, payments, billing_runs, stall_day_occupancy(frozen), reconciliation_reports, notifications(insert), audit_log` | FastAPI + SQLAlchemy 2.0 async; domain service layer; in-process APScheduler faqat billing/domain job'lari uchun (advisory lock bilan) |
| **cv-service** | `capture_runs, snapshots, occupancy_events, detector_runs, camera_health` | FastAPI (faqat internal/health endpoint'lar) + tick scheduler + ikkita worker task (capture, detect); ONNX Runtime CPU inference alohida process pool'da |
| **bot-service** | `notifications(status update), vendor_telegram_links` | aiogram 3.x; outbox poller (`FOR UPDATE SKIP LOCKED`) + token-bucket throttling; long polling (webhook emas — nginx sozlash kamayadi) |
| **packages/sbozor-core** | Hech qanday runtime holati — faqat kod | Editable install (`pip install -e ./packages/sbozor-core`) uchala image ichida; modellar + enum'lar + infra; **biznes logikasi yo'q** |
| **PostgreSQL** | Yagona haqiqat manbai (source of truth) | Postgres 16; RLS + composite FK; `capture_runs` va `notifications` navbat vazifasini ham bajaradi |
| **MinIO** | Kadr baytlari | Obyekt kaliti DB'da, URL emas; presigned URL faqat core-api tomonidan generatsiya qilinadi |
| **Redis** | Yo'qolishi mumkin bo'lgan ma'lumot | Kesh, rate-limit counter, SSE pub/sub. **Navbat yoki biznes holati uchun ishlatilmaydi** |
| **go2rtc** | Live stream sessiyalari | Sidecar konteyner; RTSP→WebRTC/HLS; nginx orqasida, `auth_request` bilan himoyalangan |

**Asosiy chegara qoidasi:** har bir jadvalning **aynan bitta yozuvchi servisi** bor. Qolganlari faqat o'qiydi. Bu compose ichidagi 3 servisni "taqsimlangan monolit" bo'lib qolishdan saqlaydi va race'larni yo'q qiladi.

---

## Recommended Project Structure

```
sbozor/
├── docker-compose.yml            # 3 servis + postgres + redis + minio + go2rtc + nginx
├── docker-compose.override.yml   # dev: hot reload, port mapping
├── .env.example
├── Makefile                      # make up / make migrate / make seed / make test
│
├── packages/
│   └── sbozor-core/              # UMUMIY paket — uchala servis import qiladi
│       ├── pyproject.toml
│       └── sbozor_core/
│           ├── models/           # SQLAlchemy 2.0 declarative — YAGONA schema ta'rifi
│           │   ├── base.py       # Base, TenantMixin(market_id), TimestampMixin
│           │   ├── market.py     # markets, zones, stalls, tariffs, vendors...
│           │   ├── camera.py     # cameras, camera_zones, snapshot_schedules
│           │   ├── vision.py     # capture_runs, snapshots, occupancy_events, reviews
│           │   ├── billing.py    # daily_charges, charge_adjustments, payments...
│           │   └── ops.py        # notifications (outbox), audit_log
│           ├── enums.py          # OccupancyStatus, CaptureStatus, PaymentMethod...
│           ├── db.py             # engine, session factory, tenant_session()
│           ├── tenancy.py        # RLS set_config helper, market_id contextvar
│           ├── storage.py        # MinIO/S3 klient, obyekt kalit sxemasi
│           ├── money.py          # BIGINT so'm, formatlash
│           ├── timeutil.py       # business_date(market_tz), UTC↔Asia/Tashkent
│           └── logging.py        # structured JSON log + request_id/market_id
│
├── services/
│   ├── core-api/
│   │   ├── Dockerfile
│   │   └── app/
│   │       ├── main.py           # lifespan: scheduler start (agar RUN_SCHEDULER=1)
│   │       ├── deps.py           # get_current_user, get_market_session (RLS)
│   │       ├── api/v1/           # routerlar: markets, stalls, tariffs, cameras,
│   │       │                     #   zones, review, billing, payments, reports, live
│   │       ├── domain/           # BIZNES LOGIKASI (shared paketda emas)
│   │       │   ├── billing/      # close_day.py, adjustments.py, debts.py
│   │       │   ├── reconcile/    # mismatch_report.py
│   │       │   ├── tariff/       # tarixiy tarif tanlash
│   │       │   └── audit/
│   │       ├── jobs/             # APScheduler job'lari: close_day, debt_reminder,
│   │       │                     #   digest_enqueue, report_retention
│   │       └── security/         # JWT, RBAC policy, RTSP parol shifrlash (Fernet/KMS)
│   │
│   ├── cv-service/
│   │   ├── Dockerfile            # ffmpeg + onnxruntime bazasida
│   │   └── app/
│   │       ├── main.py           # lifespan: tick + workerlarni ishga tushiradi
│   │       ├── scheduler/tick.py # har daqiqa: due slot → capture_runs materializatsiya
│   │       ├── capture/
│   │       │   ├── worker.py     # SKIP LOCKED claim → ffmpeg → MinIO → status
│   │       │   ├── ffmpeg.py     # buyruq qurish, timeout, kill, stderr parsing
│   │       │   └── quality.py    # qorong'ilik/blur tekshiruvi → skip_dark
│   │       ├── detect/
│   │       │   ├── worker.py     # SKIP LOCKED claim → inference → occupancy_events
│   │       │   ├── engine.py     # ONNX Runtime session (process pool ichida)
│   │       │   └── zones.py      # normallashtirilgan poligon, prepared geometry, PIP
│   │       ├── retention/        # 90 kun → siqish, 1 yil → o'chirish
│   │       └── api/internal.py   # POST /internal/cameras/{id}/test, /capture-now
│   │
│   └── bot-service/
│       ├── Dockerfile
│       └── app/
│           ├── main.py
│           ├── outbox.py         # poller + throttle (30 msg/s global, 1 msg/s/chat)
│           ├── handlers/vendor/  # ro'yxatdan o'tish, qoldiq, tarix
│           ├── handlers/director/# dayjest, nomuvofiqlik hisoboti
│           └── render/           # i18n matnlar, rasm-dalil biriktirish
│
├── migrations/                   # YAGONA Alembic env — core-api jamoasi egalik qiladi
│   ├── env.py                    # target_metadata = sbozor_core.models.Base.metadata
│   └── versions/
│
├── frontend/                     # Next.js + Tailwind
│   └── src/{app,components,lib,locales}/
│
├── ops/
│   ├── nginx/                    # reverse proxy + auth_request go2rtc uchun
│   ├── go2rtc/go2rtc.yaml.tmpl   # DB'dan generatsiya qilinadi
│   ├── backup/                   # pg_dump + mc mirror + tiklash skripti
│   └── wireguard/
└── tests/
    ├── unit/
    ├── integration/              # testcontainers: postgres + minio
    └── tenancy/                  # META-TEST: har jadvalda market_id + RLS yoqilganmi
```

### Structure Rationale

- **`packages/sbozor-core/`:** uchala servis bitta commit'da deploy bo'lgani uchun versiyalash muammosi yo'q — editable install yetarli. Paketda **faqat** modellar/enum/infra bo'ladi; biznes logikasi kirsa, u "yashirin 4-servis"ga aylanadi va o'zgarish uchala image'ni qayta test qilishni talab qiladi.
- **`services/*/app/domain/`:** biznes qoidalari (billing, rekonsiliatsiya) core-api ichida qoladi — CV yoki bot ularni chaqira olmaydi, faqat natijani DB'dan o'qiydi.
- **`migrations/` ildizda:** bitta baza → bitta migratsiya tarixi. Ikkita Alembic env (har servis uchun `version_table` bilan) bir bazada texnik jihatdan mumkin, lekin MVP'da bu murakkablik faqat zarar keltiradi — jadvallar bir-biriga FK bilan bog'langan.
- **`tests/tenancy/`:** multi-tenant xatolar eng qimmat regressiya. Meta-test har yangi jadval uchun `market_id` + RLS mavjudligini avtomatik tekshiradi.
- **`ops/go2rtc/*.tmpl`:** kamera ro'yxati DB'da yashaydi; go2rtc konfigi undan generatsiya qilinadi (yoki `PUT /api/streams` bilan runtime'da qo'shiladi) — ikki joyda qo'lda saqlanmaydi.

---

## Architectural Patterns

### Pattern 1: DB-materialized capture plan (tick scheduler + holat mashinasi)

**What:** Scheduler *ishni bajarmaydi* — u faqat "rejalashtirilgan slot"larni `capture_runs` jadvaliga materializatsiya qiladi. Ishni alohida worker `FOR UPDATE SKIP LOCKED` bilan olib bajaradi.

**When to use:** rejalashtirilgan tashqi I/O (RTSP) ishonchsiz bo'lsa va "o'tkazib yuborilgan snapshot" auditga tushishi kerak bo'lsa — ya'ni aynan bizning holat.

**Trade-offs:**
- (+) Restart, deploy, VPS reboot'ga chidamli — reja bazada.
- (+) Idempotent: `UNIQUE (market_id, camera_id, business_date, slot_local_time)`.
- (+) Kuzatuvchanlik tekin: "kamera offline" alert = deadline'dan keyin `pending/failed` qolgan qatorlar.
- (+) Jadval o'zgarishi (wizard'da) 1 daqiqada kuchga kiradi — job store sinxronizatsiyasi yo'q.
- (−) Har daqiqada bitta yengil DB so'rovi (arzimas).

**Example:**
```python
# cv-service/app/scheduler/tick.py — APScheduler'da ATIGI BITTA job
@scheduler.scheduled_job(CronTrigger(second=0))          # har daqiqa
async def tick() -> None:
    now = datetime.now(timezone.utc)
    async with system_session() as s:                     # cross-tenant, service role
        for market in await active_markets(s):
            local = now.astimezone(market.tz)             # Asia/Tashkent, DST yo'q
            # lookback: VPS 15 daqiqa o'chib qolsa ham slot yo'qolmaydi
            for slot in due_slots(market.schedule, local, lookback=timedelta(minutes=20)):
                await materialize(s, market, slot)

async def materialize(s, market, slot) -> None:
    await s.execute(
        insert(CaptureRun)
        .values([
            dict(market_id=market.id, camera_id=c.id,
                 business_date=slot.business_date, slot_local_time=slot.time,
                 scheduled_at=slot.utc, status=CaptureStatus.pending,
                 # thundering herd'dan saqlanish: kamera bo'yicha 0–90 s jitter
                 next_attempt_at=slot.utc + timedelta(seconds=jitter(c.id, 90)))
            for c in market.enabled_cameras
        ])
        .on_conflict_do_nothing(
            index_elements=["market_id", "camera_id", "business_date", "slot_local_time"]
        )
    )
```

```python
# capture worker — atomik claim
CLAIM = text("""
UPDATE capture_runs SET status='capturing', attempts=attempts+1,
       locked_by=:worker, locked_at=now()
WHERE id IN (
    SELECT id FROM capture_runs
    WHERE status IN ('pending','retry') AND next_attempt_at <= now()
    ORDER BY scheduled_at
    FOR UPDATE SKIP LOCKED
    LIMIT :batch
) RETURNING *""")
```

Holat mashinasi (bitta yo'nalishli, orqaga qaytish yo'q):
```
pending ──▶ capturing ──▶ captured ──▶ detecting ──▶ detected
   │             │            │             │
   │             ▼            │             ▼
   └────────▶ retry ◀─────────┘         detect_failed
                 │  (attempts < 3, eksponensial backoff)
                 ▼
              failed  ──▶ camera_health degraded ──▶ admin Telegram alert
```

---

### Pattern 2: O'zgarmas AI natija + review qoplamasi (HITL)

**What:** `occupancy_events` da AI bashorati **hech qachon o'zgartirilmaydi**. Nazoratchi qarori alohida `occupancy_reviews` qatori sifatida yoziladi. Amaldagi holat = `COALESCE(review.final_status, ai_status)`.

**When to use:** model aniqligini o'lchash talab qilinsa (9-bo'limdagi ≥90% mezoni) va tuzatishlar fine-tuning dataseti bo'lishi kerak bo'lsa.

**Trade-offs:**
- (+) Aniqlik hisoboti (AI vs inson) tekinga chiqadi — hech narsa yo'qolmagan.
- (+) Fine-tuning dataseti = `reviews JOIN snapshots` — alohida eksport quvuri kerak emas.
- (+) Detector versiyasini yangilab, eski kadrlarni qayta tahlil qilish mumkin (`detector_version` bilan) — billing'ga tegmasdan.
- (−) Ikkita jadvalni join qilish kerak; har o'qishda `COALESCE` — view bilan yashiriladi.

**Example:**
```sql
-- Kun davomidagi "jonli" bandlik — VIEW (yozuvchisi yo'q, doim aktual)
CREATE VIEW v_stall_day_occupancy AS
SELECT e.market_id, z.stall_id, s.business_date,
       bool_or(COALESCE(r.final_status, e.ai_status) = 'occupied') AS occupied,
       bool_or(COALESCE(r.final_status, e.ai_status) = 'uncertain') AS had_uncertain,
       (array_agg(e.id ORDER BY e.ai_confidence DESC)
          FILTER (WHERE COALESCE(r.final_status, e.ai_status) = 'occupied'))[1:3]
         AS evidence_event_ids
FROM occupancy_events e
JOIN snapshots s        ON s.id = e.snapshot_id
JOIN camera_zones z     ON z.id = e.camera_zone_id
LEFT JOIN occupancy_reviews r ON r.occupancy_event_id = e.id
WHERE e.detector_version = current_setting('app.active_detector')   -- backfill'lar aralashmasin
GROUP BY e.market_id, z.stall_id, s.business_date;
```

**Review navbati routing qoidasi** (uncertainty-based deferral — sanoat standarti):

```python
def triage(score: float, lo: float, hi: float) -> OccupancyStatus:
    if score >= hi:  return OccupancyStatus.occupied     # avto-qabul
    if score <= lo:  return OccupancyStatus.empty        # avto-qabul
    return OccupancyStatus.uncertain                      # → nazoratchi navbati
```
`lo`/`hi` **bozor bo'yicha sozlanadigan** bo'lishi shart: navbat hajmi nazoratchilar quvvatiga moslanadi (Karmanada ~1000 rasta × 7 kadr → 5% noaniq ham kuniga ~350 element; bu chegara). Navbatni prioritetlash: (1) biriktirilgan sotuvchisi bor rastalar, (2) yuqori tarifli toifalar, (3) qolganlari.

**Spetsifikatsiya qoidasi:** kun oxirigacha tasdiqlanmagan `uncertain` → `empty` sifatida hisoblanadi (kam hisoblash xavfsizroq). Bu qoida **bitta joyda** — `close_day` ichida — yashashi kerak, view'da emas.

---

### Pattern 3: Ikki fazali billing — kun davomida proyeksiya, kun oxirida o'zgarmas yozuv

**What:** Kun davomida kassir ko'radigan "kutilayotgan patta" **hech qachon jadvalga yozilmaydi** — u o'qish paytida hisoblanadi. Kun yopilganda bitta tranzaksiyada `daily_charges` ga **o'zgarmas** qator yoziladi. Keyingi har qanday o'zgarish faqat `charge_adjustments` orqali.

**When to use:** hisob-kitob kun davomida "shakllanib boradi", lekin yakuniy raqam auditga chidamli bo'lishi kerak bo'lganda. Bu Formance/Stripe uslubidagi immutable-ledger + reversal amaliyoti.

**Trade-offs:**
- (+) Qayta ishga tushirish (retry, qo'lda re-run) zararsiz — `ON CONFLICT DO NOTHING`.
- (+) Auditda "eski→yangi" tarixi tabiiy ravishda saqlanadi.
- (+) Kech kelgan review tuzatishi mavjud hisobotni buzmaydi — u `+adjustment` bo'lib ko'rinadi.
- (−) "Joriy summa" har doim `amount + Σ delta` — view bilan qoplanadi.
- (−) Bekor qilish ham qator qo'shadi (`delta = -amount`), UI buni "bekor qilingan" deb ko'rsatishi kerak.

**Example:**
```python
# core-api/app/domain/billing/close_day.py
async def close_day(s: AsyncSession, market_id: UUID, business_date: date,
                    triggered_by: UUID | None = None) -> BillingRun:
    # 1) Bir market-kun uchun bir vaqtning o'zida faqat bitta run (2 replica bo'lsa ham)
    key = advisory_key("billing", market_id, business_date)
    if not await s.scalar(select(func.pg_try_advisory_xact_lock(key))):
        raise BillingRunInProgress(market_id, business_date)

    run = await s.scalar(insert(BillingRun).values(
        market_id=market_id, business_date=business_date,
        kind="close_day", triggered_by=triggered_by).returning(BillingRun))

    # 2) Kun-darajali bandlikni MUZLATISH (view → jadval)
    #    uncertain → empty qoidasi shu yerda qo'llanadi
    await s.execute(text("""
        INSERT INTO stall_day_occupancy
            (market_id, stall_id, business_date, occupied, had_uncertain,
             evidence_event_ids, frozen_by_run)
        SELECT market_id, stall_id, business_date, occupied, had_uncertain,
               evidence_event_ids, :run
        FROM v_stall_day_occupancy
        WHERE market_id = :m AND business_date = :d
        ON CONFLICT (market_id, stall_id, business_date) DO NOTHING"""),
        {"m": market_id, "d": business_date, "run": run.id})

    # 3) Hisob yozish — faqat band VA biriktirilgan sotuvchisi bor rastalar
    #    Tarif business_date bo'yicha TARIXIY tanlanadi
    await s.execute(text("""
        INSERT INTO daily_charges
            (market_id, stall_id, business_date, vendor_id, tariff_id,
             amount_soum, billing_run_id)
        SELECT o.market_id, o.stall_id, o.business_date, a.vendor_id, t.id,
               t.daily_amount_soum, :run
        FROM stall_day_occupancy o
        JOIN stalls st ON (st.market_id, st.id) = (o.market_id, o.stall_id)
        JOIN stall_assignments a ON (a.market_id, a.stall_id) = (o.market_id, o.stall_id)
             AND o.business_date BETWEEN a.valid_from AND COALESCE(a.valid_to, 'infinity')
        JOIN tariffs t ON (t.market_id, t.category_id) = (st.market_id, st.category_id)
             AND o.business_date BETWEEN t.valid_from AND COALESCE(t.valid_to, 'infinity')
        WHERE o.market_id = :m AND o.business_date = :d
          AND o.occupied AND st.status = 'active'
        ON CONFLICT (market_id, stall_id, business_date) DO NOTHING"""),   -- ← idempotentlik
        {"m": market_id, "d": business_date, "run": run.id})

    # 4) Rekonsiliatsiya hisobotini yozib qo'yish (raqamlar keyin "siljib ketmasin")
    await build_reconciliation_report(s, market_id, business_date, run.id)
    # 5) Telegram xabarlarini outbox'ga qo'yish — SHU TRANZAKSIYADA
    await enqueue_evening_report(s, market_id, business_date, run.id)
    return run
```

**Recompute / tuzatish qoidasi** (hech qachon `UPDATE daily_charges`, hech qachon `DELETE + INSERT`):

| Vaziyat | Harakat |
|---|---|
| Job yarim yo'lda uzildi | Shunchaki qayta ishga tushiring — `ON CONFLICT DO NOTHING` dublikat yaratmaydi |
| Nazoratchi kun yopilgandan keyin "band" deb tasdiqladi | Yangi `daily_charges` qatori (agar yo'q bo'lsa) yoki `charge_adjustments(+tarif, reason='late_review')` |
| AI xato "band" degan, nazoratchi rad etdi | `charge_adjustments(delta = -amount, reason='ai_false_positive')` |
| Tarif noto'g'ri kiritilgan edi | `charge_adjustments(delta = new - old, reason='tariff_correction')` + tarif tarixini tuzatish |
| Detector versiyasi yangilandi, eski kunlar qayta tahlil qilindi | Billing'ga **ta'sir qilmaydi** — faqat aniqlik hisoboti uchun |

```sql
-- Amaldagi summa har doim shu view orqali o'qiladi
CREATE VIEW v_charge_balance AS
SELECT c.market_id, c.id AS charge_id, c.stall_id, c.business_date, c.vendor_id,
       c.amount_soum + COALESCE(a.delta, 0)                 AS effective_amount_soum,
       c.amount_soum + COALESCE(a.delta, 0) - COALESCE(p.paid, 0) AS balance_soum
FROM daily_charges c
LEFT JOIN LATERAL (SELECT sum(delta_soum) delta FROM charge_adjustments
                   WHERE charge_id = c.id) a ON true
LEFT JOIN LATERAL (SELECT sum(amount_soum) paid FROM payments
                   WHERE market_id = c.market_id AND stall_id = c.stall_id
                     AND business_date = c.business_date) p ON true;
```

`debts` — spetsifikatsiyada aytilganidek **hisoblanadigan ko'rinish** (jadval emas): `SUM(balance_soum) WHERE vendor_id IS NOT NULL AND balance_soum > 0`.

---

### Pattern 4: Multi-tenant izolyatsiya — composite kalit + RLS ikki qatlami

**What:** Ilova qatlamida tenant filtri (repository/dependency), DB qatlamida RLS himoya to'ri, sxema qatlamida composite FK. Uchtasi ham kerak — har biri boshqa turdagi xatoni ushlaydi.

**When to use:** shared-DB/shared-schema SaaS'da har doim. 2026 amaliyoti: "shared schema + RLS as safety net".

**Trade-offs:**
- (+) Dasturchi `WHERE market_id` yozishni unutsa ham, ma'lumot chiqmaydi (RLS ~1–5% overhead).
- (+) Composite FK **strukturaviy** himoya: A bozorining rastasi B bozorining to'loviga bog'lana olmaydi.
- (−) Composite FK'da `ON DELETE SET NULL` PG 15 gacha ishlamaydi (PG 16 da partial FK bor) — soft delete ishlating.
- (−) RLS'ni unutish oson → meta-test majburiy.

**Example:**
```sql
-- Sxema: har bir jadvalda (market_id, id) UNIQUE, FK'lar market_id ni ham olib yuradi
CREATE TABLE stalls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id UUID NOT NULL REFERENCES markets(id),
    number TEXT NOT NULL,
    category_id UUID NOT NULL,
    status stall_status NOT NULL DEFAULT 'active',
    UNIQUE (market_id, id),                       -- ← composite FK uchun target
    UNIQUE (market_id, number),
    FOREIGN KEY (market_id, category_id) REFERENCES product_categories(market_id, id)
);

CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id UUID NOT NULL,
    stall_id  UUID NOT NULL,
    business_date DATE NOT NULL,
    amount_soum BIGINT NOT NULL CHECK (amount_soum > 0),   -- pul: BIGINT, float emas
    method payment_method NOT NULL,
    cashier_id UUID NOT NULL,
    idempotency_key TEXT NOT NULL,
    FOREIGN KEY (market_id, stall_id) REFERENCES stalls(market_id, id),  -- ← cross-tenant imkonsiz
    UNIQUE (market_id, idempotency_key)            -- ← kassir ikki marta bosishi zararsiz
);

-- Indekslar: market_id DOIM birinchi ustun
CREATE INDEX ON payments (market_id, business_date, stall_id);
CREATE INDEX ON occupancy_events (market_id, snapshot_id);
CREATE INDEX ON capture_runs (status, next_attempt_at)
    WHERE status IN ('pending','retry');           -- ← partial index: navbat so'rovi uchun

-- RLS
ALTER TABLE stalls ENABLE ROW LEVEL SECURITY;
ALTER TABLE stalls FORCE  ROW LEVEL SECURITY;      -- ← owner ham bo'ysunsin (oson unutiladi!)
CREATE POLICY tenant_isolation ON stalls
    USING       (market_id = current_setting('app.market_id', true)::uuid)
    WITH CHECK  (market_id = current_setting('app.market_id', true)::uuid);
```

Ikkita DB roli:
| Rol | Vazifa | RLS |
|---|---|---|
| `sbozor_owner` | Alembic migratsiyalari, DDL | Egasi — DDL uchun |
| `sbozor_app` | core-api, bot-service (DML) | RLS **amal qiladi** |
| `sbozor_worker` | cv-service, tizim job'lari (cross-tenant tick) | `BYPASSRLS` — lekin kod darajasida market_id filtri majburiy |

```python
# core-api/app/deps.py — tenant kontekst HAR TRANZAKSIYADA, ulanishda emas
async def get_market_session(
    market_id: UUID = Path(...),
    user: User = Depends(get_current_user),
) -> AsyncIterator[AsyncSession]:
    if not user.can_access(market_id):
        raise HTTPException(403)
    async with SessionLocal() as s:
        async with s.begin():                       # tranzaksiya ochiladi
            await s.execute(
                text("SELECT set_config('app.market_id', :m, true)"),  # true = SET LOCAL
                {"m": str(market_id)},
            )
            yield s
```

> **Kritik pitfall:** `SET` (LOCAL'siz) ishlatilsa, qiymat pool'dagi ulanishda **qoladi** va keyingi so'rov boshqa bozor ma'lumotini ko'radi. Har doim `set_config(..., is_local => true)` yoki `SET LOCAL` — va faqat ochiq tranzaksiya ichida.

**Meta-test (majburiy):**
```python
def test_every_table_is_tenant_scoped(inspector):
    for t in inspector.get_table_names():
        if t in GLOBAL_TABLES:              # markets, alembic_version, platform_settings
            continue
        assert "market_id" in cols(t),          f"{t}: market_id yo'q"
        assert rls_enabled(t) and rls_forced(t), f"{t}: RLS yoqilmagan"
        assert leading_index_col(t) == "market_id", f"{t}: indeks market_id bilan boshlanmaydi"
```

---

### Pattern 5: Servislararo aloqa — DB integratsiya + outbox, Redis pub/sub emas

**What:** Uchala servis bitta PostgreSQL'ni bo'lishadi. Ma'lumot **holat jadvallari** orqali oqadi (polling), yo'qolishi mumkin bo'lmagan xabarlar **outbox** orqali. Redis faqat kesh/SSE uchun. Sinxron javob kerak bo'lgan kam sonli holatlarda internal HTTP.

**When to use:** bitta VPS, bitta jamoa, kam hajm (kuniga ~175 kadr/bozor). "Toza" event bus bu masshtabda faqat operatsion yuk.

**Trade-offs:**
- (+) Bitta backup, bitta tranzaksiya chegarasi, bitta monitoring nuqtasi.
- (+) Outbox → "kechki hisobot yuborilmay qoldi" holati imkonsiz (at-least-once + dedupe).
- (+) Polling latensiyasi 1–5 s — bu domen uchun mutlaqo yetarli.
- (−) Sxema o'zgarishi uchala servisga ta'sir qiladi → shuning uchun bitta migratsiya egasi.
- (−) Kelajakda alohida deploy kerak bo'lsa, jadval egaligini API'ga aylantirish kerak (lekin egalik matritsasi bu ko'chishni oldindan chizib qo'ygan).

| Aloqa | Kanal | Sabab |
|---|---|---|
| core-api → cv-service: "kamera qo'shildi / jadval o'zgardi" | **DB** (`cameras`, `snapshot_schedules`) — tick keyingi daqiqada ko'radi | Yo'qolmaydi, alohida kod yo'q |
| core-api → cv-service: "kamerani hozir sinab ko'r" | **Internal HTTP** `POST /internal/cameras/{id}/test` (service token) | Foydalanuvchi javobni kutib turadi |
| cv-service → core-api: yangi occupancy natijalari | **DB** (`occupancy_events`) + Redis pub/sub → SSE (faqat UI yangilanishi) | Haqiqat DB'da; pub/sub yo'qolsa UI 5 s dan keyin poll qiladi |
| core-api → bot-service: xabar yuborish | **DB outbox** (`notifications`) | Telegram yuborishi tranzaksiya bilan atomik bo'lishi kerak |
| bot-service → core-api: sotuvchi qoldiqni so'radi | **DB o'qish** (view orqali) | Read-only, HTTP hop keraksiz |
| har uchalasi → admin alert | **DB outbox** (`notifications`, channel='admin') | Bitta yo'l, bitta throttle |

```python
# bot-service/app/outbox.py — at-least-once + Telegram rate limitlari
POLL = text("""
UPDATE notifications SET status='sending', attempts=attempts+1, locked_at=now()
WHERE id IN (SELECT id FROM notifications
             WHERE status IN ('pending','retry') AND next_attempt_at <= now()
             ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 25)
RETURNING *""")

# Telegram: ~30 msg/s global, ~1 msg/s bitta chatga. 1000 sotuvchiga eslatma ≈ 35 s.
# Global token bucket + chat bo'yicha oxirgi-yuborilgan vaqt Redis'da.
```

`notifications` da `UNIQUE (market_id, dedupe_key)` — masalan `debt_reminder:{vendor_id}:{date}`. Shu bilan job ikki marta ishlasa ham sotuvchi ikkita bir xil xabar olmaydi.

---

### Pattern 6: Kamera zonalari — normallashtirilgan poligon + anchor-point agregatsiya

**What:** Poligonlar **normallashtirilgan** `[0..1]` koordinatalarda JSONB sifatida saqlanadi. Point-in-polygon Python'da (shapely, prepared geometry) hisoblanadi. PostGIS **kerak emas** — bu geografik emas, kadr fazosidagi geometriya.

**When to use:** CCTV zona tahlili. Frigate ham xuddi shu konvensiyani ishlatadi (nisbiy koordinatalar + bbox pastki markazi).

**Trade-offs:**
- (+) Kamera rezolyutsiyasi o'zgarsa yoki substream ishlatilsa, zonalar buzilmaydi.
- (+) PostGIS image'i, kengaytmasi va migratsiya murakkabligi yo'q.
- (+) Prepared geometry bilan 1000 zona × 50 deteksiya ≈ millisekundlar.
- (−) SQL'da "shu nuqta qaysi zonada" so'rovini yoza olmaysiz (kerak emas — cv-service qiladi).

```sql
CREATE TABLE camera_zones (
    id UUID PRIMARY KEY,
    market_id UUID NOT NULL,
    camera_id UUID NOT NULL,
    stall_id  UUID NOT NULL,
    polygon   JSONB NOT NULL,          -- [[0.12,0.44],[0.31,0.41],...]  normallashtirilgan
    version   INT  NOT NULL DEFAULT 1, -- qayta chizilganda oshadi
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to   TIMESTAMPTZ,            -- eski geometriya o'chirilmaydi (dalil auditi)
    FOREIGN KEY (market_id, camera_id) REFERENCES cameras(market_id, id),
    FOREIGN KEY (market_id, stall_id)  REFERENCES stalls(market_id, id)
);
CREATE INDEX ON camera_zones (market_id, camera_id) WHERE valid_to IS NULL;
```
`occupancy_events` da `camera_zone_id` + `zone_version` saqlanadi → "bu hisob qaysi geometriya bo'yicha chiqarilgan" savoli auditda javobsiz qolmaydi.

```python
# cv-service/app/detect/zones.py
@dataclass(frozen=True)
class ZoneGeom:
    zone_id: UUID; stall_id: UUID
    poly: Polygon                     # normallashtirilgan fazoda
    prepared: PreparedGeometry        # shapely.prepared.prep(poly) — takroriy contains uchun

def zone_signals(det: Detection, z: ZoneGeom) -> ZoneSignal:
    # 1) ODAM uchun: bbox pastki markazi (oyoq turgan joy) — Frigate konvensiyasi
    anchor = Point((det.x1 + det.x2) / 2, det.y2)
    person_inside = det.label == "person" and z.prepared.contains(anchor)
    # 2) MAHSULOT uchun: qoplama nisbati (quti zonaning qanchasini egallagan)
    inter = z.poly.intersection(box(det.x1, det.y1, det.x2, det.y2)).area
    coverage = inter / z.poly.area if z.poly.area else 0.0
    return ZoneSignal(person_inside, coverage, det.score)
```

**Agregatsiya iyerarxiyasi (uch qavat, har biri alohida sinaladi):**
```
deteksiya ──▶ zona natijasi        (1 kadr × 1 zona)  → band/bo'sh/noaniq  [occupancy_events]
zona natijalari ──▶ rasta-kadr     (bir necha kamera) → OR: birortasi band → band
rasta-kadr ──▶ rasta-kun           (7 kadr)           → OR: birortasi band → band  [v_stall_day_occupancy]
rasta-kun ──▶ hisob                (kun yopilganda)   → to'liq kunlik tarif  [daily_charges]
```
> Frigate'dagi `inertia` (ketma-ket kadrlar) bizda **qo'llanilmaydi** — bizda video emas, kuniga 7 mustaqil kadr. Uning o'rniga ikki ostonali `noaniq` zonasi va kun-darajali OR ishlaydi.

---

### Pattern 7: go2rtc — live view uchun alohida failure domain

**What:** go2rtc **faqat** jonli ko'rish uchun sidecar. Snapshot capture esa cv-service ichidagi to'g'ridan-to'g'ri `ffmpeg` subprocess orqali.

**Why:** snapshot — billing dalili; live view — qulaylik. Ikkalasi bitta process'da bo'lsa, direktor 10 ta stream ochib 4 vCPU'ni to'ldirganda ertalabki 06:00 kadrlari yo'qoladi.

**Alternativa (hujjatlashtirilgan zaxira):** go2rtc'da `GET /api/frame.jpeg?src=cam1&cache=10s` endpoint'i bor va streamlarni runtime'da `PUT /api/streams?name=&src=` bilan qo'shish mumkin. Agar biror kamerada to'g'ridan-to'g'ri RTSP beqaror bo'lsa, o'sha kamera uchun capture manbasini go2rtc'ga o'tkazish mumkin — `cameras.capture_backend` ustuni bilan (`ffmpeg` | `go2rtc`).

```bash
# ffmpeg capture — ishonchli variant
ffmpeg -hide_banner -loglevel error \
  -rtsp_transport tcp \          # UDP'da kadr yo'qoladi; TCP majburiy
  -timeout 8000000 \             # soket I/O timeout, MIKROSEKUND (ffmpeg ≥5; eski nomi -stimeout)
  -i "rtsp://user:pass@10.8.0.5:554/Streaming/Channels/101" \
  -frames:v 1 -q:v 3 -f image2 -y /tmp/frame.jpg
```
> **Versiya tuzog'i:** `-stimeout` ffmpeg 5.0 da `-timeout` ga qayta nomlangan va ffmpeg 8 da butunlay olib tashlangan. Docker image tegini **qat'iy pin qiling** (`jrottenberg/ffmpeg:7.1-...` yoki o'z base image'ingiz) va bayroqni bir marta integratsiya testida tasdiqlang. Har holda tashqi backstop shart:
```python
proc = await asyncio.create_subprocess_exec(*cmd, stderr=PIPE)
try:
    await asyncio.wait_for(proc.communicate(), timeout=25)   # ffmpeg osilib qolsa ham
except asyncio.TimeoutError:
    proc.kill(); raise CaptureTimeout()
```

**Tarmoq chegarasi:** WireGuard'ni **host darajasida** ishga tushiring (`wg-quick`), konteynerlar NVR IP'lariga oddiy routing bilan chiqadi. `network_mode: service:wireguard` varianti konteynerni o'z network namespace'idan mahrum qiladi va compose DNS bilan xizmat topishni buzadi — 3 servisli setup uchun ortiqcha murakkablik.

**Xavfsizlik chegarasi:** go2rtc'da foydalanuvchi darajasidagi auth yo'q → u **hech qachon** to'g'ridan-to'g'ri internetga chiqmaydi. nginx `auth_request` core-api'ga murojaat qilib, foydalanuvchining shu bozor kamerasiga huquqi borligini tekshiradi.

---

### Pattern 8: Audit — service layer'da, aktor contextvar orqali

**What:** Audit yozuvi biznes amali bilan **bir tranzaksiyada** yoziladi. Aktor (`user_id`, `ip`, `request_id`) `contextvar` orqali uzatiladi; SQLAlchemy `before_flush` hook'i `AuditedMixin` ga ega modellarning old→new farqini yozadi.

**Trade-offs:** (+) Hech qanday endpoint unutilmaydi. (−) Contextvar background job'larda qo'lda o'rnatiladi (`actor='system:billing'`).

---

## Data Flow

### Flow 1: Snapshot → dalil (cv-service, kuniga 7 marta)

```
[tick, har daqiqa]
      │  due slot? (market TZ)
      ▼
capture_runs INSERT ... ON CONFLICT DO NOTHING   ← idempotentlik nuqtasi #1
      │
      ▼  (capture worker: SKIP LOCKED claim, bounded concurrency 4–6)
ffmpeg -rtsp_transport tcp ... -frames:v 1        ── xato ──▶ retry (2 marta, backoff)
      │                                                          │ tugadi
      ▼                                                          ▼
sifat tekshiruvi (qorong'ilik/blur)                        status=failed
      │  qorong'i → status=captured_dark (arxivga, tahlilga emas)  │
      ▼                                                          ▼
MinIO PUT  market/{mid}/cam/{cid}/{YYYY-MM-DD}/{HHMM}.jpg   camera_health++ ▶ admin alert
      │
      ▼
snapshots INSERT (object_key, sha256, w, h, business_date)
      │
      ▼  (detect worker: SKIP LOCKED claim)
ONNX Runtime inference (process pool, intra_op=2)   ← event loop'ni BLOKLAMAYDI
      │
      ▼  zone_signals() → ikki ostonali triage
occupancy_events INSERT (ai_status, ai_confidence, detector_version, zone_version)
      │
      ├── uncertain ──▶ nazoratchi navbati (core-api'dagi view orqali ko'rinadi)
      └── Redis PUBLISH occupancy:{market_id} ──▶ core-api SSE ──▶ panel xaritasi jonlanadi
```

### Flow 2: Kun davomidagi kassir oqimi (≤3 bosish)

```
Kassir: rasta raqamini kiritadi
      │
      ▼  GET /api/v1/markets/{m}/stalls/{n}/today
core-api: v_stall_day_occupancy (jonli)  +  v_charge_balance (eski qarz)
      │      ↑ hech narsa YOZILMAYDI — bu proyeksiya
      ▼
"Kutilayotgan patta: 15 000 so'm + qarz 30 000 = 45 000"   [tarifdan avtomatik]
      │
      ▼  POST /payments  {method, amount, idempotency_key}
payments INSERT (UNIQUE market_id+idempotency_key)   ← idempotentlik nuqtasi #2
      + audit_log INSERT (bir tranzaksiyada)
      + summa tarifdan farq qilsa: reason_code MAJBURIY
```

### Flow 3: Kun yopilishi → rekonsiliatsiya → Telegram (core-api + bot-service)

```
[APScheduler, 23:30 Asia/Tashkent]  yoki  POST /internal/billing/close (qo'lda)
      │
      ▼  pg_try_advisory_xact_lock(market, date)      ← bir vaqtda bitta run
BEGIN
  stall_day_occupancy  ← v_stall_day_occupancy dan MUZLATILADI (uncertain→empty)
  daily_charges        ← INSERT ON CONFLICT DO NOTHING  ← idempotentlik nuqtasi #3
  reconciliation_reports ← hisoblab, JSONB natija bilan saqlanadi
       ├─ "band, lekin to'lovsiz"     : charge bor, balance > 0
       ├─ "ro'yxatga olinmagan savdo" : occupied=true, assignment YO'Q → charge yozilmaydi
       └─ "noaniq kunlar"             : had_uncertain=true → hisobotda alohida belgi
  notifications  ← INSERT (dedupe_key='evening_report:{market}:{date}')   ← outbox
COMMIT
      │
      ▼  (bot-service poller, 2 s)
SKIP LOCKED claim ▶ throttle (30/s, 1/chat/s) ▶ Telegram sendMessage/sendPhoto
      │                                                │ 429
      ▼                                                ▼
status='sent', sent_at, telegram_file_id          retry + backoff
```

> **Dalil rasmlari:** bot MinIO'dan baytlarni **ichkaridan** o'qib Telegram'ga yuklaydi (MinIO tashqariga ochilmaydi). Telegram qaytargan `file_id` saqlanadi — takroriy yuborishda qayta yuklash shart emas.

### Flow 4: Review → aniqlik hisoboti → fine-tuning dataseti

```
Nazoratchi navbati (uncertain, prioritetlangan)
      │  POST /reviews {event_id, final_status, note}
      ▼
occupancy_reviews INSERT   (ai_status HECH QACHON o'zgartirilmaydi)
      │
      ├──▶ v_stall_day_occupancy avtomatik yangilanadi → kassir/xarita darhol ko'radi
      ├──▶ Aniqlik hisoboti: confusion matrix (ai_status × final_status) — ≥90% mezoni
      └──▶ Dataset eksporti: reviews ⋈ snapshots ⋈ camera_zones → GPU ijarasida fine-tuning
              │
              ▼  yangi detector_version
      Arxivdagi kadrlarni QAYTA tahlil qilish (backfill) — billing'ga tegmasdan,
      faqat "yangi model eski kunlarda qanday ishlar edi" savoliga javob
```

---

## Scaling Considerations

Yuk profili: **1 bozor ≈ 25 kamera × 7 kadr = 175 kadr/kun**. Bu "katta ma'lumot" emas — arxitektura murakkabligi hajmdan emas, **ishonchlilik va auditdan** kelib chiqadi.

| Scale | Arxitektura o'zgarishi |
|-------|------------------------|
| **1 bozor (Karmana pilot)** | Hech narsa. Bitta compose, bitta cv-service, uvicorn 1–2 worker. Inference ≈ 175 × 1 s ≈ 3 daqiqa/kun. |
| **5–20 bozor** | Slot'larni bozorlar bo'yicha **jitter** qiling (hammasi 06:00 da NVR'larga urilmasin). `snapshots`/`occupancy_events` uchun oylik partitioning. cv-service worker konkurentligini 4→8 ga oshiring. |
| **20–50 bozor** | **Disk birinchi cheklov** (quyida hisob). MinIO'ni alohida diskka/S3'ga chiqarish. cv-service'ni bir xil image'dan ikki komanda bilan bo'lish: `scheduler` (1 ta) + `worker` (N ta) — bu servislar sonini oshirmaydi, faqat replica. |
| **50+ bozor / davlat bosqichi** | Read replica hisobotlar uchun; Postgres navbatini alohida broker'ga (Redis Streams / NATS) ko'chirish; O'zbekiston hostingiga migratsiya (compose buni arzon qiladi). |

### Scaling Priorities

1. **Birinchi buzilish nuqtasi — disk (MinIO).** Bozor uchun: 175 kadr/kun × ~0.5 MB ≈ 87 MB/kun → 90 kun full ≈ **8 GB**; siqilgan 1 yillik nusxa (~120 KB) ≈ **8 GB**. Barqaror holatda **≈16 GB/bozor/yil**. 400 GB diskdan DB+backup uchun ~50 GB ayirsak → **~20 bozor**. Yechim: retention job'i 1-kundan ishlasin (keyin qo'shish = disk to'lgach favqulodda ish).
2. **Ikkinchi — 06:00 dagi burst.** Barcha bozorlar/kameralar bir vaqtda RTSP so'rasa, VPN va NVR bo'g'iladi. Yechim boshidan: kamera bo'yicha deterministik jitter (0–90 s) + `Semaphore(4..6)`.
3. **Uchinchi — CPU inference vs API javob vaqti.** ONNX Runtime'ni `intra_op_num_threads=2` bilan cheklang va **alohida process**da (ProcessPoolExecutor) ishlating; `run_in_executor` bilan event loop'ni bloklamang. Aks holda 06:00 da panel "muzlaydi".
4. **To'rtinchi — hisobot so'rovlari.** `v_stall_day_occupancy` view'i oylik hisobotlarda sekinlashadi → `stall_day_occupancy` muzlatilgan jadvalidan o'qing (u allaqachon bor, chunki billing uni yozadi).

---

## Anti-Patterns

### Anti-Pattern 1: Kun davomida "kutilayotgan patta"ni jadvalga yozish

**What people do:** birinchi "band" snapshot'da `daily_charges` ga `status='draft'` qator yozadi, keyin kun davomida `UPDATE` qiladi.
**Why it's wrong:** job ikki marta ishlasa dublikat; nazoratchi tuzatsa summa "orqaga" o'zgaradi; kassir allaqachon chop etgan chek bilan mos kelmaydi; auditda "kim o'zgartirdi" javobi yo'q.
**Do this instead:** kun davomida — **o'qishda hisoblanadigan proyeksiya** (view). Kun oxirida — bitta o'zgarmas INSERT. Keyingi barcha o'zgarish `charge_adjustments`.

### Anti-Pattern 2: Kunni qayta hisoblash uchun `DELETE + INSERT`

**What people do:** "kechagi hisob noto'g'ri" → `DELETE FROM daily_charges WHERE business_date=...` va qayta yuritadi.
**Why it's wrong:** to'lovlar allaqachon o'sha charge'ga bog'langan; sotuvchiga yuborilgan Telegram xabari endi mavjud bo'lmagan hisobga ishora qiladi; audit uziladi.
**Do this instead:** `ON CONFLICT DO NOTHING` bilan yetishmagan qatorlarni qo'shish + farqlarni `charge_adjustments` bilan yopish. `billing_runs` da har urinish qayd etiladi.

### Anti-Pattern 3: APScheduler job store'ini snapshot jadvalining haqiqat manbai qilish

**What people do:** har bozor × har slot uchun alohida persistent job yaratadi; wizard'da jadval o'zgarganda job'larni qo'lda sinxronlaydi.
**Why it's wrong:** job store va DB o'rtasida drift; o'chirilgan bozorning job'lari qoladi; APScheduler **4.x hozircha alpha** (pre-release, "production'da ishlatmang" deb ogohlantirilgan), 3.x esa cross-process koordinatsiya bermaydi.
**Do this instead:** APScheduler 3.x + **MemoryJobStore** + **atigi bitta** `tick` job'i. Butun reja `snapshot_schedules` va `capture_runs` da.

### Anti-Pattern 4: Redis pub/sub orqali muhim hodisalarni uzatish

**What people do:** "kun yopildi" yoki "hisobot tayyor" xabarini `PUBLISH` bilan bot-service'ga yuboradi.
**Why it's wrong:** Redis pub/sub — at-most-once, persistence yo'q. Bot-service deploy paytida 3 soniya o'chsa, kechki nomuvofiqlik hisoboti **butunlay yo'qoladi** va hech kim buni bilmaydi.
**Do this instead:** `notifications` outbox jadvali (dedupe_key bilan) + poller. Pub/sub faqat "UI'ni yangila" kabi yo'qolishi mumkin bo'lgan signal uchun.

### Anti-Pattern 5: Zona poligonlarini piksel koordinatalarida saqlash

**What people do:** wizard'da chizilgan poligonni 1920×1080 piksel koordinatalarida yozadi.
**Why it's wrong:** NVR substream'ga o'tsa (704×576), yoki kamera almashtirilsa — barcha zonalar siljiydi va bandlik jimgina noto'g'ri hisoblanadi (billing xatosi!).
**Do this instead:** `[0..1]` normallashtirilgan koordinatalar + `frame_width/height` metadata + `zone_version`. Kamera burchagi o'zgarsa — yangi versiya, eskisi `valid_to` bilan yopiladi.

### Anti-Pattern 6: Inference'ni FastAPI event loop'ida bajarish

**What people do:** `async def detect(...)` ichida to'g'ridan-to'g'ri `session.run(...)`.
**Why it's wrong:** ONNX inference — CPU-bound, sinxron. 25 kadr ketma-ket ishlansa cv-service'ning healthcheck'i ham javob bermay qoladi va Docker uni restart qiladi (aynan capture paytida!).
**Do this instead:** worker'ni HTTP'dan butunlay ajrating (background task), inference'ni `ProcessPoolExecutor` da, thread sonini cheklab.

### Anti-Pattern 7: `SET app.market_id` (LOCAL'siz) va pool

**What people do:** ulanish olinganda `SET app.market_id = '...'`.
**Why it's wrong:** qiymat pool'dagi ulanishda qoladi → keyingi so'rov (boshqa bozor) eski kontekstni meros oladi. Bu SaaS'dagi eng jimgina va eng halokatli bug.
**Do this instead:** `set_config('app.market_id', :m, true)` faqat ochiq tranzaksiya ichida; har so'rov o'z tranzaksiyasida.

### Anti-Pattern 8: Bitta jadvalni ikki servis yozishi

**What people do:** cv-service ham, core-api ham `stall_day_occupancy` ni yangilaydi.
**Why it's wrong:** race condition, "kim oxirgi yozdi" mantig'i, tushunib bo'lmaydigan bug'lar; 3 servis "taqsimlangan monolit"ga aylanadi.
**Do this instead:** egalik matritsasini kod-review qoidasi qiling. Ikki tomon ham yozishi kerak bo'lsa — bu ikkita alohida jadval (fakt + qaror), ustidan view.

### Anti-Pattern 9: go2rtc yoki MinIO'ni to'g'ridan-to'g'ri internetga ochish

**Why it's wrong:** go2rtc'da per-user auth yo'q — havolani bilgan har kim bozor kameralarini ko'radi (shaxsiy ma'lumot + O'zR lokalizatsiya qonuni). MinIO ochiq bo'lsa dalil arxivi ochiq.
**Do this instead:** ikkalasi ham faqat ichki tarmoqda; nginx `auth_request` → core-api RBAC; rasm havolalari qisqa muddatli presigned URL yoki bot orqali bayt sifatida.

### Anti-Pattern 10: `business_date` ni UTC'dan olish

**Why it's wrong:** Asia/Tashkent = UTC+5. 18:00 dagi snapshot UTC'da 13:00 — bu tuzoq emas; lekin 23:30 dagi kun yopilishi UTC'da 18:30, va "kecha"ni UTC sanasi bo'yicha hisoblasangiz kun chegarasi 5 soatga siljiydi.
**Do this instead:** `business_date` — bozor timezone'ida hisoblangan `DATE` ustuni, snapshot yozilayotganda bir marta belgilanadi va keyin faqat shu ustun bo'yicha guruhlanadi. (Yaxshi xabar: O'zbekistonda DST yo'q — murakkablik minimal.)

---

## Integration Points

### External Services

| Service | Integration Pattern | Gotchas |
|---------|---------------------|---------|
| **Hikvision NVR (RTSP)** | `ffmpeg -rtsp_transport tcp` WireGuard tunnel orqali; kanal URL'i `/Streaming/Channels/{ch}01` (main) / `...02` (sub) | Parollar bazada shifrlangan (Fernet, kalit env'da); NVR bir vaqtda cheklangan sonli sessiya beradi → konkurentlikni cheklang; substream sifati zona tahliliga yetmasligi mumkin — pilotda o'lchang |
| **go2rtc** | Sidecar; `PUT /api/streams?name=&src=` bilan runtime qo'shish, `GET /api/stream.m3u8?src=`, WebRTC WS; zaxira snapshot: `GET /api/frame.jpeg?src=&cache=10s` | Auth yo'q → nginx orqasida; konfig DB'dan generatsiya qilinadi |
| **MinIO** | S3 API (boto3/aiobotocore); kalit sxemasi `market/{mid}/cam/{cid}/{YYYY-MM-DD}/{HHMM}_{uuid}.jpg`; DB'da **kalit**, URL emas | Lifecycle policy'ni MinIO'ga tashlab qo'ymang — retention job'i siqilgan nusxa yaratishi kerak (oddiy delete emas) |
| **Telegram Bot API** | aiogram 3.x long polling; outbox poller | **30 msg/s global, ~1 msg/s bitta chatga, guruhga 20 msg/min**; 1000 sotuvchiga eslatma ≈ 35 s → throttle majburiy; 429 da `retry_after` ni hurmat qiling; `file_id` ni keshlang |
| **Sentry** | SDK uchala servisda; `market_id` va `request_id` tag sifatida | PII (sotuvchi F.I.Sh./telefon) event'larga tushmasin — `before_send` filtri |
| **WireGuard** | Host darajasida `wg-quick`; konteynerlar oddiy routing bilan | `network_mode: service:wg` compose DNS'ni buzadi — tavsiya etilmaydi |
| **Backup** | `pg_dump` + `mc mirror` boshqa lokatsiyaga; kunlik cron | **Tiklash mashqi** kamida bir marta — tekshirilmagan backup = backup emas |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| core-api ↔ cv-service | Asosan **DB** (jadval egaligi bilan); sinxron buyruqlar uchun internal HTTP (service token, faqat ichki tarmoq) | cv-service `cameras/camera_zones/snapshot_schedules` ni faqat **o'qiydi** |
| cv-service ↔ core-api (natijalar) | **DB** + Redis pub/sub (faqat SSE fan-out) | Haqiqat DB'da; pub/sub yo'qolsa UI 5 s poll bilan tiklanadi |
| core-api ↔ bot-service | **DB outbox** (`notifications`) bir yo'nalishda; bot read-only view'lardan o'qiydi | Bot core-api HTTP'ini chaqirmaydi — bitta bog'liqlik kamayadi |
| Uchala servis ↔ sxema | `packages/sbozor-core` (modellar) + **yagona** Alembic | Migratsiya compose'da alohida **one-shot job** sifatida ishga tushadi, app startup'da emas |
| Panel ↔ live view | nginx `auth_request` → core-api → go2rtc | Foydalanuvchi go2rtc URL'ini hech qachon to'g'ridan-to'g'ri olmaydi |

---

## Build Order (Dependency-Driven)

Tartib **bog'liqlik** va **xavfni erta ochish** tamoyillari bo'yicha, 12 haftalik reja bilan moslashtirilgan.

| # | Blok | Nega shu tartibda | Bog'liqligi |
|---|------|-------------------|-------------|
| **0** | **Fundament:** monorepo + compose + `sbozor-core` + Alembic (yagona) + 2 DB roli + RLS/tenant session + auth/RBAC + audit_log + i18n skaffolding + healthcheck/Sentry/CI | Tenant izolyatsiyasi, audit va i18n — **retrofit qilinmaydigan** narsalar. 8-haftada RLS qo'shish = har bir endpoint'ni qayta test qilish. Meta-test shu yerda yoziladi. | — |
| **1** | **Bozor domeni:** markets, zones, stalls, product_categories, tariffs (tarixiy), vendors, stall_assignments + wizard'ning ma'lumot qadamlari + sxematik plan-xarita | CV ham, billing ham `stalls` va `tariffs` ga tayanadi. Karmana ma'lumotlari erta kiritilsa, keyingi bloklar real ma'lumotda sinaladi. | 0 |
| **2** | **Kamera va tarmoq:** WireGuard, cameras CRUD (shifrlangan RTSP), ulanish testi, go2rtc live view | **Eng yuqori tashqi xavf** (NVR login/parolni bozor ma'muriyati beradi). Bu ishlamasa butun mahsulot ishlamaydi → imkon qadar erta isbotlang. Live view shu yerda "tekin" chiqadi. | 0, 1 |
| **3** | **Capture pipeline (AI'siz):** snapshot_schedules, tick, capture_runs holat mashinasi, ffmpeg, MinIO, retry, o'tkazib yuborilgan snapshot alerti, retention job'i | **Eng muhim tartib qarori:** kadrlar — doimiy aktiv, deteksiya esa qayta ishlanadigan. Bu blok prod'da ishlab turgan vaqtda CV yozilaveradi → 7-8 haftaga kelib **haqiqiy Karmana kadrlari** ostona sozlash va fine-tuning uchun tayyor bo'ladi. | 2 |
| **4** | **Zona muharriri + detektor v1 + review:** camera_zones (normallashtirilgan poligon), detect worker, occupancy_events, ikki ostonali triage, nazoratchi navbati, aniqlik hisoboti asosi | Poligon muharriri — eng og'ir frontend qism (spec 10-bo'lim), lekin 3-blok tayyor bo'lgach real kadr ustida chiziladi. Review'siz aniqlikni o'lchab bo'lmaydi. | 1, 3 |
| **5** | **Billing + kassir:** close_day job'i (advisory lock + ON CONFLICT), stall_day_occupancy muzlatish, daily_charges, charge_adjustments, payments (idempotency key), debts view | occupancy_events'siz hisoblash uchun kirish ma'lumoti yo'q. Kassir moduli hisobning proyeksiyasiga tayanadi. | 1, 4 |
| **6** | **Rekonsiliatsiya + bildirishnomalar + botlar:** mismatch report (2 anomaliya turi), notifications outbox, throttling, sotuvchi boti, direktor dayjest/kechki hisobot | Hisobotning kirish ma'lumoti — 5-blok. Outbox 5-blok tranzaksiyasiga ulanadi. | 5 |
| **7** | **Hisobotlar va yakun:** Excel eksport, AI aniqlik hisoboti, 3 til sayqali, backup tiklash mashqi, jonli ishga tushirish runbook'i, parallel rejim solishtirish vositasi | Barcha ma'lumot manbalari mavjud bo'lgach. Parallel rejim (2–4 hafta) uchun "eski usul vs tizim" solishtirish ekrani kerak. | 5, 6 |

**Kritik tartib qoidalari:**
1. **Capture (3) deteksiyadan (4) oldin.** Kadrlar arxivi qayta ishlatiladi; deteksiya esa `detector_version` bilan istalgan vaqtda qayta yuritiladi. Teskarisi mumkin emas — o'tgan kunning kadri qaytmaydi.
2. **Tenant + audit (0) hamma narsadan oldin.** Bu ikkisi keyin qo'shilsa, har bir yozilgan endpoint qayta ko'rib chiqiladi.
3. **Kamera ulanishi (2) CV rejasidan oldin.** NVR kirishi 2 hafta kechiksa, butun 3–4 bloklar siljiydi — buni 5-haftada emas, 3-haftada bilish kerak.
4. **i18n 1-haftadan.** Spec buni alohida ta'kidlaydi; matnlar tarqalgach yig'ish qimmat.
5. **Billing (5) faqat review (4) tayyor bo'lgach.** `uncertain → empty` qoidasi review oqimisiz ma'nosiz va hisobni asossiz kamaytiradi.

**Chuqurroq tadqiqot talab qiladigan bloklar:** 4 (detektor tanlash, ostonalar, CPU tezligi, Apache-2.0 model eksporti), 3 (ffmpeg/Hikvision o'ziga xosliklari, erta tong yorug'ligi), 2 (VPN + NVR sessiya cheklovlari).

---

## Sources

**Context7 / rasmiy hujjatlar (HIGH confidence):**
- go2rtc API — `/alexxit/go2rtc` (Context7): `GET /api/frame.jpeg?src=&w=&h=&cache=`, `PUT /api/streams?name=&src=`, `GET /api/stream.m3u8?src=`, MSE/WebRTC WS
- APScheduler — `/agronholm/apscheduler` (Context7): `misfire_grace_time`, `CoalescePolicy`, `max_running_jobs`, SQLAlchemy data store sxemasi
- Frigate zonalari — https://docs.frigate.video/configuration/zones/ : nisbiy (0–1) koordinatalar, "presence evaluated based on the **bottom center** of the bounding box", `inertia`
- Telegram Bot API cheklovlari — https://core.telegram.org/bots/faq : ~30 msg/s global, ~1 msg/s bitta chatga, guruhga 20 msg/min
- Shapely (BSD-3) — https://shapely.readthedocs.io/ : `prepared` geometry, `contains`, `intersection`

**Verifikatsiyalangan web manbalar (MEDIUM confidence):**
- APScheduler 4.0 holati (alpha, "should NOT be used in production") — https://github.com/agronholm/apscheduler/issues/465 , https://pypi.org/project/APScheduler/ (barqaror: 3.11.x)
- `FOR UPDATE SKIP LOCKED` navbat pattern'i — https://www.netdata.cloud/academy/update-skip-locked/ , https://www.mgaillard.fr/2024/12/01/job-queue-postgresql.html (~100–200 job/s gacha yetarli — bizda kuniga 175)
- Multi-tenant RLS + `SET LOCAL` tuzog'i — https://ricofritzsche.me/mastering-postgresql-row-level-security-rls-for-rock-solid-multi-tenancy/ , https://planetscale.com/blog/approaches-to-tenancy-in-postgres , https://oneuptime.com/blog/post/2026-01-25-row-level-security-postgresql/view
- Composite FK bilan cross-tenant havolani bloklash — https://clickhouse.com/resources/engineering/multi-tenant-saas-postgres-architecture , https://planetscale.com/blog/approaches-to-tenancy-in-postgres
- O'zgarmas ledger + reversal/adjustment amaliyoti — https://www.formance.com/blog/financial-operations/account-reconciliation-patterns-for-high-volume-fintech , https://prachub.com/concepts/payment-systems-ledgers-idempotency-and-reconciliation
- Transactional outbox + dedupe key + poller — https://microservices.io/patterns/data/transactional-outbox.html , https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
- HITL uncertainty routing (ikki ostona, deferral policy) — https://123ofai.com/qnalab/system-design/blocks/human-in-loop , https://arxiv.org/html/2605.12303v1
- ffmpeg `-stimeout` → `-timeout` qayta nomlanishi va v8 da olib tashlanishi — https://patchwork.ffmpeg.org/project/ffmpeg/patch/20210419141024.8174-46-jamrial@gmail.com/ , https://github.com/seydx/homebridge-camera-ui/issues/1081
- FastAPI'da bloklovchi ML chaqiruvlari (`run_in_executor` / alohida process) — https://apxml.com/courses/fastapi-ml-deployment/chapter-5-async-operations-performance/running-blocking-ml-operations
- WireGuard + Docker tarmoq variantlari — https://www.procustodibus.com/blog/2022/02/wireguard-remote-access-to-docker-containers/ , https://www.linuxserver.io/blog/routing-docker-host-and-container-traffic-through-wireguard

**LOW confidence / pilotda tekshirilishi shart:**
- CPU inference tezligi (kadr uchun ~0.3–1.5 s) — model va VPS'ga qarab; 3-blokdan keyin real kadrlarda o'lchang
- JPEG kadr o'lchami (~0.5 MB) va shundan kelib chiqadigan disk hisobi — Karmana kameralarining haqiqiy rezolyutsiyasi bilan qayta hisoblang
- Hikvision NVR'ning bir vaqtdagi RTSP sessiya limiti — modelga bog'liq, 2-blokda o'lchanadi

---
*Architecture research for: multi-tenant bozor raqamlashtirish SaaS (CCTV → CV → billing → hisobot)*
*Researched: 2026-07-28*
