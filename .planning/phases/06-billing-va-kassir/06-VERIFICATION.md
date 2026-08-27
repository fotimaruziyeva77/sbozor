---
phase: 06-billing-va-kassir
verified: 2026-08-11T08:24:54Z
status: human_needed
score: 5/5 must-haves verified (9/9 requirements satisfied)
overrides_applied: 0
human_verification:
  - test: "Dalil kadrining nizoda O'QILISHI — real Karmana kadrida rasta ko'rinadimi, sotuvchi uni tanib oladimi, nizoda ishonch uyg'otadimi"
    expected: "Direktor GET /snapshots/{id}/image orqali ochilgan kadrni ko'rib, u orqali sotuvchi bilan nizoni hal qila oladi"
    why_human: "Zanjir oxirigacha (daily_charges -> charge_evidence -> occupancy_events.snapshot_id -> GET /snapshots/{id}/image, 200 + image/jpeg + aynan o'sha baytlar) mexanik o'lchangan va tasdiqlandi (test_sc2_charge_reaches_evidence_and_cannot_be_edited, real SeaweedFS ustida). O'lchanmagani inson idroki: kadr sifati/burchagi haqiqiy nizoda YETARLIMI — buni hech qanday test ayta olmaydi."
  - test: "Kassir oqimining (≤3 bosish, rasta qidiruv, to'lov tasdig'i) REAL TELEFONDA bajarilishi"
    expected: "Kassir jonli qurilmada barmoq bilan bossa, klaviatura ekranni qoplamasa, bir qo'lda ishlatsa va quyosh ostida ko'rinadigan bo'lsa"
    why_human: "≤3 bosish DOM'dan hosila sanoq bilan mexanik o'lchangan (collect-session.test.tsx, steps derived from a real interaction loop — 3 baxtli yo'lda, 4 ko'p moslikda, ikkalasi ham to'g'ri assert bilan qulflangan). Lekin jsdom brauzer emas: tegish nishoni o'lchami (min-h-11/min-h-14) sinf sifatida bor, biroq real qurilmada bosish, klaviatura qoplashi va yorug'lik sharoiti o'lchanmagan."
  - test: "Ko'r deklaratsiyaning AMALIY ko'rligi — kassir smena jamini boshqa yo'ldan (qog'oz daftar, o'z xotirasi) chiqarib olmasligi"
    expected: "Kassir smenani yopganda faqat o'zi sanagan naqdga tayanadi, boshqa hech qanday tashqi yozuvdan foydalanmaydi"
    why_human: "Uch strukturaviy qatlam mexanik o'lchangan va barchasi kodda tasdiqlandi: backend javobida system_* maydoni umuman e'lon qilinmagan (CLOSE_RESPONSE_KEYS to'plam tengligi), klientda z.strictObject sxema (server qo'shsa parse vaqtida yiqiladi), components/collect/** katalogining statik token skani (collect-surface.test.mjs) va ekranda AYNAN uchta natija elementi (page.test.tsx, query-eviction rerender bilan). O'lchanmagani tashkiliy shart — texnik emas."
  - test: "Sabab-kodlarning amalda TO'G'RI tanlanishi (summani o'zgartirish va storno uchun)"
    expected: "Kassir 'boshqa' variant yo'qligida vaziyatga eng mos sabab-kodni tanlaydi va bu tanlov keyingi hisobotda mazmunli guruhlanadi"
    why_human: "Yopiq ro'yxat (ReversalReason/AdjustmentReason, 'other' a'zosi ATAYIN yo'q) va 422 darvozasi (sabab-kodsiz chetlanish rad etiladi) HTTP darajasida mexanik o'lchangan (test_sc4(c)). O'lchanmagani — kassirning real vaziyatda qaysi sababni tanlashi: bu pilotning birinchi oyida sabab taqsimoti hisobotidan kuzatiladi."
---

# Phase 6: Billing va kassir Verification Report

**Phase Goal:** Band rasta kun oxirida o'zgarmas, dalilga bog'langan pattaga aylanadi va kassir uni telefonda ≤3 bosishda yig'adi
**Verified:** 2026-08-11T08:24:54Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

Bu tekshiruv SUMMARY.md da'volariga ishonmadi — har bir da'vo kod, migratsiya, test va sxema darajasida qayta o'qildi. Quyida har bir mezon uchun aniq fayl/qator dalili keltirilgan.

