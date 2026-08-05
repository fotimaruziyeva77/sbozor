---
phase: 04-snapshot-pipeline
verified: 2026-08-05T10:52:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "SC#5 — Kamera offline bo'lsa, slot o'tkazib yuborilsa yoki backup xato bersa — platforma adminiga Telegram-alert keladi va xato Sentry'da ko'rinadi (FOUND-06)"
  gaps_remaining: []
  regressions: []
  corrections_to_previous_report:
    - claim: "`pytest -q` → ~1925 test"
      actual: "1889 passed, 5 deselected — o'lchandi. `~1925` HECH QACHON o'lchanmagan; aniq o'lchovlar 1879 -> 1886 -> 1889"
    - claim: "`node --test scripts/*.test.mjs` → 115 passed"
      actual: "Repo ILDIZIDAN bu buyruq JIMGINA hech nima qaytaradi — `*.test.mjs` fayllari `frontend/scripts/` da. To'g'ri shakli `cd frontend && node --test scripts/*.test.mjs` → 115 pass. ⚠ `npm run gate` ning O'ZI to'g'ri ishlaydi (`npm --prefix frontend test`), xato FAQAT hujjatdagi buyruqda edi"
    - claim: "`node scripts/check-validation-signoff.mjs` — argumentsiz ishlatilishi nazarda tutilgan"
      actual: "`DEFAULT_FILE` hamon 2-fazaga qadalgan (`scripts/check-validation-signoff.mjs:54-61`), ya'ni argumentsiz chaqiruv 4-faza faylini QAMRAMAYDI. Ochiq band, egasi 5-fazaning validatsiya rejasi"
deferred:
  - truth: "Tashqi dead-man's switch (`/internal/self-check` ni tashqaridan so'rash) KOD bilan qurilmagan"
    addressed_in: "D-21 (fazaning O'Z qarori) + Phase 8"
    evidence: "D-21: «Tashqi dead-man's switch v1 da kod yozilmaydi — `ops/docs/monitoring.md` ga bitta URL sozlash yo'riqnomasi va ops bandi». `ops/docs/monitoring.md` §5 mavjud; band `04-HUMAN-UAT.md` #5, egasi Ops"
  - truth: "Zaxira (`backup`) komponentining yurak urishi hech qachon yozilmagan — `/internal/self-check` uni `never_seen` da ko'rsatadi"
    addressed_in: "Phase 8"
    evidence: "Phase 8 mezoni: «backup mashqi, go-live»; FOUND-07 o'sha fazada. `self_check.py::EXPECTED_COMPONENTS` (108-113) `backup` ni ATAYIN ro'yxatda saqlaydi; `ok` FAQAT `stale` bo'yicha hisoblanadi (170-172)"
open_items:
  - item: "`npm run gate` davomiyligi hujjatlashtirilgan 900 s byudjetidan yuqori"
    severity: open_item_not_gap
    evidence: "04-14: 1009 s va 1174 s. TEKSHIRUVCHINING MUSTAQIL O'LCHOVI shu xostda sababni TASDIQLADI — pastdagi «Davomiylik» bo'limi"
    owner: "Phase 5 validation plan"
    trigger: "TINCH xostda, seans boshida, kamida uch o'lchov"
  - item: "`scripts/check-validation-signoff.mjs::DEFAULT_FILE` 2-fazaga qadalgan"
    severity: open_item_not_gap
    evidence: "`scripts/check-validation-signoff.mjs:54-61` — o'qildi va tasdiqlandi"
    owner: "Phase 5 validation plan"
    trigger: "Fazaning validatsiya rejasi shu faylga tegganda"
