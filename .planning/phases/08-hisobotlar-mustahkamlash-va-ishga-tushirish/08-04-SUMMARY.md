---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 04
subsystem: hisobot-arifmetikasi
tags: [reports, sql, multi-tenant, billing, reconciliation]
requires:
  - services/core-api/app/repositories/billing_repo.py
  - services/core-api/app/repositories/reconciliation_repo.py
  - packages/sbozor-core/sbozor_core/enums.py
provides:
  - "report_repo.revenue_by_day() — davr tushumi (ikki sana, ikki ustun, nol kunlar)"
  - "report_repo.receivables() — qarzdorlik reestri, ism SERVERDA joinlangan"
  - "report_repo.anomaly_archive() — nomuvofiqlik arxivi, ikki sinf / ikki sanoq"
  - "ARCHIVE_KIND_UNPAID / ARCHIVE_KIND_UNREGISTERED — sinf nomlari enumdan"
affects:
  - "08-07 (JSON marshrutlari) — javob envelopelari shu DTO'lardan quriladi"
  - "08-10 (.xlsx eksport) — AYNI DTO'dan, ikkinchi hisob yo'li YO'Q"
  - "08-16 (3 tomonlama solishtiruv) — pul arifmetikasi shu moduldan"
tech-stack:
  added: []
  patterns:
    - "generate_series + LEFT JOIN LATERAL — nol kun QATOR sifatida chiqadi"
    - "sum(...) OVER () — yig'indi SERVERDA, klient reduce qilmaydi"
    - "unnest(uuid[], bigint[]) — arifmetika billing_repo dan, so'rov faqat yuza"
    - "UNION ALL + kind ustuni — ikki sinf bitta xronologiyada, sanoqlar alohida"
key-files:
  created:
    - services/core-api/app/repositories/report_repo.py
    - tests/integration/test_report_repo.py
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/deferred-items.md
  modified: []
decisions:
  - "revenue_by_day() `RevenuePeriod` qaytaradi, yalang'och `list` EMAS — yig'indini ALOHIDA qaytarish talabini ro'yxat ifodalay olmaydi"
  - "`:from_date::date` shakli RAD ETILDI — text() bind regeksi parametrni topmaydi va modul IMPORTDA yiqiladi; `CAST(:from_date AS date)` ishlatildi"
  - "receivables(): `as_of = to_date + 1 kun` IKKALA billing chaqiruvida ham bir xil — G-14 tengligi"
  - "oldest_unpaid_date `vendor_charge_allocation()` dan (FIFO nomlangan qoidasi), sotuvchi boshiga bitta chaqiruv — narx ONGLI"
  - "stall_codes `code_sort` bo'yicha, DISTINCT ichki so'rovda — leksikografik «1,10,100,2» rad etildi"
  - "anomaly_archive() sinf nomlarini ENUMDAN oladi; yangi lug'at javob bilan bazani ajratardi"
  - "arxiv `closed_day_occupied` va `no_coverage_stall` ni QAMRAMAYDI — nomlangan qaror, deferred-items №1"
metrics:
  duration: 67 min
  completed: 2026-08-16
---

# Phase 8 Plan 04: Davr hisobotlarining arifmetikasi — Summary

Uch davr hisoboti (tushum · qarzdorlik reestri · nomuvofiqlik arxivi) mavjud
jadvallardan HOSILA `text()` SQL bilan qurildi — yangi agregat jadval ham,
oldindan hisoblab qo'yilgan ko'rinish ham yo'q; `_SIGNED_*_EXPR` `billing_repo`
dan import qilinadi, ya'ni G-14 darvozasi chetlab o'tilmaydi.

## Nima qurildi

### `services/core-api/app/repositories/report_repo.py`

Uchta funksiya, uchta `text()` so'rovi, beshta `frozen dataclass`:

