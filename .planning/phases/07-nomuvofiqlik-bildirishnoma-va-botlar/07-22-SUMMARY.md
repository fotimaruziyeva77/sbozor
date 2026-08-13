---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 22
subsystem: frontend
tags: [pagination, keyset-cursor, a11y, money-integrity, i18n, gap-closure]
gap_closure: true
requires:
  - "GET /reconciliation/cases?day=&cursor=&limit= (07-10, 07-20)"
  - "GET /reconciliation/delivery?day=&cursor=&limit= (07-16, 07-19)"
  - "@tanstack/react-query useInfiniteQuery (mavjud paket)"
provides:
  - "useReconciliationCases / useDeliveries — useInfiniteQuery + next_cursor iste'moli"
  - "PagedQuery<TPage, TRow> — rows (birlashma) + counts (BIRINCHI sahifa) o'rami"
  - "[Yana yuklash] boshqaruvi (recon.loadMore) ikkala ro'yxatda"
  - "recon.amountUnit / recon.amountUnknown — nomuvofiqlik yuzasining O'Z pul matni"
  - "G-37 darvozasi — klient pul arifmetikasi taqiqi (taxallus orqali ham)"
  - "G-38 darvozasi — jonli hudud soni va <dl> semantikasi"
affects:
  - "frontend/src/components/reconciliation/* (oltala blok)"
  - "07-23 — frontend/messages/*.json ni kengaytiradi (bu reja yozgan kalitlar ustiga)"
tech-stack:
  added: []
  patterns:
    - "keyset kursor + useInfiniteQuery (market-queries.ts::useStallsQuery etaloni)"
    - "sahifalangan so'rovning yupqa o'rami: rows yig'iladi, counts YIG'ILMAYDI"
    - "aria-disabled + onClick erta return (disabled EMAS — fokus saqlanadi)"
    - "jonli hudud <dl> ning O'ZIDA emas, aria-live O'RAMIDA"
key-files:
  created:
    - frontend/src/components/reconciliation/case-list.test.tsx
  modified:
    - frontend/src/lib/reconciliation-queries.ts
    - frontend/src/lib/reconciliation-queries.test.tsx
    - frontend/src/components/reconciliation/case-list.tsx
    - frontend/src/components/reconciliation/delivery-list.tsx
    - frontend/src/components/reconciliation/delivery-list.test.tsx
    - frontend/src/components/reconciliation/unpaid-list.tsx
    - frontend/src/components/reconciliation/unpaid-list.test.tsx
    - frontend/src/components/reconciliation/unregistered-list.tsx
    - frontend/src/components/reconciliation/hit-rate-card.tsx
    - frontend/src/components/reconciliation/page.test.tsx
    - frontend/scripts/reconciliation-copy.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
decisions:
  - "Sanoqlar BIRINCHI sahifadan o'qiladi, sahifalar bo'ylab YIG'ILMAYDI — server kontrakti bo'yicha ular filtr va sahifadan mustaqil"
  - "Kursor kesh kalitidan olib tashlandi — useInfiniteQuery sahifalarni bitta kalit ostida saqlaydi"
  - "«Qarz» ustuni butunlay olib tashlandi (uchinchi ustun ham qo'shilmadi): ReportRowResponse da outstanding_soum maydoni YO'Q — 07-UI-SPEC §8.3 dan ASOSLI CHETLANISH"
  - "Blok darajasidagi xato keyingi-sahifa xatosidan AJRATILDI: 422 kursor rad etilishi o'z matnini oladi"
  - "recon.amountUnit qo'shildi (headline.amountUnit dan nusxa emas, O'Z kaliti) — IN-05 bog'lanishi uzildi"
metrics:
  duration: "~2 soat"
  completed: 2026-08-13
  tasks: 3
  commits: 3
  files_changed: 15
---

# Phase 7 Plan 22: Sahifalash, pul yaxlitligi va sanoq semantikasi Summary

Navbat va yetkazilganlik ro'yxatlari endi `next_cursor` ni haqiqatan iste'mol qiladi
(`useInfiniteQuery` + `[Yana yuklash]`), `unpaid-list.tsx` dagi klient pul ayirmasi
o'chirildi va to'rtta `<dl>` dan `role="status"` olib tashlanib sahifada bitta jonli
hudud qoldi — uchala nuqson ham yangi mexanik darvozalar bilan qulflandi.

## Nima qilindi

### B-6 — jim qirqilgan navbat (`6fd19a5`)

