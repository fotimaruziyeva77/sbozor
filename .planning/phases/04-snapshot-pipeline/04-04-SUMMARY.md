---
phase: 04-snapshot-pipeline
plan: 04
subsystem: backend
tags: [quality-filter, pillow, settings, secrets, object-key, error-taxonomy, cam-06, d-14, d-15]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 01
    provides: "`Pillow 12.3.0` prod bog'liqligi va `.env.example` dagi 18 ta Phase-4 kaliti"
  - phase: 04-snapshot-pipeline
    plan: 02
    provides: "`tests/fixtures/frames.py` — `frame_bytes`, `truncate`, `HTML_ERROR_PAGE`. Usiz sifat filtri darvoza emas, konventsiya bo'lib qolardi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 05
    provides: "`isapi/errors.py` — 12 kodli reyestr shakli va sanoq darvozasi"
provides:
  - "`app/services/quality.py` — `analyze(data, thresholds) -> QualityReport` sof funksiyasi: verdikt, `light_mode`, `reason` VA o'lchovlarning O'ZI"
  - "`QualityThresholds` / `QualityReport` frozen dataclass'lari + `QUALITY_THRESHOLDS_VERSION`"
  - "`app/services/object_key.py` — `object_key()` va `KEY_PREFIX_FOR_DAY()`; kalit foydalanuvchi matnidan qurilmaydi"
  - "`app/services/capture_errors.py` — 11 kod, `CaptureErrorMeta` (`actor` bilan), `CAPTURE_AUTH_LOCKING_CODES` / `CAPTURE_DEFER_CODES` / `CAPTURE_JOB_ERROR_CODES`, `CaptureError`"
  - "`Settings` — fazaning 24 sozlamasi bitta joyda; `quality_thresholds()` sof modulga argument beradi"
  - "`.env.example` <-> `Settings` IKKI TOMONLAMA parity darvozasi (kalit VA qiymat)"
