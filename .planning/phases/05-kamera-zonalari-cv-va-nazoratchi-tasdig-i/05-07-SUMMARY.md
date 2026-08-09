---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 07
subsystem: detektor-yadrosi
tags: [cv-service, onnx, supervision, polygon-zone, postprocess, no-stub-gate, model-marker, ai-02]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 02
    provides: "`cv-service` toolchain (`cv-tests` konteyneri), uch qatlamli litsenziya devori, `tests/fixtures/detections.py` — GEOMETRIK FAKT bo'yicha nomlangan `sv.Detections` konstruktori (W0-7)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 05
    provides: "`sbozor_core.enums.OccupancyVerdict` — `occupied`/`empty`/`uncertain`; `occupancy_events.thresholds_version` (D-11 ning qator-darajasidagi langari)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 01
    provides: "`model` va `golden` pytest markerlari, `--strict-markers` ostida e'lon qilingan"
provides:
  - "`app/detector/postprocess.py` — sigmoid -> background ustuni -> `cxcywh`->`xyxy` -> confidence filtri; `raw_to_detections()`"
  - "`app/detector/zones.py` — `polygon_to_pixels()` + `zone_verdict()` + `UncertaintyThresholds` (chegaralar ARGUMENT, D-11)"
  - "`app/detector/session.py` — `DetectorSession`: jarayon-lokal ONNX sessiyasi, rezolyutsiya grafdan O'QILADI, `providers` ATAYIN"
  - "`app/detector/annotate.py` — `annotate_zone()` + `EVIDENCE_PREFIX`; asl kadr QAYTA YOZILMAYDI (T-05-32)"
  - "`tests/unit/test_detector_has_no_stub.py` — AST predikati: `InferenceSession` AYNAN bitta joyda, `Fake*`/`Stub*`/`Dummy*`/`Mock*` klass yo'q (T-05-29)"
  - "`tests/integration/test_onnx_session.py` — `model` markerli YAGONA test, `skipif` YO'Q (artefaktsiz YIQILADI)"
  - "`services/cv-service/tests/integration/` — `cv-service` ning integratsiya daraxti (05-08 uni kengaytiradi)"
