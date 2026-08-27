---
phase: 06-billing-va-kassir
plan: 06
subsystem: billing
tags: [repository, sqlalchemy, postgres, lateral-join, idempotency, fifo-allocation, sabotage]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 01
    provides: "Sof qoidalar — `billable_from_slots()`, `allocate_charge_credit()` (`FIFO_OLDEST_SERVICE_DATE_FIRST`), `total_due_soum()`, `ChargeDue`/`ChargeCreditAllocation`"
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`AMOUNT_UNAVAILABLE_REASONS` yopiq to'plami + `MARKET_CLOSED`/`TARIFF_MISSING` konstantalari; domen enumlari"
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "Olti billing jadvali, `uq_daily_charges_market_id_stall_id_service_date` idempotentlik kaliti, `charge_evidence` kompozit FK zanjiri, `billing_anomalies` juftlangan `CHECK` lari"
  - phase: 06-billing-va-kassir
    plan: 05
    provides: "`tests/fixtures/billing_domain.py` — olti rasta stsenariysi, ikki tarifli zanjir, yopiq kun, biriktirish bo'shlig'i; slotlar `day_close` ORQALI"
  - phase: 02-bozor-domeni
    provides: "`stall_repo.py:602-629` uch LATERAL naqshi, `market_is_open()` DB funksiyasi, `stalls.code_sort`, `periods.py` ning `[)` konventsiyasi"
provides:
  - "`services/core-api/app/repositories/billing_repo.py` — yetti funksiya: `resolve_stall_day_money()`, `billable_stalls()`, `write_charge()`, `write_evidence()`, `write_anomaly()`, `vendor_outstanding()`, `vendor_charge_allocation()`, `pending_projection()`"
  - "`StallDayMoney` / `SlotEvidenceRow` / `StallSlotVerdict` / `PendingStall` / `PendingMarket` / `PendingProjection` natija tiplari"
  - "`tests/integration/test_billing_repo.py` — 30 xulq darvozasi haqiqiy `postgres:18.4` da, soxta qatlamsiz"
  - "O'LCHANGAN SABOTAJ: G-6 (C-6 predikati) — holat (2) QIZARDI, (1) va (3) yashil qoldi"
  - "O'LCHANGAN SABOTAJ: D-24 LIFO — repo qatlamida YASHIL (kutilgan), sof funksiya qatlamida QIZARDI"
