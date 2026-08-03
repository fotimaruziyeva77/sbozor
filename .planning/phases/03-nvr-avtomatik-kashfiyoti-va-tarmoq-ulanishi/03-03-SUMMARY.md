---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 03
subsystem: data-model
tags: [migration, rls, multi-tenant, audit, pg_catalog, gate, nvr, wave-2, wr-02]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`Base`/`TenantMixin`/`uuid_pk()` va `market_fk_column()`; `fn_audit_row()` + `attach_audit_trigger()`; `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`market_delete_draft()` ning o'n ikki jadvalli kaskadi; `ALL_TENANT_TABLES` reyestri; `0009_vendors.py` migratsiya shabloni; `tests/tenancy/test_meta.py` ning besh invarianti"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 01
    provides: "`tests/integration/test_market_delete_guard.py` — kaskad to'liqligining `pg_catalog` darvozasi (W0-7 ning MEXANIZM yarmi)"
provides:
  - "`nvr_devices` / `nvr_credentials` / `cameras` / `nvr_discovery_runs` — to'rt tenant jadvali, hammasi RLS ENABLE+FORCE + policy + composite FK ostida"
  - "`UNIQUE (market_id, nvr_id, channel_no)` — SC#2 ning DB kafolati; xom `INSERT` `23505` beradi"
  - "`nvr_credentials` audit triggeridan CHIQARILGAN (SC#4) va bu `pg_trigger` bo'yicha qulflangan"
  - "`0013_market_delete_guard` — kaskad NVR domenini qamraydi VA `markets` ga `BEFORE DELETE` trigger (SC#8 / WR-02 YOPILDI)"
  - "`sbozor_core.enums.CameraStatus` va `DiscoveryRunStatus`"
  - "`migrations.entities.NVR_TENANT_TABLES` / `NVR_AUDITED_TABLES` reyestrlari"
  - "`tests/fixtures/nvr_domain.py` — ikki bozorli NVR/kamera seed'i + `nvr_rows()` kontekst menejeri + `add_discovery_run()`"
  - "`tests/tenancy/test_nvr_domain_meta.py` — NVR domenining to'rt invarianti"
affects: [03-04-shifrlash, 03-05-isapi-klient, 03-06-job, 03-07-api, 04-snapshot, 05-zonalar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Yangi tenant jadvali BESH JOYDA e'lon qilinadi (reyestr / migratsiya RLS trio / AUDITED_TABLES / model barreli / seed) — biri unutilsa CI qizaradi"
    - "Audit qamrovi RLS qamrovidan ALOHIDA ro'yxatda: `NVR_TENANT_TABLES` (to'rtta) va `NVR_AUDITED_TABLES` (ikkita). Istisno migratsiya ichidagi `if` da EMAS, reyestrda"
    - "Qisman/global indeks IKKALA tomonda e'lon qilinadi (model `Index(...)` + migratsiya `op.create_index`), nom va predikat esa BITTA konstantadan — aks holda autogenerate uni `remove_index` deb ko'radi"
    - "Konstrayt predikati enum'dan HOSILA (`DISCOVERY_RUN_ACTIVE_PREDICATE`), literal emas — enum kengaysa indeks jimgina hech nimani qamramay qolardi"
    - "Kafolat IKKI QATLAMDA: ilova yo'lida tushunarli xabar (`market_delete_draft()` -> 409), sxemada esa chetlab o'tib bo'lmaydigan to'siq (`BEFORE DELETE` trigger)"
    - "Sir jadvali RLS ostida QOLADI, lekin audit triggeridan CHIQARILADI — ikki qamrov bir-birini almashtirmaydi"

key-files:
  created:
    - packages/sbozor-core/sbozor_core/models/nvr.py
    - migrations/versions/0012_nvr_domain.py
    - migrations/versions/0013_market_delete_guard.py
    - tests/fixtures/nvr_domain.py
    - tests/tenancy/test_nvr_domain_meta.py
  modified:
    - packages/sbozor-core/sbozor_core/enums.py
    - packages/sbozor-core/sbozor_core/models/__init__.py
    - packages/sbozor-core/sbozor_core/schema_contract.py
    - migrations/entities/__init__.py
    - migrations/entities/functions.py
    - migrations/entities/triggers.py
    - tests/tenancy/test_meta.py
    - tests/integration/test_market_delete_guard.py
    - tests/fixtures/two_markets.py
    - tests/integration/test_market_calendar.py

key-decisions:
  - "`nvr_credentials` audit triggeridan chiqarildi — IKKI MUSTAQIL sabab bir xil qarorga olib keladi: (a) `fn_audit_row()` `to_jsonb(NEW)` yozadi va Fernet shifrmatni `audit_log` ga tushardi (kalit buzilganda TARIXIY parollar ochilardi); (b) `attach_audit_trigger()` `id uuid` PK talab qiladi, bu 1:1 jadvalda esa PK — `nvr_id`. Jadval RLS ostida QOLDI: audit istisnosi tenant izolyatsiyasini bekor qilmaydi"
  - "Indekslar MODELDA HAM e'lon qilindi (Rule 3). O'lchandi: faqat `op.create_index(...)` bilan `test_autogenerate_is_empty` uchta `remove_index` bilan qizardi — ya'ni keyingi `alembic revision --autogenerate` indekslarni O'CHIRISHNI taklif qilardi va kimdir buni «tozalash» deb qabul qilishi mumkin edi"
  - "`markets_delete_guard()` `ERRCODE = '23514'` beradi — `tariff_past_immutable()` va `category_period_past_immutable()` bilan AYNAN bir xil kod. Yangi konvensiya kiritilmadi: uchalasi ham «domen qoidasi buzildi» sinfida va chaqiruvchi ularni bitta yo'lda 409 ga aylantiradi"
  - "Test teardown'lari bozorni o'chirishdan OLDIN qoralamaga qaytaradigan bo'ldi (Rule 3). Bu zaiflashtirish EMAS, mahsulot qoidasining o'zi: faol bozorni o'chirish yo'li ATAYIN yo'q (`market_deactivate()` yaratilmagan) va endi bu sxemada ham majburlanadi. Naqsh yangi emas — `cleanup_market_domain()` 02-04 dan beri aynan shu qadamni bajaradi"
  - "`tunnel_subnet` va `stream_name` `INDEX_EXCEPTIONS` ga sabab bilan qo'shildi: ikkalasi ham ATAYIN tenant chegarasidan tashqarida. Noyoblikni `(market_id, ...)` ga tushirish ikkalasining ham HIMOYASINI yo'q qilardi — to'qnashuv aynan bozorlar ORASIDA yuz beradi"
  - "`nvr_domain` seed'i pytest fixture EMAS, `contextmanager` (`fixtures/auth_api.py::draft_market` naqshi). Sabab bog'liqlik yo'nalishida: fixture `tests/conftest.py` da yashashi kerak bo'lardi, o'sha faylni esa shu to'lqinda 03-02 ham tahrirlaydi (`sim_url`) — merge to'qnashuvi bo'lardi"
  - "`FINANCIAL_TABLES` TEGILMADI (qiymati HEAD bilan bayt-ma-bayt bir xil). 3-fazada pul ustuni yo'q; jadval qo'shilsa meta-test soxta `amount_soum` talab qilardi (2-fazadagi Pitfall 3 ning takrorlanishi)"

patterns-established:
  - "Pattern: yangi tenant jadvalining audit qamrovi RLS qamrovidan ALOHIDA reyestrda e'lon qilinadi — istisno kodning ichida `if` bo'lib yashirinmaydi"
  - "Pattern: qisman indeksning predikati enum'dan hosila, nomi esa modeldagi konstantadan — migratsiya va model BITTA manbadan oladi"
  - "Pattern: DB kafolati IKKI TOMONDAN o'lchanadi — katalogda mavjudligi VA xom `INSERT` dagi SQLSTATE. Faqat birinchisi «e'lon qilingan» ni isbotlaydi, «ishlaydi» ni emas"
  - "Pattern: inkor da'vosi («ustun yo'q», «trigger yo'q») HAR DOIM nazorat bandi bilan keladi — so'rov buzilganda bo'sh natija inkorni JIMGINA rost qilardi"
  - "Pattern: cross-tenant nazorati uchun ikkinchi bozorda ham qator BO'LISHI shart; seed asimmetriyasi test tomonidan `add_discovery_run()` bilan to'ldiriladi, seed simmetrik qilinmaydi"

requirements-completed: []

# Metrics
duration: 65min
completed: 2026-08-03
---

# Phase 3 Plan 03: NVR ma'lumot modeli Summary

**To'rtta NVR tenant jadvali RLS/policy/audit tsikli bilan tug'ildi, SC#2 va SC#4 sxema darajasida qulflandi, va WR-02 — 2-fazadan meros qolgan «faol bozorni `psql` dan o'chirib bo'ladi» teshigi — `markets` ustidagi `BEFORE DELETE` trigger bilan yopildi.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-08-03T00:30Z
- **Completed:** 2026-08-03T01:35Z
- **Tasks:** 3/3
- **Files:** 15 (5 yangi, 10 o'zgargan)

## Accomplishments

- **W0-7 to'liq yopildi.** 03-01 mexanizmni qoldirgan edi; bu reja uning ikkinchi yarmini bajardi va darvoza **o'z ishini isbotladi**: `0012` qo'ngan zahoti qizardi, to'rtala jadvalni nomma-nom aytdi, `0013` dan keyin yana yashil bo'ldi.
- **WR-02 (SC#8) YOPILDI** — bu 2-fazadan meros qolgan yagona ochiq xavfsizlik bandi edi.
- **Bazaviy darvoza o'smadi, kengaydi:** 1021 → **1028** backend (+7), 322 → **326** tenancy (+4), **60** node:test (o'zgarmadi), frontend fayllari **umuman tegilmadi**.
- **Ikkala sabotaj ham kutilgan natijani berdi** va ikkalasida ham «nima yashil qoldi» alohida o'lchandi.

## Task Commits

1. **Task 1: to'rt model + enumlar + besh joyning reyestrlari** — `77401e0` (feat)
2. **Task 2: `0012_nvr_domain` + ikki bozorli seed** — `13a2b5d` (feat)
3. **Task 3: `0013_market_delete_guard` + to'rt meta-invariant** — `ef0614d` (feat)

## O'lchangan dalillar

### W0-7 ning ikki yarmi — darvoza ishladi

| Bosqich | `test_market_delete_guard.py` | Xabar |
|---|---|---|
| `0012` qo'ngandan keyin | **QIZIL** (1 test) | `kaskadida ['cameras', 'nvr_credentials', 'nvr_devices', 'nvr_discovery_runs'] YO'Q` |
| `0013` dan keyin | **YASHIL** (7 test) | — |

