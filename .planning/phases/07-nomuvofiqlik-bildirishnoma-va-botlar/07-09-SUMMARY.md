---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 09
subsystem: notification-delivery
tags: [outbox, telegram, backoff, throttling, secrets, ast-gate, html-escape]
requires:
  - "app/repositories/outbox_repo.py — claim / resolve_chat_id / mark_* / reschedule / release_expired_leases (07-06)"
  - "app/jobs/notification_meta.py — NOTIFICATION_META / outbox_payload() (07-06)"
  - "app/services/alerts.py::AlertSender — 4-fazaning uch taqiqli jo'natuvchisi"
  - "app/jobs/retention.py::active_market_ids — SECURITY DEFINER yuzasi, YAGONA chaqiruv nuqtasi"
  - "sbozor_core.money.format_soum — YANGI formatlash yozilmadi"
provides:
  - "app/jobs/outbox.py::outbox_tick(sessionmaker, sender, *, now, monotonic, sleep) — navbatni haydaydigan tik"
  - "OUTBOX_COMPONENT / MAX_ATTEMPTS / OUTBOX_BATCH_SIZE / OUTBOX_LEASE_SECONDS / UNRESOLVED_RETRY_SECONDS"
  - "OutboxDisposition / OutboxFailure / OutboxTickResult / UnresolvedRecipient"
  - "AlertSender.last_failure -> SendFailure | None — sirsiz uch fakt (ContextVar)"
  - "alerts.last_message_id() — provider_message_id ning YAGONA manbai"
  - "G7-1 (test_outbox_surface.py), G7-4 (test_outbox_secrets.py), G7-5 (test_outbox.py)"
affects:
  - "07-14 (cron registratsiyasi — OUTBOX_COMPONENT nomi va job callable)"
  - "07-12 (kvitansiya enqueue + test_telegram_failure_does_not_block_payment ning ikkinchi bosqichi)"
  - "07-10/07-11/07-13 (dayjest va eslatma navbatga yozadi, jo'natish haqida hech nima bilmaydi)"
  - "07-16 (UI matni: `delivered` = «Telegram qabul qildi»)"
tech-stack:
  added: []
  patterns:
    - "istisno OBYEKTI qatlamdan CHIQMAYDI — uch sirsiz fakt (`SendFailure`) chiqadi"
    - "holat `ContextVar` da, instans atributida EMAS — bir jarayondagi parallel vazifalar"
    - "AST darvozasi (grep EMAS) — docstringdagi taqiq tushuntirishi darvozani qizartirmaydi"
    - "darvoza uchinchi qoidasi TAQIQ emas, TALAB: `error_type=` ning SHAKLI"
    - "soat va uyqu ARGUMENT — throttling haqiqiy `sleep` siz o'lchanadi"
    - "ijara COMMIT qilinadi, HTTP chaqiruvi tranzaksiyadan TASHQARIDA"
    - "sonlar HISOBLANADI: batch = tezlik x byudjet, MAX_ATTEMPTS = ~42 daqiqa"
key-files:
  created:
    - services/core-api/app/jobs/outbox.py
    - tests/unit/test_outbox_surface.py
    - tests/unit/test_outbox_secrets.py
    - tests/integration/test_outbox.py
  modified:
    - services/core-api/app/services/alerts.py
    - services/core-api/app/repositories/outbox_repo.py
    - tests/integration/test_alerting.py
decisions:
  - "`last_failure` — XOSSA va `ContextVar` da: `AlertSender` TaskiqState da bitta nusxa, vazifalar parallel"
  - "`provider_message_id` modul funksiyasi (`last_message_id()`) orqali: sinf yuzasi 4 nomda QULFLANGAN qoldi"
  - "`error_type=` darvozasi SHAKL talab qiladi (`__name__` yoki `.error_type`) — denylist yolg'iz o'zi yetmasdi"
  - "manzilsiz qator byudjetni yemaydi: MAX_ATTEMPTS unga qo'llanmaydi + 15 daqiqa kechiktiriladi"
  - "`str(error)` `alerts.py` dan olib tashlandi — bugun xavfsiz edi, lekin darvoza nozik farqni ko'rmaydi"
  - "[Rule 1] `_validate_error_type` `\"http\"` taqig'i `HTTPStatusError` ni rad etardi -> `\"://\"` + isidentifier()"
