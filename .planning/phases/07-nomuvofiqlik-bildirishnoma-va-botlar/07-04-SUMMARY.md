---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 04
subsystem: testing
tags: [meta-test, rls, information-schema, ast-gate, security-definer, fixtures, d-26b]
requires:
  - "0023_notification_domain — beshala jadval, RLS, case_event_immutable()"
  - "sbozor_core.models.notification — AST darvozasining skanerlash yuzasi"
  - "tests/fixtures/two_markets.py::seed_two_markets — D-26(b) seed'ining poydevori"
  - "tests/fixtures/market_domain.py::MarketDomainSeed — stall/vendor identifikatorlari"
provides:
  - "G7-2 — `notification_outbox` taqiqlangan ustunlari `information_schema` dan"
  - "G7-7 — `pg_proc.prosecdef` to'plami TENGLIK bilan (test_meta.py ning `>=` bo'shlig'i yopildi)"
  - "G7-8 — saqlangan qoldiq YO'Q + suzuvchi arifmetika AST bilan taqiqlangan"
  - "tests/fixtures/notification_domain.py — beshala jadval seed'i + `seed_same_phone_in_two_markets()`"
  - "case tarixining append-only ekani XULQIY o'lchandi (07-02 ning 3-ochiq bandi yopildi)"
affects:
  - "07-05…07-13 (outbox jo'natuvchisi, case oqimi, bot) — hammasi shu seed'lardan oziqlanadi"
  - "07-08 (D-26 bog'lanish oqimi) — `seed_same_phone_in_two_markets()` uning YAGONA kirish holati"
tech-stack:
  added: []
  patterns:
    - "taqiqning YO'QLIGI `information_schema` TO'PLAM kesishmasi bilan, grep bilan EMAS"
    - "AST darvozasi — docstring taqiqni tushuntira olsin (03-07 darsi)"
    - "definer to'plami TENGLIK bilan, `>=` bilan emas"
    - "fixture mahsulot qoidasini BUZA OLMAYDI (hosila diskriminator + XOR + payload allowlist)"
    - "seed O'Z-O'ZINI tekshiradi — buzilganda test emas, FIXTURE qizaradi"
key-files:
  created:
    - tests/tenancy/test_notification_domain_meta.py
    - tests/fixtures/notification_domain.py
  modified: []
decisions:
  - "`ALLOWED_DATA_TYPES` dan `boolean` OLIB TASHLANDI — sxemada bayroq ustuni YO'Q va solishtiruv TENGLIK bilan"
  - "G7-7 TENGLIK bilan o'lchandi: `test_meta.py::>=` yangi definer funksiyani UMUMAN ko'rmasdi"
  - "`test_meta.py` TEGILMADI — `EXPECTED_DEFINER_FUNCTIONS` sanog'i 21, o'zgarmadi"
  - "Fixture uchta qo'shimcha seed oldi — usiz rejaning O'Z akseptans mezoni bo'sh rost bo'lardi"
metrics:
  duration: ~55 min
  completed: 2026-08-12
  tasks: 2
  files: 2
---

# Phase 7 Plan 04: Sxema darvozalari va D-26(b) seed'i — Summary

`0023` ning kafolatlari endi **o'lchanadi**: taqiqlangan ustunlarning
yo'qligi sxemadan o'qiladi, suzuvchi arifmetika AST bilan bloklanadi,
`SECURITY DEFINER` yuzasi tenglik bilan qulflanadi — va D-26(b) ning
«bir nechta moslik» shoxi birinchi marta **bajariladigan** holatga ega.

## Nima qurildi

**Task 1 — `test_notification_domain_meta.py` (`8023c0e`).** To'qqiz
darvoza, hammasi `pg_catalog` / `information_schema` dan. Uchtasi
fazaning nomlangan darvozalari (G7-2, G7-7, G7-8), qolgan oltitasi
ularning **shartlari**: nazorat o'lchovi, tip tengligi, RLS, case
nishonining to'rt cheklovi va tarixning xulqiy append-only tekshiruvi.

**Task 2 — `fixtures/notification_domain.py` (`2dd4758`).** Beshala
jadvalning seed'lari va fazaning eng nozik funksiyasi —
`seed_same_phone_in_two_markets()`. Meta faylga yana beshta test
qo'shildi (fixture kontrakti), jami **14**.

## O'lchangan dalillar

### Sabotaj 1 — G7-2 (reja talab qilgan)

