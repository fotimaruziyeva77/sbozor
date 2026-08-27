---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 21
subsystem: infra
tags: [heartbeat, monitoring, telegram, aiogram, httpx, compose, rls, audit, pytest]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-13 ikki dayjest jobi va ularning yagona yurak urishi; 07-14 heartbeat reyestri (`EXPECTED_COMPONENTS` + `watched`) va uning AST darvozasi; 07-18 `binding_repo.bind_director()`; 07-19 outbox muddati va urinish hisobi"
provides:
  - "Ikki alohida dayjest yurak urishi (`notify_digest_morning` / `notify_digest_evening`) — yarim o'lgan juftlik endi kuzatuvda KO'RINADI"
  - "Kechki dayjestning case sanog'i KECHAGI kundan — strukturaviy nol yopildi va yorliq sonning ma'nosini uchala locale'da AYTADI"
  - "Bot `404` ni NOMLANGAN `detail == \"not_bound\"` bilan o'qiydi — noto'g'ri `CORE_API_URL` endi «siz bog'lanmagansiz» yolg'onini bermaydi"
  - "`binding_repo.revoke()` — `revoked_at IS NULL` qo'riqchisi, idempotent NO-OP, auditsiz"
  - "`npm run up` `bot-service` ni ko'taradi; `bot-tests` prod tokenlarini meros olmaydi"
  - "`tests/unit/test_dev_environment.py` — dev muhitining Dockersiz mexanik darvozasi (nazorat bandi bilan)"
  - "`deferred-items.md` — 13 rejalashtirilmagan WARNING + 8 INFO nomma-nom, egasi bilan; qayta sanoq ikkala ko'rik fayli ustida"
