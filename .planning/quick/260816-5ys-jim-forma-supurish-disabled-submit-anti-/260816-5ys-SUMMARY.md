---
quick_id: 260816-5ys
phase: quick
plan: 260816-5ys
subsystem: frontend
tags: [ux, a11y, forms, tdd, regression, gate]
requirements: [F-1, F-2, F-3, F-4, F-5, G-SUBMIT]
dependency_graph:
  requires:
    - "frontend/src/components/users/create-user-dialog.tsx (260815-86p — etalon naqsh)"
    - "frontend/src/components/ui/button.tsx (01-xx — standart type=\"button\", faqat native disabled CSS'i)"
    - "frontend/src/components/ui/field.tsx (01-xx — ${id}-error / ${id}-hint konvensiyasi)"
    - "frontend/scripts/bulk-action-surface.test.mjs (05-xx — stripComments + meta-test naqshi)"
  provides:
    - "G-SUBMIT darvozasi: submit tugmasida domen-shartli disabled TAQIQ (D-1) + submit yo'lidan qochish TAQIQI (D-2)"
    - "stall-dialog / stall-category-dialog / tariff-dialog / camera-rename-dialog — ko'rinadigan validatsiya"
    - "camera-rename-dialog endi useForm+zodResolver formasi (ilgari useState)"
    - "market-requisites-form: 0 -> 1 o'tishida xato ekrandan chiqadi"
    - "to'rt yangi regressiya test fayli (F-1…F-4)"
  affects:
    - "kelajakdagi HAR forma: submit tugmasi endi mexanik darvoza ostida"
tech_stack:
  added: []
  patterns:
    - "disabled={<yuborilyapti>} — submit tugmasining YAGONA ruxsat etilgan qulfi"
    - "JSX teg ajratish jingalak-qavs CHUQURLIGI bilan (`>` ifoda ichida ham uchraydi)"
    - "tokenizatsiyadan OLDIN satr literallarini olib tashlash (`\"edit\"` -> soxta token bermasin)"
    - "istisno reyestri: eskirgani ham, qoldig'i siljigani ham darvozani QIZARTIRADI"
    - "aria-describedby: xato izohni ALMASHTIRMAYDI, unga QO'SHILADI"
key_files:
  created:
    - frontend/src/components/stalls/stall-dialog.test.tsx
    - frontend/src/components/stalls/stall-category-dialog.test.tsx
    - frontend/src/components/tariffs/tariff-dialog.test.tsx
    - frontend/src/components/cameras/camera-rename-dialog.test.tsx
    - frontend/scripts/submit-gate.test.mjs
  modified:
    - frontend/src/components/stalls/stall-dialog.tsx
    - frontend/src/components/stalls/stall-category-dialog.tsx
    - frontend/src/components/tariffs/tariff-dialog.tsx
    - frontend/src/components/cameras/camera-rename-dialog.tsx
    - frontend/src/components/wizard/market-requisites-form.tsx
    - frontend/src/components/wizard/market-requisites-form.test.tsx
decisions:
  - "D-2 detektori MAJBURIY va bu O'LCHOV bilan asoslandi: type=\"submit\" ni olib tashlab onClick+aria-disabled ga qaytish D-1 ni JIMGINA yashil qoldirdi (sabotaj B)"
  - "aria-disabled darvozaga QO'SHILMADI — nvr-form/nvr-password-dialog/schedule-dialog uni ATAYIN ishlatadi va bosilganda SABABNI aytadi (role=\"status\" + fokus); qo'shilsa ongli naqsh yolg'on-qizil bo'lardi"
  - "stall-dialog ning `mode === \"edit\" && detail === undefined` sharti TEGILMADI — u yopilmagan tri-state masalasi (260816-5yz) va darvozada NOM BILAN, qoldig'i bilan hujjatlashtirilgan istisno"
  - "collect-session istisnosining SABABI rejadagidan boshqa: u yerda `<form>` umuman yo'q, `onSubmit` — `StallLookup` ga uzatilgan PROP (rejadagi «qidiruv formasi» taxmini o'lchovda tasdiqlanmadi)"
  - "Darvoza rejada yo'q TO'RTINCHI holatni ham yopadi: shartsiz `disabled` (JSX shorthand) — «hech qachon bosilmaydi» eng qattiq shakli va u aks holda jimgina o'tib ketardi"
  - "camera-rename-dialog: `defaultValues` + mavjud `key={camera.id}` montaji — urug'lanish semantikasi `useState` shakli bilan AYNAN bir xil qoldi, fon refetch'i terilayotgan matnni bosmaydi"
  - "Field komponentiga TEGILMADI: unga role=\"alert\" qo'shish ilovadagi HAR forma xatosini e'longa aylantirardi"
  - "Yangi tarjima kaliti QO'SHILMADI — `npm run i18n:gen` kerak bo'lmadi"