To'rtala nom ham xato xabarida turdi — ya'ni 03-01 ning «yetishmayotgan jadval nomi xato xabarida bo'ladi» da'vosi o'lchandi.

### Migratsiya aylanmasi (nol holatdan, `postgres:18.4-trixie`)

| Qadam | Natija |
|---|---|
| `upgrade head` | `revision=0013`, NVR jadvallari **4/4** |
| `alembic check` | **bo'sh diff** (`No new upgrade operations detected`) |
| `downgrade 0011` | `revision=0011`, NVR jadvallari **0/4** |
| `upgrade head` (qayta) | `revision=0013`, NVR jadvallari **4/4** |
| `alembic check` (aylanmadan keyin) | **bo'sh diff** |

### SC#2 — DB kafolati tirik o'lchandi

Xom `INSERT` bilan mavjud kanal (boshqa `stream_name` bilan, ya'ni yagona qolgan sabab kanal noyobligi):

```
dublikat kanal RAD ETILDI, sqlstate = 23505
```

### SC#4 — sir auditga tushmaydi

`pg_trigger` bo'yicha: `nvr_credentials` da **birorta** (ichki bo'lmagan) trigger yo'q; nazorat bandi sifatida `nvr_devices` da `trg_audit_nvr_devices` **bor** — ya'ni so'rov haqiqatan trigger topa oladi va inkor da'vosi bo'sh natijadan kelib chiqmagan.

