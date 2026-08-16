---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 20
subsystem: testing
tags: [pytest, ast, xlsx, backup, restic, i18n, audit-draw, roadmap, requirements]

# Dependency graph
requires:
  - phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
    provides: "08-07/08-12: uch JSON marshruti va to'rt `.xlsx` eksporti; 08-16/08-18: `/reports/compare` va imzoli hujjat; 08-14: `POST /reports/compare/ledger`; 08-05/08-08: zaxira zanjiri va yurak urishi halqasi; 08-19: `ops/docs/go-live.md`"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`audit_draw()` hosila urug'i, 70/30 kvota, `accuracy_report()` ning ikki maxraji va `MIN_SAMPLE_FOR_PERCENT`"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`test_phase7_criteria.py` — zanjir bog'lash falsafasi, `_FAKE_ROOTS`/`_FAKE_FIXTURES` reyestri va meta-testning shakli"
provides:
  - "tests/integration/test_phase8_criteria.py — beshta mezon BITTA buyruqda + to'rt mustaqil soxtalashtirish darvozasi"
  - "Yangi taqiq (3): zaxira faktini QO'LDA yozadigan xom SQL — AST bilan"
  - "Yangi taqiq (4): `.xlsx` yo'liga tegib javob KODI haqida da'vo qilgan test baytlarni ham o'qishi SHART"
  - "08-VALIDATION.md — to'ldirilgan kontrakt (20 qatorli map, 5 inson bandi, 6 almashtirish, nyquist_compliant: true)"
  - "gate byudjetining o'lchovi: 1909 / 1842 s — chegara 2300 s da QOLDI"
  - "REQUIREMENTS.md: RECON-04/05 `Done`, FOUND-07 `Blocked` (sababi LITERAL)"
  - "deferred-items.md: 13 WR + 8 Info bandining NOMMA-NOM hisobi + yettita yangi band"
affects: [09, gsd-verify-work, ops]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Mezon moduli MAVJUD testlarni takrorlamaydi — u ularni ZANJIR sifatida bog'laydi va yagona savol beradi: ROADMAP'dagi jumla bugun rostmi?"
    - "Soxtalashtirish taqig'i HAR FAZADA BOSHQA SHAKLDA: 5-fazada metrika nomlari, 6-fazada suzuvchi arifmetika, 7-fazada jo'natuvchining vorisi, 8-fazada zaxira fakti va baytsiz eksport da'vosi"
    - "Taqiq TETIGI «nomni tilga oldi» emas, «javob haqida DA'VO qildi» (`status_code` ga murojaat) — birinchi shakl nazorat testini yolg'on-qizil qilgan edi"

key-files:
  created:
    - tests/integration/test_phase8_criteria.py
  modified:
    - package.json
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/08-VALIDATION.md
    - .planning/phases/08-hisobotlar-mustahkamlash-va-ishga-tushirish/deferred-items.md

key-decisions:
  - "08-20: SC#2 ning namunasi shunday QURILDI-ki, «band deb xato» O'LCHANADI, «bo'sh deb xato» esa BO'SH KATAK bo'lib qoladi — ikki maxrajning boshqaligi FAQAT shunda hujjatning O'ZIDA ko'rinadi; bir maxrajga qo'shilganda ikkala katak ham to'lardi"
  - "08-20: doira hajmi (30) MAHSULOT KONSTANTASIDAN hosila — `eval_quota(30, 0.70) >= MIN_SAMPLE_FOR_PERCENT` testning ichida o'lchanadi, ya'ni chegara o'zgarsa nosozlik SHU YERDA chiqadi, hujjatning bo'sh katagida emas"
  - "08-20: SC#3 yurak urishini FAQAT `ops/backup/heartbeat.sql` dan bajaradi va `DELETE` taqiqdan CHIQARILGAN — o'chirish faktni YOZMAYDI, u o'lchov boshlanadigan bo'sh holatni quradi"
  - "08-20: SC#3 restic'ni UMUMAN ishlatmaydi; «offsite» va «toza server» chegarasi docstringda LITERAL va FOUND-07 `Blocked` bo'lib qoladi"
  - "08-20: SC#4 ning mexanik yarmi UCH TILNING HUJJATGA yetib borishi bilan o'lchanadi (profil -> server -> sarlavha), runbookning SHAKLI esa `test_runbook_shape.py` da qoladi — takrorlanmaydi"
  - "08-20: `respx` bu fazada TAQIQLANGAN ildizlar ro'yxatiga QO'SHILDI (7-fazada ATAYIN yo'q edi) — bu fazaning birorta mezoni tashqi tarmoqqa chiqmaydi, ya'ni tarmoqni tutish vositasi faqat almashtirish yo'lini ochib qo'yardi"
  - "08-20: gate byudjeti KO'TARILMADI — eng yomon o'lchov 1909 s < 2300 s (D-26: byudjet shunchaki oshirilmaydi)"
  - "08-20: FOUND-07 `Done` QILINMADI va bu qoidaning o'zi — mexanizm uch qatlamda yashil, lekin zanjir BUGUNGACHA HECH QACHON yugurmagan"

