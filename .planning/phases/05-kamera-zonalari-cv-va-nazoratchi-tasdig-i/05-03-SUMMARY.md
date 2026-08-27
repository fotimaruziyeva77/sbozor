---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 03
subsystem: ui
tags: [typescript, vitest, node-test, geometry, svg, statistics, wilson, gate, blind-audit]

requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`camera-page-state.ts` + `.test.tsx` juftligi (sof mantiqni marshrut faylidan ajratish sababi, 03-09 sabotaji S3 bilan o'lchangan); `vitest.config.ts` ning `include` naqshi va M-2 tuzog'i; `scripts/*.test.mjs` darvozalarining shakli (`wizard-reachability`, `role-gate`, `vendor-integrity`)"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`stall-map.tsx` — canvas kutubxonasining O'LCHOV bilan rad etilishi (D-05 ning dalili); «klientdagi chegara qulaylik, ishonch manbai server» qoidasi"
provides:
  - "`lib/zone-geometry.ts` — 11 sof funksiya (0..1 koordinata), DOM'siz, React'siz; render qatlami almashtiriladi, geometriya emas"
  - "`MIN_VERTICES` / `MAX_VERTICES_PER_ZONE` / `MAX_ZONES_PER_CAMERA` / `UNDO_DEPTH` — serverdagi juftiga havola bilan"
  - "G-19 darvozasi (`zone-geometry.test.tsx`, 45 test) — `isSelfIntersecting` ning ijobiy VA salbiy nazorati, aylanma yo'qotishsizlik butun piksel domenida sanab chiqilgan"
  - "`lib/wilson.ts` — `wilsonInterval` va `MIN_SAMPLE_FOR_PERCENT`; bog'liqliksiz, yangi paketsiz"
  - "G-12 va G-14(a,b,c) darvozasi (`scripts/blind-payload.test.mjs`) — ko'r payloadning STATIK modul chegarasi, ekranlar yozilishidan OLDIN"
  - "Izohni holat mashinasi bilan olib tashlash + uning ijobiy/salbiy nazorat jadvali va «yutib yuborish» qo'riqchisi"
affects: [05-06, 05-09, 05-12, 05-13, 05-14]

tech-stack:
  added: []
  patterns:
    - "Frontend sof mantiq: modul `src/lib/*.ts`, test `src/lib/*.test.tsx` (§S-13 A yo'li) — `.ts` test fayli vitest tomonidan JIMGINA o'tkazib yuboriladi"
    - "Rad etilgan formulaning NOMI skanerlanadigan faylga emas, uning TEST faylining docstringiga yoziladi (03-07 qoidasi)"
    - "Bajarilgan amal -> yangi massiv; RAD ETILGAN amal -> aynan o'sha havola; chaqiruvchi farqni `Object.is` bilan bir bosqichda ajratadi"
    - "Chekli domenli aylanma/chegara testi TANLAB OLINMAYDI, SANAB CHIQILADI — «omadli fixture» yo'lini yopadi"
    - "Fixture haqiqiyligi alohida assert bilan tekshiriladi: rad etilgan arifmetika HAQIQATAN yo'qotishini o'lchaydi, aks holda test o'z farazini tasdiqlaydi"
    - "Statik matn darvozasi izohlarni satr-filtri bilan emas, satr-literallarni biladigan holat mashinasi bilan tozalaydi; `export` ning omon qolishi runaway nazorati"
    - "Hali mavjud bo'lmagan yo'l `skip` bilan emas, OCHIQ `assert.equal(exists, false)` bilan qayd etiladi — chegara o'zi qurollanadi"

key-files:
  created:
    - frontend/src/lib/zone-geometry.ts
    - frontend/src/lib/zone-geometry.test.tsx
    - frontend/src/lib/wilson.ts
    - frontend/src/lib/wilson.test.tsx
    - frontend/scripts/blind-payload.test.mjs
  modified: []

key-decisions:
  - "§S-13 ning A yo'li: geometriya `src/lib/zone-geometry.ts`, testi `.test.tsx` — UI-SPEC §6.2 va RESEARCH taklif qilgan `scripts/zone-geometry.test.mjs` BAJARILMAYDI (`node --test` TS import qila olmaydi)"
  - "`denormalize` butun pikselga yaxlitlaydi — aylanma yo'qotishsizlikning SHARTI; yaxlitlashsiz poligon har ochilib-saqlanganda siljib, rastadan sirg'alib chiqardi"
  - "`translate` TEPANI emas, SILJISH MIQDORINI qisadi — per-vertex clamp poligonni jimgina ezib, zona boshqa shaklni o'lchardi"
  - "`addVertex`/`insertMidpoint` `MAX_VERTICES_PER_ZONE` da rad etadi (T-05-12 ning klient tomondagi izi), `deleteVertex` ning `MIN_VERTICES` naqshiga simmetrik"
  - "`wilsonInterval().point` — KUZATILGAN ulush (`s/n`), oraliqning markazi EMAS; markaz qisqartirilgan baho va uni ekranga chiqarish direktorga boshqa raqam ko'rsatardi"
  - "`n === 0` tekshiruvi `successes > n` dan OLDIN: bo'sh namuna birinchi kunning normal holati, chaqiruvchi xatosi emas"
  - "G-12 satr literallarini SAQLAYDI — tarjima kaliti yoki kesh kalitidagi taqiqlangan nom ham brauzerga yetib boradi"
  - "Darvozaning MEXANIZMI (reyestr uzunligi, izoh filtri, runaway nazorati) bugun o'lchanadi, chunki skanerlanadigan to'plam hali bo'sh"

patterns-established:
  - "Sabotaj natijasi IKKI TOMONLAMA qayd etiladi: nima qizardi VA nima yashil qoldi — yashil qolgani o'lchanmagan talabni fosh qiladi"
  - "Darvoza fayli o'z izohlarida taqiqlangan nomlarni erkin ishlatadi, chunki u skanerlanadigan to'plamda YO'Q"

requirements-completed: [AI-01, AI-04]

duration: 100min
completed: 2026-08-08
---

# Phase 5 Plan 03: Geometriya, Wilson va ko'r payload chegarasi Summary

**Poligon geometriyasi render qatlamidan mustaqil 11 sof funksiyaga ajratildi va G-19 bilan qulflandi; nisbat oralig'i Wilson bilan hisoblanadigan bo'ldi; ko'r auditning modul chegarasi (G-12/G-14) ekranlar yozilishidan OLDIN mexanik darvozaga aylandi.**

## Performance

- **Duration:** ~100 daqiqa
- **Started:** 2026-08-08T16:40:00Z
- **Completed:** 2026-08-08T18:20:00Z
- **Tasks:** 3/3
- **Files created:** 5

## Accomplishments

- **W0-8 bajarildi.** Geometriya `src/lib/zone-geometry.ts` da — nol bog'liqlik, DOM yo'q. D-05 ning chiqish yo'li ochiq qoldi: Konva'ga o'tish faqat `zone-canvas.tsx` ni o'zgartiradi.
- **M-2 tuzog'i takrorlanmadi.** Test `.test.tsx` va u `vitest run` chiqishida nomma-nom ko'rinadi (yuqorida o'lchandi). `.ts` bo'lganda jimgina o'tkazib yuborilardi.
- **W0-F3 bajarildi.** `wilsonInterval` chetki `p` va kichik `n` da ham [0,1] ichida qoladigan, KENGLIKKA EGA oraliq beradi. Yangi npm paketi qo'shilmadi.
- **W0-F4 bajarildi.** G-12/G-14 darvozasi ekranlardan oldin turibdi — birinchi ijro taqiqlangan maydonni kiritsa, u darhol qizaradi.
- **Uchta darvoza ham sabotaj bilan IKKI YO'NALISHDA o'lchandi** (pastda jadval), va bittasi haqiqiy bo'shliqni fosh qildi.

## Task Commits

1. **Task 1: `lib/zone-geometry.ts` (TDD)** — `544ee27` (test, RED) → `7cddad6` (feat, GREEN) → `83969a6` (test, o'lchangan bo'shliq yopildi)
2. **Task 2: `lib/wilson.ts` (TDD)** — `ae9c32d` (test, RED) → `cd93ad7` (feat, GREEN)
3. **Task 3: `scripts/blind-payload.test.mjs`** — `92a8413` (feat)

## Files Created

- `frontend/src/lib/zone-geometry.ts` — 11 sof funksiya + 4 chegara konstantasi; fayl boshida uchta qaror (D-05 chiqish yo'li va uning o'lchov tetigi, M-3, saqlash darvozasi)
- `frontend/src/lib/zone-geometry.test.tsx` — G-19, 45 test
- `frontend/src/lib/wilson.ts` — `wilsonInterval`, `MIN_SAMPLE_FOR_PERCENT`; izoh faqat IJOBIY shaklda
- `frontend/src/lib/wilson.test.tsx` — 11 test; rad etilgan muqobil va uning sababi shu yerda
- `frontend/scripts/blind-payload.test.mjs` — G-12 + G-14(a,b,c) + qamrov chegarasi, 8 test

## Sabotaj o'lchovi — nima qizardi va NIMA YASHIL QOLDI

| # | Sabotaj | Natija |
|---|---------|--------|
| S1 | `isSelfIntersecting` doim `false` | 🔴 2 test (ijobiy nazoratlar) |
| S2 | `denormalize` dan yaxlitlash olib tashlandi | 🟢 **YASHIL QOLDI** → tuzatildi, keyin 🔴 2 test |
| S3 | `translate` har TEPANI qisadi (siljish o'rniga) | 🔴 1 test (shakl saqlanishi) |
| S4 | Wilson o'rniga rad etilgan normal-approximation | 🔴 **11 tadan 7 tasi** |
| A | `const verdict = 1;` (`blind-audit-queries.ts`) | 🔴 G-12 |
| B | O'sha satr `// verdict` izohi sifatida | 🟢 G-12 yashil (izoh filtri to'g'ri ishladi) |
| E | `invalidateQueries` | 🔴 G-14(b) |
| F | `review/blind/[itemId]/` | 🔴 G-14(a) |
| G | `components/blind-audit/` da atigi 2 fayl | 🔴 qamrov chegarasi |
| H | `aiConfidence` ICHMA-ICH komponent faylida | 🔴 G-12 (fayl nomi bilan) |

⚠ **S2 bu rejaning eng qimmatli natijasi.** Aylanma testi dastlab beshta qo'lda tanlangan pikselni tekshirardi va `denormalize` dan yaxlitlashni butunlay olib tashlash **hech nimani qizartirmadi** — o'sha beshta qiymat IEEE754 da tasodifan aniq aylanadi. O'lchov: 1279 kenglikda 1280 ta butun pikseldan **183 tasi** qo'pol arifmetikada yo'qotadi, lekin tanlangan 437 ular orasida emas edi. Ya'ni test o'z farazini tasdiqlab, himoya qilishi kerak bo'lgan xususiyatni **umuman o'lchamagan**.

Tuzatish ikki bosqichli: (a) fixture haqiqiyligini tekshiradigan alohida assert — u rad etilgan arifmetikaning O'ZINI ishlatib, tanlangan juft haqiqatan yo'qotishini isbotlaydi; (b) chekli domen (kadr kengligi ~1280) **to'liq sanab chiqiladi**, ya'ni «omadli fixture» yo'li butunlay yopiladi.

⚠ **B varianti G-14(b) ni ham qizartirdi** va bu **to'g'ri xulq**, sabotajning nosozligi emas: `// verdict` dan iborat fayl G-12 dan o'tadi, lekin unda `removeQueries` yo'q. Izoh filtrini yolg'iz o'lchash uchun sabotaj `removeQueries` bilan takrorlandi (C/D variantlari): C 🔴 faqat G-12, D 🟢 **8/8**. Ya'ni yagona o'zgaruvchi izoh bo'lganda darvoza aynan reja aytgandek ishlaydi.

## Verification

| O'lchov | Boshlang'ich | Yakuniy |
|---|---|---|
| `vitest run` | 338 (28 fayl) | **394 (30 fayl)** |
| `node --test` | 115 | **123** |
| `npm run typecheck` | toza | toza |
| `npm run lint` | toza | toza |
| `npm run i18n:check` | 777 × 3 | **777 × 3 (o'zgarmagan)** |

Qabul mezonlari: `grep -c 'from "react"' zone-geometry.ts` → **0**; `grep -ci "wald" wilson.ts` → **0**; `MIN_SAMPLE_FOR_PERCENT === 20`; taqiqlangan nomlar reyestri **17 ta** (≥13, `assert` bilan, takrorsizligi ham tekshirilgan); `package.json`/`package-lock.json` **tegilmagan**.

## Decisions Made

Yuqoridagi `key-decisions` ga qarang. Eng ta'sirlilari:

1. **`denormalize` yaxlitlaydi.** Bu bezak emas, aylanma yo'qotishsizlikning yagona yo'li. Zoom bunga bog'liq emas — masshtab SVG `viewBox` transformida.
2. **`translate` siljish miqdorini qisadi.** Per-vertex clamp poligonni jimgina ezardi va zona rastani emas, boshqa shaklni o'lchardi — bu aynan «jimgina noto'g'ri hisob» sinfi.
3. **`point` — kuzatilgan ulush.** Oraliqning markazi (0,885) nuqta baho (0,900) dan farq qiladi; markazni ekranga chiqarish direktor o'qiydigan raqamni jimgina o'zgartirardi. Test buni assimetriya orqali qulflaydi va shu bilan rad etilgan formulani ham ajratadi.
4. **Rad etilgan amal aynan o'sha havolani qaytaradi.** Undo steki nusxa emas, havola ro'yxati; rad etilgan amal yangi massiv qaytarsa, `Ctrl+Z` «hech nima qilmaydigan» qadamni bosib o'tishga majbur qilardi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `addVertex`/`insertMidpoint` uchun `MAX_VERTICES_PER_ZONE` chegarasi**

- **Found during:** Task 1
- **Issue:** Reja `<behavior>` da faqat `deleteVertex` ning `MIN_VERTICES` himoyasini sanaydi. Yuqori chegarada esa hech qanday funksiya to'smasdi, holbuki `<threat_model>` da T-05-12 (juda ko'p tepali poligon) `mitigate` dispozitsiyasi bilan turibdi va uning mitigatsiyasi aynan `MAX_VERTICES_PER_ZONE = 12`.
- **Fix:** Ikkala qo'shuvchi funksiya ham chegaraga yetganda kirishni o'zgarishsiz qaytaradi — `deleteVertex` ning quyi chegaradagi naqshiga simmetrik.
- **Files modified:** `frontend/src/lib/zone-geometry.ts`, `frontend/src/lib/zone-geometry.test.tsx`
- **Verification:** «⚠ MAX_VERTICES_PER_ZONE da RAD ETILADI (T-05-12)» testi
- **Committed in:** `7cddad6`

**2. [Rule 2 - Missing Critical] `translate` ning chegara xulqi va shakl saqlanishi**

- **Found during:** Task 1
- **Issue:** Reja `translate` uchun chegara xulqini umuman belgilamaydi. Qismasa, nusxalangan poligon 0..1 dan chiqib ketardi va T-05-11 ning aynan o'sha aniqlanmagan holatini yasardi; har tepani alohida qisish esa poligonni deformatsiya qilardi.
- **Fix:** Siljish miqdori qisiladi (rigid translate), tepalar emas.
- **Files modified:** `frontend/src/lib/zone-geometry.ts`, `frontend/src/lib/zone-geometry.test.tsx`
- **Verification:** S3 sabotaji shu testni qizartiradi
- **Committed in:** `7cddad6`

**3. [Rule 1 - Bug] Aylanma testi hech nimani o'lchamayotgan edi**

- **Found during:** Task 1 sabotaj o'lchovi (S2)
- **Issue:** Yuqorida to'liq yozilgan — qo'lda tanlangan besh juft IEEE754 da tasodifan aniq aylanardi.
- **Fix:** Fixture haqiqiyligi asserti + chekli domenni to'liq sanash.
- **Files modified:** `frontend/src/lib/zone-geometry.test.tsx`
- **Verification:** S2 endi 2 testni qizartiradi
- **Committed in:** `83969a6`

**4. [Rule 3 - Blocking] `toBeCloseTo(x, 3)` ning chegarasi rejadagi tolerans emas**

- **Found during:** Task 2
- **Issue:** Reja `1e-3` tolerans va uch xonali literal (`0,825`) talab qiladi. `toBeCloseTo(0.825, 3)` ning haqiqiy chegarasi `0,5·10⁻³`, haqiqiy qiymat esa `0,825633` — ya'ni idiomatik yozuv qatorni **yiqitardi** va keyingi ijrochi literalni aniqroq yozib, reja talab qilgan «qo'lda hisoblangan uch xonali literal» xususiyatini yo'qotardi.
- **Fix:** Aniq `TOLERANCE = 1e-3` va `expectNear()` yordamchisi; sabab test faylida yozilgan.
- **Files modified:** `frontend/src/lib/wilson.test.tsx`
- **Verification:** 11/11 yashil, literal `0,825` va `0,945` saqlandi
- **Committed in:** `ae9c32d`

---

**Total deviations:** 4 auto-fixed (2 missing critical, 1 bug, 1 blocking)
**Impact on plan:** Hammasi to'g'rilik uchun zarur; qamrov kengaymadi. Ikkita `Rule 2` bandi rejaning `<threat_model>` idagi dispozitsiyalarni bajaradi, ya'ni ular yangi talab emas.

## Issues Encountered

- **`node_modules` worktree'da yo'q edi** — `npm ci` bilan lockfile'dan tiklandi (yangi paket qo'shilmadi).
- **Birinchi `vitest run` sovuq kesh bilan 7 xato berdi** (21/28 fayl, 133 s). Ikkinchi ishga tushirish 28/28 va 338 test — ya'ni bu flake, nosozlik emas. Boshlang'ich shu ikkinchi o'lchovdan olindi.
- **UI-SPEC §6.2 va §15 (G-19) `scripts/zone-geometry.test.mjs` ni ko'rsatadi** — reja buni M-3 sifatida oldindan hal qilgan; ijro §S-13 ning A yo'lini bajardi va sababni ikkala faylning docstringiga yozdi.

## Keyingi rejalar uchun

- **05-13** `lib/blind-audit-queries.ts` va `components/blind-audit/**` ni yaratganda G-12/G-14 **tahrirsiz** ishlay boshlaydi: uchala «hali yo'q» sharti o'z-o'zini qurollantiradigan qilib yozilgan. Katalog ≥3 fayl bo'lishi va `removeQueries` ning mavjudligi darhol talab qilinadi.
- **05-09** (zona muharriri) `zone-geometry.ts` ni to'g'ridan-to'g'ri import qiladi; render qatlami `zone-canvas.tsx` da bo'lishi shart, aks holda D-05 ning chiqish yo'li yopiladi.
- **05-14** (aniqlik hisoboti) `wilsonInterval` va `MIN_SAMPLE_FOR_PERCENT` ni ishlatadi; `n < 20` da birorta foiz chizilmasligi §11.5 ning talabi.
- **05-06** (server) `isSelfIntersecting`, `MAX_VERTICES_PER_ZONE` va `MAX_ZONES_PER_CAMERA` ning **ishonch manbaini** yozadi — bu yerdagilar qulaylik.
- ⚠ **D-05 ning UAT bandi ochiq:** 50+ poligonli kamerada `pointermove` narxi hali o'lchanmagan. U darvoza emas va bo'lmasligi ham kerak.

## User Setup Required

None.

## Self-Check: PASSED

Beshala fayl diskda mavjud; oltala commit `git log` da topildi. Sabotaj
artefaktlari (`blind-audit-queries.ts`, `components/blind-audit/`,
`review/blind/`) to'liq o'chirilgan — `git status` faqat shu rejaning
fayllarini ko'rsatadi va birorta kuzatilayotgan fayl o'chirilmagan.

## Known Stubs

Yo'q. Uchala modul ham to'liq ishlaydi va sof funksiyalardan iborat;
birorta hardkod bo'sh qiymat yoki placeholder matn yo'q.

⚠ Bir band **ataylab hali qurollanmagan** va u stub EMAS: G-12/G-14
skanerlaydigan uchala yo'l (`lib/blind-audit-queries.ts`,
`components/blind-audit/`, `app/[locale]/(app)/review/blind/`) **05-13
da tug'iladi**. Bugungi holat `skip` bilan emas, ochiq
`assert.equal(exists, false)` bilan qayd etilgan, ya'ni fayllar paydo
bo'lgan kuni darvoza **bu faylga tegilmasdan** ishlay boshlaydi. Bu
rejaning ataylab tanlangan tartibi: darvoza ekranlardan OLDIN qo'yiladi.

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-08*
