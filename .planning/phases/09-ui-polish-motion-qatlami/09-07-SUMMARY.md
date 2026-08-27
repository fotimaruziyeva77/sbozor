---
phase: 09-ui-polish-motion-qatlami
plan: 07
subsystem: ui
tags: [phase-gate, roadmap-parse, node-test, budget, human-uat, monday-blindness]
requires:
  - "09-01..09-06: yettala G-motion darvozasi va mahsulot qatlami (xoreografiya, dashboard, temalar, tipografiya)"
  - "08-20: mezon-modul naqshi (zanjir, takror emas) va byudjet o'lchov protokoli (05-15 W0-13)"
provides:
  - "frontend/scripts/phase9-criteria.test.mjs — beshala ROADMAP mezoni BITTA buyruqda (8 test: 5 mezon + META + soxtalashtirish + reyestr)"
  - "gate/gate:fast byudjet qarori: IKKALASI O'ZGARMADI (2259/2102 < 2300; 189/171 < 200) — package.json izohlarida yangi xatboshi"
  - "09-VALIDATION.md imzolangan (nyquist_compliant: true, signoff exit 0); 09-HUMAN-UAT.md besh bandi OCHIQ (raqamsiz, ega+tetik bilan)"
  - "deferred-items.md yakunlangan: konfetti holati + gate zaxirasi 1,8% + dushanba-ko'rlik sinfi"
affects:
  - "/gsd-verify-work (fazani yopish qarori — HUMAN-UAT №1/№2/№5 tetigi)"
  - "10-faza rejalashtiruvchisi (gate byudjeti KRITIK TOR — deferred №2)"
tech-stack:
  added: []
  patterns:
    - "Mezon moduli darvozalarni QAYTA YUGURTIRMAYDI — zanjir dalili (fayl + CI glob) va mahsulot dalili (src/, package.json) juftligi; spawn taqiqi o'z manbasida mexanik"
    - "ROADMAP prozasiga bog'lanish FAQAT mezon modulida va ATAYLAB — langar so'zlar jumla o'zgarganda darvozani qizartiradi"
    - "Vaqtga bog'liq test yiqilishi ikki sinfga ajratiladi: deterministik (kun jadvali — tuzatiladi) va ehtimoliy (meros flake — jurnalga)"
key-files:
  created:
    - frontend/scripts/phase9-criteria.test.mjs
    - .planning/phases/09-ui-polish-motion-qatlami/09-07-SUMMARY.md
  modified:
    - tests/integration/test_billing_api.py
    - tests/integration/test_phase6_criteria.py
    - package.json
    - .planning/phases/09-ui-polish-motion-qatlami/09-HUMAN-UAT.md
    - .planning/phases/09-ui-polish-motion-qatlami/09-VALIDATION.md
    - .planning/phases/09-ui-polish-motion-qatlami/deferred-items.md
decisions:
  - "Mezon moduli 8 testdan iborat va .planning/ ni FAQAT u o'qiydi — boshqa darvozalar prozaga bog'lanmaydi (02-22 darsi saqlangan)"
  - "Byudjetlar protokol bo'yicha KO'TARILMADI (eng yomon < chegara), LEKIN zaxira 1,8% KRITIK TOR deb nomlandi va egasi 10-faza rejalashtiruvchisiga biriktirildi"
  - "Dushanba-ko'rlik Rule 3 bilan tuzatildi (meros flake №12 esa TEGILMADI) — farq: deterministik kun-bog'liqlik to'liq zanjirni bloklaydi, 1,4% ehtimoliy flake bloklamaydi"
  - "HUMAN-UAT beshala bandi RAQAMSIZ OCHIQ qoldi (orkestrator chegarasi): real qurilma/inson idroki o'lchovlari olinmagan — mexanik yashillik bilan yopilmaydi"
metrics:
  duration: "~180 min (shundan ~130 min — to'rt to'liq gate urinishi: 2 yaroqli + 2 yaroqsiz)"
  completed: "2026-08-17"
  tasks: 3
  commits: 5
  tests_added: 8
requirements: [SC-1, SC-2, SC-3, SC-4, SC-5]
---

# Phase 9 Plan 07: Faza darvozasi — phase9-criteria, byudjet qayta o'lchovi, HUMAN-UAT Summary

**Beshala ROADMAP Phase 9 mezoni endi BITTA buyruqda o'lchanadi (`node --test frontend/scripts/phase9-criteria.test.mjs` — mahsulot dalili + zanjir dalili juftligi, uch sabotaj isboti bilan); to'liq `npm run gate` bu fazada BIRINCHI marta backend yarmi bilan ikki marta exit 0 (2259/2102 s) va ikkala byudjet O'ZGARMADI; yo'lda birinchi DUSHANBA yugurishi ikki billing testining kun-ko'rligini fosh qildi (Rule 3 bilan tuzatildi), beshala inson bandi esa orkestrator qarori bilan RAQAMSIZ OCHIQ qoldirildi.**

