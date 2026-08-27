---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
verified: 2026-08-16T02:56:03Z
status: human_needed
score: 4/5 to'liq tasdiqlandi (SC2 — QISMAN: mexanika VERIFIED, real model bloklangan)
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  previous_verified: 2026-08-10T04:20:00Z
  note: >-
    Oldingi tekshiruv 05-12 va 05-15 SUMMARY yakunlanishidan (10-avg 15:23) va
    UI-SPEC o'zgarishidan (12-avg) OLDIN yozilgan, shuning uchun to'liq qayta
    o'lchov o'tkazildi — SUMMARY da'volari emas, o'z buyruqlarim bilan.
  gaps_closed:
    - "Deferred #3 — `occupancy_day_close_markets()` chaqiruvchisiz qolishi: 6-faza (0020/C-11) ikkala SQL funksiyani DROP qildi; `day_close` endi `active_market_ids()` ustida ishlaydi va `worker.py:1100` da `DAY_CLOSE_CRON` bilan REJALASHTIRILGAN. Yuza endi chaqiruvchiga ega."
  regressions:
    - "YO'Q — 5-faza kod yo'llarida 2026-08-10 04:51 dan keyin birorta commit yo'q (o'lchandi: `git log --since` bo'sh). `0018` faqat 6-faza tomonidan (78a0c6f) tarixiy holatni MUZLATISH uchun tegildi; o'zgarmaslik triggerlari joyida."
  new_findings:
    - "F-1 (WARNING): `test_a_different_round_number_draws_a_different_sample` FLAKY — birinchi yugurishimda QIZARDI, ikkinchisida yashil."
    - "F-2 (WARNING): `cv-service` konteyneri 44 soatdan beri `Exited (137)` — artefaktsiz UMUMAN ISHGA TUSHMAYDI; `sbozor:cv` navbatida 3 ta yetim vazifa."
    - "F-3 (WARNING): `cv-tests` dev bazasiga HAQIQIY `cv_detect` yurak urishini yozadi va `/internal/self-check` ni dev muhitida chalg'itadi."
deferred:
  - truth: "DL-5 rasta-slot qatorlari (vaqt · kamera · natija · manba)"
    addressed_in: "Phase 8"
    evidence: "Phase 8 goal: «Direktor raqamlarni o'zi chiqarib oladi»; `deferred-items.md` #3"
  - truth: "`fast_decision_ms` chegarasining javobda maydon sifatida bo'lishi"
    addressed_in: "Phase 8"
    evidence: "`deferred-items.md` #4 — chegara `accuracy_report.is_fast_decision()` da yashaydi"
human_verification:
  - test: "Detektorning aniqligi — real Karmana kadrlarida verdikt qanchalik to'g'ri"
    expected: "Oltin to'plamda `source='karmana'` qatorlari paydo bo'lishi va `-m golden` darvozasining KODSIZ uyg'onishi"
    why_human: "Haqiqat yo'q — manifestda 8 qator, `karmana` AYNAN 0 (o'zim sanadim). Sintetik `sv.Detections` zona mantig'ini isbotlaydi, modelni emas (D-01)"
  - test: "RF-DETR ning COCO sinflari o'zbek bozori mollarida ishlaydimi"
    expected: "Birinchi real kadrlar to'plamida sinflarning mazmunli ishlashi"
    why_human: "Fazaning eng katta qoldiq xavfi; sintetik detektsiya bu savolni umuman bermaydi"
  - test: "ONNX artefaktini eksport qilib `ops/models/` ga qo'yish"
    expected: "`pytest -m model` bandi (aynan bitta) yashil bo'lishi VA `cv-service` konteynerining ko'tarilishi"
    why_human: "Ops ishi — GPU ijarasi va eksport retsepti; `ops/models/` da faqat README.md bor (o'lchandi)"
  - test: "Artefakt qo'yilgach yetim navbatning so'rilishi"
    expected: "`sbozor:cv` (hozir 3 ta vazifa) bo'shashi va `occupancy_events` ning to'lishi"
    why_human: "Faqat tirik `cv-service` bilan o'lchanadi; bugun iste'molchi o'lik"
  - test: "Ko'r auditning amaliy xolisligi"
    expected: "Nazoratchi haqiqatan langarlanmasligi"
    why_human: "Strukturaviy himoyalar o'lchangan; odamning o'zini birorta test o'lchay olmaydi"
  - test: "Poligon chizishning amalda bajariladiganligi (300–1000 rasta)"
    expected: "Uch yordamchi bilan 0.5–1 soat"
    why_human: "Vaqt faqat real bozor chizmasida va real admin bilan o'lchanadi"
  - test: "Nazoratchining kunlik 30 bandlik byudjeti realmi"
    expected: "Charchashsiz bajariladigan hajm"
    why_human: "Byudjetning MEXANIZMI o'lchangan (409 `review_budget_exhausted`), QIYMATNING o'zi emas"
  - test: "D-05 chiqish yo'li: 60 poligonli kamerada `pointermove` > 16 ms mi"
    expected: "Sudrash 16 ms ichida"
    why_human: "Real brauzerdagi render o'lchovi — jsdom buni bermaydi"
  - test: "«Ko'rmasdan tekshirish» atamasining ona tilida ko'rigi (O-01)"
    expected: "Atama nazoratchiga tushunarli"
    why_human: "Til sifati — ona tilida so'zlashuvchi bahosi"
