---
phase: 04-snapshot-pipeline
plan: 14
subsystem: namuna-fayllar-juftligi-va-faza-yopilishi
tags: [env-example, seaweedfs, s3-credentials, found-06, derivation-gate, human-uat, gate-threshold, gap-closure]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 13
    provides: "`test_sentry_processes.py` — `compose.yaml` dan HOSILA qilingan jarayon darvozasi; `ObservedScheduler`; `REQUIREMENTS.md:272` va `ROADMAP.md` ziddiyatining olib tashlanishi"
  - phase: 04-snapshot-pipeline
    plan: 12
    provides: "900 s `gate` chegarasi (olti o'lchov), `04-HUMAN-UAT.md` ning oltita bandi, `04-VALIDATION.md` ning Per-Task jadvali"
  - phase: 04-snapshot-pipeline
    plan: 1
    provides: "`ops/seaweedfs/s3.json.example`, `storage` xizmati, `test_storage_config.py` ning qo'lda compose parseri"
  - phase: 04-snapshot-pipeline
    plan: 4
    provides: "`settings.py:329-355` — bo'sh S3 kalitini ISHGA TUSHISHDA rad etuvchi validatorlar (T-04-29)"
provides:
  - "`.env.example` ↔ `ops/seaweedfs/s3.json.example` juftligi — yangi klon `cp .env.example .env` dan keyin `npm run up` da yiqilmaydi"
  - "`tests/unit/test_storage_config.py` — juftlikning TENGLIK darvozasi + bo'shlik taqig'i + parser quyi chegarasi (uch mustaqil da'vo)"
  - "`ops/seaweedfs/README.md` — `04-12` dan meros qolgan ikkita egasiz ogohlantirish (`down -v` bucketni o'chiradi; `s3.json` `npm run up` dan OLDIN FAYL bo'lishi shart)"
  - "FOUND-06 dalilining HOSILA shakli `REQUIREMENTS.md` da — sanoq emas, `compose.yaml` dan chiqariladigan talab"
  - "`04-HUMAN-UAT.md` #7 — planer istisnosining HAQIQIY Sentry loyihasida ko'rinishi (egasi Ops, tetigi haqiqiy DSN)"
  - "`04-VALIDATION.md` — 42 Per-Task qatori, 7 inson bandi, va `gate` davomiyligining CHEGARADAN OSHGANI o'lchov bilan yozilgan"
