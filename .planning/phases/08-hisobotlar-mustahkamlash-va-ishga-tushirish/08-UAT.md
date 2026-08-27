---
status: partial
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
source: [08-01…08-20 SUMMARY.md (20 fayl)]
mode: autonomous
started: 2026-08-16T18:35:00Z
updated: 2026-08-16T18:52:00Z
---

## Rejim eslatmasi

Foydalanuvchi topshirig'i (2026-08-16): verify AVTONOM yuritiladi — orkestrator
har testga O'Z tavsiyasini belgilaydi va sababini yozadi. Faqat
foydalanuvchidagina bo'lgan haqiqiy ma'lumot (real bozor, jonli NVR, byudjet)
talab qilingan bandlar `blocked` bo'lib ochiq qoladi — ular allaqachon
`08-HUMAN-UAT.md` da egasi va tetigi bilan ro'yxatda.

Dalil siyosati: `pass` faqat O'LCHANGAN xulqqa qo'yiladi (sabotaj o'lchovi /
darvoza yugurishi / mustaqil qayta yugurish). «Kod shunday yozilgan» dalil emas.

## Current Test

[testing paused — 3 dala bandi ochiq (1, 12, 14); ular 08-HUMAN-UAT.md da egasi/tetigi bilan]

## Tests

### 1. Sovuq start — to'liq stek (`npm run up`, 10 servis)
expected: Toza mashinada `npm run up` → `docker compose ps` da 10 servis `running` (db, cache, storage, core-api, worker, scheduler, cv-service, bot-service, go2rtc, backup)
result: blocked
blocked_by: prior-phase
reason: "cv-service uchun CV_MODEL_PATH ONNX artefakti yo'q — konteyner crash-loop (o'lchangan: ~1 s interval, ~80 % CPU). Band 08-HUMAN-UAT.md №5 da egasi (Ops/dasturchi) va tetigi (birinchi deploy) bilan. Qolgan 9 servisning jonli holati bugungi xostda kuzatildi (7+ soat up, core-api healthy), lekin bu TOZA start emas."

### 2. Direktor `/reports` sahifasini ochadi
expected: Navigatsiyada «Hisobotlar» (17-yozuv), sahifada 4 blok, davr tanlagichi maksimum KECHA, uchala locale'da SSG
result: pass
evidence: "08-17: vitest 1079/1110 yashil, nav reyestri darvozasi 16→17 joy qulfi bilan (`reports === reconciliation + 1`), `next build` uchala locale'da EXIT 0; G-37 sabotaji rejaning literal kutilmasini berdi (a yashil / c qizil / e qizil)."

### 3. Tushum hisoboti — davr va yig'indi SERVERDAN
expected: Ko'rinadigan davr server javobidan chiziladi (so'ralganidan emas), yig'indi serverniki, klient hech nima hisoblamaydi
result: pass
evidence: "08-13: RED→GREEN TDD; sabotaj darsi — «ko'rinadigan matn» asserti `textContent` minus `.sr-only` ga tuzatildi va sabotaj shundan keyin qizardi. Pitfall 14: `<th>` ikkinchi qatori bilan «patta kuni / to'lov kuni» ajratildi."

### 4. Qarzdorlik reyestri — nomsiz sotuvchi halol ko'rinadi
expected: Topilmagan ism BO'SH katak, lekin skrinriderda NOMLANGAN; «{shown} qatordan {total}» jumlasi yig'indi bilan bir joyda
result: pass
evidence: "08-13: ikkala shakl sabotaji o'lchandi (yalang tire ham, sr-only saqlangan tire ham qizaradi)."

### 5. Nomuvofiqlik arxivi va aniqlik bloki — halol «o'lchanmagan» holat
expected: AI-02 jumlasi manbada aynan 1 marta, bezaksiz (tone="warning" 0, role="alert" emas); `measured=false` da ConfusionMatrix chiziladi va sabab USTIGA qo'shiladi
result: pass
evidence: "08-15: uch sabotaj, ikkitasi testning o'zidagi yolg'on-yashilni fosh qildi va testda tuzatildi. Ongli chetlanish hujjatlangan: `min_sample` 1 marta o'qiladi (G-43(d) `{min}` platsholderi talab qiladi), mezon maqsadi 3 aniqroq assert bilan qulflangan (taqqoslash operatori 0, MIN_SAMPLE konstanta 0, `?? 0` 0) — klient chegara HISOBLAMAYDI."

