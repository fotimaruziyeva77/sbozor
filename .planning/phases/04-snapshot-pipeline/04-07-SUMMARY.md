---
phase: 04-snapshot-pipeline
plan: 07
subsystem: backend
tags: [capture-pipeline, scheduler, taskiq, frame-source, isapi-picture, tenant-context, cam-05, cam-06, cam-07, d-02, d-06, d-07]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 05
    provides: "`capture_repo` (`ensure_plan`/`claim_due`/`release_expired`/`mark_missed`/`finish_*`/`defer`), `snapshot_repo.record()` va uning OCHIQ ziddiyati"
  - phase: 04-snapshot-pipeline
    plan: 06
    provides: "`storage.open()` / `SnapshotStorage.put`/`head`, sirsiz `StorageError`, `s3_client` fixture'i"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`quality.analyze()`, `object_key()`, `capture_errors` reyestri, fazaning 24 sozlamasi"
  - phase: 04-snapshot-pipeline
    plan: 03
    provides: "Beshta model, `capture_due_markets()`, `market_activate()` ning standart profili"
  - phase: 04-snapshot-pipeline
    plan: 02
    provides: "`SimState.frame_mode` va ISAPI `/picture` — D-07 ga MOSLANGAN (nol RTSP sessiyasi)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`jobs/discovery.py` shabloni, `worker.py` broker, `Go2rtcClient`, `IsapiClient`, `live_source`, `rtsp`"
provides:
  - "`app/services/frame_source.py` — `FrameSource` protokoli, `FrameSourcePool`, `capture_frame()`; uchta usul bitta protokol ortida, tanlov BAZADAN"
  - "`IsapiClient.fetch_picture()` — XML parseridan o'tmaydi; `IsapiClient.stream_claims` ommaviy"
  - "`_claims_rtsp_session()` — D-07 ning koddagi mexanizmi: `/picture` oqim DA'VO QILMAYDI"
  - "`app/jobs/capture.py` — `capture_tick` (to'rt qadam) va `capture_batch` (semafor + stagger), navbat kutubxonasisiz"
  - "`app/worker.py` — `scheduler` (bitta daqiqalik cron), `capture.tick`/`capture.batch` yupqa qobiqlari, `JOBS_QUEUE`, worker resurslari"
  - "`capture_repo.running_by_ids()` — navbat FAQAT identifikator tashiydi"
  - "`0016` — `snapshots.quality_mean`/`quality_stddev` NULLABLE (04-05 ning ochiq ziddiyati YOPILDI)"
  - "`0017` — `capture_due_markets()` ijarasi tugagan `running` qatorli bozorni ham qaytaradi"