---

# Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i — Qayta tekshiruv

**Phase Goal:** Tizim har rastaning band/bo'shligini kadrdan aniqlaydi va bu javobning aniqligi halol — noaniq navbatidan emas, ko'r namunadan — o'lchanadi
**Verified:** 2026-08-16T02:56:03Z
**Status:** human_needed
**Re-verification:** HA — oldingi tekshiruv (2026-08-10 04:20) 05-12/05-15 SUMMARY yakunidan oldin yozilgan

---

## Bu tekshiruvning qoidasi

Maqsad ikki bandli va ular ALOHIDA o'lchanadi:

1. **«Tizim ... kadrdan aniqlaydi»** — detektsiya yo'li;
2. **«aniqligi ... ko'r namunadan o'lchanadi»** — o'lchov asbobi.

Ikkinchi band **to'liq qurilgan va tasdiqlangan**. Birinchi bandning
**mexanikasi** qurilgan, lekin **real model bilan hech qachon
bajarilmagan** — va bu holat bugun kodda emas, **ishlab turgan
muhitda** ham ko'rinadi (F-2). Hech qayerda yashirilmagan.

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Admin poligon chizadi; koordinatalar normalangan (0..1), versiyalangan, bitta rasta bir necha kameraga bog'lanadi | ✓ VERIFIED | `api/v1/camera_zones.py` **398 qator**, 4 marshrut (`GET /coverage`, `GET`, `PUT`, `DELETE`); `zone_geometry.py:383` — `0.0 <= x <= 1.0` shakli (`NaN` ni ham RAD ETADI, izohda sabab); `camera_zone_repo.py:394-402` — eskisi `is_active=false` JOYIDA qoladi, yangisi `version = MAX+1`; `uq_camera_zones_market_id_camera_id_stall_id_version` (`0018:391`) da `camera_id` KALIT ichida → ko'p kamera. O'zim yugurtirdim: **277 passed** (zone/occupancy to'plami), frontend **221 passed** |
| 2 | Har zona band/bo'sh/noaniq bahosini confidence bilan oladi; AI javobi hech qachon tahrirlanmaydi — nazoratchi qarori alohida yozuv | ⚠ **QISMAN** | **Ikkinchi jumla ✓ VERIFIED:** `0018:249-250` — `trg_occupancy_event_immutable` + `trg_zone_review_immutable`; nazoratchi qarori `zone_reviews` da ALOHIDA jadval. **Birinchi jumla ⚠ MEXANIKA-ONLY:** `detector/` 5 modul, `session.py:126` da HAQIQIY `ort.InferenceSession(..., providers=["CPUExecutionProvider"])`, `zones.py:248` `zone_verdict` ikki chegarali; `cv-tests` → **130 passed**. LEKIN barchasi SINTETIK detektsiya ustida — pastdagi F-2 ga qarang |
| 3 | Byudjet doirasidagi ustuvorlashtirilgan noaniq navbat; «hammasini tasdiqlash» tugmasi yo'q; javoblar dataset sifatida yig'iladi | ✓ VERIFIED | `AnswerRequest` da AYNAN BITTA maydon (`human_verdict`), massiv varianti YO'Q (`schemas.py:2681+`); `test_no_bulk_approve_endpoint` OpenAPI **sxemasini** skanerlaydi; `bulk-action-surface.test.mjs` → **16 pass** va qamrov UI-SPEC §15 **e'lonidan hosila**; `review/` va `blind-audit/` kataloglarida `type="checkbox"` YO'Q (o'zim skanerladim) |
| 4 | Nazoratchi ko'r audit navbatida AI javobini ko'rmasdan baholaydi — aniqlik hisoboti faqat shu namunadan | ✓ VERIFIED (⚠ F-1) | `BlindItemResponse` (`schemas.py:2628+`) — 10 ta neytral maydon, sakkiz AI maydonining BIRORTASI e'lon qilinmagan (sinfni to'liq o'qidim, `None` bilan emas — kalitning O'ZI yo'q); `accuracy_report.py:396` — `purpose == 'eval' AND queue_kind == 'blind_audit'` IKKI shartli filtr; `audit_draw.py:237-290` `sha256` `ORDER BY`, `random()` yo'q; `measured = n >= MIN_SAMPLE_FOR_PERCENT` SERVERDA (`:408`), foiz faqat `report.measured` da chiziladi (`confusion-matrix.tsx:156`). O'zim: **33 passed** (`test_blind_audit.py` yolg'iz). ⚠ F-1 — flaky test |
| 5 | Birortasi «band» desa rasta band; tasdiqlanmagan «noaniq» kun oxirida «bo'sh» va hisobotda alohida belgilanadi | ✓ VERIFIED | `sbozor_core/occupancy.py` (273 qator) — `occupied > uncertain > empty > no_coverage`; `effective_verdict()` `uncertain → ('empty','default_empty')`; bo'sh kirish `no_coverage` beradi, `empty` EMAS (D-22); `schemas.py:2884` — `default_empty` **ALOHIDA hisoblagich**. Kun yopilishi TIRIK: `worker.py:1100` `@broker.task(task_name="occupancy.day_close", schedule=[{"cron": DAY_CLOSE_CRON}])` va u KECHAGI kunni yopadi |