### 6. Excel eksport — bitta bosish
expected: To'rtala hisobot `.xlsx` bo'lib yuklab olinadi; fayl nomi serverda, ASCII; davr faylning birinchi qatorida; bayt-determinik
result: pass
evidence: "08-09: eksport tugmasi YAGONA yuklab olish yo'li, poyga qulfi bilan; 08-12: 4 quruvchi + 4 GET marshruti RED→GREEN, `ast` darvozasi grep o'rniga (3→5 funksiya)."

### 7. Shaxsiy eksport auditi — kim yuklaganini tizim biladi
expected: `debtors.xlsx` faqat `VENDOR_VIEW` bilan ochiladi va AYNAN BITTA `audit_read` yozadi; kassir/nazoratchi uchala JSON marshrutdan 403 oladi
result: pass
evidence: "08-12 KRITIK topilma: majburiy sabotaj (debtors.xlsx ni «nomashaxsiy» ro'yxatga ko'chirish) 854 tenancy testi yashil holda JIM O'TDI — darvoza ishlamasdi. Tuzatish holatda: `test_no_non_personal_claim_survives_a_vendor_data_guard` tasnifni mahsulot e'loniga mexanik bog'laydi; sabotaj qayta o'lchandi va endi qizaradi. 08-07: audit sanog'i sabotaji 3 testni qizartirdi."

### 8. Solishtiruv sahifasi `/reports/compare`
expected: Uch farq sinfi badge bilan, `match` simda EMAS (null), DL-6 destruktiv tasdiq ConfirmDialog bilan, sanoqlar serverdan
result: pass
evidence: "08-16: `_wire_diff_class()` — `match` simga chiqsa 287 mos qator badge olib 13 farqni ko'mardi (rejada YO'Q edi, o'lchab topildi); 08-18: yetti sabotaj, `has_ledger` sabotaji sahifa darvozasidagi ikki ko'r nuqtani ochdi va testda tuzatildi; G-42(a) darvozasining o'zi registr sababli Set(0) qaytarayotgani topilib kengaytirildi. Orkestrator integratsiya tekshiruvi: `matched_count` serverdan (compare-table.tsx:223), `diffClass===null` badge chizmaydi (diff-cell.tsx:112)."

### 9. Daftar importi — all-or-nothing
expected: Xato qatorli fayl 422 + qator darajasidagi sabablar bilan rad etiladi va HECH NIMA yozilmaydi; to'g'ri fayl idempotent upsert
result: pass
evidence: "08-14: sabotaj o'lchovi — validator yo'li o'chirilganda 200 + 2 qator bazaga yozildi (`assert 200 == 422` qizardi), ya'ni himoya haqiqatan validatorga tayanadi. Audit ikki qatlamga ajratildi va ikkalasi o'lchandi: yig'ma source='app' AYNAN 1, qator source='db_trigger' AYNAN 30 — trigger o'chirish yo'li RAD ETILDI."

### 10. Tenant chegarasi — A bozor direktori B ni ko'rmaydi
expected: Hisobot va eksport marshrutlarida cross-tenant so'rov bo'sh/403; yopiq to'plam testlari marshrut sonini qulflaydi
result: pass
evidence: "tests/tenancy 764→854→887: uch mustaqil yugurish EXIT 0 (08-07 close-out, 08-12, 08-16); `/reports` prefiksi yopiq to'plam bilan qulflangan, son test NOMIDA."

### 11. Zaxira mexanizmi — heartbeat va tiklash mashqi
expected: `backup` konteneri idempotent tsikl + yurak urishi; heartbeat yo'qolsa 26 soatda `backup_stale` (CRITICAL, never_suppressed); pg_dump toza serverga tiklanadi, GRANT qadami hujjatlangan
result: pass
evidence: "08-05: quvursiz zaxira + statik darvoza; 08-08: tiklash mashqi CI qatlami — o'lchangan fakt: tiklangan baza 44 jadval / 83 policy / 0 GRANT, shuning uchun §4.4 to'rt qadamda GRANT majburiy; heartbeat→self-check→backup_stale zanjiri testda o'lchandi."

### 12. Offsite S3 — real zanjir
expected: `RESTIC_REPOSITORY` to'ldirilgan, birinchi zaxira offsite'ga yozilgan, parol ikki joyda/ikki odamda
result: blocked
blocked_by: third-party
reason: "Byudjet va provayder qarori buyurtmachiniki — .env da RESTIC* kalitlari YO'Q (o'lchangan: grep -c = 0), .env.example:240 bo'sh. Bu holatda backup_unconfigured → 26 soatdan keyin backup_stale (CRITICAL) chiqadi va uni o'chirish TAQIQ — bandning ochiqligini ko'rsatuvchi yagona signal. 08-HUMAN-UAT №2/№3, deferred №11."

