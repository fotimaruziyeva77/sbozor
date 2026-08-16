---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 08
subsystem: testing
tags: [backup, restore-drill, heartbeat, self-check, alerting, testcontainers, pg_dump, pg_restore, rls]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    provides: "`system_heartbeats` jadvali, `/internal/self-check` va uning `EXPECTED_COMPONENTS` reyestri"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`alerting.BACKUP_COMPONENT`, `HEARTBEAT_STALE_HOURS = 26`, `backup_stale` (CRITICAL, `never_suppressed`)"
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-05 ning `ops/backup/heartbeat.sql` va `run-backup.sh` bayroqlari"
provides:
  - "`tests/integration/test_backup_heartbeat.py` — yurak urishi -> `/internal/self-check` -> `backup_stale` zanjirining uchidan-uchiga o'lchovi (4 test)"
  - "`tests/integration/test_restore_drill.py` — D-16(a) mexanizm qatlami: dump -> TOZA postgres -> uch smoke da'vosi"
  - "`tests/fixtures/restore_drill.py` — toza `postgres:18.4-trixie` konteynerining hayot tsikli va dump/restore mexanikasi"
  - "`restore` pytest markeri — narxni hujjatlaydi, standart `addopts` dan CHIQARILMAGAN"
  - "O'LCHANGAN FAKT: `--no-privileges` RLS policy'larini saqlaydi, GRANT'larni EMAS (163 -> 0)"
affects: [08-19-runbook, 08-20-faza-mezoni, 08-HUMAN-UAT]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mahsulot SQL faylini TESTDAN o'qib bajarish (`heartbeat.sql`) — qo'lda takrorlangan upsert o'rniga"
    - "`psql` ning `:'day'` bog'lash mexanizmini DB-API placeholder'iga TOR va E'LON QILINGAN moslashtirish (`%s::text`)"
    - "Toza server mashqi: `pg_dump`/`pg_restore` KONTEYNER ICHIDA, manbaga `host.docker.internal` orqali (`with_kwargs(extra_hosts=...)`)"
    - "Versiya tengligi TAXMIN emas, o'lchov: manba va tiklangan serverning `server_version_num` majori solishtiriladi"

key-files:
  created:
    - tests/integration/test_backup_heartbeat.py
    - tests/integration/test_restore_drill.py
    - tests/fixtures/restore_drill.py
  modified:
    - tests/integration/conftest.py
    - pyproject.toml
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/deferred-items.md

key-decisions:
  - "08-08: yangi `restore` markeri, `slow` QAYTA ISHLATILMADI — `slow` «uzoq SIM stsenariylari» deb e'lon qilingan va `npm run test:sim*` uni `sim` bilan JUFTLAB filtrlaydi; tiklash mashqi simulyatorga tegmaydi"
  - "08-08: `restore` standart `addopts` dan CHIQARILMADI va bu TAQIQ — chiqarilsa 08-20 ning mezon testi uni chaqira olmasdi (o'lchandi: standart yig'ilishda 1 test, `-m \"not restore\"` da 0)"
  - "08-08: uch smoke da'vosi BITTA testda — uch testga bo'lish `restore_target` ni (funksiya qamrovi) UCH MARTA ko'tarardi, xost diski esa 93 % to'la edi (T-08-33)"
  - "08-08: mexanika `tests/fixtures/restore_drill.py` da, conftest'da EMAS — `pythonpath` ga `tests` katalogi kiradi, ya'ni `import conftest` ILDIZDAGI conftest'ga borardi va tipni test faylida e'lon qilib bo'lmasdi (mypy bilan o'lchandi)"
  - "08-08: `pg_dump` SUPERUSER bilan chaqiriladi — `sbozor_app`/`sbozor_owner` ATAYIN `NOSUPERUSER NOBYPASSRLS`, ya'ni ular bilan `row_security = off` o'rnatib bo'lmaydi va dump yiqilardi"
  - "08-08: toza serverda ROLLAR zaxiradan OLDIN yaratiladi (`01-roles.sql`) — dump `CREATE POLICY ... TO sbozor_app` ni o'z ichiga oladi; `00-extensions.sql` esa ATAYIN yo'q (dump kengaytmani o'zi olib keladi)"
  - "08-08: tayyorlik LOG SATRI bilan emas, ULANISH bilan kutiladi — `postgres` entrypointi «ready to accept connections» ni IKKI MARTA yozadi"
  - "08-08: `--no-privileges` ning GRANT yo'qotishi TUZATILMADI (Rule 4) — bayroq 08-05 da ONGLI tanlangan va `test_backup_contract.py` da qulflangan; band `deferred-items.md` №5, egasi 08-19"

