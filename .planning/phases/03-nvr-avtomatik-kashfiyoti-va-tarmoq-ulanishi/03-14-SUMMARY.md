---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 14
subsystem: live-view-e2e
tags: [gap-closure, e2e, mockless, go2rtc, frame-jpeg, meta-gate, gate-latency, requirements, human-uat, wave-2]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 12
    provides: "`nvr-sim:554` da MediaMTX — anonim o'qish RAD ETILADI; `sim:up` prod `go2rtc` ni ham ko'taradi; `gate` de-duplikatsiya qilingan"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 13
    provides: "`_ensure_stream()` -> `get_credential()` -> `decrypt_nvr_password()` -> `authenticated_rtsp_source()` -> `ensure_stream(SecretStr)`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 11
    provides: "SC#1…SC#8 darvozasi va kechikish o'lchash protokoli (1200 s chegara)"
provides:
  - "`tests/integration/test_live_view_e2e.py` — MOCK'SIZ uchidan-uchiga o'lchov: kashfiyot -> chipta -> go2rtc -> `/api/frame.jpeg` -> HAQIQIY JPEG"
  - "`test_phase3_criteria.py::test_the_mockless_end_to_end_measurement_exists_and_runs` — o'lchovni yo'qolishdan saqlaydigan meta-darvoza"
  - "`tests/fixtures/nvr_flow.py` — NVR zanjiri yordamchilarining YAGONA nusxasi (ikki modul uchun)"
  - "`Go2rtcClient` ning `PUT`/`DELETE` natijasi STATUS KODIDAN emas, ro'yxatdan o'lchanadi (`:ro` config 400 beradi)"
  - "`03-HUMAN-UAT.md` — uskuna/deploy talab qiladigan olti band, egasi va tetigi bilan"
  - "`npm run gate` ning toza o'lchovi: **538 s** (chegara 1200 s, o'zgarmadi)"
