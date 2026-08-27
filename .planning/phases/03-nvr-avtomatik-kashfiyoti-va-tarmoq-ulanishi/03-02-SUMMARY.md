---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 02
subsystem: testing
tags: [hikvision, isapi, digest-auth, rfc7616, simulator, go2rtc, rtsp, docker-compose, fixtures, fastapi]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`services/core-api/Dockerfile` ning `dev` target'i (sim shuni qayta ishlatadi, yangi Dockerfile yozilmadi); `compose.yaml` ning profil naqshi va xost-portiga-publish taqig'i (T-01-04)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "03-01: `sim`/`slow`/`hardware` pytest markerlari `--strict-markers` ostida; `httpx==0.28.1` prod bog'liqligi; `defusedxml==0.7.1` (allaqachon mavjud edi)"
provides:
  - "`services/nvr-sim/` — simulyatsiya qilingan Hikvision NVR; `--profile sim` ortida, prodga chiqmaydi"
  - "RFC 7616 Digest'ning SERVER tomoni — `response` HAQIQATAN hisoblanadi (`httpx.DigestAuth` bilan haqiqiy handshake)"
  - "Sozlanadigan `Date` sarlavhasi — `nvr_clock_drift` yo'lining yagona sinov vositasi, `401` javobida ham amal qiladi"
  - "`/__sim__/` control-plane: `state` / `reset` / `attempts`; B.8 ning o'n oltita xato rejimi"
  - "D-05 ning IKKALA `stream_limit` shakli: `reject` (Hikvision xato XML'i) va `silent` (javobsiz uzilish)"
  - "7 ta fixture — `hikvision_next` ning YOZIB OLINGAN dumplaridan, manba/commit/blob-sha izohi bilan"
  - "`ops/go2rtc/go2rtc.sim.yaml` — 6 sintetik RTSP oqimi (`sim_cam_01..06`), kadrda kanal raqami va soat"
  - "`npm run test:sim` / `test:sim:slow` / `sim:up` / `sim:down`; `gate` zanjiriga `test:sim` qo'shildi"
  - "`tests/unit/test_no_sim_branching.py` — sim ilova kodiga sizmasligining darvozasi (SC#7 ning strukturaviy asosi)"
  - "`tests/unit/test_sim_fixtures.py` — fixture kelib chiqishining darvozasi (Pitfall 4)"
  - "`tests/fixtures/nvr_sim.py` — `sim_url` (CI'da `fail`, dev'da `skip`), `sim`, `sim_mode`, `sim_patch`, `sim_reset`, `sim_attempts`"
affects: [03-04-fernet, 03-05-isapi-klient, 03-06-job, 03-07-live-view, 03-09-frontend, 03-10-wireguard, 03-11-yakuniy-darvoza]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture KELIB CHIQISHI mexanik tekshiriladi: har fayl uchun dumpdagi namespace QULFLANADI — korpus darajasidagi tekshiruv bitta faylning 'to'g'rilanishini' ko'rmasligi O'LCHANDI"
    - "Simulyatorning ISHONCHLILIGI sabotaj bilan o'lchanadi: `verify()` -> `True` qilinganda AYNAN bitta test qizaradi; qolgan sakkiztasi yashil qoladi va bu darvozaning yagonaligini isbotlaydi"
    - "Noaniqlik BITTA shaklga siqilmaydi: A.5 LOW ishonch bilan belgilangan sessiya limiti IKKALA shaklda modellashtiriladi va IKKALASI ham sinaladi"
    - "`Date` sarlavhasi sof ASGI middleware'da qo'yiladi (`BaseHTTPMiddleware` EMAS) — u javob TANASIGA aralashmaydi, `silent` rejimi esa aynan tana darajasida ishlaydi"
    - "Control-plane qurilma yuzasidan AJRATILGAN nomlar fazasida (`/__sim__/` vs `/ISAPI/`) va healthcheck nishoni AYNAN control-plane — aks holda `mode=slow` testi konteynerni `unhealthy` qilardi"
    - "Sanagichlar (`stream_claims`, `auth_attempts`) tashqaridan O'RNATILMAYDI: test o'zi o'lchayotgan qiymatni o'zi yozib qo'ya olmaydi; nollashning yagona yo'li — `reset`"
    - "Noma'lum rejim/model/maydon `400` beradi, `500` emas: 'rejimni o'rnatdim deb o'ylab, aslida hech nima o'zgarmagan' holati testda KO'RINADI"

key-files:
  created:
    - services/nvr-sim/sim/digest.py
    - services/nvr-sim/sim/state.py
    - services/nvr-sim/sim/isapi.py
    - services/nvr-sim/sim/main.py
    - services/nvr-sim/fixtures/README.md
    - ops/go2rtc/go2rtc.sim.yaml
    - tests/fixtures/nvr_sim.py
    - tests/unit/test_sim_fixtures.py
    - tests/unit/test_no_sim_branching.py
    - tests/integration/test_nvr_sim.py
  modified:
    - compose.yaml
    - package.json
    - tests/conftest.py