affects: [08-faza, faza-yakuni-darvozasi, kuzatuv, bot-ishonchliligi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bir jobga bir yurak urishi: ikki job bitta `system_heartbeats` qatorini BO'LISHMAYDI"
    - "Statusga emas, NOMLANGAN javob detaliga tayanish (`404` + `detail`) — servislararo kelishuv literal juftlik bilan, sabab kodda ochiq"
    - "Ajratilganlikning NAZORAT bandi: «test blokida `${` yo'q» da'vosi «prod blokida `${` bor» bilan JUFTLANADI"
    - "Devor soatidan mustaqil navbat testi: `next_attempt_at` ANIQ beriladi, `enqueue()` ning `now()` server_default'iga tayanilmaydi"

key-files:
  created:
    - tests/unit/test_dev_environment.py
  modified:
    - services/core-api/app/jobs/notifications.py
    - services/core-api/app/jobs/notification_meta.py
    - services/core-api/app/jobs/outbox.py
    - services/core-api/app/jobs/alerting.py
    - services/core-api/app/api/internal/self_check.py
    - services/core-api/app/repositories/binding_repo.py
    - services/bot-service/app/core_client.py
    - compose.yaml
    - package.json
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md

key-decisions:
  - "`digest_stale` alert KALITI bitta qoldi (ikkala komponent ham unga bog'lanadi) — ikkinchi kalit `ALERT_META` + frontend `ALERT_TITLE_KEYS` + uchala locale matniga tegardi; qaysi dayjest o'lgani `/internal/self-check` da nomma-nom ko'rinadi"
  - "Eski `DIGEST_COMPONENT` aliasi QOLDIRILMADI — qolgan alias eski nomni yozadigan yangi chaqiruvchi uchun ochiq eshik bo'lardi va u ikkala reyestrda ham ko'rinmasdi"
  - "`anomaly_count` -> `prev_day_case_count`: ikkala nom bir vaqtda allowlistda TURMAYDI, aks holda «bugungi kunni sanaydigan» eski chaqiruvchi darvozadan jimgina o'tardi"
  - "Javob tanasidagi `detail` `_failure()` ga UMUMAN yetib bormaydi — qaror chaqiruvchida qabul qilinadi, ya'ni D-04 ning `ast` darvozasi tegilmasdan yashil qoladi"
  - "`revoke()` `bool` qaytaradi (ilgari `None`) — «holat o'zgardimi?» savoli chaqiruvchida ham javob topadi va test ikki yo'nalishni o'lchay oladi"
  - "Matn yorlig'i testi `test_outbox.py` emas, `tests/unit/test_digest_qualifiers.py` ga yozildi — u `_build_text` ni bazasiz o'lchaydigan MAVJUD fayl va uning `_EVENING_PAYLOAD` i baribir yangilanishi shart edi"

patterns-established:
  - "Yurak urishi granularligi = job granularligi (WR-10 ning umumiy shakli)"
  - "Reyestr qarori (`AUDITED_TABLES`) va kod ZID bo'lsa — KOD moslashadi, reyestr emas"
  - "Compose muhitidagi `${X:-y}` STANDART emas, MAJBURLASH: test konteynerida u har doim prod qiymatiga aylanadi"

requirements-completed: [RECON-03, BOT-01, BOT-04]

# Metrics
duration: 55min
completed: 2026-08-13
---

# Phase 7 Plan 21: Ikki yurak urishi, rost kechki son va ishlaydigan dev buyrug'i — Summary

**Yarim o'lgan dayjest juftligi endi kuzatuvda ko'rinadi, kechki xabardagi nomuvofiqlik soni strukturaviy noldan o'lchangan songa aylandi, bot `404` ni nomlangan detal bilan o'qiydi, bog'lanish tarixi qayta yozilmaydi va `npm run up` fazaning mahsulotini haqiqatan ko'taradi.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-13T00:00:00Z (mahalliy ~05:00 +05:00)
- **Completed:** 2026-08-13T00:55:00Z (mahalliy ~05:55 +05:00)
- **Tasks:** 3/3
- **Files modified:** 18 (1 yangi, 17 o'zgargan)

## Accomplishments

- **WR-10 yopildi.** `notify_digest` ikki komponentga bo'lindi. Ilgari kechki job har kuni 20:45 da o'sha bitta qatorni yangilardi, ya'ni ertalabkisi **butunlay o'lsa ham** yurak urishi yangi ko'rinardi va `digest_stale` **hech qachon** ko'tarilmasdi — D-20 ning «alert muvaffaqiyat signalining YO'QLIGIGA qo'yiladi» qoidasi yarim ishlardi.
- **WR-02 yopildi.** Kechki dayjestning case sanog'i `as_of` dan `as_of - 1 kun` ga ko'chdi. Bugungi `service_date` li case faqat ertaga 04:25 da (`RECON_OPEN_CRON`) tug'iladi, ya'ni 20:45 dagi so'rov **har kuni, istisnosiz `0`** qaytarardi — o'lchanmagan holat o'lchangan nol bo'lib chiqardi. Payload kaliti `prev_day_case_count` ga, yorliq esa sonning **ma'nosini aytadigan** matnga aylandi (uchala locale).
- **WR-01 (frontend) yopildi.** `404` ning ma'nosi endi javob tanasidan keladi. Noto'g'ri sozlangan `CORE_API_URL`, o'zgargan prefiks va proxy'ning HTML sahifasi — uchalasi ham `bot.error.retry` beradi, `start.py:97-98` ochiq taqiqlagan «siz bog'lanmagansiz» yolg'onini emas.
- **WR-03 yopildi.** `revoke()` uch nuqsondan tozalandi: qo'riqchi qo'shildi, audit chaqiruvi olib tashlandi, to'qilgan `old` qiymat yo'qoldi. Reyestr (`AUDITED_TABLES`) va kod endi bir narsani aytadi.
- **B-8 / B-9 yopildi** va ular bu fazada **birinchi marta qayd etildi** — `deferred-items.md` da ilgari umuman yo'q edi.
- **`deferred-items.md` 4 banddan 8 ga o'sdi**, mavjud to'rttasi **tegilmadi** (3-band YOPILDI deb belgilandi).

## Task Commits

1. **Task 1: ikki dayjest — ikki yurak urishi; kechki son rost gapiradi** — `b259482` (fix)
2. **Task 2: bot `404` ni NOMLANGAN o'qiydi; bog'lanish tarixi qayta yozilmaydi** — `e2a2eb9` (fix)
3. **Task 3: dev muhiti va'dasi + ko'rik topilmalari egasi bilan** — `4d8ef49` (chore)

## Files Created/Modified

**Yangi:**
- `tests/unit/test_dev_environment.py` — `npm run up` va `bot-tests` token merosining Dockersiz mexanik darvozasi (4 test, nazorat bandi bilan)

**O'zgargan — mahsulot:**
- `services/core-api/app/jobs/notifications.py` — `DIGEST_MORNING_COMPONENT` / `DIGEST_EVENING_COMPONENT`; kechki case sanog'i kechagi kundan
- `services/core-api/app/jobs/notification_meta.py` — kechki allowlist: `anomaly_count` -> `prev_day_case_count`
- `services/core-api/app/jobs/outbox.py` — `_EVENING_TEXT` yorlig'i `prev_anomalies`, uchala locale
- `services/core-api/app/jobs/alerting.py` — `watched` beshta juftlik; alert kaliti bitta qoldi (sabab kodda)
- `services/core-api/app/api/internal/self_check.py` — `EXPECTED_COMPONENTS` 10 -> **11**
- `services/core-api/app/repositories/binding_repo.py` — `revoke()` qo'riqchi + `bool` + auditsiz; `AuditAction` / `write_app_audit` importlari olib tashlandi
- `services/bot-service/app/core_client.py` — `_NOT_BOUND_DETAIL`, `_is_not_bound()`, `_failure(..., not_bound=)`
- `compose.yaml` — `bot-tests` tokenlari literal
- `package.json` — `scripts.up` ga `bot-service`

**O'zgargan — testlar:**
- `tests/integration/test_notifications.py` — ikki yurak urishi (ikki yo'nalishli), kechagi son, allowlist rad etishi, quiet-hours testining devor soatidan ajratilishi
- `tests/integration/test_alerting.py` — «ertalabkisi o'lgan, kechkisi tirik -> `digest_stale`» (ikki yo'nalishli)
- `tests/integration/test_bot_internal_api.py` — qayta bekor qilish NO-OP; audit da'vosi audit jadvalidan tarix jadvaliga ko'chdi; AST darvozasi `== 1` -> `== []`
- `tests/unit/test_digest_qualifiers.py` — kechagi yorliq uchala locale'da + eski yorliqning yo'qligi
- `tests/unit/test_outbox_policy.py`, `tests/integration/test_capture_schedule.py` — yangi nomlarga moslashtirildi

**Rejalashtirish:**
- `.planning/.../deferred-items.md` — 5, 6, 7, 8-bandlar qo'shildi; 3-band yopildi

## Decisions Made

- **`digest_stale` kaliti bitta qoldi.** Ikkinchi kalit `ALERT_META` reyestriga, frontend'ning `ALERT_TITLE_KEYS` xaritasiga, uchala locale matniga **va** `snapshot-copy.test.mjs` ning G-36 o'lcham qulfiga (`ALERT_TITLE_KEY_COUNT = 15`) tegardi — ya'ni sof backend o'zgarishi ikkita frontend faylni tortardi. Operatorga kerakli fakt bitta kalit bilan yetadi; qaysi biri o'lgani `/internal/self-check` da nomma-nom. Narx `deferred-items.md` ning 6-bandida ochiq yozildi.
- **Alias qoldirilmadi.** `DIGEST_COMPONENT` butunlay olib tashlandi: qolgan alias eski nomni yozadigan yangi chaqiruvchi uchun ochiq eshik bo'lardi va o'sha nom **ikkala reyestrda ham** yo'q bo'lardi.
- **`detail` `_failure()` ga yetib bormaydi.** Javob tanasi `_request()` da o'qiladi, `_failure()` esa faqat `bool` bayroq oladi — D-04 ning `ast` darvozasi (u aynan `_failure()` tanasini o'qiydi) tegilmasdan yashil qoladi.
- **`revoke()` endi `bool` qaytaradi.** `None` bilan «holat o'zgardimi?» savoliga javob berib bo'lmasdi va qayta bekor qilish testi faqat qiymatlarni solishtira olardi — funksiya umuman ishlamay qolgan holatda ham u yashil bo'lardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_capture_schedule.py` eski komponent nomini kutardi**
- **Found during:** Task 1
- **Issue:** `tests/integration/test_capture_schedule.py:731` `seven = {..., "notify_digest", ...}` to'plamini `never_seen` ichida talab qilardi. `EXPECTED_COMPONENTS` dan `notify_digest` chiqarilgach test qizarardi. Fayl rejaning `files_modified` ro'yxatida yo'q edi.
- **Fix:** To'plam ikki yangi nom bilan almashtirildi (to'rtta -> **beshta**). Da'vo susaymadi: endi **ikkala** dayjest ham alohida ko'rinishi talab qilinadi.
- **Files modified:** `tests/integration/test_capture_schedule.py`
- **Verification:** `pytest tests/integration/test_capture_schedule.py -q` — yashil
- **Committed in:** `b259482`