patterns-established:
  - "Mahsulot SQL faylidan izoh qatorlarini AJRATIB olish: `:'day'` faylda UCH marta uchraydi (ikkitasi izohda) — predikat izoh matnini SQL bilan aralashtirsa hech qachon rost bo'lmasdi"
  - "«Sanoq TENG» da'vosi QUYI CHEGARASIZ bo'sh-rost: 0 == 0 yashil bo'ladi va sabotaj ham kesadigan qator topmaydi"
  - "Sabotaj SISTEMAGA yetib borib, tekshirilayotgan PREDIKATGA yetib bormasligi mumkin (08-05 ning 1b darsi takrorlandi — quyida o'lchandi)"

requirements-completed: [FOUND-07]

# Metrics
duration: 40min
completed: 2026-08-16
---

# Phase 8 Plan 08: FOUND-07 ning ikki o'lchanadigan qatlami — Summary

**Zaxira yurak urishi endi `/internal/self-check` va `backup_stale` bilan uchidan-uchiga bog'langani o'lchandi (test SQL ni qo'lda yozmaydi — `ops/backup/heartbeat.sql` FAYLINI bajaradi), `pg_dump` esa toza `postgres:18.4-trixie` konteyneriga tiklanib pul yozuvlari, RLS policy'lari va audit jurnali joyida qolgani tasdiqlandi — «offsite repodan tiklash» ning O'LCHANMAGANI esa kodda LITERAL yozildi.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2/2
- **Files:** 6 (3 yangi, 3 tahrirlangan)

## Accomplishments

- **FOUND-07 ning kuzatuv halqasi endi MANBA bilan bog'langan holda o'lchanadi.** 08-05 zaxira jarayonini qurdi, lekin «yurak urishi haqiqatan `self-check` va `alert_sweep` ga yetib boradimi?» savoli o'lchanmagan edi. Endi to'rt test uni ikki uchidan ushlaydi — va ular SQL ni qo'lda takrorlamaydi.
- **Tiklash mashqining CI qatlami (D-16a) qurildi va u haqiqiy `pg_restore` ni ishlatadi** — bitta qo'shimcha konteyner, uch smoke da'vosi, ~5.5–9.4 s.
- **Uchta halol chegara KODDA literal yozildi:** (1) `restic` bu testda ishtirok etmaydi; (2) «offsite repodan tiklandi» `08-HUMAN-UAT.md` da, egasi Ops; (3) ⚠ YANGI — «tiklandi» ≠ «ilova ishlay oladi» (GRANT'lar yo'qoladi).
- **Ikki majburiy sabotaj + ikki qo'shimcha variant o'lchandi** va hammasi qaytarildi.
- **Regressiya yo'q:** `test_alerting.py` 28/28, `tests/unit` to'liq yashil, `ruff`/`mypy` butun daraxt bo'ylab toza, `pytest --collect-only` xatosiz.

## Task Commits

1. **Task 1: yurak urishi -> self-check -> `backup_stale` zanjiri** — `ae46f92` (test)
2. **Task 2: tiklash mashqi — mexanizm qatlami (D-16a)** — `5370d52` (test)

## Sabotajlar — o'lchandi va qaytarildi

| # | Sabotaj | Kutilgan | O'lchangan natija |
|---|---------|----------|-------------------|
| 1 | `heartbeat.sql` da `'backup'` -> `'backups'` | (b) qizaradi | ✅ QIZARDI: «`heartbeat.sql` bajarildi, lekin `system_heartbeats` da `backup` qatori paydo bo'lmadi — komponent nomi `alerting.BACKUP_COMPONENT` dan AJRALGAN» |
| 1b | O'sha sabotaj, lekin `never_seen` PREDIKATIGA yetkazilgan (zond bilan) | `backup` `never_seen` da QOLADI | ✅ QIZARDI: `{'ok': True, 'stale': [], 'never_seen': [... 'backup' ...]}` — ⛔ e'tibor: `ok = true`, ya'ni endpoint 200 qaytarib turgan holda zaxira komponenti JIMGINA uzilgan |
| 1c | (kutilmagan natija) o'sha sabotaj ostida (d) ham qizardi | — | ✅ «YANGI yurak urishi ustida `backup_stale` ochildi» — yangi yozuv boshqa nomga ketgani uchun |
| 2 | `pg_restore` dan KEYIN `TRUNCATE TABLE payments CASCADE` | (1) da'vosi qizaradi | ✅ QIZARDI: «`payments`: manbada 1, tiklangan bazada 0 — pul yozuvlari zaxiradan TO'LIQ tiklanmadi» |

> ⛔ **1b QO'SHIMCHA VA U 08-05 NING DARSINING TAKRORI.** 1-sabotaj (b) ni
> BIRINCHI sub-assert'da (bazada qator bormi?) to'xtatdi, ya'ni rejaning
> «`backup` ning `never_seen` da QOLISHI o'lchansin» talabi o'lchanmagan
> bo'lib qolardi. Vaqtinchalik zond aynan o'sha predikatga yetkazdi.
> **Sabotaj sistemaga yetib borsa ham, u tekshirmoqchi bo'lgan PREDIKATGA
> yetib bormasligi mumkin.**

> ⚠ **1c — SABOTAJ (c) NI QIZARTIRMADI VA BU TO'G'RI.** Komponent nomi
> ajralganda `backup` ning yurak urishi HAQIQATAN yo'q bo'ladi, ya'ni
> «27 soatlik yozuv alert beradi» testi TO'G'RI sabab bilan yashil
> qoladi. Ya'ni (c) ni AYNAN shu sabotaj qo'riqlamaydi — uni (b) va (d)
> qo'riqlaydi. Bu qamrovdagi bo'shliq EMAS, mas'uliyat taqsimoti.

## Verification natijalari

| O'lchov | Natija |
|---------|--------|
| `pytest tests/integration/test_backup_heartbeat.py -q` | ✅ **4 passed** |
| `pytest tests/integration/test_restore_drill.py -q` | ✅ **1 passed** |
| `pytest test_backup_heartbeat.py test_alerting.py -q` (rejaning buyrug'i) | ✅ **32 passed** — mavjud alert testlarida regressiya YO'Q |
| `pytest test_backup_heartbeat.py test_restore_drill.py test_alerting.py -q` | ✅ **33 passed** |
| `pytest tests/unit -q` | ✅ to'liq yashil (`test_backup_contract.py` ham) |
| `ruff check . && ruff format --check . && mypy .` | ✅ `All checks passed` / `364 files already formatted` / `no issues found in 353 source files` |
| `pytest --collect-only -q` (butun daraxt) | ✅ xatosiz |
| `grep -c "def test_" test_backup_heartbeat.py` | **4** (rejaning talabi) |
| Marker: standart `addopts` bilan yig'ilish | **1 test** — ⛔ CHIQARILMAGAN |
| Marker: `-m restore` | **1 test** |
| Marker: `-m "not restore"` | **0 test** — marker haqiqatan qo'llangan |
| Tiklash mashqining narxi | setup **3.4–5.0 s** + call **1.6–2.7 s** + teardown **~1.3–1.8 s** ≈ **5.5–9.4 s** |
| Birinchi (sovuq) yugurish | setup 18.4 s + call 3.2 s + teardown 1.3 s — sessiya Postgres'i va `alembic upgrade head` bilan birga |
| Konteyner qoldig'i | ✅ `sbozor_restored` konteyneri QOLMADI (`docker ps -a` bilan tekshirildi) |
| Xost diski | **C: 93 % to'la (13 GB bo'sh)** o'lchov paytida; `E:` 5 % (115 GB bo'sh). Yangi image TORTILMADI — `postgres:18.4-trixie` allaqachon mavjud edi |