## Bajarilgan vazifalar

| # | Vazifa | Commit |
|---|--------|--------|
| 1 | `phase9-criteria.test.mjs` — 5 mezon + META (ROADMAP parse, aynan 5, langar so'zlar) + soxtalashtirish darvozasi (`import.meta.filename`) + reyestr nazorati (takrorsizlik, 18 nom, pollar 14/7, spawn taqiqi); uch sabotaj IKKI natija bilan | `7be12bb` |
| — | Deviatsiya (Rule 3): dushanba-ko'rlik — ikki backend testiga ochiq-kun prekonditsiyasi | `11a4f3a` |
| 2 | Byudjet qayta o'lchovi (05-15 W0-13): tinch xost, IKKI to'liq `gate` (2259/2102 s, exit 0) + IKKI `gate:fast` (189/171 s, exit 0); qaror ikkala izohga yangi xatboshi bo'lib yozildi, eski matn saqlangan | `a0a70bd` |
| 3 | Checkpoint qaytarildi → orkestrator qarori bilan yakun: VALIDATION imzosi (signoff exit 0), HUMAN-UAT besh bandi OCHIQ, deferred-items (+2 yangi band) | `8d1b942` |

## Byudjet o'lchovi (05-15 W0-13 protokoli) — halollik bandlari bilan

| O'lchov | Natija | Davomiylik | Holat |
|---------|--------|------------|-------|
| gate №1 (10:15) | exit=1 | 1871 s | **YAROQSIZ** — zanjir backend'da uzildi: dushanba-ko'rlik (2 test, `market_closed`) |
| gate №1B (11:00) | exit=1 | 1871 s | **YAROQSIZ** — meros flake №12 (`test_phase5_criteria::test_sc4`, 1/70) bir marta tripladi; 08-20 qarori bo'yicha TEGILMADI |
| **gate №1C (11:38)** | **exit=0** | **2259 s** | 1-yaroqli o'lchov |
| **gate №2 (12:24)** | **exit=0** | **2102 s** | 2-yaroqli o'lchov |
| gate:fast №1 | exit=0 | 189 s | |
| gate:fast №2 | exit=0 | 171 s | |

- **Qaror:** ikkala byudjet **O'ZGARMADI** (protokol: eng yomon < chegara). `gate` zaxirasi **41 s (1,8 %)** — KRITIK TOR, `gate:fast` zaxirasi **11 s (5,5 %)** — TOR; ikkalasi `deferred-items.md` №2 da egali band.
- ⛔ **HALOLLIK: UCH EMAS, IKKI yaroqli o'lchov** (08-20 presedenti, orkestrator tezlikni ustuvor belgiladi). Tarqoqlik: gate 157 s (7,0 %), fast 18 s (9,5 %).
- ⛔ **«Tuzatishdan oldingi toza yugurishni hisobga olish» QO'LLANMADI** — tuzatishdan oldingi TOZA to'liq yugurish umuman YO'Q (ikkala urinish zanjir yarmida uzilgan).
- Tinch xost: 6 `parnikkpi-*` + restart halqasidagi `sbozor-bot-service-1` to'xtatildi va o'lchovdan keyin TIKLANDI.
- Zanjir boshidagi majburiy nazorat (deferred №13 darsi): `npm --prefix frontend ls` exit 0 — `node_modules` joyida, `npm ci` KERAK BO'LMADI.
- O'sish to'plamniki: skript-darvozalar ~296 → **349**, vitest 1110 → **1170**; A3 taxminining (~40–60 s) pastki yarmi ro'yobga chiqdi (`gate:fast` +34 s).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Bloklovchi] Billing testlarining dushanba-ko'rligi**
- **Topildi:** Task 2, birinchi to'liq gate o'lchovida — bu zanjirning tarixdagi BIRINCHI dushanba yugurishi
- **Muammo:** seed A bozori dushanba YOPIQ (`A_OPEN_WEEKDAYS = 2..7`); `test_billing_api::test_a_stall_in_maintenance_...` (pending `amount_soum=None`) va `test_phase6_criteria::test_sc5_...` (POST 422 `market_closed`) «bugun ochiq kun» prekonditsiyasini o'rnatmagan — dushanba kunlari DETERMINISTIK qizil, boshqa kunlari yashil
- **Tuzatish:** har ikkala testning arrange qadamiga `open_weekdays = 1..7` UPDATE (`test_market_calendar.py` naqshi); da'volar TEGILMADI, mahsulot yo'liga NOL ta'sir; backend'da 08-20 dan beri nol diff — 9-faza sababchi emas
- **Nega №12 dan farq qiladi:** meros flake ehtimoliy (1,4 %) va qayta yugurishda o'tadi — u TEGILMADI; bu esa deterministik va butun kun to'liq zanjirni imkonsiz qilardi (Task 2 ning o'zi bloklangan)
- **Fayllar:** `tests/integration/test_billing_api.py`, `tests/integration/test_phase6_criteria.py` · **Commit:** `11a4f3a`
- **Sinf sifatida:** `deferred-items.md` №3 — boshqa testlarda ham shu yashirin prekonditsiya bo'lishi mumkin

**2. [Rule 1 - Reja matnidagi noaniqlik] 150ms o'lchovining joyi**
- **Topildi:** Task 1, SC#4 zanjir dalilini yozishda
- **Muammo:** reja «`success-choreography.test.tsx` matnida `matchMedia` stubi va 150ms o'lchovi bor» degan; haqiqatda `matchMedia` stubi o'sha faylda, **150ms o'lchovi esa `collect-session.test.tsx` da** (`advanceTimersByTimeAsync(150)` — G-motion-2(a,b) egasi, 09-04 da shunday qurilgan)
- **Tuzatish:** SC#4 testi ikkala faylni ham tekshiradi — stub choreography-testda, 150ms collect-session-testda; izoh modulda ochiq yozilgan
- **Fayl:** `frontend/scripts/phase9-criteria.test.mjs` · **Commit:** `7be12bb`

**3. [Rule 3 - Checkpoint muhiti] Frontend konteyneri eskirgan build bilan ishlab turgan edi**
- **Topildi:** Task 3 checkpoint'idan oldin (avtomatlashtirish-birinchi tamoyili)
- **Muammo:** `sbozor-frontend-1` imiji 9-faza kodidan OLDIN qurilgan — UAT eski UI'ni ko'rsatardi; qayta qurishda esa `depends_on` zanjiri core-api'ni ham qayta yaratdi va xost `:8000` bandligi (`parnikkpi-backend-1` tiklashda egallagan) bind xatosi berdi; 23 soatlik nginx eski frontend IP'sini keshlab 502 qaytardi
- **Tuzatish:** frontend joriy kod bilan qayta qurildi; core-api `compose.override.yml` ning o'z hujjatlashtirilgan mexanizmi bilan vaqtincha `API_HOST_PORT=8010` da (`127.0.0.1:8010/healthz` → 200, `.env` TEGILMADI); `docker restart sbozor-nginx-1` → `/uz/collect` 200; servis qilinayotgan HTML'da 9-faza markerlar (`sbozor-theme` skripti, `suppressHydrationWarning`) tasdiqlandi
- **Commit:** yo'q (faqat lokal muhit — kod/konfiguratsiya o'zgarmadi)

### Rejalashtirilgan oqim eslatmalari (deviatsiya emas)

- **Checkpoint orkestrator tomonidan hal qilindi:** mexanik qatlam tasdiqlandi, LEKIN beshala inson bandiga ⛔ RAQAM YOZILMADI va birortasi «bajarildi» deb belgilanmadi — o'lchovlar real qurilma/inson idrokini talab qiladi va olinmagan. №1/№2 tetigi «birinchi deploy yoki `/gsd-verify-work`», №3/№4 pilot haftasi, №5 o'zgarishsiz.
- **`requirements mark-complete` O'TKAZIB YUBORILDI:** SC-1..SC-5 `REQUIREMENTS.md` da mavjud emas (ROADMAP A7 qarori: yangi REQ-ID yaratilmaydi, fayl tegilmaydi) — grep 0 natija bilan tasdiqlandi.

## Sabotaj jurnali (3/3 — har birida IKKI natija, fayllar yig'iladigan holda)

| # | Sabotaj (REAL manba ustida) | Nishon | Qo'shnilar |
|---|------------------------------|--------|------------|
| S1 | `collect-surface.test.mjs` `MIN_FORBIDDEN_NAMES` 14 → 10 | **SC#5 QIZARDI** («= 10 — 14 dan KAMAYTIRISH TAQIQ») | **7/8 yashil**; fayl parse OK (`node --check`) |
| S2 | `collect-session.tsx` da xoreografiya chaqiruvi `focus()` dan OLDINGA ko'chirildi | **SC#1 QIZARDI** («focus()dan OLDIN chaqirilgan — scroll-anchoring») | **7/8 yashil**; `tsc --noEmit` exit 0 |
| S3 | `globals.css` dan `[data-theme="sun"]` bloki (1725 belgi) olib tashlandi | **SC#3 QIZARDI** («scope bloki TOPILMADI») | **7/8 yashil**; CSS yaroqli qoldi |

Uchalasi ham qaytarildi — S2/S3 dan keyin `git diff` NOL; yakuniy to'plam 349/349.

## TDD Gate Compliance

Task 1 `tdd="true"` (darvoza-fayl): `test(09-07)` `7be12bb` — RED bosqichi sog'lom bazada YASHIL chiqdi va bu KUTILGAN (09-06 Task 4 presedenti): o'lchanadigan holat 09-01..09-06 da allaqachon qurilgan, modulning butun maqsadi — o'sha holatning ROADMAP jumlalari bilan mosligini qulflash. Falsifikatsiya qatlamini REJA TALAB QILGAN uch sabotaj berdi (S1→SC#5, S2→SC#1, S3→SC#3 — har biri qo'shni 7/8 yashil bilan). Birinchi yugurishdagi yagona qizil (SC#3) test-kodning o'z nuqsoni edi (`u`-bayroqli regexda yaroqsiz escape) va `feat` emas, modul ichida tuzatildi — mahsulot nuqsoni topilmadi.

## Verifikatsiya natijalari

| Buyruq | Natija |
|--------|--------|
| `node --test scripts/phase9-criteria.test.mjs` | **8/8** (5 mezon + META + soxtalashtirish + reyestr) |
| `node --test scripts/*.test.mjs` | **349/349** (23 skript-darvoza; mavjud 341 tasi REGRESSIYASIZ) |
| `npm run gate` (to'liq, backend yarmi bilan) | **exit 0 × 2** (2259 s / 2102 s — bu fazada BIRINCHI to'liq yugurish) |
| `npm run gate:fast` | **exit 0 × 2** (189 s / 171 s) |
| `node scripts/check-validation-signoff.mjs` | **exit 0** — `nyquist_compliant: true` hisob-kitob bilan MOS (7 qator yashil, 5 inson bandi to'liq) |
| `>-`/`\|` skalyar nazorati | 0 ta |
| vitest (gate ichida) | **1170/1170** (99 fayl) |

## Muhit eslatmalari (verify bosqichi BILISHI SHART)

- **Frontend** `http://localhost:8081` da JORIY kod bilan qayta qurilgan (prod build, nginx orqali); telefon uchun ayni tarmoqda `http://192.168.137.54:8081` (LAN IP o'zgaruvchan). Lighthouse/60fps o'lchovi AYNAN shu prod-build ustida olinsin, dev-serverda EMAS.
- **core-api vaqtincha `127.0.0.1:8010`** da (`compose.override.yml` ning `API_HOST_PORT` mexanizmi, `.env` tegilmagan): xost `:8000` ni `parnikkpi-backend-1` band qilgan. Keyingi `npm run up` parnikkpi ishlab turganda ayni to'qnashuvni beradi — `API_HOST_PORT=8010` bilan chaqirilsin yoki `.env` da ochilsin.
- **`sbozor-bot-service-1` restart halqasida** — bu o'lchovdan OLDINGI holat va u TIKLANGAN (yashirilmagan); UAT yuzalariga (collect/dashboard/reports) aloqasi yo'q.
- `sbozor-cv-service-1` 2 kun oldin Exited (137) — tegilmadi (o'lchovdan oldin ham shunday edi).

## Known Stubs

Yo'q — mezon moduli 8 testining hammasi jonli o'lchov; HUMAN-UAT bandlari stub emas, EGALI ochiq o'lchovlar (mexanik yashillik bilan yopish TAQIQLANGANI faylning o'zida yozilgan).

## Threat Flags

Yo'q — yangi endpoint, sir yoki paket yo'q. Reja `<threat_model>` mitigatsiyalari bajarildi: T-09-21 (soxtalashtirish darvozasi — har SC bloki mahsulot yo'liga murojaat qiladi, META ROADMAP'dan 5 ni parse qiladi, uch sabotaj), T-09-22 (`check-validation-signoff` yashil, har band ega+tetik bilan), T-09-04 (SC#5 pollar 14/7 — S1 isboti), T-09-SC (`dependencies` tengligi ikkinchi joyda, importsiz — 05-15 darsi).

## Self-Check: PASSED

- FOUND: frontend/scripts/phase9-criteria.test.mjs (`ROADMAP` ✓)
- FOUND: 09-VALIDATION.md (`nyquist_compliant: true` ✓) · 09-HUMAN-UAT.md · deferred-items.md
- FOUND: commit 7be12bb · 11a4f3a · a0a70bd · 8d1b942