**Score: 4/5 to'liq · 1 qisman (SC2)**

---

### Ikkinchi qatlam — ATAYIN ISBOTLANMAGAN va bu to'g'ri

| Miqdor | Holat | O'zim tekshirdim |
|---|---|---|
| RF-DETR verdiktining aniqligi | ⛔ **O'LCHANMAGAN** | `manifest.jsonl` — **8 qator, `karmana` AYNAN 0** (`grep -c` → 0); `ops/models/` da faqat `README.md` |
| Aniqlik darvozasi | 😴 **UXLAB YOTIBDI** | `test_golden_harness.py` → **9 passed**; `test_the_accuracy_gate_is_asleep_today` bu **skip EMAS** — u `len(karmana) == 0` ni FAKT sifatida qayd etadi va real kadr kelgan kuni QIZARADI |
| Real artefakt yo'li | ⛔ **YIQILADI (skip emas)** | `pytest -m model` → **EXIT 1**, `AssertionError: ONNX artefakti topilmadi: /app/models/rfdetr-large.onnx`. Aynan **1 ta** marker (`test_onnx_session.py:106`), `addopts` uni standart zanjirdan chiqaradi |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `services/core-api/app/api/v1/camera_zones.py` | Zona API (AI-01) | ✓ VERIFIED | 398 qator, 4 marshrut — stub emas |
| `services/core-api/app/services/zone_geometry.py` | Normalanish darvozasi | ✓ VERIFIED | 495 qator; `NaN` ni ham rad etadi |
| `services/core-api/app/repositories/camera_zone_repo.py` | Versiyalash | ✓ VERIFIED | 615 qator; `version = MAX+1`, eskisi joyida |
| `services/cv-service/app/detector/` | Haqiqiy ONNX yo'li | ⚠ WIRED, MA'LUMOT OQMAYDI | 5 modul; kod real, lekin artefaktsiz **ishga tushmaydi** (F-2) |
| `services/cv-service/app/jobs/detect.py` | Orkestratsiya | ✓ WIRED | `session_detector` → `preprocess` → `run` → `raw_to_detections` → `zone_verdict` → `OccupancyWriter` |
| `migrations/versions/0018_occupancy_domain.py` | O'zgarmaslik + langarlar | ✓ VERIFIED | Ikki trigger (`:249-250`); `fk_zone_reviews_queue_kind_anchor` + `uq_review_assignments_queue_anchor` |
| `services/core-api/app/jobs/audit_draw.py` | Hosila urug', 70/30 | ✓ VERIFIED | `sha256` `ORDER BY`, `random()` yo'q; `eval_quota` `Decimal` bilan |
| `services/core-api/app/jobs/day_close.py` | Kun yopilishi | ✓ VERIFIED + REJALASHTIRILGAN | `worker.py:1100` cron; 6-fazadagi DROP dan keyin `active_market_ids()` ga o'tgan |
| `services/core-api/app/services/accuracy_report.py` | Ko'r namunadan hisobot | ✓ VERIFIED | Ikki shartli filtr `:396`; `measured` serverda `:408` |
| `packages/sbozor-core/sbozor_core/occupancy.py` | Agregatsiya | ✓ VERIFIED | 273 qator; `effective_verdict` + `aggregate_stall_slot` |
| `frontend/src/components/camera-zones/` | Y-1 muharrir | ✓ VERIFIED | 7 komponent; `zone-editor.tsx` ~29 KB, `zone-canvas.tsx` ~17 KB |
| `frontend/src/components/{review,blind-audit,occupancy}/` | Y-2/Y-3/Y-4 | ✓ VERIFIED | Barchasi substantiv; **221 test yashil** |
| `ops/models/rfdetr-large.onnx` | Inference artefakti | ✗ **MISSING** | Katalogda faqat `README.md` — bu KUTILGAN (repoda saqlanmaydi), lekin oqibati F-2 |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `capture.py:1067` | `cv.detect` navbati | `enqueue_detect()` | ✓ WIRED | Yagona chaqiruvchi; `CV_QUEUE_NAME = "sbozor:cv"` |
| `sbozor:cv` | `cv-service` `detect_task` | taskiq broker | ✗ **UZILGAN (runtime)** | Iste'molchi **o'lik**; navbatda **3 ta yetim vazifa** (o'zim o'lchadim) |
| `worker.py:1100` | `day_close()` | `DAY_CLOSE_CRON` | ✓ WIRED | Kechagi kunni yopadi (`business_today() - 1`) |
| `worker.py:1074` | `daily_queue_tick()` | `QUEUE_TICK_CRON` (19:30) | ✓ WIRED | Noaniq navbat + ko'r audit tortuvi |
| `accuracy_report()` | ko'r namuna | `purpose=='eval' AND queue_kind=='blind_audit'` | ✓ WIRED | Ikki shart, `:396` |
| `GET /snapshots/{id}/image` | `require_any_permission` | `EVIDENCE_FRAME_PERMISSIONS` | ✓ WIRED, KENGAYMAGAN | Butun `services/` da AYNAN **1 ta** haqiqiy ishlatish (`snapshots.py:479`); qolgan 6 uchrash — «ISHLATILMAYDI» deb yozilgan izohlar |
| `confusion-matrix.tsx` | `report.measured` | server qarori | ✓ WIRED | Foiz faqat `measured` rost bo'lganda |