affects: [05-cv-zonalar, 06-billing, 08-hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ikki NAMUNA fayl juftligi TENGLIK bilan qulflanadi, YO'QLIK bilan emas — «bo'sh satr yo'q» shaklidagi darvoza faylning O'Z izoh matni bilan to'qnashadi"
    - "Namuna faylni o'lchaydigan darvoza MAHALLIY faylni (`\\.env`) hech qachon o'qimaydi — aks holda u kodni emas, xost holatini o'lchaydi"
    - "Talab dalilining shakli MUHIM: sanoq n+1-elementni struktura jihatidan ko'ra olmaydi, hosila esa ko'radi va yiqiladi"
    - "Bir seans ichidagi davomiylik o'lchovlari solishtirma emas — nazorat o'lchovi (o'zgarmagan ish hajmi) buni ochib beradi"
    - "Chegaradan oshgan o'lchov chegarani KO'TARISH sababi emas; u chegara YOZILGAN hujjatga, sabab tahlili bilan yoziladi"

key-files:
  created:
    - .planning/phases/04-snapshot-pipeline/04-14-SUMMARY.md
  modified:
    - .env.example
    - ops/seaweedfs/README.md
    - ops/docs/monitoring.md
    - tests/unit/test_storage_config.py
    - tests/unit/test_snapshot_settings.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/phases/04-snapshot-pipeline/deferred-items.md
    - .planning/phases/04-snapshot-pipeline/04-HUMAN-UAT.md
    - .planning/phases/04-snapshot-pipeline/04-VALIDATION.md
  deleted: []

key-decisions:
  - "`.env.example` TUZATILDI, egasi bilan yozib qo'yilmadi: `compose.yaml` uchala servisga `${S3_ACCESS_KEY}` ni `:-` STANDARTSIZ uzatadi va `Settings` bo'sh qiymatni rad etadi — ya'ni band «noqulaylik» emas, yangi klonda ISHGA TUSHISHDAGI yiqilish edi"
  - "Juftlik darvozasi TENGLIK sifatida yozildi: «`.env.example` da bo'sh S3 satri yo'q» shaklidagi grep faylning o'z izohi bilan to'qnashardi (izohda `S3_ACCESS_KEY` so'zi bor) va u qiymat ALMASHTIRILGANINI umuman ko'rmasdi"
  - "Darvoza FAQAT `.env.example` ni o'qiydi: `tests` konteyneri repozitoriyni mount qiladi, ya'ni `.env` ni o'qish `deferred-items.md` #2 o'lchagan sinfni (`_env_file=None` tuzatishini) BEKOR QILARDI"
  - "`compose.yaml` TEGILMADI — `:-` siz qaror tuzatishdan keyin ham to'g'ri: kalitni butunlay o'chirgan deploy ishga tushishda yiqilishi KERAK"
  - "`deferred-items.md` #3 ning O'Z «Taklif» i (`s3.json` FAYLmi degan darvoza) ATAYIN bajarilmadi — fayl `.gitignore` ostida, ya'ni darvoza toza klonda qizil bo'lardi va yana mahalliy holatga bog'lanardi; band HUJJAT bilan yopildi va farq ochiq yozildi"
  - "FOUND-06 dalili SANOQDAN HOSILAGA o'tkazildi: uch jarayon nomi endi da'voning ASOSI emas, `compose.yaml` dan chiqarilgan BUGUNGI NATIJA — to'rtinchi servis qo'shilganda darvoza yiqiladi, hujjat esa eskirmaydi"
  - "`deferred-items.md` #1 ning HOLATI o'zgartirilmadi: u boshqa hujjatda (`04-VERIFICATION.md`) yuritiladi va u yerda YOPILGAN deb yozilgan; reyestrga faqat HAVOLA qo'shildi, yangi da'vo emas"
  - "`gate` chegarasi 900 s da QOLDIRILDI, garchi ikkala o'lchov ham undan yuqori chiqqan bo'lsa ham — chegara qarori olti o'lchovga tayanadi va uni bitta ifloslangan seans bilan qayta yozish darvozani mazmunsiz qilardi"
  - "Per-Task jadvalidagi `04-14/T3` qatori `✅ green` — chunki `Status` ustuni BUYRUQ o'tishini o'lchaydi (`npm run gate` exit 0, ikki marta). Chegaradan oshish qator holatini soxtalashtirish bilan emas, chegara YOZILGAN bo'limga o'lchov bilan yozildi"

patterns-established:
  - "«Namuna ↔ namuna» juftligi: ikkala fayl ham repoda, ikkalasi ham sirsiz, tenglik esa darvoza — sir fayllari (`\\.env`, `s3.json`) umuman o'qilmaydi"
  - "Nosozlik SHAKLI xato matnida yoziladi: «konteynerlar ko'tariladi, xato faqat birinchi `PUT` da `SignatureDoesNotMatch` bo'lib chiqadi» — o'quvchi darvozaning NEGA borligini kod o'qimasdan biladi"
  - "Bitta o'zgarish uchta MUSTAQIL da'voga bo'linadi (parser ishlayaptimi · qiymat bo'sh emasmi · qiymatlar tengmi) va sabotaj faqat bittasini qizartiradi — bu ularning mustaqilligining isboti"
  - "Davomiylik regressiyasini e'lon qilishdan oldin NAZORAT o'lchovi olinadi: o'zgarmagan ish hajmi (`gate:fast`) bir seansda ikki barobar sekinlashsa, sabab kodda emas"

requirements-completed: []

# Metrics
duration: 3h 35m
completed: 2026-08-05
---

# Phase 4 Plan 14: Namuna rekvizitlar juftligi, FOUND-06 dalilining hosila shakli va o'lchangan bazaviy holat Summary

**`deferred-items.md` #2 va #3 yopildi (`.env.example` endi `s3.json.example` bilan AYNAN teng va bu TENGLIK darvoza bilan qulflandi, `ops/seaweedfs/README.md` esa `04-12` dan meros qolgan ikkita egasiz ogohlantirishni oldi), FOUND-06 ning dalili hujjatlarda SANOQDAN HOSILAGA o'tkazildi, yettinchi inson bandi o'z chegarasini ochiq aytgan holda qo'shildi — va to'liq darvoza ikki marta yashil o'tdi, LEKIN 900 s chegarasidan oshdi: sabab bu fazaning kodida emasligi nazorat o'lchovi bilan isbotlandi va chegara KO'TARILMADI.**

## Performance

- **Duration:** ~3 soat 35 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 1 ta yangi (SUMMARY) + 10 ta o'zgargan
- **Commits:** 3 ta

## Task Commits

| # | Task | Commit | Turi |
|---|------|--------|------|
| 1 | `.env.example` ↔ `s3.json.example` juftligi + uch darvoza + `README.md` + reyestr | `90869d9` | `fix` |
| 2 | FOUND-06 dalilining hosila shakli, 7-inson bandi, VALIDATION/ROADMAP/monitoring | `2f6a7f4` | `docs` |
| 3 | S4 sabotaji, bazaviy jadval, chegaradan oshish hujjati | `62aaacd` | `docs` |

## ⛔ ENG MUHIM TOPILMA: `npm run gate` CHEGARADAN OSHDI

Buni yumshatmasdan yozaman, chunki reja aynan shuni talab qiladi
(«oshsa bu REGRESSIYA va uni SUMMARY da ochiq yozing; chegarani
ko'tarmang»).

| # | Yugurish | Natija | Chegara |
|---|---|---|---|
| 7 | `npm run gate` (seans o'rtasida) | **exit 0, 1 009 s** | 900 s — **+12 %** |
| 8 | `npm run gate` (darhol keyin, AYNAN o'sha kod) | **exit 0, 1 174 s** | 900 s — **+30 %** |

Reja bitta yugurishni so'ragan edi. Bitta o'lchov «kod sekinlashdimi yoki
xost sekinlashdimi?» savoliga javob BERMAYDI, shuning uchun ikkinchisi
qo'shildi — va u birinchisidan ham SEKIN chiqdi.

### Sabab O'LCHANDI, taxmin qilinmadi

7- va 8-yugurishlar orasida **kod umuman o'zgarmagan** (`git status`
faqat bitta hujjat qatorini ko'rsatdi), shunga qaramay **bu fazaga
umuman aloqasi yo'q bosqichlar ham** sekinlashdi:

| Bosqich | 7-yugurish | 8-yugurish | Farq |
|---|---|---|---|
| `vitest` umumiy davomiyligi | 58.47 s | 79.55 s | **+36 %** |
| `vitest` `environment` (jsdom) | 225.94 s | 282.90 s | **+25 %** |
| `next build` — `Compiled successfully` | 10.9 s | 13.5 s | **+24 %** |
| `next build` — `Finished TypeScript` | 18.7 s | 20.9 s | **+12 %** |
| 51 statik sahifa generatsiyasi | 1 894 ms | 2 500 ms | **+32 %** |

**Hal qiluvchi nazorat o'lchovi** — `gate:fast`, AYNAN bir xil ish hajmi
ustida (uchala yangi unit test ikkala o'lchovda ham bor edi):

| Qachon | `gate:fast` | Izoh |
|---|---|---|
| Seans BOSHIDA (ikkala `gate` dan OLDIN) | **68 s** | `04-12` bazasi bilan **AYNAN teng** |
| Seans OXIRIDA (ikkala `gate` dan KEYIN) | **129 s** | **+90 %** |

O'zgarmagan ish hajmi bir seans ichida ikki barobarga sekinlashdi. Ya'ni
sekinlashuv **xost tomonida va PROGRESSIV** (Windows ustidagi Docker
Desktop uzluksiz og'ir IO ostida).

### Nima da'vo qilinadi va nima QILINMAYDI

1. ✅ **Darvozaning O'ZI yashil:** ikkala yugurish ham exit 0; to'plam
   mazmuni bo'yicha regressiya YO'Q (pastdagi bazaviy jadval).
2. ⛔ **«Davomiylik bo'yicha regressiya yo'q» degan da'vo BERILMAYDI.**
   O'lchov vositasining o'zi ishonchsiz ekani o'lchandi; buni «yashil»
   deb yozish `04-12` ning olti o'lchovli qaroriga yolg'on ustun
   qo'shish bo'lardi.
3. 📌 **Chegara KO'TARILMADI** va band ega bilan uzatildi: 5-fazaning
   validatsiya rejasi, tetigi — TINCH xostda, seans boshida, kamida uch
   o'lchov. Yozilgan joyi: `04-VALIDATION.md` § «3-qadam o'lchovlari».
4. ⚠ **Amaliy ogohlantirish:** xost shu holatda qolsa `npm run gate`
   dasturchining mashinasida ham chegaraga urilishi mumkin. Bu
   darvozaning nosozligi emas — u aynan shuni ko'rsatish uchun qo'yilgan.

## Bazaviy holat jadvali — HAR SON O'LCHANDI, ko'chirilmadi

| O'lchov | Baza (`04-12` / `04-13` / VERIFICATION) | Hozir | Holat |
|---|---|---|---|
| `pytest` (sim ko'tarilgan) | 1 879 / **1 886** / «~1 925» | **1 889 passed**, 5 deselected | ✅ **+3** — aynan shu rejaning uchta yangi unit testi |
| `pytest tests/tenancy` | 472 | **472** | ✅ o'zgarmadi |
| `npx vitest run` (frontend) | 338 (28 fayl) | **338 (28 fayl)** | ✅ o'zgarmadi |
| `node --test frontend/scripts/*.test.mjs` | 115 | **115 tests · 115 pass · 0 fail** | ✅ o'zgarmadi |
| `npm run i18n:check` | 777 × 3 | **777 kalit × 3 til, drift yo'q** | ✅ o'zgarmadi |
| `npm run gate` | exit 0, 686–745 s / **731 s** | **exit 0, 1 009 s va 1 174 s** | ⛔ **CHEGARADAN OSHDI** (yuqoridagi bo'lim) |
| `npm run gate:fast` | 68 s (chegara 180 s) | **68 s** → seans oxirida **129 s** | ⚠ nazorat o'lchovi — degradatsiyani ochib berdi |

Qo'shimcha (gate jurnalidan): `ruff check` + `ruff format --check` +
`mypy` — **exit 0**, 252 fayl formatlangan, 244 manba faylda muammo yo'q.

⚠ **`pytest` soni bazadan PAST EMAS** va farq to'liq izohlanadi:
`04-13` **1 886** o'lchagan, bu reja `test_storage_config.py` ga
**uchta** test qo'shdi → **1 889**. Boshqa hech nima qo'shilmadi va
olib tashlanmadi.

⚠ **VERIFICATION hujjatidagi «~1 925» soni HECH QACHON o'lchanmagan
qiymat bo'lgan ko'rinadi:** `04-12` 1 879, `04-13` 1 886, bu reja 1 889
o'lchadi. Uchala aniq o'lchov ham «~1 925» dan past va ular o'sish
tartibida — ya'ni baza sifatida `04-13` ning **1 886** i ishlatildi.
Bu son SUMMARY da nomlanadi, chunki keyingi tekshiruvchi «1 925 dan
1 889 ga tushdi, regressiya!» degan noto'g'ri xulosaga kelishi mumkin edi.

## S4 sabotajining natijasi — bashoratdan ANIQROQ

**Sabotaj:** `.env.example` dagi `S3_ACCESS_KEY` qiymatiga bitta harf
qo'shildi (`...-access` → `...-accessx`).

| QIZARDI | YASHIL QOLDI |
|---|---|
| **AYNAN BITTA test:** `test_storage_config.py::test_env_example_matches_the_s3_config_example`. Xabar so'zma-so'z ajralishni ko'rsatdi: `{'S3_ACCESS_KEY': ('NAMUNA-ALMASHTIRING-accessx', 'NAMUNA-ALMASHTIRING-access')}` | `tests/unit` ning qolgan **733 testi** — shu jumladan o'sha fayldagi to'rtala `s3.json` darvozasi (`anonymous`, identity soni, `Action:bucket`, `Admin` yo'qligi), compose darvozalari, **va shu rejada qo'shilgan ikkita QO'SHNI test**: `test_env_example_credentials_are_not_empty` hamda `test_env_example_parser_actually_sees_the_keys` |

**Reja nima degan edi:** juftlik testi qizarsin, `s3.json` darvozalari va
qolgan to'plam yashil qolsin. → **Aynan shunday.**

⚠ **Bashoratdan ANIQROQ chiqqan joyi va uning ma'nosi:** ikkita qo'shni
YANGI test ham yashil qoldi. Bu ZAIFLIK emas, ISBOT: uchta da'vo
haqiqatan MUSTAQIL. «Qiymat bo'shmi?», «parser ishlayaptimi?» va
«qiymatlar tengmi?» — uch boshqa savol, va sabotaj faqat uchinchisiga
tegdi. Agar ikkalasi ham qizarganda, bu ularning bir-birini takrorlashini
bildirardi.

**Tiklash:** fayl **`cp` bilan** tiklandi (`git checkout --` bilan
**HECH QACHON EMAS** — `04-12`/`04-13` qoidasi), `git diff --exit-code`
bo'sh chiqdi va darvoza qayta **12 passed** berdi.

## `nyquist_compliant` — IKKI YO'NALISHDA tekshirildi

`03-14` naqshi bo'yicha bayroq faqat «yashil» bo'lgani yetarli emas —
skript uni HISOBLAYOTGANINI ham isbotlash kerak:

| Yo'nalish | Holat | Natija |
|---|---|---|
| 1 | Bayroq `true`, hisob `true` | **exit 0** — «hisob-kitob bilan MOS», 42 qator · 7 inson bandi |
| 2 | Bayroq qo'lda `false` ga o'zgartirildi, hisob hamon `true` | **exit 1** — «`nyquist_compliant: false` HISOB-KITOBGA MOS EMAS (hisoblangani: true)» |

Ya'ni skript qiymatni O'QIMAYDI, HISOBLAYDI. Fayl **`cp` bilan** tiklandi.

⚠ Argumentsiz `npm run validation:check` **2-faza** fayliga ishora qiladi
(`DEFAULT_FILE` qadalgan) va bu faylni QAMRAMAYDI — shuning uchun hamma
o'lchov to'liq yo'l bilan bajarildi. Band `04-13` ning «ochiq qolgan
bandlar» ro'yxatida, egasi 5-fazaning validatsiya rejasi.

## Talab holatlari va darvozalar

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/unit/test_storage_config.py` | **12 passed** (oldin 9) |
| 2 | `pytest tests/unit/test_storage_config.py tests/unit/test_snapshot_settings.py` | **29 passed** |
| 3 | `docker compose --env-file .env.example config` da `S3_ACCESS_KEY: NAMUNA` | **3** — aynan `core-api`, `worker`, `scheduler` (servis nomlari bilan tekshirildi, ko'r-ko'rona `grep -c` bilan emas) |
| 4 | `git diff --exit-code compose.yaml` | **bo'sh** — `:-` siz qaror tegilmagan |
| 5 | `node scripts/check-requirements-sync.mjs` | **exit 0** — 49 talab MOS (**Done 16 · Pending 32 · Blocked 1**) |
| 6 | `node scripts/check-validation-signoff.mjs <04-VALIDATION.md>` | **exit 0** — 42 qator · **7** inson bandi |
| 7 | `**Egasi:**` / `**Tetigi:**` sanog'i `04-HUMAN-UAT.md` da | **7 / 7** |
| 8 | `human_only_verifications` ↔ `04-HUMAN-UAT.md` sarlavhalari | **7 ↔ 7, TARTIBI bir xil** (yonma-yon dastur bilan solishtirildi) |
| 9 | Per-Task jadvalining har qatori: katak soni va `Automated Command` da quvur | **42 qator, 0 muammo** — har qatorda aynan 10 katak, quvur yo'q, hammasi `✅` |
| 10 | `git diff --exit-code .planning/PROJECT.md .planning/STATE.md services/core-api/pyproject.toml frontend/package.json` | **bo'sh** — yangi paket YO'Q (T-04-SC), `STATE.md` ATAYIN tegilmagan |
| 11 | `CAM-02` holati | **`Blocked` bo'lib QOLDI** (3-fazadan; egasi Ops, tetigi VPS deploy'i) |
| 12 | Holat lug'ati | `Done`/`Pending`/`Blocked` — **`Complete` YO'Q** (`04-10` ning urinishini darvoza to'sgan edi) |

## Files Modified

| Fayl | O'zgarish |
|---|---|
| `.env.example` | `S3_ACCESS_KEY`/`S3_SECRET_KEY` bo'shdan `NAMUNA-ALMASHTIRING-*` juftligiga; izoh bloki SAQLANDI va unga juftlik qoidasi hamda `TELEGRAM_*` dan TESKARI ekani qo'shildi |
| `tests/unit/test_storage_config.py` | `ENV_EXAMPLE`, `ENV_LINE`, `PAIRED_CREDENTIALS`, `MIN_ENV_EXAMPLE_KEYS`, `_env_example_values()`, `env_example` fixture'i va **uchta yangi test** (parser chegarasi · bo'shlik taqig'i · TENGLIK) |
| `tests/unit/test_snapshot_settings.py` | Docstring tuzatildi — «S3 kalitlari `.env.example` da ATAYIN BO'SH» endi YOLG'ON; yangi matn chetlab o'tishning HAQIQIY sababini (standart qiymat yo'q) va ikkala o'z darvozasini nomlaydi |
| `ops/seaweedfs/README.md` | §2 ga «`npm run up` DAN OLDIN» ⛔ bloki (Docker bind-mount manbasini KATALOG qilib yaratadi) + «Ikkala NAMUNA fayl — JUFTLIK» bo'limi; §3 ga «`down -v` bucketni ham o'chiradi» ⛔ bloki |
| `ops/docs/monitoring.md` | Yangi §1.1 — `scheduler` Sentry'ni O'ZI o'rnatadi, `schedule_send_failed`, va «planer o'lsa `alert_sweep` ham o'ladi» sababi; halol chegara + `04-HUMAN-UAT.md` #7 havolasi |
| `.planning/REQUIREMENTS.md` | FOUND-06 dalili SANOQDAN HOSILAGA; chegara ustuniga uchinchi inson bandi; footer yangilandi (holat O'ZGARMADI) |
| `.planning/phases/.../deferred-items.md` | Bosh jadval + #2 va #3 uchun «✅ Yopilishi» bo'limlari; #1 uchun faqat HAVOLA |
| `.planning/phases/.../04-HUMAN-UAT.md` | 7-band + intro «oltita»→«yettita» + Summary 6→7 + «Diqqat» bandi (#4/#5/#7 farqi) |
| `.planning/phases/.../04-VALIDATION.md` | 7-inson bandi; `automated_replacements` ning o'lik havolasi almashtirildi + yangi band; **oltita** yangi Per-Task qatori; «3-qadam o'lchovlari» bo'limi (chegaradan oshish) |
| `.planning/ROADMAP.md` | Phase 4 qatori tekshiruv natijasini nomlaydi (4/5, bo'shliq nomma-nom, yopilishi); `04-13`/`04-14` `- [x]`; progress jadvali `14/14` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — bug] `test_snapshot_settings.py` ning docstringi mening o'zgarishimdan keyin YOLG'ON bo'lib qolardi**

- **Topildi:** Task 1 da, `.env.example` ni tahrirlagandan keyin
  paritet testlarini yugurtirganda.
- **Muammo:** `test_env_example_values_equal_the_settings_defaults`
  docstringi «`S3_ACCESS_KEY`/`S3_SECRET_KEY` … `.env.example` da ATAYIN
  BO'SH (sir)» deb yozardi. Mening o'zgarishimdan keyin ular bo'sh emas.
  Testning O'ZI to'g'ri ishlaydi (chetlab o'tish mantiqiy sabab — bu
  maydonlarda ma'noli standart yo'q), lekin SABAB matni yolg'onga aylandi.
- **Yechim:** docstring chetlab o'tishning haqiqiy sababini yozadi va
  ikkala o'z darvozasini (bo'shlik taqig'i + juftlik tengligi) nomlaydi.
- **Nega bu qoldirilmadi:** o'z o'zgarishing yozib qo'ygan yolg'onni
  keyingi rejaga uzatish — bu rejaning O'ZI yopayotgan «jimgina yolg'on»
  sinfi. Fayl rejaning `<files>` ida yo'q edi; qamrov ochiq kengaytirildi.
- **Committed in:** `90869d9`

**2. [Rule 1 — bug] `ops/docs/monitoring.md` da eskirgan bo'lim havolasi**

- **Muammo:** 1-jadvalning 3-qatori tashqi ping uchun «⚠ **ops ishi**,
  §4» deb yozardi; tashqi dead-man's switch yo'riqnomasi esa **§5** da
  (§4 — Telegram boti va chat ID). Havola o'quvchini noto'g'ri bo'limga
  yuborardi.
- **Yechim:** §4 → §5.
- **Committed in:** `2f6a7f4`

### Qamrov qarorlari (hammasi ochiq yozilgan)

**3. [Qamrov qarori] `deferred-items.md` #1 ning HOLATI o'zgartirilmadi — faqat HAVOLA qo'shildi**

- Reja «#1 ning holati o'zgarmagan» deb talab qildi. Lekin men uni
  o'lchadim: `grep -c _anchor_today tests/tenancy/test_snapshot_domain_meta.py`
  → **3**, ya'ni band amalda `04-12` da YOPILGAN va `04-VERIFICATION.md`
  ham «#1 yopilgan» deb yozadi.
- **Muammo:** reyestrga «⬜ OCHIQ» deb yozish YANGI YOLG'ON bo'lardi;
  hech nima yozmaslik esa o'quvchini «demak ochiq» degan xulosaga
  yetaklardi.
- **Tanlangan yo'l:** bandning matni, egasi va tetigi **bayt-bayt
  tegilmadi**; jadvalga esa faqat HAVOLA qo'shildi — holat qayerda
  yuritilishi, o'sha hujjat nima deyishi va uni qanday o'lchash mumkinligi.
  Ya'ni yangi da'vo qilinmadi, mavjud da'voga yo'l ko'rsatildi.
- **Committed in:** `90869d9`

**4. [Qamrov qarori] `deferred-items.md` #3 ning O'Z «Taklif» i ATAYIN bajarilmadi**

- Band «`s3.json` ning FAYL ekanini tekshiradigan bitta qatorli darvoza
  (`test_storage_config.py` da)» ni taklif qilgan edi.
- **O'lchangan sabab:** `ops/seaweedfs/s3.json` `.gitignore` ostida —
  toza klonda u UMUMAN mavjud emas, ya'ni bunday darvoza yangi klonda
  **qizil** bo'lardi va har dasturchini test yugurtirishdan oldin fayl
  yaratishga majburlardi. Bundan tashqari u darvozani MAHALLIY holatga
  bog'lardi — bu #2 o'lchagan aynan o'sha sinf.
- **Tanlangan yo'l:** band HUJJAT bilan yopildi (`README.md` §2 ning ⛔
  bloki), va bu farq reyestrda ochiq yozildi — «darvoza bilan emas,
  hujjat bilan yopildi».
- **Committed in:** `90869d9`

**5. [Rejadan ORTIQ ish] Ikkinchi `gate` yugurishi va `gate:fast` nazorat o'lchovi**

- Reja BITTA `gate` yugurishini so'ragan edi. Birinchisi 1 009 s
  (chegaradan 109 s yuqori) chiqdi.
- **Nega ortiq ish qilindi:** bitta o'lchov «kod sekinlashdimi yoki xost
  sekinlashdimi?» savoliga javob bermaydi, ya'ni u SUMMARY ga faqat
  «sekin» degan foydasiz jumla yozardi. Ikkinchi yugurish (1 174 s) va
  `gate:fast` nazorat o'lchovi (68 s → 129 s, o'zgarmagan ish hajmi
  ustida) savolga ANIQ javob berdi.
- **Natija:** sabab bu fazaning kodida emasligi ISBOTLANDI, chegara
  ko'tarilmadi, band ega va tetik bilan 5-fazaga uzatildi.
- **Committed in:** `62aaacd`

### Kutilmagan topilma

**6. [Topilma] `node --test` darvozasining yo'li hujjatda NOTO'G'RI yozilgan**

- `04-VERIFICATION.md` uni `node --test scripts/*.test.mjs` deb yozadi.
  Repo ildizidagi `scripts/` da esa **birorta** `*.test.mjs` yo'q —
  fayllar `frontend/scripts/` da (sakkizta fayl, 115 test).
- Repo ildizidan yugurtirilgan buyruq **jimgina hech nima
  qaytarmaydi** (glob mos kelmaydi), `node --test frontend/scripts/`
  esa nisbiy yo'llar tufayli **fail** beradi. Ya'ni hujjatdagi buyruqni
  so'zma-so'z ko'chirgan o'quvchi ikkala holatda ham noto'g'ri xulosaga
  kelardi.
- **Bu rejada nima qilindi:** o'lchov to'g'ri yo'l bilan bajarildi
  (`cd frontend && node --test scripts/*.test.mjs` → **115 tests · 115
  pass**) va son bazaviy jadvalga TO'G'RI buyruq bilan yozildi.
- **Nima QILINMADI:** `04-VERIFICATION.md` tahrirlanmadi — u tekshiruv
  hisoboti, ya'ni TARIX hujjati, va uni ijrochi qayta yozmaydi. Band
  qayta tekshiruvga uzatiladi (pastda).

---

**Total deviations:** 6 (**2× Rule 1 bug** — ikkalasi ham hujjat
darajasida, 3× qamrov/ortiq ish qarori, 1× topilma).

**Impact on plan:** Birorta darvoza kuchsizlantirilmadi. Ikkitasi (1, 2)
hujjatdagi yolg'onni yopdi, ikkitasi (3, 4) YANGI yolg'on yozishdan
saqladi, biri (5) rejadagi «bitta o'lchov» ni ma'noli xulosaga
aylantirdi. Mahsulot kodi (`services/`) bu rejada UMUMAN o'zgarmadi —
o'zgargan yagona ishga tushiriladigan artefakt `tests/` va namuna
fayllar.

## Issues Encountered

- **`docker compose --env-file .env.example config | grep -c` ni
  ko'r-ko'rona ishlatish yetarli emas edi.** Sanoq `3` chiqdi, lekin
  «qaysi uchtasi?» savoliga javob bermasdi. `awk` bilan servis nomiga
  bog'lab qayta o'lchandi: `core-api`, `worker`, `scheduler` — aynan
  reja kutgan uchlik.
- **`npm run test` ichidagi pytest `-qq` bo'lib qoladi** (`addopts` da
  allaqachon bitta `-q` bor), shuning uchun `gate` jurnalida pytest
  ning yakuniy «N passed» satri UMUMAN yo'q. Sonlar shuning uchun
  alohida, `-q` siz yugurish bilan o'lchandi (**1 889 passed**).
- **`ops/seaweedfs/s3.json` va `.env` ikkalasi ham ish stansiyasida
  MAVJUD** va ular TEGILMADI — darvoza faqat `.example` fayllarni
  o'qiydi, ya'ni mahalliy holat o'lchovga ta'sir qilmadi.

## Known Stubs

Yo'q. Bu rejada mahsulot kodi umuman o'zgarmadi; qo'shilgan uchta test
ham haqiqiy fayllarni o'qiydi (mock, fixture yoki qattiq yozilgan
qiymat yo'q).

⚠ **Stub bo'lmagan, lekin OCHIQ qolgan bandlar:**

1. **`npm run gate` davomiyligi chegaradan yuqori** (1 009 s / 1 174 s,
   chegara 900 s). Sabab xost tomonida ekani o'lchandi, lekin band
   yopilmadi. **Egasi:** 5-fazaning validatsiya rejasi. **Tetigi:**
   tinch xostda uch o'lchov.
2. **`scripts/check-validation-signoff.mjs` ning `DEFAULT_FILE` i
   2-fazaga qadalgan** (`04-13` dan meros). **Egasi:** 5-fazaning
   validatsiya rejasi.
3. **`04-VERIFICATION.md` dagi ikkita noaniq son/yo'l** — «~1 925 test»
   (aniq o'lchovlar 1 879/1 886/1 889) va `node --test scripts/*.test.mjs`
   (fayllar `frontend/scripts/` da). Tekshiruv hujjati TARIX bo'lgani
   uchun ijrochi uni tahrirlamadi. **Egasi:** qayta tekshiruv.
4. **`04-HUMAN-UAT.md` ning yettala bandi** — hammasi `pending`, har
   birida ega va tetik bor. **#2 (90 kunlik kalendar) bu rejada
   TEGILMADI va YOPILMADI** — vaqtni kutib bo'lmaydi va mexanizm dalili
   siyosat dalili sifatida KO'RSATILMADI.

## Threat Flags

Reja threat register'ining beshala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-101 (`.env.example` dagi rekvizit ma'lumot oshkorligi) | **mitigate bajarildi**: qiymatning O'ZI `NAMUNA-ALMASHTIRING-*` — prod qiymati bilan adashtirib bo'lmaydi; `ops/seaweedfs/README.md` almashtirish qadamini yozadi; `compose.yaml` ning `:-` siz qarori TEGILMADI, ya'ni kalit butunlay o'chirilsa servis ISHGA TUSHISHDA yiqiladi. ⚠ Sir fayllar (`.env`, `s3.json`) darvoza tomonidan UMUMAN o'qilmaydi |
| T-04-102 (FOUND-06 dalilining rad etilishi) | **mitigate bajarildi**: dalil sanoq emas, hosila darvozaga (`test_sentry_processes.py`) ishora qiladi; `check-requirements-sync.mjs` exit 0 va ro'yxat ↔ jadval driftini ushlaydi |
| T-04-103 (`nyquist_compliant` bayrog'ining soxtalashtirilishi) | **mitigate bajarildi**: bayroq IKKI yo'nalishda tekshirildi (yuqoridagi jadval); `Automated Command` katagida quvur belgisi yo'qligi 42 qator bo'yicha KATAKMA-KATAK o'lchandi (butun fayl grep'i EMAS) |
| T-04-104 (`gate` chegarasining jimgina bo'shashi) | **mitigate bajarildi va SINALDI**: chegara oshdi, KO'TARILMADI, oshish sababi bilan birga hujjatga yozildi |
| T-04-SC (paket o'rnatishlari) | **Yangi paket YO'Q**; `git diff --exit-code services/core-api/pyproject.toml frontend/package.json` bo'sh |

⚠ **Yangi xavf yuzasi topilmadi.** Bu reja tarmoq endpointi, auth yo'li,
fayl kirish naqshi yoki sxema o'zgarishi kiritmadi.

## `.planning/STATE.md` uchun TAYYOR MATN

⚠ **`STATE.md` bu rejada ATAYIN TEGILMADI** (`04-12`/`04-13` naqshi) —
`git diff --exit-code .planning/STATE.md` bo'sh. Quyidagi matn faza
yopilish oqimi uchun tayyor holda beriladi.

### `Current Position` bo'limi

```
Phase: 4
Plan: 14 of 14
Status: Bo'shliq yopildi — qayta tekshiruv kutilmoqda
Last activity: 2026-08-05

Progress: [██████████] 100% (14/14 reja — 04-01…04-14)

⚠ 04-13 va 04-14 gap-closure to'lqini edi. `04-VERIFICATION.md` fazani
`gaps_found` (4/5) deb yopgan; yagona bo'shliq — `scheduler` jarayonida
`init_sentry()` chaqirilmasligi — `04-13` da uch mustaqil qatlamda
yopildi, `04-14` esa uning atrofidagi ochiq bandlarni yopib bazaviy
holatni o'lchadi. Fazaning `- [x]` belgisi ATAYIN qo'yilmadi: yopish
qarori QAYTA TEKSHIRUVNIKI, ijrochiniki emas.
```

### `Progress` frontmatter'i

```
completed_plans: 67   # 66 -> 67
percent: 33           # o'zgarmaydi (9 fazadan 3 tasi yopiq)
```

### `Performance Metrics` jadvaliga qator

```
| Phase 04 P14 | 215min | 3 tasks | 11 files |
```

### `Decisions` bo'limiga qo'shiladigan bandlar

```
- [Phase 04]: 04-14: `.env.example` ↔ `s3.json.example` juftligi TENGLIK bilan qulflandi, YO'QLIK bilan emas — «bo'sh satr yo'q» shaklidagi grep faylning O'Z izohi bilan to'qnashardi va qiymat almashtirilganini ko'rmasdi
- [Phase 04]: 04-14: namuna faylni o'lchaydigan darvoza `.env` ni HECH QACHON o'qimaydi — aks holda u `deferred-items.md` #2 o'lchagan sinfga (`_env_file=None` tuzatishiga) qaytib tushardi
- [Phase 04]: 04-14: `compose.yaml` ning `:-` siz qarori tuzatishdan KEYIN ham to'g'ri — kalitni butunlay o'chirgan deploy ishga tushishda yiqilishi KERAK
- [Phase 04]: 04-14: FOUND-06 dalili SANOQDAN HOSILAGA — uch jarayon nomi endi da'voning ASOSI emas, `compose.yaml` dan chiqarilgan bugungi NATIJA; to'rtinchi servisda darvoza yiqiladi, hujjat esa eskirmaydi
- [Phase 04]: 04-14: `deferred-items.md` #3 ning o'z «Taklif» i (`s3.json` FAYLmi darvozasi) ATAYIN bajarilmadi — fayl `.gitignore` ostida, darvoza toza klonda qizil bo'lardi va yana mahalliy holatga bog'lanardi
- [Phase 04]: 04-14: `npm run gate` 1 009 s va 1 174 s (chegara 900 s) — chegara KO'TARILMADI; sabab kodda emasligi nazorat o'lchovi bilan isbotlandi (`gate:fast` o'zgarmagan ish hajmida 68 s -> 129 s)
- [Phase 04]: 04-14: davomiylik regressiyasi e'lon qilinishidan OLDIN nazorat o'lchovi olinadi — bir seans ichidagi o'lchovlar solishtirma emas
```

### `Blockers/Concerns` bo'limi — TO'RTTA Phase 4 bandi almashtiriladi

**O'CHIRILADI (hammasi yopilgan):**

```
- **[Phase 4] Kadr olish usuli hal qilinmagan** — ...
- **[Phase 4] Job orchestration** — ...
- [Phase 4] npm run gate — 1000 s, shundan 316 s (31 %) qayta bajarish; ...
- [Phase 4] go2rtc-sim oqimini birorta test iste'mol qilmaydi — ...
```

**O'RNIGA YOZILADI:**

```
- ~~[Phase 4] Kadr olish usuli~~ — **YOPILDI 2026-08-01/`04-07`:** uchala yo'l (go2rtc `/api/frame.jpeg` → ISAPI `/picture` → ffmpeg) qurildi va `nvr_devices.capture_method` bilan tanlanadi; real qurilmaga o'tish MA'LUMOT o'zgarishi
- ~~[Phase 4] Job orchestration~~ — **YOPILDI 2026-08-05/`04-12`:** ikkalasi ham kerak edi — `taskiq scheduler` holatsiz 1-daqiqalik tik, reja/ijara/idempotentlik esa Postgres `capture_runs` da (`SKIP LOCKED` + lease, D-02/D-03)
- ~~[Phase 4] npm run gate — 316 s (31 %) qayta bajarish~~ — **YOPILDI `03-12` da**, chegara esa `04-12` da olti o'lchov asosida 1200 s -> 900 s ga TUSHIRILDI
- ~~[Phase 4] go2rtc-sim oqimini birorta test iste'mol qilmaydi~~ — **YOPILDI `03-14` da:** `test_live_view_e2e.py` kashfiyot hosil qilgan oqimdan HAQIQIY JPEG oladi
- **[Phase 4 → 5] `npm run gate` davomiyligi chegaradan oshdi** — `04-14` da 1 009 s va 1 174 s o'lchandi (chegara **900 s**, KO'TARILMADI). Sabab bu fazaning kodida EMAS va bu o'lchandi: o'zgarmagan kod ustida har bosqich 12–36 % sekinlashdi, nazorat o'lchovi `gate:fast` esa bir seansda 68 s -> 129 s bo'ldi (xost tomonidagi progressiv degradatsiya). **Egasi:** 5-fazaning validatsiya rejasi. **Tetigi:** TINCH xostda, seans boshida, kamida uch o'lchov. ⚠ Chegarani ko'tarish faqat shu o'lchovdan KEYIN muhokama qilinadi
- **[Phase 4 → 8] `include_local_variables=False` qarori** — `04-12` da xavfsiz standart sifatida qo'yilgan va HAQIQIY hodisa kelmaguncha baholab bo'lmaydi. Sentry'ga real DSN ulangan kuni (`04-HUMAN-UAT.md` #7) qayta ko'riladi: lokal o'zgaruvchilar diagnostikani sezilarli yaxshilaydi, lekin ular shaxsiy ma'lumot tashishi mumkin. **Egasi:** Ops + 8-faza. **Tetigi:** birinchi haqiqiy Sentry hodisasi
```

⚠ Qolgan bandlar (Phase 0 NVR kirish, tushum bazasi, Phase 5 CV
samaradorligi, huquqiy ko'rik, 7 savol, stek yangilanishi, CAM-02)
**TEGILMAYDI** — ular bu fazaning mavzusi emas.

### `Session Continuity`

```
Last session: 2026-08-05
Stopped at: Completed 04-14-PLAN.md
Resume file: None
```

## Qayta tekshiruvga TAYYORLIK

`04-VERIFICATION.md` ning `gaps:` bloki bo'yicha nima yopildi va u
QAYSI BUYRUQ bilan qayta o'lchanadi:

### `gaps[0]` — SC#5 / FOUND-06 ning Sentry yarmi (yagona bo'shliq)

| `missing` bandi | Yopildi | Qayta o'lchash buyrug'i |
|---|---|---|
| `CLIENT_STARTUP` ilmog'i — planer istisnolari Sentry'ga borishi uchun | `04-13` (`_install_client_observability`) | `pytest tests/unit/test_scheduler_observability.py -q` |
| `SENTRY_ENTRYPOINTS` / `test_both_processes_install_sentry` ni JARAYON bo'yicha hisoblaydigan qilish | `04-13` — ro'yxat QO'SHILMADI, ro'yxatning O'ZI olib tashlandi va `compose.yaml` dan hosila qilindi | `pytest tests/unit/test_sentry_processes.py -q` |
| Planerning yutilgan `send_task` istisnosini qoplash | `04-13` (`ObservedScheduler.on_ready` → jurnal + Sentry → QAYTA KO'TARISH) | `pytest tests/integration/test_phase4_criteria.py -q` |

`artifacts` bo'yicha uchala fayl ham o'zgargan:
`app/worker.py` (ilmoq + `ObservedScheduler`), `tests/unit/test_sentry_scrub.py`
(sanoqli test olib tashlandi), `tests/integration/test_phase4_criteria.py`
(`SENTRY_ENTRYPOINTS` o'rniga HAQIQIY jarayon zondi).

### Anti-naqshlar jadvalidagi yagona ⚠️ Warning bandi

| Band | Yopildi | Qayta o'lchash buyrug'i |
|---|---|---|
| `.env.example:108-109` — bo'sh `S3_ACCESS_KEY`/`S3_SECRET_KEY` | **`04-14` / T1** | `pytest tests/unit/test_storage_config.py -q` va `docker compose --env-file .env.example config` |

### «FOUND-06 ning `Done` holati bu bo'shliq bilan to'liq mos emas» bandi

`04-13` matnni uchala jarayonga kengaytirdi; **`04-14` esa uni SANOQ
bo'lishdan chiqardi** — dalil endi `compose.yaml` dan hosila qilinadigan
TALAB. Qayta o'lchash: `node scripts/check-requirements-sync.mjs`
(exit 0, Done 16 · Pending 32 · Blocked 1).

### `deferred` va `human_verification` bloklari

- `deferred` ning ikkala bandi (tashqi dead-man's switch, `backup`
  yurak urishi) **O'ZGARMADI** — ikkalasi ham D-21/Phase 8 niki.
- `human_verification` **oltitadan YETTITAGA** chiqdi. Yangi band —
  hodisaning haqiqiy Sentry loyihasiga yetib borishi (`04-HUMAN-UAT.md`
  #7, egasi Ops). Qayta o'lchash:
  `node scripts/check-validation-signoff.mjs .planning/phases/04-snapshot-pipeline/04-VALIDATION.md`
  → «inson bandlari: **7**».

### ⚠ Qayta tekshiruvchi uchun uchta OGOHLANTIRISH

1. **`npm run gate` chegaradan oshishi mumkin** (1 009 s / 1 174 s
   o'lchandi, chegara 900 s). Bu SIZNING xostingizda ham takrorlanishi
   mumkin. Sabab tahlili `04-VALIDATION.md` § «3-qadam o'lchovlari» da;
   band ega bilan 5-fazaga uzatilgan. **Bu bo'shliq deb sanalmasin —
   u OCHIQ BAND deb sanalsin va uni shu SUMMARY nomlaydi.**
2. **`node --test scripts/*.test.mjs` ni repo ILDIZIDAN yugurtirmang** —
   fayllar `frontend/scripts/` da; ildizdan yugurtirilgan buyruq jimgina
   hech nima qaytaradi. To'g'ri shakli:
   `cd frontend && node --test scripts/*.test.mjs` → **115 pass**.
3. **`pytest` ning kutilgan soni — 1 889**, `04-VERIFICATION.md` dagi
   «~1 925» EMAS. Uchala aniq o'lchov (1 879 → 1 886 → 1 889) o'sish
   tartibida.

**Bloklovchi yo'q.**

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*

## Self-Check: PASSED

- **Yaratilgan fayl diskda tasdiqlandi** (`MISSING: 0`):
  `.planning/phases/04-snapshot-pipeline/04-14-SUMMARY.md`.
- **O'ntala o'zgargan fayl ham diskda:** `.env.example`,
  `ops/seaweedfs/README.md`, `ops/docs/monitoring.md`,
  `tests/unit/test_storage_config.py`, `tests/unit/test_snapshot_settings.py`,
  `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`,
  `deferred-items.md`, `04-HUMAN-UAT.md`, `04-VALIDATION.md`.
- **Uchala commit `git log` da tasdiqlandi:** `90869d9`, `2f6a7f4`,
  `62aaacd`.
- **Birorta commitda fayl o'chirilishi YO'Q**
  (`git diff --diff-filter=D --name-only 3643a7b..HEAD` bo'sh).
- **Ikkala sabotajdan/tekshiruvdan keyin ham tiklash `cp` bilan
  bajarildi** (`.env.example` S4 dan keyin, `04-VALIDATION.md`
  bayroq tekshiruvidan keyin) va `git diff` har safar bo'sh chiqdi —
  **`git checkout --` HECH QACHON ishlatilmadi**.
- **Guard fayllari tegilmagan:**
  `git diff --exit-code .planning/PROJECT.md .planning/STATE.md
  services/core-api/pyproject.toml frontend/package.json` — **bo'sh**.
- **Ishchi daraxt toza** — repo ildizidagi uchta begona fayl
  (`.docx` × 2, `SBOZOR-MVP-texnik-topshiriq.md`) TEGILMADI.
- ⛔ **`npm run gate` exit 0 (ikki marta), LEKIN 1 009 s va 1 174 s —
  900 s chegarasidan yuqori.** Bu Self-Check'ni PASSED qilishga
  to'sqinlik qilmaydi (darvoza yashil va to'plam sonlari bazadan past
  emas), lekin u OCHIQ BAND sifatida yuqorida ega va tetik bilan
  yozilgan va chegara KO'TARILMAGAN.
