---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 05
subsystem: isapi-integration
tags: [hikvision, isapi, digest-auth, httpx, tenacity, retry-policy, clock-drift, xml-namespace, defusedxml, discovery, idempotency, wave-4]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 02
    provides: "`nvr-sim` — o'n oltita xato rejimi, `GET /__sim__/attempts` sanog'i, yozib olingan yetti fixture; `tests/fixtures/nvr_sim.py`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 04
    provides: "`nvr_repo.upsert_cameras`/`mark_missing_offline`/`update_device`, `DiscoveredChannel`, `UpsertCounts`; `rtsp.py::stream_id`/`rtsp_url`; `audit_repo.mask_sensitive`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 01
    provides: "`httpx==0.28.1` ISHLAB CHIQARISH bog'liqligi (D-16), `tenacity==9.1.4`, `respx==0.23.1` (dev), `sim`/`slow` markerlari"
provides:
  - "`app/services/isapi/errors.py` — o'n ikki kodli taksonomiya; allowlist KONSTRUKTORDA majburlanadi"
  - "`app/services/isapi/parser.py` — namespace-agnostik parser; IKKALA ISAPI namespace'i; `@size` o'qilmaydi"
  - "`app/services/isapi/client.py` — `httpx.DigestAuth`, TESKARI retry siyosati, `Date` dan erta drift, `assert_supported_device`, `resolve_rtsp_port`"
  - "`app/services/isapi/discovery.py` — orkestratsiya; `taskiq` IMPORT QILINMAYDI; `on_channels_found` callback'i"
  - "`nvr-sim` control-plane'ida ikki yangi maydon: `endpoint_hits` va `no_substream_channels`"
  - "109 yangi test: 66 unit (hermetik) + 43 integratsiya (haqiqiy TCP + Digest)"
