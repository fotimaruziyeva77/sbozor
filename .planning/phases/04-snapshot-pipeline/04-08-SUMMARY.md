---
phase: 04-snapshot-pipeline
plan: 08
subsystem: backend
tags: [retention, alerting, telegram, debounce, heartbeat, secret-filter, cam-07, found-06, d-18, d-19, d-20, d-21, d-22]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`Settings` ning retention/telegram maydonlari, `object_key()`, `capture_errors` reyestri VA `censor_secrets` ning O'LCHANGAN qamrov teshigi"
  - phase: 04-snapshot-pipeline
    plan: 05
    provides: "`snapshot_repo.retention_candidates`/`mark_compressed`/`mark_purged` — bir yo'nalishli holat o'tishlari; `capture_repo.day_summary`"
  - phase: 04-snapshot-pipeline
    plan: 06
    provides: "`storage.get`/`put`/`delete_many`/`list_prefix`/`orphan_keys` va `Quiet` SIZ `delete_objects` (o'lchangan qaror)"
  - phase: 04-snapshot-pipeline
    plan: 07
    provides: "`capture_runs` ning `missed` qatori (D-20 ning YAGONA manbai), `worker.py` planeri, `_system_transaction` naqshi"
  - phase: 04-snapshot-pipeline
    plan: 03
    provides: "`alert_events` + qisman UNIQUE indeks, `system_heartbeats`, `auth_list_markets_full()`"
provides:
  - "`app/jobs/retention.py` — `retention_daily()`: siqish, arxivdan chiqarish va yetim supurgisi; vaqt IN'EKTSIYA qilinadi"
  - "`RetentionPolicy` / `RetentionResult`, `RETENTION_COMPONENT`, `active_market_ids()`, `disk_usage_percent()`"
  - "`app/services/alerts.py` — `AlertSender`: bitta metod (`send_message`), sirsiz `AlertError`, `bool` kontrakti; rasm biriktiruvchi metod STRUKTURAVIY ravishda YO'Q"
  - "`app/jobs/alerting.py` — `alert_sweep()` / `daily_digest()`; `ALERT_META` reyestri va undan HOSILA `NEVER_SUPPRESSED_ALERT_KEYS` / `PLATFORM_SCOPED_ALERT_KEYS` / `STORABLE_ALERT_KEYS`"
  - "`ALERT_DETAIL_KEYS` — `alert_events.detail` ning ALLOWLIST'i (D-19 ning yozish paytidagi chegarasi)"
  - "`app/worker.py` — `retention.daily` / `alert.sweep` / `alert.digest` qobiqlari, uchalasida ham `cron_offset`; `AlertSender` worker resursi"
  - "`ops/docs/monitoring.md` — D-21 ning bajarilishi: uch qatlam, HALOL chegara, tashqi ping yo'riqnomasi, uch ops bandi"
  - "`SENSITIVE_KEYS` — 04-04 O'LCHAGAN sir oqishi YOPILDI (`telegram_bot_token`, `s3_access_key`, `s3_secret_key`)"
