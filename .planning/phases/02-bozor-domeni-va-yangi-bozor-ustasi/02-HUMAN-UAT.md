---
status: partial
phase: 02-bozor-domeni-va-yangi-bozor-ustasi
source: [02-VERIFICATION.md, 02-VALIDATION.md]
started: 2026-08-03
updated: 2026-08-03
---

## Current Test

[inson tekshiruvini kutmoqda — fazaning muhandislik yetkazmalari tugallangan, bu bandlar oqimni bloklamaydi]

## Tests

### 1. Foydalanuvchanlik kuzatuvi — usta yo'li (VALIDATION Manual-Only #2)

**Nega avtomatlashtirib bo'lmaydi:** rejani va kodni yozgan tomon yo'lni qurilishiga ko'ra topadi. O'lchov faqat mahsulotni birinchi marta ko'rayotgan odam bilan ma'noga ega.

**Kim bajaradi:** dasturchi bo'lmagan odam (bozor admini yoki ma'muriyat xodimi)
**Qachon:** demo/pilot tayyorlanganda, go-live'gacha

expected: Bozori yo'q platforma admini tizimga kiradi va yordamsiz "Yangi bozor" ustasiga yetib boradi; 7 qadamni oxirigacha bosib o'tadi; oxirida bozor faol holatda ko'rinadi. To'liq skript `02-18-SUMMARY.md` § "OCHIQ BAND" da. 6-qadam (mobil ≤5 element) va 7-qadam (ruscha yorliq o'ralishi) allaqachon o'lchangan — **1–5 qadamlar qolgan inson ishi**.
result: [pending]

### 2. Real Karmana faylining shakli (VALIDATION Manual-Only #1)

**Nega avtomatlashtirib bo'lmaydi:** `ast` darvozasi generator **modul** mustaqilligini isbotlaydi, **epistemik** mustaqilligini emas. Ma'muriyat `A-12/1` shaklidagi kodlar yoki kutilmagan to'rtinchi ustun bilan kelsa, buni faqat real fayl ochadi.

**Kim bajaradi:** bozor admini (import saytning o'zidan, muhandis kerak emas)
**Qachon:** ma'muriyat hujjatlarni topshirganda

expected: Real fayl `ops/data/karmana/README.md` §7 tekshiruv ro'yxatidan o'tadi; validatsiya xatolari tushunarli va tuzatiladigan; import all-or-nothing ishlaydi.
result: [pending]

### 3. Plan-xarita idroki real qurilmada (VALIDATION Manual-Only #3)

**Kim bajaradi:** bozor admini o'z telefonida
**Qachon:** pilot tayyorlanganda

expected: 600+ rastali xaritada zona chegaralari va rasta holatlari real ekranda ajratiladi; grid o'qilishi qiyin bo'lmaydi.
result: [pending]

### 4. Rekvizit formati bo'yicha buyurtmachi tasdig'i (VALIDATION Manual-Only #4)

**Kim bajaradi:** buyurtmachi (bozor ma'muriyati)
**Qachon:** hujjatlar almashinuvida

expected: STIR raqamlari soni, majburiy maydonlar to'plami va yetishmayotgan maydonlar bo'yicha yozma javob olinadi.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps

Yo'q — bu bandlar bo'shliq emas, **inson ishtirokini talab qiladigan tekshiruvlar**. 2026-08-01 self-service direktivasi bo'yicha ular fazani yoki jarayonni bloklamaydi. `02-VERIFICATION.md` 9/9 must-have ni 0 bloker bilan tasdiqlagan; faza holati `human_needed` aynan shu to'rt band tufayli, muhandislik qarzi tufayli emas.

**Diqqat:** agar 1-band (foydalanuvchanlik kuzatuvi) to'xtash nuqtasini topsa, `REQUIREMENTS.md` dagi MARKET-01 `Pending` ga qaytarilishi kerak — u mexanik natija bilan emas, hukm bilan belgilangan (`02-22-SUMMARY.md`).
