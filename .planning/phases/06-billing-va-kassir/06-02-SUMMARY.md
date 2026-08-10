---
phase: 06-billing-va-kassir
plan: 02
subsystem: api
tags: [rbac, i18n, enums, error-taxonomy, next-intl, strenum, parity-gate]

# Dependency graph
requires:
  - phase: 01-poydevor
    provides: "`rbac.py` <-> `rbac.ts` matritsasi, `role-gate.test.mjs` (G-8), `audit_log.action` enumi"
  - phase: 02-bozor-domeni
    provides: "`test_personal_data_coverage.py` (C-10 darvozasi), `MARKET_ERROR_CODES` allowlist naqshi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`occupancy_errors.py` shabloni, `zone-errors.ts` jadvali, `zone-copy.test.mjs` copy darvozasi, `error-codes.test.mjs` G-17 bloki"
provides:
  - "Ikki yangi huquq: `billing_collect_view` (kassir/bozor admini/direktor) va `shift_manage` (kassir/bozor admini) — ikkala tilda"
  - "Ikki nav yozuvi: `/collect` va `/billing` (NAV_ITEMS 13 -> 15)"
  - "Yetti domen enumi: PaymentKind, PaymentMethod, AdjustmentDirection, AdjustmentReason, ReversalReason, AnomalyKind, ShiftStatus"
  - "Ikki `AuditAction` a'zosi: `payment_override`, `payment_reverse`"
  - "14 billing xato kodi (`billing_errors.py`) + `AMOUNT_UNAVAILABLE_REASONS` alohida frozenset"
  - "`SERVER_BILLING_ERROR_CODES` (13) `schemas.py` allowlist'iga ulangan"
  - "~110 tarjima kaliti uchala tilda (`collect.*`, `billing.*`, `audit.actions.*`)"
  - "Ikki yangi darvoza: `billing-copy.test.mjs` (13 test) va `error-codes.test.mjs` ning billing bloki (6 test)"
