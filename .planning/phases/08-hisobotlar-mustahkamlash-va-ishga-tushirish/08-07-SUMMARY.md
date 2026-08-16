---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 07
subsystem: backend-hisobot-json-yuzasi
tags: [RECON-04, D-01, D-03, D-04, D-07, D-09, R-1, R-2, Pitfall-1, Pitfall-11, Pitfall-13]
requires:
  - "app/repositories/report_repo.py — revenue_by_day() / receivables() / anomaly_archive() (08-04)"
  - "app/settings.py — report_max_period_days, report_max_rows (08-01)"
  - "app/security/rbac.py — Permission.REPORT_VIEW (mavjud, TEGILMADI)"
  - "app/security/audit.py — audit_read, AuditReadIntent, TABLE_VENDORS"
  - "frontend/src/lib/report-errors.ts — REPORT_ERROR_CODES (08-03, reyestr langari)"
  - "frontend/src/lib/report-queries.ts — REPORT_KINDS -> yo'l nomlari (08-03)"
provides:
  - "GET /api/v1/reports/revenue — davr tushumi, kunlik qatorlar, ikki yig'indi"
  - "GET /api/v1/reports/debtors — qarzdorlik reestri (ism SERVERDA joinlanadi, BITTA audit_read)"
  - "GET /api/v1/reports/anomalies — nomuvofiqlik arxivi, ikki sanoq alohida"
  - "REPORT_PAGE_SIZE = 500 — ekran sahifasi (hujjat chegarasi EMAS)"
  - "To'rt xato kodi: report_period_future / _invalid / _too_long / report_too_large"
affects:
  - "app/main.py — reports_router /api/v1/reports prefiksi bilan ulandi"
  - "tests/tenancy/test_route_coverage.py — /reports yuzasi YOPIQ to'plam (N=3)"
  - "tests/tenancy/test_personal_data_coverage.py — PERSONAL_ROUTES HOSILA to'plami /debtors bilan o'sdi"
  - "08-12 (.xlsx) shu uch nomdan yuradi; 08-13/08-15 ularni iste'mol qiladi"
tech-stack:
  added: []
  patterns:
    - "Huquq IMZODA (Annotated Dep), dekoratorda emas — billing.py naqshi"
    - "Bitta so'rov = bitta audit_read, natija hajmidan MUSTAQIL"
    - "Sahifalash ILOVA qatlamida: row_count BUTUN DAVRNIKI, shown_count sahifaniki"
    - "Server davrni JIMGINA kesmaydi — sig'masa 422 bilan RAD ETADI"
    - "Yuza yopiq to'plam bilan qulflanadi va SON test NOMIDA yoziladi (R-11)"
key-files:
  created:
    - services/core-api/app/api/v1/reports.py
    - tests/integration/test_reports_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/tenancy/test_route_coverage.py
decisions:
  - "platform_admin ga REPORT_VIEW BERILMADI (Pitfall 11 varianti A, UI-SPEC O-07) — bozorlararo rolga hisobot ochish bitta akkauntni butun platformaning shaxsiy ma'lumot xaritasiga aylantirardi; taqiq test NOMI bilan o'lchanadi"
  - "Marshrut nomlari KLIENT KONTRAKTIDAN: /revenue, /debtors, /anomalies — reja aytgan /receivables, /discrepancies EMAS; server klientni kuzatadi (08-03 REPORT_KINDS to'plam tengligi bilan qulflangan)"
  - "Davrning yuqori chegarasi KECHA, bugun EMAS — daily_charges D+1 04:10 da tug'iladi, ya'ni bugunni qamragan hisobot KAM KO'RSATILGAN bo'lib .xlsx orqali tarqalardi"
  - "Uch davr xatosi UCH ALOHIDA kod bilan, bittaga yig'ilmaydi — yolg'on sabab foydalanuvchini tizim buzuq degan xulosaga olib borardi"
  - "Xato kodlari ALL_BILLING_ERROR_CODES reyestriga QO'SHILMADI — reyestrning SONI frontend darvozasiga bog'langan; hisobot kodlarining O'Z reyestri report-errors.ts da"
  - "Sahifalash SQL da EMAS, ilova qatlamida — row_count BUTUN DAVRNIKI bo'lishi shart va ikkinchi count(*) so'rovi ro'yxat bilan sanoqni ajratardi"
  - "audit_read AYNAN /debtors da: /revenue va /anomalies javoblarida shaxsiy maydon yo'q va ularga audit qo'yish jurnalni shovqinga to'ldirardi"
  - "phone javobda YO'Q (UI-SPEC O-03) — telefon aloqa ma'lumoti va u eksportga tushib fayl bo'lib tarqalardi"
  - "QUERY_PARAM_ROUTES istisnosi ISHLATILMADI — majburiy from/to matritsani buzmaydi, chunki istisnoning yagona iste'molchisi BODY_ROUTES ustidan yuradi"
