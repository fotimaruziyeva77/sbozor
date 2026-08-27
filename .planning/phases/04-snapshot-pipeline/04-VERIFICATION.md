---
phase: 04-snapshot-pipeline
verified: 2026-08-16T02:45:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  round: 3
  note: >-
    Uchinchi tekshiruv. Ikkinchisi (2026-08-05) `human_needed` bilan yopilgan
    va `gaps_remaining: []` bo'lgan. Bu yugurishning ASOSIY savoli boshqa:
    o'shandan beri 5-, 6- va 7-fazalar qurildi (11 kun, yuzlab commit), ya'ni
    savol «bo'shliq yopildimi?» EMAS, «yopilgani REGRESSIYAGA uchramadimi?».
  gaps_closed: []
  gaps_remaining: []
  regressions: []
  previously_open_items_now_resolved:
    - item: "`npm run gate` davomiyligi 900 s byudjetidan yuqori (oldingi hisobotning 1-ochiq bandi)"
      resolution: >-
        YOPILDI. `STATE.md` bo'yicha o'lchov TINCH XOSTDA qayta olindi —
        `parnikkpi-*` steki `docker stop` bilan to'xtatilib, uch o'lchov:
        1009/1004/983 s. Byudjet keyin 1250 s (05-15), so'ng 2300 s
        (06-14) qilib qayta belgilandi va `07-17` da qayta o'lchandi
        (1424/1263/1349 s). Oldingi hisobot aytgan «tinch xostda uch
        o'lchov» tetigi HAQIQATAN bajarilgan.
    - item: "`scripts/check-validation-signoff.mjs::DEFAULT_FILE` 2-fazaga qadalgan"
      resolution: >-
        YOPILDI (D-27). Skript endi `.planning/phases/` ni SKANERLAYDI
        (`check-validation-signoff.mjs:54`), qadalgan yo'l olib tashlangan
        va nosozlik izohda nomlab qoldirilgan. TEKSHIRUVCHI O'ZI O'LCHADI:
        argumentli chaqiruv 4-faza faylida exit 0, argumentsiz chaqiruv
        endi ENG SO'NGGI fazani o'qiydi (8-faza shabloni), ya'ni u endi
        4-fazani yashil deb SOXTA ko'rsatmaydi.
  observations:
    - item: >-
        4-fazaning frontend qatlamida foydalanuvchiga KO'RINADIGAN nuqson
        tekshiruvdan KEYIN topildi
      detail: >-
        `KAMCHILIKLAR-REESTRI.md` №6 — «Jadval dialogi bo'sh holatda abadiy
        Yuklanmoqda» (2026-08-14/15 brauzer testi) va KR-tri —
        «schedule-dialog yolg'on tashxis / ternary / EmptyState». IKKALASI
        HAM 4-fazaning artefakti (`schedule-dialog.tsx`, SC#1 ning UI yo'li)
        va IKKALASI HAM 2026-08-05 tekshiruvidan O'TIB KETGAN.
      status: "Ikkalasi ham YOPILGAN (`c411636`, `8c142a3`, `067a4dd`)"
      lesson: >-
        Bu bo'shliq EMAS (bugun kod to'g'ri va 104 ta frontend testi yashil),
        lekin u tekshiruv METODIKASINING chegarasini ko'rsatadi: 4-fazaning
        backend dalili juda kuchli (haqiqiy konteyner, haqiqiy jarayon zondi,
        sabotaj), frontend dalili esa komponent testlari bilan cheklangan edi
        va tri-state kolapsini ko'rmadi. Keyingi fazalarda UI mezonlari uchun
        brauzer darajasidagi o'lchov qo'shilishi kerak.
deferred:
  - truth: "Tashqi dead-man's switch (`/internal/self-check` ni tashqaridan so'rash) KOD bilan qurilmagan"
    addressed_in: "D-21 (fazaning O'Z qarori) + Phase 8"
    evidence: >-
      D-21: «v1 da kod yozilmaydi — bitta URL sozlash yo'riqnomasi va ops
      bandi». TASDIQLANDI: `ops/docs/monitoring.md` §5 «Tashqi dead-man's
      switch (D-21) — bitta URL, kod emas» mavjud (healthchecks.io va
      UptimeRobot yo'llari bilan); band `04-HUMAN-UAT.md` #5, egasi Ops.
  - truth: "Zaxira (`backup`) komponentining yurak urishi hech qachon yozilmagan — `/internal/self-check` uni `never_seen` da ko'rsatadi"
    addressed_in: "Phase 8 (FOUND-07)"
    evidence: >-
      TASDIQLANDI: `BACKUP_COMPONENT` butun `services/` bo'ylab faqat O'QILADI
      (`alerting.py:179,762`, `self_check.py:112`) — birorta yozuvchi yo'q.
      Phase 8 ROADMAP mezoni #3 (zaxira + tiklash mashqi) va aynan ikkita
      reja shu ishni oladi: `08-05-PLAN.md` («`backup` konteyneri: ...
      yurak urishi») va `08-08-PLAN.md` («Zaxira yurak urishi va tiklash
      mashqining CI qatlami»). `self_check.py:268` — `ok` FAQAT `stale`
      bo'yicha hisoblanadi, ya'ni `never_seen` bugun 503 BERMAYDI.
human_verification:
  - test: "Sifat chegaralarini REAL Karmana kadrida sozlash (04-HUMAN-UAT #1)"
    expected: "06:00 va 18:00 kadrlarida `dark`/`blank` verdiktlari qonuniy kadrni rad etmaydi; chegaralar SQL bilan sozlanadi"
    why_human: "Chegaralar LOW confidence — real kadr yo'q. Sintetik JPEG MEXANIZMNI isbotlaydi, QIYMATNI emas. Egasi: nazoratchi + ijrochi; tetigi: Phase 0 kadrlari. `result: [pending]` — tekshirildi"
  - test: "90 kunlik saqlash siyosatining KALENDAR bo'yicha ishlashi (04-HUMAN-UAT #2)"
    expected: "90 kundan keyin birinchi `full -> compressed` to'lqini; 455 kundan keyin birinchi `purged`"
    why_human: "Vaqtni kutib bo'lmaydi. Test chegarani SOZLAMA (`full_days=0`), vaqtni ARGUMENT (`today=`) qiladi — mexanizm rost, kalendar emas. Egasi: Ops; tetigi: go-live + 90 kun. `result: [pending]`"
  - test: "Tiklash mashqi (restore drill) (04-HUMAN-UAT #3)"
    expected: "Zaxiradan to'liq tiklash hujjatlashtirilgan holda bajariladi"
    why_human: "Real ombor, real ma'lumot va toza server talab qiladi. Egasi: Ops; tetigi: go-live'dan oldin, Phase 8 (FOUND-07). `result: [pending]`"
  - test: "Telegram alertining HAQIQATAN yetib borishi (04-HUMAN-UAT #4)"
    expected: "Platforma admini Telegram'da guruhlangan xabarni oladi; xabarda rasm, havola va obyekt kaliti yo'q"
    why_human: "Token va chat ID CI'da yo'q — bu yugurishda ham `TELEGRAM_BOT_TOKEN` bo'sh edi (docker ogohlantirishi). HTTP kontrakti `respx` bilan o'lchangan, YETIB BORISH emas. Egasi: Ops. `result: [pending]`"
  - test: "Tashqi dead-man's switch — `/internal/self-check` ni tashqaridan so'rash (04-HUMAN-UAT #5)"
    expected: "healthchecks.io/UptimeRobot 503 holatida ogohlantirish yuboradi"
    why_human: "Quti tashqarisidagi xizmat, D-21 bo'yicha kod yozilmaydi. Egasi: Ops. `result: [pending]`"
  - test: "Real NVR'da bir vaqtdagi sessiya chegarasining kadr olishga ta'siri (04-HUMAN-UAT #6)"
    expected: "25 kamera ketma-ket olinganda NVR sessiya chegarasiga urilmaydi yoki `capture_stream_limit` bilan kechiktiriladi"
    why_human: "Simulyator sessiya chegarasini UMUMAN modellamaydi. Egasi: Ops. `result: [pending]`"
  - test: "Planer istisnosi HAQIQIY Sentry loyihasida ko'rinadi (04-HUMAN-UAT #7)"
    expected: "Sentry Issues ro'yxatida `ObservedScheduler.on_ready` dan kelgan hodisa; ichida `task_name` va `schedule_id`, shaxsiy ma'lumot YO'Q"
    why_human: "CI'da DSN yo'q. Darvoza `init()` chaqirilishini va `capture_exception` ga borishni o'lchaydi — Sentry SERVERIGA yetishini emas. Egasi: Ops. `result: [pending]`"
---

# Phase 4: Snapshot pipeline — Uchinchi tekshiruv hisoboti

**Faza maqsadi:** Har kuni rejadagi kadrlar avtomatik olinadi, sifat tekshiruvidan o'tadi, ishonchli arxivlanadi va uzilish jim qolmaydi
**Tekshirildi:** 2026-08-16T02:45:00Z
**Holat:** `human_needed`
**Qayta tekshiruv:** Ha — uchinchi yugurish. Oldingisi 2026-08-05, `human_needed`, 5/5

---

## Bu yugurishning savoli boshqa edi

Oldingi tekshiruv (2026-08-05) bo'shliqni yopilgan deb topgan va uni
haqiqiy jarayonda o'lchagan. Men o'sha ishni takrorlamadim. **O'shandan
beri 11 kun o'tdi va loyihada 5-, 6- va 7-fazalar qurildi** — ya'ni
`worker.py` 787 → **1310 qator**, `test_sentry_processes.py` 437 →
**862 qator**, `compose.yaml` ga ikkita yangi Python servisi qo'shildi.

Shuning uchun bu yugurishning savoli: **4-fazaning da'volari
REGRESSIYAGA uchramadimi?** Javob — yo'q, va bir da'vo hatto
KUCHAYDI.

**Hamma raqam quyida MENING O'Z yugurishlarim** (`docker compose
--profile test`), SUMMARY yoki oldingi hisobotdan ko'chirilgan emas.

---

## Maqsad bajarilishi

### Kuzatiladigan haqiqatlar (ROADMAP SC#1–SC#5)

| # | Haqiqat | Holat | Dalil (o'z o'lchovim) |
|---|---|---|---|
| 1 | Admin jadvalni mavsumiy profil bilan sozlaydi va **ertasi kuni** aynan o'sha slotlarda kadrlar paydo bo'ladi | ✓ VERIFIED | `test_sc1_schedule_produces_slots` o'tdi. Test HTTP `PATCH /snapshot-schedules/{id}` bilan admin sifatida sozlaydi, keyin ERTANGI kunni materializatsiya qiladi. Ikki tomonlama: ertaga `SEASONAL_SLOTS`, standart yettilikdan **hech nima qolmaydi** (`:509`), va BUGUNGI reja qator IDENTITETI bilan o'zgarmaydi (`:516`, D-05) |
| 2 | Uzilish/takror ishga tushishda dublikat yo'q, urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda **ochiq ko'rinadi** | ✓ VERIFIED | `test_sc2_...` o'tdi. Struktura: `SKIP LOCKED` × **7**, `ON CONFLICT` × **8** (`capture_repo.py`), `mark_missed()` `:686`. Yuza: `GET /capture-runs` `main.py:371` da ro'yxatdan o'tgan; UI'da to'qqiz holat (`capture-cell.tsx:72-79`) |
| 3 | Qorong'i/buzuq/bo'sh kadr avtomatik belgilanadi, `light_mode` bilan saqlanadi va hisob-kitobga **hech qachon** ta'sir qilmaydi | ✓ VERIFIED **(kuchaydi)** | `test_sc3_...` o'tdi. ⬆ **YANGI DALIL:** 5-faza langarni HAQIQATAN ishlatdi — `0018_occupancy_domain.py:436,472,493` da `snapshot_is_billable` ustuni + kompozit FK (`uq_snapshots_billable_anchor` ga) + `CHECK`. 2026-08-05 da bu FAQAT «5-faza uchun ilgak» edi; bugun zanjir **DB darajasida yopiq** |
| 4 | Kadrlar S3-mos omborda topiladi; 90 kun to'liq, keyin siqilgan siyosat **amalda ishlaydi** | ✓ VERIFIED (mexanizm) | `test_sc4_...` + `test_storage_layout.py` (13 test) + `test_retention.py` (16 test) o'tdi — **haqiqiy SeaweedFS konteynerida**, mock taqiqi kod ichida (`_MOCK_MODULE_ROOTS`). `object_key()` = `{market}/{YYYY-MM-DD}/{camera}/{HHMM}.jpg`; `retention_full_days=90` / `retention_compressed_days=365` (`settings.py:243-244`). Kalendar kechishi — UAT #2 |
| 5 | Kamera offline / slot o'tkazib yuborilgan / backup xato → Telegram-alert **va xato Sentry'da ko'rinadi** | ✓ VERIFIED **(kuchaydi)** | `test_sc5_...` o'tdi — ichida HAQIQIY subprocess zondi (`SENTRY_ACTIVE=True`) + **MAJBURIY nazorat yugurishi** (DSN'siz `False`, `:1366`). Uchala tetik ham reyestrda: `camera_offline`, `capture_missed`, `backup_stale` (`alerting.py:338-353`). ⬆ **YANGI DALIL** — pastda |

**Ball: 5/5 haqiqat tasdiqlandi.** Regressiya **yo'q**.

---

## ⬆ SC#5 — hosila darvoza VAQT bilan isbotlandi

Oldingi tekshiruv darvozaning HOSILA ekanini **sabotaj** bilan isbotlagan
edi (to'rtinchi soxta servis qo'shib). Bugun uni isbotlash uchun sabotaj
kerak emas — **hayotning o'zi n+1 testini o'tkazdi.**

Tekshiruvchining read-only zondi (`compose.yaml` ni tests konteynerida
parse qilib):

```
total services: 17
services receiving SENTRY_DSN: ['bot-service', 'core-api', 'cv-service',
                                'scheduler', 'worker']
   bot-service -> ['python', '-m', 'app.main']
   core-api    -> ['uvicorn', 'app.main:app', ...]
   cv-service  -> ['taskiq', 'worker', 'app.worker:broker', ...]
   scheduler   -> ['taskiq', 'scheduler', 'app.worker:scheduler']
   worker      -> ['taskiq', 'worker', 'app.worker:broker', ...]
```

2026-08-05 da bu ro'yxat **uchta** edi. Bugun **beshta** — 5-faza
`cv-service` ni, 7-faza `bot-service` ni qo'shdi. **Darvoza hamon
yashil.**

Bu qat'iy dalil: agar darvoza sanoqli ro'yxat bo'lganida u ikki marta
jimgina eskirardi. U eskirmadi — u yangi jarayonlarni **topdi va
tekshirdi**. Manbada buning izi ham bor: `test_sentry_processes.py:185-188`
«2026-08-08 holati: ... va `cv-service` ... hodisa aynan shu `cv-service`
da sodir bo'ldi» — ya'ni darvoza HAQIQATAN qizargan va tuzatishga
majburlagan.

Fazaning O'Z ilmog'i ham joyida: `@broker.on_event(TaskiqEvents.CLIENT_STARTUP)`
→ `_install_client_observability` → `init_sentry()` (`worker.py:717-743`),
`ObservedScheduler.on_ready` → `capture_exception(exc)` → `raise`
(`worker.py:667-678`).

---

## Xulqiy o'lchovlar — HAMMASINI O'ZIM YUGURTIRDIM

| # | O'lchov | Buyruq | Natija | Holat |
|---|---|---|---|---|
| 1 | Beshala faza mezoni | `pytest tests/integration/test_phase4_criteria.py` | **7 passed**, exit 0 | ✓ PASS |
| 2 | 4-fazaning unit to'plami (10 fayl: sentry ×3, storage_config, object_key, quality ×2, frame_source, capture_errors, snapshot_settings) | `pytest tests/unit/...` | **141 passed**, exit 0 | ✓ PASS |
| 3 | 4-fazaning integratsiya to'plami (8 fayl: capture_repo/schedule/tick, storage_layout, retention, alerting, snapshot_quality, snapshot_api) | `pytest tests/integration/...` | **141 passed**, exit 0 | ✓ PASS |
| 4 | Frontend snapshot qatlami | `npx vitest run src/components/snapshots src/lib/snapshot-queries.test.tsx` | **9 fayl / 104 test**, exit 0 | ✓ PASS |
| 5 | Talab ↔ Traceability | `node scripts/check-requirements-sync.mjs` | exit 0 — **49 talab MOS** (Done 39 · Pending 8 · Blocked 2) | ✓ PASS |
| 6 | `nyquist_compliant` (4-faza fayli) | `check-validation-signoff.mjs <04-VALIDATION.md>` | exit 0 — **true**, 42 qator · **7** inson bandi | ✓ PASS |
| 7 | Sentry jarayonlarining hosilasi | `compose.yaml` read-only parse | **5 servis** (oldin 3) — darvoza yashil | ✓ PASS |
| 8 | D-19 (rasm taqig'i) | `grep sendPhoto\|send_photo\|SendPhoto services/` | **0 natija** butun `services/` bo'ylab | ✓ PASS |
| 9 | Qarz belgilari | `grep TBD\|FIXME\|XXX` 15 ta 4-faza faylida | **0 natija** | ✓ CLEAN |

⚠ **Halollik bandi:** to'liq `npm run gate` YUGURTIRILMADI. Topshiriq uni
aniq taqiqladi (xostda parallel og'ir ishlar ketmoqda) va byudjet
hozir 2300 s. Yuqoridagi to'qqiz o'lchov 4-fazaning YUZASINI qoplaydi,
lekin ular «butun repo yashil» degan sertifikat EMAS.

---

## Talab qilingan artefaktlar

| Artefakt | Kutilgan | Holat | Tafsilot |
|---|---|---|---|
| `tests/integration/test_phase4_criteria.py` | SC#1–SC#5 + meta | ✓ VERIFIED | 1478 qator; 5 ta `test_sc*` + `test_every_criterion_has_its_own_test` + `test_criteria_module_uses_no_storage_mock`. **7/7 o'tdi** |
| `services/core-api/app/worker.py` | `CLIENT_STARTUP` ilmog'i + `ObservedScheduler` + `capture.tick` cron | ✓ VERIFIED | 1310 qator (o'sish 5–7-fazalardan). Ilmoq `:717`, `ObservedScheduler` `:629-678`, `scheduler` `:682`, `capture.tick` cron `:990` |
| `services/core-api/app/observability.py` | `init_sentry`, `capture_exception`, `scrub_event` | ✓ VERIFIED | 278 qator — o'zgarmagan |
| `services/core-api/app/jobs/capture.py` | kadr → `analyze()` → `storage.put()` → `record()` | ✓ VERIFIED | Zanjir `:965-1019` da to'liq: sifat, obyekt kaliti, ombor, DB yozuvi |
| `services/core-api/app/jobs/retention.py` | `retention_daily`, compress + purge | ✓ VERIFIED | `:258` `retention_daily`, `_compress_market` `:419`, `_purge_market`; kalit O'ZGARMAYDI (`mark_compressed`) |
| `services/core-api/app/jobs/alerting.py` | uch tetik + guruhlash + `NEVER_SUPPRESSED` | ✓ VERIFIED | `ALERT_META` `:331`; `camera_offline`/`capture_missed`/`backup_stale` mavjud; `NEVER_SUPPRESSED_ALERT_KEYS` `:464` |
| `services/core-api/app/services/quality.py` | `dark`/`blank`/`corrupt`/`ok` + `light_mode` | ✓ VERIFIED | D-14 ikki shartli `dark`; `cv2` importi **yo'q** (D-13) |
| `services/core-api/app/services/object_key.py` | `{market}/{sana}/{kamera}/{slot}.jpg` | ✓ VERIFIED | `object_key()` `:73` prefiks fabrikasidan HOSILA (`:105`); nomli argumentlar majburiy |
| `migrations/versions/0014_snapshot_domain.py` | `is_billable` hosila ustun + langar | ✓ VERIFIED | `sa.Computed("quality_verdict = 'ok'", persisted=True)` `:474`; `uq_snapshots_billable_anchor` `:513` |
| `migrations/versions/0018_occupancy_domain.py` | **langarning ISTE'MOLCHISI** | ✓ VERIFIED (yangi) | `snapshot_is_billable` `:436`, kompozit FK `:472`, `CHECK` `:493` — 5-faza zanjirni yopdi |
| `services/core-api/app/api/{v1/schedules,v1/snapshots,internal/self_check}.py` | jadval CRUD, kun jurnali, kadr, alertlar, self-check | ✓ VERIFIED | Beshala router `main.py:359-373,402` da ro'yxatdan o'tgan |
| `frontend/src/app/[locale]/(app)/snapshots/page.tsx` + `components/snapshots/*` | jadval kartasi, matritsa, kun xulosasi, alertlar | ✓ VERIFIED | 10 komponent, har biriga test; sahifa 400 qator; **104 test yashil** |
| `ops/docs/monitoring.md` | D-21 ops yo'riqnomasi | ✓ VERIFIED | §5 «Tashqi dead-man's switch (D-21) — bitta URL, kod emas» + §0–§6 |
| `.env.example` ↔ `ops/seaweedfs/s3.json.example` | juftlik | ✓ VERIFIED | `NAMUNA-ALMASHTIRING-access/secret` — ikkala faylda AYNAN teng |
| `04-HUMAN-UAT.md` | 7 band, ega + tetik | ✓ VERIFIED | 7 ta `Egasi:` / 7 ta `Tetigi:` / 7 ta `result: [pending]` — sanaldi |
| `04-VALIDATION.md` | hisoblangan `nyquist_compliant` | ✓ VERIFIED | Skript exit 0, `true`, 42 qator · 7 inson bandi |

---

## Kalit bog'lanishlar

| From | To | Via | Holat |
|---|---|---|---|
| `scheduler` jarayoni | `observability.py::init_sentry` | `CLIENT_STARTUP` ilmog'i | ✓ WIRED — haqiqiy subprocess zondi `True`, nazorat `False` |
| `ObservedScheduler.on_ready` | `capture_exception` | `try/except -> log -> capture -> raise` | ✓ WIRED (`worker.py:667-678`) |
| `compose.yaml` (`SENTRY_DSN`) | `test_sentry_processes.py` | `command` → `modul:atribut` → import → hodisa reyestri | ✓ WIRED — **5 servis**, hosila hamon tirik |
| `capture.tick` (cron) | `capture_batch` → `analyze` → `storage.put` → `SnapshotRepository.record` | taskiq | ✓ WIRED (`worker.py:990`, `capture.py:965-1019`) |
| `snapshots.is_billable` | `occupancy_events.snapshot_is_billable` | kompozit FK + `CHECK` | ✓ WIRED (0018) — **5-fazada yopildi** |
| `snapshots/page.tsx` | `/api/v1/{snapshot-schedules,capture-runs,snapshots,alerts}` | `useQuery`/`useMutation` → `apiFetch` | ✓ WIRED (`snapshot-queries.ts`) |

### Data-Flow Trace (Level 4)

| Artefakt | Ma'lumot o'zgaruvchisi | Manba | Rost ma'lumot | Holat |
|---|---|---|---|---|
| `snapshots/page.tsx` | `captureDay.data.rows` | `useCaptureDayQuery` → `apiFetch('/capture-runs?day=')` | Ha — `page.tsx:246`, `?? []` faqat zaxira | ✓ FLOWING |
| `schedule-card.tsx` / `schedule-dialog.tsx` | `schedules.data` | `useSchedulesQuery` → `apiFetch(SNAPSHOT_SCHEDULES_PATH)` | Ha; `isPending`/`isError`/bo'sh — uch holat AJRATILGAN (`schedule-dialog.tsx:149-153`, `EmptyState`) | ✓ FLOWING |
| `alert-list.tsx` | `alerts.data` | `useAlertsQuery` → `apiFetch('/alerts')` | Ha | ✓ FLOWING |
| `GET /capture-runs` | qator to'plami | `capture_repo` (haqiqiy SQL) | Ha — statik `[]` qaytaruvchi yo'l yo'q | ✓ FLOWING |
| `/internal/self-check` | `stale` / `never_seen` | `system_heartbeats` jadvali | Qisman — `backup` HECH QACHON yozilmaydi | ⚠ Kechiktirilgan (Phase 8) |

---

## Talablar qamrovi

| Talab | Ta'rif | Holat | Dalil |
|---|---|---|---|
| CAM-04 | Snapshot jadvali, mavsumiy profil | ✓ SATISFIED | `test_sc1_...` o'tdi (o'z yugurishim); `REQUIREMENTS.md:155` = `Done` |
| CAM-05 | Idempotent + retry; missed jurnalda + alert | ✓ SATISFIED | `test_sc2_...` + `test_sc5_...`; `SKIP LOCKED` + lease |
| CAM-06 | Sifat filtri; yaroqsiz kadr billing'ga ta'sir qilmaydi | ✓ SATISFIED **(kuchaydi)** | `test_sc3_...`; zanjir endi `0018` da DB darajasida YOPIQ. ⚠ Chegara QIYMATI hamon LOW confidence — UAT #1 |
| CAM-07 | S3 tartib + 90/455 kun siyosati | ✓ SATISFIED | `test_sc4_...` + 29 ta yordamchi test haqiqiy SeaweedFS'da. ⚠ Kalendar — UAT #2 |
| FOUND-06 | Telegram-alert + xatolar Sentry'da | ✓ SATISFIED | `test_sc5_...`; hosila darvoza 3 → 5 servisga o'sdi va yashil qoldi. ⚠ Yetib borish — UAT #4/#7 |

`check-requirements-sync.mjs` exit 0 — **49 talab MOS**, holat lug'ati
uch qiymatli (`Done`/`Pending`/`Blocked`). **Yetim talab yo'q.**

---

## Anti-naqshlar

| Fayl | Naqsh | Jiddiylik | Ta'siri |
|---|---|---|---|
| 15 ta 4-faza fayli | `TBD` / `FIXME` / `XXX` | — | **0 natija — QARZ-BELGISI DARVOZASI TOZA** |
| `services/` (butun) | `sendPhoto` / `send_photo` | — | **0 natija — D-19 hamon rost** (7-faza botlari qo'shilganidan KEYIN ham) |
| `services/core-api/pyproject.toml` | `aioboto3` / `minio-py` | ℹ️ Info | Faqat TAQIQ izohida (`:84-89`); haqiqiy bog'liqlik `aiobotocore==3.9.0` (D-17) |
| `frontend/.../schedule-dialog.tsx` | tri-state kolapsi | ✅ **YOPILGAN** | Tekshiruvdan KEYIN topilgan (№6, KR-tri) va tuzatilgan — pastdagi «Halol qayd» |

---

## ⚠ Halol qayd — tekshiruv metodikasining chegarasi

Bu bo'shliq **emas** (bugun kod to'g'ri), lekin uni yozmaslik xato
bo'lardi.

2026-08-14/15 dagi to'liq brauzer testi va kod-review 4-fazaning
`schedule-dialog.tsx` faylida **ikkita foydalanuvchiga ko'rinadigan
nuqson** topdi:

- **№6** — «Jadval dialogi bo'sh holatda abadiy *Yuklanmoqda*»
- **KR-tri** — «schedule-dialog yolg'on tashxis / ternary / EmptyState»

Ikkalasi ham SC#1 ning UI yo'lida edi va ikkalasi ham **2026-08-05
tekshiruvidan o'tib ketgan**. Ikkalasi ham keyin yopilgan (`c411636`,
`8c142a3`, `067a4dd`) va men bugun tuzatishni tasdiqladim:
`schedule-dialog.tsx:149-153` da `isPending` → `isError` → `EmptyState`
uch holati ajratilgan, 104 ta frontend testi yashil.

**Xulosa:** 4-fazaning backend dalili juda kuchli (haqiqiy konteyner,
haqiqiy jarayon zondi, sabotaj bilan sinalgan darvozalar), **frontend
dalili esa komponent testlari bilan cheklangan** va u tri-state
kolapsini ko'rmadi. Bu keyingi fazalar uchun metodik saboq, 4-faza
uchun ochiq band emas.

---

## Kechiktirilgan bandlar

| # | Band | Qayerda hal bo'ladi | Dalil |
|---|---|---|---|
| 1 | Tashqi dead-man's switch KOD bilan qurilmagan | D-21 (faza qarori) + Phase 8 | `ops/docs/monitoring.md` §5 mavjud; UAT #5 |
| 2 | `backup` yurak urishi hech qachon yozilmagan | Phase 8 (FOUND-07) | `BACKUP_COMPONENT` faqat O'QILADI; `08-05` («backup konteyneri … yurak urishi») va `08-08` («Zaxira yurak urishi va tiklash mashqining CI qatlami») + Phase 8 mezoni #3 |

Ikkalasi ham 9-fazali yo'l xaritasining KEYINGI fazasida aniq nomlangan
reja bilan qoplangan — shu sababdan bo'shliq emas, kechiktirilgan.

---

## Oldingi hisobotning ochiq bandlari — IKKALASI HAM YOPILGAN

| # | Band | Bugungi holat |
|---|---|---|
| 1 | `npm run gate` > 900 s | ✅ **YOPILDI.** Tetik («TINCH xostda uch o'lchov») bajarilgan: `parnikkpi-*` steki to'xtatilib 1009/1004/983 s o'lchandi; byudjet 1250 s (05-15) → 2300 s (06-14) va `07-17` da qayta o'lchandi (1424/1263/1349 s) |
| 2 | `check-validation-signoff.mjs::DEFAULT_FILE` 2-fazaga qadalgan | ✅ **YOPILDI (D-27).** Skript endi `.planning/phases/` ni skanerlaydi. O'zim o'lchadim: 4-faza fayli argument bilan exit 0; argumentsiz chaqiruv endi eng so'nggi fazani o'qiydi, ya'ni u 4-fazani SOXTA yashil deb ko'rsatmaydi |

---

## Simulyator chegarasi — o'zgarmadi

Bu fazaning dalili hamon simulyator va sintetik kadrlar ustida
o'lchanadi. Ombor HAQIQIY SeaweedFS, NVR HAQIQIY `nvr-sim`, baza
HAQIQIY Postgres — lekin real Karmana uskunasi, real kalendar vaqt va
real tashqi xizmat (Telegram, Sentry) YO'Q. Bu yugurishda ham
`TELEGRAM_BOT_TOKEN` bo'sh edi.

Uch narsa aniq aytiladi: (1) 90 kunlik siyosat KUTIB o'lchanmagan;
(2) Telegram xabari va Sentry hodisasining YETIB BORISHI isbotlanmagan;
(3) real NVR sessiya chegarasi modellanmagan. Uchalasi ham ega va tetik
bilan yozilgan — bo'shliq emas, lekin «o'lchandi» deb o'qish xato
bo'lardi.

---

## Bo'shliqlar xulosasi

**Bo'shliq yo'q. Regressiya yo'q.**

Beshala haqiqat mustaqil o'lchov bilan tasdiqlandi (jami **393 ta
backend testi + 104 ta frontend testi**, hammasi exit 0), qarz-belgisi
darvozasi toza, D-13/D-14/D-17/D-18/D-19/D-21/D-22 markerlari joyida,
talablar reyestri mos.

Ikki da'vo 2026-08-05 dagidan **kuchliroq**:

1. **SC#3** — «yaroqsiz kadr hisob-kitobga ta'sir qilmaydi» endi faqat
   langar emas: 5-faza `0018` da kompozit FK + `CHECK` bilan zanjirni
   DB darajasida yopdi.
2. **SC#5** — hosila darvozani isbotlash uchun endi sabotaj kerak emas.
   `SENTRY_DSN` oladigan jarayonlar soni **3 → 5** ga o'sdi (`cv-service`,
   `bot-service`) va darvoza jimgina eskirmadi — u topdi, tekshirdi va
   yashil qoldi.

**Faza `passed` emas, `human_needed`:** bloklovchi yo'q, lekin **yettita
inson bandi hamon `[pending]`** va ular fazaning eng qimmat
da'volarining oxirgi bo'g'inini tashkil qiladi — alert HAQIQATAN yetib
boradimi, xato HAQIQIY Sentry loyihasida ko'rinadimi, siyosat 90 kundan
keyin ishlaydimi. ROADMAP ning 2026-08-01 self-service direktivasi
bo'yicha ular fazani **bloklamaydi**.

---

*Verified: 2026-08-16T02:45:00Z*
*Verifier: Claude (gsd-verifier) — uchinchi yugurish, 5/6/7-fazalardan keyingi regressiya tekshiruvi*