metrics:
  duration_min: 35
  tasks: 3
  files: 11
  commits: 3
  completed: 2026-08-16
---

# Quick 260816-5ys: «jim-disabled submit» anti-naqshini supurish Summary

Kod-review tasdiqlagan **«jim-disabled submit»** anti-naqshi kodbazadan
supurildi: submit tugmasi endi FAQAT yuborish jarayoni davomida yopiladi,
domen shartlari esa validatsiya xabari bo'lib EKRANGA chiqadi. Beshala sayt
tuzatildi, har biri RED-first regressiya testi bilan qulflandi va anti-naqsh
qaytmasligi ikki detektorli mexanik darvoza (`G-SUBMIT`) bilan ta'minlandi.

## Nima qilindi

| Talab | Nuqson | Yechim | Commit |
|-------|--------|--------|--------|
| **F-1** | Bo'sh rasta raqamida «Saqlash» bosilmasdi | `disabled` dan `code.trim() === ""` disjunkti olib tashlandi | `04a473b` |
| **F-2** | Toifa tanlanmaganda «Saqlash» bosilmasdi | `disabled={isSubmitting}` | `04a473b` |
| **F-3** | Bo'sh toifa ro'yxatida tugma yopiq, `noCategories` matniga ZID | `disabled={isSubmitting}` — endi `tariffs.categoryRequired` chiqadi | `04a473b` |
| **F-4** | Tugma `aria-disabled` bilan «yopiq», amalda BOSILARDI va jimgina no-op qilardi | `useState` -> `useForm`+`zodResolver`; `type="submit"` + `disabled={rename.isPending}` | `486fdb1` |
| **F-5** | 0 -> 1 o'tishida xato ekranda QOLARDI | `shouldValidate: isSubmitted` | `486fdb1` |
| **G-SUBMIT** | Anti-naqsh qaytishini hech nima ushlamasdi | Ikki detektorli darvoza + istisno reyestri + 5 meta-test | `0315196` |

---

## 1-MAJBURIY O'LCHOV — har sayt uchun tuzatishdan OLDINGI QIZIL test

Har uch taskda test AVVAL yozildi va tuzatishdan OLDIN yugurtirildi.

### Task 1 — 7 test qizil (`Tests 7 failed | 13 passed (20)`)

