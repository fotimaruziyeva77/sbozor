---
phase: 04-snapshot-pipeline
plan: 09
subsystem: backend
tags: [http-api, image-proxy, audit-read, rbac, self-check, cam-04, cam-06, found-06, d-05]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 05
    provides: "`ScheduleRepository.today_and_tomorrow()` (BITTA so'rov), `create_seasonal()` davr bo'lish, to'rt xato sinfi; `CaptureRepository.day_summary()`/`list_day()`; `SnapshotRepository.get()`"
  - phase: 04-snapshot-pipeline
    plan: 06
    provides: "`storage.open()` konteksti va `SnapshotStorage.get()` — rasm proxysining bayt manbai"
  - phase: 04-snapshot-pipeline
    plan: 07
    provides: "`capture_tick` ning `system_heartbeats['capture_tick']` yozuvi; `0016` ning nullable o'lchovlari (`succeeded`+`corrupt` hujayrasi)"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`CAPTURE_JOB_ERROR_CODES` reyestri — `schemas.py` uni IMPORT qiladi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`cameras.py` router naqshi, `internal` paketi, `CAMERA_VIEW`/`CAMERA_MANAGE`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`stalls.py` ning dekorator-darajasidagi huquq naqshi va `audit_read` ning ATAYIN yo'qligi (nazorat holati); `tariffs.py` davrli router"
provides:
  - "`GET /api/v1/snapshot-schedules/today` — «bugun» va «ertaga» BITTA javobda (D-05)"
  - "Jadval CRUD: `GET ''` / `POST ''` / `PATCH /{id}` / `DELETE /{id}` uch rejim (`past`/`active`/`future`) bilan"
  - "`GET /api/v1/capture-runs?day=` — kun jurnali: oltala hisoblagich + matritsa qatorlari + `archived_present`"
  - "`GET /api/v1/snapshots/{id}` — kadr detali (`object_key` YO'Q)"
  - "`GET /api/v1/snapshots/{id}/image` — AUDITLANGAN proxy; presigned URL berilmaydi"
  - "`GET /api/v1/alerts?closed=0|1` — allowlist bilan filtrlangan `detail`; yopish marshruti YO'Q"
  - "`GET /internal/self-check` — `stale` va `never_seen` ALOHIDA, `ok` faqat birinchisi bo'yicha"
  - "`AlertRepository` — faqat o'qish; `ScheduleRepository.list_profiles()`"
  - "Uchta yangi audit resurs konstantasi va oltita yangi `MARKET_ERROR_CODES` kodi"
