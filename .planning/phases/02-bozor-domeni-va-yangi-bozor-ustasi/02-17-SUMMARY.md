---
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
plan: 17
subsystem: ops
tags: [karmana, real-data, import-cli, phase-criteria, validation, sabotage, pii, gate]

# Dependency graph
requires:
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "02-16 — usta UI va import paneli; 02-12 — import endpointlari (`/imports/template`, `/imports/stalls`, `/imports/vendors`), 422 `errors[]` + `error_counts`, D-14/D-15 semantikasi va o'nta qator-xato kodi; 02-11 — `POST /markets`, `setup-status`, `activate`, `PLATFORM_ADMIN_ROUTES`; 02-09 — `POST /tariffs` ning ikki tarmoqli qoidasi (qoralama bozorda `operating_since` istisnosi); 02-08 — `GET /stalls`, `/stalls/map`, `/stalls/{id}`; 02-07 — SC#2/SC#3/SC#4 ning DB darajasidagi isbotlari; 02-06 — `market_is_open()`, ikki bozorli domen seed'i"
  - phase: 01-poydevor-va-tenant-xavfsizligi
    provides: "`audit_log` append-only qo'riqchilari, `fn_audit_row()`, RBAC matritsasi, `two_markets` seed'i, `market_scope`/`market_today` fixture'lari, `npm run gate` zanjiri"
provides:
  - "`ops/data/karmana/README.md` — real ma'lumotni kiritishning sakkiz bo'limli yo'riqnomasi (tartib, ustunlar, chegaralar, o'nta xato kodi, tekshiruv ro'yxati, `operating_since` ogohlantirishi)"
  - "`ops/data/karmana/.gitignore` — shaxsiy ma'lumot git tarixiga tushmasligining mexanik darvozasi (T-02-128)"
  - "`scripts/karmana-import.mjs` — brauzersiz, tashqi npm bog'liqligisiz import CLI'si (`template` / `upload`)"
  - "`package.json` — `karmana:template` va `karmana:upload`"
  - "`tests/integration/test_phase2_criteria.py` — fazaning BESHTA mezonini ROADMAP matni bilan bog'laydigan yagona fayl (5 test)"
  - "`02-VALIDATION.md` — to'ldirilgan per-task xarita, SHU FAZADA o'lchangan kechikish va halol imzo (`nyquist_compliant: false` + ochiq bandlar)"
affects: [03-kamera, 06-hisob-kitob, 08-hisobotlar]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Skript TIRIK stek ustida ishga tushirilmaguncha 'yozildi' — bu 'ishlaydi' EMAS: ikkala defekt ham faqat ijro bilan ko'rindi"
    - "Windows'da `process.exit(1)` quvurga yozilayotgan stdio bilan libuv assertion'i beradi va kod **127** bo'ladi — `process.exitCode = 1` yagona to'g'ri shakl"
    - "Server bergan matnda prefiks BOR-YO'QLIGI tekshiriladi, ko'r-ko'rona qo'shilmaydi (`rowLine`) — aks holda `2-qator: 2-qator: ...`"
    - "Mezon darajasidagi test qismlar ORASIDAGI uzilishni o'lchaydi: har bosqichdan keyin darvoza, faqat oxirida emas"
    - "Sabotaj testning O'ZIDAGI defektni ham fosh qiladi: to'g'ri qizarish yetarli emas, XABAR ham harakatga aylanishi kerak"
    - "Maxfiy qiymat argv'dan OLINMAYDI — `ps` va shell tarixi (T-02-129)"

key-files:
  created:
    - ops/data/karmana/README.md
    - ops/data/karmana/.gitignore
    - scripts/karmana-import.mjs
    - tests/integration/test_phase2_criteria.py
  modified:
    - package.json
    - .planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-VALIDATION.md

key-decisions:
  - "`nyquist_compliant: false` ATAYIN — real ma'lumot kelmagan, ya'ni faza maqsad jumlasining ikkinchi yarmi isbotlanmagan"
  - "Skript tirik stek ustida uchidan-uchiga ishlatildi — reja buni talab qilmaydi, lekin usiz u tekshirilmagan stub bo'lib qolardi"
  - "Namuna ma'lumot repoga QO'YILMADI — API generatsiya qilgan shablonning O'ZI namuna (yagona haqiqat manbai)"
  - "SC#5 katakning AYNAN to'rt maydonini tekshiradi (to'plam TENGLIGI), 'bor' emas"
  - "SC#2 toifa o'zgarishidan `old -> new` TALAB QILINMAYDI — u `insert` (D-04 voris modeli)"
  - "To'lqin kechikishi byudjeti BUZILGANI yashirilmadi, tuzatish esa 3-fazaga o'tkazildi (fixture doirasi izolyatsiyaga tegadi)"

patterns-established:
  - "Pattern: CLI xatosi `process.exit()` bilan emas, `process.exitCode` bilan — stdio bo'shatilishi kafolatlanadi"
  - "Pattern: ko'p bosqichli oqim testida darvoza HAR BOSQICHDAN KEYIN — aks holda birinchi rad etish keyingi bosqichda texnik xato bo'lib niqoblanadi"
  - "Pattern: shaxsiy ma'lumot katalogi o'z `.gitignore` i bilan tug'iladi va u `git check-ignore` bilan qabul mezoniga ulanadi"

requirements-completed: []

# Metrics
duration: 195min
completed: 2026-08-01
---

# Phase 2 Plan 17: Karmananing real ma'lumoti, faza mezonlari testi va darvoza Summary

