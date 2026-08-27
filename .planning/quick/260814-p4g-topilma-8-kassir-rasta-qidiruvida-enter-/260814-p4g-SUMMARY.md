---
quick_id: 260814-p4g
phase: quick
plan: 260814-p4g
subsystem: kassir-oqimi-tashxis
tags: [test-report, topilma-8, collect, keyboard, focus, jsdom-limit, sabotage-measurement]

requires:
  - phase: 06-billing-va-kassir
    provides: "stall-lookup.tsx onKeyDown ishlovchisi, collect-session.tsx inputRef/draft holati, collect-session.test.tsx (G-20) va payment-bar.test.tsx (G-21) naqshlari"
provides:
  - "stall-lookup.tsx uchun BIRINCHI test fayli — 8 holat (T1..T8)"
  - "Fokus-yo'naltirilgan `Enter` regressiya darvozasi: hodisa `document.activeElement` ga yuboriladi, element havolasiga EMAS"
  - "BIRINCHI `Enter` lahzasidagi fokus invarianti (ilgari faqat to'lovdan KEYIN o'lchanardi)"
  - "TEST-REPORT Topilma №8 uchun yozma tashxis: jsdom qatlamida mahsulot kodi SOG'LOM"
  - "Brauzer uchun uch qatorli CDP qayta o'lchov retsepti (artefakt gipotezasini HAL QILADIGAN o'lchov)"
  - "Naqsh: sabotaj IMZOSI (nechta va QAYSI test qizardi) darvozaning FARQLASH qobiliyatini o'lchaydi — sanoq emas"
affects: [06-billing-va-kassir, 08-hisobotlar-mustahkamlash-va-ishga-tushirish, TEST-REPORT]

tech-stack:
  added: []
  patterns:
    - "Klaviatura da'vosi FOKUS orqali o'lchanadi (`document.activeElement`) — element havolasiga qaratilgan `fireEvent` haqiqiy klaviatura marshrutini QAYTA HOSIL QILMAYDI"
    - "`defaultPrevented` — ishlovchi yugurganining MOCK'DAN MUSTAQIL dalili; josus soxtalashtirilsa ham DOM ning o'z yozuvi qoladi"
    - "Sinov hodisasi HAQIQIY klaviaturaning `key`+`code` juftligini olib yuradi — `code: \"\"` sabotaj imzolarini bir-biriga yopishtirib qo'yadi"
    - "jsdom cheklovi SUMMARY da OCHIQ nomlanadi va o'rniga brauzer retsepti yoziladi — yashil darvoza «brauzerda ham ishlaydi» degani EMAS"

key-files:
  created:
    - "frontend/src/components/collect/stall-lookup.test.tsx"
  modified: []

key-decisions:
  - "Mahsulot kodi (`stall-lookup.tsx`) UMUMAN TEGILMADI — Task 1 exit 0 bergani uchun rejaning shartli tuzatish bandi (a) ISHGA TUSHMADI; `git diff` bo'sh bo'lishi bilan qulflandi"
  - "`@testing-library/user-event` ATAYIN qo'shilmadi: u ham trusted hodisa yaratmaydi, uning yagona qimmatli xossasi (hodisani `activeElement` ga yo'naltirish) ikki qator `fireEvent` bilan yangi bog'liqliksiz olindi"
  - "Test hodisalari haqiqiy klaviaturaning `key`+`code` juftligini oladi — bu S-B ni S-A dan AJRATGAN yagona o'zgarish"
  - "jsdom darvozasi Topilma №8 ni YOPMAYDI, TORAYTIRADI: u ishlovchi + fokus marshrutini qopladi, brauzerning kirish qatlami o'lchanmagan qoldi"

patterns-established:
  - "Sabotaj o'lchovida SANOQ emas, IMZO qaraladi: ikki boshqa nuqson bir xil to'plamni qizartirsa — darvoza farqlay olmaydi va tuzatish TEST HOLATIDA izlanadi"
  - "Tashxis rejasida IKKALA natija ham to'g'ri: exit 0 -> «kod sog'lom + regressiya darvozasi qo'yildi», exit != 0 -> «nuqson lokallashtirildi»"

