---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 02
subsystem: cv-service-poydevori
tags: [cv-service, uv-lock, license-fence, onnx, supervision, taskiq, sentry-gate, docker, wave-0]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 13
    provides: "`tests/unit/test_sentry_processes.py` — `compose.yaml` dan HOSILA qilingan jarayon darvozasi (bu reja uni IKKINCHI kod bazasi uchun kengaytirdi)"
  - phase: 04-snapshot-pipeline
    plan: 12
    provides: "`app/observability.py` — `init_sentry` + ikki ilmoq naqshi"
  - phase: 04-snapshot-pipeline
    plan: 9
    provides: "`app/api/internal/self_check.py::EXPECTED_COMPONENTS` — «kim BO'LISHI KERAK?» reyestri"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 1
    provides: "`tests/unit/test_runtime_deps.py` — manifest darvozasining to'liq shabloni va `_requirement_name()`"
provides:
  - "`services/cv-service/` — loyihaning IKKINCHI Python bog'liqlik to'plami: o'z `pyproject.toml`, `uv.lock`, `Dockerfile` (`dev`/`runtime`) va o'z test daraxti (W0-2)"
  - "`tests/unit/test_license_fence.py` — UCH QATLAMLI litsenziya devori (manifest / `uv.lock` / o'rnatilgan metadata predikati); `rfdetr`, `rfdetr-plus`, `torch`, `ultralytics` mexanik rad etiladi (W0-1, D-03, D-04)"
  - "`compose.yaml` dagi `cv-service` (profilsiz, sof worker) va `cv-tests` (test profili) — UCHINCHI servis (W0-11)"
  - "`self_check.EXPECTED_COMPONENTS` ga `cv_detect` — bugun `never_seen`, 05-08 uni yozadigan qiladi"
  - "`services/cv-service/tests/fixtures/detections.py` — GEOMETRIK FAKT bo'yicha nomlangan sintetik `Detections` konstruktori (W0-7)"
  - "`ops/models/README.md` — ONNX artefaktining yagona haqiqat manbai va eksport retsepti (W0-12, D-24)"
  - "`npm run cv:test` / `npm run cv:lint` va ular `npm run gate` zanjirida"
  - "`tests/unit/test_sentry_processes.py` — kod ildizi bo'yicha tarmoqlanish: begona kod bazasi endi JIMGINA yashil bo'lolmaydi"
  - "`services/cv-service/tests/unit/test_sentry_entrypoints.py` — obyekt darajasidagi Sentry darvozasi, `cv-tests` konteynerida"
affects: [05-07-detektor, 05-08-detect-job, 05-15-faza-darvozasi, 06-billing]

# Tech tracking
tech-stack:
  added:
    - "onnxruntime 1.28.0 — CPU inference (torch O'RNIGA: 58 MB vs ~800 MB)"
    - "supervision 0.30.0 — `PolygonZone` va `Detections` (MIT)"
    - "opencv-python-headless 4.14.0.94 — dekod/kesish, GTK/X11siz"
    - "numpy 2.5.1 · Pillow 12.3.0 · scipy (supervision orqali)"
  patterns:
    - "Litsenziya darvozasi MANIFESTDAN OLDIN yoziladi va birinchi commit'da QIZIL turadi — `uv add` dan keyin qo'yilgan devor allaqachon sodir bo'lgan ishni tasdiqlardi"
    - "Lockfile qatlami manifest qatlamidan KUCHLIROQ: `rfdetr-plus` manifestda hech qachon ko'rinmaydi, u faqat `[plus]` ekstrasi orqali tranzitiv keladi"
    - "Litsenziya predikati NOMLAR RO'YXATI emas (`LicenseRef-*`/AGPL), lekin u IDENTIFIKATORNI matndan ajratishi shart — aks holda litsenziya MATNI yolg'on-qizil beradi"
    - "Ikkinchi kod bazasi paydo bo'lganda `compose.yaml` dan hosila darvoza KOD ILDIZINI ham hosila qilishi shart, aks holda u nomdosh paketni jimgina noto'g'ri image'dan o'qiydi"
    - "Ikkinchi toolchain root `ruff`/`mypy` dan ISTISNO qilinadi — bitta faylni ikki konfiguratsiya tekshirsa ular ajralib ketadi"
    - "Fixture GEOMETRIK FAKT bilan nomlanadi va nom aytgan fakt ARIFMETIK KAFOLAT bilan ta'minlanadi (`box_center_in_polygon` qavariq bo'lmagan shaklda YIQILADI)"
    - "Skanerlanadigan fayl o'z tabusining nomini YOZMAYDI — qoida va taqiqlangan tokenlar TEST faylining docstringida yashaydi"

