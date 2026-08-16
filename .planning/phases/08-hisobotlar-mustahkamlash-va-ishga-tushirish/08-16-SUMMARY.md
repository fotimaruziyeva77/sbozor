---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 16
subsystem: backend-uch-tomonlama-solishtiruv
tags: [RECON-04, SC5, D-18, D-19, D-10, D-09, D-03, R-8, Open-Question-3, T-08-69, T-08-70, T-08-71, T-08-72, T-08-73, T-08-74, three-way, xlsx, signature, tariff-history]
requires:
  - "report_repo.ledger_day() / LedgerDay — daftar qatorlari VA `has_ledger` fakti (08-14)"
  - "occupancy_repo._PER_STALL_CTE — rasta x kun bo'lagining YAGONA `CASE` i (05-x)"
  - "billing_repo._SIGNED_PAYMENT_EXPR — belgili to'lov ifodasi (06-x)"
  - "daily_charges.tariff_amount_soum — kun yopilishida MUZLATILGAN tarif (D-09)"
  - "xlsx_export: new_workbook/write_text/write_money/write_optional_text/layout_sheet/finish (08-01, 08-12)"
  - "api/v1/reports.py — _ascii_slug / _locale_of / _xlsx_response / _guard_row_count (08-07, 08-12)"
  - "tests/tenancy: BINARY_PERSONAL_ROUTES / BINARY_PERSONAL_ALLOWED per-route xaritasi (08-12)"
  - "frontend/src/lib/api-types.ts — threeWayReportSchema / threeWayRowSchema / DIFF_CLASSES (08-03)"
provides:
  - "report_repo.three_way() / ThreeWayReport / ThreeWayRow — uch ustunli HOSILA so'rov"
  - "report_repo.DIFF_LEDGER_OVER / DIFF_SYSTEM_OVER / DIFF_AI_MISMATCH / DIFF_MATCH"
  - "GET /api/v1/reports/compare?day= — JSON (REPORT_VIEW; ismSIZ)"
  - "GET /api/v1/reports/compare.xlsx?day= — IMZOLANADIGAN hujjat (REPORT_VIEW + VENDOR_VIEW + audit_read)"
  - "xlsx_export.build_three_way_workbook / COMPARE_EXPORT_COLUMNS / write_optional_money"
  - "schemas: ThreeWayReportResponse / ThreeWayReportRow — klient strictObject kontraktiga teng"
  - "tests/integration/test_three_way.py — 37 test (18 daftar importi + 19 solishtiruv)"
affects:
  - "08-18 — compare-table.tsx shu javob shakliga va `diff_class: null` konvensiyasiga ulanadi"
  - "08-20 — SC#5 mezon testi shu marshrutdan o'lchaydi"
  - "tests/tenancy/test_route_coverage.py — /reports yuzasi 8 -> 10, son test NOMIDA"
  - "tests/tenancy/test_personal_data_coverage.py — bayt-tasnif ikki kalitdan UCHTAGA"
  - "tests/unit/test_xlsx_export.py — `ast` darvozasining yopiq to'plami 5 -> 6 funksiya"
tech-stack:
  added: []
  patterns:
    - "Sim ustidagi shakl bilan server vokabulyari FARQ QILADI va o'girish BIR joyda (`_wire_diff_class`)"
    - "O'lchanmaganlik UCH manbadan hosila: qator yo'q · `no_coverage` · `default_empty` — uchalasi ham `NULL`"
    - "Tarif AVVAL muzlatilgan nusxadan, so'ng `valid_from <= kun` bo'yicha — retroaktivlik ikki qavatda yopiq"
    - "Sanoqlar qatorlarning O'ZIDAN (`Counter`), ikkinchi `count(*) FILTER` so'rovidan EMAS"
    - "To'rt sanoqning yig'indisi `len(rows)` ga TENG EMAS va tenglikning YO'QLIGI assert bilan qulflangan"
    - "Yangi bayt yo'li ochilganda darvoza BO'SHATILMAYDI — yangi NOMLANGAN yordamchi qo'shiladi"
key-files:
  created:
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-16-SUMMARY.md
  modified:
    - services/core-api/app/repositories/report_repo.py
    - services/core-api/app/api/v1/reports.py
    - services/core-api/app/services/xlsx_export.py
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/integration/test_three_way.py
    - tests/unit/test_xlsx_export.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_personal_data_coverage.py