---

### Data-Flow Trace (Level 4)

| Artifact | Data manbai | Real ma'lumot oqadimi | Status |
|---|---|---|---|
| Y-1 zona muharriri | `GET /camera-zones?camera_id=` (`camera-zone-queries.ts:103`) | HA | ✓ FLOWING |
| Y-2 noaniq navbat | `GET /review/uncertain/next` | HA | ✓ FLOWING |
| Y-3 ko'r audit | `GET /review/blind/next` (`blind-audit-queries.ts:110`) | HA | ✓ FLOWING |
| Y-4 aniqlik hisoboti | `accuracy_report()` → `measured` | HA (bo'sh namunada `measured=False`, foiz `None`) | ✓ FLOWING |
| `occupancy_events` | `cv-service detect_task` | ⛔ **YO'Q** — ishlab chiqaruvchi o'lik | ✗ **DISCONNECTED (runtime)** |

---

### Behavioral Spot-Checks (hammasini O'ZIM yugurtirdim)

| Behavior | Command | Result | Status |
|---|---|---|---|
| Beshala mezon | `pytest tests/integration/test_phase5_criteria.py -q` | **9 passed** | ✓ PASS |
| Ko'r audit (yolg'iz) | `pytest tests/integration/test_blind_audit.py -q` | **33 passed**, exit 0 | ✓ PASS |
| Mezon + ko'r audit + navbat (1-urinish) | `pytest test_phase5_criteria.py test_blind_audit.py test_uncertain_queue.py -q` | **1 FAILED** | ✗ **FAIL (F-1)** |
| O'sha buyruq (2-urinish, AYNI) | yuqoridagining takrori | **70 passed**, exit 0 | ✓ PASS |
| Zona · agregatsiya · aniqlik · kun yopilishi | `pytest tests/unit/test_accuracy_report.py test_aggregate_stall_slot.py test_zone_geometry.py tests/integration/test_camera_zones_api.py test_day_close.py test_occupancy_report.py test_occupancy_immutable.py -q` | **277 passed**, exit 0 | ✓ PASS |
| cv-service | `docker compose run --rm cv-tests pytest -q` | **130 passed**, exit 0 | ✓ PASS |
| Model darvozasi | `cv-tests pytest -m model -q` | **exit 1** — `ONNX artefakti topilmadi` | ✓ PASS (kutilgan YIQILISH) |
| Oltin to'plam | `pytest tests/unit/test_golden_harness.py -q` | **9 passed** | ✓ PASS (uxlab yotibdi) |
| Tenancy qamrovi | `pytest tests/tenancy/test_personal_data_coverage.py test_camera_route_coverage.py -q` | **39 passed**, exit 0 | ✓ PASS |
| Frontend Y-1…Y-4 | `npx vitest run src/components/{camera-zones,review,blind-audit,occupancy} src/lib/*-queries.test.tsx` | **221 passed** (13 fayl) | ✓ PASS |
| Ommaviy amal darvozasi | `node --test scripts/blind-payload.test.mjs scripts/bulk-action-surface.test.mjs` | **16 pass**, 0 fail | ✓ PASS |
| Talablar sinxroni | `npm run requirements:check` | **49 MOS** — Done 39 · Pending 8 · Blocked 2 | ✓ PASS |
| `cv-service` runtime | `docker compose ps -a` + `docker logs` | **`Exited (137)`, 44 soat** — `ValidationError: CV_MODEL_PATH topilmadi` | ✗ **FAIL (F-2)** |
| Yetim navbat | `valkey-cli LLEN sbozor:cv` | **3** | ⚠ WARN (F-2) |
| `/internal/self-check` | `GET /internal/self-check` | **503** — `stale:["retention"]`, `never_seen:[backup, billing_close, …]` | ⚠ WARN (F-3) |
| To'liq `npm run gate` | — | ? SKIP — xostda ikkinchi stek (`parnikkpi-*` 6 konteyner) ishlab turibdi; topshiriqda og'ir suite taqiqlangan | ? SKIP |

