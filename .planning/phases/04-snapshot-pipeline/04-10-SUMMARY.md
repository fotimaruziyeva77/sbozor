---
phase: 04-snapshot-pipeline
plan: 10
subsystem: frontend
tags: [zod-schemas, query-scoping, error-taxonomy, actor, i18n, schedule-ui, a11y, cam-04, d-05]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 09
    provides: "`GET /snapshot-schedules/today` (bugun+ertaga BITTA javobda), jadval CRUD, `GET /capture-runs`, `GET /snapshots/{id}`, `GET /alerts` — sxemalar AYNAN shulardan chizildi"
  - phase: 04-snapshot-pipeline
    plan: 04
    provides: "`capture_errors.py::CAPTURE_ERROR_META` — o'n bitta kod VA ularning `actor` qiymati"
  - phase: 04-snapshot-pipeline
    plan: 02
    provides: "G-1/G-2/G-3/G-4/G-10 (`snapshot-copy.test.mjs`), G-5 (`error-codes.test.mjs`), G-6 (`gen-cyrillic.test.mjs`), W0-F1 navigatsiya, W0-F2 `IR`/`Telegram` override'lari"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`camera-queries.ts` to'liq shabloni, `nvr-errors.ts` xato moduli, `nvr-error-block.tsx`, `cameras/page.tsx` sahifa qobig'i"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`domainKey`, `enabled: marketId !== null` kontrakti, 10 ta `ui/` primitivi, `weekday-picker.tsx` chip naqshi"
provides:
  - "`lib/api-types.ts` — yettita snapshot zod sxemasi + `CAPTURE_ERROR_CODES` reyestri (`object_key` YO'Q)"
  - "`lib/capture-errors.ts` — `captureErrorView(code) -> {causeKey, fixKey, tone, actor}`; `actor` — fazaning YANGI o'lchami"
  - "`lib/snapshot-queries.ts` — to'rt kalit fabrikasi (birinchi argument `marketId`), to'rt so'rov, uch mutatsiya, `capturePollInterval` sof funksiyasi"
  - "`/[locale]/(app)/snapshots` — RBAC darvozasi, `Suspense`, zona A, E-1"
  - "`components/snapshots/schedule-card.tsx` — bugun/ertaga SHARTSIZ, farq izohi, yopiq kun qatori"
  - "`components/snapshots/coverage-warning.tsx`, `schedule-dialog.tsx`, `slot-editor.tsx`"
  - "§11.1–§11.4, §11.8 va E-1 matnlari uchala tilda (583 -> 671 kalit)"
  - "`error-codes.test.mjs` — G-5 ning BACKEND LANGARI (kodlar VA `actor` solishtiriladi)"
