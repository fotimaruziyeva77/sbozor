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
