---
phase: 06-billing-va-kassir
plan: 05
subsystem: testing
tags: [pytest, testcontainers, postgres, pg_catalog, immutability-triggers, fixtures, sabotage]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "Olti billing jadvali, uch o'zgarmaslik qo'riqchisi va ularning SQLSTATE taksonomiyasi (`P0001` shartsiz / `23514` shartli)"
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "Yetti domen enumi — meta darvozasining KUTILMASI aynan shulardan iteratsiya bilan quriladi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`fixtures/occupancy_domain.py` (seed naqshi + `add_zone_with_event`), `app.jobs.day_close.day_close` (slotlarning YAGONA yozuvchisi), `test_occupancy_immutable.py` shabloni"
  - phase: 04-snapshot-quvuri
    provides: "`fixtures/snapshot_domain.py` (`SEED_BUSINESS_DATE`, `scheduled_at_for()`), `snapshots.is_billable` langari"
provides:
  - "`tests/fixtures/billing_domain.py` — olti jadvalli billing seedi; `stall_slot_occupancy` FAQAT `day_close` orqali to'ladi (C-3)"
  - "Seedning IKKI VARIANTI: `billing_domain_before_day_close` (slotlar YO'Q) va `billing_domain` (slotlar BOR) — Pitfall 2 ni o'lchanadigan qiladi"
  - "Fakt bo'yicha nomlangan olti rasta stsenariysi + yopiq kun holati + biriktirish bo'shlig'i"
  - "Qator yozuvchi yordamchilar: `add_daily_charge()`, `add_charge_evidence()`, `add_payment()`"
  - "`tests/tenancy/test_billing_domain_meta.py` — 13 sxema invarianti, hammasi `pg_catalog`/`information_schema` dan"
  - "`tests/integration/test_billing_immutable.py` — 12 xulq darvozasi, `sbozor_owner` roli bilan, soxta qatlamsiz"
  - "O'LCHANGAN TOPILMA: `shift_declaration_immutable()` ning `declared_soum`/`system_soum` shoxlari YETIB BO'LMAYDIGAN (juftlangan `CHECK` tufayli)"
  - "O'LCHANGAN TOPILMA: enum <-> DDL ajralishi YANGI bazada ifodalab bo'lmaydi (yagona manba) — `test_no_migration_hard_codes_a_value_list` shuni qo'riqlaydi"