key-files:
  created:
    - tests/unit/test_license_fence.py
    - ops/models/README.md
    - services/cv-service/pyproject.toml
    - services/cv-service/uv.lock
    - services/cv-service/Dockerfile
    - services/cv-service/README.md
    - services/cv-service/app/__init__.py
    - services/cv-service/app/settings.py
    - services/cv-service/app/observability.py
    - services/cv-service/app/worker.py
    - services/cv-service/app/main.py
    - services/cv-service/tests/conftest.py
    - services/cv-service/tests/unit/__init__.py
    - services/cv-service/tests/unit/test_sentry_entrypoints.py
    - services/cv-service/tests/unit/test_detection_fixtures.py
    - services/cv-service/tests/fixtures/__init__.py
    - services/cv-service/tests/fixtures/detections.py
  modified:
    - compose.yaml
    - package.json
    - .gitignore
    - pyproject.toml
    - services/core-api/app/api/internal/self_check.py
    - tests/unit/test_sentry_processes.py
    - tests/integration/test_capture_schedule.py
  deleted: []

key-decisions:
  - "Litsenziya devori uchinchi qatlamda `License` erkin matn maydonini FAQAT identifikator uzunligida o'qiydi. O'lchov: `scipy` ning `License` maydoni 47 567 belgi (vendorlangan uchinchi tomon matnlari) va uning ichida `Affero` uchraydi, haqiqiy litsenziyasi esa BSD. Bu yolg'on-qizil faqat IKKINCHI muhitda (cv runtime image) ko'rindi — birinchi muhitda darvoza yashil edi"
  - "`test_sentry_processes.py` kod ildizini `build.dockerfile` dan chiqaradigan qilib kengaytirildi. Usiz `cv-service` uchun `importlib.import_module('app.worker')` `core-api` ning modulini qaytarardi (o'lchandi: `/app/services/core-api/app/worker.py`, ichida `init_sentry(` BOR) — ya'ni darvoza yashil bo'lib, HECH NIMANI o'lchamasdi"
  - "Paket nomi `app` bo'lib qoldi (`cv_app` ga qayta nomlanmadi): keyingi rejalarda `services/cv-service/app/...` yo'li ~30 marta yozilgan. Nomdoshlikning narxi darvozada to'landi, rejalarda emas"
  - "`cv-service` konteyneri — SOF WORKER (`taskiq worker app.worker:broker`) va unga healthcheck YOZILMADI. `nc -z` uchun port ochish o'z portiga o'zi javob beradigan yuza bo'lardi; yagona ishonchli signal — `cv_detect` yurak urishi va `/internal/self-check`"
  - "`cv-tests` ning `working_dir` i `/app` EMAS, `/app/services/cv-service`: `pytest`/`ruff`/`mypy` uchalasi ham ikkinchi `pyproject.toml` ni topishi shart, aks holda ular repo ildizidagi konfiguratsiyani olib `core-api` to'plamini shu image'da yuritardi"
  - "`services/cv-service/tests/` PAKET QILINMADI (`__init__.py` yo'q) — repo ildizidagi `tests/` bilan aynan bir xil shakl. Paket qilinsa `fixtures.detections` va `tests.fixtures.detections` bitta faylning ikki nomi bo'lardi va `mypy` uni rad etardi"
  - "Root `pyproject.toml` `ruff`/`mypy` dan `services/cv-service` istisno qilindi. O'lchov: `mypy .` `Duplicate module named \"app\"` bilan BUTUN tekshiruvni to'xtatadi. Filtr `package.json` da emas, `pyproject.toml` da — o'sha faylning `:27-33` dagi o'z qoidasi bo'yicha"
  - "Navbat nomi (`sbozor:cv`) KODDA konstanta, sozlamada emas — `core-api::JOBS_QUEUE` bilan bir xil qaror. Ikki servis bitta navbatdan o'qisa `BRPOP` vazifani tasodifiy jarayonga berardi va u yerda kerakli modul umuman yo'q"
  - "`REDIS_URL` o'rniga `VALKEY_URL` — repo bo'ylab yagona nom; yangi nom kiritish `compose.yaml` bilan `Settings` ni jimgina ajratardi"
  - "`box_center_in_polygon` qavariq bo'lmagan poligonda `ValueError` beradi: kafolat tepaliklar o'rtachasining qavariq kombinatsiya ekanligiga tayanadi, ya'ni boshqa shaklda funksiya NOMI yolg'on bo'lardi"

