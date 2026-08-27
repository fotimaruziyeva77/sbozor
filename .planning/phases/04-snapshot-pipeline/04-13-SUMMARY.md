---
phase: 04-snapshot-pipeline
plan: 13
subsystem: kuzatuv-darvozasi
tags: [sentry, taskiq, scheduler, observability, process-gate, compose-derived, found-06, gap-closure]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 12
    provides: "`app/observability.py` (`init_sentry`, `scrub_event`, `scrub_breadcrumb`), `test_phase4_criteria.py` — SC#1…SC#5 darvozasi"
  - phase: 04-snapshot-pipeline
    plan: 8
    provides: "`alert_sweep` — planer boshqaruvidagi Telegram yo'li (D-20/D-22)"
  - phase: 04-snapshot-pipeline
    plan: 7
    provides: "`app/worker.py::scheduler` — holatsiz planer obyekti (D-02/D-03)"
  - phase: 04-snapshot-pipeline
    plan: 1
    provides: "`compose.yaml` dagi profilsiz `scheduler` konteyneri (W0-3) va `test_storage_config.py` ning qo'lda compose parseri"
provides:
  - "`app/worker.py::_install_client_observability` — `TaskiqEvents.CLIENT_STARTUP` ilmog'i; `taskiq scheduler` jarayonida `init_sentry()` HAQIQATAN chaqiriladi"
  - "`app/worker.py::ObservedScheduler` — `on_ready` ni o'rab, taskiq yutib yuboradigan istisnoni jurnal + Sentry'ga chiqaradi va QAYTA KO'TARADI"
  - "`app/observability.py::sentry_installed()` va `capture_exception()` — `sentry_sdk` ning YAGONA uyi"
  - "`tests/unit/test_sentry_processes.py` — `compose.yaml` dan HOSILA qilingan jarayon darvozasi (sanoq emas); noma'lum `command` shakli YIQILADI"
  - "`tests/unit/test_scheduler_observability.py` — CLIENT_STARTUP ilmog'i, env-nom pariteti, `on_ready` ning istisno e'loni"
  - "`test_sc5_...` ichidagi HAQIQIY jarayon zondi + nazorat yugurishi (`SENTRY_ACTIVE=True/False`)"
