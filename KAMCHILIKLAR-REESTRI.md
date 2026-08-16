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
| ⬜ №L | Kassir qidiruv kartasida rasta holati/sotuvchi konteksti yo'q: ta'mirdagi rasta ogohlantirishsiz to'lov kartasi; sotuvchisiz rasta faqat submit'da rad | Lookup javobiga holat/sotuvchi qo'shish; ta'mir/yopiq rasta uchun ogohlantirish banner; sotuvchisiz — kartadayoq bildirish | A-02 (ta'mirda) qidirilganda banner ko'rinadi; B-01 (sotuvchisiz) kartada belgi + submit oldi ogohlantirish |
| ✅ №D | ~~Istisno kun dialogi jim no-op~~ — **TEST ARTEFAKTI deb tasdiqlandi** (№8 precedenti): Saqlash IKKINCHI tasdiq dialogini ochadi ("Yopiq kun belgilash — patta hisoblanmaydi"), avvalgi test faqat birinchi dialogni o'qigan. 2026-08-16 jonli tekshiruvda istisno kun saqlandi va ro'yxatda ko'rindi. Kod sog'lom, tuzatish KERAK EMAS | — (qayta tasnif; sana formati "M09" — №1 tizimiy bandiga tegishli) |
| ⬜ №C | MARKET-06 bo'shlig'i: plan-xaritada to'lov ranglari yo'q, rasta bosilganda karta ochilmaydi | Rang qatlami (yashil bo'sh/ko'k to'langan/qizil qarzdor/sariq nomuvofiq) + bosilganda karta (dalil-rasm) | Bugun to'lagan rasta ko'k; bosilganda karta ochiladi; legenda yangilanadi |

## 3. MAYDA (bitta umumiy `/gsd:quick` to'plami)

| № | Kamchilik | Yechim |
|---|---|---|
| ⬜ №E | Kelajak tarif davri "Hozircha amalda" deb yorliqlanadi | Kelajak davr uchun "…dan kuchga kiradi" yorlig'i |
| ✅ №K | "Ruxsat yo'q" sahifasi yalang'och — qaytish havolasi yo'q | Nazoratchi 7 ta URL'da ko'rgan, o'lchov esa 20 ta sahifa ko'rsatdi. Yalang'och blok BITTA `ForbiddenNotice` komponentiga yig'ildi: tushuntirish + `/dashboard` havolasi (u `permission: null`). `localeHref` ning 7 nusxasi 1 modulga (`src/lib/locale-href.ts`). Darvoza: `scripts/forbidden-notice.test.mjs` |
| ⬜ №M | Bekor qilingan to'lov ro'yxatda ikkita bir xil qator; hisoblagich bekordan keyin ham "1" | Bekor hodisasini vizual ajratish (kim/qachon/sabab); hisoblagich semantikasini aniqlashtirish |
| ⬜ №F | "Diagnostika" tugmasi ulanish-tahrirlash formasini ochadi | Yorliq-mazmun mosligini tekshirish: alohida diagnostika paneli yoki tugma nomini to'g'rilash |
| ⬜ №G | Foydalanuvchi rollarini keyin tahrirlash yo'li yo'q | Amallar menyusiga "Rollarni tahrirlash" (dizayn qarori bilan) |
| ⬜ №H | Admin dashboardi bo'sh (bozor holati, hisoblagichlar yo'q) | Holat kartasi ("Qoralama — ishga tushirish uchun ...") + asosiy hisoblagichlar |

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
| 🔒 4/5-fazalar qayta tekshiruvi | `/gsd-verify-work` yoki tegishli tekshiruv oqimi |

## 6. DEV-MUHIT TOZALASH (kod emas)

- ✅ "23" nomli test-rasta — "Yopiq" holatga o'tkazildi (2026-08-16)
- ✅ 2 ta "Jonli sinov admini" — bloklandi (is_active=false, 2026-08-16)
- ⬜ Dev eslatma: core-api qayta yaratilsa nginx restart kerak (compose'da `depends_on`/resolver yaxshilash mumkin)

## 7. IJRO TARTIBI (limit tiklangach, ketma-ket)

1. ✅ `/gsd:quick` — №B + №A (bloker juftlik, bitta vazifa) — bajarildi 2026-08-16, `b90bb09` · `9e52fd5` · `96171c1`
2. `/gsd:quick` — ✅ №J (+ 3-bo'limdan №K, bitta vazifada — bajarildi 2026-08-16) · ✅ №I (bajarildi 2026-08-16, `1ea9c5d` · `55535f0`) · ⬜ №L · ✅ №D (test artefakti — kod sog'lom) · ⬜ №C
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

---
*Reestr har yopilgan band bilan yangilanadi. "Hech narsa qolmasligi" sharti: 1–3 va 6-bo'limlar to'liq ✅ bo'lgunicha 8-faza yakunlanmaydi deb hisoblanmaydi. 8-bo'lim hududlaridan chiqqan yangi topilmalar reestrga qo'shiladi.*
