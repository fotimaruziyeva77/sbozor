---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 01
subsystem: core-api / xlsx eksport
tags: [determinizm, formula-injection, xlsx, settings, RECON-04]
requires:
  - "app.services.xlsx_template (mavjud eksport yo'llari)"
  - "app.services.xlsx_reader (ZIP darvozalari)"
  - "tests/fixtures/karmana_seed (_freeze_zip naqshining manbasi)"
provides:
  - "app.services.xlsx_export — freeze_zip / new_workbook / finish / write_text / write_money / write_optional_text / money_format / escape_formula"
  - "Settings.report_max_period_days, Settings.report_max_rows"
  - "tests/unit/test_xlsx_export.py — Wave-0 darvozasi (10 test funksiyasi, 15 holat)"
affects:
  - "08-10 (eksport marshrutlari) — shu modulni chaqiradi"
  - "08-16 (imzoli solishtiruv eksporti) — bayt-determinizmga tayanadi"
  - "08-07 (hisobot so'rovlari) — report_max_* chegaralarini o'qiydi"
tech-stack:
  added: []
  patterns:
    - "Yagona yozish yuzasi: worksheet.write* faqat xlsx_export ichida, ast bilan qulflangan"
    - "Bog'liqlik yo'nalishi bitta: xlsx_template -> xlsx_export"
    - "Sabotaj o'lchovi da'voni rad etsa — hujjat tuzatiladi, test emas"
key-files:
  created:
    - services/core-api/app/services/xlsx_export.py
    - tests/unit/test_xlsx_export.py
  modified:
    - services/core-api/app/services/xlsx_template.py
    - services/core-api/app/settings.py
    - services/core-api/app/services/__init__.py
    - tests/fixtures/karmana_seed.py
    - tests/unit/test_karmana_seed.py
    - tests/unit/test_xlsx_template.py
decisions:
  - "escape_formula ta'rifi xlsx_export ga ko'chdi — rejadagi yo'nalish halqa hosil qiladi (ikkala kirish nuqtasida ImportError o'lchandi)"
  - "report_export_max_rows maydoni QO'YILMADI — report_max_rows bilan ayni ma'noda"
  - "T-02-165 darvozasi 'hech qanday app.*' dan 'aynan ikki simvol' ga toraytirildi + yangi tranzitiv da'vo qo'shildi"
  - "freeze_zip determinizm qatlami EMAS — XlsxWriter 3.2.9 a'zo sanasini o'zi muzlatadi; u invariant qo'riqchisi sifatida saqlandi va shartnomasi alohida o'lchanadi"
  - "worksheet.write( darvozasi grep emas, ast bilan (02-23 pretsedenti)"
requirements: [RECON-04]
metrics:
  duration: 40 min
  tasks: 3
  files: 8
  completed: 2026-08-16
---

# Phase 8 Plan 01: Bayt-determinik `.xlsx` eksport poydevori — Summary

Bayt-determinik `.xlsx` eksportining yagona uyi (`app/services/xlsx_export.py`) qurildi, uchala eksport yo'li unga bog'landi va hisobot chegaralari `Settings` ga chiqarildi — sabotaj esa rejaning «ikki mustaqil determinizm qatlami» da'vosini rad etdi.

## Nima qilindi

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | `xlsx_export.py` + `Settings` chegaralari (TDD: RED -> GREEN) | `e2eb3e8`, `ef671ad` |
| 2 | `xlsx_template` + `karmana_seed` ni yangi modulga bog'lash | `ece6a27` |
| 3 | Wave-0 darvozasi + majburiy sabotaj | `3ecd02c` |

## Reja tuzatgan texnik da'vo (kutilgan)

Reja o'zi ogohlantirgan edi: D-05 «`xlsx_template.py` dagi mavjud `_freeze_zip`
naqshi qayta ishlatiladi» der edi, aslida u faqat `tests/fixtures/karmana_seed.py`
da yashardi. Bu tasdiqlandi va bajarildi — naqsh mahsulotga ko'chirildi,
fikstursdagi nusxa o'chirildi.

