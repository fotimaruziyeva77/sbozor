---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 15
subsystem: ui
tags: [vendors, tariffs, calendar, zones, categories, personal-data, immutability, wcag, sabotage]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-13 — `api-types.ts` sxemalari, `market-queries.ts` ning 35 hooki, `market-errors.ts` ning 23 kodi, to'qqiz i18n namespace'i; 02-02 — yetti `ui/` primitivi (`Skeleton`, `ConfirmDialog`, `EmptyState`, `Field`, `Badge`, `Dialog`, `Select`); 02-09 — tarif/kalendar marshrutlari va `min_valid_from` qiymati; 02-10 — sotuvchi/biriktirish marshrutlari"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`rbac.ts` matritsasi, `auth-store.ts`, `global.ts` kalit xavfsizligi, `gen-cyrillic.mjs` + `check-messages.mjs`, `create-user-dialog.tsx` naqshi"
provides:
  - "`/vendors` — sotuvchi reestri, biriktirish ochish va davrni yopish oqimi"
  - "`/tariffs` — tarif tarixi + zona/toifa reestrlari (yon panel)"
  - "`/calendar` — haftalik ish rejimi va istisno kunlar"
  - "`components/zones/zone-list.tsx` va `components/categories/category-list.tsx` — sahifaga bog'lanmagan, 02-16 ning 2/3-qadamlarida qayta ishlatiladi"
  - "`components/tariffs/tariff-dialog.tsx` — ustaning 4-qadami ham shu dialogni ishlatadi"
  - "`vendor-list.test.tsx` — §8.6 shaxsiy ma'lumot qarorlarining regressiya darvozasi"