key-decisions:
  - "D-04 BAJARILDI VA KENGAYTIRILDI: fixture'lar `hikvision_next` dumplaridan tarmoq orqali olindi (tuzilma taxmindan QURILMADI). Rejadagi 5 ta o'rniga 7 ta — real IP-kamera dumpi (`DS-2CD2346G2-ISU`) qo'shildi, chunki Task 2 ning `<behavior>` bandi `deviceType=IPCamera` yo'lini talab qiladi va uni sintetik XML bilan qoplash aynan Pitfall 4 bo'lardi"
  - "TOPILMA: `DS-7732NI-M4` `http://www.isapi.org/ver20/XMLSchema` namespace'ini ishlatadi, `hikvision.com` EMAS. Reja va tadqiqot faqat `hikvision.com` ni kutgan edi. Fixture TAHRIRLANMADI — qabul mezonining NIYATI bajarildi va ikkala namespace ham qulflandi"
  - "TOPILMA: `DS-7732NI-M4` dumpida `InputProxyChannelList size=\"14\"`, elementlar esa 18 ta. `@size` fixture'da VERBATIM qoldirildi va sim uni emitilgan kanallar soniga MOSLAMAYDI — kashfiyot kodi elementlarni sanashi kerak"
  - "TOPILMA: ikkala NVR dumpida ham `/ISAPI/System/Video/inputs/channels` uchun `403` yozib olingan. Sim NVR rejimida aynan 403 qaytaradi — A.1 ning «InputProxy avtoritetli» xulosasi endi O'LCHOV bilan qo'llab-quvvatlangan"
  - "`--no-date-header` uvicorn bayrog'i QO'SHILDI (rejada yo'q edi): usiz uvicorn o'z `Date` ini ASGI javobidan OLDIN qo'yadi, javobda ikkita `Date` bo'ladi va `parsedate_to_datetime` yiqiladi — ya'ni butun soat-farqi yo'li JIMGINA ishlamay qolardi"
  - "`silent` uzilish ASGI'dan erishiladigan eng yaqin analog bilan modellashtirildi: `Content-Length` e'lon qilinadi, tana yuborilmaydi -> `h11` protokol xatosi -> uvicorn ulanishni yopadi. O'lchandi: klient `httpx.RemoteProtocolError` oladi, status kodi ham, xato XML'i ham YO'Q — D-05 talab qilgan xususiyat aynan shu"
  - "`auth_attempts` FAQAT `Authorization` sarlavhasi bo'lgan so'rovlarni sanaydi. Sabab: Hikvision'ning qulflash sanagichi ham rekvizit urinishlarini sanaydi, ya'ni sanoq D-03 uchun mos birlikda bo'ladi. O'lchandi: bitta kashfiyot chaqiruvi = AYNAN 1"
  - "`defusedxml` ishlatildi, `xml.etree` emas — loyiha standarti (`app/services/xlsx_reader.py`). Yangi paket QO'SHILMADI: `defusedxml==0.7.1` allaqachon core-api ning ishlab chiqarish bog'liqligi"

patterns-established:
  - "Pattern: fixture provenance IKKI QATLAMDA qulflanadi — fayldagi izoh (odam uchun) va testdagi kutilgan qiymat jadvali (mashina uchun); ikkinchisisiz birinchisi shunchaki matn"
  - "Pattern: darvozaning O'ZI o'lchanadi — `test_no_sim_branching.py` loyihasi bo'yicha har doim yashil, shuning uchun skaner mantig'i ATAYIN EKILGAN satr ustida alohida test bilan tekshiriladi"
  - "Pattern: `skip` ning xavfi muhitga qarab ochiladi — CI'da `fail`, dev'da `skip`; va tekshiruv o'zgaruvchining MAVJUDLIGIGA emas, manzilning YETIB BORILISHIGA qaraydi"
  - "Pattern: sim rejimi `unreachable` `POST /__sim__/state` bilan o'rnatilmaydi va `400` beradi — 'hech nima qilmaydigan rejim' bo'lib qolgandan ko'ra ochiq rad etish yaxshi"

requirements-completed: []

# Metrics
duration: 105min
completed: 2026-08-03
---

# Phase 3 Plan 02: Hikvision NVR simulyatori (CAM-09) Summary

**`--profile sim` ostida ishlaydigan Hikvision NVR simulyatori: RFC 7616 Digest'ning haqiqiy server tomoni, siljitiladigan `Date` sarlavhasi, o'n oltita xato rejimi va `hikvision_next` ning yozib olingan dumplaridan ajratilgan yetti fixture — fazaning qolgan to'qqizta rejasi endi real uskunasiz o'lchanadi.**

## Performance