⛔ **ONGLI KENGAYTMA (rejada ochiq yozilgan):** `build_template()` va
`build_error_report()` bugungacha bayt-determinik EMAS edi. Ular determinik
qilindi, ya'ni chiqish baytlari O'ZGARDI. O'lchandi: sabotaj (ikkalasini eski
holatga qaytarish) `test_two_builds_are_byte_identical[template]` ni qizartirdi,
baytlar **4735-indeksda** ajraldi.

## ⛔ TOPILMA: sabotaj rejaning da'vosini RAD ETDI

Reja Task 3 da majburiy sabotaj buyurgan va natijani oldindan aytgan edi:
«Ikki qatlam ikki xil sababdan qo'riqlaydi — bittasi ikkinchisini
yopmasligi ISBOTLANSIN». O'lchov teskarisini ko'rsatdi.

| # | Sabotaj | Kutilgan | O'LCHANGAN |
|---|---------|----------|------------|
| S-1 | `new_workbook()` dan `set_properties({"created": ...})` olindi | qizarish | ✅ **QIZARDI** — baytlar 3942-indeksda ajraldi |
| S-2 | `finish()` dan `freeze_zip` olindi | qizarish | ❌ **QIZARMADI** — 14/14 test yashil qoldi |
| S-3 | `freeze_zip` `return raw` qilindi (yangi shartnoma testiga qarshi) | — | ✅ **QIZARDI** — `(2026, 8, 16, 10, 27, 0)` vs `(1980, 1, 1, 0, 0, 0)` |

**Sabab o'lchandi** (zond, `XlsxWriter` 3.2.9):

```
XOM xlsxwriter a'zo sanalari: {(1980, 1, 1, 0, 0, 0)}
set_properties SIZ,   freeze_zip SIZ, 1.1 s oraliq -> teng? False
set_properties BILAN, freeze_zip SIZ, 1.1 s oraliq -> teng? True
```

Ya'ni `XlsxWriter` ZIP a'zo sanasini O'ZI muzlatadi va soat faylga **faqat
bitta yo'ldan** — `docProps/core.xml` dagi `dcterms:created` — kiradi.
Determinizm qatlami **bitta**, ikkitasi emas.

Bu 02-23 dan meros qolgan docstring da'vosini ham yolg'on qiladi
(«`zipfile` a'zo sanasini SOAT'dan oladi»). Da'vo ikki faylda tuzatildi.

**Qaror:** `freeze_zip` O'CHIRILMADI (reja uni `must_haves` artefakti deb
belgilagan va u haqiqiy qiymat beradi), lekin **halol qayta ta'riflandi** —
u determinizm qatlami emas, **a'zo sanasi invariantining qo'riqchisi**:
`XlsxWriter` ning ichki tanlovi o'zgarsa ham da'vo rost qoladi. Uning O'Z
shartnomasi endi `test_freeze_zip_normalises_clock_dated_members` da
to'g'ridan-to'g'ri o'lchanadi — kirish arxivi ATAYIN `zipfile` bilan, SOAT
sanasi bilan quriladi (`XlsxWriter` dan olingan kirish kutubxonani sinardi,
funksiyani emas).

⚠ Bu 05-15 darsining takrori: **sabotaj hech nimani qizartirmasa, tuzatish
testda emas.** Bu safar tuzatish HUJJATDA bo'ldi — mexanizm to'g'ri, uni
ta'riflagan hikoya noto'g'ri edi.

## Reja belgilagan yo'ldan chetlanishlar

### 1. [Rule 3 — Bloklovchi] `escape_formula` ta'rifi `xlsx_export` ga ko'chdi

- **Qachon:** Task 1/2 chegarasida
- **Muammo:** Task 1 «`escape_formula` ni `xlsx_template` dan import qil»
  deydi, Task 2 esa «`xlsx_template` `new_workbook`/`finish` ni `xlsx_export`
  dan olsin» — bu halqa.