### Seed va sxema

| O'lchov | Natija |
|---|---|
| Seed sanoqlari | `nvr_devices=2, nvr_credentials=2, cameras=4, nvr_discovery_runs=1` |
| `stream_name` global noyobligi | 4/4 farqli |
| Kaskad tartibi | `cameras`(1056) → `nvr_discovery_runs`(1057) → `nvr_credentials`(1058) → `nvr_devices`(1059) → … → `markets`(1073) |
| `require_extension(` chaqiruvi `0012` da | **0** |
| `postgresql_where` `0012` da | 2 ta indeks (+1 izoh) |
| Muzlatilgan `TENANT_TABLES` / `RLS_TABLES` diffi | **0 qator** |
| `FINANCIAL_TABLES` | `['charge_adjustments', 'daily_charges', 'payments', 'tariffs']` — **HEAD bilan bir xil** |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| S1 | `0013` dagi `BEFORE DELETE` trigger ULANMADI (funksiya qoldi) | `test_market_delete_guard.py` — **1 test** (`test_active_market_cannot_be_deleted_by_raw_sql`) | **Shu fayldagi qolgan 6 test**, `test_nvr_domain_meta.py` (4), va **`test_wizard_flow.py::test_active_market_cannot_be_deleted`** (ilova qatlamining O'Z testi) | Ilova qatlami va DB qatlami MUSTAQIL o'lchanadi. Eng muhimi: ilova qatlamidagi «faol bozor o'chirilmaydi» testi sxemadagi teshikni **KO'RMAYDI** — aynan shuning uchun WR-02 alohida test talab qilardi |
| S2 | `0012` dan `UNIQUE (market_id, nvr_id, channel_no)` olib tashlandi | `test_nvr_domain_meta.py` — **1 test**; xabar mavjud konstraytlarni ham sanadi: `{'uq_cameras_market_id_id': [...], 'uq_cameras_stream_name': [...]}` | **`test_market_delete_guard.py` (7) va `test_meta.py` (25)** — jami 32 test | SC#2 ning kafolati haqiqatan shu invariant bilan o'lchanadi; besh umumiy tenant invarianti uni **umuman ko'rmaydi** (ular `market_id`+RLS+policy+indeks tartibini tekshiradi, domen qarorini emas) |

Ikkala sabotaj ham commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; ikkalasidan keyin ham ish daraxti toza (`git status --short` bo'sh).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Bloklovchi] Indekslar modelda ham e'lon qilindi**

- **Found during:** Task 2
- **Issue:** Reja indekslarni faqat migratsiyada (`op.create_index`) yaratishni yozgan. O'lchandi: `test_autogenerate_is_empty` **uchta `remove_index`** bilan qizardi (`ix_cameras_market_id_nvr_id`, `uq_nvr_devices_tunnel_subnet_global`, `uq_nvr_discovery_runs_market_id_nvr_id_active`). Sabab — autogenerate model metadata'sini baza bilan solishtiradi, ya'ni modelda e'lon qilinmagan indeks «o'chirilgan» deb ko'rinadi. Bu shunchaki qizil test emas: keyingi `alembic revision --autogenerate` uchala indeksni **O'CHIRISHNI** taklif qilardi va uni «tozalash» deb qabul qilish oson bo'lardi — ya'ni SC#2 va D-07 kafolatlari jimgina yo'qolishi mumkin edi.
- **Fix:** Uchala indeks `__table_args__` ga `Index(...)` sifatida qo'shildi; nomlar va predikatlar `models/nvr.py` dagi konstantalarga ko'chirildi va migratsiya ularni **import qiladi** (ikki nusxa ajralib ketmasin).
- **Verification:** `alembic check` nol holatdan ham, downgrade/upgrade aylanmasidan keyin ham bo'sh diff beradi.
- **Committed in:** `13a2b5d`

**2. [Rule 3 — Bloklovchi] `INDEX_EXCEPTIONS` ga ikki global indeks**

- **Found during:** Task 2
- **Issue:** `test_tenant_indexes_lead_with_market_id` `uq_nvr_devices_tunnel_subnet_global` va `uq_cameras_stream_name` uchun qizarardi — ikkalasi ham ATAYIN `market_id` bilan boshlanmaydi. Reja bu holatni oldindan ko'rgan («agar o'sha meta-test istisno ro'yxatini talab qilsa, ijrochi uni **sabab bilan** qo'shadi»), lekin `tests/tenancy/test_meta.py` `files_modified` da yo'q edi.
- **Fix:** Ikkala nom ham `INDEX_EXCEPTIONS` ga qo'shildi, har biriga **nima uchun tenant chegarasidan tashqarida** ekani yozildi: `tunnel_subnet` uchun to'qnashuv bozorlar ORASIDA yuz beradi (T-03-19), `stream_name` uchun go2rtc bitta jarayon va uning oqim nomlari fazosi barcha bozorlar uchun umumiy.
- **Verification:** `npm run test:tenancy` → 326 passed.
- **Committed in:** `13a2b5d`

**3. [Rule 3 — Bloklovchi] Trigger funksiyasi `triggers.py` ga**

- **Found during:** Task 3
- **Issue:** Reja «`migrations/entities/triggers.py` dagi mavjud shaklga ergashadi» deb yozgan, lekin faylning o'zi `files_modified` da yo'q edi. Mavjud konvensiya qat'iy: trigger FUNKSIYASI `alembic-utils` nazoratida (`triggers.py`), trigger'ning O'ZI esa migratsiyada xom `op.execute("CREATE TRIGGER ...")` bilan.
- **Fix:** `MARKETS_DELETE_GUARD` `triggers.py` ga qo'shildi (`NVR_DOMAIN_TRIGGER_FUNCTIONS` ro'yxati bilan, `ALL_TRIGGER_FUNCTIONS` ga kiritildi). `functions.py` ga qo'yish konvensiyani buzardi (u trigger bo'lmagan funksiyalar uchun), migratsiya ichiga xom `CREATE FUNCTION` yozish esa uni autogenerate nazoratidan chiqarardi.
- **Verification:** `alembic check` bo'sh diff; `EXPECTED_DEFINER_FUNCTIONS` tegilmadi (funksiya ATAYIN `SECURITY DEFINER` emas).
- **Committed in:** `ef0614d`

