---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 19
subsystem: api
tags: [outbox, telegram, postgres, sqlalchemy, backoff, lease, taskiq]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "07-06 outbox repozitoriysi (ijara, quiet-hours, append-only), 07-09 tik va jo'natuvchi, 07-14 cron reyestri va deterministik ORDER BY, 07-16 yetkazilganlik yuzasi"
provides:
  - "outbox_tick() ning HAQIQIY vaqt deadline'i (monotonic, ikki tekshiruv nuqtasi)"
  - "attempt_count ning yangi semantikasi: FAQAT haqiqiy jo'natish urinishi sanaladi"
  - "outbox_repo.defer_unresolved() — manzilsiz qatorni byudjetsiz kechiktirish"
  - "OutboxClaim.created_at — qatorning yoshi jo'natuvchiga chiqdi"
  - "UNRESOLVED_MAX_AGE_HOURS = 72 — navbatning konvergentligi (head-of-line bloklashga qarshi)"
  - "OutboxTickResult.skipped_markets / budget_exhausted + yurak urishi detali"
affects: [07-verification, 08-*, bot-service, reconciliation-delivery-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vaqt byudjeti MONOTON soatdan, saqlanadigan payt DEVOR soatidan (_moment())"
    - "Terminal chegara ikki xil o'lchov bilan: urinish soni (RETRY) va qator YOSHI (UNRESOLVED)"
    - "Bayroq argumenti o'rniga ALOHIDA funksiya (defer_unresolved vs reschedule) — niyat chaqiruv joyida ko'rinadi"
    - "Darvozani (grep) buzmaslik uchun taqiqlangan shakl izohda LITERAL yozilmaydi"

key-files:
  created: []
  modified:
    - services/core-api/app/jobs/outbox.py
    - services/core-api/app/repositories/outbox_repo.py
    - tests/integration/test_outbox.py
    - tests/integration/test_outbox_repo.py
    - tests/integration/test_delivery_surface.py

key-decisions:
  - "UNRESOLVED terminal chegarasi YOSH bo'yicha (72 soat), urinish soni bo'yicha EMAS — hisoblagich bu shoxda umuman oshmaydi va sanoq chegarasi YANGI USTUN (migratsiya) talab qilardi"
  - "Byudjet tugaganda qolgan claim lar uchun _settle() CHAQIRILMAYDI — ijara o'z-o'zidan bo'shaydi; «yuborilmadi» `failed` ga aylantirilmaydi"
  - "attempt_count uch terminal bayonotda oshadi (_MARK_DELIVERED, _MARK_TERMINAL, _RESCHEDULE); defer_unresolved va release_expired_leases tegmaydi"
  - "_next_attempt_at() ga claim.attempt_count + 1 uzatiladi — DQ-3 jadvali (30s/2daq/8daq/32daq) o'z joyida qoladi"
  - "budget_exhausted yurak urishiga int(...) bilan chiqadi: isinstance(True, int) rost, ya'ni bayroq «faqat sanoqlar» darvozasidan jimgina o'tib ketardi"
  - "Soxta soat monotonic() chaqiruvlarini emas, CHIQQAN XABAR sonini kuzatadi — refaktoring testni sababsiz qizartirmaydi"

patterns-established:
  - "Ikki nusxaga qarshi da'vo CHIQQAN SO'ROV ustidan o'lchanadi (holat ustuni yetarli emas)"
  - "«Navbatdan chiqdi» yagona haqiqiy o'lchovi — IKKINCHI TIK claimed == 0"
  - "Qatorning yoshi testda ANIQ beriladi (_SET_CREATED_AT), server soatiga qoldirilmaydi"

requirements-completed: [RECON-03, CASH-05, BOT-04]

# Metrics
duration: 60min
completed: 2026-08-12
---

# Phase 07 Plan 19: Navbat mexanikasining uch nuqsoni Summary

**Tik endi `monotonic()` deadline'ini ikki nuqtada o'lchaydi, `attempt_count` faqat haqiqiy jo'natishdan keyin oshadi, manzilsiz qator esa 72 soatdan keyin `failed` bo'lib navbatdan chiqadi — ya'ni kvitansiya ikki marta ketmaydi, kech ulangan sotuvchining byudjeti yeyilmaydi va navbat konvergent bo'ladi.**

## Performance

- **Duration:** ~60 min
- **Started:** 2026-08-12T17:36:00Z
- **Completed:** 2026-08-12T18:36:00Z
- **Tasks:** 3 (ikkitasi TDD: RED -> GREEN)
- **Files modified:** 5 (+1 planning: `deferred-items.md`)

## Accomplishments

- **B-3 yopildi — ikki nusxa endi STRUKTURAVIY imkonsiz.** `outbox_tick()` boshida
  `started = monotonic()` va `deadline = started + OUTBOX_TICK_BUDGET_SECONDS` olinadi;
  tekshiruv HAR BOZORDAN va HAR QATORDAN oldin bajariladi. Byudjet tugaganda qolgan
  bozorlar `skipped_markets` ga yoziladi, joriy bozorning qolgan `claim` lari esa
  ⛔ **holatsiz** qoldiriladi — ijara o'z-o'zidan bo'shaydi va keyingi tik ularni qayta
  oladi. Tik `OUTBOX_LEASE_SECONDS` (120 s) dan uzun yashay olmaydi.
- **B-4 yopildi — urinish hisobi jo'natish joyiga ko'chdi.** `_CLAIM_DUE` ning `claimed`
  CTE si hisoblagichga UMUMAN tegmaydi; `attempt_count = attempt_count + 1` uch terminal
  bayonotga (`_MARK_DELIVERED`, `_MARK_TERMINAL`, `_RESCHEDULE`) ko'chdi. Yangi
  `defer_unresolved()` manzilsiz qatorni byudjetsiz kechiktiradi.
- **B-1(2) yopildi — navbat konvergent.** `UNRESOLVED_MAX_AGE_HOURS = 72` bilan manzilsiz
  qator terminal holatga (`failed`, sabab `UnresolvedRecipient`) chiqadi va
  `ORDER BY o.created_at` ning boshini bo'shatadi.
- **Vaqt to'g'rilandi:** `_moment()` ijara va backoff'ni tikning BOSHIDAGI emas, JORIY
  paytdan hisoblaydi (monoton soatdan o'tgan vaqt + devor soati).
- **WR-07/WR-08 yopildi:** to'rt tiplanmagan bind parametri tiplandi
  (`now`/`next_attempt_at` -> `TIMESTAMPTZ`, `provider_message_id` -> `BigInteger`),
  `OutboxDisposition.FAILED` ning yolg'on jumlasi olib tashlandi,
  `OUTBOX_TICK_BUDGET_SECONDS` `__all__` ga chiqdi.

## Task Commits

1. **Task 1 (RED): urinish hisobi darvozalari** — `926fd84` (test)
2. **Task 1 (GREEN): hisob `claim()` dan jo'natish joyiga ko'chdi** — `bc5bc4b` (fix)
3. **Task 2 (RED): byudjet va yosh chegarasi darvozalari** — `a5b95f1` (test)
4. **Task 2 (GREEN): deadline + terminal chegara + arifmetika** — `9b19e17` (fix)
5. **Task 3: yetkazilganlik yuzasi qayta o'qildi + deferred-items** — `7469d13` (docs)

_TDD tsikli: har ikkala mahsulot vazifasi RED (`test(...)`) va GREEN (`fix(...)`) bilan
alohida commit qilindi; REFACTOR bosqichi kerak bo'lmadi._

## Files Created/Modified

- `services/core-api/app/jobs/outbox.py` — `UNRESOLVED_MAX_AGE_HOURS`, `_moment()`,
  ikkita deadline tekshiruvi, `OutboxTickResult.skipped_markets`/`budget_exhausted`,
  `_settle()` ning ikki terminal chegarasi, `_next_attempt_at(claim.attempt_count + 1, ...)`
- `services/core-api/app/repositories/outbox_repo.py` — `_CLAIM_DUE` hisoblagichga
  tegmaydi va `created_at` ni chiqaradi; `OutboxClaim.created_at`; `defer_unresolved()` +
  `_DEFER_UNRESOLVED`; uch terminal bayonotda hisob; tiplangan bind parametrlari
- `tests/integration/test_outbox_repo.py` — olti da'vo (claim hisoblamaydi, uchala
  terminal yozuvchi aynan 1 ga oshiradi, `defer_unresolved` tegmaydi, `created_at`
  qatordan keladi, D-04 chegarasi yangi yo'lda ham)
- `tests/integration/test_outbox.py` — beshta yangi xulqiy darvoza + `_BudgetClock`
- `tests/integration/test_delivery_surface.py` — `attempt_count` ning yangi MA'NOSI
  docstringlarda (T-07-108); da'vo shakli SUSAYTIRILMADI
- `.planning/phases/07-.../deferred-items.md` — qamrovdan tashqaridagi flaki qayd etildi

## Decisions Made

- **Yosh chegarasi, sanoq chegarasi emas.** Task 1 dan keyin `UNRESOLVED` shoxi
  hisoblagichni oshirmaydi, ya'ni sanoq bo'yicha chegara yangi ustun (migratsiya) talab
  qilardi. `created_at` esa jadvalda ALLAQACHON bor va `_CLAIM_DUE` uni o'qiydi — shuning
  uchun `OutboxClaim` ga bitta maydon qo'shish yetarli bo'ldi. **`migrations/` diffda
  YO'Q.**
- **72 soat hisoblangan:** `UNRESOLVED_RETRY_SECONDS` (15 daq) bo'yicha ~288 qayta
  jadvallash = ulanish uchun uch kun; undan keyin xabarning O'ZI eskirgan (dayjest AYNAN
  BIR KUNGA tegishli).
- **Byudjet tugashi `failed` EMAS.** Qolgan `claim` lar uchun `_settle()` chaqirilmaydi.
- **`budget_exhausted` yurak urishiga `int(...)` bilan.** `isinstance(True, int)` Python'da
  ROST, ya'ni xom `bool` «detalda faqat sonlar» darvozasidan jimgina o'tib ketardi.
- **Soxta soat `sent` ga qaraydi**, `monotonic()` chaqiruvlari soniga emas: chaqiruvlar
  soni ichki tuzilishga bog'liq va refaktoringda testni sababsiz qizartirardi.

## Sabotaj natijalari

⛔ Uchala sabotaj ham qo'llandi, o'lchandi va `git checkout -- <fayl>` bilan qaytarildi.
`git status --porcelain services/` sabotajlardan keyin **BO'SH**.

| # | Sabotaj | Kutilgan | HAQIQIY natija |
|---|---------|----------|----------------|
| **S-1** | `outbox_tick()` dagi ikkala deadline tekshiruvi olib tashlandi (`grep -c` -> 0) | (1) va (2) qizaradi | ⛔ **AYNAN 2 QIZIL:** `test_a_full_queue_stops_at_the_budget_and_leaves_the_rest`, `test_a_row_left_by_an_exhausted_tick_is_delivered_once`. Jurnalda `budget_exhausted=0 skipped_markets=0 delivered=6` — ya'ni tik butun navbatni byudjetsiz yugurib chiqdi |
| **S-2** | `_settle()` dagi `UNRESOLVED` yosh chegarasi olib tashlandi | (4) qizaradi, (5) YASHIL qoladi | ⛔ **AYNAN 1 QIZIL:** `test_an_undeliverable_row_reaches_a_terminal_state_and_leaves_the_queue`. `test_a_young_unresolved_row_stays_in_the_queue` **yashil qoldi** — darvoza ANIQ, «hammasini failed qil» yechimi uni o'tkazmasdi |
| **S-3** | `_CLAIM_DUE` ga `attempt_count = o.attempt_count + 1` qaytarildi | (3) qizaradi | ⛔ **7 QIZIL** (kutilganidan keng): `test_outbox.py` da 6 ta — `test_403_marks_blocked_and_never_retries`, `test_five_attempts_then_failed`, `test_two_ticks_do_not_send_twice`, `test_a_full_queue_stops_at_the_budget_and_leaves_the_rest`, `test_an_unbound_vendor_does_not_burn_the_attempt_budget`, `test_a_young_unresolved_row_stays_in_the_queue`; `test_outbox_repo.py` da 1 ta — `test_claim_takes_a_lease_without_counting_an_attempt` |

## Verifikatsiya

| O'lchov | Natija |
|---|---|
| `pytest test_outbox.py test_outbox_repo.py test_delivery_surface.py` | ⛔ **54 yashil** |
| `pytest tests/integration -m "not sim and not slow"` | 1 yiqilish — ⛔ **07-19 sababi EMAS** (pastda), 4 ERROR — `--no-deps` bilan `storage` ko'tarilmagani uchun; ular alohida `storage` bilan qayta yugurtirilib **31/31 yashil** bo'ldi |
| `pytest tests/unit` | ⛔ **hammasi yashil** (G7-4 `test_outbox_secrets.py` va G7-5 `test_outbox_surface.py` ichida) |
| `ruff check .` / `ruff format --check .` / `mypy .` | ⛔ **toza** |
| `git diff --name-only` da `migrations/` | ⛔ **YO'Q** |
| `pyproject.toml` / `uv.lock` diffda | ⛔ **YO'Q** (T-07-SC: yangi paket o'rnatilmadi) |
| Task 1 grep darvozalari | `attempt_count = o.attempt_count + 1` -> **0**; `attempt_count = attempt_count + 1` -> **3**; `async def defer_unresolved` -> **1** |
| Task 2 grep darvozalari | `monotonic() >= deadline` -> **2**; `UNRESOLVED_MAX_AGE_HOURS` -> **5**; `byudjet tugadi` -> **0**; `OUTBOX_TICK_BUDGET_SECONDS` `__all__` da -> **ha** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Backoff jadvali yangi hisob semantikasiga moslandi**
- **Found during:** Task 2
- **Issue:** Reja `RETRY` chegarasini `claim.attempt_count + 1 >= MAX_ATTEMPTS` ga
  o'zgartirishni aytadi, lekin `_next_attempt_at(claim.attempt_count, ...)` chaqiruvini
  tilga olmaydi. `claim()` endi hisoblagichni oshirmagani uchun xom `attempt_count`
  bilan chaqirilgan formula butun jadvalni BIR QADAM surib yuborardi: 1-urinish 30 s,
  **2-urinish ham 30 s** (`exponent = max(1-1, 0) = 0`) va hokazo — ya'ni DQ-3 ning
  `30s -> 2daq -> 8daq -> 32daq` zinasi qulardi va `429` lar zanjiri tug'ilardi.