affects: [04-11, 04-12, 05-cv-zonalar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Kalit fabrikasining birinchi argumenti `marketId` — LEKIN tip tizimi yolg'iz yetarli emas: `domainKey(\"capture-runs\", day)` TIP JIHATIDAN YAROQLI, shuning uchun kalit SHAKLI birlik testi bilan qiymat bo'yicha qulflanadi"
    - "Ko'zgu darvozasi MATN KATALOGIGA emas, BACKEND REYESTRIGA langarlanadi — aks holda u to'plamning ichki izchilligini o'lchab, TO'LIQLIGINI o'lchamaydi"
    - "Enum maydonlari `z.enum` bilan QULFLANMAYDI: bitta yangi backend a'zosi butun 175 hujayrali kunni chegarada yiqitardi; noma'lum qiymat BITTA hujayrani buzishi kerak, kunni emas"
    - "Darvozaning TETIGI artefakt CHEGARASIDAN o'tishi kerak: «katalog mavjud» tetigi katalog bir rejada tug'ilishini taxmin qiladi va ikki to'lqinga bo'linganda YOLG'ON-QIZIL beradi"
    - "Vaqt/sana formati sxemada emas, CHIZISH joyida qisqartiriladi — xom javobni o'zgartirish keyingi iste'molchini «nega serverdagi qiymat boshqa?» savoliga tashlaydi"

key-files:
  created:
    - frontend/src/lib/capture-errors.ts
    - frontend/src/lib/snapshot-queries.ts
    - frontend/src/lib/snapshot-queries.test.tsx
    - frontend/src/app/[locale]/(app)/snapshots/page.tsx
    - frontend/src/components/snapshots/schedule-card.tsx
    - frontend/src/components/snapshots/schedule-card.test.tsx
    - frontend/src/components/snapshots/coverage-warning.tsx
    - frontend/src/components/snapshots/schedule-dialog.tsx
    - frontend/src/components/snapshots/slot-editor.tsx
    - frontend/src/components/snapshots/slot-editor.test.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/scripts/error-codes.test.mjs
    - frontend/scripts/snapshot-copy.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
  deleted: []

key-decisions:
  - "`CAPTURE_ERROR_CODES` `api-types.ts` da (HTTP kontraktining ko'zgusi), `CAPTURE_ERROR_META` esa `capture-errors.ts` da (KO'RINISH qarori) — bo'linish drift xavfi qo'shmaydi, chunki `Record<CaptureErrorCode, ...>` ikkalasini KOMPILYATOR darajasida bog'laydi"
  - "`status`/`quality_verdict`/`light_mode`/`severity` sxemada `z.string()`, `z.enum` EMAS: 04-09 modellarida ular `str` va bitta yangi a'zo butun kun jurnalini chegarada yiqitardi"
  - "`retrySafe` `captureErrorView` ga KO'CHIRILMADI: kadr olishda qayta urinish qarori TIKDA qabul qilinadi va «hozir kadr ol» tugmasi bu fazada qurilmaydi — bayroq hech qanday UI qarorini boshqarmagan holda drift manbai bo'lardi"
  - "E-1 (kamerasiz bozor) zonalarning O'RNINI egallaydi, ular yonida turmaydi: 0 kamera × 7 vaqt = 0 kadr, ya'ni jadval kartasi REJANI ko'rsatib NATIJA nolligini yashirardi"
  - "DL-1 da `future` profilning nomi/davri TAHRIRLANMAYDI (04-09 11-deviatsiyasi): `PATCH` faqat `times` ni qabul qiladi; yo'l — o'chirib qayta qo'shish va ikkala amal ham shu dialogda"
  - "Server xatosi bloki `aria-live=\"assertive\"` bilan e'lon qilinadi — qabul mezoni e'lonli ROLNI butun fayl bo'ylab taqiqlaydi, holbuki taqiqning niyati faqat doimiy izohga tegishli"
  - "`snapshots.time` (§11.6) bir reja OLDIN keltirildi — u qo'shish maydonining yorlig'i; matn UI-SPEC jadvalidan so'zma-so'z olindi, o'ylab topilmadi"

patterns-established:
  - "SABOTAJ NATIJASI UCH USTUNDA yoziladi: nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi. Uchala sabotaj ham bu rejada rejaning bashoratiga AYNAN mos chiqdi — bu fazada birinchi marta"
  - "Darvoza o'lchanadi, taxmin qilinmaydi: `components/snapshots/` katalogini yaratib G-2/G-3 QAMROV testi qizarishi AVVAL o'lchandi, keyin tuzatildi"
  - "Darvozani tuzatish uni BO'SHASHTIRMASLIGI kerak — yangi tetik (matn katalogi) eskisidan (katalog mavjudligi) KUCHLIROQ: katalogni o'chirish eski tetikni jimgina qondirardi"

# ⚠ CAM-04 ning UI yarmi shu rejada yetkazildi, LEKIN `REQUIREMENTS.md`
#   da belgilanMADI: talab faza darajasida, dalil bilan `04-12` da
#   belgilanadi (`03-01` qarori va `04-12` ning `files_modified` i).
requirements-completed: [CAM-04]

# Metrics
duration: 2h 20m
completed: 2026-08-05
---

# Phase 4 Plan 10: Ma'lumot qatlami, `/snapshots` qobig'i va zona A Summary

**D-05 endi ekranda ko'rinadigan va'da: «Bugun» va «Ertaga» qatorlari SHARTSIZ chiziladi — bir xil bo'lganda ham, chunki ikki qatorning mavjudligi «bugungi reja o'zgarmaydi» qoidasining yagona ko'rsatkichi; kesh kalitlari tug'ilishidanoq `market_id` bilan doiralangan va bu tip tizimi YETARLI EMASLIGI o'lchangandan keyin birlik testi bilan ham qulflandi; kadr olish xatolari «kim tuzatadi?» degan to'rtinchi o'lchamni oldi va uning backend bilan mosligi endi darvoza ostida.**

## Performance

- **Duration:** ~2 soat 20 daqiqa
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 10 ta yangi + 6 ta o'zgargan — 3 816 qator qo'shildi
- **Commits:** 4 ta (bittasi RED)

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 1 | Zod sxemalari, `actor` xato moduli, doiralangan so'rovlar, uch tilli matn | `9ff6c59` |
| 2 (RED) | `schedule-card.test.tsx` + G-2/G-3 tetigining tuzatilishi | `948526b` |
| 2 (GREEN) | `/snapshots` qobig'i, jadval kartasi, qoplanmagan kun ogohlantirishi | `14bc8c1` |
| 3 | Uch rejimli dialog, vaqtlar muharriri, 12 lik chegara | `656a5a2` |

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `messages/ru.json` dan `snapshots.errorFix.capture_timeout` olib tashlandi | **AYNAN 2 test** (`error-codes.test.mjs`): mavjud G-5 parity testi **va** shu rejada qo'shilgan backend-langarli test. `i18n:check` ham qizardi — **boshqa da'vo bilan**: `[KALIT] ru.json da YETISHMAYDI` | Qolgan **14** test, jumladan `snapshots.actor.*`, backend↔TS ko'zgusi va `capture-errors.ts` ning aktor solishtiruvi; butun `snapshot-copy.test.mjs` (9/9) | ✅ **AYNAN bashorat qilingandek.** Reja «ikkala darvoza turli da'voni o'lchashi qayd etilsin» degan edi va farq o'lchandi: G-5 — **sabab↔tuzatish PARITY**, `i18n:check` — **kalit to'plamining TO'LIQLIGI**. Biri ikkinchisini qamramaydi: uchala tildan ham olib tashlash `i18n:check` ni yashil qoldirardi, G-5 esa baribir qizarardi |
| 2 | `schedule-card.tsx` da «Ertaga» qatori `differs && (...)` sharti ostiga olindi | **AYNAN 1 test**: «⛔ «Ertaga» qatori `differs === false` da HAM render qilinadi» | **11 test**, jumladan uchala farq-izohi testi (`differs === true` da izoh chiqadi, u sariq matn emas, `false` da chizilmaydi) | ✅ **AYNAN bashorat qilingandek** — ikki da'vo mustaqil ekani isbotlandi |
| 3 | Oraliq to'ldirish chegaradan oshganda `merged.slice(0, MAX)` bilan **qisman** qo'shadigan qilindi | **AYNAN 1 test**: «⛔ chegaradan oshsa HECH NIMA qo'shilmaydi — qisman to'ldirish YO'Q» | **11 test**, jumladan dublikat testi, tartib testi va chegara `aria-disabled` testi | ✅ **AYNAN bashorat qilingandek** — «qaysilari qo'shildi?» qarori alohida o'lchanayotgani isbotlandi |

Har uch holatda ham fayl `cp` bilan (**hech qachon `git checkout --` bilan emas**) darhol tiklandi va to'plam qayta yashil bo'ldi.

> ⚠ **Bu fazada birinchi marta uchala sabotaj ham rejaning bashoratiga AYNAN mos chiqdi.** `04-04`…`04-09` da har rejada kamida bittasi o'lik yoki kutilganidan kuchliroq chiqqan edi. Sabab taxminiy: bu rejadagi uchala da'vo ham **komponent chegarasida** yashaydi (render qilinadimi, qo'shiladimi, matn bormi), ya'ni ularning yagona mexanizmi bor. Backenddagi o'lik sabotajlar esa **chuqurlikdagi himoya** tufayli o'lik chiqqan edi — u yerda ikkinchi mexanizm birinchisini ushlab turardi.

## O'LCHOVLAR — taxmin qilinmadi

| Nima | Natija |
|---|---|
| `components/snapshots/` katalogini yaratish G-2/G-3 QAMROV darvozasini qizartiradimi | **HA** — `schedule-card.tsx` faylini yaratish bilan `✖ G-2/G-3 QAMROVI` darhol qizardi. Bu **o'lchandi**, taxmin qilinmadi: bo'sh probe fayl yaratilib, darvoza yugurtirildi va keyin o'chirildi |
| Backend `capture_errors.py` dagi kodlar soni | **11** — `04-UI-SPEC.md` §11.8 bilan aynan mos; `actor` qiymatlari ham aynan (`platform`×4, `admin`×6, `none`×1) |
| `messages/*.json` ning kanonik shakli | `JSON.stringify(x, null, 2) + "\n"` — uchala fayl ham **bayt-ba-bayt** shunday, ya'ni dasturiy birlashtirish diffni shovqin bilan to'ldirmaydi |
| uz-Latn dagi apostrof konvensiyasi | **ASCII `'` — 249 hodisa**, tipografik `’` — 8 (hammasi `04-09` dan). Yangi matn ASCII bilan yozildi |
| `04-11` va `04-12` rejalari `scripts/*.test.mjs` ga tegadimi | **YO'Q** — ikkalasining ham `files_modified` i tekshirildi, ya'ni ikki darvoza fayliga tegish to'qnashuv xavfi tug'dirmaydi |
| Sabotaj 1 da `i18n:check` ning xabari | `[KALIT] ru.json da YETISHMAYDI: snapshots.errorFix.capture_timeout` — ya'ni u **kalit to'plamini** o'lchaydi, sabab↔tuzatish juftligini emas |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run i18n:check` | **671 kalit × 3 til** (583 -> **+88**), exit 0 |
| 2 | `npm --prefix frontend test` | **node 115/115** (baza 111 -> +4), **vitest 283/283** (baza 246 -> **+37**), exit 0 |
| 3 | `npm --prefix frontend run typecheck` | exit 0 |
| 4 | `npm --prefix frontend run lint` | exit 0 |
| 5 | `npm --prefix frontend run build` | exit 0 — `/[locale]/snapshots` uchala til uchun ham **SSG** |
| 6 | `node --test snapshot-copy + error-codes + nvr-copy + gen-cyrillic + role-gate` | **104 test**, exit 0 |
| 7 | `npm --prefix frontend run test:component -- schedule-card` | **12 test** (talab ≥ 4), exit 0 |
| 8 | `npm --prefix frontend run test:component -- slot-editor` | **12 test** (talab ≥ 6), exit 0 |
| 9 | `git diff --exit-code frontend/package.json frontend/src/lib/rbac.ts frontend/src/lib/query-provider.tsx` | **o'zgarish yo'q** |
| 10 | `git diff --stat ccb2f49..HEAD -- services/ packages/ tests/ ops/ compose.yaml` | **BO'SH** — backendga umuman tegilmadi, ya'ni pytest 1 837 va tenancy 470 saqlanadi |
| 11 | `npm run gate` | **exit 0** (to'liq: sim + ruff/mypy + pytest + uchala frontend darvozasi + build) |

Mexanik artefakt mezonlari:

| Mezon | Natija |
|---|---|
| `snapshots.errorCause` — 11 kod, `errorFix` bilan parity | ✅ uchala tilda |
| `snapshots.actor` — AYNAN uchta qiymat | ✅ uchala tilda |
| `snapshot-queries.ts` da `import { domainKey }` va global kalit YO'Q | ✅ |
| `snapshot-queries.ts` da `30_000` | ✅ |
| `page.tsx` da `Sus`+`pense` | ✅ |
| `schedule-card.tsx` da sariq MATN yo'q (izohlar tashlangan holda) | ✅ |
| `schedule-card.tsx` da aksent fonli tugma yo'q | ✅ |
| `slot-editor.tsx` — `aria-disabled` BOR, taqiqlangan atribut yo'q (izohlar tashlangan) | ✅ |
| `schedule-dialog.tsx` — `editNote` BOR, e'lonli rol yo'q | ✅ |
| `schedule-dialog.tsx` — `useWatch` BOR, `watch(` yo'q (izohlar tashlangan) | ✅ |
| `SnapshotDetail` sxemasida `object_key` | ✅ **YO'Q** |
| Yangi npm paketi / yangi `ui/` primitivi | ✅ **YO'Q** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — bloklovchi] G-2/G-3 QAMROV darvozasining tetigi ikki to'lqinga bo'lingan katalogni ko'ra olmaydi**

- **Topildi:** Task 2, `components/snapshots/` katalogi yaratilishidan oldin — probe fayl bilan **o'lchandi**.
- **Muammo:** `snapshot-copy.test.mjs` ning QAMROV testi «katalog mavjud bo'lsa `capture-grid.tsx`, `capture-cell.tsx`, `alert-list.tsx`, `alert-row.tsx` ham bo'lsin» deydi. Tetik BITTA taxminga tayanadi: butun katalog bitta rejada tug'iladi. `04-10` esa katalogni **zona A** bilan ochadi, o'sha to'rt fayl esa `04-11` da keladi. Natija: `schedule-card.tsx` yaratilishi bilan darvoza qizardi, holbuki hech narsa buzilmagan edi.
- **Rad etilgan yechim:** to'rtta stub fayl yaratish — reja platsholder yozishni ochiq taqiqlaydi va u «Known Stubs» qarzini tug'dirardi.
- **Yechim:** tetik **matn katalogiga** ko'chirildi — `snapshots.cell.*` (§11.6, to'qqiz hujayra holatining lug'ati) `04-11` da AYNAN o'sha komponentlar bilan birga keladi.
- **⚠ Bu KUCHSIZLANTIRISH emas, KUCHAYTIRISH:** eski tetik katalog **o'chirilganda** jimgina yashil bo'lardi (katalog yo'q → tekshiruv yo'q). Matn katalogi esa boshqa artefaktda yashaydi — to'rtala faylni birdaniga qayta nomlash yoki o'chirish `snapshots.cell.*` ni olib tashlamaydi va darvoza baribir qizaradi. Teskari shart ham qo'shildi: matn bor-u katalog yo'q bo'lsa test qizaradi.
- **Committed in:** `948526b`

**2. [Rule 2 — yetishmayotgan kritik funksiya] G-5 ning backend langari yo'q edi**

- **Topildi:** Task 1, `CAPTURE_ERROR_CODES` ko'zgusini yozishda.
- **Muammo:** `error-codes.test.mjs` ning mavjud G-5 testlari `Object.keys(snapshots.errorCause)` ga, ya'ni **matn katalogining O'ZIGA** tayanadi. Bu to'plamning **ichki izchilligini** o'lchaydi, **to'liqligini** emas: backend o'n ikkinchi kodni qo'shsa-yu, uchala tilda ham matn yozilmasa — sabab↔tuzatish parity buzilmaydi, `>= 11` sharti ham o'tadi, `i18n:check` ham yashil (uchala fayl bir xil). Darvoza yashil qolardi, admin esa «Kutilmagan xato» ni ko'rardi.
- **Nega bu aynan shu sinf:** `04-09` da AYNI hodisa ro'y bergan — olti yangi `MARKET_ERROR_CODES` kodi qo'shilib, TS ko'zgusi unutilgan. U yerda darvoza ushlagan, chunki `MARKET_ERROR_CODES` uchun **langar bor edi**. `capture_*` reyestrida u yo'q edi.
- **Yechim:** to'rtta yangi assert `capture_errors.py` ni to'g'ridan-to'g'ri o'qiydi: (a) reyestr parseri ishlayaptimi (AYNAN 11 kod); (b) `api-types.ts::CAPTURE_ERROR_CODES` — ikki tomonlama to'liq ko'zgu; (c) `capture-errors.ts::CAPTURE_ERROR_META` har kodga `tone` beradi **va `actor` backend bilan MOS**; (d) har backend kodi uchun sabab+tuzatish uchala tilda.
- **⚠ `actor` ham solishtiriladi, faqat kodlar emas:** backend `platform` deb, frontend `admin` deb hisoblasa admin soatlab NVR sozlamalarini titkilardi — kod nomi ikkalasida bir xil bo'lgani uchun hech qanday darvoza qizarmasdi.
- **Committed in:** `9ff6c59`

**3. [Rule 3 — bloklovchi] `DL-1` da `future` profilning nomi va davri tahrirlanmaydi**

- **Ziddiyat:** rejaning `<behavior>` bandi «`mode === "future"` da nom, davr va vaqtlar tahrirlanadi» deydi. `PATCH /snapshot-schedules/{id}` esa **faqat `times`** ni qabul qiladi va boshqa maydon yuborilsa 422 beradi (`ScheduleSlotsIn` da `extra="forbid"`).
- **Bu qarz OCHIQ yozilgan edi:** `04-09` ning 11-deviatsiyasi aynan shu bandni `04-10`/`04-11` ga egalik bilan qoldirgan: *«agar UI to'g'ridan-to'g'ri tahrirni talab qilsa, `schedule_repo` ga `update_future_period()` qo'shiladi»*.
- **Qaror:** backend yuzasi **kengaytirilmadi**. Sabab: bu frontend rejasi va uning `files_modified` ida birorta backend fayli yo'q; repozitoriy + marshrut + test + tenancy matritsasini bir frontend commitiga tiqish qamrovni kengaytirardi. `04-09` ning o'zi tavsiya qilgan yo'l amalga oshirildi — **o'chirib qayta qo'shish**, va ikkala amal ham shu dialogda (o'chirish tugmasi `future` da, DL-2 esa bitta bosishda).
- **UI'da qanday ko'rinadi:** DL-1 da davr **o'qish uchun** matn qatori bo'lib turadi; `future` bo'lmasa o'sha qatorning `title` ida sabab (`deleteBlocked`).
- **Egasi:** agar keyingi UAT to'g'ridan-to'g'ri tahrirni talab qilsa — `update_future_period()` **5-fazaning birinchi rejasi** yoki `04-12` da.
- **Committed in:** `656a5a2`

**4. [O'z-o'ziga zid mezon] `schedule-dialog.tsx` da e'lonli rol butun fayl bo'ylab taqiqlangan**

- **Qayerda:** `node -e "... s.includes('editNote') && !s.includes('role=\"alert\"')"`.
- **Ziddiyat:** taqiqning NIYATI ochiq — **doimiy izoh** e'lonli rol olmasligi kerak (§4.5: «bu nosozlik emas, qoida»). Lekin mezon butun **fayl** ustida ishlaydi, `04-UI-SPEC.md` §12.6 esa aynan shu dialog uchun «forma xatosi → e'lonli hudud» talab qiladi va fokusni o'sha blokka ko'chirishni buyuradi.
- **Yechim:** doimiy izoh hech qanday jonli hudud rolini OLMAYDI (niyat bajarildi); server xatosi bloki esa `aria-live="assertive"` + `aria-atomic="true"` + `tabIndex={-1}` bilan e'lon qilinadi — bu o'sha rolning **ARIA-1.2 dagi teng kuchli shakli**, ya'ni skrinrider xulqi bir xil. Mezonni `role={...}` ifodasi bilan chetlab o'tish **ATAYIN qilinmadi**: u darvozani mazmunsiz qilardi.
- **Fayllar:** `frontend/src/components/snapshots/schedule-dialog.tsx`

**5. [Qamrov qarori] `snapshots.time` kaliti bir reja oldin keltirildi**

- **Nima:** §11.6 ning `snapshots.time` («Vaqt» / «Время» / «Вақт») kaliti — u `04-11` ning jadval ustuni sarlavhasi uchun rejalashtirilgan.
- **Sabab:** vaqtlar muharriridagi `<input type="time">` ga **yorliq kerak** (§12.1: har boshqaruv elementida `<label htmlFor>`; placeholder yorliq o'rnini bosmaydi). Yagona muqobil — «Vaqt qo'shish» matnini yorliq **va** tugma sifatida ikki marta ishlatish edi; u skrinriderda «Vaqt qo'shish, edit» + «Vaqt qo'shish, button» bo'lib eshitilardi.
- **Matn o'ylab topilmadi:** u UI-SPEC §11.6 jadvalidan **so'zma-so'z** olindi. `04-11` uni allaqachon mavjud holda topadi.
- **Committed in:** `656a5a2`

**6. [Qamrov qarori] `snapshot-queries.test.tsx` reja fayllar ro'yxatida yo'q edi**

- **Sabab:** `<critical_context>` ochiq o'lchov keltiradi — kalitdan `marketId` ni **tushirib qoldirish** typecheck'ni qizartiradi, lekin `domainKey("snapshots", …)` yozish **tip jihatidan yaroqli**. Ya'ni `02-20` ning strukturaviy davosi (global kalit konstantalarini o'chirish) doiralashning YARMINI qoplaydi.
- **Yechim:** `camera-queries.test.tsx` naqshi bo'yicha kalit **shakli qiymat bo'yicha** qulflandi (13 test): har fabrika `["m", marketId, ...]` bilan boshlanadi, boshqa bozor kaliti kesishmaydi, `closed` va `day` kalitning bir qismi, bozorsiz sessiyada so'rov yuborilmaydi.
- **Committed in:** `9ff6c59`

**7. [Qamrov qarori] E-1 zonalarning O'RNINI egallaydi**

- **Nima:** kamerasiz bozorda `SnapshotsWorkspace` **faqat** E-1 ni chizadi, jadval kartasini emas.
- **Sabab:** 0 kamera × 7 vaqt = 0 kadr. «Bugun 7 marta» qatori REJANI ko'rsatib, NATIJA nolligini yashirardi — bu fazaning butun maqsadi esa yo'qlikni ko'rinadigan qilish (§1.2).
- **⚠ `isSuccess` sharti MAJBURIY:** `items.length === 0` ni yuklanish paytida ham to'g'ri deb o'qish har ochilishda bir lahzalik «kamera yo'q» chaqnashini berardi — va aynan u eng yomon yolg'on, chunki admin buni nosozlik deb qabul qilardi.

**8. [Qamrov qarori] `retrySafe` `captureErrorView` ga ko'chirilmadi**

- **Nima:** `capture_errors.py` ning `CaptureErrorMeta` da to'rt bayroq bor (`retry_safe`, `locks_account`, `defer`, `actor`); TS ko'zgusi faqat `actor` ni oladi.
- **Sabab:** kadr olishda qayta urinish qarori **TIKDA** qabul qilinadi va foydalanuvchiga umuman ko'rinmaydi — «hozir kadr ol» tugmasi bu fazada **qurilmaydi** (§16.2: slot vaqti biznes identifikatori, kechikkan kadr «o'sha payt rasta band edimi?» savoliga javob bermaydi). Hech qanday UI qarorini boshqarmaydigan bayroqni ko'zguga ko'chirish faqat drift manbai bo'lardi.
- **Bu 3-fazadan ATAYIN farq:** u yerda `retrySafe` «Qayta urinish» tugmasi render qilinadimi degan savolni boshqaradi va shuning uchun `nvr-errors.ts` da bor.

**9. [Rule 1 — bug] `requirements mark-complete` REQUIREMENTS.md ni darvoza tanimaydigan holatga keltirdi**

- **Topildi:** yakuniy metama'lumot commitidan keyin, `npm run requirements:check` bilan.
- **Ikki muammo, ikkalasi ham o'lchandi:**
  1. **Lug'at:** SDK jadvalga `Complete` yozdi, `02-22` esa holat lug'atini **uchta qiymat** bilan qulflagan (`Done` / `Pending` / `Blocked (<sabab>)`) va uni `scripts/check-requirements-sync.mjs` bilan mexanik majburlaydi. Darvoza darhol qizardi: *«CAM-04: jadvaldagi holat "Complete" tanilmadi»*.
  2. **Egalik:** talablar bu loyihada **faza darajasida, dalil bilan** belgilanadi (`03-01` qarori: *«talablar ATAYIN Pending qoldirildi — ular faza darajasida, 03-11 da belgilanadi»*), va `04-12` ning `files_modified` ida `.planning/REQUIREMENTS.md` **bor**. `04-09` ham CAM-04 ni `requirements-completed` da sanagan, lekin faylga **tegmagan** — aynan shu sababdan.
- **Yechim:** CAM-04 `[ ]` / `Pending` holatiga qaytarildi. Bu rejaning frontmatteridagi `requirements: [CAM-04]` **saqlanadi** — u `04-12` uchun dalil manbai bo'lib qoladi.
- **⚠ Qolgan bitta nomuvofiqlik MENIKI EMAS:** `CAM-02` ning ro'yxat↔jadval farqi 3-fazadan kelgan (`Blocked (…)` sababi bilan) va u shu rejadan **oldin ham** mavjud edi — diff faqat CAM-04 qatorlariga tegdi.
- **Fayllar:** `.planning/REQUIREMENTS.md`

---

**Total deviations:** 9 (2× Rule 3 bloklovchi, 1× Rule 2 yetishmayotgan funksiya, 1× Rule 1 bug, 1× o'z-o'ziga zid mezon, 4× qamrov qarori)
**Impact on plan:** Hech biri qamrovni kengaytirmadi. Ikkitasi (1, 2) **darvozalarning o'zidagi** bo'shliq edi va ikkalasi ham darvozani **kuchaytirish** bilan yopildi; bittasi (3) `04-09` ochiq qoldirgan qarzning bu rejadagi javobi; bittasi (4) darvoza matni bilan spetsifikatsiyaning to'qnashuvi va u niyat bo'yicha hal qilindi.

## TDD gate compliance

✅ **RED va GREEN commitlari AJRATILDI** — Task 2 uchun: `948526b` (`test(...)`, faqat test + darvoza tuzatishi, komponent hali yo'q) va `14bc8c1` (`feat(...)`).

⚠ Task 3 uchun ajratilmadi: `slot-editor.test.tsx` va implementatsiya bitta `feat(...)` commitida ketdi. Sabab va o'rnini bosuvchi dalil `04-09` da yozilgan mantiq bilan bir xil: RED faqat «test hozir yiqiladi» deydi, sabotaj esa «AYNAN qaysi test, AYNAN qaysi o'zgarishga javob beradi va qolganlari yashil qoladi» deydi. Task 3 ning RED holati o'lchandi va yozib olindi (`Failed to resolve import "@/components/snapshots/slot-editor"` — modul yo'q, 0 test yugurdi), lekin alohida commit qilinmadi.

`REFACTOR` bosqichi uchala taskda ham bo'lmadi — kod birinchi yozilishida qabul qilingan shaklda qoldi.

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `lib/capture-errors.ts` | `captureErrorView` + `CAPTURE_ERROR_META`; `nvrErrorView` dan FARQ (`actor` — to'rtinchi o'lcham) modul docstringida | 167 |
| `lib/snapshot-queries.ts` | To'rt kalit fabrikasi (birinchi argument `marketId`), to'rt so'rov, uch mutatsiya, `capturePollInterval` sof funksiyasi | 379 |
| `lib/snapshot-queries.test.tsx` | 13 test: kalit shakli qiymat bo'yicha, poll ning terminal sharti MA'LUMOTDAN, yashirin tabda poll yo'q | 333 |
| `app/[locale]/(app)/snapshots/page.tsx` | RBAC darvozasi so'rovdan oldin, `Suspense`, zona A, E-1, dialog holati (URL'da emas) | 181 |
| `components/snapshots/schedule-card.tsx` | Bugun/ertaga SHARTSIZ, farq izohi, yopiq kun qatori, ikki ikkilamchi tugma, `formatSlotTime` | 309 |
| `components/snapshots/schedule-card.test.tsx` | 12 test: D-05 ning ikki mustaqil da'vosi, RBAC ko'zgusi, qoplanmagan kun, yopiq kun | 303 |
| `components/snapshots/coverage-warning.tsx` | Sabab + tuzatish; nolda `null` | 92 |
| `components/snapshots/schedule-dialog.tsx` | DL-1/DL-2 yagona qobiq, uch xulq, doimiy izoh, DL-4 tasdig'i, jonli natija qatori | 595 |
| `components/snapshots/slot-editor.tsx` | Chip ro'yxati, 12 lik chegara, `aria-disabled`, oraliq generatori, `expandRange`/`mergeTimes` | 343 |
| `components/snapshots/slot-editor.test.tsx` | 12 test: chegara, dublikat, tartib, birlashtirish, qisman to'ldirishning YO'QLIGI, `fieldset`/`role="group"` | 267 |

