---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 06
subsystem: api
tags: [fastapi, sqlalchemy, pure-functions, v5-validation, versioning, rls, rbac, coverage, i18n]

requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`camera_zones` sxemasi va uning `CHECK` lari (05-05); `OCCUPANCY_ERROR_CODES` reyestri va `app/schemas.py` allowlist'i (05-04); `zone-geometry.ts` — klient jufti va uning `EPS` i (05-03)"
  - phase: 04-snapshot-pipeline
    provides: "`snapshots.width`/`height` ustunlari (kadr NISBATINING yagona manbai), `snapshot_domain` seed'i, `capture_errors` reyestr naqshi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`cameras (market_id, id)` kompozit FK nishoni, `CAMERA_VIEW`/`CAMERA_MANAGE` huquqlari, «huquq dekoratorda» qarorining O'LCHANGAN chegarasi (03-07)"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`zones.py` router shakli (alias bloki, cross-tenant 404), `stalls.py` ning `audit_read` ATAYIN YO'Q holati, `TenantScopedRepository.scoped()`"
provides:
  - "`app/services/zone_geometry.py` — V5 ning ISHONCH MANBAI: `validate_polygon`, `aspect_ratio_matches`, `normalize`/`denormalize`; `Settings` ni bilmaydi"
  - "`app/repositories/camera_zone_repo.py` — D-07 versiyalash, D-22 qamrov, `latest_frame_size()`, `zones_needing_review()`"
  - "`app/api/v1/camera_zones.py` — to'rt marshrut, YANGI `Permission` SIZ"
  - "`ZONE_POLYGON_DEGENERATE_EDGE` — reyestrning 15-kodi va uchala tildagi matni"
  - "`Settings.zone_max_vertices` / `zone_max_per_camera` / `zone_aspect_tolerance`"
  - "`tests/fixtures/occupancy_domain.py` — ikki kamerali rasta, 4:3 kadrda chizilgan zona, zonasiz rasta, `camera_id`"
  - "`tests/fixtures/snapshot_domain.py` — `snapshots.width`/`height` ENDI to'ldiriladi (ular NULL edi)"
  - "Cross-tenant matritsasining BESHINCHI qatlami (`TenantSeed.occupancy`) va `camera_zone_id` filleri"
affects: [05-08, 05-09, 05-12, 05-15]

tech-stack:
  added: []
  patterns:
    - "Sof geometriya moduli klient juftidan AYNAN ko'chiriladi (`EPS` ham) — ikki tomon «yaroqli poligon» ta'rifida ajrala olmaydi"
    - "Server klientdan QAT'IYROQ bo'lishi mumkin va bu to'g'ri yo'nalish; teskarisi TAQIQLANGAN"
    - "Reyestrga yangi kod qo'shish — `zone_geometry.py` da literal o'ylab topishdan yagona to'g'ri muqobil (§S-5), va u UCHALA til bilan BIRGA boradi"
    - "`round()` ISHLATILMAYDI: Python bankir yaxlitlashi, `Math.round` esa yarimni yuqoriga — ikki tomon chegarada bir pikselga ajraladi"
    - "Oraliq tekshiruvi SOLISHTIRISHGA tayanadi (`0.0 <= v <= 1.0`), `abs(v) > 1` ga EMAS — `NaN` ni ushlash uchun"
    - "`scoped()` `select(func.count(...))` da ISHLAMAYDI (entity yo'q) — predikat qo'lda yoziladi"
    - "Query parametridagi tenant identifikatori cross-tenant matritsasiga TUSHMAYDI va uning chegarasi ALOHIDA test bilan qoplanadi"

key-files:
  created:
    - services/core-api/app/services/zone_geometry.py
    - services/core-api/app/repositories/camera_zone_repo.py
    - services/core-api/app/api/v1/camera_zones.py
    - tests/unit/test_zone_geometry.py
    - tests/integration/test_camera_zones_api.py
  modified:
    - services/core-api/app/schemas.py
    - services/core-api/app/settings.py
    - services/core-api/app/main.py
    - services/core-api/app/services/occupancy_errors.py
    - frontend/src/lib/zone-errors.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json
    - frontend/scripts/error-codes.test.mjs
    - tests/fixtures/occupancy_domain.py
    - tests/fixtures/snapshot_domain.py
    - tests/tenancy/test_cross_tenant.py
    - tests/tenancy/test_route_coverage.py