## Decisions Made

Frontmatter `key-decisions` to'liq. Uchtasi alohida diqqat talab qiladi:

- **`pg_dump` SUPERUSER bilan chaqiriladi va bu ZARURIYAT, qulaylik emas.**
  `pg_dump` ishini `row_security = off` bilan boshlaydi; uni o'rnatish
  SUPERUSER yoki `BYPASSRLS` talab qiladi, `sbozor_app` va `sbozor_owner`
  esa ATAYIN `NOSUPERUSER NOBYPASSRLS`. Muqobil (`--enable-row-security`)
  dumpga FAQAT ko'rinadigan qatorlarni yozardi — zaxira JIMGINA qisman
  bo'lardi. ⛔ Ya'ni prod'dagi `BACKUP_DATABASE_URL` ham superuser/
  `BYPASSRLS` roliga ishora qilishi SHART; band `source_dsn` fixture'ining
  docstringida literal.
- **Uch da'vo BITTA testda.** Uch testga bo'lish uch konteyner degani
  edi, uchala da'vo esa AYNAN BIR XIL tiklash natijasini o'lchaydi.
  Har da'vo O'Z xabari bilan keladi, ya'ni tashxis yo'qolmaydi.
- **Mexanika `tests/fixtures/restore_drill.py` da.** Bu conftest'ning
  o'z qoidasi («fixture'lar REYESTRI bo'lib qolsin»), lekin bu yerda u
  MEXANIK zaruriyatga aylandi: `pythonpath` ga `tests` katalogi kiradi,
  ya'ni `from conftest import RestoreTarget` ILDIZDAGI `tests/conftest.py`
  ga borardi (integratsiya conftest'iga EMAS) va `mypy` da yiqilardi —
  o'lchandi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `:'day'` faylda UCH marta uchraydi — ikkitasi IZOHDA**

- **Found during:** Task 1, birinchi test yugurishi
- **Issue:** Reja «test `heartbeat.sql` faylini o'qib bajarsin, `:'day'` test tomonidan bog'lansin» deydi. Yalang'och `replace()` esa IZOH matniga ham tegardi, «aynan bitta bog'langan o'zgaruvchi» nazorat asserti esa `3 == 1` bilan yiqildi (o'lchandi, taxmin emas: `heartbeat.sql` T-08-22 ni o'z izohida IKKI marta tilga oladi).
- **Fix:** `_sql_body()` to'liq qatorli `--` izohlarini olib tashlaydi; sanoq SHUNDAN KEYIN o'lchanadi. Faqat TO'LIQ QATORLI izohlar kesiladi — qator ichidagi `--` satr literaliga tegib SQL ni buzardi.
- **Files modified:** `tests/integration/test_backup_heartbeat.py`
- **Committed in:** `ae46f92`

**2. [Rule 3 - Blocking] Bog'langan parametrning tipi ANIQLANMADI**

- **Found during:** Task 1, ikkinchi yugurish
- **Issue:** `:'day'` -> `%s` almashtirilgach `psycopg.errors.IndeterminateDatatype: could not determine data type of parameter $1`. Sabab: `psql` ning `:'day'` i QOCHIRILGAN SATR LITERALINI qo'yadi (Postgres uni `unknown` -> `text` deb hal qiladi), DB-API esa TIPSIZ parametr yuboradi va `jsonb_build_object(..., "any")` tipni aniqlay olmaydi.
- **Fix:** Almashtirish `%s::text` bo'ldi. ⚠ Bu yangi xulq emas — `psql` ning qochirishi bergan tipni AYNAN tiklash; qiymat ikkala yo'lda ham BOG'LANGAN parametr bo'lib qoladi (T-08-22 buzilmaydi). Sabab `DBAPI_DAY_BINDING` docstringida o'lchangan xato bilan birga yozilgan.
- **Files modified:** `tests/integration/test_backup_heartbeat.py`
- **Committed in:** `ae46f92`

### Ongli shakl farqlari (xato emas, qaror)

**3. Quyi chegara ALOHIDA TEST emas, `autouse` FIXTURE (08-05 naqshining takrori).**
Reja `test_backup_heartbeat.py` da AYNAN 4 ta `def test_` talab qiladi. `heartbeat.sql` ning mavjudligi darvozasi beshinchi test bo'lganda sanoq 5 ga chiqardi — va u yolg'iz qizarib, qolgan to'rt da'vo bo'sh-rost holida yashil bo'lib turardi (fayl yo'qolsa ular `FileNotFoundError` bilan «buzuq test» kabi yiqilardi). `autouse` shaklida chegara TO'RTALA o'lchovning HAR BIRIDAN oldin bajariladi va sanoq 4 bo'lib qoladi.

**4. To'rtinchi fayl — `tests/fixtures/restore_drill.py` (rejada YO'Q edi).**
Reja Task 2 uchun uch faylni sanaydi. Tipni integratsiya conftest'ida qoldirish MEXANIK ravishda ishlamadi (yuqoridagi «Decisions» ning uchinchi bandi, `mypy` bilan o'lchandi), shuning uchun mexanika `tests/fixtures/` ga — repozitoriyning O'Z hujjatlangan qoidasi ko'rsatgan joyga — chiqarildi. Qamrov kengaymadi: conftest faqat ikki fixture e'lon qiladi.