- **Fix:** `_next_attempt_at(claim.attempt_count + 1, ...)`; funksiyaning `Args` bloki
  «hozir yozilayotgan urinishning RAQAMI» deb qayta yozildi va sabab ochiq qo'yildi.
- **Files modified:** `services/core-api/app/jobs/outbox.py`
- **Verification:** `test_an_unbound_vendor_does_not_burn_the_attempt_budget` birinchi
  haqiqiy urinishdan keyin `next_attempt_at` ni AYNAN 30 s ga tekshiradi;
  `test_five_attempts_then_failed` (mavjud, tegilmagan) beshta urinishni ushlab turadi.
- **Committed in:** `9b19e17`

**2. [Rule 1 - Bug] `_seed_receipt()` ning yashirin DEVOR-SOAT bog'liqligi olib tashlandi**
- **Found during:** Task 3 (yangi yosh chegarasi testlarini yozayotganda)
- **Issue:** `seed_outbox_row()` `created_at` ni SERVER `now()` idan oladi, tik esa
  `LOUD_MOMENT` (2026-08-12 09:00) bilan chaqiriladi. Ya'ni
  `test_unresolved_chat_stays_pending_without_consuming_an_attempt` dagi qatorning YOSHI
  test yugurgan KUNGA bog'liq bo'lib qolardi va kalendar `LOUD_MOMENT` dan 72 soat
  o'tgach yangi yosh darvozasi uni JIMGINA `failed` ga tushirardi.