affects: [06-03, 06-04, 06-05, 06-06, 06-09, 06-10, 06-11, 06-12, 06-13, 07-nomuvofiqlik-va-botlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Backend <-> frontend domen-enum parity darvozasi (`readPythonEnumValues` x4, §5.10 ning yopilishi)"
    - "Xato reyestri EKRAN bo'yicha bo'linadi, matn namespace'i esa YUZA bo'yicha — ular 1:1 emas"
    - "Allowlist uchun `SERVER_*` va frontend darvozasi uchun `ALL_*` — ikki hosila pog'ona"

key-files:
  created:
    - services/core-api/app/services/billing_errors.py
    - frontend/src/lib/billing-errors.ts
    - frontend/scripts/billing-copy.test.mjs
  modified:
    - services/core-api/app/security/rbac.py
    - services/core-api/app/schemas.py
    - packages/sbozor-core/sbozor_core/enums.py
    - frontend/src/lib/rbac.ts
    - frontend/src/lib/api-types.ts
    - frontend/src/components/shell/app-shell.tsx
    - frontend/scripts/error-codes.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - tests/unit/test_rbac_matrix.py
    - .planning/phases/06-billing-va-kassir/06-UI-SPEC.md

key-decisions:
  - "06-02: kassirga AYNAN ikki huquq berildi; `market_data_view`/`vendor_view`/`camera_view`/`report_view` TEGILMADI va to'rtala rad etish sababi BITTA docstringda — `market_data_view` egasida `vendor_view` bo'lishi SHART (test_personal_data_coverage.py), ya'ni birini berish ikkinchisini ham berardi"
  - "06-02: `AuditAction` ga AYNAN IKKI a'zo — `shift_open`/`shift_close`/`charge_adjust` QO'SHILMADI, chunki `cashier_shifts` va `charge_adjustments` `AUDITED_TABLES` da bor va app audit DUBLIKAT bo'lardi; UI-SPEC §13.6 nomzod to'plamidan chetlashish uning O'Z presedenti bilan ruxsat etilgan"
  - "06-02: xato kodlari `occupancy_errors.py` ga QO'SHILMADI — u yerdagi `occupancyConstants.size === 15` nazorat qiymati darhol qizarardi va uni «tuzatish» nazoratning butun ma'nosini yo'q qilardi (M-B)"
  - "06-02: xato REYESTRI EKRAN bo'yicha (collect/shift/billing/client-only), matn NAMESPACE'i esa YUZA bo'yicha (collect/billing) — ular 1:1 EMAS, chunki `/collect/shift` `/collect` ning bolasi"
  - "06-02: allowlist `SERVER_BILLING_ERROR_CODES` (13) ni oladi, `ALL_BILLING_ERROR_CODES` (14) ni EMAS — `network_unreachable` serverdan hech qachon qaytmaydi va allowlist «server nima qaytarishi mumkin» degan savolga javob beradi"
  - "06-02: `override_not_applicable` tони `neutral` — `warning` kassirga xato qilgandek tuyulardi va u keyingi safar sababni umuman yubormaslikka o'rganardi"
  - "06-02: `AMOUNT_UNAVAILABLE_REASONS` frozenset — 06-06 uni IMPORT qiladi, `market_closed` satri kodda takrorlanmaydi; darvoza uning `billingConstants` sanog'iga TUSHMASLIGINI alohida assert bilan qulflaydi"

patterns-established:
  - "Domen enum parity: `readPythonEnumValues(enums.py, X)` <-> `api-types.ts::X_S` deepEqual — yangi domen enumi ko'zgusiz o'tolmaydi"
  - "Copy darvozasi shabloni (`zone-copy.test.mjs` -> `billing-copy.test.mjs`): reyestrdan iteratsiya · uchala locale · to'plam tengligi · MIN_* quyi chegara · detektorning O'ZI uchun ijobiy va salbiy nazorat"
  - "Ikki pog'onali hosila reyestr: `SERVER_*` (server yuzasi) va `ALL_*` (frontend yuzasi) — iste'molchi tanlovi kodda nomlangan, chaqiruvchida emas"

requirements-completed: [BILL-04, BILL-05, CASH-01, CASH-02, CASH-03]

# Metrics
duration: 55min
completed: 2026-08-10
---

# Phase 6 Plan 02: Reyestr qatlami Summary

**Kassirning o'qish yuzasi ochildi (2 huquq × 2 fayl), 7 domen enumi + 2 audit hodisasi frontend ko'zgusi bilan juftlandi, 14 billing xato kodi uch qatlamda qulflandi va §5.10 ning parity bo'shlig'i sabotaj bilan o'lchab yopildi.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-08-10T09:12:00Z
- **Completed:** 2026-08-10T10:07:00Z
- **Tasks:** 3/3
- **Files modified:** 15 (3 yangi, 12 tahrirlangan)

## Accomplishments

- ⛔ **M-7 yopildi.** `cashier: ["payment_create"]` -> `["payment_create", "billing_collect_view", "shift_manage"]`. Kassir endi yozayotgan narsasini KO'RA oladi; `market_data_view`/`vendor_view`/`camera_view`/`report_view` TEGILMADI, ya'ni shaxsiy maydon kassir yuzasida **strukturaviy ravishda** imkonsiz (C-9/C-10) va `require_any_permission()` ning yopiq to'plami **tegilmagan** qoldi (M-8).
- ⛔ **§5.10 ning parity bo'shlig'i yopildi va yopilishi O'LCHANDI.** 06-02 gacha `readPythonEnumValues` faqat `AuditAction` va `Role` uchun ishlatilgan — ya'ni yangi **domen** enum a'zosi frontend ko'zgusisiz jimgina o'tardi. `billing-copy.test.mjs` to'rt solishtiruv qo'shadi va sabotaj (`AnomalyKind` ga `probe_kind`) uni **qizartirdi**.
- **14 xato kodi uch qatlamda** (backend reyestri · frontend `{tone, surface}` jadvali · uchala tildagi `errorCause`/`errorFix` **juftligi**), `occupancy_errors.py` **tegilmagan** holda.
- **`frontend/messages/*` bu fazada BITTA rejaga tegishli**: `collect.*` (39+13×2 kalit), `billing.*` (32+1×2 kalit), `audit.actions.*` (+2). Keyingi rejalar kalit **qo'shmaydi**, faqat iste'mol qiladi. `uz-Cyrl.overrides.json` ga **birorta yozuv qo'shilmadi** — M-5 ning da'vosi yakuniy copy'da ham rost chiqdi.

## Task Commits

1. **Task 1: Ikki huquq, ikki nav yozuvi va butun matn (OP-6, W0-F1)** — `00bf179` (feat)
2. **Task 2: Yetti domen enumi, ikki `AuditAction` a'zosi va parity darvozasi (OP-7, W0-F7, §5.10)** — `cffb6f4` (feat)
3. **Task 3: `billing_errors.py` — 14 kod, ko'zgu, darvoza bloki va §13.7/§15.1 kengaytmasi (OP-12, W0-F2, M-B)** — `293f2e0` (feat)

## Files Created/Modified

**Yangi:**
- `services/core-api/app/services/billing_errors.py` — 14 `Final[str]` kod + 4 yuza frozenset + `AMOUNT_UNAVAILABLE_REASONS` + ikki hosila aggregat
- `frontend/src/lib/billing-errors.ts` — kod -> `{tone, surface}` (14 yozuv), `billingErrorView()`
- `frontend/scripts/billing-copy.test.mjs` — G-24 + G-26 + §5.10 parity (13 test)

**Tahrirlangan:**
- `services/core-api/app/security/rbac.py` — 2 `Permission` a'zosi + matritsa; rad etish sabablari docstringda
- `services/core-api/app/schemas.py` — `SERVER_BILLING_ERROR_CODES` allowlist'ga ulandi
- `packages/sbozor-core/sbozor_core/enums.py` — 7 yangi `StrEnum` + `AuditAction` ga 2 a'zo
- `frontend/src/lib/rbac.ts` — 2 huquq (literal satr, import YO'Q)
- `frontend/src/lib/api-types.ts` — 4 domen ko'zgusi + `AUDIT_ACTIONS` ga 2; `AUDIT_TABLES` **tegilmadi**
- `frontend/src/components/shell/app-shell.tsx` — `/collect` (HandCoins) va `/billing` (ReceiptText)
- `frontend/scripts/error-codes.test.mjs` — billing bloki (6 test); bandlik bloki **tegilmadi**
- `frontend/messages/{uz-Latn,ru}.json` — qo'lda; `uz-Cyrl.json` — `i18n:gen` generatsiya
- `tests/unit/test_rbac_matrix.py` — kassir to'plami yangilandi + 2 yangi holder darvozasi
- `.planning/phases/06-billing-va-kassir/06-UI-SPEC.md` — §13.7 ga 3 qator (14 kod), §15.1 backend diapazoni `G-12` -> `G-16`

## Decisions Made

Yuqoridagi `key-decisions` frontmatterida. Qo'shimcha ikkita amaliy qaror:

- **`AuditAction` ga IKKI a'zo, UI-SPEC §13.6 ning UCH nomzodi emas.** Reja matnining ikki joyida «uch audit hodisasi» deyilgan (Task 2 sarlavhasi va `<done>`), lekin bog'lovchi band `⛔ AYNAN IKKI a'zo` va acceptance criteria `CHARGE_ADJUST`/`SHIFT_OPEN`/`SHIFT_CLOSE` ning **YO'QLIGINI** talab qiladi. Ikkitasi bajarildi; sabab `enums.py::AuditAction` docstringida **mexanizm sifatida** yozildi (`AUDITED_TABLES` da bor jadval -> DB trigger yozadi -> app audit dublikat).
- **`billing.anomalyKind.*` Task 1 da yozildi, Task 2 da emas.** Task 1 ning action bandi «§13.4 (`billing.*` — 34 kalit) ning **hammasi**» deydi va §13.4 jadvalida bu uch kalit bor. Task 2 esa ularni faqat **darvoza bilan bog'ladi** (G-26). Natija bir xil, kalit ikki marta yozilmadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_cashier_scope_minimal` eski kontraktni literal yozgan edi**
- **Found during:** Task 1
- **Issue:** `assert ROLE_PERMISSIONS[Role.CASHIER] == frozenset({Permission.PAYMENT_CREATE})` — reja talab qilgan ikki huquq qo'shilishi bilan bu test darhol qizarardi. `test_unknown_role_contributes_nothing` ham o'sha to'plamni **ikkinchi marta** literal yozgan edi.
- **Fix:** Birinchisi uch a'zoli to'plamga yangilandi va docstringiga sabab yozildi (testning O'Z izohi «bu chegara 5- va 6-fazalarda ATAYIN qayta ko'riladi» deb bu holatni oldindan nomlagan edi). Ikkinchisi matritsani takrorlashdan **butunlay xalos qilindi** — endi u `ROLE_PERMISSIONS[Role.CASHIER]` ga solishtiradi, ya'ni «noma'lum rol hech nima qo'shmaydi» da'vosi kassir yuzasi kengayganda ham o'z ma'nosini saqlaydi.
- **Files modified:** `tests/unit/test_rbac_matrix.py`
- **Verification:** `pytest tests/unit/test_rbac_matrix.py tests/tenancy/test_personal_data_coverage.py -q` — 33 passed
- **Committed in:** `00bf179`

**2. [Rule 2 - Missing Critical] Yangi huquqlarning taqsimoti darvozasiz qolardi**
- **Found during:** Task 1
- **Issue:** Reja acceptance criteria'da `python -c` bir qatorliklar bilan tekshirilgan, lekin **doimiy** darvoza yo'q edi: oltinchi rol qo'shilib unga `billing_collect_view` «zarari yo'q» deb berilsa hech nima qizarmasdi.
- **Fix:** `test_billing_collect_view_holders_are_exactly_three_roles` va `test_shift_manage_holders_exclude_the_director` qo'shildi — HUQUQ bo'yicha, **to'plam tengligi** bilan (D-31), `test_camera_manage_holders_are_exactly_the_two_admins` naqshida.
- **Files modified:** `tests/unit/test_rbac_matrix.py`
- **Verification:** ikkala test yashil; `holders` to'plami o'zgartirilganda qizaradi
- **Committed in:** `00bf179`

**3. [Rule 2 - Missing Critical] Billing kodlari HTTP allowlist'ida yo'q edi**
- **Found during:** Task 3
- **Issue:** `app/schemas.py::MARKET_ERROR_CODES` — HTTP chegarasida `detail` kodini **taniydigan** yagona reyestr. Undagi bo'shliq 06-09 da jimgina ochilardi: router `stall_not_assigned` bilan `HTTPException` ko'tarardi, allowlist uni tanimay `errors.generic` ga tushirardi va kassir «Bu rastaga sotuvchi biriktirilmagan» o'rniga umumiy xato matnini ko'rardi — ya'ni nosozlik FAQAT dala sinovida ko'rinardi. Aynan shu sinf `occupancy_errors.py` docstringida §S-5/§S-7 sifatida yozilgan.
- **Fix:** `SERVER_BILLING_ERROR_CODES` (13 kod — `network_unreachable` **kirmaydi**) hosila reyestr sifatida qo'shildi va `schemas.py` ga import qilindi. ⚠ Ikki pog'ona ATAYIN: `ALL_BILLING_ERROR_CODES` (14) frontend darvozasi uchun qoladi. Busiz `ALL_BILLING_ERROR_CODES` ning docstringi «`app/schemas.py` bu to'plamni IMPORT qiladi» deb **yolg'on** da'vo qilardi (02-VERIFICATION CR-02 sinfi).
- **Files modified:** `services/core-api/app/services/billing_errors.py`, `services/core-api/app/schemas.py`
- **Verification:** `SERVER_BILLING_ERROR_CODES <= MARKET_ERROR_CODES` va `'network_unreachable' not in MARKET_ERROR_CODES` konteynerda tasdiqlandi; `ruff` + `mypy` toza; `pytest tests/unit tests/tenancy` — 800+ test yashil; `error-codes.test.mjs` ning mavjud `MARKET_ERROR_CODES` parseri splat qatorlarini o'qimaydi, ya'ni eski darvoza **tegilmadi**.
- **Committed in:** `293f2e0`

**4. [Rule 3 - Blocking] Worktree'da `node_modules` va `.env` yo'q edi**
- **Found during:** Task 1 (verifikatsiya)
- **Issue:** Worktree — repo nusxasi, `node_modules` va `.env` esa gitignore'da, ya'ni `typecheck`/`lint`/`vitest` va `docker compose` ishlamasdi.
- **Fix:** `frontend/node_modules` uchun asosiy repoga **junction** (`mklink /J`) va `.env` nusxasi. Ikkalasi ham gitignore'da — commit'ga **tushmagan**.
- **Files modified:** yo'q (ikkalasi ham gitignore'da)
- **Verification:** `git status --short` da ko'rinmaydi; `typecheck`, `lint`, `vitest` (620 test) yashil
- **Committed in:** —

---

**Total deviations:** 4 auto-fixed (2 missing critical, 2 blocking)
**Impact on plan:** Hammasi to'g'rilik uchun zarur. Reja fayllar ro'yxatidan tashqariga chiqqan **ikki** fayl bor — `tests/unit/test_rbac_matrix.py` (usiz Task 1 ni umuman commit qilib bo'lmasdi) va `services/core-api/app/schemas.py` (usiz reyestrning docstringi yolg'on da'vo bo'lardi). Ko'lam kengaymadi: ikkalasi ham mavjud mexanizmning ikkinchi yarmi.

## Sabotaj o'lchovlari (D-30 — majburiy)

| # | Sabotaj | Kutilgan | Natija |
|---|---------|----------|--------|
| **S-1** | `enums.py::AnomalyKind` ga vaqtincha `PROBE_KIND = "probe_kind"` | `billing-copy.test.mjs` **qizaradi** | ✅ **QIZARDI** — `§5.10: domen enumlari api-types.ts ko'zgusi bilan AYNAN mos` yiqildi (12 pass / 1 fail) |
| **S-2** | `billing_errors.py::COLLECT_ERROR_CODES` dan `PAYMENT_ALREADY_REVERSED` olib tashlandi | `error-codes.test.mjs` **qizaradi** (aniq son 14) | ✅ **QIZARDI** — **uch** test birdan yiqildi: aniq son, ko'zgu to'liqligi va matn juftligi (23 pass / 3 fail) |
| **S-3** | `uz-Latn.json` dan `collect.errorFix.payment_already_reversed` o'chirildi | juftlik sharti **qizaradi** | ✅ **QIZARDI** — `HAR BILLING kodi uchun sabab va tuzatish UCHALA tilda bor` yiqildi (25 pass / 1 fail) |

⚠ **S-1 DA YASHIL QOLGANI HAM YOZILADI** va bu topilma: o'sha yugurishда `G-26: har anomaliya turi UCHALA locale'da — TO'PLAM TENGLIGI` **yashil qoldi**. Sabab — u frontend reyestrini **matn katalogi** bilan solishtiradi, backend enumi bilan emas. Ya'ni **copy darvozasi backend driftiga tamoman KO'R** va aynan shu ko'rlik §5.10 ning parity blokini zarur qilgan. Ikkalasini bitta testga qo'shish (yoki parity blokini «ortiqcha» deb tashlab yuborish) 05-15 ning S-D sinfini takrorlagan bo'lardi.

## Issues Encountered

- **Worktree'dan `docker compose` asosiy stekni qayta yaratadi.** Compose loyihasi nomi `sbozor` (compose.yaml da qat'iy), worktree'ning `working_dir` i esa boshqa — natijada har `docker compose run` `sbozor-storage-1` ni **qayta yaratardi** va healthcheck ulgurmay `dependency failed to start` berardi. Yechim: barcha pytest/ruff/mypy yugurishlari `--no-deps` bilan bajarildi (bu testlar DB talab qilmaydi). Asosiy stek yakunda **sog'lom** holatda: `sbozor-storage-1` va ikki `nvr-sim` konteyneri `Up (healthy)`.
- **`pathlib.write_text` Windows'da faylni CRLF ga aylantiradi.** Sabotaj skriptidan keyin `enums.py` CRLF bo'lib qoldi (git `.gitattributes` bo'yicha normallashtirardi, lekin ishchi nusxa `eol=lf` siyosatidan chiqardi). Keyingi sabotajlar `io.open(..., newline="")` bilan bajarildi va fayllar LF holida tekshirildi.
- **`python -c "from app...."` konteynerда ishlamaydi:** `app` paketi `sys.path` da yo'q (u `pyproject.toml` ning `pythonpath` i orqali FAQAT pytest ostida qo'shiladi). Acceptance criteria'dagi bir qatorliklar `sys.path.insert(0, '/app/services/core-api')` bilan bajarildi.

