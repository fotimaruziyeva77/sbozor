---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 15
subsystem: testing
tags: [phase-gate, rbac, gate-threshold, human-uat, validation-signoff, requirements, occupancy, blind-audit]

requires:
  - phase: 05-01..05-14
    provides: "Zona registri va API, cv-service detektor yadrosi, detect job, noaniq navbat, ko'r audit, agregatsiya va kun yopilishi, to'rtta frontend yuzasi"
  - phase: 04-snapshot-pipeline
    provides: "`test_phase4_criteria.py` shakli (mezon boshiga bitta test + meta-test + mock'siz o'lchov), `04-HUMAN-UAT.md` shakli, 900 s `gate` chegarasi va uning OCHIQ bandi (D-26)"
provides:
  - "`tests/integration/test_phase5_criteria.py` — beshala ROADMAP mezoni BITTA buyruqda, uch meta-darvoza bilan"
  - "Dalil-kadr huquq bo'shlig'ining YOPILISHI: `GET /snapshots/{id}/image` endi `CAMERA_VIEW` YOKI `OCCUPANCY_REVIEW` ostida"
  - "`require_any_permission()` — «yo P, yo Q» darvozasi, ALOHIDA introspektsiya tegi bilan"
  - "`gate` byudjeti 900 s -> 1250 s, TINCH XOSTDAGI uch o'lchov asosida (W0-13/D-26 yopildi)"
  - "`05-HUMAN-UAT.md` — sakkiz band, har birida ega va tetik"
  - "`05-VALIDATION.md` imzosi: 45 Per-Task qatori, 14 Wave 0 bandi, `nyquist_compliant` skript bilan hisoblangan"
  - "AI-01/03/04/05/06 -> `Done` dalil bilan; AI-02 -> `Blocked` sabab, ega va tetik bilan"
affects: [phase-06-billing, phase-08-reports, verify-work]

tech-stack:
  added: []
  patterns:
    - "«Yo P, yo Q» huquq darvozasi: `require_any_permission()` + KO'PLIKDAGI introspektsiya tegi (`required_any_permissions`), `required_permission` QO'YILMAYDI"
    - "Ruxsat etilgan huquqlar to'plami darvozada IKKINCHI marta yoziladi (import qilinMAYDI) — aks holda darvoza o'z tekshirayotgan qiymatini tekshirardi"
    - "Mezon modulida aniqlik metrikasi NOMI `ast` daraxtidan taqiqlanadi (matn skani emas — docstringning o'zi qizartirardi)"
    - "Soxtalashtirish darvozasi IKKI yo'ldan: import daraxti VA `inspect.signature` fixture skani"

key-files:
  created:
    - tests/integration/test_phase5_criteria.py
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-HUMAN-UAT.md
  modified:
    - services/core-api/app/deps.py
    - services/core-api/app/api/v1/snapshots.py
    - tests/tenancy/test_personal_data_coverage.py
    - tests/integration/test_snapshot_api.py
    - frontend/src/lib/review-queries.ts
    - package.json
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-VALIDATION.md
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-UI-SPEC.md
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/deferred-items.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Dalil-kadr huquq bo'shlig'i TUZATILDI, to'rtinchi marta kechiktirilmadi: faza mezoni «nazoratchi kadrdan baholaydi» deganda, ekranning asosiy boshqaruvi o'z foydalanuvchisida 403 berib turgan holda fazani yopib bo'lmasdi"
  - "Kengaytma AYNAN BITTA marshrutda: `ROLE_PERMISSIONS[INSPECTOR]` ga `CAMERA_VIEW` qo'shish (butun kuzatuv yuzasi ochilardi) va `SnapshotViewerDep` ni bo'shatish (to'rtta marshrut) — ikkalasi ham rad etildi va sababi kodda yozildi"
  - "`required_permission` tegi «yo P, yo Q» darvozasiga QO'YILMADI: qo'yilsa struktura skanerlari «CAMERA_VIEW majburiy» deb yolg'on gapirardi — bu fazaning to'qqiz rejasi topgan nosozlik sinfining aynan o'zi"
  - "`gate` chegarasi 900 -> 1250 s ga KO'TARILDI, LEKIN jimgina emas: sabab o'lchangan (cv:lint + cv:test qo'shildi, to'plam o'sdi), tinch xost ta'minlandi va uchala o'lchov ham alohida yozildi"
  - "AI-02 `Done` EMAS, `Blocked`: talab matnidagi birinchi jumla («detektor har zonani baholaydi») CI'da real ONNX artefakti bilan bajarilmaydi va modelning aniqligi umuman o'lchanmagan"
  - "UI-SPEC §11.6 (D-16 qatori) va §11.7 (DL-5 per-slot jadvali) TUZATILDI — spetsifikatsiya qurilmagan narsani ta'riflab tursa, keyingi faza uni yo'qolgan funksiya deb o'qiydi"
  - "`occupancy_day_close_markets()` va `audit_draw_due_markets()` SAQLANADI — Rule 4; qaror 6-fazaning billing tikida ma'lumot bilan qabul qilinadi"