human_verification:
  - test: "Sifat chegaralarini REAL Karmana kadrida sozlash (04-HUMAN-UAT #1)"
    expected: "06:00 va 18:00 kadrlarida `dark`/`blank` verdiktlari qonuniy kadrni rad etmaydi; chegaralar SQL bilan sozlanadi"
    why_human: "Chegaralar LOW confidence — real kadr yo'q. Sintetik JPEG MEXANIZMNI isbotlaydi, QIYMATNI emas. Egasi: nazoratchi + ijrochi; tetigi: Phase 0 kadrlari"
  - test: "90 kunlik saqlash siyosatining KALENDAR bo'yicha ishlashi (04-HUMAN-UAT #2)"
    expected: "90 kundan keyin birinchi `full -> compressed` to'lqini; 455 kundan keyin birinchi `purged`"
    why_human: "Vaqtni kutib bo'lmaydi. ⚠ TASDIQLANDI: bu band OCHIQ qoldi va «o'lchandi» deb KO'RSATILMADI. Egasi: Ops; tetigi: go-live + 90 kun"
  - test: "Tiklash mashqi (restore drill) (04-HUMAN-UAT #3)"
    expected: "Zaxiradan to'liq tiklash hujjatlashtirilgan holda bajariladi"
    why_human: "Real ombor, real ma'lumot va toza server talab qiladi. Egasi: Ops; tetigi: go-live'dan oldin, Phase 8 (FOUND-07)"
  - test: "Telegram alertining HAQIQATAN yetib borishi (04-HUMAN-UAT #4)"
    expected: "Platforma admini Telegram'da guruhlangan xabarni oladi; xabarda rasm, havola va obyekt kaliti yo'q"
    why_human: "Token va chat ID CI'da yo'q. Egasi: Ops. ⚠ FOUND-06 ning `Done` holati shu bandga bog'liq"
  - test: "Tashqi dead-man's switch — `/internal/self-check` ni tashqaridan so'rash (04-HUMAN-UAT #5)"
    expected: "healthchecks.io/UptimeRobot 503 holatida ogohlantirish yuboradi"
    why_human: "Quti tashqarisidagi xizmat, D-21 bo'yicha kod yozilmaydi. Egasi: Ops"
  - test: "Real NVR'da bir vaqtdagi sessiya chegarasining kadr olishga ta'siri (04-HUMAN-UAT #6)"
    expected: "25 kamera ketma-ket olinganda NVR sessiya chegarasiga urilmaydi yoki `capture_stream_limit` bilan kechiktiriladi"
    why_human: "Simulyator sessiya chegarasini UMUMAN modellamaydi. Egasi: Ops"
  - test: "Planer istisnosi HAQIQIY Sentry loyihasida ko'rinadi (04-HUMAN-UAT #7 — YANGI)"
    expected: "Sentry loyihasining Issues ro'yxatida `ObservedScheduler.on_ready` dan kelgan hodisa paydo bo'ladi; ichida `task_name` va `schedule_id` bor, shaxsiy ma'lumot YO'Q"
    why_human: "CI'da DSN yo'q. Darvoza `init()` chaqirilishini va `capture_exception` ga borishni o'lchaydi — hodisaning Sentry SERVERIGA yetib borishini emas. Egasi: Ops; tetigi: haqiqiy `SENTRY_DSN` yozilgan kun"
---

# Phase 4: Snapshot pipeline — Qayta tekshiruv hisoboti

**Faza maqsadi:** Har kuni rejadagi kadrlar avtomatik olinadi, sifat tekshiruvidan o'tadi, ishonchli arxivlanadi va uzilish jim qolmaydi
**Tekshirildi:** 2026-08-05T10:52:00Z
**Holat:** `human_needed`
**Qayta tekshiruv:** Ha — `04-13`/`04-14` bo'shliq yopish to'lqinidan keyin
**Oldingi holat:** `gaps_found`, 4/5

---

## Xulosa

