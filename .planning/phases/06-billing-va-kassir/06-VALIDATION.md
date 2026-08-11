---
phase: 6
slug: billing-va-kassir
status: complete
nyquist_compliant: false
wave_0_complete: true
created: 2026-08-10
updated: 2026-08-11
human_only_verifications:
  - item: Dalil kadrining nizoda O'QILISHI — rasm direktor uchun yetarli dalilmi
    why_not_automatable: Zanjir oxirigacha o'lchangan (daily_charges -> charge_evidence -> occupancy_events.snapshot_id -> GET /snapshots/{id}/image, 200 + image/jpeg + AYNAN o'sha baytlar, HAQIQIY SeaweedFS ustida). O'lchanmagani — INSON IDROKI: kadrda rasta ko'rinadimi, sotuvchi tanib oladimi, nizoda ishonch uyg'otadimi. Buni birorta test ayta olmaydi
    owner: Direktor + bozor admini
    trigger: Karmananing birinchi real kadrlari kelganda (Phase 0 artefakti)
  - item: Kassir oqimining REAL TELEFONDA bajariladiganligi
    why_not_automatable: ≤3 bosish DOM'dan HOSILA sanoq bilan o'lchangan (collect-session.test.tsx, expect(steps).toBe(3), 2 ham 4 ham qizil). Lekin jsdom BRAUZER EMAS: barmoq bilan tegish nishoni, klaviatura ekranni qoplashi, bir qo'lda ishlash va quyoshda ko'rinish faqat qurilmada ko'rinadi
    owner: Kassir
    trigger: Pilot tayyorgarligi haftasi — Karmana kassirining o'z telefonida
  - item: Ko'r deklaratsiyaning AMALIY ko'rligi
    why_not_automatable: Uch strukturaviy qatlam o'lchangan (sxemada system_* maydoni umuman e'lon qilinmagan, klientda z.strictObject, ekranda aynan uchta element) va GET /payments/recent oynasi serverda qat'iy beshta. O'lchanmagani TASHKILIY: kassir jamini qog'oz daftardan yoki o'z xotirasidan chiqarib olmasligi texnik shart emas
    owner: Direktor
    trigger: Parallel rejimning birinchi haftasi (hafta 13)
  - item: Sabab-kodlarning amalda TO'G'RI tanlanishi
    why_not_automatable: Reyestr yopiq (ReversalReason/AdjustmentReason, `other` a'zosi ATAYIN YO'Q) va uchala locale'da matni bor; 422 darvozasi HTTP bilan o'lchangan. O'lchanmagani — kassir «boshqa» yo'qligida qaysi sababni bosishi: bu inson kuzatuvi
    owner: Direktor + kassir
    trigger: Pilotning birinchi oyi (sabab taqsimoti hisobotdan ko'rinadi)
automated_replacements:
  - was: Kunni kutib ertalab hisobotga qarash — patta yozildimi
    now: docker compose --profile test run --rm tests pytest tests/integration/test_phase6_criteria.py -q — o'tmishdagi OCHIQ kunda day_close -> billing_close zanjiri; hisob AYNAN ikki rastada, summa tariffs qatoridan O'QIB solishtiriladi
  - was: Job'ni ikki marta qo'lda ishga tushirib dublikat paydo bo'lmaganini ko'zdan kechirish
    now: test_sc1_immutable_daily_charge_is_written_once — qayta yugurish charged=0, qiymatlar va created_at o'zgarmaydi, errors BO'SH va skipped_existing mavjud hisoblarni TANIYDI (oxirgi ikkisi S-1 sabotaji bilan tug'ildi)
  - was: Hisobni qo'lda tahrirlab ko'rish va rad etilishini kuzatish
    now: test_sc2_charge_reaches_evidence_and_cannot_be_edited — UPDATE/DELETE -> RaiseException; charge_adjustments INSERT o'tadi va audit_log da qator paydo bo'ladi
  - was: Kassir ekranini ochib bosishlarni SANAB chiqish
    now: npm --prefix frontend test — collect-session.test.tsx qadamni DOM'dan yig'adi ([data-collect-step]) va expect(steps).toBe(3); zanjirga ulangani test_sc4 da package.json::gate skani bilan o'lchanadi
  - was: Smenani yopib direktor hisobotida farqni ko'zdan kechirish
    now: test_sc5_idempotent_payment_reversal_and_blind_variance — variance FAQAT GET /shifts?day= da, IKKI YO'NALISHDA (-5 000 va +7 000, har xil kattalikda) va close javobida system_* umuman yo'q
  - was: Matritsaga yangi marshrut qo'shilganini qo'lda eslab yurish
    now: docker compose --profile test run --rm tests pytest tests/tenancy/test_route_coverage.py -q — MINIMUM_MATRIX_ROUTES o'lchangan son bilan (88 dan 80)
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> **Manba:** `06-RESEARCH.md` § `Validation Architecture` (852-satr) — bu fayl undan HOSILA, qayta yozilmaydi.

---

## Bu fazaning validatsiyasi 5-fazaning teskarisi — buni birinchi o'qing

5-fazada haqiqat YO'Q edi (oltin to'plam bo'sh, model aniqligi o'lchanmagan) va shuning uchun
validatsiya ikki qatlamga — «mexanika» va «aniqlik» — bo'lingan edi.

**Bu fazada haqiqat TO'LIQ MAVJUD** (CONTEXT.md D-01): pul miqdori aniq, tarif jadvalda,
bandlik `stall_slot_occupancy` da materializatsiya qilingan. Ya'ni:

> **Beshala mezon bugun mexanik isbotlanadi. «Hozir o'lchab bo'lmaydi» degan bandning bu
> fazada o'rni YO'Q.** Agar reja shunday band tug'dirsa — bu dizayn xatosi, tabiiy chegara emas.

`## Manual-Only Verifications` bo'limi shu sababdan **bo'sh bo'lishi kutiladi**. Unga qo'shilgan
har bir qator — sabab bilan asoslanishi va `06-HUMAN-UAT.md` ga ega hamda tetik bilan
yozilishi shart.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), testcontainers 4.15.0 + haqiqiy `postgres:18.4` (SQLite TAQIQ) |
| **Backend config** | `services/core-api/pyproject.toml` + `tests/conftest.py` — **mavjud**, o'rnatish kerak emas |
| **Frontend framework** | vitest (komponent, `.test.tsx`) + `node --test` (`frontend/scripts/*.test.mjs` — matn/katalog darvozalari) |
| **Quick run command** | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| **Full suite command** | `npm run test` + `npm run test:tenancy` |
| **Phase gate command** | `npm run gate` + `tests/integration/test_phase6_criteria.py` |
| **Estimated runtime** | `gate:fast` ~87 s (byudjet 180 s, **05-15 o'lchovi**) · `gate` ~1009 s (byudjet **1250 s**, **05-15 o'lchovi**) |