**4. [Rule 3 — Bloklovchi] Test teardown'lari bozorni qoralamaga qaytaradi**

- **Found during:** Task 3
- **Issue:** Bu rejaning **eng katta ta'sir doirasidagi** topilmasi. `0013` ning triggeri qo'shilgach `cleanup_two_markets()` **yiqildi**: seed bozorlarni `INSERT INTO markets (id, name)` bilan yaratadi va `markets.is_active` `DEFAULT true` — ya'ni ular FAOL, teardown esa ularni to'g'ridan-to'g'ri o'chiradi. O'lchangan xato: `psycopg.errors.CheckViolation: market <uuid> is active and cannot be deleted (WR-02)`. Bu `two_markets` fixture'iga tayanadigan **butun integratsiya va tenancy to'plamini** qizartirardi (o'lchandi: `test_wizard_flow.py` ning 19 testi ERROR holatiga tushdi).
- **Fix:** Uchta joyda o'chirishdan **bir satr oldin** bayroq tushiriladi: `fixtures/two_markets.py::cleanup_two_markets()`, va `test_market_calendar.py` ning ikkita probe fixture'i (ular uchun `_drop_probe_market()` yordamchisi yozildi). Har uchalasiga **nega** kerakligi va **nega bu zaiflashtirish emasligi** yozildi.
- **Nega bu to'g'ri yechim:** naqsh YANGI EMAS — `fixtures/market_domain.py::cleanup_market_domain()` 02-04 dan beri aynan shu qadamni o'zgarmaslik triggerlari uchun bajaradi va uning docstringi buni «semantik jihatdan HALOL» deb asoslaydi (qator bir necha satr keyin butunlay o'chiriladi). Muqobil yechim — triggerni ega roliga istisno berish — kafolatni butunlay bekor qilardi, chunki migratsiya ham, `psql` ham aynan ega bilan ishlaydi.
- **Verification:** to'liq `pytest` → **1028 passed**; `pytest tests/tenancy` → **326 passed**.
- **Committed in:** `ef0614d`

