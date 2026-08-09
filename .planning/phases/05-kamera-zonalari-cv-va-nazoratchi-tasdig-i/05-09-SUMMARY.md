---
phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
plan: 09
subsystem: frontend
tags: [svg, a11y, roving-tabindex, wcag, react-query, market-scoping, i18n, ai-01, d-05, d-22]

requires:
  - phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i
    provides: "`camera_zones` API va uning `frame_width`/`frame_height` OGOHLANTIRISHI (05-06); `zone-geometry.ts` ning 11 sof funksiyasi va HAVOLA kontrakti (05-03); `zone-errors.ts` reyestri, `cameraZones.*` namespace'i va G-15/G-16 copy darvozalari (05-04)"
  - phase: 04-snapshot-pipeline
    provides: "`GET /snapshots/{id}/image` proxysi va uning bayt-olish naqshi; `GET /capture-runs?day=` (kadr identifikatorining YAGONA manbai); `capture-grid.tsx` ning roving tabindex naqshi; `day-picker.tsx::businessDayIn`/`shiftIsoDay`"
  - phase: 02-bozor-domeni-va-yangi-bozor-ustasi
    provides: "`domainKey` fabrikasi va global kalitlarning O'CHIRILGANI; `GET /stalls/map` (sahifalashsiz, `code_sort` tartibida); `stall-map.tsx` ning canvas rad etish o'lchovi"
provides:
  - "`lib/camera-zone-queries.ts` — `cameraZonesKey`/`zoneCoverageKey`/`cameraFrameKey`/`frameImageKey`, `useCameraZones`/`useZoneCoverage`/`useCameraFrame`/`useFrameImageHref`/`useReplaceCameraZones`; POLL YO'Q"
  - "`zoneEditorState()` — Z-1…Z-8 darvozasi SOF FUNKSIYA sifatida"
  - "`latestOkFrame()` — kadr tanlash qoidasi, serverning `latest_frame_size()` i bilan bir xil shart"
  - "`components/camera-zones/zone-canvas.tsx` — SVG yuzasi; `VIEW_WIDTH`/`viewHeight`/`pointsAttr`/`clientToNormalized`/`midpointOf` sof funksiyalari"
  - "`components/camera-zones/zone-list.tsx` — OCHIQLIKNING ASOSIY YUZASI; `nudgedPoint()` va `invalidZoneIds()`"
  - "`components/camera-zones/zone-editor.tsx` — qoralama holat, undo/redo (50), saqlash darvozasi, nisbat lentasi"
  - "`components/camera-zones/row-assist-dialog.tsx` — `rowTargets()` va `planRowSplit()` (interpolyator INJEKSIYA qilinadi)"
  - "`components/camera-zones/coverage-card.tsx` — D-22 uchligi, nolda ham render"
  - "`/cameras/{id}/zones` marshruti va `/cameras` dagi bitta amal + bitta karta"
  - "`cameraZones.*` matni uchala tilda (821 -> 879 kalit)"
affects: [05-12, 05-14, 05-15]

tech-stack:
  added: []
  patterns:
    - "SVG `viewBox` kengligi DOIMIY shartli birlik, balandligi faqat NISBATdan — `draft()` kichraytirgan ustunlar piksel geometriyasiga HECH QACHON aylanmaydi"
    - "Konteynerning `aspect-ratio` si kadrnikiga TENG qilinadi — letterbox yo'q, ya'ni `getBoundingClientRect()` to'g'ridan-to'g'ri normalangan koordinataga aylanadi"
    - "Roving tabindex FAOL elementi ICHKI HOLAT emas, proplardan HOSILA — kadr bilan ro'yxat fokusi struktura jihatidan ajrala olmaydi"
    - "Qirra o'rtasidagi ushlagich `insertMidpoint` DAN HOSILA (`midpointOf`) — formula takrorlanmaydi va rad etilgan amalda ushlagich UMUMAN chizilmaydi"
    - "Nudge qadami RENDER PIKSELIDA (`1/renderHeight`), normalangan doimiy qadamda emas; nol o'lchamda `null` (`1/0` tepani burchakka sakratardi)"
    - "`aria-invalid` `button` rolida YAROQSIZ — o'rniga `aria-describedby` xato blokiga"
    - "Himoya qatlami YETIB BO'LMAYDIGAN bo'lsa, u o'lchanmagan DA'VO: bog'liqlikni ARGUMENT qilib, testda sun'iy buzuq implementatsiya beriladi"
    - "`@/i18n/navigation` import zanjiri vitest ostida YECHILMAYDI — router-siz test fayllari bo'lgan modulda `routing` konfiguratsiyasi o'qiladi"

