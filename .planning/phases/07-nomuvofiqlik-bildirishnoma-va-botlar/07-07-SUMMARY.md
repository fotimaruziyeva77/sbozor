---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 07
subsystem: backend
tags: [reconciliation, case, hit-rate, keyset, cron, idempotency, rls]
requires:
  - "0023_notification_domain — reconciliation_cases / reconciliation_case_events, ikki qisman UNIQUE indeks, append-only trigger"
  - "sbozor_core.models.notification — MarketNotificationSettings.overdue_days server_default (A3)"
  - "billing_repo.vendor_outstanding() — BILL-03 hisoblanadigan qoldiq"
  - "billing_repo.vendor_charge_allocation() — FIFO_OLDEST_SERVICE_DATE_FIRST (D-24)"
  - "app/jobs/retention.py::active_market_ids — YAGONA RLS-chetlab o'tuvchi yuza (D-15)"
  - "tests/fixtures/notification_domain.py — seed_case / seed_no_coverage_anomaly / seed_notification_settings"
provides:
  - "reconciliation_repo.open_cases() — ikki sinf, idempotent, OpenCasesResult"
  - "reconciliation_repo.list_cases() — kun kesimi + keyset (CaseListPage, CaseCursor)"
  - "reconciliation_repo.hit_rate() — HOSILA, o'lchanmagan holat None (HitRate)"
  - "reconciliation_repo.transition() — ikki yozuv bitta tranzaksiyada (CaseTransition)"
  - "reconciliation_repo.case_evidence() — FAQAT UUID (CaseEvidence)"
  - "CASE_WORTHY_ANOMALY_KINDS / NON_CASE_ANOMALY_KINDS / CASE_PAGE_SIZE"
  - "app/jobs/reconciliation.py::reconciliation_open() + RECON_OPEN_COMPONENT + DEFAULT_OVERDUE_DAYS"
affects:
  - "07-10 (case API) va 07-15 (frontend) — arifmetikani TAKRORLAMAYDI, shu repodan o'qiydi"
  - "07-14 (cron reyestri) — `recon.open` qobig'i, self_check.EXPECTED_COMPONENTS, alerting watched"
tech-stack:
  added: []
  patterns:
    - "ikki mustaqil `INSERT ... SELECT ... ON CONFLICT DO NOTHING` bitta CTE'da (nomzod + yozilgan sanoq bir borishda)"
    - "qisman UNIQUE indeksga `ON CONFLICT` inferensiyasi PREDIKAT bilan"
    - "taqiq ro'yxati (`NON_CASE_ANOMALY_KINDS`), ruxsat ro'yxati EMAS — yangi enum a'zosi jimgina tushib qolmasin"
    - "hosila nisbat Python tomonda, o'lchanmagan holat `None` (D-13)"
    - "keyset qator solishtiruvi `(created_at, id) < cursor` — `OFFSET` yo'q"
    - "kod standarti SXEMANING `server_default` idan HOSILA, literal EMAS"
key-files:
  created:
    - services/core-api/app/repositories/reconciliation_repo.py
    - services/core-api/app/jobs/reconciliation.py
    - tests/integration/test_reconciliation_repo.py
  modified: []
decisions:
  - "Sinf A predikati IKKI mahsulot funksiyasidan: `vendor_outstanding()` qarzdorni topadi, `vendor_charge_allocation()` qaysi KUN to'lanmaganini aytadi — yangi SQL yozilmadi (T-07-33)"
  - "N+1 so'rov ONGLI qabul qilindi: muqobil — `FIFO_OLDEST_SERVICE_DATE_FIRST` ni SQL da qayta yozish, ya'ni nomlangan qoidaning IKKINCHI nusxasi"
  - "`DEFAULT_OVERDUE_DAYS` sxemadan HOSILA — `notification_meta.py` 07-06 niki va bu worktree'da YO'Q"
  - "Rejadagi nosozlik misoli («overdue_days yo'q») STRUKTURAVIY imkonsiz — `COALESCE` uni xato emas, standart qiladi; o'rniga HAQIQIY ma'lumot holati (manfiy qoldiq)"
  - "`next_cursor` envelope'ga qo'shildi — usiz keyset sahifalash IFODALAB BO'LMASDI"
  - "Topilmagan case — `LookupError`, jim `return` EMAS"
