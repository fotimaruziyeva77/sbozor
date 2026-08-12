---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 10
subsystem: api
tags: [reconciliation, case, hit-rate, keyset, evidence, personal-data, rbac, audit]
requires:
  - "reconciliation_repo.list_cases / hit_rate / transition / case_evidence (07-07)"
  - "billing_repo.charge_list / anomaly_list / vendor_charge_allocation (06-06, 06-08)"
  - "Permission.REPORT_VIEW + Permission.DISPUTE_DECIDE — MAVJUD a'zolar (D-07)"
  - "0023_notification_domain — reconciliation_cases DB-audit triggeri + case_events o'zgarmasligi"
  - "tests/fixtures/notification_domain.py::seed_case; billing_domain (day_close bilan)"
provides:
  - "GET /api/v1/reconciliation/report — ikki sinf, dalil UUID, standart kun KECHA"
  - "GET /api/v1/reconciliation/cases — keyset envelope (day + rows + 4 hisoblagich + cursor)"
  - "GET /api/v1/reconciliation/cases/{case_id} — case + TO'LIQ tarix + dalil"
  - "PATCH /api/v1/reconciliation/cases/{case_id} — DISPUTE_DECIDE, ikki jurnal"
  - "GET /api/v1/reconciliation/hit-rate — hosila, null, 92 kun chegarasi"
  - "schemas: ReconciliationReportRow/Response, CaseRowResponse, CaseListResponse, CaseDetailResponse, CaseEventRow, CaseUpdateRequest, HitRateResponse"
  - "reconciliation_repo.case_detail() — case + tarix, topilmasa None"
  - "tests/tenancy: G7-6 ning to'rt nomlangan bandi (shu jumladan Telegram identifikatori)"
affects:
  - "07-15 / 07-16 (frontend) — sxema qat'iy, envelope ChargeListResponse bilan bir xil"
  - "07-17 (faza yakuni) — MINIMUM_MATRIX_ROUTES chegarasi hali ko'tarilmagan"
tech-stack:
  added: []
  patterns:
    - "keyset kursori UNUMSIZ SATR bo'lib chegaradan o'tadi — ichki shakl (created_at|uuid) klient kontrakti EMAS"
    - "hisobot keyset bo'ylab yurib TO'LIQ yig'iladi; budjet tugashi TRUNKATSIYA emas, NOSOZLIK (RuntimeError)"
    - "AUDITED_TABLES dagi jadval uchun app-audit CHAQIRILMAYDI — DB-trigger yagona yozuvchi"
    - "TenantSessionDep yo'lida `session.commit()` chaqirilmaydi — tranzaksiyani dependency yopadi"
    - "cross-tenant o'qish repo qatlamida `None`, yozuvda `LookupError` — ikki BOSHQA ma'no"
key-files:
  created:
    - services/core-api/app/api/v1/reconciliation.py
    - tests/integration/test_reconciliation_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - services/core-api/app/repositories/reconciliation_repo.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_personal_data_coverage.py
    - tests/tenancy/test_cross_tenant.py
decisions:
  - "⛔ `write_app_audit()` OLIB TASHLANDI (reja buyurgan): `reconciliation_cases` 0023 da NOTIFICATION_AUDITED_TABLES da va DB-trigger audit qatorini O'ZI yozadi — chaqiruv bilan sanoq +2 bo'ldi va bu AuditAction docstringi nomma-nom taqiqlagan DUBLIKAT"
  - "`?limit=` qo'shildi: usiz `next_cursor` FAQAT 51+ case'da tug'ilardi, ya'ni kursor shoxi SINALMAGAN kod bo'lib qolardi"
  - "`reconciliation_repo.case_detail()` qo'shildi — `list_cases()` KUN kesimi bilan ishlaydi, `GET /cases/{id}` esa kunni bilmaydi"
  - "`DIRECTOR_ROUTES` + direktor sessiyasi matritsaga qo'shildi — `DISPUTE_DECIDE` bozor adminida YO'Q, ya'ni 403 tenant darvozasini YOPIB qo'yardi"
  - "`NON_PERSONAL_BINARY_ROUTES` O'SMADI (reja buyurgan): beshala marshrut ham `response_model` e'lon qiladi, ya'ni bayt tasnifiga UMUMAN tushmaydi"
  - "Hisobot `expected_soum`/`paid_soum` ni HISOBLAMAYDI — birinchisi `charge_list()` dan, ikkinchisi `vendor_charge_allocation()` dan keladi"
