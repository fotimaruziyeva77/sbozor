---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 04
subsystem: frontend
tags: [error-taxonomy, i18n, copy-gate, navigation, rbac, transliteration, ai-01, ai-03, ai-04, ai-06, d-22, d-27]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 10
    provides: "`error-codes.test.mjs` ning BACKEND LANGARI — kodlar VA `actor` solishtiriladi; oltinchi reyestr aynan shu naqshni davom ettiradi"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`capture_errors.py` — `Final[str]` + docstring reyestr shakli, `frozenset` ni `schemas.py` ga IMPORT bilan ulash"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`nvr-errors.ts` xato moduli (`…ErrorView(code)` shakli), `isapi/errors.py` reyestri, G-1/G-2 parity darvozasi"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`app-shell.tsx::NAV_ITEMS` va uning literal union'lari, `app-shell.test.tsx` naqshi, `gen-cyrillic` transliteratsiya darvozasi"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`rbac.ts` matritsasi — `occupancy_review` va `report_view` ALLAQACHON mavjud (M-8)"
provides:
  - "`app/services/occupancy_errors.py` — oltinchi xato reyestri: 14 kod, har birida docstring; IKKI SIRT reyestri (`ZONE_ERROR_CODES` 8 + `REVIEW_ERROR_CODES` 6), `OCCUPANCY_ERROR_CODES` ulardan HOSILA"
  - "`app/schemas.py::MARKET_ERROR_CODES` — 60 -> 74 kod (IMPORT bilan, qo'lda takrorlamasdan)"
  - "`lib/zone-errors.ts` — `zoneErrorView(code) -> {code, causeKey, fixKey, tone, surface}`; `actor` va `retrySafe` ATAYIN yo'q"
  - "`NAV_ITEMS` 11 -> 13: `/review` va `/occupancy` — nazoratchining BIRINCHI ekrani navigatsiyada"
  - "`scripts/zone-copy.test.mjs` — G-11, G-15, G-16, G-18(a); har taqiq uchun ijobiy VA salbiy nazorat holati"
  - "`scripts/error-codes.test.mjs` — G-17: oltinchi reyestrning BACKEND LANGARI + SIRT solishtiruvi"
  - "`scripts/check-validation-signoff.mjs` — fazadan mustaqil (D-27 yopildi)"
  - "`cameraZones.*` / `review.*` / `occupancy.*` matni uchala tilda (777 -> 819 kalit)"
affects: [05-06, 05-07, 05-08, 05-09, 05-10, 05-11, 05-12, 05-13, 05-14, 05-15]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reyestr NOMI — SIRTNING O'ZI: `ZONE_ERROR_CODES` -> `cameraZones.*`, `REVIEW_ERROR_CODES` -> `review.*`. Alohida `surface` xaritasi qurilmaydi; darvoza kodni ham, u QAYSI REYESTRDA turishini ham solishtiradi (04-10 dagi `actor` ustunining aynan bir xil sinfi)"
    - "So'z taqig'i INKORNI TASDIQDAN ajratishi SHART: `bo'sh emas` / `не свободны` oldin olib tashlanadi, keyin qidiriladi — aks holda darvoza D-22 ni tushuntiruvchi jumlaning O'ZINI qizartirardi (S-15 diskriminatorining takrori)"
    - "So'z taqig'i NAMESPACE bo'yicha doiralanadi: `tuzatish` faqat tizim VERDIKTI ko'rinadigan sirtlarda (`review.*`, `occupancy.*`) taqiqlanadi; zona muharririda u qonuniy fe'l"
    - "Akronim darvozasi RO'YXAT emas, PREDIKAT ham bo'lishi kerak: bitta tokenda lotin+kirill birga bo'lsa — defekt, akronim nomidan qat'i nazar (M-5 `CV`->`CВ`)"
    - "JavaScript'da `\\b` — FAQAT ASCII (`u` bayrog'i buni o'zgartirmaydi): kirill so'zi oldidagi `\\b` HECH QACHON mos kelmaydi"
    - "Faza raqami MATN emas, SON bo'yicha taqqoslanadi (`10` > `9`, `02.1` qo'llab-quvvatlanadi); darvoza tanlagan faylni BIRINCHI SATRDA chop etadi"