- **Duration:** ~105 min
- **Started:** 2026-08-03T00:45Z
- **Completed:** 2026-08-03T02:30Z
- **Tasks:** 3/3
- **Files modified:** 21 (18 yangi, 3 o'zgargan) — +3071 qator

## Accomplishments

- **CAM-09 ning enabling deliverable'i yopildi.** Tayyor Hikvision NVR emulyatori mavjud emas (ikki mustaqil qidiruv bilan tasdiqlangan) — u qurildi va **42 ta xulq nuqtasi haqiqiy TCP orqali o'lchandi**.
- **Digest HAQIQIY:** `httpx.DigestAuth` sim bilan to'liq RFC 7616 handshake bajaradi; noto'g'ri parol hech qachon o'tmaydi. Sabotaj bilan isbotlandi.
- **Fixture'lar real dumpdan olindi va uchta kutilmagan fakt topildi** (namespace ikki xil, `@size` yolg'on bo'lishi mumkin, NVR'da `Video/inputs/channels` = 403). Uchalasi ham qo'lda yozilgan XML'da hech qachon paydo bo'lmasdi.
- **D-05 ning ikkala shakli ham ishlaydi va sinaladi** — `reject` (503 + `Maximum number of streams`) va `silent` (`RemoteProtocolError`, status kodi yo'q).
- **go2rtc RTSP oqimi uchidan-uchiga tekshirildi:** `sim_cam_03` dan olingan kadrda kanal nomi va Toshkent vaqti ko'rinadi.
- **Bazaviy darvoza qizarmadi:** 1021 → **1069** backend (+48), **322** tenancy (o'zgarmadi), **74** vitest va **60** node:test (ikkalasi ham o'zgarmadi), `npm run gate` → **exit 0 / 534 s**, `services/core-api/pyproject.toml` **tegilmadi** (T-03-SC: yangi paket yo'q).

## Task Commits

1. **Task 1: Sim yadrosi (Digest / `Date` / control-plane)** — `1b7781d` (feat)
2. **Task 2: Fixture kelib chiqishi darvozasi** — `427d8a4` (test)
3. **Task 3: Compose profili, go2rtc, test yo'naltirilishi, sizmaslik darvozasi** — `b824700` (feat)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `services/nvr-sim/sim/digest.py` | RFC 7616 **server** tomoni: `build_challenge` / `parse_authorization` / `verify` / `verify_basic`. `response` haqiqatan hisoblanadi; nonce `secrets.token_hex` |
| `services/nvr-sim/sim/state.py` | `SimState` + B.8 ning o'n oltita rejimi; qisman yangilash, sanagichlar faqat o'qishga, noma'lum qiymat `400` |
| `services/nvr-sim/sim/isapi.py` | Fixture'larni `SimState` bo'yicha parametrlaydi; B.7 ning o'n ikki endpointi; `stream_limit` ning ikkala shakli |
| `services/nvr-sim/sim/main.py` | FastAPI ilovasi: sof ASGI `Date` middleware'i, Digest darvozasi, `/__sim__/` control-plane |
| `services/nvr-sim/fixtures/*.xml` (7) | Yozib olingan dumplardan verbatim; har birida manba/commit/blob-sha izohi |
| `services/nvr-sim/fixtures/README.md` | Provenance jadvali, litsenziya-atribut bandi, dumpda **bo'lmagan** javoblarning ochiq ro'yxati |
| `ops/go2rtc/go2rtc.sim.yaml` | 6 sintetik RTSP oqimi; API `127.0.0.1` ga bog'langan (D-11) |
| `compose.yaml` | `nvr-sim` + `go2rtc-sim` `profiles: ["sim"]`; xost portiga publish yo'q; `tests` ga `NVR_SIM_BASE_URL` |
| `package.json` | `sim:up` / `sim:down` / `test:sim` / `test:sim:slow`; `gate` ga `test:sim` |
| `tests/fixtures/nvr_sim.py` | `sim_url` (zondlaydi, CI'da `fail`), `sim`, `sim_mode`, `sim_patch`, `sim_reset`, `sim_attempts` |
| `tests/unit/test_sim_fixtures.py` | Fixture kelib chiqishi darvozasi — 34 test |
| `tests/unit/test_no_sim_branching.py` | Sim ilova kodiga sizmasligi — 5 test |
| `tests/integration/test_nvr_sim.py` | 9 test, haqiqiy TCP orqali |
| `tests/conftest.py` | `pytest_plugins = ["fixtures.nvr_sim"]` + ikki qatlamning farqi izohi |

## O'lchangan dalillar

### Fixture'lar haqiqatan real dumpdan (D-04)

Tarmoq orqali olindi (`raw.githubusercontent.com`, HTTP 200), `xmltodict` shaklidagi JSON'dan XML'ga **tahrirsiz** o'girildi:

| Qurilma | Upstream commit | Blob sha1 | Nima olindi |
|---|---|---|---|
| `DS-7616NI-K2` | `a0e59ea7426c` (2024-10-14) | `a145a70cf863…` | `deviceInfo`, `InputProxy/channels`, `adminAccesses` |
| `DS-7732NI-M4` | `c5f6cb85f6e8` (2024-12-04) | `92c315bd8dc1…` | `deviceInfo`, `InputProxy/channels` |
| `DS-2CD2346G2-ISU` | `c83426ec2e19` (2024-11-24) | `89be73551de1…` | `deviceInfo`, `Video/inputs/channels` |

`DS-7616NI-K2` `deviceInfo` javobi `03-RESEARCH.md` A.1 dagi verbatim keltirilgan XML bilan **maydonma-maydon mos keldi** (bizniki ikkita qo'shimcha maydon bilan to'liqroq: `encoderReleasedDate`, `telecontrolID`).

### Uchta kutilmagan topilma — qo'lda yozilgan fixture ularni bermasdi

| # | Topilma | Oqibati |
|---|---|---|
| 1 | `DS-7732NI-M4` **`isapi.org/ver20/XMLSchema`** namespace'ida (`@version="2.0"`), `hikvision.com` da emas | Parser namespace-agnostik bo'lishi SHART (Pitfall 2) endi fixture bilan qo'llab-quvvatlangan |
| 2 | `InputProxyChannelList size="14"`, elementlar esa **18 ta** | `@size` ga ishonib bo'lmaydi — elementlarni sanash kerak. Sim `size` ni verbatim qoldiradi va emitilgan songa moslamaydi |
| 3 | Ikkala NVR dumpida ham `/ISAPI/System/Video/inputs/channels` -> **`403`** | A.1 ning «`InputProxy` avtoritetli» xulosasi endi taxmin emas, o'lchov |

### Sim xulqi — 42 nuqta haqiqiy TCP orqali

Ijro davomida efemer zond bilan o'lchandi (zond commit qilinmadi; doimiy darvoza — `tests/integration/test_nvr_sim.py`):

| Guruh | Natija |
|---|---|
| Digest challenge (`qop="auth"`, tasodifiy nonce) + `httpx.DigestAuth` handshake | ✅ `401` -> `200` |
| `Date` sarlavhasi AYNAN BITTA (uvicorn dublikati yo'q) | ✅ |
| `clock_drift=420` — `401` javobida o'lchangan siljish | ✅ **419 s** |
| Noto'g'ri parol -> `401`, `attempts` **+1** (aynan bitta) | ✅ |
| `account_locked` / `no_permission` / `isapi_404` / `digest_stale` / `not_hikvision` | ✅ |
| `basic_only`: Basic qabul, Digest rad | ✅ |
| `stream_limit=4, reject`: `[200,200,200,200,503]` + `Maximum number of streams` | ✅ |
| `stream_limit=4, silent`: `RemoteProtocolError: peer closed connection without sending complete message body` | ✅ |
| `reset` `stream_claims` ni `4 -> 0` qildi | ✅ |
| 25 kanal ish paytida (`channel_count=25`, `model=DS-7732NI-M4`) — yaroqli XML | ✅ |
| IP-kamera yo'li: `InputProxy` -> 404, `Video/inputs/channels` -> 1 kanal, `deviceType=IPCamera` | ✅ |
| `port_moved`: RTSP `10554`, HTTP `80` tegilmagan | ✅ |
| `channel_offline=[3]`, `channel_removed=[5]`, `camera_swapped` | ✅ |
| `slow (delay_ms=700)`: ISAPI **716 ms**, control-plane **14 ms** | ✅ |
| `mode=unreachable` / sanagichni yozish / noma'lum maydon -> `400` | ✅ |

### go2rtc RTSP oqimi (uchidan-uchiga)

`go2rtc-sim` konteyneri ichidan `rtsp://127.0.0.1:8554/sim_cam_03` dan bitta kadr olindi — **64 018 baytli JPEG**, kadrda `sim_cam_03` yozuvi va `2026-08-03 06:07:43` (Asia/Tashkent) soati ko'rinadi. Ya'ni `exec:` + `{output}` mexanikasi, `-re` bayrog'i va `drawtext` filtri ishlaydi.

### T-03-10 — CI'da `skip` mumkin emas

| Stsenariy | Natija |
|---|---|
| `NVR_SIM_BASE_URL` yetib bo'lmaydi, `CI` **o'rnatilmagan** | `sssssssss` (9 skip), exit **0** |
| `NVR_SIM_BASE_URL` yetib bo'lmaydi, **`CI=true`** | 9 ERROR, xabar sabab va tuzatish yo'lini aytadi, pytest exit **1** |

### T-03-07 / T-03-12 — sim prodga chiqmaydi

| Buyruq | Natija |
|---|---|
| `docker compose config --services` | `cache`, `db`, `core-api` — `nvr-sim` **YO'Q** |
| `docker compose --profile sim config --services` | `nvr-sim` va `go2rtc-sim` **BOR** |
| `nvr-sim.ports` / `go2rtc-sim.ports` | ikkalasi ham `None` |
| `grep -rn "__sim__" services/core-api/app/ \| wc -l` | **0** |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `services/core-api/app/settings.py` ga `SIM_MODE = "ok"` qo'shildi | `test_no_sim_branching.py::test_application_code_has_no_simulator_branching[SIM_]`; xabarda `services/core-api/app/settings.py:102` | `test_sim_fixtures.py` (34), `tests/integration -m sim` (9) | Sizib ketish darvozasi kod daraxtini o'lchaydi; sim'ning O'Z testlari uni ko'rmaydi va ko'rmasligi ham kerak |
| **S2** | `sim/digest.py::verify` -> `return True` (konteyner restart bilan) | `test_nvr_sim.py::test_wrong_password_never_authenticates` (`401` o'rniga `200`) | **Qolgan 8 sim testi**, `test_sim_fixtures.py` (34), `test_no_sim_branching.py` (5) | ⚠ **Eng muhim natija:** Digest stub bo'lganda ham `test_digest_handshake_succeeds` YASHIL qoladi (to'g'ri parol baribir ishlaydi). Ya'ni auth hikoyasining bo'sh bo'lib qolmasligini ushlab turuvchi YAGONA test — noto'g'ri parol testi (T-03-09) |
| **S-A** | `DS-7732NI-M4-deviceInfo.xml` da `isapi.org` -> `hikvision.com` | `test_sim_fixtures.py::test_fixture_root_is_in_an_isapi_namespace[DS-7732NI-M4-deviceInfo.xml]` | qolgan hammasi | Fixture tahriri FAYL darajasida ko'rinadi |
| **S-B** | `DS-7616NI-K2-deviceInfo.xml` dan manba izohi olib tashlandi | `test_sim_fixtures.py::test_fixture_declares_its_source[...]` | qolgan hammasi | Kelib chiqishi hujjatlashtirilmagan fixture qabul qilinmaydi |

Hamma sabotajlar commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har tiklashdan keyin ish daraxti toza va darvozalar yashil.

⚠ **S-A birinchi urinishda YASHIL qoldi** va bu darvozani kuchaytirishga olib keldi: dastlabki loyiha namespace'larni faqat **korpus darajasida** tekshirardi («ikkalasi ham bor»), ya'ni bitta faylni «to'g'rilash» ikkinchi faylning qiymati hisobiga jimgina o'tib ketardi. Endi har fayl uchun dumpdagi namespace `EXPECTED_NAMESPACE` jadvalida qulflangan.

## Decisions Made

1. **Fixture'lar tarmoq orqali olindi, taxmindan qurilmadi.** Reja «tarmoq orqali olib bo'lmasa A.1 spetsifikatsiyasidan qur va buni ochiq yoz» degan zaxira yo'lni bergan edi — u **kerak bo'lmadi**. Barcha uchta dump HTTP 200 bilan olindi.
2. **Rejadagi 5 ta o'rniga 7 ta fixture.** Task 2 ning `<behavior>` bandi `deviceType=IPCamera` yo'lini talab qiladi; uni sintetik XML bilan qoplash aynan Pitfall 4 bo'lardi. Yuqori oqimda real IP-kamera dumpi bor edi — u olindi. Qabul mezoni `>= 5` bo'lgani uchun bu chegaradan chiqish emas.
3. **`state.model` — fixture TANLAGICHI, javobdagi `<model>` emas.** Javobdagi qiymat fixture'dan verbatim keladi (`DS-2CD2346G2-ISU/SL`), tanlagich esa fayl nomiga mos (`DS-2CD2346G2-ISU`). Ikkalasini ajratmaslik `/` belgisi tufayli 500 berardi.
4. **`stream_limit` standarti — 128, «0 = cheksiz» emas.** 128 — Hikvision hujjatlashtirgan «maximum number of streams» (A.5). Sehrli qiymat o'rniga realistik son «chegara yo'q» degan yolg'on taxminni kodga kiritmaydi. Test D-09 bo'yicha **4** bilan ishlaydi.
5. **`unreachable` rejimi `POST /__sim__/state` bilan o'rnatilmaydi** — u `400` beradi va konteynerni to'xtatish kerakligini aytadi. Aks holda u «qabul qilinadigan, lekin hech nima qilmaydigan» rejim bo'lib qolardi.
6. **go2rtc API `127.0.0.1` ga bog'landi** (rejada talab qilinmagan). T-03-08 «port publish qilinmaydi» deydi; `listen: "127.0.0.1:1984"` esa RCE yuzasini **compose tarmog'idan ham** yopadi. Sim go2rtc'ining API'si hech kimga kerak emas.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Bloklovchi] `uvicorn --no-date-header` qo'shildi**
- **Found during:** Task 1
- **Issue:** Reja `nvr-sim` uchun `command: ["uvicorn","sim.main:app","--host","0.0.0.0","--port","8080"]` ni belgilaydi. Ammo uvicorn o'z `Date` sarlavhasini ASGI javobining sarlavhalaridan **oldin** qo'yadi (`default_headers + message headers`). Natijada javobda ikkita `Date` bo'lardi, `httpx` ularni vergul bilan qo'shib berardi va `parsedate_to_datetime` yiqilardi — ya'ni A.3 ning butun soat-farqi yo'li (SC#3 ning eng qimmatli qismi) **jimgina** ishlamay qolardi.
- **Fix:** `--no-date-header` bayrog'i qo'shildi (uvicorn 0.51.0 da mavjudligi tekshirildi) va sababi `compose.yaml` da izohlandi.
- **Verification:** `Date` sarlavhalari soni o'lchandi — **1**; `clock_drift=420` da o'lchangan siljish **419 s**.
- **Committed in:** `b824700`

**2. [Rule 2 — Yetishmayotgan kritik funksiya] IP-kamera fixture'lari va `deviceType` bo'yicha tarmoqlanish**
- **Found during:** Task 2
- **Issue:** Task 2 ning `<behavior>` bandi `deviceType=IPCamera` bo'lganda `InputProxy` -> 404 va `Video/inputs/channels` -> 1 kanal bo'lishini talab qiladi, lekin `files_modified` da faqat NVR fixture'lari sanalgan. Sintetik XML yozish Pitfall 4 ning aynan o'zi bo'lardi.
- **Fix:** `DS-2CD2346G2-ISU` (real IP-kamera) dumpidan ikkita fixture olindi; `isapi.py` `state.model` ga qarab tarmoqlanadi.
- **Verification:** `IPCamera -> InputProxy 404`, `-> 1 VideoInputChannel`, `deviceType=IPCamera` — uchalasi ham o'lchandi.
- **Committed in:** `1b7781d`

**3. [Rule 2 — Yetishmayotgan kritik funksiya] Fixture namespace'i HAR FAYL uchun qulflandi**
- **Found during:** Task 2 (sabotaj S-A)
- **Issue:** Darvozaning birinchi loyihasi namespace'larni faqat korpus darajasida tekshirardi. `DS-7732NI-M4-deviceInfo.xml` ni `hikvision.com` ga «to'g'rilash» darvozani **yashil qoldirdi** (o'lchandi) — chunki `isapi.org` boshqa faylda saqlanib qolgan edi.
- **Fix:** `EXPECTED_NAMESPACE` jadvali — har fayl uchun dumpdagi qiymat; yangi fixture jadvalga qo'shilmasa test aytadi.
- **Verification:** S-A qayta bajarildi va endi aniq fayl nomi bilan qizaradi.
- **Committed in:** `427d8a4`

**4. [Rule 2 — Yetishmayotgan kritik funksiya] `sim_url` manzilni ZONDLAYDI**
- **Found during:** Task 3
- **Issue:** Reja fixture'ni «`NVR_SIM_BASE_URL` bo'lmasa skip/fail» deb belgilaydi. Ammo compose bu o'zgaruvchini `tests` konteyneriga **har doim** beradi, ya'ni «o'zgaruvchi yo'q» sharti amalda hech qachon bajarilmasdi va T-03-10 mitigatsiyasi o'z kuchini yo'qotardi. Haqiqiy xavf — o'zgaruvchi bor, konteyner esa ko'tarilmagan.
- **Fix:** Fixture `GET /__sim__/state` bilan zondlaydi va bir xil skip/fail qoidasini yetib borilmaslik holatiga ham qo'llaydi.
- **Verification:** Ikkala stsenariy ham o'lchandi (yuqoridagi T-03-10 jadvali).
- **Committed in:** `b824700`

**5. [Rule 2 — Yetishmayotgan kritik funksiya] `stream_limit` uchun integratsiya testlari**
- **Found during:** Task 3
- **Issue:** Reja Task 3 uchun aynan uchta test nomlagan (`reachable`, `handshake`, `wrong_password`). D-05 ning ikkala shakli, `reset` ning sanagichni nollashi va RTSP portining kashf etilishi esa **hech qanday doimiy test bilan qoplanmagan** edi — ya'ni ular faqat ijro paytidagi zondda o'lchanib, keyin regressiyaga ochiq qolardi. Reja-tekshiruvchining dastlabki blokeri ham aynan «e'lon qilingan, lekin ishlatilmaydigan `stream_limit`» edi.
- **Fix:** Yana olti test qo'shildi: drift, RTSP porti, `stream_limit` ning ikkala shakli, `reset` sanagichlari, `channel_offline`/`channel_removed`.
- **Verification:** 9/9 yashil; S2 sabotaji aynan bittasini qizartiradi.
- **Committed in:** `b824700`

**6. [Rule 1 — Xato] `state.model` fixture nomi bilan mos kelmasdi**
- **Found during:** Task 1 (zond)
- **Issue:** `_fixture_for` model satridan `/` ni `-` ga almashtirardi, ya'ni `DS-2CD2346G2-ISU/SL` -> `DS-2CD2346G2-ISU-SL-deviceInfo.xml` — bunday fayl yo'q, natija `FileNotFoundError` va `500`.
- **Fix:** `model` fixture **tanlagichi** sifatida ajratildi (`KNOWN_MODELS`), noma'lum qiymat `400` beradi.
- **Verification:** IPCamera yo'lining uchala tekshiruvi ham yashil; noma'lum model `400` beradi.
- **Committed in:** `1b7781d`

### Rejadan ataylab chetlangan bandlar (sabab bilan)

**A. Qabul mezoni `grep -L "hikvision.com/ver20/XMLSchema" fixtures/*.xml` -> bo'sh chiqish BAJARILMADI (niyat bajarildi).**
Real `DS-7732NI-M4` dumpi `http://www.isapi.org/ver20/XMLSchema` namespace'ini ishlatadi. Mezonni **literal** bajarishning yagona yo'li — fixture'ni tahrirlash, ya'ni aynan shu reja bloklash uchun mavjud bo'lgan `simulator-confirms-itself` anti-naqshini bajarish bo'lardi. Mezonning niyati («namespace'siz fixture yo'q») bajarildi va undan kuchliroq qilindi: har fayl uchun dumpdagi namespace qulflandi, hamda ikkala namespace'ning korpusda saqlanishi alohida test bilan himoyalandi. `grep -L "ver20/XMLSchema"` esa bo'sh chiqish beradi.

**B. Task 1 va Task 2 ning fayl chegarasi commit chegarasi sifatida ishlatilmadi.**
Task 1 ning o'z qabul mezoni `python -c "... import sim.main"` ning exit 0 bo'lishini talab qiladi, `main.py` esa `isapi.py` ni import qiladi, `isapi.py` esa fixture'larni o'qiydi. Ya'ni rejadagi chegara **yaroqli commit chegarasi emas** — Task 1 ni yolg'iz commit qilish import xatosi bilan buzilgan daraxt qoldirardi. Commitlar shunday ajratildi: `1b7781d` = **ishlaydigan sim** (kod + fixture), `427d8a4` = **provenance darvozasi** (README + test), `b824700` = **wiring darvozasi**. Har uchala commit ham yaroqli holat.

**C. `tests/integration/conftest.py` TEGILMADI (topilma qayd etildi).**
O'lchandi: `_cleanup_api_created_users` (`autouse`) `sync_owner_conn` ni talab qiladi, ya'ni sim testlari Postgres testcontainer'ini ko'taradi (~3.4 s) va har testdan keyin bazaga `DELETE` yuboradi — sim testlari uchun bu **butunlay keraksiz**. Tuzatish prototipi ishladi (23.2 s -> 16.8 s), lekin `pg_container` baribir ko'tarilardi: `tests/conftest.py` dagi `_bootstrap_extensions` / `_bootstrap_roles` **sessiya darajasida `autouse`**. Ya'ni «sim darvozasi Postgres'ga bog'liq emas» da'vosini to'liq bajarish uchun tenancy test infratuzilmasining o'zagiga tegish kerak — bu bu rejaning doirasidan tashqarida va parallel ishlayotgan 03-03 bilan bir vaqtda qilinmasligi kerak. O'zgarish **qaytarildi**. **03-11 uchun band:** sim testlarini `pg_container` dan ajratish `gate` dan ~4–6 s oladi va yiqilish sababini to'g'ri quyi tizimga bog'laydi.

**D. `mode="slow"` uchun doimiy test yozilmadi.**
U ijro paytida o'lchandi (ISAPI 716 ms, control-plane 14 ms), lekin doimiy testga aylantirilmadi: 700 ms lik kutish har `gate` ga qo'shilardi va timeout xulqining o'zi 03-05 ning (`httpx` timeout siyosati) zimmasida. Mexanizm mavjud va o'lchangan; uni sinaydigan test o'sha rejada tabiiy joyini topadi.

---

**Total deviations:** 6 auto-fixed (4 × Rule 2, 1 × Rule 3, 1 × Rule 1) + 4 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. To'rtala Rule 2 tuzatishi e'lon qilingan darvozani **haqiqiy** darvozaga aylantirdi yoki rejaning O'Z `<behavior>` bandini bajarilishi mumkin holga keltirdi. Rule 3 tuzatishisiz fazaning eng qimmatli diagnostik yo'li (soat farqi) jimgina ishlamasdi.

## Issues Encountered

1. **`silent` uzilishni ASGI'dan modellash.** ASGI qatlamida soketni to'g'ridan-to'g'ri yopish mumkin emas. Yechim: `Content-Length` e'lon qilinadi, tana yuborilmaydi — `h11` protokol xatosi beradi va uvicorn ulanishni yopadi. Klient tomonda kuzatilgani **o'lchandi** va kodda hujjatlashtirildi: `httpx.RemoteProtocolError: peer closed connection without sending complete message body (received 0 bytes, expected 1024)` — status kodi ham, xato XML'i ham yo'q, ya'ni D-05 talab qilgan xususiyat aynan bajarilgan. Kodda bu «shakl, kafolat emas» deb ochiq yozilgan (A.5 ning LOW ishonchi).
2. **`Date` middleware'i sof ASGI qilindi.** `BaseHTTPMiddleware` javobni alohida task'da qayta oqimlaydi va ataylab tugatilmagan javob bilan qanday ishlashi noaniq. Sof ASGI wrapper `http.response.start` xabarini joyida tahrirlaydi va tananing taqdiriga umuman aralashmaydi.
3. **Birinchi sabotaj (S-A) darvozaning bo'shlig'ini ochdi** — batafsiloti yuqorida (Deviation 3). Bu «sabotaj natijasini ikki tomonlama yozish» qoidasining aynan qiymatini ko'rsatdi: agar men faqat «qizardimi?» deb so'raganimda va javob «yo'q» bo'lganini yozib qo'yganimda, darvoza bo'sh holicha commit bo'lardi.
4. **`ruff format`** `test_nvr_sim.py` ni bir marta qayta formatladi (uzun `async with` qatorlari) — natija `ruff format --check` bilan tasdiqlandi.

## Known Stubs

Yo'q — lekin ATAYIN SODDALASHTIRILGAN va **ochiq belgilangan** uchta joy bor (hammasi `fixtures/README.md` da jadval sifatida va kod izohlarida qayd etilgan):

| Joy | Nima soddalashtirilgan | Nega bu fazada yetarli |
|---|---|---|
| `/ISAPI/System/capabilities` | Qisqartirilgan `DeviceCap` (to'liq dump ~40 KB) | B.7 #11 fidelity darajasi **PAST**; kashfiyot undan foydalanmaydi |
| `/ISAPI/System/time` | Shakl Hikvision hujjatidan, dumpda yo'q | B.7 #10 fidelity **PAST**; `drift_seconds` bilan siljiydi, ya'ni foydali qismi ishlaydi |
| `.../picture` JPEG | Sintetik 1×1 tasvir (160 bayt) | B.7 #9 — 4-faza uchun ilgak; bu fazada faqat mavjudligi tekshiriladi. Git'ga binar fayl qo'shilmaydi |
| `InputProxy/channels/status` | Shakl A.1 spetsifikatsiyasidan (dumpda yo'q) | Ochiq belgilangan taxmin; `<online>` mantig'i to'liq ishlaydi va sinaladi |

Bularning birortasi ham fazaning maqsadini bloklamaydi va hech biri «ma'lumot ulanmagan komponent» emas.

## Threat Flags

Yo'q. Yangi ishonch chegarasi ochilmadi — aksincha, ikkitasi **yopildi**:

- **T-03-07 / T-03-12:** sim `profiles: ["sim"]` ortida va xost portiga hech narsa publish qilinmaydi (o'lchandi).
- **T-03-08:** go2rtc API `127.0.0.1:1984` ga bog'landi — RCE yuzasi (GHSA-wwww-5h25-jf98) compose tarmog'idan ham yopiq.
- **T-03-SC:** `services/core-api/pyproject.toml` **tegilmadi** — `git diff --exit-code` toza. Yangi paket qo'shilmadi; `alexxit/go2rtc:1.9.14` CLAUDE.md da qulflangan versiya.

`nvr-sim` yangi HTTP endpoint'lar ochadi, lekin ular **ishlab chiqarish yuzasi emas**: konteyner prod deploy'da umuman mavjud bo'lmaydi va buni `docker compose config --services` bilan o'lchash mumkin.

## Next Phase Readiness

**03-04 (Fernet) uchun:** sim rekvizitlari (`admin` / `Sim12345`) muhitdan keladi va bazadagi shifrlangan qiymatga almashtirish uchun **kod o'zgarishi kerak emas**.

**03-05 (ISAPI klienti) uchun TO'LIQ TAYYOR — bu rejaning asosiy iste'molchisi:**
- Har `error_code` uchun tayyor rejim bor (`bad_password`, `account_locked`, `clock_drift`, `digest_stale`, `basic_only`, `no_permission`, `isapi_404`, `not_hikvision`, `stream_limit`, `port_moved`, `channel_offline`, `channel_removed`, `channel_added`, `camera_swapped`, `slow`).
- `GET /__sim__/attempts` — D-03 ning («`401` da retry YO'Q») yagona o'lchov vositasi; hozircha o'lchangan: bitta chaqiruv = 1 urinish.
- **Parser uchun ogohlantirish:** namespace IKKI XIL (`hikvision.com` va `isapi.org`) va `@size` atributiga ISHONIB BO'LMAYDI. Ikkalasi ham fixture bilan qo'llab-quvvatlangan.
- `deviceType` bo'yicha tarmoqlanish ikkala yo'lda ham sinaladi (NVR va IPCamera).

**03-06 (job) uchun:** `mode="slow"` + `delay_ms` timeout va job byudjetini sinash uchun tayyor va o'lchangan.

**03-07 (jonli ko'rish) uchun:** `go2rtc-sim` da 6 ta ishlaydigan RTSP oqimi bor va kadr olish uchidan-uchiga tekshirilgan. ⚠ Sim go2rtc'ining API'si `127.0.0.1` ga bog'langan — jonli ko'rish PROD go2rtc'i orqali boradi, sim go2rtc esa faqat «tashqi qurilma» rolini o'ynaydi.

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**
1. `npm run test:sim:slow` (25 kanalli stsenariy) — test 03-05 Task 3 da yoziladi; sim tomonidagi mexanizm tayyor va o'lchangan (`channel_count=25` ish paytida ishlaydi).
2. `npm run gate` **534 s** da o'lchandi (`test:sim` bilan) va 618 s lik nomzod chegaraga sig'adi — 03-11 uni `03-VALIDATION.md` chegara jadvalida rasmiylashtiradi. ⚠ Worktree'da ishlaydigan agent frontend bosqichlaridan oldin `npm ci --prefix frontend` bajarishi kerak.
3. Sim testlarini `pg_container` dan ajratish (yuqoridagi chetlanish C) — ixtiyoriy, ~4–6 s.

## Bazaviy darvoza — o'lchangan holat

| Bosqich | Natija |
|---|---|
| `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (151 fayl, 154 formatlangan) |
| `pytest -q` (butun backend) | ✅ **1069** test (1021 → +48: 34 fixture + 5 sizmaslik + 9 sim) |
| `pytest tests/tenancy -q` | ✅ **322** test (o'zgarmadi) |
| `npm run test:sim` | ✅ **9** test |
| `pytest tests/unit/test_sim_fixtures.py tests/unit/test_no_sim_branching.py` | ✅ **39** test |
| `frontend i18n:check` | ✅ 439 kalit × 3 til |
| `frontend node --test scripts/*.test.mjs` | ✅ **60** test (o'zgarmadi) |
| `frontend vitest run` | ✅ **74** test / 11 fayl (o'zgarmadi) |
| `frontend typecheck` (`tsc --noEmit`) | ✅ toza |
| `frontend lint` (`eslint .`) | ✅ toza |
| `frontend build` (`next build`) | ✅ 3 til uchun to'liq prerender |
| **`npm run gate`** | ✅ **exit 0** — **534 s** |
| `git diff --exit-code services/core-api/pyproject.toml` | ✅ toza — yangi paket yo'q (T-03-SC) |

### `gate` kechikishi — o'lchangan qiymat

| O'lchov | Qiymat |
|---|---|
| 03-01 asosi (`test:sim` siz) | 496–515 s |
| **Bu reja (`test:sim` bilan)** | **534 s** |
| Qo'shimcha | **~+19…+38 s** |
| 03-01 belgilagan nomzod chegara | 618 s — **sig'adi** (zaxira ~84 s) |

Zanjir tartibi ham tasdiqlandi: `lint` → `test` → `test:tenancy` → **`test:sim`** → `i18n:check` → `vitest` → `typecheck` → `eslint` → `build`.

⚠ **Birinchi `gate` urinishi bu worktree'da `vitest` topilmagani uchun to'xtagan edi** (`'vitest' is not recognized…`). Sabab kod emas, muhit: git worktree'da `frontend/node_modules` yo'q (u `.gitignore` da). `npm ci --prefix frontend` dan keyin zanjir to'liq yashil bo'ldi. Bu 03-11 uchun ham amaliy qayd: worktree'da ishlaydigan har qanday agent frontend bosqichlaridan oldin `npm ci` bajarishi kerak.

## Self-Check: PASSED

- **Fayllar:** 21/21 mavjud (18 yangi + 3 o'zgargan)
- **Commitlar:** 3/3 mavjud (`1b7781d`, `427d8a4`, `b824700`)
- **`must_haves.artifacts` `contains` shartlari:** 5/5
  - `sim/digest.py` -> `qop` (7 marta) ✅
  - `sim/state.py` -> `__sim__` ✅
  - `fixtures/README.md` -> `hikvision_next` ✅
  - `tests/unit/test_no_sim_branching.py` -> `__sim__` ✅
  - `tests/integration/test_nvr_sim.py` -> `CI` ✅
- **`must_haves.key_links`:** 2/2
  - `compose.yaml` -> `nvr-sim` (`profiles: ["sim"]` + `dev` target) ✅
  - `test_nvr_sim.py` -> `NVR_SIM_BASE_URL` (haqiqiy TCP, `ASGITransport` emas) ✅
- **`import sim.main`:** exit 0 (standalone, `sys.path` bilan)
- **Ish daraxti:** toza (`__pycache__` — `.gitignore:10` da)

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