metrics:
  duration_minutes: 105
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 17
  files_modified: 7
  commits: 5
---

# Phase 5 Plan 02: `cv-service` poydevori va litsenziya devori — Summary

Loyihaning ikkinchi Python bog'liqlik to'plami tug'ildi va u tug'ilishidan **oldin** uch qatlamli litsenziya devori qo'yildi; `torch` ning ishlab chiqarish image'ida yo'qligi haqiqiy `--no-dev` build'idan o'lchandi, faylni o'qib emas.

## What Was Built

### Task 1 — Litsenziya devori, manifestdan OLDIN (`7b88228`)

`tests/unit/test_license_fence.py` — **uch qatlam**, va har birining o'z quyi chegarasi bor:

| Qatlam | Manba | Nimani ushlaydi |
|---|---|---|
| (1) manifest | `services/cv-service/pyproject.toml` (`tomllib`) | E'lon qilingan NIYAT — ikkala guruh ham (`[project]` va `dev`) |
| (2) lockfile | `services/cv-service/uv.lock` (MATN sifatida) | Hal qilingan graf — **tranzitiv** tortish ham |
| (3) metadata | `importlib.metadata.distributions()` | `LicenseRef-*` / AGPL **predikati** — nomlar ro'yxati emas |

`FORBIDDEN_PACKAGES` ichida `rfdetr` ning **O'ZI** ham bor va sabab D-04: `torch` uning ekstrasi emas, **majburiy** bog'liqligi. Nom normallashtirish `test_runtime_deps` dan **import qilinadi**, nusxa olinmaydi.

**O'lchangan qizillik (kutilgan holat):** Task 2 dan oldin ishga tushirilganda `29 error + 3 passed` — 29 tasi fixture bosqichida yiqiladi va xabar aynan yetishmayotgan faylni nomlaydi (`services/cv-service/pyproject.toml`, keyin `uv.lock`). Uchtasi (3-qatlam) yashil, chunki u `core-api` muhitini o'lchaydi va u mavjud. Bu farq test docstringida ochiq yozilgan — soxta qamrov da'vosi qilinmadi.

Yana: `ops/models/README.md` (artefaktning yagona haqiqat manbai, eksport retsepti, nega repoda saqlanmaydi), `.gitignore` ga `ops/models/*.onnx`, `package.json` ga `cv:test`/`cv:lint` va ular `gate` zanjirida.

### Task 2 — `cv-service`: ikkinchi to'plam, image, minimal ilova (`15b37ca`)

