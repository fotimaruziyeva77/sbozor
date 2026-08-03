---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 12
subsystem: infra
tags: [mediamtx, rtsp, sim, compose, network-mode, auth, gate-latency, supply-chain, wave-1]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 02
    provides: "`nvr-sim` konteyneri, `SIM_RTSP_PORT_ADVERTISED`, `sim` markeri va `sim` fixture'i (CI'da `fail`, skip emas)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 11
    provides: "`gate` zanjirining qadam-baqadam o'lchovi va 31 % qayta bajarish topilmasi"
provides:
  - "`nvr-sim-rtsp` — sim NVR'ning RTSP oyog'i, `network_mode: service:nvr-sim` bilan NVR'ning O'Z manzilida (`nvr-sim:554`)"
  - "`ops/mediamtx/mediamtx.yml` — Hikvision `/Streaming/Channels/<id>` regex yo'li, `authInternalUsers` bilan MAJBURIY rekvizit, RTSP dan boshqa hamma server o'chirilgan"
  - "`tests/integration/test_rtsp_source.py` — rekvizitsiz `DESCRIBE` -> `401` + `WWW-Authenticate` ning xom TCP o'lchovi (3 test)"
  - "`tests/unit/test_compose_sim_env.py` — har bir `SIM_*` kalitining iste'molchisi bor; o'lik konfiguratsiya CI'da qizaradi (4 test)"
  - "`SIM_RTSP_HOST` / `SIM_RTSP_PORT` compose'dan olib tashlandi; qaytishi darvoza bilan to'silgan"
  - "`gate` zanjiri de-duplikatsiya qilindi: `test:tenancy` + `test:sim` chiqarildi, `sim:up` boshiga o'tdi"