key-files:
  created:
    - services/core-api/app/services/occupancy_errors.py
    - frontend/src/lib/zone-errors.ts
    - frontend/scripts/zone-copy.test.mjs
  modified:
    - services/core-api/app/schemas.py
    - frontend/src/components/shell/app-shell.tsx
    - frontend/src/components/shell/app-shell.test.tsx
    - frontend/scripts/error-codes.test.mjs
    - scripts/check-validation-signoff.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "Xato kodlari nomlanishida REJA tanlandi, UI-SPEC §12.7 emas — 05-06 va 05-10 aynan reja nomlarini ishlatadi (`zone_limit_reached`, `review_already_answered`)"
  - "`review_sample_not_drawn` uchun `warning`, `neutral` emas — uchinchi tone butun taksonomiyani uch tarmoqli qilardi; 4-fazada `capture_plan_created_late` (u ham normal holat) aynan `warning` olgan"
  - "G-15 sodda `bo'sh` taqig'i emas, INKOR DISKRIMINATORI — UI-SPEC §12.6 ning verbatim matni («Ular bo'sh emas») aynan D-22 ni amalga oshiradi va uni qizartirish matnni buzardi"
  - "G-17 uchun `readPythonFrozenset` emas, `readPythonStrConstants` + yangi `readPythonFrozensetRefs` — har kod uchun docstring talab konstantalarni majburlaydi, literal ro'yxat esa IKKI NUSXA bo'lardi"
  - "RBAC va `/review/blind` navigatsiyaga TEGILMADI; yangi `Permission` o'ylab topilmadi"

patterns-established:
  - "Darvozaning DETEKTORI ham o'lchanadi: har taqiq uchun sun'iy IJOBIY satr ushlanishi VA qonuniy satr ushlanMAsligi tasdiqlanadi"
  - "Skaner maydoni OCHIQ chegaralanadi (`messages/*.json` qiymatlari) — darvoza fayli o'z taqiq so'zlarini olib yuradi va `grep` asosidagi tekshiruv ishlatilmaydi"

requirements-completed: [AI-01, AI-03, AI-04, AI-06]

# Metrics
duration: 48min
completed: 2026-08-08
---

# Phase 5 Plan 04: Reyestr, navigatsiya va copy darvozalari Summary