`services/cv-service/` — `pyproject.toml` + `uv.lock` (91 paket) + uch bosqichli `Dockerfile` + `README.md` + `app/` (settings, observability, worker, main).

`compose.yaml` ga ikki servis: `cv-service` (profilsiz, `taskiq worker`, port YO'Q, sirlar `:-` standartsiz) va `cv-tests` (`test` profili, `dev` target, `SENTRY_DSN` **berilmaydi**).
`self_check.EXPECTED_COMPONENTS` ga `cv_detect` — bugun `never_seen`, `healthy` ni buzmaydi.

### Task 3 — `sv.Detections` konstruktori (`e35076f`)

`services/cv-service/tests/fixtures/detections.py`: `detections_at()`, uch poligon (`unit_square`, `l_shape`, `self_intersecting`) va ikki quti yordamchisi. Nomlar **faqat geometrik fakt** aytadi; qoida va taqiqlangan tokenlar ro'yxati `test_detection_fixtures.py` ning docstringida (skanerlanadigan faylda emas — 03-07 darsi).

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| Ishlab chiqarish image'ida `torch` yo'q | `docker compose run cv-service python -c "import torch"` | `ModuleNotFoundError` ✅ |
| Prod image tarkibi (`--no-dev`) | `importlib.util.find_spec` bo'yicha skan | `onnxruntime/supervision/cv2/numpy/PIL/taskiq/fastapi/sbozor_core` **BOR**; `torch/torchvision/rfdetr/ultralytics/pytest/ruff/mypy/respx/testcontainers` **YO'Q**; 78 distributiv |
| `opencv` varianti | prod image | faqat `opencv-python-headless` |
| Lockfileda taqiq | `grep -E '^name = "(rfdetr\|torch\|ultralytics\|boto3\|opencv-python)"'` | 0 natija |
| `cv-tests` da CV kutubxonalari | `python -c "import onnxruntime, supervision, cv2, numpy"` | `ok` |
| Litsenziya devori | `pytest tests/unit/test_license_fence.py -q` | 32 yashil |
| Task 2 verify | `pytest test_license_fence + test_sentry_processes + test_compose_sim_env -q` | 42 yashil |
| `cv-service` to'plami | `cv-tests pytest -q` | 24 yashil |
| `cv-service` lint | `cv-tests: ruff check + format --check + mypy` | toza (11 fayl) |
| **Root to'liq to'plam** | `tests pytest -q` | **1921 yig'ildi, 81 skip, 0 failed, 0 error** (bazaviy 1889 + 32 yangi) |
| Root lint | `tests: ruff check + format --check + mypy .` | toza (253 formatlangan, 245 mypy) |
| `ports:` sanog'i | `grep -cE '^[[:space:]]+ports:' compose.yaml` | **1** — o'zgarmagan |
| ONNX ignore | `git check-ignore ops/models/rfdetr-large.onnx` | ✅ |

### Sabotajlar — beshtasi ham QIZIL berdi

| # | Nima buzildi | Kutilgan darvoza | Natija |
|---|---|---|---|
| 1 | `pyproject.toml` ga `torch==2.13.0` | (1) manifest | `test_forbidden_package_is_absent_from_both_groups[torch]` FAILED |
| 2 | `uv.lock` ga `name = "rfdetr-plus"` bloki | (2) lockfile | `..._from_the_lockfile[rfdetr-plus]` FAILED — **manifest tegilmagan holda**, ya'ni 2-qatlam haqiqatan kuchliroq |
| 3 | `cv-service/app/worker.py` dan `init_sentry` olib tashlandi | root + mirror Sentry | IKKALASI ham FAILED (root xabarida `code_root = /app/services/cv-service`) |
| 4 | `np.zeros` → `np.empty` | fixture token skani | `test_fixture_module_never_names_a_verdict[empty]` FAILED |
| 5 | `import supervision as sv` qo'shildi | fixture chegarasi | `test_fixture_module_does_not_import_the_zone_machinery` FAILED |

Har biri `cp` bilan snapshotdan tiklandi (`git checkout --` ishlatilmadi).

## Deviations from Plan

### 1. [Rule 1 - Bug] Litsenziya predikati litsenziya MATNINI identifikator deb o'qirdi

- **Qachon:** Task 2, prod image o'lchanayotganda
- **Muammo:** `cv-service` ning ishlab chiqarish muhitida 3-qatlam `scipy` ni AGPL deb belgiladi. Sabab: `scipy` ning `License` maydoni **47 567 belgi** vendorlangan litsenziya matni va uning ichida `Affero` so'zi uchraydi; haqiqiy litsenziyasi — `Classifier: License :: OSI Approved :: BSD License`.
- **Nega birinchi muhitda ko'rinmadi:** `core-api` muhitida (97 distributiv) `scipy` yo'q — ya'ni darvoza yashil edi va xato **faqat ikkinchi muhitda** ochildi.
- **Tuzatish:** `License` erkin matn maydoni endi FAQAT identifikator shaklida (`<= 100` belgi, satr ko'chirishsiz) o'qiladi. `License-Expression` va `Classifier: License ::` — boshqariladigan lug'at, ular TO'LIQ skanerlanadi, ya'ni qamrov yo'qolmadi (`rfdetr-plus` birinchisida, `ultralytics` ikkinchisida e'lon qiladi).
- **Qayta o'lchov:** ikkala muhitda ham `hits []` (89 va 97 distributiv).
- **Commit:** `15b37ca`

### 2. [Rule 2 - Kritik funksionallik] `test_sentry_processes.py` kengaytirildi (rejaning fayl ro'yxatidan tashqarida)

- **Muammo:** darvoza `SENTRY_DSN` olgan har servis uchun `importlib.import_module(<modul>)` qiladi. `cv-service` ning paketi ham `app` deb ataladi, root `tests` konteynerining `pythonpath` i esa faqat `services/core-api` ni ko'radi.
- **O'lchov (taxmin emas):** `PYTHONPATH=/app:/app/tests:/app/services/core-api python -c "import app.worker"` →
  `app.worker resolves to: /app/services/core-api/app/worker.py`, `contains init_sentry( : True`.
  Ya'ni darvoza `cv-service` uchun **core-api ning worker'ini** tekshirib, YASHIL bo'lardi — 04-12 nosozligining boshqa yo'ldan takrori.
- **Tuzatish:** har servisning kod ildizi `build.dockerfile` dan chiqariladi; `services/core-api` bo'lsa — eski import+introspeksiya yo'li (o'zgarmagan), boshqa bo'lsa — manba darajasidagi to'rt shart (fayl bor, atribut bor, ishga tushish ilmog'i bor, `init_sentry(` bor). **«O'tkazib yuborish» shoxi yo'q.** Parser uchun ikki yangi quyi chegara qo'shildi.
- **Ruxsat asosi:** `05-PATTERNS.md` §1.6 bu faylni allaqachon **(MOD)** deb belgilagan; rejaning `files_modified` i uni tushirib qoldirgan.
- **Qamrov chegarasi yashirilmadi:** manba qatlami importdan kuchsizroq, shuning uchun **obyekt darajasidagi** darvoza `services/cv-service/tests/unit/test_sentry_entrypoints.py` da, `cv-tests` konteynerida yozildi (u ham servis nomlarini ro'yxat qilmaydi — `build.dockerfile` bo'yicha tanlaydi).

### 3. [Rule 3 - Bloklovchi] Root `mypy .` ikki `app` paketidan yiqildi

- **O'lchov:** `services/cv-service/app/__init__.py: error: Duplicate module named "app" ... errors prevented further checking` — ya'ni `npm run lint` **butunlay** to'xtardi.
- **Tuzatish:** root `pyproject.toml` da `ruff.extend-exclude` va `mypy.exclude` ga `services/cv-service` qo'shildi. Filtr `package.json` da emas, `pyproject.toml` da — o'sha faylning `:27-33` dagi o'z qoidasi («uchta joyda takrorlangan filtr ikkitasida unutilardi»).
- **⚠ Orkestrator uchun:** `05-01/T1` ham root `pyproject.toml` ni o'zgartiradi (`golden` marker, W0-10). Ikki tahrir **turli bloklarda** (`[tool.pytest.ini_options] markers` ↔ `[tool.ruff]`/`[tool.mypy]`), lekin ular fayl bo'ylab yaqin — merge paytida ko'rib chiqilsin.
- **Commit:** `84a2eb4`

### 4. [Rule 3 - Bloklovchi] `test_capture_schedule.py` reyestr nusxasidan yiqildi

- **Muammo:** `assert set(body["never_seen"]) == {"capture_tick", "alert_sweep", "retention", "backup"}` — `EXPECTED_COMPONENTS` ning qo'lda yozilgan IKKINCHI NUSXASI. `cv_detect` qo'shilgach test yiqildi.
- **Tuzatish:** kutilgan to'plam endi reyestrdan olinadi (`set(EXPECTED_COMPONENTS)`), ustiga **alohida quyi chegara** qo'yildi (uchta komponent reyestrda bo'lishi shart), aks holda hosila da'vo bo'sh reyestrda ma'nosiz bo'lardi.
- **Commit:** `ca04d65`

### 5. Rejadan ongli farqlar (mahsulot qarorlari)

| Reja aytgan | Bajarildi | Sabab |
|---|---|---|
| `cv-tests` `working_dir: /app` | `/app/services/cv-service` | `/app` da `pytest`/`ruff`/`mypy` **root** konfiguratsiyani olardi va rejaning O'Z verify buyruqlari (`pytest tests/unit/test_detection_fixtures.py`) ishlamasdi |
| `cv-service` healthcheck `nc -z` | healthcheck **yo'q** | 05-08: «`cv-service` — sof worker». `nc -z` uchun port ochish o'z portiga o'zi javob beradigan yuza — `scheduler` blokidagi «HEALTHCHECK SOXTALASHTIRILMAYDI» qarori |
| `REDIS_URL` | `VALKEY_URL` | Repo bo'ylab yagona nom (`compose.yaml`, `core-api/settings.py`) |
| navbat nomi «sozlamadan» | kodda `Final` konstanta | `core-api::JOBS_QUEUE` ning aynan qarori: nom muhitga chiqsa ikki jarayon jimgina boshqa navbatlarga qarab qolardi |
| `tests/__init__.py` yaratilsin | yaratilmadi | Root `tests/` ham paket emas; paket qilinsa `fixtures.*` va `tests.fixtures.*` bitta faylning ikki nomi bo'lib `mypy` ni yiqitardi |
| — | `app/observability.py` **qo'shildi** | `init_sentry()` ni `worker.py` va `main.py` ikkalasi ham chaqiradi; `core-api` ning 270 qatorli moduli NUSXA OLINMADI — uning qoidalari RTSP ga sozlangan, bu servis esa RTSP ga tegmaydi |
| — | `detections_at(..., frame_size=)` | 0..1 ↔ piksel konversiyasi YAGONA joyda qolishi uchun; standart `FRAME_SIZE` modulda |

### 6. `app/main.py` bugun konteynerga chiqarilmagan — ochiq yozilgan

D-23 minimal FastAPI ni talab qiladi, 05-08 esa `cv-service` ni **sof worker** deb belgilaydi. Ikkalasi bir konteynerda uchrashmaydi, ikkinchi konteyner esa faqat o'z healthcheck'iga javob beradigan yuza bo'lardi. Shuning uchun `app/main.py` bor, lekin uni birorta compose servisi yuritmaydi — bu holat **fayl docstringida va `README.md` §4 da ochiq yozilgan**, va u **sinalmagan kod emas**: `test_sentry_entrypoints.py::test_health_surface_also_installs_sentry` uning `lifespan` zanjirini obyekt darajasida o'lchaydi.

## Known Stubs

Yo'q. Bu rejada UI ham, ma'lumot oqimi ham yo'q; `app/main.py` ning holati yuqorida (§6) ochiq yozilgan va u stub emas — u ishlaydigan, o'lchanadigan, lekin hozircha konteynerga chiqarilmagan kirish nuqtasi.

## Observations for later plans (fixed emas — scope tashqarisi)

1. **`cv-service` runtime venv — 819 MB (image 2.35 GB).** Eng kattalari: `scipy` 108 M, `opencv_python_headless.libs` 84 M, `cv2` 78 M, `av.libs` 72 M, `onnxruntime` 58 M, `phonenumbers` 46 M, `numpy` 42 M, `matplotlib` 35 M.
   `scipy`/`matplotlib`/`av` — `supervision` orqali; `phonenumbers` — `sbozor-core` orqali (bu servisga kerak emas). `torch`siz bu ~800 MB kam, lekin **W0-13 ning `gate` byudjeti** va Contabo diski uchun bu son hisobga olinsin (05-15).
2. **`tests/integration/test_alerting.py` — YARIM TUNGA bog'liq flake (mavjud, meniki emas).** To'liq to'plamning birinchi yugurishida ikki test yiqildi (`23:54` Asia/Tashkent): ular `datetime.now(tz=MARKET_TZ) + 30 daqiqa` ishlatadi va u yarim tundan o'tib **biznes kunini almashtiradi** — alert `resolved` bo'lib ikkinchi xabar ketadi. Ayni fayl `00:15` da qayta yuritilganda **15/15 yashil**. Tuzatilmadi (bu reja tegmagan kod), lekin qayd etilishi kerak.
3. **Worktree/CI muhitining sharti:** yangi checkout'da `ops/seaweedfs/s3.json` va `sbozor-snapshots` bucket'i bo'lmasa 32 ta ombor/saqlash testi yiqiladi (`NoSuchBucket`, `AccessDenied`). Bucket `ops/seaweedfs/README.md` §3 dagi buyruq bilan yaratilgach hammasi yashil.

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-SC | mitigate | Uchala paket CLAUDE.md pinlariga mos; noma'lum paket 3-qatlam predikati bilan ushlanadi (identifikator/matn farqi bilan tuzatilgan) |
| T-05-05 | mitigate | `FORBIDDEN_PACKAGES` + lockfile skani; `rfdetr` ning O'ZI ham taqiqlangan. Ikkala yo'l ham sabotaj bilan o'lchandi |
| T-05-06 | mitigate | `S3_ACCESS_KEY`/`S3_SECRET_KEY` da `:-` standart YO'Q; `Settings` bo'sh qiymatni ISHGA TUSHISHDA rad etadi |
| T-05-07 | mitigate | `cv-service` da `ports:` bloki yo'q (`grep` sanog'i o'zgarmadi: 1) |
| T-05-08 | accept | Artefakt repoda emas; manba va retsept `ops/models/README.md` da nomma-nom |

Yangi tahdid yuzasi topilmadi: `cv-service` ning DB va S3 rekvizitlari rejaning chegara jadvalida allaqachon nomlangan.

## Frontend

Bu reja birorta frontend faylga tegmadi, shuning uchun `vitest`/`node --test`/`i18n:check` **yuritilmadi** — ular ayni paytda 05-03 va 05-04 tomonidan o'zgartirilmoqda va bu yerdagi yugurish chalg'ituvchi bo'lardi.

## Self-Check: PASSED

Barcha e'lon qilingan fayllar diskda va barcha commit'lar tarixda mavjud (quyida tekshirildi).
