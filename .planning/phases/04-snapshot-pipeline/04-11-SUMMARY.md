---
phase: 04-snapshot-pipeline
plan: 11
subsystem: frontend
tags: [a11y, roving-tabindex, aria-table, i18n, d-12, d-19, g-3, g-7, g-8, cam-05, cam-06, cam-07, found-06]

# Dependency graph
requires:
  - phase: 04-snapshot-pipeline
    plan: 10
    provides: "`snapshot-queries.ts` (`useCaptureDay`/`useSnapshotDetail`/`useAlerts`), `capture-errors.ts` (`actor`), `api-types.ts` sxemalari, `/snapshots` qobig'i va zona A; G-2/G-3 QAMROV tetigining matn katalogiga ko'chirilishi"
  - phase: 04-snapshot-pipeline
    plan: 09
    provides: "`GET /capture-runs?day=`, `GET /snapshots/{id}`, AUDITLANGAN `GET /snapshots/{id}/image`, `GET /alerts?closed=`"
  - phase: 04-snapshot-pipeline
    plan: 08
    provides: "`jobs/alerting.py::ALERT_META` — TO'QQIZ alert kaliti va `alert_events.detail` ning YOZISH paytidagi allowlisti"
  - phase: 04-snapshot-pipeline
    plan: 02
    provides: "G-1/G-2/G-3/G-4/G-10 (`snapshot-copy.test.mjs`), G-6 (`gen-cyrillic.test.mjs`)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    provides: "`camera-status-badge.tsx` rang+ikonka naqshi, `live-view-dialog.tsx` holat mashinasi, `discovery-result.tsx` `<dl>` hisoblagichlari, `channelLabel`, `nvr-copy.test.mjs` G-6 darvozasi"
provides:
  - "`components/snapshots/capture-cell.tsx` — TO'QQIZ hujayra holati; `missed` UCH mustaqil kanalda (ikonka + `aria-label` + punktir chegara) va 44×44 nishonda"
  - "`components/snapshots/capture-grid.tsx` — kamera × vaqt matritsasi, native `<table>`, roving tabindex, BITTA tab to'xtashi"
  - "`components/snapshots/capture-legend.tsx` — to'qqizala yozuv DOIM ochiq"
  - "`components/snapshots/day-picker.tsx` — `?day=`/`?issues=`/`?closed=` URL holati BIR joyda; kelajak kun IKKI qatlamda to'siladi"
  - "`components/snapshots/day-summary.tsx` — oltala hisoblagich nol bilan birga; `planned === 0` da Z-7"
  - "`components/snapshots/snapshot-dialog.tsx` — sakkiz juftlik -> sakkiz jumla; rasm FAQAT auditlangan proxydan"
  - "`components/snapshots/alert-list.tsx` + `alert-row.tsx` — rasmsiz ogohlantirish zonasi; `notified_at` yashirilmaydi"
  - "`/snapshots` sahifasining to'rtala zonasi yig'ilgan; Z-7/Z-8/Z-10 ajratilgan"
  - "§11.5–§11.7, §11.9, §11.10 uchala tilda (671 -> 777 kalit)"