**2. [Rule 3 - Blocking] `test_digest_qualifiers.py` ning `_EVENING_PAYLOAD` i eskirardi**
- **Found during:** Task 1
- **Issue:** Fayl `anomaly_count: 3` bilan matn quradi. `_plain()` yo'q kalit uchun `KeyError` bermaydi, `-` chizadi — ya'ni matn quruvchisi **buzilgan holatda ham** bu fayldagi barcha da'volar yashil qolardi (jim eskirish).
- **Fix:** Payload `prev_day_case_count` ga o'tkazildi; **qo'shimcha** — yangi yorliqning uchala locale'da son bilan **bir qatorda** turishi va eski yorliqning yo'qligi ikki yangi test bilan qulflandi.
- **Files modified:** `tests/unit/test_digest_qualifiers.py`
- **Verification:** `pytest tests/unit/test_digest_qualifiers.py -q` — yashil
- **Committed in:** `b259482`

**3. [Rule 3 - Blocking] `test_outbox_policy.py` eski kalit nomiga tayanardi**
- **Found during:** Task 1
- **Issue:** `assert "anomaly_count" in OUTBOX_PAYLOAD_KEYS` — test farazi kalit nomiga qadalgan edi.
- **Fix:** Faraz `prev_day_case_count` ga ko'chirildi; o'lchanayotgan narsa (birlashma emas, **har tur uchun alohida** allowlist) o'zgarmadi.
- **Files modified:** `tests/unit/test_outbox_policy.py`
- **Verification:** `pytest tests/unit/test_outbox_policy.py -q` — yashil
- **Committed in:** `b259482`