### 13. Go-live runbook va shakl darvozasi
expected: `ops/docs/go-live.md` har buyruq blokidan keyin «Kutilgan natija:» bilan; `test_runbook_shape.py` 5 test; 08-HUMAN-UAT 6 band egasi/tetigi bilan
result: pass
evidence: "08-19: ikki sabotaj aynan mo'ljaldagi bandni qizartirdi (ikkinchisi RESTIC_PASSWORD kaliti faylda QOLGAN holda — darvoza bandni o'lchaydi, kalit eslatilishini emas); orkestrator artefaktni o'zi o'qib tasdiqladi (checkpoint approved)."

### 14. Uch tilning tabiiyligi — ona tili ko'rigi
expected: Kassir/nazoratchi/admin har biri O'Z oqimini uch tilda bajaradi; nuqsonlar KALIT NOMI bilan yoziladi; O-01/O-03/O-07 atama qarorlari yopiladi
result: blocked
blocked_by: other
reason: "Ona tilida so'zlashuvchilar bilan jonli sessiya kerak — mexanik parity (i18n:check 1349×3, glossary, error-codes) yashil, lekin matnning TABIIYLIGI mexanik o'lchanmaydi. 08-HUMAN-UAT №4, egasi mahsulot egasi, tetigi pilot tayyorgarligi haftasi."

### 15. Faza mezonlari bitta buyruqda
expected: `pytest tests/integration/test_phase8_criteria.py` — 9 test yashil (orkestratorning MUSTAQIL yugurishi, ijrochi da'vosiga tayanmasdan)
result: pass
evidence: "Orkestrator 2026-08-16 23:37 da o'zi yugurtirdi: 9 passed, EXIT 0 — ijrochining 08-20 dagi da'vosi mustaqil tasdiqlandi. Bu gate ichidagi ikkita yugurishdan keyingi UCHINCHI mustaqil o'lchov."

## Summary

total: 15
passed: 12
issues: 0
pending: 0
skipped: 0
blocked: 3

## Gaps

[none — kod nuqsoni topilmadi]

## Verify stolidagi qarorlar (avtonom rejimda qabul qilindi)

| # | Band | Qaror | Sabab |
|---|------|-------|-------|
| 1 | 08-15 `min_sample` chetlanishi | QABUL | Reja o'z-o'ziga zid edi (G-43(d) `{min}` platsholderi vs «token 0 marta»); maqsad 3 aniqroq assert bilan qulflangan |
| 2 | 08-18 «Sotuvchi» ustuni yo'q | QABUL, savol OCHIQ | `threeWayRowSchema` strictObject — texnik to'g'ri; «direktor farqni ISM bilan ko'rishi kerakmi?» mahsulot savoli sifatida deferred №9 da qoldi (buyurtmachi hal qiladi) |
| 3 | Marshrut nomlari (/debtors, /anomalies, /compare) | QABUL | Klient kontrakti (08-03) haqiqat manbai; uch marta izchil qo'llandi (08-07/12/14/16) |
| 4 | Gate byudjeti IKKI o'lchov bilan | QABUL | Tezlik foydalanuvchi talabi edi; halollik bandi package.json + VALIDATION + SUMMARY da bir xil; 1909/1842 s < 2300 s chegara |
| 5 | FOUND-07 Blocked | QABUL | Mexanizm uch qatlamda yashil; konfiguratsiya buyurtmachi byudjetiga bog'liq — halol Blocked, yashirilmagan |
| 6 | AI-02 Blocked (5-faza merosi) | QABUL | 8-faza o'z yuzasini halol qurdi (aniqlik bloki «o'lchanmagan» deydi); modelni o'lchash oltin to'plam + real ONNX talab qiladi — dala bandi |
| 7 | SECURITY.md yo'q (08) | OCHIQ BAND | enforcement=true, lekin presedent: 7-faza ham SECURITY'siz yopilgan; 8-faza ichki darvozalari sabotaj bilan o'lchangan. Tavsiya: go-live'dan oldin `/gsd-secure-phase 08` (shaxsiy ma'lumot eksport yuzalari qo'shildi) — 08-HUMAN-UAT yo'lida |
| 8 | Deferred №12 (1/70 flake, 5-faza testi) | QABUL | Mexanizmi o'lchangan, scope boundary hurmat qilingan; 5-fazaning bandi |
| 9 | Deferred №14 (SDK faza belgisini o'zi [x] qilgani) | QAYD | Asbob nuqsoni, qaytarilgan; transition ENDI legitim ravishda belgini qo'yadi (verify huquqi) |