metrics:
  duration: "o'lchanmadi (sessiya uzilishi — pastdagi izohga qarang)"
  tasks: 3
  files: 5
  completed: 2026-08-16
---

# Phase 8 Plan 07: `/api/v1/reports` yuzasining JSON yarmi Summary

Uch davr hisoboti (`/revenue`, `/debtors`, `/anomalies`) JSON bilan
ishlaydi: huquq imzoda, qarzdorlik reestri **bitta** `audit_read` yozadi
(200 qarzdorda ham), davrning yuqori chegarasi **kecha** va u 422 bilan
majburlanadi, yuza esa uch marshrutli **yopiq to'plam** bilan qulflangan.

## ⚠ Bu reja KECH yopildi — sabab yozib qo'yiladi

Ijro **oldingi sessiyada** worktree'da bajarilgan va uch vazifaning ham
commiti `main` ga birlashtirilgan (`166edce`, `0539c7d`, `a54481c`,
`8b8f1e6`), lekin **sessiya SUMMARY yozilishidan oldin uzilgan**. Shu
sababli `c257dbb` merge commiti «SUMMARY yo'q — yakunlanadi» degan
izohni ko'targan.

Bu yakunlash sessiyasida **yangi ish qilinmadi**. Qilingani:
har uch vazifaning har bir `acceptance_criteria` si kodda dalil bilan
tekshirildi, rejaning `<verify>` va `<verification>` buyruqlari
**haqiqatan yugurtildi**, rejadagi **majburiy sabotaj** o'lchandi va
natijalar quyida yozildi. **Bo'shliq topilmadi — kod tegilmadi.**

## Nima qilindi

### Task 1 — Modul skeleti, DTO'lar va davr yechish qoidasi

`services/core-api/app/api/v1/reports.py` `billing.py` ning modul boshi
bilan yaratilgan: `from __future__ import annotations`,
`router = APIRouter(tags=["reports"])`, `_reject()` (⛔ `detail` **satr**,
lug'at emas — `api-client.ts::detailOf()` kontrakti), `_market_id()`.

`date` va `UUID` **ish vaqtida** import qilingan va sabab izohda literal:
`from __future__ import annotations` ostida annotatsiyalar satr bo'lib
qoladi va FastAPI ularni Pydantic uchun yecha olmaydi — nosozlik
marshrutda emas, OpenAPI meta-testida ko'rinardi.

`_report_period()` uch xatoni **uch alohida kod** bilan beradi:

| Shart | Kod | HTTP |
|---|---|---|
| `to > business_today() - 1` | `report_period_future` | 422 |
| `from > to` | `report_period_invalid` | 422 |
| `(to - from).days + 1 > report_max_period_days` | `report_period_too_long` | 422 |

Uchtala DTO o'rami `schemas.py` da (`RevenueReportResponse`,
`ReceivablesReportResponse`, `AnomalyArchiveResponse`) va uchalasida ham
`from_date`/`to_date` **majburiy**: ekran davr jumlasini **serverning
javobidan** chizadi, `nuqs` holatidan emas (G-39).

### Task 2 — Uch JSON marshruti: huquq, audit, sahifalash

Huquq imzoda: `ReportViewerDep`. `/debtors` da **ikkinchi** huquq
(`VendorFieldGuardDep` → `VENDOR_VIEW`) va **uchinchi** dependency
(`ReceivablesReadIntentDep` → `audit_read(TABLE_VENDORS,
reason="report_receivables")`). E'lon **tartibi** majburiy va u bezak
emas: FastAPI dependency'larni shu tartibda hal qiladi va 403 olgan
so'rov `audit_read` gacha yetib kelmaydi — teskari tartibda jurnalda
«kassir qarzdorlar ro'yxatini o'qidi» degan **yolg'on dalil** paydo
bo'lardi (T-02-71).

Pitfall 1 kodda ochiq yozilgan: `PERSONAL_ROUTES` — **hosila** to'plam va
`/debtors` unga **o'zi** tushadi; bu D-07 ning niyatiga mos, chunki taqiq
**operativ moliyaviy JSON** marshrutlariga (`/billing/charges`,
`/reconciliation/cases`) tegishli va ular tegilmadi.

