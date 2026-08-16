---
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
plan: 10
subsystem: frontend
tags: [reconciliation, snapshots, i18n, a11y, tenant-guard, tdd]
requires:
  - "08-03 (frontend/messages/*.json — hisobot kontrakti)"
provides:
  - "lib/format-day.ts — sana-faqat qiymatning YAGONA yordamchisi (mintaqadan mustaqil)"
  - "lib/vendor-labels.ts — to'liq sahifalangan ism lug'ati + MAX_LABEL_PAGES chegarasi"
  - "useReconciliationMarketId() — recon bloklari uchun tenant qo'riqchisi"
  - "ALERT_TITLE_KEYS eksporti — reyestrdan render-holida o'lchash imkoni"
affects:
  - "frontend/src/components/reconciliation/** (beshala blok)"
  - "frontend/src/components/snapshots/alert-row.tsx"
tech-stack:
  added: []
  patterns:
    - "Noma'lum enum -> NOMLANGAN zaxira yorliq (case-status-badge naqshi alert yuzasiga kengaytirildi)"
    - "O'lchanmagan qiymat -> element UMUMAN chizilmaydi (D-10), na 0, na «—»"
    - "Sana-faqat qiymat 12:00 UTC ga langarlanadi (ofset < 12 da barqaror)"
    - "Sahifalangan fon so'rovi useEffect da + qattiq sahifa chegarasi (audit shovqini)"
key-files:
  created:
    - frontend/src/lib/format-day.ts
    - frontend/src/lib/format-day.test.tsx
    - frontend/src/lib/vendor-labels.test.tsx
  modified:
    - frontend/src/components/snapshots/alert-row.tsx
    - frontend/src/components/snapshots/alert-list.test.tsx
    - frontend/src/components/reconciliation/unpaid-list.tsx
    - frontend/src/components/reconciliation/unregistered-list.tsx
    - frontend/src/components/reconciliation/case-list.tsx
    - frontend/src/components/reconciliation/case-detail-dialog.tsx
    - frontend/src/components/reconciliation/hit-rate-card.tsx
    - frontend/src/components/reconciliation/delivery-list.tsx
    - frontend/src/lib/reconciliation-queries.ts
    - frontend/src/lib/vendor-labels.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
decisions:
  - "WR-15 SERVER TOMONIDA TUZATILMADI: `CaseUpdate.resolution_note` da `min_length` yo'q, ya'ni bo'sh satr 422 bermaydi va `COALESCE('', …)` = `''` — matn HAQIQATAN o'chadi. Klient tomoni yetarli."
  - "WR-07 yordamchisi `lib/format-day.ts` da (rejaning fayl ro'yxatidan tashqarida) — ko'rikning O'Z tavsiyasi; muqobillar (recon-queries yoki day-picker) semantik jihatdan noto'g'ri joy edi."
  - "07 №2 mexanikasi — MAVJUD `GET /vendors` marshrutini sahifalash (D-08 ning ikkinchi ruxsati). Recon marshrutiga `vendor_name` QO'SHILMADI."
  - "IN-02 3-vazifada emas, 2-vazifada bajarildi: uning fayllari (`case-list`, `delivery-list`) o'sha vazifaning fayl to'plamida."
metrics:
  duration: "~55 daqiqa"
  completed: 2026-08-16
  tasks: 3
  commits: 7
  tests_before: 1004
  tests_after: 1039
---

# Phase 8 Plan 10: 7-fazadan meros frontend ogohlantirishlari Summary

7-fazaning o'nta ko'rik bandi (WR-05/07/11/12/13/15 + IN-02/03/04/08) va ikki
`deferred-items` bandi yopildi: ekran endi noma'lum server qiymatini yashirmaydi,
o'lchanmagan sonni «0» qilib ko'rsatmaydi va 50-chi sotuvchidan keyingi ismlarni
ham chizadi.

## Nima qilindi

### 1-vazifa — alert yuzasi (WR-11, WR-12, IN-03, 07 №1-qo'shimcha)

