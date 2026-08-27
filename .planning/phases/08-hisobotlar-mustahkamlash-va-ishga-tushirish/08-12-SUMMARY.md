---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 12
subsystem: backend-xlsx-eksport-va-bayt-tasnif-darvozasi
tags: [RECON-04, RECON-05, D-05, D-06, D-09, D-10, D-11, R-3, Pattern-2, Pattern-3, Pitfall-2, T-08-48, T-08-49, T-08-50, T-08-51, T-08-52, T-08-53]
requires:
  - "app/services/xlsx_export.py — new_workbook/write_text/write_money/write_optional_text/finish (08-01)"
  - "app/api/v1/reports.py — /revenue, /debtors, /anomalies va _report_period() (08-07)"
  - "app/api/v1/imports.py — _xlsx_response(), _locale_of(), XLSX_SUFFIX (02-x)"
  - "app/services/accuracy_report.py — accuracy_report(), ConfusionMatrix, measured bayrog'i (05-12)"
  - "app/repositories/occupancy_repo.py — OccupancyRepository.accuracy_rows()"
  - "app/repositories/market_repo.py — MarketRepository.current_market() (fayl nomi uchun)"
  - "frontend/src/lib/report-queries.ts — buildReportPath() (08-03, yo'l kontraktining langari)"
provides:
  - "GET /api/v1/reports/revenue.xlsx — davr tushumi hujjati"
  - "GET /api/v1/reports/debtors.xlsx — qarzdorlik reestri (audit_read: report_receivables_export)"
  - "GET /api/v1/reports/anomalies.xlsx — nomuvofiqlik arxivi (dalil IDENTIFIKATOR)"
  - "GET /api/v1/reports/accuracy.xlsx — AI aniqlik hisoboti (MAVJUD accuracy_report() dan)"
  - "xlsx_export: build_revenue/receivables/discrepancies/accuracy_workbook, ReportPeriod, report_texts()"
  - "xlsx_export: write_optional_number / write_header / layout_sheet (varaqqa tegish yuzasi)"
  - "tests/tenancy: BINARY_PERSONAL_ALLOWED — per-route ruxsat XARITASI"
affects:
  - "tests/tenancy/test_route_coverage.py — /reports yuzasi 3 -> 7 (yopiq to'plam, son test NOMIDA)"
  - "tests/tenancy/test_personal_data_coverage.py — bayt-tasnif darvozasi kengaydi, EVIDENCE_FRAME_ALLOWED TEGILMADI"
  - "08-16 — solishtiruv eksporti shu xaritaga qo'shiladi"
  - "08-17 — frontend eksport tugmalari shu to'rt marshrutga ulanadi"
tech-stack:
  added: []
  patterns:
    - "Eksport marshruti HAR DOIM `GET` — `POST` bayt-tasnif darvozasidan jimgina chetlab o'tardi"
    - "Fayl nomi SERVERDA quriladi va ASCII (kirill -> lotin translit, tashlab yuborish EMAS)"
    - "Qator o'giruvchi ekran va fayl uchun BITTA joyda — arifmetika ikkilanmaydi"
    - "Bayt-marshrut huquqlari per-route XARITADA, umumiy to'plamda emas"
    - "Yolg'on tasnif mahsulot kodidagi e'londan (VENDOR_VIEW / audit) mexanik langar oladi"
key-files:
  created: []
  modified:
    - services/core-api/app/services/xlsx_export.py
    - services/core-api/app/api/v1/reports.py
    - tests/unit/test_xlsx_export.py
    - tests/integration/test_reports_api.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_personal_data_coverage.py
