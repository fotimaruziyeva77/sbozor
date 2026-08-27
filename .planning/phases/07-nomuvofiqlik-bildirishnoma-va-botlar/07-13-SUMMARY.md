---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 13
subsystem: notification-jobs
tags: [digest, projection, ledger, overdue, quiet-hours, idempotency, heartbeat, d-32]
requires:
  - "outbox_repo.enqueue() — ijarali navbat, D-18 siyosat darvozasi (07-06)"
  - "notification_meta.NOTIFICATION_META / outbox_payload() — allowlist (07-06)"
  - "reconciliation_repo.list_cases() + jobs/reconciliation.py (07-07)"
  - "billing_repo.pending_projection() / vendor_outstanding() / vendor_charge_allocation()"
  - "headline_repo.revenue_today_soum() — bozor x kun belgili yig'indi"
  - "OccupancyRepository.day_summary() — bandlik bo'laklari"
  - "jobs/retention.py::active_market_ids — YAGONA RLS-chetlab o'tuvchi yuza"
provides:
  - "app/repositories/digest_repo.py — ledger_day / occupancy_percent / top_debtors / overdue_vendors"
  - "app/jobs/notifications.py::digest_morning / digest_evening / overdue_reminder"
  - "DIGEST_COMPONENT = notify_digest, OVERDUE_COMPONENT = notify_overdue"
  - "DigestResult / ReminderResult"
  - "notification_meta.DEFAULT_OVERDUE_DAYS — endi SXEMADAN hosila (D-32 yopildi)"
affects:
  - "07-14 (cron reyestri) — uchala job qobiqsiz, EXPECTED_COMPONENTS ga IKKI nom qo'shiladi"
  - "07-09 (outbox tik) — matn `payload` dan quriladi; kalitlar shu rejada qulflandi"
  - "07-15 (frontend) — G-35 ning matn yarmi va TOP-10 havolasi"
tech-stack:
  added: []
  patterns:
    - "ikki manba, ikki ma'no — farq NUQSON emas, DIZAYN va u payloadda NOMLANADI"
    - "modulning ommaviy yuzasi aliaslangan importlar bilan yopiladi (headline_repo naqshi)"
    - "yopiq lug'at ustidagi TO'PLAM TENGLIGI — ikkinchisining YO'QLIGI ham o'lchanadi (G-35)"
    - "kod standarti sxemaning `server_default` idan HOSILA; literal AST bilan taqiqlanadi"
    - "bir qoidaning ikki ifodasi (SQL juftlari) TESTDA solishtiriladi, taxmin qilinmaydi"
    - "sabotajni KO'RINADIGAN qiladigan seed — kun SESHANBA tanlanadi (D ochiq, D-1 yopiq)"
key-files:
  created:
    - services/core-api/app/repositories/digest_repo.py
    - services/core-api/app/jobs/notifications.py
    - tests/integration/test_notifications.py
  modified:
    - services/core-api/app/jobs/notification_meta.py
decisions:
  - "collected_soum headline_repo.revenue_today_soum() dan CHAQIRILADI — bozor x kun ifodasi ikkinchi marta yozilmadi"
  - "LedgerDay ga paid_stall_count qo'shildi: kechqurun `charged` BO'SH va LEFT JOIN orqali hisoblangan sanoq mangu nol chiqardi"
  - "to'rtinchi komponent `notify_overdue` — tadqiqotning uch komponentli ro'yxatidan CHETLANISH (D-17 ni kuchliroq o'qish)"
  - "DEFAULT_OVERDUE_DAYS yo'nalishi: reyestr <- sxema (leaf). Teskarisi outbox_repo ni reconciliation_repo ga bog'lab import halqasi xavfini ochardi"
  - "test 1 ning 2-fazasi billing_close O'RNIGA to'g'ridan-to'g'ri seed — o'lchanayotgan da'vo `digest_morning` ning MANBASI, hisobni kim yozgani emas"
  - "G-35 ning matn yarmi bu rejada O'LCHANMADI (07-09 ning fayli yo'q); shakl `payload` qatlamida bajarildi"
metrics:
  duration: ~135 min
  completed: 2026-08-12
  tasks: 3
  files: 4
---

# Phase 7 Plan 13: Har rol o'z xabarini o'z vaqtida oladi — Summary

