---
phase: 06-billing-va-kassir
plan: 07
subsystem: billing
tags: [job, cron, taskiq, heartbeat, observability, idempotency, sabotage, migration]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 06
    provides: "`billing_repo` — `resolve_stall_day_money()`, `billable_stalls()`, `write_charge()`, `write_evidence()`, `write_anomaly()`"
  - phase: 06-billing-va-kassir
    plan: 05
    provides: "`tests/fixtures/billing_domain.py` — slotlar `day_close` ORQALI; ikki variant (Pitfall 2)"
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "Olti billing jadvali, uch o'zgarmaslik qo'riqchisi, `service_date <= business_date` sharti"
  - phase: 06-billing-va-kassir
    plan: 01
    provides: "`billable_from_slots()` — hisob shartining sof qoidasi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`app/jobs/day_close.py` (VERBATIM shablon), `occupancy_repo.active_stall_ids()`, `stall_slot_occupancy` ning yagona yozuvchisi"
  - phase: 04-snapshot-quvuri
    provides: "`worker.py` cron naqshi + yupqa qobiq, `alerting._platform_signals`, `self_check.EXPECTED_COMPONENTS`, `retention.active_market_ids()`"
provides:
  - "`services/core-api/app/jobs/billing_close.py` — argumentli, konvergent, hech qachon yiqilmaydigan job + `BillingCloseResult` (o'n bir maydon)"
  - "`worker.py::BILLING_CLOSE_CRON = \"10 4 * * *\"` + `billing.close` yupqa qobig'i (KECHAGI kunni yopadi)"
  - "`migrations/0022_billing_late_review.py` — `actor_user_id` `NULL` qabul qiladi + `late_review` uchun qisman UNIQUE indeks"
  - "`billing_repo`: `event_snapshots()`, `market_day_charges()`, `write_late_review_adjustment()` — BILL-02 ning YAGONA producer'i"
  - "M-C YOPILDI: `billing_close` `EXPECTED_COMPONENTS` da VA `alert_sweep::watched` da"
  - "`tests/integration/test_billing_close.py` — 7 darvoza haqiqiy `postgres:18.4` da, soxta qatlamsiz"
  - "O'LCHANGAN SABOTAJ: Pitfall 9 (tenant konteksti) — 6/7 QIZARDI va nosozlik shakli REJADAGIDAN BOSHQA chiqdi"
