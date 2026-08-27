---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 06
subsystem: backend-nomuvofiqlik-va-bildirishnoma
tags: [WR-04, WR-06, WR-09, D-19, RECON-04, deferred-items-7a]
requires:
  - "app/jobs/reconciliation.py — reconciliation_open() va DEFAULT_OVERDUE_DAYS"
  - "app/jobs/notifications.py — overdue_reminder() (BOT-03)"
  - "app/repositories/reconciliation_repo.py — open_cases() SINF A/B"
  - "app/repositories/digest_repo.py — overdue_vendors()"
  - "app/security/ratelimit.py — BOT_RESOLVE_LIMIT"
provides:
  - "overdue_cutoff(business_date, overdue_days) — kechikish chegarasining YAGONA ta'rifi"
  - "CASE_LOOKBACK_DAYS = 30 — SINF A nomzodlar oynasi"
  - "open_cases(cutoff=...) / overdue_vendors(cutoff=...) — repo chegarani QO'LLAYDI, hisoblamaydi"
affects:
  - "app/worker.py — overdue_reminder_task endi business_today() - 1 beradi"
  - "tests/integration/test_notifications.py — knob testi qobiqlardan yuritadi"
  - "tests/integration/test_reconciliation_repo.py — open_cases chaqiruvlari cutoff oladi"
tech-stack:
  added: []
  patterns:
    - "Chegara JOB qatlamida hisoblanadi, repo qatlamiga tayyor qiymat bo'lib tushadi"
    - "Ikki mustaqil job bir qoidani ishlatsa — qoida import qilinadi, nusxa olinmaydi"
    - "O'lchanmagan xavfsizlik da'vosi kodda qolmaydi: bajariladi yoki kamaytiriladi"
key-files:
  created: []
  modified:
    - services/core-api/app/jobs/reconciliation.py
    - services/core-api/app/jobs/notifications.py
    - services/core-api/app/repositories/reconciliation_repo.py
    - services/core-api/app/repositories/digest_repo.py
    - services/core-api/app/repositories/binding_repo.py
    - services/core-api/app/worker.py
    - tests/integration/test_notifications.py
    - tests/integration/test_reconciliation_repo.py
decisions:
  - "overdue_cutoff() jobs/reconciliation.py da; notifications.py uni IMPORT qiladi — 07-fazadagi «import emas, juft» qarori aynan shu nuqtada yolg'on da'vo tug'dirgan edi"
  - "Chegara JOB da hisoblanadi: repo signaturalari overdue_days dan cutoff ga o'tdi, shunda ikkinchi ayirish ifodasi STRUKTURAVIY imkonsiz"
  - "floor business_date DAN sanaladi, cutoff dan EMAS — oyna mahsulot qarori, overdue_days esa bozor sozlamasi"
  - "WR-04 uchun A yo'li: da'vo kamaytirildi, sun'iy kechikish RAD ETILDI (narx real, foyda nazariy)"
metrics:
  duration: 135min
  tasks: 3
  files: 8
  completed: 2026-08-16
---

# Phase 8 Plan 06: 7-fazadan meros uch backend ogohlantirishini yopish Summary

7-fazadan meros qolgan uch ogohlantirish (WR-04, WR-06, WR-09) yopildi:
kechikish chegarasi endi **bitta funksiyada** ta'riflanadi va ikkala
mexanizm ham unga **bir xil kun** beradi; SINF A ning nomzodlari 30
kunlik oynaga qamaldi; `resolve()` ning o'lchanmagan tayming da'vosi
kamaytirildi.

## Nima qilindi

### Task 1 — WR-06: «bir knob» tengligi MAHSULOT yo'lida ham rost

**Nuqson:** `notifications.py` va `reconciliation.py` ikkalasi ham D-19
ni («AYNI knob, AYNI javob») e'lon qilardi, lekin qobiqlar boshqa kun
berardi:

```
reconciliation_open_task:  business_today() - 1   -> cutoff = T-1-N
overdue_reminder_task:     business_today()       -> cutoff = T-N
```

Ya'ni ikki chegara **har doim bir kunga farq qilardi** va uni
qo'riqlaydigan test ikkala jobga ham **qo'lda bir xil** `business_date`
uzatgani uchun buni ko'rmasdi.

**Tuzatish uch qatlamda:**

