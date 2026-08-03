---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 01
subsystem: infra
tags: [rbac, dependencies, httpx, taskiq, pytest-markers, structlog, pg_catalog, gate, wave-0]

# Dependency graph
requires:
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`Permission`/`ROLE_PERMISSIONS` matritsasi va uning UI ko'zgusi; `sbozor_core.logging.SENSITIVE_KEYS` + rekursiv `censor_secrets`; `services/core-api/Dockerfile` ning `dev`/`runtime` ikki target'i"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`market_delete_draft()` ning o'n ikki jadvalli kaskadi va `ALL_TENANT_TABLES` reyestri; `tests/tenancy/test_meta.py` ning `pg_catalog` naqshi; `frontend/scripts/role-gate.test.mjs` darvozasi"
provides:
  - "`httpx==0.28.1` ishlab chiqarish bog'liqligi — ISAPI klienti (03-05) uchun; o'lchangan dalil bilan"
  - "`taskiq==0.12.4` + `taskiq-redis==1.2.3` + `tenacity==9.1.4` prod'da, `respx==0.23.1` dev'da"
  - "`Permission.CAMERA_MANAGE` va kamera huquqlari IKKALA matritsada (backend + UI ko'zgusi)"
  - "`role-gate.test.mjs` ning G-8 darvozasi — ikki RBAC matritsasining mexanik parity tekshiruvi (YANGI)"
  - "`sim` / `hardware` / `slow` pytest markerlari `--strict-markers` ostida e'lon qilingan"
  - "`tests/unit/test_runtime_deps.py` — manifest darvozasi (prod/dev chegarasi + `redis` pini + `arq` taqiqi)"
  - "`tests/integration/test_market_delete_guard.py` — kaskad to'liqligining `pg_catalog` darvozasi"
  - "`npm run test:fast` va `npm run gate:fast` — task darajasidagi 32 s lik teskari aloqa lentasi"
  - "`03-VALIDATION.md` chegara jadvali o'lchangan qiymatlar bilan to'ldirildi"
affects: [03-02-sim, 03-03-migratsiya, 03-05-isapi-klient, 03-06-job, 03-08-frontend-wave0, 03-11-yakuniy-darvoza]

# Tech tracking
tech-stack:
  added: [taskiq 0.12.4, taskiq-redis 1.2.3, tenacity 9.1.4, respx 0.23.1 (dev)]
  patterns:
    - "Bog'liqlik guruhi darvoza bilan qulflanadi: manifest `tomllib` bilan O'QILADI, import qilib SINALMAYDI — import bu konteynerda har doim ishlaydi va aynan shu muammoni yashiradi"
    - "Ikki tilli ko'zgu (Python <-> TypeScript) manba fayllarni O'QIB solishtiriladi; 'qo'lda sinxron saqlanadi' izohi darvoza EMAS"
    - "DB obyektining ta'rifi `pg_get_functiondef` bilan BAZADAN o'qiladi, Python manbasidan emas: manba — istalgan holat, baza — haqiqiy holat"
    - "Kaskad to'liqligi CHET EL KALITI bo'yicha o'lchanadi, ustun NOMI bo'yicha emas — `DELETE` ni yiqitadigan narsa FK, ustun emas"
    - "Qoldiq xavf test bilan HUJJATLASHTIRILADI (filtrning chegarasi qulflanadi), 'bilamiz' izohi bilan emas"
    - "Teskari aloqa ikki lentaga bo'linadi: task (`gate:fast`, qat'iy chegara) va to'lqin (`gate`, chegarasi o'lchovdan)"

key-files:
  created:
    - tests/unit/test_runtime_deps.py
    - tests/integration/test_market_delete_guard.py
  modified:
    - services/core-api/pyproject.toml
    - services/core-api/uv.lock
    - pyproject.toml
    - package.json
    - services/core-api/app/security/rbac.py
    - frontend/src/lib/rbac.ts
    - frontend/scripts/role-gate.test.mjs
    - tests/unit/test_rbac_matrix.py
    - tests/unit/test_logging.py
    - migrations/entities/functions.py
    - .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-VALIDATION.md