affects: [05-08-detect-job, 05-10-noaniq-navbat, 05-11-kor-audit, 05-12-agregatsiya, 05-15-faza-darvozasi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kutilgan qiymat TEKSHIRILAYOTGAN KOD bilan hisoblanmaydi: `sigmoid()` chaqirilmaydi, ehtimolliklar qo'lda hisoblangan o'nlik literal"
    - "Background ustuni olib tashlanganda ustun INDEKSLARI massivi AYNAN o'sha `np.delete` bilan kesiladi — kafolat konstantaning qiymatidan MUSTAQIL"
    - "Sonli barqaror `sigmoid` ikki shoxli: `nan` chegara solishtirishida JIMGINA `False` beradi, ya'ni quti sababsiz tushib qolardi"
    - "Yaxlitlash `round` (`np.rint`), `floor` EMAS — `floor` ning xatosi TASODIFIY emas, BIR TOMONLAMA va u qayta konversiyalarda to'planadi"
    - "Kutubxona imzosi RESEARCH sitatasi bilan emas, `inspect.signature` bilan tekshiriladi — sitata to'liq bo'lmasligi mumkin"
    - "Soxta amalga oshirilish darvozasi AST bilan yuradi (`ast.parse` + `ClassDef`/`Call`), matn bilan emas — shunda darvozaning O'ZI taqiqlangan nomni docstringida yoza oladi"
    - "`model` markerli testda `skipif` YO'Q: `skip` «o'lchov bajarildi» degan YOLG'ON signal berardi"
    - "Verdikt bilan birga O'LCHOVNING O'ZI qaytariladi (`empty` ham o'z ishonchini olib keladi) — chegaralar keyin SQL bilan sozlanadi"

key-files:
  created:
    - services/cv-service/app/detector/__init__.py
    - services/cv-service/app/detector/postprocess.py
    - services/cv-service/app/detector/zones.py
    - services/cv-service/app/detector/session.py
    - services/cv-service/app/detector/annotate.py
    - services/cv-service/tests/unit/test_rfdetr_postprocess.py
    - services/cv-service/tests/unit/test_zone_verdict.py
    - services/cv-service/tests/unit/test_detector_has_no_stub.py
    - services/cv-service/tests/unit/test_zone_annotation.py
    - services/cv-service/tests/unit/test_detector_settings.py
    - services/cv-service/tests/integration/__init__.py
    - services/cv-service/tests/integration/test_onnx_session.py
  modified:
    - services/cv-service/app/settings.py
  deleted: []

key-decisions:
  - "⚠ O'LCHANGAN FAKT: `supervision` 0.30.0 ning `PolygonZone.__init__` da UCHINCHI parametr bor — `require_all_anchors: bool = True`. RESEARCH §B.4 ning imzo sitatasida u YO'Q edi. Standart `True` = AND, ya'ni `(CENTER, BOTTOM_CENTER)` juftligi yagona ankordan QAT'IYROQ bo'lib qoladi va D-09 ning MAQSADIGA (bottom-center qo'shni zonaga tushish xavfini yumshatish) ZID ishlaydi. Shuning uchun `DEFAULT_REQUIRE_ALL_ANCHORS = False` (OR) va ikkala rejim ham argument bilan tanlanadi hamda test bilan o'lchangan"
  - "⚠ O'LCHANGAN FAKT: `PolygonZoneAnnotator.annotate()` sahnani JOYIDA bo'yaydi va AYNAN o'sha obyektni qaytaradi. Himoyasiz kodda asl kadr massivi o'rnida bo'yalardi va ko'r auditning dalil zanjiri JIMGINA uzilardi — shuning uchun `annotate_zone()` nusxa ustida ishlaydi va bu holat test bilan qulflangan (T-05-32)"
  - "`class_id` MODELNING ASL yorliq fazosida qoladi: ustun indekslari massivi (`class_axis`) va ehtimolliklar AYNAN bir xil `np.delete` bilan kesiladi. Kafolat `BACKGROUND_CLASS_INDEX` ning QIYMATIDAN mustaqil — test arifmetikani o'lchaydi, konstantaning to'g'riligini emas"
  - "`BACKGROUND_CLASS_INDEX = 0` — TAXMIN, o'lchangan fakt EMAS (`[LOW confidence]`). Rasmiy hujjat «background ustunini olib tashlang» deydi, lekin INDEKSNI aytmaydi. Bu holat modul docstringida ochiq yozilgan va uni tekshirish `05-HUMAN-UAT` bandi"
  - "Rezolyutsiyaning AYNIQ SONI (`704` va h.k.) darvoza QILINMADI: `model` markerli test grafning O'Z qiymati bilan bizning o'qishimiz mos kelishini o'lchaydi, ya'ni «kod grafdan o'qiydimi?» degan savolni. Qattiq yozilgan son boshqa variantga o'tishda yolg'on-qizil berardi"
  - "`preprocess()` da `BGR -> RGB` — `cv2.imdecode` BGR beradi, ImageNet statistikasi esa RGB uchun. Tushirib qoldirilsa hech qanday istisno chiqmaydi, model shunchaki YOMONROQ ishlaydi va nosozlik «aniqlik past» bo'lib model sifatiga yozilardi"
  - "`EVIDENCE_PREFIX` — KOD konstantasi, sozlama EMAS (`worker.CV_QUEUE` bilan aynan bir xil qaror): prefiks muhitga chiqsa yozuvchi (05-08) bilan o'quvchi (`core-api` proxysi) jimgina boshqa yo'llarga qarab qolardi"
  - "Chegara INKLYUZIV ikkala modulda ham (`confidence == threshold` -> yuqorigi toifa). Ikki modulda ikki xil o'qilsa, chegarani sozlash natijani oldindan aytib bo'lmaydigan qilardi"
  - "`intra_op_num_threads` uchun benchmark O'TKAZILMADI va bu D-08/§B.3 ning bevosita talabi: «reja EPYC'da benchmarkni DARVOZA qilib qo'ymasin». `settings.py` dagi eskirgan «optimal qiymat 05-07 da o'lchanadi» va'dasi shu sababdan tuzatildi"

metrics:
  duration_minutes: 95
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 12
  files_modified: 1
  commits: 3
---

# Phase 5 Plan 07: Detektor yadrosi — xom tenzor, zona verdicti va ONNX sessiya — Summary

AI-02 ning idrok yadrosi qurildi va uning **chegarasi ochiq belgilandi**: `sv.Detections` chokidan pastdagi hamma narsa — arifmetika, geometriya, chegaralar — sintetik detektsiyalar bilan **to'liq isbotlandi**; chokdan yuqoridagi «model to'g'ri javob berdimi?» savoli esa **o'lchanmagan** holicha qoldi va hech qayerda yopilmadi.

## What Was Built

### Task 1 — `detector/postprocess.py`: xom tenzor arifmetikasi (`0381835`)

`raw_to_detections(dets, labels, *, frame_size, confidence_threshold)` — sof funksiyalar moduli: tarmoqqa chiqmaydi, bazaga tegmaydi, `Settings` ni bilmaydi.

Zanjir: `sigmoid` → background ustuni → `cxcywh` (normalangan) → `xyxy` (piksel) → confidence filtri.

**Modulning butun ma'nosi `_foreground_scores()` da.** `np.delete(probabilities, BG, axis=1)` dan keyin ustunlar qayta raqamlanadi, ya'ni kesilgan massivdagi `argmax` asl yorliq indeksi **emas**. Uni to'g'ridan-to'g'ri `class_id` qilib yozish — RESEARCH §B.2 ogohlantirgan **jimgina surilish**. Yechim: ustun indekslari massivi **aynan o'sha** `np.delete` bilan kesiladi, ya'ni kafolat `BACKGROUND_CLASS_INDEX` ning qiymatidan **mustaqil**.

20 test; kutilgan qutilar va ehtimolliklar **qo'lda hisoblangan literal** — `sigmoid()` kutilgan qiymatni olish uchun **chaqirilmagan**.

### Task 2 — `detector/zones.py`: 0..1 ↔ piksel va zona verdicti (`0b299c0`)

`polygon_to_pixels()` — Tuzoq 1 ning mexanizmi (`PolygonZone` piksel kutadi, AI-01 esa 0..1 saqlaydi). Yaxlitlash `np.rint`, `floor` **emas**, va sabab sistematik: `floor` har koordinatani pastga suradi, ya'ni har poligon o'ng va pastki chetidan qisqaradi va kamera ruxsati o'zgarganda chegara **har safar bir tomonga** siljiydi.

`zone_verdict()` — `sv.PolygonZone` ni sozlaydi va natijadan verdikt yasaydi. Nuqta-poligon hisobi **qo'lda yozilmadi**.

Chegaralar `UncertaintyThresholds` **argumenti** bilan kiradi (D-11); modul `Settings` ni import qilmaydi va teskari oynani (`low > high`) rad etadi.

30 test: ichkarida/tashqarida × past/o'rta/yuqori ishonch × oddiy/L-shakl.

### Task 3 — `session.py`, `annotate.py` va ikki darvoza (`6165787`)

`DetectorSession` — jarayon-lokal ONNX sessiyasi. `providers=["CPUExecutionProvider"]` **atayin** yoziladi; rezolyutsiya `session.get_inputs()[0].shape[2:4]` dan **o'qiladi**. Graf kontrakti (kirish nomi, chiqishlar soni, statik shakl) **ishga tushishda** tekshiriladi.

`annotate_zone()` — `sv.PolygonZoneAnnotator` bilan dalil rasmi, `EVIDENCE_PREFIX` alohida prefiks.

**Ikki darvoza:** `test_detector_has_no_stub.py` (AST predikati) va `test_onnx_session.py` (`model` markerli yagona test, `skipif` **yo'q**).

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| `cv-service` to'liq to'plami | `cv-tests pytest -q` | **93 yashil** (bazaviy 24 + yangi 69) |
| `cv-service` lint/tiplar | `cv-tests: ruff check + format --check + mypy` | toza (23 fayl) |
| Litsenziya devori (`torch` kirmadi) | `tests pytest tests/unit/test_license_fence.py -q` | 32 yashil |
| Root skanerlar | `tests pytest test_sentry_processes + test_runtime_deps + test_license_fence -q` | 61 yashil |
| `model` marker YIG'ILADI | `cv-tests pytest -m model --collect-only` | **1 ta** |
| `model` marker standart zanjirda YIG'ILMAYDI | `cv-tests pytest --collect-only` | `test_onnx_session.py: 2` (markerli test deselect) |
| ⚠ **Artefaktsiz `model` testi SKIP EMAS** | `cv-tests pytest -m model` | **FAILED** — xabar artefakt yo'lini va eksport retseptini nomlaydi |
| `torch`/`rfdetr` importi | `grep -cE "^\s*(import\|from) (torch\|rfdetr)" postprocess.py` | `0` |
| `Settings` importi | `grep -cE "^\s*(from\|import) app\.settings" zones.py` | `0` |
| Qo'lda nuqta-poligon | `grep -cE "^\s*def .*point.*polygon" zones.py` | `0` |
| Kutubxona mexanizmi | `grep -c "PolygonZone(" zones.py` | `3` |
| `providers` atayin | `grep -c "CPUExecutionProvider" session.py` | `2` |
| Rezolyutsiya o'qiladi | `grep -c "get_inputs()\[0\].shape" session.py` | `3` |

### Sabotajlar — to'rttasi ham QIZIL berdi

| # | Nima buzildi | Kutilgan darvoza | Natija |
|---|---|---|---|
| A | `BACKGROUND_CLASS_INDEX` `0` → `1` | qo'lda hisoblangan `class_id` | **5 ta** FAILED (surilish, chegara va konvertatsiya testlari) |
| B | `np.rint` → `np.floor` | yaxlitlash qoidasi | `test_rounding_is_arithmetic_and_not_floor` FAILED |
| C | `anchors` argumenti e'tiborsiz qoldirildi | ankor sozlamasi | `..._switching_the_anchor...` va `..._require_all_anchors...` FAILED |
| D | `class FakeDetectorSession` qo'shildi | AST prefiks predikati | `..._no_faked_implementation_class...` FAILED |
| E | Ikkinchi `InferenceSession(...)` chaqiruvi | AST sanoq + egalik | `..._exactly_one_place` va `..._is_the_detector_session` FAILED |

Har biri `cp` bilan snapshotdan tiklandi (`git checkout --` **ishlatilmadi**).

## Deviations from Plan

### 1. [Rule 1 - Bug] RESEARCH §B.4 dagi `PolygonZone` imzosi TO'LIQ EMAS — o'lchov bilan topildi

- **Qachon:** Task 2, `inspect.signature` bilan haqiqiy API tekshirilayotganda
- **Muammo:** RESEARCH §B.4 imzoni ikki parametrli qilib sitata qilgan (`polygon`, `triggering_anchors`). `supervision` 0.30.0 ning haqiqiy imzosida **uchinchi** parametr bor: `require_all_anchors: bool = True`.
- **Nega muhim:** standart `True` — bu **AND**. O'lchandi (markazi ichkarida, pastki markazi tashqarida bo'lgan quti ustida):

  | Ankorlar | `require_all` | `trigger()` |
  |---|---|---|
  | `(CENTER,)` | — | `True` |
  | `(BOTTOM_CENTER,)` | — | `False` |
  | `(CENTER, BOTTOM_CENTER)` | `True` (AND) | **`False`** |
  | `(CENTER, BOTTOM_CENTER)` | `False` (OR) | **`True`** |

  D-09 juftlikni aynan «`BOTTOM_CENTER` qo'shni zonaga tushib qolishi mumkin» degan xavfni **yumshatish** uchun tanlagan (RESEARCH §B.4, Tuzoq 2). AND ostida juftlik bu xavfni yumshatmaydi — **kuchaytiradi**: u har ikkala ankorni talab qilib, yagona ankordan qat'iyroq bo'ladi va aynan o'sha savat-qo'shni-zona holatida detektsiyani **yo'qotadi**.
- **Tuzatish:** `require_all_anchors` yashirilmadi — u ochiq argument, standarti `DEFAULT_REQUIRE_ALL_ANCHORS = False` (kutubxona standartidan **ongli chekinish**, sabab modul docstringida o'lchov bilan yozilgan). Ikkala rejim ham test bilan qulflandi.
- **⚠ Qamrov chegarasi yashirilmadi:** qulflangan narsa **qiymat emas, mexanizm**. OR ostida yolg'on-musbat (qo'shni rastaning savati) ko'payishi mumkin; to'g'ri javobni faqat real Karmana kadri aytadi. Bu `05-HUMAN-UAT` bandi.
- **Commit:** `0b299c0`

### 2. [Rule 2 - Kritik funksionallik] `PolygonZoneAnnotator` asl kadrni JOYIDA bo'yaydi

- **Qachon:** Task 3, `annotate.py` yozilishidan oldingi o'lchovda
- **O'lchov (taxmin emas):** `out = annotator.annotate(scene=frame, ...)` → `out is frame` = `True`, `frame` o'zgardi = `True`.
- **Nega kritik:** T-05-32 ning dispozitsiyasi `mitigate` va u «asl kadr **qayta yozilmaydi**» deydi. Nusxasiz kodda chaqiruvchining massivi o'rnida bo'yalardi; o'sha massiv omborga qayta yozilsa yoki nazoratchiga «asl kadr» deb ko'rsatilsa, **ko'r auditning dalil zanjiri jimgina uzilardi** — hech qanday xatosiz.
- **Tuzatish:** `annotate_zone()` har doim `frame.copy()` ustida ishlaydi.
- **Commit:** `6165787`

### 3. [Rule 2 - Kritik funksionallik] Rejaning fayl ro'yxatidan tashqaridagi ikkita test fayli

Reja Task 3 uchun `annotate.py` va `settings.py` ni sanaydi, lekin ularni **o'lchaydigan** fayl bermaydi. Ikkalasi ham qabul mezoni yoki tahdid reyestri bilan talab qilingan, ya'ni ularni test siz qoldirish «`mitigate`» so'zini izohga aylantirardi.

| Fayl | Nega qo'shildi |
|---|---|
| `tests/unit/test_zone_annotation.py` (5 test) | **T-05-32** `mitigate` — `mitigate` o'lchanadigan da'vo, izoh emas. Sintetik `np.zeros` kadr bilan to'liq testlanadi, real kadr KERAK EMAS |
| `tests/unit/test_detector_settings.py` (7 test) | Task 3 ning qabul mezoni: «`CV_MODEL_PATH` mavjud bo'lmagan yo'lga qo'yilganda ilova **ishga tushishda** yiqiladi». `field_validator` 05-02 da yozilgan edi, lekin uni **xulq bilan** o'lchaydigan test yo'q edi — mezon kod o'qib tasdiqlanardi |

### 4. [Rule 1 - Bug] O'ZIM YOZGAN testda YOLG'ON-YASHIL topildi va tuzatildi

- **Qachon:** Task 3, `test_detector_settings.py` birinchi yugurishida
- **Muammo:** `test_an_implausible_thread_count_is_rejected` `cv_model_path=DEFAULT_MODEL_PATH` bergan edi. O'sha yo'l (`/app/models/rfdetr-large.onnx`) test konteynerida **yo'q** (`Dockerfile` ning `dev` bosqichi modelni ko'chirmaydi), ya'ni `ValidationError` **model yo'li uchun** chiqardi. Test yashil edi, lekin chegara tekshiruvi **umuman ishlamagan** bo'lsa ham yashil bo'lar edi.
- **Tuzatish:** `tmp_path` da haqiqiy fayl yaratiladi va yiqilgan maydonlar to'plami **aynan** `{"cv_intra_op_threads"}` ekani tasdiqlanadi.
- **Sabab qayd etilsin:** bu 05-03 ning darsining aynan takrori — «test o'tdi» va «test o'zi so'ragan narsani o'lchadi» ikki xil savol.

