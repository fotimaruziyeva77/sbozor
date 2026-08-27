---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 06
subsystem: notification-delivery
tags: [outbox, telegram, quiet-hours, skip-locked, append-only, allowlist, rls]
requires:
  - "0023_notification_domain — notification_outbox / vendor_telegram_bindings / market_notification_settings"
  - "sbozor_core.enums — OutboxKind / OutboxRecipientKind / OutboxStatus"
  - "tests/fixtures/notification_domain.py — seed_outbox_row / seed_binding / seed_notification_settings"
  - "app/services/alerts.py::AlertSender — 4-fazaning uch taqiqli jo'natuvchisi"
provides:
  - "AlertSender.send_message(text, *, chat_id=None) — YAGONA jo'natuvchi, yuzasi o'smagan"
  - "worker._alert_sender() + TaskiqState.alerts_enabled — Pitfall 9 ning chegarasi"
  - "app/jobs/notification_meta.py — NOTIFICATION_META / NEVER_SUPPRESSED_OUTBOX_KINDS / OUTBOX_PAYLOAD_KEYS / outbox_payload()"
  - "app/repositories/outbox_repo.py — enqueue / claim / resolve_chat_id / mark_* / reschedule / release_expired_leases"
  - "DEFAULT_QUIET_HOURS_START / DEFAULT_QUIET_HOURS_END / DEFAULT_OVERDUE_DAYS"
affects:
  - "07-09 (outbox tik + backoff), 07-12 (kvitansiya chaqiruv joyi), 07-10/07-11 (dayjestlar), 07-13 (BOT-03 eslatmasi)"
tech-stack:
  added: []
  patterns:
    - "yagona jo'natuvchi KENGAYTIRILADI — chat_id metod emas, ARGUMENT (D-23)"
    - "chegara CHAQIRUV JOYIDA, ikkinchi bayroqda emas (Pitfall 9)"
    - "reyestrdan HOSILA bayroq (ALERT_META naqshi) — D-18"
    - "allowlist HAR TUR UCHUN ALOHIDA, birlashma EMAS"
    - "bir bayonotli CTE: FOR UPDATE OF ... SKIP LOCKED + lease_until (capture_repo naqshi)"
    - "quiet oyna LEFT JOIN + COALESCE, yarim tunni kesish shoxi SQL da OCHIQ"
    - "bir qoidaning IKKI IFODASI (SQL darvozasi + Python spetsifikatsiyasi) testda solishtiriladi"
key-files:
  created:
    - services/core-api/app/jobs/notification_meta.py
    - services/core-api/app/repositories/outbox_repo.py
    - tests/unit/test_outbox_policy.py
    - tests/integration/test_outbox_repo.py
  modified:
    - services/core-api/app/services/alerts.py
    - services/core-api/app/worker.py
    - tests/integration/test_alerting.py
decisions:
  - "AlertSender ning ommaviy yuzasi TO'PLAM TENGLIGI bilan qulflandi — len() bir metodni ikkinchisiga almashtirishni ko'rmasdi"
  - "settings.py TEGILMADI: chegara worker._alert_sender() da (enabled=bool(TOKEN)) va vazifalarning birinchi qatorida"
  - "claim/release market_id ni ARGUMENT sifatida oladi — RLS himoya to'ri, aniq filtr so'rovda (capture_repo ning ikki qatlam qoidasi)"
  - "SKIP LOCKED asyncio.gather bilan EMAS, ikki OCHIQ tranzaksiyada o'lchandi — gather sabotajda ham yashil qolardi"
  - "is_quiet_now/is_suppressed_now — qoidaning SPETSIFIKATSIYASI; darvozaning o'zi SQL da va ikkalasi integratsiya testida solishtiriladi"
  - "alerts.py docstringidan taqiqlangan metod nomlari olib tashlandi (03-07 darsi) — da'vo yuza tengligi darvozasiga ko'chdi"
metrics:
  duration: ~110 min
  completed: 2026-08-12
  tasks: 3
  files: 7
---

# Phase 7 Plan 06: Chiquvchi xabar mexanizmining yuragi — Summary

