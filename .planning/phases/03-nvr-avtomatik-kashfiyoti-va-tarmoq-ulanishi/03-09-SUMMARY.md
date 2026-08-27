---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 09
subsystem: frontend-nvr-yuzasi
tags: [ui, forma, auth-lock, xato-kontrakti, zod, rbac, nuqs, a11y, wave-8]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 08
    provides: "`nvrErrorView()`, `useNvrAuthLock()`, `camera-queries.ts` ning 9 hooki, 132 `cameras.*` satri"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`POST /nvr-devices`, `/test-connection`, `/{id}/password`, `/{id}/discover` va ularning xato kodlari"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 04
    provides: "`nvr_host.split_address()` va `assert_private_host()` — klientdagi ajratish/validatsiyaning MANBAI"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 01
    provides: "`camera_view` / `camera_manage` va ularning `rbac.py` bilan G-8 pariteti"
provides:
  - "`/cameras` — fazaning YAGONA marshruti: uch zona, RBAC darvozasi, `?run=`"
  - "`NvrForm` — uchta maydon, klientdagi manzil ajratish va AUTH QULFI"
  - "`NvrErrorBlock` — sabab VA tuzatish teng og'irlikda; qulflovchi kodlarda retry YO'Q"
  - "`NvrTestResult` — kanallar soni MAJBURIY, soat farqi DOIM"
  - "`NvrCard` + `NvrPasswordDialog` — pasport, taxmin qilingan port, uchta amal"
  - "`camera-page-state.ts` — to'rtta bo'sh holatning sof qarori (E-1/E-2 chegarasi)"
  - "`discoveryRunIdOf()` — 409 poyga holatining chaqiruvchi tomondagi shakli (03-08 ochiq bandi)"
  - "`errors.loadFailedTitle` / `errors.loadFailedBody` — uch tilda (03-08 ochiq bandi)"
affects: [03-10-frontend-kamera-yuzasi, 03-11-yakuniy-darvoza]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth qulfi HOOK darajasida va uning ochilish sharti EFFEKTDA, `useWatch` QIYMATLARIGA bog'langan — fokus/bosish hodisasiga emas. Sabotaj bu chegarani o'lchadi"
    - "Xato bloki `<dl>` juftligi: yorliq va mazmun BIR XIL sinf satrida, ya'ni teng og'irlik razmetkadan ham, testdan ham ko'rinadi (`terms[0].className === terms[1].className`)"
    - "ICU platsholderlari HAR DOIM to'liq uzatiladi (`minutes`/`time`/`model`/`channel`), yetishmagani `—` bo'ladi: kodga qarab tanlab uzatish «platsholder unutildi -> ekranda bo'sh blok» yo'lini ochiq qoldirardi"
    - "Soat — TASHQI TIZIM: holat interval CALLBACK ida yangilanadi, boshlang'ich qiymat `useState` ning dangasa initsializatorida (React Compiler ning `set-state-in-effect` qoidasi)"
    - "Marshrut faylining ichidagi sof qaror O'LCHANMAYDI — Next 16 tanilmagan eksportni rad etadi. Qaror `components/` ga chiqariladi, aks holda u SABOTAJDAN omon o'tadi"

key-files:
  created:
    - frontend/src/app/[locale]/(app)/cameras/page.tsx
    - frontend/src/components/cameras/nvr-form.tsx
    - frontend/src/components/cameras/nvr-form.test.tsx
    - frontend/src/components/cameras/nvr-error-block.tsx
    - frontend/src/components/cameras/nvr-error-block.test.tsx
    - frontend/src/components/cameras/nvr-test-result.tsx
    - frontend/src/components/cameras/nvr-card.tsx
    - frontend/src/components/cameras/nvr-password-dialog.tsx
    - frontend/src/components/cameras/camera-page-state.ts
    - frontend/src/components/cameras/camera-page-state.test.tsx
  modified:
    - frontend/src/lib/camera-queries.ts
    - frontend/scripts/nvr-copy.test.mjs
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "«Diagnostika» SAQLANGAN rekvizitlar bilan ishlay OLMAYDI va bu qurilgan backend bilan ziddiyat: `POST /nvr-devices/test-connection` faqat `{address, username, password}` qabul qiladi (03-06) va `{id}` ga bog'langan varianti YO'Q, parol esa hech qachon qaytarilmaydi (D-12). Tugma formani manzil va login BILAN TO'LDIRILGAN holda ochadi — bu D-03 ga ham mos: har urinish odamning ANIQ qarori va u yangi terilgan rekvizit bilan ketadi"
  - "Qurilma holati badge'i («Onlayn») RENDER QILINMADI: `nvrDeviceSchema` da bunday maydon yo'q va oxirgi skan vaqtidan «hozir onlayn» xulosasi YOLG'ON DALIL bo'lardi (03-08 ning `activation-panel` da `—` qoldirish qarorining aynan mantiqi). O'rniga skan VAQTI ko'rsatiladi"
  - "Auth qulfi IKKI mustaqil nusxada: forma o'zi, karta o'zi `useNvrAuthLock()` chaqiradi. Ular hech qachon BIR VAQTDA montaj bo'lmaydi (zona A ikkalasidan bittasini ko'rsatadi), ya'ni ajralib ketish xavfi yo'q; kartaning qulfi esa faqat «Parolni yangilash» muvaffaqiyatidan ochiladi — kartada rekvizit maydoni yo'q va bu yagona rekvizit o'zgarishi"
  - "Noma'lum kodda YORLIQLANGAN IKKI BLOK chizilmaydi: yorliq TUZILISHNI va'da qiladi, bizda esa uning yarmi yo'q. «SABAB» yorlig'i ostida umumiy jumla turib «NIMA QILISH KERAK» bo'sh qolsa, u halol «bilmayman» emas, KAMCHILIK bo'lib ko'rinardi"
  - "G-4 naqshiga CHAP so'z chegarasi qo'shildi (Rule 1): chegarasiz u `ko'chirish` ni ham ushlaydi va darvoza o'zi himoya qilayotgan izoh ustida qizaradi — bu fazada besh marta takrorlangan sinfning oltinchi holati"
  - "`cameraEmptyKind` marshrut faylidan CHIQARILDI: sabotaj S3 uni `page.tsx` ichida o'lchab bo'lmasligini ko'rsatdi (E-1 sharti olib tashlanganda BUTUN darvoza yashil qoldi)"

