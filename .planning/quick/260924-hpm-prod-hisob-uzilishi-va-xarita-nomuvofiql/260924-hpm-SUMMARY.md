---
quick_id: 260924-hpm
phase: quick
plan: 260924-hpm
subsystem: billing
tags: [billing_close, hybrid-billing, alerting, reconciliation, map, backfill, landing, time-bomb, lint-gate, tenancy]
status: complete

provides:
  - "Gibrid hisob qoidasi: kamerali bozorda ZONASIZ rasta biriktirish bo'yicha, zonali rasta D-04 bo'yicha (`_charge_by_assignment` — ikki chaqiruvchi, bitta qoida)"
  - "`_late_review` dalilsiz (biriktirish bo'yicha yozilgan) hisobni kamaytirmaydi (`ExistingCharge.has_evidence`)"
  - "Xavfsiz tiklash skripti `ops/scripts/backfill_charges.py` — bo'sh kun qo'riqchisi, quruq yugurish, bugun qo'riqchisi, `day_close` -> `billing_close`"
  - "Faqat-o'qish qarz tekshiruvi `ops/scripts/debt_preview.py`"
  - "`billing_no_charges` alerti — «to'lov bor, hisob yo'q» jimjit uzilishi"
  - "`GET /reconciliation/open-days` + sahifadagi «boshqa kunlarda hal qilinmagan ishlar» e'loni"
  - "Rasta kartasidan case kuniga havola; «ochiq» -> «hal qilinmagan» matni (3 til)"
  - "Landing kalkulyatorining oylik soni qayta ko'rinadi (`t.rich` tegi)"
  - "Sana-bombasi testlari hosila summaga o'tkazildi (`day_tariff_soum` / `day_total_soum`)"
  - "`/internal/camagent/snapshot` — tenancy matritsasidan sabab bilan chiqarildi, o'z kontrakti testlandi"
  - "Root lint darvozasi (`ruff check . && ruff format --check . && mypy .`) qayta yashil"

key-files:
  created:
    - ops/scripts/debt_preview.py
    - frontend/src/components/reconciliation/open-case-days.tsx
    - tests/unit/test_billing_silence_alert.py
    - tests/integration/test_camagent_internal_auth.py
  modified:
    - services/core-api/app/jobs/billing_close.py
    - services/core-api/app/repositories/billing_repo.py
    - services/core-api/app/jobs/alerting.py
    - services/core-api/app/repositories/reconciliation_repo.py
    - services/core-api/app/api/v1/reconciliation.py
    - services/core-api/app/schemas.py
    - services/core-api/app/api/internal/camagent.py
    - ops/scripts/backfill_charges.py
    - frontend/src/components/stalls/stall-card-dialog.tsx
    - frontend/src/lib/reconciliation-queries.ts
    - frontend/src/app/[locale]/(app)/reconciliation/page.tsx
    - frontend/src/components/marketing/loss-calc.tsx
    - frontend/messages/{uz-Latn,uz-Cyrl,ru}.json
    - tests/fixtures/billing_domain.py
    - tests/tenancy/test_cross_tenant.py
    - pyproject.toml

key-decisions:
  - "Zonasiz rasta — o'lchovning YO'QLIGI, «bo'sh» javobi emas: kamerasiz bozor bilan AYNI ma'muriy prezumpsiya. Zonali rastalar D-04 da qoldi — gibrid yo'l o'lchov bilan bahslashmaydi"
  - "Dalilsiz hisobni kech tasdiq kamaytirmaydi — tuzatish inson qarori (`charge_adjustments`)"
  - "Tiklash skripti bo'sh (to'lovsiz ochiq) kunni SO'RAMASDAN hisoblamaydi — bayram kuni butun bozorga soxta qarz yozardi"
  - "Case'ni to'lov bilan avtomatik yopish QILINMADI (D-C2 qulflangan); o'rniga topiluvchanlik tuzatildi"
  - "Vendored `services/camagent-gateway` root lintdan chiqarildi (cv/bot-service naqshi); undagi bitta haqiqiy `log` xatosi minimal tuzatildi — manba reposiga ko'chirilishi shart"

completed: 2026-09-24
---

# Quick 260924-hpm: prod hisob uzilishi, jimjit uzilish alerti va xarita nomuvofiqligi

**Karmanada 28-avgustdan 28 kun davomida bironta patta hisobi yozilmagan edi: kamera ulangach bozor butunlay bandlik (D-04) rejimiga o'tgan, zona esa 53 rastadan 6–9 tasida bo'lgan. Endi zonasiz rastalar biriktirish bo'yicha hisoblanadi, o'tgan kunlarni xavfsiz tiklash skripti tayyor, bunday jimjit uzilish ertasi kuni ertalab alert bilan ko'rinadi va xaritadagi sariq rastadan bir bosishda o'sha ishga o'tiladi. Yo'l-yo'lakay ko'rilgan barcha qizil testlar, lint darvozasi va landing kalkulyatoridagi yashirin xato ham tuzatildi.**

## Commitlar

