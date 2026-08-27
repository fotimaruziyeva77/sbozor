---
phase: 04-snapshot-pipeline
plan: 12
subsystem: faza-darvozasi
tags: [phase-gate, meta-test, mock-free, threshold, requirements, human-uat, sentry, found-06]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 11
    provides: "`capture-cell.tsx` (G-7), `capture-grid.tsx`, `alert-list.tsx` — SC#2 ning UI isboti"
  - phase: 04-snapshot-pipeline
    plan: 09
    provides: "`GET /capture-runs`, `GET /snapshots/{id}/image` (`audit_read`), `/internal/self-check`"
  - phase: 04-snapshot-pipeline
    plan: 08
    provides: "`retention_daily(today=)`, `alert_sweep(now=)`, `AlertSender`, `ops/docs/monitoring.md`"
  - phase: 04-snapshot-pipeline
    plan: 07
    provides: "`capture_tick`/`capture_batch`, `FrameSourcePool`, holatsiz planer"
  - phase: 04-snapshot-pipeline
    plan: 06
    provides: "`SnapshotStorage` (haqiqiy SeaweedFS) va `test_storage_layout_uses_no_mock` naqshi"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 14
    provides: "`test_phase3_criteria.py` — meta-test va mock'siz o'lchov darvozasining SHABLONI"
provides:
  - "`tests/integration/test_phase4_criteria.py` — SC#1…SC#5 uchun aynan bitta nomlangan test + meta-test + mock'siz o'lchov darvozasi"
  - "`services/core-api/app/observability.py` — Sentry ilmoqlari va `init_sentry()`; IKKALA jarayon uchun"
  - "`04-HUMAN-UAT.md` — qo'lda tekshiriladigan oltita band, ega va tetik bilan"
  - "`04-VALIDATION.md` — 36/36 yashil, Wave 0 ning 12 bandi yopiq, `nyquist_compliant: true` HISOBLANGAN"
  - "`npm run gate` chegarasi: 1200 s -> **900 s** (olti o'lchov asosida)"
  - "`tests/tenancy/test_personal_data_coverage.py` — BAYT javobli marshrutlarning yopiq tasnifi"
