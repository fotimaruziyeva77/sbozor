---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 12
subsystem: api
tags: [pure-domain, day-close, materialization, wilson, confusion-matrix, rbac, taskiq, cron, ai-04, ai-05, ai-06]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 05
    provides: "`stall_slot_occupancy` (`SLOT_VERDICT_VALUES` superseti, `occupied_has_winning_event`, `no_coverage_is_paired`, `UNIQUE(market, stall, day, slot)`), `ck_review_assignments_eval_needs_blind_audit`, `audit_rounds`, `occupancy_day_close_markets()` va `tests/fixtures/occupancy_domain.py` seed'i"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 11
    provides: "`audit_draw` (namuna, `purpose` kvotasi, `FRAME_PREDICATE`), `QUEUE_TICK_CRON` ning 19:30 qarori, `active_market_ids()` naqshining IKKINCHI tasdig'i va D-16 ning O'LCHANGAN ziddiyati (takroriy band bugungi sxemada IFODALAB BO'LMAYDI)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 10
    provides: "`zone_reviews` javob yozuvi, `decision_ms` ning `NULL` bo'lishi mumkinligi (05-10 ochiq bandi #7), `INSPECTOR_ROUTES` matritsasi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 08
    provides: "`occupancy_events` ga yozadigan `detect` jobi va `no_coverage` ning IKKI manbai (zonasiz kamera, `quality_verdict <> 'ok'`)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 03
    provides: "`frontend/src/lib/wilson.ts` — Wilson formulasi, `Z_95`, `MIN_SAMPLE_FOR_PERCENT` va QO'LDA hisoblangan `0,825`/`0,945` nazorat qiymatlari"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 01
    provides: "`scripts/eval-golden-set.py` — uxlab yotgan darvoza va `ACCURACY_MODULE`/`LOWER_BOUND_ATTR` import nuqtasi"
  - phase: 04-snapshot-pipeline
    provides: "`retention.py::active_market_ids()` (RLS chetlab o'tuvchi YAGONA yuza), `_tenant_session` naqshi, `system_heartbeats` va `worker.py` ning cron ro'yxatga olish shakli"
provides:
  - "`packages/sbozor-core/sbozor_core/occupancy.py` — `effective_verdict()`, `aggregate_stall_slot()`; `__all__` KORTEJ va u ikkinchi daraja agregatsiyasini chegaralaydi"
  - "`app/jobs/day_close.py` — `day_close(business_date)`, `DayCloseResult`, `DAY_CLOSE_COMPONENT`"
  - "`app/repositories/occupancy_repo.py` — `zone_outcomes`, `active_stall_ids`, `day_slot_times`, `materialize`, `day_summary`, `day_stalls`, `accuracy_rows`, `round_status`; `_PER_STALL_CTE` (BITTA bo'lak `CASE`, ikki iste'molchi)"
  - "`app/services/accuracy_report.py` — `wilson_interval`, `confusion_matrix`, `accuracy_report`, `accuracy_lower_wilson_bound`, `is_fast_decision`, `MIN_SAMPLE_FOR_PERCENT`, `Z_95`"
  - "`app/api/v1/occupancy.py` — `GET /occupancy`, `/occupancy/accuracy`, `/occupancy/round` (uchalasi `REPORT_VIEW`)"
  - "`worker.py::occupancy.day_close` — 03:40 (Asia/Tashkent) cron, KECHAGI kunni yopadi"
  - "Sxemalar: `OccupancyDayResponse`, `OccupancyAccuracyResponse`, `OccupancyRoundResponse`, `OccupancyStallItem`, `ConfusionMatrixOut`, `ProportionIntervalOut`"
  - "`MINIMUM_MATRIX_ROUTES` 57 -> 60"
  - "211 yangi test (154 + 15 + 29 + 13) va oltin darvozaning QUROLLANGAN yo'lining birinchi o'lchovi"