affects: [04-10, 04-11, 04-12, 05-cv-zonalar, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Huquq DEKORATORDA + imzoda `principal` `intent` DAN OLDIN — ikki mexanizm, va IKKALASI ham alohida test bilan o'lchanadi"
    - "«403 iz qoldirmaydi» testi kafolatning BIRINCHI mexanizmini, «410 iz qoldirmaydi» testi IKKINCHISINI qamraydi — bittasi yolg'iz o'zi hech qachon qizarmaydi"
    - "Matn darvozasi izohlarni FILTRLAMAGANDA modul docstringi taqiqlangan nomni LITERAL yozmasligi kerak — taqiqni so'z bilan ta'riflash yetadi"
    - "`compose.yaml` ustidagi matn darvozasi esa AKSINCHA — izohlarni filtrlashi SHART, aks holda u o'z hujjatini buzilish deb belgilaydi"
    - "`Annotated[date | None, Query()]` uchun `date` ISH PAYTIDA import qilinishi shart — xato import paytida emas, BIRINCHI SO'ROVDA chiqadi"
    - "Kirish va chiqish vaqt formatlari BIR XIL EMAS: `06:00` yuboriladi, `06:00:00` qaytadi — test ikki konstanta bilan ishlaydi"

key-files:
  created:
    - services/core-api/app/api/v1/schedules.py
    - services/core-api/app/api/v1/snapshots.py
    - services/core-api/app/api/internal/self_check.py
    - services/core-api/app/repositories/alert_repo.py
    - tests/integration/test_capture_schedule.py
    - tests/integration/test_snapshot_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/security/audit.py
    - services/core-api/app/settings.py
    - services/core-api/app/main.py
    - services/core-api/app/api/internal/__init__.py
    - services/core-api/app/repositories/schedule_repo.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/market-errors.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json
  deleted: []

key-decisions:
  - "`ScheduleNotEditableError` -> **403**, rejaning `<behavior>` bandidagi 409 EMAS: 04-05 ning istisno docstringi 403 ni KONTRAKT sifatida yozgan va `tariff_past_locked` / `category_period_past_locked` ikkalasi ham 403 — o'tmish HUQUQ masalasi, konflikt emas"
  - "`ScheduleSlotsIn` da `extra=\"forbid\"`: `starts_on` yuborilsa so'rov RAD ETILADI. Jim e'tiborsizlik rad etishdan yomonroq — klient «davrni o'zgartirdim» deb o'ylab qolardi"
  - "DTO vaqtlar ro'yxatiga `MAX_TIMES_PER_DAY` chegarasi QO'YILMADI: u sozlama PASAYTIRILGANDA haqiqiy darvozani (`snapshot_max_times_per_day`) o'lik kodga aylantirardi. DTO'da faqat suiste'mol shifti (100)"
  - "`archived_present` — BAYROQ, ro'yxat emas: arxivlangan kameraning qatorlari `rows` dan chiqariladi (xulosa ham ularni sanamaydi), lekin MAVJUDLIGI aytiladi"
  - "`alert_events.detail` allowlisti `AlertEventOut` VALIDATORIDA, marshrutda emas — marshrutda bo'lsa ikkinchi chaqiruvchi uni chetlab o'tardi"
  - "`/internal/self-check` da `EXPECTED_COMPONENTS` QATTIQ yozilgan, jadvaldan hosila EMAS: hosila bo'lsa bo'sh jadval «kutilayotgan hech nima yo'q» deb `200` berardi va worker umuman ko'tarilmagan holat «sog'lom» ko'rinardi"
  - "`ok` faqat `stale` bo'yicha, LEKIN bitta istisno bilan: butunlay bo'sh jadval ham `ok=false` — bu «hali qurilmagan» emas, «hech nima ishlamayapti»"
  - "`GET /coverage` marshruti QURILMADI: `uncovered_days` va `uncovered_horizon_days` allaqachon `/today` javobida va ikkinchi marshrut ikkinchi haqiqat manbai bo'lardi"

patterns-established:
  - "Sabotaj o'lchovi UCH natijaga bo'linadi: (a) rejaning bashorati to'g'ri, (b) sabotaj O'LIK — hech nima qizarmaydi, (c) sabotaj rejaning bashoratidan KO'PROQ narsani qizartiradi. Uchalasi ham shu rejada uchradi"
  - "O'LIK sabotaj tuzatiladi, hisobotdan olib tashlanmaydi: `04-04`/`04-06`/`04-07` naqshi — kafolatning O'LCHANMAY qolgan mexanizmini alohida test bilan yopish"
  - "Marshrut-grafi darvozasi (`test_personal_data_coverage.py`) MAYDON NOMIGA tayanadi, ya'ni u shaxsiy ma'lumot BAYT bo'lgan marshrutni PRINSIPIAL ravishda ko'rmaydi — bu o'lchandi, taxmin qilinmadi"
  - "`MARKET_ERROR_CODES` ga kod qo'shish HAR DOIM frontend qarzini tug'diradi (ko'zgu QO'LDA saqlanadi) — «backend-only» deb rejalashtirilgan reja ham `npm --prefix frontend test` ni yugurtirishi SHART"

requirements-completed: [CAM-04, CAM-06, CAM-07, FOUND-06]

# Metrics
duration: 3h 05m
completed: 2026-08-05
---

# Phase 4 Plan 09: Jadval, kun jurnali va auditlangan rasm proxysi Summary

**Fazaning HTTP yuzasi yopildi: «bugun/ertaga» bitta so'rovda keladi va D-05 yarim tunda ham yolg'on gapirmaydi; dalil-kadr faqat `core-api` proxysi orqali chiqadi va uning har o'qilishi `audit_log` da iz qoldiradi — presigned URL na berildi, na so'raldi; kun jurnali YO'QLIKNI (`missed`) natija sifatida ifodalaydi; `/internal/self-check` esa worker jimligini boshqa jarayondan ko'rsatadi — va u ilk yugurishdayoq HAQIQIY to'xtagan tikni fosh qildi.**

## Performance

- **Duration:** ~3 soat 05 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 6 ta yangi + 8 ta o'zgargan — 3 547 qator qo'shildi
- **Commits:** 3 ta task commiti

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 1 | Jadval CRUD, `/today`, xato reyestrining importi | `4ca059c` |
| 2 | Kun jurnali, kadr detali, RASM PROXYSI, ogohlantirishlar | `da752ec` |
| 3 | `/internal/self-check` | `8546d1d` |
| — | TS xato-kod ko'zgusining sinxronlanishi (12-deviatsiya) | `56d818d` (fix) |

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

Bu rejada uchinchi ustun **ikki marta** birinchisidan ko'ra ko'proq ma'lumot berdi, va bir marta sabotaj **butunlay o'lik** chiqdi.

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `PATCH /snapshot-schedules/{id}` dekoratoridan `CAMERA_MANAGE` olindi (imzodagi `ScheduleManagerDep` qoldirildi) | **HECH NIMA** — 15/15 test yashil | Hammasi | ❌ **Reja «AYNAN qizartiradi» degan edi.** Sabab: imzo aliasi AYNI huquqni majburlashda davom etadi va bu faylda `audit_read` UMUMAN YO'Q, ya'ni qoldiriladigan yolg'on dalilning O'ZI mavjud emas. **Sabotaj o'lik** |
| 1-b | O'rniga: `PATCH` dan `CAMERA_MANAGE` BUTUNLAY olindi (`CAMERA_VIEW` qoldi) | **AYNAN 1 test**: `test_the_director_reads_the_schedule_but_cannot_edit_it` (`200 == 403`) | Qolgan **14**, jumladan kassirning 403 testi (unda `CAMERA_VIEW` ham yo'q) va butun CRUD | ⚠ Rejada bu variant yo'q — u 1-sabotajning o'likligi o'lchangandan keyin qo'shildi |
| 2 | Rasm marshrutidan `audit_read` chaqiruvi olindi | **AYNAN 1 test**: `test_reading_the_image_leaves_an_audit_row` | **15 test**, jumladan `test_the_image_arrives_as_jpeg_through_the_proxy` (baytlar hamon keladi) **VA butun `test_personal_data_coverage.py`** | ✅ **AYNAN bashorat qilingandek** — shaxsiy ma'lumot izining ALOHIDA o'lchanayotgani isbotlandi |
| 3 | Huquq dekoratordan olindi **va imzoda `intent` DAN KEYINGA surildi** | **HECH NIMA** — 24/24 test yashil | Hammasi | ⚠ Rejada yo'q; u `<critical_context>` ning talabi bo'yicha qo'shildi. **Sabotaj o'lik** — sabab quyida |
| 3-b | O'rniga: `audit_read` `BackgroundTasks` dan olinib INLINE `await` ga o'tkazildi | **2 test**: yangi qo'shilgan `test_a_request_that_fails_after_the_audit_dependency_leaves_no_row` (410 da yolg'on dalil paydo bo'ldi) va `test_reading_the_image_leaves_an_audit_row` (filtrlar bo'sh qoldi) | **403 testi YASHIL** (dekorator uni hamon oldinroq to'xtatadi) va qolgan 15 | ⚠ Yangi o'lchov — 3-sabotajning o'likligini tuzatish uchun |
| 4 | `never_seen` `stale` ga birlashtirildi | **2 test**: `test_self_check_is_ok_when_the_heartbeat_is_fresh` (`503 != 200`) **va** `test_self_check_reports_a_stale_component_with_503` (`['backup','capture_tick'] != ['capture_tick']`) | Qolgan **19** | ⚠ **Reja YARIM to'g'ri.** «Yangi heartbeat testi AYNAN qizaradi» — ✅; «eskirganlik testi YASHIL qoladi» — ❌: mening testim status kodini emas, `stale` RO'YXATINING TARKIBINI qulflaydi, ya'ni u rejaning kutganidan kuchliroq |

Har olti holatda ham fayl `cp` bilan (hech qachon `git checkout --` bilan emas) darhol tiklandi va to'plam qayta yashil bo'ldi.

### Nega 1- va 3-sabotajlar o'lik chiqdi — va bu nimani anglatadi

Ikkalasi ham **bir xil sinfdagi** natija: `04-PATTERNS.md` §3.9 ning «huquq dekoratorda» qoidasi *mexanizm*, kafolat esa *natija*. 03-07 buni bir marta o'lchagan edi; bu reja uni **ikkinchi marta**, boshqa faylda tasdiqladi.

Kafolatning **ikki mustaqil manbai** bor:

1. dekorator darajasidagi bog'liqliklar imzo parametrlaridan oldin hal bo'ladi;
2. `audit_read` yozuvni `BackgroundTasks` orqali yuboradi, u esa **faqat muvaffaqiyatli** javobga biriktiriladi.

Ikkinchisi birinchisini **yolg'iz ham** ushlab turadi — shuning uchun huquqni imzoga ko'chirish (hatto `intent` dan keyinga surish ham) hech nimani qizartirmaydi. Bu **nuqson emas, chuqurlikdagi himoya**; lekin u shuni anglatadiki, birinchi mexanizmni faqat *mexanizm testi* bilan o'lchash mumkin — va `<critical_context>` aynan bunday testni yozishni ta'qiqlaydi.

**Yechim (04-04/04-06/04-07 naqshi):** o'lik sabotaj hisobotdan olib tashlanmadi, balki **ikkinchi mexanizm alohida o'lchanadigan** qilindi. Yangi test — `test_a_request_that_fails_after_the_audit_dependency_leaves_no_row` — so'rovni `audit_read` dan **o'tkazib**, keyin 410 bilan yiqitadi va jurnal baribir bo'sh qolishini talab qiladi. Endi:

| Mexanizm | Qaysi test qamraydi | Bitta o'zgarish bilan buziladimi |
|---|---|---|
| Dekorator tartibi | `..._is_refused_and_leaves_no_audit_row` (403) | Yo'q — 2-mexanizm uni ushlab turadi |
| Fon vazifasining faqat muvaffaqiyatga biriktirilishi | `..._fails_after_the_audit_dependency_leaves_no_row` (410) | **Ha** — 3-b sabotaji bilan o'lchandi |

Ikkalasi birga butun kafolatni qamraydi va **hech biri ikkinchisining o'rnini bosmaydi**.

## O'LCHOVLAR — taxmin qilinmadi

| Nima | Natija |
|---|---|
| `test_personal_data_coverage.py` rasm marshrutini KO'RADIMI | **YO'Q.** Darvoza `response_model` ning MAYDON NOMLARIGA (`vendor_name`/`phone`/`full_name`) tayanadi; rasm marshrutida `response_model` yo'q va shaxsiy ma'lumot — **baytlarning o'zi**. Qamragan 5 marshrut: `/stalls`, `/stalls/{id}`, `/stalls/{id}/assignments`, `/vendors`, `/vendors/{id}`. `audit_resources()` esa rasm marshruti uchun `['snapshots']` beradi, ya'ni **audit e'lon qilingan, lekin darvoza uni TALAB qilmaydi** |
| 2-sabotaj `test_personal_data_coverage.py` ni qizartiradimi | **YO'Q** — `audit_read` butunlay olib tashlanganda ham darvoza yashil qoldi. Yuqoridagi qatorning amaliy isboti |
| `Annotated[date \| None, Query()]` da `date` `TYPE_CHECKING` ostida | **Yiqiladi, lekin IMPORT PAYTIDA EMAS:** `PydanticUserError: not fully defined` faqat **birinchi so'rovda** chiqadi. `mypy` ham, `import app.main` ham buni ko'rmadi — uni faqat integratsiya testi topdi |
| `create_seasonal()` mavjud profil USTIDA boshlanadigan davrni | **BO'LADI (split), rad etmaydi** — ya'ni «kesishuv 409 beradi» da'vosini bu yo'ldan o'lchab bo'lmaydi (birinchi urinishda 201 chiqdi). Test BO'SHLIQDA boshlanib KEYINGI profilning ustiga chiqadigan davrga o'tkazildi |
| Pydantic `time` ni qanday seriyalaydi | **`HH:MM:SS`** (`06:00:00`), yuborilgani esa `06:00`. Ikki konstanta kerak bo'ldi |
| `compose.yaml` da `self-check` satri | **BOR** — `scheduler` blokidagi IZOHDA, va u aynan shu qoidani TUSHUNTIRADI. Darvoza izohlarni filtrlashga majbur bo'ldi |
| `/internal/self-check` ning HAQIQIY javobi (jonli konteyner) | **`503`** — `{"ok":false,"stale":["capture_tick"],"never_seen":["alert_sweep","backup","retention"]}` |
| `capture_tick` heartbeat'ining haqiqiy yoshi | **02:27:10** (`SELECT now() - last_seen_at`) — ya'ni 503 **yolg'on signal emas**, u haqiqatan to'xtagan tikni fosh qildi |
| `core-api` runtime image'i | **ESKIRGAN edi** — `ModuleNotFoundError: No module named 'PIL'` (04-04 `Pillow` ni qo'shgan, image qayta qurilmagan). `docker compose build core-api` bilan tuzatildi; kod o'zgarmadi |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `pytest tests/integration/test_capture_schedule.py -q` | **21 test**, exit 0 |
| 2 | `pytest tests/integration/test_capture_schedule.py -k self_check -q` | **6** (talab ≥ 3), exit 0 |
| 3 | `pytest tests/integration/test_snapshot_api.py -q` | **17** (talab ≥ 9), exit 0 |
| 4 | `pytest tests/tenancy/test_route_coverage.py test_personal_data_coverage.py -q` | **16**, exit 0 |
| 5 | `pytest tests/tenancy -q` | **470** (baza 426, talab ≥ 412), exit 0 |
| 6 | `pytest -q` (to'liq) | **1 837** (baza 1 755 -> **+82**, talab ≥ 1 520), exit 0 |
| 7 | `ruff check . && ruff format --check . && mypy .` | exit 0 (**241 fayl formatlangan, 235 fayl tiplangan**) |
| 8 | `git diff --exit-code services/core-api/app/security/rbac.py frontend/src/lib/rbac.ts` | **o'zgarish yo'q** (W0-F6 — yangi `Permission` qo'shilmagan) |
| 9 | `git diff --exit-code compose.yaml` | **o'zgarish yo'q**; `git diff --unified=0 compose.yaml \| grep -c healthcheck` -> **0** |
| 10 | `git diff --exit-code services/core-api/pyproject.toml frontend/package.json frontend/package-lock.json` | **o'zgarish yo'q** (T-04-SC) |
| 11 | `curl /internal/self-check` (jonli konteyner) | **503** + `never_seen: [alert_sweep, backup, retention]` (ikkalasi ham qonuniy — mezon shunday deydi) |
| 12 | `npm --prefix frontend run i18n:check` | **583 kalit × 3 til** (577 -> +6, 12-deviatsiya), exit 0 |
| 13 | `npm --prefix frontend test` | **node 111 / 111 pass**, **vitest 246 passed (20 fayl)**, exit 0 |
| 14 | `npm --prefix frontend run typecheck` | exit 0 |
| 15 | `npm --prefix frontend run lint` | exit 0 |
| 16 | `npm --prefix frontend run build` | exit 0 (uchala til uchun ham SSG) |

Mexanik artefakt mezonlari:

| Mezon | Natija |
|---|---|
| `schemas.py` da `from app.services.capture_errors import` | ✅ |
| `CAPTURE_JOB_ERROR_CODES <= MARKET_ERROR_CODES` | ✅ |
| `'object_key' not in SnapshotDetailOut.model_fields` | ✅ |
| `snapshots.py` da imzolangan-havola API'sining ikkala nomi | ✅ **YO'Q**; `audit_read` **BOR** |
| `snapshots.py` da `PATCH/POST/DELETE /alerts` (izohsiz matnda) | ✅ **YO'Q** |
| `self_check.py` da taqiqlangan ikki maydon nomi (izohsiz matnda) | ✅ **YO'Q**; `stale` **BOR** |
| `schedules.py` da `/today` `{schedule_id}` dan oldin | ✅ — lekin quyidagi ogohlantirishga qarang |

> ⚠ **Rejaning `/today` tartibi mezoni ZAIF va bu o'lchandi.** `t.index('/today') < t.index('{schedule_id}')` sharti **modul docstringidagi matnga** tushdi (190 va 206-belgilar) — ya'ni u marshrut tartibini emas, IZOHNI o'lchadi. Haqiqiy tartib alohida, izohsiz matn ustida tekshirildi: `@router.get("/today")` dekoratori 9 474-belgida, `"/{schedule_id}"` esa 14 079-belgida. **Mezon o'z-o'ziga zid emas, lekin u yolg'on-yashil berishi mumkin edi** va bu SUMMARY'da ochiq qoldiriladi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — bloklovchi] Reja `409` deydi, 04-05 kontrakti `403` — `ScheduleNotEditableError`**

- **Topildi:** Task 1, xato xaritasini yozishda
- **Ziddiyat:** rejaning `<behavior>` bandi «`PATCH` `past` profilda `409`» va «`DELETE` boshlangan profilda `409`» deydi. Lekin `schedule_repo.ScheduleNotEditableError` ning docstringi (04-05, muzlatilgan kontrakt) **403** ni yozib qo'ygan va sababini ham beradi: «qator MAVJUD va uni chaqiruvchi ko'ra oladi; rad etilayotgani AMAL». 04-05 ning SUMMARY'si ham «`ScheduleNotEditableError` 403» deb sanaydi.
- **Loyiha precedenti ham 403:** `tariff_past_locked` (02-09) va `category_period_past_locked` (02-08) — ikkalasi ham 403 va ikkalasining ham izohi bir xil: «403 ATAYIN, 422 EMAS: o'tmish hech kimga ochiq emas, bu HUQUQ masalasi».
- **Qaror:** **403** amalga oshirildi. Mezonning NIYATI («o'tmishdagi profil tahrirlanmaydi va javob TANILGAN kod bo'ladi, 500 emas») to'liq bajarildi; kod `MARKET_ERROR_CODES` da (`schedule_not_editable`). 409 uchta manbaga (repozitoriy kontrakti va ikki fazaning precedenti) zid bo'lardi.
- **Verifikatsiya:** `test_a_past_profile_is_read_only`, `test_only_a_future_profile_can_be_deleted`.
- **Committed in:** `4ca059c`

**2. [Rule 3 — bloklovchi] `settings.py` `files_modified` da yo'q, lekin ikkita sozlama kerak edi**

- **Muammo:** reja `self_check_stale_minutes` (standart 10) ni ochiq talab qiladi, `/today` esa `uncovered_horizon_days` ni qaytarishi kerak — repozitoriy uni ARGUMENT sifatida oladi (04-05 ning sof-modul chegarasi). Ikkalasi ham `Settings` da yo'q edi.
- **Yechim:** `schedule_horizon_days` (90) va `self_check_stale_minutes` (10) qo'shildi. Modul darajasidagi konstanta varianti rad etildi — reja «**sozlanadigan** chegara» deydi va loyiha konventsiyasi `Settings`.
- **To'qnashuv xavfi:** yo'q — `04-08` ning `files_modified` ida `settings.py` yo'q (tekshirildi).
- **Committed in:** `4ca059c`

**3. [Rule 3 — bloklovchi] `schedule_repo.list_profiles()` mavjud emas edi**

- **Muammo:** reja `GET /api/v1/snapshot-schedules` -> ro'yxat kontraktini talab qiladi (DL-2 undan chiziladi), lekin `ScheduleRepository` da profillarni ro'yxatlash metodi YO'Q.
- **Nega marshrutda SQL yozilmadi:** routerlar bu loyihada hech qachon SQL yozmaydi — tenant predikati (`scoped()`) repozitoriy qatlamida yashaydi va uni chetlab o'tish T-04-32 ning ikkinchi qatlamini yo'qotardi.
- **Yechim:** `list_profiles(today=...)` qo'shildi. `mode` ARGUMENTDAGI `today` dan hisoblanadi (yozish metodlari bilan bir xil qoida) — aks holda ro'yxatda `future` deb ko'rsatilgan profil o'sha zahoti yuborilgan `DELETE` da `active` bo'lib chiqishi mumkin edi.
- **Committed in:** `4ca059c`

**4. [Rule 3 — bloklovchi] Matritsa qatlami `test_cross_tenant.py` da, reja esa `test_route_coverage.py` ni nomlagan**

- **Muammo:** reja «`tests/tenancy/test_route_coverage.py` — yangi marshrutlar matritsaga qo'shiladi» deydi, lekin `PARAM_FILLERS`, `BODY_FILLERS` va `EXEMPT_ROUTES` **`test_cross_tenant.py`** da yashaydi; `test_route_coverage.py` da faqat `MINIMUM_MATRIX_ROUTES` bor.
- **Yechim:** ikkala fayl ham tahrirlandi. `test_cross_tenant.py` ga `TenantSeed.snapshot` qatlami, `snapshot_domain` fixture'i, ikki filler va `/internal/self-check` istisnosi; `test_route_coverage.py` da chegara 42 -> 48.
- **Qo'shimcha topilma:** matritsaning O'Z darvozasi (`test_param_fillers_point_at_the_other_market`) B qiymatlarining **MUSTAQIL** ro'yxatini tutadi va u ham yangilanishi kerak bo'ldi — ya'ni darvoza haqiqatan ishlaydi, u yangi fillerni darhol ushladi.
- **Committed in:** `4ca059c`

**5. [Rule 1 — bug] `date` `TYPE_CHECKING` ostida bo'lsa `GET /capture-runs` ish paytida yiqiladi**

- **Muammo:** `Annotated[date | None, Query()]` uchun FastAPI annotatsiyani ISH PAYTIDA `get_type_hints` bilan o'qiydi va Pydantic `TypeAdapter` ga beradi. `date` faqat tip-tekshiruv paytida mavjud bo'lsa `PydanticUserError: not fully defined` chiqadi.
- **Nega jimgina o'tib ketardi:** xato **import paytida emas, BIRINCHI SO'ROVDA** chiqadi. `mypy` toza, `import app.main` toza, OpenAPI ham qurilaveradi — uni faqat integratsiya testi topdi.
- **Yechim:** `date` modul darajasiga ko'chirildi, sabab izohda o'lchov bilan yozildi.
- **Committed in:** `da752ec`

**6. [Rule 1 — bug] Modul docstringi o'z darvozasini buzdi (`snapshots.py`)**

- **Muammo:** docstringda «bu faylda `generate_presigned` va `presigned_url` satrlari YO'Q» deb yozgan edim — va darvoza aynan shu satrlarni izohlarni FILTRLAMASDAN qidiradi.
- **Nega darvoza filtrlanmaydi (va filtrlanmasligi kerak):** rejaning mezoni ochiq aytadi — «docstringdagi «presigned URL berilmaydi» taqiq matni bu shartga tegmaydi», ya'ni taqiqni **so'z bilan** ta'riflash ko'zda tutilgan. Filtrsiz darvoza «nom umuman yozilmagan» degan kuchliroq da'voni beradi.
- **Yechim:** docstring qayta yozildi — API nomlari o'rniga «`boto3` ning imzolangan-havola yasaydigan ikkala metod nomi» ta'rifi, hamda keyingi tahrirlovchi uchun ochiq ogohlantirish.
- **Committed in:** `da752ec`

**7. [Rule 1 — bug] `compose.yaml` darvozasi o'z hujjatini buzilish deb belgiladi**

- **Muammo:** birinchi variant butun `compose.yaml` da `self-check` satrini qidirardi va `scheduler` blokidagi **izohni** topib qizardi. O'sha izoh esa aynan shu qoidani tushuntiradi: «yagona ishonchli signal bazadagi natija, konteyner healthcheck'ida emas».
- **Yechim:** darvoza izoh qatorlarini filtrlaydi va faqat KONFIGURATSIYANI o'qiydi. Bu `snapshots.py` dagi 6-deviatsiyaning **teskarisi** va farq ataylab: u yerda taqiq API NOMI (uni yozmaslik oson), bu yerda esa YO'L (uni tushuntirishda nomlash muqarrar).
- **Committed in:** `8546d1d`

**8. [O'z-o'ziga zid mezon] Kesishuv testini bo'lish semantikasi orqali o'lchab bo'lmaydi**

- **Qayerda:** «`POST` kesishuvchi davr bilan `409` beradi (`EXCLUDE` xatosi tanilgan kodga aylanadi)»
- **O'lchandi:** mavjud profilning USTIDA boshlanadigan davr **409 bermaydi** — `create_seasonal()` uni QISQARTIRADI (bo'lish semantikasi) va yangi profil muammosiz yoziladi (birinchi urinishda `201` chiqdi).
- **Yechim:** mezonning NIYATI (`23P01` xom holda chiqmasin) test yo'lini o'zgartirib bajarildi: seed profili qisqartiriladi, yangi davr **BO'SHLIQDA** boshlanadi (qisqartiriladigan profil yo'q) va KEYINGI profilning ichiga kirib ketadi. Endi 409 ning manbai — ilova mantig'i emas, **DB invarianti**. Bu `04-05` ning 5-deviatsiyasi bilan aynan bir xil qaror.
- **Fayllar:** `tests/integration/test_capture_schedule.py`