**5. Uch smoke da'vosi BITTA testda, uchta emas.**
Reja «uch smoke da'vosi» deydi (uch TEST emas) va qabul mezoni ham «uch smoke assertioni bor» shaklida. T-08-33 (disk bosimi) ostida uch konteyner ko'tarish narxi asossiz edi.

## Threat Flags

Rejadagi `<threat_model>` dan TASHQARIDA yangi hujum yuzasi topilmadi (bu reja mahsulot kodiga UMUMAN tegmaydi — u faqat test qatlamini qo'shadi). Bitta band qayd etiladi va u T-08-31 ning YONIDA turadi:

| Band | Fayl | Ta'rif |
|------|------|--------|
| ⚠ Tiklangan bazada ILOVA ROLI huquqsiz | `ops/backup/run-backup.sh` (tegilmadi) | `--no-privileges` RLS policy'larini SAQLAYDI (83 -> 83, ya'ni T-08-31 haqiqatan yumshatilgan), lekin `sbozor_app` uchun GRANT'larni CHIQARMAYDI (163 -> 0). Tiklangan platforma **ochiq emas** — aksincha, ilova UMUMAN ishlay olmaydi (`permission denied for table`). Bu maxfiylik emas, TIKLANISH (RTO) risk'i. `deferred-items.md` №5, egasi 08-19. |