patterns-established:
  - "Faza darvozasining uchinchi meta-testi: modul o'z qamrovidan tashqaridagi DA'VONI (aniqlik metrikasi) yozmasligi `ast` bilan qulflanadi"
  - "Sabotaj o'lchovi test KUCHAYTIRISHIGA olib keladi: birinchi shaklda hech nima qizarmasa, test emas — DA'VO toraytiriladi yoki holat kengaytiriladi"
  - "O'lchov SHARTI natijaning bir qismi: `docker ps`, `docker system df` va xost diski o'lchovdan OLDIN yoziladi"

requirements-completed: [AI-01, AI-03, AI-04, AI-05, AI-06]

duration: 235min
completed: 2026-08-10
---

# Phase 5 Plan 15: Faza darvozasi, `gate` byudjeti va yakunlash Summary

**Beshala ROADMAP mezoni bitta `pytest` buyrug'ida o'lchanadigan bo'ldi; nazoratchining dalil kadriga bo'lgan uch reja davomida ochiq turgan 403 i AYNAN BITTA marshrut darvozasini kengaytirish bilan yopildi; `gate` byudjeti 4-fazadan meros ochiq band sifatida tinch xostda uch marta o'lchanib 900 s dan 1250 s ga ko'tarildi.**

## Performance

- **Duration:** ~235 min
- **Started:** 2026-08-09T23:20Z
- **Completed:** 2026-08-10T03:15Z
- **Tasks:** 3 (+1 rejadan tashqari, deviatsiya)
- **Files modified:** 12 (2 yangi)

## Accomplishments

- **`tests/integration/test_phase5_criteria.py`** — beshta mezon, har biriga AYNAN BITTA test, **uch meta-darvoza** bilan. Baza HAQIQIY `postgres:18.4`, marshrutlar HAQIQIY FastAPI grafi, soxtalashtirish YO'Q.
- **Dalil-kadr huquq bo'shlig'i YOPILDI** — sof `inspector` endi kadrni ko'radi (200 + baytlar teng), kadr metama'lumoti va kun jurnali esa unga YOPIQ QOLADI (403). Ikki MUSTAQIL darvoza: struktura (marshrut grafi) va xulq (HTTP).
- **W0-13/D-26 yopildi** — uch o'lchov tinch xostda: **1009 / 1004 / 983 s**, tarqoqlik 26 s. Nazorat o'lchovi `gate:fast` **87 s** (chegara 180 s). Yangi chegara **1250 s**.
- **`05-HUMAN-UAT.md`** — sakkiz band, birinchisi **detektorning aniqligi** va u ochiq «o'lchanmagan» deb turadi.
- **UI-SPEC ning ikki eskirgan bo'limi tuzatildi** (§11.6 D-16 qatori, §11.7 DL-5 per-slot jadvali) va §12.6 shipping copy bilan moslandi.
- **Talablar dalil bilan belgilandi**: AI-01/03/04/05/06 `Done`, AI-02 `Blocked`.

## Task Commits