affects: [05-cv-zonalar, 06-billing, 08-hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Faza darvozasi UCH mustaqil qulf bilan quriladi: mezon boshiga bitta test · meta-test (bittasi jimgina tushib qolmasin) · mock'siz o'lchov. Uchtasi ham sabotaj bilan o'lchanadi"
    - "Mezon testi MEXANIZMNI emas, MAHSULOT DA'VOSINI o'lchaydi — mavjud testlar takrorlanmaydi, ular zanjir sifatida bog'lanadi"
    - "RED bosqichi «testni yozish» emas, O'LCHOV: bu yerda u ishlab chiqarishdagi haqiqiy bo'shliqni ochdi (worker jarayonida Sentry umuman o'rnatilmasdi)"
    - "Darvozaning quyi chegarasi (`>= N ta test`) mezon testining IKKINCHI, mustaqil qulfi bo'lib chiqadi — sabotaj buni ko'rsatdi"
    - "Bayt qaytaradigan marshrutlar uchun YOPIQ tasnif: har `response_model` siz `GET` ikki ro'yxatdan birida bo'lishi SHART, ya'ni «unutish» yo'li yopiq"
    - "Chegara O'RTACHA bilan emas, ENG YOMON o'lchov bilan belgilanadi — o'rtacha sovuq yugurishni har safar qizartirib, darvozani shovqinga aylantirardi"

key-files:
  created:
    - tests/integration/test_phase4_criteria.py
    - services/core-api/app/observability.py
    - .planning/phases/04-snapshot-pipeline/04-HUMAN-UAT.md
  modified:
    - services/core-api/app/main.py
    - services/core-api/app/worker.py
    - tests/unit/test_sentry_scrub.py
    - tests/tenancy/test_personal_data_coverage.py
    - tests/tenancy/test_snapshot_domain_meta.py
    - frontend/src/components/snapshots/capture-grid.test.tsx
    - compose.yaml
    - .planning/phases/04-snapshot-pipeline/04-VALIDATION.md
    - .planning/phases/04-snapshot-pipeline/04-UI-SPEC.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
  deleted: []

key-decisions:
  - "SC#5 ning ikkinchi yarmi («xato Sentry'da ko'rinadi») RED bosqichida O'LCHANDI va U YOLG'ON CHIQDI: `sentry_sdk.init()` faqat API jarayonida chaqirilardi, kadr olish/saqlash/alert esa WORKER da ishlaydi. Testni bu banddan chetlab o'tish o'rniga MAHSULOT tuzatildi (Rule 2)"
  - "Ilmoqlar `app/main.py` dan `app/observability.py` ga ko'chirildi, `app.main` dan import QILINMADI — teskari yo'nalish aylanma bog'liqlik bo'lardi va butun FastAPI ilovasini worker jarayoniga tortib kelardi"
  - "`test_sentry_init_wires_both_hooks` darvozasi KUCHSIZLANTIRILMADI, KUCHAYTIRILDI: u endi `init_sentry` manbasini o'qiydi va yangi `test_both_processes_install_sentry` ikkala kirish nuqtasini talab qiladi"
  - "CAM-07 `Done` qilindi, `Blocked` emas: talab jumlasining MEXANIZMI haqiqiy SeaweedFS ustida o'lchangan; kalendar vaqti esa CI'da mavjud bo'lmagan SHOX emas, o'sha shoxning PARAMETRI — bu CAM-02 dan (CI'da `wg0` UMUMAN yo'q) tubdan farq qiladi"
  - "Chegara olti o'lchovning ENG YOMONI + 20 % bo'yicha: 745 -> 900 s. O'rtacha (591 s) 710 s berardi va u sovuq yugurishni HAR SAFAR qizartirardi"
  - "`04-01` ning uch o'lchovi (461–490 s) bilan bugungi uchtasi (691–745 s) BOSHQA to'plam ustida — farq yozildi, o'rtachaga aralashtirilmadi"
  - "Bayt javobli marshrutlar uchun ikki ro'yxat (shaxsiy / shaxsiy emas) va ular YOPIQ to'plam hosil qiladi — bitta ro'yxat birinchi unutilgan marshrutda jimgina eskirardi"
  - "`.planning/STATE.md` ATAYIN tegilmadi (reja mezonining talabi); uning Blockers/Concerns bandlarining yangi matni shu SUMMARY da, faza yopilish oqimi uchun"

patterns-established:
  - "Sabotaj natijasi UCH USTUNDA: nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi. Beshta sabotajdan ikkitasi bashoratdan KUCHLIROQ chiqdi va ikkalasi ham yangi topilma berdi"
  - "«Darvoza bor, lekin hech kim bosmaydi» sinfi: `npm run requirements:check` `03-14` dan beri qizil turgan va uni faqat shu reja chaqirgani uchun topildi"
  - "Markdown jadvalidagi buyruq ichidagi ustun ajratuvchisi skriptning ustun indeksini siljitadi — darvoza `Status` ustunini boshqa katakdan o'qib, JIMGINA noto'g'ri javob berardi"

requirements-completed: [CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06]

# Metrics
duration: 5h 20m
completed: 2026-08-05
---

# Phase 4 Plan 12: Faza darvozasi, chegara qarori va talab holatlari Summary

**Beshala faza mezoni endi BITTA buyruq bilan o'lchanadi va uchala darvozasi — mezon boshiga bitta test, meta-test, mock'siz o'lchov — sabotaj bilan tekshirilgan; RED bosqichi ishlab chiqarishdagi haqiqiy bo'shliqni ochdi (worker jarayonida Sentry umuman o'rnatilmasdi va FOUND-06 ning bir jumlasi shu sababdan yolg'on edi); `npm run gate` chegarasi olti o'lchov asosida 1200 s dan 900 s ga TUSHIRILDI; beshala talab dalil bilan `Done` va qo'lda tekshiriladigan oltita band ega hamda tetik bilan yozildi.**

## Performance

- **Duration:** ~5 soat 20 daqiqa (shundan ~42 daqiqa — to'rtta `gate` yugurishi)
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 3 ta yangi + 11 ta o'zgargan
- **Commits:** 5 ta (bittasi RED)

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 1 (RED) | `test_phase4_criteria.py` — 5 mezon + meta + mock darvozasi | `f42a1e9` |
| 1 (GREEN) | `app/observability.py` + worker'da `init_sentry()` | `2f85b35` |
| — (deviatsiya) | Oldingi rejalardan qolgan beshta ochiq band | `3aeaf90` |
| 3 | `REQUIREMENTS.md` + `ROADMAP.md` | `7d6074d` |
| 2 | `04-VALIDATION.md` + `04-HUMAN-UAT.md` | `3f9effe` |

⚠ Task 3 Task 2 dan OLDIN commit qilindi va sabab mexanik: Task 2 uchinchi
`gate` o'lchovini kutardi, Task 3 esa o'sha paytda allaqachon yashil edi
(«tasdiqlangan zahoti commit qil» qoidasi).

## ⛔ RED BOSQICHI NIMA TOPDI — bu rejaning eng muhim natijasi

`test_phase4_criteria.py` yozilib birinchi marta ishga tushirilganda
**AYNAN BITTA test qizardi** — `test_sc5` — va u aynan Sentry bandida
yiqildi (`ModuleNotFoundError: app.observability`). Telegram yarmi darhol
yashil bo'ldi (ikkita xabar: bozor + platforma, rasmsiz).

O'lchov ochgan haqiqat:

| Nima | Holat |
|---|---|
| `compose.yaml` `SENTRY_DSN` ni beradi | `core-api` ✅ · `worker` ✅ · `scheduler` ✅ |
| `sentry_sdk.init()` HAQIQATAN chaqiriladi | `core-api` ✅ · `worker` ❌ · `scheduler` ❌ |

Ya'ni **kadr olish** (`capture_batch`), **saqlash siyosati**
(`retention_daily`) va **alert supurgisi** (`alert_sweep`) — 4-fazaning
BUTUN ish qismi — worker jarayonida ishlaydi va ularning istisnolari
Sentry'ga **hech qachon** bormasdi. FOUND-06 ning «xatolar Sentry'da»
jumlasi aynan shu faza tug'diradigan xatolar uchun **yolg'on** edi.

⚠ **Nosozlik JIM:** `init()` chaqirilmasa `sentry_sdk` hech qanday xato
bermaydi — konteyner sog'lom, jurnal toza, hodisa esa jo'natilmaydi.
Buni birorta mavjud test ko'rsatmasdi.

**Qaror:** testni bu banddan chetlab o'tish (Sentry ni «qo'lda» deb
belgilash) mumkin edi va u soatlab tez bo'lardi. Lekin u talabni
`Done` qilib, keyingi to'rt fazani mavjud bo'lmagan kuzatuv ustiga
qurardi — 2-fazaning `02-VERIFICATION.md` da hujjatlashtirilgan
xatosining aynan takrori. Shuning uchun MAHSULOT tuzatildi (Rule 2).

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `test_sc3_...` -> `_test_sc3_...` (vaqtincha qayta nomlash) | **IKKI test**: `test_every_criterion_has_its_own_test` (SC#3 uchun 0 ta test) **VA** `test_criteria_module_uses_no_storage_mock` (haqiqiy omborga boradigan testlar 2 dan 1 ga tushdi) | **To'rtala qolgan mezon testi** — `sc1`, `sc2`, `sc4`, `sc5` | ⚠ **Bashoratdan KUCHLIROQ.** Reja «meta-testni AYNAN qizartiradi va qolgan to'rttasi yashil qoladi» degan edi — ikkalasi ham to'g'ri, lekin reja IKKINCHI qulfni sanamagan edi. **Yangi topilma quyida** |
| 2 | `test_snapshot_domain_meta.py` da yarim tun sharti takrorlandi (`now()+1 kun`) va `_anchor_today()` olib tashlandi | **AYNAN BITTA assertion** — «muddati KELMAGAN slotlari bor bozor qaytarildi» (650-qator), ya'ni `deferred-items.md` #1 dagi o'lchov bilan BIR XIL joyda | Faylning qolgan sakkiz testi | ✅ **Aynan bashorat qilingandek** — langar qator load-bearing ekani isbotlandi va nosozlik oynasi NOLGA tushdi |
| 3 | `capture-cell.tsx` `missed` holati uchun hech nima chizmaydi (`return null`) | **YETTI test**: `capture-cell.test.tsx` ning beshtasi **VA `capture-grid.test.tsx` ning IKKITASI** | `capture-grid` ning qolgan 13 tasi, shu jumladan `buildMatrix` ning `missed` testi (u sof funksiya — render qilmaydi) | ✅ **Aynan bashorat qilingandek** va u `04-11` ning ochiq topilmasini yopdi: ilgari AYNI sabotajda grid to'plami **12/12 yashil** qolardi |
| 4 | `GET /snapshots/{id}/image` marshrutidan `audit_read` olib tashlandi | **`test_binary_personal_routes_declare_read_audit_and_permission`** — AYNAN o'sha marshrut nomi bilan | Faylning qolgan to'qqiz testi (`PERSONAL_ROUTES` ga tegilmadi) | ✅ **Aynan bashorat qilingandek.** `04-09` AYNI sabotajni o'lchaganda bu fayl **butunlay yashil** qolardi — bo'shliq shu bilan yopildi |
| 5 | `04-VALIDATION.md` front-matter'idan `automated_replacements` olib tashlandi | `check-validation-signoff.mjs` **AYNAN (4) qoidasida** — `1 ta qoida buzilishi` | (1) Per-Task Map, (2) `BAJARILMADI`, (3) `human_only_verifications` — uchalasi ham tekshirildi va o'tdi | ✅ **Aynan bashorat qilingandek** — to'rtta shart mustaqil o'lchanayotgani isbotlandi |

Har besh holatda ham fayl `cp` bilan (**hech qachon `git checkout --` bilan
emas**) darhol tiklandi va to'plam qayta yashil bo'ldi.

> ⛔ **1-sabotajning yangi topilmasi: mezon testining IKKINCHI, mustaqil qulfi bor.**
> `test_criteria_module_uses_no_storage_mock` ning oxirgi asserti «haqiqiy
> omborga boradigan mezon testlari ≥ 2» deydi. SC#3 va SC#4 — aynan
> o'shalar. Ya'ni ikkalasidan birini o'chirish **ikkita** darvozani
> birdan qizartiradi: biri «mezon egasiz qoldi», ikkinchisi «mock'siz
> o'lchov bo'shab qoldi». Bu naqsh `test_storage_layout.py::
> MIN_STORAGE_TESTS` dan meros va u bu yerda **kutilmagan qo'shimcha
> qiymat** berdi.

## O'LCHOVLAR — taxmin qilinmadi

| Nima | Natija |
|---|---|
| `npm run gate` #4 (**sovuq**: `down -v` + `.next` o'chirilgan) | **745 s**, exit 0 |
| `npm run gate` #5 (issiq) | **691 s**, exit 0 |
| `npm run gate` #6 (issiq) | **695 s**, exit 0 |
| `npm run gate:fast` | **68 s** (chegara 180 s — **2.6× zaxira**) |
| **Yangi chegara** | 745 × 1.20 = 894 -> **900 s** (1200 s dan **TUSHIRILDI**) |
| `npm run gate` #7 (yakuniy tasdiq — chegara uchun ISHLATILMAYDI) | **686 s**, exit 0 — yangi chegaradan **214 s** past |
| `pytest` (sim ko'tarilgan) | **1 879** (baza 1 869 -> **+10**), 5 deselected (`hardware`) |
| `pytest tests/tenancy` | **472** (baza 470 -> **+2**) |
| vitest | **338** (baza 335 -> **+3**) |
| node | **115** (o'zgarmadi) |
| i18n | **777 × 3** (o'zgarmadi) |
| `--collect-only` da `test_sc[1-5]_` sanog'i | **5** |
| `capture_due_markets()` ning uchinchi disjunkti sabotajda | `pending` qator bilan **FALSE** — ya'ni `deferred-items.md` #1 dagi tahlil to'g'ri edi |
| `GET` marshrutlari `response_model` siz | **5 ta**: rasm proksisi, xlsx shabloni, `live-authz`, `self-check`, `readyz` |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm run sim:up && pytest tests/integration/test_phase4_criteria.py -q` | **7/7**, exit 0 |
| 2 | `pytest test_phase4_criteria.py --collect-only \| grep -c 'test_sc[1-5]_'` | **5** |
| 3 | `pytest ...::test_every_criterion_has_its_own_test -q` | exit 0 |
| 4 | `pytest ...::test_criteria_module_uses_no_storage_mock -q` | exit 0 |
| 5 | `python -c "... 'import moto' not in b and 'unittest.mock' not in b"` | exit 0 |
| 6 | `python -c "... meta nomlarida sc[1-5] yo'q"` | exit 0 — `['test_every_criterion_has_its_own_test', 'test_criteria_module_uses_no_storage_mock']` |
| 7 | `ruff check . && ruff format --check . && mypy .` | exit 0 (250 fayl, 242 manba) |
| 8 | `node scripts/check-validation-signoff.mjs .../04-VALIDATION.md` | exit 0 — **36 qator · 6 inson bandi** |
| 9 | `grep -c BAJARILMADI .../04-VALIDATION.md` | **0** |
| 10 | Per-Task Map: 36 qator, `pending` yo'q | exit 0 |
| 11 | Wave 0: `- [x] **W0-` sanog'i | **12** (W0-F7 ham) |
| 12 | `04-HUMAN-UAT.md`: `ega` ≥ 6, `Telegram`, `self-check` | **29 / bor / bor** — `**Egasi:**` **6**, `**Tetigi:**` **6** |
| 13 | `npm run requirements:check` | exit 0 — **Done 16 · Pending 32 · Blocked 1** |
| 14 | Beshala talab `Pending` emas | exit 0 — hammasi `Done` |
| 15 | ROADMAP: `- [x] **Phase 4`, `Plans` to'ldirilgan, Open Decision `Resolved` | exit 0 |
| 16 | `git diff --exit-code PROJECT.md STATE.md pyproject.toml package.json` | **o'zgarish yo'q** |
| 17 | `npm run gate` (yakuniy, to'rtinchi yugurish) | **exit 0**, **686 s** — yangi 900 s chegarasidan past |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — yetishmayotgan kritik funksionallik] Sentry worker jarayonida umuman o'rnatilmasdi**

- **Topildi:** Task 1 ning RED yugurishida — o'lchov bilan, tahmin bilan emas.
- **Muammo:** yuqoridagi «RED bosqichi nima topdi» bo'limi. Qisqasi:
  `SENTRY_DSN` uchala konteynerga beriladi, `sentry_sdk.init()` esa faqat
  bittasida chaqiriladi va aynan ish bajaradigan jarayonda chaqirilmaydi.
- **Rad etilgan yechim:** `test_sc5` ni faqat Telegram yarmi bilan yozib,
  Sentry ni «qo'lda tekshiriladigan» deb belgilash. U FOUND-06 ni
  isbotsiz `Done` qilardi.
- **Yechim:** `app/observability.py` (yangi) — `MASKED`, `PII_KEYS`,
  `mask_secrets`, `scrub_event`, `scrub_breadcrumb` va `init_sentry(dsn)`.
  `app/main.py::lifespan` va `app/worker.py::_open_worker_resources`
  ikkalasi ham uni chaqiradi; worker holatni `worker_started` jurnal
  satrida (`sentry=`) e'lon qiladi — «jim ishlash» taqiqlangan.
- **Nega ilmoqlar KO'CHIRILDI, `app.main` dan import qilinmadi:**
  `app.main` ning O'ZI `app.worker` dan `broker` ni import qiladi, ya'ni
  teskari yo'nalish aylanma bog'liqlik bo'lardi; undan ham qimmatrog'i —
  `app.main` ni import qilish butun FastAPI ilovasini va barcha
  routerlarni worker jarayoniga tortib kelardi.
- **Darvoza KUCHAYTIRILDI, kuchsizlantirilmadi:**
  `test_sentry_init_wires_both_hooks` endi `init_sentry` manbasini
  o'qiydi (ilmoqlar bir joyda), yangi `test_both_processes_install_sentry`
  esa IKKALA kirish nuqtasini talab qiladi.
- **⚠ Chegara ochiq aytiladi:** `scheduler` jarayoni `WORKER_STARTUP`
  hodisasini olmaydi, ya'ni unda Sentry o'rnatilMAYDI. Bu ATAYIN:
  planer faqat `capture_tick` ni navbatga qo'yadi va uning o'z istisnolari
  `taskiq` jurnalida qoladi. Ish bajaradigan jarayon — worker — qoplangan.
- **Committed in:** `2f85b35`

**2. [Rule 1 — bug] `npm run requirements:check` `03-14` dan beri QIZIL turgan**

- **Topildi:** Task 3 ning birinchi chaqiruvida.
- **Muammo:** `CAM-02` ro'yxatda `- [x]`, Traceability jadvalida esa
  `Blocked (...)` edi — ya'ni fayl ikki xil haqiqat aytardi. `git show
  HEAD:.planning/REQUIREMENTS.md` bilan tasdiqlandi: nosozlik MENING
  o'zgarishimdan emas, `03-14` dan.
- **Nega hech kim sezmagan:** skript CI darvozasi EMAS va buni o'z
  docstringida ochiq yozadi («qo'lda, har faza yopilishida»). 3-faza uni
  oxirgi marta chaqirmasdan yopilgan. Bu «darvoza bor, lekin hech kim
  bosmaydi» sinfi.
- **Yechim:** belgi JADVALGA moslandi (`- [ ]`), chunki jadval to'g'ri —
  CAM-02 ning bitta jumlasi hamon o'lchanmagan (CI'da `wg0` yo'q). Teskari
  yo'nalish (jadvalni `Done` qilish) talabni isbotsiz yopardi.
- **Committed in:** `7d6074d`

**3. [Rule 1 — bug] `04-VALIDATION.md` ning bitta qatori skript ustunlarini SILJITARDI**

- **Topildi:** `check-validation-signoff.mjs` ning birinchi chaqiruvida —
  `04-07/T2: Status yashil emas — "yangi"`.
- **Muammo:** o'sha qatorning `Automated Command` katagida
  `grep -cE '^\s*(import|from)\s+taskiq'` bor edi va undagi `|` markdown
  jadval AJRATUVCHISI hisoblanadi. Skript qatorni 11 katakka bo'lib,
  `cells[9]` ni `File Exists` ustunidan o'qirdi.
- **Nega bu jimgina zarar:** qator YASHIL bo'lgani holda darvoza uni qizil
  deb ko'rsatardi — yoki teskarisi, agar `File Exists` katagida tasodifan
  `✅` bo'lsa, QIZIL qator YASHIL o'qilardi.
- **Yechim:** buyruq `grep -c -e '^import taskiq' -e '^from taskiq'`
  shakliga o'tkazildi — semantikasi bir xil, ajratuvchi yo'q. Natija
  o'lchandi: **0** (`capture.py` da `taskiq` faqat izohda uchraydi va u
  aynan shu tekshiruvni tasvirlaydi — ya'ni `! grep -q taskiq` shakli
  darvozani o'z izohida o'ziga qaratardi).
- **Committed in:** `3f9effe`

**4. [Rule 3 — bloklovchi] «Sovuq» o'lchov S3 bucketini yo'q qiladi**

- **Muammo:** reja sovuq o'lchovni `docker compose down -v` dan keyin
  talab qiladi, `-v` esa `seaweed` volume'ini o'chiradi va u bilan birga
  bucketni. Bucket ilova tomonidan yaratilMAYDI (`ops/seaweedfs/README.md`
  §3: `Admin` amali ataylab berilmagan), ya'ni birinchi sovuq yugurish
  16 ta testni yiqitardi — bu «sekin» emas, «yiqilgan» o'lchov bo'lardi.
- **Yechim:** bucket o'lchovdan OLDIN qayta yaratildi
  (`printf 's3.bucket.create -name sbozor-snapshots\n' | docker compose
  exec -T storage weed shell`) va bu bir martalik TA'MINOT qadami sifatida
  `04-VALIDATION.md` da yozildi — u `04-01` ning `npm install` qadami
  bilan bir toifada va o'lchov oynasidan tashqarida.

**5. [Qamrov qarori] Rejadagi ikki qabul buyrug'i o'z holida ishlamaydi — sabab o'lchandi**

- `pytest ... --collect-only -q` : `pyproject.toml` ning `addopts` ida
  allaqachon `-q` bor, ya'ni ikkinchi `-q` chiqishni **fayl darajasiga**
  yig'adi (`test_phase4_criteria.py: 7`) va `grep -c 'test_sc[1-5]_'`
  **0** beradi. `--collect-only` (qo'shimcha `-q` siz) **5** beradi va
  da'vo o'zgarmaydi.
- `npm run validation:check` : argumentsiz chaqiruv **2-faza** fayliga
  ishora qiladi (`scripts/check-validation-signoff.mjs` ning
  `DEFAULT_FILE` i) va u exit 0 beradi (71 qator · 4 inson bandi), lekin
  4-faza faylini QAMRAMAYDI. Reja bu holatni oldindan ko'rgan; to'g'ridan-
  to'g'ri chaqiruv ishlatildi va natija yuqoridagi jadvalning 8-qatorida.

### Rejadan tashqari yopilgan bandlar (topshiriqning 3–7 bandlari)

Bularning hammasi `3aeaf90` da. Har biri **sabotaj bilan o'lchandi**,
«tuzatdim» deb yozilmadi:

| # | Band | Qaror | Dalil |
|---|---|---|---|
| 3 | `test_personal_data_coverage.py` rasm marshrutini ko'rmasdi | **DARVOZA KENGAYTIRILDI** (qabul qilinmadi) | `BINARY_PERSONAL_ROUTES` + `NON_PERSONAL_BINARY_ROUTES` **yopiq to'plami**: `response_model` siz har `GET` ikkisidan birida bo'lishi shart. 4-sabotaj: `audit_read` olib tashlanganda darvoza endi AYNAN qizaradi |
| 4 | `compose.yaml` `tests` da `depends_on: storage` yo'q | **TUZATILDI** | `depends_on: storage: condition: service_healthy`. `db`/`cache` ATAYIN qo'shilmadi (testcontainers), `nvr-sim` ham (skip/fail farqi saqlanadi) |
| 5 | Yarim tun chegarasidagi flakiness | **TUZATILDI** | `_anchor_today()` — bugungi kunga QAT'IY bog'langan `succeeded` qator; oyna 5 daqiqadan **NOLGA** tushdi. 2-sabotaj shartni deterministik takrorladi |
| 6 | UI-SPEC §11.7 bajarilmas va §11.9 bitta kalitga orqada | **TUZATILDI** | Yorliq `snapshots.methodLabel` ga ko'chdi (enum xaritasi joyida qoldi — ko'chirish uchala tildagi uch kalitni qayta nomlardi); §11.9 ga `nvrAccountLocked` qo'shildi |
| 7 | `capture-grid.test.tsx` fixture'ida `missed` qator yo'q | **TUZATILDI** | Uchta yangi test (12 -> 15); `makeRows()` ning O'ZI o'zgartirilmadi — roving-tabindex va semantika testlari bir xil holatdagi olti hujayrani talab qiladi. 3-sabotaj grid to'plamining endi qizarishini ko'rsatdi |

⚠ **Bitta assertion o'z-o'zini yolg'on-yashil qilardi va u yozilishi
bilanoq olib tashlandi:** `capture-grid` ning yangi testida
`getBoundingClientRect().width` solishtiruvi bor edi — jsdom layout
hisoblamaydi va u HAR DOIM `0 === 0` beradi. Uning o'rniga nishon
o'lchami SINF TOKENLARI bo'yicha (`min-h-11`/`min-w-11`) tekshiriladi va
sabab kodda yozildi. Bu aynan shu faza qidirayotgan «bo'sh to'plam
ustida yashil» sinfi edi.

---

**Total deviations:** 5 (1× Rule 2 kritik funksionallik, 2× Rule 1 bug,
1× Rule 3 bloklovchi, 1× qamrov qarori) + topshiriqning beshta bandi

**Impact on plan:** Hech biri darvozani kuchsizlantirmadi. Bittasi
(1-deviatsiya) MAHSULOT kodini o'zgartirdi va u talabning jumlasini
yolg'ondan rostga o'tkazdi; ikkitasi (2, 3) mavjud darvozalarning
jimgina buzilgan joylarini ochdi.

## `.planning/STATE.md` uchun tayyor matn (bu rejada TEGILMADI)

Reja mezoni `git diff --exit-code .planning/STATE.md` ni talab qiladi,
STATE.md ning `Blockers/Concerns` bo'limida esa 4-fazaga tegishli to'rt
band bor. Ular **jimgina qoldirilmadi** — quyida ularning yangi matni,
faza yopilish oqimi uchun:

| Joriy band (STATE.md) | Yangi matn |
|---|---|
| `[Phase 4] Kadr olish usuli hal qilinmagan` | ~~...~~ **YOPILDI (04-07)**: uchala usul bitta protokol ortida (`FrameSourcePool`), tanlov `nvr_devices.capture_method` da — real qurilmaga o'tish MA'LUMOT o'zgarishi (`test_frame_source.py`, `test_snapshot_quality.py`) |
| `[Phase 4] Job orchestration` | ~~...~~ **YOPILDI (04-07, Open Decision #2)**: `taskiq scheduler` holatsiz 1-daqiqalik tik; reja/ijara/idempotentlik/yo'qlik Postgres `capture_runs` da (`SKIP LOCKED` + lease). `test_capture_tick.py`, `test_capture_repo.py`, `test_sc2_...` |
| `[Phase 4] npm run gate — 1000 s, shundan 316 s (31 %) qayta bajarish` | ~~...~~ **YOPILDI (04-12)**: qayta bajarish `03-12` da olib tashlangan; chegara olti o'lchov asosida qayta belgilandi — **1200 s -> 900 s** (eng yomon 745 s + 20 %); `gate:fast` 68 s, chegarasi 180 s da qoldi |
| `[Phase 4] go2rtc-sim oqimini birorta test iste'mol qilmaydi` | ~~...~~ **YOPILDI (03-12/03-14 + 04-07)**: `test_live_view_e2e.py` kashfiyot hosil qilgan oqimdan haqiqiy JPEG oladi; kadr olish yo'li esa sim'ning ISAPI `/picture` i orqali `test_snapshot_quality.py` da mock'siz o'lchanadi |

Qo'shiladigan yangi band (4-fazadan meros, ochiq):

> `[Phase 5] Sifat chegaralarining QIYMATI hali LOW confidence` — mexanizm
> o'lchangan, qiymat real Karmana kadri bilan sozlanadi. Egasi: nazoratchi
> + ijrochi. Tetigi: Phase 0 kadrlari. Bandi: `04-HUMAN-UAT.md` #1.
> D-15 bo'yicha o'lchovlar qatorda saqlanadi, ya'ni sozlash SQL bilan
> bo'ladi — qayta kadr olish TALAB QILINMAYDI.

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `tests/integration/test_phase4_criteria.py` | SC#1…SC#5 uchun aynan bitta nomlangan test (har docstringda ROADMAP jumlasi so'zma-so'z) + meta-test + mock'siz o'lchov darvozasi; `respx` istisnosi `telegram_calls` fixture'i bilan NOMLANGAN va bitta testga qulflangan | 1 330 |
| `services/core-api/app/observability.py` | Sentry ilmoqlari (`scrub_event`, `scrub_breadcrumb`, `mask_secrets`) va `init_sentry(dsn) -> bool`; `Settings` ga bog'lanmaydi — faqat DSN satrini oladi | 217 |
| `.planning/phases/04-snapshot-pipeline/04-HUMAN-UAT.md` | Oltita band, har birida **Egasi** va **Tetigi**; #4 va #5 to'liq qadamlar bilan (FOUND-06 ning sharti) | 234 |

## Bazaviy holat

| O'lchov | Baza (`04-11`) | Hozir | Holat |
|---|---|---|---|
| pytest (sim ko'tarilgan) | 1 869 | **1 879** | ✅ **+10** (7 mezon + 1 Sentry + 2 shaxsiy-ma'lumot darvozasi) |
| tenancy | 470 | **472** | ✅ **+2** |
| vitest | 335 | **338** | ✅ **+3** (`capture-grid` ning SC#2 bloki) |
| node | 115 | **115** | ✅ o'zgarmadi |
| i18n | 777 × 3 | **777 × 3** | ✅ o'zgarmadi |
| `npm run gate` | exit 0 | **exit 0** | ✅ (to'rt marta) |
| `gate` chegarasi | 1 200 s | **900 s** | ⬇ **TUSHIRILDI** |
| `git diff pyproject.toml / package.json` | — | **o'zgarish yo'q** | ✅ yangi paket YO'Q |

## Issues Encountered

- **Yangi paket qo'shilmadi** va bu tekshirildi
  (`git diff --exit-code services/core-api/pyproject.toml
  frontend/package.json` — bo'sh). T-04-SC bajarildi.
- **`docker compose down -v` bucketni yo'q qiladi** — 4-deviatsiya.
  `ops/seaweedfs/README.md` da bu ogohlantirish HALI YO'Q va u
  `deferred-items.md` #3 bilan bir xil sinfda (bind-mount `s3.json`
  katalog bo'lib yaratilishi). **Egasi:** `ops/seaweedfs/README.md` ga
  keyingi tegadigan reja.
- **`npm run validation:check` faqat 2-faza faylini qamraydi** —
  5-deviatsiya. Skriptning `DEFAULT_FILE` i qadalgan; har faza uchun
  to'g'ridan-to'g'ri chaqiruv kerak. **Egasi:** 5-fazaning validatsiya
  rejasi (o'sha yerda uchinchi fayl paydo bo'ladi va naqsh takrorlanadi).

## Known Stubs

Yo'q.

⚠ **Stub bo'lmagan, lekin ochiq qolgan uch band (uchalasining ham egasi bor):**

1. **`scheduler` jarayonida Sentry o'rnatilmaydi** — 1-deviatsiyaning
   ochiq yozilgan chegarasi. `WORKER_STARTUP` hodisasi planer jarayonida
   ishlamaydi; planer faqat navbatga qo'yadi va uning istisnolari
   `taskiq` jurnalida qoladi. **Egasi:** 8-faza (mustahkamlash).
   **Tetigi:** agar planerning o'z nosozligi bir marta ham dala
   diagnostikasini qiyinlashtirsa.
2. **`ops/seaweedfs/README.md` da `down -v` ogohlantirishi yo'q** —
   yuqoridagi «Issues» bandi.
3. **`scripts/check-validation-signoff.mjs` ning `DEFAULT_FILE` i
   qadalgan** — yuqoridagi «Issues» bandi.

## Threat Flags

Reja threat register'ining yettala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-90 (mezon testining jimgina yo'qolishi) | **IKKI MUSTAQIL QULF** — `test_every_criterion_has_its_own_test` (`range(1,6)`, `len == 5`) **va** mock darvozasining «≥ 2 ombor testi» chegarasi; 1-sabotaj ikkalasini ham qizartirdi |
| T-04-91 (S3/kadr olishning mock ostida o'lchanishi) | `test_criteria_module_uses_no_storage_mock` — `ast` daraxti bo'yicha; `respx` istisnosi NOMLANGAN va AYNAN bitta testga qulflangan; `test_storage_layout.py` ning jufti o'z joyida |
| T-04-92 (`nyquist_compliant` ning kelishuv sifatida yozilishi) | Skript bayroqni IKKALA yo'nalishda majburlaydi; 5-sabotaj to'rtta shart mustaqil ekanini ko'rsatdi |
| T-04-93 (talab holatining dalilsiz `Done` qilinishi) | Har holat mezon testining NOMI bilan bog'landi; `check-requirements-sync.mjs` exit 0 (va u yo'l-yo'lakay `03-14` dan qolgan driftni ochdi) |
| T-04-94 (chegaraning jimgina bo'sh qolishi) | Chegara olti o'lchov bilan **900 s** ga tushirildi; `gate:fast` 180 s da qoldi va joriy qiymati (68 s) yozildi |
| T-04-95 (Telegram xabarida rasm) | `test_sc5` har so'rovning yo'li `/sendMessage` bilan tugashini, matnda `http` va `.jpg` YO'Qligini talab qiladi |
| T-04-SC (paket o'rnatishlari) | Yangi paket **YO'Q**; `git diff --exit-code` toza |

⚠ **YANGI YUZA (registerda yo'q edi): worker jarayonidan Sentry'ga
chiquvchi hodisalar.**
1-deviatsiya worker jarayonida ilova chegarasidan TASHQARIGA (uchinchi
tomon xizmatiga) yangi ma'lumot yo'lini ochadi. Bu **ataylab** va u
FOUND-06 ning talabi, lekin yuzani nomlash shart:

- **Nima chiqadi:** istisno matni, stack, breadcrumb'lar.
- **Nima CHIQMAYDI:** `before_send` (`scrub_event`) so'rov tanasi va
  cookie'larni tashlaydi, `Authorization`/`Cookie` sarlavhalarini
  maskalaydi, `extra` dagi `PII_KEYS` ni maskalaydi va butun hodisani
  matn darajasida `mask_secrets()` dan o'tkazadi; `before_breadcrumb`
  (`scrub_breadcrumb`) chiquvchi so'rov URL'laridagi `src=` va
  `rtsp://user:pass@` shakllarini maskalaydi. Ikkalasi ham **AYNI**
  funksiyalar — API jarayonida 03-13 dan beri ishlab turgan va 13 ta
  test bilan qoplangan.
- **⚠ Qoldiq xavf:** kadr BAYTLARI hech qachon istisno matniga tushmaydi
  (ular hech qayerda `repr` qilinmaydi), lekin `include_local_variables`
  yoqilgan holda katta `bytes` obyektining qisqartirilgan `repr` i
  freym lokallariga tushishi mumkin. Bu **yangi** xavf emas — u API
  jarayonida ham mavjud edi; endi u worker jarayonida ham amal qiladi.
  **Egasi:** 8-faza (mustahkamlash) — `SENTRY_DSN` haqiqiy qiymat olgan
  kun `include_local_variables=False` qarori qayta ko'rib chiqilsin.

## Next Phase Readiness

**Fazani tekshirish (`/gsd-verify-work`) uchun:**

- Beshala mezon **bitta buyruq** bilan: `npm run sim:up && docker compose
  --profile test run --rm tests pytest tests/integration/test_phase4_criteria.py -q`
- ⚠ **Hamma dalil SIMULYATOR ustida.** `04-HUMAN-UAT.md` ning oltita
  bandi real uskuna, real vaqt yoki real odam talab qiladi va ularning
  natijasi hech qayerda da'vo qilinmagan.
- ⚠ **CAM-02 hamon `Blocked`** (3-fazadan) va bu TO'G'RI holat.
- `04-VALIDATION.md` ning `nyquist_compliant` bayrog'i skript bilan
  hisoblangan, `Approval` bandida esa «imzo nimani anglatmaydi» ochiq
  yozilgan.

**5-faza uchun:**

- `snapshots` jadvalining D-16 langari (`UNIQUE (id, is_billable)` +
  `CHECK` + kompozit FK) `test_sc3` da HAQIQIY bola-jadval bilan
  o'lchandi — `occupancy_events` aynan shu shaklda quriladi.
- `BINARY_PERSONAL_ROUTES` yopiq to'plami tayyor: zona kesimlarini yoki
  belgilangan kadrni bayt sifatida qaytaradigan yangi marshrut tasnifsiz
  o'tolmaydi.
- Sifat chegaralari 5-fazada **o'zgaradi** (real kadrlar bilan) va
  `quality_thresholds_version` ustuni aynan shuning uchun bor — eski
  qatorlar qayta hisoblanmaydi.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **Uchala yaratilgan fayl diskda tekshirildi** (`MISSING: 0`):
  `tests/integration/test_phase4_criteria.py`,
  `services/core-api/app/observability.py`,
  `.planning/phases/04-snapshot-pipeline/04-HUMAN-UAT.md`.
- **Beshala commit `git log 0c2ea9c..HEAD` da tasdiqlandi:** `f42a1e9`,
  `2f85b35`, `3aeaf90`, `7d6074d`, `3f9effe`.
- **Birorta commitda fayl o'chirilishi YO'Q.**
- **Ishchi daraxt toza** — repo ildizidagi uchta begona fayl
  (`.docx` × 2, `SBOZOR-MVP-texnik-topshiriq.md`) TEGILMADI.
- **`npm run gate` exit 0** (to'rtinchi, yakuniy yugurish).

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