key-decisions:
  - "D-16 TAXMIN EMAS, O'LCHOV bilan tasdiqlandi: `git archive HEAD` dan qurilgan `--no-dev` runtime image'da `import httpx` -> `ModuleNotFoundError`, o'zgarishdan keyin -> `0.28.1`. Birinchi zond (`sbozor-core-api:latest`) `httpx` ni TOPGAN edi va da'voga zid ko'ringan — tekshirilganda u aslida `dev` build ekani aniqlandi (pytest/ruff/mypy ichida bor), ya'ni zond yolg'on signal bergan"
  - "Kaskad darvozasi jadvallarni `markets` ga CHET EL KALITI bo'yicha topadi, `market_id` USTUNI bo'yicha emas: o'lchandi — `audit_log` da ustun BOR, FK YO'Q. Ustun bo'yicha izlash 13 jadval topib darvozani bugunoq yolg'on-qizil qilardi va 'tuzatish' ning eng oson yo'li audit izini kaskadga tortish bo'lardi"
  - "`role-gate.test.mjs` ga G-8 parity darvozasi QO'SHILDI (Rule 2). Rejaning qabul mezoni sabotaj shu faylni qizartirishini talab qilardi, lekin fayl matritsalarni UMUMAN solishtirmasdi — ya'ni mezon bajarilmas edi va W0-3 mexanizmsiz qolardi"
  - "`CAMERA_MANAGE` `CAMERA_VIEW` dan ajratildi (D-07): bitta huquq ikkalasini qamrasa, 'direktor kameralarni ko'rsin' so'rovi jimgina 'direktor NVR parolini yangilay olsin' ga aylanardi"
  - "`requirements mark-complete` ATAYIN BAJARILMADI: CAM-01/03/08/09 faza darajasida belgilanadi (MARKET-01..07 naqshi) va ularni Wave 0 dan keyin 'Done' qilish yolg'on da'vo bo'lardi — CAM-08 ning ISAPI kashfiyoti hali yozilmagan. Belgilash 03-11 ning zimmasida"
  - "`gate:fast` chegarasi 180 s da QOLDI va ko'tarilmadi — o'lchangan 32 s unga 5.6× zaxira bilan sig'adi"
  - "Task 3 ning TDD RED bosqichi SABOTAJ bilan olindi: darvoza loyihasi bo'yicha bugun YASHIL (reja shuni talab qiladi), shuning uchun 'qizil' isboti kaskaddan bir `DELETE` ni olib tashlash orqali o'lchandi"

patterns-established:
  - "Pattern: prod/dev bog'liqlik chegarasi IKKI YO'NALISHDA qulflanadi — prod moduli dev'da nusxalanmasin, dev mock'i (`respx`) prodga sizmasin"
  - "Pattern: manifest darvozasining quyi chegarasi majburiy (`>= 20 paket`) — bo'sh to'plamda barcha 'yo'q' assert'lari jimgina o'tib ketardi"
  - "Pattern: sabotaj natijasi IKKI TOMONLAMA yoziladi — nima qizardi VA nima yashil qoldi; ikkinchisi darvozaning mustaqilligini isbotlaydi"
  - "Pattern: ruff `S608` yolg'on-musbatida `noqa` emas, matnni oddiy konstantaga ko'chirish — qoida chetlab o'tilmaydi, QO'LLANILMAYDIGAN qilinadi"
  - "Pattern: reja bosqichma-bosqich yarim qoldirgan ish (W0-7) ATAYIN yarim qoldiriladi — 'yordam berib' tugatish keyingi to'lqinlar orasidagi yashil darvozani sindiradi"

requirements-completed: []

# Metrics
duration: 65min
completed: 2026-08-03
---

# Phase 3 Plan 01: Wave 0 blokerlari Summary

