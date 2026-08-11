---
phase: 06-billing-va-kassir
plan: 12
subsystem: ui
tags: [nextjs, react, tanstack-query, zod, a11y, i18n, vitest, blind-declaration]

# Dependency graph
requires:
  - phase: 06-billing-va-kassir
    plan: 02
    provides: "`billing-errors.ts` (14 kod, `billingErrorView`), `rbac.ts` da `shift_manage`, uchala locale'dagi `collect.shift*` matni, `NAV_ITEMS` ning ikki yozuvi"
  - phase: 06-billing-va-kassir
    plan: 03
    provides: "`shift-queries.ts` — `shiftCloseResponseSchema` (`z.strictObject`, AYNAN 4 kalit), `useOpenShift`, `useOpenShiftMutation`, `useCloseShift`; `collect-surface.test.mjs` (G-7/G-22/G-28(d))"
  - phase: 06-billing-va-kassir
    plan: 10
    provides: "`POST /shifts/{id}/close` javobida sakkiz maydonning E'LON QILINMASLIGI — D-25 ning server yarmi"
  - phase: 06-billing-va-kassir
    plan: 11
    provides: "`components/collect/` katalogi va uning OLTI mahsulot fayli — `MIN_COLLECT_FILES = 5` chegarasi shu yerda bajarilgan; `api-types.ts` dagi enum ko'zgulari"
provides:
  - "`app/[locale]/(app)/collect/shift/page.tsx` — Y-3 marshruti, `shift_manage` ko'zgusi, URL holati NOL, ikkala shoxi ham komponent chizadigan kompozitsiya"
  - "`components/collect/shift-open-card.tsx` — §10.1 ning IKKI holati, yig'indi yuzasi NOL"
  - "`components/collect/shift-close-form.tsx` — ko'r naqd deklaratsiyasi va DL-4; D-25 ning UCHINCHI (ekran) qatlami"
  - "`components/collect/shift-close-form.test.tsx` — G-7(d) + G-23(b)/(c); sonlar to'plami NOM BILAN BOG'LANMAGAN"
  - "`components/collect/**` katalogi SAKKIZ mahsulot fayliga yetdi — `MIN_COLLECT_FILES` chegarasida 3 fayl zaxira"
