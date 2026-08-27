---
phase: 06-billing-va-kassir
plan: 09
subsystem: billing
tags: [fastapi, postgres, idempotency, append-only, rbac, tenancy, audit, sabotage]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 01
    provides: "A1 zondi (`IDEMPOTENT_GET_OR_CREATE_SUPPORTED = True`) — ikki bayonotli get-or-create shoxining KIRISH SHARTI; `payment_quote_set()` va `total_due_soum()` sof funksiyalari"
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "14 kodli xato reyestri (`stall_not_assigned`, `reason_required`, `override_not_applicable`, `idempotency_key_reused`, `payment_already_reversed`), `AuditAction.PAYMENT_OVERRIDE` / `PAYMENT_REVERSE`, `Permission.PAYMENT_CREATE` taqsimoti"
  - phase: 06-billing-va-kassir
    plan: 03
    provides: "`frontend/src/lib/payment-queries.ts` — `paymentResponseSchema` (8 kalit) va `PaymentInput` (so'rov maydon NOMLARI)"
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "`payments` jadvali: `UNIQUE (market_id, idempotency_key)`, `request_fingerprint`, uch juftlangan `CHECK`, `payment_immutable()` qo'riqchisi"
  - phase: 06-billing-va-kassir
    plan: 06
    provides: "`billing_repo.resolve_stall_day_money()` va `vendor_outstanding()` — marshrut o'qiydigan YAGONA pul yechimi"
  - phase: 06-billing-va-kassir
    plan: 08
    provides: "`schemas.py` ning «E'LON QILMASLIK» naqshi, `main.py` router konventsiyasi, `test_no_matrix_route_returns_422` darvozasi"
provides:
  - "`services/core-api/app/repositories/payment_repo.py` — ikki bayonotli idempotent get-or-create, `request_fingerprint()`, storno (bitta bayonot, `NOT EXISTS` ichida), `recent_payments()` (oyna KODDA), `shift_system_total()` (06-10 uchun)"
  - "`services/core-api/app/api/v1/payments.py` — uch marshrut, 200/201/403/404/409/422 to'liq, CASH-02 auditi"
  - "`app/schemas.py` — `PaymentCreateRequest` / `PaymentReverseRequest` / `PaymentResponse` / `RecentPaymentsResponse`"
  - "`CASHIER_ROUTES` — matritsaning UCHINCHI sessiya shoxi (`payment_create` yolg'iz kassirda)"
  - "`tests/integration/test_payments_api.py` — 27 test; SC#5(a) ketma-ket VA parallel, SC#5(c), CASH-02, BLOCKER 3/4"
  - "O'LCHANGAN SABOTAJ: S-1 QIZARDI · S-2 avval YASHIL QOLDI (topilma) -> holat kuchaytirilgach QIZARDI · S-3 QIZARDI"
