---
phase: 6
slug: billing-va-kassir
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
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
| **Estimated runtime** | `gate:fast` ~87 s (byudjet 180 s) · `gate` ~1009 s (byudjet **1250 s**) |

### ⚠ Byudjet xavfi — birinchi darajali

`gate` byudjeti bugun **241 s zaxira** bilan turadi (1009 / 1250). Bu faza ~6 jadval,
~8 marshrut va ~10 komponent qo'shadi.

**Qoida (05-15 W0-13 naqshi):** har to'lqin oxirida `gate` vaqti **o'lchanadi**. Oshsa —
byudjet **sabab bilan** qayta belgilanadi (`package.json` dagi `//gate-budget` izohida **va**
bu faylda BIR XIL qiymat). O'lchov **tinch xostda** olinadi: `parnikkpi-*` konteynerlar
`docker stop` bilan to'xtatiladi, o'lchovdan keyin tiklanadi.

⚠ **`C:` diski 91 % to'la (bo'sh 15 GB)** — Docker VHDX o'sha yerda. O'lchovdan oldin joy
tekshiriladi.

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

---

## Per-Task Verification Map

> Rejalar yozilgandan keyin to'ldiriladi (`/gsd-execute-phase` har task commit'idan keyin yangilaydi).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| _(rejalardan to'ldiriladi)_ | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

**Ikkitasi ZOND** — javobi noma'lum va rejaning shakliga ta'sir qiladi, shuning uchun
boshqa hamma ishdan oldin o'lchanadi:

- [ ] **A1 ZOND** — `tests/tenancy/test_idempotency_concurrency.py`: haqiqiy PG, ikki parallel `asyncio` sessiya bir xil `idempotency_key` bilan. `ON CONFLICT DO NOTHING ... RETURNING` konfliktda qator **qaytarmaydi** → majburiy alohida `SELECT`; READ COMMITTED ostidagi oyna **o'lchanmagan** (G-12)
- [ ] **A2 ZOND** — `tests/tenancy/test_generated_from_column_probe.py`: PG 18 da `GENERATED ALWAYS AS (<plain column>) STORED` ruxsat etiladimi (C-2 ning ikkinchi variantiga kerak)
- [ ] `tests/fixtures/billing_domain.py` — 6 jadval seed'i (`fixtures/occupancy_domain.py` naqshi). ⚠ `stall_slot_occupancy` qatorlari **`day_close` orqali** yoziladi, qo'lda `INSERT` EMAS — aks holda C-3 sinfidagi xato testda **ko'rinmaydi**
- [ ] `tests/integration/test_phase6_criteria.py` — beshta mezon + meta-test + G-2/G-3/G-6
- [ ] `tests/tenancy/test_billing_domain_meta.py` — sxema konstraytlari (`test_occupancy_domain_meta.py` naqshi)
- [ ] `frontend/scripts/collect-surface.test.mjs` — G-7 (ko'r deklaratsiya + ommaviy amal yo'qligi), **katalogdan hosila**
- [ ] `frontend/src/components/collect/*.test.tsx` — bosish sanog'i (SC#4b), `useRef` qulfi (SC#5b)
- [ ] `tests/unit/test_billable_from_slots.py` + `tests/unit/test_variance.py` — sof funksiyalar, **jadval testi** (`test_aggregate_stall_slot.py` naqshi), bitta holat emas
- [ ] Framework install — **kerak emas**, hammasi mavjud

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| _(kutilmaydi — D-01 bo'yicha bu fazada hammasi mexanik isbotlanadi)_ | | | |

⚠ **Bu jadvalga qo'shilgan har qator dizayn xatosi gumoni bilan qaraladi.** Qo'shilsa —
sabab, ega va tetik bilan `06-HUMAN-UAT.md` ga ham yoziladi.

⚠ Ochiq buyurtmachi savollari (OQ-3/OQ-4/OQ-6/OQ-7) **manual verification EMAS** — ular
`[ASSUMED]` standart qiymat bilan qurilib, javob kelganda sozlanadigan **parametr**.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (A1 va A2 zondlari BAJARILDI)
- [ ] No watch-mode flags
- [ ] Feedback latency < 180 s
- [ ] `gate` byudjeti o'lchandi va `package.json` bilan bu fayl BIR XIL qiymatda
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

---
*Phase: 06-billing-va-kassir*
*Derived from: 06-RESEARCH.md § Validation Architecture (2026-08-10)*