metrics:
  duration: ~95 min
  completed: 2026-08-12
  tasks: 3
  files: 8
---

# Phase 7 Plan 10: Nomuvofiqlik hisoboti va case yuzasi — Summary

RECON-01 ning «rasm-dalil **havolalari**» so'zi endi kod darajasida
bir ma'noli: javobda `list[UUID]` va **imzolangan havolani ifodalash
TIP darajasida imkonsiz**. Beshala marshrut ham shaxsiy maydonsiz
o'tdi va buni **sabotaj** o'lchadi — `vendor_name` qo'shilganda darvoza
**to'rt testda** qizardi.

## Nima qurildi

**Task 1 — sxemalar (`2387b73`).** Sakkiz model (`ReconciliationReportRow/
Response`, `CaseRowResponse`, `CaseListResponse`, `CaseDetailResponse`,
`CaseEventRow`, `CaseUpdateRequest`, `HitRateResponse`), hammasi
`ConfigDict(extra="forbid")` bilan. Envelope `ChargeListResponse` naqshini
**takrorlaydi** (DQ-4). `hit_rate` — bo'limdagi yagona `float` va u pul
emas, nisbat; istisno docstringda **ochiq** yozildi.

**Task 2 — besh marshrut (`1a3e83c`).** `billing.py` ning aynan shakli:
`_reject()` (detail **satr**, CR-04), `_market_id()`, `_report_day()`
(standart — **kecha**, kelajak kuni **422**). Router `main.py` ga
`/api/v1/reconciliation` prefiksi bilan ulandi; qaror sababi (nega
`/billing` ostida emas) o'sha faylda uch bandda yozildi.

**Task 3 — darvoza va xulq (`a21c1d7`).** `test_personal_data_coverage.py`
ga to'rt band, `test_reconciliation_api.py` ga **17 test**.

## O'lchangan dalillar

### ⛔ Sabotaj — G7-6 (reja talab qilgan)

`ReconciliationReportRow` ga `vendor_name: str` vaqtincha qo'shildi.
Natija — **to'rtta** test qizardi:

| Test | Sabotajsiz | Sabotaj bilan |
|---|---|---|
| `test_reconciliation_routes_are_not_personal` (yangi) | yashil | **QIZIL** |
| `test_personal_data_routes_declare_read_audit` (mavjud) | yashil | **QIZIL** |
| `test_personal_data_routes_require_vendor_view` (mavjud) | yashil | **QIZIL** |
| `test_no_reconciliation_route_enters_the_personal_data_gate` (yangi) | yashil | **QIZIL** |

⛔ **Ikkinchi va uchinchi qatorlar eng qimmat**: ular MAVJUD darvozalar va
ular yangi marshrutlarni **avtomatik** qamragan — ya'ni G7-6 «reja
yozgani uchun» emas, **mexanizm sifatida** ishlaydi. Nosozlik xabari
aniq: `PERSONAL_ROUTES` da `/api/v1/reconciliation/report` paydo bo'ldi.