patterns-established:
  - "Pattern: qabul mezonining grep naqshi izohdagi literaldan farq qilmaydi — `variant=\"default\"` izohda yozilgan zahoti budjet YOLG'ON oshadi. Izohda tugma variantining NOMI emas, ROLI yoziladi"
  - "Pattern: `aria-disabled={...}` `\\bdisabled=\\{` naqshiga TUSHADI (`-` so'z chegarasi). Mezon `(^|[^-])\\bdisabled=\\{` bo'lishi kerak — aks holda u o'zi talab qilgan yechimni taqiqlaydi"
  - "Pattern: sabotaj FAQAT komponent ichida emas, MODUL CHEGARASIDA ham o'lchanadi — «bu qaror qayerda yashaydi?» savoliga javobni sabotaj beradi"

requirements-completed: []

# Metrics
duration: 105min
completed: 2026-08-03
---

# Phase 3 Plan 09: NVR yuzasi — forma, xato bloki va auth qulfi Summary

**Fazaning va'dasi ekranga chiqdi: admin uchta maydonni to'ldirib bitta tugma bosadi; xato bo'lsa SABAB va NIMA QILISH KERAK teng og'irlikda ko'rinadi; autentifikatsiya xatosidan keyin esa qayta urinish affordansi UMUMAN render qilinmaydi va qulf faqat login yoki parol qiymati o'zgarganda ochiladi.**

## Performance

