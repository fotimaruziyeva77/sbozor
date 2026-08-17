---
phase: 10-landing-sbozor-uz
plan: 08
subsystem: phase-gate-budgets-requirements
tags: [phase-gate, criteria, error-codes, budgets, w0-13, requirements, validation, human-uat]
requires:
  - "10-01 (test_demo_request.py, DEMO_ERROR_CODES, EXEMPT_ROUTES yozuvi)"
  - "10-07 (landing-surface.test.mjs to'rt darvozasi, page.tsx kompozitsiyasi)"
provides:
  - "frontend/scripts/phase10-criteria.test.mjs — beshala ROADMAP SC + META + soxtalashtirish + reyestr nazorati BITTA buyruqda (8 test)"
  - "error-codes.test.mjs oltinchi juftlik — DEMO_ERROR_CODES backend langari → demo-errors.ts ko'zgusi (ikki yo'nalish) → landing.form.* uch tilda"
  - "gate byudjetlari W0-13 bilan qayta o'lchangan: gate:fast 200→300 (249/175/175), gate 2300 QOLADI (2227/1856/1760)"
  - "LAND-01…05 REQUIREMENTS.md da (01…04 Done dalil bilan, 05 Blocked); Coverage 49→54"
  - "10-VALIDATION.md approved/nyquist_compliant; 10-HUMAN-UAT.md olti band (№2 SON bilan yopiq)"
affects:
  - "verify-work (faza yopilishi qarori — ROADMAP belgisi ataylab '- [ ]')"
  - "11-faza rejalashtiruvchisi (gate zaxirasi 73 s / 3,3% — tor)"
tech-stack:
  added: []
  patterns:
    - "assertChainPytest — mezon modulining YANGI zanjir turi: backend dalil fayli tests/integration/ ostida ekanini tasdiqlaydi (gate zanjiri uni avtomatik yugurtiradi)"
    - "SOXTALASHTIRISH darvozasi src/ + services/ + tests/ + package.json to'rt manba sinfiga kengaytirildi (9-fazada ikki edi)"
    - "W0-13 uch-o'lchov: yaroqsiz urinishlar (fon-seans uzilishi, flake) nomma-nom jurnalda, «uch marta o'lchandi» faqat yaroqlilar uchun"
key-files:
  created:
    - frontend/scripts/phase10-criteria.test.mjs
    - .planning/phases/10-landing-sbozor-uz/10-HUMAN-UAT.md
  modified:
    - frontend/scripts/error-codes.test.mjs
    - package.json
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .planning/phases/10-landing-sbozor-uz/10-VALIDATION.md
key-decisions:
  - "gate:fast chegarasi 300, reja mo'ljallagan 250 EMAS — o'lchangan eng yomon 249 s bilan 250 chegarasi 0,4% zaxira berardi (tarqoqlik 29,7% ichida); W0-13 formulasi (eng yomon × 1,20 → 300) qo'llandi, rejaning '250 qat'iy emas' bandi asosida"
  - "LAND-05 Blocked — Lighthouse ≥95 va LCP <1,5 s CI'da umuman o'lchanmaydi; mexanika yashilligi bilan o'lchov yo'qligini yopish TAQIQ (T-10-22)"
  - "requirements.mark-complete SDK verbi ATAYIN chaqirilmadi — LAND-05 Blocked holatini [x] bilan buzardi; holatlar qo'lda dalil jadvali bilan qo'yilib check-requirements-sync exit 0 bilan qulflangan"
  - "HUMAN-UAT №2 (payload) 10-03 ning haqiqiy o'lchovi bilan SON asosida yopildi; qolgan besh band raqamsiz OCHIQ — raqam uydirilmadi"
metrics:
  duration: "~3h 43m (shundan ~2h 40m — uchta to'liq gate o'lchovi)"
  completed: "2026-08-17T19:14:46Z"
  tasks: 3
  commits: 3
---

# Phase 10 Plan 08: Faza darvozasi, byudjetlar va LAND talablari Summary

