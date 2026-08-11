---
phase: 06-billing-va-kassir
plan: 13
subsystem: frontend
tags: [billing, director-ui, evidence, variance, anomaly, g-25, g-27, g-28]
requires:
  - "06-02: `api-types.ts` reyestrlari (`ANOMALY_KINDS`, `ADJUSTMENT_REASONS`) va `billing.*` matn kalitlari"
  - "06-03: `billing-charge-queries.ts`, `billing-pending-queries.ts`, `shift-queries.ts` hooklari"
  - "06-08: `GET /billing/charges|anomalies` o'ramlari (`{day, rows, …}`)"
  - "06-10: `GET /shifts?day=` va smenasiz to'lovlar sanog'i"
  - "06-11: klient envelopelarining serverga moslanishi (`.rows`) va enum ko'chirilishi"
  - "05-15: `GET /snapshots/{id}/image` ning `CAMERA_VIEW | OCCUPANCY_REVIEW` ostiga o'tishi"
provides:
  - "Y-4 direktor sahifasi (`/[locale]/billing`) — beshala blok bir faylda kompozitsiya qilingan"
  - "G-25 (uch qatlamli): blok to'plami disjunktligi + mazmun juftligi + mock'dan hosila haqiqiy mazmun"
  - "G-27: ikki tomonlama variance va yozuv yuzasi nolligining to'plam-tenglik o'lchovi"
  - "G-28: dalil kadrining mavjud yagona marshrutdan kelishi (tarmoq yuzasi bo'yicha o'lchangan)"
  - "`hasAdjustedRow` / `varianceDirection` / `shortChargeId` — sof funksiyalar"
affects:
  - "8-faza hisobot yuzasi: ism joinining sahifa chegarasi (deferred #9)"
tech-stack:
  added: []
  patterns:
    - "Ro'yxat komponenti `data-billing-content` ni O'ZI chiqaradi — sahifa emas (bo'sh o'ram darvozadan o'ta olmasligi uchun)"
    - "Dalil marshruti da'vosi DOM'dagi `src` dan emas, `apiRequest` ga berilgan YO'LLAR TO'PLAMIDAN o'lchanadi"
    - "Yo'qlik da'volari to'plam tengligi bilan (D-31), inkor matcher bilan emas"
    - "Grep darvozasi qo'riqlaydigan token izohda ham literal yozilmaydi (badge.tsx:24-26 konvensiyasi)"
key-files:
  created:
    - frontend/src/app/[locale]/(app)/billing/page.tsx
    - frontend/src/app/[locale]/(app)/billing/page.test.tsx
    - frontend/src/components/billing/day-picker.tsx
    - frontend/src/components/billing/day-picker.test.tsx
    - frontend/src/components/billing/pending-summary.tsx
    - frontend/src/components/billing/charge-list.tsx
    - frontend/src/components/billing/charge-detail-dialog.tsx
    - frontend/src/components/billing/charge-detail-dialog.test.tsx
    - frontend/src/components/billing/anomaly-list.tsx
    - frontend/src/components/billing/variance-cell.tsx
    - frontend/src/components/billing/variance-list.tsx
    - frontend/src/components/billing/variance-list.test.tsx
  modified:
    - .planning/phases/06-billing-va-kassir/06-UI-SPEC.md
    - .planning/phases/06-billing-va-kassir/deferred-items.md
    - frontend/messages/uz-Latn.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/ru.json
decisions:
  - "G-28 ning marshrut da'vosi DOM'dagi `src` dan TARMOQ YUZASIGA ko'chirildi — rejaning literal shakli ishlaydigan ekranni buzardi"
  - "DL-3 ning `description` i `billing.immutableNotice` dan `billing.detail` ga o'zgartirildi — aks holda D-07 darvozasi 3-bo'limni ko'rmasdan yashil qaytardi"
  - "Dalil affordansi turning NOMIDAN emas, `snapshot_id === null` MA'LUMOTIDAN o'qiladi (C-12 ning juftlangan CHECK i)"
  - "Bo'sh holat matnlari uchun ettita `billing.*` kaliti qo'shildi — usiz G-25 (c) ning «bo'sh natija ham mazmun» sharti bajarilmasdi"