Sahifalash **ilova qatlamida** (`_page()`), SQL da emas — `row_count`
butun davrniki bo'lishi shart va ikkinchi `count(*)` so'rovi ro'yxat
bilan sanoqni ajratardi. `row_count > report_max_rows` → 422
`report_too_large`: **jimgina kesish taqiq**.

### Task 3 — Yuza yopiq to'plam bilan qulflandi

`test_the_reports_surface_is_exactly_three_routes` — to'plam **tengligi**
bilan (`{("GET", …) × 3}`), «kamida uchtasi» bilan emas. Son test
**nomida** va u qo'lda yangilanadi (R-11 darsi). Yoniga uch mustaqil
darvoza qo'shilgan:

| Test | Nimani ushlaydi |
|---|---|
| `test_every_reports_route_is_documented_in_openapi` | uchalasi OpenAPI'da — 08-13/08-15 sxemani shundan oladi |
| `test_only_the_debtors_route_carries_personal_data` | shaxsiy yuza AYNAN bitta: `/debtors` to'plamda BOR, qolgan ikkitasi YO'Q |
| `test_the_reports_surface_needs_no_query_param_exemption` | istisno reyestri BO'SH qolgani MEXANIK sabab bilan |

## ⛔ ONGLI QAROR: `platform_admin` ga `REPORT_VIEW` **BERILMADI**

**(Pitfall 11 varianti A, UI-SPEC O-07.)**

Platforma admini **bozorlararo** rol: u har bozorni ko'ra oladi. Unga
hisobot yuzasini ochish **har bozorning qarzdorlari ismini bitta
akkauntga** to'plardi — ya'ni bitta sessiya butun platformaning shaxsiy
ma'lumot xaritasiga aylanardi. Uning ishi bozorni **qurish** (wizard) va
**platforma** auditini o'qish; bozorning **puli va qarzdorlari** uning
yuzasi emas.

Bu «unutilgan huquq» emas, taqiq va u **nom bilan** o'lchanadi:
`test_the_platform_admin_cannot_read_any_report` — uchala marshrut uchun
403, va test docstringi sababni to'liq yozadi. Testda sessiyada bozor
**tanlangan** (`platform_admin_headers`), ya'ni 403 aynan **huquqdan**
keladi, `market_not_selected` dan emas — bu farq testning butun ma'nosini
ushlab turadi.

⛔ `ROLE_PERMISSIONS` matritsasi, `rbac.py` ↔ `rbac.ts` juftligi va
`role-gate.test.mjs` darvozasi **tegilmadi** (R-1, M-6).

## Sabotaj o'lchovi (reja MAJBURIY degan — shu sessiyada bajarildi)

`/debtors` handleridan `intent: ReceivablesReadIntentDep` dependency si
va niyat to'ldirish qatorlari olib tashlandi:

```
E  AssertionError: 200 qarzdorli so'rov 0 ta audit qatori yozdi —
   kutilgan AYNAN 1 (bitta so'rov = bitta o'qish hodisasi, D-09)
   assert (0 - 0) == 1

E  AssertionError: Quyidagi `GET` marshrutlari shaxsiy maydon qaytaradi,
   lekin o'qish auditini e'lon qilmaydi (D-09)...
       /api/v1/reports/debtors -> ['vendor_name']
   assert not ['/api/v1/reports/debtors']

FAILED test_one_debtors_request_writes_exactly_one_audit_row[uch]
FAILED test_one_debtors_request_writes_exactly_one_audit_row[ikki-yuz]
FAILED tests/tenancy/test_personal_data_coverage.py::test_personal_data_routes_declare_read_audit
```

**Ikkala darvoza ham qizardi** — reja «ikkinchisi qizarmasa javobda ism
bor-yo'qligini tekshir» degan zaxira yo'lni ko'rsatgan edi, u kerak
bo'lmadi: `/debtors` hosila to'plamga `vendor_name` bilan **tushadi** va
undan `audit_read` **avtomatik** talab qilinadi. Ya'ni himoya reja
intizomiga emas, **mexanikaga** tayanadi.

⚠ Nazorat: `test_personal_data_routes_require_vendor_view` **yashil
qoldi** — sabotaj faqat auditni oldi, `VENDOR_VIEW` joyida qoldi. Ikki
darvoza haqiqatan **ikki boshqa savolni** o'lchayapti (C-9), bittasining
soyasi emas.

Fayl `git checkout -- services/core-api/app/api/v1/reports.py` bilan
tiklandi; ishchi daraxt toza.