affects: [06-10, 06-11, 06-12, 06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zond markerining natijasi mahsulot modulining BIRINCHI docstring bandida nomma-nom keltiriladi; rad etilgan shox (`SAVEPOINT`) YOZILMAYDI, faqat NOMLANADI — o'lik shox sinalmaydi"
    - "«Tekshir-keyin-yoz EMAS» storno uchun: `NOT EXISTS` `INSERT ... SELECT` ning `WHERE` ida, alohida `SELECT` yozilmaydi"
    - "Sabotaj YASHIL qolsa — bu TEST TOPILMASI: da'vo susaytirilmaydi, HOLAT toraytiriladi (ikki so'rov FAQAT bitta maydonda farq qiladi)"
    - "Kalendar istisnosi (`is_open = true`) test faylining BUTUN kunini haftaning kunidan MUSTAQIL qiladi; yopiq kun testlari AYNI qatorni `false` ga o'giradi"
    - "Til chegarasi to'plam tengligi bilan qulflanadi: server javob kalitlari `frontend/.../payment-queries.ts` dagi `z.strictObject` dan regeks bilan HOSILA qilinadi"

key-files:
  created:
    - services/core-api/app/repositories/payment_repo.py
    - services/core-api/app/api/v1/payments.py
    - tests/integration/test_payments_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "06-09: so'rov maydoni `reason_code`, `override_reason` EMAS — klientning `PaymentInput` i (06-03, merge qilingan) aynan shu nomni yuboradi va `extra=\"forbid\"` ostida ikkinchi nom 422 berardi; ustun nomi `payments.override_reason` bo'lib qoladi, ko'chirish AYNAN BITTA joyda"
  - "06-09: `shift_id` MIJOZDAN OLINMAYDI (rejadan ongli chetlanish) — server so'rovchining ochiq smenasini o'zi yechadi; qabul qilish kassirga BOSHQA kassirning smenasiga to'lov yozish va o'sha smenaning ko'r deklaratsiyasini ifloslantirish yo'lini ochardi (T-06-57)"
  - "06-09: OQ-6 (`shift_id = NULL`) DIREKTOR sessiyasi bilan o'lchanmaydi — direktorda `payment_create` YO'Q (D-07, 06-02 da qulflangan); da'vo SMENA haqida, huquq haqida emas, shuning uchun u ochiq smenasiz KASSIR bilan o'lchanadi"
  - "06-09: `SAVEPOINT` zaxira shoxi YOZILMADI — marker `True`, ya'ni u o'lik shox bo'lardi va sinalmasdi; shart va oqibati docstringda NOMLANDI"
  - "06-09: `payment_owner()` `stall_code` ni HAM qaytaradi — storno javobiga rasta kodi kerak va qator o'sha darvoza uchun ALLAQACHON o'qilyapti; ikkinchi `SELECT` yozilmadi"
  - "06-09: begona smenaning to'lovini bekor qilish -> 403 `forbidden` (strukturaviy), reyestrga YANGI kod qo'shilmadi — `error-codes.test.mjs` ning aniq soni tegilmasligi kerak edi"
  - "06-09: matritsa tanasi `amount_soum = 1` + sabab — server taklifini QAYTA HISOBLAMAYDI (D-20); taklifga teng summa yuborish testni serverning arifmetikasiga bog'lardi"

patterns-established:
  - "Yangi rolga bog'langan marshrut uchun: `<ROL>_ROUTES` frozenset + `<rol>_headers` fixture + `_pick` shoxi + IKKI darvoza (`*_point_at_live_routes` va `*_really_need_the_*_permission`)"
  - "Matritsa fixture'i yozgan qator sanaga bog'liq bo'lsa u BAZADAN o'qiladi (`sa.period @> (now() AT TIME ZONE 'Asia/Tashkent')::date`), indeks bilan qotirilmaydi"
  - "Matritsa marshruti haftaning kuniga bog'liq bo'lib qolmasligi uchun seed shart-sharoitni (qarz) O'ZI yaratadi"

requirements-completed: [CASH-01, CASH-02, CASH-03]

# Metrics
duration: 105min
completed: 2026-08-11
---

# Phase 6 Plan 09: To'lov yozish yuzasi Summary

**Uch marshrut, ikki bayonotli idempotentlik va uchta sabotaj: 422 ning sharti `amount_soum is None` dan BO'SH KVOTA TO'PLAMIGA ko'chirildi (yopiq kunda eski qarz endi undiriladi — eski shartni qaytarish ikki testni qizartirdi), Pitfall 4 ning sabotaji esa avval YASHIL qolib testning O'ZIDAGI nuqsonni fosh qildi: ikki so'rov `amount_soum` dan tashqari `override_reason` da ham farq qilardi, ya'ni test o'z nomidagi da'voni umuman o'lchamayotgan edi.**

## Performance

- **Duration:** ~105 min
- **Started:** 2026-08-10T20:40:00Z
- **Completed:** 2026-08-10T22:25:00Z
- **Tasks:** 3
- **Files modified:** 6 (3 yangi, 3 kengaytirilgan) — **+3 172 / −27** qator

## Accomplishments

- **A1 zondining javobi mahsulot kodiga NOMMA-NOM ko'chdi.** `payment_repo.py` ning birinchi docstring bandi o'lchov sanasini (2026-08-10), PG versiyasini (18.4) va o'lchagan testni keltiradi; tanlangan shox — **ikki bayonot**. `SAVEPOINT` zaxirasi **yozilmadi** va sabab ochiq: marker `True`, ya'ni u **o'lik shox** bo'lardi va sinalmasdi.
- **D-21 xulq bilan yopildi — VA PARALLEL HOLAT HAM.** `asyncio.gather` bilan ikki bir vaqtdagi `POST`: jadvalda **1 qator**, ikkala javobda ham **bir xil** `payment_id`, **5xx yo'q**. Bu A1 zondining SQL o'lchovini butun yo'l (marshrut → repo → `ON CONFLICT` → ikkinchi `SELECT` → javob) bo'ylab takrorlaydi.
- **⛔ BLOCKER 4 bajarildi va sabotaj bilan isbotlandi.** 422 endi **bo'sh kvota to'plamiga** bog'langan: yopiq kunda (`market_closed`) qarzi bor sotuvchidan **201** bilan pul olinadi, tarifsiz toifada ham; qarz `<= 0` bo'lgandagina 422 va `detail` da **nomlangan sabab**. Eski shartni (`amount_soum is None`) qaytarish **ikki testni qizartirdi**.
- **⛔ BLOCKER 3 bajarildi va NAZORAT holati bilan o'lchandi.** Biriktirilmagan rastaga to'lov → **409 `stall_not_assigned`**, `payments` da **0 qator**; o'sha rastaga biriktirish qo'shilgach **AYNI so'rov 201** beradi — ya'ni 409 **holatdan**, kod xatosidan emas. Reyestrga **hech nima qo'shilmadi**.
- **D-23 uch qatlamda o'lchandi:** xom `UPDATE payments` **ega rolida ham** `RaiseException` beradi; storno **yangi qator** (`kind='reversal'`, `reversal_reason` majburiy, asl qator bayt-bayt o'zgarmagan); `openapi()` da `/api/v1/payments*` metodlari **AYNAN** `{POST, GET}` (to'plam tengligi).
- **Yig'indi yo'li ikki tomondan to'sildi:** `recent_payments()` imzosida `limit` argumenti **yo'q** (oyna `RECENT_PAYMENT_WINDOW = 5` konstantasida), `openapi()` da oyna marshrutining parametrlari **bo'sh to'plam**, `shift_system_total()` esa docstringda **taqiq** bilan birga keladi.
- **OP-8 va OP-9 ning ikki yarmi ayni rejada.** `CASHIER_ROUTES` (aynan ikki `POST`), `market_a_cashier_headers`, `_pick` ning uchinchi shoxi va **ikki** yangi darvoza (`*_point_at_live_routes` + `*_really_need_the_payment_permission`).
- **Yangi paket o'rnatilmadi** (T-06-SC — `sha256` stdlib `hashlib` dan), **frontendga tegilmadi** (`git diff --numstat frontend/` → **bo'sh**), **xato reyestri tegilmadi** (`billing_errors.py` / `billing-errors.ts` / `error-codes.test.mjs` → **bo'sh diff**).

## Task Commits

1. **Task 1: `payment_repo.py` — ikki bayonotli idempotentlik, storno va qat'iy oyna** — `26182ab` (feat)
2. **Task 2: uch marshrut, 200/201/409/422 va CASH-02 auditi** — `186dabe` (feat)
3. **Task 3: `CASHIER_ROUTES` matritsasi, SC#5(a)/(c) va uch sabotaj** — `f8b3f14` (test)

## Files Created/Modified

- `services/core-api/app/repositories/payment_repo.py` (**yangi**, 929 qator) — `request_fingerprint()`, `create_payment()`, `reverse_payment()`, `payment_owner()`, `recent_payments()`, `shift_system_total()`, `open_shift_id()`.
- `services/core-api/app/api/v1/payments.py` (**yangi**, 528 qator) — uch marshrut, ikki imzo aliasi, `_reject()` (satr `detail`).
- `tests/integration/test_payments_api.py` (**yangi**, 1 152 qator) — **27 test**, to'qqiz guruh.
- `services/core-api/app/schemas.py` (+182) — to'rt model; so'rovda `quote_soum`/`charge_id`/`shift_id`/`service_date`/`vendor_id` **umuman e'lon qilinmagan**.
- `services/core-api/app/main.py` (+23) — `/payments` prefiksi va uning to'rt sababi.
- `tests/tenancy/test_cross_tenant.py` (+385/−27) — `CASHIER_ROUTES`, kassir fixture'i, `_pick` shoxi, `payment_id` filleri, ikki tana, `_assigned_stall_today()`, A bozorining qarzi.

## Sabotaj (D-30) — UCH URINISH, IKKITASI QIZARDI, BITTASI TOPILMA BERDI

| # | Sabotaj | Natija | Xulosa |
|---|---------|--------|--------|
| **S-1 (Pitfall 3)** | `create_payment()` dagi **ikkinchi `SELECT`** olib tashlandi (`found = None`) | 🔴 **QIZARDI — 3 test** | `test_the_same_key_twice_...`, `test_two_concurrent_requests_...`, `test_the_same_key_with_a_different_amount_...` — uchalasi ham `RuntimeError: idempotency invariant buzildi` bilan yiqildi. ⛔ **Jimgina 200 EMAS**: xato **nomma-nom** va u kalitni ham, `market_id` ni ham xabarda ko'rsatdi |
| **S-2 (Pitfall 4)** | `request_fingerprint()` dan **`amount_soum`** olib tashlandi | 🟢 **AVVAL YASHIL QOLDI → 🔴 KUCHAYTIRILGACH QIZARDI** | Quyidagi alohida bo'limga qarang — bu rejaning **eng qimmat topilmasi** |
| **S-3 (BLOCKER 4)** | Marshrutga **eski shart** qaytarildi (`if money.amount_soum is None:`) | 🔴 **QIZARDI — 2 test** | `test_on_a_closed_day_an_outstanding_debt_can_still_be_collected` (a) va `test_without_a_tariff_an_outstanding_debt_can_still_be_collected` (c) — ikkalasi ham `422 {"detail":"market_closed"/"tariff_missing"}` oldi. ⛔ (b) (`qarz yo'q → 422 market_closed`) **YASHIL qoldi** va bu TO'G'RI: u eski shartda ham bir xil javob beradi, ya'ni uch test **uch xil xossani** o'lchaydi |

### ⛔ S-2 — SABOTAJ YASHIL QOLDI VA U TESTNING O'ZIDAGI NUQSONNI FOSH QILDI

`request_fingerprint()` dan `amount_soum` maydoni olib tashlandi, lekin **`test_the_same_key_with_a_different_amount_is_rejected` YASHIL QOLDI**.

**Sabab:** test ikkinchi so'rovga `reason_code` ni **ham** qo'shgan edi (birinchisida u yo'q edi). Ya'ni ikki so'rov `amount_soum` dan **tashqari** `override_reason` da ham farq qilardi va xesh 409 ni **boshqa maydondan** chiqarardi — test o'z nomidagi da'voni (**«summa boshqa»**) umuman o'lchamayotgan edi.

**Tuzatish testda emas, ⛔ HOLATNING O'ZIDA** (05-15 ning S-D darsi: da'vo susaytirilmaydi, holat **toraytiriladi**). Ikkala so'rov ham kvota to'plamidan **tashqaridagi** summa yuboradi, ya'ni:

| Maydon | 1-so'rov | 2-so'rov |
|---|---|---|
| `quote_soum` | `quotes[0]` | `quotes[0]` — **BIR XIL** |
| `override_reason` | `partial_day` | `partial_day` — **BIR XIL** |
| `stall` / `service_date` / `method` | — | **BIR XIL** |
| `amount_soum` | 1 000 | 2 000 — ⛔ **YAGONA FARQ** |

Kuchaytirilgan test bilan S-2 **darhol qizardi**. Qo'shimcha ravishda **ikkinchi shox alohida testga ajratildi** (`test_the_same_key_with_a_different_reason_is_also_rejected`): endi har maydonning **o'z** testi bor va sabotaj ularni **ajratib** ko'rsatadi. Bitta testda ikki maydonni birdan o'zgartirish «qaysi maydon xeshni himoya qilyapti?» savolini javobsiz qoldirardi.

⚠ Uchala sabotaj ham `git checkout -- <fayl>` bilan **qaytarib olindi**; `git status` toza, `ruff`/`mypy` yashil.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] So'rov maydonining nomi rejada `override_reason`, klientda esa `reason_code`**