## Verification natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test frontend/scripts/*.test.mjs` | **171 pass / 0 fail** (shundan `billing-copy` 13, `error-codes` 26) |
| `npm --prefix frontend run i18n:check` | yashil — **1094 kalit × 3 til**, kalit va ICU parity to'liq |
| `npm --prefix frontend run i18n:gen -- --check` | yashil — drift yo'q, `uz-Cyrl.overrides.json` ga yozuv **qo'shilmadi** |
| `npm --prefix frontend run typecheck` | toza |
| `npm --prefix frontend run lint` | toza |
| `npm --prefix frontend test` (vitest) | **620 pass / 43 fayl** |
| `pytest tests/unit tests/tenancy -q` | **hammasi yashil** (`test_rbac_matrix`, `test_personal_data_coverage` ichida) |
| `ruff check .` · `ruff format --check .` · `mypy .` | toza — 289 fayl formatlangan, 280 manbada muammo yo'q |
| `npm run gate:fast` (ikki yarim alohida o'lchandi) | **~131 s** (pytest `tests/unit` 53 s + frontend 78 s) — chegara **180 s**, ichida |

⚠ **`gate:fast` o'lchovi SOVUQ WORKTREE'da olingan** (kesh yo'q, `node_modules` junction orqali). 05-15 dagi 87 s asosiy repoda, issiq kesh bilan o'lchangan — ikki son **to'g'ridan-to'g'ri solishtirilmaydi**. Byudjet **qayta belgilanmadi**: u hamon 180 s va o'lchov uning ichida.

## Known Stubs

Yo'q. Bu reja **reyestr qatlami** — mahsulot kodi yozilmaydi va ekranga chizilmaydi. Barcha kalitlar, enumlar va kodlar **haqiqiy iste'molchiga ega** yoki iste'molchisi nomlangan rejaga biriktirilgan:

| Artefakt | Bugungi iste'molchi | Rejalashtirilgan iste'molchi |
|---|---|---|
| `AuditAction.PAYMENT_OVERRIDE/PAYMENT_REVERSE` | darvoza (parity + i18n) | **06-09** `write_app_audit()` chaqiruvlari |
| `AMOUNT_UNAVAILABLE_REASONS` | darvoza (§9.4 tengligi) | **06-06** `resolve_stall_day_money()` importi · **06-03** `pendingStallSchema` |
| `collect.*` / `billing.*` kalitlari | `i18n:check` + copy darvozasi | **06-10…06-13** komponentlari |
| 14 xato kodi | allowlist + uch qatlamli darvoza | **06-09** marshrutlari |

⚠ Ikki `AuditAction` a'zosi 06-09 gacha **ishlatilmasdan turadi** va bu **kutilgan** — sabab `enums.py` docstringida yozilgan, aks holda keyingi ijrochi ularni «o'lik kod» deb o'chirardi.

## Threat Flags

Yo'q. Reja `<threat_model>` dagi to'qqizala band ham bajarildi:

| Threat ID | Holat |
|---|---|
| T-06-05 | ✅ Kassirda `market_data_view`/`vendor_view`/`camera_view`/`report_view` YO'Q; `test_personal_data_coverage.py` yashil |
| T-06-06 | ✅ `require_any_permission()` va `SNAPSHOT_EVIDENCE_FRAME_ROUTES` **tegilmadi** |
| T-06-07 | ✅ `other`/`custom` yo'q; G-24 to'plam tengligi bilan o'lchaydi |
| T-06-08 | ✅ `readPythonEnumValues` ×4 `deepEqual`; sabotaj S-1 bilan tasdiqlandi |
| T-06-09 | ✅ Modulda foydalanuvchi matni YO'Q — faqat kod |
| T-06-09a | ✅ `stall_not_assigned` (409) nomlandi, uchala tilda |
| T-06-09b | ✅ `market_closed` **kod** bo'lib qaytadi; matni §9.4 ekran matni bilan **AYNAN teng** (darvoza bilan qulflangan) |
| T-06-SC | ✅ Yangi paket **yo'q** — `package.json` va `pyproject.toml` tegilmadi |

## User Setup Required

Yo'q — tashqi servis sozlamasi talab qilinmaydi.

## Next Phase Readiness

**Tayyor:**
- **06-03** (`pendingStallSchema`) — `AMOUNT_UNAVAILABLE_REASONS` ning frontend yarmi uchun qiymatlar reyestrda; `soumSchema` qayta ishlatiladi
- **06-04** (sxema) — `PaymentKind`, `PaymentMethod`, `AdjustmentDirection`, `AdjustmentReason`, `ReversalReason`, `AnomalyKind`, `ShiftStatus` `CHECK` konstraytlarini **hosila** qilish uchun tayyor (`occupancy.py::_quoted()` naqshi)
- **06-06** — `AMOUNT_UNAVAILABLE_REASONS` ni import qiladi; satr literali takrorlanmaydi
- **06-09** — 14 kodning hammasi allowlist'da; `payment_override`/`payment_reverse` audit a'zolari joyida
- **06-10…06-13** — uchala tildagi butun copy joyida; **kalit qo'shish kerak emas**

**Bandlar (bloklamaydi, lekin nomlangan):**
- ⛔ **W0-F6 hamon OCHIQ.** `05-UI-SPEC.md` §15 ning G-18 qatoriga `` `components/collect/**` `` **qo'shilmadi** — bu reja UI-SPEC ning talabi bo'yicha (§15.4, 2-qadam) aynan **birinchi `components/collect/*.tsx` mahsulot fayli bilan bitta commitda** bajarilishi kerak, chunki `bulk-action-surface.test.mjs:293-308` e'lon qilingan katalogning **mavjud va bo'sh emasligini** tekshiradi. Hozir qo'shilsa darvoza qizarardi. Egasi — birinchi `collect` komponentini yozadigan reja (06-10).
- ⚠ `06-VALIDATION.md` da `G-13`…`G-16` darvozalari **hali yozilmagan** — §15.1 diapazoni ular uchun band qilindi (raqam to'qnashuvini oldini olish uchun), lekin darvozalarning o'zi o'sha hujjatning egasi bo'lgan rejada tug'iladi.

## Self-Check: PASSED

- 15 fayl (3 yangi, 12 tahrirlangan) — hammasi diskda **FOUND**
- 3 commit (`00bf179`, `cffb6f4`, `293f2e0`) — hammasi `git log` da **FOUND**
- `git diff --numstat services/core-api/app/services/occupancy_errors.py` — **bo'sh** (M-B saqlandi)
- `git diff` da `AUDIT_TABLES` — **0 marta** (Gotcha 15 saqlandi)
- Fayl o'chirilishi — **yo'q** (uchala commitda ham `--diff-filter=D` bo'sh)

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-10*