key-decisions:
  - "Marshrut nomlari KLIENT KONTRAKTIDAN: /compare va /compare.xlsx — reja aytgan /three-way EMAS (to'rtinchi takror)"
  - "JSON javobida `vendor_name` YO'Q, `.xlsx` da BOR — ikki yuza, ikki qaror; JSON shuning uchun VENDOR_VIEW talab qilmaydi"
  - "`match` sim ustida `null` — DIFF_CLASSES uch a'zoli, `\"match\"` yuborilsa klient ZAXIRA badge chizardi (§13.4)"
  - "`ledger_soum` `int`, `int | None` EMAS: daftar yuklangan kun TO'LIQ hujjat, ro'yxatda yo'q rasta = qog'ozda 0"
  - "AI-kutilgan tarifi AVVAL `daily_charges.tariff_amount_soum` (muzlatilgan), hisobsiz band rasta uchun `tariffs` dan `valid_from <= kun`"
  - "`default_empty` -> `NULL` («hech kim qaramadi»), `empty` -> `0` («AI bo'sh dedi») — D-10 ning mexanik shakli"
  - "Qatorlar to'plami — TO'RT signaldan kamida bittasi bo'lgan rastalar, bozorning HAMMA rastasi EMAS (maxraj shishmasin)"
  - "`ai_expected` o'lchanmagan va daftar/tizim mos qator BIRORTA sanoqqa tushmaydi — na `match`, na `ai_mismatch`"
  - "`_open_report()` `_open_document()` ga bo'lindi: kunlik hujjat sarlavhasi «Kun: …», «Davr: X — X» EMAS"
  - "Xom `worksheet.write_blank` o'rniga yangi `write_optional_money` — `ast` darvozasi bo'shatilmadi"
patterns-established:
  - "Klient `strictObject` i bilan to'plam TENGLIGI testda IKKINCHI marta yoziladi (javob modelidan hosila qilinmaydi)"
  - "Sanoqlarning yig'indisi qatorlar soniga TENG EMASLIGI assert bilan qulflanadi — «tenglikni tiklash» refleksi bloklanadi"
  - "Bayt-marshrut tasnifi mahsulot kodidagi e'londan mexanik langar oladi (08-12 darvozasi uchinchi kalit bilan sinaldi)"
requirements-completed: [RECON-04]
duration: 118min
completed: 2026-08-16
---

# Phase 8 Plan 16: Uch tomonlama solishtiruv Summary

**Qog'oz daftar, tizim to'lovi va AI-kutilgani bitta hosila so'rovda yonma-yon
qo'yiladi; kutilgan summa o'sha KUNNING tarifidan chiqadi va HECH QAYERDA
saqlanmaydi, o'lchanmagan bandlik `0` ga aylanmaydi, uch farq sinfi mustaqil
sanaladi — natija esa ikki bo'sh imzo qatori bilan `.xlsx` bo'lib chiqadi.**

## Performance