metrics:
  duration: "~2 soat 40 daqiqa"
  completed: 2026-08-11
  tasks: 3
  commits: 4
  files_created: 12
  files_modified: 5
---

# Phase 6 Plan 13: Y-4 — direktorning hisob, anomaliya va variance yuzasi (Summary)

Direktor yuzasi (`/[locale]/billing`) beshala blokni bitta faylda kompozitsiya qiladi va
G-25 uch qatlamga kuchaytirildi — endi bo'sh `<div data-billing-block="charges" />`
o'rami darvozadan **o'ta olmaydi**, va bu ikki sabotaj bilan **o'lchandi**.

## Nima qurildi

| Blok | Fayl | Muzokarasiz xossasi |
|------|------|---------------------|
| A kun tanlagichi | `day-picker.tsx` | Standart ⛔ **KECHA** (C-3), maksimum bugun — ikki qatlamda |
| B kutilayotgan patta | `pending-summary.tsx` | Avtomatik taymer yo'q; `[Yangilash]` + server bergan `fetched_at` |
| C yozilgan hisoblar | `charge-list.tsx` | Qatorlar `.rows` dan; tarif=hisob bo'lsa bitta ustun (D-09); DL-3 ni O'ZI ochadi |
| — DL-3 | `charge-detail-dialog.tsx` | Besh bo'lim; o'zgarmaslik jumlasi **shartsiz**; `snapshot_id` yo'q qatorda kadr **chizilmaydi** |
| D anomaliyalar | `anomaly-list.tsx` | Uch yorliq, ⛔ **uch alohida sanoq** (D-05); dalil affordansi `disabled` emas, **yo'q** |
| E smena farqi | `variance-list.tsx` + `variance-cell.tsx` | Ikki tomonlama, uch kanal; yozuv yuzasi **aynan nol**; smenasiz to'lovlar nomlangan |
| Sahifa | `billing/page.tsx` | Beshala bolani import qilib chizadi; `Suspense`; `data-billing-block` kontrakti |

## Sabotaj natijalari (D-30) — ikkalasi ham talab qilingan javobni berdi

### S-E — G-25 ning kuchayishini o'lchaydi

`billing/page.tsx` da `<ChargeList … />` vaqtincha `<div data-billing-block="charges" />`
ga almashtirildi.

| Qatlam | Natija | Ma'nosi |
|--------|--------|---------|
| **(a) blok to'plami** | ⛔ **YASHIL QOLDI** | **Eski darvozaning ko'rligi hujjatlashtirildi**: bo'sh o'ram atribut to'plamini o'zgartirmaydi, ya'ni BILL-02/03/04 umuman chizilmagan holda faza yashil qaytardi |
| **(b) mazmun juftligi** | ⛔ **QIZARDI** | `charges` bloki ichida o'z `data-billing-content` i topilmadi |
| **(c) haqiqiy mazmun** | ⛔ **QIZARDI** | rasta kodi ham, `tbody tr` sanog'i ham yo'q |
| bo'sh natija varianti | ⛔ **QIZARDI** | `rows: []` shoxi ham bo'sh o'ramni o'tkazmadi |
| D-09 ustun juftligi | ⛔ **QIZARDI** | qo'shimcha qamrov |

Jami **5 test qizardi, 11 yashil qoldi** — reja kutgan natijaning aynan o'zi.

### S-F — G-27 ning ikki tomonlamaligini o'lchaydi

`variance-cell.tsx` da `> 0` shoxi `< 0` bilan birlashtirildi (ikkalasi «Kamomad» berdi).

**3 test qizardi:** sof funksiya da'vosi, «Kamomad **va** Ortiqcha» juft testi (matn **va**
ikonka to'plami bo'yicha), va unga langarlangan yozuv-yuzasi nazorati. Ya'ni ortiqcha
naqdni jimgina yutish **o'lchanadi**.

