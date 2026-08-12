---
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
plan: 05
subsystem: frontend
tags: [nextjs, react, tanstack-query, zod, next-intl, i18n, rbac-free]

# Dependency graph
requires:
  - phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
    provides: "`GET /api/v1/me/headline` — `{metric, value}`, `extra=\"forbid\"`, 403 `headline_unavailable` (07-03)"
  - phase: 06-billing-va-kassir
    provides: "`pending-summary.tsx` `amountUnit` naqshi; kassir ko'rligining uch qatlami (T-06-53, T-06-59, `shifts.py:126`)"
  - phase: 04-bozor-obyektlari
    provides: "`market-queries.ts::domainKey` — kalit doiralash konvensiyasi (04-10)"
  - phase: 01-poydevor
    provides: "`Card`/`Skeleton` primitivlari, `api-client` (`ApiError`), uch locale skeleti"
provides:
  - "`frontend/src/lib/headline-queries.ts` — `z.strictObject` sxemasi, kalit fabrikasi, `useHeadline`"
  - "`HEADLINE_UNIT` — metrika -> birlik reyestri (3 a'zo), `api-types.ts` da"
  - "`components/headline/headline-card.tsx` — ikkinchi sonni ko'rsata olmaydigan karta"
  - "⛔ **G-33** — oltita bandli darvoza (07-UI-SPEC §16.6)"
  - "`headline.*` kalitlari uchala locale'da (ICU plural bilan)"