**Bandlik domenining oltinchi xato reyestri uch qatlamda (backend 14 kod -> `zone-errors.ts` ko'zgusi -> uch til), nazoratchining birinchi navigatsiya yozuvi, va `messages/*.json` ustidagi to'rtta so'z darvozasi — har biri o'z detektorini o'zi o'lchaydigan nazorat holati bilan.**

## Performance

- **Duration:** ~48 min
- **Started:** 2026-08-08T17:47:00Z
- **Completed:** 2026-08-08T18:35:00Z
- **Tasks:** 3
- **Files modified:** 11 (3 yangi, 8 o'zgartirilgan)

## Accomplishments

- **Nazoratchining ishi uchun ekran paydo bo'ldi.** Bugungacha `inspector` roli navigatsiyada FAQAT Boshqaruv panelini ko'rardi. `NAV_ITEMS` 11 -> 13 va `/review` uning uyiga aylandi — yangi `Permission` o'ylab topilmasdan, `rbac.ts`/`rbac.py` matritsalariga tegilmasdan.
- **Oltinchi xato reyestri BACKEND LANGARI bilan tug'ildi.** 04-09 va 04-10 da ikki marta takrorlangan sinf («backend kod qo'shdi, copy unutildi») bu safar birinchi kundanoq yopiq: G-17 matn katalogidan emas, `occupancy_errors.py` dan boshlanadi.
- **Yangi o'lcham — SIRT.** 4-fazada `actor` ustuni ikki tomonda mustaqil yozilgani uchun solishtirilardi. Bu yerda o'sha sinfdagi fakt — xato QAYSI EKRANDA ko'rsatiladi. Backendda u REYESTR NOMI bilan, frontendda `surface` maydoni bilan yashaydi va G-17 ikkalasini qulflaydi.
- **To'rtta copy darvozasi o'z detektorini o'zi o'lchaydi.** Har taqiq uchun sun'iy ijobiy satr VA qonuniy satr sinaladi — ya'ni «hech qachon qizarmaydigan darvoza» holati struktura jihatidan mumkin emas.
- **D-27 (meros band) yopildi** va tuzatish o'lchandi: `10` > `9` (leksikografik tartib buni teskari qilardi), `02.1` qo'llab-quvvatlanadi, topilmasa `exit 1`, tanlangan fayl birinchi satrda chop etiladi.

## Task Commits

1. **Task 1: Oltinchi xato reyestri — backend, frontend ko'zgusi va uch til** — `61edf38` (feat)
2. **Task 2: Navigatsiya — ikkita yozuv va RBAC tasdig'i (W0-F1, W0-F5)** — `2d91c8c` (feat)
3. **Task 3: Uch copy darvozasi + parity kengaytmasi + D-27** — `6594e4e` (test)

## Files Created/Modified

- `services/core-api/app/services/occupancy_errors.py` — 14 kod, har birida docstring; `ZONE_ERROR_CODES` (8) va `REVIEW_ERROR_CODES` (6); `OCCUPANCY_ERROR_CODES` ularning birlashmasi
- `services/core-api/app/schemas.py` — `MARKET_ERROR_CODES` ga IMPORT bilan qo'shildi (60 -> 74)
- `frontend/src/lib/zone-errors.ts` — `zoneErrorView(code)`; `Record<OccupancyErrorCode, …>` kompilyator qatlami; taqsimlangan birlashma tipi `causeKey` ni faqat MAVJUD kalitlar bilan chegaralaydi
- `frontend/src/components/shell/app-shell.tsx` — ikkita `NAV_ITEMS` yozuvi + literal union'larga to'rt satr
- `frontend/src/components/shell/app-shell.test.tsx` — 5 yangi test; `ROLES` `rbac.ts` dan olinadi
- `frontend/scripts/zone-copy.test.mjs` — 17 test (G-11, G-15, G-16, G-18a)
- `frontend/scripts/error-codes.test.mjs` — 4 yangi test (G-17)
- `scripts/check-validation-signoff.mjs` — fazadan mustaqil `DEFAULT_FILE`
- `frontend/messages/{uz-Latn,ru,uz-Cyrl}.json` — 777 -> 819 kalit; `uz-Cyrl` `i18n:gen` bilan hosila

## O'lchangan sabotajlar

⛔ **Barchasi `cp` bilan snapshot'dan qaytarildi** (`git checkout --` ishlatilmadi).

| # | Sabotaj | Natija | Qizargan darvoza |
|---|---------|--------|------------------|
| 1 | `cameraZones.errorCause.zone_limit_reached` ga `poligon` so'zi (reja talab qilgan sabotaj) | ✅ QIZARDI | `zone-copy` G-16 |
| 2 | `/review` yozuviga noto'g'ri `permission` (`camera_view`) | ✅ QIZARDI — **ikki yo'nalishda**: nazoratchi havolani yo'qotdi VA direktorda ortiqcha havola paydo bo'ldi | `app-shell.test.tsx` (2 test) |
| 3 | Backend reyestriga o'n beshinchi kod, copy'siz (04-09 ning aynan sinfi) | ✅ QIZARDI — **uch joyda**: sanoq nazorati, ko'zgu, uchala tildagi matn | `error-codes` G-17 |
| 4 | `zone_aspect_mismatch` ning `surface` i `review` ga o'zgartirildi | ✅ QIZARDI | `error-codes` G-17 |
| 5 | `.planning/phases/` bo'sh (vaqtinchalik katalog) | ✅ `exit 1` | `check-validation-signoff` |
| 6 | `9-noleadingzero` + `10-x` yonma-yon | ✅ `10` tanlandi (leksikografik tartib `9` ni tanlardi) | `check-validation-signoff` |

**Hech biri jimgina yashil qolmadi.** 4-fazadagi «olti sabotaj — nol qizil» holati bu yerda takrorlanmadi.

## Decisions Made

- **Kod nomlanishi: REJA, UI-SPEC emas.** UI-SPEC §12.7 qisqa nomlarni (`zone_self_intersecting`, `zone_stall_taken`, `zone_no_frame`, `zone_too_few_points`) beradi, reja esa to'liq nomlarni. Qaror `05-06-PLAN.md:230` (`zone_limit_reached`) va `05-10-PLAN.md:117,193` (`review_already_answered`) bilan hal qilindi — ular XATONI KO'TARADIGAN rejalar, ya'ni ular ishlatgan nom kanonik. UI-SPEC §12.7 ning matni kanonik nomlarga ko'chirildi.
- **Ikki sirt reyestri** rejadagi bitta `OCCUPANCY_ERROR_CODES` bilan UI-SPEC G-17 dagi «`ZONE_ERROR_CODES` va `REVIEW_ERROR_CODES`» talabini birlashtiradi: ikkalasi ham bor, uchinchisi HOSILA.
- **`tone` frontendda, `surface` ikki tomonda.** `tone` — chizish qarori (backendda iste'molchisi yo'q); `surface` — matn kalitining manzili, ya'ni ikki tomonda mustaqil yozilgan fakt va shuning uchun solishtiriladi.
- **`uz-Cyrl.overrides.json` TEGILMADI** — M-13 o'lchovi tasdiqlandi: 5-fazaning copy'si mavjud override to'plami bilan 0 lotin qoldig'i, 0 akronim defekti berdi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Spek ziddiyati] Xato kodlarining nomlanishi**
- **Found during:** Task 1
- **Issue:** Reja 14 ta to'liq nom beradi, UI-SPEC §12.7 esa 7 ta qisqa nom (`zone_self_intersecting` va h.k.). Ikkalasi bir vaqtda to'g'ri bo'la olmaydi.
- **Fix:** Reja nomlari tanlandi; qaror boshqa rejalarning matnidan o'lchandi (05-06, 05-10 aynan shu nomlarni ishlatadi). §12.7 copy'si kanonik nomlarga ko'chirildi.
- **Files modified:** `occupancy_errors.py`, `zone-errors.ts`, uchala `messages/*.json`
- **Verification:** `grep` bilan 05-06/05-10 rejalari tekshirildi; G-17 uchala qatlamni qulfladi
- **Committed in:** `61edf38`

