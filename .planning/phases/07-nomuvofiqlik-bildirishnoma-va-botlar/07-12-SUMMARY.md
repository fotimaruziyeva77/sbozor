---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 12
subsystem: payment-receipt
tags: [cash-05, outbox, atomicity, idempotency, quiet-hours, allowlist, d-23]
requires:
  - "app/repositories/outbox_repo.py::enqueue — 07-06 ning append-only navbati"
  - "app/jobs/notification_meta.py::outbox_payload / NOTIFICATION_META — 07-06 reyestri"
  - "app/repositories/payment_repo.py::create_payment — (row, created) shartnomasi (D-21)"
  - "app/repositories/user_repo.py::list_profiles — kassir `full_name` i (A8)"
provides:
  - "POST /payments ning 6.5-QADAMI — kvitansiya niyati AYNAN O'SHA tranzaksiyada"
  - "dedupe_key = receipt:{payment_id} — takror so'rovda AYNAN o'sha kalit"
  - "tests/integration/test_receipt_outbox.py — CASH-05 ning 8 xulqiy o'lchovi"
affects:
  - "07-09 (outbox tik bu qatorlarni yetkazadi), 07-11 (sotuvchi boti matnni quradi)"
tech-stack:
  added: []
  patterns:
    - "atomiklik CHAQIRUV JOYIDA: o'sha `session`, oraliq `commit` YO'Q"
    - "ikki qatlamli idempotentlik — ilova sharti BIRINCHI, `UNIQUE` cheklov IKKINCHI"
    - "«bir tranzaksiya» da'vosi FAQAT teskari yo'nalishda isbotlanadi"
    - "sabotaj nishoni 6.5-QADAMDAN KEYINGI qadam (`write_app_audit`)"
    - "nazorat bandi ikki joyda: sabotajsiz takror + `respx` tuzog'ining qurollanishi"
    - "kutilgan `payload` kalitlari REYESTRDAN, fixture nusxasidan EMAS"
key-files:
  created:
    - tests/integration/test_receipt_outbox.py
  modified:
    - services/core-api/app/api/v1/payments.py
    - tests/integration/test_payments_api.py
    - tests/integration/test_phase6_criteria.py
    - tests/tenancy/test_cross_tenant.py
decisions:
  - "6.5-QADAM 6 DAN KEYIN va 7 DAN OLDIN — `dedupe_key` ichida `payment_id` bor, ya'ni qatordan oldin yozib bo'lmaydi"
  - "Sabotaj nishoni `write_app_audit` — u 6.5 DAN KEYIN turadi; undan oldingi nuqta «niyat yozilganmi?» savolini umuman bermasdi"
  - "`test_receipt_and_payment_share_one_transaction` IKKI QADAMLI: sabotaj bilan 0/0, `monkeypatch.undo()` dan keyin AYNAN o'sha tana bilan 1/1 — usiz 422/409/404 ham «yashil» berardi"
  - "`respx` tuzog'i O'Z NAZORATI bilan: `call_count == 0` dan keyin zond chaqiruv `call_count == 1` beradi — aks holda test o'z uskunasining ko'rligini mahsulot fazilati deb o'qirdi"
  - "Kutilgan `payload` kalitlari `NOTIFICATION_META[payment_receipt].payload_keys` dan — `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` allaqachon ajralgan"
  - "`_TransactionSabotage` O'Z SINFI — yalang'och `RuntimeError` `payment_repo` ning Pitfall 3 ini ham tutardi"
metrics:
  duration: ~75 min
  completed: 2026-08-12
  tasks: 2
  files: 5
---

# Phase 7 Plan 12: To'lov kvitansiyasi (CASH-05) Summary

Kassir tugmani bosgan payt sotuvchining kvitansiya niyati **o'sha to'lov
qatori bilan bitta tranzaksiyada** tug'iladi — va bu da'vo ⛔ **ikki
tomonlama** o'lchandi: oqim 6.5-QADAMDAN keyin yiqitilganda `payments` da
ham, `notification_outbox` da ham **0** qator qoladi.

## Nima qurildi

