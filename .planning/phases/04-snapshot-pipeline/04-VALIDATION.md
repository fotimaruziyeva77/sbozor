---
phase: 4
slug: snapshot-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-04
---

# Phase 4 — Validation Strategy

> Fazani ijro qilish davomida teskari aloqa namunasini olish uchun validatsiya kontrakti.
> **Manba:** `04-RESEARCH.md` § `Validation Architecture`, `04-PATTERNS.md` §5 (Wave 0, 11 band), `04-UI-SPEC.md` darvozalari (G-1…G-7 + W0-F7).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (`asyncio_mode=auto`) · vitest (frontend) · `node:test` (skript darvozalari) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) · `frontend/vitest.config.ts` |
| **Quick run command** | `npm run gate:fast` — 3-fazada o'lchandi: **32 s**, chegara 180 s |
| **Full suite command** | `npm run gate` — 3-fazada oxirgi toza o'lchov: **538 s** |
| **Slow lane** | `npm run test:sim:slow` (`-m "sim and slow"`) — `gate` dan ataylab tashqarida |
| **Markerlar** | `tenancy`, `sim`, `hardware`, `slow` — **yangi marker kerak emas** (W0-11 buni tasdiqlaydi, qo'shmaydi) |

**Bu fazada tug'iladigan infratuzilma:**

| Komponent | Nima uchun | Wave 0 bandi |
|---|---|---|
| `taskiq scheduler` konteyneri | D-02 — holatsiz 1-daqiqalik tik | **W0-3** |
| `storage` (SeaweedFS) xizmati | CAM-07 — S3-mos arxiv | **W0-4** |
| `tests/fixtures/frames.py` — sintetik JPEG generatori | **Usiz sifat filtri darvoza emas, konventsiya** | **W0-9** |
| `nvr-sim` ning `frame_mode` boshqaruvi | Buzuq kadrni MediaMTX **bera olmaydi** — u yaroqli oqim beradi, ya'ni baytlarni sim boshqarishi shart | **W0-10** |

---

## Sampling Rate

- **Har task commitidan keyin:** `npm run gate:fast`
- **Har to'lqindan keyin:** `npm run gate`
- **`/gsd-verify-work` dan oldin:** to'liq to'plam yashil
- **Task darajasidagi chegara:** **180 s** — o'zgarmaydi (3-fazada 32 s o'lchangan, 5.6× zaxira sog'lom)

### 3-fazadan meros qolgan band: to'lqin chegarasi

3-faza qayta bajarish qismini yopdi (`gate` 1000 s → **538 s**, qamrov kamaymadi: 1520 ⊃ 412 ⊃ 76), lekin chegarani **1200 s da qoldirdi** va buni ochiq band sifatida shu fazaga topshirdi. Sabab yozib qo'yilgan: 538 s ga 2.2× zaxira — **signal bo'shashgan**, ya'ni sekinlashuv chegaraga urilguncha uzoq sezilmaydi.

**Bu fazaning qarori:** chegara **bir necha yugurish o'lchovi** asosida qayta belgilanadi, bitta o'lchov bilan emas. Bu faza `storage` va `scheduler` konteynerlarini qo'shadi, ya'ni bazaviy vaqt o'sadi — shuning uchun:

| Qadam | Kim | Nima |
|---|---|---|
| 1 | Wave 0 rejasi | 3× o'lchov (sovuq / issiq / issiq) **yangi konteynerlar bilan** |
| 2 | Yakuniy reja | Yana 3× o'lchov, chegara = eng yomon + 20 % |
| 3 | — | Agar yangi chegara 1200 s dan past bo'lsa — **tushiriladi**; oshsa — sabab bilan asoslanadi |

⚠ **Jimgina oshib ketish yoki jimgina bo'sh qoldirish — ikkalasi ham qabul qilinmaydi.**

---

## Per-Task Verification Map

*Har PLAN.md taski uchun bitta qator — `gsd-planner` to'ldiradi. `Status` ustunini ijrochi to'ldiradi.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01/T1 | 04-01 | 1 | CAM-07 | T-04-01…05, T-04-SC | Prod bog'liqliklari to'g'ri guruhda; `storage`/`scheduler` profilsiz; `s3.json` da `anonymous` yo'q; ombor porti publish qilinmagan | unit | `pytest tests/unit/test_runtime_deps.py tests/unit/test_storage_config.py -q` | yangi | ⬜ pending |
| 04-01/T2 | 04-01 | 1 | CAM-06 | T-04-17 | `GENERATED STORED` ustun kompozit FK nishoni bo'la oladimi — haqiqiy `postgres:18.4` da o'lchanadi (D-23) | tenancy | `pytest tests/tenancy/test_billable_anchor_probe.py -q` | yangi | ⬜ pending |
| 04-01/T3 | 04-01 | 1 | CAM-05 | T-04-06, T-04-07, T-04-08 | Besh jadval reyestrlari va kaskad tartibi migratsiyadan oldin; `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi (darvoza **yashil** qoladi); `markets.timezone` invarianti; `ix_capture_runs_overdue` istisnosi | tenancy | `pytest tests/tenancy/test_meta.py tests/integration/test_market_delete_guard.py -q` | mavjud (kengaytiriladi) | ⬜ pending |
| 04-02/T1 | 04-02 | 1 | CAM-06 | T-04-09 | Sintetik kadr fizik xususiyat bilan yasaladi (`mean`/`stddev`/to'yinganlik), determinstik va JPEG tolerans kodda | unit | `pytest tests/unit/test_frame_fixtures.py -q` | yangi | ⬜ pending |
| 04-02/T2 | 04-02 | 1 | CAM-06 | T-04-10, T-04-13 | Sim buzuq/kesilgan/bo'sh/HTML javobni buyurtma bilan beradi; noma'lum `frame_mode` rad etiladi; yangi rekvizit qo'shilmaydi | integration (`sim`) + unit | `pytest tests/integration/test_nvr_sim.py tests/unit/test_compose_sim_env.py -q` | mavjud (kengaytiriladi) | ⬜ pending |
| 04-02/T3 | 04-02 | 1 | CAM-04, FOUND-06 | T-04-11, T-04-12, T-04-14, T-04-15 | G-1…G-4, G-10 darvozalari; `IR`/`Telegram` override; `ъ` ning ikki ma'nosi; hedging ikkala reyestrda | node gate | `node --test frontend/scripts/snapshot-copy.test.mjs frontend/scripts/gen-cyrillic.test.mjs frontend/scripts/error-codes.test.mjs frontend/scripts/nvr-copy.test.mjs` | yangi + mavjud | ⬜ pending |
| 04-03/T1 | 04-03 | 2 | CAM-04, CAM-05, CAM-06 | T-04-17, T-04-18 | Beshta model, kompozit FK va `UNIQUE (id, is_billable)`; `business_date` `scheduled_at` dan; indeks nomlari enum'dan hosila | unit (metadata) | `pytest tests/unit/test_enums.py -q` + `mypy packages` | yangi | ⬜ pending |
| 04-03/T2 | 04-03 | 2 | CAM-04, CAM-05, CAM-06, CAM-07 | T-04-18, T-04-19, T-04-21, T-04-22 | RLS+policy beshta jadvalda; audit trigger faqat ikkitasida va `PENDING_AUDIT_TRIGGERS` dan ikkala nom **o'chiriladi**; `EXCLUDE` va qisman indekslar; `downgrade()` ishlaydi | tenancy + migration | `npm run migrate && pytest tests/tenancy/test_meta.py -q` | yangi | ⬜ pending |
| 04-03/T3 | 04-03 | 2 | CAM-04, CAM-05, FOUND-06 | T-04-16, T-04-20 | Kaskad besh jadvalni qamraydi; `capture_due_markets()` faqat identifikator beradi; standart 7 slotli profil avtomatik | tenancy + integration | `pytest tests/tenancy/test_snapshot_domain_meta.py tests/integration/test_market_delete_guard.py -q` | yangi | ⬜ pending |
| 04-04/T1 | 04-04 | 2 | CAM-07, FOUND-06 | T-04-28, T-04-29 | Sirlar `SecretStr`; bo'sh S3 kaliti ishga tushishda yiqitadi; `.env.example` ↔ `Settings` parity | unit | `pytest tests/unit/test_snapshot_settings.py -q` | yangi | ⬜ pending |
| 04-04/T2 | 04-04 | 2 | CAM-06 | T-04-24, T-04-25, T-04-26, T-04-31 | `dark` ikki shartli; kesilgan va HTML javob dekodsiz tutiladi; `LOAD_TRUNCATED_IMAGES is False`; `MAX_IMAGE_PIXELS` chegaralangan | unit | `pytest tests/unit/test_quality_filter.py -q` | yangi | ⬜ pending |
| 04-04/T3 | 04-04 | 2 | CAM-05, CAM-07 | T-04-27, T-04-30 | Kalit faqat UUID+ISO sana+`HHMM` dan (yo'l chiqishi mumkin emas); xato reyestri 11 kod, hosila to'plamlar metadan | unit | `pytest tests/unit/test_object_key.py tests/unit/test_capture_errors.py -q` | yangi | ⬜ pending |
| 04-05/T1 | 04-05 | 3 | CAM-05 | T-04-32, T-04-33, T-04-34, T-04-35, T-04-38 | `ensure_plan` idempotent; `SKIP LOCKED` parallelda kesishmaydi; lease qaytaradi; `grace` dan chiqqan `missed`; auth-locking darhol `failed` | integration | `pytest tests/integration/test_capture_repo.py -q` | yangi | ⬜ pending |
| 04-05/T2 | 04-05 | 3 | CAM-04 | T-04-19, T-04-32 | Davr bo'lish semantikasi; `bugun`/`ertaga` bitta so'rovda; qoplanmagan kunlar SQL'da; server chegarasi majburlanadi | integration | `pytest tests/integration/test_schedule_repo.py -q` | yangi | ⬜ pending |
| 04-05/T3 | 04-05 | 3 | CAM-06, CAM-07 | T-04-36, T-04-37 | `delete` metodi umuman yo'q; retention holat o'tishi bir yo'nalishli; sof modul ↔ enum pariteti | unit | `pytest tests/unit/test_quality_enum_parity.py -q` | yangi | ⬜ pending |
| 04-06/T1 | 04-06 | 3 | CAM-07 | T-04-40, T-04-41, T-04-42, T-04-44 | `StorageError` endpoint/imzo tashimaydi; `from None`; `create_bucket` yo'q; qo'lda SigV4 yo'q | static + type | `ruff check services/core-api && mypy services/core-api` | yangi | ⬜ pending |
| 04-06/T2 | 04-06 | 3 | CAM-07 | T-04-43, T-04-45, T-04-47 | Kalit tartibi, ustiga yozish idempotentligi va prefiks izolyatsiyasi HAQIQIY SeaweedFS da; mock yo'q | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_storage_layout.py -m sim -q` | yangi | ⬜ pending |
| 04-06/T3 | 04-06 | 3 | CAM-07 | T-04-46 | `orphan_keys` faqat kun prefiksini qabul qiladi; erkin prefiks `ValueError` | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_storage_layout.py -m sim -q` | yangi | ⬜ pending |
| 04-07/T1 | 04-07 | 4 | CAM-05 | T-04-49, T-04-52, T-04-53, T-04-56 | Uch usul bitta protokol ortida; `cache` va `remove_stream` yo'q; natijadan o'lchash; sir oqmaydi | unit (`respx`) | `pytest tests/unit/test_frame_source.py -q` | yangi | ⬜ pending |
| 04-07/T2 | 04-07 | 4 | CAM-05, CAM-06 | T-04-48, T-04-50, T-04-51, T-04-54, T-04-55 | Tik tenant kontekstini o'zi o'rnatadi; tartib kadr→sifat→S3→baza; auth-locking batchni to'xtatadi; job yiqilmaydi | static + type | `ruff check services/core-api && mypy services/core-api && grep -cE '^\s*(import|from)\s+taskiq' services/core-api/app/jobs/capture.py` | yangi | ⬜ pending |
| 04-07/T3 | 04-07 | 4 | CAM-05, CAM-06, CAM-07 | T-04-48, T-04-54, T-04-57 | Planer holatsiz; kontekstsiz tik 0 qator; dublikat yo'q; lease qaytaradi; buzuq kadr `is_billable=false` va FK rad etadi | integration (+`sim`) | `npm run sim:up && pytest tests/integration/test_capture_tick.py tests/integration/test_snapshot_quality.py -q` | yangi | ⬜ pending |
| 04-08/T1 | 04-08 | 5 | CAM-07 | T-04-64, T-04-66 | Siqish 90 kunni kutmasdan isbotlanadi; o'lchamlar saqlanadi; qator o'chirilmaydi; ikki marta siqish mumkin emas | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_retention.py -m sim -q` | yangi | ⬜ pending |
| 04-08/T2 | 04-08 | 5 | FOUND-06 | T-04-58, T-04-59, T-04-60 | `sendPhoto` funksiyasi umuman yo'q; token xato matnida yo'q; `send_message` istisno ko'tarmaydi | static + type | `ruff check . && mypy . && pytest tests/unit/test_logging.py -q` | yangi | ⬜ pending |
| 04-08/T3 | 04-08 | 5 | FOUND-06 | T-04-61, T-04-62, T-04-63, T-04-65 | 22 kameralik yiqilish bitta xabar; debounce va eskalatsiya `alert_events` da; bostirilmaydiganlar metadan; Telegram yiqilsa kadr olish davom etadi | integration (`respx`) | `pytest tests/integration/test_alerting.py -q` | yangi | ⬜ pending |
| 04-09/T1 | 04-09 | 5 | CAM-04 | T-04-70, T-04-75 | Huquq dekoratorda; `/today` bitta so'rovda; kesishuv 409; `object_key` DTO'da yo'q | integration | `pytest tests/integration/test_capture_schedule.py -q` | yangi | ⬜ pending |
| 04-09/T2 | 04-09 | 5 | CAM-06, CAM-07 | T-04-67, T-04-68, T-04-69, T-04-73, T-04-74 | Rasm faqat proxy orqali; presigned URL yo'q; `audit_read` yozuvi; `purged` da 410; alert yopish marshruti yo'q | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_snapshot_api.py -q` | yangi | ⬜ pending |
| 04-09/T3 | 04-09 | 5 | FOUND-06 | T-04-71, T-04-72 | `/internal/self-check` boshqa jarayondan heartbeat holatini beradi; javob yuzasi tor; konteyner healthcheck'i tegilmagan | integration + tenancy | `pytest tests/integration/test_capture_schedule.py -k self_check tests/tenancy/test_route_coverage.py -q` | yangi | ⬜ pending |
| 04-10/T1 | 04-10 | 6 | CAM-04 | T-04-79, T-04-80, T-04-81 | Kesh kalitlari `marketId` bilan doiralangan; global kalit yo'q; 11 kod uchun sabab↔tuzatish↔`actor` parity | node gate + i18n | `npm --prefix frontend run i18n:check && node --test frontend/scripts/error-codes.test.mjs frontend/scripts/snapshot-copy.test.mjs` | yangi | ⬜ pending |
| 04-10/T2 | 04-10 | 6 | CAM-04 | T-04-76, T-04-77 | «Ertaga» qatori doim; farq izohi `bg-warning/20`; `camera_manage` yo'q rolda tugmalar render bo'lmaydi; qoplanmagan kun ko'rinadi | component (vitest) | `npm --prefix frontend run test:component -- schedule-card` | yangi | ⬜ pending |
| 04-10/T3 | 04-10 | 6 | CAM-04 | T-04-78 | 12 lik chegara `aria-disabled` bilan; dublikat rad etiladi; oraliq to'ldirish qisman emas | component (vitest) | `npm --prefix frontend run test:component -- slot-editor` | yangi | ⬜ pending |
| 04-11/T1 | 04-11 | 7 | CAM-05 | T-04-89 | Oltala hisoblagich nol bilan birga (G-8); `planned === 0` da «0/0» chiqmaydi; foiz yo'q | component (vitest) | `npm --prefix frontend run test:component -- day-summary` | yangi | ⬜ pending |
| 04-11/T2 | 04-11 | 7 | CAM-05, CAM-06 | T-04-83, T-04-88 | `missed` hujayrasi bo'sh emas (G-7); `CircleSlash` ≠ `XCircle`; `role=grid` yo'q; bitta tab to'xtashi | component (vitest) + node gate | `npm --prefix frontend run test:component -- capture-cell capture-grid && node --test frontend/scripts/snapshot-copy.test.mjs` | yangi | ⬜ pending |
| 04-11/T3 | 04-11 | 7 | CAM-06, CAM-07, FOUND-06 | T-04-82, T-04-84, T-04-85, T-04-86, T-04-87 | `dark`+`ir_night` ≠ `dark`+`day`; `purged` halol ko'rsatiladi; ogohlantirishda rasm yo'q (G-3); `notified_at` yashirilmaydi | component (vitest) + node gate | `npm --prefix frontend run test:component -- snapshot-dialog alert-list && node --test frontend/scripts/snapshot-copy.test.mjs` | yangi | ⬜ pending |
| 04-12/T1 | 04-12 | 8 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-90, T-04-91, T-04-95 | Beshala mezon bitta buyruqda; meta-test mezon yo'qolishini tutadi; S3 mock'i to'silgan | integration (`sim`) | `npm run sim:up && pytest tests/integration/test_phase4_criteria.py -q` | yangi | ⬜ pending |
| 04-12/T2 | 04-12 | 8 | CAM-06, CAM-07, FOUND-06 | T-04-92, T-04-94 | Chegara olti o'lchov asosida; `nyquist_compliant` hisoblangan; qo'lda bandlar ega va tetik bilan | script gate | `node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md` | yangi | ⬜ pending |
| 04-12/T3 | 04-12 | 8 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | T-04-93 | Talab holatlari dalil bilan; ro'yxat ↔ Traceability parity; ROADMAP yakunlangan | script gate | `npm run requirements:check` | yangi | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Wave 0 bandlari → reja xaritasi** (`04-12` ularni `[x]` bilan belgilaydi):

| Band | Reja / task | Band | Reja / task |
|---|---|---|---|
| W0-1 | `04-01` / T2 | W0-7 | `04-01` / T3 |
| W0-2 | `04-01` / T1 | W0-8 | `04-01` / T3 |
| W0-3 | `04-01` / T1 | W0-9 | `04-02` / T1 |
| W0-4 | `04-01` / T1 | W0-10 | `04-02` / T2 |
| W0-5 | `04-01` / T3 | W0-11 | `04-01` / T1 (tasdiqlash) |
| W0-6 | `04-01` / T3 (muddat) + `04-03` / T3 (`0015`) | W0-F1…F7 | `04-02` / T2, T3 |

---

## Wave 0 Requirements

`04-PATTERNS.md` §5 o'n bir bandni sanaydi; `04-UI-SPEC.md` bittasini qo'shadi. **Uchtasi jimgina yiqiladigan turdagi** — testlar yashil bo'lgani holda ishlab chiqarish buziladi:

- [ ] **W0-1** — ⚠ **O'LCHOV:** `GENERATED STORED` ustun **kompozit FK nishoni** bo'la oladimi (`postgres:18.4`). `UNIQUE` tomoni allaqachon isbotlangan (`helpers.py:356-362` + `tests/fixtures/financial.py`), **FK-nishon tomoni emas**. Zond shabloni: `tests/fixtures/financial.py:59-145`. Yiqilsa `0014` trigger variantida yoziladi — **migratsiyadan keyin aniqlash qayta migratsiya demakdir** (D-23 / OQ-4).
- [ ] **W0-2** — 🔇 `aiobotocore==3.9.0` va `Pillow==12.3.0` ni `[project] dependencies` ga. **3-fazadagi `httpx` epizodining aynan takrori:** `dev` guruhida qolsa hamma test yashil, deploy'da `ModuleNotFoundError`. `tests/unit/test_runtime_deps.py` kengaytiriladi.
- [ ] **W0-3** — 🔇 `taskiq scheduler` ni `compose.yaml` ga + `npm run up` yorlig'ini yangilash. Planer profil ortida qolsa slotlar **hech qachon** materializatsiya bo'lmasdi **va hech qanday xato chiqmasdi**.
- [ ] **W0-4** — `storage` (SeaweedFS) xizmati + `ops/seaweedfs/s3.json.example`. `anonymous` yozuvining **yo'qligi** grep-darvoza bilan qulflanadi.
- [ ] **W0-5** — `AUDITED_TABLES` ga `snapshot_schedules`, `snapshot_schedule_slots`. Reyestr **migratsiyadan oldin** yoziladi va `test_audited_tables_have_trigger` vaqtincha qizil turadi — bu **kutilgan** (1-fazadagi `FINANCIAL_TABLES` naqshi).
- [ ] **W0-6** — 🔇 `market_delete_draft()` kaskadini beshta yangi jadval bilan kengaytirish + `0015` migratsiyasi. **3-fazadagi `0012`→`0013` juftligining aynan takrori:** kengaytirilmasa `0014` dan keyin bozor o'chirish FK buzilishi bilan yiqiladi. Tartib: `snapshots` → `capture_runs` → `snapshot_schedule_slots` → `snapshot_schedules`.
- [ ] **W0-7** — `tests/tenancy/test_meta.py` ga `markets.timezone = 'Asia/Tashkent'` invarianti. `scheduled_at` `markets.timezone` dan, `business_date` esa **literal**dan hisoblanadi — ikkinchi mintaqa qo'shilgan kuni test qizarsin, biznes-kun **jimgina siljimasin**.
- [ ] **W0-8** — `ix_capture_runs_overdue` uchun `INDEX_EXCEPTIONS` ga **sabab bilan** yozuv. Watchdog barcha bozorlar ustidan yuradi, indeks `market_id` bilan boshlanmaydi.
- [ ] **W0-9** — `tests/fixtures/frames.py`: sintetik JPEG generatori (`mean`/`stddev`/to'yinganlik bo'yicha). Fixture nomlari **fizik xususiyat** bilan (`frame_mean_8_stddev_2`), detektor chegarasi bilan **emas** — aks holda test o'z chegarasini tasdiqlaydi.
- [ ] **W0-10** — `nvr-sim` ga `frame_mode` + `/Streaming/channels/{ch}/picture`; `mediamtx.yml` ga sifat yo'llari. **Buzuq kadrni MediaMTX bera olmaydi** — u yaroqli oqim beradi, ya'ni baytlarni sim boshqarishi shart.
- [ ] **W0-11** — Markerlarni **tasdiqlash** (`tenancy`, `sim`, `hardware`, `slow` yetadi). Yangi marker qo'shilmaydi; `--strict-markers` tufayli e'lon qilinmagan marker yig'ilishda yiqiladi.
- [ ] **W0-F7** — ⚠ **Rejalararo darvoza to'qnashuvi.** 3-fazaning G-3 darvozasi hedge so'zi **aynan bitta** `errorCause.*` kalitida bo'lishini talab qiladi. 4-fazaga u `capture_stream_limit` uchun ham qonuniy kerak (bir xil fizik sabab). Tegilmasa darvoza **birinchi kuniyoq qizaradi**. `HEDGED_KEYS` ikki kalitli allowlist'ga kengaytiriladi (`04-UI-SPEC.md` §11.11 Qoida 4).

🔇 = jimgina yiqiladigan (testlar yashil, ishlab chiqarish buzilgan)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Owner | Trigger |
|----------|-------------|------------|-------|---------|
| Sifat chegaralarini real Karmana kadrida sozlash | CAM-06 | Chegaralar hozir **LOW confidence** — real kadr yo'q. Sintetik JPEG generatori mexanizmni isbotlaydi, **qiymatni emas**. D-15 bo'yicha o'lchovlarning o'zi saqlanadi, ya'ni sozlash SQL bilan bo'ladi, qayta kadr olish bilan emas | Nazoratchi + ijrochi | Phase 0 real kadrlari kelganda |
| 90 kunlik saqlash siyosatining amalda ishlashi | CAM-07 | **Vaqtni kutib bo'lmaydi.** Test soatni siljitib mexanizmni isbotlaydi; siyosatning 90 kun davomida haqiqatan ishlashi faqat kalendar bilan tasdiqlanadi | Ops | Go-live + 90 kun |
| Tiklash mashqi (restore drill) | FOUND-07 (8-faza) | Backup'ni tiklash real ombor va real ma'lumot talab qiladi | Ops | Go-live'dan oldin, 8-fazada |
| Telegram alertining haqiqatan yetib borishi | FOUND-06 | Bot tokeni, chat id va tarmoq — CI'da yo'q. Soxta yashil test alert ishlayapti deb yolg'on ishonch berardi | Ops | Bot sozlanganda |
| Tashqi dead-man's switch | FOUND-06 / D-21 | v1 da **kod yozilmaydi** — URL sozlash yo'riqnomasi va ops bandi | Ops | VPS deploy'idan keyin |
| Real NVR'da sessiya chegarasining kadr olishga ta'siri | CAM-05 | Simulyator sessiya chegarasini modellashtirmaydi (3-faza tekshiruvida ochiq yozilgan). `max_concurrent=1` uni **bloklovchi emas**, faqat kechikish masalasi qiladi | Ops | Real NVR ulanganda |

> Bu bandlar **fazani bloklamaydi** (2026-08-01 self-service direktivasi). `nyquist_compliant` ularning bajarilganini emas, **shaklini** tekshiradigan skript bilan hisoblanadi — 2-fazadagi `scripts/check-validation-signoff.mjs` naqshi.

---

## Validation Sign-Off

- [ ] Har taskda `<automated>` verify yoki Wave 0 bog'liqligi bor
- [ ] Namuna uzluksizligi: ketma-ket 3 taskda avtomatik verify yo'qligi holati yo'q
- [ ] Wave 0 ning 12 bandi (11 + W0-F7) qoplangan; uchala 🔇 bandi **birinchi migratsiyadan oldin**
- [ ] W0-1 o'lchandi va `0014` ning shakli **o'lchov natijasiga qarab** tanlandi
- [ ] Watch-mode bayrog'i yo'q
- [ ] Sifat filtri sintetik kadrlar bilan **darvoza**, konventsiya emas (W0-9 + W0-10)
- [ ] To'lqin chegarasi 6 o'lchov asosida qayta belgilandi (jimgina qoldirilmadi)
- [ ] `nyquist_compliant: true` skript bilan **hisoblangan**, qo'lda yozilmagan

**Approval:** pending
