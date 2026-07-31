---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 12
subsystem: api
tags: [xlsx, openpyxl, defusedxml, xlsxwriter, dos, formula-injection, all-or-nothing, idempotency, multipart, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-11 — `PLATFORM_ADMIN_ROUTES` matritsa mexanikasi, `market_is_active` kodi, faollashtirish darvozasining `valid_from <= operating_since` talabi; 02-10 — `normalize_phone()` ni IMPORT yo'lida chaqirish majburiyati, `BODY_FILLERS` mexanikasi, 'bo'sh javob tenant teshigini yashiradi' darsi; 02-09 — 'routerlar SQL bajarmaydi' konvensiyasi; 02-08 — `app/schemas.py` DTO shartnomasi (`ImportResultResponse`/`ImportErrorItem`/`ImportErrorResponse`), `MARKET_ERROR_CODES`, `sqlstate_of()`, `_market_id()` naqshi, `BODY_FILLERS` (deviatsiya #4); 02-07 — `market_scope`/`market_today` fixture'lari; 02-05 — `stall_code_claim()` `BEFORE INSERT` triggeri `ON CONFLICT DO NOTHING` da HAM ishlaydi; 02-04 — `StallStatus`, `MarketProfile.operating_since`"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`TenantSessionDep` (tranzaksiyani O'ZI ochadi), `SettingsDep` (`app.state` dan), `require_permission`, `user_repo.list_profiles()`, cross-tenant matritsasi"
provides:
  - "`app/services/` — DB ga tegmaydigan sof domen servislari paketi (yangi qatlam)"
  - "`app/services/xlsx_reader.py` — xavfsiz `.xlsx` o'qish (ZIP + XML DoS darvozalari, sozlanadigan chegaralar)"
  - "`app/services/import_validator.py` — YOZISHDAN OLDIN to'liq validatsiya, qator-raqamli xatolar"
  - "`app/services/xlsx_template.py` — shablon va xato hisoboti + formula injection qochirish"
  - "`app/repositories/import_repo.py` — `ImportRepository` (olti lug'at so'rovi + ikkita ommaviy `INSERT`)"
  - "`app/api/v1/imports.py` — 4 marshrut (`template`, `stalls`, `vendors`, `errors.xlsx`)"
  - "`app.schemas`: `ImportErrorReportRequest`, `IMPORT_ERROR_REPORT_MAX`, `import_conflict` kodi (22 -> 23)"
  - "`app/settings.py` — oltita import chegarasi (A7, muhitdan sozlanadi)"
  - "`tests/tenancy/test_cross_tenant.py::FILE_FILLERS` — `multipart/form-data` marshrutlari uchun matritsa mexanikasi + uni yuk ko'taruvchi qiladigan darvoza"
  - "`fixtures.admin_api.IMPORTS_TEMPLATE_URL` / `IMPORT_STALLS_URL` / `IMPORT_VENDORS_URL` / `IMPORTS_ERRORS_URL`"
  - "`fixtures.market_domain.A_CATEGORY_NAMES` (eksport qilindi)"
affects: [02-13, 02-14, 02-15, 02-16, 02-17, 06-hisob-kitob]

# Tech tracking
tech-stack:
  added:
    - "openpyxl==3.1.5 (MIT) — faqat O'QISH"
    - "defusedxml==0.7.1 (PSFL) — openpyxl uchun XML hujum himoyasi"
    - "XlsxWriter==3.2.9 (BSD-2) — faqat YOZISH"
  patterns:
    - "Ikkita mustaqil DoS yuzasi ikkita mustaqil darvozani talab qiladi va ULARNING TARTIBI test bilan o'lchanadi (natija emas, `load_workbook` CHAQIRILGANI)"
    - "Hujumchi yozgan metama'lumotga (`<dimension>`) tayangan chegara — chegara EMAS; sanoq ITERATSIYA paytida takrorlanadi va natija RO'YXATGA YIG'ILMAYDI"
    - "`get_settings()` routerdan CHAQIRILMAYDI — `SettingsDep` (`app.state`); birinchisi testda `ValidationError` beradi va prod'da ilova holatini chetlab o'tadi"
    - "Yuklama CHEGARALANGAN holda o'qiladi: `read_rows()` `len(raw)` ni tekshirganda baytlar allaqachon xotirada bo'lardi"
    - "Excel yozishda YAGONA matn yo'li (`_write_text`) — `write_string()` bilan; `write()` qochirishdan keyin ham formulani tiklardi"
    - "Shablon TILDA, parser POZITSIYA bo'yicha — va bu uchidan-uchiga test bilan qulflanadi (uchala til -> bir xil natija)"
    - "Matritsaga `multipart` marshruti qo'shilganda `FILE_FILLERS` YETMAYDI: uning yo'qligini KO'RSATADIGAN pozitiv da'vo ham kerak (o'lchandi — 307 test yashil qolardi)"

key-files:
  created:
    - services/core-api/app/services/__init__.py
    - services/core-api/app/services/xlsx_reader.py
    - services/core-api/app/services/import_validator.py
    - services/core-api/app/services/xlsx_template.py
    - services/core-api/app/repositories/import_repo.py
    - services/core-api/app/api/v1/imports.py
    - tests/unit/test_xlsx_reader.py
    - tests/unit/test_xlsx_template.py
    - tests/integration/test_stall_import.py
  modified:
    - pyproject.toml
    - services/core-api/pyproject.toml
    - services/core-api/uv.lock
    - services/core-api/app/settings.py
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/fixtures/admin_api.py
    - tests/fixtures/market_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "`defusedxml` ning HAQIQIY darvozasi — `openpyxl.DEFUSEDXML` bayrog'i (o'lchandi), rejadagi `defuse_stdlib()` emas; ikkalasi ham saqlandi, lekin test AYNAN bayroqni qulflaydi"
  - "`app/repositories/import_repo.py` REJADAN TASHQARI yaratildi — 02-09 konvensiyasi (routerlar SQL bajarmaydi) buni TALAB qiladi"
  - "`ON CONFLICT DO NOTHING` ATAYIN YOZILMADI — `stall_code_claim()` uni chetlab o'ta olmaydi va band yozish YOLG'ON kafolat berardi"
  - "Chetlangan kod `skipped` EMAS, 409 `import_conflict` — jimgina yo'qotish adminni chalg'itardi (D-02)"
  - "Til `users.locale` dan, so'rov parametridan EMAS — ikkinchi haqiqat manbai tug'ilmasin"
  - "Zona/toifa qidiruvi registrga SEZGIR EMAS, lekin NOANIQLIK xato bo'lib qoladi"
  - "Sotuvchi importida bo'sh sana `operating_since` ga tushadi (`business_today()` EMAS — o'tmish sotuvchisiz ko'rinardi)"
  - "`duplicate_code_in_file` sotuvchi faylida QAYTA ISHLATILADI (bitta rastaga ikki sotuvchi) — usiz EXCLUDE konstrayti QATOR RAQAMISIZ 409 berardi"

patterns-established:
  - "Pattern: chegara hujumchi E'LON QILGAN qiymatga tayansa, u chegara emas — haqiqiy sanoq lazy iteratsiya paytida bo'ladi"
  - "Pattern: darvozaning TARTIBI o'lchanadi (`load_workbook` chaqirilganmi), faqat NATIJASI emas"
  - "Pattern: yangi kontent tipi matritsaga qo'shilganda mexanizmning O'ZI uchun POZITIV darvoza yoziladi — aks holda u jimgina o'chib qoladi"

requirements-completed: []

# Metrics
duration: 150min
completed: 2026-08-01
---

# Phase 2 Plan 12: Excel import — Karmananing real ro'yxati kiradigan yo'l Summary

**Uch qatlamli import yo'li ochildi (chegaralangan o'qish -> ZIP/XML darvozalari -> yozishdan oldingi validatsiya) va yettita sabotaj o'lchovi darvozalarning kuchini aniq ko'rsatdi; ikkitasi rejaning ko'rmagan narsasini fosh qildi — `<dimension>` e'loni YO'Q faylda qator chegarasi xotira yeyilgandan KEYIN ishlardi (qatorlar `list()` ga yig'ilardi), `FILE_FILLERS` mexanizmi esa butunlay olib tashlanganda tenancy to'plamining 307 testi YASHIL qolardi, ya'ni ikkala import marshruti matritsada "bor" bo'lib turib endpoint mantiqini umuman ishga tushirmasdi.**