| Sayt | Test | RED xabari |
|------|------|-----------|
| F-1 | `⛔ errors.required EKRANDA ko'rinadi` | `AssertionError: expected null not to be null` (`#stall-form-code-error` tug'ilmadi) |
| F-1 | `⛔ xabar maydonga DASTURIY bog'lanadi` | bir xil |
| F-1 | `⛔ POST /stalls YUBORILMAYDI — qulf saqlanadi` | bir xil (xabar KUTILADI, keyin so'rov sanaladi) |
| F-2 | `⛔ errors.required EKRANDA ko'rinadi va maydonga bog'lanadi` | `AssertionError: expected null not to be null` |
| F-2 | `⛔ POST /stalls/{id}/category YUBORILMAYDI` | bir xil |
| F-3 | `⛔ «Saqlash» YOPILMAYDI va bosilganda sabab ko'rinadi` | `Error: expect(element).toBeEnabled()` |
| F-3 | `⛔ POST /tariffs YUBORILMAYDI — qulf saqlanadi` | `AssertionError: expected null not to be null` |

Nazorat testlari (T3 to'liq forma, T4 tahrir rejimidagi tri-state qulfi) RED
bosqichida ham YASHIL edi — bu KUTILGAN va ular tuzatish qamrovdan oshib
ketmaganini o'lchaydi.

Yakuniy holat: `Tests 20 passed (20)`.

### Task 2 — 5 test qizil (`Tests 5 failed | 7 passed (12)`)

| Sayt | Test | RED xabari |
|------|------|-----------|
| F-4 | `⛔ errors.required EKRANDA ko'rinadi` | `AssertionError: expected null not to be null` |
| F-4 | `⛔ PATCH /cameras/{id} YUBORILMAYDI` | bir xil |
| F-4 | `⛔ xabar maydonga DASTURIY bog'lanadi — izoh bilan BIRGA` | bir xil |
| F-4 | `⛔ type="submit" va bo'sh nomda aria-disabled bilan YOPILMAYDI` | `Error: expect(element).toHaveAttribute("type", "submit")` |
| F-5 | `⛔ birinchi kun qayta belgilanganda xato EKRANDAN CHIQADI` | `AssertionError: expected <p …(2)></p> to be null` |

⚠ F-5 ning RED xabari boshqa sinfdan va bu MUHIM: element **bor edi** — ya'ni
xabar ekranda QOLGAN. Qolgan to'rttasi «element umuman tug'ilmadi» sinfidan.

Nazorat testlari (T4 yaroqli nom, T5 NVR nomiga qaytarish) RED bosqichida ham
yashil edi: eski kod yaroqli nomni to'g'ri saqlardi — nuqson faqat RAD
ETILGAN yo'lda edi.

Yakuniy holat: `Tests 12 passed (12)`, mavjud 5 ta usta testi TEGILMAY yashil.

---

## 2-MAJBURIY O'LCHOV — G-SUBMIT eski holatda nechta saytni ushladi

**Metod:** darvoza yozilgandan keyin beshala mahsulot fayli `644de85`
(tuzatishdan oldingi commit) holatiga qaytarildi, darvoza yugurtirildi,
so'ng joriy holat tiklandi.

```
# tests 11   # pass 8   # fail 3
```

| Test | Natija | Ushlagani |
|------|--------|-----------|
| 7 — D-1 istisnolar muzlamaydi | **not ok** | `stall-dialog.tsx` qoldig'i `["detail","mode","trim","undefined"]`, kutilgan `["detail","mode","undefined"]` — ya'ni `code.trim()` disjunkti (**F-1**) |
| 8 — D-1 domen-shartli disabled yo'q | **not ok** | `stall-category-dialog.tsx -> ["categoryId"]` (**F-2**) va `tariff-dialog.tsx -> ["length"]` (**F-3**) |
| 11 — D-2 submit yo'lidan qochish | **not ok** | `camera-rename-dialog.tsx` — `onSubmit` bor, `type="submit"` yo'q (**F-4**) |

**Beshta saytdan TO'RTTASI ushlandi** (reja minimumi — uchta).

⚠ **BESHINCHISI (F-5) ATAYIN USHLANMAYDI va bu darvozaning kamchiligi EMAS.**
F-5 — submit YUZASINING emas, qayta validatsiya LAHZASINING nuqsoni
(`shouldValidate` sharti). Uni statik skan bilan o'lchab bo'lmaydi; uning
qo'riqchisi — `market-requisites-form.test.tsx` dagi T6. Darvoza qamrovi
e'lon qilganidan keng ko'rinmasligi uchun bu chegara shu yerda yozib
qo'yilgan.

---

## 3-MAJBURIY O'LCHOV — SABOTAJ

### Sabotaj A — etalonga domen sharti (reja talab qilgan o'lchov)

`create-user-dialog.tsx`: `disabled={isSubmitting}` ->
`disabled={isSubmitting || selectedRoles.length === 0}`.

```
# pass 10   # fail 1
not ok 8 - ⛔ G-SUBMIT D-1: submit tugmasida domen-shartli `disabled` YO'Q
      components/users/create-user-dialog.tsx -> ["length"]
```

**Sabotaj QIZARTIRDI.** Qaytarildi (`git checkout -- <fayl>`).

### Sabotaj B — D-1 dan QOCHISH (rejadan tashqari, qo'shimcha o'lchov)

Rejaning «D-1 yolg'iz qolganda undan qochish arzon» da'vosi TEKSHIRILDI:
`create-user-dialog.tsx` ning saqlash tugmasidan `type="submit"` olib
tashlanib, `onClick` + `aria-disabled={selectedRoles.length === 0}` ga
qaytarildi — ya'ni AYNAN F-4 ning shakli qayta yaratildi.

```
# pass 10   # fail 1
ok      8 - ⛔ G-SUBMIT D-1: submit tugmasida domen-shartli `disabled` YO'Q
not ok 11 - ⛔ G-SUBMIT D-2: `onSubmit` bor joyda submit tugmasi ham bor
      components/users/create-user-dialog.tsx
```

**Bu natija rejaning eng muhim tasdig'i:** D-1 **YASHIL QOLDI** (qochish
haqiqatan ishladi) va nuqsonni faqat **D-2 ushladi**. Ikkinchi detektor
«ehtiyot chorasi» emas — usiz darvoza bir bosishda chetlab o'tilardi.
Qaytarildi.

---

## Darvozaning ichki tuzilishi

**D-1 — submit tugmasida domen-shartli `disabled` TAQIQ.**
`src/**/*.tsx` (test fayllari QAMROVDAN TASHQARI) izohlardan tozalanadi, har
`<Button`/`<button` ochuvchi tegi **jingalak-qavs chuqurligi** bilan
ajratiladi (`>` ifoda ichida ham uchraydi — meta-test `disabled={count > 0}`
holatini alohida o'lchaydi), `type="submit"` bo'lsa `disabled={…}` ifodasi
satr literallaridan tozalanib tokenlanadi va har tokenning OXIRGI nuqtali
segmenti ruxsat lug'atiga (`isSubmitting`, `isPending`, `isLoading`, `busy`,
`saving`, `submitting`) solishtiriladi.

**D-2 — submit yo'lidan QOCHISH taqiqi.** `onSubmit={` ishlatadigan har
mahsulot fayli kamida bitta `type="submit"` ga ega bo'lishi shart.

**Quyi chegaralar (§S-10):** `MIN_SUBMIT_BUTTONS = 10` (o'lchov: 12),
`MIN_ONSUBMIT_FILES = 12` (o'lchov: 14). Busiz bo'sh skan «taqiq topilmadi»
deb JIMGINA rost bo'lardi.

**Meta-testlar (5):** ijobiy nazorat (5 holat, jumladan `>` ifoda ichida va
shartsiz `disabled`), salbiy nazorat (etalon, `busy`, `rename.isPending`,
submit bo'lmagan tugma, `aria-disabled`), **izoh nazorati** (busiz darvoza
BUGUN qizarardi — Task 1/2 qo'shgan izohlar anti-naqshni matn sifatida
o'z ichiga oladi), izoh filtri faylni yutmasligi, satr literali soxta token
bermasligi.

### Istisnolar — uchta, va ular MUZLAMAYDI

| # | Detektor | Fayl | Qoldiq (O'LCHANGAN) | Yopilish tetigi |
|---|----------|------|---------------------|-----------------|
| 1 | D-1 | `components/stalls/stall-dialog.tsx` | `["detail","mode","undefined"]` | 260816-5yz (tri-state) |
| 2 | D-2 | `components/collect/collect-session.tsx` | — | qidiruv haqiqiy `<form>` ga aylansa |
| 3 | D-2 | `components/stalls/stall-filters.tsx` | — | filtr paneliga yozuv amali qo'shilsa |

Uch meta-qoida darvozaning O'ZIDA bajariladi: (a) qoldiq **AYNAN** mos
kelmasa — kengaysa ham, torayadi ham — qizil; (b) **eskirgan** istisno (fayl
tuzatilgan, hit yo'q) — qizil, ya'ni ro'yxat o'z-o'zini tozalashga majbur;
(c) yangi yozuv qo'shish diff'da ko'rinadi.

Qoldiq **rejadan ko'chirilmadi** — detektor chiqargan qiymat yozildi. Reja
`["detail","mode","undefined"]` ni taxmin qilgan edi va o'lchov uni AYNAN
tasdiqladi.

---

## Rejadan chetlanishlar

### 1. [O'lchov] `collect-session` istisnosining SABABI rejadagidan boshqa

Reja uni «qidiruv formasi, saqlash amali yo'q» deb ta'riflagan edi. O'lchov
boshqa narsa ko'rsatdi: `collect-session.tsx` da `<form>` **umuman yo'q** —
`onSubmit` u yerda `StallLookup` ga uzatilgan **PROP**, va `stall-lookup.tsx`
ham forma emas. Istisno yozuvi o'lchangan sabab bilan yozildi. Amaliy farqi
bor: yopilish tetigi ham boshqacha («saqlash tugmasi qo'shilsa» emas,
«qidiruv haqiqiy formaga aylansa»).

### 2. [Rule 2 — yetishmayotgan qamrov] Shartsiz `disabled` ham ushlanadi

Reja faqat `disabled={<ifoda>}` shaklini nomlagan edi. JSX shorthand
(`<Button type="submit" disabled>`) — «hech qachon bosilmaydi», ya'ni
anti-naqshning ENG qattiq shakli — bu qamrovdan tashqarida qolardi va
jimgina o'tib ketardi. Detektor uni `["<shartsiz-disabled>"]` qoldig'i bilan
ushlaydi; meta-testda ijobiy nazorat holati bor. Bugun kodbazada bunday
tugma yo'q.

### 3. [Rule 1 — tip xatosi] `CategoryItem` to'liq emas edi

`tariff-dialog.test.tsx` dagi namunaviy toifa `{id, name}` bilan qurilgan
edi; `tsc` uni rad etdi (`stall_count`, `current_tariff_soum` yetishmaydi).
Tuzatildi — kontrakt testda ham to'liq.

### 4. [Kengaytma] Ikkinchi sabotaj o'lchovi qo'shildi

Reja bitta sabotaj talab qilgan edi (A). Rejaning D-2 ni asoslovchi da'vosi
(«D-1 yolg'iz qolganda undan qochish arzon») tekshirilmagan taxmin bo'lib
qolmasligi uchun sabotaj B qo'shildi va u da'voni **tasdiqladi**.

### 5. [Chegara — tegilmadi] `aria-disabled` li uchta submit tugmasi

`nvr-form.tsx`, `nvr-password-dialog.tsx`, `schedule-dialog.tsx` submit
tugmalari `aria-disabled={<domen sharti>}` ishlatadi. **Bu F-4 sinfi EMAS va
tegilmadi** — o'qib tekshirildi: ular ATAYIN shunday (02-UI-SPEC §6.6 qoida
2) va bosilganda **sababni AYTADI** (fokus muammoli maydonga + `role="status"`
e'loni). F-4 dagi nuqson `aria-disabled` ning O'ZIDA emas, uning yonida
sababning YO'QLIGIDA edi. Shu sababli darvoza `aria-disabled` ni
taqiqlamaydi — taqiqlaganda ongli naqsh yolg'on-qizil bo'lardi. Bu qaror
darvoza faylining docstringida yozilgan.

---

## Yakuniy tekshiruv

```
npm run lint       -> toza
npm run typecheck  -> toza
npm test           -> node --test: tests 246, pass 246, fail 0
                      vitest:      Test Files 71 passed, Tests 906 passed
```

Reja nomlagan regressiya to'plamlari (`market-requisites-form.test.tsx` —
5 eski test, `create-user-dialog.test.tsx`, `nvr-form.test.tsx`,
`stall-map.test.tsx`) 71 fayllik yashil yugurishning ichida.

## Known Stubs

Yo'q — bu vazifada mavjud kod tuzatildi, yangi to'qilgan yuza qo'shilmadi.

## Threat Flags

Yo'q. Yangi tarmoq yuzasi, marshrut yoki sxema o'zgarishi qo'shilmadi.
Reja `threat_model` ining `T-5ys-02` (takroriy bosish) bandi bajarildi:
`camera-rename-dialog` endi **native** `disabled={rename.isPending}` bilan
qulflanadi — `aria-disabled` dan farqli o'laroq u bosilishni HAQIQATAN
to'xtatadi. `T-5ys-SC` shartiga rioya qilindi: **hech qanday paket
o'rnatilmadi**.

## Self-Check: PASSED

Yaratilgan fayllar mavjud:
`stall-dialog.test.tsx`, `stall-category-dialog.test.tsx`,
`tariff-dialog.test.tsx`, `camera-rename-dialog.test.tsx`,
`scripts/submit-gate.test.mjs` — beshalasi ham diskda.

Commitlar mavjud: `04a473b`, `486fdb1`, `0315196`.
Ishchi daraxt toza; sabotaj va o'lchov uchun vaqtincha qaytarilgan beshala
fayl asl (tuzatilgan) holatiga qaytarilgani `git status` bilan tasdiqlandi.

## Ochiq bandlar

- **260816-5yz** — `stall-dialog` ning tahrir rejimidagi tri-state qulfi.
  Bugun u darvozada NOM BILAN, aynan qoldig'i bilan hujjatlashtirilgan
  istisno; o'sha vazifa yopilganda istisno yozuvi O'CHIRILISHI shart, aks
  holda darvoza «eskirgan istisno» deb qizaradi.
