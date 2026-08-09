---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 11
subsystem: api
tags: [taskiq, cron, sha256, derived-seed, blind-audit, openapi-gate, sampling, rls, ai-04]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 01
    provides: "W0-3 O'LCHOVI (`AUDIT_SEED_SHA256_SUPPORTED = true`, `PGCRYPTO_ABSENT = true`) va `_SAMPLE_SQL` ning tayyor shakli; sabotaj C ning darsi — nazorat holatisiz «qayta chiqariladi» da'vosi «urug' ishlamaydi» degani bo'lishi mumkin"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 05
    provides: "`audit_rounds` (`frame_size`/`frame_predicate_hash`/`drawn_at`), `UNIQUE (occupancy_event_id)`, `UNIQUE (review_assignment_id)`, `fk_zone_reviews_queue_kind_anchor` langari, `ck_review_assignments_eval_needs_blind_audit`, shartsiz o'zgarmaslik triggeri va `tests/fixtures/occupancy_domain.py` seed'i"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 10
    provides: "`review_repo` (`build_uncertain_queue`, `claim_next`, `record_answer`, `_PRIORITY_ORDER`), `reviews.py` routeri, `AnswerRequest`/`AnswerResponse`, `INSPECTOR_ROUTES` matritsasi va sabotaj D ning darsi (da'vo o'lchanadigan farqdan chiqishi kerak)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 03
    provides: "`blind-payload.test.mjs` (G-12/G-14) — oshkor javobning maydon nomlari AYNAN shu darvoza tufayli `verdict`/`confidence` dan farq qiladi"
  - phase: 04-snapshot-pipeline
    provides: "`alerting.py::_tenant_session` va `retention.py::active_market_ids()` (RLS chetlab o'tuvchi YAGONA yuza); `worker.py` ning cron ro'yxatga olish shakli va `MARKET_CRON_OFFSET` qoidasi"
provides:
  - "`app/jobs/audit_draw.py` — `audit_draw()`, `daily_queue_tick()`, `QueueTickPolicy`, `FRAME_PREDICATE`/`FRAME_PREDICATE_HASH`, `FIRST_ROUND_NO`, `eval_quota()`"
  - "`worker.py::review.queue_tick` — 19:30 (Asia/Tashkent) kunlik cron va `QUEUE_TICK_CRON` ning xolislik asosi"
  - "`Settings.review_blind_eval_ratio` (0,70); namuna hajmi `review_blind_daily_budget` dan (IKKINCHI sozlama ATAYIN yozilmagan)"
  - "`BlindItemResponse` — o'n maydon; sakkizala AI/tortish maydoni E'LON QILINMAGAN va `has_active_vendor` ham YO'Q"
  - "`GET /review/blind/next` va `POST /review/blind/{review_assignment_id}/answer` (`409 blind_answer_locked`)"
  - "`review_repo`: `_CLAIM_TEMPLATE` (yagona `SELECT`, o'zgaruvchi `ORDER BY`), `_BLIND_ORDER`, `claim_next_blind()`, `has_any_round()`"
  - "`tests/integration/test_blind_audit.py` — 33 test, olti nomlangan invariant + qayta tortish skani + D-16 ning o'lchangan ziddiyati"
  - "`MINIMUM_MATRIX_ROUTES` 55 -> 57; `INSPECTOR_ROUTES` +2"