affects: [03-13, 03-14, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added:
    - "bluenviron/mediamtx 1.19.3-ffmpeg (MIT) — FAQAT `--profile sim`, digest bilan qadalgan"
  patterns:
    - "Simulyator qurilmaning TOPOLOGIYASINI ham modellaydi, faqat protokolini emas: ISAPI va RTSP bitta netns'da (`network_mode: service:<nvr>`) — real NVR'da ular bitta manzilda yashaydi"
    - "Sim manbai rekvizitni MAJBURIY qiladi: manba anonim o'qishga ruxsat bersa, uni iste'mol qiladigan kodning rekvizit oyog'i umuman o'lchanmay qoladi"
    - "O'lik muhit o'zgaruvchisi darvozasi: compose'dagi har bir prefiksli kalitning iste'molchisi mexanik izlanadi; skaner O'Z faylini iste'molchilar to'plamidan chiqarib tashlaydi"
    - "Konfiguratsiya kalitlari o'rnatilgan versiyaning MOS YOZUVLAR faylidan olinadi (`docker cp <konteyner>:/mediamtx.yml`), hujjat sahifasidan emas — noto'g'ri kalit serverni ishga tushishda yiqitadi, ya'ni jimgina o'tib ketmaydi"
    - "Zanjirdan qadam olib tashlanganda uning YAGONA haqiqiy xususiyati (bu holda `sim:up --wait`) alohida saqlanadi — tejash qamrovni kamaytirmaydi"

key-files:
  created:
    - ops/mediamtx/mediamtx.yml
    - tests/integration/test_rtsp_source.py
    - tests/unit/test_compose_sim_env.py
  modified:
    - compose.yaml
    - package.json
    - ops/go2rtc/go2rtc.yaml
    - ops/docs/nvr-onboarding.md
    - tests/fixtures/nvr_sim.py
  deleted:
    - ops/go2rtc/go2rtc.sim.yaml

key-decisions:
  - "`network_mode: service:nvr-sim` — bu ARXITEKTURAVIY qaror, qulaylik emas. Real NVR'da ISAPI ham, RTSP ham bitta manzilda yashaydi va kashfiyot hosil qiladigan URL'ning xosti `nvr_devices.host` dan keladi. Ikki xil xost (`nvr-sim` + `go2rtc-sim`) GAP-1 ning ildizi edi: mahsulot yo'lidan boradigan test yozilganda ulanadigan joy YO'Q edi"
  - "`SIM_RTSP_HOST` iste'mol qilinmadi, O'CHIRILDI: to'g'ri modelda alohida «RTSP xosti» tushunchasining O'ZI yo'q. Kalitni tirik qilish noto'g'ri modelni kodga muhrlab qo'yardi"
  - "Anonim o'qish RAD ETILADI va bu deliverable'ning eng muhim xususiyati. Manba anonim o'qishga ruxsat bersa 03-13 ning rekvizit uzatish oyog'i UMUMAN o'lchanmasdan qolardi va 03-14 ning testi rekvizit tashlab yuborilganda ham yashil bo'lardi. S1 sabotaji shuni tasdiqladi"
  - "MediaMTX tanlandi, `go2rtc-sim` saqlanmadi: Hikvision yo'li `/Streaming/Channels/102` ichida SLESH bor va go2rtc'ning oqim nomi <-> URL yo'li moslashuvi sleshli nom uchun HUJJATLASHTIRILMAGAN. Ijro paytida go2rtc'ning bunga qodirligiga dalil TOPILMADI — reja qarori kuchida qoladi"
  - "Image `@sha256:` digest bilan qadaldi, teg bilan emas (T-03-82/T-03-SC). Teg ko'chirilishi mumkin, digest — yo'q"
  - "`rtspAuthMethods: [basic, digest]` — MediaMTX standarti faqat `basic`, real Hikvision esa Digest so'raydi. Sim mijozdan real qurilmadan KAMROQ narsa talab qilmasligi kerak"
  - "`moq: false` QO'SHILDI (rejada yo'q edi): MediaMTX 1.19.3 da Media-over-QUIC serveri standart bo'yicha YOQIQ (`:8892`) — T-03-83 ning «qolgan serverlar hammasi o'chiriladi» talabini qanoatlantirish uchun zarur"
  - "`gate` dan `test:tenancy` va `test:sim` olib tashlandi; `sim:up` boshiga chiqarildi. Bu 03-VALIDATION.md ning o'z taklifi va u qamrovni kamaytirmaydi (1457 ⊃ 412 ⊃ 70). Chegara (1200 s) KO'TARILMADI — u 03-14 da bir marta o'lchanadi"
  - "Tekshiruv IZOLYATSIYALANGAN compose loyihasida bajarildi (`COMPOSE_PROJECT_NAME=sbozor0312`): `compose.yaml` `name: sbozor` ni qadalgan holda saqlaydi va parallel ishlayotgan 03-13 ijrochisi AYNAN shu loyihani bo'lishadi. Izolyatsiyasiz ularning `docker compose up` i `nvr-sim` ni qayta yaratib, `nvr-sim-rtsp` ulangan netns'ni yo'q qilardi"

patterns-established:
  - "Pattern: uchinchi tomon image'ining ta'minot zanjiri tekshiruvi KOD YOZILISHIDAN OLDIN bajariladi va natijasi (litsenziya, arxiv holati, oxirgi release sanasi, digest) SUMMARY ga yoziladi — image repoga kirgandan keyin uni ko'rish kech"
  - "Pattern: sabotaj YASHIL qoladigan to'plamni ham NOMLAYDI — «nima qizardi» kabi «nima qizarmadi» ham o'lchov natijasi (bu yerda: liveness zondi ataylab yashil qoldi, chunki u faqat «RTSP gapiradimi» deydi)"
  - "Pattern: sim testidagi port QOTIRILMAYDI — u `__sim__/state` dan so'raladi, ya'ni `adminAccesses` e'lon qiladigan qiymat bilan bitta manbadan keladi"
  - "Pattern: takrorlangan qiymat (sim paroli compose'da va MediaMTX configida) MEXANIK tenglik darvozasi bilan qulflanadi — ajralib ketsa nosozlik «to'g'ri parol -> 401» shaklida chiqib, «kod buzilgan» bo'lib ko'rinardi"

requirements-completed: [CAM-09, CAM-03]

# Metrics
duration: 50min
completed: 2026-08-03
---

# Phase 3 Plan 12: Sim NVR'ning autentifikatsiyali RTSP oyog'i Summary

**Sim NVR endi O'Z manzilida (`nvr-sim:554`, `network_mode: service:nvr-sim`) MediaMTX orqali RTSP xizmat qiladi va rekvizitsiz `DESCRIBE` ni `401` bilan rad etadi; `SIM_RTSP_HOST`/`SIM_RTSP_PORT` o'lik konfiguratsiyasi olib tashlanib mexanik darvoza bilan to'sildi; `gate` zanjiridagi 31 % qayta bajarish yo'q qilindi.**

## Performance

- **Duration:** ~50 min (shundan **~12 min** — `npm run gate` ning bir yugurishi)
- **Started:** ~2026-08-03T16:37Z
- **Completed:** 2026-08-03T17:27Z
- **Tasks:** 4 (1 ta bloklovchi inson tekshiruvi + 3 ta avtomatik)
- **Files modified:** 9 (3 yaratildi, 5 o'zgartirildi, 1 o'chirildi)

## Accomplishments

- **GAP-1 ning 2-bandi yopildi:** `nvr-sim` endi `adminAccesses` e'lon qiladigan portda (554) HAQIQATAN RTSP tinglaydi. Uchidan-uchiga o'lchandi: rekvizit bilan `rtsp://admin:***@nvr-sim:554/Streaming/Channels/102` dan **44 138 baytli JPEG kadr** olindi (`runOnDemand` -> ffmpeg -> loopback publish -> tashqi o'quvchi).
- **GAP-1 ning 3-bandi yopildi:** `SIM_RTSP_HOST` va `SIM_RTSP_PORT` compose'dan chiqarildi va qaytishi ikki darajada to'sildi — nomma-nom regressiya testi va umumiy «har bir `SIM_*` kalitining iste'molchisi bor» darvozasi.
- **Rekvizit MAJBURIY:** anonim `DESCRIBE` `401` oladi, javobda `WWW-Authenticate: Basic realm="ipcam"` VA `Digest realm="ipcam", nonce=..., algorithm=MD5`. Noma'lum yo'l ham `401` oladi — server yo'lning mavjudligini autentifikatsiyadan oldin oshkor qilmaydi.
- **31 % qayta bajarish yo'q qilindi:** `gate` dan `test:tenancy` (249 s) va `test:sim` (67 s) chiqarildi; `sim:up` zanjirning boshiga o'tdi, ya'ni `test:sim` olib tashlanganda yo'qoladigan yagona haqiqiy xususiyat (sim konteynerlarining ko'tarilgan bo'lishi, T-03-10) saqlandi.
- **`sim:up` endi ishlab chiqarish `go2rtc` konteynerini ham ko'taradi** — 03-14 ning mock'siz testi unga murojaat qiladi.

## Task Commits

1. **Task 1: Yangi sim RTSP image'ining ta'minot zanjiri tekshiruvi** — kod yozilmadi (natija quyida, «Ta'minot zanjiri tekshiruvi» bo'limi)
2. **Task 2: Sim NVR o'z manzilida RTSP xizmat qiladi; o'lik konfiguratsiya olib tashlanadi** — `204992d` (feat)
3. **Task 3: `sim:up` prod go2rtc'ni ko'taradi, `gate` de-duplikatsiya qilinadi** — `523fa2a` (perf)
4. **Task 4: Ikki mexanik darvoza** — `c04e89d` (test)

## Ta'minot zanjiri tekshiruvi (Task 1) — MAJBURIY yozuv

Tekshiruv **kod yozilishidan OLDIN** bajarildi (T-03-SC).

| Savol | Javob | Manba |
|---|---|---|
| Repozitoriy arxivlanganmi? | **Yo'q** (`archived: false`, `disabled: false`) | GitHub API `/repos/bluenviron/mediamtx` |
| Litsenziya | **MIT** (`license.spdx_id: MIT`) | o'sha yerda |
| Faollik | 19 711 yulduz; oxirgi push **2026-08-03T16:33:21Z** (bugun) | o'sha yerda |
| Oxirgi release | **v1.19.3**, 2026-07-23T21:58:00Z, `prerelease: false` — 11 kunlik, 6 oy chegarasidan ancha yangi | GitHub API `/releases/latest` |
| Tanlangan teg | **`1.19.3-ffmpeg`** (Docker Hub `last_updated: 2026-07-23T22:04:11Z`) | Docker Hub v2 tags API |
| Digest | **`sha256:e8eda6a884bbb2eaebf0c0454200ddc8087f428e091bae10d20e330a08558778`** | `docker pull` chiqishi VA `docker image inspect --format '{{index .RepoDigests 0}}'` — ikkalasi mos |
| Doira | FAQAT `profiles: ["sim"]`; profilsiz `docker compose up` uni umuman ko'rmaydi; prodga hech qachon chiqmaydi | `compose.yaml` |

`compose.yaml` da image **digest bilan** yozilgan (`bluenviron/mediamtx:1.19.3-ffmpeg@sha256:e8eda…`), teg bilan emas.

Image'ning kuzatilgan xususiyatlari (`docker run --entrypoint sh`): Alpine Linux **3.24.1**, `/usr/bin/nc` (healthcheck uchun), `ffmpeg 8.1.2` + `libx264` + `lavfi testsrc2`, `uid=0(root)` — 554 imtiyozli portini bog'lash uchun `cap_add: [NET_BIND_SERVICE]` **kerak bo'lmadi** (rejada shartli ravishda ko'rsatilgan edi).

## Files Created/Modified

- `ops/mediamtx/mediamtx.yml` **(yangi, 172 qator)** — sim NVR'ning RTSP oyog'i. `rtspAddress: :554`; `authMethod: internal` + uch yozuvli `authInternalUsers` (anonim = huquqsiz, `admin` = faqat `read`, loopback anonim = faqat `publish`); `rtmp/hls/webrtc/srt/moq/api/metrics/pprof/playback` — hammasi `false`; bitta regex yo'l `"~^Streaming/Channels/[0-9]+$"` + `runOnDemand` ffmpeg.
- `compose.yaml` — `go2rtc-sim` o'rniga `nvr-sim-rtsp`; `network_mode: "service:nvr-sim"`; `SIM_RTSP_HOST`/`SIM_RTSP_PORT` o'chirildi (sababi butun-qator izohda); profil izohi va `go2rtc` healthcheck izohidagi havolalar yangilandi.
- `package.json` — `sim:up`/`sim:down` uchta konteynerni boshqaradi; `gate` de-duplikatsiya qilindi.
- `tests/integration/test_rtsp_source.py` **(yangi, 180 qator)** — xom TCP `DESCRIBE`, 3 test.
- `tests/unit/test_compose_sim_env.py` **(yangi, 227 qator)** — o'lik `SIM_*` darvozasi, 4 test.
- `ops/go2rtc/go2rtc.yaml` — 6-qatordagi `go2rtc.sim.yaml` havolasi `ops/mediamtx/mediamtx.yml` ga ko'chdi (prod'da `exec:` yo'qligining SABABI saqlandi).
- `ops/go2rtc/go2rtc.sim.yaml` **(o'chirildi)**.
- `tests/fixtures/nvr_sim.py` — `SIM_MISSING_HINT` yangi xizmat nomiga moslandi.
- `ops/docs/nvr-onboarding.md` — «sim RTSP tinglamaydi» qatori endi yolg'on; sessiya limiti hamon modellanmagani aniq yozildi.

## S1 sabotaji — ANIQ natija

**O'zgartirish:** `ops/mediamtx/mediamtx.yml` dagi birinchi yozuvga (anonim, har qanday IP) vaqtincha `permissions: [- action: read]` berildi; `docker compose --profile sim restart nvr-sim-rtsp`.

**QIZARDI (aynan 2 ta, ikkalasi ham `401` assertida):**

| Test | Assert | Kuzatilgan |
|---|---|---|
| `test_rtsp_source.py::test_anonymous_describe_is_rejected` | `assert "401" in status_line.split()` | `AssertionError: rekvizitsiz DESCRIBE 401 OLMADI: 'RTSP/1.0 200 OK'` |
| `test_rtsp_source.py::test_unknown_channel_also_requires_credentials` | `assert "401" in status_line.split()` | `AssertionError: noma'lum yo'l uchun javob 401 EMAS: 'RTSP/1.0 200 OK'` |

**YASHIL QOLDI:**

| To'plam | Natija |
|---|---|
| `test_rtsp_source.py::test_rtsp_source_listens_on_the_advertised_port` | ✅ — **ataylab**: u faqat «554 da RTSP gapiradigan server bormi» deydi, va sabotaj ostida bu hamon rost |
| `tests/unit/test_compose_sim_env.py` (4 test) | ✅ 4 passed |
| Mavjud sim to'plami (`-m "sim and not slow"`, yangi fayl chiqarilgan) | ✅ **70 passed, 451 deselected in 53.09 s** |

**Tiklash:** `git checkout -- ops/mediamtx/mediamtx.yml` -> `git status --short` **toza** -> konteyner restart -> `pytest tests/unit/test_compose_sim_env.py tests/integration/test_rtsp_source.py` -> **7 passed in 5.44 s**.

⚠ **Reja «test_rtsp_source.py ning IKKALA testi ham» qizarishini kutgan edi; fayl uchta testdan iborat bo'lib chiqdi va uchinchisi ataylab yashil qoldi.** Bu chetlanish emas, o'lchov natijasi: liveness zondining vazifasi «sim ko'tarilganmi» savolini «rekvizit talab qilinadimi» savolidan AJRATISH — sabotaj aynan ikkinchisiga tegdi, birinchisiga emas.

## Media quvurining narxi — o'lchov

| O'lchov | Qiymat | Izoh |
|---|---|---|
| `npm run test:sim` (yangi testlardan OLDIN, konteynerlar ko'tarilgan) | **60 s** | 70 test |
| `npm run test:sim` (yangi 3 test bilan) | **99 s** va **77 s** (ikki yugurish) | 73 test |
| Rekvizit bilan birinchi kadr | ~2 s | `runOnDemand` ffmpeg ishga tushishi + publish + o'qish; natija 44 138 baytli JPEG |
| `nvr-sim-rtsp` `healthy` bo'lguncha | < 5 s | `nc -z 127.0.0.1 554`, `interval: 5s` |
| `npm run lint` | 14 s | ruff + `ruff format --check` + mypy: `All checks passed`, `196 files already formatted`, `no issues found in 191 source files` |

**Media quvurining sof narxi kichik, chunki u LAZY:** `runOnDemand` ffmpeg faqat
birinchi tomoshabin ulanganda ishga tushadi va oxirgisi ketgach 15 soniyada
yopiladi. Yangi uchta testning ikkitasi umuman oqim ochmaydi — ular `401` da
to'xtaydi, ya'ni ffmpeg ishga tushmaydi ham. `test:sim` ning 60 s -> 77–99 s
o'sishi asosan **o'lchov shovqini**: ikki yugurish orasidagi farq (22 s) yangi
testlar qo'shgan ishdan (3 test, har biri < 1 s) ancha katta.

### `npm run gate` — O'LCHANDI

| O'lchov | Qiymat |
|---|---|
| **`npm run gate`** | **exit 0, 716 s** |
| 03-11 ning bazaviy o'lchovi (eski zanjir) | 1000 / 994 / 983 s |
| Farq | **~270 s tejaldi (~27 %)** — bashorat 316 s / 31 % edi, farq media quvurining narxi va o'lchov shovqini |
| Chegara | **1200 s — KO'TARILMADI** (reja shuni talab qiladi; qayta o'lchov 03-14 da) |

**Zanjirning yangi sanog'i (hammasi o'lchandi, `gate` ichida):**

| Qadam | Natija |
|---|---|
| `npm run sim:up` | uchala konteyner `healthy` |
| `npm run lint` | `All checks passed!` · `196 files already formatted` · `no issues found in 191 source files` |
| `npm run test` (pytest) | **1464 test yig'ildi** (03-11 da 1457 edi: +3 sim, +4 unit), hammasi o'tdi |
| `i18n:check` | `576 kalit × 3 til — kalit va ICU parity to'liq`, drift yo'q |
| frontend vitest | **246 passed (20 fayl)** |
| `typecheck` / `lint` / `build` | uchalasi ham o'tdi (`next build`: `✓ Compiled successfully`) |

Mustaqil yorliqlar (zanjirdan chiqarilgan, lekin hamon ishlaydi):
`npm run test:tenancy` — **exit 0**; `npm run test:sim` — **exit 0**.

⚠ **716 s soni PARALLEL YUK ostida olindi** (03-13 ijrochisining konteynerlari,
asosiy `sbozor` steki va bog'liq bo'lmagan boshqa loyiha bir vaqtda ishlayotgan
edi). Ya'ni u pessimistik tomonga qiyshaygan — chegarani qayta belgilash uchun
EMAS, faqat «de-duplikatsiya ishladi» faktini tasdiqlash uchun.

## Decisions Made

Yuqoridagi `key-decisions` frontmatteriga qarang. Qisqacha eng muhimlari:

1. **`network_mode: service:nvr-sim`** — topologiyani real qurilmaga o'xshatish; bu GAP-1 ning ildizini yopadi, alomatini emas.
2. **Anonim o'qish rad etiladi** — 03-13 va 03-14 ning o'lchanuvchanligining SHARTI.
3. **`SIM_RTSP_HOST` iste'mol qilinmadi, o'chirildi** — noto'g'ri modelni tirik qilish o'lik kalitdan yomonroq.
4. **Digest bilan qadash** — teg ko'chirilishi mumkin.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `moq: false` qo'shildi**
- **Found during:** Task 2
- **Issue:** MediaMTX 1.19.3 ning mos yozuvlar konfiguratsiyasida **`moq: true`** (Media-over-QUIC, `:8892` HTTP2/HTTP3) — rejaning o'chiriladigan serverlar ro'yxati (`rtmp`, `hls`, `webrtc`, `srt`, `api`, `metrics`, `pprof`, `playback`) bu serverdan oldingi versiyalarga tayanadi. Uni yoqiq qoldirish T-03-83 ning «hammasi o'chiriladi» talabini buzardi va `nvr-sim` ning tarmoq fazasida yana bitta tinglovchi qoldirardi.
- **Fix:** `moq: false` qo'shildi.
- **Verification:** konteyner jurnali faqat bitta serverni e'lon qiladi: `[RTSP] started with listeners on :554 (TCP/RTSP), :8000 (UDP/RTP), :8001 (UDP/RTCP)`.
- **Committed in:** `204992d`

**2. [Rule 2 - Missing Critical] `rtspAuthMethods: [basic, digest]`**
- **Found during:** Task 2
- **Issue:** MediaMTX ning standarti `[basic]`. Real Hikvision NVR RTSP'da **Digest** so'raydi. Sim faqat Basic qabul qilsa, «rekvizit uzatiladi» da'vosi prodda BOSHQACHA xulq ustida yashil bo'lardi — ya'ni 03-13 sim'da ishlab, dalada yiqilishi mumkin edi.
- **Fix:** ikkala sxema ham e'lon qilinadi.
- **Verification:** `401` javobida ikkala `WWW-Authenticate` sarlavhasi ham kuzatildi.
- **Committed in:** `204992d`

**3. [Rule 2 - Missing Critical] `multicast` transporti olib tashlandi**
- **Found during:** Task 2
- **Issue:** `rtspTransports` ning standarti `[udp, multicast, tcp]` — multicast bu yerda hech kimga kerak emas, lekin server multicast guruhlariga qo'shilardi.
- **Fix:** `rtspTransports: [tcp, udp]`. `udp` ATAYIN saqlandi: 03-13 parallel yozilyapti va uning go2rtc mijozi qaysi transportni tanlashi men tekshira olmaydigan fakt — transportni cheklash uni jimgina buzishi mumkin edi.
- **Verification:** jurnalda multicast tinglovchisi yo'q (yuqoridagi qator).
- **Committed in:** `204992d`

**4. [Rule 2 - Missing Critical] Sim parolining ikki manbadagi tengligi darvozasi**
- **Found during:** Task 4
- **Issue:** Reja `ops/mediamtx/mediamtx.yml` dagi parol `compose.yaml` dagi `SIM_PASSWORD` standarti bilan bir xil bo'lishini TALAB qildi, lekin buni ushlab turadigan hech qanday mexanizm bermadi. Ajralib ketsa nosozlik shakli o'ta yomon: kashfiyot TO'G'RI parolni yozadi, go2rtc uni to'g'ri uzatadi, server esa baribir `401` beradi — va sabab «kod buzilgan» bo'lib ko'rinadi.
- **Fix:** `test_compose_sim_env.py::test_sim_password_matches_between_compose_and_rtsp_config` — compose'dagi HAMMA `SIM_PASSWORD` standarti bir xil ekanini va MediaMTX configida AYNAN bitta qiymatli `pass:` borligini (anonim yozuvlarniki bo'sh bo'lishi shart) tekshiradi.
- **Verification:** 4 test yig'iladi va o'tadi.
- **Committed in:** `c04e89d`

**5. [Rule 3 - Blocking] Tekshiruv izolyatsiyalangan compose loyihasida bajarildi**
- **Found during:** Task 2
- **Issue:** `compose.yaml` `name: sbozor` ni qadalgan holda saqlaydi, ya'ni parallel ishlayotgan 03-13 ijrochisi AYNAN bir Docker loyihasini bo'lishadi. Uning `docker compose --profile sim up` i (uning `compose.yaml` ida hamon `go2rtc-sim` bor) `nvr-sim` ni QAYTA YARATARDI va `nvr-sim-rtsp` ulangan tarmoq fazasi yo'q bo'lardi — mening o'lchovlarim tasodifiy yiqilardi yoki, yomoni, noto'g'ri natija berardi.
- **Fix:** barcha tekshiruv buyruqlari `COMPOSE_PROJECT_NAME=sbozor0312` bilan bajarildi. **Repoda hech nima o'zgarmadi** — bu faqat ijro muhitining o'zgaruvchisi. Xost portlari to'qnashmaydi: ishlatilgan uchala konteynerning hech biri port publish qilmaydi.
- **Verification:** `docker compose --profile sim ps` -> `go2rtc healthy`, `nvr-sim healthy`, `nvr-sim-rtsp healthy` (izolyatsiyalangan loyihada).
- **Committed in:** — (repo o'zgarishi yo'q)

### Rejaning ichki ziddiyatlari (bajarildi, lekin harfma-harf emas)

**A. Task 2 ning `npm run sim:up` mezoni Task 3 gacha bajarilmaydi.** Task 2 tugaganda `sim:up` hamon `go2rtc-sim` ni nomlab turardi (uni Task 3 o'zgartiradi). Task 2 ekvivalent xom buyruq bilan tekshirildi — `docker compose --profile sim up -d nvr-sim nvr-sim-rtsp --wait` (exit 0, ikkala konteyner `healthy`) — va `npm run sim:up` Task 3 dan keyin qayta bajarildi (uchala konteyner `healthy`).

**B. Task 4 ning sabotaj kutilmasi «ikkala test».** Fayl uchta testdan iborat; ikkitasi qizardi, uchinchisi ataylab yashil qoldi (yuqorida batafsil). Niyat — «anonim o'qish ochilsa o'lchov qizaradi» — to'liq bajarildi.

---

**Total deviations:** 5 auto-fixed (4 missing critical, 1 blocking) + 2 ta rejaning ichki ziddiyati hal qilindi
**Impact on plan:** Barcha auto-fix'lar rejaning O'Z threat-model'i (T-03-83) va O'Z talablari (parol tengligi) uchun zarur. Doira kengaymadi: bironta yangi xizmat, endpoint yoki bog'liqlik qo'shilmadi.

## Issues Encountered

- **`go2rtc` sleshli oqim nomini qo'llay oladimi?** — reja «ijro paytida aniqlansa ayting» dedi. **Ijro davomida buni tasdiqlaydigan hujjatlashtirilgan dalil topilmadi**, ya'ni rejaning MediaMTX qarori kuchida qoladi. Bu masala qayta ochilishi mumkin bo'lgan yagona shart: go2rtc hujjatida oqim nomi <-> URL yo'li moslashuvi aniq yozilsa.
- **`npm run gate` ning o'lchovi PARALLEL YUK ostida olindi.** Mashinada bir vaqtning o'zida 03-13 ijrochisining konteynerlari, asosiy `sbozor` steki va bog'liq bo'lmagan boshqa loyiha ishlab turardi. Shu sababli quyidagi son 03-11 ning ketma-ket o'lchovi (1000/994/983 s) bilan TO'G'RIDAN-TO'G'RI solishtirilmaydi va u chegarani qayta belgilash uchun ishlatilmasligi kerak — chegara 03-14 da bir marta, toza sharoitda o'lchanadi (reja aynan shuni talab qiladi).

## Known Stubs

Yo'q. Bu rejadagi hamma narsa ishlaydigan holatda: RTSP server real oqim beradi (o'lchandi — 44 KB JPEG), darvozalar real fayllarni o'qiydi, sabotaj ikkalasini ham qizartirdi.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new-listener | `ops/mediamtx/mediamtx.yml` | RTSP serveri UDP transportini qo'llagani uchun `:8000` (RTP) va `:8001` (RTCP) tinglovchilarini ham ochadi. T-03-83 «qo'shimcha SERVERLAR» ni sanaydi va bu ikkisi RTSP serverining O'Z qismi, alohida server emas — lekin ular baribir YANGI tinglovchi. Ular `nvr-sim` ning netns'ida yashaydi, xost portiga publish QILINMAGAN va faqat compose tarmog'idan ko'rinadi. `udp` ni olib tashlash ularni yopadi; bu 03-13 ning go2rtc mijozi qaysi transportni tanlashi aniq bo'lgach qayta ko'rib chiqilsin. |

## Doiradan tashqarida topilgan band (`deferred-items.md` ga YOZILMADI — sabab quyida)

**`tests/unit/test_go2rtc_client.py:284`** — `test_production_go2rtc_config_has_no_exec_source` ning docstringi hamon «`go2rtc.sim.yaml` da `exec:` BOR» deydi, holbuki fayl endi mavjud emas (uning o'rnini `ops/mediamtx/mediamtx.yml` ning `runOnDemand` i egalladi). Test **yiqilmaydi** — u prod configni o'qiydi va assert'i to'g'ri; muammo faqat docstringda.

**Nega tuzatilmadi:** bu fayl `03-13` ning fayllar to'plamiga kiradi (`app/services/go2rtc.py` ning testlari) va bu to'lqinda parallel tahrirlanmoqda. **`deferred-items.md` ga ham yozilmadi**, chunki u ikkala ijrochi uchun umumiy fayl va oxiriga qo'shish merge konfliktiga olib kelardi. Egasi: `03-13` yoki `03-14`.

## User Setup Required

Yo'q — tashqi xizmat sozlamasi talab qilinmaydi. `bluenviron/mediamtx:1.19.3-ffmpeg` public Docker Hub image'i; birinchi `npm run sim:up` uni o'zi tortib oladi.

## Next Phase Readiness

**03-13 (rekvizit uzatish) uchun tayyor:**
- `rtsp://nvr-sim:554/Streaming/Channels/<{ch}01|{ch}02>` — mahsulot `rtsp_url()` hosil qiladigan AYNAN o'sha shakl, mavjud va ishlaydi;
- rekvizit **majburiy** (`admin` / `Sim12345`), ya'ni 03-13 ning ishi o'lchanadi va uni tashlab yuborish testni qizartiradi;
- `Basic` ham, `Digest` ham qabul qilinadi — go2rtc qaysi birini tanlasa ham ishlaydi.

**03-14 (uchidan-uchiga o'lchov) uchun tayyor:**
- `npm run sim:up` endi `go2rtc` (prod konteyner) ni ham ko'taradi — mock'siz test murojaat qiladigan xizmat ishlab turadi;
- `gate` zanjiri de-duplikatsiya qilingan, ya'ni 03-14 ning o'lchovi qayta bajarishsiz sof qiymat beradi;
- ⚠ **1200 s chegarasi TOZA sharoitda qayta o'lchanishi shart** — bu rejadagi o'lchov parallel yuk ostida olingan.

**Ochiq bandlar:**
- Sim RTSP sessiya limitini (D-05) modellamaydi — `ops/docs/nvr-onboarding.md` da ochiq yozilgan;
- `tests/unit/test_go2rtc_client.py:284` docstringi eskirgan (yuqorida).

## Self-Check: PASSED

**Fayllar** (`ls -1`): `ops/mediamtx/mediamtx.yml`, `tests/integration/test_rtsp_source.py`,
`tests/unit/test_compose_sim_env.py`, `compose.yaml`, `package.json`,
`ops/go2rtc/go2rtc.yaml`, `ops/docs/nvr-onboarding.md`, `tests/fixtures/nvr_sim.py`,
`03-12-SUMMARY.md` — hammasi mavjud. `ops/go2rtc/` da endi faqat `go2rtc.yaml`
qoldi (`go2rtc.sim.yaml` o'chirilgan).

**Commitlar** (`git log --oneline --all`): `204992d`, `523fa2a`, `c04e89d` — uchalasi ham topildi.

**Reja mezonlari (`must_haves`):** `mediamtx.yml` `authInternal` ni o'z ichiga oladi ✓;
`test_rtsp_source.py` 180 qator (≥60) ✓; `test_compose_sim_env.py` 227 qator (≥50) ✓;
`compose.yaml` da `network_mode: "service:nvr-sim"` ✓; `package.json` da `sim:up … go2rtc` ✓.

**Task 2 ning grep mezonlari:** `SIM_RTSP_HOST` (izohsiz) = **0** ✓ ·
`SIM_RTSP_PORT:` (izohsiz) = **0** ✓ · `SIM_RTSP_PORT_ADVERTISED` = **1** ✓ ·
`sha256:` = **1** ✓ · `go2rtc.sim.yaml` havolasi = **0** ✓ ·
prod `exec:` (izohsiz) = **0** ✓ · `service:nvr-sim` rendered configda = **1** ✓.

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
