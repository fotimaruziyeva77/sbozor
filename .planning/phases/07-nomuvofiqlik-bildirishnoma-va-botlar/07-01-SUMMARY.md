---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 01
subsystem: bot-service
tags: [bot-service, aiogram, compose, sentry-gate, dependency-isolation]
requires:
  - "compose.yaml — `cache` servisi (FSM ombori uchun)"
  - "tests/unit/test_sentry_processes.py — 04-13 da qurilgan hosila darvoza"
  - "services/cv-service/* — ikkinchi toolchain naqshi (Dockerfile, pyproject, README)"
provides:
  - "services/bot-service/ — loyihaning UCHINCHI va OXIRGI servisi (D-08/D-09)"
  - "compose.yaml::bot-service — profilsiz long-poller (`python -m app.main`)"
  - "compose.yaml::bot-tests — o'sha image'ning test entrypointi"
  - "npm run bot:test / bot:lint — `gate` zanjirida"
  - "tests/unit/test_sentry_processes.py — `-m` shakli + `dp.startup.register` markeri"
  - "services/bot-service/tests/unit/test_runtime_deps.py — D-08/1 mexanik darvozasi"
affects:
  - "07-08 (ichki API) va 07-11 (handlerlar) shu skeletga yozadi"
  - "pyproject.toml (root) — ruff/mypy `exclude` uchinchi servisni ham qamraydi"
tech-stack:
  added:
    - "aiogram[fast,redis,i18n]==3.30.0"
    - "redis[hiredis]==7.4.1 (⛔ core-api ning 8.0.1 idan ATAYIN boshqa)"
    - "pydantic==2.13.4 (alohida lockfaylda)"
    - "Babel 2.18.0 / aiodns 4.0.4 / uvloop 0.22.1 (tranzitiv, aiogram ekstralari)"
  patterns:
    - "Servis kesimidagi bog'liqlik izolyatsiyasi (D-09) — uchinchi `uv.lock`"
    - "Darvoza kengaytmasi + NAZORAT testi (kengaytma jimgina eskirmasin)"
    - "Manba darajasidagi tekshiruv `ast` bilan BAJARILADIGAN kodga toraytirildi"
key-files:
  created:
    - services/bot-service/pyproject.toml
    - services/bot-service/uv.lock
    - services/bot-service/Dockerfile
    - services/bot-service/README.md
    - services/bot-service/app/__init__.py
    - services/bot-service/app/main.py
    - services/bot-service/app/settings.py
    - services/bot-service/app/observability.py
    - services/bot-service/tests/unit/test_sentry_entrypoints.py
    - services/bot-service/tests/unit/test_runtime_deps.py
  modified:
    - compose.yaml
    - package.json
    - .env.example
    - pyproject.toml
    - tests/unit/test_sentry_processes.py
decisions:
  - "Sozlama maydoni `bot_token` EMAS, `telegram_bot_token` — loyihada `validation_alias` hech qayerda ishlatilmaydi va muhit kaliti maydon nomining katta harfli shakli"
  - "`bot-tests` standart tokeni shaklga mos (`123456:TEST-TOKEN-NOT-REAL`) — `test-token` `TokenValidationError` beradi"
  - "Root darvozaning manba qatlami `ast` bilan izoh/docstringdan tozalanadi — sabotaj bu teshikni O'LCHAB ko'rsatdi"
  - "Root `pyproject.toml` da `services/bot-service` ruff+mypy `exclude` ga qo'shildi (`Duplicate module named app`)"
metrics:
  duration: "~65 daqiqa (bir marta stream uzilishi bilan)"
  completed: 2026-08-12
  tasks: 3
  commits: 5
---

# Phase 07 Plan 01: bot-service skeleti va Sentry darvozasining kengaytmasi — Summary

Loyihaning uchinchi va oxirgi servisi (`services/bot-service`) o'z `uv.lock` i
bilan tug'ildi, `compose.yaml` ga ikki yozuv bilan kirdi va `test_sentry_processes.py`
darvozasini ATAYIN buzib, o'sha yerda kengaytma + nazorat testi bilan tuzatdi —
kengaytma ikkita sabotaj bilan o'lchandi va biri darvozadagi HAQIQIY teshikni ochdi.

## Nima qilindi

### Task 1 — `services/bot-service/` skeleti (`b201346`)

`cv-service` naqshining aynan takrori: `base`/`dev`/`runtime` uch bosqichli
Dockerfile (`python:3.13-slim-trixie`, ⛔ Alpine emas — `uvloop` uchun musl
g'ildiragi yo'q), o'z `pyproject.toml` va `uv.lock` i.

`uv.lock` **konteynerda** generatsiya qilindi
(`ghcr.io/astral-sh/uv:0.11.33-python3.13-trixie-slim`) — xostda `uvloop`
Windows g'ildiragi bo'lmagani uchun manbadan qurilib yiqilardi. Bu **xost
artefakti, paket nuqsoni emas** (07-RESEARCH § Package Legitimacy Audit).