key-files:
  created:
    - frontend/src/lib/camera-zone-queries.ts
    - frontend/src/lib/camera-zone-queries.test.tsx
    - frontend/src/app/[locale]/(app)/cameras/[cameraId]/zones/page.tsx
    - frontend/src/components/camera-zones/zone-canvas.tsx
    - frontend/src/components/camera-zones/zone-canvas.test.tsx
    - frontend/src/components/camera-zones/zone-list.tsx
    - frontend/src/components/camera-zones/zone-list.test.tsx
    - frontend/src/components/camera-zones/zone-editor.tsx
    - frontend/src/components/camera-zones/zone-toolbar.tsx
    - frontend/src/components/camera-zones/zone-detail-dialog.tsx
    - frontend/src/components/camera-zones/row-assist-dialog.tsx
    - frontend/src/components/camera-zones/row-assist-dialog.test.tsx
    - frontend/src/components/camera-zones/coverage-card.tsx
    - frontend/src/components/camera-zones/coverage-card.test.tsx
  modified:
    - frontend/src/lib/api-types.ts
    - frontend/src/app/[locale]/(app)/cameras/page.tsx
    - frontend/src/components/cameras/camera-row.tsx
    - frontend/messages/uz-Latn.json
    - frontend/messages/ru.json
    - frontend/messages/uz-Cyrl.json

key-decisions:
  - "`viewBox` = `1000 × (1000·h/w)` — `frame_width`/`frame_height` FAQAT nisbat sifatida ishlatiladi; test 480×270 kadrda x=0,5 tepasi 500 da chizilishini va 240 da EMASLIGINI literal o'lchaydi"
  - "`denormalize()` muharrirda UMUMAN chaqirilmaydi: u KADR PIKSELLARI uchun va uning yaxlitlashi serverning `_round_half_up()` i bilan juftlashtirilgan; render birliklari boshqa masshtabda"
  - "Klient koordinatani QAYTA YAXLITLAMAYDI — ikkinchi yaxlitlash nuqtasi 05-06 ning S6 sinfini qaytarardi; yaxlitlash faqat serverda, aniqlash paytida"
  - "HAR ZONA UCHUN AYNAN BITTA `<polygon>`; §10.5 ning ikki qatlamli konturi `drop-shadow` bilan bajarildi, chunki ikkinchi element «poligon soni = zona soni» invariantini buzardi"
  - "Kadr yuzasining nisbati kadrnikiga tenglashtirildi (`aspect-video` letterbox O'RNIGA) — sudrash matematikasida qora chiziqlar uchun tuzatish kerak emas"
  - "«Bosib chizish» rejimi QURILMADI: §13.4 uni klaviatura foydalanuvchisiga taklif qilmaydi, ya'ni u ikkinchi (faqat sichqonchali) yaratish modeli bo'lardi; markazdagi to'rtburchak + qirra ushlagichi TO'LIQ yo'l"
  - "Rastasiz zona LOKAL QORALAMA: `CameraZoneWrite.stall_id` MAJBURIY, ya'ni uni yuborish yo'li YO'Q — saqlashdan keyin ham hisoblagich nolga tushmaydi va toast sonni aytadi"
  - "`camera-row.tsx` `@/i18n/navigation` ni IMPORT QILMAYDI — o'lchandi: import zanjiri vitest ostida yechilmaydi va TO'RTTA test fayli «0 test» bilan yiqiladi"
  - "`planRowSplit` interpolyatorni ARGUMENT sifatida oladi — S4 sabotaji `count-mismatch` tarmog'ining yetib bo'lmaydigan ekanini fosh qildi"

patterns-established:
  - "«Ikkinchi himoya qatlami» da'vosi SABOTAJ bilan tekshirilmasa, u ko'pincha YETIB BO'LMAYDIGAN kod bo'lib chiqadi — bog'liqlikni injeksiya qilish uni o'lchanadigan qiladi"
  - "Bola kesh kaliti ota kalitning BUZILISHINI ko'ra olmaydi (S6 da o'lchandi): u prefiksni meros olgani uchun xatoni ham meros oladi"
  - "Modul IMPORTINING o'zi test muhitida yiqilishi mumkin — bu render kontekstidan boshqa nosozlik sinfi va u faqat to'liq to'plamni yugurtirganda ko'rinadi"

requirements-completed: []
requirements-advanced: [AI-01]
# ⚠ ATAYIN BO'SH. Bu reja AI-01 ning CHIZISH YUZASINI yetkazadi va SC#1
# ning UI qismini yopadi, lekin talabni DALIL bilan yopish `05-15` ning
# ishi — 05-05 va 05-06 bilan aynan bir xil qaror. Sabab aniq: brauzerdagi
# 8 qadamli qo'lda tekshiruv bu worktree'da BAJARILMADI (pastga qarang).

duration: ~100 daqiqa
completed: 2026-08-09
---

# Phase 5 Plan 09: Zona muharriri — SVG yuzasi, ro'yxat birlamchi klaviatura yuzasi va qator yordamchisi Summary

**Poligon chizish yuzasi SVG bilan qurildi va ochiqlikning asosiy yuzasi kadr emas, RO'YXAT bo'ldi — 44 px tepa tugmalari, bitta tab to'xtashi va o'q tugmalari bilan piksel-aniq siljitish; `frame_width` ning piksel geometriyasiga aylanishi literal test bilan yopildi va yettita sabotajdan biri «ikkinchi himoya qatlami» degan da'voning yetib bo'lmaydigan kod ekanini fosh qildi.**

