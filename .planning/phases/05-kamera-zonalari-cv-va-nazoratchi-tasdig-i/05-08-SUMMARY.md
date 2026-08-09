---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 08
subsystem: detect-quvuri
tags: [cv-service, detect-job, occupancy-events, cross-service-queue, taskiq, s3, rls, heartbeat, ai-02]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 07
    provides: "`DetectorSession`, `raw_to_detections()`, `zone_verdict()`, `polygon_to_pixels()`, `annotate_zone()` + `EVIDENCE_PREFIX`; `DEFAULT_REQUIRE_ALL_ANCHORS = False` (o'lchangan chekinish)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 05
    provides: "`occupancy_events` sxemasi — D-21 billing langari, `UNIQUE(market_id, snapshot_id, camera_zone_id, model_version)`, shartsiz o'zgarmaslik triggeri; `camera_zones` va uning `ix_camera_zones_active` qisman indeksi; `market_delete_draft()` kaskadi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 02
    provides: "`cv-service` toolchain (`cv-tests`), `CV_QUEUE = 'sbozor:cv'`, `self_check.EXPECTED_COMPONENTS` dagi `cv_detect`, `tests/fixtures/detections.py`"
  - phase: 04-snapshot-pipeline
    plan: 07
    provides: "`_system_transaction()` naqshi, `asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS)` bilan enqueue va uning TRANZAKSIYADAN KEYIN turishi"
  - phase: 04-snapshot-pipeline
    plan: 06
    provides: "`SnapshotStorage` — sirsiz `_failure()`, `_ABSENT_ERROR_CODES`, klient egaligi; UCHTA o'lchangan `botocore` fakti"
provides:
  - "`services/cv-service/app/db.py` — `system_transaction()` (`Principal` YO'Q, `actor_id` PARAMETRI ham yo'q) va `open_sessionmaker()`"
  - "`services/cv-service/app/services/storage.py` — `CvStorageClient`: AYNAN `get` + `put_evidence`; `head`/`list_prefix`/`delete_many` UMUMAN yozilmagan"
  - "`services/cv-service/app/repositories/occupancy_writer.py` — `ON CONFLICT DO NOTHING ... RETURNING`; `business_date`/`slot_time` qatordan NUSXALANADI"
  - "`services/cv-service/app/jobs/detect.py` — bir kadr -> barcha zona hodisasi; `DetectFrame` (D-02 choki), `MODEL_VERSION`, `THRESHOLDS_VERSION`, `UNCERTAIN_THRESHOLDS`, `evidence_key()`"
  - "`services/cv-service/app/worker.py` — `WORKER_STARTUP` da `AsyncExitStack` (engine + ombor + ONNX sessiya); `cv.detect` vazifasi"
  - "`services/core-api/app/services/cv_queue.py` — `sbozor:cv` ga NASHR; `cv.detect` tanasi `RuntimeError` tashlaydi"
  - "`system_heartbeats['cv_detect']` — 05-02 dan beri `never_seen` bo'lgan komponent endi YOZILADI"
  - "`services/cv-service/tests/conftest.py` — migratsiya qilingan bazaga boradigan DB fixture'i (05-06…05-12 shundan foydalanadi)"