**Bir qator:** `phase10-criteria.test.mjs` beshala ROADMAP mezonini BITTA buyruqda o'lchaydi (mahsulot + zanjir dalili, yangi `assertChainPytest` bilan backend qatlamiga ham), `DEMO_ERROR_CODES` oltinchi juftlik bilan ikki yo'nalishda qulflandi, `gate` UCH yaroqli o'lchovda 2300 da qoldi (2227/1856/1760, zaxira 73 s), `gate:fast` esa o'lchov asosida 200→300 ga ko'tarildi (249/175/175 — rejadagi 250 o'lchov bilan bekor bo'ldi) va LAND-01…05 REQUIREMENTS'ga dalil jadvali bilan tug'ildi (04 Done, LAND-05 halol Blocked).

## Bajarilgan vazifalar

| # | Vazifa | Commit | Kalit fayllar |
|---|--------|--------|---------------|
| 1 | phase10-criteria darvozasi + DEMO_ERROR_CODES oltinchi juftligi | `7364e21` | frontend/scripts/phase10-criteria.test.mjs, error-codes.test.mjs |
| 2 | gate/gate:fast byudjetlarining W0-13 qayta o'lchovi | `c9e6898` | package.json (ikkala jurnal izohi) |
| 3 | LAND-01…05, VALIDATION yakuni, olti bandli HUMAN-UAT, ROADMAP | `adc1261` | .planning/REQUIREMENTS.md, ROADMAP.md, 10-VALIDATION.md, 10-HUMAN-UAT.md |

## Nima qurildi

- **`phase10-criteria.test.mjs` (8 test, hammasi yashil):** har SC uchun (i) MAHSULOT dalili (`src/`, `services/`, `tests/`, `package.json` o'qiladi) va (ii) ZANJIR dalili (o'lchaydigan test fayli CI glob'ida). Yangi `assertChainPytest` — SC#3 ning backend dalili `tests/integration/test_demo_request.py` da; META ROADMAP'dan AYNAN 5 mezonni 5 langar regex bilan parse qiladi; SOXTALASHTIRISH darvozasi har SC blokini mahsulot yo'liga majburlaydi; REYESTR NAZORATI spawn'ni taqiqlaydi. SC#1 ga ENVIRONMENT_FALLBACK regressiya quli kirdi (`app-providers.tsx` da `timeZone: string;` majburiy prop + uzatish — 10-07 tuzatishining quli).
- **Sabotaj o'lchovi (reja talabi, ikkalasi ham QAYTARILDI):** SC#2 bloki konstanta bilan almashtirildi → SOXTALASHTIRISH qizardi (7 pass / 1 fail); ROADMAP'dan 3-mezon vaqtincha o'chirildi → META qizardi. Ikkala sabotajda modul import bo'ladigan holda qoldi.
- **`error-codes.test.mjs` oltinchi juftlik (3 yangi test):** `schemas.py::DEMO_ERROR_CODES` (frozenset, AYNAN 4 kod — nazorat) → `lib/demo-errors.ts` ko'zgusi IKKI yo'nalishda (yetishmagan ham, ortiqcha ham xato) → `demoErrorMessageKey` har kodni xaritalaydi → `landing.form.*` kaliti uchala tilda. Variant A (backend langar) — mahalliy switch darvozada ko'r nuqta qoldirardi (RESEARCH №3 qarori).
- **Byudjetlar (W0-13, tinch xost — 6 `parnikkpi-*` + restart halqasidagi `sbozor-bot-service-1` to'xtatilib o'lchovdan keyin TIKLANDI):**
  - `gate` UCH yaroqli o'lchov: **2227 / 1856 / 1760 s** (uchalasi exit 0, tarqoqlik 467 s / 21,0% — birinchi o'lchov sovuq keshda). Eng yomon 2227 < 2300 → **byudjet O'ZGARMAYDI**, zaxira 73 s (3,3%) — 11-faza birinchi qo'shimchasida qayta baholasin.
  - `gate:fast` UCH yaroqli o'lchov: **249 / 175 / 175 s** → chegara **300** (eng yomon × 1,20 = 298,8 → 50 ga yaxlitlab). 09-07 bashorati aynan ro'yobga chiqdi (189 → 249, landing testlari qo'shildi).
  - To'plam o'sishi: backend pytest 3101→3191 (+90), vitest 1170→1197 (+27), skript darvozalari 349→386 (+37), SSG 83→86 marshrut.
- **REQUIREMENTS.md:** yangi `### Landing (LAND)` bo'limi + Traceability + «Qoidaning 10-fazadagi qo'llanishi» dalil jadvali (har qator: nima o'lchandi QAYSI test bilan / nima o'lchanMAGAN). LAND-01…04 `Done`, LAND-05 `Blocked` to'liq sabab bilan. Coverage 49→54, faza kesimiga 10-qator (9-faza yo'qligi izohlangan).
- **10-VALIDATION.md:** `status: approved`, `nyquist_compliant: true`, `wave_0_complete: true`; olti `human_only_verifications` + olti `automated_replacements` (hammasi BIR qatorli qiymatlar, `>-` 0); per-task xarita P-01…P-08 hammasi ✅; signoff exit 0.
- **10-HUMAN-UAT.md:** olti band, har biri ega/tetik/SON sharti bilan. №2 (payload farqi) 10-03 ning haqiqiy `next build` jadvali bilan YOPIQ (ildiz 287,8→208,4 KB gz, −79,4; ru anonim jami ~103,7 KB kam). №4 da T-10-25 PII intizomi LITERAL (sinovlar faqat soxta ism/telefon bilan).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] package.json jurnal kalitlari noto'g'ri joyga yozilgan edi — tuzatildi va commit amend qilindi**
- **Found during:** Task 2 (jurnal yozuvi)
- **Issue:** Jurnal izohlari (`//gate-budget`, `//gate-fast-budget`) `scripts` obyekti ICHIDA yashaydi; birinchi yozuv ularni top-level'da `"undefined ..."` prefiksi bilan YANGI kalit qilib yaratdi. ⚠ Rejaning o'z `<automated>` verify buyrug'i ham AYNAN shu noto'g'ri top-level manzilni o'qiydi — u xato tufayligina yashil bo'lgan.
- **Fix:** Matn `scripts` ichidagi haqiqiy kalitlarga ko'chirildi, bogus kalitlar o'chirildi, verify `p.scripts[...]` bilan qayta yugurtirildi (OK), commit amend qilindi. Yakuniy diff faqat ikki jurnal satri (2+/2−).
- **Files modified:** package.json
- **Commit:** `c9e6898`

