---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 11
subsystem: faza-darvozasi-va-validatsiya
tags: [phase-gate, sim, hardware-marker, runbook, validation-signoff, traceability, latency, wave-10]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 10
    provides: "kameralar ro'yxati, kashfiyot paneli va jonli ko'rish dialogi — fazaning oxirgi yuzasi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 07
    provides: "`POST /cameras/{id}/live-token`, `/internal/live-authz`, `ops/wireguard/wg0.conf.example`"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`POST /nvr-devices`, `/discover` (202 + `run_id`), poll marshruti"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 02
    provides: "`nvr-sim` konteyneri, real dumpdan olingan fixture'lar, `sim`/`slow`/`hardware` markerlari"
provides:
  - "`tests/integration/test_phase3_criteria.py` — SC#1…SC#8 ning YAGONA darvozasi (8 mezon testi + meta-test)"
  - "SC#7 zanjiri: forma -> saqlash -> kashfiyot jobi -> poll -> kameralar ro'yxati -> jonli ko'rish chiptasi, BIR sessiyada"
  - "`tests/integration/test_real_nvr.py` — `hardware` markeri ostida 5 test; fazani BLOKLAMAYDI"
  - "`pyproject.toml` addopts: `-m \"not hardware\"` standarti (filtr bitta joyda)"
  - "`ops/scripts/verify-real-nvr.sh` — chiqishi JSON bo'lgan dala zondi (sim fixture'lari bilan solishtiriladi)"
  - "`ops/docs/nvr-onboarding.md` — admin, on-site odam, subnet to'qnashuvi, real NVR tartibi, 12 xato kodi"
  - "`03-VALIDATION.md` — 33/33 ✅, hisoblangan imzo, o'lchangan kechikish va 31 % qayta bajarish topilmasi"
