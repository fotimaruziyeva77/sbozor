---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 14
subsystem: frontend
tags: [react-query, zod-strict, a11y, i18n, wilson, confusion-matrix, rbac, ai-04, ai-05, ai-06]

# Dependency graph
requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 12
    provides: "`GET /occupancy` (BESH hisoblagich + `stalls` guvohi + rastalar ro'yxati), `GET /occupancy/accuracy` (matritsa, `measured`, `min_sample`, `base_rate`, uch Wilson oralig'i), `GET /occupancy/round` (`drawn=false` da qolgan maydonlar `null`); ⚠ D-16 ning javobda NA SON, NA MAYDON sifatida YO'QLIGI"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 13
    provides: "`localeHref` naqshi, `reviewYesterdaySummarySchema` (TOR egizak), so'rov modulining shakli, `z.strictObject` ning o'lchangan foydasi (S1) va «da'vo o'lchanadigan FARQDAN chiqadi» darsi (S2)"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 11
    provides: "D-16 ning O'LCHANGAN ziddiyati — takroriy band bugungi sxemada IFODALAB BO'LMAYDI"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    plan: 03
    provides: "`lib/wilson.ts` — `MIN_SAMPLE_FOR_PERCENT` va uning serverdagi jufti bilan matn darajasidagi qulfi"
  - phase: 04-snapshot-pipeline
    provides: "`day-picker.tsx` (`useDaySelection`, `businessDayIn`, `shiftIsoDay`), `day-summary.tsx` ning hisoblagichli `<dl>` shabloni, `capturePollInterval` ning sof-funksiyali poll naqshi"
provides:
  - "`lib/occupancy-queries.ts` — `occupancyDayKey`/`accuracyKey`/`roundKey`, `useOccupancyDay`/`useAccuracyReport`/`useAuditRound`, `occupancyPollInterval` (SOF funksiya); MUTATSIYA YO'Q"
  - "`api-types.ts`: `occupancyDaySchema` (`z.object`), ⛔ `accuracyReportSchema` va `auditRoundSchema` (`z.strictObject`), `occupancyStallItemSchema`, `OCCUPANCY_STATUSES`"
  - "`/occupancy` — `report_view` yuzasi; O-1…O-5, `stalls === 0` da E-6"
  - "`components/occupancy/`: `day-breakdown.tsx` (+ `OCCUPANCY_COUNTERS`), `confusion-matrix.tsx` (+ `percentView()`), `round-summary.tsx` (+ `roundCounters()`), `stall-day-list.tsx` (+ `visibleStalls()`, `useNoCoverageOnly`, `StallStatusBadge`), `stall-detail-dialog.tsx` (+ `stallSource()`)"
  - "`DayPicker` ning YAGONA parametri: `noFutureDaysKey` — xulq emas, SABAB"
  - "`occupancy.*` — 39 yangi kalit uchala tilda (927 -> 980)"