1. **Deviatsiya (Rule 2): dalil-kadr huquq bo'shlig'i** — `d571026` (fix)
2. **Task 1: `test_phase5_criteria.py`** — `a01d9db` (test)
3. **Task 3 (a qismi): UI-SPEC, UAT, deferred-items, REQUIREMENTS** — `460920c` (docs)
4. **Task 2: W0-13 — `gate` byudjeti** — `98865e1` (chore)

**Plan metadata:** quyida (docs: complete plan)

## Files Created/Modified

- `tests/integration/test_phase5_criteria.py` *(yangi, 1287 qator)* — beshta mezon + 4 meta/nazorat testi
- `.planning/phases/05-.../05-HUMAN-UAT.md` *(yangi)* — 8 band, har birida ega va tetik
- `services/core-api/app/deps.py` — `require_any_permission()` fabrikasi
- `services/core-api/app/api/v1/snapshots.py` — `EVIDENCE_FRAME_PERMISSIONS`, `EvidenceFrameViewerDep`, marshrut dekoratori
- `tests/tenancy/test_personal_data_coverage.py` — `required_any_permissions()` o'quvchisi, `EVIDENCE_FRAME_ALLOWED` yopiq to'plami, kengayish chegarasi testi
- `tests/integration/test_snapshot_api.py` — `inspector_headers` fixture'i + ikki xulq testi
- `frontend/src/lib/review-queries.ts` — 403 haqidagi ESKIRGAN izoh tuzatildi
- `package.json` — `//gate-budget` va `//gate-fast-budget` izohlari
- `.planning/phases/05-.../05-VALIDATION.md` — frontmatter, 45 Per-Task qatori, 14 W0 bandi, byudjet bo'limi, imzo
- `.planning/phases/05-.../05-UI-SPEC.md` — §11.6, §11.7, §12.6, M-8
- `.planning/phases/05-.../deferred-items.md` — to'rtala bandning qarori
- `.planning/REQUIREMENTS.md` — AI-01…AI-06 dalil bilan
- `.planning/ROADMAP.md` — 05-15 belgilandi, progress qatori 15/15

## Decisions Made

### 1. ⛔ Dalil-kadr bo'shlig'i — TO'RTINCHI marta kechiktirilmadi

05-10 topdi, 05-11 yozdi, 05-13 **qayta o'lchadi** — va uchalasi ham M-8 («bu fazada RBAC tegilmaydi») bilan qoldirdi. Bu reja fazaning YOPILISHI, ya'ni M-8 endi qalqon emas: mezonlari «nazoratchi kadrdan baholaydi» deyilgan fazani ekranning asosiy boshqaruvi sof nazoratchida **403** berib turgan holda yopib bo'lmasdi.

**Tanlangan yechim va rad etilgan ikkitasi kodda yozildi:**

| Variant | Narxi | Qaror |
|---|---|---|
| `ROLE_PERMISSIONS[INSPECTOR]` ga `CAMERA_VIEW` | Bitta qator, LEKIN nazoratchiga kamera reestri, jonli tasvir, NVR ro'yxati va kadr arxivi ochilardi | ⛔ rad |
| `SnapshotViewerDep` ni bo'shatish | 05-13 o'lchagan (b) varianti — kun jurnali va kadr metama'lumoti ham ochilardi | ⛔ rad |
| **FAQAT `/image` marshruti «yo P, yo Q» ga** | Yangi `Permission` YO'Q, `ROLE_PERMISSIONS` TEGILMAYDI | ✅ tanlandi |

⚠ **Introspektsiya tegi KO'PLIKDA (`required_any_permissions`) va `required_permission` QO'YILMADI.** Qo'yilsa struktura skanerlari (`required_permissions()`) «bu marshrut `CAMERA_VIEW` TALAB QILADI» deb o'qirdi, holbuki u endi MAJBURIY emas — ya'ni darvoza o'z da'vosidan boshqa narsani o'lchay boshlardi. Bu fazaning to'qqizta rejasi topgan nosozlik sinfining aynan o'zi.