1. **Qobiqlar tenglashtirildi** — `overdue_reminder_task` endi
   `business_today() - timedelta(days=1)`. Sabab izohda literal: ikkala
   mexanizm ham **YOZILGAN** hisob ustida ishlaydi, hisob esa D+1 ning
   04:10 da tug'iladi (`BILLING_CLOSE_CRON`), ya'ni bugungi kun bilan
   ishlash chegarani hali **ma'lumoti yo'q** kunga qadardi.
2. **Chegaraning yagona ta'rifi** — `overdue_cutoff(business_date,
   overdue_days) -> date` `app/jobs/reconciliation.py` da; `notifications.py`
   uni import qilib chaqiradi.
3. **Ikkinchi ayirish ifodasi olib tashlandi** — `reconciliation_repo.
   _open_unpaid_cases()` va `digest_repo.overdue_vendors()` endi tayyor
   `cutoff` oladi va chegarani **hisoblamaydi, qo'llaydi**.

Test endi `worker.reconciliation_open_task` / `worker.overdue_reminder_task`
qobiqlarini `original_func` orqali yuritadi va `overdue_cutoff` ni **har
ikki modulda alohida** spionlab, ikkala chegara to'plamining tengligini
talab qiladi.

### Task 2 — WR-09: nomzodlar oynasi

`_OVERDUE_CHARGES` da faqat yuqori chegara (`<= :cutoff`) bor edi, ya'ni
har yugurishda **butun tarixning** to'lanmagan hisoblari nomzod bo'lardi
va ular uchun case **o'sha hisobning kuni** bilan ochilardi. Yagona
ro'yxat yuzasi esa kun kesimida (`?day=`, standart kun kecha) — bu
case'lar ekranda **hech qachon** ko'rinmasdi, `hit_rate()` ning `pending`
sanog'i esa ular bilan doimiy shishib, «hali O'LCHOV YO'Q» signalini
shovqinga aylantirardi.

`CASE_LOOKBACK_DAYS: Final[int] = 30` qo'shildi va so'rovga quyi chegara
kiritildi (`AND c.service_date >= :floor`). Konstanta docstringi
**qarzdorlik reestrini nomma-nom** ko'rsatadi (RECON-04, 08-07/08-10):
ma'lumot yo'qolmaydi, **yuzasi almashadi**.

⚠ `floor` `business_date` dan sanaladi, `cutoff` dan **emas**: oyna
yugurish kuniga bog'langan mahsulot qarori, `overdue_days` esa bozorning
sozlamasi. `cutoff` dan sanash chegarasini kengaytirgan bozorda oynani
ham jimgina siljitardi.

### Task 3 — WR-04: `resolve()` ning tayming da'vosi

**Tanlangan yo'l: (A) — da'voni KAMAYTIRISH.** Sabab: tsikldan keyingi
ish uch shoxda uch xil narxga ega va farq tsiklnikidan katta —

| shox | tsikldan keyingi ish |
|---|---|
| `NO_MATCH` | faqat `log.info` — I/O yo'q |
| `BOUND` | yangi tranzaksiya + `SELECT` + `UPDATE`/`INSERT` + `flush` |
| `MULTIPLE_MATCHES` | har mos bozor uchun tranzaksiya + `alert_events` upsert |

ya'ni «doimiy javob vaqti» da'vosi kodda **bajarilmasdi**. Endi docstring
himoyaning haqiqiy ikki qatlamini nomlaydi: **D-24** (odam Telegram'da
faqat O'Z kontaktini ulasha oladi — enumeratsiya strukturaviy imkonsiz)
va **rate-limit** (`BOT_RESOLVE_LIMIT = 5`). Tsikldagi `break` ning
yo'qligi **saqlandi** va uning izohi endi rost.

**(B) yo'li ongli rad etildi:** sun'iy doimiy kechikish botning javob
vaqtini har chaqiruvda oshirardi va test to'plamining yugurish vaqtiga
ham tushardi — narx real, foyda esa yuqoridagi ikki qatlam borligida
nazariy.

⚠ Taqiqlangan literal (`RESOLVE_MIN_LATENCY_SECONDS`) va eski da'vo
jumlasi faylda **izohda ham** qoldirilmadi — 03-07 da o'rnatilgan qoida:
shunda sodda grep darvozasi istisnosiz tirik qoladi.

## Sabotaj o'lchovlari (ikkalasi ham MAJBURIY edi)

### Sabotaj 1 — WR-06 (qobiq kuni)

`overdue_reminder_task` ni `business_today()` ga qaytardim:

```
E   AssertionError: MAHSULOT yo'lida ikki chegara AJRALDI:
    eslatma=[datetime.date(2026, 8, 6), datetime.date(2026, 8, 13)],
    case=[datetime.date(2026, 8, 5), datetime.date(2026, 8, 12)]