**Task 1 — `POST /payments` ning 6.5-QADAMI (`0d91284`).**
6-QADAM (`create_payment`) bilan 7-QADAM (CASH-02 auditi) **orasida**;
`outbox_repo.enqueue()` marshrutning **o'z** `session` i bilan chaqiriladi
va bu blokda ⛔ **birorta `commit` yo'q** — tranzaksiyani
`deps.get_tenant_session()` o'z joyida yopadi. `dedupe_key =
f"receipt:{row.payment_id}"`, `payload` esa `outbox_payload()` allowlisti
ostida (`amount_soum`, `stall_code`, `paid_at`, `cashier_name`).
`reverse_payment()` ga ⛔ **hech nima qo'shilmadi** va bu **ongli rad
etish** sifatida docstringda yozildi.

**Task 2 — `test_receipt_outbox.py` (`af9544c`).** **8 test**: ketma-ket
takror, **parallel** takror (`asyncio.gather`), `payload` kalitlarining
to'plam tengligi, kassir ismining javobga chiqmasligi, «bir tranzaksiya»
ning ikki tomonlama isboti, D-23 (`respx`), D-18 (quiet hours) va
stornoning kvitansiya yozmasligi.

## O'lchangan dalillar

### ⛔ To'rt sabotaj — ikki qatlam ALOHIDA o'lchandi

Reja bitta sabotajni talab qilgan (`dedupe_key` -> `uuid4()`). U bajarildi
— va natijasi **ikkinchi va uchinchi sabotajni majburiy qildi**: birinchisi
`UNIQUE` cheklovining o'zini umuman qo'zg'atmagan.

| # | Sabotaj | Natija |
|---|---|---|
| 1 | `dedupe_key=f"receipt:{uuid4()}"` (reja talab qilgani) | **1 QIZIL** — `test_receipt_is_enqueued_once_per_payment` (kalit SHAKLI); qolgan 7 yashil |
| 2 | `if created:` -> `if True:` (ilova sharti OLIB TASHLANDI, kalit to'g'ri) | ⛔ **8/8 YASHIL** — ya'ni `UNIQUE (market_id, dedupe_key)` **yolg'iz o'zi** chiziqni ushlaydi |
| 3 | ikkalasi birga (`if True:` + `uuid4()`) | **2 QIZIL**, jumladan `test_two_concurrent_requests_enqueue_one_receipt`: `assert 2 == 1` |
| 4 | 6.5-QADAMDAN keyin `await session.commit()` | **QIZIL** — `test_receipt_and_payment_share_one_transaction`: `assert 1 == 0` (to'lov qatori qoldi) |

⛔ **2 va 3 birgalikda rejaning eng qimmat jumlasini isbotlaydi** —
«himoya ILOVA SHARTIDA emas, CHEKLOVIDA». Sabotaj 2 cheklovning yolg'iz
yetarli ekanini ko'rsatadi; sabotaj 3 esa parallel testning cheklov
buzilishini ⛔ **haqiqatan ko'ra olishini** — usiz «cheklov ishlayapti»
da'vosi o'lchanmagan taxmin bo'lib qolardi.

⛔ **4 «bir tranzaksiya» ning O'ZINI o'lchaydi** va u ⛔ **toza natija**
berdi (yig'ish xatosi emas, plumbing nosozligi emas): so'rov tugadi,
keyingi qadam yiqildi va **to'lov qatori bazada qoldi**. Aynan shu holat —
«pul yozildi, keyin nimadir yiqildi, lekin hech nima orqaga qaytmadi» —
D-02 ning ikkinchi nizosining tug'ilish nuqtasi.

⚠ Har bir sabotaj **`ruff check` dan o'tkazildi** (07-06 ning darsi):
`ReferenceError` sinfidagi yiqilish D-21 ni emas, nomning mavjudligini
o'lchagan bo'lardi. Sabotaj 1 va 3 uchun `uuid4` importi **ataylab**
qo'shildi va o'lchovdan keyin olib tashlandi.

### Rejaning mexanik da'volari

| Da'vo | Natija |
|---|---|
| `grep -c "outbox_repo.enqueue" payments.py` | **1** ✓ |
| `grep -cE "await session\.commit\(\)" payments.py` — OLDIN (`4aec616`) / KEYIN | **0 / 0** — 6.5-QADAM yangi `commit` qo'shmagan ✓ |
| `payload` kalitlari to'plami | **aynan** `{amount_soum, stall_code, paid_at, cashier_name}` ✓ |
| `PaymentResponse.model_fields` | `[amount_soum, created_at, kind, method, payment_id, reversed, service_date, stall_code]` — `cashier_name`/`full_name` ⛔ **YO'Q** ✓ |
| `dedupe_key` shakli | `receipt:{payment_id}`, takror so'rovda AYNAN o'sha ✓ |
| Storno -> navbatda yangi qator | **YO'Q** (`count(*)` o'zgarmadi) ✓ |
| `respx` chaqiruvlari (to'lov marshruti) | **0**; nazorat zondidan keyin **1** ✓ |
| Yangi paket | **YO'Q** — `pyproject.toml`/`uv.lock` tegilmadi ✓ |

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/integration/test_receipt_outbox.py` | **8 test, hammasi yashil** |
| `pytest tests/integration/test_receipt_outbox.py tests/integration/test_payments_api.py` | **39 test, 0 yiqilish** |
| `pytest tests/tenancy` | ⛔ **exit 0, 0 yiqilish** (G7-6 / `test_personal_data_coverage.py` o'z joyida) |
| `pytest tests/unit` | **0 yiqilish** |
| `pytest tests/integration -m "not sim and not slow"` | **0 yiqilish, 5 skip** (2-yugurish; 1-yugurishdagi yagona qizil — FLAKE, pastda) |
| `pytest tests/integration/test_outbox_repo.py` (yolg'iz) | **21 test yashil** |
| `ruff check .` + `ruff format --check .` + `mypy .` (325 fayl) | **toza** |

## Rejadan chetlanishlar

### Rule 3 — yangi qadam UCH mavjud fixture teardownini yiqitardi

**1. [Rule 3 - Blocking] `notification_outbox` tozalash uch faylga qo'shildi**

- **Topildi:** Task 1 tugagach, `files_modified` ro'yxatidan tashqaridagi
  chaqiruvchilarni tekshirayotganda.
- **Muammo:** 6.5-QADAM tufayli HTTP orqali yozilgan **har** to'lov endi
  navbat qatori ham qoldiradi. `fk_notification_outbox_vendor` da
  `ondelete` ⛔ **YO'Q** (NO ACTION), ya'ni qoldiq qator
  `cleanup_market_domain()` / `cleanup_billing_domain()` ning sotuvchi va
  bozor `DELETE` ini **FK buzilishi** bilan yiqitardi. Nosozlik o'z
  faylida emas, ⛔ **keyingi test faylining seed'ida** ko'rinardi — ya'ni
  sabab va simptom bir-biridan uzoqda bo'lardi.
- **Nima uchun bu `files_modified` dan chiqish OQLANADI:** uchala fayl ham
  `POST /api/v1/payments` ni **haqiqiy** chaqiradi
  (`test_cross_tenant.py` matritsasi A bozoriga qator yozadi,
  `test_phase6_criteria.py` SC#4/SC#5 ham) va ular ⛔ **bu o'zgarish
  tufayli** buziladi — pre-existing nosozlik emas.
- **Yechim:** har uch teardownga bitta `DELETE FROM notification_outbox
  WHERE market_id = ...` qatori sabab izohi bilan qo'shildi.
- **Fayllar:** `tests/integration/test_payments_api.py`,
  `tests/integration/test_phase6_criteria.py`,
  `tests/tenancy/test_cross_tenant.py`
- **Commit:** `af9544c`

### Reja matnidan ONGLI chetlanishlar

**2. Reja 4 (parallel bilan 5) test so'ragan — yozilgani 8**

Uchta qo'shimcha test **rejaning akseptans mezonlaridan** tug'ildi va
ularsiz o'sha mezonlar o'lchanmagan bo'lardi:

- `test_the_receipt_payload_carries_exactly_the_registry_keys` —
  «`payload` kalitlari to'plami ⛔ **aynan** to'rttasi» mezoni;
- `test_the_cashier_name_never_reaches_the_http_response` — «javob
  modelida kassir ismi **yo'q**» mezoni, ⛔ **javob tanasining xom matni**
  ustida (maydon nomlari ro'yxati boshqa nom bilan qaytarilgan ismni
  ko'rmasdi);
- `test_a_reversal_writes_no_receipt` — «storno kvitansiya yozmaydi»
  mezoni. ⚠ O'lchov `count(*)` ning **o'zgarmasligi** ustida, «0» ustida
  emas: storno o'zidan oldingi to'lovni talab qiladi, ya'ni navbatda
  bitta qator ALLAQACHON bor va «0» kutish testni **ifodalab
  bo'lmaydigan** qilardi.

**3. `test_receipt_and_payment_share_one_transaction` IKKI QADAMLI**

Reja «ikkala jadvalda ham 0 qator» deydi. Yolg'iz bu da'vo ⛔ **so'rov
6.5-QADAMGA umuman yetmagan** holatda ham rost: 422 (bo'sh kvota
to'plami), 409 (smena yo'q), 404 (rasta topilmadi) — uchalasida ham ikkala
jadval bo'sh. Shuning uchun test `monkeypatch.undo()` dan keyin ⛔ **aynan
o'sha tana** bilan ikkinchi so'rov yuboradi va **1/1** ni talab qiladi.

⚠ Tananing chetlanishli bo'lishi (`reason_code=partial_day` + kvotadan
tashqari summa) ⛔ **majburiy**: `write_app_audit()` faqat `created and
override_reason is not None` shoxida chaqiriladi, ya'ni oddiy to'lovda
sabotaj **umuman bajarilmasdi** va jimgina yashil qolardi.

**4. Quiet-hours vaqti QOTIRILMAYDI — u `next_attempt_at` dan hosila**

Reja «soat 22:30 ga o'rnatiladi» deydi. `next_attempt_at` ni ⛔ **marshrut**
yozadi (`server_default` = `now()`) va uni test boshqara olmaydi.
Qotirilgan sana bilan test kechasi 23:00 dan keyin yugurganda «22:30»
o'tmishda qolardi va qator `next_attempt_at <= :now` sharti bilan — ya'ni
quiet-hours darvozasiga ⛔ **umuman yetmasdan** — chiqib ketardi.
`_quiet_moment_after()` sanani qatorning O'ZIDAN oladi.

⚠ Bundan tashqari test oynaning **haqiqatan** 21:00–08:00 ekanini bazadan
o'qib tekshiradi (`quiet_window()`): bu shart taxmin qilinsa va
`server_default` o'zgarsa, test **butunlay boshqa savolni** o'lchay
boshlardi (22:30 oynadan tashqarida qolib, darvozasiz ham yashil bo'lardi).

## Topilgan, LEKIN TUZATILMAGAN nuqson (07-06 ning fayli, egasi boshqa)

⛔ **`tests/integration/test_outbox_repo.py::test_the_oldest_row_is_
claimed_first` — LATENT FLAKE, va sabab TESTDA, mahsulotda emas.**

- **Qanday ko'rindi:** to'liq integratsiya to'plamining **1-yugurishida**
  qizardi, **2-yugurishida** o'sha buyruq bilan **yashil** bo'ldi; yolg'iz
  yugurtirilganda (`pytest tests/integration/test_outbox_repo.py`)
  **21/21 yashil**.
- **Nima aynan yiqildi:** ⛔ qatorlar **to'g'ri tanlangan** — faqat
  **tartibi almashgan**: `assert [ids[1], ids[0]] == [ids[0], ids[1]]`.
  Begona qator YO'Q, qator soni to'g'ri.
- **Sabab:** `_CLAIM_DUE` ning `ORDER BY o.created_at, o.id` bandi ⛔ **CTE
  ICHIDA** (`WITH due AS (...)`) va u FAQAT **qaysi** qatorlar `LIMIT` ga
  tushishini belgilaydi. Tashqi `UPDATE ... FROM due ... RETURNING` ning
  **chiqish tartibi** PostgreSQL da ⛔ **kafolatlanmagan** — u join
  rejasiga bog'liq va statistika o'zgarganda (to'liq to'plamdan keyin
  jadval o'lik qatorlar bilan boshqacha ko'rinadi) reja ham o'zgaradi.
  Test esa **ro'yxat tengligi** bilan tartiqni da'vo qiladi.
- **Nega BU REJA SABABCHISI EMAS — o'lchandi, taxmin qilinmadi:**
  `test_outbox_repo.py` alifbo tartibida `test_payments_api.py`,
  `test_phase6_criteria.py` va `test_receipt_outbox.py` dan ⛔ **OLDIN**
  yuradi (`o` < `p` < `r`), ya'ni bu rejaning birorta qatori u
  yugurayotgan paytda mavjud ham emas. Bu rejaning uchala tegilgan test
  fayli ham undan keyin keladi.
- **Nega tuzatilmadi:** fayl bu rejaning `files_modified` ida **yo'q** va
  u 07-09 bilan **bir to'lqinda** (07-09 aynan `outbox` tikini yozadi).
  Uni bu yerda o'zgartirish ikki rejani bitta faylda to'qnashtirardi.
- **To'g'ri tuzatish (keyingi egaga):** da'voni ikkiga bo'lish — **qaysi**
  qatorlar olingani `set` tengligi bilan, **tartib** esa `RETURNING` dan
  emas, alohida `SELECT ... ORDER BY created_at` bilan; yoki tashqi
  bayonotga `ORDER BY` qo'shish. Egasi: **07-09**.

## Ochiq bandlar

**1. `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` HAMON
VAQTINCHALIK NUSXA va u endi ⛔ ANIQ O'LCHANGAN DARAJADA ajralgan.**
Fixture `{amount_soum, stall_code, created_at, service_date, overdue_days,
total_due_soum}` biladi; `payment_receipt` ning haqiqiy kalitlari esa
`{amount_soum, stall_code, paid_at, cashier_name}` — ya'ni ⛔ **`paid_at`
va `cashier_name` fixture'da UMUMAN YO'Q**. Amaliy oqibat: bu rejaning
mahsulot payloadini `seed_outbox_row()` bilan **takrorlab bo'lmaydi**.

Fayl bu rejaning `files_modified` ida yo'q va u **tegilmadi** (07-09/07-11/
07-13 parallel ishlayapti). Buning o'rniga `test_receipt_outbox.py` har
bir kvitansiya qatorini ⛔ **mahsulot yo'lidan** (`POST /payments`) oladi
va kutilgan kalitlarni ⛔ **reyestrdan** (`NOTIFICATION_META`) o'qiydi —
ya'ni bu reja ajralgan nusxaga umuman tayanmaydi. **Egasi:** fixture
faylini o'zgartiradigan keyingi reja; `ALLOWED_PAYLOAD_KEYS`
`OUTBOX_PAYLOAD_KEYS` dan **hosila** bo'lishi kerak, nusxa emas (D-32 ning
sinfi). Bu 07-06 ning 1-ochiq bandining **davomi**, yangisi emas.

**2. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Python yarmi (`pytest tests/unit`) **yashil**. Frontend yarmi
(`npm --prefix frontend test`) ishga tushmadi: worktree'da
`frontend/node_modules` **YO'Q** (gitignored). Bu ⛔ **muhit bo'shlig'i,
kod nuqsoni emas** va u bu rejadan MUSTAQIL — `git diff --name-only
4aec616 HEAD` ⛔ **beshala fayl ham** Python (`services/core-api/**` yoki
`tests/**`), `grep -c "^frontend/"` -> ⛔ **0**. Egasi: orkestrator
(07-02/07-04/07-06 da ham aynan shu band edi).

**3. `.env` va `ops/seaweedfs/s3.json` worktree'ga QO'LDA ko'chirildi,
SeaweedFS bucket'i esa QO'LDA yaratildi.** Ikkalasi ham gitignored, ya'ni
yangi worktree ularsiz keladi va `docker compose` `s3.json` ni **katalog**
qilib yaratib, `storage` ni sog'lomsiz qoldirardi. Izolyatsiyalangan
loyihada (`-p sbozor-a0507f09`) bucket ham yangi volume'da yo'q edi —
`weed shell` bilan `s3.bucket.create -name sbozor-snapshots` bajarildi.
Bu **kod nuqsoni emas**, parallel-worktree muhitining bandi va u 07-06 da
ham qayd etilgan. Egasi: orkestrator.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi qurmaydi va birorta bo'sh qiymat renderga
oqmaydi. ⚠ `cashier_name` ning `None` bo'lishi ⛔ **stub emas**: `users.
full_name` `0001_identity` dan beri NULLABLE va `outbox_payload()` `None`
qiymatni **tashlab yuboradi** — matn quruvchisi «kalit bormi?» degan bitta
savol bilan ishlaydi (07-06 ning yozilgan konvensiyasi). Bu
hujjatlashtirilgan mahsulot holati, yozilmagan yo'l emas.

⚠ **Kvitansiya sotuvchi Telegram'ga ULANMAGAN bo'lsa ham yoziladi** va bu
ham stub emas: `chat_id` jo'natish paytida hal qilinadi
(`outbox_repo.resolve_chat_id`, 07-06) va qator navbatda **kutadi**.
Marshrutning bog'lanishni tekshirmasligi ⛔ **ongli qaror**: tekshirish
pul yozuvini bildirishnoma holatiga bog'lardi (D-23 ning teskarisi).

## Threat Flags

Yo'q. Yangi tarmoq endpointi, auth yo'li, fayl kirishi yoki sxema
o'zgarishi qo'shilmadi — marshrutlar to'plami **o'zgarmadi**
(`payments.py` da yangi `@router` yo'q) va migratsiya yozilmadi. Reja
`<threat_model>` dagi beshala mitigatsiya ham bajarildi:

| Threat ID | Qanday yopildi |
|---|---|
| T-07-71 | `dedupe_key = receipt:{payment_id}` + `UNIQUE`; ketma-ket **va** parallel test; sabotaj 1/2/3 bilan o'lchandi |
| T-07-72 | Bitta tranzaksiya; ikki tomonlama isbot + nazorat bandi; sabotaj 4 bilan o'lchandi |
| T-07-73 | `respx` chaqiruvlari **0**, tuzoq qurollangani nazorat zondi bilan isbotlangan |
| T-07-74 | Ism faqat outbox `payload` ida; `PaymentResponse.model_fields` da YO'Q; javob **xom matnida** ham yo'q; `tests/tenancy` yashil |
| T-07-75 | Kvitansiya quiet oyna ichida OLINADI; nazorat `overdue_reminder` OLINMAYDI; oyna bazadan o'qib tasdiqlanadi |
| T-07-SC | Yangi paket **YO'Q** |

## Self-Check: PASSED

Yaratilgan/o'zgartirilgan fayllar diskda mavjud:
- `services/core-api/app/api/v1/payments.py` ✓
- `tests/integration/test_receipt_outbox.py` ✓
- `tests/integration/test_payments_api.py` ✓
- `tests/integration/test_phase6_criteria.py` ✓
- `tests/tenancy/test_cross_tenant.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-12-SUMMARY.md` ✓

Commitlar: `0d91284` (feat) · `af9544c` (test) — baza `4aec616`.
Birorta commitda fayl o'chirilishi **YO'Q** (`git diff --diff-filter=D`
ikkala commitda ham bo'sh). `git diff --name-only 4aec616 HEAD` — aynan
**5 fayl**, `frontend/` dan **0 ta**.

⛔ **TEGILMAGAN fayllar** (reja va orkestrator talabi):
`app/schemas.py`, `app/main.py`, `app/worker.py`, `app/services/alerts.py`,
`app/repositories/outbox_repo.py`, `app/jobs/notification_meta.py`,
`tests/integration/test_outbox.py`, `tests/fixtures/notification_domain.py`
— ⛔ **birortasi ham** `git diff --name-only 4aec616 HEAD` da yo'q.

⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi.