requirements-completed: [TOPILMA-8]

duration: ~35 min
completed: 2026-08-14
---

# Quick Task 260814-p4g: Topilma №8 — rasta qidiruvida `Enter` Summary

`/uz/collect` da `Enter` nuqsoni **jsdom qatlamida QAYTA HOSIL BO'LMADI** — `stall-lookup.tsx` uchun qurilgan birinchi test fayli (8 holat, fokus-yo'naltirilgan) 8/8 yashil qaytdi va mahsulot kodi tegilmadi; uch sabotaj darvozaning tirikligini isbotladi, jsdom cheklovi va brauzer uchun CDP retsepti ochiq yozildi.

## ⛔ TASHXIS XULOSASI

**«KOD SOG'LOM — KUZATUV AVTOMATLASH ARTEFAKTI (jsdom qamrovi doirasida), REGRESSIYA DARVOZASI QO'YILDI.»**

Ya'ni: `frontend/src/components/collect/stall-lookup.tsx` **O'ZGARTIRILMADI**. Rejaning
Task 2 (a) bandi — «shartli minimal tuzatish» — **ishga tushmadi**, chunki uning sharti
(Task 1 exit != 0) bajarilmadi. Bu holat rejada oldindan nomlangan va **ikkala natija ham
to'g'ri** deb belgilangan edi.

⚠ **LEKIN BU «TOPILMA №8 YOLG'ON» DEGANI EMAS.** Xulosaning qamrovi aniq:
o'lchangan ikki qatlam (`onKeyDown` ishlovchisining mantig'i + maydonning fokusda
bo'lishi) **sog'lom**. O'lchanmagan qatlam — brauzerning kirish qatlami — quyida
«Ochiq qolgan band» da nomlangan va uni hal qiladigan retsept berilgan.

### Nima o'lchandi (T1..T8)

| # | Da'vo | Natija |
|---|-------|--------|
| T1 | mount'dan keyin fokus AYNAN qidiruv `<input>` ida (`autoFocus` qo'nadi) | ✅ |
| T2 | terishdan keyin ham fokus O'SHA maydonda (hech nima o'g'irlamaydi) | ✅ |
| T3 | ⛔ ASOSIY: `Enter` **fokuslangan elementga** yuborilsa `onSubmit` AYNAN 1 marta, AYNAN `"A-01"` | ✅ |
| T4 | NAZORAT: xuddi shu yo'l bilan `{ key: "a" }` -> `onSubmit` CHAQIRILMAYDI | ✅ |
| T5 | `"  A-01  "` -> `onSubmit` `"A-01"` oladi (`trim`) | ✅ |
| T6 | `"   "` -> `onSubmit` CHAQIRILMAYDI (bo'sh qo'riqchi) | ✅ |
| T7 | hodisaning `defaultPrevented === true` — mock'dan MUSTAQIL dalil | ✅ |
| T8 | `{ key: "Enter", code: "NumpadEnter" }` ham ishlaydi (raqamli klaviatura) | ✅ |

### Nega bu test mavjud to'plamning TAKRORI EMAS

`collect-session.test.tsx:194-198` (`actOn`) allaqachon `fireEvent.keyDown(el, { key: "Enter" })`
qiladi va u yashil — bu brauzerda **ISHLAGAN** «JS dispatch» yo'lining aynan o'zi. Yangi fayl
hodisani **`document.activeElement` ga** yuboradi (element havolasiga emas), chunki haqiqiy
klaviatura hodisasi elementga **nom bilan emas, FOKUS bilan** yetadi. Shu bilan birga
**BIRINCHI `Enter` lahzasidagi fokus** ham o'lchandi — mavjud to'plamda fokus faqat
**to'lovdan KEYIN** (`collect-session.test.tsx:337-351`, §8.5) tekshirilardi.

