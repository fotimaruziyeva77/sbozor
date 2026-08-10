---
phase: 06-billing-va-kassir
plan: 08
subsystem: billing
tags: [fastapi, pydantic, rbac, openapi, tenancy, sabotage, contract]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`Permission.BILLING_COLLECT_VIEW` / `REPORT_VIEW` taqsimoti, `AMOUNT_UNAVAILABLE_REASONS`, `SERVER_BILLING_ERROR_CODES` allowlist'i, domen enumlari"
  - phase: 06-billing-va-kassir
    plan: 04
    provides: "`daily_charges` / `charge_adjustments` / `charge_evidence` / `billing_anomalies` jadvallari, C-12 juftlangan `CHECK` i, `service_date` domen ustuni"
  - phase: 06-billing-va-kassir
    plan: 05
    provides: "`tests/fixtures/billing_domain.py` — `add_daily_charge()` va olti rasta stsenariysi"
  - phase: 06-billing-va-kassir
    plan: 06
    provides: "`billing_repo.pending_projection()`, `resolve_stall_day_money()`, `vendor_outstanding()` — marshrutlar o'qiydigan YAGONA pul yechimi"
  - phase: 05-ai-nazorat
    provides: "`api/v1/occupancy.py` marshrut naqshi (imzo aliasi, nol-natija, `market_id` yechimi), `schemas.py::BlindItemResponse` ning «E'LON QILMASLIK» naqshi"
provides:
  - "`services/core-api/app/api/v1/billing.py` — to'rt marshrut (`/pending`, `/charges`, `/charges/{charge_id}`, `/anomalies`)"
  - "`app/schemas.py` — sakkiz javob modeli, ikki juftlangan `model_validator` va `AmountUnavailableReason` ning import-vaqti reyestr darvozasi"
  - "`billing_repo.charge_list()` / `charge_detail()` / `anomaly_list()` — direktor yuzasining o'qish so'rovlari"
  - "`tests/integration/test_billing_api.py` — 22 darvoza, ikki mustaqil kontrakt qatlami"
  - "⛔ YANGI MEXANIK DARVOZA: `test_no_matrix_route_returns_422` — `BODY_FILLERS` ko'rligini yopadi"
  - "O'LCHANGAN SABOTAJ: S-A (`charge_id` e'loni) — IKKALA qatlam ham QIZARDI; S-B (`BODY_FILLERS` yozuvi) — yangi darvoza QIZARDI, eskisi YASHIL qoldi"
affects: [06-09, 06-10, 06-11, 06-12, 06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Literal tip aliasi mahsulot reyestri bilan IMPORT-VAQTIDA to'plam tengligiga solishtiriladi (`Literal[*frozenset]` statik tip emas, ya'ni nusxa MEXANIK qulflanadi)"
    - "OpenAPI skani `$ref` va `anyOf` bo'ylab REKURSIV yuradi — birlashma javobli marshrutda faqat birinchi variantga qarash qolgan ikkitasini skandan chiqarib yuborardi"
    - "Matritsa darvozasining istisnosi RO'YXAT bo'lib e'lon qilinadi (`QUERY_PARAM_ROUTES`), test ichida `skip` bilan emas — marker qo'yilgan darvoza qizarmaydi"
    - "Kutilgan natija ro'yxati testda QO'LDA yoziladi, modeldan hosila QILINMAYDI: hosila ro'yxat testni «model o'ziga teng» tavtologiyasiga aylantirardi"

key-files:
  created:
    - services/core-api/app/api/v1/billing.py
    - tests/integration/test_billing_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/main.py
    - services/core-api/app/repositories/billing_repo.py
    - tests/tenancy/test_cross_tenant.py