- **Fix:** `_SET_CREATED_AT` yordamchisi (`_age_the_row()`) qo'shildi va mavjud test
  yoshni ANIQ beradigan qilindi (`LOUD_MOMENT - 1 soat`); yangi testlar ham shu naqshdan
  yuradi.
- **Files modified:** `tests/integration/test_outbox.py`
- **Verification:** `test_outbox.py` — 16/16 yashil; darvoza endi kalendar surilishidan
  mustaqil.
- **Committed in:** `a5b95f1`

**3. [Rule 2 - Missing Critical] Darvozani buzadigan izohlar qayta yozildi**
- **Found during:** Task 1 va Task 2
- **Issue:** Nuqsonni TUSHUNTIRISH uchun yozilgan izohlar taqiqlangan shaklni LITERAL
  tashigan (`attempt_count = o.attempt_count + 1`, `«byudjet tugadi»`), ya'ni rejaning
  O'Z `grep` darvozalarini (`-> 0`) buzardi — izoh o'zi tushuntirayotgan qoidaga qarshi
  ishlardi. Bu `outbox.py` ning 1-taqig'ida allaqachon o'lchangan sinf.
- **Fix:** Ikkala izoh ham shaklni TA'RIFLAYDIGAN matnga aylantirildi va sabab ochiq
  yozildi.