Nuqsonning o'lchami: `next_cursor` uchala sxemada parse qilinardi va `CASE_PAGE_SIZE = 50`
e'lon qilingan edi — ⛔ **nol iste'molchi bilan**. `useReconciliationCases(day, "")`
kursorni qat'iy bo'sh satrga qadagan, `delivery-list.tsx` da esa «cursor» so'zi umuman
uchramasdi. Sanoqlar server kontrakti bo'yicha kun bo'yicha to'liq kelgani uchun ekran
**«Yangi 120» yozuvini 50 qatorli jadval ustida** ko'rsatardi.

- ikkala hook ham `useInfiniteQuery` ga o'tdi: `initialPageParam: null` +
  `getNextPageParam: (last) => last.next_cursor` — `market-queries.ts::useStallsQuery`
  naqshining aynan nusxasi, yangi shakl o'ylab topilmadi;
- so'rov `limit=CASE_PAGE_SIZE` yuboradi, ya'ni konstanta **haqiqiy iste'molchiga ega**;
  `DELIVERY_PAGE_SIZE` ham qo'shildi (ikkalasi ham server chegarasining ko'zgusi — 50);
- ⛔ **kursor kesh kalitidan olib tashlandi.** `casesKey(marketId, day, cursor)` ->
  `casesKey(marketId, day)`. Kursor kalitda qolsa `useInfiniteQuery` bilan to'qnashardi:
  ikkinchi sahifa YANGI zanjir boshlab, birinchisini **almashtirardi**;
- `PagedQuery` o'rami ikkala iste'molchini bitta shaklga qaratdi — `rows` (barcha
  sahifalarning birlashmasi) va `counts` (⛔ **BIRINCHI** sahifa). `hit-rate-card.tsx`
  ham shu o'ramga o'tdi va **ulush arifmetikasi o'zgarmadi**;