affects: [03-06-job, 03-07-api, 03-08-frontend-kopya, 03-11-yakuniy-darvoza, 04-snapshot]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Retry predikati TESKARI va u YAGONA joyda: `_should_retry()` da `httpx.HTTPStatusError` ATAYIN yo'q — sabotaj bilan o'lchandi (0 -> 5 urinish, ya'ni AYNAN qulflash chegarasi)"
    - "Tashxis AUTENTIFIKATSIYADAN OLDIN: rekvizitsiz BITTA `GET` ikkita diagnostikani beradi (`Date` -> drift, `WWW-Authenticate` -> auth rejimi) va qurilmaning qulflash hisoblagichini qo'zg'atmaydi"
    - "5xx `_TransientServerError`, 4xx `httpx.HTTPStatusError` — IKKI ALOHIDA sinf, chunki bitta sinf bo'lganda retry predikati `401` ni tarmoq xatosidan ajrata olmasdi"
    - "Xato ALLOWLIST'i konstruktorda `ValueError` bilan majburlanadi (`assert` EMAS: `python -O` uni ishlab chiqarishda o'chirardi)"
    - "«Chaqirilmadi» da'vosining yagona dalili — SO'ROVLAR SANOG'I: natijadan o'lchab bo'lmaydi, chunki chaqirib-yutgan kod ham bir xil natija beradi"
    - "Namespace testi PARAMETRIZATSIYALANGAN (`namespaced` / `stripped`): sabotaj birinchisini qizartiradi, ikkinchisi yashil qoladi — ya'ni test namespace'ni O'LCHAYDI, boshqa narsani emas"
    - "`NvrError` QIYMAT sifatida ham ishlatiladi (`channel_issues`): `code` + `detail` + allowlist tekshiruvi bir joyda va ikkinchi marta yozilmaydi"

key-files:
  created:
    - services/core-api/app/services/isapi/__init__.py
    - services/core-api/app/services/isapi/errors.py
    - services/core-api/app/services/isapi/parser.py
    - services/core-api/app/services/isapi/client.py
    - services/core-api/app/services/isapi/discovery.py
    - tests/unit/test_isapi_parser.py
    - tests/unit/test_isapi_errors.py
    - tests/integration/test_nvr_errors.py
    - tests/integration/test_nvr_discovery.py
  modified:
    - services/nvr-sim/sim/state.py
    - services/nvr-sim/sim/isapi.py

key-decisions:
  - "TOPILMA (eng qimmatlisi): `DS-7732NI-M4` dumpida `<manufacturer>` maydoni UMUMAN YO'Q, `DS-7616NI-K2` da esa BOR. `manufacturer != 'hikvision'` sharti HAQIQIY 32 kanalli Hikvision NVR ni — Karmananing 25 kanaliga eng yaqin modelni — rad etardi. D-09 ning 25 kanalli SEKIN testi topdi; 6 kanalli standart zanjir buni HECH QACHON ko'rmasdi"
  - "Basic diagnostikasi `nvr_bad_credentials` xulosasidan OLDIN EMAS, challenge SXEMASI bo'yicha bajariladi. Reja aytgan joyda u `test_auth_failure_is_not_retried` ning «urinishlar AYNAN 1» da'vosini buzardi (sanoq 2 bo'lardi). Ajratuvchi belgi — `WWW-Authenticate` da Digest TAKLIF QILINMAGANI; bu real qurilma xulqiga ham MOSROQ"
  - "`_should_retry` `httpx.RemoteProtocolError` ni QAMRAMAYDI (u `ProtocolError` -> `TransportError`, `NetworkError` EMAS). Sabab: u D-05 ning «javobsiz uzilish» alomati va uni qayta urinish chegaraga yana urilardi"
  - "5xx retry qatlamiga BERILISHDAN OLDIN chegara alomatiga tekshiriladi: `stream_limit` ning `503` i qayta urinilmaydi — u qurilmani battar bosardi"
  - "`nvr_stream_limit` ning `silent` shakli XULQ heuristikasi bilan aniqlanadi (shu klientda kamida bitta oqim da'vosi o'tgan) — A.5 ning aynan o'zi. Barcha `RemoteProtocolError` ni chegaraga bog'lash `deviceInfo` uzilishini ham «sessiya limiti» deb ko'rsatardi"
  - "Kanal `id` normallashuvi IKKALA firmware shaklini qamraydi (`1` va `101`), chegaradagi noaniqlik (100+ kanalli NVR) esa OCHIQ hujjatlashtirilgan — yashirin taxmin qabul qilinmaydi"
  - "Parserning `skipped` ro'yxati `error_detail` ga TUSHMAYDI: `ERROR_DETAIL_KEYS` da ro'yxat uchun kalit yo'q (`channel_no`/`channel_name` birlikda) va allowlist zaiflashtirilmaydi. O'tkazib yuborish `structlog` ga nomlangan kalit bilan yoziladi"
  - "Sim'ga IKKI maydon qo'shildi (reja `endpoint_hits` uchun ochiq ruxsat bergan): `endpoint_hits` D-04 tarmoqlanishining yagona dalili, `no_substream_channels` esa `has_substream=False` shoxining yagona sinov yo'li"

patterns-established:
  - "Pattern: sabotaj natijasi IKKI TOMONLAMA yoziladi va «yashil qolgani» ba'zan qizarganidan qimmatroq — S1 da «hech qachon jimgina bo'sh emas» darvozasi YASHIL qoldi, ya'ni u Pitfall 2 ni QAMRAMAYDI"
  - "Pattern: bitta tekshiruv IKKI chaqiruvchida ishlatilsa u FUNKSIYAGA chiqariladi (`assert_supported_device`) — ikki nusxa bo'lganda «tugma rad etadi, job yaratadi» holati tug'ilardi"
  - "Pattern: ilova kodida simulyator NOMI izohda ham yozilmaydi — 03-04 dan meros, va bu rejada YANA bir marta urildi (`parser.py:170`)"
  - "Pattern: sekin test faqat MIQYOSNI o'lchaydi, mantiqni emas — lekin aynan u standart zanjir ko'rmaydigan fixture yo'lini ochadi"

requirements-completed: []

# Metrics
duration: 115min
completed: 2026-08-03
---

# Phase 3 Plan 05: ISAPI klienti, xato taksonomiyasi va kashfiyot Summary

**Loyihaning birinchi chiquvchi HTTP integratsiyasi qurildi: namespace-agnostik parser, o'n ikki kodli xato taksonomiyasi va odatdagiga TESKARI retry siyosati — `401` hech qachon qayta urinilmaydi va buni simulyatordagi urinishlar sanog'i raqam bilan isbotlaydi (sabotajda 0 → 5, ya'ni AYNAN Hikvision qulflash chegarasi).**

## Performance

- **Duration:** ~115 min
- **Tasks:** 3/3
- **Files:** 11 (9 yangi, 2 o'zgargan), ~3180 qator qo'shildi

## Accomplishments

- **SC#3 to'liq yopildi:** o'n ikki xato kodining **har biri** alohida test bilan o'lchanadi va qamrov **mexanik** tekshiriladi (har kod ikki test faylida nomma-nom izlanadi).
- **D-03 ning ikki raqami o'lchandi:** soat farqida urinishlar **0**, `401` da **aynan 1**. Sabotaj bu ikkinchi raqamni **5** ga chiqardi — bu Hikvision hujjatlashtirgan qulflash chegarasining o'zi.
- **Bir haqiqiy, ishlab chiqarishni bloklaydigan xato topildi va tuzatildi** (quyida, Deviation 1): `manufacturer` maydoni yo'q bo'lgan **haqiqiy** Hikvision NVR rad etilardi.
- **Bazaviy darvoza kengaydi:** 1180 → **1289** backend (+109), **326** tenancy (o'zgarmadi), 9 → **52** sim, **60** node + **74** vitest (o'zgarmadi), `npm run gate` → **exit 0 / 12 m 23 s**.
- **`services/core-api/pyproject.toml` TEGILMADI** (T-03-SC): birorta yangi paket qo'shilmadi.

## Task Commits

1. **Task 1: Xato taksonomiyasi va namespace-agnostik parser** — `5ab3531` (feat)
2. **Task 2: `IsapiClient` — Digest, timeout, teskari retry, erta drift** — `18914ef` (feat)
3. **Task 3: Kashfiyot orkestratsiyasi va idempotentlik isboti** — `69d6a2f` (feat)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `app/services/isapi/errors.py` | O'n ikki kod uch guruhda; `AUTH_LOCKING_CODES`; `ERROR_DETAIL_KEYS` **konstruktorda** majburlanadi; `raw` kesiladi va `mask_sensitive` dan o'tadi |
| `app/services/isapi/parser.py` | `local_name()` `rpartition` bilan; `defusedxml`; javob hajmi chegarasi; kanal `id` normallashuvi; kutilgan ildiz topilmasa `NvrError` |
| `app/services/isapi/client.py` | `httpx.DigestAuth`; `_should_retry()`; `greet()` (drift + auth rejimi BIR borishda); A.3 jadvalining satrma-satr xaritalanishi; `resolve_rtsp_port`; `assert_supported_device` |
| `app/services/isapi/discovery.py` | Orkestratsiya; `channels_found` callback'i; `channel_issues`; upsert + `mark_missing_offline` + `update_device` |
| `tests/unit/test_isapi_parser.py` | 44 test, kirish **yozib olingan dumplardan** |
| `tests/unit/test_isapi_errors.py` | 22 test — reyestrning shakli va allowlist darvozasi |
| `tests/integration/test_nvr_errors.py` | 29 test — o'n bir kod, haqiqiy Digest handshake ustida |
| `tests/integration/test_nvr_discovery.py` | 14 test (13 + D-09 ning sekin testi) |
| `services/nvr-sim/sim/state.py` | `endpoint_hits` (faqat o'qishga) va `no_substream_channels` (patchable) |
| `services/nvr-sim/sim/isapi.py` | So'rovlar sanog'i (auth'dan KEYIN); `{ch}02` uchun sozlanadigan `404` |

## O'lchangan dalillar

### D-03 — ikki raqam, va sabotajning uchinchisi

| Da'vo | O'lchov |
|---|---|
| Soat farqi `401` dan **oldin** aniqlanadi | `/__sim__/attempts` **0 → 0** |
| `401` hech qachon qayta urinilmaydi | `/__sim__/attempts` **0 → 1** |
| **Sabotajda** (`httpx.HTTPStatusError` predikatga qo'shildi) | `/__sim__/attempts` **0 → 5** |

⚠ Uchinchi qator eng muhimi: **5** — Hikvision hujjatlashtirgan «~5 xato urinishdan keyin 30 daqiqaga qulflash» chegarasining O'ZI. Ya'ni sabotaj qilingan kod bilan foydalanuvchining **bitta bosishi** hisobni qulflardi va undan keyin to'g'ri parol ham ishlamasdi.

Sabab: `httpx.DigestAuth` har urinishda challenge'ni qayta oladi va **ikki** rekvizit so'rovi yuboradi; `tenacity` ning 3 urinishi bilan bu 5 ta rekvizit urinishiga aylanadi.

### SC#3 — o'n ikki kodning qamrovi (mexanik tekshirilgan)

| Kod | Qayerda o'lchanadi |
|---|---|
| `nvr_bad_credentials` … `device_not_supported` (8 ta) | `test_nvr_errors.py::test_each_failure_mode_produces_its_own_reason_code` — sim rejimi bilan |
| `nvr_unreachable` | `test_unreachable_address_is_diagnosed` (+ `test_slow_device_times_out_instead_of_hanging`) |
| `nvr_stream_limit` | `test_stream_limit_produces_actionable_error[reject]` **va** `[silent]` |
| `nvr_tls_untrusted` | `test_tls_untrusted_is_diagnosed` — transport darajasida, sim rejimi EMAS |
| `channel_offline` | `test_nvr_discovery.py::test_channels_found_counts_offline_channels_too` |

`python -c "... missing=[c for c in NVR_ERROR_CODES if c not in src]"` → **bo'sh** (12/12).

### SC#1 / SC#2 — kashfiyot

| Da'vo | O'lchov |
|---|---|
| Manzil + parol → 6 kamera, nom va IP **NVR javobidan** | `tagahoov` / `1.0.0.208` / `DS-2CD2387G2-LSU/SL` — hammasi dumpdagi HAQIQIY qiymatlar |
| Qurilma pasporti bazaga yoziladi | `serial_number`, `firmware_version`, `last_discovery_at` |
| NVR yo'lida `Video/inputs/channels` **chaqirilmaydi** | `endpoint_hits` = **0** (`InputProxy` = 1, `.../status` = 1) |
| IP-kamerada `InputProxy` **chaqirilmaydi** | `endpoint_hits` = **0**, `Video/inputs/channels` = 1 |
| `channels_found` sub-oqim tekshiruvidan **oldin** | callback chaqirilganda `Streaming/channels/*` sanog'i = **0** |
| `channels_found` oflayn kanallarni ham sanaydi | 8 kanal, 2 tasi oflayn → `channels_found = 8` |
| Ikkinchi skan idempotent | `channels_added = 0`; `id` va `first_seen_at` **o'zgarmagan**; `last_seen_at` yangilangan |
| Yangi kanal qo'shiladi | 6 → 8: `channels_added = 2`, mavjudlarining `id` si o'zgarmagan |
| Yo'qolgan kanal **oflayn**, o'chirilmaydi | qator soni **kamaymadi**, `id` **o'sha**, `channels_marked_offline = 1` |
| Admin nomi saqlanadi, arxiv tiklanmaydi | `Sabzavot qatori (admin nomi)`; `is_archived` = `true` |
| Kamera almashtirilishi auditga tushadi | `source_ip` = `10.20.30.40`, `audit_log` da `cameras`/`update` qatori |
| RTSP porti kashf etiladi va URL'ga yetadi | `rtsp://nvr-sim:10554/Streaming/Channels/301` |
| Sub-oqimi yo'q kanal belgilanadi | kanal 4 → `has_substream = False`, kanal 5 → `True` (nazorat bandi) |
| **D-09:** 25 kanal | `channels_found = 25`, 25 kamera yozuvi (`npm run test:sim:slow`) |

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `ruff format --check` + `mypy` | ✅ exit 0 (177 fayl / 173 manba) |
| `pytest -q` (butun backend) | ✅ **1289** (1180 → **+109**) |
| `pytest tests/tenancy -q` | ✅ **326** (o'zgarmadi) |
| `npm run test:sim` | ✅ **51** (9 → +42) |
| `npm run test:sim:slow` | ✅ **1** (25 kanalli stsenariy) |
| `frontend` node / vitest / typecheck / lint / build | ✅ **60** / **74** / toza / toza / to'liq prerender |
| **`npm run gate`** | ✅ **exit 0** — **12 m 23 s** (742 s) |
| `git diff --exit-code services/core-api/pyproject.toml` | ✅ toza (T-03-SC) |

+109 = 44 (parser) + 22 (errors) + 29 (nvr_errors) + 14 (discovery).

⚠ **Darvoza vaqti:** 03-04 dagi 728 s → **742 s** (+14 s). O'sish 43 ta yangi sim testidan; 03-01 ning nomzod chegarasi (618 s) allaqachon 03-04 da buzilgan edi va **03-11 uchun ochiq band bo'lib qoladi**.

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `local_name` → `lambda tag: tag` | **20 / 66** parser testi, shu jumladan `test_namespaced_xml_parses_the_same_as_plain_xml[**namespaced**]` | `[**stripped**]` va **butun** `test_isapi_errors.py` (22) | Parametrizatsiyaning ikki yarmi ATAYIN ajratilgan: namespace'li holat qizardi, namespace'siz holat yashil qoldi — ya'ni test namespace'ni o'lchayotgani isbotlandi |
| **S2** | `_should_retry` ga `httpx.HTTPStatusError` qo'shildi (D-03 ni buzadi) | **AYNAN BITTA** test: `test_auth_failure_is_not_retried` (`0 → 5` urinish) | **Qolgan 28 tasi**, shu jumladan sakkizala xato-kod xaritasi va `stream_limit` ning ikkala shakli | D-03 ning butun siyosati BITTA test bilan ushlanadi. Xato kodlari to'g'ri qolaveradi — ya'ni «kodlar to'g'ri» tekshiruvi qulflanishdan HIMOYA QILMAYDI |
| **S3** | `mark_missing_offline` chaqiruvi olib tashlandi | **AYNAN BITTA**: `test_missing_channel_goes_offline_and_is_not_deleted` | **12 tasi**, shu jumladan uchala idempotentlik testi | SC#2 ning ikki qoidasi (idempotentlik / yo'qolgan kanal) MUSTAQIL o'lchanadi |
| **S4** | `adminAccesses` e'tiborsiz, `rtsp_port = 554` qotirildi | **AYNAN BITTA**: `test_moved_rtsp_port_reaches_the_generated_url` | **12 tasi** + **butun** `test_nvr_errors.py` (29) | Port kashfiyoti IKKI yo'lda (probe va discovery) mustaqil bajariladi va ikkalasi ALOHIDA o'lchanadi |

Hamma sabotajlar commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi.

### ⚠ S1 ning eng qimmatli natijasi — nima YASHIL qolgani

Namespace buzilganda `test_broken_or_unexpected_xml_raises_instead_of_returning_empty` (20 holat) **YASHIL qoldi**. Sabab: identity `local_name` bilan ildiz nomi **hech qachon** kutilganiga mos kelmaydi, ya'ni parser baribir `NvrError` ko'taradi — **to'g'ri xatoni NOTO'G'RI sababdan**.

Xulosa: «hech qachon jimgina bo'sh natija bermaydi» darvozasi (T-03-34) Pitfall 2 ni **QAMRAMAYDI**. Ikkalasi bir-birining o'rnini bosa olmaydi va `test_namespaced_xml` ning mavjudligi majburiy — bu 03-02 ning S2 sabotajidan («stub `verify()` 8 ta testni yashil qoldirdi») olingan darsning aynan takrori.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Xato] `manufacturer` maydoni YO'Q bo'lgan haqiqiy Hikvision NVR rad etilardi**

- **Found during:** Task 3, D-09 ning 25 kanalli **sekin** testi
- **Issue:** Reja va tadqiqot `manufacturer` maydonini har doim mavjud deb qabul qilgan (A.3: «`manufacturer` Hikvision emas → `device_not_supported`»). **O'lchandi:**
  ```
  DS-7616NI-K2 dumpi  ->  <manufacturer>hikvision</manufacturer>
  DS-7732NI-M4 dumpi  ->  maydon UMUMAN YO'Q
  ```
  Ikkalasi ham **haqiqiy** Hikvision NVR va ikkalasi ham yozib olingan dumpdan. `manufacturer.lower() != "hikvision"` sharti **32 kanalli NVR ni — Karmananing 25 kanaliga eng yaqin modelni — rad etardi**:
  ```
  E   app.services.isapi.errors.NvrError: device_not_supported
  ```
- **Nega CI buni ko'rmasdi:** standart 6 kanalli zanjir `DS-7616NI-K2` fixture'ini ishlatadi va unda maydon **bor**. Nosozlik faqat `DS-7732NI-M4` ga o'tilganda ochiladi — ya'ni **faqat** D-09 talab qilgan sekin testda.
- **Fix:** `assert_supported_device()` — rad etish sharti «maydon **BOR VA** u Hikvision emas» ga o'zgartirildi. Bir vaqtda tekshiruv `client.py` va `discovery.py` dan **bitta funksiyaga** chiqarildi (ikki nusxa bo'lganda «tugma rad etadi, job yaratadi» holati tug'ilardi).
- **Nega darvoza zaiflashmadi:** sim'ning `not_hikvision` rejimi o'zini **ochiq** boshqa ishlab chiqaruvchi deb e'lon qiladi (`Acme Video Systems`) va u hamon rad etiladi — `test_device_not_supported_names_the_device` yashil. Qoldiq xavf (`manufacturer` sizni ISAPI qurilma) kodda **ochiq** hujjatlashtirildi.
- **Committed in:** `69d6a2f`

**2. [Rule 3 — Bloklovchi] `parser.py` docstringidan simulyator nomi olib tashlandi**

- **Found during:** Task 1 verifikatsiyasi
- **Issue:** `parser.py` izohida `services/nvr-sim/sim/isapi.py` ga havola bor edi. 03-02 ning `test_no_sim_branching.py` darvozasi `app/` daraxtida `nvr-sim` satrini qidiradi va **kodni izohdan ajratmaydi** — bu 03-04 boshidan kechirgan holatning aynan takrori (o'shanda `nvr_host.py` docstringida edi).
  ```
  FAILED test_no_sim_branching.py::test_application_code_has_no_simulator_branching[nvr-sim]
    services/core-api/app/services/isapi/parser.py:170
  ```
- **Fix:** Izoh **tushunchani** saqladi (`200 OK` bilan kelgan javob ham xato bo'lishi mumkin), lekin xizmat nomini yozmaydi.
- **Committed in:** `5ab3531`

**3. [Rule 2 — Yetishmayotgan kritik funksiya] Sim control-plane'iga ikki maydon**

- **Found during:** Task 3
- **Issue:** Rejaning `<behavior>` bandi ikkita da'voni talab qiladi, lekin **ikkalasini ham mavjud sim bilan o'lchab bo'lmasdi**:
  1. «IP-kamera yo'lida `InputProxy` **chaqirilmaydi**» — chaqirib, `404` ni yutib, keyin to'g'ri yo'ldan borgan kod **aynan bir xil** kamera yozuvlarini yaratardi;
  2. «Sub-oqimi yo'q kanal uchun `has_substream=False`» — sim barcha mavjud kanallar uchun `{ch}02` ni beradi, ya'ni bu shox **hech qachon** bajarilmasdi.
- **Fix:** `endpoint_hits` (faqat o'qishga, `reset` bilan nollanadi) va `no_substream_channels` (patchable, `offline_channels` bilan bir xil tabiat). Reja Task 3 da control-plane'ga **qo'shimcha maydon** kiritishga ochiq ruxsat bergan.
- **Verification:** `test_nvr_path_never_calls_the_video_inputs_endpoint`, `test_ip_camera_path_never_calls_input_proxy`, `test_channel_without_a_substream_is_flagged`, `test_substream_probe_can_be_switched_off`.
- **Committed in:** `69d6a2f`

**4. [Rule 2 — Yetishmayotgan xavfsizlik] `raw` ning maskalash chegarasi ochiq belgilandi**

- **Found during:** Task 1
- **Issue:** UI-SPEC §7.4 backend `error_detail` ni `mask_sensitive` dan o'tkazishini talab qiladi. Ammo `mask_sensitive` **kalit nomiga** qaraydi va `raw` **ichidagi matnni o'qimaydi** — ya'ni «maskalangan» degan da'vo xom XML uchun **yolg'on xotirjamlik** berardi.
- **Fix:** Filtr baribir qo'llanadi (ichma-ich obyekt kelajakda mumkin), lekin chegara kodda **ochiq** yozildi va **nazorat testi** bilan qulflandi: `test_detail_passes_through_the_key_based_mask` xom matnning maskalanMASLIGINI tasdiqlaydi.
- **Committed in:** `5ab3531`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. Basic diagnostikasining joyi — `test_auth_failure_is_not_retried` bilan ZID edi.**

Reja: *«Basic sinovi … faqat `nvr_bad_credentials` xulosasidan **oldin** va faqat bitta so'rov bilan qilinadi»*, va bir vaqtda: *«`test_auth_failure_is_not_retried` — `/__sim__/attempts` **aynan 1** ekani»*.

Ikkalasi birga bajarilmaydi: Basic sinovi ham rekvizit urinishi va u sanoqni **2** ga chiqarardi.

**Bajarilgani:** ajratuvchi belgi **challenge sxemasi** qilindi — `WWW-Authenticate` da Digest **taklif qilinmaganda** Basic sinovi bajariladi. Bu:
- reja niyatini to'liq bajaradi (Basic **faqat diagnostika**, **faqat bir marta**, avtomatik zaxira **emas** — T-03-36);
- «aynan 1» da'vosini saqlaydi (noto'g'ri parol yo'li bu tarmoqqa **hech qachon** tushmaydi);
- real qurilma xulqiga **mosroq**: `basic` rejimidagi firmware Digest'ni umuman taklif qilmaydi, ya'ni biz uni «sinab ko'rmaymiz», **o'qiymiz**.

**B. Parserning `skipped` ro'yxati `detail` ga qo'shilmadi.**

Reja: *«noaniq qiymat uchun `NvrError` ko'tarilmaydi, kanal o'tkazib yuboriladi va `detail` ga qo'shiladi»*. Ammo `ERROR_DETAIL_KEYS` (UI-SPEC §7.4 [TALAB]) da **ro'yxat uchun kalit yo'q** — `channel_no`/`channel_name` birlikda. Ya'ni harfma-harf bajarish allowlist'ni buzishni talab qilardi.

**Bajarilgani:** o'tkazib yuborish `parse_input_proxy_channels(..., skipped=[...])` orqali chaqiruvchiga beriladi va `discovery`/`client` uni `structlog` ga **nomlangan kalit** bilan yozadi. Allowlist zaiflashtirilmadi; `test_unparseable_channel_is_skipped_and_reported_not_hidden` uni qulflaydi.

**C. `sim_mode` maydon nomlari rejadan farq qiladi.**

Reja B.8 dan `count: 8`, `channels: [3,7]`, `channel: 3, ip: …` yozadi; 03-02 amalga oshirgan control-plane'da esa `channel_count`, `offline_channels`/`removed_channels`, `swapped_channel`/`swapped_ip`/`swapped_model`. Testlar **haqiqiy** maydon nomlarini ishlatadi — sim noma'lum maydonga `400` beradi, ya'ni xato jimgina o'tib ketmasdi.

**D. `sim_mode("slow", delay_ms=15000)` da klient timeout'i qisqartirildi.**

Standart 10 s timeout × 3 urinish har `gate` ga ~45 s qo'shardi. Test klientni 2 s timeout bilan quradi va **aynan shu xulqni** o'lchaydi («urinish uziladi, klient qaytadi, osilmaydi»), faqat arzonroq. Sabab test docstringida yozilgan.

### Rejadan ataylab chetlangan bandlar

**E. TDD RED/GREEN commitlari ajratilmadi.**

Rejaning uchala taski `tdd="true"` bilan belgilangan, `.planning/config.json` da esa `workflow.tdd_mode: false`. Fazaning oldingi rejalari (03-02, 03-04) ham har task uchun bitta `feat` commit qilgan. Bu reja o'sha konventsiyaga ergashdi. **RED dalili yo'qolmadi:** to'rtala sabotaj testlarning kodsiz qizarishini **o'lchov bilan** ko'rsatadi va har birida «nima yashil qoldi» alohida yozilgan.

**F. `adminAccesses` da RTSP yozuvi yo'qligi sim bilan emas, sof funksiya bilan o'lchandi.**

Sim `adminAccesses` da RTSP yozuvini **har doim** beradi va uni olib tashlash uchun uchinchi control-plane maydoni kerak bo'lardi. O'lchanadigan narsa — `resolve_rtsp_port()` sof funksiyasi, va u to'g'ridan-to'g'ri chaqiriladi (`test_missing_rtsp_entry_falls_back_to_554_and_is_flagged`). Sabab test docstringida ochiq yozilgan.

---

**Total deviations:** 4 auto-fixed (1 × Rule 1, 1 × Rule 3, 2 × Rule 2) + 4 ta rejadagi ziddiyat + 2 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. Rule 1 tuzatishi **ishlab chiqarishni bloklaydigan** xatoni yopdi; ikkala Rule 2 tuzatishi rejaning O'Z `<behavior>` bandlarini bajarilishi mumkin holga keltirdi.

## Issues Encountered

1. **Sim konteyneri `--reload` bilan ishlamaydi.** `state.py`/`isapi.py` o'zgargandan keyin `docker compose up -d --wait` konteynerni **qayta ko'tarmaydi** (u allaqachon sog'lom) va beshta test eski kod ustida qizardi (`KeyError: 'endpoint_hits'`). `docker compose restart nvr-sim` majburiy. **03-06/03-11 uchun amaliy qayd.**
2. **`AsyncRetrying.__call__` tanlandi**, `async for attempt in ...` naqshi emas: ikkinchisi qaytish qiymatini `Optional` qilib qoldirardi va mypy uni `assert` bilan torroq qilishni talab qilardi — ya'ni tip xavfsizligi ishlab chiqarish kodidagi `assert` ga bog'lanib qolardi.
3. **`ruff` ning `SIM300` (Yoda condition)** ikki assertni qayta yozishga majbur qildi; natijada `ERROR_DETAIL_KEYS` kutilmasi testda **alohida konstantaga** chiqdi va bu aslida yaxshiroq — endi u spetsifikatsiyadan ko'chirilgan mustaqil nusxa, moduldan import qilingan «o'ziga teng» tekshiruv emas.
4. **`verify=False` uchun `# noqa: S501` kerak bo'ldi.** Bu majburiy izohga aylandi va u yerda sabab to'liq yozildi: tekshiruv o'chirilmaydi, **ishonch manbai ko'chiriladi** (WireGuard tunneli). A.3 aynan shuni aytadi va shu sababdan o'z-o'zini imzolagan sertifikat `nvr_tls_untrusted` ni **ishga tushirmaydi**.

## Known Stubs

Yo'q. To'rtala modul ham to'liq ishlaydi.

Ikkita **ochiq belgilangan soddalashtirish** bor va ikkalasi ham kodda sababi bilan yozilgan:

| Joy | Soddalashtirish | Nega bu fazada yetarli |
|---|---|---|
| `_has_substream()` | `nvr_isapi_unavailable` «sub-oqim yo'q» deb o'qiladi | Bu nuqtaga yetish uchun `deviceInfo` va `adminAccesses` **muvaffaqiyatli** o'tgan, ya'ni ISAPI ishlayapti va `404` kanalga tegishli. Qolgan barcha kodlar **yuqoriga ko'tariladi** |
| `_normalise_channel_id()` | 100+ kanalli NVR'da `101` ikki ma'noli | Hikvision NVR'lari 128 kanalgacha chiqadi, ya'ni nazariy jihatdan mumkin; Karmanada 25 kanal kutilmoqda. Noaniqlik docstringda **ochiq** |

## Threat Flags

Yangi ishonch chegarasi ochilmadi — **chiquvchi HTTP** yuzasi rejaning `<threat_model>` ida allaqachon modellashtirilgan va to'qqizala band bajarildi:

| Threat | Holat |
|---|---|
| T-03-29 (`401` da retry → o'z-o'ziga DoS) | ✅ Predikat faqat tarmoq sinfini qamraydi; **sabotaj 0 → 5 urinishni ko'rsatdi** |
| T-03-30 (XML bomba / cheksiz javob) | ✅ `defusedxml` + `MAX_RESPONSE_BYTES` (2 MiB) + `timeout=None` **AST bilan** taqiqlangan |
| T-03-31 (sekin NVR job'ni bloklashi) | ✅ `httpx.Timeout(10.0, connect=5.0)`; `delay_ms=15000` bilan o'lchandi |
| T-03-32 (xom javobning rekvizit bilan chiqishi) | ✅ Allowlist **konstruktorda**; `raw` kesiladi; **chegarasi** ham test bilan hujjatlashtirilgan |
| T-03-33 (Hikvision bo'lmagan qurilma) | ✅ `assert_supported_device` + `detail.model`; **Rule 1 tuzatishidan keyin ham** yashil |
| T-03-34 (jimgina bo'sh natija) | ✅ Kutilgan ildiz topilmasa `NvrError`; **sabotaj S1** bu darvozaning Pitfall 2 ni qamramasligini ham ochdi |
| T-03-35 (parolning jurnalga tushishi) | ✅ Jurnal kontekstida faqat `username` va `base_url`; parol **umuman uzatilmaydi** |
| T-03-36 (Basic ga doimiy tushish) | ✅ Basic **bir marta**, faqat qurilma Digest taklif qilmaganda; natija — **tavsiya**, avtomatik tushish emas |
| T-03-SC (paket o'rnatish) | ✅ `pyproject.toml` diffi **bo'sh** |

⚠ **03-06 uchun bitta qayd (yangi flag emas, mavjudning davomi):** 03-04 ning `threat_flag: audit-volume` bandi endi **o'lchandi** — har kashfiyot 6 kamera uchun 6 ta `audit_log` qatori yozadi (`test_swapped_camera_updates_the_source_and_leaves_an_audit_row` da ko'rinadi). Ustun bilan cheklangan trigger (`UPDATE OF name, status, source_ip, …`) shu sababdan 03-06/03-07 da qaralishi kerak.

## Next Phase Readiness

**03-06 (job) uchun TAYYOR — bu rejaning asosiy iste'molchisi:**
- `run_discovery(repo, client, *, nvr_id, run_started_at, on_channels_found=None, probe_substreams=True)` — `taskiq` **import qilinmagan**, qobiq ~10 qator.
- Oqim: `create_run` → `run_discovery` → `finish_run(counts, ...)`. `NvrError` **yuqoriga ko'tariladi**; uni `error_code`/`error_detail` ga aylantirish job qatlamining ishi.
- `on_channels_found` callback'i `nvr_discovery_runs.channels_found` ga **oraliq** `UPDATE` yozishi kerak (UI-SPEC §5.2 S2a → S2b).
- `DiscoveryOutcome.channel_issues` — `channel_offline` sabablari; ular **xato emas**, skan `succeeded` bo'lib qoladi.
- ⚠ `compose.yaml` da `worker` konteyneriga `NVR_CREDENTIAL_KEY` **majburiy** (03-04 ning ochiq bandi).

**03-07 (API) uchun tayyor:**
- `IsapiClient.probe() -> ProbeResult` — `test-connection` endpointining butun mazmuni; xato **ko'tarmaydi**, `ok=False` + `error_code` qaytaradi.
- `ProbeResult.channels_preview` va `clock_drift_seconds` — UI-SPEC §4.5 **majburiy** maydonlari, ikkalasi ham to'ldirilgan.
- `AUTH_LOCKING_CODES` — javobda `auth_locked` bayrog'ini hosil qilish uchun.
- ⚠ `source_ip` ni JSON'ga berishdan oldin normalizatsiya (03-04 ning `threat_flag: value-format`).

**03-08 (frontend matni) uchun:**
- `NVR_ERROR_CODES` — `cameras.errorCause.*` kalitlarining **yagona** manbai; o'n ikkitasi ham uch tilda kerak.
- ⚠ `nvr_stream_limit` — **yagona** hedged kod (G-3 darvozasi). Hedge so'zi backendda **umuman yo'q** va buni `test_backend_never_writes_the_hedge_word` qulflaydi.
- `ERROR_DETAIL_KEYS` — UI render qiladigan sakkiz kalit.

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**
1. `npm run gate` **742 s** — 03-01 ning 618 s chegarasi ikkinchi rejada ketma-ket buzildi. Chegara qayta o'lchansin yoki `gate` bo'linsin.
2. `npm run test:sim:slow` fazani yopishdan oldin **bir marta** bajarilsin — u standart zanjirda ishlamaydi va aynan u ishlab chiqarishni bloklaydigan xatoni topdi.
3. Sim konteyneri kod o'zgargandan keyin **`restart`** talab qiladi (`--reload` yo'q).

## Self-Check: PASSED

- **Fayllar:** 11/11 mavjud (9 yangi + 2 o'zgargan)
- **Commitlar:** 3/3 mavjud (`5ab3531`, `18914ef`, `69d6a2f`)
- **`must_haves.artifacts` `contains`:** 4/4 — `NVR_ERROR_CODES` (6×), `rpartition` (2×), `DigestAuth` (2×), `channels_found` (13×)
- **`min_lines`:** `discovery.py` — 120 talab, **287** mavjud
- **`must_haves.key_links`:** 3/3 — `parsedate_to_datetime` (`client.py`), `upsert_cameras` (`discovery.py`, 4×), `sim_mode` (`test_nvr_errors.py`, 9×)
- **12/12 kod qamrovi:** mexanik tekshiruv **bo'sh** ro'yxat qaytardi
- **Ish daraxti:** to'rtala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