affects: [05-10-noaniq-navbat, 05-11-kor-audit, 05-12-agregatsiya, 05-13, 05-15-faza-darvozasi, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sirsizlik testi ISTISNO SINFINI to'g'ri tanlashi shart: `ClientError` sir tashimaydi, ya'ni faqat u bilan yozilgan test kod sizayotganda ham YASHIL bo'ladi"
    - "`raise … from None` `__context__` ni TOZALAMAYDI — uni faqat `except` blokidan TASHQARIDA `raise` qilish tozalaydi"
    - "Idempotentlik testi `ON CONFLICT DO NOTHING` ni QO'RIQLAMAYDI, agar «job yiqilmaydi» qoidasi DB rad etishini yutib yuborsa: yurak urishining `detail` i yagona ichki signal"
    - "`business_date` ning «qatordan nusxalanishi» BUGUNGI kadrda sinalmaydi — seed kadrni ORQAGA surishi shart"
    - "Navbat nomi VA vazifa nomi — ikki kod bazasidagi kontrakt: import mumkin emas, shuning uchun MANBA MATNI `Final[str]` shakli bilan birga solishtiriladi"
    - "Fon-vazifada `market_id` xabardan OYNANI ochadi, yozuvga ketadigan qiymatlar esa QATORDAN o'qiladi (RLS ostida «faqat qatordan» mumkin emas)"

key-files:
  created:
    - services/cv-service/app/db.py
    - services/cv-service/app/services/__init__.py
    - services/cv-service/app/services/storage.py
    - services/cv-service/app/repositories/__init__.py
    - services/cv-service/app/repositories/occupancy_writer.py
    - services/cv-service/app/jobs/__init__.py
    - services/cv-service/app/jobs/detect.py
    - services/cv-service/tests/unit/test_storage_surface.py
    - services/cv-service/tests/integration/test_detect_job.py
    - services/core-api/app/services/cv_queue.py
    - tests/integration/test_capture_enqueues_detect.py
  modified:
    - services/cv-service/app/worker.py
    - services/cv-service/tests/conftest.py
    - services/core-api/app/jobs/capture.py
    - compose.yaml
  deleted: []

key-decisions:
  - "⚠ O'LCHANGAN: `ClientError` bilan yozilgan sirsizlik testi kod SIZAYOTGANDA ham YASHIL qoladi. `_failure()` ga `{exc}` kiritilganda realistik (kalitsiz) `ClientError` testi o'tdi, `EndpointConnectionError` testi esa qizardi — 04-06 ning ikkinchi fakti aynan shu tuzoqni yasaydi. Test IKKALA sinfni ham o'lchaydi va `ClientError` ning `Message` iga kalit ATAYIN qo'yilgan (kelajakka qarshi darvoza)"
  - "⚠ O'LCHANGAN: `raise … from None` `__context__` ni SAQLAB QOLADI — u faqat `__suppress_context__` ni qo'yadi. `from None` OLIB TASHLANGANDA test YASHIL qoldi; `raise` `except` ICHIGA ko'chirilganda QIZARDI. Ya'ni test `from None` ni emas, `raise` NING JOYINI qulflaydi"
  - "⚠ O'LCHANGAN: `ON CONFLICT DO NOTHING` -> `DO UPDATE` sabotaji `test_rerun_creates_no_duplicate` ni QIZARTIRMADI. Sabab zanjiri: `DO UPDATE` -> o'zgarmaslik triggeri `RAISE` -> `detect()` istisnoni yutadi -> qatorlar o'zgarmagan. Test yurak urishining `detail.written == 0` bandi bilan KUCHAYTIRILDI va shundan keyin sabotaj qizardi"
  - "⚠ O'LCHANGAN: `snapshot.business_date` -> `date.today()` sabotaji 17 testning HAMMASINI yashil qoldirdi. Seed kadri BUGUNGI edi, `business_date` esa `scheduled_at` dan hosila. `past_frame_seed` (3 kun oldingi kadr) qo'shildi va shundan keyin sabotaj qizardi — Pitfall 3 ning butun mazmuni shu farqda"
  - "Navbat nomi va vazifa nomi `Settings` GA CHIQARILMADI (reja shuni so'ragan edi). Sabab: qiymat IKKI BOSHQA konteynerga beriladi va bitta `.env` satrini unutish ularni jimgina ajratardi — 05-02 (`CV_QUEUE`) va 04-07 (`JOBS_QUEUE`) aynan shu sababdan kodda qoldirgan. Ikki nusxa `Final[str]` shakli bilan birga MANBADAN solishtiriladi"
  - "`market_id` navbat xabarida QOLDI: RLS ostida `snapshots` ni kontekstsiz o'qib bo'lmaydi, ya'ni «faqat qatordan olish» IMKONSIZ. Xabardagi qiymat FAQAT oynani ochadi; `_SnapshotContext` ga hamma narsa — `market_id` ning O'ZI ham — qatordan o'qiladi"
  - "`put()` emas, `put_evidence()`: prefiks tekshiruvi NOMDA ham, TANADA ham turadi. `put` umumiy yozish yuzasi bo'lib ko'rinardi va tekshiruv «keraksiz to'siq» deb olib tashlanishi mumkin edi (T-05-32)"
  - "`assert_model_version_matches()` — `CV_MODEL_PATH` fayl nomi `MODEL_VERSION` ning boshi ekanini ISHGA TUSHISHDA tekshiradi. Usiz `rfdetr-medium.onnx` ga o'tish jimgina eski nom bilan yozilardi va «qaysi model yaxshiroq?» savolining o'lchovi buzilardi"
  - "`cv-service` integratsiya testlari `testcontainers` GA TAYANMAYDI: bo'sh konteynerga sxema kerak, sxema esa `alembic` + `alembic-utils` ni ikkinchi image'ga olib kirardi (`create_all()` RLS ni ham, triggerni ham yaratmaydi). To'plam MAVJUD, migratsiya qilingan bazaga boradi va tayyorgarliksiz QATTIQ yiqiladi (`skip` shoxi yo'q)"
  - "Seed EGA roli ostida, `detect` esa `sbozor_app` ostida: `sbozor_app` da `markets` uchun FAQAT `SELECT` bor (o'lchandi). Ajratish testni KUCHAYTIRADI — RLS da'vosi haqiqiy qoladi"

requirements-completed: []
requirements-advanced: [AI-02]

metrics:
  duration_minutes: 175
  completed: 2026-08-09
  tasks_completed: 3
  files_created: 11
  files_modified: 4
  commits: 4
---

# Phase 5 Plan 08: `detect` quvuri — tor ombor, orkestratsiya va cross-servis enqueue — Summary

Kadr endi saqlangandan keyin `sbozor:cv` navbatiga tushadi, `cv-service` uni **kaliti bo'yicha** S3 dan oladi va har faol zona uchun `occupancy_events` ga yozadi; **to'rtta sabotajdan ikkitasi hech nimani qizartirmadi** va ikkala test ham shu sababdan kuchaytirildi.

## Bajarilgan ishlar

### Task 1 — Tor ombor klienti va fon-vazifaning tenant konteksti (`443af83`)

`app/services/storage.py` — `core-api` nikining **shakli**, lekin yuzasi ikki amal:

| Metod | Holat |
|---|---|
| `get(key)` | ✅ kadr S3 **kaliti** bo'yicha (RESEARCH §E.13) |
| `put_evidence(key, data)` | ✅ **faqat** `EVIDENCE_PREFIX` ostiga — prefiks tanada tekshiriladi |
| `head` / `list_prefix` / `delete_many` / `create_bucket` / `delete_bucket` | ⛔ **umuman yozilmadi** |

`app/db.py::system_transaction()` — `discovery.py:170-205` ning jufti, lekin `actor_id` **parametri ham yo'q**: aniqlashni hech kim so'ramaydi, ya'ni D-12 ning «AI qarori — MASHINANING qarori» ajratmasi audit jurnalida strukturaviy bo'lib qoladi.

19 test: yuza `hasattr` bilan **va sanoq** bilan, xato ikkala istisno sinfida, zanjirning ikkala tomoni, `EVIDENCE_PREFIX` ning ikkala yo'nalishi.

### Task 2 — `detect` orkestratsiyasi, idempotentlik va yurak urishi (`5223a89`)

`jobs/detect.py` (≈620 q.) — yetti qadam, uchta tranzaksiya chegarasi:

```
1. kadr qatori + faol zonalar        (1-tranzaksiya, O'QISH)
2. quality_verdict <> 'ok' -> CHIQISH (hodisa yozilmaydi)
3. S3 dan baytlar                    (tranzaksiyadan TASHQARIDA)
4. detektsiyalar + zona verdikti      (sof hisob)
5. bitta ommaviy INSERT               (2-tranzaksiya, YOZISH)
6. dalil rasmi                        (tranzaksiyadan TASHQARIDA)
7. yurak urishi                       (3-tranzaksiya, ALOHIDA, xatosi YUTILADI)
```

**D-02 choki nomlangan tip:** `DetectFrame = Callable[[bytes, tuple[int, int]], Detections]`. Mahsulot yo'lida u `session_detector(DetectorSession(...))`, testda esa sintetik `sv.Detections`.

`repositories/occupancy_writer.py` — `ON CONFLICT DO NOTHING` **indeksni nomma-nom** ko'rsatadi va `RETURNING` bilan **haqiqatan yozilgan** qatorlarni sanaydi (`rowcount` emas).

`worker.py` — `AsyncExitStack` bilan uchala og'ir resurs; `cv.detect` ro'yxatdan o'tdi.

18 integratsiya testi haqiqiy Postgres ustida.

### Task 3 — Cross-servis enqueue va sifat filtri (`2323c55`, `c002323`)

`core-api/app/services/cv_queue.py` — **ikkinchi** broker (`sbozor:cv`), chunki `worker.py` ning brokeri `sbozor:jobs` dan **o'qiydi**: `cv.detect` ni unga ro'yxatdan o'tkazish xabarni `core-api` ning o'z worker'iga yuborardi.

`cv.detect` tanasi `core-api` da **`RuntimeError` tashlaydi**. Bo'sh tana (`pass`) o'sha holatni jimgina yutardi — vazifa «muvaffaqiyatli» bo'lib navbatdan yo'qolardi va kadr hech qachon aniqlanmasdi.

`capture.py` — enqueue **tranzaksiyadan keyin** va **faqat `VERDICT_OK`**.

12 test: kontrakt (manbadan hosila), haqiqiy Valkey, AST bilan quvurdagi o'rin.

## Verification Performed

| O'lchov | Buyruq | Natija |
|---|---|---|
| `cv-service` to'liq to'plami | `cv-tests pytest -q` | **130** (bazaviy 93 + 19 + 18) |
| `cv-service` lint/tiplar | `cv-tests: ruff check + format --check + mypy` | toza (32 fayl) |
| `core-api` to'liq to'plami | `tests pytest -q` | **exit 0**, 2043 yig'ildi (bazaviy 2032 + 11) |
| `core-api` tenancy | `tests pytest tests/tenancy -q` | **506** — o'zgarmadi |
| `core-api` lint/tiplar | `tests: ruff check + format --check + mypy .` | toza (264 fayl) |
| Yangi enqueue to'plami | `tests pytest tests/integration/test_capture_enqueues_detect.py -q` | **12** |
| `cv.detect` ro'yxatdan o'tgani | `cv-tests python -c "…broker.get_all_tasks()"` | `['cv.detect']`, navbat `sbozor:cv`, 2 ilmoq |
| `cv.detect` `core-api` brokerida YO'Q | `test_cv_queue_name_differs_from_core_queue` | ✅ (`cv_broker` da BOR, `broker` da YO'Q) |
| D-06: `capture.py` da `taskiq` | `test_the_capture_job_never_imports_the_queue_library` | `0` import |