metrics:
  duration: ~95 min
  completed: 2026-08-12
  tasks: 3
  files: 7
---

# Phase 7 Plan 09: Chiquvchi xabar navbatining tiki — Summary

Navbat endi HAYDALADI: `403` `blocked` beradi va qayta urinilmaydi, `429`
Telegram bergan `retry_after` bilan qaytadi, beshinchi urinishdan keyin
`failed` — va bu yo'lning HECH BIR nuqtasida bot tokeni jurnalga, xato
tanasiga yoki `last_error_type` ustuniga tushmaydi.

## Nima qurildi

**Task 1 — tik va jo'natuvchining bitta yangi xossasi (`defe2e7`).**
`app/jobs/outbox.py` (1042 satr): `outbox_tick()` ijarani bo'shatadi,
partiyani `claim()` bilan oladi (bu QISQA tranzaksiyada va COMMIT bilan —
HTTP chaqiruvi tranzaksiya ICHIDA ushlab turilmaydi), manzilni jo'natishdan
BEVOSITA oldin o'qiydi, matnni `kind` + `payload` dan quradi va natijaga
qarab `mark_delivered` / `mark_blocked` / `mark_failed` / `reschedule`
chaqiradi. `alerts.py` ga AYNAN BITTA o'qish-uchun xossa qo'shildi —
`last_failure`.

**Task 2 — ikki strukturaviy darvoza (`3e61e0f`).** `test_outbox_surface.py`
(matn skaneri, G7-1) va `test_outbox_secrets.py` (AST, G7-4). Ikkalasining
ro'yxatlari ham mahsulotdan IMPORT QILINMAYDI va ikkalasida ham quyi chegara
bor.

**Task 3 — xulqiy o'lchovlar (`4f90808`).** `test_outbox.py` — 11 test,
`respx` bilan, haqiqiy tarmoqqa chiqmaydi va haqiqiy `sleep` kutmaydi.

## O'lchangan dalillar

### ⛔ Mavjud alerting testlari — OLDIN va KEYIN

| O'lchov | Natija |
|---|---|
| `test_alerting.py` **07-06 dan keyin** (baza `80af5be`) | **19 test, hammasi yashil** |
| AYNAN o'sha fayl **bu rejadan keyin** | **22 test, hammasi yashil** (19 + 3 yangisi) |

⛔ **16 ta eski test TAHRIRLANMADI.** O'zgargan yagona mavjud test —
`test_sender_public_surface_did_not_grow`, ya'ni 07-06 ning O'ZI qo'shgan
qulf testi: reja uni yangi literal to'plamga (`+ last_failure`) o'tkazishni
ATAYIN talab qilgan va o'zgarish sababi test docstringida to'liq yozilgan
(nima qo'shildi, nega xossa, nega metod emas, nega 1-taqiq
kuchsizlanmaydi).

### ⛔ Sabotaj 1 — G7-4 (AST, reja talab qilgan)

`outbox.py::_swallow()` ga qo'shildi: `log.warning("sabotage_one", detail=str(exc))`.

| Darvoza | Natija |
|---|---|
| `test_no_exception_text_leaves_the_scanned_modules[.../outbox.py]` | **QIZIL** |
| `test_no_exception_text_leaves_the_scanned_modules[.../alerts.py]` | **yashil** |
| Qolgan **25** darvoza testi | **yashil** |

Xato xabari aniq qatorni ko'rsatdi (`outbox.py:672`) — ya'ni sabotaj
HAQIQATAN parse qilingan va o'lchov kompilyatsiya xatosini emas, taqiqni
o'lchagan (07-06 ning o'lchangan darsi: yiqilgan sabotaj noto'g'ri narsani
o'lchaydi). Parametrizatsiyaning ikkinchi yarmi yashil qolgani darvozaning
MANZILLI ekanini isbotlaydi.

### ⛔ Sabotaj 2 — G7-1 (yuza)

`outbox.py::_deliver()` ga **kod** sifatida qo'shildi:
`await sender.sendPhoto(str(chat_id), photo=body)`.