- `[Yana yuklash]`: `variant="secondary"`, `aria-disabled={isFetchingNextPage}`
  (⛔ `disabled` emas — fokus yo'qolmaydi), `onClick` ichida erta `return`.
  `next_cursor === null` da tugma ⛔ **umuman chizilmaydi**.

### 422 kursor — endi ko'rinadigan holat

07-20 o'lchagan xulqni ekranga chiqardim: bazada buzilgan kursor `200` + **bo'sh `rows`**
qaytarardi (ekran jimgina yolg'on gapirardi), endi u `422`. Klientda:

- blok darajasidagi xato (`isError && !isFetchNextPageError`) — «butun blok yiqildi»;
- keyingi-sahifa xatosi (`isFetchNextPageError`) — **alohida matn** (`recon.loadMoreFailed`),
  allaqachon kelgan qatorlar va sanoq **joyida qoladi**.

Ikkalasini bir matn bilan ko'rsatish direktorga ro'yxat butunlay yo'q deb aytardi.

### WR-06 — klient pul arifmetikasi (`f7d0e85`)

`unpaid-list.tsx:182` `expected - paid` ni hisoblardi, holbuki faylning O'Z docstringi
(54-56) «⛔ ARIFMETIKA YO'Q» deb yozgan edi. Ayirma `int` ustida ketgani uchun pul TURI
buzilmasdi, lekin u **ikkinchi haqiqat manbai** edi.

Ayirma va «Qarz» ustuni butunlay o'chirildi; `expected_soum` va `paid_soum` ikki alohida
ustunda, serverdan kelganicha. `null` katak `recon.amountUnknown` matnini oladi — `0` emas,
bo'sh katak ham emas. `t("headline.amountUnit")` -> `t("recon.amountUnit")` (IN-05).

### WR-08 — to'rtta jonli hudud (`f7d0e85`)

`role="status"` `<dl>` ning implicit rolini **almashtiradi**, ya'ni «Yangi 120 Ko'rilmoqda 7»
skrinriderda atama–qiymat bog'lanishini yo'qotib matn oqimiga aylanardi. To'rtala `<dl>` dan
atribut olib tashlandi. `delivery-list` da e'lon `<div aria-live="polite">` **o'ramiga**
ko'chdi — `[Yangilash]` foydalanuvchining ochiq niyati. Qolgan uchtasida jonli hudud umuman
yo'q: ularda foydalanuvchi boshlaydigan yangilash mavjud emas.

### Darvozalar (`ae76324`)

**G-37** — klient pul arifmetikasi taqiqi. Skan ⛔ **ikki shaklni** ham ko'radi:
to'g'ridan-to'g'ri (`row.expected_soum - row.paid_soum`) **va taxallus orqali**
(`const expected = row.expected_soum; … expected - paid`). Ikkinchisi majburiy edi —
**aynan shu shakl kodda turgan edi**, ya'ni faqat birinchisini ko'radigan darvoza o'zi
tug'ilgan nuqsonni o'tkazib yuborib «toza kod» degan yolg'on signal berardi. Skan izohsiz
matnda yuradi (03-07 darsi).

**G-38** — jonli hudud soni. `role="status"` faqat `aria-busy` bilan bir elementda
bo'lishi mumkin; ruxsat etilgan fayllar to'plami nomlangan konstanta
(`ALLOWED_STATUS_ROLES`, o'lchami alohida assert bilan qulflangan); `<dl` ochuvchi tegida
`role=` — 0.

## Ikki sabotaj — o'lchandi va qaytarildi

| # | Sabotaj | Kutilgan | O'LCHANDI |
|---|---------|----------|-----------|
| **S-1** | `getNextPageParam` -> `() => null` (`reconciliation-queries.ts`) | sahifalash da'volari qizaradi; sanoq da'volari yashil qoladi | ✅ `tsc` toza (kompilyatsiya qildi). **8 ta da'vo qizardi**: `case-list.test.tsx` ning yettitasi + `page.test.tsx` ning yangisi. ⛔ `hit-rate-card.test.tsx` — **6/6 YASHIL**, `delivery-list.test.tsx` — **13/13 YASHIL**, `node --test` darvozalari — **36/36 YASHIL**. Blast radius aynan sahifalash bilan chegaralangan |
| **S-2** | `unpaid-list.tsx` ga `expected - paid` QAYTARILDI | G-37 qizaradi va faylni nomma-nom ko'rsatadi | ✅ `tsc` toza. **G-37 qizardi**, 36 tadan **aynan 1 tasi**: `` components/reconciliation/unpaid-list.tsx -> `expected -` ``. DOM yarmi ham qizardi (`⛔ IKKI SON ALOHIDA chiziladi…`), ya'ni statik va DOM darvozalari **bir-birini almashtirmaydi** |

Ikkalasi ham `git checkout -- <fayl>` bilan qaytarildi (⛔ `git clean` / `git reset`
**ishlatilmadi**); qaytarilgandan keyin `git status --porcelain frontend/` — **bo'sh**.

⚠ **S-1 da bitta sanoq da'vosi ham qizardi** va bu halol qayd etilishi kerak:
`case-list.test.tsx` ning «to'rt sanoq ikkinchi sahifadan KEYIN ham o'zgarmaydi» da'vosi
qizardi — lekin **sanoq drift qilgani uchun emas**, balki u avval `[Yana yuklash]` ni
bosishi kerakligi uchun (tugma sabotajda umuman yo'q). Sanoq **arifmetikasining** o'zini
o'lchaydigan `hit-rate-card.test.tsx` to'liq yashil qoldi — darvozaning aniqligi shundan
ko'rinadi.

## uz-Cyrl — QO'LDA tekshirilgan yangi so'zlar

`uz-Cyrl.json` qo'lda tahrirlanmadi (`npm run i18n:gen` bilan qurildi). Har yangi so'z
**yakka-yakka** o'qildi; `ns`/`ts` klasteri alohida qaralди.

| Kalit | uz-Latn | uz-Cyrl (hosil) | ru | Tekshiruv |
|-------|---------|-----------------|-----|-----------|
| `recon.loadMore` | Yana yuklash | **Яна юклаш** | Показать ещё | `Ya`->`я`, `yu`->`ю`, `sh`->`ш` — sof mexanik, ✅ to'g'ri |
| `recon.loadMoreFailed` | Keyingi sahifa yuklanmadi — ro'yxat to'liq emas. | **Кейинги саҳифа юкланмади — рўйхат тўлиқ эмас.** | Следующая страница не загрузилась — список неполный. | ✅ pastdagi so'z-ba-so'z jadval |
| `recon.amountUnit` | so'm | **сўм** | сум | ✅ mavjud `headline.amountUnit` bilan **aynan bir xil** — ikki namespace orasida drift yo'q |
| `recon.amountUnknown` | Noma'lum | **Номаълум** | Неизвестно | ✅ mavjud `recon.caseStatus.unknown` («Noma'lum holat» -> «Номаълум ҳолат») bilan bir o'zak |

**`loadMoreFailed` ning so'z-ba-so'z tekshiruvi** (o'zlashma so'zlar alohida):

| So'z | Hosil | Sinf | Xulosa |
|------|-------|------|--------|
| Keyingi | Кейинги | sof o'zbekcha | ✅ undoshdan keyingi `e` -> `е` (to'g'ri shox) |
| **sahifa** | **саҳифа** | ⚠ **o'zlashma** (arab-fors) | ✅ **to'g'ri** — `h` -> `ҳ` standart shakl; `ns`/`ts` klasteri **yo'q** |
| yuklanmadi | юкланмади | sof o'zbekcha | ✅ |
| **ro'yxat** | **рўйхат** | ⚠ **o'zlashma** (fors) | ✅ **to'g'ri** — `o'` -> `ў` apostrof-digrafi `yo` dan kuchliroq bog'landi |
| to'liq | тўлиқ | sof o'zbekcha | ✅ `q` -> `қ` |
| emas | эмас | sof o'zbekcha | ✅ so'z boshidagi `e` -> `э` (to'g'ri shox) |

⛔ **`ns`/`ts` tuzog'i bu safar ochilmadi va bu tasodif emas:** yangi to'rt satrning
birortasida ham `ns`/`ts` birikmasi **yo'q**, ya'ni `kvitansiya` -> `квитанси…` (07-16 da
tuzatilgan) va `autentifikatsiya` -> `аутентификатсия` sinfidagi semantik defekt paydo
bo'lmadi. Shu sababli `uz-Cyrl.overrides.json` ga **yangi yozuv qo'shilmadi** —
o'zlashmalar (`sahifa`, `ro'yxat`) mexanik qoida bilan to'g'ri chiqdi va ular
allaqachon kodbazada shu shaklda ishlatiladi.

Boshqa ma'lum tuzoqlar ham tekshirildi: raqam-aralash token (`[A-Za-z]+[0-9]`) — yo'q;
apostrofli qo'shimcha (`Excel'ga` sinfi) — yo'q; akronim — yo'q.

## O'lchangan natijalar — HAQIQIY raqamlar

`frontend/node_modules` yangi worktree'da yo'q edi; `npm --prefix frontend install`
bilan o'rnatildi (530 paket, 50 s).

| Darvoza | Baza (bu reja boshlanishida) | Yakun | Izoh |
|---------|------------------------------|-------|------|
| `node --test scripts/*.test.mjs` | **227 pass / 0 fail** | **234 pass / 0 fail** | +7 (G-37: 3, G-38: 4) |
| `vitest run` | **806 pass / 61 fayl** | **833 pass / 62 fayl** | +27 da'vo, +1 fayl |
| `npm run typecheck` | toza | **toza** | |
| `npm run lint` | toza | **toza** | |
| `npm run i18n:check` | 1207 kalit × 3 | **1210 kalit × 3, drift yo'q** | +4 yangi, −1 o'lik (`outstandingColumn`) |
| `npm run build` | — | **✓ 75 SSG sahifa** | 07-16 bazasi bilan bir xil |

⛔ `frontend/package.json` va `frontend/package-lock.json` **diffda yo'q** (T-07-SC).

## Rejadan chetlanishlar

### 1. [Rule 1 — Bug] `<dl>` dan `role` olib tashlanishi `page.test.tsx` ning kalit nuqsonini ochdi

- **Qayerda:** Task 3
- **Muammo:** `page.test.tsx::caseRow(status)` barcha qatorlarga **bir xil** `case_id`
  berardi. Bir sahifada bir nechta qator kerak bo'lganda React takroriy kalitlarni oladi
  va qatorlarni birlashtirish erkinligiga ega bo'ladi — ya'ni «qator soni o'sdi» da'vosi
  o'zi o'lchamoqchi bo'lgan narsani emas, React'ning ichki qarorini o'lchardi.
- **Tuzatish:** `case_id` endi holatdan hosila. Mavjud da'volar (har biri bitta qator
  bilan ishlaydi) tegilmadi.
- **Fayl:** `frontend/src/components/reconciliation/page.test.tsx`
- **Commit:** `ae76324`

### 2. [Rule 3 — Blocking] G-38 darvozasi platformaga bog'liq edi

- **Qayerda:** Task 3
- **Muammo:** `path.relative()` Windows'da `\`, ubuntu'da `/` beradi. Reyestrni bir
  platformaning shakliga qadash darvozani **ikkinchisida** qizartirardi — ya'ni u kod
  haqida emas, operatsion tizim haqida gapirardi. Birinchi yugurishda aynan shundan
  qizardi.
- **Tuzatish:** `posix()` normallashtiruvchisi qo'shildi va izohda sabab yozildi.
- **Commit:** `ae76324`

### 3. [Rule 2 — Missing critical] `422` kursor rad etilishi uchun alohida matn

- **Qayerda:** Task 1
- **Sabab:** Reja «keyingi sahifa» xatosini alohida matn bilan ko'rsatishni ochiq
  talab qilmagan edi, lekin mavjud shox (`isError` -> `errors.loadFailedBody`) 422 da
  **jadval ustida** «yuklab bo'lmadi» deb yozardi — ya'ni ekranda ikki qarama-qarshi
  signal turardi. `recon.loadMoreFailed` qo'shildi va ikki xato ajratildi.
- **Commit:** `6fd19a5`

### 4. [DIZAYN KONTRAKTIDAN ASOSLI CHETLANISH] «Qarz» ustuni chizilmaydi

07-UI-SPEC §8.3 `unpaid` jadvaliga «⛔ **Qarz** (`outstanding_soum`, `font-mono` +
`text-danger-text`)» ustunini yozadi. ⛔ **Kontraktning O'ZI manbani server maydoni deb
ko'rsatgan**, `services/core-api/app/schemas.py::ReportRowResponse` esa
`outstanding_soum` ni **umuman qaytarmaydi** (u faqat `PendingChargeResponse`,
`CashierTotalsResponse` va `ChargeRowResponse` da bor — ular **sotuvchi** kesimida).

Ya'ni ustunni **rost chizishning yo'li yo'q**: yagona imkoniyat klientda ayirish edi va u
aynan WR-06 nuqsoni. Reja bu chetlanishni ochiq buyurgan va sabab `paid_soum` ning O'Z
docstringida yozilgan. Qaror `unpaid-list.tsx` ning modul docstringiga to'liq yozildi.
Bu fazada ayni sinfdagi chetlanishlar allaqachon bor (`case-list.tsx` — sotuvchi ustuni;
`unregistered-list.tsx` — kamera/zona ustunlari).

⚠ **8-faza uchun ochiq band:** agar direktorga rasta-kun kesimidagi qoldiq kerak bo'lsa,
to'g'ri tuzatish — `ReportRowResponse` ga `outstanding_soum` **qo'shish** (server
hisoblaydi), klientga ayirish qo'shish emas.

## Bu reja QILMAGAN ishlar (chegara aniq)

- ⛔ `assignee_not_in_market` (07-20 ning yangi `422` si) uchun klient xato xaritasi va
  locale matnlari — **07-23 ning ishi**, ataylab tegilmadi;
- ⛔ `deliveryCachePolicy()` ning `staleTime`/`gcTime` qarori o'zgarmadi;
  `refetchInterval` yozilmadi (§11.4, T-07-125 `accept`);
- ⛔ `hit_rate` / `recon-hitrate` qayta kiritilmadi — ulush hamon to'rt sanoqdan render
  paytida hisoblanadi (G-36 taqig'i kuchda);
- ⛔ `vendor-labels.ts` joylashuvi va `vendor_view` darvozasi tegilmadi;
- ⛔ Yangi npm paketi yo'q.

## Threat Flags

Yangi xavfsizlik yuzasi topilmadi — reja `<threat_model>` idagi beshala `mitigate`
bandi bajarildi (T-07-122 sahifalash, T-07-123 kursor parse qilinmaydi, T-07-124 G-37,
T-07-126 sanoq yig'ilmaydi, T-07-SC paket diffi bo'sh); T-07-125 `accept` bo'lib qoldi.

## Keyingi qadam uchun eslatma

`07-23` bu reja yozgan `frontend/messages/*.json` ustiga quriladi. To'rt yangi `recon.*`
kaliti (`loadMore`, `loadMoreFailed`, `amountUnit`, `amountUnknown`) qo'shildi va
`outstandingColumn` **o'chirildi** — 07-23 o'sha o'chirilgan kalitga murojaat qilmasligi
kerak.

## Self-Check: PASSED

| Da'vo | Tekshiruv | Natija |
|-------|-----------|--------|
| `case-list.test.tsx` yaratildi | fayl mavjudligi | ✅ FOUND |
| `reconciliation-queries.ts` o'zgardi | fayl mavjudligi | ✅ FOUND |
| `unpaid-list.tsx` o'zgardi | fayl mavjudligi | ✅ FOUND |
| `reconciliation-copy.test.mjs` o'zgardi | fayl mavjudligi | ✅ FOUND |
| `07-22-SUMMARY.md` yaratildi | fayl mavjudligi | ✅ FOUND |
| `6fd19a5` (Task 1) | `git log` | ✅ FOUND |
| `f7d0e85` (Task 2) | `git log` | ✅ FOUND |
| `ae76324` (Task 3) | `git log` | ✅ FOUND |
| Sabotajlar qaytarilgan | `git status --porcelain frontend/` | ✅ BO'SH |
| STATE.md / ROADMAP.md tegilmagan | `git diff --name-only` | ✅ diffda YO'Q |