affects: [07-15, 07-16, 07-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`403` ni `queryFn` ichida `null` ga aylantirish — «huquq yo'q» XATO EMAS, HOLAT"
    - "Birlik matnini SHART emas, REYESTR hal qiladi (`HEADLINE_UNIT`)"
    - "Taqiqni imkonsizlikka aylantirish: rol tokenlari KATALOG darajasida skanerlanadi"
    - "Komponent testida HAR RENDER O'Z `QueryClient` ini oladi (kesh kaliti metrikani o'z ichiga olmaydi)"

key-files:
  created:
    - frontend/src/lib/headline-queries.ts
    - frontend/src/components/headline/headline-card.tsx
    - frontend/src/components/headline/headline-card.test.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/app/[locale]/(app)/dashboard/page.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/uz-Cyrl.overrides.json

key-decisions:
  - "Kalit fabrikasi `domainKey(marketId, \"headline\")` — reja yozgan yalang'och `[marketId, \"headline\"]` shakli RAD ETILDI: u kodbazadagi yagona doiralash konvensiyasini ikkiga bo'lardi"
  - "Xatoda karta CHIZILMAYDI (`null`) — reja `role=\"alert\"` matnini so'ragan edi, UI-SPEC §10.2 uni [QAROR] bilan rad etadi"
  - "`403` `queryFn` ichida `null` ga aylanadi — xato kanaliga tushsa keyingi ijrochi uni TUZATILADIGAN nosozlik deb o'qirdi"
  - "Yorliq kaliti KOMPILYATSIYA VAQTIDA toraytiriladi (`headlineLabelKey`), `t(string)` emas — `next-intl` kalitlari tiplangan"
  - "`kvitansiyalar` -> `квитанциялар` overrides'ga qo'shildi — transliterator `ns`/`ts` birikmasini buzadi va bu ko'rinmas semantik defekt sinfi"

patterns-established:
  - "Rol o'qish taqig'ini KATALOG skani bilan imkonsizlikka aylantirish (`components/<yuza>/**`, izohlar strip, quyi chegara)"
  - "Komponent testida kutish signali sifatida `aria-busy` — formatlangan son ISHLAMAYDI (`Intl` uzilmas bo'shliq qo'yadi, Testing Library uni normalizatsiya qiladi)"

requirements-completed: [RECON-06]

# Metrics
duration: 88min
completed: 2026-08-12
---

# Phase 7 Plan 05: Bosh ekran ko'rsatkichi — frontend (RECON-06) Summary

**Bosh ekranda endi bitta HAQIQIY raqam bor: server huquq bo'yicha tanlaydi, klient uni faqat formatlaydi — va komponent rolni O'QIY OLMAYDI, ya'ni kassirga pul birligi chizish uchun kod yozib bo'lmaydi.**

## Performance

- **Duration:** ~88 min
- **Completed:** 2026-08-12T02:30:31Z
- **Tasks:** 3/3
- **Files:** 9 (3 yangi, 6 tahrirlangan) — ⛔ **hammasi `frontend/` ichida**, birorta Python fayli tegilmagan

## Accomplishments

- **`dashboard/page.tsx` ning 1-fazadan beri turgan va'dasi bajarildi.** O'sha izoh «metrikalar 5- va 6-fazalarda haqiqiy ma'lumot bilan keladi; ularning o'rniga "0" ko'rsatish ma'muriyatga tizim ishlayotgandek tuyulishiga sabab bo'lardi» degan edi. Izoh **o'chirilmadi — yangilandi**: endi bitta haqiqiy raqam bor, qolganlari hamon yo'q.

- **⛔ Fazaning eng nozik UI qarori MEXANIZMGA aylandi.** `components/headline/**` katalogida rol o'qishning to'qqizta izi (`useAuthStore`, `principal`, `roles`, `hasPermission` va besh rol nomi qo'shtirnoq bilan) — **har biri 0**, va bu **hosila skan** bilan o'lchanadi (`readdirSync` rekursiv, izohlar strip, quyi chegara: reyestr ≥9, fayl ≥1). Ya'ni `if (isCashier) { ... }` shoxini yozish uchun avval taqiqlangan nom import qilinishi kerak, va o'sha import **darvozani qizartiradi**.
  ⛔ **Ikkinchi, kutilmagan qatlam o'lchandi** (sabotaj 2, pastda): komponent testi `<AuthProvider>` ni **umuman bermaydi**, ya'ni sessiya do'konini o'qigan komponent **mount ham bo'lmaydi**. Statik skan «yozib bo'lmaydi» deydi, test garnituri esa «ishlatib ham bo'lmaydi».

- **Pitfall 1 birlik matnigacha yopildi.** `HEADLINE_UNIT["headline.receipts_written"] === "count"` — va bu **qiymat bo'yicha** qulflangan, matn bo'yicha emas. Kassir ekranida `so'm` / `сум` / `UZS` **chizilmaydi**; nazorat holati (`revenue_today` da birlik **bor**) bir testda yonma-yon turadi, ya'ni `amountUnit` ni butunlay o'chirgan regressiya ham qizaradi.

- **`403` NOLGA aylanmaydi.** Huquqi mos kelmagan sessiyada (07-03 o'lchoviga ko'ra — `platform_admin`) hook `available: false` beradi, `value` **`undefined`** bo'lib qoladi va karta **umuman chizilmaydi**: `container.firstChild === null`, `textContent === ""`. Nol **o'lchangan qiymat** ma'nosini berardi.

- **Yuza jimgina kengaya olmaydi.** `z.strictObject` — server `secondary_value` qo'shsa klient **parse paytida** yiqiladi. Bu server tomondagi `extra="forbid"` ning **jufti**, o'rnini bosuvchisi emas: bittasini olib tashlash ikkinchisini ochmaydi.

## Task Commits

1. **Task 1: `headline-queries.ts` + `HEADLINE_UNIT` reyestri (W0-F5)** — `5ffc2e5` (feat)
2. **Task 2: `headline-card.tsx` + bosh ekranga ulash + uchala locale** — `48dcc71` (feat)
3. **Task 3: ⛔ G-33 darvozasi** — `eb47848` (test)

## Files Created/Modified

- `frontend/src/lib/headline-queries.ts` *(yangi, 236 qator)* — `headlineResponseSchema` (`z.strictObject`), `HEADLINE_PATH`, `headlineKey`, `useHeadline`, `headlineUnitOf`, `headlineLabelKey`, `isHeadlineMetric`; `HEADLINE_UNIT` shu yerdan qayta eksport qilinadi (UI-SPEC §10.3 uni shu modulda ko'rsatadi).
- `frontend/src/lib/api-types.ts` — `HEADLINE_UNITS`, `HeadlineUnit`, `HEADLINE_UNIT` (3 a'zo), `HeadlineMetric`. Reyestrning **ta'rifi** shu yerda: bu fayl server reyestrlarining klientdagi ikkinchi nusxasi uchun ajratilgan.
- `frontend/src/components/headline/headline-card.tsx` *(yangi, 165 qator)* — bitta son (Display + `font-mono` + `tabular-nums`), bitta yorliq (Body + `text-text-muted`), ichki bo'shliq `p-4` (`lg`, §6.2 — yangi o'lcham so'ralmadi). Ikonka, trend, havola, avtomatik taymer — **yo'q**.
- `frontend/src/components/headline/headline-card.test.tsx` *(yangi, 540 qator)* — **G-33**, oltita band + to'rtta qo'shimcha test.
- `frontend/src/app/[locale]/(app)/dashboard/page.tsx` — `<HeadlineCard marketId={...} />` sarlavhadan **keyin**, `SECTIONS` dan **oldin** (§10.4). Komponentga rol ham, huquq ham **uzatilmaydi**.
- `frontend/messages/{uz-Latn,ru}.json` — `headline` namespace'i (5 kalit). `uz-Cyrl.json` **generatsiya qilindi**; `uz-Cyrl.overrides.json` ga bitta so'z qo'shildi.

## Decisions Made

- **Yorliq kaliti kompilyatsiya vaqtida toraytiriladi.** `next-intl` kalitlari `global.ts` da `uz-Latn.json` dan tiplangan, ya'ni `t(serverBergan_string)` **tip xatosi**. `headlineLabelKey()` noma'lum kalitni `headline.unknown` ga aylantiradi va natija — to'rtta literal kalitning birlashmasi. Bu D-29 ni **kompilyatorga** ham o'rgatadi.
- **Noma'lum metrika KO'RSATILADI, yashirilmaydi** (04-10 darsi): backend to'rtinchi ko'rsatkich qo'shsa ekran «raqam bor, nomi hali tarjima qilinmagan» holatini beradi. Zaxira birlik — ⛔ **`"count"`**, ya'ni eng **kam da'vo qiladigan** standart: `"soum"` bo'lganda ekran noma'lum songa «so'm» yozib, sanoqni pulga aylantirardi (Pitfall 1, orqa eshikdan).
- **`403` `queryFn` ichida ushlanadi, `useQuery` ning xato kanalida emas.** Xato kanalida qolsa u DevTools'da **qizil** holat bo'lib turardi va keyingi ijrochi uni tuzatiladigan nosozlik deb o'qirdi — huquqi yo'q foydalanuvchi uchun esa `403` **to'g'ri javob**.
- **ICU ko'plik faqat ikki SANOQ metrikasida.** `revenue_today` — summa, unda ko'plik grammatik ma'no bermaydi. Ko'plik branch'larida ⛔ `#` **yo'q**: matn ichida son chizilsa ekranda **ikkinchi raqam** paydo bo'lardi va G-33(a) qizarardi. `count` argumenti faqat **shakl tanlash** uchun uzatiladi.
- **ru `review_queue` matni sanoqqa moslashtirildi** («Зона ожидает проверки» / «Зоны ожидают…» / «Зон ожидает…»). Sof tarjima («Очередь на проверку») sanoqqa **umuman bog'lanmaydi**, ya'ni majburiy `plural` o'ramchasi **o'lik bezak** bo'lardi. uz-Latn/uz-Cyrl matnlari §14.3 ning shipping matnida **o'zgarishsiz** qoldi (`other` branch).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reja qabul mezoni kalit fabrikasini kodbazadagi doiralash konvensiyasiga ZID shaklda yozgan**

- **Found during:** Task 1
- **Issue:** Reja `headlineKey("m1")[0] === "m1"` deb yozgan, ya'ni `["m1", "headline"]` yalang'och shaklini. Lekin **rejaning O'ZI keltirgan manba** — `tenant-cache.test.tsx` ning «doiralash qoidasi» — buning teskarisini qulflaydi (o'sha fayl, 175–178: `key[0] === "m"`, `key[1] === marketId`), va `market-queries.ts::domainKey` **butun kodbazada** shu shaklni beradi. Yalang'och kalit `["m", marketId]` prefiksidan **tashqarida** qolardi: kodbazadagi yagona doiralash konvensiyasi ikkiga bo'linardi va prefiks bo'yicha tozalash bu kalitga **yetib bormasdi**.
- **Fix:** `headlineKey = (marketId) => domainKey(marketId, "headline")` → `["m", marketId, "headline"]`. Rejaning ⛔ bilan belgilangan **haqiqiy** qoidasi — «birinchi **ARGUMENT** `marketId`» — to'liq bajarildi; buzilgani faqat mezonning literal `[0]` indeksi. Sabab kod izohida **ochiq** yozildi.
- **Files modified:** `frontend/src/lib/headline-queries.ts`
- **Verification:** `npm --prefix frontend test` (748 vitest) yashil; tenant doiralash testlari tegilmagan
- **Committed in:** `5ffc2e5`

**2. [Rule 1 - Bug] Reja xato holatida `role="alert"` matnini so'ragan — UI-SPEC §10.2 buni [QAROR] bilan RAD ETADI**

- **Found during:** Task 2
- **Issue:** Reja Task 2 amali: «xatoda `role="alert"` bilan qisqa matn». UI-SPEC §10.2 esa **jadval qatorida** ham, alohida [QAROR] bandida ham teskarisini yozadi: «Xato — ⛔ **Karta umuman chizilmaydi** (`null`)… bosh ekranda "ko'rsatkichni yuklab bo'lmadi" qizil bloki — foydalanuvchi **hech narsa qila olmaydigan** shovqin». Qo'shimcha: §14.9 xato kontrakti har xato matnidan **SABAB + NIMA QILISH KERAK** talab qiladi — bu yerda ikkalasi ham yo'q, ya'ni rejadagi «qisqa matn» §14.9 ni ham buzardi. Uchinchi ziddiyat: reja `unavailable` kalitini qo'shishni **taqiqlaydi** («o'lik matn bo'lardi»), lekin alert uchun aynan shunday kalit kerak bo'lardi.
- **Fix:** Tarmoq xatosida ham, `403` da ham komponent `null` qaytaradi. Bog'lovchi hujjat sifatida UI-SPEC olindi (topshiriq uni «binding for this frontend plan» deb belgilagan). Sabab komponent docstringida **ochiq** yozildi.
- **Files modified:** `frontend/src/components/headline/headline-card.tsx`
- **Verification:** `⛔ tarmoq xatosida ham karta chizilmaydi (qizil blok YO'Q, §10.2)` testi
- **Committed in:** `48dcc71`

**3. [Rule 2 - Missing critical] `kvitansiyalar` transliteratsiyasi ko'rinmas semantik defekt bergan**

- **Found during:** Task 2 (`i18n:gen` natijasini o'qishda)
- **Issue:** Transliterator `kvitansiyalar` → ⛔ **`квитансиялар`** berdi; o'zbek kirillchasida to'g'ri shakl — **`квитанциялар`**. Bu `messages/README.md` **Qoida 5** da ta'riflangan **uchinchi, ko'rinmas** defekt sinfi: chiqishda na lotin harfi, na `ъ` bor, ya'ni mavjud skript darvozasi (`gen-cyrillic.test.mjs`) uni **ko'rmaydi**. UI-SPEC §14.4 [M-8] «overrides tegilishi kutilmaydi» degan edi, lekin o'sha o'lchov faqat **mexanik** defektlarni qamragan.
- **Fix:** `uz-Cyrl.overrides.json` → `words` ga bitta yozuv (`kvitansiyalar` → `квитанциялар`) — `litsenziya`/`autentifikatsiya` bilan **aynan bir xil** mexanizm. Yangi mexanizm yozilmadi; `uz-Cyrl.json` **qo'lda tahrirlanmadi** (`i18n:gen` bilan qayta hosil qilindi).
- **Files modified:** `frontend/messages/uz-Cyrl.overrides.json`, `frontend/messages/uz-Cyrl.json`
- **Verification:** `npm --prefix frontend run i18n:check` → «drift yo'q» + 1114 kalit × 3 til parity; `npm --prefix frontend test` da `gen-cyrillic.test.mjs` yashil
- **Committed in:** `48dcc71`

---

**Total deviations:** 3 auto-fixed (2 bug, 1 missing-critical)
**Impact on plan:** Qamrov kengaymadi. Birinchi ikkisi rejaning **hujjatlararo ziddiyatini** hal qildi va ikkalasida ham bog'lovchi manba (kodbaza konvensiyasi / UI-SPEC) tanlandi; uchinchisi mavjud mexanizmni qayta ishlatdi. ⛔ Yangi npm paketi **qo'shilmadi** (T-07-SC), yangi `ui/` primitivi **qurilmadi** (§3.2), yangi bo'shliq/tipografiya o'lchami **so'ralmadi** (§6.2, §7.1).

## ⛔ Sabotaj natijalari (ikkalasi ham BAJARILDI)

| # | Sabotaj | Kutilgan | Natija |
|---|---------|----------|--------|
| 1 | Kartaga ikkinchi raqamli element: `<p>{value - 1}</p>` | (a) bandi **QIZARADI** | ⛔ **QIZARDI** — `AssertionError: expected [ '47', '46' ] to have a length of 1 but got 2`. Bonus: «noma'lum metrika» testi ham ushladi (`[ '12', '11' ]`). Qolgan 8 test yashil qoldi, ya'ni sabotaj **aynan nishonga** tegdi. |
| 2 | Komponentga `const { principal } = useAuthStore()` + import qo'shildi va **haqiqatan ishlatildi** (`useHeadline(principal?.marketId ?? marketId)`) | (c) bandi **QIZARADI** | ⛔ **QIZARDI** — `AssertionError: expected [ …(2) ] to deeply equal []`, topilganlar: `headline-card.tsx: useAuthStore`, `headline-card.tsx: principal`. |

⚠ **Sabotaj 2 ning kutilmagan ikkinchi natijasi — va u qimmatli.** Sabotaj birinchi urinishda importsiz qo'yilgan edi (`ReferenceError`), ya'ni testlar «shunchaki yiqilgan» bo'lardi va bu **zaif dalil** edi. Import qo'shib **kompilyatsiya qilinadigan** holatga keltirilganda ham render testlari qizardi — sababi boshqa: `useAuthStore() faqat <AuthProvider> ichida ishlaydi`, va komponent testi `<AuthProvider>` ni ⛔ **umuman bermaydi**. Ya'ni himoya **ikki mustaqil qatlamda**: (c) bandi «yozib bo'lmaydi» deydi, test garnituri esa «ishlatib ham bo'lmaydi». Ikkinchisi **rejalashtirilmagan** edi va u (c) bandini almashtirmaydi — statik skan rol nomini **ishlatmasdan** import qilgan holatni ham ushlaydi.

Ikkala sabotaj `git checkout -- <fayl>` bilan qaytarildi (`git clean`/`reset` **ishlatilmadi**); qaytargandan keyin `git status` toza va 10/10 test yashil.

## Issues Encountered

- **Kesh kaliti metrikani o'z ichiga OLMAYDI va bu testni bir marta yolg'on-qizil qildi.** Kalit `["m", marketId, "headline"]` — metrikasiz (u ham bo'la olmaydi: qaysi metrika kelishini server hal qiladi). Natijada bitta test ichida ikki metrikani ketma-ket render qilganda ikkinchisi birinchisining **keshlangan** javobini darhol chizdi («47» kutilgan «1 200 000» o'rniga) va `aria-busy` umuman paydo bo'lmadi. Yechim: **har render o'z `QueryClient` ini oladi**; sabab test faylida docstring bilan yozildi. ⛔ Bu mahsulot nuqsoni **emas** — bir sessiyada bitta bozor uchun bitta metrika bo'ladi.
- **`findByText(formatlangan son)` ISHLAMAYDI.** `Intl.NumberFormat` ming ajratgichi sifatida **uzilmas bo'shliq** qo'yadi, Testing Library'ning standart normalizatori esa uni oddiy bo'shliqqa aylantiradi — solishtiruv mos kelmaydi. `variance-list.test.tsx` ham shu sababdan xom `textContent` bilan ishlaydi. Kutish signali `aria-busy` ning yo'qolishiga o'zgartirildi; sanoq bo'yicha kutish **rad etildi** — u (a) bandini tavtologiyaga aylantirib, sabotajni toza nosozlik o'rniga **taymaut** bilan qizartirardi.
- **`import.meta.url` vite transformidan keyin `file:` sxemasida emas** — `fileURLToPath` yiqildi. Skan katalogi `process.cwd()` dan quriladi va topilmasa ⛔ **`throw`** qiladi (`skip` ham, bo'sh massiv ham emas: ikkalasi darvozani jimgina o'chirardi).
- **Izoh o'z darvozasini qizartirishi mumkin edi.** Task 1 qabul mezoni `headline-queries.ts` da taqiqlangan validator nomini `grep` bilan **sanaydi**, izohim esa uni tushuntirish uchun **literal** yozgan edi. Nom izohdan olib tashlandi va sabab o'sha joyda qayd etildi — bu `collect-surface.test.mjs` docstringida «2 va 3-fazada 15+ marta yuz bergan» deb yozilgan sinf.

## User Setup Required

None — yangi tashqi xizmat ham, yangi npm paketi ham qo'shilmadi (T-07-SC).
⚠ Worktree'da `frontend/node_modules` yo'q edi (gitignore'da) — `npm install` bir marta bajarildi, `package.json`/`package-lock.json` **tegilmadi**.

## Verification Evidence

| Darvoza | Buyruq | Natija |
|---------|--------|--------|
| Reja Task 1 | `npm --prefix frontend run typecheck` | toza |
| Reja Task 1 | `grep -c "strictObject" headline-queries.ts` / taqiqlangan validator | **4** / ⛔ **0** |
| Reja Task 2 | `npm --prefix frontend run i18n:check` | «drift yo'q» + **1114 kalit × 3 til** parity to'liq |
| Reja Task 3 | `npm --prefix frontend run test:component -- headline` | **10 passed** (6 band + 4 qo'shimcha), exit 0 |
| Darvoza konvensiyasi | `grep -c "G-3 "` / `grep -c "not.toContain"` | ⛔ **0** / ⛔ **0** (`G-33 (07-UI-SPEC)` — 7 marta) |
| Butun frontend | `npm --prefix frontend test` | **182** node + **748** vitest passed (10 tasi yangi) |
| Tip/lint | `npm --prefix frontend run typecheck && ... run lint` | ikkalasi toza |
| Build | `npm --prefix frontend run build` | ✓ compiled; **72 SSG sahifa** (uchala locale) |
| Sabotaj 1 | ikkinchi raqamli element | ⛔ (a) **qizardi** |
| Sabotaj 2 | `useAuthStore()` (kompilyatsiya qilinadigan) | ⛔ (c) **qizardi** |

⚠ **`npm run gate:fast` ning backend yarmi YUGURTIRILMADI va bu ochiq qayd etiladi.** `gate:fast = npm run test:fast && npm --prefix frontend test`; birinchi yarmi `docker compose --profile test run --rm tests pytest tests/unit` — ya'ni docker talab qiladi. Bu rejaning o'zgarishi ⛔ **butunlay `frontend/` ichida** (`git diff --stat` bilan o'lchandi: 9 fayl, birortasi ham `.py` emas), ya'ni `tests/unit` ga ta'sir qila oladigan yo'l **yo'q**. Ikkinchi yarmi (`npm --prefix frontend test`) **yashil**. Worktree'da izolyatsiyalanmagan docker ko'tarish yondosh agentlarning stekiga tegish xavfini tug'dirardi (07-03 SUMMARY'sida qayd etilgan `s3.json` katalog bo'lib yaralishi sinfi).

## Next Phase Readiness

- **07-15/07-16 uchun tayyor:** `HEADLINE_UNIT` reyestri va `headlineKey` fabrikasi joyida; yangi metrika qo'shish uchun (a) `api-types.ts` da reyestrga bitta qator, (b) uchala locale'ga bitta kalit, (c) G-33(d) dagi kutilgan to'plamga bitta a'zo kerak — uchalasi ham **darvoza bilan majburlanadi**.
- **`components/headline/` katalogi endi qo'riqlanadi:** unga qo'shiladigan HAR QANDAY yangi fayl avtomatik ravishda G-33(c) skaniga tushadi (hosila qamrov), ya'ni ro'yxatni yangilash **esdan chiqmaydi**.
- **`frontend/scripts/glossary.test.mjs` HALI YO'Q** (07-11 egaligida). Task 2 ning oxirgi qabul mezoni («agar u allaqachon mavjud bo'lsa») shu sababdan **07-11 ga qoldi**. Qo'shilgan matnlar taqiqlangan sinonimlardan **toza**: `yig'im`, `do'kon`, `лавк`, `магазин` — hech birida yo'q (`tushum`, `kvitansiya`, `navbat`, `выручка`, `квитанция`, `зона` ishlatilgan).
- **Ochiq savol (bloklovchi emas):** `headline.unknown` bugun **hech qachon ko'rinmaydi** — server faqat uch kalitdan birini qaytaradi. U to'rtinchi metrika qo'shilgan kunning **birinchi himoyasi** sifatida turibdi va shu holat testda o'lchanadi (`headline.brand_new_metric`), ya'ni «o'lik matn» emas.

## Self-Check: PASSED

- Fayllar mavjud: `headline-queries.ts`, `headline-card.tsx`, `headline-card.test.tsx`, `07-05-SUMMARY.md`
- Commit'lar mavjud: `5ffc2e5`, `48dcc71`, `eb47848`
- Ish daraxti toza; ikkala sabotaj ham qaytarilgan (`git status` bo'sh)
- STATE.md / ROADMAP.md ⛔ **TEGILMAGAN** (worktree rejimi — orkestrator markazlashgan holda yangilaydi)

---
*Phase: 07-nomuvofiqlik-bildirishnoma-va-botlar*
*Completed: 2026-08-12*
