---
status: partial
phase: 01-poydevor-va-tenant-xavfsizligi
source: [01-VERIFICATION.md]
started: 2026-07-29T22:05:00Z
updated: 2026-07-29T22:05:00Z
---

## Current Test

[inson tekshiruvini kutmoqda]

## Tests

### 1. Jonli stek ustida to'liq oqim (8 + 15 qadam)
expected: `npm run up` + `npm run migrate` + `docker compose --profile web --profile proxy up -d` bilan stek ko'tariladi; 01-08 Task 3 dagi 8 qadamlik va 01-09 Task 2 dagi 15 qadamlik `<human-check>` ketma-ketligining har bir qadami kutilgan natijani beradi — login, majburiy parol almashtirish, bozor tanlash, til almashtirish (uz-Latn ↔ uz-Cyrl ↔ ru), foydalanuvchi yaratish, audit jurnali ko'rinishi, DB-owner o'zgarmaslik namoyishi.
result: [pending]
note: CR-01 (parol darvozasi) va CR-02 (bozor tanlash tugmalari) tuzatildi va kodda + testda mustaqil tasdiqlandi — ilgari bu ketma-ketlikni to'xtatgan 3- va 8-qadamlar endi o'tishi kutilmoqda.

### 2. uz-Cyrl imlo sifati
expected: `frontend/messages/uz-Cyrl.json` dagi matnlar o'zbek kirill imlosi qoidalariga to'liq mos (masalan `Ҳисоб`, `маъмурият`, `аъзоликлари` kabi so'zlar); avtomatik transliteratsiya generatori chiqargan ambiguity'lar `uz-Cyrl.overrides.json` da to'g'ri hal qilingan.
result: [pending]
note: `i18n:check` struktura darajasida yashil (120 kalit × 3 til, drift yo'q) — qolgani tilshunoslik sifati, uni faqat inson baholaydi. Gap-closure to'lqini bu fayllarga tegmadi.

### 3. Apple-uslub vizual muvofiqlik
expected: AppShell mobil pastki navigatsiyasi va umumiy ko'rinish SBOZOR-MVP-texnik-topshiriq.md §7 talablariga mos — kassir mobil oqimida barmoq nishonlari ≥44px, minimalist va kam-kontrastli dizayn.
result: [pending]
note: Vizual dizayn sifati grep/test bilan o'lchanmaydi. Gap-closure to'lqini bu qismga tegmadi.

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