key-decisions:
  - "06-08: ANIQ MOSLIKDA javob TEKIS (`PendingStallResponse`, yetti kalit), ko'p moslikda esa `PendingLookupResponse` — rejaning qabul mezoni («javob kalitlari AYNAN yettita») va 06-03 ning `pendingStallSchema` si IKKALASI ham tekis shaklni talab qiladi"
  - "06-08: nol moslik -> 404 `stall_not_found`, bo'sh `matches` bilan 200 EMAS — bo'sh ro'yxat kassirga «rasta bor, faqat ko'rsatilmadi» deb yolg'on aytardi"
  - "06-08: `amount_soum` ro'yxatda ham, tafsilotda ham TUZATISHLAR BILAN NETLANGAN — aks holda u har doim `tariff_amount_soum` ga teng bo'lardi va §11.2 ning «farq tuzatishni ko'rsatadi» qoidasi HECH QACHON ishlamasdi"
  - "06-08: `day_in_future` va `not_found` xato reyestriga QO'SHILMADI — `ALL_BILLING_ERROR_CODES` ning soni frontend darvozasi bilan qulflangan, ya'ni yangi kod matnsiz uni qizartirardi"
  - "06-08: yangi 422 darvozasi `{403,404}` emas, `!= 422` shaklida — reja matnidagi status to'plami POST marshrutlari uchun (ular 201/409 qaytaradi) mumkin emas; qabul mezoni va sabotaj ikkalasi ham `!= 422` ni o'lchaydi"

patterns-established:
  - "Yangi marshrut moduli uchun: huquq IMZO ALIASIDA, sabab alias docstringida; `require_any_permission()` ning yopiq to'plamiga tegilmaydi"
  - "Javob modelining «yo'q maydonlari» docstringda NOM BILAN sanaladi va to'plam tengligi + OpenAPI hosila skani bilan IKKI QATLAMDA o'lchanadi"
  - "Matritsaga yangi yo'l parametri qo'shilganda qiymat B bozorining HAQIQIY qatori bo'ladi va uni fixture O'ZI yozadi (seed kirishni ta'riflaydi, chiqishni emas)"

requirements-completed: [BILL-02, BILL-03, BILL-04, BILL-05]

# Metrics
duration: 165min
completed: 2026-08-11
---

# Phase 6 Plan 08: Direktor va kassirning o'qish yuzasi Summary

