---
phase: 04-snapshot-pipeline
plan: 02
subsystem: infra
tags: [fixtures, pillow, nvr-sim, mediamtx, isapi, i18n, gates, wave-0, cam-06]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 02
    provides: "`nvr-sim` konteyneri, `/__sim__` control-plane, `SimState`, `sim` markeri va fixture'lari"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 12
    provides: "`nvr-sim-rtsp` (MediaMTX, `network_mode: service:nvr-sim`), `ops/mediamtx/mediamtx.yml`, `test_compose_sim_env.py`"
  - phase: 04-snapshot-pipeline
    plan: 01
    provides: "⚠ `Pillow` `services/core-api/pyproject.toml` da — `tests/fixtures/frames.py` uni TALAB QILADI (quyida «Deviations» 1-band)"
provides:
  - "`tests/fixtures/frames.py` — sintetik JPEG generatori: `frame_bytes(mean=, stddev=, saturation=)`, `truncate()`, `HTML_ERROR_PAGE`. Chegara qiymatlari FIZIK XUSUSIYAT bilan yasaladi, detektor verdikti bilan EMAS"
  - "`services/nvr-sim/sim/frames.py` — `FRAME_MODES` (`ok`/`truncated`/`html`/`empty`) va `frame_bytes_for_mode()`; sim `Pillow` ga bog'lanmaydi"
  - "`SimState.frame_mode` — buzuq kadr BUYURTMA bo'yicha; noma'lum QIYMAT rad etiladi, `reset` `ok` ga qaytaradi"
  - "ISAPI `GET /Streaming/channels/{ch}/picture` — baytlar `frame_mode` dan; shakl buzuq -> 400, kanal yo'q -> 404; RTSP sessiyasi DA'VO QILINMAYDI (D-07)"
  - "`ops/mediamtx/mediamtx.yml` — uchta sifat-ssenariy yo'li (qorong'i / kulrang / past-kontrastli) umumiy regexdan OLDIN, yangi rekvizitsiz"
  - "`frontend/scripts/snapshot-copy.test.mjs` — G-1, G-2, G-3, G-4, G-10 darvozalari qamrov chegarasi bilan"
  - "`nav.snapshots` uch tilda + `NAV_ITEMS` da `/snapshots` yozuvi (`camera_view`)"
  - "`HEDGED_KEYS` / `HEDGED_NAMESPACES` — hedging invarianti IKKALA xato reyestriga qo'llanadi"
affects: [04-03, 04-04, 04-05, 04-08, 04-09, 04-10]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Sinov ma'lumoti FIZIK XUSUSIYAT bilan parametrlanadi (`mean`/`stddev`/`saturation`), detektor CHEGARASI bilan emas — chegara bilan nomlangan fixture testni o'z farazining aks-sadosiga aylantiradi"
    - "Determinizm ALOHIDA test bilan o'lchanadi: u tolerans testlaridan mustaqil bo'lishi shart, aks holda urug' yo'qolganda faqat flaky natija qoladi va sabab topilmaydi"
    - "Tolerans MODULDA yashaydi (`MEAN_TOLERANCE`), testda emas — u generatorning E'LON QILINGAN va'dasi, testning qulayligi emas; kuzatilgan xato va e'lon qilingan kontrakt AJRATIB yoziladi"
    - "Nishonga tushib bo'lmaydigan argument QISILMAYDI (`clamp`), RAD ETILADI — jimgina qisish chaqiruvchiga so'ralmagan ma'lumot berardi"
    - "Simulyatorda IKKI MUSTAQIL O'LCHAM: `mode` (ulanish/auth) va `frame_mode` (javob baytlari). Bitta enumga yig'ish «noto'g'ri parol VA buzuq kadr» kombinatsiyasini ifodalab bo'lmas qilardi"
    - "Reyestr o'z MA'LUMOTI bilan bitta modulda yashaydi (`FRAME_MODES` + baytlar `sim/frames.py` da) — yangi rejim qo'shilganda ular ajralib keta olmaydi"
    - "Yo'llar TARTIBI muhim bo'lgan konfiguratsiyada tartib MEXANIK darvoza bilan qulflanadi; darvoza faylni MATN sifatida o'qiydi va izohda umumiy naqsh TAKRORLANMAYDI (aks holda yolg'on-qizil)"
    - "Shartli darvoza (nishon hali mavjud emas) SABABNI CHOP ETADI — jimgina o'tish «darvoza bor» degan yolg'on da'voni qoldirardi"
    - "Darvoza spetsifikatsiyaning NIYATINI bajaradi, LITERAL naqshini emas: naqsh o'lchov bilan tekshiriladi va ishlamasa TUZATILIB, farq sabab bilan yoziladi"