## Performance

- **Duration:** ~100 daqiqa
- **Tasks:** 3/3 (uchtasi ham commit qilindi) + bitta qo'shimcha qattiqlashtirish commiti
- **Files:** 14 yangi, 6 o'zgartirilgan — **rejaning `files_modified` ro'yxatidan tashqarida BIRORTA fayl yo'q**

## Task Commits

1. **Task 1: kesh kalitlari, sxemalar, qamrov kartasi** — `cae1314`
2. **Task 2: SVG yuzasi, ro'yxat yuzasi, muharrir qobig'i** — `1aa68be`
3. **Task 3: asboblar, DL-1, DL-2** — `e574e75`
4. **Sabotaj natijasi bo'yicha qattiqlashtirish** — `0bf11b5`

## Bajarilgan ishlar

### Task 1 — ma'lumot yo'li va qamrov yuzasi

`camera-zone-queries.ts`: `cameraZonesKey(marketId, cameraId)` va `zoneCoverageKey(marketId)` — ikkalasi ham `domainKey` orqali, **marketsiz kalit konstantasi umuman yo'q** (`grep -c 'domainKey("' …` → **0** ✅). Poll **yo'q** va bu test bilan qulflandi (`refetchInterval` sozlanmaganini o'qiydi).

`zoneEditorState()` — Z-1…Z-8 ning darvozasi **sof funksiya** sifatida: `xato -> yuklanmoqda -> kadr yo'q -> tayyor`. Tartib literal test bilan qulflangan, chunki xato pastga tushsa, yiqilgan so'rov «kadr yo'q» bo'lib ko'rinardi va admin nosozlikni kadr olish bo'limidan qidirardi.

`coverage-card.tsx`: uchala son **doim**, nol bo'lganda ham. `<dl>` semantikasi, `role="status"`, sariq tint `bg-warning/20 text-text`.

### Task 2 — SVG yuzasi va ro'yxat yuzasi

`zone-canvas.tsx` (432 qator, talab 120): har zona uchun **aynan bitta** `<polygon>`, konteyner `aria-hidden="true"`, tepada `setPointerCapture`, qirra o'rtasidagi ushlagich `insertMidpoint` **dan hosila**.

`zone-list.tsx`: har poligon `<li>`, tanlanganda tepalar ro'yxat bo'lib ochiladi, har tepa tugmasi **`min-h-11 min-w-11`**, butun ro'yxatda **aynan bitta** `tabIndex={0}`, `ArrowUp` **1/720**, `Shift+ArrowUp` **10/720**, uch tepada o'chirish `aria-disabled`.

`zone-editor.tsx`: qoralama holat, undo/redo (chuqurlik 50), kesishgan poligon saqlashni to'sadi, nisbat lentasi (**avtomatik to'g'rilash yo'q**), ichki navigatsiyada tasdiq.

### Task 3 — uchta yordamchi va ikkita dialog

`rowTargets()` — tartib **`GET /stalls/map`** ning `code_sort` idan; zonasi bor rasta chiqariladi va **sanaladi**. `planRowSplit()` — **yoki hammasi, yoki hech nima**; ikki rad etish sababi alohida nomlangan.

`zone-toolbar.tsx` — besh tugma, **hammasi `secondary`** (`.bg-accent` soni testda **0**), `aria-disabled` + og'zaki sabab.

`zone-detail-dialog.tsx` — rasta biriktirish + `Versiya N`. **«Tiklash» tugmasi yo'q** va `cameraZones.restore*` kaliti ham yo'q — ikkalasi ham test bilan qulflangan.

## Sabotaj o'lchovi — nima QIZARDI va NIMA YASHIL QOLDI

Har sabotaj snapshotdan `cp` bilan qaytarildi (`git checkout --` **ishlatilmadi**); oxirida `git status` toza.

| # | Sabotaj | Natija |
|---|---------|--------|
| **S1** | `viewHeight()` nisbat o'rniga **xom `frame_height`** ni qaytaradi | 🔴 **4 test** (`viewBox` shakli, `500 ≠ 240`, `denormalize` farqi, 4:3 nazorati)<br>⚠ Poligon sanog'i va `aria-hidden` **yashil qoldi** — va bu TO'G'RI: ular masshtabdan mustaqil invariantlar |
| **S2** | Roving tabindex o'chirildi (har tepa `tabIndex={0}`) | 🔴 **1 test** — «butun ro'yxatda aynan bitta to'xtash»<br>⚠ Qolgan 24 ta ro'yxat testi yashil: ular fokus **xulqini** o'lchaydi, tuzoqni emas |
| **S3** | Gorizontal nudge maxraji `renderWidth` o'rniga `renderHeight` | 🔴 **1 test** — «gorizontal qadam kenglikdan olinadi»<br>⚠ `ArrowUp` testlari yashil qoldi (ular vertikal o'qni o'lchaydi), ya'ni **fixture'da `1280 ≠ 720` bo'lishi majburiy** va bu test ichida assert bilan qulflangan |
| **S4** | `planRowSplit` dan `count-mismatch` tarmog'i **butunlay o'chirildi** | 🟢 **HAMMASI YASHIL (70/70)** → tuzatildi, keyin 🔴 1 test (pastda) |
| **S5** | Qamrov kartasi `uncovered === 0` da `null` qaytaradi (4-fazaning `coverage-warning` naqshi) | 🔴 **3 test** — nolda render, ijobiy xulosa, sabab jumlasining nazorati |
| **S6** | `cameraZonesKey` ni marketsiz qilish (`domainKey("camera-zones", cameraId)`) | ⚠ **`tsc --noEmit` TOZA QOLDI** — 04-02 ning o'lchovi qayta tasdiqlandi<br>🔴 **2 test** (kalit shakli va bozorlararo ajralish)<br>⚠ **`cameraFrameKey` testi YASHIL QOLDI** — bola kalit otasidan prefiks meros oladi, ya'ni xatoni ham meros oladi va uni KO'RA OLMAYDI |
| **S7** | Kadr konteyneridan `aria-hidden` olib tashlandi | 🔴 **2 test** (`aria-hidden` va konteyner nisbati — ikkinchisi selektor orqali bir xil elementni topadi) |