- **O'lchov (taxmin emas, probe bilan bajarildi):**
  ```
  $ python -c "import app.services.xlsx_export"
  ImportError: cannot import name 'finish' from partially initialized
  module 'app.services.xlsx_export' (most likely due to a circular import)

  $ python -c "import app.services.xlsx_template"
  ImportError: cannot import name 'FORMULA_PREFIXES' from partially
  initialized module 'app.services.xlsx_template'
  ```
  Halqa import TARTIBIGA bog'liq emas — ikkala tomondan ham yiqiladi,
  shu jumladan mahsulot yo'li (`api/v1/imports.py` -> `xlsx_template`).
- **Yechim:** rejaning O'ZI ko'zda tutgan zaxira yo'li (Task 2:
  «yo'nalish BITTA bo'lsin va tanlangan yo'nalish SUMMARY da nomlansin»).
  **Tanlangan yo'nalish: `xlsx_template` -> `xlsx_export`.**
  `xlsx_template` `FORMULA_PREFIXES`/`escape_formula` ni QAYTA E'LON qiladi,
  ya'ni mavjud chaqiruvchilar o'zgarmadi va ta'rif hamon bitta.
- **Fayllar:** `xlsx_export.py`, `xlsx_template.py`
- **Commit:** `ef671ad`, `ece6a27`

### 2. [Rule 3 — Bloklovchi] T-02-165 mustaqillik darvozasi toraytirildi

- **Qachon:** Task 2
- **Muammo:** Reja `karmana_seed.py` ga
  `from app.services.xlsx_export import freeze_zip` ni MAJBURIY qildi, lekin
  mavjud darvoza `app.*` dan HAR QANDAY importni taqiqlaydi. O'lchandi:
  ```
  AssertionError: generator ishlab chiqarish paketiga bog'landi:
  ['app.services.xlsx_export'] — yuk quvurning O'ZIDAN kelsa miqyos
  o'lchovi hech nimani isbotlamaydi
  ```
- **Yechim:** darvozaning MA'NOSI saqlandi, YUZASI toraytirildi. U «yuk
  quvurning o'zidan kelmasin» deydi — ustun tartibi, sarlavha matni,
  namunaviy qator shablondan olinmasin. `freeze_zip`/`new_workbook` esa
  yuk emas: ular metama'lumotni muzlatadi, MAZMUNGA bitta bayt qo'shmaydi.
- **Darvoza ikki tomondan KUCHAYTIRILDI ham:**
  1. Ruxsat endi **simvol** darajasida (modul emas) — `build_template` ni
     `xlsx_export` orqali olib kelib bo'lmaydi; yalang'och `import app...`
     alohida taqiqlandi.
  2. **Yangi, ilgari umuman bo'lmagan da'vo:** `xlsx_export` ning O'ZI
     `xlsx_template` ni import qilmasligi. Usiz ruxsat TRANZITIV orqa eshik
     bo'lardi va `ast` skaneri buni ko'rmasdi.
- **Fayllar:** `tests/unit/test_karmana_seed.py`
- **Commit:** `ece6a27`

### 3. [Rule 3 — Bloklovchi] `worksheet.write(` darvozasi `grep` emas, `ast`

- **Qachon:** Task 1
- **Muammo:** Qabul mezoni `grep -c 'worksheet.write(' -> 0` talab qiladi,
  lekin AYNI reja modul docstringiga `worksheet.write()` ni LITERAL yozishni
  ham buyuradi (2-fakt). O'lchandi: naiv `grep` **2** qaytaradi va ikkalasi
  ham DOKUMENTATSIYA (14- va 204-qatorlar). Darvoza o'z-o'ziga qarshi turardi.