decisions:
  - "Marshrut nomlari KLIENT KONTRAKTIDAN: /debtors.xlsx va /anomalies.xlsx — reja aytgan /receivables.xlsx, /discrepancies.xlsx EMAS (08-07 ning aynan qarori, buildReportPath() reyestrdan quradi)"
  - "freeze_panes(2, 0) — reja aytgan freeze_panes(1, 0) EMAS: AYNI reja davrni 1-qatorga qo'ygan, ya'ni `1` bilan sarlavha skrollda yo'qolardi"
  - "Eksport audit `reason` i JSON nikidan FARQ QILADI (report_receivables_export): fayl tizimdan CHIQIB ketadi va bu ekranda ko'rishdan jiddiyroq hodisa"
  - "Kirill nomlar TASHLAB YUBORILMAYDI, LOTINGA o'giriladi — aks holda har kirill nomli bozor AYNAN bir xil fayl nomini olardi"
  - "Aniqlikning JSON marshruti /reports ga KO'CHIRILMADI: u GET /occupancy/accuracy da qoladi, eksport esa AYNI xizmatni chaqiradi"
  - "Revenue/receivables hujjatlarida YIG'INDI QATORI yo'q — filtrlanadigan varaqdagi yig'indi qatori saralashda ma'lumot qatori bo'lib ko'chib yurardi; pul SON, ya'ni Excel o'zi yig'adi"
  - "Nomuvofiqlik hujjatida amount_soum ustuni YO'Q — JSON yuzasi bilan tenglik saqlandi, yangi maydon yangi yuza bo'lardi"
  - "SABOTAJ TOPILMASI: yolg'on «nomashaxsiy» tasnif JIM edi -> yangi mexanik darvoza QO'SHILDI (test emas, HOLAT tuzatildi)"
requirements: [RECON-04, RECON-05]
metrics:
  duration: "123 min"
  tasks: 3
  files: 6
  completed: 2026-08-16
---

# Phase 8 Plan 12: `.xlsx` eksport marshrutlari va bayt-tasnif darvozasi Summary

To'rtala hisobot bitta bosishda `.xlsx` bo'lib yuklab olinadi (`GET`,
sahifalanmagan, bayt-determinik), fayl nomini **server** quradi va u
kirill nomli bozorda ham ASCII qoladi; bayt-marshrut tasnif darvozasi esa
**per-route ruxsat xaritasiga** kengaydi — `EVIDENCE_FRAME_ALLOWED` ga
bitta ham huquq qo'shilmadi.

## Nima qilindi

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | To'rt workbook quruvchisi (TDD: RED -> GREEN) | `0818745`, `ee957c3` |
| 2 | To'rt `GET` eksport marshruti + fayl nomi (TDD: RED -> GREEN) | `d4e7b6a`, `71accab` |
| 3 | Bayt-tasnif darvozasi — per-route xarita | `6210366` |
| 3+ | **Sabotaj topilmasi bo'yicha yangi darvoza** | `a987580` |

## ⛔ ENG QIMMAT BAND: DARVOZA KENGAYDI, BO'SHAMADI

Reja uchta xato yo'lni oldindan nomlagan edi va **uchalasi ham
o'lchandi** (pastdagi sabotaj bo'limi). Yozilgan yechim — per-route
xarita:

```python
BINARY_PERSONAL_ALLOWED: dict[str, frozenset[Permission]] = {
    "/api/v1/snapshots/{snapshot_id}/image": EVIDENCE_FRAME_ALLOWED,
    "/api/v1/reports/debtors.xlsx": frozenset({REPORT_VIEW, VENDOR_VIEW}),
}
```

- shart `granted <= EVIDENCE_FRAME_ALLOWED` dan
  `granted <= BINARY_PERSONAL_ALLOWED[path]` ga o'tdi;
- indekslash **to'g'ridan-to'g'ri**, `.get()` yo'q
  (`grep -c "BINARY_PERSONAL_ALLOWED.get(" -> 0`);
- ikki lug'atning kalitlari tengligi **alohida** testda
  (`test_the_two_binary_personal_registries_have_identical_keys`) va u
  `KeyError` dan **oldin** turib sababni aniq aytadi;
- `EVIDENCE_FRAME_ALLOWED` (`test_personal_data_coverage.py:540`) hamon
  AYNAN `{CAMERA_VIEW, OCCUPANCY_REVIEW}`, `SNAPSHOT_EVIDENCE_FRAME_ROUTES`
  (`:612`) hamon bitta elementli — va **ikkalasining o'zgarmagani endi
  alohida test bilan o'lchanadi**.

## ⛔ TOPILMA: SABOTAJ JIM O'TDI — TUZATISH TESTDA EMAS, HOLATDA EDI

Reja majburiy uch sabotajni buyurgan. Natijalar (haqiqiy yugurish,
Docker 29.4.2):