affects: [04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mezon testi USULNI ham qulflaydi, faqat natijani emas: SC#1 o'z manba matnini o'qib taqiqlangan literalning yo'qligini tasdiqlaydi, izlanadigan satr esa MAHSULOT chiqishidan olinadi (obfuskatsiya ham, ikkinchi haqiqat manbai ham emas)"
    - "Bir markerga `skip`, boshqasiga `fail` — siyosat MUHITGA emas, BOG'LIQLIK TABIATIGA qarab tanlanadi: simulyator CI'da BO'LISHI shart (`fail`), real qurilma esa YO'Q (`skip`)"
    - "Marker filtri `pyproject.toml` addopts'ida, `package.json` da emas: uch chaqiruv joyi (npm, yalang'och pytest, IDE) bir xil standartni oladi"
    - "Bloklamaydigan to'plam SIMULYATORGA qaratib bir marta ishga tushiriladi — «hech qachon bajarilmaydigan to'plam» tuzatish emas; qizargan assert'lar sim'ning modellamagan joylarini NOMLAYDI"
    - "Dala skriptining chiqishi JSON: uni saqlash, `jq` bilan kesish va fixture bilan `diff` qilish mumkin — Pitfall 4 ni yopadigan yagona mexanik yo'l"

key-files:
  created:
    - tests/integration/test_phase3_criteria.py
    - tests/integration/test_real_nvr.py
    - ops/scripts/verify-real-nvr.sh
    - ops/docs/nvr-onboarding.md
  modified:
    - pyproject.toml
    - .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Taqiqlangan RTSP literali test faylida YOZILMAYDI — u `rtsp_url()` ning CHIQISHIDAN olinadi. Muqobil ikkita variant ham yomon edi: literalni yozish assert'ni o'z-o'zini yolg'on-yashil qilardi, satrni bo'laklab qurish (`\"rtsp\" + \"://\"`) esa 03-09 ochiq rad etgan obfuskatsiya bo'lardi. Uchinchi yo'l naqshni MAHSULOTGA bog'laydi va sxema o'zgarsa u ham ko'chadi"
  - "`hardware` markerining filtri `pyproject.toml` addopts'iga qo'yildi, `package.json` ga emas. Buyruq qatoridagi `-m` uni to'liq almashtiradi (o'lchandi: `-m hardware` -> 5 test, standart -> 0), ya'ni `test:sim` ning `-m \"sim and not slow\"` i buzilmaydi. `package.json` da qilinsa filtr uch joyda takrorlanardi"
  - "`hardware` to'plami SIMULYATORGA qaratib ishga tushirildi va 5 testdan 3 tasi o'tdi. Ikkita qizarish — sim'ning ATAYIN modellamagan joylari (160 baytli `TINY_JPEG` va RTSP tinglovchisining yo'qligi). Ya'ni to'plam haqiqatan bajariladi va assert'lari haqiqatan o'lchaydi"
  - "To'lqin chegarasi 618 s -> 1200 s ga KO'TARILDI, lekin sababsiz emas: har qadamning narxi sanaldi va o'sishning 31 % i QAYTA BAJARISH ekani `--collect-only` bilan isbotlandi. `gate:fast` chegarasi (180 s) KO'TARILMADI — o'lchov 75 s"
  - "31 % qayta bajarish bu rejada TUZATILMADI: tuzatish `package.json` ni o'zgartiradi (T-03-SC da qulflangan) va sof tejash emas — `test:sim` zanjirga `sim:up --wait` ni olib keladi, `test:tenancy` esa NOMLANGAN signal beradi. Taklif aniq diff bilan 4-fazaga yozildi"
  - "CAM-01 va CAM-08 `Done`; CAM-02, CAM-03, CAM-09 `Blocked` — uchalasining ham yetishmayotgan dalili NOMLANGAN. `Done` qo'yish o'lchanmagan jumlani «isbotlangan» qilib ko'rsatardi va keyingi faza uning ustiga qurilardi (`02-VERIFICATION.md` ning darsi)"
  - "`Go2rtcClient.remove_stream` chaqirilmasligi QABUL QILINDI: arxivlangan kamera token olmaydi (404, testda), go2rtc ro'yxati xotirada yashaydi, `rtsp_url()` parolni umuman olmaydi. Arxivlash yo'liga tarmoq chaqiruvini qo'shish uni go2rtc MAVJUDLIGIGA bog'lardi — yomonroq savdo; to'g'ri shakl 4-fazadagi reconciliation"
  - "Audit hajmi QABUL QILINDI o'lchov bilan: Karmana miqyosida ~75 qator/kun, ~27k qator ~14 MB/yil — 400 GB diskda ahamiyatsiz. Remediatsiya ma'lum va arzon, lekin u BARCHA audit ostidagi jadvallarga tegadi; qayta ochish sharti nomlandi (skan CRON'ga o'tganda yoki bozorlar > 10)"
  - "Sim testlarini Postgres testcontainer'idan ajratish O'LCHANDI va RAD ETILDI: 70 sim testidan 32 tasi (46 %) bazani HAQIQATAN talab qiladi, ya'ni `npm run test:sim` konteynerni baribir ko'taradi. 03-02 ning prototipi faqat yolg'iz fayl uchun foyda berardi; haqiqiy lever — 31 % qayta bajarish"

patterns-established:
  - "Pattern: qabul mezonining `-q` bayrog'i `addopts` dagi `-q` bilan qo'shilib `-qq` beradi va chiqishni faqat sanoq qatoriga aylantiradi — naqsh yozilganda konfiguratsiyadagi standart bayroqlar HISOBGA OLINISHI kerak"
  - "Pattern: `wait` (argumentsiz) POSIX bo'yicha HAR DOIM 0 qaytaradi — bir vaqtdagi bolalar natijasini o'lchaydigan skript har PID ni ALOHIDA kutishi shart; aks holda yolg'on-yashil"
  - "Pattern: bloklamaydigan to'plamni yozgandan keyin uni MAVJUD eng yaqin nishonga qaratib bir marta ishga tushirish shart — birinchi yugurish ikkita haqiqiy xatoni topdi (ISAPI prefiksining ikkilanishi va yolg'on-yashil `wait`)"
  - "Pattern: `nyquist_compliant` ikkala yo'nalishda sinaladi — `true` yozib skriptni chaqirish YETARLI EMAS, `false` ga o'zgartirib skript qizarishini ham ko'rish kerak"

requirements-completed: [CAM-01, CAM-08]

# Metrics
duration: 150min
completed: 2026-08-03
---

# Phase 3 Plan 11: Sakkizala mezonning yagona darvozasi, `hardware` to'plami va validatsiya imzosi Summary

**ROADMAP'ning sakkizala mezoni endi bitta faylda, bitta buyruq bilan o'lchanadi va SC#7 zanjiri — forma'dan jonli ko'rish chiptasigacha — bir sessiyada kesib o'tiladi; real qurilma to'plami mavjud, ishlaydi va fazani bloklamaydi; kechikish chegarasi o'lchov bilan asoslandi va darvozaning 31 % i qayta bajarish ekani isbotlandi.**

## Performance

- **Duration:** ~150 min (shundan ~55 min — kechikishning uch martalik o'lchovi)
- **Tasks:** 3/3 (uchta commit)
- **Files:** 8 (4 yangi, 4 o'zgargan)
- **Sabotajlar:** 2 ta (biri rejada, biri qo'shimcha) — ikkalasi ham AYNAN kutilgan testni qizartirdi

## Task Commits

1. **Sakkizala mezonning yagona darvozasi (reja Task 1)** — `2932c68` (test)
2. **Bloklanmaydigan `hardware` to'plami, dala zondi va runbook (reja Task 2)** — `4ccd14b` (feat)
3. **Validatsiya imzosi, kechikish o'lchovi va talablar traceability'si (reja Task 3)** — `1046685` (docs)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `tests/integration/test_phase3_criteria.py` | SC#1…SC#8 uchun bittadan nomlangan test + meta-test; docstringlarda ROADMAP matni verbatim |
| `tests/integration/test_real_nvr.py` | `hardware` markeri ostidagi 5 test: `deviceInfo`, kanal ro'yxati, RTSP porti, har kanaldan kadr, 3 ta bir vaqtdagi RTSP sessiyasi |
| `ops/scripts/verify-real-nvr.sh` | Dala zondi — `curl --digest`, chiqishi JSON, qurilmani O'ZGARTIRMAYDI |
| `ops/docs/nvr-onboarding.md` | Admin (7 qadam), on-site odam (2 qadam), subnet to'qnashuvi, real NVR tartibi, 12 xato kodi, nosozliklar jadvali |
| `pyproject.toml` | `addopts` ga `-m "not hardware"` standarti |
| `03-VALIDATION.md` | 33/33 ✅, hisoblangan imzo, yakuniy kechikish o'lchovi, 4 ta `open_items` |
| `.planning/REQUIREMENTS.md` | CAM-01/CAM-08 `Done`; CAM-02/03/09 `Blocked` (sabab bilan); «Faza kesimida» 3-qatori tuzatildi |
| `.planning/ROADMAP.md` | 03-11 `[x]`, Phase 3 `[x]` (qayta tekshiruv kutilyapti izohi bilan) |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** *(rejada yozilgan)* | `nvr_repo.py` dagi `_name_expression()` `CASE WHEN name_overridden` dan `EXCLUDED.name` ga soddalashtirildi | `test_phase3_criteria.py::test_sc2_rescan_is_idempotent` — **AYNAN 1**, va AYNAN to'g'ri assertda: «qayta skan admin qo'ygan nomni bosib ketdi» (`'tagahoov' == 'Sabzavot qatori'`) | SC#1, SC#3…SC#8 va meta-test — **8 test** | ⚠ Rejaning bashorati **aynan tasdiqlandi**. Mezonlar bir faylda bo'lsa ham ALOHIDA o'lchanadi: SC#1 «kashfiyot ishlaydi» ni, SC#2 esa «qayta skan admin qarorini saqlaydi» ni tekshiradi va ular bir-birini niqoblamaydi |
| **S2** *(qo'shimcha)* | `test_sc5_...` funksiyasining nomidan `sc5` bo'lagi olib tashlandi (test O'ZI o'zgarmadi) | `test_every_criterion_has_its_own_test` — **1** | Sakkizala mezon testi (o'sha qayta nomlangani ham) — **8 test** | ⚠ Meta-testning butun qiymati shu: mezon testining O'ZI ishlab turadi, lekin u endi SC#5 ning egasi sifatida SANALMAYDI. Usiz fayl qayta tashkil qilinganda mezonlardan biri jimgina egasiz qolardi va darvoza baribir yashil bo'lardi |

Ikkala sabotaj ham commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; tiklanish testlar bilan tasdiqlandi va ish daraxti toza qoldi.

## O'lchangan dalillar

### Sakkizala mezon (bitta buyruq: `npm run test:sim`)

| Mezon | Test | Nima kesib o'tiladi |
|---|---|---|
| SC#1 | `test_sc1_admin_enters_only_the_address_and_credentials` | Forma (3 maydon) -> 201 -> kashfiyot -> `channels_found = channels_added = 6` -> 6 kamera; model/seriya ISAPI'dan; RTSP porti **kashf etildi** (`rtsp_port_assumed is False`); **fayl o'z manbasida RTSP literali yo'qligini tasdiqlaydi** |
| SC#2 | `test_sc2_rescan_is_idempotent` | Uch ketma-ket skan: 2-si `channels_added = 0` va `id` lar o'zgarmaydi; 3-sida 5-kanal yo'qoladi -> `offline`, **qator soni KAMAYMAYDI**; admin qo'ygan nom (mahsulot yo'lidan, `PATCH /cameras/{id}`) ikki skandan keyin ham joyida |
| SC#3 | `test_sc3_failure_names_the_cause_and_the_fix` | Uch rejim -> uch **ajratilgan** kod; har kod uchun `cameras.errorCause.*` **va** `cameras.errorFix.*` **uchala** katalogda bo'sh emas |
| SC#4 | `test_sc4_password_never_leaves_the_cipher` | Xom bayt bazada (ochiq matn yo'q); to'rt javob tanasi; **butun** `audit_log` (`old` + `new` + `changed_keys`) — ochiq matn ham, shifrlangan token ham yo'q |
| SC#5 | `test_sc5_the_nvr_is_reachable_only_through_the_tunnel` | Ommaviy IP -> **422 `nvr_host_public_blocked`**; `wg0.conf.example` da butun-internet CIDR'i yo'q; `verify-tunnel.sh` mavjud, shebang bilan va bajariladigan. **3-da'vo QO'LDA** deb belgilangan |
| SC#6 | `test_sc6_live_view_requires_authorization` | Direktor chipta oladi + `audit_log` da `reason='live_view'` **aynan 1** qator; chiptasiz `/internal/live-authz` -> **403**; begona bozor direktori -> **404** |
| SC#7 | `test_sc7_the_whole_flow_runs_against_a_simulator` | **Butun zanjir bir sessiyada** + go2rtc'ga yuborilgan `src` da admin kiritgan `host` bor; ilova kodining **barcha** `.py` fayllarida `nvr-sim`/`__sim__`/`SIM_` **yo'q** |
| SC#8 | `test_sc8_the_delete_guard_lives_in_the_schema` | Faol bozor `DELETE FROM markets` da **`23514`** (ilova qatlami butunlay chetlab o'tiladi); qoralama bozor to'rtala NVR jadvali bilan o'chadi; B bozori **tegilmaydi** |
| meta | `test_every_criterion_has_its_own_test` | Har mezon uchun **aynan bitta** `test_sc<N>_` funksiyasi; jami 8 |

`pytest tests/integration/test_phase3_criteria.py --collect-only | grep -c "sc[1-8]"` = **8**.
`grep -c "rtsp://" tests/integration/test_phase3_criteria.py` = **0**.

### `hardware` to'plami — bloklamaydi VA ishlaydi

| Da'vo | O'lchov |
|---|---|
| Standart zanjir uni chetlab o'tadi | `pytest --collect-only` -> `test_real_nvr` **0 marta**; `1457/1462 tests collected (5 deselected)` |
| Marker to'planadi | `pytest -m hardware --collect-only` -> **5 test**, exit 0 |
| Rekvizitsiz bloklamaydi | `pytest -m hardware -q` -> `sssss` (5 skip), exit 0 |
| **Haqiqatan bajariladi** | Simulyatorga qaratilganda (`REAL_NVR_URL=http://nvr-sim:8080`) — **5 dan 3 tasi o'tdi** |
| `bash -n verify-real-nvr.sh` | exit 0 |
| Zond chiqishi JSON | `python3 -c "json.load(...)"` -> **VALID JSON** |

**Simulyatorga qaratilgan yugurishning natijasi (bu — TOPILMA, nosozlik emas):**

| Test | Natija | Nima aytadi |
|---|---|---|
| `test_device_info_is_readable` | ✅ | `model='DS-7616NI-K2'`, `type='NVR'`, seriya, `firmware='V4.74.210'`, `manufacturer` BOR |
| `test_channel_list_has_the_expected_shape` | ✅ | 6 kanal, takrorlanish yo'q |
| `test_rtsp_port_is_discovered_not_assumed` | ✅ | 554, **taxmin qilinmagan** |
| `test_every_channel_returns_one_frame` | ❌ | Kadrlar **JPEG** (sehrli baytlar ✅), lekin har biri **160 bayt** — sim `TINY_JPEG` beradi, ya'ni **protokol modeli, piksel emas** |
| `test_three_concurrent_rtsp_sessions` | ❌ | `nvr-sim` 554-portni **umuman tinglamaydi** (RTSP manbasi alohida `go2rtc-sim` da) |

Ikkala qizarish ham 4-faza uchun aniq band: snapshot yo'li va sessiya limiti bugungi sim ustida o'lchab bo'lmaydi.

### Kechikish — YAKUNIY o'lchov (uch martadan)

| O'lchov | Sovuq | Issiq #1 | Issiq #2 | Eng yomon | Chegara |
|---|---:|---:|---:|---:|---|
| `npm run gate:fast` | 75 s | 71 s | 72 s | **75 s** | **180 s** — KO'TARILMADI (2.4× zaxira) |
| `npm run gate` | 1000 s | 994 s | 983 s | **1000 s** | **1200 s** (eng yomon + 20 %) |

Oltala yugurishning **har bir qadami** exit 0.

**Qadam kesimida (eng yomon):**

| Qadam | s | % |
|---|---:|---:|
| `npm run test` | 557 | 56 % |
| `npm run test:tenancy` | 249 | 25 % |
| `npm run test:sim` | 67 | 7 % |
| `npm --prefix frontend test` | 48 | 5 % |
| `next build` | 38 | 4 % |
| eslint / typecheck / lint / i18n | 54 | 5 % |

**⚠ TOPILMA — darvozaning 31 % i QAYTA BAJARISH.** `pyproject.toml` dagi `testpaths = ["tests"]` tufayli `npm run test` `tests/tenancy` va `tests/integration` ni ham qamraydi. `--collect-only` bilan o'lchandi:

```
pytest                                          -> 1457 test
pytest tests/tenancy                            ->  412 test  (1457 ning QISMI)
pytest tests/integration -m "sim and not slow"  ->   70 test  (1457 ning QISMI)
```

Ya'ni `test:tenancy` (249 s) + `test:sim` (67 s) = **316 s** allaqachon bajarilgan testlarni ikkinchi marta bajaradi. **Tuzatilmadi** va sabab ochiq: `package.json` T-03-SC da qulflangan, hamda `test:sim` zanjirga `sim:up --wait` ni olib keladi (usiz sim testlari jimgina skip bo'lardi — T-03-10), `test:tenancy` esa nomlangan signal beradi. Taklif aniq shakli bilan `open_items` ga yozildi.

### Validatsiya imzosi — IKKALA yo'nalishda sinaldi

| Qadam | Natija |
|---|---|
| `node scripts/check-validation-signoff.mjs <03-VALIDATION.md>` | `nyquist_compliant: true — hisob-kitob bilan MOS. Per-Task qatorlari: 33 · inson bandlari: 6`, exit **0** |
| Bayroq qo'lda `false` ga o'zgartirilganda | `HISOB-KITOBGA MOS EMAS (hisoblangani: true)`, exit **1** — ya'ni qiymat **hisoblanadi**, yozilmaydi |
| `npm run validation:check` (2-faza fayli) | exit 0 — regressiya yo'q |
| `npm run requirements:check` | `49 ta talab ... MOS. Done: 9 · Pending: 37 · Blocked: 3`, exit 0 |

### Talablar — dalil bilan

| Band | Holat | Dalil |
|---|---|---|
| **CAM-01** | **Done** | Qo'shish/sozlash — `test_nvr_api.py::test_create_device_returns_the_passport_without_the_password`, `test_phase3_criteria.py::test_sc1_...` va `::test_sc2_...`; shifrlash — `tests/unit/test_nvr_secrets.py` + `::test_sc4_password_never_leaves_the_cipher`; «ulanishni tekshirish» — `test_nvr_errors.py` (12 kod) + `::test_sc3_...` + `frontend/.../nvr-form.test.tsx` |
| **CAM-08** | **Done** | Avtomat kashfiyot — `::test_sc1_...`; idempotentlik — `::test_sc2_...` + `test_nvr_discovery.py`; sabab+tuzatish — `::test_sc3_...` (backend kodi **va** uchala katalog) |
| **CAM-02** | **Blocked** | 2-da'vo («NVR internetga ochilmaydi») o'lchandi: `::test_sc5_...` + `tests/unit/test_nvr_host_validation.py`. **1-da'vo o'lchanmadi** — «server NVR'ga FAQAT tunnel orqali kiradi» CI'da tunnel bo'lmagani uchun sinalmaydi (Pitfall 10). Egasi Ops, tetigi VPS deploy'i, vositasi `ops/scripts/verify-tunnel.sh` |
| **CAM-03** | **Blocked** | Avtorizatsiya zanjiri to'liq: `test_live_view.py` (6 rad etish yo'li) + `::test_sc6_...`; oqim ro'yxatga olinishi — `::test_sc7_...`. **«Tasvirni KO'RADI» qismi o'lchanmadi** — jsdom `RTCPeerConnection` bermaydi va `go2rtc-sim` ning oqimini birorta test iste'mol qilmaydi |
| **CAM-09** | **Blocked** | Profil (`--profile sim`), kashfiyot va ulanish testi o'lchandi (`npm run test:sim` — 70 test). **«Jonli ko'rish» sim ustida uchidan-uchiga sinalmadi** va **«kadr olish yo'li» 4-fazaning mavzusi** |

⚠ **SC#7 yashil, CAM-09 esa `Blocked` — bu ziddiyat EMAS.** SC#7 «yuqoridagi oqim» (SC#1…SC#6) haqida va u o'lchandi; CAM-09 ning jumlasi undan kengroq — u «kadr olish yo'li» ni ham sanaydi, u esa CAM-04…CAM-07 bilan birga 4-fazada.

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `format --check` + `mypy` | ✅ |
| `pytest -q` | ✅ **1457** (1448 → 1457, +9) |
| `pytest tests/tenancy -q` | ✅ **412** (o'zgarmadi) |
| `npm run test:sim` | ✅ **70** (61 → 70, +9) |
| `npm run test:sim:slow` | ✅ **1** (D-09 ning 25 kanalli testi, 26 s) |
| `pytest -m hardware` | ✅ **5 skip** (fazani bloklamaydi) |
| frontend i18n / node / vitest | ✅ **576 × 3** / **86** / **246** (o'zgarmadi — bu reja frontendga tegmadi) |
| typecheck / eslint / build | ✅ |
| **`npm run gate`** | ✅ **exit 0 — uch marta** (1000 / 994 / 983 s) |
| `git diff services/core-api/pyproject.toml frontend/package.json package.json` | ✅ **bo'sh** (T-03-SC) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Bloklovchi] `pyproject.toml` `addopts` ga `-m "not hardware"` qo'shildi**

- **Found during:** Task 2
- **Issue:** Rejaning qabul mezoni «`npm run test` chiqishida `test_real_nvr` testlari bajarilmagan» deydi, lekin `files_modified` da na `pyproject.toml`, na `package.json` bor. Filtrsiz `pytest -q` yangi faylni **to'plardi**.
- **Fix:** Filtr `pyproject.toml` addopts'iga qo'yildi (`package.json` T-03-SC da qulflangan). Buyruq qatoridagi `-m` uni to'liq almashtiradi — **o'lchandi:** `-m hardware --collect-only` → 5 test; standart → `1457/1462 (5 deselected)`; `-m "sim and not slow"` → 70 test.
- **Files modified:** `pyproject.toml`
- **Commit:** `4ccd14b`

**2. [Rule 1 — Xato] `hardware` to'plamining ISAPI yo'llari `/ISAPI` prefiksini IKKI marta yozardi**

- **Found during:** Task 2, to'plamni simulyatorga qaratib sinaganda
- **Issue:** `IsapiClient._url()` `ISAPI_PREFIX` ni O'ZI qo'shadi. `"/ISAPI/System/deviceInfo"` yozilgani `/ISAPI/ISAPI/System/deviceInfo` beradi, qurilma `404` qaytaradi va klient uni **`nvr_isapi_unavailable`** deb tasniflaydi — ya'ni xato «firmware'da ISAPI yo'q» bo'lib ko'rinardi va real qurilmada butunlay noto'g'ri diagnoz qo'yilardi.
- **Fix:** Yo'llar prefikssiz yozildi va sabab konstantalar ustidagi izohda qulflandi.
- **Files modified:** `tests/integration/test_real_nvr.py`
- **Commit:** `4ccd14b`

**3. [Rule 1 — Xato] `verify-real-nvr.sh` RTSP porti sifatida `80` ni qaytarardi**

- **Found during:** Task 2, zondni simulyatorga qaratganda
- **Issue:** Port `adminAccesses` ning BIRINCHI `<portNo>` idan olinardi. Ro'yxatda kamida to'rtta blok bor (HTTP 80, RTSP 554, HTTPS 443, SDK 8000), ya'ni zond `80` ni yozib qo'yardi.
- **Fix:** `<protocol>RTSP</protocol>` blokidan olinadi. **O'lchandi:** `null` → **554**.
- **Files modified:** `ops/scripts/verify-real-nvr.sh`
- **Commit:** `4ccd14b`

**4. [Rule 1 — Xato] Zondning bir vaqtdagi oqim tekshiruvi YOLG'ON-YASHIL berardi**

- **Found during:** Task 2, zondni simulyatorga qaratganda
- **Issue:** `if wait; then OK=true` — POSIX bo'yicha **argumentsiz `wait` HAR DOIM 0 qaytaradi**. Sim 554-portni umuman tinglamaydi, uchala ulanish ham rad etilgan edi, zond esa `concurrent_options_ok: true` yozdi.
- **Fix:** Har PID alohida kutiladi va yiqilganlar sanaladi. **O'lchandi:** `true` → `false`, `concurrent_failed: 3` — bu `pytest -m hardware` ning natijasi bilan **mos**.
- **Files modified:** `ops/scripts/verify-real-nvr.sh`
- **Commit:** `4ccd14b`

**5. [Rule 2 — Yetishmayotgan kritik funksiya] SC#3 har rejimda `drift_seconds` ni ANIQ qo'yadi**

- **Found during:** Task 1, birinchi yugurish
- **Issue:** `POST /__sim__/state` — **qisman** yangilash (03-02): berilmagan maydon tegilmaydi. `clock_drift` (420 s) dan keyingi `basic_only` rejimida farq saqlanib qoldi va diagnostika (soat farqi autentifikatsiyadan **oldin** tekshiriladi) `nvr_clock_drift` qaytardi — test uchinchi rejimni umuman o'lchamagan bo'lardi.
- **Fix:** Har holat `drift_seconds` ni aniq beradi; sabab test docstringida yozildi.
- **Files modified:** `tests/integration/test_phase3_criteria.py`
- **Commit:** `2932c68`

**6. [Rule 2 — Yetishmayotgan kritik funksiya] SC#4 audit qatorlarini `old_value` bilan birga o'qiydi**

- **Found during:** Task 1, birinchi yugurish
- **Issue:** `fixtures.auth_api.audit_rows()` ustunlar ro'yxati SOBIT va unda `old_value` **yo'q**. Parol almashtirilganda eski qiymat aynan `old_value` ga tushardi — ya'ni eng ehtimolli sizish yo'li o'lchanmasdan qolardi.
- **Fix:** Lokal `_audit_blobs()` yordamchisi (`old_value` + `new_value` + `changed_keys`), ilova roli va tenant konteksti bilan.
- **Files modified:** `tests/integration/test_phase3_criteria.py`
- **Commit:** `2932c68`

**7. [Rule 3 — Bloklovchi] `nvr_cleanup` fixture'i qo'shildi**

- **Found during:** Task 1
- **Issue:** Mezon testlari NVR qurilmasini **API orqali** yaratadi, `cleanup_two_markets()` esa `DELETE FROM markets` bilan tugaydi va `nvr_devices` unga chet el kaliti bilan tayanadi — birinchi testdan keyin butun fayl bazani buzilgan holatda qoldirardi.
- **Fix:** `fixtures.nvr_domain.CLEANUP_ORDER` bilan tozalaydigan fixture (tartib **qayta yozilmaydi**).
- **Files modified:** `tests/integration/test_phase3_criteria.py`
- **Commit:** `2932c68`

**8. [Rule 2 — Yetishmayotgan kritik funksiya] SC#4 XATO yo'lini o'lchaydi, muvaffaqiyat yo'lini emas**

- **Found during:** Task 1
- **Issue:** Soxta parol bilan kashfiyot **yiqiladi** va yugurish qatoriga `error_detail` yoziladi — parolning sizib ketishi uchun eng qulay joy aynan shu (03-05 uni allowlist ostiga olgan). Dastlabki yozuvda testda bu natija tekshirilmagan edi.
- **Fix:** `run["status"] == "failed"` va `error_code == "nvr_bad_credentials"` alohida assert bilan qulflandi, keyin javob tanasi parol bo'yicha tekshiriladi.
- **Files modified:** `tests/integration/test_phase3_criteria.py`
- **Commit:** `2932c68`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. `pytest ... -q --collect-only | grep -c "sc[1-8]"` = 8 — BAJARILMAS.**
`pyproject.toml` ning `addopts` ida `-q` **allaqachon bor**; ikkinchisi `-qq` beradi va pytest faqat `tests/integration/test_phase3_criteria.py: 9` degan sanoq qatorini chiqaradi, node ID'larni emas. **Tuzatilgan naqsh (o'lchandi = 8):**
`docker compose --profile test run --rm tests pytest tests/integration/test_phase3_criteria.py --collect-only | grep -c "sc[1-8]"`
Xuddi shu sabab Task 2 ning `pytest -m hardware -q --collect-only` mezoniga ham tegishli.

**B. `grep -c "⬜ pending"` = 0 — jadval LEGENDASIGA urilardi.**
Barcha 33 qator ✅ bo'lgach, faylda `⬜ pending` faqat legenda qatorida qolardi. Legendani o'chirish jadvalni o'qib bo'lmas qilardi. Legenda qayta yozildi (`⬜ hali o'lchanmagan`) — belgining ma'nosi **saqlandi**, naqsh esa **0** beradi.

**C. `grep -c "Kamera va tarmoq ulanishi"` = 0 — tuzatishning O'ZINI yozib bo'lmasdi.**
`REQUIREMENTS.md` ning oxiridagi o'zgarishlar qaydiga eski nomni yozish naqshni qayta qizartirardi. Qayd eski nomni **atamasdan** yozildi, eski qiymat esa shu SUMMARY'da: **«Kamera va tarmoq ulanishi»** → **«NVR avtomatik kashfiyoti va tarmoq ulanishi»**, soni 5 (Traceability qatorlaridan qayta hisoblandi).

**D. `npm run validation:check` FAZA ARGUMENTINI olmaydi.**
Alias 2-fazaning fayliga qadalgan (`scripts/check-validation-signoff.mjs` ning `DEFAULT_FILE` i). 3-faza uchun `npm run validation:check -- <yo'l>` ishlatildi — `package.json` **tegilmadi** (T-03-SC). Ikkala chaqiruv ham exit 0.

**E. Task 2 ning `docker compose ... pytest -m hardware -q --collect-only` verifysi konteynerdan tashqarida ham bajarildi.**
`--profile test` konteynerida `curl` **yo'q**, ya'ni `verify-real-nvr.sh` ni o'sha yerda sinab bo'lmadi. Zond `alpine:3.20` konteynerida, `sbozor_default` tarmog'ida, `nvr-sim` ga qaratib bajarildi va JSON validligi tasdiqlandi.

### Rejadan ataylab chetlangan bandlar

**F. `requirements mark-complete` SDK buyrug'i ishlatilmadi.** `REQUIREMENTS.md` qo'lda tahrirlandi, chunki beshala CAM bandidan uchtasi `Done` **emas**, `Blocked (<sabab>)` bo'lishi kerak edi va SDK buyrug'i faqat `Done` yozadi. Natija baribir **mexanik tekshirildi**: `npm run requirements:check` exit 0 (`Done: 9 · Pending: 37 · Blocked: 3`).

**G. TDD RED/GREEN commitlari ajratilmadi.** Task 1 va Task 2 `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02…03-10) — har task uchun bitta commit. **RED dalili yo'qolmadi:** ikkala sabotaj ham darvozalarning kodsiz qizarishini o'lchov bilan ko'rsatadi.

**H. 31 % qayta bajarish TUZATILMADI.** Sabab va taklif yuqorida hamda `03-VALIDATION.md` ning `open_items` ida. Bu **Rule 4** (strukturaviy o'zgarish): u `package.json` ni o'zgartiradi, `test:sim` ning `sim:up --wait` xususiyatini va `test:tenancy` ning nomlangan signalini yo'qotadi — qaror egasi 4-faza.

---

**Total deviations:** 8 auto-fixed (4 × Rule 1, 3 × Rule 2, 2 × Rule 3 — ikkitasi bitta bandda sanalgan) + 5 ta rejadagi ziddiyat + 3 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. To'rtala Rule 1 tuzatishi ham **haqiqiy xatolarni** yopdi va ularning uchtasi to'plamni/skriptni **haqiqiy nishonga qaratib ishga tushirish** natijasida topildi — ya'ni «bloklamaydigan to'plamni bir marta bajarish» qoidasi darhol qaytim berdi.

## 03-10 dan meros qolgan beshta ochiq band — YOPILDI

| # | Band | Qaror | Dalil |
|---|---|---|---|
| 1 | **Darvoza vaqti 950 s, chegara 618 s** | Uch martadan o'lchandi, chegara **1200 s** qilib belgilandi va o'sishning **31 % i** nomlandi | Yuqoridagi jadvallar; `--collect-only` bilan isbot |
| 2 | **`requirements mark-complete`** | CAM-01 va CAM-08 **`Done`**; CAM-02/03/09 **`Blocked`**, yetishmayotgan dalil har birida nomlangan | `npm run requirements:check` exit 0 |
| 3 | **`Go2rtcClient.remove_stream` chaqirilmaydi** | **QABUL QILINDI.** Qoldiq ta'sir chegaralangan va **o'lchangan**: arxivlangan kamera token so'rovida **404** oladi (`test_live_view.py::test_archived_camera_has_no_live_token`), ya'ni yangi oqim ochilmaydi; go2rtc ro'yxati **xotirada** yashaydi va servis qayta ishga tushganda yo'qoladi; `rtsp_url()` parolni umuman qabul qilmaydi, ya'ni yetim yozuvda sir yo'q. Arxivlash marshrutiga tarmoq chaqiruvini qo'shish uni go2rtc **mavjudligiga** bog'lardi (go2rtc sekin bo'lsa arxivlash osilardi) — yomonroq savdo. To'g'ri shakl — **4-fazada reconciliation** | `open_items` ning 4-bandi |
| 4 | **`audit-volume` remediatsiyasi** | **QABUL QILINDI o'lchov bilan.** Karmana miqyosida (25 kamera) `last_seen_at` + jonli ko'rish yangilanishlari ≈ **75 qator/kun**, ya'ni **~27k qator ≈ 14 MB/yil/bozor** — 400 GB diskda ahamiyatsiz. Bugungi holatda skan **admin bosgan** paytda bo'ladi (cron 4-fazada), ya'ni haqiqiy hajm bundan ham kam. Remediatsiya (ustun bilan cheklangan trigger) **ma'lum va arzon**, lekin u `migrations/helpers.py` orqali **barcha** audit ostidagi jadvallarga tegadi (Rule 4). **Qayta ochish sharti nomlandi:** skan CRON'ga o'tganda (4-faza) yoki bozorlar soni o'ntadan oshganda | `open_items` ning 3-bandi |
| 5 | **Sim testlari Postgres testcontainer'ini ko'taradi** | **O'LCHANDI va RAD ETILDI.** `npm run test:sim` ning **70** testidan **32 tasi (46 %)** bazani haqiqatan talab qiladi (`test_nvr_discovery.py` 13, `test_phase3_criteria.py` 9, `test_nvr_discovery_job.py` 7, `test_nvr_api.py` 3), ya'ni konteyner **baribir** ko'tariladi. 03-02 ning prototipi (23.2 s → 16.8 s) faqat **yolg'iz fayl** uchun foyda berardi. Haqiqiy lever — 1-banddagi **31 % qayta bajarish** (316 s), ya'ni bu yo'nalishga vaqt sarflash noto'g'ri ustuvorlik bo'lardi | Per-fayl collect sanog'i yuqorida |

## Issues Encountered

1. **Bloklamaydigan to'plamni yozib, ishga TUSHIRMASLIK — eng oson tuzoq.** To'plam `sssss` bergani «ishlaydi» degani emas: uni simulyatorga qaratib bir marta bajarish **ikkita haqiqiy xatoni** topdi (ISAPI prefiksining ikkilanishi va zonddagi yolg'on-yashil `wait`). Ikkalasi ham real qurilma kelgan kuni «firmware nosoz» degan noto'g'ri diagnozga olib kelardi.
2. **`grep` mezonlari bu fazada YANA uch marta kod bilan ziddiyatga kirdi** (`-q` ning ikkilanishi ikki joyda, legenda qatori, o'zgarish qaydidagi eski nom). Bu sinf 03-08 dan beri **o'n uchinchi–o'n beshinchi** marta uchradi. Umumiy sabab bitta: naqsh yozilganda **konfiguratsiyadagi standart bayroqlar** va **hujjatning o'z matni** hisobga olinmaydi.
3. **Sim'ning control-plane'i QISMAN yangilaydi va bu testlar orasida meros qoldiradi.** `sim_mode(url, "basic_only")` oldingi testning `drift_seconds` ini **tozalamaydi**. `sim` fixture'i testlar orasida `reset` qiladi, lekin BIR test ichidagi ketma-ket rejimlar himoyalanmagan.
4. **`npm run test` ning natijasi ambient holatga bog'liq.** Sim konteynerlari ko'tarilgan bo'lsa u 70 sim testini ham bajaradi; ko'tarilmagan bo'lsa ularni **jimgina skip** qiladi (dev qoidasi). Ya'ni `npm run test` ning **davomiyligi ham, qamrovi ham** o'zgaruvchan — bu 31 % qayta bajarish topilmasining ikkinchi tomoni.

## Known Stubs

| Joy | Stub | Nega bu fazada yetarli | Kim yopadi |
|---|---|---|---|
| SC#5 ning 3-da'vosi (`ip route get` → `wg0`) | Test uni **bajarmaydi**, faqat vositasining mavjudligini tekshiradi | CI'da `wg0` interfeysi umuman yo'q — bunday test har doim yashil bo'lardi va hech nima isbotlamasdi (Pitfall 10) | Ops, VPS deploy'idan keyin (`03-VALIDATION.md` Manual-Only) |
| `go2rtc-sim` ning oqimi | Konteyner haqiqiy RTSP test-oqimlarini beradi, lekin **birorta test undan kadr olmaydi** | Bu fazaning mezonlari media UZATISHNI emas, AVTORIZATSIYANI va ro'yxatga olishni talab qiladi | **4-faza** — CAM-03/CAM-09 ning `Blocked` sababi aynan shu |
| `setup-status.cameras` sanog'i | Hamon `—` (03-08 dan meros) | Backend maydonni har doim `0` qaytaradi; birorta mezon unga tayanmaydi | 4-faza |

## Threat Flags

Yangi ishonch chegarasi **ochilmadi**: bu reja ilova kodiga umuman tegmadi (`services/core-api/app/` diffi **bo'sh**), yangi tarmoq yuzasi, sxema o'zgarishi yoki paket qo'shilmadi. Reja `<threat_model>` idagi **yettala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-76 (mezonlar zanjir sifatida o'lchanmasligi) | ✅ `test_sc7_...` butun zanjirni bir sessiyada kesib o'tadi; meta-test sakkizala mezon uchun **aynan bitta** test borligini majburlaydi va **sabotaj S2** bilan o'lchandi |
| T-03-77 (SC#1 ning faqat natija bo'yicha tekshirilishi) | ✅ Test **o'z manba matnini** o'qiydi; izlanadigan satr `rtsp_url()` ning chiqishidan olinadi, faylda **yozilmaydi** (`grep -c` = 0); chegara docstringda |
| T-03-78 (`nyquist_compliant` ning qo'lda yozilishi) | ✅ Skript hisobladi (exit 0) **va** `false` ga o'zgartirilganda exit 1 berdi — ikkala yo'nalish ham o'lchandi |
| T-03-79 (kechikishning jimgina o'sishi) | ✅ Ikkala lenta ham **uch martadan**; chegara o'lchovdan; o'sishning 31 % i **nomlandi** va taklif yozildi; `gate:fast` chegarasi ko'tarilMADI |
| T-03-80 (talabning o'lchanmagan holda `Done` belgilanishi) | ✅ Beshtadan **ikkitasi** `Done`; uchtasining yetishmayotgan dalili NOMLANGAN; `requirements:check` mexanik moslikni tasdiqladi |
| T-03-81 (runbookda muhandis aralashuvi qadami) | ✅ `grep -ci "ssh"` = **0**; admin 7 qadam, on-site odam **2 qadam**; yagona skript qadami (§4) mahsulot oqimidan **tashqarida** deb ochiq belgilangan |
| T-03-SC (npm/pip o'rnatishlari) | ✅ `git diff --exit-code services/core-api/pyproject.toml frontend/package.json package.json` — **bo'sh** |

## Next Phase Readiness

**4-faza (snapshot pipeline) uchun TAYYOR:**

- **Kadr olish usuli bo'yicha zond allaqachon yozilgan:** `test_real_nvr.py::test_every_channel_returns_one_frame` ISAPI `/picture` yo'lini har kanal uchun sinaydi va `verify-real-nvr.sh` uni JSON'da qayd etadi. Rekvizit kelgan kunning O'ZIDA ROADMAP'ning 1-ochiq qarori yopiladi.
- **`cameras.id` barqaror**, `last_seen_at` UI'da ko'rinadi, `rtsp_port_assumed` diagnostikasi tayyor.
- **`nvr-sim` va `go2rtc-sim` ko'tarilgan holatda** — snapshot yo'lining birinchi testi ularni darhol ishlata oladi.

**4-faza uchun OCHIQ bandlar (barchasi `03-VALIDATION.md` `open_items` da):**

1. **Darvozaning 31 % i qayta bajarish** — taklif: `sim:up` ni zanjir boshiga, `test:tenancy` va `test:sim` ni `gate` dan olib tashlash (~316 s tejaydi, qamrovni kamaytirmaydi).
2. **`go2rtc-sim` oqimini iste'mol qiladigan test** — CAM-03 va CAM-09 ni `Blocked` dan chiqaradigan yagona narsa.
3. **Audit hajmi** — qayta ochish sharti: skan CRON'ga o'tganda yoki bozorlar > 10.
4. **go2rtc reconciliation** — arxivlangan kameralarning yetim oqimlarini davriy tozalash (`remove_stream` uchun to'g'ri joy).
5. **`gate:fast` ning zaxirasi 5.6× dan 2.4× ga tushdi** — bugun band emas, lekin trend kuzatilsin.

**Faza tekshiruvchisi uchun:** sakkizala mezon `docker compose --profile test run --rm tests pytest tests/integration/test_phase3_criteria.py` bilan bitta buyruqda bajariladi; `hardware` markeri ATAYIN darvozadan tashqarida; uchta talabning `Blocked` bo'lishi **fazani bloklamaydi** (ROADMAP self-service qoidasi), lekin ular fazaning haqiqiy chegarasini ko'rsatadi.

## Self-Check: PASSED

- **Fayllar:** 8/8 mavjud (4 yangi + 4 o'zgargan) + SUMMARY
- **Commitlar:** 3/3 mavjud (`2932c68`, `4ccd14b`, `1046685`)
- **`must_haves.artifacts`:** `test_phase3_criteria.py` — `SC#` 30 marta, 1078 qator (talab 200); `nvr-onboarding.md` — `tunnel_subnet` 2; `verify-real-nvr.sh` — `deviceInfo` 2; `03-VALIDATION.md` — `nyquist_compliant` 6
- **`must_haves.key_links`:** 2/2 — `sim` markeri (`test_phase3_criteria.py` `pytestmark`, haqiqiy TCP orqali `nvr-sim` + go2rtc oqim manbasi); `CAM-0` (`REQUIREMENTS.md`, beshala band + `requirements:check`)
- **Qabul mezonlari:** `sc[1-8]` collect = **8**; `rtsp://` = **0**; `⬜ pending` = **0**; `[ ] **W0-` = **0**; `tunnel_subnet` = 2; `1:1 NAT` = 2; `SSH` = **0**; `bash -n` exit 0; `validation:check` exit 0 (ikkala fayl); `requirements:check` exit 0
- **`npm run gate`:** ✅ exit 0 — **uch marta** (1000 / 994 / 983 s), har qadamning exit kodi 0
- **Ish daraxti:** ikkala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
