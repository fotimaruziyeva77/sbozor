---
phase: 5
slug: kamera-zonalari-cv-va-nazoratchi-tasdig-i
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-05
---

# Phase 5 — Validation Strategy

> **Manba:** `05-RESEARCH.md` § `Validation Architecture`, `05-PATTERNS.md` §5 (Wave 0, 14 band), `05-UI-SPEC.md` darvozalari (G-11…G-19).

---

## Bu fazaning validatsiyasi boshqacha — buni birinchi o'qing

Oldingi to'rt fazada «to'g'ri ishlayaptimi?» savoliga test javob berardi. **Bu fazada bermaydi** (D-01).

Modelning band/bo'sh qarori to'g'riligi — bu haqiqatga qarshi **o'lchov**, va haqiqat (real Karmana kadrlari) hali yo'q. Shuning uchun validatsiya ikki qatlamga bo'linadi va ular aralashtirilmasligi shart:

| Qatlam | Nima isbotlanadi | Bugun mumkinmi |
|---|---|---|
| **Mexanika** | Zona geometriyasi, agregatsiya qoidasi, navbat oqimi, ko'r auditning xolisligi, billing chegarasi, immutabillik | **Ha, to'liq** — seam `sv.Detections` da, undan keyingi hamma narsa sintetik detektsiyalar bilan testlanadi |
| **Aniqlik** | RF-DETR ning verdikti qanchalik to'g'ri | **Yo'q** — oltin to'plam bo'sh; darvoza **uxlab yotadi** |

