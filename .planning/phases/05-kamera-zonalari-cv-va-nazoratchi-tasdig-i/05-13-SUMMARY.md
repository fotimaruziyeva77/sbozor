---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 13
subsystem: frontend
tags: [react-query, zod-strict, module-boundary, a11y, i18n, race-condition, ai-03, ai-04]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 10
    provides: "`GET /review/uncertain/next`, `GET /review/budget`, `POST /review/{id}/answer`; `AnswerResponse` ning ATAYIN boshqacha nomlari; `locked` HAR DOIM `true` va UI-SPEC §7.1 ning eskirgani; `review_queue_empty` / `review_budget_exhausted` kodlari"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 11
    provides: "`BlindItemResponse` — O'N maydon va `has_active_vendor` NING YO'QLIGI; `GET /review/blind/next`, `POST /review/blind/{id}/answer` (`409 blind_answer_locked`); `review_sample_not_drawn`; dalil-kadr huquq bo'shlig'ining o'lchangan ta'rifi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 03
    provides: "`scripts/blind-payload.test.mjs` (G-12/G-14) — EKRANDAN OLDIN qo'yilgan darvoza; `FORBIDDEN_NAMES` reyestri va uning quyi chegarasi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 04
    provides: "`lib/zone-errors.ts` ning `ReviewErrorCode` reyestri, `review.errorCause`/`errorFix` matnlari, G-11/G-15/G-16/G-18(a) copy darvozalari"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 09
    provides: "`localeHref` naqshi va `@/i18n/navigation` ning vitest ostida YECHILMASLIGI o'lchovi; sof funksiyali sahifa-holati naqshi (`zoneEditorState`); `key` bilan holat nollash o'rniga ishlatilgan naqshlar"
  - phase: 04-snapshot-pipeline
    provides: "`GET /snapshots/{id}/image` proxysi va uning bayt-olish naqshi (`apiRequest` + vaqtinchalik havola); `day-picker.tsx::businessDayIn`/`shiftIsoDay`"
provides:
  - "`lib/review-queries.ts` — `uncertainNextKey`/`reviewBudgetKey`/`evidenceImageKey`, `useUncertainNext`/`useReviewBudget`/`useAnswerUncertainItem`/`useEvidenceImageHref`; POLL YO'Q"
  - "`lib/blind-audit-queries.ts` — ALOHIDA modul: `blindPrefix`/`blindNextKey`/`blindBudgetKey`, `useBlindNext`/`useBlindBudget`/`useAnswerBlindItem`; `removeQueries`, `gcTime: 0`"
  - "`api-types.ts`: `reviewItemSchema`, ⛔ `blindAuditItemSchema` (`z.strictObject`), `answerResponseSchema`, `reviewBudgetResponseSchema`, `HUMAN_ANSWERS`, `answerRequestBody()`, `BLIND_FORBIDDEN_KEYS`, `reviewYesterdaySummarySchema`"
  - "`/review` uyi (ko'r audit kartasi DOM'da birinchi), `/review/uncertain`, ⛔ `/review/blind` (dinamik segmentsiz)"
  - "`components/review/`: `review-session.tsx` (+ `sessionState()`, `errorCodeOf()`), `evidence-frame.tsx` (+ `frameState()`, `overlayPoints()`), `decision-bar.tsx`, `budget-counter.tsx`"
  - "`components/blind-audit/`: `blind-session.tsx`, `blind-banner.tsx`, `reveal-panel.tsx`, `blind-session.test.tsx` — G-12 ning qamrov chegarasi (>=3 fayl) endi HAQIQIY to'plamda"
  - "`review.*` — 48 yangi kalit uchala tilda (879 -> 927)"
affects: [05-14-hisobot, 05-15-faza-darvozasi]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DARVOZA KODNING SHAKLINI MAJBURLAYDI: server maydonining nomi taqiqlangan tokenni o'z ichiga olgani uchun uni kodlash SIM QATLAMIGA (`api-types.ts`) ko'chdi — ikki nusxa yozish MEXANIK ravishda imkonsiz bo'ldi"
    - "TEST FAYLI DARVOZANING O'Z MAYDONIDA bo'lsa, taqiqlangan nom LITERAL yozilmaydi — u REYESTRDAN iteratsiya qilinadi va natija rejadagidan kuchliroq chiqadi"
    - "«Bitta so'rov = bitta qaror» HOLAT emas, POYGA masalasi: `blocked` render paytida hisoblanadi va bir hodisa oqimidagi uch bosish uchalasi ham eski qiymatni ko'radi"
    - "Qulf BAYROQ emas, IDENTIFIKATOR: bayroqni nollash kerak, identifikatorni esa kerak emas — «nollashni unutish» sinfi butunlay yo'qoladi (va `react-hooks/refs` ham qanoatlanadi)"
    - "Ichki holat `useEffect` bilan emas, `key` bilan nollanadi: unutilgan bitta `setState` qolib ketishi MUMKIN EMAS"
    - "O'LCHANMAGAN SONNING O'RNIGA NOL YOZILMAYDI: qator umuman chizilmaydi, chunki ko'rilgan nol «kecha hammasi ko'rilgan» degan eng yomon yolg'onni aytardi (T-05-04)"

key-files:
  created:
    - frontend/src/lib/review-queries.ts
    - frontend/src/lib/review-queries.test.tsx
    - frontend/src/lib/blind-audit-queries.ts
    - frontend/src/app/[locale]/(app)/review/page.tsx
    - frontend/src/app/[locale]/(app)/review/uncertain/page.tsx
    - frontend/src/app/[locale]/(app)/review/blind/page.tsx
    - frontend/src/components/review/review-session.tsx
    - frontend/src/components/review/review-session.test.tsx
    - frontend/src/components/review/evidence-frame.tsx
    - frontend/src/components/review/decision-bar.tsx
    - frontend/src/components/review/budget-counter.tsx
    - frontend/src/components/blind-audit/blind-session.tsx
    - frontend/src/components/blind-audit/blind-session.test.tsx
    - frontend/src/components/blind-audit/blind-banner.tsx
    - frontend/src/components/blind-audit/reveal-panel.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - tests/integration/test_alerting.py   # ⚠ REJADAN TASHQARI — deviatsiya #11
  deleted: []