**4. [Rule 1 - Bug] Quiet-hours testining IKKINCHI yarmi ham devor soatiga bog'liq edi**
- **Found during:** Task 1 (`deferred-items.md` 3-bandini yopish)
- **Issue:** Band faqat **kvitansiya** nazorat qatorini nomlagan edi. Lekin **eslatma** qatorini ham `overdue_reminder` jobi `enqueue()` bilan yozadi (`next_attempt_at = now()`), ya'ni mahalliy vaqt 22:30 dan keyin `«22:30 da eslatma OLINMAYDI»` da'vosi **bo'sh-rost** bo'lardi: qator quiet oyna tufayli emas, muddati kelmagani uchun qolib ketardi va quiet-hours darvozasi **butunlay buzuq** holatda ham test yashil bo'lardi.
- **Fix:** `_set_due()` yordamchisi qo'shildi va eslatmaning muddati ham qadaladi. Mahsulot yo'li chetlab o'tilmadi — qatorni baribir **job** yozadi, faqat testning predmeti bo'lmagan o'lchov (muddat) determinlashtiriladi.
- **Files modified:** `tests/integration/test_notifications.py`
- **Verification:** Ikki yo'nalishli zond (pastda, «Issues Encountered»)
- **Committed in:** `b259482`

**5. [Rule 3 - Blocking] `_binding_rows()` bog'lanish `id` sini qaytarmasdi**
- **Found during:** Task 2
- **Issue:** Qayta bekor qilish testi `revoke(binding_id=...)` ni to'g'ridan-to'g'ri chaqirishi kerak, yordamchi esa `id` ustunini umuman tanlamasdi.
- **Fix:** `id` ustuni ro'yxatning **oxiriga** qo'shildi (indeks `5`). Boshiga qo'yish mavjud o'nlab da'vodagi indekslarni siljitardi va ular **jimgina** boshqa ustunni o'lchay boshlardi.
- **Files modified:** `tests/integration/test_bot_internal_api.py`
- **Verification:** `pytest tests/integration/test_bot_internal_api.py -q` — 49 test yashil
- **Committed in:** `e2a2eb9`

---

**Total deviations:** 5 auto-fixed (4 blocking, 1 bug)
**Impact on plan:** Hammasi rejaning O'Z o'zgarishlari tufayli tug'ilgan yoki reja topshirgan bandning to'liq bajarilishi uchun zarur edi. Qamrov o'smadi: yangi mahsulot xulqi qo'shilmadi, mavjud da'volar esa **birortasi ham susaymadi** — ikkitasi (audit sanog'i, `capture_schedule` to'plami) aksincha qattiqlashdi.