affects: [06-08, 06-09, 06-10, 06-12, 06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fon jobi yozadigan AUDIT OSTIDAGI qator uchun `actor_user_id` `NULL` bo'ladi (`audit_log.actor_user_id` naqshi) — soxta «tizim foydalanuvchisi» qatori YARATILMAYDI"
    - "Konvergent job'ning idempotentligi QISMAN UNIQUE INDEKS bilan majburlanadi, «avval tekshir, keyin yoz» bilan EMAS (`SHIFT_OPEN_INDEX` qarorining takrori)"
    - "Hisoblagichning MAXRAJI o'zi o'lchayotgan yozuvchining to'plamidan olinadi (`no_slot_rows` <- `active_stall_ids()`), aks holda signal doimiy shovqinga aylanadi"
    - "Kelajakdagi seed kunida ifodalab bo'lmaydigan darvoza uchun test O'TMISHDAGI kunni O'ZI quradi (`PastDay`) — seedning sanasiga moslashish uchun mahsulot shartini bo'shatish TAQIQLANADI"
    - "Yangi platforma alerti qo'shilganda mavjud guruhlash testlarining `_PLATFORM_COMPONENTS` ro'yxati ham yangilanadi — aks holda ular MAHSULOT to'g'ri ishlayotgan holda qizaradi"

key-files:
  created:
    - services/core-api/app/jobs/billing_close.py
    - tests/integration/test_billing_close.py
    - migrations/versions/0022_billing_late_review.py
  modified:
    - services/core-api/app/worker.py
    - services/core-api/app/repositories/billing_repo.py
    - services/core-api/app/api/internal/self_check.py
    - services/core-api/app/jobs/alerting.py
    - packages/sbozor-core/sbozor_core/models/billing.py
    - tests/fixtures/billing_domain.py
    - tests/integration/test_alerting.py
    - tests/tenancy/test_billing_domain_meta.py
    - frontend/src/components/snapshots/alert-row.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json

key-decisions:
  - "06-07: `charge_adjustments.actor_user_id` `NULL` QABUL QILADI (`0022`) — rejada `actor_user_id = NULL` yozilgan, `0020` da esa ustun `NOT NULL` edi; soxta «tizim foydalanuvchisi» qatori yaratish audit javobini YOLG'ON qilardi"
  - "06-07: `late_review` idempotentligi QISMAN UNIQUE INDEKS bilan — rejadagi `on_conflict_do_nothing` uchun NISHON umuman yo'q edi va ikki parallel yugurish TO'LIQ SUMMANI ikki marta ayirardi (netto MANFIY)"
  - "06-07: `no_slot_rows` maxraji `active_stall_ids()` dan — bozorning BARCHA rastalari olinsa `closed`/`maintenance` rastalar HAR KUNI Pitfall 2 signalini shishirardi"
  - "06-07: integratsiya testi O'TMISHDAGI kunni O'ZI quradi — `SEED_BUSINESS_DATE` (2026-09-01) KELAJAKDA va `service_date <= business_date` unga birorta hisob/anomaliya yozishga yo'l bermaydi"
  - "06-07: kech tasdiq shoxi `no_coverage_only` HOLATIDA ISHLAMAYDI — «ko'ra olmadik» sababli hisobni kamaytirish tushumni KO'R NUQTA hisobiga o'chirardi (D-05 ning teskarisi)"
  - "06-07: `day_close` ning AYNAN o'sha ko'rligi ATAYIN yopilmadi va `deferred-items.md` ga NOMLANGAN band bo'lib yozildi — 6-fazani 5-fazaning testlariga bog'lash"

patterns-established:
  - "Reja SXEMA bilan ziddiyatga tushganda: sxema o'zgarishi ENG TOR shaklda (bitta `ALTER` + bitta indeks) qilinadi va SABAB migratsiya docstringida O'LCHOV bilan yoziladi"
  - "Sabotaj natijasi REJADAGI GIPOTEZADAN farq qilsa, farq SUMMARY da AYNAN qayd etiladi (da'vo emas, O'LCHOV yoziladi)"
  - "Prose'dagi taqiq matni grep darvozasini qizartirsa, o'lchov AST bilan takrorlanadi (`raise` bayonotlari soni, nom havolalari) — matn darvozasi sababni yozishga to'sqinlik qilmaydi"

requirements-completed: [BILL-01, BILL-02, BILL-04]

# Metrics
duration: 105min
completed: 2026-08-11
---

# Phase 6 Plan 07: Kun yopilishining tetigi — `billing_close` Summary

**Kunlik patta hisobi endi ARGUMENTLI, KONVERGENT va HECH QACHON YIQILMAYDIGAN job'da; cron `day_close` DAN KEYIN yuguradi va KECHAGI kunni yopadi (C-3); «yashil, lekin bo'sh» holati `no_slot_rows` bilan «ishladi» dan MEXANIK ravishda ajraldi; va vazifaning UMUMAN ISHLAMAGANI endi ikki joyda ko'rinadi — `EXPECTED_COMPONENTS` va `alert_sweep` (M-C).**

## Performance

- **Duration:** ~105 min
- **Started:** 2026-08-10T23:35:00Z
- **Completed:** 2026-08-11T01:20:00Z
- **Tasks:** 3
- **Files:** 3 yangi + 12 tahrirlangan

## Accomplishments

- **C-3 hal qilindi va D-13 ning MAZMUNI saqlandi.** `BILLING_CLOSE_CRON = "10 4 * * *"` (`DAY_CLOSE_CRON` = 03:40 dan **keyin**), qobiq `business_today() - timedelta(days=1)` beradi. Cron konstantasining docstringida uchala band ham yozilgan: (a) nega 03:40 dan keyin, (b) 30 daqiqalik oraliqning sababi, (c) **tartib kafolati bu satrga tayanmaydi** — job idempotent va konvergent.
- **Pitfall 2 IKKI HOLAT bilan ajraldi va sonlar NAZORAT bilan o'lchandi.** `day_close` siz: `charged == 0`, `no_slot_rows == 8` (ikkala bozorning **faol** rastalari soniga TENG — «noldan katta» emas), `errors == []`. `day_close` bilan: `charged == 2`, `no_slot_rows == 0`, `errors == []`.
- **Uchala anomaliya ALOHIDA sanaladi va ARALASHMAYDI.** O'lchandi: `anomalies_unassigned == 1` (dalil **bilan** — `occupancy_event_id` va `snapshot_id` `NOT NULL`), `anomalies_no_coverage == 4` (dalil **siz** — ikkalasi ham `NULL`), to'plamlar kesishmaydi.
- **D-14 ning miqdori TRIVIAL BO'LMAGAN holda o'lchandi.** Stsenariyda inson tasdiqlagan hisob ham bor: `charged == 2`, `resolved_without_reviewer == 1`. Bitta AI hisobi bilan ikkala son teng bo'lardi va sanoq hech nimani ajratmasdi.
- **Pitfall 5(c) ning uchala bandi ham BAJARILDI va u endi MAHSULOT YO'LI.** Kech tasdiqdan keyin `daily_charges` qatori **bayt-bayt o'zgarmadi**, `charge_adjustments` da `decrease`/`late_review`/`actor_user_id IS NULL` qatori paydo bo'ldi, `audit_log` da DB-trigger yozgan qator `actor_kind = 'system'` bilan turibdi, uchinchi chaqiruvda **ikkinchi tuzatish yozilmadi**.
- **M-C yopildi va IKKALA yarmi ham ALOHIDA sabotaj bilan o'lchandi** (pastdagi jadval): producer (`_write_heartbeat`) va consumer (`watched` reyestri) BOSHQA testni qizartiradi — ya'ni ular bir-birini almashtirmaydi.
- **Yangi paket o'rnatilmadi**, yangi `SECURITY DEFINER` funksiya qo'shilmadi, yangi HTTP marshruti ochilmadi.

## Task Commits

1. **Task 1: argumentli, konvergent `billing_close` job'i** — `851612c` (feat)
2. **Task 2: cron `day_close` dan KEYIN + Pitfall 2 ketma-ketlik testi** — `3b65606` (feat)
3. **Task 3: yurak urishining YO'QLIGI ikki joyda ko'rinadi (M-C)** — `f8c3b6f` (feat)

## Deploy

⛔ **MEXANIK RAVISHDA USHLANMAYDIGAN BAND — QO'LDA BAJARILADI:**

```
docker compose up -d --force-recreate scheduler
```

Cron jadvali `import` PAYTIDA olinadi (`worker.py:55-58`, `LabelScheduleSource`). `scheduler` konteyneri qayta ishga tushirilmasa `billing.close` vazifasi **ro'yxatga olinmaydi**: job hech qachon ishlamaydi, patta hisobi yozilmaydi va **hech qanday xato chiqmaydi**. Buni **birorta test ushlamaydi** — testlar reyestrni jarayonning O'ZIDA o'qiydi.

⚠ **YAGONA MEXANIK HIMOYA** — yurak urishining yo'qligi: band unutilsa 26 soatdan keyin `billing_close_stale` alerti ochiladi (`alerting._platform_signals`, `None` ham eskirish) va `/internal/self-check` javobida `billing_close` `never_seen` ro'yxatida turadi. Buyruq `worker.py::BILLING_CLOSE_CRON` docstringida ham AYNAN shu shaklda yozilgan.

## Sabotaj (D-30) — UCH URINISH, UCH BOSHQA O'LCHOV

| # | Sabotaj | Natija | Xulosa |
|---|---------|--------|--------|
| **S-A (Pitfall 9)** | `billing_close._tenant_session()` dan `set_tenant_context()` chaqiruvi olib tashlandi | 🔴 **6/7 QIZARDI** | ⛔ **NOSOZLIK SHAKLI REJADAGI GIPOTEZADAN BOSHQA CHIQDI.** Reja «hamma kun anomaliya bo'lib chiqishi kerak» degan edi. O'lchandi: `charged=0, anomalies_closed_day=0, anomalies_unassigned=0, anomalies_no_coverage=0, no_slot_rows=0, errors=0` — ya'ni **TO'LIQ SUKUNAT**. Sabab: RLS `market_is_open()` dan tashqari `stall_slot_occupancy` ni ham berkitadi, ya'ni `billable_stalls()` bo'sh qaytadi va yopiq-kun shoxida ham yozadigan hech nima qolmaydi. Bu **rejadagidan YOMONROQ** sinf va uni 6 ta test ushlaydi |
| **S-B (M-C producer)** | `billing_close()` dan `_write_heartbeat(...)` chaqiruvi olib tashlandi | 🔴 **1 QIZARDI** | `test_the_run_writes_a_heartbeat_with_counters_only`. ⚠ `test_alerting.py` dagi yangi da'vo **YASHIL QOLDI** va bu TO'G'RI: u CONSUMER ni (yo'qlik alert beradimi?) o'lchaydi, producer ni emas |
| **S-C (M-C consumer)** | `alerting._platform_signals::watched` dan `(BILLING_CLOSE_COMPONENT, "billing_close_stale")` olib tashlandi | 🔴 **1 QIZARDI** | `test_a_missing_billing_close_heartbeat_is_visible`. ⚠ `test_billing_close.py` dagi yurak urishi testi **YASHIL QOLDI** — ikkala yarim MUSTAQIL o'lchanadi va ular bir-birini ALMASHTIRMAYDI |

