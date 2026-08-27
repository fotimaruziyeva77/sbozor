---
status: partial
phase: 10-landing-sbozor-uz
source: [10-01…10-08 SUMMARY.md (8 fayl)]
mode: autonomous
started: 2026-08-18T05:10:00Z
updated: 2026-08-18T05:30:00Z
---

## Rejim eslatmasi

Avtonom verify (foydalanuvchi topshirig'i). Orkestrator mustaqil o'lchovlari:
mezon darvozasi + landing-surface qayta yugurtirildi, demo-endpoint integratsiya
to'plami docker'da alohida yugurtirildi, prerender HTML uch tilda tekshirildi,
sitemap/robots artefaktlari o'qildi. Real qurilma/deploy o'lchovlari —
`10-HUMAN-UAT.md` da ega/tetik bilan, blocked.

## Current Test

[testing paused — 1 dala bandi ochiq (9); 10-HUMAN-UAT.md da 5 band]

## Tests

### 1. Faza mezonlari bitta buyruqda
expected: `node --test frontend/scripts/phase10-criteria.test.mjs` — 8 test yashil
result: pass
evidence: "Orkestrator MUSTAQIL yugurtirdi (2026-08-18): pass 8 / fail 0. Gate ichidagi uch yugurishdan keyingi to'rtinchi tasdiq."

### 2. Landing yuzasi darvozasi (G-land-1…5)
expected: landing-surface.test.mjs — 25 band yashil (jumladan yangi transition-skan parseri)
result: pass
evidence: "Orkestrator qayta yugurtirdi: pass 25 / not-ok 0. 10-07 da 6 reja-sabotaji + 2 nazorat, har biri aynan o'z bandini qizartirgan."

### 3. Anonim root — landing (redirect EMAS)
expected: `/{locale}` endi login-redirect emas, landing sahifasi; hero sarlavha + «Demo so'rang» CTA uchala tilda
result: pass
evidence: "Prerender HTML tekshirildi: uz-Latn.html / uz-Cyrl.html / ru.html har birida hero sarlavha 1 marta va CTA 1 marta. Build 86/86 marshrut, ENVIRONMENT_FALLBACK 0 (10-07 tuzatishi)."

### 4. Demo-so'rov backend yo'li
expected: anonim POST — rate-limit 5/15daq, honeypot jim 200, telefon normalizatsiya 422, html.escape, sinxron Telegram + halol 502
result: pass
evidence: "Orkestrator docker'da alohida yugurtirdi: tests/integration/test_demo_request.py — 9 passed. 10-01 sabotajlari: escape'siz test qizardi; yolg'on-200 shoxida delivery_failed qizardi."

### 5. Hero 12s sikl + reduced-motion
expected: server final-kadr, sikl faqat ko'rinishda (IO + visibilitychange), reduced-motion'da 0 taymer, GPU-only
result: pass
evidence: "10-05: G-land-2(a–e) testlari; ikki sabotaj (erta return olib tashlash → (a) qizardi; cleanup olib tashlash → (d) qizardi). Davr 13500ms testda literal."

### 6. Demo-forma (klient)
expected: zod grafisiz (69KB tejash), honeypot sr-only, dwell ≥3s, xato matnlari sabab+qadam bilan, G-SUBMIT
result: pass
evidence: "10-04: 11 vitest; B-2 quli sabotaji — apiFetch importi kirsa darvoza qizaradi (o'lchandi). Post-merge 1197/1197."

### 7. SEO infra + maxfiylik
expected: sitemap (hreflang bilan), robots (hosila Disallow), OG PNG, maxfiylik sahifasi 3 tilda
result: pass
evidence: "Artefaktlar o'qildi: sitemap.xml.body — 18 hreflang yozuv; robots.txt.body — 21 Disallow; maxfiylik.html 3 locale'da prerender. JSON-LD Organization+FAQPage 10-07 da."

### 8. Payload — katalog og'irligi yutug'i
expected: provayder refaktoridan keyin anonim sahifa yengil
result: pass
evidence: "10-03 haqiqiy o'lchovi: ildiz JS 287.8→208.4 KB gz (−79.4), HTML(ru) 32.3→8.0 KB gz; dashboard nazorati o'zgarishsiz. HUMAN-UAT #2 SHU dalil bilan yopilgan."

### 9. Lighthouse ≥95 / LCP <1.5s / 60fps / jonli Telegram / kirill idroki / yurist
expected: real qurilma va deploy o'lchovlari — har biri SON bilan
result: blocked
blocked_by: physical-device
reason: "Besh band 10-HUMAN-UAT.md da ega/tetik bilan (ijrochi: №1/№3 deploy'da; mahsulot egasi: №4 jonli Telegram, №5 kirill ko'rigi pilot haftasi, №6 yurist go-live). LAND-05 shu sababdan halol Blocked."

### 10. Gate byudjetlari
expected: to'liq gate < 2300; gate:fast yangi chegara o'lchov bilan asoslangan
result: pass
evidence: "10-08 W0-13: gate 2227/1856/1760 s (chegara 2300 qoladi, zaxira 73 s — deferred'da tor deb nomlangan); gate:fast 249/175/175 → chegara 300 (rejadagi 250 o'lchov bilan bekor — 0,4% zaxira qolardi). Uch yaroqsiz urinish jurnalda."

## Summary

total: 10
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps

[none — kod nuqsoni topilmadi]

## Verify stolidagi qarorlar (avtonom)

| # | Band | Qaror | Sabab |
|---|------|-------|-------|
| 1 | LAND-05 Blocked | QABUL | Lighthouse/LCP CI'da o'lchanmaydi (paket taqiqi); mexanik proksilar yashil, son deploy'da |
| 2 | gate 73 s zaxira | QABUL, deferred | 9-fazadagi 41 s dan yaxshiroq, lekin tor; egasi keyingi faza rejalovchisi |
| 3 | gate:fast 300 (reja 250 emas) | QABUL | O'lchov 249 rejani bekor qildi — W0-13 formula, jurnal literal; jimgina emas |
| 4 | Flake №12 uchinchi marta (yaroqsiz urinish sababi) | QAYD | 5-faza mezon faylining 1/70 flake'i; scope tashqarisida, deferred'da |
| 5 | deferred №14 uchinchi marta | QAYD | SDK asbob nuqsoni; har safar ushlanib qaytarilgan — GSD'ga upstream masala |
| 6 | SECURITY.md yo'q (10) | OCHIQ | Anonim endpoint threat modeli PLAN ichida (T-10-04 html.escape testda); alohida secure-phase go-live ro'yxatida 08 bilan birga |
