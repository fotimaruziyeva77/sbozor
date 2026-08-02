# Requirements: SBOZOR

**Defined:** 2026-07-29
**Core Value:** Bozor ma'muriyati har bir band rastadan patta to'liq yig'ilayotganini raqamlar va rasm-dalil bilan ko'radi — "band, lekin to'lovsiz" rastalar kunlik hisobotda avtomatik fosh bo'ladi.

## v1 Requirements

Birinchi reliz (Karmana pilot, 12 hafta) talablari. Har biri roadmap fazalariga bog'lanadi.

### Poydevor (FOUND)

- [ ] **FOUND-01**: Foydalanuvchi rolga mos kirish oladi — platforma admini, direktor, bozor admini, kassir, nazoratchi (RBAC); har rol faqat o'z bozori ma'lumotini ko'radi
- [ ] **FOUND-02**: Tenant izolyatsiyasi: har jadvalda `market_id` + Postgres RLS; cross-tenant kirish avtomatik test bilan isbotlangan
- [ ] **FOUND-03**: Har moliyaviy/ma'muriy harakat audit jurnaliga yoziladi (kim, qachon, nima, eski→yangi); jurnal o'zgartirib bo'lmaydigan
- [ ] **FOUND-04**: Interfeys 3 tilda (o'zbek-lotin asosiy, o'zbek-kirill, rus); til bir bosishda almashadi
- [ ] **FOUND-05**: Biznes-kun Asia/Tashkent bo'yicha hisoblanadi (`business_date`); pul qiymatlari butun so'mda (BIGINT)
- [ ] **FOUND-06**: Tizim o'zini kuzatadi: kamera offline, o'tkazib yuborilgan snapshot, backup xatosi — platforma adminiga Telegram-alert; xatolar Sentry'da
- [ ] **FOUND-07**: Kunlik avtomatik backup (Postgres + obyekt-ombor) boshqa lokatsiyaga; tiklash mashqi kamida bir marta o'tkazilgan

### Bozor boshqaruvi (MARKET)

- [x] **MARKET-01**: Platforma admini "Yangi bozor" ustasi orqali bozorni kod yozmasdan kiritadi: rekvizitlar → zonalar → rastalar → toifalar → tariflar → kameralar → kamera zonalari → snapshot jadvali
- [x] **MARKET-02**: Bozor admini rastalar reestrini yuritadi: raqam, zona/qator, mahsulot toifasi, holat (faol/ta'mirda/yopiq), sotuvchi biriktirish
- [x] **MARKET-03**: Tariflar tarixiy saqlanadi (qaysi sanadan qaysi narx) — o'tmishdagi hisoblar keyingi narx o'zgarishidan buzilmaydi
- [x] **MARKET-04**: Bozor admini sotuvchilar reestrini yuritadi (F.I.Sh., telefon) va rasta biriktirish davrlarini boshqaradi
- [x] **MARKET-05**: Bozor admini ishlamaydigan/bayram kunlarini belgilaydi — o'sha kunlarga patta hisoblanmaydi
- [x] **MARKET-06**: Sxematik plan-xarita: rastalar zona bo'yicha rangli grid (yashil bo'sh, ko'k to'langan, qizil qarzdor, sariq nomuvofiq); rasta bosilganda karta (dalil-rasm bilan) ochiladi
- [x] **MARKET-07**: Bozor admini ma'muriyat bergan xodimlar ro'yxatini bitta fayl bilan yuklaydi (F.I.Sh., telefon, rol); tizim hisoblarni rollar bilan yaratadi, telefon raqamlarini E.164 ga normallaydi, dublikatni rad etadi va vaqtinchalik parollarni beradi — qo'lda birma-bir kiritish shart emas

### Kamera va suratga olish (CAM)