## Rejadan chetlanishlar

### 1. [Rule 1 — Bug] G-28 ning marshrut da'vosi tarmoq yuzasiga ko'chirildi

- **Qayerda:** Task 2, `charge-detail-dialog.test.tsx`
- **Muammo:** Reja `img` elementlarining `src` to'plami `/api/v1/snapshots/{id}/image`
  shabloniga mos bo'lishini talab qilardi. `GET /snapshots/{id}/image` **sessiya tokenini
  talab qiladi**, `<img>` esa sarlavha qo'sha olmaydi. Da'voning literal shakli ikki
  singan yo'ldan birini majburlardi: (a) tokensiz `<img src>` — ishlab turgan ekranda
  **401**; (b) tokenni URL'ga qo'yish — §14.2 taqiqlagan oldindan avtorizatsiyalangan
  havolaning aynan o'zi. Ikkalasi ham darvozani qondirib **mahsulotni buzardi**.
- **Tuzatish:** Kadr `useEvidenceImageHref` (05-13/05-15 ning mavjud hooki) orqali
  olinadi va da'vo `apiRequest` ga berilgan **yo'llar to'plamiga** qo'yildi —
  `review-session.test.tsx:339-350` ning aynan naqshi. ⛔ Bu **kuchaytirish**: to'plam
  tengligi ikkinchi manbani ham (imzolangan havola, boshqa proxy) qizartiradi, `src`
  regeksi esa faqat bitta elementning matnini ko'rardi.
- **Fayllar:** `charge-detail-dialog.tsx`, `charge-detail-dialog.test.tsx`
- **Commit:** `ef434e6`

### 2. [Rule 1 — Bug] DL-3 ning D-07 darvozasi KO'R edi

- **Qayerda:** Task 2
- **Muammo:** `billing.immutableNotice` dialogning `description` propi sifatida ham
  berilgan edi. Radix uni `sr-only` `<p>` bo'lib DOM'ga chiqaradi va u **dialog tanasi
  hali yuklanayotgan paytda ham mavjud**. Natijada «jumla har doim ko'rinadi» darvozasi
  3-bo'limni **umuman ko'rmasdan** yashil qaytardi — bo'lim o'chirilgan holatda ham.
  Bu 05-15 ning **S-D sinfi**.