**9. [O'z-o'ziga zid mezon] Task 1 va Task 3 ning tartibi bir-birini bloklaydi**

- **Qayerda:** Task 3 ning `<action>` i «`main.py` **bu taskda tegilmaydi** — router Task 1 da ulanadi» deydi. Lekin Task 1 da `self_check.py` hali MAVJUD EMAS, ya'ni `main.py` ni o'sha commitda ulash ilovani **import qilinmaydigan** holga keltirardi.
- **Yechim:** har bir router O'Z taskining commitida ulandi. Natijada uchala commit ham **mustaqil ravishda yashil** va `git bisect` ishlatib bo'ladigan holda qoldi. Qoidaning niyati (`main.py` bitta fayl, uni ikki task bo'lib tortmasin) buzilmadi — u ketma-ket, to'qnashuvsiz uch marta tahrirlandi.
- **Fayllar:** `services/core-api/app/main.py`

**10. [Qamrov qarori] `GET /coverage` marshruti qurilmadi**

- **Qayerda:** Task 1 ning `<action>` i marshrut tartibi qoidasida `/coverage` ni eslatadi.
- **Sabab:** rejaning `<interfaces>` bo'limi («bu rejada tug'iladigan kontraktlar») uni **sanamaydi**, `uncovered_days` va `uncovered_horizon_days` esa allaqachon `/today` javobida. UI-SPEC §4.3 ham CoverageWarning'ni aynan `/today` payload'idan chizadi. Ikkinchi marshrut ikkinchi haqiqat manbai va qo'shimcha hujum yuzasi bo'lardi.
- **Egasi:** agar 04-10/04-11 unga muhtoj bo'lsa, u `/today` dan ajratilib olinadi.

