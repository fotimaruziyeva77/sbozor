---
phase: 04-snapshot-pipeline
plan: 01
subsystem: infra
tags: [aiobotocore, pillow, seaweedfs, taskiq, docker-compose, postgres, rls, generated-columns, s3]

requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`taskiq` brokeri va `worker` konteyneri (profilsiz naqsh), `httpx` ning prod guruhiga ko'chirilishi (D-16 epizodi), `market_delete_draft()` kaskadining `pg_catalog` to'liqlik darvozasi, `cameras` jadvali (kompozit FK nishoni)"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`AUDITED_TABLES` reyestri va `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi, `INDEX_EXCEPTIONS` naqshi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`GENERATED STORED` + `UNIQUE` DDL yo'li (`financial_guard_statements`), probe-jadval shabloni, tenancy meta-darvozalari"
provides:
  - "`aiobotocore==3.9.0` va `Pillow==12.3.0` — ishlab chiqarish bog'liqliklari (HAQIQIY `--no-dev` image'da o'lchangan)"
  - "`storage` (SeaweedFS 4.40) konteyneri — profilsiz, `ports:` siz, `nc -z` healthcheck bilan"
  - "`scheduler` (taskiq scheduler) konteyneri — profilsiz, soxta healthchecksiz"
  - "`ops/seaweedfs/s3.json.example` + README — bitta identity, `anonymous`/`Admin` yo'q, parser-darvoza ostida"
  - "D-23 O'LCHOVI: `BILLABLE_ANCHOR_SUPPORTED = true` — `0014` D-16 ning tuzilmaviy shaklida yoziladi"
  - "`SNAPSHOT_TENANT_TABLES` / `SNAPSHOT_AUDITED_TABLES` / `SNAPSHOT_DELETE_ORDER` reyestrlari"
  - "`markets.timezone` invarianti va `ix_capture_runs_overdue` indeks istisnosi"
  - "`tests/fixtures/billable_probe.py` — kelajakdagi generated-ustun/FK savollari uchun zond shabloni"
affects: [04-03, 04-04, 04-06, 04-07, 04-08, 04-12, 05-cv-zonalar, 06-billing]

tech-stack:
  added: ["aiobotocore 3.9.0", "Pillow 12.3.0", "chrislusf/seaweedfs:4.40"]
  patterns:
    - "O'zi qurollanadigan reyestr darvozasi: shart BAZAGA bog'lanadi, ya'ni qarz jadval tug'ilgan zahoti avtomatik qizaradi"
    - "Wave 0 zondi: mavjud bo'lmagan jadvalning DDL yo'lini probe bilan oldindan o'lchash (financial.py naqshining kengaytmasi)"
    - "Konfiguratsiya darvozasi `json.loads` bilan (grep emas) — kalit nomini matn ichidagi tasodifiy uchrashuvdan ajratadi"

key-files:
  created:
    - ops/seaweedfs/s3.json.example
    - ops/seaweedfs/README.md
    - tests/unit/test_storage_config.py
    - tests/fixtures/billable_probe.py
    - tests/tenancy/test_billable_anchor_probe.py
  modified:
    - compose.yaml
    - services/core-api/pyproject.toml
    - services/core-api/uv.lock
    - migrations/entities/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - tests/tenancy/test_meta.py
    - tests/unit/test_runtime_deps.py
    - .env.example
    - .gitignore
    - package.json

key-decisions:
  - "D-23 O'LCHANDI: `GENERATED STORED` ustunning UNIQUE'i kompozit FK NISHONI bo'la OLADI (postgres:18.4) -> `0014` trigger variantida EMAS, tuzilmaviy shaklda yoziladi"
  - "`alert_events` — GLOBAL emas, TENANT jadvali (`market_id NOT NULL`); `GLOBAL_TABLES` ga faqat `system_heartbeats` qo'shildi"
  - "`SNAPSHOT_TENANT_TABLES` `ALL_TENANT_TABLES` ga BU REJADA qo'shilmadi — `alembic_utils` komparatori policy'ni haqiqatan yaratib ko'radi va `UndefinedTable` beradi; qo'shish `0014` bilan bir oynada (04-03/T2), tetigi mexanik"
  - "`scheduler` konteyneri ta'rifi koddan OLDIN yozildi (profilsizlikni qulflash uchun), lekin `app.worker:scheduler` obyekti 04-07 da tug'iladi — shuning uchun `up --wait scheduler` 04-07 gacha ishlamaydi va bu compose izohida yozildi"
  - "`scheduler` ga healthcheck ATAYIN yozilmadi — jarayon tirikligi «tik ketyaptimi?» savoliga javob bermaydi"