### 5. [Rule 3 - Bloklovchi] `mypy` ikki modul nomidan yiqildi

- **O'lchov:** `Source file found twice under different module names: "integration.test_onnx_session" and "tests.integration.test_onnx_session"` — **butun tekshiruv to'xtadi**.
- **Sabab:** `tests/` paket **emas**, `tests/integration/` esa paket, ya'ni fayl `integration.test_onnx_session` nomiga ega. Men yozgan `import tests.integration.test_onnx_session` o'sha faylga **ikkinchi nom** bergan edi.
- **Tuzatish:** import olib tashlandi, uning o'rniga `sys.modules[__name__]`.
- **Bu 05-02 da allaqachon o'lchangan nosozlikning takrori** (`fixtures.detections` ↔ `tests.fixtures.detections`) va sabab shu yerda ham xuddi o'sha.

### 6. Rejadan ongli farqlar (mahsulot qarorlari)

| Reja aytgan | Bajarildi | Sabab |
|---|---|---|
| `model` testida «rezolyutsiya **kutilgan qiymatga** teng» | Grafning **o'z** qiymati bilan bizning o'qishimiz mos kelishi tekshiriladi | «704 to'g'rimi?» — variantga tegishli savol va uning javobi artefakt bilan keladi. Qattiq yozilgan son boshqa variantga o'tishda **yolg'on-qizil** berardi, ya'ni darvoza noto'g'ri narsani qo'riqlardi. Tekshirilayotgan MEXANIZM — «kod grafdan o'qiydimi?» — va u to'liq o'lchandi |
| `settings.py` (Task 3 fayli) | Faqat **bitta docstring** tuzatildi | `cv_model_path` validatori ham, `cv_intra_op_threads` chegaralari ham 05-02 da allaqachon yozilgan edi. Funksional o'zgarish **kerak emas edi**; buning o'rniga eskirgan va'da tuzatildi (pastga qarang) va xulq test bilan qulflandi |
| — | `settings.py`: «optimal qiymat 05-07 da o'lchanadi» → D-08 ning ochiq bayoni | Va'da **bajarilmadi va bajarilmasligi kerak edi**: RESEARCH §B.3 «reja EPYC'da benchmarkni **darvoza qilib qo'ymasin**» deydi va arifmetika savolni ahamiyatsiz qiladi (~47 daq CPU/kun). Eskirgan satr keyingi o'quvchiga bajarilmagan ish bo'lib ko'rinardi |
| `run()` `dets`/`labels` ni qaytaradi | Pozitsion tartibda, tartib `[LOW confidence]` deb **ochiq** belgilandi | Rasmiy hujjat ikkala tenzorni nomlaydi, lekin **tartibni aytmaydi**. Nom bo'yicha izlashning ikkinchi shoxi yozilmadi — uni birorta test qoplamasdi, ya'ni u sinalmagan kod bo'lardi. Tartib `model` markerli test bilan haqiqiy artefaktda o'lchanadi |
| — | `EXPECTED_OUTPUT_COUNT` tekshiruvi **qo'shildi** | Boshqa shakldagi eksport (masalan segmentatsiya varianti) uchinchi tenzor qo'shardi va pozitsion o'qish `labels` o'rniga boshqa tenzorni olardi — **istisnosiz**, bema'ni ballar bilan |
| — | `preprocess()` da `BGR → RGB` | Rasmiy misol PIL (RGB) ishlatadi, biz `cv2` (BGR). Almashtirilmasa istisno **chiqmaydi** — model yomonroq ishlaydi va nosozlik model sifatiga yozilardi |