affects: [05-15-faza-darvozasi, 06-billing, 08-hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FOIZ KLIENTDA HISOBLANMAYDI: maxrajlar 05-12 da SPETSIFIKATSIYADAN o'lchab olingan va klientdagi qayta hisob XATO bo'lib emas, IKKINCHI JAVOB bo'lib chiqardi (5,4 % -> 3,8 %) — shu sababdan `confusion-matrix.tsx` da birorta bo'lish amali yo'q"
    - "«O'LCHANMAGAN -> QATOR YO'Q, NOL -> QATOR BOR» MEXANIK QOIDAGA AYLANDI: `roundCounters()` `null` maydonni tashlaydi, `0` ni saqlaydi — D-16 ning printsipi endi bitta sof funksiyada yashaydi"
    - "MAVJUD BO'LMAGAN NARSANI «SO'Z YO'Q» BILAN O'LCHASH TAQIQ: D-16 qatorining yo'qligi `<dt>` yorliqlari TO'PLAMINI literal qulflash bilan o'lchanadi — «falon so'z topilmadi» asserti sabotaj ostida ham yashil qolardi"
    - "SERVER QARORINI KLIENTDA TAKRORLAMASLIK IKKI MAYDON BILAN QULFLANADI: `measured` (foiz chizilsinmi?) va `min_sample` (chegara) — ikkalasi ham javobdan olinadi va `min_sample = 25` fixture'i klientdagi qotirilgan 20 ni fosh qiladi"
    - "KLIENT BILMAYDIGAN KONSTANTA MATNDA NOMLANMAYDI: «tez qaror» chegarasi (2000 ms) javobda yo'q, shuning uchun yorliq sonni emas MA'NONI aytadi — nomlash server konstantasining ikkinchi nusxasi bo'lardi"
    - "SPEK SO'RAGAN YUZA MA'LUMOT MANBASISIZ QURILMAYDI: DL-5 ning slot qatorlari uchun marshrut YO'Q va ularni to'qib chiqarish ham, «tez orada» jadvali ham RAD ETILDI"

key-files:
  created:
    - frontend/src/lib/occupancy-queries.ts
    - frontend/src/lib/occupancy-queries.test.tsx
    - frontend/src/app/[locale]/(app)/occupancy/page.tsx
    - frontend/src/components/occupancy/day-breakdown.tsx
    - frontend/src/components/occupancy/day-breakdown.test.tsx
    - frontend/src/components/occupancy/confusion-matrix.tsx
    - frontend/src/components/occupancy/confusion-matrix.test.tsx
    - frontend/src/components/occupancy/round-summary.tsx
    - frontend/src/components/occupancy/round-summary.test.tsx
    - frontend/src/components/occupancy/stall-day-list.tsx
    - frontend/src/components/occupancy/stall-day-list.test.tsx
    - frontend/src/components/occupancy/stall-detail-dialog.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/components/snapshots/day-picker.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
  deleted: []

key-decisions:
  - "⚠⚠ `lib/wilson.ts` `confusion-matrix.tsx` GA IMPORT QILINMADI — reja `key_links` da uni AYNAN talab qiladi. Sabab o'lchangan: uch nisbat ham, uch oraliq ham, `min_sample` ham SERVERDAN keladi (05-12 ning 2-ochiq bandi klientga konstantani YOZMASLIKNI aniq aytadi), ya'ni import qilingan formula ikkinchi javob tug'dirardi"
  - "⚠⚠ UI-SPEC §11.6 ning «Ichki moslik» qatori CHIZILMADI — reja Task 2 da uni ochiq so'raydi. 05-11 mexanizm bugungi sxemada IFODALAB BO'LMASLIGINI o'lchagan, 05-12 maydonni javobdan chiqargan; `occupancy.selfConsistency*` KALITLARI HAM yozilmadi (iste'molchisiz kalit keyingi ijrochini uni chizishga undardi)"
  - "`accuracyReportSchema` va `auditRoundSchema` — `z.strictObject`: server bir kun `self_consistency` qaytarsa, klient BALAND ovozda yiqiladi. `z.object` uni jimgina brauzerga o'tkazardi va render testlarining BIRORTASI qizarmasdi (sabotaj S10 buni o'lchadi)"
  - "Foiz `measured` bo'yicha chiziladi, `n >= min_sample` bo'yicha EMAS: ikkinchi shakl bugun bir xil natija berardi va chegara o'zgargan kuni jimgina ajralib ketardi"
  - "«Tez qaror» chegarasi (2 soniya) MATNDA NOMLANMAYDI — u javobda yo'q; §12.6 ning `{seconds}` argumenti tushirildi va eng tor tuzatish `deferred-items.md` ga yozildi"
  - "DL-5 SLOT QATORLARISIZ qurildi: `OccupancyStallItem` da slot vaqti ham, kamera ham, `snapshot_id` ham YO'Q. To'qib chiqarish (stub) va bo'sh jadval (placeholder) rad etildi — dialog FAQAT o'lchanganini ko'rsatadi"
  - "`stallSource()` `no_coverage` uchun `null` qaytaradi: «Tizim» bo'lmagan javobni bor qilardi, «Ko'rilmadi» esa D-22 ni D-19 ga aralashtirardi"
  - "`DayPicker` ikkinchi nusxa qilib yozilmadi — unga BITTA parametr (`noFutureDaysKey`) qo'shildi. Nusxa `max` atributi yoki normallashtirish qoidasi bo'yicha ajralib ketardi va bittasida kelajakdagi kun TANLANADIGAN bo'lib qolardi"
  - "Aniqlik bloki POLL QILINMAYDI (kunlik so'rov qilinadi): (B) zonasi kunlik emas, oyning to'plangan namunasi (§11.1)"

patterns-established:
  - "MAVJUD BO'LMAGAN QATORNI TO'PLAM BILAN QO'RIQLASH: «yo'q» degan da'vo faqat BOR narsalarning to'liq ro'yxatini qulflash orqali o'lchanadi — aks holda assert sabotaj ostida ham yashil qoladi"
  - "SOF FUNKSIYA DOM DAN KO'RADIGANNI KO'RADI: `?? 0` sabotaji `roundCounters` testlarini qizartirdi, «tortilmagan turda qator yo'q» DOM testi esa YASHIL qoldi (komponent `drawn` bo'yicha oldin shoxlanadi)"
  - "SXEMA DARVOZASI RENDER TESTLARIDAN MUSTAQIL: `strictObject` -> `object` sabotaji 57 komponent testining BIRORTASINI qizartirmadi — maydon ekranga chiqmaydi-yu, brauzerga YETIB BORADI"

requirements-completed: []
requirements-advanced: [AI-04, AI-05, AI-06]
# ⚠ ATAYIN BO'SH — 05-09/05-10/05-11/05-12/05-13 dagi bilan AYNAN bir xil
# qaror. Bu reja uchala talabning ham YUZASINI yetkazadi (bandlik
# xulosasi, chalkashlik matritsasi, namuna holati, rastalar ro'yxati),
# lekin ularni YOPMAYDI: (a) 8 qadamli qo'lda tekshiruv bu muhitda
# BAJARILMADI (`human_verify_mode: "end-of-phase"`); (b) DL-5 ning slot
# qatorlari ma'lumot manbasisiz qoldi (`deferred-items.md` 3-band);
# (c) sof `inspector` dalil kadrini hali ko'ra olmaydi (05-13 ning
# `threat_flag` i). `05-15` fazani DALIL bilan yopadi.

# Metrics
metrics:
  duration_minutes: 150
  completed: 2026-08-10
  tasks_completed: 3
  files_created: 12
  files_modified: 5
---

# Phase 5 Plan 14: Bandlik va aniqlik hisoboti — foiz SERVERDAN keladi, o'lchanmagan qator esa TUG'ILA OLMAYDI — Summary

**Direktor endi kunlik bandlikni besh qo'shilmaydigan hisoblagichda va aniqlikni chalkashlik matritsasi + bazaviy ulush + uch Wilson oralig'i bilan ko'radi; barcha foizlar SERVER hisoblagan holda chiziladi (klientda birorta bo'lish amali yo'q), `measured` va `min_sample` ham serverniki, D-16 esa na qator, na «—», na nol sifatida mavjud emas — va uning yo'qligi «so'z topilmadi» bilan emas, `<dt>` yorliqlari TO'PLAMINI literal qulflash bilan o'lchanadi.**

## Performance

- **Duration:** ~150 daqiqa
- **Tasks:** 3/3
- **Files:** 12 yaratildi, 5 o'zgartirildi — **mahsulot kodida rejaning `files_modified` ro'yxatidan tashqarida bitta fayl**: `components/snapshots/day-picker.tsx` (deviatsiya #1, bitta ixtiyoriy parametr)
- **Sabotajlar:** 13 ta, hammasi o'lchandi va `cp` bilan tiklandi

## Task Commits

1. **Task 1 — so'rovlar, sahifa qobig'i, besh hisoblagich** — `05229e8` (feat)
2. **Task 2 — chalkashlik matritsasi va namuna holati** — `6c7bfc0` (feat)
3. **Task 3 — rastalar ro'yxati, DL-5 va matn** — `509a43e` (feat)

## Bajarilgan ishlar

### Task 1 — Besh hisoblagich va NOMUVOFIQLIK DARVOZASI

| Element | Holat |
|---|---|
| `occupancy-queries.ts` | ✅ uchta doiralangan kalit; poll SOF funksiyada; **mutatsiya YO'Q** |
| Poll | ✅ `day === bugun ? 60_000 : false`; `refetchIntervalInBackground: false` |
| `occupancyDaySchema` | ✅ `z.object` — TOR egizagi (`reviewYesterdaySummarySchema`) bilan ajralib keta olmaydi |
| `accuracyReportSchema` / `auditRoundSchema` | ✅ **`z.strictObject`** |
| `/occupancy` | ✅ `report_view` ko'zgusi; O-1/O-2/O-3/O-5 |
| `stalls === 0` | ✅ **E-6**, «0 band» EMAS |
| `day-breakdown.tsx` | ✅ besh `<dt>`/`<dd>`, `role="status"`, foiz YO'Q |

**Eng qimmatli qaror shu taskda:** yig'indi (`Rasta N ta`) **serverdan**
keladi va klientda qayta jamlanmaydi. Test esa uni **DOM'dan** oladi:
to'rtta `<dd>` o'qiladi, qo'shiladi va sarlavhadagi son bilan
solishtiriladi. Fixture ATAYIN «notekis» (186/68/4/42/31, ya'ni
`default_empty`, `no_coverage` va `human_confirmed` **noldan farqli**),
shuning uchun:

- `default_empty` `empty` ga qo'shilsa yig'indi **oshadi** (sabotaj S1);
- `human_confirmed` yig'indiga qo'shilsa u ham **oshadi** — ikkinchi
  assert buni alohida o'lchaydi.

Nol fixture'da ikkala buzilish ham **jimgina o'tardi**, shuning uchun
«hammasi nol» holati **alohida** test.

### Task 2 — Raqam kontekst bilan keladi yoki umuman kelmaydi

`confusion-matrix.tsx` — sof native `<table>` + `<caption>` +
`th[scope=col]` (nazoratchi) + `th[scope=row]` (tizim), to'rt katak
`font-mono`, ikki xato katagi `⚠` **va** o'z toni bilan.

**Foiz bu faylda hisoblanmaydi.** `percentView()` faqat **miqyosni**
o'zgartiradi (0..1 -> foiz) va uchala chegaradan birortasi `null` bo'lsa
`null` qaytaradi — ya'ni **nuqta baho oraliqsiz chizilmaydi**. Faylda
birorta bo'lish amali ham, `lib/wilson.ts` importi ham yo'q
(deviatsiya #2).

`round-summary.tsx` — `roundCounters()` sof funksiyasi D-16 ning
printsipini **mexanik** qildi:

```
null  ->  QATOR YO'Q   (o'lchovning yo'qligi)
0     ->  QATOR BOR    (natija)
```

Va aynan shu qoida «Nazoratchining ichki mosligi» qatorini ham
tug'ilmaydigan qiladi: mos keladigan maydon javobda **yo'q**.

### Task 3 — Ro'yxat, DL-5 va manbaning YO'QLIGI

| Element | Holat |
|---|---|
| Tartib | ✅ **SERVERDAN**; fixture alifbo bo'yicha teskari, klient saralasa test qizaradi |
| Filtr | ✅ AYNAN BITTA — `?nocov=1` |
| Badge matni | ✅ **to'liq**, qisqartirilmagan |
| Virtualizatsiya | ✅ **yo'q** — `content-visibility` naqshi inline; `package.json` diff **bo'sh** |
| DL-5 | ✅ hukm, MANBA, slot nisbati, `notBillingYet`; ⛔ patta/summa YO'Q, `<img>` va `<a>` YO'Q |
| `stallSource()` | ✅ `no_coverage` -> **`null`** (qator umuman chizilmaydi) |

## Sabotaj o'lchovlari — nima QIZARDI, **nima YASHIL QOLDI** va **yetdimi?**

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --`
**ishlatilmadi**); oxirida `git status` toza.

| # | Sabotaj | Tizimga yetdimi? | NATIJA |
|---|---|---|---|
| **S1** | `empty` ga `default_empty` qo'shildi (D-19) | ✅ | 🔴 **2 test** — yorliq testi **va** DOM yig'indisi |
| **S2** | Nol qiymatli hisoblagichlar yashirildi | ✅ | 🔴 **2 test**. ⚠ «Notekis» fixture'li 6 test **yashil qoldi** |
| **S3** | `measured` -> `n >= min_sample` | ✅ | 🔴 **AYNAN BITTA** test — pastga qarang |
| **S4** | `percentView` oraliqsiz nuqtani qaytardi | ✅ | 🔴 **2 test** — sof funksiya **va** DOM |
| **S5** | `false_occupied` klientda `fp / n` bilan hisoblandi | ✅ | 🔴 **AYNAN BITTA** test — pastga qarang |
| **S6** | `roundCounters` `?? 0` bilan | ✅ | 🔴 **2 SOF FUNKSIYA testi**. ⚠ **DOM testi YASHIL qoldi** — pastga qarang |
| **S7** | «Ichki moslik: 100 %» qatori qo'shildi | ✅ | 🔴 **2 test** — to'plam asserti **va** qator soni |
| **S8** | Ro'yxat klientda saralandi | ✅ | 🔴 **3 test** |
| **S9** | `no_coverage` ga «Tizim» manbasi berildi | ✅ | 🔴 **2 test** — sof funksiya **va** DOM |
| **S10** | `strictObject` -> `object` | ✅ | 🔴 **AYNAN BITTA** test. ⚠⚠ **57 render testi YASHIL qoldi** — pastga qarang |
| **S11** | Poll o'tgan kunda ham yoqildi | ✅ | 🔴 1 test |
| **S12** | `unanswered` javobdan emas, `answered - n` dan | ✅ | 🔴 **3 test** (o'lchangan **va** o'lchanmagan holatda) |
| **S13** | Bazaviy ulush yashirildi | ✅ | 🔴 1 test |

### S3 — «BUGUN BIR XIL NATIJA» ENG XAVFLI SABOTAJ SHAKLI

`report.measured` ni `report.n >= report.min_sample` ga almashtirish
**faqat bitta** testni qizartirdi va sabab o'lchanadigan:

- `n = 19`, `min_sample = 20` -> ikkala shart ham «yashirish» deydi;
- `n = 22`, `min_sample = 25` -> ikkalasi ham «yashirish» deydi;
- `n = 612`, `measured = true` -> ikkalasi ham «ko'rsatish» deydi.

Ya'ni **uchala tabiiy fixture ham farqni ko'rmaydi**. Farq faqat
`measured = false` bo'lgan-u `n` katta holatda tug'iladi — va o'sha
holat **ataylab** yozilgan test bilan qo'riqlanadi. Bu 05-12 sabotaj J
va 05-10 sabotaj D ning aynan sinfi: **ikki ifoda bugungi ma'lumotda
teng bo'lsa, hech qanday «tabiiy» test ularni ajratmaydi.**

### S5 — MAXRAJ SABOTAJI FAQAT LITERAL FOIZ TESTIDA KO'RINADI

`fp/(tp+fp)` ni `fp/n` ga almashtirish 5,4 % ni 3,8 % ga aylantirdi va
**faqat** «uch oraliq ham chiqadi va foizlar SERVER qiymatidan» testi
qizardi. Yashil qolganlari mantiqiy:

- «ikki xato uchun ikki xil jumla» — u **jumlalarni** o'lchaydi, sonlarni
  emas;
- `percentView` ning uchala testi — ular **miqyosni** o'lchaydi, MANBANI
  emas.

**Xulosa yozib qo'yildi:** foizning MANBASI (server) faqat **literal
qiymat** testi bilan qulflanadi; struktura testlari unga **ko'r**.

### S6 — DOM DARVOZASI `?? 0` NI KO'RA OLMAYDI

`roundCounters` `null` ni `0` ga aylantirganda **ikkala sof funksiya
testi** qizardi, «tortilmagan turda hisoblagich umuman chizilmaydi»
degan **DOM testi esa yashil qoldi** — chunki komponent `round.drawn`
bo'yicha **oldin** shoxlanadi va o'sha holatda `roundCounters` umuman
chaqirilmaydi.

Ya'ni bu buzilish ekranga **faqat** `drawn = true` bo'lgan-u biror
maydon `null` bo'lgan kunda chiqardi. DOM testi uni ko'rmasdi, sof
funksiya testi esa **darhol** ko'rsatdi — S-13 naqshining («sof mantiq
ajratiladi») bu rejadagi ikkinchi tasdig'i.

### S10 — SXEMA DARVOZASI RENDER TESTLARIDAN MUSTAQIL

`z.strictObject` -> `z.object` **57 komponent testining birortasini**
qizartirmadi va bu **kutilgan**: maydon ekranga chiqmaydi. Lekin u
**brauzerga yetib boradi** — kesh grafida, DevTools'da, `JSON.stringify`
da. Aynan shu sababdan D-16 ning himoyasi **ikki qatlamli**:

1. **sxema** — javobni RAD ETADI (`occupancy-queries.test.tsx`);
2. **DOM** — `<dt>` to'plami literal qulflangan (`round-summary.test.tsx`,
   sabotaj S7 bilan o'lchandi).

Bu 05-13 ning S1 sabotajining aynan takrori va u yerdagi xulosa shu
yerda ham amal qiladi.

### ⛔ «SO'Z TOPILMADI» ASSERTI YOZILMADI — VA BU ONGLI

D-16 uchun eng tabiiy test —
`expect(text).not.toContain("ichki moslik")` — **hech qachon
qizarmaydigan** test bo'lardi: u komponentda hech qachon bo'lmagan
narsani o'lchaydi. Sabotaj S7 aynan shuni sinab ko'rish uchun qilindi va
u qatorni **boshqa nom bilan** (`Ichki moslik`) qo'shdi; qizargan yagona
mexanizm — **yorliqlar to'plamining literal tengligi**. Bu 05-13 ning
S2 darsining («da'vo o'lchanadigan FARQDAN chiqishi kerak») to'g'ridan-
to'g'ri qo'llanishi.

## Deviations from Plan

### 1. `[Rule 3 - Blocking]` `DayPicker` ga BITTA parametr qo'shildi — fayl reja ro'yxatidan tashqarida

- **Muammo:** Reja «kun tanlagichi 4-fazadagi bilan **aynan bir xil** va
  qayta ta'riflanmaydi; yagona farq — `occupancy.noFutureDays` matni»
  deydi. `DayPicker` esa `snapshots.noFutureDays` ni **qotirib** yozgan
  va rejaning `files_modified` ro'yxatida `day-picker.tsx` **yo'q**.
- **Rad etilgan variant — ikkinchi nusxa:** u `max` atributi,
  normallashtirish qoidasi (`raw <= todayIso`) yoki `history:"push"`
  bo'yicha ajralib ketardi va **bittasida kelajakdagi kun tanlanadigan
  bo'lib qolardi** — buni hech qanday test ko'rmasdi, chunki ikkinchi
  nusxa o'z testi bilan kelardi.
- **Tuzatish:** bitta ixtiyoriy prop (`noFutureDaysKey`), standart
  qiymati 4-fazaning xulqini **saqlaydi**. Tip — `string` emas,
  **ittifoq** (`useTranslations()` kalitlarni sxemadan chiqaradi, ya'ni
  `string` mavjud bo'lmagan kalitni ish vaqtiga o'tkazardi).
- **Commit:** `05229e8`

### 2. `[Rule 4 - QAROR]` `lib/wilson.ts` matritsaga IMPORT QILINMADI — reja uni AYNAN talab qiladi

- **Muammo:** Rejaning `key_links` bo'limi
  `confusion-matrix.tsx -> lib/wilson.ts` bog'lanishini
  `wilsonInterval + MIN_SAMPLE_FOR_PERCENT` orqali talab qiladi.
- **⛔ IKKALA import ham NOTO'G'RI bo'lardi va sabab O'LCHANGAN:**
  - `wilsonInterval` — uch nisbat ham, uch oraliq ham serverda
    hisoblangan holda keladi. Klientda qayta hisoblash **xato bo'lib
    ko'rinmasdi**: 05-12 o'lchagan ikki maxraj (`fp/(tp+fp)` va `fp/n`)
    **ikkalasi ham to'g'ri arifmetika**, lekin **boshqa savolga** javob
    (5,4 % vs 3,8 %). Sabotaj **S5** buni mahsulot yo'lida o'lchadi;
  - `MIN_SAMPLE_FOR_PERCENT` — 05-12 ning **2-ochiq bandi** ochiq
    aytadi: «javobda `min_sample` maydoni bor — klient uni **o'zi
    yozmasligi** kerak».
- **Niyat SAQLANDI va KUCHAYTIRILDI:** «foiz kichik namunada
  chizilmaydi» kafolati **serverning ikki maydoni** bilan qulflanadi
  (`measured` + `min_sample`) va ikkalasi ham **alohida** test bilan
  o'lchanadi — shu jumladan `min_sample = 25` fixture'i, u klientdagi
  qotirilgan `20` ni **fosh qiladi**.
- **⚠ `lib/wilson.ts` TEGILMADI va u tirik qoladi:** uning
  `MIN_SAMPLE_FOR_PERCENT` konstantasi serverdagi jufti bilan
  `test_the_shared_constants_match_the_client` orqali matn darajasida
  qulflangan (05-12), ya'ni chegaraning ikki tomoni hamon bog'langan.
- **Commit:** `6c7bfc0`

### 3. `[Rule 1 - Meros qilib olingan o'lchangan ziddiyat]` UI-SPEC §11.6 ning «Ichki moslik» qatori CHIZILMADI

- **Muammo:** Reja Task 2 da uni ochiq sanaydi («nazoratchining ichki
  mosligi (D-16)»), UI-SPEC §11.6 esa uni ekran eskiziga ham qo'yadi va
  `occupancy.selfConsistency*` kalitlarini ham beradi.
- **05-11 buni O'LCHADI va IMKONSIZ deb topdi;** 05-12 esa maydonni
  javobdan **na son, na maydon** sifatida chiqarib tashladi va o'z
  SUMMARY sining **1-ochiq bandida** 05-14 uchun ochiq yozdi: «Uni
  ekranda `100 %` yoki `—` qilib chizish ham TAQIQLANADI».
- **To'rt variant ko'rildi:** (a) `100 %` — o'lchanmagan miqdorni
  o'lchangan qilardi; (b) `—` yoki o'chirilgan qator — bo'sh joy
  keyingi ijrochini uni to'ldirishga undardi; (c) kalitlarni
  yozib qo'yib, komponentni yozmaslik — **iste'molchisiz kalit**, ya'ni
  05-13 deviatsiya #8 ning aynan sinfi; (d) **umuman yo'q**.
- **Tuzatish:** (d). Qator ham, kalitlar ham yozilmadi. Sabab
  `round-summary.tsx` ning modul docstringida va
  `confusion-matrix.tsx` da (u yerga ham «tabiiy» ravishda tushishi
  mumkin edi).
- **⛔ Yo'qlik `<dt>` TO'PLAMI bilan o'lchanadi**, «so'z topilmadi»
  bilan emas — sabotaj **S7** ikkinchi shaklning yashil qolishini
  ko'rsatgan bo'lardi.
- **Commit:** `6c7bfc0`

### 4. `[Rule 4 - QAROR]` DL-5 SLOT QATORLARISIZ qurildi — ma'lumot manbai YO'Q

- **Muammo:** UI-SPEC §11.7 va rejaning Task 3 i DL-5 dan «kun
  davomidagi har vaqt uchun bitta qator: vaqt · kamera · natija · manba»
  va har qatordan **dalil kadri** talab qiladi.
- **O'lchandi:** `GET /occupancy` bitta rasta uchun `OccupancyStallItem`
  beradi — **aynan yetti maydon**, ular ichida na slot vaqti, na kamera
  nomi, na `snapshot_id`. `occupancy_repo.py` da bunday metod ham
  **yozilmagan** (`day_stalls` agregat qaytaradi).
- **Rad etilgan ikki variant:** (a) qatorlarni klientda to'qib chiqarish
  — **soxta ma'lumot**, ya'ni eng yomon shakldagi stub; (b) «tez orada»
  degan bo'sh jadval — **placeholder**, u ham va'da berib bajarmaydi.
- **Tuzatish:** dialog **faqat o'lchanganini** ko'rsatadi — kun
  hukmi, uning MANBASI, slot nisbati va `notBillingYet`. Hech biri
  to'qilmagan.
- **Nega yangi marshrut qurilmadi:** `GET /occupancy/stalls/{id}?day=`
  + repozitoriy metodi + `REPORT_VIEW` tegi + `MINIMUM_MATRIX_ROUTES`
  60 -> 61 + `tests/tenancy` qatorlari — **Rule 4** (arxitektura), va bu
  rejaning fayl to'plami **faqat `frontend/`**.
- **`deferred-items.md` 3-bandi** — to'liq sabab va eng tor tuzatish.
- **Commit:** `509a43e`

### 5. `[Rule 2 - Correctness]` «Tez qaror» chegarasi MATNDA NOMLANMAYDI

- **Muammo:** §12.6 ning matni `Tez qaror: {count} ta ({seconds}
  soniyadan tez)`. Chegara — 2000 ms — `accuracy_report.
  is_fast_decision()` da yashaydi va `GET /occupancy/round` javobida
  **maydon sifatida yo'q**.
- **Rad etilgan variant:** klientda `2` yozish. U server
  konstantasining **ikkinchi nusxasi** bo'lardi va chegara o'zgargan
  kuni yorliq **jimgina yolg'on** gapirardi — aynan `min_sample` uchun
  05-12 rad etgan yo'l.
- **Tuzatish:** matn sonni emas, **ma'noni** aytadi
  (`occupancy.fastDecisionsWhy`: «Juda tez berilgan javoblar. Ular
  bloklanmaydi — faqat shu hisobotda ko'rinadi»). Eng tor tuzatish
  (`OccupancyRoundResponse` ga bitta maydon) `deferred-items.md` ning
  4-bandida.
- **Commit:** `6c7bfc0`

### 6. `[Rule 2 - Correctness]` `stallSource()` `no_coverage` uchun MANBA BERMAYDI

- **Muammo:** §12.6 uch manba beradi (`Tizim`/`Nazoratchi`/`Ko'rilmadi`)
  va qamrovsiz rasta ularning **birortasiga ham** tushmaydi: uni birorta
  kamera ko'rmagan, ya'ni **hukm umuman yo'q**.
- **Ikkala «tabiiy» tanlov ham noto'g'ri:** «Tizim» bo'lmagan javobni
  bor qilardi; «Ko'rilmadi» esa **D-19 ni (nazoratchi ulgurmadi) D-22
  ga (kamera ko'rmaydi) aralashtirardi** — ikkalasi butunlay boshqa
  nosozlik va boshqa tuzatish.
- **Tuzatish:** `null` -> qator **umuman chizilmaydi**; o'rniga
  `occupancy.noCoverageWhy` jumlasi chiqadi. Bu `roundCounters` ning
  «`null` -> qator yo'q» qoidasining aynan o'zi.
- **Commit:** `509a43e`

### 7. `[Qaror]` `round-summary.test.tsx` — reja ro'yxatida yo'q QO'SHIMCHA test fayli

Reja Task 2 uchun bitta test fayli (`confusion-matrix.test.tsx`)
sanaydi, qabul mezonlarida esa **`round-summary` ning ikki bandi** bor.
Ularni matritsa faylida yashirish D-16 darvozasini **topib bo'lmaydigan**
joyga qo'yardi. Fayl **mahsulot kodi emas**; ikkala komponent ham o'z
testiga ega.

### 8. `[Qaror]` Aniqlik bloki POLL QILINMAYDI

§8.5 «Y-4» uchun bitta poll qoidasi beradi. (B) zonasi esa **kunlik
emas** — u oyning to'plangan namunasi (§11.1: «(B) o'zgarmaydi»). Uni
har 60 soniyada so'rash 30 kunlik agregatni qayta hisoblatardi va
ekranda hech nima o'zgarmasdi. Kunlik so'rov va tur holati **poll
qilinadi** (bugungi kunda).

### 9. `[Qaror]` `n` sarlavhada `font-mono` OLMAYDI

§9.4 «Namuna hajmi `n`» ni monospace ro'yxatiga qo'yadi. Bu yerda u
**proza jumlasining ichida** («Ko'rmasdan tekshirish namunasidan · … ·
n=612») va hech nima bilan **ustunlashmaydi**, ya'ni monospace bezak
bo'lardi. §9.4 ning sababi («ustunlar tik solishtiriladi») **matritsa
kataklari** va **uch oraliq** uchun to'liq bajarilgan.

### 10. `[Qaror]` `content-visibility` uchun `globals.css` ga sinf QO'SHILMADI

Mavjud `.zone-block` plan-xaritaning ~400px lik bloklari uchun
o'lchangan va uning `contain-intrinsic-size` i 56px lik qatorga
to'g'ri kelmaydi. Yangi sinf qo'shish `globals.css` ni bu rejaning
fayl ro'yxatidan tashqarida o'zgartirardi; Tailwind ning ixtiyoriy
xossasi (`[content-visibility:auto]`) aynan shu ehtiyoj uchun bor.

---

**Total deviations:** 10 (1× Rule 1 meros ziddiyat, 3× Rule 2
to'g'rilik, 1× Rule 3 bloklovchi, 2× Rule 4 qaror, 3× ongli qaror)
**Impact on plan:** Ko'lam kengaymadi; yangi npm paketi qo'shilmadi
(`package.json` diff **bo'sh**). Mahsulot kodida ro'yxatdan tashqarida
**bitta** fayl (`day-picker.tsx`, bitta ixtiyoriy prop). Uchta
deviatsiya (#2, #3, #4) spek yoki reja so'ragan narsani **atayin
qurmaslik** haqida va uchalasining ham sababi bitta: **ma'lumot manbai
yo'q**, taxmin emas.

## Verification Performed

| O'lchov | Bazaviy | Yakuniy | Holat |
|---|---|---|---|
| `vitest run` | 550 (38 fayl) | **620 (43 fayl)** | ✅ +70 |
| `node --test scripts/*.test.mjs` | 144 | **144** | ✅ o'zgarmadi (G-11…G-18 yashil) |
| `npm run i18n:check` | 927 × 3 | **980 × 3** | ✅ +53, kalit va ICU parity to'liq |
| `npm run typecheck` | toza | **toza** | ✅ |
| `npm run lint` | toza | **toza** | ✅ 0 xato, 0 ogohlantirish |
| `npm run build` | — | **✓ Compiled** | ✅ `/[locale]/occupancy` uchala tilda ro'yxatda |
| `grep -c recharts package.json` | 0 | **0** | ✅ diagramma paketi yo'q |
| `git diff frontend/package.json` | — | **bo'sh** | ✅ virtualizatsiya paketi ham yo'q |
| `uz-Cyrl.overrides.json` diff'da | — | **YO'Q** | ✅ (D-14) |
| `rbac.ts` / `app-shell.tsx` diff'da | — | **YO'Q** | ✅ (M-8) — `/occupancy` navigatsiyada allaqachon bor edi |
| `git diff --name-only` da `services/` | — | **0 fayl** | ✅ backend TEGILMADI |
| Sabotajlar | — | **13/13 o'lchandi** | ✅ hammasi `cp` bilan tiklandi, `git status` toza |
| **`npm run gate`** (to'liq zanjir) | — | **exit 0** | ✅ **BIRINCHI ijroda** |

**`npm run gate` — exit 0, birinchi urinishda.** To'liq zanjir yuritildi:
`sim:up` -> `ruff`+`mypy` (`core-api`) -> `pytest` -> `ruff`+`mypy`
(`cv-service`) -> `cv:test` -> `i18n:check` -> `node --test` + `vitest`
-> `typecheck` -> `lint` -> `build`. ⚠ Bu 05-12 va 05-13 dan **farq
qiladi**: ikkalasida ham birinchi ijro soatga bog'liq alert testida
yiqilgan edi. `dc5f182` + `bcc2d49` langarlari **ishlayapti** — bu
o'sha tuzatishlarning mustaqil tasdig'i.

⚠ **BACKEND QAYTA YUGURTIRILDI, LEKIN O'ZGARTIRILMADI:** bu reja
birorta Python faylini o'zgartirmagan (`git diff --name-only` da
`services/` **0 fayl**), ya'ni 05-12 ning **548 tenancy** va 05-13 ning
bazaviy sonlariga strukturaviy ta'sir yo'q.

## Known Stubs

**Yo'q** — soxta ma'lumot manbai ham, placeholder matn ham yaratilmadi.
To'rt band ATAYIN «qurilmagan» va ular stub EMAS:

| Nima | Nega stub emas |
|---|---|
| «Ichki moslik» qatori **umuman yo'q** | Bu bo'sh element ham, ishlamaydigan qator ham emas: son o'lchanmaganda **qator umuman tug'ilmaydi**. `100 %` ham, `—` ham aynan stub bo'lardi va ular T-05-04 ni buzardi. Yo'qlik **ikki qatlamda** o'lchanadi (sxema + `<dt>` to'plami) |
| `occupancy.selfConsistency*` kalitlari **yozilmadi** | Iste'molchisiz kalit — «bu ishlaydi» degan yolg'on va'da (05-13 deviatsiya #8 ning aynan mantiqi). Ustiga u keyingi ijrochini qatorni chizishga **undardi** |
| DL-5 da **slot qatorlari yo'q** | Ularni beradigan **marshrut yo'q** (yuqorida o'lchandi). To'qilgan qator soxta ma'lumot, bo'sh jadval esa placeholder bo'lardi. Dialog CHIZAYOTGAN hamma narsa serverdan keladi va to'liq ishlaydi |
| «Tez qaror» chegarasi **nomlanmagan** | Son javobda **yo'q**; uni klientda yozish server konstantasining ikkinchi nusxasi bo'lardi. Ko'rsatilayotgan SON esa haqiqiy va serverdan keladi |

## Threat Model Coverage

| Threat ID | Disposition | Qanday yopildi |
|---|---|---|
| T-05-67 (jimgina yo'qotish) | mitigate | `Ko'rilmagani uchun bo'sh` **alohida** `<dt>`, nol bo'lganda ham (S2 bilan o'lchandi); `> 0` da majburiy OQIBAT jumlasi + `occupancy_review` bo'lsa ko'rib chiqishga yo'l. ⛔ Yig'indi darvozasi (S1) uni `empty` ga qo'shishni **arifmetik** ravishda ushlaydi |
| T-05-68 («aniqlik 94 %» yolg'iz) | mitigate | Matritsa + `base_rate` (S13) + `n` majburiy; foiz `measured` bo'yicha (S3) va oraliqsiz nuqta **umuman chizilmaydi** (S4). ⚠ Foizning MANBASI faqat literal qiymat testi bilan qulflanadi (S5) |
| T-05-69 (nazoratchiga o'z aniqligi) | mitigate | Sahifa `report_view` ostida — huquq tekshiruvi **so'rovdan oldin**, ya'ni uchala so'rov ham ketmaydi. Haqiqiy nazorat serverda (05-12: uchala marshrut `REPORT_VIEW`, nazoratchi uchun 403 alohida sinalgan) |
| T-05-70 (namunani qayta tortish) | mitigate | Tugma **umuman qurilmagan** — `round-summary` da `<button>`, `<input>`, `<form>` yo'qligi **ikkala holatda** ham o'lchanadi; G-18(a) matn darvozasi yashil; server tomonda marshrut yo'q (05-11 OpenAPI skani) |
| T-05-71 (dalil kadri) | mitigate | DL-5 da `<img>` ham, `<a>` ham, `download` ham **yo'q** (test bilan). ⚠ Bu ayni paytda deviatsiya #4 ning oqibati: kadr yo'li bugun **umuman mavjud emas** |
| T-05-72 (6-faza bilan chalkashish) | mitigate | `occupancy.notBillingYet` **shartsiz** chiziladi (xulosada ham, DL-5 da ham); ikkala komponentda ham `so'm`/`tarif`/`qarz`/`summa` so'zlarining yo'qligi DOM asosida o'lchanadi |

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: authorization-gap | `services/core-api/app/api/v1/snapshots.py` | ⚠ **05-10/05-11/05-13 dan MEROS va u KUCHDA.** Bu reja `rbac.ts`, `rbac.py` yoki `snapshots.py` ga **tegmadi** (M-8). ⚠ Bu SAHIFAGA ta'siri **yo'q**: `/occupancy` `report_view` ostida va u rolda `camera_view` ham bor — bo'shliq faqat sof `inspector` da |

**Bu rejaning O'Z yuzasida yangi tahdid topilmadi.** Yangi marshrut ham,
yangi mutatsiya ham, yangi huquq yuzasi ham ochilmadi; `/occupancy`
navigatsiya yozuvi 05-13 dan **oldin** ham bor edi va `report_view` ga
bog'langan.

## ⚠ BAJARILMAGAN QO'LDA TEKSHIRUV (faza yopilishiga)

`.planning/config.json`: `workflow.human_verify_mode: "end-of-phase"`.
Bu muhitda brauzer yo'q, shuning uchun Task 3 ning 8 qadamli qo'lda
tekshiruvi **bajarilmadi** (05-09 deviatsiya #16 va 05-13 bilan aynan
bir xil holat). Ish bajarildi va **avtomatik verifikatsiyadan to'liq
o'tdi**.

Faza yopilishida bajarilishi kerak:

1. `npm run up`; urug'ni yuklang va **kamida bir kunni yoping**
   (`day_close`) — aks holda bugungi kun `stalls = 0` beradi va ekran
   **to'g'ri** ravishda E-6 ni ko'rsatadi.
2. `director` roli bilan `/uz/occupancy` — **beshala hisoblagich**
   ko'rinyaptimi, **nol bo'lganlari ham**?
3. Sarlavhadagi «Rasta N ta» hisoblagichlar yig'indisiga mos keladimi?
4. Aniqlik bloki: `n` kichik bo'lsa **foiz ko'rinmayaptimi**? Ma'lumot
   yetarli bo'lsa to'rt katak, uch oraliq va bazaviy ulush bormi?
5. «Namunani qayta tortish» degan tugma **bormi**? (Kutilgan: **yo'q**)
6. Rasta ro'yxatidan bittasini oching (DL-5). **Summa yoki patta
   hisobi bormi**? (Kutilgan: **yo'q**) ⚠ Slot qatorlari ham
   **yo'q** — bu kutilgan holat, sababi deviatsiya #4 da.
7. `?nocov=1` — faqat qamrovsiz rastalar qoladimi va URL'da
   saqlanadimi?
8. Uch tilni almashtiring: `uz-Latn`, `uz-Cyrl`, `ru` — kirillchada
   lotin qoldig'i yoki aralash alifbo defekti bormi? (Kutilgan: yo'q)
9. `inspector` roli bilan kiring — `/occupancy` navigatsiyada
   **ko'rinmasligi** kerak va manzilni qo'lda kiritganda «ruxsat yo'q»
   chiqishi kerak.

⚠ **Qo'shimcha o'lchov bandi:** kun tanlagichda kelajakdagi kunni
tanlashga urinib ko'ring — e'lon matni **`occupancy.noFutureDays`**
bo'lishi kerak (`snapshots.noFutureDays` EMAS). Bu deviatsiya #1 ning
yagona ko'rinadigan oqibati va u avtomatik test bilan qamralmagan
(nuqs adapteri talab qilinadi).

## Keyingi rejalar uchun ochiq bandlar

1. **⚠⚠ `05-15` uchun — UI-SPEC §11.6 va §11.7 ESKIRGAN.** §11.6 ning
   «Ichki moslik» qatori (05-12 ning 1-ochiq bandi) va §11.7 ning DL-5
   slot jadvali (deviatsiya #4). Spek faylini tuzatish `05-15` ning
   bandi — 05-13 ning 7-ochiq bandi bilan **bir xil sinf**.
2. **`05-15` yoki 8-faza uchun — DL-5 ning ma'lumot manbai.**
   `deferred-items.md` 3-bandi: yangi marshrut, repozitoriy metodi,
   `MINIMUM_MATRIX_ROUTES` 60 -> 61.
3. **`05-15` yoki 8-faza uchun — «tez qaror» chegarasi javobga.**
   `deferred-items.md` 4-bandi: bitta maydon, yangi huquq yuzasi
   ochilmaydi.
4. **`05-15` uchun — `MINIMUM_MATRIX_ROUTES` bu rejada O'ZGARMADI**
   (backend tegilmadi): u 05-12 dan keyin **60**.
5. **`localeHref` TO'RTINCHI nusxada** (`camera-row.tsx`,
   `review/page.tsx`, `review/uncertain/page.tsx`,
   `review/blind/page.tsx`, `occupancy/page.tsx`). 05-13 ning 4-ochiq
   bandi kuchda; prefiks XARITASI nusxa ko'chirilmagani uchun bugungi
   xavf past, lekin nusxalar soni endi **beshta**.
6. **6-faza uchun:** bu sahifa «kun davomida kamida bir marta band
   ko'rindi» deydi va `occupancy.notBillingYet` buni **shartsiz**
   aytadi. BILL-01 (slotlararo agregatsiya) kelganda ikkinchi son
   paydo bo'ladi — jumla **o'sha paytda ham** qolishi kerak, aks holda
   direktor ikki sonni bir narsa deb o'qiydi.
7. **Operatsion (05-HUMAN-UAT ga):** `day_close` **03:40** da ishlaydi
   va **KECHAGI** kunni yopadi, ya'ni bugungi `/occupancy` odatda E-6
   ko'rsatadi. Bu **nosozlik emas** va matn ham shuni aytadi, lekin UAT
   da ochiq tushuntirilishi kerak (05-12 ning 8-ochiq bandi).
8. **8-faza uchun:** `accuracyKey(marketId, from, to)` imzosi davr
   tanlagichiga **tayyor** — kesh yozuvi davr bo'yicha o'zi bo'linadi.
   Bugun ikkala argument ham `null` va so'rovga parametr qo'shilmaydi.

## Self-Check: PASSED

- **Fayllar:** e'lon qilingan **12 yaratilgan + 5 o'zgartirilgan** —
  hammasi diskda (`git diff --name-only 05229e8~1..HEAD` -> **17 fayl**);
- **Commitlar:** `05229e8`, `6c7bfc0`, `509a43e` — uchalasi ham
  `git log` da;
- **O'chirilgan fayl YO'Q:** `git diff --diff-filter=D --name-only
  05229e8~1..HEAD` **bo'sh**;
- **Sabotajlar:** 13/13 o'lchandi va har biri **`cp` bilan** snapshotdan
  tiklandi; `git checkout --` **ishlatilmadi**; oxirida `git status`
  toza (faqat bu rejaga tegishli bo'lmagan to'rtta ildiz fayli
  kuzatilmagan holda qoldi — ular **tegilmadi**);
- **Tegilmagan fayllar tasdig'i:** `frontend/src/lib/rbac.ts`,
  `frontend/src/components/shell/app-shell.tsx`,
  `frontend/messages/uz-Cyrl.overrides.json`, `frontend/package.json`,
  `frontend/package-lock.json`, `frontend/src/app/globals.css`,
  `frontend/src/lib/wilson.ts`, `services/**`, `tests/**` — **birortasi
  ham diff'da yo'q**;
- **`npm run gate`: exit 0** (birinchi ijroda).

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-10*