affects: [02-16, kassir-moduli, hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Yozuv dialoglari RO'YXAT komponentida yashaydi, sahifada emas — sahifa dialogsiz qolgani uchun audit bildirishini modalga aylantirish MUMKIN emas"
    - "Prop o'zgarganda forma holatini tiklash `key` bilan qayta montaj orqali, effekt ichida `setState` bilan EMAS (`react-hooks/set-state-in-effect`)"
    - "Dinamik tarjima kaliti literal xarita orqali (`WEEKDAY_KEYS`) — `t(`a.b.${x}`)` tip xavfsizligini buzadi"
    - "Ro'yxat testi HTTP qatlamini mock qilmaydi, `queryClient.setQueryData` bilan keshni ekadi — haqiqiy hook va haqiqiy kalit fabrikasi ishlaydi"
    - "Mexanik grep darvozasi bilan to'qnashadigan atama IZOHDA ham yozilmaydi (02-08 dan meros; bu rejada IKKI marta qo'llandi)"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/vendors/page.tsx
    - frontend/src/app/[locale]/(app)/tariffs/page.tsx
    - frontend/src/app/[locale]/(app)/calendar/page.tsx
    - frontend/src/components/vendors/vendor-list.tsx
    - frontend/src/components/vendors/vendor-dialog.tsx
    - frontend/src/components/vendors/assignment-dialog.tsx
    - frontend/src/components/vendors/vendor-list.test.tsx
    - frontend/src/components/tariffs/tariff-list.tsx
    - frontend/src/components/tariffs/tariff-dialog.tsx
    - frontend/src/components/zones/zone-list.tsx
    - frontend/src/components/categories/category-list.tsx
    - frontend/src/components/calendar/weekday-picker.tsx
    - frontend/src/components/calendar/exception-list.tsx
    - frontend/src/components/calendar/exception-dialog.tsx
  modified:
    - frontend/src/components/users/create-user-dialog.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "Audit bildirishi sahifada, yozuv dialoglari ro'yxatda — sahifada `Dialog` importi UMUMAN yo'q"
  - "Tarif dialogida `min` faqat `min_valid_from` dan; bugungi sana FAQAT permissiv qarorlar uchun va u `useNow()`/`useTimeZone()` dan olinadi"
  - "Biriktirishni yopish IKKINCHI modal so'ramaydi — dialogning o'zi forma va oqibat matni tanlangan sana bilan chiqadi"
  - "Zona/toifa QO'SHISH inline, TAHRIRLASH modal — 409 uchun joy kerak (§8.4)"
  - "Test HTTP qatlamini mock qilmaydi — `apiFetch` grep darvozasi test faylini ham qamraydi"

patterns-established:
  - "Pattern: sahifa dialogsiz -> qaror strukturaviy jihatdan buzilmaydi (bildirish modalga aylana olmaydi)"
  - "Pattern: `key` bilan qayta montaj — forma holatini prop bilan sinxronlashning effektsiz yo'li"
  - "Pattern: kesh ekish (`setQueryData`) — HTTP mockisiz komponent testi"

requirements-completed: [MARKET-03, MARKET-04, MARKET-05]

# Metrics
duration: 115min
completed: 2026-08-01
---

# Phase 2 Plan 15: Sotuvchilar, tariflar va ish kunlari ekranlari Summary

**Uchta ekran va o'n to'rtta komponent qurildi; ularning har biri bitta ko'rinmas chegarani foydalanuvchiga ko'rinadigan qildi — shaxsiy ma'lumot o'qilishi ekran boshida e'lon qilinadi, o'tgan tarif qatori amallarsiz qoladi va sababi yoziladi, tushumni nolga tushiruvchi har amal oqibatini nomma-nom aytadi; tarif sanasining chegarasi esa qat'iy serverdan olinadi, ya'ni qoralama bozorda ustaning 4-qadami UI orqali ochiq qoladi.**

## Performance

- **Duration:** ~115 min
- **Tasks:** 3/3
- **Fayllar:** 18 (14 yaratildi, 4 o'zgartirildi), +3976 / −1
- **Testlar:** vitest 18 → **21**, node 54 (o'zgarmadi) — jami **75**
- **i18n kalitlari:** 295 → **366** (×3 til)
- **Yangi npm paketi:** 0

## Accomplishments

- **Uchta ekran ham uchala tilda statik prerender bo'ladi** (`/vendors`, `/tariffs`, `/calendar` × `uz-Latn`/`uz-Cyrl`/`ru`) — navigatsiyadagi 404 qarzining uch bandi yopildi (02-13 "Known Stubs" jadvali).

- **§8.6 shaxsiy ma'lumot qarori STRUKTURAVIY jihatdan qulflandi.** Audit bildirishi `vendors/page.tsx` da, barcha yozuv dialoglari esa `vendor-list.tsx` da yashaydi — ya'ni sahifada `Dialog` importi UMUMAN yo'q va bildirishni "tasdiq oynasiga aylantirish" uchun avval fayl chegarasini buzish kerak bo'ladi. Bu izohdan kuchliroq: qaror kod strukturasida.

- **Ikkita darvoza sabotaj bilan O'LCHANDI va har birida AYNAN kutilgan test yiqildi:**

  | Sabotaj | Yiqilgan test | Nazorat holati |
  |---|---|---|
  | `{t("vendors.auditNotice")}` sahifadan olib tashlandi | AYNAN 1: `audit bildirishi ekranda ko'rinadi va u DIALOG emas` | qolgan 20 ✅ (telefon va badge testlari ham) |
  | Telefon `slice()` bilan maskalandi | AYNAN 1: `telefon tel: havolasi bo'lib chiqadi va MASKALANMAYDI` | qolgan 20 ✅ |

  Uchinchi test (`NAZORAT: rasta kodlari badge bo'lib ko'rinadi`) ikkala sabotajda ham yashil qoldi — ya'ni yuqoridagi ikki test "karta umuman render bo'lmadi" holatini emas, AYNAN o'z da'vosini o'lchaydi.

- **T-02-119a to'liq yopildi va o'lchandi.** `tariff-dialog.tsx` da sana chegarasi hisoblanmaydi: `min={minValidFrom}` javobdan to'g'ridan-to'g'ri keladi, `??`/`||` fallback yo'q, `valid_from` uchun zod `refine` i yozilmagan. Taqiqlangan atamalar grep'i (`new Date()`, `addDays`, `tomorrow`, `ertaga`) — **0**.

- **`min_valid_from` o'tmishda bo'lganda maydon oldindan to'ldiriladi va sabab ko'rsatiladi** (`tariffs.initialHint`), ya'ni qoralama bozorda admin "nega o'tmishdagi sana?" deb o'ylab uni kelajakka surib yubormaydi — aks holda bozor ishlay boshlagan kunlar tarifsiz qolardi.

- **T-02-116 ning klient qatlami qo'yildi:** barcha kunlar olib tashlanganda "Saqlash" `aria-disabled` bo'ladi va SABAB yoziladi (`disabled` emas — o'chirilgan tugma skrinriderga umuman ko'rinmasdi).

- **Almashinuvning bir kunlik xatosi (T-02-117) uch joyda to'siladi:** yopish maydonining doimiy izohi (`vendors.handoverHint`), sana tanlangach chiqadigan oqibat matni (`vendors.closeAssignmentConfirm` — {vendor} va {date} bilan) va DB'dagi `EXCLUDE` konstrayti.

## Task Commits

1. **Task 1: Sotuvchilar reestri va biriktirish oqimi** — `59cfd25` (feat)
2. **Task 2: Tarif tarixi, zona va toifa ro'yxatlari** — `76d5627` (feat)
3. **Task 3: Ish kunlari kalendari** — `9fb35ba` (feat)

## Files Created/Modified

**Yaratildi (14)**

- `app/[locale]/(app)/vendors/page.tsx` — huquq tekshiruvi so'rovdan oldin, §8.6 bildirishi, `Suspense`. **`Dialog` importi YO'Q.**
- `components/vendors/vendor-list.tsx` (400) — `useVendorsQuery` (keyset), to'rt holat, `Skeleton`, maskalanmagan `tel:` havola, rasta kodlari badge'lari, `⋯` amallari.
- `components/vendors/vendor-dialog.tsx` (207) — yaratish/tahrirlash bitta komponentda.
- `components/vendors/assignment-dialog.tsx` (405) — `open`/`close` rejimlari, rasta qidiruvi (kechikish bilan), qoplanish ogohlantirishi.
- `components/vendors/vendor-list.test.tsx` (181) — uchta test (2 darvoza + 1 nazorat).
- `components/tariffs/tariff-list.tsx` (346) — toifa bo'yicha guruhlangan tarix, `is_past` qatorda amallar render qilinmaydi.
- `components/tariffs/tariff-dialog.tsx` (358) — `min` serverdan; permissiv oldindan to'ldirish.
- `components/zones/zone-list.tsx` (392), `components/categories/category-list.tsx` (413) — inline qo'shish, modal rename, 409 da ochiq qoladigan tasdiq.
- `app/[locale]/(app)/tariffs/page.tsx` (143) — ikki ustunli layout, `category` filtri `nuqs` bilan.
- `app/[locale]/(app)/calendar/page.tsx` (151), `components/calendar/weekday-picker.tsx` (245), `exception-list.tsx` (197), `exception-dialog.tsx` (205).

**O'zgartirildi (4)**

- `components/users/create-user-dialog.tsx` — `looksLikeUzbekPhone` **eksport qilindi** (bir qator; xulq o'zgarmadi).
- `messages/{uz-Latn,ru}.json` — 71 yangi kalit; `uz-Cyrl.json` faqat `i18n:gen` bilan.

## Decisions Made

- **Yozuv dialoglari sahifada emas, ro'yxat komponentida.** Qabul mezoni sahifada audit bildirishi dialogda EMASligini talab qiladi. Uni izoh bilan kafolatlash zaif; dialoglarni butunlay boshqa faylga ko'chirish esa buzilishni struktura darajasida imkonsiz qiladi. Narxi — ikkita prop (`createOpen`, `onCreateOpenChange`).
- **Bugungi sana `useNow()` + `useTimeZone()` dan, `new Date()` dan EMAS.** Grep darvozasidan qat'i nazar bu to'g'ri tanlov: vaqt mintaqasi `i18n/request.ts` da BITTA joyda (`Asia/Tashkent`) e'lon qilingan va qo'lda `new Date()` uni ikkinchi marta e'lon qilishga majbur qilardi (FOUND-05 sinfi). Mintaqa noma'lum bo'lsa qulaylikdan voz kechiladi va `min` O'ZGARMAYDI — noaniqlikda hech narsa taqiqlanmaydi.
- **Biriktirishni yopishda ikkinchi modal yo'q.** §10.6 D-4 1-darajali tasdiqni talab qiladi; dialogning o'zi forma bo'lib, tugma yorlig'i o'z fe'li ("Biriktirishni yopish") va oqibat matni TANLANGAN sana bilan chiqadi. Forma ustiga yana modal qo'yish ikki qavatli tasdiq bo'lardi va §10.6 aynan shundan ogohlantiradi (tasdiq refleksga aylanadi).
- **Zona/toifa: qo'shish inline, tahrirlash modal.** Reja qo'shishni inline qiladi (element bitta maydondan iborat). Tahrirlash esa 409 (`zone_name_taken`) berishi mumkin va §8.4 aynan shu sababdan modalni tanlaydi — inline maydonda tushuntirishga joy yo'q.
- **Qoplanish ogohlantirishi TO'SIQ emas** (`role="status"`, tugma bloklanmaydi). Klient serverdan qattiqroq bo'lmasligi kerak; darvoza — DB'dagi `EXCLUDE`.
- **Haftalik jadval tasdig'ida yopiladigan kun bo'lmasa tugma qizil EMAS.** Faqat ish kuni qo'shilayotgan amal destruktiv emas; qizil rangni har tasdiqda ishlatish uning ma'nosini yemiradi.
- **`Ellipsis` ikonkasi** (`MoreHorizontal` — taxallus), 02-13 o'lchoviga muvofiq.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reja `frontend/messages/*` ni `files_modified` da sanamagan, lekin ekranlar 71 ta yangi kalitsiz qurilmasdi**

- **Found during:** Task 1
- **Issue:** Reja mavjud kalitlar bilan kifoyalanishni nazarda tutgan, lekin `vendors` namespace'ida amal yorliqlari (`edit`, `actions`), dialog sarlavhalari, `loadMore`, `resultCount`, biriktirish maydonlari va D-10 ning majburiy tushuntiruvchi matni umuman yo'q edi. `src/global.ts` `uz-Latn.json` ni `AppConfig.Messages` ga bog'laydi, ya'ni mavjud bo'lmagan kalit **kompilyatsiya xatosi** — ekranni "kalitsiz" yozish mumkin emas.
- **Fix:** 71 kalit qo'shildi, FAQAT shu reja egalik qiladigan namespace'larga: `vendors` (+26), `tariffs` (+16), `calendar` (+18), `zones` (+6), `categories` (+6). `common` va `errors` ATAYIN tegilmadi — ular umumiy yuza va 02-14 bilan to'qnashish ehtimoli eng yuqori joy. Xato holatlari uchun yangi kalit o'rniga mavjud `marketErrorMessageKey` naqshi ishlatildi.
- **Files modified:** `frontend/messages/{uz-Latn,ru,uz-Cyrl}.json`
- **Verification:** `i18n:check` — 366 kalit × 3 til, kalit va ICU parity to'liq
- **Committed in:** `59cfd25`, `76d5627`, `9fb35ba`

**2. [Rule 3 - Blocking] `looksLikeUzbekPhone` eksport qilinmagan edi**

- **Found during:** Task 1
- **Issue:** Reja "`create-user-dialog.tsx` dagi mavjud yordamchi QAYTA ISHLATILADI" deydi, lekin funksiya `export` emas. Nusxa ko'chirish ikkita telefon regexi yaratardi va ular bir kun ajralib ketardi — o'shanda bir forma qabul qilgan raqamni ikkinchisi rad etardi (D-12 telefonni bozor ichida YAGONA identifikator qiladi).
- **Fix:** Bitta so'z qo'shildi (`function` -> `export function`) + sabab izohi. Xulq o'zgarmadi; `create-user-dialog.tsx` ning mavjud 21 testi va build yashil qoldi.
- **Files modified:** `frontend/src/components/users/create-user-dialog.tsx`
- **Committed in:** `59cfd25`

**3. [Rule 1 - Bug] Effekt ichida `setState` — lint darvozasi ushladi (IKKI joyda)**

- **Found during:** Task 1 va Task 2
- **Issue:** `vendor-dialog.tsx` da `useEffect` ichida `setFormError(null)`, `zone-list.tsx` da esa `setName(zone.name)` — ikkalasi ham `react-hooks/set-state-in-effect` qoidasini buzadi (kaskad renderlar). Bu typecheck'dan o'tardi va faqat lint uni ushladi.
- **Fix:** (a) `vendor-dialog` da `setFormError` effektdan chiqarildi — u allaqachon `handleOpenChange` da tozalanadi, ya'ni chaqiruv ORTIQCHA edi. (b) `zone-list`/`category-list` da rename dialogi `key={id}` bilan SHARTLI render qilinadi, ya'ni boshlang'ich qiymat `useState(zone.name)` bo'ladi va effekt umuman kerak emas. Xuddi shu naqsh `weekday-picker` ga ham qo'llandi (`key={open_weekdays.join("-")}`).
- **Files modified:** `vendor-dialog.tsx`, `zone-list.tsx`, `category-list.tsx`, `calendar/page.tsx`
- **Committed in:** `59cfd25`, `76d5627`, `9fb35ba`

**4. [Rule 1 - Bug] Grep darvozasi O'Z HUJJATIGA qarshi turdi — IKKI marta**

- **Found during:** Task 1 va Task 2
- **Issue:** (a) `vendor-list.tsx` izohida "Bu faylda `apiFetch` yo'q" deb yozilgan edi — qabul mezoni esa aynan shu atamani papka bo'ylab grep qilib **0** talab qiladi. (b) `tariff-dialog.tsx` izohida `"ertaga"` so'zi turardi va u taqiqlangan atamalar ro'yxatida.
- **Fix:** 02-08 da o'rnatilgan konvensiya qo'llanildi: TAQIQ va uning TO'LIQ sababi saqlandi, atamaning O'ZI literal yozilmadi, ustiga "bu qoida grep bilan qulflangan" ogohlantirishi qo'shildi — keyingi ishlovchi so'zni izohga qaytarib qo'ymaydi.
- **Verification:** ikkala grep ham **0**
- **Committed in:** `59cfd25`, `76d5627`

**5. [Rule 2 - Missing Critical] Test HTTP qatlamini mock qilib, o'z papkasining qoidasini buzardi**

- **Found during:** Task 1
- **Issue:** Birinchi variant `market-picker.test.tsx` naqshini takrorlab `apiFetch` ni mock qilardi. Lekin qabul mezoni `frontend/src/components/vendors` papkasi BO'YLAB grep qiladi va test fayli ham o'sha papkada — ya'ni mezon 4 ta uchrash bilan qizil bo'lardi.
- **Fix:** Test `queryClient.setQueryData(vendorsKey({q: ""}), ...)` bilan keshni ekadi. Bu qamrovni ham OSHIRDI: endi test HAQIQIY `useVendorsQuery` ni, haqiqiy kalit fabrikasini va haqiqiy `pages.flatMap` yassilashini ishlatadi. Kalit bir kun o'zgarsa test jimgina yashil qolmaydi — u bo'sh holat chiqarib yiqiladi. `staleTime: Infinity` majburiy, aks holda ekilgan ma'lumot "eskirgan" deb hisoblanib haqiqiy so'rov ketardi.
- **Files modified:** `vendor-list.test.tsx`
- **Verification:** papka bo'ylab grep **0**; uchala test yashil; ikkala sabotaj kutilganidek qizardi
- **Committed in:** `59cfd25`

**6. [Rule 2 - Missing Critical] `useTimeZone()` `undefined` qaytarishi mumkin edi**

- **Found during:** Task 2
- **Issue:** Typecheck `TimeZone | undefined` ni ushladi. Ahamiyatsiz ko'rinadi, lekin `Intl.DateTimeFormat` ga `timeZone: undefined` uzatilsa u BRAUZERNING o'z mintaqasiga tushadi — boshqa mintaqadagi foydalanuvchida "bugun" bir kunga siljib, `tariffs.initialHint` noto'g'ri holatda chiqardi.
- **Fix:** Yordamchi `string | null` qaytaradi; `null` bo'lsa oldindan to'ldirish ham, izoh ham o'chadi. **`min` esa O'ZGARMAYDI** — o'tmishdagi sanani qo'lda kiritish yo'li ochiq qoladi. Yo'nalish saqlandi: noaniqlikda hech narsa taqiqlanmaydi.
- **Files modified:** `tariff-dialog.tsx`
- **Committed in:** `76d5627`

**7. [Rule 2] Reja ko'rmagan uchta amal qo'shildi**

- **Found during:** Task 1 va Task 3
- **Issue va fix:**
  - `vendor-list` amallar menyusiga **"Biriktirishni yopish"** qo'shildi (`stall_count > 0` bo'lganda). Rejaning o'zi "almashinuv IKKI qadam: avval davrni yopish, so'ng yangi biriktirish" deydi, lekin amallar ro'yxatida faqat "Tahrirlash" va "Rasta biriktirish" sanalgan — birinchi qadamga kirish yo'li bo'lmasdi.
  - `assignment-dialog` ga **qoplanish ogohlantirishi** qo'shildi: rastada ochiq davr bo'lsa `vendors.periodOverlaps` + hozirgi sotuvchi ismi ko'rinadi. Ochiq davr `[from, ∞)` bo'lgani uchun ustiga yangi davr ochish HAR QANDAY sanada 409 beradi — usiz admin sababni faqat yuborgandan keyin bilardi. To'siq EMAS.
  - `exception-list` ga **o'chirish tasdig'i** qo'shildi (`useDeleteException` reja matnida sanalgan, lekin tasdiq talab qilinmagan).
- **Committed in:** `59cfd25`, `9fb35ba`

**8. [Rule 2] Haftalik jadval tasdig'i "o'zgarmagan" holatini ham to'sadi**

- **Found during:** Task 3
- **Issue:** Reja faqat BO'SH to'plamni to'sishni talab qiladi. Lekin hech narsa o'zgarmaganda ham "Saqlash" so'rov yuborardi — bu ma'nosiz `PUT` va ma'nosiz AUDIT yozuvi bo'lardi (haftalik jadval o'zgarishi auditga tushadi va nizo tekshiruvida shovqin yaratardi).
- **Fix:** `isUnchanged` hisoblanadi; tugma `aria-disabled` bo'ladi va `calendar.weekdaysUnchanged` sababi ko'rinadi.
- **Committed in:** `9fb35ba`

---

**Total deviations:** 8 auto-fixed (2 bug, 3 missing-critical, 3 blocking). Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Yangi npm paketi QO'SHILMADI, backend'ga tegilmadi, yangi endpoint yo'q. #1, #2, #5 rejaning o'z bandlari orasidagi yoki reja bilan kodbaza orasidagi haqiqiy ziddiyatlar; #3, #4, #6 darvozalar (lint, grep, typecheck) ushlagan haqiqiy defektlar; #7, #8 reja ko'rmagan to'rtta yo'lni yopadi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `grep -rn "apiFetch" components/vendors` | ✅ **0** (test fayli bilan birga) |
| `grep -rn "apiFetch" components/{tariffs,zones,categories}` | ✅ **0** |
| `grep -rn "apiFetch" components/calendar` | ✅ **0** |
| `grep -rniE "new Date\(\)\|addDays\|tomorrow\|ertaga" tariff-dialog.tsx` | ✅ **0** |
| `grep -rn "date-fns" components/calendar` | ✅ **0** |
| `vendors/page.tsx` da `Dialog` importi | ✅ **YO'Q** (struktura darajasidagi qaror) |
| `min` atributining manbai | ✅ `minValidFrom` (prop) — `??`/`\|\|` fallback **0** |
| `valid_from` uchun zod `refine` | ✅ **YO'Q** (faqat `min(1)` — "to'ldirilgan bo'lsin") |
| `is_past` qatorda amallar | ✅ render QILINMAYDI + `tariffs.pastRowHint` |
| `tariff-list.tsx` da "qulaylik vs darvoza" izohi | ✅ mavjud (`tariffs.pastLocked` bilan birga) |
| `weekday-picker` yorliqlarida `min-h-11` | ✅ mavjud (WCAG 2.5.5) |
| Bo'sh to'plamda "Saqlash" | ✅ `aria-disabled` + `calendar.weekdaysRequired` |
| Istisnolar tartibi | ✅ kamayish (`localeCompare` teskari, nusxa ustida) |
| Sabotaj o'lchovlari (2 ta) | ✅ har birida AYNAN 1 test yiqildi, nazorat yashil |
| Sabotajdan keyin tiklash | ✅ `git status` toza |
| `npm run typecheck` | ✅ exit 0 |
| `npm run lint` | ✅ exit 0 |
| `npm run i18n:check` | ✅ **366 kalit × 3 til**, drift yo'q |
| `npm test` | ✅ **54 node + 21 vitest**, 0 fail |
| `npm run build` | ✅ exit 0 — `/vendors`, `/tariffs`, `/calendar` uchala tilda SSG |
| `git diff --stat frontend/package.json` | ✅ **bo'sh** |
| Commit'larda fayl o'chirilishi | ✅ **0** |

## Issues Encountered

- **Skript bilan qilingan sabotaj YOLG'ON signal berdi.** Birinchi urinishda sabotaj `python` bilan matn almashtirish orqali qilindi va TS faylga yaroqsiz sintaksis tushdi — natijada NAZORAT testi ham yiqildi. Bu "darvoza bitadi" degan xulosani BEKOR qiladi: uchala test yiqilgan bo'lsa, o'lchov komponent umuman render bo'lmaganini ko'rsatadi, da'voning buzilganini emas. Sabotaj `Edit` bilan qayta bajarildi va har biri alohida o'lchandi.
- **`nuqs` test adapteri kerak bo'ldi.** Ro'yxat qidiruv satrini URL'dan o'qiydi, ya'ni testda `NuqsTestingAdapter` (`nuqs/adapters/testing`) bo'lmasa komponent yiqilardi. Yangi paket EMAS — u `nuqs` 2.9.2 ning o'z eksporti.
- **`frontend/node_modules` worktree'da bo'sh edi** — `npm ci` bilan `package-lock.json` dan tiklandi (yangi paket o'rnatilmadi).

## Known Stubs

Yo'q. Uchala ekranning har bir tugmasi haqiqiy endpointga ulangan, birorta komponent `TODO` yoki qattiq yozilgan bo'sh massiv qoldirmaydi.

**Ataylab ochiq qoldirilgan, ko'rinadigan qarz (stub emas):**

| Qarz | Kim yopadi | Bugungi holati |
|---|---|---|
| `errors.loadFailedTitle` / `loadFailedBody` (UI-SPEC §10.5) hamon yo'q | belgilanmagan | Ro'yxatlarning xato holati mavjud `marketErrorMessageKey` naqshini ishlatadi (1-fazadan beri shunday). Bu reja `errors` namespace'iga ATAYIN tegmadi — u umumiy yuza va 02-14 bilan bir vaqtda tahrirlanishi konfliktga olib kelardi |
| `vendor-dialog` va `assignment-dialog` uchun komponent testi yo'q | 02-17 (tekshiruv to'lqini) | Reja aynan uchta testni talab qildi va uchalasi ham `vendor-list` ekranining §8.6 qarorlariga qaratilgan. Dialoglar typecheck + build bilan qoplangan, xulq testi bilan emas |
| `calendar.isOpenLabel` kaliti ishlatilmaydi | 02-16 | Kalit 02-13 dan meros; bu ekranda uning o'rniga `calendar.typeLabel` ("Kun turi") ishlatildi, chunki boshqaruv elementi ikki tanlovli `<select>` |
| Rasta qidiruvi dialog ichida 8 ta natija bilan cheklangan | — | `STALL_SUGGESTION_LIMIT`; qidiruvni aniqlashtirish yo'li ochiq. Sahifalash bu yerda ma'no bermaydi (admin aniq raqamni qidiradi) |

## Threat Flags

Yangi xavfsizlik yuzasi rejaning `<threat_model>` idan tashqarida paydo bo'lmadi: yangi endpoint, yangi auth yo'li, fayl kirishi yoki sxema o'zgarishi YO'Q. Uchala ekran ham 02-13 ning so'rov qatlami orqali ishlaydi.

| Threat ID | Holat |
|-----------|-------|
| T-02-112 | mitigate — §8.6 bildirishi ekran boshida, `<p>` sifatida; regressiya testi bilan qulflangan. Huquq tekshiruvi so'rovdan OLDIN, ya'ni huquqsiz foydalanuvchi uchun `GET /vendors` umuman ketmaydi va audit jurnaliga ma'nosiz "ko'rildi" yozuvi tushmaydi |
| T-02-113 | avoid — telefon maskalanmaydi; qaror izohda to'liq yozilgan va test bilan qulflangan (`*`/`•` belgilari yo'qligi ham tekshiriladi) |
| T-02-114 | mitigate — `is_past` qatorda tugmalar render QILINMAYDI (qulaylik) **va** izoh bu qulaylikni serverdagi 403 darvozasidan aniq ajratadi, "keyingi ishlovchi serverdagisini olib tashlamasin" ogohlantirishi bilan |
| T-02-115 | mitigate — yopiq kun uchun ikkinchi bosqichli tasdiq; matn oqibatni aytadi ("o'sha kunga patta hisoblanmaydi") va sana bilan chiqadi |
| T-02-116 | mitigate — klientda `aria-disabled` + sabab; server pydantic `min_length=1`; DB `CHECK`. Uch qatlamning birinchisi shu rejada |
| T-02-117 | mitigate — `vendors.handoverHint` doimiy izoh sifatida maydon yonida, `vendors.closeAssignmentConfirm` esa sana tanlangach oqibatni takrorlaydi; DB `EXCLUDE` baribir rad etadi |
| T-02-118 | mitigate — `hasPermission` bo'yicha render: direktorda `tariff_manage`/`vendor_manage`/`stall_manage` yo'q, ya'ni u tarixni ko'radi-yu, qo'shish/tahrir/o'chirish tugmalarini umuman ko'rmaydi. Server `require_permission` bilan darvoza |
| T-02-119 | mitigate — `dangerouslySetInnerHTML` qo'shilmadi; DB kontenti (sotuvchi ismi, telefon, zona/toifa nomi, rasta raqami, istisno izohi) faqat matn tugunlari va har biri D-16 izohi bilan belgilangan |
| T-02-119a | mitigate — `min` FAQAT `min_valid_from` dan; klientda sana hisoblanmaydi va `valid_from` uchun refine yozilmagan; ikkalasi ham grep bilan **0** deb o'lchandi. Mintaqa noma'lum bo'lgan chekka holatda ham `min` o'zgarmaydi |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm --prefix frontend run typecheck` | ✅ exit 0 |
| 2 | `npm --prefix frontend run lint` | ✅ exit 0 |
| 3 | `npm --prefix frontend run test:component` | ✅ **21** vitest, 0 fail |
| 4 | `npm --prefix frontend run test:unit` | ✅ **54** node test, 0 fail |
| 5 | `npm --prefix frontend run i18n:check` | ✅ 366 kalit × 3 til, drift yo'q |
| 6 | `npm --prefix frontend run build` | ✅ exit 0; uchala yangi marshrut uchala tilda SSG |
| 7 | `git diff --stat frontend/package.json` | ✅ bo'sh |

## User Setup Required

Yo'q — tashqi xizmat sozlamasi, migratsiya yoki deploy qadami kerak emas. Bu reja backend'ga umuman tegmaydi (`alembic_version` `0010` bo'lib qoladi) va yangi npm paketi o'rnatmaydi.

## Next Phase Readiness

**02-16 (usta) uchun tayyor komponentlar:**

- `ZoneList` va `CategoryList` — sahifaga bog'lanmagan, faqat `canManage` propini oladi. Ustaning 2- va 3-qadamlarida TO'G'RIDAN-TO'G'RI ishlatiladi.
- `TariffDialog` — 4-qadam uchun tayyor. **`minValidFrom` ni chaqiruvchi `useTariffsQuery()` javobidan olib uzatadi va uni HISOBLAMAYDI.** Qoralama bozorda u o'tmishdagi sana bo'ladi va dialog buni o'zi taniydi (maydonni to'ldiradi + izoh chiqaradi).
- `WeekdayPicker` — 7-qadam uchun; `openWeekdays` propini oladi va chaqiruvchi uni `key` bilan qayta montaj qiladi.
- `ExceptionDialog` / `ExceptionList` — 7-qadamning ikkinchi yarmi.

**Konfliktga e'tibor:** bu reja `frontend/messages/{uz-Latn,ru}.json` ga 71 kalit qo'shdi — FAQAT `vendors`/`tariffs`/`calendar`/`zones`/`categories` namespace'lariga. 02-14 `stalls`/`map` namespace'lariga tegishi kutiladi; `common` va `errors` ikkalasida ham tegilmadi. Merge'da konflikt chiqsa u namespace chegarasida bo'ladi va ikkala tomonni ham saqlash to'g'ri hal.

## Self-Check: PASSED

- Da'vo qilingan 14 yangi fayl diskda mavjud (`ls` bilan tekshirildi — quyidagi jadval)
- Da'vo qilingan 4 o'zgartirilgan fayl `git diff --stat 9849d42..HEAD` da ko'rinadi (18 fayl, +3976/−1)
- Uchala vazifa commit'i git tarixida mavjud: `59cfd25`, `76d5627`, `9fb35ba`
- Birorta commit'da fayl o'chirilishi yo'q (`git diff --diff-filter=D` bo'sh)
- Ikki sabotajdan keyin ishchi daraxt toza
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi — orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