- **Duration:** ~118 daqiqa (18:29 → 20:27, o'lchov yugurishlari bilan)
- **Tasks:** 3 (hammasi TDD)
- **Files modified:** 9

## Nima qilindi

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | `three_way()` — uch ustun, to'rt sanoq | `31ddac7` (RED) → `ecba428` (GREEN) |
| 2 | `GET /compare` + `/compare.xlsx` + darvozalar | `07210d6` (RED) → `c4ccc59` (GREEN) |
| 3 | Farq sinflari va tenant chegarasi | `c1a5bbd` |
| + | `ast` darvozasi topilmasi bo'yicha tuzatish | `05883f4` |
| + | `main.py` izohining haqiqatga keltirilishi | `8054a51` |

## ⛔ ENG QIMMAT BAND: KLIENT KONTRAKTI REJANING UCH BANDINI QAYTA YOZDI

Reja `/three-way`, `diff_class = "match"` va `vendor_name` li JSON degan edi.
Uchalasi ham 08-03 da (TO'LQIN 1) yozilgan va allaqachon jo'natilgan klient
bilan ZID. Uchala nosozlik ham **JIMGINA** bo'lardi.

### 1. Yo'l — `/compare`, `/three-way` EMAS

`report-queries.ts:253` va `:383` aynan `/compare` va `/compare.xlsx` ga
boradi. Bu 08-07 (`/debtors`), 08-12 (`/debtors.xlsx`) va 08-14
(`/compare/ledger`) qarorining **TO'RTINCHI** takrori.

### 2. ⛔ `match` sim ustiga CHIQMAYDI — bu topilma rejada YO'Q edi

`api-types.ts::DIFF_CLASSES` — AYNAN uch a'zo va `match` unda **ATAYIN**
yo'q; javob sxemasi esa `diff_class` ni `z.string().nullable()` deb o'qiydi,
ya'ni `"match"` **PARSE'DAN O'TIB KETARDI**. Klient uni noma'lum sinf deb
ZAXIRA YORLIQ bilan chizardi — natijada **287 ta mos qator badge olardi va
13 ta haqiqiy farq ular ostida ko'milib ketardi** (UI-SPEC §13.4: «Mos qator
badge OLMAYDI»).

⚠ Nosozlik 200 status, yashil sxema va bo'sh xato jurnali bilan kelardi —
yagona ko'rinadigan oqibat imzolanadigan varaqning MA'NOSI yo'qolishi
bo'lardi.

Yechim: serverda sinf NOM bilan qoladi (`matched_count` aynan shunga
tayanadi), sim ustiga chiqishda esa `_wire_diff_class()` — **YAGONA** o'girish
joyi — uni `None` ga aylantiradi.

### 3. JSON da ISM YO'Q, `.xlsx` da BOR

`threeWayRowSchema` — `strictObject` va unda `vendor_name` ham, `stall_id` ham
yo'q. Ismni «qulaylik uchun» qo'shish IKKI narsani birdan buzardi: klientning
parse chegarasini **va** jurnalni (marshrut `PERSONAL_ROUTES` ga tushib, har
hisobot ochilishida `audit_read` yozardi — HAQIQIY o'qish hodisasi shovqin
ichida ko'milardi).

⛔ Shuning uchun huquq matritsasi ikki yuzada IKKI XIL:

| Yuza | Huquq | `audit_read` | Sabab |
|---|---|---|---|
| `GET /compare` | `REPORT_VIEW` | **yo'q** | javobda shaxsiy maydon YO'Q |
| `GET /compare.xlsx` | `REPORT_VIEW` + `VENDOR_VIEW` | **bor** | rasta ↔ sotuvchi bog'lanishi |

Reja ikkalasidan ham `VENDOR_VIEW` talab qilgan edi; JSON da ism bo'lmagach
u hech nimani qo'riqlamasdan faqat kirishni toraytirardi.

## ⛔ IKKI SABOTAJ — IKKALASI HAM O'LCHANDI

### Sabotaj 1 (Task 1): «bugungi tarif»

`COALESCE(chg.tariff_amount_soum, tar.amount_soum)` → `tar.amount_soum` va
`t.valid_from <= CAST(:business_date AS date)` → `t.valid_from <= CURRENT_DATE`.

**NATIJA — QIZARDI, xabar LITERAL:**

```
E  AssertionError: hisobi bor rastaning kutilgani MUZLATILGAN tarifdan olinishi kerak edi
E  assert 25000 == 15000
E   +  where 25000 = ThreeWayRow(..., stall_code='2', ledger_soum=15000,
E       system_soum=15000, ai_expected_soum=25000, diff_class='ai_mismatch').ai_expected_soum
```

⛔ **Topilma da'vodan kuchliroq chiqdi:** sabotaj ostida qatorning FARQ SINFI
ham `match` dan `ai_mismatch` ga o'zgardi — ya'ni «bugungi tarif» xatosi faqat
bitta ustunni emas, **hisobotning xulosasini** buzardi va u imzolanadigan
varaqda soxta nomuvofiqlik bo'lib ko'rinardi (Open Question 3 ning aynan
oqibati).

### Sabotaj 2 (Task 3): ikki sinfning birlashishi — IKKI SHAKLDA

**(a) SQL shakli** (`WHEN ledger_soum <> system_soum THEN :ledger_over`):

```
E  KeyError: 'system_over'
E  sqlalchemy.exc.ArgumentError: This text() construct doesn't define a
   bound parameter named 'system_over'
```

⛔ Modul **IMPORT BO'LMADI** — `bindparams()` ishlatilmayotgan parametrni
darhol rad etdi, ya'ni sinfni SQL matnidan o'chirish birorta test yugurishidan
OLDIN to'xtaydi. Bu enum qiymatlarini parametr qilish qoidasining
(`_REVERSAL`/`_INCREASE`) kutilmagan, lekin haqiqiy foydasi.

**(b) JIM shakli** (`"system_over": DIFF_LEDGER_OVER` — ikkala sinf bitta
qiymat beradi):

```
E  AssertionError: sinflar bir-biriga oqib o'tdi:
   {'ledger_over': 2, 'system_over': 0, 'ai_mismatch': 1, 'match': 1}
E  Differing items: {'system_over': 0} != {'system_over': 1}
```

⛔ Ikkinchi shakl AYNAN reja o'lchamoqchi bo'lgan holat va u **IKKI** testni
qizartirdi: alohida sinf testi va to'rt sinf birga testi. Holatni
kengaytirish TALAB QILINMADI — seed ikkala yo'nalishdagi farqni ham
o'z ichiga olgan edi (05-15 S-D darsining kutilgan natijasi).

Har sabotajdan keyin fayl `git checkout -- services/core-api/app/repositories/report_repo.py`
bilan tiklandi.

## ⛔ UCHINCHI O'LCHOV: `ast` DARVOZASI XOM YOZUV YO'LINI USHLADI

`build_three_way_workbook` `ai_expected_soum is None` uchun varaqqa **xom**
`worksheet.write_blank(...)` bilan tegdi. 08-01 da qurilgan `ast` darvozasi
buni **o'zi topdi**:

```
E  AssertionError: xom yozish yo'li ochilgan:
   {..., 'build_three_way_workbook': ['write_blank']}
E  Left contains 1 more item: {'build_three_way_workbook': ['write_blank']}
```

⛔ **Ikkita «tuzatish» yo'li bor edi va biri DARVOZANI BO'SHATARDI:**
quruvchining nomini ro'yxatga qo'shish «bu yerda xom yozsa ham bo'larkan»
degan pretsedent berardi va u keyingi safar **sotuvchi ismi yoziladigan
joyda** ishlatilardi.

Tanlangan yo'l — yangi NOMLANGAN yordamchi: `write_optional_money`.
⛔ `write_optional_number` ISHLATILMADI va sabab uning O'Z docstringida
literal yozilgan: annotatsiyasi `float` va «BU FUNKSIYA PUL UCHUN EMAS».
Darvozaning yopiq to'plami 5 → **6** funksiyaga ONGLI ravishda oshdi.

## Task 1 — `three_way()` hosila so'rovi

### Uch ustun, uch manba, BITTA domen sanasi

| Ustun | Manba | Sana |
|---|---|---|
| daftar | `ledger_entries` | `business_date` (domen) |
| tizim | `payments` (belgili, `_SIGNED_PAYMENT_EXPR`) | `service_date` (domen) |
| AI-kutilgan | bandlik bo'lagi × tarif | `stall_slot_occupancy.business_date` |

⛔ **`payments.business_date` (kassa kuni) ISHLATILMADI** va bu modul
docstringining 3-bandidan chekinish emas, uning aynan qo'llanishi: tushum
hisoboti «pul QACHON yig'ildi?» degan KASSA savoliga javob beradi,
solishtiruv esa «shu KUNNING pattasi to'liq yig'ildimi?» degan DOMEN savoliga.
`ledger.py` model docstringi daftarning sanasini AYNAN `daily_charges.service_date`
bilan «bir oilada» deb e'lon qilgan.

### O'lchanmaganlikning UCH manbasi va ular BIR XIL javob beradi

| Bo'lak | `ai_expected_soum` | Ma'nosi |
|---|---|---|
| `occupied` | tarif | O'LCHANGAN |
| `empty` | **`0`** | «AI rastani bo'sh dedi» — O'LCHANGAN |
| `default_empty` | **`NULL`** | «hech kim qaramadi» (AI-06/D-19) |
| `no_coverage` | **`NULL`** | «qamrov yo'q» (D-22) |
| qator YO'Q | **`NULL`** | kun materializatsiya qilinmagan |

Bo'lak `occupancy_repo._PER_STALL_CTE` dan **IMPORT** qilinadi. O'sha
konstanta docstringi «BITTA `CASE`, IKKI ISTE'MOLCHI» der edi — endi
**UCHTA**. Uchinchi nusxa yozilsa `/occupancy` ekranidagi «Bo'sh 68» bilan
solishtiruvdagi bo'sh rastalar soni sekin-asta ajralib ketardi va
**ikkalasi ham xatosiz** ko'rinardi.

### Tarif — ikki qavatli retroaktivlik himoyasi

`COALESCE(chg.tariff_amount_soum, tar.amount_soum)`, tartib MAJBURIY:

1. **muzlatilgan nusxa** (D-09) — `tariffs` qatori keyin TAHRIRLANSA ham
   o'tgan kunning kutilgani o'zgarmaydi;
2. **`valid_from <= kun`** — hisobi YO'Q, lekin BAND rasta (BILL-04/D-28)
   uchun. Bu shoxsiz o'sha rasta BO'SH katak olardi va u «bandlik
   o'lchanmagan» bo'lib O'QILARDI — holbuki bandlik AYNAN o'lchangan.

Ikkala yo'l ham (e) testida BIRGA o'lchanadi.

## Task 2 — ikki marshrut va imzoli hujjat

- ikkalasi ham `@router.get` (`grep -c '@router.post'` → **1**, u 08-14 ning
  daftar importi);
- `day` ning yuqori chegarasi **KECHA** va u `_compare_day()` da, `_report_period()`
  DAN AYRIM: davrning uch xato kodidan ikkitasi bir kunlik so'rovda MA'NOSIZ;
- sahifalash YO'Q, `report_max_rows` dan oshsa `422 report_too_large` —
  **ikkala** yuzada ham;
- fayl nomi `{bozor-slug}_compare_{kun}.xlsx` — `_export_filename()` ishlatilmadi
  (u bir kunlik hujjatda `..._2026-08-15_2026-08-15.xlsx` berardi), slug qoidasi
  esa `_ascii_slug()` da YAGONA joyda qoldi;
- `_open_report()` `_open_document()` ga bo'lindi — kunlik hujjatning birinchi
  qatori «Kun: 2026-08-15», «Davr: 2026-08-15 — 2026-08-15» EMAS.

### Imzo bloki (D-19, §12.6)

Ikki qator, jadvaldan keyin, **filtr diapazonidan TASHQARIDA** (bir qator
tashlab): filtr ichiga tushgan imzo qatori saralashda MA'LUMOT qatori bo'lib
yuqoriga chiqib ketardi va varaqning o'rtasida «Bajaruvchi: ____» paydo
bo'lardi. Ismlar OLDINDAN TO'LDIRILMAYDI — tizim kim imzolashini BILMAYDI.

## Task 3 — farq sinflarining mustaqilligi

⛔ **ENG MUHIM ASSERT — TENGLIKNING YO'QLIGI:**

```python
assert sum(counts.values()) != len(report.rows), (
    "to'rt sanoqning yig'indisi qatorlar soniga TENG bo'lib qoldi — demak "
    "o'lchanmagan AI-kutilganli qator birorta sinfga QO'SHILGAN va u "
    "imzolanadigan varaqda maxrajni SHISHIRADI (D-10)"
)
```

Seedda BESHINCHI rasta ATAYIN bor: daftar va tizimi MOS, AI-kutilgani
O'LCHANMAGAN. Bunday qator na farq DA'VO QILADI, na moslik — ya'ni birorta
sanoqqa tushmaydi. Bu **rejada so'ralmagan**, lekin `matched_count` ning
halolligini saqlaydigan yagona mexanik to'siq: kelajakdagi ijrochi
«sanoqlar qo'shilmayapti-ku» deb tenglikni «tiklashga» urinsa, u
o'lchanmagan qatorni `matched_count` ga qo'shishi kerak bo'lardi — ya'ni
imzolanadigan varaqda «uchala manba mos» degan YOLG'ON maxraj tug'ilardi.

## Rejadan chetlanishlar

### 1. [Rule 1 — Klient kontrakti] `/compare` va `/compare.xlsx`

- **Reja aytgan:** `GET /reports/three-way` va `/three-way.xlsx` (shu jumladan
  `must_haves.artifacts` da).
- **Yozilgan:** `/compare`, `/compare.xlsx`.
- **Sabab:** `report-queries.ts:253,383` (08-03) allaqachon jo'natilgan.
- **Commit:** `c4ccc59`

### 2. [Rule 1 — Klient kontrakti] `match` sim ustida `null`

- **Reja aytgan:** «`diff_class` to'rt qiymatdan biri: … `match`».
- **Yozilgan:** serverda to'rt qiymat, sim ustida uchta + `null`.
- **Sabab:** `DIFF_CLASSES` uch a'zoli va `z.string().nullable()` `"match"` ni
  JIMGINA o'tkazib yuborardi → mos qatorlar zaxira badge olardi (§13.4).
- **Fayllar:** `api/v1/reports.py::_wire_diff_class`, `schemas.py`
- **Commit:** `c4ccc59`

### 3. [Rule 1 — Klient kontrakti] JSON da `vendor_name` YO'Q

- **Reja aytgan:** `ThreeWayRow` da `vendor_name` va JSON marshrutida ham
  `VENDOR_VIEW` + `audit_read` MAJBURIY.
- **Yozilgan:** ism FAQAT `.xlsx` da; JSON `REPORT_VIEW` bilan ochiladi.
- **Sabab:** `threeWayRowSchema` — `strictObject`, ortiqcha maydon butun
  sahifani parse chegarasida yiqitardi. Repo qatorida (`report_repo.ThreeWayRow`)
  ism BOR va u eksportga to'g'ridan-to'g'ri boradi.
- **Commit:** `c4ccc59`

### 4. [Reja tanlovi] `ledger_soum` — `int`, `int | None` EMAS

- **Reja aytgan:** `ledger_soum: int | None`.
- **Sabab:** kunga daftar YUKLANGAN bo'lsa u o'sha kunning TO'LIQ qog'oz
  yozuvi; unda ko'rinmagan rasta «qog'ozda hech nima yig'ilmagan» degani.
  `None` qilib qo'yish `system_over` sinfini («Daftar kamchiligi», §10.5)
  **hisoblab bo'lmaydigan** qilardi — holbuki o'sha sinf AYNAN shu holat uchun
  mavjud. «Daftar umuman yo'q» holati esa KUN darajasida (`has_ledger`).
- **Commit:** `ecba428`

### 5. [Rule 2 — Yetishmayotgan kritik funksiya] Tarifning ikkinchi manbasi

- **Reja aytgan:** AI-kutilgan `daily_charges.tariff_amount_soum` dan.
- **Muammo:** hisobi YO'Q, lekin BAND rasta (BILL-04/D-28 — biriktirilmagan
  savdo) uchun muzlatilgan nusxa MAVJUD EMAS. Faqat birinchi manba bilan u
  BO'SH katak olardi va bo'sh katak §10.4 bo'yicha «bandlik ma'lumoti yo'q»
  degani — ya'ni hujjat **o'lchangan bandlikni o'lchanmagan deb ko'rsatardi**.
- **Yechim:** `COALESCE(...)` ning ikkinchi shoxi — AYNI qoida (`valid_from <= kun`).
- **Commit:** `ecba428`

### 6. [Rule 2 — Yetishmayotgan kritik funksiya] `write_optional_money`

Yuqoridagi `ast` darvozasi topilmasi. **Commit:** `05883f4`

### 7. [Rule 1 — Hujjat kodga zid bo'lib qolardi] `main.py` izohi

- **Muammo:** izoh eskirgan test nomiga (`..._eight_routes`) va «Yetti `GET`»
  ga havola qilardi — 08-14 deviatsiya #3 ning aynan takrori (WR-03).
- **Yechim:** izoh haqiqatga muvofiq qayta yozildi; solishtiruvning
  `REPORT_KINDS` ga kirmasligi ham sabab bilan yozildi.
- **Commit:** `8054a51`

### 8. [Reja tanlovi] Qatorlar to'plami — SIGNALLI rastalar

Reja qatorlar to'plamini aytmagan. Tanlangan: to'rt signaldan (daftar · hisob ·
to'lov · bandlik) kamida bittasi bo'lgan rastalar. Bozorning HAMMA rastasini
yozish 1000 rastali bozorda 700 ta «0 · 0 · bo'sh» qatorini qo'shardi va ular
`matched_count` ga tushardi — «287 tasi mos» o'rniga «987 tasi mos» chiqib,
13 ta farq varaqda KO'MILIB ketardi (§10.5 ning aynan ogohlantirishi).

### 9. [Test tuzatishi] `quote_soum = paid_soum`

Seed dastlab `quote_soum=TARIFF_SOUM` yozgan edi; `ck_payments_override_is_paired`
uni `CheckViolation` bilan rad etdi (server summasidan chetlangan to'lov
`override_reason` talab qiladi). Sababni to'qib yozish testga solishtiruvga
aloqasi yo'q ikkinchi holat kiritardi.

### 10. [Test tuzatishi] `billed_stall()` — toifasi bor rastalar

O'lchandi: `billing_domain._seed_market_a()` toifa davrini FAQAT to'rtta
rastaga beradi; qolgan ikkitasida `market_domain` ning O'Z tarifi (12 000)
qoladi. Tarif izlash yo'lini o'lchaydigan test aynan shu ro'yxatdan rasta
olishi kerak — aks holda u «noto'g'ri tarif» degan YOLG'ON xulosa berardi.

---

**Jami chetlanishlar:** 10 (3 × Rule 1 klient kontrakti, 2 × Rule 2, 1 × Rule 1
hujjat, 2 × reja tanlovi, 2 × test tuzatishi)
**Ta'sir:** yangi paket YO'Q, yangi jadval YO'Q, migratsiya YO'Q. Uchala
klient-kontrakti chetlanishi ham MEXANIK ravishda majburlangan.

## Tekshiruv natijalari — HAQIQIY o'lchov (2026-08-16, Docker 29.4.2)

| O'lchov | Natija |
|---|---|
| `pytest tests/integration/test_three_way.py` | **EXIT 0 — 37 passed** |
| `pytest tests/unit tests/integration/test_three_way.py` | **EXIT 0 — 1069+ passed** |
| `pytest tests/tenancy + test_phase6_criteria + test_reports_api` | **EXIT 0** (birlashgan yugurish) |
| `pytest tests/integration/test_phase6_criteria.py` | **EXIT 0 — 12 passed** |
| `pytest tests/integration/test_reports_api.py` | **EXIT 0 — 63 passed** |
| ⛔ OXIRGI HOLATDA (`05883f4` + `8054a51` dan KEYIN): `tests/tenancy/test_route_coverage.py` + `test_personal_data_coverage.py` + `tests/unit/test_xlsx_export.py` | **EXIT 0 — 82 passed** |
| `ruff check .` / `ruff format --check .` | **All checks passed / 369 fayl** |
| `mypy .` | **Success: 357 fayl, xato yo'q** |
| `node --test frontend/scripts/*.test.mjs` | **295 passed, 0 fail** |

⚠ Buyruqlar `--no-deps` bilan olindi (08-04 `deferred-items.md` №3 qoidasi):
bu worktree xost bilan AYNI compose loyihasini baham ko'radi.

⚠ `npm run gate:fast` TO'LIQ bajarilmadi: `frontend/node_modules` bu
worktree'da yo'q (08-12 va 08-14 da ham shunday edi). `scripts/*.test.mjs`
darvozalari npm bog'liqliksiz yugurdi. **Bu rejaning frontend o'zgarishi
UMUMAN YO'Q** — 9 faylning hammasi backend/test. **Egasi:** orkestrator.

## Qabul mezonlari — bandma-band dalil

### Task 1

| Mezon | Holat | Dalil |
|---|---|---|
| `report_repo.py` da `three_way` bor | ✅ | `grep -cE '^async def three_way'` → `1` |
| `ThreeWayReport` maydonlari AYNAN yettita | ✅ | `test_the_report_carries_four_counters_and_no_total_field` (to'plam tengligi) |
| `grep -cE "total_diff\|totalDiff\|combined_diff\|grand_total"` → `0` | ⚠ **1** | Yagona moslik `report_repo.py:1427` — **DOCSTRING**, taqiqning O'Z sababini yozadi. Bu 08-12/08-14 da ikki marta o'lchangan «grep-ning o'z-o'ziga qarshiligi» sinfi; nomlarni o'chirish keyingi ijrochi uchun taqiqni TOPIB BO'LMAYDIGAN qilardi |
| Test (b) `None` va `0` ni bitta testda ajratadi | ✅ | `test_an_unmeasured_ai_column_is_never_the_same_as_a_measured_zero` (+ uchinchi holat `default_empty`) |
| Test (e) eski tarifdan chiqishini assert qiladi | ✅ | `test_yesterdays_expectation_uses_yesterdays_tariff` — IKKI yo'l (muzlatilgan + `tariffs`) |
| Sabotaj natijasi SUMMARY da | ✅ | yuqoridagi bo'lim (literal xabar bilan) |

### Task 2

| Mezon | Holat | Dalil |
|---|---|---|
| `/compare` va `/compare.xlsx` mavjud, ikkalasi `@router.get` | ✅ | `test_the_reports_surface_is_exactly_ten_routes` metod xaritasini ham qulflaydi |
| `compare.xlsx` ikkala bayt reyestrida | ✅ | `BINARY_PERSONAL_ROUTES` + `BINARY_PERSONAL_ALLOWED`; kalit tengligi alohida testda |
| `xlsx_export.py` da imzo qatorlari, ismlar to'ldirilmaydi | ✅ | `compare_sign_executor`/`compare_sign_approver` uch tilda; `build_three_way_workbook` faqat shu ikki matnni yozadi |
| Test (c) fayl baytlarini QAYTA O'QIYDI | ✅ | `read_rows(response.content, ...)` — mahsulot o'quvchisi; oxirgi ikki qator tekshiriladi |
| `pytest tests/tenancy -q` EXIT 0 | ✅ | to'liq to'plam yashil |

### Task 3

| Mezon | Holat | Dalil |
|---|---|---|
| To'rt sinf uchun alohida testlar + birlashgan holat | ✅ | 4 + 1 test |
| Cross-tenant testi bor | ✅ | `test_the_other_markets_director_sees_none_of_market_a_stalls` (NAZORAT bilan) |
| (e) yig'indi maydonining YO'Qligini to'plam tengligi bilan | ✅ | `set(response.json()) == COMPARE_RESPONSE_KEYS` + `sum(counts) != len(rows)` |
| `pytest tests/integration/test_three_way.py -q` EXIT 0 | ✅ | 37 passed |
| Sabotaj natijasi SUMMARY da | ✅ | ikki shaklda (SQL va jim) |

### Reja darajasidagi `success_criteria`

| Mezon | Holat |
|---|---|
| `three_way()` uch ustunni hosila so'rov bilan beradi, AI-kutilgan saqlanmaydi | ✅ |
| `None` va `0` ajratilgan va IKKI joyda (JSON va xlsx) o'lchangan | ✅ |
| Uch farq sinfi alohida sanaladi, yig'indi maydoni yo'q | ✅ |
| Imzo qatorlari faylda, ismlar bo'sh | ✅ |
| Ikki sabotaj o'lchangan | ✅ (uchtasi: 1 + 2 shakl) |

## Xavfsizlik — `<threat_model>` bandlari

| Threat | Bajarilishi |
|---|---|
| T-08-69 (uch farqni bitta songa siqish) | To'rt sanoq alohida; yig'indi maydoni yo'q; **yig'indi ≠ `len(rows)`** assert bilan; sabotaj 2 ikki shaklda o'lchandi |
| T-08-70 (o'lchanmagan bandlikni «0» deb ko'rsatish) | `default_empty`/`no_coverage`/qatorsiz → `NULL`; test (b) uch holatni ajratadi; eksportda `write_optional_money` → `write_blank` |
| T-08-71 (eski kunga bugungi tarifni qo'llash) | Muzlatilgan nusxa + `valid_from <= kun`; test (e) ikki yo'l bilan; sabotaj 1 QIZARDI |
| T-08-72 (rasta ↔ sotuvchi bog'lanishi) | `.xlsx` da `VENDOR_VIEW` + `audit_read(report_three_way_export)`; ikkala bayt reyestrida; JSON da ism UMUMAN yo'q; cross-tenant testi NAZORAT bilan |
| T-08-73 (sahifalashsiz javob) | `report_max_rows` → `422 report_too_large` IKKALA yuzada; `limit`/`offset` parametrlari umuman yo'q |
| T-08-74 («imzolangan» soxta holat) | Raqamli imzo YO'Q; ismlar to'ldirilmaydi (test buni fayl baytlaridan o'lchaydi); `[Imzolash]` tugmasi 08-18 da qurilmaydi |
| T-08-SC (pip o'rnatish) | ⛔ **Birorta paket o'rnatilmadi** — `pyproject.toml` / `uv.lock` / `package.json` TEGILMADI |

## Known Stubs

Yo'q. Uchala ustun ham HAQIQIY jadvallardan o'qiladi (`ledger_entries`,
`payments`, `stall_slot_occupancy` + `daily_charges`/`tariffs`), eksport
HAQIQIY qatorlarni yozadi. To'qilgan qiymat, bo'sh ro'yxat konstantasi yoki
«hozircha mavjud emas» matni qo'shilmadi.

⚠ `diff_class is None` (AI o'lchanmagan) qatorlari birorta sanoqqa tushmaydi
va bu **stub emas, nomlangan qaror** — sababi `_THREE_WAY` docstringida va
`ThreeWayReport` docstringida LITERAL yozilgan hamda test bilan qulflangan.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-personal-export | `services/core-api/app/api/v1/reports.py` | `GET /compare.xlsx` — rasta ↔ sotuvchi bog'lanishini ochadigan IKKINCHI bayt marshruti. Reja `<threat_model>` ida nomlangan (T-08-72) va uch mustaqil darvoza bilan qulflangan: yuza yopiq to'plami (`test_route_coverage`), bayt tasnifi + per-route ruxsat xaritasi (`test_personal_data_coverage`) va rol matritsasi (`test_three_way`). Reyestrdan tashqarida qolgan yuza yo'q |

## Ochiq qolgan bandlar

- ⚠ **`ledger_day_locked` klient kodi HAMON SERVERDA YO'Q** (08-14 dan meros;
  o'sha SUMMARY uning egasini 08-16 deb belgilagan). Bu reja kun ustidagi
  qoidani o'rnatdi — **maksimum KECHA** — va uni `report_period_future`
  bilan majburlaydi. Ya'ni bugungi kunda `day_locked` ga AJRALIB TURADIGAN
  ma'no YO'Q: «kun yopilgan» degan ma'muriy holat (bozor yopiq kuni, qulflangan
  hisobot davri) hech qayerda mavjud emas. Kodni «bo'lsin» deb qo'shish
  klientga hech qachon kelmaydigan shoxni ochib qo'yardi. **Egasi:** ma'muriy
  qulf tushunchasi tug'ilgan reja (bugun rejalashtirilmagan).
- ⚠ **`compare.xlsx` ning fayl nomi `test_reports_api.py` ning ASCII/kirill
  testlari bilan QAMRALMAGAN**: o'sha testlar `EXPORT_URLS` ro'yxatidan yuradi
  va u davr hisobotlariniki. Nom `_ascii_slug()` ning AYNI funksiyasidan
  quriladi, ya'ni slug qoidasi qamrangan; qamralmagani — `_compare_filename()`
  ning `compare_{kun}` qismi. **Egasi:** 08-20 (mezon testi) yoki alohida band.
- ⚠ **50 000 qatorli solishtiruv hujjatini qurish vaqti o'lchanmadi** —
  08-12 ning aynan o'sha ochiq bandi. Karmana miqyosida bir kun ≤ 1000 qator,
  ya'ni xavf 08-12 dagidan ham past.

## Keyingi reja uchun

- **08-18:** javob shakli `threeWayReportSchema` bilan AYNAN mos.
  ⛔ **`diff_class === null` IKKI ma'noni tashiydi** va ekranda ikkalasi ham
  BADGE OLMAYDI: «uchala manba mos» (`matched_count` ga tushgan) va «AI-kutilgan
  o'lchanmagan» (birorta sanoqqa tushmagan). Ikkinchisini ajratish kerak bo'lsa
  signal `ai_expected_soum === null` da — badge'da emas.
  ⚠ `matched_count` `rows` uzunligidan HOSILA EMAS va ular teng bo'lmasligi
  NORMAL — «Mos: {matched}» matnini `rows.length` bilan solishtirmang.
- **08-20:** SC#5 mezon testi `GET /reports/compare?day=` dan o'lchasin;
  seed retsepti `tests/integration/test_three_way.py::compare` fixture'ida
  (billing + bandlik + daftar uchun bo'sh maydon) tayyor.
- Yangi bayt yozish yo'li kerak bo'lgan HAR KIM uchun: `ast` darvozasi
  (`test_xlsx_export.py`) quruvchini ro'yxatga QO'SHISHNI emas, yangi
  NOMLANGAN yordamchi yozishni talab qiladi — 08-16 da bu bir marta
  o'lchandi va yo'l shu.

## Self-Check: PASSED

- `.planning/phases/08-.../08-16-SUMMARY.md` — FOUND
- `services/core-api/app/repositories/report_repo.py` — FOUND
- `services/core-api/app/api/v1/reports.py` — FOUND
- `services/core-api/app/services/xlsx_export.py` — FOUND
- `services/core-api/app/schemas.py` — FOUND
- `services/core-api/app/main.py` — FOUND
- `tests/integration/test_three_way.py` — FOUND
- `tests/unit/test_xlsx_export.py` — FOUND
- `tests/tenancy/test_route_coverage.py`, `tests/tenancy/test_personal_data_coverage.py` — FOUND
- Commitlar `git log` da FOUND: `31ddac7`, `ecba428`, `07210d6`, `c4ccc59`,
  `c1a5bbd`, `05883f4`, `8054a51`
- Sabotajlardan keyin ishchi daraxt toza (`git status --short` da faqat SUMMARY)
- ⛔ `STATE.md` va `ROADMAP.md` **TEGILMADI** (parallel ijro qoidasi —
  ularni orkestrator to'lqin tugagach yozadi)
- ⛔ `frontend/` **TEGILMADI** (08-18 parallel ishlayapti)

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