---

### Requirements Coverage

| Requirement | Status | Verdict | Evidence |
|---|---|---|---|
| **AI-01** | `Done` | ✓ SATISFIED | Normalanish DARVOZA (piksel → 422), versiyalash, ko'p kamera |
| **AI-02** | `Blocked` | ✓ **TO'G'RI TASNIFLANGAN** | Ikkinchi jumla to'liq o'lchangan; birinchisi real artefaktsiz bajarilmaydi. `REQUIREMENTS.md:162` da egasi/tetigi/bandlari yozilgan — **halol** |
| **AI-03** | `Done` | ✓ SATISFIED | Byudjet 409, ustuvorlik, ommaviy yuza YO'Q |
| **AI-04** | `Done` | ✓ SATISFIED | Ko'r payload + ikki shartli hisobot filtri |
| **AI-05** | `Done` | ✓ SATISFIED | `aggregate_stall_slot()`; `occupied` yutadi |
| **AI-06** | `Done` | ✓ SATISFIED | `default_empty` alohida hisoblagich |

Yaroqsiz `Complete` qiymati yo'q; `npm run requirements:check` mexanik tasdiqladi.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | `TBD` / `FIXME` / `XXX` / `HACK` / `PLACEHOLDER` | — | **TOPILMADI** — 5-fazaning barcha asosiy `.py`/`.tsx` fayllari skanerlandi |
| — | — | Stub / bo'sh ekran | — | **TOPILMADI** |

