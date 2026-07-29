---
phase: 01-poydevor-va-tenant-xavfsizligi
plan: 01
subsystem: infra
tags:
  [
    docker-compose,
    postgres,
    valkey,
    rls,
    uv,
    fastapi,
    pytest,
    testcontainers,
    ci,
  ]

# Dependency graph
requires: []
provides:
  - "Compose steki: db (postgres:18.4-trixie), cache (valkey 9.1.1), core-api, hamda migrate/web/proxy/test profillari"
  - "Ikkita superuser bo'lmagan DB roli: sbozor_owner (DDL) va sbozor_app (DML) — NOSUPERUSER NOBYPASSRLS"
  - "uv workspace: packages/sbozor-core (editable) + services/core-api (o'z uv.lock i bilan)"
  - "core-api image: python:3.13-slim-trixie, dev/runtime multi-stage, runtime non-root"
  - "/healthz (liveness) va /readyz (DB + Valkey ping) endpointlari"
  - "Wave 0 test infratuzilmasi: tests/conftest.py — haqiqiy Postgres konteyneri, sbozor_app roli bilan ulanadigan app_engine"
  - "tests/tenancy/test_meta.py — 5 ta RLS-bypass meta-testi (faza darvozasi)"
  - "Root package.json skriptlari (make o'rniga): up, down, migrate, test, lint"
  - "CI quvuri: ruff -> ruff format -> mypy strict -> pytest"
affects:
  - "01-02 (frontend skeleti — compose `frontend` servisi va `web` profili tayyor)"
  - "01-03 (sbozor-core modullari — paket va editable install tayyor)"
  - "01-04 (Alembic + RLS policy'lar — `migrate` profili, owner_url fixture'i, meta-test fayli tayyor)"
  - "01-05..01-10 (barcha RLS/audit isbotlari shu conftest fixture'i ustida quriladi)"

# Tech tracking
tech-stack:
  added:
    - "postgres:18.4-trixie, valkey/valkey:9.1.1-alpine, nginx:1.30.4-alpine"
    - "uv 0.11.33, hatchling, FastAPI 0.140.13, uvicorn 0.51.0, pydantic 2.13.4 + pydantic-settings 2.14.2"
    - "SQLAlchemy 2.0.51 + asyncpg 0.31.0, alembic 1.18.5 + alembic-utils 0.8.8"
    - "PyJWT 2.13.0, pwdlib[argon2] 0.3.0, cryptography 49.0.0, structlog 26.1.0, redis[hiredis] 8.0.1"
    - "ruff 0.16.0, mypy 2.3.0, pytest 9.1.1 + pytest-asyncio 1.4.0, testcontainers 4.15.0, psycopg 3.3.4"
  patterns:
    - "Rol ajratish: ilova hech qachon superuser bilan ulanmaydi (RLS uchun yagona haqiqiy nazorat)"
    - "Rol DDL uchun yagona haqiqat manbai: prod entrypoint va test fixture bir xil SQL faylini bajaradi"
    - "Fixture o'z-o'zini himoyalash testi: engine superuser'ga qaytarilsa CI yiqiladi"
    - "Bitta orkestratsiya nuqtasi: compose profillari + root npm skriptlari (Makefile yo'q)"
    - "Multi-stage image: dev (testlar/alembic) va runtime (non-root, dev deps yo'q)"

key-files:
  created:
    - compose.yaml
    - compose.override.yml
    - ops/db/init/01-roles.sql
    - ops/db/init/02-passwords.sh
    - ops/nginx/nginx.conf
    - package.json
    - pyproject.toml
    - .env.example
    - .gitignore
    - .gitattributes
    - .dockerignore
    - packages/sbozor-core/pyproject.toml
    - packages/sbozor-core/sbozor_core/__init__.py
    - services/core-api/pyproject.toml
    - services/core-api/uv.lock
    - services/core-api/Dockerfile
    - services/core-api/.dockerignore
    - services/core-api/app/main.py
    - services/core-api/app/settings.py
    - tests/conftest.py
    - tests/tenancy/test_meta.py
    - .github/workflows/ci-backend.yml
  modified: []