Direktorning kechki xabari **proyeksiyadan**, ertalabkisi **yozilgan
hisobdan** o'qiydi va ularning sonlari **bir xil emas** — bu farq endi
`payload` kalitlarida **nomlangan** va `==` bilan o'lchangan; BOT-03
eslatmasi esa `recon.open` bilan **aynan bir knobdan** yuradi va quiet
hours ga **bo'ysunadi**, kvitansiyadan farqli.

## Nima qurildi

**Task 1 — `digest_repo.py` (`509fe80`).** To'rt ommaviy funksiya va uch
natija tipi; `headline_repo.py` ning aliaslangan-import uslubi
qo'llanildi, ya'ni `dir()` dagi ommaviy funksiyalar **aynan to'rtta**.
Har bir son mavjud mahsulot funksiyasidan **chaqirib** olinadi:
`collected_soum` -> `revenue_today_soum()`, bandlik ->
`OccupancyRepository.day_summary()`, qarz -> `vendor_outstanding()`,
kechikish -> `vendor_charge_allocation()`. Yangi SQL faqat bitta:
`daily_charges` x `payments` ning **rasta kesimi**.

**Task 2 — `app/jobs/notifications.py` (`9fa4d80`).** Uch job,
`alerting.py`/`reconciliation.py` ning aynan shakli: `active_market_ids()`
**import qilinadi**, har bozor uchun `_tenant_session` + alohida
tranzaksiya, xato `_swallow()` bilan yutiladi, oxirida yurak urishi.
Uchalasi ham `outbox_repo.enqueue()` ga **niyat** yozadi. Cron
registratsiyasi **atayin yo'q** — `worker.py` 07-14 niki va u
**tegilmadi**.

**Task 3 — `tests/integration/test_notifications.py` (`81049c7`).**
18 test. Ikki manbaning tengsizligi, G-35 ning to'plam tengligi
(payload qatlamida), D-19 ning bozor kesimi, Pattern 5, D-18 ning
teskarisi (ikki tomonlama), idempotentlik, yurak urishi, nosozlikka
chidamlilik va D-32 ning ikki darvozasi.

**`0d3b414`** — orkestrator ruxsat bergan D-32 tuzatishi (pastda).

## O'lchangan dalillar

### ⛔ Sabotaj B — MANBANING ALMASHTIRILISHI (D-15 ning o'zi)

`digest_evening` ning `expected_soum` i `market.pending_amount_soum`
o'rniga `ledger.charged_soum` dan olindi — ya'ni kechki xabar
**yozilgan hisobdan** o'qiy boshladi.

| Darvoza | Natija |
|---|---|
| `test_evening_reads_projection_and_morning_reads_ledger` | **QIZIL** — `assert 0 == 80000` |
| Qolgan **17** test | **yashil** |

⛔ Ikkinchi qator darvozaning **aniqligini** isbotlaydi: sabotaj ular
uchun **ko'rinmas**, ya'ni D-15 ni qamrab turadigan yagona test —
birinchisi. `0` soni mexanik sabab bilan chiqdi: kechqurun
`daily_charges` da o'sha kun **umuman yo'q** — bu D-15 ning butun
mazmuni.

### ⛔ Sabotaj A — reja talab qilgan (`as_of = D − 1`) va uning IKKI natijasi

`digest_evening(as_of=day - 1)`.

| Da'vo | Natija | Sabab |
|---|---|---|
| **(a)** `expected_soum == pending_projection(as_of=D)` | **QIZIL** — `assert 0 == 80000` | `D − 1` — **dushanba** va A bozori o'sha kuni **yopiq** (`A_OPEN_WEEKDAYS` da ISO 1 yo'q), ya'ni proyeksiya `0` qaytaradi |
| **(c)** `charged_soum != expected_soum` | ⚠ **YASHIL QOLDI** | `22 000 != 0` — farq **hamon bor**, faqat sababi boshqa |

⚠ **Reja aynan (c) ning qizarishini talab qilgan va u qizarmadi — bu
TOPILMA sifatida qayd etilyapti, yashirilmayapti.** (c) ikki sonning
**tengligini** rad etadi, sabotaj esa kechki sonni **nolga** tushiradi,
ya'ni farq saqlanadi. D-15 ning haqiqiy da'vosi — «kechki son
proyeksiyaning **o'zi**» — (a) bandida yashaydi va u ikkala sabotajda ham
**qizardi**.