| # | Sabotaj | Kutilgan | O'LCHANGAN |
|---|---------|----------|------------|
| 1a | `debtors.xlsx` **faqat** `BINARY_PERSONAL_ROUTES` dan `NON_PERSONAL_BINARY_ROUTES` ga | qizarish | ✅ **1 FAILED** — `..._registries_have_identical_keys` (`faqat xaritada ['/api/v1/reports/debtors.xlsx']`) |
| 1b | `debtors.xlsx` **IKKALA** reyestrdan ham `NON_PERSONAL` ga | qizarish | ❌ **QIZARMADI** — butun `tests/tenancy` **854 passed** |
| 2 | Kalit `BINARY_PERSONAL_ALLOWED` dan o'chirildi | baland ovozli `KeyError` | ✅ **2 FAILED** — kalit-tengligi testi + `KeyError: '/api/v1/reports/debtors.xlsx'` |
| 3 | `EVIDENCE_FRAME_ALLOWED` ga `REPORT_VIEW` qo'shildi | qizarish | ✅ **1 FAILED** — `..._stayed_exactly_as_05_15_left_it` (`Extra items in the right set: REPORT_VIEW`) |

**1b — bu rejaning eng muhim topilmasi.** Marshrutni ikkala reyestrdan
ham «nomashaxsiy» deb e'lon qilganda `audit_read` talabi **jimgina**
yo'qoldi va butun tenancy to'plami yashil qoldi. Ya'ni yagona to'siq
`NON_PERSONAL_BINARY_ROUTES` ga yozilgan izohning **rostligi** — inson
intizomi — edi.

Reja bu holat uchun aniq ko'rsatma bergan (05-15 S-D darsi: «sabotaj
yetib borsa ham hech nima qizarmasa, tuzatish testda emas — HOLATDA»),
shuning uchun **yangi darvoza qo'shildi**:

`test_no_non_personal_claim_survives_a_vendor_data_guard` — nomashaxsiy
deb atalgan bayt-marshrut `VENDOR_VIEW` huquqini ham, `vendors` o'qish
auditini ham e'lon qila olmaydi. Langar **mahsulot kodida**
(`api/v1/reports.py` dagi `VendorFieldGuardDep` va
`ReceivablesExportIntentDep`), ya'ni test o'zining ro'yxatidan mustaqil
dalilga tayanadi.

Qo'shilgandan keyin 1b **qayta o'lchandi**:

```
E  AssertionError: /api/v1/reports/debtors.xlsx «shaxsiy ma'lumot YO'Q» deb
   tasniflangan, lekin `VENDOR_VIEW` darvozasini ko'taradi ...
   assert <Permission.VENDOR_VIEW: 'vendor_view'> not in
       [<Permission.REPORT_VIEW: 'report_view'>, <Permission.VENDOR_VIEW: 'vendor_view'>]
FAILED test_no_non_personal_claim_survives_a_vendor_data_guard
```

⚠ **3-sabotaj ham xuddi shu narsani isbotladi, faqat teskari tomondan:**
u AYNAN BITTA testni qizartirdi va o'sha test **shu rejada qo'shilgan**.
Ya'ni bu reja bo'lmaganda `EVIDENCE_FRAME_ALLOWED` ni kengaytirish
butunlay jim o'tardi — dalil-kadr marshruti direktorga (unda
`REPORT_VIEW` bor) ochilardi va 05-15 ning ishi bekor bo'lardi.

Har sabotajdan keyin fayl `git checkout -- <fayl>` bilan tiklandi.

## Task 1 — to'rt workbook quruvchisi

`xlsx_export.py` ga to'rt `build_*_workbook(dto, locale, period) -> bytes`
qo'shildi. Umumiy qoidalar kodda **literal** yozilgan:

| Qoida | Qayerda |
|---|---|
| Davr **fayl ichida**, 1-qatorda `Davr: {from} — {to}` | `_open_report()`, `ReportPeriod.label` |
| Matn faqat `write_text()` orqali | `ast` darvozasi (pastda) |
| Pul — SON, **butun so'm** | `write_money` + `MONEY_NUM_FORMAT` |
| O'lchanmagan qiymat — **BO'SH katak** | `write_optional_text` / `write_optional_number` |
| Rasm YO'Q — faqat `snapshot_id` | `build_discrepancies_workbook` |
| Uch tilli sarlavha SERVERDA | `_REPORT_TEXTS` (`xlsx_template._TEXTS` naqshi) |

Aniqlik hujjatining ikki qat'iy bandi:

- **ikki xato turi ALOHIDA qatorda** — «Band deb xato ulushi» va «Bo'sh
  deb xato ulushi»; qiymatlar `AccuracyReport` dan **ko'chiriladi**,
  qayta hisoblanmaydi. Test buni yumaloq bo'lmagan sonlar bilan
  o'lchaydi (`0.05424528301886792`, `0.08656036446469248`);
- **AI-02 holati jumlasi shartsiz** — `measured` ning ikkala holatida
  ham. Matn ekrandagi bilan **ayni** (`reports.accuracyDisclaimer`).

### `ast` darvozasi kengaydi, bo'shashmadi

08-01 ning `test_raw_worksheet_writes_live_only_inside_write_text` i
`worksheet.*` chaqiruvini AYNAN uch funksiyaga qulflagan edi. To'rt
quruvchi varaqqa **umuman xom tegmaydi**; o'rniga ikki yangi yordamchi
ro'yxatga qo'shildi:

```
write_text            -> [write_string]
write_money           -> [write_number]
write_optional_text   -> [write_blank]
write_optional_number -> [write_blank, write_number]   # 08-12
layout_sheet          -> [autofilter, freeze_panes, set_column]   # 08-12
```

Ya'ni «kim varaqqa tegishi mumkin?» savoli hamon **yopiq to'plam** bilan
javob oladi va quruvchining o'zi ro'yxatda paydo bo'lsa test qizaradi.

## Task 2 — to'rt `GET` eksport marshruti

`/revenue.xlsx`, `/debtors.xlsx`, `/anomalies.xlsx`, `/accuracy.xlsx` —
**hammasi `GET`** (`grep -c "@router.post" -> 0`). Sabab kodda literal:
`POST` bo'lganda marshrut `get_routes()` (faqat `GET`) dan chiqib
ketardi, ya'ni yopiqlik testi uni umuman ko'rmasdi.

- javob `_xlsx_response(payload, filename)` bilan — `imports.py` dan
  **import**, ko'chirma emas;
- til `_locale_of()` bilan **profildan**, so'rov parametridan emas;
- fayl nomi `{bozor-slug}_{tur}_{from}_{to}.xlsx`, `_ascii_slug()` da
  **bir joyda** quriladi;
- `/accuracy.xlsx` **mavjud** `accuracy_report()` ni chaqiradi va u
  `GET /occupancy/accuracy` bilan **ayni** manba — test buni mexanik
  o'lchaydi (`n` ikkala yuzada teng).

### Sahifalash yo'q, chegara bor

Eksport `limit`/`offset` **qabul qilmaydi**: hujjat butun davrni yozadi,
sig'masa `report_too_large` bilan rad etiladi. Davrning yuqori chegarasi
(kecha) eksportda ham majburlanadi va u yerda **muhimroq**: ekranda
ko'rilgan kam ko'rsatilgan raqam tuzatiladi, faylga tushgani esa
imzolanadi va tarqaladi.

## Rejadan chetlanishlar

### 1. [Rule 1 — Klient kontrakti] `/debtors.xlsx` va `/anomalies.xlsx`

- **Reja aytgan:** `/receivables.xlsx`, `/discrepancies.xlsx` (shu
  jumladan `must_haves.key_links.pattern` da).
- **Yozilgan:** `/debtors.xlsx`, `/anomalies.xlsx`.
- **Sabab:** `report-queries.ts::buildReportPath()` yo'lni AYNAN
  `REPORT_KINDS` a'zosidan quradi: `${REPORTS_PATH}/${kind}.xlsx`. Bu
  08-07 da JSON yarmi uchun qabul qilingan qarorning **aynan takrori**
  va `reports.py` modul docstringining 2-bandi buni oldindan yozib
  qo'ygan («08-12 SHU NOMLARDAN yuradi»).
- **Nega jim nosozlik bo'lardi:** komponent testlari mock bilan yashil
  qolardi, 404 esa faqat jonli ekranda ko'rinardi.

### 2. [Rule 1 — Reja ichidagi ziddiyat] `freeze_panes(2, 0)`

- **Reja aytgan:** `freeze_panes(1, 0)` **va** «davr 1-qatorda».
- **Muammo:** ikkalasi birga bo'lolmaydi — `1` bilan faqat davr
  muzlaydi, sarlavha esa skrollda yo'qoladi.
