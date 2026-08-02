---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 22
subsystem: testing
tags: [traceability, requirements, regression, node-test, sabotage, gap-closure, gate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-18 — CR-03 (ustaga yetib borish) yopilishi va `wizard-reachability.test.mjs`; 02-19 — CR-02 (shaxsiy ma'lumot o'qish auditi), `test_personal_data_audit.py` + `test_personal_data_coverage.py`; 02-20 — CR-01 (klient keshining tenant chegarasi) va `tenant-cache.test.tsx`; 02-21 — WR-06 (`open_weekdays`), `0011` migratsiyasi va 18 topilmali REVIEW triaji"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-17 — `tests/integration/test_phase2_criteria.py` (SC#1…SC#5 ning yagona joyi) va `npm run gate` darvozasi"
provides:
  - "`.planning/REQUIREMENTS.md` — MARKET-01…06 ikkala joyda (ro'yxat + Traceability) `Done`; MARKET-07 `Pending` (egasi `02-24`)"
  - "`.planning/REQUIREMENTS.md` §Traceability — «belgilash qoidasi va uning chegarasi» izohi: belgi «talab bajarildi» degani, «faza yopildi» degani EMAS"
  - "`scripts/check-requirements-sync.mjs` — ro'yxat ↔ Traceability jadvalini ikki yo'nalishda solishtiruvchi, tashqi bog'liqliksiz (`node:` moduldan boshqa import yo'q) vosita"
  - "Oltala MARKET bandi uchun nomlangan buyruq + test soni + natija ko'rinishidagi o'lchangan dalil jadvali"
affects: [02-23, 02-24, 03-nvr]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Traceability belgisi DA'VOga emas, nomlangan buyruq + o'lchangan test soniga bog'lanadi; qizarish belgilashni bloklaydi"
    - "Bir faylning ikki joyi (ro'yxat + jadval) mexanik solishtiriladi — hujjat ham sabotaj bilan o'lchanadigan artefakt"
    - "Holat lug'ati ATAYIN uch qiymat bilan chegaralangan (`Done` / `Pending` / `Blocked (...)`) — sinonim ruxsat etilsa mexanik solishtiruv sekin yemirilardi"
    - "Sanoq skriptning O'ZIDA qattiq yozilmaydi, faylning mazmunidan olinadi — aks holda vosita uchinchi eskiradigan haqiqat manbai bo'lardi"
    - "Ma'lum eskirgan son XATO emas, OGOHLANTIRISH sifatida chiqariladi va egasi nomlanadi — shunda u ham jimgina yashamaydi, ham vositani doimiy qizil qilmaydi"

key-files:
  created:
    - scripts/check-requirements-sync.mjs
  modified:
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Oltala MARKET bandi ham belgilandi — 02-VERIFICATION.md ning O'Z ochilish sharti bajarilgan: CR-01/02/03 yopilgan VA real ma'lumot bandini milestone egasi ROADMAP'da ochiq qayta ta'riflagan (2026-08-01)"
  - "MARKET-05 ning holati `Complete` dan `Done` ga normallandi — 02-21 boshqa lug'at ishlatgan va bu ajralishni yangi skript birinchi ishga tushishidayoq topdi"
  - "MARKET-07 `Pending` qoldi — talabi 2026-08-01 da qo'shilgan, egasi `02-24` va u hali ishga tushmagan"
  - "`Coverage` bloki va `Faza kesimida` jadvali TEGILMADI (reja shuni talab qiladi), lekin ularning eskirgani faylda VA skript chiqishida ochiq yozildi — bilib turib noto'g'ri sonni jim qoldirish mumkin emas"
  - "Skript `node --test` darvozasiga ULANMADI — u har commit'da hali yozilmagan fazalarning `Pending` qatorlarini qayta o'qib, yangi ma'lumot bermasdi"

patterns-established:
  - "Pattern: traceability belgisining yonida «bu belgi NIMA emasligini» aytadigan izoh turadi — aks holda keyingi tekshiruv 'talab bajarildi' ni 'faza yopildi' deb o'qiydi"
  - "Pattern: hujjat vositasi ham sabotaj bilan o'lchanadi (uch yo'nalish: checkbox→jadval, jadval→checkbox, mavjudlik)"

requirements-completed: [MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06]

# Metrics
duration: 60min
completed: 2026-08-02
---

# Phase 2 Plan 22: Traceability yozuvi haqiqatga keltirildi

**02-18…02-21 ning yopilish da'volari oltita nomlangan regressiya guruhi (233 test) va to'liq `npm run gate` (585 s, exit 0) bilan qayta o'lchandi; `.planning/REQUIREMENTS.md` ning IKKALA joyida MARKET-01…06 `Done` qilindi, MARKET-07 `02-24` uchun ochiq qoldi, va ikkala joyning mosligi endi uch yo'nalishda sabotaj bilan o'lchangan `scripts/check-requirements-sync.mjs` bilan mexanik qulflandi.**

## Holat

**Reja to'liq bajarildi.** Ikkala task ham yetkazildi. Kutilmagan qizarish **bo'lmadi** — ya'ni «belgilashni bloklash» tarmog'i ishga tushmadi va oltala band ham dalil bilan belgilandi.

## Performance

- **Duration:** ~60 min
- **Started:** 2026-08-02T17:07:00Z
- **Completed:** 2026-08-02T18:07:00Z
- **Tasks:** 2 / 2
- **Files modified:** 2 (1 yangi, 1 tahrir)

---

## 1-task — Tor regressiya

### Qatlam 1 — to'liq darvoza

| O'lchov | Natija |
|---|---|
| `npm run gate` | **exit 0** |
| Davomiyligi | **585 s** (02-VALIDATION.md dagi baza: **403 s** → **+182 s / +45%**) |
| Backend to'plami | **916** test (dot sanog'i: 12×72 + 52) |
| Tenant izolyatsiyasi | **317** test (4×72 + 29) |
| Frontend | **124** test (`node --test` 57 + vitest 67, 10 fayl) |
| i18n pariteti | **424 kalit × 3 til**, drift yo'q |
| `next build` | ✓ 9,4 s da kompilyatsiya, 45/45 statik sahifa |