affects: [04-09, 04-10, 04-11, 04-12, 05-cv-zonalar, 06-billing, 08-backup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vaqt IN'EKTSIYA qilinadi, SILJITILMAYDI: `retention_daily(..., today=)` va `alert_sweep(..., now=)` — 90 kun ham, 3 soatlik eskalatsiya ham `freezegun`siz o'lchanadi"
    - "Ikkinchi darvoza sabotajni YUTIB YUBORISHI mumkin: `retention_candidates` ning tier predikatini olib tashlash HECH NIMANI qizartirmadi, chunki `mark_compressed()` ning O'Z predikati QATORNI himoya qiladi — lekin OBYEKT himoyalanmagan edi"
    - "Sanoq maydoni darvozaga aylanadi: `RetentionResult.not_smaller` («enkoder chaqirildi va foyda bermadi») — sabotaj tomonidan qizartiriladigan YAGONA o'lchov"
    - "Xavfsizlik YUZASI takrorlanmaydi, STRUKTURAVIY naqsh esa takrorlanadi: `active_market_ids()` (RLS ni chetlab o'tadi) BITTA joyda, `_tenant_session` esa uch modulda ATAYIN nusxa"
    - "Test shartidagi shovqin MAHSULOT xulqidan ajratiladi: platforma alertlari (`backup`/`retention` yurak urishlari yo'q) guruhlash o'lchovini buzardi — fixture ularni YANGI qilib qo'yadi va `test_stale_heartbeat_alerts` ularni ALOHIDA o'lchaydi"
    - "Bostirilmaydigan alert debounce testini buzadi: 22 kameralik stsenariy `camera_offline` ni ham ko'taradi va u `NEVER_SUPPRESSED` — debounce testi chegaradan PAST stsenariy talab qiladi"

key-files:
  created:
    - services/core-api/app/jobs/retention.py
    - services/core-api/app/jobs/alerting.py
    - services/core-api/app/services/alerts.py
    - ops/docs/monitoring.md
    - tests/integration/test_retention.py
    - tests/integration/test_alerting.py
  modified:
    - services/core-api/app/worker.py
    - packages/sbozor-core/sbozor_core/logging.py
    - tests/unit/test_snapshot_settings.py
    - tests/integration/test_capture_tick.py
  deleted: []

key-decisions:
  - "⛔ D-19 STRUKTURAVIY: rasm biriktiruvchi Telegram metodi UMUMAN yozilmadi. Taqiq IKKI darvoza bilan: `dir(AlertSender)` da tegishli a'zo yo'q (struktura) VA `respx` tutgan barcha so'rovlar `/sendMessage` bo'lib, tanasida faqat to'rt kalit bor (xulq). Uchinchi qatlam — `ALERT_DETAIL_KEYS` allowlist'i YOZISH paytida"
  - "REJANING SABOTAJI 1 HECH NIMANI QIZARTIRMADI va sabab MAHSULOTNING IKKINCHI DARVOZASI edi. `mark_compressed()` ning `storage_tier='full'` sharti (04-05) qatorni himoya qiladi, ya'ni `result.compressed` baribir 0 chiqadi. OBYEKT esa himoyalanmagan edi — kengaytirilgan predikat bilan u enkoderga QAYTA beriladi. Nazorat `not_smaller` sanog'i bilan kuchaytirildi va sabotaj AYNAN 1 testni qizartiradigan bo'ldi"
  - "Bozorlar ro'yxati `auth_list_markets_full()` dan, `capture_due_markets()` dan EMAS. Ikkinchisi «qaysi bozorda HOZIR ish bor» ni beradi va uning uchala disjunkti ham BUGUNGI kadr olish rejasiga qaraydi — tik rejani materializatsiya qilib bo'lgach bozor undan CHIQMAYDI. Retention 03:20 da ishlaydi, ya'ni u JIMGINA hech nima ko'rmasdi"
  - "Tozalash `PURGEABLE_TIERS` ning IKKALA a'zosidan (reja faqat `compressed` degan edi). Sabab `snapshot_repo.py` ning O'Z docstringida: siqishdan o'tolmagan kadr (buzuq obyekt, ombor xatosi) `full` bo'lib qoladi va faqat `compressed` ni tozalash uni MANGU saqlab qolardi — jimgina"
  - "`RetentionPolicy` qo'shildi (reja imzosida yo'q edi): `CapturePolicy` (04-07) va `QualityThresholds` (04-04) bilan bir xil qaror — job `Settings` ning butun yuzasini ko'rmasligi kerak, aks holda `full_days=0` bilan test qurish uchun `DATABASE_URL`/`JWT_SECRET`/`NVR_CREDENTIAL_KEY` kerak bo'lardi"
  - "Qayta kodlash natijasi KATTAROQ chiqsa obyekt TEGILMAYDI, lekin qator BARIBIR `compressed` deb belgilanadi. Ikkinchi qism majburiy: aks holda o'sha kadr HAR KECHA qayta urinilardi va har safar yana bir avlod yo'qotardi — «ehtiyotkorlik» aynan o'zi oldini olayotgan zararni keltirardi"
  - "`camera_offline` IKKI mustaqil yo'ldan tug'iladi: per-kamera (3 ketma-ket slot, `subject_id` = kamera) va butun bozor (bitta slotda >=30 %, `subject_id` = `NULL`). 22 kamera bitta slotda yiqilganda faqat ikkinchisi ishlaydi va u BITTA qator beradi, 22 ta emas"
  - "Platforma alertlari (`backup_stale`, `retention_stale`, `disk_pressure`) HAR BOZORGA qator sifatida yoziladi (UI ularni bozor sahifasida ko'rsatadi), lekin Telegram xabari bozorlar bo'ylab BIRLASHTIRILADI — aks holda bitta zaxira nosozligi N ta xabar berardi"
  - "`04-07` ning `schedule=[` sanog'i TORAYTIRILDI, susaytirilmadi. Uning haqiqiy da'vosi hech qachon «jadval bitta» bo'lmagan — u «DAQIQALIK cron oqimi bitta» edi. Yangi shakl konstantalarni MAHSULOT modulidan yechadi va `\"*/1 * * * *\"` variantini ham ushlaydi"

patterns-established:
  - "Pattern: sabotaj natija bermasa, u AVVAL ikkinchi darvoza borligini bildiradi — darvozani izlash va uni AYNAN qizartiradigan yangi o'lchov qo'shish (04-04/04-06/04-07 ning uchinchi takrori)"
  - "Pattern: test shartidagi SHOVQIN (bo'lmagan yurak urishlari) mahsulot xulqi bilan aralashib ketmasligi kerak — fixture uni bartaraf qiladi va ALOHIDA test uni o'z holicha o'lchaydi"
  - "Pattern: «bostirilmaydigan» xususiyat debounce testini BUZADI, ya'ni debounce chegaradan PAST stsenariyda o'lchanadi (aks holda test o'z farazini emas, D-22 ning istisnosini o'lchardi)"
  - "Pattern: o'zini bekor qiladigan test AG'DARILADI, o'chirilmaydi — `04-04` ning «qamramaydi» testi «qamraydi» testiga aylandi va yoniga yolg'on-musbatga qarshi NAZORAT test qo'shildi"

requirements-completed: [CAM-07, FOUND-06]

# Metrics
duration: 1h 45m
completed: 2026-08-05
---

# Phase 4 Plan 08: Saqlash siyosati va o'zini kuzatish Summary

**Fazaning ikkinchi yarmi jonlandi va uning uchala eng qattiq da'vosi HAQIQIY konteynerlarda o'lchandi: kadr 90 kunni KUTMASDAN siqiladi (o'lchamlari saqlanadi, kaliti o'zgarmaydi, ikkinchi marta siqilmaydi), muddati tugagan obyekt arxivdan chiqadi va QATOR qoladi, 22 kameralik yiqilish esa 22 ta emas, AYNAN BITTA Telegram xabari beradi. `04-04` o'lchagan sir oqishi yopildi va uning o'zini bekor qiladigan testi ag'darildi; D-19 uch mustaqil qatlamda majburlandi — rasm biriktiruvchi metod umuman yozilmadi, `respx` barcha so'rovlarni tekshiradi va `detail` kalitlari YOZISH paytida allowlist ostida.**

## Performance

- **Duration:** ~1 soat 45 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 10 (6 yangi, 4 o'zgartirilgan) — 2 251 qator ishlab chiqarish kodi, 32 yangi test
- **Commits:** 3

## Task Commits

| # | Task | Commit | Turi |
|---|------|--------|------|
| 1 | `retention.py` + 16 test | `6b8f06c` | `feat` |
| 2 | `alerts.py` + `SENSITIVE_KEYS` + `04-04` testining ag'darilishi | `9dfb704` | `feat` |
| 3 | `alerting.py` + `worker.py` + `monitoring.md` + 15 test | `bfbaa1f` | `feat` |

## ⛔ D-19 — FAZANING ENG QATTIQ MAXFIYLIK QOIDASI, UCH QATLAMDA

Alertga kadr rasmi HECH QACHON biriktirilmaydi. Sabab ikki qatlamli va ikkalasi ham huquqiy: dalil-kadrlar bozor tashrifchilarining **shaxsiy ma'lumoti**, Telegram serverlari esa loyiha zimmasiga olgan **O'zR data-rezidentlik chegarasidan tashqarida** — yuborilgan baytni **qaytarib bo'lmaydi**.

| # | Qatlam | Mexanizm | O'lchov |
|---|--------|----------|---------|
| 1 | **STRUKTURA** | `AlertSender` da rasm biriktiruvchi metod **umuman yozilmagan**; `dir()` da tegishli a'zo yo'q | `dir(AlertSender)` -> `['aclose', 'enabled', 'send_message', ...]` — mos a'zo **0 ta** |
| 2 | **MATN** | Faylda tegishli literal izohsiz tanada **umuman uchramaydi** | matn darvozasi exit 0 |
| 3 | **XULQ** | `respx` tutgan **barcha** so'rovlar `/sendMessage` bilan tugaydi, tanasi `{chat_id, text, parse_mode, disable_web_page_preview}` bilan cheklangan, matnda `http` ham, `.jpg` ham yo'q | `test_no_request_ever_carries_an_image` |
| 4 | **YOZISH** | `alert_events.detail` **ALLOWLIST** ostida (`ALERT_DETAIL_KEYS`, olti kalit) — ro'yxatdan tashqari kalit `ValueError` beradi | `test_the_detail_allowlist_matches_the_ui_contract` |

Uchinchisi ikkinchisining o'rnini bosmaydi: metod bir kun qo'shilsa, matn darvozasi uni **yozilgan** paytda, `respx` esa **ishlatilgan** paytda ushlaydi. To'rtinchisi esa boshqa yuzani yopadi — UI noma'lum kalitni render qilmaydi, lekin u **bazaga baribir yozilardi** va u yerdan zaxiraga, zaxiradan tashqi bucketga chiqardi.

## ⛔ `04-04` NING O'LCHANGAN SIR OQISHI YOPILDI

`04-04-SUMMARY.md` bu bandni aniq o'lchov bilan qoldirgan edi:

```
censor_secrets(None, "info", {"s3_access_key": …, "s3_secret_key": …,
                              "telegram_bot_token": …})
    ->  covered == set()        # UCHALASI HAM SENZURADAN O'TDI
```

Sabab: `SENSITIVE_KEYS` — **aniq nomlar ro'yxati, naqsh emas** (`_is_sensitive`: `str(key).lower() in SENSITIVE_KEYS`), ya'ni `*_key`/`*_token`/`*_secret` shakli avtomatik qamralmaydi. `SecretStr` bu yo'lni **yopmaydi** — u `repr(settings)` ni yopadi, structlog kalitini emas.

**Yopildi va bandning o'zi ham yopildi:** uchala nom `SENSITIVE_KEYS` ga qo'shildi va `04-04` ning **o'zini bekor qiladigan testi** (`test_log_filter_coverage_of_the_new_secret_names_is_measured`) **ag'darildi** — u endi qamrovning **mavjudligini** talab qiladi va nom `test_log_filter_covers_the_phase_four_secret_names` ga o'zgardi.

⚠ **Yoniga NAZORAT test qo'shildi** (rejada yo'q edi): `test_the_secret_filter_still_ignores_non_secret_key_shaped_names`. Naqshga (`har qanday *_key`) o'tish vasvasasi tabiiy, lekin u `object_key` ni ham maskalardi — retention, dalil zanjiri va ombor diagnostikasining hammasi o'sha kalitga tayanadi va ular jurnalda `***` bo'lib qolardi. Yolg'on-musbat senzura nosozlikni **topib bo'lmaydigan** qiladi.

**Tirik tasdiq (sabotaj 2 ning jurnalidan):** xom `httpx` istisnosi to'liq URL'ni tokeni bilan tashiydi (`... for url 'https://api.telegram.org/bot1234567890:TEST-TOKEN-NEVER-REAL/sendMessage'`), bizning jurnal satrimiz esa faqat `error='telegram \`sendMessage\` yiqildi: HTTPStatusError (status=500)'` beradi.

## SABOTAJ O'LCHOVLARI — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

Bu loyihada ikkinchi ustun qayta-qayta birinchisidan ko'ra ko'proq ma'lumot bergan.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---------|---------|--------------|---------------------|
| 1a | `retention.py`: siqish nomzodlari `COMPRESSIBLE_TIER` -> `PURGEABLE_TIERS` | **HECH NIMA — 16/16 YASHIL** | hammasi | ⚠ **Reja «ikkinchi yugurish qayta siqmaydi» testini AYNAN qizartiradi degan edi — NOTO'G'RI.** Sabab pastda |
| 1b | O'sha sabotaj, `not_smaller` nazorati qo'shilgandan keyin | **AYNAN 1 test**: `test_a_second_run_does_not_compress_the_frame_again` (`assert 1 == 0`) | **15 test**, jumladan IKKALA tozalash testi | Endi bashorat aynan bajarildi va u KUCHLIROQ shaklda |
| 2 | `alerting.py`: debounce sharti (`notified_at <= debounce_before`) `True` ga almashtirildi | **AYNAN 1 test**: `test_a_repeat_inside_the_debounce_window_sends_nothing` | **14 test**, jumladan `test_stale_heartbeat_alerts` VA `test_missed_slots_are_grouped` | ⚠ Reja `test_missed_slots_are_grouped` ni nomlagan edi — u YASHIL QOLDI, chunki u BITTA supurgi qiladi. Debounce esa supurgilar ORASIDA yashaydi |
| 3 | `capture.py`: bloklovchi Telegram chaqiruvi tikning tranzaksiyasi ICHIGA ko'chirildi | **AYNAN 1 test**: `test_telegram_failure_does_not_block_capture` (`httpx.HTTPStatusError` tikdan chiqdi) | **14 test**, jumladan `test_missed_slots_are_grouped` | ✅ **AYNAN bashorat qilingandek** |

Uch holatda ham fayl **`cp` bilan olingan nusxadan** tiklandi (`git checkout --` ATAYIN ishlatilmadi — 04-07 ning darsi) va to'plam qayta yashil bo'ldi.

### ⚠ 1-SABOTAJNING TOPILMASI — REJANING FARAZI YARIM NOTO'G'RI EDI

Predikatni kengaytirish **hech qanday testni qizartirmadi** va sabab **mahsulotning ikkinchi darvozasida** edi:

```
retention_candidates(tier=COMPRESSIBLE_TIER)   <- 1-darvoza (bu rejaning)
mark_compressed(...) WHERE storage_tier='full' <- 2-darvoza (04-05 niki)
```

Ikkinchi darvoza **QATORNI** himoya qiladi: allaqachon siqilgan qator yangilanmaydi va `result.compressed` baribir `0` chiqadi. **Lekin OBYEKT himoyalanmagan edi** — kengaytirilgan predikat bilan `compressed` kadr **enkoderga qayta beriladi**. Bu yugurishda u omborga yozilmadi (natija kichraymadi), ya'ni zarar **ko'rinmadi** — sifat sozlamasi boshqa bo'lgan har qanday holatda esa obyekt ustiga **ikki marta siqilgan** versiya yozilardi va baza **eski hajmni** ko'rsatib turardi.

**Yechim:** `RetentionResult.not_smaller` (mahsulotdagi sanoq, «enkoder chaqirildi va foyda bermadi») testga assert sifatida qo'shildi. U sabotaj tomonidan qizartiriladigan **yagona** o'lchov, ya'ni nazorat aynan **so'nggi qatlamdan o'ta oladigan** kirish bilan qurildi — `04-04` ning 2a/2b darsi, uchinchi marta takrorlandi.

## O'LCHOVLAR — taxmin qilinmadi

| Savol | O'lchangan javob | Qarorga ta'siri |
|---|---|---|
| 1280x720 @ q92 kadr q60 ga qayta kodlanganda? | **37 167 -> 11 416 bayt** (−69 %), o'lchamlar AYNAN `(1280, 720)` | Siqish HAQIQATAN ishlaydi va geometriya saqlanadi |
| Siqilgan kadrni YANA q60 bilan kodlash? | **11 416 -> 11 416** (aynan teng) | «Kattaroq chiqsa yozmaymiz» shoxi ISHLAYDI va u `not_smaller` ni beradi |
| `capture_due_markets()` 03:20 da nima qaytaradi? | Reja materializatsiya qilingach — **hech nima** (ikkinchi disjunkt yolg'on) | Retention `auth_list_markets_full()` ga o'tdi |
| Yurak urishi YOZILMAGAN holat (`backup`)? | `None` -> `backup_stale` alerti **tug'iladi** | «alert on absence of a success signal» ning bevosita shakli |
| Supurgi test muhitida nechta xabar yuboradi? | **2** (bozor + platforma), 1 emas | Fixture platforma yurak urishlarini yangi qiladi; platforma xulqi ALOHIDA testda |
| 22 kameralik stsenariy debounce testiga to'g'ri keladimi? | **YO'Q** — 88 % `camera_offline` ni ko'taradi va u `NEVER_SUPPRESSED` | Debounce testi 5 kamera (20 % < 30 %) bilan yoziladi |
| `AsyncRetrying(...)` ning qaytish tipi mypy uchun? | **`Any`** — aniq annotatsiya talab qilinadi | `response: httpx.Response = await retrying(...)` |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm run sim:up && pytest tests/integration/test_retention.py -m sim -q` | **16 test**, exit 0 (talab >= 9) |
| 2 | `pytest tests/integration/test_alerting.py -q` | **15 test**, exit 0 (talab >= 10) |
| 3 | Rejaning uch nomli testi (`test_missed_slots_are_grouped`, `test_stale_heartbeat_alerts`, `test_telegram_failure_does_not_block_capture`) | exit 0 |
| 4 | `grep -cE '^\s*(import\|from)\s+taskiq' retention.py alerting.py` | **0 / 0** (S-4) |
| 5 | `retention.py`: stdlib sana chaqiruvi / `.resize(`/`thumbnail(` / qator o'chirish literallari | **uchalasi ham YO'Q** |
| 6 | `alerts.py`: rasm literali yo'q; `get_secret_value()` sanog'i **1**; `from None` bor; `_failure` tanasida interpolyatsiya ham, `TOKEN` ham yo'q | exit 0 (to'rtala darvoza) |
| 7 | `dir(AlertSender)` da rasmga tegishli a'zo | **0 ta** |
| 8 | `SENSITIVE_KEYS >= {telegram_bot_token, s3_access_key, s3_secret_key}` | **True** |
| 9 | `worker.py` da `cron_offset` sanog'i | **5** (talab >= 3) |
| 10 | `NEVER_SUPPRESSED_ALERT_KEYS` inline `frozenset({...})` literali | **yo'q** — metadan hosila |
| 11 | `monitoring.md` da `self-check` va `healthcheck` | **ikkalasi ham bor** |
| 12 | `ruff check . && ruff format --check . && mypy .` | exit 0 — **241 fayl formatlangan, 234 fayl tiplangan** |
| 13 | `pytest` (to'liq) | **1 787 passed**, 5 deselected, exit 0 (talab >= 1 520) |
| 14 | `pytest tests/tenancy -q` | **426** (o'zgarmagan, talab >= 412) |
| 15 | `npm run gate` | **exit 0** |
| 16 | vitest / node / i18n | **246 / 111 / 577x3** (uchalasi ham o'zgarmagan) |
| 17 | `git diff --exit-code services/core-api/pyproject.toml frontend/package.json frontend/package-lock.json` | **o'zgarish yo'q** (T-04-SC) |

Artefakt mezonlari: `retention.py` **765** qator (talab >= 150, `storage_tier` bor); `alerts.py` `sendMessage` ni o'z ichiga oladi; `alerting.py` **1 124** qator (talab >= 200, `alert_events` bor); `monitoring.md` **250** qator.

`key_links` ikkalasi ham o'lchandi: `retention.py` -> `storage.py` (`get` / `put` / `mark_compressed` uchalasi ham CHAQIRILADI); `alerting.py` -> `alerts.py` (`send_message` CHAQIRILADI va xato YUTILADI).

## Bazaviy holat

| O'lchov | Baza (`384195a`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 755 | **1 787** | ✅ +32 |
| tenancy | 426 | **426** | ✅ o'zgarmagan |
| vitest | 246 | **246** | ✅ o'zgarmagan |
| node darvozalari | 111 | **111** | ✅ o'zgarmagan |
| i18n | 577 x 3 | **577 x 3** | ✅ o'zgarmagan |
| `ruff` + `ruff format` + `mypy` | toza | **toza** | ✅ |
| `npm run gate` | — | **exit 0** | ✅ |

⚠ +32 = 16 (retention) + 15 (alerting) + 1 (sir filtrining nazorat testi).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — yetishmayotgan kritik xulq] `capture_due_markets()` retention uchun JIMGINA bo'sh qaytaradi**

- **Topildi:** Task 1, bozorlar ro'yxatini tanlashda
- **Muammo:** Reja bozorlar manbaini aniq nomlamagan, `alert_sweep` uchun esa «`capture_due_markets()` yoki uning qo'shnisi» degan. O'sha funksiyaning uchala disjunkti ham **bugungi kadr olish rejasiga** qaraydi: (a) muddati kelgan `pending` qator, (b) bugungi reja HALI yo'q, (c) ijarasi tugagan `running` qator. Retention esa **03:20 da**, kadr olish oynasidan tashqarida ishlaydi.
- **Nima uchun kritik:** tik rejani materializatsiya qilib bo'lgach (b) yolg'onga aylanadi va bozor funksiyadan **umuman chiqmaydi**. Ya'ni retention o'sha bozorni ko'rmasdi: **xato yo'q, jurnal yozuvi yo'q**, faqat disk asta-sekin to'lardi va nosozlik oylar keyin ko'rinardi. Bu `04-07` ning 2-deviatsiyasi bilan bir xil sinf.
- **Yechim:** `auth_list_markets_full()` — o'sha funksiyaning **qo'shnisi**, ham `SECURITY DEFINER`, ham `STABLE`, yuzasi tor (bozor konfiguratsiyasi, tenant ma'lumoti emas) va `sbozor_app` ga allaqachon `GRANT` qilingan. Migratsiya **kerak bo'lmadi**.
- **Verifikatsiya:** `test_the_job_reports_zero_instead_of_crashing_on_an_empty_market` — `result.markets >= 2`.
- **Committed in:** `6b8f06c`

**2. [Rule 2 — yetishmayotgan kritik xulq] Faqat `compressed` ni tozalash `full` kadrni MANGU saqlab qolardi**

- **Topildi:** Task 1, `PURGEABLE_TIERS` ning docstringini o'qiganda
- **Muammo:** Reja tozalash nomzodlarini `tier='compressed'` bilan cheklaydi. `snapshot_repo.py::PURGEABLE_TIERS` esa `full` ni ATAYIN o'z ichiga oladi va sababni O'ZI yozadi: «siqish bosqichini o'tkazib yuborgan kadr ham 455 kundan keyin arxivdan chiqarilishi kerak».
- **Nima uchun kritik:** buzuq obyekt yoki ombor xatosi tufayli siqilmagan kadr `full` bo'lib qoladi. Faqat `compressed` ni tozalaydigan variant uni **hech qachon** o'chirmasdi — jimgina, chunki hech qanday xato chiqmasdi.
- **Yechim:** tozalash `PURGEABLE_TIERS` bo'ylab yuradi (reyestrdan hosila, qo'lda sanalmagan).
- **Verifikatsiya:** `test_a_frame_that_could_not_be_compressed_is_still_purged` — buzuq obyekt siqilmaydi (`compressed == 0`), lekin **arxivdan chiqadi** (`purged == 1`).
- **Committed in:** `6b8f06c`

**3. [Rule 1 — o'lchanmagan faraz] Rejaning SABOTAJ 1 i hech nimani qizartirmadi**

- **Qayerda:** Task 1 ning sabotaj mezoni
- **O'lchandi:** predikatni `PURGEABLE_TIERS` ga kengaytirish **16/16 testni yashil qoldirdi**. Sabab yuqorida («1-SABOTAJNING TOPILMASI») to'liq yozilgan: `mark_compressed()` ning O'Z predikati **qatorni** himoya qiladi, **obyekt** esa himoyalanmagan edi.
- **Yechim:** `RetentionResult.not_smaller` sanog'i testga assert sifatida qo'shildi. Sabotaj endi **aynan 1** testni qizartiradi va ikkala tozalash testi **yashil qoladi** — rejaning niyati (bir yo'nalishli o'tish alohida o'lchanadi) **isbotlandi**, mexanika esa o'lchov bilan almashtirildi.
- **Fayllar:** `tests/integration/test_retention.py` — `6b8f06c`

**4. [Rule 3 — bloklovchi] `04-07` ning `schedule=[` sanog'i bu rejani BAJARIB BO'LMAYDIGAN qilardi**

- **Topildi:** Task 3, `worker.py` ga uchta jadval qo'shganda
- **Muammo:** `test_capture_tick.py::test_the_scheduler_has_exactly_one_minute_cron` `len(re.findall(r"schedule=\[", body)) == 1` deb yozilgan. Bu reja esa REJA BO'YICHA yana **uchta** jadval qo'shadi (`retention.daily`, `alert.sweep`, `alert.digest`).
- **Yechim:** darvozaning HAQIQIY da'vosi hech qachon «jadval bitta» bo'lmagan — u «**DAQIQALIK** cron oqimi bitta» edi (D-02/D-03). Sanoq endi jadval KIRISHLARI bo'yicha yuradi, cron konstantalari **mahsulot modulidan** yechiladi va daqiqalik namunaga mos keladigani AYNAN bitta bo'lishi talab qilinadi.
- **Darvoza SUSAYMADI, KUCHAYDI:** yangi shakl `"*/1 * * * *"` va `"* * * * *"` ning har qanday bo'shliqli variantini ham ushlaydi, holbuki eski shakl faqat literalning aynan bir ko'rinishini sanardi.
- **Fayllar:** `tests/integration/test_capture_tick.py` — `bfbaa1f`

**5. [Rule 2] `RetentionPolicy` qo'shildi (rejaning imzosida yo'q edi)**

- **Muammo:** Rejaning `<interfaces>` bandi `retention_daily(sessionmaker, storage, *, today=None)` deydi, `<action>` bandi esa `settings.retention_jpeg_quality` ni chaqiradi — ya'ni `Settings` obyekti kerak, lekin imzoda u yo'q.
- **Yechim:** `RetentionPolicy` — `CapturePolicy` (04-07) va `QualityThresholds` (04-04) bilan aynan bir xil qaror va bir xil sabab: job sozlamalar obyektining butun yuzasini ko'rmasligi kerak. `Settings` uzatilganda testni qurish uchun `DATABASE_URL`, `JWT_SECRET` va `NVR_CREDENTIAL_KEY` majburiy bo'lardi — 90 kunni kutmasdan isbotlash mexanizmining o'zi shu bilan qiyinlashardi.
- **Fayllar:** `services/core-api/app/jobs/retention.py`, `services/core-api/app/worker.py` — `6b8f06c` / `bfbaa1f`

**6. [Rule 2] `RetentionResult.not_smaller` shoxi — «kattaroq chiqsa yozmaymiz, lekin belgilaymiz»**

- **Muammo:** Reja qayta kodlash natijasi kattaroq chiqishi mumkinligini ko'rmagan. Sodda variant («har doim yoz») avlod yo'qotishiga hech qanday chegara qo'ymasdi; boshqa sodda variant («kattaroq bo'lsa tashlab ket») esa qatorni `full` da qoldirib, **har kecha** qayta urinishga olib kelardi — va har urinish yana bir avlod yo'qotardi.
- **Yechim:** obyekt TEGILMAYDI, lekin qator BARIBIR `compressed` deb belgilanadi va hodisa `log.info("retention_recompress_not_smaller")` bilan sanoqqa tushadi. Yon foyda: aynan shu sanoq 3-deviatsiyadagi darvozani berdi.
- **Fayllar:** `services/core-api/app/jobs/retention.py` — `6b8f06c`

**7. [Rule 1 — test shartidagi shovqin] Guruhlash testlari platforma alertlari tufayli qizardi**

- **Topildi:** Task 3, `test_alerting.py` ning birinchi yugurishida (`4 == 1`)
- **O'lchandi:** sabab MAHSULOTDA emas edi. `system_heartbeats` da na `backup`, na `retention` qatori bor (zaxira 8-fazada quriladi, retention esa hali yugurmagan), ya'ni supurgi HAR yugurishda ikkita **platforma** alertini ham ko'taradi va ular **ikkinchi** (platforma) xabarini tug'diradi.
- **Yechim:** `bed` fixture'i ikkala yurak urishini YANGI qilib qo'yadi. Bu mahsulot xulqini yashirmaydi — `test_stale_heartbeat_alerts` uni ALOHIDA va uch holatda (yozilmagan / eskirgan / yangi) o'lchaydi.
- **Fayllar:** `tests/integration/test_alerting.py` — `bfbaa1f`

**8. [Rule 1 — test shartidagi shovqin] Debounce testi BOSTIRILMAYDIGAN alert bilan yozilgan edi**

- **Topildi:** Task 3, ikkinchi yugurishda
- **O'lchandi:** 22 kameralik stsenariy (88 % >= 30 %) `camera_offline` ni ham ko'taradi, u esa `NEVER_SUPPRESSED_ALERT_KEYS` da — ya'ni u debounce oynasi ichida ham **to'g'ri ravishda** yuboriladi va test o'z farazini emas, D-22 ning **istisnosini** o'lchardi.
- **Yechim:** debounce va eskalatsiya testlari 5 kamera (20 % < 30 %) bilan yoziladi — o'shanda yagona alert `capture_missed` bo'ladi va u bo'g'iladigan sinfda. Sabab ikkala testning docstringida raqamning yonida yozildi.
- **Fayllar:** `tests/integration/test_alerting.py` — `bfbaa1f`

**9. [Rule 3 — bloklovchi] `ops/seaweedfs/s3.json` yana KATALOG bo'lib yaratilgan edi**

- **Muammo:** `04-07` ning 8-deviatsiyasining aynan takrori: bind-mount manba fayli bo'lmaganda Docker uni **katalog** qilib yaratadi va `storage` konteyneri unhealthy bo'ladi (`read /etc/seaweedfs/s3.json: is a directory`). Fayl `.gitignore` da, ya'ni har yangi worktree'da qaytadan yuzaga keladi.
- **Yechim:** `rmdir` + `.example` dan fayl (kalitlar `compose.yaml` ning `tests` bloki standartlari bilan AYNAN bir xil) + `docker compose rm -sf storage` (eski konteyner eskirgan mountni ushlab turardi). Repo **o'zgarmadi** (`git check-ignore -v` bilan tasdiqlandi).

---

**Total deviations:** 9 (3x Rule 2 yetishmayotgan kritik xulq, 3x Rule 1 o'lchanmagan faraz/shovqin, 2x Rule 3 bloklovchi, 1x reja mezonining mexanikasi)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Ikkitasi (1, 2) rejada umuman ko'rilmagan **jim nosozlikni** yopdi va ikkalasi ham «xato bermaydi, alert bermaydi, faqat disk to'lganda ko'rinadi» sinfiga tegishli edi. Uchinchisi (3) rejaning o'lchanmagan farazini o'lchov bilan almashtirdi va natija rejadagidan **kuchliroq** darvoza berdi.

## Qamrov chegaralari — ochiq yozilgan

1. **⛔ 90 KUNLIK SIYOSAT 90 HAQIQIY KUN DAVOMIDA SINALMAGAN — va bu farq ochiq yozilgan.** Isbotlangani **mexanizm**: chegara nolga qo'yiladi, bugungi kadr darhol siqiladi, o'lchamlari saqlanadi, kaliti o'zgarmaydi, ikkinchi marta siqilmaydi va muddati tugaganda obyekti ketib qatori qoladi. Isbotlanmagani — **siyosatning bir yil davomida ishlab turishi**. Uni faqat vaqt isbotlaydi. Band `04-VALIDATION.md` da **Manual-Only**, egasi **Ops**; `ops/docs/monitoring.md` §7 buni operator tiliga o'girib yozadi va nazorat qilinadigan yagona sonni (`system_heartbeats['retention'].last_seen_at`) nomlaydi. Bu faylni «90 kunlik siyosat sinaldi» deb o'qish **xato** bo'lardi va test modulining docstringi buni birinchi abzatsda aytadi.

2. **`disk_pressure` shoxi haqiqiy to'lish ostida o'lchanmagan.** `disk_usage_percent()` HAQIQIY `statvfs` dan o'qiydi va u alohida test bilan qulflangan (`0 < used < 100`), lekin `>= 85 %` shoxining o'zi konteyner diskini to'ldirishni talab qiladi. Kod yo'li `_platform_signals` da boshqa platforma alertlari bilan **bir xil** (`backup_stale` to'liq o'lchangan), ya'ni xavf tor. **Egasi:** `04-12` yoki Ops.

3. **`nvr_account_locked` shoxi integratsiya testida o'lchanmagan.** Mantiq yozilgan va u `CAPTURE_AUTH_LOCKING_CODES` dan **hosila** (reyestrga yangi qulflovchi kod qo'shilsa shox uni avtomatik ko'radi), lekin uni fire qilish uchun bugungi qatorda `capture_bad_credentials` kodi kerak. Hosila to'plamning o'zi `04-04` da qulflangan. **Egasi:** `04-12`.

4. **Kunlik dayjest MATNI ops nuqtai nazaridan sinalmagan.** Uning sonlari `day_summary` dan chiziladi va test ularni tekshiradi, lekin «bu xabar admin uchun o'qiladimi?» savoli — inson o'lchovi. **Egasi:** `04-HUMAN-UAT` yoki pilot.

5. **Tashqi dead-man's switch (D-21) — kod yozilmagan va bu QAROR.** `ops/docs/monitoring.md` §5 ikki provayder uchun qadamma-qadam yo'riqnoma beradi va oxirida uni **tekshirish** qadamini ham (worker'ni ataylab to'xtatib ko'rish). Kodga aylantirish yangi bog'liqlik va yangi nosozlik nuqtasi qo'shardi.

## Known Stubs

Yo'q. Uchala task ham to'liq ishlaydi. Yuqoridagi «Qamrov chegaralari» beshta bandi **stub emas** — ular yozilgan va ishlaydigan kodning o'lchanmagan yuzalari (yoki ataylab kod yozilmagan qaror) va har birining egasi nomlangan.

## Threat Flags

Yangi tarmoq **endpointi** yo'q (kod Telegram'ga va S3 ga MIJOZ sifatida boradi). Yangi sxema o'zgarishi ham yo'q (migratsiya YOZILMADI). **Yangi CHIQUVCHI trust boundary bor va u threat register'da allaqachon nomlangan** (ilova -> Telegram serverlari).

| Threat | Holat |
|---|---|
| T-04-58 (alertga kadr rasmi) | **mitigate** — rasm biriktiruvchi metod umuman yozilmagan; UCH darvoza: `dir()`, matn, `respx`; TO'RTINCHISI — `detail` allowlist'i (yozish paytida) |
| T-04-59 (bot tokeni xato matnida) | **mitigate** — `SecretStr` + `_failure()` da interpolyatsiya yo'q + `raise ... from None`; `SENSITIVE_KEYS` qamrovi YOPILDI; jurnal satri sabotaj 3 da tirik tasdiqlandi |
| T-04-60 (Telegram uzilishi kadr olishni to'xtatadi) | **mitigate** — `send_message` `bool` qaytaradi; chaqiruv alohida tranzaksiyada va xato yutiladi; sabotaj 3 bilan o'lchandi |
| T-04-61 (alert charchog'i) | **mitigate** — bozor bo'yicha BITTA xabar + 60 daq debounce + eskalatsiya (daraja); `occurrences` UI uchun saqlanadi; sabotaj 2 bilan o'lchandi |
| T-04-62 (muhim hodisaning bo'g'ilishi) | **mitigate** — `NEVER_SUPPRESSED_ALERT_KEYS` `ALERT_META` dan HOSILA; `test_the_never_suppressed_list_is_derived_from_the_registry` |
| T-04-63 («alert bor deb o'ylash») | **mitigate** — `log.warning("alerts_disabled")` konstruktorda; `notified_at` `NULL` qoladi va u YASHIRILMAYDI; `test_alerts_disabled_never_raises_and_never_calls` |
| T-04-64 (ikki marta siqish) | **mitigate** — `WHERE storage_tier='full'` qat'iy predikat + `mark_compressed()` ning O'Z predikati; **ikkala qatlam ham o'lchandi** (1-sabotajning topilmasi) |
| T-04-65 (heartbeat -> konteyner healthcheck) | **mitigate** — `ops/docs/monitoring.md` §2 sabab bilan yozilgan; endpoint `04-09` da va u `compose.yaml` ga ulanmaydi |
| T-04-66 (`cron_offset` siz UTC) | **mitigate** — `MARKET_CRON_OFFSET` uchala jadvalda; sanoq darvozasi (5 >= 3); `TICK_CRON` da ATAYIN yo'q va sabab yozilgan (daqiqalik cron mintaqadan mustaqil) |
| T-04-SC (paket o'rnatish) | **mitigate** — yangi paket YO'Q: `aiogram` ham, `freezegun` ham qo'shilmadi; `git diff --exit-code` toza |

## Issues Encountered

- **`ops/seaweedfs/s3.json` KATALOG edi va `storage` konteyneri unhealthy.** `04-07` ning 8-deviatsiyasining aynan takrori (fayl `.gitignore` da, ya'ni har yangi worktree'da qaytadan yuzaga keladi). Tuzatildi; qo'shimcha qadam kerak bo'ldi — eski konteyner eskirgan mountni ushlab turardi va `docker compose rm -sf storage` talab qilindi. **Parallel ijrochiga ta'siri:** konteyner allaqachon **buzuq** edi, ya'ni uni qayta yaratish ikkala ijrochi uchun ham tuzatish. Bucket (`sbozor-snapshots`) volume'da saqlangan va **qayta yaratilishi kerak bo'lmadi**.
- **`.env` bu worktree'da umuman yo'q.** `compose.yaml` `S3_ACCESS_KEY`/`S3_SECRET_KEY` ni standartsiz talab qiladi, lekin `tests` bloki ularga `:-sbozor-local-*` standartini beradi — ya'ni test yo'li `.env` siz ham butun. `worker`/`scheduler` konteynerlari bu rejada ishga tushirilmadi.
- **Frontend `node_modules` yo'q edi** — `npm ci --prefix frontend` bajarildi. `package.json`/`package-lock.json` **tegilmadi** (`git diff --exit-code` bilan tasdiqlandi).
- **`mypy` `AsyncRetrying.__call__` ning qaytish tipini yecha olmadi** (`Any`) — `response: httpx.Response = await retrying(...)` aniq annotatsiyasi qo'shildi.
- **`ruff` ning `E501`, `SIM300` va `I001` qoidalari** bir necha joyda ishga tushdi — `--fix`/qo'lda tuzatildi, birorta qoida chetlab o'tilmadi.

## Next Phase Readiness

**`04-09` (API) uchun tayyor va u shu uch satrni o'qishi kerak:**
- `/internal/self-check` `ALERT_SWEEP_COMPONENT` va `RETENTION_COMPONENT` konstantalarini **import qilishi shart**, qo'lda yozmasligi — `capture.py::CAPTURE_TICK_COMPONENT` bilan bir xil qoida.
- ⛔ Endpoint `compose.yaml` ning `healthcheck` iga **ulanmaydi** (Pitfall 14). Sabab `ops/docs/monitoring.md` §2 da operator tilida yozilgan.
- `alert_events` ni o'qiydigan marshrut `occurrences` va `notified_at` ni **qaytarishi shart** — UI-SPEC §6.7 ikkalasini ham majburiy qiladi va `notified_at IS NULL` qatori **yashirilmaydi**.

**`04-10`/`04-11` (UI) uchun:**
- `alert_key` qiymatlari `ALERT_META` reyestrida va ular `04-UI-SPEC.md` §11.9 ning tarjima kalitlari bilan mos (`capture_missed`, `capture_stopped`, `camera_offline`, `backup_stale`, `retention_stale`, `disk_pressure`, `nvr_account_locked`, `capture_credential_unreadable`, `capture_recovered`).
- ⛔ **G-3:** alert komponentlarida `<img>` **taqiqlangan**. Backend tomoni shu rejada yopildi; frontend darvozasi `04-10`/`04-11` da.
- `detail` faqat olti kalitni tashiydi (`ALERT_DETAIL_KEYS`) — UI noma'lum kalitni render qilmasligi kerak, lekin endi u **bazaga ham tushmaydi**.
- `capture_recovered` — **qator emas, XABAR**: u `alert_events` ga hech qachon yozilmaydi (`storable=False`). UI tiklanishni yopilgan alertning `resolved_at` idan ko'radi.

**`04-12` (faza darvozasi) uchun:** yuqoridagi «Qamrov chegaralari» ning besh bandi. ⚠ **Ikki band `04-06`/`04-07` dan meros va HALI OCHIQ:** (a) `tests` xizmatiga `depends_on: storage` (`compose.yaml` bu rejaning fayllari ichida emas edi), (b) `S3_REGION` `.env.example` da yo'q.

**8-faza (FOUND-07, zaxira) uchun:** kontrakt tayyor va u **bitta qator**: har muvaffaqiyatli zaxira `system_heartbeats` ga `component = 'backup'` bilan yozadi. Yozmaslik — **alert** (`backup_stale`, hech qachon bo'g'ilmaydi) va u «hech qachon yozilmagan» holatini ham qoplaydi.

⚠ **`REQUIREMENTS.md` ATAYIN TEGILMADI** — `03-01` da o'rnatilgan qoida bo'yicha faza darajasidagi talablar reja emas, **FAZA** oxirida, dalil bilan belgilanadi.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan 6 fayl + o'zgartirilgan 4 fayl** — hammasi diskda tekshirildi (`MISSING: 0`).
- **Uchala commit `git log` da tasdiqlandi:** `6b8f06c`, `9dfb704`, `bfbaa1f` — bazasi `384195a`.
- **Reja artefakt shartlari o'lchandi:** `retention.py` **765** qator (talab >= 150) va `storage_tier` ni o'z ichiga oladi; `alerts.py` da `sendMessage` bor; `alerting.py` **1 124** qator (talab >= 200) va `alert_events` ni o'z ichiga oladi; `monitoring.md` da `self-check` va `healthcheck` bor.
- **`key_links` ikkalasi ham o'lchandi:** `retention.py` -> `storage.py` (`get`/`put` CHAQIRILADI, keyin `mark_compressed`); `alerting.py` -> `alerts.py` (`send_message` CHAQIRILADI va xato YUTILADI).
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin orkestrator tomonidan yangilanadi.
- **Ishchi daraxt toza:** `git status --short` da faqat topshiriqda «meniki emas» deb belgilangan uchta fayl qoldi; `.env` va `ops/seaweedfs/s3.json` gitignore ostida.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