⚠ **Ruxsat etilgan to'plam darvozada IKKINCHI marta yozildi** (`EVIDENCE_FRAME_ALLOWED`), mahsulot konstantasidan **import qilinmadi**: import qilingan darvoza o'z tekshirayotgan qiymatini tekshirardi va mahsulotga uchinchi huquq qo'shilsa **jimgina kengayardi**.

### 2. `gate` chegarasi KO'TARILDI — va sabab o'lchangan

4-faza chegarani ko'tarmagan edi, chunki o'lchov **ifloslangan** edi (xostda ikkinchi Docker steki). Bugun stek `docker stop` bilan to'xtatildi va o'lchovdan keyin tiklandi; uchala o'lchov ham `docker ps` da faqat `sbozor-*` ko'rinib turgan holatda olindi.

Ko'tarishning sababi degradatsiya EMAS: zanjirga `cv:lint` + `cv:test` qo'shildi (05-02) va `tests` to'plami o'sdi. Buni **uch o'lchovning bir-biriga yaqinligi** (tarqoqlik 2,6 %) va **`gate:fast` nazorati** (87 s — 04-14 dagi ifloslangan 129 s dan farqli o'laroq, o'sgan ish hajmida) tasdiqlaydi.

### 3. AI-02 `Blocked` — `Done` emas