affects: [06-13, 06-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Yo'qlik SONLAR TO'PLAMI bilan o'lchanadi, nom bilan emas: DOM matnidan har qanday raqamli qiymat ajratiladi va to'plam AYNAN bitta bo'lishi talab qilinadi — ikkinchi son qanday nom/uslub/elementda paydo bo'lishidan qat'i nazar test qizaradi"
    - "«Aynan N element» IKKI mustaqil kanal bilan qulflanadi: `data-*` to'plami tengligi NOMLANGAN qo'shimchani, bolalar SANOG'I esa NOMLANMAGANINI ushlaydi"
    - "Sxema QAT'IYLIGI ortiqcha kalitning ISHLASH PAYTIDA qurilgan nomi bilan o'lchanadi — qotirilgan nom da'voni yana «aynan o'sha nom» sinfiga qaytarardi"
    - "Noto'g'ri kiritish FILTRLANMAYDI, BELGILANADI: `-5000` ni jimgina `5000` ga aylantirish rad etishdan yomonroq — u kassir yozmagan raqamni yozib qo'yardi"
    - "Jonli hudud `sr-only` bo'lishi mumkin: e'lon KANALI ko'rinadigan elementlar SANOG'INI o'zgartirmaydi"
    - "Matn kaliti yo'q bo'lsa YOLG'ON matn to'qilmaydi va boshqa ma'nodagi kalit QAYTA ISHLATILMAYDI — affordans butunlay chizilmaydi va band kechiktirilgan bandlarga yoziladi"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/collect/shift/page.tsx
    - frontend/src/components/collect/shift-open-card.tsx
    - frontend/src/components/collect/shift-close-form.tsx
    - frontend/src/components/collect/shift-close-form.test.tsx
  modified:
    - .planning/phases/06-billing-va-kassir/deferred-items.md

key-decisions:
  - "06-12: yo'qlik da'vosi NOM BILAN BOG'LANMADI — `distinctNumbers()` DOM matnidan raqam guruhlarini ajratadi va to'plam tengligi bilan o'lchaydi; sabotaj S-D buni `Set{'980000','1200000'}` bilan tasdiqladi"
  - "06-12: `z.strictObject` -> `z.object` sabotaji (S-C) KALITLAR TO'PLAMI da'vosini UMUMAN qizartirmaydi (`.shape` bir xil qoladi) — shuning uchun yuzaga IKKINCHI, nom bilan bog'lanmagan qat'iylik da'vosi qo'shildi; da'vo SUSAYTIRILMADI, yuza KENGAYTIRILDI (05-15 S-D darsi)"
  - "06-12: manfiy qiymat FILTRLANMAYDI — xom holda saqlanadi va `aria-invalid` oladi; filtrlash `-5000` ni `5000` ga aylantirib, kassir yozmagan raqamni yozib qo'yardi va bu jimgina o'tib ketardi"
  - "06-12: §14.5 ning 5-e'lon hududi `sr-only` — aks holda ekranda §10.3 ning uchtasi o'rniga TO'RTTA element bo'lardi va «aynan uchta» shartnomasi o'z matni bilan buzilardi"
  - "06-12: yopish natijasi bloki `data-shift-result-region` + uchta `data-shift-result` bilan nomlanadi, VA bolalar sanog'i marker sanog'iga tenglashtiriladi — nomlanmagan to'rtinchi qator ham ushlanadi"
  - "06-12: yangi tarjima kaliti QO'SHILMADI (06-02 egaligi, `<verification>` talabi) — «Smena ochildi» toasti va noto'g'ri kiritish xatosi matnsiz qoldi; ikkala band `deferred-items.md` ning 8-qatorida"
  - "06-12: `shift_already_open` kelganda ochiq smena so'rovi QAYTA yugurtiriladi — aks holda server «sizda ochiq smena bor» degan bo'lsa ham ekran bo'sh holatda qolib, kassir tugmani qayta bosib turardi"

patterns-established:
  - "Sabotajning IKKALA natijasi ham qiymatli: qizargan da'vo mexanizmni, YASHIL qolgan da'vo esa yuzaning ko'r nuqtasini ko'rsatadi — ikkinchisi tuzatishni testda emas, YUZADA talab qiladi"
  - "Izohdagi taqiqlangan literal xom `grep` mezonini qizartiradi: ma'no saqlanadi, literal olib tashlanadi (`badge.tsx` konvensiyasi)"
  - "Bola marshrut sahifasi kompozitorlik qiladi, karta emas: karta `onRequestClose` bilan XABAR beradi va o'z ikki holatida qoladi"

requirements-completed: [CASH-04]

# Metrics
duration: 50min
completed: 2026-08-11
---

# Phase 6 Plan 12: Ko'r naqd deklaratsiyasi Summary

**Uch fayl, uch commit va bitta to'plam: yopilgandan keyin ekranda ko'rinadigan SONLAR to'plami AYNAN bitta — kiritilgan naqd — va bu da'vo taqiqlangan maydon NOMLARINI umuman aytmaydi, ya'ni ikkinchi son qanday nom, qanday uslub va qaysi elementda paydo bo'lishidan qat'i nazar darvoza qizaradi; sabotaj `Set{'980000','1200000'}` bilan buni tasdiqladi, va kassir `[Smenani yopish]` dan formaga HAQIQATAN yetib boradi, chunki sahifa `closing` shartining IKKALA tarmog'ida ham komponent chizadi.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3 (+ kechiktirilgan band va SUMMARY commit'lari)
- **Files:** 4 yangi mahsulot/test fayli (1069 satr) + `deferred-items.md` ga bitta qator

## Accomplishments

- **⛔ D-25 ning UCHINCHI qatlami qurildi va yo'qlik TO'PLAM TENGLIGI bilan o'lchandi.** Sxema (06-10) va klient tipi (06-03) allaqachon bor edi; bu reja EKRAN qatlamini qo'shdi. Yopilgandan keyin `document.body` matnidan ajratilgan raqam guruhlari to'plami — **`{"980000"}`**, ya'ni AYNAN bitta.
- **⛔ Da'vo NOM BILAN BOG'LANMAGAN va bu uning butun qiymati.** `distinctNumbers()` `textContent` dan `\d[\d\s  .,]*\d` naqshi bo'yicha raqam guruhlarini oladi va ajratmalarni tashlab yuboradi. Ya'ni maydon `systemSoum`, `expected`, `kutilgan` yoki umuman nomsiz bo'lsin — ekranga **ikkinchi son** chiqishi bilan to'plam o'sadi. 05-14 ning S7 sabotaji (inkor tasdiq faqat o'z nomini ushlaydi) bu yerda **strukturaviy jihatdan imkonsiz**.
- **⛔ «Aynan uchta element» IKKI mustaqil kanalda qulflandi.** `data-shift-result` to'plami tengligi **nomlangan** to'rtinchi elementni ushlaydi; natija bloki **bolalarining sanog'i** esa **nomlanmaganini**. Sabotaj S-D aynan ikkinchi kanalga tushdi (`expected 4 to be 3`) — birinchisi **yashil qoldi**, ya'ni yolg'iz o'zi yetmasdi.
- **⛔ KOMPOZITSIYA KONTRAKTI BAJARILDI.** `shift/page.tsx` T2 da `<ShiftCloseForm />` ni **haqiqatan** chizdi (import **va** render) va `closing` holatida `<ShiftOpenCard>` ni **ALMASHTIRDI**. T1 da oldinga murojaat **nol** edi (`grep -cE "ShiftCloseForm|shift-close-form"` → **0**), ya'ni T1 ning `typecheck` darvozasi o'z nuqsonisiz qizarmadi.
- **⛔ §10.4 bajarildi:** kassir yuzasida farq **umuman yo'q** — na maydon, na so'z, na hisob. `collect-surface.test.mjs` ning taqiqlangan token skani sakkizala mahsulot faylida **0** topdi.
- **⛔ Nol RUXSAT, manfiy RAD — va manfiy JIMGINA MUSBATGA AYLANMAYDI.** Uchinchi da'vo ataylab qo'shildi: `replace` bilan filtrlash `-5000` ni `5000` ga aylantirib, kassir **yozmagan** raqamni yozib qo'yardi va ikkala «rad etildi» da'vosi ham yashil qolardi.
- **⛔ Ko'rlik EKRANDA tushuntirildi.** `collect.shiftBlindNotice` maydonning kichik izohiga **tushirilmadi** — u alohida, ko'rinadigan jumla va `aria-describedby` orqali maydonga bog'langan. O'qilmagan tushuntirish tushuntirilmagan ko'rlik bilan bir xil.
- **⛔ `collect-surface.test.mjs` YASHIL KELIB, YASHIL KETDI** — reja bashorat qilganidek. Katalog **6 → 8** mahsulot fayli; chegarada endi **3 fayl zaxira**.
- **Yangi paket o'rnatilmadi** (T-06-SC), **yangi `ui/` primitivi qurilmadi** (M-2), **yangi tarjima kaliti qo'shilmadi** (`i18n:check` → **1095 kalit × 3 til**, o'zgarmadi), **backendga tegilmadi** (`git diff --numstat services/` → **bo'sh**), **`messages/*.json` ga tegilmadi** (qo'shni 06-13 worktree'i bilan merge nizosi ham tug'ilmadi).

## Task Commits

1. **Task 1: `/collect/shift` sahifasi va smena ochish kartasi** — `e627402` (feat)
2. **Task 2: ko'r naqd deklaratsiyasi formasi va sahifa kompozitsiyasi** — `db3afb0` (feat)
3. **Task 3: G-7(d) va G-23(b)/(c) — yo'qlik to'plam tengligi bilan** — `cf27031` (test)

## ⛔ Sabotaj (D-30) — IKKALA natija ham

| # | Sabotaj | Kutilgan | Kuzatilgan |
|---|---------|----------|------------|
| **S-C** | `shift-queries.ts` da `shiftCloseResponseSchema` ning `z.strictObject` i `z.object` ga almashtirildi | 1- va 2-da'volar **qizarishi shart** | ⛔ **4 test QIZARDI**: uchala nomlangan `parse` asserti (`system_total_soum`, `variance_soum`, `system_soum`) **va** nom bilan bog'lanmagan qat'iylik asserti. ⚠ **LEKIN kalitlar to'plami tengligi YASHIL QOLDI** — pastdagi topilmaga qarang |
| **S-D** | Natija blokiga vaqtincha ikkinchi son qo'shildi (`<p className="font-mono">Kutilgan: 1 200 000</p>`, `data-shift-result` **siz**) | 3- va 4-da'volar **qizarishi shart** | ⛔ **2 test QIZARDI**: `expected Set{ '980000', '1200000' } to deeply equal Set{ '980000' }` va `expected 4 to be 3`. ⚠ **LEKIN `data-shift-result` to'plami tengligi YASHIL QOLDI** — element **nomlanmagan** edi |

**⛔ IKKI TOPILMA — ikkalasi ham 05-15 ning S-D sinfi (sabotaj sistemaga yetib boradi, lekin test tanlagan YUZA ikkala shoxda bir xil javob beradi):**

1. **S-C: `.shape` `z.object` ostida O'ZGARMAYDI.** «Sxema `z.strictObject`» degan da'voni `Object.keys(schema.shape)` bilan o'lchash **mumkin emas** — to'plam ikkala holatda ham `{id, status, declared_soum, closed_at}`. Tuzatish **testda emas, YUZADA** bajarildi: ikkinchi, **nom bilan bog'lanmagan** assert qo'shildi — ortiqcha kalitning nomi `unexpected_${Date.now().toString(36)}` bilan **ishlash paytida** quriladi, ya'ni u `z.object` ni nomdan qat'i nazar ushlaydi. ⚠ Ikkala da'vo ham **kerak** va ular **boshqa-boshqa** narsani o'lchaydi: to'plam tengligi «beshinchi maydon E'LON QILINGANMI?», qat'iylik esa «e'lon qilinmagan maydon JIMGINA o'tadimi?».
2. **S-D: `data-*` to'plami tengligi NOMLANMAGAN qo'shimchani ko'rmaydi.** Saboteur atributni qo'ymasa, to'plam `{badge, figure, action}` bo'lib **qoladi**. Shuning uchun yonida **bolalar sanog'i** turibdi (`region.children.length === marked.length`) va aynan **o'sha** qizardi. Bu ham yuzani kengaytirish, assertni almashtirish emas.

⚠ **Ikkala sabotaj ham qaytarildi** (`git checkout -- <fayl>`): `grep -c "z.strictObject" shift-queries.ts` → **6**, `grep -c "Kutilgan" shift-close-form.tsx` → **0**, `git status --short` → toza.

## Files Created/Modified

**Yangi (4):**

- `frontend/src/app/[locale]/(app)/collect/shift/page.tsx` (158) — §4.2/§4.5/§4.6 qarorlari docstringda; `shift_manage` ko'zgusi; `closing` holati; ikkala tarmoq ham komponent chizadi.
- `frontend/src/components/collect/shift-open-card.tsx` (191) — §10.1 ning ikki holati; `EmptyState` §13.7 juftligidan quriladi; `shift_already_open` da qayta so'rov.
- `frontend/src/components/collect/shift-close-form.tsx` (312) — §10.2 formasi, DL-4, §10.3 ning aynan uchta natijasi; `parseDeclaredSoum()` sof funksiya.
- `frontend/src/components/collect/shift-close-form.test.tsx` (408) — beshta da'vo, 14 test.

**Kengaytirilgan (1):**

- `.planning/phases/06-billing-va-kassir/deferred-items.md` — **bitta** yangi qator (8), jadval oxirida (`git diff --stat` → **1 insertion**).

## Decisions Made

- **Yo'riqnoma jumlasi `Field` ning kichik `hint` uyasiga tushirilmadi.** U alohida, `text-sm text-text` bo'lgan paragraf va `id={`${fieldId}-hint`}` orqali maydonning `aria-describedby` iga bog'langan. Sabab: §10.2 ning talabi «ko'rlik **tushuntiriladi**» — `text-xs text-text-muted` bilan chizilgan jumla shaklan bajarib, **ma'nan** buzardi.
- **`role="status"` (§14.5, 5-hudud) `sr-only`.** Aks holda §10.3 ning «aynan uchta narsa» shartnomasi **o'z e'loni bilan** buzilardi. E'lon kanali ko'rinadigan elementlar sanog'idan **mustaqil** bo'lishi kerak.
- **Natija bloki markerlanadi, lekin da'vo markerga TAYANMAYDI.** `data-shift-result` — qulaylik; haqiqiy qo'riqchi ikkita: sonlar to'plami (marker talab qilmaydi) va bolalar sanog'i (marker qo'yilishini talab qilmaydi).
- **Tugma yorliqlari uchta MAVJUD kalitdan taqsimlandi:** forma sarlavhasi va DL-4 tasdig'i — `collect.shiftClose` («Smenani yopish», o'z fe'li), forma yuborish tugmasi — `common.close` («Yopish», §10.2 dagi `[Yopish]`), bekor qilish — `common.cancel`. Uchala rol **turlicha** query bilan ajraladi, ya'ni testda chalkashlik yo'q.
- **DL-4 matni uchta mavjud kalitdan quriladi:** `collect.shiftConfirmBody` + `collect.declaredLabel` + formatlangan naqd. «{summa} kiritildi — yopilsinmi?» uchun alohida kalit **yo'q**, lekin oqibat **summani takrorlab** aytiladi — §10.2 ning talabi shu.
- **Bo'sh maydonda `role="status"` matni `collect.declaredLabel`.** Naqsh 06-11 ning `payment-bar.tsx` idan: u ham `notice === "method"` da to'liq jumla emas, **legend matnini** e'lon qiladi. Ikkinchi naqsh yozilmadi.
- **`shift_already_open` KODDA, izohda emas.** U xulqni boshqaradi (`refetch()`), ya'ni mezonning `grep` i izoh emas, **mexanizm** ustida bajariladi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] `shift_already_open` xatosi ekranni JIM holatda qoldirardi**

- **Found during:** Task 1
- **Issue:** D-27 bo'yicha server ikkinchi smenani 409 bilan rad etadi. Reja faqat xato blokini chizishni talab qiladi, lekin bu holatda ekran hamon **bo'sh holatda** ([Smenani ochish] tugmasi bilan) qolardi: server «sizda ochiq smena bor» deydi, ekran esa «ochiq smena yo'q» deb turadi. Kassir tugmani qayta-qayta bosib, har safar bir xil xatoni olardi.
- **Fix:** `onError` da kod `shift_already_open` bo'lsa `useOpenShift().refetch()` chaqiriladi — karta ikkinchi holatiga (boshlangan vaqt + [Smenani yopish]) o'tadi.
- **Files modified:** `frontend/src/components/collect/shift-open-card.tsx`
- **Verification:** `typecheck` + `lint` toza; `grep -c "shift_already_open"` → **2** (mezon ≥1) va nom **kodda**, izohda emas.
- **Committed in:** `e627402`

**2. [Rule 3 - Blocking] Worktree'da `frontend/node_modules` yo'q edi**

- **Found during:** Boshlanish
- **Issue:** Frontend darvozalari umuman yugurmasdi (06-07/06-08/06-09/06-11 SUMMARY'laridagi holatning **beshinchi** takrori).
- **Fix:** `npm ci` **shu worktree ichida** yugurtirildi. ⛔ Junction/symlink **YARATILMADI** — o'sha xatolik ilgari asosiy checkout'ning nusxasini yo'q qilgan.
- **Files modified:** yo'q (`node_modules` gitignored)
- **Committed in:** — (repoga tegmaydi)

### Reja matnining aniqlashtirilishi (ziddiyat emas)

Beshala holat ham bitta sinf: **mezon xom `grep` bilan o'lchanadi, o'lchanadigan matn esa mezonning O'Z literalini o'z ichiga oladi**. Bu 06-11 da uch marta yuz bergan naqshning davomi; har safar **ma'no saqlandi, literal olib tashlandi** yoki **o'lchov niyatga ko'ra qayta yozildi**.

1. **⛔ `grep -c "/collect/shift" app-shell.tsx` → `0` BAJARILMAYDIGAN.** Fayl **06-02 ning egaligida** va unda qaror **izoh bilan** yozilgan: «`/collect/shift` NAVIGATSIYAGA QO'SHILMAYDI…». Ya'ni literal allaqachon u yerda va uni o'chirish qarorning sababini yo'q qilardi. O'lchov mexanizmga qaratildi: `grep -cE 'href:\s*"/collect/shift"'` → **0** (`NAV_ITEMS` da bunday yozuv **yo'q**).
2. **⛔ T1 izohining matni mezoni bilan ZIDDIYATDA.** Reja izohda `<ShiftCloseForm>` nomini **yozishni** buyuradi, ayni taskning mezoni esa `grep -cE "ShiftCloseForm|shift-close-form"` → **0** ni talab qiladi. Izoh literalsiz qayta yozildi («yopish formasi moduli hali tug'ilmagan…»), `TODO`/`FIXME` **yozilmadi**, ma'no to'liq saqlandi. O'lchov: **0**.
3. **⛔ `grep -cE "\bdisabled=" shift-close-form.tsx` → `0` O'ZIGA ZID** — 06-11 buni allaqachon o'lchagan: `\b` so'z chegarasi va `-` so'z belgisi emas, ya'ni ifoda `aria-disabled=` ni **ham** ushlaydi, `aria-disabled ≥ 1` esa bir vaqtda talab qilingan. O'lchov 06-11 ning shakliga keltirildi: `grep -cE "(^|[^-])\bdisabled="` → **0** (yalang'och `disabled=` yo'q), `grep -c "aria-disabled"` → **2**.
4. **⛔ `grep -cE "hidden|display:\s*none" page.tsx` → `0` MAJBURIY a11y atributi bilan to'qnashadi.** Bezak ikonkasidagi `aria-hidden="true"` §14.1 talabi va `collect/page.tsx` ning naqshi. Bundan tashqari mezon **mening o'z izohimni** ham qizartirdi (izohda taqiqlangan utilitalar literal yozilgan edi). Izoh literalsiz qayta yozildi, o'lchov esa niyatga ko'ra: `grep -cE "(^|[^-])hidden|display:\s*none"` → **0**; faylda `hidden` **bitta** marta va u **`aria-hidden`**.
5. **⛔ `grep -c "not.toContain" shift-close-form.test.tsx` → `0` test faylining O'Z DOCSTRINGIDAN qizardi** — u aynan «bu shakl **ishlatilmaydi**» deb tushuntirardi. Izohlar literalsiz qayta yozildi («inkor tasdiq», «inkor matcher»), ma'no saqlandi. O'lchov: **0**. Bu 06-11 ning `type="number"` va `toBeLessThanOrEqual` holatlarining aynan takrori.

---

**Total deviations:** 2 auto-fixed (1 missing critical functionality, 1 blocking) + 5 reja matnining aniqlashtirilishi
**Impact on plan:** Qamrov kengaymadi. Yangi paket **o'rnatilmadi**, yangi `ui/` primitivi **qurilmadi**, yangi tarjima kaliti **qo'shilmadi**, backendga **tegilmadi**, 06-13 ning birorta fayliga (`billing/**`, `06-UI-SPEC.md`) **tegilmadi**.

## Issues Encountered

- **⚠ `collect.*` da IKKI matn kaliti yo'q va ular to'qib chiqarilmadi.** (a) §13.8 ning **4-toasti** («Smena ochildi») — `collect.shiftOpen` **buyruq** («Smenani ochish»), natija emas; uni toast sifatida ishlatish boshqa ma'nodagi kalitni qayta ishlatish bo'lardi (05-14 darsi). Shuning uchun **toast chizilmaydi** va smena ochilgani kartaning **o'z holat almashuvi** bilan aytiladi (`EmptyState` → boshlangan vaqt kartasi) — bu ham to'liq, ko'rinadigan javob. (b) Deklaratsiya maydoniga **noto'g'ri** qiymat kiritilganda xato **matni** yo'q, faqat `aria-invalid`; `tariffs.amountInvalid` («Summa noldan katta butun son bo'lsin») bu yerda **YOLG'ON** bo'lardi, chunki §10.2 bo'yicha **nol AYNAN ruxsat etilgan**. Ikkala band `deferred-items.md` ning **8-qatorida**, sinfi va egasi bilan.
- **⚠ `gate` ning backend yarmi yugurmadi** (docker; qo'shni 06-13 worktree'i bilan umumiy konteynerlar — 06-08/06-09/06-11 da o'lchangan poyga). Bu reja **frontend-only**: `git diff --numstat services/` → **bo'sh**. Band `deferred-items.md` ning 7-qatorida.
- **⚠ `npm test -- <filtr>` tuzog'iga tushilmadi.** Bitta test fayli `npx vitest run <yo'l>` bilan **to'g'ridan-to'g'ri** yugurtirildi (`npm test` zanjiri **umuman** oraga kirmadi), `node --test` darvozalari esa **nomi bilan** chaqirildi. To'liq zanjir (`npm --prefix frontend test`) T3 dan keyin bir marta yugurtirildi.

## Verification

| Buyruq | Natija |
|---|---|
| `npm --prefix frontend test` (to'liq zanjir) | ✅ `node --test` **182/182** + vitest **670/670** (bazadan **+14**) |
| `npx vitest run .../shift-close-form.test.tsx` | ✅ **14/14** |
| `node --test .../collect-surface.test.mjs .../bulk-action-surface.test.mjs` | ✅ **19/19** |
| `node --test .../collect-surface.test.mjs` (T1 dan OLDIN) | ✅ **11/11** — yashil **KELDI** |
| `node --test .../collect-surface.test.mjs` (T3 dan KEYIN) | ✅ **11/11** — yashil **KETDI** |
| `npm --prefix frontend run typecheck` | ✅ toza |
| `npm --prefix frontend run lint` | ✅ toza |
| `npm --prefix frontend run build` | ✅ `✓ Compiled successfully in 16.5s`; `/[locale]/collect/shift` **uchala** locale'da prerender qilindi |
| `npm --prefix frontend run i18n:check` | ✅ **1095 kalit × 3 til** — yangi kalit **qo'shilmagan**, drift yo'q |
| `gate` frontend segmenti (i18n + test + typecheck + lint + build) | ⏱ **170 s** (06-11 da 231 s; xost tinchroq va `.next` keshi iliq edi) |
| `git diff --numstat services/` | ✅ **bo'sh** (backendga tegilmadi) |
| `git diff --numstat HEAD~3 -- frontend/messages/` | ✅ **bo'sh** (copy'ga tegilmadi) |
| `components/collect/` mahsulot fayllari | **6 → 8** (`MIN_COLLECT_FILES = 5`, zaxira **3**) |

**Qabul mezonlari (Task 1):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `page.tsx` mavjud va `build` uni yig'adi | ✓ uchala locale | ✅ |
| `useSearchParams\|useQueryState\|nuqs\|declared=` → 0 | **0** | ✅ |
| `NAV_ITEMS` da `/collect/shift` → 0 | **0** (`href:` bo'yicha; izoh mezoni uchun yuqoridagi 1-aniqlashtirishga qarang) | ✅ |
| `\.reduce\(\|\bsum\b\|total\|paymentCount\|averag` — karta | **0** | ✅ |
| `system_soum\|variance` — karta | **0** | ✅ |
| `shift_already_open` ≥ 1 | **2** (kodda, izohda emas) | ✅ |
| `onRequestClose` kartada ≥1 **va** sahifada ≥1 | **5** / **1** | ✅ |
| Oldindan murojaat sahifada → 0 | **0** | ✅ |
| Oldindan murojaat kartada → 0 | **0** | ✅ |
| `typecheck` va `lint` toza | ✓ | ✅ |

**Qabul mezonlari (Task 2):**

| Mezon | O'lchov | Natija |
|---|---|---|
| ⛔ Kirish sharti: `components/collect/*.tsx` (testsiz) ≥ 6 | **6** (06-11 bajargan) | ✅ |
| `collect-surface.test.mjs` **YASHIL** | **11/11**, katalogda **8** fayl | ✅ |
| Taqiqlangan nomlar — forma | **0** | ✅ |
| `shiftBlindNotice` ≥ 1 | **2** | ✅ |
| `min-h-14` ≥ 1 | **2** (maydon **va** tasdiq tugmasi) | ✅ |
| `aria-disabled` ≥ 1; yalang'och `disabled=` → 0 | **2** / **0** (mezon ifodasi tuzatildi) | ✅ |
| `ConfirmDialog` ≥ 1 | **2** | ✅ |
| Kompozitsiya: `ShiftCloseForm` ≥ 2 **va** `<ShiftCloseForm` ≥ 1 | **2** / **1** | ✅ |
| Almashtirish: `hidden\|display:none` → 0 | **0** (yagona `hidden` — `aria-hidden`; 4-aniqlashtirish) | ✅ |
| T1 ning bo'sh shoxi qolmagan: `closing…?…null` → 0 | **0** | ✅ |
| `closing…?…<ShiftCloseForm` ≥ 1 | **1** | ✅ |
| `typecheck` va `lint` toza | ✓ | ✅ |

**Qabul mezonlari (Task 3):**

| Mezon | O'lchov | Natija |
|---|---|---|
| `npm --prefix frontend test` to'liq yashil | 182 + 670 | ✅ |
| `not.toContain` → 0 | **0** (5-aniqlashtirish) | ✅ |
| Uchala `parse({...toza, <nom>})` asserti **alohida** | **3** ta alohida `test()` | ✅ |
| Sxema maydonlari to'plami `toEqual` bilan AYNAN to'rtta | `Set{id,status,declared_soum,closed_at}` | ✅ |
| Ko'rinadigan sonlar to'plami AYNAN bitta | `Set{"980000"}` | ✅ |
| Yopilgandan keyingi elementlar to'plami AYNAN uchta | `Set{badge,figure,action}` **+** bolalar sanog'i **3** | ✅ |
| `declared_soum = 0` → so'rov **ketadi** | `closeCalls()[0].declared_soum === 0` | ✅ |
| Manfiy → so'rov **ketmaydi** | `aria-invalid="true"`, `closeCalls()` **0**, DL-4 **ochilmaydi** | ✅ |
| Manfiy jimgina musbatga aylanmaydi | maydon qiymati hamon `-5000` | ✅ |
| Ikkala sabotaj natijasi SUMMARY da | yuqoridagi «Sabotaj» bo'limi | ✅ |
| `collect-surface.test.mjs` yashil; `build` muvaffaqiyatli | 11/11; ✓ | ✅ |

## Known Stubs

Yo'q. Uchala mahsulot fayli ham to'liq implementatsiya qilingan; `TODO`/`FIXME`/placeholder matn yo'q va birorta komponent qotirilgan bo'sh qiymat chizmaydi.

⚠ **Ikki narsa ATAYIN chizilmaydi va ular stub EMAS** (ikkalasi ham `deferred-items.md` 8-qatorida, egasi bilan):

1. **Smena ochilganda toast yo'q** — «Smena ochildi» uchun matn kaliti mavjud emas va boshqa ma'nodagi kalitni qayta ishlatish **rad etildi**. Javob kartaning holat almashuvi bilan beriladi.
2. **Noto'g'ri kiritish uchun xato MATNI yo'q** (faqat `aria-invalid`) — mavjud yagona nomzod matn nolni rad etadi, §10.2 esa nolni **aynan ruxsat etadi**; yolg'on matn chizish rad etildi.

## Threat Flags

Yangi **server** yuzasi ochilmadi — reja frontend-only (`git diff --numstat services/` → bo'sh). Threat register bo'yicha:

- **T-06-74** (yopish ekranida tizim raqami) — ✅ **uch qatlam**: sxema (06-10), `z.strictObject` (06-03), ekran (bu reja). Yopilgandan keyin **aynan uchta** element, **to'plam tengligi** bilan; sabotaj S-D bilan o'lchandi.
- **T-06-75** (ko'rinadigan ikkinchi son) — ✅ 3-da'vo **nom bilan bog'lanmagan**: `document.body` matnidagi raqam guruhlarining **to'plami** aynan bitta. S-D `Set{'980000','1200000'}` bilan qizardi.
- **T-06-76** (ochiq smena kartasidagi yig'indi) — ✅ `\.reduce\(|\bsum\b|total|paymentCount|averag` → **0**; §10.1 taqig'i komponent docstringida sabab bilan.
- **T-06-77** (deklaratsiyani oldindan to'ldirish) — ✅ Y-3 da URL holati **taqiq**: `useSearchParams|useQueryState|nuqs|declared=` → **0**; `Suspense` chegarasi ham **kerak emas** va sabab docstringda.
- **T-06-78** (ikkinchi ochiq smena) — ✅ **uch qatlam**: DB qisman `UNIQUE` (06-04), server 409 (06-10), UI ikkinchi «ochish» tugmasini **ko'rsatmaydi**. ⛔ **To'rtinchi qatlam qo'shildi** (Rule 2): 409 kelganda ekran ochiq smena holatiga **o'zi o'tadi**.
- **T-06-79** (nol naqdni yozib bo'lmasligi) — ✅ `0` **ruxsat** va bu **xulq testida** o'lchandi (`closeCalls()[0].declared_soum === 0`).
- **T-06-SC** (`accept`) — ✅ yangi paket **o'rnatilmadi**; native `<input>` + mavjud `ui/` primitivlari.

⚠ **Yangi klient yuzasi:** `/collect/shift` marshruti `shift_manage` ko'zgusi bilan. Bu **himoya emas**, foydalanuvchi tajribasi — haqiqiy nazorat serverda (`require_permission(SHIFT_MANAGE)`, 06-10).

## User Setup Required

None — tashqi servis sozlamasi talab qilinmadi.

⚠ Ops bandi (blokirovkasiz): parallel worktree'da frontend darvozalarini yugurtirish uchun `npm ci` **shu worktree ichida** bajariladi. ⛔ Junction/symlink **YARATILMAYDI**.

## Next Phase Readiness

- **06-13 (direktor yuzasi, PARALLEL):** bu reja uning birorta fayliga **tegmadi** (`billing/**`, `06-UI-SPEC.md`). `deferred-items.md` ga **bitta** qator qo'shildi (8), jadval **oxirida** — merge trivial (`git diff --stat` → **1 insertion**).
- **06-14 (faza darvozasi):** `gate` ning frontend segmenti **170 s** (o'lchandi, tinch xost, iliq `.next` keshi); backend yarmi bu worktree'da yugurmadi (7-qator). Byudjet **1250 s** — hozircha zaxira bor, lekin **to'liq** `gate` merge'dan keyin bir marta ketma-ket yugurtirilishi kerak.
- **Copy egasi uchun:** `deferred-items.md` ning **6** va **8-qatorlari** bitta tuzatishga birlashadi — uchala locale'ga `collect.recentEmpty`, `collect.shiftOpened`, `collect.declaredInvalid` + `i18n:gen`.
- **`components/collect/**` chegarasi:** **8** mahsulot fayli, `MIN_COLLECT_FILES = 5` — **3 fayl zaxira**, ya'ni keyingi ijrochi bitta faylni ko'chirsa ham darvoza qizarmaydi (lekin ikkitasi tushsa ogohlantiradi).

## Self-Check: PASSED

**Fayllar (5/5 mavjud):** `collect/shift/page.tsx` (158) · `shift-open-card.tsx` (191) · `shift-close-form.tsx` (312) · `shift-close-form.test.tsx` (408) · `deferred-items.md` (+1 qator)

**Commitlar (3/3 topildi):** `e627402` · `db3afb0` · `cf27031`

**`must_haves` artefaktlari:**

| Talab | O'lchov | Natija |
|---|---|---|
| `shift-close-form.tsx` `min_lines: 130` | `wc -l` → **312** | ✅ |
| `shift-close-form.tsx` `contains: shiftBlindNotice` | `grep -c` → **2** | ✅ |
| `shift-close-form.test.tsx` `contains: shiftCloseResponseSchema` | `grep -c` → **7** | ✅ |
| `key_links`: forma → `shiftCloseResponseSchema` | `grep -c` → **1** (docstringda uch qatlamning ikkinchisi nomma-nom); mexanizm — `useCloseShift` → `apiFetch({schema})` | ✅ |
| `key_links`: sahifa → `/collect` | `grep -c` → **6** (qaytish havolasi + qarorlar) | ✅ |
| `key_links`: sahifa → `<ShiftCloseForm />` | import **va** render (`grep -c` → **2**) | ✅ |

**`truths` (7/7):**
kassir deklaratsiyadan oldin tizim raqamini **ko'rmaydi** — maydon sxemada **yo'q**, CSS emas ·
kassir `[Smenani yopish]` dan formaga **yetib boradi** (`page.tsx` T2 ning `<files>` ida va `<ShiftCloseForm />` ni **haqiqatan** chizadi) ·
yopgandan keyin **aynan uchta** narsa (to'plam tengligi **+** bolalar sanog'i) ·
farq kassirga **ko'rsatilmaydi** — sonlar to'plami aynan bitta, da'vo **nom bilan bog'lanmagan** ·
ko'rlik **ekranda tushuntiriladi** (`shiftBlindNotice`, alohida ko'rinadigan jumla) ·
deklaratsiya **`0` ruxsat** (xulq testi bilan o'lchandi) ·
`collect-surface.test.mjs` **yashil kelib yashil ketdi** (11/11 → 11/11, katalog 6 → 8).

---
*Phase: 06-billing-va-kassir*
*Completed: 2026-08-11*