affects: [04-08, 04-09, 04-10, 04-11, 04-12, 05-cv-zonalar, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Navbat kutubxonasi chegarasi ARGUMENT bilan majburlanadi: `capture_tick(..., enqueue=...)` — job `taskiq` ni ko'rmaydi va `worker.py` yagona o'tish nuqtasini beradi"
    - "Sabotaj natijasi TEST FAYLI bo'yicha ajratiladi: bitta o'zgarish ikki faylning BIRIDA qizarsa, ikki qaror haqiqatan mustaqil o'lchanayotgani isbotlanadi"
    - "«(a) yoki (b)» tanlovi noto'g'ri savol bo'lishi mumkin: ikki yechim IKKI XIL QATLAMDA yashasa ikkalasi ham kerak bo'ladi"
    - "`git checkout -- <fayl>` sabotajni tiklashda XAVFLI: u o'sha fayldagi COMMIT QILINMAGAN tuzatishni ham yuvib yuboradi — nusxa (`cp`) bilan tiklash ishonchliroq"
    - "Test dasturchining `.env` faylini o'lchamasligi kerak: `env_file` li `BaseSettings` da «o'zgaruvchi umuman yo'q» yo'li faqat `_env_file=None` bilan haqiqiy bo'ladi"
    - "Semafor MODUL darajasida keshlanadi (hajm -> obyekt): batch ichida qurilgan semafor «jarayonda bir vaqtda N ta» chegarasini UMUMAN bermasdi"

key-files:
  created:
    - services/core-api/app/services/frame_source.py
    - services/core-api/app/jobs/capture.py
    - tests/unit/test_frame_source.py
    - tests/integration/test_capture_tick.py
    - tests/integration/test_snapshot_quality.py
    - migrations/versions/0016_corrupt_frame_measurements.py
    - migrations/versions/0017_capture_due_watchdog.py
    - .planning/phases/04-snapshot-pipeline/deferred-items.md
  modified:
    - services/core-api/app/worker.py
    - services/core-api/app/jobs/__init__.py
    - services/core-api/app/services/isapi/client.py
    - services/core-api/app/repositories/capture_repo.py
    - services/core-api/app/repositories/snapshot_repo.py
    - packages/sbozor-core/sbozor_core/models/snapshot.py
    - migrations/entities/functions.py
    - compose.yaml
    - tests/unit/test_snapshot_settings.py
  deleted: []

key-decisions:
  - "04-05 NING OCHIQ ZIDDIYATI YOPILDI VA SAVOL NOTO'G'RI QO'YILGAN EDI: «(a) `corrupt` yozilmaydi» va «(b) ustunlar NULLABLE» BIR VAQTDA to'g'ri, chunki ular IKKI XIL QATLAMDA hal bo'ladi — `frame_source` ning magic-bayt darvozasi (javob umuman kadr emas -> `capture_invalid_response`, qator YO'Q) va `quality.analyze()` (javob kadr, lekin yaroqsiz -> `corrupt` qator, `is_billable=false`). `capture_invalid_response` HAM ishlatiladi, C4 hujayrasi HAM chiziladi"
  - "`SnapshotMeasurementMissingError` darvozasi OLIB TASHLANMADI, TORAYTIRILDI: `corrupt` dan boshqa verdikt uchun o'lchov MAJBURIY bo'lib qoladi — `ok` kadrni o'lchovsiz yozish D-15 ning butun mexanizmini jimgina buzardi"
  - "`0017` — `capture_due_markets()` ga UCHINCHI disjunkt. O'lchandi: ijara mexanizmi AYNAN o'zi qoplashi kerak bo'lgan holatda («worker o'rtada o'ldi») ishlamasdi, chunki `pending` qatori qolmagan bozor funksiyadan chiqmasdi va `release_expired()` UMUMAN chaqirilmasdi"
  - "D-07 KODDA HAM MAJBURLANDI: `_claims_rtsp_session()` `/picture` ni oqim da'vosidan CHIQARADI. Usiz `nvr_stream_limit` evristikasi eng XAVFSIZ usulni chegara qurboni deb belgilardi va adaptiv pasaytirish noto'g'ri tomonga ishlardi"
  - "Magic-bayt darvozasi `capture_frame()` da — BITTA joyda, uchala usul uchun; ISAPI protokoli chegarasida IKKINCHI qatlam (`fetch_picture`). Sabotaj ikkalasining mustaqilligini isbotladi"
  - "`_write_heartbeat` `Exception` ni yutadi, `SQLAlchemyError` ni EMAS: o'lchandi — `socket.gaierror` SQLAlchemy ga o'ralmaydi va butun tikni ENG OXIRIDA yiqitardi (reja allaqachon yozilgan, batch'lar allaqachon yuborilgan holatda)"
  - "`JOB_INTERNAL_ERROR = CAPTURE_WORKER_LOST` — reyestrga o'n ikkinchi kod QO'SHILMADI: u `04-UI-SPEC.md` §11.8 bilan mos va sanoq darvozasi bilan qulflangan o'n bir a'zoni o'zgartirardi hamda frontendga tarjimasiz kod berardi"
  - "`e2e` testlarida `capture_method = 'isapi'`: FAQAT ISAPI `/picture` javob baytlarini `frame_mode` dan oladi, ya'ni buzuq/HTML javoblarni BUYURTMA bilan berish mumkin. go2rtc oqimi bu to'rt shaklni bera olmaydi"
  - "`min_bytes` e2e testlarida 1024 ga tushirildi: simulyator kadri 320x180 (2 927 bayt) va yetkazilgan 4 096 poli ostida qoladi — pol REAL kadr uchun to'g'ri va u o'z alohida testiga ega"

patterns-established:
  - "Sabotaj o'lchovi endi TEST FAYLI kesimida ham hisobot beradi: «`test_capture_tick.py` 11/11 yashil» — `test_snapshot_quality.py` dagi 2 qizil bilan birga tartib qarorining ALOHIDA o'lchanayotganini isbotlaydi"
  - "O'z-o'ziga zid mezonni bajarishning uchinchi shakli: mezonning MEXANIKASI rejaning O'Z `<action>` bandiga zid bo'lsa, niyat KUCHLIROQ darvoza bilan bajariladi (satr sanog'i + `schedule=[` bloklari soni)"
  - "Yiqilgan testning sababini SQL darajasida ajratish: uch disjunktning har birini alohida `SELECT` bilan o'lchab, qaysi biri fire qilganini ko'rsatish «bu mening o'zgarishimmi?» savoliga aniq javob beradi"

requirements-completed: [CAM-05, CAM-06, CAM-07]

# Metrics
duration: 2h 05m
completed: 2026-08-05
---

# Phase 4 Plan 07: Kadr olish quvuri — tik, batch va uchta usul Summary

**Fazaning markaziy oqimi jonlandi va u KONTEYNERLARDA, mock'siz o'lchandi: planer `capture.tick` ni yubordi, tik rejani materializatsiya qildi, muddati kelgan slotni `SKIP LOCKED` bilan oldi, batch NVR simulyatoridan ISAPI `/picture` orqali kadr oldi, sifat filtri uni baholadi, SeaweedFS ga yozdi va `snapshots` qatorini qoldirdi — `2359.jpg`, 2 927 bayt, `corrupt`, `is_billable=false`. `04-05` ochiq qoldirgan `succeeded`+`corrupt` ziddiyati yopildi va uning savoli NOTO'G'RI qo'yilgani isbotlandi; D-07 endi faqat hujjatda emas, `_claims_rtsp_session()` da yashaydi; ijara mexanizmining AYNAN o'zi qoplashi kerak bo'lgan holatda ishlamasligi topilib `0017` bilan tuzatildi.**

## Performance

- **Duration:** ~2 soat 5 daqiqa (22:21 -> 00:26)
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 17 (8 yangi, 9 o'zgartirilgan) — 2 290 qator ishlab chiqarish kodi, 1 846 qator test
- **Commits:** 6 (bittasi TDD RED, ikkitasi topilgan nosozlik tuzatishi)

## Task Commits

| # | Task | Commit | Turi |
|---|------|--------|------|
| 1 | `frame_source` + `fetch_picture` — RED | `07ae0d5` | `test` |
| 1 | `frame_source` + `fetch_picture` — GREEN | `96ab8a9` | `feat` |
| — | `succeeded`+`corrupt` ziddiyatining yechimi (`0016`) | `cbccd49` | `fix` |
| 2 | `jobs/capture.py` — tik va batch | `431608f` | `feat` |
| 3 | `worker.py` planer + qobiqlar + e2e testlar (`0017`) | `29e4d54` | `feat` |
| — | `.env` dan mustaqil sozlama darvozasi | `d8b71e5` | `fix` |

## ⛔ EGALIK QILINGAN QAROR — `succeeded` + `corrupt`

`04-05` bu bandni ATAYIN qattiq yiqiladigan qilib qoldirgan va egasini shu reja deb nomlagan edi. U ziddiyatni shunday qo'ygan:

> «(a) `corrupt` kadr `snapshots` ga umuman yozilmaydi» va «(b) migratsiya ustunlarni NULLABLE qiladi» — **bir vaqtda to'g'ri bo'la olmaydi**: birinchisida C4 hujayrasi hech qachon chizilmaydi, ikkinchisida `capture_invalid_response` kodi ishlatilmaydi.

**O'lchov ko'rsatdiki savol noto'g'ri qo'yilgan edi. Ikkala yechim ham kerak, chunki ular IKKI XIL nosozlikni IKKI XIL QATLAMDA ifodalaydi:**

| Nosozlik | Qaysi qatlam rad etadi | Natija |
|---|---|---|
| Javob **umuman kadr emas** (HTML sahifa, bo'sh tana, JPEG bo'lmagan bayt) | `frame_source` ning magic-bayt darvozasi — sifat tahliliga UMUMAN qo'ymaydi | `capture_invalid_response`, qator `failed`, `snapshots` qatori **YO'Q** → **(a) bajarildi** |
| Javob **kadr, lekin yaroqsiz** (kesilgan JPEG, dekod xatosi) | `quality.analyze()` — `corrupt`, o'lchovlar `None` | qator `succeeded`, `snapshots` qatori **BOR**, `is_billable=false` → **C4 hujayrasi CHIZILADI, (b) bajarildi** |

Ya'ni `capture_invalid_response` **HAM** ishlatiladi va C4 hujayrasi **HAM** mavjud bo'ladi. Yagona kerak bo'lgan narsa — ikkinchi yo'l uchun ustunlarning `NULL` qabul qilishi (`0016`).

**Darvoza olib tashlanmadi, TORAYTIRILDI:** `SnapshotMeasurementMissingError` endi faqat `corrupt` dan **boshqa** verdiktda o'lchovsiz yozishni rad etadi. `ok` kadrni o'lchovsiz yozish D-15 ning butun mexanizmini (chegaralarni haqiqiy taqsimotdan chiqarish) jimgina buzardi va nosozlik faqat Phase 0 da ko'rinardi. **Sentinel nol RAD ETILDI** — u bazada «o'lchandi va nol chiqdi» ma'nosini berardi va `percentile_cont` ni pastga tortardi.

Bu qaror **ishlab chiqarish konfiguratsiyasida** ham o'lchandi (pastdagi konteyner o'lchovi): yetkazilgan `QUALITY_MIN_BYTES=4096` bilan simulyatorning 2 927 baytli kadri `corrupt` bo'ldi va qator `succeeded` + `is_billable=false` + `quality_mean IS NULL` bilan yozildi.

## KONTEYNER USTIDAGI O'LCHOV — natija BAZADAN, konteyner holatidan EMAS

Reja bu bandni Pitfall 14 bilan qulflagan: «bu konteyner healthcheck'i emas — natija bazadan o'lchanadi».

```
23:17:46  scheduler  Starting scheduler. / Startup completed.
23:17:47  scheduler  Sending task capture.tick with schedule_id 4cbc6252...
23:17:47  worker     Executing task capture.tick
23:17:47  worker     capture_tick_done markets=1 created=7 skipped=7 claimed=0
```

```sql
SELECT status, count(*) FROM capture_runs WHERE business_date = bugun GROUP BY status;
 skipped | 7          <- 23:17 da BARCHA slotlar (06:00–18:00) grace dan chiqqan
SELECT component, last_seen_at, detail FROM system_heartbeats;
 capture_tick | 23:17:47.152 | {"missed":0,"claimed":0,"created":7,"markets":1}
```

Keyin **muddati kelgan** bitta slot qo'yildi (`23:59`, `now() - 30 s`) va zanjir oxirigacha bordi:

```sql
 status    | error_code | capture_method | quality_verdict | is_billable | size_bytes | object_key
-----------+------------+----------------+-----------------+-------------+------------+-----------
 succeeded |            | isapi          | corrupt         | f           |       2927 | <market>/2026-08-04/<camera>/2359.jpg
```

```
weed shell> fs.ls /buckets/sbozor-snapshots/<market>/2026-08-04/<camera>/
2359.jpg
```

Ya'ni **planer → navbat → tik → `claim_due` → batch → ISAPI `/picture` → sifat → S3 → baza** zanjirining har bir halqasi konteynerlarda ishladi. O'lchov ma'lumotlari keyin to'liq tozalandi (`markets=0, runs=0, snaps=0`, ombor prefiksi bo'sh).

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `capture_frame()` dan magic-bayt darvozasi olib tashlandi | **AYNAN 1 test**: `test_an_html_body_is_rejected_even_when_the_content_type_says_jpeg` (`DID NOT RAISE`) | Qolgan **21**, jumladan `..._timeout_becomes_capture_timeout`, `..._401_...` VA **ISAPI ning HTML testi** | ✅ **AYNAN bashorat qilingandek**, ustiga BONUS: ISAPI yo'li YASHIL qoldi, chunki `fetch_picture` ning O'Z magic-bayt qatlami uni tutdi — ya'ni ikki qatlamning mustaqilligi ham o'lchandi |
| 2 | `_system_transaction()` dan `set_tenant_context` chaqiruvi olib tashlandi | **5 test**: `test_capture_tick_sets_tenant_context` (ikkinchi yarmi — `assert 0 > 0`), `test_duplicate_tick_is_noop` (`0 == 14`), `test_expired_lease_returns_to_pending`, `test_overdue_slot_is_missed_not_executed`, `test_fan_out_...` | **6 test**: uchala matn/tip darvozasi, navbat nomi, yurak urishi va `_heartbeat_failure_is_swallowed` | ⚠ **Reja IKKI testni bashorat qilgan edi, o'lchandi — BESHTA.** Sabab: kontekstsiz tik BIRORTA qator yozmaydi, ya'ni HAR BIR xulq testi qizaradi. Rejaning «teskari yo'nalishda qizaradi» tahlili TO'G'RI chiqdi: `..._sets_tenant_context` ning birinchi yarmi (0 qator) o'tadi, IKKINCHI yarmi (kontekst bilan >0) yiqiladi |
| 3 | `storage.put()` o'tkazib yuborildi (baza qatori MAVJUD BO'LMAGAN obyektga havola qiladi) | **`test_snapshot_quality.py` da AYNAN 2 test**: `test_a_good_frame_walks_the_whole_chain` va `test_a_truncated_frame_is_stored_but_never_billable` — ikkalasi ham `head()` assertida | **`test_capture_tick.py` — 11/11 YASHIL**; `..._html_response_...` va `test_non_billable_cannot_be_referenced` ham yashil | ✅ **AYNAN bashorat qilingandek** («`test_capture_tick.py` yashil qoladi»). ⚠ Sabotajning MEXANIKASI o'zgartirildi: rejaning «`put()` ni `record()` dan KEYIN ko'chirish» varianti obyektni BARIBIR yozardi, ya'ni `head()` uni topardi va sabotaj HECH NIMANI qizartirmasdi. `put()` ni butunlay o'tkazib yuborish — «tartib teskari + S3 xatosi» holatining AYNAN natijasi |

Uchala holatda ham fayl darhol tiklandi va to'plam qayta yashil bo'ldi.

⚠ **2-sabotajning tiklanishi bitta darsni berdi:** `git checkout -- services/core-api/app/jobs/capture.py` sabotajni ham, o'sha faylda TURGAN COMMIT QILINMAGAN tuzatishni ham (yurak urishining `except Exception` kengaytmasi) yuvib yubordi — va u keyingi yugurishda boshqa test sifatida ko'rindi. Qolgan sabotajlar `cp` bilan olingan nusxadan tiklandi.

## O'LCHOVLAR — taxmin qilinmadi

| Savol | O'lchangan javob | Qarorga ta'siri |
|---|---|---|
| `capture_due_markets()` ijarasi tugagan `running` qatorli bozorni qaytaradimi? | **YO'Q.** `TickResult(markets=1, created=0, released=0)` — fixture bozori funksiyadan UMUMAN chiqmadi | `0017` migratsiyasi (pastda, 2-deviatsiya) |
| Yetib bo'lmaydigan bazaga `_write_heartbeat` nima beradi? | **`socket.gaierror`** — `SQLAlchemyError` ga O'RALMAYDI va `except SQLAlchemyError` uni tutmaydi | `except Exception` (3-deviatsiya) |
| `Settings()` `tests` konteynerida `.env` faylini o'qiydimi? | **HA** — `model_config` da `env_file=".env"` va repo `/app` ga mount qilingan | `_env_file=None` (5-deviatsiya) |
| Simulyatorning `frame_mode="ok"` kadri yetkazilgan `QUALITY_MIN_BYTES` dan o'tadimi? | **YO'Q** — 2 927 bayt < 4 096 | e2e testlarida `min_bytes=1024`; ishlab chiqarish o'lchovida verdikt `corrupt` bo'ldi va bu `0016` ning yo'lini KO'RSATDI |
| `capture_due_markets()` ning qaysi disjunkti yarim tunda testni qizartirdi? | **Ikkinchisi** (`NOT EXISTS bugungi reja`): `now()+5 daq` qatori ERTANGI kunga tushdi. **Uchinchisi (mening qo'shganim) `FALSE`** | Nosozlik `0015` dan meros, `0017` bilan aloqasi yo'q (`deferred-items.md` 1-band) |
| `capture_batch_task.kiq(...)` mypy'dan o'tadimi? | **YO'Q** — `Context` majburiy pozitsion argument sifatida ko'rinadi | `kicker().kiq(**payload)` (`enqueue_discovery` bilan bir xil yo'l) |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/unit/test_frame_source.py -q` | **22 test**, exit 0 (talab ≥ 8) |
| 2 | `pytest tests/integration/test_capture_tick.py -q` | **11 test**, exit 0 (talab ≥ 8) |
| 3 | `pytest tests/integration/test_snapshot_quality.py -m sim -q` | **4 test**, exit 0 (talab ≥ 4) |
| 4 | `pytest tests/integration/test_capture_tick.py::test_capture_tick_sets_tenant_context -q` | exit 0 |
| 5 | `python -c "... os.environ.pop('NVR_CREDENTIAL_KEY'); import app.worker; hasattr(w,'scheduler')"` | **OK** — modul `Settings` siz import bo'ladi |
| 6 | `isinstance(w.scheduler, TaskiqScheduler)` | **OK** |
| 7 | `grep -cE '^\s*(import\|from)\s+taskiq' app/jobs/capture.py` | **0** (S-4) |
| 8 | Vaqt in'ektsiyasi / `_system_transaction` / navbat `claim_due` dan keyin / `SKIP LOCKED` ochiq savoli | **to'rtala darvoza ham OK** |
| 9 | `docker compose up -d --build worker scheduler` + 60 s + SQL | **`capture_runs` da 7 qator, yurak urishi yozilgan** (yuqoridagi bo'lim) |
| 10 | `ruff check . && ruff format --check . && mypy .` | exit 0 — **236 fayl formatlangan, 229 fayl tiplangan** |
| 11 | `pytest -q` (to'liq) | **1 755 test**, exit 0 — baza 1 718 → **+37** (talab ≥ 1 520) |
| 12 | `pytest tests/tenancy -q` | **426** (o'zgarmagan, talab ≥ 412) |
| 13 | `pytest tests/unit/test_no_sim_branching.py -q` | **5**, exit 0 |
| 14 | `pytest tests/integration/test_nvr_discovery_job.py tests/integration/test_capture_repo.py -q` | **38**, exit 0 (mavjud yo'llar qizarmagan) |
| 15 | `npm run gate` | **exit 0** |
| 16 | vitest / node / i18n | **246 / 111 / 577×3** (uchalasi ham o'zgarmagan) |
| 17 | `git diff --exit-code pyproject.toml package.json package-lock.json` | **o'zgarish yo'q** (T-04-SC) |

Artefakt mezonlari: `frame_source.py` **666** qator (talab ≥ 200, `capture_method` bor); `capture.py` **1 142** qator (talab ≥ 300, `_system_transaction` bor); `worker.py` da `TaskiqScheduler` va `capture.tick` bor; `key_links` uchalasi ham o'lchandi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — yetishmayotgan kritik xulq] D-07 KODDA majburlanmagan edi**

- **Topildi:** Task 1, `fetch_picture()` ni `_send()` ga ulaganda
- **Muammo:** `IsapiClient._attempt()` `path.startswith("Streaming/channels/")` bo'lgan HAR BIR yo'lni RTSP sessiya da'vosi deb sanaydi. `/picture` ham o'sha prefiksdan boshlanadi, ya'ni u sanoqqa tushardi. Sanoq esa `_classify()` ning `nvr_stream_limit` evristikasining KIRISHI: `path.startswith(prefix) and self._stream_claims >= 1` → `nvr_stream_limit`.
- **Nima uchun kritik:** D-07 ning butun mazmuni «ISAPI `/picture` NOL RTSP sessiyasi ochadi, ya'ni sessiya bosimida u ENG XAVFSIZ yo'l». Sanoqqa tushgan holda esa `/picture` yo'lidagi har qanday tarmoq uzilishi «NVR chegarasi to'ldi» deb talqin qilinardi va `04-07` ning adaptiv pasaytirishi eng xavfsiz usulni CHEGARA QURBONI deb belgilab, chegarani sababsiz tushirardi. `04-02` simulyatorni AYNAN shu sababdan tuzatgan edi (3-fazadagi sim `/picture` da `_claim_stream()` chaqirardi — D-07 ning teskarisi); mahsulot tomoni esa tuzatilmay qolgan edi.
- **Yechim:** `_claims_rtsp_session(path)` predikati — `Streaming/channels/` bilan boshlanadi VA `/picture` bilan tugamaydi. U IKKI joyda ishlatiladi (`_attempt` sanog'i va `_classify` evristikasi).
- **Verifikatsiya:** `test_the_isapi_path_claims_no_rtsp_session` — ikki marta `/picture` dan keyin `client.stream_claims == 0`. `IsapiClient.stream_claims` ommaviy property qilindi (xususiy maydonga test orqali tegish o'lchovni mahsulot yuzasidan uzardi).
- **Committed in:** `96ab8a9`

**2. [Rule 2 — yetishmayotgan kritik xulq] Ijara mexanizmi AYNAN o'zi qoplashi kerak bo'lgan holatda ishlamasdi**

- **Topildi:** Task 3, `test_expired_lease_returns_to_pending` birinchi yugurishida
- **O'lchandi:** `TickResult(markets=1, created=0, skipped=0, released=0, claimed=0, ...)` — fixture bozori `capture_due_markets()` dan **umuman chiqmadi**.
- **Muammo:** `0015` ning funksiyasi ikki shart bilan qurilgan: muddati kelgan `pending` qator BOR, yoki bugungi reja HALI yo'q. Uchinchi holat — «reja bor, `pending` qator yo'q, lekin ijarasi tugagan `running` qator bor» — ikkalasiga ham tushmaydi. Ishlab chiqarishdagi ketma-ketlik:

  ```
  06:00  worker batch o'rtasida o'ldi  -> 25 qator `running`
  06:01  tik: `pending` yo'q (keyingisi 06:30 da) VA bugungi reja BOR
             -> bozor funksiyadan CHIQMAYDI
             -> `release_expired()` UMUMAN chaqirilmaydi
  06:30  tik: bozor qaytadi, qatorlar bo'shatiladi — LEKIN grace (600 s)
             allaqachon o'tgan -> ular `missed` bo'ladi
  ```

  Ya'ni qayta urinish uchun berilgan **9 daqiqa jimgina yo'qolardi**: xato yo'q, jurnal yozuvi yo'q, alert faqat kun oxirida. CAM-05 ning «kadr olish uzilsa **urinish qayta bajariladi**» talabi bajarilmasdi.
- **Yechim:** `0017` migratsiyasi — uchinchi disjunkt: `EXISTS (running qator, locked_until IS NULL OR <= now())`. Shart ATAYIN tor: har qanday `running` bo'yicha filtrlash normal kadr olish davomida BARCHA bozorlarni qaytarib, ikkinchi shartning («muddati kelmagan slot — ish emas», `0015` da alohida test bilan qulflangan) ma'nosini yo'qotardi.
- **Verifikatsiya:** `test_expired_lease_returns_to_pending` — `released >= 1` VA qator o'sha tikda QAYTA olinadi (`locked_by` o'zgargan). Mavjud `test_capture_due_markets_exposes_only_identifiers` qizarmadi (u faqat `pending` qator yozadi).
- **Committed in:** `29e4d54`

**3. [Rule 1 — o'lchanmagan faraz] Yurak urishining `except SQLAlchemyError` i yetarli emas edi**

- **Topildi:** Task 3, `test_a_heartbeat_failure_is_swallowed` birinchi yugurishida
- **O'lchandi:** yetib bo'lmaydigan xostga qurilgan sessiya fabrikasi bilan `_write_heartbeat` **`socket.gaierror`** beradi — u `SQLAlchemyError` ga O'RALMAYDI, chunki xato SQLAlchemy dialekti ishga tushishidan OLDIN, `asyncio.getaddrinfo` ichida yuz beradi.
- **Nima uchun kritik:** yurak urishi tikning **eng oxirida** yoziladi. O'sha paytda reja allaqachon materializatsiya qilingan, `missed` slotlar yopilgan va batch'lar navbatga qo'yilgan bo'ladi — ya'ni tik butun ishini bajarib bo'lib, FAQAT monitoring yozuvi tufayli yiqilardi. Va u har daqiqada takrorlanardi.
- **Yechim:** `except Exception` (`# noqa: BLE001`) + `type(exc).__name__` (istisno matni EMAS — u ulanish satrini tashiydi). `discovery.py::_publish_channels_found` dan farq sababi izohda: u tranzaksiya O'RTASIDA chaqiriladi va ulanish allaqachon o'rnatilgan.
- **Committed in:** `29e4d54`

**4. [Rule 3 — bloklovchi] `capture_repo` da navbat vazifasi uchun o'qish metodi yo'q edi**

- **Muammo:** rejaning `capture_batch(..., run_ids)` imzosi navbat xabaridan FAQAT identifikatorlarni oladi, `capture_repo` da esa qatorlarni identifikator bo'yicha o'qiydigan metod yo'q (`claim_due()` ularni FAQAT qulflab olish paytida beradi).
- **Muqobil rad etildi:** slot vaqti va biznes-kunni navbat xabariga solish ularni JSON'da IKKINCHI HAQIQAT MANBAIGA aylantirardi — vazifa navbatda turgan paytda `release_expired()` qatorni qaytarib yuborishi mumkin va worker ESKIRGAN qiymatlar bilan kadr yozardi.
- **Yechim:** `CaptureRepository.running_by_ids()` — mavjud `ClaimedRun` dataclassini qaytaradi va `status = 'running'` predikati bilan filtrlaydi. Predikat DARVOZA: navbat vazifani «kamida bir marta» yetkazadi, ikkinchi chaqiruvda qator allaqachon yakunlangan bo'ladi va batch JIMGINA no-op bo'ladi.
- **Committed in:** `431608f`

**5. [Rule 1 — bug] Sozlama darvozasi dasturchining `.env` faylini o'lchayotgan edi**

- **Topildi:** to'liq `pytest -q` yugurishida (`test_a_missing_empty_s3_key_env_var_fails_the_same_way` qizardi)
- **Muammo:** `Settings.model_config` da `env_file=".env"` va `tests` konteyneri repozitoriyni `/app` ga mount qiladi. `compose.yaml` esa `worker`/`scheduler`/`core-api` bloklariga `${S3_ACCESS_KEY}` ni **standartsiz** beradi, ya'ni konteynerlarni ishga tushirish uchun kalit `.env` da BO'LISHI SHART. Ikkalasi birga: to'g'ri sozlangan dasturchi mashinasida darvoza QIZARADI. `monkeypatch.delenv` faylni yopa olmaydi.
- **Yechim:** `Settings(_env_file=None)` — ikki joyda (`build` fixture'i va o'sha test). Darvoza endi AYNAN maydonning STANDARTINI o'lchaydi va muhitdan mustaqil. Test **kuchaydi**, zaiflashmadi: fayl bo'lsa ham, bo'lmasa ham natija bir xil.
- **Qoldiq:** `.env.example` hali ham bo'sh kalit beradi — `deferred-items.md` 2-band.
- **Committed in:** `d8b71e5`

**6. [O'z-o'ziga zid mezon] «AYNAN bitta `"cron": "* * * * *"` literali» mezoni bajarib bo'lmaydi**

- **Qayerda:** Task 3 ning qabul mezoni `len(re.findall(r'"cron"\s*:\s*"\* \* \* \* \*"', t)) == 1`
- **Muammo:** o'sha rejaning O'Z `<action>` §2 bandi cron satrini **nomlangan konstanta** qilishni talab qiladi («Cron satri — **literal konstanta**, sozlama emas»). Konstanta bo'lganda dekoratorda `schedule=[{"cron": TICK_CRON}]` turadi va inline literal UMUMAN uchramaydi — ya'ni ikki shart bir vaqtda bajarilmaydi.
- **Yechim:** mezonning NIYATI («ikkinchi daqiqalik cron qo'shilsa darvoza qizarsin») **kuchliroq** shaklda bajarildi va u testga aylantirildi (`test_the_scheduler_has_exactly_one_minute_cron`): `"* * * * *"` satri **aynan 1 marta** VA `schedule=[` bloklari **aynan 1 marta**. Ikkinchi shart rejaning o'z variantidan kuchliroq — u BOSHQA literal bilan yozilgan ikkinchi jadvalni ham ushlaydi.
- **O'lchandi:** ikkala sanoq ham 1.
- **Fayllar:** `tests/integration/test_capture_tick.py`

**7. [O'z-o'ziga zid mezon] SABOTAJ 2 ning mexanikasi qizil bermasdi**

- **Qayerda:** Task 3 ning ikkinchi sabotaji: «`storage.put()` ni `snapshot_repo.record()` dan KEYIN ko'chirish»
- **Muammo:** shunchaki ko'chirish obyektni BARIBIR yozardi (faqat kechroq), ya'ni `head()` uni topardi va sabotaj HECH NIMANI qizartirmasdi. Mezonning qavs ichidagi izohi buni ochiq aytadi: «(S3 xatosi holatida qator qolib ketadi)» — ya'ni haqiqiy nosozlik uchun IKKI o'zgarish kerak (tartib + S3 xatosi).
- **Yechim:** ikkalasi bitta qadamga yig'ildi — `put()` butunlay o'tkazib yuborildi va `PutResult` soxta qurildi. Bu «tartib teskari + S3 yiqildi» holatining AYNAN kuzatiladigan natijasi: baza qatori MAVJUD BO'LMAGAN obyektga havola qiladi.
- **Natija:** bashorat aynan tasdiqlandi — `test_capture_tick.py` **11/11 yashil**, `test_snapshot_quality.py` da AYNAN 2 test qizardi.

**8. [Rule 3 — bloklovchi] `ops/seaweedfs/s3.json` KATALOG bo'lib yaratilgan edi**

- **Muammo:** Docker bind-mount manba fayli bo'lmaganda uni **katalog** qilib yaratadi. `storage` konteyneri `-s3.config=/etc/seaweedfs/s3.json` ni katalog sifatida ko'rardi.
- **Yechim:** `rmdir` + `.example` dan fayl (kalitlar `compose.yaml` ning `tests` bloki standartlari bilan AYNAN bir xil). `.env` ga ham `S3_ACCESS_KEY`/`S3_SECRET_KEY` qo'shildi (`worker`/`scheduler` ularni standartsiz talab qiladi). Ikkala fayl ham `.gitignore` ostida — repoga tushmadi (`git check-ignore -v` bilan tasdiqlandi).
- **Qoldiq:** `deferred-items.md` 3-band.

---

**Total deviations:** 8 (3× Rule 2 yetishmayotgan kritik xulq, 2× Rule 1 bug, 2× o'z-o'ziga zid mezon, 1× Rule 3 bloklovchi)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Uchtasi (1, 2, 3) rejada umuman ko'rilmagan **jim nosozlikni** yopdi va uchalasi ham «xato bermaydi, alert bermaydi, faqat kun oxirida ko'rinadi» sinfiga tegishli edi.

## Qamrov chegaralari — ochiq yozilgan

1. **go2rtc yo'li e2e da o'lchanmagan.** `test_snapshot_quality.py` `capture_method='isapi'` bilan ishlaydi (sabab modul docstringida: FAQAT ISAPI javob baytlarini `frame_mode` dan oladi). go2rtc yo'li `test_frame_source.py` da `respx` bilan to'liq qoplangan (ro'yxatga olish tartibi, parametr allow-listi, `404`/timeout/`401` xaritalashi, sir oqishi), lekin **haqiqiy go2rtc konteyneri ustida kadr olish** o'lchanmagan. Uning eng yaqin mavjud o'lchovi — `test_live_view_e2e.py` (03-14) va u `/api/frame.jpeg` ni AYNAN o'sha yo'l bilan chaqiradi. **Egasi:** `04-12` (faza darvozasi).

2. **`ffmpeg` yo'li real subprocess bilan o'lchanmagan** — testda `asyncio.create_subprocess_exec` almashtiriladi. O'lchangani: argv shakli (shellsiz, ro'yxat, rekvizitli manba), timeout'da `kill()` **va** `wait()`, nolga teng bo'lmagan chiqishda `stderr` ning xato matniga tushmasligi. Haqiqiy `ffmpeg` `runtime` image'ida **yo'q** (u `cv-service` ning bog'liqligi, 5-faza), ya'ni bu yo'l bugun **oxirgi chora sifatida ham ishlamaydi** va `OSError` → `capture_source_unreachable` beradi. **Egasi:** `04-12` yoki 5-faza.

3. **Adaptiv pasaytirish (`observed_stream_limit`) testsiz.** Kod yozilgan va ikki qattiq shart bilan qulflangan (≥2 nosozlik VA ≥1 muvaffaqiyat), lekin uni o'lchash uchun NVR sessiya chegarasini modellaydigan simulyator kerak — `04-02` ochiq yozganidek, sim uni **umuman modellashtirmaydi**. **Egasi:** real NVR (Phase 0/pilot) yoki sim'ga chegara qo'shadigan reja.

4. **`capture_batch` ning auth-qulflash yo'li integratsiya testida o'lchanmagan.** Mantiq yozilgan (`_account` → `stopped_code` → `_finish_unprocessed`) va u `capture_repo` darajasida allaqachon o'lchangan (`test_an_auth_locking_code_burns_the_whole_retry_budget`, 04-05). Batch darajasidagi «qolgan kameralarga borilmaydi» da'vosi esa bir NVR da IKKI kamera va noto'g'ri parol talab qiladi. **Egasi:** `04-12`.

## Bazaviy holat

| O'lchov | Baza (`385a6d5`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 718 | **1 755** | ✅ +37 |
| tenancy | 426 | **426** | ✅ o'zgarmagan |
| vitest | 246 | **246** | ✅ o'zgarmagan |
| node darvozalari | 111 | **111** | ✅ o'zgarmagan |
| i18n | 577 × 3 | **577 × 3** | ✅ o'zgarmagan |
| `ruff` + `ruff format` + `mypy` | toza | **toza** (236 / 229 fayl) | ✅ |
| `npm run gate` | — | **exit 0** | ✅ |
| `git diff pyproject.toml package.json` | — | **o'zgarish yo'q** | ✅ (T-04-SC) |

## Issues Encountered

- **`npm run gate` birinchi yugurishda 23:59:33 da qizardi** — `tests/tenancy/test_snapshot_domain_meta.py::test_capture_due_markets_exposes_only_identifiers`. Sabab SQL darajasida ajratildi: test `now() + 5 daqiqa` da qator yozadi, u yarim tundan oldin **ERTANGI** biznes-kunga tushadi va `capture_due_markets()` ning **IKKINCHI** disjunkti («bugungi reja YO'Q») ishga tushadi. Uchinchi disjunkt (04-07 qo'shgan) o'sha holatda `FALSE` — u `status = 'running'` talab qiladi, test esa faqat `pending` yozadi. Yarim tundan keyin test qayta yashil bo'ldi va `npm run gate` **exit 0** berdi. Band `deferred-items.md` ga yozildi.
- **`ops/seaweedfs/s3.json` katalog edi va `.env` da S3 kalitlari yo'q edi** — ikkalasi ham tuzatildi (8-deviatsiya). Ikkala fayl ham `.gitignore` ostida.
- **`docker compose up -d --force-recreate scheduler` YETMAYDI** — `scheduler`/`worker` `target: runtime` bilan quriladi va kod image ICHIGA ko'chiriladi. `--build` bayrog'isiz konteyner ESKI kodni ishga tushiradi. O'lchov `up -d --build` bilan bajarildi.
- **Konteyner o'lchovi uchun bazaga minimal faol bozor QO'LDA yozildi** (`market_activate()` standart profilni berdi) va o'lchovdan keyin to'liq tozalandi.

## Known Stubs

Yo'q. Uchala task ham to'liq ishlaydi. Yuqoridagi «Qamrov chegaralari» bo'limidagi to'rt band **stub emas** — ular yozilgan va ishlaydigan kodning **o'lchanmagan** yuzalari va har birining egasi nomlangan.

## Threat Flags

Yangi tarmoq **endpointi** yo'q (kod NVR ga va S3 ga MIJOZ sifatida boradi). Ikkita sxema o'zgarishi bor va ikkalasi ham migratsiya bilan hujjatlangan (`0016` — ustun nullability, `0017` — `SECURITY DEFINER` funksiyaning predikati; `_regrant()` ikkalasida ham bajarildi).

| Threat | Holat |
|---|---|
| T-04-48 (tikning tenant chegarasini kesib o'tishi) | `capture_due_markets()` FAQAT identifikator beradi; har bozorga ALOHIDA `_system_transaction()`; kontekstsiz 0 qator ANIQ o'lchangan va sabotaj bilan tasdiqlangan |
| T-04-49 (NVR paroli xato matnida) | `_failure()` faqat KOD va TUR beradi; `from None` + istisno `except` blokidan TASHQARIDA; `ffmpeg` `stderr` = `DEVNULL`; test NAZORAT holati bilan (xom istisno parolni HAQIQATAN tashiydi) |
| T-04-50 (`401` da retry — hisob qulflanishi) | `CAPTURE_AUTH_LOCKING_CODES` butun batchni to'xtatadi; qolgan qatorlar o'sha kod bilan yopiladi; `finish_failed` byudjetni to'liq yoqadi (04-05) |
| T-04-51 (sessiya chegarasiga urilish) | Ikki darajali semafor (global kesh + per-NVR) + stagger; adaptiv PASAYTIRISH ikki qattiq shart ostida; oshirish YO'Q |
| T-04-52 (keshlangan kadr) | So'rov parametrlari allow-list (`{"src"}`); `cache` satri kodda YO'Q — matn darvozasi bilan |
| T-04-53 (HTML sahifa yaroqli kadr sifatida) | Magic-bayt darvozasi IKKI qatlamda (`capture_frame` va `fetch_picture`); `Content-Type` ga ishonilmaydi; sabotaj mustaqilligini isbotladi |
| T-04-54 (baza qatori mavjud bo'lmagan obyektga havola) | Tartib QAT'IY; `StorageError` da `snapshots` qatori YOZILMAYDI; sabotaj bilan o'lchandi |
| T-04-55 (job jarayonining yiqilishi) | `except Exception` uch joyda (`_capture_one`, yozuv tranzaksiyasi, `enqueue`); `_Finisher.done` to'plami har qatorni yakuniy holatga keltiradi |
| T-04-56 (`ffmpeg` osilishi va zombi) | `asyncio.wait_for` + `kill()` + `await wait()`; shell YO'Q, argv ro'yxat; `ProcessLookupError` yutiladi |
| T-04-57 (planer holatiga ishonish) | Planer HOLATSIZ; reja Postgres'da; `test_duplicate_tick_is_noop` + konteyner ustidagi 60 s o'lchovi |
| T-04-SC (paket o'rnatish) | Yangi paket YO'Q; `git diff --exit-code` toza |

⚠ **Yangi mitigatsiya (registerda yo'q edi):** `_claims_rtsp_session()` — D-07 ning koddagi majburlanishi (1-deviatsiya). Usiz adaptiv pasaytirish **eng xavfsiz usulni** chegara qurboni deb belgilardi.

## Next Phase Readiness

**`04-08` (alert + retention) uchun tayyor:**
- `TickResult.missed` — `list[MissedSlot]`, D-20 ning YAGONA manbai. `capture_tick` uni har tikda qaytaradi.
- `system_heartbeats['capture_tick']` yoziladi; komponent nomi `CAPTURE_TICK_COMPONENT` konstantasida va `/internal/self-check` **AYNAN o'sha satrni** import qilishi shart.
- Yangi vazifa (`alert.sweep`, `retention.sweep`) **`JOBS_QUEUE` ga** qo'shiladi — ikkinchi navbat ochilmaydi (sabab `worker.py` da).
- ⚠ **Ikki band `04-06` dan o'tkazilgan va HALI OCHIQ:** (a) `tests` xizmatiga `depends_on: storage`, (b) `censor_secrets` ning `s3_*` qamrovi.

**`04-09`/`04-10` (API/UI) uchun:**
- `capture_runs.capture_method` endi to'ldiriladi (DALIL); `nvr_devices.capture_method` — SOZLAMA. UI ikkalasini ham ko'rsatishi mumkin va farq dala diagnostikasining birinchi savoli.
- `snapshots.quality_mean`/`quality_stddev` endi **NULLABLE** — UI `corrupt` qatorda o'lchov ustunlarini bo'sh ko'rsatishi kerak (`—`, `0` EMAS).
- UI-SPEC §6.4 ning **C4 hujayrasi** (`succeeded` + `corrupt`) endi HAQIQATAN mavjud va u `test_a_truncated_frame_is_stored_but_never_billable` bilan qulflangan.

**`04-12` (faza darvozasi) uchun:** yuqoridagi «Qamrov chegaralari» ning to'rtala bandi va `deferred-items.md` ning uchala bandi.

⚠ **`REQUIREMENTS.md` ATAYIN TEGILMADI.** SDK `CAM-05`/`CAM-06`/`CAM-07` ni `Complete` deb belgilagan edi va o'zgarish QAYTARILDI — `03-01` da o'rnatilgan qoida bo'yicha faza darajasidagi talablar reja emas, **FAZA** oxirida, dalil bilan belgilanadi. Sabab bu yerda aniq: `CAM-05` ning matni «o'tkazib yuborilgan slot jurnalda ko'rinadi **va alert yuboradi**» deydi — alert jo'natuvchisi esa `04-08` da tug'iladi. Ikkinchidan, SDK yozgan `Complete` qiymati `02-22` da uch qiymat bilan chegaralangan lug'atda (`Done`/`Pending`/`Blocked`) YO'Q.

⚠ `node scripts/check-requirements-sync.mjs` **bitta nomuvofiqlik** beradi va u MEROS: `CAM-02` ro'yxatda `[x]`, jadvalda esa `Blocked (...)`. U 3-fazadan qolgan va bu rejada tegilmadi.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan 8 fayl + o'zgartirilgan 9 fayl** — hammasi diskda tekshirildi (`MISSING: 0`).
- **Oltala commit `git log` da tasdiqlandi:** `07ae0d5`, `96ab8a9`, `cbccd49`, `431608f`, `29e4d54`, `d8b71e5` — bazasi `385a6d5`.
- **Reja artefakt shartlari o'lchandi:** `frame_source.py` **666** qator (talab ≥ 200) va `capture_method` ni o'z ichiga oladi; `capture.py` **1 142** qator (talab ≥ 300) va `_system_transaction` ni o'z ichiga oladi; `worker.py` da `TaskiqScheduler` bor.
- **`key_links` uchalasi ham o'lchandi:** `capture.py` → `capture_repo` (`claim_due` va qolgan to'rttasi CHAQIRILADI), `worker.py` → `capture.py` (`capture.tick` qobig'i `str` → `UUID` konversiyasi bilan), `frame_source.py` → `go2rtc.py` (`ensure_stream` CHAQIRILADI).
- **Ishchi daraxt toza:** `git status --short` da faqat topshiriqda «meniki emas» deb belgilangan uchta fayl qoldi; `.env` va `ops/seaweedfs/s3.json` gitignore ostida.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