### S4 — bu rejaning eng qimmatli natijasi

`planRowSplit` da ikkita rad etish tarmog'i bor edi: `vertex-mismatch` va `count-mismatch`. Ikkinchisi «ikkinchi himoya qatlami» deb yozilgan edi — «geometriya funksiyasi bir kun boshqacha ishlasa, dialog jimgina noto'g'ri sonda zona qo'shmasin».

**Uni butunlay o'chirish hech nimani qizartirmadi.** Sabab strukturaviy: bugungi `interpolateRow` kontrakti ostida u **yetib bo'lmaydigan** tarmoq — tepa soni teng bo'lmagan holat bir qator yuqorida ushlanadi, qolgan har qanday kirishda esa funksiya **aynan `n` ta** poligon qaytaradi.

Ya'ni himoya qatlami **hech qachon bajarilmaydigan kod** edi va uning «bor» ekani faqat *da'vo* bo'lardi. Bu 05-06 ning S4 darsining aynan boshqa shakli: u yerda test trivial qanoatlanardi, bu yerda esa **kodning o'zi** hech qachon bajarilmasdi.

**Tuzatish:** `planRowSplit` interpolyatorni **argument** sifatida oladi (standart qiymat — `interpolateRow`). Test ataylab kam poligon qaytaradigan funksiya beradi va himoya haqiqatan ishlashini o'lchaydi. Sabotaj takrorlanganda **endi qizaradi** (`0bf11b5`).

### S6 — nima uchun kalit shakli testi YETARLI EMAS EDI, va endi ham to'liq emas

`tsc` toza qoldi (kutilgan), lekin qimmatliroq natija boshqa: **`cameraFrameKey` testi yashil qoldi**. U ota kalitning prefiksini tekshiradi, prefiks esa buzilgan otadan kelgani uchun **ichki jihatdan izchil** bo'lib qoladi. Ya'ni bola kalitlar hech qachon ota kalitning doiralanishini himoya qila olmaydi — himoya faqat **otaning o'z** literal testida yashaydi.

## Deviations from Plan

### 1. `[Rule 3 - Bloklovchi]` `frontend/node_modules` worktree'da yo'q edi

`npm ci` bilan **lockfile'dan** tiklandi (yangi paket qo'shilmadi; `package.json`/`package-lock.json` diff'da yo'q). 05-03 va 05-04 da ham aynan shu holat bo'lgan.

### 2. `[Rule 1 - O'lchangan ziddiyat]` `camera-row.tsx` `@/i18n/navigation` ni import qila olmaydi

- **Topildi:** Task 1, `Link`/`getPathname` qo'shilgandan keyin **to'liq to'plamni** yugurtirganda
- **Muammo:** `@/i18n/navigation` → `next-intl/navigation` → `next/navigation` zanjiri **vitest ostida yechilmaydi**:
  `Cannot find module '…/node_modules/next/navigation'`. Ya'ni nosozlik render paytidagi router konteksti emas, **modulni import qilishning o'zi**.
- **Qamrovi kutilganidan keng edi:** `camera-row.tsx` yana **uchta** test faylining import grafida (`capture-grid`, `snapshot-dialog`, `live-view-dialog` — ular `channelLabel` ni oladi). O'lchov: **to'rtala fayl ham «0 test» bilan yiqildi, 27 test yo'qoldi**.
- **Tuzatish:** navigatsiya moduli o'rniga uning **yagona manbai** — `routing` konfiguratsiyasi — o'qiladi va prefiks undan olinadi (`localeHref`). Prefiks xaritasi **nusxa ko'chirilmadi**.
- **Narxi halol aytilgan:** oddiy `<a>` to'liq sahifa yuklashini beradi. Zona muharriri kunlik amal emas (bir martalik sozlash), lekin `camera-row.test.tsx` ni o'z fayl to'plamiga oladigan keyingi reja modulni mock qilib, bu yerni `Link` ga o'tkazishi kerak.
- **Commit:** `cae1314`