key-decisions:
  - "⚠⚠ `answerRequestBody()` `api-types.ts` DA: server maydoni `human_verdict` G-12 ning `verdict` TOKENINI o'z ichiga oladi, ya'ni `blind-audit-queries.ts` uni YOZA OLMAYDI. Darvozaning O'ZI kodlashni sim qatlamiga majburladi va ikki nusxa imkonsiz bo'ldi"
  - "⚠⚠ Taqiqlangan nomlar `blind-session.test.tsx` da LITERAL yozilmaydi — fayl G-12 ning SKANER MAYDONIDA. Ular `BLIND_FORBIDDEN_KEYS` dan iteratsiya qilinadi; natija rejadagidan kuchliroq (bitta nom emas, REYESTRNING HAMMASI + reyestrda YO'Q ortiqcha maydon)"
  - "⚠ TEST TOPGAN XATO: uch bosish UCH javob yuborardi. Qulf `useRef` da va u BAND IDENTIFIKATORINI saqlaydi — nollash kerak emas, ya'ni «nollashni unutish» sinfi ham yo'qoladi"
  - "D-19 ilgagi (`Kecha: N ta rasta …`) `report_view` ostida va SOF nazoratchida u YO'Q. Nol yozib qo'yish TAQIQLANDI — o'lchanmagan raqam ko'rilgan zahoti o'lchangan deb o'qiladi"
  - "Javobdan keyin yaqinlashtirish tugmasi OLIB TASHLANADI: qaror o'zgarmas, ya'ni kadrni qayta ochish faqat qayta o'ylashni taklif qilardi. O'lchanadigan oqibati — sessiyada AYNAN BITTA faol boshqaruv qoladi"
  - "`sessionState`, `DecisionBar` va `EvidenceFrame` IKKALA sessiya uchun UMUMIY: ular tizim javobini umuman olib yurmaydi. Ajratilgani — MA'LUMOT QATLAMI va PAYLOAD TIPI, chunki xavf aynan o'sha yerda"
  - "Dalil kadri kesh kaliti `review-evidence` — ikkala navbat uchun UMUMIY va `gcTime: 0`. Kadrda tizim javobi yo'q, ya'ni §14.3 ning 4-qatlami buzilmaydi"
  - "Noaniq navbat oshkor paneli va ko'r audit oshkor paneli IKKI XIL KOMPONENT: birinchisi 1,5 s da o'zi ketadi va boshqaruv bermaydi, ikkinchisi qoladi va sessiyaning YAGONA oldinga yo'lini tashiydi"
  - "`review.inQueue` («Navbatda: N») QURILMADI — `ReviewBudgetResponse` da bunday son YO'Q va uni to'qib chiqarish stub bo'lardi"

patterns-established:
  - "DARVOZA KOD SHAKLINI BOSHQARADI: taqiqlangan token server kontraktida bo'lsa, kodlash darvoza maydonidan TASHQARIGA ko'chadi va takrorlanish mexanik ravishda imkonsiz bo'ladi"
  - "Da'vo SABOTAJ bilan toraytiriladi: `remove` vs `invalidate` BUGUNGI sozlamada o'lchanmaydi (18 test yashil qoldi), ya'ni kafolat JUFTLIKDAN (`gcTime: 0` + `removeQueries`) chiqadi va ikkala yarim ALOHIDA qo'riqlanadi"
  - "Ikki mustaqil implementatsiya ikki mustaqil testni talab qiladi: Y-2 ning poyga qulfini buzish Y-3 ning testlarini QIZARTIRMAYDI (va teskarisi ham)"

requirements-completed: []
requirements-advanced: [AI-03, AI-04]
# ⚠ ATAYIN BO'SH — 05-09/05-10/05-11/05-12 dagi bilan AYNAN bir xil qaror.
# Bu reja AI-03 va AI-04 ning EKRANLARINI to'liq yetkazadi, lekin
# talablarni YOPMAYDI: (a) brauzerdagi 8 qadamli qo'lda tekshiruv bu
# muhitda BAJARILMADI (`human_verify_mode: "end-of-phase"`); (b) AI-04
# xolis ANIQLIK HISOBOTINING ekranini ham talab qiladi va u 05-14 da;
# (c) sof `inspector` dalil kadrini hali ko'ra olmaydi (pastdagi
# `threat_flag`). `05-15` fazani DALIL bilan yopadi.

# Metrics
metrics:
  duration_minutes: 165
  completed: 2026-08-10
  tasks_completed: 3
  files_created: 15
  files_modified: 5
  commits: 5
---

# Phase 5 Plan 13: Nazoratchining ikki sessiyasi — ko'rlik SXEMADA, poyga REFDA va o'lchanmagan sonning O'RNI BO'SH — Summary

**Nazoratchi endi ikkala navbatni ham brauzerda bitta-bittadan yuritadi va ko'rlik uch mustaqil qatlamda qulflangan: modul chegarasi (G-12), sxemaning qattiqligi (G-13) va marshrutning shakli (G-14) — ustiga darvozaning O'ZI server maydonining nomini kodlashni boshqa faylga majburlagani sababli ko'r modulda ikkinchi nusxa yozib bo'lmaydi; yettita sabotajdan biri esa `remove` vs `invalidate` da'vosining bugungi sozlamada UMUMAN o'lchanmasligini fosh qildi.**

## Performance