key-files:
  created:
    - tests/fixtures/frames.py
    - tests/unit/test_frame_fixtures.py
    - services/nvr-sim/sim/frames.py
    - frontend/scripts/snapshot-copy.test.mjs
  modified:
    - services/nvr-sim/sim/state.py
    - services/nvr-sim/sim/isapi.py
    - ops/mediamtx/mediamtx.yml
    - tests/unit/test_compose_sim_env.py
    - tests/integration/test_nvr_sim.py
    - frontend/src/components/shell/app-shell.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/scripts/gen-cyrillic.test.mjs
    - frontend/scripts/error-codes.test.mjs
    - frontend/scripts/nvr-copy.test.mjs
  deleted: []

key-decisions:
  - "Kadr VERTIKAL polosalardan quriladi va polosa kengligi AYNAN 8 — JPEG ning DCT to'riga tushadi, ya'ni har blok bir xil rangli bo'lib faqat DC koeffitsiyenti qoladi va kvantlash amalda yo'qotish keltirmaydi. Nishon TASODIFGA tayanmaydi: ikki darajali muvozanatli taqsimotning `mean`/`stddev` i arifmetik natija"
  - "Kenglik 8 ga karrali bo'lishi SHART va aks holda `ValueError`. O'lchandi: `width=100, mean=140` -> 134,6 o'qildi, ya'ni e'lon qilingan ±2 toleransidan tashqarida. Jimgina qisish o'rniga rad etish tanlandi"
  - "To'yinganlik kiritilganda YORUG'LIK SAQLANADI (`M` teskari hisoblanadi). Aks holda `mean` nishoni to'yinganlik bilan birga suzib ketardi va ikki fizik xususiyat bir-biriga bog'lanib qolardi — `ir_night` (monoxrom) va `day` (rangli) shoxlari bir xil yorug'likda taqqoslanmasdi"
  - "Sim `Pillow` ga BOG'LANMAYDI: `sim/frames.py` da bitta yaroqli JPEG base64 konstanta va qolgan uch rejim undan hosila. Bu YAGONA ruxsat etilgan takrorlanish va uning sababi ochiq — sim qurilmani modellaydi, qurilma esa test kodini import qilmaydi (T-04-SC: yangi paket yo'q)"
  - "`SIM_MODES` TEGILMADI. `frame_mode` — ikkinchi o'lcham; 04-04 ning retry siyosati `401` (qayta urinish ZARARLI, D-03) va buzuq kadr (qayta urinish TO'G'RI) ni ajratishi shart, bitta enumda bu kombinatsiya ifodalanmasdi"
  - "`html` va `empty` rejimlari `200` status bilan keladi (T-04-10). Bu ENG AYYOR shakl: HTTP darajasida hammasi joyida, tanada esa kadr o'rniga sahifa yoki hech nima. `Content-Type` ga ishonadigan filtr ularni yaroqli deb qabul qilardi"
  - "ISAPI `/picture` RTSP sessiyasini DA'VO QILMAYDI (D-07) — 3-fazadagi `_claim_stream` chaqiruvi bu yo'ldan olib tashlandi. Sim oqim da'vosini sanasa, o'z hujjatining TESKARISINI modellagan bo'lardi (Deviations 2-band)"
  - "`/picture` da SHAKL va MAVJUDLIK ikki xil kod oladi: shakl buzuq -> 400, shakl to'g'ri lekin kanal yo'q -> 404. Ularni bir xil kodga yig'ish 04-04 ning xato taksonomiyasini ko'rlantirardi — «kod noto'g'ri URL quryapti» retry bilan HECH QACHON tuzalmaydi"
  - "MediaMTX sifat yo'llari kanal 90/91/92 da — `SIM_CHANNEL_COUNT` diapazonidan tashqarida, ya'ni kashfiyot ular uchun kamera yaratmaydi va sifat-ssenariylari haqiqiy kameralar bilan aralashmaydi"
  - "Yo'llar tartibi EMPIRIK tasdiqlandi, hujjatga ishonilmadi: 9001 -> YAVG 16 (YLOW=YHIGH=16), 9101 -> 126 (YLOW=YHIGH=126), 9201 -> 63 (YLOW=55, YHIGH=71), 101 -> 126 (YLOW=41, YHIGH=210). Har uchala maxsus yo'l umumiy yo'ldan FARQ QILADI, ya'ni MediaMTX e'lon tartibini haqiqatan hurmat qiladi"
  - "W0-F7 darvozani UMUMLASHTIRADI, «tuzatmaydi». O'lchandi: `nvr-copy.test.mjs` `cameras.errorCause` ni qattiq qadagan edi, ya'ni `snapshots.*` qo'shilganda darvoza QIZARMASDI — u shunchaki KO'RMASDI. Haqiqiy xavf jim qamrovsizlik edi"
  - "`ъ` darvozasining mexanikasi TUZATILDI (spetsifikatsiyaning niyati saqlandi): haqiqiy defekt `НВРъга` SOF KIRILL (`Р` = U+0420), ya'ni `/[A-Za-z]ъ/` uni hech qachon ushlamaydi va `/[а-яёқғҳўъ]ъ/i` uni TO'G'RI deb belgilaydi. Ishlaydigan farq — `ъ` dan oldingi IKKI YOKI UNDAN KO'P BOSH HARF"
  - "Tekshiruv IZOLYATSIYALANGAN compose loyihasida bajarildi (`-p sbozor_w0402`): `compose.yaml` `name: sbozor` ni qadalgan holda saqlaydi va parallel ishlayotgan 04-01 ijrochisi AYNAN shu loyihani bo'lishardi (03-12 dagi bilan bir xil qaror)"