### 3. `[Ongli chegirma]` Kamera qatoridagi **zona soni badge'i qurilmadi**

§5.5 uni so'raydi. U kamera-boshiga alohida so'rov talab qiladi (agregat marshrut yo'q), fan-out qilinadigan yagona joy — `camera-list.tsx` — bu rejaning fayl to'plamidan **tashqarida**, `CameraRow` ning o'ziga so'rov qo'yish esa `camera-row.test.tsx` ni (u ham to'plamdan tashqarida, `QueryClientProvider` siz render qiladi) yiqitardi. **Qatorga bitta amal qo'shildi**, badge esa ochiq band sifatida qayd etildi. To'g'ri yechim — `GET /cameras` javobiga zona sonini qo'shish, N+1 emas.

### 4. `[Rule 3 - Bloklovchi]` Javobda kadr IDENTIFIKATORI yo'q

- **Muammo:** `GET /camera-zones` `frame_width`/`frame_height` beradi, lekin **qaysi kadr** ekanini aytmaydi; rasm esa `GET /snapshots/{id}/image` dan keladi.
- **Tuzatish:** klient `GET /capture-runs?day=` dan **bugun, topilmasa kecha** kadr izlaydi (`latestOkFrame`, serverning `latest_frame_size()` i bilan **bir xil shart**: faqat `quality_verdict = 'ok'`, eng so'nggisi). Topilgan kadrning **vaqti ekranda** (`cameraZones.frameAt`), ya'ni admin qaysi kadr ustida chizayotganini ko'radi.
- **Qoldiq xavf ochiq aytiladi:** nisbat lentasi server ko'rgan kadrga tegishli bo'lib, ekranda boshqa kadr turishi mumkin. U **ogohlantirish**, hisob emas. To'g'ri yechim — javobga `frame_snapshot_id` (bitta maydon).
- **Commit:** `1aa68be`

### 5. `[Rule 1 - Spek ziddiyati]` Rastasiz zona SAQLANA OLMAYDI

- **Muammo:** §6.3 «rastasiz zona **saqlanadi**» deydi. Server kontrakti buni imkonsiz qiladi: `CameraZoneWrite.stall_id` — **majburiy** `UUID` (05-06 `schemas.py`).
- **Tuzatish:** bunday zona muharrirda **qoladi**, `PUT` tanasiga **tushmaydi**, saqlashdan keyin ham «saqlanmagan» hisoblanadi — **hisoblagich nolga tushmaydi**. Toast sonni aytadi (`noStallWarning`).
- **Nega bu to'g'ri:** muqobil — uni jimgina tashlab yuborish — «saqlandi» toasti bilan birga kelgan ma'lumot yo'qotishining eng yomon shakli bo'lardi.
- **Commit:** `1aa68be`

### 6. `[Rule 1 - Yaroqsiz ARIA]` `aria-invalid` `button` rolida qo'llab-quvvatlanmaydi

§6.6 uni ko'rsatadi, `jsx-a11y/role-supports-aria-props` esa ogohlantirish bilan fosh qildi. **Yaroqsiz ARIA — «bor, lekin ishlamaydigan» himoya:** ko'rikda to'g'ri ko'rinardi, skrinrider esa uni umuman e'lon qilmasdi. O'rniga **`aria-describedby`** xato blokiga — fokus ayblanuvchi zonaga tushganda sabab o'qiladi. **Commit:** `1aa68be`

### 7. `[Qaror]` Har zona uchun BITTA `<polygon>`

§10.5 ikki qatlamli kontur (qora ostida, oq ustida) taklif qiladi. Ikkinchi element **«poligon soni = zona soni»** invariantini buzardi va o'sha invariant «bir zona jimgina chizilmay qoldi» sinfini ushlaydigan yagona arzon test. Vizual natija `drop-shadow` bilan olindi — bitta element, ikki qatlam. **Commit:** `1aa68be`

### 8. `[Qaror]` Konteyner nisbati kadrnikiga tenglashtirildi

§6.3 `aspect-video` letterbox eskizini beradi. Qat'iy 16:9 konteynerda 4:3 kadr letterbox olardi va **har `pointermove` da** o'sha bo'shliqni hisobdan chiqarish kerak bo'lardi — jimgina siljish uchun ideal joy. Nisbatlar teng bo'lganda `getBoundingClientRect()` to'g'ridan-to'g'ri normalangan koordinataga aylanadi.

### 9. `[Qaror]` «Bosib chizish» rejimi qurilmadi

§6.4 uni sanaydi, §13.4 esa uni **klaviatura foydalanuvchisiga taklif qilmaydi** — ya'ni u ikkinchi, faqat sichqonchali yaratish modeli bo'lardi (o'z rejimi, yopish/bekor qilish semantikasi, `Esc` xulqi). Majburiy yo'l — **markazdagi to'rtburchak** — va u to'liq: rasta amalda to'rtburchak (§6.5), boshqa shakl qirra o'rtasidagi ushlagich bilan quriladi. ⚠ Qo'lda tekshiruvning **2-qadami shunga muvofiq o'zgaradi**.

### 10. `[Qaror]` «Oldingi versiyalar» ro'yxati qurilmadi

§6.6 `<details>` ichida «sana + kim» ni ko'rsatadi. Server **faqat faol** zonalarni qaytaradi; eskirgan qatorlar jadvalda qoladi, lekin ular uchun marshrut **yo'q**. Bo'sh `<details>` «tarix yo'q» degan **yolg'on** xabar berardi.

### 11. `[Rule 2 - O'lchangan bo'shliq]` `planRowSplit` interpolyatorni injeksiya qiladi

S4 sabotaji bilan o'lchandi — yuqoridagi bo'limga qarang. **Commit:** `0bf11b5`

### 12. `[Tartib]` Muharrir sahifasi Task 1 dan Task 2 ga ko'chdi

`page.tsx` `ZoneEditor` ni import qiladi, ya'ni u Task 1 ning commitida **kompilyatsiya qilinmasdi**. Task 1 ning «kadrsiz muharrir ochilmaydi» qabul mezoni buzilmadi: qaror `zoneEditorState()` sof funksiyasiga ko'chirildi va Task 1 da **literal test bilan** qulflandi; render qilingan E-1 esa Task 2 da.

### 13. `[Tartib]` Task 2 ning copy kalitlari Task 2 commitida

Reja copy'ni Task 1 va Task 3 ga bo'ladi, lekin `zone-list.tsx`/`zone-editor.tsx` o'z matnisiz kompilyatsiya qilinmasdi. Har commit **o'z-o'zicha yashil** bo'lishi ustun qo'yildi.

### 14. `[Aniqlik]` Qabul mezonining so'z shakli

Mezon: «`cameraZonesKey("m1","c1")` birinchi elementi `"m1"`». `domainKey` ning haqiqiy shakli — `["m", marketId, …]`, ya'ni **birinchi element `"m"`, ikkinchisi bozor identifikatori**. Test ikkalasini ham literal qulflaydi; mezonning niyati (kalit tug'ilishidanoq doiralangan) to'liq bajarilgan.

### 15. `[Qaror]` `toastZoneDeleted` kaliti qo'shilmadi

Zona o'chirish **alohida `DELETE` so'rovi yubormaydi**: `PUT` — kameraning to'liq holati, ya'ni ro'yxatdan chiqarilgan zona saqlash paytida eskirtiriladi. «O'chirildi» toasti saqlashdan **oldin** chiqib, mavjud bo'lmagan natijani tasdiqlardi.

### 16. `[Checkpoint]` Task 3 ning qo'lda tekshiruvi BAJARILMADI

`config.json` da `workflow.human_verify_mode: "end-of-phase"`, ya'ni qo'lda tekshiruv faza oxiriga to'planadi. Bu worktree'da brauzer ham, ishlaydigan Docker steki ham yo'q. **Ish bajarildi va avtomatik verifikatsiyadan o'tdi; 8 qadamli qo'lda tekshiruv esa faza yopilishiga qoldirildi** — pastdagi ro'yxatga qarang.

---

**Total deviations:** 16 (1× Rule 3 muhit, 2× Rule 3 kontrakt bo'shlig'i, 3× Rule 1 spek/ARIA ziddiyati, 1× Rule 2 o'lchangan bo'shliq, 6× ongli qaror, 3× tartib/aniqlik)
**Impact on plan:** Ko'lam kengaymadi. Uchta qaror (3, 9 va 10-bandlar) spek so'ragan narsani **qurmaslik** haqida va uchalasining sababi kontrakt yoki fayl chegarasi — taxmin emas.

## Verification

| O'lchov | Bazaviy | Yakuniy | Holat |
|---|---|---|---|
| `vitest run` | 399 (30 fayl) | **494 (35 fayl)** | ✅ +95 |
| `node --test scripts/*.test.mjs` | 144 | **144** | ✅ o'zgarmadi (G-11/G-15/G-16/G-18 yashil) |
| `npm run i18n:check` | 821 × 3 | **879 × 3** | ✅ +58, kalit va ICU parity to'liq |
| `npm run typecheck` | toza | **toza** | ✅ |
| `npm run lint` | toza | **toza** | ✅ 0 xato, 0 ogohlantirish |
| `npm run build` | — | **✓ Compiled** | ✅ `/[locale]/cameras/[cameraId]/zones` dinamik marshrut sifatida ro'yxatda |
| `grep -c 'domainKey("' camera-zone-queries.ts` | — | **0** | ✅ |
| `grep -rE "\.toDataURL\(\|beforeunload" components/camera-zones/` | — | **0** | ✅ |
| `app-shell.tsx` / `rbac.ts` / `uz-Cyrl.overrides.json` diff'da | — | **YO'Q** | ✅ |

⚠ **`pytest` va `tests/tenancy` QAYTA YUGURTIRILMADI** va bu ataylab: bu reja **birorta Python faylini o'zgartirmagan** (`git diff --name-only` chiqishida `services/` ham, `tests/` ham yo'q), ya'ni 2032/506 bazaviy sonlariga strukturaviy ta'sir yo'q. Ularni bu worktree'dan yugurtirish DB va ombor stekini talab qiladi va 05-04 SUMMARY da hujjatlashtirilgan `sbozor-storage-1` muammosini qaytarardi — undan tashqari, `05-08` ayni paytda backend fayllarida parallel ishlayapti.

