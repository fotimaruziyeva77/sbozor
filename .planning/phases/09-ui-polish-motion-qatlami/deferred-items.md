# Phase 09 — Kechiktirilgan bandlar

> Ijro davomida topilgan, LEKIN bu fazaning ko'lamiga kirmaydigan bandlar.
> Har bandda sabab va (bor bo'lsa) kelajak ijrochisi uchun foydali topilma.

## 1. Konfetti ijrosi va `market_day_cleared` bayrog'i — 9-fazadan CHIQARILDI

- **Qayd etildi:** 2026-08-17 (09-01 Task 1)
- **Sabab — uch qavat:**
  - **(a)** Tetikning haqiqat manbai bugun **yo'q**: `daily_plan` / `daily_target` /
    `plan_soum` skani backend'da ham, frontend'da ham **0 natija** [09-UI-SPEC M-10].
  - **(b)** `paymentResponseSchema` — `z.strictObject` (**8 kalit**,
    `frontend/src/lib/payment-queries.ts:119`), ya'ni javobga maydon qo'shish
    **ikki tomonlama, kelishilgan** o'zgarish (server yolg'iz qo'shsa klient
    parse'da yiqiladi) va u **backend fazasining** ishi [09-RESEARCH Tuzoq 8].
  - **(c)** Klientdagi **har qanday** hosila ko'r deklaratsiya darvozasini buzadi:
    oxirgi to'lovlarni qo'shish — server oynasi atayin 5 ta va yig'uvchi amal
    taqiqlangan; `useMarketPending()` — bozor kesimidagi summani ochardi [M-12];
    «yig'ilgan/hisoblangan» foizi — `system_total_soum` `BLIND_DECLARATION_TOKENS`
    ro'yxatida [09-UI-SPEC §0.2, §9.2].
- ⛔ **Shartnoma 09-UI-SPEC §9.1/§9.3 da [TALAB] holatida TO'LIQ QOLADI** —
  o'chirilmaydi. Tetik kelgan kunda yoqish **bir qator**:
  `if (record.market_day_cleared && !firedThisSession && !reducedMotion) burst()`.
- **Foydali topilma (kelajak ijrochisi uchun):** tetikning ma'lumot manbai
  **ALLAQACHON mavjud** — `billing_repo.PendingMarket.pending_stall_count`
  [`services/core-api/app/repositories/billing_repo.py:1338-1341`, chiqarilishi
  `api/v1/billing.py:275-278`]. Ya'ni kelajakdagi ijro **migratsiya TALAB
  QILMAYDI**: `market_day_cleared` — hosila mantiqiy qiymat (saqlanadigan ustun
  emas), `create_payment` ichida `pending_projection(...)` ni bir marta chaqirish
  bilan hisoblanadi. **Audit ta'siri: nol** — mantiqiy hosila qiymat yozuv emas,
  `audit_log` ga tushmaydi [09-RESEARCH Tuzoq 8 bonus topilmasi].
- ✅ **Holat 09-07 da TASDIQLANDI (2026-08-17):** band o'z kuchida — konfetti
  ijrosi bu fazada YO'Q va bu to'g'ri; shartnoma 09-UI-SPEC §9.1/§9.3 da
  [TALAB] holatida SAQLANGAN; `G-motion-1(d)` ta'rif skani va
  `collect-surface` `CONFETTI_TOKENS` (3 nom) darvozalari yashil — ijro
  izlari 0. Takror yozilmadi, faqat holat qayd etildi.

## 2. `gate` byudjeti zaxirasi 41 s (1,8 %) — KRITIK TOR

- **Qayd etildi:** 2026-08-17 (09-07 Task 2 o'lchovi)
- **O'lchov:** tinch xostda IKKI to'liq o'lchov: **2259 / 2102 s**, chegara
  **2300 s**. Protokol bo'yicha chegara KO'TARILMADI (eng yomon < chegara),
  LEKIN zaxira 08-20 dagi 391 s (17 %) dan 41 s (1,8 %) ga tushdi —
  o'sish to'plamniki (9-faza: skriptlar ~296→349, vitest 1110→1170).
- **Xavf:** keyingi faza to'plamga BIRINCHI qo'shimchasini kiritganidayoq
  darvoza **nuqson sababli EMAS** qizaradi.
- **Egasi:** keyingi `/gsd-plan-phase` (10-faza rejalashtiruvchisi).
- **Tetigi:** 10-fazaning birinchi to'plam qo'shimchasi / birinchi `gate`
  o'lchovi — chegara `eng yomon × 1,20` bilan ko'tarilsin YOKI zanjir
  yengillashtirilsin (masalan, backend yarmini faza-shartli qilish);
  qaror raqam bilan yozilsin.
- `gate:fast` ham xuddi shu sinfda: 189 s / 200 s — zaxira 11 s (5,5 %).

## 3. Backend testlarda «bugun ochiq kun» yashirin prekonditsiyasi — SINF

- **Qayd etildi:** 2026-08-17 (09-07 Task 2, birinchi DUSHANBA gate yugurishi)
- **Topilma:** seed A bozori dushanba YOPIQ (`A_OPEN_WEEKDAYS = 2..7`) va
  «bugun»ga tayangan ikki test dushanba kuni DETERMINISTIK qizardi:
  `test_billing_api::test_a_stall_in_maintenance_...` (pending
  `amount_soum=None`) va `test_phase6_criteria::test_sc5_...` (POST 422
  `market_closed`). Ikkalasi `11a4f3a` da tuzatildi (arrange qadamida
  `open_weekdays=1..7` UPDATE — mahsulot yo'liga nol ta'sir).
- **Ochiq qolgani — SINF:** boshqa testlar ham «bugun»ga yashirin tayangan
  bo'lishi mumkin (bugungi yugurishda faqat shu ikkitasi qizardi, lekin
  qamrov «dushanba kuni to'liq gate» bilan atigi BIR marta o'lchandi).
- **Egasi:** kelajak ijrochisi (birinchi duch kelgan plan).
- **Tetigi:** navbatdagi dushanba kungi `gate` yugurishi qizarsa — yiqilgan
  testga ayni naqsh (ochiq-kun prekonditsiyasi) qo'llansin; ildiz yechim
  (masalan, `env` fixture darajasida bugunni ochiq qilish) alohida reja
  bandi sifatida baholansin.