- [ ] **CAM-01**: Bozor admini kameralarni qo'shadi/sozlaydi; RTSP ma'lumotlari shifrlangan saqlanadi; "ulanishni tekshirish" tugmasi ishlaydi
- [ ] **CAM-02**: Server NVR'ga faqat WireGuard VPN orqali kiradi; NVR internetga to'g'ridan-to'g'ri ochilmaydi
- [ ] **CAM-03**: Direktor/admin panelda jonli kamera tasvirini ko'radi (go2rtc, avtorizatsiya ortida)
- [ ] **CAM-04**: Snapshot jadvali har bozor uchun sozlanadi va mavsumiy profilni qo'llaydi (standart: 06:00–08:00 har 30 daq + 16:00, 18:00)
- [ ] **CAM-05**: Rejalashtirilgan kadr olish idempotent va retry'li; o'tkazib yuborilgan slot jurnalda ko'rinadi va alert yuboradi
- [ ] **CAM-06**: Har kadr sifat filtridan o'tadi (qorong'i/buzuq/bo'sh kadr belgilanadi, `light_mode` saqlanadi) — yaroqsiz kadr billing'ga ta'sir qilmaydi
- [ ] **CAM-07**: Kadrlar S3-mos omborda (SeaweedFS) bozor/kamera/sana bo'yicha saqlanadi; 90 kun to'liq, keyin siqilgan 1 yil (sozlanadigan)
- [ ] **CAM-08**: Admin **faqat** NVR manzili + login/parolni kiritadi; tizim Hikvision ISAPI orqali qurilmani aniqlaydi, barcha kanallarni sanab chiqadi va kameralarni (nom, kanal, asosiy/sub oqim URL'i) avtomat yaratadi. Qayta skanerlash idempotent (yangi kanal qo'shiladi, yo'qolgani `offline`, mavjudi tegilmaydi). Ulanish xatosi **sababi va tuzatish yo'li** bilan ko'rsatiladi: parol xato / NVR soati >5 daq farqi → NTP / firmware `digest/basic` talab qiladi / kanal offline / sessiya limitiga yetildi
- [ ] **CAM-09**: Simulyatsiya qilingan Hikvision NVR (ISAPI mock + go2rtc RTSP manbasi) compose profili sifatida mavjud; kamera kashfiyoti, ulanish testi, jonli ko'rish va kadr olish yo'li real uskunasiz uchidan-uchiga ishlaydi va CI'da o'lchanadi

### AI tahlil (AI)

- [ ] **AI-01**: Bozor admini har kamera kadrida rasta zonalarini poligon qilib chizadi (normalangan 0..1 koordinatalar, versiyalangan); bitta rasta bir necha kameraga bog'lanishi mumkin
- [ ] **AI-02**: Detektor (RF-DETR Apache-2.0, ONNX Runtime CPU) har zonani band/bo'sh/noaniq deb baholaydi; AI natijasi confidence bilan saqlanadi va hech qachon o'zgartirilmaydi (nazoratchi qarori alohida yozuv)
- [ ] **AI-03**: Nazoratchi noaniq navbatini ko'rib chiqadi — kunlik byudjet va ustuvorlik bilan, "hammasini tasdiqlash" tugmasisiz; tasdiqlangan javoblar fine-tuning dataseti bo'ladi
- [ ] **AI-04**: Ko'r tasodifiy audit navbati: nazoratchi AI javobini ko'rmasdan tasodifiy tanlangan zonalarni baholaydi — aniqlik hisoboti faqat shu namunadan olinadi
- [ ] **AI-05**: Rasta bir necha kamerada ko'rinsa — birortasi "band" desa rasta band (agregatsiya qoidasi)
- [ ] **AI-06**: Kun oxirigacha tasdiqlanmagan noaniq → "bo'sh" (hisobotda alohida belgi bilan)

### Billing (BILL)

- [ ] **BILL-01**: Kun yopilishida band rastaga (kamida 2 snapshotda band, yoki 1 snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq kunlik patta hisoblanadi; job idempotent — qayta ishga tushirish dublikat yaratmaydi (`UNIQUE(market_id, stall_id, business_date)`)
- [ ] **BILL-02**: Har hisob yozuvi dalil-kadrlarga bog'langan; yaratilgach o'zgartirilmaydi — tuzatish faqat sabab ko'rsatilgan `charge_adjustments` yozuvi orqali
- [ ] **BILL-03**: Qarz faqat biriktirilgan sotuvchiga yoziladi; qoldiq har doim hisoblanadigan ko'rinish (hisoblar − to'lovlar), saqlangan balans ustuni emas
- [ ] **BILL-04**: Biriktirilmagan rasta band ko'rinsa — hisob yozilmaydi, "ro'yxatga olinmagan savdo" anomaliyasi sifatida hisobotga tushadi
- [ ] **BILL-05**: Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi tarif + eski qarz) ko'radi — bu jonli projection, yozilgan hisob emas

### Kassir (CASH)

