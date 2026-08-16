---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 14
subsystem: backend-daftar-importi
tags: [RECON-04, D-17, D-14, D-20, D-21, R-4, R-11, Pattern-6, WR-05, T-08-58, T-08-59, T-08-60, T-08-61, T-08-62, T-08-63, ledger, xlsx-import, idempotency, audit]
requires:
  - "migrations/versions/0024_ledger_entries.py — jadval, kompozit FK, UNIQUE(market_id, business_date, stall_id), audit triggeri (08-02)"
  - "app/api/v1/imports.py — _read_bounded / _read / _reject_if_invalid / _conflict / _xlsx_response / _locale_of (02-x)"
  - "app/services/xlsx_template.py — build_template, _write_text, escape_formula, freeze_zip zanjiri (02-x + 08-01)"
  - "app/services/import_validator.py — validate_staff_rows naqshi, _lookup/_fold_index (02-x, WR-05)"
  - "app/api/v1/reports.py — /revenue, /debtors, /anomalies va to'rt .xlsx eksporti (08-07, 08-12)"
  - "frontend/src/lib/report-queries.ts — uploadLedger() yo'l kontrakti (08-03)"
  - "frontend/src/lib/api-types.ts — ledgerImportResultSchema (strictObject) (08-03)"
provides:
  - "GET /api/v1/imports/template?kind=ledger — TO'RTINCHI shablon turi (AYNAN ikki ustun)"
  - "POST /api/v1/reports/compare/ledger?day= — kunlik daftar importi (STALL_MANAGE)"
  - "import_validator: validate_ledger_rows / LedgerImportRow / LEDGER_COLUMNS"
  - "report_repo: ledger_upsert (ON CONFLICT DO UPDATE) / ledger_day / LedgerDay / LedgerDayRow"
  - "schemas: LedgerImportResponse — klient strictObject kontraktiga teng"
  - "audit: TABLE_LEDGER_ENTRIES — ommaviy importning YIG'MA izi"
  - "tests/integration/test_three_way.py — 18 test (08-16 shu faylni davom ettiradi)"
affects:
  - "08-16 — three_way() ledger_day() dan o'qiydi; /reports yuzasi 8 -> 10 bo'ladi"
  - "08-18 — ledger-import.tsx shu marshrutga va uch xato kodiga ulanadi"
  - "tests/tenancy/test_route_coverage.py — yuza 7 -> 8, son test NOMIDA"
  - "tests/tenancy/test_cross_tenant.py — QUERY_PARAM_ROUTES ikkinchi a'zoni oldi"
tech-stack:
  added: []
  patterns:
    - "Tashqi manba jadvali (daftar) HOSILA taqig'i (D-03) ostiga tushmaydi — u KIRISH ma'lumoti"
    - "Upsertning `xmax = 0` RETURNING i — almashtirilgan qatorlarni ikkinchi SELECTsiz sanash"
    - "Yig'ma audit yozuvi DB triggeri bilan BIRGA yashaydi: ikki qatlam, ikki savol"
    - "Yangi `ImportIssue` kodi = uch tilli tarjima (mexanik darvoza, ixtiyoriy emas)"
    - "Marshrut metodlari per-route XARITADA, umumiy «hammasi GET» da'vosida emas"
key-files:
  created:
    - tests/integration/test_three_way.py
  modified:
    - services/core-api/app/services/xlsx_template.py
    - services/core-api/app/services/import_validator.py
    - services/core-api/app/repositories/report_repo.py
    - services/core-api/app/api/v1/imports.py
    - services/core-api/app/api/v1/reports.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/unit/test_xlsx_template.py
    - tests/unit/test_import_validator.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_cross_tenant.py
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json
key-decisions:
  - "Marshrut nomi KLIENT KONTRAKTIDAN: POST /reports/compare/ledger — reja aytgan /three-way/ledger EMAS (08-12 ning aynan qarori)"
  - "validate_ledger_rows `stalls_by_code` (Mapping) oladi, reja aytgan `known_stall_codes` (to'plam) EMAS — WR-05 registrsiz dublikatini ushlash uchun"
  - "«30 qatorli import = 1 audit qatori» da'vosi IKKI QATLAMGA bo'lindi: yig'ma (app) 1 ta, qator (db_trigger) 30 ta — 08-02 triggerini o'chirmasdan"
  - "Uch yangi ImportIssue kodi frontend messages'iga uch tilda qo'shildi — error-codes.test.mjs darvozasi buni MAJBURLAYDI"
  - "Razryad ajratgichi (150 000, U+00A0 bilan ham) QABUL QILINADI — all-or-nothing tufayli bitta katak 300 qatorni qaytarardi"
  - "amount uchun yuqori chegara MAX_SAFE_SOUM — usiz 30 xonali son BIGINT da 22003 va foydalanuvchida 500 berardi"
  - "`day` MAJBURIY: standart kun faylni jimgina noto'g'ri kunga yozardi"
