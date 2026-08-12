---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 16
subsystem: fullstack
tags: [fastapi, sqlalchemy, outbox, nextjs, react, tanstack-query, zod, next-intl, i18n, reconciliation, delivery, gates]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`notification_outbox` leased queue + `outbox_repo` terminal writers (07-06/07-09)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`app/api/v1/reconciliation.py` router + `ChargeListResponse` envelope naqshi (07-10)"
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`/reconciliation` sahifasi, `lib/reconciliation-queries.ts`, `domainKey` konvensiyasi, HOSILA aksent byudjeti (07-15)"
  - phase: 06-billing-va-kassir
    provides: "`charge-detail-dialog.tsx` — o'qish dialogining shabloni; `ui/` primitivlari"
provides:
  - "`GET /reconciliation/delivery?day=&vendor_id=&cursor=&limit=` — BOT-04 ning server yarmi"
  - "`outbox_repo.list_deliveries()` — navbatning FAQAT-O'QISH yuzasi (DeliveryPage/DeliveryRow/DeliveryCursor)"
  - "`components/reconciliation/delivery-list.tsx` + `delivery-badge.tsx` — besh holat, uch kanal"
  - "`components/reconciliation/case-detail-dialog.tsx` — DL-5, fazadagi YAGONA aksent tugma"
  - "`lib/reconciliation-errors.ts::deliveryErrorCode()` — istisno SINFI -> yopiq to'rt a'zoli to'plam"
  - "`lib/vendor-labels.ts::useAssigneeLabels()` — mas'ul ismi skanlanmaydigan modulda"
  - "⛔ G-31 va G-34 darvozalari (copy yarmi + DOM yarmi) va G-34 ning BACKEND LANGARI"
affects: [07-17]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Ko'zgu reyestri BACKEND ENUM'iga langarlanadi (matn sifatida parse) — ichki izchillik emas, TO'LIQLIK o'lchanadi"
    - "Sim maydonining nomi USTUN nomidan farq qiladi, chunki darvoza tokeni PREFIKS bo'yicha ishlaydi (`hitRate*` -> `accuracy*` pretsedentining ikkinchi qo'llanishi)"
    - "Zaxira yorliq kalitlari to'plami NOMLANADI va O'LCHAMI alohida assert bilan qulflanadi (`CONTENT_EXEMPT` naqshi)"
    - "Nol o'tishda yozuv tugmasi `aria-disabled` — server xato KODI to'g'ri, lekin uning MATNI o'sha shoxda yolg'on bo'lardi"
    - "Xom istisno SINFI yopiq to'plamga skanlanmaydigan modulda xaritalanadi"

key-files:
  created:
    - services/core-api/app/repositories/outbox_repo.py (list_deliveries — mavjud faylga)
    - tests/integration/test_delivery_surface.py
    - frontend/src/components/reconciliation/delivery-badge.tsx
    - frontend/src/components/reconciliation/delivery-list.tsx
    - frontend/src/components/reconciliation/case-detail-dialog.tsx
    - frontend/src/components/reconciliation/delivery-list.test.tsx
    - frontend/src/components/reconciliation/case-detail-dialog.test.tsx
  modified:
    - services/core-api/app/api/v1/reconciliation.py
    - services/core-api/app/schemas.py
    - tests/tenancy/test_route_coverage.py
    - tests/tenancy/test_personal_data_coverage.py
    - frontend/src/lib/reconciliation-queries.ts
    - frontend/src/lib/reconciliation-errors.ts
    - frontend/src/lib/vendor-labels.ts
    - frontend/src/lib/api-types.ts
    - frontend/src/components/reconciliation/case-list.tsx
    - frontend/src/components/reconciliation/page.test.tsx
    - frontend/src/app/[locale]/(app)/reconciliation/page.tsx
    - frontend/scripts/reconciliation-copy.test.mjs
    - frontend/messages/{uz-Latn,ru,uz-Cyrl,uz-Cyrl.overrides}.json
  deleted:
    - frontend/src/components/reconciliation/delivery-placeholder.tsx

key-decisions:
  - "⛔ Sim maydoni `last_error_type` -> `error_type`: G-36 tokeni (`last_error`) PREFIKS bo'yicha qidiriladi va XAVFSIZ maydon nomining O'ZI darvozani qizartirardi. Darvozaga istisno YOZILMADI (07-15 pretsedenti)"
  - "⛔ `last_attempt_at` USTUNI YO'Q — `updated_at` qaytariladi; yangi ustun MIGRATSIYA bo'lardi va mavjud qiymatdan ko'proq narsa AYTMASDI"
  - "⛔ Bekor qilishda IKKI domen, uchta emas: `recon-hitrate` kesh kaliti MAVJUD EMAS (07-15 ulushni envelope sanoqlaridan hisoblaydi) — uni bekor qilish NO-OP va izoh YOLG'ON bo'lardi"
  - "⛔ Nol o'tishda `[Holatni saqlash]` `aria-disabled`: server 409 beradi, klient uni «boshqa foydalanuvchi o'zgartirgan» matniga xaritalaydi — nol o'tishda esa HECH KIM hech nima qilmagan"
  - "⛔ Urinishlar MAXRAJSIZ (`2`, `2/5` emas): chegara SERVER konstantasi va javobda YO'Q; klientdagi literal server qiymati o'zgargan kuni jimgina yolg'on gapirardi"
  - "`useAssigneeLabels()` `vendor-labels.ts` da — modul chegarasi «sotuvchi» emas, «shaxsiy ismni TAQIQLANGAN YUZADAN TASHQARIDA o'qish»"
  - "Xato TURI yopiq to'rt a'zoli to'plamga xaritalanadi: `RemoteProtocolError` direktorga hech nima aytmaydi"