## Tasks Completed

| Task | Nomi | Commit |
|------|------|--------|
| 1 | Fokus-yo'naltirilgan reproduksiya testi — tashxisni O'LCHASH | `8ee8e2e` |
| 2 | Sabotaj bilan darvozani o'lchash, shartli tuzatish (ISHGA TUSHMADI), jurnal | `e3e0cf4` |

## ⛔ SABOTAJ JURNALI — DARVOZANING O'ZI O'LCHANDI

Asl holat: **8/8 yashil**. Har sabotajdan keyin fayl asliga qaytarildi va tiklanish
`git diff -- frontend/src/components/collect/stall-lookup.tsx` ning **bo'sh** bo'lishi +
yashil yugurish bilan tasdiqlandi.

| Sabotaj | O'zgartirilgan qator | Qizargan testlar | Ushlaydigan gipoteza |
|---------|----------------------|------------------|----------------------|
| **S-A** | `stall-lookup.tsx:116` `onKeyDown` -> `onKeyUp` | T3, T5, T7, T8 (**4 qizil**) | «ishlovchi noto'g'ri HODISANI tinglaydi» |
| **S-B** | `:117` `event.key !== "Enter"` -> `event.code !== "Enter"` | T8 (**1 qizil**) | «ishlovchi noto'g'ri MAYDONNI o'qiydi» (NumpadEnter) |
| **S-C** | `:109` `<Input>` dan `autoFocus` olib tashlandi | T1..T8 (**8 qizil**) | «fokus maydonda emas» — kuzatuvning eng jiddiy mahsulot-tomon gipotezasi |

### ⛔⛔ S-B DARVOZANI FOSH QILDI (05-15 sabog'ining takrori)

**Birinchi o'lchovda S-B ham AYNAN S-A bilan bir xil to'rtta testni qizartirdi**
(T3/T5/T7/T8). Ya'ni sabotaj sistemaga yetib bordi va testlar qizardi — **lekin darvoza
ikki BOSHQA nuqsonni FARQLAY OLMASDI**: ikkalasining imzosi ustma-ust tushardi.

Sabab da'voda emas, **TEST HOLATIDA** edi: T3/T5/T7 hodisani `code: ""` bilan yuborardi
(chunki `key` dan boshqa hech nima berilmagandi), haqiqiy klaviatura esa `Enter` ni
**har doim `key: "Enter"` + `code: "Enter"` juftligi** bilan beradi. Holat haqiqiy
klaviaturaga moslangach (`code`: `"Enter"` · T4 da `"KeyA"` · T8 da `"NumpadEnter"`),
S-B **aynan T8 ni** qizartirdi va imzolar ajraldi.

⚠ **Tuzatish da'voni kuchsizlantirmadi:** S-A moslashtirilgan holat bilan **qayta**
yugurtirildi va o'sha to'rtta testni qizartirgani tasdiqlandi.

**Naqsh (yangi):** sabotaj o'lchovida **sanoq emas, IMZO** qaraladi. «Nimadir qizardi»
yetarli emas — ikki boshqa nuqson bir xil to'plamni qizartirsa, darvoza tashxis quroli
sifatida ishlamaydi.

## ⚠⚠ jsdom CHEKLOVI — OCHIQ QOLADI

Bu darvoza **ISHLOVCHI + FOKUS** marshrutini qopladi, **brauzerning KIRISH QATLAMINI emas.**
jsdom da yuborilgan hodisa ham **trusted EMAS** (`isTrusted === false`), demak
**O'LCHANMAGAN** qoldi:

- Chromium ning kalit-hodisa **sintezi**;
- CDP `Input.dispatchKeyEvent` ning **parametrlari** (`windowsVirtualKeyCode`,
  `nativeVirtualKeyCode`, `text`);