affects: [05-cv-zonalar, 06-billing, 08-hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Darvoza JARAYONLARNI sanaydi, KOD kirish nuqtalarini emas — va ro'yxatni `compose.yaml` dan HOSILA qiladi, ya'ni n+1-jarayon jimgina o'tib ketmaydi"
    - "Uch bosqichli darvozaning HAR bosqichida «topilmadi» = `pytest.fail`; «o'tkazib yuborish» yo'li ATAYIN yozilmaydi"
    - "Vendor xulqiga tayangan darvoza vendor manbasidan QULFLANADI (`AsyncBroker.startup` + `run_scheduler` matni), aks holda u jimgina eskirardi"
    - "Global holatni (`sentry_sdk.init()`) o'lchash uchun SUBPROCESS: to'plam holatini ifloslantirmaydi va yo'l-yo'lakay HAQIQIY jarayon chegarasini o'lchaydi"
    - "Har zondga NAZORAT YUGURISHI juft: `SENTRY_ACTIVE=True` da'vosi faqat `False` beradigan yugurish bilan birga ma'noga ega"
    - "Kuzatuv qatlami `Settings` ga BOG'LANMAYDI — aks holda u o'zi kuzatishi kerak bo'lgan konfiguratsiya nosozligidan yiqilardi"

key-files:
  created:
    - tests/unit/test_sentry_processes.py
    - tests/unit/test_scheduler_observability.py
  modified:
    - services/core-api/app/worker.py
    - services/core-api/app/observability.py
    - tests/unit/test_sentry_scrub.py
    - tests/integration/test_phase4_criteria.py
  deleted: []

key-decisions:
  - "Darvoza UCHINCHI nomni ro'yxatga QO'SHMADI, ro'yxatning O'ZINI olib tashladi: `SENTRY_DSN` oladigan jarayonlar `compose.yaml` dan hosila qilinadi. Nom qo'shish nosozlikni n+1 da qaytadan tug'dirardi — bu 04-12 ning aynan takrori bo'lardi"
  - "Ilmoq `get_settings()` ni CHAQIRMAYDI: `settings.py:329` bo'sh `S3_ACCESS_KEY` ni rad etadi va planer bugun `Settings` ni umuman qurmaydi. `get_settings()` planerni ombor rekvizitiga BOG'LARDI — kuzatuv qatlami o'zi xabar berishi kerak bo'lgan nosozlikdan yiqilardi. Narxi (nusxa xavfi) `test_scheduler_env_names_agree_with_settings` bilan qulflandi"
  - "`init_sentry()` ning O'ZI yetarli emas deb qabul qilindi: taskiq `send()` da `try/except` yo'q va `add_done_callback` istisnoni o'qimaydi, ya'ni planerning nosozligi Sentry o'rnatilgan holda ham hech qayerga bormasdi. Shuning uchun reja IKKI mahsulot o'zgarishi qildi"
  - "`ObservedScheduler.on_ready` istisnoni QAYTA KO'TARADI — taskiq semantikasi o'zgarmaydi; qatlam faqat QO'SHADI"
  - "`sentry_sdk` `app/worker.py` ga import QILINMADI: SDK ning yagona chaqiruvchisi `app/observability.py` bo'lib qoladi, ya'ni `before_send`/`before_breadcrumb` siz o'rnatish yo'li umuman ochilmaydi (T-04-98)"
  - "Zondning `PYTHONPATH` i `pyproject.toml` dan O'QILADI (`tomllib`), qadalgan uchlik sifatida takrorlanmaydi — u fayl tahrirlanganda jimgina eskirardi"
  - "`test_both_processes_install_sentry` OLIB TASHLANDI, kuchsizlantirilmadi: ikki haqiqat manbai saqlansa «qaysinisi to'g'ri?» savoli har regressiyada qaytadan so'ralardi. `test_sentry_init_wires_both_hooks` QOLDI — u ILMOQLAR haqida, jarayonlar haqida emas"
  - "Zond uchun `valkey_url` fixture'i KERAK BO'LMADI — o'lchov ko'rsatdi: `taskiq-redis` result backend ulanishni yalqov qiladi va zond yetib bo'lmaydigan `VALKEY_URL` bilan exit 0 beradi"

patterns-established:
  - "«Ro'yxat emas, predikat»: darvoza servis NOMLARINI bilmaydi — u `SENTRY_DSN` kalitiga qarab jarayonni O'ZI topadi. Quyi chegara (>= 3) yozilgan, nomlar YO'Q"
  - "Compose parseri ikkala `command` shaklini (blok ro'yxat + flow ro'yxat) qo'llab-quvvatlashi ALOHIDA o'lchanadi — shakl bo'yicha, servis nomi bo'yicha emas"
  - "RED bosqichi TO'RT testda TO'RT BOSHQA sabab bilan qizardi (bo'sh reyestr / konstanta yo'q / `capture_exception` yo'q / `on_ready` o'ralmagan) — ya'ni ular mustaqil da'volar"
  - "Nazorat da'vosi o'zining SHARTINI ham tekshiradi: «bekor qilingan vazifa Sentry'ga ketmaydi» testi avval `on_ready` ning O'RALGANINI talab qiladi, aks holda u bo'sh to'plam ustida yashil bo'lardi"

requirements-completed: [FOUND-06]

# Metrics
duration: 2h 05m
completed: 2026-08-05
---

# Phase 4 Plan 13: Planer jarayonida Sentry va yutilgan `on_ready` istisnosi Summary

**`taskiq scheduler` jarayoni `WORKER_STARTUP` emas, `CLIENT_STARTUP` ni ateshlaydi — shuning uchun `init_sentry()` u yerda hech qachon chaqirilmasdi; ilmoq qo'shildi, planerning `on_ready` istisnosi (taskiq uni `add_done_callback` da O'QIMAYDI) endi jurnal + Sentry'ga chiqib qayta ko'tariladi, Sentry darvozasi esa ikki elementli kod ro'yxatidan `compose.yaml` dan HOSILA qilinadigan jarayon darvozasiga almashtirildi va SC#5 ning Sentry yarmi manba matnidan emas, HAQIQIY subprocess'dan o'lchanadi.**

## Performance

- **Duration:** ~2 soat 05 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 2 ta yangi + 4 ta o'zgargan
- **Commits:** 4 ta (bittasi RED)

## Task Commits

| # | Task | Commit | Turi |
|---|------|--------|------|
| 1 (RED) | `test_scheduler_observability.py` — to'rt da'vo | `d3e8dee` | `test` |
| 1 (GREEN) | `CLIENT_STARTUP` ilmog'i + `ObservedScheduler` + `sentry_installed`/`capture_exception` | `dfa0b86` | `feat` |
| 2 | `test_sentry_processes.py` (hosila darvoza) + sanoqli darvozani olib tashlash | `ca88bc4` | `test` |
| 3 | SC#5 mezon testida HAQIQIY jarayon zondi | `6b05e5a` | `test` |

## ⛔ RED bosqichi — TO'RT test, TO'RT BOSHQA sabab

Reja «har bir da'vo hozir qizil bo'lishi shart» deb talab qildi va bu
o'lchandi. Modul darajasidagi bitta `ImportError` bilan hammasini
qizartirish YETARLI emas edi — u to'rttasini bitta sababga bog'lab,
ularning MUSTAQILLIGINI isbotsiz qoldirardi. Shuning uchun test fayli
`from app import worker` shaklida yozildi va har da'vo o'z nishoniga
tegdi:

| Test | RED sababi (o'lchangan) |
|---|---|
| `test_client_startup_hook_installs_sentry` | `assert []` — `CLIENT_STARTUP` reyestri BO'SH |
| `test_scheduler_env_names_agree_with_settings` | `AttributeError: module 'app.worker' has no attribute 'SENTRY_DSN_ENV'` |
| `test_on_ready_reports_the_swallowed_exception` | `AttributeError: ... has no attribute 'capture_exception'` |
| `test_on_ready_keeps_taskiq_semantics` | `on_ready` O'RALMAGAN (`type(scheduler).on_ready is TaskiqScheduler.on_ready`) |

⚠ To'rtinchi test — NAZORAT («bekor qilingan vazifa Sentry'ga ketmasin»)
va u tabiiy holda BUGUN HAM yashil bo'lardi: o'ralmagan
`TaskiqScheduler.on_ready` ham `capture_exception` ni chaqirmaydi —
chunki u umuman mavjud emas. Bu aynan fazaning o'zi qidirayotgan «bo'sh
to'plam ustida yashil» sinfi. Yechim: nazorat o'zining SHARTINI ham
tekshiradi — avval qobiqning mavjudligini talab qiladi, keyin xulqni
o'lchaydi.

## O'LCHANGAN FAKTLAR — taxmin qilinmadi

Reja ettita faktni (`M-1…M-7`) satr raqamlari bilan bergan edi; ijroda
ular `tests` konteynerida QAYTA tekshirildi (`taskiq 0.12.4`):

| # | Fakt | Tasdiq |
|---|---|---|
| M-1 | `cli/scheduler/run.py:392` -> `scheduler.broker.is_scheduler_process = True` | ✓ satr 392 |
| M-1b | `is_worker_process` ni FAQAT `cli/worker/run.py:148` o'rnatadi | ✓ satr 148 |
| M-2 | `cli/scheduler/run.py:406` -> `await scheduler.startup()` | ✓ satr 406 |
| M-3 | `TaskiqScheduler.startup()` -> `await self.broker.startup()` | ✓ manbadan |
| M-4 | `AsyncBroker.startup()`: `event = CLIENT_STARTUP`, `WORKER_STARTUP` ga FAQAT `is_worker_process` da almashadi | ✓ manbadan |
| M-5 | `add_done_callback` faqat `running_schedules.pop(...)` qiladi | ✓ satr 346-350 |
| M-6 | `send()` da `try/except` YO'Q | ✓ satr 157-174 |
| M-7 | `on_ready` — oddiy `async def` metod (override qilinadi) | ✓ manbadan |

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| S1 | `app/worker.py` dan `@broker.on_event(TaskiqEvents.CLIENT_STARTUP)` **dekoratori** olib tashlandi (funksiya QOLDIRILDI) | **UCH test**: `test_sentry_processes.py::test_every_sentry_process_installs_sentry`, `test_scheduler_observability.py::test_client_startup_hook_installs_sentry` **va** `test_phase4_criteria.py::test_sc5_...` — zond `'False' == 'True'` bilan yiqildi | `test_sentry_scrub.py` ning HAMMASI (13); `test_scheduler_observability.py` ning qolgan uchtasi (shu jumladan `_open_worker_resources` nazorati); `test_sentry_processes.py` ning qolgan uchtasi; qolgan to'rt mezon testi + ikkala meta-test (**6 passed**) | ⚠ **Bashoratdan KUCHLIROQ.** Reja ikkita nishon aytgan edi (jarayon testi + zond); UCHINCHISI — unit darajasidagi ilmoq testi — ham qizardi. Ya'ni bir xil da'voning ikki mustaqil qulfi bor: biri REYESTRNI o'qiydi (unit), ikkinchisi HAQIQIY JARAYONNI o'lchaydi (mezon) |
| S2 | `compose.yaml` ga to'rtinchi servis (`sabotage-probe`) qo'shildi: `SENTRY_DSN` beriladi, `command` esa `["python", "-m", "app.something"]` — `module:attr` tokenisiz | **AYNAN BITTA test**: `test_sentry_processes.py::test_every_sentry_process_installs_sentry`, xabar so'zma-so'z: «`sabotage-probe` servisi `SENTRY_DSN` ni oladi, lekin darvoza uning kirish nuqtasini `command` dan chiqara olmadi: `modul:atribut` shaklidagi 0 ta token topildi» | `test_storage_config.py` (7), `test_compose_sim_env.py`, `test_sentry_processes.py` ning parser/chegara/vendor testlari, va **butun** `test_phase4_criteria.py` (7/7) + `test_scheduler_observability.py` + `test_sentry_scrub.py` (**28 passed**) | ✅ **Aynan bashorat qilingandek** — bu sabotaj darvozaning HOSILA ekanini isbotlaydi: yangi jarayon paydo bo'lganda u jimgina o'tib ketmaydi. Eski (sanoqli) darvoza bu sabotajda **butunlay yashil** qolardi |
| S3 | `ObservedScheduler.on_ready` dan `capture_exception(...)` chaqiruvi olib tashlandi | **AYNAN BITTA test**: `test_scheduler_observability.py::test_on_ready_reports_the_swallowed_exception` (`assert [] == [RuntimeError(...)]`) | Jarayon darvozasi (4/4), zond va butun `test_phase4_criteria.py` (**7/7**), `test_sentry_scrub.py` | ✅ **Aynan bashorat qilingandek** — «Sentry O'RNATILDIMI?» va «istisno Sentry'ga BORDIMI?» ikki BOSHQA da'vo ekani isbotlandi |