patterns-established:
  - "AST darvozasining TETIGI ehtiyotkorlik bilan tanlanadi: «nomni ishlatgan» predikati nazorat testini ushlab qoladi, «javob haqida da'vo qilgan» predikati esa aynan taqiqning nishoniga tegadi"
  - "Reyestr nomlari (`_EXPORT_URL_NAMES`) NAZORAT testi bilan qulflanadi: har nom modul globali VA qiymati `.xlsx` tashishi tekshiriladi — eskirgan reyestr jimgina bo'shab qololmaydi"
  - "Sabotaj mahsulotni emas, O'LCHOV ASBOBINI tekshiradi — bu fazada u BESH marta testning o'z ko'r nuqtasini topdi"

requirements-completed: [RECON-04, RECON-05]

# Metrics
duration: 385min
completed: 2026-08-16
---

# Phase 8 Plan 20: Faza darvozasi Summary

**8-fazaning beshala ROADMAP mezoni `tests/integration/test_phase8_criteria.py` da BITTA buyruqda o'lchanadi; soxtalashtirishning ikki eng arzon yo'li (zaxira faktini qo'lda yozish va `.xlsx` ni baytsiz tasdiqlash) AST bilan mexanik yopildi; `gate` byudjeti tinch xostda o'lchanib 2300 s da QOLDI; RECON-04/05 dalil bilan `Done`, FOUND-07 esa sababi nomlangan holda `Blocked`.**

## Performance

- **Duration:** ~6 soat 25 daqiqa (shundan ~2 soat 10 daqiqa — `gate` o'lchovlari va ikki bekor qilingan urinish)
- **Started:** 2026-08-16T14:55:00Z
- **Completed:** 2026-08-16T19:20:00Z
- **Tasks:** 3/3
- **Files modified:** 6 (1 yaratildi, 5 tahrirlandi)

## Accomplishments

- **Beshala mezon bitta buyruqda** — `pytest tests/integration/test_phase8_criteria.py -q` 9 ta testni (5 mezon + 4 meta-darvoza) yashil beradi
- **Ikki yangi soxtalashtirish taqig'i mexanik reyestrda** — zaxira faktini qo'lda yozadigan xom SQL va baytsiz eksport da'vosi, ikkalasi ham `ast` daraxtidan
- **Beshala sabotaj o'lchandi** — har biri AYNAN o'z mezonini qizartirdi, qo'shnilari yashil qoldi
- **Byudjet o'lchandi va O'ZGARMADI** — 1909 / 1842 s, chegara 2300 s (zaxira 17 %)
- **FOUND-07 `Blocked` qilindi** — bu fazaning eng muhim halolligi: mexanizm to'liq, fakt esa hech qachon tug'ilmagan

## Task Commits

1. **Task 1: `test_phase8_criteria.py`** — `06325a1` (test)
2. **Task 2: `gate` byudjeti + `08-VALIDATION.md`** — `fe23db0` (docs)
3. **Task 3: Talab holatlari, ROADMAP va `deferred-items.md`** — `772f588` (docs)

## Files Created/Modified

- `tests/integration/test_phase8_criteria.py` — **YANGI**, 1767 qator: beshta mezon testi, meta-test, to'rt yo'lli soxtalashtirish darvozasi, reyestr nazorati va seed nazorati
- `package.json` — `//gate-budget` va `//gate-fast-budget` izohlariga 08-20 o'lchovi qo'shildi (chegara qiymatlari O'ZGARMADI)
- `.planning/phases/.../08-VALIDATION.md` — shablon holatidan to'liq kontraktga: 20 qatorli Per-Task map, 5 inson bandi, 6 avtomatlashtirilgan almashtirish, `nyquist_compliant: true`
- `.planning/REQUIREMENTS.md` — RECON-04/05 `Done`, FOUND-07 `Blocked`; «Qoidaning 8-fazadagi qo'llanishi» bo'limi dalil jadvali bilan
- `.planning/ROADMAP.md` — 08-20 belgilandi, Progress 20/20; ⛔ FAZA belgisi ATAYIN `- [ ]` qoldi
- `.planning/phases/.../deferred-items.md` — uch yangi jadval: eski yetti bandning holati, 13 WR + 8 Info ning nomma-nom hisobi, yettita yangi band

## Beshala sabotajning natijasi

⛔ **Har biri AYNAN bitta mezonni qizartirdi va qo'shnilari yashil qoldi.** Hammasi
`git status` toza holatga qaytarildi.

| # | Mezon | Sabotaj | Natija |
|---|-------|---------|--------|
| S-1 | SC#1 | `anomaly_archive_export` `.xlsx` o'rniga xom bayt qaytaradi (status 200 va `content-type` O'ZGARMAYDI) | ⛔ **AYNAN `test_sc1_*` QIZARDI** — `read_rows` faylni ocha olmadi (`import_not_a_zip`). Bu «`200` mezon EMAS» da'vosining bevosita isboti |
| S-2 | SC#2 | `accuracy_report()`: `false_empty` ning maxraji `truly_occupied` -> `n` | ⛔ **AYNAN `test_sc2_*` QIZARDI** — bo'sh qolishi kerak bo'lgan katak to'ldi |
| S-3 | SC#3 | `ops/backup/heartbeat.sql` da komponent nomi `'backup'` -> `'backup_ok'` | ⛔ **AYNAN `test_sc3_*` QIZARDI** — mahsulot skripti bajarilgandan keyin ham komponent `never_seen` da qoldi (`self_check.py` ogohlantirgan nosozlikning aynan o'zi) |
| S-4 | SC#4 | `_locale_of()` har doim `uz-Latn` qaytaradi | ⛔ **AYNAN `test_sc4_*` QIZARDI** — uch profil bir xil sarlavha berdi |
| S-5 | SC#5 | `_THREE_WAY` da `:ledger_over` va `:system_over` ALMASHTIRILDI | ⛔ **AYNAN `test_sc5_*` QIZARDI** — ikki sinf o'rin almashdi |

⚠ **S-5 NING BIRINCHI SHAKLI YARAMADI VA SABAB YOZILADI.** Avval
`WHEN ai_expected_soum <> system_soum THEN :ai_mismatch` -> `:match`
qilingan edi. U sistemaga yetib bordi, LEKIN natija **yig'ish xatosi**
bo'ldi (`sqlalchemy.exc.ArgumentError` — endi ishlatilmaydigan
`bindparam`), ya'ni BUTUN modul yiqildi va «qo'shnilari yashil qoladimi?»
degan yarim o'lchanmay qoldi. ⛔ **Dars: sabotaj modulni IMPORT
QILINADIGAN holda qoldirishi shart** — aks holda u mezonni emas,
yig'ilishni o'lchaydi.

## `gate` byudjetining o'lchovi

⛔ **HALOLLIK BANDI — UCH EMAS, IKKI O'LCHOV OLINDI.** Ijro paytida
tezlik ustuvor deb belgilandi va uchinchi o'lchov (~32 daqiqa)
**boshlanmadi**. «Uch marta o'lchandi» degan da'vo **BERILMAYDI**; agar
kelajakda darvoza byudjet sababli yolg'on qizil bersa, birinchi shubha
shu yerga tushadi. Qayd `package.json` izohida ham, `08-VALIDATION.md`
da ham AYNAN shu shaklda yozilgan.

| O'lchov | `gate` | `gate:fast` |
|---------|--------|-------------|
| 1 | **1909 s** (exit 0) | **155 s** (exit 0) |
| 2 | **1842 s** (exit 0) | **152 s** (exit 0) |
| Tarqoqlik | 67 s = **3,5 %** | 3 s = **1,9 %** |
| Chegara | 2300 s — ⛔ **O'ZGARMADI**, zaxira 391 s (17 %) | 200 s — ⛔ **O'ZGARMADI**, zaxira 45 s (23 %) |

**Tinch xost ta'minlandi va TIKLANDI:** oltita `parnikkpi-*` konteyner va
qayta-qayta yiqilib turgan `sbozor-bot-service-1` `docker stop` bilan
to'xtatildi, o'lchovdan keyin yettalasi ham `docker start` bilan
tiklandi. **Disk o'lchovdan OLDIN tekshirildi:** `C:` **84 % to'la,
28 GB bo'sh** — `STATE.md` dagi 91 % ogohlantirishidan yaxshiroq, ya'ni
`docker system prune` KERAK BO'LMADI.

⚠ **O'sish (+485 s, 07-17 ning 1424 s idan) degradatsiya EMAS:** to'rt
yangi integratsiya fayli, uch unit fayli, mezon fayli (30 hodisali doira
+ ikki `.xlsx` zanjiri), `test_restore_drill` ning **ikkinchi postgres
konteyneri** va ikki yangi SSG marshruti × 3 locale.

## Decisions Made

Yuqoridagi frontmatter `key-decisions` ro'yxatiga qo'shimcha ravishda ikki
band alohida izoh talab qiladi:

**1. SC#2 ning namunasi «bir tomonlama» qurildi va bu ATAYIN.** Doiraning
hammasi tizim tomonidan `occupied`, nazoratchi esa butun namunaga `empty`
javob beradi. Natijada `tp = fn = tn = 0` va matritsa shunday
joylashadi-ki, «band deb xato» ning maxraji (`tp+fp`) **musbat**, «bo'sh
deb xato» niki (`tp+fn`) esa **nol** bo'ladi. Ya'ni bitta varaqda
bittasi **son**, ikkinchisi **bo'sh katak** — va bu FAQAT maxrajlar
boshqa bo'lganda mumkin. Ikki xato bitta «xatolik ulushi» ga qo'shilganda
yoki umumiy maxraj (`n`) ishlatilganda ikkala katak ham to'lardi va
da'vo darhol qulardi. ⚠ Bu «yakka nol» EMAS (08-15 darsi): o'lchanmagan
katak **nol emas, bo'sh**.

**2. Determinizm ehtimollikka qoldirilmadi.** Doira 30 ta hodisadan
iborat va `eval` kvotasi 21 — ya'ni `MIN_SAMPLE_FOR_PERCENT` (20) dan
katta. Tenglik testning O'ZIDA, MAHSULOT funksiyasi (`eval_quota`) bilan
o'lchanadi, ya'ni chegara yoki kvota o'zgarsa nosozlik shu yerda, aniq
xabar bilan chiqadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Frontend bog'liqliklari muhitda umuman o'rnatilmagan edi**

- **Found during:** Task 2 (`gate` byudjetining o'lchovi, ikkinchi urinish)
- **Issue:** `npm run gate` 1767 soniyadan keyin `npm --prefix frontend test`
  da yiqildi: `"vitest" ... ��� ���譥� ��������`. O'lchandi:
  `frontend/node_modules` **BO'SH** (`ls | wc -l` -> 0), ildizdagisi ham.
  Ya'ni zanjirning frontend yarmi (vitest, typecheck, lint, build) UMUMAN
  yugura olmasdi va Task 2 ning qabul mezoni (`npm run gate` EXIT 0)
  bajarilmasdi.
- **Fix:** `npm ci` (frontend) — ⛔ **QULFLANGAN** `package-lock.json` dan,
  530 paket. Yangi paket nomi TANLANMADI, `package.json` ham,
  `package-lock.json` ham O'ZGARMADI (`git diff` bo'sh).
- **Nega bu paket-o'rnatish taqig'iga tushmaydi:** taqiqning sababi
  slopsquatting va o'ylab topilgan nom. Bu yerda birorta nom ijrochi
  tomonidan tanlanmagan — repoda qulflangan daraxt tiklandi (bu
  `uv sync --frozen` ning aynan jufti). Hech nima o'rnatishga
  URINMADI ham: `npm ci` lockfile bilan mos kelmasa YIQILARDI.
- **Verification:** `npm run gate:fast` EXIT 0 (vitest 1110 test, 94 fayl);
  keyin `npm run gate` ikki marta EXIT 0.
- **Committed in:** kod o'zgarishi YO'Q (`node_modules` gitignore'da);
  topilma `deferred-items.md` №13 ga yozildi.

**2. [Rule 1 - Bug] 4-darvozaning TETIGI yolg'on-qizil berdi va u ijro paytida toraytirildi**

- **Found during:** Task 1 (mezon modulining birinchi yugurishi)
- **Issue:** «Eksport da'vosi baytlarsiz qolmaydi» darvozasining birinchi
  shakli iste'molchini «modul nomini ISHLATGAN test» deb ta'riflagan edi.
  U nazorat testini (`test_the_module_measures_a_market_that_the_seed_
  actually_owns`) **YOLG'ON-QIZIL** qildi: o'sha test hujjat yo'llarini
  `app.openapi()` grafida izlaydi va birorta so'rov YUBORMAYDI.
- **Fix:** tetik «javob haqida DA'VO qildi» ga toraytirildi — iste'molchi
  eksport nomini ishlatgan VA `status_code` ga murojaat qilgan test.
  ⛔ Nom bo'yicha istisno ro'yxati ATAYIN yozilmadi: u darvozani
  bo'shatardi va keyingi ijrochi unga yangi nom qo'shib qutulardi.
  Tetikning O'ZI nazorat asserti bilan qulflandi (`httpx.Response(200)`
  da maydon mavjudligi).
- **Files modified:** `tests/integration/test_phase8_criteria.py`
- **Verification:** darvoza yashil, iste'molchilar soni 4 (quyi chegara 3);
  nazorat testi endi iste'molchi sifatida sanalmaydi.
- **Committed in:** `06325a1` (Task 1 commit)

**3. [Rule 3 - Blocking] Meros flake `gate` ning birinchi urinishini yiqitdi**

- **Found during:** Task 2 (`gate` ning birinchi urinishi)
- **Issue:** `test_phase5_criteria.py::test_sc4_*` `409 review_queue_empty`
  bilan yiqildi.
- **Fix:** ⛔ **TUZATILMADI (SCOPE BOUNDARY)** — u BOSHQA fazaning mezon
  fayli va bu rejaning `files_modified` ida YO'Q. O'rniga MEXANIZMI
  o'lchandi va `deferred-items.md` №12 ga yozildi: doira 8 hodisadan
  iborat (seed 2 + test 6), ulardan **4 tasi `uncertain`**, `audit_draw`
  esa 4 tasini tasodifiy tanlaydi — ya'ni **P = 1/C(8,4) = 1/70 ≈ 1,4 %**
  ehtimollik bilan noaniq navbatga hodisa QOLMAYDI.
- **Verification:** yakka holda **20/20 yashil** (6 + 14 yugurish);
  `test_blind_audit` + `test_uncertain_queue` + `test_phase5_criteria`
  birga — yashil; keyingi ikki to'liq `gate` yugurishida ham qaytmadi.
- **Committed in:** kod o'zgarishi YO'Q; band `772f588` da hujjatlashtirildi.

**4. [Rule 1 - Bug] GSD SDK handleri FAZA belgisini o'zi belgilab qo'ydi**

- **Found during:** holat yangilash bosqichi (uchala vazifa commitidan keyin)
- **Issue:** `roadmap update-plan-progress 8` hamma reja uchun SUMMARY
  borligini ko'rib `- [ ] **Phase 8: ...**` ni ⛔ **`- [x]`** ga
  aylantirdi va Progress qatorini `Complete` qildi. Bu ROADMAP ning O'Z
  **Note** bandiga hamda rejaning qat'iy shartiga ZIDDIR: fazani yopish
  qarori **qayta tekshiruvniki**.
- **Fix:** `git checkout -- .planning/ROADMAP.md` — belgi `- [ ]` ga,
  qator «Ijro tugadi (qayta tekshiruv kutilmoqda)» ga qaytarildi.
- **Verification:** `sed -n '53p;617p' .planning/ROADMAP.md` — belgi
  `- [ ]`, qator to'g'ri; `git status` toza.
- **Committed in:** qaytarish `772f588` dagi holatni saqladi; ogohlantirish
  `deferred-items.md` №14 ga yozildi.

---

**Total deviations:** 4 auto-fixed (2 blocking, 2 bug)
**Impact on plan:** Ikkitasi ijro muhitiga tegishli (bog'liqlik va meros
flake), bittasi darvozaning O'Z predikatiga, bittasi esa VOSITA bilan
QOIDA ziddiyatiga. Qamrov kengaymadi: birorta mahsulot fayli
tahrirlanmadi.

## Issues Encountered

1. **Ikki `gate` urinishi bekor qilindi** — birinchisi meros flake bilan
   (1633 s), ikkinchisi frontend bog'liqliklari yo'qligi bilan (1767 s).
   Ikkalasi ham o'lchov sifatida HISOBGA OLINMADI va sabab yuqorida
   nomma-nom.
2. **Uchinchi o'lchov boshlanmadi** — tezlik ustuvor deb belgilandi.
   Protokol ikki o'lchovga qisqartirildi va bu SUMMARY da,
   `package.json` izohida hamda `08-VALIDATION.md` da ochiq yozildi.
3. **GSD SDK ning `roadmap update-plan-progress` handleri faza belgisini
   o'zi belgiladi** — darhol qaytarildi va ogohlantirish
   `deferred-items.md` №14 ga yozildi. ⚠ 4–7-fazalarda bu bosqich,
   ehtimol, umuman chaqirilmagan: shuning uchun ziddiyat bugungacha
   ko'rinmagan.
4. **`.env` da RESTIC kalitlari yo'q** — bu nosozlik EMAS, ochiq band:
   `backup_stale` (CRITICAL) go-live'dan keyin ham chiqib turadi va ⛔
   uni o'chirish TAQIQ. FOUND-07 ning `Blocked` sababida va
   `deferred-items.md` №11 da yozilgan.

## Known Stubs

None — bu reja mahsulot kodini umuman o'zgartirmadi.

## Threat Flags

Yangi xavfsizlik yuzasi YO'Q: reja birorta marshrut, migratsiya yoki
huquq qo'shmadi. Mezon moduli faqat MAVJUD yuzalarni o'qiydi va o'zining
uch darvozasi (`T-08-89`, `T-08-90`, `T-08-91`) reja `threat_model` ida
`mitigate` sifatida yozilgan holicha bajarildi.

## User Setup Required

**Beshta band `08-HUMAN-UAT.md` da, ega va tetik bilan** — ulardan
uchtasi FOUND-07 ni bloklaydi:

1. REAL toza serverda REAL offsite repodan tiklash mashqi (Ops, VPS deploy)
2. `RESTIC_PASSWORD` ning saqlangan joyi va ikkinchi egasi (Ops)
3. Offsite S3 hisobi va `RESTIC_REPOSITORY` (Ops / buyurtmachi)
4. Uch tilli yakuniy tekshiruv — kassir, nazoratchi, admin (mahsulot egasi)
5. `npm run up` ning dev mashinasida tasdiqlanishi (Ops / dasturchi)

## Next Phase Readiness

- ✅ **Faza darvozasi tayyor:** `/gsd-verify-work` uchun yagona kirish
  nuqtasi — `pytest tests/integration/test_phase8_criteria.py -q`
- ✅ **ROADMAP dagi FAZA belgisi ATAYIN `- [ ]`** — yopish qarori qayta
  tekshiruvniki, ijrochi emas (4–7-fazalarda aynan shunday saqlangan)
- ⚠ **`gate` zaxirasi torayib bormoqda:** 391 s (17 %). Qayta o'lchov
  9-fazaning bandi.
- ⛔ **FOUND-07 ochiq va u go-live'ning yo'lida turadi** — offsite repo
  sozlanmaguncha kunlik zaxira UMUMAN olinmaydi.

---
*Phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish*
*Completed: 2026-08-16*

## Self-Check: PASSED

Barcha da'volar o'lchandi:

- **Fayllar (7/7 topildi):** `tests/integration/test_phase8_criteria.py`,
  `package.json`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`,
  `08-VALIDATION.md`, `deferred-items.md`, `08-20-SUMMARY.md`
- **Commitlar (3/3 topildi):** `06325a1`, `fe23db0`, `772f588`
- **Darvozalar:** `pytest tests/integration/test_phase8_criteria.py -q` — **9 passed**;
  `node scripts/check-requirements-sync.mjs` — **EXIT 0** (Done 41 · Pending 5 · Blocked 3);
  `npm run validation:check` — **EXIT 0** (20 qator · 5 inson bandi);
  `npm run gate` — **EXIT 0** (ikki marta: 1909 s, 1842 s)