### Rejadan ongli chetlanishlar (nuqson emas, qaror)

- **Matn yorlig'i testi `test_outbox.py` ga emas, `tests/unit/test_digest_qualifiers.py` ga yozildi.** Ikkinchisi `_build_text()` ni **bazasiz** o'lchaydigan mavjud fayl va uning `_EVENING_PAYLOAD` i baribir yangilanishi shart edi (yuqoridagi 2-chetlanish). Bir da'voni ikki faylga bo'lish ikkinchi haqiqat manbai bo'lardi. `test_outbox.py` **tegilmadi** va yashil qoldi.
- **Allowlist rad etishi `test_notifications.py` ga yozildi** (`test_the_evening_payload_rejects_the_old_anomaly_key`) — o'sha fayl `notification_meta` reyestri ustidagi da'volarni allaqachon saqlaydi.
- **`deferred-items.md` ning 8-bandi rejada yo'q edi** — u ijro davomida topilgan, qamrovdan tashqaridagi qizil darvoza (pastda).

## Issues Encountered

**1. `deferred-items.md` 3-bandi — zond bilan IKKI YO'NALISHDA o'lchandi.**
Tuzatish 05:11 da, ya'ni muammoli oynadan (22:30–00:00) **tashqarida** bajarildi, shuning uchun oddiy «test yashilmi?» yugurishi hech nimani isbotlamasdi. Soatni siljitish o'rniga `claim(now=...)` **o'tmishdagi, lekin quiet oyna ichidagi** paytga (`04:00`) qo'yildi va ikkita vaqtinchalik zond testi yugurtirildi:

| Zond | Natija |
|---|---|
| `enqueue()` bilan seed qilingan kvitansiya qatori | ⛔ **OLINMADI (qizil)** — nosozlik aynan takrorlandi |
| aniq `next_attempt_at` bilan seed qilingan qator | ✅ **OLINDI (yashil)** |

Zond fayli o'lchovdan keyin o'chirildi.

**2. `bot:lint` ning `mypy` bosqichi 07-21 dan OLDIN ham qizil.**
`services/bot-service/tests/unit/test_binding.py` da beshta `[attr-defined]` xatosi (`TelegramMethod[Any]` ning `reply_markup` / `text` atributlari). Fayl bu rejaning fayl ro'yxatida **yo'q** va ijro davomida **umuman o'zgartirilmadi** (`git status` da ko'rinmaydi), ya'ni mazmuni bazadagi (`6b0a849`) holat bilan bayt-bayt bir xil; oxirgi marta `0d8c1f3` (07-18) da o'zgargan. `ruff check` va `ruff format` ikkalasi ham toza. SCOPE BOUNDARY bo'yicha **tuzatilmadi**, `deferred-items.md` ning 8-bandiga egasi bilan yozildi.