⚠ **Ikkinchi qatlamning yo'qligini birinchisining yashilligi bilan yopish taqiqlanadi.** Bu loyiha bu shaklni ikki marta rad etgan: 2-fazaning o'zini o'zi tasdiqlovchi shabloni va 3-fazaning «simulyatordan kadr olib tekshiramiz» taklifi.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` · `frontend/vitest.config.ts` |
| **Quick run command** | `npm run gate:fast` — chegara **180 s** (o'zgarmaydi) |
| **Full suite command** | `npm run gate` — chegara **W0-13 da qayta belgilanadi** (pastga qarang) |
| **Markerlar** | `tenancy`, `sim`, `hardware`, `slow` + **yangi: `golden`** (W0-10) |

**Bu fazada tug'iladigan infratuzilma:**

| Komponent | Nima uchun | Wave 0 |
|---|---|---|
| `services/cv-service/` — **loyihaning ikkinchi Python bog'liqlik to'plami** | `services/nvr-sim` da `pyproject.toml` ham, `Dockerfile` ham yo'q, ya'ni bu shakl repoda hech qachon qurilmagan | **W0-2**, W0-11, W0-12 |
| `tests/fixtures/detections.py` — `sv.Detections` konstruktori | **Usiz butun zona mantig'i darvoza emas, konventsiya** | **W0-7** |
| `tests/fixtures/golden_set/` + `manifest.jsonl` + `eval-golden-set.py` | Faza mahsuloti — **mashina**, raqam emas | **W0-9** |
| `frontend/src/lib/zone-geometry.ts` | Geometriya sof funksiyalarda — render qatlami almashadi, geometriya emas (D-05) | **W0-8** |

---

## Sampling Rate

- **Har task commitidan keyin:** `npm run gate:fast` (chegara **180 s**, o'zgarmaydi)
- **Har to'lqindan keyin:** `npm run gate`
- **Maksimal kechikish:** W0-13 o'lchoviga qarab

### `gate` byudjeti — 4-fazadan meros ochiq band (D-26)

4-faza chegarani **900 s** ga tushirdi, keyin `04-14` uni **1009 s va 1174 s** bo'lib o'tganini o'lchadi va **chegarani ko'tarmadi**. Sababni `04-VERIFICATION` nomladi: xostda **ikkinchi to'liq Docker steki** ishlab turgan (7 ta `parnikkpi-*` konteyner). Nazorat: `gate:fast` ayni bir xil ish ustida **68 s → 129 s**.

**W0-13 ning talabi:** o'lchov **tinch xostda** va **`cv-service` build'i qo'shilgandan keyin** uch marta olinadi. Chegara = eng yomon + 20 %.

⚠ **Jimgina oshib ketish ham, jimgina bo'sh qoldirish ham qabul qilinmaydi.** Agar tinch xost ta'minlanmasa — buni o'lchov sharti sifatida yozib qo'yish kerak, o'rtachaga aylantirib yashirish emas.

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator. **15 reja × 3 task = 45 qator.** `Threat Ref` — o'sha rejaning `<threat_model>` bloki (to'liq ro'yxat reja faylida).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01/T1 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | Reyestrlar, `PENDING_AUDIT_TRIGGERS` qulfi va ikki yangi ma… | avtomatik | `docker compose --profile test run --rm tests pytest tests/tenancy/test_meta.py tests/unit -q` | ⬜ | ⬜ pending |
| 05-01/T2 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | W0-3 — ko'r audit urug'ining zondi (`sha256(bytea)`, kengay… | avtomatik | `docker compose --profile test run --rm tests pytest tests/tenancy/test_audit_seed_probe.py -q` | ⬜ | ⬜ pending |
| 05-01/T3 | 05-01 | 1 | AI-02, AI-04 | T-05-01/02/04 | W0-9 — oltin to'plam skeleti va UXLAB YOTADIGAN aniqlik dar… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_golden_harness.py -m golden -q` | ⬜ | ⬜ pending |
| 05-02/T1 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | Litsenziya devori — uch qatlam, manifestdan OLDIN (W0-1, D-… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_license_fence.py -q` | ⬜ | ⬜ pending |
| 05-02/T2 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | `cv-service` — ikkinchi bog'liqlik to'plami, image va minim… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_license_fence.py tests/unit/test_sentry…` | ⬜ | ⬜ pending |
| 05-02/T3 | 05-02 | 1 | AI-02 | T-05-SC/05/06/07 | W0-7 — `sv.Detections` konstruktori, GEOMETRIK FAKT bo'yich… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_detection_fixtures.py -q` | ⬜ | ⬜ pending |
| 05-03/T1 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `lib/zone-geometry.ts` — 11 sof funksiya + G-19 darvozasi (… | avtomatik | `npm --prefix frontend run test:component` | ⬜ | ⬜ pending |
| 05-03/T2 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `lib/wilson.ts` — Wilson score oralig'i (W0-F3) | avtomatik | `npm --prefix frontend run test:component` | ⬜ | ⬜ pending |
| 05-03/T3 | 05-03 | 1 | AI-01, AI-04 | T-05-09/10/11 | `blind-payload.test.mjs` — G-12 va G-14 (W0-F4, D-17.2/3/4) | avtomatik | `npm --prefix frontend run test:unit` | ⬜ | ⬜ pending |
| 05-04/T1 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Oltinchi xato reyestri — backend, frontend ko'zgusi va uch til | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit -q && npm --prefix frontend run i18n:check` | ⬜ | ⬜ pending |
| 05-04/T2 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Navigatsiya — ikkita yozuv va RBAC tasdig'i (W0-F1, W0-F5) | avtomatik | `npm --prefix frontend run test:component && npm --prefix frontend run typecheck` | ⬜ | ⬜ pending |
| 05-04/T3 | 05-04 | 1 | AI-01, AI-03, AI-04, AI-06 | T-05-13/14/15 | Uch copy darvozasi + parity kengaytmasi + D-27 (G-11, G-15,… | avtomatik | `npm --prefix frontend run test:unit && node scripts/check-validation-signoff.mjs .planning/phases/05-kamera…` | ⬜ | ⬜ pending |
| 05-05/T1 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | Enumlar va olti model (`models/occupancy.py`) | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_enums.py -q && docker compose --profile…` | ⬜ | ⬜ pending |
| 05-05/T2 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | Ikki o'zgarmaslik qo'riqchisi va `0018_occupancy_domain` | avtomatik | `docker compose --profile migrate run --rm migrate alembic upgrade head && docker compose --profile test run…` | ⬜ | ⬜ pending |
| 05-05/T3 | 05-05 | 2 | AI-01, AI-02, AI-04, AI-05, AI-06 | T-05-17/18/19/20 | `0019` kaskad, seed fixture va uchta xulq darvozasi | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_occupancy_immutable.py tests/int…` | ⬜ | ⬜ pending |
| 05-06/T1 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `app/services/zone_geometry.py` — V5 validatsiyasi sof funk… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_zone_geometry.py -q` | ⬜ | ⬜ pending |
| 05-06/T2 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `camera_zone_repo.py` — versiyalash va qamrov (D-07, D-22) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_camera_zones_api.py -q` | ⬜ | ⬜ pending |
| 05-06/T3 | 05-06 | 3 | AI-01 | T-05-23/24/25 | `app/api/v1/camera_zones.py` — marshrutlar, RBAC va darvoza | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_camera_zones_api.py tests/tenanc…` | ⬜ | ⬜ pending |
| 05-07/T1 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/postprocess.py` — xom tenzor arifmetikasi (§4.3) | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_rfdetr_postprocess.py -q` | ⬜ | ⬜ pending |
| 05-07/T2 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/zones.py` — 0..1 ↔ piksel va zona verdicti (D-09,… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_zone_verdict.py -q` | ⬜ | ⬜ pending |
| 05-07/T3 | 05-07 | 3 | AI-02 | T-05-28/29/31 | `detector/session.py` + `annotate.py` — ONNX sessiya va dal… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_detector_has_no_stub.py -q` | ⬜ | ⬜ pending |
| 05-08/T1 | 05-08 | 4 | AI-02 | T-05-33/34/35 | Tor ombor klienti va tenant kontekstli sessiya | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/unit/test_storage_surface.py -q` | ⬜ | ⬜ pending |
| 05-08/T2 | 05-08 | 4 | AI-02 | T-05-33/34/35 | `jobs/detect.py` — orkestratsiya, idempotentlik va yurak ur… | avtomatik | `docker compose --profile test run --rm cv-tests pytest tests/integration/test_detect_job.py -q` | ⬜ | ⬜ pending |
| 05-08/T3 | 05-08 | 4 | AI-02 | T-05-33/34/35 | Cross-servis enqueue va sifat filtri | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_capture_enqueues_detect.py -q` | ⬜ | ⬜ pending |
| 05-09/T1 | 05-09 | 4 | AI-01 | T-05-39/40/41 | Kesh kalitlari, sxemalar, sahifa qobig'i va qamrov kartasi | avtomatik | `npm --prefix frontend run test:component && npm --prefix frontend run i18n:check && npm --prefix frontend r…` | ⬜ | ⬜ pending |
| 05-09/T2 | 05-09 | 4 | AI-01 | T-05-39/40/41 | SVG yuzasi va RO'YXAT yuzasi — chizish, sudrash va klaviatura | avtomatik | `npm --prefix frontend run test:component` | ⬜ | ⬜ pending |
| 05-09/T3 | 05-09 | 4 | AI-01 | T-05-39/40/41 | Asboblar, DL-1/DL-2 dialoglari va 300–1000 rasta uchun yord… | avtomatik + qo'lda | `npm --prefix frontend run test:component && node --test frontend/scripts/zone-copy.test.mjs` | ⬜ | ⬜ pending |
| 05-10/T1 | 05-10 | 5 | AI-03 | T-05-43/44/45 | `review_repo.py` — qulflab olish, byudjet va ustuvorlik | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py -q` | ⬜ | ⬜ pending |
| 05-10/T2 | 05-10 | 5 | AI-03 | T-05-43/44/45 | `app/api/v1/reviews.py` — bitta so'rov = bitta qaror (D-18) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py tests/tenancy…` | ⬜ | ⬜ pending |
| 05-10/T3 | 05-10 | 5 | AI-03 | T-05-43/44/45 | SC#3 darvozalari — OpenAPI skani, byudjet va ustuvorlik | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_uncertain_queue.py -q` | ⬜ | ⬜ pending |
| 05-11/T1 | 05-11 | 6 | AI-04 | T-05-49/50/51 | `jobs/audit_draw.py` — hosila urug', muzlatilgan doira, 70/… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | ⬜ | ⬜ pending |
| 05-11/T2 | 05-11 | 6 | AI-04 | T-05-49/50/51 | Ko'r serializer — maydonning UMUMAN yo'qligi (D-17.2) | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | ⬜ | ⬜ pending |
| 05-11/T3 | 05-11 | 6 | AI-04 | T-05-49/50/51 | SC#4 darvozasi — oltita invariant | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_blind_audit.py -q` | ⬜ | ⬜ pending |
| 05-12/T1 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | `sbozor_core/occupancy.py` — kameralararo agregatsiya (AI-0… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_aggregate_stall_slot.py -q` | ⬜ | ⬜ pending |
| 05-12/T2 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | `jobs/day_close.py` — materializatsiya va `default_empty` (… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_day_close.py -q` | ⬜ | ⬜ pending |
| 05-12/T3 | 05-12 | 7 | AI-04, AI-05, AI-06 | T-05-55/56/57 | Aniqlik hisoboti, `/occupancy` API va oltin to'plamning ula… | avtomatik | `docker compose --profile test run --rm tests pytest tests/unit/test_accuracy_report.py -q && docker compose…` | ⬜ | ⬜ pending |
| 05-13/T1 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Ikki ALOHIDA so'rov moduli, `z.strictObject` sxemasi va `/r… | avtomatik | `npm --prefix frontend run test:component && node --test frontend/scripts/blind-payload.test.mjs && npm --pr…` | ⬜ | ⬜ pending |
| 05-13/T2 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Y-2 sessiyasi — bitta band, dalil darvozasi, byudjet hisobl… | avtomatik | `npm --prefix frontend run test:component` | ⬜ | ⬜ pending |
| 05-13/T3 | 05-13 | 7 | AI-03, AI-04 | T-05-61/62/63 | Y-3 ko'r sessiya — uch kanal, oshkor paneli va G-13/G-14 | avtomatik + qo'lda | `npm --prefix frontend run test:component && node --test frontend/scripts/blind-payload.test.mjs` | ⬜ | ⬜ pending |
| 05-14/T1 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | So'rovlar, sahifa qobig'i va BESH hisoblagich | avtomatik | `npm --prefix frontend run test:component && node --test frontend/scripts/zone-copy.test.mjs` | ⬜ | ⬜ pending |
| 05-14/T2 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | Chalkashlik matritsasi va namuna holati | avtomatik | `npm --prefix frontend run test:component` | ⬜ | ⬜ pending |
| 05-14/T3 | 05-14 | 8 | AI-04, AI-05, AI-06 | T-05-67/68/69 | Rastalar ro'yxati, DL-5 va matn | avtomatik + qo'lda | `npm --prefix frontend test && npm --prefix frontend run i18n:check && npm --prefix frontend run build` | ⬜ | ⬜ pending |
| 05-15/T1 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | `test_phase5_criteria.py` — beshta mezon, meta-test va soxt… | avtomatik | `docker compose --profile test run --rm tests pytest tests/integration/test_phase5_criteria.py -q` | ⬜ | ⬜ pending |
| 05-15/T2 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | W0-13 — `gate` byudjetini TINCH XOSTDA uch marta o'lchash (… | avtomatik + qo'lda | `node -e "const p=require('./package.json'); if(!/cv:test/.test(p.scripts.gate)) { console.error('gate zanji…` | ⬜ | ⬜ pending |
| 05-15/T3 | 05-15 | 9 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | T-05-73/74/75 | `05-HUMAN-UAT.md`, validatsiya imzosi va talablarni belgilash | avtomatik + qo'lda | `` buyruq bormi? 4. `05-HUMAN-UAT.md` dagi **har** bandda egasi va tetigi bormi? 5. ⛔ **Halollik ko'rigi (qo…` | ⬜ | ⬜ pending |

---

## Wave 0 Requirements

`05-PATTERNS.md` §5 o'n to'rt bandni sanaydi. **Uchtasi migratsiyadan oldin hal qilinishi shart** — keyin aniqlash qayta migratsiya demakdir:

- [ ] **W0-1** (05-02/T1) — `tests/unit/test_license_fence.py`: `rfdetr-plus` / `LicenseRef-*` / AGPL darvozasi. **D-03 — litsenziya endi lockfile invarianti.** Keyin qo'shilsa `uv add rfdetr` allaqachon `torch` ni tortgan bo'lardi.
- [ ] **W0-2** — ⚠ **QAROR QULFLANDI (05-02/T2):** `cv-service` **o'z `pyproject.toml` + `uv.lock` + `Dockerfile`** i bilan keladi; testlari `services/cv-service/tests/` da va **yangi `cv-tests` konteynerida** yuradi (`cv-service` Dockerfile'ining `dev` target'i qayta ishlatiladi — `tests` ↔ `core-api` naqshining aynan takrori). Rad etilgan muqobil: CV kutubxonalarini `core-api` dev guruhiga olib kirish — `test_runtime_deps.py:91-94` `opencv-python-headless` ni **ikkala guruhda ham** taqiqlaydi va bu o'lchangan darvoza.
- [ ] **W0-3** — ⚠ **QAROR QULFLANDI (05-01/T2):** yadro **`sha256(bytea)`** — yangi kengaytma **YO'Q**, `require_extension()` chaqirilmaydi. Qaror fikr emas, **o'lchov**: `tests/fixtures/audit_seed_probe.py` + `tests/tenancy/test_audit_seed_probe.py` uni HAQIQIY `postgres:18.4` da o'lchaydi (`billable_probe.py` naqshi) va `0018` ning migratsiyasi `pgcrypto`siz bazada o'tishi bilan **xulqiy** tasdiqlanadi.
- [ ] **W0-4** (05-01/T1) — `OCCUPANCY_TENANT_TABLES` + `_AUDITED_` + `_DELETE_ORDER` reyestrlari. Reyestr **migratsiyadan oldin** yoziladi va meta-test vaqtincha qizil turadi — bu **kutilgan** (1-fazadagi `FINANCIAL_TABLES` naqshi).
- [ ] **W0-5** (05-01/T1) — `AUDITED_TABLES` ga `camera_zones`, `zone_reviews`.
- [ ] **W0-6** — 🔇 `market_delete_draft()` kaskadi. **IKKI BOSQICH va bu ataylab:** reyestr (`OCCUPANCY_DELETE_ORDER`) **05-01/T1** da — ya'ni migratsiyadan OLDIN, `SNAPSHOT_DELETE_ORDER` naqshi bo'yicha; funksiya tanasi + `0019` esa **05-05/T3** da, `0018` bilan **bir to'lqinda** (04-03 ning `0014`+`0015` juftligi shakli). `pg_catalog` to'liqlik darvozasi `0018` dan keyin qizaradi va `0019` uni yopadi.
- [ ] **W0-7** (05-02/T3) — `tests/fixtures/detections.py`: `sv.Detections` konstruktori, **geometrik fakt bo'yicha** nomlangan (`box_center_in_polygon`), hech qachon kutilgan verdikt bo'yicha emas — aks holda test o'z farazini tasdiqlaydi (4-fazadagi `frame_mean_8_stddev_2` naqshi).
- [ ] **W0-8** — `frontend/src/lib/zone-geometry.ts` + `zone-geometry.**test.tsx**` (**05-03/T1**). ⚠ **`.ts` test fayli `vitest` tomonidan JIMGINA o'tkazib yuboriladi** (`vitest.config.ts:34`). ⚠ UI-SPEC va RESEARCH `scripts/zone-geometry.test.mjs` ni taklif qiladi — u **bajarilmaydi** (M-3: `node --test` TS import qila olmaydi); §S-13 ning **A yo'li** tanlandi.
- [ ] **W0-9** (05-01/T3) — `tests/fixtures/golden_set/` skeleti + `manifest.jsonl` sxemasi + `scripts/eval-golden-set.py`. **Uxlab yotadigan darvoza:** `source='karmana'` qatorlari paydo bo'lgan kuni **kodsiz o'zi uyg'onadi**.
- [ ] **W0-10** (05-01/T1) — `golden` pytest markerini e'lon qilish. `--strict-markers` ostida e'lon qilinmagan marker **yig'ilishda** yiqiladi.
- [ ] **W0-11** — `compose.yaml` ga `cv-service` **va** `cv-tests` + `self_check.EXPECTED_COMPONENTS` ga `cv_detect` (**05-02/T2**). `SENTRY_DSN` berilishi bilan `test_sentry_processes.py` **avtomatik** talab qo'yadi, shuning uchun minimal `app/main.py` + `app/worker.py` (`init_sentry`) **o'sha taskda** tug'iladi. `cv_detect` bugun `never_seen` bo'ladi va `/internal/self-check` ni **buzmaydi** (`healthy = not stale and bool(seen)` — `backup` bilan aynan bir xil holat).
- [ ] **W0-12** (05-02/T1+T2) — ONNX artefaktini image'ga `COPY` bilan olib kirish (yuklab olish emas, D-24).
- [ ] **W0-13** — ⚠ `npm run gate` byudjetini **tinch xostda uch marta** o'lchash va 900 s ni qayta belgilash (D-26). ⚠ **YAGONA WAVE-0 BANDI KI OXIRIDA BAJARILADI (05-15/T2) va sabab ordinal:** o'lchovning sharti — zanjirda `cv-service` build'ining **mavjudligi**, u esa Wave 0 ning O'ZIDA (05-02) tug'iladi. Ya'ni bandni Wave 0 da bajarish shartni buzardi. Protokol (tinch xost tekshiruvi, uch o'lchov + `gate:fast` nazorati, chegara = eng yomon + 20 %) shu yerda va 05-15 da yozilgan.
- [ ] **W0-14** — ⚠ `scripts/check-validation-signoff.mjs::DEFAULT_FILE` ni fazadan mustaqil qilish (D-27, **05-04/T3**) — hozir 2-fazaga qadalgan. Topilmasa `exit 1`; tanlangan fayl yo'li **chop etiladi**.

🔇 = jimgina yiqiladigan (testlar yashil, ishlab chiqarish buzilgan)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger |
|----------|-------------|------------|-------|---------|
| **Modelning aniqligi** — RF-DETR ning verdikti qanchalik to'g'ri | AI-02, AI-04 | **Haqiqat yo'q.** Oltin to'plam bo'sh; sintetik detektsiyalar mexanikani isbotlaydi, **modelni emas**. Darvoza uxlab yotadi va real kadrlar kelganda o'zi uyg'onadi | Nazoratchi (yorliqlaydi) + ijrochi (o'lchaydi) | Phase 0 ning real kadrlari kelganda |
| RF-DETR ning COCO sinflari **o'zbek bozori mollarida umuman ishlaydimi** | AI-02 | Fazaning eng katta qoldiq xavfi, hamma joyda LOW confidence. `occupancy_events.model_version` `timm` klassifikatoriga raqobatlashuvchi verdikt yozish imkonini beradi | Nazoratchi | Birinchi real kadrlar to'plamida |
| Ko'r auditning **amaliy** xolisligi | AI-04 | Strukturaviy himoyalar (urug', payloadda yo'qlik, `CHECK`, immutabillik, 70/30) testlanadi; **nazoratchi haqiqatan langarlanmaganini** faqat real ish jarayoni ko'rsatadi | Nazoratchi + direktor | Pilot tayyorgarligi haftasi |
| Poligon chizishning **amalda bajariladiganligi** 300–1000 rasta uchun | AI-01 | UI-SPEC uch yordamchi bilan 2–5 soatni 0.5–1 soatga tushirishni **hisoblab** chiqdi; haqiqiy vaqt faqat real bozor chizmasida o'lchanadi | Bozor admini | Karmana chizmasi kelganda |
| Nazoratchining kunlik 30 bandlik byudjeti realmi | AI-03, AI-04 | Charchash va tezlik — inson o'lchovi | Nazoratchi | Pilotning birinchi haftasi |

> Bu bandlar **fazani bloklamaydi** (self-service direktivasi). `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 ning 14 bandi qoplangan; **W0-2, W0-3 va W0-6 birinchi migratsiyadan oldin**
- [ ] Zona mantig'i sintetik `sv.Detections` bilan **darvoza**, konventsiya emas (W0-7)
- [ ] Oltin to'plam darvozasi mavjud, **uxlab yotadi** va real ma'lumot kelganda kodsiz uyg'onadi (W0-9)
- [ ] Ko'r auditning beshala strukturaviy himoyasi testlangan (D-17)
- [ ] `gate` byudjeti **tinch xostda** uch o'lchov asosida qayta belgilandi (W0-13)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan
- [ ] ⚠ **Aniqlik da'vosi hech qayerda o'lchanmagan holda yozilmagan**

**Approval:** pending (rejalashtirish 2026-08-08 da yakunlandi — 15 reja, 9 to'lqin, 45 task)
