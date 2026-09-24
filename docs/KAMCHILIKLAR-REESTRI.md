# SBOZOR — Kamchiliklar reestri va ijro rejasi

> **Manba:** 2026-08-14/15 to'liq 4-rol brauzer testi (TEST-REPORT.md) + kod-review.
> **Qoida:** limit tiklangach shu reestr yuqoridan pastga yopiladi. Band yopilganda commit hash yoziladi.
> **Holat belgilari:** ⬜ ochiq · ✅ yopiq · 🔒 tashqi shartga bog'liq

## 0. ALLAQACHON YOPILGAN (2026-08-14/15 sessiyalarida)

| № | Kamchilik | Commit |
|---|---|---|
| ✅ №7 | Sessiya uzilishi (change-password yangi sessiya bermasdi) | `9cf8a66` |
| ✅ №8 | Kassir Enter — kod sog'lom, 8-holatli regressiya darvozasi qo'shildi | `8ee8e2e`, `e3e0cf4` |
| ✅ №6 | Jadval dialogi bo'sh holatda abadiy "Yuklanmoqda" | `c411636` |
| ✅ №4 | Rolsiz saqlash jim no-op (+yashirin 2-qatlam) | `d059a7d` |
| ✅ №2 | Usta Rastalar qadamida qo'lda qo'shish yo'q | `dc2ea27` |
| ✅ №A | Qoralama bozor tanlanganda usta 1-qadamiga qaytarardi (qo'nish qoidasining ikki nusxasi birlashtirildi) | `b90bb09` |
| ✅ №B | Bozorni "Qoralama"dan FAOL holatga o'tkazish yo'li (navigatsiya + tasdiq dialogi + billing zanjirining o'lchovi) | `9e52fd5`, `96171c1` |
| ✅ KR-jim | Kod-review: jim-disabled submit oilasi — stall/stall-category/tariff/camera-rename dialoglari + usta hafta-kunlari + G-SUBMIT mexanik darvozasi | `04a473b`, `486fdb1`, `0315196` |
| ✅ KR-tri | Kod-review: stall-dialog tri-state kolapsi + schedule-dialog yolg'on tashxis/ternary/EmptyState tozalash | `067a4dd`, `8c142a3` |
| ✅ №J | NVR kartasining uchta amali `camera_manage` ostiga o'tdi (majburiy `canManage` propi + WIRING testi, sabotaj bilan tasdiqlangan) | `154c751` |
| ✅ №K | Rad etish ekrani bitta `ForbiddenNotice` komponentiga yig'ildi (20 sahifa) + `/dashboard` havolasi + mexanik darvoza | `1708fa7` |
| ✅ №C | MARKET-06 ning ikkinchi yarmi: `GET /billing/map` (yopiq `MapDayState` enumi, ustuvorlik serverda) + xaritada rang/ikonka/`aria-label` qatlami + rasta kartasidagi «Bugungi holat» bo'limi va dalil HAVOLASI. ⚠ «Yashil bo'sh» MARKET-06 matnidan CHETLANDI: bandlik o'lchanmagan (AI-02 `Blocked`), yashil endi «sotuvchi biriktirilmagan» degani. ⚠ Karta bosish yo'li nosoz emas edi — o'lchandi | `9dbd631`, `192eb2e`, `43b4628` |
| ✅ №F | «Diagnostika» tugmasi endi DIAGNOSTIKA panelini ochadi (o'lik `saveAndDiscover` affordansi olib tashlandi, forma rejimlashtirildi) | `4d0e583` |
| ✅ №G | Mavjud foydalanuvchining rollarini tahrirlash: `PATCH /users/{id}/roles` + dialog; D-04 darajasi ikki yo'nalishda | `f57c3da` |
| ✅ №H | Platforma admini bosh ekranida bozor holati (Qoralama/Faol/`—`) va to'rt hisoblagich | `a13c447` |

## 1. BLOKER — birinchi navbatda (`/gsd:quick` bilan)

| № | Kamchilik | Yechim yo'nalishi | Qabul mezoni |
|---|---|---|---|
| ✅ №B | Bozorni "Qoralama"dan FAOL holatga o'tkazish yo'li UI'da yo'q | Endpoint ALLAQACHON bor edi (`POST /markets/{id}/activate`) — yo'l ochildi: №A tuzatilgach bozor tanlash bevosita faollashtirish qadamiga olib boradi, tugma esa qaytarib bo'lmaslikni va hisob qachondan boshlanishini aytadigan tasdiq dialogini ochadi | ✅ Qoralama faollashtiriladi (`test_wizard_flow.py:354-366`); ✅ audit hodisasi (`:1106-1132`); ✅ faollashgach billing kunlik hisob yozadi (`test_billing_close.py::test_a_draft_market_is_skipped_and_activation_starts_the_daily_charge`, sabotaj bilan tasdiqlangan) |
| ✅ №A | Qoralama bozor tanlanganda HAR SAFAR usta 1-qadamiga qaytaradi | Ildiz: qo'nish qoidasi IKKI nusxada (`fallbackStep()` va `fetchFirstIncompleteStep()`) va ular ajralib ketgan edi. Nusxa yo'q qilindi — qoida endi AYNAN BITTA joyda | ✅ 7/7 holatda kirish `?step=7` (faollashtirish) qadamiga tushadi, "Davom etish" karuseli yo'qoldi; chala qoralama hamon birinchi to'siqqa, faol bozor dashboardga |

## 2. MUHIM (har biri `/gsd:quick`)

| № | Kamchilik | Yechim yo'nalishi | Qabul mezoni |
|---|---|---|---|
| ✅ №J | Direktorga kameralar sahifasida admin tugmalari ko'rinadi (Parolni yangilash/Qayta skanerlash/Diagnostika) → bosganda "ruxsat yo'q" | Ildiz: huquq ko'zgusi sahifada ALLAQACHON bor edi (`page.tsx:128`) va to'rtta iste'molchidan uchtasiga uzatilgan — `NvrCard` tushib qolgan. Prop endi MAJBURIY (standart qiymatsiz), ya'ni unutish `tsc` da yiqiladi | ✅ Direktor uchala tugmani ham ko'rmaydi, pasport va kameralar ro'yxati QOLADI; ✅ ikki qatlamli o'lchov (komponent + haqiqiy rol bilan sahifa); ✅ sabotaj (`canManage={true}`) faqat sahifa testini qizartiradi — WIRING o'lchanayotganining dalili |
| ✅ №I | Xabar navbati jim qotadi: kvitansiya 18+ soat "Navbatda", 0 urinish, sabab/sana yo'q | Ikki mustaqil ko'rlik yopildi. (1) `notification_stale` alerti (`1ea9c5d`): manba navbat YOSHI (`created_at`), `next_attempt_at` EMAS — `defer_unresolved()` uni har 15 daqiqada oldinga surib, "muddati o'tgan" shartini mangu yolg'on qilardi; mavjud `outbox_stale` esa jobning TIRIKLIGIGA qaraydi va bu holatni strukturaviy ravishda ko'rmasdi. (2) Jadval qatori (`55535f0`): sabab yopiq to'plamdan (`pending`/`sent`/`failed`) va vaqt katagi ayniq raqamli maydonlardan | ✅ 30 daq'dan oshgan `pending` `warning` alert ko'taradi (urinishlar = 0 va kelajakdagi `next_attempt_at` bilan ham — alohida test); ✅ uchala locale'da matn; ✅ o'tgan kun sahifasida SANA, harfsizlik darvozasi + sun'iy ijobiy nazorati; ✅ `pending` sababni ko'rsatadi, `delivered`/`blocked` KO'RSATMAYDI |
| ✅ №L | *(yopildi 2026-08-16 — `f2b1830`)* Kassir qidiruv kartasida rasta holati/sotuvchi konteksti yo'q: ta'mirdagi rasta ogohlantirishsiz to'lov kartasi; sotuvchisiz rasta faqat submit'da rad | Lookup javobiga holat/sotuvchi qo'shish; ta'mir/yopiq rasta uchun ogohlantirish banner; sotuvchisiz — kartadayoq bildirish | A-02 (ta'mirda) qidirilganda banner ko'rinadi; B-01 (sotuvchisiz) kartada belgi + submit oldi ogohlantirish |
| ✅ №D | ~~Istisno kun dialogi jim no-op~~ — **TEST ARTEFAKTI deb tasdiqlandi** (№8 precedenti): Saqlash IKKINCHI tasdiq dialogini ochadi ("Yopiq kun belgilash — patta hisoblanmaydi"), avvalgi test faqat birinchi dialogni o'qigan. 2026-08-16 jonli tekshiruvda istisno kun saqlandi va ro'yxatda ko'rindi. Kod sog'lom, tuzatish KERAK EMAS | — (qayta tasnif; sana formati "M09" — №1 tizimiy bandiga tegishli) |
| ✅ №C | *(yopildi 2026-08-16 — `9dbd631`, `192eb2e` + shu commit)* MARKET-06 bo'shlig'i: plan-xaritada to'lov ranglari yo'q, rasta bosilganda karta ochilmaydi | Rang SERVERDA yechiladi (`GET /billing/map`, yopiq `MapDayState` enumi) — ustuvorlik `mismatch > no_billing > free > paid > due` bitta sof funksiyada. Klient uni faqat CSS sinfiga maps qiladi. **⚠ MARKET-06 MATNIDAN CHETLANISH:** «yashil bo'sh» BANDLIK ma'nosida QURILMADI — CV modeli yo'q (AI-02 `Blocked`), ya'ni bandlik o'lchanmagan va o'lchanmagan miqdorni rang bilan da'vo qilish taqiqlanadi (D-01); yashil endi «sotuvchi biriktirilmagan — bugun patta kutilmaydi» degan ma'noni beradi va legenda AYNAN shu jumlani yozadi. **Karta bosish yo'li NOSOZ EMAS edi** — o'lchandi: `map/page.test.tsx` birinchi yugurishdayoq YASHIL chiqdi, ya'ni yopilgan narsa kartaning BUGUNGI HOLAT bo'limi va rang qatlami | ✅ Beshala holat + ustuvorlik + storno + qoralama bozor + huquq: `tests/integration/test_map_day_status.py` (14 test); ✅ rang + ikonka + `aria-label` bo'lagi: `stall-map.test.tsx::"StallMap — to'lov rang qatlami"` (6 test); ✅ HAQIQIY `MapPage` da bosish -> dialog: `map/page.test.tsx` (3 test); ✅ kartadagi bugungi holat + dalil havolasi + ma'lumotsiz holatda bo'lim YO'Q: `stall-card-dialog.test.tsx` (8 test); ✅ server tomonidagi rol matritsasi: `test_stall_registry.py::test_every_role_that_sees_the_map_can_open_a_stall_card` |

## 3. MAYDA (bitta umumiy `/gsd:quick` to'plami)

| № | Kamchilik | Yechim |
|---|---|---|
| ✅ №E | *(yopildi 2026-08-16 — `aed8391`)* Kelajak tarif davri "Hozircha amalda" deb yorliqlanadi | Kelajak davr uchun "…dan kuchga kiradi" yorlig'i |
| ✅ №K | "Ruxsat yo'q" sahifasi yalang'och — qaytish havolasi yo'q | Nazoratchi 7 ta URL'da ko'rgan, o'lchov esa 20 ta sahifa ko'rsatdi. Yalang'och blok BITTA `ForbiddenNotice` komponentiga yig'ildi: tushuntirish + `/dashboard` havolasi (u `permission: null`). `localeHref` ning 7 nusxasi 1 modulga (`src/lib/locale-href.ts`). Darvoza: `scripts/forbidden-notice.test.mjs` |
| ✅ №M | *(yopildi 2026-08-16 — `93c0a78`)* Bekor qilingan to'lov ro'yxatda ikkita bir xil qator; hisoblagich bekordan keyin ham "1" | Bekor hodisasini vizual ajratish (kim/qachon/sabab); hisoblagich semantikasini aniqlashtirish |
| ✅ №F | *(yopildi 2026-08-16 — `4d0e583`)* "Diagnostika" tugmasi ulanish-tahrirlash formasini ochadi | Ildiz yorliq nomuvofiqligi EMAS, O'LIK AFFORDANS edi: forma birlamchi tugmasi `POST /nvr-devices` ga borardi va mavjud `host:port` uchun 409 `nvr_host_taken` dan boshqa hech nima qaytara olmasdi. Forma rejimlashtirildi (`mode="diagnose"`) — yangi panel ham, yangi endpoint ham qurilmadi; "Saqlash va kameralarni topish" o'sha panelda UMUMAN render qilinmaydi |
| ✅ №G | *(yopildi 2026-08-16 — `f57c3da`)* Foydalanuvchi rollarini keyin tahrirlash yo'li yo'q | `PATCH /users/{id}/roles` (204) + amallar menyusida "Rollarni tahrirlash". D-04 endi IKKI YO'NALISHDA: bozor admini teng adminni yoki direktorni PASAYTIRA olmaydi. Audit — mavjud `fn_audit_row()` triggeridan (ilova darajasida dublikat YOZILMAYDI); yangi rollar `/auth/refresh` dan keyin kuchga kiradi va bu ekranda halol aytiladi |
| ✅ №H | *(yopildi 2026-08-16 — shu commit)* Admin dashboardi bo'sh (bozor holati, hisoblagichlar yo'q) | Bozor holati kartasi (`market_manage` ostida — u FAQAT platforma adminida bor, ya'ni direktor bosh ekrani tegilmadi) + to'rt hisoblagich MAVJUD ikki so'rovdan (`setup-status` + `GET /users`), yangi endpoint YO'Q. Noma'lum qiymat o'rniga NOL yozilmaydi — `—` chiziladi va faollashtirish havolasi CHIZILMAYDI |

## 4. 8-FAZA IJROSIGA KIRITILGAN (alohida quick kerak emas)

| № | Kamchilik | Qayerda yopiladi |
|---|---|---|
| 🔒 №1 | uz-lokal sana formati buzuq ("2026 M08 15") — tizimiy | 8-faza (hisobot sahifalari format utillari) |
| 🔒 №3 | Pul formati nomuvofiq (UZS 8,000 / 8,000 so'm / 8 000 UZS) | 8-faza |
| 🔒 №5 | "oxirgi ko'rilgan: -1 d" manfiy nisbiy vaqt | 8-faza yoki mayda to'plam |

## 5. TASHQI SHARTGA BOG'LIQ

| Band | Shart |
|---|---|
| 🔒 Nazoratchi baholash oqimi testi | CV `.onnx` modeli eksporti (GPU ijara) |
| 🔒 Telegram botlar testi (+№I ning to'liq E2E tekshiruvi) | Bot tokenlari `.env`ga |
| 🔒 Jonli ko'rinish (MSE) uzilishi | Chip mavjud (alohida debug sessiya) |
| ✅ 4/5-fazalar qayta tekshiruvi | Bajarildi 2026-08-16: ikkalasi `human_needed` (04: 5/5 mezon, 7 UAT bandi; 05: 4/5, SC2 ONNX'ga bog'liq) — VERIFICATION.md fayllari yangi |
| ✅ Jonli brauzer qayta tekshiruvi (yangi frontend imij) | Bajarildi 2026-08-16: №A (tanlov→step=7; faol bozorda → dashboard), №B (bozor FAOL, `is_active=t`, tasdiq dialogi halol), №H (holat kartasi "Faol" + 4 hisoblagich), №F (Diagnostika→NVR paneli), №C (xarita ranglari + rasta kartasi: toifa/tarif/sotuvchi), №J (direktor kameralarda faqat "Ko'rish"), №K (taqiq sahifasi + dashboard havolasi), №L (A-02 "Ta'mirda" banneri + sotuvchi konteksti). Vitest to'liq: 82 fayl / 1004 test yashil |

## 5b. QAYTA TEKSHIRUVDAN CHIQQAN YANGI MAYDA BANDLAR (2026-08-16)

| # | Band | Manba |
|---|---|---|
| ⬜ V-1 | Ko'r audit urug' testi flaky (~0.6% yolg'on-qizil har yugurishda, C(12,4)=495 kombinatorikasi) — determinlashtirilsin yoki retry-annotatsiya | 05-VERIFICATION F-1 |
| ⬜ V-2 | cv-tests dev bazasiga haqiqiy cv_detect yurak urishini yozadi — dev-monitor o'lik quvurni sog'lom ko'rsatadi (prod'ga tegmaydi) | 05-VERIFICATION F-3 |
| ⬜ V-3 | cv-service yetim navbat vazifalari (model kelganda tozalash/qayta ishga tushirish tartibi runbook'ka) | 05-VERIFICATION F-2 |
| ⬜ V-4 | Faollashtirishdan keyin dashboard "Bozor holati" kartasi sessiya yangilanishida "—" ko'rsatadi (refresh payload'da `is_active` yo'q) — faqat qayta kirishda "Faol" chiqadi. Yechim: sessiya-refresh javobiga `is_active` qo'shish yoki faollashtirishdan keyin sessiyani qayta qo'llash | Jonli sayr 2026-08-16 |
| ⬜ V-5 | Direktor wizard'ni (`/markets/setup`) o'qiy oladi — backend yozishni 403 qiladi, lekin sahifa ko'rinishi rol-qarori aniqlanmagan: ataylab shaffoflikmi yoki guard qo'shiladimi | Jonli sayr 2026-08-16 |

## 6. DEV-MUHIT TOZALASH (kod emas)

- ✅ "23" nomli test-rasta — "Yopiq" holatga o'tkazildi (2026-08-16)
- ✅ 2 ta "Jonli sinov admini" — bloklandi (is_active=false, 2026-08-16)
- ⬜ Dev eslatma: core-api qayta yaratilsa nginx restart kerak (compose'da `depends_on`/resolver yaxshilash mumkin)

## 7. IJRO TARTIBI (limit tiklangach, ketma-ket)

1. ✅ `/gsd:quick` — №B + №A (bloker juftlik, bitta vazifa) — bajarildi 2026-08-16, `b90bb09` · `9e52fd5` · `96171c1`
2. `/gsd:quick` — ✅ №J (+ 3-bo'limdan №K, bitta vazifada — bajarildi 2026-08-16) · ✅ №I (bajarildi 2026-08-16, `1ea9c5d` · `55535f0`) · ✅ №L (bajarildi 2026-08-16, `f2b1830`) · ✅ №D (test artefakti — kod sog'lom) · ✅ №C (bajarildi 2026-08-16, `9dbd631` · `192eb2e` · shu commit)
3. `/gsd:quick` — 3-bo'lim mayda to'plami
4. `/clear` → `/gsd-execute-phase 8` (№1/№3/№5 shu yerda)
5. 4/5-faza qayta tekshiruvi + MSE chip + dev tozalash
6. UI-polish bosqichi (UI-UX-MASTERPLAN.md) + landing (LANDING-BRIEF.md)

## 7b. UI/UX JILO QARZI (buzilmagan, lekin 10/10 emas — UI-polish bosqichi, manba: UI-UX-MASTERPLAN.md)

> Bular "bug" emas — mijoz talab qilgan 10/10 darajaga yetish uchun qurish kerak bo'lgan qatlam. Ijro: 7-bo'lim 6-bandi (sketch → UI-SPEC → polish faza). Hech biri unutilmasligi uchun shu yerda sanaladi:

| # | Band | Masterplan bo'limi |
|---|---|---|
| ⬜ U-1 | Motion tizimi: tokenlar (150/250/400ms), kirish/chiqish xoreografiyasi, stagger, reduced-motion | §3 |
| ⬜ U-2 | 6 "vau" lahza (bosh: to'lov muvaffaqiyati — check-draw + pulse + shared-element; smena muhri; direktor count-up; usta bayrami; NVR kashfiyot; nomuvofiqlik kirishi) | §4 |
| ⬜ U-3 | Komponent jilosi: tugma press-scale, karta hover, dialog scale+fade, skeleton'lar (spinner o'rniga), forma shake, bo'sh-holat SVG illustratsiyalari | §5 |
| ⬜ U-4 | Dark mode + quyosh rejimi (kassir uchun yuqori kontrast) | §1.3–1.4 |
| ⬜ U-5 | Rang 2.0: iliq fon, surface balandliklari, aksent hover/pressed tonlari | §1 |
| ⬜ U-6 | Direktor paneli boyitish: 2 ustun grid, stat-kartalar, sparkline, bandlik halqasi (8-faza hisobotlari bilan birga) | §6.3 |
| ⬜ U-7 | Desktop bo'shligi: max-width konteyner, katta ekran maketlari | §7.5 |
| ⬜ U-8 | Kameralar ro'yxatiga snapshot-thumbnail'lar (25 kanalda uzun ro'yxat muammosi) | §6.5 |
| ⬜ U-9 | Qisqa validatsiya matnlarini to'liq gapga ("To'lov turi" → "To'lov turini tanlang — Naqd yoki Terminal") | §7.4 |
| ⬜ U-10 | Kassir "bugun yig'ildi" mini-hisoblagichi (motivatsiya) | §6.2 |
| ⬜ U-11 | Nazoratchi konveyeri: klaviatura-birinchi, crossfade, progress "34/50" | §6.6 |
| ⬜ U-12 | Kadr jadvali timeline ko'rinishi (bajarilgan ✓ / o'tkazilgan ✗) | §6.7 |
| ⬜ U-13 | Plan-xarita jilosi: zoom inersiya, hover glow, spring yon panel (№C funksional qismidan KEYIN) | §6.4 |
| ⬜ U-14 | V2-PROC-04: plan-rasm yuklash + rastalarni chizma ustida chizish (qator-quroli, avto-raqamlash) | §6.4 |
| ⬜ U-15 | Tipografiya 2.0: Display-XL pul raqamlari, tabular-nums | §2 |
| ⬜ U-16 | Login sahifasi brend lahzasi (nozik jonli gradient) | §6.1 |
| ⬜ U-17 | sbozor.uz landing: "Jonli bozor" hero (12s sikl), scroll-hikoya, demo-forma → bot, SEO/OG, 3 til (LANDING-BRIEF.md to'liq) | LANDING-BRIEF |
| ⬜ U-18 | G-motion sifat darvozalari (reduced-motion, kassir ≤150ms, Lighthouse ≥90 arzon Android) | §9 |
| ⬜ U-19 | Mobil matritsa smoke-testi (arzon Android + Safari) — 8-bo'limdagi band bilan bog'liq | §7.5 |

## 8. QAMROV CHEGARALARI — noma'lum kamchiliklar qayerda yashashi mumkin

> Bu reestr BILGAN kamchiliklar ro'yxati. Quyidagi hududlar tekshirilmagan — ulardan yangi bandlar chiqishi tabiiy:

| Hudud | Holat | Qachon/qanday tekshiriladi |
|---|---|---|
| Butun kodbaza reviewi | Faqat so'nggi tuzatishlar atrofi ko'rildi (tor review 5 yangi joy topdi — keng review ko'proq topadi) | Fazama-faza `/gsd:code-review` yoki `/code-review ultra` (bulut) |
| CV qatlami jonli ishi | Model yo'q — nazoratchi konveyeri, aniqlik, dalil-rasm real oqimi sinalmagan | 🔒 `.onnx` eksportidan keyin to'liq sikl-test |
| Botlar E2E | Token yo'q | 🔒 token qo'shilgach real Telegram sinovi |
| Masshtab (300–1000 rasta, 25 kamera, parallel kassirlar) | 3 rasta bilan sinaldi | Karmana ma'lumotlari import qilingach yuk-sinov; plan-xarita/ro'yxatlar/billing-close kuzatuvi |
| Real NVR firmware farqlari | Simulyatorda sinaldi | 🔒 Dala ishi (hujjatlashtirilgan risk: oqim limiti, ISAPI xulqi) |
| 4/5-faza qayta tekshiruvi | VERIFICATION kutilmoqda | Reja bo'yicha (5-band, 7-bo'lim) |
| Brauzer/qurilma matritsasi | Faqat desktop Chrome | Kassir oqimini arzon Androidda + Safari smoke-test (UI-polish bosqichida) |
| Xavfsizlik retro-auditi | Threat-modellar va RLS testlari bor; maxsus hujum-sinovi yurgizilmagan | `/gsd:secure-phase` barcha fazalar bo'yicha (go-live'dan oldin) |
| 8-faza yangi yuzalari | Hali qurilmagan | O'z verifikatori + ijrodan keyin 4-rol smoke-sayr takrori |

## 9. PROD TAHLILI — 2026-09-24 (Karmana, quick 260924-hpm)

> **Manba:** prod bazasidan faqat-o'qish so'rovlari (buyurtmachi yurgizgan) + to'liq lokal test/lint yugurishi.

| № | Kamchilik | Yechim | Commit |
|---|---|---|---|
| ✅ P-1 | **KRITIK:** 28-avgustdan 28 kun davomida bironta patta hisobi yozilmadi (to'lovlar kuniga 30–44). Kamera ulangach bozor butunlay D-04 ga o'tdi, zona esa 53 rastadan 6–9 tasida — zonasiz rastalar hisobsiz qoldi | Gibrid qoida: zonasiz rasta biriktirish bo'yicha (`_charge_by_assignment`), zonali — D-04; kech tasdiq dalilsiz hisobni kamaytirmaydi; tiklash skripti bo'sh kunni so'ramasdan hisoblamaydi | `ba3edc3` |
| ✅ P-2 | Uzilish 28 kun sezilmadi: `billing.close` har kecha ishladi, faqat natijasi 0 edi | `billing_no_charges` alerti — ochiq kunda to'lov bor, hisob yo'q | `add2376` |
| ✅ P-3 | Xaritadagi 5 sariq rasta 4 hafta ko'rilmagan ishlar edi: «ochiq nomuvofiqlik» matni noaniq, kartadan ishga yo'l yo'q, sahifa faqat kechani ko'rsatadi | Matn «hal qilinmagan», kartada ish kuniga havola, `GET /reconciliation/open-days` + e'lon | `6cc6e44` |
| ✅ P-4 | Landing kalkulyatorida oylik yo'qotish soni chiqmas edi («Oyiga ~ so‘m») | `t.rich` tegi; regressiya testi | `ffd6604` |
| ✅ P-5 | 37 ta test seed sanasi o'tmishga qolgach qizargan (sana-bombasi) | Summa kundan hosila (`day_tariff_soum`/`day_total_soum`) | `123bc0f` |
| ✅ P-6 | `/internal/camagent/snapshot` tenancy matritsasida 3 ta qizil, o'z kontrakti o'lchanmagan | `EXEMPT_ROUTES` + `test_camagent_internal_auth.py` | `8c4f9f4` |
| ✅ P-7 | Root lint darvozasi vendoring'dan beri qizil (ruff 37, mypy 125); vendored gateway'da `log` aniqlanmagan (tozalash halqasini o'ldirardi) | Vendored nusxa root lintdan chiqarildi, `log` tuzatildi, o'z fayllarimiz tozalandi | `603a972` |
| ✅ P-8 | `camagent.py` izohlari mojibake, `_accept` tiplanmagan | Tiklandi, tiplandi, `.one()` | `d9a20dc` |
| ⬜ P-9 | Prod'ga deploy + o'tgan kunlarni tiklash | Buyurtmachi qarori: 1, 2, 6, 7-sentabr yopiqmi; 28-avgust va 10-sentabr; keyin `backfill_charges.py` (avval `BACKFILL_DRY_RUN=1`) | — |
| ⬜ P-10 | 26–27-avgustdagi 5 ta ochiq «band, lekin to'lovsiz» ishi | Nazoratchi/direktor ko'rib chiqadi | — |
| 🔒 P-11 | Vendored `agent_gateway/app.py` dagi `log` tuzatmasi | CamAgent (Kamera) manba reposiga kiritilsin — aks holda keyingi sinxronizatsiya qaytaradi | — |

---
*Reestr har yopilgan band bilan yangilanadi. "Hech narsa qolmasligi" sharti: 1–3 va 6-bo'limlar to'liq ✅ bo'lgunicha 8-faza yakunlanmaydi deb hisoblanmaydi. 8-bo'lim hududlaridan chiqqan yangi topilmalar reestrga qo'shiladi.*