key-decisions:
  - "Deployment topologiyasi: BITTA DOMEN (nginx `/api/` -> core-api, `/` -> frontend) — shu sababli refresh cookie uchun SameSite=Lax yetarli, alohida CSRF token qurilmaydi (RESEARCH Open Question 3)"
  - "Dev xost portlari `.env` orqali o'zgaruvchan (DB_HOST_PORT/CACHE_HOST_PORT/API_HOST_PORT/PROXY_HOST_PORT), default qiymatlar 5432/6379/8000/8080; bog'lanish interfeysi har doim 127.0.0.1"
  - "postgres 18+ volume'i `/var/lib/postgresql` ga o'rnatiladi (`/var/lib/postgresql/data` ga EMAS) — 18+ image'lar major-versiya kataloglaridan foydalanadi"
  - "pytest-asyncio loop scope (fixture va test) `session` ga qulflandi — sessiya doirasidagi asyncpg engine bilan bir xil event loop kerak"
  - "testcontainers importi `testcontainers.community.postgres` dan (4.15 da `testcontainers.postgres` eskirgan)"
  - "`astral-sh/setup-uv` aynan `v9.0.0` relizga qulflandi — repo v8/v9 uchun ko'chuvchi major teg chiqarmaydi"
  - "`.gitattributes` bilan LF majburiy — Windows checkout CRLF bilan `.sh` faylni Linux konteynerida buzardi"

patterns-established:
  - "Pattern: RLS ishonchliligi rol atributlaridan boshlanadi — `NOSUPERUSER NOBYPASSRLS` va uni tekshiruvchi meta-test har fazada yashil turishi shart"
  - "Pattern: test fixture'lari ilova roli bilan ulanadi; superuser faqat bootstrap uchun (`superuser_url` testlarda ishlatilmaydi)"
  - "Pattern: konfiguratsiya sirlari faqat muhitdan — repoda `.env.example` da faqat kalit nomlari, `.dockerignore` `.env` ni image qatlamiga kiritmaydi"
  - "Pattern: har servis o'z `pyproject.toml` + `uv.lock` i bilan (aiogram pin konflikti uchun), umumiy kod `packages/sbozor-core` da editable"
  - "Pattern: healthcheck majburiy — `docker compose up --wait` `sleep` naqshini butunlay almashtiradi"

requirements-completed: [FOUND-02]

# Metrics
duration: 30min
completed: 2026-07-29
---

# Phase 1 Plan 01: Poydevor va Wave 0 test infratuzilmasi Summary

**Bitta buyruq (`npm run up`) bilan ko'tariladigan Compose steki, `NOSUPERUSER NOBYPASSRLS` ikki DB roli va haqiqiy `postgres:18.4-trixie` ga qarshi `sbozor_app` roli bilan ulanadigan pytest fixture'i — RLS bypass meta-testi bilan qulflangan.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-29T04:12:03Z
- **Completed:** 2026-07-29T04:42:15Z
- **Tasks:** 3/3
- **Files created:** 24

## Accomplishments

- **Tenant xavfsizligining poydevori birinchi kunda qo'yildi.** `sbozor_app` va `sbozor_owner` rollari `NOSUPERUSER NOBYPASSRLS` bilan yaratildi va bu holat `pg_roles` dan avtomatik tekshiriladi. RESEARCH Pitfall 2 empirik ko'rsatdiki, `FORCE ROW LEVEL SECURITY` superuser'ga ta'sir qilmaydi — endi bu yo'l strukturaviy yopiq.
- **Wave 0 test infratuzilmasi yashil.** `tests/conftest.py` haqiqiy `postgres:18.4-trixie` konteynerini ko'taradi, `ops/db/init/01-roles.sql` ni **verbatim** bajaradi (prod va test bir xil DDL'ni oladi) va `app_engine` ni `pool_size=1, max_overflow=0` bilan **`sbozor_app`** roliga ulaydi.
- **Fixture o'z-o'zini himoyalaydi.** `test_app_engine_connects_as_sbozor_app` ataylab `superuser_url` ga qaytarilganda **haqiqatan yiqilishi tekshirildi** (`app_engine 'test' bilan ulangan, 'sbozor_app' bilan emas`) — himoya ishlaydi, keyingi RLS ishi yolg'on-yashil bo'la olmaydi.
- **Stek uchdan-uchi ishlaydi.** Toza holatdan `npm run up` → `db`, `cache`, `core-api` uchalasi `healthy`; `/healthz` → `{"status":"ok"}`; `/readyz` → `{"status":"ok","checks":{"database":"ok","cache":"ok"}}` (ya'ni `sbozor_app` bilan DB'ga real ulanish tasdiqlandi).
- **Darvoza to'liq avtomatik.** `ruff check` + `ruff format --check` + `mypy` (strict) + `pytest` — hammasi yashil, va aynan shu zanjir CI quvurida ham ishlatiladi (mahalliy `uv run --project ...` ekvivalenti bilan tekshirildi).