| Band | Qanday yopildi |
|---|---|
| **WR-11** | `??` refleksi olib tashlandi. `SEVERITY_VIEW` endi `Record<AlertSeverityValue, …>` (reyestrga to'rtinchi daraja qo'shilsa `tsc` qizaradi) + `isAlertSeverity()` qo'riqchisi. Noma'lum daraja `tone="neutral"` + `snapshots.severityUnknown` oladi — xom kalit ham, `info` ko'k nishoni ham EMAS. |
| **WR-12** | `alertDurationParts()` yaroqsiz satrda `null` qaytaradi (`parseInstant()` yordamchisi). Yopilish lahzasi va davomiylik ⛔ IKKI MUSTAQIL shoxda chiziladi: biri o'qilmasa, ikkinchisi yo'qolmaydi. Na `0`, na «—». |
| **IN-03** | Eskirgan «o'n bitta» izohi RAQAMSIZ shaklga o'tdi: reyestr manzili + `ALERT_TITLE_KEY_COUNT` qulfiga ishora (raqam yozilsa yana eskirardi). |
| **07 №1-qo'shimcha** | `ALERT_TITLE_KEYS` eksport qilindi; `alert-list.test.tsx` reyestrdan ITERATSIYA qilib har a'zoni render holida o'lchaydi + qamrov nazorati 07-14 ning to'rt kalitini reyestrda talab qiladi + reyestrdan tashqaridagi kalit zaxira yorliqni olishi alohida o'lchanadi. |

**O'LCHANGAN TOPILMA (rejada yo'q edi):** eski `NaN` ekranda `NaN` bo'lib
ko'rinmasdi — `Intl` uni LOCALE'GA TARJIMA qiladi va uz-Latn da qator
«**son emas** soat davom etdi» bo'lib chizilardi. Ya'ni faqat ASCII `NaN` ni
qidiradigan darvoza bu nosozlikni UMUMAN ko'rmasdi. Test ikkala shaklni ham
tekshiradi.

### 2-vazifa — nomuvofiqlik yuzasi (WR-07, WR-13, WR-15, IN-04, IN-08 + IN-02)