patterns-established:
  - "Backend langari: ko'zgu reyestri `enums.py` dan MATN sifatida parse qilinib TENGLIK bilan solishtiriladi"
  - "Zaxira yorliq kalitlari (`unknown`) NOMLANGAN to'plamda va uning o'lchami alohida assert bilan qulflangan"

requirements-completed: [RECON-02, BOT-04]

# Metrics
duration: ~200min (bitta tarmoq uzilishi bilan)
completed: 2026-08-12
---

# Phase 7 Plan 16: Yetkazilganlik yuzasi va nomuvofiqlik hukmi Summary

**Direktor endi «xabar bordimi?» savoliga ekranda javob topadi — va tizim
o'zi isbotlay olmagan narsani DA'VO QILMAYDI: `delivered` matni uchala
tilda «Telegram qabul qildi» ma'nosini beradi, ikki belgili «o'qildi»
glifi esa DOM'da nol marta uchraydi.**

## Performance

- **Duration:** ~200 min (⚠ o'rtada `ENOTFOUND` tarmoq uzilishi; ikkita commit va butun ish daraxti saqlanib qoldi)
- **Tasks:** 3/3
- **Files:** 24 (7 yangi, 16 tahrirlangan, ⛔ **1 o'chirilgan**)

## Task Commits

1. **Task 1: `GET /reconciliation/delivery`** — `4a85cfa` (feat)
2. **Task 2: DL-5 + yetkazilganlik jadvali va yorlig'i** — `28d744d` (feat)
3. **Task 3: G-31 va G-34 darvozalari** — `1029439` (test)

## ⛔ Ikki sabotaj — MAJBURIY, BAJARILDI (va tarmoq uzilishidan KEYIN qayta bajarildi)

Uzilish aynan 2-sabotaj qatorida sodir bo'ldi, shuning uchun ikkalasi ham
⛔ **qayta yugurtirildi** — qismán qo'llangan sabotaj butun yugurishning
dalilini yolg'onga aylantiradigan yagona nosozlik sinfi.

| # | Sabotaj | Kutilgan | ⛔ Natija |
|---|---------|----------|-----------|
| 1 | `ru.json` `recon.deliveryState.delivered` -> «Прочитано» | ⛔ **QIZARISHI SHART** | ⛔ **QIZARDI** — `G-34(b)`: `ru: «прочитан» -> «прочитано»`; **28 pass / 1 fail** |
| 2 | `OutboxStatus` ga oltinchi a'zo (`EXPIRED = "expired"`) | ⛔ **QIZARISHI SHART** | ⛔ **QIZARDI** — backend langari: `backend enum'ida 6 a'zo`, `6 !== 5`; **28 pass / 1 fail** |

⛔ **Ikkalasi ham `git checkout -- <fayl>` bilan qaytarildi** (`git clean` /
`reset` ⛔ **ishlatilmadi**). Qaytargandan keyin o'lchandi:
`git status --porcelain packages/` → ⛔ **BO'SH**; `grep -c EXPIRED
enums.py` → ⛔ **0**; `OutboxStatus` yana **beshta** a'zo;
`ru.deliveryState.delivered` → «Telegram принял».

⚠ **2-sabotaj eng qimmati va sababi 04-10 darsi:** langarsiz ko'zgu
darvozasi **ichki izchillikni** o'lchardi («reyestrda nima bo'lsa, matni
ham bor»). Backend oltinchi holat qo'shsa, frontend reyestri **beshta
bo'lib qolardi** va ⛔ **ikkala darvoza ham yashil qaytardi** — ekranda
esa o'sha holat «Noma'lum» yorlig'i bilan chiqardi.

## ⛔ To'liq to'plam o'lchandi — 07-15 bazasi bilan taqqoslab

| Darvoza | 07-15 BAZA | 07-16 YAKUNIY | Farq |
|---|---|---|---|
| `node --test scripts/*.test.mjs` | 216 pass | ⛔ **223 pass / 0 fail** | **+7** |
| `vitest run` | 783 pass | ⛔ **806 pass / 0 fail** | **+23** |
| Test fayllari | 59 | **61** | +2 |
| `i18n:check` | 1174 kalit × 3 til | ⛔ **1207 kalit × 3 til** | **+33** |
| `build` (SSG) | 75 sahifa | **75 sahifa** | **0** |
| `typecheck` / `lint` | toza | ⛔ **ikkalasi toza** | — |
| Backend `pytest` (⬇ 5 to'plam) | — | ⛔ **795 pass / 0 fail** | — |
| `ruff check` + `ruff format --check` + `mypy` | — | ⛔ **hammasi toza** (337 fayl) | — |

**Backend qamrovi:** `tests/integration/test_delivery_surface.py` (**15
test**) + `tests/tenancy` (to'liq) + `test_reconciliation_api.py` +
`test_outbox_repo.py` + `test_outbox.py` — ya'ni yangi marshrut ham,
u tegadigan **mavjud** yuzalar ham birga o'lchandi.

**+23 vitest taqsimoti:** `delivery-list.test.tsx` **12**,
`case-detail-dialog.test.tsx` **10**, `page.test.tsx` ga qo'shilgan
`delivery` mazmun da'vosi **1**.

**+33 i18n kaliti:** DL-5 matnlari **11** · yetkazilganlik ustunlari va
`blocked` jumlasi **7** · `deliveryState` **6** · `deliveryError` **4** ·
`notificationKind` **5**.

## ⛔ uz-Cyrl QO'LDA tekshirildi — har bir o'zlashma so'z ALOHIDA

`i18n:gen` chiqishi so'zma-so'z o'qildi. ⛔ **07-05 topgan `ns`/`ts`
klasterli defekt sinfi BU REJADA HAQIQATAN UCHRADI** va tuzatildi:

| # | Lotin | Transliterator BERGAN BO'LARDI | ⛔ Yakuniy | Holat |
|---|-------|-------------------------------|-----------|-------|
| 1 | `kvitansiya` | ⛔ **`квитанси`ya** (`ns` klasteri) | ⛔ **`Квитанция`** | ⛔ **DEFEKT TOPILDI — override qo'shildi** |
| 2 | `Telegram` | `Телеграм` | ⛔ **`Telegram`** | ✅ mavjud override ishladi (M-9 bashorati) |
| 3 | `Chat` | — | ⛔ **`Чат`** | ✅ `ch` digrafi to'g'ri; `ns`/`ts` klasteri YO'Q |
| 4 | `Direktor` | — | **`Директор`** | ✅ (kodbazada `Директорга` bilan izchil) |
| 5 | `Tizim` | — | **`Тизим`** | ✅ |
| 6 | `bot` / `botni` | — | **`бот` / `ботни`** | ✅ standart shakl |
| 7 | `hisobot` | — | **`ҳисобот`** | ✅ |
| 8 | `eslatmasi` | — | **`эслатмаси`** | ✅ |

⛔ **1-band batafsil:** `kvitansiyalar` overrayди `uz-Cyrl.overrides.json`
da **allaqachon bor edi** (07-03 dan), lekin o'zbek tili
⛔ **agglyutinativ** — lug'at TOKENni qidiradi, o'zakni emas, ya'ni
`kvitansiya` (qo'shimchasiz shakl) o'sha yozuvga ⛔ **TUSHMASDI**.
Yangi yozuv (`"kvitansiya": "квитанция"`) qo'shildi.

⚠ Shu sababdan `uz-Cyrl.overrides.json` ⛔ **TEGILDI** — M-8 ning «tegilishi
kutilmaydi» bashorati bu reja uchun **noto'g'ri chiqdi**. Faylning O'Z
izohi bu qadamni buyuradi: «Yangi kalitda lug'atdagi so'zning yangi
qo'shimchali shakli paydo bo'lsa, uni shu yerga qo'shing».

⛔ **Boshqa xavf sinflari tekshirildi va HECH BIRI uchramadi:** `ts`
klasteri (`autentifikatsiya` sinfi) — **0**; raqam aralashgan token (`S3`
sinfi) — **0**; apostrofli lotin qo'shimchasi (`Excel` sinfi) — **0**.

## Rejadan chetlanishlar

### Rule 1 — hujjatlararo va kontraktlararo ziddiyat

**1. [Rule 1 - Bug] ⛔ `last_error_type` sim nomi G-36 darvozasini QIZARTIRARDI**

- **Topildi:** Task 2, `deliveryRowSchema` yozilayotganda.
- **Muammo — MEXANIK:** G-36 reyestrida `last_error` tokeni bor va u
  ⛔ **`code.includes(token)`**, ya'ni **PREFIKS** bo'yicha qidiriladi.
  `last_error_type` o'sha satrni **o'z ichiga oladi** — ya'ni maydonning
  ⛔ **XAVFSIZ** varianti (tur nomi, matn emas) darvozani **darhol**
  qizartirardi. Taqiqning SABABI esa aynan xom **matn** (u bot tokenini
  tashiydi), ya'ni darvoza **to'g'ri narsani** qo'riqlaydi, faqat ikkalasini
  **ajrata olmaydi**.
- **Yechim:** sim maydonlari `error_type` va `error_status_code` ga
  o'zgartirildi (USTUN nomlari `notification_outbox` da **o'zgarmadi**).
  ⛔ **Darvozaga istisno YOZILMADI** — 07-15 ning `hitRate*` ->
  `accuracy*` pretsedenti: «... dan tashqari» degan carve-out keyingi
  ijrochi tomonidan kengaytirilardi va reyestr asta-sekin bo'shashardi.
- **Qo'shimcha xossa:** yangi nom **mazmunan ham aniqroq** — maydon
  «oxirgi xato» emas, «xatoning TURI»; `last_` prefiksi `_type` bilan
  bir narsani ikki marta aytardi.
- **Fayllar:** `app/schemas.py`, `app/api/v1/reconciliation.py`,
  `lib/reconciliation-queries.ts`, `tests/integration/test_delivery_surface.py`
- **Tekshiruv:** `assert "last_error_type" not in rows[0]` (integratsiya);
  G-36(a) 16 nomli reyestr → ⛔ **`[]`**
- **Commit:** `28d744d`

**2. [Rule 1 - Bug] `last_attempt_at` USTUNI MAVJUD EMAS**

- **Topildi:** Task 1, `notification_outbox` modelini o'qiganda.
- **Muammo:** Reja qaytariladigan maydonlar ro'yxatida `last_attempt_at`
  ni nomlaydi. Jadvalda bunday ustun ⛔ **umuman yo'q**:
  `created_at`, `updated_at`, `next_attempt_at`, `lease_until` bor.
- **Yechim:** `updated_at` qaytariladi. Holatni o'zgartiradigan
  **beshala** bayonot (`_CLAIM_DUE`, `_MARK_DELIVERED`, `_MARK_TERMINAL`,
  `_RESCHEDULE`, `_RELEASE_EXPIRED`) uni yangilaydi, ya'ni u aynan
  «oxirgi marta nima bo'ldi?» savoliga javob beradi. ⛔ Yangi ustun
  **MIGRATSIYA** bo'lardi (Rule 4 hududi) va mavjud qiymatdan
  **ko'proq narsa aytmasdi**. Sabab ikkala docstringda ham yozildi.
- **Commit:** `4a85cfa`

**3. [Rule 1 - Bug] ⛔ Bekor qilishda IKKI domen, reja so'ragan UCHTA emas**

- **Topildi:** Task 2, `useCaseUpdate()` yozilayotganda.
- **Muammo:** Reja `recon-cases` + **`recon-hitrate`** + `recon-report`
  ni birga bekor qilishni buyuradi. Lekin `recon-hitrate` degan kesh
  kaliti ⛔ **MAVJUD EMAS**: 07-15 aniqlik ulushini `caseListSchema`
  ning **to'rt sanog'idan render paytida** hisoblaydi va
  `hit-rate-card.tsx` `useReconciliationCases()` dan o'qiydi (o'lchandi:
  `grep -n useReconciliation hit-rate-card.tsx` → `useReconciliationCases`).
- **Yechim:** `recon-cases` va `recon-report` bekor qilinadi; ulush
  birinchisi bilan **avtomatik** yangilanadi. ⛔ Mavjud bo'lmagan kalitni
  bekor qilish **NO-OP** bo'lardi va yonidagi izoh («ulush ham
  yangilanadi») ⛔ **YOLG'ON** bo'lib qolardi — kod o'qiyotgan keyingi
  ijrochi uni haqiqat deb qabul qilardi. Sabab funksiya docstringiga
  ochiq yozildi.
- **Commit:** `28d744d`

**4. [Rule 1 - Bug] Urinishlar MAXRAJSIZ ko'rsatiladi**

- **Muammo:** UI-SPEC §11.3 «Urinishlar» ustunini `attempt_count/max_attempts`
  (`2/5`) shaklida ta'riflaydi. `max_attempts` javobda ⛔ **yo'q** va u
  serverning **konstantasi** (`outbox.py::MAX_ATTEMPTS = 5`).
- **Yechim:** faqat `attempt_count`. Maxrajni klientda literal bilan
  yozish serverdagi qiymat o'zgargan kuni ⛔ **jimgina yolg'on**
  gapirardi (05-14 ning «to'qilgan qiymat» darsi); uni javobga qo'shish
  esa konstantani har qatorda takrorlardi. Sabab kod izohida.
- **Commit:** `28d744d`

### Rule 2 — rejada yo'q, lekin usiz kontrakt YOLG'ON gapirardi

**5. [Rule 2 - Missing] ⛔ NOL O'TISH QULFI — server kodi to'g'ri, MATNI yolg'on bo'lardi**

- **Topildi:** Task 2, `SERVER_CODE_MAP` ni o'qiganda.
- **Muammo — ZANJIR:** server bir xil holatga o'tishni **409
  `status_unchanged`** bilan rad etadi (07-10 kontrakti); 07-15 ning
  `SERVER_CODE_MAP` i uni `case_status_conflict` ga xaritalaydi; uning
  matni esa «**Holatni boshqa foydalanuvchi allaqachon o'zgartirgan**».
  Nol o'tishda ⛔ **HECH KIM HECH NIMA QILMAGAN** — ya'ni direktor
  mavjud bo'lmagan poyga haqidagi xabarni o'qirdi va ro'yxatni
  «yangilashga» urinardi.
- **Yechim:** tanlangan holat joriysiga teng bo'lganda `[Holatni
  saqlash]` ⛔ **`aria-disabled`** (⛔ `disabled` **emas** — u fokusni
  yo'qotadi). Poyga shoxi ⛔ **OCHIQ qoladi**: boshqa direktor
  allaqachon o'sha holatga o'tkazgan bo'lsa 409 keladi va o'shanda matn
  ⛔ **ROST** bo'ladi. Ya'ni qulf xato kodini yashirmaydi, uni
  **rostgo'y** qiladi.
- **Tekshiruv:** `case-detail-dialog.test.tsx` — nol o'tishda
  `aria-disabled="true"` va `patchCalls` → **0**
- **Commit:** `28d744d` (test `1029439`)

**6. [Rule 2 - Missing] `deliveryErrorCode()` — xom istisno SINFI ekranga chiqmasin**

- **Muammo:** Server `type(exc).__name__` beradi (`RemoteProtocolError`,
  `ConnectTimeout`, `HTTPStatusError`) va bu ⛔ **TO'G'RI** (D-04: matn
  hech qachon saqlanmaydi). Lekin `RemoteProtocolError` direktorga
  ⛔ **hech nima aytmaydi** va u istisno matnining bir bo'lagiga
  **o'xshaydi**. UI-SPEC §11.3/§14.9 ekranda ⛔ **yopiq to'rt a'zoli**
  to'plamni talab qiladi.
- **Yechim:** `lib/reconciliation-errors.ts` da `DELIVERY_ERROR_CODES` +
  `deliveryErrorCode(errorType, statusCode)`. ⛔ **IKKI KIRISH BIRGA**:
  Telegram `429` ni ham, `400` ni ham AYNAN BIR sinf bilan
  (`HTTPStatusError`) beradi — faqat sinfga qarash «chegara oshdi» bilan
  «chat topilmadi» ni ajrata olmasdi.
- **Nega o'sha modulda:** `components/reconciliation/**` taqiqlangan
  nomlar skanidan o'tadi va sinf nomlarining ro'yxati u yerga
  **taqiqlangan token olib kirishi** mumkin edi.
- **Commit:** `28d744d`

**7. [Rule 2 - Missing] `useAssigneeLabels()` — mas'ul ismi skanlanmaydigan modulda**

- **Muammo:** UI-SPEC §9.3 DL-5 ga «Mas'ul — native `<select>`, bozor
  foydalanuvchilari» bo'limini beradi va 07-15 ning 4-ochiq bandi buni
  nomma-nom 07-16 ga qoldirgan. Ism maydoni `full_name`, u esa G-36
  reyestrida — ya'ni `case-detail-dialog.tsx` uni ⛔ **o'zi o'qiy
  olmaydi**.
- **Yechim:** `lib/vendor-labels.ts` ga qo'shildi (⛔ **`user-labels.ts`
  ochilmadi**). Modulning chegarasi «sotuvchi» **emas** — u ⛔ **shaxsiy
  ISMNI taqiqlangan yuzadan TASHQARIDA o'qish** chegarasi. Ikkinchi
  modul o'sha chegarani **ikkiga** bo'lardi va keyingi ijrochi
  uchinchisini ochish uchun pretsedent topardi.
- **Qo'shimcha xossa:** `user_view` yo'q sessiyada `GET /users`
  ⛔ **umuman yubormaydi**; nofaol foydalanuvchi ⛔ **variantlarda yo'q,
  lekin YORLIQDA bor** (bloklangan xodimga yangi case biriktirib
  bo'lmaydi, ammo u eski audit izida **nomi bilan** ko'rinishi shart).
- **Commit:** `28d744d`

**8. [Rule 2 - Missing] `kvitansiya` overrayди — `ns` klasteri defekti**

- Yuqoridagi «uz-Cyrl QO'LDA tekshirildi» bo'limida batafsil.
- **Commit:** `28d744d`

### Rule 3 — bloklovchi (aniq sonli darvozalar)

**9. [Rule 3 - Blocking] Ikki tenancy darvozasi ANIQ SON bilan qulflangan edi**

- **Muammo:** Yangi marshrut ikkita **aniq sonli** da'voni sindirdi
  (ikkalasi ham `>=` emas, `==`):
  - `test_personal_data_coverage.py::test_the_reconciliation_gate_sees_the_routes`
    → `len(found) == 4`;
  - `test_route_coverage.py::test_the_reconciliation_surface_is_exactly_five_routes`
    → `RECONCILIATION_ROUTES` to'plam tengligi + OpenAPI'da `len == 5`.
- **Yechim:** ikkalasi ham **6 marshrut / 5 yo'l** ga yangilandi va
  ⛔ **da'vo shakli SAQLANDI** (tenglik, «kamida» emas): 07-16 ning
  marshruti ikkala reyestrga ham **nomma-nom** qo'shildi va yangi
  metodning yo'qligi (`{GET}`) o'sha tenglik bilan qulflandi.
  `MINIMUM_PERSONAL_ROUTES` va `MINIMUM_MATRIX_ROUTES` ⛔ **o'zgarmadi**.
- **Nega bu «shunchaki sonni oshirish» EMAS:** o'sha ikki testning
  butun vazifasi — yangi marshrut qo'shgan odamni **shu yerga olib
  kelish**, ya'ni u pastdagi uch da'vo (shaxsiy maydon / Telegram
  identifikatori / binar tasnif) o'z marshrutini ham qamraganini
  **ko'rishi** kerak. Sabab ikkala docstringga yozildi.
- **Commit:** `4a85cfa`

**10. [Rule 3 - Blocking] `page.test.tsx` yetkazilganlik marshrutini mock'lamasdi**

- **Muammo:** 07-15 ning G-29 fayli `/reconciliation/delivery` ni
  mock'lamaydi (o'shanda marshrut yo'q edi) va mock'lanmagan yo'l
  `Promise.reject` ga tushadi. Haqiqiy jadval ulangan zahoti blok
  **xato holatiga** o'tardi va G-29(c) ning bo'sh-holat da'vosi
  ⛔ **BOSHQA sababdan** qizarardi.
- **Yechim:** marshrut mock'landi va ⛔ **G-29(c) ga `delivery` bloki
  uchun mazmun da'vosi QO'SHILDI** (mock'dagi AYNAN holat yorlig'i +
  qator soni) — ya'ni bo'shliq yopilmadi, **kengaytirildi**.
- **Commit:** `28d744d`

### Reja matnining kichik moslashuvi

**11. `deliveriesKey` EMAS, mavjud `deliveryKey`**

Reja `deliveriesKey(marketId, day)` nomini beradi; 07-15 ⛔ **allaqachon**
`deliveryKey(marketId, day)` ni shiplagan (aynan shu shakl, aynan shu
doiralash). Ikkinchi fabrika bir xil kalitni ikki nom bilan yaratardi.
Mavjudi qayta ishlatildi.

---

**Total deviations:** 11 auto-fixed (4 bug, 4 missing-critical, 2 blocking, 1 naming)
**Impact:** Qamrov kengaymadi. ⛔ Yangi npm/pip paketi **yo'q** (T-07-SC),
yangi `ui/` primitivi **yo'q**, yangi rang tokeni **yo'q**,
`rbac.py`/`rbac.ts` juftligi ⛔ **TEGILMADI** (M-6), migratsiya **yo'q**.

## Verification Evidence

| Darvoza | Buyruq | Natija |
|---|---|---|
| Task 1 | `pytest tests/integration/test_delivery_surface.py -q` | ⛔ **15 pass** (reja ≥7) |
| Task 1 | Javobda `payload`/`chat_id`/`text`/`provider_message_id`/`dedupe_key`/`lease_until` — **rekursiv** skan | ⛔ **`[]`** |
| Task 1 | Rekursiv skanerning NAZORATI (`rows[].meta.payload`) | ⛔ **USHLADI** |
| Task 1 | `last_error_type` qiymatida `http` / `api.telegram.org` / probel / `/` | ⛔ **har biri 0** |
| Task 1 | Kassir / nazoratchi sessiyasi | ⛔ **403 / 403** |
| Task 1 | Begona bozor (RLS) — javob tanasida A ning identifikatorlari | ⛔ **0** (va A da 5 qator — nazorat) |
| Task 1 | Keyset: ikki sahifa kesishmasi | ⛔ **bo'sh**; hisoblagichlar sahifadan **mustaqil** |
| Task 1 | Buzilgan kursor | ⛔ **422 `cursor_invalid`** (jim e'tiborsizlik EMAS) |
| Task 1 | ⛔ OpenAPI: `/reconciliation/delivery` ostidagi metodlar | ⛔ **`{GET}` ga TENG** |
| Task 1 | `app/api/v1/notifications.py` mavjudmi | ⛔ **YO'Q** (marshrut mavjud routerda) |
| Task 1 | `ruff check` + `ruff format --check` + `mypy` | ⛔ **hammasi toza** (337 fayl) |
| Task 2 | `grep -c dangerouslySetInnerHTML case-detail-dialog.tsx` | ⛔ **0** |
| Task 2 | `grep -rc CheckCheck components/reconciliation/` | ⛔ **har faylda 0** |
| Task 2 | `ConfirmDialog` / `Qayta yuborish` / `removeQueries` | ⛔ **0 / 0 / 0** |
| Task 2 | `lib/delivery-queries.ts` mavjudmi | ⛔ **YO'Q** (ikkinchi so'rov moduli ochilmadi) |
| Task 2 | `variant="default"` — katalog + so'rov moduli | ⛔ **AYNAN 1** (`case-detail-dialog.tsx`) |
| Task 2 | `variant="destructive"` | ⛔ **0** |
| Task 2 | 16 nomli taqiqlangan reyestr (izohsiz skan) | ⛔ **`[]`** |
| Task 2 | `evidence-link.tsx` ikkinchi marta yozilganmi | ⛔ **YO'Q** — `/billing` literali katalogda **faqat o'sha faylda** |
| Task 3 | `node --test scripts/reconciliation-copy.test.mjs` | ⛔ **29 pass** (22 -> 29) |
| Task 3 | `delivery-list.test.tsx` / `case-detail-dialog.test.tsx` | ⛔ **12 / 10 pass** (reja ≥5 talab qilgan) |
| Task 3 | `<option>` qiymatlari to'plami ↔ `CASE_STATUSES` | ⛔ **TENG** |
| Task 3 | `DELIVERY_STATES` ↔ `enums.py::OutboxStatus` | ⛔ **TENG** (backend langari) |
| Task 3 | `grep -c "enums.py" reconciliation-copy.test.mjs` | ⛔ **≥1** |
| Task 3 | `blocked` qatorida `role="alert"` / `bg-danger` | ⛔ **0 / 0** |
| Task 3 | `blocked` blokidagi interaktiv elementlar to'plami | ⛔ **`{Yangilash}` ga TENG** |
| Task 3 | ⛔ **Ikki sabotaj** | ⛔ **ikkalasi ham QIZARDI** (yuqoridagi jadval) |
| Butun to'plam | `npm --prefix frontend test` | ⛔ **223 node + 806 vitest, 0 fail** |
| Butun to'plam | Backend `pytest` (5 to'plam) | ⛔ **795 pass / 0 fail** |
| Tip / lint | `typecheck && lint` | **ikkalasi toza** |
| i18n | `i18n:check` | **1207 kalit × 3 til**, drift yo'q |
| Build | `build` | ✓ compiled; **75 SSG sahifa** |

## Known Stubs

⛔ **Yo'q.** `delivery-placeholder.tsx` ⛔ **o'chirildi** va uning o'rnini
haqiqiy jadval oldi — ikkita komponent bir slotni da'vo qilib qolmadi.
Beshala blok ham haqiqiy ma'lumot chizadi va G-29(c) buni mock'dagi
**aynan qiymatga qadalgan** da'vo bilan o'lchaydi.

## Threat Flags

Rejaning `<threat_model>` idagi **sakkizala** disposition o'zgarmadi.
Yangi tarmoq yuzasi ⛔ **rejada e'lon qilingan** marshrutdan iborat;
yangi auth yo'li, yangi fayl kirishi va chegaradagi sxema o'zgarishi
⛔ **yo'q** (migratsiya yozilmadi).

| Threat | Mitigatsiya | O'lchov |
|---|---|---|
| T-07-92 | ortiqcha da'vo leksikasi | ⛔ **9 token × 3 locale → 0**; ⛔ **sabotaj bilan o'lchandi** |
| T-07-92a | ikonka matndan boshqa narsa aytishi | ⛔ ikki belgili glif DOM'da **0**; `delivered` da bitta belgi **BOR** |
| T-07-93 | xabar matni / Telegram identifikatori | marshrut qaytarmaydi (**rekursiv skan**) + DOM'da **0** + sxema chegarasida **rad etiladi** |
| T-07-94 | holatni qo'lda o'zgartirish | ⛔ OpenAPI: `{GET}` ga **TENG**; yozuv marshruti **yozilmagan** |
| T-07-95 | yechim matnining XSS'i / uzunligi | `dangerouslySetInnerHTML` **0**; `RESOLUTION_NOTE_MAX` — **bitta konstanta**, server bilan bir son |
| T-07-95a | hukmning noto'g'ri rolga ochilishi | ⛔ yozuv yuzasi **umuman chizilmaydi** (to'plam tengligi bilan); `rbac` juftligi **tegilmadi** |
| T-07-95b | `blocked` ning xato sifatida ko'rsatilishi | `role="alert"` **0**, `bg-danger` **0**, `tone="neutral"` |
| T-07-SC | paket o'rnatish | ⛔ `package.json` / `package-lock.json` / `pyproject.toml` **diffda yo'q** |

## Ochiq bandlar

**1. ⛔ FAQAT mas'ulni o'zgartirish bugun mumkin emas.** Server
`CaseUpdateRequest.status` ni **majburiy** qiladi va nol o'tishni **409**
bilan rad etadi (07-10 kontrakti), ya'ni mas'ul ⛔ **holat o'zgarishi
bilan birga** yoziladi. To'g'ri tuzatish — serverda **alohida
biriktirish amali**, klientda nol o'tishni «jimgina o'tkazish»
⛔ **EMAS** (u soxta audit qatori yozardi). Egasi: 8-faza yoki dala UAT
tetigi. Sabab `case-detail-dialog.tsx` ning modul izohida.

**2. `MAX_ATTEMPTS` ekranda ko'rinmaydi** (4-chetlanish). Urinishlar
maxrajsiz. Kerak bo'lsa to'g'ri shakl — javob envelope'iga **bir marta**
(qator emas, envelope darajasida) qo'shish.

**3. `next_cursor` iste'molchisiz.** Yetkazilganlik kursori sxemada va
javobda **bor**, ikkinchi sahifaga o'tish boshqaruvi esa **yo'q** —
07-15 ning `CASE_PAGE_SIZE` bandi bilan **aynan bir sinf**. Karmana
konvertida bir kunda ~1000 kvitansiya bo'lishi mumkin, ya'ni bu band
`deferred-items.md` 2-bandidan **jiddiyroq** va 8-fazada yopilishi kerak.

**4. `deferred-items.md` 1-bandi (`ALERT_TITLE_KEYS`) TEGILMADI** — u
07-17 niki va fayli (`components/snapshots/**`) bu rejaning to'plamidan
tashqarida. ⚠ **Lekin uning narxi tushdi:** bu rejada qurilgan naqsh
(reyestr → uchala locale, **to'plam tengligi** + nomlangan zaxira
kalitlar istisnosi + o'lchami qulflangan assert) o'sha bandga
⛔ **o'zgarishsiz** ko'chiriladi.

**5. `npm run gate:fast` yaxlit holda yugurtirilmadi**, lekin ikkala
yarmi ham **alohida** o'lchandi: frontend yarmi (`npm --prefix frontend
test`) ⛔ **223 + 806 pass**, backend yarmi esa `tests/unit` o'rniga
⛔ **kengroq** to'plam bilan (`test_delivery_surface` + `tests/tenancy` +
`test_reconciliation_api` + `test_outbox_repo` + `test_outbox`) —
⛔ **795 pass / 0 fail**. Egasi: orkestrator.

## Self-Check: PASSED

Yaratilgan fayllar diskda mavjud (`git diff --name-only 9402b7c HEAD` —
**24 fayl**):
- `services/core-api/app/repositories/outbox_repo.py` ✓ (`list_deliveries`)
- `services/core-api/app/api/v1/reconciliation.py` ✓ (`GET /delivery`)
- `services/core-api/app/schemas.py` ✓ (`DeliveryRow`, `DeliveryListResponse`)
- `tests/integration/test_delivery_surface.py` ✓ (15 test)
- `frontend/src/components/reconciliation/{delivery-badge,delivery-list,case-detail-dialog}.tsx` ✓
- `frontend/src/components/reconciliation/{delivery-list,case-detail-dialog}.test.tsx` ✓
- `frontend/scripts/reconciliation-copy.test.mjs` ✓ (29 test)
- `.planning/…/07-16-SUMMARY.md` ✓

Commitlar mavjud: `4a85cfa` · `28d744d` · `1029439` (baza `9402b7c`).

⛔ `git diff --diff-filter=D --name-only 9402b7c HEAD` — ⛔ **AYNAN BITTA
fayl**: `delivery-placeholder.tsx`, va u ⛔ **ATAYIN** (07-15 uni
07-16 uchun o'rin sifatida qurgan; haqiqiy jadval uning o'rnini oldi).

⛔ **TEGILMAGANI ALOHIDA TEKSHIRILDI** (`git diff --name-only` da **YO'Q**):
`frontend/src/lib/rbac.ts` va `services/core-api/app/security/rbac.py`
(M-6 — yangi huquq yo'q), `frontend/package.json` va
`package-lock.json`, `pyproject.toml` (T-07-SC — yangi paket yo'q),
`packages/sbozor-core/sbozor_core/enums.py` (⛔ **sabotajdan keyin
qaytarildi va o'lchandi**), `migrations/` (migratsiya yo'q),
`.planning/STATE.md` va `.planning/ROADMAP.md` (⛔ worktree rejimi —
ularni orkestrator markazlashgan holda yangilaydi).

⛔ **Ikkala sabotaj ham commitga TUSHMADI:** qo'llandi, o'lchandi va
`git checkout -- <fayl>` bilan qaytarildi (`git clean` / `reset`
⛔ **ishlatilmadi**); `git status --porcelain packages/` → **BO'SH**.

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