- **Yechim:** 02-23 pretsedenti («mustaqillik darvozasi grep emas, ast bilan —
  docstring taqiqning sababini literal aytadi va grep uni o'z-o'ziga qarshi
  qo'yardi»). `test_raw_worksheet_writes_live_only_inside_write_text` `ast`
  bilan HAQIQIY da'voni o'lchaydi va u grep'dan kuchliroq: har `worksheet.*`
  chaqiruvi qaysi funksiyada ekani qulflanadi.
- **Commit:** `ef671ad`

### 4. [Rule 2 — Yetishmayotgan izchillik] `_FROZEN_CREATED` nusxasi ham o'chirildi

Reja faqat `_freeze_zip` ni ko'chirishni so'ragan edi, lekin `karmana_seed`
da `_FROZEN_CREATED` ham nusxa bo'lib qolardi — ya'ni «ikki nusxa bir kun
ajralib ketardi» degan sabab yarim hal bo'lardi. Fikstur endi `new_workbook()`
ni ishlatadi; `_FROZEN_ZIP_TIME` va `_FROZEN_CREATED` o'chirildi.

⛔ `karmana_seed` ATAYIN `xlsx_export.finish()` ni ISHLATMAYDI va matnni XOM
yozishda davom etadi: `_FORMULA_NOTE = "=1+1 (eski hisob izohi)"` qochirilmasligi
KERAK (qochirish eksport tomonining ishi, import tomonida `=` oddiy izoh).

### 5. [Reja tanlovi] `report_export_max_rows` maydoni qo'yilmadi

Reja «agar ikkinchisi va uchinchisi bir xil ma'noda bo'lsa BITTA maydon
qoldirilsin» degan edi. Ular bir xil ma'noda: eksport hisobotning O'ZI
qaytargan qatorlarni yozadi (`in_memory` kitob). Ikki maydon ikki xil qiymat
olganda «ekranda ko'rinadi, lekin yuklab bo'lmaydi» degan tushuntirib bo'lmas
holat tug'ilardi. Sabab `settings.py` da izoh sifatida yozilgan.

## Muvaffaqiyat mezonlari

| Mezon | Holat | Dalil |
|-------|-------|-------|
| `freeze_zip` repo'da AYNAN BIR joyda, mahsulot modulida | ✅ | `grep -c "_freeze_zip" karmana_seed.py` -> 0; ta'rif faqat `xlsx_export.py` da |
| `build_template` / `build_error_report` ikki chaqiruvda bayt-bayt teng | ✅ | `test_two_builds_are_byte_identical[template]`, `[error-report]` (1.1 s oraliq bilan) |
| `Settings.report_max_period_days = 366`, `report_max_rows = 50000` | ✅ | `settings.py:125-126` |
| Formula-injection oltala prefiks uchun o'lchangan | ✅ | `test_formula_injection_is_escaped_for_every_prefix` — 6 holat, fayldan QAYTA O'QIB |
| Ikki sabotaj bajarilgan va natijasi SUMMARY da | ✅ | Yuqoridagi jadval — uchta sabotaj, biri da'voni rad etdi |

## Tekshiruv

| Buyruq | Natija |
|--------|--------|
| `pytest tests/unit/test_xlsx_export.py -q` | **15 passed** |
| `pytest tests/unit/test_xlsx_template.py tests/unit/test_karmana_seed.py -q` | **61 passed** |
| `pytest tests/unit -q` (regressiya) | **1243 passed** |
| `ruff check .` | All checks passed |
| `ruff format --check .` | 352 files already formatted |
| `mypy .` | 342 source files, no issues |
| `node --test` (frontend) | **249 passed**, 0 fail |
| `python -c "import app.api.v1.imports"` | OK (mahsulot import zanjiri sog'lom) |

## Ochiq bandlar

- **`npm run gate:fast` TO'LIQ bajarilmadi** va sababi muhit, kod emas:
  1. `test:fast` `docker compose ... run --rm tests` ni `--no-deps` SIZ
     chaqiradi. Bu worktree xost bilan AYNI compose loyihasini
     (`sbozor`) baham ko'radi, ya'ni buyruq ishlab turgan xost stekini
     qayta yaratadi — bir marta o'lchandi, `sbozor-storage-1` uzildi va
     qo'lda tiklandi. Shundan keyin barcha yugurishlar `--no-deps` bilan
     olindi; qamrov ayni (`pytest tests/unit`, faqat `-x` farqi).
  2. `frontend test` zanjiridagi `vitest run` bajarilmadi:
     `frontend/node_modules` bu worktree'da yo'q. Paket o'rnatish ATAYIN
     qilinmadi. **Ta'sir yo'q:** bu rejaning o'zgarishlari 100 % backend
     Python (8 fayl, birortasi `frontend/` da emas).
  - **Egasi:** orkestrator (merge'dan keyin to'liq `gate:fast`), yoki
    keyingi reja.
- **`report_max_rows = 50_000` `[ASSUMED]`** va tetigi yozilgan
  (`settings.py` izohi): birinchi oyda `report_too_large` bir marta ham
  chiqmasa chegara to'g'ri.
- `report_max_period_days` / `report_max_rows` hali BIROR joyda
  ISHLATILMAYDI — ular 08-07/08-10 uchun qo'yildi (reja shunday belgilagan).
  Chegaralarni 422 ga aylantirish o'sha rejalarning zimmasida.

## Xavfsizlik

`<threat_model>` bandlari:

- **T-08-01 (formula injection)** — mitigatsiya qilindi va o'lchandi: yagona
  matn yo'li `write_text`, `ast` darvozasi xom `worksheet.write*` ni
  bloklaydi, oltala prefiks fayldan qayta o'qib tekshiriladi. `xlsx_template`
  dagi IKKINCHI qochirish yo'li ham yo'q qilindi (`_write_text` endi
  delegatsiya qiladi).
- **T-08-02 (DoS)** — chegaralar `Settings` da (majburlash 08-07/08-10 da).
- **T-08-03 (tampering)** — a'zo nomi/siqish turi/ochilgan hajm o'zgarmasligi
  ikki testda, `xlsx_reader` ning O'ZI bilan ham (`read_rows` orqali).
- **T-08-SC** — birorta yangi paket o'rnatilmadi; `pyproject.toml` va
  `package.json` TEGILMADI (`git diff --name-only` bilan tasdiqlangan).

Yangi xavfsizlik yuzasi ochilmadi (tarmoq endpointi, auth yo'li, sxema
o'zgarishi yo'q) — `## Threat Flags` bo'limi shu sababdan yo'q.

## Known Stubs

Yo'q. Modulning har yuzasi (`freeze_zip`, `new_workbook`, `money_format`,
`write_text`, `write_money`, `write_optional_text`, `finish`, `escape_formula`)
kamida bitta test bilan bajariladi va uchala eksport yo'li (import shabloni,
xato hisoboti, test fiksturasi) unga real ravishda bog'langan.

## Keyingi reja uchun

- 08-10 va 08-16 `xlsx_export` ni chaqiradi; `xlsxwriter.Workbook(...)` ni
  to'g'ridan-to'g'ri chaqirish yoki ikkinchi `escape_formula` yozish endi
  KERAK EMAS va `test_raw_worksheet_writes_live_only_inside_write_text`
  buni modul ichida mexanik ravishda to'sadi.
- ⚠ O'sha darvoza hozircha FAQAT `xlsx_export.py` ni skanerlaydi. Yangi
  eksport moduli qo'shilganda skaner maydonini kengaytirish kerak — aks
  holda yangi modul xom `worksheet.write()` bilan yozsa darvoza jim qoladi.

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:

- `services/core-api/app/services/xlsx_export.py`
- `tests/unit/test_xlsx_export.py`
- `.planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-01-SUMMARY.md`

Commitlar `git log` da mavjud: `e2eb3e8`, `ef671ad`, `ece6a27`, `3ecd02c`,
`77483c8`. Ish daraxti toza (`git status --short` bo'sh).
