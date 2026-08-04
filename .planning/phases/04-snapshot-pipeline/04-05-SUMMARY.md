---
phase: 04-snapshot-pipeline
plan: 05
subsystem: backend
tags: [repository, skip-locked, lease, idempotency, daterange-split, rls, cam-04, cam-05, d-05]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 03
    provides: "Beshta model, `uq_capture_runs_...` idempotentlik kaliti, `ex_snapshot_schedules_no_overlap`, `market_activate()` ning standart profili, `tests/fixtures/snapshot_domain.py` seed'i"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`CAPTURE_AUTH_LOCKING_CODES` / `CAPTURE_DEFER_CODES` / `CAPTURE_ERROR_META`, `quality.py` ning `VERDICT_*`/`LIGHT_*` konstantalari, fazaning 24 sozlamasi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`nvr_repo.py` — shartli holat o'tishi, «tekshir-keyin-yoz» rad etilishi, xom `text()` da tiplangan bind; `mask_sensitive()`; `sqlstate_of()`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`market_is_open()`, `assignment_period()` va `[)` konventsiyasi, `daterange` bo'lish naqshi, `market_today` fixture'i"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`TenantScopedRepository`, RLS policy'lari, `tenant_session` fixture'i"
provides:
  - "`CaptureRepository` — `ensure_plan` / `claim_due` / `release_expired` / `mark_missed` / `finish_*` / `defer` / `day_summary` / `list_day` / `cameras_in_plan`"
  - "`ScheduleRepository` — `today_and_tomorrow` (BITTA so'rov) / `active_profile` / `slots_for` / `uncovered_days` / `create_seasonal` (davr bo'lish) / `update_slots` / `delete_future`"
  - "`SnapshotRepository` — `record` / `get` / `retention_candidates` / `mark_compressed` / `mark_purged`; qator o'chiradigan metod YO'Q"
  - "To'rt xato sinfi va ularning HTTP kodlari: `ScheduleStartsTooSoonError` 422, `ScheduleSlotsInvalidError` 422, `ScheduleNotEditableError` 403, `ScheduleOverlapError` 409"
  - "D-05 ning TUZILMAVIY kafolati — `ensure_plan()` bugungi rejani SLOT o'lchovida muzlatadi"
  - "`test_quality_enum_parity.py` — 04-04 nomlagan qarzning yopilishi (sof modul <-> enum <-> CHECK)"