**5. [Rule 2 — Yetishmayotgan funksiya] `add_discovery_run()` yordamchisi**

- **Found during:** Task 3
- **Issue:** Seed B bozoriga ATAYIN kashfiyot yugurishi yozmaydi («bo'sh ro'yxat» stsenariysi 03-06 uchun kerak). Lekin kaskad testining cross-tenant nazorati B da **to'rtala jadvalda ham** qator bo'lishini talab qiladi — aks holda `DELETE FROM nvr_discovery_runs` dan `WHERE market_id` predikati yo'qolgan taqdirda ham test yashil qolardi.
- **Fix:** Seed asimmetriyasi SAQLANDI, kerak bo'lgan test qatorni `add_discovery_run()` bilan o'zi qo'shadi. Yordamchi 03-06 uchun ham ishlaydi: `status="queued"` bilan chaqirilganda qisman UNIQUE indeks ishga tushadi va 409 stsenariysini beradi.
- **Verification:** ikkala guard testi ham to'rtala jadvalni o'lchaydi va yashil.
- **Committed in:** `ef0614d`

### Rejadan ataylab chetlangan bandlar (sabab bilan)

**A. `docker compose --profile migrate run --rm migrate alembic ...` BAJARIB BO'LMADI — muqobil, KUCHLIROQ yo'l bilan o'lchandi.**
Compose `db` xizmati xost portini bog'lay olmadi: `ports are not available: exposing port TCP 127.0.0.1:5432 -> listen tcp4 127.0.0.1:5432: bind: An attempt was made to access a socket in a way forbidden by its access permissions` — Windows ning zahiralangan (Hyper-V) port diapazoni. Bu **muhit sharti**, kod bilan bog'liq emas.
Muhimi: pytest to'plami compose `db` ga UMUMAN tayanmaydi — `tests/conftest.py::pg_container` **testcontainers** bilan o'z Postgres'ini ko'taradi va `migrated` fixture'i `alembic upgrade head` ni aynan o'sha yerda bajaradi. Rejaning uchala migratsiya mezoni (`upgrade head` / `downgrade 0011` + qayta `upgrade` / `check`) aynan shu yo'lda, **nol holatdan qurilgan** bazada o'lchandi (yuqoridagi jadval). Bu compose'dagi mavjud, allaqachon migratsiya qilingan bazadan kuchliroq: u `ops/db/init` rollarini ham noldan qo'llaydi.