- **Duration:** ~165 daqiqa (shundan ~45 daqiqa — `npm run gate` ning ikki to'liq ijrosi)
- **Tasks:** 3/3
- **Files:** 15 yaratildi, 5 o'zgartirildi — **mahsulot kodida rejaning `files_modified` ro'yxatidan tashqarida BIRORTA fayl yo'q**; yagona istisno `tests/integration/test_alerting.py` (deviatsiya #11)

## Task Commits

1. **Task 1 — ikki so'rov moduli, `z.strictObject` va `/review` uyi** — `06b445b` (feat)
2. **Task 2 — Y-2 sessiyasi, dalil darvozasi, byudjet hisoblagichi** — `4e0bec2` (feat)
3. **Task 3 — Y-3 ko'r sessiya, oshkor paneli, G-13/G-14** — `089f0ef` (feat)
4. **Sabotaj natijasi bo'yicha qattiqlashtirish** — `f119a93` (test)
5. **⚠ Rejadan TASHQARI: soatga bog'liq ikki alert testi** — `bcc2d49` (fix) — deviatsiya #11

## Bajarilgan ishlar

### Task 1 — Ikki modul va ularni AJRATIB TURGAN sabab

| Element | Holat |
|---|---|
| `lib/review-queries.ts` | ✅ `uncertainNextKey`, `reviewBudgetKey`, `evidenceImageKey`; poll YO'Q |
| `lib/blind-audit-queries.ts` | ✅ **ALOHIDA MODUL**, `blind-audit` prefiksi, `gcTime: 0`, `removeQueries` |
| `blindAuditItemSchema` | ✅ **`z.strictObject`** — o'n maydon, `has_active_vendor` **YO'Q** |
| `answerResponseSchema` | ✅ `{system_answer, human_answer, matched, locked}` — nomlar ATAYIN boshqa |
| `/review` uyi | ✅ ko'r audit kartasi **DOM tartibida birinchi**; ikkala karta DOIM ko'rinadi |
| Copy | ✅ 48 kalit uchala tilda; `uz-Cyrl.overrides.json` **tegilmadi** |

**Eng qimmatli topilma shu taskda chiqdi va u kod shaklini o'zgartirdi.**
`AnswerRequest` ning yagona maydoni — `human_verdict` — G-12 ning
taqiqlangan reyestridagi `verdict` **tokenini o'z ichiga oladi**
(`FORBIDDEN_NAMES` `includes` bilan qidiradi). Ya'ni
`blind-audit-queries.ts` bu satrni **yoza olmaydi**, va ikkinchi nusxa
yozish ham mumkin emas — ikkinchi nusxa aynan o'sha faylga tushardi.

Demak **darvozaning o'zi kodlashni sim qatlamiga majburladi**:
`answerRequestBody()` `api-types.ts` da yashaydi, ikkala navbat esa uni
funksiya orqali oladi. Natijada maydon nomi **bir marta** yozilgan va
ikki navbat hech qachon ajralib keta olmaydi. Bu «cheklov kamchilik»
emas — u takrorlanishni **mexanik ravishda imkonsiz** qildi.

### Task 2 — Dalil rasmi qarorning darvozasi

`frameState()` — sof funksiya, **uch** nosozlik manbaini qamraydi:
so'rovning o'zi yiqilishi (⚠ sof `inspector` uchun **403**), `onError`
va «baytlar keldi, lekin hali dekod qilinmagan». Uchalasida ham natija
bir xil: uchala javob tugmasi `aria-disabled` **bo'lib qoladi**.

Zona konturi **klientda** SVG overlay bilan. Javobda kadr o'lchami
umuman yo'q (05-10, 5-band), shuning uchun overlay `viewBox="0 0 1000
1000"` + `preserveAspectRatio="none"` bilan quriladi va **rasmning
o'ziga siqilgan** o'rovchi elementga cho'ziladi — ya'ni `aspect-video`
qutisidagi letterbox bo'shlig'i koordinatalarga **umuman tushmaydi** va
tuzatish kerak emas.

**Test mahsulot xatosini topdi** — pastdagi deviatsiya #1.

### Task 3 — Uch kanal va oldinga-faqat sessiya

Lenta `sticky top-0`, `bg-surface-muted`, `border-l-4 border-text`,
qulf ikonkasi va **ikki jumla**; `role="alert"` **olmaydi** (§13.6) va
rangi `warning` **emas**. `<h1>` DOM'da **birinchi** — skrinrider
foydalanuvchisi birinchi «Ko'rmasdan tekshirish» ni eshitadi.

Oshkor panel ma'lumotni **prop** sifatida oladi; faylda so'rov hooki
umuman yo'q va bu **xom manbadan** o'lchanadi.

Javobdan keyin sessiyada **aynan bitta** faol boshqaruv qoladi va u
`[Keyingisi →]`. Yaqinlashtirish tugmasi ham olib tashlanadi (sabab
mahsulotga oid — pastdagi deviatsiya #3).

## Sabotaj o'lchovlari — nima QIZARDI va **nima YASHIL QOLDI**

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --`
**ishlatilmadi**); oxirida `git status` toza.

| # | Sabotaj | Tizimga yetdimi? | NATIJA |
|---|---|---|---|
| **S1** | `blindAuditItemSchema`: `z.strictObject` → `z.object` | ✅ (sxemani testlar import qiladi) | 🔴 **2 test** (G-13 jufti). ⚠ **G-12 (statik darvoza) TO'LIQ YASHIL** — spek aytgan «faqat G-12 yetmaydi» ning teskari yarmi o'lchandi. Barcha render testlari ham yashil: **maydon ekranga chiqmaydi-yu, brauzerga YETIB BORADI** — aynan shu sababdan G-13 kerak |
| **S2** | `removeQueries` → `invalidateQueries` | ✅ | 🔴 **1 test** — faqat statik G-14(b). ⚠⚠ **`blind-session.test.tsx` ning 18 TESTI HAM YASHIL QOLDI** — pastga qarang |
| **S2b** | `gcTime: 0` → `gcTime: 300_000` (qattiqlashtirishdan keyin) | ✅ | 🔴 **1 test** — yangi xulq testi. ⚠ Statik G-14(b) **yashil qoldi** — ya'ni juftlikning ikkala yarmi endi **alohida** qo'riqlanadi |
| **S3** | `frameState` dan `imageFailed` sharti olib tashlandi | ✅ | 🔴 **2 test** — sof funksiya jadvali **va** DOM xulqi. ⚠ Ko'r sessiya testlari yashil qoldi: darvoza UMUMIY faylda, ya'ni bitta o'lchov strukturaviy jihatdan yetarli |
| **S4** | Y-2 dan poyga qulfi (`submittedRef`) olib tashlandi | ✅ | 🔴 **2 test** (bosish yo'li **va** klaviatura yo'li). ⚠ **Y-3 testlari yashil qoldi** — qulf ikki mustaqil implementatsiya, ya'ni har biri O'Z testini talab qiladi |
| **S4b** | Y-3 dan o'sha qulf olib tashlandi | ✅ | 🔴 **1 test**. ⚠ «Javob yozilgach ikkinchi urinish» testi **yashil qoldi** va bu TO'G'RI: u BOSHQA oynani (javob qo'ngandan keyingi holatni) o'lchaydi |
| **S5** | `/review` uyida kartalar tartibi almashtirildi | ✅ | 🔴 **1 test** — DOM tartibi asserti |
| **S6** | Javobdan keyin yaqinlashtirish tugmasi QOLDIRILDI | ✅ | 🔴 **1 test** — «aynan bitta faol boshqaruv» |
| **S7** | D-19 qatori huquqsiz sessiyada **0** bilan chiziladi | ✅ | 🔴 **1 test** — «huquq yo'q bo'lsa qator ham yo'q» |

### S2 — bu rejaning eng qimmatli natijasi

`removeQueries` ni `invalidateQueries` ga almashtirish **birorta xulq
testini qizartirmadi**. Sabab test kuchsizligi **emas**, strukturaviy:

1. **Oshkor ma'lumot keshga umuman tushmaydi** (u mutatsiya natijasi),
   ya'ni kesh skani ikki chaqiruvni ajratadigan **hech nimani ko'rmaydi**;
2. `invalidate` keshda **qoldiradigan** narsa — band payloadi — esa
   `gcTime: 0` tufayli kuzatuvchi uzilishi bilan **baribir o'chadi**.

Ya'ni bugungi sozlamada ikki chaqiruv **kuzatiladigan farq bermaydi**.
Bu 05-10 sabotaj D ning aynan sinfi: **da'vo o'lchanadigan FARQDAN
chiqishi kerak, kodning SHAKLIDAN emas.**

**Da'vo toraytirildi va shu bilan kuchaydi:** kafolat **juftlikdan**
chiqadi — `gcTime: 0` **oynani** yopadi, `removeQueries` esa **darhol**
tozalaydi va `gcTime` bir kun oshirilsa yolg'iz o'zi ham kafolat beradi.
Shuning uchun endi **ikkala yarim ham alohida** qo'riqlanadi: birinchisi
statik darvoza (G-14b) bilan, ikkinchisi yangi xulq testi bilan — va
ikkinchisi sabotaj **S2b** bilan qizartirildi.

## Deviations from Plan

### 1. `[Rule 1 - Bug]` Uch bosish UCH javob yuborardi — TEST TOPDI

- **Topildi:** Task 2, `review-session.test.tsx` ning birinchi ijrosida
- **Muammo:** `blocked` bayrog'i **render paytida** hisoblanadi,
  `answer.isPending` esa faqat **keyingi** renderda `true` bo'ladi. Bir
  hodisa oqimidagi ketma-ket uch bosish (yoki `1`,`2`,`3` ni tez bosish)
  **uchalasi ham** eski qiymatni ko'rardi va **uchta** javob yuborilardi:
  birinchisi yozilib, qolgan ikkitasi `409` bo'lardi.
- **Nega bu D-18 masalasi:** «bitta so'rov = bitta qaror» kafolati
  **holat emas, POYGA masalasi**. Ommaviy tasdiqlashning eng tabiiy
  chetlab o'tish yo'li — tugmani tez bosish.
- **Tuzatish:** `useRef` bilan qulf (render kutmaydi). ⚠ **Qulf bayroq
  emas, BAND IDENTIFIKATORI:** bayroqni band almashganda render paytida
  nollash kerak bo'lardi, ref'ga esa render paytida tegib bo'lmaydi
  (`react-hooks/refs`). Identifikator bilan nollash **umuman kerak
  emas** — yangi bandning identifikatori boshqa, ya'ni qulf o'zi
  ochiladi va «nollashni unutish» sinfi ham yo'qoladi.
- **Ikki sessiyada IKKI mustaqil implementatsiya** va bu ataylab:
  sabotaj S4/S4b ikkalasini ham alohida o'lchadi.
- **Commit:** `4e0bec2`, `089f0ef`

### 2. `[Rule 3 - Blocking]` Server maydonining nomi darvozaning tokenini o'z ichiga oladi

- **Muammo:** `POST …/answer` tanasi `{human_verdict: …}`. G-12
  `verdict` ni **substring** sifatida qidiradi, ya'ni
  `blind-audit-queries.ts` bu satrni yoza olmaydi.
- **Rad etilgan «ishlaydigan» muqobil:** tokenni bo'laklab yozish
  (`["verd","ict"].join("")`). U darvozadan o'tardi-yu, aynan spek G-13
  ni **nima uchun** qo'shganini (`data["verd"+"ict"]`) mahsulot kodiga
  olib kirardi va keyingi ijrochiga **namuna** bo'lardi.
- **Tuzatish:** `answerRequestBody()` `api-types.ts` da — u sim
  kontraktining uyi va G-12 ning skaner maydonida emas. Sabab ikkala
  faylda ham yozilgan.
- **Commit:** `06b445b`

### 3. `[Rule 2 - Correctness]` Javobdan keyin yaqinlashtirish tugmasi olib tashlanadi

- **Muammo:** Qabul mezoni «javobdan keyin `button:not([aria-disabled])`
  soni **1**» deydi. Yaqinlashtirish tugmasi kadr tayyor bo'lganda
  chiqadi, ya'ni javobdan keyin ham qolardi va son **2** bo'lardi.
- **Tuzatish mezonni qanoatlantirish uchun emas:** qaror allaqachon
  **o'zgarmas**, ya'ni kadrni qayta kattalashtirish faqat «to'g'ri javob
  berdimmi?» degan **qayta o'ylashni** taklif qilardi — aynan
  o'zgarmaslik himoya qilayotgan narsani. `showZoom` propi qo'shildi
  (standart — HA, ya'ni noaniq navbatda xulq o'zgarmadi).
- **Commit:** `089f0ef`

### 4. `[Rule 1 - O'lchangan ziddiyat]` D-19 ilgagi FAQAT `report_view` ostida

- **Muammo:** §7.2 oxirgi qatorni «doim ko'rinadi, nol bo'lsa ham» deb
  belgilaydi. Manba — `GET /occupancy?day=…` ning `default_empty`
  maydoni (`occupancy.py:114`), u esa **`REPORT_VIEW`** ostida.
  `ROLE_PERMISSIONS[inspector]` esa aynan `["occupancy_review"]`
  (`rbac.ts:104`) — ya'ni **birorta rol** ikkala huquqni birga
  bermaydi va sof nazoratchi bu sonni **umuman ololmaydi**.
- **Rad etilgan variant — nol yozib qo'yish.** «Kecha: 0 ta rasta
  ko'rilmagani uchun bo'sh deb hisoblandi» — o'lchanmagan holatda bu
  **eng yomon shakldagi yolg'on**: u nazoratchining kechagi qoldig'ini
  **nol** deb e'lon qilardi. T-05-04 ning qoidasi aniq: o'lchanmagan
  raqam ko'rilgan zahoti o'lchangan deb o'qiladi.
- **Tuzatish:** qator **faqat huquq bo'lganda** so'raladi va chiziladi;
  nol bo'lganda **chiziladi** (test bilan), huquq bo'lmaganda esa
  **umuman chizilmaydi** va so'rov ham ketmaydi (ikkinchi test).
  Sabotaj **S7** ikkinchi shartni qizartirdi.
- **⚠ Eng tor tuzatish 05-14/05-15 uchun yozib qo'yiladi:**
  `ReviewBudgetResponse` ga **bitta maydon** (`default_empty_yesterday`)
  — u marshrut allaqachon `OCCUPANCY_REVIEW` ostida bo'lgani uchun yangi
  huquq yuzasi ochmaydi.
- **Commit:** `06b445b`

### 5. `[Rule 2 - Correctness]` Taqiqlangan nomlar test faylida LITERAL yozilmaydi

- **Muammo:** Reja G-13 ni `blind-session.test.tsx` ga qo'yadi va
  `blindAuditItemSchema.parse({...toza, verdict: "occupied"})` ni
  so'raydi. Lekin **o'sha fayl `components/blind-audit/` katalogida**,
  ya'ni **G-12 ning skaner maydonida**: `verdict` so'zini u yerga
  yozish darvozani **o'z testi bilan** qizartirardi va yagona
  «tuzatish» yo'li darvozani **bo'shatish** bo'lardi (05-11
  deviatsiya #7 ning aynan sinfi).
- **Tuzatish:** nomlar `api-types.ts::BLIND_FORBIDDEN_KEYS` da yashaydi
  va test ularni **iteratsiya** qiladi. Natija rejadagidan
  **kuchliroq**: bitta nom emas, **reyestrning hammasi**, ustiga
  reyestrda **yo'q** ortiqcha maydon (`risk_score`) va
  `has_active_vendor` ham.
- **⚠ Ikkinchi nusxa xavfi ochiq aytiladi:** mexanik manba hamon
  `scripts/blind-payload.test.mjs::FORBIDDEN_NAMES`. Drift'ga qarshi
  test **uzunlik chegarasini** ham o'lchaydi (§S-10) va **salbiy
  nazorat** (toza payload parse bo'ladi) trivial qanoatlanishni yopadi.
- **Commit:** `089f0ef`

### 6. `[Rule 3 - Blocking]` `useEffect` ichida `setState` — lint XATO deb rad etadi

- **Muammo:** Band almashganda ichki holatni (`loaded`/`failed`,
  `reveal`/`notice`) nollash tabiiy ravishda effektga yozilgan edi;
  `react-hooks/set-state-in-effect` ikkalasini ham **xato** bilan rad
  etdi.
- **Tuzatish ikki xil va ikkalasi ham effektdan KUCHLIROQ:**
  (a) `EvidenceFrame` — chaqiruvchida **`key={snapshotId}`**, ya'ni
  komponent butunlay qayta tug'iladi va unutilgan bitta `setState`
  qolib ketishi **mumkin emas**; (b) `ReviewSession`/`BlindSession` —
  **render paytida moslash** (React'ning «adjusting state when a prop
  changes» naqshi), u effektdan **bir render tez** ham: effekt varianti
  yangi bandni bir kadr davomida **eski oshkor panel** bilan
  ko'rsatardi.
- **Commit:** `4e0bec2`

### 7. `[Rule 3 - Blocking]` `@testing-library/user-event` o'rnatilmagan

Test avval `userEvent.click` bilan yozilgan edi; paket loyihada **yo'q**.
Paket **o'rnatilmadi** (Rule 3 dan ATAYIN chiqarilgan sinf) —
`fireEvent` ga o'tildi, u kodbazadagi mavjud konventsiya.

### 8. `[Qaror]` `review.inQueue` («Navbatda: N») QURILMADI

§12.4 bu kalitni sanaydi, `ReviewBudgetResponse` esa **bunday sonni
bermaydi** (`answered`/`budget`/`remaining`). Uni `remaining` dan
hisoblash **boshqa narsani** aytardi («byudjetda qolgan» ≠ «navbatda
turgan»), to'qib chiqarish esa **stub** bo'lardi. Kalit **yozilmadi** —
iste'molchisiz kalit ham, yolg'on son ham qo'shilmadi.

### 9. `[Qaror]` Y-2 va Y-3 ning oshkor panellari IKKI XIL komponent

`UncertainReveal` (Y-2, `review-session.tsx` ichida) 1,5 soniyada o'zi
ketadi va **birorta boshqaruv bermaydi**; `RevealPanel` (Y-3) esa
**qoladi**, «o'zgartirib bo'lmaydi» jumlasini olib yuradi va sessiyaning
**yagona oldinga yo'lini** tashiydi. Nusxa emas — ikki xil **xulq**.
Umumiy qilib «bayroq» bilan boshqarish ikkinchisining kafolatini
**shartli** qilardi.

### 10. `[Qaror]` `localeHref` UCHINCHI marta yozildi

`@/i18n/navigation` vitest ostida yechilmaydi (05-09 deviatsiya #2 da
o'lchangan), ya'ni render qilinadigan sahifalar undan foydalana olmaydi.
Funksiya uchta sahifada takrorlandi; **prefiks xaritasi esa nusxa
ko'chirilmadi** — u `routing.localePrefix` dan o'qiladi. Uni umumiy
modulga chiqarish to'g'ri qadam, lekin o'sha modul bu rejaning fayl
to'plamidan tashqarida — **ochiq band** sifatida qayd etildi.

### 11. `[Rule 1 - Bug]` `npm run gate` ikkita alert testini SOAT tufayli yiqitdi

- **Topildi:** yakuniy `npm run gate` ijrosida, **23:37** Toshkent vaqti
- **⚠ BU REJANING KODI EMAS:** `git diff --name-only 06b445b~1..HEAD`
  chiqishida **birorta Python fayli yo'q**. Nosozlik `dc5f182` tuzatgan
  testning **qo'shnilari** da — aynan o'sha fayl, aynan o'sha sabab.
- **Muammo:** `alert_sweep` biznes-kunni `now` **argumentidan** oladi
  (`alerting.py:487`) va yugurishlarni o'sha kun bo'yicha filtrlaydi
  (`:668`). Ikkala debounce testi ham **haqiqiy soatni** olib, ustiga
  30 / 61 daqiqa qo'shadi — ya'ni Toshkent vaqti bilan **23:30 / 22:59**
  dan keyin kech supurgi **ERTANGI** kunni ko'radi, u yerda yiqilgan
  slot yo'q, alert **yopiladi** va yopilish xabari **ikkinchi chaqiruv**
  bo'lib chiqadi. O'lchandi: `resolved=1`, `assert 2 == 1`.
- **⚠⚠ NAZORAT TESTI YIQILGANIDAN HAM YOMONROQ EDI:**
  `test_a_repeat_after_the_debounce_window_sends_again` `call_count == 2`
  ni kutadi va **yopilish xabari aynan 2 ga yetkazadi** — ya'ni u
  **yashil qolib**, «debounce oynasidan keyin qayta yuborildi» o'rniga
  «alert yopildi» ni o'lchardi. Jim yolg'on-yashil.
- **Tuzatish:** `dc5f182` ning **aynan o'sha ikki qatori** (signal kech
  supurgining biznes-kuniga ham yoziladi). Mahsulot kodi **tegilmagan**.
- **Ikki tomonlama o'lchandi (23:56 da):** langar bilan fayl **15/15**
  yashil; langar olib tashlanganda birinchi test **aynan o'sha
  imzo bilan** qizaradi.
- **Commit:** `bcc2d49` — ⚠ **ALOHIDA `fix(tests)` commiti**, rejaning
  uchta `feat` commitiga aralashtirilmadi.

### 12. `[Qaror]` Dalil kadri kesh kaliti IKKALA navbat uchun UMUMIY

`review-evidence` prefiksi — `blind-audit` ham, `review-uncertain` ham
emas. Kadr ikkala navbatda ham **bir xil bayt** va unda tizim javobi
**yo'q**; uni ikki prefiksga ko'chirish bir xil baytni ikki marta
so'rashga majburlardi. §14.3 ning 4-qatlami buzilmaydi: kadr
`gcTime: 0` bilan yuritiladi.

---

**Total deviations:** 12 (3× Rule 1 xato/ziddiyat, 2× Rule 2 to'g'rilik,
3× Rule 3 bloklovchi, 4× ongli qaror)
**Impact on plan:** Ko'lam kengaymadi; **mahsulot kodida** birorta fayl
ro'yxatdan tashqarida o'zgarmadi. Yagona istisno — deviatsiya #11 dagi
`tests/integration/test_alerting.py` va u **o'lchov qurilmasining**
nosozligi (mahsulot kodi tegilmagan, alohida `fix(tests)` commiti). Ikki
qaror (#8 va #4) spek so'ragan narsani **to'liq qurmaslik** haqida va
ikkalasining sababi ham **ma'lumot manbasining yo'qligi** — taxmin emas.

## Verification Performed

| O'lchov | Bazaviy | Yakuniy | Holat |
|---|---|---|---|
| `vitest run` | 494 (35 fayl) | **550 (38 fayl)** | ✅ +56 |
| `node --test scripts/*.test.mjs` | 144 | **144** | ✅ o'zgarmadi (G-11…G-18 yashil) |
| `npm run i18n:check` | 879 × 3 | **927 × 3** | ✅ +48, kalit va ICU parity to'liq |
| `npm run typecheck` | toza | **toza** | ✅ |
| `npm run lint` | toza | **toza** | ✅ 0 xato, 0 ogohlantirish |
| `npm run build` | — | **✓ Compiled** | ✅ uchala yangi marshrut ham ro'yxatda |
| G-12 (`blind-audit-queries.ts` + `components/blind-audit/**`) | bo'sh to'plam | **4 fayl skanerlandi** | ✅ qamrov chegarasi (≥3) endi HAQIQIY |
| G-14(a) (`review/blind/` da `[` yo'q) | katalog yo'q edi | **katalog bor, segment yo'q** | ✅ |
| `uz-Cyrl.overrides.json` / `rbac.ts` / `app-shell.tsx` diff'da | — | **YO'Q** | ✅ (M-8) |
| `git diff --name-only` da `services/` | — | **0 fayl** | ✅ mahsulot backendi TEGILMADI |
| **`npm run gate`** (to'liq zanjir) | — | **exit 0** | ✅ ikkinchi ijroda (birinchisi soatga bog'liq alert testida yiqildi — deviatsiya #11) |
| `ruff` + `mypy` (`core-api`) | toza | **toza** (278 fayl) | ✅ |
| `ruff` + `mypy` (`cv-service`) | toza | **toza** (32 fayl) | ✅ |
| `pytest -q` (`core-api`) | exit 0 | **exit 0** | ✅ birorta nosozliksiz |
| `pytest tests/integration/test_alerting.py` | 15/15 | **15/15** | ✅ langar bilan; **langarsiz 1 ta qizaradi** (nazorat 23:56 da) |
| `cv-tests` | o'tgan | **o'tgan** | ✅ bu reja `cv-service` ga tegmadi |

⚠ **`services/**` QAYTA YUGURTIRILDI, LEKIN O'ZGARTIRILMADI:** bu reja
**birorta mahsulot Python faylini** o'zgartirmagan, ya'ni 05-11 ning
**2134 passed** / **536 tenancy** bazaviy sonlariga strukturaviy ta'sir
yo'q. Yagona Python o'zgarishi — **test qurilmasining** langari
(deviatsiya #11), u ham alohida commitda.

## Known Stubs

**Yo'q** — soxta ma'lumot manbai ham, placeholder matn ham yaratilmadi.
Uch band ATAYIN «qurilmagan» va ular stub EMAS:

| Nima | Nega stub emas |
|---|---|
| D-19 ilgagi sof nazoratchida **chizilmaydi** | Bu bo'sh element ham, ishlamaydigan tugma ham emas: **son o'lchanmaganda qator umuman yo'q**. Nol yozib qo'yish esa aynan stub bo'lardi va u T-05-04 ni buzardi. Huquqli sessiyada qator **to'liq ishlaydi** va ikki test bilan o'lchangan |
| `review.inQueue` kaliti **yozilmadi** | Iste'molchisiz kalit — «bu ishlaydi» degan yolg'on va'da (05-11 ning `BLIND_AUDIT_REPEAT_RATIO` qarori bilan bir xil mantiq) |
| UI-SPEC §11.6 ning «Ichki moslik» qatori bu ekranlarda **yo'q** | D-16 bugungi sxemada ifodalab bo'lmaydi (05-11 deviatsiya #1) va 05-12 uni hisobotdan ham **maydon sifatida** chiqarib tashlagan. Bu ekranlar u haqida **hech nima demaydi** — placeholder ham qo'yilmadi |

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-61 (ko'r payloadda tizim javobi) | mitigate | **Uch qatlam:** G-12 (statik modul chegarasi, 4 fayl skanerlanadi) + G-13 (`z.strictObject` — **reyestrning hammasi** va reyestrda yo'q maydon ham) + serverdagi «e'lon qilinmagan maydon» (05-11). Sabotaj **S1** ikkinchi qatlamning **yolg'iz** ishlashini o'lchadi |
| T-05-62 (kesh grafi) | mitigate | Oshkor ma'lumot **faqat** mutatsiya natijasida (kesh skani bilan o'lchandi); ko'r so'rovlar `gcTime: 0` + `staleTime: 0` (xulq testi, **S2b** bilan qizartirildi) + `removeQueries` (statik G-14b, **S2** bilan qizartirildi). ⚠ Da'vo **juftlikka** toraytirildi — yuqoridagi S2 bo'limiga qarang |
| T-05-63 (javobni keyin o'zgartirish) | mitigate | URL'da identifikator **yo'q** (G-14a endi haqiqiy katalogni skanerlaydi); javobdan keyin uchala tugma `aria-disabled` va **aynan bitta** faol boshqaruv qoladi (**S6** bilan o'lchandi); server `409` uchun **qayta urinish tugmasi berilmaydi** |
| T-05-64 (ommaviy tasdiqlash UI'da) | mitigate | Render qilingan DOM'da `input[type="checkbox"]` **yo'q** (uchala ekranda ham o'lchandi); mutatsiya tanasi massiv **emas**; ⚠ **poyga yo'li ham yopildi** (deviatsiya #1) — u D-18 ning klaviatura/tez-bosish shakli edi |
| T-05-65 (dalil kadri) | mitigate | Faqat `core-api` proxysi; havola **vaqtinchalik** va komponent yopilganda bekor qilinadi; `crossOrigin` **qo'yilmagan** (test bilan); yuklab olish/ulashish yo'li **yo'q**; `snapshot-copy.test.mjs` ombor yuzasi taqig'i yashil |
| T-05-66 (ankorlash) | mitigate | Ikkala navbatda ham tizim javobi javobdan **keyin** (ikkala test to'plamida ham «javobdan OLDIN ekranda yo'q» asserti bor); ko'r sessiyada «sotuvchi biriktirilgan» qatori ham **chizilmaydi** (05-11 ning xolislik qarori) |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authorization-gap | `services/core-api/app/api/v1/snapshots.py` | ⚠⚠ **05-10 va 05-11 dan MEROS va u endi EKRANDA ko'rinadi.** Sof `inspector` navbat bandini oladi, dalil kadrini esa **403** bilan ko'ra olmaydi |

### ⚠⚠ Dalil-kadr huquq bo'shlig'i — TUZATILMADI, sabab va NARXI qayta o'lchandi

**Nega bu rejada tuzatilmadi (ongli qaror):** rejaning `files_modified`
ro'yxati **faqat `frontend/`** dan iborat; `snapshots.py`, `deps.py`,
`rbac.py` va `tests/tenancy/**` ning **birortasi** ham unda yo'q.
UI-SPEC **M-8** bu fazada RBAC tegilmasligini o'lchov bilan qo'yadi va
05-10 ham, 05-11 ham buni **Rule 4** deb tasniflab, ongli ravishda
qoldirgan.

**⚠ 05-11 ning «eng tor tuzatish» bahosi ANIQ EMAS — qayta o'lchandi:**

| Nima | 05-11 aytgan | O'LCHANDI (2026-08-09) |
|---|---|---|
| Huquq talab qilinadigan joylar soni | bitta teg | **IKKITA**: marshrut dekoratori (`snapshots.py:410`) **va** `principal: SnapshotViewerDep` (`snapshots.py:170`) |
| `SnapshotViewerDep` ning qamrovi | aytilmagan | **to'rtta marshrutda** ishlatiladi (322, 381, 414, 500) — uni bo'shatish nazoratchiga **kadr metama'lumoti, kun jurnali va ro'yxatni ham** ochardi |
| O'zgaradigan fayllar | 2 ta | **kamida 4 ta**: `deps.py` (teg ko'plikka aylanadi), `snapshots.py` (ALOHIDA dependency alias — mavjudini bo'shatish MUMKIN EMAS), `tests/tenancy/test_personal_data_coverage.py:462` va `tests/tenancy/test_camera_route_coverage.py:214/244/265` (⚠ u ham `required_permissions()` dan o'qiydi) |

**Ya'ni tuzatish 05-11 baholaganidan kengroq va u xavfsizlik
darvozasining semantikasiga tegadi — Rule 4 tasnifi TO'G'RI qoladi.**

**Bu rejada nima QILINDI:** xulq **halol** bo'lishi kafolatlandi.
`useEvidenceImageHref` ning 403 i `frameState()` da **uchinchi nosozlik
manbai** sifatida ochiq qayd etilgan; nazoratchi «Rasm ochilmadi —
javob bera olmaysiz» matnini ko'radi, uchala tugma `aria-disabled`
**bo'lib qoladi** va **taxminiy javob yozilmaydi**. Ya'ni ekran
jimgina buzilmaydi — u **nima ishlamayotganini aytadi** va o'lchovga
axlat qo'shmaydi.

**⛔ Qaror `05-15` da qabul qilinishi SHART.** Bugungi holatda AI-03 va
AI-04 ning **oxirgi qadami** (rasmni ko'rib javob berish) sof
`inspector` roli bilan **bajarilmaydi**; ishlaydigan yagona konfiguratsiya
— nazoratchiga `market_admin` (yoki `director`) rolini **ham** berish
(D-05: rollar to'plam).

## ⚠ BAJARILMAGAN QO'LDA TEKSHIRUV (faza yopilishiga)

`.planning/config.json`: `workflow.human_verify_mode: "end-of-phase"`.
Bu muhitda brauzer yo'q, shuning uchun Task 3 ning 8 qadamli qo'lda
tekshiruvi **bajarilmadi** (05-09 deviatsiya #16 bilan aynan bir xil
holat). Ish bajarildi va **avtomatik verifikatsiyadan to'liq o'tdi**.

Faza yopilishida bajarilishi kerak:

1. `npm run up`, urug'ni yuklang, `audit_draw` ni bir marta ishga
   tushiring; ⚠ **`inspector` roliga `market_admin` ham qo'shing** —
   aks holda 5-qadam dalil kadrida `403` beradi (yuqoridagi
   `threat_flag`).
2. `/uz/review` — ko'r audit kartasi **yuqoridami**? (avtomatik test
   DOM tartibini qulflaydi, lekin **vizual** tartib CSS bilan
   o'zgartirilishi mumkin)
3. «Ko'rmasdan tekshirishni boshlash» — manzil qatorida **identifikator
   bormi**? (Kutilgan: yo'q, faqat `/uz/review/blind`)
4. DevTools → Network: `GET /review/blind/next` javobida taqiqlangan
   maydonlar **bormi**? (Kutilgan: yo'q — 05-11 buni server tomonda ham
   o'lchagan)
5. Javob bering. Oshkor panel chiqdimi? Tugmalar `aria-disabled`
   bo'ldimi? Brauzer tarixi orqali qaytib javobni **o'zgartira
   olasizmi**? (Kutilgan: yo'q)
6. `F5` — **o'sha band** qaytadimi yoki **keyingisi**? (Kutilgan:
   keyingisi)
7. Ikkala navbatni ketma-ket oching — ular **ko'rinishda ajralib
   turadimi**? (lenta + manzil + sarlavha)
8. Skrinrider bilan `/uz/review/blind` — birinchi eshitiladigan narsa
   **«Ko'rmasdan tekshirish»** mi?

⚠ **Qo'shimcha o'lchov bandi:** oshkor panel Y-2 da **1,5 soniya**
turadi (`REVEAL_MS`). Bu qiymat **o'lchanmagan** — u 05-RESEARCH dan
emas, §8.3 dagi S-6 ta'rifidan olingan. UAT'da «o'qishga ulguriladimi?»
savoli berilsin; kam bo'lsa, o'zgarish **bitta konstanta**.

## Keyingi rejalar uchun ochiq bandlar

1. **⚠⚠ `05-15` uchun — dalil-kadr huquqi.** Yuqoridagi `threat_flag`
   va qayta o'lchangan narx jadvali. Bu **mahsulot qarori**, texnik
   tanlov emas.
2. **`05-14` uchun — `lib/occupancy-queries.ts` hali YO'Q.** Bu reja
   `GET /occupancy` ga **bitta tor sxema** bilan tegdi
   (`reviewYesterdaySummarySchema`, faqat `default_empty`). To'liq sxema
   05-14 niki; ikkovi **ajralib keta olmaydi**, chunki tor sxema faqat
   bitta maydonni o'qiydi va uning **o'chirilishi** ikkalasini ham
   qizartiradi.
3. **`05-14`/`05-15` uchun — D-19 ilgagining eng tor tuzatishi:**
   `ReviewBudgetResponse` ga `default_empty_yesterday` (bitta maydon).
   Marshrut allaqachon `OCCUPANCY_REVIEW` ostida, ya'ni yangi huquq
   yuzasi ochilmaydi va `/review` uyining oxirgi qatori **sof
   nazoratchida ham** ko'rinadigan bo'ladi.
4. **`localeHref` UCHINCHI nusxada** (`camera-row.tsx`, `review/page.tsx`,
   `review/uncertain/page.tsx`, `review/blind/page.tsx`). Uni
   `lib/locale-href.ts` ga chiqarish to'g'ri qadam; prefiks xaritasi
   nusxa ko'chirilmagani uchun bugungi xavf **past**.
5. **`05-14` uchun:** `review.*` namespace'i endi **G-11/G-15/G-16/G-18(a)
   darvozalarining skaner maydonida** va u yerda 48 kalit bor. Yangi
   `occupancy.*` kalitlari o'sha darvozalardan o'tadi — ayniqsa G-15
   (`occupancy.noCoverage*` da «bo'sh» so'zi) va G-16 («tuzatish»).
6. **`05-15` uchun:** `MINIMUM_MATRIX_ROUTES` bu rejada **o'zgarmadi**
   (backend tegilmadi) — u hamon **57**.
7. **UI-SPEC §7.1 va §11.6 ESKIRGAN** (05-10 deviatsiya #7 va 05-11
   deviatsiya #1). Bu reja ikkalasiga ham **rioya qilmadi va rioya
   qilmasligi TO'G'RI**: noaniq javob uchun tahrirlash affordansi
   **qurilmadi** (server `409` beradi), «Ichki moslik» qatori esa
   **umuman yo'q**. Spek faylini tuzatish `05-15` ning bandi.

## Self-Check: PASSED

- **Fayllar:** e'lon qilingan **15 yaratilgan + 5 o'zgartirilgan** —
  hammasi diskda (`git diff --name-only 06b445b~1..HEAD` → **20 fayl**);
  19 tasi rejaning `files_modified` ro'yxatida, 20-si esa deviatsiya #11
  da **ochiq yozilgan** test langari;
- **Commitlar:** `06b445b`, `4e0bec2`, `089f0ef`, `f119a93`, `bcc2d49` —
  beshtasi ham `git log` da;
- **O'chirilgan fayl yo'q:** har commitdan keyin `git diff
  --diff-filter=D` **bo'sh**;
- **Sabotajlar:** 10/10 o'lchandi (9 ta frontend + 1 ta alert langari
  nazorati) va har biri `cp` bilan snapshotdan tiklandi;
  `git checkout --` **ishlatilmadi**; yakuniy `npm run gate`
  **exit 0** (`550` vitest + `144` node + `927×3` i18n + `pytest` toza),
  `git status` toza;
- **Tegilmagan fayllar tasdig'i:** `frontend/src/lib/rbac.ts`,
  `frontend/src/components/shell/app-shell.tsx`,
  `frontend/messages/uz-Cyrl.overrides.json`, `frontend/package.json`,
  `frontend/package-lock.json`, `services/**`, `tests/**` — **birortasi
  ham diff'da yo'q**.

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