O'lchangan natija (`bot-tests` konteynerida):

| Paket | Kutilgan | Haqiqiy |
|---|---|---|
| `aiogram` | 3.30.0 | **3.30.0** |
| `redis` | `7.` bilan boshlanadi (⛔ `8.` emas) | **7.4.1** |
| `pydantic` | 2.13.4 | **2.13.4** |
| `import sqlalchemy` | `ModuleNotFoundError` | **exit 1, `ModuleNotFoundError`** |

`app/main.py` — kirish nuqtasi: modul darajasida `bot`/`storage`/`dp`,
`dp.startup.register(_on_startup)` ilmog'ida `init_sentry(...)` va
`delete_webhook(drop_pending_updates=False)`, `TelegramConflictError` esa
**jim yutilmaydi** (CRITICAL + Sentry + qayta ko'tariladi).

### Task 2 — compose + npm + `.env.example` (`c17089d`)

`bot-service` **profilsiz** (ishlab chiqarish komponenti), `bot-tests` test
profilida — **to'rtinchi servis tug'ilmadi**, bu o'sha image'ning boshqa
entrypointi.

O'lchangan darvozalar: `docker compose config --quiet` → **exit 0**;
`config --services | grep -c '^bot-service$'` → **1**;
`--profile test config --services | grep -c '^bot-tests$'` → **1**;
`config | grep -c "replicas"` → **0**.

`gate` zanjiriga `bot:lint` + `bot:test` qo'shildi; **`gate:fast` tegilmadi**
(mexanik tasdiqlandi: `s['gate:fast'].includes('bot:')` → `false`). Byudjet
**2300 s da qoldi**, sabab `//gate-budget` izohiga bir jumla bilan yozildi.

### Task 3 — darvoza kengaytmasi + `bot-service` ning o'z darvozalari (`db28572`)

Root `tests/unit/test_sentry_processes.py` — **o'chirilmadi, kengaytirildi**:

1. `FOREIGN_HOOK_MARKERS` ga `dp.startup.register` (aiogram ilmog'i).
2. (b) bosqichi endi `-m <modul>` shaklini ham o'qiydi
   (`MODULE_RUN_ATTRIBUTE = "main"`); ikkalasi ham topilmasa **hamon
   `pytest.fail`** — «o'tkazib yuborish» shoxi qo'shilmadi.
3. Nazorat testi `test_entrypoint_reader_handles_both_launch_shapes` — ikkala
   shox ham **haqiqatan ishlatilyaptimi** (usiz kengaytma jimgina eskirardi).

⛔ Fayl birorta servis nomini tashimaydi: `grep -c "bot-service"` → **0**.
`MIN_SENTRY_SERVICES`/`MIN_BUILD_SERVICES`/`MIN_COMPOSE_SERVICES`/`MIN_ENV_KEYS`
qiymatlari **o'zgarmadi** (3/4/8/40).

`bot-service` ning o'z darvozalari (`bot-tests`, **21 test, 2 fayl**):
`test_sentry_entrypoints.py` — **reyestr** darajasi (`dp.startup` observeriga
haqiqatan ro'yxatga olingan callback manbasida `init_sentry(`);
`test_runtime_deps.py` — D-08/1 **ikki qatlamda** (`importlib.metadata` +
xulqiy `import`), pin darvozasi va AGPL/`LicenseRef-` predikati.

## Sabotaj natijalari (ikkalasi ham bajarildi)

### ⛔ Sabotaj 1 — darvoza QIZARMADI. Bu HAQIQIY topilma edi.

`app/main.py` dan `init_sentry(...)` **chaqiruvi** vaqtincha olib tashlandi
(`log.info("sentry", enabled=False)`) va `pytest tests/unit/test_sentry_processes.py -q`
**YASHIL qoldi**.

**Sabab:** `_assert_foreign_entrypoint_installs_sentry` `INIT_MARKER in source`
bilan **xom matnni** ko'radi, kirish nuqtasi fayli esa o'sha nomni **o'z
docstringida** tushuntiradi. Ya'ni **izohning o'zi darvozani qanoatlantirardi** —
bu darvoza qarshi kurashayotgan «jimgina yolg'on» sinfining bir qavat yuqorisi:
fayl qanchalik yaxshi hujjatlansa, darvoza shunchalik bo'sh bo'lardi.

**Tuzatish testda emas, (c) bosqichining shoxida** (reja aynan shuni talab
qilgan): `_executable_source()` manbani `ast` bilan qayta quradi —
`ast.unparse` izohlarni tashlaydi, docstringlar esa `_DocstringStripper` bilan
olinadi. Endi **uchala shart ham** (atribut e'loni, ilmoq markeri,
`init_sentry(`) **bajariladigan kod** ustida tekshiriladi.

Tuzatishdan keyin sabotaj **QIZARDI**:

```
E  AssertionError: `bot-service` (`app.main:main`, kod ildizi `bot-service`):
   `SENTRY_DSN` konteynerga BERILADI, lekin kirish nuqtasining faylida
   `init_sentry(` chaqiruvi YO'Q
```

Teshik `test_source_layer_ignores_comments_and_docstrings` **nazorat testi**
bilan qulflandi (u `_executable_source` ni sun'iy namunada o'lchaydi, ya'ni
tuzatish jimgina qaytib kelmaydi). ⚠ Qolgan chegara ochiq yozildi: docstring
bo'lmagan satr literali (`log.info("init_sentry(")`) hamon o'tib ketardi — uni
obyekt darajasidagi `bot-tests` darvozasi qoplaydi.

### ✓ Sabotaj 2 — darvoza kutilganidek yiqildi

`compose.yaml` dagi `bot-service.command` `["python", "app/main.py"]` ga
o'zgartirildi → (b) bosqichi **`pytest.fail`** berdi (jimgina o'tkazib
yuborish YO'Q) va **ikkita test birdan** qizardi:

```
FAILED test_entrypoint_reader_handles_both_launch_shapes
FAILED test_every_sentry_process_installs_sentry
E  Failed: `bot-service` ... `modul:atribut` shaklidagi 0 ta token ([]) va
   `-m <modul>` shaklidagi 0 ta token ([]) topildi
```

Ikkala sabotaj ham **qaytarildi** (`git checkout --`) va to'plam yashil.

## Rejadan chetlanishlar

### Avtomatik tuzatilganlar

**1. [Rule 3 - Bloklovchi] `bot-tests` standart tokeni shaklga mos qilindi**

- **Qachon:** Task 2
- **Muammo:** Reja `TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN:-test-token}` deb
  yozgan. `app/main.py` `Bot(...)` ni **modul darajasida** quradi, aiogram esa
  konstruktorda `validate_token()` chaqiradi. O'lchandi:
  `aiogram.utils.token.TokenValidationError: Token is invalid!` — ya'ni
  `import app.main` yozadigan **har bir test** yig'ilishda yiqilardi va sabab
  test mantig'ida emas, compose standartida bo'lardi.
- **Tuzatish:** `${TELEGRAM_BOT_TOKEN:-123456:TEST-TOKEN-NOT-REAL}` + blokda
  o'lchov izoh sifatida yozildi.
- **Fayl:** `compose.yaml` · **Commit:** `c17089d`

**2. [Rule 3 - Bloklovchi] Root `pyproject.toml` ga `services/bot-service` istisnosi**

- **Qachon:** Task 3
- **Muammo:** `npm run lint` (`mypy .`) **butunlay to'xtadi**:
  `services/core-api/app/__init__.py: error: Duplicate module named "app"
  (also at "./services/bot-service/app/__init__.py") — errors prevented
  further checking`. Bu `cv-service` uchun 2026-08-08 da allaqachon
  o'lchangan va root manifestda **hujjatlangan** xato sinfi.
- **Tuzatish:** `services/bot-service` ruff `extend-exclude` va mypy `exclude`
  ga qo'shildi; mavjud izoh yangi o'lchov bilan kengaytirildi.
- **Fayl:** `pyproject.toml` · **Commit:** `db28572`

**3. [Rule 1 - Nuqson] Darvozaning manba qatlami izohni chaqiruv deb o'qirdi**

- **Qachon:** Task 3 (sabotaj 1)
- **Tafsilot:** yuqoridagi «Sabotaj 1» bo'limi.
- **Fayl:** `tests/unit/test_sentry_processes.py` · **Commit:** `db28572`

**4. [Rule 3 - Bloklovchi] Sozlama maydoni `telegram_bot_token` deb nomlandi**

- **Qachon:** Task 1
- **Muammo:** Reja `bot_token: SecretStr` deb yozgan, `compose.yaml` esa
  `TELEGRAM_BOT_TOKEN` beradi (A1 — alert supurgisi bilan bir xil token).
  Loyihada `validation_alias` **hech qayerda** ishlatilmaydi (o'lchandi:
  `core-api/app/settings.py` da nol uchrash) — muhit kaliti maydon nomining
  katta harfli shakli va **bu qoidaning o'zi mexanik kafolat**. `bot_token`
  `BOT_TOKEN` ni izlardi va konteyner «Field required» bilan yiqilardi, token
  esa muhitda **turgan** bo'lardi.
- **Tuzatish:** maydon `telegram_bot_token`; sabab kod izohida yozildi.
  Alias qo'shish **ataylab rad etildi** — u loyihada ikkinchi nomlash yo'lini
  ochardi.
- **Fayl:** `services/bot-service/app/settings.py` · **Commit:** `b201346`

**5. [Rule 1 - Nuqson] Qabul mezonining literal sanog'i izohlardan shishgan edi**

- **Qachon:** yakuniy tekshiruv
- **Muammo:** mezon `sentry_sdk.init(` sanog'ini `observability.py` da 1,
  `main.py` da 0 deb talab qiladi. O'lchandi: **3 va 1** — barcha ortiqcha
  uchrashlar izoh/docstringda edi, ya'ni keyingi tekshiruvchi yolg'on
  ogohlantirish olardi.
- **Tuzatish:** izohlar matni o'zgartirildi (ma'no o'zgarmadi). Endi **1 va 0**.
- **Commit:** `9556b1b`

### Muhit muammosi (kod nuqsoni emas)

⚠ **Worktree'da compose ishga tushirish `storage` konteynerini buzdi va
tuzatildi.** Worktree'da `.env` va `ops/seaweedfs/s3.json` **yo'q** (ikkalasi
ham `.gitignore` da). `docker compose` ular o'rniga **katalog** yaratdi va
`sbozor-storage-1` ni o'sha mount bilan qayta yaratdi
(`read /etc/seaweedfs/s3.json: is a directory` → unhealthy).

Tuzatildi: bogus katalog o'chirildi, asosiy repodan `.env` va `s3.json`
nusxalandi (ikkalasi ham gitignore'da — commitga tushmadi),
`docker compose up -d --force-recreate storage` → **healthy**. Shundan keyin
barcha yugurishlar `--no-deps` bilan bajarildi.

⚠ **Orkestrator uchun band:** `sbozor-storage-1` hozir **worktree yo'liga**
bog'langan bind-mount bilan ishlayapti. Worktree o'chirilgandan keyin asosiy
repodan bir marta `docker compose up -d --force-recreate storage` bajarilsin.

## Yakuniy tekshiruv natijalari

| Buyruq | Natija |
|---|---|
| `docker compose config --quiet` | ✅ exit 0 |
| `docker compose ... run --rm tests pytest tests/unit -q` | ✅ **671 test yashil** |
| `docker compose ... run --rm bot-tests pytest -q` | ✅ **21 test yashil** (2 fayl) |
| `bot-tests`: `ruff check . && ruff format --check . && mypy .` | ✅ `All checks passed` · `7 files already formatted` · `no issues in 6 source files` |
| root: `ruff check . && ruff format --check . && mypy .` | ✅ `316 files already formatted` · `no issues in 307 source files` |
| `test_sentry_processes.py` | ✅ **6 test yashil** (4 edi: +nazorat, +docstring nazorati) |

⚠ **`npm run gate:fast` bu worktree'da yuritilmadi** — u
`npm --prefix frontend test` ni chaqiradi, `frontend/node_modules` esa
`.gitignore` da va worktree'ga o'rnatilmagan. Bu **muhit cheklovi, kod
nuqsoni emas**: o'zgarish `gate:fast` ga **strukturaviy jihatdan tegmaydi** va
bu mexanik tasdiqlandi (`s['gate:fast'].includes('bot:')` → `false`).
Byudjet o'lchovi faza yopilishida (07-17) bajariladi.

## Known Stubs

⚠ **Bot bugun `/start` ga javob bermaydi va bu ATAYIN.** `dp` bo'sh router
bilan ishga tushadi — handlerlar **07-11** ning ishi (reja buni ochiq talab
qilgan: «Handlerlar bu rejada YOZILMAYDI»). Holat `services/bot-service/README.md`
§5 da ochiq yozilgan va bu rejaning maqsadi (skelet + darvoza) to'liq bajarildi.

| Stub | Fayl | Sabab / kim yopadi |
|---|---|---|
| Routerlar ulanmagan, `/start` javobsiz | `services/bot-service/app/main.py` | 07-11 (BOT-01/BOT-02 handlerlari) |
| `core_api_url`/`bot_service_token` ishlatilmaydi | `services/bot-service/app/settings.py` | 07-08 (`core_client.py` ichki API qobig'i) |
| `locales/` katalogi yo'q | — | 07-11/D-30 (Babel `.po` katalogi) |

## Threat Flags

Yangi, rejaning `<threat_model>` idan tashqaridagi xavf yuzasi **topilmadi**.
`T-07-01`, `T-07-02`, `T-07-03`, `T-07-05` mitigatsiyalari amalga oshirildi va
mexanik o'lchandi (`test_runtime_deps.py`, `Settings` validatorlari,
`grep -c replicas` → 0, `redis` pin darvozasi).

## Self-Check: PASSED

Barcha e'lon qilingan fayllar diskda mavjud va barcha commitlar `git log` da:
`b201346`, `c17089d`, `db28572`, `9556b1b` (+ SUMMARY commiti).