- **Files modified:** `services/core-api/app/repositories/outbox_repo.py`,
  `services/core-api/app/jobs/outbox.py`
- **Verification:** `grep -c` darvozalari yuqoridagi jadvalda — ikkalasi ham **0**.
- **Committed in:** `bc5bc4b`, `9b19e17`

---

**Total deviations:** 3 auto-fixed (2 bug, 1 missing critical)
**Impact on plan:** Uchalasi ham rejaning O'Z da'volarini bajarish uchun zarur edi —
qamrov kengaymadi. Reja ko'rsatgan barcha o'zgarishlar aynan yozilganidek bajarildi.

## Issues Encountered

**1. `test_notifications.py::test_overdue_reminder_is_held_by_quiet_hours` — DEVOR SOATIGA
bog'liq, 07-19 ning sababi EMAS.**

To'liq integratsiya to'plamida bitta yiqilish bor. Sabab: test nazorat bandi uchun
kvitansiyani `outbox_repo.enqueue()` bilan yozadi va `next_attempt_at` ning
`server_default` i — `now()`. Keyin `claim(now=_wall(today, time(22, 30)))` chaqiriladi,
ya'ni **mahalliy vaqt 22:30 dan keyin** yugurgan har qanday yugurishda qator hali
«muddati kelmagan» bo'ladi. Ijro 23:03 da bajarildi.