affects: [04-05, 04-06, 04-07, 04-08, 04-09, 04-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sof modul chegaralarni BILMAYDI: `QualityThresholds` da standart qiymat YO'Q va u argument sifatida kiradi — shunda test muhitga bog'lanmaydi va `Settings` bilan ikki manba tug'ilmaydi"
    - "Test IKKI chegara to'plami bilan o'lchaydi: `_RULE` qoidaning SHAKLINI (raqamlar har shart ALOHIDA hal qiluvchi bo'lsin deb tanlangan), `_SHIPPED` esa MAHSULOTDAGI xulqni. Faqat birinchisi bo'lsa «qoida to'g'ri, lekin mahsulotda hech qachon ishlamaydi» ko'rinmasdan qolardi"
    - "Rad etish SABABI verdiktdan ALOHIDA maydon — usiz darvozalarni bir-biridan ajratib o'lchab bo'lmaydi (bir darvozani o'chirish keyingisi tomonidan yopib ketiladi)"
    - "Sabotaj nazorati DEKODLANADIGAN bo'lishi kerak: HTML tanasi darvozani o'lchamaydi (u keyingi qadamda baribir rad etiladi), PNG esa o'lchaydi"
    - "Hujjat (`.env.example`) va kod (`Settings`) o'rtasidagi tenglik IKKI TOMONLAMA va u KALIT bilan cheklanmaydi — QIYMAT ham tekshiriladi"
    - "Yopib bo'lmaydigan qarz REYESTRDA nomlanadi (`_ENV_EXAMPLE_TODO`) va reyestr IKKI TOMONLAMA qulflanadi: yangi yozuv ham, yopilgan yozuv ham darvozani qizartiradi"
    - "Global jarayon holati (`Image.MAX_IMAGE_PIXELS`) ANIQ o'rnatiladi; `LOAD_TRUNCATED_IMAGES` esa ATAYIN o'rnatilmaydi — import tartibi tasodifiy, ya'ni «o'rnatdim» yolg'on ishonch berardi va yagona ishonchli himoya HOLATNI O'QIYDIGAN test"

key-files:
  created:
    - services/core-api/app/services/quality.py
    - services/core-api/app/services/object_key.py
    - services/core-api/app/services/capture_errors.py
    - tests/unit/test_quality_filter.py
    - tests/unit/test_snapshot_settings.py
    - tests/unit/test_object_key.py
    - tests/unit/test_capture_errors.py
  modified:
    - services/core-api/app/settings.py
  deleted: []

key-decisions:
  - "⛔ `blank` chegarasi `dark` ni ERISHILADIGAN qoldirishi SHART. O'lchandi: simulyatorning ikkala qorong'i yo'li ham (`9001` YAVG 16 YLOW=YHIGH=16, `9101` YAVG 126 YLOW=YHIGH=126) `stddev≈0` beradi, ya'ni `blank` ikkalasini ham yutadi. Yagona `dark` manbai — sintetik kadr. Shuning uchun test to'plamida `blank_stddev=1,0` (o'lchangan `stddev` AYNAN 2,000 dan past) va mahsulotda `dark` erishiladigan ekani ALOHIDA test bilan qulflandi"
  - "Rejaning `blank_stddev=8,0` mezoni O'Z-O'ZIGA ZID: `stddev=2` kadri `blank` dan OLDIN o'tolmasdi. Niyat (D-14 ni bevosita o'lchash) bajarildi, mexanika tuzatildi"
  - "`.env.example` (04-01 ning fayli) SOZLAMA NOMLARI VA QIYMATLARI uchun HAQIQAT MANBAI qilib olindi — reja taklif qilgan nomlar/standartlar bilan ziddiyatda. Sabab: kod va operator hujjati ajralib ketishi JIM nosozlik, chegara raqami esa D-15 bo'yicha ataylab sozlanadigan"
  - "`draft` rejimi `\"RGB\"`, `\"L\"` EMAS (reja `\"L\"` yozgan). O'lchandi: `draft(\"L\", ...)` dekoderni kul rang rejimiga o'tkazadi va to'yinganlik HAR DOIM 0,0 chiqadi — `ir_night` va `low_light` shoxlari ajralmay qolardi va D-12 ning butun mazmuni jimgina yo'qolardi"
  - "`QualityReport` ga `reason` maydoni QO'SHILDI (rejada yo'q). Usiz magic-bayt darvozasini o'chirish HECH QANDAY testni qizartirmasdi — o'lchandi, quyidagi sabotaj jadvaliga qarang"
  - "O'lchab bo'lmagan qiymat `None`, NOL EMAS: nol bazada «o'lchandi va nol chiqdi» ma'nosiga ega bo'lardi va `corrupt` kadrlarning soxta nollari D-15 ning `percentile_cont` bilan chegara chiqarish yo'lini buzardi"
  - "S3 kalitlarining standarti `\"\"` + validator (standartsiz maydon EMAS). Kafolat AYNAN o'sha (yetishmayotgan o'zgaruvchi `\"\"` ga tushadi va rad etiladi), lekin standartsiz shakl bu rejaning fayllari BO'LMAGAN `tests/conftest.py` va `test_nvr_secrets.py` ni mypy darajasida buzardi"
  - "`capture_stream_limit` `defer`, `locks_account` EMAS — ikki MUSTAQIL o'lcham. Bitta bayroqqa yig'ish «NVR band edi» sababini «kadr yo'q» ga aylantirardi"

patterns-established:
  - "Pattern: chegara to'plami TESTDA aniq yoziladi va har raqamning YONIDA nega aynan shu son ekani turadi («40 — `mean=30` dan yuqori, ya'ni birinchi shart YOLG'IZ hal qila olmaydi»). Chegara sababsiz bo'lsa test o'z farazini tasdiqlaydi"
  - "Pattern: darvozaning MUSTAQIL nazorati keyingi darvozadan O'TA OLADIGAN kirish bilan quriladi — aks holda sabotaj natijasi keyingi qadam tomonidan yopib ketiladi va darvoza «bor» bo'lib ko'rinadi"
  - "Pattern: ikki gate bir xil obyektni tekshirsa ham TURLI da'voni o'lchaydi — hosila to'plamning QIYMATI (test) va uning QURILISH SHAKLI (matn ustidagi regex). Ikkalasi ham kerak: qo'lda yozilgan literal bugun to'g'ri qiymat berishi mumkin"
  - "Pattern: yetkazilgan standartlar test faylida QO'LDA takrorlanadi (muhitdan mustaqillik uchun), lekin nusxa BOSHQA test bilan manbaga bog'lanadi — shunda u eskirib qola olmaydi"

requirements-completed: [CAM-05, CAM-06, CAM-07, FOUND-06]

# Metrics
duration: 3h 05m
completed: 2026-08-04
---

# Phase 4 Plan 04: Sof funksiya qatlami — sifat filtri, kalit fabrikasi, xato taksonomiyasi Summary

**CAM-06 ning yuragi endi sof funksiyada va DARVOZA ostida: `analyze()` sintetik baytlardan `ok`/`dark`/`blank`/`corrupt` ni aniq ajratadi, `dark` ikki shartli (D-14) va qonuniy qish-tong kadri IKKALA chegara to'plamida ham yaroqli; o'lchovlarning o'zi qaytariladi (D-15), obyekt kaliti foydalanuvchi matnidan strukturaviy ravishda qurilmaydi, o'n bir xato kodi `actor` bilan bitta reyestrda va fazaning 24 sozlamasi `.env.example` bilan IKKI TOMONLAMA parity darvozasi ostida.**

## Performance

- **Duration:** ~3 soat 5 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 8 (7 yangi, 1 o'zgartirilgan) — 922 qator ishlab chiqarish kodi, 74 yangi test
- **Commits:** 6 (ikkitasi TDD RED juftligi + bitta repo-darajasidagi tuzatish)

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 2 | `quality.py` — RED | `da71c8d` (test) |
| 2 | `quality.py` — GREEN | `5b44455` (feat) |
| 1 | `Settings` + parity darvozasi | `4185fb4` (feat) |
| 3 | `object_key.py` + `capture_errors.py` — RED | `dc1dca4` (test) |
| 3 | `object_key.py` + `capture_errors.py` — GREEN | `7ce7019` (feat) |
| — | S3 standartlari (repo-darajasidagi `mypy` topilmasi) | `9aea493` (fix) |

## O'LCHOVLAR — taxmin qilinmadi

Barcha chegara qarorlari `Pillow 12.3.0` konteynerida o'lchangan qiymatlarga tayanadi.

| Kadr | Bayt | `mean` | `stddev` | to'yinganlik |
|---|---|---|---|---|
| `mean=140, stddev=45` (320x180) | 2 927 | **140,000** | **45,000** | 0,0000 |
| `mean=8, stddev=2` | 2 467 | **8,000** | **2,000** | 0,0000 |
| `mean=30, stddev=28` | 2 812 | **30,000** | **28,000** | 0,0000 |
| `mean=24, stddev=24` | 2 812 | **24,000** | **24,000** | 0,0000 |
| `mean=60, stddev=0` | 2 237 | 60,000 | **0,000** | 0,0000 |
| `mean=70, stddev=25, sat=0,5` | 3 619 | 70,000 | 25,000 | **0,5114** |
| `mean=8, stddev=2` (1280x720) | 29 607 | 8,000 | 2,000 | 0,0000 |
| kesilgan (EOI yo'q) | 22 300 | — | — | — |
| HTML xato sahifasi | 150 | — | — | — |

**Uchta natija bevosita qarorga aylandi:**

1. **Barcha 320x180 sintetik kadr 4 096 baytdan KICHIK** (2 236–3 849). Ya'ni yetkazilgan `QUALITY_MIN_BYTES=4096` bilan o'lchanadigan testlar 1280x720 kadr ishlatishi SHART — aks holda ular o'lcham polida to'xtab, sifat qoidasini umuman sinamasdi. Bu real kadr uchun to'g'ri chegara (1280x720 dagi eng qorong'i kadr ham 29 607 bayt).
2. **`draft(\"RGB\", (320,180))` statistikani BUZMAYDI:** 1280x720 kadr kichraytirilgan dekod bilan o'qilganda `mean`/`stddev` AYNAN o'zgarmadi (24,000/24,000), to'yinganlik esa 0,5081 (to'liq dekodda 0,5114 — e'lon qilingan ±0,05 toleransi ichida).
3. **Kesilgan JPEG ga SOXTA EOI qo'shilsa u JIMGINA dekodlanadi:** 22 302 baytli tana `mean=127,992, stddev=30,806` berdi (haqiqiysi 128/40). Ya'ni `LOAD_TRUNCATED_IMAGES=False` bu shaklni tutmaydi — dekoder EOI markerini ko'rib TOZA to'xtaydi. Qoldiq chegara ochiq yozildi (quyida «Qoldiq chegaralar»).

## Sabotaj o'lchovlari — nima QIZARDI va nima YASHIL QOLDI

Ikkinchi ustun bu loyihada qayta-qayta birinchisidan ko'ra ko'proq ma'lumot bergan.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Xulosa |
|---|---|---|---|---|
| 1 | `dark` dan `and stddev < thresholds.dark_stddev` olib tashlandi | **AYNAN 2 test**: `test_mean_30_stddev_28_is_ok_because_it_has_structure` (`'dark' == 'ok'`) va `test_mean_24_stddev_24_is_ok_at_shipped_defaults` | 22 test, jumladan BARCHA qolgan verdikt testlari | D-14 IKKI joyda mustaqil o'lchanadi — qoida chegaralarida VA yetkazilgan raqamlarda |
| 2a | Magic-bayt (`SOI`) qadami olib tashlandi, nazorat XOM PNG bilan | **1 test**, lekin faqat `reason` bo'yicha: `'missing_end_of_image' == 'not_a_jpeg'`. **VERDIKT `corrupt` bo'lib QOLDI** | qolgan 23 | ⚠ **Topilma:** faqat verdikt qaytarilganda bu sabotaj HECH QANDAY testni qizartirmasdi. Darvoza «bor» bo'lib ko'rinardi |
| 2b | O'sha sabotaj, nazorat PNG + EOI markeri bilan (kuchaytirildi) | **1 test**, endi VERDIKT bo'yicha: `'ok' == 'corrupt'` | qolgan 23 | JPEG bo'lmagan tana YAROQLI BILLING KADRI sifatida qabul qilinardi — sabotajning haqiqiy narxi shu |
| 3 | `.env.example` ga `RETENTION_PURGE_DAYS=1000` (`Settings` maydonisiz) | **1 test**: `test_every_env_example_key_has_a_settings_field`, xabarda kalit so'zma-so'z | qolgan 15 | Jim no-op darvozasi mustaqil ishlaydi |
| 4 | `retention_jpeg_quality` standarti 60 -> 55 (rejaning taklifi) | **1 test**: `test_env_example_values_equal_the_settings_defaults`, xabarda IKKALA tomon: `{'retention_jpeg_quality': (55, 60)}` | qolgan 15 | Rejaning uchta standarti aynan shu darvozani qizartirardi — u ularni JIMGINA o'tkazib yubormadi |
| 5 | `capture_stream_limit` ning `defer` bayrog'i `True` -> `False` | **1 test**: `test_stream_limit_is_deferred_but_never_locking` | 17 test, **jumladan `test_defer_codes_are_derived_from_the_metadata`** | ⚠ **Reja bu sabotajni «hosila darvozasini qizartiradi» degan edi — NOTO'G'RI.** Hosila darvoza ikkala tomonni ham metadan hisoblaydi, ya'ni bayroq o'zgarganda u BIRGA o'zgaradi. Qizargani — SEMANTIK darvoza |
| 6 | `CAPTURE_AUTH_LOCKING_CODES` qo'lda literal qilib yozildi | **struktura tekshiruvi** (matn ustidagi regex) | **18 testning HAMMASI** | Ikki darvoza turli da'voni o'lchaydi: test QIYMATNI, regex esa QURILISH SHAKLINI. Qo'lda yozilgan literal BUGUN to'g'ri qiymat beradi, ya'ni faqat test yetarli emas edi |

Har olti holatda ham fayl darhol tiklandi va to'plam qayta yashil bo'ldi.

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/unit/test_snapshot_settings.py test_quality_filter.py test_object_key.py test_capture_errors.py -q` | **74 test**, exit 0 |
| 2 | `pytest tests/unit -q` | **695**, exit 0 |
| 3 | `pytest tests/unit/test_no_sim_branching.py -q` | **5**, exit 0 |
| 4 | `ruff check . && ruff format --check . && mypy .` | exit 0 (215 fayl formatlangan, **209 fayl tiplangan**) |
| 5 | `pytest -q` (to'liq) | **1 644 test** (5 `hardware` deselected), exit 0 — baza 1 570 -> **+74** |
| 6 | `pytest tests/tenancy -q` | **417** (o'zgarmagan) |
| 7 | `npm run gate:fast` | exit 0, **72 s** (chegara 180 s, 2,5x zaxira) |
| 8 | `npm --prefix frontend run i18n:check` | **577 kalit x 3 til** (o'zgarmagan) |
| 9 | vitest / node darvozalari | **246** / **111** (ikkalasi ham o'zgarmagan) |
| 10 | `git diff --exit-code logging.py pyproject.toml frontend/package.json .env.example` | **o'zgarish yo'q** (T-04-SC tasdiqlandi) |

Rejaning ikkita qabul mezoni (`get_settings()` ni `python -c` bilan chaqiradigan buyruqlar) **bajarib bo'lmaydigan shaklda** yozilgan edi: `tests` konteynerida `DATABASE_URL`/`VALKEY_URL`/`JWT_SECRET` YO'Q (`compose.yaml` ularni faqat `core-api` va `worker` ga beradi), ya'ni buyruq mening kodim emas, yetishmayotgan muhit tufayli yiqilardi. Ikkalasi ham **niyati bo'yicha** bajarildi — majburiy muhit `-e` bilan berilib, o'sha assertion'lar aynan o'sha holda o'lchandi (`retention_full_days==90`, `SecretStr` tipi, `repr` da sizib chiqmaslik).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — bloklovchi] Task tartibi almashtirildi: 2 -> 1 -> 3**

- **Topildi:** Task 1 ni boshlashda
- **Muammo:** Task 1 (`settings.py`) `quality_thresholds()` ni talab qiladi, u esa `app.services.quality` dan `QualityThresholds` ni import qiladi — modul Task 2 da tug'iladi. Rejaning o'z `<interfaces>` bo'limi import yo'nalishini `settings.py -> quality.py` deb QATIY belgilaydi, ya'ni teskarisi mumkin emas.
- **Yechim:** `quality.py` (Task 2) birinchi bajarildi. Muqobil — Task 1 da yarim `quality.py` yozib, Task 2 da uni to'ldirish — modulni ikki commitga bo'lib, docstringdagi uch majburiyatni koddan ajratib qo'yardi.
- **Fayllar:** yo'q (faqat tartib)

**2. [O'z-o'ziga zid mezon] `blank_stddev=8.0` bilan `mean=8, stddev=2` -> `DARK` MUMKIN EMAS**

- **Qayerda:** Task 2 ning `<behavior>` 2-bandi va D-14 ning bevosita o'lchov buyrug'i
- **O'lchandi:** qaror tartibi rejaning O'ZIDA `blank -> dark -> ok` va `blank` faqat `stddev` ga qaraydi. `stddev=2 < blank_stddev=8` -> kadr `blank`, `dark` ga UMUMAN yetib bormaydi. `.env.example` ning `QUALITY_BLANK_STDDEV_MAX=3` i bilan ham xuddi shunday (`2 < 3`).
- **Chuqurroq topilma:** simulyatorning IKKALA qorong'i yo'li ham (`9001`: `YAVG 16, YLOW=YHIGH=16`; `9101`: `126, YLOW=YHIGH=126`) `stddev≈0` beradi, ya'ni `blank` ularni ham yutadi. Ya'ni bu fazadagi YAGONA `dark` manbai — sintetik kadr, va `blank_stddev` 2 dan past bo'lmasa **`dark` verdikti butunlay erishilmaydigan (o'lik) shox bo'lib qolardi**.
- **Yechim:** mezonning NIYATI bajarildi (D-14 ni bevosita o'lchash), mexanika tuzatildi. Test to'plamida `blank_stddev=1,0` va tanlovning sababi kodda, raqamning YONIDA yozildi. Yetkazilgan standart (`3,0`) esa `.env.example` bilan mos qoldi va `dark` u yerda ham ERISHILADIGAN ekani alohida test bilan qulflandi (`test_mean_8_stddev_5_is_dark_at_shipped_defaults`).
- **Fayllar:** `tests/unit/test_quality_filter.py` — commit `da71c8d`

**3. [Rule 1 — bug] `draft(\"L\", ...)` to'yinganlikni HAR DOIM 0,0 qilardi**

- **Topildi:** Task 2, §C.7 zanjirini yozishda
- **Muammo:** Reja (va `04-RESEARCH.md` §C.7) `im.draft(\"L\", (320,180))` ni buyuradi, keyin esa 5-qadamda «kichraytirilgan RGB -> HSV -> o'rtacha `S`» ni talab qiladi. Bular BIR VAQTDA mumkin emas: `draft(\"L\", ...)` JPEG dekoderini kul rang rejimiga o'tkazadi va undan keyin RGB ma'lumot QOLMAYDI.
- **Nima uchun kritik:** to'yinganlik har doim 0,0 bo'lganda `ir_night` (`sat < 0,05`) va `low_light` (`sat >= 0,05`) shoxlari BIR-BIRIDAN AJRALMAY qolardi — barcha qorong'i kadr `ir_night` bo'lib yozilardi. D-12 ning butun mazmuni (~15 qator narxiga 5 va 8-fazalar uchun segmentatsiya) jimgina yo'qolardi va nosozlik faqat 8-fazadagi aniqlik hisobotida ko'rinardi.
- **Tuzatish:** `draft(\"RGB\", (320,180))`. O'lchandi: 1280x720 kadrda statistika AYNAN saqlanadi (yuqoridagi jadval), ya'ni tezlik yutug'i ham yo'qolmaydi. Sabab kodda `_DRAFT_SIZE` ning yonida yozildi.
- **Verifikatsiya:** `test_saturation_000_..._is_ir_night` va `test_saturation_050_..._is_low_light` — ikkalasi ham yashil; `\"L\"` bilan ikkinchisi qizarardi.
- **Fayllar:** `services/core-api/app/services/quality.py` — commit `5b44455`

**4. [Rule 2 — yetishmayotgan kritik xulq] `QualityReport.reason` maydoni qo'shildi**

- **Topildi:** Task 2 ning SABOTAJ 2 mezonini bajarganda
- **Muammo:** Reja magic-bayt darvozasini olib tashlash «`analyze(HTML_ERROR_PAGE)` testini AYNAN qizartiradi» deb kutadi. **O'lchandi — qizartirmaydi:** HTML tanasi 150 bayt, ya'ni u magic darvozasiga YETIB BORMAYDI, `MIN_BYTES` polida to'xtaydi. Kattaroq nazorat (5 159 baytli to'ldirilgan HTML) ham yordam bermaydi: u keyingi qadamda `UnidentifiedImageError` bilan baribir `corrupt` bo'ladi. Ya'ni **faqat verdikt qaytarilganda darvozani o'chirib qo'yish mumkin va hech narsa sezmasdi.**
- **Tuzatish:** `QualityReport` ga `reason` maydoni (`REASON_SIZE_BELOW_FLOOR`, `REASON_NOT_JPEG`, `REASON_TRUNCATED`, `REASON_DECODE_FAILED`, `REASON_BLANK`, `REASON_DARK`, `REASON_OK`) va nazorat sifatida **yaroqli PNG** — u dekodlanadi, ya'ni uni FAQAT magic darvozasi rad etadi.
- **Ikkinchi foyda operatsion:** «corrupt» yolg'iz o'zi adminga hech nima aytmaydi. `not_a_jpeg` (go2rtc sozlamasi), `missing_end_of_image` (tunnel uzilyapti) va `size_below_floor` (javob bo'sh) — uchtasining yechimi UCH XIL joyda (`discovery.py:112-121` bilan bir xil mulohaza).
- **Verifikatsiya:** sabotaj jadvalining 2a/2b qatorlari.
- **Fayllar:** `services/core-api/app/services/quality.py`, `tests/unit/test_quality_filter.py` — commit `5b44455`

**5. [Rule 1 — bug] Rejaning sozlama NOMLARI va STANDARTLARI `.env.example` bilan ziddiyatda**

- **Topildi:** Task 1, `.env.example` ni o'qishda
- **Muammo:** Reja `quality_blank_stddev`/`quality_dark_mean`/`quality_dark_stddev` nomlarini va `8.0`/`40.0`/`20.0` standartlarini buyuradi; `04-01` yetkazgan `.env.example` da esa `QUALITY_BLANK_STDDEV_MAX=3`, `QUALITY_DARK_MEAN_MAX=25`, `QUALITY_DARK_STDDEV_MAX=12`. Xuddi shunday: `CAPTURE_GLOBAL_CONCURRENCY` reja 8 deydi, `.env.example` va **D-08 ning o'zi** 1 deydi; `RETENTION_JPEG_QUALITY` 55 ga qarshi 60; `RETENTION_BATCH_SIZE` 500 ga qarshi 200; `QUALITY_MIN_BYTES` 2 000 ga qarshi 4 096.
- **Nima uchun kritik:** rejaning nomlari bilan parity testi HECH QACHON o'ta olmasdi (u kalit to'plamlarining tengligini talab qiladi), standartlari bilan esa `.env` ni `.env.example` dan nusxalagan operator KODDAGI standartdan BOSHQA xulq olardi — va ikkalasi ham «to'g'ri» ko'rinardi.
- **Yechim:** `.env.example` HAQIQAT MANBAI qilib olindi — nomlar ham, qiymatlar ham. `capture_global_concurrency=1` bundan tashqari `04-CONTEXT.md` D-08 ning ochiq qarori (rejaning 8 i D-08 ga zid edi). Tenglik endi MEXANIK darvoza ostida (sabotaj 3 va 4).
- **Fayllar:** `services/core-api/app/settings.py`, `tests/unit/test_snapshot_settings.py` — commit `4185fb4`

**6. [Rule 3 — bloklovchi] S3 kalitlarining standartsiz shakli begona fayllarni buzardi**

- **Topildi:** rejaning 4-verifikatsiya qadami (`mypy .` — repo bo'ylab)
- **Muammo:** `s3_access_key: str` / `s3_secret_key: SecretStr` (standartsiz) `Settings` ning konstruktorini o'zgartiradi va **`tests/conftest.py:549`** hamda **`tests/unit/test_nvr_secrets.py:243,274`** dagi mavjud `Settings(...)` chaqiruvlarini `call-arg` xatosi bilan buzadi. Ikkala fayl ham bu rejaning `files_modified` ida YO'Q va `conftest.py` — parallel to'lqin uchun umumiy infratuzilma.
- **Yechim:** standart `\"\"` + validator. **Kafolat AYNAN o'sha bo'lib qoladi:** yetishmayotgan o'zgaruvchi `\"\"` ga tushadi, validator uni ISHGA TUSHISHDA rad etadi. Farq faqat XABAR sifatida — bizniki `ops/seaweedfs/s3.json` ga yo'l ko'rsatadi, pydantic'ning «Field required» i esa yo'q.
- **Yangi yo'l ALOHIDA qulflandi:** standart qo'shilishi «o'zgaruvchi umuman yo'q» yo'lini ochadi va u validator faqat bo'sh satrni tekshirsa jimgina o'tib ketardi — `test_a_missing_empty_s3_key_env_var_fails_the_same_way` aynan shuni o'lchaydi.
- **Fayllar:** `services/core-api/app/settings.py`, `tests/unit/test_snapshot_settings.py` — commit `9aea493`

**7. [O'z-o'ziga zid mezon] Task 3 sabotajining kutilgan natijasi noto'g'ri edi**

- **Qayerda:** Task 3 ning sabotaj mezoni: «`capture_stream_limit` ning `defer` ni `False` ga o'zgartirish HOSILA darvozasini qizartiradi»
- **O'lchandi:** hosila darvoza (`test_defer_codes_are_derived_from_the_metadata`) **YASHIL QOLDI** va bu TO'G'RI xulq: u `expected` ni AYNAN o'sha metadan hisoblaydi, ya'ni bayroq o'zgarganda ikkala tomon BIRGA o'zgaradi. Qizargani — SEMANTIK darvoza (`test_stream_limit_is_deferred_but_never_locking`).
- **Yechim:** mezonning niyati («ikki darvoza turli da'voni o'lchaydi») **isbotlandi**, lekin boshqa juftlik bilan: hosila darvozaning haqiqiy juftisi — matn ustidagi **regex** (rejaning o'z mezoni). Alohida o'lchandi: `CAPTURE_AUTH_LOCKING_CODES` ni qo'lda literal qilib yozish **18 testning HAMMASINI yashil qoldiradi** (bugungi qiymat mos keladi) va faqat regex uni tutadi. Ya'ni ikkala darvoza ham HAQIQATAN kerak — bu rejaning da'vosidan ham kuchliroq natija.
- **Fayllar:** yo'q (mezonning o'lchovi; natija shu jadvalda)

**8. [Rule 2] `test_object_key.py` ga rejada aytilmagan darvozalar**

- `test_arguments_are_keyword_only` — `market_id` va `camera_id` BIR XIL tipda (`UUID`), ya'ni pozitsion chaqiruvda ularni almashtirib yuborish TIP XATOSI BERMASDI va kadrlar begona bozorning prefiksiga tushardi. Nomli argumentlar bu sinfni butunlay yopadi.
- `test_seconds_and_microseconds_never_reach_the_key` — sekund kalitga tushsa retry IKKINCHI obyekt yaratardi va §B.4 ning idempotentlik kaliti ombor darajasida buzilardi.
- `test_day_prefix_does_not_match_a_neighbouring_day` — nazorat holati: ajratuvchisiz prefiks `2026-09-1` bilan `2026-09-10` ni aralashtirardi.
- **Fayllar:** `tests/unit/test_object_key.py` — commit `dc1dca4`

---

**Total deviations:** 8 (3x Rule 1/2 bug yoki yetishmayotgan xulq, 2x Rule 3 bloklovchi, 3x o'z-o'ziga zid mezon)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Uchtasi (2, 4, 7) rejaning O'LCHANMAGAN farazlarini o'lchov bilan almashtirdi va uchalasida ham natija rejadagidan **kuchliroq** darvoza berdi.

## Topilma — `censor_secrets` yangi sir nomlarini QAMRAMAYDI

`sbozor_core.logging::SENSITIVE_KEYS` — **aniq nomlar ro'yxati, naqsh emas** (`_is_sensitive`: `str(key).lower() in SENSITIVE_KEYS`). Ya'ni `*_key` / `*_token` / `*_secret` shakli avtomatik qamrab olinmaydi.

**O'lchandi:** `censor_secrets(None, \"info\", {\"s3_access_key\": ..., \"s3_secret_key\": ..., \"telegram_bot_token\": ...})` -> **uchalasi ham senzuradan O'TIB KETADI** (`covered == set()`).

Ya'ni `log.info(\"upload_failed\", s3_secret_key=...)` shaklidagi chaqiruv sirni jurnalga va Sentry'ga yuborardi. `SecretStr` bu yo'lni YOPMAYDI — u `repr(settings)` ni yopadi, structlog kalitini emas.

- **Nima uchun bu rejada tuzatilmadi:** `packages/sbozor-core/sbozor_core/logging.py` bu rejaning `files_modified` ida YO'Q va rejaning o'z mezoni unga tegilmaganini `git diff --exit-code` bilan talab qiladi (tekshirildi: tegilmagan).
- **Kimga o'tkazildi:** **`04-08`** (alert jo'natuvchisi) — u Telegram tokenini ISHLATADIGAN birinchi reja.
- **Darvoza qo'yildi:** `test_log_filter_coverage_of_the_new_secret_names_is_measured` bugungi holatni (`covered == set()`) qulflaydi va **qamrov paydo bo'lganda QIZARADI** — ya'ni band yopilgan kuni u ko'rinadi va bu yerdagi «qamramaydi» matni jimgina eskirib qola olmaydi.

## Qoldiq chegaralar — ochiq yozilgan

1. **Kesilgan JPEG + SOXTA EOI JIMGINA o'tadi.** O'lchandi: 22 302 baytli tana (haqiqiy ma'lumotning 60% i + qo'lda qo'shilgan `\\xff\\xd9`) muvaffaqiyatli dekodlandi va `mean=127,992, stddev=30,806` berdi. Sabab: dekoder EOI markerini ko'rib TOZA to'xtaydi, ya'ni `LOAD_TRUNCATED_IMAGES=False` ishga tushmaydi. **Amaliy xavf TOR:** bu shakl uchun tarmoq uzilishi AYNAN oxirgi ikki bayt `\\xff\\xd9` bo'ladigan joyda sodir bo'lishi kerak. Ikkala darvoza ham (EOI va dekod) o'z o'rnida qoladi — ular chuqurlikdagi himoya.
2. **`mean=8, stddev=2` yetkazilgan standartlarda `blank`, `dark` EMAS** (`2 < QUALITY_BLANK_STDDEV_MAX=3`). Ikkala verdikt ham `is_billable = false` beradi va ikkalasi ham adminga ko'rinadi — farq FAQAT diagnostikada («linza yopiq» va «yorug'lik yo'q»). Holat ATAYIN test bilan qulflangan (`test_mean_8_stddev_2_is_blank_at_shipped_defaults`), ya'ni Phase 0 da chegara sozlangan kuni u qizaradi va o'zgarish KO'RINADI.
3. **Sifat chegaralari LOW confidence — bu qaror, kamchilik emas** (D-15). Real Karmana kadri yo'q. Isbotlangani — **mexanizm**: o'lchovlarning o'zi qaytariladi, chegaralar `Settings` da va `quality_thresholds_version` har kadrga yoziladi, ya'ni sozlash bitta SQL so'rovi bo'ladi va o'tmish RETROAKTIV o'zgarmaydi.

## Known Stubs

Yo'q. Uchala modul ham to'liq ishlaydi va har biri o'z darvozasi bilan keldi.

⚠ **Stub bo'lmagan, lekin ochiq qolgan ikki band (ikkalasining ham egasi va tetigi bor):**

1. **`_ENV_EXAMPLE_TODO` — olti sozlama `.env.example` da hujjatlanmagan:** `S3_REGION` (egasi `04-06`), `CAPTURE_LEASE_SECONDS` va `CAPTURE_BATCH_SIZE` (`04-07`), `QUALITY_MAX_BYTES` / `QUALITY_IR_SATURATION` / `QUALITY_NIGHT_MEAN` (`.env.example` ning egasi kim bo'lsa — ular sifat filtrining chegaralari va bugun faqat kodda). Ular `Settings` ga KIRITILDI, chunki muqobil (04-06/04-07 sozlamani o'z fayllariga sochishi) «fazaning barcha sozlamalari bitta joyda» qoidasini buzardi. Tetik: `test_every_settings_field_is_documented_or_registered` reyestrni IKKI TOMONLAMA qulflaydi — yangi hujjatlanmagan maydon ham, hujjatlangan eski maydon ham darvozani qizartiradi.
2. **`censor_secrets` qamrovi** — yuqoridagi bo'lim, egasi `04-08`.

## Threat Flags

Yangi tarmoq endpointi, auth yo'li yoki sxema chegarasi YO'Q — uchala modul ham sof funksiya. Aksincha, threat register'ning oltita mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-24 (dekompressiya bombasi) | `MAX_BYTES` DEKODDAN OLDIN; `Image.MAX_IMAGE_PIXELS = 50 000 000` ANIQ o'rnatildi (Pillow standarti 89 478 485 — biz PASAYTIRDIK) va `is not None` darvozasi bilan qulflandi |
| T-04-25 (JPEG o'rniga HTML) | Magic-bayt darvozasi DEKODSIZ va `Content-Type` ga umuman qaramaydi; PNG nazorati bilan MUSTAQIL o'lchandi |
| T-04-26 (`LOAD_TRUNCATED_IMAGES = True`) | Import qatlamida global holat o'qiladi. ⚠ Bayroq ATAYIN `False` ga «o'rnatilmadi»: import tartibi tasodifiy, ya'ni bizdan KEYIN yuklangan bog'liqlik uni baribir `True` qilardi va biz «o'rnatdik» degan yolg'on ishonchda qolardik |
| T-04-27 (yo'l chiqishi) | Kalit FAQAT `UUID` + ISO sana + `HHMM` dan; `..`, `//`, bo'sh segment, `\\`, `\\x00` va URL-xavfsiz belgilar alohida tekshiriladi |
| T-04-28 (sir `repr` da) | `s3_secret_key` va `telegram_bot_token` — `SecretStr`; kanareyka qiymatlar bilan o'lchandi. ⚠ `censor_secrets` qamrovi QAMRAMAYDI — yuqoridagi topilma |
| T-04-29 (bo'sh S3 kaliti) | `field_validator` ISHGA TUSHISHDA yiqitadi; bo'sh, bo'shliqli VA umuman yo'q — uchala yo'l ham |
| T-04-30 (reyestrning bo'linishi) | Bitta reyestr; `CAPTURE_JOB_ERROR_CODES` `schemas.py` tomonidan import qilinadi (04-07); sanoq darvozasi 11 kod |
| T-04-31 (chegaraning kodda qotishi) | `QualityThresholds` da standart qiymat YO'Q — modul chegaralarni bilmaydi |
| T-04-SC (paket o'rnatish) | Yangi paket YO'Q; `git diff --exit-code pyproject.toml package.json` toza |

## Issues Encountered

- **`docker compose up -d --wait db cache` `sbozor-db-1` ni QAYTA YARATDI va u ko'tarilmadi.** Sabab: xostda mahalliy `postgres` jarayoni (PID 7252) `0.0.0.0:5432` ni egallagan, ya'ni konteyner `127.0.0.1:5432` ga bog'lana olmadi. **Konteyner tiklandi:** `DB_HOST_PORT=5433 docker compose up -d db` -> `Started`. `pgdata` nomlangan volume, ya'ni **ma'lumot yo'qolmadi**; compose tarmog'i ichidagi manzil (`db:5432`) O'ZGARMADI, faqat xost tomonidagi port 5433 ga ko'chdi. ⚠ Bu buyruq umuman KERAK EMAS edi: to'plam bazani `testcontainers` orqali oladi (`conftest.py:201`), compose `db` sidan emas. **Parallel ijrochiga ta'siri:** `tests/tenancy` ham testcontainers ishlatadi, ya'ni ta'sir yo'q.
- **Frontend `node_modules` worktree'da yo'q edi** — `npm ci --prefix frontend` bilan o'rnatildi (530 paket, 39 s). `package.json` va `package-lock.json` **tegilmadi** (`git diff --exit-code` bilan tasdiqlandi).
- **`ruff` ning `SIM300` (Yoda condition) va `I001` qoidalari** bir necha testda ishga tushdi — `--fix` bilan tuzatildi, qoida chetlab o'tilmadi.

## Doiradan tashqarida topilgan band (TEGILMADI)

`04-02` ning SUMMARY'si `tests/integration/test_live_view_e2e.py:102` va `tests/integration/test_real_nvr.py:109` izohlarining eskirganini (`/picture` endi 160 emas, 2 927 bayt beradi) qayd etib, uni **`04-04` yoki `04-05`** ga o'tkazgan edi. **Bu rejada ham tuzatilmadi:** ikkala fayl ham bu rejaning `files_modified` idan tashqarida va parallel to'lqinda ularga tegish fayl to'qnashuvi xavfini tug'dirardi. Funksional ta'siri yo'q (ikkala test ham ISAPI'ni emas, boshqa yuzani o'lchaydi). **Egasi endi `04-05`** — u `/picture` ning birinchi haqiqiy iste'molchisi.

## User Setup Required

Yo'q. ⚠ Lekin bitta OPERATSION eslatma: xostda mahalliy `postgres` ishlayotgani uchun `docker compose up db` standart 5432 portida ko'tarilmaydi. `.env` ga `DB_HOST_PORT=5433` yozilsa muammo butunlay yo'qoladi (`.env.example` bu holatni allaqachon hujjatlagan, 187-qator).

## Next Phase Readiness

**`04-05` (repozitoriy qatlami) uchun tayyor va u shu uch satrni o'qishi kerak:**
- `quality.py` `sbozor_core.enums` ga ATAYIN bog'lanmagan (to'lqin ichidagi bog'liqlik yo'q). `VERDICT_*` / `LIGHT_*` konstantalarining `SnapshotQuality` / `SnapshotLightMode` bilan mosligini **`04-05` bitta test bilan qulflashi SHART** — bu qarz `QUALITY_VERDICTS` va `LIGHT_MODES` docstringlarida nomlangan.
- `QualityReport` da `reason` maydoni bor (rejada yo'q edi). U saqlanishi SHART emas, lekin saqlansa operator diagnostikasi ancha aniq bo'ladi.
- O'lchovlar `None` bo'lishi mumkin (`corrupt` kadrlarda) — `snapshots.quality_*` ustunlari NULLABLE bo'lishi kerak.

**`04-06` (ombor) uchun:** `object_key()` va `KEY_PREFIX_FOR_DAY()` tayyor; `s3_region` `Settings` da bor, lekin `.env.example` da YO'Q — `04-06` uni o'sha faylga qo'shsa `_ENV_EXAMPLE_TODO` dan ham OLIB TASHLASHI shart (darvoza aks holda qizaradi).

**`04-07` (tik/scheduler) uchun:** `CAPTURE_AUTH_LOCKING_CODES` va `CAPTURE_DEFER_CODES` metadan hosila; `capture_lease_seconds`/`capture_batch_size` `Settings` da (ular ham `_ENV_EXAMPLE_TODO` da). `app/schemas.py` `CAPTURE_JOB_ERROR_CODES` ni IMPORT qilishi shart, qayta yozmasligi.

**`04-08` (alert) uchun:** `alerts_enabled` tayyor; bo'sh token bilan `log.warning` yozish O'SHA rejaning ishi. **Va `censor_secrets` qamrovi bandi ham o'sha yerda** (yuqoridagi topilma).

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan 7 fayl + o'zgartirilgan 1 fayl** — hammasi diskda tekshirildi (`MISSING COUNT: 0`).
- **Oltala commit `git log` da tasdiqlandi:** `da71c8d`, `5b44455`, `4185fb4`, `dc1dca4`, `7ce7019`, `9aea493` — bazasi `f55bde9`.
- **Reja artefakt shartlari o'lchandi:** `quality.py` 485 qator (talab ≥ 150) va `LOAD_TRUNCATED_IMAGES` ni o'z ichiga oladi; `object_key.py` da `def object_key`; `capture_errors.py` da `CAPTURE_ERROR_CODES`; `settings.py` da `retention_full_days` va `QualityThresholds`; `test_quality_filter.py` da `frame_bytes`.
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin orkestrator tomonidan yangilanadi.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-04*