## Task Commits

1. **Task 1: Repo ildizi, Compose steki va DB rollari** — `23ae7fd` (feat)
2. **Task 2: Python workspace — sbozor-core, core-api, Dockerfile, tool konfiguratsiyasi** — `7de8539` (feat)
3. **Task 3: Wave 0 test infratuzilmasi (TDD)**
   - `9c992ef` (test) — RED: 5 ta meta-test, fixture'siz yiqiladi
   - `3e9a0a5` (feat) — GREEN: `tests/conftest.py`, 5/5 yashil
   - `49095a4` (ci) — CI quvuri
4. **Grep-darvoza tuzatishi** — `652ca83` (docs)

## Files Created/Modified

**Orkestratsiya va infra**

- `compose.yaml` — db/cache/migrate/core-api/frontend/nginx/tests; `db` va `cache` xost portiga publish QILINMAYDI
- `compose.override.yml` — dev: portlar faqat `127.0.0.1` ga, core-api `dev` target + `--reload`
- `ops/db/init/01-roles.sql` — rol atributlari uchun **yagona haqiqat manbai**, idempotent, parolsiz
- `ops/db/init/02-passwords.sh` — parollarni env'dan `psql -v` + `:'var'` orqali o'rnatadi (injection'ga chidamli)
- `ops/nginx/nginx.conf` — bitta domen: `/api/` → core-api, `/` → frontend
- `package.json` — `up`/`down`/`logs`/`migrate`/`revision`/`test`/`test:unit`/`lint`/`fe:*`
- `.env.example` — faqat kalit nomlari; `JWT_SECRET` bo'sh + hosil qilish buyrug'i izohda
- `.gitignore`, `.gitattributes`, `.dockerignore`

**Python workspace**

- `pyproject.toml` (ildiz) — pytest/ruff/mypy konfiguratsiyasi, `[project]` bo'limi atayin yo'q
- `packages/sbozor-core/` — umumiy paket (hatchling), `__version__ = "0.1.0"`
- `services/core-api/pyproject.toml` + `uv.lock` — 75 paket, barcha versiyalar qulflangan
- `services/core-api/Dockerfile` — `python:3.13-slim-trixie`, uv 0.11.33, `dev`/`runtime` stage'lari, runtime non-root `appuser`
- `services/core-api/app/settings.py` — pydantic-settings, `JWT_SECRET >= 32 bayt` validatori
- `services/core-api/app/main.py` — `lifespan=`, `/healthz`, `/readyz`

**Testlar va CI**

- `tests/conftest.py` — `pg_container`, `superuser_url`, `owner_url`, `app_url`, `app_engine`, `sync_app_conn`, `_bootstrap_roles`; `TEST_DATABASE_URL` qochish yo'li
- `tests/tenancy/test_meta.py` — 5 ta rol invarianti
- `.github/workflows/ci-backend.yml` — ruff → format → mypy → pytest

## Decisions Made

- **Bitta domen topologiyasi** `ops/nginx/nginx.conf` da qat'iylashtirildi (RESEARCH Open Question 3). Bu 01-06 dagi `SameSite=Lax` + `Path=/api/v1/auth` yechimini oqlaydi.
- **Dev xost portlari `.env` orqali sozlanadi.** Default qiymatlar rejadagidek (5432/6379/8000/8080), lekin xostda band bo'lsa almashtiriladi. Bog'lanish interfeysi (`127.0.0.1`) hech qachon o'zgarmaydi — T-01-04 buzilmaydi.
- **testcontainers `community` importi** — 4.15 da eski yo'l `DeprecationWarning` beradi; API bir xil ekanligi tekshirildi.
- **`setup-uv` aynan `v9.0.0`** — repoda `v8`/`v9` ko'chuvchi major teglari yo'q (faqat `v1`..`v7`), shuning uchun reliz tegiga qulflandi. `actions/checkout@v7` — ko'chuvchi teg mavjudligi tasdiqlandi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dev xost portlari band edi**

- **Found during:** Task 1 (verify: `docker compose up -d db cache --wait`)
- **Issue:** Xostda 5432, 6379 va 8080 portlari boshqa jarayonlar tomonidan band (`netstat`: PID 7252, 7060, 4256). `compose.override.yml` dagi qat'iy `127.0.0.1:5432:5432` bind xatosi bilan yiqildi.
- **Fix:** Xost port raqamlari `${DB_HOST_PORT:-5432}` naqshiga o'tkazildi (cache/api/proxy uchun ham). Default qiymatlar rejadagidek qoldi; `.env.example` da ixtiyoriy override sifatida hujjatlashtirildi. Bog'lanish interfeysi `127.0.0.1` o'zgarmadi.
- **Files modified:** `compose.override.yml`, `compose.yaml`, `.env.example`
- **Verification:** `docker compose up -d db cache --wait` exit 0, ikkalasi `healthy`
- **Committed in:** `23ae7fd`

**2. [Rule 1 - Bug] postgres 18+ volume yo'li noto'g'ri edi**

- **Found during:** Task 1 (verify: db konteyneri `unhealthy`)
- **Issue:** `pgdata:/var/lib/postgresql/data` bilan konteyner ishga tushmaydi: `Error: in 18+, these Docker images are configured to store database data in a format which is compatible with "pg_ctlcluster" ... there appears to be PostgreSQL data in: /var/lib/postgresql/data (unused mount/volume)`. PG 18+ image'lari ma'lumotni `/var/lib/postgresql/18/docker` da saqlaydi.
- **Fix:** Volume `pgdata:/var/lib/postgresql` ga ko'chirildi, sababi izoh bilan yozildi.
- **Files modified:** `compose.yaml`
- **Verification:** Toza `down -v` dan keyin `up --wait` → `db` `healthy`, rollar yaratilgan
- **Committed in:** `23ae7fd`

**3. [Rule 2 - Missing Critical] `.gitattributes` yo'q edi (CRLF konteynerni buzardi)**

- **Found during:** Task 1 (staging: `warning: LF will be replaced by CRLF`)
- **Issue:** Xostda `core.autocrlf` faol. Toza clone'da `ops/db/init/02-passwords.sh` CRLF bilan checkout bo'ladi va Linux konteynerida `\r: not found` bilan yiqiladi — `docker-entrypoint-initdb.d` jimgina to'xtaydi va parollar o'rnatilmaydi.
- **Fix:** `.gitattributes` qo'shildi: `*.sh`, `*.sql`, `*.yaml/yml`, `*.conf`, `*.py`, `Dockerfile` va boshqalar uchun `eol=lf` majburiy. `02-passwords.sh` indeksda `100755` bilan belgilandi.
- **Files modified:** `.gitattributes`, `ops/db/init/02-passwords.sh` (rejim)
- **Verification:** `git ls-files -s` → `100755`; toza stekda `sbozor_app` o'z paroli bilan `psql` orqali kirdi
- **Committed in:** `23ae7fd`

**4. [Rule 2 - Missing Critical] Ildiz `.dockerignore` yo'q edi — `.env` image qatlamiga tushardi**

- **Found during:** Task 2 (Dockerfile `dev` stage'idagi `COPY . /app`)
- **Issue:** Reja `services/core-api/.dockerignore` ni ko'rsatadi, lekin BuildKit repo-ildizi konteksti uchun `<context>/.dockerignore` ni o'qiydi (yoki `<dockerfile>.dockerignore`). Ya'ni bu fayl **amalda ishlamas edi** va `dev` image ichiga `.env` (JWT_SECRET, DB parollari) baked bo'lardi.
- **Fix:** Ildizda `.dockerignore` yaratildi (amaldagi fayl); `services/core-api/.dockerignore` reja talab qilganidek saqlandi va izohda cheklov tushuntirildi.
- **Files modified:** `.dockerignore`, `services/core-api/.dockerignore`
- **Verification:** `dev` va `runtime` image'larida `test -f /app/.env` → yo'q
- **Committed in:** `7de8539`

**5. [Rule 3 - Blocking] mypy strict `Settings()` chaqiruvini rad etdi**

- **Found during:** Task 2 (verify: `mypy .`)
- **Issue:** `Missing named argument "database_url" / "valkey_url" / "jwt_secret" for "Settings"` — pydantic mypy plagini atayin yoqilmagan (reja `plugins = []` deydi), shuning uchun mypy muhitdan to'ldirishni ko'rmaydi.
- **Fix:** `get_settings()` da nuqtali `# type: ignore[call-arg]` + sababni tushuntiruvchi izoh.
- **Files modified:** `services/core-api/app/settings.py`
- **Verification:** `mypy .` → `Success: no issues found in 7 source files`
- **Committed in:** `7de8539`

**6. [Rule 3 - Blocking] pytest-asyncio loop scope sessiya doirasidagi engine bilan mos emas edi**

- **Found during:** Task 3 (GREEN: `app_engine` sessiya fixture'i)
- **Issue:** `asyncio_mode = "auto"` yolg'iz o'zi fixture'lar uchun funksiya doirasidagi event loop beradi; sessiya doirasidagi asyncpg engine boshqa loop'ga bog'lanib qolardi.
- **Fix:** `asyncio_default_fixture_loop_scope = "session"` va `asyncio_default_test_loop_scope = "session"` qo'shildi (izoh bilan).
- **Files modified:** `pyproject.toml`
- **Verification:** `pytest tests/tenancy -x -q` → 5/5 yashil, ogohlantirishsiz
- **Committed in:** `3e9a0a5`

**7. [Rule 1 - Bug] Taqiqlangan texnologiya izohlari grep-darvozani yiqitardi**

- **Found during:** Yakuniy `must_haves` tekshiruvi
- **Issue:** Qabul mezonlari literal grep: "`tests/conftest.py` da `sqlite` yo'q", "`Dockerfile` da `alpine` yo'q". Mening TAQIQ izohlarim aynan shu so'zlarni o'z ichiga olardi → yolg'on-musbat.
- **Fix:** Ikkala izoh ham ma'nosini saqlagan holda, trigger so'zlarsiz qayta yozildi.
- **Files modified:** `tests/conftest.py`, `services/core-api/Dockerfile`
- **Verification:** `grep -ic sqlite tests/conftest.py` → 0; `grep -ic alpine services/core-api/Dockerfile` → 0; to'liq darvoza qayta yashil
- **Committed in:** `652ca83`

---

**Total deviations:** 7 auto-fixed — 2× Rule 1 (bug: #2 postgres volume, #7 grep darvozasi), 2× Rule 2 (missing critical: #3 `.gitattributes`, #4 ildiz `.dockerignore`), 3× Rule 3 (blocking: #1 band portlar, #5 mypy, #6 asyncio loop scope).
**Impact on plan:** Hech qanday scope creep yo'q. Ikkitasi (#3 va #4) xavfsizlik/korrektlik teshigini yopdi (sir sizishi va jimgina buziladigan entrypoint), qolganlari muhit va vosita darajasidagi bloklovchilar edi. Rejaning barcha qabul mezonlari o'zgarishsiz bajarildi.

## Issues Encountered

- **`uv` xostda yo'q** (RESEARCH da qayd etilgan). `uv.lock` bir martalik `python:3.13-slim-trixie` konteynerida (`pip install uv==0.11.33 && uv lock`) hosil qilindi — xost muhiti iflos qilinmadi, RESEARCH ning (b) tavsiyasiga mos.
- **`docker compose --wait` va healthcheck.** `sleep` naqshi umuman ishlatilmadi; uchala servisda healthcheck bor, shuning uchun verify buyruqlari flaky emas.
- **GitHub Action teglari empirik tekshirildi** (`api.github.com`), taxmin qilinmadi: `setup-uv` uchun `v9` ko'chuvchi teg **mavjud emas**, shuning uchun `v9.0.0`.

## Known Stubs

Yo'q. Bu rejada yaratilgan hamma narsa ishlaydi va tekshirildi. Rejada atayin keyingi rejalarga qoldirilgan (stub emas, hali yo'q) qismlar:

- `frontend/Dockerfile` — 01-02 rejasi yaratadi; shuning uchun `frontend` servisi `profiles: ["web"]` ortida (default `up` ni buzmaydi).
- `packages/sbozor-core/` modullari (`models`, `tenancy`, `security`, `money`, `timeutil`) — 01-03.
- Alembic konfiguratsiyasi va migratsiyalar — 01-04 (`migrate` profili va `owner_url` fixture'i tayyor kutmoqda).
- `tests/tenancy/test_meta.py` dagi **sxema** invariantlari (har jadvalda `market_id`, RLS ENABLE+FORCE, policy) — 01-04, chunki hozircha jadvallar yo'q. Fayl izohida bu aniq yozilgan.

## Threat Flags

Yo'q — bu rejada `<threat_model>` da qayd etilmagan yangi xavfsizlik yuzasi paydo bo'lmadi. Registrdagi 8 ta dispozitsiya (`T-01-01`, `-02`, `-03`, `-04`, `-05`, `-06`, `-07`, `-SC`) amalga oshirildi:

| Threat  | Qanday yopildi                                                                | Tekshiruv                                     |
| ------- | ----------------------------------------------------------------------------- | --------------------------------------------- |
| T-01-01 | `01-roles.sql`: `NOSUPERUSER NOBYPASSRLS`                                      | `test_app_role_cannot_bypass_rls`             |
| T-01-02 | `app_engine` `sbozor_app` bilan ulanadi                                        | `test_app_engine_connects_as_sbozor_app` (sabotaj bilan sinaldi) |
| T-01-03 | `.env.example` da faqat kalit nomlari; `.gitignore` + `.dockerignore` `.env` ni bloklaydi | `git check-ignore .env`; image'da `.env` yo'q  |
| T-01-04 | `compose.yaml` da `db`/`cache` uchun `ports:` yo'q; override faqat `127.0.0.1` | `docker compose config`                       |
| T-01-05 | `session_replication_role` ilova roliga yopiq                                  | `test_app_cannot_disable_triggers`            |
| T-01-06 | `REVOKE CREATE ON SCHEMA public FROM PUBLIC`                                    | `test_public_schema_create_revoked_from_public` |
| T-01-07 | `runtime` stage non-root `appuser` (uid 10001)                                 | `docker run ... id -un` → `appuser`           |
| T-01-SC | Barcha versiyalar qulflangan, `uv.lock` commit qilingan                        | `uv sync --frozen` build'da                   |

## User Setup Required

Yo'q — tashqi servis konfiguratsiyasi talab qilinmaydi. Ishlab chiquvchi uchun yagona qadam:

```
cp .env.example .env
# JWT_SECRET ni to'ldiring:
#   python -c "import secrets;print(secrets.token_urlsafe(48))"
# POSTGRES_PASSWORD / SBOZOR_OWNER_PASSWORD / SBOZOR_APP_PASSWORD ni to'ldiring
# (agar xostda 5432/6379/8000 band bo'lsa, DB_HOST_PORT/... ni o'zgartiring)
npm run up
```

## Next Phase Readiness

**Tayyor:**

- 01-02 (frontend): `compose.yaml` da `frontend` servisi va `web` profili, `NEXT_PUBLIC_API_BASE_URL`, nginx marshrutlari kutmoqda.
- 01-03 (sbozor-core modullari): paket, editable install va bog'liqliklar (sqlalchemy, pydantic, pyjwt, pwdlib, phonenumbers, structlog, tzdata) o'rnatilgan.
- 01-04 (Alembic + RLS): `migrate` profili, `MIGRATION_DATABASE_URL`, `owner_url`/`app_engine` fixture'lari va bo'sh `test_meta.py` sxema bo'limi kutmoqda. `alembic-utils` 0.8.8 o'rnatilgan va import bo'ladi (A9 autogenerate tekshiruvi 01-04 Task 1 da).
- 01-05..01-10: har qanday RLS/audit da'vosi endi `sbozor_app` roli ostida isbotlanadi.

**Ochiq e'tibor nuqtalari:**

- `services/core-api/.dockerignore` amalda ishlatilmaydi (BuildKit ildiz konteksti uchun `/.dockerignore` ni o'qiydi). Ikkalasi qo'lda sinxron ushlab turilishi kerak — kelajakda bittasini olib tashlash mumkin.
- `mypy strict` `Settings()` uchun bitta `type: ignore` talab qiladi. Agar keyinchalik pydantic mypy plagini yoqilsa, uni olib tashlash kerak bo'ladi.
- `.github/workflows/ci-backend.yml` haqiqiy GitHub runner'ida hali ishlamadi (repo remote'ga push qilinmagan) — mahalliy ekvivalent zanjir yashil, lekin birinchi CI ishga tushishi kuzatilishi kerak.

## Self-Check: PASSED

- **Fayllar:** da'vo qilingan 24 ta artefaktning hammasi mavjud va git'da kuzatilmoqda (`git ls-files`).
- **Commitlar:** `23ae7fd`, `7de8539`, `9c992ef`, `3e9a0a5`, `49095a4`, `652ca83` — hammasi `git log` da mavjud (shu SUMMARY o'zi yettinchi commit).
- **O'chirilgan fayl yo'q:** `git diff --diff-filter=D 247e8e8..HEAD` bo'sh.
- **Ishchi katalog toza:** `git status --short` bo'sh; `.env` kuzatilmaydi (`git check-ignore .env` → `.gitignore:2`).
- **Darvozalar:** `ruff check` + `ruff format --check` + `mypy` (strict) + `pytest` — 5/5 test yashil.

---

_Phase: 01-poydevor-va-tenant-xavfsizligi_
_Completed: 2026-07-29_