- **Found during:** Task 2 (`read_first` bo'yicha `payment-queries.ts` ni o'qishda)
- **Issue:** Reja `PaymentCreateRequest` da `override_reason: AdjustmentReason | None` maydonini nomlaydi. `frontend/src/lib/payment-queries.ts::PaymentInput` (06-03, **allaqachon merge qilingan**) esa `reason_code?: AdjustmentReason` yuboradi. `extra="forbid"` ostida bu **422** berardi va 06-11 ning kassir paneli **birinchi bosishdayoq** yiqilardi — nosozlik esa faqat dala sinovida ko'rinardi.
- **Fix:** Sim nomi `reason_code` (klient kontrakti); ustun nomi `payments.override_reason` **o'zgarmadi**; ikki nom orasidagi ko'chirish **aynan bitta joyda** (`payments.py` handleri). Alias **ishlatilmadi** — u ikki nomni bir vaqtda tirik qoldirib, aynan oldini olayotgan drifni tug'dirardi.
- **Files modified:** `services/core-api/app/schemas.py`
- **Verification:** `PaymentCreateRequest.model_fields` = `{idempotency_key, stall_code, method, amount_soum, reason_code}` — klientning `PaymentInput` i bilan **AYNAN** bir xil.
- **Committed in:** `186dabe`