**To'rt marshrut, sakkiz serializator va bitta yangi mexanik darvoza: `charge_id` proyeksiya javobida UMUMAN e'lon qilinmagan va bu ikki MUSTAQIL qatlam (payload to'plam tengligi + OpenAPI hosila skani) bilan o'lchandi — sabotaj ikkalasini ham qizartirdi; `BODY_FILLERS` ning uch faza davomida jimgina yashiringan ko'rligi esa yangi darvoza bilan yopildi va u darhol birinchi topilmasini berdi (`POST /api/v1/users`).**

## Performance

- **Duration:** ~165 min
- **Started:** 2026-08-10T18:25:00Z
- **Completed:** 2026-08-10T20:35:00Z
- **Tasks:** 3
- **Files modified:** 6 (2 yangi, 4 kengaytirilgan)

## Accomplishments

- **D-17 «E'LON QILMASLIK» darajasida bajarildi va IKKI QATLAM bilan o'lchandi.** `GET /billing/pending` javobida `charge_id` yo'q — `null` ham emas, `include_in_schema=False` ham emas. Naqsh `schemas.py::BlindItemResponse` dan verbatim olindi (uning uch bandi: «`None` yetarli emas», «sxemadan yashirish himoya emas», «marshrutning o'zi sxemada ko'rinadi»).
- **D-20 IMKONSIZLIK darajasiga chiqarildi.** `tariff_id`, `category_id`, `valid_from` birorta `/billing/*` javobida yo'q — ya'ni klientda pul arifmetikasi *taqiqlanmaydi*, **kirish ma'lumoti yo'q**. `total_due_soum` serverda (`sbozor_core.billing.total_due_soum()`, 06-01).
- **C-10: `PERSONAL_ROUTES` O'SMADI.** To'rtala marshrut ham `vendor_name`/`phone`/`full_name` dan bittasini ham qaytarmaydi; `test_personal_data_coverage.py` **13/13 yashil**. Nom bilan aylanib o'tish (`vendor_label`, `payer`, `who`) ham yo'q — OpenAPI skani `PERSONAL_FIELDS` ni butun `/billing/*` grafi bo'ylab qidiradi.
- **C-9: `require_any_permission()` TEGILMADI.** Kassir va direktor bitta marshrutni (`/pending`) BITTA HUQUQ (`billing_collect_view`) orqali bo'lishadi. Fayl matnida u faqat modul docstringida — **import qilinmagan, chaqirilmagan** (`from app.deps import Principal, TenantSessionDep, require_permission`).
- **D-05 uch alohida sanoq bilan bajarildi.** `AnomalyListResponse` da `unassigned_count` / `closed_day_count` / `no_coverage_count` — umumiy `anomaly_count` maydoni **YO'Q** va uchalasi nol bo'lganda ham qaytadi.
- **⛔ `BODY_FILLERS` NING MEXANIK KO'RLIGI YOPILDI VA U DARHOL TOPILMA BERDI.** Yangi `test_no_matrix_route_returns_422` ishga tushgan zahoti `POST /api/v1/users` ning tanasi **umuman yo'qligini** ko'rsatdi: marshrut 01-05 dan beri matritsada turgan, har safar **422** olgan va uning tenant da'vosi **hech qachon sinalmagan**. Yozuv qo'shildi.
- **Yangi paket o'rnatilmadi**, yangi `SECURITY DEFINER` funksiya qo'shilmadi, `SNAPSHOT_EVIDENCE_FRAME_ROUTES` va `MINIMUM_MATRIX_ROUTES` **tegilmadi**.

## Task Commits

1. **Task 1: `schemas.py` — maydonni E'LON QILMASLIK naqshi** — `62f4327` (feat)
2. **Task 2: `api/v1/billing.py` — to'rt marshrut, ikki imzo aliasi, nol-natija** — `8397509` (feat)
3. **Task 3: tenant matritsasi, `charge_id` filleri va YANGI 422 darvozasi** — `1b3751f` (test)

## Files Created/Modified

- `services/core-api/app/api/v1/billing.py` (**yangi**, 399 qator) — to'rt marshrut, ikki imzo aliasi, `_report_day()` (standart KECHA + kelajak 422).
- `tests/integration/test_billing_api.py` (**yangi**, 828 qator) — 22 test, besh guruh; OpenAPI skani `$ref`/`anyOf` bo'ylab rekursiv.
- `services/core-api/app/schemas.py` (+418) — sakkiz model, ikki juftlangan `model_validator`, `AmountUnavailableReason` ning import-vaqti darvozasi.
- `services/core-api/app/repositories/billing_repo.py` (+~470) — `charge_list()`, `charge_detail()`, `anomaly_list()`, `_MARKET_OPEN` va `PendingMarket.market_open`.
- `services/core-api/app/main.py` (+33) — `/billing` prefiksi va §4.3 ning to'rt sababi.
- `tests/tenancy/test_cross_tenant.py` (+~230) — `MatrixBillingRows`, `billing_rows` fixture'i, `charge_id` filleri, `POST /users` tanasi, `QUERY_PARAM_ROUTES`, `MIN_BODY_ROUTES` va yangi darvoza.

## Sabotaj (D-30) — IKKI URINISH, IKKALASI HAM QIZARDI

| # | Sabotaj | Natija | Xulosa |
|---|---------|--------|--------|
| **S-A (D-17)** | `PendingStallResponse` ga `charge_id: UUID \| None = None` maydoni qo'shildi | 🔴 **QIZARDI — IKKALA QATLAM** | `test_the_pending_payload_has_exactly_the_seven_keys` (payload to'plam tengligi) **va** `test_charge_id_is_declared_only_by_the_charge_routes` (OpenAPI hosila skani) mustaqil ravishda yiqildi. Qolgan 20 test **yashil qoldi** — ya'ni ikkala test ham AYNAN o'z xossasini o'lchaydi, «hammasi buzildi» ni emas |
| **S-B (§6 ko'rligi)** | `BODY_FILLERS[POST /api/v1/zones]` yozuvi **o'chirildi** | 🔴 **QIZARDI — FAQAT YANGI DARVOZA** | `test_no_matrix_route_returns_422[POST_/api/v1/zones]` yiqildi (`assert 422 != 422`, xabar `BODY_FILLERS[POST_/api/v1/zones]` ni NOMMA-NOM ko'rsatdi). ⛔ **`test_body_fillers_point_at_live_routes` YASHIL QOLDI** va `test_no_route_leaks_other_market_identifiers[POST_/api/v1/zones]` ham — ya'ni o'lchangan ko'rlik AYNAN mavjud edi va u AYNAN yangi darvoza bilan yopildi |

⚠ **S-A da `charge_id` ATAYIN `= None` standarti bilan qo'shildi** — ya'ni sabotaj «maydonni to'ldirish» emas, «maydonni E'LON QILISH» edi. Aynan shu D-17 ning matni: `null` qilib yuborish ham buzilish, chunki keyingi bosqich **bir satrlik**. Ikkala sabotaj ham `git checkout -- <fayl>` / teskari yamoq bilan qaytarildi; `git status` toza.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `billing_repo` da `charge_list()` / `charge_detail()` / `anomaly_list()` MAVJUD EMAS edi**

- **Found during:** Task 2
- **Issue:** Reja «handlerlar `billing_repo` ni chaqiradi: `pending_projection()`, `charge_list()`, `charge_detail()`, `anomaly_list()`» deydi va `files_modified` da `billing_repo.py` **yo'q** — ya'ni reja bu uchtasini mavjud deb hisoblagan. 06-06 esa **yetti** funksiya yozgan va ular orasida bu uchtasi yo'q. Handlerni ularsiz yozishning yagona yo'li — SQL ni marshrutga ko'chirish, ya'ni D-16 ni buzish.
- **Fix:** Uch o'qish funksiyasi `billing_repo.py` ga qo'shildi (7-bo'lim). Netlangan summa mavjud `_SIGNED_ADJUSTMENT_EXPR` konstantasidan chiqadi — ikkinchi arifmetika yozilmadi.
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Verification:** `test_billing_api.py` 22/22; `mypy`/`ruff` toza. 06-07 ning fayllariga **tegilmadi** (`billing_repo.py` uning ro'yxatida yo'q).
- **Committed in:** `8397509`

**2. [Rule 2 - Missing Critical] `PendingMarket` ga `market_open` qo'shildi**

- **Found during:** Task 2
- **Issue:** `PendingMarketResponse` UI-SPEC §9.5 va 06-03 ning `pendingMarketSummarySchema` si bo'yicha `market_open` ni **talab qiladi**, 06-06 ning `PendingMarket` i esa uni bermaydi. Uni rastalar ro'yxatidan hosila qilish RASTASIZ bozorda javobsiz qolardi.
- **Fix:** `_market_projection()` uni AYNI `as_of` bilan alohida so'raydi (`market_is_open()` DB funksiyasi). Bu 06-06 deviatsiya #1 ning aynan takrori va sabab ham o'sha: `now()` bilan olingan ikkinchi so'rov yarim tunda BOSHQA kunning javobini berardi.
- **Files modified:** `services/core-api/app/repositories/billing_repo.py`
- **Committed in:** `8397509`

**3. [Rule 2 - Missing Critical] `BODY_FILLERS` ga `POST /api/v1/users` yozuvi**

- **Found during:** Task 3 (yangi darvozaning birinchi yugurishi)
- **Issue:** Marshrut 01-05 dan beri matritsada, tanasi esa **yo'q** — ya'ni u har safar **422** olardi. Yo'l parametri bo'lmagani uchun `test_cross_tenant_object_returns_404` unga umuman tegmaydi, `test_no_route_leaks_...` esa 422 javobida ham yashil qoladi (validatsiya xatosida B bozorining identifikatori bo'lmaydi). Natija: marshrutning tenant da'vosi **uch faza davomida sinalmagan**.
- **Fix:** `{phone, full_name, roles: ["cashier"]}` tanasi qo'shildi. Telefon `TEST_PHONE_PREFIX` diapazonida (`cleanup_test_users()` uni supurib ketadi) va SOBIT — ikkinchi chaqiruv `409 phone_taken` beradi, bu esa darvoza uchun yetarli.
- **Files modified:** `tests/tenancy/test_cross_tenant.py`
- **Verification:** `tests/tenancy` **628/628 yashil**.
- **Committed in:** `1b3751f`

**4. [Rule 3 - Blocking] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**

- **Found during:** Task 1 (birinchi `docker compose run`)
- **Issue:** Ikkala fayl ham `.gitignore` da (06-04/06-05/06-06 dagi holatning to'rtinchi takrori).
- **Fix:** Ikkalasi asosiy repodan **NUSXALANDI**. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning `frontend/node_modules` ini yo'q qilgan.
- **Files modified:** yo'q (gitignored infra fayllari)
- **Committed in:** — (repoga tegmaydi)

**5. [Rule 1 - Bug] `HTTP_422_UNPROCESSABLE_ENTITY` deprecated alias edi**

- **Found during:** Task 3 (`test_billing_api.py` ning birinchi yugurishi)
- **Issue:** Starlette ogohlantirish berdi; kod bazasining qolgan o'n ikki joyi allaqachon `HTTP_422_UNPROCESSABLE_CONTENT` (RFC 9110 nomi) ishlatadi (`audit.py:184-187` da sabab ham yozilgan).
- **Fix:** Joriy nomga o'tildi, sabab izohda.
- **Files modified:** `services/core-api/app/api/v1/billing.py`
- **Committed in:** `1b3751f`

### Reja matnining aniqlashtirilishi (ziddiyat emas)

- **`PendingLookupResponse` — FAQAT ko'p moslik javobi.** Reja Task 1 da uni `?stall_code=` ning javobi deb yozadi, LEKIN Task 3 ning qabul mezoni «`GET /billing/pending?stall_code=` javobining kalitlari **AYNAN** UI-SPEC §9.2 dagi yettita» deydi — bu **tekis** shakl. UI-SPEC §9.2 ning o'zi ham javobni tekis qilib ta'riflaydi va 06-03 ning `pendingStallSchema` si (`z.strictObject`, allaqachon merge qilingan) uni **shunday parse qiladi**. Shuning uchun: aniq moslikda `PendingStallResponse` (tekis, yetti kalit), ko'p moslikda `PendingLookupResponse`, nol moslikda **404**. Ikkalasi ham `response_model` birlashmasida e'lon qilingan, ya'ni OpenAPI skani ikkalasini ham ko'radi.
- **Yangi darvozaning sharti `{403, 404}` EMAS, `!= 422`.** Reja matni statuslar to'plamini nomlaydi, lekin `POST /api/v1/zones` A bozori sessiyasi bilan **201** (yoki takrorida 409) qaytaradi — ya'ni `{403,404}` sharti darvozani BIRINCHI yugurishdayoq imkonsiz qilardi. Rejaning **qabul mezoni** esa aynan `!= 422` ni o'lchaydi («`BODY_FILLERS` yozuvi vaqtincha o'chirilsa test qizaradi»), sabotaj ham shuni tasdiqladi. Shakl `test_file_routes_actually_execute` (02-12) dan olingan — u ham AYNAN shu qarorni SABOTAJ bilan asoslagan.
- **`MINIMUM_MATRIX_ROUTES` ATAYIN KO'TARILMADI.** Reja shuni buyuradi va sabab shu yerda **ochiq yozilgan**: shart `>=`, ya'ni to'rt yangi marshrut qo'shilgani bilan darvoza yashil qoladi; yakuniy son **06-14** da, o'lchov bilan qo'yiladi. ⚠ Keyingi ijrochi buni «unutilgan» deb o'qimasin.
- **Ikki grep mezoni rejaning O'Z talabiga zid va ular MATN darajasida bajarilmadi.** (a) «yangi bloklarda `vendor_name|full_name|phone` → 0», lekin o'sha reja docstringda yo'q maydonlarni **nom bilan sanashni** buyuradi; (b) «`grep -c require_any_permission` → 0» va «`grep -c audit_read` → 0», lekin reja sababni **modul docstringiga** yozishni buyuradi. Ikkala holatda ham nomlar FAQAT docstringda: `require_any_permission` — 4 va 16-qatorlar, `audit_read` — 22, 25 va 324-qatorlar; **import ham, chaqiruv ham yo'q** (`from app.deps import Principal, TenantSessionDep, require_permission`). Yuk ko'taruvchi darvoza esa matn skani emas — u `test_personal_data_coverage.py` (marshrut grafini yuradi) va u **yashil**.
- **`day_in_future` / `not_found` xato reyestriga qo'shilmadi.** `ALL_BILLING_ERROR_CODES` ning soni `scripts/error-codes.test.mjs` tomonidan uchala locale'dagi matn juftligi bilan solishtiriladi — matn qo'shilmagan yangi kod o'sha darvozani qizartirardi. `not_found` uchun presedent allaqachon bor (`assignments.py:149`, `reviews.py:211`).

---

**Total deviations:** 5 auto-fixed (2 blocking, 2 missing-critical, 1 bug) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Qamrov kengaymadi. Yangi paket **o'rnatilmadi** (T-06-SC), 06-07 ning birorta fayliga **tegilmadi**, frontendga **tegilmadi**.

## Issues Encountered

- **To'liq to'plamda 39 qizil — hammasi NVR-sim va SeaweedFS guruhida, sababi PARALLEL WORKTREE.** `pytest -q` yugurayotgan paytda qo'shni worktree (06-07) o'z `docker compose run` ini ishga tushirdi va u **umumiy** `sbozor-storage-1` / `nvr-sim` konteynerlarini **qayta yaratdi** (`Container sbozor-storage-1 Recreate` — `compose run` ning standart xulqi). O'lchov: o'sha 39 test **izolyatsiyada qayta yugurtirildi va 115/115 yashil bo'ldi** (`test_storage_layout.py` + `test_nvr_sim.py` → 34/34; `test_nvr_discovery.py` + `test_nvr_discovery_job.py` + `test_nvr_errors.py` + `test_nvr_api.py` + `test_phase3_criteria.py` + `test_live_view_e2e.py` → 81/81). Bu reja birorta NVR/RTSP/kamera/ombor fayliga **tegmaydi** va o'sha fayllar billing modullarini import qilmaydi. ⛔ Repoga birorta o'zgarish kiritilmadi.
- **5-fazadan meros flaky test (`test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`) bu yugurishda QIZARMADI.** U `deferred-items.md` ning 1-bandida va tegilmadi.
- **`gate` ning frontend yarmi bu worktree'da yugurmaydi** — `frontend/node_modules` yo'q. ⛔ Junction/symlink **YARATILMADI** (bu ilgari asosiy checkout'ni buzgan), `npm ci` esa paket-menejer amali va ijrochi qoidasi bo'yicha avto-tuzatishdan chiqarilgan. Bu reja birorta frontend fayliga **tegmaydi**, ya'ni `gate` byudjetining (1250 s) to'liq o'lchovi yana keyingi to'lqinga qoladi.

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_billing_api.py -q` | ✅ **22/22** |
| `pytest tests/tenancy -q` | ✅ **628/628** |
| `pytest tests/tenancy/test_personal_data_coverage.py -q` | ✅ **13/13** (`PERSONAL_ROUTES` **o'smadi**) |
| `pytest tests/tenancy/test_route_coverage.py -q` | ✅ (`MINIMUM_MATRIX_ROUTES` **o'zgarmagan**) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (**306** fayl formatlangan, **297** fayl tiplangan) |
| `pytest -q` (to'liq to'plam) | ⚠ 39 qizil — hammasi umumiy konteyner poygasidan (yuqoridagi bandga qarang) |
| O'sha 39 testning izolyatsiyada qayta yugurishi | ✅ **115/115** |

**Qabul mezonlari (Task 1):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `set(PendingStallResponse.model_fields) == {yetti kalit}` | to'plam tengligi | ✅ |
| `'tariff_id' not in ChargeDetailResponse.model_fields` | ✅ | ✅ |
| `set(AnomalyListResponse.model_fields) == {day, rows, uch sanoq}` | to'plam tengligi | ✅ |
| Juftlangan invariant → `ValidationError` | ikki yo'nalish alohida | ✅ |
| `extra="forbid"` → `ValidationError` | ✅ | ✅ |
| `test_personal_data_coverage.py` yashil | 13/13 | ✅ |

**Qabul mezonlari (Task 2):**

| Mezon | O'lchov | Natija |
|---|---|---|
| Kassir `/pending` da **200** | `test_the_report_viewer_also_sees_the_projection` + kalit testlari | ✅ |
| Kassir `/charges` va `/anomalies` da **403** | `test_the_cashier_cannot_reach_the_director_surface` | ✅ |
| Kunsiz `/charges` → `day` **KECHA** | `test_the_default_day_is_yesterday` | ✅ |
| `?day=<ertaga>` → **422** | `test_a_future_day_is_rejected` | ✅ |
| `grep -c require_any_permission` | **2** — ikkalasi ham modul docstringida; import/chaqiruv **yo'q** | ⚠ (yuqoridagi «reja matnining aniqlashtirilishi» ga qarang) |
| `grep -c audit_read` | **3** — uchalasi ham docstringda | ⚠ (o'sha band) |
| `grep -cE "^from datetime import\|^from uuid import"` ≥ 2, `TYPE_CHECKING` dan tashqarida | **2**, ikkalasi ham modul darajasida | ✅ |
| Bo'sh kunda `charge_count == 0` **va** `charged_soum == 0` | `test_an_empty_day_still_returns_both_charge_counters` | ✅ |
| `test_no_unclassified_routes` yashil | to'rt marshrut klassifikatsiya qilingan | ✅ |
| `openapi()` da `/pending` javobida `charge_id` yo'q | hosila skan | ✅ |

**Qabul mezonlari (Task 3):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `test_cross_tenant_object_returns_404` — `/charges/{charge_id}` **404** (403 emas, 422 emas) | matritsa | ✅ |
| `test_no_matrix_route_returns_422` mavjud, yashil, `MIN_BODY_ROUTES` bilan | 37 marshrut, chegara 30 | ✅ |
| Sabotaj: `BODY_FILLERS` yozuvi o'chirilsa yangi darvoza **qizaradi** | S-B | ✅ 🔴 |
| `PARAM_FILLERS` da `charge_id` HAQIQIY qiymat | `test_param_fillers_point_at_the_other_market` | ✅ |
| `test_all_path_params_have_fillers` yashil | ✅ | ✅ |
| OpenAPI skani sabotajda **qizaradi** | S-A | ✅ 🔴 |
| Bo'sh kunda uchala anomaliya sanog'i **0** bilan qaytadi | `test_an_empty_day_still_returns_all_three_anomaly_counters` | ✅ |
| `MINIMUM_MATRIX_ROUTES` o'zgarmagan | `git diff tests/tenancy/test_route_coverage.py` → **bo'sh** | ✅ |
| `pytest tests/tenancy -q` to'liq yashil | 628/628 | ✅ |

## Known Stubs

Yo'q. Ikkala yangi fayl ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q.

⚠ **`PendingLookupResponse.stall` bugungi kodda har doim `null`** va u **stub EMAS**: maydon «aynan bitta moslik» slotini nom bilan band qilib turadi va uning juftlangan invarianti (`stall` va `matches` bir vaqtda to'lgan bo'la olmaydi) `model_validator` bilan majburlanadi. Aniq moslik holatida marshrut TEKIS `PendingStallResponse` ni qaytaradi — sabab §9.2 ning to'plam tengligi va 06-03 ning `pendingStallSchema` si (yuqoridagi «reja matnining aniqlashtirilishi» ga qarang). Sabab modelning docstringida ochiq yozilgan, aks holda keyingi ijrochi uni «o'lik maydon» deb o'chirardi.

⚠ **`ChargeEvidenceRow.snapshot_id` kontraktda nullable, bugungi sxemada esa `NOT NULL`** — ya'ni `null` amalda kelmaydi. Bu ham stub emas: 06-03 ning `chargeEvidenceSchema` si uni `z.uuid().nullable()` deb e'lon qilgan va 05-14 ning darsi bo'yicha klientda «kadr yo'q → qator umuman chizilmaydi» shoxi MAVJUD bo'lishi kerak. Sabab `_CHARGE_EVIDENCE_ROWS` docstringida.

## Threat Flags

Yangi xavfsizlik yuzasi **to'rtta marshrut** bilan ochildi va ularning hammasi threat register bo'yicha qoplangan:

- ⛔ Threat register: **oltala `mitigate` bandi bajarildi** — T-06-43 (`charge_id`/`tariff_id`/`vendor_*` e'lon qilinmadi + ikki qatlam + S-A sabotaji), T-06-44 (`PERSONAL_FIELDS` birorta javobda yo'q, `PERSONAL_ROUTES` o'smadi), T-06-45 (RLS + `PARAM_FILLERS` da HAQIQIY B qiymati → 404; to'qilgan UUID ishlatilmadi), T-06-46 (`require_any_permission()` import ham qilinmadi; `test_personal_data_coverage.py:691-706` tegilmadi), T-06-47 (yangi `test_no_matrix_route_returns_422` + `MIN_BODY_ROUTES` quyi chegarasi + S-B sabotaji), T-06-48 (kelajak kuni → 422). T-06-SC (`accept`) — yangi paket o'rnatilmadi.
- Yangi `SECURITY DEFINER` funksiya **qo'shilmadi**; `market_is_open()` INVOKER bo'lib qoldi.
- Yangi rasm/fayl yuzasi **ochilmadi**: dalil kadri MAVJUD `GET /snapshots/{id}/image` proxysidan keladi va `SNAPSHOT_EVIDENCE_FRAME_ROUTES` **tegilmadi** (C-9).
- ⚠ **Yangi tenant yuzasi**: to'rt marshrut `TenantSessionDep` ostida va cross-tenant matritsasiga **avtomatik** tushdi (negativ ro'yxat). `charge_id` filleri B bozorining haqiqiy qatorini ko'rsatadi.

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): parallel worktree'lar bir vaqtda `docker compose run` chaqirsa umumiy `storage`/`nvr-sim` konteynerlari **qayta yaratiladi** va boshqasining yugurayotgan to'plami qizaradi. Tuzatish: to'lqin ichida to'liq to'plamni ketma-ket yugurtirish, yoki `docker compose --profile sim up -d --force-recreate nvr-sim nvr-sim-rtsp` dan keyin qayta o'lchash (⛔ `-v` **ishlatilmaydi**).

## Next Phase Readiness

- **06-09 (`POST /payments`):** xato reyestri va `PendingStallResponse` tayyor; kassir kvota to'plamini `total_due_soum` bilan solishtiradi. ⚠ Yangi POST marshruti `BODY_FILLERS` ga yozilishi SHART — aks holda `test_no_matrix_route_returns_422` **darhol qizaradi** (darvoza aynan shu uchun qo'yilgan).
- **06-10 (smena):** `POST /shifts`, `POST /shifts/{id}/close` uchun ham o'sha darvoza amal qiladi; `shift_manage` huquqi 06-02 da tayyor.
- **06-11/06-13 (frontend):** kontrakt **o'lchangan**, LEKIN ⛔ **06-03 ning uchta klient sxemasi serverdan orqada** — `chargeListSchema`/`anomalyListSchema` (`{items}` → `{day, rows, hisoblagichlar}`) va ko'p moslik uchun `pendingLookupSchema`. Band `deferred-items.md` ning **2-qatorida** to'liq yozilgan.
- **06-12/06-14 (darvozalar):** G-22 (taqiqlangan nomlar) ning **server yarmi** shu rejada hosila skan bilan yopildi; klient yarmi (`scripts/collect-surface.test.mjs`) 06-12 niki. `MINIMUM_MATRIX_ROUTES` **06-14 da** ko'tariladi (bugungi o'lchov: matritsada 4 yangi marshrut, tana yuboriladigan marshrutlar **37**).
