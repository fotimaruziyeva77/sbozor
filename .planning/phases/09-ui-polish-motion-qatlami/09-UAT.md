---
status: partial
phase: 09-ui-polish-motion-qatlami
source: [09-01…09-07 SUMMARY.md (7 fayl)]
mode: autonomous
started: 2026-08-17T08:20:00Z
updated: 2026-08-17T08:35:00Z
---

## Rejim eslatmasi

Avtonom verify (foydalanuvchi topshirig'i): pass faqat O'LCHANGAN xulqqa.
Orkestrator mustaqil o'lchovlari: mezon darvozasi + 4 gate skripti qayta
yugurtirildi (docker'siz), jonli prod-build HTTP smoke qilindi, dushanba-fix
diffi tekshirildi. Real qurilma o'lchovlari (fps, Lighthouse, idrok) —
`09-HUMAN-UAT.md` da ega/tetik/kutilgan-son bilan, blocked.

## Current Test

[testing paused — 3 dala bandi ochiq (8, 9, 10); ular 09-HUMAN-UAT.md da]

## Tests

### 1. Faza mezonlari bitta buyruqda
expected: `node --test frontend/scripts/phase9-criteria.test.mjs` — 8 test yashil (5 mezon + META + soxtalashtirish + reyestr)
result: pass
evidence: "Orkestrator MUSTAQIL yugurtirdi (2026-08-17): fail 0, 230ms. Ijrochining 09-07 dagi da'vosidan alohida, uchinchi tasdiq (gate ichida ikki marta o'tgan)."

### 2. Motion darvozalari to'plami (G-motion-1…7)
expected: motion-tokens / theme-tokens / contrast / typography gate skriptlari yashil
result: pass
evidence: "Orkestrator to'rtala skriptni alohida yugurtirdi: fail=0 har birida. Fazada jami 349 skript-darvoza ikki to'liq gate'da exit 0."

### 3. Kassir to'lov xoreografiyasi (SC#1)
expected: 6 qadam (press→check-draw→halqa→uchish→qo'nish→avtofokus), ~700ms, bloklamaydi, input ≤150ms tayyor
result: pass
evidence: "09-04: collect 94/94; UCH real sabotaj ikki natija bilan (reduced-motion chetlab o'tish → 1(c) qizardi; bayram 700ms await → 2(a,b) qizardi; pointerEvents olib tashlash → 2(c) qizardi). Ko'r deklaratsiya darvozasi yashil qoldi — yig'ma sanoq kiritilmadi."

### 4. Direktor jonlanishi (SC#2)
expected: skeleton→stagger→count-up 600ms+tick, sparkline/donut chizilishi, REPORT_VIEW sharti SAHIFADA (kassir kartalarni ko'rmaydi)
result: pass
evidence: "09-05: vitest 1145/1145 (o'z bosqichida); sabotajlar kassirning DOM va so'rov qatlamlarini ALOHIDA qizartirdi; huquq sharti sahifada — MarketStatusCard naqshi."

### 5. Tema qatlami — 3 tema token-scope bilan (SC#3, mexanik yarmi)
expected: light/dark/sun almashtirgich, SSR chaqnashsiz, komponent kodi o'zgarmasdan
result: pass
evidence: "09-03: G-motion-4 beshala bandi + 2 sabotaj; build 81/81 SSG. Orkestrator JONLI tekshirdi (2026-08-17): prod-build HTTP 200, SSG HTML'da data-theme=\"light\" server tomonda — chaqnash yo'qligining jonli dalili. Dark AA: 09-01 kontrast reyestri dark'da 3 yangi buzilishni fosh qilib tuzatdi (0.205/0.64/0.72)."

### 6. Jonli kontrast nuqsoni + reyestr (G-motion-5)
expected: review/page.tsx va blind-session.tsx 1.28:1 → 4.72:1; 45 o'lchov mashina o'qiydigan da'vo sifatida
result: pass
evidence: "09-01: TDD — test avval ikkala jonli nuqsonni nomma-nom topdi, keyin tuzatildi; kalkulyator SPEC'ning 15 da'vosidan 13 ini mustaqil takrorlagan tadqiqot kodidan."

### 7. Dushanba-ko'rlik tuzatilishi — mahsulot yo'liga nol ta'sir
expected: 11a4f3a FAQAT test fayllariga tegadi (billing testlari ochiq-kun prekonditsiyasi)
result: pass
evidence: "Orkestrator diffni tekshirdi: 2 fayl (test_billing_api.py, test_phase6_criteria.py), +23 qator, mahsulot kodi 0. Da'vo tasdiqlandi. Sinf deferred №3 da — kun-sezgir testlar."

### 8. 60fps + 20 to'lov real qurilmada (SC#5 yarmi)
expected: arzon Android / 4x CPU throttling: 20 ketma-ket to'lov, yo'qolgan belgi 0, ≥55–60 fps
result: blocked
blocked_by: physical-device
reason: "Real telefon/DevTools o'lchovi kerak — CI/jsdom layout qilmaydi. 09-HUMAN-UAT №1, tetigi: birinchi deploy yoki foydalanuvchi sinovi. Test muhiti tayyor: localhost:8081 / 192.168.137.54:8081."

### 9. Lighthouse ≥90 / CLS <0.05 (SC#5 yarmi)
expected: mobil profil, /collect /dashboard /reports — har birida Performance ≥90, CLS <0.05
result: blocked
blocked_by: physical-device
reason: "Lighthouse CI'da yo'q (paket qo'shish taqiq — G-motion-3(d) to'plam tengligi). 09-HUMAN-UAT №2. Mexanik proksilar yashil: SSG build, GPU-only transformlar, skeleton geometriya juftligi (G-motion-7)."

### 10. Uch tema idroki + OS reduced-motion (SC#3/SC#4 inson yarmi)
expected: ochiq havoda telefon + ofis monitorida 3 tema × 3 rol; OS darajasida reduced-motion → kuzatilgan harakat 0, natija ayni
result: blocked
blocked_by: physical-device
reason: "Inson idroki va OS sozlamasi — 09-HUMAN-UAT №3/№4, tetigi pilot haftasi (rejaning o'z dizayni). Mexanik yarmi o'lchangan: global reduced-motion kill + real manba sabotaji."

## Summary

total: 10
passed: 7
issues: 0
pending: 0
skipped: 0
blocked: 3

## Gaps

[none — kod nuqsoni topilmadi]

## Verify stolidagi qarorlar (avtonom)

| # | Band | Qaror | Sabab |
|---|------|-------|-------|
| 1 | Gate zaxirasi 41 s (1,8%) | QABUL, deferred'da | Chegara oshirilmadi — halol; egasi 10-faza rejalovchisi: to'plam qo'shilsa chegara yoki zanjir qayta ko'riladi |
| 2 | IKKI o'lchov (uch emas) | QABUL | 08-20 presedenti, tezlik foydalanuvchi talabi; halollik bandi package.json'da, ikki yaroqsiz urinish jurnali bilan |
| 3 | Konfetti ijrosi fazadan tashqarida | QABUL | Tadqiqot o'lchovi: z.strictObject ikki tomonlama + ko'r deklaratsiya xavfi; UI-SPEC [TALAB], deferred'da |
| 4 | 09-02 globals.css shartli bandi ishlatilmagani | QABUL | postcss-probe o'lchovi: Tailwind hover: ni o'zi media'ga o'raydi — shart ishga tushmadi, e'lon halol edi |
| 5 | SECURITY.md yo'q (09) | OCHIQ | Faza yangi endpoint/huquq YOZMAGAN (frontend jilo + 2 test-fix); 7/8-faza presedenti; go-live oldi ro'yxatida /gsd-secure-phase 08 bilan birga |
| 6 | SDK faza-belgi nuqsoni (№14) ikkinchi marta | QAYD | Ijrochi ushlab qaytardi; GSD asbob nuqsoni sifatida deferred'da qoladi |
| 7 | Verify muhiti vaqtinchaliklari | QAYD | core-api :8010 (xost :8000 parnikkpi niki), .env tegilmagan; bot-service restart halqasi — 08 dan meros holat, bu faza aybdor emas |