**Fazaning beshta mezoni endi ROADMAP matniga bog'langan beshta testda yashaydi va olti sabotajning har biri AYNAN kutilgan testni qizartirdi — jumladan `PLATFORM_ADMIN` dan `STALL_MANAGE` ni olib tashlash, u testning O'ZIDAGI defektni fosh qildi (test rostdan qizardi, lekin xabar `ValueError: zip() argument 2 is longer than argument 1` edi). Import skripti TIRIK stek ustida uchidan-uchiga ishlatildi va aynan shu ijro ikkita haqiqiy defektni topdi: qator raqami ikki marta chiqardi va Windows'da exit kodi 1 emas, 127 bo'lardi. ⚠ Fazaning maqsad jumlasining ikkinchi yarmi — «Karmananing real ma'lumoti tizimda yashaydi» — BAJARILMADI: ma'muriyatdan birorta hujjat topshirilmagan va bu `02-VALIDATION.md` da `nyquist_compliant: false` bilan ochiq qoldirildi.**

## Performance

- **Duration:** ~195 min
- **Tasks:** 3/3
- **Fayllar:** 6 (4 yaratildi, 2 o'zgartirildi), **+1625 / −77**
- **Testlar:** backend 885 → **890** (+5); frontend 94 (o'zgarmadi)
- **Migratsiya:** `alembic_version` **0010** — o'zgarmadi (`git diff --name-only -- migrations/ frontend/ services/` **BO'SH**)
- **Yangi paket:** **0** (na npm, na pip)

## Task Commits

1. **Task 1: Real ma'lumot yo'riqnomasi va takrorlanadigan import skripti** — `e4ce21f` (feat)
2. **Task 1 tuzatishi: holat qiymatlari manba bilan moslashtirildi** — `7aa6772` (fix)
3. **Task 2: Beshta faza mezonining uchidan-uchiga tekshiruvi** — `af717d6` (test)
4. **Task 1 tuzatishi: skriptning ikki defekti (tirik stek o'lchovi)** — `c56ae71` (fix)
5. **Task 3: Validatsiya xaritasi va o'lchangan kechikish** — `30ff2c6` (docs)

## ⚠ Real Karmana ma'lumoti: BAJARILMADI

**Bu bo'lim rejaning eng muhim qabul mezoniga to'g'ridan-to'g'ri javob beradi va u salbiy.**

Reja SUMMARY'dan "real ma'lumot solishtiruvi (rasta soni, zona taqsimoti,
sotuvchi soni, farqlar) jadval bilan" yozilishini talab qiladi. **Bunday
jadval yo'q, chunki solishtiriladigan ma'lumot yo'q.** Rejaning `user_setup`
bandidagi beshta hujjatning **birortasi ham** topshirilmagan:

| Kerak bo'lgan hujjat | Kimdan | Holat |
|---|---|---|
| Rastalar reestri (raqam, zona, toifa, holat) | Hisobchi / yig'uvchilar boshlig'i | ❌ yo'q |
| Toifalar bo'yicha amaldagi patta narxlari + amal qilish sanasi | Direktor (yozma) | ❌ yo'q |
| Sotuvchilar ro'yxati (F.I.Sh., telefon, rasta) | Yig'uvchilar | ❌ yo'q |
| Haftalik ish rejimi + bayram kunlari | Direktor | ❌ yo'q |
| Bozor rekvizitlari (nom, manzil, STIR, bank) | Hisobchi | ❌ yo'q |

Shuning uchun quyidagi da'volarning **hech biri** qilinmaydi: rasta soni,
zona bo'yicha taqsimot, sotuvchi soni, ma'muriyat reestri bilan farqlar,
boshlang'ich tariflar qaysi sanaga yozilgani, bozor qachon
faollashtirilgani. **Raqam o'ylab topilmadi.**

### Buning o'rniga: yo'l TAKRORLANADIGAN qilib o'lchandi

Reja "brauzersiz takrorlanadigan yo'l" ni talab qiladi. Skript **haqiqiy
stek ustida** ishga tushirildi (`docker compose up db cache core-api` +
`alembic upgrade head` + qo'lda yozilgan bitta platforma admini), namuna
sifatida esa **API generatsiya qilgan shablonning O'ZI** ishlatildi — repoda
namuna fayl saqlanmaydi (`.gitignore`), chunki repodagi nusxa zona/toifa
ro'yxati o'zgarganda jimgina eskirardi.

| O'lchov | Buyruq | Natija |
|---|---|---|
| Shablon olish | `karmana-import.mjs template --kind=stalls` | ✅ **6209 bayt**, `local/stalls.xlsx` |
| Shablon olish (sotuvchi) | `--kind=vendors` | ✅ **5562 bayt** |
| O'zgarmagan shablonni import | `upload --kind=stalls` | ✅ `inserted: 1, skipped: 0` |
| **Qayta** import (D-15) | ayni fayl, ikkinchi marta | ✅ `inserted: 0, skipped: 1` + tushuntirish |
| Sotuvchi importi | `upload --kind=vendors` | ✅ `inserted: 1`; `GET /vendors` da `stall_codes: ["1"]` (biriktirish ham yozildi) |
| **Noto'g'ri fayl** (sotuvchi shabloni rasta endpointiga) | `upload --kind=stalls --file=vendors.xlsx` | ✅ **422**, guruhlangan sanoq (`zone_not_found: 1`, `category_not_found: 1`, `invalid_status: 1`), uch qator, **exit 1** |
| Muhit o'zgaruvchisisiz | har qanday buyruq | ✅ exit 1, to'rtala nom ro'yxati bilan |
| `--help` | — | ✅ exit 0, ikkala buyruq ham |

`README.md` §7 dagi **tekshiruv ro'yxatining o'zi ham** tirik tizimga qarshi
tasdiqlandi — ya'ni u to'qib chiqarilgan emas:

| README da va'da qilingan | Haqiqiy javob |
|---|---|
| `GET /zones` → zona bo'yicha rasta soni | ✅ `{"name":"Go'sht qatori","stall_count":1}` |
| `GET /categories` → toifa soni + amaldagi narx | ✅ `{"stall_count":1,"current_tariff_soum":null}` (`null` = tarif kiritilmagan) |
| `GET /vendors` → sotuvchi soni | ✅ `{"stall_count":1,"stall_codes":["1"]}` |
| `GET /stalls?status=maintenance` | ✅ 200 (holat filtri haqiqiy qiymatni oladi) |
| `GET /stalls/map` → `has_vendor` | ✅ `{"code":"1","status":"active","has_vendor":true}` |

**Real fayl kelganda bajariladigan aniq yo'l:** `ops/data/karmana/README.md`
§2 (tartib) + «Skript bilan ishlash». O'zgarishi kerak bo'lgan yagona narsa —
`SBOZOR_MARKET_ID` va fayl yo'li.

⚠ **Sinov muhiti butunlay tozalandi:** `docker compose down`, `.env`
o'chirildi, `ops/data/karmana/local/` o'chirildi. `git status` toza va
birorta `.xlsx` repoga tushmadi.

## Accomplishments

### Olti sabotaj va ularning aniq natijalari

Har sabotaj MAHSULOT kodiga qo'yildi (testga emas) va faqat
`test_phase2_criteria.py` ishga tushirildi. Nazorat — qolgan to'rt test.

| # | Sabotaj (mahsulot kodida) | Yiqilgan test | Nazorat |
|---|---|---|---|
| 1 | `_MAP_ROWS`: `ORDER BY z.name, s.code_sort` → `s.code` | AYNAN 1: `test_sc5_...` | qolgan 4 ✅ |
| 2 | `_MAP_ROWS`: `(a.stall_id IS NOT NULL)` → `true` | AYNAN 1: `test_sc5_...` | qolgan 4 ✅ |
| 3 | `is_valid_from_allowed`: `and window.is_draft` olib tashlandi | AYNAN 1: `test_sc3_...` | qolgan 4 ✅ |
| 4 | `market_is_open()`: istisno qavati (`COALESCE` ning 1-bandi) olib tashlandi | AYNAN 1: `test_sc4_...` | qolgan 4 ✅ |
| 5 | `fn_audit_row()`: `changed_keys` diffi (`WHERE n.v IS DISTINCT FROM ...`) olib tashlandi | AYNAN 1: `test_sc2_...` | qolgan 4 ✅ |
| 6 | `rbac.py`: `PLATFORM_ADMIN` dan `STALL_MANAGE` olib tashlandi (Pitfall 6 qaytarildi) | AYNAN 1: `test_sc1_...` | qolgan 4 ✅ |

Har oltitasidan keyin `git checkout` bilan tiklandi va `git status` toza
bo'lgani tekshirildi.

**Oltinchisi eng qimmatlisi va u testning O'ZIDAGI defektni topdi.** Test
rostdan qizardi, lekin xabar quyidagicha edi:

```
E   ValueError: zip() argument 2 is longer than argument 1
```

Sabab: `POST /zones` 403 oldi, `zone_ids` bo'sh qoldi va keyingi bosqich
403 tekshiruviga YETIB BORMASDAN texnik xato bilan qulab tushdi — ya'ni
Pitfall 6 ning aniq alomati "usta ishlamayapti" degan foydasiz xabar ostida
niqoblandi. `_assert_no_refusals()` har bosqichdan keyin chaqiriladigan
qilindi va sabotaj QAYTA o'lchandi:

```
E   AssertionError: usta oqimida 403 olingan qadamlar:
    ['2-qadam: POST /zones (Mezon markaziy)', '2-qadam: POST /zones (Mezon sharqiy)']
```

Bu **to'g'ri qizarish yetarli emas** degan darsning aniq ko'rinishi: darvoza
qizardi-yu, u qaysi qadamni tuzatish kerakligini AYTMASDI.

### Skriptning ikki defekti — faqat IJRO bilan ko'rindi

**1. Qator raqami IKKI MARTA chiqardi.** Reja qator formatini
`{row}-qator: {message}` deb belgilaydi. Lekin `ImportIssue.message`
docstringi uni "foydalanuvchi uchun, uz-Latn, **qator raqami BILAN**" deb
ta'riflaydi — ya'ni prefiks ALLAQACHON ichida. Natija:

```
2-qator: 2-qator: ''+998901234567' zonasi topilmadi
```

`rowLine()` endi prefiks borligini tekshiradi va yo'q bo'lsa qo'shadi
(server bir kun prefiksni olib tashlasa qator raqami YO'QOLMASLIGI kerak —
u xatoni topishning yagona yo'li).

**2. Exit kodi 1 emas, 127 edi.** Windows'da quvurga yozilayotgan stdio
bo'shatilmagan paytda `process.exit(1)` libuv assertion'i bilan qulaydi:

```
Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), file src\win\async.c, line 76
```

Ya'ni xato hisobotining oxirgi qatorlari yo'qolardi va CI/`&&` zanjiri
noto'g'ri kodni ko'rardi — **rejaning "exit kodi 1" qabul mezoni
bajarilmasdi**. `CliError` + `process.exitCode = 1` bilan yopildi; qayta
o'lchandi: **exit 1** va hisobotning oxirgi qatori joyida.

### Mezon testlari NIMANI qo'shadi

Beshta test mavjud fayllarni takrorlamaydi — ular qismlar **orasidagi**
uzilishni o'lchaydi:

- **SC#1** — butun zanjir FAQAT HTTP orqali (birorta xom `INSERT`,
  `sbozor_owner` ulanishi yoki migratsiya qadami yo'q; `sync_owner_conn`
  faqat TEARDOWN uchun olinadi). Bu "kod yozilmaydi" da'vosining mashinaviy
  shakli.
- **SC#2** — uch xil o'zgarishning audit SHAKLI har xil ekani birinchi
  marta bir joyda yozildi: holat/kod → `update` (`old -> new`), toifa →
  **`insert`** (D-04 voris modeli, `old` BO'LMAYDI), biriktirish davri →
  `update` (`period`). Ustiga jurnalning O'ZI append-only ekani
  tekshiriladi — usiz "har o'zgarish auditda ko'rinadi" da'vosini izni
  o'chirish bilan chetlab o'tish yo'li ochiq qolardi.
- **SC#3** — yozuv MAHSULOT yo'lidan (`POST /tariffs`) va **faol** bozorda.
  Avval boshlang'ich narx yo'lining YOPIQ ekani o'lchanadi (422
  `valid_from_must_be_future`), keyin qonuniy yo'ldan yoziladi. 02-07 ayni
  da'voni xom SQL bilan isbotlaydi — ikkalasi har xil tahdid modelini
  qoplaydi.
- **SC#4** — javob istisnodan OLDIN ham o'lchanadi. Faqat "keyin"
  o'lchansa test kun haftalik jadval bo'yicha allaqachon yopiq bo'lgan
  holatda ham yashil bo'lardi.
- **SC#5** — xarita va reestr **to'plamining tengligi** (birorta rasta
  yo'qolmaydi), tartib da'vosining BO'SH EMASLIGI (kamida bitta zonada
  raqamli va matn tartibi farq qilishi shart) va **katak↔karta mosligi**
  (har katakning `has_vendor` i kartadagi `vendor_name` bilan mos).

## Files Created/Modified

**Yaratildi (4)**

| Fayl | Qator | Mazmuni |
|---|---|---|
| `tests/integration/test_phase2_criteria.py` | 783 | 5 test; har biri ROADMAP mezonini so'zma-so'z olib yuradi |
| `scripts/karmana-import.mjs` | 400 | `template`/`upload`; tashqi bog'liqlik **0**; maxfiy qiymat faqat muhitdan |
| `ops/data/karmana/README.md` | 280 | sakkiz bo'lim + skript qo'llanmasi |
| `ops/data/karmana/.gitignore` | 25 | `*.xlsx`/`*.xls`/`*.csv`/`local/` + qaytarib bo'lmaslik sababi |

**O'zgartirildi (2)**

- `package.json` — `karmana:template`, `karmana:upload` (+2 qator)
- `02-VALIDATION.md` — 51 satr holati, o'lchangan kechikish, Wave 0, Manual-Only natijalari, imzo (+135/−77)

## Decisions Made

- **`nyquist_compliant: false` ATAYIN qo'yildi.** Kod darvozalari to'liq
  yashil va beshta mezon avtomatik testga bog'langan, lekin fazaning maqsad
  jumlasi IKKI qismdan iborat va ikkinchisi ("Karmananing real
  rasta/tarif/sotuvchi ma'lumoti tizimda yashaydi") isbotlanmagan. `true`
  qo'yish aynan shu farqni yashirardi.
- **Skript tirik stek ustida ishga tushirildi.** Reja buni talab qilmaydi
  (Task 1 ning `<automated>` bandi faqat `--help` va `.gitignore` ni
  tekshiradi). Lekin `--help` yashil bo'lgan skript "ishlaydi" degani emas:
  ikkala defekt ham `--help` dan keyin ham yashil bo'lib turardi. Sinov
  muhiti keyin butunlay tozalandi.
- **Namuna ma'lumot repoga qo'yilmadi.** Reja `stalls.example.xlsx` ni
  ATAYIN taqiqlaydi (`<interfaces>`) va o'lchov buni tasdiqladi: shablon
  bozorning O'Z zona/toifa ro'yxatidan quriladi, ya'ni repodagi nusxa
  boshqa bozorda darhol `zone_not_found` berardi.
- **SC#5 katakning maydonlarini TO'PLAM TENGLIGI bilan tekshiradi.** D-20
  bo'yicha rang serverda hisoblanmaydi va D-19 bo'yicha koordinata
  saqlanmaydi — ya'ni ORTIQCHA maydon ham shartnoma buzilishi. "Bor"
  tekshiruvi (`test_stall_registry.py` dagi shakl) buni ko'rmasdi.
- **SC#2 toifa o'zgarishidan `old -> new` TALAB QILINMAYDI.** Reja "uchala
  o'zgarish uchun ham `old→new`" deydi, lekin toifa D-04 bo'yicha YANGI
  qator (`insert`) — eski davr tahrirlanmaydi. `old` ni talab qilish mezonni
  noto'g'ri o'qish bo'lardi va testni doim qizil qilardi. Sabab test
  docstringida yozildi.
- **To'lqin kechikishi byudjeti buzilgani yashirilmadi.** 225 s / maqsad
  ≤180 s. Sabab strukturaviy (har integratsiya testi ikki bozorlik seed'ni
  qayta yozadi) va tuzatish fixture doirasiga tegadi — ya'ni bu fazaning
  eng qimmat kafolatiga (testlar orasidagi izolyatsiya). 3-fazaga
  o'tkazildi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] README rasta holati qiymatlarini NOTO'G'RI yozgan edi**

- **Found during:** Task 2 ga tayyorgarlik (manba o'qilganda)
- **Issue:** README ning "Nima noto'g'ri bo'lishi mumkin" bo'limi mumkin
  qiymatlarni `active / repair / closed` deb yozgan edi. Manba
  (`sbozor_core.enums.StallStatus`) esa `active / maintenance / closed`
  beradi. Yo'riqnomaga ergashgan admin `repair` yozib, butun faylni
  `invalid_status` bilan qaytarib olardi — D-14 tufayli **bitta katak butun
  importni** bloklaydi.
- **Fix:** Qiymatlar to'g'rilandi; ustiga ikki fakt qo'shildi — ular DB
  kontenti va shablon TILIDAN qat'i nazar o'zgarmaydi (tarjima qilib yozish
  ham `invalid_status` beradi), hamda `maintenance`/`closed` rastalarga
  6-fazada hisob YOZILMAYDI (ya'ni bu ustun pul oqimiga bevosita ta'sir
  qiladi). Tekshiruv ro'yxatidagi `?status=repair` misoli ham tuzatildi.
- **Verification:** `grep -n "repair"` ikkala faylda ham **0**; keyinchalik
  tirik stekda `GET /stalls?status=maintenance` **200** qaytardi
- **Committed in:** `7aa6772`

**2. [Rule 1 - Bug] Skript qator raqamini IKKI MARTA chiqarardi**

- **Found during:** Task 3 (skriptni tirik stek ustida ishga tushirish)
- **Issue:** Reja formatni `{row}-qator: {message}` deb belgilaydi, lekin
  `ImportIssue.message` prefiksni ALLAQACHON o'z ichiga oladi (docstringi
  buni literal aytadi). Natija: `2-qator: 2-qator: '...' zonasi topilmadi`.
  Rejaga literal ergashish aynan shu buzilishni beradi.
- **Fix:** `rowLine()` — prefiks bor-yo'qligini tekshiradi. Tekshiruv
  ATAYIN bir tomonlama emas: server bir kun prefiksni olib tashlasa qator
  raqami baribir chiqadi.
- **Files modified:** `scripts/karmana-import.mjs`
- **Verification:** 422 yo'li qayta ishga tushirildi — uch qatorning
  uchalasi ham bir marta prefiks bilan chiqdi
- **Committed in:** `c56ae71`

**3. [Rule 1 - Bug] Xato yo'lida exit kodi 1 emas, 127 edi**

- **Found during:** Task 3 (ayni ijro)
- **Issue:** `process.exit(1)` Windows'da quvurga yozilayotgan stdio
  bo'shatilmagan paytda libuv assertion'i bilan quladi
  (`!(handle->flags & UV_HANDLE_CLOSING)`) va protsess **127** kodi bilan
  tugadi. Rejaning qabul mezoni "exit kodi `1`" ni aniq talab qiladi va u
  bajarilmasdi; hisobotning oxirgi qatorlari ham yo'qolardi. Bu skriptning
  E'LON QILINGAN maqsadini (CI'da `&&` zanjirida ishlatish) buzardi.
- **Fix:** `CliError` sinfi + yuqori qatlamda `process.exitCode = 1`.
  `fail()` endi `throw` qiladi, ya'ni "chaqiruvdan keyin kod davom etmaydi"
  fakti statik ravishda ham ko'rinadi.
- **Files modified:** `scripts/karmana-import.mjs`
- **Verification:** qayta o'lchandi — **exit 1**, assertion yo'q, hisobot
  to'liq
- **Committed in:** `c56ae71`

**4. [Rule 1 - Bug] SC#1 testi to'g'ri qizarardi, lekin XABARI foydasiz edi**

- **Found during:** 6-sabotaj (Pitfall 6 ni qaytarish)
- **Issue:** 403 tekshiruvi faqat oqim OXIRIDA turardi. `PLATFORM_ADMIN`
  dan `STALL_MANAGE` olib tashlanganda `POST /zones` 403 oldi, `zone_ids`
  bo'sh qoldi va test `zip(..., strict=True)` da `ValueError` bilan quladi
  — ya'ni testning O'Z docstringi va'da qilgan diagnostika ("qaysi qadam
  to'xtadi") bermadi. Bu aynan sabotaj o'lchamoqchi bo'lgan holat edi.
- **Fix:** `_assert_no_refusals()` har bosqichdan keyin chaqiriladi. Sabab
  va o'lchov funksiya docstringida yozildi.
- **Files modified:** `tests/integration/test_phase2_criteria.py`
- **Verification:** sabotaj QAYTA o'lchandi — xabar endi
  `['2-qadam: POST /zones (...)']` ni nomlaydi
- **Committed in:** `af717d6`

**5. [Rule 3 - Blocking] Sinov stekini ko'tarish uchun uch qadam kerak bo'ldi**

- **Found during:** Task 3
- **Issue:** Skriptni tirik stek ustida sinash uchun: (a) `core-api` imaji
  02-12 dagi uchta yangi paketsiz qurilgan edi va
  `ModuleNotFoundError: defusedxml` bilan qulardi; (b) mavjud `pgdata`
  hajmi eski parollar bilan tug'ilgan edi (`init` skriptlari faqat birinchi
  ishga tushishda bajariladi); (c) `btree_gist` o'sha eski hajmda yo'q edi.
- **Fix:** `docker compose build core-api`; rol parollari superuser bilan
  `ALTER ROLE` qilindi; `CREATE EXTENSION IF NOT EXISTS btree_gist`
  (migratsiya xato xabarining O'ZI aynan shu buyruqni beradi — ya'ni
  darvoza to'g'ri ishladi). **Repoga birorta o'zgarish kirmadi.**
- **Verification:** `alembic upgrade head` 0010 gacha o'tdi; keyin
  `docker compose down` va `.env` o'chirildi
- **Committed in:** — (kod o'zgarishi yo'q)

**6. [Rule 2 - Missing Critical] `02-VALIDATION.md` ning `Status` ustuni yolg'on tasalli berardi**

- **Found during:** Task 3
- **Issue:** Reja 51 satrning holatini yashil qilishni buyuradi va
  `02-17-03` satrining turi — `gate + human-check`. Uni oddiygina
  `✅ green` qilib qo'yish "faza tekshiruvi tugadi" degan ma'no berardi,
  holbuki human-check ning **to'rtala bandi ham ochiq**. Aynan shu — "gate
  looked green while proving nothing" sinfidagi xato.
- **Fix:** Jadval ostiga izoh qo'shildi: `Status` FAQAT `Automated Command`
  ni bildiradi va `02-17-03` ning human-check yarmi Manual-Only jadvalida
  ALOHIDA yuritiladi. Manual-Only jadvaliga beshinchi ustun (`Natija`)
  qo'shildi va to'rtala bandda ham `❌ BAJARILMADI` + sabab + o'rniga nima
  o'lchangani yozildi.
- **Files modified:** `.planning/.../02-VALIDATION.md`
- **Committed in:** `30ff2c6`

---

**Total deviations:** 6 auto-fixed (4 bug, 1 missing-critical, 1 blocking).
Rule 4 (arxitektura) holati bo'lmadi.
**Impact on plan:** Sxemaga, frontendga va servis kodiga UMUMAN tegilmadi
(`git diff --name-only -- migrations/ frontend/ services/` **BO'SH**;
`alembic_version` `0010`). #1, #2 va #3 rejaning O'Z matni bilan manba
orasidagi ziddiyatlar (holat qiymatlari, qator formati, exit kodi); #4
sabotaj fosh qilgan test defekti; #6 esa reja ko'rmagan yolg'on-yashil
yo'lini yopadi.

## Empirik o'lchovlar

| O'lchov | Natija |
|---|---|
| `node scripts/karmana-import.mjs --help` | ✅ exit **0**, ikkala buyruq ham |
| `git check-ignore ops/data/karmana/probe.xlsx` | ✅ **exit 0** (`.gitignore:19:*.xlsx`) |
| `git check-ignore ops/data/karmana/README.md` | ✅ exit 1 (yo'riqnoma ignore QILINMAYDI) |
| `grep 'require(\|from "' karmana-import.mjs` | ✅ FAQAT `node:fs`, `node:path` |
| `grep "process.argv"` da parol/telefon | ✅ **YO'Q** (faqat `argv.slice(2)` da buyruq va bayroq) |
| README bo'limlari | ✅ **8** + skript qo'llanmasi |
| `pytest tests/integration/test_phase2_criteria.py` | ✅ **5 passed** (aynan beshta) |
| `grep -c "async def test_"` | ✅ **5** |
| To'liq backend to'plami | ✅ **890 passed** (885 + 5) |
| `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 (132 fayl, 130 manba) |
| `npm run gate` | ✅ to'liq yashil (**403 s**) |
| `npm --prefix frontend run i18n:check` | ✅ **418 kalit × 3 til** |
| Frontend testlari | ✅ 54 node + 40 vitest (o'zgarmadi) |
| **Kechikish — task darajasi** (`pytest tests/unit -x -q`) | ✅ **11 s** (maqsad ≤30 s) |
| **Kechikish — tenancy** (`npm run test:tenancy`) | **99 s** |
| **Kechikish — to'liq backend** (`npm run test`) | ❌ **225 s** (maqsad ≤180 s) |
| **Kechikish — frontend** (`npm --prefix frontend test`) | ✅ **12 s** |
| Skript: shablon | ✅ 6209 bayt (rasta) / 5562 bayt (sotuvchi) |
| Skript: o'zgarmagan shablon importi | ✅ `inserted: 1` |
| Skript: qayta import (D-15) | ✅ `inserted: 0, skipped: 1` |
| Skript: noto'g'ri fayl | ✅ **422** + guruhlangan sanoq + **exit 1** |
| Skript: muhit o'zgaruvchisisiz | ✅ exit 1, to'rtala nom bilan |
| Sabotaj o'lchovlari (6 ta) | ✅ har birida AYNAN bitta kutilgan test qizardi |
| Sabotajdan keyin tiklash | ✅ `git status` toza |
| Commit'larda fayl o'chirilishi | ✅ **0** |
| `git diff --name-only -- migrations/ frontend/ services/` | ✅ **BO'SH** |
| Sinov muhiti tozalandi | ✅ `docker compose down`, `.env` va `local/` o'chirildi |

## Issues Encountered

- **`docker compose run` ning oxirgi qatori quvurga yetib bormaydi.**
  `pytest -q` ning `=== N passed ===` xulosasi `| tail` bilan
  ko'rinmasdi (konteyner tugashi bilan oxirgi buferni yo'qotadi).
  `-v --no-header` bilan xulosa chiqadi — barcha sanoqlar shu yo'l bilan
  o'qildi.
- **`addopts = "-q"` `-v` ni NEYTRALLASHTIRADI.** `-q` va `-v` birga
  berilganda verbosity 0 bo'ladi, ya'ni `PASSED` satrlari chiqmaydi.
  Sanoq faqat xulosa satridan olinadi.
- **Mavjud `sbozor_pgdata` hajmi eski parollar bilan tug'ilgan edi.**
  `docker-entrypoint-initdb.d` faqat birinchi ishga tushishda bajariladi,
  ya'ni `.env` dagi yangi parollar rollarga YETIB BORMAYDI. Xato xabari
  (`password authentication failed for user "sbozor_owner"`) aniq, lekin
  sababi emas — bu dev muhitida takrorlanadigan qopqon.
- **`btree_gist` migratsiyasining xato xabari o'z tuzatish buyrug'ini
  beradi** va u ISHLADI — 02-01 dagi `require_extension()` yordamchisi
  aynan shu holat uchun yozilgan (Pitfall 1) va u dala sharoitida
  tekshirildi.
- **`market_delete_draft()` faol bozorga tegmaydi**, shuning uchun SC#1
  ning teardown'i avval `is_active` ni tushiradi. Bu `test_wizard_flow.py`
  da allaqachon hujjatlashtirilgan va shu yerda qayta ishlatildi.

## Known Stubs

Yo'q. Birorta test `skip`/`xfail` bilan yozilmagan, skriptda `TODO` yoki
qattiq yozilgan bo'sh qiymat yo'q, README da "keyinroq to'ldiriladi" bo'limi
qoldirilmagan.

**⚠ Stub EMAS, lekin OCHIQ ish (rejaning o'zi kutgan holat):**

| Ochiq band | Kim yopadi | Bugungi holati |
|---|---|---|
| Karmananing REAL rasta/tarif/sotuvchi ma'lumoti | Ma'muriyat + keyingi to'lqin | Yo'l qurilgan, hujjatlangan va TIRIK stekda o'lchangan; kiritiladigan ma'lumotning O'ZI yo'q |
| Ustaga navigatsiya havolasi (`app-shell.tsx`) | belgilanmagan | 02-16 dan meros; **shu rejaning fayl chegarasidan tashqarida** — atayin kengaytirilmadi |
| Bozorsiz platforma admini ustaga kira olmaydi (`(app)/layout.tsx`) | belgilanmagan | 02-16 dan meros; **fayl chegarasidan tashqarida**. ⚠ Bu ikkisi birgalikda "birinchi bozorni yaratish" yo'lini UI'da BUTUNLAY yopadi |
| To'lqin kechikishi 225 s (byudjet ≤180 s) | 3-faza | Sabab aniqlangan (function-scope seed); tuzatish izolyatsiya kafolatiga tegadi |
| `market_requisites_form` / `activation-panel` komponent testlari | belgilanmagan | 02-16 "02-17 yopadi" degan edi; bu reja `frontend/` ga TEGMAYDI (`files_modified` da yo'q) |

## Threat Flags

Rejaning `<threat_model>` idan TASHQARIDA yangi xavfsizlik yuzasi paydo
bo'lmadi: yangi endpoint, yangi auth yo'li yoki sxema o'zgarishi YO'Q.
Skript faqat mavjud uchta endpointni iste'mol qiladi.

| Threat ID | Holat |
|-----------|-------|
| T-02-128 | **mitigate** — `ops/data/karmana/.gitignore` (`*.xlsx`, `*.xls`, `*.csv`, `local/`); `git check-ignore` bilan **o'lchandi**; sinovda yaratilgan ikkala fayl ham `git status` da UMUMAN ko'rinmadi va keyin o'chirildi |
| T-02-129 | **mitigate** — telefon va parol FAQAT `process.env` dan; `grep "process.argv"` uchala uchrashuvi ham buyruq/bayroqqa tegishli. Chala sozlangan muhitda skript LOGIN dan oldin to'xtaydi |
| T-02-130 | **mitigate** — README §8 to'liq ogohlantirish (aynan shu sana, `± 1 kun` ham rad etiladi, noto'g'ri qo'yilsa 6-faza tarifsiz kun topadi, tuzatish = bozorni qayta yaratish); §2 da tartib va uning sababi |
| T-02-131 | **mitigate** — README §3 pozitsiya qoidasini va "tartib almashsa 422, jimgina YOZILMAYDI" faktini aytadi. **O'lchandi:** sotuvchi shabloni rasta endpointiga yuborilganda 422 keldi va birorta qator yozilmadi |
| T-02-132 | **mitigate (qisman)** — tekshiruv ro'yxati README §7 da va uning har bir endpointi tirik tizimda tasdiqlandi. ⚠ Solishtiruvning O'ZI bajarilmadi (real reestr yo'q) va bu SUMMARY hamda `02-VALIDATION.md` da ochiq qoldirildi |
| T-02-133 | accept (aniqlangan) — 5000 qator chegarasi; README importni ish vaqtidan tashqarida bajarishni tavsiya qiladi |
| T-02-133a | **mitigate** — README §2 tarif qadamini faollashtirishdan OLDIN qo'yadi va ikkinchi qatlam (02-11 `activate` darvozasi, `tariff_missing_for_category`) tilga olinadi. ⚠ README bu darvozaga TAYANMASLIKNI ham aytadi: u faqat "tarif umuman yo'q" ni ushlaydi, "noto'g'ri sanaga yozilgan tarif" ni emas |

## Verification Results

| # | Buyruq | Natija |
|---|--------|--------|
| 1 | `npm run gate` | ✅ to'liq yashil, **403 s** |
| 2 | `pytest tests/integration/test_phase2_criteria.py` | ✅ **5 passed** |
| 3 | `node scripts/karmana-import.mjs --help` | ✅ exit 0 |
| 4 | `git check-ignore ops/data/karmana/probe.xlsx` | ✅ exit 0 |
| 5 | `02-VALIDATION.md` frontmatter'i haqiqiy holatga mos | ✅ `nyquist_compliant: false` + `open_items` |
| 6 | `ruff check . && ruff format --check . && mypy .` | ✅ exit 0 |
| 7 | To'liq backend to'plami | ✅ **890 passed** (225 s) |
| 8 | Skriptning tirik stek ustidagi oqimi | ✅ 8 stsenariy (yuqoridagi jadval) |
| 9 | Sabotaj o'lchovlari | ✅ 6/6, har birida AYNAN kutilgan test |

## User Setup Required

⚠ **Bu fazani YAKUNLASH uchun tashqi kirish SHART.** Kod tomoni tayyor;
quyidagilar bajarilmaguncha faza mezonlarining ikkinchi yarmi isbotlanmaydi:

1. **Bozor ma'muriyatidan beshta hujjat** — `ops/data/karmana/README.md` §1
   dagi jadval (rasta reestri, tariflar + amal qilish sanasi, sotuvchilar,
   ish rejimi, rekvizitlar).
2. **`operating_since` ni direktordan YOZMA tasdiqlash** — noto'g'ri
   qo'yilsa tuzatishning yagona yo'li bozorni qayta yaratish (README §8).
3. **Import tartibi:** tariflar **faollashtirishdan OLDIN** (README §2).
4. **Foydalanuvchanlik kuzatuvi** — undan OLDIN 02-16 ning ikki qarzi
   yopilishi kerak (usta havolasi + bozorsiz admin yo'li), aks holda
   kuzatuv birinchi daqiqada to'xtaydi.
5. **Rekvizitlar formasini buyurtmachiga ko'rsatish** (A1/A2 taxminlari).

## Next Phase Readiness

- **Beshta mezon endi REGRESSIYA darvozasi.** 3–8 fazalarning har qanday
  o'zgarishi `test_phase2_criteria.py` ni buzsa, u ROADMAP jumlasini
  buzganini AYTADI — chunki har test docstringi o'sha jumlani olib yuradi.
- **6-faza uchun ikki kontrakt so'rov shakli test faylida LITERAL yozilgan**
  va ular endi qulflangan: `PRICE_AT` ("D sanadagi amaldagi tarif",
  `valid_from <= :d ORDER BY valid_from DESC LIMIT 1` — qator topilmasa
  `None`, `0` EMAS) va `IS_OPEN` (`market_is_open(market_id, date)` —
  kunlik job'ning `WHERE` bandi).
- **Import yo'li ISHLAYDI va o'lchangan** — 3-fazadagi kamera qadamlari
  qo'shilganda `README.md` §2 tartibiga bitta qator qo'shiladi, skript esa
  o'zgarmaydi.
- **⚠ 3-faza uchun ogohlantirish:** to'lqin darajasidagi test kechikishi
  225 s va u har fazada o'sadi. Sabab function-scope seed'da; tuzatish
  izolyatsiya kafolatiga tegadi, ya'ni uni "tezlashtirish" deb emas,
  **arxitektura qarori** deb ko'rish kerak.
- **⚠ Konflikt e'tibori:** bu reja `frontend/`, `services/` va
  `migrations/` ga UMUMAN tegmadi. `package.json` ga faqat ikkita skript
  qo'shildi (mavjud skriptlar o'zgarmadi).

## Self-Check: PASSED

- Da'vo qilingan 4 yangi fayl diskda mavjud: `ops/data/karmana/README.md`,
  `ops/data/karmana/.gitignore`, `scripts/karmana-import.mjs`,
  `tests/integration/test_phase2_criteria.py`
- Da'vo qilingan 2 o'zgartirilgan fayl `git diff --stat 7022ad1..HEAD` da
  ko'rinadi (6 fayl, +1625/−77)
- Beshala commit git tarixida mavjud: `e4ce21f`, `7aa6772`, `af717d6`,
  `c56ae71`, `30ff2c6`
- Birorta commit'da fayl o'chirilishi YO'Q
  (`git diff --diff-filter=D --name-only 7022ad1 HEAD` bo'sh)
- Olti sabotajdan keyin ishchi daraxt toza (`git status --short` bo'sh)
- Sinov muhiti tozalangan: `.env` YO'Q, `ops/data/karmana/local/` YO'Q,
  konteynerlar to'xtatilgan
- `STATE.md`, `ROADMAP.md` va `REQUIREMENTS.md` TEGILMADI (worktree rejimi —
  orkestrator egalik qiladi)

---
*Phase: 02-bozor-domeni-va-yangi-bozor-ustasi*
*Completed: 2026-08-01*