patterns-established:
  - "Pattern: fixture va test nomlarida VERDIKT so'zi (`dark`, `blank`, `corrupt`, `rejected`) taqiqlanadi va taqiq REGEX bilan mexanik tekshiriladi — nomlash konventsiyasi darvozaga aylanadi"
  - "Pattern: sabotaj QIZARADIGAN to'plamni ham, YASHIL QOLADIGAN to'plamni ham nomlaydi — «nima qizarmadi» ham o'lchov natijasi (bu yerda: determinizm qizardi, to'rtala tolerans testi yashil qoldi)"
  - "Pattern: konfiguratsiyaning kuzatiladigan xulqi HUJJATDAN emas, O'LCHOVDAN olinadi (`ffmpeg signalstats` bilan har yo'lning YAVG/YLOW/YHIGH i)"
  - "Pattern: spetsifikatsiyaning naqshi ijro paytida O'LCHANADI; ishlamasa niyat bajariladi, mexanika tuzatiladi va farq sabab bilan kodda qoladi"
  - "Pattern: shartli darvoza `console.log` bilan sababni chop etadi — «darvoza bor» da'vosi shu bilan aniq chegaralanadi"

requirements-completed: [CAM-04, CAM-05, CAM-06, FOUND-06]

# Metrics
duration: 75min
completed: 2026-08-04
---

# Phase 4 Plan 02: Sintetik kadr, sim `frame_mode` va Wave 0 frontend darvozalari Summary

**Sifat filtri endi DARVOZA bo'la oladi: chegara qiymatlari fizik xususiyat bilan (`mean=8, stddev=2`) determinstik yasaladi, simulyator esa buzuq, kesilgan, bo'sh va HTML javoblarni buyurtma bilan beradi — MediaMTX bera olmaydigan aynan o'sha to'rt shakl; frontend tomonida `/snapshots` navigatsiyaga chiqdi va beshta yangi mexanik darvoza (G-1…G-4, G-10) hamda ikki namespace ustida ishlaydigan hedging darvozasi qo'yildi.**