⚠ **O'sish yashirilmaydi.** To'lqin byudjeti 02-VALIDATION.md da allaqachon buzilgan edi (225 s / ≤180 s) va bu to'rt reja test sonini yana oshirdi (890 → 916 backend, 94 → 124 frontend). Darvozaning **585 s** i baza 403 s dan 45% yuqori. Sababning bir qismi strukturaviy va allaqachon qayd etilgan (har integratsiya testi `two_markets` + `market_domain` seed'ini qayta yozadi — 02-VALIDATION.md, 3-faza), qolgan qismi shu mashinaning yuki: mustaqil o'lchangan `npm run test:tenancy` bu ijroda **152 s** oldi, o'sha to'plam 02-17 da esa 99 s edi. Ya'ni 585 s ni sof «kod sekinlashdi» deb o'qish **noto'g'ri** bo'lardi; to'g'ri xulosa — byudjet hamon buzilgan va uni 3-fazada o'lchash sharti o'zgarmadi.

### Qatlam 2 — MARKET bandlari bo'yicha nomlangan tekshiruvlar

⚠ Bu jadval «hammasi yashil» degan bitta satrning O'RNIGA turadi. Har qatorda **qaysi buyruq**, **nechta test** va **qanday da'vo** yozilgan.

| # | Requirement | Bloklovchi bor edimi | Uni qaysi reja yopdi | Regressiya buyrug'i | Test soni | Natija | Belgilash qarori |
|---|---|---|---|---|---|---|---|
| 1 | **MARKET-01** / SC#1 | **Ha — CR-03** (usta erishib bo'lmas edi) | **02-18** (`6468af4`, `30a6659`, `1cbca80`) | `docker compose --profile test run --rm tests pytest tests/integration/test_wizard_flow.py tests/integration/test_phase2_criteria.py::test_sc1_platform_admin_builds_a_market_without_code` | **29** | ✅ exit 0 (37 s) | **belgilandi** |
| 1a | MARKET-01 (yetib borish darvozasi) | — | 02-18 | `node --test frontend/scripts/wizard-reachability.test.mjs` | **3** | ✅ exit 0 (uchala to'siq alohida) | ↑ |
| 1b | MARKET-01 (qobiq va marshrut) | — | 02-18 | `npm --prefix frontend run test:component -- layout.test app-shell.test` | **9** (5+4) | ✅ exit 0 | ↑ |
| 2 | **MARKET-02** / SC#2 | **Yo'q** | — (02-19 audit qatlamini, 02-20 klient chegarasini kuchaytirdi) | `pytest tests/integration/test_stall_registry.py tests/integration/test_stall_code_reuse.py tests/integration/test_phase2_criteria.py::test_sc2_registry_changes_are_audited` | **26** | ✅ exit 0 (31 s) | **belgilandi** |
| 3 | **MARKET-03** / SC#3 | **Yo'q** | — | `pytest tests/integration/test_tariff_history.py tests/integration/test_tariffs_api.py tests/integration/test_phase2_criteria.py::test_sc3_past_charges_keep_the_old_price` | **27** | ✅ exit 0 (31 s) | **belgilandi** |
| 4 | **MARKET-04** | **Ha — CR-02** (+ CR-01 ning shaxsiy-ma'lumot yarmi) | **02-19** (`3b9d5f9`, `b1c2286`, `4c72da2`) + **02-20** (`025634b`, `940c505`, `51ca6f3`) | `pytest tests/integration/test_stall_assignments.py tests/integration/test_vendors_api.py tests/integration/test_assignments_api.py tests/integration/test_personal_data_audit.py tests/tenancy/test_personal_data_coverage.py` | **54** | ✅ exit 0 (42 s) | **belgilandi** |
| 5 | **MARKET-05** / SC#4 | **Ha — WR-06** (`calendar_missing` hech qachon yonmasdi) | **02-21** (`1b74a8c`, `cac9b4d`) | `pytest tests/integration/test_market_calendar.py tests/integration/test_calendar_api.py tests/integration/test_phase2_criteria.py::test_sc4_closed_day_has_no_charge_basis` | **23** | ✅ exit 0 (27 s) | **belgilandi** (holati normallandi) |
| 5a | MARKET-05 (`calendar_missing` usta yo'lida) | — | 02-21 | `pytest tests/integration/test_wizard_flow.py -k "weekday or calendar"` | **5** | ✅ exit 0 (20 s) | ↑ |
| 6 | **MARKET-06** / SC#5 | **Yo'q** | — | `pytest tests/integration/test_phase2_criteria.py` (`test_sc5_map_groups_stalls_by_zone_in_code_order` shu yerda) | **5** (fayl bo'yicha) | ✅ exit 0 (19 s) | **belgilandi** |
| 6a | MARKET-06 (xarita komponenti) | — | 02-14 | `npm --prefix frontend run test:component -- stall-map.test` | **8** | ✅ exit 0 | ↑ |
| — | **Tenant chegarasi** (CLAUDE.md cheklovi) | **Ha — CR-01** | **02-20** | `npm run test:tenancy` | **317** | ✅ exit 0 (152 s) | belgi bandi emas |
| — | Tenant chegarasi (klient yarmi) | — | 02-20 | `npm --prefix frontend run test:component -- tenant-cache.test` | **6** | ✅ exit 0 | belgi bandi emas |
| — | **MARKET-07** | — | **hech kim (hali)** | — (talabi `02-24` da quriladi) | 0 | — | **belgilanmadi** |

**Jami nomlangan qatorlar bo'yicha o'lchangan:** 233 test (SC-testlari 6-qatordagi fayl yurishida bir marta qayta hisoblangan) + 317 tenancy = **550 test ijrosi**, birortasi qizarmadi.

### Kutilmagan qizarish

**Bo'lmadi.** Yuqoridagi 12 buyruqning hammasi exit 0 berdi, shuning uchun birorta band «qizarish tufayli belgilanmadi» holatiga tushmadi. Yagona belgilanmagan band — MARKET-07 — qizarish sababli emas, **hali qurilmagani** uchun ochiq qoldi.

---

## 2-task — `.planning/REQUIREMENTS.md`

### Belgilangan bandlar va ularning asosi

| Band | Asos |
|---|---|
| **MARKET-01** | CR-03 ni 02-18 yopdi — marshrut istisnosi, `market_manage` bilan himoyalangan menyu yozuvi va bo'sh ro'yxatdagi havola; uchalasi manba darvozasi bilan qulflangan (3 test), SC#1 uchidan-uchiga yashil |
| **MARKET-02** | Bloklovchi yo'q edi; SC#2 sabotaj bilan o'lchangan (02-17), reestr + kod qayta ishlatilmasligi 26 test bilan yashil |
| **MARKET-03** | Bloklovchi yo'q edi; SC#3 sabotaj bilan o'lchangan, tarif tarixi 27 test bilan yashil |
| **MARKET-04** | CR-02 ni 02-19 yopdi (`audit_read` + `VENDOR_VIEW`, `TABLE_STALLS` konstantasi 17 rejadan keyin birinchi marta ishlatildi); CR-01 ning shaxsiy-ma'lumot yarmini 02-20 yopdi; 54 test yashil |
| **MARKET-05** | WR-06 ni 02-21 yopdi (`0011` migratsiyasi ikkala standart yo'lini oldi, usta 1-qadami rejimni so'raydi); `calendar_missing` endi mahsulot yo'lida yonadi |
| **MARKET-06** | Bloklovchi yo'q edi; SC#5 ikki marta sabotaj bilan o'lchangan, `stall-map.test.tsx` 8 test |

### Belgilanmagan band va uning sababi

| Band | Sabab (bir jumla) |
|---|---|
| **MARKET-07** | Talab 2026-08-01 da qo'shilgan va uni quradigan `02-24` rejasi hali ishga tushmagan — ya'ni ortida birorta kod ham, test ham yo'q. |

⚠ «Keyinroq» degan bo'sh ibora ishlatilmadi: bandning egasi (`02-24`), qurilishi kutilayotgan narsa (xodimlar ro'yxatining ommaviy importi) va uning darvozasi (o'sha rejaning 3-taski) nomma-nom ma'lum.

### 02-VERIFICATION.md ning hukmi va uning ochilish sharti

Tekshiruv oltala bandni `Pending` qoldirishni tavsiya qilgan va ochilish shartini AYNAN yozgan:

> «leave all six `Pending` until a closure plan resolves CR-01/02/03 **and** real Karmana data is loaded (**or the milestone owner explicitly overrides the real-data clause**); re-verify MARKET-02/03/05/06 with a light regression pass at that point»

Ikkala shart ham bugun bajarilgan:

1. **CR-01/CR-02/CR-03 yopilgan** — 02-20 / 02-19 / 02-18, har biri sabotaj bilan o'lchangan va yuqoridagi jadvalda qayta yugurtirilgan.
2. **Real ma'lumot bandini milestone egasi ochiq qayta ta'riflagan** — `ROADMAP.md` §"Phase 2" ga 2026-08-01 da «Real ma'lumot haqida (qayta ta'riflandi)» xatboshisi qo'shilgan: *«fazaning yetkazib berish mahsuloti — import qobiliyati, ma'lum bir fayl emas … Real Karmana ma'lumoti kelganda admin uni saytning o'zidan yuklaydi — bu operatsion amal, faza darvozasi emas»*. Bu tekshiruv nazarda tutgan «explicit override» ning o'zi va u REJADAN KEYIN, ya'ni bu ijroda birinchi marta hisobga olindi (pastda, deviatsiya #2).

Ya'ni belgilash tekshiruvning hukmini **buzmaydi** — uning o'z shartini bajaradi.

### Traceability izohi (T-02-162 mitigatsiyasi)

Jadval ostiga «Belgilash qoidasi va uning chegarasi» xatboshisi qo'shildi. U uchta chalkashish nuqtasini nomma-nom ajratadi:

1. **Real ma'lumot sharti** — birorta MARKET bandining matnida YO'Q; `02-VALIDATION.md` da (`nyquist_compliant`, `02-23`) yuritiladi.
2. **MARKET-01 ning kamera / kamera-zonasi / kadr jadvali qadamlari** — `ROADMAP.md` **Note** bandi bo'yicha keyingi fazalarda ulanadi; 2-faza rekvizit → zona → rasta → toifa → tarif zanjirini yetkazadi va o'lchanadigan narsa aynan shu.
3. **Odam ishtirokidagi tasdiqlar** — `02-VALIDATION.md` ning «Manual-Only Verifications» jadvalida, bu yerda emas.

⚠ 2-band rejada talab qilinmagan va u ATAYIN qo'shildi: MARKET-01 ning MATNI sakkizta qadamni sanaydi, 2-faza esa beshtasini yetkazadi. Buni jim qoldirish keyingi tekshiruvni «belgi asossiz» degan xulosaga olib borardi; izoh farqni ko'rinadigan qiladi va uning **qayerda hal qilinishini** aytadi.

### `scripts/check-requirements-sync.mjs`

Tashqi bog'liqliksiz vosita (`node:fs`, `node:path`, `node:process` — boshqa import yo'q). Butun faylni o'qiydi va **ikki yo'nalishda** solishtiradi: (a) ro'yxatdagi har ID jadvalda bor va teskarisi; (b) `[x]` ↔ `Done`, `[ ]` ↔ `Pending` yoki `Blocked (...)`. Mos kelmasa AYNAN qaysi ID, ro'yxatda nima, jadvalda nima — ikkala qator raqami bilan.

**Toza ishga tushish natijasi:**

```
check-requirements-sync: 49 ta talab tekshirildi — ro'yxat va Traceability jadvali MOS.
  Done: 6 · Pending: 43 · Blocked: 0
  ⚠ OGOHLANTIRISH: "**Coverage:**" bloki 46 deydi (217-qator), mazmunidan
    hisoblanganda 49 chiqdi. Bu XATO deb sanalmadi — sanoqlarni qayta
    hisoblash 02-24 rejasining zimmasida.
```

Skript `node --test` darvozasiga **ulanmadi** va sabab uning boshidagi izohda: u har commit'da hali yozilmagan fazalarning `Pending` qatorlarini qayta o'qib, hech qanday yangi ma'lumot bermasdi.

### SABOTAJ o'lchovlari (3 ta — reja bittasini talab qiladi)

Har biri kiritildi, o'lchandi va darhol qaytarildi; qaytarilgandan keyin skript qayta exit 0 berdi.

| # | Sabotaj | Kutilgan | O'lchangan natija |
|---|---|---|---|
| 1 | `MARKET-03` checkbox'i `[x]` → `[ ]`, jadvaldagi holat `Done` qoldirildi | exit 1 va xato xabarida AYNAN `MARKET-03` | **exit 1**, `✗ MARKET-03: jadvalda "Done" (147-qator), ro'yxatda esa BELGILANMAGAN ([ ], 24-qator)` — **1 ta** topilma, qolgan 48 talab toza |
| 2 | Teskari yo'nalish: `MARKET-06` jadval holati `Done` → `Pending`, checkbox `[x]` qoldirildi | exit 1 va AYNAN `MARKET-06` | **exit 1**, `✗ MARKET-06: ro'yxatda BELGILANGAN ([x], 27-qator), jadvalda esa "Pending" (150-qator)` — **1 ta** topilma |
| 3 | Mavjudlik yo'nalishi: `\| MARKET-07 \| Phase 2 \| Pending \|` qatori jadvaldan butunlay o'chirildi | exit 1 va AYNAN `MARKET-07` | **exit 1**, `✗ MARKET-07: ro'yxatda bor (28-qator), Traceability jadvalida YO'Q` — **1 ta** topilma |

**Uchala o'lchovning birgalikdagi qiymati:** ular skriptning uchta MUSTAQIL da'vosi borligini ko'rsatadi. Bitta yo'nalishli tekshiruv 2- va 3-sabotajlarni jimgina o'tkazib yuborardi — aynan shu sinf nuqson (`REQUIREMENTS.md` ning ikki joyi ajralib ketishi) T-02-161 ning o'zi.

**Sabotajdan tashqari, skript birinchi ishga tushishidayoq HAQIQIY nomuvofiqlikni topdi** — MARKET-05 ning jadvaldagi holati `Complete` edi (02-21 ning lug'ati), ro'yxatda esa `[x]`. Pastda, deviatsiya #1.

### Mexanik qabul mezonlari (o'lchangan)

| Mezon | Natija |
|---|---|
| `node scripts/check-requirements-sync.mjs` | ✅ **exit 0** |
| `grep -c "\| MARKET-0. \| Phase 2 \| Pending \|"` = belgilanmagan bandlar soni | ✅ **1** (= MARKET-07) |
| Boshqa fazalar tegilmagan (`git diff --unified=0 … \| grep -c` boshqa prefikslar) | ✅ **0** |
| `grep -n "02-VALIDATION.md" .planning/REQUIREMENTS.md` | ✅ 2 natija (200- va 208-qatorlar) |
| `Coverage` bloki o'zgarmagan (`grep -c "^[+-].*v1 requirements: 46"`) | ✅ **0** |
| Skriptdagi har import `node:` prefiksli | ✅ 3/3 (`node:fs`, `node:path`, `node:process`), `require(` yo'q |
| `git diff --stat .planning/REQUIREMENTS.md` | ✅ 1 fayl, +50 / −12 (MARKET qatorlari + izoh + oxirgi yangilanish satri) |

## Task Commits

1. **Task 1: Tor regressiya** — commit **yo'q** (fayl o'zgarishi yaratmaydigan o'lchov taski; dalili shu SUMMARY'da, pastdagi deviatsiya #3)
2. **Task 2: REQUIREMENTS.md belgilash + sync darvozasi** — `a425ece` (docs)

## Files Created/Modified

**Yangi**

- `scripts/check-requirements-sync.mjs` — ro'yxat ↔ Traceability jadvalini ikki yo'nalishda solishtiruvchi vosita; sanoqni faylning mazmunidan oladi; eskirgan `Coverage` blokini ogohlantirish bilan ko'rsatadi

**Tahrir**

- `.planning/REQUIREMENTS.md` — MARKET-01/02/03/04/06 checkbox'lari `[x]`; Traceability jadvalida MARKET-01…06 `Done` (MARKET-05 `Complete` → `Done` normallandi); «Belgilash qoidasi va uning chegarasi» izohi; `Coverage` bloklarining eskirgani haqidagi ogohlantirish; `*Last updated:*` satri

## Decisions Made

- **Oltala band ham belgilandi, subset emas.** 02-VERIFICATION.md subset belgilashni «halol yozuvni parchalab yuborardi» deb rad etgan edi — bu ijroda subset holati umuman tug'ilmadi, chunki ikkala bloklovchi ham yopilgan va oltala regressiya guruhi ham yashil chiqdi.
- **MARKET-01 belgilandi, garchi foydalanuvchanlik kuzatuvi (`02-VALIDATION.md` Manual-Only #2) ochiq bo'lsa ham.** Sabab: 02-VERIFICATION.md ning «Requirements Coverage» jadvali MARKET-01 ga qarshi AYNAN bitta bloklovchi (CR-03) yozgan, Manual-Only bandlarini esa «worth carrying into a closure plan **without blocking the verdict**» deb ajratgan. Belgi shu bilan «talab bajarildi» deydi; odam tasdig'i esa `02-VALIDATION.md` da qoladi va Traceability izohining 3-bandi buni AYNAN shu so'zlar bilan aytadi. Bu qaror **hukm**, mexanik natija emas — shuning uchun asosi shu yerda ochiq yozildi.
- **Holat lug'ati uch qiymat bilan chegaralandi.** Sinonimlarga (`Complete`, `Ready`) ruxsat berish skriptning butun maqsadini sekin yemirardi: solishtiruv «taxminan mos» ga aylanardi.
- **Sanoq skriptda qattiq yozilmadi.** Aks holda vosita eskiradigan uchinchi haqiqat manbai bo'lardi — aynan u to'xtatishi kerak bo'lgan nuqsonning o'zi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MARKET-05 ning holati boshqa lug'atda yozilgan edi (`Complete`, `Done` emas)**

- **Found during:** Task 2 (skriptning birinchi ishga tushishi, hali belgilash boshlanmasdan)
- **Issue:** `02-21` MARKET-05 ni belgilaganda ro'yxatga `[x]` qo'ygan, Traceability jadvaliga esa `Complete` yozgan. Reja `[x]` ↔ `Done` juftligini talab qiladi va uning task ro'yxati MARKET-05 ni hamon `[ ]` deb hisoblagan. Ya'ni fayl ikki xil lug'atda gapirayotgan edi va buni birorta vosita ushlamasdi.
- **Fix:** Jadval qatori `Complete` → `Done` ga normallandi (ro'yxatdagi `[x]` tegilmadi — u to'g'ri edi va uning asosi 02-21 da o'lchangan). Skript noma'lum holatni XATO deb sanaydi va sababi uning docstringida yozilgan.
- **Files modified:** `.planning/REQUIREMENTS.md`, `scripts/check-requirements-sync.mjs`
- **Verification:** Normallashdan oldin: `✗ MARKET-05: jadvaldagi holat "Complete" tanilmadi (149-qator)`, exit 1. Keyin: exit 0. MARKET-05 ning belgisi mustaqil ham asoslandi — 23 + 5 test yashil (yuqoridagi 5- va 5a-qatorlar).
- **Committed in:** `a425ece`

**2. [Rule 2 - Missing Critical] Reja ROADMAP maqsad jumlasining ESKI, ikki qismli variantiga tayanadi**

- **Found during:** Task 1 (`ROADMAP.md` §"Phase 2" ni o'qish paytida)
- **Issue:** Reja `<decisions_context>` da «ROADMAP Phase 2 maqsad jumlasi ikki qismli va uning ikkinchi yarmi (Karmananing real ma'lumoti) …» deydi. Amalda maqsad jumlasi 2026-08-01 da QAYTA YOZILGAN va u endi bir qismli; real ma'lumot sharti esa alohida «Real ma'lumot haqida (qayta ta'riflandi)» izohiga ko'chirilib, ochiq ravishda faza darvozasi EMAS deb e'lon qilingan. Rejaning matnini so'zma-so'z bajarish Traceability izohiga mavjud bo'lmagan jumlaga havola yozardi va — muhimrog'i — 02-VERIFICATION.md ning ochilish shartidagi «or the milestone owner explicitly overrides the real-data clause» tarmog'i **bajarilganini ko'rmay qolardi**.
- **Fix:** Izoh ikkala manbaga ham bog'landi: qayta ta'riflash `ROADMAP.md` da, kundalik holat esa `02-VALIDATION.md` da yuritilishi yozildi. Belgilash qarorining asosi (override bajarilgan) shu SUMMARY'da alohida bo'limda ochiq keltirildi.
- **Files modified:** `.planning/REQUIREMENTS.md`
- **Verification:** `grep -n "02-VALIDATION.md" .planning/REQUIREMENTS.md` → 2 natija; izoh `ROADMAP.md` ning aynan mavjud sarlavhasiga havola qiladi
- **Committed in:** `a425ece`

**3. [Rule 3 - Blocking] Reja MARKET bandlari sonini oltita deb hisoblaydi — amalda yettita**

- **Found during:** Task 1 (init konteksti `phase_req_ids` ni yettita ID bilan qaytardi)
- **Issue:** Rejaning `requirements:` frontmatteri va butun task matni oltita MARKET bandini nazarda tutadi. 2026-08-01 da MARKET-07 (va boshqa ikki band) qo'shilgan, ya'ni oltita songa tayanadigan har qanday assert noto'g'ri bo'lardi. Fayl ichidagi `**Coverage:** 46 total` va `Faza kesimida` jadvali ham xuddi shu sababdan eskirgan (haqiqiy son — 49; Phase 2 uchun 7).
- **Fix:** (a) skript hech qanday sonni qattiq yozmaydi — `49` ni faylning O'Z mazmunidan hisoblaydi; (b) `Coverage` bloki reja talab qilganidek TEGILMADI, lekin uning eskirgani faylda ⚠ izoh bilan va skript chiqishida OGOHLANTIRISH bilan ko'rsatildi, egasi (`02-24`) nomlandi; (c) MARKET-07 `Pending` qoldirildi.
- **Files modified:** `.planning/REQUIREMENTS.md`, `scripts/check-requirements-sync.mjs`
- **Verification:** `node scripts/check-requirements-sync.mjs` → `49 ta talab`, `Done: 6 · Pending: 43`, exit 0 + ogohlantirish; `git diff … grep -c "v1 requirements: 46"` = 0
- **Committed in:** `a425ece`

**4. [Rule 3 - Blocking] Rejaning `-q` bayrog'i pytest xulosa satrini o'chirib qo'yadi**

- **Found during:** Task 1 (birinchi regressiya guruhi)
- **Issue:** Reja buyruqlari `pytest … -q` deb yozilgan, `pyproject.toml::addopts` da esa `-q` ALLAQACHON bor. Ikkinchi `-q` pytest uchun `-qq` degani va u yakuniy `N passed` satrini butunlay o'chiradi — ya'ni rejaning O'Z qabul mezoni («aynan 5 test o'tadi») bajarilganini o'lchab bo'lmasdi.
- **Fix:** Ortiqcha `-q` olib tashlandi (xulq bir xil, faqat xulosa satri qaytadi). Nuqta sanog'i bilan mustaqil tekshirildi: 12×72+52 = **916** backend, 4×72+29 = **317** tenancy — ikkalasi ham 02-21 ning raqamlari bilan mos.
- **Files modified:** yo'q (buyruq darajasidagi tuzatish)
- **Verification:** `pytest tests/integration/test_phase2_criteria.py` → `5 passed in 14.04s`, exit 0
- **Committed in:** — (fayl o'zgarishi yo'q)

**5. [Rule 3 - Blocking] 1-task fayl o'zgarishi yaratmaydi — atomik commit qilinadigan narsa yo'q**

- **Found during:** Task 1 oxiri
- **Issue:** Reja 1-taskning `<files>` iga `.planning/REQUIREMENTS.md` ni yozadi, lekin uning `<action>` i faqat O'LCHOV — fayl tahriri 2-taskda. Bo'sh commit yaratish tarixni yolg'on qilardi («1-task fayl o'zgartirdi» degan taassurot).
- **Fix:** 1-task commit qilinmadi; uning butun natijasi shu SUMMARY'ning dalil jadvali sifatida yozildi va SUMMARY commit'i bilan tarixga tushdi. O'lchangan raqamlar yo'qolmasligi uchun ular ijro davomida bosqichma-bosqich saqlab borildi.
- **Files modified:** yo'q
- **Verification:** `git log` da 02-22 uchun bitta task commit'i (`a425ece`) va bitta metadata commit'i bor — bo'sh commit yo'q
- **Committed in:** —

---

**Total deviations:** 5 auto-fixed (1 bug, 1 missing-critical, 3 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Qamrov kengaymadi — birorta kod fayli, test, migratsiya yoki paket qo'shilmadi. #1 mavjud faylning ichki ziddiyatini yopdi; #2 va #3 rejaning eskirgan premissalarini (maqsad jumlasi, bandlar soni) haqiqatga keltirdi va ikkalasi ham belgilash qarorining asosiga bevosita ta'sir qildi; #4 va #5 rejaning o'z mezonlarini o'lchanadigan holga keltirdi.

## Issues Encountered

- **`-qq` tuzog'i (deviatsiya #4)** birinchi ikki yugurtishda «test soni o'lchanmadi» holatini berdi. Yechim buyruq darajasida; test xulqiga ta'siri yo'q.
- **Darvoza davomiyligining o'sishi qisman mashina yukidan.** Mustaqil o'lchangan `npm run test:tenancy` bu ijroda 152 s oldi (02-17 da 99 s), ya'ni 585 s ni sof kod sekinlashuvi deb o'qish noto'g'ri bo'lardi. Byudjet buzilgani esa o'zgarmadi va u 3-fazaga o'tkazilgan holicha qoladi.
- **Repo ildizida uchta kuzatilmagan fayl bor** (`*.docx` va `SBOZOR-MVP-texnik-topshiriq.md`) — ular bu ijro boshlanishidan OLDIN ham turgan, foydalanuvchining fayllari va bu rejaning qamrovidan tashqarida. Tegilmadi.

## Known Stubs

Yo'q. Bu reja kod yozmaydi; yagona ijro etiladigan artefakt (`check-requirements-sync.mjs`) haqiqiy faylni o'qiydi, qattiq yozilgan qiymat qaytarmaydi va uning ikkala tarmog'i ham (mos / mos emas) sabotaj bilan o'lchandi.

## Threat Flags

Yo'q — yangi tarmoq endpointi, auth yo'li, fayl kirish naqshi yoki ishonch chegarasidagi sxema o'zgarishi kiritilmadi.

| Threat ID | Holat |
|-----------|-------|
| T-02-160 | mitigate — har belgi nomlangan buyruq + test soniga bog'landi (yuqoridagi 13 qatorli jadval); qizarish tarmog'i qurildi, lekin ishga tushmadi |
| T-02-161 | mitigate — `check-requirements-sync.mjs` ikki yo'nalishda solishtiradi; **uch sabotaj bilan o'lchandi**, har birida AYNAN bitta ID topildi |
| T-02-162 | mitigate — Traceability izohi «talab bajarildi» ni «faza yopildi» dan ajratadi; izohning mavjudligi `grep -n "02-VALIDATION.md"` bilan tekshirildi |
| T-02-SC | n/a — yangi paket o'rnatilmadi; skript faqat `node:` modullarini ishlatadi (3/3 tekshirildi) |

## User Setup Required

Yo'q — tashqi servis sozlamasi, migratsiya yoki deploy qadami talab qilinmaydi.

## Next Phase Readiness

- **`02-24` uchun tayyor:** `scripts/check-requirements-sync.mjs` mavjud va uning 3-taski aynan shu vositani chaqirishni rejalashtirgan; MARKET-07 ning ikkala joyi ham `[ ]` / `Pending` holatda va bir-biriga mos, ya'ni belgilash bitta juft tahrir bo'ladi. **Sanoq bloklarini qayta hisoblash ham o'sha rejaning zimmasida** va u endi faylning o'zida ⚠ bilan yozilgan (haqiqiy sonlar: jami **49**, Phase 2 uchun **7**, Phase 3 uchun **5**).
- **`02-23` uchun tayyor:** REQUIREMENTS.md endi real ma'lumot shartini VA odam ishtirokidagi tasdiqlarni `02-VALIDATION.md` ga nomma-nom yo'naltiradi — ya'ni o'sha reja `nyquist_compliant` bayrog'ini qaytarganda ikkala fayl bir-biriga zid gapirmaydi.
- **Darvoza holati:** `npm run gate` **yashil** (exit 0, 585 s) — bu reja regressiya qilmadi va qila olmasdi (birorta kod fayliga tegmadi).
- **Ochiq qarz (bu rejaniki emas, ko'rinadigan bo'lsin uchun):** to'lqin darajasidagi kechikish byudjeti hamon buzilgan; `GET /api/v1/users` hamon o'qish auditisiz (02-19 flagi); `02-VALIDATION.md` ning to'rtala Manual-Only bandi hamon ochiq (`02-23`).

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-02*