**2. [Rule 2 - Missing Critical] `shift_id` mijozdan olinmaydi (T-06-57)**

- **Found during:** Task 2
- **Issue:** Reja `PaymentCreateRequest` da `shift_id: UUID | None` maydonini nomlaydi. Uni qabul qilish kassirga **boshqa kassirning** ochiq smenasiga to'lov yozish imkonini berardi va o'sha smenaning **ko'r deklaratsiyasi** (D-25) begona pul bilan ifloslanardi — variance hisobotida sababi topilmaydigan farq chiqardi. Bu `quote_soum` bilan **aynan bir xil sinf**: server o'zi biladigan qiymatni mijozdan olmaydi (D-20).
- **Fix:** Maydon **umuman e'lon qilinmadi**; server `payment_repo.open_shift_id(cashier_id=principal.user_id)` bilan yechadi, ochiq smena bo'lmasa `NULL` (OQ-6/A5 saqlanadi). Klient uni baribir **yubormaydi** (`PaymentInput` da yo'q), ya'ni kontraktga ta'sir yo'q.
- **Files modified:** `services/core-api/app/schemas.py`, `services/core-api/app/api/v1/payments.py`
- **Verification:** `test_a_payment_without_an_open_shift_is_written_but_stays_out_of_the_window` — `shift_id` `NULL` bo'lib yoziladi va oynada **ko'rinmaydi**.
- **Committed in:** `186dabe`

**3. [Rule 3 - Blocking] Reja OQ-6 ni DIREKTOR sessiyasi bilan o'lchashni aytadi — direktorda `payment_create` YO'Q**

- **Found during:** Task 3
- **Issue:** Reja test 7 ni «`shift_id=None` bilan to'lov (**direktor sessiyasi**) → 201» deb yozadi. `security/rbac.py` (06-02 da qulflangan, `test_rbac_matrix.py` bilan) `Role.DIRECTOR` ga `PAYMENT_CREATE` **bermaydi** — u FAQAT `Role.CASHIER` da. Direktor sessiyasi **403** olardi va OQ-6 umuman o'lchanmasdi.
- **Fix:** Da'voning O'ZI huquq haqida emas, **SMENA** haqida («`shift_id` `NULL` bo'lishi mumkin»). Test ochiq smenasiz **KASSIR** bilan yozildi: (1) seed smenasi o'chiriladi → to'lov `shift_id = NULL` bilan **201**; (2) yangi smena ochiladi → ikkinchi to'lov o'sha smenaga; (3) `GET /payments/recent` **faqat ikkinchisini** ko'rsatadi. Ikkala yarim ham o'lchandi.
- **Files modified:** `tests/integration/test_payments_api.py`
- **Verification:** test yashil; smenani `status='closed'` ga o'girish **rad etildi** (`closed_has_declaration` / `closed_has_system_total` `CHECK` lari ko'r deklaratsiyani talab qiladi va u **06-10** ning o'lchovi).
- **Committed in:** `f8b3f14`

**4. [Rule 1 - Bug] Matritsa tanasi HAFTADA BIR KUN qizarardi**

- **Found during:** Task 3 (`BODY_FILLERS` tanasini loyihalashda)
- **Issue:** A bozori **dushanba yopiq** (`A_OPEN_WEEKDAYS` = ISO 2..7). Yopiq kunda `today_soum is None`, matritsa seedida esa A bozorining qarzi **yo'q** edi → `payment_quote_set()` **bo'sh** to'plam → **422** → `test_no_matrix_route_returns_422` haftada bir kun qizarardi. Bu «to'lqin chegarasida yashil, dushanba qizil» sinfidagi eng qimmat flakelik.
- **Fix:** `billing_rows` fixture'i A bozoriga ham **bitta `daily_charges` qatori** yozadi (`service_date = CURRENT_DATE - 1`), ya'ni kvota to'plami **har kuni** kamida bitta elementli. Sotuvchi **bazadan** o'qiladi (`sa.period @> (now() AT TIME ZONE 'Asia/Tashkent')::date`), `vendor_ids[1]` deb **qotirilmaydi** — almashinuv sanasi o'tgach indeks jimgina boshqa sotuvchini ko'rsatardi.
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** `pytest tests/tenancy -q` — **to'liq yashil** (ikki mustaqil yugurish, exit 0).
- **Committed in:** `f8b3f14`

**5. [Rule 1 - Bug] CASH-02 auditi `sync_owner_conn` bilan o'qilganda BO'SH ko'rinardi**

- **Found during:** Task 3 (`test_payments_api.py` ning birinchi yugurishi)
- **Issue:** Test `audit_log` ni `sync_owner_conn` (ega roli, tenant konteksti **o'rnatilmagan**) bilan o'qidi va **0 qator** oldi — ya'ni «audit yozilmagan» degan **yolg'on** natija. Sabab: `audit_read` policy'si oddiy tenant predikatiga bo'ysunadi va `audit_log` `owner_bootstrap` policy'sini **ATAYIN olmagan** (`policies.py`), ya'ni ega ham kontekstsiz 0 qator ko'radi.
- **Fix:** Jurnal `market_scope()` (ilova roli + tenant konteksti) orqali o'qiladi — shakl `test_assignments_api.py:500-506` dan olindi va sabab test docstringida yozildi.
- **Files modified:** `tests/integration/test_payments_api.py`
- **Verification:** `test_a_changed_amount_with_a_reason_is_written_and_audited` yashil; auditda aktor, `quote_soum`, `amount_soum`, `reason_code` **va** `quotes` to'plami bor.
- **Committed in:** `f8b3f14`

**6. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da (06-01/06-04/06-05/06-06/06-08 dagi holatning **beshinchi** takrori).
- **Fix:** Ikkalasi asosiy repodan **NUSXALANDI**. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **`grep -cE "UNION ALL" payment_repo.py` → `2`, LEKIN IKKALASI HAM MODUL DOCSTRINGIDA.** Rejaning `<action>` bandi «fayl docstringining birinchi bandi A1 zondining natijasini **nomma-nom** keltiradi» deb TALAB qiladi, `<objective>` esa CTE + `UNION ALL` shaklining rad etilishini alohida bandda tushuntiradi — ya'ni matn qabul mezoniga o'zi zid. Yuk ko'taruvchi o'lchov — **bajariladigan** kodda `UNION ALL` yo'qligi: `awk 'NR>96' payment_repo.py | grep -cE "UNION ALL"` → **`0`** (modul docstringi 96-qatorda tugaydi). Bu 06-08 ning `require_any_permission` bandidagi holatning aynan takrori.
- **`grep -c "require_any_permission" payments.py` → `2` va `grep -cE "amount_soum is None" payments.py` → `1` — UCHALASI HAM DOCSTRINGDA.** Reja ikkalasining sababini **docstringga yozishni** buyuradi (`⛔ require_any_permission() ISHLATILMAYDI` va `⛔ NEGA ESKI SHART ... NOTO'G'RI EDI`) va bir vaqtda `grep → 0` ni talab qiladi. Import ham, chaqiruv ham **yo'q**: `from app.deps import Principal, TenantSessionDep, require_permission`; 422 sharti esa `if not quotes:`.
- **`grep -c "select(" payment_repo.py` → `2`.** Reja bu sonni «ikkinchi bayonot mavjud» ning o'lchovi deb qo'yadi. Ikkala `select()` ham ORM shaklida: `create_payment()` ning ikkinchi bayonoti va `payment_owner()`. Qolgan so'rovlar `text()` da (`billing_repo` konventsiyasi) — bu **shakl** tanlovi, «ikkinchi bayonot bormi?» degan da'voga ta'sir qilmaydi va u **xulq bilan** (S-1 sabotaji) o'lchandi.
- **Task 1 ning `<verify>` bloki hali mavjud bo'lmagan test faylini chaqiradi.** `tests/integration/test_payments_api.py` — **Task 3** ning artefakti, Task 1 esa uni verifikatsiya buyrug'ida nomlaydi. Task 1 `ruff`/`mypy` bilan verifikatsiya qilindi va xulq darvozalari Task 3 da yopildi (reja o'zi shu tartibni belgilagan). Ayni holat Task 2 uchun ham (`test_route_coverage.py` Task 3 dagi matritsa yozuvlarisiz qizil bo'lardi — va u **aynan shunday qizardi**, ya'ni darvoza ishladi).
- **`GET /payments/recent` javobi `{items: [...]}`.** Reja envelope shaklini nomlamaydi; klientning `recentPaymentsSchema` (06-03) esa `z.strictObject({ items })` — server o'sha shaklga moslandi.

---

**Total deviations:** 6 auto-fixed (2 blocking, 1 missing-critical, 3 bug) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Qamrov kengaymadi. Yangi paket **o'rnatilmadi** (T-06-SC), xato reyestriga **hech nima qo'shilmadi** (uchala fayl diffi **bo'sh**), frontendga **tegilmadi**, migratsiyaga **tegilmadi**.

## Issues Encountered

- **To'liq to'plamda 33 qizil — hammasi NVR-sim va live-view guruhida, sababi UMUMIY KONTEYNER POYGASI.** Bu 06-08 SUMMARY dagi holatning aynan takrori: `pytest -q` yugurayotgan paytda `docker compose run` chaqiruvlari umumiy `sbozor-storage-1` / `nvr-sim` konteynerlarini **qayta yaratadi**. **O'lchov:** o'sha 33 test izolyatsiyada qayta yugurtirildi va **99/99 yashil** bo'ldi (`test_nvr_discovery.py` + `test_nvr_discovery_job.py` + `test_nvr_errors.py` + `test_nvr_sim.py` + `test_phase3_criteria.py` + `test_nvr_api.py` → **97/97**; `test_live_view_e2e.py` → **2/2**). Bu reja birorta NVR/RTSP/kamera/ombor fayliga **tegmaydi**. Ops qadami bajarildi: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` (⛔ `-v` **ishlatilmadi**).
- **5-fazadan meros flaky test (`test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`) bu yugurishda QIZARMADI.** U `deferred-items.md` ning 1-bandida va tegilmadi.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q. ⛔ Junction/symlink **YARATILMADI**, `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. Bu reja birorta frontend fayliga **tegmaydi** (`git diff --numstat frontend/` → **bo'sh**), ya'ni `gate` byudjetining (1250 s) to'liq o'lchovi yana keyingi to'lqinga qoladi. Band `deferred-items.md` ning 3-qatorida allaqachon bor.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_payments_api.py -q` | ✅ **27/27** |
| `pytest tests/tenancy -q` | ✅ **to'liq yashil** (ikki mustaqil yugurish, exit 0) |
| `pytest tests/integration/test_payments_api.py tests/tenancy/test_route_coverage.py -q` | ✅ **35/35** |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**312** fayl formatlangan, **303** fayl tiplangan) |
| `pytest -q` (to'liq to'plam) | ⚠ 33 qizil — hammasi umumiy konteyner poygasidan (yuqoridagi bandga qarang) |
| O'sha 33 testning izolyatsiyada qayta yugurishi | ✅ **99/99** |
| `git diff --numstat billing_errors.py billing-errors.ts error-codes.test.mjs` | ✅ **bo'sh** (reyestr tegilmagan) |
| `git diff --numstat frontend/` | ✅ **bo'sh** |

**Qabul mezonlari (Task 1):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `grep -c on_conflict_do_nothing` ≥ 1 | **1** | ✅ |
| `grep -c "select("` ≥ 2 | **2** | ✅ |
| `grep -cE "UNION ALL"` → 0 | **2** — ikkalasi ham modul docstringida; bajariladigan kodda **0** | ⚠ (yuqoridagi «reja matnining aniqlashtirilishi» ga qarang) |
| `grep -c RuntimeError` ≥ 1 | **8** | ✅ |
| `grep -c RECENT_PAYMENT_WINDOW` ≥ 2; imzoda `limit` yo'q | **7**; imzo `(session, *, market_id, shift_id)` | ✅ |
| `grep -cE "UPDATE payments\|update\(Payment"` → 0 | **0** | ✅ |
| Xulq: bir xil kalit ikki chaqiruv → 1 qator, `created is False`, o'sha `id` | `test_the_same_key_twice_...` | ✅ |
| Xulq: bir xil kalit + boshqa summa → `IdempotencyConflict` | `test_the_same_key_with_a_different_amount_...` (kuchaytirilgan holat) | ✅ |
| Xulq: `reverse_payment` ikki marta → `PaymentAlreadyReversed`; **1** reversal qatori | `test_reversing_twice_is_rejected` | ✅ |
| Xulq: `recent_payments` 7 to'lovda **5** qator | `test_the_window_returns_at_most_five_rows` | ✅ |
| `shift_system_total` docstringida «HTTP javobiga ... kirmaydi» taqig'i | so'z bilan bor (`⛔⛔ TAQIQ:` bloki) | ✅ |
| `ruff` va `mypy` toza | ✅ | ✅ |

**Qabul mezonlari (Task 2):**

| Mezon | O'lchov | Natija |
|---|---|---|
| Bir xil kalit ikki marta → **201** so'ng **200** va o'sha `payment_id` | `test_the_same_key_twice_...` | ✅ |
| Bir xil kalit + boshqa summa → **409 `idempotency_key_reused`** | `test_the_same_key_with_a_different_amount_...` | ✅ |
| Sababsiz chetlanish → **422 `reason_required`** | `test_a_changed_amount_without_a_reason_...` | ✅ |
| ⛔ **BLOCKER 4:** yopiq kun + qarz → **201**, javobda `service_date` | `test_on_a_closed_day_an_outstanding_debt_...` | ✅ |
| `tariff_missing` + qarz → **201**; qarz `<= 0` → **422** + nomlangan sabab | ikki alohida test | ✅ |
| `[Qarzni ham olish]` sababsiz → **201** | `test_paying_the_total_due_needs_no_reason_code` | ✅ |
| Taklifga teng summa + sabab → **422 `override_not_applicable`** | `test_an_unchanged_amount_with_a_reason_...` | ✅ |
| ⛔ **BLOCKER 3:** biriktirilmagan rasta → **409 `stall_not_assigned`**, 0 qator, 404 emas | `test_an_unassigned_stall_...` + nazorat testi | ✅ |
| Reyestr tegilmagan (uch faylning diffi bo'sh) | `git diff --numstat` | ✅ |
| `override_reason` bilan → 201 va `audit_log` da `quote_soum` **va** `amount_soum` | `test_a_changed_amount_with_a_reason_...` | ✅ |
| `reason_code` siz storno → **422**; ikkinchi marta → **409** | ikki alohida test | ✅ |
| Storno yozilgach asl qator o'zgarmagan | `test_a_reversal_is_a_new_row_...` | ✅ |
| `GET /payments/recent` ≤5 va OpenAPI da parametr **yo'q** | ikki alohida test (`names == set()`) | ✅ |
| `openapi()` da metodlar to'plami **AYNAN** `{POST, GET}` | to'plam tengligi | ✅ |
| `PaymentResponse` klient `paymentResponseSchema` bilan mos | `test_the_payload_matches_the_client_schema` (regeks bilan HOSILA) | ✅ |
| `grep -c require_any_permission` → 0 | **2** — ikkalasi ham docstringda; import/chaqiruv **yo'q** | ⚠ (aniqlashtirish bandiga qarang) |
| `grep -c payment_quote_set` ≥ 1; arifmetika → 0 | **4**; **0** | ✅ |
| `grep -cE "amount_soum is None"` → 0 | **1** — modul docstringida; shart `if not quotes:` | ⚠ (aniqlashtirish bandiga qarang) |

**Qabul mezonlari (Task 3):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `CASHIER_ROUTES` da **aynan ikki** `RouteSpec`; `/recent` u yerda yo'q | ✅ | ✅ |
| `_pick` da uchinchi shox (`grep -c CASHIER_ROUTES` ≥ 2) | **10** | ✅ |
| `test_cross_tenant_object_returns_404` ikki yangi POST uchun **404** | tenancy yashil | ✅ |
| `test_no_matrix_route_returns_422` yashil | tenancy yashil | ✅ |
| `test_all_path_params_have_fillers` yashil (`payment_id` HAQIQIY) | tenancy yashil | ✅ |
| Parallel `asyncio.gather`: 1 qator, bir xil `payment_id`, 5xx yo'q | `test_two_concurrent_requests_...` | ✅ |
| `openapi()` metodlari **AYNAN** `{POST, GET}` | to'plam tengligi | ✅ |
| Qisman va ortiqcha to'lov **201**; ortiqchadan keyin qoldiq **manfiy** | `test_a_partial_and_an_overpayment_...` | ✅ |
| `shift_id=None` to'lovi oynada **ko'rinmaydi** | `test_a_payment_without_an_open_shift_...` | ✅ |
| Sabotaj natijalari SUMMARY da | yuqoridagi «Sabotaj» bo'limi (uch urinish) | ✅ |
| `pytest tests/tenancy -q` to'liq yashil | ikki mustaqil yugurish, exit 0 | ✅ |

## Known Stubs

Yo'q. Uchala yangi fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q, birorta funksiya qotirilgan bo'sh qiymat qaytarmaydi.

⚠ **`payment_repo.shift_system_total()` bugungi kodda HECH QAYERDAN chaqirilmaydi** va u **stub EMAS**: funksiya to'liq ishlaydi va uning yagona iste'molchisi — **06-10** ning smena yopilishi. U shu rejada yozildi, chunki `_SIGNED_PAYMENT_EXPR` qoidasi (`kind='reversal'` → manfiy) shu modulning javobgarligida va uni 06-10 da ikkinchi marta yozish ikki haqiqat manbai bo'lardi. Docstringda **taqiq** (HTTP javobiga chiqmaslik) so'z bilan yozilgan — keyingi ijrochi uni «o'lik kod» deb o'chirmasin.

## Threat Flags

Yangi xavfsizlik yuzasi **uch marshrut** bilan ochildi va threat register bo'yicha qoplandi:

- ⛔ Threat register: **o'n bir `mitigate` bandi bajarildi** — T-06-49 (ikki bayonotli get-or-create + parallel o'lchov + S-1 sabotaji), T-06-50 (`request_fingerprint` + S-2 sabotaji), T-06-51 (422 `reason_required` + juftlangan `CHECK` + `payment_override` auditi), T-06-52 (`PATCH`/`PUT`/`DELETE` **umuman yo'q** + xom `UPDATE` → `RaiseException` + storno yangi qator), T-06-53 (oyna serverda 5, parametr **yo'q**, `shift_system_total()` javobga chiqmaydi), T-06-54 (`quote_soum` so'rovda **umuman e'lon qilinmagan**), T-06-54a (422 **bo'sh kvota to'plamiga** bog'langan + S-3 sabotaji), T-06-54b (409 `stall_not_assigned` + nazorat holati), T-06-54c (422 `override_not_applicable`), T-06-55 (RLS + `CASHIER_ROUTES` matritsasi + **haqiqiy** B qiymati), T-06-56 (`PaymentResponse` da `vendor_name`/`phone` **yo'q**, to'plam tengligi bilan), T-06-57 (begona smenaning to'lovini bekor qilish → **403**). T-06-SC (`accept`) — yangi paket o'rnatilmadi.
- ⛔ **Rejadan TASHQARIDA topilgan va yopilgan yuza:** `shift_id` ni **mijozdan olish** (T-06-57 ning yozuv tomondagi jufti) — reja uni so'rov maydoni sifatida nomlagan edi; server o'zi yechadigan qilib yopildi (deviatsiya #2).
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**; migratsiyaga **tegilmadi**.
- ⚠ **Yangi tenant yuzasi**: uchala marshrut ham `TenantSessionDep` ostida va cross-tenant matritsasiga **avtomatik** tushdi; `payment_id` filleri B bozorining **haqiqiy** qatorini ko'rsatadi.
- Yangi rasm/fayl yuzasi **ochilmadi**; `SNAPSHOT_EVIDENCE_FRAME_ROUTES` va `PERSONAL_ROUTES` **tegilmadi**.

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): parallel worktree'lar bir vaqtda `docker compose run` chaqirsa umumiy `storage`/`nvr-sim` konteynerlari **qayta yaratiladi** va boshqasining yugurayotgan to'plami qizaradi. Tuzatish: `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` dan keyin qayta o'lchash (⛔ `-v` **ishlatilmaydi** — u xostdagi dev volumelarni o'chiradi).

## Next Phase Readiness

- **06-10 (smena):** `payment_repo.shift_system_total()` **tayyor** va u 06-10 ning yagona tizim-summa manbai; `open_shift_id()` ham eksport qilingan. ⚠ `POST /shifts`, `POST /shifts/{id}/close` `BODY_FILLERS` ga yozilishi SHART, aks holda `test_no_matrix_route_returns_422` darhol qizaradi. ⚠ Smenani yopish `declared_soum` **va** `system_soum` ni birga talab qiladi (`closed_has_declaration` / `closed_has_system_total`).
- **06-11 (kassir ekrani):** kontrakt **o'lchangan va til chegarasi bo'ylab qulflangan** — `test_the_payload_matches_the_client_schema` server javobini `paymentResponseSchema` bilan solishtiradi. So'rov maydonlari ham klientning `PaymentInput` i bilan **aynan** bir xil (`reason_code`, `shift_id` **yo'q**).
- **06-12/06-14 (darvozalar):** `MINIMUM_MATRIX_ROUTES` **ATAYIN ko'tarilmadi** (06-08 ning qarori davom etadi: shart `>=`, yakuniy son 06-14 da o'lchov bilan qo'yiladi). Bugungi o'lchov: matritsada **3 yangi** marshrut, tana yuboriladigan marshrutlar **39**.
- ⚠ **Ochiq band (bloklamaydi):** `deferred-items.md` ning 2-qatoridagi klient envelopelari (06-03 ning `chargeListSchema`/`anomalyListSchema`/`pendingLookupSchema`) hamon serverdan orqada — bu reja unga **tegmadi** (frontend diffi bo'sh).

## Self-Check: PASSED

**Fayllar (4/4 mavjud):** `services/core-api/app/repositories/payment_repo.py` (929 qator) · `services/core-api/app/api/v1/payments.py` (528 qator) · `tests/integration/test_payments_api.py` (1 152 qator) · `06-09-SUMMARY.md`

**Commitlar (3/3 topildi):** `26182ab` · `186dabe` · `f8b3f14`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `payment_repo.py` `min_lines: 300` | `wc -l` → **929** | ✅ |
| `payment_repo.py` `contains: on_conflict_do_nothing` | `grep -c` → **1** | ✅ |
| `payments.py` `provides`: uch marshrut | OpenAPI da `POST /payments`, `POST /payments/{payment_id}/reverse`, `GET /payments/recent` | ✅ |
| `test_payments_api.py` — SC#5(a)/(c) + Pitfall 3/4 + CASH-02 422 | 27 test, to'qqiz guruh | ✅ |
| `key_links`: `payment_repo` → `UNIQUE (market_id, idempotency_key)` (`select(Payment`) | `on_conflict_do_nothing(index_elements=[...])` + ALOHIDA `select(*_PAYMENT_COLUMNS)` | ✅ |
| `key_links`: `payments.py` → `write_app_audit(AuditAction.PAYMENT_OVERRIDE)` | `grep -c PAYMENT_OVERRIDE` → **1** (chaqiruvda) | ✅ |
| `key_links`: `CASHIER_ROUTES` + `market_a_cashier_headers` + `_pick` uchinchi shoxi | uchalasi ham mavjud, ikki darvoza bilan | ✅ |

**`truths` (9/9):**
takror `POST` **200** va O'SHA `payment_id` (409 EMAS) ·
bir xil kalit + boshqa summa **409 `idempotency_key_reused`** (S-2 bilan o'lchangan) ·
sababsiz chetlanish **422 `reason_required`** ·
storno YANGI qator + sabab majburiy; tahrirlash/o'chirish marshruti **umuman yo'q** (OpenAPI to'plam tengligi) ·
`GET /payments/recent` oxirgi 5, parametr **yo'q** (OpenAPI da bo'sh to'plam) ·
`POST /payments` FAQAT kassirda — `CASHIER_ROUTES` matritsasi **404** bilan o'lchaydi ·
YOPIQ kunda eski qarz **undiriladi** (201) va 422 faqat asoslanmagan summa uchun (S-3 bilan o'lchangan) ·
biriktirilmagan rasta **409 `stall_not_assigned`**, nazorat holati bilan ·
server taklif qilgan uch summaning HAR BIRI sababsiz o'tadi, boshqasi sabab talab qiladi (ikki tomonlama).

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-11*