## ⚠ Isbotlanmagan qoldi — ATAYIN va OCHIQ

Bu bo'lim `05-VALIDATION.md` ning ikki qatlamli bo'linishini bajaradi. **Quyidagilarning hech biri bu rejaning yashil to'plami bilan yopilmagan va yopilishi ham mumkin emas.**

| Nima | Nega bugun isbotlanmaydi | Kim/qachon |
|---|---|---|
| **Modelning aniqligi** — RF-DETR ning band/bo'sh qarori to'g'rimi | Haqiqat (real Karmana kadrlari) YO'Q. 93 yashil test **mexanikani** o'lchaydi, modelni **emas** | Oltin to'plam darvozasi (W0-9) — real kadrlar kelganda kodsiz uyg'onadi |
| `BACKGROUND_CLASS_INDEX = 0` to'g'rimi | Rasmiy hujjat indeksni aytmaydi (`[LOW confidence]`). Arifmetika bu qiymatdan mustaqil to'g'ri, lekin **qaysi ustun** ekani artefaktdan o'lchanadi | `05-HUMAN-UAT`: `pytest -m model` + yorliqlar taqsimoti |
| `dets`/`labels` ning pozitsion tartibi | Hujjat tartibni aytmaydi | `05-HUMAN-UAT`: `pytest -m model` |
| Grafning aniq rezolyutsiyasi | Artefakt bilan keladi | `05-HUMAN-UAT`: `pytest -m model` |
| `require_all_anchors = False` (OR) **to'g'ri tanlovmi** | Mexanizm o'lchandi, **qiymat** esa faqat real kadrda hal bo'ladi: OR yolg'on-musbatni ko'paytirishi mumkin | Nazoratchi + ijrochi, Phase 0 kadrlari |
| Dalil rasmi nazoratchi uchun **tushunarlimi** | Inson o'lchovi (rang, qalinlik, yorliq joyi) | `05-HUMAN-UAT` |
| CPU kechikishi EPYC'da | D-08/§B.3 bo'yicha **atayin darvoza qilinmadi** | Operatsion o'lchov, fazani bloklamaydi |