- **Yechim:** `layout_sheet(header_row=1)` -> `freeze_panes(2, 0)`, ya'ni
  davr **va** sarlavha ikkalasi ham qotadi. Sabab `xlsx_export` modul
  docstringidagi `constant_memory` taqiqi bilan bir xil: «sarlavha
  muzlatilmagan 30 000 qatorli faylda direktor qaysi ustun nima ekanini
  ko'rmay qolardi». Test `sheet.freeze_panes == "A3"` bilan qulflaydi.

### 3. [Rule 2 — Yetishmayotgan kritik funksiya] Yangi darvoza qo'shildi

Sabotaj 1b jim o'tgani uchun
`test_no_non_personal_claim_survives_a_vendor_data_guard` qo'shildi
(yuqoridagi topilma bo'limi). Commit: `a987580`.

### 4. [Rule 3 — Bloklovchi] `request.getfixturevalue()` async fixture bilan ishlamaydi

- **Qachon:** Task 2, rol matritsasi testi.
- **O'lchandi:**
  `RuntimeError: Runner.run() cannot be called from a running event loop`
  — 12 test AYNAN shu bilan qizardi.
- **Yechim:** uch sessiya **argument** sifatida olinadi va test ular
  ustidan yuradi. Sabab test docstringida literal yozildi.

### 5. [Reja tanlovi] Aniqlik jumlasining matni UI'dan olindi

Reja jumlani «...Modelning o'zi **CI'da** o'lchanmagan» deb yozgan;
`reports.accuracyDisclaimer` esa uchala tilda «...**avtomatik sinovda**
o'lchanmagan» deydi. D-06 («atamalar vebdagi bilan AYNI») bo'yicha
**ekran matni** langar qilib olindi — aks holda hujjat va ekran bir
gapni ikki xil aytardi.

### 6. [Reja tanlovi] Hujjatlarda yig'indi qatori yo'q

Reja yig'indi so'ramagan. Filtrlanadigan varaqdagi yig'indi qatori
saralashda ma'lumot qatori bo'lib yuqoriga chiqardi; pul esa SON bo'lib
yozilgani uchun Excelning o'zi yig'adi (bu 08-01 ning `write_money`
qaroridan chiqadigan foyda).

## Tekshiruv natijalari — HAQIQIY o'lchov (2026-08-16, Docker 29.4.2)

| O'lchov | Natija |
|---|---|
| `pytest tests/tenancy tests/unit/test_xlsx_export.py tests/integration/test_reports_api.py tests/integration/test_phase5_criteria.py -q` | **EXIT 0 — 894 passed** |
| `pytest tests/unit/test_xlsx_export.py -q` (Task 1) | **EXIT 0 — 39 passed** |
| `pytest tests/integration/test_reports_api.py tests/tenancy -q` (Task 2) | **EXIT 0 — 845 passed** |
| `pytest tests/tenancy/test_personal_data_coverage.py -q` (Task 3) | **EXIT 0 — 20 passed** |
| `ruff check .` / `ruff format --check .` / `mypy .` | **All checks passed / 366 formatted / 355 fayl, xato yo'q** |
| ⛔ `test_phase5_criteria.py` — 05-15 dalil-kadr kafolati | **YASHIL** (yuqoridagi birinchi qatorga kiradi) |

⚠ Buyruqlar `--no-deps` bilan olindi (08-01 da o'rnatilgan qoida): bu
worktree xost bilan AYNI compose loyihasini baham ko'radi va `--no-deps`
siz chaqiruv ishlab turgan xost stekini qayta yaratardi. Qamrov ayni.

## Qabul mezonlari — bandma-band dalil

### Task 1

| Mezon | Holat | Dalil |
|---|---|---|
| To'rt `build_*_workbook` bor | ✅ | `grep -c '^def build_.*_workbook' -> 4` |
| `worksheet.write(` / `.write_string(` -> `0` | ⚠ **3** | Uchalasi ham **hujjat/yagona sanksiyalangan yo'l**: `:20` va `:288` — izoh (taqiqning O'Z sababi), `:292` — `write_text` ning ichidagi YAGONA `write_string`. Bu 08-01 da o'lchangan **grep-ning o'z-o'ziga qarshiligi**; haqiqiy darvoza `ast` bilan va u shu rejada KENGAYDI (5 funksiya) |
| `measured=False` da foiz katagi bo'sh | ✅ | `test_the_unmeasured_accuracy_file_leaves_the_percent_cells_empty` — `row[1:4] == (None, None, None)` + butun faylda `0` yo'q |
| AI-02 jumlasi ikkala holatda | ✅ | `test_the_accuracy_file_always_carries_the_ai_02_disclaimer[measured|unmeasured]` |
| `pytest tests/unit/test_xlsx_export.py -q` EXIT 0 | ✅ | 39 passed |

### Task 2

| Mezon | Holat | Dalil |
|---|---|---|
| To'rt `.xlsx` marshruti `@router.get` bilan, `@router.post` YO'Q | ✅ | `grep -c '@router.post' -> 0`; `test_the_reports_surface_is_exactly_seven_routes` metodlar to'plamini ham qulflaydi |
| `grep -c "format=xlsx\|format: str"` -> `0` | ⚠ **1** | Yagona moslik `reports.py:651` — **izoh**, taqiqning sababini literal yozadi (Task 1 dagi bilan ayni sinf). Marshrut IMZOSIDA `format` parametri yo'q va yuza yopiq to'plam bilan qulflangan |
| Fayl nomi serverda va ASCII | ✅ | `test_the_server_names_the_export_file_in_ascii` (`filename.isascii()`) + `test_the_export_filename_survives_a_cyrillic_market_name` (`karmana-markaziy-bozori_...`) |
| Test (e) baytlarni QAYTA O'QIYDI | ✅ | `read_rows(response.content, ...)` — mahsulot o'quvchisi; sarlavha qatori uch locale to'plamiga solishtiriladi |
| `pytest tests/integration/test_reports_api.py -q` EXIT 0 | ✅ | butun to'plam yashil |

### Task 3

| Mezon | Holat | Dalil |
|---|---|---|
| `BINARY_PERSONAL_ALLOWED` bor | ✅ | `test_personal_data_coverage.py` (ikki kalitli) |
| Kalitlar tengligi alohida assert | ✅ | `test_the_two_binary_personal_registries_have_identical_keys` |
| `grep -c "BINARY_PERSONAL_ALLOWED.get("` -> `0` | ✅ | o'lchandi: `0` |
| `EVIDENCE_FRAME_ALLOWED` o'zgarmagan | ✅ | `:540` — `{CAMERA_VIEW, OCCUPANCY_REVIEW}`; endi **test bilan** ham qulflangan |
| `pytest tests/tenancy -q` EXIT 0 | ✅ | 854 passed (to'liq yugurishda 894 bilan birga) |
| Uch sabotaj natijasi SUMMARY da | ✅ | yuqoridagi jadval (to'rt o'lchov: 1a, 1b, 2, 3) |

### Reja darajasidagi `success_criteria`

| Mezon | Holat |
|---|---|
| To'rt `.xlsx` marshruti `GET` bilan ishlaydi, baytlari haqiqiy xlsx | ✅ |
| Fayl nomi serverda, ASCII, deterministik | ✅ |
| `BINARY_PERSONAL_ALLOWED` mavjud, kalitlari tengligi assert bilan | ✅ |
| `EVIDENCE_FRAME_ALLOWED` va `SNAPSHOT_EVIDENCE_FRAME_ROUTES` tegilmagan | ✅ |
| Uch sabotaj o'lchangan va natijasi SUMMARY da | ✅ (uchtasi + `1b` varianti) |

## Xavfsizlik — `<threat_model>` bandlari

| Threat | Bajarilishi |
|---|---|
| T-08-48 (formula injection) | `write_text` yagona yo'l; `ast` darvozasi kengaydi; test faylni QAYTA O'QIB `'=HYPERLINK(...)` ni ko'radi |
| T-08-49 (dalil-kadr huquqining kengayishi) | Per-route xarita; `EVIDENCE_FRAME_ALLOWED` TEGILMADI; sabotaj 3 bilan o'lchandi va yangi test bilan qulflandi |
| T-08-50 (auditsiz shaxsiy eksport) | `debtors.xlsx` `BINARY_PERSONAL_ROUTES` da -> `audit_read` majburiy; **sabotaj 1b bo'shliq topdi va u yopildi** |
| T-08-51 (darvozani `POST` bilan chetlash) | To'rtala marshrut `GET`; metodlar to'plami yopiq to'plam testida |
| T-08-52 (sarlavhaga kirill/bo'sh joy) | `_ascii_slug()`; kirill nomli bozor bilan HAQIQIY so'rov o'lchandi |
| T-08-53 (o'lchanmagan aniqlikni `0` qilib yozish) | `write_optional_number` -> `write_blank`; butun faylda `0` yo'qligi o'lchandi; AI-02 jumlasi shartsiz |
| T-08-SC (pip o'rnatish) | ⛔ **Birorta paket o'rnatilmadi** — `pyproject.toml` / `uv.lock` / `package.json` TEGILMADI |

## Known Stubs

Yo'q. To'rtala marshrut ham `report_repo` (08-04) va `accuracy_report`
(05-12) dan **haqiqiy** ma'lumot oladi; to'qilgan qiymat, bo'sh ro'yxat
konstantasi yoki «hozircha mavjud emas» matni qo'shilmadi.

## Threat Flags

Yo'q. To'rt yangi tarmoq endpointi qo'shildi, lekin ular reja
`<threat_model>` ida allaqachon nomlangan va **uch** mustaqil darvoza
bilan qulflangan: yuza yopiq to'plami (`test_route_coverage`), bayt
tasnifi yopiq to'plami va per-route ruxsat xaritasi
(`test_personal_data_coverage`). Reyestrdan tashqarida qolgan yuza yo'q.

## Ochiq qolgan bandlar

- ⚠ **`npm run gate:fast` to'liq bajarilmadi** va sabab muhitda:
  `frontend/node_modules` bu worktree'da yo'q. **Ta'sir yo'q** — bu
  rejaning o'zgarishlari 100 % backend Python (6 fayl, birortasi
  `frontend/` da emas). **Egasi:** orkestrator (merge'dan keyin to'liq
  `gate:fast`).
- ⚠ `_ascii_slug()` **o'zbek kirillicha** jadvali bilan ishlaydi. Rus
  alifbosining `ъ`/`ь`/`ы` lari ham qamrangan, lekin boshqa til (masalan
  qozoq `ә`, `ң`) qo'shilsa belgi `-` ga tushadi — nom baribir ASCII
  qoladi, faqat o'qilishi yomonlashadi. Tetigi: yangi til qo'shilganda
  jadvalni kengaytirish.
- ⚠ `report_max_rows` chegarasi eksportda ham amal qiladi, lekin
  **50 000 qatorli hujjat qurish vaqti o'lchanmadi** (`constant_memory`
  ATAYIN ishlatilmaydi — u `freeze_panes`/`autofilter` ni buzardi).
  Karmana miqyosida (1000 rasta × 30 kun ≈ 30 000) bu xavf past;
  o'lchov 08-18 (yuk) ning zimmasida.

## Keyingi reja uchun

- **08-16** solishtiruv eksportini qo'shganda: yo'l `GET` bo'lsin va u
  `BINARY_PERSONAL_ROUTES`/`NON_PERSONAL_BINARY_ROUTES` dan **biriga**
  yozilsin; shaxsiy bo'lsa `BINARY_PERSONAL_ALLOWED` ga ham
  (aks holda `KeyError` — bu ATAYIN). `/reports` yuzasining soni test
  **NOMIDA** (`..._seven_routes`) va u qo'lda yangilanadi.
- **08-17** eksport tugmalarini `downloadReport(kind, period)` orqali
  ulaydi — yo'l ham, fayl nomi ham allaqachon serverdan keladi, klient
  tomonda qurish KERAK EMAS.
- `xlsx_export.report_texts()` uch tilning kalit to'plami tengligi bilan
  qulflangan: yangi ustun qo'shgan odam uchala tilda ham yozishga
  majbur.

## Self-Check: PASSED

- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-12-SUMMARY.md` — FOUND
- `services/core-api/app/services/xlsx_export.py` — FOUND
- `services/core-api/app/api/v1/reports.py` — FOUND
- `tests/unit/test_xlsx_export.py` — FOUND
- `tests/integration/test_reports_api.py` — FOUND
- `tests/tenancy/test_route_coverage.py` — FOUND
- `tests/tenancy/test_personal_data_coverage.py` — FOUND
- Commitlar `git log` da FOUND: `0818745`, `ee957c3`, `d4e7b6a`,
  `71accab`, `6210366`, `a987580`
- Sabotajlardan keyin ishchi daraxt toza (`git status --short` bo'sh)
- ⛔ `STATE.md` va `ROADMAP.md` **TEGILMADI** (parallel ijro qoidasi —
  ularni orkestrator to'lqin tugagach yozadi)