**Frontend to'plamlari (`vitest`/`node --test`/`i18n:check`) YURITILMADI:** bu reja birorta frontend faylga tegmadi va ular ayni paytda `05-09` tomonidan o'zgartirilmoqda — bu yerdagi yugurish chalg'ituvchi bo'lardi (05-02 ning aynan o'sha qarori).

### Sabotajlar — nima QIZARDI va **nima YASHIL QOLDI**

Har biri `cp` bilan snapshotdan tiklandi (`git checkout --` **ishlatilmadi**).

| # | Sabotaj | NATIJA |
|---|---|---|
| A | `_failure()` ga `{exc}` interpolyatsiyasi | ✅ `..._network_failure_...`, `..._a_leak_from_the_response_body...`, `..._failure_body_never_interpolates...` qizardi<br>⚠⚠ **REALISTIK `ClientError` BILAN YOZILGAN TEST YASHIL QOLARDI** — alohida o'lchandi (pastga qarang) |
| B | `head()` metodi qo'shildi | ✅ `..._forbidden_method_is_absent[head]` **va** `..._surface_is_exactly_two_public_methods` |
| C | `from None` olib tashlandi (`raise` blokdan tashqarida qoldi) | ⚠ **YASHIL QOLDI** |
| C′ | `raise` `except` bloki **ICHIGA** ko'chirildi (`from None` bilan) | ✅ `..._exception_chain_is_broken...` qizardi va xabarda to'liq endpoint URL ko'rindi |
| D | `system_transaction()` da `market_id=None` | ✅ **9 test** qizardi, jurnalda `detect_snapshot_not_visible`<br>⚠ `..._dark_snapshot_...` va `..._zoneless_camera_...` **YASHIL QOLDI** — «hodisa yo'q» va «kontekst yo'q» ajratilmaydi (Pitfall 13 ning aynan o'zi) |
| E | `ON CONFLICT DO NOTHING` -> `DO UPDATE SET verdict='empty'` | ⚠⚠ **YASHIL QOLDI** (pastga qarang) |
| E′ | O'sha sabotaj, **kuchaytirilgan** testdan keyin | ✅ `test_rerun_creates_no_duplicate` qizardi: `occupancy_events is append-only (attempted UPDATE)` |
| F | `snapshot.business_date` -> `date.today()` | ⚠⚠ **17 TESTNING HAMMASI YASHIL QOLDI** (pastga qarang) |
| F′ | O'sha sabotaj, `past_frame_seed` qo'shilgandan keyin | ✅ `test_business_date_comes_from_the_row_and_not_from_today` qizardi |
| G | `quality_verdict != "ok"` filtri olib tashlandi | ✅ `test_dark_snapshot_produces_no_events` qizardi (`storage.read_keys == []` bandi); jurnalda ikkinchi qatlam ham ko'rindi — `fk_occupancy_events_snapshot_billable` |
| H | `enqueue_detect` shartsiz qilindi | ✅ `test_dark_frame_is_not_enqueued` (AST) qizardi |

## Deviations from Plan

### 1. `[Rule 1 - Bug]` Rejaning sirsizlik testi TUZOQ USTIGA yozilgan edi — o'lchov bilan topildi

- **Qachon:** Task 1, reja aytgan shaklni (`sun'iy ClientError bilan`) yozgandan keyin.
- **Muammo:** `04-06` ning **ikkinchi** o'lchangan fakti: `ClientError` ning matni manzilni ham, rekvizitni ham **tashimaydi**. Ya'ni faqat `ClientError` bilan yozilgan sirsizlik testi tekshirayotgan istisno sinfida sizadigan narsaning **o'zi yo'q**.
- **O'lchov (2026-08-09):** `_failure()` ga `{exc}` kiritildi va `_client_error()` ning `Message` i realistik (kalitsiz) shaklga keltirildi →

  | Test | Natija |
  |---|---|
  | `..._client_error_message_carries_no_bucket_or_key` | **YASHIL** — kod to'liq endpoint URL ni sizayotgan holda |
  | `..._network_failure_message_carries_no_endpoint_bucket_or_key` | **QIZIL** |

- **Tuzatish:** test **ikkala** sinfni ham o'lchaydi; hal qiluvchisi `EndpointConnectionError`. Sun'iy `ClientError` ning `Message` iga kalit **ataylab** qo'yildi — u endi *kelajakka* qarshi darvoza (`botocore` yoki SeaweedFS bir kun kalitni xato tanasiga qo'shsa, da'vo shu yerda qizaradi). Sabab `_client_error()` ning docstringida o'lchov bilan yozilgan.
- **Commit:** `443af83`

### 2. `[Rule 1 - Bug]` `raise … from None` `__context__` ni TOZALAMAYDI

- **O'lchov:** `from None` **olib tashlandi** (`raise` blokdan tashqarida qoldi) → zanjir testi **yashil**. `raise` `except` **ichiga** ko'chirildi (`from None` bilan) → **qizil**, va xabarda `EndpointConnectionError('… http://…/sbozor-snapshots/…jpg')` `__context__` da turibdi.
- **Xulosa:** `from None` faqat `__suppress_context__` ni qo'yadi; kontekstni **faqat `except` blokidan chiqish** tozalaydi. `core-api` ning «`raise` BLOKDAN TASHQARIDA» izohi shu sababdan nozik qaror va u endi test bilan qulflangan.
- **Tuzatish:** test docstringi da'voni aniqlashtirdi — u `from None` ni emas, **`raise` ning joyini** qulflaydi.
- **Commit:** `443af83`

### 3. `[Rule 1 - Bug]` Idempotentlik testi idempotentlikni O'LCHAMAS EDI

- **O'lchov:** `ON CONFLICT DO NOTHING` → `DO UPDATE SET verdict='empty'`. **17 test ham yashil qoldi.**
- **Sabab zanjiri:** `DO UPDATE` → `BEFORE UPDATE` o'zgarmaslik triggeri `RAISE` → `detect()` ning `except Exception` i uni **yutadi** → qatorlar o'zgarmagan → «dublikat yo'q» da'vosi bajarildi. Ya'ni test **sxemaning himoyasini** o'lchayotgan edi va uni idempotentlikdan ajrata olmasdi.
- **Tuzatish:** yurak urishining `detail` i o'qiladi (`written == 0`, `zones == 2`). Yurak urishi jobning **oxirida** yoziladi, ya'ni u «yo'l oxirigacha bosib o'tildi» degan yagona ichki signal. Sabotaj takrorlanganda test qizardi va xabar mexanizmni nomma-nom ko'rsatdi.
- **Fayllar:** `tests/integration/test_detect_job.py` (`_heartbeat_detail`)
- **Commit:** `5223a89`

### 4. `[Rule 1 - Bug]` «`business_date` qatordan nusxalanadi» da'vosi BUGUNGI kadrda sinalmaydi

- **O'lchov:** `snapshot.business_date` → `date.today()`. **17 test ham yashil qoldi**, shu jumladan rejaning «literal solishtiruv» mezoni.
- **Sabab:** `snapshots.business_date` — `GENERATED (scheduled_at AT TIME ZONE 'Asia/Tashkent')`, seed kadri esa **bugungi**. Ikkala kod ham bir xil sanani berardi. Pitfall 3 ning butun mazmuni — yarim tunda bir kun farq — bugungi kadrda **ko'rinmaydi**.
- **Tuzatish:** `past_frame_seed` fixture'i (3 kun oldingi kadr) va `test_business_date_comes_from_the_row_and_not_from_today`. Test avval «seed haqiqatan o'tmishdami?» ni tekshiradi — aks holda u o'z farqini jimgina yo'qotardi.
- **Commit:** `5223a89`

### 5. `[Rule 2 - Kritik funksionallik]` Navbat va vazifa nomlari `Settings` GA CHIQARILMADI

Reja `Settings.CV_QUEUE_NAME` va `CV_ENQUEUE_TIMEOUT_SECONDS` ni so'raydi va mezon sifatida `settings.CV_QUEUE_NAME != settings.JOB_QUEUE_NAME` ni beradi. **Bajarilmadi**, sabab bu repoda ikki marta yozilgan:

- `core-api/app/worker.py::JOBS_QUEUE` — «nomni muhit o'zgaruvchisiga chiqarish ikki jarayonning jimgina boshqa navbatlarga qarab qolish yo'lini ochardi»;
- `cv-service/app/worker.py::CV_QUEUE` (05-02) — aynan o'sha qaror.

Bu yerda xavf **kuchliroq**: qiymat **ikki boshqa konteynerga** beriladi, ya'ni ajralish uchun bitta `.env` satrini unutish yetardi va nosozlik mutlaqo jim bo'lardi (`LPUSH` muvaffaqiyatli, `BRPOP` abadiy kutadi).

Mezonning **niyati** esa saqlandi va kuchaytirildi:

| Da'vo | Mexanizm |
|---|---|
| Ikki navbat ajratilgan | `CV_QUEUE_NAME != JOBS_QUEUE` — **runtime** assert |
| `cv.detect` faqat CV brokerida | `cv_broker.get_all_tasks()` da **bor**, `broker.get_all_tasks()` da **yo'q** |
| Ikki nusxa ajralib ketmaydi | `cv-service/app/worker.py` **manbasi** o'qiladi va `Final[str]` shakli bilan birga solishtiriladi (§S-10) |

### 6. `[Rule 3 - Bloklovchi]` `cv-service` integratsiya testlari uchun DB fixture'i — `testcontainers`siz

Reja «haqiqiy Postgres (`testcontainers`)» deydi, lekin `cv-service` ning `pyproject.toml` ida `testcontainers` ham, `psycopg` ham, `alembic` ham **yo'q** va ular rejaning `files_modified` ida sanalmagan. Uch narx birga keladi: ikkita yangi paket + 2.35 GB image'ning qayta qurilishi; **sxema** (bo'sh konteynerga `alembic upgrade head` kerak, ya'ni `alembic-utils` ham — RLS siyosatlari va triggerlar `entities/` da yashaydi); `docker.sock` + `TESTCONTAINERS_*`.

`Base.metadata.create_all()` bilan qisqartirish **rad etildi**: u RLS ni ham, o'zgarmaslik triggerini ham yaratmaydi — ya'ni aynan o'lchanishi kerak bo'lgan kafolatlar sinalmasdi.

**Yechim:** to'plam **mavjud, migratsiya qilingan** bazaga boradi (`DATABASE_URL`) — repo ildizidagi conftest'ning O'Z qochish yo'li (`TEST_DATABASE_URL`) bilan bir xil mexanizm va `04-06` ning ombor testlari bilan bir xil maqom: tashqi tayyorgarlik talab qilinadi, u yetishmasa test **qattiq yiqiladi** va xabar `npm run up` / `npm run migrate` ni nomma-nom ko'rsatadi. **`skip` shoxi ataylab yo'q** (05-07 ning `model` markeri bilan bir xil qaror).

**Reja ro'yxatidan tashqaridagi fayllar:** `services/cv-service/tests/conftest.py` (05-02 ning conftest'i uni **ochiq va'da qilgan**: «fixture 05-08 da tug'iladi») va `compose.yaml` (`cv-tests` ga `DATABASE_URL`, seed URL va `depends_on: db`).

### 7. `[Rule 2 - Kritik funksionallik]` Seed EGA roli ostida — o'lchangan zaruriyat

- **O'lchov (`information_schema.role_table_grants`):** `sbozor_app` da `markets` uchun **faqat `SELECT`** bor. Bozor yaratish — eganing ishi (mahsulot qarori, test cheklovi emas).
- **Tuzatish:** `CV_TEST_SEED_DATABASE_URL` (= `MIGRATION_DATABASE_URL`) va alohida `seed_sessionmaker`. `detect` **va** natijani o'qish hamon `sbozor_app` (NOSUPERUSER, NOBYPASSRLS) ostida — ya'ni ajratish testni **kuchaytiradi**. Muqobil («`markets` INSERT grantini ilova roliga berish») rad etildi: testni qulaylashtirish uchun mahsulot huquqini kengaytirish bo'lardi.
- **Tozalash** mahsulotning **o'z** kaskadi bilan (`market_delete_draft()`), qo'lda yozilgan `DELETE` ro'yxati bilan emas — u jimgina eskirardi.

### 8. `[Rule 2 - Kritik funksionallik]` Rejadan tashqaridagi qo'shimchalar

| Nima | Nega |
|---|---|
| `assert_model_version_matches()` | `model_version` — `occupancy_events` **kalitining** bir qismi. Usiz `rfdetr-medium.onnx` ga o'tish jimgina eski nom bilan yozilardi va «qaysi model yaxshiroq?» savolining o'lchovi buzilardi |
| `_assert_threshold_order()` (import paytida) | `CONFIDENCE_THRESHOLD >= uncertain_low` bo'lsa `uncertain` oynasining pastki qismi **butunlay** kesilardi — nazoratchi navbati jimgina kambag'allashardi va nosozlik «rastalar haqiqatan aniq ekan» degan STATISTIK xulosaga yozilardi |
| `FrameAbsent` (`StorageError` vorisi) | «Kadr o'chirilgan» va «ombor javob bermadi» ikki xil operatsion holat; bittasiga yig'ish ombor uzilishini kunlik shovqin ichida ko'rinmas qilardi |
| `put_evidence()` (`put()` emas) + prefiks tekshiruvi | T-05-32 ning **kod tomondagi** yarmi: asl kadr yo'liga yozish imkonsiz |
| Zona bo'yicha `try` (`_zone_events`) | Bitta buzuq poligon o'sha kameraning **barcha** rastalarini hisobdan chiqarardi va hisobot ularni «bo'sh» emas, **umuman yo'q** qilib ko'rsatardi |
| Yurak urishi `detail` iga faqat SANOQLAR | `system_heartbeats` — **global** jadval (RLS yo'q); unga yozilgan `market_id`/`snapshot_id` hamma uchun ko'rinadigan joyda qolardi |
| `test_the_message_carries_no_frame_bytes` | RESEARCH §E.13 ning «baytlar emas, kalit» qarorining o'lchovi (xabar < 1 KB) |
| `test_the_capture_job_never_imports_the_queue_library` | D-06 ning izohda va'da qilingan mexanik tekshiruvi — `capture.py` uchun endi HAQIQATAN mavjud |

### 9. Rejadan ongli farqlar (mahsulot qarorlari)

| Reja aytgan | Bajarildi | Sabab |
|---|---|---|
| `_system_transaction()` (`cv-service` da) | `system_transaction()` — **ostki chiziqsiz** | U `db.py` ning ommaviy yuzasi va `detect.py` hamda conftest undan import qiladi; ostki chiziqli nom «modul ichida» degan yolg'on va'da berardi |
| Xabar «faqat identifikator», `market_id` **qatordan** | `market_id` xabarda **ham** bor | RLS ostida kontekstsiz o'qish 0 qator beradi, ya'ni «faqat qatordan» **imkonsiz** — kontekstni ochish uchun u OLDIN kerak. Xabardagi qiymat faqat **oynani ochadi**; yozuvga ketadigan hamma narsa `_SnapshotContext` ga QATORDAN o'qiladi. Boshqa bozorning kadri 0 qator ko'radi (test bilan o'lchangan) |
| Detektor «chok darajasida in'ektsiya qilinadi» | Chok **nomlangan tip** (`DetectFrame`) va u `__all__` da | Nomsiz `Callable` argument «tasodifiy shakl» bo'lardi; nomlangan tip in'ektsiya nuqtasini kod bo'ylab ko'rinadigan qiladi |
| `test_enqueue_happens_after_commit` — xulqiy | **AST bilan strukturaviy** | Xulqiy o'lchov `capture_batch` ni to'liq yuritishni talab qiladi va u `-m sim` to'plamining ishi (`test_snapshot_quality.py` — haqiqiy NVR simulyatori + SeaweedFS). Qamrov chegarasi test faylida **ochiq** yozilgan: darvoza eng ehtimolli regressiyani (chaqiruvni tranzaksiya ichiga ko'chirish) yopadi, «chaqiruv ishlaydimi?» savoliga esa `enqueue_detect` ning O'Z testlari javob beradi |
| `settings.py` ga ikki maydon | **O'zgartirilmadi** | Deviatsiya #5 |

## ⚠ Isbotlanmagan qoldi — ATAYIN va OCHIQ

`05-VALIDATION.md` ning ikki qatlamli bo'linishi. **Quyidagilarning hech biri bu rejaning yashil to'plami bilan yopilmagan.**

| Nima | Nega bugun isbotlanmaydi | Kim/qachon |
|---|---|---|
| **Modelning aniqligi** — band/bo'sh qarori to'g'rimi | `detect_frame` testda **sintetik** `sv.Detections` qaytaradi. 130 yashil test ORKESTRATSIYANI o'lchaydi, modelni **emas** (D-01/D-02) | Oltin to'plam darvozasi (W0-9) |
| `UNCERTAIN_THRESHOLDS = (0.30, 0.60)` **to'g'ri oynami** | Real Karmana kadrlari yo'q. Qiymatlar 4-fazadagi sifat chegaralari bilan bir maqomda: shakl himoyalangan, raqamlar taqsimotdan chiqariladi | SQL bilan sozlanadi (`percentile_cont`), `THRESHOLDS_VERSION` oshadi |
| `CONFIDENCE_THRESHOLD = 0.20` yetarlicha pastmi | Tartib qulflangan (`_assert_threshold_order`), **qiymat** esa emas | `05-HUMAN-UAT` |
| `MODEL_VERSION` ning kutubxona qismi (`1.9.1`) | Fayl nomi mexanik tekshiriladi, versiya qismi esa eksport RETSEPTIGA tegishli | `ops/models/README.md` |
| **Ikkala JARAYON bir xil navbatga qaradimi** | Manba darvozasi «ikkala faylda bir xil satr» ni tasdiqlaydi, ishlab turgan ikki konteynerni **emas** | `05-15` — to'liq compose yugurishi |
| `docker compose up -d cv-service --wait` | **YURITILMADI** va sabab ikkita: (1) ONNX artefakti repoda yo'q (gitignored, `ops` qo'yadi) — `Settings._validate_model_file` konteynerni **ataylab** to'xtatadi, ya'ni o'lchov kodni emas, artefaktning yo'qligini ko'rsatardi; (2) bu worktree'ning compose loyihasi **umumiy `sbozor`** ga hal bo'ladi va `up` umumiy konteynerni worktree build'idan almashtirardi (05-04 aynan shunda `storage` ni yiqitgan). O'rniga `cv.detect` ning ro'yxatdan o'tgani `cv-tests` da o'lchandi | `05-15` / `05-HUMAN-UAT` |
| Dalil rasmi nazoratchi uchun **tushunarlimi** | Inson o'lchovi | `05-HUMAN-UAT` |

## Known Stubs

**Yo'q.** Soxta ma'lumot manbai ham, joylashtirilmagan komponent ham yaratilmadi:

- `detect`, `OccupancyWriter`, `CvStorageClient` — to'liq amalga oshirilgan va haqiqiy Postgres ustida o'lchangan;
- `cv_detect_task` ning `RuntimeError` tashlaydigan tanasi **stub emas** — u **ataylab** yiqiladigan signal va uning xulqi test bilan qulflangan (deviatsiya §Task 3);
- `cv-service` konteyneri ONNX artefaktisiz ko'tarilmaydi — bu **kutilgan** xulq (05-02/05-07 da o'rnatilgan), yarim tayyor kod emas.

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-33 | mitigate | Xabar **faqat ikki identifikator** (test: < 1 KB, baytlar yo'q). `market_id` oynani ochadi, yozuvga ketadigan hamma narsa **qatordan**; boshqa bozorning `snapshot_id` si bilan yuborilgan xabar 0 qator ko'radi va **omborga ham bormaydi** (`test_a_message_naming_another_market_writes_nothing`) |
| T-05-34 | mitigate | Har chaqiruvda yangi `system_transaction()`; bitta tranzaksiyada bitta bozor. Mexanizm **xulq bilan** o'lchandi (`test_the_job_sets_its_own_tenant_context` — kontekstsiz o'qish 0 qator berishi ALOHIDA tasdiqlanadi) va sabotaj D bilan qizartirildi |
| T-05-35 | mitigate | **Ikki qatlam:** enqueue oldidan `VERDICT_OK` filtri (AST darvozasi) **va** DB kompozit FK. Sabotaj G ikkalasini ham bir yugurishda ko'rsatdi |
| T-05-36 | mitigate | `asyncio.timeout(5 s)`; xatosi yutiladi va `False` qaytadi (`test_enqueue_failure_does_not_raise`) |
| T-05-37 | mitigate | `_failure()` faqat amal + istisno turi + status; `raise` **blokdan tashqarida**. Ikkala istisno sinfi ham o'lchanadi — deviatsiya #1 |
| T-05-38 | mitigate | `cv_detect` yurak urishi endi **yoziladi** (05-02 dan beri `never_seen` edi); alohida qisqa tranzaksiya, xatosi yutiladi (`test_heartbeat_failure_does_not_stop_the_job`) |