## Qabul mezonlari

**Task 1:** kalit literal testi ✅ · marketsiz konstanta yo'q (grep 0) ✅ · qamrov kartasi nolda render ✅ · `zone-copy.test.mjs` yashil ✅ · kadrsiz muharrir ochilmaydi (sof funksiya + E-1 renderi) ✅ · `app-shell.tsx` diff'da yo'q ✅

**Task 2:** poligon soni = zona soni ✅ · `aria-hidden="true"` ✅ · `setPointerCapture` ✅ · har poligon `<li>` ✅ · tanlanganda tepalar ochiladi ✅ · `ArrowUp` 1 px / `Shift` 10 px ✅ · 3 tepada `aria-disabled` ✅ · bitta `tabIndex={0}` ✅ · `[role=grid|tree|gridcell|treeitem|row]` **hech nima topmaydi** ✅ · taqiqlangan chaqiruvlar grep 0 ✅ · kesishgan poligon saqlashni to'sadi, sabab `role="alert"` da ✅ · vitest ≥ 338 (**494**) ✅

**Task 3:** rasta soni ≠ poligon soni → hech nima qo'shilmaydi ✅ · tepa soni teng bo'lmasa dialog xato ko'rsatadi ✅ · `cameraZones.restore*` kaliti yo'q **va** render qilingan DL-1 da qaytarish tugmasi topilmaydi ✅ · asboblarda `.bg-accent` **0** ✅ · `i18n:check` yashil, `uz-Cyrl.overrides.json` o'zgarmagan ✅