---

## Yangi topilmalar — oldingi tekshiruvda YO'Q edi

### ⚠ F-1: ko'r audit urug' testi FLAKY (o'z ko'zim bilan qizardi)

`test_a_different_round_number_draws_a_different_sample` mening
**birinchi** yugurishimda qizardi:

```
AssertionError: kun namunani o'zgartirmadi — urug' `ORDER BY` da emas
assert {UUID('092a44...')} != {UUID('092a44...')}  → Both sets are equal
```

**AYNI buyruq ikkinchi marta — 70 passed, exit 0.** Yolg'iz yugurganda
33 passed.

**Bu mahsulot nosozligi EMAS va men buni tasdiqladim:** urug'ning
ta'siri uchta MUSTAQIL yo'l bilan isbotlangan —
`test_the_sample_query_orders_by_the_derived_seed` (kompilyatsiya
qilingan SQL da `sha256(` bor), `test_sample_is_reproducible` (baza =
qayta hisoblangan namuna) va o'sha testning **bazadan mustaqil**
`first_round != seedless` sharti.

**Sabab test dizaynida va mualliflar uni O'ZLARI yozib qo'yishgan**
(`test_blind_audit.py:111-115`):

> `C(12, 4) = 495` — ya'ni ikki xil tartib TASODIFAN ayni to'plamni
> berish ehtimoli 1/495.

Testda shu shakldagi **uchta** `!=` sharti bor, ya'ni har yugurishda
**~0,6 % yolg'on-qizil**. Men uni birinchi urinishda ushladim.

**Nima xavfli:** faza darvozasi tasodifan qizarsa, jamoa «yana o'sha
flaky» deb qayta yugurtirishga o'rganadi — va HAQIQIY regressiya aynan
shu odat ostida ko'milib ketadi. Tuzatish arzon: `FRAME_TARGET` ni
oshirish (`C(20,4) = 4845`) yoki namunani qat'iy TARTIB bo'yicha
solishtirish.

### ⚠ F-2: `cv-service` 44 soatdan beri o'lik — artefaktsiz ishga TUSHMAYDI

```
docker compose ps -a  → cv-service   Exited (137) 44 hours ago
docker logs sbozor-cv-service-1:
  pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  cv_model_path
    Value error, CV_MODEL_PATH (/app/models/rfdetr-large.onnx) topilmadi.
```

`settings.py:83-99` validatori artefaktsiz **ishga tushishni rad
etadi** (D-24), `Dockerfile:71` esa `COPY ops/models/ /app/models/`
qiladi — o'sha katalogda faqat `README.md` bor. Ya'ni bu **muhit
nosozligi emas, e'lon qilingan xulq**.

Oqibati bugun **o'lchanadigan** holatda:

| O'lchov | Qiymat |
|---|---|
| `valkey-cli LLEN sbozor:cv` | **3** — yetim `cv.detect` vazifalari |
| `occupancy_events` ishlab chiqaruvchisi | **yo'q** |

