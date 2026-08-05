---
phase: 04-snapshot-pipeline
verified: 2026-08-05T01:45:12Z
status: gaps_found
score: 4/5 must-haves verified (SC#5 qisman)
overrides_applied: 0
re_verification:
  previous_status: null
  previous_score: null
  gaps_closed: []
  gaps_remaining: []
  regressions: []
gaps:
  - truth: "SC#5 — Kamera offline bo'lsa, slot o'tkazib yuborilsa yoki backup xato bersa — platforma adminiga Telegram-alert keladi va xato Sentry'da ko'rinadi (FOUND-06)"
    status: partial
    reason: "Telegram yarmi to'liq isbotlangan. Sentry yarmi FAQAT `core-api` va `worker` jarayonlarida ulangan. `scheduler` konteyneri `SENTRY_DSN` ni oladi, 4-fazaning HAMMA jobini tetiklaydi, lekin `init_sentry()` u yerda HECH QACHON chaqirilmaydi — o'lchandi, taxmin emas. Bu 04-12 ning O'ZI worker uchun topgan va yopgan nosozlik sinfining bitta jarayon nariga ko'chgan takrori."
    artifacts:
      - path: "services/core-api/app/worker.py"
        issue: "`init_sentry()` faqat `@broker.on_event(TaskiqEvents.WORKER_STARTUP)` ilmog'ida (satr 333/363). `taskiq scheduler` jarayonida `broker.is_worker_process` `False` bo'lib qoladi (taskiq `cli/scheduler/run.py:392` BOSHQA bayroqni — `is_scheduler_process` ni — o'rnatadi), ya'ni `AsyncBroker.startup()` (`abc/broker.py:187-194`) `CLIENT_STARTUP` ni ateshlaydi. Reyestrda `CLIENT_STARTUP` ilmog'i UMUMAN yo'q."
      - path: "tests/unit/test_sentry_scrub.py"
        issue: "`test_both_processes_install_sentry` AYNAN ikkita kirish nuqtasini (`lifespan`, `_open_worker_resources`) sanaydi — uchinchi jarayonni struktura jihatidan ko'ra olmaydi, shuning uchun darvoza yashil bo'lib qoladi."
      - path: "tests/integration/test_phase4_criteria.py"
        issue: "`SENTRY_ENTRYPOINTS` (satr 224-227) qattiq yozilgan 2 elementli kortej; `_assert_sentry_is_wired()` faqat shu ikkitasini o'qiydi. Docstring «YETTI EMAS, IKKI kirish nuqtasi» deydi — hisob KONTEYNER emas, KOD kirish nuqtasi bo'yicha yuritilgan va `scheduler` shu bo'shliqqa tushgan."
    missing:
      - "`@broker.on_event(TaskiqEvents.CLIENT_STARTUP)` ilmog'i (yoki `init_sentry()` ni `app/worker.py` modul darajasida / `scheduler` uchun alohida kirish nuqtasida chaqirish) — planer jarayonining istisnolari Sentry'ga borishi uchun"
      - "`SENTRY_ENTRYPOINTS` va `test_both_processes_install_sentry` ni JARAYON bo'yicha hisoblaydigan qilib kengaytirish — `compose.yaml` da `SENTRY_DSN` oladigan har konteyner uchun bitta o'lchangan kirish nuqtasi"
      - "Planer jarayonining `send_task` istisnosi yutilishini qoplash: taskiq `cli/scheduler/run.py:346-350` `add_done_callback` da istisnoni O'QIMAYDI, ya'ni broker yiqilsa tik jimgina to'xtaydi"
deferred:
  - truth: "Tashqi dead-man's switch (`/internal/self-check` ni tashqaridan so'rash) KOD bilan qurilmagan"
    addressed_in: "D-21 (fazaning O'Z qarori) + Phase 8"
    evidence: "D-21: «Tashqi dead-man's switch v1 da kod yozilmaydi — `ops/docs/monitoring.md` ga bitta URL sozlash yo'riqnomasi va ops bandi». `ops/docs/monitoring.md` §5 healthchecks.io/UptimeRobot yo'riqnomasi bilan mavjud; band `04-HUMAN-UAT.md` #5, egasi Ops"
  - truth: "Zaxira (`backup`) komponentining yurak urishi hech qachon yozilmagan — `/internal/self-check` uni `never_seen` da ko'rsatadi"
    addressed_in: "Phase 8"
    evidence: "Phase 8 mezoni: «backup mashqi, go-live»; FOUND-07 o'sha fazada. `self_check.py::EXPECTED_COMPONENTS` `backup` ni ATAYIN bugundan ro'yxatda saqlaydi"
human_verification:
  - test: "Sifat chegaralarini REAL Karmana kadrida sozlash (04-HUMAN-UAT #1)"
    expected: "06:00 va 18:00 kadrlarida `dark`/`blank` verdiktlari qonuniy kadrni rad etmaydi; chegaralar SQL bilan sozlanadi"
    why_human: "Chegaralar LOW confidence — real kadr yo'q. Sintetik JPEG MEXANIZMNI isbotlaydi, QIYMATNI emas. Egasi: nazoratchi + ijrochi; tetigi: Phase 0 kadrlari"
  - test: "90 kunlik saqlash siyosatining KALENDAR bo'yicha ishlashi (04-HUMAN-UAT #2)"
    expected: "90 kundan keyin birinchi `full -> compressed` to'lqini; 455 kundan keyin birinchi `purged`"
    why_human: "Vaqtni kutib bo'lmaydi. Test chegarani sozlama (`full_days=0`), vaqtni argument (`today=`) qilib mexanizmni isbotlaydi. Egasi: Ops; tetigi: go-live + 90 kun"
  - test: "Tiklash mashqi (restore drill) (04-HUMAN-UAT #3)"
    expected: "Zaxiradan to'liq tiklash hujjatlashtirilgan holda bajariladi"
    why_human: "Real ombor, real ma'lumot va toza server talab qiladi. Egasi: Ops; tetigi: go-live'dan oldin, Phase 8 (FOUND-07)"
  - test: "Telegram alertining HAQIQATAN yetib borishi (04-HUMAN-UAT #4)"
    expected: "Platforma admini Telegram'da guruhlangan xabarni oladi; xabarda rasm, havola va obyekt kaliti yo'q"
    why_human: "Token va chat ID CI'da yo'q. Egasi: Ops. ⚠ FOUND-06 ning `Done` holati shu bandga bog'liq"
  - test: "Tashqi dead-man's switch — `/internal/self-check` ni tashqaridan so'rash (04-HUMAN-UAT #5)"
    expected: "healthchecks.io/UptimeRobot 503 holatida ogohlantirish yuboradi"
    why_human: "Quti tashqarisidagi xizmat, D-21 bo'yicha kod yozilmaydi. Egasi: Ops"
  - test: "Real NVR'da bir vaqtdagi sessiya chegarasining kadr olishga ta'siri (04-HUMAN-UAT #6)"
    expected: "25 kamera ketma-ket olinganda NVR sessiya chegarasiga urilmaydi yoki `capture_stream_limit` bilan kechiktiriladi"
    why_human: "Simulyator sessiya chegarasini UMUMAN modellamaydi (3-faza tekshiruvida ochiq yozilgan). Egasi: Ops"
---

# Phase 4: Snapshot pipeline — Tekshiruv hisoboti

**Faza maqsadi:** Har kuni rejadagi kadrlar avtomatik olinadi, sifat tekshiruvidan o'tadi, ishonchli arxivlanadi va uzilish jim qolmaydi
**Tekshirildi:** 2026-08-05T01:45:12Z
**Holat:** `gaps_found`
**Qayta tekshiruv:** Yo'q — birinchi tekshiruv

---

## Maqsad bajarilishi

Maqsad jumlasining to'rt bandi alohida o'lchandi. Uchtasi to'liq bajarilgan;
to'rtinchisi — «uzilish jim qolmaydi» — **qisman**, va aynan o'sha bandda
`04-12` ning o'zi topgan nosozlik sinfi bitta jarayon nariga ko'chib qolgan.

### Kuzatiladigan haqiqatlar (ROADMAP SC#1–SC#5)

| # | Haqiqat | Holat | Dalil |
|---|---|---|---|
| 1 | Bozor admini jadvalni mavsumiy profil bilan sozlaydi va **ertasi kuni** aynan o'sha slotlarda kadrlar paydo bo'ladi | ✓ VERIFIED | `test_sc1_schedule_produces_slots` — men ishga tushirdim, o'tdi. `ensure_plan` (`capture_repo.py:247-294`) rejani **oldindan** materializatsiya qiladi; muzlatish **slot o'qida** va u STRUKTURAVIY (bitta `INSERT … SELECT`, `NOT EXISTS(bugun) OR EXISTS(shu slot_time)`), check-then-write emas — kun o'rtasida topilgan kamera bugungi slotlarni OLADI, yangi slot esa OLMAYDI (D-05). `market_activate()` 7 slotli standart profilni yozadi (D-01). `EXCLUDE USING gist` kesishuvchi profilni DB darajasida rad etadi |
| 2 | Uzilish/takror ishga tushishda dublikat yo'q, urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda **ochiq ko'rinadi** | ✓ VERIFIED | `test_sc2_…` o'tdi. `missed` — **hosila**, istisno ilovasi emas: `_MARK_MISSED` (`capture_repo.py:426-437`) `status='pending' AND scheduled_at < now() - grace` bo'yicha `UPDATE … RETURNING`, va `RETURNING` alertning yagona manbai. `ON CONFLICT ON CONSTRAINT … DO NOTHING`; `FOR UPDATE SKIP LOCKED` + ijara; `0017` uchinchi disjunkt (o'lchangan nosozlik) — `migrations/entities/functions.py:1453-1459`. **Sabotajni o'zim qayta yugurtirdim** (pastda) |
| 3 | Qorong'i/buzuq/bo'sh kadr avtomatik belgilanadi, `light_mode` bilan saqlanadi va hisob-kitobga **hech qachon** ta'sir qilmaydi | ✓ VERIFIED | `test_sc3_…` o'tdi. `dark` ikki shartli (`quality.py:457`, `mean < X AND stddev < Y` — D-14). Kafolat **strukturaviy**: `is_billable` `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED` + `UNIQUE (id, is_billable)` langari (`0014:472-513`), D-23 haqiqiy `postgres:18.4` da o'lchangan |
| 4 | Kadrlar S3-mos omborda bozor/kamera/sana bo'yicha topiladi; 90 kun to'liq, keyin siqilgan siyosat **amalda ishlaydi** | ✓ VERIFIED (mexanizm) | `test_sc4_…` o'tdi — **haqiqiy SeaweedFS konteynerida**, mock'siz (`test_criteria_module_uses_no_storage_mock` buni AST bilan qulflaydi). `retention_full_days=90` / `retention_compressed_days=365` `Settings` da. Kalendar kechishi — `04-HUMAN-UAT.md` #2 (kutib bo'lmaydi, egasi Ops) |
| 5 | Kamera offline / slot o'tkazib yuborilgan / backup xato → Telegram-alert **va xato Sentry'da ko'rinadi** | ⚠ **PARTIAL** | Telegram yarmi to'liq: guruhlash, 60 daq debounce, `NEVER_SUPPRESSED_ALERT_KEYS` metadan hosila, D-19 **yozish paytidagi** allowlist. **Sentry yarmi `scheduler` jarayonida ULANMAGAN** — quyida o'lchangan |

**Ball: 4/5 haqiqat to'liq tasdiqlandi**

---

## ⛔ Bo'shliq — SC#5 / FOUND-06 ning Sentry yarmi `scheduler` da yo'q

Bu bo'shliq **o'lchangan**, manba o'qish bilan taxmin qilingan emas. Quyidagi
chiqish `tests` konteynerida, `app.worker` ni import qilib, `taskiq scheduler`
CLI'sining aynan qadamlarini takrorlab olindi:

```
registered handlers:
    TaskiqEvents.WORKER_STARTUP ['_open_worker_resources']
    TaskiqEvents.WORKER_SHUTDOWN ['_close_worker_resources']
is_worker_process = False
after CLI sets is_scheduler_process -> is_worker_process = False
broker.startup() fires: TaskiqEvents.CLIENT_STARTUP
handlers for it: []
sentry active: False
```

**Sabab zanjiri:**

1. `compose.yaml:383` — `command: ["taskiq", "scheduler", "app.worker:scheduler"]`,
   va `compose.yaml:398` o'sha konteynerga `SENTRY_DSN` ni **beradi**.
2. taskiq `cli/scheduler/run.py:392` — `scheduler.broker.is_scheduler_process = True`.
   Bu **boshqa bayroq**: `is_worker_process` ni FAQAT `cli/worker/run.py:148`
   o'rnatadi.
3. `abc/broker.py:187-194` — `is_worker_process` `False` bo'lgani uchun
   `startup()` `CLIENT_STARTUP` ni ateshlaydi.
4. Reyestrda `CLIENT_STARTUP` ilmog'i **umuman yo'q** (`worker.py` da faqat
   `WORKER_STARTUP` va `WORKER_SHUTDOWN`).
5. Ya'ni `init_sentry()` — API'dan tashqaridagi yagona chaqiruv joyi —
   planer jarayonida **hech qachon** bajarilmaydi.

**Nega bu shu fazaning aynan o'z nosozlik sinfi.** `04-12` ning RED yugurishi
`sentry_sdk.init()` worker jarayonida chaqirilmasligini topgan va uni yopgan.
Xuddi o'sha nosozlik bitta jarayon nariga ko'chgan: `scheduler` — 4-fazaning
**hamma** jobini tetiklaydigan jarayon (`capture.tick` har daqiqada,
`retention.daily`, `alert.sweep` har 5 daqiqada, `alert.digest` 20:00 da).

**Nega darvozalar buni ko'rmaydi.** Ikkala «isbot» ham AYNAN ikkita **kod**
kirish nuqtasini sanaydi:

* `tests/unit/test_sentry_scrub.py:176` → `for entrypoint in (lifespan, _open_worker_resources)`
* `tests/integration/test_phase4_criteria.py:224-227` → `SENTRY_ENTRYPOINTS` — 2 elementli kortej

Docstring «YETTI EMAS, IKKI kirish nuqtasi» deb yozadi — hisob **konteyner**
emas, **kod kirish nuqtasi** bo'yicha yuritilgan, va `scheduler` shu
bo'shliqqa tushgan. Ikkala test ham struktura jihatidan uchinchi jarayonni
ko'ra olmaydi, shuning uchun ular abadiy yashil.

**Amaliy oqibati — va u kosmetik emas.** taskiq planeri vazifani
`asyncio.create_task` bilan yuboradi va `add_done_callback`
(`cli/scheduler/run.py:346-350`) faqat nomni ro'yxatdan **o'chiradi** —
istisnoni **o'qimaydi**. Ya'ni broker yiqilsa (masalan Valkey yetib
bo'lmasa):

* tik navbatga tushmaydi → kadr olinmaydi;
* `alert_sweep` ham planer boshqaruvida → **Telegram yo'li ham to'xtaydi**;
* istisno faqat konteyner jurnalida «Task exception was never retrieved»
  bo'lib qoladi;
* Sentry'ga hech nima bormaydi.

Qolgan yagona detektor — `/internal/self-check` (yurak urishi eskiradi), lekin
uning tashqi kuzatuvchisi D-21 bo'yicha **ataylab kod emas**, hujjat. Ya'ni
maqsad jumlasining «uzilish jim qolmaydi» bandi aynan eng muhim jarayonda
bitta qatlamga tayanib qolgan.

> **Adolat uchun aniq chegara:** kadr olish, saqlash siyosati va alert
> supurgisining O'ZI `worker` da bajariladi va **u yerda Sentry ulangan**.
> Ya'ni 4-fazaning istisnolarining ko'p qismi Sentry'ga BORADI. Bo'shliq —
> planer jarayonining o'z istisnolari.

---

## Talab qilingan artefaktlar

| Artefakt | Kutilgan | Holat | Tafsilot |
|---|---|---|---|
| `packages/sbozor-core/sbozor_core/models/snapshot.py` | 5 model, konstantalar, `DEFAULT_SNAPSHOT_SLOTS` | ✓ VERIFIED | 879 qator (min 300) |
| `migrations/versions/0014_snapshot_domain.py` | 5 jadval + RLS + `EXCLUDE` + `is_billable` langari | ✓ VERIFIED | 842 qator |
| `migrations/versions/0015_market_delete_snapshots.py` | kaskad, `capture_due_markets()`, standart profil | ✓ VERIFIED | 279 qator |
| `migrations/versions/0016_corrupt_frame_measurements.py` | o'lchov ustunlari NULLABLE | ✓ VERIFIED | Sentinel nol ATAYIN rad etilgan |
| `migrations/versions/0017_capture_due_watchdog.py` | uchinchi disjunkt | ✓ VERIFIED | Eski tana migratsiyada muzlatilgan |
| `services/core-api/app/services/quality.py` | `analyze()` sof funksiyasi | ✓ VERIFIED | 485 qator (min 150), `LOAD_TRUNCATED_IMAGES` bor |
| `services/core-api/app/services/object_key.py` | deterministik kalit | ✓ VERIFIED | 125 qator; UUID + ISO sana + `HHMM` — foydalanuvchi matni yo'q |
| `services/core-api/app/services/capture_errors.py` | xato taksonomiyasi | ✓ VERIFIED | 312 qator |
| `services/core-api/app/services/storage.py` | `aiobotocore` qobig'i | ✓ VERIFIED | 530 qator (min 150); `create_bucket`/`delete_bucket` YO'Q |
| `services/core-api/app/services/frame_source.py` | go2rtc → ISAPI → ffmpeg | ✓ VERIFIED | 666 qator (min 200) |
| `services/core-api/app/services/alerts.py` | Telegram `sendMessage` | ✓ VERIFIED | 362 qator; `sendPhoto` reyestrda UMUMAN yo'q |
| `services/core-api/app/repositories/capture_repo.py` | `ensure_plan`…`finish_*` | ✓ VERIFIED | 1115 qator (min 250), `SKIP LOCKED` bor |
| `services/core-api/app/repositories/schedule_repo.py` | profil CRUD + davr bo'lish | ✓ VERIFIED | 912 qator, `uncovered` bor |
| `services/core-api/app/repositories/snapshot_repo.py` | kadr yozuvi, retention nomzodlari | ✓ VERIFIED | 445 qator, `storage_tier` bor |
| `services/core-api/app/jobs/capture.py` | `capture_tick` + `capture_batch` | ✓ VERIFIED | 1142 qator (min 300) |
| `services/core-api/app/jobs/retention.py` | siqish, tozalash, yetim supurgisi | ✓ VERIFIED | 765 qator (min 150) |
| `services/core-api/app/jobs/alerting.py` | `alert_sweep` | ✓ VERIFIED | 1124 qator (min 200) |
| `services/core-api/app/worker.py` | `scheduler` obyekti + qobiqlar | ⚠ **PARTIAL** | 628 qator, `TaskiqScheduler` bor — LEKIN `CLIENT_STARTUP` ilmog'i yo'q (yuqoridagi bo'shliq) |
| `services/core-api/app/api/v1/schedules.py` | jadval CRUD + `/today` | ✓ VERIFIED | 450 qator; `/today` `/{schedule_id}` DAN OLDIN |
| `services/core-api/app/api/v1/snapshots.py` | kun jurnali + rasm proxysi | ✓ VERIFIED | 520 qator, `audit_read` bor |
| `services/core-api/app/api/internal/self_check.py` | eskirgan yurak urishi | ✓ VERIFIED | 203 qator; `stale` va `never_seen` ajratilgan |
| `frontend/src/components/snapshots/capture-cell.tsx` | 9 holat, `missed` uchun `CircleSlash` | ✓ VERIFIED | Sabotaj bilan tasdiqlandi |
| `frontend/src/components/snapshots/capture-grid.tsx` | matritsa, roving tabindex | ✓ VERIFIED | `<table>` semantikasi, `tabIndex` bor |
| `frontend/src/components/snapshots/day-summary.tsx` | 6 hisoblagich `<dl>` bilan | ✓ VERIFIED | `missedCallout` bor |
| `frontend/src/components/snapshots/alert-list.tsx` | ogohlantirishlar; rasm YO'Q | ✓ VERIFIED | `occurrences` bor |
| `ops/docs/monitoring.md` | D-21 yo'riqnomasi | ✓ VERIFIED | 250 qator; healthchecks.io + UptimeRobot |
| `ops/seaweedfs/s3.json.example` | `anonymous` YO'Q | ✓ VERIFIED | `grep -c anonymous` → **0** |
| `tests/integration/test_phase4_criteria.py` | 5 mezon + meta + mock darvozasi | ✓ VERIFIED | 1330 qator; **7/7 o'tdi** |
| `.planning/phases/04-snapshot-pipeline/04-HUMAN-UAT.md` | 6 band, ega + tetik | ✓ VERIFIED | 6 ta `Egasi:`, tetiklar frontmatter'da |
| `.planning/phases/04-snapshot-pipeline/04-VALIDATION.md` | 6 o'lchov, hisoblangan bayroq | ✓ VERIFIED | Skript exit 0 |

---

## Kalit bog'lanishlar (wiring)

| From | To | Via | Holat | Tafsilot |
|---|---|---|---|---|
| `capture_repo.py` | `postgres` | tiplangan `text()` + `bindparams` | ✓ WIRED | `_ENSURE_PLAN`, `_CLAIM_DUE`, `_MARK_MISSED`, `_RELEASE_*` |
| `jobs/capture.py` | `capture_repo.py` | `ensure_plan`/`claim_due`/`mark_missed` | ✓ WIRED | `_system_transaction` tenant kontekstini O'ZI o'rnatadi |
| `jobs/capture.py` | `storage.py` → DB | `put()` (963) → `record()`+`finish_succeeded()` (1017) | ✓ WIRED | Tartib to'g'ri: avval ombor, keyin baza |
| `frame_source.py` | `go2rtc.py` | `ensure_stream()` + `/api/frame.jpeg` | ✓ WIRED | `remove_stream()` juftisiz (D-11) |
| `isapi/client.py` | `nvr_stream_limit` evristikasi | `_claims_rtsp_session()` | ✓ WIRED | `/picture` istisno qilingan → `stream_claims == 0` (D-07) |
| `jobs/retention.py` | `storage.py` | `get` → `_encode` → `put` → `mark_compressed` | ✓ WIRED | Kichraymasa obyekt TEGILMAYDI, `not_smaller` sanaydi |
| `jobs/alerting.py` | `alerts.py` | `send_message`, xato YUTILADI | ✓ WIRED | `_detail()` allowlist YOZISH paytida |
| `worker.py` | `jobs/capture.py` | `@broker.task(schedule=[{"cron": …}])` | ✓ WIRED | `capture.tick`, `retention.daily`, `alert.sweep`, `alert.digest` |
| `worker.py` (`scheduler` jarayoni) | `observability.py::init_sentry` | `WORKER_STARTUP` ilmog'i | ✗ **NOT_WIRED** | Planer `CLIENT_STARTUP` ni ateshlaydi; ilmoq yo'q |
| `snapshot-queries.ts` | `market-queries.ts` | `import { domainKey }` | ✓ WIRED | Ikkinchi nusxa yaratilmagan |
| `snapshots/page.tsx` | `/api/v1/capture-runs` | `useCaptureDay` → `apiFetch` | ✓ WIRED | zod sxemasi bilan |

---

## Ma'lumot oqimi izi (Level 4)

| Artefakt | Ma'lumot o'zgaruvchisi | Manba | Haqiqiy ma'lumot | Holat |
|---|---|---|---|---|
| `snapshots/page.tsx` | `visibleRows` | `useCaptureDay` → `GET /capture-runs?day=` | Ha | ✓ FLOWING |
| `api/v1/snapshots.py` | `rows` | `CaptureRepository.list_day()` → `_LIST_DAY` SQL | Ha | ✓ FLOWING |
| `schedule-card.tsx` | `data.today` / `data.tomorrow` | `GET /snapshot-schedules/today` → `repo.today_and_tomorrow()` | Ha | ✓ FLOWING |
| `capture-grid.tsx` | `rows` prop | `page.tsx` dan `visibleRows` | Ha | ✓ FLOWING |
| `alert-list.tsx` | `occurrences` | `alerts_router` → `alert_events` jadvali | Ha | ✓ FLOWING |

Snapshot komponentlarida qattiq yozilgan bo'sh prop **topilmadi**
(`=\{(\[\]|\{\}|null|''|"")\}` skani — 0 natija).

---

## Xulqiy spot-check va sabotajlar (o'zim bajardim)

| Xulq | Buyruq | Natija | Holat |
|---|---|---|---|
| Beshala mezon bitta buyruqda | `pytest tests/integration/test_phase4_criteria.py` | 7 passed | ✓ PASS |
| To'liq pytest to'plami | `pytest -q` | exit 0, ~1925 test, 0 fail | ✓ PASS |
| Tenant izolyatsiyasi | `pytest tests/tenancy -q` | 472 passed | ✓ PASS |
| Frontend komponentlari | `npx vitest run` | 28 fayl / 338 test passed | ✓ PASS |
| Skript darvozalari | `node --test scripts/*.test.mjs` | 115 passed | ✓ PASS |
| i18n pariteti | `npm run i18n:check` | 777 kalit × 3 til, drift yo'q | ✓ PASS |
| Talab ↔ Traceability pariteti | `node scripts/check-requirements-sync.mjs` | exit 0 — 49 talab MOS (**03-14 dan beri qizil edi, endi YASHIL**) | ✓ PASS |
| `nyquist_compliant` HISOBI | `node scripts/check-validation-signoff.mjs` | exit 0 — bayroq hisob-kitobga mos, 71 qator / 4 inson bandi | ✓ PASS |
| **Sabotaj:** `missed` hujayra holatini `pending` ga yiqitish | `npx vitest run capture-grid.test.tsx` | **2 failed / 13 passed** | ✓ RED — bo'shliq HAQIQATAN yopilgan |
| **Sabotaj nazorati:** fayl tiklandi | `git diff` | bo'sh | ✓ CLEAN |
| **Planer Sentry zondi** | konteynerda `app.worker` import + taskiq CLI qadamlari | `handlers for CLIENT_STARTUP: []`, `sentry active: False` | ✗ **FAIL** |

`04-11` ning eng zaif joyi (`capture-grid.test.tsx` fixture'ida `missed`
qator yo'q edi, ya'ni matritsa to'plami SC#2 ga **nol** kafolat berardi)
**haqiqatan yopilgan** — men `capture-cell.tsx` dagi `missed` holatini
`pending` ga yiqitib qayta o'lchadim va to'plam qizardi.

`04-08` ning `not_smaller` hisoblagichi ham haqiqiy o'lchov:
`_recompress()` (`retention.py:517-523`) natija kichraymasa obyektni
**yozmaydi** va `(len(original), False)` qaytaradi; chaqiruvchi
(`retention.py:457-459`) aynan `changed is False` bo'yicha sanaydi. Ya'ni
u «enkoder chaqirildi va foyda bermadi» hodisasini o'lchaydi — sabotaj
qizartiradigan yagona kuzatiladigan qiymat.

---

## Qaror reyestri D-01…D-23

| Qaror | Holat | Dalil |
|---|---|---|
| D-01 standart 7 slotli profil | ✓ | `DEFAULT_SNAPSHOT_SLOTS` (`snapshot.py:275`), `market_activate()` (`0015`) |
| D-02 planer faqat holatsiz tik | ✓ | `LabelScheduleSource`, reja/ijara Postgres'da |
| D-03 tik idempotent | ✓ | `ON CONFLICT DO NOTHING`; «aynan bitta planer» talabi yo'q |
| D-04 vazifa birligi NVR + slot | ✓ | `_group_by_nvr()` (`capture.py:398-405`), `BatchRequest.nvr_id` |
| D-05 kun o'rtasidagi tahrir bugunga ta'sir qilmaydi | ✓ | `_ENSURE_PLAN` predikati — muzlatish **slot o'qida**, strukturaviy |
| D-06 uch usul sozlanadigan | ✓ | `nvr_devices.capture_method` + `CAPTURE_METHOD_CHECK` |
| D-07 ISAPI `/picture` nol RTSP sessiyasi | ✓ | `_claims_rtsp_session()` `/picture` ni istisno qiladi; test `stream_claims == 0` |
| D-08 `max_concurrent` = 1 | ✓ | `capture_global_concurrency: … = 1` (`settings.py:199`) |
| D-09 `capture_stream` = `'main'` | ✓ | `CAPTURE_STREAM_CHECK` — `'main'`/`'sub'` |
| D-10 yopiq kunlarda ham kadr | ✓ | `capture_runs.is_market_open` ustuni; `market_is_open()` qayta ishlatilgan |
| D-11 `remove_stream()` chaqirilmaydi | ✓ | `frame_source.py:66,414`; `remove_stream` faqat `go2rtc.py` da |
| D-12 `light_mode` superset | ✓ | Enum + alohida `quality_verdict` (`0014:469`) |
| D-13 faqat Pillow | ✓ | `quality.py` da `cv2` yo'q; `pyproject.toml:92` opencv'ni ATAYIN rad etadi |
| D-14 `dark` ikki shartli | ✓ | `quality.py:457` — `mean < X and stddev < Y` |
| D-15 o'lchovlar saqlanadi | ✓ | `quality_mean`/`quality_stddev`/`quality_saturation` ustunlari |
| D-16 billing kafolati strukturaviy | ✓ | `GENERATED ALWAYS … STORED` + `uq_snapshots_billable_anchor` |
| D-17 `aiobotocore`, `aioboto3` yo'q | ✓ | `pyproject.toml:97` — `aiobotocore==3.9.0`; `minio-py` yo'q |
| D-18 90 + 365 kun | ✓ | `retention_full_days=90`, `retention_compressed_days=365` |
| D-19 alertga rasm YO'Q | ✓ | `sendPhoto` butun repoda yo'q; `_detail()` **yozish paytida** allowlist, ro'yxatdan tashqari kalit `ValueError` |
| D-20 alert yo'qlikka qo'yiladi | ✓ | `mark_missed()` hosilasi → `RETURNING` → `capture_missed` alerti |
| D-21 tashqi switch — kod emas, hujjat | ✓ | `ops/docs/monitoring.md` §5; band `04-HUMAN-UAT.md` #5 |
| D-22 guruhlash + debounce; ba'zilari bo'g'ilmaydi | ✓ | `DEBOUNCE_MINUTES=60`; `NEVER_SUPPRESSED_ALERT_KEYS` metadan **hosila** |
| D-23 `GENERATED STORED` FK nishoni | ✓ | Haqiqiy `postgres:18.4` da o'lchangan → `0014` strukturaviy shaklda |

**23/23 qaror hurmat qilingan.**

---

## Talablar qamrovi

| Talab | Reja | Ta'rif | Holat | Dalil |
|---|---|---|---|---|
| CAM-04 | 04-03, 04-05, 04-09, 04-10, 04-12 | Snapshot jadvali sozlanadi, mavsumiy profil | ✓ SATISFIED | `test_sc1_…` + `test_capture_schedule.py` (26 test); `EXCLUDE USING gist`; `DEFAULT_SNAPSHOT_SLOTS` talab matniga harfma-harf teng |
| CAM-05 | 04-01…04-07, 04-11, 04-12 | Idempotent + retry; missed jurnalda + alert | ✓ SATISFIED | `test_sc2_…`; `ON CONFLICT`; ijara + `0017`; `missed` UI'da (sabotaj bilan qulflangan) |
| CAM-06 | 04-02…04-07, 04-09, 04-11, 04-12 | Sifat filtri; yaroqsiz kadr billing'ga ta'sir qilmaydi | ✓ SATISFIED | `test_sc3_…`; DB darajasidagi rad etish. ⚠ Chegara QIYMATI LOW confidence — `04-HUMAN-UAT.md` #1 |
| CAM-07 | 04-01, 04-03…04-09, 04-11, 04-12 | S3 tartib + 90/455 kun siyosati | ✓ SATISFIED | `test_sc4_…` haqiqiy SeaweedFS'da. ⚠ Kalendar kechishi — `04-HUMAN-UAT.md` #2 |
| FOUND-06 | 04-01…04-04, 04-08, 04-09, 04-11, 04-12 | Telegram-alert + xatolar Sentry'da | ⚠ **PARTIAL** | Telegram qismi to'liq o'lchangan. **«Xatolar Sentry'da» `scheduler` jarayoni uchun BAJARILMAGAN** |

**Yetim talab yo'q:** `REQUIREMENTS.md` Phase 4 ga aynan shu beshtasini
biriktiradi va beshalasi ham reja frontmatter'larida da'vo qilingan.

**Holat lug'ati to'g'ri:** `Done`/`Pending`/`Blocked` — `Complete` yo'q
(`04-10` ning `mark-complete` urinishini darvoza to'sgan; hozir 16 `Done`,
32 `Pending`, 1 `Blocked`).

⚠ **FOUND-06 ning `Done` holati bu bo'shliq bilan to'liq mos emas.**
`REQUIREMENTS.md:272` dalil ustuni «`init_sentry` **IKKALA jarayonda** ham
chaqiriladi» deydi va ikkalasini nomma-nom sanaydi — bu **to'g'ri**, lekin
`SENTRY_DSN` oladigan jarayon **uchta**.

---

## Anti-naqshlar

| Fayl | Qator | Naqsh | Jiddiylik | Ta'siri |
|---|---|---|---|---|
| — | — | `TBD`/`FIXME`/`XXX` | — | **Topilmadi** (0 natija) |
| — | — | `TODO`/`HACK` | — | **Topilmadi** |
| — | — | `coming soon` / `not yet implemented` | — | **Topilmadi** |
| `frontend/src/components/wizard/wizard-*.{tsx,ts}` | 8/119/123/149 | `CAMERA_PLACEHOLDER` | ℹ️ Info | 2-fazadan qolgan **nomlangan konstanta** (usta qadamiga havola), qarz belgisi emas |
| `tests/fixtures/nvr_domain.py` | 85/102 | `NVR_PASSWORD_PLACEHOLDER` | ℹ️ Info | Seed konstantasi ATAYIN Fernet tokeni emas — test shu faktga tayanadi |
| `.env.example` | 108-109 | `S3_ACCESS_KEY=` / `S3_SECRET_KEY=` bo'sh | ⚠️ Warning | `compose.yaml` ularni `worker`/`scheduler` ga **standartsiz** uzatadi → yangi klonda `npm run up` ikkala konteynerni yiqitadi, sabab faqat `docker compose logs` da. `deferred-items.md` #2 da ega bilan yozilgan, **hali yopilmagan** |

**Debt-marker darvozasi: TOZA.** 4-faza tekkan birorta faylda havolasiz
`TBD`/`FIXME`/`XXX` yo'q.

---

## Kechiktirilgan bandlar

| # | Band | Qayerda hal bo'ladi | Dalil |
|---|---|---|---|
| 1 | Tashqi dead-man's switch KOD bilan qurilmagan | D-21 (faza qarori) + Phase 8 | «v1 da kod yozilmaydi — hujjat va ops bandi». `ops/docs/monitoring.md` §5 mavjud |
| 2 | `backup` yurak urishi hech qachon yozilmagan | Phase 8 | `EXPECTED_COMPONENTS` uni ATAYIN bugundan ro'yxatda saqlaydi; `never_seen` `ok` ga ta'sir qilmaydi |

`deferred-items.md` ning uchala bandidan **#1 yopilgan** (`_anchor_today()`
qo'shildi — yarim tun oynasi nolga tushdi, `04-12` da), **#3 yopilgan**,
**#2 ochiq** (yuqoridagi anti-naqsh jadvali).

---

## Bo'shliqlar xulosasi

Faza o'z ishining katta qismini haqiqatan bajargan va buni **o'lchov bilan**
bajargan: 12 rejaning hammasi, 23 qarorning hammasi, beshala mezon uchun
mock'siz test, hamma darvoza yashil (men mustaqil yugurtirdim, SUMMARY'dan
o'qimadim). Ikkita eng shubhali da'vo — `04-11` ning `capture-grid` fixture
bo'shlig'i va `04-08` ning `not_smaller` hisoblagichi — **sabotaj bilan qayta
o'lchandi va ikkalasi ham haqiqiy chiqdi**.

Bitta bo'shliq qoldi va u aynan fazaning eng nozik bandida:

**Maqsad jumlasining to'rtinchi bandi — «uzilish jim qolmaydi» — `scheduler`
jarayonida bir qatlamni yo'qotgan.** `04-12` ning RED yugurishi
`sentry_sdk.init()` ning worker'da chaqirilmasligini topib, uni yopgan;
xuddi o'sha nosozlik planer jarayonida **saqlanib qolgan** va uni
hech qanday test ko'ra olmaydi, chunki ikkala darvoza ham AYNAN ikkita
kod kirish nuqtasini sanaydi, jarayonlarni emas.

Nosozlik shakli — fazaning o'zi nomlagan «jimgina yolg'on» sinfi:
`SENTRY_DSN` konteynerga beriladi, konteyner sog'lom ko'rinadi, `init()`
chaqirilmagani uchun `sentry_sdk` hech qanday xato bermaydi, va planer
istisnosi (taskiq uni `add_done_callback` da **o'qimaydi**) faqat konteyner
jurnaliga tushadi. Planer o'lsa `alert_sweep` ham u bilan to'xtaydi, ya'ni
Telegram yo'li ham yopiladi — qolgan yagona detektor `/internal/self-check`,
uning tashqi kuzatuvchisi esa D-21 bo'yicha ataylab kod emas.

Tuzatish kichik (bitta `CLIENT_STARTUP` ilmog'i), lekin darvozani ham
kengaytirish kerak — aks holda to'rtinchi jarayon qo'shilgan kuni xuddi
shu narsa uchinchi marta takrorlanadi.

**Simulyator chegarasi haqida ochiq gap.** Hamma narsa simulyator va
sintetik kadrlar ustida o'lchangan. Real uskuna, real kalendar vaqt yoki
real odam talab qiladigan oltita band `04-HUMAN-UAT.md` da **ega va tetik**
bilan yozilgan; roadmap'ning self-service direktivasi bo'yicha ular fazani
bloklamaydi. Lekin ochiq aytish kerak: **90 kunlik saqlash siyosati kutib
o'lchanmagan va uni kutmasdan o'lchab bo'lmaydi** — mexanizm isbotlangan,
kalendar xulqi emas.

---

*Verified: 2026-08-05T01:45:12Z*
*Verifier: Claude (gsd-verifier)*