key-decisions:
  - "`POLYGON_DEGENERATE_EDGE` REYESTRGA QO'SHILDI — u mavjud beshta kodning birortasiga ham to'g'ri kelmaydi va uni `SELF_INTERSECTING` ga qo'shish adminni MAVJUD BO'LMAGAN kesishmani qidirishga majburlardi. Klient uni UMUMAN ko'rmasligi test bilan O'LCHANDI"
  - "`_round_half_up()` — o'rnatilgan `round()` BANKIR yaxlitlashi va `Math.round` bilan aynan chegarada ajraladi; `math.floor(v + 0.5)` ham rad etildi (qo'shishning O'ZI yaxlitlash xatosi kiritadi)"
  - "`zone_aspect_tolerance` 0,05 — `snapshots.width`/`height` `draft()` ning KICHRAYTIRILGAN natijasi, ya'ni 1/8 masshtabda nisbat ~0,013 ga siljiydi va 0,01 tolerans HAR ZONANI belgilardi"
  - "`coverage()` `market_id` ni ARGUMENT sifatida OLMAYDI (reja imzosidan farq) — ikkinchi argument T-05-24 ning aynan shakli bo'lardi"
  - "Qamrov sanog'i FAQAT `active` rastalarni oladi: `closed`/`maintenance` ga hisob yozilmaydi (A4), ya'ni ularni sanash `uncovered` ni hech qachon nolga tushmaydigan shovqinga aylantirardi"
  - "Bir payloadda takrorlangan `stall_id` ROUTERDA rad etiladi — `UNIQUE (market_id, camera_id, stall_id, version)` uni USHLAMASDI (ikkala qator ham YANGI va ular turli `version` oladi)"
  - "`version` FAOL qatordan emas, `MAX(version)` DAN hisoblanadi — o'chirilib qayta chizilgan zona aks holda eski raqamni qayta ishlatib, sababsiz 409 berardi"
  - "Huquq IMZODA (`zones.py` alias bloki), dekoratorda EMAS — bu router `audit_read` E'LON QILMAYDI, ya'ni 03-07 dagi tartib xavfi bu yerda MAVJUD EMAS; da'vo o'rniga XULQ bilan qulflandi"

patterns-established:
  - "Chekli domenni sanab chiqish AYLANMA yo'qotishsizligini isbotlaydi, lekin klient bilan YAXLITLASH FARQINI ko'rmaydi — ikki xususiyat, ikki test (S6 bilan o'lchandi)"
  - "«Uchala son qaytadi» testi buzilgan `uncovered` ni USHLAY OLMAYDI — nol qiymat uni trivial qanoatlantiradi (S4 bilan o'lchandi)"
  - "Cross-tenant matritsasi HUQUQ kuchsizlanishini ham, QUERY parametridagi tenant chegarasini ham umuman ko'rmaydi (S3 va S5 bilan o'lchandi)"

requirements-completed: []
requirements-advanced: [AI-01]
# ⚠ ATAYIN BO'SH. Bu reja AI-01 ning SERVER yuzasini to'liq yetkazadi,
# lekin talabni YOPMAYDI: AI-01 «bozor admini kamera kadrida rasta
# zonalarini poligon qilib CHIZADI» deydi va chizish yuzasi 05-09 da
# (`zone-canvas.tsx` + muharrir ekrani). Bugungi holatda poligon faqat
# `curl` bilan yuborilishi mumkin. `05-15` fazani DALIL bilan yopadi —
# 05-05 dagi bilan aynan bir xil qaror.

duration: ~3 soat
completed: 2026-08-09
---

# Phase 5 Plan 06: `camera_zones` API — V5 ning ishonch manbai, D-07 versiyalash va D-22 qamrovi Summary

**Poligon geometriyasining ishonch manbai endi serverda va sof funksiyalarda; tahrir `UPDATE` emas, yangi `version` qatori; qamrovsiz rasta `no_coverage` bo'lib «bo'sh» dan ajratildi — oltita sabotaj bilan har biri alohida o'lchandi va ulardan uchtasi TEST YOZILMAGAN bo'shliqni fosh qildi.**

## Bajarilgan ishlar

### Task 1 — `zone_geometry.py` (TDD) — `56a5a6b` (RED) → `f33b899` (GREEN)