**Bo'shliq HAQIQATAN yopilgan va u manba o'qish bilan emas, HAQIQIY
JARAYONDA o'lchandi.** Oldingi tekshiruv `sentry active: False` deb
o'lchagan zondni men aynan o'sha yo'l bilan qayta yugurtirdim va u endi
`SENTRY_ACTIVE=True` beradi; nazorat yugurishi (DSN'siz) `False` beradi,
ya'ni zond bo'sh emas.

Bundan MUHIMROQ: bo'shliqning ikkinchi yarmi — yutilgan istisno — ham
mustaqil o'lchandi. `init()` ishlab turgan holda ham istisno tashlab
yuborilsa hech nima yopilmagan bo'lardi. Men `on_ready` ni yiqiladigan
manba bilan chaqirib, Sentry ning HAQIQIY transportini kuzatdim: bitta
envelope chiqdi, ichida `RuntimeError`, va istisno qayta ko'tarildi
(taskiq semantikasi o'zgarmagan).

Darvozaning HOSILA ekani ham tasdiqlandi — va men uni `04-13` sinamagan
ikkita yo'ldan ham sinadim. Uchala holatda ham darvoza **yiqildi**,
o'tkazib yubormadi.

⚠ **Oldingi hisobotning uchta soni/yo'li noto'g'ri edi va uchalasi ham
tuzatildi** (frontmatter `corrections_to_previous_report`). `04-14` ni
bu masalada haq deb topdim va sonlarni O'ZIM qayta o'lchadim.

---

## Maqsad bajarilishi

### Kuzatiladigan haqiqatlar (ROADMAP SC#1–SC#5)

| # | Haqiqat | Holat | Dalil |
|---|---|---|---|
| 1 | Admin jadvalni mavsumiy profil bilan sozlaydi va **ertasi kuni** aynan o'sha slotlarda kadrlar paydo bo'ladi | ✓ VERIFIED | `test_sc1_...` o'tdi (7/7). Regressiya yo'q: `DEFAULT_SNAPSHOT_SLOTS` joyida, `EXCLUDE USING gist` joyida, muzlatish slot o'qida strukturaviy |
| 2 | Uzilish/takror ishga tushishda dublikat yo'q, urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda **ochiq ko'rinadi** | ✓ VERIFIED | `test_sc2_...` o'tdi. `SKIP LOCKED` × 7, `ON CONFLICT` × 8 `capture_repo.py` da; `missed` — `RETURNING` hosilasi |
| 3 | Qorong'i/buzuq/bo'sh kadr avtomatik belgilanadi, `light_mode` bilan saqlanadi va hisob-kitobga **hech qachon** ta'sir qilmaydi | ✓ VERIFIED | `test_sc3_...` o'tdi. `quality.py:457` ikki shartli (D-14); `uq_snapshots_billable_anchor` + `GENERATED ALWAYS ... STORED` (`0014:513`) o'z joyida |
| 4 | Kadrlar S3-mos omborda topiladi; 90 kun to'liq, keyin siqilgan siyosat **amalda ishlaydi** | ✓ VERIFIED (mexanizm) | `test_sc4_...` o'tdi — haqiqiy SeaweedFS konteynerida. `retention_full_days=90` / `retention_compressed_days=365` (`settings.py:242-243`). Kalendar kechishi — `04-HUMAN-UAT.md` #2 (kutib bo'lmaydi) |
| 5 | Kamera offline / slot o'tkazib yuborilgan / backup xato → Telegram-alert **va xato Sentry'da ko'rinadi** | ✓ **VERIFIED** (oldin ⚠ PARTIAL) | **Har ikkala yarmi ham HAQIQIY JARAYONDA o'lchandi — quyida** |

**Ball: 5/5 haqiqat tasdiqlandi** (oldingi: 4/5)

---

## ✅ Bo'shliqning yopilishi — O'LCHANGAN, manbadan o'qilmagan

### 1-yarmi: `init_sentry()` planer jarayonida HAQIQATAN bajariladi

Oldingi tekshiruv aynan shu zondni yugurtirib `sentry active: False`
olgan edi. Men uni qayta yugurtirdim (`tests` konteyneri, taskiq CLI'sining
`cli/scheduler/run.py:392` qadamini takrorlab):

```
registered handlers:
    TaskiqEvents.CLIENT_STARTUP ['_install_client_observability']   <- OLDIN YO'Q EDI
    TaskiqEvents.WORKER_STARTUP ['_open_worker_resources']
    TaskiqEvents.WORKER_SHUTDOWN ['_close_worker_resources']
is_worker_process = False
after CLI sets is_scheduler_process -> is_worker_process = False
scheduler type: ObservedScheduler
sentry BEFORE startup: False
{"queue": "sbozor:jobs", "sentry": true, "event": "scheduler_started", ...}
SENTRY_ACTIVE=True                                                  <- OLDIN False
```

**Nazorat yugurishi** (aynan o'sha zond, `SENTRY_DSN=`):

```
{"queue": "sbozor:jobs", "sentry": false, "event": "scheduler_started", ...}
SENTRY_ACTIVE=False
```

Ya'ni zond doimiy `True` qaytarmaydi — u haqiqatan holat o'lchaydi.

### 2-yarmi: yutilgan `on_ready` istisnosi — MUSTAQIL o'lchandi

Bu yarmi alohida o'lchanishi SHART edi: `init()` ishlab turgan holda ham
istisno tashlab yuborilsa bo'shliq yopilmagan bo'lardi. Men planerni
haqiqiy jarayonda ko'tarib, `sentry_sdk` ning HAQIQIY transportini
kuzatdim va yiqiladigan `ScheduleSource` berdim:

```
{"task_name": "capture.tick", "schedule_id": "2daa8379...",
 "source": "BoomSource", "event": "scheduler_send_failed", "level": "error",
 "exception": "Traceback ... RuntimeError: valkey unreachable -- verifier probe"}
RE_RAISED=True (RuntimeError('valkey unreachable -- verifier probe'))
ENVELOPES=1
  sentry event -> RuntimeError: valkey unreachable -- verifier probe
```

Uch da'vo birdan tasdiqlandi: (a) jurnalga `scheduler_send_failed` chiqdi,
(b) Sentry'ga HAQIQIY envelope ketdi, (c) istisno QAYTA KO'TARILDI —
taskiq semantikasi o'zgarmagan.

`sentry_sdk` ning yagona uyi ham saqlangan: butun `services/` bo'ylab
import faqat `app/observability.py:56-57` da (T-04-98 mitigatsiyasi tirik).

---

## 🔬 Darvoza HOSILAmi? — `04-13` sinamagan yo'llardan ham sinaldi

Topshiriq aynan shuni talab qildi: to'rtinchi `SENTRY_DSN` servisini
qo'shib, darvoza uni SEZISHINI va noma'lum `command` shakli **o'tkazib
yuborilmasdan YIQILISHINI** tasdiqlash. `compose.yaml` ni zaxiraladim,
uchta sabotaj qildim va `cp` bilan tikladim.

| # | Sabotaj | Natija | Kim sinagan |
|---|---|---|---|
| A | 4-servis, `SENTRY_DSN` bor, `command: ["python","-m","app.something"]` — `module:attr` YO'Q | ✗ **FAILED** — «`verifier-probe-a` servisi `SENTRY_DSN` ni oladi, lekin darvoza uning kirish nuqtasini `command` dan chiqara olmadi: 0 ta token» | `04-13` (S2) + men |
| B | 4-servis, `command` da `app.worker:JOBS_QUEUE` — QONUNIY token, lekin obyekt turi **noma'lum** (`str`) | ✗ **FAILED** — «obyektning turi (`str`) darvozaga noma'lum ... Yangi tur uchun (c) bosqichiga shox qo'shing» | **FAQAT men — `04-13` bu shoxni sinamagan** |
| C | 4-servis, `command` da `sim.main:app` — HAQIQIY `FastAPI`, lekin `init_sentry` YO'Q | ✗ **FAILED** — yig'ilgan-manba QUYI CHEGARASI ishladi: «`lifespan_context` zanjiridan birorta manba o'qilmadi» | **FAQAT men** |

**Xulosa: darvoza uchala «bilmadim» yo'lida ham YIQILADI, o'tkazib
yubormaydi.** Servis NOMLARI test kodida umuman yo'q — faqat `SENTRY_DSN`
predikati va quyi chegaralar (`MIN_COMPOSE_SERVICES=8`,
`MIN_SENTRY_SERVICES=3`, `MIN_ENV_KEYS=40`). Bu haqiqatan HOSILA, sanoq emas.

### Fazaning O'Z nosozlik shakli qaytarilsa nima bo'ladi (S1)

Men `@broker.on_event(TaskiqEvents.CLIENT_STARTUP)` **dekoratorini** olib
tashladim (funksiyani qoldirib) — ya'ni aynan oldingi tekshiruv topgan
holatni qayta yaratdim:

```
FAILED tests/unit/test_sentry_processes.py::test_every_sentry_process_installs_sentry
FAILED tests/unit/test_scheduler_observability.py::test_client_startup_hook_installs_sentry
FAILED tests/integration/test_phase4_criteria.py::test_sc5_absence_reaches_telegram_and_sentry
3 failed, 29 passed
```

**Uch mustaqil qulf birdan qizardi** — hosila darvoza, unit ilmoq testi va
HAQIQIY jarayon zondi (`- True + False`). `04-13` ning da'vosi aynan
takrorlandi. Muhimi shu: eski (sanoqli) darvoza bu sabotajda **butunlay
yashil** qolardi.

**S3** (`capture_exception(...)` ni `on_ready` dan olib tashlash) → AYNAN
BITTA test qizardi (`test_on_ready_reports_the_swallowed_exception`,
`assert [] == [RuntimeError(...)]`). «Sentry o'rnatildimi?» va «istisno
Sentry'ga bordimi?» haqiqatan ikki boshqa da'vo.

Har sabotajdan keyin fayl `cp` bilan tiklandi; `git diff --exit-code` bo'sh.

---

## 🔬 Lifespan yuruvchisi — chuqurlik chegarasi va quyi chegara

`04-13` «depth-8 va depth-40 ikkalasi ham topa olmadi» degan edi. Men buni
o'zim o'lchadim (`tests` konteyneri, `app.main` import qilingan holda):

| Chuqurlik | Yig'ilgan manba | `init_sentry(` topildimi |
|---|---|---|
| `getsource(lifespan_context)` to'g'ridan-to'g'ri | 1 | **YO'Q** |
| `__wrapped__` orqali | 1 | **YO'Q** |
| 8 | 14 | **YO'Q** |
| 40 | 62 | **YO'Q** |
| **chegarasiz** | **69** | **BOR** |

**`04-13` ning da'vosi harfma-harf takrorlandi.** Yetkazib berilgan
yuruvchida (`test_sentry_processes.py:329-350`) chuqurlik chegarasi
**YO'Q** — faqat `seen: set[int]` takrorlanishni to'xtatadi — va
yig'ilgan-manba QUYI CHEGARASI bor (`assert sources`, satr 379). Sabotaj C
aynan shu chegarani ishlatib qizardi, ya'ni u dekorativ emas.

---

## Talab qilingan artefaktlar (o'zgarganlari)

| Artefakt | Kutilgan | Holat | Tafsilot |
|---|---|---|---|
| `services/core-api/app/worker.py` | `CLIENT_STARTUP` ilmog'i + `ObservedScheduler` | ✓ **VERIFIED** (oldin ⚠ PARTIAL) | 787 qator (oldin 628). Ilmoq `:462-489`, `ObservedScheduler` `:374-424`, `scheduler` `:427`. `_open_worker_resources` TEGILMAGAN |
| `services/core-api/app/observability.py` | `sentry_installed`, `capture_exception` | ✓ VERIFIED | 278 qator; `__all__` da ikkalasi ham. `sentry_sdk` importi butun `services/` da FAQAT shu yerda |
| `tests/unit/test_sentry_processes.py` | `compose.yaml` dan hosila darvoza | ✓ VERIFIED | 437 qator (min 150); uch sabotaj bilan sinaldi |
| `tests/unit/test_scheduler_observability.py` | ilmoq, env-nom pariteti, istisno e'loni | ✓ VERIFIED | 286 qator (min 100); S3 aynan uni qizartirdi |
| `tests/integration/test_phase4_criteria.py` | HAQIQIY jarayon zondi | ✓ VERIFIED | 1478 qator (oldin 1330); `subprocess` zondi + MAJBURIY nazorat yugurishi (`:1359-1369`). **7/7 o'tdi** |
| `tests/unit/test_sentry_scrub.py` | sanoqli darvoza olib tashlangan | ✓ VERIFIED | 329 qator; `test_sentry_init_wires_both_hooks` SAQLANGAN |
| `.env.example` | `s3.json.example` bilan juftlik | ✓ VERIFIED | `:122-123` = `NAMUNA-ALMASHTIRING-access/secret`, `s3.json.example` bilan AYNAN teng |
| `tests/unit/test_storage_config.py` | juftlik darvozasi | ✓ VERIFIED | 473 qator; TENGLIK da'vosi (yo'qlik emas) |
| `.planning/.../04-HUMAN-UAT.md` | 7 band, ega + tetik | ✓ VERIFIED | 7 `Egasi:` / 7 `Tetigi:` / 7 `[pending]` — sanaldi |
| `.planning/.../04-VALIDATION.md` | 42 qator, 7 inson bandi | ✓ VERIFIED | Skript exit 0; bayroq IKKI yo'nalishda sinaldi |

---

## Kalit bog'lanishlar (o'zgarganlari)

| From | To | Via | Holat | Tafsilot |
|---|---|---|---|---|
| `worker.py` (`scheduler` jarayoni) | `observability.py::init_sentry` | `CLIENT_STARTUP` ilmog'i | ✓ **WIRED** (oldin ✗ NOT_WIRED) | Reyestrda `['_install_client_observability']`; jarayonda `SENTRY_ACTIVE=True` |
| `ObservedScheduler.on_ready` | `observability.py::capture_exception` | `try/except -> log + capture -> raise` | ✓ WIRED | HAQIQIY transportda 1 envelope; qayta ko'tarilgan |
| `compose.yaml` (`SENTRY_DSN` servisi) | `test_sentry_processes.py` | `command` dan `module:attr` -> import -> reyestr | ✓ WIRED | 3 sabotaj bilan tasdiqlandi |
| `.env.example` | `ops/seaweedfs/s3.json.example` | `test_storage_config.py` tenglik darvozasi | ✓ WIRED | `docker compose --env-file .env.example config` → 3 servis, bo'sh emas |

---

## Xulqiy spot-check — HAMMASINI O'ZIM YUGURTIRDIM

| Xulq | Buyruq | Natija | Holat |
|---|---|---|---|
| Planer Sentry zondi (DSN bilan) | konteynerda taskiq CLI qadamlari | **`SENTRY_ACTIVE=True`** | ✓ PASS |
| Planer Sentry zondi (nazorat, DSN'siz) | o'sha zond | **`SENTRY_ACTIVE=False`** | ✓ PASS |
| `on_ready` istisnosi → HAQIQIY Sentry transporti | `BoomSource` + transport ilmog'i | **1 envelope + `RE_RAISED=True`** | ✓ PASS |
| Beshala mezon | `pytest tests/integration/test_phase4_criteria.py` | **7 passed** | ✓ PASS |
| Sentry darvozalari | `pytest test_sentry_processes.py test_scheduler_observability.py test_sentry_scrub.py` | **25 passed** | ✓ PASS |
| To'liq pytest | `pytest` (sim ko'tarilgan) | **1889 passed, 5 deselected**, exit 0 | ✓ PASS |
| Tenant izolyatsiyasi | `pytest tests/tenancy` | **472 passed** | ✓ PASS |
| Frontend | `npx vitest run` | **28 fayl / 338 test** | ✓ PASS |
| Skript darvozalari | `cd frontend && node --test scripts/*.test.mjs` | **115 tests · 115 pass** | ✓ PASS |
| i18n pariteti | `npm run i18n:check` | **777 kalit × 3 til, drift yo'q** | ✓ PASS |
| Talab ↔ Traceability | `node scripts/check-requirements-sync.mjs` | exit 0 — **49 talab MOS (Done 16 · Pending 32 · Blocked 1)** | ✓ PASS |
| `nyquist_compliant` (yo'nalish 1) | `check-validation-signoff.mjs <04-VALIDATION.md>` | exit 0 — 42 qator · **7** inson bandi | ✓ PASS |
| `nyquist_compliant` (yo'nalish 2 — **flip**) | bayroqni `false` ga o'zgartirib qayta | **exit 1** — «HISOB-KITOBGA MOS EMAS (hisoblangani: true)» | ✓ PASS — bayroq HISOBLANADI |
| `.env.example` juftligi | `docker compose --env-file .env.example config` | `core-api`/`worker`/`scheduler` — uchalasida ham bo'sh EMAS | ✓ PASS |
| **Sabotaj S1** | `CLIENT_STARTUP` dekoratori olib tashlandi | **3 failed** (darvoza + unit + zond) | ✓ RED |
| **Sabotaj S3** | `capture_exception` olib tashlandi | **1 failed** | ✓ RED |
| **Sabotaj A/B/C** | 4-servis, uch xil shakl | **uchalasi ham FAILED** | ✓ RED |
| Sabotaj nazorati | `git diff --exit-code` | **bo'sh** | ✓ CLEAN |

---

## ⏱ Davomiylik — `04-14` ning tahlili TO'G'RI, va men uni MUSTAQIL TASDIQLADIM

`04-14` `npm run gate` ni ikki marta yugurtirib **1009 s** va **1174 s**
(chegara **900 s**) olgan, sababni xost tomonidagi progressiv
degradatsiyaga bog'lagan, chegarani ko'tarmagan va «bu seansda davomiylik
regressiyasi yo'q deb ayta olmayman» degan. Topshiriq bu mulohazani
baholashni so'radi.

### Attributsiya ASOSLI — va men uni O'Z o'lchovlarim bilan tasdiqladim

Men `npm run gate` ni qayta yugurtirmadim (17–20 daqiqa), lekin **uchta
O'ZGARMAGAN ish hajmini** o'lchadim va uchalasi ham bir yo'nalishda chiqdi:

| Ish hajmi | Sog'lom baza | Mening o'lchovim | Nisbat |
|---|---|---|---|
| To'liq `pytest` | **538–557 s** (`gate-timings.tsv`, 3 yugurish) | **1012.82 s** | **1.85×** |
| `pytest tests/tenancy` | **248–249 s** (o'sha manba) | **406.38 s** | **1.64×** |
| `vitest` `environment` (jsdom) | 225.94 s → 282.90 s (`04-14`) | **353.72 s** | monoton o'sish davom etyapti |

Uchala holatda ham **kod men uchun ham, bazaviy o'lchov uchun ham AYNAN
bir xil** (`git diff` bo'sh). Ya'ni sekinlashuv kodning funksiyasi emas.

**Men qo'shadigan yangi dalil — sabab endi taxmin emas, KO'RINADIGAN:**
xost ayni paytda **ikkinchi to'liq Docker stekini** yuritmoqda —
`parnikkpi-*` oilasidan 7 konteyner (`backend`, `frontend`, `celery_worker`,
`bot`, `db`, `redis`, `migrate`), hammasi «Up 2 days». Bu SBOZOR ning
o'z 6 konteyneri ustiga qo'shiladi. `04-14` degradatsiyani o'lchagan,
lekin manbasini nomlamagan edi; u shu yerda nomlanadi.

### Xulosam: chegarani 900 s da qoldirish TO'G'RI qaror

1. **Ko'tarish noto'g'ri bo'lardi.** Ishonchsizligi ENDIGINA isbotlangan
   o'lchov vositasi bilan chegarani qayta yozish xost shovqinini
   shartnomaga abadiy singdirardi. `04-12` ning olti o'lchovli qarori
   bitta ifloslangan seansdan kuchliroq.
2. **«Davomiylik regressiyasi yo'q» demaslik — halol pozitsiya.** `04-14`
   yashil yozishi mumkin edi (`exit 0` ikki marta), lekin yozmadi.
3. **Bu BO'SHLIQ EMAS, OCHIQ BAND.** Uch sabab: (a) faza maqsadi
   jumlasida davomiylik bandi umuman yo'q; (b) `npm run gate` da
   PROGRAMMATIK taymer yo'q — men qidirdim, `package.json` va
   `scripts/*.mjs` da 900 s chegarasini majburlaydigan kod topilmadi,
   ya'ni chegara hujjatlashtirilgan BYUDJET, darvoza emas, va uni oshish
   soxta yashil BERMAYDI; (c) band `04-VALIDATION.md:359` da `- [ ]`
   bo'lib, ega va tetik bilan yozilgan.

⚠ **Ochiq aytiladi:** shu sababli **«bu fazadan davomiylik regressiyasi
yo'q» degan sertifikat BERILMAYDI.** Byudjetni qayta o'lchash tinch xostda
bajarilishi kerak.

---

## Qaror reyestri D-01…D-23 — regressiya tekshiruvi

Bo'shliq yopish to'lqini faqat kuzatuv qatlamiga, namuna fayllarga va
hujjatlarga tegdi (`git diff fc9877e..HEAD` — 11 fayl, `services/` dan
faqat `worker.py` va `observability.py`). Struktura markerlarini qayta
o'lchadim:

| Qaror | Marker | Natija |
|---|---|---|
| D-01 | `DEFAULT_SNAPSHOT_SLOTS` | ✓ mavjud |
| D-02/03 | `LabelScheduleSource` (kod), `SKIP LOCKED` × 7, `ON CONFLICT` × 8 | ✓ `RedisScheduleSource` faqat IZOHDA (rad etish sababi) |
| D-04 | `_group_by_nvr` | ✓ |
| D-07 | `_claims_rtsp_session` | ✓ |
| D-08 | `capture_global_concurrency ... = 1` (`settings.py:199`) | ✓ |
| D-11 | `frame_source.py` da `remove_stream` faqat IZOHDA («juftisiz») | ✓ |
| D-13 | `quality.py` da `cv2` — **0** | ✓ |
| D-14 | `quality.py:457` — `mean < ... and stddev < ...` | ✓ ikki shartli |
| D-16 | `uq_snapshots_billable_anchor` + `GENERATED ALWAYS ... STORED` | ✓ |
| D-17 | `aiobotocore` bor; `aioboto3`/`minio` faqat TAQIQ izohida | ✓ |
| D-18 | `retention_full_days=90`, `retention_compressed_days=365` | ✓ |
| D-19 | `sendPhoto` butun `services/` da — **0**; `TELEGRAM_SEND_METHOD="sendMessage"` | ✓ |
| D-21 | `ops/docs/monitoring.md` §5 + `04-HUMAN-UAT.md` #5 | ✓ kod emas, hujjat |
| D-22 | `NEVER_SUPPRESSED_ALERT_KEYS` | ✓ |
| D-23 | `0014` strukturaviy shaklda | ✓ |

**23/23 qaror hurmat qilingan — regressiya yo'q.**

---

## Talablar qamrovi

| Talab | Ta'rif | Holat | Dalil |
|---|---|---|---|
| CAM-04 | Snapshot jadvali, mavsumiy profil | ✓ SATISFIED | `test_sc1_...`; `EXCLUDE USING gist` |
| CAM-05 | Idempotent + retry; missed jurnalda + alert | ✓ SATISFIED | `test_sc2_...`; `SKIP LOCKED` + lease |
| CAM-06 | Sifat filtri; yaroqsiz kadr billing'ga ta'sir qilmaydi | ✓ SATISFIED | `test_sc3_...`; DB darajasidagi rad etish. ⚠ Chegara QIYMATI LOW confidence — UAT #1 |
| CAM-07 | S3 tartib + 90/455 kun siyosati | ✓ SATISFIED | `test_sc4_...` haqiqiy SeaweedFS'da. ⚠ Kalendar — UAT #2 |
| FOUND-06 | Telegram-alert + xatolar Sentry'da | ✓ **SATISFIED** (oldin ⚠ PARTIAL) | Telegram yarmi o'lchangan; **Sentry yarmi endi uchala jarayonda** — dalil `REQUIREMENTS.md:272` da SANOQDAN HOSILAGA o'tkazilgan. ⚠ Yetib borish — UAT #4/#7 |

**Yetim talab yo'q.** Holat lug'ati to'g'ri: `Done`/`Pending`/`Blocked`,
`Complete` YO'Q. **CAM-02 `Blocked` bo'lib QOLDI** (3-fazadan; egasi Ops,
tetigi VPS deploy'i) — tekshirildi.

---

## Anti-naqshlar

| Fayl | Naqsh | Jiddiylik | Ta'siri |
|---|---|---|---|
| — | `TBD`/`FIXME`/`XXX` 11 o'zgargan faylda | — | **0 natija — DEBT-MARKER DARVOZASI TOZA** |
| `tests/unit/test_snapshot_settings.py` | `_ENV_EXAMPLE_TODO` | ℹ️ Info | Nomlangan REYESTR konstantasi, qarz belgisi emas: `test_registered_gaps_carry_a_reason` har yozuvdan >40 belgili SABAB talab qiladi va `test_every_settings_field_is_documented_or_registered` ikki yo'nalishni ham qulflaydi |
| `frontend/src/components/snapshots/` | qattiq yozilgan bo'sh prop | — | **0 natija** |
| `.env.example` | bo'sh `S3_ACCESS_KEY`/`S3_SECRET_KEY` | ✅ **YOPILDI** | Oldingi hisobotning yagona ⚠️ Warning bandi — `04-14`/T1 da tuzatildi va TENGLIK darvozasi bilan qulflandi |

---

## Kechiktirilgan bandlar

| # | Band | Qayerda hal bo'ladi | Dalil |
|---|---|---|---|
| 1 | Tashqi dead-man's switch KOD bilan qurilmagan | D-21 (faza qarori) + Phase 8 | `ops/docs/monitoring.md` §5 mavjud; UAT #5 |
| 2 | `backup` yurak urishi hech qachon yozilmagan | Phase 8 (FOUND-07) | `EXPECTED_COMPONENTS:108-113` uni ATAYIN saqlaydi; `ok` FAQAT `stale` bo'yicha (`:170-172`) |

`deferred-items.md`: **#1 yopilgan** (`_anchor_today`, `04-12`),
**#2 yopilgan** (`04-14`/T1 — juftlik + darvoza), **#3 yopilgan**
(`04-14`/T1 — README ogohlantirishi). Uchala band ham reyestrda
SAQLANGAN, o'chirilmagan.

---

## Ochiq bandlar (bo'shliq EMAS)

| # | Band | Nega bo'shliq emas | Egasi / tetigi |
|---|---|---|---|
| 1 | `npm run gate` > 900 s | Maqsad jumlasida davomiylik bandi yo'q; chegara programmatik emas, hujjatlashtirilgan byudjet; soxta yashil bermaydi | Phase 5 validatsiya rejasi / tinch xostda 3 o'lchov |
| 2 | `check-validation-signoff.mjs::DEFAULT_FILE` 2-fazaga qadalgan (`:54-61`) | Skript to'g'ri yo'l bilan ishlaydi va u shu tarzda chaqirilgan; noqulaylik, nosozlik emas | Phase 5 validatsiya rejasi |

---

## Inson tekshiruvi talab qilinadigan bandlar

Yettita band — hammasi `04-HUMAN-UAT.md` da **ega va tetik bilan**.
Roadmap'ning 2026-08-01 self-service direktivasi bo'yicha ular fazani
**bloklamaydi**, lekin ular bajarilmaguncha tegishli da'volar BERILMAGAN
bo'lib qoladi. To'liq ro'yxat frontmatter'da.

⚠ **#2 (90 kunlik saqlash kalendari) TEKSHIRILDI VA U OCHIQ:**
`result: [pending]`, matni «vaqtni kutib bo'lmaydi» deb boshlanadi va
mexanizm dalili siyosat dalili sifatida KO'RSATILMAGAN. `04-14` unga
tegmagan — bu to'g'ri qaror.

⚠ **#7 YANGI** (`04-14`): planer istisnosining HAQIQIY Sentry loyihasiga
yetib borishi. Bu band darvozaning chegarasini halol nomlaydi — men
o'lchagan narsa `capture_exception` gacha; Sentry SERVERIGACHA emas.

---

## Simulyator chegarasi — ochiq gap

Bu fazaning HAMMA dalili simulyator va sintetik kadrlar ustida
o'lchangan. Ombor HAQIQIY SeaweedFS, NVR HAQIQIY `nvr-sim` (Digest auth
bilan), baza HAQIQIY Postgres — lekin real Karmana uskunasi, real
kalendar vaqt va real tashqi xizmat (Telegram, Sentry) YO'Q.

Aniq aytilishi kerak bo'lgan uch narsa:

1. **90 kunlik saqlash siyosati kutib o'lchanmagan** va uni kutmasdan
   o'lchab bo'lmaydi — mexanizm isbotlangan, kalendar xulqi emas.
2. **Telegram xabarining va Sentry hodisasining YETIB BORISHI
   isbotlanmagan** — HTTP kontrakti va `capture_exception` gacha
   bo'lgan zanjir isbotlangan.
3. **Real NVR sessiya chegarasi umuman modellanmagan.**

Bularning bittasi ham bo'shliq emas — ularning har biri ROADMAP
dizayni bo'yicha inson/uskuna/vaqt talab qiladi va har biri ega hamda
tetik bilan yozilgan. Lekin ularni «o'lchandi» deb o'qish xato bo'lardi.

---

## Bo'shliqlar xulosasi

**Bo'shliq yo'q.** Oldingi tekshiruvning yagona bo'shlig'i — SC#5 ning
Sentry yarmi `scheduler` jarayonida — yopilgan va yopilishi **uch mustaqil
qatlamda** o'lchangan (hosila darvoza · unit ilmoq testi · haqiqiy jarayon
zondi). Men uchalasini ham SABOTAJ bilan sinadim va uchalasi ham qizardi.

`04-13` ning eng qimmatli qarori — ro'yxatga uchinchi nom qo'shmasdan
ro'yxatning O'ZINI olib tashlash — o'zini oqladi: men qo'shgan
to'rtinchi servis darvozani uchta boshqa yo'ldan yiqitdi, ya'ni n+1
nosozlik takrorlanmaydi.

`04-14` ning eng qimmatli hissasi — o'z o'lchovining ishonchsizligini
E'LON QILISHI. Men uni mustaqil tasdiqladim (pytest 1.85×, tenancy
1.64×, vitest jsdom monoton) va sababni nomladim (xostda ikkinchi to'liq
Docker steki). Chegarani ko'tarmaslik to'g'ri qaror edi.

**Faza `passed` emas, `human_needed`:** beshala haqiqat ham tasdiqlangan
va bloklovchi yo'q, lekin yettita inson bandi ochiq turibdi va ular
fazaning eng qimmat da'volarining (alert HAQIQATAN yetib boradi, xato
HAQIQIY Sentry'da ko'rinadi, siyosat 90 kun ishlaydi) oxirgi bo'g'inini
tashkil qiladi.

---

*Verified: 2026-08-05T10:52:00Z*
*Verifier: Claude (gsd-verifier) — qayta tekshiruv, `04-13`/`04-14` dan keyin*