Telegram'ga yozadigan sinf HAMON BITTA va uning ommaviy nomlari to'plami
O'ZGARMADI — `chat_id` **argument** bo'lib qo'shildi; navbat esa ijarali,
append-only va uning quiet-hours darvozasi D-18 istisnosini **reyestrdan
hosila** bayroq bilan hurmat qiladi.

## Nima qurildi

**Task 1 — `AlertSender` kengaydi, yuzasi o'smadi (`e97118b`).**
`send_message(text, *, chat_id=None)`; `_post()` manzilni **argument**
sifatida oladi. `worker._alert_sender()` jo'natuvchini
`enabled=bool(TOKEN)` bilan quradi, `alert_sweep_task` va
`daily_digest_task` esa **chaqiruv joyida** `state.alerts_enabled` bilan
o'raladi. ⛔ `settings.py` **umuman o'zgarmadi**.

**Task 2 — `notification_meta.py` (`a07ff69`).** To'rt yozuvli reyestr;
`NEVER_SUPPRESSED_OUTBOX_KINDS` va `OUTBOX_PAYLOAD_KEYS` undan **hosila**.
`outbox_payload()` allowlisti **har tur uchun alohida** (birlashma emas —
alohida test bilan qulflangan). 13 qatorli `QUIET_HOURS_TABLE`.

**Task 3 — `outbox_repo.py` (`ac8a618`).** Sakkiz funksiya, hammasi
chaqiruvchining tranzaksiyasida. `claim()` — bir bayonotli CTE
(`FOR UPDATE OF o SKIP LOCKED` + `lease_until`), quiet oyna
`markets.timezone` da baholanadi va `market_notification_settings` dan
`LEFT JOIN` + `COALESCE` bilan olinadi.

## O'lchangan dalillar

### ⛔ Mavjud alerting testlari — OLDIN va KEYIN

| O'lchov | Natija |
|---|---|
| `pytest tests/integration/test_alerting.py` **o'zgarishdan OLDIN** (baza `461d5b9`) | **16 test, hammasi yashil** |
| AYNAN o'sha fayl **o'zgarishdan KEYIN** | **19 test, hammasi yashil** (16 eskisi + 3 yangisi) |

⛔ **Birorta mavjud test tuzatilmadi va birorta mavjud chaqiruvchi
o'zgarmadi.** `alerting.py` ning `sender.send_message(text_body)`
chaqiruvlari argumentsiz qoldi — `chat_id` ning standarti `None` bo'lgani
uchun ular tegilmadi.

### Sabotaj 1 — D-18 (Task 2, reja talab qilgan)

`NOTIFICATION_META["payment_receipt"].never_suppressed` vaqtincha `False`
ga o'zgartirildi.

| Darvoza | Natija |
|---|---|
| `test_quiet_hours_table[payment_receipt @ 22:30]` (⛔ **jadvalning 1-qatori**) | **QIZIL** |
| `test_quiet_hours_table[payment_receipt @ 02:00]` (yarim tun jufti) | **QIZIL** |
| `test_never_suppressed_is_derived_from_meta` | **QIZIL** |
| Qolgan **17** test | yashil — ya'ni darvoza aynan D-18 ni o'lchaydi, hammasini emas |

Sabotaj o'lchovdan keyin olib tashlandi (`grep never_suppressed=True` → 1).

### Sabotaj 2 — D-18 ning **SQL** yarmi (Task 3)

`claim()` ning `o.kind = ANY(:never_suppressed)` bandi
`o.kind <> ALL(:never_suppressed)` ga o'zgartirildi (operator xatosi sinfi
— bind parametri joyida qoladi, ya'ni sabotaj **jimgina** o'tishi mumkin
edi).

Natija: **8 test qizardi**, jumladan
`test_the_quiet_window_holds_the_reminder_but_never_the_receipt` va
`test_the_sql_gate_agrees_with_the_specification`.