**2. [Rule 1 - meros nomuvofiqlik] FOUND-07 checkbox jadvalga moslandi**
- **Found during:** Task 3 (`check-requirements-sync` birinchi yugurishda exit 1)
- **Issue:** FOUND-07 ro'yxatda `[x]`, jadvalda `Blocked` — 08-20 dan beri qizil turgan (03-14 dagi CAM-02 presedentining aynan takrori: «darvoza bor, lekin hech kim bosmaydi»). Bu mening verify buyrug'imni bloklardi.
- **Fix:** Jadval to'g'ri (08-20 dalil bo'limi `Blocked` deydi) → belgi `- [ ]` ga moslandi, sabab REQUIREMENTS changelog'ida yozildi.
- **Files modified:** .planning/REQUIREMENTS.md
- **Commit:** `adc1261`

### Reja moslashuvlari (o'lchov bilan)

**3. [Byudjet] `gate:fast` chegarasi 250 emas — 300**
- Reja 250 ni mo'ljallagan edi (RESEARCH ~+5…7 s kutgan, eng yomon ~196 chiqadi degan hisob). O'lchov boshqacha chiqdi: eng yomon **249 s** — 250 chegarasi 1 s (0,4%) zaxira berardi, tarqoqlik esa 74 s (29,7%). Bunday chegara nuqson sababli EMAS tripplashi kafolatlangan — W0-13 ning o'z maqsadiga zid. Rejaning o'zida «250 raqami qat'iy emas» va «chegara o'lchovdan HOSILA» literal yozilgan; formula qo'llandi (249 × 1,20 = 298,8 → 300). Jurnalda to'liq asoslangan.

**4. [SC#1 dalili] prerender-manifest kalitlari ICHKI locale segmenti bilan**
- Reja `/uz`, `/uz-cyrl`, `/ru` ni tekshirishni aytgan edi (URL prefikslari). O'lchov: manifest marshrutlarni `/uz-Latn`, `/uz-Cyrl`, `/ru` bilan saqlaydi (prefikslar `routing.ts::localePrefix.prefixes` da xaritalanadi). Reyestr o'lchangan haqiqatga qadalgan, sabab test izohida.

**5. [SC#4 dalili] `sampleBadge` faqat hero-scene'da**
- Reja «`trust-block.tsx`, `pilot.tsx`, `hero-scene.tsx` da `sampleBadge`» degan edi; mahsulotda belgi FAQAT `hero-scene.tsx` da (u yagona soxta-raqamli sahna). Trust-block/pilot uchun dalil ularning haqiqiy halollik yuzasiga moslandi: `trustBlock.*` katalog o'qishi, `pilot.status` rozetkasi, `landing.pilot.*` va `residency.body` katalog skani.

**6. [O'lchov muhiti] UCH yaroqsiz gate urinishi — hammasi jurnalda**
- (1) fon ijro seansi ~66-daqiqada o'ldirildi (2-urinish backend 57% da uzildi); (2) **1845 s exit 1 — meros flake №12** (`test_phase5_criteria::test_sc4`, o'lchangan ehtimol 1/70) tripladi → o'lchov YAROQSIZ, qaytadan olindi, flake TEGILMADI (08-20 scope-boundary qarori); (3) ikkinchi fon seansi ham o'ldirildi (3-urinish build bosqichida uzildi). Ikkala uzilish vosita muhitining fon-vazifa chegarasi, mahsulot nuqsoni EMAS — qolgan uchtasi ALOHIDA seanslarda to'liq o'tdi.

### SDK bosqichidagi ongli chetlanish

**7. `requirements.mark-complete` chaqirilmadi** — reja frontmatter'ida beshala LAND ID bor; SDK verbi beshalasini `[x]` qilardi va LAND-05 ning `Blocked` holatini buzardi (checkbox ↔ jadval nomuvofiqligi — sync skripti darhol qizarardi). Holatlar qo'lda, dalil jadvali bilan qo'yildi va `check-requirements-sync` exit 0 bilan qulflangan.

**8. [Rule 1 - deferred №14 UCHINCHI takror] SDK faza belgisini yana buzdi — qaytarildi**
- **Found during:** SDK `roadmap update-plan-progress 10` dan keyingi majburiy nazorat (orkestrator ogohlantirgan edi)
- **Issue:** Verb Phase 10 milestone-belgisini `- [x] … (completed 2026-08-17)` qilib qo'ydi — fazani yopish qarori `/gsd-verify-work` niki, ijrochi/SDK niki emas. Bu deferred №14 nuqsonining UCHINCHI chiqishi (9-fazada ham xuddi shunday qaytarilgan).
- **Fix:** Belgi `- [ ]` ga qaytarildi; reja-darajali `- [x] 10-08-PLAN.md` va `Plans: 8/8 plans complete` TEGILMADI (ular to'g'ri).
- **Files modified:** .planning/ROADMAP.md

## Authentication gates

Yo'q — auth talab qilinadigan qadam uchramadi.

## Known Stubs

Yo'q — bu reja UI komponenti yaratmadi; tegilgan fayllarda placeholder/bo'sh-qiymat oqimi yo'q.

## Threat Flags

Yo'q — yangi tarmoq yuzasi, auth yo'li yoki sxema o'zgarishi kiritilmadi. Reja threat-modelidagi to'rtala mitigatsiya bajarildi: T-10-22 (LAND-05 Blocked), T-10-23 (ikki yo'nalishli ko'zgu), T-10-24 (W0-13 jurnal), T-10-25 (UAT #4 da soxta PII bandi LITERAL).

## Keyingi ijrochi uchun

- `gate:fast` byudjeti endi **300 s**, `gate` **2300 s** (zaxira 73 s — TOR, 11-faza birinchi qo'shimchasida qayta o'lchov kutiladi).
- HUMAN-UAT №1/№3/№4/№5/№6 ochiq — raqamlar birinchi deploy / pilot haftasi / go-live'da olinadi; RAQAM UYDIRILMAYDI.
- ROADMAP faza belgisi `- [ ]` — yopish `/gsd-verify-work` niki.

## Self-Check: PASSED

Yaratilgan/o'zgartirilgan to'rtala kalit fayl diskda mavjud
(phase10-criteria.test.mjs, 10-HUMAN-UAT.md, 10-VALIDATION.md, SUMMARY);
uchala task commiti (`7364e21`, `c9e6898`, `adc1261`) git tarixida;
verify buyruqlari: criteria 8/8 · error-codes 44/44 · requirements-sync
exit 0 · validation-signoff exit 0 · gate 3× exit 0 · gate:fast
post-commit 172 s exit 0.
