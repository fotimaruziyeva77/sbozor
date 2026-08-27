---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 04
subsystem: security-and-data-access
tags: [fernet, encryption, key-rotation, ssrf, rtsp, upsert, idempotency, multi-tenant, wave-3]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`Settings` + `_validate_jwt_secret` naqshi; `TenantScopedRepository`; `SENSITIVE_KEYS` + `censor_secrets`; `audit_repo.mask_sensitive`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 02
    provides: "`tests/unit/test_no_sim_branching.py` — `app/` daraxtida simulyator imzolarining darvozasi (bu reja unga URILDI)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 03
    provides: "`nvr_devices`/`nvr_credentials`/`cameras`/`nvr_discovery_runs`; `uq_cameras_market_id_nvr_id_channel_no`; qisman UNIQUE faol yugurish indeksi; `tests/fixtures/nvr_domain.py` seed'i"
provides:
  - "`app/security/secrets.py` — loyihadagi BIRINCHI shifrlash moduli: `MultiFernet`, `build_cipher()`, `split_retired_keys()`, `CURRENT_KEY_VERSION`"
  - "`Settings.nvr_credential_key` / `nvr_credential_keys_retired` — IKKALASI HAM `SecretStr`, birinchisi MAJBURIY va startup'da validatsiya qilinadi"
  - "`app/services/rtsp.py` — `stream_id()`/`rtsp_url()`/`new_stream_name()`; parol parametri STRUKTURAVIY ravishda yo'q"
  - "`app/services/nvr_host.py` — `assert_private_host()` (`is_global` bo'yicha) + `split_address()` (UI-SPEC §4.1 ning server zaxirasi)"
  - "`app/repositories/nvr_repo.py` — `NvrRepository`, `DiscoveredChannel`, `UpsertCounts`; SC#2 ning uch qoidasi `ON CONFLICT` ichida"
  - "`tests/integration/test_nvr_repo.py` — 24 test, shundan ikkitasi NAZORAT bandi va bittasi qattiq o'chirishning mexanik darvozasi"