⛔ **Rejaning yo'riqnomasi bo'yicha tuzatish TESTDA emas, HOLATDA
bajarildi** (05-15 ning S-D darsi): kun endi tasodifiy «kecha» emas,
`_recent_open_day()` **eng yaqin o'tmishdagi seshanbani** qaytaradi.
Ixtiyoriy kun tanlansa `D` va `D − 1` **ikkalasi ham ochiq** bo'lardi,
ikkala proyeksiya **aynan teng** chiqardi va sabotaj A **hech nimani**
qizartirmasdi — ya'ni u sistemaga yetib borib ham ko'rinmas bo'lardi.

### Reja talab qilgan mexanik da'volar

| Da'vo | Natija |
|---|---|
| `dir(digest_repo)` ommaviy **funksiyalari** | `['ledger_day', 'occupancy_percent', 'overdue_vendors', 'top_debtors']` ✓ |
| `dir(digest_repo)` ommaviy **nomlari** (tiplar bilan) | `+ ['LedgerDay', 'OverdueVendor', 'TopDebtors']` — begona import **yo'q** |
| `TopDebtors` maydonlari | `{count, outstanding_soum}` — `vendor_id`/`vendor_name`/`phone` **YO'Q** ✓ |
| `OverdueVendor` maydonlari | `{vendor_id, outstanding_soum, oldest_service_date}` — ism **yo'q** ✓ |
| `occupancy_percent` rastasiz kunda | **`None`** (`0` emas) — test bilan ✓ |
| `ledger_day().collected_soum == revenue_today_soum()` | ✓ (bir seedda ikkala yo'l ham chaqirildi) |
| `grep -c vendor_outstanding` `digest_repo.py` | **9** (talab: ≥ 1) |
| `grep -nE "float(\|Decimal\|round(\|balance"` `digest_repo.py` | **0** |
| `(DIGEST_COMPONENT, OVERDUE_COMPONENT)` | `('notify_digest', 'notify_overdue')` ✓ |
| `grep -cE "AlertSender\|send_message\|api.telegram.org"` `notifications.py` | **0** |
| `grep -c pending_projection` `notifications.py` | **7**; `resolve_stall_day_money` -> **0** |
| `grep -c "business_today()"` `notifications.py` | **0** |
| `grep -nE "float(\|Decimal\|round(\|balance"` `notifications.py` | **0** |
| `NOTIFICATION_META["overdue_reminder"].never_suppressed` | **`False`** (test bilan) |
| Takroriy `digest_morning` -> `notification_outbox` | **1** qator; `skipped_existing >= 1` |
| Takroriy `overdue_reminder` (bir sotuvchi, bir kun) | **1** qator |
| Ikki bozorli nosozlik seedi | `len(errors) == 1`, `markets == 2`, sog'lom bozor **eslatma oldi** |
| `system_heartbeats` | `notify_digest` va `notify_overdue` — `last_seen_at NOT NULL`, `detail` **faqat butun sonlar** |
| `digest_repo.py` uzunligi | **488** satr (talab: ≥ 160) |
| `notifications.py` uzunligi | **770** satr (talab: ≥ 240) |

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/integration/test_notifications.py` | **18 test yashil** (reja ≥ 8 so'ragan) |
| `test_notifications` + `test_outbox_repo` + `test_reconciliation_repo` + `test_alerting` | **82 test yashil** — qo'shni rejalarning darvozalari buzilmadi |
| `pytest tests/integration -m "not sim and not slow"` | **964 yashil, 29 skip, 0 yiqilish — `EXIT=0`** |
| `pytest tests/unit tests/tenancy` | **`EXIT=0`**, birorta yiqilish yo'q (07-04 ning G7-2/G7-7/G7-8 lari o'z joyida) |
| `ruff check .` + `ruff format --check .` + `mypy .` | **toza** (327 fayl) |

### Ikki manbaning tengsizligi — o'lchangan sonlar

| Payt | Manba | Son |
|---|---|---|
| Kechqurun (`as_of = D`) | `pending_projection(D).market.pending_amount_soum` | **80 000** |
| Ertalab (`business_date = D`) | `sum(daily_charges)` | **22 000** |

⛔ Ikkalasi ham **to'g'ri** va ular **bir xil bo'lmasligi shart**.

## Rejadan chetlanishlar

### Orkestrator ATAYIN ruxsat bergan chetlanish

**1. [Ruxsat etilgan] `DEFAULT_OVERDUE_DAYS` — D-32 nusxasi yopildi**

- **Topildi:** merge qilingan `main` da qiymat **ikki marta** e'lon
  qilingan edi: `notification_meta.py:248` -> `Final[int] = 3`
  (**literal**), `jobs/reconciliation.py:143` ->
  `_schema_default_overdue_days()` (**sxemadan hosila**). Ikkalasi ham
  `__all__` da.
- **Nega muhim:** sxemaning `server_default` i o'zgargan kuni literal
  **jimgina eskirardi** — eslatma bir kunda, case boshqa kunda ishlab,
  D-19 ning **bir knobi ikkiga bo'linardi**.
- **Yechim:** `notification_meta.py` ham **sxemadan** o'qiydi
  (`_schema_default_overdue_days()`), ya'ni **manba bitta** —
  `MarketNotificationSettings.overdue_days.server_default`. Ikki e'lon
  endi **ajrala olmaydi**.
- **⛔ Yo'nalish bo'yicha ONGLI qaror va u orkestratorning tavsiyasidan
  farq qiladi.** Tavsiya «biri ikkinchisidan **import** qilsin» edi;
  bu yerda **reyestr sxemani o'qiydi** va `reconciliation.py` (bu
  rejaning `files_modified` ida **YO'Q**) tegilmadi. Sabab o'lchanadigan:
  `outbox_repo` -> `notification_meta` zanjiri allaqachon mavjud, ya'ni
  `notification_meta` -> `app.jobs.reconciliation` importi
  `outbox_repo` ni `reconciliation_repo` ga **tranzitiv** bog'lardi.
  `reconciliation_repo` bir kun outboxga yozadigan bo'lsa (case
  ochildi -> xabar — bu fazaning **tabiiy keyingi qadami**) import
  **halqasi** yopilardi. Qo'shimcha narx: reyestr moduli `PIL`,
  `aiobotocore` va `storage` ni tranzitiv ravishda tortib kelardi va
  `tests/unit/test_outbox_policy.py` o'sha zanjirni import qilardi.
- **Darvoza IKKITA va ikkinchisi kuchliroq:**
  1. `test_default_overdue_days_has_exactly_one_source` — uchala qiymat
     (`notification_meta`, `reconciliation`, sxema literali) `==`;
  2. `test_default_overdue_days_is_never_a_bare_literal_again` — **AST**
     bilan: `DEFAULT_OVERDUE_DAYS` ning o'ng tomoni `ast.Call` bo'lishi
     shart. ⛔ Faqat qiymat tengligi **yetmasdi**: sxemaning standarti
     bugun `3`, ya'ni kimdir literalni **qayta yozib qo'ysa** birinchi
     test **yashil qolardi**. AST grep o'rniga ATAYIN — grep izohni
     koddan ajratmaydi (03-07 ning o'lchangan darsi va u bu rejada yana
     bir marta to'landi, pastga qarang).
- **⛔ Qolgan qadam (bu rejaning ruxsatidan TASHQARIDA):**
  `jobs/reconciliation.py` o'zining `_schema_default_overdue_days()`
  ini o'chirib, konstantani `notification_meta` dan **import qilishi**
  kerak — o'shanda **o'quvchi ham bitta** bo'ladi. Bugun manba bitta,
  o'quvchi ikkita va ularning ajralishi yuqoridagi ikki darvoza bilan
  qulflangan. **Bir satrlik o'zgarish.**
- **Commit:** `0d3b414`

### Rule 2 — rejada yo'q, lekin usiz son YOLG'ON bo'lardi

**2. [Rule 2] `LedgerDay.paid_stall_count` qo'shildi**

- **Topildi:** Task 2, kechki payloadning `unpaid_stall_count` kalitini
  to'ldirayotganda.
- **Nega muhim:** reja «to'lanmagan rasta sanog'i» deydi, lekin
  **kechqurun `daily_charges` da bugungi kun umuman yo'q** (D-15 ning
  o'zi), ya'ni hisobdan hosila qilingan har qanday sanoq **mangu nol**
  chiqardi. Ikkinchi variant — proyeksiyaning `pending_stall_count` ini
  o'sha kalitga qo'yish — **aktiv yolg'on** bo'lardi: 20:45 da
  «300 ta rasta to'lamadi» deb yozardi, holbuki 280 tasi allaqachon
  to'lagan.
- **Yechim:** `_LEDGER_DAY` ga **skalyar quyi so'rov** qo'shildi
  (`charged` CTE dan **mustaqil**, aks holda kechqurun u ham nol
  bo'lardi) va kechki sanoq
  `max(0, pending_stall_count - paid_stall_count)` bo'lib quriladi.
- **⚠ Ochiq narx KODDA yozilgan:** faqat **eski qarzini** to'lagan
  sotuvchining rastasi ham «yig'ilgan» tomonga tushadi — ya'ni son
  «kassir bu rastaga **bordimi**?» ni o'lchaydi. Aniqroq savol
  («hisob to'liq qoplandimi?») ertalabki dayjestda, `daily_charges`
  yozilgandan **keyin** javob oladi.
- **Commit:** `9fa4d80`

**3. [Rule 2] `collected_soum` `headline_repo` dan CHAQIRIB olindi**

- **Topildi:** Task 1. Reja «ifoda `payment_repo` dagi belgili yig'indi
  bilan **bir xil** bo'lishi shart» deydi — ya'ni **nusxa** ko'zda
  tutilgan.
- **Yechim:** nusxa umuman yozilmadi. `ledger_day()`
  `headline_repo.revenue_today_soum()` ni **chaqiradi**, ya'ni
  direktorning ertalabki xabari va bosh ekrandagi «bugungi tushum»
  **aynan bir ifodadan** chiqadi va ajrala **olmaydi**. Rasta kesimi
  (`GROUP BY p.stall_id`) esa boshqa savol va u bu modulda **bir marta**
  yozilgan — `headline_repo.py` ning modul docstringi bu farqni
  allaqachon nomlab qo'ygan.
- **Da'vo susaymadi, kuchaydi:** reja `==` tengligini so'ragan edi, kod
  esa tenglikni **strukturaviy** qildi; test (`test_ledger_day_collected_
  equals_the_signed_payment_sum`) baribir ikkala yo'lni ham chaqirib
  solishtiradi.
- **Commit:** `509fe80`

### Rule 1 — reja matni haqiqatdan farq qilgan joyda HAQIQAT ustun turdi

**4. [Rule 1] Test 1 ning 2-fazasi `billing_close(D)` O'RNIGA to'g'ridan-to'g'ri seed**

- **Topildi:** Task 3. Reja «(b) so'ng `billing_close(business_date=D)`
  chaqiriladi» deydi.
- **Nega bajarilmadi:** `billing_close(D)` o'tmishdagi kun uchun
  `stall_slot_occupancy` qatorlarini talab qiladi va ularni qurish
  `test_billing_close.py::PastDay` ning **butun mashinasini** (~200
  satr: kadr + zona + hodisa + `day_close` zanjiri) bu faylga
  ko'chirardi. Chaqirilganda ham u **0 hisob** yozardi va o'shanda (b)
  bandi `0 == 0` ni o'lchagan bo'lardi — ya'ni **bo'sh rost**.
- **Yechim:** hisob `add_daily_charge()` bilan, **tarifdan farqli**
  summa (`TARIFF_SOUM + 7 000`) bilan yoziladi. O'lchanayotgan da'vo —
  `digest_morning` **qaysi manbadan** o'qiydi; hisobni **kim** yozgani
  (job yoki seed) bu da'voga ta'sir qilmaydi va `billing_close` ning
  o'zi `test_billing_close.py` da 20+ test bilan allaqachon o'lchangan.
- **Nazorat bandi:** 1-fazada `daily_charges` da o'sha kun uchun
  **0 qator** ekani assert qilinadi, ya'ni «yozilgan hisob» holatini
  testning **o'zi** yaratgani ko'rinib turadi.
- **Commit:** `81049c7`

**5. [Rule 1] `docstring` dan taqiqlangan chaqiruv nomlari olib tashlandi**

- **Topildi:** Task 1 ning grep darvozasini o'lchayotganda:
  `grep -cE "float(|Decimal|round(|balance"` `digest_repo.py` -> **1**,
  holbuki reja **0** talab qiladi. Moslik **izohda** edi —
  `occupancy_percent()` ning docstringi taqiqni **tushuntirish** uchun
  chaqiruv nomlarini literal yozgan.
- **Nega muhim:** bu 03-07 ning o'lchangan darsi va 07-06 uni
  `alerts.py` da bir marta to'lagan: sodda grep darvozasi **izohni
  koddan ajratmaydi**, ya'ni taqiqni tushuntirish darvozani **o'z-o'ziga
  qarshi** qo'yadi.
- **Yechim:** matn tavsifiy shaklga («kasrli tip hamda yaxlitlash
  chaqiruvlari») qayta yozildi va sabab **o'sha docstringda ochiq
  yozildi**, ya'ni keyingi ijrochi nomlarni qaytarib yozmaydi. AYNI
  qaror D-32 darvozasida ham qo'llandi: u **AST** bilan yozildi, grep
  bilan emas.
- **Commit:** `509fe80`

**6. [Rule 1] Nosozlik tuzatishi `amount * 3` emas, `amount + 5 000`**

- **Topildi:** `test_one_broken_market_does_not_stop_the_others`
  birinchi yugurishda `errors == []` berdi.
- **Sabab:** uch baravar `decrease` sotuvchining **umumiy** qoldig'ini
  ham manfiy qilardi (`-30 000 + 15 000 = -15 000`), ya'ni u qarzdorlar
  ro'yxatiga **umuman kirmasdi** va nosozlik **tug'ilmasdi** — job
  «xatosiz» yakunlanardi.
- **Yechim:** tuzatish `TARIFF_SOUM + 5 000` (07-07 ning aynan qiymati):
  umumiy qoldiq **musbat** qoladi, o'sha KUNNING qoldig'i esa manfiy
  bo'ladi va `allocate_charge_credit()` uni `ValueError` bilan rad
  etadi. Sabab **kodda yozib qo'yildi**.
- **Commit:** `81049c7`

**7. [Rule 1] Qisman to'lov `quote_soum` orqali ifodalandi**

- **Topildi:** `ck_payments_override_is_paired` — `amount_soum` va
  `quote_soum` farq qilsa `override_reason` **majburiy**.
- **Yechim:** ikkalasi ham `TARIFF_SOUM // 3` qilib berildi. Qisman
  qoplanish **kotirovkaning kichikligidan** keladi va o'lchanayotgan
  da'vo («hisob to'liq qoplanmagan» -> `unpaid_stall_count == 1`)
  o'zgarmadi.