## ⚠ O'LCHANMAGAN: D-05 ning chiqish yo'li (§16.4 O-04)

**`pointermove` narxi 50+ poligonli kamerada O'LCHANMADI** va uni o'lchash uchun brauzer kerak — bu worktree'da u yo'q. Bu **UAT bandi, darvoza emas** va shunday qoladi.

Bilinadigan **strukturaviy** fakt esa yozib qo'yiladi: sudrash har `pointermove` da `zones` massivini yangilaydi, ya'ni **barcha** poligonlar qayta render bo'ladi. 2-fazaning ~4 ms o'lchovi **statik** render uchun edi va bu profilga to'g'ridan-to'g'ri ko'chmaydi.

**O'lchash tartibi (faza yopilishida):** 60 poligonli kamerani oching, DevTools Performance panelida tepani sudrang, `pointermove` ishlovchisining 100 harakat bo'yicha o'rtachasini yozing. **>16 ms bo'lsa** — birinchi arzon chora: tanlanmagan poligonlarni memoizatsiya qilish (ular sudrash paytida **o'zgarmaydi**); u yetmasa `zone-canvas.tsx` Konva'ga almashtiriladi va **boshqa hech qanday fayl o'zgarmaydi**.

## ⚠ BAJARILMAGAN QO'LDA TEKSHIRUV (faza yopilishiga)

`human_verify_mode: "end-of-phase"`. Quyidagilar **bajarilmadi** va faza yopilishida bajarilishi kerak:

1. `/uz/cameras/<kameraId>/zones` ochiladi (bozor tanlangan holda)
2. ⚠ **Reja matnidan farq qiladi (deviatsiya 9):** `[+ Yangi zona]` kadr **markazida to'rtburchak** yaratadi (nuqta qo'yish rejimi yo'q). Zona ro'yxatda paydo bo'ladimi?
3. Tepani sudrang; keyin **faqat klaviatura bilan**: `Tab` → ro'yxat, `ArrowUp` va `Shift+ArrowUp`
4. Ikki zonani ketma-ket tanlab `[Qator bo'yicha bo'lish]`: oldindan ko'rishdagi poligonlar soni oradagi rastalar soniga tengmi? `[Bo'lish]` dan keyin ular **saqlanmagan** holatda turibdimi?
5. Poligonni ataylab kesishtiring va `[Saqlash]` ni bosing — saqlash to'xtadimi va sabab ko'rinyaptimi?
6. Sahifada aksent fonli tugma **nechta**? (Kutilgan: 1)
7. Versiya tarixida qaytarish tugmasi **bormi**? (Kutilgan: yo'q)
8. **O'lchov:** yuqoridagi `pointermove` bandi

## Decisions Made

Yuqoridagi `key-decisions` ga qarang. Eng ta'sirlilari:

1. **`frame_width` NISBAT, piksel emas.** 05-06 ning ogohlantirishi literal test bilan yopildi: 480×270 kadrda x=0,5 tepasi **500** da chiziladi, **240** da emas. Bu «jimgina to'rt barobar xato» sinfini butunlay yopadi.
2. **Ochiqlik ro'yxatda, SVG esa uning ko'zgusi.** Bu bezak emas: kadr ustiga bosish klaviatura bilan bajarilmaydi, ya'ni chizish faqat sichqoncha bilan bo'lsa, klaviatura foydalanuvchisi ekrandan **butunlay** chiqarib tashlanardi.
3. **Klient koordinatani yaxlitlamaydi.** Yaxlitlash faqat serverda, aniqlash paytida. Ikkinchi yaxlitlash nuqtasi 05-06 ning S6 sinfini — ikki tomonning bir kun ajralib ketishini — qaytarardi.
4. **Yetib bo'lmaydigan himoya — himoya emas.** S4 buni o'lchadi va tuzatish bog'liqlikni **argument** qilish bo'ldi.

## Known Stubs

Yo'q. Barcha komponentlar to'liq ishlaydi; hardkod bo'sh qiymat, placeholder matn yoki «keyinroq to'ldiriladi» holati qoldirilmadi. **Qurilmagan uchta narsa stub EMAS, ular ongli qarorlar** va sababi kodda yozilgan: kamera qatoridagi zona soni badge'i (deviatsiya 3), «oldingi versiyalar» ro'yxati (10) va «bosib chizish» rejimi (9). Birortasi ham bo'sh element yoki ishlamaydigan tugma qoldirmaydi.

## Threat Flags

Rejalashtirilmagan yangi xavfsizlik yuzasi topilmadi. `<threat_model>` ning to'rttala bandi qoplandi:

| Threat | Qoplandi |
|---|---|
| T-05-39 (kadrni yuklab olish) | Rastr eksport yo'li qurilmadi; `grep -rE "\.toDataURL\(\|beforeunload" components/camera-zones/` → **0**; kadr faqat `core-api` proxysi orqali, `crossOrigin` **qo'yilmagan** (test bilan) |
| T-05-40 (klient chegarasini chetlab o'tish) | `MAX_ZONES_PER_CAMERA`/`MAX_VERTICES_PER_ZONE` serverda majburlanadi (05-06); klientdagisi qulaylik va bu izohlarda yozilgan |
| T-05-41 (240 fokuslanadigan element) | Roving tabindex — **bitta** tab to'xtashi, literal test; S2 bilan o'lchandi |
| T-05-42 (aylanma mantiq) | Bunday funksiya **umuman qurilmadi**; sabab `zone-toolbar.tsx` va `row-assist-dialog.tsx` ning izohlarida |

## Keyingi rejalar uchun ochiq bandlar

- **⚠ `frame_snapshot_id` javobga qo'shilsin** (05-06 ning `CameraZoneListResponse` iga bitta maydon). Shunda nisbat ham, ekrandagi rasm ham **aynan bir** kadrdan bo'ladi va klientdagi ikki so'rovli qidiruv (`useCameraFrame`) olib tashlanadi.
- **⚠ Rastasiz zonani saqlash yo'li yo'q** (deviatsiya 5). Agar mahsulot uni haqiqatan talab qilsa, `stall_id` ni `nullable` qilish **server qarori** va u qamrov hisobiga ta'sir qiladi.
- **⚠ Zona versiyalari tarixi uchun marshrut yo'q** — DL-1 dagi `<details>` shu marshrut paydo bo'lgan kuni qo'shiladi.
- **`camera-row.test.tsx` ni oladigan reja** `@/i18n/navigation` ni mock qilib, `localeHref` ni `Link` ga o'tkazsin (deviatsiya 2).
- **`GET /cameras` javobiga zona soni** — kamera qatoridagi badge uchun yagona N+1 siz yo'l (deviatsiya 3).
- **05-12 (kun yopilishi)** `zoneCoverageKey` keshini bekor qilishi kerak bo'lsa, u `["m", marketId, "zone-coverage"]` prefiksida.
- **05-15 (faza yopilishi)** yuqoridagi 8 qadamli qo'lda tekshiruvni va `pointermove` o'lchovini bajarsin; AI-01 shu dalil bilan yopiladi.

## User Setup Required

None — tashqi servis sozlamasi talab qilinmaydi.

## Self-Check: PASSED

- **Fayllar:** 20/20 diskda mavjud (`git diff --name-only 064d20c..HEAD` bilan tasdiqlandi) va **hammasi rejaning `files_modified` ro'yxatida**
- **Commitlar:** `cae1314`, `1aa68be`, `e574e75`, `0bf11b5` — to'rttasi ham `git log` da
- **O'chirilgan fayl yo'q:** har commitdan keyin `git diff --diff-filter=D` **bo'sh**
- **Sabotajlar:** 7/7 o'lchandi va `cp` bilan qaytarildi; `git checkout --` **ishlatilmadi**; oxirgi to'liq ijro **494 vitest + 144 node** yashil
- **Tegilmagan fayllar tasdig'i:** `frontend/src/components/shell/app-shell.tsx`, `frontend/src/lib/rbac.ts`, `frontend/messages/uz-Cyrl.overrides.json`, `frontend/package.json`, `frontend/package-lock.json`, `.planning/STATE.md`, `.planning/ROADMAP.md` — **birortasi ham diff'da yo'q**

---
*Phase: 05-kamera-zonalari-cv-va-nazoratchi-tasdig-i*
*Completed: 2026-08-09*