patterns-established:
  - "O'zi qurollanadigan darvoza: `born = set(REGISTRY) & set(pg_class)` — bugun yashil, jadval tug'ilgan kuni qizil"
  - "Zond ikki DDL'ni ALOHIDA bajaradi, aks holda ota-jadvalning muvaffaqiyati bola-jadvalning nosozligi bilan bir tranzaksiyada yo'qoladi"
  - "Prod bog'liqlik da'vosi FAYLDAN emas, `git archive HEAD` dan qurilgan `--no-dev` image'dan o'lchanadi (3-fazadagi `httpx` metodikasi)"

requirements-completed: [CAM-05, CAM-06, CAM-07, FOUND-06]

duration: 4h 10m
completed: 2026-08-04
---

# Phase 4 Plan 01: Wave 0 poydevori Summary

**`aiobotocore`/`Pillow` prod guruhiga ko'chirildi va HAQIQIY `--no-dev` image'da o'lchandi, `storage` (SeaweedFS) hamda `scheduler` konteynerlari profilsiz qo'shildi, `s3.json` ning `anonymous` tuzog'i parser-darvoza bilan yopildi, va D-23 o'lchandi: `GENERATED STORED` ustun kompozit FK NISHONI bo'la OLADI — ya'ni `0014` D-16 ning tuzilmaviy shaklida yoziladi.**

## Performance