| Darvoza | Natija |
|---|---|
| `test_no_media_bot_api_method_appears_in_scanned_modules[sendPhoto]` | **QIZIL** |
| `test_no_media_bot_api_method_appears_in_scanned_modules[photo=]` | **QIZIL** |
| Qolgan **15** taqiqlangan token parametri | yashil |

⛔ **Ikkala sabotaj ham o'lchovdan keyin OLIB TASHLANDI** —
`git diff --stat services/core-api/app/jobs/outbox.py` commitdan keyin
BO'SH.

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/unit` | **1194 test yashil** (07-06 da 1166 edi — +28) |
| `pytest tests/tenancy` | **690 test yashil** (o'zgarmadi) |
| `pytest tests/integration -m "not sim and not slow"` | **899 yashil, 5 skip, 0 kod yiqilishi** |
| `tests/unit/test_outbox_surface.py` + `test_outbox_secrets.py` | **28 test** (talab: ≥ 7) |
| `tests/integration/test_outbox.py` | **11 test** (talab: ≥ 9), **~46 s** |
| `tests/integration/test_alerting.py` | **22 test** |
| `tests/integration/test_outbox_repo.py` (07-06 niki) | **21 test yashil** |
| `ruff check .` + `ruff format --check .` (331 fayl) + `mypy .` (322 fayl) | **toza** |

⚠ Integratsiya to'plamining birinchi yugurishida **4 test** `StorageError:
AccessDenied (status=403)` bilan qizardi. Bu **muhit bo'shlig'i, kod nuqsoni
EMAS va u TAXMIN QILINMADI, O'LCHANDI**: `weed shell` bilan
`s3.bucket.create -name sbozor-snapshots` bajarilgach **o'sha to'rt test ham
yashil bo'ldi** (`31 passed`). Aynan shu band 07-06 da ham qayd etilgan.

### Reja talab qilgan mexanik da'volar

| Da'vo | Natija |
|---|---|
| `OUTBOX_COMPONENT == "outbox_tick"` va `MAX_ATTEMPTS == 5` | ✓ |
| Backoff jadvali `attempt=1..5` | **`[30, 120, 480, 1920, 3600]`** — aynan |
| `retry_after=7` berilganda kutish | **7 s** (formulaning 30 s i EMAS) |
| `403` -> `blocked`, ikkinchi tikda `respx` sanog'i | **1 -> 1** (o'smadi) |
| `400` -> `failed` | `_classify()` da `{400, 401, 404}` |
| `html.escape`: payload `A <b> B` | matnda `&lt;b&gt;` **bor**, `<b>` **yo'q** |
| `resolve_chat_id` `None` -> qator `pending`, HTTP so'rovi | **0 so'rov**, `blocked` EMAS |
| `grep -cE "/snapshots/.*image\|presign\|object_key"` `outbox.py` | **0** |
| `grep -cE "float(\|Decimal\|round(\|balance"` `outbox.py` | **0** |
| `dir(AlertSender)` ommaviy nomlari | `['aclose', 'enabled', 'last_failure', 'send_message']` ✓ |
| `TELEGRAM_SEND_METHOD == "sendMessage"` | ✓ |
| `grep -cE "sendPhoto\|sendDocument\|sendMediaGroup\|InputFile\|photo="` `alerts.py` | **0** |
| `AlertSender.__dict__["last_failure"]` — `property` | ✓ |
| `SendFailure` maydonlari | `{'status', 'error_type', 'retry_after'}` — aynan |
| `enabled=False` -> `send_message()` `False`, `last_failure` | **`None`** ✓ |
| `grep -cE "^from app\.\|^import app\."` `test_outbox_surface.py` | **0** (ro'yxat LITERAL) |
| `outbox.py` uzunligi | **1042 satr** (talab: ≥ 260) |
| `worker.py` `git diff --name-only` da | **YO'Q** ✓ (cron 07-14 niki) |
| `git diff --diff-filter=D` (baza -> HEAD) | **bo'sh** — birorta fayl o'chirilmadi |
| `git diff --name-only \| grep -c "^frontend/"` | **0** |

## Rejadan chetlanishlar

### Rule 1 — mahsulotdagi nuqson tikni ULAGANDA ochildi

**1. [Rule 1] `outbox_repo._validate_error_type()` `HTTPStatusError` ni RAD ETARDI**

- **Topildi:** Task 3, birinchi yugurishda. To'rt test
  `outbox_state_not_written:ValueError` bilan qizardi.
- **Sabab:** `_ERROR_TYPE_FORBIDDEN` ro'yxatida `"http"` parchasi bor edi va
  u `str(exc)` ni emas, **`httpx` istisno SINFLARINING NOMLARINI** to'sardi:
  `HTTPStatusError`, `HTTPError` — hammasi «http» bilan boshlanadi.
- **Nega jiddiy:** D-04 ga TO'LIQ MOS keladigan qiymat
  (`type(exc).__name__`) yozib bo'lmasdi. Mahsulotda bu shuni bildirardi:
  Telegram ning **har bir status xatosi** `ValueError` berardi, qator
  yakuniy holatga **umuman o'tolmasdi**, ijara muddati o'tgach `pending` ga
  qaytardi va **cheksiz** aylanardi — xatosiz, jimgina, `last_error_type`
  hech qachon yozilmagan holda. Ya'ni BOT-04 ning butun taksonomiyasi
  amalda ishlamasdi.
- **Yechim:** `"http"` -> `"://"` (har qanday URL uni ham, `"/"` ni ham
  o'z ichiga oladi, ya'ni URL avvalgidek rad etiladi) va ustiga
  **`isidentifier()` SHAKL talabi** qo'shildi — bu denylist emas,
  **ALLOWLIST**: Python sinf nomi HAR DOIM identifikator, `str(exc)` esa
  (nuqta, ikki nuqta, qavs, probel bilan) HECH QACHON emas.
- **Da'vo susaymadi, kuchaydi:** 07-06 ning beshala rad etish holati ham
  QIZIL bo'lib qoldi (`test_a_leaky_error_type_is_rejected_at_the_repository`
  — 5 parametr, hammasi yashil), chunki har biri `isidentifier()` dan ham,
  qolgan parchalardan ham o'tolmaydi.
- **⚠ FAYL BU REJANING `files_modified` RO'YXATIDA YO'Q.** Chetlanish ongli:
  (a) `outbox_repo.py` ni 07-06 yozgan va u ALLAQACHON merge qilingan, ya'ni
  birorta parallel ijrochi unga tegmayapti (07-07 — `reconciliation_repo`,
  07-08 — `main`/`settings`/`alerting`, 07-12 — `api/v1/payments`);
  (b) muqobil yo'l — chegarani `outbox.py` da TAKRORLASH — bir qoidaning
  ikki ifodasini yaratardi va ular jimgina ajralib ketardi (D-32 sinfi).
- **Commit:** `4f90808`

### Rule 3 — rejaning o'zi talab qilgan, lekin sezmagan bloklovchi bo'shliq

**2. [Rule 3] `alerts.last_message_id()` — `provider_message_id` ning yagona yo'li**

- **Topildi:** Task 1, `_mark_delivered()` ni yozayotganda.
- **Bo'shliq:** reja `test_delivered_records_the_provider_message_id` ni
  talab qiladi va 07-06 ning `mark_delivered(..., provider_message_id: int)`
  imzosi qiymatni **MAJBURIY** qiladi. Lekin Telegram ning `message_id` iga
  boradigan ikkala tabiiy yo'l ham YOPIQ:
  1. `send_message()` ning qaytish tipini o'zgartirish — `bool` kontrakti
     3-taqiqning o'zi va **mavjud test uni `is False` bilan qulflagan**
     (`test_alerting.py:1055`), o'sha test esa 16 ta tegilmaydigan testdan;
  2. sinfga ikkinchi xossa qo'shish — reja ommaviy yuzani AYNAN to'rt
     nomga qulflagan.
- **Nega bu 1-taqiq bilan bir sinfdagi bo'shliq:** reja `403`/`429` farqini
  «BOT-04 ning butun marshrutlashi uchun bloklovchi bo'shliq» deb atagan va
  uni bitta xossa bilan yopgan. `message_id` — **aynan o'sha sinfdagi
  ikkinchi holat** va reja uni sezmagan.
- **Yechim:** modul darajasidagi o'qish-uchun funksiya
  (`ContextVar` ustida, `last_failure` bilan AYNAN bir xil hayot sikli).
  U (a) `AlertSender` ga atribut QO'SHMAYDI, ya'ni literal to'plam darvozasi
  TEGILMAGAN qoladi; (b) **yangi Bot API metodi emas** —
  `TELEGRAM_SEND_METHOD` hamon yagona qiymat; (c) sirsiz — javob tanasidan
  olingan butun son.
- **⛔ VA U «TESHIK» BO'LIB QOLMADI: qaror O'LCHANADI.**
  `test_outbox_surface.py::test_the_message_id_accessor_is_module_level_not_a_sender_attribute`
  funksiyaning modul darajasida ekanini VA `AlertSender` da YO'Qligini
  assert qiladi — ya'ni kimdir uni ertaga sinfga ko'chirsa, darvoza
  qizaradi.
- **Commit:** `defe2e7`

### Rule 2 — rejaning O'Z akseptans mezoni mavjud kodni o'zgartirishni talab qildi

**3. [Rule 2] `log.warning("alert_not_delivered", error=str(error))` olib tashlandi**

- **Topildi:** Task 1. Reja ochiq talab qiladi: «`alerts.py` ham G7-4 ning
  AST skaneriga kiradi va u yerda `str(exc)`/`repr(exc)` -> **0**».
  Mavjud satr `except AlertError as error:` bloki ichida va `error` —
  `ExceptHandler.name`, ya'ni AST darvozasi uni ushlaydi.
- **Nega satr BUGUN xavfsiz edi:** `_failure()` `AlertError` ni faqat uch
  sirsiz faktdan quradi.
- **Nega baribir o'zgartirildi:** darvoza bu nozik farqni **ko'ra olmaydi** —
  `str(<istisno>)` shakli `AlertError` uchun xavfsiz, `httpx` istisnosi uchun
  esa tokenni olib chiqadi va ikkalasi AST da **bir xil ko'rinadi**. Yagona
  muqobil — darvozaga istisno qo'shish, ya'ni uni sekin-asta teshikka
  aylantirish (03-07 ning o'lchangan darsi).
- **Diagnostika SUSAYMADI, KUCHAYDI:** bitta erkin matn o'rniga uchta
  STRUKTURAVIY maydon (`status`, `error_type`, `retry_after`) — ular
  filtrlanadi, agregatlanadi va sirni tashiy olmaydi.
- **Commit:** `defe2e7`

### Chegara — reja matnini AYNAN bajarib bo'lmadi va sabab yozildi

**4. [Chegara] Manzilsiz qatorning `attempt_count` i: reja «oshmaydi» deydi**

- **Reja matni:** «`resolve_chat_id` `None` qaytarganda qator `pending` da
  qoladi va `attempt_count` **oshmaydi**».
- **Nima to'sdi:** `attempt_count` ni oshiradigan **yagona joy** —
  `outbox_repo.claim()` ning CTE si, va u qatorni QAYTARISHDAN OLDIN
  oshiradi. `reschedule()` esa sanoqqa ATAYIN tegmaydi (07-06 ning qarori).
  Ya'ni «oshmasin» ni **so'zma-so'z** bajarish uchun `outbox_repo` ga sanoqni
  qaytaradigan yangi funksiya kerak bo'lardi — bu esa `claim()` ning «urinish
  shu yerda sanaladi» invariantini buzardi.
- **Niyat (byudjet yeyilmasin) IKKI mustaqil mexanizm bilan bajarildi:**
  1. `MAX_ATTEMPTS` tekshiruvi `UNRESOLVED` shoxga **qo'llanmaydi** — ya'ni
     bog'lanmagan sotuvchining kvitansiyasi **hech qachon `failed`
     bo'lmaydi**;
  2. qator `UNRESOLVED_RETRY_SECONDS` (15 daqiqa) ga **kechiktiriladi** —
     ya'ni keyingi tiklar uni umuman **olmaydi** va sanoq tik-be-tik
     o'smaydi.
- **Da'vo qanday o'lchandi (holat nomidan emas, HTTP sanog'idan):**
  `respx` chaqiruvlari soni **0** — ya'ni «urinish qilinmadi» fakti
  to'g'ridan-to'g'ri isbotlangan; ikkinchi tikdan keyin `attempt_count`
  **o'zgarmagan**.
- **Commit:** `4f90808`

**5. [Chegara] `_MESSAGE_ID_UNKNOWN = 0` — `200`, lekin identifikator o'qilmagan**

Telegram `200` qaytardi (xabar CHATGA JOYLANDI), ammo javob tanasi
kutilmagan shaklda. Qatorni `retry` ga tushirish xabarni **ikkinchi marta**
yuborardi — ya'ni yetkazilganni «yetkazilmadi» deb o'qish D-21 ning
teskarisi bo'lardi. Nol sentinel haqiqiy identifikator bilan hech qachon
aralashmaydi (Telegram identifikatorlari 1 dan boshlanadi) va shox
`log.warning("outbox_message_id_unreadable")` bilan **ko'rinadi**.

## Ochiq bandlar

**1. `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` HAMON
VAQTINCHALIK NUSXA va u reyestrdan AJRALGAN.** 07-06 bu bandni ochiq
qoldirgan; bugun ham `cashier_name`, `paid_at`, `outstanding_soum` va
dayjest kalitlari fixture ro'yxatida **yo'q**. Fayl bu rejaning
`files_modified` ro'yxatida ham **yo'q**, shuning uchun u **tegilmadi**:
`html.escape()` testi fixture o'rniga **mahsulotning `enqueue()` idan**
yuradi va shu bilan reyestrning HAQIQIY allowlisti ustidan o'lchaydi.
**Egasi:** fixture faylini o'zgartiradigan keyingi reja —
`ALLOWED_PAYLOAD_KEYS` `OUTBOX_PAYLOAD_KEYS` dan **hosila** qilinishi kerak.

**2. `_LOCALE` — matn tili hozircha BITTA va bu OCHIQ yozilgan chegara.**
`vendors` da til ustuni **yo'q** (2-faza sxemasi), ya'ni «sotuvchining tili»
bugun **bilinmaydi**. Uni bozor sozlamasidan taxmin qilish yolg'on aniqlik
berardi. Matn quruvchilari `locale` ni **argument** sifatida oladi, ya'ni til
ustuni qo'shilgan kun o'zgarish CHAQIRUV JOYIDA bo'ladi. **Egasi:** uch
tilli bot matnlari rejasi (BOT-01/07-15 doirasi).

**3. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Python yarmi (`pytest tests/unit`) **1194/1194 yashil**. Frontend yarmi
ishga tushmadi: worktree'da `frontend/node_modules` **YO'Q** (gitignored).
Bu **muhit bo'shlig'i, kod nuqsoni emas** va u bu rejadan MUSTAQIL:
`git diff --name-only 80af5be HEAD` — **yettala fayl ham** Python
(`services/core-api/**` yoki `tests/**`), `grep -c "^frontend/"` -> **0**.
**Egasi:** orkestrator (07-02, 07-04 va 07-06 da ham aynan shu band edi).

**4. Izolyatsiyalangan compose loyihasida SeaweedFS bucket'i YO'Q edi — va bu
KOD NUQSONI EMAS, ISBOTLANDI.** To'rt test `AccessDenied (status=403)` bilan
qizardi; `s3.bucket.create -name sbozor-snapshots` dan keyin **o'sha to'rt
test ham yashil** (`31 passed`). **Egasi:** orkestrator — asosiy `sbozor`
stekida volume allaqachon to'ldirilgan.

**5. Cron registratsiyasi — 07-14 niki va u ATAYIN qilinmadi.** Job faqat
funksiya sifatida mavjud; `OUTBOX_COMPONENT` (`"outbox_tick"`) 07-14 dagi
`EXPECTED_COMPONENTS` va `watched` yozuvlari bilan **AYNAN bir xil**
bo'lishi shart — aks holda jadval jobni yugurtirardi, kuzatuv esa boshqa
nomni kutib «yurak urishi yo'q» alertini mangu ko'tarib turardi.

**6. `test_telegram_failure_does_not_block_payment` IKKI BOSQICHLI va uning
birinchi yarmi shu yerda.** Bugun u ALOQANING YO'QLIGINI o'lchaydi (tik
istisno ko'tarmaydi; bitta qatorning nosozligi qolganlarini to'xtatmaydi;
jo'natuvchi kutilmagan istisno berganda ham shu ikkisi kuchda qoladi).
`POST /payments` ning `201` i **07-12** da qo'shiladi. Chegara test
docstringida OCHIQ yozilgan.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi qurmaydi va birorta bo'sh qiymat renderga
oqmaydi. Ikki qiymat **stub emas, hujjatlashtirilgan va o'lchangan mahsulot
holati**:

- `resolve_chat_id()` ning `None` natijasi — «sotuvchi hali ulanmagan»
  (`test_unresolved_chat_stays_pending_without_consuming_an_attempt` uni
  ochiq assert qiladi, jumladan `blocked` EMASligini);
- `_MESSAGE_ID_UNKNOWN` — «Telegram qabul qildi, identifikator o'qilmadi»
  (yuqoridagi 5-chetlanish).

To'rtala `OutboxKind` uchun ham matn quruvchisi **mavjud** (`_BUILDERS`
to'plami yopiq); dayjest va eslatma turlariga hali hech kim navbatga
YOZMAYDI, lekin bu shu rejaning stubi emas — u 07-10/07-11/07-13 ning ishi.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, yangi auth yo'li, yangi fayl kirishi va sxema
o'zgarishi **qo'shilmadi**; migratsiya yozilmadi, yangi paket
o'rnatilmadi (`pyproject.toml` va `uv.lock` tegilmadi). `outbox_repo.py`
dagi yagona o'zgarish — validatsiyani **QATTIQLASHTIRISH**, ya'ni yuza
toraydi.

Reja `<threat_model>` idagi mitigatsiyalar:

| Threat ID | Qanday yopildi |
|---|---|
| T-07-46 | G7-4 (AST, sabotaj bilan) **va** G7-5 (xulqiy: `capture_logs` + `caplog` + ustun, ikki nazorat bandi bilan) |
| T-07-47 | G7-1 — media metodlari va argumentlari ikki modul bo'ylab 0; matnda `/snapshots/*/image` yo'q (grep -> 0) |
| T-07-48 | `_swallow()` + tikning davom etishi; `_ExplodingSender` bilan xulqiy test |
| T-07-49 | `_Throttle` — per-chat 1 msg/s (soxta soat bilan o'lchandi), global 25 msg/s; `MAX_ATTEMPTS=5` + 1 soatlik chegara |
| T-07-50 | `delivered` ning ma'nosi UCH joyda bir xil: `outbox.py` modul docstringi, `_mark_delivered()` va test docstringi |
| T-07-51 | `_text()` -> `html.escape()`; xulqiy test (`A <b> B` -> `&lt;b&gt;`, xom `<b>` YO'Q) |
| T-07-52 | `_classify()` faqat STATUS KODIGA qaraydi; xato matni hech qayerda solishtirilmaydi |
| T-07-53 | Ijara + `SKIP LOCKED` (07-06) + `test_two_ticks_do_not_send_twice` (`respx` sanog'i = 1) |
| T-07-54 | `chat_id` na `log.*` argumentiga, na yurak urishi detaliga tushadi (detalda faqat SONLAR — alohida assert) |
| T-07-SC | Yangi paket **yo'q** |

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `services/core-api/app/jobs/outbox.py` ✓
- `tests/unit/test_outbox_surface.py` ✓
- `tests/unit/test_outbox_secrets.py` ✓
- `tests/integration/test_outbox.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-09-SUMMARY.md` ✓

Commitlar mavjud: `defe2e7` · `3e61e0f` · `4f90808` (baza `80af5be`).
Birorta commitda fayl o'chirilishi **YO'Q**
(`git diff --diff-filter=D 80af5be HEAD` bo'sh). O'zgargan fayllar —
**7 ta**, oltitasi rejaning `files_modified` ro'yxatidan, yettinchisi
(`outbox_repo.py`) yuqorida 1-chetlanish sifatida ochiq hujjatlashtirilgan.

⚠ `worker.py` ATAYIN TEGILMADI — cron registratsiyasi 07-14 niki.
⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi.