affects: [04-06, 04-07, 04-08, 04-09, 04-10, 04-11, 05-cv-zonalar, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`SELECT … FOR UPDATE SKIP LOCKED` + ijara: ikkala mexanizm TURLI muddatni qoplaydi va ALOHIDA testlar bilan o'lchanadi — bittasini o'chirish ikkinchisini yashil qoldiradi"
    - "Parallel qulf testi IKKI OCHIQ tranzaksiyani talab qiladi va `SET LOCAL statement_timeout` bilan quriladi: `SKIP LOCKED` siz test OSILIB QOLARDI, timeout uni AYNAN qizartiradi"
    - "`pool_size=1` engine ustida konkurentlikni o'lchab bo'lmaydi — test o'z engine'ini quradi, `conftest.py` ga tegmaydi"
    - "Xom `text()` da `:param::cast` shakli parametr DEB TANILMAYDI (SQLAlchemy regexida `(?!:)` lookahead) — tiplangan `bindparam` kastni O'ZI chiqaradi"
    - "«Tekshir-keyin-yoz» taqiqlangan bo'lsa ham, SHART O'SHA OPERATOR ICHIDA bo'lsa u poyga tug'dirmaydi (`NOT EXISTS ... OR EXISTS ...` + `ON CONFLICT`)"
    - "Sana bo'yicha qaror qiladigan test QADALGAN sanaga tayanmaydi: seed'ning sobit kuni bugun kelajak, ertaga o'tmish bo'ladi va shox jimgina almashadi"

key-files:
  created:
    - services/core-api/app/repositories/capture_repo.py
    - services/core-api/app/repositories/schedule_repo.py
    - services/core-api/app/repositories/snapshot_repo.py
    - tests/integration/test_capture_repo.py
    - tests/integration/test_schedule_repo.py
    - tests/unit/test_quality_enum_parity.py
  modified: []
  deleted: []

key-decisions:
  - "D-05 TUZILMAVIY qilindi: `ensure_plan()` bugungi rejani SLOT o'lchovida muzlatadi. `capture_tick` HAR DAQIQADA `ensure_plan(bugun)` ni chaqiradi (§3.3), ya'ni shartsiz so'rov kun o'rtasidagi jadval tahririni bugungi rejaga yozib qo'yardi va SC#1 yolg'onga aylanardi"
  - "Muzlatish KUN o'lchovida EMAS, SLOT o'lchovida: mid-day kashf etilgan kamera bugungi MAVJUD slotlarni oladi, yangi VAQT esa ertagacha kutadi. Kun o'lchovi bunday kamerani butun kunga ko'rinmas qilardi"
  - "`claim_due()` ga `locked_until` predikati QO'SHILDI (§A.2 eskizida YO'Q edi) — usiz `defer()` butunlay no-op bo'lardi va T-04-35 mitigatsiyasi umuman mavjud bo'lmasdi"
  - "`defer()` ga ixtiyoriy `code` argumenti: berilsa u `CAPTURE_DEFER_CODES` da bo'lishi SHART. Qulflovchi kodni kechiktirish T-04-34 ni bitta chaqiruv bilan chetlab o'tardi"
  - "`finish_failed()` da qulflovchi kod qarori Python'da (u KODGA bog'liq), byudjet qarori esa SQL ichida (u QATOR HOLATIGA bog'liq) — o'qib-keyin-yozish orasida `release_expired()` qatorni qaytarib yuborishi mumkin edi"
  - "Bu modulda barcha vaqt tamg'alari DB soatidan (`now()`), `nvr_repo` dan FARQLI: watchdog so'rovlari aynan o'sha soatga qarab qaror qiladi va ikkinchi soat chegaralarni siljitardi"
  - "`day_summary()` ARXIVLANGAN kamerani chiqarmaydi — `list_day()` bilan bir xil to'plam. Filtrlash matritsani xulosa bilan ZID qilardi (175 rejalashtirildi, 168 hujayra)"
  - "`today_and_tomorrow()` «bugun» ni SQL ichida hisoblaydi (argument emas), yozish metodlari esa uni ARGUMENT sifatida oladi — o'qishda atomiklik, yozishda so'rov bo'yicha qadalgan biznes-kun"
  - "`create_seasonal()` `starts_on` da BOSHLANADIGAN profil bo'lsa RAD ETADI: qisqartirish bo'sh davr berardi va `period_not_empty` yiqilardi; avtomatik almashtirish esa kelajakdagi profilni JIMGINA yo'q qilardi"
  - "`schedule_repo` da o'chirish RUXSAT ETILADI (fazadagi yagona istisno) — hali boshlanmagan profil birorta `capture_runs` qatorini tug'dirmagan, ya'ni dalil yo'q; amal audit jurnaliga tushadi"

patterns-established:
  - "Sabotaj o'lchovi endi UCH ustunli: qaysi test qizardi, qaysilari YASHIL qoldi VA reja nimani bashorat qilgan edi. Uchinchisi ikki marta reja matnidan kuchliroq natija berdi"
  - "Bir plandagi ikki repozitoriyni BIRGA sinaydigan test qonuniy: D-05 ni `schedule_repo` yolg'iz o'lchay olmaydi (u jadvalni ko'radi, rejani emas)"
  - "Zanjirli parity testi: sof modul -> enum -> DB CHECK ifodasi bitta faylda uchrashtiriladi, chunki har bir bo'g'in alohida qulflangan bo'lsa ham ULAR ORASI qo'riqlanmagan qoladi"

requirements-completed: [CAM-04, CAM-05, CAM-06, CAM-07]

# Metrics
duration: 1h 20m
completed: 2026-08-04
---

# Phase 4 Plan 05: Repozitoriy qatlami — reja, ijara va davr bo'lish Summary

**Fazaning markaziy orkestratsiya primitivi (`FOR UPDATE SKIP LOCKED` + ijara) precedentsiz o'rnatildi va IKKALA mexanizm ALOHIDA o'lchandi; CAM-05 idempotentligi endi qator sanog'i bilan (04-03 topgan qarzning xulq yarmi), D-05 esa bitta `INSERT` ichidagi slot-muzlatishi bilan TUZILMAVIY bo'ldi; mavsumiy profil davrni bo'ladi va tugash sanasidan keyin oldingisini vaqtlari bilan tiklaydi; `snapshots` qatorini o'chiradigan metod umuman yozilmadi.**

## Performance

- **Duration:** ~1 soat 20 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 6 ta yangi — 2 351 qator ishlab chiqarish kodi, 2 283 qator test
- **Commits:** 5 (bittasi TDD RED, bittasi D-05 tuzatishi)

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 1 | `capture_repo` — RED | `9876ff7` (test) |
| 1 | `capture_repo` — GREEN | `b023e8d` (feat) |
| — | D-05 tuzilmaviy tuzatishi (1-deviatsiya) | `0d8ac4f` (fix) |
| 2 | `schedule_repo` + testlari | `93b8678` (feat) |
| 3 | `snapshot_repo` + parity testi | `79b48ac` (feat) |

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

Bu loyihada ikkinchi ustun qayta-qayta birinchisidan ko'ra ko'proq ma'lumot bergan. Bu safar **uchinchi ustun** ham kerak bo'ldi: reja to'rt bashoratdan ikkitasida yanglishdi va ikkalasida ham haqiqiy natija rejanikidan **kuchliroq** chiqdi.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `claim_due` dan `SKIP LOCKED` olib tashlandi | **AYNAN 1 test**: `test_parallel_claim_due_never_hands_the_same_row_twice_skip_locked`, `QueryCanceled` bilan (`statement_timeout` 4 s) | Qolgan **25** test, jumladan BARCHA boshqa `claim_due` testlari | ✅ **AYNAN bashorat qilingandek.** Timeout bo'lmasa test osilib qolardi — u shu sababdan qo'yilgan |
| 2 | `finish_failed` dagi `CAPTURE_AUTH_LOCKING_CODES` sharti o'chirildi | **AYNAN 1 test**: `test_an_auth_locking_code_burns_the_whole_retry_budget` (`'pending' == 'failed'`) | Qolgan 25, jumladan `test_defer_keeps_the_row_pending_and_delays_the_next_tick` | ✅ **AYNAN bashorat qilingandek** — ikki siyosat mustaqil ekani isbotlandi |
| 3 | `ensure_plan` dan D-05 slot-muzlatishi olib tashlandi | **AYNAN 1 test**: `test_a_slot_added_after_materialisation_waits_until_tomorrow` | Nazorat bandi `test_a_camera_discovered_after_materialisation_still_gets_todays_slots` — **YASHIL** (to'g'ri: muzlatishsiz ham yangi kamera bugungi slotlarni oladi) | ⚠ **Rejada bu sabotaj YO'Q** — u 1-deviatsiya bilan birga tug'ildi |
| 4 | `create_seasonal` dan davrni **qisqartirish** qadami olib tashlandi | **5 test**: uchala split testi + `delete_future` + cross-tenant testi (hammasi `create_seasonal` orqali o'tadi) | **12 test**, jumladan **`test_an_overlapping_period_is_a_recognised_error_not_a_five_hundred`** va **ikkala `uncovered_days` testi** | ⚠ **Reja YARIM to'g'ri.** «`uncovered_days` yashil qoladi» — ✅ to'g'ri. «Kesishuv testi AYNAN qizaradi» — ❌ **noto'g'ri**: u ATAYIN bo'lishga tayanmaydigan yo'ldan boradi (davr BO'SHLIQDA boshlanadi), shuning uchun DB invarianti ilova semantikasidan MUSTAQIL o'lchanadi. Bu rejaning da'vosidan kuchliroq natija |
| 5 | `SnapshotQuality` ga `"unusable"` a'zosi qo'shildi | **3/5 parity testi**: `test_verdict_constants_equal_...`, `test_the_verdict_tuple_has_no_duplicates`, `test_verdict_tuple_equals_...` | **`test_quality_filter.py` ning BARCHA 24 testi** | ✅ **AYNAN bashorat qilingandek** — ikki manba mustaqil va ko'prik aynan shu fayl |

Har besh holatda ham fayl darhol tiklandi va to'plam qayta yashil bo'ldi (`git diff --exit-code packages/.../enums.py` bilan tasdiqlandi).

## O'LCHOVLAR — taxmin qilinmadi

| Nima | Natija |
|---|---|
| `:business_date::date` xom `text()` da | **Parametr DEB TANILMAYDI.** SQLAlchemy ning bind regexida `(?!:)` lookahead bor: `::` dan oldin turgan `:name` xom matn bo'lib asyncpg'ga boradi va `syntax error at or near ":"` beradi. Uchta bir xil parametrdan ikkitasi almashdi, uchinchisi (kastli) almashmadi |
| `pool_size=1` engine'da parallel `claim_due` | **O'lchab bo'lmaydi** — ikkinchi sessiya poolda kutib qolardi va test qulfni emas, pool chegarasini o'lchagan bo'lardi. Test o'z engine'ini quradi (`pool_size=2`) |
| `SKIP LOCKED` siz ikkinchi tranzaksiya | **ABADIY bloklanadi** (osiladi, xato bermaydi). `SET LOCAL statement_timeout = '4000ms'` uni `QueryCanceled` ga aylantiradi — sabotaj natijasi shu bilan KO'RINADIGAN bo'ldi |
| `capture_tick` ning `ensure_plan` chaqirish chastotasi | **HAR DAQIQADA** (`04-PATTERNS.md` §3.3 ning 1-qadami), «kunning birinchi tikida» EMAS — D-05 ni konventsiya sifatida qoldirib bo'lmasligining sababi |
| `snapshots.quality_mean` NULL qabul qiladimi | **YO'Q** (`nullable=False`, 04-03). 04-04 esa `corrupt` uchun `None` qaytaradi — quyida, «Ochiq ziddiyat» |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/integration/test_capture_repo.py test_schedule_repo.py tests/unit/test_quality_enum_parity.py -q` | **48 test**, exit 0 |
| 2 | `pytest tests/integration/test_capture_repo.py -q` | **26** (talab ≥ 11), exit 0 |
| 3 | `pytest tests/integration/test_capture_repo.py -k "skip_locked or parallel" -q` | **1 passed, 23 deselected**, exit 0 |
| 4 | `pytest tests/integration/test_schedule_repo.py -q` | **17** (talab ≥ 9), exit 0 |
| 5 | `pytest tests/integration/test_schedule_repo.py -k "uncovered or split or single_query" -q` | **5**, exit 0 |
| 6 | `pytest tests/unit/test_quality_enum_parity.py -q` | **5**, exit 0 |
| 7 | `pytest tests/tenancy -q` | **426** (o'zgarmagan, talab ≥ 412) | 
| 8 | `pytest tests/unit -q` | **743**, exit 0 |
| 9 | `pytest -q` (to'liq) | **1 702**, exit 0 — baza 1 654 -> **+48** (talab ≥ 1 520) |
| 10 | `pytest tests/integration/test_tariff_history.py -q` | **9** (mavjud davr naqshi qizarmagan) |
| 11 | `pytest tests/unit/test_no_sim_branching.py -q` | **5**, exit 0 |
| 12 | `ruff check . && ruff format --check . && mypy .` | exit 0 (**226 fayl formatlangan, 220 fayl tiplangan**) |
| 13 | `git diff --exit-code services/core-api/pyproject.toml frontend/package.json` | **o'zgarish yo'q** (T-04-SC) |
| 14 | `npm run gate:fast` | exit 0, **64 s** (chegara 180 s) |
| 15 | `npm --prefix frontend run i18n:check` | **577 kalit × 3 til** (o'zgarmagan) |
| 16 | vitest / node darvozalari | **246** / **111** (ikkalasi ham o'zgarmagan) |

Mexanik artefakt mezonlari (rejaning `python -c` darvozalari) ham o'lchandi:

| Mezon | Natija |
|---|---|
| `capture_repo.py` da `FOR UPDATE SKIP LOCKED` + `bindparam` | ✅ |
| `capture_repo.py` da tenant predikati (izohsiz qatorlarda) | **9** ta `market_id = :market_id` + **5** ta `market_id ==` (talab ≥ 3) |
| `capture_repo.py` da `FILTER` | ✅ (`func.count().filter(...)` + docstringdagi ifoda) |
| `capture_repo.py` uzunligi | **1 063** qator (talab ≥ 250) |
| `schedule_repo.py` da xom diapazon konstruktori | ✅ **YO'Q**; `generate_series` **BOR**; `uncovered` **BOR** |
| `snapshot_repo.py` da o'chirish metodi / `DELETE FROM` | ✅ **YO'Q** (izohsiz matnda regex bilan); `storage_tier` + `object_deleted_at` **BOR** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — yetishmayotgan kritik xulq] D-05 hech qanday mexanizm bilan qo'riqlanmagan edi**

- **Topildi:** Task 2 ning `<decisions_context>` ini o'qib, `04-PATTERNS.md` §3.3 bilan solishtirganda
- **Muammo:** D-05 «jadval kun o'rtasida o'zgartirilsa **bugungi rejaga ta'sir qilmaydi**» deydi va SC#1 aynan shunga tayanadi («**ertasi kuni** aynan o'sha slotlarda»). UI ham DL-1 da doimiy, yopib bo'lmaydigan izoh chizadi: «Yangi vaqtlar ERTADAN boshlab ishlaydi». **Lekin `capture_tick` `ensure_plan(bugun)` ni HAR DAQIQADA chaqiradi** (§3.3 ning 1-qadami), ya'ni shartsiz `INSERT … SELECT` soat 12:00 da qo'shilgan vaqtni **bugungi rejaga yozib qo'yardi**. Kafolat faqat «04-07 `ensure_plan` ni kuniga bir marta chaqirsin» degan KONVENTSIYA bo'lib qolardi — va o'sha konventsiya boshqa rejaning boshqa ijrochisida yashardi.
- **Nima uchun kritik:** D-05 ning buzilishi JIM. Hisobotdagi son o'zgaradi, xato chiqmaydi, birorta test qizarmaydi. UI esa aksini va'da qilib turaveradi.
- **Yechim:** `ensure_plan()` ning `WHERE` iga `AND (NOT EXISTS (bugun uchun qator) OR EXISTS (shu `slot_time` bugun allaqachon bor))` qo'shildi. **Bu «tekshir-keyin-yoz» EMAS va rejaning 3-majburiyatiga zid kelmaydi:** shart o'sha operatorning ICHIDA, alohida `SELECT` yo'q, ya'ni poyga oynasi ham yo'q. Uchala interleaving ham to'g'ri: ikki tik bo'sh kunni ko'rsa ikkalasi ham yozadi va `ON CONFLICT` dublikatni yutadi; biri qatorlarni ko'rsa u yangi vaqt yozmaydi. Idempotentlik hamon `UNIQUE` konstraytida.
- **Muzlatish SLOT o'lchovida, KUN o'lchovida EMAS** — bu farq alohida qaror: kun o'lchovi mid-day kashf etilgan kamerani BUTUN KUNGA ko'rinmas qilardi (uning birorta `capture_runs` qatori bo'lmasdi, ya'ni jurnalda ham, yo'qlik yozuvida ham iz qolmasdi). Slot o'lchovida esa u bugungi mavjud slotlarni oladi (o'tib ketganlari `skipped` bo'lib tug'iladi va alert bermaydi), yangi VAQT esa ertagacha kutadi.
- **Verifikatsiya:** ikki yangi test (`test_a_slot_added_after_materialisation_waits_until_tomorrow` + nazorat bandi) va uchinchi sabotaj — muzlatishni olib tashlash AYNAN birinchisini qizartirdi, nazorat bandi YASHIL qoldi. Uchinchi o'lchov `test_editing_the_active_profile_never_reaches_todays_plan` da (ikki repozitoriy birga).
- **Committed in:** `0d8ac4f`

**2. [Rule 2 — yetishmayotgan kritik xulq] `defer()` `claim_due()` ning predikatisiz NO-OP bo'lardi**

- **Topildi:** Task 1, `defer` testini yozishda
- **Muammo:** `04-RESEARCH.md` §A.2 dagi `claim_due()` eskizida `locked_until` predikati **YO'Q** (u kechiktirish siyosati kiritilishidan oldin yozilgan). Eskizga aynan ergashilsa `defer()` `locked_until` ni qo'yardi, keyingi tik esa uni **darhol qayta olardi** — ya'ni T-04-35 mitigatsiyasi («`capture_stream_limit` da NVR ni bosmaymiz») **umuman mavjud bo'lmasdi** va NVR o'sha zahoti qaytadan bosilardi.
- **Yechim:** `claim_due()` ga `AND (locked_until IS NULL OR locked_until <= now())` qo'shildi va sabab SQL ning yonida yozildi, jumladan «§A.2 eskizida bu predikat YO'Q» degan fakt.
- **Verifikatsiya:** `test_defer_keeps_the_row_pending_and_delays_the_next_tick` kechikishni `locked_until` ustunini o'qish bilan emas, keyingi `claim_due()` ning qatorni **OLMAGANI** bilan o'lchaydi — ya'ni predikat olib tashlansa test qizaradi.
- **Committed in:** `b023e8d`

**3. [Rule 2] `defer()` ga kod darvozasi qo'shildi (rejada yo'q edi)**

- **Muammo:** rejaning imzosi `defer(run_id, seconds)`. Lekin `CAPTURE_DEFER_CODES` va `CAPTURE_AUTH_LOCKING_CODES` — ikki MUSTAQIL siyosat, va `defer()` ni istalgan kod bilan chaqirish mumkin bo'lsa `capture_bad_credentials` ni kechiktirib, T-04-34 ning butun himoyasini **bitta noto'g'ri chaqiruv bilan** chetlab o'tish mumkin bo'lardi.
- **Yechim:** ixtiyoriy `code` kalit argumenti; berilsa u reyestrda VA `CAPTURE_DEFER_CODES` da bo'lishi shart. Imzo kengaydi, mavjud kontrakt buzilmadi.
- **Verifikatsiya:** `test_defer_refuses_a_code_that_is_not_a_defer_code`.
- **Committed in:** `b023e8d`

**4. [Rule 2] `finish_failed()` reyestrga qarshi allowlist tekshiruvi**

- **Muammo:** metod xom `str` kod qabul qiladi. Reyestrda yo'q kod bazaga tushib ketsa API uni tanimay `errors.generic` qaytarardi va sabab FAQAT foydalanuvchi ekranida yo'qolardi (§S-5 aynan shu sinf). `CaptureError.__init__` allowlist'ni tekshiradi, lekin repozitoriy istisnodan emas, satrdan chaqiriladi.
- **Yechim:** `_require_known_code()` — `assert` EMAS, `ValueError` (`python -O` bilan `assert` o'chib ketardi va allowlist aynan ishlab chiqarishda jimgina yo'qolardi).
- **Committed in:** `b023e8d`

**5. [O'z-o'ziga zid mezon] Task 2 ning sabotaj bashorati noto'g'ri edi**

- **Qayerda:** «bo'lish qadamini olib tashlash «kesishuvchi davr tanilgan xato beradi» testini AYNAN qizartiradi (u endi `IntegrityError` ni ko'radi)»
- **O'lchandi:** repozitoriy `23P01` ni **o'zi** tanilgan xatoga aylantirgani uchun bo'lish qadami tushib qolganda ham `IntegrityError` emas, `ScheduleOverlapError` chiqadi — ya'ni o'sha test bashorat qilingandek qizara olmaydi.
- **Yechim:** mezonning NIYATI («ilova semantikasi va DB invarianti ALOHIDA o'lchansin») **kuchliroq shaklda** bajarildi: kesishuv testi ATAYIN bo'lishga umuman tayanmaydigan yo'ldan boradi — seed profili «bugun+30» ga ko'chiriladi, yangi davr esa BO'SHLIQDA boshlanadi (qisqartiriladigan profil yo'q) va keyingi profilning ustiga chiqadi. Natijada sabotaj **beshta split testini** qizartirdi va kesishuv testi **YASHIL** qoldi — bu rejaning da'vosidan kuchliroq: ikki qatlam haqiqatan mustaqil o'lchanadi.
- **Fayllar:** `tests/integration/test_schedule_repo.py`

**6. [Rule 3 — bloklovchi] `today_and_tomorrow()` argumentsiz, yozish metodlari argumentli**

- **Muammo:** rejaning imzosi `today_and_tomorrow()` — argumentsiz. Lekin `create_seasonal`/`update_slots`/`delete_future` ning D-05 darvozasi «bugun» ni bilishi shart, loyiha konventsiyasi esa uni ARGUMENT sifatida beradi (`tariff_repo.tariff_window(today)` — «bitta HTTP so'rovi ichidagi bir necha so'rov AYNAN bir xil biznes-kunga tayanishi kerak»).
- **Yechim:** ikkala shakl ham saqlandi va farq docstringda sabab bilan yozildi: **o'qish** yo'lida «bugun» SQL ichida `(now() AT TIME ZONE m.timezone)::date` dan chiqadi (atomiklik MUHIM — `today` va `tomorrow` bitta `now()` dan), **yozish** yo'lida esa argumentdan (so'rov bo'yicha qadalgan kun MUHIM).
- **Committed in:** `93b8678`

**7. [Rule 1 — bug] `SnapshotSchedule.__table__.update()` mypy'da yiqildi**

- **Muammo:** `"FromClause" has no attribute "update"` — `__table__` ning e'lon qilingan tipi `FromClause`.
- **Yechim:** `sqlalchemy.update(SnapshotSchedule)`.
- **Committed in:** `93b8678`

**8. [Rule 3 — bloklovchi] Worktree'da `.env` va `ops/seaweedfs/s3.json` yo'q edi**

- **Muammo:** ikkala fayl ham `.gitignore` da, ya'ni ular worktree'ga ko'chmaydi (04-03 da ham aynan shu bo'lgan). Usiz `docker compose` sirlarni bo'sh satr bilan almashtirardi.
- **Yechim:** `.env` asosiy repodan nusxalandi; `s3.json` `.example` dan yaratildi. `git check-ignore -v` ikkalasini ham tasdiqladi — repoga tushmaydi.
- **Committed in:** commit qilinmadi (ataylab — ikkalasi ham gitignore ostida)

---

**Total deviations:** 8 (3× Rule 2 yetishmayotgan kritik xulq, 1× Rule 1 bug, 2× Rule 3 bloklovchi, 1× o'z-o'ziga zid mezon, 1× imzo ziddiyati)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Ikkitasi (1, 2) **rejada umuman ko'rilmagan** mitigatsiya bo'shlig'ini yopdi va ikkalasi ham locked qarorning (D-05, T-04-35) jimgina ishlamasligiga olib borardi. Bittasi (5) rejaning bashorati noto'g'ri bo'lgan joyda o'lchovni reja matnidan ustun qo'ydi.

## Ochiq ziddiyat — `corrupt` kadrni `snapshots` ga YOZIB BO'LMAYDI

`record()` ni yozishda ikki rejaning **o'zaro zid** qarori topildi:

| Manba | Qaror |
|---|---|
| **04-03** (sxema) | `snapshots.quality_mean` va `quality_stddev` — `NOT NULL` |
| **04-04** (sof modul) | `analyze()` `corrupt` kadr uchun o'lchovlarni **`None`** qaytaradi. Nol qiymat ATAYIN rad etilgan: u «o'lchandi va nol chiqdi» ma'nosini berardi va D-15 ning `percentile_cont` bilan chegara chiqarish yo'lini buzardi |
| **04-UI-SPEC §6.4** | **C4 hujayrasi** = `succeeded` + `corrupt` — ya'ni bunday qator MAVJUD bo'lishi kutiladi |
| **04-04 xato reyestri** | `capture_invalid_response` = «Javob keldi, lekin ichida TASVIR YO'Q — `quality.py` uni `corrupt` dedi» — ya'ni taksonomiya bu holatni `failed` deb yopishni ko'zlaydi |

Uchinchi va to'rtinchi qator **bir vaqtda to'g'ri bo'la olmaydi.** Ikki yechim bor va ikkalasi ham shu rejadan tashqarida:

**(a)** `corrupt` kadr `snapshots` ga umuman yozilmaydi — u `finish_failed(capture_invalid_response)` bilan yopiladi. U holda **C4 hujayrasi hech qachon chizilmaydi**.
**(b)** Migratsiya uchala `quality_*` ustunini NULLABLE qiladi. U holda **`capture_invalid_response` kodi ishlatilmaydi**.

**Bu rejada nima qilindi:** `record()` `None` o'lchov kelganda `SnapshotMeasurementMissingError` ko'taradi va istisnoning docstringi ikkala yechimni ham nomlaydi. Sabab: nosozlik aks holda `NotNullViolation` bo'lib **worker ichida, birinchi buzuq kadrda** — ya'ni ehtimol ertalabki 06:00 slotida — chiqardi va xabar hech nimani tushuntirmasdi. Sentinel nol yozish esa 04-04 ning ochiq qaroriga zid.

**Egasi: `04-07`** — u ikkala yuzani (sifat filtri va kadr olish oqimi) ham ko'radigan birinchi reja.

## Qamrov chegarasi — ochiq yozilgan

**`snapshot_repo.py` bu rejada BIRORTA integratsiya testi bilan qoplanmagan** va bu rejaning **ATAYIN** qarori (`<action>`: «repozitoriyni yolg'iz o'lchash uchun yozilgan test kadr olish yo'lini takrorlagan bo'lardi va u yo'l bilan ajralib ketishi mumkin edi»). Uning DB xulqi `04-06` (`test_retention.py`) va `04-07` (`test_capture_tick.py`) da **haqiqiy oqim ustida** o'lchanadi.

Shu rejada qo'lga kiritilgani — **statik** kafolatlar: `mypy strict` (220 fayl), o'chirish metodining regex bilan yo'qligi, `storage_tier` predikatining mavjudligi, va `test_quality_enum_parity.py` (u `record()` yozadigan verdikt satrlari bazadagi `CHECK` dan o'tishini qulflaydi). **Xulq o'lchovi esa qarz bo'lib qoladi va uning egasi nomlangan.**

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `app/repositories/capture_repo.py` | To'rt majburiyatli docstring; `ensure_plan` (D-05 muzlatishi bilan), `claim_due` (CTE + `SKIP LOCKED`), ikki `release_expired` so'rovi, `mark_missed`, `finish_succeeded`/`finish_failed`/`defer`, `day_summary` (8 `FILTER`), `list_day`, `cameras_in_plan` | 1 063 |
| `app/repositories/schedule_repo.py` | Uch qarorli docskring; `today_and_tomorrow` (bitta `SELECT`, 7 CTE), `active_profile`, `slots_for`, `uncovered_days`, `create_seasonal` (bo'lish + nusxa tiklash), `update_slots`, `delete_future`; 4 xato sinfi | 853 |
| `app/repositories/snapshot_repo.py` | To'rt qoidali docstring; `record` (+`capture_runs` havolasi), `get`, `retention_candidates`, `mark_compressed`, `mark_purged`; `SnapshotMeasurementMissingError` | 435 |
| `tests/integration/test_capture_repo.py` | 26 test; parallel `SKIP LOCKED` uchun o'z engine'i (`pool_size=2`) + `statement_timeout` | 1 337 |
| `tests/integration/test_schedule_repo.py` | 17 test; SQL operatorlarini SANAYDIGAN «bitta so'rov» darvozasi; D-05 ning ikki-repozitoriyli o'lchovi | 812 |
| `tests/unit/test_quality_enum_parity.py` | 5 test; sof modul -> enum -> DB `CHECK` zanjiri | 134 |

## Bazaviy holat

| O'lchov | Baza (`04-03`+`04-04`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 654 | **1 702** | ✅ +48 |
| tenancy | 426 | **426** | ✅ o'zgarmagan |
| vitest | 246 | **246** | ✅ o'zgarmagan |
| node | 111 | **111** | ✅ o'zgarmagan |
| i18n | 577 × 3 | **577 × 3** | ✅ o'zgarmagan |
| `ruff` + `ruff format` + `mypy` | toza | **toza** (226 / 220 fayl) | ✅ |
| `npm run gate:fast` | — | **exit 0, 64 s** | ✅ |
| `git diff pyproject.toml package.json` | — | **o'zgarish yo'q** | ✅ (T-04-SC) |

## Issues Encountered

- **`test_the_server_enforces_the_slot_limit` birinchi yugurishda o'z arifmetikasida yiqildi** (3 soat × 4 = 12, chegara ham 12). To'g'irlandi (4 soat = 16) va nazorat asserti sabab bilan yozildi — chegaradan OSHIQ ekani endi testning o'zida tekshiriladi.
- **Frontend `node_modules` worktree'da yo'q edi** — `npm ci --prefix frontend` bilan o'rnatildi. `package.json` va `package-lock.json` **tegilmadi** (`git diff --exit-code` bilan tasdiqlandi).
- **`ruff format` uch marta o'z tuzatishini kiritdi** (uzun chaqiruvlarni bir qatorga yig'ish). Har safar `ruff check` + `mypy` qayta yugurtirildi.

## Doiradan tashqarida qolgan band (TEGILMADI)

`04-04` ning SUMMARY'si `tests/integration/test_live_view_e2e.py:102` va `test_real_nvr.py:109` izohlarining eskirganini (`/picture` endi 160 emas, 2 927 bayt beradi) qayd etib, egasini **`04-05`** deb belgilagan edi («u `/picture` ning birinchi haqiqiy iste'molchisi»).

**Bu rejada ham tuzatilmadi va sabab o'zgardi:** bu reja `/picture` ni **umuman iste'mol qilmaydi** — u repozitoriy qatlami va tarmoqqa chiqmaydi. `/picture` ning birinchi haqiqiy iste'molchisi — **`04-07`** (`frame_source`). Ikkala fayl ham bu rejaning `files_modified` idan tashqarida va parallel to'lqinda ularga tegish fayl to'qnashuvi xavfini tug'dirardi. **Egasi endi `04-07`.**

## Known Stubs

Yo'q. Uchala repozitoriy ham to'liq ishlaydi.

⚠ **Stub bo'lmagan, lekin ochiq qolgan uch band (uchalasining ham egasi bor):**

1. **`corrupt` kadr yozilmaydi** — yuqoridagi «Ochiq ziddiyat», egasi `04-07`. Tetik: `SnapshotMeasurementMissingError` chaqirilgan zahoti ko'rinadi.
2. **`snapshot_repo` ning xulq testlari** — yuqoridagi «Qamrov chegarasi», egalari `04-06` va `04-07`.
3. **`/picture` izohlari** — yuqoridagi band, egasi `04-07`.

## Threat Flags

Yangi tarmoq endpointi, auth yo'li yoki sxema o'zgarishi **YO'Q** — uchala modul ham DB qatlamida qoladi va migratsiyaga tegmaydi. Threat register'ning sakkizta mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-32 (tenant predikatisiz so'rov) | Har so'rovda `market_id` ikkinchi qatlam sifatida; `tests/tenancy` 426/426; uchala faylda ham cross-tenant testi |
| T-04-33 (bir slot ikki marta) | `FOR UPDATE SKIP LOCKED` + `UNIQUE`; parallel test kesishmani **bo'sh** deb talab qiladi va sabotaj bilan o'lchandi |
| T-04-34 (`bad_credentials` dan keyin retry) | `finish_failed` byudjetni to'liq yoqadi; **`claim_due()` uni qayta OLMAGANI** bilan isbotlanadi, `status` bilan emas |
| T-04-35 (`stream_limit` da darhol retry) | `defer()` + **`claim_due()` ning `locked_until` predikati** (2-deviatsiya — usiz mitigatsiya umuman yo'q edi) |
| T-04-36 (`snapshots` qatorining o'chirilishi) | O'chirish metodi umuman yozilmagan; regex darvozasi izohsiz matnda tekshiradi |
| T-04-37 (ikki marta siqish) | `retention_candidates` va `mark_compressed` da `storage_tier` **qat'iy predikat**; enum a'zolaridan hosila konstantalar |
| T-04-38 (soxta `missed` alertlari) | `ensure_plan` da `is_late` shoxi -> `skipped` + `capture_plan_created_late`; alohida test |
| T-04-39 (`error_detail` da sir) | `mask_sensitive()` ichma-ich obyektlarni ham qamraydi; kanareyka parol bilan o'lchandi |
| T-04-SC (paket o'rnatish) | Yangi paket YO'Q; `git diff --exit-code` toza |

⚠ **Yangi mitigatsiya (registerda yo'q edi):** `finish_failed()` va `defer()` ning reyestrga qarshi allowlist tekshiruvlari — noma'lum yoki noto'g'ri toifadagi `error_code` bazaga tusha olmaydi.

## Next Phase Readiness

**`04-06` (ombor) uchun:** `SnapshotRepository.retention_candidates()` / `mark_compressed()` / `mark_purged()` tayyor; `RetentionCandidate` `object_key` va `size_bytes` ni beradi. `COMPRESSIBLE_TIER` va `PURGEABLE_TIERS` — enum'dan hosila konstantalar, literal yozilmaydi. ⚠ `test_retention.py` `snapshot_repo` ning **birinchi xulq darvozasi** bo'ladi.

**`04-07` (tik/scheduler) uchun:** `capture_repo` ning butun yuzasi tayyor va tik tartibida joylashgan (`ensure_plan` -> `release_expired` -> `mark_missed` -> `claim_due` -> `finish_*`). ⚠ **Uch band aynan shu rejaga qoldi:** (a) `corrupt` kadr qarori, (b) `claim_due()` natijasini tranzaksiyadan KEYIN navbatga qo'yish (`04-PATTERNS.md` §3.3 — repozitoriy shuning uchun ORM obyekti emas, frozen dataclass qaytaradi), (c) `/picture` izohlari.

**`04-08` (alert) uchun:** `mark_missed()` `list[MissedSlot]` qaytaradi — bu D-20 ning yagona manbai. `day_summary()` kunlik dayjest uchun oltala hisoblagichni nol bilan birga beradi.

**`04-09`/`04-10` (API/UI) uchun:** `ScheduleView` `04-UI-SPEC.md` §4.3 ning `[TALAB]` shakli bilan **aynan** mos (`profile{id,name,starts_on,ends_on,mode}`, `today`, `tomorrow`, `differs`, `capture_on_closed_days`, `uncovered_days`, `uncovered_horizon_days`). To'rt xato sinfi va ularning HTTP kodlari modul docstringida kontrakt sifatida yozilgan. `list_day()` `RunRow` da `is_archived` bayrog'ini beradi — filtrlash qarori UI qatlamida.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan oltala fayl diskda tekshirildi** (`MISSING: 0`).
- **Beshala commit `git log` da tasdiqlandi:** `9876ff7`, `b023e8d`, `0d8ac4f`, `93b8678`, `79b48ac` — bazasi `6db3d51`.
- **Reja artefakt shartlari o'lchandi:** `capture_repo.py` 1 063 qator (talab ≥ 250) va `FOR UPDATE SKIP LOCKED` + `bindparam` + `FILTER` ni o'z ichiga oladi; `schedule_repo.py` da `uncovered` va `generate_series` bor, xom diapazon konstruktori **yo'q**; `snapshot_repo.py` da `storage_tier` va `object_deleted_at` bor, o'chirish metodi **yo'q**.
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin orkestrator tomonidan yangilanadi.
- **Ishchi daraxt toza:** `git status --short` bo'sh; `.env` va `ops/seaweedfs/s3.json` gitignore ostida qoldi.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-04*