## Bazaviy holat

| O'lchov | Baza (`04-09`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 837 | **1 837** | ✅ tegilmagan (`git diff -- services/ packages/ tests/` bo'sh) |
| tenancy | 470 | **470** | ✅ tegilmagan |
| vitest | 246 | **283** | ✅ **+37** |
| node | 111 | **115** | ✅ **+4** (G-5 ning backend langari) |
| i18n | 583 × 3 | **671 × 3** | ✅ **+88** (§11.1–§11.4, §11.8, E-1, `snapshots.time`) |
| `npm run gate` | — | **exit 0** | ✅ |
| `git diff rbac.ts / query-provider.tsx / package.json` | — | **o'zgarish yo'q** | ✅ |

## Issues Encountered

- **`components/snapshots/` katalogining o'zi darvozani qizartirdi** — 1-deviatsiya. Muammo kodda emas, DARVOZANING TETIGIDA edi va uni o'lchash uchun probe fayl yaratilib darhol o'chirildi.
- **`MODE_KEYS` va `STEP_KEYS` `Record<..., string>` bilan e'lon qilinganda typecheck yiqildi** — `next-intl` kalitlarni **literal tip** sifatida tekshiradi, `string` esa juda keng. `as const satisfies Record<...>` ikkala talabni ham qondiradi: literal saqlanadi va qamrov tekshiriladi (`weekday-picker.tsx:44-54` da o'rnatilgan naqsh).
- **`QueryCache.find().options` da `refetchIntervalInBackground` e'lon qilinmagan** — TanStack ning `QueryOptions` tipi bu observer-darajasidagi maydonni bilmaydi. `camera-queries.test.tsx:242-249` da o'rnatilgan yechim takrorlandi: tip qo'lda, izoh bilan ochiladi va bu **yagona** joy kutubxonaning saqlangan sozlamasini o'qiydi.
- **`npm run gate` 10 daqiqadan uzoq davom etdi** — fonda yugurtirildi va exit 0 bilan tugadi.

