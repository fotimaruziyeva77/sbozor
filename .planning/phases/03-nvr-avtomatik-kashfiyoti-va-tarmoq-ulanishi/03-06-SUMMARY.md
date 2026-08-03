---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 06
subsystem: api-and-background-jobs
tags: [taskiq, taskiq-redis, valkey, background-job, rls, tenant-context, fastapi, rate-limit, savepoint, wave-5]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 05
    provides: "`run_discovery(...)` (`taskiq` importsiz), `IsapiClient.probe()`, `NVR_ERROR_CODES`, `AUTH_LOCKING_CODES`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 04
    provides: "`NvrRepository`, `encrypt/decrypt_nvr_password`, `assert_private_host`/`split_address`, `Settings.nvr_credential_key`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 03
    provides: "`nvr_discovery_runs` + faol yugurishning qisman UNIQUE indeksi; `tests/fixtures/nvr_domain.py`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    plan: 19
    provides: "marshrut dekoratoridagi huquq naqshi (§S-4) va `audit_read` ning nazorat holati"
provides:
  - "`app/worker.py` — navbat brokeri va yupqa qobiq; `taskiq` FAQAT shu faylda"
  - "`app/jobs/discovery.py` — sof `async def discover_nvr(...)`; tenant kontekstini O'ZI o'rnatadi"
  - "`compose.yaml` da `worker` konteyneri (profilsiz, `target: runtime`)"
  - "NVR ning yettita marshruti: CRUD, `test-connection` (yozuvsiz, rate-limit ostida), `202` + poll"
  - "`NvrRepository.start_run()` / `set_channels_found()` / `devices_with_credentials()`"
  - "`check_nvr_test_rate()` — `rl:nvr_test:<market_id>:<host>` kesimi"
  - "26 yangi test (19 API + 7 job) + cross-tenant matritsasining yettita yangi marshruti"