| Commit | Mazmun |
|---|---|
| `123bc0f` | Sana-bombasi testlari: summa kundan hosila (`day_tariff_soum` / `day_total_soum`), tik sanog'i ikki bozor bilan |
| `ba3edc3` | Gibrid hisob qoidasi + `has_evidence` + xavfsiz tiklash skripti + `debt_preview.py` |
| `add2376` | `billing_no_charges` alerti (3 til, kalitlar darvozasi 16 -> 17) |
| `6cc6e44` | Xarita matni, rasta kartasidan ish kuniga havola, `GET /reconciliation/open-days` + e'lon |
| `d9a20dc` | `camagent.py`: mojibake izohlar, `_accept` tiplari, `.one()` |
| `8c4f9f4` | `/internal/camagent/snapshot`: `EXEMPT_ROUTES` + `test_camagent_internal_auth.py` |
| `603a972` | Root lint darvozasi: vendored gateway chiqarildi, `log` xatosi, o'z fayllarimiz |
| `ffd6604` | Landing kalkulyatorining oylik soni (`t.rich` tegi) + app-shell mock shovqini |

## Tekshiruv (2026-09-24, lokal Docker)

- **Backend lint:** `ruff check .` toza · `ruff format --check .` 405 fayl · `mypy .` 382 fayl — xatosiz
  (vendoring'dan beri birinchi marta yashil).
- **Backend testlar:** to'liq to'plam (~3 570 test) bir marta yugurtirildi — 41 ta qizil, 0 ta setup
  xatosi. 41 tasining HAR BIRI tuzatildi va o'z fayllari bilan qayta yugurtirildi:
  sana-bombasi 7 fayli — 121/121; `test_capture_tick` + `test_three_way` +
  `test_camagent_internal_auth` + `tests/tenancy/test_cross_tenant.py` — 670/670;
  `tests/unit` + lint tegilgan `test_review_seed` / `test_rate_limit_proxy` — 1359/1359.
  Qolgan fayllar to'liq yugurishda (yakuniy mahsulot kodi bilan) yashil edi; undan keyingi
  mahsulot o'zgarishlari faqat `ruff format` (AST-teng) va vendored nusxa.
- **Frontend:** vitest to'liq to'plam 110 fayl / 1300 test yashil; landing tuzatmasidan keyin
  marketing (33) + app-shell (10) qayta — yashil, stderr ogohlantirishlari yo'q; skript
  darvozalari 399/399; `tsc --noEmit`, `eslint`, i18n 1987 kalit × 3 til parity — toza.
- **TDD izi:** landing regressiya testi tuzatishdan OLDIN «Oyiga ~ so‘m» bilan qizil ekanligi
  o'lchandi.

## Rejadan chetlanishlar

1. **Sana-bombasi testlari (rejada yo'q edi).** To'liq backend to'plamida 41 ta
   qizil test chiqdi; 37 tasi mahsulotga aloqasiz: seed QADALGAN sanalarga
   tayanadi (tarif 2026-09-02 da o'zgaradi, kadr jadvallari 2026-09-01 dan),
   «bugun» testlari esa bu sanalar kelajak bo'lgan paytda yozilgan. Summa
   kundan hosila qilindi; tik sanog'i ikki bozorning haqiqiy qatorlari bilan.
   Bittasi (faza-6 SC#1) gibrid qoidaning kutilgan natijasi — to'plam dalil
   bo'yicha ajratildi.
2. **`/internal/camagent/snapshot` matritsasi (3 ta qizil).** Servis marshruti
   tenancy matritsasiga foydalanuvchi marshruti sifatida tushib qolgan edi —
   `EXEMPT_ROUTES` ga sabab bilan qo'shildi va o'z kontrakti alohida testlandi.
3. **Root lint darvozasi qizil edi.** CamAgent vendoring'idan beri `npm run lint`
   yiqilardi (ruff 37, mypy 125). Vendored nusxa root lintdan chiqarildi, undagi
   haqiqiy `log` xatosi tuzatildi, o'z fayllarimizdagi xatolar va format tuzatildi.
4. **Landing kalkulyatori.** To'liq vitest stderr'ida «Functions are not valid as a
   React child» ko'rindi — oylik yo'qotish soni ekranda umuman chiqmas edi
   («Oyiga ~ so‘m»). Tuzatildi, regressiya testi qizil->yashil o'lchandi.
5. **`camagent.py`** — mojibake izohlar va mypy xatosi (`.one()`).
6. **Manfiy «-22 s»** — `41f5587` (2026-08-28) da allaqachon tuzatilgan edi, qayta
   ish qilinmadi.

## Ochiq qoldi (buyurtmachi qarori / tashqi)

- Prod'ga deploy va tiklashni yurgizish. Oldin: 1, 2, 6, 7-sentabr (to'lov 0)
  kalendarda yopiq deb belgilanishi yoki `BACKFILL_ALLOW_EMPTY_DAYS` ga yozilishi;
  28-avgust (2 to'lov) va 10-sentabr (9 to'lov) bo'yicha qaror.
- Zonali 6–9 rasta D-04 da: nazoratchi tasdiqlamagan kunlar hisobsiz qoladi.
- 26–27-avgustdagi 5 ta ochiq ish ko'rib chiqilishi kerak.
- Tiklashdan keyin: kechikkan qarzlar uchun sotuvchilarga eslatma va yangi
  «band, lekin to'lovsiz» ishlari tug'iladi (mahsulotning odatiy xulqi).
- `agent_gateway/app.py` dagi `log` tuzatmasi CamAgent (Kamera) reposiga ham
  kiritilsin, aks holda keyingi sinxronizatsiya uni qaytaradi.
- Rasta holati tarixi yo'q (tiklash bugungi holatni o'qiydi) — sxema ishi.