⚠ **Birinchi urinish RAD ETILDI va bu ham o'lchov:** bandni butunlay
o'chirish `sqlalchemy.exc.ArgumentError` bilan **yig'ish paytida**
yiqildi, ya'ni u D-18 ni emas, bind-parametr e'lonini o'lchagan bo'lardi.
Shuning uchun sabotaj mahsulotda haqiqatan sodir bo'ladigan shaklga
(noto'g'ri operator) almashtirildi.

### Sabotaj 3 — `SKIP LOCKED` (Task 3)

`FOR UPDATE OF o SKIP LOCKED` → `FOR UPDATE OF o`.

| Darvoza | Natija |
|---|---|
| `test_two_open_transactions_never_get_the_same_row_skip_locked` | **QIZIL** (`statement_timeout` → `QueryCanceled`) |
| Qolgan **20** test, jumladan ijara testi | **yashil** |

⛔ Ya'ni `SKIP LOCKED` va `lease_until` **alohida** o'lchanadi va
bittasini o'chirish ikkinchisini yashil qoldiradi — `capture_repo.py`
ning 1-majburiyati aynan shuni talab qiladi.

### Sabotaj 4 — `COALESCE` (Task 3)

Quiet oyna `COALESCE(s.quiet_hours_start, :quiet_start)` o'rniga xom
`s.quiet_hours_start` dan o'qildi (bind parametrlar joyida qoldi).

Natija: **3 test qizardi**, jumladan
`test_a_market_without_a_settings_row_falls_back_to_the_code_defaults`.

⛔ **Nazorat bandi aynan shu sabotaj uchun yozilgan:** quiet oyna
**ichida** `NULL` oyna «to'g'ri» natija bilan **aynan bir xil** ko'rinadi
(`NULL` `WHERE` dan chiqib ketadi). Farq faqat oynadan **tashqarida**
ochiladi — shuning uchun test ikkala paytni ham o'lchaydi.

### Darvozalar