affects: [05-13-frontend-sessiya, 05-14-hisobot-ekrani, 05-15-faza-darvozasi, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IKKI XATONING MAXRAJI SPETSIFIKATSIYANING O'Z MISOLIDAN CHIQARILDI: UI-SPEC §11.1 dagi 401/23/38/150 faqat `fp/(tp+fp)` va `fn/(tp+fn)` bilan 5,4 % va 8,7 % beradi — ya'ni maxraj tanlanmadi, O'LCHANDI"
    - "TENGLIK BUZISH TARTIBI MONOTONLIK bilan tanlanadi: «eng kuchsiz dalil yutadi» varianti rad etildi, chunki KAMERA QO'SHISH to'liq tasdiqlangan rastani «hech kim qaramagan» holatiga tushirardi"
    - "SLOTLAR `snapshots` DAN, `occupancy_events` DAN EMAS: qorong'i kadr sloti hodisa yozmaydi va u aks holda hisobotdan BUTUNLAY g'oyib bo'lardi (`no_coverage` nol bo'lib turardi)"
    - "`ON CONFLICT DO UPDATE` va `DO NOTHING` ning farqi DALIL/HOSILA chizig'ida: `occupancy_events` — dalil (append-only), `stall_slot_occupancy` — hosila (kechikkan inson javobi yetib borishi SHART)"
    - "SXEMA IKKI FILTRNI TENG QILIB QO'YGANDA da'vo SOF FUNKSIYA CHEGARASIDA o'lchanadi: `CHECK` ruxsat bermaydigan qator QO'LDA quriladi va da'vo «bugungi kafolat» dan «`CHECK` bo'shatilgan kunga chidamlilik» ga TORAYTIRILADI"
    - "O'LCHANMAGAN MIQDOR UCHUN MAYDON HAM YOZILMAYDI: D-16 hisobotda na son, na `null` maydon — bo'sh maydon keyingi ijrochini unga son yozishga undardi"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/occupancy.py
    - services/core-api/app/jobs/day_close.py
    - services/core-api/app/repositories/occupancy_repo.py
    - services/core-api/app/services/accuracy_report.py
    - services/core-api/app/api/v1/occupancy.py
    - tests/unit/test_aggregate_stall_slot.py
    - tests/unit/test_accuracy_report.py
    - tests/integration/test_day_close.py
    - tests/integration/test_occupancy_report.py
  modified:
    - packages/sbozor-core/sbozor_core/__init__.py
    - services/core-api/app/worker.py
    - services/core-api/app/main.py
    - services/core-api/app/schemas.py
    - scripts/eval-golden-set.py
    - tests/unit/test_golden_harness.py
    - tests/tenancy/test_route_coverage.py
  deleted: []

key-decisions:
  - "⚠⚠ D-16 (nazoratchining ichki mosligi) hisobotda NA SON, NA MAYDON sifatida yo'q — 05-11 ning o'lchangan ziddiyati bo'yicha. UI-SPEC §11.6 uni «namuna holati» blokida SO'RAYDI; reja ham `/occupancy/round` da so'raydi. IKKALASI HAM BAJARILMADI va sabab yozildi: mexanizm QURILMAGAN, ya'ni har qanday son O'LCHANMAGAN bo'lardi"
  - "Tenglik buzish tartibi `human > ai > default_empty` («eng kuchli dalil yutadi»). Rad etilgan variant MONOTON EMAS edi; hozirgi variantda «ko'rilmagani uchun bo'sh» AYNAN nazoratchining yo'qligi hal qilgan rastalarni sanaydi"
  - "Kunlik bo'lak `_PER_STALL_CTE` da BIR MARTA yozilgan va uni xulosa ham, rasta ro'yxati ham ishlatadi: ikki nusxa «xulosada 68, ro'yxatda 69» ni ikkalasi ham xatosiz beradigan holatga olib kelardi"
  - "`day_close` bozorlarni `active_market_ids()` dan oladi: `occupancy_day_close_markets()` kunni `now()` dan oladi va uning `event_count` ustuni BOSHQA kun uchun noto'g'ri son bo'lardi (05-11 deviatsiya #4 ning ikkinchi tasdig'i)"
  - "Cron 03:40 va u KECHAGI kunni yopadi: 19:30 da yopish nazoratchining butun ish oynasini kesib tashlardi va D-19 hisoblagichi HAR KUNI to'la bo'lib, signal doimiy shovqinga aylanardi"
  - "Tizimning `uncertain` javobi matritsada `empty` deb sanaladi va hosila `effective_verdict(..., None)` DAN chiqadi — kun yopilishi YOZADIGAN qiymat bilan hisobot O'LCHAYDIGAN qiymat bir manbadan"
  - "Qamrov to'ri TO'LIQ materializatsiya qilinadi (1000 rasta x 7 slot = kuniga 7000 qator) — ONGLI narx: muqobili («qator yo'q = qamrov yo'q») «kun hali yopilmagan» bilan «kamera ko'rmaydi» ni bir xil ko'rsatardi"
  - "Oltin to'plamga STANDART provayder YOZILMADI: `cv-service` boshqa image va boshqa toolchain, ONNX artefakti esa repoda yo'q — ishga tushmaydigan kod «ulangan» degan yolg'on va'da bo'lardi. O'rniga darvozaning QUROLLANGAN yo'li in'ektsiya qilingan provayder bilan to'liq yuritildi"

patterns-established:
  - "Sabotajning javobi «qaysi test qizardi» emas, «SABAB xabarda ko'rinadimi»: sabotaj D birinchi shaklda `KeyError` berdi (oqibat), test qo'shilgandan keyin esa yo'qolgan slotni NOMMA-NOM ko'rsatdi"
  - "Ikki testning JUFTLIGI bittasining o'zidan kuchli: idempotentlik testi `DO NOTHING` sabotajida YASHIL qoldi va uni faqat «kechikkan javob yetib boradi» testi qizartirdi"
  - "Sxema kafolati testni KO'R qilishi mumkin: `queue_kind` filtrining sabotaji integratsiya testini qizartirmadi (CHECK ikki filtrni teng qiladi) va bu OLDINDAN aytilgan hamda o'lchangan"

requirements-completed: []
requirements-advanced: [AI-04, AI-05, AI-06]
# ⚠ ATAYIN BO'SH — 05-05/05-06/05-10/05-11 dagi bilan AYNAN bir xil qaror.
# AI-05 ning QOIDASI to'liq isbotlandi (120 holatli jadval) va AI-06
# HISOBLANADI, YOZILMAYDI kafolati o'lchandi, lekin uchala talab ham
# EKRANNI talab qiladi: bandlik xulosasi va matritsa 05-14 da, nazoratchi
# sessiyasi 05-13 da. `05-15` fazani DALIL bilan yopadi.

# Metrics
metrics:
  duration_minutes: 175
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 9
  files_modified: 7
  commits: 5
---

# Phase 5 Plan 12: Agregatsiya, kun yopilishi va aniqlik mashinasi — Summary

**Rasta darajasidagi hukm endi sof funksiyadan chiqib `stall_slot_occupancy` ga materializatsiya qilinadi, «ko'rilmagani uchun bo'sh» soxta javob YOZMASDAN hisoblanadi, aniqlik esa faqat ko'r namunaning `eval` qismidan chalkashlik matritsasi bo'lib chiqadi — va ikki xatoning MAXRAJI spetsifikatsiyaning o'z ishlangan misolidan o'lchab olindi.**

## Performance

- **Duration:** ~175 daqiqa
- **Tasks:** 3/3
- **Files:** 9 yaratildi, 7 o'zgartirildi
- **Testlar:** +211 (154 + 15 + 29 + 13); oltin darvoza 6 → **9**

## Task Commits

1. **Task 1 — kameralararo agregatsiya** — `3afcb1c` (feat)
2. **Task 2 — kun yopilishi va materializatsiya** — `280700f` (feat), `f0b9799` (test), `a886e44` (style)
3. **Task 3 — aniqlik hisoboti, `/occupancy` va oltin darvoza** — `5fc785d` (feat)

## Bajarilgan ishlar

### Task 1 — Qoida sof funksiyada, chegara `__all__` da

| Element | Holat |
|---|---|
| `effective_verdict(event, review)` | ✅ uch shox; `uncertain` + javobsiz → `('empty', 'default_empty')` |
| `aggregate_stall_slot([])` | ✅ `('no_coverage', 'no_coverage')` — `empty` **EMAS** |
| Ustuvorlik | ✅ `occupied > uncertain > empty > no_coverage` |
| Tenglik buzish | ✅ `human > ai > default_empty` (pastda — deviatsiya #1) |
| `__all__` | ✅ **KORTEJ**, aynan ikki nom; ikkinchi daraja (BILL-01) eksport qilinmagan |
| `grep sqlalchemy` | ✅ **0** |

**Jadval testi IKKI LITERAL manbadan** va ularning hech biri mahsulot
kodidan hosil qilinmagan: 1–2 kamerali **12 qator** qo'lda yozilgan, 7 ta
verdikt-to'plami esa **120 kombinatsiyani** (3+9+27+81) qoplaydi.
Ikkinchi shakl qo'shimcha DA'VO ham qo'yadi — natija verdiktlar
TO'PLAMIGA bog'liq, tartibga ham, takrorlanish soniga ham **emas**.

### Task 2 — Kun yopiladi, qamrovsizlik KO'RINADI

Uch qadam, bitta tranzaksiya (har bozor uchun alohida):

```
1. faol rastalar        (stalls.status = 'active')
2. kunning slotlari     (snapshots DAN — occupancy_events dan EMAS)
3. zona hodisalari + inson javoblari  ->  sof funksiya  ->  materializatsiya
```

| Kafolat | Mexanizm |
|---|---|
| AI-06 hisoblanadi, yozilmaydi | `zone_reviews` ga yozadigan yo'l faylda MAVJUD EMAS; `test_no_fake_review_row_is_written` sonni oldin va keyin solishtiradi |
| D-22 ko'rinadi | (rasta × slot) to'ri **TO'LIQ** — qamrovsiz katak `no_coverage` bo'lib YOZILADI |
| Idempotentlik | `ON CONFLICT (market, stall, day, slot) DO UPDATE` |
| Kechikkan javob | O'sha `DO UPDATE` — `DO NOTHING` birinchi hisobni MUZLATARDI (D-15) |
| Tranzitiv billing | `winning_occupancy_event_id` → `occupancy_events` → `snapshots (id, is_billable)`; yangi mexanizm o'ylab topilmadi |

`day_summary()` — to'rt o'zaro inkor bo'lak + kesishuvchi
`human_confirmed` + yig'indi guvohi `stalls`. Bo'sh kunda ham AYNAN
bitta qator qaytadi (tashqi `SELECT` agregat, `GROUP BY` yo'q).

Cron: **03:40 (Asia/Tashkent), KECHAGI kunni yopadi.**

### Task 3 — Aniqlik mashinasi ulandi

`accuracy_report()` — ikki filtr (`purpose='eval'`, `queue_kind='blind_audit'`),
javobsizlar SANALADI, «aniq ayta olmayman» matritsadan TASHQARIDA,
`n < 20` da birorta foiz qaytarilmaydi.

**Ikki xatoning maxraji SPETSIFIKATSIYADAN chiqarildi.** UI-SPEC §11.1
ning ishlangan misoli (tp=401, fp=23, fn=38, tn=150) foizlari bilan
birga yozilgan va faqat quyidagi juftlik uni beradi:

| Ko'rsatkich | Formula | Spetsifikatsiya | Hisob |
|---|---|---|---|
| To'g'ri | `(tp+tn)/n` | 90,0 % (87,4–92,2) | 551/612 ✅ |
| **Band deb xato** | `fp/(tp+fp)` | 5,4 % (3,6–8,0) | 23/424 ✅ |
| **Bo'sh deb xato** | `fn/(tp+fn)` | 8,7 % (6,4–11,7) | 38/439 ✅ |
| Bazaviy ulush | `(tp+fn)/n` | 71,7 % | 439/612 ✅ |

Ikkala nisbatni ham `n` ga bo'lish 3,8 % va 6,2 % berardi — **xatosiz**,
lekin boshqa savolga javob bo'lardi. Test
`test_matrix_matches_the_ui_spec_worked_example` uni qulflaydi va
sabotaj H uni qizartirdi.

`/occupancy`, `/occupancy/accuracy`, `/occupancy/round` — uchalasi ham
`REPORT_VIEW` ostida. **Nazoratchida bu huquq yo'q** va uchala marshrut
ham alohida sinaladi.

Oltin to'plam: matematikaning import nuqtasi endi **haqiqatan
yechiladi** (nom, atribut va imzo o'lchanadi) va darvozaning
**QUROLLANGAN yo'li** birinchi marta to'liq yuritildi — sintetik
`karmana` manifesti + in'ektsiya qilingan «har doim band» provayderi
bilan, ikkala chegarada (o'tadi/yiqiladi). Haqiqiy manifest
**tegilmadi**: `test_the_accuracy_gate_is_asleep_today` hamon uxlab
yotgan holatni o'lchaydi.

## Sabotaj o'lchovlari — nima QIZARDI va **nima YASHIL QOLDI**

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --`
**ishlatilmadi**); oxirida `git status` toza.

| # | Sabotaj | NATIJA |
|---|---|---|
| **A** | `_SOURCE_STRENGTH` teskari (`default_empty` yutadi) | 🔴 **AYNAN BITTA** test (`..._evidence_beats_the_absence_of_evidence...`). 153 test **YASHIL** — pastga qarang |
| **B** | `aggregate_stall_slot([])` → `('empty', 'no_coverage')` | 🔴 `test_no_zone_gives_no_coverage_and_never_empty`, va xabar D-22 ni **nomma-nom** ayttirdi (ajratilgan assert tufayli) |
| **C** | Ustuvorlikda `empty` `uncertain` dan yuqori | 🔴 **ikkala literal jadval ham** — `{uncertain, empty}` qatorlari |
| **D** | Slotlar `snapshots` o'rniga `occupancy_events` dan | 🔴 birinchi shaklda **faqat `KeyError`** (oqibat). Test qo'shilgandan keyin 🔴 **2 test** va xabar yo'qolgan slotni ko'rsatdi |
| **E** | `DO UPDATE` → `DO NOTHING` | 🔴 `..._a_later_human_answer_reaches_a_closed_day`.<br>⚠ **`test_rerun_is_idempotent` YASHIL QOLDI** — pastga qarang |
| **F** | Qamrovsiz kataklar o'tkazib yuborildi | 🔴 2 test; jurnalda `no_coverage=0` — jim yo'qotishning aynan shakli |
| **G** | Javobsiz bandlar namunadan tashlandi | 🔴 `test_unanswered_items_stay_in_the_sample` |
| **H** | Ikki xato nisbati ham `n` ga bo'lindi | 🔴 UI-SPEC misoli **va** «ikki xato teng emas» testi |
| **I** | `purpose='eval'` filtri olib tashlandi | 🔴 **3 test**, shu jumladan HAQIQIY baza ustidagi integratsiya testi |
| **J** | `queue_kind='blind_audit'` filtri olib tashlandi | 🔴 faqat **2 sof funksiya testi**.<br>⚠ **INTEGRATSIYA TESTI YASHIL QOLDI** — va bu OLDINDAN aytilgan |
| **K** | `REPORT_VIEW` → `OCCUPANCY_REVIEW` | 🔴 nazoratchi testining **uchala** parametri **va** direktorning nazorat testi |

### A — tenglik buzish qoidasini AYNAN BITTA test qo'riqlaydi

120 holatli sweep sabotaj A ni **umuman ko'rmadi** va sabab mantiqiy:
u manbani `ai` da qotirib qo'yadi, ya'ni tenglik holati unda **mavjud
emas**. `test_a_default_empty_zone_takes_part_as_empty` va
`test_default_empty_survives_only_when_no_zone_had_evidence` ham yashil
qoldi — birinchisida bitta zona, ikkinchisida ikkala zona ham
`default_empty`.

**Xulosa yozib qo'yildi:** katta parametrlangan to'plam KENG, lekin u
faqat O'ZI o'zgartiradigan o'lchamni qamraydi. Tenglik buzish tartibi —
ikkinchi o'lcham va uni bitta, ATAYIN yozilgan test ushlab turadi.

### E — idempotentlik testi «muzlatish» ni AJRATA OLMAYDI

`DO NOTHING` bilan `test_rerun_is_idempotent` **yashil qoladi** va bu
to'g'ri: muzlatilgan jadval ham «ikkinchi yugurish hech nimani
o'zgartirmadi» degan da'voni bajaradi. Ya'ni idempotentlik testi yolg'iz
`DO NOTHING` va `DO UPDATE` ni ajratmaydi.

Ularni faqat **juftlik** ajratadi: `..._a_later_human_answer_reaches_a_
closed_day` aynan shu sababdan yozilgan va u D-15 ni (inson javobi
bandlikni TUZATADI) mahsulot yo'lida qulflaydi.

Bu 05-10 sabotaj B ning aynan sinfi: ikki test ikki xil YARIMNI
o'lchaydi.

### J — SXEMA KAFOLATI TESTNI KO'R QILADI (oldindan aytilgan va o'lchangan)

`queue_kind` filtri olib tashlanganda **integratsiya testi yashil
qoldi**, chunki `ck_review_assignments_eval_needs_blind_audit` (05-05)
`eval` + `uncertain` juftligini bazaga **yozdirmaydi** — ya'ni ikki
filtrni ajratadigan qator mahsulot ma'lumotida **mavjud emas**. Bu
05-10 sabotaj D ning aynan sinfi.

Farq shundaki bu safar u **oldindan aytildi**: modul docstringi, test
docstringi va bu SUMMARY uchalasida ham da'vo TORAYTIRILGAN holda
yozilgan — «funksiya ikkinchi filtrni O'ZI bajaradi va sxemaga
tayanmaydi», ya'ni bu bugungi kafolatning takrori emas, **`CHECK`
bo'shatilgan kunga chidamlilik**. O'lchov sof funksiya chegarasida,
sxema RUXSAT BERMAYDIGAN qator bilan qilinadi.

## Deviations from Plan

### 1. `[Rule 2 - Correctness]` Tenglik buzish tartibi — reja belgilamagan, natija esa unga BOG'LIQ

- **Muammo:** Reja «`resolution_source` g'olib zonanikini oladi» deydi,
  lekin bir necha zona AYNI verdiktni bergan holatni belgilamaydi.
  Tartibsiz shaklda natija kirish TARTIBIGA bog'liq bo'lardi — ya'ni
  rastaning hisobotdagi o'rni zonalar qaysi navbatda o'qilganiga qarab
  o'zgarardi. Bu JIM nosozlik: hisoblagichlar to'g'ri yig'iladi, faqat
  noto'g'ri kataklarga tushadi.
- **Ikki qoida qarama-qarshi edi:**
  - «eng kuchsiz dalil yutadi» (`default_empty > ai > human`) —
    **RAD ETILDI**, chunki u **MONOTON EMAS**: ko'rilmagan zonasi bor
    kameraning QO'SHILISHI to'liq tasdiqlangan rastani «hech kim
    qaramagan» holatiga TUSHIRARDI;
  - «eng kuchli dalil yutadi» (`human > ai > default_empty`) —
    **TANLANDI**: «ko'rilmagani uchun bo'sh» hisoblagichi AYNAN
    nazoratchining yo'qligi verdiktni belgilagan rastalarni sanaydi
    (§C.10 ning «bu raqam katta bo'lsa nazoratchi ulgurmayapti» degan
    BAJARILADIGAN soni) va D-15 ning «Nazoratchi tasdig'i bilan»
    kesishuvchi o'lchami boshqa zona tufayli yo'qolmaydi.
- **Rad etilgan variant kodda NOMMA-NOM yozilgan** (`_SOURCE_STRENGTH`
  docstringi) — bu skanerlanadigan darvoza fayli emas, ya'ni 03-07
  qoidasi bu yerda amal qilmaydi.
- **Commit:** `3afcb1c`

### 2. `[Rule 4 - QAROR]` D-16 hisobotda YO'Q — reja ham, UI-SPEC ham uni SO'RAYDI

- **Muammo:** Reja `/occupancy/round` uchun «ichki moslik (D-16)» ni
  sanaydi; UI-SPEC §11.6 uni «Nazoratchining ichki mosligi: 94 %
  (takroriy 3 banddan)» deb ekranga ham qo'yadi.
- **05-11 buni O'LCHADI va IMKONSIZ deb topdi:**
  `uq_review_assignments_occupancy_event_id` o'sha hodisaga ikkinchi
  topshiriqni, `uq_zone_reviews_review_assignment_id` esa ikkinchi
  javobni rad etadi. Mexanizm QURILMAGAN, ya'ni **o'lchov ham yo'q**.
- **Uch variant ko'rildi:** (a) `100 %` qaytarish — o'lchanmagan
  miqdorni o'lchangan qilib ko'rsatardi (T-05-04); (b) `null` maydon
  qoldirish — keyingi ijrochi «bu yerni to'ldirish kerak ekan» deb
  mavjud bo'lmagan mexanizmga son yozardi; (c) **maydonni umuman
  yozmaslik**.
- **Tuzatish:** (c). Sabab `accuracy_report.py` modul docstringida,
  `OccupancyAccuracyResponse` docstringida va ikkita testda
  (`test_the_report_declares_no_reviewer_self_consistency` — dataclass
  maydonlari AYNAN sanab chiqiladi;
  `test_the_accuracy_response_declares_no_self_consistency` — IKKALA
  javob ham skanerlanadi, chunki moslik «namuna holati» blokiga
  tabiiy ravishda yozilib qolishi mumkin edi).
- **⚠ Oqibat 05-14 uchun:** UI-SPEC §11.6 ning «Ichki moslik» qatori
  **eskirgan** va uni chizadigan komponent yozilmasligi kerak.
- **Commit:** `5fc785d`

### 3. `[Rule 3 - Blocking]` Bozorlar ro'yxati `active_market_ids()` dan

- **Muammo:** Reja `occupancy_day_close_markets()` ni ko'rsatadi.
  Funksiya kunni `now() AT TIME ZONE 'Asia/Tashkent'` dan oladi va uni
  argument qilib bo'lmaydi; bu job esa `business_date` ni argument
  sifatida oladi (`retention_daily(today=...)` qoidasi).
- **Ikkinchi sabab kuchliroq va u 05-11 dagidan FARQ QILADI:** funksiya
  `event_count` ustunini ham qaytaradi va u **har qanday boshqa kun
  uchun noto'g'ri son** bo'lardi — xato bermasdi, faqat mahsulot
  yo'lida jimgina chalg'itardi.
- **Bozorlar TO'PLAMI ikkalasida ham AYNAN bir xil** (`WHERE m.is_active`),
  ya'ni `active_market_ids()` hech nima yo'qotmaydi va yangi
  RLS-chetlab o'tuvchi yuza ochilmaydi.
- **⚠ Oqibat:** `occupancy_day_close_markets()` endi **ikkinchi**
  chaqiruvchisiz `SECURITY DEFINER` funksiya —
  `deferred-items.md` da ochiq band.
- **Commit:** `280700f`

### 4. `[Rule 2 - Correctness]` Slotlar `snapshots` dan, `occupancy_events` dan EMAS

- **Muammo:** Kunning slotlarini bandlik hodisalaridan olish tabiiy
  ko'rinadi va aynan D-22 ni buzardi: kamera qorong'i bo'lgan
  (`quality_verdict <> 'ok'`) yoki birorta zona chizilmagan slotda
  **hodisa yozilmaydi** (05-08 ning ikkala sababi ham xato emas). O'sha
  slot butunlay g'oyib bo'lardi — «hech kim ko'rmagan» slot hisobotda
  UMUMAN ko'rinmasdi va `no_coverage` nol bo'lib turardi.
- **Tuzatish:** doira `snapshots` dan quriladi (kadr olingan slot
  sifati yaroqsiz bo'lsa ham qatorda bor). Sabotaj D buni ikki marta
  o'lchadi.
- **Commit:** `280700f` + `f0b9799`

### 5. `[Rule 2 - Correctness]` Rasta-kun bo'lagi BITTA `CASE` da

- **Muammo:** Xulosadagi hisoblagich (`day_summary`) va ro'yxatdagi
  badge (`day_stalls`) BIR XIL savolga javob beradi. Ikki nusxa
  yozilganda ular sekin-asta ajralib ketardi va nosozlik ENG YOMON
  shaklda ko'rinardi: xulosada «Bo'sh 68», ro'yxatda 69 ta bo'sh rasta
  — **ikkalasi ham xatosiz**.
- **Tuzatish:** `_PER_STALL_CTE` — bitta SQL bo'lagi, ikki iste'molchi.
  `_bucket_params()` parametrlarni ham bir joyda beradi.
- **Commit:** `5fc785d`

### 6. `[Qaror]` «Aniq ayta olmadi» sloti kunlik bo'lakda `empty` ga tushadi

Inson `uncertain` deb javob berganda zona `('uncertain', 'human')`
bo'ladi va u `stall_slot_occupancy` ga SHU HOLICHA yoziladi (sxema
`SLOT_VERDICT_VALUES` da `uncertain` ni ATAYIN qoldirgan).

Kunlik BESH hisoblagich esa UI-SPEC §11.4 da qat'iy va ularning ichida
`uncertain` yo'q. Qaror: bunday rasta `empty` bo'lagiga tushadi va
`human_confirmed` ga ham kiradi. Sabab: uning oqibati «bo'sh» bilan bir
xil (patta yozilmaydi), lekin u «hech kim qaramadi» **emas** —
`default_empty` ga qo'shilsa yo'qotish signali nazoratchi ISHLAGAN
holatlar bilan shishirilardi.

### 7. `[Qaror]` Oltin to'plamga standart provayder YOZILMADI

Reja «verdikt provayderi sifatida `cv-service` ning `zone_verdict`
yo'lini oladi» deydi. **Bajarilmadi**, sabab uch qatlamli:

1. `cv-service` — **boshqa image va boshqa toolchain**
   (`onnxruntime`/`supervision` `tests` konteynerida o'rnatilmagan;
   `mypy` uni ATAYIN istisno qiladi — ikki `app` paketi to'qnashadi);
2. ONNX artefakti repoda **saqlanmaydi** (D-24, `.gitignore`);
3. Ya'ni yozilgan provayder **birorta muhitda ishga tushmasdi** —
   «ulangan» degan yolg'on va'da bo'lardi (05-11 deviatsiya #1 ning
   «iste'molchisiz sozlama» qoidasi bilan bir sinf).

**Niyat esa saqlandi va KUCHAYTIRILDI:**

| Da'vo | Mexanizm |
|---|---|
| Matematika import qilinadi, takrorlanmaydi | Import nuqtasi endi **yechiladi**: nom, atribut VA imzo o'lchanadi (`lower_bound(90, 100) ≈ 0,8256`) |
| Darvoza uyg'onganda ISHLAYDI | QUROLLANGAN yo'l sintetik `karmana` manifesti + in'ektsiya qilingan provayder bilan **ikkala chegarada** yuritiladi (o'tadi va yiqiladi) |
| Provayder yo'qligi JIMGINA o'tmaydi | `SystemExit` xabari endi provayderning MANBASINI nomma-nom aytadi va test uni tekshiradi |

Haqiqiy manifest **tegilmadi**: `karmana` yozuvlari hamon **0**.

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| Task 1 to'plami | `pytest tests/unit/test_aggregate_stall_slot.py` | ✅ **154** |
| Task 2 to'plami | `pytest tests/integration/test_day_close.py` | ✅ **15** |
| Task 3 (sof) | `pytest tests/unit/test_accuracy_report.py` | ✅ **29** |
| Task 3 (API) | `pytest tests/integration/test_occupancy_report.py` | ✅ **13** |
| Oltin darvoza | `pytest -m golden` | ✅ **9** (bazaviy 6 + 3) |
| `core-api` to'liq to'plami | `pytest -q --deselect <soat bog'liq test>` | ✅ **exit 0**, **2360** yig'ildi (1 tasi chiqarildi) |
| `core-api` tenancy | `pytest tests/tenancy` | ✅ **548 passed** (bazaviy **536** + 12) |
| `core-api` lint/tiplar | `ruff check . && ruff format --check . && mypy .` | ✅ toza (**288** formatlangan, **278** tiplangan fayl) |
| `cv-tests` | `npm run cv:test` | ✅ **130** — o'zgarmadi (bu reja `cv-service` ga tegmadi) |
| `vitest run` | frontend | ✅ **494 (35 fayl)** — o'zgarmadi |
| `npm run i18n:check` | | ✅ **879 × 3** — o'zgarmadi |
| `npm run gate` | to'liq zanjir | ⚠ **exit 1** — YAGONA nosozlik SOAT BOG'LIQ, pastga qarang |
| `grep -cE "^\s*def (wilson\|confusion)" scripts/eval-golden-set.py` | | ✅ **0** |
| `grep -c sqlalchemy .../occupancy.py` | | ✅ **0** |

⚠ **BAZAVIY SON O'LCHOV BIRLIGI BILAN SOLISHTIRILMAYDI** (05-11 ning
ogohlantirishi kuchda): bu yerdagi **2360** — `collected`, 05-11 dagi
**2134** esa `passed`. Ikkisini ayirib «+226 test» deb yozish ikki xil
o'lchovni tenglashtirardi. **O'LCHANGAN va SOLISHTIRILADIGAN yagona
farq — `tests/tenancy`: 536 → 548** (ikkalasi ham `passed`) va u aynan
uch yangi marshrutning matritsadagi to'rttadan qatoriga to'g'ri keladi.

### ⚠⚠ `npm run gate` EXIT 1 — VA SABAB O'LCHANGAN

**Yagona nosozlik:**
`tests/integration/test_alerting.py::test_an_old_alert_escalates_by_level_not_by_frequency`

Test `moment = datetime.now(tz=MARKET_TZ)` oladi va ikkinchi supurgini
`moment + 3 soat 1 daqiqa` bilan chaqiradi. Mahalliy vaqt **20:59 dan
keyin** bo'lganda ikkinchi nuqta YARIM TUNDAN o'tadi, ya'ni boshqa
biznes-kunga tushadi va «o'tkazib yuborilgan slot» sharti UMUMAN
mavjud bo'lmaydi — alert eskalatsiya qilinmay **hal qilinadi**
(`resolved=1`, yugurish chiqishida ko'rinib turibdi).

**Nega bu 05-12 ning bandi EMAS — uch mustaqil o'lchov:**

1. `tests/integration/test_alerting.py` va `app/jobs/alerting.py`
   ikkalasi ham `b5d4f78` (05-12 dan OLDINGI HEAD) dagi bilan
   **bayt-bayt bir xil** (`git hash-object` bilan solishtirildi);
2. ikkala faylda ham `day_close`, `occupancy_repo`, `accuracy_report`
   yoki `sbozor_core.occupancy` **umuman uchramaydi** — import yo'li yo'q;
3. o'sha bitta test CHIQARIB tashlanganda to'liq to'plam **exit 0**
   beradi (2360 yig'ildi).

**Falsifikatsiya qilinadigan bashorat:** bu test mahalliy vaqt **20:59
dan OLDIN** yuritilganda o'tadi. 05-11 ning SUMMARY si to'liq to'plamni
o'sha kuni ertaroq `exit 0` deb yozgan va bu bashorat bilan MOS.

Band `deferred-items.md` da yozildi; tuzatish `04-08` ning fayliga
tegadi va uning egasi `05-15`.

### ⚠ TO'RTTA SIM NOSOZLIGI — MENING O'Z ZANJIRIM KELTIRIB CHIQARDI

Birinchi `npm run gate` yugurishida yana **to'rtta** nosozlik bo'lgan
(`test_nvr_errors.py` 2 ta, `test_nvr_discovery_job.py` 2 ta). Sabab
o'lchandi va u **kodda emas**: men o'sha paytda BIR VAQTDA uchta Docker
yukini yuritayotgan edim, `docker compose` esa bu worktree'da ham
**umumiy `sbozor` loyihasiga** hal bo'ladi (05-08 ning 6-kuzatuvi).
`test_nvr_errors.py` esa simulyatorning REJIMINI o'zgartiradi
(`sim_mode(sim, "slow", delay_ms=15000)`) — ya'ni ikki parallel to'plam
bir simulyatorni boshqarib, bir-birining rejimini bekor qilgan
(alomat: `ok=True`, sekin rejim umuman ishlamagan).

**Yakka yugurishda to'rttasi ham YASHIL** — ya'ni o'lchov takrorlandi va
sabab tasdiqlandi. Bu SUMMARY ga yozildi, chunki «gate yashil emas»
degan faktni izohsiz qoldirish keyingi ijrochini noto'g'ri joyga
yuborardi.

## Known Stubs

**Yo'q** — soxta ma'lumot manbai ham, placeholder matn ham yaratilmadi.
Ikki band ATAYIN «hozircha to'liq emas» va ular stub EMAS:

| Nima | Nega stub emas |
|---|---|
| Oltin to'plam provayderi `None` | Bu **qaror** (deviatsiya #7), yarim tayyor kod emas: uning o'rniga hech nima qo'yilmagan va darvoza provaydersiz **BALAND ovozda** yiqiladi. Chok (`VerdictProvider`) 05-01 da e'lon qilingan va u endi in'ektsiya bilan **to'liq yuritiladi** |
| `/occupancy` javobining EKRANI yo'q | Ekran 05-14 ning ishi. Yuza `curl` bilan to'liq ishlaydi va 13 test bilan o'lchangan |

⚠ **D-16 — stub EMAS, MEROS QILIB OLINGAN O'LCHANGAN ZIDDIYAT.**
Maydon yozilmadi va uning o'rniga hech nima qo'yilmadi.

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-55 (aniqlik raqami) | mitigate | Ikki filtr, **ikki alohida test**; `train` filtri HAQIQIY baza ustida ham o'lchandi (sabotaj I uni 3 testda qizartirdi). ⚠ `queue_kind` filtri mahsulot ma'lumotida o'lchanmaydi — da'vo TORAYTIRILGAN (sabotaj J) |
| T-05-56 (soxta «nazoratchi tasdig'i») | mitigate | `zone_reviews` ga yozadigan yo'l `day_close.py` da MAVJUD EMAS; `test_no_fake_review_row_is_written` sonni oldin/keyin solishtiradi va nazorat asserti bilan keladi |
| T-05-57 (yaroqsiz kadr → hisob) | mitigate | `winning_occupancy_event_id` FK + `CHECK`; **zanjirning IKKALA halqasi** ham o'lchanadi (ikkinchisi nazorat sifatida) |
| T-05-58 (nazoratchiga o'z aniqligi) | mitigate | Uchala marshrut `REPORT_VIEW`; nazoratchi uchun **uchalasi ham alohida** 403 bilan sinaladi + direktorning nazorat testi (sabotaj K ikkalasini ham qizartirdi) |
| T-05-59 (jimgina yo'qotish) | mitigate | `default_empty` ALOHIDA bo'lak; besh hisoblagich NOL bo'lganda ham qaytadi (`test_the_day_report_returns_five_counters_even_at_zero`) |
| T-05-60 («aniqlik» ni yolg'iz e'lon qilish) | mitigate | `base_rate` MAJBURIY maydon; `n < 20` da BIRORTA foiz maydoni `None`; matritsa har doim xom sonlar bilan |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authorization-gap | `services/core-api/app/api/v1/snapshots.py` | ⚠ **05-10/05-11 dan MEROS va u KUCHDA:** `GET /snapshots/{id}/image` `CAMERA_VIEW` talab qiladi, `ROLE_PERMISSIONS[INSPECTOR]` esa aynan `{OCCUPANCY_REVIEW}`. Bu reja `rbac.py` ga ham, `snapshots.py` ga ham **tegmadi** (M-8) |

**Bu rejaning O'Z yuzasida yangi tahdid topilmadi.** Uchala marshrut ham
`REPORT_VIEW` ostida va javoblarida shaxsiy ma'lumot yo'q; `_market_id()`
tenant chegarasini `reviews.py` bilan bir xil shaklda oladi.

## Keyingi rejalar uchun ochiq bandlar

1. **⚠⚠ `05-14` uchun — UI-SPEC §11.6 ning «Ichki moslik» qatori
   ESKIRGAN.** Server bu maydonni **qaytarmaydi** va qaytarmasligi
   kerak (deviatsiya #2). Uni ekranda «100 %» yoki «—» qilib chizish
   ham TAQIQLANADI — o'lchanmagan miqdor ko'rilgan zahoti o'lchangan
   deb o'qiladi (T-05-04).
2. **`05-14` uchun:** `GET /occupancy/accuracy` javobida `min_sample`
   maydoni bor — klient `MIN_SAMPLE_FOR_PERCENT` ni **o'zi yozmasligi**
   kerak. `lib/wilson.ts` dagi konstanta hamon 20 va u server bilan
   matn darajasida qulflangan (`test_the_shared_constants_match_the_client`).
3. **`05-14` uchun:** besh hisoblagich `stalls` bilan birga qaytadi va
   to'rtta bo'lakning yig'indisi unga TENG — sarlavhadagi «Rasta N ta»
   shu maydondan olinadi, klientda qayta jamlanmaydi.
4. **`05-14` uchun:** `GET /occupancy/round` da `drawn: false` bo'lsa
   qolgan maydonlar `null` — «tur tortilmagan» va «hammasi bajarildi»
   ikki xil holat va ekran ham ularni ajratishi shart.
5. **`05-15` uchun:** `MINIMUM_MATRIX_ROUTES` endi **60**.
   `INSPECTOR_ROUTES` ga yangi marshrut **qo'shilmadi** (uchalasi ham
   `REPORT_VIEW`).
6. **`05-15` uchun:** `deferred-items.md` da ikki band —
   `test_alerting.py` ning soat bog'liq nosozligi (bu reja tegmagan
   fayl, o'lchov bilan tasdiqlangan) va ikkita chaqiruvchisiz
   `SECURITY DEFINER` funksiya.
7. **`06-billing` uchun:** ikkinchi daraja agregatsiyasi (slotlararo)
   **YOZILMAGAN** va `sbozor_core.occupancy.__all__` uni eksport
   qilmaydi. `day_summary()` dagi kunlik yig'ish — **ko'rsatish**
   yig'indisi va u `sbozor_core` ga funksiya sifatida ATAYIN
   chiqarilmagan.
8. **Operatsion:** `day_close` **03:40** da ishlaydi va **KECHAGI**
   kunni yopadi, ya'ni direktor bugungi bandlikni ertasi kuni ertalab
   ko'radi. Bu `05-HUMAN-UAT` da ochiq aytilishi kerak.
9. **Hajm kuzatuvi:** materializatsiya kuniga ~`faol rasta × slot`
   qator yozadi (1000 × 7 = 7000). Bir yillik arxiv ~2,5 mln qator —
   4-fazadagi `snapshots` bilan bir tartibda, lekin `05-15` ning
   retention ko'rigida qayd etilsin.

## Self-Check: PASSED

- E'lon qilingan **9 yaratilgan + 7 o'zgartirilgan** fayl —
  `git diff --name-only 3afcb1c~1..HEAD` **16 fayl** beradi va
  hammasi diskda;
- `3afcb1c`, `280700f`, `f0b9799`, `a886e44`, `5fc785d` — beshala
  commit ham `git log` da;
- Sabotajlardan keyin to'plamlar qayta yugurtirildi va `git status`
  toza — har biri `cp` bilan snapshotdan tiklandi, `git checkout --`
  **ishlatilmadi**;
- `npm run gate` ning yagona qizil bandi **o'lchov bilan** shu rejadan
  tashqarida ekani tasdiqlandi (uch mustaqil dalil, yuqorida).

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