affects: [06-06, 06-07, 06-08, 06-09, 06-10, 06-12, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Seed MAHSULOT YO'LINI CHAQIRADI: hosila jadval qatorlarini seed o'zi yozmaydi, u job'ni (`day_close`) chaqiradi — aks holda «job yugurdi, hech nima yozmadi» sinfi testda ko'rinmaydi"
    - "Seed IKKI VARIANTDA beriladi (job'gacha / job'dan keyin) — bittasi bilan «hali yugurmagan» va «yugurdi, natijasiz» holatlari AJRALMAYDI"
    - "Sabotaj YASHIL qolganda da'vo SUSAYTIRILMAYDI, IKKIGA BO'LINADI: sabab o'lchanadi va yangi test o'sha sababning O'ZINI (mexanizmni) qo'riqlaydi"
    - "Chuqurlikdagi himoyani «o'lik kod» deb o'chirmaslik uchun uning YETIB BO'LMASLIGI docstringda O'LCHOV bilan yoziladi (qaysi sabotaj qizardi, qaysi biri yo'q)"
    - "Fixture'ning qator yozuvchi yordamchilari SEEDGA QO'SHILMAYDI — so'ralganda chaqiriladi, aks holda job'ning idempotentlik testi jimgina trivial bo'ladi"

key-files:
  created:
    - tests/fixtures/billing_domain.py
    - tests/tenancy/test_billing_domain_meta.py
    - tests/integration/test_billing_immutable.py
  modified: []

key-decisions:
  - "06-05: Seed O'ZI `capture_runs` + `snapshots` qatori yozadi — `A_RUN_PLAN` A bozoriga BITTA yaroqli kadr beradi, ya'ni `stall_with_two_occupied_slots` (BILL-01 ning kirish holati) mavjud seed bilan IFODALAB BO'LMASDI"
  - "06-05: Hisob/to'lov qatorlarining `service_date` i `CURRENT_DATE - 1` dan olinadi, `SEED_BUSINESS_DATE` DAN EMAS — `ck_daily_charges_service_date_not_in_future` `business_date` (bugun) bilan cheklaydi, qadalgan 2026-09-01 esa kelajakda bo'lishi mumkin"
  - "06-05: G-3 ning ruxsat etilgan tip to'plami O'LCHOVDAN olindi: `boolean` CHIQARILDI (oltala jadvalda bayroq ustuni yo'q), `time without time zone` QO'SHILDI (`charge_evidence.slot_time`)"
  - "06-05: Xulq darvozasi seedning `before_day_close` variantida yuguradi (qo'riqchilar slotlarga tegmaydi); `billing_domain` varianti ALOHIDA testda o'lchanadi, aks holda u sinalmagan holda ship bo'lardi"
  - "06-05: `shift_declaration_immutable()` ning `declared_soum`/`system_soum` shoxlari YETIB BO'LMAYDIGAN — D-25 ni AMALDA `OLD.status = 'closed'` shoxi + `ck_cashier_shifts_closed_has_declaration` ushlaydi (S-B/S-B2 bilan o'lchandi)"
  - "06-05: Enum <-> DDL ajralishi YANGI bazada IFODALAB BO'LMAYDI (`0020` `*_CHECK` ni enumdan hosila konstantadan import qiladi) — shuning uchun darvoza IKKINCHI NUSXANING TUG'ILISHINI bloklaydi"

patterns-established:
  - "Yangi domen seedi uchun: modul docstringining BIRINCHI bandi hosila qatorlar QAYSI mahsulot yo'lidan yozilishini va SABABINI yozadi; `INSERT INTO <hosila jadval>` matni faylda grep bilan taqiqlanadi"
  - "Meta darvozasining kutilmasi ENUMDAN ITERATSIYA bilan quriladi (`tuple(m.value for m in <Enum>)`), qo'lda ko'chirilgan literal ro'yxat TAQIQLANADI"
  - "Har juftlangan `CHECK` IKKI TOMONGA o'lchanadi va IMPLIKATSIYA shakli (`OR`) alohida rad etiladi — `payments` da ataylab implikatsiya shaklidagi uchinchi `CHECK` ham borligi uchun nom bo'yicha ajratiladi"
  - "Xulq darvozasida har rad etish SQLSTATE ni OCHIQ solishtiradi; istisno klassi nomi bilan kifoyalanish shaklning jimgina almashtirilishini sezmaydi"

requirements-completed: [BILL-01, BILL-02, CASH-03, CASH-04]

# Metrics
duration: 155min
completed: 2026-08-10
---

# Phase 6 Plan 05: Billing seedi, sxema meta darvozasi va o'zgarmaslik xulqi Summary

**`0020` ning kafolatlari endi «ishlaydi deb» qabul qilinmaydi: seed slot qatorlarini `day_close` ORQALI tug'diradi (C-3), 13 meta darvoza sxemani `pg_catalog` dan o'lchaydi va 12 xulq darvozasi uchala qo'riqchini `sbozor_owner` roli bilan haqiqiy `postgres:18.4` da sinaydi — beshta sabotajning uchtasi qizardi, ikkitasi YASHIL QOLDI va har ikkalasining sababi o'lchanib, da'vo kengaytirildi.**

## Performance

- **Duration:** 155 min
- **Started:** 2026-08-10T19:35:00Z
- **Completed:** 2026-08-10T22:10:00Z
- **Tasks:** 3
- **Files modified:** 3 (uchalasi ham YANGI; mavjud birorta fayl tahrirlanmadi)

## Accomplishments

- **C-3 mexanik qulfga aylandi.** Seed `stall_slot_occupancy` ga birorta qator yozmaydi — u `snapshots` + `occupancy_events` ni yozib, `await day_close(...)` ni CHAQIRADI. Ya'ni «job yuguradi, `errors` bo'sh, `charged = 0`» (Pitfall 2) holati endi testda IFODALANADIGAN.
- **Ikki variant Pitfall 2 ni ko'rinadigan qildi.** `billing_domain_before_day_close` dan keyin slot sanog'i **0**, `billing_domain` dan keyin **> 0** — ikkalasi ham fixture ichida NAZORAT ASSERTI bilan o'lchanadi, ya'ni seed o'z va'dasini o'zi tekshiradi.
- **Olti rasta stsenariysi HAQIQATAN materializatsiya qilindi** (`day_close` chiqishidan o'lchandi): ikki band slot → **2**, bitta AI band slot → **1**, inson tasdiqlagan → **1** (manba `human`), qamrovsiz → `('no_coverage', 'no_coverage')`, biriktirilmagan band rasta → 1 band slot va `period @> D` bo'yicha **0** biriktirish, yopiq kunda band → `('occupied', 'ai')`.
- **Sxema invariantlari enumdan HOSILA.** `ENUM_BACKED_COLUMNS` kutilmani `tuple(m.value for m in <Enum>)` bilan quradi; sakkiz ustun, yetti enum (`AdjustmentReason` ikki ustunni oziqlantiradi).
- **Beshta sabotaj bajarildi va IKKITASI YASHIL QOLDI** — ikkalasi ham o'lchandi, sababi topildi va HAR IKKALASI YANGI TEST TUG'DIRDI (pastdagi «Sabotaj» bo'limi).
- **To'liq to'plam yashil** va lint/format/mypy toza (302 fayl formatlangan, 293 fayl tiplangan).

## Task Commits

1. **Task 1: `tests/fixtures/billing_domain.py` — olti jadval seedi, slotlar `day_close` orqali** — `920593b` (test)
2. **Task 2: `test_billing_domain_meta.py` — sxema invariantlari `pg_catalog` dan** — `44d50e0` (test)
3. **Task 3: `test_billing_immutable.py` — o'zgarmaslikning xulqiy darvozasi** — `7b2f492` (test)

## Files Created/Modified

- `tests/fixtures/billing_domain.py` (**yangi**, 1367 qator) — ikki bozorli billing seedi. Tarif zanjiri (15 000 @ `valid_from <= D`, 20 000 @ `D + 1`), olti rasta stsenariysi, yopiq kun istisnosi, kassir smenasi, ikkinchi yaroqli kadr, ikki variant va uch qator yozuvchi yordamchi.
- `tests/tenancy/test_billing_domain_meta.py` (**yangi**, 837 qator) — 13 meta darvoza; model IMPORT QILINMAYDI (bazadagi haqiqiy holat o'lchanadi), enum esa ATAYIN import qilinadi (kutilma undan hosila).
- `tests/integration/test_billing_immutable.py` (**yangi**, 876 qator) — 12 xulq darvozasi, olti guruh; `sbozor_owner` ulanishi, soxta qatlam yo'q, har rad etish SQLSTATE bilan.

## Sabotaj (D-30) — BESHTA URINISH, HAR BIRINING NATIJASI

| # | Sabotaj | Natija | Xulosa |
|---|---|---|---|
| **S-A** | `ALTER TABLE daily_charges DISABLE TRIGGER trg_charge_immutable` — ⛔ **o'lchanayotgan bazaning O'ZIDA**, sessiya ichida | 🔴 **QIZARDI** | `test_a_written_charge_cannot_be_edited_or_deleted` yiqildi. 05-11 darsi bajarildi: sabotaj sistemaga YETIB BORDI. |
| **S-B** | `shift_declaration_immutable()` dan `declared_soum` sharti OLIB TASHLANDI | 🟢 **YASHIL QOLDI** | **TOPILMA** — pastga qarang. |
| **S-B2** | S-B ustiga `OLD.status = 'closed'` shoxi ham olib tashlandi | 🔴 **QIZARDI** (`DID NOT RAISE CheckViolation`) | Yukni AYNAN `status` shoxi ko'taradi. |
| **S-C** | `enums.py::ReversalReason` ga beshinchi a'zo qo'shildi (migratsiyasiz) | 🟢 **YASHIL QOLDI** | **TOPILMA** — pastga qarang. |
| **S-C+** | Kuchaytirilgan sabotaj: `0020` ga qo'lda `sa.CheckConstraint("kind IN ('payment', 'reversal')")` yozildi | 🔴 **QIZARDI** | Yangi 13-test ishlaydi. |
| **S-D** | `OVERRIDE_IS_PAIRED_CHECK` juftlangan tenglikdan `OR` (implikatsiya) shakliga o'tkazildi, migratsiya qayta yugurdi | 🔴 **QIZARDI** | `test_quote_pairing_check_exists` yiqildi. |

Uchala sabotaj ham qaytarildi; `git status` toza (`git checkout -- migrations/entities/triggers.py` bilan tiklandi, boshqalari qo'lda).

### TOPILMA 1 (S-B): shartli qo'riqchining ikki shoxi YETIB BO'LMAYDIGAN

`shift_declaration_immutable()` ning `declared_soum` shoxi sharti — `OLD.declared_soum IS NOT NULL`.
`ck_cashier_shifts_closed_has_declaration` esa `(status = 'closed') = (declared_soum IS NOT NULL)` ni
majburlaydi. Ya'ni `OLD.declared_soum IS NOT NULL` ⟹ `OLD.status = 'closed'` ⟹ **birinchi shox
allaqachon rad etgan**. `system_soum` shoxi ham aynan shu sinfda.

**Da'vo susaymadi, u KENGAYTIRILGAN HOLATGA ko'chdi:** yangi
`test_an_open_shift_cannot_carry_a_declaration` o'lchaydi — OCHIQ smenaga deklaratsiya yozish
`ck_cashier_shifts_closed_has_declaration` bilan **rad etiladi** (`23514`) va qator o'zgarmaydi.
Ya'ni D-25 ikki mexanizmdan keladi va ular ALMASHTIRILADIGAN emas, KETMA-KET:
(a) yopilgan smenaga har qanday `UPDATE` rad etiladi (trigger); (b) ochiq smenaga deklaratsiya
umuman yozib bo'lmaydi (`CHECK`). S-B2 birinchisining yuk ko'tarishini isbotladi.

⛔ Ikki shox **«o'lik kod» deb OLIB TASHLANMAYDI** va sabab test docstringida yozilgan: `CHECK` bir
kun bo'shatilsa (masalan ochiq smenaga oraliq deklaratsiya ruxsat etilsa) ular DARHOL yuk
ko'taradigan bo'lib qoladi.

### TOPILMA 2 (S-C): enum <-> DDL ajralishi YANGI bazada ifodalab bo'lmaydi

Sabotaj sistemaga **yetib bordi** (konteynerda `sbozor_core` `/app/packages/...` dan import
qilinadi; enum 5 a'zo bilan o'qildi — mexanik tekshirildi). Test baribir yashil qoldi, chunki
`0020_billing_domain.py` `REVERSAL_REASON_CHECK` ni `sbozor_core.models.billing` DAN import
qiladi, u esa f-string bilan **enumdan** quriladi. Ya'ni `alembic upgrade head` yugurganda `CHECK`
ham besh qiymat bilan tug'iladi — **ikkala tomon ham AYNI manbadan keladi**.

Bu 05-15 ning S-D darsining aynan takrori: sabotaj sistemaga yetib bordi, lekin test tanlagan
MA'LUMOT ikkala shoxda bir xil natija berdi.

**Da'vo IKKIGA BO'LINDI:**
- `test_every_check_is_derived_from_enum` — MAVJUD bazaning enumdan ajralishini ushlaydi (qo'lda
  `ALTER TABLE`, konstraytni qayta ta'riflagan keyingi migratsiya, restore qilingan eski sxema);
- **YANGI** `test_no_migration_hard_codes_a_value_list` — IKKINCHI NUSXANING TUG'ILISHINI
  bloklaydi. Naqsh SHAKLGA yozilgan (`IN ('` / `ANY (ARRAY[`), NOMGA emas, va naqshning O'ZI
  pozitiv/negativ nazorat bilan sinaladi (06-04 ning `DERIVED_ORDER_PATTERN` qoidasi).
  ⚠ Bitta qiymatli `server_default=sa.text("'open'")` ONGLI ravishda yuzadan tashqarida — u
  a'zolik TO'PLAMINI takrorlamaydi, ya'ni «yangi a'zo» holatida jimgina eskirmaydi. `0020` da ayni
  ikkita shunday qiymat bor (`cashier_shifts.status`, `payments.kind`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi (06-04 dagi holatning takrori)**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da va worktree ularsiz yaratilgan.
- **Fix:** Ikkala fayl asosiy repodan **NUSXALANDI**. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

**2. [Rule 1 - Bug] Rejadagi verify buyrug'i `&&` bilan zanjirlanган va u HAR DOIM yiqiladi**

- **Found during:** Task 1
- **Issue:** `pytest tests/fixtures -q --collect-only && pytest tests/integration/test_day_close.py -q` — birinchi buyruq **exit 5** (`no tests collected`) qaytaradi, chunki `tests/fixtures/` da test YO'Q (u fixture katalogi). Zanjir ikkinchi buyruqqa umuman yetmaydi.
- **Fix:** Ikkala buyruq **alohida** yugurtirildi. Import xatosiz (`--collect-only` toza chiqdi), `test_day_close.py` **15/15 yashil**.
- **Verification:** Ikkalasi ham alohida bajarildi va natijalari «Verification» jadvalida.
- **Committed in:** — (buyruq, kod emas)

**3. [Rule 2 - Missing Critical] Seed IKKINCHI yaroqli kadr yozishi SHART edi**

- **Found during:** Task 1
- **Issue:** `snapshot_domain.A_RUN_PLAN` A bozoriga ikki kadr beradi va ulardan faqat BITTASI `quality_verdict = 'ok'`; ikkinchisi `dark`, ya'ni unga bandlik hodisasi umuman yozib bo'lmaydi (D-21 langari). Ya'ni bir rasta ENG KO'PI BILAN bitta slotda band bo'la olardi va rejaning `stall_with_two_occupied_slots` fixture'i — BILL-01 ning butun sharti — **ifodalab bo'lmasdi**.
- **Fix:** Seed IKKINCHI kameraga, IKKINCHI slotga o'z `capture_runs` + `snapshots` juftligini yozadi (`_add_billable_frame()`). ⛔ `A_RUN_PLAN` ga qator QO'SHILMADI: u `snapshot_domain` ning barcha sanoq testlarini jimgina siljitardi.
- **Files modified:** `tests/fixtures/billing_domain.py`
- **Verification:** `day_close` chiqishidan o'lchandi — o'sha rasta uchun `occupied` slotlar soni **2**.
- **Committed in:** `920593b`

**4. [Rule 2 - Missing Critical] Hisob sanasi `SEED_BUSINESS_DATE` DAN OLINMAYDI**

- **Found during:** Task 1 (yordamchilar)
- **Issue:** `ck_daily_charges_service_date_not_in_future` `service_date <= business_date` ni talab qiladi, `business_date` esa `created_at` DAN HOSILA — ya'ni HAR DOIM «bugun». `SEED_BUSINESS_DATE` (2026-09-01) qadalgan sana va u bugundan KEYIN bo'lishi mumkin; o'shanda har `INSERT` `CheckViolation` bilan yiqilardi va sabab «konstrayt buzuq» kabi ko'rinardi.
- **Fix:** `_safe_service_date()` — `CURRENT_DATE - 1`. Shakl 06-04 da o'lchangan (`test_market_delete_guard.py:615-620`): `business_date` `Asia/Tashkent` da hisoblanadi, ya'ni u UTC `CURRENT_DATE` dan hech qachon kichik emas.
- **Files modified:** `tests/fixtures/billing_domain.py`
- **Verification:** `test_billing_immutable.py` ning oltala guruhi ham hisob/to'lov yozadi — hammasi yashil.
- **Committed in:** `920593b`

**5. [Rule 1 - Bug] G-3 ning ruxsat etilgan tip to'plami rejada NOTO'G'RI yozilgan**

- **Found during:** Task 2
- **Issue:** Reja to'plamni `{uuid, bigint, date, text, timestamp with time zone, boolean}` deb yozgan. Amalda: (a) oltala jadvalning birortasida ham `boolean` ustun **YO'Q** (holat `text` + enumdan hosila `CHECK` bilan ifodalanadi); (b) `charge_evidence.slot_time` `time without time zone` va u ro'yxatda **yo'q edi**. Rejadagi to'plam bilan darvoza DARHOL qizarardi.
- **Fix:** To'plam O'LCHOVDAN olindi. `boolean` chiqarildi va uning **yo'qligi ONGLI fakt** sifatida konstanta docstringida yozildi («har ehtimolga qarshi qo'shish `is_closed`/`is_reversed` bayrog'iga yo'l ochardi»); `time without time zone` sabab bilan qo'shildi.
- **Files modified:** `tests/tenancy/test_billing_domain_meta.py`
- **Verification:** `test_billing_columns_use_only_allowed_types` yashil; solishtiruv `==` bilan (`not in` emas).
- **Committed in:** `44d50e0`

**6. [Rule 2 - Missing Critical] S-C yashil qolgach 13-test qo'shildi**

- **Found during:** Task 2 (sabotaj bosqichi)
- **Issue:** «Enumga a'zo qo'shildi, migratsiya yozilmadi» sabotaji yashil qoldi va D-30 bunday holatda da'voni KUCHAYTIRISHNI talab qiladi.
- **Fix:** `test_no_migration_hard_codes_a_value_list` qo'shildi (yuqoridagi TOPILMA 2). Naqshning O'ZI pozitiv/negativ nazorat bilan sinaladi.
- **Files modified:** `tests/tenancy/test_billing_domain_meta.py`
- **Verification:** Kuchaytirilgan sabotaj (`0020` ga qo'lda `IN (...)`) **QIZARDI**.
- **Committed in:** `44d50e0`

**7. [Rule 2 - Missing Critical] S-B yashil qolgach yangi xulq testi qo'shildi**

- **Found during:** Task 3 (sabotaj bosqichi)
- **Issue:** `declared_soum` shoxini olib tashlash hech nimani qizartirmadi (TOPILMA 1).
- **Fix:** `test_an_open_shift_cannot_carry_a_declaration` qo'shildi — D-25 ning IKKINCHI mexanizmi (`CHECK`) endi ochiq o'lchanadi.
- **Files modified:** `tests/integration/test_billing_immutable.py`
- **Verification:** Test yashil; S-B2 birinchi mexanizmning yuk ko'tarishini isbotladi.
- **Committed in:** `7b2f492`

**8. [Rule 2 - Missing Critical] Seedning `billing_domain` varianti SINALMAGAN holda qolardi**

- **Found during:** Task 3
- **Issue:** Beshala rejalashtirilgan guruh `before_day_close` variantida yuguradi. Agar `day_close` chaqiradigan variant birorta testda ishlatilmasa, u shu rejadan **sinalmagan** holda chiqardi va C-3 ning butun mexanizmi faqat kelajakdagi rejada birinchi marta yugurardi (stub sinfidagi xavf).
- **Fix:** Oltinchi guruh qo'shildi — `test_the_evidence_chain_needs_materialised_slots`: `billing_domain` varianti ustida dalil zanjiri (`charge_evidence -> stall_slot_occupancy -> occupancy_events -> snapshots`) yoziladi va `is_billable` bilan `verdict` o'lchanadi.
- **Files modified:** `tests/integration/test_billing_immutable.py`
- **Verification:** Test yashil; `slot_count(...) > 0` nazorat asserti bilan.
- **Committed in:** `7b2f492`

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **Rasta indekslari.** Reja «to'rt rasta + beshinchi + oltinchi» deydi, indekslarni bermaydi. Tanlov NOMMA-NOM qilindi va sabab kodda yozildi: `stall_ids[0]` (inson tasdiqlagan — `occupancy_domain` DAN keladi), `[1]` (yopiq kun), `[2]` (qamrovsiz — unga zona QO'SHILMAYDI), `[3]` (ikki slot), `[4]` (bitta AI slot), `[5]` (biriktirish bo'shlig'i).
- **Smenaning ikkinchi `UPDATE` i `RaiseException` emas, `CheckViolation`.** Reja qabul mezoni `RaiseException` deb yozgan; 06-04 ning o'lchangan taksonomiyasi bo'yicha SHARTLI qo'riqchi `23514` beradi. Test kuchliroq shaklda yozildi — u **SQLSTATE ni** solishtiradi.
- **`no_coverage` rastaga tarif berilmadi** (reja «tarif zanjiri» ni umumiy aytadi): qamrovsizlik anomaliyasi tarifga umuman tayanmaydi va unga toifa berish «tarif yo'q» shoxini seedda o'chirib qo'yardi.

---

**Total deviations:** 8 auto-fixed (1 blocking, 2 bug, 5 missing-critical) + 3 reja matnining aniqlashtirilishi
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Yangi paket **o'rnatilmadi** (T-06-SC bandi bajarildi), mavjud birorta fayl **tahrirlanmadi** — uchala fayl ham YANGI. Ikki qo'shimcha test (6 va 7-deviatsiya) D-30 ning O'Z talabidan tug'ildi.

## Issues Encountered

- **To'liq to'plamning BIRINCHI yugurishida 4 test qizil edi** — `test_rtsp_source.py` (3) va `test_live_view_e2e.py` (1), hammasi `ConnectionRefusedError: ('172.19.0.4', 554)`. **Bu rejaning o'zgarishlariga aloqasi yo'q** (u birorta NVR/RTSP fayliga tegmaydi) va ikkala fayl uchala yangi faylni ham import qilmaydi. Sabab o'lchandi: `sbozor-nvr-sim-1` qayta yaratilgan (yangi IP), `sbozor-nvr-sim-rtsp-1` esa 2 soatlik eski konteyner bo'lib qolgan — kashf qilingan RTSP manzili eskirgan. `docker compose --profile sim up -d --force-recreate nvr-sim-rtsp` bilan tuzatildi (⛔ `-v` **ishlatilmadi**), o'sha 4 test **yashil** bo'ldi va to'liq to'plam qayta yugurtirilib **to'liq yashil** chiqdi. Repoga birorta o'zgarish kiritilmadi.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q. ⛔ Junction/symlink **YARATILMADI** (bu ilgari asosiy checkout'ni buzgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. **Bu reja birorta frontend fayliga tegmaydi.** `gate` ning to'liq vaqtini o'lchash keyingi to'lqinga qoldirildi.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/fixtures -q --collect-only` | ✅ import xatosi yo'q (test yo'q — exit 5, kutilgan) |
| `pytest tests/integration/test_day_close.py -q` | ✅ **15/15** (seed uni buzmagan) |
| `pytest tests/tenancy/test_billing_domain_meta.py -q` | ✅ **13/13** |
| `pytest tests/tenancy -q` | ✅ **to'liq yashil** |
| `pytest tests/integration/test_billing_immutable.py -q` | ✅ **12/12** |
| `pytest -q` (to'liq to'plam) | ✅ **to'liq yashil** (`sim` profili ko'tarilgan holda) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**302** fayl formatlangan, **293** fayl tiplangan) |

**Seedning DB darajasidagi o'lchovlari** (`day_close` chiqishidan, A bozori, `D = 2026-09-01`):

| Da'vo | O'lchov |
|---|---|
| `billing_domain_before_day_close` dan keyin slot soni | **0** (fixture ichida nazorat asserti bilan) |
| `billing_domain` dan keyin slot soni (D) | **> 0** (`day_close`: `slots=14, stalls=8, no_coverage=7, default_empty=1, errors=0`) |
| `billing_domain` dan keyin slot soni (yopiq kun) | **> 0** (`slots=6, errors=0`) |
| `stall_with_two_occupied_slots` band slotlari | **2** |
| `stall_with_one_ai_occupied_slot` band slotlari | **1** |
| `stall_with_one_human_confirmed_occupied_slot` | **1**, manba `human` |
| `stall_with_only_no_coverage_slots` | `('no_coverage', 'no_coverage')`, band slot **yo'q** |
| `stall_occupied_without_assignment` | 1 band slot; `period @> D` bo'yicha **0** biriktirish |
| `stall_occupied_on_a_closed_day` (yopiq kunda) | `('occupied', 'ai')` |
| Tarif zanjiri | `[(2026-08-01, 15000), (2026-09-02, 20000)]` |
| Kalendar istisnosi | `CLOSED_BUSINESS_DATE` uchun `is_open = false`, **1 qator** |

**Grep mezonlari:**
`grep -c "await day_close(" billing_domain.py` → **2** (≥ 1) ·
`grep -cE "INSERT INTO stall_slot_occupancy|StallSlotOccupancy\(" billing_domain.py` → **0** ·
`grep -c "def billing_domain_before_day_close" billing_domain.py` → **1** ·
`grep -c cashier billing_domain.py` → **32** (≥ 1) ·
`grep -c 'roles=\["cashier"\]' billing_domain.py` → **0** (yangi kassir yaratilmadi) ·
`grep -cE "for .* in (PaymentKind|...|ShiftStatus)" test_billing_domain_meta.py` → **8** (≥ 1) ·
`grep -ciE "mock|monkeypatch|MagicMock|unittest" test_billing_immutable.py` → **0** ·
`grep -c RaiseException test_billing_immutable.py` → **7** ·
`assert` / `pytest.raises` nuqtalari soni → **67** (≥ 14).

## Known Stubs

Yo'q. Uchala fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q.

⚠ **Fixture yuzasining ikki qismi ATAYIN «hozircha bir chaqiruvchili»** va ular stub EMAS:
`add_charge_evidence()` bitta testda (`test_the_evidence_chain_needs_materialised_slots`), `add_payment()`
esa uchta testda ishlatiladi. Ikkalasi ham 06-06 (`billing_repo`) va 06-09 (`POST /payments`)
rejalarining bevosita talabi va ularning shakli shu yerda xulq bilan sinalgan — ya'ni keyingi reja
ularni «ishlaydi deb» qabul qilmaydi. `billing_domain` (async) varianti ham 8-deviatsiya
tufayli sinalgan holda ship bo'lyapti.

## Threat Flags

Yangi xavfsizlik yuzasi **ochilmadi**:

- Bu reja faqat **test qatlamiga** tegadi — yangi tarmoq endpointi, autentifikatsiya yo'li, fayl kirishi yoki sxema o'zgarishi **yo'q**.
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**.
- Yangi paket **o'rnatilmadi** (T-06-SC).
- ⛔ Threat register bo'yicha **beshala `mitigate` bandi bajarildi**: T-06-25 (xulq darvozasi `sbozor_owner` bilan + nazorat holati + S-A), T-06-26 (shartli qo'riqchining chegarasi hujjatlashtirildi + S-B/S-B2), T-06-27 (audit assimetriyasi IKKI yo'nalishda), T-06-28 (slotlar `day_close` orqali, qo'lda `INSERT` grep bilan taqiqlangan), T-06-29 (`UniqueViolation` xulq bilan + yopilgandan keyingi nazorat).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): `sbozor-nvr-sim-rtsp` konteyneri `nvr-sim` qayta yaratilganda ESKIRIB
qoladi va RTSP testlari `ConnectionRefused` beradi. Tuzatish: `docker compose --profile sim up -d
--force-recreate nvr-sim-rtsp` (⛔ `-v` ishlatilmaydi).

## Next Phase Readiness

- **06-06 (`billing_repo`):** seed tayyor va u MAHSULOT yo'lidan yuradi. `billing_domain` varianti
  materializatsiya qilingan slotlar bilan keladi, `before_day_close` esa Pitfall 2 ni o'lchash
  uchun. FIFO taqsimlash testlari `add_payment()` ni `kind`/`service_date` bilan chaqira oladi.
- **06-08 (`billing_close`):** SC#1 ning uchala holati (2 slot / 1 AI slot / 1 inson slot) seedda
  MATERIALIZATSIYA QILINGAN va o'lchangan; D-05 (qamrovsiz), D-10 (yopiq kun) va BILL-04/D-28
  (biriktirish bo'shlig'i) ham kirish holati bilan tayyor. `no_coverage` rastaga tarif ATAYIN
  berilmagan — «tarif yo'q» shoxi ham sinaladi.
- **06-09 (`POST /payments`):** o'zgarmaslik va storno yo'li xulq bilan qulflangan; `add_payment()`
  `override_reason` ni ham qabul qiladi, ya'ni D-19 ning 422 yo'li seedni qayta yozmasdan
  sinaladi.
- **06-12/06-14 (darvozalar):** `tests/tenancy` to'liq yashil; 13 meta darvoza va 12 xulq darvozasi
  qo'shildi. G-2 (`daily_charges.service_date` ↔ slot mosligi) HALI YOZILMAGAN — u
  `test_phase6_criteria.py` ning ishi (06-14).
- ⚠ **Ochiq band (bloklamaydi):** `gate` ning to'liq vaqti bu to'lqinda O'LCHANMADI (frontend yarmi
  worktree'da yugurmaydi). `06-VALIDATION.md` byudjeti (1250 s) keyingi to'lqinda tinch xostda
  qayta o'lchanishi kerak — backend yarmi bu rejada ~25 daqiqa oldi, lekin o'lchov `sim` profili
  ko'tarilgan va boshqa konteynerlar ishlab turgan xostda olingan, ya'ni u BYUDJET o'lchovi EMAS.

## Self-Check: PASSED

Har bir da'vo mexanik tekshirildi.

**Fayllar (3/3 mavjud):** `tests/fixtures/billing_domain.py` (52 463 bayt) ·
`tests/tenancy/test_billing_domain_meta.py` (36 878 bayt) ·
`tests/integration/test_billing_immutable.py` (37 371 bayt)

**Commitlar (3/3 topildi):** `920593b` · `44d50e0` · `7b2f492`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `billing_domain.py` `provides`: olti jadval seedi + `day_close` orqali materializatsiya | `grep -c "await day_close("` → **2** | ✅ |
| `billing_domain.py` `contains: day_close` | mavjud (import + ikki chaqiruv) | ✅ |
| `test_billing_domain_meta.py` — `pg_catalog` dan sxema invariantlari | 13 test, hammasi yashil | ✅ |
| `test_billing_immutable.py` — xulq darvozasi, `sbozor_owner`, soxta qatlam YO'Q | 12 test; `grep -ciE "mock\|monkeypatch"` → **0** | ✅ |
| `key_links`: seed → `app.jobs.day_close.day_close` (`await day_close\(`) | **2 ta chaqiruv** (D va yopiq kun) | ✅ |
| `key_links`: xulq darvozasi → uch trigger (`RaiseException`) | `grep -c RaiseException` → **7** | ✅ |

**`truths` (4/4):**
slot qatorlari `day_close` ORQALI yoziladi, qo'lda `INSERT` faylda **yo'q** ·
`UPDATE`/`DELETE daily_charges` faol bozorda **rad etiladi** va rad etilgan `UPDATE` `audit_log` ga
qator **qoldirmaydi** ·
`UPDATE payments` **rad etiladi**; `open -> closed` **ruxsat**, ikkinchi `UPDATE` **rad** ·
har juftlangan `CHECK` **ikki tomonga** o'lchangan (buzilishi va qonuniy holati).

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