Har uch holatda ham fayl **`cp` bilan** tiklandi (**hech qachon
`git checkout --` bilan emas** — `04-12`/`04-07` qoidasi) va
`git diff --exit-code` bo'sh chiqdi.

> ⛔ **S1 ning ahamiyati.** Bu fazaning nosozligi aynan «ro'yxatda uchinchi
> jarayon YO'Q» edi, ya'ni «ro'yxatdan bitta nomni o'chirish» sabotaji
> `04-12` da hech nimani qizartirmasdi. S1 esa JARAYON darajasida
> tishlaydi va uchta mustaqil qulfni birdan ochadi.

## O'LCHOVLAR — taxmin qilinmadi

### Valkey shoxi (reja ochiq savol qoldirgan edi)

| Yugurish | `VALKEY_URL` | Natija | Vaqt |
|---|---|---|---|
| Zond, DSN bilan | `redis://127.0.0.1:6399/0` (**yetib bo'lmaydi**) | `SENTRY_ACTIVE=True`, exit 0 | **4 s** |
| Zond, DSN'siz (nazorat) | o'sha | `SENTRY_ACTIVE=False`, exit 0 | **4 s** |

**Tanlangan shox: `valkey_url` fixture'i QO'SHILMADI.** Sabab o'lchandi:
`AsyncBroker.startup()` `result_backend.startup()` ni chaqiradi, lekin
`taskiq-redis` ulanishni YALQOV qiladi — zond yetib bo'lmaydigan manzil
bilan ham muvaffaqiyatli tugaydi. Ya'ni mezon buyrug'i zond uchun
qo'shimcha konteyner ko'tarmaydi.

**Yon foyda (rejada yo'q edi):** shu tanlov bir vaqtning o'zida «broker
yetib bo'lmasa ham kuzatuv qatlami ko'tariladi» invariantini ham
o'lchaydi — aks holda planer aynan o'sha nosozlikni ayta olmasdi.

Zondning ikkala yugurishi jurnal satrini ham chiqardi va u
«jim ishlash taqiqlangan» qoidasini tasdiqlaydi:

```
{"queue": "sbozor:jobs", "sentry": true,  "event": "scheduler_started", ...}
{"queue": "sbozor:jobs", "sentry": false, "event": "scheduler_started", ...}
```

### `inspect.getsource(app.router.lifespan_context)` nima qaytardi

Reja bu savolni «O'LCHANG, taxmin qilmang» deb qoldirgan edi. O'lchov
(`tests` konteynerida, `app.main` import qilingan holda):

| Nima chaqirildi | Natija | `init_sentry(` bormi |
|---|---|---|
| `inspect.getsource(app.router.lifespan_context)` | `fastapi.routing._merge_lifespan_context.<locals>.merged_lifespan` | **YO'Q** |
| `getattr(ctx, "__wrapped__", ctx)` -> `getsource` | YANA o'sha `merged_lifespan` (boshqa nusxa) | **YO'Q** |
| closure zanjiri, chuqurlik 8 | 14 manba, 1 noyob qobiq | **YO'Q** |
| closure zanjiri, chuqurlik 40 | 62 manba, 1 noyob qobiq | **YO'Q** |
| closure zanjiri, **chegarasiz** | 69 manba, 2 noyob: `merged_lifespan` **va `app.main.lifespan`** | **BOR** |

**Sabab:** FastAPI har `include_router` da ilova `lifespan` ini router
lifespan'i bilan QO'SHADI (`_merge_lifespan_context`), ya'ni bizning
`lifespan` o'nlab qobiq ostida, closure hujayralarida yotadi. Shuning
uchun `_lifespan_sources()` da chuqurlik CHEGARASI YO'Q — takrorlanishni
`seen` to'plami to'xtatadi (zanjir chekli) — va yig'ilgan manbalar soni
uchun quyi chegara qo'yilgan (bo'sh yuruvchi darvozani yashil
qoldirmaydi).

### Darvozaning `compose.yaml` dan chiqargani

| Nima | Natija |
|---|---|
| Parse qilingan servislar | **13** (chegara: >= 8) |
| `SENTRY_DSN` oladigan jarayonlar | **3** — `core-api`, `worker`, `scheduler` (chegara: >= 3) |
| `core-api` kirish nuqtasi | `app.main:app` (**blok ro'yxatdan**) |
| `worker` kirish nuqtasi | `app.worker:broker` (**flow ro'yxatdan**) |
| `scheduler` kirish nuqtasi | `app.worker:scheduler` (**flow ro'yxatdan**) |
| `environment` kalitlari jami | **75** (chegara: >= 40) |
| `${FORWARDED_ALLOW_IPS:-172.16.0.0/12}` kirish nuqtasi deb tanildimi | **YO'Q** — naqsh identifikatordan boshlanishni talab qiladi |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/unit/test_sentry_processes.py tests/unit/test_scheduler_observability.py tests/unit/test_sentry_scrub.py` | **25 passed**, exit 0 |
| 2 | `pytest tests/integration/test_phase4_criteria.py` | **7 passed**, exit 0 |
| 3 | `pytest` (sim ko'tarilgan) | **1 886 passed**, 5 deselected, exit 0 |
| 4 | `pytest tests/tenancy` | **472 passed** (o'zgarmadi) |
| 5 | `ruff check . && ruff format --check . && mypy .` | exit 0 (252 fayl / 244 manba) |
| 6 | `git diff --exit-code services/core-api/pyproject.toml frontend/package.json` | **bo'sh** — yangi paket YO'Q (T-04-SC) |
| 7 | `pytest test_phase4_criteria.py --collect-only \| grep -c 'test_sc[1-5]_'` | **5** |
| 8 | `pytest tests/unit --collect-only \| grep -c 'test_sentry_init_wires_both_hooks'` | **1** — saqlanadigan darvoza joyida |
| 9 | `python -c "... len(broker.event_handlers[CLIENT_STARTUP])"` | **1** (oldin `0`) |
| 10 | `python -c "... type(scheduler).__name__, isinstance(..., TaskiqScheduler)"` | **`ObservedScheduler True`** |
| 11 | `_open_worker_resources`/`_close_worker_resources` tanasi (izoh/docstringsiz solishtirildi) | **IDENTICAL** — ikkalasi ham tegilmadi |
| 12 | `npm run gate` | **exit 0**, **731 s** — `04-12` belgilagan **900 s** chegarasidan 169 s past |
| 13 | `node scripts/check-requirements-sync.mjs` | exit 0 — 49 talab MOS (Done 16 · Pending 32 · Blocked 1) |

⚠ `npm run gate` ichidagi frontend darvozalari ham o'lchandi va
o'zgarmadi: **vitest 338** (28 fayl), **i18n 777 × 3** (drift yo'q),
`typecheck`/`lint`/`build` — hammasi exit 0, `Compiled successfully`.

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `tests/unit/test_sentry_processes.py` | `compose.yaml` dan HOSILA jarayon darvozasi: (a) `SENTRY_DSN` servislari, (b) `command` dan `module:attr`, (c) obyekt turiga mos hodisa reyestrida `init_sentry(`; + parser chegarasi + vendor qulfi | **437** (min 150) |
| `tests/unit/test_scheduler_observability.py` | `CLIENT_STARTUP` ilmog'i, env-nomlarining `Settings` bilan pariteti, `on_ready` ning istisno e'loni va nazorati | **286** (min 100) |

## Files Modified

| Fayl | O'zgarish |
|---|---|
| `services/core-api/app/worker.py` | `SENTRY_DSN_ENV`/`LOG_LEVEL_ENV`/`DEFAULT_LOG_LEVEL`; `_install_client_observability` (`CLIENT_STARTUP`); `ObservedScheduler`; modul docstringiga «planer boshqa hodisani ateshlaydi» bo'limi. `_open_worker_resources` TEGILMADI |
| `services/core-api/app/observability.py` | `sentry_installed()` + `capture_exception()`; `init_sentry()` docstringi «IKKITA» -> «UCHTA jarayon» ga; modul docstringiga 04-13 bo'limi |
| `tests/unit/test_sentry_scrub.py` | `test_both_processes_install_sentry` OLIB TASHLANDI; `lifespan`/`_open_worker_resources` importlari keraksiz qoldi va olib tashlandi; docstringga «jarayon darvozasi endi qayerda» bandi |
| `tests/integration/test_phase4_criteria.py` | `SENTRY_ENTRYPOINTS` olib tashlandi; `_probe_pythonpath`, `_run_scheduler_probe`, `_assert_sentry_reaches_every_process` qo'shildi; `OBSERVABILITY_MODULE` QOLDI |

## Bazaviy holat

| O'lchov | Baza (`04-12`) | Hozir | Holat |
|---|---|---|---|
| pytest (sim ko'tarilgan) | 1 879 | **1 886** | ✅ **+7** (4 planer kuzatuvi + 4 jarayon darvozasi − 1 olib tashlangan sanoqli test) |
| tenancy | 472 | **472** | ✅ o'zgarmadi |
| `test_phase4_criteria.py` | 7 | **7** | ✅ o'zgarmadi (yangi `test_sc*` QO'SHILMADI — meta-test buni talab qiladi) |
| `--collect-only` da `test_sc[1-5]_` | 5 | **5** | ✅ o'zgarmadi |
| vitest / i18n | 338 / 777×3 | **338 / 777×3** | ✅ TEGILMADI (bu rejada frontend yo'q) — `npm run gate` ichida o'lchandi |
| `npm run gate` | exit 0, 686 s (chegara 900 s) | **exit 0, 731 s** | ✅ chegaradan 169 s past |
| `git diff pyproject.toml / package.json` | — | **bo'sh** | ✅ yangi paket YO'Q |

## Deviations from Plan

### Rejadan farq qilgan qarorlar (hammasi ochiq yozilgan)

**1. [Qamrov qarori] `_lifespan_sources()` — `__wrapped__` yetmadi, closure zanjiri kerak bo'ldi**

- **Topildi:** Task 2 ning o'lchov qadamida (reja «O'LCHANG» deb ataylab
  ochiq qoldirgan joy).
- **Muammo:** reja `getattr(ctx, "__wrapped__", ctx)` ni EHTIMOLIY yechim
  sifatida taklif qilgan edi; o'lchov ikkalasi ham ishlamasligini
  ko'rsatdi (yuqoridagi jadval).
- **Yechim:** chuqurlik chegarasisiz, `seen` to'plami bilan
  to'xtaydigan closure yuruvchisi; yig'ilgan manbalar soniga quyi chegara
  (bo'sh yuruvchi yashil qolmasin).
- **Committed in:** `ca88bc4`

**2. [Qamrov qarori] Zondning `PYTHONPATH` i qadalmadi — `pyproject.toml` dan o'qiladi**

- Reja «`pyproject.toml:26` dagi uchta yo'l» degan edi. Uchtasini test
  kodiga ko'chirish `pyproject.toml` tahrirlanganda JIMGINA eskirardi —
  ya'ni aynan shu reja yopayotgan nosozlik sinfi. `tomllib` (stdlib,
  `_MOCK_ROOTS` da yo'q) bilan o'qiladi va `len(paths) >= 3` chegarasi
  buzilgan o'qishni yashil qoldirmaydi.
- **Committed in:** `6b05e5a`

**3. [Qamrov qarori] RED bosqichi `from app import worker` shaklida yozildi**

- To'g'ridan-to'g'ri `from app.worker import SENTRY_DSN_ENV, ObservedScheduler`
  yozilsa modul darajasidagi BITTA `ImportError` to'rtala testni bir
  sababga bog'lab qo'yardi va ularning mustaqilligi isbotsiz qolardi.
  Modulni import qilib atributlarga murojaat qilish har da'voni O'Z
  nishoniga tegizdi (yuqoridagi RED jadvali).
- **Committed in:** `d3e8dee`

**4. [Bashoratdan kuchliroq natija] S1 ikkita emas, UCHTA testni qizartirdi**

- Reja S1 uchun ikkita nishon aytgan edi. Uchinchisi —
  `test_scheduler_observability.py::test_client_startup_hook_installs_sentry` —
  ham qizardi. Bu ZAIFLIK emas, TOPILMA: bir xil da'voning ikki mustaqil
  qulfi bor va ular BOSHQA qatlamda o'lchaydi (reyestr o'qish vs haqiqiy
  jarayon). Bo'shliq YO'Q, shuning uchun qo'shimcha ish talab qilinmadi.

### Auto-fixed Issues

**5. [Rule 1 — bug] `REQUIREMENTS.md` ning FOUND-06 dalili bu o'zgarishdan keyin YOLG'ON bo'lib qolardi**

- **Topildi:** yakuniy holat tekshiruvida.
- **Muammo:** `REQUIREMENTS.md:272` dalil ustuni «`init_sentry` **IKKALA
  jarayonda** ham chaqiriladi» deb yozadi va ikkalasini nomma-nom
  sanaydi. `04-VERIFICATION.md` buni allaqachon ⚠ bilan belgilagan
  («`SENTRY_DSN` oladigan jarayon **uchta**»); 04-13 dan keyin jumla
  shunchaki NOTO'G'RI bo'lib qolardi.
- **Yechim:** dalil matni uchala jarayonni nomma-nom sanaydi va hisob
  KOD kirish nuqtasi bo'yicha emas, JARAYON bo'yicha yuritilishini ochiq
  yozadi; ikkala yangi darvozaga havola qo'shildi.
- **Nega bu 04-14 ga qoldirilmadi:** o'z o'zgarishing yozib qo'ygan
  yolg'onni keyingi rejaga uzatish aynan shu reja yopayotgan «jimgina
  yolg'on» sinfi bo'lardi.
- **Tekshirildi:** `node scripts/check-requirements-sync.mjs` exit 0 —
  49 talab MOS (Done 16 · Pending 32 · Blocked 1), sanoqlar o'zgarmadi.

**6. [Rule 1 — bug] `ROADMAP.md` da `[x]` va «12/12» — ikkalasi ham fakt bilan zid edi**

- **Muammo:** `04-12` fazani `- [x]` va `12/12 | Complete` deb yopgan;
  keyin `04-VERIFICATION.md` uni `gaps_found` qildi va fazaga ikkita
  reja qo'shildi (14 ta). Ya'ni ROADMAP ikki xil haqiqat aytardi.
- **Yechim:** progress qatori `13/14 | In Progress`; belgi `- [ ]` ga
  qaytarildi va SABABI o'sha qatorda yozildi (bo'shliq `04-13` da
  yopildi, belgini qaytarish `04-14` ning qayta tekshiruviga bog'liq).
- **⚠ Chegara ochiq aytiladi:** faza HOLATI haqidagi yakuniy qaror
  `04-14` niki. Bu yerda faqat ZIDDIYAT olib tashlandi — «Complete»
  bo'lgan holda 13/14 reja bo'lishi mumkin emas.

---

**Total deviations:** 6 (3× qamrov qarori, 1× bashoratdan kuchliroq
natija, **2× Rule 1 bug** — ikkalasi ham hujjat darajasida, ikkalasi
ham shu o'zgarish tug'dirgan/ochgan ziddiyat).

**Impact on plan:** Hech biri darvozani kuchsizlantirmadi; uchtasi
(1–3) darvozani rejadagidan KUCHLIROQ qildi (hosila `PYTHONPATH`,
chegarasiz zanjir yuruvchisi + quyi chegara, mustaqil RED sabablari),
ikkitasi (5, 6) hujjatdagi ikki xil haqiqatni yopdi. Mahsulot kodidagi
yagona o'zgarish rejaning O'Z topshirig'i edi.

## Issues Encountered

- **`ruff format` uch marta o'z-o'zidan qayta formatladi** (`worker.py`,
  `test_sentry_processes.py`, `test_phase4_criteria.py`) — har safar
  `ruff format .` chaqirilib, keyin `ruff check` + `mypy` qayta
  yugurtirildi. Hech qanday semantik o'zgarish bo'lmadi.
- **`ruff` `SIM105` ni talab qildi** (`try/except/pass` ->
  `contextlib.suppress`) va `mypy` keyin ikkita `# type: ignore` ni
  «unused» deb belgiladi — ikkalasi ham tuzatildi va sabab kodda izoh
  bilan yozildi (manbasiz obyekt zanjirning QONUNIY bo'g'ini).
- **Zondning `subprocess.run` chaqiruvi `S603` beradi** (ruff `S`
  to'plami). `# noqa: S603` sababi bilan yozildi: argvda foydalanuvchi
  kiritmasi yo'q va `shell=True` ishlatilmaydi.

## Known Stubs

Yo'q.

⚠ **Stub bo'lmagan, lekin ochiq qolgan bandlar** (uchalasi ham `04-12`
dan meros va bu reja ularga TEGMADI):

1. `ops/seaweedfs/README.md` da `docker compose down -v` ogohlantirishi
   yo'q. **Egasi:** `ops/seaweedfs/README.md` ga keyingi tegadigan reja.
2. `scripts/check-validation-signoff.mjs` ning `DEFAULT_FILE` i qadalgan.
   **Egasi:** 5-fazaning validatsiya rejasi.
3. `deferred-items.md` #2 — `.env.example` dagi bo'sh `S3_ACCESS_KEY`/
   `S3_SECRET_KEY` yangi klonda `worker`/`scheduler` ni yiqitadi.
   **Egasi:** `deferred-items.md` da yozilgan.

⚠ **`04-12` ning «ochiq qolgan band #1» YOPILDI:** «`scheduler`
jarayonida Sentry o'rnatilmaydi» — u o'sha SUMMARY da 8-fazaga
biriktirilgan edi, `04-VERIFICATION.md` esa uni BLOKLOVCHI bo'shliq deb
qayta tasnifladi. Shu reja uni yopdi.

## Threat Flags

Reja threat register'ining oltala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-96 (planer jarayonining kuzatuvsiz qolishi) | **UCH MUSTAQIL QULF**: `CLIENT_STARTUP` ilmog'i (`dfa0b86`), hosila jarayon darvozasi (`ca88bc4`), haqiqiy jarayon zondi (`6b05e5a`). S1 uchalasini ham qizartirdi |
| T-04-97 (`on_ready` istisnosining yutilishi) | `try/except -> log.exception + capture_exception -> raise`; S3 aynan uni qizartirdi va zond bilan mezon testi YASHIL qoldi (boshqa da'vo) |
| T-04-98 (uchinchi jarayondan Sentry'ga chiquvchi hodisa) | `init_sentry()` — YAGONA o'rnatish yo'li; darvoza `init_sentry(` ni talab qiladi, `sentry_sdk` esa `app/worker.py` ga import QILINMAGAN, ya'ni ilmoqsiz o'rnatish yo'li ochilmaydi |
| T-04-99 (darvozaning `compose.yaml` dan import qilishi) | **accept** (rejadagidek): faqat repo ichidagi fayldan o'qiladi va faqat test jarayonida ishlaydi — `test_storage_config.py` bilan bir xil xavf darajasi |
| T-04-100 (taskiq ning hodisa tanlovi jimgina o'zgarishi) | `test_taskiq_still_picks_the_event_by_process` — `AsyncBroker.startup` manbasida uchala marker, `run_scheduler` da `is_scheduler_process` |
| T-04-SC (paket o'rnatishlari) | **Yangi paket YO'Q**; `git diff --exit-code` bo'sh |

⚠ **Yangi yuza (registerda bor edi, lekin qoldiq xavf aniqlashtirildi):
planer hodisasining mazmuni.** `ObservedScheduler.on_ready` Sentry'ga
`task_name`, `schedule_id` va manba SINF NOMINI yozadi. Reja to'rtala
jadval vazifasi ARGUMENTSIZ (`capture.tick`, `retention.daily`,
`alert.sweep`, `alert.digest`), ya'ni shaxsiy ma'lumot yo'q — bu
o'zgarmadi. `include_local_variables` qarori hamon **8-fazada**
(`04-12` ning Threat Flags bandi).

## Next Phase Readiness

**Fazani qayta tekshirish (`/gsd-verify-work`) uchun:**

- `04-VERIFICATION.md` ning YAGONA bo'shlig'i yopildi va u **uch
  mustaqil qatlamda** o'lchanadi:
  - `pytest tests/unit/test_scheduler_observability.py` — ilmoq + istisno
  - `pytest tests/unit/test_sentry_processes.py` — `compose.yaml` dan hosila
  - `pytest tests/integration/test_phase4_criteria.py` — HAQIQIY jarayon zondi
- ⚠ `FOUND-06` ning `Done` holati endi **uchala** `SENTRY_DSN`
  jarayoniga tayanadi. `REQUIREMENTS.md:272` ning dalil matni SHU REJADA
  yangilandi (u «IKKALA jarayonda» deb yozardi va bu o'zgarishdan keyin
  YOLG'ON bo'lib qolardi); `node scripts/check-requirements-sync.mjs`
  exit 0 — 49 talab mos, Done 16 · Pending 32 · Blocked 1.
- ⚠ `04-HUMAN-UAT.md` #4 (Telegram alertining HAQIQATAN yetib borishi)
  hamon OCHIQ va u FOUND-06 ning ops sharti.

**`.planning/STATE.md` haqida — bu rejada QAYERGACHA tegildi:**

Yangilandi: `Current Position` (Plan 14 of 14, 93 % — 13/14), progress
frontmatter'i (67/66), Performance Metrics (`Phase 04 P13`), oltita
qaror va sessiya bandi.

⚠ **`Blockers/Concerns` bo'limiga ATAYIN TEGILMADI.** U yerdagi to'rtta
Phase 4 bandi (kadr olish usuli, job orchestration, `gate` 1000 s /
31 % qayta bajarish, go2rtc-sim oqimi) **hech biri 04-13 ning mavzusi
emas**, va `04-12` SUMMARY si ularning yangi matnini «faza yopilish
oqimi uchun» tayyor holda yozib qo'ygan. Ularni bu yerda qo'llash
qamrovni kengaytirardi — **egasi: `04-14`** (faza yopilish rejasi).

**5-faza uchun:**

- **Yangi jarayon qo'shish endi ARZON EMAS, lekin XAVFSIZ:** `compose.yaml`
  ga `SENTRY_DSN` beriladigan servis qo'shilgan zahoti
  `test_sentry_processes.py` uni TALAB QILADI — kuzatuvsiz jarayon
  jimgina paydo bo'la olmaydi.
- `capture_exception()` — `app/observability.py` dagi yagona tashqi
  eshik; CV servisidagi job qobiqlari xuddi shu naqshdan foydalanadi.

**Bloklovchi yo'q.**

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*

## Self-Check: PASSED

- **Ikkala yaratilgan fayl diskda tekshirildi** (`MISSING: 0`):
  `tests/unit/test_sentry_processes.py` (437 qator),
  `tests/unit/test_scheduler_observability.py` (286 qator).
- **To'rtala o'zgargan fayl ham diskda:** `app/worker.py`,
  `app/observability.py`, `tests/unit/test_sentry_scrub.py`,
  `tests/integration/test_phase4_criteria.py`.
- **To'rtala commit `git log 079d628..HEAD` da tasdiqlandi:** `d3e8dee`,
  `dfa0b86`, `ca88bc4`, `6b05e5a` (+ `e907a88` — kirill harflari
  tuzatilgan izoh).
- **Birorta commitda fayl o'chirilishi YO'Q**
  (`git diff --diff-filter=D --name-only 079d628..HEAD` bo'sh).
- **Uchala sabotajdan keyin `git diff --exit-code` bo'sh** — tiklash
  har safar `cp` bilan bajarildi.
- **Ishchi daraxt toza** — repo ildizidagi uchta begona fayl
  (`.docx` × 2, `SBOZOR-MVP-texnik-topshiriq.md`) TEGILMADI.
- **`npm run gate` exit 0** (731 s, chegara 900 s).