- **Duration:** ~4h 10m
- **Tasks:** 3/3
- **Files modified:** 16 (5 yangi, 11 o'zgartirilgan)
- **Commits:** 4 ta task commiti (biri TDD juftligi) + 1 metadata

## Accomplishments

- **W0-2 (🔇 jimgina yiqiladigan) yopildi va O'LCHANDI.** Fayldagi o'zgarish yetarli deb hisoblanmadi: `git archive HEAD` dan alohida `--no-dev` runtime image qurilib, `import aiobotocore` -> `ModuleNotFoundError` bo'lishi tasdiqlandi, o'zgarishdan keyin esa `3.9.0`/`12.3.0` o'qildi. Ikkala image ham HAQIQATAN `--no-dev` ekani `pytest`/`ruff` ning yo'qligi bilan alohida tekshirildi — 3-fazada birinchi zond aynan shu tekshiruvsiz yolg'on signal bergan edi.
- **W0-3 va W0-4 (🔇) yopildi.** `scheduler` va `storage` **profilsiz**; `storage` da `ports:` yo'q va `PublishedPort: 0` bilan tasdiqlandi; `scheduler` da soxta `healthcheck` yozilmadi.
- **T-04-01 mitigatsiyasi FAYLDAN EMAS, TIRIK OMBORDAN o'lchandi:** `anonymous` yozuvsiz `s3.json` bilan ishlayotgan SeaweedFS anonim `GET` va `PUT` ga **`403 AccessDenied`** qaytaradi.
- **W0-1 / D-23 O'LCHANDI** — natija pastda, `0014` shu satrdan o'z shaklini oladi.
- **W0-5/6/7/8 yopildi** va `PENDING_AUDIT_TRIGGERS` ikki tomonlama qulfi **ikkala yo'nalishda ham** o'lchandi (`closed` va `regressed`).
- **Rejalararo ziddiyat topildi va o'lchov bilan hal qilindi:** `ALL_TENANT_TABLES` ni bugun kengaytirish `test_autogenerate_is_empty` ni yiqitardi (pastda, «Deviations» §2).

## D-23 O'LCHOV NATIJASI — `04-03` SHU SATRNI O'QIYDI

```
BILLABLE_ANCHOR_SUPPORTED = true
server_version = PostgreSQL 18.4 (Debian 18.4-1.pgdg13+1) on x86_64-pc-linux-gnu,
                 compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit
failure        = None
```

**Ma'nosi:** `GENERATED ALWAYS AS (quality_verdict = 'ok') STORED` ustun ustidagi
`UNIQUE (id, is_billable)` kompozit FK ning **NISHONI bo'la oladi**. Ya'ni:

- `0014` da `snapshots.is_billable` **`GENERATED ... STORED`** bo'lib qoladi;
- **`BEFORE INSERT/UPDATE` trigger varianti KERAK EMAS** (~15 qator tejaldi);
- D-16 ning billing kafolati **TUZILMAVIY** bo'ladi, kelishuv emas.

Zond kafolatning ikkala yo'nalishini ham o'lchadi: `quality_verdict='dark'`
qatorga havola `ForeignKeyViolation` beradi, **va** mavjud `'ok'` qatorni
`'dark'` ga `UPDATE` qilish ham rad etiladi — ya'ni kafolat faqat `INSERT`
paytida emas, hukm o'zgarganda ham ishlaydi.

## Task Commits

1. **Task 1: W0-2/3/4/11 — prod bog'liqliklari, `scheduler`/`storage`, `s3.json` darvozasi** — `8c35843` (feat)
2. **Task 2: W0-1 (D-23) zondi** — `91d215c` (test, RED) → `5ae3fd2` (feat, GREEN)
3. **Task 3: W0-5/6/7/8 — reyestrlar, kaskad tartibi, invariantlar** — `e1a711e` (feat)

**Plan metadata:** quyidagi `docs(04-01)` commiti.

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `services/core-api/pyproject.toml` | `aiobotocore==3.9.0` + `Pillow==12.3.0` prod guruhida; `aioboto3`/`opencv` nega yo'qligi izohda |
| `services/core-api/uv.lock` | Qayta hal qilindi (`redis` 8.0.1 da QOLDI, `boto3` tortilmadi) |
| `compose.yaml` | `storage` va `scheduler` (ikkalasi profilsiz), S3/Telegram env, `seaweed` volume |
| `package.json` | `up` -> `storage`+`scheduler`; `sim:up`/`sim:down` -> `storage` |
| `.env.example` | Fazaning 17 yangi kaliti sabab-izohi bilan |
| `.gitignore` | `ops/seaweedfs/s3.json` (sirlar repoga tushmaydi) |
| `ops/seaweedfs/s3.json.example` | Bitta identity, bucketga qadalgan huquqlar, `anonymous`/`Admin` yo'q |
| `ops/seaweedfs/README.md` | `anonymous` tuzog'i, `cp .example`, bucket yaratish, nega SeaweedFS |
| `tests/unit/test_runtime_deps.py` | +2 majburiy paket, +7 taqiqlangan paket (`FORBIDDEN_PACKAGES`) |
| `tests/unit/test_storage_config.py` | 9 test: `s3.json` parseri (4) + compose shakli (5) |
| `tests/fixtures/billable_probe.py` | D-23 zondi — ikki probe jadvali, DDL alohida bajariladi |
| `tests/tenancy/test_billable_anchor_probe.py` | Nazorat holati + O'LCHOV + D-16 kafolatining ikki yo'nalishi |
| `migrations/entities/__init__.py` | Uch yangi reyestr (`SNAPSHOT_*`) sabab-docstringlari bilan |
| `migrations/entities/functions.py` | FAQAT docstring — `MARKET_DELETE_DRAFT` tanasi TEGILMADI |
| `packages/sbozor-core/.../schema_contract.py` | `AUDITED_TABLES` +2, `GLOBAL_TABLES` +`system_heartbeats`, chiqarilganlar sababi |
| `tests/tenancy/test_meta.py` | `PENDING_AUDIT_TRIGGERS` +2, `INDEX_EXCEPTIONS` +1, 2 yangi test |

## Sabotaj o'lchovlari — nima qizardi VA nima YASHIL QOLDI

Bu loyihada ikkinchi ustun birinchisidan ko'ra ko'proq ma'lumot bergan.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Xulosa |
|---|---|---|---|---|
| 1 | `s3.json.example` ga `{"name":"anonymous","actions":["Read"]}` | `test_storage_config.py` — **3 ta** test (`exactly_one_identity`, `no_anonymous_identity`, `every_action_is_scoped`), xato matnida `anonymous` so'zma-so'z | `test_runtime_deps.py` (25/25) | Ikki darvoza mustaqil; `anonymous` uch qatlamdan birdan tutiladi |
| 2 | `_CREATE_PARENT` da `UNIQUE (id, is_billable)` -> `UNIQUE (id)` | `test_generated_stored_column_can_be_unique` **va** `..._composite_fk_target`; ikkinchisi PG ning aniq xatosini chiqardi: `InvalidForeignKey: there is no unique constraint matching given keys for referenced table "probe_snapshots"` | `test_meta.py` (25/25); uchinchi test **`skip`** bo'ldi (`fail` emas) | Zond meta-darvozalardan mustaqil o'lchaydi; `skip` yo'li ham ishlaydi va sabab matni `0014` ga yo'l ko'rsatadi |
| 3 | `PENDING_AUDIT_TRIGGERS` dan `snapshot_schedule_slots` olib tashlandi | `test_audited_tables_have_trigger` — AYNAN `regressed` assertida, nom xabarda | Qolgan 26 test, jumladan `test_markets_all_use_tashkent_timezone` | Ikki tomonlama qulfning **birinchi** yo'nalishi o'lchandi |
| 4 | (RED bosqichi) reyestrga qo'shishdan OLDIN `PENDING_AUDIT_TRIGGERS` to'ldirildi | `test_audited_tables_have_trigger` — AYNAN `closed` assertida | Qolgan testlar | Ikki tomonlama qulfning **ikkinchi** yo'nalishi o'lchandi. ⚠ Kuzatuv: `closed` assertining matni («audit triggeri ULANGAN») bu stsenariyda **noaniq** — trigger ulanmagan, jadval shunchaki `AUDITED_TABLES` da yo'q. Holat o'tkinchi (bir commitda yopiladi), shuning uchun 2-faza kodiga tegilmadi |
| 5 | `SNAPSHOT_DELETE_ORDER` dan `alert_events` olib tashlandi | `test_snapshot_registries_are_self_consistent` — `Extra items in the right set: 'alert_events'` | `test_meta.py` ning qolgani; `test_market_delete_guard.py` (u hali mavjud bo'lmagan jadvallarni ko'rmaydi) | Reyestr darvozasi meta-darvozadan mustaqil |
| 6 | `SNAPSHOT_TENANT_TABLES` da `alert_events` -> `audit_log` (bazada MAVJUD jadval) | `test_snapshot_registries_are_self_consistent` — `jadval BAZADA bor, lekin ALL_TENANT_TABLES da yo'q: ['audit_log']` | Qolgan testlar | **O'zi qurollanadigan darvoza ishlaydi:** `0014` jadvallarni yaratgan kuni `04-03` reyestrni kengaytirmasa CI qizaradi |

## Darvoza o'lchovlari (`04-VALIDATION.md` 1-qadami)

| # | Holat | `npm run gate` | Exit |
|---|---|---|---|
| 1 | **sovuq** (`.next` yo'q, `node_modules` yangi) | **490 s** | 0 |
| 2 | issiq | **466 s** | 0 |
| 3 | issiq | **461 s** | 0 |

`npm run gate:fast` — **49 s** (chegara **180 s**, 3.7× zaxira; chegara **o'zgartirilmadi**).

⚠ **Chegara bu rejada JIMGINA HAM O'ZGARTIRILMADI, JIMGINA HAM QOLDIRILMADI.**
Uchala qiymat 3-fazaning 538 s bazasidan past (461–490 s) bo'lsa-da, chegara
1200 s da qoladi: bitta seansda olingan bitta seriya chegarani qayta belgilash
uchun yetarli emas va `04-VALIDATION.md` ning o'zi buni ikki bosqichli qilib
belgilagan. Qaror `04-12` da, olti o'lchov asosida. Sabab `04-VALIDATION.md` ga
ham yozildi.

⚠ **O'lchov sharti halol yozildi:** bu qiymatlar `storage` ning narxini o'z
ichiga oladi, `scheduler` ning narxini **emas** (u `gate` zanjirida ishga
tushirilmaydi — pastdagi 1-deviatsiya).

## Bazaviy holat

| O'lchov | Baza | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1520 | **1544** | ✅ +24 |
| tenancy | 412 | **417** | ✅ +5 |
| vitest | 246 | **246** | ✅ |
| node gates | 86 | **86** | ✅ |
| i18n | 576×3 | **576×3** | ✅ |
| `ruff` + `ruff format` + `mypy` | toza | **toza** (199 fayl) | ✅ |

## Decisions Made

1. **D-23 natijasi `0014` ning shaklini belgiladi** — yuqoridagi bo'limga qarang.
2. **`alert_events` — TENANT jadvali.** `04-RESEARCH.md` §E.13 uni `GLOBAL_TABLES` deb atagan, lekin o'sha yerdayoq unga `market_id` bergan; `GLOBAL_TABLES` ning ta'rifi esa «`market_id` ustuni **BO'LMASLIGI** kutilgan jadvallar». Ikkisi bir vaqtda to'g'ri bo'la olmaydi. `04-PATTERNS.md` §S-1 tanlandi (UI ogohlantirishlarni bozor sahifasida ko'rsatadi). `GLOBAL_TABLES` ga faqat `system_heartbeats` qo'shildi.
3. **`scheduler` ta'rifi koddan oldin yozildi.** W0-3 ning butun mazmuni — profilsizlikni migratsiyadan va koddan **oldin** qulflash. Narxi: `docker compose up scheduler` `04-07` gacha import xatosi beradi, va bu compose izohida hamda testda ochiq yozildi.
4. **`scheduler` ga healthcheck yozilmadi.** `pgrep`/`CMD true` kabi tekshiruv «konteyner Up, hech nima bajarilmayapti» holatini **sog'lom** deb belgilab, yolg'on ishonch berardi (3-fazada o'lchangan sinf). Buni `test_scheduler_has_no_fake_healthcheck` qulfladi, `storage` da healthcheck **borligi** esa nazorat holati sifatida tekshiriladi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `docker compose up -d --wait scheduler` qabul mezoni bajarib bo'lmaydigan shaklda yozilgan edi**
- **Found during:** Task 1
- **Issue:** Reja `scheduler` uchun `command: ["taskiq","scheduler","app.worker:scheduler"]` ni talab qiladi va `docker compose up -d --wait db cache storage scheduler` exit 0 bo'lishini kutadi. Lekin `app.worker:scheduler` obyekti **mavjud emas** — u `04-07`/T3 da tug'iladi (`services/core-api/app/worker.py` o'sha rejaning fayli va bu rejaning `files_modified` ida YO'Q). Konteyner ko'tarilsa `ImportError` bilan restart tsikliga tushardi.
- **Fix:** Bandning **niyati** bajarildi, harfi emas. `storage` HAQIQATAN ko'tarildi va `healthy` bo'ldi; `scheduler` ning profilsizligi, `command` i, `healthcheck` yo'qligi va `ports` yo'qligi `docker compose config --format json` dan o'lchandi. Bundan tashqari niyat **doimiy darvozaga** aylantirildi: `test_storage_config.py::test_production_service_has_no_profile` (parametrlangan: `storage`+`scheduler`) va `test_scheduler_has_no_fake_healthcheck`. `docker compose up --wait scheduler` `04-07` ning O'Z qabul mezonida allaqachon turibdi.
- **Verification:** `docker compose config --format json` -> `scheduler.profiles = None`, `storage.profiles = None`, `storage.ports` yo'q; `docker compose ps storage` -> `healthy`, `PublishedPort: 0`.
- **Committed in:** `8c35843`

**2. [Rule 1 - Bug] `ALL_TENANT_TABLES` ni bugun kengaytirish `test_autogenerate_is_empty` ni yiqitadi**
- **Found during:** Task 3
- **Issue:** Reja `ALL_TENANT_TABLES` ga `*SNAPSHOT_TENANT_TABLES` qo'shishni talab qiladi. Bajarilgach `pytest tests/tenancy` qizardi:
  ```
  sqlalchemy.exc.ProgrammingError: (psycopg.errors.UndefinedTable)
  relation "public.snapshot_schedules" does not exist
  [SQL: CREATE POLICY tenant_isolation on public.snapshot_schedules ...]
  ```
  Sabab: `ALL_ENTITIES` aynan `ALL_TENANT_TABLES` dan quriladi, `alembic_utils` ning komparatori esa har bir entity'ni **haqiqatan yaratib ko'radi** (`simulate_entity`). Buni `test_market_domain_meta.py::test_autogenerate_is_empty` ning **o'z docstringi** oldindan aytgan: «⚠ REYESTR BO'SHATISHNI QAYTA TIKLAMANG... To'g'ri yechim — migratsiyani YOZISH». Migratsiya (`0014`) esa `04-03` ning ishi, boshqa to'lqinda.
- **Fix:** Uch yangi reyestr (`SNAPSHOT_TENANT_TABLES`, `SNAPSHOT_AUDITED_TABLES`, `SNAPSHOT_DELETE_ORDER`) yozildi — ya'ni W0-5/W0-6 ning butun niyati (kaskad tartibi va audit ro'yxati migratsiyadan **oldin** qog'ozda) bajarildi. `ALL_TENANT_TABLES` ga splice `0014` bilan bir oynaga (`04-03`/T2) qoldirildi va sabab o'sha konstantaning yonida o'lchov matni bilan yozildi. Qarz **mexanik tetik** oldi: `test_snapshot_registries_are_self_consistent` shartni bazaga bog'laydi (`born = set(SNAPSHOT_TENANT_TABLES) & pg_class`) — bugun yashil, `0014` qo'ngan kuni `04-03` ro'yxatni kengaytirmaguncha qizil.
- **Precedent:** 3-fazada `NVR_TENANT_TABLES` `ALL_TENANT_TABLES` ga **`0012` bilan bir rejada** (03-03) qo'shilgan, Wave 0 da emas. 4-fazada `0014` boshqa **to'lqinda**, ya'ni bu yerda qo'shish darvozani to'lqinlar **orasida** qizil qoldirardi — bu esa `PENDING_AUDIT_TRIGGERS` docstringi taqiqlagan holatning o'zi («Buzilgan darvoza — darvoza emas»).
- **Verification:** `pytest tests/tenancy` 417/417 yashil; 6-sabotaj tetikning ishlashini o'lchadi.
- **Committed in:** `e1a711e`

**3. [Rule 3 - Blocking] `services/core-api/uv.lock` qayta hal qilindi**
- **Found during:** Task 1
- **Issue:** `uv.lock` reja fayllarida yo'q, lekin `Dockerfile` `uv sync --frozen` ishlatadi — lock yangilanmasa **hamma docker build** yiqilardi.
- **Fix:** `ghcr.io/astral-sh/uv:0.11.33-python3.13-trixie-slim` konteynerida `uv lock --project services/core-api`.
- **Verification:** `redis` **8.0.1 da qoldi** (`arq`/`aioboto3` sinfidagi pasaytirish sodir bo'lmadi), `boto3` umuman tortilmadi, faqat `botocore`/`jmespath`/`aioitertools`/`python-dateutil`/`six`/`pillow` qo'shildi. Runtime image'da ham `redis 8.0.1` o'qildi.
- **Committed in:** `8c35843`

**4. [Rule 2 - Missing Critical] `.gitignore` ga `ops/seaweedfs/s3.json`**
- **Found during:** Task 1
- **Issue:** Reja `compose.yaml` da `./ops/seaweedfs/s3.json` ni mount qilishni va repoda faqat `.example` qolishini talab qiladi (threat model: «`git` repozitoriysi → S3 sirlari»). Lekin `.gitignore` reja fayllarida yo'q edi — ya'ni haqiqiy, sirli fayl birinchi `git add` da repoga tushib ketardi.
- **Fix:** `.gitignore` ning «Sirlar» bo'limiga bitta qator + sabab (SeaweedFS `s3.json` ichida muhit o'zgaruvchisini **interpolatsiya qilmaydi**, ya'ni kalitlar faylga literal yoziladi).
- **Verification:** `git check-ignore -v ops/seaweedfs/s3.json` -> `.gitignore:10`.
- **Committed in:** `8c35843`

**5. [Rule 1 - Bug] `ops/seaweedfs/README.md` dagi bucket yaratish buyrug'i ishlamasdi**
- **Found during:** Task 1 (verifikatsiya paytida bajarib ko'rilganda)
- **Issue:** `weed shell -c "s3.bucket.create ..."` — SeaweedFS 4.40 da `-c` bayrog'i **yo'q**; buyruq o'rniga yordam matni chiqadi va **xato kodi ham qaytmaydi**. Yo'riqnomaga ergashgan operator «bajarildi» deb o'ylab, bucketsiz qolardi.
- **Fix:** `printf 's3.bucket.create -name sbozor-snapshots\n' | docker compose exec -T storage weed shell` shakliga o'zgartirildi va noto'g'ri shaklning **nega ishlamasligi** ogohlantirish sifatida yozildi.
- **Verification:** Buyruq bajarildi -> `created bucket sbozor-snapshots`; `s3.bucket.list` -> `sbozor-snapshots size:0`.
- **Committed in:** `8c35843`

**6. [Rule 2 - Missing Critical] `test_storage_config.py` ga compose profil/healthcheck darvozalari qo'shildi**
- **Found during:** Task 1
- **Issue:** Reja bu faylga 5 test bergan (4 ta `s3.json` + 1 ta `ports`). W0-3 ning o'zi (profilsizlik) esa faqat bir martalik `docker compose config` chaqiruvi bilan tekshirilardi — bir martalik chaqiruv darvoza emas, ya'ni kimdir keyinroq `profiles: ["prod"]` qo'shsa hech nima sezmasdi.
- **Fix:** +3 test: `test_production_service_has_no_profile` (parametrlangan), `test_scheduler_has_no_fake_healthcheck`, `test_compose_parser_actually_sees_the_services` (quyi chegara + nazorat qiymatlari — `nginx` da `ports` va `nvr-sim` da `profiles` topilishi shart, aks holda parser buzilganda hamma «yo'q» da'vosi jimgina rost bo'lardi).
- **Verification:** 9/9 yashil; parser `PyYAML` siz (yangi bog'liqlik qo'shilmadi).
- **Committed in:** `8c35843`

**7. [Rule 1 - Bug] `04-VALIDATION.md` dagi ikki fakt noto'g'ri edi**
- **Found during:** Yakuniy verifikatsiya
- **Issue:** (a) W0-5 bandi «`test_audited_tables_have_trigger` vaqtincha qizil turadi — bu **kutilgan**» deydi. Bu **noto'g'ri**: test `not missing` ni emas, `missing == PENDING_AUDIT_TRIGGERS` **tengligini** tekshiradi, ya'ni to'g'ri qurilganda darvoza yashil qoladi. Bu matnga ergashgan ijrochi qizil testni «normal» deb qoldirardi va `04-01`→`04-03` oralig'ida darvoza signal bermay qolardi. (b) W0-6 bandi «beshta jadval» deb yozib, tartibda **to'rttasini** sanaydi (`alert_events` yo'q) va blokning NVR blokidan oldin turishi shartini aytmaydi.
- **Fix:** Ikkala band ham tuzatildi, tuzatish sababi bilan belgilandi va to'liq tartib `SNAPSHOT_DELETE_ORDER` ga havola qilindi.
- **Verification:** `node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md` -> 04-01 qatorlari yashil deb tanildi.
- **Committed in:** metadata commiti

**8. [Rule 3 - Blocking] `tests/tenancy/test_meta.py` da ruff `S608` yolg'on-musbati**
- **Found during:** Task 3
- **Issue:** Yangi assert xabarida `DELETE FROM markets` iborasi bor edi va ruff uni «string-based query construction» deb belgiladi.
- **Fix:** `test_market_delete_guard.py::CASCADE_FIX_HINT` da o'rnatilgan naqsh: matn f-satrsiz modul-darajasidagi konstantaga (`CASCADE_REGISTRY_HINT`, `TENANT_REGISTRY_HINT`) ko'chirildi. Qoida chetlab o'tilmadi — **qo'llanilmaydigan** qilindi.
- **Committed in:** `e1a711e`

**9. [Rule 1 - Bug] `functions.py` docstringida taqiqlangan literal shakl**
- **Found during:** Task 3 (qabul mezonini bajarganda)
- **Issue:** Reja `MARKET_DELETE_DRAFT` izohida `DELETE FROM public.<jadval>` **literal shaklini yozmaslikni** talab qiladi, chunki qabul mezoni `git diff` ni o'qiydi va u izohni koddan ajratmaydi. Men aynan shu shaklni — o'sha ogohlantirishni tushuntirayotgan izohning ichida — yozib qo'ygan edim. `grep -c` **1** berdi (kutilgani 0).
- **Fix:** Ibora literal shaklsiz qayta yozildi.
- **Verification:** `git diff --unified=0 migrations/entities/functions.py | grep -c '^[+-].*DELETE FROM public'` -> **0**; funksiya tanasi tegilmagan (diff faqat +26 qator docstring).
- **Committed in:** `e1a711e`

### TDD tartibidan chekinish

Task 3 `tdd="true"` bo'lsa-da, **bitta commitda** berildi (RED alohida commit qilinmadi). Sabab rejaning o'z talabi: «⛔ bu rejada «kutilgan qizil» degan holat YO'Q — to'g'ri qurilganda test `04-01` dan `04-03` gacha YASHIL turadi». RED holatini branchga commit qilish darvozani to'lqin ichida qizil qoldirardi. RED **o'lchandi va yozib olindi** (yuqoridagi 4-sabotaj) — u ikki tomonlama qulfning `closed` yo'nalishining yagona dalili. Task 2 esa to'liq RED (`91d215c`) → GREEN (`5ae3fd2`) juftligida berildi.

---

**Total deviations:** 9 auto-fixed (3× Rule 1 bug, 3× Rule 2 missing-critical, 3× Rule 3 blocking)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Ikkitasi (1 va 2) rejaning o'zidagi bajarib bo'lmaydigan mezonlarni **niyati bo'yicha** bajardi va ikkalasida ham bir martalik tekshiruv **doimiy darvozaga** aylantirildi. Uchtasi (3, 4, 5) bo'lmasa deploy yoki operator yo'li jimgina buzilardi.

## Issues Encountered

- **`04-VALIDATION.md` va reja o'rtasidagi ziddiyat.** Reja verifikatsiyasi uch darvoza o'lchovini SUMMARY'ga yozishni, orkestrator esa `04-VALIDATION.md` ga yozishni talab qildi. **Ikkalasiga ham** yozildi; `04-VALIDATION.md` `04-02` ning `files_modified` ida yo'q, ya'ni parallel ijrochi bilan to'qnashuv yo'q.
- **Frontend `node_modules` worktree'da yo'q edi** — `npm --prefix frontend test` vitest'ni topa olmadi, lekin `node --test` qismi o'tgani uchun birinchi qarashda «86 test yashil» ko'rindi. `npm ci` bajarildi va o'lchov qayta olindi (246 vitest + 86 node, exit 0). ⚠ Bu ham «yashil ko'rindi, aslida ishlamadi» sinfining namunasi: quvurdagi oxirgi buyruqning chiqish kodi butun zanjirniki emas.
- **Parallel ijro va bitta compose loyihasi.** `04-02` ijrochisi bir xil `sbozor` compose loyihasida ishlaydi. `storage` alohida ko'tarildi va hech qanday konteyner to'xtatilmadi/o'chirilmadi; `gate` o'lchovlari shu sharoitda olingan (shovqin ehtimoli SUMMARY'da qayd etilgan).

## Known Stubs

Yo'q. Bu reja mahsulot xususiyati bermaydi — u infratuzilma va reyestr qo'yadi, va har bir yozuv o'zining darvozasi bilan birga keldi.

⚠ **Stub bo'lmagan, lekin ochiq qolgan ikki band (ikkalasining ham egasi va tetigi bor):**
1. `app.worker:scheduler` — `04-07`/T3. `compose.yaml` da izohda va `04-07` ning qabul mezonida.
2. `ALL_TENANT_TABLES` ga snapshot jadvallari — `04-03`/T2. Tetik: `test_snapshot_registries_are_self_consistent`.

## Threat Flags

Yo'q — bu reja yangi tarmoq endpointi, auth yo'li yoki sxema chegarasi qo'shmadi. Aksincha, uchta mavjud yuza qulflandi (T-04-01 anonim S3 o'qish, T-04-02 ombor porti, T-04-05 `aioboto3` pasaytirishi) va uchalasi ham o'lchov bilan tasdiqlandi.

## User Setup Required

**Ombor birinchi marta ko'tarilganda ikkita qo'l qadami bor** (`ops/seaweedfs/README.md`):

1. `cp ops/seaweedfs/s3.json.example ops/seaweedfs/s3.json` va ichidagi namunaviy kalitlarni haqiqiylari bilan almashtirish; **o'sha qiymatlar `.env` dagi `S3_ACCESS_KEY`/`S3_SECRET_KEY` bilan aynan bir xil bo'lishi shart**.
2. Bucketni bir marta yaratish:
   `printf 's3.bucket.create -name sbozor-snapshots\n' | docker compose exec -T storage weed shell`

`TELEGRAM_BOT_TOKEN` **shart emas** — bo'sh qiymat «alertlar o'chiq» degani va u fazani bloklamaydi (D-19).

## Next Phase Readiness

**`04-03` uchun tayyor va u shu ikki satrni o'qishi kerak:**
- `BILLABLE_ANCHOR_SUPPORTED = true` -> `0014` da `is_billable` `GENERATED ... STORED` + `UNIQUE (id, is_billable)`; trigger varianti **kerak emas**.
- `0014` bilan **bir oynada** bajariladigan uch ish: (a) `SNAPSHOT_TENANT_TABLES` ni `ALL_TENANT_TABLES` ga qo'shish, (b) `PENDING_AUDIT_TRIGGERS` dan ikkala nomni o'chirish, (c) `0015` da `SNAPSHOT_DELETE_ORDER` bo'yicha kaskadni kengaytirish — **mavjud NVR blokidan OLDIN**.

**`04-04`/`04-06`/`04-08` uchun:** `aiobotocore` va `Pillow` prod image'da mavjud (o'lchangan), `storage` ko'tariladi va bucket yaratish yo'riqnomasi yozilgan, `.env.example` da barcha sozlama kalitlari bor.

**`04-07` uchun:** `scheduler` konteyneri profilsiz va tayyor turibdi; unga faqat `app.worker:scheduler` obyekti yetishmaydi.

**`04-12` uchun:** darvoza chegarasining birinchi uch o'lchovi `04-VALIDATION.md` da; qolgan uchtasi va chegara qarori o'sha rejada.

**Bloklovchi yo'q.**

## Self-Check: PASSED

Yaratilgan fayllar diskda tekshirildi (6/6 topildi); commit hashlari `git log`
da tasdiqlandi (`8c35843`, `91d215c`, `5ae3fd2`, `e1a711e`); yakuniy
`pytest tests/unit tests/tenancy` yashil; `ruff check . && ruff format --check .
&& mypy .` toza; `npm run gate` uch marta exit 0.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-04*