### Observable Truths

| # | Truth (ROADMAP mezoni) | Status | Evidence |
|---|---|---|---|
| 1 | Kun yopilganda band rastaga (≥2 snapshot band, yoki 1 + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq patta yoziladi; qayta ishga tushirish ikkinchi hisob bermaydi | ✓ VERIFIED | `write_charge()` (`billing_repo.py:622-638`) `ON CONFLICT (market_id, stall_id, service_date) DO NOTHING` — DB `UNIQUE` (`0020_billing_domain.py:408-413`), application discipline emas. D-04 predikati `billable_from_slots()` (`sbozor_core/billing.py:169-265`, sof funksiya, C-6 rioya qiladi — `human_confirmed_occupied` bir qator konyunksiyasi bilan). `test_sc1_immutable_daily_charge_is_written_once` real Postgres ustida: (a) materializatsiyasiz `charged=0` VA `no_slot_rows>0` (Pitfall 2 ajratilgan); (b) yozilgan ikkita rasta AYNAN kutilgan to'plamga teng, summa `tariffs` dan o'qib solishtirilgan; (c) qayta yugurish `charged=0` **VA** `amount_soum`/`created_at` ikkalasi ham o'zgarmagan (D-06, sabotaj S-1 bilan sinalgan — `on_conflict_do_update`ga almashtirilganda ikkinchi assert qizardi). |
| 2 | Har hisobdan dalilga o'tish mumkin; hisob o'zgarmas; tuzatish faqat sabab bilan `charge_adjustments` | ✓ VERIFIED | `test_sc2_charge_reaches_evidence_and_cannot_be_edited`: zanjir OXIRIGACHA — `daily_charges -> charge_evidence -> occupancy_events.snapshot_id -> GET /snapshots/{id}/image` **200 + `image/jpeg` + aynan o'sha baytlar**, HAQIQIY SeaweedFS'ga yozilgan (mock yo'q). `daily_charges`/`payments`/`cashier_shifts` uchtasi ham `attach_immutability_trigger` bilan shartsiz `BEFORE UPDATE OR DELETE` (`0020_billing_domain.py:744`, `triggers.py:601-689`) — `UPDATE`/`DELETE` `psycopg.errors.RaiseException` beradi (testda tasdiqlangan). Yagona DELETE-yo'l — `is_active=false` bo'lgan qoralama bozor uchun, va `market_deactivate()` funksiyasi ATAYIN yaratilmagan (`markets.py:500-504`) — ya'ni jonli bozor uchun bu yo'l mavjud emas. `charge_adjustments` INSERT o'tadi va `audit_log`ga tushadi (testda tasdiqlangan). |
| 3 | Qarz faqat biriktirilgan sotuvchida; qoldiq hisoblanadigan (hisoblar−to'lovlar); biriktirilmagan band rasta = anomaliya | ✓ VERIFIED | `vendor_outstanding()` yozilgan hisobni qamraydi (`test_sc3` (a)). Biriktirilmagan rastada `daily_charges` 0 qator **va** `billing_anomalies(kind='unassigned_occupied')` 1 qator (D-28, `write_charge()`ning `ValueError` shoxi + `_close_stall`ning anomaliya shoxi — ikki mustaqil qo'riqchi, sabotaj S-3 bilan tasdiqlangan). Saqlangan balans ustuni **yo'q** — mustaqil ravishda `0020_billing_domain.py:373-421` DDL'idan o'qib tekshirildi (`daily_charges` ustunlari: market_id/id/stall_id/vendor_id/service_date/tariff_id/tariff_amount_soum/amount_soum/created_at/business_date — `balance*` yo'q) **va** testning `information_schema` to'plam-tengligi bilan. FIFO taqsimlash (`allocate_charge_credit()`, `sbozor_core/billing.py:470-586`) — hosila ko'rinish, ikki ichki invariant o'zini o'zi tekshiradi (kredit yo'qolmaydi; `unpaid == vendor_outstanding` bilan bir xil son), `payment_allocations` jadvali yo'q, `allocated_*` ustuni yo'q. `test_payment_credit_rules.py` — 9+ qatorli FIFO jadvali, 7+ qatorli kvota jadvali; `test_billing_repo.py::test_a_single_payment_across_days_settles_the_oldest_first` uch kunlik qarz + bitta 45 000 to'lov → yopilgan kunlar aynan `[D-2, D-1, D]`. |
| 4 | Kun davomida kassir/direktor "kutilayotgan patta"ni jonli ko'radi; kassir ≤3 bosishda tasdiqlaydi; summani faqat sabab-kod bilan o'zgartiradi | ✓ VERIFIED | `GET /billing/pending` javobi AYNAN 7 kalit, `charge_id` yo'q (D-17, `test_sc4`(a) to'plam tengligi bilan). `resolve_stall_day_money()` va `pending_projection()` — ikki chaqiruv, bir natija (D-16, testda arifmetik solishtirilgan). ≤3 bosish `collect-session.test.tsx::runFlow()` da HAQIQIY DOM interaksiya siklidan HOSILA sanoq (hardcoded emas) — baxtli yo'lda `steps===3`, ko'p-moslik yo'lida `steps===4` (alohida test bilan qulflangan, ya'ni son ham 2ga, ham 4ga qizarardi). `package.json::gate` zanjirida `npm --prefix frontend test` bor — testning DARVOZAGA ulanganini o'zim tekshirdim. Sabab-kodsiz chetlangan summa → **422** (`test_sc4`(c), haqiqiy marshrutdan). |
| 5 | Takror bosilgan to'lov dublikat yaratmaydi, tuzatish faqat storno; smena yopilishida kassir tizim summasini ko'rmasdan naqd deklaratsiya qiladi, farq direktor hisobotiga chiqadi | ✓ VERIFIED | Idempotentlik kaliti — DB `UNIQUE(market_id, idempotency_key)` (`0020_billing_domain.py:597-600`) + ikki bayonotli get-or-create (`payment_repo.py:446-540`), application discipline emas. **CR-02 tasdiqlandi TUZATILGAN:** `payments.py:319-355` idempotentlik tekshiruvi endi QUOTE/SABAB darvozalaridan (5-QADAM) OLDIN, saqlangan `quote_soum`dan (qayta hisoblanmagan) fingerprint hisoblanadi — `test_a_debt_moving_payment_is_still_idempotent_on_retry` (ikki parametr: qarz+tarif, faqat qarz) ilgari 422 bilan yiqiladigan holatni endi 200 deb tasdiqlaydi. Storno — YANGI qator (`kind='reversal'`), `UPDATE payments` rad etiladi (trigger). Ko'r deklaratsiya **4 mustaqil qatlamda**: (1) backend `CLOSE_RESPONSE_KEYS` to'plam tengligi — `system_*` yo'q; (2) frontend `z.strictObject` (`shift-queries.ts:103-108`) — server qo'shsa parse yiqiladi; (3) `collect-surface.test.mjs` — `components/collect/**` katalogining HOSILA (readdirSync) statik token skani (`variance`, `system_soum` va b. taqiqlangan); (4) `shift/page.test.tsx` — ekranda AYNAN 3 ta `data-shift-result` bolasi, **query-cache evikatsiyasidan keyingi qayta chizishda** ham (CR-05 ning aynan regressiyasi). Variance ikki yo'nalishda, HAR XIL kattalikda sinalgan (`-5000` / `+7000`) — `abs()` sabotaji (S-5) bir shoxni tutdi, ikkinchisini YO'Q — bu HOLAT tanlovi ataylab shunday, testda tasdiqlangan. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `packages/sbozor-core/sbozor_core/billing.py` | Sof qoidalar: billable_from_slots, variance, allocate_charge_credit | ✓ VERIFIED | 587 qator, DB/HTTP bog'liqligi yo'q, ikki ichki invariant `AssertionError` bilan o'z-o'zini tekshiradi, `assert` bayonoti emas (S101 dan qochish uchun ataylab) |
| `migrations/versions/0020_billing_domain.py` | 6 jadval: cashier_shifts, daily_charges, charge_adjustments, charge_evidence, payments, billing_anomalies | ✓ VERIFIED | Barcha UNIQUE/CHECK/FK constraint mavjud, uchta immutability trigger bog'langan (744-qator) |
| `services/core-api/app/repositories/billing_repo.py` | write_charge, vendor_outstanding, pending_projection, charge_list, anomaly_list, vendor_charge_allocation | ✓ VERIFIED | Barcha funksiyalar haqiqiy SQL bilan (`_CHARGE_ROWS`, `_ANOMALY_ROWS` va b.), static return yo'q |
| `services/core-api/app/repositories/payment_repo.py` | create_payment (idempotent get-or-create) | ✓ VERIFIED | Ikki bayonotli shakl, `IdempotencyConflict` xato turi bilan |
| `services/core-api/app/jobs/billing_close.py` | billing_close(business_date) — argumentli, konvergent job | ✓ VERIFIED | WR-03 tuzatilgan: anomaliya sanoqlari YOZUVGA ergashadi, urinishga emas |
| `services/core-api/app/api/v1/{billing,payments,shifts}.py` | GET/POST marshrutlar | ✓ VERIFIED, WIRED | Barcha `detail` qiymatlari SATR (CR-04/WR-06 tuzatilgan); NO_OPEN_SHIFT endi 3.5-QADAMDA ushlanadi (WR-01 tuzatilgan) |
| `frontend/src/app/[locale]/(app)/{billing,collect,collect/shift}/page.tsx` | Direktor va kassir ekranlari | ✓ VERIFIED, WIRED | `billing/page.tsx` — G-25 kesishmasi (pending/charges hech qachon birga chiqmaydi), real hook'lar (useCharges, useAnomalies, useShiftReport) |
| `frontend/src/components/collect/*.tsx` | ≤3 bosishli oqim, ko'r deklaratsiya | ✓ VERIFIED, WIRED, DATA FLOWING | CR-03 (NetworkError), CR-05 (unmount) tuzatilgan va regression testlar bilan qulflangan |
| `tests/integration/test_phase6_criteria.py` | 5 SC + meta + no-fakes darvozasi | ✓ VERIFIED | 12 test funksiyasi (mening sanoq — `grep`), o'lchov bilan mos (SUMMARY "12 passed" da'vosi tasdiqlandi) |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `billing/page.tsx` | `useCharges()`/`useAnomalies()` | import + render | WIRED | `charge-list.tsx:11`, `anomaly-list.tsx:15` — real `useQuery` chaqiruvi |
| `useCharges()` | `GET /billing/charges` | `apiFetch()` + zod schema | WIRED | `billing-charge-queries.ts:322-330`, `chargeListSchema` orqali parslanadi |
| `GET /billing/charges` | `billing_repo.charge_list()` | direct call | WIRED | Haqiqiy SQL (`_CHARGE_ROWS`), statik bo'sh javob emas |
| `charge-detail-dialog.tsx` | `GET /snapshots/{id}/image` | `useEvidenceImageHref()` | WIRED, DATA FLOWING | `<img src={image.href}>` — real baytlar (SC#2 testida tasdiqlangan) |
| `POST /payments` | `payment_repo.create_payment()` | 2.5/6-QADAM | WIRED | Idempotentlik tekshiruvi endi pricing gate'lardan OLDIN (CR-02 tuzatilgan) |
| `ShiftCloseForm` | `useCloseShift()` | mutation + query eviction | WIRED (regression-tested) | `shift/page.test.tsx` query-eviction rerender'dan KEYIN ham natija ekranini tasdiqlaydi (CR-05) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `charge-list.tsx` | `useCharges(day)` | `GET /billing/charges` → `billing_repo.charge_list()` → real SQL | Ha | ✓ FLOWING |
| `anomaly-list.tsx` | `useAnomalies(day)` | `GET /billing/anomalies` → `billing_repo.anomaly_list()` → real SQL | Ha | ✓ FLOWING |
| `pending-summary.tsx` | `pending_projection()` | `GET /billing/pending` → `resolve_stall_day_money()` + `pending_projection()` | Ha | ✓ FLOWING |
| `variance-list.tsx` | `useShiftReport(day)` | `GET /shifts?day=` → `shift_repo.shift_report()` → real SQL, variance SERVERDA | Ha | ✓ FLOWING |
| `charge-detail-dialog.tsx` (evidence img) | `useEvidenceImageHref()` | `GET /snapshots/{id}/image` → haqiqiy SeaweedFS `GetObject` | Ha (mock yo'q) | ✓ FLOWING |

### Behavioral Spot-Checks

Skip qilindi — dockerized backend (docker compose) yugurish `<measurements_already_taken>` blokida allaqachon berilgan va parallel yugurayotgan to'liq suite bilan poyga xavfi bor edi. Buning o'rniga statik/kod darajasidagi tekshiruv (yuqoridagi Key Link va Data-Flow jadvallari) bilan almashtirildi.

### Probe Execution

Loyihada `scripts/*/tests/probe-*.sh` shaklidagi probe fayllari topilmadi va PLAN/SUMMARY fayllarida probe so'zi ishlatilmagan — bu qadam qo'llanilmaydi.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| BILL-01 | 06-01, 04, 05, 06, 07, 14 | Kun yopilishida to'liq patta, idempotent job | ✓ SATISFIED | SC#1 dalili yuqorida |
| BILL-02 | 06-04, 05, 06, 07, 08, 13, 14 | Dalilga bog'langan, o'zgarmas, tuzatish faqat charge_adjustments | ✓ SATISFIED | SC#2 dalili yuqorida |
| BILL-03 | 06-01, 04, 06, 08, 13, 14 | Qarz faqat biriktirilgan sotuvchida, hisoblanadigan qoldiq | ✓ SATISFIED | SC#3 dalili yuqorida |
| BILL-04 | 06-02, 04, 06, 07, 08, 13, 14 | Biriktirilmagan band = anomaliya, hisob yo'q | ✓ SATISFIED | SC#3(b) dalili yuqorida |
| BILL-05 | 06-02, 03, 06, 08, 11, 14 | Kutilayotgan patta — jonli proyeksiya, hisob emas | ✓ SATISFIED | SC#4(a) dalili yuqorida |
| CASH-01 | 06-02, 03, 09, 11, 14 | Rasta→summa→to'lov turi→≤3 bosishda tasdiq | ✓ SATISFIED | SC#4(b) dalili yuqorida |
| CASH-02 | 06-02, 09, 11, 14 | Sabab-kod bilan o'zgartirish, auditda ko'rinadi | ✓ SATISFIED | SC#4(c) dalili yuqorida |
| CASH-03 | 06-01, 02, 03, 09, 11, 14 | Idempotent to'lov, tuzatish faqat storno | ✓ SATISFIED | SC#5(a)(c) dalili yuqorida |
| CASH-04 | 06-01, 03, 04, 10, 12, 13, 14 | Smena, ko'r deklaratsiya, variance direktorga | ✓ SATISFIED | SC#5(d) dalili yuqorida |

Barcha 9 talab 14 rejaning `requirements:` maydonida hisobga olingan; ORPHANED talab yo'q (REQUIREMENTS.md ning Phase 6 qatoriga mos, 9/9).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| — | — | TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER qidiruvi (billing.py, payments.py, shifts.py, billing_repo.py, payment_repo.py, shift_repo.py, billing_close.py, billing.py (core), collect/*.tsx, billing/*.tsx, *-queries.ts) | — | ℹ️ INFO — hech narsa topilmadi. Kod bazasi bu jihatdan toza. |
| `frontend/src/components/billing/charge-list.tsx` (vendor name join) | — | 50 sotuvchidan ortiq bozorda 51+ qatorning sotuvchi ismi bo'sh qoladi (`useVendorsQuery` sahifalangan, `PAGE_SIZE=50`) | ℹ️ INFO | `deferred-items.md` #9 da hujjatlashtirilgan, ataylab (audit shovqini, yangi backend yuzasi va shaxsiy-ma'lumot marshrutini oldini olish uchun). Rasta kodi baribir ko'rinadi — qarz SONI to'g'ri, faqat ISM to'liq emas. 8-fazaning hisobot yuzasiga tegishli, phase 6 SC#3 ning "qarz ko'rinadi" talabini buzmaydi. |
| `services/core-api/app/services/billing_errors.py:243` (`CHARGE_IMMUTABLE`) | 243 | Reyestrda bor, lekin birorta marshrut uni HTTP orqali qaytarmaydi (WR-08 ning yarmi — `NO_OPEN_SHIFT` yarmi WR-01 bilan tuzatilgan) | ℹ️ INFO | Xom SQL `UPDATE daily_charges` trigger orqali baribir rad etiladi (500 sifatida, 409 emas) — MA'LUMOT YAXLITLIGI buzilmaydi, faqat xato kodi granulyar emas. HTTP orqali charge mutatsiyasi marshruti umuman yo'q, ya'ni bu kod amalda hech qachon kerak bo'lmaydi. |

Debt-marker gate: toza — birorta fayl `TBD`/`FIXME`/`XXX` bermadi.

### Human Verification Required

Quyidagilar `06-VALIDATION.md`ning `human_only_verifications` frontmatteridan olindi. Ularning har biri **talab matnining o'zi emas** — inson idroki, real qurilma yoki tashkiliy shart haqida, va bu farq REQUIREMENTS.md da ham izchil hujjatlashtirilgan. Lekin ular hali ham "visual appearance / real device feel" toifasiga kirgani uchun bu tekshiruv ularni human-needed sifatida qoldiradi (3- va 5-fazalarda o'rnatilgan xuddi shu andoza).