⚠ Bu aynan `compose.yaml:448-451` ogohlantirgan **«jimgina yolg'on»**
sinfining qo'shnisi. O'sha izoh servisni PROFIL ortiga yashirishdan
qo'rqqan edi; bugungi holat esa boshqa yo'l bilan o'sha nuqtaga keladi
— servis profilsiz, navbat to'ladi, iste'molchi esa o'lik.

**Bloklovchi emas:** artefaktning yo'qligi `AI-02 = Blocked` sifatida
OCHIQ e'lon qilingan va uch inson bandi (#1, #2, #3) shu ishni
kutmoqda. Bu topilma o'sha blokning **operatsion ko'rinishi** — 5-faza
kodining kamchiligi emas.

### ⚠ F-3: `cv-tests` dev bazasiga HAQIQIY yurak urishini yozadi

`/internal/self-check` bugun **503** qaytardi, lekin ro'yxatda
`cv_detect` **YO'Q** — na `stale`, na `never_seen`:

```json
{"ok":false,"stale":["retention"],
 "never_seen":["backup","billing_close","notify_digest_evening", …]}
```

Sabab bazada:

```
cv_detect | 2026-08-16 07:45:01+05 | {"zones": 2, "flagged": 0, "written": 2}
```

**07:45:01 — bu mening `cv-tests` yugurtirgan daqiqam.** `compose.yaml:
536-556` bu tanlovni ochiq yozadi: `cv-tests` `testcontainers`
ishlatmaydi va `DATABASE_URL` ga, ya'ni **dev bazasining o'ziga**
boradi.

Natijada `self_check.py:134-145` ning e'lon qilingan kafolati —
«`cv_detect` `never_seen` ro'yxatida OCHIQ ko'rinadi» — **dev muhitida
test yugurtirilgan zahoti buziladi**: monitor o'lik quvurni sog'lom
deb ko'rsatadi.

**Ishlab chiqarishga tegmaydi** (`test` profili u yerda yugurmaydi),
shuning uchun bu WARNING, BLOCKER emas. Lekin D-20 ning butun g'oyasi
«muvaffaqiyat signalining YO'QLIGIGA alert qo'yish» edi — va dev'da
o'sha signalni test soxtalashtira oladi.

---

## Oldingi tekshiruvdan beri YOPILGAN

| Element | Holat |
|---|---|
| Deferred #3 — `occupancy_day_close_markets()` chaqiruvchisiz | ✅ **YOPILDI.** 6-faza (`78a0c6f`) ikkala SQL funksiyani DROP qildi (C-11/G-10 — chaqiruvchisiz `SECURITY DEFINER` yuzasi); `day_close` endi `active_market_ids()` ustida va `worker.py:1100` da cron bilan rejalashtirilgan |
| W-1 / W-2 / W-3 (05-16) | ✅ Tasdiqladim: `require_any_permission` butun `services/` da aynan **1 ta** haqiqiy ishlatishda; `bulk-action-surface.test.mjs` qamrovni **e'londan** oladi (16 pass) |
| Regressiya | ✅ **YO'Q** — 5-faza kod yo'llarida 04:51 dan keyin commit yo'q; `0018` ga 6-faza faqat tarixiy holatni muzlatish uchun tegdi |

---

## Human Verification Required

Fazani bloklamaydi (self-service direktivasi), lekin ularsiz
**«detektor to'g'ri ishlaydi» da'vosi berilmagan bo'lib qoladi.**
To'liq matn `05-HUMAN-UAT.md` da.

### 1. Detektorning aniqligi
**Test:** Real Karmana kadrlarini yorliqlab `manifest.jsonl` ga `source='karmana'` qo'shish, so'ng `pytest -m golden`
**Expected:** Uxlab yotgan darvoza **kodsiz uyg'onadi**
**Why human:** Bugun `karmana` qatorlari aynan 0

### 2. COCO sinflari o'zbek bozori mollarida
**Test:** Birinchi real kadrlar to'plamida verdiktlarni ko'zdan kechirish
**Expected:** Sinflar mazmunli ishlaydi (yoki `timm` ikkinchi bosqichi kerakligi ma'lum bo'ladi)
**Why human:** Sintetik detektsiya bu savolni umuman bermaydi