**3. `npm run up` ning O'ZI yugurtirilmadi — sabab va o'rnini bosgan o'lchov.**
Buyruq standart compose loyihasiga (`sbozor`) tegadi va foydalanuvchining **jonli stekidagi** `cv-service` ni qayta ishga tushirardi (u ataylab to'xtatilgan: `CV_MODEL_PATH` artefakti yo'q, konteyner ~1 s da bir qayta ishga tushib xostning ~80 % CPU sini yeydi — `package.json` ning `//gate-budget` izohida o'lchangan). Ajratilgan loyihada yugurtirish `bot-service` ning `runtime` image'ini **qurishni** talab qiladi, bu muhitda esa Docker Hub'ga tarmoq yo'q (`registry-1.docker.io: no such host`). O'rniga: `docker compose config` **xatosiz** va darvozaning 4-testi `scripts.up` da nomlangan **har** servis `compose.yaml` da mavjudligini tekshiradi. Band `deferred-items.md` 5-bandida egasi bilan yozildi.

**4. Test image'lari qayta qurilmadi — mavjudlari teglandi.**
Docker Hub'ga tarmoq yo'qligi sababli `sbozor-tests:latest` va `sbozor-bot-tests:latest` ajratilgan loyiha nomi bilan qayta teglandi. Repo konteynerga `- .:/app` bilan mount qilinadi, ya'ni **kod** har doim worktree'dan keladi va faqat bog'liqlik qatlami qayta ishlatiladi.

## Sabotaj natijalari (majburiy — ikkitasi rejadan, ikkitasi qo'shimcha)

| # | Sabotaj | Kutilgan | Natija |
|---|---|---|---|
| 1 | `bot-tests` ga `${TELEGRAM_BOT_TOKEN:-...}` qaytarildi | Task 3 ning (2) darvozasi qizaradi | ⛔ **QIZARDI**, qiymatni nomma-nom ko'rsatib. Qaytarildi |
| 2 | `watched` dan `DIGEST_MORNING_COMPONENT` juftligi olib tashlandi | «faqat kechkisi ishlaganda `digest_stale`» testi qizaradi | ⛔ **IKKI** darvoza qizardi: xulqiy test **va** `test_heartbeat_registry.py::test_every_job_component_is_watched` (komponentni nomma-nom ko'rsatib). Qaytarildi |
| 3 | `not_bound=(status == 404)` — WR-01 dan oldingi shakl | Nomlanmagan `404` testi qizaradi | ⛔ **TO'RTALA** parametrlangan holat ham qizardi (FastAPI `Not Found`, detalsiz JSON, HTML sahifa, bo'sh tana). Qaytarildi |
| 4 | `revoke()` dan `revoked_at IS NULL` qo'riqchisi olib tashlandi | Qayta bekor qilish testi qizaradi | ⛔ **QIZARDI** (`second is False` -> `True`); jurnalda ikkinchi `vendor_binding_revoked` yozuvi ham ko'rindi. Qaytarildi |

## Ko'rik topilmalarining QAYTA SANOG'I

⛔ Reja matniga ishonilmadi — ikkala ko'rik fayli ochilib, `Warnings` va `Info` sarlavhalari ostidagi bandlar **sanaldi**:

| Manba | `Warnings` | `Info` |
|---|---|---|
| `07-REVIEW-backend.md` | **10** (WR-01…WR-10) | bo'lim yo'q |
| `07-REVIEW-frontend.md` | **16** (WR-01…WR-16) | **8** (IN-01…IN-08) |
| **Jami** | **26** | **8** |

Egalik taqsimoti: 07-19 (backend WR-07, WR-08) · 07-20 (backend WR-01, WR-05) · **07-21** (backend WR-02, WR-03, WR-10 + frontend WR-01, WR-10) · 07-22 (frontend WR-06, WR-08) · 07-23 (frontend WR-09, WR-16) — jami **13 ta egalik qilingan**, qolgan **13 tasi** rejalashtirilmagan.

**⛔ REJA MATNIDAN BITTA FARQ TOPILDI VA U KO'RIK FOYDASIGA HAL QILINDI:**
Reja sakkizala `Info` bandini ham «rejalashtirilmagan» deb sanagan edi. Qayta sanoqda **IN-05** (`unpaid-list.tsx:117` — `t("headline.amountUnit")`) `07-22-PLAN.md` ning `<behavior>` bandida **nomma-nom** turibdi, ya'ni u shu to'lqinda yopiladi. `deferred-items.md` ning jadvalida uning egasi **07-22** deb yozildi, qolgan yettitasi 8-fazaga.
⚠ **IN-04** esa 8-fazada qoldi va sabab jadvalda ochiq: 07-22 o'sha naqshni **faqat o'zi qo'shadigan yangi tugmaga** qo'llaydi; `delivery-list.tsx:141` dagi **mavjud** `disabled` uning qamrovida emas.

## uz-Cyrl tekshiruvi (qo'lda)

Yangi uz-Cyrl matni: **«Кеча аниқланган номувофиқликлар»**. Uchala so'z ham qo'lda tekshirildi — `ns` / `ts` klasterli **o'zlashma so'z yo'q**:

| Lotin | Kirill | Klaster | Xulosa |
|---|---|---|---|
| `Kecha` | `Кеча` | yo'q | sof o'zbek o'zagi |
| `aniqlangan` | `аниқланган` | yo'q (`q` -> `қ`) | sof o'zbek o'zagi |
| `nomuvofiqliklar` | `номувофиқликлар` | yo'q | sof o'zbek o'zagi |

Ya'ni 07-16 da `kvitansiya` -> `квитанси…` bilan o'lchangan translitteratsiya nuqsoni bu satrlarga **umuman tegmaydi**. Eski `Аномалиялар` o'zlashmasi shu bilan birga chiqib ketdi va uning o'rnini `_MORNING_TEXT` allaqachon ishlatadigan atama (`расхождения` / `nomuvofiqlik`) egalladi — ya'ni glossariy **kengaymadi**.

## Known Stubs

Yo'q — bu rejada stub, placeholder yoki simlanmagan komponent yaratilmadi.

## Threat Flags

Yo'q — yangi tarmoq endpointi, auth yo'li, fayl kirish naqshi yoki ishonch chegarasidagi sxema o'zgarishi qo'shilmadi. Aksincha, ikki mavjud yuza **toraydi**: `bot-tests` endi prod sirlarini yuklamaydi (T-07-115/T-07-116) va `404` ning talqini nomlangan detalga qadaldi (T-07-117).

## User Setup Required

Yo'q — tashqi xizmat sozlamasi talab qilinmaydi.

⚠ Lekin **bitta qo'lda tasdiqlash ochiq qoldi**: dev mashinasida `npm run up` yugurtirilib, `docker compose ps` da `bot-service` ko'rinishi. Sabab va o'rnini bosgan mexanik o'lchov yuqorida (`Issues Encountered` 3) va `deferred-items.md` 5-bandida.

## Next Phase Readiness

- **Mezon #3 ning kuzatuv teshigi yopildi:** dayjest juftligining har biri endi o'z izini qoldiradi va uning yo'qligi alert beradi.
- **Bot ishonchliligi:** infratuzilma nosozligi endi foydalanuvchining nuqsoni bo'lib ko'rinmaydi.
- **Ochiq bandlar 8-fazaga tayyor holda yozilgan:** 13 warning + 7 info nomma-nom, sababi va egasi bilan (`deferred-items.md` 7-band).
- **⚠ BLOKER EMAS, LEKIN DARVOZAGA TA'SIR QILADI:** `npm run bot:lint` hozir **qizil** (`test_binding.py`, 5 ta mypy xatosi, 07-21 dan oldin ham mavjud). Faza yakunidagi `npm run gate` zanjiri shu bosqichda to'xtaydi — sabab bu rejaning ishi emas, lekin uni **kimdir** tuzatishi kerak (`deferred-items.md` 8-band).

## Self-Check: PASSED

**Fayllar (5/5 topildi):**
- `tests/unit/test_dev_environment.py`
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-21-SUMMARY.md`
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md`
- `services/bot-service/app/core_client.py`
- `services/core-api/app/repositories/binding_repo.py`

**Commitlar (3/3 topildi):** `b259482`, `e2a2eb9`, `4d8ef49`

**Reja `<done>` mezonlari — o'lchangan:**

| Mezon | Kutilgan | O'lchangan |
|---|---|---|
| `grep -c "\"notify_digest\"" services/core-api/` | 0 | **0** (qolgan uchrashuvlar faqat IZOHlarda, tarixni tushuntiradi) |
| `EXPECTED_COMPONENTS` uzunligi | 11 | **11** |
| `grep -c "anomaly_count" services/core-api/app/jobs/` | 0 | **0** (`notification_meta.py` dagi ikki uchrashuv — izoh va mavjud docstring) |
| `grep -c "write_app_audit" .../binding_repo.py` | 0 | **0** (import ham olib tashlandi) |
| `grep -nE "log\.[a-z]+\(.*detail" .../core_client.py` | 0 | **0** |
| `docker compose config` | xatosiz | **exit 0** |

**Test yugurishlari (hammasi yashil):**
- `tests/unit` (to'liq) + `test_notifications.py` + `test_alerting.py` + `test_outbox.py` + `test_bot_internal_api.py` + `test_capture_schedule.py` + `test_phase7_criteria.py` + `test_outbox_repo.py` — **exit 0**
- `tests/tenancy` (to'liq) — **exit 0**
- `bot-tests pytest -q` — **exit 0**
- core-api: `ruff check` + `ruff format --check` + `mypy` — **toza** (338/339 fayl)
- bot-service: `ruff check` + `ruff format --check` — **toza**; `mypy` — **5 xato**, hammasi tegilmagan `test_binding.py` da (`deferred-items.md` 8-band)

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-13*