Quyidagilar sabotaj ostida ham **yashil qoldi** va bu darvozalarning
**aniqligini** isbotlaydi (sabotaj ular uchun ko'rinmas):

- `test_the_snapshot_surface_is_a_closed_set` — ⛔ **o'zgarmadi**, ya'ni
  yangi tasvir marshruti **ochilmagan** (T-06-81);
- `test_every_binary_response_route_is_classified`;
- `test_no_reconciliation_route_exposes_a_telegram_identifier` — ya'ni u
  `vendor_name` ga emas, **boshqa** to'plamga qaraydi;
- `test_gate_covers_a_meaningful_number_of_routes`.

Sabotaj o'lchovdan keyin **olib tashlandi** (`grep -c SABOTAJ` → `0`).

### ⛔ Ikki jurnal — reja matni bilan HAQIQAT to'qnashdi va HAQIQAT ustun turdi

Reja `PATCH` ga `write_app_audit(...)` ni buyurdi. Chaqiruv bilan
`audit_log` sanog'i **+2** bo'ldi (o'lchandi: `assert 3 == (1 + 1)`).
Sabab: `0023` migratsiyasi `reconciliation_cases` ni
`NOTIFICATION_AUDITED_TABLES` ga qo'shgan va unga `attach_audit_trigger()`
ulagan — DB-trigger qatorni **o'zi** yozadi.

Chaqiruv **olib tashlandi**; rejaning MAQSADI («ikki jurnal, ikkalasi ham
`+1`») **buzilmadi** — u boshqa qatlamdan bajariladi. Da'vo `+1` bilan,
`>= 1` bilan **EMAS** o'lchanadi (dublikatni ushlaydigan yagona shakl).

### Xulq darvozalari (`test_reconciliation_api.py`, 17 test)

| Da'vo | Natija |
|---|---|
| ikkala sinf ham hisobotda | ✓ `unpaid_count=1`, `unregistered_count=1` |
| `anomaly` qatorida `expected_soum` | **`null`** (nol EMAS), `vendor_id` ham `null` |
| `evidence_snapshot_ids` bo'sh emasmi | ✓ har ikki sinfda ham, hammasi `UUID` |
| javob tanasida `presigned`/`http`/`image` | **0** ta; `Content-Type: application/json` |
| rekursiv kalit skani | `vendor_name`/`phone`/`full_name` **yo'q**; nazorat: `vendor_id` **bor** |
| standart kun | **kecha**; kelajak kuni → **422 `day_in_future`** |
| bo'sh kunda hisoblagichlar | uchalasi ham **`0` bo'lib qaytadi** |
| kassir sessiyasi (3 marshrut) | **403** |
| bozor admini | `GET` → **200**, `PATCH` → **403** |
| `PATCH {"status": "other"}` | **422**; nazorat: `in_review` → **200** |
| o'tishdan keyin `case_events` | **+1**; `audit_log` **+1**; `actor_user_id` = direktor |
| bir xil holatga o'tish | **409 `status_unchanged`**, tarixga qator **yozilmadi** |
| keyset ikkinchi sahifasi | birinchisi bilan **kesishmaydi**, birlashmasi = seed |
| hisoblagichlar ikkala sahifada | **bir xil** (kun kesimi) |
| buzilgan kursor | **422**, jim e'tiborsizlik **EMAS** |
| `status` filtri hisoblagichlarga | **ta'sir qilmaydi**; `?status=other` → **422** |
| hit-rate maxraji | `justified=1, unjustified=1, open=1` → **0.5** |
| o'lchov yo'q | **`null`** (`0.0` EMAS) |
| oraliqsiz / 93 kun / teskari | **422** (`range_too_wide`, `range_invalid`); nazorat: **92 kun → 200** |
| begona bozor case'i | **404**, mavjud bo'lmagan ID bilan **bayt-bayt bir xil**; `PATCH` ham 404 |

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/integration/test_reconciliation_api.py -q` | **17 yashil** (reja ≥ 8 so'ragan) |
| `pytest tests/tenancy/test_personal_data_coverage.py test_route_coverage.py -q` | **36 yashil** |
| `pytest tests/tenancy -q` (07-08 darvozalari bilan) | TENANCY_RESULT |
| `pytest tests/unit/test_rbac_matrix.py -q` | RBAC_RESULT |
| `node --test frontend/scripts/role-gate.test.mjs` | **6/6 yashil** (G-8 parity) |
| `ruff check .` + `ruff format --check .` + `mypy .` | **toza** (326 fayl) |
| `MINIMUM_PERSONAL_ROUTES` | **4 — O'ZGARMAGAN** (`git diff` da yo'q) |
| `services/core-api/app/security/rbac.py` | `git diff --name-only` da **YO'Q** |
| `grep presign\|object_key\|https?://` marshrut modulida | **0** |
| `min_lines` (`reconciliation.py` ≥ 240) | **726** |

⚠ 07-08 ning uchala `/internal/bot/*` asserti va uning `EXEMPT_ROUTES`
yozuvi **tegilmadi** — `test_route_coverage.py` ga faqat YANGI bo'lim
qo'shildi va bot bo'limi o'z joyida qoldi.

## Rejadan chetlanishlar

### Rule 1 — reja MATNI haqiqatdan farq qilgan joyda HAQIQAT ustun turdi

**1. [Rule 1 - Bug] `write_app_audit(...)` OLIB TASHLANDI — u DUBLIKAT edi**

- **Topildi:** Task 3, `test_case_transition_writes_to_both_journals` da.
- **Muammo:** `audit_log` sanog'i `+2` (DB-trigger + app chaqiruvi). Bitta
  hodisa xavfsizlik jurnalida **ikki marta** ko'rinardi va «bugun nechta
  case yopildi?» savoli jurnaldan ikki xil javob berardi. Taqiq loyihada
  NOMMA-NOM yozilgan: `AuditAction` docstringi `shift_open` /
  `shift_close` / `charge_adjust` a'zolarini **aynan shu sabab bilan**
  rad etgan.
- **Yechim:** chaqiruv olib tashlandi, sabab marshrut docstringiga
  yozildi. Rejaning maqsadi (ikki jurnal, ikkalasi ham `+1`) **bajarildi**.
- **Fayllar:** `app/api/v1/reconciliation.py`
- **Commit:** `a21c1d7`

**2. [Rule 1 - Bug] `session.commit()` OLIB TASHLANDI**

- **Topildi:** `InvalidRequestError: Can't operate on closed transaction
  inside context manager` — `PATCH` javobini qurish paytida.
- **Muammo:** `TenantSessionDep` tranzaksiyani `async with session.begin()`
  bilan **o'zi** boshqaradi. `write_app_audit()` docstringi «chaqiruvchi
  tranzaksiyani O'ZI yopadi» deydi va u `AuthSessionDep` yo'li uchun
  to'g'ri (`auth.py` / `me.py` / `markets.py`), tenant yo'lida esa
  «chaqiruvchi» — **dependency**.
- **Fayllar:** `app/api/v1/reconciliation.py`
- **Commit:** `a21c1d7`

**3. [Rule 1 - Bug] `NON_PERSONAL_BINARY_ROUTES` GA QO'SHILMADI**

- **Topildi:** Task 3 boshida, `test_every_binary_response_route_is_
  classified` ni o'qiganda.
- **Muammo:** reja «yangi marshrutlar `NON_PERSONAL_BINARY_ROUTES` ga
  qo'shiladi» degan, lekin o'sha ro'yxat FAQAT `response_model` i YO'Q
  marshrutlar uchun. Beshalasi ham modelini e'lon qiladi, ya'ni qo'shish
  o'sha testning **eskirish** tekshiruvini (`classified - found`)
  qizartirardi.
- **Yechim:** teskari da'vo yozildi —
  `test_reconciliation_routes_never_enter_the_binary_classification`:
  (a) birorta marshrut modelsiz emas, (b) birortasi bayt-tasnifda emas.
  Da'vo KUCHLIROQ: model **borligi** maydon-nomi darvozasini haqiqatan
  ishlatadi (04-09 ning topilmasi — modelsiz javob darvozani ko'r qiladi).
- **Fayllar:** `tests/tenancy/test_personal_data_coverage.py`
- **Commit:** `a21c1d7`

### Rule 3 — rejaning `files_modified` i sanamagan, lekin matni TALAB qilgan fayllar

**4. [Rule 3 - Blocking] `services/core-api/app/repositories/reconciliation_repo.py`**

- **Topildi:** Task 2, `GET /reconciliation/cases/{case_id}` yozilishidan
  oldin. Reja «case + hodisalar tarixi» ni talab qiladi, lekin 07-07
  faqat `list_cases()` (KUN kesimi, `service_date` majburiy bind) va
  `case_evidence()` beradi — `case_id` bo'yicha o'quvchi **umuman yo'q**.
  Kunni klientdan so'rash uni javobning SHARTIGA aylantirardi va nizo
  hujjatidagi havola («shu case'ga qarang») ishlamay qolardi.
- **Yechim:** `case_detail()` + `CaseDetail` / `CaseEvent` — **qo'shimcha**
  bo'lim (fayl oxirida), mavjud birorta funksiya tegilmagan. Topilmaganda
  `None` qaytaradi, `LookupError` **emas**: `transition()` — YOZUV (jim
  qaytish yolg'on taassurot qoldirardi), bu esa SOF O'QISH va
  `billing_repo.charge_detail()` ning aynan qarori.
- **Commit:** `1a3e83c`

**5. [Rule 3 - Blocking] `tests/tenancy/test_cross_tenant.py`**

- **Topildi:** Task 2 dan keyin. `tenant_resource_routes()` NEGATIV
  ro'yxat bilan quriladi, ya'ni yangi `{case_id}` marshruti matritsaga
  **avtomatik** tushadi va `test_no_unclassified_routes`
  `PARAM_FILLERS["case_id"]` ni **talab qiladi**. Reja darvozani
  `test_route_coverage.py` da qayd etishni buyurgan, `PARAM_FILLERS` esa
  qo'shni faylda yashaydi (07-08 ning `EXEMPT_ROUTES` bandi bilan aynan
  bir xil holat).
- **Yechim:** to'rt o'zgarish, hammasi **qo'shimcha**:
  `MatrixBillingRows.case_id` (B bozorining HAQIQIY case'i, `billing_rows`
  fixture'i yozadi), `PARAM_FILLERS["case_id"]`, `BODY_FILLERS` yozuvi
  (`{"status": "in_review"}` — seed holati `new`, ya'ni 409 shoxiga
  tushmaydi) va `DIRECTOR_ROUTES` + `market_a_director_headers`.
- ⛔ **`DIRECTOR_ROUTES` MAJBURIY edi:** `DISPUTE_DECIDE` bozor adminida
  YO'Q, ya'ni matritsa `PATCH` ga **403** olardi va
  `test_cross_tenant_object_returns_404` aynan 403 ga qarshi yozilgan
  assertda yiqilardi. «Yiqilmasin» deb 403 ni ruxsat etish HUQUQ
  darvozasini TENANT darvozasi ustiga yopib qo'yardi va «begona bozorning
  case'ini yopib bo'lmaydi» da'vosi hech qachon sinalmasdi (OP-9).
- **Tozalash:** `reconciliation_case_events` va `reconciliation_cases`
  `daily_charges` dan **oldin** o'chiriladi (kompozit FK).
- **Commit:** `1a3e83c`

### Rule 2 — rejada yo'q, lekin usiz kontrakt YETIB BORMASDI

**6. [Rule 2 - Missing] `GET /reconciliation/cases?limit=`**

- **Topildi:** Task 3, `test_case_list_pagination_is_keyset` yozilayotganda.
- **Muammo:** repo kursorni FAQAT sahifa **to'lganda** beradi, ya'ni
  `CASE_PAGE_SIZE` (50) qat'iy bo'lganda ikkinchi sahifa 51 ta case'siz
  umuman tug'ilmasdi. Seed bozorida bir kunda ko'pi bilan ~18 case
  bo'ladi (6 rasta × [1 hisob + 2 case'ga arzir anomaliya turi]) —
  ya'ni `cursor` shoxi **hech qachon ochilmasdi** va u sinalmagan kod
  bo'lib qolardi (07-08 ning 4-ochiq bandi aynan shu holatni qayd etgan).
- **Yechim:** `limit: int | None = Query(ge=1, le=CASE_PAGE_SIZE)`.
  Chegara **ikki qatlamda**: HTTP da `le=`, repo da `max(1, min(...))` —
  klient bir so'rov bilan butun navbatni tortib ololmaydi.
- **Commit:** `a21c1d7`

**7. [Rule 2 - Missing] `test_no_reconciliation_route_exposes_a_telegram_identifier`**

- **Topildi:** rejaning O'ZI (Task 1, (a1) taqig'i) `chat_id` /
  `telegram_user_id` / `telegram_username` ni taqiqlaydi va **ochiq
  yozadi**: ular `PERSONAL_FIELDS` da bo'lmagani uchun C-10 darvozasi
  ularni **ushlamaydi**. Ya'ni taqiq faqat docstringda qolardi — CR-02
  ning aynan sinfi («SABAB yozilgan, KOD yozilmagan»).
- **Yechim:** alohida ro'yxat (`TELEGRAM_IDENTIFIER_FIELDS`) va alohida
  test. ⛔ `PERSONAL_FIELDS` ga **qo'shilmadi**: uning butun kuchi
  torligida va bu uchtasi BOSHQA talabga ega — ular `audit_read` +
  `VENDOR_VIEW` bilan «qonuniylashtirilmaydi», ular javobda **umuman
  bo'lmaydi**.
- **Commit:** `a21c1d7`

### Struktura bo'yicha ongli qarorlar

**Hisobot N+1 so'rovni QABUL QILADI.** Har case uchun `case_evidence()`
chaqiriladi. Yagona muqobil — dalil so'rovini hisobot so'roviga qo'shib
yozish, ya'ni `_CASE_EVIDENCE` ning **ikkinchi nusxasi**; 07-07 aynan shu
vasvasani `vendor_charge_allocation()` uchun nomma-nom rad etgan.
Taqsimlash esa **sotuvchi bo'yicha keshlanadi** (so'rov ichida) —
`allocate_charge_credit()` docstringi natijani jadvalga yozishni ham,
uzoq muddatli keshlashni ham taqiqlaydi.

**Hisobot keyset bo'ylab TO'LIQ yig'iladi, `REPORT_PAGE_BUDGET = 100`
esa TRUNKATSIYA chegarasi EMAS, nosozlik detektori.** Bir kunda bitta
rastada ko'pi bilan bitta hisob va bitta anomaliya bo'ladi, ya'ni
case'lar soni `2 × rasta_soni` dan oshmaydi (MVP konvertida ≤ 2000 =
40 sahifa). Budjetning tugashi — ma'lumot hajmi emas, **kursorning
aylanib qolishi**, shuning uchun `RuntimeError` (500), jim qisqarish
bilan emas: yashirin qisqargan hisobot «bugun nomuvofiqlik kam» degan
yolg'on xulosa berardi.