Olti xato kodi (**hammasi reyestrdan ALIAS**, literal yozilmagan), `validate_polygon()`, `aspect_ratio_matches()`, `normalize`/`denormalize`.

Kesishish algoritmi `zone-geometry.ts:112-400` dan **aynan ko'chirildi**, `EPS = 1e-12` bilan birga: ikki tomon «yaroqli poligon» ta'rifida ajralib ketsa, admin brauzerda yashil ko'rgan poligon serverda rad etilardi va sabab **ekranda ko'rinmasdi**.

`Settings` ga uch chegara: `zone_max_vertices` (DB `CHECK` i bilan **yuqoridan chegaralangan**), `zone_max_per_camera`, `zone_aspect_tolerance`.

**O'lchangan qabul mezonlari:** `grep -cE "^\s*(from|import) app\.settings" zone_geometry.py` → **0** ✅ (va u endi `test_geometry_module_does_not_import_settings` bilan CI ostida); oltala kod `OCCUPANCY_ERROR_CODES` ichida ✅; aylanma to'rt kenglikda **to'liq sanab** chiqildi ✅; `mypy .` toza ✅.

### Task 2 — `camera_zone_repo.py` va seed kengaytmasi — `d799726`

| Metod | Holat |
|---|---|
| `list_for_camera(camera_id, *, include_inactive=False)` | ✅ rasta raqami tartibida, `stall_code` bilan |
| `replace_for_camera(camera_id, zones)` | ✅ uch tarmoq: yangi / o'zgarmagan / versiyalangan + ro'yxatda yo'qlarni eskirtirish |
| `coverage()` | ✅ uchlik, `market_id` ARGUMENTSIZ (deviatsiya #5) |
| `needs_review_for_camera(...)` | ✅ FAKT qaytaradi, avtomatik to'g'rilash YO'Q |
| `latest_frame_size(camera_id)` | ➕ rejada yo'q edi — `needs_review` ning yagona kirishi |
| `camera_exists(camera_id)` | ➕ rejada yo'q edi — bo'sh ro'yxat 404 ning o'rnini bosa olmaydi |
| `deactivate(zone_id)` | ✅ qattiq `DELETE` yo'q; `is_active = true` sharti bilan |

Seed: `stall_ids[0]` **ikki kamerada**, ikkinchisining zonasi **640×480** (4:3) kadrda, `stall_ids[2]` **zonasiz**, `camera_id` endi `MarketOccupancyRows` da.

### Task 3 — marshrutlar, sxemalar va darvoza — `5afadf7`

To'rt marshrut (`GET`, `PUT`, `GET /coverage`, `DELETE /{camera_zone_id}`), `CameraZoneItem`/`CameraZoneListResponse`/`CameraZoneWrite`/`CameraZoneRequest`/`ZoneCoverageResponse`.

**Yangi `Permission` QO'SHILMADI** — `git diff --name-only` chiqishida `security/rbac.py` ham, `frontend/src/lib/rbac.ts` ham **YO'Q** ✅.

20 integration test (rejadagi **o'n bittasi ham** nomma-nom bor) + cross-tenant matritsasining beshinchi qatlami.

## Deviations from Plan

### 1. `[Rule 3 - Blocking]` `ZONE_POLYGON_DEGENERATE_EDGE` reyestrga qo'shildi

- **Topildi:** Task 1, `<behavior>` dagi `POLYGON_DEGENERATE_EDGE` uchun kod izlaganda
- **Muammo:** Reja oltita konstantani sanaydi; reyestrda esa **beshtasi** bor edi. Reja bu holatni oldindan ko'rgan: «kerak bo'lsa reyestrga qo'shiladi va uchala til bilan birga».
- **Nega ALOHIDA kod, `SELF_INTERSECTING` ga qo'shilmadi:** klientning `isSelfIntersecting` algoritmi takrorlangan tepani **TOPA OLMAYDI** — nol uzunlikdagi kesmada orientatsiya determinanti har doim nol, ya'ni na «nina» sharti (`dot > EPS`), na umumiy kesishuv sharti (`o1 !== o2`) bajariladi. Bu **o'lchandi**: `test_client_geometry_cannot_see_a_duplicate_vertex` klient shartlarini aynan takrorlab, ikkalasining ham bajarilmasligini isbotlaydi. Ya'ni bu rad etish yo'li **faqat serverda** mavjud va uni «kesishgan» deb atash adminni **mavjud bo'lmagan** kesishmani qidirishga majburlardi.
- **Tuzatish:** `occupancy_errors.py` (kod + docstring), `zone-errors.ts` (union + meta), uchala `messages/*.json` (`errorCause` + `errorFix`), `error-codes.test.mjs` nazorat sanoqlari (14 → 15, `ZONE_ERROR_CODES` 8 → 9).
- **Fayllar:** yuqoridagi beshta + `uz-Cyrl.json` (generator bilan)
- **Commit:** `56a5a6b`

### 2. `[Rule 1 - Bug]` Python ning `round()` i klient bilan AJRALADI

- **Topildi:** Task 1, `denormalize` ni yozayotganda
- **Muammo:** O'rnatilgan `round()` — **bankir yaxlitlashi** (yarimni juft songa): `round(640.5) == 640`, lekin `round(641.5) == 642`. JavaScript ning `Math.round` esa yarimni **har doim yuqoriga** oladi. Ya'ni klient va server aynan chegara qiymatida **bir pikselga** ajralardi va farq faqat ba'zi koordinatalarda, ba'zi kadr kengliklarida ko'rinardi — takrorlab bo'lmaydigan «zona bir piksel siljidi» nosozligi.
- **Rad etilgan muqobil:** `math.floor(value + 0.5)` — qo'shishning O'ZI suzuvchi nuqtada yaxlitlash xatosi kiritadi (`0.49999999999999994 + 0.5` aynan `1.0` beradi).
- **Tuzatish:** `_round_half_up()` — kasr qismini **ayirish** bilan oladi (aniq amal).
- **Nega aylanma testi buni USHLAMAYDI:** sabotaj S6 bilan o'lchandi (pastdagi jadval).
- **Fayllar:** `zone_geometry.py`, `test_zone_geometry.py`
- **Commit:** `f33b899`

### 3. `[Rule 3 - Blocking]` `snapshots.width`/`height` seed'da `NULL` edi

- **Topildi:** Task 3, `test_aspect_change_flags_zone` **o'zining nazorat asserti** bilan
- **Muammo:** `needs_review` joriy kadr o'lchamiga tayanadi, `snapshot_domain` seed'i esa `width`/`height` ustunlarini **umuman yozmasdi**. Natijada `latest_frame_size()` har doim `None` qaytarardi va bayroq **hech qachon ko'tarilmasdi**.
- **⚠ Bu deviatsiyaning qiymati testning SHAKLIDA:** assert `assert body["frame_width"] is not None` bo'lmaganda test **yashil** bo'lardi — `flags[stall_narrow] is True` tekshiruvi bajarilmasdan oldin ro'yxat bo'sh emas edi, lekin ikkala bayroq ham `false` bo'lib, test faqat `is False` shoxida yiqilardi... yoki umuman yiqilmasdi, agar men faqat bitta zonani tekshirgan bo'lsam. Nazorat asserti sababni **birinchi qadamda** ko'rsatdi.
- **Tuzatish:** `DECODED_WIDTH = 480` / `DECODED_HEIGHT = 270` (16:9) — **haqiqiy kadr o'lchami EMAS, `draft()` ning natijasi sinfida**, chunki ishlab chiqarishda ham shunday. Sabab ikkala joyda ham yozildi.
- **Fayllar:** `tests/fixtures/snapshot_domain.py`
- **Commit:** `5afadf7`

### 4. `[Rule 2 - Correctness]` `zone_aspect_tolerance` — sozlama, va u 0,05

- **Muammo:** Reja `Settings` ga ikki chegara qo'yishni aytadi, `aspect_ratio_matches()` esa **uchinchisini** talab qiladi (tolerans **argument**). U routerda literal bo'lib qolsa `quality_*` chegaralari yonida **ko'rinmasdi**.
- **Nega 0,01 EMAS, 0,05:** `snapshots.width`/`height` — `quality.py::analyze()` ning `draft("RGB", (320,180))` natijasi, ya'ni **kichraytirilgan dekod**. Pillow ko'paytuvchini ikkala o'qqa bir xil qo'llaydi (nisbat saqlanadi), lekin natija `ceil()` bilan yaxlitlanadi va 1/8 masshtabda (1920×1080 → 240×135) har o'qdagi bir pikselli farq nisbatni **~0,013** ga siljitishi mumkin. 0,01 tolerans bilan bu **har zonani** «tekshirish kerak» qilib, bayroqni butunlay ma'nosiz qilardi. 0,05 esa 16:9 va 4:3 orasidagi farqdan (0,444) **to'qqiz barobar** kichik.
- **Fayllar:** `settings.py`
- **Commit:** `f33b899` (qiymat `5afadf7` da aniqlashtirildi)

### 5. `[Rule 2 - Correctness]` `coverage()` `market_id` ni ARGUMENT sifatida olmaydi

- **Muammo:** Reja imzosi `coverage(market_id)`. Repozitoriy `TenantScopedRepository` dan meros oladi, ya'ni `self.market_id` allaqachon **yagona manba**. Ikkinchi argument chaqiruvchiga boshqa bozorning identifikatorini berish yo'lini ochardi va u aynan **T-05-24** ning shakli bo'lardi.
- **Tuzatish:** `coverage()` — argumentsiz; sabab docstringda.
- **Fayllar:** `camera_zone_repo.py`

### 6. `[Rule 3 - Blocking]` Cross-tenant matritsasiga BESHINCHI qatlam kerak bo'ldi

- **Topildi:** Task 3, `tests/tenancy` birinchi ijrosida
- **Muammo:** `DELETE /camera-zones/{camera_zone_id}` yangi yo'l parametri kiritadi va `test_no_unclassified_routes` uni **darhol** rad etdi. Filler esa **haqiqiy B bozori qatorini** talab qiladi (`test_param_fillers_point_at_the_other_market`) — tasodifiy UUID bilan 404 hech nimani isbotlamasdi.
- **Tuzatish:** `TenantSeed` ga `occupancy` qatlami (`occupancy_domain` fixture'i, `snapshot_domain` USTIGA), `PARAM_FILLERS["camera_zone_id"]` va `foreign_values` ga B ning **faol** zonalari. Eskirgan zona ATAYIN olinmadi: `deactivate()` `is_active = true` shartini qo'yadi, ya'ni u 404 ni tenant chegarasi emas, **holat** tufayli berardi.
- **⚠ Matritsaning O'Z darvozasi bu xatoni birinchi ijroda ushladi** — `test_param_fillers_point_at_the_other_market` men filler qo'shgan zahoti qizardi.
- **Fayllar:** `tests/tenancy/test_cross_tenant.py`, `tests/tenancy/test_route_coverage.py` (`MINIMUM_MATRIX_ROUTES` 48 → 52)
- **Commit:** `5afadf7`

### 7. `[Rule 2 - Correctness]` Bir payloadda takrorlangan `stall_id` ROUTERDA rad etiladi

- **Muammo:** `ZONE_STALL_ALREADY_COVERED` reyestrda bor, lekin **DB konstrayti uni ushlamaydi**: `UNIQUE (market_id, camera_id, stall_id, version)` uchun ikkala qator ham YANGI va ular **turli `version`** oladi. Ya'ni bir rasta bitta kamerada IKKI faol konturga ega bo'lardi va ular bir kadrga ikki qarama-qarshi verdikt berardi.
- **Tuzatish:** `replace_camera_zones()` da payload ichidagi takrorni 409 bilan rad etadi; sabab docstringda, taqiqning **BIR KAMERA ICHIDA** ekani ta'kidlangan (bir rasta bir necha kamerada — D-20 ning asosi).
- **Fayllar:** `camera_zones.py`; `test_second_zone_for_the_same_stall_on_one_camera_is_rejected`
- **Commit:** `5afadf7`

### 8. `[Rule 2 - Correctness]` `zone_max_vertices` DB `CHECK` i bilan chegaralandi

`Field(le=POLYGON_MAX_VERTICES)` — usiz sozlamani 13 ga qo'yish mumkin bo'lardi va 13 tepali poligon ilova darvozasidan **o'tib**, bazada `23514` bilan rad etilardi; admin `zone_polygon_too_many_points` o'rniga tushunarsiz javob olardi. Pastga qo'yish (qat'iyroq) — qonuniy sozlash yo'li.

### 9. `[Qaror]` Huquq IMZODA, dekoratorda EMAS

Reja `zones.py:50-53` alias blokini **verbatim** ko'rsatadi (imzo shakli), orkestrator esa `stalls.py` ning `dependencies=[...]` shaklini eslatadi. Ikkalasi zid emas: `stalls.py` da dekorator **AYNAN `audit_read` tufayli** kerak — 403 olgan so'rov `audit_read` gacha yetib bormasligi va jurnalda «kim nimani ko'rdi» degan **yolg'on dalil** qolmasligi uchun.

Bu router `audit_read` ni **e'lon qilmaydi** (jadval shaxsiy ma'lumot emas — `stalls.py:348-369` bilan bir xil qaror), ya'ni o'sha tartib xavfi bu yerda **mavjud emas**. Shuning uchun `zones.py` shakli olindi va **da'vo** qulflandi, mexanizm emas: `test_director_cannot_replace_zones` 403 ni **VA** rad etilgan `PUT` dan keyin audit jurnalida yangi qator qolmaganini o'lchaydi, nazorat sifatida esa o'sha sessiyaning `GET` i 200 berishini talab qiladi.

### 10. `[Rule 2 - Correctness]` `_has_degenerate_edge` aniq tenglik EMAS, `_EPS`

Aniq `==` 1e-15 ga ajralgan juftni o'tkazib yuborardi va **u ham** kesishuv testidan bemalol o'tardi — ya'ni na kesishgan, na degenerat deb hisoblangan poligon zona kutubxonasiga **aniqlanmagan holda** yetib borardi. Chegara — orientatsiya testidagi **aynan o'sha** `_EPS`, yangi son emas.

## Sabotage o'lchovi — nima QIZARDI va NIMA YASHIL QOLDI

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --` ishlatilmadi); oxirida `git status` **toza**.

| # | Sabotaj | NATIJA |
|---|---|---|
| **S1** | `validate_polygon` dan kesishuv tekshiruvini o'chirish | 🔴 `test_bowtie_is_rejected`, `test_spike_along_an_existing_edge_is_rejected`, `test_vertex_touching_a_non_adjacent_edge_is_rejected`, `test_self_intersecting_polygon_is_rejected` — **to'rtta, uchta darajada** (unit + HTTP) |
| **S2** | `replace_for_camera` ni joyida `UPDATE` ga aylantirish (versiyalash yo'q) | 🔴 `test_edit_creates_new_version`; 🔴 `test_zone_change_is_audited` (kutilmagan ikkinchi signal: `UPDATE` audit qatori `insert` emas)<br>⚠ **`test_old_version_survives_edit` YASHIL QOLDI** — va bu TO'G'RI: sabotaj **faol** qatorni o'zgartiradi, eskirgani esa tegilmagan. Ikki test D-07 ning **ikki xil yarmini** o'lchaydi va faqat birgalikda uni qulflaydi |
| **S3** | `PUT` ni `CAMERA_MANAGE` o'rniga `CAMERA_VIEW` ga tushirish | 🔴 `test_director_cannot_replace_zones` — **yolg'iz**<br>⚠ **BUTUN `tests/tenancy` (506 test) YASHIL QOLDI** — cross-tenant matritsasi huquq kuchsizlanishini **umuman ko'rmaydi**: u faqat begona obyektga 404 ni tekshiradi |
| **S4** | `coverage()` da `uncovered = 0` (D-22 yiqiladi) | 🔴 `test_coverage_reports_uncovered_stalls`<br>⚠ **`test_coverage_returns_all_three_counts_when_nothing_is_uncovered` YASHIL QOLDI** — u `uncovered == 0` ni kutadi, ya'ni sabotaj uni **trivial qanoatlantiradi**. «Uchala son qaytadi» testi buzilgan `uncovered` ni HECH QACHON ushlay olmaydi |
| **S5** | `GET` dan `camera_exists()` tekshiruvini olib tashlash | 🔴 `test_cross_tenant_camera_returns_404` — **yolg'iz**<br>⚠ **BUTUN `tests/tenancy` YASHIL QOLDI** — `camera_id` QUERY parametri, `PARAM_FILLERS` esa faqat YO'L parametrlarini to'ldiradi. Matritsa bu tenant chegarasini **prinsipial ravishda** qamramaydi |
| **S6** | `_round_half_up()` o'rniga o'rnatilgan `round()` (bankir yaxlitlashi) | 🔴 `test_denormalize_rounds_halves_upward_like_the_client` — **yolg'iz**<br>⚠ **`test_round_trip_is_lossless_for_every_integer_pixel` TO'RTALA KENGLIKDA HAM YASHIL QOLDI** (640, 1279, 1280, 1920 — har biri to'liq sanab chiqilgan holda) |

### S6 — bu rejaning eng qimmatli natijasi

05-03 aylanma testini **tanlashdan sanashga** o'tkazdi va u to'g'ri tuzatish edi. S6 esa **bir qavat chuqurroq** boradi: chekli domenni **to'liq sanab chiqish** ham klient bilan yaxlitlash farqini **ko'ra olmaydi** — chunki `p/w*w` hech qachon aniq `.5` ga tushmaydi, ya'ni bankir yaxlitlashi bilan yarimni-yuqoriga yaxlitlash **o'sha domenda hech qanday farq bermaydi**.

Ya'ni «aylanma yo'qotishsiz» va «klient bilan bir xil yaxlitlaydi» — **ikki mustaqil xususiyat** va ular ikki alohida test talab qiladi. Sanab chiqish birinchisini isbotlaydi, ikkinchisi haqida esa **hech nima aytmaydi**.

### S3 va S5 — matritsaning chegarasi o'lchandi

Ikkala sabotaj ham **506 tenancy testini yashil qoldirdi**. Bu matritsaning nosozligi emas, **qamrovining ta'rifi**: u «A tokeni + B obyekti → 404» ni o'lchaydi va (a) huquq darajasini, (b) query parametridagi tenant identifikatorini ko'rmaydi. Ikkalasi ham `test_camera_zones_api.py` da **nomma-nom** qoplangan va bu bog'liqlik `main.py` dagi router izohida yozib qo'yildi.

## Verification

| Tekshiruv | Natija |
|---|---|
| `pytest -q` (to'liq) | ✅ **2032 o'tdi, 0 nosoz** (bazaviy 1956 + 76) |
| `pytest tests/tenancy` | ✅ **506** (bazaviy 488 + 18) |
| `tests/unit/test_zone_geometry.py` | ✅ **38** |
| `tests/integration/test_camera_zones_api.py` | ✅ **20** (rejadagi 11 tasi nomma-nom + 9 nazorat) |
| `ruff check . && ruff format --check . && mypy .` | ✅ toza (262 fayl) |
| `vitest run` | ✅ **399 (30 fayl)** |
| `node --test scripts/*.test.mjs` | ✅ **144**, G-17 ichida |
| `npm run i18n:check` | ✅ **821 × 3** (bazaviy 819 + 2 — yangi kodning sabab/tuzatish matni) |
| `npm run typecheck` / `npm run lint` (frontend) | ✅ toza |
| `grep -cE "^\s*(from\|import) app\.settings" zone_geometry.py` | ✅ **0** |
| `git diff --name-only` da `security/rbac.py` / `frontend/src/lib/rbac.ts` | ✅ **YO'Q** (yangi huquq qo'shilmadi) |

## Decisions Made

Yuqoridagi `key-decisions` ga qarang. Eng ta'sirlilari:

1. **Server klientdan QAT'IYROQ bo'lishi mumkin.** `POLYGON_DEGENERATE_EDGE` klient ko'rmaydigan yo'lni yopadi. Teskarisi — server yumshoqroq bo'lishi — taqiqlangan: u darvozani butunlay brauzerga ko'chirardi.
2. **`round()` ishlatilmaydi.** Bu bezak emas: bankir yaxlitlashi klient bilan aynan chegarada bir pikselga ajraladi va nosozlik takrorlab bo'lmaydigan bo'lardi.
3. **Qamrov faqat `active` rastalarni sanaydi.** `closed`/`maintenance` ga hisob yozilmaydi (A4), ya'ni ularni sanash `uncovered` ni hech qachon nolga tushmaydigan shovqinga aylantirardi va admin ogohlantirishga qarashni to'xtatardi.
4. **Payloaddagi takror routerda rad etiladi.** DB konstrayti uni ushlamaydi — bu o'lchangan fakt, ehtiyot chorasi emas.

## Keyingi rejalar uchun ochiq bandlar

- **`05-09` (muharrir ekrani):** `GET /camera-zones?camera_id=` javobida `frame_width`/`frame_height` bor va ular `None` bo'lishi mumkin (kamerada hali yaroqli kadr yo'q). ⚠ Bu qiymatlar **kadrning haqiqiy o'lchami EMAS** (`draft()` natijasi) — ularni `denormalize()` uchun ishlatish har koordinatada to'rt barobar xato berardi. Render `<img>` ning **haqiqiy** o'lchamiga tayanishi kerak.
- **`05-09`:** `PUT` — **butun kamera uchun almashtirish**: ro'yxatda yo'q faol zona eskirtiriladi. Qisman `PATCH` yo'li YO'Q.
- **`05-08` (detektor yozuvi):** faol zonalar `list_for_camera()` bilan olinadi va `zone_version` **qatordan** nusxalanadi — qayta hisoblanmaydi.
- **`05-12` (kun yopilishi):** `coverage()` faqat `active` rastalarni sanaydi. `stall_slot_occupancy` ning `no_coverage` materializatsiyasi **boshqa** populyatsiyani tanlasa (masalan barcha rastalarni), ikki son bir-biriga mos kelmasligi mumkin — bu qaror o'sha rejada **ongli** qilinishi kerak.
- **⚠ OCHIQ BAND — `zone_aspect_tolerance` ning HAQIQIY qiymati.** 0,05 `draft()` ning yaxlitlash siljishidan (~0,013) chiqarilgan **hisob**, real Karmana kadrlaridagi **o'lchov emas**. Phase 0 ning kadrlari kelganda `snapshots.width`/`height` taqsimotidan tekshirilishi kerak. U darvoza emas va bo'lmasligi ham kerak.
- **⚠ OCHIQ BAND:** `PUT` bitta tranzaksiyada zona sonicha `UPDATE`+`INSERT` bajaradi (60 zona → ~120 operator). Karmana miqyosida bu qabul qilinadigan, lekin 05-09 ning UAT'ida o'lchanishi ma'noli.

## Known Stubs

Yo'q. Uchala modul ham to'liq ishlaydi; birorta hardkod bo'sh qiymat, placeholder matn yoki «keyinroq to'ldiriladi» holati qoldirilmadi. `latest_frame_size()` ning `None` qaytarishi stub EMAS — u **nomlangan mahsulot holati** (yangi ulangan kamerada hali kadr yo'q) va javobda `frame_width: null` bilan ochiq ifodalanadi.

## Threat Flags

Rejalashtirilmagan yangi xavfsizlik yuzasi topilmadi. `<threat_model>` ning beshala bandi qoplandi:

| Threat | Qoplandi |
|---|---|
| T-05-23 (DoS, ulkan poligon) | `zone_max_vertices` (DB `CHECK` i bilan chegaralangan) + `zone_max_per_camera`; ikkalasi ham serverda, `test_zone_limit_is_enforced_server_side` |
| T-05-24 (`market_id` tanadan) | Maydon sxemada **umuman e'lon qilinmagan**; `test_market_id_in_body_is_ignored` qatorning A bozoriga yozilishini o'lchaydi |
| T-05-25 (cross-tenant oshkorlik) | Har amal 404; `test_cross_tenant_zone_returns_404` javob **TANASINI** ham solishtiradi |
| T-05-26 (o'tmishdagi poligon) | Versiyalash; `test_old_version_survives_edit` poligonning **o'zini** ham solishtiradi |
| T-05-27 (kesishgan poligon) | `validate_polygon()`; S1 bilan to'rt testda o'lchandi |

⚠ Bitta **yangi** (rejada nomlanmagan) yuza qayd etildi va u deviatsiya #7 da: bitta `PUT` payloadida bir rastani ikki marta yuborish orqali **bir kamerada ikki faol kontur** yasash yo'li. DB konstrayti uni ushlamaydi (ikkala qator ham yangi va turli `version` oladi); router darvozasi bilan yopildi va test bilan qulflandi.

## Self-Check: PASSED

- Yaratilgan 5 + o'zgartirilgan 13 fayl — **hammasi diskda mavjud** (`git diff --name-only 72fdf7e..HEAD` bilan tasdiqlandi, **18 fayl**)
- `56a5a6b`, `f33b899`, `d799726`, `5afadf7` — **to'rtala commit ham `git log` da mavjud**
- Sabotajlardan keyin to'liq to'plam qayta yugurtirildi: **2032 o'tdi, 0 nosoz**; `ruff` + `mypy` toza; `git status` **toza** (birorta sabotaj artefakti qolmadi)
- `STATE.md` va `ROADMAP.md` **TEGILMAGAN** (orkestrator talabi)

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