## Performance

- **Duration:** ~150 min
- **Tasks:** 3/3 (+1 sabotaj natijasidagi darvoza commit'i)
- **Files:** 19 (9 yaratildi, 10 o'zgartirildi), +4613 / −5
- **Testlar:** 778 → **885** (+107: unit +63, integratsiya +24, tenancy +20)
- **Marshrutlar:** matritsa 39 → **43** (`EXEMPT_ROUTES` uzunligi O'ZGARMADI — 14)
- **Xato kodlari:** 22 → **23** (`import_conflict`)

## Accomplishments

- **Yettita sabotaj o'lchovi va ularning aniq natijalari:**

  | Sabotaj | Yiqilgan test(lar) | Nazorat holati |
  |---|---|---|
  | ZIP darvozasi `_load()` dan KEYINGA ko'chirildi | AYNAN 2: `test_zip_bomb_is_rejected_before_parsing` (monkeypatch qilingan `load_workbook` CHAQIRILDI) va `test_too_many_zip_entries_is_rejected` | qolgan 24 unit testi ✅ — tartib HAQIQATAN yuk ko'taruvchi, natija esa emas |
  | Iteratsiya paytidagi qator sanog'i olib tashlandi | AYNAN 1: `test_missing_dimension_does_not_bypass_the_row_limit` | **`test_too_many_rows_is_rejected` ✅ YASHIL qoldi** — ya'ni e'lon qilingan `<dimension>` darvozasi YOLG'IZ O'ZI hech nima kafolatlamaydi |
  | `escape_formula()` yagona yozish yo'lidan olib tashlandi | AYNAN 7: oltala prefiks (`= + - @ \t \r`) + `test_error_report_escapes_the_message` | qolgan 30 test ✅ — ikkinchi yozish yo'li (xato hisoboti) mustaqil ravishda qamralgan |
  | D-15 skip (`existing_codes`) olib tashlandi | AYNAN 1: `test_existing_codes_are_skipped_not_reported` | qolgan 36 ✅ |
  | D-14 darvozasi (`_reject_if_invalid`) butunlay olib tashlandi | AYNAN 6 integratsiya testi | qolgan 18 ✅ |
  | **Qatorlar 422 dan OLDIN yozilib TASDIQLANDI** (status kodi TO'G'RI qoldi) | AYNAN 5, va `test_all_or_nothing` **`assert 9 == 6`** bilan — ya'ni javob `422` bo'lgani holda uchta qator jimgina yozilgan | uchala status assertion'i ✅ O'TDI — bu **sanoq assertion'ining yagona yuk ko'taruvchi ekanini** isbotlaydi |
  | `FILE_FILLERS` `call_route()` dan olib tashlandi | **0 (hech biri)** — 307 test YASHIL qoldi | ⚠ TESHIK: qarang "eng qimmat topilma" |

  Har yettitasidan keyin fayllar `git checkout` bilan **bit-ba-bit** tiklandi (`git status` toza, `git diff --stat` bo'sh).

- **Fazaning eng qimmat topilmasi — matritsa YANGI KONTENT TIPI oldida jimgina bo'shab qoladi.** `call_route()` dan `FILE_FILLERS` olib tashlanganda butun tenancy to'plami yashil qoldi. Sabab strukturaviy: JSON tanali so'rov `multipart/form-data` endpointida **422** beradi, 422 esa matritsaning birorta da'vosini buzmaydi — u `403` emas (tenant testi o'tadi), javobda B bozorining birorta identifikatori yo'q (sizish testi o'tadi) va tokensiz so'rov baribir `401` oladi. Ya'ni ikkala import marshruti ro'yxatda "qamralgan" bo'lib turib, endpoint mantiqi UMUMAN ishga tushmasdi. Bu 02-08 deviatsiya #4 (`BODY_FILLERS` ning o'zi tug'ilgan holat) bilan AYNAN bir xil sinf xato, faqat bir qavat yuqorida — tana MAVJUDLIGIDA emas, tana TIPIDA. Yechim mexanizmning o'zi emas, uning YO'QLIGINI ko'rsatadigan **pozitiv** da'vo: `test_file_routes_actually_execute` har bir fayl marshruti uchun javob `422` BILAN TUGAMASLIGINI talab qiladi. Qayta o'lchandi — filler bypass qilinganda AYNAN 2 test yiqiladi.

- **Ikkinchi qimmat topilma — hujumchi E'LON QILGAN chegara chegara emas.** `ws.max_row` faylning O'ZIDAGI `<dimension>` elementidan keladi. Uchta yolg'on shakli o'lchandi: e'lon KATTA (arzon rad etish ishlaydi), e'lon KICHIK (openpyxl e'londan ortiq qator qaytarmaydi — DoS emas, hujumchi faqat o'z ma'lumotini yo'qotadi) va **e'lon YO'Q** — o'shanda `max_row` `None` bo'ladi, birinchi darvoza jimgina o'tadi va butun varaq o'qiladi. Dastlabki yozuvda qatorlar `list(worksheet.iter_rows(...))` bilan yig'ilib, KEYIN sanalardi — ya'ni chegara xotira ALLAQACHON yeyilgandan keyin ishlardi. Test aynan shuni fosh qildi (`DID NOT RAISE`), yechim esa lazy iteratsiya (`_safe_rows`). Ikkinchi sabotaj bu ikkala testning HAR XIL narsani o'lchashini isbotladi: e'lon qilingan darvoza testi yashil qolib, faqat e'lonsiz holat qizardi.

- **`defusedxml` ning haqiqiy mexanizmi rejadagidan BOSHQA ekan — va u o'lchandi.** Reja "`defuse_stdlib()` import paytida chaqiriladi (`openpyxl` uni SHU YO'L BILAN oladi)" deydi. Konteynerda o'lchandi: openpyxl `defusedxml` ni O'RNATILGANLIGI bo'yicha aniqlaydi va `openpyxl.DEFUSEDXML = True` qo'yadi; `iterparse` HAM, `fromstring` HAM `defusedxml.common` dan keladi — ya'ni himoya bu modulning import TARTIBIGA umuman bog'liq emas. `defuse_stdlib()` saqlandi (u standart kutubxonaning boshqa XML yo'llarini qoplaydi), lekin **test AYNAN bayroqni qulflaydi** (`test_openpyxl_detected_defusedxml`): bayroq `False` bo'lib qolsa fayllar baribir o'qilaverardi va birorta test qizarmasdi. A9 smoke-testi uchta pozitsiyada o'lchandi (`sharedStrings.xml`, `sheet1.xml`, `workbook.xml`) — uchalasida ham rad etiladi, ya'ni `python-calamine` ga o'tish SHART EMAS.

- **D-14 ning yagona ishonchli o'lchovi — SANOQ, javob emas.** Oltinchi sabotaj buni to'g'ridan-to'g'ri isbotladi: qatorlar yozilib tasdiqlangandan keyin ham javob `422` bo'lib qoldi va `test_all_or_nothing` ning uchala **status** assertion'i O'TDI (`422`, `import_validation_failed`, qator raqamlari). Faqat `assert count_stalls(...) == before` qizardi (`9 == 6`). Ya'ni "422 keldi" degan da'vo bilan yozilgan test bu buzilishni UMUMAN ko'rmasdi.

- **Uchidan-uchiga: yuklab olingan shablonning O'ZI import qilinadi.** `test_downloaded_template_is_accepted_by_the_import` shablonni `GET` bilan oladi va uni o'zgartirmasdan `POST` qiladi — natija HAQIQIY rasta. Bu O-05 (shablon tilda, parser pozitsiyada) va A6 (ustunlar tartibi) ning eng kuchli isboti: ikkalasi bir kun ajralib ketsa AYNAN shu test qizaradi. Uchala til uchun esa unit darajasida `test_template_is_parsed_back_by_the_reader_in_every_locale` — uz-Latn, uz-Cyrl va ru shablonlari `read_rows()` dan AYNAN bir xil natija beradi.

## Task Commits

1. **Task 1: Xavfsiz `.xlsx` o'qish qatlami va uning hujum testlari** — `4a3d047` (feat)
2. **Task 2: Validator (yozishdan oldin) va shablon/xato-hisoboti generatori** — `021b1eb` (feat)
3. **Task 3: `imports.py` routeri va all-or-nothing / idempotentlik testlari** — `e9bc223` (feat)
4. **Sabotaj natijasi: `FILE_FILLERS` ni yuk ko'taruvchi qiladigan darvoza** — `bb0f701` (test)

## Files Created/Modified

**Yaratildi**

- `services/core-api/app/services/__init__.py` — yangi QATLAM: DB ga tegmaydigan sof domen servislari. Nega `repositories/` ga qo'shilmagani docstringda.
- `services/core-api/app/services/xlsx_reader.py` — `read_rows()`; ikkita mustaqil DoS yuzasi va ularning TARTIBI modul docstringida literal; `ReadLimits` (A7) `Settings` dan to'ladi; `_safe_rows()` lazy iteratsiya.
- `services/core-api/app/services/import_validator.py` — sof funksiyalar; Pitfall 4 ning empirik matni docstringda; `_fold_index()` registrsiz qidiruv (noaniqlik xato bo'lib qoladi).
- `services/core-api/app/services/xlsx_template.py` — `escape_formula()` + YAGONA yozish yo'li (`_write_text` → `write_string`); uch tilli sarlavhalar; yashirin ma'lumotnoma varag'i + `data_validation`.
- `services/core-api/app/repositories/import_repo.py` — **rejadan tashqari** (deviatsiya #1): olti lug'at so'rovi + ikkita ommaviy `INSERT ... RETURNING`.
- `services/core-api/app/api/v1/imports.py` — to'rtta marshrut; tranzaksiya boshqaruvi UMUMAN yo'q (grep darvozasi: 0); `_read_bounded()` chegaralangan o'qish.
- `tests/unit/test_xlsx_reader.py` — 26 test (reja ≥9 talab qiladi).
- `tests/unit/test_xlsx_template.py` — 37 test (reja ≥5 talab qiladi).
- `tests/integration/test_stall_import.py` — 24 test (reja ≥9 talab qiladi).

**O'zgartirildi**

- `pyproject.toml` — uchta paket uchun `ignore_missing_imports` (uchalasida ham `py.typed` YO'Q — o'lchandi).
- `services/core-api/pyproject.toml` + `uv.lock` — `openpyxl==3.1.5`, `defusedxml==0.7.1`, `XlsxWriter==3.2.9` (+ `et-xmlfile` tranzitiv).
- `services/core-api/app/settings.py` — oltita import chegarasi (A7).
- `services/core-api/app/schemas.py` — `import_conflict` kodi (22 → 23), `ImportErrorReportRequest`, `IMPORT_ERROR_REPORT_MAX`.
- `services/core-api/app/main.py` — `imports_router`; izohda `FILE_FILLERS` sababi.
- `tests/fixtures/admin_api.py` — to'rtta URL konstantasi.
- `tests/fixtures/market_domain.py` — `A_CATEGORY_NAMES` eksport qilindi (02-08 deviatsiya #8 naqshi).
- `tests/tenancy/test_cross_tenant.py` — `FILE_FILLERS`, `call_route()` kengaytmasi, uchta meta-test.
- `tests/tenancy/test_route_coverage.py` — `MINIMUM_MATRIX_ROUTES` 31 → 34.

## Decisions Made

- **`app/repositories/import_repo.py` REJADAN TASHQARI yaratildi.** Reja `files_modified` da repozitoriy fayli yo'q, lekin 02-09 konvensiyasi ("routerlar SQL bajarmaydi") va topshiriq eslatmasi buni TALAB qiladi. Mavjud repozitoriylarning birortasi ham to'g'ri kelmadi: `ZoneRepository.list_zones()` har zonaga rasta SANOG'ini qo'shadi, `CategoryRepository.list_categories()` bugungi TARIFNI hisoblaydi va `today` talab qiladi, `StallRepository` esa bittalab yozadi (1000 qatorli faylda 1000 borish-kelish).
- **`ON CONFLICT DO NOTHING` ATAYIN yozilmadi.** RESEARCH Code Example 3 uni ko'rsatadi, lekin `stall_code_claim()` `BEFORE INSERT` triggeri konfliktdan OLDIN ishga tushadi va `ON CONFLICT` bandi uni CHETLAB O'TA OLMAYDI (02-05). Bandni yozish "mavjud kodlar jimgina o'tkazib yuboriladi" degan YOLG'ON kafolat berardi; haqiqiy skip validatorda, yozishdan oldin.
- **Chetlangan kod `skipped` EMAS — 409 `import_conflict`.** `existing_stall_codes()` FAQAT tirik rastalarni beradi. Muqobil (chetlangan kodlarni ham "mavjud" deb o'tkazib yuborish) faylda qolgan eski raqamni foydalanuvchiga KO'RSATMASDAN yo'q qilardi — admin uni import qilindi deb o'ylab yurardi. 409 esa D-02 haqiqatini ko'rsatadi. Tranzaksiya butunlay orqaga qaytadi, ya'ni D-14 buzilmaydi.
- **Til `users.locale` dan olinadi, so'rov parametridan EMAS.** Reja `principal.locale` deydi, lekin `Principal` da bunday maydon yo'q. Parametr sifatida qabul qilish ikkinchi haqiqat manbai tug'dirardi (admin interfeysi bir tilda, shabloni boshqa tilda). Profil `PATCH /me/locale` bilan o'zgaradi va u yagona manba.
- **Zona/toifa qidiruvi registrga SEZGIR EMAS, lekin NOANIQLIK xato bo'lib qoladi.** `zones.name` unikaligi registrga sezgir, ya'ni faqat aniq mos kelishga tayanish 1000 qatorlik `zone_not_found` to'foni berardi ("zona ro'yxatda turibdi-ku?"). Lekin `Sabzavot` va `SABZAVOT` ikkalasi ham mavjud bo'lsa taxmin QILINMAYDI — bunday kalit indeksdan chiqariladi va qator `zone_not_found` oladi.
- **`duplicate_code_in_file` sotuvchi faylida QAYTA ISHLATILADI.** Bitta rastaga ikki sotuvchi — sotuvchi faylidagi eng ehtimolli xato. Usiz u `ex_stall_assignments_no_overlap` ga urilib, QATOR RAQAMISIZ 409 berardi va D-14 aynan shuni taqiqlaydi. Yangi kod o'ylab topilmadi: mavjud kodning ma'nosi ("fayl ichida takroriy kod") bu holatga aynan to'g'ri keladi.
- **`_reject_if_invalid()` javobni DTO'dan quradi.** `HTTPException(detail={...})` javobni `{"detail": {"detail": ..., "errors": [...]}}` shaklida o'raydi — 02-11 dagi `blocking[]` bilan AYNAN bir xil holat. Bu yerda o'ram QABUL QILINDI (klient `response.json()["detail"]["errors"]` ni o'qiydi) va u `test_error_report_round_trip` bilan qulflandi; `ImportErrorResponse` DTO'si esa tananing ICHKI shaklini belgilaydi.
- **`defuse_stdlib()` ning `DeprecationWarning` i NARROW so'ndirildi.** `defusedxml` 0.7.1 manbasida `with warnings.catch_warnings(): from . import cElementTree` yozilgan, lekin `simplefilter("ignore")` TUSHIB QOLGAN (upstream xatosi, manba o'qildi). So'ndirish AYNAN shu chaqiruv atrofida va AYNAN shu toifada — global filtr qo'yilmadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Router SQL bajarishi kerak bo'lardi — repozitoriy fayli rejada YO'Q**

- **Found during:** Task 3
- **Issue:** Reja `files_modified` da birorta repozitoriy fayli yo'q, lekin import oqimiga olti lug'at so'rovi va ikkita ommaviy yozuv kerak. Ularni routerga yozish 02-09 da o'rnatilgan konvensiyani ("routerlar SQL bajarmaydi") va topshiriq eslatmasini bevosita buzardi.
- **Fix:** `app/repositories/import_repo.py` — `ImportRepository`. Mavjud repozitoriylarning birortasi NEGA to'g'ri kelmagani modul docstringida uchta band bilan yozildi.
- **Files modified:** `services/core-api/app/repositories/import_repo.py`
- **Verification:** `ruff check . && mypy .` exit 0; 24 integratsiya testi yashil
- **Committed in:** `e9bc223`

**2. [Rule 1 - Bug] Qator chegarasi xotira YEYILGANDAN KEYIN ishlardi**

- **Found during:** Task 1
- **Issue:** Dastlabki yozuv `list(worksheet.iter_rows(values_only=True))` bilan qatorlarni RO'YXATGA yig'ib, keyin sanardi. `<dimension>` e'loni YO'Q faylda (`ws.max_row` `None`) e'lon darvozasi jimgina o'tadi va butun varaq o'qiladi — ya'ni chegara xotira ALLAQACHON yeyilgandan keyin ishlardi (T-02-89 ning bevosita bypassi). Reja faqat e'lon qilingan qiymatga tayanadi.
- **Fix:** `_safe_rows()` — lazy generator; sanoq har qatorda va natija HECH QACHON ro'yxatga yig'ilmaydi. `StopIteration` qo'lda ushlanadi (PEP 479).
- **Files modified:** `services/core-api/app/services/xlsx_reader.py`
- **Verification:** `test_missing_dimension_does_not_bypass_the_row_limit` (dastlab `DID NOT RAISE` bilan yiqilgan) + nazorat `test_missing_dimension_still_reads_a_valid_file`; **sabotaj #2** — sanoq olib tashlanganda AYNAN u qizardi, `test_too_many_rows_is_rejected` esa YASHIL qoldi
- **Committed in:** `4a3d047`

**3. [Rule 3 - Blocking] `get_settings()` routerda testni yiqitardi va prod'da ilova holatini chetlab o'tardi**

- **Found during:** Task 3
- **Issue:** Reja chegaralarni `app/settings.py` dan olishni buyuradi; tabiiy chaqiruv — `get_settings()`. Lekin u `lru_cache` bilan MUHITDAN o'qiydi, integratsiya testi esa faqat `app.state.settings` ni almashtiradi (`main.py` modul docstringi buni literal talab qiladi). Natija o'lchandi: AYNAN 2 matritsa testi `3 validation errors for Settings` bilan qulagan. Prod'da esa `lifespan` bergan sozlama bilan endpoint ko'rgan sozlama ajralib ketishi mumkin edi.
- **Fix:** `SettingsDep` (`deps.get_settings_dep`) — u aynan shu maqsad uchun mavjud. `_read_bounded()` va `_read()` sozlamani ARGUMENT sifatida oladi.
- **Files modified:** `services/core-api/app/api/v1/imports.py`
- **Verification:** `pytest tests/tenancy` — 307 passed
- **Committed in:** `e9bc223`

**4. [Rule 2 - Missing Critical] Fayl chegaraga YETIB BORMASDAN xotiraga to'liq olinardi**

- **Found during:** Task 3
- **Issue:** Reja `read_rows()` ning `len(raw) > MAX_UPLOAD_BYTES` darvozasini yagona hajm himoyasi deb belgilaydi. Lekin router `await file.read()` qilishi kerak — ya'ni 4 GB lik yuklama chegaraga yetib bormasdan konteynerni o'ldirardi. Darvoza mavjud bo'lib turib, u himoya qilmoqchi bo'lgan holatdan KEYIN ishlardi.
- **Fix:** `_read_bounded()` — 64 KB bo'laklar bilan o'qiydi va chegaradan oshgan zahoti to'xtaydi (qolgan baytlar UMUMAN o'qilmaydi). `read_rows()` ning o'z darvozasi QOLDIRILDI (ikkinchi qatlam); ikkalasining ajratmasi funksiya docstringida.
- **Files modified:** `services/core-api/app/api/v1/imports.py`
- **Verification:** `test_oversized_file_returns_422`
- **Committed in:** `e9bc223`

**5. [Rule 2 - Missing Critical] Bo'sh matnli katak `empty_code` darvozasidan JIMGINA o'tardi**

- **Found during:** Task 2
- **Issue:** `_at()` faqat indeks chegarasini tekshirardi. `""` qiymati "to'ldirilgan" deb hisoblanardi va `empty_code` xatosi UMUMAN chiqmasdi — bo'sh kodli rasta bazaga yozilardi. Test buni fosh qildi (`empty_code` xatolar ro'yxatida yo'q edi).
- **Fix:** `_at()` bo'sh va faqat bo'sh joydan iborat matnni ham `None` ga keltiradi. O'quvchi qatlam buni allaqachon qiladi, lekin takrorlash validatorni undan MUSTAQIL qiladi (sabab docstringda).
- **Files modified:** `services/core-api/app/services/import_validator.py`
- **Verification:** `test_every_error_in_a_row_is_reported_at_once` — to'rtala kod ham ro'yxatda
- **Committed in:** `021b1eb`

**6. [Rule 2 - Missing Critical] Bitta rastaga ikki sotuvchi QATOR RAQAMISIZ 409 berardi**

- **Found during:** Task 2
- **Issue:** Reja sotuvchi validatori uchun `stall_not_found` ni belgilaydi, lekin FAYL ICHIDA bir xil rasta kodining takrorlanishini ko'rmaydi. Bu sotuvchi faylidagi eng ehtimolli xato va u `ex_stall_assignments_no_overlap` ga urilib, D-14 taqiqlagan shaklda (qator raqamisiz 409) chiqardi.
- **Fix:** `duplicate_code_in_file` kodi QAYTA ISHLATILADI ("fayl ichida takroriy kod" ma'nosi aynan to'g'ri keladi); xabarda IKKALA qator raqami.
- **Files modified:** `services/core-api/app/services/import_validator.py`
- **Verification:** `test_vendor_stall_code_must_exist_and_is_unique_in_the_file`
- **Committed in:** `021b1eb`

**7. [Rule 2 - Missing Critical] `POST /imports/errors.xlsx` o'z-o'ziga DoS bo'lardi**

- **Found during:** Task 3
- **Issue:** Reja "kirish uzunligi `MAX_ROWS` bilan cheklanadi" deydi, lekin `MARKET_ERROR_CODES` da ham, DTO to'plamida ham bunday model yo'q. Chegarasiz endpoint o'nlab million elementli massiv bilan o'nlab million qatorli fayl qurdirardi — kirish MAHSULOT yo'lidan kelmaydi, u 422 javobining NUSXASI.
- **Fix:** `ImportErrorReportRequest` + `IMPORT_ERROR_REPORT_MAX = 5000` (`xlsx_reader.MAX_ROWS` bilan AYNAN bir xil). Cheklov `Field(max_length=...)` orqali, ya'ni Pydantic darajasida.
- **Files modified:** `services/core-api/app/schemas.py`, `services/core-api/app/api/v1/imports.py`
- **Verification:** `test_error_report_rejects_an_oversized_list`
- **Committed in:** `e9bc223`

**8. [Rule 3 - Blocking] `import_conflict` xato kodi `MARKET_ERROR_CODES` da YO'Q edi**

- **Found during:** Task 3
- **Issue:** Reja 409 `import_conflict` javobini AYTADI (Task 3 action, 6-band), lekin 02-08 qotirgan to'plamda kod yo'q. Ro'yxatning O'ZI hujjat ("bu fazada nima noto'g'ri ketishi mumkin") va frontend ko'zgusining manbai.
- **Fix:** `import_conflict` qo'shildi (22 → **23**) va `import_validation_failed` dan NEGA ajratilgani izohda: birinchisi qator raqami bilan keladi va `errors[]` massivi bor, ikkinchisi hech qanday qator ko'rsatmaydi.
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `test_retired_code_is_reported_not_silently_skipped` javobni AYNAN `{"detail": "import_conflict"}` bilan solishtiradi
- **⚠ Qarz:** `frontend/src/lib/api-types.ts::ERROR_CODES` endi 23 kod kutadi (02-13/02-14 yopadi)
- **Committed in:** `e9bc223`

**9. [Rule 2 - Missing Critical] `FILE_FILLERS` mexanizmi JIMGINA o'chib qolishi mumkin edi**

- **Found during:** Task 3 dan keyingi sabotaj o'lchovi
- **Issue:** Mexanizm o'zi to'g'ri, lekin uning YO'QLIGINI hech nima ko'rsatmasdi: `call_route()` dan olib tashlanganda tenancy to'plamining 307 testi YASHIL qoldi. JSON tanali so'rov multipart endpointida 422 beradi, 422 esa matritsaning birorta da'vosini buzmaydi (403 emas, sizish yo'q, 401 baribir keladi). Ya'ni ikkala import marshruti ro'yxatda "qamralgan" bo'lib turib, endpoint mantiqi UMUMAN ishlamasdi.
- **Fix:** `test_file_routes_actually_execute` — POZITIV da'vo: javob 422 BILAN TUGAMASLIGI shart. Aniq status kodi ATAYIN qulflanmaydi (200 ham, 409 ham qonuniy — matritsa qatorlarni HAQIQATAN yozadi); yagona ma'noli da'vo — yuklama QABUL QILINDI. `test_file_and_body_fillers_do_not_overlap` esa ikkinchi teshikni yopadi (kesishuvda `BODY_FILLERS` yozuvi jimgina e'tiborsiz qolardi).
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** **Sabotaj #7 QAYTA o'lchandi** — filler bypass qilinganda endi AYNAN 2 test yiqiladi (ilgari 0 edi)
- **Committed in:** `bb0f701`

**10. [Rule 1 - Bug] Reja `defusedxml` ning ULANISH MEXANIZMINI noto'g'ri ta'riflaydi**

- **Found during:** Task 1
- **Issue:** Reja "`defusedxml.defuse_stdlib()` import paytida chaqiriladi (`openpyxl` uni SHU YO'L BILAN oladi)" deydi. O'lchov buni rad etdi: openpyxl paketni O'RNATILGANLIGI bo'yicha aniqlaydi va `iterparse` HAM, `fromstring` HAM `defusedxml.common` dan keladi — chaqiruvdan MUSTAQIL. Rejaga literal ergashish "himoya `defuse_stdlib()` da" degan yolg'on ishonch qoldirardi va kimdir uni olib tashlaganda hech nima qizarmasdi (chunki himoya boshqa joydan keladi), lekin TESKARI holatda (paket `pyproject.toml` dan tushib qolsa) ham hech nima qizarmasdi.
- **Fix:** Chaqiruv SAQLANDI (u standart kutubxonaning boshqa XML yo'llarini qoplaydi va zarari yo'q), lekin test AYNAN haqiqiy darvozani qulflaydi: `test_openpyxl_detected_defusedxml` `openpyxl.DEFUSEDXML is True` va ikkala funksiyaning modulini tekshiradi. O'lchov natijasi modul docstringiga literal yozildi.
- **Files modified:** `services/core-api/app/services/xlsx_reader.py`, `tests/unit/test_xlsx_reader.py`
- **Verification:** A9 smoke-testi uchta XML pozitsiyasida (`sharedStrings.xml`, `sheet1.xml`, `workbook.xml`) — uchalasi ham rad etiladi
- **Committed in:** `4a3d047`

**11. [Rule 1 - Bug] Bo'sh qatorlar va Excel tiplari TO'G'RI faylni ham rad etardi**

- **Found during:** Task 1
- **Issue:** Uchta mustaqil holat, uchalasi ham real fayllardan keladi va uchalasi ham D-14 (all-or-nothing) tufayli BUTUN faylni qaytarib yuborardi: (a) Excel eksportidagi formatlangan bo'sh qatorlar har biriga `empty_code` xatosi berardi; (b) `str(datetime)` `"2026-08-01 00:00:00"` beradi va `date.fromisoformat()` uni rad etardi; (c) Excel butun sonni ba'zan `12.0` qilib qaytaradi va `str()` `"12.0"` berardi — rasta kodi bazadagi `"12"` bilan mos tushmasdi, ya'ni D-15 idempotentligi buzilardi.
- **Fix:** Bo'sh qatorlar TASHLANADI (raqamlash SURILMAYDI); `_cell_text()` sana, butun qiymatli float va `bool` ni aniq matnga keltiradi.
- **Files modified:** `services/core-api/app/services/xlsx_reader.py`
- **Verification:** `test_blank_rows_are_skipped_but_numbering_is_preserved`, `test_cell_values_are_normalised` (4 holat), `test_date_cells_become_iso_dates` (2 holat)
- **Committed in:** `4a3d047`

**12. [Rule 1 - Bug] `_quote_sheet_name()` — apostrofli varaq nomi `data_validation` ni jimgina buzardi**

- **Found during:** Task 2
- **Issue:** Ma'lumotnoma varag'ining nomi `Ma'lumotnoma` — ichida APOSTROF bor. Qo'shtirnoqsiz formula havolasi (`=Ma'lumotnoma!$A$2:$A$4`) Excelda buzilardi va ochiluvchi ro'yxat KO'RINMASDI, lekin fayl "to'g'ri" bo'lib ochilaverardi — ya'ni Open Question 5 ning yechimi jimgina ishlamay qolardi.
- **Fix:** `_quote_sheet_name()` — nom qo'shtirnoqqa olinadi va ichki apostrof ikkilantiriladi (Excel formulasining O'Z qoidasi).
- **Files modified:** `services/core-api/app/services/xlsx_template.py`
- **Verification:** `test_template_binds_data_validation_to_the_reference_sheet` havolaning `'Ma''lumotnoma'!` bilan boshlanishini talab qiladi
- **Committed in:** `021b1eb`

---

**Total deviations:** 12 auto-fixed (3 blocking, 5 missing-critical, 4 bug). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Sxemaga UMUMAN tegilmadi (`alembic_version` `0010` bo'lib qoladi; `migrations/` va `frontend/` teginilmadi) va rejadan tashqari endpoint ochilmadi. Uchta qamrov kengaytmasi: bitta yangi fayl (`import_repo.py` — konvensiya talabi), bitta xato kodi (`import_conflict`, 22 → 23) va matritsaga YANGI tushuncha (`FILE_FILLERS`). #1, #3, #8 va #10 rejaning O'Z bandlari bilan haqiqat orasidagi ziddiyatlar; #2, #4, #5, #6, #7 va #9 reja ko'rmagan olti yo'lni yopadi va ikkitasi sabotaj bilan o'lchandi; #11 va #12 real fayllardan keladigan holatlar.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `openpyxl.DEFUSEDXML` | ✅ `True` |
| `openpyxl.xml.functions.iterparse.__module__` | ✅ `defusedxml.common` |
| `openpyxl.xml.functions.fromstring.__module__` | ✅ `defusedxml.common` (reja faqat `iterparse` ni kutgan) |
| `defuse_stdlib()` py3.13 da | ✅ ishlaydi; `ET.XMLParser` → `defusedxml.ElementTree.DefusedXMLParser` |
| Billion-laughs — `sharedStrings.xml` / `sheet1.xml` / `workbook.xml` | ✅ UCHALASI ham `ValueError: Unable to read workbook: ...` |
| `EntitiesForbidden` ni to'g'ridan-to'g'ri ushlash | ❌ MUMKIN EMAS — openpyxl uni O'Z `ValueError` iga o'raydi |
| Zip-bomba (20 MB nol → ~20 KB) | ✅ `file_too_large`, `load_workbook` CHAQIRILMAGAN |
| `<dimension ref="A1:A1"/>` (yolg'on KICHIK e'lon) | ✅ DoS EMAS — openpyxl e'londan ortiq qator qaytarmaydi |
| `<dimension>` e'loni YO'Q + 10 qator, chegara 5 | ✅ `file_too_complex` (lazy sanoq bilan) |
| `py.typed` — openpyxl / xlsxwriter / defusedxml | ✅ uchalasida ham YO'Q → `ignore_missing_imports` |
| Sana katagi FORMATSIZ | ⚠ `46235` (seriya raqami) — format bilan `2026-08-01` |
| `12.0` → matn | ✅ `"12"` (`str()` `"12.0"` berardi) |
| Formula katagi (`data_only=True`) | ✅ hisoblangan qiymat (`"2"`), formula matni EMAS |
| `\r` prefiksi faylda | ⚠ `'_x000D_=...` — qochirish ISHLADI, OOXML uni kodlaydi |
| Shablon → `read_rows()` (uz-Latn / uz-Cyrl / ru) | ✅ UCHALASI ham AYNAN bir xil natija, `row == 2` |
| Yuklab olingan shablonni import qilish | ✅ **200**, `inserted: 1` (namunaviy kod `"1"` seed'da YO'Q) |
| Aralash fayl (3 to'g'ri + 3 xato) | ✅ **422**, qatorlar `{5, 6, 7}`, `stalls` sanog'i O'ZGARMADI |
| `error_counts` guruhlash | ✅ `{"zone_not_found": 2, "category_not_found": 1}` |
| Ikkinchi ma'lumot qatorining raqami | ✅ **3** (sarlavha = 1) |
| Qayta import | ✅ `{inserted: 0, skipped: 3}`; `stalls` HAM, `stall_category_periods` HAM o'zgarmadi |
| Qisman qayta import (+2 yangi) | ✅ `{inserted: 2, skipped: 3}` |
| Sotuvchi qayta importi | ✅ `{inserted: 0, skipped: 1}`; biriktirishlar soni O'ZGARMADI |
| Chetlangan kod | ✅ **409** `import_conflict`; javobda `duplicate key` YO'Q; sanoq o'zgarmadi |
| Import qilingan rastaning toifa davri | ✅ `valid_from = A_OPERATING_SINCE` (2026-01-15) |
| Import qilingan biriktirish | ✅ `lower = operating_since`, `upper IS NULL` (OCHIQ davr) |
| Telefon `"90 991 00 03"` | ✅ `+998909910003` javobda ham, `GET /vendors` da ham |
| 5 MB + 1 bayt | ✅ **422** `file_too_large` |
| `.csv` / `.xlsx` deb nomlangan PDF | ✅ ikkalasi ham **422** `unsupported_file_type` |
| B bozorining zona nomi | ✅ `zone_not_found`; noma'lum nom bilan `error_counts` AYNAN teng |
| Faylda `market_id` ustuni | ✅ A da 1 qator, B da **0** qator (ikki tomonlama) |
| Direktor — `stalls` / `vendors` / `template` | ✅ uchalasi **403**; admin **200** (nazorat) |
| Tokensiz + fayl | ✅ **401** (422 EMAS) |
| `?kind=payments` | ✅ **422** (`Literal` tipi) |
| `errors.xlsx` 5001 element | ✅ **422** |
| `grep "session.begin()\|begin_nested" imports.py` | ✅ **0** |
| OpenAPI'dagi import yo'llari | ✅ 4 yo'l / 4 marshrut |
| `MARKET_ERROR_CODES` uzunligi | ✅ **23** (22 + `import_conflict`) |
| Cross-tenant matritsasi | ✅ 39 → **43**; `EXEMPT_ROUTES` uzunligi O'ZGARMADI (**14**) |
| `PARAM_FILLERS` / `BODY_FILLERS` / `FILE_FILLERS` | ✅ 9 / 16 / 2 |
| `git diff --name-only -- migrations/ frontend/` | ✅ BO'SH |

## Issues Encountered

- **`.env` worktree'da yo'q** (gitignore), ya'ni `npm run migrate` ishlamaydi. Ekvivalent qamrov o'zgarmadi: `migrated` fixture'i AYNAN `alembic upgrade head` ni `alembic.command` API'si bilan, `sbozor_owner` roli bilan va haqiqiy `postgres:18.4-trixie` konteynerida bajaradi — 885 testning har birida.
- **Konteyner IMAJI QAYTA QURILISHI shart.** Uchta yangi paket qo'shildi, ya'ni `docker compose --profile test build tests` bajarilmasa butun to'plam `ModuleNotFoundError: openpyxl` bilan yiqiladi. `uv.lock` ham yangilandi (`uv lock --project services/core-api`) — `--frozen` bilan sync qiladigan Dockerfile aks holda qurilmaydi.
- **`defusedxml` 0.7.1 upstream `DeprecationWarning` chiqaradi** va uni O'ZI so'ndirmoqchi bo'lib, `simplefilter("ignore")` ni tushirib qoldirgan. Bu A9 xavfining ("paket 2021-yilgi") aniq ko'rinishi — funksional muammo emas, lekin so'ndirilmasa har ishga tushishda jurnalga yolg'on signal qo'shardi.
- **`ruff format` uchta test faylini qayta formatladi** (uzun `replace_zip_entry(...)` va `ImportIssue(...)` chaqiruvlari) — qator uzunligi darajasida.
- **`HTTP_422_UNPROCESSABLE_ENTITY` Starlette'da ESKIRGAN** va u har 422 javobda `StarletteDeprecationWarning` chiqardi. Kod bazasi allaqachon RFC 9110 nomini (`..._CONTENT`) ishlatadi — to'rtta chaqiruv unga to'g'rilandi.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, birorta endpoint `NotImplementedError` qoldirmagan va birorta DTO bo'sh qolmagan.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `frontend/src/lib/api-types.ts::ERROR_CODES` da 2-fazaning **23** kodi YO'Q | 02-13 / 02-14 | Bu reja BITTA kod qo'shdi (`import_conflict`), qarz 22 dan 23 ga o'sdi |
| Import paneli (4 holat, guruhlangan xatolar, `.xlsx` yuklab olish) | 02-16 | Server kontrakti TO'LIQ: `errors[]` + `error_counts{}` + `POST /imports/errors.xlsx` round-trip testi bilan qulflangan |
| `MAX_SHEETS` / `MAX_ZIP_ENTRIES` STANDART qiymatlari test bilan qamralmagan | — | Mexanika toraytirilgan chegara bilan o'lchandi; standart QIYMATLAR `test_default_limits_match_the_documented_values` bilan qulflangan |
| `import_conflict` ning POYGA yo'li (ikki admin bir vaqtda) test bilan qamralmagan | — | Chetlangan kod yo'li AYNAN o'sha kodni beradi va u qamralgan; haqiqiy poygani deterministik sinash ikkita parallel tranzaksiya talab qiladi |
| Sotuvchi shablonida rasta kodi ro'yxati YO'Q | — | ATAYIN: minglab element ochiluvchi ro'yxatga aylanganda fayl foydasiz kattalashardi (sabab `_reference_sheet` docstringida) |
| `.xlsx` dan boshqa format (`.csv`, `.ods`) | — | D-13 faqat Excel'ni belgilaydi; `unsupported_file_type` ikkalasini ham rad etadi |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA bitta yuza aniqlandi va u YOPILDI (deviatsiya #4):

| Flag | File | Description |
|------|------|-------------|
| threat_flag: denial_of_service | `services/core-api/app/api/v1/imports.py` | Fayl `read_rows()` ning hajm darvozasiga YETIB BORMASDAN xotiraga to'liq olinardi (`await file.read()`). Reja bu yo'lni umuman ko'rmaydi — u chegara `read_rows()` da deb hisoblaydi. `_read_bounded()` bilan yopildi |

| Threat ID | Holat |
|-----------|-------|
| T-02-87 | mitigate — `openpyxl.DEFUSEDXML` bayrog'i test bilan qulflandi (**haqiqiy darvoza**, deviatsiya #10); A9 smoke-testi UCHTA XML pozitsiyasida; `python-calamine` ga o'tish sharti test docstringida |
| T-02-88 | mitigate — ochilgan hajm `zf.infolist()` bilan parse'dan OLDIN. **Sabotaj #1 bilan o'lchandi**: darvoza parse'dan keyinga ko'chirilganda `load_workbook` CHAQIRILDI va test aynan shu faktni ushladi |
| T-02-89 | mitigate — `read_only=True` + oltita sozlanadigan chegara + **iteratsiya paytidagi sanoq** (deviatsiya #2) + `_read_bounded()` (deviatsiya #4). **Sabotaj #2 bilan o'lchandi**: e'lon darvozasi yolg'iz o'zi yetmaydi |
| T-02-90 | mitigate — qator chegarasi 5000; bitta tranzaksiya, batching yo'q. Import testlari 3–5 qatorda millisekundlarda tugaydi |
| T-02-91 | mitigate — `escape_formula()` + YAGONA yozish yo'li (`_write_text` → `write_string`). **Sabotaj #3 bilan o'lchandi**: AYNAN 7 test yiqildi (oltala prefiks + xato hisobotining mustaqil yo'li) |
| T-02-92 | mitigate — tranzaksiya `TenantSessionDep` dan (grep: 0). **Sabotaj #6 bilan o'lchandi**: qatorlar tasdiqlanganda javob HAMON 422 bo'lib qoldi va faqat SANOQ assertion'i qizardi (`9 == 6`) |
| T-02-93 | mitigate — D-15 validatorda; upsert yo'li umuman yozilmagan. `test_reimport_does_not_touch_the_vendor_history` biriktirishlar sonini ham tekshiradi. **Sabotaj #4 bilan o'lchandi** |
| T-02-94 | mitigate — lug'atlar `TenantSessionDep` ostida RLS bilan; `test_cross_tenant_zone_name_is_not_found` javobni NOMA'LUM nom bilan solishtiradi (mavjudlik oshkor bo'lmaydi) |
| T-02-95 | mitigate — validatsiya yozishdan oldin; `IntegrityError` → 409 `import_conflict`, xom matn faqat log'ga (`assert "duplicate key" not in response.text`) |
| T-02-96 | mitigate — `require_permission(STALL_MANAGE / VENDOR_MANAGE)`; direktor UCHALA marshrutda ham 403, admin 200 (nazorat) |
| T-02-97 | mitigate — `ImportErrorReportRequest.errors` `max_length=5000` (deviatsiya #7); `test_error_report_rejects_an_oversized_list` |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (129 fayl) |
| 2 | `pytest tests/unit -q` | ✅ (to'liq to'plam ichida; +63) |
| 3 | `pytest tests/integration -q` | ✅ (to'liq to'plam ichida; +24) |
| 4 | `pytest tests/tenancy` | ✅ **309 passed** (02-11 dagi 289 + 20) |
| 5 | `pytest` (to'liq) | ✅ **885 passed** (02-11 dagi 778 + 107) |
| 6 | `uv lock --project services/core-api` | ✅ `Added defusedxml / et-xmlfile / openpyxl / xlsxwriter` |
| 7 | `app.openapi()` da import yo'llari | ✅ 4 yo'l / 4 marshrut |
| 8 | Sabotaj o'lchovlari (7 ta) | ✅ oltitasida AYNAN kutilgan test(lar) yiqildi; yettinchisi TESHIKNI fosh qildi va u yopilgandan keyin QAYTA o'lchandi |
| 9 | Sabotajdan keyin tiklash | ✅ `git status` toza, `git diff --stat` bo'sh |

**Task 1 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| Uchta paket pin qilingan | ✅ `openpyxl==3.1.5`, `defusedxml==0.7.1`, `XlsxWriter==3.2.9` |
| `pytest tests/unit/test_xlsx_reader.py` ≥9 test | ✅ **26** |
| `test_zip_bomb_...` `load_workbook` chaqirilmaganini tasdiqlaydi | ✅ (sabotaj #1 bilan qayta o'lchandi) |
| `test_row_numbers_match_excel` uchinchi qator `row == 4` | ✅ `[2, 3, 4]` |
| `defusedxml` import qilingan; `read_only=True, data_only=True` | ✅ ikkalasi ham |
| Chegaralar `app/settings.py` orqali qayta yoziladi (A7) | ✅ `test_limits_can_be_overridden_from_settings` |
| `test_valid_file_is_read` (nazorat) | ✅ |
| `ruff check . && mypy .` | ✅ exit 0 |

**Task 2 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `pytest tests/unit/test_xlsx_template.py` ≥5 test | ✅ **37** |
| Oltita prefiks uchun ham yashil | ✅ (sabotaj #3 bilan o'lchandi) |
| `existing_codes` xato ro'yxatiga TUSHMAYDI va natijadan chiqariladi | ✅ ikkala da'vo alohida |
| `duplicate_code_in_file` da ikkala qator raqami | ✅ `"88-qator: 12 raqami 14-qatorda ham bor"` |
| `zone_not_found` formati | ✅ `"14-qator: 'Sabzavot' zonasi topilmadi"` |
| Barcha yozish yo'llari `escape_formula()` dan o'tadi | ✅ YAGONA yo'l (`_write_text`), sabotaj bilan tasdiqlandi |
| Ikkinchi varaq yashirin + `data_validation` | ✅ `sheet_state == "hidden"`, ikkita ro'yxat bog'langan |
| `ruff check . && mypy .` | ✅ exit 0 |

**Task 3 qabul mezonlari (o'lchangan):**

| Mezon | Natija |
|-------|--------|
| `pytest tests/integration/test_stall_import.py` ≥9 test | ✅ **24** |
| `test_all_or_nothing` sanoqni oldin/keyin solishtiradi | ✅ (sabotaj #6 bilan o'lchandi — YAGONA yuk ko'taruvchi assertion) |
| `test_reimport_is_idempotent` `inserted == 0`, `skipped == N` | ✅ `{inserted: 0, skipped: 3}` |
| 422 tanasida `errors[]` va `error_counts{}` | ✅ ikkalasi ham |
| `grep "session.begin()\|begin_nested" imports.py` | ✅ **0** |
| OpenAPI'da uchala yo'l | ✅ to'rttasi ham |
| Direktor tokeni → 403 | ✅ uchala marshrutda |
| `pytest tests/tenancy` exit 0 | ✅ 309 passed |
| `npm run test` exit 0 | ✅ 885 passed |

## User Setup Required

**⚠ KONTEYNER IMAJINI QAYTA QURISH SHART** — bu rejaning YAGONA qo'lda qadami:

```bash
docker compose --profile test build tests
```

Sabab: uchta yangi Python paketi qo'shildi va Dockerfile `uv sync --frozen` bilan ishlaydi. Imaj qayta qurilmasa butun to'plam `ModuleNotFoundError: No module named 'openpyxl'` bilan yiqiladi. `uv.lock` allaqachon commit qilingan, ya'ni qo'shimcha `uv lock` chaqiruvi KERAK EMAS.

Migratsiya, tashqi servis sozlamasi yoki deploy qadami kerak emas — bu reja sxemaga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi).

## REQUIREMENTS.md holati — ATAYIN belgilanmadi

Reja frontmatteri `requirements: [MARKET-02, MARKET-04]` deb yozgan. Ikkalasining ham **import yarmi** shu rejada tugadi va u API darajasida uchidan-uchiga isbotlandi, lekin foydalanuvchi ko'radigan qobiliyat sifatida UI'siz to'liq emas: import paneli (4 holat, guruhlangan xato ro'yxati, `.xlsx` yuklab olish) 02-16 da quriladi. Ularni bu yerda "bajarildi" deb belgilash traceability jadvalini yolg'on qilardi (02-04…02-11 SUMMARY'laridagi bilan bir xil sabab).

Qo'shimcha texnik sabab: bu agent **worktree'da** ishlaydi va `REQUIREMENTS.md` — orkestrator egalik qiladigan umumiy artefakt.

## Next Phase Readiness

**02-16 (import paneli) uchun:**

- **422 javobining shakli:** `{"detail": {"detail": "import_validation_failed", "errors": [{row, code, message}], "error_counts": {kod: son}}}`. E'tibor bering — tana `detail` ICHIDA (FastAPI o'rami). `test_error_report_round_trip` bu shaklni qulflaydi.
- **`message` QATOR RAQAMINI O'ZIDA SAQLAYDI** (`"14-qator: 'Sabzavot' zonasi topilmadi"`). UI-SPEC §8.5 dagi `{row}-qator: {message}` formati AYNAN shu satrning o'zi — uni QAYTA prefikslamang. `row` maydoni tartiblash va Excelga o'tish uchun alohida beriladi.
- **`error_counts` — ekranning eng qimmatli qismi** (UI-SPEC §8.5) va u ro'yxatdan YUQORIDA ko'rsatiladi. Uni `errors` dan qayta hisoblamang: 50 ta ko'rsatilgan qatordan hisoblangan sanoq 300 xatoli faylda YOLG'ON bo'lardi.
- **`skipped > 0` tushuntirishi MAJBURIY** (D-15). Server `{inserted, skipped}` beradi; "38 tasi allaqachon mavjud edi — ular o'zgartirilmadi" matni bo'lmasa admin "nega yo'qoldi?" deb o'ylaydi.
- **`POST /imports/errors.xlsx`** — 422 javobining `errors` massivini AYNAN qaytarib yuboring (`{"errors": [...]}`). Server saqlamaydi; uzunlik 5000 bilan cheklangan.
- **Shablon havolasi** — `GET /api/v1/imports/template?kind=stalls|vendors`. Til SERVERDA (`users.locale`) hal bo'ladi, parametr YUBORMANG.
- **`import_conflict`** — YANGI xato kodi (23-chi). U `import_validation_failed` dan FARQLI: `errors[]` massivi YO'Q va foydalanuvchi uchun yagona ma'noli harakat — qayta urinish. Eng ehtimolli sababi — faylda CHETLANGAN rasta raqami (D-02).
- **`file_too_large` / `file_too_complex` / `unsupported_file_type`** — uchalasi ham 422 va ular `errors[]` BILAN KELMAYDI. Tanlash ekranidagi "Faqat xlsx fayl · 5 MB gacha · 5000 qatorgacha" matni aynan shu uchtaning oldini oladi.

**02-17 (real ma'lumot yo'riqnomasi) uchun:**

- Shablon repoda SAQLANMAYDI — `GET /imports/template` dan HAR SAFAR yangidan olinadi (Open Question 5). Yo'riqnomada aynan shu yo'l ko'rsatilsin, nusxa qo'yilmasin.
- `zone_not_found` — eng ko'p uchraydigan xato. Yo'riqnomaning 5-bo'limi uni tuzatish yo'lini (shablon ichidagi ochiluvchi ro'yxat) ko'rsatishi kerak. Registr FARQ QILMAYDI (`sabzavot` ham topiladi), lekin bo'sh joy va imlo farq qiladi.
- Sotuvchi faylida SANA ustuni bo'sh qoldirilishi mumkin — u `operating_since` ga tushadi. Sana matn sifatida yozilsa `2026-08-01` yoki `01.08.2026` shakllari qabul qilinadi.
- Rasta kodi Excelda SON sifatida yozilsa ham to'g'ri o'qiladi (`12.0` → `"12"`), lekin `"007"` shaklidagi kod MATN sifatida yozilishi shart — aks holda Excel uni `7` qilib yuboradi.

**06-hisob-kitob uchun:**

- Import qilingan rastaning boshlang'ich toifa davri `operating_since` bilan yoziladi — bu UCHINCHI yozish yo'li (seed, `POST /stalls`, import) va uchalasi ham AYNAN bir xil sanani ishlatadi. To'rtinchi yo'l qo'shilsa u ham shu qoidaga bo'ysunishi SHART, aks holda 02-11 faollashtirish darvozasi o'sha rastalarni bloklaydi.
- Import qilingan biriktirish — OCHIQ davr (`upper(period) IS NULL`), boshlanish sanasi esa `operating_since` yoki fayldagi sana. Ya'ni o'tmishga hisob qayta hisoblanganda import qilingan sotuvchilar BUTUN tarix davomida biriktirilgan ko'rinadi.

**Yangi marshrut qo'shadigan HAR KIM uchun (02-08…02-11 dan meros, endi 43 marshrut bilan):**

1. `main.py` ga `include_router(...)`;
2. yangi yo'l parametri bo'lsa — `PARAM_FILLERS` ga **B bozorining haqiqiy ID'si**;
3. marshrut JSON TANA talab qilsa — `BODY_FILLERS` ga yaroqli tana;
4. **(02-10):** marshrut BO'SH ro'yxat qaytarishi mumkin bo'lsa — tenant darvozasi ALOHIDA mavjudlik so'rovi bilan;
5. **(02-11):** marshrut bozor adminida YO'Q huquqni talab qilsa — `PLATFORM_ADMIN_ROUTES` ga;
6. **YANGI (02-12):** marshrut `multipart/form-data` (yoki umuman JSON'dan BOSHQA kontent tipi) qabul qilsa — `FILE_FILLERS` ga HAQIQIY yuklama. Bu YETARLI EMAS: mexanizmning YO'QLIGI matritsani qizartirmaydi (o'lchandi — 307 test yashil qoldi), shuning uchun `test_file_routes_actually_execute` kabi POZITIV darvoza ham kerak. Yangi kontent tipi qo'shgan odam o'sha darvozani ham kengaytirsin.

## Self-Check: PASSED

- Da'vo qilingan 9 yangi fayl diskda mavjud: `services/core-api/app/services/{__init__,xlsx_reader,import_validator,xlsx_template}.py`, `services/core-api/app/repositories/import_repo.py`, `services/core-api/app/api/v1/imports.py`, `tests/unit/test_xlsx_{reader,template}.py`, `tests/integration/test_stall_import.py`
- Da'vo qilingan 10 o'zgartirilgan fayl `git diff --stat 8e78d1f..HEAD` da ko'rinadi (19 fayl, +4613 / −5)
- To'rtala commit git tarixida mavjud: `4a3d047`, `021b1eb`, `e9bc223`, `bb0f701`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D --name-only` bo'sh)
- `migrations/` va `frontend/` UMUMAN teginilmadi
- Yettita sabotajdan keyin fayllar `git checkout -- <fayl>` bilan bit-ba-bit tiklandi; ishchi daraxtda kuzatilmagan fayl qolmadi va yakuniy darvoza (`ruff` + `mypy` + `pytest`) **885 passed** bilan yashil
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