- **Commit:** `81049c7`

### Struktura bo'yicha ongli qarorlar

**A. To'rtinchi komponent `notify_overdue` — tadqiqotdan CHETLANISH.**
`07-RESEARCH.md` uchta komponentni sanaydi (`outbox_tick`,
`reconciliation_open`, `notify_digest`) va BOT-03 ning jobi o'sha
ro'yxatda **yo'q** edi. D-17 «yangi cron joblar kuzatiladi» deydi,
`deferred-items.md` ning 2-bandidagi dars esa aynan **ro'yxatga
olinmagan cronning jimgina o'lishi**. Kuzatilmagan eslatma jobi hech
qanday xato bermaydi — sotuvchilar shunchaki eslatma olmay qo'yadi va
buni ma'muriyat **oylar keyin** sezadi. ⛔ Reja bu chetlanishni
SUMMARY da qayd etishni **talab qilgan**.

**B. Ikkala dayjest ham BITTA yurak urishi qatorini yangilaydi — va
uning narxi OCHIQ.** Reja konstantalar sonini **aynan ikkita** qilib
belgilagan (akseptans mezoni `(DIGEST_COMPONENT, OVERDUE_COMPONENT)`
kortejini `==` bilan o'lchaydi), ya'ni uchinchi nom qo'shib bo'lmasdi.
Oqibat kodda yozilgan: **kechkisi ishlab, ertalabkisi o'lsa yurak
urishi hamon yangi ko'rinadi**. Egasi — **07-14**: reyestrni
kengaytirish qarori o'sha rejaniki. (`detail` faqat butun sonlardan
iborat bo'lishi `system_heartbeats` ning global jadval ekanidan
keladi va u test bilan qulflangan, ya'ni «morning/evening» satrini
`detail` ga yozib qutulish yo'li ham **yopilgan**.)

**C. `_MARKET_OVERDUE_DAYS` — NUSXA EMAS, JUFT va ajralish O'LCHANADI.**
`app/jobs/reconciliation.py` dagi jufti bilan **so'zma-so'z bir xil**
so'rov. Import o'rniga juft yozildi (`_tenant_session` da o'rnatilgan
qoida: ikki mustaqil jobni bir-biriga bog'lamaslik), lekin ajralish
**taxmin qilinmadi**: `test_overdue_reminder_shares_the_knob_with_case_
opening` ayni bozorda **ikkala mexanizmni ham** yuritadi va ular
**bir xil javob** berishini talab qiladi — teskari nazorat bilan
(`overdue_days = 10` bo'lgan bozorda **ikkalasi ham** yo'q). Standart
qiymat esa endi **haqiqatan bitta** (D-32 tuzatishi).

**D. `overdue_vendors()` taqqoslashi `<=`, `<` EMAS.** `_OVERDUE_CHARGES`
ning `c.service_date <= :cutoff` bandi bilan **aynan bir xil**. Farq
**faqat chegaradagi kunda** ko'rinadi, shuning uchun u alohida test
bilan qulflandi (`test_overdue_vendors_uses_the_same_cutoff_as_case_
opening`): `bugun − 3` kuni `overdue_days = 3` da **qamraladi**,
`overdue_days = 4` da **qamralmaydi**.

## Ochiq bandlar

**1. ⛔ G-35 ning MATN yarmi bu rejada O'LCHANMADI va bu MUHIT
bo'shlig'i, qaror emas.** Reja `test_evening_and_morning_texts_name_the_
difference` ni `app/jobs/outbox.py::_build_text` (07-09) ustida
yozishni buyuradi; o'sha fayl **07-09 ning `files_modified` ida** va
bu worktree'da **umuman yo'q** (`ls services/core-api/app/jobs/` — 10
fayl, `outbox.py` yo'q). Noma'lum shaxsiy API ga qarshi spekulyativ
test yozish **atayin rad etildi**: imzo taxmin qilinganda u merge'dan
keyin `TypeError` bilan yiqilardi va tuzatish 07-09 ning ishini
buzardi. O'rniga G-35 ning **shakli** (yopiq lug'at ustidagi **to'plam
tengligi**, ya'ni ikkinchisining **yo'qligi** ham) bu reja egallik
qiladigan qatlamda — `payload` kontraktida — bajarildi:
`test_the_two_digests_name_their_difference_in_the_payload`.
**Egasi:** 07-09 (server matni, uchala locale) va 07-15 (frontend
jufti, `reconciliation-copy.test.mjs`).

**2. `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` HAMON
VAQTINCHALIK NUSXA va u bu rejada ham TEGILMADI.** 07-06 SUMMARY ning
1-ochiq bandi o'z kuchida: fixture ro'yxati `OUTBOX_PAYLOAD_KEYS` dan
**hosila** bo'lishi kerak, nusxa emas (D-32 ning aynan sinfi). Fayl bu
rejaning `files_modified` ida yo'q. ⚠ **Bu rejaga to'sqinlik
QILMADI:** testlar `seed_outbox_row()` ga umuman tayanmaydi —
kvitansiya qatori ham **mahsulotning `enqueue()` idan** yoziladi
(`notification_meta.outbox_payload()` orqali), ya'ni fixture'ning
eskirgan ro'yxati bu faylning yo'liga tushmaydi.

**3. `jobs/reconciliation.py` HAMON O'Z `_schema_default_overdue_days()`
INI SAQLAYDI.** Manba bitta (sxema), lekin **o'quvchi ikkita**.
Yuqoridagi 1-chetlanishga qarang: bir satrlik o'zgarish, egasi —
`reconciliation.py` ni ochadigan **keyingi reja** (ehtimol 07-14).

**4. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
`frontend/node_modules` YO'Q (gitignored). Bu band bu rejadan
**mustaqil** va u **dalil bilan** yopiladi:
`git diff --name-only 4aec616 HEAD | grep -c "^frontend/"` -> **0**,
ya'ni to'rtala fayl ham Python (`services/core-api/**` va `tests/**`).
Egasi: orkestrator (07-02/07-04/07-06/07-07 da ham aynan shu band edi).

**5. Izolyatsiyalangan compose loyihasida SeaweedFS bucket'i YO'Q edi —
va bu KOD NUQSONI EMAS, ISBOTLANDI.** To'liq integratsiya to'plamining
birinchi yugurishida to'rt test (`test_snapshot_api.py` ning uchtasi va
`test_phase6_criteria.py::test_sc2_...`) `StorageError: AccessDenied
(status=403)` bilan qizardi. `weed shell` bilan
`s3.bucket.create -name sbozor-snapshots` bajarilgach o'sha to'rt test
ham **yashil** bo'ldi va to'liq to'plam **`EXIT=0`** (964 yashil,
29 skip, **0 yiqilish**) berdi. 07-06 va 07-07 SUMMARY laridagi aynan
o'sha band — parallel worktree stekiga tegishli, mahsulotga emas. Bu
reja birorta ombor, kadr yoki `storage` fayliga **tegmagan**.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi qurmaydi; birorta bo'sh qiymat renderga
oqmaydi. `occupancy_percent()` ning `None` javobi **stub emas** — u
hujjatlashtirilgan va o'lchangan mahsulot holati («o'sha kunda birorta
rasta materializatsiya qilinmagan») va u `outbox_payload()` tomonidan
payloaddan **butunlay tashlanadi**, ya'ni matn quruvchisi «kalit
bormi?» degan bitta savol bilan ishlaydi. `DigestResult` ning nol
sonlari ham javob: `charges = 0` — «hisob hali yozilmagan» degan
**haqiqiy** holat va u yurak urishida ko'rinadi.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, auth yo'li, fayl kirishi yoki sxema
o'zgarishi qo'shilmadi (birorta migratsiya yo'q). Rejaning
`<threat_model>` idagi yettala mitigatsiya bajarildi:

| Threat ID | Qanday yopildi |
|---|---|
| T-07-76 | `top_debtors()` **son** qaytaradi; `dataclasses.fields()` to'plam tengligi + `payload` da ism ham, `vendor_id` ham **yo'q** (nazorat bandi: ism bazada BOR) |
| T-07-77 | `pending_projection()` **chaqiriladi**; tenglik `==` bilan; sabotaj B bilan o'lchandi; `resolve_stall_day_money` grepi -> 0 |
| T-07-78 | Farq `payload` kalitlarida **nomlangan** va to'plam tengligi bilan o'lchangan (matn yarmi 07-09 da) |
| T-07-79 | `dedupe_key` da **kun** -> sotuvchi kuniga 1 eslatma (test bilan); `overdue_days` bozor kesimida (3 vs 10) |
| T-07-80 | To'rtinchi komponent `notify_overdue`; ikkala yurak urishi ham test bilan qulflangan |
| T-07-81 | `_swallow()`; ikki bozorli seedda `errors == 1`, `markets == 2`, sog'lom bozor **eslatma oldi** |
| T-07-SC | Yangi paket **yo'q** — `pyproject.toml` va `uv.lock` **tegilmadi** |

## Self-Check: PASSED

Yaratilgan/o'zgartirilgan fayllar diskda mavjud:
- `services/core-api/app/repositories/digest_repo.py` ✓ (488 satr)
- `services/core-api/app/jobs/notifications.py` ✓ (770 satr)
- `tests/integration/test_notifications.py` ✓ (1123 satr, 18 test)
- `services/core-api/app/jobs/notification_meta.py` ✓ (o'zgartirildi)
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-13-SUMMARY.md` ✓

Commitlar: `509fe80` · `0d3b414` · `9fa4d80` · `81049c7` (baza `4aec616`).

`git diff --diff-filter=D --name-only 4aec616 HEAD` — **BO'SH**, ya'ni
birorta fayl o'chirilmadi. `git diff --name-only 4aec616 HEAD` — **aynan
to'rtta fayl**: uchtasi rejaning `files_modified` ida, to'rtinchisi
(`notification_meta.py`) — orkestrator **ochiq ruxsat bergan** D-32
tuzatishi.

⚠ `STATE.md`, `ROADMAP.md` va `app/worker.py` ATAYIN TEGILMADI:
birinchi ikkitasini worktree rejimida orkestrator markazlashgan holda
yangilaydi, `worker.py` esa 07-14 niki (parallel ijrochilar
to'qnashuvining oldi olindi).