affects: [06-07, 06-08, 06-09, 06-10, 06-12, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Belgili pul ifodasi BITTA `text()` konstantasi bo'lib e'lon qilinadi va ikkala hosila ko'rinish SHUNI f-string bilan qo'yadi (`# noqa: S608` tor sabab bilan) — ikki ko'rinishning ajralib ketishi shu bilan MEXANIK imkonsiz"
    - "`market_is_open()` `WITH ... AS MATERIALIZED` CTE da bir marta hisoblanadi — kalendar mantig'i ham takrorlanmaydi, 1000 rastada 1000 chaqiruv ham bo'lmaydi"
    - "Juftlangan invariant mahsulot kodida `AssertionError` bilan majburlanadi, `assert` BAYONOTI bilan emas (ruff S101 + `python -O`)"
    - "Prefiks qidiruvida ANIQ MOSLIK USTUN — aks holda «kod boshqa kodning prefiksi» holatida ikkinchi chaqiruv ham ro'yxat qaytarib, oqim hech qachon tugamasdi"
    - "Testda tug'ilgan zona/hodisa/javob qatorlari uchun ALOHIDA EGA fixture (`LateReview`) — seed cleanup'i o'z ID'lari bo'yicha ishlaydi va test qatorlarini bilmaydi"

key-files:
  created:
    - services/core-api/app/repositories/billing_repo.py
    - tests/integration/test_billing_repo.py
  modified: []

key-decisions:
  - "06-06: `StallDayMoney` ga YETTINCHI maydon (`market_open`) qo'shildi — UI-SPEC §9.2 uni mustaqil maydon sifatida talab qiladi va uni ikkinchi so'rov bilan olish yarim tunda BOSHQA kunning javobini berardi"
  - "06-06: prefiks qidiruvida ANIQ MOSLIK USTUN — «10» va «100» birga yashaydigan seedda sof prefiks semantikasi ikkinchi chaqiruvni ham ro'yxat bilan qaytarardi va kassir oqimi `ready` ga hech qachon yetmasdi"
  - "06-06: `PendingProjection` UCH SHAKLNI ALOHIDA maydon bilan beradi (`stall` / `matches` / `market`) — bitta «bo'sh qiymatlar» to'plamiga siqish «summa hisoblanmadi» bilan «summa nol» ni ajratmasdi"
  - "06-06: `write_charge()` `tariff_id`/`amount_soum` yo'qligida ham `ValueError` beradi (D-28 dan tashqari) — `NOT NULL` ga urilgan `IntegrityError` xato TURINI yo'qotardi"
  - "06-06: to'liq G-2 invarianti («har hisob uchun o'sha kunda slot qatori bor») bu seedda IFODALAB BO'LMAYDI (slot kuni kelajakda, hisob esa kelajakka yozilmaydi) — repo yarmi shu yerda, to'liq invariant 06-14 da"
  - "06-06: `vendor_outstanding()` da `as_of` FAQAT hisoblarni cheklaydi, to'lovlarni EMAS — bugungi patta proyeksiyada alohida maydon va uni qoldiqqa ham qo'shish `total_due_soum` ni ikki marta sanardi"

patterns-established:
  - "Yangi repository moduli uchun: hosila ko'rinishlar bir xil arifmetikani BITTA modul darajasidagi SQL fragment konstantasidan oladi va tenglik integratsiya testida ARIFMETIK solishtiriladi"
  - "Integratsiya testida ikki seed varianti: bandlikka tegmaydigan guruhlar `*_before_day_close` dan (arzon), bandlik darvozasi esa `day_close` yugurgan variantdan"
  - "Sabotaj YASHIL qolganda sabab O'LCHANADI va sabotaj BIR QAVAT PASTGA ko'chiriladi (repo -> sof funksiya), da'vo susaytirilmaydi"

requirements-completed: [BILL-01, BILL-02, BILL-03, BILL-04, BILL-05]

# Metrics
duration: 145min
completed: 2026-08-10
---

# Phase 6 Plan 06: Pul mantig'i — `billing_repo` Summary

**Fazaning butun pul qarori endi BITTA modulda va u hech qanday qoidani qayta yozmaydi: hisob sharti, taqsimlash va qo'shish amali 06-01 dan CHAQIRILADI, kalendar DB funksiyasidan keladi, xato sabablari 06-02 reyestridan import qilinadi — 30 xulq darvozasi buni haqiqiy `postgres:18.4` da o'lchaydi va ikkala rejalashtirilgan sabotaj ham o'z javobini berdi.**

## Performance

- **Duration:** ~145 min
- **Started:** 2026-08-10T21:45:00Z
- **Completed:** 2026-08-10T00:10:00Z (keyingi kun, UTC)
- **Tasks:** 3
- **Files modified:** 2 (ikkalasi ham YANGI; mavjud birorta fayl tahrirlanmadi)

## Accomplishments

- **D-16 ning MAQSADI bajarildi va o'lchandi.** Summa `resolve_stall_day_money()` dan keladi; proyeksiya ham, kun yopilishi ham AYNAN shu funksiyani chaqiradi va `test_the_projection_amount_equals_the_money_resolution` ikki chaqiruvni `==` bilan solishtiradi. C-8 ning topilmasi hurmat qilindi: **bandlik darvozasi bo'linmadi**, faqat pul yechimi.
- **C-6 tuzatildi va SABOTAJ bilan isbotlandi.** Predikat 06-01 ning `billable_from_slots()` idan keladi; hisobot ustuni (`_PER_STALL_CTE` niki) modulda **umuman uchramaydi** (grep → 0). Sabotaj (manba butun rasta bo'ylab `bool_or`) holat (2) ni **qizartirdi**, (1) va (3) **yashil qoldi** — ya'ni u aynan mo'ljallangan nosozlikni ushlaydi.
- **D-24 ning javobi TASDIQ bo'ldi.** Uch kunlik qarz + BITTA 45 000 to'lov → yopilgan kunlar **AYNAN `[D-3, D-2, D-1]`**, tartibi bilan. Qisman to'lov (20 000) → `D-3` yopiq, `D-2` da `paid_soum == 5000` va `settled is False`, `D-1` da `0`. Hech nima saqlanmadi: taqsimlash jadvali ham, `allocated_*` ustuni ham yo'q (grep → 0).
- **G-14 ARIFMETIK o'lchandi.** `Σ unpaid_soum == vendor_outstanding()[vendor_id]`. Mexanizm: belgili to'lov ifodasi **bitta** `text()` konstantasi (`_SIGNED_PAYMENT_EXPR`) va ikkala funksiya **shuni** ishlatadi.
- **D-08 muzlatilgan dalil kech kelgan tasdiqdan keyin ham barqaror**, va nazorat asserti bilan: sabotaj sistemaga **yetib bordi** (`stall_slot_occupancy.winning_occupancy_event_id` `NULL` bo'ldi), `charge_evidence` esa **o'zgarmadi**.
- **Yangi paket o'rnatilmadi**, yangi `SECURITY DEFINER` funksiya qo'shilmadi, yangi HTTP marshruti ochilmadi — bu reja faqat repository qatlamiga tegadi.

## Task Commits

1. **Task 1: `resolve_stall_day_money()` — yagona pul yechimi** — `9c927b4` (feat)
2. **Task 2: `billable_stalls()`, hisob, muzlatilgan dalil, uch anomaliya** — `a9a5f82` (feat)
3. **Task 3: qoldiq, FIFO hosila ko'rinish va `pending_projection()`** — `7a8d958` (feat)

## Files Created/Modified

- `services/core-api/app/repositories/billing_repo.py` (**yangi**, 1255 qator) — yetti funksiya, olti natija tipi, to'rt `LEFT JOIN LATERAL`, ikki belgili-pul ifoda konstantasi.
- `tests/integration/test_billing_repo.py` (**yangi**, 1608 qator) — 30 test, o'n bir guruh; ikki seed varianti; soxta qatlam **yo'q**.

## Sabotaj (D-30) — IKKI REJALASHTIRILGAN URINISH, UCH O'LCHOV

| # | Sabotaj | Natija | Xulosa |
|---|---|---|---|
| **S-A (G-6)** | `billable_stalls()` ichida manba butun rasta bo'ylab `bool_or` bilan almashtirildi (ya'ni hisobot ustunining semantikasi) | 🔴 **QIZARDI** — faqat holat (2) | Sabotaj sistemaga yetib bordi va AYNAN mo'ljallangan holatni ushladi: `assert True is False` + `BillableDecision(occupied_slots=1, billable=True)`. Holatlar (1) va (3) **yashil qoldi**, ya'ni test predikatning O'ZINI o'lchaydi, «hammasi buzildi» ni emas |
| **S-B (D-24, repo qatlami)** | `allocate_charge_credit()` ga hisoblar **teskari** tartibda berildi (LIFO) | 🟢 **YASHIL QOLDI** | **KUTILGAN TOPILMA** (reja buni oldindan nomlagan): sof funksiya `sorted()` ni **o'zi** bajaradi va bu **to'g'ri xulq** — ya'ni sabotaj o'lchanayotgan qatlamga **yetib bormadi** |
| **S-B2 (D-24, sof funksiya qatlami)** | `sbozor_core/billing.py::allocate_charge_credit` dagi `sorted(...)` ga `reverse=True` qo'shildi | 🔴 **QIZARDI** — (a) va (b) | Ikkala kun-kesimi testi ham yiqildi (`by_day[oldest].settled` → `False`). Ya'ni tartib da'vosi **haqiqatan** o'lchanadi, faqat u sof funksiya qatlamida yashaydi |

⚠ **S-B2 da uchinchi test (`matches_vendor_outstanding`) YASHIL qoldi va bu TO'G'RI:** `Σ unpaid_soum` tartibdan **mustaqil** miqdor. G-14 ordering da'vosi EMAS, u ikki ko'rinishning **tenglik** da'vosi — ikkalasini bitta testga qo'shish «qaysi xossa qizardi?» savolini javobsiz qoldirardi. Uchala sabotaj ham `git checkout -- <fayl>` bilan qaytarildi; `git status` toza.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `StallDayMoney` ga YETTINCHI maydon (`market_open`) qo'shildi**

- **Found during:** Task 1
- **Issue:** Reja `StallDayMoney` ning olti maydonini sanaydi, `PendingStall` esa UI-SPEC §9.2 bo'yicha `market_open` ni **talab qiladi**. Uni `unavailable_reason == MARKET_CLOSED` dan hosila qilish mumkin edi, lekin u **xato kodidan mantiqiy qiymat chiqarish** bo'lardi; ikkinchi so'rov bilan olish esa yarim tunda **boshqa kunning** javobini berardi (`as_of` bir chaqiruvda, `now()` boshqasida).
- **Fix:** `market_open` AYNI so'rovdan, AYNI `as_of` bilan keladi (`WITH calendar AS MATERIALIZED`), ya'ni manba bitta va kun bitta.
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Verification:** `test_resolve_reports_a_closed_day_without_an_amount` `market_open is False` ni ham o'lchaydi; `PendingStall` ning maydon to'plami esa **aynan yettita** (D-31 to'plam tengligi).
- **Committed in:** `9c927b4`

**2. [Rule 2 - Missing Critical] Prefiks qidiruvida ANIQ MOSLIK USTUN qilindi**

- **Found during:** Task 3
- **Issue:** Reja «prefiks bo'lsa va bir nechta rasta mos kelsa `matches` qaytariladi; kassir aniq kodni tanlagach IKKINCHI chaqiruv bo'ladi» deydi. Sof prefiks semantikasida bu **tugamaydi**: seedda «10» va «100» birga yashaydi, ya'ni kassir ro'yxatdan «10» ni tanlaganda ikkinchi chaqiruv **o'sha ro'yxatni** qaytarardi va oqim `ready` holatiga **hech qachon** yetmasdi (UI-SPEC §8.3 ning «aynan bitta natija → darhol ready» kontrakti buzilardi).
- **Fix:** tergan kod moslashlar orasida AYNAN bo'lsa u yagona natija sifatida qabul qilinadi; sabab funksiya docstringida **o'lchov bilan** yozildi.
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Verification:** `test_an_ambiguous_prefix_returns_matches_without_an_amount` ikkala chaqiruvni ham o'lchaydi — «1» → `("10", "100")`, «10» → to'liq proyeksiya.
- **Committed in:** `7a8d958`

**3. [Rule 2 - Missing Critical] `write_charge()` summasiz/tarifsiz holatni ham `ValueError` bilan rad etadi**

- **Found during:** Task 2
- **Issue:** Reja faqat `vendor_id is None` uchun rad etishni yozadi. `tariff_id`/`amount_soum` `None` bo'lgan holat (yopiq kun, tarifsiz toifa) `NOT NULL` ustunga urilib **`IntegrityError`** berardi — ya'ni xato TURI yo'qolardi va 06-07 uni `billing_close_failed` deb yozib qo'yardi (aynan D-28 uchun rad etilgan sinf).
- **Fix:** uchala shart ham ilova qatlamida, AYRIM xabar bilan.
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Verification:** `mypy` toza; D-28 testi `match="D-28"` bilan AYNAN o'z shoxini o'lchaydi.
- **Committed in:** `a9a5f82`

**4. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi (06-04/06-05 dagi holatning takrori)**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da va worktree ularsiz yaratilgan.
- **Fix:** Ikkala fayl asosiy repodan **NUSXALANDI**. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

**5. [Rule 1 - Bug] Testda tug'ilgan zona/hodisa/javob qatorlari seed cleanup'ini yiqitardi**

- **Found during:** Task 2 (birinchi to'liq yugurish)
- **Issue:** `cleanup_billing_domain()` `occupancy_events` va `snapshots` ni **O'Z ID'lari** bo'yicha o'chiradi va testda qo'shilgan `review_assignments` qatorlarini bilmaydi → `ForeignKeyViolation` **teardown'da**, ya'ni nosozlik SEEDDA ko'rinardi, holbuki u TESTNIKI.
- **Fix:** `LateReview` — testda tug'ilgan qatorlarning ALOHIDA EGASI; fixture `env_with_slots` GA bog'langan, ya'ni pytest uni seeddan **oldin** yopadi. Tozalash FK tartibida va bozorni qoralamaga qaytarib bajaradi (`cleanup_occupancy_domain()` ning aynan qadami).
- **Files modified:** `tests/integration/test_billing_repo.py`
- **Verification:** 30/30 yashil, teardown xatosi yo'q.
- **Committed in:** `a9a5f82`

**6. [Rule 1 - Bug] Testning sanasi kalendarga bog'lanib qolgan edi (flaky sinf)**

- **Found during:** Task 2
- **Issue:** `CURRENT_DATE - 1` ni hisob sanasi qilib olish testni HAFTA KUNIGA bog'lardi: A bozori dushanba yopiq, ya'ni seshanba kuni yugurgan test `write_charge()` ni `market_closed` bilan yiqitardi va sabab kodda emas, **kalendarda** bo'lardi.
- **Fix:** `_open_past_day()` — o'tmishdagi eng yaqin OCHIQ kun, `A_OPEN_WEEKDAYS` dan hosila.
- **Files modified:** `tests/integration/test_billing_repo.py`
- **Committed in:** `a9a5f82`

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **`tariff_missing` holati B BOZORIDAN olinadi.** Reja «tarifsiz toifada» deydi, indeksni bermaydi. A bozorining HAR rastasiga `market_domain` toifa davri yozadi va uchala toifaning ham tarifi bor; B bozorida esa IKKI toifa, BITTA tarif — ikkinchi toifa ATAYIN tarifsiz (`market_domain.py:503`). Ya'ni bu shox faqat B da ifodalanadi va test uni o'sha yerdan oladi.
- **D-28 testining kuni `SEED_BUSINESS_DATE`.** Seed biriktirish bo'shlig'ini `[BILLING_VALID_FROM, D)` va `[D + 7, ∞)` qilib yozadi, ya'ni o'tmishdagi ixtiyoriy kunda rasta **biriktirilgan**. Nazorat asserti buni darhol fosh qildi va sana bo'shliqning O'ZIGA ko'chirildi (`ValueError` baribir DB ga yetib bormaydi).
- **G-2 ikkiga bo'lindi.** To'liq invariant («har yozilgan hisob uchun o'sha `(market_id, stall_id, service_date)` da kamida bitta slot qatori bor») bu seedda **ifodalab bo'lmaydi**: slot kuni `SEED_BUSINESS_DATE` = kelajak, hisob esa `ck_daily_charges_service_date_not_in_future` bo'yicha kelajakka yozilmaydi. Repo yarmi (`service_date` va `business_date` ning FARQI ochiq da'vo qilinadi) shu faylda; to'liq invariant `test_phase6_criteria.py` (06-14) da — 06-05 uni allaqachon o'sha yerga biriktirgan.
- **`ORDER BY` `_VENDOR_CHARGE_DUES` da e'lon qilinmadi** (reja «tartib SQL da emas» deydi va aynan shunday qilindi): tartib `sbozor_core.billing` ning `sorted()` ida yashaydi va S-B2 buni isbotladi.

---

**Total deviations:** 6 auto-fixed (1 blocking, 2 bug, 3 missing-critical) + 4 reja matnining aniqlashtirilishi
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Yangi paket **o'rnatilmadi** (T-06-SC bandi bajarildi), mavjud birorta mahsulot fayli **tahrirlanmadi** — ikkala fayl ham YANGI.

## Issues Encountered

- **To'liq to'plamning birinchi yugurishida 33 test qizil edi** — hammasi NVR simulyatori guruhida (`test_nvr_*`, `test_live_view_e2e`, `test_phase3_criteria`), sababi `nvr_isapi_unavailable`: `sbozor-nvr-sim-1` konteyneri eskirgan edi. **Bu rejaning o'zgarishlariga aloqasi yo'q** (u birorta NVR/RTSP/kamera fayliga tegmaydi va o'sha fayllar `billing_repo` ni import qilmaydi). Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` **ishlatilmadi**). Shundan keyin o'sha yetti fayl **99/99 yashil** bo'ldi. Repoga birorta o'zgarish kiritilmadi.
- **5-FAZADAN MEROS FLAKY TEST TOPILDI (qamrovdan TASHQARIDA, TUZATILMADI).**
  `test_blind_audit.py::test_a_different_round_number_draws_a_different_sample` to'liq
  to'plamning **ikkinchi** yugurishida qizardi (`Both sets are equal`), **birinchisida**
  esa yashil edi; izolyatsiyada ham (33/33), yolg'iz qayta yugurganda ham **yashil**.
  Sabab tabiati aniq: namuna hajmi nomzodlar havzasiga yaqin bo'lganda ikki har xil
  urug' **bir xil** to'plamni tanlashi mumkin, ya'ni «tur raqami namunani o'zgartiradi»
  da'vosi ehtimoliy. ⛔ **TUZATILMADI** — u bu rejaning o'zgarishlaridan kelib chiqmagan
  (bu reja birorta bandlik/audit fayliga tegmaydi) va ijrochi qoidasi bo'yicha qamrovdan
  tashqaridagi topilma `deferred-items.md` ga yoziladi. Yozildi.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q. ⛔ Junction/symlink **YARATILMADI** (bu ilgari asosiy checkout'ni buzgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. **Bu reja birorta frontend fayliga tegmaydi**, ya'ni `gate` byudjetining (1250 s) to'liq o'lchovi yana keyingi to'lqinga qoladi.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_billing_repo.py -q` | ✅ **30/30** |
| `pytest tests/integration/test_billing_repo.py -q -k resolve` | ✅ (Task 1 darvozasi) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**304** fayl formatlangan, **295** fayl tiplangan) |
| `pytest -q` (to'liq to'plam, **eskirgan** sim bilan) | ⚠ 33 qizil — hammasi NVR sim guruhida (yuqoridagi bandga qarang) |
| Sim guruhining qayta yugurishi (7 fayl) | ✅ **99/99** simulyator qayta yaratilgandan keyin |
| `pytest -q` (to'liq to'plam, **yangi** sim bilan) | ⚠ **1 qizil** — `test_blind_audit.py::test_a_different_round_number_draws_a_different_sample` (5-fazadan meros, **FLAKY**; pastdagi bandga qarang) |
| `pytest tests/integration/test_blind_audit.py -q` (izolyatsiyada) | ✅ **33/33** |
| O'sha testning yolg'iz qayta yugurishi | ✅ yashil |

**Grep mezonlari** (`billing_repo.py`):

| Mezon | Kutilgan | O'lchov |
|---|---|---|
| `LEFT JOIN LATERAL` | ≥ 3 | **4** |
| `t.id` | ≥ 1 | **2** |
| `market_is_open` | ≥ 1 | **5** |
| `open_weekdays\|market_calendar_exceptions` | 0 | **0** |
| `code_sort` | ≥ 1 | **7** |
| `\bfloat\b\|Decimal` (izohsiz qatorlar) | 0 | **0** |
| `unavailable_reason is not None` | ≥ 1 | **1** |
| `billable_from_slots` | ≥ 1 | **6** |
| `human_confirmed` | 0 | **0** |
| `on_conflict_do_nothing` | ≥ 3 | **4** |
| `on_conflict_do_update` | 0 | **0** |
| `FROM occupancy_events` | ≥ 1 | **1** |
| `allocate_charge_credit` | ≥ 1 | **4** |
| `total_due_soum(` | ≥ 1 | **3** |
| `\babs\(` | 0 | **0** |
| `ORDER BY[^;]*service_date DESC` | 0 | **0** |
| `payment_allocations\|allocated_soum\|allocated_charge` | 0 | **0** |
| `AMOUNT_UNAVAILABLE_REASONS` | ≥ 1 | **4** |
| `market_closed` (satr literali) | 0 | **0** |
| Qatorlar soni | ≥ 400 | **1255** |

**Qo'lda tekshirilgan bandlar** (reja shuni talab qiladi):

- ⛔ `FROM occupancy_events` **faqat bitta joyda** — `_EVIDENCE_SNAPSHOTS` (`write_evidence` ning `snapshot_id` nusxasi). Bandlik agregatsiyasi uchun `occupancy_events` ga **umuman murojaat yo'q** (D-03).
- ⛔ `pending_projection` natijasining rasta dataclassida (`PendingStall`) `charge_id` ham, `tariff_id` ham **yo'q** — maydon to'plami **aynan yettita** va u `dataclasses.fields()` dan olinib **literal to'plam** bilan solishtiriladi (`test_pending_projection_exposes_exactly_seven_fields`).

## Known Stubs

Yo'q. Ikkala fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q.

⚠ **`vendor_charge_allocation()` ning HTTP iste'molchisi 6-fazada ATAYIN YO'Q** va u **stub EMAS**: sotuvchi kesimidagi to'lov tarixi 8-fazaniki (UI-SPEC §16.1). Qoida bugun **tasdiq bilan** qulflandi (uch integratsiya testi + ikki qatlamli sabotaj), yuza keyin qo'shiladi. Sabab funksiya docstringida ochiq yozilgan, aks holda keyingi ijrochi uni «o'lik kod» deb o'chirardi (06-02 ning `AuditAction` bandi bilan aynan bir xil naqsh).

## Threat Flags

Yangi xavfsizlik yuzasi **ochilmadi**:

- Yangi tarmoq endpointi, autentifikatsiya yo'li yoki fayl kirishi **yo'q** (bu reja faqat repository qatlamiga tegadi; marshrutlar 06-08/06-09 da).
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**; `market_is_open()` INVOKER bo'lib qoldi va modul docstringi chaqiruvchiga tenant kontekstini **shart** qilib yozadi (T-06-34 / Pitfall 9).
- Yangi paket **o'rnatilmadi** (T-06-SC).
- ⛔ Threat register bo'yicha **sakkizala `mitigate` bandi bajarildi**: T-06-30 (predikat qayta ishlatildi + grep taqiqi + G-6 sabotaji), T-06-31 (`valid_from <= :as_of` + `tariff_id` va summa birga), T-06-32 (`no_coverage_stall` alohida `kind`, hisob yozilmaydi), T-06-33 (`vendor_id` yo'q → `ValueError`), T-06-34 (`market_is_open()` DB funksiyasi, kalendar takrorlanmagan), T-06-35 (`occupancy_event_id` muzlatilgan, `day_close` qayta yugurgandan keyin o'lchandi), T-06-36a (FIFO hosila ko'rinish + uch tasdiq + ikki qatlamli sabotaj), T-06-36b (bitta belgili ifoda konstantasi + arifmetik tenglik testi). T-06-36 (`accept`) — qoldiq sotuvchi kesimida qoldi va sabab `_VENDOR_OUTSTANDING` docstringida.

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): `sbozor-nvr-sim` konteyneri eskirganda NVR guruhi `nvr_isapi_unavailable` beradi. Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` ishlatilmaydi).

## Next Phase Readiness

- **06-07 (`billing_close` job):** yetti funksiya tayyor va **job hech qanday pul mantig'i yozmaydi** — u `billable_stalls()` → `resolve_stall_day_money()` → `write_charge()`/`write_evidence()`/`write_anomaly()` zanjirini chaqiradi. `no_slot_rows` (Pitfall 2) hisoblanadigan holat: `billable_stalls()` slot qatori bo'lmagan rastani ro'yxatga **umuman kiritmaydi**, ya'ni chaqiruvchi uni sanashi mumkin. Yopiq kun `resolve_stall_day_money()` da `MARKET_CLOSED` bo'lib chiqadi va D-10 anomaliyasining tetigi shu.
- **06-08/06-09 (marshrutlar):** `pending_projection()` UI-SPEC §9.2 ning aynan yetti maydonini beradi va `total_due_soum` **serverda**; ko'p moslik shakli (`matches`) 06-11 dagi `collect-session.test.tsx` uchun tayyor.
- **06-09 (`POST /payments`):** `vendor_outstanding()` kvota to'plamining ikkinchi elementini beradi (`as_of` bilan «eski qarz» aniq ajratilgan) va `payment_quote_set()` (06-01) uni to'g'ridan-to'g'ri qabul qiladi.
- **06-12/06-14 (darvozalar):** G-6 ning uch holati va G-13/G-14 shu faylda **allaqachon yashil**; 06-14 ga qoladigan yagona band — to'liq G-2 invarianti (yuqoridagi «Reja matnining aniqlashtirilishi» ga qarang).
- ⚠ **Ochiq band (bloklamaydi):** `gate` ning to'liq vaqti bu to'lqinda ham **O'LCHANMADI** (frontend yarmi worktree'da yugurmaydi). Backend yarmi ~33 daqiqa oldi, lekin o'lchov `sim` profili ko'tarilgan va boshqa konteynerlar ishlab turgan xostda olindi — ya'ni u **BYUDJET o'lchovi EMAS**.

## Self-Check: PASSED

**Fayllar (4/4 mavjud):** `services/core-api/app/repositories/billing_repo.py` (1255 qator, 50 704 bayt) · `tests/integration/test_billing_repo.py` (1608 qator, 62 247 bayt) · `06-06-SUMMARY.md` · `deferred-items.md`

**Commitlar (3/3 topildi):** `9c927b4` · `a9a5f82` · `7a8d958`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `billing_repo.py` `min_lines: 400` | `wc -l` → **1255** | ✅ |
| `billing_repo.py` `contains: resolve_stall_day_money` | `grep -c` → **4** | ✅ |
| `provides`: yetti funksiya | `__all__` da sakkiz nom (yetti funksiya + tiplar) | ✅ |
| `test_billing_repo.py` — G-6 uch holati + D-06 + D-08 | 30 test, uchala G-6 holati **alohida nomlangan** | ✅ |
| `key_links`: `resolve_stall_day_money` → `ORDER BY p.valid_from DESC` | mavjud (uch LATERAL) | ✅ |
| `key_links`: `billable_stalls` → `resolution_source = :human` | predikat 06-01 da; SQL faqat qatorlarni beradi (`grep human_confirmed` → **0**) | ✅ |
| `key_links`: `write_evidence` → `occupancy_event_id` | `charge_evidence.occupancy_event_id` muzlatilgan nusxa | ✅ |
| `key_links`: `vendor_charge_allocation` → `allocate_charge_credit` | `grep -c` → **4** | ✅ |

**`truths` (9/9):**
pul yechimi BITTA funksiyada va ikki chaqiruvchi bir natija beradi (`==` bilan o'lchandi) ·
tarif TARIXIY va hisob `tariff_id` ni HAM saqlaydi ·
hisob sharti hisobot ustunidan AJRALGAN (grep → 0 + sabotaj qizardi) ·
ikkinchi hisob yozib bo'lmaydi va qayta yugurish qatorga TEGMAYDI (summa VA `created_at`) ·
dalil NUSXA va `day_close` qayta yugurgandan keyin ham o'zgarmadi ·
`vendor_id NULL` bilan hisob YOZILMAYDI (`ValueError`) ·
qoldiq HISOBLANADIGAN so'rov (saqlangan ustun yo'q) ·
D-24 ga javob RO'YXAT bilan berildi (`[D-3, D-2, D-1]`, tartibi bilan) ·
hosila taqsimlash `vendor_outstanding()` bilan ARIFMETIK teng.

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
