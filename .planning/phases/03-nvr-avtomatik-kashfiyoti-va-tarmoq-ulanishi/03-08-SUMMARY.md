---
phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
plan: 08
subsystem: frontend-contract-and-gates
tags: [i18n, transliteratsiya, zod, tanstack-query, poll, auth-lock, vendored-artifact, sha256, supply-chain, wave-7]

# Dependency graph
requires:
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 07
    provides: "`GET/POST /cameras`, `POST /cameras/{id}/live-token`, `live_view_unavailable` (503)"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 06
    provides: "`nvr-devices` marshrutlari, `MARKET_ERROR_CODES` ning NVR kodlari, `cameras.*` ning beshta detail kaliti"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 05
    provides: "`app/services/isapi/errors.py::NVR_ERROR_CODES` — G-2 darvozasining MANBAI"
  - phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi
    plan: 01
    provides: "`lib/rbac.ts` dagi `camera_view`/`camera_manage` va ularning `rbac.py` bilan G-8 pariteti"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    plan: 20
    provides: "`domainKey(marketId, ...)` va global kalit konstantalarining ATAYIN o'chirilgani (CR-01)"
provides:
  - "`NAV_ITEMS` da `/cameras` + literal union kengaytmasi (`camera_view`)"
  - "Ustaning U-1/U-2/U-3 tuzatishlari — kamera QADAM BO'LMASDAN yo'l ko'rsatadi"
  - "132 ta `cameras.*` satri uch tilda; `uz-Cyrl` hosilasi 0 defekt bilan"
  - "`lib/nvr-errors.ts` — kod -> {causeKey, fixKey, tone, retrySafe, authLocking}"
  - "`lib/camera-queries.ts` — tug'ilishidanoq doiralangan kalitlar, 9 hook, kodbazadagi BIRINCHI poll"
  - "`lib/use-nvr-auth-lock.ts` — D-03 ning UI tarjimasi (§4.4)"
  - "`api-types.ts` — yettita zod sxemasi backend DTO'lari bilan maydonma-maydon"
  - "G-1…G-7: `error-codes.test.mjs` (kengaytirildi), `nvr-copy.test.mjs`, `vendor-integrity.test.mjs`, `gen-cyrillic.test.mjs` (kengaytirildi)"
  - "`public/vendor/go2rtc/` — SHA-256 bilan qulflangan pleyer (v1.9.14, ikki mustaqil manbadan tasdiqlangan)"