**2. [Rule 1 - Spek ziddiyati] `review_sample_not_drawn` uchun `neutral` tone**
- **Found during:** Task 1
- **Issue:** UI-SPEC §12.7 bu kodga `neutral` beradi; reja esa `warning|danger` deydi va meros qoida «uchinchi tone YO'Q» deb yozilgan (03-UI-SPEC §7.2, `capture-errors.ts:54`).
- **Fix:** `warning` tanlandi va sabab `zone-errors.ts` da yozildi — 4-fazada normal holat (`capture_plan_created_late`) aynan shu tone'ni olgan.
- **Files modified:** `frontend/src/lib/zone-errors.ts`
- **Verification:** G-17 `tone` ning faqat ikki qiymatini qabul qiladi
- **Committed in:** `61edf38`

**3. [Rule 1 - Spek ziddiyati] G-15 sodda `bo'sh` taqig'i UI-SPEC §12.6 ning O'Z matnini qizartirardi**
- **Found during:** Task 3
- **Issue:** §15 (G-15) `occupancy.noCoverage*` da `bo'sh` ni taqiqlaydi; §12.6 esa o'sha kalitning verbatim matnini beradi: «Ular **bo'sh emas** — ular haqida ma'lumot yo'q». Sodda taqiq D-22 ni AMALGA OSHIRADIGAN jumlani defekt deb belgilardi va uni "tuzatgan" ijrochi aynan farqni tushuntiruvchi so'zlarni o'chirgan bo'lardi.
- **Fix:** `ъ` diskriminatori (S-15) naqshi: INKOR SHAKLI oldin olib tashlanadi (`bo'sh emas` / `бўш эмас` / `не свободны`), qolganida qidiriladi. Uchala inkor shakli `npm run i18n:gen` chiqishidan o'lchandi.
- **Files modified:** `frontend/scripts/zone-copy.test.mjs`
- **Verification:** Nazorat holati IKKI yo'nalishda — tasdiq ushlanadi, inkor ushlanMAYDI
- **Committed in:** `6594e4e`

**4. [Rule 2 - Yetishmayotgan kritik funksiya] G-15 ning skaner maydoni umuman yo'q edi**
- **Found during:** Task 2
- **Issue:** `occupancy.noCoverage*` va `cameraZones.uncovered*` kalitlari hech qayerda yaratilmagan edi (reja ularni birorta bandga bermagan). Ularsiz G-15 bo'sh to'plam ustida ishlab, ABADIY yashil bo'lardi — «darvoza bor» degan yolg'on da'vo.
- **Fix:** §12.3 va §12.6 dan to'rtta kalit uchala tilga qo'shildi; G-15 ga ALOHIDA assert — prefiksga mos kalit topilmasa test qizaradi.
- **Files modified:** uchala `messages/*.json`, `zone-copy.test.mjs`
- **Verification:** `G-15: qamrov kalitlari BO'SH EMAS` testi
- **Committed in:** `2d91c8c`, `6594e4e`