| Darvoza | Natija |
|---|---|
| `pytest tests/unit` | **1166 test yashil** |
| `pytest tests/tenancy` | **690 test yashil** (07-04 ning G7-2/G7-7/G7-8 lari o'z joyida) |
| `pytest tests/integration -m "not sim and not slow"` | **1014 test, 0 yiqilish** |
| `tests/unit/test_outbox_policy.py` | **20 test** |
| `tests/integration/test_outbox_repo.py` | **21 test** |
| `tests/integration/test_alerting.py` | **19 test** |
| `ruff check` + `ruff format --check` + `mypy` (318 fayl) | **toza** |

### Reja talab qilgan mexanik da'volar

| Da'vo | Natija |
|---|---|
| `dir(AlertSender)` ommaviy nomlari | `['aclose', 'enabled', 'send_message']` ✓ |
| `chat_id` — KEYWORD_ONLY, standarti `None` | ✓ |
| `grep -cE "sendPhoto\|sendDocument\|sendMediaGroup\|InputFile\|photo="` `alerts.py` | **0** |
| `grep -nE "log\.(info\|warning\|error)\(.*chat_id"` `alerts.py` | **0** |
| `settings.py` `git diff --name-only` da | **YO'Q** ✓ |
| `NEVER_SUPPRESSED_OUTBOX_KINDS == frozenset({'payment_receipt'})` | ✓ |
| `outbox_payload('payment_receipt', secret='x')` | `ValueError` ✓ |
| `QUIET_HOURS_TABLE` uzunligi | **13** (talab: ≥ 6) |
| `grep -nE "float(\|Decimal\|round("` `notification_meta.py` | **0** |
| `grep -nE "float(\|Decimal\|round(\|balance"` `outbox_repo.py` | **0** |
| `grep -ciE "\bdelete\b"` `outbox_repo.py` | **1** — aynan bitta docstring taqig'i |
| `DELETE FROM notification_outbox` SQL matnida | **0** ✓ |
| `outbox_repo.py` uzunligi | **776 satr** (talab: ≥ 200) |
| Takror `enqueue` → `notification_outbox` da qator soni | **1**, ikkinchi chaqiruv `None` ✓ |

## Rejadan chetlanishlar

### Rule 1 — mavjud kod reja matnidan farq qilgan joyda KOD ustun turdi

**1. [Rule 1] `alerts.py` docstringidan taqiqlangan metod nomlari olib tashlandi**

- **Topildi:** Task 1, akseptans mezonini o'lchayotganda.
  `grep -cE "sendPhoto|sendDocument|sendMediaGroup|InputFile|photo="`
  → **1**, holbuki reja **0** talab qiladi. Moslik **bazadagi commitda
  ham bor edi** (`git show 461d5b9:...` → 1), ya'ni bu 07-06 ning
  regressiyasi EMAS: satr 4-fazadan beri turgan sinf docstringi va u
  taqiqni **tushuntirish** uchun metod nomlarini literal yozgan.
- **Nega muhim:** bu 03-07 ning o'lchangan darsi va 07-02 uni
  `models/notification.py` da bir marta to'lagan — sodda grep darvozasi
  **izohni koddan ajratmaydi**, ya'ni taqiqni tushuntirish darvozani
  **o'z-o'ziga qarshi** qo'yadi va yagona «tuzatish» yo'li darvozaga
  istisno qo'shish bo'lardi.
- **Yechim:** matn tavsifiy shaklga (hujjat / media guruh / xabar
  tahrirlash) qayta yozildi va da'vo **o'lchanadigan joyga ko'chdi**:
  yangi `test_sender_public_surface_did_not_grow` ommaviy nomlarni
  **to'plam tengligi** bilan solishtiradi, ya'ni yangi metod **nima deb
  atalishidan qat'i nazar** ushlanadi — grep esa faqat oldindan sanab
  chiqilgan nomlarni ko'rardi. **Da'vo susaymadi, kuchaydi.**
- **Commit:** `e97118b`

### Rule 2 — rejaning imzosi kod bazasining o'lchangan konventsiyasiga zid edi

**2. [Rule 2] `claim()` va `release_expired_leases()` `market_id` ni ARGUMENT sifatida oladi**

- **Topildi:** Task 3. Reja imzoni `claim(session, *, batch_size,
  lease_seconds, now)` deb bergan, ya'ni tenant filtri **faqat RLS**
  ustida qolardi.
- **Nega muhim:** `capture_repo.py` ochiq yozgan qoida —
  «TENANT FILTRI IKKI QATLAM: RLS policy'si himoya **to'ri**,
  `market_id = :market_id` predikati esa **aniq filtr**; xom SQL'da u
  qo'lda, ko'rinadigan joyda turadi». Bir qatlamli so'rov `alerting.py`
  ning per-market `_tenant_session` naqshi bilan ham mos kelmasdi.
- **Yechim:** argument qo'shildi va u
  `test_claim_without_tenant_context_returns_nothing_and_never_raises`
  bilan o'lchandi (RLS fail-closed + nazorat bandi).
- **Commit:** `ac8a618`

**3. [Rule 2] `SKIP LOCKED` `asyncio.gather` bilan EMAS, ikki ochiq tranzaksiyada o'lchandi**

- **Topildi:** Task 3 testini yozayotganda. Reja `asyncio.gather` ni
  nomlaydi.
- **Nega muhim:** `gather` tartibni **kafolatlamaydi**. Ikki chaqiruv
  ketma-ket bajarilsa ikkinchisi 0 qator oladi (birinchisi ularni
  allaqachon `sent` qilgan) — «kesishmadi» da'vosi **`SKIP LOCKED`
  butunlay olib tashlangan holatda ham** yashil bo'lardi.
- **Yechim:** `test_capture_repo.py` ning o'lchangan shakli: ikkinchi
  sessiya birinchisi **COMMIT qilishidan oldin** chaqiriladi va
  `SET LOCAL statement_timeout = '4000ms'` qulfda osilishni **qizil**
  natijaga aylantiradi. Sabotaj 3 bu tanlovni tasdiqladi.
- **Commit:** `ac8a618`

**4. [Rule 2] Quiet oyna mintaqasi `markets.timezone` dan, literaldan emas**

- **Topildi:** Task 3. Reja «`Asia/Tashkent` da baholanadi» deydi.
- **Nega muhim:** literal yozish loyihada **ikkinchi** qotirilgan
  mintaqa yaratardi. `capture_repo._ENSURE_PLAN` allaqachon
  `AT TIME ZONE m.timezone` ishlatadi va `test_meta.py::
  test_markets_all_use_tashkent_timezone` bugungi tenglikni qo'riqlaydi
  — ya'ni xulq **bir xil**, lekin ikkinchi bozor boshqa mintaqada
  ochilganda kod **o'zi** to'g'ri javob beradi.
- **Commit:** `ac8a618`

### Struktura bo'yicha ongli qaror

**`is_quiet_now()` / `is_suppressed_now()` — qoidaning IKKINCHI IFODASI va
bu ATAYIN nomlangan.** Darvozaning o'zi **SQL da bo'lishi shart**: oyna
har bozorda `market_notification_settings` dan `LEFT JOIN` bilan olinadi
va navbatni xotiraga tortib bo'lmaydi. Lekin rejaning jadval testi
(`QUIET_HOURS_TABLE`) **bajariladigan** funksiyani talab qiladi — aks
holda oyna arifmetikasi testning o'zida yashab, **o'z aksini** o'lchagan
bo'lardi.

⛔ Ikki ifodaning ajralish xavfi **yopilgan, e'tiborsiz qoldirilmagan**:
`test_the_sql_gate_agrees_with_the_specification` to'rt vaqt nuqtasida
HAQIQIY `claim()` natijasini `is_suppressed_now()` ning bashorati bilan
solishtiradi. Sabotaj 2 va 4 ikkalasida ham aynan shu test qizardi.

## Ochiq bandlar

**1. `tests/fixtures/notification_domain.py::ALLOWED_PAYLOAD_KEYS` HAMON
VAQTINCHALIK NUSXA.** 07-04 ning 2-ochiq bandi uning haqiqiy manbasini
(`NOTIFICATION_META[<kind>].payload_keys`) 07-05 ga bergan edi; reyestr
esa aslida **shu rejada** (07-06) tug'ildi, ya'ni topshiriq egasiz qoldi.
Bugun ikki ro'yxat **ajralgan**: fixture `{amount_soum, stall_code,
created_at, service_date, overdue_days, total_due_soum}` biladi, reyestr
esa `{..., paid_at, cashier_name, outstanding_soum, oldest_service_date,
business_date, ...}`. Fayl bu rejaning `files_modified` ro'yxatida
**yo'q** (07-07/07-08 parallel ishlayapti), shuning uchun u
**tegilmadi**; bu rejaning testlari ikkala ro'yxatga ham mos keladigan
payloadlar bilan yozildi yoki to'g'ridan-to'g'ri mahsulotning
`enqueue()` idan yuradi. **Egasi:** fixture faylini o'zgartiradigan
keyingi reja — `ALLOWED_PAYLOAD_KEYS` `OUTBOX_PAYLOAD_KEYS` dan
**hosila** qilinishi kerak, nusxa emas (D-32 ning aynan sinfi).

**2. Backoff formulasi (DQ-3) BU REJADA YOZILMADI va bu reja bo'yicha
to'g'ri.** `reschedule()` faqat `next_attempt_at` **ustunini** boshqaradi;
`min(30s * 4**(attempt-1), 1 soat)` va Telegram ning `retry_after`
ustunligi **07-09** ning ishi. `attempt_count >= 5` -> `failed`
qoidasining chegarasi ham o'sha yerda — bu modul urinish byudjetini
**bilmaydi**.

**3. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Node yarmi (`npm run test:fast` = `pytest tests/unit`) **1166/1166
yashil**. Frontend yarmi (`npm --prefix frontend test`) ishga tushmadi:
worktree'da `frontend/node_modules` **YO'Q** (gitignored). Bu **muhit
bo'shlig'i, kod nuqsoni emas** va u bu rejadan MUSTAQIL:
`git diff --name-only 461d5b9 HEAD` — **yettala fayl ham** Python
(`services/core-api/**` yoki `tests/**`), birorta frontend fayli
**yo'q** (`grep -c "^frontend/"` → **0**). Egasi: orkestrator
(07-02 va 07-04 da ham aynan shu band edi).

**4. Izolyatsiyalangan compose loyihasida SeaweedFS bucket'i YO'Q edi —
va bu KOD NUQSONI EMAS, ISBOTLANDI.** `docker compose -p sbozor-af99c2d7`
YANGI, bo'sh `seaweed` volume yaratadi; `ops/seaweedfs/s3.json` esa
identitetga faqat `sbozor-snapshots` **ichidagi** amallarni beradi,
bucket **yaratishni** emas. Natijada to'rtta test
(`test_snapshot_api.py` ning uchtasi va `test_phase6_criteria.py::
test_sc2_...`) `StorageError: AccessDenied (status=403)` bilan qizardi.
⛔ **Taxmin qilinmadi, o'lchandi:** `weed shell` bilan
`s3.bucket.create -name sbozor-snapshots` bajarilgach **o'sha to'rt test
ham yashil bo'ldi** va to'liq integratsiya to'plami **0 yiqilish** berdi.
Egasi: orkestrator — asosiy `sbozor` stekida bu volume allaqachon
to'ldirilgan, ya'ni band faqat parallel worktree stekiga tegishli.

## Known Stubs

Yo'q. Bu reja UI yoki API yuzasi qurmaydi; birorta bo'sh qiymat renderga
oqmaydi. `resolve_chat_id()` ning `None` natijasi **stub emas**, u
hujjatlashtirilgan va o'lchangan mahsulot holati («sotuvchi hali
ulanmagan») — `test_resolve_chat_id_follows_the_active_binding_not_the_revoked_one`
uni ochiq assert qiladi.

## Threat Flags

Yo'q. Yangi tarmoq endpointi, auth yo'li, fayl kirishi yoki sxema
o'zgarishi qo'shilmadi; yangi `SECURITY DEFINER` funksiya **yo'q**
(07-04 ning `EXPECTED_DEFINER_FUNCTIONS` = 21 tenglik darvozasi
**yashil** qoldi). Aksincha, reja `<threat_model>` dagi yettala
mitigatsiyani ham bajardi:

| Threat ID | Qanday yopildi |
|---|---|
| T-07-25 | `AlertSender` yuzasi TO'PLAM TENGLIGI bilan; rasm metodlari grepi → 0 |
| T-07-26 | `log.*` chaqiruvlarida `chat_id` yo'q (grep darvozasi → 0) |
| T-07-27 | `_validate_error_type()` — uzunlik + probel/URL rad etiladi (5 qatorli jadval testi) |
| T-07-28 | D-18 metadan hosila; sabotaj 1 (Python) va 2 (SQL) bilan o'lchandi |
| T-07-29 | `ON CONFLICT DO NOTHING` + ikki ochiq tranzaksiyali `claim` testi |
| T-07-30 | `enabled=bool(TOKEN)` + `state.alerts_enabled`; xulqiy test `sender.enabled is True` ni talab qiladi |
| T-07-31 | `release_expired_leases()` — `attempt_count` oshirilmaydi (alohida test) |
| T-07-SC | Yangi paket **yo'q** — `pyproject.toml` va `uv.lock` tegilmadi |

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `services/core-api/app/jobs/notification_meta.py` ✓
- `services/core-api/app/repositories/outbox_repo.py` ✓
- `tests/unit/test_outbox_policy.py` ✓
- `tests/integration/test_outbox_repo.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-06-SUMMARY.md` ✓

Commitlar mavjud: `e97118b` · `a07ff69` · `ac8a618` (baza `461d5b9`).
Birorta commitda fayl o'chirilishi **YO'Q** (`git diff --diff-filter=D`
uchala commitda ham bo'sh). O'zgargan fayllar reja ro'yxatidan
**chiqmadi** — `git diff --name-only 461d5b9 HEAD` aynan **7 fayl** va
hammasi `files_modified` da.

⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi (parallel ijrochilar
to'qnashuvining oldi olinadi).