- **IME/kompozitsiya** va OS klaviatura tartibi;
- brauzerdagi **haqiqiy fokus** holati (avtomatlash sessiyasida oyna fokusda bo'lmasligi mumkin).

⛔ Ya'ni **yashil darvoza «brauzerda ham ishlaydi» degani emas.** Bu reja artefakt
gipotezasini jsdom da hal qila **olmaydi** va buni yashirmaydi.

## ⛔ BRAUZER UCHUN QAYTA O'LCHOV RETSEPTI (uch qator)

Keyingi brauzer sessiyasida Topilma №8 ni **HAL QILADIGAN** uch o'lchov — shu tartibda:

1. **`Enter` dan OLDIN fokusni o'qing:** `document.activeElement.id` (va
   `document.hasFocus()`) qiymatini yozib oling. Agar u qidiruv maydonining `id` si
   **emas** bo'lsa — tashxis tugadi: nuqson mahsulotda emas, avtomatlash sessiyasi
   hodisani boshqa elementga yuborgan.
2. **CDP ni to'liq parametr bilan chaqiring:** `Input.dispatchKeyEvent` ga
   `type: "keyDown"`, `key: "Enter"`, `code: "Enter"`, `windowsVirtualKeyCode: 13`,
   `nativeVirtualKeyCode: 13` va `text: "\r"` bering. ⚠ `text` va virtual key kodlarisiz
   yuborilgan hodisa brauzerda **`key` maydonini bo'sh** qoldirishi mumkin — bu aynan
   kuzatuvning shakli.
3. **Kelgan hodisani `document` da tinglab yozib oling:**
   `document.addEventListener("keydown", (e) => console.log(e.key, e.code, e.isTrusted, e.target.id), true)`
   — `key` qiymati `"Enter"` bo'lmasa yoki `target` qidiruv maydoni bo'lmasa, sabab
   **kirish qatlamida**; ikkalasi ham to'g'ri bo'lib turib `onSubmit` chaqirilmasa —
   **o'shanda** mahsulot nuqsoni va u yuqoridagi darvoza bilan lokallashtiriladi.

## Deviations from Plan

### [Rule 1 - Bug] Sabotaj imzolarining ustma-ust tushishi (darvoza nuqsoni)

- **Found during:** Task 2 (b), S-B o'lchovi
- **Issue:** S-B (`key` -> `code`) S-A bilan **aynan bir xil** to'rtta testni qizartirdi —
  darvoza «noto'g'ri hodisa» va «noto'g'ri maydon» nuqsonlarini farqlay olmasdi. Sabab:
  T3/T5/T7 hodisalari `code: ""` bilan ketardi, ya'ni **haqiqiy klaviaturani ifodalamasdi**.