affects: [03-09-frontend-nvr-yuzasi, 03-10-frontend-kamera-yuzasi, 03-11-yakuniy-darvoza, 04-snapshot-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Poll UCH chegara bilan: terminal holat + serverning `started_at` i + ketma-ket yiqilishlar soni. Ikkinchisi klient taymeriga tayanmaydi — sahifa yangilanganda qotib qolgan yugurish yana uch daqiqa poll qilinardi"
    - "Poll qarori SOF FUNKSIYA (`discoveryPollInterval`), `refetchInterval` uni faqat chaqiradi: chegarani real vaqtga bog'lanmasdan o'lchash mumkin va test TanStack ning ichki `query.state` shakliga qadalmaydi"
    - "Qulf DAVLAT MASHINASI: `lock(code)` -> `unlockOnCredentialChange()`. Vaqt bo'yicha ochilish faqat `nvr_account_locked` da va QO'SHIMCHA shart sifatida — buzuq `unlock_at` fail-CLOSED"
    - "Vendored artefakt BAYT-BA-BAYT saqlanadi: litsenziya izohi FAYLGA QO'SHILMAYDI (upstreamda yo'q), u yonidagi `LICENSE` da — aks holda xesh upstream tegi bilan solishtirib bo'lmas edi"
    - "Vendored katalog LINTDAN CHIQARILADI: `--fix` xeshni buzib, yaxlitlik darvozasining butun mazmunini yo'q qilardi"
    - "Darvoza matn SINFINI ochiq belgilaydi: G-4 BUYRUQ FE'LINI izlaydi, o'zakni emas — `o'chirilmaydi` taqiqning TESKARISI va u matnda BO'LISHI kerak. Chegara ijobiy VA salbiy nazorat testi bilan qulflangan"

key-files:
  created:
    - frontend/src/lib/nvr-errors.ts
    - frontend/src/lib/camera-queries.ts
    - frontend/src/lib/use-nvr-auth-lock.ts
    - frontend/src/lib/nvr-errors.test.tsx
    - frontend/src/lib/camera-queries.test.tsx
    - frontend/scripts/nvr-copy.test.mjs
    - frontend/scripts/vendor-integrity.test.mjs
    - frontend/public/vendor/go2rtc/video-stream.js
    - frontend/public/vendor/go2rtc/video-rtc.js
    - frontend/public/vendor/go2rtc/LICENSE
    - frontend/public/vendor/go2rtc/README.md
    - frontend/public/vendor/go2rtc/video-stream.js.sha256
    - frontend/public/vendor/go2rtc/video-rtc.js.sha256
  modified:
    - frontend/src/components/shell/app-shell.tsx
    - frontend/src/components/wizard/wizard-steps.ts
    - frontend/src/components/wizard/wizard-stepper.tsx
    - frontend/src/components/wizard/wizard-stepper.test.tsx
    - frontend/src/components/wizard/activation-panel.tsx
    - frontend/src/lib/api-types.ts
    - frontend/src/lib/market-errors.ts
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json
    - frontend/messages/uz-Cyrl.overrides.json
    - frontend/messages/README.md
    - frontend/scripts/gen-cyrillic.test.mjs
    - frontend/scripts/error-codes.test.mjs
    - frontend/eslint.config.mjs
    - .planning/phases/03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-UI-SPEC.md

key-decisions:
  - "TOPILMA (rejada yo'q): `video-stream.js` — YOLG'IZ ISHLAMAYDIGAN modul. Uning birinchi qatori `import {VideoRTC} from './video-rtc.js'`, ya'ni faqat uni vendoring qilish 03-10 ni ikki yo'ldan biriga majburlardi: yo bog'liqlikni runtime'da go2rtc'dan yuklash (D-11 ning buzilishi), yo o'z pleyerini yozish (UI-SPEC §1.4.1 ochiq rad etgan). IKKALASI ham vendored va IKKALASINING ham xeshi qayd etilgan"
  - "TOPILMA: `docker cp` YO'LI ISHLAMAYDI — go2rtc statik fayllarni Go `embed` bilan binar ICHIDA olib yuradi (`find / -name video-stream.js` -> 0 natija). Ikkinchi yo'l konteynerning O'Z HTTP yuzasidan olish bilan bajarildi va u GitHub tegidan olingan bayt bilan AYNAN mos keldi — bu oddiy nusxa emas, YETKAZIB BERISH ZANJIRINING ikki tomonlama tasdig'i"
  - "MIT izohi vendored `.js` FAYLGA QO'SHILMADI: upstream v1.9.14 da u YO'Q. Izoh qo'shish faylni upstreamdan farqli qilardi va yozib qo'yilgan xesh `AlexxIT/go2rtc` tegi bilan mustaqil solishtirib bo'lmas holga kelardi — ya'ni darvozaning eng qimmatli xususiyati yo'qolardi. MIT talabi yonidagi `LICENSE` fayli bilan bajariladi va G-7 uni tekshiradi"
  - "Poll chegarasi KLIENT TAYMERIDAN SERVER VAQTIGA ko'chirildi. `useRef` + `Date.now()` varianti React Compiler qoidalariga urildi (`react-hooks/refs`, `react-hooks/purity`), lekin muhimrog'i — u UI-SPEC §5.4 ga ZID edi: `?run=` bilan sahifa yangilanganda taymer noldan boshlanardi va qotib qolgan yugurish HAR yangilashda yana uch daqiqa poll qilinardi"
  - "IKKINCHI, mustaqil poll chegarasi qo'shildi (`DISCOVERY_POLL_MAX_FAILURES = 3`): server umuman javob bermasa `started_at` HECH QACHON kelmaydi va birinchi chegara mangu ochiq qolardi. UI-SPEC §5.3 buni «3 ta ketma-ket tarmoq xatosi -> S5» deb allaqachon talab qilgan"
  - "O'n ikki ISAPI kodi `api-types.ts::ERROR_CODES` ga QO'SHILMADI — reja shuni so'ragan bo'lsa ham. Sabab 03-06 ning o'z izohida yozilgan va u kuchli: o'sha massiv HTTP `detail` kodlari uchun (to'g'ridan-to'g'ri 4xx), ISAPI kodlari esa javob TANASIDAGI `error_code` maydoni (`test-connection` HAR DOIM 200 qaytaradi). Aralashtirish «ulanmadi» ni oddiy toast qilib, D-02 ning butun mazmunini yo'qotardi. Kodlar `nvr-errors.ts` da yashaydi va G-2 ularni backend reyestri bilan solishtiradi"
  - "G-4 BUYRUQ FE'LINI izlaydi (`o'chirish`/`удалить`/`delete`), O'ZAKNI emas. Chegara o'lchangan: `cameras.archiveBody` ning o'zi «tarixi o'chirilmaydi» deydi (ru: «не удаляются») va bu taqiqning AYNAN TESKARISI — u matnda BO'LISHI kerak. O'zak bo'yicha qidiruv darvozani o'zi himoya qilayotgan matn ustida qizartirardi (bu fazada BESH marta uchragan sinf). Chegara ijobiy VA salbiy nazorat testi bilan qulflandi"
  - "G-3 FAQAT `errorCause.*` ustida ishlaydi va bu ham o'lchangan: `errorFix.nvr_isapi_unavailable` ning ruschasi «Возможно, введён адрес камеры» deydi va u TO'G'RI — u sababni emas, TUZATISH yo'lidagi ehtimolni bildiradi. Darvozani `cameras.*` ga kengaytirish uni uchta to'g'ri satr ustida qizartirardi"
  - "`live_view_unavailable` (503) ko'zguga qo'shildi (03-07 ning ochiq bandi): u `MARKET_ERROR_CODES` da yo'q va bo'lmaydi ham (u domen rad javobi emas, tashqi servisning holati), lekin ko'zgusiz 503 `errors.generic` ga tushardi va admin NIMA qilishni bilmasdi — D-02 ning aynan buzilishi"
  - "Faollashtirish panelidagi kamera sanog'i `—`, `status.cameras` EMAS: backend bu maydonni HAR DOIM `0` qaytaradi (`markets.py::_setup_status_response` — D-16 ning «ilgagi»). «0 ta» yozish kameralar ulangandan keyin ham ekranda turar va YOLG'ON dalil bo'lardi. UI-SPEC §3.4 U-3 ikkala qiymatga ham ruxsat beradi"
  - "Manzilni `host`/`port`/`use_tls` ga ajratish KLIENTDA QILINMAYDI: UI-SPEC §4.1 shuni aytadi, lekin backend (`NvrDeviceCreateRequest`) XOM `address` qabul qiladi va ajratishni o'zi bajaradi. Qurilgan kontrakt yutadi — ikki grammatika bir kun ajralib ketardi"

patterns-established:
  - "Pattern: ikki darvoza IKKI XIL narsani o'lchaydi va buni SABOTAJ bilan isbotlash mumkin — `i18n:check` (parity) va `gen-cyrillic.test.mjs` (SIFAT) bir-birining o'rnini bosmaydi"
  - "Pattern: kalit UCHALA tildan olib tashlanganda parity darvozasi YASHIL qoladi — to'plam TO'LIQLIGINI faqat backend reyestrini o'qiydigan darvoza (G-1) ushlaydi"
  - "Pattern: transliteratsiya darvozasi ikki qatlamli — «lotin harfi qolmadi» (ko'rinadigan defekt) VA buzuq-shakl ro'yxati (SEMANTIK defekt, chiqish sof kirill bo'lgani uchun birinchisi uni KO'RMAYDI)"
  - "Pattern: uchinchi tomon artefakti IKKI MUSTAQIL manbadan olinadi va xeshlar solishtiriladi — bitta manba faqat «nusxa oldim» deydi, ikkitasi «manba buzilmagan» deydi"
  - "Pattern: darvoza o'z izlash satrlarini olib yuradi, lekin SKANERLANADIGAN daraxtdan tashqarida yashaydi (`scripts/` vs `src/`) — bu izohda ochiq yozilishi shart, aks holda keyingi ishlovchi uni `src/` ga ko'chirib darvozani o'ldiradi"

requirements-completed: []

# Metrics
duration: 95min
completed: 2026-08-03
---

# Phase 3 Plan 08: Frontend kontrakti va yettita mexanik darvoza Summary

**D-02 va D-10 endi hujjatdagi niyat emas, CI shartidir: har xato kodi uchun sabab VA tuzatish uchala tilda majburiy, «o'chirish» fe'li kamera yuzasida taqiqlangan — va vendored go2rtc pleyeri ikki mustaqil manbadan bayt-ba-bayt tasdiqlanib SHA-256 bilan qulflandi.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3/3
- **Files:** 29 (13 yangi, 16 o'zgargan), 3976 qator qo'shildi
- **Sabotajlar:** 6 ta (har biri commit'dan keyin, `git checkout -- <aniq fayl>` bilan tiklandi)

## Accomplishments

- **Yettita darvoza ham ishlaydi va HAR BIRI sabotaj bilan o'lchandi** — G-1…G-7 (G-8 03-01 dan meros va tegilmadi).
- **Vendored pleyer IKKI mustaqil yo'ldan olinib xeshlari solishtirildi** (GitHub tegi va `alexxit/go2rtc:1.9.14` image'i) — natija bayt-ba-bayt mos.
- **Rejada yo'q bog'liqlik topildi:** `video-stream.js` yolg'iz ishlamaydi; `video-rtc.js` ham vendored, aks holda 03-10 D-11 ni buzishga majbur bo'lardi.
- **Poll kontrakti kodbazada birinchi marta o'rnatildi** va u rejadagidan KUCHLIROQ chiqdi: uch chegara, ikkitasi mustaqil.
- **Bazaviy darvoza kengaydi:** node **60 → 86** (+26), vitest **74 → 106** (+32), i18n **444 → 572** kalit × 3 til. Backend (1448 / 412 / 61) **tegilmadi**.
- **Yangi npm paketi qo'shilmadi** (T-03-SC): `frontend/package-lock.json` va `dependencies` bloki diffi **bo'sh**.

## Task Commits

1. **Task 1: Navigatsiya, ustaning uch tuzatishi va uch tilli matn katalogi (G-5)** — `a1f0ed2` (feat)
2. **Task 2: zod sxemalari, xato moduli, doiralangan so'rov qatlami va auth qulfi** — `2507cae` (feat)
3. **Task 3: Oltita mexanik darvoza va vendored go2rtc pleyeri (G-1…G-7)** — `a163a44` (feat)

## Files Created/Modified

| Fayl | Nima qiladi |
|---|---|
| `lib/nvr-errors.ts` | UI-SPEC §7.3 jadvali kod sifatida; `nvrErrorView()` beshta qiymat; `AUTH_LOCKING_CODES` jadvaldan HOSIL bo'ladi; `pickErrorDetail`/`rawDetailText` |
| `lib/camera-queries.ts` | Uchta kalit fabrikasi (hammasi `marketId` bilan boshlanadi), 9 hook, `discoveryPollInterval` sof funksiyasi, oltita konstanta |
| `lib/use-nvr-auth-lock.ts` | §4.4 — qulf faqat rekvizit QIYMATI o'zgarganda ochiladi; `nvr_account_locked` da ikkala shart; buzuq `unlock_at` fail-closed |
| `lib/api-types.ts` | 7 sxema + 2 enum + `isTerminalRunStatus`; `password`/`stream_name`/`rtsp_url` UMUMAN yo'q |
| `lib/market-errors.ts` | `live_view_unavailable` -> `cameras.liveUnavailable` |
| `shell/app-shell.tsx` | `/cameras` yozuvi (`camera_view`, `market`, `/calendar` dan keyin) + literal unionlar |
| `wizard/{wizard-steps,wizard-stepper,activation-panel}` | U-1/U-2/U-3 — havola, `aria-disabled` yo'q, qadam maqomi berilmagan |
| `messages/{uz-Latn,ru}.json` | 132 ta `cameras.*` satri (+ `nav.cameras`, `wizard.cameraNote`) |
| `messages/uz-Cyrl.overrides.json` | 21 yangi yozuv (20 ta §11.7 dan + o'lchov bilan topilgan `filtrini`) |
| `messages/README.md` | Qoida 1 kengaytirildi (akronimlar) + **Qoida 5** (semantik defekt) |
| `scripts/nvr-copy.test.mjs` | G-3, G-4, G-6 + ikkita nazorat testi |
| `scripts/vendor-integrity.test.mjs` | G-7 — xesh, import grafi, MIT, teg |
| `scripts/error-codes.test.mjs` | G-1, G-2 + `readPythonTuple` parseri |
| `scripts/gen-cyrillic.test.mjs` | G-5 — beshta kutilgan chiqish, ikkita copy qoidasi, 7 yangi buzuq-shakl |
| `public/vendor/go2rtc/*` | Pleyer (2 fayl), `LICENSE`, `README.md`, ikkita `.sha256` |
| `eslint.config.mjs` | `public/vendor/**` ignore — lint xeshni buzmasin |

## Sabotajlar — nima qizardi VA nima yashil qoldi

| # | Sabotaj | Qizardi | **Yashil qoldi** | Ma'nosi |
|---|---|---|---|---|
| **S1** | `uz-Cyrl.overrides.json` dan `"NVR"` olib tashlandi + qayta generatsiya | `gen-cyrillic.test.mjs` — **AYNAN 2**: `T-05` (kutilgan chiqish) va buzuq-shakl ro'yxati (`НВР`) | **`i18n:check` (exit 0)** + o'sha fayldagi 51 test, shu jumladan «lotin harfi qolmagan» | Ikki darvoza IKKI XIL narsani o'lchaydi. Muhimi: «lotin harfi qolmagan» testi ham YASHIL qoldi — `НВР` sof kirill, ya'ni akronimning yo'qolishini FAQAT kutilgan-chiqish assertioni ushlaydi |
| **S2** | `camerasKey` dan `marketId` argumenti olib tashlandi | `typecheck` — **6 xato**, shu jumladan modulning O'ZIDA (`Cannot find name 'marketId'`) | — | Doiralash STRUKTURAVIY: `domainKey` ning birinchi argumenti majburiy |
| **S2b** | O'sha, LEKIN literal bilan: `domainKey("cameras", ...)` | `typecheck` — **5 xato** (chaqiruvchilarda) **va** `camera-queries.test.tsx` — **2 test** | Qolgan 12 test | ⚠ **Nozik holat:** `domainKey("cameras", ...)` TIP JIHATIDAN YAROQLI (birinchi argument `string`). Modul ichidagi xato yo'qoladi va faqat CHAQIRUVCHILAR hamda kalit-shakli testi qizaradi. Ya'ni tip tizimi yolg'iz YETARLI EMAS — kalit shaklining birlik testi kerak |
| **S3** | `uz-Latn.json` dan bitta `cameras.errorFix.*` olib tashlandi | `error-codes.test.mjs` — **AYNAN 1** (G-1, kod va **ikkala** til nomi bilan); `i18n:check` — **1 muammo** (`ru.json` da ORTIQCHA) | Qolgan 8 test | Ikkalasi ham qizardi, lekin BOSHQA SABABDAN: G-1 «kalit YO'Q» deydi, `i18n:check` esa «ru'da ortiqcha» — u kalit KERAKLIGINI bilmaydi |
| **S3b** | O'sha kalit **uchala** tildan olib tashlandi | `error-codes.test.mjs` — **AYNAN 1** (G-1, uchala til nomi bilan) | **`i18n:check` (exit 0, 571 kalit × 3)** | ⚠ **Hal qiluvchi o'lchov.** Parity darvozasi to'plam TO'LIQLIGINI ko'rmaydi — D-02 ni faqat backend reyestrini o'qiydigan G-1 ushlaydi. Rejaning savoliga aniq javob |
| **S4** | `errorCause.nvr_stream_limit` boshidan hedge so'zi olib tashlandi | `nvr-copy.test.mjs` — **AYNAN 1** (G-3 birinchi assertioni) | `i18n:check`, `error-codes.test.mjs`, `gen-cyrillic.test.mjs`, G-3 ning ikkinchi assertioni | D-05 ni boshqa hech bir darvoza qamramaydi |
| **S5** | Vendored `video-stream.js` ga bitta izoh qatori qo'shildi | `vendor-integrity.test.mjs` — **AYNAN 1** (eski va yangi xesh bilan) | **Hammasi**: `nvr-copy`, `error-codes`, `gen-cyrillic`, `role-gate`, `wizard-reachability`, `audit-actions`, `typecheck`, `lint` | T-03-55 ning butun mazmuni: uchinchi tomon kodining jimgina o'zgarishini BOSHQA HECH QANDAY darvoza ko'rmaydi |

Hamma sabotajlar commit'dan **keyin** bajarildi va `git checkout -- <aniq fayl>` bilan tiklandi; har birida ish daraxti toza qoldi.

## O'lchangan dalillar

### Vendored artefakt — ikki tomonlama tasdiq (T-03-55)

| Yo'l | `video-stream.js` | `video-rtc.js` |
|---|---|---|
| GitHub `v1.9.14` tegi | `86b4b690…70b16` | `d48ce627…e64fb` |
| `alexxit/go2rtc:1.9.14` image'i | **AYNAN o'sha** | **AYNAN o'sha** |

⚠ `docker cp` **ishlamadi**: `find / -name video-stream.js` konteynerda **0 natija** berdi — go2rtc statik fayllarni Go `embed` bilan binar ichida olib yuradi. Ikkinchi yo'l konteynerning HTTP yuzasidan olish bilan bajarildi; versiya kafolati o'zgarmadi (image **tegi**).

**Ko'rik natijasi** (ikkala fayl to'liq o'qildi): `eval(`, `new Function`, `document.write`, `fetch(` — **yo'q**; obfuskatsiya — **yo'q**. Ikkita band 03-10 uchun qayd etildi (UI-SPEC §14.2): `VideoRTC.pcConfig` standart holda **tashqi STUN serverlariga** murojaat qiladi (Cloudflare, Google) va `media` standarti `"video,audio"` — ikkalasi ham `live-player.tsx` da bekor qilinishi kerak.

### Transliteratsiya (G-5)

| Holat | Chiqish |
|---|---|
| `NVR qurilmasiga ulanib bo'lmadi` | `NVR қурилмасига уланиб бўлмади` ✅ |
| `NTP xizmatini yoqing` | `NTP хизматини ёқинг` ✅ |
| `WireGuard tunneli yoqilganini tekshiring` | `WireGuard туннели ёқилганини текширинг` ✅ |
| `... digest/basic qilib belgilang` | `... digest/basic қилиб белгиланг` ✅ |
| `digest autentifikatsiyasini qabul qilmayapti` | `digest аутентификациясини қабул қилмаяпти` ✅ |
| `NVR'ga ulanmadi` (taqiqlangan shakl) | `НВРъга уланмади` ❌ — copy qoidasining mavjudlik sababi |
| `Asia/Tashkent` (taqiqlangan shakl) | `Асиа/Ташкент` ❌ — **sof kirill**, skript ko'rmaydi |

Yetkazilayotgan `uz-Cyrl.json` da `НВР`, `РТСП`, `НТП`, `ъга`, `ъни`, `Асиа`, `аутентификатсия` — **hech biri yo'q**.

⚠ **O'lchov bilan topilgan defekt (rejada yo'q):** `Holat filtrini o'zgartiring` -> `Ҳолат филтрини…` (yumshatish belgisiz). `filtrini` override lug'atida yo'q edi — bu `README.md` Qoida 2 ning (agglyutinatsiya) aynan takrori. Qo'shildi.

### Darvozalar

| Darvoza | Fayl | Holat |
|---|---|---|
| **G-1** sabab↔tuzatish pariteti (uch til) | `error-codes.test.mjs` | ✅ 12 kod × 2 matn × 3 til |
| **G-2** kod qamrovi (backend -> ko'zgu) | `error-codes.test.mjs` | ✅ ikki yo'nalishda (yetishmagan VA ortiqcha) |
| **G-3** hedging yagonaligi | `nvr-copy.test.mjs` | ✅ faqat `nvr_stream_limit` |
| **G-4** «o'chirish» taqig'i | `nvr-copy.test.mjs` | ✅ 132 satr + nazorat testi |
| **G-5** transliterator regressiyasi | `gen-cyrillic.test.mjs` | ✅ 5 holat + 2 copy qoidasi |
| **G-6** go2rtc yuzasi taqig'i | `nvr-copy.test.mjs` | ✅ `frontend/src` da **0** hodisa |
| **G-7** vendored yaxlitlik | `vendor-integrity.test.mjs` | ✅ 2 fayl + import grafi + MIT + teg |
| **G-8** RBAC ko'zgusi | `role-gate.test.mjs` (03-01) | ✅ tegilmadi, yashil |

### Bazaviy darvoza

| Bosqich | Natija |
|---|---|
| `ruff check` + `format --check` + `mypy` | ✅ exit 0 (192 fayl / 187 manba) |
| `pytest -q` | ✅ **1448** (o'zgarmadi) |
| `pytest tests/tenancy -q` | ✅ **412** (o'zgarmadi) |
| `npm run test:sim` | ✅ **61** (o'zgarmadi) |
| `npm --prefix frontend run i18n:check` | ✅ **572 kalit × 3 til** (444 -> 572) |
| frontend node testlari | ✅ **86** (60 -> 86) |
| frontend vitest | ✅ **106** (74 -> 106) |
| frontend typecheck / lint / build | ✅ toza / toza / to'liq prerender |
| `grep -rnE "/api/streams\|exec:\|ffmpeg:" frontend/src` | ✅ **0** |
| `sha256sum -c *.sha256` | ✅ ikkala fayl **OK** |
| `git diff frontend/package-lock.json` | ✅ toza (T-03-SC) |
| **`npm run gate`** | ✅ **exit 0** — **~10 daqiqa (611 s)** |

⚠ **Darvoza vaqti 932 s -> ~611 s ga TUSHDI.** Bu bu rejaning yutug'i emas: og'irlik backendda va u tegilmagan; 03-07 dagi 932 s `test:sim` bosqichining `alexxit/go2rtc:1.9.14` image'ini **birinchi marta tortib olishini** ham o'z ichiga olgan edi. Ya'ni 03-01 ning 618 s nomzod chegarasi — realistik, lekin u **image keshda bo'lganda**. `03-11` uchun qayd: chegarani o'lchashda «sovuq» va «issiq» yugurishni ajratish kerak.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 — Yetishmayotgan kritik funksiya] `video-rtc.js` ham vendored qilindi**

- **Found during:** Task 3, pleyer fayli birinchi marta o'qilganda
- **Issue:** Reja va UI-SPEC §1.4.1 faqat `www/video-stream.js` ni nomlaydi. Ammo o'sha faylning **birinchi qatori** — `import {VideoRTC} from './video-rtc.js'`, ya'ni u 2.5 KB lik GUI qobig'i va butun WebRTC → MSE → HLS mantiqi 22 KB lik qo'shni faylda. Yolg'iz `video-stream.js` — **ishlamaydigan ES modul**. 03-10 Task 3 (`live-player.tsx`) uni iste'mol qilganda ikki yo'ldan biriga majbur bo'lardi: (a) bog'liqlikni runtime'da go2rtc'dan yuklash — **D-11 ning to'g'ridan-to'g'ri buzilishi** va nginx allow-listiga yana bitta yozuv; (b) o'z pleyerini yozish — UI-SPEC §1.4.1 ochiq **rad etgan**.
- **Fix:** Ikkala fayl ham vendored; ikkalasining ham `.sha256` i qayd etilgan. G-7 ga to'rtinchi test qo'shildi: `video-stream.js` ning `import` grafidagi har fayl vendored bo'lishi shart — ya'ni kelajakdagi versiya yangi bog'liqlik keltirsa, u **xeshsiz kirib kela olmaydi**.
- **Committed in:** `a163a44`

**2. [Rule 3 — Bloklovchi] MIT izohi faylga qo'shilmadi, `LICENSE` yoniga qo'yildi**

- **Found during:** Task 3, qabul mezoni `grep -c "MIT" video-stream.js` ≥ 1 ni tekshirganda
- **Issue:** Mezon **bajarilmas**: upstream `v1.9.14` ning ikkala faylida ham litsenziya izohi **YO'Q** (o'lchandi). UI-SPEC §14.2 «fayl boshidagi litsenziya izohi **saqlanadi**» deydi — ya'ni mavjud bo'lsa. Izohni **qo'shish** faylni upstreamdan farqli qilardi va yozib qo'yilgan xesh `AlexxIT/go2rtc` tegi bilan **mustaqil solishtirib bo'lmas** holga kelardi — yaxlitlik darvozasining eng qimmatli xususiyati aynan shu solishtirish imkoniyati.
- **Fix:** `.js` fayllar **bayt-ba-bayt** upstream nusxasi bo'lib qoldi; MIT matni (`Copyright (c) 2022 Alexey Khit`) yonidagi `LICENSE` faylida va G-7 uning mavjudligini hamda mazmunini tekshiradi. Sabab test docstringida yozildi. `grep -c "MIT" video-stream.js` = **0** va bu ATAYIN.
- **Committed in:** `a163a44`

**3. [Rule 2 — Yetishmayotgan kritik funksiya] `live_view_unavailable` ko'zguga qo'shildi**

- **Found during:** Task 2 (03-07 SUMMARY ning «Next Phase Readiness» bandi)
- **Issue:** `POST /cameras/{id}/live-token` go2rtc javob bermaganda **503** `live_view_unavailable` qaytaradi, lekin bu kod `MARKET_ERROR_CODES` da yo'q va `error-codes.test.mjs` uni **ko'rmaydi** (u faqat backend -> frontend yo'nalishini tekshiradi). Natija: admin «Kutilmagan xato yuz berdi» ni ko'rardi va NIMA qilishni bilmasdi — D-02 ning aynan buzilishi.
- **Fix:** `ERROR_CODES` ga izoh bilan qo'shildi (nega u backend reyestrida **yo'q**: 503 domen rad javobi emas), `market-errors.ts` ga `case`, `cameras.liveUnavailable` uch tilda. Matn qayta urinishning **xavfsiz** ekanini ochiq aytadi — bu yo'l NVR hisobiga urinish yubormaydi (§8.5).
- **Committed in:** `2507cae`

**4. [Rule 3 — Bloklovchi] Poll chegarasi klient taymeridan server vaqtiga ko'chirildi**

- **Found during:** Task 2, `npm run lint`
- **Issue:** Rejadagi shakl (`startedAt` ni `useRef` da saqlash) React Compiler qoidalariga urildi: `react-hooks/refs` («Cannot update ref during render») va `react-hooks/purity` («`Date.now` is an impure function»). Lekin `useEffect` ga ko'chirish **yetarli emas edi**: klient taymeri UI-SPEC §5.4 ga zid — `?run=` bilan sahifa yangilanganda yoki yugurish boshqa qurilmadan ochilganda taymer **noldan** boshlanardi va qotib qolgan yugurish har yangilashda yana uch daqiqa poll qilinardi.
- **Fix:** Chegara yugurishning **`started_at`** iga (server vaqti) tayanadi va u sahifa yangilanishidan omon o'tadi. Qaror `discoveryPollInterval` sof funksiyasiga chiqarildi — `refetchInterval` uni faqat chaqiradi.
- **Committed in:** `2507cae`

**5. [Rule 2 — Yetishmayotgan kritik funksiya] Ikkinchi, mustaqil poll chegarasi**

- **Found during:** Task 2, 4-tuzatishning oqibatini tekshirganda
- **Issue:** `started_at` **birinchi muvaffaqiyatli javobdan keyin** paydo bo'ladi. Server umuman javob bermasa (tarmoq uzildi, 500) u hech qachon kelmaydi va yagona chegara **mangu ochiq** qolardi — ya'ni «cheksiz poll hech qachon» qoidasi aynan eng ehtimolli nosozlikda buzilardi. UI-SPEC §5.3 buni allaqachon talab qilgan: «3 ta ketma-ket tarmoq xatosi -> S5».
- **Fix:** `DISCOVERY_POLL_MAX_FAILURES = 3` — `query.state.fetchFailureCount` bo'yicha. Ikkala chegara ham `discoveryPollInterval` da va ikkalasi ham alohida test bilan o'lchandi.
- **Committed in:** `2507cae`

**6. [Rule 1 — Xato] `filtrini` override lug'atida yo'q edi**

- **Found during:** Task 1, birinchi generatsiyadan keyingi skanerlash
- **Issue:** `cameras.emptyFilteredHint` = «Holat **filtrini** o'zgartiring…» -> `Ҳолат **филтрини**…` — yumshatish belgisiz. Bu 2-fazadagi `T-03` (`filtr` -> `фильтр`) defektining aynan davomi: lug'at **butun so'zni** qidiradi va `filtrga`/`filtrni`/`filtrdan` bor edi-yu, `filtrini` yo'q edi.
- **Fix:** Override qo'shildi. Buzuq-shakl ro'yxati (`филтр`) uni ushladi — ya'ni 2-fazadagi darvoza 3-fazadagi matnda **ishladi**.
- **Committed in:** `a1f0ed2`

**7. [Rule 3 — Bloklovchi] `eslint.config.mjs` ga `public/vendor/**` ignore**

- **Found during:** Task 3
- **Issue:** `npm run lint` = `eslint .` va u butun `frontend/` ni yuradi. Bugun vendored fayllar toza o'tdi, lekin keyingi upstream versiyasi yoki qoida yangilanishi ularni qizartirishi mumkin — va yagona «tuzatish» faylni **tahrirlash** bo'lardi, bu esa xeshni buzib G-7 ning butun mazmunini yo'q qilardi.
- **Fix:** `public/vendor/**` global ignore, sababi izohda: uslub darvozasi bu yerda **yaxlitlik darvozasidan past turadi**.
- **Committed in:** `a163a44`

**8. [Rule 3 — Bloklovchi] `nvr-errors.test.ts` -> `.test.tsx`**

- **Found during:** Task 2
- **Issue:** `vitest.config.ts` ning `include` naqshi — `src/**/*.test.tsx` (faqat `.tsx`). `.ts` fayl **jimgina** ishga tushmasdi: `vitest run` uni ko'rmay, «hammasi yashil» deb chiqardi.
- **Fix:** Fayl `.test.tsx` ga ko'chirildi (konfiguratsiyaning o'z izohi shu konvensiyani talab qiladi). Konfiguratsiya **o'zgartirilmadi**.
- **Committed in:** `2507cae`

### Rejadagi ziddiyatlar (NIYAT bajarildi, literal emas)

**A. O'n ikki ISAPI kodi `ERROR_CODES` ga qo'shilmadi.**

Reja: *«`ERROR_CODES` massiviga backendning yangi kodlari qo'shiladi (o'n ikki NVR kodi + …)»*. Qolgan to'rttasi (`nvr_host_taken`, `nvr_host_public_blocked`, `discovery_already_running`, `nvr_not_found`) **allaqachon bor** (03-06), o'n ikkitasi esa 03-06 tomonidan **ATAYIN** chiqarib qoldirilgan va sabab o'sha faylning izohida yozilgan: bu massiv HTTP `detail` kodlari uchun, ISAPI kodlari esa javob **tanasidagi** `error_code` maydoni (`test-connection` **har doim 200** qaytaradi). Aralashtirish «ulanmadi» ni oddiy toast qilib D-02 ni yo'q qilardi.

**Bajarilgani:** kodlar `nvr-errors.ts::NVR_ERROR_CODES` da yashaydi va **G-2** ularni backend reyestri bilan **ikki yo'nalishda** solishtiradi — rejaning maqsadi (mexanik qamrov) to'liq bajarildi, ikkita yuza aralashmadi.

**B. Faollashtirish panelidagi sanoq `—`, `{count}` emas.**

Reja: *«`activation-panel.tsx` da qator havolaga aylanadi va sanoq ko'rsatiladi»*. `setup-status` javobida `cameras` maydoni **bor**, lekin backend uni **har doim `0`** qaytaradi (`markets.py::_setup_status_response` — D-16 ning ilgagi). «0 ta» yozish kameralar ulangandan keyin ham ekranda turar va **yolg'on dalil** bo'lardi. UI-SPEC §3.4 U-3 `—` ga ochiq ruxsat beradi.

**Bajarilgani:** qator **havola** bo'ldi (U-3 ning asosiy talabi), qiymat `—`. Haqiqiy sanoq — «Known Stubs» bo'limida, bir qatorlik o'zgarish sifatida.

**C. `frontend/package.json` tegilmadi.**

Reja uni `files_modified` da sanaydi. Ammo `"test": "node --test scripts/*.test.mjs && vitest run"` — **glob**, ya'ni yangi `.test.mjs` fayllari mavjud zanjirga **avtomatik** qo'shildi (o'lchov: 71 -> 86 test). Rejaning o'z talabi — *«`error-codes.test.mjs` qanday ishga tushirilayotgan bo'lsa o'sha yo'l bilan»* — aynan shu.

**D. Manzilni ajratish klientda emas, serverda.**

UI-SPEC §4.1: *«Ajratish klientda (`zod` `.transform()`) bajariladi; serverga allaqachon ajratilgan `{host, port, use_tls}` yuboriladi»*. Ammo qurilgan backend (`NvrDeviceCreateRequest`, 03-06) **xom `address`** qabul qiladi va ajratishni o'zi bajaradi — uning docstringi buni ochiq yozgan: *«klientdagi ajratish QULAYLIK, bu yerdagisi esa KONTRAKT»*.

**Bajarilgani:** `useCreateNvr`/`useTestConnection` `{address, username, password}` yuboradi. Klient tomonidagi **validatsiya** (§4.7 — ommaviy IP, port oralig'i) forma qatlamiga tegishli va u 03-09/03-10 da keladi.

**E. `wizard-stepper.test.tsx` ning ikkita da'vosi TESKARISIGA o'zgardi.**

Mavjud test kamera elementining **havola emasligini** va `aria-disabled` **borligini** qulflagan edi. U-2 ikkalasini ham bekor qiladi. Da'volar yangilandi va **kuchaytirildi**: endi havola `href="/cameras"` ga borishi, `aria-disabled` **yo'qligi**, hamda qadam maqomi **berilmagani** (matnda raqam yo'q, `aria-current` yo'q) tekshiriladi — D-16 aynan shu ikki belgi orqali buzilardi.

**F. `wizard.cameraLater` -> `wizard.cameraNote` (kalit nomi o'zgardi).**

UI-SPEC §11.5 yangi kalitni `wizard.cameraNote` deb nomlaydi. Eski kalitni qoldirish o'lik kalit tug'dirardi (`i18n:check` uni ko'rmaydi — u uchala tilda ham bor edi). Kalit **ko'chirildi**, matn yangilandi, `activation-panel.tsx` dagi chaqiruv ham.

### Rejadan ataylab chetlangan bandlar

**G. TDD RED/GREEN commitlari ajratilmadi.** Uchala task ham `tdd="true"`, `.planning/config.json` da esa `workflow.tdd_mode: false`. Faza konventsiyasi (03-02…03-07) — har task uchun bitta commit. **RED dalili yo'qolmadi:** oltala sabotaj darvozalarning kodsiz qizarishini o'lchov bilan ko'rsatadi.

**H. `requirements mark-complete` ATAYIN bajarilmadi.** Frontmatterda `requirements: [CAM-01, CAM-03, CAM-08]` bor, lekin bu reja ularning birortasini ham **yakunlamaydi**: CAM-01 va CAM-03 ning ekranlari 03-09/03-10 da. 03-01, 03-03…03-07 ham shu sababdan belgilamagan; belgilash `03-11` ning zimmasida.

---

**Total deviations:** 8 auto-fixed (1 × Rule 1, 3 × Rule 2, 4 × Rule 3) + 6 ta rejadagi ziddiyat + 2 ta hujjatlashtirilgan chetlanish
**Impact on plan:** Scope creep yo'q. Uchala Rule 2 tuzatishi ham **qoidaning jimgina buzilish yo'lini** yopdi (D-11, D-02, «cheksiz poll yo'q»); Rule 3 tuzatishlari rejaning o'z maqsadini bajarilishi mumkin holga keltirdi.

## Issues Encountered

1. **`docker cp` yo'li ishlamadi** — go2rtc statik fayllarni binar ichida (Go `embed`) olib yuradi. Reja ikkita «ekvivalent» yo'l bergan edi va **ikkinchisi rejadagi shaklda mavjud emas**; konteynerning HTTP yuzasidan olish bilan almashtirildi va bu versiya kafolatini buzmaydi (image tegi). Bu **runtime'da yuklash EMAS** — fayl bir marta olinib repozitoriyaga commit qilindi.
2. **React Compiler qoidalari rejadagi poll shaklini rad etdi** (`react-hooks/refs`, `react-hooks/purity`). Bu foydali bo'lib chiqdi: majburiy qayta loyihalash chegarani klient taymeridan **server vaqtiga** ko'chirdi va u sahifa yangilanishidan omon o'tadigan holga keldi.
3. **`vitest.config.ts` ning `include` naqshi `.ts` test faylini JIMGINA tashlab ketadi.** Fayl `.test.tsx` ga ko'chirilmaganda 15 ta test hech qachon ishga tushmasdi va «106 test yashil» degan hisobot **yolg'on** bo'lardi. Bu sinf — «darvoza bo'sh to'plamni skanerlaydi» ning aynan o'zi, faqat konfiguratsiya darajasida.
4. **Grep-ziddiyat sinfi bu rejada UCHRAMADI va bu tasodif emas:** G-4 va G-6 ning ikkalasi ham skanerlanadigan daraxtdan **tashqarida** yashaydi (`frontend/scripts/` vs `frontend/src/`), G-4 esa buyruq fe'lini o'zakdan **ochiq ajratadi**. Ikkala chegara ham test izohida yozilgan — bu fazada besh marta takrorlangan xatoning oldi ataylab olindi.

## Known Stubs

| Joy | Stub | Nega bu fazada yetarli | Kim yopadi |
|---|---|---|---|
| `activation-panel.tsx` — kamera qatorining qiymati | `—` (qattiq) | Backend `setup-status.cameras` ni **har doim `0`** qaytaradi. `—` «hali o'lchanmagan» degan **halol** qiymat; `0 ta` esa kameralar ulangandan keyin ham turadigan yolg'on dalil bo'lardi (UI-SPEC §3.4 U-3 ikkalasiga ham ruxsat beradi) | 03-11 yoki 4-faza: `markets.py::_setup_status_response` da `cameras=0` -> haqiqiy sanoq; frontend tomonda **bitta qator** (`value: count(status.cameras)`) |

Boshqa stub yo'q: `nvr-errors.ts`, `camera-queries.ts` va `use-nvr-auth-lock.ts` ning har bir eksporti to'liq ishlaydi va birlik testi bilan qamralgan. Ular hali **iste'mol qilinmaydi** (yuzalar 03-09/03-10 da) — bu stub emas, **to'lqin tartibi**: reja ataylab «bironta ekran chizmaydi».

## Threat Flags

Yangi ishonch chegarasi **ochilmadi**. Reja `<threat_model>` idagi **to'qqizala** band bajarildi:

| Threat | Holat |
|---|---|
| T-03-55 (vendored kodning almashtirilishi) | ✅ SHA-256 **ikki** faylda; **sabotaj S5** boshqa darvozalarning hech biri buni ko'rmasligini o'lchadi; manba `v1.9.14` tegi va u **ikki mustaqil yo'ldan** tasdiqlandi; to'liq ko'rik §14.2 jadvalida |
| T-03-56 (`/api/streams` frontendga kirishi) | ✅ G-6 `frontend/src` ni skanerlaydi (**0** hodisa); darvozaning o'zi `scripts/` da va o'z satrini topmaydi — chegara test izohida |
| T-03-57 (parolning keshga tushishi) | ✅ Uchala chaqiruv `useMutation`: `useCreateNvr`, `useTestConnection`, `useUpdateNvrPassword`. `useQuery` ga parol **hech qayerda** uzatilmaydi |
| T-03-58 (doiralanmagan kesh kaliti) | ✅ `domainKey` **import qilinadi**; global kalit konstantasi **0** (`grep -cE "^export const [A-Za-z]+Key = \["` = 0); **sabotaj S2/S2b** chegarani o'lchadi va tip tizimi yolg'iz yetarli emasligini ko'rsatdi |
| T-03-59 (auth qulfining unutilishi) | ✅ Qoida `useNvrAuthLock()` **hook darajasida**; `AUTH_LOCKING_CODES` jadvaldan **hosil** bo'ladi; 7 birlik testi, shu jumladan ikkala shart va fail-closed |
| T-03-60 (cheksiz poll) | ✅ **Uch** chegara (terminal, `started_at`, yiqilishlar); `refetchIntervalInBackground: false`; har biri alohida test |
| T-03-61 (D-02 ning jimgina buzilishi) | ✅ G-1 uchala tilda; quyi chegara (12 kod); **sabotaj S3b** parity darvozasi buni **ko'rmasligini** isbotladi |
| T-03-62 (D-10 ning tarjima orqali buzilishi) | ✅ G-4 132 satrni skanerlaydi; chegarasi ijobiy **va** salbiy nazorat testi bilan qulflangan |
| T-03-SC (npm o'rnatishlari) | ✅ `package-lock.json` va `dependencies` diffi **bo'sh**; vendored artefakt npm'dan emas va u git'da ko'rinadi |

⚠ **03-10 uchun ikkita majburiy sozlama (vendored pleyer ko'rigidan):**

1. `VideoRTC.pcConfig` standart holda **tashqi STUN** serverlariga (`stun.cloudflare.com`, `stun.l.google.com`) murojaat qiladi. Bu kod bajarish xavfi emas, lekin bozor tarmog'idan tashqariga chiqadigan **ko'rinmas bog'liqlik**. `live-player.tsx` `pcConfig` ni **o'zi belgilaydi**.
2. `VideoRTC.media` standarti `"video,audio"`. Oqim **ovozsiz** (§12.4) — `media = "video"` qilinadi, aks holda NVR ning bitreyt byudjeti bekorga yeyiladi.

## Next Phase Readiness

**03-09 / 03-10 (yuzalar) uchun TAYYOR:**

- `nvrErrorView(code)` -> `{causeKey, fixKey, tone, retrySafe, authLocking}`; `pickErrorDetail()` va `rawDetailText()` (2000 belgi chegarasi bilan).
- `useNvrAuthLock()` -> `{authLocked, lockedCode, unlockAt, lock, unlockOnCredentialChange, reset}`. **Forma `unlockOnCredentialChange()` ni faqat `useWatch` QIYMATI o'zgarganda chaqirishi shart** — `onFocus`/`onBlur` dan chaqirish qoidani buzadi.
- `camera-queries.ts`: 9 hook + `discoveryPollInterval` + oltita konstanta. `CameraFilters` — `nuqs` uchun uchala maydon ham `string`.
- 132 matn kaliti uch tilda; xato bloki uchun `errorCauseLabel`/`errorFixLabel`/`errorDetails` ham bor.
- Vendored pleyer `/vendor/go2rtc/video-stream.js` yo'lida (Next `public/`), `<script type="module">` bilan yuklanadi.

**03-09 / 03-10 uchun OCHIQ bandlar:**

1. **Manzil validatsiyasi (§4.7) hali yo'q** — ommaviy IP bloki, port oralig'i, `zod` sxemasi. U **forma** qatlamiga tegishli va shu rejaning yuzasida emas edi. Server darvozasi bor (`assert_private_host`, 03-04), ya'ni bu **qulaylik**, xavfsizlik chegarasi emas.
2. **`errors.loadFailedTitle` / `errors.loadFailedBody` kalitlari YO'Q.** UI-SPEC §10.3 ularni «meros blok» deb ataydi, lekin `errors` namespace'ida ular hech qachon yaratilmagan (hozir faqat `generic`/`network`/`forbidden`/`notFound`/`required`). 03-10 ularni qo'shishi yoki mavjud kalitlardan foydalanishi kerak.
3. **`discoveryConflictSchema` (409 -> `run_id`) yozildi, lekin CHAQIRUVCHI yo'q.** `useStartDiscovery` ning `onError` ida uni ochish 03-10 ning ishi (UI-SPEC §5.6: 409 **xato emas**).
4. **`Go2rtcClient.remove_stream` hamon mahsulot yo'lida chaqirilmaydi** (03-07 dan meros) — arxivlash oqimini go2rtc bilan sinxronlash ochiq.

**03-11 (yakuniy darvoza) uchun ochiq bandlar:**

1. `audit-volume` remediatsiyasi (03-04/03-06/03-07 dan meros).
2. `npm run test:sim:slow` fazani yopishdan oldin bir marta.
3. **`npm run gate` vaqti — 611 s** (03-07: 932 s). 03-01 ning 618 s nomzod chegarasi **birinchi marta buzilmadi**, lekin sabab bu reja emas: 932 s ga `alexxit/go2rtc:1.9.14` image'ining birinchi tortilishi kirgan edi. Chegarani qayta o'lchashda **sovuq va issiq yugurish ajratilsin**.
4. `setup-status.cameras` ning haqiqiy sanog'i (yuqoridagi «Known Stubs»).
5. `requirements mark-complete` — CAM-01…CAM-08 shu yerda belgilanadi.

## Self-Check: PASSED

- **Fayllar:** 29/29 mavjud (13 yangi + 16 o'zgargan)
- **Commitlar:** 3/3 mavjud (`a1f0ed2`, `2507cae`, `a163a44`)
- **`must_haves.artifacts` `contains`:** 5/5 — `authLocking` (`nvr-errors.ts`), `domainKey` (`camera-queries.ts`), `errorCause` (`nvr-copy.test.mjs`), `sha256` (`vendor-integrity.test.mjs`), `NVR` (`uz-Cyrl.overrides.json`)
- **`must_haves.key_links`:** 3/3 — `domainKey` (`camera-queries.ts` -> `market-queries.ts`), `NVR_ERROR_CODES` (`error-codes.test.mjs` -> `isapi/errors.py`), `cameras` (`app-shell.tsx` -> `/cameras`)
- **Global kalit konstantasi:** `grep -cE "^export const [A-Za-z]+Key = \["` = **0**
- **go2rtc yuzasi:** `grep -rnE "/api/streams|exec:|ffmpeg:" frontend/src` = **0**
- **Vendored xeshlar:** `sha256sum -c` -> ikkala fayl **OK**
- **Ish daraxti:** oltala sabotajdan keyin ham **toza**

---
*Phase: 03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi*
*Completed: 2026-08-03*