**`case_id` / `status` `| None` bo'lib qoldi (reja shakli).** Bugun
hisobot qatorlari FAQAT case'lardan quriladi, ya'ni ikkalasi ham to'lgan
keladi. `| None` — kontraktning **ochiq e'tirofi**: nomuvofiqlikning
o'zi `recon.open` yugurishidan oldin ham mavjud bo'ladi.

## Ochiq bandlar

**1. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA BAJARILMADI.**
`frontend/node_modules` gitignored va bu worktree'da YO'Q. Band bu
rejadan **mustaqil** va buni dalil tasdiqlaydi:
`git diff --name-only 4aec616 HEAD` — **aynan sakkizta fayl, sakkalasi
ham Python**. Birorta frontend fayl tegilmagan, birorta `messages/*.json`
kaliti qo'shilmagan. Node'ga bog'liq bo'lmagan darvoza BAJARILDI va
yashil: `node --test frontend/scripts/role-gate.test.mjs` — **6/6**
(G-8 parity, ya'ni `rbac.py` ↔ `rbac.ts` ajralmagan). Egasi: orkestrator.

**2. `MINIMUM_MATRIX_ROUTES` (80) KO'TARILMADI va bu ONGLI.** Shart `>=`,
ya'ni besh yangi marshrut darvozani qizartirmaydi. Ko'tarish D-32
intizomi bo'yicha faza **oxirida**, yakuniy o'lchov bilan (07-17) —
06-14 va 07-03 ning aynan qarori, `test_route_coverage.py` ning O'Z
docstringida yozilgan.

**3. Xato kodlari (`status_unchanged`, `range_too_wide`, `range_invalid`,
`cursor_invalid`, `not_found`, `day_in_future`, `market_not_selected`)
KLIENT REYESTRIGA hali ulanmagan.** Ular `app/services/billing_errors.py`
ga **qo'shilmadi** va bu ATAYIN: o'sha reyestrning soni
`frontend/scripts/error-codes.test.mjs` tomonidan uchala locale'dagi
`errorCause`/`errorFix` juftligi bilan solishtiriladi, ya'ni yangi kod
matn qo'shilmaguncha o'sha darvozani QIZARTIRARDI. Matn va ko'zgu —
07-16 ning ishi (WR-08 ning naqshi: kod marshrutdan qaytadi, tarjima
ekran bilan birga keladi).

**4. `assignee_user_id` ni TOZALASH yo'li YO'Q.** `transition()` uni
`COALESCE` bilan yangilaydi (07-07 SUMMARY, 5-ochiq band), ya'ni
`CaseUpdateRequest.assignee_user_id = None` «o'zgartirma» degani.
«Biriktirishni bekor qilish» amali 07-16 da kerak bo'lsa u ALOHIDA
argument bilan keladi va `None` ni «o'zgartirma» dan ajratadigan sentinel
talab qiladi.

**5. `subject_kind` bo'yicha FILTR yo'q** (07-07 ning 4-ochiq bandi kuchda
qoladi). `GET /cases` faqat `status` bo'yicha filtrlaydi. Hisobot ikkala
sinfni ham ko'rsatadi va sanoqlari alohida, ya'ni ekran bugun savolga
javob oladi; navbat ekrani «faqat to'lovsiz» filtrini so'rasa u
`_CASE_ROWS` ga bitta `AND` bo'ladi va hisoblagichlarga **tegmasligi**
kerak.

## Known Stubs

Yo'q. Beshala marshrut ham haqiqiy ma'lumot qaytaradi va uchtasi
6/7-fazaning hisoblanadigan ko'rinishlariga bog'langan
(`charge_list()`, `vendor_charge_allocation()`, `reconciliation_repo`).
Birorta qattiq kodlangan bo'sh qiymat renderga oqmaydi: bo'sh kundagi
`rows: []` + `0` hisoblagichlar — **stub emas, javob** («bu kunda
nomuvofiqlik yo'q» degan haqiqiy ma'no, va u ATAYIN «hisoblagich
ishlamayapti» dan farq qiladigan qilib qaytariladi).

`expected_soum: null` / `paid_soum: null` ham stub emas: birinchisi
«hisob yozilmagan» (sinf B), ikkinchisi «taqsimlash qatori topilmadi»
degan **o'lchangan** ma'noga ega va nol bilan almashtirilmasligi
D-13 ning aynan qoidasi.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-network-surface | services/core-api/app/api/v1/reconciliation.py | ⛔ **Ochiq qayd, yangi yuza EMAS**: rejaning `<threat_model>` i beshala marshrutni to'liq qamraydi (T-07-55…T-07-61). Yuza `/api/v1` ostida, mavjud sessiya va mavjud huquq matritsasi bilan; nginx uni odatdagi `/api/` yo'li bilan proxy qiladi. Mitigatsiyalar: `REPORT_VIEW`/`DISPUTE_DECIDE`, cross-tenant **404**, oraliq chegarasi **92 kun**, yechim matni **2000 belgi**, javobda **shaxsiy maydon yo'q**, dalil **faqat `UUID`**. |

⚠ Rejaning tahdid reyestridagi **birorta** disposition o'zgarmadi.
`T-07-SC` («yangi paket o'rnatilmaydi») kuchda: birorta bog'liqlik
qo'shilmadi, `pyproject.toml` tegilmadi. **Sxema o'zgarishi ham yo'q** —
birorta migratsiya qo'shilmadi, ya'ni 07-04 ning
`EXPECTED_DEFINER_FUNCTIONS` to'plam tengligi darvozasi tegilmadi.

Rejaning `<threat_model>` idagi yettala mitigatsiya bajarildi:

| Threat | Mitigatsiya | O'lchov |
|---|---|---|
| T-07-55 | javob modellarida shaxsiy maydon yo'q | ⛔ **sabotaj** — 4 test qizardi |
| T-07-56 | javobda faqat `UUID`; yangi tasvir marshruti yo'q | `presigned/http/image` skani = 0; snapshot yopiqligi o'zgarmadi |
| T-07-57 | `resolution_note` uzunligi 2000 | 2001 belgi → `ValidationError` |
| T-07-58 | `REPORT_VIEW` / `DISPUTE_DECIDE` — mavjud matritsa | kassir 403 (3 marshrut); bozor admini `PATCH` da 403; `rbac.py` diffda YO'Q; G-8 parity 6/6 |
| T-07-59 | begona case → 404, mavjud bo'lmagani bilan bayt-bayt bir xil | ✓ (`GET` va `PATCH` ikkalasida ham) |
| T-07-60 | oraliq majburiy, maksimal 92 kun | oraliqsiz/93/teskari → 422; nazorat: 92 → 200 |
| T-07-61 | ikki jurnal, ikkalasi ham `+1` | `case_events` +1 **va** `audit_log` +1 (⛔ `+2` EMAS — dublikat topildi va olib tashlandi) |

## Self-Check: SELFCHECK_RESULT