**Yangi tahdid yuzasi:** `cv-service` birinchi marta S3 ga **YOZADI** (dalil rasmi). U rejaning chegara jadvalida `cv-service → S3` sifatida bor, lekin **yozish** yo'nalishi u yerda nomlanmagan. Yuza ikki qatlamda toraytirilgan: kod tomondan `put_evidence()` `EVIDENCE_PREFIX` ni talab qiladi (test bilan qulflangan), operatsion tomondan esa `ops/seaweedfs/s3.json` dagi `cv-service` rekviziti o'sha prefiksdan tashqariga yozishga **ruxsat bermasligi kerak**. Ikkinchisi **bu rejada bajarilmadi** — `ops/seaweedfs/s3.json.example` rejaning fayl ro'yxatida yo'q va u `05-15` ning bandi bo'lib qoladi.

## Keyingi rejalar uchun ochiq bandlar

1. **`ops` uchun (`05-15` da tekshirilsin):** `ops/seaweedfs/s3.json.example` da `cv-service` rekvizitiga `evidence/` prefiksidan tashqariga **yozish taqiqlangani** ko'rinishi kerak. Bugun kafolat faqat KODDA (`put_evidence`).
2. **`05-10`/`05-11` uchun:** `detect` yozadigan `uncertain` qatorlar noaniq navbatning kirishi; `OCCUPANCY_UNCERTAIN_INDEX` (`market_id, business_date` bo'yicha qisman) allaqachon tayyor.
3. **`05-12` uchun:** `no_coverage` ning ikki manbai bor va ikkalasi ham `detect` da **xato emas**: (a) kameraning faol zonasi yo'q, (b) kadr `quality_verdict <> 'ok'`. Ikkalasida ham `occupancy_events` ga 0 qator tushadi.
4. **`05-15` uchun:** ikki jarayonning bir navbatga qarashi manba darvozasi bilan emas, **to'liq compose yugurishi** bilan tasdiqlanishi kerak; shu yugurishda `cv_detect` yurak urishi `/internal/self-check` da `never_seen` dan chiqishi ham o'lchansin.
5. **`cv-tests` ning yangi sharti:** integratsiya testlari **migratsiya qilingan** bazani talab qiladi. `npm run cv:test` `depends_on: db` orqali bazani ko'taradi, lekin `npm run migrate` ni **bajarmaydi** — birinchi marta yugurtirayotgan dasturchi xabarni ko'radi va buyruqni bajaradi. `npm run gate` zanjirida bu bosqich hozircha **ochiq band**.
6. **Kuzatuv (meniki emas, tuzatilmadi):** `docker compose` bu worktree'da ham **`sbozor`** loyihasiga hal bo'ladi (konteyner nomlari `sbozor-cv-tests-run-…`). Ya'ni worktree'dan `docker compose up` **umumiy** konteynerlarni almashtiradi. Bu rejada faqat `run --rm --no-deps` ishlatildi va birorta umumiy servis qayta yaratilmadi.

## Self-Check: PASSED

- E'lon qilingan 11 yaratilgan + 4 o'zgartirilgan fayl — **hammasi diskda**;
- `443af83`, `5223a89`, `2323c55`, `c002323` — **to'rtala commit ham git tarixida**;
- Sabotajlardan keyin to'liq to'plamlar qayta yugurtirildi: `cv-tests` **130 yashil**, `tests` **exit 0** (2043 yig'ildi), `tests/tenancy` **506**, lint/mypy ikkala kod bazasida ham toza.