affects: [04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Uchidan-uchiga o'lchov NOMLARNI MAHSULOTDAN oladi: oqim nomi kashfiyot hosil qilgan `cam_<uuid4>` va u chipta URL'ining `src=` idan ajratiladi — test o'z nomini o'ylab topsa, o'lchov mahsulot haqida hech nima isbotlamaydi (Pitfall 4)"
    - "Kadr asserti UCH SHARTLI: status 200 + JPEG SOI (`FF D8 FF`) + uzunlik >= 1024. Ikkala sabotajda ham go2rtc **200 va 0 bayt** qaytardi — faqat statusni tekshiradigan assert IKKALASIDA ham soxta-yashil bo'lardi"
    - "Tashqi servisning MUVAFFAQIYATI status kodidan emas, NATIJADAN o'lchanadi: go2rtc oqimni xotiraga qo'shib, keyin `:ro` configga yozolmay 400 qaytaradi — ro'yxatni qayta o'qish yagona to'g'ri o'lchov"
    - "Natijani o'lchash `except` blokidan TASHQARIDA bajariladi: ichida bajarilsa yangi istisnoning `__context__` i parolli URL tashigan `httpx` istisnosi bo'lardi (T-03-87 ning qayta ochilishi)"
    - "Tekshiruvning O'ZI yiqilishi mumkin -> uch holatli javob (`True`/`False`/`None` = «ayta olmadim») va `None` FAIL-CLOSED talqin qilinadi"
    - "Ikki modul bir zanjirni kesib o'tsa — zanjir UCHINCHI joyda yashaydi (`fixtures/nvr_flow.py`), fixture'lari esa conftest reyestrida; ikki nusxa jimgina ajralib ketardi"
    - "Meta-darvoza o'lchovning MAVJUDLIGINI emas, XUSUSIYATLARINI majburlaydi: modul import qilinadi, `sim` markeri bor va birorta testi mock fixture'ini so'ramaydi"

key-files:
  created:
    - tests/integration/test_live_view_e2e.py
    - tests/fixtures/nvr_flow.py
    - .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-HUMAN-UAT.md
  modified:
    - services/core-api/app/services/go2rtc.py
    - tests/unit/test_go2rtc_client.py
    - tests/integration/test_phase3_criteria.py
    - tests/integration/conftest.py
    - .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "REJADA YO'Q, LEKIN MAJBURIY (Rule 1): `Go2rtcClient` ning `PUT`/`DELETE` natijasi endi ro'yxatdan o'lchanadi. Birinchi MOCK'SIZ o'lchov go2rtc ning `PUT /api/streams` **400** qaytarishini ochdi — u oqimni xotiraga qo'shib, keyin `:ro` mount qilingan `/config/go2rtc.yaml` ga yozmoqchi bo'ladi va o'sha qadam HAR DOIM yiqiladi. `raise_for_status()` ga so'zsiz ishonish jonli ko'rishni ISHLAB TURGAN holatda 503 qilardi. Rejaning O'Z sabotaj mezoni (S1: «chipta hamon 200 keladi») bu tuzatishsiz bajarilmasdi"
  - "`03-VALIDATION.md` ning taklif qilgan yopilish yo'li («sim'dan bitta kadr olib JPEG ekanini tekshirish») ATAYIN ISHLATILMADI — u mahsulot yo'lini chetlab o'tardi va aynan Pitfall 4 bo'lardi. Oqim nomi kashfiyotdan keladi va chipta URL'idan ajratiladi"
  - "Zanjir yordamchilari `test_phase3_criteria.py` dan `fixtures/nvr_flow.py` ga chiqarildi, e2e modul ularni IMPORT qiladi. Muqobil (test modulidan test moduliga import) repoda ochiq qoralangan naqsh (`go2rtc_calls` fixture'ining izohi) va u ikki fayl orasida yashirin bog'liqlik hosil qilardi"
  - "Meta-darvozaning nomi `test_sc` bilan BOSHLANMAYDI: `test_every_criterion_has_its_own_test` mezon testlarini SANAYDI va to'qqizinchi `test_sc*` uni qizartirardi"
  - "`MOCK_FIXTURE = \"go2rtc_calls\"` satri darvozaning O'ZIDA `hasattr` bilan tasdiqlanadi — mock qayta nomlansa darvoza mavjud bo'lmagan naqsh izlab jimgina yashil qolardi"
  - "CAM-03 `Done`, LEKIN brauzerdagi idrok `03-HUMAN-UAT.md` #5 ga chiqarildi va dalil satrida OCHIQ aytiladi. CAM-09 ham `Done`, va uning matnidagi «go2rtc RTSP manbasi» endi harfma-harf to'g'ri emasligi (MediaMTX) yashirilmadi"
  - "CAM-02 `Blocked` BO'LIB QOLDI. CI'da `wg0` yo'q; soxta yashil test yozish yomonroq bo'lardi (Pitfall 10). Egasi Ops, tetigi VPS deploy'i, bandlari `03-HUMAN-UAT.md` #1 va #2"
  - "Chegara 1200 s da QOLDI — na ko'tarildi (talab shunday), na tushirildi. 538 s ga 2.2× zaxira bo'shashgan signal ekani ochiq yozildi va qayta belgilash 4-fazaga band sifatida qoldirildi: chegara o'zgarishi bir necha yugurishga tayanishi kerak"

patterns-established:
  - "Pattern: sabotajning KUTILGANDAN KENGROQ qizarishi ham natija — S2 da `test_rtsp_source.py` ning ikkita testi ham qizardi va sabab strukturaviy (MediaMTX yo'lni AUTENTIFIKATSIYADAN OLDIN hal qiladi); buni yashirish o'rniga sabab yozildi"
  - "Pattern: mock bilan almashtirilgan tashqi servisning tarmoq xulqi HECH QACHON o'lchanmagan bo'ladi — birinchi mock'siz o'lchov mahsulot nuqsonini ochishi KUTILGAN natija, chetlanish emas"
  - "Pattern: assert xabari qiymatlar emas, O'LCHOVLAR ro'yxatidan iborat (nom, soniya, urinish, status, UZUNLIK) — sir ham, binar ham jurnalga chiqmaydi"

requirements-completed: [CAM-03, CAM-09]

# Metrics
duration: 95min
completed: 2026-08-03
---

# Phase 3 Plan 14: Mock'siz uchidan-uchiga jonli ko'rish o'lchovi Summary

**`03-VERIFICATION.md` ning ikkala bo'shlig'i ham o'lchov bilan yopildi: kashfiyot hosil qilgan `cam_<uuid4>` oqimidan, jonli ko'rish chiptasi berilgandan keyin, mahsulot go2rtc'i orqali `/api/frame.jpeg` dan **99 681 baytli HAQIQIY JPEG** keladi — birorta mock ishlatilmasdan; o'lchov meta-darvoza bilan qulflandi, `npm run gate` toza sharoitda **538 s** o'lchandi, CAM-03/CAM-09 dalil bilan `Done` bo'ldi va CAM-02 sababi bilan ochiq qoldi.**

## Performance

- **Duration:** ~95 min (shundan **~9 min** — `npm run gate` ning bir yugurishi, **~2 min** — ikkala sabotaj)
- **Tasks:** 3/3, to'rtta commit (Task 1 ikkiga bo'lindi: mahsulot tuzatishi alohida)
- **Files:** 10 (3 yaratildi, 7 o'zgartirildi)
- **Sabotajlar:** 2/2 bajarildi, har biridan keyin ish daraxti toza

## Task Commits

| Task | Nomi | Commit | Asosiy fayllar |
| ---- | ---- | ------ | -------------- |
| 1a | go2rtc `PUT`/`DELETE` natijadan o'lchanadi (Rule 1 tuzatish) | `9d2bbd8` | `app/services/go2rtc.py`, `tests/unit/test_go2rtc_client.py` |
| 1b | Mock'siz uchidan-uchiga o'lchov va meta-darvoza | `3be8575` | `test_live_view_e2e.py`, `fixtures/nvr_flow.py`, `integration/conftest.py`, `test_phase3_criteria.py` |
| 2 | Darvoza vaqti + talab holatlari | `f3ab52b` | `03-VALIDATION.md`, `REQUIREMENTS.md`, `ROADMAP.md` |
| 3 | `03-HUMAN-UAT.md` | `5d34f08` | `03-HUMAN-UAT.md` |

## KADR KELDI — asosiy o'lchov

| O'lchov | Qiymat |
|---|---|
| Kadr kelgunicha o'tgan vaqt | **0.26 s** |
| Urinishlar soni | **1** (chegara: 45 urinish / 45 s) |
| Kadr hajmi | **99 681 bayt** |
| Birinchi bayt | `FF D8 FF` (JPEG SOI) |
| Sovuq boshlash (`nvr-sim-rtsp` va `go2rtc` qayta ishga tushirilgandan keyin) | **0.26 s**, hamon 1 urinish |

⚠ **Nega sovuq va issiq bir xil:** `runOnDemand` ffmpeg birinchi tomoshabin
kelganda ishga tushadi, tomoshabin esa **chipta so'ralganda** paydo bo'ladi
(`PUT /api/streams` -> go2rtc RTSP sessiyasini ochadi). Ya'ni kadr kutish
tsikli boshlanganda quvur ALLAQACHON issiq bo'ladi. 45 soniyalik chegara
shuning uchun ~170× zaxira bilan qoladi va u o'lchovdan emas, ehtiyotdan
kelib chiqqan.

## ⚠ MAHSULOT NUQSONI — birinchi mock'siz o'lchov ochdi

Bu rejaning eng qimmatli topilmasi va u **rejada nomlanmagan**.

**Kuzatuv (haqiqiy konteynerlar ustida, kod yozilishidan oldin):**

```
PUT /api/streams?name=...&src=rtsp://admin:***@nvr-sim:554/...
  -> 400  "yaml: line 38: did not find expected key"
GET /api/streams
  -> 200  ['smoke_probe_0314']          <- oqim RO'YXATDA
GET /api/frame.jpeg?src=smoke_probe_0314
  -> 200  99 681 bayt, JPEG             <- kadr KELADI
DELETE /api/streams?src=smoke_probe_0314
  -> 400  "open /config/go2rtc.yaml: read-only file system"
GET /api/streams
  -> 200  []                            <- oqim CHIQDI
```

**Sabab:** go2rtc `PUT`/`DELETE` ni **ikki qadamda** bajaradi — avval
xotiradagi ro'yxatni o'zgartiradi, keyin uni `/config/go2rtc.yaml` ga
yozib qo'ymoqchi bo'ladi. Bizda o'sha fayl `:ro` mount qilingan va bu
**ataylab** (D-11 — `exec:` ning konfiguratsiyaga muhrlanishiga qarshi
qatlam; `PATCH /api/config` yo'li RESEARCH D.13 da ochiq rad etilgan).
Ya'ni ikkinchi qadam **har doim** yiqiladi va javob 400 bo'ladi.

**Ta'siri:** `raise_for_status()` -> `Go2rtcError` -> `POST /cameras/{id}/live-token`
**503**. Jonli ko'rish ISHLAB TURGAN holatda har safar 503 berardi.

**Nega ilgari ko'rinmadi:** `Go2rtcClient` mahsulot yo'lida hech qachon
haqiqiy go2rtc ustida bajarilmagan edi — `test_live_view.py` ham,
`test_phase3_criteria.py` ham uni `go2rtc_calls` mock'i bilan
almashtirardi, `test_go2rtc_client.py` esa `httpx.MockTransport` ishlatadi
va u 400 qaytarmasdi. Bu **aynan** GAP-2 ning nima uchun bo'shliq
ekanini ko'rsatadi.

**Tuzatish (Rule 1, `9d2bbd8`):** muvaffaqiyat status kodidan emas,
**natijadan** o'lchanadi — `PUT` yiqilsa ro'yxat qayta o'qiladi va oqim
bor bo'lsa amal bajarilgan hisoblanadi; `DELETE` uchun teskarisi. Uch
nozik nuqta:

1. **istisno `except` blokidan TASHQARIDA ko'tariladi** — ichida
   ko'tarilsa yangi istisnoning `__context__` i parolli URL tashigan
   `httpx` istisnosi bo'lardi (T-03-87 ning qayta ochilishi);
2. `_registered()` **uch holatli** (`True`/`False`/`None` = «ayta
   olmadim») va `None` **fail-closed** talqin qilinadi — aks holda
   tuzatish «har qanday 400 ni yutish» ga aylanardi;
3. `ensure_stream` da `from None` (URL'da sir bor), `remove_stream` da
   `from delete_cause` (URL'da sir yo'q) — `03-13` o'rnatgan farq
   SAQLANDI.

D-11 **yumshatilmadi**: konfiguratsiyaga yozish baribir bajarilmaydi va
bu ATAYIN — oqimlar xotirada yashaydi.

## Sabotajlar — nomma-nom natija

### S1 — MARKAZIY DA'VO: rekvizit oyog'i olib tashlandi

**O'zgartirish:** `cameras.py::_ensure_stream` da
`authenticated_rtsp_source(url, device.username, password)` ->
`SecretStr(url)` (rekvizitsiz `rtsp_url()` chiqishi).

**Buyruq:** `pytest test_live_view_e2e.py test_phase3_criteria.py test_live_view.py test_rtsp_source.py`
-> **4 failed, 31 passed** (67.9 s)

**QIZARDI — va AYNAN kutilgan joyda:**

| Test | Qaysi assert | Kuzatilgan |
|---|---|---|
| **`test_live_view_e2e.py::test_a_frame_arrives_through_the_discovered_stream`** | **`assert probe.arrived`** — ya'ni KADR asserti | `45 urinish, 45.0 s, oxirgi status 200, tana uzunligi 0 bayt` |
| `test_phase3_criteria.py::test_sc7_...` | `parts.username == quote(username, safe="")` | 03-13 S3 ning takrori |
| `test_live_view.py::test_stream_registered_dynamically` | `parts.username == NVR_USERNAME` | 03-13 S3 ning takrori |
| `test_live_view.py::test_live_token_never_leaks_the_device_password` | nazorat bandi: `real_credentials in source` | 03-13 S3 ning takrori |

**CHIPTA HAMON 200 KELDI** — test `assert issued.status_code == 200` va
`_stream_name_from(...)` dan MUVAFFAQIYATLI o'tdi va faqat kadr
assertida to'xtadi. Reja aynan shuni talab qilgan edi («sozlash xatosida
emas»).

**YASHIL QOLDI (reja talab qilgan uchala to'plam ham):**

| To'plam | Natija |
|---|---|
| `test_phase3_criteria.py::test_sc6_live_view_requires_authorization` | ✅ — u avtorizatsiyani o'lchaydi, rekvizitni emas |
| `test_live_view.py` ning AVTORIZATSIYA testlari (rad etish matritsasi, 403/404/chipta bog'lanishi) | ✅ |
| `tests/integration/test_rtsp_source.py` (3 test) | ✅ |
| `test_live_view_e2e.py::test_an_archived_camera_never_reaches_the_real_go2rtc` | ✅ |

⚠ **Eng qimmatli tafsilot:** go2rtc **200 va 0 bayt** qaytardi. Ya'ni
`assert response.status_code == 200` shaklidagi sodda assert bu sabotaj
ostida **soxta-yashil** bo'lardi. Kadr assertining uch sharti (status +
JPEG SOI + `>= 1024` bayt) shu sababdan zarur.

**Tiklash:** `git checkout -- services/core-api/app/api/v1/cameras.py` ->
`git status --short` **toza** -> `pytest test_live_view_e2e.py test_rtsp_source.py`
-> **5 passed**.

### S2 — YO'L MOSLASHUVI: `Channels` -> `Channel`

**O'zgartirish:** `ops/mediamtx/mediamtx.yml` dagi yo'l regulyar ifodasi
`"~^Streaming/Channels/[0-9]+$"` -> `"~^Streaming/Channel/[0-9]+$"`;
`nvr-sim-rtsp` qayta ishga tushirildi.

**Buyruq:** `pytest test_live_view_e2e.py test_rtsp_source.py` ->
**3 failed, 2 passed** (56.5 s)

| Test | Qaysi assert | Kuzatilgan |
|---|---|---|
| **`test_live_view_e2e.py::test_a_frame_arrives_through_the_discovered_stream`** | **`assert probe.arrived`** — KADR asserti | `45 urinish, 45.0 s, status 200, 0 bayt` |
| `test_rtsp_source.py::test_anonymous_describe_is_rejected` | `"401" in status_line.split()` | `RTSP/1.0 400 Bad Request` |
| `test_rtsp_source.py::test_unknown_channel_also_requires_credentials` | `"401" in status_line.split()` | `RTSP/1.0 400 Bad Request` |

**YASHIL QOLDI:** `test_rtsp_source.py::test_rtsp_source_listens_on_the_advertised_port`
(u faqat «554 da RTSP gapiradigan server bormi» deydi) va
`test_live_view_e2e.py::test_an_archived_camera_never_reaches_the_real_go2rtc`.

⚠ **REJADAN CHETLANISH — sabotaj KUTILGANDAN KENGROQ qizardi va bu
o'lchov natijasi.** Reja `test_rtsp_source.py` ning **yashil qolishini**
kutgan edi («u autentifikatsiyani o'lchaydi, yo'lni emas»). Amalda
MediaMTX yo'lni **autentifikatsiyadan OLDIN** hal qiladi: birorta
`paths:` yozuviga mos kelmagan so'rov uchun u qaysi auth qoidasini
qo'llashni ayta olmaydi va `401` emas, **`400 Bad Request`** qaytaradi.

Ya'ni «manba rekvizit talab qiladi» da'vosi «yo'l konfiguratsiyada
mavjud» shartiga BOG'LIQ. Bu nuqson emas — **to'g'ri konfiguratsiyada**
`/Streaming/Channels/9901` (kanal 99) regulyar ifodaga MOS KELADI va
`401` oladi, ya'ni `test_unknown_channel_also_requires_credentials`
ning niyati («mavjudlik autentifikatsiyadan oldin oshkor bo'lmaydi»)
buzilmaydi. Rejaning MARKAZIY kutilmasi esa tasdiqlandi: kadr asserti
yo'l moslashuvini haqiqatan o'lchaydi.

**Tiklash:** `git checkout -- ops/mediamtx/mediamtx.yml` ->
`git status --short` **toza** -> konteyner qayta ishga tushirildi ->
`pytest test_live_view_e2e.py test_rtsp_source.py` -> **5 passed**.

## `npm run gate` — BIR MARTA, TOZA SHAROITDA

| O'lchov | Qiymat |
|---|---|
| **`npm run gate`** | **exit 0, 538 s** (`18:36:38Z` -> `18:45:36Z`) |
| `03-11` ning bazaviy o'lchovi (eski zanjir, 3 yugurish) | 1000 / 994 / 983 s |
| `03-12` ning oraliq o'lchovi (parallel yuk ostida) | 716 s — chegara uchun ishlatilmagan |
| **Chegara** | **1200 s — KO'TARILMADI va TUSHIRILMADI** (2.2× zaxira) |
| Farq (`03-11` ga nisbatan) | **−462 s (−46 %)**; bashorat −316 s (−31 %) edi |

Zanjirning sakkizala qadami `exit 0`: `sim:up` (uchala konteyner
`healthy`) · `ruff` + `ruff format` + `mypy` (**202 fayl formatlangan**,
**196 manbada muammo yo'q**) · pytest **1520 test** · i18n **576 × 3** ·
`node --test` **86 pass / 0 fail** · vitest **246 passed (20 fayl)** ·
`typecheck` · `eslint` · `next build`.

⚠ **Farq bashoratdan 146 s katta va buni «bonus» deb yozish noto'g'ri
bo'lardi.** Ikki o'lchov bir xil sharoitda olinmagan: `03-11` **uchta**
yugurishning eng yomonini olgan (sovuq `frontend/.next` keshi bilan),
bugungisi esa **bitta** yugurish va unda Docker image'lari ham, frontend
keshi ham issiq edi. Ishonch bilan aytiladigani: **media quvuri zanjirni
sezilarli qimmatlashtirmadi** (u LAZY va kadr birinchi urinishda keladi)
va **zanjir chegaradan ikki barobardan ko'proq pastda**.

⚠ **Chegara tushirilmagani ham qaror.** 2.2× zaxira signalni
bo'shashtiradi; uni qattiqlashtirish bir necha yugurishning o'lchoviga
tayanishi kerak va shu sababdan `03-VALIDATION.md` ning `open_items`
iga 4-faza bandi sifatida yozildi — jimgina o'zgartirilmadi.

## Talab holatlari — dalil bilan

| Talab | Edi | Bo'ldi | Dalil / sabab |
|---|---|---|---|
| **CAM-03** | `Blocked` | **`Done`** | `tests/integration/test_live_view_e2e.py::test_a_frame_arrives_through_the_discovered_stream` — kadr HAQIQATAN keladi (99 681 bayt). ⚠ Brauzerdagi ijro va idrok O'LCHANMAGAN va bu dalil satrida OCHIQ aytilgan: `03-HUMAN-UAT.md` #5 |
| **CAM-09** | `Blocked` | **`Done`** | Beshala bandi o'lchanadi; «jonli ko'rish» va «kadr olish yo'li» ikkalasi ham `/api/frame.jpeg` orqali — bu 4-fazaning STANDART mexanizmi. ⚠ Talab matnidagi «go2rtc RTSP manbasi» endi harfma-harf to'g'ri emas (MediaMTX) va bu yashirilmadi |
| **CAM-02** | `Blocked` | **`Blocked`** | CI konteynerida `wg0` YO'Q; soxta yashil test Pitfall 10 bo'lardi. **Egasi Ops, tetigi VPS deploy'i**, bandlari `03-HUMAN-UAT.md` #1 va #2 |
| CAM-01, CAM-08 | `Done` | `Done` | TEGILMADI |

`npm run requirements:check` -> **exit 0** · 49 talab MOS · **Done 11 ·
Pending 37 · Blocked 1**.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] go2rtc `PUT`/`DELETE` ning 400 javobi jonli ko'rishni 503 qilardi**
- **Found during:** Task 1, mahsulot yo'lini haqiqiy konteynerlar ustida zondlashda
- **Issue:** Yuqorida batafsil («MAHSULOT NUQSONI» bo'limi). `:ro` mount qilingan config (D-11) tufayli go2rtc har `PUT` va har `DELETE` da 400 qaytaradi, amalning O'ZI esa bajariladi.
- **Fix:** natijadan o'lchash (`_registered()` uch holatli, fail-closed); istisno `except` blokidan tashqarida ko'tariladi.
- **Files modified:** `services/core-api/app/services/go2rtc.py`, `tests/unit/test_go2rtc_client.py` (+3 test)
- **Nega REJA DOIRASIDA:** rejaning O'Z sabotaj mezoni (S1: «chipta hamon 200 keladi, kadr esa kelmaydi») bu tuzatishsiz bajarilmasdi — sabotajsiz ham chipta 503 berardi.
- **Commit:** `9d2bbd8`

**2. [Rule 3 - Blocking] Eskirgan sim konteynerlari**
- **Found during:** Task 1 ning boshi
- **Issue:** Xostda `03-12` dan oldingi `go2rtc-sim` konteyneri hamon ishlab turardi va `nvr-sim` eski konfiguratsiya bilan edi — `nvr-sim-rtsp` umuman yaratilmagan.
- **Fix:** `docker rm -f sbozor-go2rtc-sim-1` + `docker compose --profile sim up -d nvr-sim nvr-sim-rtsp go2rtc --wait` (compose `nvr-sim` ni konfiguratsiya drifti sababli o'zi qayta yaratdi va `nvr-sim-rtsp` uning yangi netns'iga ulandi).
- **Repoda o'zgarish YO'Q** — bu ijro muhitining holati.

### Rejadan chetlanishlar

**A. Zanjir yordamchilari UMUMIY joyga chiqarildi (reja ikkala yo'lni ham ruxsat etgan).**
Reja «`test_phase3_criteria.py` dan import qiling YOKI umumiy joyga
chiqaring» degan edi. Ikkinchisi tanlandi: birinchisi test modulidan
test moduliga import bo'lardi va bu naqsh repoda ochiq qoralangan
(`go2rtc_calls` fixture'ining izohi: «yashirin bog'liqlik hosil
qilardi»). Natijada `fixtures/nvr_flow.py` yaratildi,
`enqueued`/`nvr_cleanup` fixture'lari `tests/integration/conftest.py`
reyestriga ko'chdi, `admin_headers`/`director_headers` esa har modulda
LOKAL qoldi (ikki qatorlik fixture va `test_assignments_api.py` da
xuddi shu nomlar allaqachon bor).

**B. S2 sabotaji kutilgandan kengroq qizardi** — batafsil yuqorida.
Rejaning markaziy kutilmasi (kadr asserti yo'l moslashuvini o'lchaydi)
tasdiqlandi; qo'shimcha ikki qizarish MediaMTX ning «yo'l
autentifikatsiyadan oldin» tartibini ochdi va u yozib qo'yildi.

**C. Kadr «45 s ichida» emas, 0.26 s da keldi.** Reja 45 soniyalik
chegarani va 1 soniyalik oraliqni talab qilgan; ular saqlandi, lekin
amalda BIRINCHI urinish yetdi. Sabab yuqorida (quvur chipta so'ralganda
issiq bo'ladi). Chegara TUSHIRILMADI — u sekin CI mashinasi uchun zaxira.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking) + 3 rejadan chetlanish
**Impact on plan:** Doira kengaymadi — yangi xizmat, endpoint yoki
bog'liqlik qo'shilmadi. `go2rtc.py` rejaning `files_modified` ida yo'q
edi, lekin usiz rejaning O'Z qabul mezoni bajarilmasdi.

## Verification

| Tekshiruv | Natija |
|---|---|
| `npm run sim:up && pytest test_live_view_e2e.py test_phase3_criteria.py` | **12 passed** (16.1 s) |
| `pytest tests/integration -m "sim and not slow"` | **76 passed** (03-12 dan keyin 73 edi) |
| `pytest --co` | **1520 test** (5 hardware deselected) — kamaymadi, **+6** |
| `pytest tests/tenancy --co` | **412** — o'zgarmadi |
| `pytest tests/unit/test_go2rtc_client.py` | **30 passed** (edi 27, **+3**) |
| `ruff check . && ruff format --check . && mypy .` | **exit 0** — 202 fayl formatlangan, 196 manbada muammo yo'q |
| `npm run gate` | **exit 0, 538 s** |
| `npm run validation:check -- .../03-VALIDATION.md` | **exit 0** — `nyquist_compliant: true`, Per-Task **43**, inson bandlari **6** |
| `npm run requirements:check` | **exit 0** — 49 MOS, Done 11 · Blocked 1 |
| `grep -c 'go2rtc_calls' test_live_view_e2e.py` | **0** ✓ |
| `grep -c 'frame.jpeg' test_live_view_e2e.py` | **4** (>=1) ✓ |
| `test_every_criterion_has_its_own_test` | ✅ yashil — mezon testlari soni hamon **8** |
| Meta-darvoza `--collect-only` da | ✅ `test_the_mockless_end_to_end_measurement_exists_and_runs` (10 test yig'ildi) |
| `grep -c 'result: \[pending\]' 03-HUMAN-UAT.md` | **6** (>=6) ✓ |
| vitest / node:test / i18n | **246** / **86 pass, 0 fail** / **576 × 3** — o'zgarmadi |
| Ish daraxti | **toza** (faqat oldindan mavjud kuzatilmagan `.docx`/`.md` fayllar) |

## Known Stubs

Yo'q. Bu rejada yozilgan hamma narsa ishlaydigan holatda: kadr haqiqatan
keladi (o'lchandi), meta-darvoza haqiqiy modulni import qiladi,
`03-HUMAN-UAT.md` ning oltala bandi egasi va tetigi bilan yozilgan va
birortasi «o'lchandi» deb ko'rsatilmagan.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, autentifikatsiya yo'li yoki sxema
o'zgarishi kiritilmadi. `go2rtc.py` ning tuzatishi ishonch chegarasini
KENGAYTIRMAYDI: allow-list (`assert_safe_go2rtc_src`) o'zgarmadi va
hamon tarmoqqa chiqishdan OLDIN ishlaydi; `:ro` mount ham, uch qatlamli
D-11 himoyasi ham tegilmadi. Yangi qo'shilgan yagona tarmoq chaqiruvi —
`PUT`/`DELETE` yiqilganda bajariladigan `GET /api/streams`, va uning
javob tanasi (T-03-90) hech qayerda chop etilmaydi.

## Issues & Notes

1. **`Go2rtcClient.remove_stream` endi HAQIQATAN bajariladi** — e2e
   testning `finally` sida. Uning tarmoq xulqi shu bilan birinchi marta
   o'lchandi. Mahsulot MARSHRUTIDA (arxivlash) u hamon chaqirilmaydi va
   bu ATAYIN (`03-VALIDATION.md` `open_items`); to'g'ri shakl —
   4-fazadagi reconciliation.
2. **go2rtc ning O'Z jurnali `PUT` URL'ini, ya'ni parolni ko'radi**
   (`03-13` Issue 2). Endi unga yana bir tafsilot qo'shiladi: har `PUT`
   400 bilan tugagani uchun go2rtc jurnalida **xato darajasidagi** qator
   ham qoladi. 8-faza (deploy runbook) uchun: go2rtc jurnali tashqi
   log-agregatorga UZATILMASIN.
3. **MediaMTX yo'lni autentifikatsiyadan OLDIN hal qiladi** (S2 ning
   topilmasi). `test_rtsp_source.py` ning «rekvizit talab qilinadi»
   da'vosi shu sababdan «yo'l konfiguratsiyada mavjud» shartiga
   bog'liq. Bugun band emas — to'g'ri konfiguratsiyada ikkala test ham
   o'z niyatini o'lchaydi — lekin `paths:` o'zgarganda buni eslash kerak.
4. **`gate` chegarasi 2.2× bo'shashgan** (538 s / 1200 s). 4-fazaga band.
5. **4-faza uchun tayyor:** `/api/frame.jpeg` yo'li endi mahsulot
   zanjirining ichida o'lchanadi — 4-fazaning kadr olish jobi shu
   mexanizmni ishlatadi va uning oldingi sharti (`03-VERIFICATION.md`
   shunday nomlagan) bajarildi.

## Self-Check: PASSED

**Fayllar** (`ls -1`): `tests/integration/test_live_view_e2e.py`,
`tests/fixtures/nvr_flow.py`, `03-HUMAN-UAT.md`,
`services/core-api/app/services/go2rtc.py`, `tests/unit/test_go2rtc_client.py`,
`tests/integration/test_phase3_criteria.py`, `tests/integration/conftest.py`,
`03-VALIDATION.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` —
o'nalasi ham mavjud.

**Commitlar** (`git log --oneline`): `9d2bbd8`, `3be8575`, `f3ab52b`,
`5d34f08` — to'rttasi ham topildi.

**Reja mezonlari (`must_haves`):**
`test_live_view_e2e.py` **373 qator** (min 100) ✓ ·
`03-HUMAN-UAT.md` da `result: [pending]` **6** marta ✓ ·
`key_links`: `test_live_view_e2e.py` -> `frame\.jpeg` **4** ta moslik ✓,
`test_phase3_criteria.py` -> `test_live_view_e2e` **3** ta moslik ✓.

**`must_haves.truths`:** 3/3 — SC#6 ning ikkinchi yarmi mahsulot
yo'lidan o'tib o'lchandi (kadr keldi); SC#7 ning oxirgi bo'g'ini
mock'siz kesib o'tildi (`Go2rtcClient` almashtirilmadi); yopilmagan
oltala band egasi va tetigi bilan yozildi va birortasi «o'lchandi» deb
ko'rsatilmadi.

**Sabotajlar:** 2/2, har biridan keyin `git status --short` **toza**.

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