- [ ] **CASH-01**: Kassir telefonda rastani raqam bo'yicha topadi → summa tarifdan avtomatik → to'lov turi (naqd/terminal) → ≤3 bosishda tasdiqlaydi
- [ ] **CASH-02**: Kassir summani faqat sabab-kod bilan o'zgartira oladi; har o'zgartirish auditda ko'rinadi
- [ ] **CASH-03**: To'lov kiritish idempotent (takror bosish dublikat yaratmaydi); to'lov tuzatish faqat storno + qayta kiritish orqali, o'chirish/tahrirlash yo'q
- [ ] **CASH-04**: Kassir smenani ochadi/yopadi; yopishda yig'ilgan naqdni ko'r (tizim summasini ko'rmasdan) deklaratsiya qiladi; tizim farqni (variance) hisoblab direktor hisobotiga chiqaradi
- [ ] **CASH-05**: To'lov kiritilishi bilan sotuvchiga Telegram orqali zudlik push-kvitansiya boradi (summa, rasta, kassir, vaqt)

### Nomuvofiqlik va hisobotlar (RECON)

- [ ] **RECON-01**: Kunlik nomuvofiqlik hisoboti: "band, lekin to'lovsiz" rastalar + "ro'yxatga olinmagan savdo" anomaliyalari, rasm-dalil havolalari bilan
- [ ] **RECON-02**: Har nomuvofiqlik case sifatida yuritiladi: mas'ul, holat (yangi/ko'rilmoqda/asosli/asossiz), yechim; hit-rate metrikasi hisoblanadi
- [ ] **RECON-03**: Direktor ertalab dayjesta oladi (kechagi tushum, bandlik %, TOP-10 qarzdor), kechqurun nomuvofiqlik xabarini oladi
- [ ] **RECON-04**: Davr bo'yicha hisobotlar: tushum (kunlik/oylik), qarzdorlik reestri, nomuvofiqlik arxivi — har biri Excel (.xlsx) yuklab olinadi
- [ ] **RECON-05**: AI aniqlik hisoboti: ko'r audit namunasidan, xatolik turlari ajratilgan ("band deb xato" = nizo xavfi, "bo'sh deb xato" = yo'qotish)
- [ ] **RECON-06**: Har rol bosh ekranida o'ziga mos bitta asosiy ko'rsatkich (direktor: bugungi tushum; nazoratchi: kutayotgan navbat; kassir: bugungi yig'im)

### Telegram-bot (BOT)

- [ ] **BOT-01**: Sotuvchi botga telefon raqamini contact ulashish orqali tasdiqlab ulanadi — raqam admin kiritgan reestrga mos bo'lsa
- [ ] **BOT-02**: Sotuvchi botda qoldiq/qarz va to'lov tarixini ko'radi
- [ ] **BOT-03**: Qarz N kundan oshsa sotuvchiga avtomatik eslatma (N sozlanadigan; quiet hours hurmat qilinadi)
- [ ] **BOT-04**: Barcha xabarlar outbox orqali throttling bilan yuboriladi; yetkazilganlik holati saqlanadi; botni bloklagan foydalanuvchi belgilanadi

## v2 Requirements

Keyingi relizga qoldirilgan. Kuzatiladi, lekin joriy roadmapda emas.

### Kassir kengaytmalari

- **V2-CASH-01**: Jonli undirish ro'yxati — kassirga "band, hali to'lamagan" rastalar real vaqtda (GAP-06)
- **V2-CASH-02**: Kassir↔zona biriktirish va kassir kesimida samaradorlik statistikasi (GAP-08)
- **V2-CASH-03**: QR/bank o'tkazma to'lov turi + majburiy referens; UzQR/bank ko'chirmasi bilan solishtiruv importi (GAP-09)
- **V2-CASH-04**: Qonuniy to'liq kvitansiya maydonlari (lex.uz 2185), "nofiskal" belgisi bilan; keyin OFD'ga o'tish zamini (GAP-03)
- **V2-CASH-05**: Kassir offline-lite rejimi (navbat + qayta yuborish)

### AI kengaytmalari

- **V2-AI-01**: Kamera siljish/tebranish nazorati — reference kadr bilan avtomatik solishtirish (GAP-16)
- **V2-AI-02**: Qo'lda rejim: kamera ko'rmaydigan ~10% rastalar uchun nazoratchi kunlik band/bo'sh belgilaydi, manba hisobotlarda ajratiladi (GAP-07). V1 da bu rastalar uchun faqat to'lov qaydi ishlaydi, AI hisobi yo'q
- **V2-AI-03**: O'tkazib yuborilgan snapshotni NVR arxividan tiklash (GAP-20)
- **V2-AI-04**: Karmana ma'lumotida RF-DETR fine-tuning

### Jarayon kengaytmalari

- **V2-PROC-01**: Sotuvchi e'tiroz/nizo oqimi — rasmiy appeal jarayoni (GAP-04)
- **V2-PROC-02**: Kun/davr yopish qulfi (period lock)
- **V2-PROC-03**: Qarz eskirish tahlili (aging) va hisobdan chiqarish siyosati
- **V2-PROC-04**: To'liq interaktiv plan-xarita (yuklangan rasmda rastalarni belgilash)
- **V2-PROC-05**: Onlayn to'lov: Payme/Click/Uzum merchant integratsiyasi

## Out of Scope

Aniq chiqarilgan. Qayta qo'shishning oldini olish uchun hujjatlashtirilgan.

| Funksiya | Sabab |
|---------|--------|
| Do'kon ijarasi (yillik shartnoma) | MVP faqat rasta/kunlik patta; alohida modul |
| Avtoturargoh (ANPR), hojatxona, mol bozor modullari | Keyingi bosqich modullari |
| Xaridor super-ilovasi | Strategik, lekin pilot qiymatiga aloqasiz |
| Soliq/OFD, E-bozor integratsiyasi | Davlat bosqichida; v1 kvitansiya "nofiskal" |
| Yuzni aniqlash / biometrik identifikatsiya | Huquqiy xavf (shaxsiy ma'lumot), daromad signali deyarli nol |
| AI natijasidan avtomatik jarima | Ishonch o'ldiradi; AI faqat ko'rsatadi, qaror insonda |
| Hamyon/to'lov-rail mahsuloti | Bank emas, nazorat vositasimiz |
| To'liq VMS/video yozib olish | NVR bor; biz faqat snapshot olamiz |
| Uzluksiz real-time inference | 175 kadr/kun yetadi; xarajat oqlanmaydi |
| Yarim kunlik proratsiya | Buyurtmachi qarori: to'liq patta (2026-07-28) |
| Biriktirilmagan rastani placeholder'ga avtomatik billing | To'lovchisiz qarz ma'nosiz; anomaliya sifatida ko'rsatiladi |
| Kassir leaderboard/gamifikatsiya | Raqobat emas, nazorat kerak |
| To'lov yozuvini tahrirlash/o'chirish | Faqat storno; moliyaviy yaxlitlik |
| Erkin summali to'lov (sababsiz) | Korrupsiya teshigi |
| Sotuvchilar uchun LLM-chatbot | Qiymat yo'q, xarajat bor |

## Traceability

Har v1 talab aynan bitta fazaga biriktirilgan. Phase 0 (dala treki) — tashqi bog'liqlik ishi, v1 REQ-ID biriktirilmagan.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| FOUND-05 | Phase 1 | Pending |
| FOUND-06 | Phase 4 | Pending |
| FOUND-07 | Phase 8 | Pending |
| MARKET-01 | Phase 2 | Done |
| MARKET-02 | Phase 2 | Done |
| MARKET-03 | Phase 2 | Done |
| MARKET-04 | Phase 2 | Done |
| MARKET-05 | Phase 2 | Done |
| MARKET-06 | Phase 2 | Done |
| MARKET-07 | Phase 2 | Done |
| CAM-01 | Phase 3 | Pending |
| CAM-02 | Phase 3 | Pending |
| CAM-03 | Phase 3 | Pending |
| CAM-04 | Phase 4 | Pending |
| CAM-05 | Phase 4 | Pending |
| CAM-06 | Phase 4 | Pending |
| CAM-07 | Phase 4 | Pending |
| CAM-08 | Phase 3 | Pending |
| CAM-09 | Phase 3 | Pending |
| AI-01 | Phase 5 | Pending |
| AI-02 | Phase 5 | Pending |
| AI-03 | Phase 5 | Pending |
| AI-04 | Phase 5 | Pending |
| AI-05 | Phase 5 | Pending |
| AI-06 | Phase 5 | Pending |
| BILL-01 | Phase 6 | Pending |
| BILL-02 | Phase 6 | Pending |
| BILL-03 | Phase 6 | Pending |
| BILL-04 | Phase 6 | Pending |
| BILL-05 | Phase 6 | Pending |
| CASH-01 | Phase 6 | Pending |
| CASH-02 | Phase 6 | Pending |
| CASH-03 | Phase 6 | Pending |
| CASH-04 | Phase 6 | Pending |
| CASH-05 | Phase 7 | Pending |
| RECON-01 | Phase 7 | Pending |
| RECON-02 | Phase 7 | Pending |
| RECON-03 | Phase 7 | Pending |
| RECON-04 | Phase 8 | Pending |
| RECON-05 | Phase 8 | Pending |
| RECON-06 | Phase 7 | Pending |
| BOT-01 | Phase 7 | Pending |
| BOT-02 | Phase 7 | Pending |
| BOT-03 | Phase 7 | Pending |
| BOT-04 | Phase 7 | Pending |

**Belgilash qoidasi va uning chegarasi** (2026-08-02, 2-faza yopish to'lqini —
`02-22`). Bu jadvaldagi belgi **talab MATNI** bo'yicha qo'yiladi: band `Done`
bo'ladi faqat o'sha talabning o'z jumlasi o'lchangan test bilan qoplangan va
unga qarshi ochiq bloklovchi qolmagan bo'lsa. Belgi «faza to'liq yopildi»
degani EMAS — va bu farq ataylab ko'rsatiladi, chunki 2-fazada uni
chalkashtirish mumkin bo'lgan uchta joy bor:

1. **Real ma'lumot sharti** — «Karmananing real rasta/tarif/sotuvchi
   ma'lumoti tizimda yashaydi» — birorta MARKET bandining matnida YO'Q. U
   `ROADMAP.md` §"Phase 2" ning «Real ma'lumot haqida» izohida qayta
   ta'riflangan (2026-08-01: fazaning yetkazib berish mahsuloti — import
   qobiliyati, ma'lum bir fayl emas), holati esa
   `phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-VALIDATION.md` da
   (`nyquist_compliant` bayrog'i, `02-23` rejasi) yuritiladi — bu yerda emas.
2. **MARKET-01 ning kamera, kamera-zonasi va kadr jadvali qadamlari**
   `ROADMAP.md` §"Phase 2" ning **Note** bandi bo'yicha keyingi fazalarda
   ulanadi. 2-faza ustaning rekvizit → zona → rasta → toifa → tarif zanjirini
   yetkazadi va o'lchanadigan narsa aynan shu zanjir.
3. **Odam ishtirokidagi tasdiqlar** (foydalanuvchanlik kuzatuvi, xaritaning
   haqiqiy qurilmada o'qilishi, rekvizit formatini buyurtmachi bilan
   tasdiqlash) `02-VALIDATION.md` ning «Manual-Only Verifications» jadvalida
   yuritiladi va bu jadvalda AKS ETMAYDI.

Yuqoridagi ro'yxat va bu jadvalning bir-biriga mosligi mexanik tekshiriladi:
`node scripts/check-requirements-sync.mjs` — qo'lda, har faza yopilishida
(doimiy CI darvozasi emas; sabab skript boshida yozilgan).

**Coverage:**

- v1 requirements: 49 total
- Mapped to phases: 49 ✓
- Unmapped: 0

**Faza kesimida:**

| Phase | Nomi | Talablar soni |
|-------|------|---------------|
| 1 | Poydevor va tenant xavfsizligi | 5 |
| 2 | Bozor domeni va "Yangi bozor" ustasi | 7 |
| 3 | Kamera va tarmoq ulanishi | 5 |
| 4 | Snapshot pipeline | 5 |
| 5 | Kamera zonalari, CV va nazoratchi tasdig'i | 6 |
| 6 | Billing va kassir | 9 |
| 7 | Nomuvofiqlik, bildirishnoma va botlar | 9 |
| 8 | Hisobotlar, mustahkamlash va ishga tushirish | 3 |

✅ **Sanoqlar 2026-08-02 da (`02-24`) faylning O'Z mazmunidan qayta
hisoblangan** — qo'lda taxmin qilinmagan: checkbox ro'yxati 49 ta band,
Traceability jadvali 49 ta qator beradi va ular faza bo'yicha
5/7/5/5/6/9/9/3 ga taqsimlanadi. Ilgari bu bloklar `46` va Phase 2 uchun
`6`, Phase 3 uchun `3` deb turgan edi: 2026-08-01 da qo'shilgan uchta
talab (MARKET-07, CAM-08, CAM-09) sanoqlarga kiritilmagan edi.
`node scripts/check-requirements-sync.mjs` bu farqni har ishga tushganda
ogohlantirish sifatida ko'rsatib turgan — ya'ni eskirgan son jimgina
yashab qolmadi.

---
*Requirements defined: 2026-07-29*
*Last updated: 2026-08-02 — `02-24`: MARKET-07 (xodimlar rosteri importi)
o'lchangan dalil bilan `Done` qilindi va 2-faza talablari to'liq yopildi;
`**Coverage:**` hamda `Faza kesimida` sanoqlari faylning O'Z mazmunidan
qayta hisoblandi (46 -> 49)*