## Performance

- **Duration:** ~75 min
- **Tasks:** 3 (hammasi avtomatik, checkpoint yo'q)
- **Files:** 17 (4 yaratildi, 13 o'zgartirildi) — 2212 qator qo'shildi, 50 o'chirildi

## Accomplishments

- **W0-9 — CAM-06 ning isboti endi mavjud.** `frame_bytes(mean=8, stddev=2)` dan `PIL.ImageStat` **aynan 8,00 / 2,00** o'qiydi (e'lon qilingan tolerans ±2 / ±1,5). Generator sifat filtrini UMUMAN import qilmaydi va uning chegaralarini bilmaydi — ya'ni 04-04 dagi filtr testi o'z farazini o'ziga tasdiqlata olmaydi.
- **W0-10 — buzuq baytlar sim boshqaruvida.** `POST /__sim__/state {"frame_mode": …}` to'rt shaklni beradi: to'liq JPEG (2927 bayt), EOI'siz kesilgan (1756 bayt), `text/html` xato sahifasi (150 bayt, `200` bilan) va bo'sh tana (`image/jpeg` sarlavhasi bilan). **Noma'lum qiymat rad etiladi** — «rejimni o'rnatdim deb o'ylab, yaroqli kadr ustida ishlash» yo'li yopiq.
- **MediaMTX sifat yo'llari O'LCHANDI, taxmin qilinmadi.** `ffmpeg signalstats` bilan RTSP ustidan: kanal 9001 -> `YAVG=16, YLOW=YHIGH=16` (qorong'i, tuzilmasiz), 9101 -> `126, YLOW=YHIGH=126` (yorug'lik NORMAL, tuzilma YO'Q — D-14 ning ikkinchi sharti), 9201 -> `63, YLOW=55, YHIGH=71` (past kontrastli, LEKIN tuzilmali — qish-tong kadrining analogi), umumiy yo'l 101 -> `126, YLOW=41, YHIGH=210`. Uchalasi ham umumiy yo'ldan farq qiladi, ya'ni **tartib haqiqatan hurmat qilinadi**.
- **W0-F1…F7 — beshta yangi darvoza va bitta umumlashtirish.** G-4 (`frontend/src` da ombor yuzasi) bugundan **HAQIQIY**: 122 fayl skanerlanadi (quyi chegara 40). G-1/G-10/G-2/G-3 shartli — nishon hali yo'q va ular SABABNI CHOP ETADI.
- **Uchala sabotaj ANIQ natija berdi** (quyida alohida bo'lim) — har birida faqat KUTILGAN test qizardi.

## Task Commits

1. **Task 1: W0-9 — sintetik JPEG generatori** — `76c806e` (test)
2. **Task 2: W0-10 — sim `frame_mode`, ISAPI `/picture`, MediaMTX sifat yo'llari** — `413e816` (feat)
3. **Task 3: W0-F1…W0-F7 — navigatsiya va matn darvozalari** — `2e1e167` (feat)

## Sabotajlar — ANIQ natija

| # | Sabotaj | Kutilgan | O'LCHANGAN |
|---|---------|----------|------------|
| **T1** | `random.Random(_SEED)` -> global `random` moduli | determinizm testi qizaradi, tolerans testlari yashil qoladi | **`test_identical_arguments_produce_identical_bytes` YAGONA yiqilgan test** (15 dan 14 tasi yashil). Sabab aniq: to'plam o'sha bo'lgani uchun `mean`/`stddev` nishonda qoladi, faqat polosalar TARTIBI o'zgaradi |
| **T2** | `apply_patch` dagi `frame_mode` qiymat validatsiyasi olib tashlandi | «noma'lum qiymat rad etiladi» testi qizaradi, qolgan `frame_mode` testlari yashil qoladi | **`test_frame_mode_rejects_an_unknown_value` YAGONA yiqilgan test.** Javob: `200` + `"frame_mode":"corrupt"` — sim noma'lum rejimni jimgina qabul qildi |
| **T3-1** | `uz-Latn.json` ga vaqtincha `"snapshots": {"x": "Har slot uchun"}` | `snapshot-copy.test.mjs` G-1 da qizaradi, `gen-cyrillic.test.mjs` yashil qoladi | **G-1 YAGONA yiqilgan test** (9 dan 8 tasi yashil); `gen-cyrillic.test.mjs` **66/66 yashil** |
| **T3-2** | `frontend/src/lib/api-client.ts` ga `// presign` izohi | G-4 qizaradi | **G-4 YAGONA yiqilgan test**, xabarda aniq manzil: `src\lib\api-client.ts: presign` — darvoza butun `frontend/src` ni ko'rayotgani shu bilan isbotlandi |

Uchala holatda ham fayl **darhol tiklandi** va to'plam qayta yashil bo'ldi.

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest -q` (to'liq to'plam) | **1546 test, exit 0** (bazaviy 1520 -> +26) |
| 2 | `pytest tests/tenancy -q` | **412** (o'zgarmagan) |
| 3 | `pytest tests/integration -m "sim and not slow" -q` | **85 test, exit 0** |
| 4 | `ruff check . && ruff format --check . && mypy .` | exit 0 (204 fayl formatlangan, 199 fayl tiplangan) |
| 5 | `npm --prefix frontend run i18n:check` | **577 kalit × 3 til** (bazaviy 576 -> +1: `nav.snapshots`) |
| 6 | `npm --prefix frontend test` | **node 111** (bazaviy 86 -> +25), **vitest 246** (o'zgarmagan) |
| 7 | `npm --prefix frontend run typecheck && lint` | exit 0 |
| 8 | `git diff --exit-code services/core-api/app frontend/src/lib/rbac.ts frontend/package.json` | **o'zgarish yo'q** (W0-F6 va T-04-SC tasdiqlandi) |
| 9 | `pytest tests/unit/test_no_sim_branching.py -q` | exit 0 — ilova kodida sim tarmoqlanishi yo'q |

## Deviations from Plan

### 1. [Qoida 3 — bloklovchi] `Pillow` hali `pyproject.toml` da yo'q (`04-01` qo'shadi)

- **Qayerda:** Task 1 ning barcha `docker compose … pytest` mezonlari
- **Muammo:** `tests/fixtures/frames.py` `Pillow` ni talab qiladi, lekin u `services/core-api/pyproject.toml` da **hali yo'q** — uni bir to'lqinda ishlayotgan `04-01` qo'shadi. Bu reja o'sha faylga TEGA OLMAYDI (fayl to'plamlari ataylab kesishmaydi).
- **Yechim:** paket **repoga qo'shilmadi**. Tekshiruv efemер konteynerda bajarildi:
  `docker compose -p sbozor_w0402 --profile test run --rm tests sh -c "uv pip install --python /opt/venv 'pillow==12.3.0' -q && …"`.
  `--rm` tufayli o'rnatish konteyner bilan birga yo'qoladi; `pyproject.toml`, `uv.lock` va image **tegilmadi**.
- **Qoldiq xavf:** `04-01` merge bo'lgach `pytest tests/unit/test_frame_fixtures.py` **qo'shimcha buyruqsiz** ishlashi kerak. Agar `04-01` da `Pillow` qatori bo'lmasa, bu test `ModuleNotFoundError: PIL` bilan yiqiladi — **to'lqin merge'idan keyin birinchi tekshiriladigan band**.
- **Fayllar:** yo'q (repo o'zgarmadi)

### 2. [Qoida 2 — yetishmayotgan kritik xulq] ISAPI `/picture` endi RTSP sessiyasini DA'VO QILMAYDI

- **Topildi:** Task 2 da, `_streaming()` ni o'qishda
- **Muammo:** 3-fazadagi kod `/picture` yo'lida ham `_claim_stream(state)` ni chaqirardi, ya'ni sim ISAPI kadr olishni **oqim da'vosi** deb hisoblardi. Bu `04-CONTEXT.md` **D-07** ning AYNAN teskarisi: *«ISAPI `/picture` NOL RTSP sessiyasi ochadi — sessiya bosimi ostida u zaxira emas, eng XAVFSIZ usul»*. D-06/D-07 ning butun usul tanlovi shu xususiyatga tayanadi.
- **Nima uchun kritik:** 04-04/04-05 da «chegara to'lganda ham `/picture` ishlaydi» yo'li sim ustida **hech qachon yashil bo'lmasdi** va ijrochi kodni sim'ga moslashtirib, mahsulotni noto'g'ri tomonga burardi.
- **Tuzatish:** `_claim_stream` chaqiruvi `picture` shoxidan chiqarildi; oqim yo'li (`/picture` siz) **o'zgarmadi**. Yangi test ikkala tomonni ham o'lchaydi (`test_picture_claims_no_rtsp_session`): uch marta `/picture` -> `stream_claims == 0`, keyin bitta oqim so'rovi -> `stream_claims == 1` (sanagich buzilmaganining nazorati).
- **Regressiya xavfi tekshirildi:** `/picture` ga tayanadigan birorta mavjud test **yo'q edi**; `test_stream_limit_reject_shape` va `test_stream_limit_silent_shape` oqim yo'lini ishlatadi va ikkalasi ham yashil.
- **Fayllar:** `services/nvr-sim/sim/isapi.py`, `tests/integration/test_nvr_sim.py` — **commit** `413e816`

### 3. [O'z-o'ziga zid mezon] `pass:` qatorlarini sanash naqshi ishlamaydi

- **Qayerda:** Task 2 ning mezoni
  `assert len(re.findall(r'^\s*pass:\s*\S+', t, re.M)) == 1`
- **O'lchandi:** bu naqsh **o'zgartirilMAGAN** `mediamtx.yml` da ham **3** natija beradi, ya'ni mezon hech qachon o'ta olmasdi. Sabab `\s` ning yangi qatorni ham yeyishi: bo'sh `pass:` dan keyingi `ips:` qatori qiymat deb olinadi. Bu **allaqachon ma'lum** xato — `test_compose_sim_env.py:210-217` aynan shu sababni izohda yozib, `[ \t]` ni ishlatadi.
- **Yechim:** mezonning NIYATI bajarildi («yangi rekvizit qo'shilmagan»), mexanikasi loyihaning o'z, to'g'ri naqshidan olindi. Yangi test **ikki shartni** tekshiradi: `authInternalUsers` yozuvlari **aynan 3** va qiymatli `pass:` qatorlari **aynan 1**.
- **Fayllar:** `tests/unit/test_compose_sim_env.py` — **commit** `413e816`

### 4. [O'z-o'ziga zid mezon] Qoida 6 ning `ъ` naqshlari chiqish ustida ishlamaydi

- **Qayerda:** Task 3 / W0-F3 ning 4-bandi va `04-UI-SPEC.md` §11.11 Qoida 6:
  `DEFEKT := /[A-Za-z]ъ/`, `TO'G'RI := /[а-яёқғҳўъ]ъ/i`
- **O'lchandi:** `transliterate("NVR'ga ulanmadi")` -> `"НВРъга уланмади"`; kod nuqtalari `Н=U+41D В=U+412 Р=U+420 ъ=U+44A`. `Р` — **kirill Er**, lotin `R` emas: transliterator akronimni allaqachon kirillga o'girib bo'lgan va apostrof faqat SHUNDAN KEYIN `ъ` ga aylangan. Natija: `/[A-Za-z]ъ/` defektni **hech qachon ushlamaydi** (o'lchandi: `false`), `/[а-яёқғҳўъ]ъ/i` esa uni **TO'G'RI deb belgilaydi** (o'lchandi: `true`).
- **Yechim:** niyat SAQLANDI (tutuq belgisi defektdan ajratiladi), mexanika tuzatildi — ishlaydigan farq `ъ` dan oldingi **ikki yoki undan ko'p bosh harf** (akronim qoldig'i). Beshta nazorat holati: `маълумот`, `таъсир`, **`санъат`**, **`қалъа`**, `Санъат` — oxirgi ikkitasi ATAYIN, chunki ularda `ъ` dan oldin UNDOSH turadi va «unli bo'lsa to'g'ri» degan muqobil qoida ham NOTO'G'RI bo'lardi.
- **Spetsifikatsiyaning literal sharti ham SAQLANDI** alohida assert sifatida va uning **bugun bo'shligi kodda ochiq yozilgan** — «darvoza bor» da'vosi shu bilan chegaralangan.
- **Fayllar:** `frontend/scripts/gen-cyrillic.test.mjs` — **commit** `2e1e167`

### 5. [Qoida 2 — yetishmayotgan kritik darvoza] G-6 ning raqamli-token sharti qo'shildi

- **Muammo:** reja W0-F3 uchun to'rtta assertion sanaydi, `04-UI-SPEC.md` §15 dagi **G-6 ning ta'rifi** esa beshinchi shartni ham o'z ichiga oladi: *«`messages/*.json` da raqam aralashgan lotin tokeni (`/[A-Za-z]+[0-9]/`) umuman yo'q»*. `decisions_context` ning **Qoida 1 (M-3)** i buni takrorlaydi: bunday token **override bilan tuzalmaydi**, ya'ni yagona himoya — kirishidagi taqiq.
- **Tuzatish:** taqiq qo'shildi (`gen-cyrillic.test.mjs`), uchala `messages/*.json` ustida. Bugungi holat o'lchandi: **0 buzilish**.
- **⚠ Naqsh KENGAYTIRILDI** (`/[A-Za-z]+\.?[0-9]/`): spetsifikatsiyaning O'Z taqiq jadvalida `H.264 oqimi` turibdi, lekin nuqtasiz naqsh uni **ushlamaydi** (`H` va `264` orasida `.` bor). Kengaytma — superset. Yolg'on-ijobiy o'lchandi: `84 MB`, `1,2 GB`, `06:00 dan 08:00 gacha`, `NVR qurilmasi. 2 ta kamera` — birortasi ham ushlanmaydi.
- **ICU platsholderlari OLIB TASHLANADI** tekshiruvdan oldin: taqiq foydalanuvchi KO'RADIGAN matnga tegishli, argument NOMIGA emas (`{value1}` ekranda hech qachon ko'rinmaydi).
- **Fayllar:** `frontend/scripts/gen-cyrillic.test.mjs` — **commit** `2e1e167`

### 6. [Qoida 2] `/picture` uchun shakl darvozasi (400) va `frame_mode` reyestrining qattiqligi

- Reja `<action>` da 400 ni talab qiladi, lekin `<behavior>` da ham, mezonlarda ham u yo'q edi. Qo'shildi va testga bog'landi (`test_picture_rejects_a_malformed_channel_id`): `7` -> 400, `103` (oqim `03`) -> 400, `9901` (shakl to'g'ri, kanal yo'q) -> **404**.
- `frame_bytes_for_mode()` noma'lum rejimda `UnknownFrameMode` beradi — standart qiymatga **jimgina qaytmaydi**. Bu `apply_patch` validatsiyasidan mustaqil ikkinchi qatlam.
- **Fayllar:** `services/nvr-sim/sim/isapi.py`, `services/nvr-sim/sim/frames.py` — **commit** `413e816`

### 7. [Kengaytma] `test_nvr_sim.py` ga rejada aytilmagan ijobiy/salbiy nazoratlar

- `test_frame_mode_ok_returns_a_complete_jpeg` (ijobiy nazorat — usiz uchala buzuq-holat testi «sim har doim axlat qaytaradi» holatida ham yashil bo'lardi) va `test_picture_claims_no_rtsp_session` ning ikkinchi yarmi (oqim yo'li BARIBIR sanaydi — sanagichning o'zi buzilmaganining nazorati).
- **Fayllar:** `tests/integration/test_nvr_sim.py` — **commit** `413e816`

## Issues Encountered

- **`node_modules` worktree'da yo'q edi** — `npm ci --no-audit --no-fund` bilan o'rnatildi (530 paket, 29 s). `package.json` va `package-lock.json` **tegilmadi** (`git diff --exit-code` bilan tasdiqlandi).
- **`test_live_view_e2e.py` ning ikki testi** birinchi yugurishda `httpx.ConnectError` berdi — sabab kod emas, `go2rtc` konteyneri izolyatsiyalangan compose loyihasida ko'tarilmagan edi (`npm run sim:up` uni ham ko'taradi). `go2rtc` qo'shilgach ikkalasi ham yashil.
- **`nvr-sim` `--reload` siz ishlaydi** — har kod o'zgarishidan keyin `docker compose restart nvr-sim` bajarildi. Sabotaj tekshiruvi aynan shu tufayli ishonchli: sabotajning kuchga kirgani javob mazmunidan ko'rindi (`200` + `"frame_mode":"corrupt"`), konteyner holatidan taxmin qilinmadi.

## Known Stubs

Yo'q. Bu reja yuza (UI komponentlari) yaratmaydi — u **darvozalar va sinov uskunasi** yetkazadi. Shartli darvozalar (G-1, G-2, G-3, G-10, G-5 ning `snapshots` qismi, W0-F7 ning `snapshots` kaliti) nishon hali mavjud emasligi uchun **o'tadi va sababni CHOP ETADI** — bu stub emas, ataylab qo'yilgan va ochiq belgilangan qamrov chegarasi. Ular `04-08…04-10` da copy va komponentlar kelishi bilan **avtomatik** kuchga kiradi.

## Threat Flags

Yo'q. Bu reja yangi tarmoq endpointi, auth yo'li yoki sxema o'zgarishi kiritmaydi. Yangi ISAPI `/picture` marshruti **mavjud** Digest darvozasidan o'tadi (`test_picture_requires_credentials_and_counts_the_attempt` bilan qulflandi) va faqat `--profile sim` ostidagi test uskunasida yashaydi.

## Doiradan tashqarida topilgan band (fayl to'plamidan tashqarida — TEGILMADI)

`tests/integration/test_live_view_e2e.py:102` va `tests/integration/test_real_nvr.py:109` izohlarida *«`nvr-sim` ning ISAPI `/picture` yo'li 160 baytli `TINY_JPEG` beradi»* deyilgan. Bu **endi noto'g'ri** — `/picture` 2927 baytli kadr beradi.

- **Funksional ta'sir YO'Q:** `test_live_view_e2e` go2rtc'ning `frame.jpeg` ini o'lchaydi (ISAPI'ni emas) va uning `MIN_FRAME_BYTES = 1024` sharti buzilmaydi; `test_real_nvr` `hardware` markeri ostida va **faqat real qurilmaga** boradi, sim'ga hech qachon emas.
- **Nima uchun tuzatilmadi:** ikkala fayl ham bu rejaning `files_modified` ro'yxatidan **tashqarida** va parallel to'lqinda ularga tegish fayl to'qnashuvi xavfini tug'dirardi.
- **Kimga tegishli:** `04-04` (sifat filtri) yoki `04-05` — ikkalasi ham `/picture` iste'molchisi. Izohni bir qator bilan yangilash yetadi.

## User Setup Required

Yo'q.

## Next Phase Readiness

- `04-04` (sifat filtri) uchun **hamma narsa tayyor**: `fixtures.frames.frame_bytes` chegara qiymatlarini, `SimState.frame_mode` esa buzuq baytlarni beradi. Filtr `fixtures.frames` ni **iste'mol qiladi** — teskarisi hech qachon emas.
- `04-08…04-10` (UI) uchun darvozalar **oldindan** qo'yilgan: birinchi `snapshots.*` kaliti qo'shilgan kunning o'zida G-1, G-10 va G-5 kuchga kiradi; `components/snapshots/` katalogi paydo bo'lishi bilan G-2/G-3 to'rtala faylni TALAB qiladi.
- **⚠ To'lqin merge'idan keyin BIRINCHI tekshiriladigan band:** `docker compose --profile test run --rm tests pytest tests/unit/test_frame_fixtures.py -q` — u `04-01` ning `Pillow` qatoriga tayanadi (Deviations 1-band).

## Self-Check: PASSED

- **Yaratilgan/o'zgartirilgan 17 fayl** — hammasi diskda mavjud (`MISSING COUNT: 0`).
- **Uchala commit mavjud:** `76c806e`, `413e816`, `2e1e167` — `git log` bilan tasdiqlandi, bazasi `e9b85cd`.
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin orkestrator tomonidan yangilanadi.