affects: [05-12-agregatsiya, 05-13-frontend-sessiya, 05-14-hisobot, 05-15-faza-darvozasi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "URUG' SQL DA HOSILA, mustaqil qayta hisoblash esa TESTDA `hashlib` bilan — «qayta chiqariladi» da'vosi bitta kod yo'lini takrorlab tasdiqlanmaydi"
    - "TARTIB kod bilan, CADENCE bitta job bilan majburlanadi: ikki qadam ikki cron bo'lsa kafolat cron SATRLARIGA ko'chib ketardi"
    - "Kvota `numeric` da; da'vo o'lchov bilan TORAYTIRILDI (0,70 da farq YO'Q, 0,28x25 da BOR) — ya'ni himoya bugungi qiymatni emas, SOZLANADIGAN qiymatni qo'riqlaydi"
    - "Bitta `SELECT` shabloni, ikki `ORDER BY`: navbatlar bir xil MA'LUMOTNI, boshqa TARTIBDA ko'radi va nusxa olinmaydi"
    - "«Bo'shlik» ikki sababga ajratiladi (`review_sample_not_drawn` / `review_queue_empty`) — asbobning YO'QLIGI muvaffaqiyat bo'lib ko'rinmasin"
    - "Statik matn darvozasi IDENTIFIKATOR chegarasida ishlaydi: `digest(` taqiqlanadi, `hexdigest(` — yo'q, va ikkala yo'nalish ham nazorat testiga ega"

key-files:
  created:
    - services/core-api/app/jobs/audit_draw.py
    - tests/integration/test_blind_audit.py
  modified:
    - services/core-api/app/settings.py
    - services/core-api/app/worker.py
    - services/core-api/app/schemas.py
    - services/core-api/app/repositories/review_repo.py
    - services/core-api/app/api/v1/reviews.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
  deleted: []

key-decisions:
  - "⚠⚠ D-16 (~10% takroriy band) BUGUNGI SXEMADA IFODALAB BO'LMAYDI va bu O'LCHANDI: `uq_review_assignments_occupancy_event_id` ikkinchi topshiriqni, `uq_zone_reviews_review_assignment_id` esa ikkinchi javobni rad etadi. 5-himoyani qurish 3- yoki 4-himoyani BO'SHATISHNI talab qilardi. `BLIND_AUDIT_REPEAT_RATIO` ATAYIN yozilmadi (iste'molchisiz sozlama yolg'on va'da)"
  - "Bozorlar ro'yxati `active_market_ids()` dan, `audit_draw_due_markets()` dan EMAS: funksiya kunni `now()` dan oladi va uni argument qilib bo'lmaydi; `frame_size` esa `INSERT` bilan BIR tranzaksiyada o'lchanishi kerak"
  - "Namuna hajmi uchun IKKINCHI sozlama yozilmadi — D-13 bitta son beradi; ikki sozlamaning ajralishi ikkala yo'nalishda ham JIM nosozlik"
  - "`QUEUE_TICK_CRON` 19:30 va IKKALA qadam bitta vazifada: kun o'rtasida tortilgan namuna faqat ertalabki slotlardan iborat bo'lardi, noaniq navbat esa soat sayin qurilsa `uncertain` larni doiradan JIMGINA yeb qo'yardi"
  - "`FIRST_ROUND_NO` KONSTANTA, `max(round_no) + 1` EMAS — o'sha bir satr «qaytadan tortaman» yo'lini ochardi"
  - "`purpose` KVOTA (`ceil(ratio * drawn)`), tanga tashlash EMAS: mustaqil tanga Binomial(30, 0.7) berib kunlik nisbatni 60–80% orasida sakratardi"
  - "`BlindItemResponse` da `has_active_vendor` YO'Q (noaniq navbatda BOR): tasodifiy namunadagi «bu qarorning oqibati bor» qatori diqqatni NOTEKIS taqsimlardi va bu o'lchov asbobining O'ZIDAGI og'ish"
  - "Ko'r navbat `ORDER BY ra.id`, `_PRIORITY_ORDER` EMAS: ustuvorlik bo'yicha saralangan quyruq javobsiz qolganda TIZIMLI ravishda sotuvchisiz rastalardan iborat bo'lardi"
  - "Ko'r audit ALOHIDA marshrut, `?blind=true` bayrog'i EMAS — bitta serializer «maydon yo'q» kafolatini SHARTLI qilardi, ya'ni konventsiyaga aylantirardi"
  - "Marshrut OpenAPI sxemasida KO'RINADI: yashirish hujjatni o'zgartiradi, baytlarni emas"

patterns-established:
  - "Sabotaj TIZIMGA YETIB BORDIMI degan savol sabotajning O'ZIDAN oldin turadi: 05-11 da trigger COMPOSE bazasida o'chirildi va 33 test yashil qoldi, chunki to'plam O'Z testcontainer'ida yuguradi"
  - "«Nazorat holati» testining O'Z chegarasi ham o'lchanadi: sabotaj B da `!=` sharti yashil qoldi (urug'siz tartib UCHINCHI to'plam beradi), ya'ni nazorat faqat JUFTLIKDA ma'noga ega"
  - "Reja bergan sabab YOLG'ON bo'lishi mumkin: `float` kvotasi bugungi nisbatda farq bermaydi — da'vo o'lchov bilan toraytirildi va SOZLANADIGAN qiymatga bog'landi"

requirements-completed: []
requirements-advanced: [AI-04]
# ⚠ ATAYIN BO'SH — 05-05/05-06/05-10 dagi bilan AYNAN bir xil qaror.
# Bu reja AI-04 ning O'LCHOV MEXANIZMINI to'liq yetkazadi (namuna, ko'rlik,
# o'zgarmaslik, 70/30), lekin talabni YOPMAYDI: AI-04 xolis ANIQLIK
# HISOBOTINI talab qiladi va u 05-14 da (`accuracy_report`), ekrani esa
# 05-13 da. `05-15` fazani DALIL bilan yopadi.

# Metrics
metrics:
  duration_minutes: 205
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 2
  files_modified: 7
  commits: 3
---

# Phase 5 Plan 11: Ko'r audit — hosila urug', muzlatilgan doira va beshta strukturaviy himoya — Summary

**Nazoratchi endi tizim javobini KO'RMASDAN, hosila urug' bilan tasodifiy tanlangan va muzlatilgan doiradan tortilgan namunani baholaydi; beshala himoyaning to'rttasi kodda va sxemada o'lchandi, beshinchisi (D-16 takroriy band) esa bugungi sxemada IFODALAB BO'LMASLIGI isbotlandi va yolg'on mexanizm QURILMADI.**

## Performance

- **Duration:** ~205 daqiqa
- **Tasks:** 3/3
- **Files:** 2 yaratildi, 7 o'zgartirildi

## Task Commits

1. **Task 1 — `jobs/audit_draw.py`, sozlama va cron** — `b97e989` (feat)
2. **Task 2 — ko'r serializer, ikki marshrut va matritsa** — `1fcd96f` (feat)
3. **Task 3 — SC#4 ning olti invarianti va sabotajlar** — `ae54a38` (test)

## Bajarilgan ishlar

### Task 1 — Namuna tortiladi, doira muzlaydi

| Element | Holat |
|---|---|
| `seed = sha256(market_id \|'\|' \| day \|'\|' \| round)` | ✅ **SQL da** (`_DRAW_SAMPLE` ning `derived_seed` CTE si) |
| Namuna tartibi | ✅ `ORDER BY sha256((ev.id::text \|\| seed)::bytea)` |
| Doira | ✅ `FRAME_PREDICATE` — kunning BARCHA `is_billable` hodisalari, `verdict` filtri YO'Q |
| `frame_size` / `frame_predicate_hash` / `drawn_at` | ✅ `audit_rounds` ga, `INSERT` bilan BIR tranzaksiyada |
| 70/30 | ✅ IKKINCHI, mustaqil hash tartibi (`\|purpose`) + `ceil(ratio * drawn)` kvotasi |
| Qayta tortish | ⛔ `NOT EXISTS` + `FIRST_ROUND_NO` konstantasi; endpoint YO'Q |
| Tartib | ✅ `daily_queue_tick()` — avval tortish, keyin noaniq navbat |

**Urug' SQL da hosil qilinadi, testda esa `hashlib` bilan MUSTAQIL qayta
hisoblanadi.** Jobni ikkinchi marta chaqirish faqat uning O'Z determinizmini
o'lchardi; ikki mustaqil implementatsiyaning bir to'plamga kelishi esa
formulani o'lchaydi.

**Uch tip kasti (`::uuid`, `::date`, `::text::numeric`) bezak emas:**
`asyncpg` parametr tipini so'rov kontekstidan chiqaradi va kastsiz
`SELECT $1` uni `text` deb baholab `UUID` obyektini rad etardi.

### Task 2 — Ko'rlik payload SHAKLIDA

`BlindItemResponse` — **o'n maydon**. `verdict`, `confidence`,
`model_version`, `thresholds_version`, `effective_verdict`,
`resolution_source`, `shown_ai_verdict`, `purpose` — **kalitlarining
o'zi e'lon qilinmagan**.

⛔ **`has_active_vendor` ham yo'q, holbuki noaniq navbatda u BOR.**
Farq — Rule 2 deviatsiyasi va u pastda yozilgan.

Ikki marshrut: `GET /review/blind/next` (URL'da identifikator YO'Q) va
`POST /review/blind/{review_assignment_id}/answer` (ikkinchi chaqiruv →
**409 `blind_answer_locked`**). `AnswerResponse` **qayta ishlatildi** —
05-10 uni aynan shu marshrut uchun tanlagan edi.

Bo'shlikning ikki sababi ikki kodga ajratildi: `review_sample_not_drawn`
(asbob HALI ISHLAMAGAN) va `review_queue_empty` (ish TUGADI).

### Task 3 — Olti invariant, uch qo'shimcha va uch sabotaj

`tests/integration/test_blind_audit.py` — **33 test**. Olti nomlangan
invariant plan bergan nomlar bilan; qo'shimchalar: `test_no_redraw_endpoint`
(ikki mustaqil predikat), `test_answer_is_locked_after_reveal`,
`test_repeat_items_are_indistinguishable_in_payload`.

## Sabotaj o'lchovlari — nima QIZARDI va **nima YASHIL QOLDI**

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --`
**ishlatilmadi**); oxirida `git status` toza.

| # | Sabotaj | NATIJA |
|---|---|---|
| **A** | `BlindItemResponse` ga `confidence: float \| None = None` | 🔴 **1-invariant** (`test_payload_has_no_verdict_keys`) + tipdan hosila ikkinchi qatlam + payload-shakli testi. **2–6 invariantlar YASHIL** — reja aytgandek |
| **B** | `ORDER BY` dan urug' olib tashlandi (`sha256((ev.id::text)::bytea)`) | 🔴 **2-invariant** (`test_sample_is_reproducible`) + `purpose` kvotasi testi. **1 va 5 YASHIL** — reja aytgandek.<br>⚠⚠ **NAZORAT TESTI (`..._different_round_number_...`) HAM YASHIL QOLDI** — pastga qarang |
| **C′** | `trg_zone_review_immutable` COMPOSE bazasida `DROP` qilindi | ⚠⚠ **33 TESTNING HAMMASI YASHIL** — va bu test kuchsizligi EMAS |
| **C** | O'sha trigger `0018` ning `attach_immutability_trigger` sikldan chiqarildi | 🔴 **AYNAN 6-invariant** (`test_review_is_immutable`), **1–5 YASHIL** — reja aytgandek |

### C′ — sabotaj tizimga YETIB BORMAGAN edi

`tests/conftest.py::pg_container` `TEST_DATABASE_URL` bo'lmaganda **O'Z
`postgres:18.4-trixie` testcontainer'ini** ko'taradi, `compose.yaml` da esa
bu o'zgaruvchi yo'q. Ya'ni `docker compose exec db psql ... DROP TRIGGER`
**boshqa bazaga** tegdi va to'plam sabotajni umuman ko'rmadi.

Xulosa naqsh sifatida yozildi: **«sabotaj o'lchanayotgan tizimga yetib
bordimi?» savoli sabotajning O'ZIDAN oldin turadi.** Yashil natijani darhol
«test kuchsiz» deb o'qish 05-08 va 05-10 dagi haqiqiy topilmalarni ham
qadrsizlantirardi. Tuzatilgan shakl (`0018` ni tahrirlash) aynan bitta
testni qizartirdi.

### B — nazorat testining O'Z chegarasi

Urug' `ORDER BY` dan olib tashlanganda `test_a_different_round_number_draws_
a_different_sample` **yashil qoldi** va sabab mantiqiy: urug'siz tartib
**uchinchi** to'plamni beradi, ya'ni u 1- va 2-tur to'plamlarining
ikkalasidan ham farq qiladi va `!=` bajarilaveradi.

Demak `!=` yolg'iz hech nimani qo'riqlamaydi — u faqat
`test_sample_is_reproducible` (baza = 1-tur) bilan **juftlikda** ma'noga
ega. Testga bazadan **mutlaqo mustaqil** uchinchi shart qo'shildi
(«urug'ning o'zi formulaning natijasini o'zgartiradimi»), ya'ni u endi
urug' butunlay e'tiborsiz qoldirilgan formulani **yolg'iz** ham ushlaydi.

Bu 05-01 sabotaj C ning teskari yarmi: o'shanda reproduksiya testi yashil
qolgan edi, bu safar nazorat testi.

## Deviations from Plan

### 1. `[Rule 4 — QAROR]` D-16 (~10% takroriy band) QURILMADI — sabab O'LCHANDI

- **Muammo:** Reja «namunaning ~10% i oldin ko'rilgan bandlardan qayta
  olinadi» deydi. 05-05 sxemasi buni **ikki mustaqil joyda** imkonsiz
  qiladi: `uq_review_assignments_occupancy_event_id` o'sha hodisaga
  ikkinchi topshiriqni, `uq_zone_reviews_review_assignment_id` esa o'sha
  topshiriqqa ikkinchi javobni rad etadi.
- **Ya'ni 5-himoyani qurish 3- yoki 4-himoyani BO'SHATISHNI talab qilardi.**
  Bu texnik tanlov emas, **arxitektura qarori** (yangi migratsiya, `UNIQUE`
  ni qisman indeksga aylantirish, uchinchi langar FK) — Rule 4.
- **Rad etilgan «ishlaydigan» muqobil:** takroriy bandni *boshqa hodisa*
  (bir rasta, boshqa kun/slot) qilib berish. U **o'zini-o'zi mosligini
  o'lchamasdi** — ikki kadrda haqiqat ham boshqacha bo'lishi mumkin, ya'ni
  natija «nazoratchi izchilmi?» degan savolga javob bermay, o'lchovga
  o'xshagan raqam ishlab chiqarardi. Aynan shu reja oldini olishi kerak
  bo'lgan nosozlik sinfi.
- **Tuzatish:** (a) ziddiyat `test_a_repeat_band_is_structurally_impossible_
  today` bilan **bajariladigan o'lchovga** aylantirildi — yo'l ochilgan kuni
  darvoza qizaradi va qaror ongli qabul qilinadi; (b)
  `test_repeat_items_are_indistinguishable_in_payload` **kuchliroq**
  shaklga toraytirildi: tortish paytidagi HAR QANDAY belgi (bugun
  `purpose` ning ikkala qiymati) payloadda farq bermaydi va kalit to'plami
  `BlindItemResponse` bilan **yopiq**; (c) `BLIND_AUDIT_REPEAT_RATIO`
  sozlamasi **yozilmadi** — iste'molchisiz sozlama «bu ishlaydi» degan
  yolg'on va'da bo'lardi.
- **Commit:** `ae54a38`

### 2. `[Rule 2 - Correctness]` `has_active_vendor` KO'R payloadda YO'Q

- **Muammo:** Reja `BlindItemResponse` uchun aynan sakkizta taqiqlangan
  nomni sanaydi va `has_active_vendor` ular orasida yo'q. Noaniq navbatda
  o'sha qator **motivatsiya** (band ustuvorlik bilan tanlangan, oqibati
  bor). Ko'r auditda band **tasodifiy** tanlangan, ya'ni o'sha qator
  namunaning bir qismiga ko'proq, qolganiga kamroq e'tibor berdirardi.
- **Xolis namunadagi notekis diqqat — o'lchov asbobining O'ZIDAGI og'ish**
  va u aniqlikni «oqibati bor» rastalar tomonga siljitardi.
- **Tuzatish:** maydon `BlindItemResponse` da **e'lon qilinmagan**;
  repozitoriy uni ikkala navbat uchun ham hisoblaydi (bitta
  `_CLAIM_TEMPLATE`), serializer esa ko'chirmaydi.
  `test_the_blind_item_declares_none_of_the_eight_fields` farqni
  **ikki tomonlama** qulflaydi (nazorat: u `ReviewItemResponse` da BOR).
- **Commit:** `1fcd96f`

### 3. `[Rule 2 - Correctness]` Ko'r navbat `ORDER BY ra.id`, ustuvorlik EMAS

- **Muammo:** `claim_next()` ni `queue_kind='blind_audit'` bilan qayta
  ishlatish eng qisqa yo'l edi va u `_PRIORITY_ORDER` ni olib kelardi.
  Namuna tortilgandan keyin **kimni** ko'rish qat'iy; **qaysi tartibda**
  ko'rish esa nazoratchi ulgurmaganda ahamiyatli bo'ladi: javobsiz qolgan
  quyruq hisobotga «javobsiz» bo'lib kiradi. Billing ta'siri bo'yicha
  saralangan quyruq **tizimli ravishda sotuvchisiz** rastalardan iborat
  bo'lardi — ya'ni javob berilgan qism namunaning xolis qismi bo'lmay
  qolardi (2-dushman, faqat tortishda emas, JAVOB BERISHDA).
- **Tuzatish:** `_CLAIM_TEMPLATE` (yagona `SELECT`, `{order_by}` o'rni) +
  `_BLIND_ORDER` (`ORDER BY ra.id`). `:midpoint` ko'r so'rovda
  **e'lon qilinmagan**. `test_the_blind_queue_has_no_priority` ikki
  tartibni ATAYIN zid qo'yib o'lchaydi.
- **Commit:** `1fcd96f`

### 4. `[Rule 3 - Blocking]` Bozorlar ro'yxati `active_market_ids()` dan

- **Muammo:** Reja `audit_draw_due_markets()` ni ko'rsatadi. Funksiya kunni
  `now()` dan oladi va uni **argument qilib bo'lmaydi**, bu job esa
  `business_date` ni argument sifatida oladi (`retention_daily(today=...)`
  qoidasi). Ikki yo'l yozish (bugun → funksiya, boshqa kun → so'rov)
  **mahsulot yo'lini testsiz** qoldirardi.
- **Ikkinchi sabab kuchliroq:** `frame_size` `INSERT` bilan **bir
  tranzaksiyada** o'lchanishi kerak. Tashqarida o'lchangan son
  «o'lchadim → yozdim» oynasida eskirardi va `audit_rounds` muzlatilgan
  dalil bo'lish o'rniga **taxmin** yozardi.
- **Tuzatish:** `active_market_ids()` — `alert_sweep` va `retention_daily`
  ishlatadigan **yagona** RLS-chetlab o'tuvchi yuza, ya'ni yangi xavfsizlik
  yuzasi ochilmadi. Ikkala shart (`frame_size > 0`, «tur allaqachon
  bormi») tenant tranzaksiyasi **ichida** takrorlandi.
- **⚠ Oqibat:** `audit_draw_due_markets()` bugun **chaqiruvchisiz** qoldi —
  ochiq band sifatida pastda.
- **Commit:** `b97e989`

### 5. `[Qaror]` Namuna hajmi uchun IKKINCHI sozlama yozilmadi

Reja `BLIND_AUDIT_DAILY_SAMPLE` (30) ni so'raydi;
`review_blind_daily_budget` **allaqachon** aynan o'sha D-13 sonini
tashiydi. Ikki sozlama ajralganda ikkala yo'nalish ham jim nosozlik:
tortish > byudjet → namunaning bir qismi hech qachon javob olmaydi va
hisobotga «javobsiz» bo'lib kiradi; tortish < byudjet → «bugun bajarildi»
aslida «bugun kam tortildi» degani bo'lardi. Sabab `settings.py` da
yozilgan; `worker.py::_queue_tick_policy()` sonni bitta manbadan oladi.

### 6. `[Rule 1 - Bug]` `float8` kvotasi — reja bergan sabab YOLG'ON chiqdi

- **Boshlang'ich da'vo:** «`ceil(0.7 * 20)` IEEE754 da 15 beradi».
  **O'lchandi va RAD ETILDI:** 0,70 nisbatida `n = 1..200` oralig'ida
  `float` bilan `Decimal` **birorta joyda farq qilmaydi**.
- **Da'vo toraytirildi va shu bilan kuchaydi:** nisbat **sozlanadi**
  (`review_blind_eval_ratio` (0, 1] ni qabul qiladi) va farq boshqa
  qiymatlarda chiqadi — o'lchangan 27 ajralishdan ikkitasi:
  `ceil(0.28 x 25)` → 8 va 7; `ceil(0.55 x 100)` → 56 va 55.
- **Tuzatish:** nisbat MATN sifatida keladi va `::text::numeric` bilan
  yechiladi (`float8` PostgreSQL tomonida umuman paydo bo'lmaydi);
  `eval_quota()` `Decimal(str(...))` dan yuradi. **IKKI qatlam bilan
  o'lchandi:** `test_eval_quota_uses_decimal_arithmetic` (Python jufti,
  rad etilgan arifmetikaning O'ZI ishlatilib farqi isbotlanadi) va
  `test_the_sql_quota_matches_the_decimal_one` (**mahsulot yo'li** —
  `float8` bo'lganda baza 8 yozardi).
- **Bu 05-03 sabotaj S2 ning aynan sinfi:** test o'z farazini tasdiqlayotgan
  edi.
- **Commit:** `b97e989`

### 7. `[Rule 1 - Bug]` Statik darvoza YOLG'ON-QIZIL berdi (`hexdigest`)

- **Topildi:** Task 1, birinchi ijroda
- **Muammo:** `digest(` tokenini sodda `in` bilan qidirish
  `hashlib.sha256(...).hexdigest()` yozilgan HAR QANDAY faylni
  qizartirardi — ya'ni darvoza o'zini o'zi qizartirar va yagona
  «tuzatish» yo'li uni **bo'shatish** bo'lardi.
- **Tuzatish:** chegara identifikator chegarasiga qo'yildi
  (`(?<![a-z_])digest\s*\(`). **Bu bo'shatish emas, to'g'rilash:**
  taqiqlangan narsa — `pgcrypto` ning `digest()` funksiyasi, `hexdigest`
  esa `hashlib` ning metodi. `test_the_boundary_rejects_the_real_call`
  **ikkala yo'nalishni** ham qulflaydi.
- **Commit:** `b97e989`

### 8. `[Rule 3 - Blocking]` `grow_frame()` ikkinchi chaqiruvda yiqilardi

`version` ni `0` dan boshlash doiraning **muzlashi** testida (fixture ikki
marta chaqiriladi) `uq_camera_zones_market_id_camera_id_stall_id_version`
ni buzardi. `version` endi mavjud sondan boshlanadi; sabab kodda.

### 9. `[Qaror]` `daily_queue_tick` — ikki qadam BITTA vazifada

Reja «bitta `daily_queue_tick` ichida ketma-ket» deydi va bu bajarildi,
lekin sabab **rejadagidan kengroq** chiqdi: chaqiruv tartibini kod
majburlaydi, **cadence ni esa bitta vazifa**. Ikki alohida cron yozilsa
noaniq navbat kun bo'yi qurilib, kun oxiriga borib barcha `uncertain`
hodisalar allaqachon navbatda bo'lardi va ko'r audit ularni
`ON CONFLICT DO NOTHING` bilan **jimgina** yo'qotardi — ya'ni 2-dushman
cron JADVALI orqali qaytadan ochilardi. Sabab `QUEUE_TICK_CRON`
docstringida.

### 10. `[Qaror]` Marshrut nomlari `/review/blind/...`, `?blind=true` EMAS

Bitta marshrutni bayroq bilan ikki xulqqa bo'lish bitta serializer degani
bo'lardi va «maydon yo'q» kafolati **shartli** bo'lib qolardi. Ikkinchi
sabab frontendda: G-12 darvozasi **fayl to'plamini** skanerlaydi
(`components/blind-audit/**`) va u faqat ko'r audit alohida marshrut
bo'lgandagina ma'noga ega (UI-SPEC §4.3).

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| Yangi to'plam | `pytest tests/integration/test_blind_audit.py` | ✅ **33 passed** |
| `core-api` to'liq to'plami | `pytest` | ✅ **2134 passed, 5 deselected** (853 s), exit 0 |
| `core-api` tenancy | `pytest tests/tenancy` | ✅ **536 passed** (bazaviy 524 + 12 = 2 marshrut x 6) |
| `core-api` lint/tiplar | `ruff check . && ruff format --check . && mypy .` | ✅ toza (**269** fayl) |
| `npm run gate` | to'liq zanjir | ✅ **exit 0** |
| `vitest run` | frontend | ✅ **494** — o'zgarmadi (bu reja frontendga tegmadi) |
| `npm run i18n:check` | | ✅ **879 x 3** — o'zgarmadi |
| `node --test` | frontend skript darvozalari | ✅ **144** — o'zgarmadi |
| `cv-tests` | gate ichida | ✅ **93** — bu reja `cv-service` ga tegmadi |
| Skanerlangan marshrutlar | `test_no_redraw_endpoint` | ✅ ilova jadvalidan **92** endpoint yurildi (chegara >= 40) |
| Skanerlangan `GET` javoblari | `test_no_get_route_returns_the_reveal` | ✅ **34** (chegara >= 20) |
| `git diff --name-only` da `security/rbac.py` / `frontend/**` | | ✅ **YO'Q** (M-8) |

⚠ **BAZAVIY SON O'LCHOV BIRLIGI BILAN SOLISHTIRILMAYDI:** 05-10 «**2081**
yig'ildi» deb yozgan (collected), bu yerdagi **2134** esa `passed`. Ikkala
sonni ayirib «+53 test» deb yozish ikki xil o'lchovni tenglashtirardi.
O'LCHANGAN va SOLISHTIRILADIGAN yagona farq — `tests/tenancy`: **524 → 536**
(ikkalasi ham `passed`), va u aynan ikki yangi marshrutning matritsadagi
oltitadan qatoriga to'g'ri keladi. Frontend to'plamlari **alohida** ham
yuritildi va ular bazaviy sonlarda qoldi.

## Known Stubs

**Yo'q** — soxta ma'lumot manbai ham, placeholder matn ham yaratilmadi.
Ikki band ATAYIN «hozircha chaqiruvchisiz» va ular stub EMAS:

| Nima | Nega stub emas |
|---|---|
| `audit_draw_due_markets()` (05-05) chaqiruvchisiz qoldi | Funksiya to'liq ishlaydi va `test_due_markets_functions_expose_only_identifiers` uni o'lchaydi. Deviatsiya #4 nega bu jobda ishlatilmasligini o'lchov bilan yozadi; 05-12 ning kun yopilishi uchun u hamon to'g'ri shakl |
| `eval_quota()` mahsulot yo'lida chaqirilmaydi | Kvota SQL da hisoblanadi; funksiya chaqiruvchiga (jurnal, hisobot, test) o'sha sonni **ikkinchi marta yozmasdan** beradi va ikki qatlamli o'lchovning Python yarmi |

⚠ **D-16 (takroriy band) — stub EMAS, O'LCHANGAN ZIDDIYAT.** Mexanizm
qurilmadi va uning O'RNIGA hech nima qo'yilmadi: sozlama ham, «keyinroq
to'ldiriladi» maydoni ham yo'q. Ziddiyatning o'zi
`test_a_repeat_band_is_structurally_impossible_today` bilan bajariladigan
o'lchov bo'lib turadi.

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-49 (namunani qayta tortish) | mitigate | Urug' **hosila** va SQL da; `FIRST_ROUND_NO` konstanta; `NOT EXISTS` + `UNIQUE (market_id, business_date, round_no)`; `test_no_redraw_endpoint` **ikki mustaqil predikat** (handler manbasi + `app/api/**` import grafi) |
| T-05-50 (ko'r payloadda AI javobi) | mitigate | Sakkizala maydon **e'lon qilinmagan**; rekursiv skan **va** xom matnda verdikt so'zini qidirish; oshkor javob BOSHQA nom to'plamida va u birorta `GET` da yo'q (OpenAPI skani) |
| T-05-51 (yozilgan javobni tahrirlash) | mitigate | `409 blind_answer_locked`; `UNIQUE (review_assignment_id)`; shartsiz `BEFORE UPDATE OR DELETE` (sabotaj C bilan o'lchandi); URL'da identifikator yo'q |
| T-05-52 (doiraning qisqarishi) | mitigate | `frame_size`/`frame_predicate_hash`/`drawn_at` **bir tranzaksiyada** yoziladi; muzlash **xulq bilan** o'lchandi (tortishdan keyin hodisa qo'shiladi va son o'zgarmaydi); xesh SHART MATNIDAN hosila |
| T-05-53 (nazoratchining ichki mosligi) | **ochiq** | ⚠ D-16 bugungi sxemada ifodalab bo'lmaydi — deviatsiya #1. Payload tomoni yopiq (tortish belgisi yetib bormaydi), MEXANIZM esa qurilmadi |
| T-05-54 (`SECURITY DEFINER` orqali oldindan ko'rish) | mitigate | `audit_draw_due_markets()` bu yo'lda umuman chaqirilmaydi; namuna tenant konteksti ostida, RLS ichida tortiladi |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authorization-gap | `services/core-api/app/api/v1/snapshots.py` | ⚠⚠ **05-10 dan MEROS va u ko'r auditda ham kuchda:** `GET /snapshots/{id}/image` `CAMERA_VIEW` talab qiladi (`snapshots.py:408`), `ROLE_PERMISSIONS[INSPECTOR]` esa aynan `{OCCUPANCY_REVIEW}` (`rbac.py:217`). Sof `inspector` ko'r audit bandini **oladi**, dalil kadrini esa **403** bilan ko'ra olmaydi — UI-SPEC §7.4 esa rasmni QARORNING DARVOZASI qiladi |

**Nega bu rejada ham tuzatilmadi (ongli qaror, Rule 4):** `snapshots.py`
ham, `rbac.py` ham bu rejaning fayl ro'yxatida **yo'q**; UI-SPEC **M-8**
bu fazada RBAC tegilmasligini o'lchov bilan qo'yadi.

**Eng tor tuzatish (05-13 uchun yozib qo'yiladi):** dalil-kadr marshrutini
«`CAMERA_VIEW` **yoki** `OCCUPANCY_REVIEW`» ga o'tkazish — bu nazoratchining
butun kamera yuzasini ochmaydi. Uning narxi ham aniq:
`require_permission()` ning **yagona** `required_permission` tegi
ko'plikka aylanadi va `tests/tenancy/test_personal_data_coverage.py:462`
aynan o'sha tegdan `CAMERA_VIEW` ni talab qiladi. Ya'ni ikki fayl
o'zgaradi, semantika esa **qayta loyihalanmaydi** (teg ro'yxatga aylanadi,
tekshiruv esa «kamida bittasi» bo'ladi).

## Keyingi rejalar uchun ochiq bandlar

1. **⚠⚠ `05-13` uchun — yuqoridagi `threat_flag`.** Sof `inspector` dalil
   kadrini ko'ra olmaydi; eng tor tuzatish va uning narxi yozib qo'yildi.
2. **⚠⚠ `05-14`/`05-15` uchun — D-16.** Takroriy band bugungi sxemada
   IMKONSIZ (deviatsiya #1). Aniqlik hisoboti **nazoratchining ichki
   mosligini e'lon qila olmaydi** va uni «100%» deb ko'rsatish
   **taqiqlanadi** — o'lchanmagan raqam ko'rilgan zahoti o'lchangan deb
   o'qilardi (05-01 T-05-04 ning aynan qoidasi).
3. **`05-14` uchun:** aniqlik FAQAT `purpose = 'eval'` qatorlardan
   hisoblanadi (`ck_review_assignments_eval_needs_blind_audit` uni
   sxemada ham qo'riqlaydi). Kvota `eval_quota()` bilan **qayta
   hisoblanadi** — hisobot o'z sonini yozmasin.
4. **`05-14` uchun:** javobsiz qolgan ko'r audit bandlari namunadan
   CHIQMAYDI va hisobotda **«javobsiz»** deb sanalishi shart (C.8,
   4-dushman). `audit_rounds.frame_size` va tortilgan bandlar soni
   ikkalasi ham bazada.
5. **`05-12` uchun:** `audit_draw_due_markets()` hamon mavjud va
   o'lchangan, lekin **chaqiruvchisiz**. Kun yopilishi uchun u to'g'ri
   shakl; agar u ham `business_date` argumentini talab qilsa,
   `active_market_ids()` naqshi bu yerda tayyor.
6. **`05-13` uchun:** ko'r payload — `BlindItemResponse` (o'n maydon);
   `has_active_vendor` **YO'Q**, ya'ni ekran «sotuvchi biriktirilgan»
   qatorini ko'r sessiyada CHIZMASLIGI kerak. Oshkor ma'lumot FAQAT
   `POST` javobidan (`useMutation.data`).
7. **`05-15` uchun:** `MINIMUM_MATRIX_ROUTES` endi **57**;
   `INSPECTOR_ROUTES` da beshta marshrut.
8. **Operatsion:** tik **19:30** da ishlaydi, ya'ni nazoratchi kunning
   navbatini **ertasi kuni** ko'radi. Bu 05-10 ning byudjet qarori bilan
   mos, lekin `05-HUMAN-UAT` da ochiq aytilishi kerak.

## Self-Check: PASSED

- E'lon qilingan **2 yaratilgan + 7 o'zgartirilgan** fayl — hammasi diskda
  (`git diff --name-only b97e989~1..HEAD` → **9 fayl**);
- `b97e989`, `1fcd96f`, `ae54a38` — **uchala commit ham `git log` da**;
- Sabotajlardan keyin to'plamlar qayta yugurtirildi va `git status` toza —
  har biri `cp` bilan snapshotdan tiklandi, `git checkout --`
  **ishlatilmadi**;
- Sabotaj C′ ning artefakti (compose bazasidagi o'chirilgan trigger)
  `pg_get_triggerdef()` dan olingan AYNAN o'sha ta'rif bilan qaytarildi.

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