### 1. Dalil kadrining nizoda o'qilishi

**Test:** Real Karmana kadrini direktor sifatida `GET /snapshots/{id}/image` orqali ochib ko'rish
**Expected:** Kadr sifat/burchagi haqiqiy nizoda ishonchli dalil bo'la oladi
**Why human:** Mexanik zanjir (baza → ombor → HTTP) to'liq o'lchangan; kadrning SIFATI insonning o'zi baholaydigan narsa

### 2. Kassir oqimi real telefonda

**Test:** Kassir haqiqiy qurilmada rasta qidirish → to'lov turi → tasdiqlash zanjirini bosish
**Expected:** ≤3 bosish, klaviatura qoplamaydi, bir qo'lda ishlaydi, quyosh ostida ko'rinadi
**Why human:** DOM interaksiya sanog'i jsdom da mexanik o'lchangan, lekin jsdom brauzer emas — teginish, klaviatura va yorug'lik real qurilma talab qiladi

### 3. Ko'r deklaratsiyaning amaliy ko'rligi

**Test:** Kassirning smena yopish jarayonini kuzatish
**Expected:** Kassir faqat o'z sanog'iga tayanadi, boshqa yozuvdan (daftar, xotira) foydalanmaydi
**Why human:** To'rt strukturaviy qatlam (backend/frontend/statik-skan/render) to'liq o'lchangan va tasdiqlangan; qolgani tashkiliy intizom