| Funksiya | Qaytadi | Manba |
|---|---|---|
| `revenue_by_day()` | `RevenuePeriod` (qatorlar + ikki yig'indi) | `payments` · `daily_charges` · `charge_adjustments` |
| `receivables()` | `list[ReceivableRow]` | `vendor_outstanding()` · `vendor_charge_allocation()` · `vendors` · `stall_assignments` |
| `anomaly_archive()` | `AnomalyArchive` (qatorlar + ikki sanoq) | `reconciliation_cases` · `billing_anomalies` · `charge_evidence` |

Modul docstringi UCH faktni LITERAL yozadi: (1) yangi jadval yaratilmaydi;
(2) `_SIGNED_PAYMENT_EXPR` / `_SIGNED_ADJUSTMENT_EXPR` import qilinadi;
(3) `payments.business_date` va `daily_charges.service_date` aralashtirilmaydi.

### `tests/integration/test_report_repo.py`

To'qqiz integratsiya testi, haqiqiy `postgres:18.4` ustida, `tenant_session`
konteksti bilan. Uchala guruh ham «filtr ishladi» bilan «so'rov qator topmadi»
ni MEXANIK ravishda ajratadigan holatda yozilgan.

## Har vazifadagi asosiy qarorlar

**Task 1 — tushum.** Jim kun davrning ICHIDA joylashtirildi (birinchi kunda
hisob, uchinchisida to'lov): chetdagi bo'sh kun `GROUP BY` nosozligini
KO'RSATMASDI, chunki davr chegarasi baribir ikki qator berardi. To'lovning O'Z
`service_date` i ATAYIN kechagi kun qilindi — `business_date` o'rniga
`service_date` ga o'tib ketgan so'rov shundagina qizaradi (Pitfall 14 ning
sabotaj o'lchovi). Storno uch qatorli holatda (15k + 15k − 15k = 15k)
o'lchanadi: ikki qatorli holatda javob nol bo'lardi va «belgi qo'llandi» bilan
«so'rov qator topmadi» bir xil ko'rinardi.

**Task 2 — qarzdorlik reestri.** 06 `deferred-items.md` №9 YOPILDI: ism endi
serverda `LEFT JOIN` bilan olinadi. Uch rad etilgan yo'l docstringda LITERAL
sanaladi va rad etilgancha qoladi. `LEFT JOIN` (ichki `JOIN` emas) — himoya
QARZ QATORINING O'ZI uchun: ichki join bilan ismi topilmagan sotuvchining
qarzi hujjatdan jimgina yo'qolardi. Bu himoya FK tufayli ilova yo'lidan
erishib bo'lmaydigan holatda yashaydi, shuning uchun test HOLATNI kengaytiradi
(`session_replication_role = replica`, superuser sessiyasi) — 05-15 ning
«sabotaj o'lchanmasa testni emas, holatni kengaytir» darsi.

**Task 3 — nomuvofiqlik arxivi.** Ikki manba (`reconciliation_cases` va
`billing_anomalies`) BITTA xronologiyaga `UNION ALL` bilan qo'shiladi, sinf
`kind` ustunida. Ikki sanoq ALOHIDA va ularning yig'indisi javobda MAYDON
sifatida MAVJUD EMAS — bu `dataclasses.fields()` to'plam tengligi bilan
qulflangan, inkor tasdiq bilan emas (D-31). «To'lanmagan» ta'rifi bu yerda
IXTIRO QILINMAYDI: manba `recon.open` qo'ygan case, `daily_charges` −
`payments` uchinchi ta'rif bo'lardi.

## Deviations from Plan

### 1. [Rule 3 — Blocking] `:from_date::date` shakli modulni IMPORTDA yiqitadi

- **Topilgan joy:** Task 1, birinchi GREEN yugurishi
- **Muammo:** 08-RESEARCH Pattern 1 namunasi `generate_series(:from_date::date,
  :to_date::date, '1 day')` deb yozilgan. `text()` ning bind-parametr regeksi
  nomdan keyin yana ikki nuqta kelishini oldinga qarash bilan RAD ETADI, ya'ni
  parametr umuman topilmaydi va `bindparams()` yig'ilish paytida
  `sqlalchemy.exc.ArgumentError` bilan yiqiladi — modul IMPORT bo'lmaydi.
  Namuna hech qachon bajarilmagan.
- **Tuzatish:** `CAST(:from_date AS date)`. `gs::date`, `::bigint` va
  `'1 day'::interval` xavfsiz — ular bind parametridan KEYIN turmaydi.
- **Fayl:** `services/core-api/app/repositories/report_repo.py`
- **Commit:** `a8e3375` (sabab so'rov docstringida LITERAL yozildi)

### 2. [Rule 3 — Blocking] `revenue_by_day()` qaytish tipi `RevenuePeriod`

- **Muammo:** Reja imzoni `-> list[RevenueRow]` deb belgilaydi, LEKIN ayni
  bandda «yig'indi (`total_collected_soum`, `total_charged_soum`) ⛔ SERVERDA
  hisoblanadi va ALOHIDA qaytariladi» deydi. Yalang'och ro'yxat buni ifodalay
  olmaydi — chaqiruvchi baribir klientda `reduce` qilardi (UI-SPEC §8.2 ning
  aynan rad etgan yo'li).
- **Tuzatish:** `RevenuePeriod` envelopei (`rows` + ikki yig'indi), `AnomalyArchive`
  va `CaseListPage` bilan bir xil naqsh. Yig'indi `sum(...) OVER ()` bilan
  SERVERDA, ayni so'rovda hisoblanadi.
- **Ta'siri:** 08-07 va 08-10 `.rows` dan o'qiydi. Bu 06 `deferred-items.md`
  №5 bilan bir sinf va u yerda ham envelope tanlangan edi.
- **Commit:** `a8e3375`

### 3. [Rule 2 — Correctness] `stall_codes` `code_sort` bo'yicha saralanadi

- **Muammo:** Reja `string_agg(..., ', ' ORDER BY code)` deydi. Kod `text`
  va oddiy `ORDER BY code` «1, 10, 100, 11, 2» beradi — hujjatdagi ro'yxat
  odam o'qiy olmaydigan tartibda chiqardi (`resolve_stall_day_money()` da
  ALLAQACHON o'lchangan va yozilgan sabab).
- **Tuzatish:** `DISTINCT` ichki so'rovda, `ORDER BY code_sort, code` tashqi
  agregatda. `DISTINCT` MAJBURIY: bir sotuvchida bir rastaga ikki biriktirish
  davri bo'lishi NORMAL (bo'shliqdan keyin qaytgan sotuvchi) va kod ikki marta
  chiqardi.
- **Commit:** `9361045`

### 4. [Rule 2 — Correctness] `payment_count` storno qatorini HAM sanaydi

- Reja sanoqning semantikasini belgilamaydi. Tanlov: `payments` ning barcha
  qatorlari sanaladi (summa esa BELGILI, ya'ni bekor qilingan pul tushumga
  kirmaydi). Sabab: storno — kassirning AMALI va u to'lovlar jurnalida
  ko'rinadi; sanoqdan chiqarish hisobotdagi qatorlar sonini jurnalnikidan
  farq qiladigan qilardi. Qaror `RevenueRow` docstringida yozilgan.
- **Commit:** `a8e3375`

## Threat Flags

Yangi xavfsizlik yuzasi topilmadi — modul HTTP yuzasi bermaydi, marshrutlar
08-07 zimmasida. Reja `<threat_model>` idagi to'rt bandning uchtasi shu
qatlamda bajarildi:

| Threat ID | Holat | Qayerda |
|---|---|---|
| T-08-13 (Information Disclosure) | ✅ | Har uch so'rovda `market_id = :market_id`; arxivning tenant testi NAZORAT bilan |
| T-08-14 (SQL injection) | ✅ | f-string ga faqat import qilingan sobit `_SIGNED_*_EXPR`; har tashqi qiymat `bindparam(...)` bilan TIPLANGAN; `# noqa: S608` sababi izohda tor |
| T-08-15 (Repudiation) | ✅ | `collected_soum` va `charged_soum` ALOHIDA ustun; uchinchi «yagona tushum» maydoni YO'Q |
| T-08-16 (DoS) | ⏭ transfer | Chegara chaqiruvchi qatlamda (08-07) — repo chegara QO'YMAYDI va bu funksiya docstringida yozilgan |

## Known Stubs

Yo'q. Uchala funksiya ham haqiqiy ma'lumotdan o'qiydi va har biri integratsiya
testi bilan haqiqiy `postgres:18.4` ustida o'lchangan.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_report_repo.py -k revenue -q` | 3 passed |
| `pytest tests/integration/test_report_repo.py -k receivables -q` | 3 passed |
| `pytest tests/integration/test_report_repo.py -q` | **9 passed** |
| `pytest tests/tenancy -q` | **742 passed, exit 0** (regressiya yo'q) |
| `ruff check` + `ruff format --check` | All checks passed · 2 files already formatted |
| `mypy --strict` | Success: no issues found in 2 source files |

Qabul mezonlarining mexanik o'lchovi:

| Mezon | Natija |
|---|---|
| `grep -c "generate_series" report_repo.py` | **6** (≥ 1) |
| `grep -c "CREATE TABLE\|MATERIALIZED VIEW" report_repo.py` | **0** |
| `grep -ci "total_anomal\|anomaly_total\|combined" report_repo.py` | **0** |
| `_SIGNED_PAYMENT_EXPR` importi | `from app.repositories.billing_repo import (...)` — 70-75-qatorlar, ikkinchi ta'rif YO'Q |
| `AnomalyArchive` maydonlari | `{rows, unpaid_count, unregistered_count}` — testda to'plam tengligi bilan |

## TDD Gate Compliance

Uchala vazifa ham `tdd="true"` va uchalasida ham RED → GREEN ketma-ketligi
git tarixida ko'rinadi:

| Vazifa | RED (`test`) | GREEN (`feat`) |
|---|---|---|
| Task 1 | `31a2d3e` | `a8e3375` |
| Task 2 | `d4a7d79` | `9361045` |
| Task 3 | `82839a5` | `c9ba3d9` |

Har RED yugurishi ImportError bilan qizardi (`report_repo` moduli yo'q →
`receivables` yo'q → `ARCHIVE_KIND_UNPAID` yo'q), ya'ni birorta test kutilmagan
holda yashil bo'lmadi. REFACTOR bosqichi kerak bo'lmadi.

## Ochiq bandlar

`deferred-items.md` da uch band ochildi:

1. **Arxivda uchinchi/to'rtinchi anomaliya sinfi yo'q** — `closed_day_occupied`
   va `no_coverage_stall` davr arxivida ko'rinmaydi (javob shakli rejaning
   qabul mezoni bilan qulflangan). Ular kunlik ekranda `anomaly_list()` ning
   o'z hisoblagichlari bilan ALLAQACHON ko'rinadi.
2. **`recon.open` yugurmagan kun uchun `unpaid` qatori bo'lmaydi** — ta'rifning
   ongli oqibati. To'g'ri yechim SQL da qayta hisoblash EMAS, `recon.open`
   ning yurak urishini kuzatish (06 №2 bilan bir sinf).
3. ⛔ **Parallel worktree `docker compose -p sbozor` ni buzadi** — bu ijroda
   `sbozor-storage-1` konteyneri yiqildi (`.env` va `ops/seaweedfs/s3.json`
   worktree'da yo'q → Docker bo'sh katalog yaratadi). Yechim: izolyatsiyalangan
   compose proyekti + `--no-deps` + mavjud image'ni teglash. ⚠ To'lqin oxirida
   asosiy checkout'dan `docker compose up -d --force-recreate storage`
   yugurtirilsin.

## Self-Check: PASSED

| Tekshiruv | Natija |
|---|---|
| `services/core-api/app/repositories/report_repo.py` | FOUND (35 218 bayt) |
| `tests/integration/test_report_repo.py` | FOUND (34 443 bayt) |
| `.../08-04-SUMMARY.md` | FOUND |
| `.../deferred-items.md` | FOUND |
| Commitlar `31a2d3e · a8e3375 · d4a7d79 · 9361045 · 82839a5 · c9ba3d9 · af6a1f9` | Yettalasi ham `git log` da |
| O'chirilgan fayllar | **YO'Q** — yettala commit ham faqat qo'shish (`git log --stat`) |