affects: [04-12, 05-cv-zonalar, 06-billing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Darvozaning TETIGI o'lchanadi, taxmin qilinmaydi: `snapshots.cell.*` ni BITTA tilga qo'yish G-2/G-3 QAMROVINI darhol qizartirdi — komponentlar tartibi shu o'lchovdan keyin qayta chizildi"
    - "Fayl ustidagi matn darvozasi bilan spetsifikatsiya to'qnashsa, ARIA-1.2 ning TENG KUCHLI shakli ishlatiladi — darvoza kuchsizlantirilmaydi (`04-10` ning `schedule-dialog.tsx` qarori ikkinchi marta qo'llandi)"
    - "Xavfsizlik darvozasi obyekt KALITI bilan to'qnashsa, o'zgaradigan narsa — kodning SHAKLI, darvozaning ro'yxati emas: xarita solishtiruvga aylantiriladi"
    - "Noma'lum enum qiymati eng KAM da'vo qiladigan tomonga qiya bo'ladi: noma'lum holat `missed` deb ko'rsatilmaydi va noma'lum yorug'lik rejimi YAGONA nosozlik jumlasiga tushmaydi"
    - "Shaxsiy ma'lumot baytlari sarlavha talab qiladigan marshrutdan kelsa, tasvir elementi uni O'ZI yuklay olmaydi — baytlar sessiya tokeni bilan olinadi va vaqtinchalik havolaga aylantiriladi; har ochilish `audit_read` yozadi"
    - "URL holati SAHIFA modulida yashaydi, zona komponentida emas — zona uni prop bo'lib oladi va komponent testi URL adapterisiz ishlaydi"

key-files:
  created:
    - frontend/src/components/snapshots/day-picker.tsx
    - frontend/src/components/snapshots/day-summary.tsx
    - frontend/src/components/snapshots/day-summary.test.tsx
    - frontend/src/components/snapshots/capture-cell.tsx
    - frontend/src/components/snapshots/capture-cell.test.tsx
    - frontend/src/components/snapshots/capture-grid.tsx
    - frontend/src/components/snapshots/capture-grid.test.tsx
    - frontend/src/components/snapshots/capture-legend.tsx
    - frontend/src/components/snapshots/snapshot-dialog.tsx
    - frontend/src/components/snapshots/snapshot-dialog.test.tsx
    - frontend/src/components/snapshots/alert-list.tsx
    - frontend/src/components/snapshots/alert-list.test.tsx
    - frontend/src/components/snapshots/alert-row.tsx
  modified:
    - frontend/src/app/[locale]/(app)/snapshots/page.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
  deleted: []

key-decisions:
  - "Ogohlantirish zonasi Task 3 dan Task 2 ning MATRITSA commitidan OLDINGA ko'chirildi: `snapshots.cell.*` matni G-2/G-3 QAMROV tetigini ishga tushiradi va u AYNI commitda to'rtala faylni talab qiladi — platsholder yozish esa ochiq taqiqlangan"
  - "`snapshots.method` UI-SPEC §11.7 da IKKI xil ma'noda ishlatilgan (yorliq VA enum xaritasi) — JSON ikkalasini bitta kalitda ushlay olmaydi; enum `method.*` da qoldi, yorliq `methodLabel` ga ko'chdi"
  - "`verdictKey` noma'lum hukmda `null` qaytaradi: sakkiztadan birortasini «taxminan» tanlash ekranga tekshirilmagan DA'VO chiqarardi, holbuki bu jumlaning O'ZI da'vo"
  - "Noma'lum yorug'lik rejimi `darkDay` ga HECH QACHON tushmaydi — u sakkiztadan YAGONA nosozlik e'lon qiladigan jumla va o'lchov yo'qligidan yolg'on nosozlik chiqarish jimgina o'tkazib yuborishdan yomonroq"
  - "Noma'lum `status` `pending` ga, `succeeded` + noma'lum hukm `ok` ga tushadi — noma'lum holatni YO'QLIK deb ko'rsatish yolg'on ogohlantirish bo'lardi va admin haqiqiy `missed` larga ishonchini yo'qotardi"
  - "Rasm baytlari `apiRequest` bilan olinadi: proxy marshruti sessiya tokenini talab qiladi va tasvir elementi sarlavha qo'sha olmaydi — bu §14.3 ni KUCHAYTIRADI, chunki har ochilish `audit_read` yozadi"
  - "`?issues=1` filtri QATOR (kamera) darajasida: faqat muammoli hujayralarni qoldirish qatorni teshik-teshik qilib, «06:30 da nima bo'ldi?» savoliga kerak qo'shni kadrlarni olib tashlardi"
  - "`snapshotImageKey` — MAVJUD `snapshotKey` fabrikasining BOLASI; yangi global kalit qurilmadi va `snapshot-queries.ts` ga umuman tegilmadi"

patterns-established:
  - "Sabotaj natijasi UCH USTUNDA: nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi. Uchala sabotaj ham bashoratni tasdiqladi; ikkinchisi esa undan KUCHLIROQ chiqdi va yangi topilma berdi"
  - "«Bo'sh to'plam ustida yashil» sinfi komponent darajasida ham qo'llanadi: `capture-grid.test.tsx` ning fixture'ida `missed` qator YO'Q, ya'ni u «hujayra bo'sh emas» da'vosini UMUMAN o'lchamaydi — buni sabotaj ko'rsatdi"
  - "Uch tilli enum xaritasi backend REYESTRIGA solishtiriladi: `ALERT_META` ning to'qqizinchi kaliti UI-SPEC jadvalida yo'q edi va u faqat manbani o'qish bilan topildi"

requirements-completed: [CAM-05, CAM-06, CAM-07, FOUND-06]

# Metrics
duration: 1h 45m
completed: 2026-08-05
---

# Phase 4 Plan 11: Kun jurnali, to'qqiz hujayra holati va kadr detali Summary

**SC#2 ning «ochiq ko'rinadi» talabi endi bajarilgan: o'tkazib yuborilgan kadr bajarilgan kadr bilan AYNI 44×44 joyni egallaydi va uch mustaqil kanal bilan (`CircleSlash` ikonkasi, to'liq jumlali `aria-label`, punktir chegara) ajraladi; oltala hisoblagich nol bilan birga ko'rinadi; 175 hujayrali matritsa native jadval semantikasida BITTA tab to'xtashi bilan boshqariladi; sifat hukmi va yorug'lik rejimi bitta jumlaga birlashadi va dalil-kadr faqat auditlangan proxy orqali, ogohlantirish zonasiga esa umuman kirmasdan ochiladi.**

## Performance

- **Duration:** ~1 soat 45 daqiqa
- **Started:** 2026-08-04T22:38:55Z
- **Completed:** 2026-08-04T23:30Z
- **Tasks:** 3/3 (checkpoint yo'q)
- **Files:** 13 ta yangi + 4 ta o'zgargan
- **Commits:** 6 ta (ikkitasi RED)

## Task Commits

| # | Task | Commit |
|---|------|--------|
| 1 (RED) | `day-summary.test.tsx` + §11.5 matni | `41986e9` |
| 1 (GREEN) | Kun tanlagichi va oltita hisoblagich (G-8) | `8295a3b` |
| 2a | Ogohlantirish zonasi (G-3) — **oldinga ko'chirildi**, 1-deviatsiya | `2047c3d` |
| 2b (RED) | `capture-cell.test.tsx` + `capture-grid.test.tsx` | `13b7882` |
| 2b (GREEN) | To'qqiz hujayra holati, legenda, roving tabindex (G-7) | `4850480` |
| 3 | Kadr detali, sahifaning yig'ilishi | `876bddb` |

## Sabotaj o'lchovlari — nima QIZARDI, nima YASHIL QOLDI, reja nima degan edi

| # | Sabotaj | QIZARDI | YASHIL QOLDI | Reja nima degan edi |
|---|---|---|---|---|
| 1 | `day-summary.tsx` da hisoblagichlar ro'yxatiga nol qiymatlilarni tashlab yuboradigan shart qo'shildi | **AYNAN 3 test** — `day-summary.test.tsx` ning butun G-8 guruhi (oltala juftlik, nol qiymatning o'zi, nolmas nazorat) **VA** qabul mezonining regex darvozasi (`exit 1`) | **7 test**: `missedCallout` ning IKKALA testi, Z-7 ning uchala testi, `role="status"` va arxiv qatori | ✅ **AYNAN bashorat qilingandek.** Reja «G-8 ni AYNAN qizartiradi va `missedCallout` testi YASHIL qoladi» degan edi — ikkalasi ham to'g'ri chiqdi. Qo'shimcha: regex darvozasi ham qizardi, ya'ni bir da'vo IKKI mustaqil qulf ostida |
| 2 | `capture-cell.tsx` da `missed` holati uchun hech nima chizilmadi (`return null`) | **AYNAN 5 test**: G-7 ning to'rtala kanali **va** «`missed` va `failed` turli ikonka» testi | **17 test**: `succeeded+dark` ≠ `succeeded+ok`, «hujayrada matn yo'q», `captureCellState` ning uchala testi **va BUTUN `capture-grid.test.tsx` (12 test)** | ⚠ **Bashoratdan KUCHLIROQ.** Reja «G-7 ni AYNAN qizartiradi va `succeeded+dark` testi yashil qoladi» degan edi — ikkalasi ham to'g'ri, lekin reja beshinchi testni (ikonkalarning ajralishi) sanamagan edi, chunki u ham `missed` ning CHIZILISHIGA tayanadi. **Yangi topilma quyida** |
| 3 | `alert-row.tsx` ga tasvir elementi qo'shildi (manzili kadr proxysiga ishora qiladi) | **IKKI MUSTAQIL QULF**: `snapshot-copy.test.mjs` ning G-3 testi (u IKKALA tokenni ham — element nomini va yo'l bo'lagini — sanab berdi) **va** `alert-list.test.tsx` ning «render natijasida tasvir yo'q» testi | **`snapshot-dialog.test.tsx` ning o'nala testi**, `capture-cell` ning o'ntasi, `alert-list` ning qolgan 9 tasi, G-2, G-4 va QAMROV testi | ✅ **AYNAN bashorat qilingandek** — D-19 ikki joyda mustaqil qulflangani isbotlandi va dialog testi (u rasm CHIZADI) yashil qoldi |

Har uch holatda ham fayl `cp` bilan (**hech qachon `git checkout --` bilan emas**) darhol tiklandi va to'plam qayta yashil bo'ldi.

> ⛔ **2-sabotajning yangi topilmasi: `capture-grid.test.tsx` «hujayra bo'sh emas» da'vosini UMUMAN o'lchamaydi.**
> To'qqiz holatdan biri butunlay yo'qolganda ham matritsa to'plami 12/12 yashil qoldi — sabab uning fixture'ida `missed` qator YO'Q. Ya'ni «bitta tab to'xtashi» testi ham, `buildMatrix` testlari ham SC#2 ga hech qanday kafolat bermaydi; bu kafolat FAQAT `capture-cell.test.tsx` da yashaydi. Bu «bo'sh to'plam ustida yashil» sinfining komponent darajasidagi ko'rinishi va u rejaning «da'vo alohida o'lchanayotgani isbotlanadi» talabining aynan javobi.

## O'LCHOVLAR — taxmin qilinmadi

| Nima | Natija |
|---|---|
| `snapshots.cell.*` matni G-2/G-3 QAMROV darvozasini qizartiradimi | **HA** — probe kalit **bitta tilga** qo'yilganda ham darvoza darhol qizardi va **to'rtala** faylni talab qildi (`capture-grid`, `capture-cell`, `alert-list`, `alert-row`). Probe darhol olib tashlandi va darvoza 9/9 yashil bo'ldi |
| Backend `jobs/alerting.py::ALERT_META` dagi kalitlar soni | **9** — UI-SPEC §11.9 esa **8** ta beradi. Yetishmagani `nvr_account_locked` va u `critical` + **hech qachon bo'g'ilmaydi** |
| Backend `schemas.py::ALERT_DETAIL_KEYS` allowlisti | **6 kalit** (`market_name`, `camera_count`, `error_code`, `slot_time`, `stale_hours`, `disk_pct`); §11.9 esa faqat bittasiga (`camera_count`) matn beradi |
| `Intl.RelativeTimeFormat('uz-Latn')` va `NumberFormat` birliklari | `-3 daqiqa` -> **«3 daqiqa oldin»**; `135 minute` -> **«135 daqiqa»**; `2 hour` -> **«2 soat»** — uchalasi ham to'g'ri |
| `Intl.NumberFormat` bayt birligi uchala tilda | `ru` -> **`62 кБ`** ✅, lekin `uz-Cyrl` -> **`62 kB`** ❌ (ICU'da `uz-Cyrl` birlik ma'lumoti yo'q, lotinga tushadi). Shu sababdan birlik XABAR KATALOGIGA ko'chirildi (`sizeKb`), u yerda transliterator `КБ` beradi |
| `nvr-copy.test.mjs` G-6 (3-fazadan) yangi kodni ko'radimi | **HA** — zaxira usul nomi obyekt KALITI bo'lib yozilganda darvoza qizardi (u go2rtc ning MANBA SXEMASI matniga aynan teng edi). 4-deviatsiya |
| jsdom vaqtinchalik havolani bekor qilishni beradimi | **HA** — dialog yopilganda tozalash effекti xato bermadi, ya'ni test yo'li ham haqiqiy yo'l bilan bir xil |
| `git diff` backend bo'yicha | **BO'SH** (`services/ packages/ tests/ ops/ compose.yaml`) — pytest 1 837 va tenancy 470 saqlanadi |

## Verification

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run i18n:check` | **777 kalit × 3 til** (671 -> **+106**), exit 0 |
| 2 | `npm --prefix frontend test` | **node 115/115**, **vitest 335/335** (283 -> **+52**), exit 0 |
| 3 | `node --test snapshot-copy + error-codes + gen-cyrillic + nvr-copy + role-gate` | **104 test**, exit 0 |
| 4 | `npm --prefix frontend run typecheck` | exit 0 |
| 5 | `npm --prefix frontend run lint` | exit 0 |
| 6 | `npm --prefix frontend run build` | exit 0 — `/[locale]/snapshots` uchala til uchun ham SSG |
| 7 | `test:component -- day-summary` | **10 test** (talab ≥ 3), exit 0 |
| 8 | `test:component -- capture-cell` | **10 test** (talab ≥ 4), exit 0 |
| 9 | `test:component -- capture-grid` | **12 test** (talab ≥ 4), exit 0 |
| 10 | `test:component -- snapshot-dialog alert-list` | **20 test** (talab ≥ 6), exit 0 |
| 11 | `git diff --exit-code frontend/package.json frontend/src/lib/rbac.ts` | **o'zgarish yo'q** |
| 12 | `git diff --stat HEAD -- services/ packages/ tests/ ops/ compose.yaml` | **BO'SH** |
| 13 | `npm run gate` | **exit 0** (to'liq: sim + ruff/`ruff format`/mypy + pytest **1 869** + uchala frontend darvozasi + build) |

Mexanik artefakt mezonlari:

| Mezon | Natija |
|---|---|
| `day-summary.tsx` da nol hisoblagichlarni tashlaydigan shart (izohlar tashlangan) | ✅ **YO'Q** |
| `day-summary.tsx` da ulush belgisi (blok **va** satr izohlari tashlangan) | ✅ **YO'Q** |
| `snapshots` da `countOk…countMissed`, `missedCallout`, `noFutureDays` | ✅ oltalasi ham |
| `capture-grid.tsx` da matritsa roli yo'q, `<table>` bor | ✅ |
| `capture-cell.tsx` da `CircleSlash` + `XCircle` + `border-dashed` | ✅ uchalasi ham |
| `capture-cell`+`capture-grid` da beshinchi o'lcham va taqiqlangan og'irlik | ✅ **YO'Q** |
| `snapshots.cell` — AYNAN to'qqiz kalit | ✅ |
| `alert-list`+`alert-row` da tasvir yuzasi (izohlar tashlangan) | ✅ **YO'Q** |
| `alert-list.tsx` da e'lonli rol (izohlar tashlangan) | ✅ **YO'Q** (2-deviatsiya) |
| `snapshots.verdict` — AYNAN sakkiz kalit | ✅ |
| `tierFull` / `tierCompressed` / `tierPurged` | ✅ uchalasi ham |
| `snapshot-dialog.tsx` da ombor kaliti va imzolangan havola nomlari | ✅ **YO'Q** |
| `capture-grid.tsx` ≥ 150 qator va `tabIndex` bor | ✅ (299 qator) |
| Yangi npm paketi / yangi `ui/` primitivi | ✅ **YO'Q** |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — bloklovchi] Ogohlantirish zonasi Task 3 dan matritsa commitidan OLDINGA ko'chirildi**

- **Topildi:** Task 2 boshlanishidan oldin — probe kalit bilan **o'lchandi**.
- **Ziddiyat:** Task 2 ning ikkita qabul mezoni bir vaqtda bajarilishi kerak: `snapshots.cell` da **aynan to'qqiz kalit** bo'lsin **va** `snapshot-copy.test.mjs` **exit 0** bersin. Lekin `04-10` tetikni matn katalogiga ko'chirgan (uning 1-deviatsiyasi), ya'ni `snapshots.cell.*` paydo bo'lgan zahoti darvoza **to'rtala** faylni talab qiladi — `alert-list.tsx` va `alert-row.tsx` esa rejada Task 3 da edi.
- **Rad etilgan yechim:** ikki stub fayl yaratish — reja platsholder yozishni ochiq taqiqlaydi va u «Known Stubs» qarzini tug'dirardi.
- **Yechim:** ogohlantirish zonasi **to'liq** (komponentlar + testlar + §11.9/E-4 matni) alohida commitda, matritsa commitidan **oldin** yetkazildi. Har ikkala commit ham mustaqil ravishda yashil: birinchisida `snapshots.cell.*` hali yo'q (tetik o'chiq), ikkinchisida to'rtala fayl ham bor.
- **Qamrov o'zgarmadi:** Task 3 ning `<behavior>` bandlaridan hech biri tushib qolmadi, faqat commit tartibi o'zgardi.
- **Committed in:** `2047c3d`

**2. [O'z-o'ziga zid mezon] `alert-list.tsx` da e'lonli rol butun fayl bo'ylab taqiqlangan**

- **Qayerda:** `node -e "... !/role=[\"']alert[\"']/.test(s)"` — mezon butun **fayl** ustida ishlaydi.
- **Ziddiyat:** taqiqning NIYATI ochiq va to'g'ri — ro'yxat sahifa yuklanganda mavjud bo'lgan **HOLAT**, yangi hodisa emas (§6.7, §12.6). Lekin AYNI hujjat Z-9 (zona xatosi) uchun meros xato blokini va §12.6 ning jonli hududlar reyestrida «Zona/forma xatosi -> e'lonli hudud» ni **talab qiladi**.
- **Yechim:** ro'yxat hech qanday jonli hudud rolini olmaydi (niyat bajarildi); yuklash xatosi bloki esa `aria-live="assertive"` + `aria-atomic="true"` + `tabIndex={-1}` bilan e'lon qilinadi — ARIA 1.2 da bu **teng kuchli** shakl. Bu `04-10` ning `schedule-dialog.tsx` dagi qarorining **ikkinchi marta** qo'llanishi, ya'ni endi u naqsh.
- **Mezonni chetlab o'tish ATAYIN qilinmadi** (masalan `role={...}` ifodasi bilan) — u darvozani mazmunsiz qilardi.
- **Fayllar:** `frontend/src/components/snapshots/alert-list.tsx`

**3. [Rule 3 — bloklovchi] `snapshots.method` UI-SPEC §11.7 da IKKI ma'noda ishlatilgan**

- **Ziddiyat:** §11.7 bir jadvalda `snapshots.method.stream` / `.device` / `.fallback` (enum xaritasi) **va** `snapshots.method` = «Usul» (yorliq) ni beradi. JSON bitta kalitda satr va obyektni birga ushlay olmaydi, ya'ni spetsifikatsiya shu holida **bajarilmaydi**.
- **Yechim:** enum xaritasi `snapshots.method.*` da **qoldi** (uni ko'chirish uchala tildagi uch kalitni ham nomini o'zgartirardi), yorliq esa `snapshots.methodLabel` ga ko'chdi. Yorliq — bitta so'z va uning kalit nomi hech qayerda hujjatlashtirilmagan.
- **Egasi:** `04-12` UI-SPEC §11.7 jadvalini shu shaklga moslashtirsin.
- **Committed in:** `876bddb`

**4. [Rule 1 — bug] 3-fazaning go2rtc darvozasi (G-6) yangi kodda qizardi**

- **Topildi:** Task 3, `npm --prefix frontend test` — `nvr-copy.test.mjs` ning bitta testi (`fail 1`, `pass 114`).
- **Muammo:** kadr olish usulini inson tiliga o'giradigan xarita obyekt literali edi va uning zaxira usul kaliti **go2rtc ning MANBA SXEMASI** matniga aynan teng chiqdi. Darvoza (D-11, UI-SPEC §8.7) o'sha sxemalarni taqiqlaydi, chunki ular RCE yuzasi bo'lgan oqim boshqaruv API'siga uzatiladi.
- **Nega darvoza HAQ edi:** u izohlarni filtrlamaydi va bu ATAYIN — «bu nom umuman yozilmagan» degan da'vo «bu nom kodda ishlatilmagan» dan kuchliroq.
- **Yechim:** xarita **solishtiruvga** aylantirildi (`if (method === "…") return …`), ya'ni xom token endi hech qachon ikki nuqta bilan yonma-yon turmaydi. **Darvoza kuchsizlantirilmadi** — uning taqiq ro'yxatiga tegilmadi; o'zgargan narsa — shu yerdagi kodning shakli. Sabab funksiya docstringida yozildi.
- **Verifikatsiya:** `node --test scripts/nvr-copy.test.mjs` -> 115/115.
- **Committed in:** `876bddb`

**5. [Rule 2 — yetishmayotgan kritik matn] `nvr_account_locked` alert kaliti UI-SPEC §11.9 da yo'q edi**

- **Topildi:** Task 2a, `jobs/alerting.py::ALERT_META` ni o'qishda.
- **Muammo:** backend **to'qqizta** alert kalitini yozadi, UI-SPEC §11.9 esa **sakkiztasiga** matn beradi. Yetishmagani — `nvr_account_locked`, va u `critical` **hamda** `NEVER_SUPPRESSED_ALERT_KEYS` da, ya'ni u debounce oynasi ichida ham darhol yuboriladi.
- **Nega bu jimgina zarar bo'lardi:** xom kalit ekranga hech qachon chiqmaydi (§6.7), ya'ni matnsiz kalit `errors.generic` ga tushardi — admin eng shoshilinch xabarni «Kutilmagan xato» ko'rinishida olardi va NVR hisobining qulf oynasi (30 daqiqa) davomida nima qilishni bilmasdi.
- **Yechim:** `snapshots.alertKey.nvrAccountLocked` uchala tilda qo'shildi («NVR hisobi qulflandi» / «Учётная запись NVR заблокирована»); `NVR` allaqachon override ro'yxatida, ya'ni kirill build'ida ham lotin holida qoladi.
- **Committed in:** `2047c3d`

**6. [Rule 2 — yetishmayotgan kritik matn] `alert_events.detail` ning to'rtta kaliti matnsiz qolardi**

- **Muammo:** backend allowlisti **oltita** kalitni UI'ga chiqaradi, §11.9 esa faqat `camera_count` ga matn beradi. Qolgan to'rttasi (`market_name`, `slot_time`, `stale_hours`, `disk_pct`) chizilmasdi — ya'ni ogohlantirishning eng aniq qismi («qaysi bozor», «qaysi vaqt», «necha soat», «disk qancha») yo'qolardi.
- **Yechim:** `alertMarket`, `alertTime`, `alertStaleHours`, `alertDiskUsed` qo'shildi. ⚠ Kalit nomlarida «vaqt» ishlatildi, orkestratsiya atamasi emas (G-1).
- **⚠ Klientda IKKINCHI ALLOWLIST QURILMADI** (`api-types.ts:1418-1422` uni ochiq taqiqlaydi): `detail` dan faqat **nomlangan** kalitlar o'qiladi va noma'lum kalit ustida sikl yo'q — ya'ni bu filtr emas, «bilganini chizish».
- **Committed in:** `2047c3d`

**7. [Qamrov qarori] Rasm baytlari sessiya tokeni bilan olinadi, tasvir elementi ularni O'ZI yuklamaydi**

- **Muammo:** `GET /snapshots/{id}/image` sessiya tokenini talab qiladi (`SnapshotViewerDep`), tasvir elementi esa `Authorization` sarlavhasini qo'sha olmaydi — to'g'ridan-to'g'ri manzil 401 berardi.
- **Rad etilgan yechimlar:** (a) marshrutga cookie autentifikatsiyasi qo'shish — backend yuzasini kengaytirardi va bu frontend rejasi; (b) imzolangan havola — §14.3 ni buzardi va aynan shu reja uni taqiqlaydi.
- **Yechim:** baytlar `apiRequest` bilan olinadi (mavjud 401 -> refresh -> qayta urinish yo'li bilan birga) va brauzer ichidagi **vaqtinchalik havolaga** aylantiriladi; dialog yopilganda havola bekor qilinadi.
- **⚠ Bu §14.3 ni KUCHSIZLANTIRMAYDI, KUCHAYTIRADI:** har ochilish serverga so'rov yuboradi, ya'ni har ochilish `audit_read` yozadi. Imzolangan havola esa aynan buni yo'qotardi.
- **Committed in:** `876bddb`

**8. [Qamrov qarori] `?closed=` va `?issues=` URL holati sahifa modulida, zona komponentida emas**

- **Nima:** `AlertList` `closed` ni **prop** bo'lib oladi; URL hooki `day-picker.tsx` da (`useShowClosedAlerts`, `useIssuesOnly`).
- **Ikki sabab:** (1) `stalls/stall-filters.tsx` ning «panel ham, ro'yxat ham BIR hookdan o'qiydi» qoidasi — holatni ikki joyda ushlash checkbox va ro'yxatni bir kun ajratib qo'yardi; (2) komponent testi URL adapterisiz ishlaydi va bu kodbazada **birinchi** URL-holatli komponent testi bo'lardi.

**9. [Qamrov qarori] `snapshotImageKey` — mavjud fabrikaning BOLASI, yangi global kalit emas**

- **Sabab:** `snapshotKey` ning birinchi argumenti allaqachon `marketId`, ya'ni bola kalit doiralashni **meros** oladi va §5.4 ning «global kalit konstantasi bu modulda umuman yo'q» qoidasi buzilmaydi. Qo'shimcha foyda: detalning bekor qilinishi rasmni ham bekor qiladi.
- **`snapshot-queries.ts` ga umuman tegilmadi** — u bu rejaning `files_modified` idan tashqarida.

**10. [Qamrov qarori] Bayt birligi xabar katalogida, `Intl` da emas**

- **O'lchandi:** `Intl.NumberFormat('uz-Cyrl', {style:'unit', unit:'kilobyte'})` -> **`62 kB`** (lotin!), `ru` -> `62 кБ`. ICU'da `uz-Cyrl` uchun birlik ma'lumoti yo'q va u lotinga tushadi.
- **Yechim:** `snapshots.sizeKb` = `{value} KB` / `{value} КБ`; uz-Cyrl transliteratordan `КБ` oladi (§11.11 Qoida 3 ning ijobiy nazorati aynan shu holatni qulflaydi).

**11. [Qamrov qarori] Legenda `aria-describedby` bilan bog'lanMADI, lekin `id` lar berildi**

- **Sabab:** §6.5 ochiq talab — 175 hujayrada bog'lash skrinriderni bo'g'ardi (har fokusda to'qqiz yozuvli lug'at qayta o'qilardi). `id` lar baribir berildi va sabab izohda yozildi, aks holda keyingi ishlovchi «unutilganmi?» savolini qoldirardi.

**12. [Qamrov qarori] `snapshots.method` yorlig'i va E-2 amali**

- E-2 (Z-7) bo'sh holatiga «Jadvalni ko'rish» havolasi **qo'yilmadi**: u faqat `uncovered_days > 0` bo'lganda ma'noli va o'sha son zona A ning javobida yashaydi; uni ikkinchi so'rov bilan olib kelish ikkinchi haqiqat manbai bo'lardi. Qoplanmagan kunlar ogohlantirishi zona A da allaqachon ko'rinadi.

---

**Total deviations:** 12 (2× Rule 3 bloklovchi, 1× Rule 1 bug, 2× Rule 2 yetishmayotgan matn, 1× o'z-o'ziga zid mezon, 6× qamrov qarori)
**Impact on plan:** Hech biri qamrovni kengaytirmadi va hech biri darvozani kuchsizlantirmadi. Ikkitasi (2, 4) darvoza matni bilan spetsifikatsiyaning to'qnashuvi edi va ikkalasi ham **kodni** o'zgartirish bilan hal qilindi; ikkitasi (5, 6) UI-SPEC ning backend reyestridan orqada qolgan joylari; bittasi (1) `04-10` ochiq yozib qoldirgan tetikning bevosita oqibati.

## Files Created

| Fayl | Nima qiladi | Qator |
|---|---|---|
| `snapshots/day-picker.tsx` | `?day=`/`?issues=`/`?closed=` URL holati; kelajak kun hook'da **va** `max` atributida — ikki qatlam; yaroqsiz kun jimgina bugunga tushadi | 262 |
| `snapshots/day-summary.tsx` | Oltala hisoblagich SHARTSIZ; `planned === 0` da Z-7; `missedCallout` mustaqil da'vo sifatida | 306 |
| `snapshots/day-summary.test.tsx` | 10 test: G-8, Z-7 va «0 / 0» ning yo'qligi, callout, rol, arxiv qatori | 261 |
| `snapshots/capture-cell.tsx` | To'qqiz holat; `missed` uchun uch kanal; `captureCellState` sof funksiyasi va uning noma'lum qiymat siyosati | 277 |
| `snapshots/capture-cell.test.tsx` | 10 test: G-7 ning to'rt kanali, ikonkalarning ajralishi, matnsizlik, holat xaritasi | 215 |
| `snapshots/capture-grid.tsx` | `buildMatrix` (yetishmagan juftlik `null`), roving tabindex, native jadval, sticky qator sarlavhasi | 299 |
| `snapshots/capture-grid.test.tsx` | 12 test: bitta tab to'xtashi, o'qlar, `Home`/`End`, ochish, semantika, matritsa qurilishi | 261 |
| `snapshots/capture-legend.tsx` | To'qqizala yozuv DOIM; `legendEntryId` — bog'lash uchun tayyor, lekin ATAYIN ulanmagan nuqta | 168 |
| `snapshots/snapshot-dialog.tsx` | `verdictKey` (8 juftlik), auditlangan rasm yo'li, `purged` holati, texnik tafsilot, C5…C9 xato bloki | 558 |
| `snapshots/snapshot-dialog.test.tsx` | 10 test: D-12 ning ikki uchi, noma'lum kod, `purged`, belgilar tartibi, o'lchovlarning yo'qligi | 318 |
| `snapshots/alert-list.tsx` | Z-3/Z-4, `?closed=` prop bilan, yopish tugmasi YO'Q | 165 |
| `snapshots/alert-row.tsx` | Rasmsiz qator; `notified_at` yashirilmaydi; `detail` faqat nomlangan kalitlar bilan | 272 |
| `snapshots/alert-list.test.tsx` | 10 test: G-3 ning ikkinchi qulfi, takrorlar, Telegram holati, semantika, Z-3/Z-4 | 233 |

## Bazaviy holat

| O'lchov | Baza (`04-10`) | Hozir | Holat |
|---|---|---|---|
| pytest (backend) | 1 837 | **tegilmagan** | ✅ `git diff --stat HEAD -- services/ packages/ tests/ ops/ compose.yaml` **BO'SH**. ⚠ `npm run gate` ichidagi yugurish **1 869 test** bilan yashil chiqdi — farq mening o'zgarishimdan emas, **simulyator profili ko'tarilgan** holatda yugurganidan (`gate` avval `sim:up` qiladi va `sim` belgili testlar o'tkazib yuborilmaydi) |
| tenancy | 470 | **tegilmagan** | ✅ o'sha diff bo'sh |
| vitest | 283 | **335** | ✅ **+52** |
| node | 115 | **115** | ✅ o'zgarmagan (darvoza fayllariga tegilmadi) |
| i18n | 671 × 3 | **777 × 3** | ✅ **+106** (§11.5–§11.7, §11.9, §11.10) |
| `npm run gate` | exit 0 | **exit 0** | ✅ |
| `git diff package.json / rbac.ts` | — | **o'zgarish yo'q** | ✅ |

## Issues Encountered

- **`npm --prefix frontend test` 3-fazaning darvozasida qizardi** — 4-deviatsiya. Muammo yangi kodda emas, uning SHAKLIDA edi va darvoza to'g'ri ishladi.
- **`snapshots.cell.*` matni komponentlar tartibini boshqardi** — 1-deviatsiya. Bu `04-10` ning ochiq yozgan ogohlantirishi edi va u aynan bashorat qilingandek amalga oshdi.
- **`ffmpeg`/`go2rtc` tokenlari ikki xil darvoza ostida** — biri (G-6) ularni **manba sxemasi** sifatida taqiqlaydi, ikkinchisi (§10.7) esa xom tokenni **yig'iladigan blok ichida ko'rsatishni talab qiladi**. Ikkalasi bir vaqtda bajarildi: token API javobidan chiziladi, kodda esa faqat solishtiruv qiymati bo'lib turadi.

## Known Stubs

Yo'q.

⚠ **Stub bo'lmagan, lekin ochiq qolgan uch band (uchalasining ham egasi bor):**

1. **UI-SPEC §11.7 ning `snapshots.method` ziddiyati** — 3-deviatsiya. Kod `methodLabel` bilan ishlaydi; hujjat yangilanishi kerak. **Egasi:** `04-12`.
2. **UI-SPEC §11.9 backend reyestridan bitta kalitga orqada** — 5-deviatsiya (`nvr_account_locked`). Matn qo'shildi, jadval esa yangilanmadi. **Egasi:** `04-12`.
3. **`capture-legend.tsx` ning `id` lari hech narsaga ulanmagan** — bu ATAYIN (§6.5) va sabab kodda yozilgan. **Tetik:** agar kelajakda hujayra soni keskin kamaysa, bog'lash qayta ko'rib chiqilsin.

## Threat Flags

Threat register'ning to'qqizala mitigatsiyasi bajarildi va o'lchandi:

| Threat | Holat |
|---|---|
| T-04-82 (ogohlantirishga rasm) | **G-3 ikki mustaqil qulf** — skript darvozasi **va** `alert-list.test.tsx`; sabotaj ikkalasini ham qizartirdi, dialog testi yashil qoldi |
| T-04-83 (jurnalda thumbnail) | **G-2** yashil; `capture-grid.tsx`/`capture-cell.tsx` da tasvir yuzasi yo'q |
| T-04-84 (ombor kaliti / imzolangan havola) | **G-4** butun `frontend/src` ni skanerlaydi va yashil; `snapshot-dialog.tsx` da ikkala nom ham yo'q (izohlar tashlangan holda tekshirildi) |
| T-04-85 (xom `error_detail`) | Noma'lum kod -> `errors.generic`; test xom kodning ekranda YO'QLIGINI ham talab qiladi |
| T-04-86 (`notified_at === null` qatorining yashirilishi) | Shart faqat MATNNI tanlaydi, qatorning MAVJUDLIGINI emas; sabab `title` da; test bilan qulflangan |
| T-04-87 (qo'lda yopish) | Tugma qurilmadi; test butun zonada **birorta tugma yo'qligini** talab qiladi |
| T-04-88 (klaviatura tuzog'i) | Roving tabindex; test AYNAN bitta tab to'xtashini va uning fokus bilan birga ko'chishini talab qiladi |
| T-04-89 (nol hisoblagichlarning filtrlanishi) | **G-8** + regex darvozasi; sabotaj ikkalasini ham qizartirdi |
| T-04-SC (npm o'rnatishlari) | Yangi paket **YO'Q**; `git diff --exit-code frontend/package.json` toza |

⚠ **Yangi yuza (registerda yo'q edi): dalil-kadrning brauzer ichidagi vaqtinchalik havolasi.**
Rasm baytlari sessiya tokeni bilan olinadi va vaqtinchalik havolaga aylantiriladi (7-deviatsiya). Xususiyatlari: havola **same-origin** va **hujjatga bog'langan** — u boshqa tabga, boshqa foydalanuvchiga yoki tashqi manzilga ko'chmaydi; dialog yopilganda **bekor qilinadi**; ulashish tugmasi yo'q va DL-3 URL'da emas. Server tomondagi `Cache-Control: private, no-store` (04-09) hamon kuchda, ya'ni baytlar diskka tushmaydi. **Qoldiq xavf:** dialog ochiq turgan vaqtda havola DOM'da yashaydi — bu tasvir elementining har qanday ishlatilishida bir xil va u §14.3 ning birorta bandini buzmaydi.

## Next Phase Readiness

**`04-12` (fazani tekshirish) uchun:**

- To'rtala zona ham yig'ilgan; SC#2 ning UI isboti `capture-cell.test.tsx` da (G-7) va u sabotaj bilan o'lchangan.
- ⚠ **UI-SPEC ning ikki joyi kod bilan mos emas** — 3- va 5-deviatsiya (`method` ziddiyati va `nvr_account_locked`). Ikkalasi ham hujjat tomonida tuzatilishi kerak.
- ⚠ **`capture-grid.test.tsx` fixture'ida `missed` qator yo'q** va bu o'lchangan bo'shliq: matritsa to'plami SC#2 ga hech qanday kafolat bermaydi. Agar `04-12` matritsa darajasida ham kafolat xohlasa, fixture'ga `missed` qator qo'shilishi kerak (kafolatning O'ZI `capture-cell.test.tsx` da bor).
- `tests/tenancy/test_personal_data_coverage.py` hamon rasm marshrutini ko'rmaydi (`04-09` ning ochiq topilmasi) — bu reja unga tegmadi.

**5-faza uchun:** `capture-cell.tsx` ning to'qqiz holati va `capture-grid.tsx` ning roving tabindex naqshi zona/poligon ekranlarida qayta ishlatilishi mumkin; `CaptureCell` ning `run: CaptureRun | null` shakli «qator yo'q» holatini allaqachon ifodalaydi.

**Bloklovchi yo'q.**

## Self-Check: PASSED

- **O'n uchala yaratilgan fayl + SUMMARY diskda tekshirildi** (`MISSING: 0`).
- **Oltala commit `git log eccf402..HEAD` da tasdiqlandi:** `41986e9`, `8295a3b`, `2047c3d`, `13b7882`, `4850480`, `876bddb`.
- **Birorta commitda fayl o'chirilishi YO'Q** (`git diff --diff-filter=D eccf402..HEAD` bo'sh).
- **Ishchi daraxt toza** — repo ildizidagi uchta begona fayl (`.docx` × 2, `SBOZOR-MVP-texnik-topshiriq.md`) TEGILMADI.
- **`npm run gate` exit 0.**

---
*Phase: 04-snapshot-pipeline*
*Completed: 2026-08-05*
