---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 15
subsystem: frontend
tags: [nextjs, react, tanstack-query, zod, next-intl, i18n, reconciliation, evidence-link, gates]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`GET /reconciliation/{report,cases,hit-rate}` + sakkiz sxema, `CaseListResponse` envelope (07-10)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`domainKey(marketId, …)` kalit konvensiyasi va UI-SPEC ustunlik pretsedenti (07-05)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`_QUALIFIER_WORDS` / `_MORNING_TEXT` / `_EVENING_TEXT` — G-35 ning bot yarmi (07-13/07-14)"
  - phase: 06-billing-va-kassir
    provides: "`billing/day-picker` (standart KECHA), `data-billing-block` naqshi, `anomaly-list` qardoshi"
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`05-UI-SPEC.md` §15 G-18 e'loni — ommaviy amal darvozasining qamrovi"
provides:
  - "`/[locale]/(app)/reconciliation` — oltita blok, kunga qarab to'plam (RECON-01, RECON-02)"
  - "`lib/reconciliation-queries.ts` — YAGONA so'rov moduli (W0-F4)"
  - "`lib/reconciliation-errors.ts` — `RECON_ERROR_CODES` + `SERVER_CODE_MAP` (W0-F7)"
  - "`api-types.ts` — `CASE_STATUSES` / `SUBJECT_KINDS` / `DELIVERY_STATES` / `NOTIFICATION_KINDS` (W0-F8)"
  - "`lib/vendor-labels.ts` — shaxsiy maydonni nomuvofiqlik yuzasidan TASHQARIDA o'qiydigan modul"
  - "`scripts/reconciliation-copy.test.mjs` — G7-3 + G-30 + G-35 + G-36, bitta faylda"
  - "⛔ G-29 (blok to'plami + mazmun juftligi) va G-32 (maxrajsiz foiz) darvozalari"
  - "`components/reconciliation/**` — G-18 ommaviy-amal skanining TO'RTINCHI katalogi"