FAILED test_overdue_reminder_shares_the_knob_with_case_opening
```

Jurnal satrlari farqni mahsulot yo'lida ham ko'rsatdi:
`overdue_reminder_done business_date=2026-08-16` va
`reconciliation_open_done business_date=2026-08-15`. **Test qizardi**,
tuzatish tiklandi.

### Sabotaj 2 — WR-09 (`>=` -> `>`)

Quyi chegarani `>` ga o'zgartirdim:

```
E   AssertionError: chegaraviy kun (`business_date - 30`) qamralmadi:
    OpenCasesResult(anomaly_cases=0, unpaid_cases=0, skipped_existing=0)
FAILED test_the_lookback_boundary_day_still_opens_a_case
```

**Test qizardi** va aynan bittasi qizardi — qolgan 26 tasi yashil qoldi,
ya'ni o'lchov chegaraviy kunni **ajratib** ushlaydi. Holatni kengaytirish
kerak bo'lmadi (05-15 ning S-D darsi bu safar qo'llanmadi).

## Struktura bo'yicha ongli qarorlar

**A. `overdue_cutoff()` jobs qatlamida, repo'da emas.** Repo qatlami
uni chaqirsa `reconciliation_repo -> app.jobs.reconciliation` import
halqasi yopilardi (`jobs/reconciliation.py` allaqachon repo'ni import
qiladi). Chegarani job hisoblab, repo'ga **qiymat** bo'lib berish
halqani ham ochmaydi, ikkinchi ifodani ham imkonsiz qiladi.

**B. 07-fazadagi «import emas, juft» qarori QAYTA YOZILDI.**
`notifications.py` ning `_MARKET_OVERDUE_DAYS` docstringi
`app.jobs.reconciliation` dan import qilishni ochiq taqiqlagan edi.
Endi farq aniq ajratildi: **SO'ROV** (sozlama ustunini o'qish) hamon
juft, **CHEGARANING ARIFMETIKASI** esa import. Sabab docstringda:
qoida bitta bo'lsa, uning ta'rifi ham bitta bo'lishi shart.

**C. `open_cases()` ning musbat-chegara qo'riqchisi shaklini
o'zgartirdi.** `overdue_days < 1` o'rniga `cutoff >= business_date` —
matematik ravishda **ayni shart**. Xato matnida `overdue_days` so'zi
saqlandi (mavjud test `match="overdue_days"` bilan qidiradi va o'lchov
ma'nosi o'zgarmadi).

**D. `digest_repo.overdue_vendors()` dan `as_of` VA `overdue_days`
ikkalasi ham olib tashlandi.** `as_of` faqat chegara uchun ishlatilardi
(`_vendor_outstanding()` ga uzatilmasdi ham), ya'ni ikkala argument
bitta `cutoff` ga siqildi va yuza toraydi.

## Rejadan chetlanishlar

### Avtomatik tuzatilganlar

**1. [Rule 3 - Bloklovchi] Worktree'da `ops/seaweedfs/s3.json` va `.env` yo'q edi**

- **Qachon:** Task 1, birinchi test yugurishida
- **Nuqson:** Ikkalasi ham `.gitignore` da, ya'ni worktree'ga ko'chmagan.
  `docker compose` bind-mount manbasi topilmagani uchun `s3.json`
  o'rniga **katalog** yasadi; SeaweedFS S3 portini umuman ochmadi va
  `sbozor-storage-1` mangu `starting` holatida qoldi. Bu **umumiy
  konteyner** bo'lgani uchun asosiy stekdagi `storage` ham shu holatga
  tushdi.
- **Tuzatish:** bo'sh katalog olib tashlandi, ikkala fayl ham asosiy
  repodan (`E:/bozor`) worktree'ga nusxalandi, `storage` qayta
  yaratildi va `healthy` bo'ldi.
- **Fayllar:** `.env`, `ops/seaweedfs/s3.json` — ⚠ ikkalasi ham
  gitignored, ya'ni **commit qilinmadi**.

**2. [Rule 3 - Bloklovchi] `digest_repo.py` rejaning `files_modified` ida yo'q edi**

- **Qachon:** Task 1
- **Nuqson:** Reja «⛔ ikkinchi ayirish ifodasi kodda QOLMASIN» deydi,
  lekin ikkinchi ifoda aynan shu faylda (`overdue_vendors()`, `cutoff =
  as_of - _timedelta(days=overdue_days)`) edi.
- **Tuzatish:** fayl o'zgartirildi — usiz bandning o'zi bajarilmasdi.

**3. [Rule 1 - Nuqson] `test_notifications.py` da ishlatilmay qolgan import**

- **Qachon:** Task 1
- **Nuqson:** Knob testi qobiqlarga o'tgach `reconciliation_open` to'g'ridan-
  to'g'ri chaqirilmay qoldi; `ruff` uni ushladi.
- **Tuzatish:** import olib tashlandi.

## Ochiq qolgan bandlar

⚠ **`DEFAULT_OVERDUE_DAYS` ning IKKI o'quvchisi hamon bor.**
`notification_meta.py` ning docstringi keyingi qadamni ochiq yozgan:
`jobs/reconciliation.py` o'zining `_schema_default_overdue_days()` ini
o'chirib, qiymatni reyestrdan import qilishi kerak. Bu rejada **atayin
bajarilmadi**: manba bugun ham bitta (sxema), ajralish esa
`test_notifications.py` da ikki darvoza bilan (qiymat tengligi + AST
bo'yicha literal taqig'i) qulflangan. Yuzasi tor, tetigi yo'q.

## Tekshiruv natijalari

| O'lchov | Natija |
|---|---|
| `pytest tests/integration -q` | **EXIT 0**, birorta yiqilish yo'q |
| `pytest tests/integration/test_phase7_criteria.py -q` | **10 passed** — 7-fazaning beshala mezoni HAMON yashil |
| `pytest tests/integration/test_notifications.py -k overdue -q` | 8 passed |
| `pytest tests/integration/test_reconciliation_repo.py -q` | 27 passed |
| `pytest tests/integration/test_bot_internal_api.py -q` | 48 passed |
| `ruff check services/core-api tests` | All checks passed |
| `mypy services/core-api` | Success: no issues found in 106 source files |
| `grep -rn "def overdue_cutoff" services/core-api \| wc -l` | **1** |

## Qabul mezonlari

| Mezon | Holat |
|---|---|
| `overdue_cutoff` AYNAN bir marta ta'riflangan | ✅ `grep ... \| wc -l` -> `1` |
| `notifications.py` va `reconciliation.py` ikkalasi ham chaqiradi | ✅ ikkalasida ham `cutoff=overdue_cutoff(...)` |
| Test qobiqlardan yuritadi | ✅ `worker.overdue_reminder_task` / `worker.reconciliation_open_task` |
| WR-06 sabotaji o'lchandi | ✅ test qizardi |
| `CASE_LOOKBACK_DAYS` bor, docstringi reestrni ko'rsatadi | ✅ RECON-04, 08-07/08-10 nomma-nom |
| `service_date >= :floor` sharti bor | ✅ |
| Chegaraviy kun testi bor | ✅ `test_the_lookback_boundary_day_still_opens_a_case` |
| WR-09 sabotaji o'lchandi | ✅ aynan bitta test qizardi |
| O'lchanmagan tayming da'vosi yo'q | ✅ olib tashlandi (A yo'li), `RESOLVE_MIN_LATENCY_SECONDS` ham yo'q |
| Tanlangan yo'l va sabab SUMMARY da | ✅ Task 3 bo'limi |
| 7-faza mezonlari yashil | ✅ 10 passed |

## Known Stubs

Yo'q — bu reja mavjud xulqni tuzatdi, yangi yuza ochmadi.

## Threat Flags

Yo'q — yangi tarmoq endpointi, auth yo'li, fayl kirish naqshi yoki
ishonch chegarasidagi sxema o'zgarishi qo'shilmadi. Reja `<threat_model>`
dagi uchala `mitigate` bandi (T-08-23, T-08-24, T-08-25) bajarildi.

## Self-Check: PASSED

- `08-06-SUMMARY.md` — FOUND
- 7 ta commit (`5939839`, `c40c530`, `6978331`, `280e7d7`, `10cf06a`,
  `c30816e`, `2f69ea2`) — hammasi `git log` da FOUND
- Ishchi daraxt toza (`git status --short` bo'sh)
- ⚠ `.env` va `ops/seaweedfs/s3.json` ATAYIN commit qilinmadi —
  ikkalasi ham `.gitignore` da (sirlar)