⛔ **O'LCHANDI, taxmin qilinmadi:** ikkala mahsulot fayli `3b1e964` holatiga qaytarilib
(`git show <base>:<path> > <path>`) AYNAN shu test qayta yugurtirildi — u **bazada ham
QIZIL**. Fayllar `git checkout --` bilan tiklandi (`git status --porcelain services/`
bo'sh).

Fayl rejaning `files_modified` ro'yxatidan tashqarida, shuning uchun **tuzatilmadi** —
`deferred-items.md` ning 3-bandiga to'g'ri tuzatish shakli bilan yozildi.

**2. `--no-deps` bilan yugurtirilgan to'plamda 4 ta ERROR.** `tests` konteyneri
`storage` ga `depends_on` bilan bog'langan; izolyatsiya qilingan loyihada u ko'tarilmagani
uchun `s3_client` fixture'i yiqildi (`test_snapshot_api.py` 3 ta, `test_phase6_criteria.py`
1 ta). Alohida `storage` ko'tarilib, `weed shell` bilan `sbozor-snapshots` bucketi
yaratilgach o'sha to'plam **31/31 yashil** bo'ldi. Kod bilan aloqasi yo'q.

## Known Stubs

None — bu rejada stub, placeholder yoki simlanmagan ma'lumot yo'q.