## Known Stubs

**Yo'q.** Bu rejada soxta ma'lumot manbai ham, joylashtirilmagan komponent ham yaratilmadi:

- `postprocess`, `zones`, `annotate` — sof funksiyalar, hammasi to'liq amalga oshirilgan va o'lchangan;
- `DetectorSession` — to'liq amalga oshirilgan; u hali **birorta compose servisi tomonidan yuritilmaydi**, chunki `WORKER_STARTUP` ga ulash **05-08 ning ishi** (reja shunday belgilagan). Bu holat sinalmagan kod **emas**: `test_onnx_session.py` uni haqiqiy artefaktda o'lchaydi, `test_detector_has_no_stub.py` esa uning yagona egalik joyini AST bilan qulflaydi;
- Soxta detektorning **mavjud emasligi** darvoza bilan o'lchanadi (T-05-29) va sabotaj bilan tasdiqlangan.

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-28 | mitigate | `CV_MODEL_PATH` `field_validator` da **ishga tushishda** tekshiriladi va bu endi **xulq bilan** o'lchanadi (`test_detector_settings.py`, 7 test — katalog fayl o'rniga qabul qilinmaydi). Artefakt `COPY` bilan build paytida kiradi; manba va retsept `ops/models/README.md` da |
| T-05-29 | mitigate | `test_detector_has_no_stub.py` — AST predikati, 5 test: `InferenceSession` **aynan bitta** joyda, egasi `detector/session.py`, `Fake*/Stub*/Dummy*/Mock*` klass yo'q, `providers=` atayin berilgan. Ikki sabotaj bilan o'lchandi. Noma'lum holatda `pytest.fail` — «o'tkazib yuborish» shoxi **yo'q** |
| T-05-30 | mitigate | `preprocess()` `cv2.imdecode` ning **`None`** qaytishini ochiq `ValueError` ga aylantiradi (o'lchandi: buzuq baytda istisno chiqmaydi). Kadr o'lchami 4-faza sifat filtri bilan chegaralangan; `detect` ning qachon ishga tushishi 05-08 da |
| T-05-31 | mitigate | `zones.py` da `ultralytics`/`torch`/`rfdetr` importi darvoza ostida (3 test); `sv.Detections` xom chiqishdan **qo'lda** quriladi; litsenziya devori (05-02) hamon 32 yashil |
| T-05-32 | mitigate | `EVIDENCE_PREFIX` alohida va u **kod** konstantasi; `annotate_zone()` **nusxa** ustida ishlaydi va asl kadrning o'zgarmasligi test bilan o'lchangan (in-place bo'yash **tasdiqlangan xavf** edi) |

**Yangi tahdid yuzasi topilmadi.** Bu reja tarmoq nuqtasi ham, auth yo'li ham, sxema o'zgarishi ham qo'shmadi — barcha yangi kod jarayon ichida ishlaydigan sof hisob va bitta mahalliy fayldan o'qish.

## Observations for later plans (fixed emas — scope tashqarisi)

1. **`05-08` uchun:** `DetectorSession` `WORKER_STARTUP` ga ulanishi kerak (`worker.py` ning `_open_worker_resources` idagi «OG'IR RESURSLAR ... 05-08 da SHU ILMOQQA qo'shiladi» izohi allaqachon joyni ko'rsatib turibdi). Sessiya **jarayon-lokal**, ya'ni `WORKER_SHUTDOWN` da yopiladigan tarmoq resursi yo'q — ilmoqning bo'sh qolishi normal.
2. **`05-08` uchun:** `zone_verdict()` `thresholds`, `anchors` va `require_all_anchors` ni **majburiy** argument sifatida talab qiladi. Standartlar `zones.DEFAULT_TRIGGERING_ANCHORS` va `zones.DEFAULT_REQUIRE_ALL_ANCHORS` da — chaqiruvchi tanlovni **ko'rmasdan** qila olmaydi, bu ataylab.
3. **`05-15` uchun:** `model` markerli test **CI'da yurmaydi**. Faza darvozasi «`pytest -m model` bir marta yuritildimi?» degan savolni `05-HUMAN-UAT` bandi sifatida ko'rsatishi kerak — aks holda artefakt hech qachon tekshirilmasligi mumkin.
4. **Worktree muhitining sharti (05-02 ning 3-kuzatuvi tasdiqlandi):** yangi checkout'da `.env` va `ops/seaweedfs/s3.json` yo'q (ikkalasi ham gitignored). `cv-tests` ularsiz ham ishlaydi (u sirlarni talab qilmaydi), lekin `docker compose` o'zgaruvchi almashtirishda ogohlantirish beradi. Bu rejada ular asosiy checkout'dan **nusxalandi** va commit **qilinmadi**.

## Self-Check: PASSED

Barcha e'lon qilingan fayllar diskda va uchala commit ham tarixda mavjud (quyida tekshirildi).