`0023` ning `upgrade()` oxiriga vaqtincha
`ALTER TABLE notification_outbox ADD COLUMN evidence_url text` qo'shildi.

| Darvoza | Natija |
|---|---|
| `test_outbox_has_no_evidence_or_message_column` | **QIZIL** — `{'evidence_url': ['url']}` |
| `create_table` bloki ustidan grep | **0 moslik** (ustun u yerda YO'Q) |

⛔ **Aynan shu farq bu darvozaning mavjudlik sababi.** Ustun `ALTER TABLE`
bilan qo'shilgani uchun `0023` ning `create_table` matni **o'zgarmadi** —
ya'ni migratsiya matnini ko'radigan har qanday grep darvozasi
**YASHIL** qolardi. `information_schema` esa jadvalning **bugungi**
holatini beradi va uni birinchi yugurishdayoq ushladi. Sabotaj olib
tashlandi.

### Sabotaj 2 — G7-8, AST ning grepdan farqi

Ikki bosqichda o'lchandi va farq **ikkala yo'nalishda** ham ko'rindi:

| Sabotaj | AST darvozasi | Sodda grep |
|---|---|---|
| **2b** — `round(` / `float(` / `Decimal` **DOCSTRINGDA** | **YASHIL** ✓ | **1 moslik** (qizil bo'lardi) |
| **2a** — `RESOLUTION_NOTE_MAX_LENGTH = round(2000.0)` (haqiqiy CHAQIRUV) | **QIZIL** — `{'notification.py': ['round() @ satr 253']}` | qizil |

⛔ 2b — bu fazaning **butun sababi**: `models/notification.py` va `0023`
ikkalasi ham taqiqni **tushuntiradi**, ya'ni grep darvozasi ularni
**o'z izohlari uchun** jazolardi va yagona «tuzatish» yo'li sababni
o'chirish bo'lardi (03-07 da bir marta haqiqatan sodir bo'lgan —
07-02 uni `models/notification.py` docstringini qayta yozib
tuzatgan edi). Ikkala sabotaj ham olib tashlandi
(`git diff --stat` bo'sh bilan tasdiqlandi).

### G7-7 — DEFINER yuzasi

| Da'vo | Natija |
|---|---|
| `EXPECTED_DEFINER_FUNCTIONS` sanog'i (6-faza) | **21** |
| `EXPECTED_DEFINER_FUNCTIONS` sanog'i (7-faza, 07-04 dan keyin) | **21** — O'ZGARMADI |
| Bazadagi `pg_proc.prosecdef` funksiyalari | **22** (21 + `capture_due_markets`) — 07-02 ning o'lchovi bilan bir xil |
| `tests/tenancy/test_occupancy_domain_meta.py` (`DEFINER_SURFACES == ()`) | yashil |

⛔ **Solishtiruv TENGLIK bilan yozildi va bu `test_meta.py` dagi
darvozadan FARQ QILADI.** U yerdagi da'vo `found >=
EXPECTED_DEFINER_FUNCTIONS`, ya'ni **ortiqcha nomni umuman ko'rmaydi**:
`0023` yangi `SECURITY DEFINER` funksiya qo'shganda ham o'sha test
yashil qolardi (u faqat yangi funksiyaning `search_path` ini talab
qilardi). Bo'shliq shu faylda yopildi. `test_meta.py` ga **tegilmadi** —
reja aynan shunday yozgan.

### Darvozalar

`pytest tests/tenancy` — **690 test yashil** · `pytest tests/unit` —
**1146 test yashil** · `ruff check` + `ruff format --check` + `mypy`
(314 fayl) — **toza**.

## Rejadan chetlanishlar

### Rule 1 — reja matni sxemadan farq qilgan joyda SXEMA ustun turdi

**1. [Rule 1] `ALLOWED_DATA_TYPES` dan `boolean` olib tashlandi**

- **Topildi:** Task 1, birinchi yugurishdan OLDIN. Reja ro'yxatga
  `boolean` ni kiritgan, lekin beshala jadvalning **birortasida ham**
  bayroq ustuni yo'q: holat `text` + enumdan hosila `CHECK` bilan,
  faollik esa `revoked_at IS NULL` bilan ifodalanadi.
- **Nega muhim:** solishtiruv `test_billing_domain_meta.py` naqshi
  bo'yicha **TO'PLAM TENGLIGI** bilan yozilgan (`not in` emas — sabab
  o'sha faylning docstringida o'lchangan). Tenglikda ro'yxatdagi
  ortiqcha tip darvozani **birinchi yugurishdayoq** qizartirardi va
  yagona «tuzatish» yo'li tenglikni `⊆` ga bo'shatish bo'lardi — ya'ni
  `numeric` / `double precision` uchun eshik ochilardi.
- **Yechim:** ro'yxat sxemadan o'qib qurildi (8 tip) va `boolean` ning
  **yo'qligi** sababi bilan docstringga yozildi.
- **Commit:** `8023c0e`

**2. [Rule 1] Konstrayt nomlari — `ck_` prefiksi bilan**

- **Topildi:** reja `subject_is_exclusive` / `subject_kind_matches_target`
  deb yozgan, bazadagi haqiqiy nomlar esa
  `ck_reconciliation_cases_*` (SQLAlchemy `naming_convention` prefiksi).
  Reja nomlari bilan yozilgan test **hech qachon** topmasdi.
- **Yechim:** haqiqiy nomlar bilan assert qilindi; xato xabari mavjud
  nomlarni ro'yxatlaydi.
- **Commit:** `8023c0e`

### Rule 2 — rejaning O'Z akseptans mezoni bo'sh rost bo'lib qolardi

**3. [Rule 2] Fixture `seed_case_event()` va `seed_notification_settings()` oldi**

- **Topildi:** reja to'rtta seed sanaydi, lekin akseptans mezoni
  «`cleanup_notification_domain` dan keyin **beshala** jadvalda 0 qator»
  deydi. To'rt seed bilan `reconciliation_case_events` va
  `market_notification_settings` ga **hech qachon** qator yozilmasdi,
  ya'ni «0 qator» da'vosi o'sha ikki jadval uchun **BO'SH ROST** bo'lardi
  — tozalash funksiyasi butunlay bo'sh bo'lgan taqdirda ham darvoza
  yashil qolardi.
- **Yechim:** ikki seed qo'shildi;
  `test_cleanup_notification_domain_empties_all_five_tables` avval
  beshala jadvalni **to'ldiradi**, `count > 0` ni assert qiladi va
  faqat shundan keyin tozalaydi.
- **Commit:** `2dd4758`

**4. [Rule 2] `_UNREACHABLE_CONNECTION = cast(..., None)`**

- **Topildi:** `seed_case()` ning XOR validatsiyasi **har qanday**
  `conn.execute()` dan **oldin** ishlashi kerak. Haqiqiy ulanish bilan
  yozilgan test bu tartibni o'lchamasdi: validatsiya `INSERT` dan
  keyinga surilgan bo'lsa DB qatorni baribir rad etardi va
  `pytest.raises(ValueError)` umuman boshqa xatoni ko'rardi.
- **Yechim:** ulanish o'rniga `None` beriladi — tartib buzilsa test
  `AttributeError` bilan **aynan o'sha regressiyada** qizaradi.
- **Commit:** `2dd4758`

### Rule 3 — bloklovchi bo'shliqlar

**5. [Rule 3] `seed_no_coverage_anomaly()` + `cleanup_case_targets()`**

- **Topildi:** `seed_case()` nishonni **chaqiruvchidan** oladi
  (`anomaly_id` yoki `charge_id`), lekin ikkala nishon ham **kompozit
  FK** ortida — ya'ni haqiqiy `billing_anomalies` / `daily_charges`
  qatorisiz `seed_case()` ni umuman **chaqirib bo'lmasdi**. Shu bilan
  birga rejaning Task 1 dagi 8-testi (`test_case_events_are_append_only`)
  ham HAQIQIY case qatorini talab qiladi.
- **Yechim:** `no_coverage_stall` anomaliyasini yozadigan seed
  qo'shildi. `kind` tanlovi mexanik: ikkala juftlangan `CHECK` ham aynan
  shu qiymatda dalil ustunlarining `NULL` bo'lishini **talab qiladi**,
  ya'ni bu butun `occupancy` + `snapshot` zanjirisiz qonuniy yoziladigan
  yagona anomaliya sinfi. Tozalash **alohida** funksiyada:
  `billing_anomalies` — billing domenining jadvali va uni
  `cleanup_notification_domain()` ga qo'shish `billing_domain` seed'ining
  qatorlarini ham jimgina o'chirardi.
- **Commit:** `2dd4758`

**6. [Rule 3] `cleanup_same_phone_in_two_markets()`**

- **Topildi:** `cleanup_two_markets()` `vendors` ni **o'chirmaydi**
  (u 2-fazaning domen jadvali). Usiz seed FK bilan bog'langan qatorlar
  qoldirardi va keyingi testning bozor o'chirish qadami yiqilardi.
- **Yechim:** sotuvchilar avval, bozorlar keyin; bozor `is_active =
  false` ga tushiriladi (`cleanup_billing_domain` naqshi).
- **Commit:** `2dd4758`

### Struktura bo'yicha ongli qaror

**Task 1 ning 8-testi fixture'ga KO'CHIRILDI, takrorlanmadi.** Task 1
o'z ichida minimal `_seed_case_with_event()` yordamchisi bilan yozildi
(o'sha commit yashil), Task 2 esa uni `fixtures/notification_domain.py`
ning seed'lariga almashtirdi. Ikki nusxa qoldirish `seed_case()` ni
**ishlatilmaydigan** qilardi — ya'ni fazaning butun quyi oqimi
sinalmagan funksiyaga tayanardi.

## Ochiq bandlar

**1. `npm run gate:fast` — frontend yarmi BU WORKTREE'DA bajarilmadi.**
Node yarmi (`npm run test:fast` = `pytest tests/unit`) **1146/1146
yashil**. Frontend yarmi (`npm --prefix frontend test`) ishga tushmadi:
worktree'da `frontend/node_modules` YO'Q (gitignored). Bu **muhit
bo'shlig'i, kod nuqsoni emas** va u bu rejaning o'zgarishlaridan
MUSTAQIL: `git diff --name-only 566ba2f HEAD` — **aynan ikki fayl,
ikkalasi ham Python testi**. Egasi: orkestrator (07-02 da ham aynan shu
band edi).

**2. `ALLOWED_PAYLOAD_KEYS` — VAQTINCHALIK ro'yxat.** Haqiqiy manba
07-05 da `NOTIFICATION_META[<kind>].payload_keys` bo'ladi (har `kind`
uchun o'z ro'yxati). O'shanda bu konstanta undan **HOSILA** qilinishi
kerak, NUSXA emas — aks holda ikki ro'yxat jimgina ajralib ketardi
(D-32 ning aynan sinfi). Sabab fixture docstringida yozib qo'yildi.

**3. `EXTRA_DEFINER_FUNCTIONS` reyestri qo'lda yuritiladi.** Bugun u
bitta nom (`capture_due_markets`). Kelajakdagi faza qonuniy ravishda
yangi `SECURITY DEFINER` funksiya qo'shsa, tenglik darvozasi qizaradi va
**bu to'g'ri xulq**: nomni qo'shish ONGLI qadam bo'lishi kerak. Xato
xabari sababni («RLS'ni chetlab o'tadigan yangi yuza») aytadi.

**4. Case nishonining IKKINCHI shoxi (`charge_id`) seed'siz.**
`seed_case(charge_id=...)` yo'li kod darajasida bor va XOR testi uni
qamraydi, lekin HAQIQIY `daily_charges` qatoriga qarshi hech qachon
yugurmadi — u butun `billing_domain` zanjirini (`day_close` chaqiruvi
bilan) talab qiladi. Birinchi ehtiyoj 07-05/07-06 da tug'iladi va
o'shanda seed `billing_domain` fixture'i ustiga qatlanadi.

## Known Stubs

Yo'q. Bu reja faqat test va fixture beradi; birorta UI yoki API yuzasi
qurilmagan va birorta bo'sh qiymat renderga oqmaydi.

## Threat Flags

Yo'q. Yangi tashqi yuza (endpoint, auth yo'li, fayl kirishi, sxema
o'zgarishi) ochilmadi — ikkala fayl ham `tests/` ostida. Aksincha, reja
`<threat_model>` dagi olti tahdiddan **beshtasini** (T-07-17…T-07-21)
o'lchanadigan qildi; T-07-SC («yangi paket o'rnatilmaydi») ham kuchda:
birorta bog'liqlik qo'shilmadi.

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud:
- `tests/tenancy/test_notification_domain_meta.py` ✓
- `tests/fixtures/notification_domain.py` ✓
- `.planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/07-04-SUMMARY.md` ✓

Commitlar mavjud: `8023c0e` · `2dd4758` (baza `566ba2f`).
Birorta commitda fayl o'chirilishi YO'Q (`git diff --diff-filter=D`
bo'sh) — reja faqat ikki YANGI fayl qo'shdi.

⚠ STATE.md va ROADMAP.md ATAYIN TEGILMADI — worktree rejimida ularni
orkestrator markazlashgan holda yangilaydi (parallel ijrochilar
to'qnashuvining oldi olinadi).