## Threat Flags

None — yangi tarmoq yuzasi, yangi auth yo'li, yangi fayl kirishi yoki trust chegarasidagi
sxema o'zgarishi qo'shilmadi. `threat_model` dagi oltala disposition (`T-07-104` …
`T-07-SC`) bajarildi:

| Threat ID | Bajarilishi |
|---|---|
| T-07-104 | Ikki deadline tekshiruvi + `moment` dan hisoblanadigan ijara; ikki nusxa yo'qligi CHIQQAN SO'ROV soni bilan o'lchandi |
| T-07-105 | `UNRESOLVED` qator `failed` ga chiqadi; «navbatdan chiqdi» IKKINCHI TIK (`claimed == 0`) bilan o'lchandi |
| T-07-106 | `attempt_count` faqat uch terminal bayonotda oshadi; ulanmagan sotuvchi uch tikdan keyin ham `0` da (test) |
| T-07-107 | `defer_unresolved()` `_validate_error_type()` dan o'tadi (test parametrizatsiyada URL bilan o'lchandi) |
| T-07-108 | `attempt_count` ning ma'nosi `test_delivery_surface.py` da qayta o'qildi va docstringga yozildi |
| T-07-SC | `pyproject.toml` / `uv.lock` diffda YO'Q — yangi paket o'rnatilmadi |

## User Setup Required

None — tashqi xizmat sozlamasi talab qilinmaydi.

## Next Phase Readiness

- **Mezon #5 ning yetkazish yarmi yopildi:** kvitansiya ikki marta ketmaydi, kech ulangan
  sotuvchining byudjeti saqlanadi va navbat konvergent. Qolgan yarmi (direktorning yozuv
  yo'li: `binding_repo.py`, `api/internal/bot.py`, bot handlerlari) — **07-18** ning ishi;
  fayl to'plamlari kesishmaydi.
- **07-18 uchun ogohlantirish:** `OutboxClaim` ga `created_at` maydoni qo'shildi va
  `attempt_count` ning MA'NOSI o'zgardi («olingan marta» -> «HAQIQIY urinish»). Ikkalasi
  ham `outbox_repo` ning ommaviy kontrakti; `GET /reconciliation/delivery` javob SHAKLI
  esa o'zgarmadi.
- **Ochiq band:** `deferred-items.md` ning 3-bandi (devor-soatiga bog'liq flaki) faza
  yakuni yoki 8-fazaga qoldi.

## Self-Check: PASSED

- **Fayllar (7/7 topildi):** `07-19-SUMMARY.md`, `deferred-items.md`,
  `jobs/outbox.py`, `repositories/outbox_repo.py`, `test_outbox.py`,
  `test_outbox_repo.py`, `test_delivery_surface.py`
- **Commitlar (5/5 topildi):** `926fd84`, `bc5bc4b`, `a5b95f1`, `9b19e17`, `7469d13`
- **`git status --porcelain services/`:** bo'sh (sabotajlar qaytarilgan)
- **STATE.md / ROADMAP.md:** ⛔ **TEGILMAGAN** (merge'dan keyin orkestrator yozadi)

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