metrics:
  duration: ~75 min
  completed: 2026-08-12
  tasks: 2
  files: 3
---

# Phase 7 Plan 07: Case domeni — nomuvofiqlikning arifmetikasi — Summary

Nomuvofiqlikning **ikkala sinfi** ham endi navbat qatoriga aylanadi — biri
o'zgarmas anomaliya qatoridan, ikkinchisi `daily_charges` − `payments`
**hosilasidan** — va «to'lanmagan» ning ta'rifi ikkinchi marta
yozilmadi: u mavjud ikki mahsulot funksiyasidan **chaqirib** olinadi.

## Nima qurildi

**Task 1 — `reconciliation_repo.py` (`cad029e`).** Besh ommaviy funksiya
va olti tiplangan natija. `open_cases()` ikki mustaqil `INSERT ... SELECT
... ON CONFLICT DO NOTHING` ni bitta tranzaksiyada bajaradi; har biri CTE
ichida **nomzodlar** va **haqiqatan yozilganlar** sonini BIR borishda
qaytaradi (farqi — `skipped_existing`). `list_cases()` kun kesimi +
keyset; `hit_rate()` hosila; `transition()` ikki yozuv;
`case_evidence()` faqat `UUID`.

**Task 2 — `app/jobs/reconciliation.py` (`c670c6a`).** `billing_close.py`
ning aynan shakli: `active_market_ids()` **import qilinadi**, har bozor
uchun `_tenant_session` va alohida tranzaksiya, xato `_swallow()` bilan
yutiladi, yurak urishi xatolar bo'lganda ham yoziladi. **Cron
registratsiyasi ATAYIN yo'q** — `worker.py` 07-14 ning fayli.

**`14627f6`** — ikki assertni begona test faylining tartibidan uzdi
(pastda, «Chetlanishlar» da).

## O'lchangan dalillar

### Sabotaj — hit-rate maxraji (reja talab qilgan)

`hit_rate()` ning maxrajiga `pending` (`new` + `in_review`) vaqtincha
qo'shildi. Natija **aynan bitta** testni qizartirdi:

| Test | Sabotajsiz | Sabotaj bilan |
|---|---|---|
| `test_pending_cases_do_not_move_the_hit_rate` | yashil | **QIZIL** — `rate=0.5`, kutilgani `0.75` |
| `test_hit_rate_is_the_ratio_of_closed_cases` | yashil | **yashil** (seedda `pending` yo'q) |
| `test_hit_rate_is_none_when_nothing_was_measured` | yashil | **yashil** |

⛔ Ikkinchi va uchinchi qatorlar **darvozaning aniqligini** isbotlaydi:
sabotaj ular uchun **ko'rinmas**, ya'ni maxraj da'vosini qamrab
turadigan yagona test — birinchisi. Uning ichidagi nazorat asserti
(`measured.pending == 2`) esa 05-15 ning S-D darsini bajaradi: seedda
`new`/`in_review` qatori **bor** ekani oldindan isbotlanadi, aks holda
maxraj testi bo'sh rost bo'lardi. Sabotaj o'lchovdan keyin olib
tashlandi.

### Grep darvozalari (reja yozgan)

| Darvoza | Fayl | Kutilgan | Natija |
|---|---|---|---|
| `presign\|object_key\|https?://` | `reconciliation_repo.py` | 0 | **0** |
| `\bfloat\(\|Decimal\|\bround\(\|\bbalance\b` | `reconciliation_repo.py` | 0 | **0** |
| `NULLIF` mavjudligi | `reconciliation_repo.py` | bor | **bor** |
| `min_lines` | `reconciliation_repo.py` | ≥ 260 | **1143** |
| `from app.jobs.retention import` | `jobs/reconciliation.py` | ≥ 1 | **1** |
| `auth_list_markets_full\|SECURITY DEFINER` | `jobs/reconciliation.py` | 0 | **0** |
| `business_today()` | `jobs/reconciliation.py` | 0 | **0** |
| `RECON_OPEN_COMPONENT` qiymati | `jobs/reconciliation.py` | `reconciliation_open` | **mos** (test bilan) |

### Test darvozalari

| Darvoza | Natija |
|---|---|
| `pytest tests/integration/test_reconciliation_repo.py -q` | **24 test yashil** (reja ≥ 10 so'ragan) |
| `pytest tests/integration -q -m "not sim and not slow"` | **885 yashil, 5 skip, `EXIT=0`** |
| `pytest tests/tenancy -q` | **690 yashil** (07-04 ning darvozalari buzilmadi) |
| `pytest tests/unit -q` | `EXIT=0` |
| `ruff check .` + `ruff format --check .` + `mypy .` | **toza** (317 fayl) |

⚠ **Birinchi to'liq yugurishda 4 test qizardi va ularning hech biri bu
rejaning kodiga tegishli emas.** `test_snapshot_api.py` (3) va
`test_phase6_criteria.py::test_sc2...` `StorageError: PUT ... AccessDenied
(status=403)` berdi — izolyatsiyalangan compose loyihasining **yangi**
SeaweedFS hajmida `sbozor-snapshots` bucketi yo'q edi
(`ops/seaweedfs/README.md` buni nomma-nom yozgan). Bucket yaratilgach
o'sha ikki fayl **31/31 yashil** bo'ldi va keyingi to'liq yugurish
`EXIT=0` berdi. Ya'ni bu MUHIT bo'shlig'i, kod nuqsoni emas — va u
mustaqil ravishda ham tasdiqlanadi: reja **birorta ombor, kadr yoki
`storage` faylga tegmagan**.

### Ikki sinfning xulqi (integratsiya testlaridan)

| Da'vo | Natija |
|---|---|
| `unassigned_occupied` + `closed_day_occupied` -> case | ✓ (2 ta) |
| `no_coverage_stall` -> case | **YO'Q** (nazorat: anomaliya seedda BOR) |
| ikkinchi yugurish qator sonini o'zgartiradimi | **yo'q**, `skipped_existing > 0` |
| bugungi to'lanmagan hisob (`overdue_days=3`) | case **ochmaydi** |
| `service_date = bugun − 4` | case **ochadi**, `subject_kind='occupied_unpaid'`, `anomaly_id IS NULL` |
| to'liq to'langan sotuvchi | `unpaid_cases == 0` |
| `justified=3, unjustified=1` | `rate == 0.75` |
| o'lchov yo'q | `rate is None` (`0.0` **EMAS**) |
| `transition` bir chaqiruvda | **aynan 1** qator; uch o'tish -> **3** qator |
| yopilgan holatdan qaytish | **ruxsat**, va u ham yangi qator yozadi |
| `from == to` | `ValueError`, qator **yozilmaydi** |
| keyset ikkinchi sahifasi | birinchisi bilan **kesishmaydi**, birlashmasi = seed |
| bo'sh kunda envelope | to'rtala hisoblagich **0 bo'lib qaytadi** |
| holat filtri hisoblagichlarga ta'sir qiladimi | **yo'q** (kun kesimi) |
| `case_evidence` javobi | faqat `UUID`; topilmagan case -> `LookupError` |
| job ikki bozorda | **ikkalasida ham** case (`unpaid_cases == 2`) |
| bir bozor buzilganda | `len(errors) == 1`, ikkinchi bozor **baribir yopildi** |
| yurak urishi | `last_seen_at` NOT NULL, `detail` da faqat butun sonlar |
| bozor sozlamasi (`overdue_days=30`) vs standart | **ikki xil javob** (0 va 1 case) |

## Rejadan chetlanishlar

### Rule 3 — bloklovchi bo'shliqlar

**1. [Rule 3] `DEFAULT_OVERDUE_DAYS` sxemadan HOSILA qilindi**

- **Topildi:** Task 2, birinchi satr yozilishidan oldin. Reja
  `app/jobs/notification_meta.py::DEFAULT_OVERDUE_DAYS` ni o'qishni
  buyuradi, lekin o'sha fayl **07-06 niki** va bu worktree'da YO'Q; u
  bu rejaning `files_modified` ida ham yo'q, ya'ni uni yaratish
  parallel ijrochi bilan to'qnashardi.
- **Yechim:** qiymat `MarketNotificationSettings.overdue_days` ning
  `server_default` idan **o'qib olinadi** (`_schema_default_overdue_days()`),
  ya'ni u NUSXA emas, HOSILA — DDL ni yaratgan aynan o'sha e'londan
  keladi va undan ajralib keta olmaydi. Shakl buzilsa funksiya
  `RuntimeError` bilan yiqiladi, jim standartga tushmaydi.
- **Commit:** `c670c6a`
- ⚠ **Merge'dan keyingi band** — pastdagi «Ochiq bandlar» ning 2-bandi.

**2. [Rule 3] Dalilli anomaliyaning seed'i test modulida yozildi**

- **Topildi:** `fixtures/notification_domain.py::seed_no_coverage_anomaly`
  ATAYIN faqat **dalilsiz** sinfni yozadi (07-04 ning o'lchangan
  qarori), case OCHILADIGAN ikkala sinf esa `occupancy_event_id` VA
  `snapshot_id` ni **talab qiladi** (juftlangan `CHECK`). Ya'ni sinf B
  ni umuman o'lchab bo'lmasdi.
- **Yechim:** `_INSERT_EVIDENCED_ANOMALY` + `_EVIDENCE_PAIR` test
  modulida (fixture faylga TEGILMADI — u `files_modified` da yo'q).
  Juftlik **bazadan o'qiladi**, test uni o'zi yig'maydi
  (`add_charge_evidence` da o'rnatilgan qoida). 07-04 SUMMARY ning
  4-ochiq bandi bu ko'chishni allaqachon 07-05/07-06 ga bergan.
- **Commit:** `cad029e`

### Rule 1 — reja matni haqiqatdan farq qilgan joyda HAQIQAT ustun turdi

**3. [Rule 1] Nosozlik misoli almashtirildi — rejadagisi STRUKTURAVIY imkonsiz**

- **Topildi:** reja «bitta bozorning ma'lumoti buzilganda (masalan
  sozlamada `overdue_days` yo'q) job to'xtamaydi» deb yozgan va
  `errors == 1` ni talab qilgan. Lekin sozlama qatorining **yo'qligi
  xato emas**: `_MARKET_OVERDUE_DAYS` `COALESCE` bilan kod standartiga
  tushadi (buni rejaning O'ZI talab qilgan) va job muvaffaqiyatli
  yakunlanadi. O'sha misol bilan yozilgan test `errors == 1` ni **hech
  qachon** ko'rmasdi — ya'ni u mangu qizil (yoki soxta) bo'lardi.
- **Yechim:** nosozlik **haqiqiy ma'lumot holatidan** quriladi —
  hisobning O'ZIDAN katta `decrease` tuzatishi o'sha kunning qoldig'ini
  manfiy qiladi va `allocate_charge_credit()` uni `ValueError` bilan rad
  etadi. Bu holat o'sha funksiyaning **O'Z docstringida** nomlab
  qo'yilgan («o'ta katta `decrease` — D-07 ning o'z savoli»), ya'ni u
  hujjatlashtirilgan, erishib bo'ladigan holat. Test yana ikkinchi
  hisob qo'shadi (usiz sotuvchining umumiy qoldig'i ham manfiy bo'lardi
  va u qarzdorlar ro'yxatiga umuman kirmasdi — nosozlik TUG'ILMASDI).
- **Yon oqibat:** `_swallow()` `SQLAlchemyError` ni emas, `Exception` ni
  ushlaydi — repo qatlami buzilgan ma'lumotda `ValueError` beradi va
  torroq blok bilan bitta bozorning nuqsoni butun navbatni bo'sh
  qoldirardi.
- **Commit:** `c670c6a`

**4. [Rule 1] `result.markets == 2` -> `>= 2`**

- **Topildi:** to'liq integratsiya to'plamida. `active_market_ids()`
  **butun bazadagi** faol bozorlarni qaytaradi, ya'ni aniq songa
  qadalgan da'vo qo'shni test faylining (masalan wizard oqimi)
  tartibiga bog'lanib qolardi va kod nuqsonisiz yiqilardi.
  `test_retention.py:657` bu qoidani `>= 2` bilan allaqachon
  o'rnatgan.
- **Nima o'zgarmadi:** yukni ko'taradigan da'volar KUCHLIROQ va
  tegilmadi — ikkala SEED bozorida ham **aynan bitta** case bor
  (ya'ni job ikkalasiga ham yetdi) va nosozlik testida
  `len(errors) == 1`.
- **Commit:** `14627f6`

### Rule 2 — rejada yo'q, lekin usiz yuza ishlamasdi

**5. [Rule 2] `CaseListPage.next_cursor`**

- **Topildi:** reja envelope'ni `day` + `rows` + to'rt hisoblagich deb
  sanaydi, lekin AYNI paytda keyset sahifalashni talab qiladi. Kursor
  qaytarilmasa klient uni **o'zi qurishi** kerak bo'lardi — ya'ni
  sahifalash qoidasi serverdan klientga ko'chardi va ikki tomonda
  ajralib ketardi.
- **Commit:** `cad029e`

**6. [Rule 2] Topilmagan case — `LookupError`**

- **Topildi:** reja `transition()` va `case_evidence()` uchun «case yo'q»
  shoxini yozmagan. Jim `return` bilan chaqiruvchi «o'zgardi» deb
  hisoblardi va nazoratchi ekranida hech nima o'zgarmasdi. `ValueError`
  dan ATAYIN farqli tip: `from == to` shoxi bilan aralashib ketmasin.
- **Commit:** `cad029e`

### Struktura bo'yicha ongli qaror

**Sinf A da N+1 so'rov QABUL QILINDI.** Har qarzdor sotuvchi uchun
`vendor_charge_allocation()` chaqiriladi. Yagona muqobil —
`FIFO_OLDEST_SERVICE_DATE_FIRST` ni oyna funksiyasi bilan SQL da qayta
yozish, ya'ni **nomlangan qoidaning ikkinchi nusxasi**;
`allocate_charge_credit()` ning docstringi bu vasvasani nomma-nom
taqiqlaydi. Job kechasi bir marta yuguradi va qarzdorlar soni bozordagi
sotuvchilar sonidan katta emas. Narx kodda ochiq yozildi.

## Ochiq bandlar

**1. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Node yarmi (`pytest tests/unit`) `EXIT=0`. Frontend yarmi
(`npm --prefix frontend test`) ishga tushmadi: worktree'da
`frontend/node_modules` YO'Q (gitignored). Bu **muhit bo'shlig'i, kod
nuqsoni emas** va u bu rejadan MUSTAQIL:
`git diff --name-only 461d5b9 HEAD` — **aynan uchta fayl, uchalasi ham
Python** (`reconciliation_repo.py`, `jobs/reconciliation.py`,
`test_reconciliation_repo.py`). Birorta frontend fayl tegilmagan.
Egasi: orkestrator (07-02 va 07-04 da ham aynan shu band edi).

**2. `DEFAULT_OVERDUE_DAYS` — 07-06 MERGE QILINGANDA BIR MANBAGA
KELTIRILISHI SHART.** Bu reja qiymatni sxemadan hosila qildi; 07-06
esa `app/jobs/notification_meta.py::DEFAULT_OVERDUE_DAYS` ni beradi.
Ikkalasi bugun **bir xil son** beradi, lekin ular ikki mustaqil e'lon —
ya'ni D-32 ning aynan sinfi. Merge'dan keyin **bittasi ikkinchisidan
HOSILA** bo'lishi kerak (tavsiya: `notification_meta` sxemadan o'qisin,
`jobs/reconciliation.py` esa undan import qilsin), NUSXA emas.

**3. `reconciliation_open` HALI ro'yxatga OLINMAGAN va bu KUTILGAN.**
Job callable tayyor, lekin `worker.py` ning cron reyestri, `self_check.
EXPECTED_COMPONENTS` va `alerting._platform_signals::watched` —
**07-14 niki** (reja buni ochiq yozgan va bu ijro `worker.py` ga
TEGMADI). Shu bilan birga: komponent nomi bugun yozilyapti, lekin
**hech kim uni kuzatmayapti** — ya'ni 07-14 gacha `recon.open` ning
o'lib qolishi alert bermaydi. Nom `RECON_OPEN_COMPONENT` konstantasi
bo'lib e'lon qilingani aynan shu ulanishni bir satrga aylantiradi.

**4. `list_cases` filtri `status` bo'yicha, `subject_kind` bo'yicha
EMAS.** Ikki sinfning nisbati RECON-01 ning mazmuni, ya'ni navbat
ekrani bir kun «faqat to'lovsiz» filtrini so'rashi mumkin. Bugun u
YO'Q va bu ONGLI: 07-10 ning API kontrakti hali yozilmagan va filtrni
oldindan qo'shish uni sinalmagan holda qoldirardi. Qo'shilganda u
`_CASE_ROWS` ga bitta `AND (:subject_kind IS NULL OR ...)` bo'ladi va
hisoblagichlarga **tegmasligi** kerak (`_CASE_COUNTS` docstringidagi
sabab).

**5. `transition()` `assignee_user_id` ni `COALESCE` bilan yangilaydi.**
Ya'ni mas'ulni **tozalash** (case'ni egasiz qoldirish) yo'li ATAYIN
yo'q. Agar 07-10 «biriktirishni bekor qilish» amalini talab qilsa, u
alohida argument bilan keladi — `None` ni «o'zgartirma» dan ajratadigan
sentinel kerak bo'ladi.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi qurmaydi; birorta bo'sh qiymat renderga
oqmaydi. `open_cases()` ning nol natijasi **stub emas, javob**: hamma
maydon har doim qaytariladi va nol «case yo'q» degan haqiqiy ma'noga
ega.

## Threat Flags

Yo'q. Yangi tashqi yuza (endpoint, auth yo'li, fayl kirishi) ochilmadi va
**sxema o'zgarishi umuman yo'q** (birorta migratsiya qo'shilmadi), ya'ni
07-04 ning `EXPECTED_DEFINER_FUNCTIONS` **to'plam tengligi** darvozasi
tegilmadi — `pytest tests/tenancy -q` 690 test bilan yashil.

Rejaning `<threat_model>` idagi beshta mitigatsiya bajarildi:

| Threat | Mitigatsiya | O'lchov |
|---|---|---|
| T-07-32 | `active_market_ids()` import qilindi; har bozorga `_tenant_session` | grep = 0 (chetlab o'tuvchi so'rov takrorlanmadi) |
| T-07-33 | Sinf A predikati `vendor_outstanding()` + `vendor_charge_allocation()` dan | to'langan sotuvchi testi + sabotaj |
| T-07-34 | `transition()` ikki yozuv bitta tranzaksiyada | 1 o'tish = 1 qator; 3 o'tish = 3 qator |
| T-07-35 | `overdue_days` majburiy; `no_coverage_stall` qamralmaydi | ikkala nomlangan test yashil |
| T-07-36 | `case_evidence()` faqat `UUID` | grep = 0 + tip asserti |
| T-07-SC | Yangi paket yo'q | `pyproject.toml` tegilmadi |

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `services/core-api/app/repositories/reconciliation_repo.py` ✓ (1143 satr)
- `services/core-api/app/jobs/reconciliation.py` ✓ (382 satr)
- `tests/integration/test_reconciliation_repo.py` ✓ (24 test)
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-07-SUMMARY.md` ✓

Commitlar mavjud: `cad029e` · `c670c6a` · `14627f6` (baza `461d5b9`).

`git diff --diff-filter=D --name-only 461d5b9 HEAD` — **BO'SH**, ya'ni
birorta fayl o'chirilmadi. `git diff --name-only 461d5b9 HEAD` — **aynan
uchta fayl** va uchalasi ham rejaning `files_modified` ro'yxatida.

⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi. `app/worker.py` ham ATAYIN
tegilmadi: cron reyestri 07-14 niki va parallel ijrochilar bilan
to'qnashuvning oldi olindi.