patterns-established:
  - "Shablon turining qo'shilishi UCH reyestrni birga yangilaydi va u alohida test bilan qulflanadi"
  - "Sabotaj yozuv yo'lida ham o'lchanadi: validator o'chirilganda 422 emas, 200 + qisman yozuv keladi"
requirements-completed: [RECON-04]
duration: 78min
completed: 2026-08-16
---

# Phase 8 Plan 14: Daftar importi Summary

**Qog'oz daftar `.xlsx` bo'lib tizimga kiradi: to'rtinchi shablon turi (AYNAN
ikki ustun), `0` summani qonuniy deb biladigan validator, `ON CONFLICT DO
UPDATE` bilan idempotent yozuv va bitta ommaviy amal uchun bitta yig'ma
audit izi — hammasi 2-fazaning MAVJUD import quvuri ustida.**

## Performance

- **Duration:** ~78 daqiqa (16:49 → 18:07, o'lchov yugurishlari bilan)
- **Tasks:** 3 (hammasi TDD)
- **Files modified:** 14 + 1 yangi

## Nima qilindi

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | To'rtinchi shablon turi + ONGLI darvoza yangilanishi | `1265052` (RED) → `1b62ecd` (GREEN) |
| 2 | `validate_ledger_rows` + `ledger_upsert`/`ledger_day` | `74d5dd4` (RED) → `b303e15` (GREEN) |
| 3 | `POST /reports/compare/ledger` + integratsiya testlari | `f356b83` (mahsulot) → `2b677b9` (testlar + darvozalar) |

## ⛔ ENG QIMMAT BAND: REJANING IKKI DA'VOSI MERGE'DAN KEYIN ESKIRGAN EDI

### 1. Marshrut nomi — `/compare/ledger`, `/three-way/ledger` EMAS

`frontend/src/lib/report-queries.ts::uploadLedger()` (08-03, TO'LQIN 1)
AYNAN `${REPORTS_PATH}/compare/ledger?day=` ga boradi va u allaqachon
jo'natilgan. Bu 08-07 (`/debtors`) va 08-12 (`/debtors.xlsx`) da qabul
qilingan qarorning **uchinchi takrori**: SERVER KLIENTNI KUZATADI.

⚠ Nosozlik JIMGINA bo'lardi: 08-18 ning komponent testlari mock bilan
yashil qolardi va 404 faqat jonli ekranda ko'rinardi.

⛔ **08-16 uchun ogohlantirish:** o'sha rejaning matni ham `/three-way`
va `/three-way.xlsx` deydi, klient esa `/compare` va `/compare.xlsx`
dan yuradi (`report-queries.ts:253`, `:383`).

### 2. «30 qatorli import = 1 audit qatori» — 08-02 dan keyin yolg'on

`ledger_entries` `AUDITED_TABLES` da (08-02 qarori), ya'ni `0024` unga
`fn_audit_row()` triggerini ULAGAN. 30 qatorli import shu sababdan **31**
qator yozadi va bu TO'G'RI. Reja bandini so'zma-so'z bajarish triggerni
o'chirishni talab qilardi — ya'ni «qaysi rastaga qancha yozildi?»
savolini jurnaldan butunlay o'chirib yuborardi.

Yechim — da'voni **ikki qatlamga** bo'lish va IKKALASINI ham o'lchash:

| Qatlam | `source` | Savol | O'lchandi |
|---|---|---|---|
| Yig'ma | `app` | «bular BITTA ommaviy amaldan» (T-02-180) | **AYNAN 1** |
| Qator | `db_trigger` | «qaysi rasta, qancha summa» | **AYNAN 30** |

Faqat birinchisini o'lchash `0024` ning triggeri o'chib qolganini
KO'RMASDI.

## ⛔ SABOTAJ NATIJASI — O'LCHANDI, JIM O'TMADI

Reja majburiy sabotajni buyurgan: validatorning xato qaytarish yo'li
o'chirilsin (`return accepted, []`) va (b) testi qizarishi o'lchansin.

**NATIJA — test QIZARDI, xabar LITERAL:**

```
E  AssertionError: {"day":"2026-08-16","rows":2,"replaced":false}
E  assert 200 == 422
E   +  where 200 = <Response [200 OK]>.status_code
```

⛔ **Topilma da'vodan kuchliroq chiqdi:** sabotaj ostida javob 422 emas,
**200** keldi va **ikki qator BAZAGA YOZILDI** — ya'ni yaroqsiz qator
JIMGINA tashlab yuborilib, fayl «muvaffaqiyatli» bo'lib ko'rindi. Bu
aynan T-08-61 («qisman yozilgan import») ning ko'rinishi va u
all-or-nothing HAQIQATAN validatorga tayanayotganini isbotlaydi. Shu
sababdan testda status kodi bilan birga **SANOQ** ham tekshiriladi
(`ledger_count(...) == before == 0`).

Fayl `git checkout -- services/core-api/app/services/import_validator.py`
bilan tiklandi va test qayta YASHIL.

## ⛔ IKKINCHI O'LCHOV: MARSHRUT QO'SHILISHI UCH DARVOZANI QIZARTIRDI

Marshrut yozilgandan keyin (darvozalar YANGILANISHIDAN OLDIN) butun
`tests/tenancy` yugurtirildi. Natija — AYNAN uch qizil:

```
FAILED tests/tenancy/test_cross_tenant.py::test_no_matrix_route_returns_422[POST_/api/v1/reports/compare/ledger]
FAILED tests/tenancy/test_route_coverage.py::test_the_reports_surface_is_exactly_seven_routes
FAILED tests/tenancy/test_route_coverage.py::test_every_reports_route_is_documented_in_openapi
```

Ya'ni yopiq to'plam darvozalari yangi yuzani **o'zi topdi**. Uchalasi ham
ONGLI yangilandi:

- `test_..._is_exactly_seven_routes` → `..._eight_routes` (**NOM bilan
  birga**, R-11 qoidasi) va metodlar endi `REPORTS_ROUTE_METHODS`
  xaritasidan tekshiriladi — «hammasi `GET`» jumlasini «`GET` yoki
  `POST`» ga yumshatish ikkinchi yozuv marshrutini jimgina o'tkazardi.
  Qo'shimcha assert: yozuv marshruti **AYNAN BITTA**;
- OpenAPI sanog'i 7 → 8;
- `QUERY_PARAM_ROUTES` ga bitta a'zo qo'shildi va u `test_only_the_ledger_
  import_needs_a_query_param_exemption` da **to'plam tengligi** bilan
  qulflandi (`exempted == ["POST_/api/v1/reports/compare/ledger"]`).

⛔ **`FILE_FILLERS` ga yozish YETMASDI va u ZARARLI bo'lardi:**
`test_file_routes_actually_execute` o'sha xaritadan iteratsiya qiladi va
`?day=` siz chaqiruv baribir 422 berardi — ro'yxatga qo'shilgan yozuv
hech nimani ushlab turmasdan darvozani QIZIL qilib qo'yardi. Marshrutning
tenant chegarasi shu sababdan `test_three_way.py` da, HAQIQIY parametrlar
bilan o'lchanadi.

## Task 1 — to'rtinchi shablon turi

- `TEMPLATE_KINDS` uchtadan **to'rttaga**: `("stalls", "vendors", "staff", "ledger")`;
- `test_template_kinds_are_exactly_three` → `..._four` — **NOMI BILAN
  BIRGA** (grep: `..._four` → 1, `..._three` → 0);
- ustunlar **AYNAN IKKITA** (`rasta kodi` · `daftar summasi`) va uchinchi
  ustunning yo'qligi `header[2] is None` bilan o'lchanadi — faqat ikki
  sarlavhani tekshirish uchinchisi qo'shilganda ham yashil qolardi;
- huquq `STALL_MANAGE` va sabab `imports._TEMPLATE_PERMISSIONS`
  docstringida LITERAL;
- yangi test `test_the_three_template_registries_stay_in_sync` uch
  reyestrni (`TEMPLATE_KINDS` ↔ `ImportKind` ↔ `_TEMPLATE_PERMISSIONS`)
  to'plam tengligi bilan bog'laydi — ajralgan holat `KeyError` bilan
  **500** berardi (422 emas);
- shablon baytlari determinik (08-01 ning `freeze_zip` zanjiri) —
  `test_two_builds_are_byte_identical[ledger-template]`.

## Task 2 — validator va idempotent yozuv

| Qoida | Qayerda LITERAL |
|---|---|
| `0` summa QONUNIY (`FINANCIAL_TABLES` da yo'q) | `validate_ledger_rows` docstringi, 1-blok |
| Bo'sh katak `0` EMAS → `row_too_short` | o'sha docstring + alohida test |
| Kasr/manfiy → `ledger_amount_invalid` | `_ledger_amount()` |
| Dublikat YECHILGAN `stall_id` bo'yicha | `stall_first_seen` docstringi (WR-05) |
| `DO UPDATE`, `DO NOTHING` EMAS | `_LEDGER_UPSERT` docstringi, 1-band |

`report_repo.ledger_day()` `has_ledger` ni **alohida maydon** qilib
qaytaradi (`LedgerDay`): UI-SPEC §10.6 ga ko'ra «daftar yuklanmagan» va
«daftarda qator yo'q» IKKI BOSHQA ekran holati va chaqiruvchi ro'yxat
uzunligini TALQIN QILMASLIGI kerak — talqin ikki ekranda ikki xil
yozilardi.

### `isdigit()` emas, `isdecimal()`

`"²".isdigit()` → `True`, `int("²")` esa `ValueError` — ya'ni validator
o'zi qabul qilgan qiymatda yiqilib, foydalanuvchiga 422 o'rniga **500**
berardi. Sabab funksiya docstringida yozilgan.

## Task 3 — marshrut

- uch darvoza `imports.py` dan **import qilinadi**, ko'chirilmaydi:
  `_read_bounded()` → `_read()` → `validate_ledger_rows()`;
- tranzaksiya bloki OCHILMAYDI — `grep -c "async with\|begin()\|commit()\|
  rollback\|savepoint\|transaction" reports.py` → **0**;
- 422 javobi mavjud shakldan (`_reject_if_invalid`): `detail`,
  `errors[]`, `error_counts`;
- 409 mavjud reyestrdan (`_conflict`);
- javob AYNAN klient `strictObject` iga teng: `{day, rows, replaced}`.

## Rejadan chetlanishlar

### 1. [Rule 1 — Klient kontrakti] `/compare/ledger`

- **Reja aytgan:** `POST /reports/three-way/ledger` (shu jumladan
  `must_haves.artifacts` da).
- **Yozilgan:** `POST /reports/compare/ledger`.
- **Sabab:** `report-queries.ts::uploadLedger()` (08-03) AYNAN shu yo'lga
  boradi; `reports.py` modul docstringining 2-bandi va 08-12 SUMMARY
  precedenti.
- **Fayllar:** `app/api/v1/reports.py`, `tests/tenancy/*`, `tests/integration/test_three_way.py`
- **Commit:** `f356b83`

### 2. [Rule 2 — Yetishmayotgan kritik funksiya] Validator KODLARINING uch tilli tarjimasi

- **Topildi:** Task 2, `node --test frontend/scripts/error-codes.test.mjs`.
- **Muammo:** `error-codes.test.mjs` `import_validator.py` dagi HAR
  `ImportIssue(...)` kodini uchala `messages/*.json` dagi
  `import.errors.*` bilan **to'plam tengligi** bilan solishtiradi. Uch
  yangi kod tarjimasiz qo'shilsa `npm run gate:fast` merge'dan keyin
  QIZARARDI va 08-18 ekranda «Kutilmagan xato» ko'rsatardi.
- **O'lchandi (tarjimadan OLDIN):**
  `✖ import.errors.* backend ImportIssue.code bilan BIR-BIRGA mos` —
  `uz-Latn.json da import.errors ro'yxati backend bilan mos emas`.
- **Yechim:** uch kalit `uz-Latn.json` va `ru.json` ga qo'lda,
  `uz-Cyrl.json` esa **generator bilan** (`node scripts/gen-cyrillic.mjs`
  — u fayl «qo'lda tahrirlanmaydi»).
- **Tekshirildi:** `node --test scripts/*.test.mjs` → **272 passed**;
  `gen-cyrillic.mjs --check` → «drift yo'q»; `check-messages.mjs` →
  «1351 kalit × 3 til — parity to'liq».
- **Commit:** `b303e15`

⚠ **PARALLEL IJRO QOIDASIGA NISBATAN:** topshiriq `frontend/` ga
tegmaslikni aytgan edi. Tegilgan yagona narsa — `frontend/messages/*.json`
ning `import.errors` bloki (faylning O'RTASIDA), 08-17/08-18 esa
`reports`/`compare` bloklariga (faylning OXIRIDA) tegadi va ularning
`files_modified` ida messages fayllari UMUMAN YO'Q. Muqobil (kodlarni
tarjimasiz qoldirish) fazaning darvozasini qizil holatda merge qilardi.

### 3. [Rule 1 — Hujjat kodga zid bo'lib qolardi] `main.py` izohi

- **Muammo:** `main.py:478-481` «bu prefiksda `POST`/`PATCH`/`DELETE`
  UMUMAN yozilmagan» der edi va eskirgan test nomiga
  (`..._is_exactly_three_routes`) havola qilardi. Marshrut qo'shilgach
  bu yozuv kodning xulqiga ZID bo'lib qolardi (08-02 deviatsiya #2 ning
  aynan sinfi — WR-03).
- **Yechim:** izoh haqiqatga muvofiq qayta yozildi: `PATCH`/`DELETE`
  taqig'i KUCHDA, yagona `POST` esa nomlangan sabab bilan (daftar
  hisobot EMAS) va yangi test nomiga havola bilan.
- **Commit:** `f356b83`

### 4. [Rule 2 — Xavfsizlik/to'g'rilik] `MAX_SAFE_SOUM` yuqori chegarasi

- **Muammo:** reja summaning yuqori chegarasi haqida hech nima
  demagan. 30 xonali son `BIGINT` ga sig'masdi va DB `22003` bilan
  yiqilardi — u `_CONFLICT_STATES` da YO'Q, ya'ni foydalanuvchi qator
  raqamsiz **500** olardi (JSON tomonida esa `MAX_SAFE_INTEGER` dan
  katta qiymat jimgina yaxlitlanardi — Pitfall 7).
- **Yechim:** `_ledger_amount()` `value <= MAX_SAFE_SOUM` shartini
  qo'yadi va chegaradan oshgan qiymat `ledger_amount_invalid` beradi.
- **Commit:** `b303e15`

### 5. [Reja tanlovi] `stalls_by_code`, `known_stall_codes` EMAS

Reja `validate_ledger_rows(rows, *, known_stall_codes)` degan edi —
ya'ni KODLAR to'plami. Yozilgani `stalls_by_code: Mapping[str, UUID]`
(`validate_vendor_rows` bilan AYNI shakl) va sabab WR-05: `_lookup()`
avval aniq, so'ng registrsiz moslikni ko'radi, ya'ni `A1` va `a1` BITTA
rastaga yechiladi. Dublikat qo'riqchisi XOM SATR bo'yicha kalitlanganda
ikkala qator ham o'tardi va `uq_ledger_entries_market_day_stall` `23505`
bilan yiqilardi — foydalanuvchi esa QATOR RAQAMISIZ 409 olardi.
Qo'shimcha foyda: `stall_id` validatorda yechiladi, ya'ni repozitoriy
kod bo'yicha qidirmaydi (topilmagan kod JIMGINA nol qator yozardi).

### 6. [Reja tanlovi] Razryad ajratgichi QABUL QILINADI

`150 000` (oddiy bo'sh joy), `150 000` (Excel rus lokali) va
`150 000` — uchalasi ham `150000` deb o'qiladi. Sabab
`_DATE_FORMATS` ning uch shakli bilan AYNI: all-or-nothing tufayli bitta
bunday katak 300 qatorli faylni butunlay qaytarib yuborardi. ⛔ Vergul va
nuqta ro'yxatda YO'Q — ular kasr ajratgichi ham bo'lishi mumkin va
`150000.5` ni `1500005` ga aylantirardi.

### 7. [Test tuzatishi] Dublikat testining kutilmasi

RED bosqichida dublikat testlari `accepted == []` deb yozilgan edi.
GREEN da o'lchandi: `validate_vendor_rows` konvensiyasi bo'yicha
BIRINCHI qator `accepted` da QOLADI (all-or-nothing qarorini ROUTER
qabul qiladi, validator yaroqli qatorni jazolamaydi). Test modul
konvensiyasiga keltirildi va sabab docstringda yozildi.

---

**Jami chetlanishlar:** 7 (2 × Rule 1, 2 × Rule 2, 3 × reja/test tanlovi)
**Ta'sir:** yangi paket YO'Q, yangi jadval YO'Q, migratsiya YO'Q. Barcha
chetlanishlar mavjud kontrakt yoki mexanik darvoza tomonidan MAJBURLANGAN.

## Tekshiruv natijalari — HAQIQIY o'lchov (2026-08-16, Docker 29.4.2)

| O'lchov | Natija |
|---|---|
| `pytest tests/unit tests/integration/test_three_way.py` | **EXIT 0 — 1317 passed (49.7 s)** |
| `pytest tests/tenancy` | **EXIT 0 — 787 passed** (collect-only bilan tasdiqlandi) |
| `pytest tests/tenancy + staff_import + stall_import + karmana_scale + reports_api` | **EXIT 0 — 896 passed (897 s)** |
| `pytest tests/integration/test_three_way.py` | **EXIT 0 — 18 passed** |
| `ruff check .` / `ruff format --check .` | **All checks passed / 369 fayl** |
| `mypy .` | **Success: 356 fayl, xato yo'q** |
| `node --test frontend/scripts/*.test.mjs` | **272 passed, 0 fail** |
| `node scripts/gen-cyrillic.mjs --check` | **«drift yo'q»** |
| `node scripts/check-messages.mjs` | **1351 kalit × 3 til, parity to'liq** |

⚠ Buyruqlar `--no-deps` bilan olindi (08-04 `deferred-items.md` №3 da
o'rnatilgan qoida): bu worktree xost bilan AYNI compose loyihasini baham
ko'radi va `--no-deps` siz chaqiruv ishlab turgan xost stekini qayta
yaratardi. Qamrov ayni — `tests` konteyneri Postgres'ni `testcontainers`
bilan O'ZI ko'taradi.

⚠ `npm run gate:fast` TO'LIQ bajarilmadi: `frontend/node_modules` bu
worktree'da yo'q (08-12 da ham shunday edi). Lekin `scripts/*.test.mjs`
va `i18n` darvozalari **npm bog'liqliksiz** (`node:test`, `node:fs`)
yugurdi va ular aynan shu rejaning frontend ta'sirini qamraydi.
**Egasi:** orkestrator (merge'dan keyin to'liq `gate:fast`).

## Qabul mezonlari — bandma-band dalil

### Task 1

| Mezon | Holat | Dalil |
|---|---|---|
| `TEMPLATE_KINDS` AYNAN to'rtta | ✅ | `test_template_kinds_are_exactly_four` |
| Uch reyestr sinxron | ✅ | `test_the_three_template_registries_stay_in_sync` (to'plam tengligi) |
| `_TEMPLATE_PERMISSIONS["ledger"]` = `STALL_MANAGE` | ✅ | `test_the_ledger_template_sits_behind_stall_manage` + integratsiyada 403/200 |
| `grep -c "..._four"` → 1, `"..._three"` → 0 | ✅ | o'lchandi: `1` va `0` |
| `pytest tests/unit/test_xlsx_template.py` EXIT 0 | ✅ | 54 passed |

### Task 2

| Mezon | Holat | Dalil |
|---|---|---|
| `validate_ledger_rows` bor | ✅ | `grep -c 'def validate_ledger_rows'` → `1` |
| `0` summa uchun xato YO'Q | ✅ | `test_zero_is_a_legal_ledger_amount` + uchidan-uchiga `test_zero_survives_the_whole_chain` |
| `ledger_upsert` va `ledger_day` bor | ✅ | `grep -c 'async def ledger_upsert\|async def ledger_day'` → `2` |
| SQL da `DO UPDATE` bor, `DO NOTHING` YO'Q | ✅ (grep ⚠ **2**) | `DO UPDATE` → `3`; `DO NOTHING` ning ikkala moslik ham **DOCSTRINGDA** (`:880`, `:886`) — ular taqiqning O'Z SABABINI yozadi va SQL matnida `DO NOTHING` YO'Q. Bu 08-02/08-12 da o'lchangan «grep-ning o'z-o'ziga qarshiligi» sinfi |
| `grep -c "float" import_validator.py` o'zgarmagan | ✅ | `0` (oldin ham `0`) |
| `pytest tests/unit/test_import_validator.py` EXIT 0 | ✅ | 14 passed |

### Task 3

| Mezon | Holat | Dalil |
|---|---|---|
| Marshrut mavjud va `STALL_MANAGE` talab qiladi | ✅ | `test_the_cashier_cannot_upload_a_ledger`, `test_the_director_cannot_upload_a_ledger` |
| `reports.py` da tranzaksiya atamalari 0 marta | ✅ | o'lchandi: `0` |
| 30 qatorli import 1 ta yig'ma audit qatori | ✅ | `test_one_bulk_import_writes_exactly_one_aggregate_audit_row` (+ trigger 30) |
| Ikkinchi import qator sonini oshirmaydi | ✅ | `test_the_second_file_replaces_instead_of_adding` (+ nazorat: BOSHQA kun QO'SHADI) |
| `pytest tests/integration/test_three_way.py -k ledger` EXIT 0 | ✅ (⚠ butun fayl) | Fayldagi HAMMA test daftar importi haqida, ya'ni `-k ledger` filtri faqat 5 tasini tanlardi va qolgan 13 dalilni chetlab o'tardi. **To'liq fayl** yugurtirildi: 18 passed |
| Sabotaj natijasi SUMMARY da | ✅ | yuqoridagi bo'lim (literal xabar bilan) |

### Reja darajasidagi `success_criteria`

| Mezon | Holat |
|---|---|
| To'rtinchi shablon turi + darvoza NOMI bilan yangilangan | ✅ |
| Validator `0` ni ruxsat etadi, sabab kodda | ✅ |
| `POST .../ledger` uch darvozadan o'tadi, all-or-nothing va idempotent | ✅ |
| Bitta import = bitta yig'ma audit yozuvi (o'lchangan) | ✅ (+ trigger qatlami ham o'lchandi) |
| Sabotaj o'lchangan | ✅ |

## Xavfsizlik — `<threat_model>` bandlari

| Threat | Bajarilishi |
|---|---|
| T-08-58 (ZIP/XML bomba, ulkan fayl) | MAVJUD quvur qayta ishlatildi (`_read_bounded` → `_read`); `test_a_file_that_is_not_xlsx_never_reaches_the_validator` birinchi darvozani KOD bilan o'lchaydi |
| T-08-59 (kassir daftar yuklashi) | `STALL_MANAGE`; kassir **va** direktor 403 — ikkalasi ham alohida test |
| T-08-60 (cross-tenant daftar yozuvi) | Rasta lug'ati tenant sessiyasidan; kompozit FK (0024); `test_the_other_markets_admin_cannot_write_into_market_a` + nazorat testi |
| T-08-61 (qisman yozilgan import) | `TenantSessionDep` tranzaksiyasi + `_reject_if_invalid`; **sabotaj bilan o'lchandi** (200 + 2 qator) |
| T-08-62 (ommaviy amalning jurnalda yo'qolishi) | Yig'ma `write_app_audit`; 30 qatorda AYNAN 1; rad etilgan import IZ QOLDIRMAYDI (alohida test) |
| T-08-63 (shablonda formula injection) | `build_template` → `_write_text`/`escape_formula`; namunaviy summa `-`/`+` SIZ (`test_ledger_sample_row_carries_no_formula_prefix`) |
| T-08-SC (pip o'rnatish) | ⛔ **Birorta paket o'rnatilmadi** — `pyproject.toml` / `uv.lock` / `package.json` TEGILMADI |

## Known Stubs

Yo'q. Marshrut HAQIQIY jadvalga yozadi, validator HAQIQIY rasta
reyestridan o'qiydi, `ledger_day()` esa 08-16 uchun tayyor. To'qilgan
qiymat, bo'sh ro'yxat konstantasi yoki «hozircha mavjud emas» matni
qo'shilmadi.

⚠ `ledger_day().has_ledger` bugungi kunda qatorlar mavjudligidan HOSILA
va bu **stub emas, nomlangan qaror**: import hodisasining O'Z jadvali
YO'Q (08-02 ATAYIN faqat `ledger_entries` ni tug'dirgan). Oqibati
`LedgerDay` docstringida literal yozilgan — «daftar bor, lekin qator
yo'q» holati bugun YUZAGA KELMAYDI.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-write-endpoint | `services/core-api/app/api/v1/reports.py` | `/reports` prefiksidagi BIRINCHI yozuv marshruti. Reja `<threat_model>` ida nomlangan (T-08-59/60/61/62) va uch mustaqil darvoza bilan qulflangan: yuza yopiq to'plami + metod xaritasi (`test_route_coverage`), cross-tenant matritsasi (`test_cross_tenant`) va rol matritsasi (`test_three_way`). Reyestrdan tashqarida qolgan yuza yo'q |

## Ochiq qolgan bandlar

- ⚠ **`ledger_day_locked` klient kodi hali SERVERDA YO'Q.**
  `report-errors.ts::REPORT_ERROR_CODES` (08-03) `ledger_day_locked`
  («kun yopilgan») ni e'lon qilgan va `SERVER_CODE_MAP` unga `day_locked`
  ni bog'lagan, lekin bu reja `day` ga birorta ma'muriy chegara
  QO'YMAYDI (reja ham so'ramagan). Chegarani taxmin qilib qo'yish
  klientni buzardi: kun ustidagi qoida (kecha? bozor yopiq kunmi?)
  solishtiruvning O'ZI bilan birga aniqlanadi. **Egasi:** 08-16
  (`GET /compare?day=` ning egasi).
- ⚠ **Daftar shabloni namunaviy qatorida rasta kodi `"1"`.** A bozorining
  seed kodlari orasida `1` yo'q, ya'ni shablonni O'ZGARTIRMASDAN import
  qilish `ledger_stall_unknown` beradi. Bu `vendors` shabloni bilan AYNI
  xulq (u ham `"1"` yozadi) va u yerda ham shunday qolgan — yagona
  to'g'ri yechim namunani HAQIQIY rasta kodi bilan to'ldirish bo'lardi
  (`_sample_row` ga rasta ro'yxatini uzatish), ya'ni `build_template`
  imzosi o'zgarishi kerak. **Egasi:** 08-18 (ekranda namunani
  tushuntiruvchi matn) yoki alohida band.
- ⚠ **Rus tilidagi atama drifti** — `deferred-items.md` №7 (backend
  shablon sarlavhasi «прилавок», ekran copy'si «место»; glossariy
  darvozasi backendni qamramaydi).

## Keyingi reja uchun

- **08-16:** `three_way()` `report_repo.ledger_day()` dan o'qisin —
  `has_ledger` ALOHIDA maydon, ro'yxat uzunligidan talqin QILINMASIN
  (UI-SPEC §10.6). Marshrut nomlari ⛔ **`/compare` va `/compare.xlsx`**
  (reja `/three-way` deydi, klient esa `report-queries.ts:253,383` da
  `/compare` dan yuradi). `/reports` yuzasi 8 → 10 bo'ladi va test NOMI
  (`..._eight_routes`) hamda `REPORTS_ROUTE_METHODS` xaritasi QO'LDA
  yangilanadi; `compare.xlsx` `BINARY_PERSONAL_ROUTES`/
  `NON_PERSONAL_BINARY_ROUTES` dan BIRIGA yozilishi SHART (aks holda
  `KeyError` — bu ATAYIN).
- **08-18:** `uploadLedger()` allaqachon to'g'ri yo'lga boradi va
  javob shakli (`{day, rows, replaced}`) `strictObject` bilan MOS.
  422 javobidagi per-qator kodlar (`ledger_stall_unknown`,
  `ledger_amount_invalid`, `ledger_duplicate_stall`) uchala tilda
  ALLAQACHON tarjimalangan (`import.errors.*`).
- Yangi `ImportIssue` kodi qo'shadigan HAR KIM uchun: kod va tarjima
  BITTA commitda ketadi — `error-codes.test.mjs` ularni to'plam tengligi
  bilan bog'laydi va `uz-Cyrl.json` GENERATOR bilan yangilanadi.

## Self-Check: PASSED

- `.planning/phases/08-.../08-14-SUMMARY.md` — FOUND
- `services/core-api/app/services/xlsx_template.py` — FOUND
- `services/core-api/app/services/import_validator.py` — FOUND
- `services/core-api/app/repositories/report_repo.py` — FOUND
- `services/core-api/app/api/v1/reports.py` — FOUND
- `services/core-api/app/api/v1/imports.py` — FOUND
- `services/core-api/app/security/audit.py` — FOUND
- `services/core-api/app/schemas.py` — FOUND
- `services/core-api/app/main.py` — FOUND
- `tests/integration/test_three_way.py` — FOUND
- `tests/unit/test_xlsx_template.py`, `tests/unit/test_import_validator.py` — FOUND
- `tests/tenancy/test_route_coverage.py`, `tests/tenancy/test_cross_tenant.py` — FOUND
- `frontend/messages/{uz-Latn,uz-Cyrl,ru}.json` — FOUND
- Commitlar `git log` da FOUND: `1265052`, `1b62ecd`, `74d5dd4`,
  `b303e15`, `f356b83`, `2b677b9`
- Sabotajdan keyin ishchi daraxt toza (`git status --short` da faqat
  SUMMARY va `deferred-items.md`)
- ⛔ `STATE.md` va `ROADMAP.md` **TEGILMADI** (parallel ijro qoidasi —
  ularni orkestrator to'lqin tugagach yozadi)

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