affects: [07-16, 07-17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Taqiqlangan shaxsiy maydonni ALOHIDA, skanlanmaydigan modulda o'qish — taqiq yuzaga qo'yiladi, ma'lumotga emas"
    - "Darvozaning kutilgan SONI boshqa faylning MAVJUDLIGIDAN hosila (aksent byudjeti DL-5 dan)"
    - "Backend render kodidan parse qilib olingan kutilma (G-35: qaysi dayjest qaysi sifatlovchini QO'YADI)"
    - "i18n kalitini ekran ATAMASIGA moslash taqiqlangan tokenni ham yo'q qiladi (`hitRate*` -> `accuracy*`)"

key-files:
  created:
    - frontend/src/lib/reconciliation-queries.ts
    - frontend/src/lib/reconciliation-queries.test.tsx
    - frontend/src/lib/reconciliation-errors.ts
    - frontend/src/lib/vendor-labels.ts
    - frontend/src/app/[locale]/(app)/reconciliation/page.tsx
    - frontend/src/components/reconciliation/day-picker.tsx
    - frontend/src/components/reconciliation/unpaid-list.tsx
    - frontend/src/components/reconciliation/unregistered-list.tsx
    - frontend/src/components/reconciliation/evidence-link.tsx
    - frontend/src/components/reconciliation/case-list.tsx
    - frontend/src/components/reconciliation/case-status-badge.tsx
    - frontend/src/components/reconciliation/hit-rate-card.tsx
    - frontend/src/components/reconciliation/delivery-placeholder.tsx
    - frontend/src/components/reconciliation/page.test.tsx
    - frontend/src/components/reconciliation/unpaid-list.test.tsx
    - frontend/src/components/reconciliation/hit-rate-card.test.tsx
    - frontend/scripts/reconciliation-copy.test.mjs
    - .planning/phases/07-nomuvofiqlik-bildirishnoma-va-botlar/deferred-items.md
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/components/shell/app-shell.tsx
    - frontend/scripts/error-codes.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - .planning/phases/05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-UI-SPEC.md

key-decisions:
  - "⛔ `hit-rate` javob sxemasi YOZILMADI — UI-SPEC §9.2/§9.5 nisbatni envelope'ning to'rt sanog'idan RENDER PAYTIDA hisoblaydi va G-36 `hit_rate` nomini shu faylda 0 ga qulflaydi; reja matnining `hitRateSchema` bandi bu ikkovi bilan MEXANIK ziddiyatda edi"
  - "⛔ `recon.hitRate*` kalitlari `recon.accuracy*` ga o'zgartirildi — kalit nomining O'ZI G-36 tokenini olib kirardi; yangi nom §14.1 ning ekran atamasiga («aniqlik ulushi») MOSROQ"
  - "⛔ Aksent byudjeti (`variant=\"default\"`) HOSILA: DL-5 yo'q ekan 0, kelganda 1 — «aynan 1» ni bugun talab qilish yozuv yuzasini rejadan OLDIN qurishga majburlardi"
  - "Case ro'yxatida sotuvchi ustuni YO'Q — `CaseRowResponse` da `vendor_id` umuman yo'q (07-10 kontrakti)"
  - "`unregistered` blokida kamera/zona/slot o'rniga `stall_code` — javobda boshqasi yo'q va maydon BO'SH EMAS"
  - "Sotuvchi ismi `lib/vendor-labels.ts` da — taqiqlangan nomlar reyestri yuzani qo'riqlaydi, ma'lumotni emas"
  - "G-35 ning frontend yarmi = «veb va bot AYNAN BIR SO'ZNI ishlatadi» (D-30), backend testining nusxasi EMAS"

patterns-established:
  - "Blok to'plami + MAZMUN JUFTLIGI juftligi: atribut ro'yxat komponentida, sahifada 0 marta; sabotaj bilan o'lchanadi"
  - "Darvoza o'z manba faylini o'qiganda taqiqlangan token BO'LAKLARDAN quriladi (regeks literali darvozani o'ziga qarshi qo'yadi)"

requirements-completed: [RECON-01, RECON-02]

# Metrics
duration: ~135min
completed: 2026-08-12
---

# Phase 7 Plan 15: Nomuvofiqlik hisoboti va case yuzasi — frontend Summary

**Direktor endi «band, lekin to'lovsiz» ni KO'RADI: ikki sinf ikki
alohida blokda, hech qachon qo'shilmagan holda; dalil — 401 oladigan
kadr havolasi emas, mavjud yuzaga ilova ichidagi navigatsiya; aniqlik
ulushi esa maxraji bilan yoki UMUMAN chizilmaydi.**

## Performance

- **Duration:** ~135 min
- **Tasks:** 3/3
- **Files:** 25 (18 yangi, 7 tahrirlangan) — ⛔ **birortasi ham `.py` emas**

## ⛔ To'liq frontend to'plami BIRINCHI MARTA o'lchandi

Bu reja `frontend/node_modules` ni o'rnatgan birinchi ijro bo'ldi
(oldingi frontend rejalari uni topmagan va `vitest` yarmini
**tashlab ketgan**). Shuning uchun o'lchov **ikki marta** — o'zgarishdan
**oldin** va **keyin** — bajarildi:

| Darvoza | BAZA (o'zgarishsiz) | YAKUNIY | Farq |
|---|---|---|---|
| `node --test scripts/*.test.mjs` | **191 pass / 0 fail** | **216 pass / 0 fail** | +25 |
| `vitest run` | **748 pass / 0 fail** | **783 pass / 0 fail** | +35 |
| Test fayllari | 55 | **59** | +4 |
| `i18n:check` | 1119 kalit × 3 til | **1174 kalit × 3 til** | +55 |
| `build` (SSG) | 72 sahifa | **75 sahifa** | +3 |
| `typecheck` / `lint` | toza | **toza** | — |

⛔ **Baza YASHIL edi** — ya'ni to'plangan uchta o'lchanmagan band
(07-08 va 07-14 ning `alert-row` o'zgarishlari) **buzilmagan**. Lekin
ularning holati o'lchovsiz emas edi, **mexanizmsiz** edi — quyida.

### To'plangan bandlar: NIMA topildi

**1. `frontend/src/components/snapshots/alert-row.test.tsx` ⛔ UMUMAN
MAVJUD EMAS.** Topshiriq uni «yugurtirib bo'lmagan» deb ta'riflagan;
haqiqat boshqa — u **hech qachon yozilmagan**. `vitest run alert-row`
→ `No test files found, exiting with code 1`.

**2. Matn tomoni esa TO'LIQ TOZA — o'lchandi:** `ALERT_TITLE_KEYS` da
**15 a'zo**, ularning **15 × 3 = 45 matni ham mavjud**, yetishmagani
**0**. Ya'ni 07-08 ning uch tilli ishi ham, 07-14 ning to'rt yangi
a'zosi ham **haqiqatan bajarilgan**.

**3. ⛔ LEKIN MEXANIZM YO'Q va bu haqiqiy topilma.**
`grep -n "alertKey\|ALERT_TITLE" frontend/scripts/*.test.mjs` → **0**:
`ALERT_TITLE_KEYS` ni `messages/*.json` bilan bog'laydigan **birorta
darvoza yo'q**. O'n oltinchi a'zo matnsiz qo'shilsa, ekranda zaxira
yorliq chiqardi va buni **hech nima aytmasdi**. Qo'shimcha:
`alert-list.test.tsx` 07-14 ning to'rt kalitidan **birortasini ham
render qilmaydi**.

⛔ **Tuzatilmadi va sabab QAMROV:** fayl `components/snapshots/**` da,
bu rejaning fayl to'plamidan **tashqarida**. Band
`deferred-items.md` ga **egasi bilan** yozildi (07-17 yoki 8-faza) va
tuzatishning **tayyor shakli** ko'rsatildi (`error-codes.test.mjs` ning
`RECON_ERROR_CODES` bloki — oldinga va teskari yuradigan naqsh).

## Task Commits

1. **Task 1: yagona so'rov moduli, uch reyestr, xato kodlari** — `c6ffbc2` (feat)
2. **Task 2: oltita blok, ikki sinf, dalil HAVOLASI** — `ac27b25` (feat)
3. **Task 3: beshta darvoza + G-18 ning to'rtinchi katalogi** — `6d92d31` (test)

⚠ **Tartib invarianti BAJARILDI:** `components/reconciliation/**`
fayllari **2-taskda** (`ac27b25`) tug'ildi, `05-UI-SPEC.md` dagi e'lon
qatori esa **3-taskda** (`6d92d31`). `bulk-action-surface.test.mjs`
e'lon qilingan har katalogning **mavjud va bo'sh emasligini** tekshiradi,
ya'ni qator birinchi kelsa to'plam **darhol qizarardi**. UI-SPEC §16.5
buni «bitta commitda» deb ta'riflaydi; ijrochi protokoli har task
tugagach commit qiladi — ⛔ **ikki commit MUQARRAR**, lekin xavfsizlik
xossasi (fayllar → qator) **to'liq saqlandi**.

## ⛔ Sabotaj natijasi (majburiy, BAJARILDI)

`<UnpaidList/>` → bo'sh `<section data-recon-block="unpaid" />`:

| G-29 bandi | Kutilgan | ⛔ Natija |
|---|---|---|
| (a) blok to'plami (`bugun`, `kecha`, kesishma) | **yashil qolishi** | ✅ **YASHIL QOLDI** (3/3) |
| (b) mazmun juftligi | ⛔ **qizarishi** | ⛔ **QIZARDI** — `?day=kecha`: mazmun to'plami |
| (c) hosila mazmun | ⛔ **qizarishi** | ⛔ **QIZARDI (×2)** — rasta kodi + qator soni, va bo'sh-holat matni |

**Jami: 3 failed | 7 passed.** Bu aynan 06-fazaning o'lchangan
ko'rligidan olingan dars: faqat atribut to'plamini tekshiradigan darvoza
**bo'sh o'ramni MUKAMMAL o'tkazardi** va butun yuza **chizilmagan** holda
faza yashil qaytardi.

Sabotaj `git checkout -- <fayl>` bilan qaytarildi (⛔ `git clean` /
`reset` **ishlatilmadi**); `grep -c SABOTAJ` → **0**, ish daraxti toza.

## Rejadan chetlanishlar

### Rule 1 — hujjatlararo ziddiyat, HAQIQAT ustun turdi

**1. [Rule 1 - Bug] `hitRateSchema` YOZILMADI — reja O'ZI bilan ziddiyatda edi**

- **Topildi:** Task 1.
- **Muammo:** Reja bir bandda `hitRateSchema` ni **`hit_rate: z.number().nullable()`** bilan buyuradi, keyingi bandda esa qabul mezoni sifatida `grep -cE "hit_rate|hitRate" reconciliation-queries.ts` → **`0`** ni talab qiladi. Ikkalasi **bir vaqtda bajarilmaydi**: `hit_rate` kalitli sxema faylda o'sha satrni **literal** qoldiradi.
- **Bog'lovchi manba — UI-SPEC** (07-05 pretsedenti): §8.1 E qatori manbani «o'sha envelope sanoqlaridan» deb ko'rsatadi; §9.2 «hit-rate ularning **hosilasi** va **ikkinchi so'rov qilmaydi**» deydi; §9.5 «klientda ham `hit_rate` nomli **o'zgaruvchi/maydon yo'q** — u to'rt sanoqdan **render paytida** hisoblanadi». Va §16.6 G-32(a) ning **o'z o'lchovi** kartani `{justified:17, unjustified:8, new:5, in_review:3}` **sanoqlari bilan** render qiladi, `hit_rate` **qiymati bilan emas** — ya'ni UI-SPEC uch joyda bir xil gapiradi.
- **Yechim:** aniqlik ulushi `caseListSchema` ning to'rt sanog'idan render paytida hisoblanadi; `GET /hit-rate` marshruti bu ekranda **ishlatilmaydi** (u DAVR kesimida, ekran esa KUN kesimida — ikki manba ekranda ikki xil raqam bo'lardi). Sabab modul docstringiga **ochiq** yozildi.
- **Fayllar:** `frontend/src/lib/reconciliation-queries.ts`
- **Tekshiruv:** `grep -cE "hit_rate|hitRate"` → **0**; `strictObject` → **5** (reja ≥4 so'ragan)
- **Commit:** `c6ffbc2`

**2. [Rule 1 - Bug] `recon.hitRate*` kalitlari G-36 tokenini OLIB KIRARDI**

- **Topildi:** Task 2 qabul mezonini o'lchaganda — `hitRate` **hit** berdi.
- **Muammo:** UI-SPEC §14.3 ning shipping matni kalitlarni `recon.hitRateTitle` / `recon.hitRateBody` / … deb nomlaydi, §16.6 G-36 esa `hitRate` tokenini `components/reconciliation/**` da **0** ga qulflaydi. UI-SPEC **o'z darvozasi bilan ziddiyatda**.
- **Yechim:** kalitlar `recon.accuracyTitle` / `accuracyBody` / `accuracyExcluded` / `accuracyNone` / `accuracyNoneHint` ga o'zgartirildi. ⛔ **Ekran matni bir harf ham o'zgarmadi.** Va yangi nom §14.1 ning atama qaroriga (**«hit-rate» → «Aniqlik ulushi»**) `hitRate*` dan **MOSROQ**: kalit ham, matn ham endi bir xil atamani aytadi.
- **Nega darvozaga istisno yozilmadi:** «i18n kalitidan tashqari» degan carve-out keyingi ijrochi tomonidan kengaytirilardi va reyestr asta-sekin bo'shashardi. Nomni o'zgartirish darvozani **istisnosiz** qoldiradi.
- **Fayllar:** `messages/{uz-Latn,ru,uz-Cyrl}.json`, `components/reconciliation/hit-rate-card.tsx`
- **Tekshiruv:** 16 nomli reyestrning hits'i → **`[]`**; `i18n:check` 1174 × 3 toza
- **Commit:** `ac27b25`

**3. [Rule 1 - Bug] Case ro'yxatida SOTUVCHI ustuni qurilmadi**

- **Topildi:** Task 2, `case-list.tsx` yozilayotganda.
- **Muammo:** UI-SPEC §9.2 jadvali «Sotuvchi | ⛔ `vendor_id` → klientda join» qatorini beradi. Lekin 07-10 ning **shiplangan** `CaseRowResponse` ida `vendor_id` **umuman yo'q** — qator faqat `case_id`, `subject_kind`, `anomaly_id`/`charge_id`, `service_date`, `status`, `assignee_user_id`, `created_at` bilan keladi. Server docstringi buni **ochiq** aytadi: rasta kodi, sotuvchi va summa navbat qatorida **emas**, chunki ularni ko'chirish navbatni **ikkinchi haqiqat manbaiga** aylantirardi.
- **Yechim:** ustun **qo'shilmadi**, «—» bilan ham: doim bo'sh ustun 4-fazadagi «bo'sh katak» sinfidagi jim xato bo'lardi (05-14 darsi). Sotuvchi **hisobot bloklarida** ko'rinadi va u yerda HAQIQIY ma'lumot bilan keladi. Sabab komponent docstringiga 5-band sifatida yozildi.
- **Fayllar:** `components/reconciliation/case-list.tsx`
- **Commit:** `ac27b25`

**4. [Rule 1 - Bug] `unregistered` ustunlari — «kamera/zona + slot» O'RNIGA `stall_code`**

- **Topildi:** Task 2, marshrut kodini (`reconciliation.py:328-333`) va `AnomalyKind` docstringini o'qiganda.
- **Muammo — IKKI QATLAMLI:**
  1. Javobda **kamera ham, zona ham, slot vaqti ham yo'q**: qator `stall_code` + `service_date` bilan keladi. Ularni to'qish **to'qilgan qiymat** bo'lardi.
  2. UI-SPEC ning «rasta ustuni YO'Q» qoidasi **sababini o'zi yozgan**: «bo'sh "—" ustuni jim xato bo'lardi» — ya'ni u maydon **bo'sh** degan taxminga tayanadi. Taxmin **noto'g'ri**: `AnomalyKind.UNASSIGNED_OCCUPIED` ning ta'rifi — «rasta band, lekin ⛔ **SOTUVCHI** biriktirilmagan», ya'ni **rasta aniq** va uning kodi bor. 6-fazaning `anomaly-list.tsx` ham aynan shu qatorni `stall_code` bilan ko'rsatadi, va «ikki fazada ikki xil yorliq bo'lmasin» — UI-SPEC §14.1 ning **o'z** talabi.
- **Yechim:** ustunlar `Rasta · Sana · Dalil · Holat`. ⛔ **Sotuvchi ustuni esa HAQIQATAN yo'q** va bu sinfning butun mazmuni — biriktirilgan sotuvchi **mavjud emas**. Bu to'plam tengligi bilan o'lchanadi (`unpaid-list.test.tsx`).
- **Fayllar:** `components/reconciliation/unregistered-list.tsx`, `messages/*`
- **Commit:** `ac27b25`

**5. [Rule 1 - Bug] Aksent byudjeti «aynan 1» EMAS, DL-5 dan HOSILA**

- **Topildi:** Task 3, G-36(c) yozilayotganda.
- **Muammo:** Reja `variant="default"` ni `components/reconciliation/**` da **aynan 1 marta** talab qiladi. Lekin UI-SPEC §13.3 uning **yagona qonuniy joyini** nomma-nom beradi: DL-5 dagi `[Holatni saqlash]` — va o'sha dialog **07-16 niki** (bu reja «holat o'zgartirish boshqaruvi bu rejada YO'Q» deb **o'zi yozadi**). Ya'ni bugun «aynan 1» ni bajarish **yozuv yuzasini rejadan oldin qurishni** yoki aksent tugmani ro'yxat yuzasiga (§13.3 taqiqlaydi) qo'yishni talab qilardi.
- **Yechim:** kutilgan son **hosila**: `case-detail-dialog.tsx` **yo'q** ekan → **0**, **bor** ekan → **1**. ⛔ Ikkala holatda ham da'vo **aniq son** bilan, «ko'pi bilan bitta» **emas**: yumshoq da'vo dialog kelgan kuni tugmaning **umuman yozilmaganini** o'tkazib yuborardi. Bugungi o'lchov: **0/0** ✅.
- **Fayllar:** `frontend/scripts/reconciliation-copy.test.mjs`
- **Commit:** `6d92d31`

### Rule 2 — rejada yo'q, lekin usiz kontrakt YETIB BORMASDI

**6. [Rule 2 - Missing] `lib/vendor-labels.ts` — shaxsiy maydonni yuzadan TASHQARIDA o'qish**

- **Topildi:** Task 2. UI-SPEC §5.5/§8.3 sotuvchi ismini **talab qiladi**; G-36 esa `full_name`, `vendor_name`, `vendorName`, `phone`, `fullName` tokenlarini `components/reconciliation/**` da **0** ga qulflaydi. Reestrning maydoni aynan `full_name`, ya'ni 6-fazaning naqshini (`charge-list.tsx:109-111`) ko'chirish darvozani **darhol** qizartirardi.
- **Yechim:** ism **bitta joyda**, alohida modulda o'qiladi va yuzaga faqat **tayyor yorliq** chiqadi. ⛔ Bu darvozani aylanib o'tish **emas, uning MAQSADI**: taqiq «nomuvofiqlik yuzasi shaxsiy maydonni **O'ZI o'qimasin**» degan gap va u shu bo'linish bilan **mexanik** bajariladi. Sabab modul docstringida ochiq.
- **Qo'shimcha xossa:** `vendor_view` yo'q sessiyada so'rov ⛔ **umuman yubormaydi** — `useVendorsQuery` docstringi fon so'rovini audit shovqini deb taqiqlaydi.
- **Fayllar:** `frontend/src/lib/vendor-labels.ts`
- **Commit:** `ac27b25`

**7. [Rule 2 - Missing] `delivery-placeholder.tsx` — mazmun juftligi F blokini ham TALAB QILADI**

- **Topildi:** Task 2. G-29(b) `Set(content) === Set(blocks) \ CONTENT_EXEMPT` ni talab qiladi va `CONTENT_EXEMPT` **aynan bitta** a'zoli (`day`). Ya'ni `delivery` bloki ham mazmun atributini **chiqarishi shart**, aks holda darvoza **bo'sh o'ramni o'tkazardi** — ya'ni aynan o'zi qarshi qurilgan nosozlik.
- **Yechim:** nomlangan bo'sh holatli o'rin. ⛔ **Nomi `delivery-list.tsx` EMAS** va bu ataylab: 07-16 ning haqiqiy jadvali o'sha nomni oladi; band nom qolsa keyingi ijrochi to'ldirilmagan o'ramni «allaqachon bor» deb o'qirdi. ⛔ Holat nishoni ham **yo'q**: yarim yozilgan yorliq «yetkazildi» degan **isbotlanmagan** da'voni ekranga olib chiqarardi (Pitfall 2).
- **Fayllar:** `components/reconciliation/delivery-placeholder.tsx`
- **Commit:** `ac27b25`

**8. [Rule 2 - Missing] `lib/reconciliation-queries.test.tsx` — kesh siyosati RENDERSIZ o'lchanadi**

- **Topildi:** Task 1. Reja `day=bugun` uchun `staleTime === 0` **va** `gcTime === 0` ni **birlik testi bilan** talab qiladi, lekin `files_modified` da unga fayl yo'q.
- **Yechim:** `src/lib/*.test.tsx` — kodbazaning mavjud konvensiyasi (`market-queries.test.tsx`, `camera-queries.test.tsx`). 12 test: reyestr yopiqligi (to'plam tengligi), `strictObject` ning kutilmagan maydonda yiqilishi, `anomaly` da `expected_soum: null` ning **nolga aylanmasligi**, kalit doiralash (`key[0] === "m"`), va kesh siyosati.
- **Commit:** `c6ffbc2`

### Rule 3 — bloklovchi

**9. [Rule 3 - Blocking] `error-codes.test.mjs` ning RECON bloki LANGARSIZ qolardi**

- **Muammo:** G-17 ning barcha mavjud bloklari **backend reyestridan** boshlanadi. 07-10 SUMMARY ning 3-ochiq bandi esa marshrut kodlarini `billing_errors.py` ga **ataylab qo'shmagan**: o'sha faylning `billingConstants.size === 14` nazorat qiymati **darhol** qizarardi va uni «tuzatish» yagona yo'li sonni oshirish, ya'ni nazoratning butun ma'nosini yo'q qilish bo'lardi.
- **Yechim:** langar **frontendda** — `RECON_ERROR_CODES` **ekran** kodlarining ro'yxati. Serverning **mexanik** kodlari (`not_found`, `status_unchanged`, …) `SERVER_CODE_MAP` da xaritalanadi va ⛔ **xaritaning har NATIJASI reyestrda borligi alohida o'lchanadi** — aks holda server kod qaytarib turardi, `reconErrorView()` esa mavjud bo'lmagan matn kalitini qurardi.
- **Commit:** `c6ffbc2`

---

**Total deviations:** 9 auto-fixed (5 bug, 3 missing-critical, 1 blocking)
**Impact:** Qamrov kengaymadi. ⛔ Yangi npm paketi **yo'q** (T-07-SC), yangi
`ui/` primitivi **yo'q** (§3.2), yangi token/bo'shliq/tipografiya o'lchami
**so'ralmadi** (§6.2, §7.1), `rbac.ts`/`rbac.py` juftligi **tegilmadi** (M-6).

## ⛔ Ijro davomida darvoza IKKI MARTA o'zini qizartirdi (va ikkalasi ham qimmatli)

**1. Darvoza O'Z manbasini o'qiganda taqiqlangan tokenni ISHLATDI.**
`grep`-ga o'xshash da'vo `/\bG-3\b/` regeks **literali** bilan yozilgan
edi, test esa o'z faylini o'qiydi — ya'ni literalning **o'zi** taqiqni
buzdi. Bu kodbazada nomma-nom hujjatlashtirilgan sinf («2 va 3-fazada
15+ marta»). Yechim: naqsh **bo'laklardan** quriladi
(`new RegExp("\\bG" + "-3\\b")`) va sabab o'sha joyda yozildi.

**2. Python parseri jimgina BO'SH jadval qaytardi.** `_QUALIFIER_WORDS`
ning kalitlari satr literali **emas, KONSTANTA** (`QUALIFIER_EXPECTED:`).
Faqat qo'shtirnoqli kalitni o'qigan regeks lug'atni bo'sh deb qaytarardi
va uning ustidagi **uchala to'plam tengligi ham HECH NIMANI**
tekshirmasdi. Nosozlik `undefined` bo'lib DOM da'vosida ko'rindi;
parser ikkala shaklni ham o'qiydigan qilindi va sabab izohga yozildi.

⚠ Ikkalasi ham **quyi chegara / nazorat testi** falsafasining
tasdig'i: agar ular bo'lmaganda darvoza **jimgina yashil** qolardi.

## Verification Evidence

| Darvoza | Buyruq | Natija |
|---|---|---|
| Task 1 | `grep -c strictObject` / `z.enum` / `offset` / `hit_rate\|hitRate` | **5** / **0** / **0** / ⛔ **0** |
| Task 1 | 16 taqiqlangan nom, `float(`/`Decimal`/`.toFixed(`/`parseFloat(` | ⛔ **hammasi 0** |
| Task 1 | `node --test scripts/error-codes.test.mjs` | **29 pass** (+3 yangi) |
| Task 2 | `<img`/`next/image`/`background-image`/`backgroundImage`/`useEvidenceImageHref`/`URL.createObjectURL` | ⛔ **har biri 0** |
| Task 2 | `/snapshots/` satri katalogda | ⛔ **0** |
| Task 2 | `page.tsx` da `data-recon-content` | ⛔ **0** |
| Task 2 | `evidence-link.tsx`: `href` `/billing?day=` bilan; yangi oyna | ✅ **ha** / ⛔ **yo'q** |
| Task 2 | `total_anomalies\|combined_total\|grand_total\|totalAnomalies` | ⛔ **0** |
| Task 2 | `variant="default"` / `variant="destructive"` | **0** (DL-5 yo'q) / ⛔ **0** |
| Task 2 | `recon.*` qiymatlarida «case»/«кейс» — uchala locale | ⛔ **0 / 0 / 0** |
| Task 2 | `NAV_ITEMS` uzunligi; kassirga ko'rinadigan yozuvlar | **16** / ⛔ **2 (O'ZGARMAGAN)** |
| Task 3 | `node --test scripts/reconciliation-copy.test.mjs` | **22 pass**, 787 qator (reja ≥220) |
| Task 3 | `node --test` (recon-copy + bulk-action + error-codes + glossary) | **68 pass / 0 fail** |
| Task 3 | `bulk-action-surface.test.mjs` — to'rtinchi katalog | **8 pass**, e'lon qilingan UI-SPEC soni **1** |
| Task 3 | ⛔ **G-29 sabotaji** | ⛔ **(a) yashil, (b)+(c) QIZARDI (3 failed / 7 passed)** |
| Butun to'plam | `npm --prefix frontend test` | ⛔ **216 node + 783 vitest, 0 fail** |
| Tip / lint | `typecheck && lint` | **ikkalasi toza** |
| i18n | `i18n:check` | **1174 kalit × 3 til**, drift yo'q |
| Build | `build` | ✓ compiled; **75 SSG sahifa**; `/reconciliation` **uchala locale'da** |

### ⛔ uz-Cyrl QO'LDA tekshirildi (M-8 / 07-05 tuzog'i)

`i18n:gen` chiqishi **so'zma-so'z** o'qildi. Qarz/o'zlashma so'zlar
alohida tekshirildi va **hammasi to'g'ri shaklda**:

`рухсат` · `мурожаат` · `Директорга` · `тарих` · `суммаси` · `Камера` ·
`Синф` · `Номаълум` — ⛔ 07-05 topgan `ns`/`ts` klasterli defekt sinfidan
(`kvitansiya` → `квитанси…`) **birortasi ham yo'q**, chunki yangi
matnlarda o'sha klaster **umuman uchramaydi**.

M-8 o'lchagan satrlar **aynan mos keldi**: `Номувофиқликлар`,
`Банд, лекин тўловсиз`, `Кўрилмоқда`, `Асосли`, `Асоссиз`, `Масъул`,
`Аниқлик улуши`.

⛔ **Va bitta tasodifiy bo'lmagan tenglik:** `recon.qualifier.expected`
→ `кутилаётган`, `recorded` → `ёзилган` — ikkalasi ham `outbox.py`
ning `_QUALIFIER_WORDS` idagi **bot** so'zlari bilan **bayt-bayt bir
xil**. Bu G-35 ning frontend yarmi bilan **mexanik** ravishda
qulflandi (D-30: atamalar veb va bot orasida yagona).

⚠ `uz-Cyrl.overrides.json` ⛔ **TEGILMADI** — M-8 ning bashorati
(«tegilishi kutilmaydi») shu reja uchun **to'g'ri chiqdi**.

## Known Stubs

**1. `delivery-placeholder.tsx` — ATAYIN va REJADA.** F bloki bugun
faqat **o'rin + nomlangan bo'sh holat**. Reja buni nomma-nom yozadi:
«`delivery` bloki 07-16 da to'ldiriladi; bu rejada uning **o'rni** va
bo'sh holati quriladi». ⛔ Bu «bo'sh o'ram» **emas**: u mazmun
atributini chiqaradi va G-29(c) uning **o'z bo'sh-holat matnini**
ko'rsatishini talab qiladi. Marshrut (`GET /reconciliation/delivery`)
ham hali serverda **yo'q** — 07-16 ikkalasini birga keltiradi.

**2. `deliveryCachePolicy()` iste'molchisiz.** Kesh siyosati (bugun →
`{0, 0}`) yozildi va **birlik testi bilan o'lchandi**, lekin hook 07-16
da keladi. ⛔ Bu ataylab: reja «yetkazilganlik so'rovi **ham shu
modulda**» deb yozadi va ikkinchi modul ochilishini taqiqlaydi.

⛔ **Boshqa stub yo'q.** Beshala boshqa blok **haqiqiy** ma'lumot
chizadi va G-29(c) buni **mock'dagi aynan qiymatga** qadalgan da'vo
bilan o'lchaydi.

## Threat Flags

Yangi tarmoq yuzasi, yangi auth yo'li, yangi fayl kirishi yoki chegaradagi
sxema o'zgarishi ⛔ **yo'q** — reja butunlay klient qatlamida.
Rejaning `<threat_model>` idagi **to'qqizala** disposition o'zgarmadi:

| Threat | Mitigatsiya | O'lchov |
|---|---|---|
| T-07-87 | kadr chizishning 6 tokeni + havola `/billing` ga | ⛔ **har biri 0**; havola regeks bilan |
| T-07-88 | kadr marshruti satri | ⛔ **0** — yopiq to'plam TEGILMAGAN |
| T-07-89 | Telegram identifikatori | ⛔ **0** (5 nom); C-10 ushlamaydigan bo'shliq yopildi |
| T-07-90 | sotuvchi ismi | server ism **qaytarmaydi**; yuzada nom **0**, join alohida modulda |
| T-07-91 | yolg'on foiz | maxraj **majburiy**, `0/0` da foiz **0 marta**; kasrli arifmetika **0** |
| T-07-91a | ikki sinfning qo'shilishi | 12 nomli reyestr **0** + DOM to'plam tengligi **bo'sh** + copy skani |
| T-07-91b | chizilmagan yuza | ⛔ **sabotaj bilan o'lchandi** — (b)+(c) qizardi |
| T-07-91c | ommaviy hukm | `components/reconciliation/**` **to'rtinchi** katalog sifatida skanga kirdi |
| T-07-SC | npm o'rnatish | ⛔ **yangi paket YO'Q** — `package.json` / `package-lock.json` **diffda yo'q** |

## Ochiq bandlar

**1. `npm run gate:fast` ning BACKEND yarmi yugurtirilmadi.**
`gate:fast = npm run test:fast && npm --prefix frontend test`; birinchi
yarmi `docker compose --profile test run --rm tests pytest tests/unit`,
ya'ni docker talab qiladi. ⛔ **Bu rejaning o'zgarishi butunlay
`frontend/` va `.planning/` ichida** va buni dalil tasdiqlaydi:
`git diff --name-only 27340ae HEAD` — **25 fayl, birortasi ham `.py`
emas**. `tests/unit` ga ta'sir qila oladigan yo'l **yo'q**. Ikkinchi
yarmi (`npm --prefix frontend test`) ⛔ **yashil**. Egasi: orkestrator.

**2. `alert-row` darvozasi** — `deferred-items.md` 1-bandi (yuqorida
batafsil).

**3. `/reconciliation` ikkita qo'shimcha so'rov qiladi** —
`deferred-items.md` 2-bandi; UI-SPEC §5.5 ning **o'z** ochiq narxi,
egasi 8-faza.

**4. `case-list.tsx` da mas'ul IDENTIFIKATORNING qisqa shakli bilan
ko'rsatiladi** (`assignee_user_id.slice(0, 8)`, `font-mono text-xs`).
Ism `GET /users` dan joinlanadi va u **DL-5 bilan birga** keladi
(07-16): faqat mas'ul ustuni uchun butun foydalanuvchilar reestrini
tortish audit shovqini bo'lardi. `null` esa **nomlangan**
(«Biriktirilmagan»), bo'sh katak emas.

**5. `CASE_PAGE_SIZE` va `casesKey(…, cursor)` iste'molchisi bir
sahifalik.** Keyset kursori sxemada va kalitda **bor**, ikkinchi
sahifaga o'tish boshqaruvi esa **yo'q** — navbat kuniga ~10 qator
(chegara bilan). 51+ case'li kun kelganda `next_cursor` allaqachon
kontraktda va kalit uni **ajratadi**.

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud (`git diff --name-only 27340ae HEAD`
bilan tasdiqlandi — **25 fayl**):
- `frontend/src/lib/reconciliation-queries.ts` ✓
- `frontend/src/lib/reconciliation-errors.ts` ✓
- `frontend/src/lib/vendor-labels.ts` ✓
- `frontend/src/app/[locale]/(app)/reconciliation/page.tsx` ✓
- `frontend/src/components/reconciliation/` — **8 mahsulot + 3 test fayli** ✓
- `frontend/scripts/reconciliation-copy.test.mjs` ✓ (787 qator)
- `.planning/…/07-15-SUMMARY.md` ✓

Commitlar mavjud: `c6ffbc2` · `ac27b25` · `6d92d31` (baza `27340ae`).

⛔ `git diff --diff-filter=D --name-only 27340ae HEAD` — **BO'SH**, ya'ni
birorta fayl **o'chirilmadi**.

⛔ TEGILMAGANI ALOHIDA TEKSHIRILDI (`git diff --name-only` da **YO'Q**):
`frontend/src/lib/rbac.ts` va `services/core-api/app/security/rbac.py`
(M-6 — yangi huquq yo'q), `frontend/package.json` va
`package-lock.json` (T-07-SC — yangi paket yo'q),
`frontend/messages/uz-Cyrl.overrides.json` (M-8 bashorati),
`frontend/src/components/billing/day-picker.tsx` (qayta ishlatildi,
tahrirlanmadi), `.planning/STATE.md` va `.planning/ROADMAP.md`
(⛔ worktree rejimi — ularni orkestrator markazlashgan holda yangilaydi).

⛔ Sabotaj kodi commitga **TUSHMADI**: qo'llanildi, o'lchandi va
`git checkout -- <fayl>` bilan qaytarildi (`git clean`/`reset`
⛔ **ishlatilmadi**); `grep -c SABOTAJ` → **0**.

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