| Band | Qanday yopildi |
|---|---|
| **WR-07** | Yangi `lib/format-day.ts`: `isoDayToDate()` kunni **12:00 UTC** ga langarlaydi + `formatBusinessDay(format, day)`. Mo'rt ofsetsiz shakl katalogdan YO'Q QILINDI (`grep` → 0). To'rtala joy (`unregistered-list`, `case-detail-dialog`, `case-list`, va izchillik uchun `delivery-list`) shu yordamchidan o'qiydi. SSR/CSR gidratatsiya nomuvofiqligi ham shu bilan yopildi. |
| **WR-13** | `isSubjectKind()` NIHOYAT chaqiriladi (ilgari 0 iste'molchi). Noma'lum sinf qatorlari IKKALA blokda ham `recon.subjectUnknownNotice` bilan sanoq farqi qilib e'lon qilinadi va BIRORTA jadvalga tiqilmaydi. |
| **WR-15** | `resolutionNote: note.trim()` — bo'sh matn `null` emas, BO'SH SATR. Mutatsiya tipi ham `string` ga toraytirildi, ya'ni nuqson izohga emas, TIP TIZIMIGA bog'landi. |
| **IN-04** | `[Yangilash]` `aria-disabled` + `onClick` da erta `return` (`case-list.tsx` naqshi). `grep " disabled="` → 0. |
| **IN-08** | `useReconciliationMarketId()` eksport qilindi; beshala blok bozorsiz sessiyada NOMLANGAN holat (`recon.marketMissing` + hint) chizadi va so'rov UMUMAN yubormaydi. `role="status"` soni O'ZGARMADI (G-38 darvozasi hamon 6 ta). |
| **IN-02** | `case-list.tsx` va `delivery-list.tsx` dagi keraksiz `as` assertsiyalari olib tashlandi. |

**SERVER TEKSHIRILDI VA TEGILMADI (WR-15 ning ⚠ bandi):**
`app/schemas.py::CaseUpdate.resolution_note` — `Annotated[str,
StringConstraints(max_length=…)] | None`, ya'ni `min_length` **YO'Q** → bo'sh
satr `422` bermaydi. `reconciliation_repo._UPDATE_CASE_STATUS` dagi
`COALESCE(:note, resolution_note)` esa bo'sh satrni `NULL` deb o'qimaydi
(`COALESCE('', …) = ''`) → matn HAQIQATAN o'chadi. Server tuzatish
**talab qilmadi**.

**YON TA'SIR TUZATILDI (Rule 1):** marshrut ayni maydonni tarix qatorining
izohi qilib ham yozadi, ya'ni «tozalash» amali audit izida BO'SH `<span>`
qoldirardi. Endi `null` ham, bo'sh satr ham chizilmaydi.

### 3-vazifa — ism bo'shlig'i (07 №2) va WR-05

| Band | Qanday yopildi |
|---|---|
| **07 №2** | `useVendorLabels` `fetchNextPage()` bilan reestrni TO'LIQ sahifalaydi. **Qo'riqchi 1:** `MAX_LABEL_PAGES = 20` (audit shovqini D-09 + cheksiz halqa). **Qo'riqchi 2:** chegaradan keyin `labelOf()` → `null`, ya'ni BO'SH katak (to'qilgan qiymat YO'Q — DOM da'vosi + manba skani). So'rov `useEffect` da, render paytida EMAS (StrictMode uni ikkilantirardi). Kesh kaliti va `staleTime` TEGILMADI. |
| **WR-05** | Yiqilgan so'rov endi `errors.loadFailedBody` ni `role="alert"` ichida chizadi. `recon.accuracyNone` («Hali hal qilingan nomuvofiqlik yo'q» — O'LCHANGAN FAKT DA'VOSI) o'sha shoxdan olib tashlandi. Nolga tushiruvchi zaxira operatorlari kodda 0 marta. |

## O'LCHOVLAR

### Audit shovqini (07 №2 ning ochiq narxi — reja RAQAM talab qildi)