**`httpx` ishlab chiqarish image'iga ko'chirildi (o'lchangan `ModuleNotFoundError` dalili bilan), `CAMERA_MANAGE` ikkala RBAC matritsasiga qo'shilib parity darvozasi ostiga olindi, va `market_delete_draft()` kaskadining to'liqligi `pg_catalog` bo'yicha mexanik tekshiriladigan bo'ldi.**

## Performance

- **Duration:** ~65 min (ijro) + ~28 min (chegara o'lchovlari)
- **Started:** 2026-08-02T23:20Z
- **Completed:** 2026-08-03T00:25Z
- **Tasks:** 3/3
- **Files modified:** 12 (2 yangi, 10 o'zgargan) + 1 hujjat

## Accomplishments

- **Yettala Wave 0 bandi yopildi** (W0-7 — reja talab qilganidek FAQAT mexanizm yarmi).
- **Uchta «jimgina yiqiladigan» band endi o'lchanadi**, ya'ni ular kelasi safar CI'da ko'rinadi, deploy'da yoki ish paytida emas.
- **Bazaviy darvoza qizarmadi:** 992 → **1021** backend (+29 yangi), **322** tenancy (o'zgarmadi), 57 → **60** node:test (+3), **74** vitest (o'zgarmadi). `npm run gate` uch marta `exit 0`.
- **2-fazadan meros qolgan kechikish bandi yopildi:** `gate:fast` **32 s** (chegara 180 s, ko'tarilmadi).

## Task Commits

1. **Task 1: W0-1 + W0-5** — `5119ef5` (chore)
2. **Task 2: W0-2/3/4/6** — `6afbb8a` (test, RED) → `d4015a9` (feat, GREEN)
3. **Task 3: W0-7 mexanizmi** — `2104b69` (test)

## O'lchangan dalillar

### D-16 — `httpx` ishlab chiqarish image'ida (W0-1)

Ikki `--no-dev` image solishtirildi (ikkinchisi `git archive HEAD` dan qurilgan):

| Image | `httpx` | `taskiq` | `tenacity` | `redis` | `respx` | `pytest` |
|---|---|---|---|---|---|---|
| **OLDIN** (HEAD, `--no-dev`) | ❌ `ModuleNotFoundError` | ❌ | ❌ | 8.0.1 | ❌ | ❌ |
| **KEYIN** (bu reja, `--no-dev`) | ✅ 0.28.1 | ✅ 0.12.4 | ✅ 9.1.4 | ✅ **8.0.1** | ✅ yo'q (to'g'ri) | ✅ yo'q (to'g'ri) |

`redis` runtime image'da ham **8.0.1** — `arq` sinfidagi pasayish sodir bo'lmadi (D-06).

### W0-5 — markerlar `--strict-markers` ostida

| Holat | Natija |
|---|---|
| `@pytest.mark.definitely_not_declared` | `'definitely_not_declared' not found in markers configuration option`, pytest **exit 2** (yig'ilish xatosi) |
| `@pytest.mark.sim` / `hardware` / `slow` | 3 test to'plandi, `exit 0` |
| `-m sim` filtri | 1 test tanlandi |
| `-m "not hardware"` filtri | 2 test tanlandi |

### Kechikish (VALIDATION chegara jadvali)

| Lenta | Sovuq | Issiq #1 | Issiq #2 | Eng yomon | Chegara |
|---|---|---|---|---|---|
| `npm run gate:fast` | 32 s | 32 s | 31 s | **32 s** | **180 s** ✅ (5.6× zaxira) |
| `npm run gate` | 515 s | 502 s | 496 s | **515 s** | nomzod **618 s** (+20 %) — 03-11 `test:sim` bilan yakunlaydi |

Oltala o'lchov ham `exit 0`. **`gate:fast` chegarasi ko'tarilmadi va ko'tarishga ehtiyoj bo'lmadi.**

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| S1 | `rbac.ts` dagi `platform_admin` dan `"camera_manage"` olib tashlandi | `role-gate.test.mjs` — 2 test; xabar: `platform_admin: rbac.ts da YO'Q -> camera_manage` | `pytest tests/unit/test_rbac_matrix.py` — 18 test | Ikki matritsa MUSTAQIL o'lchanadi; backend testi UI driftini ko'rmaydi va ko'rmasligi ham kerak |
| S2 | Kaskaddan `DELETE FROM public.stall_assignments` olib tashlandi | `test_market_delete_guard.py` — 1 test; xabar: `kaskadida ['stall_assignments'] YO'Q` | **`tests/tenancy` — 322 test** | Kaskaddagi bo'shliqni butun tenancy to'plami KO'RMAYDI — darvozaning mavjud bo'lish sababi aynan shu |

Ikkala sabotaj ham commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; ikkalasidan keyin ham ish daraxti toza.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Yetishmayotgan kritik funksiya] `role-gate.test.mjs` ga G-8 parity darvozasi qo'shildi**
- **Found during:** Task 2
- **Issue:** Reja `key_links` da ikki matritsa `role-gate.test.mjs` orqali bog'lanadi deb yozgan va qabul mezoni sabotaj shu faylni **qizartirishini** talab qilgan. Ammo fayl matritsalarni umuman solishtirmasdi — u faqat `MARKET_ADMIN_ASSIGNABLE_ROLES` va rol YORLIQLARINI tekshirardi. Ya'ni «qo'lda sinxron saqlanadi» majburiyati ikkala faylning boshida yozilgan, uni tekshiradigan mexanizm esa yo'q edi. Mezon bajarilmas, W0-3 esa darvozasiz qolardi.
- **Fix:** `Permission` enum'i, `PERMISSIONS` massivi va butun rol matritsasi manba fayllardan o'qib solishtiriladigan uchta test qo'shildi (izohlar filtrlanadi — aks holda izohdagi huquq nomi «berilgan» deb o'qilardi).
- **Verification:** 3 yangi node test yashil; S1 sabotaji ularni aniq xabar bilan qizartiradi.
- **Committed in:** `d4015a9`

**2. [Rule 2 — Yetishmayotgan kritik funksiya] Marker e'lonlari uchun regressiya darvozasi**
- **Found during:** Task 1
- **Issue:** W0-5 ning yagona tekshiruvi rejadagi bir martalik `tomllib` buyrug'i edi — ya'ni marker keyinchalik o'chirilsa hech nima qizarmasdi.
- **Fix:** `test_runtime_deps.py::test_required_pytest_markers_are_declared` — to'rtala markerni va `--strict-markers` ning `addopts` da qolganini tekshiradi.
- **Verification:** yashil; o'chirilgan marker testni qizartiradi.
- **Committed in:** `5119ef5`

**3. [Rule 1 — Xato] `S608` yolg'on-musbati tuzatildi**
- **Found during:** Task 3
- **Issue:** `ruff` xato XABARI ichidagi SQL ko'rinishli matnni «so'rov qurilishi» deb hisobladi va `npm run lint` qizardi.
- **Fix:** Tuzatish yo'riqnomasi f-satrdan oddiy konstantaga (`CASCADE_FIX_HINT`) ko'chirildi — `noqa` ISHLATILMADI: qoida chetlab o'tilmadi, qo'llanilmaydigan qilindi.
- **Verification:** `ruff check .` toza.
- **Committed in:** `2104b69`

**4. [Rule 2 — Nazorat holati] `audit_log` uchun teskari yo'nalish qulfi**
- **Found during:** Task 3
- **Issue:** Kaskad darvozasi to'g'ri yozilsa ham, kelajakda `audit_log.market_id` ga FK qo'shilsa darvoza qizarardi va uni «tuzatish» ning eng oson yo'li audit jurnalini kaskadga qo'shish bo'lardi — ya'ni darvozaning o'zi dalil izini o'chirish yo'lini ochib berardi.
- **Fix:** `test_audit_log_deliberately_survives_market_deletion` — `audit_log` na FK ro'yxatida, na kaskadda bo'lishi kerakligini qulflaydi.
- **Verification:** yashil.
- **Committed in:** `2104b69`

### Rejadan ataylab chetlangan bandlar (sabab bilan)

**A. `requirements mark-complete` BAJARILMADI.** Reja frontmatter'ida `requirements: [CAM-01, CAM-03, CAM-08, CAM-09]` bor, lekin bu reja ularning birortasini ham bajarmaydi — u faqat poydevor qo'yadi. `REQUIREMENTS.md` traceability jadvali talablarni **faza darajasida** belgilaydi (`MARKET-01..07 | Phase 2 | Done` naqshi), va `03-VALIDATION.md` ning o'zi belgilashni `T03-11-3` («talablar dalil bilan belgilanadi») ga biriktirgan. CAM-08 ni bugun «Done» qilish yolg'on da'vo bo'lardi: ISAPI kashfiyoti hali yozilmagan. Talablar `Pending` da qoldirildi.

**B. Rejadagi bitta qabul mezoni bajarilmas shaklda yozilgan edi (bajarildi, o'lchov usuli aniqlashtirildi).** Mezon: `git diff --unified=0 services/core-api/pyproject.toml | grep -c '^[+-].*redis\[hiredis\]'` = **0**. Ammo shu mezonning o'zi turgan `<action>` bandi izohda `redis[hiredis]<6` va `redis[hiredis]==8.0.1` ni **literal yozishni talab qiladi** — ya'ni ikkalasi bir vaqtda mumkin emas. O'lchangan natija: grep **2** ta qator topadi va **ikkalasi ham men yozgan IZOH**. Haqiqiy niyat — pinning tegilmagani — aniqroq buyruq bilan tasdiqlandi: `grep '^[+-].*"redis\[hiredis\]'` → **0 qator** (bog'liqlik yozuvi tegilmagan). Bundan tashqari `test_redis_pin_is_not_downgraded` pinni tuzilma darajasida qulflaydi va runtime image'da ham `8.0.1` o'lchandi.

**C. `-m sim --collect-only` `exit 0` emas, `exit 5` beradi.** Reja `exit 0` kutgan, lekin izohida «bugun nol test to'planishi kutilgan xulq» deb yozgan — pytest esa nol test to'planganda **5** qaytaradi (`NO_TESTS_COLLECTED`), 0 emas. Ikkalasi bir vaqtda mumkin emas. Muhimi shundaki, `exit 5` markerning **tanilganini** bildiradi; tanilmagan marker esa boshqa kod beradi. Shuning uchun bandning haqiqiy da'vosi to'g'ridan-to'g'ri o'lchandi (yuqoridagi W0-5 jadvali): e'lon qilinmagan marker **exit 2** bilan yig'ilishni yiqitadi, e'lon qilingani esa to'planadi va filtrlanadi.

**D. Task 3 ning TDD RED bosqichi sabotaj bilan olindi.** Rejaning `<behavior>` bandi darvoza **bugun yashil** bo'lishini talab qiladi (12 jadval, hammasi ro'yxatda), ya'ni klassik «avval qizil» bosqichi mumkin emas. Qizil isboti S2 sabotaji bilan o'lchandi.

---

**Total deviations:** 4 auto-fixed (3 × Rule 2, 1 × Rule 1) + 4 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Hech qanday scope creep yo'q. Uchala Rule 2 tuzatishi rejaning O'Z qabul mezonlarini bajarilishi mumkin holga keltirdi yoki e'lon qilingan darvozani haqiqiy darvozaga aylantirdi.

## Issues Encountered

1. **Birinchi D-16 zondi yolg'on signal berdi.** Mavjud `sbozor-core-api:latest` image'ida `httpx` topildi — bu D-16 ga zid ko'rindi. Xulosa chiqarish o'rniga image tekshirildi: unda `pytest`, `ruff`, `mypy`, `testcontainers` ham bor edi, ya'ni u `runtime` emas, **`dev`** build ekan va `--no-dev` yo'li haqida hech nima ayta olmasdi. Haqiqiy o'lchov `git archive HEAD` dan alohida qurilgan `--no-dev` image bilan olindi.
2. **Kaskad darvozasining birinchi loyihasi noto'g'ri bo'lardi.** «`market_id` ustuni bor» mezoni 13 jadval topadi (`audit_log` qo'shilib) va darvoza birinchi kunidanoq yolg'on-qizil bo'lardi. Zond bilan o'lchanib, mezon FK ga o'zgartirildi — 12 jadval, aynan kaskaddagilar.
3. **`uv.lock` ni yangilash kerak bo'ldi.** `Dockerfile` `uv sync --frozen` ishlatadi, ya'ni eski lock bilan image umuman qurilmasdi. Lock mavjud test image ichida (`uv lock --project services/core-api`) yangilandi; `redis` diff'da o'zgarmagani alohida tekshirildi.

## Known Stubs

Yo'q. Bu reja yangi funksiya bermaydi — u darvoza va bog'liqlik qo'yadi, va qo'yilgan darvozalarning hammasi haqiqiy holatni o'lchaydi (bo'sh to'plamda yashil qolmasligi quyi chegara assert'lari bilan qulflangan).

## Threat Flags

Yo'q. Yangi tarmoq endpoint'i, auth yo'li, fayl kirish naqshi yoki ishonch chegarasidagi sxema o'zgarishi kiritilmadi. Reja `<threat_model>` da sanalgan `mitigate` bandlari (T-03-01, T-03-02, T-03-03, T-03-05, T-03-06, T-03-SC) bajarildi; T-03-04 «accept + verify» sifatida o'lchandi va uning **qoldiq xavfi** (formatlangan matn ichidagi parol) test bilan hujjatlashtirildi.

## Next Phase Readiness

**03-02 (simulyator) uchun tayyor:** `sim`/`slow`/`hardware` markerlari e'lon qilingan va o'lchangan, ya'ni sim testlari yig'ilish paytida yiqilmaydi. `gate` zanjiri **ataylab tegilmadi** — `test:sim` ni unga 03-02 qo'shadi.

**03-03 (migratsiya) uchun tayyor va OGOHLANTIRILGAN:** `test_market_delete_guard.py` `0012_nvr_domain` to'rtta tenant jadvalini olib kelgan zahoti **qizaradi** va yetishmayotgan jadvallarni nomma-nom aytadi. Bu kutilgan xulq — kaskadni kengaytirish `0012` bilan **bir oynada** bajarilishi shart (W0-7 ning ikkinchi yarmi).

**03-05 (ISAPI klienti) uchun tayyor:** `httpx` prod image'da, `tenacity` retry uchun, `respx` dev'da mock uchun. `censor_secrets` ning chegarasi o'lchangan — parol **nomlangan kalit** sifatida uzatilishi shart, formatlangan matn ichida hech qachon.

**03-08 (frontend Wave 0) uchun tayyor:** `camera_view`/`camera_manage` UI matritsasida va G-8 darvozasi ostida; yangi npm paketi qo'shilmadi (`frontend/package.json` tegilmagan).

**Ochiq qolgan band:** `npm run gate` ning yakuniy chegarasi (`test:sim` bilan) — 03-11 ning zimmasida; bugungi asos 515 s / nomzod 618 s.

## Self-Check: PASSED

- **Fayllar:** 7/7 mavjud (2 yangi + 5 o'zgargan asosiy fayl + SUMMARY)
- **Commitlar:** 4/4 mavjud (`5119ef5`, `6afbb8a`, `d4015a9`, `2104b69`)
- **`contains` shartlari:** 5/5 (`taskiq-redis`, `CAMERA_MANAGE`, `camera_manage`, `httpx`, `market_delete_draft`)
- **Yakuniy darvoza:** `npm run gate` → `exit 0` (uch marta ketma-ket: 515 s / 502 s / 496 s)

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