- **Tuzatish:** Tavsif `billing.detail` ga o'zgartirildi; jumla endi **aynan bitta joyda**
  (3-bo'lim) va uni kutish dialog tanasining yuklanishini talab qiladi.
- **Commit:** `ef434e6`

### 3. [Rule 1 — Bug] G-25 (a) ning kutish langari qatlamlarni aralashtirardi

- **Qayerda:** Task 3, S-E sabotajining birinchi yugurishi
- **Muammo:** `?day=kecha` uchun (a) testlari `billing.chargesTitle` ni kutardi — ya'ni
  **ro'yxat mazmuniga** bog'langan edi. S-E ostida ular ham qizardi va «eski darvoza ko'r
  edi» degan **fakt o'lchanmay qolardi** (qatlamlar ajratilmasdi).
- **Tuzatish:** (a) ning langari ikkala kun shoxida ham mavjud blokka (`billing.shiftsTitle`)
  ko'chirildi. Tuzatish **da'voning aniqligida**, kodda emas — plan'ning «(b)/(c) yashil
  qolsa tuzatish da'voni kengaytirishda» qoidasining teskari yo'nalishdagi qo'llanishi.
- **Commit:** `7e894b1`

### 4. [Rule 3 — Blocking] Yettita `billing.*` matn kaliti qo'shildi

- **Muammo:** §13.8 ning №4/№5/№6/№7 bo'sh holatlari uchun matn kaliti **mavjud emas
  edi**, `billing.noFutureDays` ham yo'q edi. Rejaning `<verification>` bandi «yangi kalit
  qo'shilmagan (06-02 egaligi)» deydi, LEKIN G-25 (c) `rows: []` bergan blok **o'z
  bo'sh-holat matnini ko'rsatishini** talab qiladi. Ikki talab bir-birini inkor qilardi.
- **Yechim:** Orkestratorning ochiq ko'rsatmasi («If you add a key, add it to all three
  locales, run `i18n:gen`, and say so in SUMMARY.md») bo'yicha kalitlar qo'shildi.
  06-02 ancha oldin (1-to'lqin) merge bo'lgan, ya'ni egalik ziddiyati endi yo'q.
- **Qo'shilgan kalitlar:** `billing.noFutureDays`, `emptyCharges`, `emptyChargesHint`,
  `goAnomalies`, `emptyToday`, `goYesterday`, `emptyAnomalies`, `emptyAnomaliesHint`,
  `emptyShifts`, `emptyShiftsHint`, `evidenceShow` (11 ta).
- **Natija:** `i18n:check` → **1106 kalit × 3 til**, kalit va ICU parity to'liq
  (bazaviy 1095 → 1106). `uz-Cyrl` `i18n:gen` bilan hosil qilindi (drift yo'q).

### 5. [Rule 2 — Missing] Dalil affordansi turning nomidan emas, ma'lumotdan o'qiladi

Reja `no_coverage_stall` turini nomi bo'yicha tekshirishni nazarda tutardi. Shart
`row.snapshot_id === null` ga qo'yildi — bu C-12 ning juftlangan `CHECK` ining aynan
takrori va u `anomalyRowSchema` ning `refine` i bilan **parse paytida** kafolatlangan.
Turning nomiga bog'lanish **ikkinchi haqiqat manbai** bo'lardi: reyestr o'zgarsa shart
jimgina eskirardi. Qo'shimcha foyda — qabul mezonining «qo'lda `"unassigned_occupied"`
literali yo'q» sharti tabiiy ravishda bajariladi.

## Darvozalar — o'lchangan raqamlar

Frontend darvozalari **haqiqatan yugurtirildi** (worktree'da `npm ci` bajarildi; junction
yoki symlink **yaratilmadi**):

| Darvoza | Natija |
|---------|--------|
| `npm --prefix frontend test` (to'liq zanjir) | ⛔ **182 node test + 703 vitest = 885, 0 fail** (51 test fayli) |
| shundan bu rejaning yangi testlari | **47** (day-picker 9, charge-detail-dialog 12, variance-list 10, billing/page 16) |
| `npm --prefix frontend run typecheck` | ⛔ **toza** (0 xato) |
| `npm --prefix frontend run lint` | ⛔ **toza** (0 xato, 0 ogohlantirish) |
| `npm --prefix frontend run i18n:check` | ⛔ **1106 kalit × 3 til**, parity to'liq |
| `npm --prefix frontend run build` | ⛔ **muvaffaqiyatli**, 13,2 s; 69/69 sahifa; `/[locale]/billing` uchala locale'da **SSG** (ya'ni `Suspense` chegarasi ishlaydi) |
| `node --test frontend/scripts/bulk-action-surface.test.mjs` | ⛔ **8/8** (`SPEC_FILES.length === 1`) |
| `node --test frontend/scripts/billing-copy.test.mjs` | ⛔ **yashil** (to'liq zanjir ichida) |

⚠ **Backend/docker yarmi ATAYIN yugurtirilmadi:** bu reja frontend-only
(`git diff --numstat services/` → **bo'sh**) va konteynerlar qo'shni 06-12 worktree'si
bilan umumiy — poyga ~33 soxta qizil berardi (06-08/06-09/06-11 da o'lchangan).

## Qabul mezonlarining mexanik tekshiruvi

| Mezon | Natija |
|-------|--------|
| `data-billing-content` in `billing/page.tsx` | **0** ✅ |
| `hidden\|display:none` in `billing/page.tsx` | **0** ✅ |
| beshala bola import **va** render (`>= 10`) | **10** ✅ |
| JSX render (`>= 5`) | **5** ✅ |
| `ChargeDetailDialog` in `charge-list.tsx` (`>= 2`) | **3** ✅ |
| `VarianceCell` in `variance-list.tsx` (`>= 2`) | **3** ✅ |
| to'rtala ro'yxat o'z `data-billing-content` ini chiqaradi | **4/4** ✅ |
| `not.toContain` (uchala test faylida) | **0** ✅ |
| `abs(` in `variance-cell.tsx` | **0** ✅ |
| `text-warning\|color-warning` in `variance-cell.tsx` | **0** ✅ |
| yozuv-yuzasi so'zlari in `variance-list.tsx` | **0** ✅ |
| `crossOrigin` in `charge-detail-dialog.tsx` | **0** ✅ |
| `presign\|X-Amz\|s3.\|seaweed\|:8333\|toDataURL\|download` in `billing/*.tsx` | **0** ✅ |
| `tariff_id\|tariffId` in `charge-detail-dialog.tsx` | **0** ✅ |
| saqlangan qoldiq nomi in `billing/*.tsx` | **0** ✅ |
| `Tahrirlash\|O'chirish\|editCharge\|deleteCharge` | **0** ✅ |
| `refetchInterval` in `pending-summary.tsx` | **0** ✅ |
| `charge_id\|chargeId` in `pending-summary.tsx` | **0** ✅ |
| `^\| \*\*G-18\*\* \|` in `06-UI-SPEC.md` | **0** ✅ |
| §11.2 dagi `[TALAB]` teglari (B, C, D, E bir xil) | **0** — to'rtala qatordan olib tashlandi ✅ |

⚠ **Konvensiya eslatmasi:** to'rt marta grep darvozasi **o'z izohim** tufayli qizardi
(`not.toContain`, `refetchInterval`, saqlangan qoldiq nomi, `data-billing-content`/`hidden`).
Har safar tuzatish `badge.tsx:24-26` ning kodbaza konvensiyasi bo'yicha bo'ldi:
**qo'riqlanadigan token izohda ham literal yozilmaydi**.

## Bilib turib qoldirilgan chegara

**Sotuvchi ismi joini faqat birinchi sahifani ko'radi** (`PAGE_SIZE = 50`). 50 dan ortiq
sotuvchisi bor bozorda 51-chidan keyingi ismlar **bo'sh** ko'rinadi. Ism **to'qilmaydi** —
bo'sh katak qoladi (05-14 darsi). Uchala tuzatish yo'li ham bu rejadan tashqarida
(audit shovqini / yangi backend yuzasi / §5.5 ning rad etgan yo'li). Batafsil sabab bilan
`deferred-items.md` ning **9-qatorida**. Rasta kodi har qatorda mavjud, ya'ni nizoda
kerak bo'ladigan identifikator yo'qolmaydi.

## Known Stubs

Yo'q. Har blok haqiqiy ma'lumot manbaiga ulangan va bo'sh holatlar **matn** ko'rsatadi
(bo'sh `<div>` emas) — buni G-25 (b)/(c) ning `rows: []` varianti o'lchaydi.

## 06-12 bilan chegara

`components/collect/**` va `app/[locale]/(app)/collect/**` ga **tegilmadi**
(`git diff --stat` bilan tasdiqlangan). ⚠ **Merge eslatmasi:** bu reja
`frontend/messages/*.json` ga tegdi (11 kalit). Agar 06-12 ham o'sha fayllarga kalit
qo'shgan bo'lsa, konflikt `billing`/`collect` bloklarida bo'ladi va ikkala tomonni
saqlab, so'ng `npm --prefix frontend run i18n:gen` yugurtirish bilan yechiladi.

## Self-Check: PASSED

Yaratilgan 12 fayl **mavjud**, o'zgartirilgan 5 fayl **mavjud**, uchala commit
`git log` da **topildi** (`80689d9`, `ef434e6`, `7e894b1`).