- **Fix:** Test holati haqiqiy klaviatura juftligiga moslandi — T3/T5/T6/T7 `code: "Enter"`,
  T4 `code: "KeyA"`, T8 `code: "NumpadEnter"`. Rejaning o'zi bu sinf tuzatishga ochiq ruxsat
  bergan («tuzatish TESTNING DA'VOSIDA emas, TEST HOLATIDA izlanadi»).
- **Verification:** S-B qayta yugurtirildi -> **faqat T8** qizardi; S-A ham qayta
  yugurtirildi -> o'sha **to'rtta** test qizardi (da'vo kuchsizlanmagani tasdiqlandi).
- **Files modified:** `frontend/src/components/collect/stall-lookup.test.tsx`
- **Commit:** `e3e0cf4`

### Rejaning bajarilmagan (shartli) bandi

- **Task 2 (a) — shartli minimal tuzatish:** **ISHGA TUSHMADI.** Sharti (Task 1 exit != 0)
  bajarilmadi. Shuning uchun `frontend/src/components/collect/stall-lookup.tsx`
  frontmatterdagi `files_modified` ro'yxatidan **tushib qoldi** va `key-files.modified`
  bo'sh. Reja buni oldindan talab qilgan edi: «buni SUMMARY da ochiq ayt».

## Verification Results

Rejaning `<verification>` bo'limi — oltala band:

| # | Tekshiruv | Natija |
|---|-----------|--------|
| 1 | `npx vitest run src/components/collect/stall-lookup.test.tsx` | ✅ **8/8 yashil** |
| 2 | `npm run test:component` (butun to'plam, regressiya yo'q) | ✅ **63 fayl / 857 test yashil** |
| 3 | `npm run lint` + `npm run typecheck` | ✅ ikkalasi ham toza |
| 4 | `git diff --stat` — sabotaj qoldig'i yo'q | ✅ faqat test fayli; `stall-lookup.tsx` diff **BO'SH** |
| 5 | `grep -c "document.activeElement" ...test.tsx` >= 4 | ✅ **10** |
| 6 | `git diff frontend/package.json` bo'sh | ✅ `package.json` + lock **tegilmagan** |

**Kassir oqimidagi bosishlar soni O'ZGARMADI (<=3):** `collect-session.test.tsx` dagi
`steps` sanog'i testlari (`AYNAN 3`, ko'p moslikda `4`, ikkinchi takror `3`) **tegilmagan**
va 857 talik to'plam ichida yashil qaytdi. Mahsulot kodi umuman o'zgarmagani uchun bu
struktural jihatdan ham kafolatlangan.

## Success Criteria

- ✅ Topilma №8 uchun **yozma xulosa** bor va u belgilangan ikki shakldan birida:
  «kod sog'lom — kuzatuv avtomatlash artefakti, regressiya darvozasi qo'yildi».
- ✅ `stall-lookup.tsx` uchun **birinchi test fayli** mavjud va u mavjud to'plamdagi
  da'voni takrorlamaydi (fokus o'lchami yangi).
- ✅ **Uch sabotajning har biri** kamida bitta testni qizartirdi; natijalar test faylining
  sarlavhasida so'zma-so'z yozilgan.
- ✅ Kassir oqimidagi bosishlar soni o'zgarmadi (<=3).
- ✅ jsdom cheklovi va brauzer uchun qayta o'lchov retsepti SUMMARY da.

## Known Stubs

Yo'q. Bu reja mahsulot yuzasini kengaytirmadi — faqat o'lchov qo'shdi.

## Ochiq qolgan band (bloklamaydi, LEKIN nomlangan)

**Topilma №8 ning brauzer yarmi HAL QILINMAGAN.** jsdom darvozasi ikki gipotezani
(«noto'g'ri hodisa», «noto'g'ri maydon», «fokus yo'q») yopdi, uchinchisini —
**brauzerning kirish qatlami** — o'lchamadi. Egasi: keyingi brauzer/E2E sessiyasi.
Tetigi: yuqoridagi uch qatorli CDP retsepti. ⚠ Playwright E2E **8-fazaga** rejalashtirilgan
(`vitest.config.ts` izohi, OQ-2) — retsept o'sha yerda tabiiy uy topadi.

## Self-Check: PASSED

- `frontend/src/components/collect/stall-lookup.test.tsx` — **FOUND**
- `.planning/quick/260814-p4g-.../260814-p4g-SUMMARY.md` — **FOUND**
- Commit `8ee8e2e` (Task 1) — **FOUND**
- Commit `e3e0cf4` (Task 2) — **FOUND**
- `frontend/src/components/collect/stall-lookup.tsx` vs HEAD — **diff BO'SH** (mahsulot
  kodi tegilmagani mexanik tasdiqlandi, sabotaj qoldig'i yo'q)
- Docs artefaktlari (SUMMARY) — **commit QILINMAGAN** (orkestrator zimmasida)

## Threat Flags

Yo'q — yangi tarmoq yuzasi, auth yo'li, fayl kirishi yoki sxema o'zgarishi kiritilmadi.
`T-p4g-02` (sabotaj tsikli mahsulot faylini vaqtincha o'zgartiradi) **mitigatsiya qilindi**:
har sabotajdan keyin asliga qaytarish bajarildi va yakuniy `git diff` mahsulot faylida
**bo'sh**.