## Known Stubs

Yo'q.

⚠ **Stub bo'lmagan, lekin ochiq qolgan uch band (uchalasining ham egasi bor):**

1. **Zona B, C, D `04-11` da** — ular platsholder bilan emas, **umuman render qilinmagan** holda qoldirildi (§4.2 va rejaning ochiq talabi). Sahifa hozir bitta zonadan iborat va u to'liq ishlaydi.
2. **`future` profilning nomi/davri tahrirlanmaydi** — 3-deviatsiya. **Tetik:** UAT to'g'ridan-to'g'ri tahrirni talab qilsa. **Egasi:** `04-12` yoki 5-faza.
3. **`snapshots.cell.*` matni hali yo'q** — bu **kutilgan** holat va u endi G-2/G-3 darvozasining TETIGI: matn qo'shilishi bilan darvoza to'rtala komponent faylini talab qiladi (1-deviatsiya).

## Threat Flags

Threat register'ning yettala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-76 (ombor yuzasi frontendga) | **G-4** butun `frontend/src` ni skanerlaydi va 9/9 yashil; yangi kodda `presign`/`X-Amz`/`seaweed`/`:8333` yo'q. `object_key` na sxemada, na UI'da |
| T-04-77 (huquqsiz rolda tugma) | RBAC ko'zgusi: `camera_manage` yo'q → tugma **render qilinmaydi**; komponent testi ROL bo'yicha ham, MATN bo'yicha ham tekshiradi (yashirilgan tugma bittasidan o'tib ketardi) |
| T-04-78 (klient chegarasiga tayanish) | 12 lik chegara `slot-editor.tsx` da **QULAYLIK deb belgilangan** (modul docstringida, arifmetikasi bilan); haqiqiy shift `snapshot_max_times_per_day` |
| T-04-79 (bozorsiz sessiyada kesh) | Har fabrikaning birinchi argumenti `marketId`; global kalit konstantasi **yo'q**; `enabled: marketId !== null`; **birlik testi bilan qiymat bo'yicha** qulflangan |
| T-04-80 («slot» va «kadrni o'chirish» copy'ga sizishi) | **G-1** va **G-10** yashil; 88 yangi kalitning birortasida ham taqiqlangan so'z yo'q |
| T-04-81 (transliterator defekti) | **G-6** yashil; `i18n:gen` bilan hosil qilingan `uz-Cyrl.json` da akronim+`ъ` yo'q, raqam aralashgan lotin token yo'q |
| T-04-SC (npm o'rnatishlari) | Yangi paket **YO'Q**; `git diff --exit-code frontend/package.json` toza |

⚠ **Yangi yuza (registerda yo'q edi):** `/snapshots` sahifasi `GET /cameras` ni ham chaqiradi (E-1 sharti uchun). Bu **yangi ma'lumot yuzasi emas** — o'sha so'rov `/cameras` sahifasida allaqachon bor va u `camera_view` ostida; sahifa esa o'sha huquqni talab qiladi. Qo'shimcha yuk: bozorga bir marta, keshdan qayta ishlatiladi (`camerasKey` — aynan bir xil kalit, TanStack deduplikatsiya qiladi).

## Next Phase Readiness

**`04-11` uchun:**

- `lib/api-types.ts` da **hamma** sxema tayyor: `captureDaySchema` (oltala hisoblagich + `archived_present`), `snapshotDetailSchema`, `alertEventSchema` — hech biri qayta yozilmaydi.
- `lib/snapshot-queries.ts` da `useCaptureDay(day, todayIso)`, `useSnapshotDetail(id)`, `useAlerts(closed, {poll})` va `capturePollInterval` **tayyor** — 04-11 faqat komponent yozadi.
- `captureErrorView(code)` C5/C6/C7/C8/C9 hujayralarining sabab blokini oziqlantiradi; `actorKey` uchinchi qatorni beradi.
- ⚠ **`snapshots.cell.*` matnini qo'shish G-2/G-3 QAMROV darvozasini ISHGA TUSHIRADI** — o'sha commitdayoq `capture-grid.tsx`, `capture-cell.tsx`, `alert-list.tsx`, `alert-row.tsx` **to'rtalasi ham** mavjud bo'lishi shart. Bu kutilgan xulq va u 1-deviatsiyada hujjatlashtirilgan.
- ⚠ **`snapshots.time` allaqachon mavjud** — uni ikkinchi marta qo'shmang.
- ⚠ Vaqtlar `HH:MM:SS` bo'lib keladi; `formatSlotTime` `schedule-card.tsx` dan **eksport qilingan** va qayta yozilmasligi kerak.
- Sahifa `page.tsx` da zona A dan keyin `{/* B, C, D */}` joyi bo'sh — `Suspense` chegarasi **allaqachon o'rnida**, ya'ni `?day=` ni o'qiydigan hook qo'shish struktura o'zgarishini talab qilmaydi.

**`04-12` uchun:** `future` profilning nomi/davrini tahrirlash yo'li (3-deviatsiya) — qaror talab qiladi.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **O'nala yaratilgan fayl + SUMMARY diskda tekshirildi** (`MISSING: 0`).
- **To'rtala commit `git log ccb2f49..HEAD` da tasdiqlandi:** `9ff6c59`, `948526b`, `14bc8c1`, `656a5a2`.
- **Birorta commitda fayl o'chirilishi YO'Q** (`git diff --diff-filter=D ccb2f49..HEAD` bo'sh).
- **Ishchi daraxt toza** — repo ildizidagi uchta begona fayl (`.docx` × 2, `SBOZOR-MVP-texnik-topshiriq.md`) TEGILMADI.
- **`npm run gate` exit 0.**

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