## Known Stubs

Yo'q. Ikkala fayl ham haqiqiy mahsulot yo'lini chaqiradi: `heartbeat.sql`
FAYLDAN bajariladi, `alert_sweep` mahsulot funksiyasining O'ZI,
`pg_dump`/`pg_restore` esa haqiqiy binarlar va haqiqiy konteyner.
Qattiq yozilgan bo'sh qiymat, soxta muvaffaqiyat yoki «coming soon» yo'q.

⛔ CI'da o'lchanmaydigan da'volar ikkalasi ham OCHIQ nomlangan va ular
mahsulot koddagi qarz emas, **egasi bor UAT bandlari**: (1) «offsite
repodan tiklash» — `08-HUMAN-UAT.md`, egasi Ops, tetigi VPS deploy;
(2) tiklangan bazani ILOVA bilan ishga tushirish — `deferred-items.md`
№5, egasi 08-19 runbook.

## Issues Encountered

- **`pedantic_saha` (sessiya Postgres'i) bir muddat qolib turdi** — u
  `tests/conftest.py::pg_container` niki (`POSTGRES_DB=test`), MENING
  `restore_target` im EMAS (`POSTGRES_DB=sbozor_restored`). O'lchov
  oxirida u ham yo'qoldi. ⚠ `TESTCONTAINERS_RYUK_DISABLED=true` sababli
  bunday qoldiqlar avtomatik yig'ishtirilmaydi — 3–4 kunlik `Exited`
  postgres konteynerlari HOZIR ham bor (boshqa to'lqinlardan).
- **Worktree izolyatsiyasi `deferred-items.md` №3 ning retsepti bilan
  bajarildi:** `.env` va `ops/seaweedfs/s3.json` asosiy checkout'dan
  nusxalandi, testlar `-p sbozor-w0808 ... --no-deps` bilan yugurdi,
  oxirida `down -v` qilindi va ikkala fayl O'CHIRILDI. Asosiy stekning
  `sbozor-storage-1` / `sbozor-db-1` konteynerlariga TEGILMADI.
- **`ruff format` butun daraxtda BEGONA faylni ham tuzatdi**
  (`services/core-api/app/jobs/reconciliation.py`). SCOPE BOUNDARY
  bo'yicha u `git checkout --` bilan QAYTARILDI va `deferred-items.md`
  №6 ga yozildi. ⚠ Band jonli: `npm run lint` va `npm run gate` shu fayl
  sababli HOZIR qizil.

## Next Phase Readiness

- **08-20 (faza mezoni testi) uchun tayyor:** ikkala fayl ham standart
  `pytest` yig'ilishida ko'rinadi (`restore` markeri `addopts` dan
  CHIQARILMAGAN — o'lchandi), ya'ni mezon testi ularni nomma-nom chaqira
  oladi.
- **08-19 (runbook) uchun IKKI band ochiq va ikkalasi ham o'lchangan
  fakt ustida turadi:** (1) tiklash tartibiga GRANT'larni qaytarish
  qadami kerak (`deferred-items.md` №5); (2) `BACKUP_DATABASE_URL`
  superuser/`BYPASSRLS` roliga ishora qilishi SHART — aks holda nochlik
  zaxira `pg_dump` bosqichida yiqiladi (bu TO'G'RI xulq, lekin runbook
  uni tushuntirishi kerak).
- **`08-HUMAN-UAT.md` ga band QO'SHILISHI kerak:** «offsite repodan
  tiklandi» tekshiruvi GRANT qadamisiz «muvaffaqiyatli» deb imzolanib
  ketishi mumkin — bu 08-08 da o'lchangan yangi fakt.
- **Orkestrator uchun:** `services/core-api/app/jobs/reconciliation.py`
  ning bitta bo'sh qatori `npm run gate` ni qizartiradi
  (`deferred-items.md` №6). U 08-08 ning commitiga ATAYIN kiritilmadi.

## Self-Check: PASSED

Yaratilgani da'vo qilingan UCHALA fayl ham diskda mavjud
(`tests/integration/test_backup_heartbeat.py`,
`tests/integration/test_restore_drill.py`,
`tests/fixtures/restore_drill.py`) va IKKALA commit ham `git log` da:
`ae46f92` -> `5370d52`. Sabotajlar `git checkout --` bilan qaytarilgani
va vaqtinchalik zondlar o'chirilgani `git status` bilan tasdiqlandi
(ishchi daraxt toza). Yo'qolgan artefakt yo'q.

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*