## Rejadan chetlanishlar

### 1. [Rule 1 — Klient kontrakti] Marshrut nomlari: `/debtors`, `/anomalies`

- **Reja aytgan:** `/receivables` va `/discrepancies`
- **Yozilgan:** `/debtors` va `/anomalies`
- **Sabab:** 08-03 (to'lqin 1) `REPORT_KINDS` ni `{revenue, debtors,
  anomalies, accuracy}` deb **to'plam tengligi** bilan qulflagan
  (UI-SPEC §12.1, G-43a) va `report-queries.ts::buildReportDataPath()`
  yo'lni aynan o'sha a'zodan quradi: `/api/v1/reports/{kind}`. Ya'ni
  jo'natilgan klient `/debtors` va `/anomalies` ga boradi.
- **Nega bu jim nosozlik bo'lardi:** boshqa nom tanlansa komponent
  testlari mock bilan yashil qolardi va 404 **faqat jonli ekranda**
  ko'rinardi.
- **Qayd:** sabab `reports.py` modul docstringining 2-bandida va
  `REPORTS_ROUTES` docstringida **literal** yozilgan; 08-12 ning
  `.xlsx` nomlari ham shu reyestrdan yuradi.

### 2. [Rule 2 — Yetishmayotgan kritik funksiya] `_guard_row_count()` uchala marshrutda

Reja `report_too_large` ni Task 2 ning xulq ro'yxatida aytgan, lekin
Task 1 ning yordamchilar ro'yxatida yo'q edi. Chegara **uchala**
marshrutga qo'yildi (T-08-30), aks holda `/revenue` va `/anomalies`
chegarasiz qolardi.

### 3. DTO nomlari `ReceivablesReportResponse` / `RevenueReportRow` va h.k.

Reja `ReceivablesResponse` degan edi; `schemas.py` dagi mavjud
konvensiya (`ChargeListResponse`, `OccupancyAccuracyResponse`) `…Report…`
bo'g'inini talab qildi va qator DTO'lari ham alohida ajratildi.
Maydonlar to'plami rejadagidek qoldi.

## Tekshiruv natijalari — HAQIQIY o'lchov (2026-08-16, Docker 29.4.2)

| O'lchov | Natija |
|---|---|
| `docker compose --profile test run --rm tests pytest tests/tenancy -q` | **EXIT 0** — 764 passed |
| `… pytest tests/integration/test_reports_api.py -q` | **EXIT 0** — 41 passed |
| `… pytest tests/integration/test_phase6_criteria.py tests/integration/test_phase7_criteria.py tests/tenancy/test_meta.py -q` | **EXIT 0** — 53 passed (oldingi fazalar hamon yashil) |
| Sabotaj (`audit_read` olib tashlandi) | **3 FAILED** — ikkala darvoza ham qizardi |

⚠ Docker demoni sessiya boshida **ishlamayotgan** edi; Docker Desktop
ishga tushirilib, o'lchovlar shundan keyin olindi. Ya'ni yuqoridagi
natijalar **haqiqiy yugurish**, taxmin emas.

## Qabul mezonlari — bandma-band dalil

### Task 1

| Mezon | Holat | Dalil |
|---|---|---|
| `reports.py` mavjud va `router` eksport qiladi | ✅ | `__all__ = ["REPORT_PAGE_SIZE", "router"]`, `reports.py:112-114` |
| `grep -c require_any_permission` → `0` | ✅ | o'lchandi: `0` (kodda ham, izohda ham nomi yo'q) |
| `date` ish vaqtida import (`TYPE_CHECKING` da emas) | ✅ | `reports.py:81` `from datetime import date, timedelta` |
| `_report_period` uch xato kodi | ✅ | `reports.py:266-276` |
| `grep -c … billing_errors.py` → `0` | ✅ | o'lchandi: `0` |
| `tests/tenancy/test_route_coverage.py` EXIT 0 | ✅ | butun `tests/tenancy` EXIT 0 |

### Task 2

| Mezon | Holat | Dalil |
|---|---|---|
| `/revenue` `REPORT_VIEW` bilan 200, `cashier` bilan 403 | ✅ | `test_the_director_reads_every_report`, `test_the_cashier_cannot_read_any_report` |
| `/debtors` javobida `vendor_name` bor, `phone` YO'Q | ✅ | `ReceivablesReportRow` (`extra="forbid"`, `phone` maydoni yo'q) + `test_the_debtors_row_carries_the_name_and_never_the_phone` |
| `audit_read(TABLE_VENDORS, reason="report_receivables")` bor | ✅ | `reports.py:143-146`, handlerda 3-o'rinda |
| 200 sotuvchida AYNAN 1 audit qatori | ✅ | `test_one_debtors_request_writes_exactly_one_audit_row[ikki-yuz]` passed |
| `test_reports_api.py` EXIT 0 | ✅ | 41 passed |
| `tests/tenancy` EXIT 0 | ✅ | 764 passed |
| Sabotaj natijasi SUMMARY da | ✅ | yuqoridagi bo'lim |

### Task 3

| Mezon | Holat | Dalil |
|---|---|---|
| `reports` prefiksi uchun to'plam tengligi testi, nomida SON | ✅ | `test_the_reports_surface_is_exactly_three_routes` |
| `tests/tenancy` EXIT 0 | ✅ | 764 passed |
| `QUERY_PARAM_ROUTES` istisnosi — sabab + havola | ✅ | istisno **ishlatilmadi**; `test_the_reports_surface_needs_no_query_param_exemption` buni mexanik sabab bilan qulflaydi va tenant o'lchoviga havola qiladi |

### Reja darajasidagi `success_criteria`

| Mezon | Holat |
|---|---|
| Uch JSON marshruti ishlaydi, huquq va audit e'lonlari to'liq | ✅ |
| `platform_admin` qarori SUMMARY da | ✅ nomma-nom bo'lim |
| Bitta so'rov = bitta `audit_read` (200 da ham) o'lchangan | ✅ |
| Davrning yuqori chegarasi KECHA va 422 bilan majburlanadi | ✅ `test_today_is_rejected_as_a_future_period` |
| `/reports` prefiksi yopiq to'plam bilan qulflangan | ✅ |

## Known Stubs

Yo'q. Uchala marshrut ham `report_repo` (08-04) dan **haqiqiy** ma'lumot
oladi; to'qilgan qiymat, bo'sh ro'yxat konstantasi yoki «hozircha mavjud
emas» matni qo'shilmadi.

## Threat Flags

Yo'q — reja `<threat_model>` idagi beshala `mitigate` bandi bajarildi:

| Threat | Bajarilishi |
|---|---|
| T-08-26 (huquq ko'tarilishi) | `require_permission(REPORT_VIEW)` + rol matritsasi (5 rol × 3 marshrut) |
| T-08-27 (cross-tenant) | RLS + `TenantSessionDep` + `test_the_other_markets_director_never_sees_market_a_rows` (nazorat holati bilan) |
| T-08-28 (auditsiz o'qish) | `audit_read(..., reason="report_receivables")`, sabotaj bilan o'lchangan |
| T-08-29 (ortiqcha maydon) | `phone` yo'q; `extra="forbid"` |
| T-08-30 (chegarasiz davr/qator) | `report_period_too_long` + `report_too_large` |

Yangi tarmoq endpointi **qo'shildi** (uch `GET`), lekin ular reja
`<threat_model>` ida allaqachon nomlangan va yopiq to'plam testi bilan
qulflangan — reyestrdan tashqarida qolgan yuza yo'q.

## Ochiq qolgan bandlar

⚠ **`/accuracy` marshruti bu rejada YO'Q va bu kutilgan.**
`REPORT_KINDS` to'rt a'zoli (`revenue`, `debtors`, `anomalies`,
`accuracy`), yuza esa uchta. Aniqlik hisoboti `GET /occupancy/accuracy`
da allaqachon yashaydi (05-12) — uni `/reports` prefiksiga ko'chirish
yoki klient reyestrini moslashtirish **08-12/08-13** ning qarori.
Bugungi holatda klient `/reports/accuracy` ga borsa 404 oladi.

## Self-Check: PASSED

- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-07-SUMMARY.md` — FOUND
- `services/core-api/app/api/v1/reports.py` — FOUND
- `tests/integration/test_reports_api.py` — FOUND
- `tests/tenancy/test_route_coverage.py` — FOUND (`/reports` bloki 561-744)
- Commitlar `git log` da FOUND: `166edce`, `0539c7d`, `a54481c`, `8b8f1e6`
- Sabotajdan keyin ishchi daraxt toza (`git status --short` da faqat
  rejadan tashqari `??` fayllar)
- ⚠ Ijro vaqti (`duration`) **o'lchanmadi** — oldingi sessiya uzilgan va
  boshlanish vaqti yozib qolinmagan; taxminiy son yozish yolg'on
  o'lchov bo'lardi