### ⛔ Byudjet — 6-FAZADA QAYTA O'LCHANMADI (ochiq band)

⛔ **Bu bo'lim 05-15 ning o'lchovini takrorlaydi, 6-fazanikini EMAS.** `06-14` da o'lchov
protokoli boshlandi va tugamadi:

| Qadam | Holat |
|---|---|
| Disk tekshiruvi (`C:` da ≥ 10 GB) | ✅ **15 GB bo'sh** (92 % to'la) — o'lchov sharti bajarildi |
| Tinch xost (begona konteynerlar to'xtatildi) | ✅ 8 ta konteyner to'xtatildi va **TIKLANDI** |
| 1-yugurish (sovuq) | ❌ **~33 % da uzildi** (transport xatosi), vaqt YOZILMADI |
| 2- va 3-yugurish | ❌ boshlanmadi |
| `gate:fast` nazorat o'lchovi | ❌ olinmadi |

⛔ **Shuning uchun byudjet O'ZGARTIRILMADI: `package.json` da ham, bu yerda ham hamon
1250 s.** Ikki joyda son BIR XIL, lekin u 05-15 da o'lchangan (1009 / 1004 / 983 s).
6-faza ~6 jadval, ~11 marshrut, ~15 komponent va ~10 test fayli qo'shdi — ya'ni
**zaxira (241 s) yetarli ekani TASDIQLANMAGAN**. Bu `/gsd-verify-work` uchun ochiq band.

**Qoida (05-15 W0-13 naqshi, o'zgarmadi):** o'lchov **tinch xostda**, **uch marta**
olinadi; oshsa yangi chegara = eng yomon o'lchov × 1,20 (50 ga yuqoriga yaxlitlanadi) va
u `package.json` dagi `//gate-budget` izohida **va** bu faylda BIR XIL qiymatda yoziladi.

⚠ **`C:` diski 92 % to'la (bo'sh 15 GB)** — Docker VHDX o'sha yerda.

---

## Sampling Rate

- **After every task commit:** `npm run gate:fast` — **max feedback latency 180 s**
- **After every plan wave:** `npm run test` + `npm run test:tenancy` (+ `gate` vaqtini o'lchash)
- **Before `/gsd-verify-work`:** `npm run gate` to'liq yashil VA `test_phase6_criteria.py` beshala mezoni
- **Max feedback latency:** 180 s

---

## Faza mezonlari → o'lchanadigan signal

> Fayl: `tests/integration/test_phase6_criteria.py` — `test_phase5_criteria.py` ning **shakli**:
> uchta mustaqil darvoza (mezon boshiga bitta test · meta-test · soxtalashtirishsiz o'lchov).

| # | ROADMAP mezoni | Test qatlami | Kerakli holat (fixture) | Kuzatiladigan signal |
|---|---|---|---|---|
| **SC#1** | Band rastaga to'liq kunlik patta; job qayta ishga tushsa ikkinchi hisob yo'q | integration (haqiqiy PG) | `billing_domain` seed: 3 rasta — (a) 2 slot AI-`occupied`, (b) 1 slot AI-`occupied`, (c) 1 slot `occupied` + `resolution_source='human'` | `billing_close(D)` → hisob **faqat** (a) va (c) da; `amount_soum == tariffs.amount_soum`. Keyin **qayta** `billing_close(D)` → qator soni o'zgarmaydi, `amount_soum` **va** `created_at` **ikkalasi ham** o'zgarmaydi (D-06) |
| **SC#2** | Har hisobdan dalilga o'tish mumkin; hisob o'zgarmas; tuzatish faqat `charge_adjustments` | integration | SC#1 ning (a) hisobi | `charge_evidence` da `occupancy_event_id` bor va u `occupancy_events.snapshot_id` orqali `GET /snapshots/{id}/image` ga yetadi. `UPDATE daily_charges SET amount_soum=1` → **`RaiseException`**; `DELETE` → **`RaiseException`**. `charge_adjustments` INSERT → o'tadi va `audit_log` da qator paydo bo'ladi |
| **SC#3** | Qarz faqat biriktirilgan sotuvchida; qoldiq hisoblanadigan; biriktirilmagan band rasta = anomaliya | integration | 2 rasta: biri biriktirilgan, biri `stall_assignments` bo'shlig'ida | Biriktirilgan → hisob + qoldiq; biriktirilmagan → `daily_charges` da **0 qator** VA `billing_anomalies(kind='unassigned_occupied')` da **1 qator**. `information_schema` da `daily_charges`/`vendors` da **`balance*` nomli ustun YO'Q** (to'plam tengligi) |
| **SC#4** | Kassir/direktor kutilayotgan pattani jonli ko'radi; ≤3 bosishda tasdiqlaydi; summani faqat sabab-kod bilan o'zgartiradi | integration + vitest | `GET /billing/pending` seed; komponent testida `apiFetch` mock'i | **(a)** proyeksiya javobida `charge_id` **umuman yo'q** (kalitlar to'plami tengligi); summa yagona funksiya bilan **bir xil** (ikki chaqiruv, bir natija — D-16); **(b)** vitest: sahifa ochilishidan muvaffaqiyatli `POST /payments` gacha **interaktiv hodisalar SANALADI** va `<= 3` (D-18, `review-session.test.tsx:403-429` naqshi); **(c)** sabab-kodsiz summa o'zgartirish → **422** |
| **SC#5** | Takror bosish dublikat bermaydi; tuzatish faqat storno; ko'r deklaratsiya + variance | integration + vitest + darvoza | ochiq smena, 1 to'lov | **(a)** bir xil `idempotency_key` bilan 2 `POST` → `payments` da **1 qator**, ikkinchi javob **200** va **o'sha `id`**; **(b)** 3 tez bosish → `apiFetch` **1 marta** (D-22); **(c)** `UPDATE payments` → `RaiseException`; storno → **yangi qator** `kind='reversal'` + `reason_code` majburiy; **(d)** `POST /shifts/{id}/close` javobi kalitlari to'plamida `system_*` **YO'Q**; variance **serverda** hisoblanadi va `declared > system` holatida ham qaytariladi |

---

## Meta-darvozalar (mezonlardan mustaqil)

| ID | Da'vo | Mexanizm |
|----|-------|----------|
| **G-1** | Beshala mezon o'lchanadi va birortasi jimgina tushib qolmaydi | `test_every_criterion_has_its_own_test()` — `test_phase5_criteria.py:1118` naqshi (modul funksiyalarini introspeksiya qiladi) |
| **G-2** | `daily_charges.service_date` ↔ `stall_slot_occupancy.business_date` semantik mos | Har yozilgan hisob uchun o'sha `(market_id, stall_id, service_date)` da kamida bitta `stall_slot_occupancy` qatori bor — **C-2 sinfidagi xatoni ushlaydi** |
| **G-3** | `float` billing modullarida yo'q | `information_schema.columns` da yangi jadvallar uchun `data_type` **to'plam tengligi** (`not in` EMAS) |
| **G-4** | Moliyaviy jadval qo'riqchilari o'rnida | mavjud `test_financial_tables_have_guards` (`test_meta.py:1313`) — jadval tug'ilgan kuni **o'zi** ishga tushadi |
| **G-5** | Yangi marshrutlar tenant matritsasida | mavjud `test_route_coverage.py` + `MINIMUM_MATRIX_ROUTES` **ko'tariladi** |
| **G-6** | D-04 predikati `human_confirmed` dan **ajraladi** | Uch holat: (1) 2 AI-`occupied` → hisob; (2) 1 AI-`occupied` + boshqa slotda `('empty','human')` → **hisob YO'Q**; (3) 1 `('occupied','human')` → hisob. **Sabotaj:** predikatni `_PER_STALL_CTE.human_confirmed` ga almashtirish → **(2) qizarishi SHART** (C-6) |
| **G-7** | Ko'r deklaratsiya serializatori | `ShiftCloseResponse` maydonlari **to'plam tengligi**; `frontend/scripts/` darvozasi `components/collect/**` katalogini **hosila** ravishda skanerlaydi |
| **G-8** | RBAC ikki tilda mos | mavjud `frontend/scripts/role-gate.test.mjs` — `rbac.py` **va** `rbac.ts` ni matn sifatida o'qiydi |
| **G-9** | Yangi `AuditAction`/xato kodlari uchala tilda | mavjud `audit-actions.test.mjs`, `error-codes.test.mjs` + `i18n:check` |
| **G-10** | Orfan `SECURITY DEFINER` funksiyalar hal qilindi | `DEFINER_SURFACES` (`test_occupancy_domain_meta.py:75-79`) to'plami `0020` dan keyin **bo'sh** (yoki qolgani sabab bilan) — ikki tomonlama qulf |
| **G-11** | Kaskad yangi jadvallarni qamraydi | mavjud `test_market_delete_guard.py::test_cascade_covers_every_table_referencing_markets` — `0020` dan keyin **o'zi qizaradi**, `0021` uni yashil qiladi |
| **G-12** | Idempotentlik parallel yozuvda ham ishlaydi | **Wave 0 zondi**: ikki `asyncio` sessiya bir xil kalit bilan; natija 1 qator + bir xil `id` |
| **G-13** | **D-24 ning savoliga javob TASDIQ, proza emas** — bitta to'lov N kunlik qarzni yopganda ham «qaysi kunning pattasi to'landi?» aniq | ⛔ Ikki qatlam: (a) jadval testi `tests/unit/test_payment_credit_rules.py` — `FIFO_OLDEST_SERVICE_DATE_FIRST` qoidasi (bir to'lov N kunga, qisman, avans, storno, bir kunda ikki rasta + kirish tartibidan **mustaqillik**); (b) integratsiya `tests/integration/test_billing_repo.py::vendor_charge_allocation` — uch kunlik qarz + **bitta** 45 000 to'lov → yopilgan kunlar ⛔ **AYNAN `[D-2, D-1, D]`**. ⛔ **Sabotaj:** tartib LIFO ga almashtiriladi → ikkala holat **qizarishi shart**. ⛔ Taqsimlash **saqlanmaydi**: `payment_allocations` jadvali va `allocated_*` ustuni **yo'q** (D-07, BILL-03) |
| **G-14** | **Hosila taqsimlash hisoblanadigan qoldiqdan AJRALIB KETA OLMAYDI** | `Σ unpaid_soum` (FIFO ko'rinish) ⛔ **`vendor_outstanding()[vendor_id]` ga TENG** (avans bo'lmagan holatda) — integratsiya testida arifmetik solishtirish; belgili to'lov ifodasi **bitta** `text()` konstantasi va ikkala funksiya **shuni** ishlatadi |
| **G-15** | **«Summa yo'q» qarzni undirilmaydigan QILMAYDI** (UI-SPEC §9.4) | `POST /payments`: (a) `market_closed` + `outstanding > 0` → ⛔ **201**; (b) `tariff_missing` + `outstanding > 0` → **201**; (c) qarz ham `<= 0` → **422** va `detail` da ⛔ **nomlangan sabab** (`market_closed`/`tariff_missing`). ⛔ **Sabotaj:** eski shart (`amount_soum is None` → 422) qaytariladi → (a) va (b) **qizarishi shart**. ⛔ 422 ning sharti — `payment_quote_set() == ()`, «bugungi summa yo'q» **emas** |
| **G-16** | **Biriktirilmagan rasta uchun BITTA aniq javob** | `POST /payments` → ⛔ **409 `stall_not_assigned`** (404 **emas**, 422 **emas**), `payments` da **0 qator**; ⛔ **nazorat**: biriktirish qo'shilgach o'sha so'rov → **201** (409 **holatdan**, kod xatosidan emas). Kod 06-02 ning **14 kodli** reyestrida tug'iladi — 06-09 reyestrga **tegmaydi** (D-28) |

---

## Per-Task Verification Map

> 14 rejaning **42** vazifasi. Manba — rejalarning `<verify><automated>` bloklari va
> `<threat_model>` jadvallari. `Automated Command` ustuni **qisqartirilgan**, lekin har biri
> AYNAN o'sha rejadagi buyruq (uzun zanjirlar `…` bilan kesilgan — to'liq matni rejada).
> ⛔ Bo'sh `Automated Command` **yo'q**: 42 qatorning har birida buyruq bor.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 06-01 | 1 | CASH-03 | T-06-01 | Parallel `get-or-create` bir qator + bir xil `id` | tenancy (real PG) | `pytest tests/tenancy/test_idempotency_concurrency.py -q` | ✅ | ✅ |
| 06-01-T2 | 06-01 | 1 | BILL-01 | T-06-02 | `GENERATED ALWAYS AS (<oddiy ustun>) STORED` zondi | tenancy | `pytest tests/tenancy/test_generated_from_column_probe.py -q` | ✅ | ✅ |
| 06-01-T3 | 06-01 | 1 | BILL-01, BILL-03, CASH-04 | T-06-03, T-06-04 | D-04 predikati, belgili variance, FIFO qoidasi — SOF funksiyalar | unit (jadval testi) | `pytest tests/unit/test_billable_from_slots.py tests/unit/test_variance.py tests/unit/test_payment_credit_rules.py -q` | ✅ | ✅ |
| 06-02-T1 | 06-02 | 1 | CASH-01, CASH-02 | T-06-05, T-06-06 | Ikki yangi huquq; shaxsiy maydon yuzasi o'smaydi | unit + tenancy | `pytest tests/unit/test_rbac_matrix.py tests/tenancy/test_personal_data_coverage.py -q` | ✅ | ✅ |
| 06-02-T2 | 06-02 | 1 | BILL-04, CASH-03 | T-06-07, T-06-08 | Yetti domen enumi ↔ frontend ko'zgusi; audit amali | node --test + i18n | `node --test frontend/scripts/billing-copy.test.mjs frontend/scripts/audit-actions.test.mjs && npm --prefix frontend run i18n:check` | ✅ | ✅ |
| 06-02-T3 | 06-02 | 1 | BILL-05, CASH-01 | T-06-09 | 14 xato kodi uchala locale'da sabab+yechim bilan | node --test + i18n | `node --test frontend/scripts/error-codes.test.mjs && npm --prefix frontend run i18n:check` | ✅ | ✅ |
| 06-03-T1 | 06-03 | 1 | BILL-05 | T-06-10, T-06-11 | `z.strictObject` klient kontrakti (proyeksiya/hisob) | typecheck + lint | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ |
| 06-03-T2 | 06-03 | 1 | CASH-03, CASH-04 | T-06-12, T-06-13 | To'lov va KO'R smena kontrakti klientda ham qulflangan | typecheck + lint | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ |
| 06-03-T3 | 06-03 | 1 | CASH-04 | T-06-14 | G-7 frontend yarmi — katalogdan HOSILA skan | node --test + vitest | `node --test frontend/scripts/collect-surface.test.mjs && npm --prefix frontend test` | ✅ | ✅ |
| 06-04-T1 | 06-04 | 2 | BILL-01, BILL-02 | T-06-15, T-06-16 | Olti model + `AUDITED_TABLES`; yetishmagan UNIQUE | unit + lint | `pytest tests/unit -q && ruff check . && mypy .` | ✅ | ✅ |
| 06-04-T2 | 06-04 | 2 | BILL-02, CASH-03 | T-06-17…T-06-21 | Uch o'zgarmaslik qo'riqchisi (`0020`), orfan DEFINER DROP | migration + tenancy | `alembic upgrade head && pytest tests/tenancy -q` | ✅ | ✅ |
| 06-04-T3 | 06-04 | 2 | BILL-03, BILL-04 | T-06-22…T-06-24 | `0021` kaskad olti jadvalni qamraydi | migration + integration | `alembic upgrade head && pytest tests/integration/test_market_delete_guard.py -q` | ✅ | ✅ |
| 06-05-T1 | 06-05 | 3 | BILL-01 | T-06-25 | Seed slotlarni `day_close` ORQALI yozadi (C-3) | fixture + integration | `pytest tests/fixtures -q --collect-only && pytest tests/integration/test_billing_close.py -q` | ✅ | ✅ |
| 06-05-T2 | 06-05 | 3 | BILL-01, BILL-02 | T-06-26, T-06-27 | Sxema invariantlari `pg_catalog` dan | tenancy (meta) | `pytest tests/tenancy/test_billing_domain_meta.py -q` | ✅ | ✅ |
| 06-05-T3 | 06-05 | 3 | CASH-03, CASH-04 | T-06-28, T-06-29 | O'zgarmaslikning XULQIY darvozasi (D-07/23/25/27) | integration (real PG) | `pytest tests/integration/test_billing_immutable.py -q` | ✅ | ✅ |
| 06-06-T1 | 06-06 | 4 | BILL-05 | T-06-30, T-06-31 | YAGONA pul yechimi; juftlangan invariant | integration + lint | `ruff check . && mypy . && pytest tests/integration/test_billing_repo.py -q` | ✅ | ✅ |
| 06-06-T2 | 06-06 | 4 | BILL-01, BILL-02, BILL-04 | T-06-32…T-06-34 | Hisob yozish, MUZLATILGAN dalil, uch anomaliya | integration | `pytest tests/integration/test_billing_repo.py -q` | ✅ | ✅ |
| 06-06-T3 | 06-06 | 4 | BILL-03, BILL-05 | T-06-35, T-06-36 | Hisoblanadigan qoldiq + proyeksiya; G-6 | integration | `pytest tests/integration/test_billing_repo.py -q` | ✅ | ✅ |
| 06-07-T1 | 06-07 | 5 | BILL-01 | T-06-37, T-06-38 | Argumentli, konvergent, YIQILMAYDIGAN job | integration | `pytest tests/integration/test_billing_close.py -q` | ✅ | ✅ |
| 06-07-T2 | 06-07 | 5 | BILL-01 | T-06-39, T-06-40 | Cron `day_close` DAN KEYIN; Pitfall 2 ketma-ketligi | integration + unit | `pytest tests/integration/test_billing_close.py tests/unit/test_scheduler_observability.py -q` | ✅ | ✅ |
| 06-07-T3 | 06-07 | 5 | BILL-01, BILL-04 | T-06-41, T-06-42 | Yurak urishining YO'QLIGI ko'rinadi (M-C) | integration | `pytest tests/integration/test_alerting.py -q` | ✅ | ✅ |
| 06-08-T1 | 06-08 | 5 | BILL-02, BILL-03 | T-06-43, T-06-44 | Shaxsiy maydon yuzasi o'smadi (C-10) | tenancy + lint | `ruff check . && mypy . && pytest tests/tenancy/test_personal_data_coverage.py -q` | ✅ | ✅ |
| 06-08-T2 | 06-08 | 5 | BILL-05 | T-06-45, T-06-46 | `charge_id` proyeksiyada YO'Q; nol-natija sanoqlari | integration | `pytest tests/integration/test_billing_api.py tests/tenancy/test_route_coverage.py -q` | ✅ | ✅ |
| 06-08-T3 | 06-08 | 5 | BILL-04 | T-06-47, T-06-48 | Tenant matritsasi + YANGI 422 darvozasi | tenancy | `pytest tests/tenancy/test_cross_tenant.py tests/tenancy/test_route_coverage.py tests/integration/test_billing_api.py -q` | ✅ | ✅ |
| 06-09-T1 | 06-09 | 6 | CASH-03 | T-06-49…T-06-51 | Ikki bayonotli get-or-create, fingerprint, storno | integration | `pytest tests/integration/test_payments_api.py -q -k "idempoten or reverse"` | ✅ | ✅ |
| 06-09-T2 | 06-09 | 6 | CASH-01, CASH-02 | T-06-52…T-06-54 | 200/201/409/422 va CASH-02 auditi | integration | `pytest tests/integration/test_payments_api.py tests/tenancy/test_route_coverage.py -q` | ✅ | ✅ |
| 06-09-T3 | 06-09 | 6 | CASH-03 | T-06-55…T-06-57 | `CASHIER_ROUTES`, SC#5(a)/(c) darvozalari | tenancy + integration | `pytest tests/integration/test_payments_api.py tests/tenancy/test_cross_tenant.py -q` | ✅ | ✅ |
| 06-10-T1 | 06-10 | 7 | CASH-04 | T-06-58, T-06-59 | Smena ochish/yopish, tizim summasi SERVERDA | integration | `pytest tests/integration/test_shifts_api.py -q -k "open or close"` | ✅ | ✅ |
| 06-10-T2 | 06-10 | 7 | CASH-04 | T-06-60…T-06-62 | KO'R serializator — `system_*` E'LON QILINMAGAN | integration | `pytest tests/integration/test_shifts_api.py tests/tenancy/test_route_coverage.py -q` | ✅ | ✅ |
| 06-10-T3 | 06-10 | 7 | CASH-04 | T-06-63…T-06-65 | SC#5(d) IKKI TOMONLAMA variance | integration + tenancy | `pytest tests/integration/test_shifts_api.py tests/tenancy/test_cross_tenant.py -q` | ✅ | ✅ |
| 06-11-T1 | 06-11 | 8 | BILL-05 | T-06-66, T-06-67 | `/collect` sahifasi, ommaviy amal yuzasi NOL | vitest + node --test | `npm --prefix frontend run test:component -- pending-card && node --test frontend/scripts/bulk-action-surface.test.mjs` | ✅ | ✅ |
| 06-11-T2 | 06-11 | 8 | CASH-01, CASH-03 | T-06-68…T-06-70 | ⛔ G-20 (≤3 qadam) va G-21 (`useRef` qulfi) | vitest | `npm --prefix frontend run test:component -- collect-session payment-bar` | ✅ | ✅ |
| 06-11-T3 | 06-11 | 8 | CASH-02, CASH-03 | T-06-71…T-06-73 | DL-1/DL-2 dialoglari HAQIQATAN chiziladi | vitest + node --test | `npm --prefix frontend run test:component -- reason-dialog && node --test frontend/scripts/collect-surface.test.mjs` | ✅ | ✅ |
| 06-12-T1 | 06-12 | 9 | CASH-04 | T-06-74, T-06-75 | §10.1 IKKI holat, uchinchisi yo'q (D-27) | typecheck + lint | `npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ |
| 06-12-T2 | 06-12 | 9 | CASH-04 | T-06-76, T-06-77 | KO'R naqd deklaratsiyasi — EKRAN qatlami | node --test + lint | `node --test frontend/scripts/collect-surface.test.mjs && npm --prefix frontend run typecheck && npm --prefix frontend run lint` | ✅ | ✅ |
| 06-12-T3 | 06-12 | 9 | CASH-04 | T-06-78, T-06-79 | G-23(b): yopilgandan keyin AYNAN uchta narsa | vitest | `npm --prefix frontend test` | ✅ | ✅ |
| 06-13-T1 | 06-13 | 9 | BILL-02 | T-06-80, T-06-81 | Kun tanlagichi + §11.2; ommaviy amal yuzasi NOL | vitest + node --test | `npm --prefix frontend run test:component -- billing/day-picker && node --test frontend/scripts/bulk-action-surface.test.mjs` | ✅ | ✅ |
| 06-13-T2 | 06-13 | 9 | BILL-02, BILL-03 | T-06-82…T-06-84 | DL-3 dalil dialogi va G-28 | vitest + typecheck | `npm --prefix frontend run test:component -- charge-detail-dialog && npm --prefix frontend run typecheck` | ✅ | ✅ |
| 06-13-T3 | 06-13 | 9 | BILL-04, CASH-04 | T-06-85…T-06-87 | Anomaliya + variance ro'yxatlari SAHIFAGA ULANGAN | vitest | `npm --prefix frontend run test:component -- billing/page variance-list && npm --prefix frontend test` | ✅ | ✅ |
| 06-14-T1 | 06-14 | 10 | BILL-01…05, CASH-01…04 | T-06-88, T-06-89 | Beshta mezon + uchta meta-darvoza BITTA buyruqda | integration (real PG + ombor) | `pytest tests/integration/test_phase6_criteria.py -q` | ✅ | ✅ |
| 06-14-T2 | 06-14 | 10 | BILL-01…05, CASH-01…04 | T-06-90…T-06-92, T-06-94 | Beshta sabotaj o'lchandi; matritsa chegarasi o'lchangan son bilan | tenancy + o'lchov | `pytest tests/tenancy/test_route_coverage.py -q` | ✅ | ✅ |
| 06-14-T3 | 06-14 | 10 | BILL-01…05, CASH-01…04 | T-06-93 | Talab belgisi DALIL bilan; ro'yxat↔jadval mexanik qulflangan | script + gate | `node scripts/check-requirements-sync.mjs && npm run gate` | ✅ | ✅ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

⚠ **`T-06-SC` (npm/pip o'rnatish) HAR REJADA `accept`** va u shu jadvalga qator sifatida
kirmaydi: faza davomida BIRORTA yangi paket o'rnatilmadi — `package.json`,
`frontend/package.json` va `pyproject.toml` fayllarining `dependencies` bloklari
6-fazada **o'zgarmadi**.

---

## Wave 0 Requirements

**Ikkitasi ZOND** — javobi noma'lum va rejaning shakliga ta'sir qiladi, shuning uchun
boshqa hamma ishdan oldin o'lchanadi:

- [x] **A1 ZOND** — `tests/tenancy/test_idempotency_concurrency.py`: haqiqiy PG, ikki parallel `asyncio` sessiya bir xil `idempotency_key` bilan. `ON CONFLICT DO NOTHING ... RETURNING` konfliktda qator **qaytarmaydi** → majburiy alohida `SELECT`; READ COMMITTED ostidagi oyna **o'lchanmagan** (G-12)
- [x] **A2 ZOND** — `tests/tenancy/test_generated_from_column_probe.py`: PG 18 da `GENERATED ALWAYS AS (<plain column>) STORED` ruxsat etiladimi (C-2 ning ikkinchi variantiga kerak)
- [x] `tests/fixtures/billing_domain.py` — 6 jadval seed'i (`fixtures/occupancy_domain.py` naqshi). ⚠ `stall_slot_occupancy` qatorlari **`day_close` orqali** yoziladi, qo'lda `INSERT` EMAS — aks holda C-3 sinfidagi xato testda **ko'rinmaydi**
- [x] `tests/integration/test_phase6_criteria.py` — beshta mezon + meta-test + G-2/G-3/G-6
- [x] `tests/tenancy/test_billing_domain_meta.py` — sxema konstraytlari (`test_occupancy_domain_meta.py` naqshi)
- [x] `frontend/scripts/collect-surface.test.mjs` — G-7 (ko'r deklaratsiya + ommaviy amal yo'qligi), **katalogdan hosila**
- [x] `frontend/src/components/collect/*.test.tsx` — bosish sanog'i (SC#4b), `useRef` qulfi (SC#5b)
- [x] `tests/unit/test_billable_from_slots.py` + `tests/unit/test_variance.py` — sof funksiyalar, **jadval testi** (`test_aggregate_stall_slot.py` naqshi), bitta holat emas
- [x] ⛔ `tests/unit/test_payment_credit_rules.py` — **G-13/G-14 ning birinchi qatlami**: `allocate_charge_credit()` (⛔ `FIFO_OLDEST_SERVICE_DATE_FIRST`), `payment_quote_set()` va `total_due_soum()` uchun ⛔ **uch mustaqil jadval** (`FIFO_ALLOCATION_TABLE` ≥ 9 qator, `EXPECTED_BY_TOTALS`, `QUOTE_SET_TABLE` ≥ 7 qator) + uchala uchun `test_the_*_table_covers_every_case()`. ⛔ **Bitta holat EMAS** — D-24 ning javobi shu jadvalda yashaydi
- [x] Framework install — **kerak emas**, hammasi mavjud

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _(BO'SH — va bu FAZANING NATIJASI, unutilgan band emas)_ | | | |

⛔ **JADVAL BO'SH QOLDI (2026-08-11, `06-14` yakunida).** D-01 bandi bajarildi: to'qqizala
talabning ham har jumlasi CI'da real artefakt bilan o'lchanadi (HAQIQIY `postgres:18.4`,
HAQIQIY SeaweedFS, HAQIQIY marshrut grafi) va beshala ROADMAP mezoni **bitta buyruqda**
yashil. ⛔ Shu sababdan `06-HUMAN-UAT.md` fayli **YARATILMADI** — 3- va 5-fazadan farqli
o'laroq bu fazada egasi/tetigi kutilayotgan band **yo'q**.

⚠ **«O'lchanMAGAN» narsalar BOR, lekin ular talab MATNINING jumlalari EMAS** va shuning
uchun bu jadvalga tushmaydi: inson idroki (dalil kadrining nizoda o'qilishi), real qurilma
(«telefonda» — jsdom brauzer emas) va tashkiliy shart (kassir jamini boshqa yo'ldan
chiqarib olmasligi). Har biri `.planning/REQUIREMENTS.md` § «Qoidaning 6-fazadagi
qo'llanishi» jadvalining oxirgi ustunida NOMMA-NOM yozilgan.

⚠ **Bu jadvalga qo'shilgan har qator dizayn xatosi gumoni bilan qaraladi.** Qo'shilsa —
sabab, ega va tetik bilan `06-HUMAN-UAT.md` ga ham yoziladi.

⚠ Ochiq buyurtmachi savollari (OQ-3/OQ-4/OQ-6/OQ-7) **manual verification EMAS** — ular
`[ASSUMED]` standart qiymat bilan qurilib, javob kelganda sozlanadigan **parametr**.

⛔ **D-24 uchun «hujjatlashtirilgan qurbonlik» BANDI YO'Q va bu ataylab.** `06-RESEARCH.md`
§C-4 `payments.charge_id` ni imkonsiz deb o'lchagan, lekin uning tavsiyasi
(`service_date`) «qaysi kunning pattasi to'landi?» savoliga faqat **shu kunning o'zi**
to'langan holatda javob berardi. Per-kun izchillikni **yo'qotib qo'yish** (uchinchi
variant: semantik test + yozma qabul) ⛔ **rad etildi**, chunki u D-02 ning
(«nizoda qaysi yozuv dalil?») o'z shartiga qarshi bo'lardi va yo'qotish **arzon
qochib bo'ladigan** edi. Tanlangan yechim — **hosila FIFO ko'rinish** (G-13/G-14):
yangi jadval **yo'q**, saqlangan balans **yo'q**, javob **tasdiq**. Ya'ni bu jadvalga
ham, `06-HUMAN-UAT.md` ga ham qator **qo'shilmaydi**.

---

## Validation Sign-Off

⛔ **`nyquist_compliant` KELISHUV EMAS, HISOB-KITOB** (02-23 darsi). Har band uchun
DALIL ko'rsatiladi — «ha» deb belgilash yetarli emas.

- [x] **All tasks have `<automated>` verify or Wave 0 dependencies** — dalil: yuqoridagi
      `## Per-Task Verification Map` da **42 qator**, har birida bo'sh bo'lmagan
      `Automated Command`. 14 reja × 3 vazifa = 42, ya'ni qamrov TO'LIQ.
- [x] **Sampling continuity: no 3 consecutive tasks without automated verify** — dalil:
      ketma-ket 0 ta vazifa `<automated>` siz (yuqoridagi jadvalda bo'sh katak YO'Q),
      ya'ni eng uzun «jim» oraliq = 0.
- [x] **Wave 0 covers all MISSING references (A1 va A2 zondlari BAJARILDI)** — dalil:
      `tests/tenancy/test_idempotency_concurrency.py` va
      `tests/tenancy/test_generated_from_column_probe.py` mavjud va yashil; qolgan
      to'qqiz band ham `## Wave 0 Requirements` da `[x]`.
- [x] **No watch-mode flags** — dalil: `package.json` va `frontend/package.json` ning
      birorta skriptida `--watch` yo'q; `vitest run` (interaktiv emas), `node --test`
      (bir marta yuguradi), `pytest` (standart).
- [x] **Feedback latency < 180 s** — dalil: `gate:fast` byudjeti **180 s** va u
      `//gate-fast-budget` izohida qulflangan. ⚠ 6-fazada `gate:fast` QAYTA
      O'LCHANMADI (pastdagi ⛔ bandga qarang), ya'ni bu band OLDINGI o'lchovga
      (87 s, 05-15) tayanadi.
- [ ] ⛔ **`gate` byudjeti o'lchandi va `package.json` bilan bu fayl BIR XIL qiymatda**
      — ⛔ **BAJARILMADI.** O'lchov BOSHLANDI (tinch xost tayyorlandi, disk
      tekshirildi) va **~33 % da uzildi**; uchala yugurishning birortasi ham
      tugamadi. Byudjet shu sababdan **O'ZGARTIRILMADI**: `package.json` da ham,
      bu faylda ham hamon **1250 s** (ikki joyda BIR XIL, lekin bu 05-15 ning
      o'lchovi, 6-fazaniki EMAS). Tafsilot `06-14-SUMMARY.md` § «Byudjet» da.
- [ ] ⛔ **`nyquist_compliant: true` set in frontmatter** — ⛔ **QO'YILMADI va bu
      QAROR, unutish emas.** `node scripts/check-validation-signoff.mjs` bayroqni
      HISOB-KITOB bilan solishtiradi va uning (2)-qoidasi ochiq: byudjet bandi
      hamon `BAJARILMADI`. Bandni `human_only_verifications` ga ko'chirish
      ⛔ **YOLG'ON** bo'lardi — u avtomatlashtirilmaydigan emas, shunchaki
      **yugurtirilmagan** (`npm run gate`). Skript bugun `nyquist_compliant:
      false — hisob-kitob bilan MOS` deydi va aynan shu javob to'g'ri.

**Approval:** ⚠ **shartli** — yettitadan **beshtasi** dalil bilan yopildi; `gate`
byudjeti va undan HOSILA bo'lgan `nyquist_compliant` bandlari OCHIQ va ikkalasi ham
`06-14-SUMMARY.md` § «Byudjet» da yozilgan. ⛔ Ularni «yashil» deb belgilash
byudjetning JIMGINA ko'tarilishi bilan bir xil sinfdagi yolg'on bo'lardi (T-06-92).

⛔ **YOPISH YO'LI BIR QADAMLIK VA U QURILGAN:** tinch xostda `npm run gate` uch marta
yugurtiriladi; oshmasa byudjet o'zgarmaydi va bu ikki band `[x]` bo'ladi, oshsa
yangi chegara `package.json` va bu faylda BIR XIL qiymatda yoziladi.

---
*Phase: 06-billing-va-kassir*
*Derived from: 06-RESEARCH.md § Validation Architecture (2026-08-10)*