**B. `npm --prefix frontend test` ning vitest qismi bu worktree'da ishlamaydi.**
`frontend/node_modules` worktree'da o'rnatilmagan (`vitest` bajariladigan fayl topilmadi). `node --test` qismi tashqi binarga muhtoj emas va **60/60 yashil**. Vitest'ning 74 testi bu reja bilan bog'liq emasligi mexanik tasdiqlandi: `git diff HEAD~3 --stat -- frontend/` **bo'sh** — birorta frontend fayli tegilmagan.

**C. `requirements mark-complete` ATAYIN BAJARILMADI.**
Reja frontmatter'ida `requirements: [CAM-01, CAM-08]` bor, lekin bu reja ularning birortasini ham bajarmaydi — u faqat **ma'lumot modelini** qo'yadi. CAM-08 ning ISAPI kashfiyoti hali yozilmagan (03-05/03-06). 03-01 ham aynan shu sababdan belgilamagan va `REQUIREMENTS.md` talablarni **faza darajasida** belgilaydi; belgilash `03-11` ning zimmasida.

**D. Rejaning `key_links` bandi O'Z `<action>` bandiga ZID edi — NIYAT bajarildi, mexanizm repozitoriyning o'zinikidan olindi.**
`key_links` `0013` ni `MARKET_DELETE_DRAFT` ga **`op.replace_entity`** orqali bog'lashni talab qiladi (`pattern: "replace_entity"`). Ammo shu rejaning `<action>` bandi aynan teskarisini yozadi: «`0011` da bu qanday qilingan bo'lsa **aynan o'shani** takrorlaydi va **yangi mexanizm o'ylab topmaydi**». O'lchandi — `0011_weekday_choice.py` da `replace_entity` **umuman ishlatilmaydi**, u `drop_entity(ESKI)` + `create_entity(YANGI)` juftligidan boradi (204–205 va 212–213-qatorlar), va uning docstringi buning **nega** shundayligini ham yozadi (`drop_entity()` faqat imzo bilan ishlaydi, `create_entity()` esa tanani yozadi). Ikkalasi bir vaqtda mumkin emas.
Bajarilgani: **niyat** — funksiya ta'rifi almashtiriladi va `downgrade()` eskisini qaytaradi — repozitoriyning O'Z mexanizmi bilan. Yangi konvensiya kiritilmadi. Haqiqiy da'vo (`0013` funksiya tanasini almashtiradi) `migration_roundtrip` bilan tasdiqlandi: `downgrade 0011` dan keyin NVR jadvallari **0/4**, qayta `upgrade` dan keyin **4/4**, va ikkala holatda ham `alembic check` **bo'sh diff**.