**5. [Rule 1 - Bug, o'z darvozamda] JavaScript'da `\b` kirill harfidan oldin ishlamaydi**
- **Found during:** Task 3
- **Issue:** `/\bбўш\s+эмас/u` va `/\bне\s+свободн\w*/u` HECH QACHON mos kelmaydi: `\b` `\w` ga tayanadi va u FAQAT ASCII (`u` bayrog'i buni o'zgartirmaydi). Natija o'lchandi — uz-Latn o'tdi (u yerda `b` ASCII), uz-Cyrl va ru YOLG'ON QIZARDI.
- **Fix:** `\b` olib tashlandi; `\w*` o'rniga `[а-яё]*`. Sabab fayl izohida yozildi.
- **Files modified:** `frontend/scripts/zone-copy.test.mjs`
- **Verification:** 17/17 yashil; nazorat holatlari ikki yo'nalishda
- **Committed in:** `6594e4e`

**6. [Rule 2 - Yetishmayotgan kritik funksiya] G-11 ga ARALASH ALIFBO predikati qo'shildi**
- **Found during:** Task 3
- **Issue:** Akronim NOMLARI ro'yxati M-5 defektining faqat MA'LUM a'zolarini ushlaydi. Ro'yxatda yo'q yangi akronim (`IoU`, `mAP`) aynan shu shaklda buzilib, hech qanday darvozadan o'tmasdi.
- **Fix:** Ro'yxatga qo'shimcha PREDIKAT (§S-10): bitta tokenda lotin va kirill harfi birga bo'lsa — defekt, nom bilishdan qat'i nazar.
- **Files modified:** `frontend/scripts/zone-copy.test.mjs`
- **Verification:** `mixedAlphabetTokens("CВ xizmati")` -> `["CВ"]`; `"SBOZOR"` va sof kirill -> `[]`
- **Committed in:** `6594e4e`

**7. [Rule 2 - Yetishmayotgan kritik funksiya] G-16 «tuzatish» taqig'i NAMESPACE bo'yicha doiralandi**
- **Found during:** Task 3
- **Issue:** UI-SPEC «tizim javobiga NISBATAN» deydi, lekin mexanik shakl bermaydi. Yassi taqiq zona muharririning qonuniy matnini («tepani to'g'rilang» sinfidagi fe'l) qizartirardi — 5-deviatsiya bilan bir xil xato.
- **Fix:** `tuzat`/`тузат`/`исправ` faqat `review.*` va `occupancy.*` da taqiqlanadi — tizim VERDIKTI aynan o'sha ikki ekranda ko'rinadi (D-12). Chegara va sababi izohda.
- **Files modified:** `frontend/scripts/zone-copy.test.mjs`
- **Committed in:** `6594e4e`

**8. [Rule 3 - Bloklovchi] G-17 parseri: `readPythonFrozenset` ishlatib bo'lmadi**
- **Found during:** Task 3
- **Issue:** Reja mavjud `readPythonFrozenset` ni ko'rsatadi, lekin u faqat qo'shtirnoqli LITERALLARNI o'qiydi. §S-7 esa har kod uchun ALOHIDA docstring talab qiladi va docstringni `frozenset` ichiga yozib bo'lmaydi. Literal ro'yxat + konstantalar IKKI NUSXA bo'lardi; `frozenset(A | B)` shakli esa parserni JIMGINA bo'sh ro'yxat qaytarishga majburlardi — §S-10 ning aynan o'sha nosozligi.
- **Fix:** 04-10 ning qarori takrorlandi: mavjud `readPythonStrConstants` + yangi `readPythonFrozensetRefs` (konstanta nomlarini o'qib, xarita orqali kodga aylantiradi). «Topilmadi = yiqilish»; bo'sh blok `assert` bilan yiqiladi.
- **Files modified:** `frontend/scripts/error-codes.test.mjs`
- **Verification:** Sabotaj #3 uch joyda qizardi
- **Committed in:** `6594e4e`

**9. [Rule 2 - Yetishmayotgan kritik funksiya] D-27: hujjatsiz yangi faza jimgina o'tkazib yuborilardi**
- **Found during:** Task 3
- **Issue:** «Eng katta raqamli fazani ol» qoidasi 6-faza katalogi yaratilib `06-VALIDATION.md` hali yozilmagan holatda 5-fazani tekshirardi va natija «yashil» ko'rinardi — D-27 nosozligining aynan yangi shakli.
- **Fix:** Bunday faza `stderr` da OGOHLANTIRISH beradi (chiqish kodi o'zgarmaydi — hujjat hali yozilmagani xato emas). Tanlangan fayl esa birinchi satrda chop etiladi.
- **Files modified:** `scripts/check-validation-signoff.mjs`
- **Verification:** `11-nofile` fikstura bilan o'lchandi
- **Committed in:** `6594e4e`

**10. [Rule 3 - Bloklovchi] `frontend/node_modules` worktree'da yo'q edi**
- **Found during:** Task 2
- **Issue:** `npm run typecheck` va `test:component` ishlamadi (`tsc` topilmadi) — `node_modules` gitignored, ya'ni worktree'ga ko'chmaydi. Task 2 ning verifikatsiyasi aynan shu ikki buyruq.
- **Fix:** `npm ci` (LOCKFILE'dan tiklash — yangi paket QO'SHILMADI, `package.json`/`package-lock.json` o'zgarmadi).
- **Verification:** `git status` da bog'liqlik fayllari yo'q; typecheck va 343 vitest testi yashil
- **Committed in:** — (kod o'zgarishi yo'q)

---

**Total deviations:** 10 auto-fixed (4× Rule 1 spek ziddiyati/bug, 4× Rule 2 yetishmayotgan kritik funksiya, 2× Rule 3 bloklovchi)
**Impact on plan:** Scope creep yo'q. To'rttasi darvozalarning O'ZINI ishlaydigan qilish uchun majburiy edi (ularsiz G-11, G-15, G-16 va G-17 ning bir qismi abadiy yashil bo'lardi). Uchtasi spek ichidagi ziddiyatning yechimi va har birida tanlov sababi kodda yozilgan.

## Issues Encountered

**⚠ UMUMIY INFRATUZILMA: `sbozor-storage-1` konteyneri buzildi — ORKESTRATORGA.**

Rejaning verifikatsiyasi `docker compose --profile test run --rm tests pytest -q` ni (bog'liqliklar BILAN) talab qiladi. Uni worktree'dan ishga tushirish quyidagini qildi:

1. `.env` va `ops/seaweedfs/s3.json` — **gitignored**, ya'ni worktree'da YO'Q (`.gitignore:10`).
2. Docker yetishmayotgan bind-mount manbasini **katalog** qilib yaratdi (`ops/seaweedfs/s3.json/`).
3. `docker compose` UMUMIY `sbozor-storage-1` konteynerini o'sha buzuq mount bilan **qayta yaratdi** → `read /etc/seaweedfs/s3.json: is a directory` → S3 API ko'tarilmadi → healthcheck `starting` da qotib qoldi.

**Qilingani:** o'zim yaratgan bo'sh katalog `rmdir` bilan olib tashlandi (worktree toza, `git status` bo'sh). Konteynerni bu yerdan «tuzatish» ATAYIN qilinmadi — u meni yana o'z worktree yo'llarimga bog'lardi va uchta parallel ijrochiga zarar yetkazardi; soxta rekvizit bilan `s3.json` yaratish esa umumiy servisga jimgina yolg'on konfiguratsiya kiritardi.

**Tavsiya:** `sbozor-storage-1` ni ASOSIY checkout'dan qayta yarating (`docker compose up -d --force-recreate storage`) — u yerda `.env` ham, haqiqiy `s3.json` ham bor. **Worktree'dan HAR DOIM `--no-deps` bilan ishlang.**

**Regressiya o'lchovi (buning o'rniga):**

| O'lchov | Baseline | Hozir | Holat |
|---------|----------|-------|-------|
| pytest — jami YIG'ILGAN | 1889 | **1889** | ✅ birorta test yo'qolmadi; yig'ish har test modulini IMPORT qiladi, ya'ni `schemas.py` ning yangi importi ham sinaldi |
| pytest `tests/unit` — bajarildi | — | **734 passed** | ✅ `--no-deps` bilan |
| pytest `tests/tenancy` — yig'ildi | 472 | **472** | ✅ |
| vitest | 338 | **343** | ✅ +5 |
| `node --test` | 115 | **136** | ✅ +21 (17 `zone-copy` + 4 G-17) |
| i18n kalitlari | 777×3 | **819×3** | ✅ +42, parity va ICU to'liq |

`tests/integration` va `tests/tenancy` BAJARILMADI — ular DB va ombor stekiga muhtoj, worktree esa `.env` siz. O'zgarish faqat qo'shimchali (`MARKET_ERROR_CODES` 60 -> 74) va yangi sof-konstanta moduli, ya'ni bu ikki to'plamga xulq ta'siri yo'q.

**Boshqa:** `ruff check` + `ruff format --check` toza; `eslint` toza; `tsc --noEmit` toza.

## User Setup Required

None — tashqi servis sozlamasi talab qilinmaydi.

## Next Phase Readiness

- **05-06 (zona API) uchun tayyor:** `occupancy_errors.py` dan `ZONE_*` kodlarini import qilib `HTTPException(detail={"error_code": …})` ga qo'ying — allowlist allaqachon qamragan, matn uchala tilda tayyor.
- **05-10 (ko'r audit API) uchun tayyor:** `REVIEW_*` va `BLIND_ANSWER_LOCKED` shu tarzda. `blind_answer_locked` ↔ `review_already_answered` farqi docstringda yozilgan — ularni BIRLASHTIRMANG.
- **05-07…05-12 (ekranlar) uchun tayyor:** `zoneErrorView(code)` kalit beradi; `t(view.causeKey)` tip-xavfsiz. Marshrutlar `/review` va `/occupancy` navigatsiyada, `cameraZones.title` / `review.title` / `review.blindTitle` / `occupancy.title` mavjud.
- **Yangi copy yozadigan har bir keyingi reja** `node --test frontend/scripts/zone-copy.test.mjs` ga tushadi — akronim, jargon, «bo'sh», ommaviy tasdiq va qayta tortish AVTOMATIK bloklanadi.
- ⚠ **Blocker (orkestrator uchun):** yuqoridagi `sbozor-storage-1` konteyneri. To'liq `pytest` (integration + tenancy) shu tuzatilmaguncha HECH BIR worktree'dan ishlamaydi.
- ⚠ **D-26 (npm run gate byudjeti) BU REJADA O'LCHANMADI** — u `cv-service` qo'shilgandan keyin o'lchanishi kerak (05-PATTERNS §3.11) va bu reja `cv-service` ga tegmaydi.

## Known Stubs

Yo'q. Bu reja ekran QURMAYDI — u reyestr, navigatsiya yozuvi va darvozalar yetkazadi. Yaratilgan matn kalitlarining iste'molchilari (`/review`, `/occupancy`, zona muharriri sahifalari) 05-07…05-12 da keladi; bu ATAYIN va rejada shunday yozilgan (Wave 0 — ekranlardan OLDIN).

## Threat Flags

Yo'q. Yangi tarmoq endpointi, auth yo'li, fayl kirishi yoki sxema o'zgarishi kiritilmadi. `<threat_model>` dagi to'rttala band ham (T-05-13…T-05-16) rejada ko'rsatilgan choralar bilan qoplandi:

| Threat | Chora | Qayerda |
|--------|-------|---------|
| T-05-13 | Kod allowlist'i + xom `detail` copy'da yo'q + har kod ikki matnga majburlanadi | `schemas.py`, G-17 |
| T-05-14 | «Hammasini tasdiqlash» va «qayta tortish» matndan chiqarildi | G-18(a) |
| T-05-15 | `no_coverage` «bo'sh» dan matn darajasida ajratildi | G-15 |
| T-05-16 | Navigatsiya xavfsizlik chegarasi EMAS — izohda va test docstringida yozilgan; haqiqiy darvoza serverda | `app-shell.tsx`, `app-shell.test.tsx` |

## Self-Check: PASSED

- **Fayllar:** 12/12 topildi (3 yangi, 8 o'zgartirilgan, 1 SUMMARY)
- **Commitlar:** 3/3 `git log` da mavjud — `61edf38`, `2d91c8c`, `6594e4e`
- **Sabotajlar:** 6/6 o'lchandi va `cp` bilan qaytarildi; `git status` toza
- **Tegilmagan fayllar tasdig'i:** `frontend/src/lib/rbac.ts`, `services/core-api/app/security/rbac.py`, `frontend/messages/uz-Cyrl.overrides.json`, `.planning/STATE.md`, `.planning/ROADMAP.md` — birortasi ham uch commitning diff'ida YO'Q

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-08*