Talab matnining **ikkinchi jumlasi** to'liq o'lchangan (o'zgarmaslik, alohida yozuv, confidence). **Birinchi jumlasi** — «RF-DETR ONNX Runtime CPU da har zonani baholaydi» — CI'da **real artefakt bilan bajarilmaydi**, modelning aniqligi esa oltin to'plam bo'shligi uchun **umuman o'lchanmagan**. CAM-02 ning aynan shakli: sabab, ega, tetik va band nomlangan.

### 4. Ikki `SECURITY DEFINER` funksiya SAQLANADI (Rule 4)

`audit_draw_due_markets()` va `occupancy_day_close_markets()` chaqiruvchisiz. **O'lchandi:** ikkalasining ham yuzasi tor (`market_id` + son), tenant ma'lumoti yo'q va `FORBIDDEN_SURFACE_TOKENS` darvozasi bilan qulflangan. Tushirish yangi migratsiya talab qiladi (bu rejaning fayl ro'yxatida yo'q) va — muhimi — **qaror uchun ma'lumot hali yetarli emas**: 6-fazaning billing tiki ularni yo ishlatadi, yo `business_date` argumentli shaklga ko'chiradi, yo tushiradi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Dalil-kadr huquq bo'shlig'i (rejadan TASHQARI ish)**

- **Found during:** Task 1 dan oldin — orkestrator topshirig'i va `deferred-items` / `05-13-SUMMARY` ning `threat_flag` i
- **Issue:** `GET /snapshots/{id}/image` `CAMERA_VIEW` talab qilardi; `ROLE_PERMISSIONS[INSPECTOR]` esa aynan `{OCCUPANCY_REVIEW}`. Sof nazoratchi navbat bandini olardi, dalilni esa **403** bilan ololmasdi — ya'ni AI-03 va AI-04 ning oxirgi qadami o'z foydalanuvchisida bajarilmasdi
- **Fix:** `require_any_permission()` fabrikasi + `EVIDENCE_FRAME_PERMISSIONS` + AYNAN BITTA marshrutning dekoratori va imzo aliasi
- **Files modified:** `deps.py`, `snapshots.py`, `test_personal_data_coverage.py`, `test_snapshot_api.py`, `review-queries.ts`
- **Verification:** ⬇ pastdagi sabotaj jadvali (S-A/S-B/S-C)
- **Committed in:** `d571026`

**2. [Rule 1 - O'lchangan ziddiyat] SC#4 ning birinchi shakli sabotajni O'TKAZIB YUBORDI**

- **Found during:** Task 1 ning sabotaj o'lchovi
- **Issue:** SC#4 dastlab **bitta** ko'r audit bandini javoblab, keyin noaniq navbatiga javob yozib «hisobot o'zgarmadi» deb o'lchardi. `accuracy_report.py:396` dagi `and` -> `or` sabotaji darvozani **umuman qizartirmadi**: noaniq navbatidagi javobda ikkala shart ham (`purpose='train'`, `queue_kind='uncertain'`) yolg'on, ya'ni `or` ham uni chetda qoldirardi. Test filtrning IKKI shartini emas, faqat bittasini o'lchayotgan edi
- **Fix:** Test KUCHAYTIRILDI — endi BUTUN namuna javoblanadi (70/30 kvota `eval` ham, `train` ham beradi) va hisobotdagi son `eval` lar soniga **TENG** bo'lishi talab qilinadi. Ajratuvchi holat ko'r namunaning ICHIDA: `queue_kind='blind_audit'` + `purpose='train'` qatorlari `or` ostida hisobotga TUSHARDI
- **Files modified:** `tests/integration/test_phase5_criteria.py`
- **Verification:** Kuchaytirilgandan keyin S-D sabotaji SC#4 ni qizartirdi (drawn=4, eval=3, train=1)
- **Committed in:** `a01d9db`

**3. [Rule 1 - Bug] `frontend/src/lib/review-queries.ts` dagi izoh YOLG'ON bo'lib qoldi**

- **Found during:** Deviatsiya 1 dan keyin
- **Issue:** Izoh «rasm marshruti `CAMERA_VIEW` talab qiladi... tuzatish bu yerda bajarilmadi» deb turardi — tuzatishdan keyin bu **yolg'on** bo'ldi
- **Fix:** Izoh 403 ning YANGI sabablarini (huquqsiz rol, begona bozor, bloklangan hisob) sanaydi va xulqning o'zgarmaganini aytadi
- **Files modified:** `frontend/src/lib/review-queries.ts`
- **Verification:** `npm --prefix frontend test` — vitest 620, node 144
- **Committed in:** `d571026`

**4. [Rule 3 - Blocking] `05-VALIDATION.md` ning `05-15/T3` qatorida buyruq buzuq edi**

- **Found during:** Task 3
- **Issue:** Qatorning `Automated Command` katagiga rejaning `how-to-verify` matni tushib qolgan edi (`` ` `` bilan boshlanadigan siniq bo'lak). `check-validation-signoff.mjs` uni «to'ldirilgan» deb sanardi, lekin u **bajarib bo'lmaydigan** matn edi
- **Fix:** Katak `npm run validation:check && npm run requirements:check` bilan almashtirildi
- **Files modified:** `.planning/phases/05-.../05-VALIDATION.md`
- **Verification:** `npm run validation:check` → «hisob-kitob bilan MOS»
- **Committed in:** `98865e1`

---

**Total deviations:** 4 auto-fixed (1 missing-critical, 2 bug/o'lchangan ziddiyat, 1 blocking)
**Impact on plan:** Deviatsiya 1 fazaning **yopilish sharti** edi va u rejaning `files_modified` ro'yxatidan tashqarida; qolgan uchtasi tuzatish. Scope creep yo'q — RBAC matritsasi (`ROLE_PERMISSIONS`) va migratsiyalar **tegilmadi**.

## Sabotaj o'lchovlari — nima QIZARDI va nima QIZARMADI

| # | Sabotaj | Kutilgan | Natija |
|---|---|---|---|
| **S-A** | `EVIDENCE_FRAME_PERMISSIONS` ni `(CAMERA_VIEW,)` ga qaytarish | Xulq testi qizaradi | ✅ **1 test qizardi** — `test_a_pure_inspector_can_open_the_evidence_frame` (403). Struktura darvozasi YASHIL qoldi va bu **to'g'ri**: u boshqa da'voni o'lchaydi |
| **S-B** | Mahsulot to'plamiga `PAYMENT_CREATE` qo'shish | Struktura darvozasi qizaradi | ✅ **1 test qizardi** — `test_binary_personal_routes_declare_read_audit_and_permission` |
| **S-C** | Kengaytmani qo'shni marshrutga (kadr detali) oqizish | IKKALASI ham qizaradi | ✅ **2 test qizardi** — struktura (`..._widening_stops_at_the_image_route`) VA xulq (`test_the_inspector_gate_stops_at_the_frame`), ya'ni ular MUSTAQIL |
| **S-D** | `accuracy_report.py:396` `and` -> `or` | SC#4 qizaradi | ⛔ **BIRINCHI SHAKLDA HECH NIMA QIZARMADI** (yuqoridagi deviatsiya 2). Test kuchaytirilgandan keyin ✅ SC#4 qizardi |
| **S-E** | Agregatsiya ustuvorligini teskari qilish (`empty` eng kuchli) | SC#5 qizaradi | ✅ **1 test qizardi** — `test_sc5_...` |
| **S-F** | Oltinchi `test_sc3_*` funksiyasini qo'shish | Meta-test qizaradi | ✅ **1 test qizardi** — `test_every_criterion_has_its_own_test` («SC#3 uchun 2 ta test topildi») |
| **S-G** | `monkeypatch` ni SC#5 imzosiga qo'shish | Soxtalashtirish darvozasi qizaradi | ✅ **1 test qizardi** — `test_criteria_module_uses_no_fakes` |

⚠ **S-D ning darsi bu fazaning naqshiga qo'shiladi:** sabotaj **sistemaga yetib bordi** (`or` haqiqatan bajarildi), lekin **hech bir test ikki holatni ajrata olmasdi** — chunki test tanlagan MA'LUMOT ikkala shoxda ham bir xil natija berardi. Tuzatish testni emas, **holatni** kengaytirish bo'ldi.

## Halollik ko'rigi (Task 3, 5-qadam — QO'LDA)

`05-*-SUMMARY.md` (14 fayl) va `05-VALIDATION.md` ketma-ket o'qildi. **Detektorning aniqligi haqida raqamli da'vo TOPILMADI.**

Ikkita nomzod ko'rildi va ikkalasi ham **saqlandi**, sababi bilan:

1. `05-01-SUMMARY.md:53` — «0.90 qo'yilsa HAQIQATAN 95 % aniq model minimal namunada o'ta olmasdi». Bu **RF-DETR haqida da'vo EMAS** — u Wilson oralig'i chegarasining tanlanishi haqidagi statistik mulohaza va u `05-RESEARCH.md` §C.8.4 jadvaliga havola qiladi. Havolasi bor → qoladi.
2. Kechikish raqamlari (74 ms / 180 ms, Intel benchmarklaridan) — birorta SUMMARY da **umuman uchramaydi**. `05-HUMAN-UAT.md` #3 ularni ochiq «da'vo sifatida ishlatilmaydi» deb belgilaydi.

⚠ **Bu qadam ATAYIN qo'lda bo'ldi** (reja shunday talab qiladi): avtomatik matn skani reja va tadqiqot hujjatlaridagi **tushuntirish** iqtiboslarini ham ushlab, o'zini o'zi qizartirardi. Lekin qamrovning bir qismi endi MEXANIK ham: `test_the_criteria_module_claims_no_accuracy_number` mezon modulida `precision`/`recall`/`f1`/`map` **nomlarini** `ast` daraxtidan taqiqlaydi (matndan emas — o'sha testning O'Z docstringi «accuracy» so'zini ishlatadi).

## Issues Encountered

1. **`shown_ai_verdict` — `bool`, verdikt NUSXASI emas.** SC#2 birinchi shaklda uni verdikt satri deb o'qidi va `assert 'False' == 'uncertain'` bilan yiqildi. Tuzatish: ustunning **haqiqiy ma'nosi** («AI javobi javobdan OLDIN ko'rsatildimi?») bo'yicha assert yozildi — noaniq navbatda ham u `false`, chunki tizim javobi faqat javobdan keyin oshkor bo'ladi (D-17.3).
2. **`build_uncertain_queue()` ning qaytargan soni navbat HAJMI emas.** Seed kunni allaqachon bitta javobsiz topshiriq bilan beradi (AI-06 kirish holati), ya'ni funksiya faqat YANGI qatorni yozadi va `1` qaytaradi. Ustuvorlik navbatning **to'liq tarkibida** o'lchanadigan bo'ldi.
3. **Aniqlik hisobotining standart 30 kunlik oynasi seed kunini qamramaydi.** `SEED_BUSINESS_DATE` (2026-09-01) bugundan KEYIN, ya'ni standart oyna bo'sh hisobot berardi va test **jimgina yashil** bo'lardi. `test_occupancy_report.py` da o'rnatilgan naqsh qayta ishlatildi: davr aniq berildi.
4. **Zona versiyalarining to'qnashuvi.** `add_zone_with_event()` standart `version=1` bilan yozadi, seed esa birinchi rastada 1 va 2 ni band qilgan. Har testda ajralgan versiya diapazoni ishlatildi (5 / 20+ / 30+).

## Known Stubs

Yo'q. Bu reja birorta stub qo'shmadi va birorta bo'sh ekran/placeholder yaratmadi.

⚠ **Fazadagi ochiq bandlar stub EMAS va ular NOMLANGAN:**

| Band | Holati | Kimga |
|---|---|---|
| D-16 (nazoratchining ichki mosligi) | Strukturaviy imkonsiz — **qurilmadi**, spetsifikatsiyadan olib tashlandi, i18n kaliti yozilmadi | Kelajakdagi qaror |
| DL-5 per-slot qatorlari | Marshrut yo'q — **qurilmadi**, §11.7 tuzatildi | 8-faza |
| `fast_decision_ms` maydoni | Javobda yo'q — chegara yorliqda **nomlanmaydi**, §12.6 tuzatildi | 8-faza |
| Ikki `SECURITY DEFINER` funksiya | Chaqiruvchisiz, yuzasi tor va darvoza bilan qulflangan | 6-faza |

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-73 (repudiation: «faza tugadi» da'vosi) | mitigate | Beshala mezon **bitta buyruqda**; meta-test mezon sonini `range(1,6)` bo'yicha qulflaydi (S-F bilan qizartirildi); fazani yopish qarori qayta tekshiruvda qoldi — `ROADMAP.md` dagi belgi hamon `- [ ]` |
| T-05-74 (tampering: soxta aniqlik da'vosi) | mitigate | Qo'lda halollik ko'rigi bajarildi va natijasi yuqorida; MEXANIK qatlam qo'shildi (`test_the_criteria_module_claims_no_accuracy_number`); `05-HUMAN-UAT.md` #1 va oltin to'plam darvozasi uxlab yotibdi |
| T-05-75 (tampering: mezon modulida soxtalashtirish) | mitigate | IKKI mustaqil yo'l — `ast` import daraxti VA `inspect.signature` fixture skani (`monkeypatch`/`enqueued`/`respx_mock`); ikkalasida ham BO'SH to'plam qo'riqchisi bor; «o'tkazib yuborish» yo'li yo'q. S-G bilan qizartirildi |
| T-05-76 (repudiation: `gate` byudjetining jimgina siljishi) | mitigate | Uch o'lchov + nazorat o'lchovi + **o'lchov sharti** (`docker ps`, `docker system df`, xost diski) yozildi; o'rtachaga aylantirilmadi; chegara `package.json` va `05-VALIDATION.md` da BIR XIL |

## Threat Flags

Yo'q. Bu reja yangi tarmoq endpointi, yangi sxema yoki yangi fayl kirish yo'lini **ochmadi**. Yagona xavfsizlik yuzasi o'zgarishi — mavjud marshrutning darvozasi — **toraytirilgan holda** kengaytirildi va ikki mustaqil test bilan chegaralandi.

⚠ **05-13 ning `threat_flag: authorization-gap` bayrog'i YOPILDI.**

## Verification

| Buyruq | Natija |
|---|---|
| `pytest tests/integration/test_phase5_criteria.py -q` | ✅ **9 passed** (5 mezon + 4 meta/nazorat) |
| `docker compose --profile test run --rm tests pytest -q` | ✅ **2372 test** yig'iladi, hammasi o'tadi |
| `docker compose --profile test run --rm cv-tests pytest -q` | ✅ **130 test** |
| `tests/tenancy` | ✅ **549 test** (bazadan +1: kengayish chegarasi testi) |
| `npm --prefix frontend test` | ✅ vitest **620**, `node --test` **144** |
| `npm --prefix frontend run i18n:check` | ✅ **980 kalit × 3 til** |
| `npm run gate` | ✅ exit 0 — **uch marta TINCH XOSTDA** (1009 / 1004 / 983 s), yangi chegara **1250 s** |
| `npm run gate` (yakuniy, `parnikkpi` TIKLANGANDAN keyin) | ✅ exit 0 — **1015 s**, chegara ichida. ⚠ Chegara asosiga KIRMAYDI; u boshqa savolga javob beradi va javob qiziq: ikkinchi stek tiklangach farq **+0,6 %**, holbuki `04-14` da ayni shu stek **+30 %** bergan edi — ya'ni «boshqa stek bor» yolg'iz o'zi hali ifloslanish DEMAKMAS |
| `npm run gate:fast` | ✅ exit 0 — **87 s** (chegara 180 s) |
| `npm run validation:check` | ✅ `nyquist_compliant: true` — hisob-kitob bilan MOS (45 qator, 5 inson bandi) |
| `npm run requirements:check` | ✅ 49 talab MOS — Done 21 · Pending 26 · Blocked 2 |
| `ruff check && ruff format --check && mypy` | ✅ toza (289 fayl, 279 manba) |

⚠ **`cv` to'plamining bazasi 93 emas, 130.** Topshiriqdagi «cv 93» soni eskirgan (05-07/05-08 uni o'stirgan); bu reja `services/cv-service/` ga **umuman tegmadi** va buni `git diff --name-only` tasdiqlaydi.

## User Setup Required

Yo'q — tashqi xizmat sozlamasi talab qilinmaydi.

⚠ **LEKIN `05-HUMAN-UAT.md` ning 8 bandi kutmoqda** va ulardan uchtasi ops ishi (ONNX artefaktini eksport qilish, real kadrlarni yig'ish, atama ko'rigi). Ular fazani **bloklamaydi** (self-service direktivasi), lekin ularsiz «detektor to'g'ri ishlaydi» degan da'vo **berilmagan** bo'lib qoladi.

## Next Phase Readiness

**6-faza (billing) uchun tayyor:**

- `stall_slot_occupancy` kun bo'yicha materializatsiya qilinadi va `resolution_source` to'rt manbani ajratadi (`ai` / `human` / `default_empty` / `no_coverage`) — BILL-01 ning «kamida 2 snapshotda band» sharti uchun kirish ma'lumoti tayyor;
- `occupancy_events` ↔ `snapshots` kompozit FK (D-21 langari) yaroqsiz kadrga hisob yozilishini **DB darajasida** rad etadi;
- dalil-kadr marshruti endi ikkala rol uchun ham ochiq, ya'ni BILL-02 ning «har hisob yozuvidan dalil-kadrlarga o'tish» talabi yangi huquq yuzasi ochmaydi.

**Ochiq bandlar (bloklamaydi, lekin nomlangan):**

- **AI-02 `Blocked`** — real ONNX artefakti va oltin to'plam kutilmoqda. 6-faza bandlik MA'LUMOTIGA tayanadi, uning ANIQLIGIGA emas, ya'ni bu bog'liqlik emas — **sifat riski**;
- ikki `SECURITY DEFINER` funksiyaning taqdiri 6-fazaning billing tikida hal bo'ladi;
- `npm run gate` endi ~17 daqiqa. 6-faza yana bosqich qo'shsa, byudjet qayta o'lchanishi kerak — **bu safar sabab bilan**, jimgina emas.

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-10*

## Self-Check: PASSED

Fayllar (5/5 mavjud): `tests/integration/test_phase5_criteria.py`,
`05-HUMAN-UAT.md`, `05-15-SUMMARY.md`, `services/core-api/app/deps.py`,
`services/core-api/app/api/v1/snapshots.py`.

Commitlar (4/4 mavjud): `d571026`, `a01d9db`, `460920c`, `98865e1`.