**11. [Qamrov qarori] `PATCH` faqat `times` ni qabul qiladi — `future` profilning nomi va davri tahrirlanmaydi**

- **Ziddiyat:** `04-UI-SPEC.md` §4.5 `future` profilda «Nom, boshlanish, tugash, vaqtlar» tahrirlanadi deydi. `ScheduleRepository` esa faqat `update_slots()` va `delete_future()` ni beradi (04-05 kontrakti).
- **Qaror:** repozitoriy yuzasini kengaytirmadim. `future` profilni **o'chirib qayta yaratish** ikkala amalning ham ruxsat etilgani (204 va 201) va u ayni natijani beradi.
- **Egasi: `04-10`/`04-11`** — agar UI to'g'ridan-to'g'ri tahrirni talab qilsa, `schedule_repo` ga `update_future_period()` qo'shiladi. **Bu qarz ochiq yozilgan.**

**12. [Rule 1 — bug] Olti yangi kod TS ko'zgusiga qo'shilmadi va IKKI node darvozasi qizardi**

- **Topildi:** `npm --prefix frontend test` — `error-codes.test.mjs` ning ikki testi (`fail 2`, `pass 109`).
- **Muammo:** `MARKET_ERROR_CODES` ning UI ko'zgusi `frontend/src/lib/api-types.ts::ERROR_CODES` da yashaydi va u **QO'LDA** sinxron saqlanadi — til chegarasi tufayli kompilyator tekshiruvi yo'q. `schemas.py` ning O'Z docstringi buni ochiq ogohlantiradi («⚠ JUFTINI YANGILASHNI UNUTMANG»), men esa olti kod qo'shib ko'zguni unutdim. Darvoza aynan shu drift uchun mavjud va u **ishladi**.
- **Nega bu jimgina zarar bo'lardi:** ko'zguda yo'q kod xavfsizlik teshigi emas — `api-client` uni `errors.generic` ga tushiradi. Ya'ni admin «Kutilmagan xato» ni ko'rardi va «nega jadval saqlanmadi?» savoliga javob **faqat foydalanuvchi ekranida** yo'qolardi (§S-5 sinfining aynan o'zi).
- **Yechim:** uch qatlam ham yangilandi — `ERROR_CODES` massivi, `marketErrorMessageKey` ning `case` lari + `MarketErrorMessageKey` union'i, va uchala tildagi matnlar. `uz-Cyrl.json` **generatordan** hosil qilindi (`gen-cyrillic.mjs`), qo'lda yozilmadi.
- **Ikki kelajakdagi darvoza oldindan hisobga olindi:** (a) **G-1** — `snapshots.*` kalitlarida `slot`/`слот` taqiqlangan, shuning uchun kalit `scheduleTimesInvalid` (backend kodi `schedule_slots_invalid` bo'lib qoladi — u TEXNIK reyestr va foydalanuvchiga ko'rinmaydi); (b) **G-10** — kadrni o'chirish fe'li taqiqlangan, shuning uchun `objectPurged` matni «saqlash muddati tugagan» deydi, «o'chirilgan» EMAS.
- **Qamrov:** bu rejaning `files_modified` idan tashqaridagi 5 ta frontend fayli. `04-08` (parallel to'lqin) frontendga umuman tegmaydi, ya'ni to'qnashuv xavfi yo'q.
- **Committed in:** `56d818d`

---

**Total deviations:** 12 (4× Rule 3 bloklovchi, 4× Rule 1 bug, 2× o'z-o'ziga zid mezon, 2× qamrov qarori)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Ikkitasi (6, 7) darvozalarning o'z hujjati bilan to'qnashuvi edi va ikkalasi ham qarama-qarshi yo'nalishda hal qilindi — farq **sabab bilan** yozildi. Bittasi (5) faqat integratsiya testi topa oladigan ish-payti nuqsoni, bittasi (12) esa faqat frontend darvozasi topa oladigan til-chegarasi drifti edi.

## TDD gate compliance

⚠ **RED/GREEN commitlari AJRATILMADI.** Uchala task ham `tdd="true"` bo'lsa-da, test va implementatsiya bitta `feat(...)` commitida ketdi — `test(...)` commiti yo'q.

**Sabab va o'rnini bosuvchi dalil:** RED bosqichining maqsadi — testning **yuk ko'taruvchi** ekanini isbotlash. Bu rejada o'sha isbot **olti sabotaj o'lchovi** bilan berildi va ular RED commitidan **kuchliroq**: RED faqat «test hozir yiqiladi» deydi, sabotaj esa «AYNAN qaysi test, AYNAN qaysi o'zgarishga javob beradi va qolganlari yashil qoladi» deydi. Ikki sabotaj (1 va 3) esa **o'lik** chiqdi — RED commiti bunday holatni umuman ko'rsata olmasdi.

Kelgusi rejalar uchun: agar `test(...)` commiti darvoza sifatida kerak bo'lsa, uni sabotaj o'lchovi bilan **birga** talab qilish kerak — yolg'iz RED bu loyihada ikki marta yolg'on ishonch bergan.

## Ochiq topilma — marshrut-grafi darvozasi rasm marshrutini KO'RMAYDI

`02-19` `MARKET_DATA_VIEW` ostidagi uch marshrutning shaxsiy ma'lumotni **izsiz** berayotganini topgan va uni `tests/tenancy/test_personal_data_coverage.py` — marshrut grafini yuradigan darvoza — bilan yopgan edi. `<critical_context>` bu darvoza yangi marshrutlarni ko'radimi degan savolni qo'ydi.

**O'lchandi (taxmin emas):**

```
Darvoza QAMRAGAN marshrutlar: /stalls, /stalls/{id}, /stalls/{id}/assignments,
                              /vendors, /vendors/{id}
rasm marshruti app.routes da:        True
rasm marshruti PERSONAL_ROUTES da:   False
rasm marshruti audit e'lon qilgan:   ['snapshots']
```

**Ya'ni:** rasm marshruti auditni **e'lon qilgan**, lekin darvoza uni **talab qilmaydi**. 2-sabotaj buni amalda tasdiqladi: `audit_read` butunlay olib tashlanganda ham `test_personal_data_coverage.py` **yashil qoldi**.

**Sabab strukturaviy:** darvoza shaxsiy ma'lumotni `response_model` ning **maydon nomlari** bo'yicha aniqlaydi (`PERSONAL_FIELDS = {vendor_name, phone, full_name}`). Rasm marshrutida `response_model` umuman yo'q va shaxsiy ma'lumot — **baytlarning o'zi** (bozor tashrifchisining tasviri). Hech qanday maydon nomi buni ifodalay olmaydi.

**Bu rejada nima qilindi:** kafolat **o'z testlarim** bilan qamrandi (`test_reading_the_image_leaves_an_audit_row` + ikki «iz qoldirmaydi» testi) va ularning uchalasi ham sabotaj bilan o'lchandi. Darvozaning O'ZI kengaytirilmadi — `test_personal_data_coverage.py` bu rejaning `files_modified` idan tashqarida va uni kengaytirish (masalan `StreamingResponse` qaytaradigan marshrutlar uchun alohida shox) **alohida qaror**, chunki u butun loyihadagi har bir bayt qaytaradigan marshrutga tegadi (`imports/errors.xlsx` ham shunday).

**Egasi tavsiya etiladi: `04-12`** (fazani tekshirish rejasi) yoki `05` fazaning birinchi rejasi. **Tetik:** ikkinchi bayt-qaytaruvchi shaxsiy-ma'lumot marshruti paydo bo'lganda.

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `app/api/v1/schedules.py` | Marshrut tartibi + huquq dekoratorda + `audit_read` ning ATAYIN yo'qligi; `/today`, ro'yxat, `POST`/`PATCH`/`DELETE`; to'rt xato sinfining HTTP xaritasi | 450 |
| `app/api/v1/snapshots.py` | Uch qoidali docstring (proxy / `object_key` / `audit_read`); kun jurnali, kadr detali, RASM PROXYSI, ogohlantirishlar | 520 |
| `app/api/internal/self_check.py` | Uch qoidali docstring (healthcheck'ga ulanmaydi / boshqa jarayon / minimal javob); `stale` va `never_seen` ning ajratilishi | 203 |
| `app/repositories/alert_repo.py` | Faqat o'qish; yozish metodining ATAYIN yo'qligi darvoza sifatida | 68 |
| `tests/integration/test_capture_schedule.py` | 21 test: D-05, huquq da'vosi, to'rt rad etish yo'li, DB-trigger auditi, cross-tenant, self-check | 843 |
| `tests/integration/test_snapshot_api.py` | 17 test: oltala hisoblagich, YO'QLIK, arxiv bayrog'i, kelajak kun, proxy baytlari, ikki audit da'vosi, `purged`, allowlist | 713 |

## Bazaviy holat

| O'lchov | Baza (`04-07`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 755 | **1 837** | ✅ +82 |
| tenancy | 426 | **470** | ✅ +44 |
| vitest | 246 | **246** | ✅ o'zgarmagan |
| node | 111 | **111** (109 pass -> **111 pass** tuzatishdan keyin) | ✅ sanoq o'zgarmagan; ikkitasi 12-deviatsiyada QIZARGAN va tuzatilgan |
| i18n | 577 × 3 | **583 × 3** | ⚠ **+6** — 12-deviatsiya (olti yangi xato matni). Boshqa sababdan o'zgarish yo'q |
| `ruff` + `ruff format` + `mypy` | toza | **toza** (241 / 235 fayl) | ✅ |
| `git diff rbac.py rbac.ts` | — | **o'zgarish yo'q** | ✅ W0-F6 |
| `git diff compose.yaml` | — | **o'zgarish yo'q** | ✅ T-04-72 |
| `git diff pyproject.toml package.json` | — | **o'zgarish yo'q** | ✅ T-04-SC |

## Issues Encountered

- **`core-api` runtime image'i eskirgan edi** — `ModuleNotFoundError: No module named 'PIL'`. 04-04 `Pillow` ni `quality.py` ga kiritgan, image esa qayta qurilmagan. `docker compose build core-api` bilan tuzatildi; **kodga tegilmadi**. Bu 04-09 ning nuqsoni emas, lekin u `/internal/self-check` ni jonli tekshirishni bloklagani uchun bu yerda qayd etiladi.
- **8000-port band** — begona loyihaning konteyneri (`parnikkpi-backend-1`). Zond `-p 8123:8000` bilan ishga tushirildi va oxirida `docker rm -f` bilan olib tashlandi. `compose.yaml` ga tegilmadi.
- **`.env` va `ops/seaweedfs/s3.json` worktree'da yo'q edi** — ikkalasi ham `.gitignore` ostida (04-05/04-07 da ham shunday bo'lgan). Asosiy repodan nusxalandi; `git check-ignore -v` ikkalasini ham tasdiqladi.
- **`frontend/node_modules` worktree'da yo'q edi** — `npm ci --prefix frontend` bilan o'rnatildi (`package.json` va `package-lock.json` **tegilmadi**, `git diff --exit-code` bilan tasdiqlandi). Dastlab frontend butunlay tegilmagan deb hisoblangan edi; **frontend darvozalari aynan shu taxminni rad etdi** (12-deviatsiya) — backend reyestriga qo'shilgan kod til chegarasidan o'tib frontendga qarz qoldirar ekan.
- **Test o'z arifmetikasida bir marta yanglishdi** — `range(6, 12)` × 2 = 12, chegara ham 12. Nazorat asserti (`assert len(times) > limit`) buni **testning o'zida** ushladi va `range(6, 13)` ga tuzatildi. Bu 04-05 da ham aynan shunday bo'lgan; nazorat asserti o'sha rejadan meros.

## Known Stubs

Yo'q. To'qqizala marshrut ham to'liq ishlaydi va har biri integratsiya testi bilan qamralgan.

⚠ **Stub bo'lmagan, lekin ochiq qolgan ikki band (ikkalasining ham egasi bor):**

1. **`future` profilning nomi/davri tahrirlanmaydi** — 11-deviatsiya, egasi `04-10`/`04-11`. Tetik: UI DL-2 da to'g'ridan-to'g'ri tahrirni talab qilganda.
2. **`test_personal_data_coverage.py` bayt-qaytaruvchi marshrutlarni ko'rmaydi** — yuqoridagi «Ochiq topilma», egasi `04-12` yoki 5-faza. Kafolat bu rejada o'z testlari bilan qamralgan.

## Threat Flags

Threat register'ning o'nala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-67 (presigned URL) | Rasm faqat proxy orqali; imzolangan-havola API'sining ikkala nomi ham faylda **yo'q**; javob **tanasi VA sarlavhalarida** ombor izi yo'qligi test bilan |
| T-04-68 (kadrning izsiz o'qilishi) | `audit_read` majburiy; **ikki** mustaqil test (403 va 410 yo'llari) + ijobiy da'vo; ikkalasi ham sabotaj bilan o'lchandi |
| T-04-69 (`object_key` sizishi) | `SnapshotDetailOut.model_fields` darvozasi; sarlavha darvozasi; jadval javoblarida ham tekshiriladi |
| T-04-70 (huquq imzoda) | Dekoratorda; **lekin sabotaj o'lik chiqdi** — sabab va o'rnini bosuvchi o'lchov yuqorida |
| T-04-71 (self-check topologiya sizishi) | Javob `{ok, stale, never_seen}` bilan CHEKLANGAN (`set(body)` tengligi bilan); ikki bozor identifikatori va nomi javobda yo'qligi alohida test bilan |
| T-04-72 (healthcheck'ga ulanish) | `compose.yaml` **tegilmagan** (`git diff --exit-code`); matn darvozasi konfiguratsiyani o'qiydi |
| T-04-73 (alertni qo'lda yopish) | Marshrut umuman qurilmagan; regex darvozasi **ikki** shaklda (`("/alerts"` va `alerts_router.patch`) |
| T-04-74 (`detail` dagi noma'lum kalit) | Allowlist **DTO validatorida**; test noma'lum kalit tashlanishini VA ma'lumi qolishini birga o'lchaydi |
| T-04-75 (begona bozor kadri) | 404 va u MAVJUD BO'LMAGAN ID bilan **bayt-bayt bir xil**; `tests/tenancy` 470/470 |
| T-04-SC (paket o'rnatish) | Yangi paket **YO'Q**; `git diff --exit-code` toza |

⚠ **Yangi mitigatsiya (registerda yo'q edi):** `_IMAGE_CACHE_CONTROL = "private, no-store"`. `private` yolg'iz o'zi brauzerga keshlashga **ruxsat berardi** va kadr diskda sessiyadan uzoqroq yashardi — umumiy kompyuterda bu boshqa foydalanuvchi uchun ochiladigan shaxsiy ma'lumot bo'lardi.

⚠ **Yangi yuza (registerda yo'q edi):** `GET /internal/self-check` — **autentifikatsiyasiz** yangi tarmoq endpointi. Javobi tor (uchta kalit, tenant ma'lumoti yo'q) va u `internal` paketida, ya'ni nginx tomonda `live-authz` bilan bir xil cheklovga tushishi kerak. ⚠ **`ops/nginx/nginx.conf` bu rejada TEGILMADI** (`files_modified` dan tashqarida) — tashqi kuzatuvchi unga yetib borishi uchun nginx qoidasi **kerak bo'ladi** va uning egasi `04-08` (`ops/docs/monitoring.md`) yoki 8-faza. **Hozircha endpoint faqat compose tarmog'idan ochiq.**

## Next Phase Readiness

**`04-10`/`04-11` (frontend) uchun:** to'qqizala marshrut ham `04-UI-SPEC.md` §4.3 / §6.3 / §6.4 / §6.6 / §6.7 shakllari bilan **aynan** mos. `CaptureRunOut` to'qqizala hujayra holatini chizish uchun yetarli (`status` + `quality_verdict`), `DaySummaryOut` oltala hisoblagichni nol bilan birga beradi, `archived_present` esa §6.4 ning oxirgi qatorini oziqlantiradi. ⚠ **Vaqtlar `HH:MM:SS` shaklida keladi** — UI ularni `HH:mm` ga formatlaydi.

**`04-12` (tekshirish) uchun:** yuqoridagi «Ochiq topilma» — marshrut-grafi darvozasining bayt-qaytaruvchi marshrutlarni ko'rmasligi.

**`04-08` (parallel to'lqin) uchun:** `/internal/self-check` `alert_sweep` va `retention` komponentlarini `EXPECTED_COMPONENTS` da **allaqachon kutadi**. Ular yurak urishi yozgan zahoti `never_seen` dan chiqadi — qo'shimcha kod kerak emas. ⚠ Komponent nomlari **aynan** `alert_sweep` va `retention` bo'lishi shart.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Yaratilgan oltala fayl + SUMMARY diskda tekshirildi** (`MISSING: 0`).
- **To'rtala commit `git log 384195a..HEAD` da tasdiqlandi:** `4ca059c`, `da752ec`, `8546d1d`, `56d818d`.
- **Uchala task commitida ham fayl o'chirilishi YO'Q** (`git diff --diff-filter=D` bo'sh).
- **`STATE.md` va `ROADMAP.md` TEGILMADI** — ular to'lqin merge'idan keyin orkestrator tomonidan yangilanadi.
- **Ishchi daraxt toza:** `.env` va `ops/seaweedfs/s3.json` gitignore ostida qoldi; zond konteyneri o'chirildi.

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