### 4. Sabab-kodlarning amaliy tanlovi

**Test:** Pilotning birinchi oyida sabab-kod taqsimotini kuzatish
**Expected:** Kassirlar vaziyatga mos sabab tanlaydi, "eng qulay" kodni ko'r-ko'rona bosmaydi
**Why human:** Yopiq ro'yxat va 422 darvozasi mexanik o'lchangan; amaliy tanlov sifati inson kuzatuvi

### Gaps Summary

**Bo'shliq topilmadi.** Beshala ROADMAP mezoni kod, migratsiya, trigger va real integratsiya testlari darajasida mustaqil tasdiqlandi. `06-REVIEW.md`da topilgan 5 blocker + 9 warning'dan barchasi kodda qayta tekshirildi (5/5 blocker to'liq, 6/9 warning namunaviy chuqur tekshirildi — WR-01, 02, 03, 04, 05, 06, 07 — hammasi tasdiqlangan tuzatilgan; WR-08 va WR-09 qisman/informatsion, funksional bo'shliq emas).

Yagona ochiq band — `human_needed` toifasidagi 4 ta band, ular ROADMAP mezonlarining o'zi emas (kod darajasida hech narsa yetishmayapti), balki inson idroki/real qurilma/tashkiliy shart bo'yicha pilot haftasida tasdiqlanishi kerak bo'lgan narsalar. Bu andoza 3-, 4- va 5-fazalarda ham xuddi shunday qo'llanilgan va bu yerda ham izchil.

`deferred-items.md`dagi 4 ta ochiq band (phase-5 flaky test, phase-5 heartbeat ko'rinmasligi, phase-5 dan meros matritsa chegarasi, 50+ sotuvchili bozorda ism ko'rinmasligi) — barchasi aniq boshqa faza/domenga tegishli deb hujjatlashtirilgan va mening mustaqil tekshiruvim bu ta'rifni tasdiqladi: hech biri phase 6 ning 5 ROADMAP mezonidan birortasini buzmaydi.

---

_Verified: 2026-08-11T08:24:54Z_
_Verifier: Claude (gsd-verifier)_