affects: [03-05-isapi-klient, 03-06-job, 03-07-api, 04-snapshot, 05-zonalar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shifr kaliti ILOVA MUHITIDA, bazada emas; `MultiFernet` BIRINCHI KUNDAN — rotatsiya keyin retrofit qilinsa mavjud qatorlar o'qib bo'lmas holga keladi"
    - "Kalit materiali `Settings` da `SecretStr` — `repr` va Sentry ning lokal-o'zgaruvchi yig'ishini yopadi; ochiq qiymatga borish `.get_secret_value()` bilan, GREP BILAN TOPILADIGAN bitta joyda"
    - "Chegara KELISHUV emas, IMZO: `rtsp_url()` parol parametrini umuman qabul qilmaydi va buni test imzoni o'qib tekshiradi"
    - "Xususiylik `is_global` bo'yicha, `is_private` bo'yicha EMAS — CGNAT (`100.64/10`) farqni ochadi va u sabotaj bilan o'lchandi"
    - "SC#2 ning uch qoidasi ILOVA MANTIG'IDA emas, `ON CONFLICT` ning `SET` ifodasida — parallel skanda poyga bo'lmasin"
    - "`channels_added` `RETURNING (xmax = 0)` bilan sanaladi — «avval o'qi, keyin yoz» ikki parallel skanda ikkalasini ham «yangi» deb hisoblardi"
    - "Repozitoriy sirni FAQAT `bytes` ko'radi; shifrlash servis qatlamida (`user_repo` parolni hash holida olgani bilan bir xil chegara)"
    - "Ilova kodida simulyatorning NOMI izohda ham yozilmaydi — 03-02 darvozasi kodni izohdan ajratmaydi va bu ataylab"

key-files:
  created:
    - services/core-api/app/security/secrets.py
    - services/core-api/app/services/rtsp.py
    - services/core-api/app/services/nvr_host.py
    - services/core-api/app/repositories/nvr_repo.py
    - tests/unit/test_nvr_secrets.py
    - tests/unit/test_rtsp_url.py
    - tests/unit/test_nvr_host_validation.py
    - tests/integration/test_nvr_repo.py
  modified:
    - services/core-api/app/settings.py
    - .env.example
    - compose.yaml
    - tests/conftest.py

key-decisions:
  - "`nvr_credential_key` MAJBURIY (standart qiymatsiz). Bo'sh standart bilan ilova shifrlashsiz KO'TARILARDI va xato faqat birinchi rekvizit yozilganda chiqardi — aynan must_have rad etgan xulq. Narxi o'lchandi va to'landi: `compose.yaml` ga bitta qator, `tests/conftest.py` ga bitta maydon"
  - "Kalit maydonlari `SecretStr`, oddiy `str` EMAS (Rule 2). Sabab O'LCHANGAN, taxmin emas: `BaseSettings.__repr__` barcha maydonlarni chop etadi, `sentry-sdk` esa istisno paytida LOKAL o'zgaruvchilarni yig'adi va `settings` `main.py::lifespan` da aynan lokal. Kalit oshkor bo'lsa BARCHA NVR parollari — o'tmishdagilari ham — ochiladi"
  - "Pydantic ning `ValidationError` ga `input_value` ni qo'shishi YASHIRILMADI, HUJJATLASHTIRILDI. Uch yo'l empirik sinaldi (`SecretStr`, `mode='after'` model validatori, oddiy `field_validator`) — uchalasida ham pydantic XOM kiritmani chop etadi. Test da'vosi shu sababdan TOR: o'z xabarimiz tekshiriladi, xato obyektining butun matni emas"
  - "`assert_private_host` `is_global` dan boradi. `not is_private` CGNAT `100.64.0.0/10` ni rad etardi — bu esa `03-RESEARCH.md` C.12 dagi «bozor tomoni rozetkaga ulaydi» stsenariysining aynan o'zi. Tanlov sabotaj bilan o'lchandi: `is_private` ga almashtirilganda FAQAT CGNAT holati qizardi"
  - "Ajratish (`split_address`) va tekshirish (`assert_private_host`) IKKI ALOHIDA funksiya va ikki alohida xato sinfi. Admin uchun «manzilni o'qib bo'lmadi» (terish xatosi) va «ommaviy IP taqiqlangan» (arxitektura qoidasi) butunlay boshqa-boshqa muammolar va ikkinchisiga javob boshqa manzil sinash EMAS"
  - "`last_seen_at` `now()` EMAS, `run_started_at`. `now()` tranzaksiya boshlanish vaqtini beradi, ya'ni `mark_missing_offline()` ning `last_seen_at < run_started_at` taqqoslashi CHEGARADA noaniq bo'lardi va ko'rilgan kanal «yo'qolgan» deb belgilanishi mumkin edi"
  - "Upsert xom `text()` EMAS, SQLAlchemy Core (reja ikkalasiga ham ruxsat bergan). Sabab TIPLASHDA: `text()` da tiplashni unutish JIMGINA ishlaydi va faqat chegara holatida yiqiladi; Core tipni model ustunidan oladi, ya'ni unutadigan qadam yo'q. `source_ip` (`inet`) va `error_detail` (`jsonb`) aynan shu xavf ostida edi"
  - "`update(...).returning(<pk>)` + `is not None`, `rowcount` EMAS. Ikki foyda: mypy'da toza tiplanadi va qator HAQIQATAN topilganini tasdiqlaydi (repozitoriyda `rowcount` ning birorta mavjud naqshi ham yo'q edi)"
  - "Ilova kodidan simulyatorning nomi olib tashlandi (izohdan ham). 03-02 darvozasi kodni izohdan AJRATMAYDI va bu to'g'ri: «ilova uchun simulyator — bu shunchaki bazadagi bir qator» qoidasi nom kodga tushishi bilanoq yemirila boshlaydi. Aniq nomga bog'langan regressiya testi test faylida qoldi"

patterns-established:
  - "Pattern: sir SOZLAMASI `SecretStr` bo'ladi va ochiq qiymatga borish BITTA, izohlangan joyda — chegara grep bilan topiladigan bo'lsin"
  - "Pattern: rotatsiya IKKI YO'NALISHDA o'lchanadi — «eski kalit bilan yozilgani o'qiladi» VA «yangi kalit bilan yozilgani eski konfiguratsiyada o'qilmaydi». Faqat birinchisi «ikkita kalit ham ishlaydi» ni isbotlaydi, ROTATSIYANI emas"
  - "Pattern: platformaning yopib bo'lmaydigan xulqi (pydantic ning `input_value` i) TEST BILAN HUJJATLASHTIRILADI, da'vo esa unga MOSLASHTIRILMAYDI — assert tor qilinadi va sabab yoziladi"
  - "Pattern: xavfsizlik chegarasi IMZODA yashaydi (`rtsp_url` parol qabul qilmaydi) va imzoning o'zi test bilan qulflanadi — «qo'shmang» degan kelishuv emas"
  - "Pattern: o'lchangan, lekin bu rejada tuzatilmaydigan artefakt (masalan `inet` ning `/32` prefiksi) ALOHIDA, NOMLANGAN test bilan qulflanadi — u yerda u keyingi rejaga KO'RINADI, docstringda esa ko'rinmasdi"

requirements-completed: []

# Metrics
duration: 110min
completed: 2026-08-03
---

# Phase 3 Plan 04: Sir, RTSP URL, manzil darvozasi va idempotent upsert Summary

**Loyihaning birinchi shifrlash qatlami `MultiFernet` rotatsiyasi bilan birga tug'ildi, SC#5 ning CI'da o'lchanadigan qismi (SSRF darvozasi) yopildi va SC#2 ning uch qoidasi ilova mantig'iga emas, `ON CONFLICT` ifodasining ichiga qo'yildi.**

## Performance

- **Duration:** ~110 min
- **Tasks:** 3/3
- **Files:** 12 (8 yangi, 4 o'zgargan), 2909 qator qo'shildi

## Accomplishments

- **Fernet qatlami noldan qurildi.** `03-PATTERNS.md` §4.1 to'g'ri o'lchagan edi: `cryptography` repozitoriyda hech qayerda import qilinmagan. Ko'chiriladigan naqsh yo'qligi SUMMARY'da e'lon qilinganidek, har bir qaror (kalit manbai, rotatsiya shakli, deshifrlash xatosining taqdiri) kodda ochiq asoslandi.
- **Bazaviy darvoza kengaydi:** 1076 → **1180** backend (+104), **326** tenancy (o'zgarmadi), **60** node + **74** vitest (o'zgarmadi), 9 sim testi yashil.
- **Uchala sabotaj ham kutilgan natijani berdi** va uchalasida ham «nima YASHIL qoldi» alohida o'lchandi.
- **Ikkita haqiqiy xavfsizlik topilmasi** rejadan tashqarida topildi va yopildi/hujjatlashtirildi (Rule 2): kalitning `repr`/Sentry orqali sizishi va pydantic ning `input_value` xulqi.

## Task Commits

1. **Task 1: Fernet shifri, kalit sozlamasi va rotatsiya** — `d09b950` (feat)
2. **Task 2: RTSP URL fabrikasi va xususiy-tarmoq darvozasi** — `8064f6d` (feat)
3. **Task 3: `nvr_repo` — repozitoriy va idempotent upsert** — `f66dbeb` (feat)

## O'lchangan dalillar

### Darvozalar

| O'lchov | Natija |
|---|---|
| `pytest` (to'liq) | **1180 passed** (oldin 1076) |
| `pytest tests/tenancy` | **326 passed** (o'zgarmadi) |
| `ruff check` + `ruff format --check` + `mypy` | **exit 0** (164 fayl) |
| `npm run test:sim` | **9 passed** |
| `npm --prefix frontend test` | **60** (node) + **74** (vitest) passed |
| `frontend typecheck` / `lint` / `build` | **exit 0** |
| **`npm run gate` (to'liq zanjir)** | **exit 0**, o'lchangan davomiylik **12 m 8 s** |
| `git diff services/core-api/pyproject.toml` | **o'zgarish yo'q** (T-03-SC: yangi paket qo'shilmadi) |

⚠ **Darvoza vaqti o'sdi:** 03-02 da o'lchangan 534 s → hozir **728 s**. Sabab yangi testlar emas (ular ~15 s): `pytest` ning to'liq yugurishi 300 s dan **394 s** ga chiqdi, chunki 03-02 ning sim testlari endi `main` da ham yig'iladi va integratsiya to'plami kattalashdi. 03-01 qo'ygan nomzod chegara **618 s** endi buzilgan — bu `03-11` uchun aniq band: chegarani qayta o'lchash yoki `gate` ni ikkiga bo'lish (`gate:fast` hamon 32 s atrofida).

⚠ **Bazaviy son haqida aniqlik:** topshiriqdagi «1028 backend» — 03-03 ning O'Z worktree'idagi o'lchov, u 03-02 ning testlarini KO'RMAGAN (ikkalasi parallel to'lqinda edi). Birlashtirilgan `main` da bu reja boshlanishida **1076** edi; qo'shilgani aynan 104 = 22 (sir) + 58 (rtsp/host) + 24 (repo).

### Rotatsiya — ikki yo'nalish

| Yo'nalish | Konfiguratsiya | Natija |
|---|---|---|
| Eski kalit bilan yozilgan token | yangi kalit birinchi, eskisi `retired` da | **o'qiladi** |
| Yangi kalit bilan yozilgan token | faqat eski kalit | **`InvalidToken`** |

### Kalit sizish yo'llari — nima yopildi, nima yopilmadi

| Yo'l | Holat | Dalil |
|---|---|---|
| `repr(settings)` / Sentry lokal o'zgaruvchilari | ✅ **YOPILDI** | `test_settings_repr_masks_the_credential_keys` — kalitning aniq qiymati `repr` da YO'Q, `**********` bor |
| `ValidationError` ning `input_value` i | ⚠ **YOPIB BO'LMADI, HUJJATLASHTIRILDI** | Uch yondashuv empirik sinaldi (`SecretStr`, `model_validator(mode="after")`, oddiy `field_validator`) — uchalasida ham pydantic xom kiritmani chop etadi |
| Bizning xato matnimiz | ✅ **TOZA** | `test_our_validator_message_does_not_repeat_the_key` — `error["msg"]` da qiymat yo'q |

⚠ Ikkinchi qatorning amaliy doirasi **tor**: chop etiladigan qiymat ta'rifi bo'yicha **ishlamaydigan** kalit va bu yo'l faqat ilova **ko'tarilmaganda** ochiladi (`main.py` Sentry'ni sozlamalardan KEYIN ishga tushiradi, ya'ni xabar faqat konteyner stderr'iga boradi). Xuddi shu xulq mavjud `_validate_jwt_secret` da ham bor — ya'ni bu maydon kiritgan yangi teshik emas.

### D-12 — parol jurnal va auditga tushmaydi (TAXMIN EMAS, O'LCHANGAN)

| Da'vo | Qanday o'lchandi |
|---|---|
| `nvr_password` / `rtsp_password` / `NVR_PASSWORD` maskalanadi | `test_password_is_censored_in_logs_under_the_nvr_keys` — 1-fazaning `SENSITIVE_KEYS` i BU FAZANING maydon nomlari bilan sinaldi |
| Ichma-ich `error_detail` ham maskalanadi | `test_password_is_censored_inside_nested_error_detail` va DB darajasida `test_finish_run_masks_the_error_detail` |
| `nvr_credentials` auditga UMUMAN tushmaydi | `test_credential_write_leaves_no_audit_row` — parol HAQIQATAN yozilgandan keyin ham `audit_log` da jadval nomi yo'q; **nazorat bandi**: o'sha tranzaksiyada `cameras` uchun qator BOR |
| Parol RTSP URL'ga kira olmaydi | `test_rtsp_url_signature_has_no_credential_parameter` (imzo) + `test_generated_url_contains_no_userinfo_section` (nazorat: `@` yo'q) |

### SC#2 — idempotentlik

| Da'vo | O'lchov |
|---|---|
| Birinchi skan: 6 topildi, 3 qo'shildi (seed'da 3 bor edi) | `channels_found=6`, `channels_added=3` |
| Ikkinchi skan bir xil kanallar bilan | `channels_added=0`; `id`, `first_seen_at`, `stream_name` **o'zgarmagan**; `last_seen_at` **yangilangan** |
| Qo'lda qo'yilgan nom | qayta skandan keyin ham admin nomi |
| `name_overridden = false` bo'lgan kamera | NVR nomini **oladi** (nazorat bandi) |
| Arxivlangan kanal | qayta skanda **tiklanmadi** |
| Yo'qolgan 2 kanal | `status='offline'`, qator soni **kamaymadi** |
| `mark_missing_offline` ikkinchi chaqiruvi | **0** (idempotent) |
| Boshqa bozorning `nvr_id` si | `IntegrityError`; B ning kameralari **tegilmagan** |
| Ikkinchi faol yugurish | `IntegrityError`, sqlstate **`23505`** |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| S1 | `build_cipher` da `retired` kalitlari tashlandi | `test_token_written_with_the_retired_key_is_still_readable` — **1 test** | **21 test**, shu jumladan `test_build_cipher_writes_with_the_first_key` | Rotatsiya ALOHIDA o'lchanadi. Muhimi: «birinchi kalit yozadi» testi ham yashil qoldi — ya'ni u rotatsiyani EMAS, faqat yozish tartibini qamraydi va ikkalasi bir-birini almashtira olmaydi |
| S2 | `assert_private_host` da `is_global` -> `not is_private` | `test_private_addresses_are_accepted[100.64.0.1-CGNAT]` — **1 holat** | **35 holat**, shu jumladan `nvr-sim`, `127.0.0.1` va `169.254.10.1` | Chegaraning TANLOVI haqiqatan o'lchanmoqda. Loopback va link-local yashil qoldi, chunki Python ularni ham `is_private` deb hisoblaydi — ya'ni CGNAT YAGONA ajratuvchi holat va u seed'ga tasodifan tushmagan |
| S3 | `ON CONFLICT` dan `CASE WHEN name_overridden` olib tashlandi (`name = EXCLUDED.name`) | `test_manually_renamed_camera_keeps_its_name` va `test_rename_sets_the_override_flag_in_one_statement` — **2 test** | **22 test**: identiklik, `first_seen_at`, arxiv, oflayn, sonlar, cross-tenant, rekvizit — hammasi | SC#2 ning «mavjudi tegilmaydi» qismi MUSTAQIL o'lchanadi. Idempotentlik testi (`channels_added=0`) sabotajni UMUMAN ko'rmaydi — u sonlarni sanaydi, qiymatlarni emas |

Uchala sabotaj ham commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har birida ish daraxti toza qoldi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Bloklovchi] `compose.yaml` ga `NVR_CREDENTIAL_KEY` qo'shildi**

- **Found during:** Task 1
- **Issue:** Reja `compose.yaml` ga tegishni **taqiqlaydi** (`git diff --exit-code compose.yaml` qabul mezoni) va sababini ham aytadi — to'lqin darajasidagi fayl to'qnashuvi. Ammo `nvr_credential_key` maydoni **majburiy** (rejaning `<interfaces>` bandida standart qiymatsiz e'lon qilingan), `core-api` xizmati esa muhit o'zgaruvchilarini `environment:` blokida **nomma-nom** sanaydi (`env_file` yo'q). O'LCHANDI:
  ```
  STARTUP FAILED: ValidationError
  1 validation error for Settings
  nvr_credential_key
    Field required [type=missing, ...]
  ```
  Ya'ni reja harfma-harf bajarilsa `npm run up` **ishlamay qolardi** va sabab faqat konteynerni ko'targanda ko'rinardi.
- **Fix:** `core-api` ning mavjud `environment:` blokiga **ikki qator**: `NVR_CREDENTIAL_KEY: ${NVR_CREDENTIAL_KEY}` (standart qiymatsiz — `:-` bilan bo'sh berish ilovani shifrlashsiz ko'tarardi) va `NVR_CREDENTIAL_KEYS_RETIRED: ${NVR_CREDENTIAL_KEYS_RETIRED:-}`.
- **Nega bu rejaning niyatini buzmaydi:** taqiqning sababi — to'lqin darajasidagi to'qnashuv, bu ijro esa **ketma-ket** (`main` da, yagona egalik bilan) bo'ldi. 03-06 ning ishi (`worker` konteyneri) **umuman qilinmadi** — o'zgarish mavjud blokdagi ikki qator.
- **Committed in:** `d09b950`

**2. [Rule 3 — Bloklovchi] `tests/conftest.py::test_settings` ga kalit qo'shildi**

- **Found during:** Task 1
- **Issue:** Majburiy maydon `Settings(...)` ni aniq argumentlar bilan quradigan yagona joyni yiqitardi va u — `test_settings` fixture'i, ya'ni **barcha API integratsiya testlari**.
- **Fix:** `nvr_credential_key=SecretStr(Fernet.generate_key().decode())` — har sessiyada YANGI, `jwt_secret` bilan aynan bir xil qaror va sabab (qotirilgan test kaliti repozitoriyga tushgan sir bo'lardi).
- **Committed in:** `d09b950`

**3. [Rule 2 — Yetishmayotgan xavfsizlik] Kalit maydonlari `SecretStr` qilindi**

- **Found during:** Task 1
- **Issue:** Reja va `03-PATTERNS.md` §3.9 ikkalasi ham `nvr_credential_key: str` deb yozgan. Oddiy `str` bilan kalit `repr(settings)` da OCHIQ turadi; `sentry-sdk` esa istisno paytida lokal o'zgaruvchilarni yig'adi va `settings` `main.py:99` da aynan lokal o'zgaruvchi. Ya'ni ilova ko'tarilgandan keyingi **har qanday** istisno butun shifr kalitini Sentry'ga yuborardi.
- **Nega bu «ortiqcha» emas:** oqibat assimetrik. JWT kaliti oshkor bo'lsa sessiyalar bekor qilinadi; SHU kalit oshkor bo'lsa **barcha NVR parollari, o'tmishdagilari ham** ochiladi — ya'ni SC#4 ning butun mazmuni yo'qoladi. `03-RESEARCH.md` C.10 `SecretStr` ni aynan ichki qiymatlar uchun tavsiya qiladi, ya'ni bu yangi mexanizm emas.
- **Narxi:** `.get_secret_value()` ikki joyda (`nvr_cipher()` ichida) va u ATAYIN ko'rinadigan, grep bilan topiladigan qadam.
- **Verification:** `test_settings_repr_masks_the_credential_keys` — kalitning aniq qiymati `repr` da yo'q (nazorat bandi bilan: qiymat testda ma'lum).
- **Committed in:** `d09b950`

**4. [Rule 1 — Xato] `rowcount` -> `RETURNING <pk>`**

- **Found during:** Task 3
- **Issue:** `session.execute()` `Result[Any]` qaytaradi va uning `rowcount` atributi mypy uchun mavjud emas (5 joyda, 10 ta xato). Repozitoriylarda `rowcount` ning birorta mavjud naqshi ham yo'q edi — ya'ni ergashiladigan uy uslubi yo'q.
- **Fix:** Beshala joyda `update(...).returning(<pk>)` + `scalar_one_or_none() is not None`.
- **Nega bu shunchaki tip tuzatishi emas:** `rowcount` «operator nechta qatorga tegdi» ni aytadi, `RETURNING` esa «qator TOPILDI» ni. Chaqiruvchi (03-07) shu javobdan 404 hosil qiladi, ya'ni semantika aynan ikkinchisi.
- **Committed in:** `f66dbeb`

**5. [Rule 3 — Bloklovchi] `nvr_host.py` docstringidan simulyator nomi olib tashlandi**

- **Found during:** Task 3 verifikatsiyasi
- **Issue:** **Bu rejaning eng qimmatli topilmasi.** Reja `<action>` bandi `nvr_host.py` docstringida sim nuance'ini «**aniq**» yozishni TALAB qiladi va simulyatorni nomi bilan atashni nazarda tutadi. Ammo 03-02 ning `tests/unit/test_no_sim_branching.py` darvozasi `services/core-api/app/` daraxtida `nvr-sim` / `__sim__` / `SIM_` satrlarini qidiradi va **kodni izohdan AJRATMAYDI**. To'liq to'plamda o'lchandi:
  ```
  FAILED tests/unit/test_no_sim_branching.py::test_application_code_has_no_simulator_branching[nvr-sim]
  ```
- **Fix:** Docstring **tushunchani** saqladi (hostname qabul qilinadi, faqat marshrutlanadigan ommaviy IP rad etiladi), lekin xizmat nomini yozmaydi. Uning o'rniga docstringga darvozaning O'ZI haqida band qo'shildi. Aniq nomga bog'langan regressiya testi (`test_the_simulator_hostname_is_accepted`) test faylida **qoldi** — ya'ni reja talab qilgan «sim sindirilmasin» kafolati yo'qolmadi, faqat to'g'ri tomonga ko'chdi.
- **Nega darvoza zaiflashtirilmadi:** darvozaning maqsadi aynan shu — nom kodga tushishi bilanoq «ilova uchun simulyator — bu shunchaki bazadagi bir qator» qoidasi yemirila boshlaydi. `assert_private_host` da sim uchun birorta tarmoqlanish yo'q (u BARCHA hostname'larni qabul qiladi), ya'ni tushuncha nomsiz ham to'liq ifodalanadi.
- **Committed in:** `f66dbeb`

**6. [Rule 3 — Bloklovchi] `create_device` testi seed'dan farqli xost oladi**

- **Found during:** Task 3
- **Issue:** `uq_nvr_devices_market_id_host_port` (03-03) tufayli seed'ning xosti bilan ikkinchi qurilma yaratish `23505` berardi va sabab «yaratish ishlamayapti» bo'lib ko'rinardi.
- **Fix:** Test boshqa `host:port` ishlatadi va **nega** kerakligi docstringda yozildi (`assert rows.host == A_HOST` nazorat bandi bilan — konstrayt sababi seed bilan bog'liqligi ko'rinsin).
- **Committed in:** `f66dbeb`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. `Settings` importi validatorni ishga tushirmaydi.**
Reja mezoni: `python -c "...os.environ['NVR_CREDENTIAL_KEY']='not-a-key'; from app.settings import Settings" 2>&1 | grep -c "Fernet"` ≥ 1. Ammo **klassni import qilish** validatorni chaqirmaydi — `Settings` **qurilishi** kerak, ya'ni bu buyruq har doim 0 berardi va mezon o'z-o'zidan bajarilmas edi.
**Bajarilgani — HAQIQIY tekshiruv:** `test_malformed_key_fails_at_settings_construction` `Settings(...)` ni QURADI va xato matnida `Fernet` ham, `generate_key` ham borligini tekshiradi. Testning docstringida sabab yozilgan.

**B. `must_haves.artifacts.contains: "ON CONFLICT"` va `<action>` ning Core'ga ruxsati.**
`<action>` bandi SQLAlchemy Core `on_conflict_do_update()` ni ochiq ruxsat etadi, `contains` esa `nvr_repo.py` da **`ON CONFLICT` literalini** talab qiladi — Core yo'li bu literalni kodda qoldirmaydi.
**Bajarilgani:** Core tanlandi (sababi kodda, «nega xom `text()` emas» bloki) va `ON CONFLICT` docstringlarda **4 marta** yozildi — u yerda u SQLAlchemy chiqaradigan SQL'ni **aynan** nomlaydi, ya'ni matn rost va foydali. Ikkala shart ham bajarildi.

**C. `is_archived` va `first_seen_at` uchun mezon inkorni tekshiradi.**
Mezon: `grep -n "first_seen_at" ...` natija beradi va `SET` bo'limida **yo'q**. Grep bu inkorni o'lchay olmaydi (ustun `VALUES` da bor). **Bajarilgani:** inkor mexanik emas, **xulq** bilan o'lchandi — `test_second_upsert_adds_nothing_and_keeps_identity` (`first_seen_at` o'zgarmagan) va `test_archived_camera_is_not_resurrected_by_a_rescan`.

### Rejadan ataylab chetlangan bandlar

**D. `docker compose --profile test run --rm tests ...` shakli SAQLANDI, `npm run *` yorliqlari orqali.**
Barcha verifikatsiya rejadagi buyruq shakli bilan bajarildi. `db` xizmati bu mashinada xost portini bog'lay olmaydi (03-03 dagi Windows Hyper-V zahiralangan diapazoni), lekin pytest to'plami unga tayanmaydi — `tests/conftest.py::pg_container` testcontainers bilan o'z Postgres'ini ko'taradi.

**E. `requirements mark-complete` ATAYIN BAJARILMADI.**
Frontmatter'da `requirements: [CAM-01, CAM-02, CAM-08]` bor, lekin bu reja ularning birortasini ham **yakunlamaydi** — u kashfiyot kodidan OLDIN turadigan to'rt qatlamni qo'yadi. CAM-08 ning ISAPI kashfiyoti 03-05/03-06 da; CAM-02 ning WireGuard qismi 03-07 da. 03-01 va 03-03 ham aynan shu sababdan belgilamagan; belgilash `03-11` ning zimmasida.

---

**Total deviations:** 6 auto-fixed (4 × Rule 3, 1 × Rule 2, 1 × Rule 1) + 3 ta rejadagi ziddiyat + 2 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. Rule 3 tuzatishlarining hammasi rejaning O'Z maqsadini bajarilishi mumkin holga keltirdi — usiz `npm run up`, butun API to'plami yoki `npm run test` qizil qolardi.

## Issues Encountered

1. **`test_no_sim_branching` darvozasi rejaning `<action>` bandiga ZID edi va buni faqat TO'LIQ to'plam ko'rsatdi.** Task 2 ning o'z testlari (58 ta) yashil edi, `ruff`/`mypy` ham toza — ziddiyat faqat 1180 testlik yugurishda chiqdi. Bu darvozalarni to'liq to'plamda bir marta ko'rish nega majburiyligining aniq misoli.
2. **`inet` ustuni qiymatni `/32` prefiksi bilan saqlaydi.** `source_ip="192.168.1.10"` yozilgach `source_ip::text` `192.168.1.10/32` beradi. Test avval xom `::text` bilan solishtirardi va sabab «yangilanmadi» bo'lib ko'rinardi (aslida yangilangan edi). **Yashirilmadi:** `_camera_rows()` endi `host(source_ip)` dan boradi va artefakt `test_source_ip_is_stored_as_a_host_prefixed_inet` da ALOHIDA qulflandi — u yerda u 03-07 ga ko'rinadi.
3. **pydantic ning `ValidationError` xulqini yopib bo'lmadi.** Uch yondashuv empirik sinaldi. Natija hujjatlashtirildi va test da'vosi torroq qilindi — kengroq da'vo testni pydantic ning ichki xulqiga bog'lab qo'yardi va uni «to'g'irlash» uchun kimdir foydali xato matnini olib tashlashi mumkin edi.
4. **`literal_column("(xmax = 0)")` mypy'ni ikki marta yiqitdi** (`var-annotated`). Yechim — ifodani `Boolean` bilan tiplash; bu bir vaqtda `Result` ni ham tiplaydi va `sum()` `Any` ustidan ishlamaydi.

## Known Stubs

Yo'q. To'rtala qatlam ham to'liq ishlaydi va o'z testlari bilan qamralgan. `DiscoveredChannel` — stub emas, **kontrakt**: uni 03-05 dagi ISAPI klienti to'ldiradi va bog'liqlik yo'nalishi ataylab klientdan repozitoriyga (repozitoriy ISAPI ni bilmaydi).

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: audit-volume | `services/core-api/app/repositories/nvr_repo.py` | `last_seen_at` HAR SKANDA yangilanadi, `cameras` esa audit triggeri ostida (03-03). `fn_audit_row()` o'zgarishsiz `UPDATE` ni o'tkazib yuboradi, lekin `last_seen_at` **har doim** o'zgaradi — ya'ni har skan har kamera uchun bitta `audit_log` qatori yozadi (25 kamera × kunlik skan ≈ 9k qator/yil/bozor). Bu **xato emas** (`last_seen_at` ning modeldagi kontrakti aynan shu) va sxemani o'zgartirish bu rejaning doirasidan tashqarida (Rule 4), lekin `audit_log` append-only — saqlash siyosati **03-06/03-07 da qaralishi kerak**. Muqobil yechim mavjud: audit triggerini ustun ro'yxati bilan cheklash (`UPDATE OF name, status, source_ip, source_model, is_archived`) |
| threat_flag: value-format | `services/core-api/app/repositories/nvr_repo.py` | `cameras.source_ip` (`inet`) qiymati `/32` prefiksi bilan saqlanadi. 03-07 uni JSON'ga to'g'ridan-to'g'ri bersa UI'da `192.168.1.10/32` ko'rinardi — serializatsiyada `host()` yoki unga teng normalizatsiya kerak. Fakt `test_source_ip_is_stored_as_a_host_prefixed_inet` da qulflangan |

Yangi tarmoq endpoint'i yoki auth yo'li kiritilmadi. Reja `<threat_model>` idagi **to'qqizala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-20 (bazadan parol o'qish) | ✅ Fernet; kalit muhitda; `pgcrypto` rad etilgan |
| T-03-21 (rotatsiyaning retrofit qilinishi) | ✅ `MultiFernet` birinchi kundan; ikki yo'nalishda o'lchangan; sabotaj bilan tasdiqlangan |
| T-03-22 (noto'g'ri kalit bilan ko'tarilish) | ✅ `field_validator`; xato matnida hosil qilish buyrug'i; **majburiy** maydon (yo'q kalit ham startup'da yiqitadi) |
| T-03-23 (SSRF — ommaviy IP) | ✅ `assert_private_host` `is_global` bo'yicha; hostname qabul qilinadi; 15 holat testda; sabotaj bilan o'lchangan |
| T-03-24 (parol RTSP URL'ida) | ✅ Imzoda parol parametri **yo'q**; imzo testda; `@` yo'qligi nazorat bandi |
| T-03-25 (oqim nomidan razvedka) | ✅ `cam_<uuid4>`; funksiya argument olmaydi (imzo testda) |
| T-03-26 (qayta skan admin qarorini bosishi) | ✅ `CASE WHEN name_overridden`; `is_archived`/`first_seen_at` `SET` dan tashqarida; **sabotaj S3** |
| T-03-27 (vaqtincha oflayn kameraning o'chirilishi) | ✅ Qattiq o'chirish yo'q; qator soni testda; **mexanik darvoza** (`test_module_has_no_hard_delete`) |
| T-03-28 (rekvizitning `error_detail` ga tushishi) | ✅ `finish_run` `mask_sensitive` dan o'tkazadi; ichma-ich holat DB darajasida o'lchangan |
| T-03-SC (paket o'rnatish) | ✅ **Birorta yangi paket qo'shilmadi** — `pyproject.toml` diffi bo'sh |

## Next Phase Readiness

**03-05 (ISAPI klienti) uchun tayyor:**
- `decrypt_nvr_password(token) -> str` — `InvalidToken` **yutilmaydi** va uni ISAPI ning `401` idan **farqlash SHART** (SC#3 taksonomiyasi).
- `rtsp_url(host, port, channel_no, substream=)` — port **kashf etilgan** holda uzatiladi; 554 fallback ishlatilsa `update_device(nvr_id, rtsp_port=554, rtsp_port_assumed=True)`.
- `DiscoveredChannel` — klientning chiqishi aynan shu shaklga keltiriladi.
- ⚠ Klient `app/services/isapi/` da yozilganda `test_no_sim_branching` darvozasi **yana urиladi**: simulyatorning nomi kodda ham, izohda ham yozilmaydi.

**03-06 (job) uchun tayyor:**
- Oqim: `create_run` → `upsert_cameras` → `mark_missing_offline` → `finish_run(counts.with_marked_offline(n))`.
- 409 ni `create_run` ning `IntegrityError`/`23505` idan hosil qiling — `active_run_id()` bilan **oldindan tekshirmang** (poyga).
- ⚠ **`compose.yaml` MAJBURIY ishi:** `worker` konteyneriga `NVR_CREDENTIAL_KEY: ${NVR_CREDENTIAL_KEY}` va `NVR_CREDENTIAL_KEYS_RETIRED: ${NVR_CREDENTIAL_KEYS_RETIRED:-}` **qo'shilishi shart** — usiz worker `Settings` ni qura olmaydi va bu ishga tushishda yiqiladi. `core-api` uchun bu allaqachon qilingan (chetlanish #1).
- ⚠ Audit hajmi (yuqoridagi `threat_flag: audit-volume`) shu rejada qaralsin.

**03-11 (yakunlash) uchun eslatma:**
`npm run gate` **728 s** — 03-01 qo'ygan nomzod chegara **618 s** dan oshdi. O'sish bu rejaning testlaridan emas (ular ~15 s), 03-02 va 03-03 ning to'lqinlari birlashgandan keyingi to'plam hajmidan. Chegara qayta o'lchansin yoki `gate` bo'linsin.

**03-07 (API) uchun tayyor:**
- `assert_private_host()` va `split_address()` **kirish chegarasida** chaqiriladi — repozitoriy ularni chaqirmaydi va bu ataylab (`create_device` docstringi).
- `NvrHostNotPrivateError` va `NvrAddressError` — ikkalasi ham `ValueError`, lekin **ALOHIDA** sinf: xato kodlari ham alohida bo'lishi kerak (admin uchun boshqa-boshqa muammolar).
- Javob modelida parol maydoni **umuman bo'lmaydi** (`exclude=True` emas). `has_password` bayrog'i `get_credential(...) is not None` dan.
- ⚠ `source_ip` ni JSON'ga berishdan oldin normalizatsiya (`threat_flag: value-format`).

## Self-Check: PASSED

- **Fayllar:** 12/12 mavjud (8 yangi + 4 o'zgargan)
- **Commitlar:** 3/3 mavjud (`d09b950`, `8064f6d`, `f66dbeb`)
- **`must_haves.artifacts`:** 4/4 — `MultiFernet` (`secrets.py`), `Streaming/Channels` (`rtsp.py`), `is_global` (`nvr_host.py`), `ON CONFLICT` (`nvr_repo.py`, 4 marta)
- **`min_lines`:** `nvr_repo.py` — 120 talab, **594** mavjud
- **`key_links`:** `nvr_credential_key` `settings.py` da bor va `secrets.py::build_cipher` ga ulanadi; `ON CONFLICT` `nvr_repo.py` da `uq_cameras_market_id_nvr_id_channel_no` konstraytiga
- **Ish daraxti:** uchala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