- **Duration:** ~105 min
- **Tasks:** 3/3 (beshta commit — sabab «Rejadagi ziddiyatlar» B bandida)
- **Files:** 15 (10 yangi, 5 o'zgargan), 3084 qator qo'shildi
- **Sabotajlar:** 3 ta (har biri commit'dan keyin, aniq fayl bilan tiklandi)

## Accomplishments

- **Auth qulfi ishlaydi va u O'LCHANGAN** — sakkizta DOM testi, shu jumladan «tugmani qayta bosish qulfni OCHMAYDI».
- **Xato bloki har 12 kod uchun sabab VA tuzatishni render qiladi** va teng og'irlik razmetkadan ham tekshiriladi (`className` tengligi).
- **03-08 ning uchala ochiq bandi yopildi:** `errors.loadFailed*` yaratildi, manzil validatsiyasi forma qatlamiga qo'yildi, `discoveryRunIdOf()` chaqiruvchi bilan birga keldi.
- **Vitest 106 → 177** (+71). Node darvozalari **86** (o'zgarmadi), i18n **572 → 574** kalit × 3 til.
- **Yangi npm paketi qo'shilmadi** (T-03-SC): `package.json` va `package-lock.json` diffi **bo'sh**.
- **`ls "frontend/src/app/[locale]/(app)/cameras/"` -> faqat `page.tsx`** — `new/`, `[id]/`, `nvr/` kataloglari yaratilmadi (§3.1 [QAROR]).

## Task Commits

1. **Xato bloki va muvaffaqiyatli tekshiruv bloki (reja Task 3, 1-yarim)** — `c12ada1` (feat)
2. **NVR formasi — uchta maydon, manzil ajratish, auth qulfi (reja Task 2)** — `926244e` (feat)
3. **NVR kartasi va parol dialogi (reja Task 3, 2-yarim)** — `abafc93` (feat)
4. **`/cameras` sahifasi — uch zona, RBAC, `?run=` (reja Task 1)** — `731e658` (feat)
5. **E-1/E-2 chegarasini o'lchanadigan qilish (sabotaj S3 ning natijasi)** — `7d4d94d` (test)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `app/[locale]/(app)/cameras/page.tsx` | Yagona marshrut; RBAC so'rovdan OLDIN; uch zona; `?run=` (`nuqs`, `history: "replace"`); yuklanish skeletlari; E-1 va E-2 |
| `components/cameras/nvr-form.tsx` | Uchta maydon, `splitNvrAddress()`, parol maydoni + ko'rsatish tugmasi, ikki tugma, AUTH QULFI, `fieldset`/`legend` |
| `components/cameras/nvr-error-block.tsx` | `<dl>` juftligi (SABAB / NIMA QILISH KERAK), tone + ikonka, shartli retry, `<details>`, `unlock_at` taymeri |
| `components/cameras/nvr-test-result.tsx` | Model · turi · **kanallar soni** · **soat farqi**; drift ≥120 s da ogohlantirish; seriya raqami YO'Q |
| `components/cameras/nvr-card.tsx` | Pasport (`font-mono text-xs`), `rtsp_port_assumed` badge + hint, uchta amal, kartadagi auth qulfi |
| `components/cameras/nvr-password-dialog.tsx` | Bitta maydon, eski parol SO'RALMAYDI, muvaffaqiyatda qulfni ochadi |
| `components/cameras/camera-page-state.ts` | `cameraEmptyKind()` + `isDiscoveryRunId()` — sahifaning sof qarorlari |
| `lib/camera-queries.ts` | `discoveryRunIdOf()` qo'shildi (03-08 ning o'z izohi shu nomni kutgan edi) |
| `scripts/nvr-copy.test.mjs` | G-4 naqshiga chap so'z chegarasi + beshta yangi nazorat assertioni |
| `messages/{uz-Latn,ru,uz-Cyrl}.json` | `errors.loadFailedTitle` / `loadFailedBody` |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `useNvrAuthLock` ning ochilish sharti rekvizit o'zgarishidan TUGMA BOSILISHIGA ko'chirildi | `nvr-form.test.tsx` — **5 test**: «so'rov yuborilmaydi», «qayta bosish qulfni ochmaydi», «parol o'zgarganda ochiladi», «login o'zgarganda ochiladi», «ochilgandan keyin so'rov yana yuboriladi» | «qulflovchi kodda ikkala tugma bloklanadi», «retry affordansi render qilinmaydi», `typecheck`, `lint`, `nvr-error-block` (36), G-1…G-6 | ⚠ Reja **1 ta** qizarishni bashorat qilgan edi, o'lchov **5** ta berdi — ya'ni D-03 ning qulf holati va uning OCHILISH SHARTI bir-biriga bog'lanmagan ikki da'vo. Muhimi ikkinchi ustun: «qulf yoqiladi» va «retry yo'q» testlari YASHIL qoldi, ya'ni ular qulfning ochilishidan MUSTAQIL o'lchanadi |
| **S2** | `nvr-error-block.tsx` dan `fixKey` render qatori olib tashlandi | `nvr-error-block.test.tsx` — **AYNAN 12** (har kod bittadan) | **`error-codes.test.mjs` (G-1, 9 test)**, G-3/G-4/G-6, `i18n:check` (574 × 3), `typecheck` | ⚠ Rejaning bashorati **aniq tasdiqlandi**: G-1 kalitlarning MAVJUDLIGINI, komponent testi esa ularning RENDER BO'LISHINI o'lchaydi. Kalitlar joyida turgani holda D-02 ekranda yo'qoladi |
| **S3** | `cameraEmptyKind` dan E-1 sharti olib tashlandi (qurilmasiz holatda «Kameralarni topish» chiqadi) | **HECH NARSA** | **HAMMASI**: `typecheck`, `lint`, `build`, 167 vitest, 86 node testi | ⚠ **Eng qimmatli o'lchov.** Rejaning O'Z talabi («E-1 va E-2 hech qachon aralashmaydi») umuman qamralmagan edi va uni marshrut faylining ichida qamrab ham bo'lmasdi (Next 16 tanilmagan eksportni rad etadi). Qaror `camera-page-state.ts` ga chiqarildi; **sabotaj takrorlanganda endi AYNAN 1 test qizaradi** |

Uchala sabotaj ham commit'dan **keyin** bajarildi. S1 va S2 `git checkout -- <aniq fayl>` bilan, S3 (fayl hali commit qilinmagan edi) qo'lda tiklandi va tiklanish har uchalasida test bilan tasdiqlandi.

## O'lchangan dalillar

### Auth qulfi (D-03, T-03-63) — fazaning eng muhim interaksiyasi

| Da'vo | O'lchov |
|---|---|
| Qulflovchi kodda ikkala tugma ham bloklanadi | `aria-disabled="true"` ikkalasida; birlamchi tugma aksent fonini yo'qotadi |
| Retry affordansi RENDER QILINMAYDI | Rol bo'yicha ham (`queryByRole` -> `null`), **matn bo'yicha ham** (`textContent` da yo'q) — yashirilgan tugma ikkinchisidan o'tolmasdi |
| Bosilganda so'rov YUBORILMAYDI | `apiFetch` **0 marta** chaqirildi; fokus parol maydonida |
| **Qayta bosish qulfni OCHMAYDI** | Uch bosishdan keyin ham `aria-disabled="true"`, `role="status"` izohi joyida, `apiFetch` **0** |
| Qulf faqat rekvizit o'zgarganda ochiladi | Parol VA login uchun alohida test; ochilgandan keyin so'rov haqiqatan ketadi |
| Qulf HAR xatoda emas | Nazorat testi: `nvr_clock_drift` da tugmalar ochiq va retry BOR |

### Manzilni ajratish (D-01, UI-SPEC §4.1)

| Kiritilgan | Natija |
|---|---|
| `192.168.1.64` | `192.168.1.64:80`, tls=false ✅ |
| `192.168.1.64:8080` | `192.168.1.64:8080`, tls=false ✅ |
| `http://192.168.1.64` | `192.168.1.64:80`, tls=false ✅ |
| `https://192.168.1.64` | `192.168.1.64:443`, tls=true ✅ |
| `https://192.168.1.64:8443` | `192.168.1.64:8443`, tls=true ✅ |
| `nvr.local` | `nvr.local:80`, tls=false ✅ |
| `https://nvr.local:8443/doc/index.html` | `nvr.local:8443`, tls=true ✅ (yo'l qismi tashlanadi) |
| `8.8.8.8` | `public_blocked` ✅ |
| `100.100.1.5` (CGNAT) | **`ok`** ✅ — `is_global` va «xususiy emas» ni ajratadigan yagona holat |
| `192.168.1.64:0` / `:70000` / `:abc` | `invalid_port` ✅ |
| `ftp://192.168.1.64` | `invalid_address` ✅ |

Serverga **xom `address`** ketishi alohida test bilan qulflangan: ajratish klientda **validatsiya**, serverda esa **kontrakt** (03-08 ziddiyat D ning davomi).

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `format --check` + `mypy` | ✅ (backend TEGILMADI) |
| `pytest -q` | ✅ **1448** (o'zgarmadi) |
| `pytest tests/tenancy -q` | ✅ **412** (o'zgarmadi) |
| `npm run test:sim` | ✅ **61** (o'zgarmadi) |
| `npm --prefix frontend run i18n:check` | ✅ **574 kalit × 3 til** (572 -> 574) |
| frontend node testlari | ✅ **86** (o'zgarmadi) |
| frontend vitest | ✅ **177** (106 -> 177) |
| frontend typecheck / lint / build | ✅ toza / toza / `/[locale]/cameras` uchala tilda prerender |
| `git diff frontend/package{,-lock}.json` | ✅ **bo'sh** (T-03-SC) |
| `grep -rc "dangerouslySetInnerHTML" src/components/cameras/` | ✅ **0** (yettala faylda) |
| **`npm run gate`** | ✅ **exit 0 — 11 daq 16 s (676 s), «issiq» yugurish** |

⚠ **Darvoza vaqti 611 s -> 676 s (+65 s).** O'sish frontendda va u kutilgan: vitest **106 -> 177** va uning ustiga to'liq `next build`. Lekin bu **03-01 ning 618 s nomzod chegarasidan oshdi** — birinchi marta. Sabab bu rejaning o'zi emas, to'plamning tabiiy o'sishi; 03-10 yana ~30 komponent testi qo'shadi. **03-11 uchun aniq band:** chegarani qayta o'lchash va «sovuq»/«issiq» yugurishni ajratish (03-08 ning tavsiyasi), aks holda u fazani yopishda yolg'on-qizil beradi.

### Transliteratsiya (yangi ikki kalit)

| uz-Latn | uz-Cyrl (hosila) |
|---|---|
| `Ma'lumot yuklanmadi` | `Маълумот юкланмади` ✅ |
| `Sahifani yangilang yoki bir oz kutib qayta urinib ko'ring. Saqlangan ma'lumot o'zgarmadi.` | `Саҳифани янгиланг ёки бир оз кутиб қайта уриниб кўринг. Сақланган маълумот ўзгармади.` ✅ |

Buzuq shakl (`ъга`, `Асиа`, `НВР`, `аутентификатсия`) — **yo'q**; override talab qilinmadi.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Xato] G-4 naqshi `ko'chirish` ni ham ushlab, o'z izohi ustida qizardi**

- **Found during:** Task 2, birinchi `node --test scripts/nvr-copy.test.mjs`
- **Issue:** `/o['ʻʼ‘’]chirish/iu` naqshida **chap so'z chegarasi yo'q** edi, ya'ni u `o'chirish` ni **so'z ichida** ham topadi. `nvr-form.tsx` ning izohidagi `ko'chirish` («fokusni ko'chirish») darvozani qizartirdi. `ko'chirish` — kundalik o'zbekcha fe'l va D-10 ga umuman aloqasi yo'q; chegarasiz darvoza keyingi ishlovchini uni **chetlab o'tishga** majbur qilardi. Bu G-4 ning O'Z docstringi ogohlantirgan sinf (darvoza o'zi himoya qilayotgan matn ustida qizaradi) va bu fazadagi **oltinchi** takrori.
- **Fix:** Naqshga `\b` qo'shildi. Chegara HECH NARSANI bo'shashtirmaydi — u faqat `o'chirish` dan oldin **boshqa so'zning oxiri** turgan hollarni chiqaradi. Ijobiy nazorat (`O'chirish`, `«O'chirish» tugmasi` — hamon ushlanadi) va salbiy nazorat (`ko'chirish`, `nusxa ko'chirish`, `Ko'chirish` — o'tadi) testga qo'shildi.
- **Files modified:** `frontend/scripts/nvr-copy.test.mjs`
- **Commit:** `c12ada1`

**2. [Rule 2 — Yetishmayotgan kritik funksiya] E-1/E-2 chegarasi o'lchanadigan qilindi**

- **Found during:** Task 1 dan keyingi sabotaj S3
- **Issue:** Rejaning `<behavior>` bandi «E-1 va E-2 hech qachon **aralashmaydi**» deydi, lekin qoida `page.tsx` ichida, eksport qilinmagan funksiyada yashardi. Sabotaj (E-1 shartini olib tashlash — ya'ni **qurilma yo'q holatda «Kameralarni topish» tugmasini ko'rsatish**) `typecheck`, `lint`, `build`, 167 vitest va 86 node testining **birortasini ham** qizartirmadi.
- **Fix:** Qaror `components/cameras/camera-page-state.ts` ga chiqarildi (`cameraEmptyKind` + `isDiscoveryRunId`) va 10 ta test bilan qamraldi. Marshrut fayli ichida qoldirish **imkonsiz** edi: Next 16 marshrut fayllarining tanilmagan eksportini rad etadi, ya'ni funksiyani import qilib bo'lmasdi.
- **Files modified:** `camera-page-state.ts`, `camera-page-state.test.tsx`, `page.tsx`
- **Commit:** `7d4d94d`

**3. [Rule 3 — Bloklovchi] `discoveryRunIdOf()` `camera-queries.ts` ga qo'shildi**

- **Found during:** Task 1, «Qayta skanerlash» ning 409 yo'lini yozganda
- **Issue:** 409 ni `run_id` ga aylantirish IKKI chaqiruvchiga kerak (forma va sahifa). U dastlab `nvr-form.tsx` ning ichida yozilgan edi — ikkinchi nusxa muqarrar bo'lardi.
- **Fix:** `camera-queries.ts` ga ko'chirildi. **Nomi tasodifiy emas:** 03-08 ning `useStartDiscovery` izohi aynan `discoveryRunIdOf` ni nomi bilan kutgan («shakl ajratish … chaqiruvchida»). Bu 03-08 ning **3-ochiq bandi** edi va u shu bilan yopildi.
- **Files modified:** `camera-queries.ts`, `nvr-form.tsx`
- **Commit:** `731e658`

**4. [Rule 1 — Xato] `set-state-in-effect` — qulf taymerining shakli qayta loyihalandi**

- **Found during:** Task 3, `npm run lint`
- **Issue:** `nvr_account_locked` taymerining boshlang'ich qiymati effekt TANASIDA `setState` bilan qo'yilgan edi va React Compiler qoidasi (`react-hooks/set-state-in-effect`) uni rad etdi. Bu 03-08 dagi poll qoidasining aynan qo'shnisi.
- **Fix:** Soat TASHQI TIZIM sifatida ko'riladi: holat faqat interval **callback** ida yangilanadi, boshlang'ich qiymat esa `useState` ning **dangasa initsializatorida** o'qiladi — shu bilan birinchi kadrda ham to'g'ri raqam turadi va «—» dan sakrash bo'lmaydi.
- **Files modified:** `nvr-error-block.tsx`
- **Commit:** `c12ada1`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. `grep -cE "\bdisabled=\{" nvr-form.tsx` = 0 mezoni BAJARILMAS.**

Mezon o'sha satrning o'zida «`aria-disabled` ishlatiladi» deydi, lekin `-` — **so'z chegarasi**, ya'ni `\bdisabled=\{` naqshi `aria-disabled={` ni ham ushlaydi. Mezonni harfma-harf bajarish uchun ARIA atributini JSX'da ochiq yozmaslik (obyekt spread'i bilan yashirish) kerak bo'lardi — ya'ni fazaning eng muhim interaksiyasini o'qishga qiyin qilish.

**O'lchov:** rejaning naqshi bilan **2**, tuzatilgan naqsh `(^|[^-])\bdisabled=\{` bilan **0**. Ya'ni **oddiy `disabled` propi bu faylda umuman yo'q** — mezonning NIYATI to'liq bajarilgan. Tuzatilgan naqsh 03-11 uchun qayd etiladi.

**B. Task'lar BOG'LIQLIK TARTIBIDA bajarildi (3 -> 2 -> 1), beshta commit bilan.**

Bog'liqlik yo'nalishi bir tomonlama: sahifa formani, forma xato blokini iste'mol qiladi. Reja tartibida (1 -> 2 -> 3) borish birinchi commitda `page.tsx` ni mavjud bo'lmagan modullarga murojaat qildirardi — ya'ni yo build yiqilardi, yo o'rniga vaqtinchalik zaglushka yozilardi va u keyingi commitda butunlay almashtirilardi. Reja Task 3 ni ikkiga bo'lish ham shundan: `nvr-password-dialog.tsx` parol maydonini **formadan** oladi (ikkinchi a11y nusxasi yaratilmasin).

Rejaning barcha qabul mezonlari yakuniy holatda tekshirildi va bajarildi.

**C. «Diagnostika» SAQLANGAN rekvizitlar bilan ISHLAY OLMAYDI.**

UI-SPEC §4.6: *«`POST /test-connection` ni **saqlangan** rekvizitlar bilan qayta ishga tushiradi»*. Ammo qurilgan backend (03-06) bunday yo'lni **bermaydi**: `POST /nvr-devices/test-connection` faqat `{address, username, password}` qabul qiladi, `{nvr_id}` ga bog'langan varianti **umuman yo'q**, parol esa hech qachon qaytarilmaydi (D-12) — ya'ni klient uni yubora olmaydi.

**Bajarilgani:** «Diagnostika» zona (A) ni formaga almashtiradi va **manzil bilan loginni oldindan to'ldiradi**; admindan faqat parol so'raladi. Bu D-03 ga ham **yaxshiroq** mos tushadi: har diagnostika urinishi odamning aniq qarori va u yangi terilgan rekvizit bilan ketadi. Yangi endpoint 03-11/4-faza uchun ochiq band sifatida qayd etildi.

**D. Qurilma holati badge'i («Onlayn») chizilmadi.**

UI-SPEC §4.6 ning eskizida u bor, lekin `nvrDeviceSchema` (03-06) da bunday maydon **yo'q**. Oxirgi skan vaqtidan «hozir onlayn» xulosasi chiqarish **yolg'on dalil** bo'lardi — muvaffaqiyatli skan uch soat oldin bo'lishi mumkin. O'rniga **oxirgi skan vaqti** ko'rsatiladi. Bu 03-08 ning «faollashtirish panelida `—`, `0 ta` emas» qarorining aynan bir xil mantiqi.

**E. Zona (B) va zona (C) ning to'ldirilgan shoxi ATAYIN bo'sh.**

Reja buni ochiq talab qiladi: *«(B) kashfiyot paneli (03-10 to'ldiradi — bu rejada **joy qoldiriladi**), (C) kameralar ro'yxati (03-10)»*. Oraliq «Boshlanmoqda» matni ham chizilmadi: 03-09 yugurishni **poll qilmaydi**, ya'ni allaqachon tugagan yugurish uchun ham «boshlanmoqda» deb turaverardi. Batafsil — «Known Stubs».

**F. `variant="default"` mezoni izohdagi literal tufayli 3 chiqdi.**

Aksent budjetini tushuntiruvchi izohda tugma variantining nomi **literal** yozilgan edi va grep uni ham sanadi (3 ≤ 2 emas). Izoh qayta yozildi — endi u variant NOMINI emas, ROLINI («birlamchi, aksent fonli») aytadi. **O'lchov: 3 -> 2.** Bu fazadagi «grep izohni koddan ajratmaydi» sinfining yettinchi holati va u endi izohning o'zida qayd etilgan.

### Rejadan ataylab chetlangan bandlar

**G. TDD RED/GREEN commitlari ajratilmadi.** Uchala task ham `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02…03-08) — har task uchun bitta commit. **RED dalili yo'qolmadi:** uchala sabotaj darvozalarning kodsiz qizarishini (va S3 da — umuman qizarmasligini) o'lchov bilan ko'rsatadi.

**H. `requirements mark-complete` ATAYIN bajarilmadi.** Frontmatterda `requirements: [CAM-01, CAM-08]` bor, lekin bu reja ularni **yakunlamaydi**: CAM-01 ning oqimi 03-10 dagi kashfiyot paneli va kameralar ro'yxati bilan yopiladi. 03-01…03-08 ham shu sababdan belgilamagan; belgilash `03-11` ning zimmasida.

---

**Total deviations:** 4 auto-fixed (2 × Rule 1, 1 × Rule 2, 1 × Rule 3) + 6 ta rejadagi ziddiyat + 2 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. Rule 2 tuzatishi rejaning O'Z talabini o'lchanadigan qildi; Rule 1 tuzatishlari darvozani va React Compiler qoidasini to'g'riladi; Rule 3 tuzatishi 03-08 ning ochiq bandini yopdi.

## Issues Encountered

1. **Backendda «saqlangan rekvizitlar bilan diagnostika» yo'li YO'Q** (ziddiyat C). Bu UI-SPEC va qurilgan API o'rtasidagi ziddiyat va u faqat kod yozilayotganda ko'rindi — 03-06 ning o'z SUMMARY'si buni ochiq band deb yozmagan edi.
2. **React Compiler qoidasi ikkinchi marta shakl dikta qildi** (03-08 dagi poll, bu yerda taymer). Ikkala holatda ham majburiy qayta loyihalash natijani YAXSHILADI: bu yerda boshlang'ich qiymat dangasa initsializatorga o'tib, birinchi kadrdagi «—» sakrashi yo'qoldi.
3. **Marshrut faylining ichidagi qaror printsipial ravishda o'lchanmaydi** (sabotaj S3). Next 16 tanilmagan eksportni rad etadi, ya'ni «keyin test yozamiz» yo'li ham yopiq. Qoida: sahifada faqat RAZMETKA va HOOK chaqiruvi qoladi, har qanday shart `components/` ga chiqariladi.
4. **Grep-ziddiyat sinfi bu rejada IKKI marta uchradi** (G-4 ning `ko'chirish` i va `variant="default"` izohi) — ikkalasi ham sekundlar ichida topildi, chunki mezonlar birma-bir o'lchandi. Uchinchi holat (`\bdisabled=\{`) esa mezonning O'ZIDA va u tuzatib bo'lmaydigan turdan — u hujjatlashtirildi.

## Known Stubs

| Joy | Stub | Nega bu fazada yetarli | Kim yopadi |
|---|---|---|---|
| `page.tsx` — zona (B) | Kashfiyot paneli **render qilinmaydi**; `?run=` parse qilinadi, tekshiriladi va saqlanadi | Reja buni ochiq talab qiladi («joy qoldiriladi»). Oraliq matn chizish YOLG'ON holat ko'rsatardi: 03-09 yugurishni poll qilmaydi | **03-10** (UI-SPEC §5.2/§5.3 — S1…S5, poll, natija hisoblagichlari) |
| `page.tsx` — zona (C) ning to'ldirilgan shoxi | `empty === "none"` bo'lganda `null` qaytariladi | Qator o'z kontraktini (nom o'zgartirish, arxivlash, jonli ko'rish) olib keladi; yarim holatda chizish 03-10 uchun qayta yozishdan boshqa narsa bermasdi | **03-10** (UI-SPEC §6) |
| `NvrCard` — `errorCode`/`errorDetail` proplari | 03-09 da chaqiruvchi ularni **uzatmaydi** | Kartaning xato manbai — kashfiyot yugurishining natijasi, u esa zona (B) bilan birga keladi. Kontrakt va qulf mexanizmi bugundan turadi va ishlaydi | **03-10** (yugurish natijasini kartaga ulash) |
| «Diagnostika» | Saqlangan rekvizitlar bilan emas, forma orqali (parol qayta so'raladi) | Backendda `{id}` ga bog'langan `test-connection` **yo'q** (ziddiyat C) | **03-11 / 4-faza**, agar kerak bo'lsa: `POST /nvr-devices/{id}/test-connection` |

## Threat Flags

Yangi ishonch chegarasi **ochilmadi** — bu reja mavjud endpointlarga murojaat qiladi va yangi tarmoq yuzasi, yangi auth yo'li yoki sxema o'zgarishi keltirmaydi. Reja `<threat_model>` idagi yettala band bajarildi:

| Threat | Holat |
|---|---|
| T-03-63 (auth xatosidan keyin qayta urinish -> hisobning qulflanishi) | ✅ Affordans `retrySafe === false` da **render qilinmaydi**; ikkala tugma `aria-disabled`; qulf faqat rekvizit o'zgarganda ochiladi va bu **alohida test** bilan o'lchanadi; ko'rsatish tugmasi terish xatosini yuborishdan oldin ushlaydi. **Sabotaj S1** chegarani o'lchadi |
| T-03-64 (`error_detail.raw` ning HTML sifatida chizilishi) | ✅ Mazmun JSX bolasi, `whitespace-pre-wrap break-all`; `<img src=x onerror=…>` testi elementning yaratilMAGANINI tekshiradi; uzunlik 2000 belgidan kesiladi; `dangerouslySetInnerHTML` `components/cameras/` da **0** |
| T-03-65 (parolning keshga/menejerga/URL'ga tushishi) | ✅ `type="password"` + `autoComplete="new-password"`; uchala chaqiruv `useMutation`; saqlangandan keyin `reset()` va bu test bilan qulflangan; parol toast, jurnal va URL'ga chiqmaydi |
| T-03-66 (noma'lum kodda xom `detail` ning sizishi) | ✅ Noma'lum kod -> `errors.generic`; `error_detail` **ko'rsatilmaydi** (`4242` ham, `statusCode` ham DOM'da yo'q); `ERROR_DETAIL_KEYS` allowlist'i; noma'lum kalit testi |
| T-03-67 (ommaviy IP -> SSRF) | ✅ Klientda `is_global` bo'yicha blok + **tushuntirish**; chegara komponent izohida ochiq yozilgan («qulaylik, xavfsizlik chegarasi emas»); haqiqiy darvoza `assert_private_host` (03-04); CGNAT o'tishi alohida test bilan |
| T-03-68 (o'chirilgan tugma -> «nega bosilmayapti?») | ✅ Oddiy `disabled` propi **yo'q** (o'lchov: ziddiyat A); `aria-disabled` + `role="status"` izohi + fokusning parol maydoniga ko'chishi |
| T-03-SC (npm o'rnatishlari) | ✅ `package.json` va `package-lock.json` diffi **bo'sh**; barcha komponentlar mavjud `ui/` primitivlari ustida qurildi |

## Next Phase Readiness

**03-10 uchun TAYYOR:**

- `<NvrErrorBlock code detail onRetry? autoFocus? />` — `autoFocus` standart holda **`false`**, ya'ni kashfiyot `failed` bilan qaytganda fokus ko'chmaydi (§7.6 talabi allaqachon bajarilgan).
- `<NvrCard device errorCode? errorDetail? onRescan onDiagnose />` — yugurish natijasini `errorCode` bilan uzatish kifoya, qulf o'zi yoqiladi.
- `discoveryRunIdOf(error)` — 409 poyga holati; `?run=` sahifada allaqachon parse qilinadi va tekshiriladi.
- `cameraEmptyKind({archivedOnly, filtersActive, hasNvr, visibleCount})` — filtr qatori qo'shilganda faqat ikkita argument to'ladi, qaror ko'chmaydi.
- `errors.loadFailedTitle` / `loadFailedBody` uch tilda; `LoadFailed` bloki sahifada.

**03-10 uchun OCHIQ bandlar:**

1. **Zona (B) va zona (C)** — «Known Stubs» jadvalidagi birinchi ikki qator.
2. **Vendored pleyerning ikki majburiy sozlamasi** (03-08 dan meros, tegilmadi): `VideoRTC.pcConfig` tashqi STUN'ga chiqadi va `media` standarti `"video,audio"`.
3. **`Go2rtcClient.remove_stream`** hamon mahsulot yo'lida chaqirilmaydi (03-07 dan meros).

**03-11 uchun ochiq bandlar:**

1. `audit-volume` remediatsiyasi (03-04/03-06/03-07 dan meros).
2. `npm run test:sim:slow` fazani yopishdan oldin bir marta.
3. **Qabul mezonining naqshi tuzatilsin:** `\bdisabled=\{` -> `(^|[^-])\bdisabled=\{` (ziddiyat A).
4. **«Diagnostika» uchun endpoint qarori** (ziddiyat C): `POST /nvr-devices/{id}/test-connection` qo'shiladimi yoki hozirgi forma yo'li qoladimi.
5. `setup-status.cameras` ning haqiqiy sanog'i (03-08 dan meros).
6. `requirements mark-complete` — CAM-01…CAM-08 shu yerda belgilanadi.

## Self-Check: PASSED

- **Fayllar:** 15/15 mavjud (10 yangi + 5 o'zgargan) + SUMMARY
- **Commitlar:** 5/5 mavjud (`c12ada1`, `926244e`, `abafc93`, `731e658`, `7d4d94d`)
- **`must_haves.artifacts` `contains`:** 4/4 — `camera_view` (`page.tsx`), `aria-pressed` (`nvr-form.tsx`), `errorFixLabel` (`nvr-error-block.tsx`), `authLock` (`nvr-form.test.tsx`)
- **`must_haves.key_links`:** 2/2 — `useNvrAuthLock` (`nvr-form.tsx` -> `use-nvr-auth-lock.ts`), `nvrErrorView` (`nvr-error-block.tsx` -> `nvr-errors.ts`)
- **Marshrut kataloglari:** `ls "src/app/[locale]/(app)/cameras/"` -> **faqat `page.tsx`**
- **`dangerouslySetInnerHTML`:** `components/cameras/` ning yettala faylida ham **0**
- **`npm run gate`:** ✅ exit 0 (1448 / 412 / 61 / 574×3 / 86 / 177)
- **Ish daraxti:** uchala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