**E. Rejadagi test sanog'i bir qadam xato edi (mezon baribir bajarildi).**
Mezon: «kamida 6 ta test o'tadi (**03-01 dagi 3** + yangi 3)». O'lchandi — 03-01 o'sha faylga **to'rtta** test qo'ygan (`test_audit_log_deliberately_survives_market_deletion` ham o'sha rejaning Rule 2 tuzatishi edi), ya'ni jami **7**. «Kamida 6» sharti ikkala hisobda ham bajariladi.

**F. STATE.md / ROADMAP.md TEGILMADI** — orkestrator zimmasida (to'lqin birlashgandan keyin).

---

**Total deviations:** 5 auto-fixed (4 × Rule 3, 1 × Rule 2) + 6 ta hujjatlashtirilgan chetlanish (shundan **ikkitasi** — D va E — rejaning O'ZIDAGI ziddiyat)
**Impact on plan:** Scope creep yo'q. To'rtala Rule 3 tuzatishi ham rejaning O'Z maqsadini bajarilishi mumkin holga keltirdi — usiz `alembic check`, `test:tenancy` yoki butun integratsiya to'plami qizil qolardi.

## Issues Encountered

1. **Trigger fixture teardown'ini yiqitdi va bu KUTILMAGAN EDI.** Reja `<action>` bandida «trigger `market_delete_draft()` ni bloklamasligi kerak» deb ogohlantirgan, lekin **testlarning O'Z teardown'lari** haqida hech nima demagan. Ular esa mahsulot yo'lidan emas, xom `DELETE FROM markets` dan boradi — ya'ni aynan trigger to'sishi kerak bo'lgan yo'ldan. Topilma darhol ko'rindi (`CheckViolation` xabari aniq edi), lekin u rejadagi ta'sir doirasidan kengroq bo'ldi: `files_modified` da bo'lmagan uchta fayl tahrirlandi.
2. **Autogenerate indekslarni ko'rmadi.** `op.create_index(...)` yolg'iz o'zi yetarli emasligi faqat `test_autogenerate_is_empty` qizarganda ma'lum bo'ldi. Reja `<action>` da indekslarni faqat migratsiyada yaratishni yozgan edi — ya'ni bu band bajarilsa ham natija qizil bo'lardi.
3. **Compose `db` xizmati ishga tushmadi** (Windows port diapazoni). Kod bilan bog'liq emas; verifikatsiya testcontainers yo'lidan olindi (chetlanish A).

## Known Stubs

Yo'q. Bu reja stub qoldirmaydi — u sxema va uning invariantlarini qo'yadi. `tests/fixtures/nvr_domain.py` dagi `NVR_PASSWORD_PLACEHOLDER` **stub emas, ataylab qilingan qaror va nomi buni ochiq aytadi**: seed sirni HOSIL QILMAYDI (Fernet kaliti test muhitida yo'q va uni shu yerda yasash shifrlash kontraktining ikkinchi manbaini tug'dirardi). Qator faqat ustunning mavjudligini va composite FK ning ishlashini tekshiradi; haqiqiy shifrlash **03-04** da o'z testi bilan keladi.

## Threat Flags

Yo'q. Yangi tarmoq endpoint'i, auth yo'li yoki fayl kirish naqshi kiritilmadi. Sxema o'zgarishi ishonch chegarasida — LEKIN u rejaning `<threat_model>` ida allaqachon ro'yxatga olingan va **hammasi `mitigate` sifatida bajarildi**:

| Threat | Holat |
|---|---|
| T-03-13 (shifrmatn auditga tushishi) | ✅ `nvr_credentials` triggersiz; `pg_trigger` bo'yicha qulflangan |
| T-03-14 (cross-tenant kamera) | ✅ composite FK + RLS ENABLE/FORCE; `test_meta.py` avtomatik qamradi |
| T-03-15 (dublikat kamera) | ✅ `UNIQUE (market_id, nvr_id, channel_no)`; `23505` o'lchandi |
| T-03-16 (parallel kashfiyot) | ✅ qisman UNIQUE; predikat enum'dan hosila va `pg_index.indpred` bo'yicha tekshiriladi |
| T-03-17 (faol bozorning o'chirilishi) | ✅ `BEFORE DELETE` trigger; ikki tomonlama test |
| T-03-18 (kaskaddan tushib qolish) | ✅ 03-01 darvozasi qizardi va qayta yashil bo'ldi |
| T-03-19 (bir xil `tunnel_subnet`) | ✅ global qisman UNIQUE; istisno sababi bilan `INDEX_EXCEPTIONS` da |
| T-03-SC (paket o'rnatish) | ✅ **birorta yangi paket qo'shilmadi** — `git diff HEAD~3 --stat` da `pyproject.toml`/`uv.lock` yo'q |

## Next Phase Readiness

**03-04 (shifrlash) uchun tayyor:** `nvr_credentials.password_encrypted` (`bytea`, `octet_length > 0` CHECK) va `key_version` (`smallint`, rotatsiya kuzatuvi) mavjud. Seed'dagi `NVR_PASSWORD_PLACEHOLDER` **almashtirilishi kerak** — u ataylab Fernet tokeni emas.

**03-05 (ISAPI klienti) uchun tayyor:** `nvr_devices` da `host`/`port`/`use_tls`/`rtsp_port`/`rtsp_port_assumed` bor; `cameras` da upsert nishoni — `uq_cameras_market_id_nvr_id_channel_no` (`ON CONFLICT` aynan shunga). ⚠ `name_overridden` va `is_archived` bayroqlarini upsert **hurmat qilishi shart** (D-10 / SC#2).

**03-06 (job) uchun tayyor:** `nvr_discovery_runs` va uning qisman UNIQUE indeksi; 409 ni `23505` dan hosil qilish yo'li ochiq. `add_discovery_run(conn, rows, status="queued")` yordamchisi aynan shu testni yozish uchun mavjud.

**03-07 (API) uchun eslatma:** `error_code` — **kod, matn emas**; uning uch joyli reyestri (`MARKET_ERROR_CODES` / `api-types.ts` / `messages/*.json`) bu rejada TEGILMADI, chunki hali birorta endpoint yo'q.

**Keyingi rejalar uchun ogohlantirish:** yangi tenant jadvali qo'shgan har qanday reja **besh joyni** ham yangilashi shart va **`market_delete_draft()` kaskadini ham** — aks holda `test_market_delete_guard.py` darhol qizaradi (bu reja buni o'z tajribasida ko'rdi).

## Self-Check: PASSED

- **Fayllar:** 15/15 mavjud (5 yangi + 10 o'zgargan)
- **Commitlar:** 3/3 mavjud (`77401e0`, `13a2b5d`, `ef0614d`)
- **`contains` shartlari:** 5/5 — `name_overridden` (`models/nvr.py`), `NVR_TENANT_TABLES` (`0012`), `market_delete_draft` (`0013`), `channel_no` (`test_nvr_domain_meta.py`), `market_id` (`fixtures/nvr_domain.py`)
- **`min_lines`:** `models/nvr.py` — 120 talab, **525** mavjud
- **Darvozalar:** `pytest` → **1028 passed**; `pytest tests/tenancy` → **326 passed**; `ruff check` + `ruff format --check` + `mypy` → **exit 0**; `alembic check` → **bo'sh diff**
- **Ish daraxti:** ikkala sabotajdan keyin ham **toza** (`git status --short` bo'sh)

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