| Ssenariy | `GET /vendors` so'rovlari |
|---|---|
| 1 sahifali bozor (≤50 sotuvchi) | **1** (o'zgarmadi) |
| 120 sotuvchi (Karmana konverti) | **3** |
| Server kursori tugamaydi | **AYNAN 20** va u O'SMAYDI |

Ya'ni Karmana pilotida (~300–1000 rasta, sotuvchi soni undan kam) qo'shimcha
narx **sahifa boshiga 1 `audit_read`**, jami ≤6 yozuv. Chegara amaliyotda
urilmaydi (20 × 50 = 1000 sotuvchi). Muqobil (`/reports/receivables` dan ism
olish) **kerak bo'lmadi** — o'lchov qabul qilinadigan darajada chiqdi.

### Sabotaj (majburiy — WR-05) va qo'shimcha zondlar

| # | Sabotaj | Natija |
|---|---|---|
| 1 | `hit-rate-card` xato shoxi nolga tushiruvchi zaxiraga almashtirildi | ⛔ QIZIL — `role="alert"` da'vosi yiqildi |
| 2 | maxraj-nol shoxi o'chirildi, foiz MAJBURAN chizildi | ⛔ QIZIL — **to'rt** darvoza bir vaqtda: foiz belgisi soni, `0` satri, `accuracyNone` nazorati, «`0`/`NaN`/`Infinity` yo'q» bandi |
| 3 | `outbox_stale` `ALERT_TITLE_KEYS` reyestridan olib tashlandi | ⛔ QIZIL — qamrov nazorati (07-14 ning to'rt kaliti) |
| 4 | alert sarlavhasi DOIM `errors.generic` ga tushirildi | ⛔ QIZIL — render testi + G-3 darvozasi |

Hammasi qaytarildi; yakuniy holat yashil.

### Darvozalar

| Buyruq | Natija |
|---|---|
| `npm --prefix frontend test` | **EXIT 0** — 272 node test + 1039 vitest (boshlanishida 1004) |
| `npm --prefix frontend run i18n:check` | **EXIT 0** — 1329 kalit × 3 til |
| `npm --prefix frontend run typecheck` | **EXIT 0** |
| `npm --prefix frontend run lint` | **EXIT 0** |
| `node --test frontend/scripts/snapshot-copy.test.mjs` | **EXIT 0** — 13/13 |

### Qabul mezonlari (`grep` bilan)

| Mezon | Kutilgan | Natija |
|---|---|---|
| `SEVERITY_VIEW.info` in `alert-row.tsx` | 0 | **0** |
| `Number.isFinite` in `alert-row.tsx` | ≥1 | **2** |
| `T00:00:00` in `components/reconciliation/*.tsx` | 0 | **0** |
| `isSubjectKind` in `components/reconciliation/` | ≥1 | **2 fayl** |
| ` disabled=` in `delivery-list.tsx` | 0 | **0** |
| to'qilgan qiymat in `vendor-labels.ts` (kod) | 0 | **0** |
| nolga tushiruvchi zaxira in `hit-rate-card.tsx` | 0 | **0** |
| `fetchNextPage` + chegara konstantasi in `vendor-labels.ts` | bor | **bor** |

## D-25 (yangi alert kaliti qo'shilmagan) — VA REJA MATNIDAN FARQ

⚠ **Reja `ALERT_TITLE_KEY_COUNT = 15` deb yozgan; haqiqiy qulf — `16`.**
Sanoq 08-10 ijrosidan OLDIN ham 16 edi: 07-21 «Topilma №I» bilan
`notification_stale` kaliti qo'shilgan va u ijro boshlanishidagi bazada
(`6e3ac5f`) allaqachon bor. Reja matni o'sha o'zgarishdan oldingi sanoqni
ko'chirgan.

**Muhimi bajarildi:** bu reja ⛔ BIRORTA yangi alert kaliti QO'SHMADI, ya'ni
qulf **o'zgarmadi** (`16` → `16`) va D-25 hurmat qilindi.

## Rejadan chetlanishlar

### 1. Yangi fayl: `frontend/src/lib/format-day.ts` (reja fayl ro'yxatida yo'q)

Reja WR-07 uchun «mavjud `businessDayIn` oilasidan yoki `useFormatter().dateTime`
bilan `timeZone` aniq berilgan holda» degan. Uchala muqobil ham ko'rib chiqildi:

* `reconciliation-queries.ts` ga qo'yish — u **server holati** moduli; sana
  formatlagichi u yerda semantik jihatdan begona bo'lardi va taqiqlangan
  nomlar skanining maydonini kengaytirardi;
* `components/snapshots/day-picker.tsx` ga qo'yish — reja ro'yxatidan
  **baribir tashqarida** va recon katalogini snapshots katalogiga bog'lardi;
* har komponentda ikki qatorlik naqshni takrorlash — WR-07 ning O'ZI
  shikoyat qilayotgan «bir maydon, uch shakl» holatini qaytarardi.

Tanlangan yo'l — **ko'rikning O'Z tavsiyasi** (`07-REVIEW-frontend.md:545-554`
`lib/format-day.ts` ni nomma-nom taklif qiladi). Yangi fayl birorta mavjud
darvozaning qamroviga tegmaydi.

### 2. IN-02 3-vazifada emas, 2-vazifada

Reja IN-02 ni 3-vazifa sarlavhasiga qo'ygan, lekin uning fayllari
(`case-list.tsx`, `delivery-list.tsx`) 2-vazifaning `<files>` ro'yxatida.
Tuzatish o'sha commitda bajarildi.

### 3. `delivery-list.tsx` ham WR-07 yordamchisiga o'tdi

Reja WR-07 uchun uchta faylni nomlagan. To'rtinchisi (`emptyDeliveryHint`) ayni
sinfda edi va fayl allaqachon 2-vazifaning to'plamida — bittasini xom ISO
holida qoldirish WR-07 ning O'ZI shikoyat qilayotgan «bir fazada ikki javob»
holatini qaytarardi.

### 4. WR-13 e'loni IKKALA blokda takrorlanadi

Reja «alohida «boshqa» guruhida yoki hech bo'lmaganda sanoq farqini e'lon
qiladigan jumla» deb tanlov qoldirgan. Tanlangan — **sanoq farqi jumlasi**,
va u har blokda mustaqil chiziladi: `unpaid-list.tsx` ning O'Z qoidasi
(«HAR BLOK O'Z MAZMUN ATRIBUTINI O'ZI CHIQARADI, SAHIFA EMAS») bir blokni
qo'shnisiga bog'lashni taqiqlaydi — kesishma kunida (bugun) to'rt blok
umuman chizilmaydi va fakt yo'qolardi.

## Auto-fixed Issues

**1. [Rule 1 - Bug] Audit izida bo'sh izoh tuguni**
- **Topildi:** 2-vazifa, WR-15 ni yopish paytida
- **Nosozlik:** marshrut yechim matnini tarix qatorining izohi qilib ham
  yozadi, ya'ni bo'sh satr audit izida bo'sh `<span>` chizardi
- **Tuzatish:** `event.note === null || event.note.trim() === ""` sharti
- **Fayl:** `case-detail-dialog.tsx`
- **Commit:** `ff1fa7a`

**2. [Rule 2 - Konvensiya] Taqiqlangan literal izohda**
- **Topildi:** 1 va 3-vazifada, qabul mezoni `grep` i bilan
- **Nosozlik:** izohda taqiqlangan shakl LITERAL yozilgani mexanik skanni
  o'ziga qarshi qo'yardi (`badge.tsx:24-26` konvensiyasi)
- **Tuzatish:** ikkala izoh ham nomsiz shaklga o'tkazildi
- **Fayl:** `alert-row.tsx`, `hit-rate-card.tsx`

## Deferred Issues

`deferred-items.md` ga **4-band** qo'shildi: `alert-row.tsx` ning qolgan uch
lahzasi (`first_seen_at`, `last_seen_at`, `notified_at`) hamon yaroqsiz satrda
`"Invalid Date"` chizadi. **O'lchandi:** next-intl istisno ko'tarmaydi —
`onError(FORMATTING_ERROR)` chaqirib satrni qaytaradi. SCOPE BOUNDARY sababli
tegilmadi (reja WR-12 ni aynan `alertDurationParts` bilan chegaralagan).

## Known Stubs

Yo'q.

## Threat Flags

Yangi tarmoq marshruti, auth yo'li yoki sxema o'zgarishi YO'Q. T-08-39,
T-08-40, T-08-41, T-08-42 — hammasi `mitigate` dispozitsiyasi bo'yicha
bajarildi va test bilan o'lchandi (T-08-41 ning o'lchovi yuqoridagi audit
shovqini jadvalida). T-08-SC (`accept`): yangi npm paketi qo'shilmadi.

## Muhit haqida qayd (keyingi ijrochilar uchun)

Worktree'da `frontend/node_modules` YO'Q. Testlarni yugurtirish uchun asosiy
checkout'ning `node_modules` iga **directory junction** qo'yildi
(`mklink /J`), ijro oxirida u `rmdir` bilan olib tashlandi va asosiy
checkout'ning `node_modules` i **butun** ekani tasdiqlandi (380 yozuv).
`npm ci` yugurtirilmadi — u tarmoq va bir necha daqiqa talab qilardi.
⚠ Junctionni ijro oxirida OLIB TASHLASH majburiy: worktree'ni majburan
o'chirish junction ichiga kirib, asosiy `node_modules` ni yo'q qilishi mumkin.

## Self-Check: PASSED

Barcha yaratilgan fayllar mavjud, barcha commitlar `git log` da; ishchi
daraxt toza, o'chirilgan fayl yo'q, kuzatilmagan fayl yo'q.