Uchala sabotaj ham qaytarildi; `git diff --stat` ikkala faylda ham toza (`billing_close.py` — o'zgarishsiz, `alerting.py` — faqat mo'ljallangan +17 qator).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Rejadagi `actor_user_id = NULL` MEXANIK IMKONSIZ edi — `0022` yozildi**

- **Found during:** Task 1
- **Issue:** Reja kech tasdiq tuzatishini `actor_user_id = NULL` (tizim) bilan yozishni talab qiladi. `0020` da esa ustun `NOT NULL` va `users.id` ga FK bilan bog'langan — ya'ni shox yozilgan taqdirda ham `NotNullViolation` bilan yiqilardi va u `errors` ga `billing_close_failed:IntegrityError` bo'lib tushardi.
- **Fix:** `migrations/versions/0022_billing_late_review.py` — `ALTER COLUMN actor_user_id DROP NOT NULL`; model `Mapped[UUID | None]` ga o'tkazildi. ⛔ Muqobil («tizim foydalanuvchisi» qatorini `users` ga yozish) **RAD ETILDI**: `users` global jadval (soxta hisob RBAC sanoqlarini siljitardi) va nizoda audit qatori «kim qaror qildi?» savoliga ODAM ko'rsatardi, holbuki qaror MODELNIKI. Naqsh yangi emas — `audit_log.actor_user_id` `0002` dan beri `nullable` va sababi AYNAN shu.
- **Files modified:** `migrations/versions/0022_billing_late_review.py`, `packages/sbozor-core/sbozor_core/models/billing.py`
- **Verification:** `test_billing_domain_meta.py` **13/13** yashil (nullability va indeks to'plami uning yuzasida emas); `test_meta.py::test_financial_tables_have_guards` yashil (qisman **indeks** `pg_constraint` ga tushmaydi, `uq_charge_adjustments_market_id_id` esa joyida).
- **Committed in:** `851612c`

**2. [Rule 2 - Missing Critical] `on_conflict_do_nothing` uchun NISHON umuman yo'q edi — qisman UNIQUE indeks qo'shildi**

- **Found during:** Task 1
- **Issue:** Reja «`on_conflict_do_nothing` bilan idempotent (bir hisobga bir `late_review` tuzatishi)» deydi. `charge_adjustments` da esa faqat `uq_charge_adjustments_market_id_id` bor va u HAR `INSERT` da yangi `uuid` bilan **hech qachon to'qnashmaydi** — ya'ni har yugurish YANGI to'liq summali kamaytirish yozardi va hisobning nettosi MANFIY bo'lib qolardi. Ilova qatlamidagi «avval tekshir, keyin yoz» ikki parallel yugurishda ikkalasiga ham bo'sh holatni ko'rsatardi.
- **Fix:** `LATE_REVIEW_ADJUSTMENT_INDEX` — `(market_id, charge_id) WHERE reason_code = 'late_review'` qisman UNIQUE indeksi; predikat `AdjustmentReason` DAN HOSILA. ⚠ Indeks **qisman**: qolgan sabab kodlari uchun «bir hisobga bir necha tuzatish qonuniy» qoidasi kuchida qoladi (`tariff_correction` ni ikki marta yozish INSONNING qonuniy amali).
- **Files modified:** `packages/sbozor-core/sbozor_core/models/billing.py`, `migrations/versions/0022_billing_late_review.py`
- **Verification:** `test_a_late_review_writes_an_adjustment_and_never_edits_the_charge` uchinchi chaqiruvda ikkinchi qator yo'qligini o'lchaydi.
- **Committed in:** `851612c`

**3. [Rule 1 - Bug] `no_slot_rows` MAXRAJI `active_stall_ids()` dan olinadi**

- **Found during:** Task 1
- **Issue:** Rejaning «ro'yxatga umuman kirmagan rastalar `no_slot_rows` ga sanaladi» matni maxrajni ochiq qoldiradi. `resolve_stall_day_money()` bozorning **BARCHA** rastalarini beradi, `day_close` esa faqat `status = 'active'` larni materializatsiya qiladi (`_ACTIVE_STALL_IDS`, 05-faza qarori). Ya'ni har `closed`/`maintenance` rasta **HAR KUNI** `no_slot_rows` ga tushardi va Pitfall 2 ning signali doimiy shovqinga aylanardi — aynan uni o'lchash uchun qo'shilgan hisoblagich.
- **Fix:** Maxraj `OccupancyRepository(session, market_id).active_stall_ids()` dan, ya'ni **AYNI** manbadan. Sabab `BillingCloseResult.no_slot_rows` docstringida.
- **Files modified:** `services/core-api/app/jobs/billing_close.py`
- **Verification:** Pitfall 2 testi `no_slot_rows == <faol rastalar soni>` ni TENGLIK bilan o'lchaydi, «noldan katta» bilan emas.
- **Committed in:** `851612c`

**4. [Rule 3 - Blocking] Rejaning `D = SEED_BUSINESS_DATE` farazi bilan hisob YOZIB BO'LMAYDI**

- **Found during:** Task 2
- **Issue:** ⛔ **BU REJANING ENG QIMMAT TOPILMASI.** `ck_daily_charges_service_date_not_in_future` (`0020`) `service_date <= business_date` ni talab qiladi va `business_date` `created_at` DAN hosila, ya'ni HAR DOIM «bugun». `SEED_BUSINESS_DATE` = **2026-09-01**, bugun esa 2026-08-11 — ya'ni seedning kuni **KELAJAKDA** va o'sha kunga hisob ham, `billing_anomalies` qatori ham (unda ham ayni `CHECK` bor) yozib bo'lmaydi. Rejaning «`day_close(D)` → `billing_close(D)` → `charged > 0`» da'vosi seed kunida **IFODALAB BO'LMAYDI**. 06-06 buni `write_charge()` uchun `_open_past_day()` bilan hal qilgan, 06-05 esa `_safe_service_date()` bilan — bu reja esa BUTUN KUNNI (kadr → hodisa → slot → hisob) talab qiladi.
- **Fix:** Test o'z `PastDay` egasini quradi: o'tmishdagi eng yaqin **ochiq** kunga (A bozorining haftalik jadvali bo'yicha) kadr + hodisa yozadi va AYNAN o'sha kun `day_close` → `billing_close` zanjiridan o'tadi. ⛔ Mahsulot sharti **BO'SHATILMADI**.
- **Files modified:** `tests/integration/test_billing_close.py`, `tests/fixtures/billing_domain.py`
- **Verification:** Yettala test ham o'tmishdagi kunda yuguradi; kun tanlovi `BILLING_VALID_FROM` ga nisbatan NAZORAT asserti bilan; tarif summasi zanjirdan HOSILA (`expected_tariff()`), qadalgan literal emas.
- **Committed in:** `3b65606`

**5. [Rule 2 - Missing Critical] D-28 ning o'tmishdagi kunda ifodalanadigan YAGONA holati boshqa rasta**

- **Found during:** Task 2
- **Issue:** Seedning `stall_occupied_without_assignment` i biriktirish bo'shlig'ini `[SEED_BUSINESS_DATE, +7)` ga qo'yadi — ya'ni **kelajakda**; o'tmishdagi kunda o'sha rasta BIRIKTIRILGAN va D-28 shoxi umuman ishlamasdi (test jimgina «hisob yozildi» ni o'lchagan bo'lardi).
- **Fix:** `market_domain.market_a.unassigned_stall_id` — unga `market_domain` **birorta** biriktirish yozmaydi (`market_domain.py:486-487`), ya'ni u HAR QANDAY kunda sotuvchisiz. Testning `PastDay` egasi unga zona + ikki band hodisa qo'shadi.
- **Files modified:** `tests/integration/test_billing_close.py`
- **Verification:** `unassigned_occupied` qatori AYNAN o'sha rastaga, dalil bilan; o'sha rasta `daily_charges` da YO'Q.
- **Committed in:** `3b65606`

**6. [Rule 2 - Missing Critical] `event_snapshots()` ommaviy qilindi — anomaliya dalili ikkinchi nusxadan olinmaydi**

- **Found during:** Task 1
- **Issue:** D-29 bo'yicha `unassigned_occupied` va `closed_day_occupied` `snapshot_id` **bilan** yoziladi, `write_anomaly()` esa uni dalilsiz `ValueError` bilan rad etadi. Kadrga yo'l `billing_repo._EVIDENCE_SNAPSHOTS` da yopiq edi — jobda ikkinchi so'rov yozish ikki nusxa tug'dirardi va anomaliya bilan hisob dalili bir kun BOSHQA kadrga ishora qilardi.
- **Fix:** `event_snapshots()` ommaviy funksiya; `write_evidence()` endi SHUNI chaqiradi (bitta manba, xulq o'zgarmagan).
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Committed in:** `851612c`

**7. [Rule 2 - Missing Critical] Kech tasdiq shoxi `no_coverage_only` da ISHLAMAYDI**

- **Found during:** Task 1
- **Issue:** Reja kech tasdiq shoxini «`billable` emas + hisob bor» deb ta'riflaydi. Bu ta'rif `no_coverage_only` holatini ham qamrardi — ya'ni zona arxivlangan yoki kamera o'chgan kuni tizim **avvalgi kunning tushumini** jimgina nolga tushirardi. Bu D-05 ning aynan teskarisi («ko'ra olmadik» ≠ «bo'sh»).
- **Fix:** Shox chaqiruv nuqtasi `no_coverage_only` shoxidan KEYIN turadi; sabab `_late_review()` docstringida O'LCHOV bilan yozilgan.
- **Files modified:** `services/core-api/app/jobs/billing_close.py`
- **Committed in:** `851612c`

**8. [Rule 2 - Missing Critical] `_PLATFORM_COMPONENTS` yangilandi + uchala locale matni**

- **Found during:** Task 3
- **Issue:** (a) `billing_close` `watched` ga qo'shilgan zahoti `test_alerting.py` ning guruhlash testlari `route.call_count == 1` da'vosida qizardi — **mahsulot to'g'ri ishlab turgan holda** (yurak urishi hali yozilmagan, ya'ni har yugurishda platforma alerti ochilardi). (b) `alert-row.tsx` ning `ALERT_TITLE_KEYS` reyestri xom kalitni ekranga chiqarmaydi — matnsiz `billing_close_stale` admin uchun «Kutilmagan xato» bo'lib ko'rinardi.
- **Fix:** (a) `_PLATFORM_COMPONENTS` ga `BILLING_CLOSE_COMPONENT` qo'shildi va SABAB fixture docstringida; (b) `alert-row.tsx` + uchala locale fayliga `alertKey.billingCloseStale`.
- **Files modified:** `tests/integration/test_alerting.py`, `frontend/src/components/snapshots/alert-row.tsx`, `frontend/messages/{uz-Latn,uz-Cyrl,ru}.json`
- **Verification:** `test_alerting.py` **14/14**, `test_capture_schedule.py` **23/23**. ⚠ Frontend darvozasi bu worktree'da **O'LCHANMADI** (pastdagi «Issues» bandiga qarang).
- **Committed in:** `f8c3b6f`

**9. [Rule 2 - Missing Critical] `0022` D-32 darvozasining yuzasiga qo'shildi**

- **Found during:** Task 1
- **Issue:** `test_no_migration_hard_codes_a_value_list` ning `_BILLING_MIGRATIONS` ro'yxati NOMMA-NOM (`0020`, `0021`). Yangi 6-faza migratsiyasi unga avtomatik kirmasdi va D-32 shu fayldan boshlab kuchsizlanardi.
- **Fix:** `"0022_billing_late_review.py"` ro'yxatga qo'shildi, sabab izohda.
- **Files modified:** `tests/tenancy/test_billing_domain_meta.py`
- **Committed in:** `851612c`

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **Uchta grep mezoni PROSE tufayli nolga teng emas** va bu `self_check.py:827-836` da o'rnatilgan qoidaning aynan o'zi («matn darvozasi sababni yozishga TO'SQINLIK QILMASLIGI kerak»): `business_today` → **1**, `write_app_audit` → **1**, `raise` → **2** — uchalasi ham **faqat docstringda**, taqiqning O'ZINI tushuntiruvchi matnda. Kod darajasidagi o'lchov AST bilan takrorlandi: `raise` bayonotlari **0**, `business_today` havolasi **yo'q**, `write_app_audit` havolasi **yo'q**.
- **`market_is_open()` chaqiruvi `_tenant_session()` ICHIDA** (reja qo'lda tekshirishni so'raydi): `_close_market()` avval `_tenant_session(...)` ochadi, so'ng `_market_open(session, ...)` ni chaqiradi — sessiya kontekst bilan. `grep -c market_is_open` → **5**.
- **Ikkinchi cron QO'SHILMADI** (A8): `worker.py` da `billing` so'zi 10 joyda uchraydi, `schedule=` bloki esa AYNAN BITTA (`grep -c 'task_name="billing.close"'` → **1**).
- **B bozoriga ham kadr yoziladi** (hodisasiz): `no_slot_rows` — BUTUN yugurishning sanog'i, ya'ni B materializatsiya qilinmasa u `day_close` dan keyin ham nolga tushmasdi va rejaning `no_slot_rows == 0` mezoni ifodalab bo'lmas bo'lardi.
- **`resolved_without_reviewer` faqat YANGI hisoblarga sanaladi** (reja «har hisob uchun» deydi): qayta yugurishda `skipped_existing` shoxi sanoqni oshirmaydi, ya'ni son «bugun nechta hisob nazoratchisiz yozildi» degan barqaror miqdor bo'lib qoladi.

---

**Total deviations:** 9 auto-fixed (2 blocking, 1 bug, 6 missing-critical) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Ikkitasi (1 va 2) **sxemaga tegdi** va ularsiz rejaning kech tasdiq shoxi yozilgan holda ham ishlamasdi. Bittasi (4) rejaning test farazini o'zgartirdi — mahsulot sharti bo'shatilmadi, test kunni o'zi qurdi. Yangi paket **o'rnatilmadi** (T-06-SC bajarildi), yangi marshrut ochilmadi, yangi `SECURITY DEFINER` funksiya qo'shilmadi.

## Issues Encountered

- **To'liq to'plamda 24 qizil — HAMMASI NVR SIMULYATORI GURUHIDA** (`test_nvr_discovery.py` 8, `test_nvr_discovery_job.py` 4, `test_nvr_errors.py` 5, `test_nvr_sim.py` 3, `test_phase3_criteria.py` 4). **Bu rejaning o'zgarishlariga aloqasi yo'q**: o'sha fayllarning birortasi ham `billing_close`, `alerting`, `self_check` yoki cron konstantalarini import qilmaydi. Sabab — 06-05/06-06 da ikki marta hujjatlashtirilgan ops holati: `sbozor-nvr-sim` konteyneri eskirgan. Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` **ishlatilmadi**). Shundan keyin o'sha besh fayl **78/78 yashil**. Repoga birorta o'zgarish kiritilmadi.
- **5-fazadan meros flaky test bu yugurishda QIZARMADI** (`test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`) — `deferred-items.md` dagi 1-band ochiq qoladi.
- **`gate` ning frontend yarmi bu worktree'da YUGURMAYDI** (`frontend/node_modules` yo'q). Bu reja uchala locale fayliga va `alert-row.tsx` ga matn qo'shdi, ya'ni frontend darvozalari **o'lchanmagan**. ⛔ Junction/symlink **YARATILMADI** (o'sha xatolik ilgari asosiy checkout'ni buzgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. Band `deferred-items.md` ga yozildi (3-qator).
- **`.env` va `ops/seaweedfs/s3.json` worktree'da yo'q edi** (06-04/06-05/06-06 dagi holatning takrori) — ikkalasi ham asosiy repodan **NUSXALANDI**, junction/symlink yaratilmadi.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_billing_close.py -q` | ✅ **7/7** |
| `pytest tests/integration/test_alerting.py -q` | ✅ **14/14** (13 mavjud + 1 yangi) |
| `pytest tests/integration/test_capture_schedule.py -q` | ✅ **23/23** (o'zgarishsiz — `never_seen` da'vosi reyestrdan HOSILA) |
| `pytest tests/unit/test_scheduler_observability.py -q` | ✅ **4/4** (yangi vazifa kuzatuv ilmog'ini buzmadi) |
| `pytest tests/integration/test_day_close.py -q` | ✅ **15/15** |
| `pytest tests/tenancy -q` | ✅ to'liq yashil (`test_billing_domain_meta.py` **13/13**) |
| `pytest tests/integration/test_billing_repo.py test_billing_immutable.py -q` | ✅ to'liq yashil |
| `pytest -q` (to'liq to'plam, **eskirgan** sim bilan) | ⚠ **24 qizil** — hammasi NVR sim guruhida (yuqoridagi bandga qarang) |
| Sim guruhining qayta yugurishi (5 fayl) | ✅ **78/78** simulyator qayta yaratilgandan keyin |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**307** fayl formatlangan, **298** fayl tiplangan) |

**Grep / o'lchov mezonlari:**

| Mezon | Kutilgan | O'lchov |
|---|---|---|
| `^import taskiq\|^from taskiq` (`billing_close.py`) | 0 | **0** |
| `active_market_ids` | ≥ 1 | **3** |
| `auth_list_markets_full\|occupancy_day_close_markets\|audit_draw_due_markets` | 0 | **0** |
| `market_is_open` | ≥ 1 | **5** |
| `late_review` | ≥ 1 | **9** |
| `type(exc).__name__` | ≥ 1 | **3** |
| `business_today` (KOD) | 0 | **0** (matnda 1) |
| `write_app_audit` (KOD) | 0 | **0** (matnda 1) |
| `raise` bayonotlari (AST) | 0 | **0** (matnda 2) |
| `billing_close.py` qatorlari | ≥ 280 | **648** |
| `BILLING_CLOSE_CRON == "10 4 * * *"` | rost | **rost** |
| `business_today() - timedelta(days=1)` (`worker.py`) | ≥ 2 | **2** |
| `task_name="billing.close"` | 1 | **1** |
| `BillingCloseResult` maydonlari | 11, `slots=True` | **11, `slots=True`** |
| `billing_close_stale` (`alerting.py`) | ≥ 1 | **2** |
| `BILLING_CLOSE_COMPONENT` (`alerting.py`) | ≥ 2 | **2** |
| `'billing_close' in EXPECTED_COMPONENTS` | rost | **rost** |
| `'day_close' in EXPECTED_COMPONENTS` | yolg'on | **yolg'on** |

## Known Stubs

Yo'q. Uchala yangi fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q.

⚠ **`billing_close_task` ning yagona iste'molchisi — planer**, ya'ni uni HTTP orqali qo'lda ishga tushirish yo'li 6-fazada ATAYIN yo'q (A8: kuniga bitta chaqiruv). Bu stub EMAS: qayta hisoblash yo'li mavjud va u `billing_close(sessionmaker, business_date=...)` ning ARGUMENTIDA yashaydi.

## Threat Flags

Yangi xavfsizlik yuzasi **ochilmadi**:

- Yangi tarmoq endpointi yoki autentifikatsiya yo'li **yo'q** (marshrutlar 06-08/06-09 da).
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**; bozorlar ro'yxati FAQAT `active_market_ids()` dan (T-06-37).
- Yangi paket **o'rnatilmadi** (T-06-SC).
- ⛔ **Threat register bo'yicha oltala `mitigate` bandi bajarildi**: T-06-37 (yagona RLS-chetlab o'tuvchi yuza + grep taqiqi), T-06-38 (`market_is_open()` tenant konteksti ostida + Pitfall 9 sabotaji o'lchandi), T-06-39 (har bozor alohida tranzaksiya, `SQLAlchemyError` yutiladi), T-06-40 (xato TURI; heartbeat `detail` da faqat butun sonlar — test buni TIP bo'yicha o'lchaydi, nom bo'yicha inkor bilan emas), T-06-41 (`EXPECTED_COMPONENTS` + `watched`, ikkalasi ham ALOHIDA sabotaj bilan), T-06-42 (`no_slot_rows` ajratilgan + ketma-ketlik testi).

⚠ **Sxema o'zgarishi (`0022`) yangi yuza EMAS, lekin QAYD ETILADI:** `charge_adjustments.actor_user_id` endi `NULL` bo'lishi mumkin. Bu **kengaytirish emas, toraytirish**: `NULL` faqat tizim yozgan qatorda uchraydi va u audit jurnalida `actor_kind = 'system'` bilan ajraladi (test buni o'lchaydi). Inson yozadigan yo'l (06-13 ning UI yuzasi, agar qo'shilsa) `actor_user_id` ni MAJBURIY qilib qolishi kerak — **marshrut qatlamida**, sxemada emas.

## User Setup Required

⛔ **Deploy paytida MAJBURIY** (yuqoridagi «Deploy» bo'limi): `docker compose up -d --force-recreate scheduler`.

⚠ Ops bandi (blokirovkasiz): `sbozor-nvr-sim` konteyneri eskirganda NVR guruhi qizaradi. Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` ishlatilmaydi).

## Next Phase Readiness

- **06-08/06-09 (marshrutlar):** job hech qanday marshrutga tegmaydi; `billing_repo` ga uchta yangi funksiya qo'shildi (`event_snapshots`, `market_day_charges`, `write_late_review_adjustment`) va ular `__all__` da. `write_evidence()` ning xulqi **o'zgarmadi** (faqat ichki so'rov umumiy funksiyaga ko'chdi).
- **06-10 (anomaliya hisoboti):** uchala `kind` ham ALOHIDA sanaladi va `billing_anomalies` da dalil juftligi (`occupancy_event_id`/`snapshot_id`) ikki yo'nalishda o'lchangan.
- **06-13 (tuzatish yuzasi, agar bo'lsa):** `charge_adjustments` ning tizim yo'li ISHLAB TURIBDI (`late_review`); inson yo'li qo'shilganda `actor_user_id` marshrut qatlamida MAJBURIY bo'lishi kerak — sabab yuqoridagi «Threat Flags» bandida.
- **06-12/06-14 (darvozalar):** `test_phase6_criteria.py` uchun G-2 invarianti («har yozilgan hisob uchun o'sha kunda slot qatori bor») endi **ifodalanadigan**: `PastDay` naqshi o'tmishdagi to'liq kunni quradi va hisob ham, slot ham AYNI kunga tegishli bo'ladi (06-06 uni «bu seedda ifodalab bo'lmaydi» deb qoldirgan edi).
- ⚠ **Ochiq band (bloklamaydi):** `gate` ning frontend yarmi yana o'lchanmadi; `day_close` ning yurak urishi ko'rligi `deferred-items.md` ning 2-bandi.

## Self-Check: PASSED

**Fayllar (4/4 mavjud):** `services/core-api/app/jobs/billing_close.py` (648 qator) · `tests/integration/test_billing_close.py` (974 qator) · `migrations/versions/0022_billing_late_review.py` (120 qator) · `.planning/phases/06-billing-va-kassir/deferred-items.md` (yangilandi)

**Commitlar (3/3 topildi):** `851612c` · `3b65606` · `f8c3b6f`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `billing_close.py` `min_lines: 280` | `wc -l` → **648** | ✅ |
| `billing_close.py` `contains: async def billing_close` | mavjud | ✅ |
| `test_billing_close.py` — Pitfall 2 + D-06 + D-10/D-28/D-05 | 7 test, hammasi nomlangan | ✅ |
| `key_links`: job → `retention.py::active_market_ids` | `grep -c` → **3** | ✅ |
| `key_links`: `BILLING_CLOSE_CRON` → `business_today() - timedelta` | qobiqda mavjud | ✅ |
| `key_links`: `EXPECTED_COMPONENTS` ↔ `alerting::watched` | ikkalasida ham `billing_close` | ✅ |

**`truths` (6/6):**
job ARGUMENTLI va `business_today()` ni CHAQIRMAYDI (AST bilan o'lchandi) ·
cron `day_close` DAN KEYIN va KECHAGI kunni yopadi (`"10 4 * * *"` + qobiq) ·
slot qatorlarisiz `charged = 0` VA `no_slot_rows = 8` VA `errors = []` — sukunat AJRALDI ·
bozorlar ro'yxati FAQAT `active_market_ids()` dan (taqiqlangan uchtasi grep → 0) ·
noaniq slotlar kunni BLOKLAMAYDI (`raise` bayonotlari → 0) va `resolved_without_reviewer` SANALADI (2 hisobdan 1 tasi) ·
yurak urishining YO'QLIGI IKKALA reyestrda ham ko'rinadi va har biri ALOHIDA sabotaj bilan o'lchandi.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-11*