### 3. ONNX artefaktini eksport qilish
**Test:** `rfdetr[train,onnx]` → `ops/models/rfdetr-large.onnx` → `pytest -m model`
**Expected:** Bitta model-markerli test yashil **va `cv-service` ko'tariladi**
**Why human:** Ops ishi + GPU ijarasi

### 4. Yetim navbatning so'rilishi (F-2 dan yangi)
**Test:** Artefakt qo'yilgach `cv-service` ni ko'tarib `sbozor:cv` ni kuzatish
**Expected:** 3 ta yetim vazifa so'riladi, `occupancy_events` to'ladi
**Why human:** Faqat tirik iste'molchi bilan o'lchanadi

### 5. Ko'r auditning amaliy xolisligi
**Test:** Nazoratchi bilan pilot haftasida ishlash
**Expected:** Nazoratchi tizim javobini taxmin qilishga urinmaydi
**Why human:** Odamning o'zini test o'lchamaydi

### 6. Poligon chizishning amalda bajariladiganligi
**Test:** Real Karmana chizmasida 300–1000 rastani chizish
**Expected:** Uch yordamchi bilan 0.5–1 soat
**Why human:** Vaqt faqat real admin bilan o'lchanadi

### 7. Kunlik 30 bandlik byudjet realmi
**Test:** Nazoratchi bir hafta navbatni yuritadi
**Expected:** Charchashsiz bajariladi
**Why human:** MEXANIZM o'lchangan, QIYMAT emas

### 8. D-05 chiqish yo'li — 60 poligonli kamerada sudrash
**Test:** Real brauzerda `pointermove` kechikishini o'lchash
**Expected:** ≤16 ms
**Why human:** jsdom render vaqtini bermaydi

### 9. «Ko'rmasdan tekshirish» atamasi (O-01)
**Test:** Ona tilida so'zlashuvchi + direktor atamani ko'rib chiqadi
**Expected:** Nazoratchi uchun tushunarli
**Why human:** Til sifati

---

## Gaps Summary

**Bloklovchi bo'shliq TOPILMADI.** Beshta ROADMAP mezonidan **to'rttasi
to'liq**, biri (**SC2**) **qisman** bajarilgan va qismanligi kodning
kamchiligidan emas — **repoda yo'q ONNX artefaktidan**.

Hamma raqamni SUMMARY dan emas, **o'z buyruqlarim bilan** oldim:
9 + 33 + 70 + 277 + 130 + 9 + 39 test (core/cv), 221 vitest, 16
`node --test` — hammasi exit 0, va **ikkita atayin qizil** (`-m model`
yiqilishi va F-1 flakei).

**Halollik skani toza:** aniqlik foizi hech qayerda da'vo qilinmagan;
`AI-02` `Blocked`; ikki darvoza (`-m model`, `-m golden`) uxlab
yotibdi va ikkalasi ham **skip emas** — biri yiqiladi, ikkinchisi
bugungi holatni fakt sifatida qulflaydi.

Uchta yangi ogohlantirish **bugungi mahsulot xulqini buzmaydi**:

- **F-1** — faza darvozasining ~0,6 % yolg'on-qizil ehtimoli. Tuzatish:
  `FRAME_TARGET` ni 12 → 20 (`C(20,4) = 4845`).
- **F-2** — `cv-service` artefaktsiz ishga tushmaydi; `sbozor:cv` da 3
  yetim vazifa. Bu `AI-02 = Blocked` ning operatsion ko'rinishi; inson
  bandi #3 va #4 buni yopadi.
- **F-3** — `cv-tests` dev bazasiga `cv_detect` yurak urishini yozadi
  va `/internal/self-check` ni dev'da chalg'itadi. Ishlab chiqarishga
  tegmaydi.

⚠ **Ikkinchi qatlam — aniqlik — hamon MAVJUD EMAS va bu kutilgan
holat.** Oltin to'plam bo'sh, artefakt yo'q, model yo'li hech qachon
bajarilmagan. Hech qayerda yashirilmagan.

---

*Verified: 2026-08-16T02:56:03Z*
*Verifier: Claude (gsd-verifier) — qayta tekshiruv*