affects: [03-07-frontend-api, 03-08-frontend-matn, 03-11-yakuniy-darvoza, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Job — SOF `async def`, resurs (sessionmaker) ARGUMENT sifatida: `audit.py::_write_read_audit` naqshining aynan davomi, faqat `set_tenant_context` QO'SHILGAN"
    - "Har TRANZAKSIYA o'z kontekstini o'rnatadi: GUC'lar `SET LOCAL`, ya'ni `COMMIT` da tozalanadi va «bir marta o'rnatib qayta ishlataman» fail-closed holatga tushardi"
    - "Progress yozuvi ALOHIDA, QISQA tranzaksiyada — uzun tranzaksiya ichidagi `UPDATE` `COMMIT` gacha poll qilayotgan mijozga KO'RINMAYDI"
    - "`IntegrityError` dan KEYIN o'qish uchun SAVEPOINT (`begin_nested`) MAJBURIY: abort holatidagi tranzaksiyada har qanday operator `InFailedSQLTransactionError` beradi"
    - "Kompensatsiya emas, ROLLBACK: so'rov ichidagi nosozlikda `finish_run(failed)` o'sha rollback bilan yo'qoladi — yozuvni emas, yo'qlikni ta'minlash to'g'riroq"
    - "Navbat brokeri MODUL darajasida quriladi, lekin `Settings` NI CHAQIRMAYDI — aks holda `app.main` ni import qilishning o'zi to'liq muhitni talab qilardi"
    - "Almashtirish nuqtasi `app.state` (`enqueue_discovery`) — `sessionmaker`/`cache`/`settings` bilan bir xil mexanizm, yangisi kiritilmaydi"

key-files:
  created:
    - services/core-api/app/worker.py
    - services/core-api/app/jobs/__init__.py
    - services/core-api/app/jobs/discovery.py
    - services/core-api/app/api/v1/nvr.py
    - tests/integration/test_nvr_api.py
    - tests/integration/test_nvr_discovery_job.py
  modified:
    - compose.yaml
    - services/core-api/app/main.py
    - services/core-api/app/schemas.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/security/ratelimit.py
    - services/core-api/app/repositories/nvr_repo.py
    - tests/conftest.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
    - tests/unit/test_nvr_secrets.py
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/market-errors.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json

key-decisions:
  - "TOPILMA (ishlab chiqarishni bloklaydigan): `redis-py 8.0.1` `socket_timeout` ni 5 s STANDART qiladi, `ListQueueBroker.listen()` esa `BRPOP` bilan CHEKSIZ bloklanadi va `listen()` faqat `ConnectionError` ni tutadi. Natija — bo'sh navbatda worker HAR 5 SONIYADA yiqilib qayta ishga tushardi, konteyner esa `Up` bo'lib turardi. `socket_timeout=None` + `socket_connect_timeout=5` + `socket_keepalive=True`"
  - "TOPILMA (UI-SPEC §5.6 ni butunlay buzardi): `create_run` ning `IntegrityError` i tranzaksiyani ABORT qiladi, ya'ni undan keyingi `active_run_id()` o'qishi `InFailedSQLTransactionError` beradi va foydalanuvchi `run_id` li 409 o'rniga **500** olardi. Yechim — `session.begin_nested()` (SAVEPOINT)"
  - "TOPILMA: navbat yiqilganda `finish_run(failed)` yozish MA'NOSIZ — istisno `get_tenant_session` ning `session.begin()` blokidan chiqib butun tranzaksiyani rollback qiladi va yozuv ham yo'qoladi. To'g'ri xulq — rollbackning O'ZI: `create_run` INSERT'i bekor bo'ladi, ya'ni bloklaydigan `queued` qator umuman qolmaydi"
  - "`worker` konteyneriga `JWT_SECRET` HAM kerak (o'lchandi: `ValidationError: jwt_secret Field required`). `Settings` — servisga yagona obyekt va uni entrypoint bo'yicha bo'lish ikki modelning jimgina ajralib ketishiga yo'l ochardi"
  - "`ListQueueBroker` tanlandi, `PubSubBroker` va `RedisStreamBroker` RAD ETILDI: birinchisi obunachisiz xabarni YO'QOTADI, ikkinchisining ack/redelivery mexanikasi esa NVR ga IKKINCHI marta borishni tug'dirardi (D-03 ning qulflash arifmetikasi)"
  - "Job ikkita YANGI xato kodi yozadi (`nvr_credential_unreadable`, `discovery_internal_error`) va ular `NVR_ERROR_CODES` GA QO'SHILMADI: o'sha reyestr ISAPI MULOQOTINING taksonomiyasi va uning «aynan o'n ikkita» ekani `03-VALIDATION.md` hamda `test_registry_has_exactly_twelve_unique_codes` bilan qulflangan. Ular `MARKET_ERROR_CODES` ga (domen kodlari reyestri) kirdi"
  - "`nvr_address_invalid` — beshinchi HTTP kodi. 03-04 ochiq talab qilgan: `NvrAddressError` va `NvrHostNotPrivateError` ikki ALOHIDA sinf, chunki «manzilni tuzating» va «tunnel ichidagi manzilni toping» butunlay boshqa maslahatlar"
  - "`start_run()` `status = 'queued'` shartini MAJBURLAYDI — navbatning «kamida bir marta» kafolatiga qarshi darvoza. Sabotaj S3 uni AYNAN bitta test bilan qulflaganini ko'rsatdi"
  - "`NvrDeviceUpdateRequest` da FAQAT `username` qoldi: `address` `UNIQUE` kalitining bir qismi (UI-SPEC §4.6), `tunnel_subnet` esa bozorlar aro noyob va uni tahrirlash rejada sanalmagan YANGI xato kodini talab qilardi"

patterns-established:
  - "Pattern: so'rov-tashqari kod resursni ARGUMENT sifatida oladi va uni O'ZI qurmaydi — worker uni startup ilgagida, test esa fixture'dan beradi"
  - "Pattern: «oldin yozildi» da'vosining yagona dalili — o'sha paytdagi SO'ROVLAR SANOG'I; natijadan o'lchab bo'lmaydi, chunki oxirida yozgan kod ham aynan bir xil qator qoldiradi"
  - "Pattern: kontekstsiz jobning nosozligi FAQAT «hech nima yozilmadi» emas — u `queued` qatorni qoldirib qurilmani BUTUNLAY qulflaydi; ikkinchi oqibat alohida assert bilan qulflanadi"
  - "Pattern: test brokerni/enqueue'ni `app.state` orqali almashtiradi va TIKLAYDI, o'chirmaydi — `del` bilan marshrut modul darajasidagi HAQIQIY brokerga tushardi va yon ta'sir qoldirardi"
  - "Pattern: ambient muhitga (`os.environ`, `.env`) tayanadigan test uni ANIQ yopadi (`monkeypatch.delenv` + `_env_file=None`) — aks holda u to'ldirilgan mashinada jimgina yashil bo'lardi"

requirements-completed: []

# Metrics
duration: 195min
completed: 2026-08-03
---

# Phase 3 Plan 06: Navbat, kashfiyot jobi va NVR API'si Summary

**Loyihaning birinchi fon-vazifasi tug'ildi va u tenant kontekstini o'zi o'rnatadi — sabotaj shuni ko'rsatdiki, kontekstsiz job HTTP qatlamidan BUTUNLAY ko'rinmaydi (19 API testining hammasi yashil qoldi) va ustiga qurilmani `queued` qator bilan mangu qulflab qo'yadi.**

## Performance

- **Duration:** ~195 min (bir marta Windows stream watchdog uzilishi bilan)
- **Tasks:** 3/3
- **Files:** 21 (6 yangi, 15 o'zgargan)

## Accomplishments

- **Pitfall 13 «yodda tutildi» darajasidan chiqdi:** `test_worker_sets_tenant_context` uni IKKI TOMONLAMA o'lchaydi va sabotaj S1 uning haqiqiy narxini ko'rsatdi.
- **Uchta ishlab chiqarishni bloklaydigan xato topildi va tuzatildi** (quyida, Deviations 1–3). Ikkitasi rejada umuman ko'rilmagan, uchinchisi esa rejaning O'Z talabini (UI-SPEC §5.6) bajarilmas holga keltirardi.
- **`worker` konteyneri HAQIQATAN ko'tariladi** — bu qog'ozda emas, `docker compose logs worker` da o'lchandi (56 soniya, istisnosiz).
- **Bazaviy darvoza kengaydi:** 1289 → **1351** backend (+62), 326 → **362** tenancy (+36), 51 → **61** sim (+10), 429 → **444** i18n kaliti; node **60** va vitest **74** o'zgarmadi. `npm run gate` → **exit 0 / 13 m 39 s**.
- **`services/core-api/pyproject.toml` TEGILMADI** (T-03-SC): birorta yangi paket qo'shilmadi — `taskiq` va `taskiq-redis` 03-01 da o'rnatilgan.

## Task Commits

1. **Task 1: taskiq brokeri, kashfiyot jobi va `worker` konteyneri (Pitfall 13)** — `1256a9b` (feat)
2. **Task 2: NVR DTO'lari, xato reyestri va yettita marshrut** — `f17126a` (feat)
3. **Task 3: API va job yo'lining uchidan-uchiga isboti** — `08846e8` (test)
4. **Darvoza tuzatishi: xato kodlarining frontend ko'zgusi va uch tildagi matni** — `83c4604` (fix)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `app/worker.py` | Broker, `discover_nvr_task` (yupqa qobiq), `enqueue_discovery`; `WORKER_STARTUP` da engine/sessionmaker; `taskiq` FAQAT shu faylda |
| `app/jobs/discovery.py` | Sof `async def discover_nvr(sessionmaker, *, market_id, nvr_id, run_id, actor_id)`; `_system_transaction` har tranzaksiyada `ActorKind.SYSTEM` bilan kontekst o'rnatadi |
| `app/api/v1/nvr.py` | Yettita marshrut; huquq HAR dekoratorida; `test-connection` `{nvr_id}` dan OLDIN; 409 tanasida `run_id` |
| `app/schemas.py` | O'nta DTO; `MARKET_ERROR_CODES` ISAPI va job kodlarini IMPORT qiladi |
| `app/security/ratelimit.py` | `check_nvr_test_rate()` + `_bump(..., window)`; modul docstringiga «chegara NVR tomonida» mulohazasi |
| `app/security/audit.py` | `TABLE_NVR_DEVICES`, `TABLE_NVR_DISCOVERY_RUNS`, `TABLE_CAMERAS` |
| `app/repositories/nvr_repo.py` | `start_run()`, `set_channels_found()`, `devices_with_credentials()` |
| `app/main.py` | `nvr_router` + `lifespan` da broker klienti va `state.enqueue_discovery` |
| `compose.yaml` | `worker` xizmati (profilsiz, `target: runtime`, `JWT_SECRET` + `NVR_CREDENTIAL_KEY`) |
| `tests/conftest.py` | `_process_settings_env` — `nvr_cipher()` GLOBAL `get_settings()` dan o'qigani uchun majburiy |
| `tests/tenancy/test_cross_tenant.py` | `nvr_domain` fixture'i, `nvr_id`/`run_id` fillerlari, to'rtta tana, yangi markerlar |
| `tests/integration/test_nvr_api.py` | 19 test (16 hermetik + 3 `sim`) |
| `tests/integration/test_nvr_discovery_job.py` | 7 test (`sim`) — job yo'lining uchidan-uchiga isboti |

## O'lchangan dalillar

### Pitfall 13 — ikki tomonlama (T-03-38)

| Da'vo | O'lchov |
|---|---|
| Kontekstsiz job kamera YARATMAYDI | 3 → **3** (seed'dagi soni o'zgarmadi) |
| Kontekstsiz job yugurish qatoriga YOZMAYDI | `channels_added` = `NULL`, `status` = `queued` |
| Kontekstsiz job XATO ham yozmaydi | `error_code` = `NULL` — nosozlik butunlay JIMGINA |
| **Kontekstsiz job qurilmani QULFLAYDI** | keyingi `create_run` → `IntegrityError` (qisman UNIQUE indeks) |
| Kontekst bilan AYNI job ishlaydi | `succeeded`, `channels_added` = **3**, kameralar 3 → **6** |

⚠ To'rtinchi qator rejada ham, `03-RESEARCH.md` Pitfall 13 da ham YO'Q edi. Ogohlantiruvchi belgi «job `succeeded`, `channels_added = 0`» deb yozilgan, amalda esa job `succeeded` ham bo'lmaydi — qator `queued` bo'lib qoladi va shu NVR uchun boshqa hech qanday kashfiyot boshlab bo'lmaydi. Ya'ni oqibat hujjatlashtirilganidan **og'irroq**.

### UI-SPEC ning uchta [TALAB] bandi

| Talab | O'lchov |
|---|---|
| §5.2 — `channels_found` sub-oqim tekshiruvlaridan OLDIN | callback paytida `Streaming/channels/*` sanog'i = **0**, qiymat = **6** |
| §5.6 — 409 tanasida mavjud `run_id` | `second.json()["detail"]["run_id"] == first.json()["run_id"]` |
| §6.3 — `channels_found` oflayn kanallarni ham sanaydi | 03-05 da o'lchangan; bu rejada `channels_found=6`, `channels_added=3` (farq sinaladi) |

### SC#4 — parol hech qanday javobda yo'q

| Da'vo | O'lchov |
|---|---|
| `NvrDeviceRead` da `password` maydoni YO'Q | `'password' not in NvrDeviceRead.model_fields` |
| So'rov modelida `market_id` YO'Q | `'market_id' not in NvrDeviceCreateRequest.model_fields` |
| Zond paroli HECH BIR javobda uchramaydi | **7/7** marshrut, XOM tana bo'yicha (quyi chegara 6) |
| Parol o'zgarishi auditda QIYMATSIZ | `credentials_updated` bor, parol satri yo'q |

### T-03-37 — «ulanishni tekshirish» chegarasi

| Da'vo | O'lchov |
|---|---|
| Uchta urinish o'tadi | `[200, 200, 200]` |
| To'rtinchisi rad etiladi | **429** `too_many_attempts` |
| **Rad etilgan so'rov NVR ga BORMAYDI** | qurilmadagi urinishlar sanog'i **o'zgarmadi** |
| Tekshiruv yozuv YARATMAYDI | `count(nvr_devices)` chaqiruvdan oldin va keyin BIR XIL |

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `ruff format --check` + `mypy` | ✅ exit 0 (183 fayl / 179 manba) |
| `pytest -q` (butun backend) | ✅ **1351** (1289 → **+62**) |
| `pytest tests/tenancy -q` | ✅ **362** (326 → **+36**) |
| `pytest tests/integration/test_nvr_api.py` | ✅ **19** |
| `pytest tests/integration/test_nvr_discovery_job.py` | ✅ **7** |
| `npm run test:sim` | ✅ **61** (51 → **+10**) |
| `frontend` node / vitest | ✅ **60** / **74** (o'zgarmadi) |
| `npm run i18n:check` | ✅ **444 kalit × 3 til** (429 → +15) |
| `frontend typecheck` / `lint` / `build` | ✅ toza / toza / to'liq prerender |
| **`npm run gate`** | ✅ **exit 0** — **13 m 39 s** (819 s) |
| `docker compose config --services \| grep -c '^worker$'` | ✅ **1** (profilsiz) |
| `docker compose logs worker` | ✅ 56 soniya, istisnosiz |
| `git diff services/core-api/pyproject.toml` | ✅ toza (T-03-SC) |

⚠ **Darvoza vaqti:** 03-05 dagi 742 s → **819 s** (+77 s). O'sish 26 ta yangi testdan emas (~35 s), asosan `worker` konteynerining birinchi `build` idan va sim to'plamining kattalashuvidan. 03-01 ning nomzod chegarasi (618 s) **uchinchi rejada ketma-ket** buzildi — `03-11` uchun ochiq band bo'lib qoladi.

⚠ **BIRINCHI YUGURISH QIZIL EDI** (`exit 1`, 764 s) va uni **frontend** yiqitdi, backend emas — Issue 5 va deviation #8 ga qarang.

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `jobs/discovery.py` dan `set_tenant_context(...)` olib tashlandi | **6 / 7** job testi | **19 / 19** API testi + `test_enqueue_puts_the_four_identifiers_on_the_queue` | **Bu ustun eng qimmatlisi.** HTTP qatlami Pitfall 13 ni MUTLAQO ko'rmaydi: `POST /discover` baribir 202 va `run_id` beradi, 409 poygasi ham to'g'ri ishlaydi, poll ham javob beradi. Ya'ni «API testlari yashil» degan dalil kashfiyotning ishlashi haqida HECH NIMA aytmaydi va job qatlamining o'z testlari ALMASHTIRIB BO'LMAYDI |
| **S2** | 409 javob tanasidan `run_id` olib tashlandi | **AYNAN BITTA**: `test_second_discover_returns_409_with_the_existing_run_id` | **25 tasi**, shu jumladan 202 yo'li, `enqueued` tarkibi va butun job to'plami | UI-SPEC §5.6 [TALAB] BITTA test bilan qulflangan. 409 ning O'ZI to'g'ri qolaveradi — ya'ni «409 keladi» tekshiruvi talabni QAMRAMAYDI |
| **S3** | `start_run()` dan `status = 'queued'` sharti olib tashlandi | **AYNAN BITTA**: `test_a_second_delivery_of_the_same_run_does_nothing` | **25 tasi**, shu jumladan to'liq kashfiyot yo'li va idempotentlik | Navbatning «kamida bir marta» kafolatiga qarshi darvoza MUSTAQIL o'lchanadi. Natija (`succeeded` qator) ikkinchi skandan keyin ham aynan bir xil ko'rinardi — yagona dalil so'rovlar sanog'i |

Hamma sabotajlar commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har birida ish daraxti toza qoldi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Xato] `redis-py 8` ning `socket_timeout` standarti workerni cheksiz qayta ishga tushirardi**

- **Found during:** Task 1, `docker compose up -d worker` dan keyingi jurnal tekshiruvi
- **Issue:** `redis-py 8.0.1` `Connection.socket_timeout` ni **5 soniya** standart qiladi (`None` emas), `taskiq_redis.ListQueueBroker.listen()` esa `BRPOP <queue>` ni CHEKSIZ bloklanadigan holda chaqiradi va faqat `ConnectionError` ni tutadi. O'lchandi:
  ```
  socket_timeout on connection: 5
  EXC after 5.01 TimeoutError Timeout reading from cache:6379
  ...
  [taskiq.process-manager] worker-0 is dead. Scheduling reload.
  ```
  Oqibat: **bo'sh navbatda** worker har 5 soniyada yiqilib qayta ko'tarilardi. `docker compose ps` uni `Up` deb ko'rsatardi, ya'ni nosozlik faqat jurnalda ko'rinardi va birorta vazifa hech qachon bajarilmasdi.
- **Fix:** `ListQueueBroker(..., socket_timeout=None, socket_connect_timeout=5.0, socket_keepalive=True)`. Chegara `socket_timeout` dan `socket_connect_timeout` ga ko'chdi (ulanish osilishi hech qachon normal emas), o'lik peer esa OS darajasida aniqlanadi.
- **Nega bu «shunchaki sozlama» emas:** API tomonida ham shu pul ishlatiladi va `socket_timeout=None` `LPUSH` ni ham cheksiz qilardi — `uvicorn --workers 1` ostida bu butun API'ni bloklardi (T-03-42 ning boshqa yo'ldan takrori). Shuning uchun `enqueue_discovery` ichida `asyncio.timeout(ENQUEUE_TIMEOUT_SECONDS)` qo'yildi: chegara AYNAN so'rov ichidagi yo'lda.
- **Committed in:** `1256a9b`

**2. [Rule 1 — Xato] `IntegrityError` dan keyingi o'qish 409 ni 500 ga aylantirardi**

- **Found during:** Task 3, `test_second_discover_returns_409_with_the_existing_run_id`
- **Issue:** `create_run()` ning `IntegrityError` i PostgreSQL tranzaksiyasini **ABORT** holatiga qo'yadi. `_discovery_conflict()` esa aynan shu sessiyada `active_run_id()` ni o'qiydi:
  ```
  InFailedSQLTransactionError: current transaction is aborted,
  commands ignored until end of transaction block
  -> {"detail":"internal_error"}  (500)
  ```
  Ya'ni UI-SPEC §5.6 [TALAB] — «409 tanasida mavjud `run_id`» — **hech qachon** bajarilmasdi va foydalanuvchi sababsiz 500 olardi. Reja (va 03-04 ning tavsiyasi) 409 ni konstrayt buzilishidan hosil qilishni to'g'ri aytgan, lekin abort holatining oqibatini hisobga olmagan.
- **Fix:** `async with session.begin_nested():` — `create_run` SAVEPOINT ichida bajariladi, konstrayt buzilishi savepoint'ni orqaga qaytaradi va tashqi tranzaksiya TIRIK qoladi.
- **Verification:** `test_second_discover_returns_409_with_the_existing_run_id` (sabotaj S2 bilan qulflangan).
- **Committed in:** `08846e8`

**3. [Rule 1 — Xato] Navbat yiqilganda yozilgan `failed` qatori rollback bilan yo'qolardi**

- **Found during:** Task 3, `test_enqueue_failure_leaves_no_active_run_behind`
- **Issue:** Boshlang'ich implementatsiya navbat xatosida `finish_run(FAILED, ...)` yozib, keyin `HTTPException` ko'tarardi. Ammo `get_tenant_session` sessiyani `async with session.begin():` ichida beradi — endpointdan chiqqan istisno butun tranzaksiyani rollback qiladi va **yozuv ham yo'qoladi**. O'lchandi:
  ```
  assert ('failed', 'discovery_internal_error') in [('succeeded', None)]
  ```
  (ro'yxatda faqat seed'ning eski qatori qolgan). Ya'ni kod «kompensatsiya yozdik» degan YOLG'ON xotirjamlik berardi.
- **Fix:** Kompensatsiya butunlay olib tashlandi. Rollbackning O'ZI to'g'ri xulq: u `create_run` INSERT'ini ham bekor qiladi, ya'ni bloklaydigan `queued` qator UMUMAN qolmaydi. Test endi «faol yugurish soni = 0» ni va **nazorat bandi sifatida** keyingi urinishning 202 olishini o'lchaydi.
- **Committed in:** `08846e8`

**4. [Rule 3 — Bloklovchi] `worker` konteyneriga `JWT_SECRET` qo'shildi**

- **Found during:** Task 1
- **Issue:** Reja `worker` muhitida `DATABASE_URL`, `VALKEY_URL`, `NVR_CREDENTIAL_KEY`, `LOG_LEVEL`, `SENTRY_DSN`, `TZ` ni sanaydi. O'lchandi:
  ```
  pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
  jwt_secret  Field required [type=missing, ...]
  ```
  `Settings` — servisga yagona obyekt va worker uni to'liq quradi.
- **Fix:** `JWT_SECRET: ${JWT_SECRET}` + kodda sabab. Muqobil (`WorkerSettings` bilan bo'lish) ikki modelning jimgina ajralib ketishiga yo'l ochardi.
- **Nega bu xavfsizlik regressiyasi emas:** worker allaqachon `NVR_CREDENTIAL_KEY` ni ushlab turadi va `settings.py` ning O'Z izohi aynan uni «yagona eng qimmat sir» deb belgilaydi.
- **Committed in:** `1256a9b`

**5. [Rule 2 — Yetishmayotgan kritik funksiya] Ikkita job xato kodi va bittasi HTTP kodi**

- **Found during:** Task 1 va Task 2
- **Issue:** 03-04 ning `Next Phase Readiness` bandi ochiq talab qiladi: *«`InvalidToken` yutilmaydi va uni ISAPI ning `401` idan **farqlash SHART**»*. Rejada bunday kod yo'q. Xuddi shunday, `NvrAddressError` va `NvrHostNotPrivateError` uchun ham alohida kodlar talab qilingan, rejada esa faqat `nvr_host_public_blocked` sanalgan.
- **Fix:** `nvr_credential_unreadable`, `discovery_internal_error` (`app/jobs/discovery.py`) va `nvr_address_invalid` (`app/api/v1/nvr.py`) — uchalasi ham `MARKET_ERROR_CODES` ga IMPORT orqali qo'shildi.
- **Nega ular `NVR_ERROR_CODES` ga QO'SHILMADI:** o'sha reyestr ISAPI MULOQOTINING taksonomiyasi. Uning «aynan o'n ikkita» ekani `03-VALIDATION.md` qamrov jadvali va `tests/unit/test_isapi_errors.py::test_registry_has_exactly_twelve_unique_codes` bilan qulflangan; 03-08 ham o'sha sondan chiqadi. Yangi kod qo'shish 03-05 ning ikkita test faylini va VALIDATION jadvalini o'zgartirishni talab qilardi — bularning ikkalasi ham bu rejaning doirasidan tashqarida.
- **Verification:** `test_unreadable_credential_is_not_reported_as_a_bad_password`, `test_unparseable_address_has_its_own_code`.
- **Committed in:** `1256a9b`, `f17126a`

**6. [Rule 3 — Bloklovchi] `tests/conftest.py` ga jarayon muhiti fixture'i**

- **Found during:** Task 2
- **Issue:** `app/security/secrets.py::nvr_cipher()` sozlamani `app.state.settings` DAN EMAS, global `get_settings()` dan o'qiydi (03-04 ning qarori). `POST /nvr-devices` esa `encrypt_nvr_password()` ni chaqiradi, ya'ni `Settings()` quriladi va u to'rtta majburiy maydonni talab qiladi. `tests` konteynerida ular YO'Q (`compose.yaml` ularni faqat `core-api` va `worker` ga beradi).
- **Fix:** `_process_settings_env` (sessiya doirasida, autouse) — to'rtta maydonni o'rnatadi, shifr kalitini HAR SESSIYADA yangi hosil qiladi va ikkala keshni ham tozalaydi.
- **Yon ta'sir va uning tuzatilishi:** bu fixture 03-04 ning `test_missing_key_fails_at_settings_construction` testini yiqitdi — o'sha test «muhitda kalit yo'q» degan AYTILMAGAN taxminga tayanardi. Test tuzatildi va u endi IKKALA ambient manbani ham (`monkeypatch.delenv` + `_env_file=None`) yopadi. Bu **da'voni kuchaytiradi**: `.env` fayli to'ldirilgan mashinada u avval jimgina yashil bo'lardi.
- **Committed in:** `f17126a`

**7. [Rule 3 — Bloklovchi] `ratelimit.py` docstringidan simulyator imzosi olib tashlandi**

- **Found during:** Task 2 verifikatsiyasi (TO'LIQ to'plamda)
- **Issue:** Docstringda sim'ning control-plane yo'li LITERAL yozilgan edi. 03-02 ning `test_no_sim_branching.py` darvozasi `app/` daraxtida o'sha imzolarni qidiradi va **kodni izohdan ajratmaydi**. Bu 03-04 (`nvr_host.py`) va 03-05 (`parser.py`) dan keyin **uchinchi** takror.
  ```
  FAILED test_no_sim_branching.py::test_application_code_has_no_simulator_branching[__sim__]
    services/core-api/app/security/ratelimit.py:45
  ```
- **Fix:** Izoh TUSHUNCHANI saqladi («da'voning yagona dalili — urinishlar sanog'i»), lekin yo'lni yozmaydi; darvozaning O'ZI haqida ogohlantirish qo'shildi.
- **Committed in:** `f17126a`

**8. [Rule 3 — Bloklovchi] Beshta domen kodining frontend ko'zgusi va uch tildagi matni**

- **Found during:** `npm run gate` (backend to'plami TO'LIQ yashil bo'lgandan KEYIN)
- **Issue:** `MARKET_ERROR_CODES` ning UI ko'zgusi (`frontend/src/lib/api-types.ts::ERROR_CODES`) va uning tarjima xaritasi (`market-errors.ts::marketErrorMessageKey`) **til chegarasi tufayli QO'LDA** sinxron saqlanadi; `frontend/scripts/error-codes.test.mjs` esa backend faylini o'qib driftni ushlaydi:
  ```
  AssertionError: api-types.ts::ERROR_CODES da yetishmaydi:
    nvr_host_taken, nvr_host_public_blocked, discovery_already_running,
    nvr_not_found, nvr_address_invalid
  AssertionError: market-errors.ts da `case` yo'q: (o'sha beshtasi)
  ```
  ⚠ Darvoza AYNAN beshtasini ko'rsatdi va ISAPI ning o'n ikki kodini KO'RSATMADI — chunki uning Python parseri faqat LITERAL `"kod",` qatorlarini o'qiydi, `*NVR_ERROR_CODES` splat'ini esa ko'rmaydi. Bu tasodifan to'g'ri chegara: ISAPI kodlari boshqa yuzada (`cameras.errorCause.*`, UI-SPEC §7) yashaydi va ular 03-08 ning ishi.
- **Fix:** Beshta kod ko'zguga va xaritaga qo'shildi; `messages/*.json` ga `cameras` namespace'i (UI-SPEC §1.1 belgilagan nom) beshta kalit bilan kiritildi. `uz-Cyrl` QO'LDA yozilmadi — u `npm run i18n:gen` bilan hosil qilindi va natija tekshirildi: akronim ham, IP manzillar ham toza (M-1/M-2 ning apostrof defekti yuzaga chiqmasligi uchun matnlarda `NVR'ga` shaklidagi qo'shimchalar UMUMAN ishlatilmadi).
- **Verification:** `npm run i18n:check` → `444 kalit × 3 til`, drift yo'q; `npm run test:unit` → 60/60; `typecheck`/`lint` toza.
- **Committed in:** `83c4604`

**9. [Rule 2 — Yetishmayotgan funksiya] `nvr_repo.py` ga uchta metod**

- **Found during:** Task 1 va Task 2
- **Issue:** Reja `nvr_repo.py` ni `files_modified` da sanamaydi, lekin jobda `queued → running` o'tishi, oraliq `channels_found` yozuvi va ro'yxatdagi `has_password` bayrog'i uchun repozitoriyda metod YO'Q edi. Ularni marshrut/job ichida xom SQL bilan yozish tenant predikatini repozitoriydan tashqarida takrorlashni talab qilardi.
- **Fix:** `start_run()`, `set_channels_found()`, `devices_with_credentials()` — uchalasi ham mavjud `finish_run`/`get_run`/`active_run_id` uslubida.
- **Committed in:** `1256a9b`, `f17126a`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. Task 2 ning `pytest tests/tenancy/test_route_coverage.py -q` mezoni Task 3 ning ishiga bog'liq edi.**

Yangi marshrutlar `PARAM_FILLERS` ga `nvr_id`/`run_id` qo'shilmaguncha `test_no_unclassified_routes` va `test_all_path_params_have_fillers` QIZARADI — bu darvozaning to'g'ri ishlashi. Reja esa fillerlarni Task 3 ga, mezonni Task 2 ga qo'ygan.

**Bajarilgani:** cross-tenant fillerlari Task 2 commit'iga kiritildi (ular marshrut qo'shilishining MEXANIK oqibati va `main.py` ning O'Z izohi buni aynan shunday tasvirlaydi), Task 3 esa ikkita YANGI test faylini olib keldi. Natijada **har uchala commit ham yashil**.

**B. `discover_nvr` imzosi rejada sanalgan to'rtta kwarg'dan tashqari `sessionmaker` ni ham oladi.**

Reja imzoni `async def discover_nvr(*, market_id, nvr_id, run_id, actor_id) -> None` deb belgilaydi. Ammo job resursni QAYERDAN olishi kerakligini aytmaydi, modul globali esa `03-PATTERNS.md` §3.8 ning «worker jarayonida `app.state` YO'Q» qarori bilan ziddiyatga tushardi.

**Bajarilgani:** `sessionmaker` — BIRINCHI pozitsion argument, xuddi loyihaning yagona so'rov-tashqari DB yozuvi (`audit.py::_write_read_audit(sessionmaker, ...)`) dagidek. To'rtta kwarg o'zgarmadi va navbat xabari AYNAN ularni olib yuradi.

**C. `test-connection` cross-tenant matritsasidan CHIQARILMADI.**

Reja uni `EXEMPT_ROUTES` ga qo'yishga ruxsat bergan. Ammo istisno marshrutni matritsadan TO'LIQ chiqarardi — tokensiz/buzilgan/muddati o'tgan token da'volari ham yo'qolardi, ular esa parol qabul qiladigan endpoint uchun juda ma'noli. Qo'shimcha to'siq: `EXEMPT_REASON_PREFIXES` uchta toifadan iborat va bu marshrut ularning birortasiga ham tushmaydi.

**Bajarilgani:** `BODY_FILLERS` ga `127.0.0.1:1` manzili berildi — xususiylik darvozasidan o'tadi (loopback global emas) va TCP darajasida DARHOL rad etiladi, ya'ni na tarmoq kutishi, na simulyatorga bog'liqlik bor.

### Rejadan ataylab chetlangan bandlar

**D. TDD RED/GREEN commitlari ajratilmadi.** Uchala task ham `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02, 03-04, 03-05) — har task uchun bitta commit. **RED dalili yo'qolmadi:** uchala sabotaj testlarning kodsiz qizarishini o'lchov bilan ko'rsatadi.

**E. `audit-volume` threat flag QARALDI, lekin bu rejada TUZATILMADI.** 03-04 uni `03-06/03-07 da qaralishi kerak` deb qoldirgan. Qaraldi va o'lchandi: remediatsiya — audit triggerini ustun ro'yxati bilan cheklash (`UPDATE OF name, status, source_ip, ...`), bu esa `migrations/helpers.py::attach_audit_trigger()` ni (BARCHA audit ostidagi jadvallarga ta'sir qiladi) va yangi migratsiyani talab qiladi. Ikkalasi ham bu rejaning `files_modified` idan tashqarida va sxema o'zgarishi Rule 4 ga tushadi. **03-11 uchun aniq band sifatida qoldirildi.** Bu reja audit hajmini OSHIRMADI: job har kashfiyot uchun 2 ta app-qatlam qatori yozadi (boshlandi/tugadi), kamera qatorlari esa 03-04 dan beri o'zgarmagan.

**F. `source_ip` ning `/32` artefakti bu rejada YUZAGA CHIQMAYDI.** 03-04 ning `value-format` flag'i kamera serializatsiyasiga tegishli; bu rejaning yettita marshrutidan birortasi ham `cameras` qatorini JSON'ga bermaydi (`GET /cameras` — 03-07). `NvrDeviceRead` da `source_ip` maydoni yo'q.

---

**Total deviations:** 9 auto-fixed (3 × Rule 1, 2 × Rule 2, 4 × Rule 3) + 3 ta rejadagi ziddiyat + 3 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. Uchala Rule 1 tuzatishi ham **ishlab chiqarishni bloklaydigan** yoki rejaning O'Z talabini bajarilmas holga keltiradigan xatoni yopdi; to'rtala Rule 3 tuzatishi esa rejaning O'Z maqsadini bajarilishi mumkin holga keltirdi (usiz `worker` ko'tarilmasdi, NVR API to'plami qurilmasdi yoki `npm run gate` qizil qolardi).

## Issues Encountered

1. **`docker compose up -d --force-recreate` YETARLI EMAS.** `worker` `target: runtime` ni ishlatadi va u kodni image'ga **COPY** qiladi (`nvr-sim` esa volume mount bilan ishlaydi). Kod o'zgargandan keyin `--build` MAJBURIY — usiz konteyner eski kod bilan qayta ko'tariladi va tuzatilgan xato «tuzalmadi» bo'lib ko'rinadi. Bu 03-05 ning «sim `--reload` bilan ishlamaydi» qaydining **boshqa shakldagi** takrori: birinchisida `restart`, bu yerda `--build` kerak.
2. **`api_app` — modul darajasidagi YAGONA obyekt.** `app.state.enqueue_discovery` ni test ichida o'chirish (`del`) o'rniga TIKLASH kerak: `del` bilan marshrut modul darajasidagi haqiqiy brokerga tushib, compose tarmog'idagi Valkey'ga yozib qo'ydi (jurnalda `nvr_discovery_enqueued` ko'rindi). Test yon ta'sir qoldirdi va o'zi o'lchayotgan narsani chetlab o'tdi.
3. **`MarketNvrRows` — muzlatilgan `dataclass`, `NamedTuple` EMAS.** `_replace` o'rniga `dataclasses.replace()` kerak; `hasattr` bilan «har ehtimolga qarshi» yozilgan variant `discovery_run_ids` ni bo'sh qoldirib, matritsani `IndexError` bilan yiqitardi.
4. **`app_engine` ning `pool_size=1` i job testlarini DEADLOCK qilardi.** Job bir vaqtda ikki ulanish talab qiladi (uzun tranzaksiya + `channels_found` ning qisqa tranzaksiyasi). `api_sessionmaker` ishlatildi va sabab test modulining docstringida yozildi.
5. **BACKEND TO'PLAMI TO'LIQ YASHIL BO'LGANDAN KEYIN HAM `npm run gate` QIZIL EDI.** 1351 backend + 362 tenancy + 26 yangi test — hammasi o'tdi, `ruff`/`mypy` toza; darvozani esa **frontend** yiqitdi (deviation #8). Bu 03-04/03-05 dagi «to'liq to'plamda bir marta ko'rish MAJBURIY» darsining kengaytmasi: bu yerda «to'liq to'plam» backend'ning to'liq to'plami ham YETARLI EMAS edi — cheklov TIL CHEGARASIDAN o'tadi.

## Known Stubs

Yo'q. Yettala marshrut ham, job ham to'liq ishlaydi.

Ikkita **ochiq belgilangan soddalashtirish** bor:

| Joy | Soddalashtirish | Nega bu fazada yetarli |
|---|---|---|
| `NvrDeviceUpdateRequest` | Faqat `username` tahrirlanadi | `address` — `UNIQUE` kalitining qismi (UI-SPEC §4.6 uni ATAYIN taqiqlaydi); `tunnel_subnet` WireGuard yuzasiga tegishli va o'z rejasida keladi |
| Natija backend'i | `RedisAsyncResultBackend`, 7 kunlik TTL | Haqiqat manbai — `nvr_discovery_runs` qatori. Backend faqat «kecha qaysi vazifalar yiqildi?» savoli uchun va u bazadagi qatorga yetib bormaydigan nosozliklarni (serializatsiya, worker yiqilishi) ko'rsatadi |

## Threat Flags

Yangi ishonch chegarasi ochilmadi. Reja `<threat_model>` idagi **to'qqizala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-37 (`test-connection` brute-force) | ✅ `rl:nvr_test:<market_id>:<host>`, chegara **3** (Hikvision ~5 dan past); rad etilgan so'rov qurilmaga BORMAYDI — sanoq bilan o'lchandi |
| T-03-38 (kontekstsiz job) | ✅ `set_tenant_context(..., SYSTEM)` har tranzaksiyada; **sabotaj S1** 6 test qizartirdi va 19 API testi yashil qoldi |
| T-03-39 (parolning javobda sizishi) | ✅ Maydon UMUMAN yo'q; darvoza `app.routes` dan avtomatik kengayadi; 7/7 marshrut |
| T-03-40 (cross-tenant `nvr_id`/`run_id`) | ✅ `_not_found()` (404, 403 emas); matritsa yettala marshrutni qamraydi |
| T-03-41 (ikki vaqtdosh kashfiyot) | ✅ Qisman UNIQUE indeks → 409 + `run_id`; **sabotaj S2** |
| T-03-42 (kashfiyot so'rovni bloklashi) | ✅ 202 + poll; `enqueue_discovery` da `asyncio.timeout(5)` — navbat osilsa ham API bloklanmaydi |
| T-03-43 (izsiz kashfiyot) | ✅ `triggered_by` + har bosqichda `write_app_audit` (`nvr_discovery_runs`, `ActorKind.SYSTEM`); parol o'zgarishi QIYMATSIZ |
| T-03-44 (`market_id` tanadan) | ✅ So'rov modellarida bunday maydon yo'q; model maydonlari testda tekshiriladi |
| T-03-SC (paket o'rnatish) | ✅ `pyproject.toml` diffi **bo'sh** |

⚠ **03-11 uchun ochiq band (yangi flag emas, 03-04 ning davomi):** `audit-volume` remediatsiyasi (ustun bilan cheklangan trigger) migratsiya va `migrations/helpers.py` o'zgarishini talab qiladi — chetlanish **E** ga qarang.

## Next Phase Readiness

**03-07 (frontend API qatlami / WireGuard) uchun TAYYOR:**
- Yettala marshrut ham OpenAPI'da; `NvrTestConnectionResponse.auth_locked` UI-SPEC §4.4 ning qulf mantig'ini backendda hisoblaydi.
- 409 javob shakli: `{"detail": {"detail": "discovery_already_running", "run_id": "..."}}` — global handler bilan mos (`detail` satr bo'lib qolmadi, lekin u NEGA shunday ekani `DiscoveryConflictResponse` docstringida).
- ⚠ `GET /cameras` yo'q — kameralar ro'yxati 03-07 ning ishi; `TABLE_CAMERAS` konstantasi ALLAQACHON mavjud va `source_ip` ni `host()` bilan normalizatsiya qilish o'sha yerda kerak.
- ⚠ `NvrDeviceUpdateRequest` da `tunnel_subnet` YO'Q — D-07 ning to'qnashuv oqimi 03-07 ga qoldi va u YANGI xato kodini (`nvr_tunnel_subnet_taken`) talab qiladi.

**03-08 (frontend matni) uchun:**
- `MARKET_ERROR_CODES` endi **43** kod: 24 (2-faza) + 4 (NVR HTTP) + 1 (`nvr_address_invalid`) + 12 (`NVR_ERROR_CODES`) + 2 (job).
- ⚠ `nvr_credential_unreadable` va `discovery_internal_error` — `cameras.errorCause.*` da EMAS, `errors.*` da bo'lishi kerak: ular ISAPI muloqotining natijasi emas.

**04-faza (snapshot pipeline) uchun meros:**
- `app/worker.py` — mexanizm almashtirilsa ko'chiriladigan YAGONA fayl (~40 qator: broker, ilgaklar, qobiq, `enqueue_*`).
- `app/jobs/discovery.py::_system_transaction` — har fon-vazifa uchun ko'chiriladigan naqsh.
- ⚠ **`socket_timeout=None` ni ko'chirishni unutmang.** `redis-py 8` standarti bilan har qanday bloklanuvchi navbat o'quvchisi 5 soniyada yiqiladi.
- ⚠ Worker puli hozircha standart (`make_engine`). Bir vaqtda ishlaydigan job soni oshsa har job IKKI ulanish talab qilishini hisobga oling.

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**
1. `audit-volume` remediatsiyasi (chetlanish **E**).
2. `npm run test:sim:slow` fazani yopishdan oldin bir marta bajarilsin (03-05 ning qaydi).
3. `worker` konteyneri kod o'zgargandan keyin **`--build`** talab qiladi (Issue 1).
4. `.env` da `NVR_CREDENTIAL_KEY` bo'lmasa `npm run up` ham, `worker` ham ko'tarilmaydi — `.env.example` da qator bor, lekin bo'sh.

## Self-Check: PASSED

- **Fayllar:** 21/21 mavjud (6 yangi + 15 o'zgargan)
- **Commitlar:** 4/4 mavjud (`1256a9b`, `f17126a`, `08846e8`, `83c4604`)
- **`must_haves.artifacts` `contains`:** 4/4 — `ActorKind.SYSTEM` (`discovery.py`, 6×), `taskiq` (`worker.py`, 10×), `CAMERA_MANAGE` (`nvr.py`, 9×), `run_id` (`test_nvr_discovery_job.py`, 27×)
- **`min_lines`:** `nvr.py` — 200 talab, **694** mavjud
- **`must_haves.key_links`:** 3/3 — `discover` (`nvr.py` → 202 + `run_id`), `set_tenant_context` (`discovery.py`, 3×), `nvr_router` (`main.py`, 2×)
- **D-06 darvozasi:** `grep -cE "^\s*(import|from)\s+taskiq" jobs/discovery.py` = **0**
- **Ish daraxti:** uchala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
