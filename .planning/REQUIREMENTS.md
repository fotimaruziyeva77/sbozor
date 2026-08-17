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
- [x] **FOUND-06**: Tizim o'zini kuzatadi: kamera offline, o'tkazib yuborilgan snapshot, backup xatosi — platforma adminiga Telegram-alert; xatolar Sentry'da
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

- [x] **CAM-01**: Bozor admini kameralarni qo'shadi/sozlaydi; RTSP ma'lumotlari shifrlangan saqlanadi; "ulanishni tekshirish" tugmasi ishlaydi
- [ ] **CAM-02**: Server NVR'ga faqat WireGuard VPN orqali kiradi; NVR internetga to'g'ridan-to'g'ri ochilmaydi
- [x] **CAM-03**: Direktor/admin panelda jonli kamera tasvirini ko'radi (go2rtc, avtorizatsiya ortida)
- [x] **CAM-04**: Snapshot jadvali har bozor uchun sozlanadi va mavsumiy profilni qo'llaydi (standart: 06:00–08:00 har 30 daq + 16:00, 18:00)
- [x] **CAM-05**: Rejalashtirilgan kadr olish idempotent va retry'li; o'tkazib yuborilgan slot jurnalda ko'rinadi va alert yuboradi
- [x] **CAM-06**: Har kadr sifat filtridan o'tadi (qorong'i/buzuq/bo'sh kadr belgilanadi, `light_mode` saqlanadi) — yaroqsiz kadr billing'ga ta'sir qilmaydi
- [x] **CAM-07**: Kadrlar S3-mos omborda (SeaweedFS) bozor/kamera/sana bo'yicha saqlanadi; 90 kun to'liq, keyin siqilgan 1 yil (sozlanadigan)
- [x] **CAM-08**: Admin **faqat** NVR manzili + login/parolni kiritadi; tizim Hikvision ISAPI orqali qurilmani aniqlaydi, barcha kanallarni sanab chiqadi va kameralarni (nom, kanal, asosiy/sub oqim URL'i) avtomat yaratadi. Qayta skanerlash idempotent (yangi kanal qo'shiladi, yo'qolgani `offline`, mavjudi tegilmaydi). Ulanish xatosi **sababi va tuzatish yo'li** bilan ko'rsatiladi: parol xato / NVR soati >5 daq farqi → NTP / firmware `digest/basic` talab qiladi / kanal offline / sessiya limitiga yetildi
- [x] **CAM-09**: Simulyatsiya qilingan Hikvision NVR (ISAPI mock + go2rtc RTSP manbasi) compose profili sifatida mavjud; kamera kashfiyoti, ulanish testi, jonli ko'rish va kadr olish yo'li real uskunasiz uchidan-uchiga ishlaydi va CI'da o'lchanadi

### AI tahlil (AI)

- [x] **AI-01**: Bozor admini har kamera kadrida rasta zonalarini poligon qilib chizadi (normalangan 0..1 koordinatalar, versiyalangan); bitta rasta bir necha kameraga bog'lanishi mumkin
- [ ] **AI-02**: Detektor (RF-DETR Apache-2.0, ONNX Runtime CPU) har zonani band/bo'sh/noaniq deb baholaydi; AI natijasi confidence bilan saqlanadi va hech qachon o'zgartirilmaydi (nazoratchi qarori alohida yozuv)
- [x] **AI-03**: Nazoratchi noaniq navbatini ko'rib chiqadi — kunlik byudjet va ustuvorlik bilan, "hammasini tasdiqlash" tugmasisiz; tasdiqlangan javoblar fine-tuning dataseti bo'ladi
- [x] **AI-04**: Ko'r tasodifiy audit navbati: nazoratchi AI javobini ko'rmasdan tasodifiy tanlangan zonalarni baholaydi — aniqlik hisoboti faqat shu namunadan olinadi
- [x] **AI-05**: Rasta bir necha kamerada ko'rinsa — birortasi "band" desa rasta band (agregatsiya qoidasi)
- [x] **AI-06**: Kun oxirigacha tasdiqlanmagan noaniq → "bo'sh" (hisobotda alohida belgi bilan)

### Billing (BILL)

- [x] **BILL-01**: Kun yopilishida band rastaga (kamida 2 snapshotda band, yoki 1 snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq kunlik patta hisoblanadi; job idempotent — qayta ishga tushirish dublikat yaratmaydi (`UNIQUE(market_id, stall_id, business_date)`)
- [x] **BILL-02**: Har hisob yozuvi dalil-kadrlarga bog'langan; yaratilgach o'zgartirilmaydi — tuzatish faqat sabab ko'rsatilgan `charge_adjustments` yozuvi orqali
- [x] **BILL-03**: Qarz faqat biriktirilgan sotuvchiga yoziladi; qoldiq har doim hisoblanadigan ko'rinish (hisoblar − to'lovlar), saqlangan balans ustuni emas
- [x] **BILL-04**: Biriktirilmagan rasta band ko'rinsa — hisob yozilmaydi, "ro'yxatga olinmagan savdo" anomaliyasi sifatida hisobotga tushadi
- [x] **BILL-05**: Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi tarif + eski qarz) ko'radi — bu jonli projection, yozilgan hisob emas

### Kassir (CASH)

- [x] **CASH-01**: Kassir telefonda rastani raqam bo'yicha topadi → summa tarifdan avtomatik → to'lov turi (naqd/terminal) → ≤3 bosishda tasdiqlaydi
- [x] **CASH-02**: Kassir summani faqat sabab-kod bilan o'zgartira oladi; har o'zgartirish auditda ko'rinadi
- [x] **CASH-03**: To'lov kiritish idempotent (takror bosish dublikat yaratmaydi); to'lov tuzatish faqat storno + qayta kiritish orqali, o'chirish/tahrirlash yo'q
- [x] **CASH-04**: Kassir smenani ochadi/yopadi; yopishda yig'ilgan naqdni ko'r (tizim summasini ko'rmasdan) deklaratsiya qiladi; tizim farqni (variance) hisoblab direktor hisobotiga chiqaradi
- [x] **CASH-05**: To'lov kiritilishi bilan sotuvchiga Telegram orqali zudlik push-kvitansiya boradi (summa, rasta, kassir, vaqt)

### Nomuvofiqlik va hisobotlar (RECON)

- [x] **RECON-01**: Kunlik nomuvofiqlik hisoboti: "band, lekin to'lovsiz" rastalar + "ro'yxatga olinmagan savdo" anomaliyalari, rasm-dalil havolalari bilan
- [x] **RECON-02**: Har nomuvofiqlik case sifatida yuritiladi: mas'ul, holat (yangi/ko'rilmoqda/asosli/asossiz), yechim; hit-rate metrikasi hisoblanadi
- [x] **RECON-03**: Direktor ertalab dayjesta oladi (kechagi tushum, bandlik %, TOP-10 qarzdor), kechqurun nomuvofiqlik xabarini oladi
- [x] **RECON-04**: Davr bo'yicha hisobotlar: tushum (kunlik/oylik), qarzdorlik reestri, nomuvofiqlik arxivi — har biri Excel (.xlsx) yuklab olinadi
- [x] **RECON-05**: AI aniqlik hisoboti: ko'r audit namunasidan, xatolik turlari ajratilgan ("band deb xato" = nizo xavfi, "bo'sh deb xato" = yo'qotish)
- [x] **RECON-06**: Har rol bosh ekranida o'ziga mos bitta asosiy ko'rsatkich (direktor: bugungi tushum; nazoratchi: kutayotgan navbat; kassir: bugungi yig'im)

### Telegram-bot (BOT)

- [x] **BOT-01**: Sotuvchi botga telefon raqamini contact ulashish orqali tasdiqlab ulanadi — raqam admin kiritgan reestrga mos bo'lsa
- [x] **BOT-02**: Sotuvchi botda qoldiq/qarz va to'lov tarixini ko'radi
- [x] **BOT-03**: Qarz N kundan oshsa sotuvchiga avtomatik eslatma (N sozlanadigan; quiet hours hurmat qilinadi)
- [x] **BOT-04**: Barcha xabarlar outbox orqali throttling bilan yuboriladi; yetkazilganlik holati saqlanadi; botni bloklagan foydalanuvchi belgilanadi

### Landing (LAND)

*10-fazada tug'ilgan (2026-08-17, `10-08`) — ROADMAP Phase 10 SC#1…SC#5
bilan ⛔ **bir-birga** xaritalangan (10-RESEARCH A6 tavsiyasi qabul
qilindi): LAND-0N = SC#N. Bu atayin — mezon moduli
(`frontend/scripts/phase10-criteria.test.mjs`) va bu ro'yxat bitta
haqiqatni ikki tildan aytadi.*

- [x] **LAND-01**: `sbozor.uz/` (anonim root) landing ko'rsatadi, uchala tilda SSG; «Kirish» app loginiga olib boradi
- [x] **LAND-02**: Hero 12s "jonli bozor" siklini o'ynaydi (xarita → kamera nuri → amber «Band, lekin to'lovsiz» → to'lov → hisobot); video EMAS, `prefers-reduced-motion`da statik final-kadr
- [x] **LAND-03**: Demo-forma yuborilganda so'rov admin Telegram-botga yetadi (mavjud bot-service infratuzilmasi orqali) — alohida CRM yo'q
- [x] **LAND-04**: Ishonch bloki (ma'lumotlar O'zbekistonda · NVR faqat VPN · har amal auditda · 3 til) va pilot holati halol («Karmana sinovda», yolg'on raqam YO'Q)
- [x] **LAND-05**: Lighthouse ≥95, LCP <1,5 s (statik sahifada), SEO meta/OG/structured data to'liq

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
| FOUND-06 | Phase 4 | Done |
| FOUND-07 | Phase 8 | Blocked (1-da'vo YARIM, 2-da'vo umuman o'lchanmagan: zaxira zanjirining O'ZI to'liq qurilgan va statik darvoza bilan qulflangan (tests/unit/test_backup_contract.py), yurak urishi halqasi mahsulot skripti orqali o'lchanadi (tests/integration/test_backup_heartbeat.py, test_phase8_criteria.py::test_sc3_*) va dump -> TOZA server -> ma'lumot zanjiri bajariladi (tests/integration/test_restore_drill.py); LEKIN «boshqa lokatsiyaga ketadi» REAL offsite restic repo'sini talab qiladi — RESTIC_REPOSITORY/RESTIC_PASSWORD .env da YO'Q — va «toza serverda tiklash mashqi kamida bir marta muvaffaqiyatli o'tkazilgan» REAL VPS ni talab qiladi. Egasi: Ops, tetigi: VPS deploy'i, bandlari 08-HUMAN-UAT.md #1 va #2. ⛔ Qo'shimcha: tiklangan bazada sbozor_app ning 0 GRANT'i bor (deferred-items №5), ya'ni tiklash tartibiga migratsiyani qayta yugurtirish qadami kerak) |
| MARKET-01 | Phase 2 | Done |
| MARKET-02 | Phase 2 | Done |
| MARKET-03 | Phase 2 | Done |
| MARKET-04 | Phase 2 | Done |
| MARKET-05 | Phase 2 | Done |
| MARKET-06 | Phase 2 | Done |
| MARKET-07 | Phase 2 | Done |
| CAM-01 | Phase 3 | Done |
| CAM-02 | Phase 3 | Blocked (2-da'vo o'lchandi, 1-da'vo emas: «server NVR'ga FAQAT tunnel orqali kiradi» CI'da tunnel bo'lmagani uchun sinalmaydi — egasi Ops, tetigi VPS deploy'i, vositasi ops/scripts/verify-tunnel.sh, bandi 03-HUMAN-UAT.md #1 va #2) |
| CAM-03 | Phase 3 | Done |
| CAM-04 | Phase 4 | Done |
| CAM-05 | Phase 4 | Done |
| CAM-06 | Phase 4 | Done |
| CAM-07 | Phase 4 | Done |
| CAM-08 | Phase 3 | Done |
| CAM-09 | Phase 3 | Done |
| AI-01 | Phase 5 | Done |
| AI-02 | Phase 5 | Blocked (2-da'vo o'lchandi, 1-da'vo YARIM: «AI natijasi confidence bilan saqlanadi va hech qachon o'zgartirilmaydi» to'liq o'lchangan (tests/integration/test_occupancy_immutable.py, test_phase5_criteria.py::test_sc2_*); «detektor har zonani baholaydi» esa faqat SINTETIK sv.Detections ustida — real ONNX artefakti CI'da YO'Q va `-m model` bandlari umuman chaqirilmaydi, modelning ANIQLIGI esa oltin to'plam bo'shligi uchun o'lchanmagan. Egasi: nazoratchi (yorliqlaydi) + Ops (artefakt), tetigi: Phase 0 real kadrlari va GPU ijarasi, bandlari 05-HUMAN-UAT.md #1, #2 va #3) |
| AI-03 | Phase 5 | Done |
| AI-04 | Phase 5 | Done |
| AI-05 | Phase 5 | Done |
| AI-06 | Phase 5 | Done |
| BILL-01 | Phase 6 | Done |
| BILL-02 | Phase 6 | Done |
| BILL-03 | Phase 6 | Done |
| BILL-04 | Phase 6 | Done |
| BILL-05 | Phase 6 | Done |
| CASH-01 | Phase 6 | Done |
| CASH-02 | Phase 6 | Done |
| CASH-03 | Phase 6 | Done |
| CASH-04 | Phase 6 | Done |
| CASH-05 | Phase 7 | Done |
| RECON-01 | Phase 7 | Done |
| RECON-02 | Phase 7 | Done |
| RECON-03 | Phase 7 | Done |
| RECON-04 | Phase 8 | Done |
| RECON-05 | Phase 8 | Done |
| RECON-06 | Phase 7 | Done |
| BOT-01 | Phase 7 | Done |
| BOT-02 | Phase 7 | Done |
| BOT-03 | Phase 7 | Done |
| BOT-04 | Phase 7 | Done |
| LAND-01 | Phase 10 | Done |
| LAND-02 | Phase 10 | Done |
| LAND-03 | Phase 10 | Done |
| LAND-04 | Phase 10 | Done |
| LAND-05 | Phase 10 | Blocked (mexanik yarim TO'LIQ o'lchangan: SEO fayl-konventsiyalari `sitemap.ts`/`robots.ts`, metadata OG/hreflang/canonical, JSON-LD rasmiy escape bilan, `--text-hero` tipografiya tokeni — `landing-surface.test.mjs` G-land-1/3/5 va `phase10-criteria.test.mjs` SC#5; payload farqi ham O'LCHANGAN (10-03: ildiz 287,8→208,4 KB gz, `10-HUMAN-UAT.md` #2 SON bilan yopiq). LEKIN talab matnining ikki RAQAMI — Lighthouse ≥95 va LCP <1,5 s — CI'da UMUMAN o'lchanmaydi (Lighthouse qo'shilmagan, 10-UI-SPEC §16.5 [QAROR]; headless Chrome `gate` byudjetiga daqiqalar qo'shardi) va 60fps ham real qurilmasiz o'lchovsiz. Mexanika qatlamining yashilligi bilan o'lchov qatlamining yo'qligini yopish TAQIQ (D-01, FOUND-07, AI-02 darslari). Egasi: ijrochi. Tetigi: birinchi deploy. Bandlari: `10-HUMAN-UAT.md` #1 va #3) |

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

**Qoidaning 3-fazadagi qo'llanishi** (2026-08-03, `03-11`). Beshta CAM
bandidan **ikkitasi** `Done` bo'ldi (CAM-01, CAM-08) — ularning har bir
jumlasi o'lchangan test bilan qoplangan. Qolgan **uchtasi** `Blocked`
bo'lib qoldi va sabab har birida ochiq yozilgan. Bu **ataylab**: uchalasi
ham amalda ISHLAYDI va katta qismi o'lchangan, lekin talab MATNIDAGI
bitta jumla CI'da bajarilmaydi. `Done` qo'yish o'sha jumlani
«isbotlangan» qilib ko'rsatardi va keyingi faza uning ustiga qurilardi —
2-fazaning `02-VERIFICATION.md` da hujjatlashtirilgan xatosining aynan
takrori bo'lardi (890 yashil test ortida to'rtta haqiqiy bo'shliq).

⚠ **`Blocked` bu yerda «ish to'xtadi» degani EMAS** — u «dalil to'liq
emas va yetishmayotgan dalil NOMLANGAN» degani. Uchala bandning ham
yopilish yo'li o'z qatorida yozilgan (Ops deploy'i, 4-faza).

### Qoidaning qayta qo'llanishi (2026-08-03, `03-14`) — DALIL BILAN

`03-VERIFICATION.md` GAP-1 va GAP-2 yopilgach uchta `Blocked` banddan
**ikkitasi** `Done` ga o'tdi. Har birining dalili NOMMA-NOM:

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **CAM-03** | `Blocked` -> **`Done`** | (a) avtorizatsiya — `test_live_view.py` (rad etish matritsasi) va `test_phase3_criteria.py::test_sc6_live_view_requires_authorization`; (b) **media yo'li** — `tests/integration/test_live_view_e2e.py::test_a_frame_arrives_through_the_discovered_stream`: kashfiyot hosil qilgan `cam_<uuid4>` oqimi uchun `/api/frame.jpeg` **99 681 baytli HAQIQIY JPEG** qaytardi (mock'siz, mahsulot `Go2rtcClient` i bilan) | **Brauzerdagi ijro va IDROK** — tasvir keladi, lekin uning ekranda qanday ko'rinishi, kechikishi va sifati o'lchanmagan (jsdom `RTCPeerConnection` bermaydi). Bandi: `03-HUMAN-UAT.md` #5, egasi direktor, tetigi pilot tayyorgarligi haftasi |
| **CAM-09** | `Blocked` -> **`Done`** | Beshala bandi ham o'lchanadi: profil (`--profile sim`, `test_compose_sim_env.py`), kashfiyot (`test_nvr_discovery.py`, `test_sc1`/`test_sc2`), ulanish testi (`test_nvr_api.py`, `test_nvr_errors.py`), **jonli ko'rish** va **kadr olish yo'li** — ikkalasi ham `test_live_view_e2e.py` da, aynan `/api/frame.jpeg` orqali (4-fazaning STANDART mexanizmi, `CLAUDE.md` § «Snapshot capture») | Sim RTSP sessiya LIMITINI (D-05) modellamaydi va real firmware chetlanishlarini ko'rsatmaydi — bular `03-HUMAN-UAT.md` #3 va #4 |
| **CAM-02** | **`Blocked` BO'LIB QOLADI** | «NVR internetga to'g'ridan-to'g'ri ochilmaydi» o'lchangan: ommaviy IP -> `422 nvr_host_public_blocked`; `wg0.conf.example` da butun-internet CIDR'i YO'Q (D-13) | «Server NVR'ga **FAQAT** tunnel orqali kiradi» — CI konteynerida `wg0` interfeysi UMUMAN YO'Q. Bunday test har doim «tunnel uzilgan» shoxidan o'tib yashil bo'lardi va HECH NIMA isbotlamasdi (Pitfall 10). **Egasi: Ops. Tetigi: VPS deploy'i.** Vositasi `ops/scripts/verify-tunnel.sh`; bandlari `03-HUMAN-UAT.md` #1 va #2 |

⚠ **CAM-09 ning matnidagi «go2rtc RTSP manbasi» endi HARFMA-HARF to'g'ri
emas va bu ochiq aytiladi.** `03-12` sim'ning RTSP oyog'ini `go2rtc-sim`
dan **MediaMTX** ga ko'chirdi (sabab: Hikvision yo'li `/Streaming/
Channels/102` ichida SLESH bor va go2rtc'ning oqim nomi <-> URL yo'li
moslashuvi sleshli nom uchun hujjatlashtirilmagan). Talabning MAZMUNI —
«real uskunasiz uchidan-uchiga ishlaydigan sim RTSP manbasi» —
bajarildi; o'zgargan narsa implementatsiya tafsiloti. go2rtc esa
MAHSULOT yo'lida, ISTE'MOLCHI sifatida qoladi va aynan u kadrni beradi.

⚠ **`Done` NIMANI ANGLATMAYDI.** Ikkala bandning ham dalili
SIMULYATOR ustida olingan. Real Hikvision NVR'ning firmware chetlanishlari
va haqiqiy sessiya limiti `03-HUMAN-UAT.md` da, egasi va tetigi bilan
yozilgan; ular fazani bloklamaydi (2026-08-01 self-service direktivasi),
lekin «real qurilmada ishlaydi» degan da'vo BERILMAGAN.

⚠ **Faza mezonlari (SC#1…SC#8) bundan MUSTAQIL** va ularning sakkiztasi
ham yashil (`tests/integration/test_phase3_criteria.py`). Mezonlar
fazaning yetkazib berish mahsulotini o'lchaydi, talablar esa v1 relizining
jumlalarini — CAM-09 ning «kadr olish yo'li» bandi, masalan, 4-fazaning
mavzusi va u SC#7 ning da'vosidan kengroq.

### Qoidaning 4-fazadagi qo'llanishi (2026-08-05, `04-12`) — DALIL BILAN

Beshala band `Done` bo'ldi va HAR BIRINING dalili nomma-nom. ⚠ `Done`
bu yerda ham «faza to'liq yopildi» degani EMAS: har qatorning oxirgi
ustuni nima o'lchanMAGANini ochiq aytadi va uning egasi
`04-HUMAN-UAT.md` da turadi.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **CAM-04** | `Pending` -> **`Done`** | `test_phase4_criteria.py::test_sc1_schedule_produces_slots` — admin HTTP orqali mavsumiy profilni sozlaydi (uchta vaqt, standart YETTILIK emas) va ERTANGI kunning materializatsiyasi AYNAN o'sha slotlarni beradi; BUGUNGI reja esa o'zgarmaydi (D-05). Standart profil (`DEFAULT_SNAPSHOT_SLOTS`) talab matnidagi ro'yxatga harfma-harf teng: 06:00/06:30/07:00/07:30/08:00 + 16:00/18:00. Yuzaning qolgani — `test_capture_schedule.py` (26 test) | Mavsumiy profillarning REAL yil davomidagi almashinuvi (yozgi -> qishki) kalendar bilan sinalmagan — davr semantikasi `test_schedule_repo.py` da o'lchangan, KALENDAR o'tishi emas |
| **CAM-05** | `Pending` -> **`Done`** | `test_sc2_interruption_leaves_no_duplicate_and_missed_is_visible` — uchala bo'lak bitta zanjirda: takroriy tik dublikat bermaydi (qator IDENTITETI bilan), ijarasi tugagan `running` qator qaytariladi (urinish qayta bajariladi) va `missed` qator `GET /capture-runs` JAVOBIDA ko'rinadi. Alert qismi — `test_sc5_...` | REAL NVR'ning sessiya limiti ostidagi xulq: simulyator uni UMUMAN modellamaydi (`04-HUMAN-UAT.md` #6, egasi Ops) |
| **CAM-06** | `Pending` -> **`Done`** | `test_sc3_quality_verdict_never_reaches_billing` — sim buzuq kadr beradi, u `corrupt` deb belgilanadi, `light_mode='unknown'` bilan SAQLANADI va `is_billable=false` bo'ladi; unga bandlik dalilini bog'lash **DB darajasida** rad etiladi (`uq_snapshots_billable_anchor` + kompozit FK + CHECK). Nazorat holati: yaroqli kadr o'tadi. `dark`/`blank` verdiktlari — `tests/unit/test_quality_filter.py` (sintetik kadrlar, fizik xususiyat bo'yicha) | Chegaralarning QIYMATI — hozir LOW confidence, real Karmana kadri yo'q. Mexanizm o'lchangan, qiymat emas (`04-HUMAN-UAT.md` #1, egasi nazoratchi + ijrochi). Agar real kadrlarda chegaralar butunlay noto'g'ri chiqsa CAM-06 `Blocked` ga QAYTARILADI |
| **CAM-07** | `Pending` -> **`Done`** | `test_sc4_storage_layout_and_retention_policy` — HAQIQIY SeaweedFS ustida: kalit `bozor/sana/kamera/slot` tartibida topiladi, qo'shni bozorning prefiksi uni KO'RSATMAYDI, chegara kelganda kadr AYNAN o'sha kalitda siqiladi (o'lcham saqlanadi, `size_bytes` kamayadi, obyekt qayta o'qib dekodlanadi) va QATOR o'chirilmaydi. Mexanizmning qolgani — `test_storage_layout.py` + `test_retention.py` | «90 kun» ning KALENDAR bo'yicha kechishi. Test chegarani SOZLAMA (`full_days=0`), vaqtni ARGUMENT (`today=`) qiladi — ikkalasi ham mahsulot yo'lidagi haqiqiy parametrlar, lekin 90 kunni faqat vaqt isbotlaydi (`04-HUMAN-UAT.md` #2, egasi Ops) |
| **FOUND-06** | `Pending` -> **`Done`** | `test_sc5_absence_reaches_telegram_and_sentry` — uchala tetik (o'tkazib yuborilgan slot · kamera javob bermayapti · zaxira yangilanmagan) xabar beradi va ular GURUHLANADI (bozor bo'yicha bitta, platforma bo'yicha bitta); birorta so'rovda rasm, havola yoki obyekt kaliti YO'Q (D-19). **«Xatolar Sentry'da»** — bu da'vo SANOQQA emas, **HOSILAGA** tayanadi. `tests/unit/test_sentry_processes.py` «bizning kodimizni qaysi jarayonlar yuritadi?» savoliga `compose.yaml` DAN javob oladi: `SENTRY_DSN` beriladigan HAR servis uchun kirish nuqtasi `command` dan chiqariladi va o'sha obyektning hodisa reyestrida `init_sentry(` bo'lishi TALAB qilinadi; uch bosqichning har birida «topilmadi» = `pytest.fail`, «o'tkazib yuborish» yo'li yo'q. Bugungi hosila **uch jarayon** beradi — `core-api`, `worker`, `scheduler` — lekin darvoza na bu sonni, na bu nomlarni biladi, ya'ni to'rtinchi servis qo'shilgan kuni u jimgina eskirmaydi, **YIQILADI**. Planer jarayoni bundan tashqari HAQIQIY subprocess bilan o'lchanadi (`test_sc5_...`; nazorat yugurishi DSN'siz `SENTRY_ACTIVE=False` beradi), uning taskiq yutib yuboradigan `on_ready` istisnosi esa `ObservedScheduler` orqali jurnal + Sentry'ga chiqib QAYTA KO'TARILADI (`tests/unit/test_scheduler_observability.py`). ⚠ `scheduler` jarayonining ilmog'i `04-13` da qo'shildi — `04-VERIFICATION.md` uning yo'qligini KONTEYNERDAN o'lchab topgan va fazani `gaps_found` qilgan edi | Telegram xabarining HAQIQATAN yetib borishi (token va chat ID CI'da yo'q), **istisnoning HAQIQIY Sentry loyihasida ko'rinishi** (CI'da DSN yo'q — darvoza `init()` chaqirilishini va `capture_exception` ga borishni o'lchaydi, hodisaning YETIB BORISHINI emas) va tashqi dead-man's switch. ⚠ Uchalasi ham `04-HUMAN-UAT.md` ning #4, #7 va #5 bandlarida **ega (Ops) va tetik bilan** yozilgan — `Done` aynan shu shartga bog'liq edi va shart bajarildi (2026-08-01 self-service direktivasi: tashqi bog'liqlik `Blocks:` bo'lmaydi) |

⛔ **YO'L-YO'LAKAY TOPILDI: bu skript `03-14` dan beri QIZIL turgan.**
`CAM-02` ro'yxatda `- [x]`, jadvalda esa `Blocked` edi — ya'ni fayl ikki
xil haqiqat aytardi va `node scripts/check-requirements-sync.mjs` buni
har chaqiruvda ko'rsatib turardi. Sabab mexanik: skript CI darvozasi
EMAS (o'z docstringida ochiq yozilgan — «qo'lda, har faza yopilishida»)
va 3-faza uni oxirgi marta chaqirmasdan yopilgan. Belgi jadvalga
moslandi (`- [ ]`), chunki **jadval to'g'ri**: CAM-02 ning bitta jumlasi
hamon o'lchanmagan. Bu «darvoza bor, lekin hech kim bosmaydi» sinfining
namunasi va u 4-fazada AYNAN shu skript bilan tutildi.

⚠ **HAMMASI SIMULYATOR USTIDA.** Beshala bandning ham dalili
`nvr-sim` (haqiqiy TCP + Digest), haqiqiy SeaweedFS va haqiqiy Postgres
ustida olingan. Real Hikvision NVR, real kadrlar va kalendar vaqti
`04-HUMAN-UAT.md` da, ega va tetigi bilan; ular fazani bloklamaydi,
lekin «real bozorda ishlaydi» degan da'vo BERILMAGAN.

### Qoidaning 5-fazadagi qo'llanishi (2026-08-10, `05-15`) — DALIL BILAN

Oltita AI bandidan **beshtasi** `Done`, **bittasi** (`AI-02`) `Blocked`.
Bu nisbat 3-fazaning shaklini takrorlaydi va ATAYIN: AI-02 amalda
ISHLAYDI va katta qismi o'lchangan, lekin talab MATNIDAGI birinchi
jumla — «detektor har zonani baholaydi» — CI'da **real og'irliklar
bilan** bajarilmaydi.

⚠ **Bu faza uchun `Done` ning ma'nosi oldingilaridan TOR va buni ochiq
aytish shart.** Oldingi fazalarda «o'lchandi» degani mahsulot yo'lining
haqiqiy komponent (Postgres, SeaweedFS, `nvr-sim`) ustida bajarilishi
edi. Bu yerda ham shunday — LEKIN detektor o'rnida **SINTETIK
`sv.Detections`** turadi va u kutilayotgan verdiktni UMUMAN bilmaydi
(geometrik fakt bo'yicha nomlangan, W0-7). Ya'ni o'lchangan narsa —
`sv.Detections` DAN KEYINGI butun zanjir; modelning o'zi emas.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **AI-01** | `Pending` -> **`Done`** | `test_phase5_criteria.py::test_sc1_polygons_are_normalized_versioned_and_multi_camera` — admin HTTP orqali kontur chizadi va u AYNAN qaytadi; javobdagi har koordinata 0..1 da **va** piksel koordinatasi **422 bilan rad etiladi** (ya'ni normalanish DARVOZA, kelishuv emas); tahrir `version = 3` yaratadi va eskisi `is_active = false` bo'lib JOYIDA qoladi; bitta rasta ikki kamerada bir vaqtda FAOL. Yuzaning qolgani — `test_camera_zones_api.py` (versiyalash, qamrov, V5 geometriyasi) va Y-1 muharriri (`npm --prefix frontend run test:component`) | Chizishning **amalda bajariladiganligi** 300–1000 rasta uchun — vaqt faqat real bozor chizmasida o'lchanadi (`05-HUMAN-UAT.md` #5, egasi bozor admini). Shuningdek 60 poligonli kamerada sudrash tezligi (#7, D-05 chiqish yo'li) |
| **AI-02** | `Pending` -> **`Blocked`** | **Ikkinchi jumla TO'LIQ o'lchangan:** `occupancy_events` ning `UPDATE` i baza darajasida rad etiladi (`test_occupancy_immutable.py`, `test_phase5_criteria.py::test_sc2_*` — xom `psycopg` bilan, `sbozor_owner` ulanishida), nazoratchi qarori `zone_reviews` da **ALOHIDA qator** bo'lib tug'iladi va AI qatori bayt-bayt o'zgarmaydi; uchala baho ham (`occupied`/`empty`/`uncertain`) `confidence` bilan saqlanadi. **Birinchi jumlaning MEXANIZMI** ham o'lchangan: xom tenzor arifmetikasi (`cv-tests::test_rfdetr_postprocess.py`), 0..1 ↔ piksel zona verdicti (`test_zone_verdict.py`), orkestratsiya va idempotentlik (`test_detect_job.py`), cross-servis enqueue (`test_capture_enqueues_detect.py`) | **Birinchi jumlaning O'ZI:** «RF-DETR ONNX Runtime CPU da har zonani baholaydi» CI'da **real artefakt bilan bajarilmaydi** — `.onnx` fayli yo'q va `-m model` bandlari umuman chaqirilmaydi. Modelning ANIQLIGI esa oltin to'plam bo'shligi uchun **umuman o'lchanmagan** va bu bo'shliq mexanika qatlamining yashilligi bilan YOPILMAYDI (D-01). **Egasi:** nazoratchi (yorliqlaydi) + Ops (artefakt). **Tetigi:** Phase 0 real kadrlari va GPU ijarasi. **Bandlari:** `05-HUMAN-UAT.md` #1, #2, #3 |
| **AI-03** | `Pending` -> **`Done`** | `test_phase5_criteria.py::test_sc3_uncertain_queue_has_budget_priority_and_no_bulk_endpoint` — navbatga FAQAT `uncertain` tushadi; birinchi band biriktirilgan sotuvchisi BOR rastaniki (ustuvorlik tasodifiy emas); byudjet tugagach **409 `review_budget_exhausted`** va u «navbat bo'sh» dan boshqa kod (nazorat: byudjet ko'tarilgach o'sha band QAYTADI); javob `purpose='train'` bilan yig'iladi; **«hammasini tasdiqlash» marshruti YO'Q** — OpenAPI sxemasi bo'yicha nazoratchi yuzasining birorta marshruti massiv qabul qilmaydi (bo'sh sxema uchun quyi chegara bilan). Ekran — Y-2 (`review-session.tsx`), DOM'da `input[type=checkbox]` yo'q. ⚠ **`05-15` da yopilgan bo'shliq:** sof `inspector` roli dalil kadrini endi KO'RADI (`test_snapshot_api.py::test_a_pure_inspector_can_open_the_evidence_frame` — 200 va baytlar teng); ilgari u **403** olardi va navbatning oxirgi qadami o'z foydalanuvchisida bajarilmasdi | Kunlik byudjetning QIYMATI (30/50) real nazoratchi uchun realmi — charchash va tezlik inson o'lchovi (`05-HUMAN-UAT.md` #6). «Tasdiqlangan javoblar fine-tuning dataseti bo'ladi» — qatorlar YIG'ILADI (`purpose='train'`), lekin ular bilan model hali O'QITILMAGAN |
| **AI-04** | `Pending` -> **`Done`** | `test_phase5_criteria.py::test_sc4_blind_audit_hides_the_system_answer_and_report_uses_only_that_sample` — ko'r payloadda tizim javobining birorta kaliti YO'Q **va** xom matnda verdikt so'zining o'zi ham uchramaydi (ikki mustaqil qatlam); hisobot BUTUN namuna javoblangandan keyin AYNAN `eval` lar sonini beradi, ya'ni ko'r namunaning `train` yarmi ham, noaniq navbatining javoblari ham unga KIRMAYDI. Namuna `audit_draw` bilan tortiladi va Python da MUSTAQIL qayta hisoblanadi (`test_blind_audit.py`); serializer maydonni **umuman e'lon qilmaydi** (D-17.2). Ekran — Y-3 va `blind-payload.test.mjs` katalog skani | Nazoratchining **amaliy** langarlanmasligi — strukturaviy himoyalar o'lchangan, odamning o'zi emas (`05-HUMAN-UAT.md` #4). ⛔ **D-16 (nazoratchining o'zi bilan ichki mosligi) QURILMADI** va u bugungi sxemada strukturaviy ravishda ifodalab bo'lmaydi: `audit_draw` har hodisani eng ko'pi bilan bir marta tortadi. Qator `05-UI-SPEC.md` §11.6 dan OLIB TASHLANDI va i18n kaliti YOZILMADI |
| **AI-05** | `Pending` -> **`Done`** | `test_phase5_criteria.py::test_sc5_any_camera_occupied_wins_and_unreviewed_uncertain_defaults_to_empty` — zonasiz rastaga ikki kamerada uch zona qo'yiladi: kamera A da IKKITA `empty`, kamera B da BITTA `occupied`. Kun yopilgach rasta-slot `occupied` va manbasi `ai`. ⛔ Ikkita `empty` ATAYIN: bittasi bilan «birinchi zona g'olib», «kamera A g'olib» va «ko'pchilik ovozi» variantlari ham yashil qolardi. Sof funksiya jadvali — `test_aggregate_stall_slot.py` (120 holat) | Real kadrda bitta rasta ikki kamerada QANDAY ko'rinishi — burchak, yorug'lik va qisman to'silish. Agregatsiya QOIDASI o'lchangan, kirish MA'LUMOTINING sifati emas |
| **AI-06** | `Pending` -> **`Done`** | O'sha testning 2- va 3-da'volari: javobsiz `uncertain` kun yopilganda `verdict='empty'` **va** `resolution_source='default_empty'` bo'ladi, `GET /occupancy` esa uni `empty` dan AJRATIB beradi (beshinchi hisoblagich). ⛔ `zone_reviews` ga SOXTA qator YOZILMAYDI — tizim «nazoratchi buni bo'sh deb tasdiqladi» deb yolg'on gapirardi va o'sha yolg'on keyin trening datasetiga tushardi. Mexanizmning qolgani — `test_day_close.py`; ekran — Y-4 ning besh hisoblagichi | Kun yopilishining REAL kalendar bo'yicha har kecha 03:40 da ishlashi — job argument sifatida `business_date` oladi, ya'ni mexanizm soat holatidan mustaqil, LEKIN planer tikining bir yil davomida uzilmasligi faqat vaqt bilan isbotlanadi (4-fazaning `retention` bandi bilan bir xil shakl) |

⚠ **`Blocked` bu yerda ham «ish to'xtadi» degani EMAS.** AI-02 ning
yopilish yo'li o'z qatorida yozilgan va u ikki bosqichli: (a) GPU
ijarasida ONNX artefakti eksport qilinadi va `ops/models/` ga `COPY`
bilan olib kiriladi (`-m model` bandlari uyg'onadi); (b) real Karmana
kadrlari yorliqlanib `tests/fixtures/golden_set/manifest.jsonl` ga
tushadi (`golden` darvozasi uyg'onadi). Ikkalasi ham QURILGAN va KUTIB
TURIBDI — kod yozish talab qilinmaydi.

⚠ **Faza mezonlari (SC#1…SC#5) bundan MUSTAQIL** va beshalasi ham yashil
(`tests/integration/test_phase5_criteria.py`, bitta buyruq). Mezonlar
fazaning yetkazib berish mahsulotini o'lchaydi, talablar esa v1
relizining jumlalarini — AI-02 ning «RF-DETR» so'zi, masalan, birorta
SC ning matnida YO'Q.

### Qoidaning 6-fazadagi qo'llanishi (2026-08-11, `06-14`) — DALIL BILAN

To'qqizala band `Pending` -> **`Done`**. ⛔ **Bu nisbat 3- va 5-fazadan
FARQ QILADI va farq TASODIF EMAS:** o'sha fazalarda talab matnidagi bir
jumla CI'da real artefakt bilan bajarilmasdi (tunnel yo'q, ONNX
og'irliklari yo'q). Bu fazada esa haqiqatning uchala qismi ham bazada
yashaydi — pul miqdori `tariffs.amount_soum` da, bandlik
`stall_slot_occupancy` da, to'lov `payments` da — ya'ni har jumla
HAQIQIY `postgres:18.4`, HAQIQIY SeaweedFS va HAQIQIY marshrut grafi
ustida bajariladi (D-01).

⚠ **`Done` NIMANI ANGLATMAYDI.** Hech bir qator «real bozorda,
real kassir bilan ishlaydi» degan da'voni bermaydi: uchala frontend
da'vosi jsdom da, pul zanjiri esa seed ma'lumoti ustida o'lchangan.
Oxirgi ustun har qatorda nima o'lchanMAGANini ochiq aytadi.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **BILL-01** | `Pending` -> **`Done`** | `test_phase6_criteria.py::test_sc1_immutable_daily_charge_is_written_once` — o'tmishdagi OCHIQ kunda `day_close` -> `billing_close` zanjiri: hisob AYNAN ikki rastada (2 slotli AI + nazoratchi tasdiqlagan), summa `tariffs` qatoridan O'QIB solishtiriladi; qayta yugurish `charged = 0`, qator qiymatlari va `created_at` o'zgarmaydi, `errors` BO'SH va `skipped_existing` mavjud hisoblarni TANIYDI. Chegara (`kamida 2 slot, yoki 1 + tasdiq`) — `test_g6_human_confirmation_must_be_on_the_occupied_slot` (uch holat) va `tests/unit/test_billable_from_slots.py` (jadval testi). Job yuzasi — `test_billing_close.py` | ⚠ **TALAB MATNIDAGI USTUN NOMI ESKIRGAN:** `UNIQUE(market_id, stall_id, business_date)` deb yozilgan, amaldagi kalit esa `(market_id, stall_id, service_date)`. Sabab loyihalash paytida hujjatlashtirilgan (Pitfall 1): `daily_charges.business_date` — qator YOZILGAN kun (`created_at` dan hosila), domen kuni esa ATAYIN `service_date` deb nomlangan. **Mexanizm** (bir rasta-kunga bitta hisob) o'lchangan, nomlanish esa boshqacha. ⛔ **Cron satrining O'ZI** (`BILLING_CLOSE_CRON = "10 4 * * *"`) birorta test bilan assert QILINMAYDI — u faqat yurak urishining YO'QLIGI orqali ko'rinadi (`billing_close_stale`, `test_alerting.py`) va deployda `scheduler` qayta ishga tushirilishini TALAB qiladi |
| **BILL-02** | `Pending` -> **`Done`** | `test_sc2_charge_reaches_evidence_and_cannot_be_edited` — zanjir OXIRIGACHA yuriladi: `daily_charges` -> `charge_evidence.occupancy_event_id` -> `occupancy_events.snapshot_id` -> `GET /snapshots/{id}/image` **200 + `image/jpeg` + AYNAN o'sha baytlar** (HAQIQIY SeaweedFS ga yozilgan, mock YO'Q, direktor sessiyasi). `UPDATE`/`DELETE` -> `RaiseException`; `charge_adjustments` INSERT o'tadi va `audit_log` da qator paydo bo'ladi, asl summa O'ZGARMAYDI. Qo'riqchilarning qolgani — `test_billing_immutable.py`; ekran — `charge-detail-dialog` (06-13) | Dalil kadrining direktor uchun **o'qilishi** (rasm ekranda qanday ko'rinadi, nizoda yetarlimi) — inson idroki, jsdom bermaydi. Rasm proxysi CI'da SEED baytlari bilan o'lchanadi, real Karmana kadri bilan emas |
| **BILL-03** | `Pending` -> **`Done`** | `test_sc3_debt_is_computed_and_unassigned_becomes_anomaly` — biriktirilgan sotuvchining qoldig'i `vendor_outstanding()` dan yozilgan hisobni QAMRAYDI; `information_schema` da `daily_charges` va `vendors` da nomi `balance` bilan boshlanadigan/tugaydigan ustun **TO'PLAM TENGLIGI bilan YO'Q**. FIFO taqsimlash SAQLANMAYDI: `payment_allocations` jadvali yo'q, `payments` da `allocated*` ustuni yo'q, qoida `ALLOCATION_RULE == "FIFO_OLDEST_SERVICE_DATE_FIRST"`. Arifmetikaning o'zi — `test_billing_repo.py` (Σ unpaid ↔ `vendor_outstanding`) va `tests/unit/test_payment_credit_rules.py` (uch jadval) | «Qarz faqat biriktirilgan sotuvchida ko'rinadi» — **ekranda** ism KLIENTDA joinlanadi va `useVendorsQuery` 50 qatorli sahifa beradi, ya'ni 50 dan ortiq sotuvchisi bor bozorda ustun bo'sh qoladi (`deferred-items.md` 9-band, 8-fazaning hisobot yuzasi). Qoldiq SONI to'g'ri, ISM to'liq emas |
| **BILL-04** | `Pending` -> **`Done`** | O'sha testning (b) qismi: biriktirilmagan band rastada `daily_charges` da **0 qator** VA `billing_anomalies(kind='unassigned_occupied')` da **AYNAN 1 qator**. Invariant IKKI joyda qo'riqlangan — `_close_stall` ning D-28 shoxi va `write_charge()` ning `ValueError` i (S-3 sabotaji ikkalasini ham ko'rsatdi). Hisobotga chiqishi — `GET /billing/anomalies` (`test_billing_api.py`, uch ALOHIDA sanoq) va `anomaly-list.tsx` (06-13) | Anomaliya bilan **nima qilinishi** — case oqimi, mas'ul, holat — 7-fazaning mavzusi (RECON-02). Bu yerda faqat «ko'rinadi» o'lchangan |
| **BILL-05** | `Pending` -> **`Done`** | `test_sc4_pending_projection_and_three_step_confirmation` (a) — `GET /billing/pending` javobining kalitlar to'plami AYNAN yetti va `charge_id` **umuman yo'q**; summa `resolve_stall_day_money()` va `pending_projection()` dan **ikki chaqiruv, bir natija** (D-16) va HTTP javobi ham AYNAN o'sha son. Nol-natija va uch shakl (aniq/ko'p moslik/bozor kesimi) — `test_billing_api.py`; ekran — `pending-card` + `pending-summary` | Kassir uchun **jonliligi**: so'rov `staleTime`/`refetch` siyosati real telefonda, zaif tarmoqda o'lchanmagan |
| **CASH-01** | `Pending` -> **`Done`** | ≤3 bosish **DOM'dan HOSILA** sanoq bilan: `frontend/src/components/collect/collect-session.test.tsx` — `expect(steps).toBe(3)` (2 ham, 4 ham qizil) va ikkinchi takror ham AYNAN 3 (fokus qidiruvga qaytadi). Mezon modulida uning DARVOZAGA ULANGANI o'lchanadi (`package.json::gate` zanjirida `npm --prefix frontend test` bor). Summa tarifdan — `test_sc4` (a); rasta raqamdan topiladi — `stall-lookup` + `pending_projection` prefiks qidiruvi | ⛔ **«Telefonda»** — jsdom brauzer EMAS: tegish nishoni o'lchami (`min-h-11`/`min-h-14`) sinf sifatida bor, lekin real qurilmada barmoq bilan bosish, klaviatura qoplashi va bir qo'lda ishlash **o'lchanmagan**. Egasi: kassir; tetigi: pilot tayyorgarligi haftasi |
| **CASH-02** | `Pending` -> **`Done`** | `test_sc4` (c) — sabab-kodsiz chetlangan summa **422** (HAQIQIY marshrutdan, `payments` da 0 qator). Sabab bilan yozilgani va auditda ko'rinishi — `test_payments_api.py::test_a_changed_amount_with_a_reason_is_written_and_audited` (`audit_log` da aktor, ESKI va YANGI summa hamda kvota to'plami). Sabablar reyestri yopiq (`ReversalReason`/`AdjustmentReason`, `other` a'zosi YO'Q) va uchala locale'da matni bor | Sabab-kodlarning **amalda to'g'ri tanlanishi** — kassir «boshqa» yo'qligida qaysi sababni bosadi degan savol inson kuzatuvi bilan javob oladi |
| **CASH-03** | `Pending` -> **`Done`** | `test_sc5_idempotent_payment_reversal_and_blind_variance` (a)/(c) — bir xil `idempotency_key` bilan ikki `POST`: `payments` da **1 qator**, ikkinchi javob **200** va **o'sha `payment_id`**; `UPDATE payments` -> `RaiseException`; storno **YANGI qator** (`kind='reversal'`) va sababsiz storno `CheckViolation`. Uch tez bosish -> bitta so'rov (`payment-bar.test.tsx`, `toHaveLength(1)`), parallel ikki so'rov -> bitta qator (`test_payments_api.py`, `asyncio.gather`) | Tarmoq **haqiqiy** uzilishi: qayta yuborish oynasi mobil tarmoqda, offlayn navbat bilan o'lchanmagan (V2-CASH-05) |
| **CASH-04** | `Pending` -> **`Done`** | `test_sc5` (d) — `POST /shifts/{id}/close` javobining kalitlar to'plami AYNAN to'rtta va `system_*` **umuman yo'q**; variance **serverda** hisoblanadi va FAQAT `GET /shifts?day=` da (direktor sessiyasi) qaytadi, IKKI YO'NALISHDA: `declared < system` -> **-5 000**, `declared > system` -> **+7 000** (har xil kattalikda — modul-kattalik sabotaji S-5 buni QIZARTIRDI). Ekran qatlami — `shift-close-form.test.tsx` (yopilgandan keyin AYNAN uchta narsa) va `variance-list.tsx` | Kassirning **haqiqatan ko'r qolishi**: u smenaning jamini boshqa yo'ldan (qog'oz daftar, o'z hisobi) chiqarib ololmasligi tashkiliy shart, texnik emas. `GET /payments/recent` oynasi serverda qat'iy beshta, lekin kassir kun davomida yozganini eslab qolishi mumkin — bu D-25 ning ochiq narxi |

⛔ **BIRORTA BAND `Blocked` EMAS VA BU DA'VO EMAS, O'LCHOV NATIJASI.**
To'qqizala talabning har jumlasi CI'da real artefakt bilan bajariladi.
Yuqoridagi «Nima o'lchanMAGAN» ustuni **inson idroki, real qurilma va
tashkiliy shart** haqida — ya'ni ular talab MATNINING jumlalari emas.
Aynan shu sababdan bu fazada `06-HUMAN-UAT.md` fayli **YARATILMADI**.

### Qoidaning 7-fazadagi qo'llanishi (2026-08-12, `07-17`) — DALIL BILAN

To'qqizala band `Pending` -> **`Done`**.

⛔ **LEKIN BU FAZA 6-FAZADAN BIR JIHATI BILAN JIDDIY FARQ QILADI VA U
YASHIRILMAYDI:** bu yerda birinchi marta **ishonch chegarasi ochiladi** —
har xabar **Telegram serverlariga**, ya'ni O'zR data-rezidentlik
chegarasidan **tashqariga** chiqadi. CI'da esa haqiqiy Telegram **YO'Q**.

Yechim soxtalashtirish EMAS: mahsulot jo'natuvchisi (`AlertSender`)
**oxirigacha** yuritiladi va `respx` faqat **tarmoq chegarasini** tutadi
(`assert_all_mocked=True` — tutilmagan so'rov QIZIL). O'lchanadigan narsa
navbat qatorining holati emas, **AYNAN CHIQQAN HTTP SO'ROVI va uning
tanasi**. Ya'ni «xabar ketdi» da'vosi mahsulot yo'lining chiqishidan
o'qiladi. ⚠ O'lchanmagani — **Telegram ning o'zi qabul qilishi**: u
`07-HUMAN-UAT.md` ning 1-bandi (ega: Ops, tetik: birinchi deploy).

⚠ **IKKINCHI CHEGARA — IKKI KOD BAZASI.** `BOT-01`/`BOT-02` ning
`contact` yarmi `bot-service` konteynerida yashaydi va u mezon
modulida **import qilinmaydi** (ikkala kod bazasi ham `app` paketiga ega;
aiogram `pydantic<2.14` va `redis<8` ni, core-api esa `redis==8.0.1` ni
qadaydi). Shuning uchun o'sha ikki qator **IKKI buyruq** bilan
belgilangan va ikkalasi ham quyida yozilgan.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **RECON-01** | `Pending` -> **`Done`** | `test_phase7_criteria.py::test_sc1_report_shows_both_classes_with_evidence_links` — seed IKKALA sinfni ham yozadi (to'lanmagan `daily_charges` + dalilli `billing_anomalies`), `reconciliation_open` jobi **CHAQIRILADI** (case qo'lda yozilmaydi), so'ng `GET /reconciliation/report` HTTP orqali: `subject_kind` to'plami AYNAN `{occupied_unpaid, anomaly}`, ikki sanoq ALOHIDA, har qatorda `evidence_snapshot_ids` BO'SH EMAS va har biri `UUID`. ⛔ Javob tanasida `presigned`/`http`/`image` satrlari **YO'Q** va rekursiv skanda shaxsiy maydon **0** (`vendor_id` nazorat sifatida BOR). Marshrutning qolgan qirralari — `test_reconciliation_api.py` | Dalil kadrining direktor uchun **o'qilishi** (nizoda yetarlimi) — inson idroki. ⚠ Hisobot qatorlari **case'dan hosila**, ya'ni SINF A kechikish chegarasidan (`overdue_days`, bugun 3) o'tgandan keyin ko'rinadi — test buni ikki `recon.open` chaqiruvi bilan OCHIQ ifodalaydi |
| **RECON-02** | `Pending` -> **`Done`** | `test_sc2_case_is_managed_and_hit_rate_is_derived` — job UCHTA case ochadi (`(anomaly_cases, unpaid_cases) == (2, 1)`), `PATCH` bilan `new`->`in_review`->`justified`: `reconciliation_case_events` da **AYNAN 2** qator, `events[].to_status` ketma-ketligi, `actor_user_id` **direktorning identifikatori** (`None` «TIZIM» degani bo'lardi), `resolution_note` javobda. Holat to'plami **YOPIQ**: `"other"` -> **422**. Hit-rate `justified=1, unjustified=1` da **0.5**, `open_cases=1` maxrajga **kirmaydi** (uchinchi case ATAYIN `new`), o'lchovsiz oraliqda **`null`** | Direktorning case'ni **amalda yuritishi** (kim mas'ul qilib tayinlanadi, yechim matni qanday yoziladi) — tashkiliy shart |
| **RECON-03** | `Pending` -> **`Done`** | `test_sc3_...` (a) — `digest_evening(as_of=D)` + `digest_morning(business_date=D)` chaqiriladi, so'ng `outbox_tick` **`respx` bilan**: Telegram'ga **AYNAN 2** so'rov, ikkalasi ham **direktorning chatiga**, kechkida «kutilayotgan», ertalabkida «yozilgan» o'zagi va ular **ARALASHMAYDI** (G-35), ikki matnning pul qatori **BIR XIL EMAS** (D-15/D-16 ning manba farqi), matnlarda **sotuvchi ismi YO'Q**. Manba farqi alohida — `test_notifications.py` | ⛔ **HAQIQIY TELEGRAM YETKAZISHI CI'DA BAJARILMAYDI** — `respx` tarmoq chegarasini tutadi. Bu `07-HUMAN-UAT.md` **1-bandi** (ega: Ops, tetik: birinchi deploy). Dayjestning direktor uchun **o'qilishi** — 3-band (5 sotuvchi/direktor sinovi) |
| **RECON-06** | `Pending` -> **`Done`** | `test_sc3_...` (b) — `GET /me/headline` UCH rolda (direktor/kassir/nazoratchi) **UCH XIL** `metric` beradi va javob maydonlari to'plami **AYNAN** `{"metric","value"}` (`len(body)==2` YETARLI EMAS: maydon almashtirilganda yashil qolardi). ⛔ Kassir qiymati **SANOQ** (`1`) va kunning summasiga (`15 000`) **TENG EMAS**. Rol matritsasi va ikki rolli foydalanuvchi — `test_headline.py` | Bosh ekranning **telefon**da ko'rinishi (jsdom brauzer emas) |
| **CASH-05** | `Pending` -> **`Done`** | `test_sc5_...` (1-qadam) — `POST /payments` **o'sha tranzaksiyada** navbat qatori qoldiradi; bir xil `idempotency_key` bilan takror `POST` **ikkinchi qator bermaydi** (`dedupe_key == receipt:{payment_id}`). Tranzaksiya birligi va Telegram yiqilganda to'lovning o'tishi — `test_receipt_outbox.py` (07-12). Matn mazmuni (summa/rasta/kassir/vaqt) — `outbox.py::_receipt_text` + `test_outbox.py` | Kvitansiyaning sotuvchi **telefonida** ko'rinishi va «zudlik» ning **his qilinishi** — UAT 3-bandi |
| **BOT-01** | `Pending` -> **`Done`** | ⛔ **IKKI MANBADAN.** (a) Server yarmi — `test_sc4_vendor_binds_and_sees_own_debt_and_history`: `POST /internal/bot/resolve` telefon reestrda **yagona** bo'lganda `bound`, `Set-Cookie` **YO'Q** (D-10); ikki bozorda **bir xil telefon** -> `multiple_matches` va `vendor_telegram_bindings` da qator **0** (D-26b). Buyruq: `docker compose --profile test run --rm tests pytest tests/integration/test_phase7_criteria.py -q`. (b) `contact` yarmi — **BOSHQA KONTEYNERDA**: `docker compose --profile test run --rm bot-tests pytest tests/unit/test_binding.py -q` (D-24 ning uch rad javobi: `user_id is None`, `user_id != from_user.id`, guruh chati) | ⛔ **`request_contact` tugmasining HAQIQIY klientlardagi xulqi** — `Contact.user_id` ning sender bilan teng kelishi iOS/Android/Desktop da (tadqiqot buni MEDIUM-HIGH ishonch bilan yozgan). UAT **4-bandi** |
| **BOT-02** | `Pending` -> **`Done`** | ⛔ **IKKI MANBADAN.** (a) `test_sc4_...` — `GET /internal/bot/vendor/summary` qaytargan son `billing_repo.vendor_outstanding()` bilan **`==` TENG** (nol emasligi nazorat bilan), `GET /internal/bot/vendor/payments` qatorlari `vendor_charge_allocation()` **DAN HOSILA** (`service_date`/`stall_code`/`due_soum` uchligi bo'yicha ro'yxat tengligi); javobda `balance` va shaxsiy maydon **yo'q**. (b) Bot tomonidagi ekran matni — `docker compose --profile test run --rm bot-tests pytest tests/unit/test_vendor_handlers.py -q` | Matnning **sotuvchi uchun tushunarliligi** («qoldiq» va «patta» ni ajrata oladimi) — UAT **3-bandi**, o'qish savodxonligi past foydalanuvchi bilan |
| **BOT-03** | `Pending` -> **`Done`** | `test_sc5_...` (2- va 3-qadam) — 30 kunlik qarz: `overdue_days=3` bo'lgan A bozorida eslatma **1**, `overdue_days=90` bo'lgan B bozorida **0** (chegara bozor kesimida). Quiet oynada (22:30) eslatma **YUBORILMAYDI** va u **navbatdan ham OLINMAYDI** (`attempt_count == 0` — «ushlab qolindi» ni «manzili topilmadi» dan ajratadigan da'vo), o'sha tikda kvitansiya esa **BORADI**. Idempotentlik (kuniga bitta) va knobning `recon.open` bilan umumiyligi — `test_notifications.py` | `overdue_days` va quiet-hours **standartlari** buyurtmachi bilan tasdiqlanmagan (`[ASSUMED]` A2/A3) — UAT **7-bandi** |
| **BOT-04** | `Pending` -> **`Done`** | `test_sc5_...` (4- va 5-qadam) — `403` -> `blocked`, `attempt_count == 1` va **ikkinchi tikda `respx` chaqiruvlari soni O'SMAYDI** (holat ustuniga qarash YETARLI EMAS). ⛔ **SABOTAJ BAJARILDI:** `outbox.py::_classify` da `403` shoxi `RETRY` ga o'zgartirilganda test **QIZARDI** (`1 -> 2`). Holat direktor yuzasida **KO'RINADI** (`GET /reconciliation/delivery` — `blocked` qatori va hisoblagichi), javobda shaxsiy maydon yo'q. Throttling, backoff, `429`/`retry_after` va token sizmasligi (G7-5) — `test_outbox.py` | ⛔ **«Yetkazildi» so'zining sotuvchi uchun MA'NOSI**: Bot API yetkazilganlik kvitansiyasini **BERMAYDI** — `delivered` = «Telegram 200 qaytardi», «o'qildi» EMAS. Kod buni to'g'ri yozadi; nizoda direktor buni **tushuntira oladimi** — UAT **2-bandi** |

⚠ **`Blocked` BAND YO'Q, LEKIN «hammasi o'lchandi» HAM DEYILMAYDI.**
5-fazadan farqli o'laroq bu yerda talab matnining birorta jumlasi
o'lchovsiz qolmadi — shuning uchun `Blocked` yo'q. Lekin yuqoridagi
oxirgi ustun **yettita** bandni nomlaydi va ular `07-HUMAN-UAT.md` ga
**ega va tetik bilan** chiqarildi. Ular talab jumlalari emas: ular
**tashqi xizmat**, **haqiqiy klient** va **inson idroki** haqida.

### Qoidaning 8-fazadagi qo'llanishi (2026-08-16, `08-20`) — DALIL BILAN

Uch banddan **ikkitasi** `Pending` -> **`Done`**, **bittasi**
`Pending` -> **`Blocked`**. ⛔ Uchinchisi 7-fazadan qaytish emas —
u **qoidaning aynan o'zi**: talab MATNINING bir jumlasi CI'da
bajarilmasa, band `Done` bo'lmaydi.

⛔ **FOUND-07 NING IKKI JUMLASI IKKI XIL NARSA VA ULARNI QO'SHIB
BO'LMAYDI.** Birinchisi mexanizm haqida («kunlik avtomatik backup ...
boshqa lokatsiyaga»), ikkinchisi FAKT haqida («tiklash mashqi kamida bir
marta o'tkazilgan»). Mexanizm to'liq qurilgan va uch qatlamda
qulflangan; fakt esa **hech qachon** CI'da tug'ilmaydi — u REAL offsite
repo va REAL toza serverda, bir marta, ODAM tomonidan yoziladi. Bu
farq `test_phase8_criteria.py::test_sc3_*` docstringida ham **literal**
yozilgan, ya'ni u ikki joyda bir xil aytiladi.

⚠ **RECON-05 `Done` VA AI-02 `Blocked` — BU ZIDDIYAT EMAS.** Ikkalasi
BOSHQA talab: AI-02 «RF-DETR ONNX Runtime CPU da har zonani baholaydi»
deydi (model artefakti va uning ANIQLIGI haqida, 5-faza), RECON-05 esa
«aniqlik HISOBOTI ko'r audit namunasidan chiqadi va xatolik turlarini
ajratadi» deydi (o'lchov qurilmasi haqida). O'lchov qurilmasi
detektorning qanchalik yaxshi ekanidan **mustaqil** ishlaydi va aynan
shuning uchun u xolis: u model yomon bo'lganda ham to'g'ri raqam
beradi. AI-02 ning `Blocked` holati RECON-05 ni **bloklamaydi**.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **RECON-04** | `Pending` -> **`Done`** | `test_phase8_criteria.py::test_sc1_director_reads_three_reports_and_downloads_each_as_a_real_xlsx` — uchala JSON marshruti (`/reports/revenue`, `/debtors`, `/anomalies`) direktor sessiyasida `200` va BO'SH EMAS (tushum qatorida `charged_soum`, reestrda kamida bitta qator, arxivda `unpaid_count == 1`), so'ng uchala `.xlsx` bayti **QAYTA O'QILADI** (`xlsx_reader.read_rows` — hajm -> ZIP -> parse) va sarlavha qatori matn katalogidan hosila. ⛔ `200` mezon EMAS va bu MEXANIK: mezon modulining 4-darvozasi hujjat yo'liga tegib javob KODI haqida da'vo qilgan HAR testda o'quvchining chaqirilishini talab qiladi. Marshrutning qolgan qirralari (huquq matritsasi, bitta `audit_read`, davr chegaralari, cross-tenant, sahifalash, bayt-determinizm) — `test_reports_api.py` + `test_report_repo.py` + `test_xlsx_export.py`. To'rtinchi eksport (`accuracy.xlsx`) va imzoli beshinchisi (`compare.xlsx`) — SC#2/SC#5 | Direktorning hisobotni **amalda o'qishi va qarorga aylantirishi** — inson idroki; `08-HUMAN-UAT.md`. ⚠ Davr arxivida uchinchi/to'rtinchi anomaliya sinfi (`closed_day`, `no_coverage`) YO'Q — ular KUNLIK ekranda ko'rinadi, davr hisobotida emas (`deferred-items.md` №1) |
| **RECON-05** | `Pending` -> **`Done`** | `test_sc2_accuracy_report_comes_from_the_blind_sample_and_splits_two_error_kinds` — 30 zona-hodisali doira quriladi, namuna **`audit_draw` bilan TORTILADI** (qo'lda yozilmaydi), butun namuna nazoratchi sessiyasidan javoblanadi va `.xlsx` bayti qayta o'qiladi. IKKI da'vo: (a) **manba** — hujjatdagi son `eval` javoblariga TENG (`train` yarmi tushmaydi) va `eval` bandlarining navbat turi AYNAN `blind_audit`; (b) **ajratilganlik** — «band deb xato» va «bo'sh deb xato» ALOHIDA qator va ularning MAXRAJI boshqa: shu namunada birinchisi **o'lchanadi** (`fp/(tp+fp)` = 1,0), ikkinchisi esa **BO'SH KATAK** bo'lib qoladi (`tp+fn = 0`). Ikkalasi bir maxrajga qo'shilganda ikkala katak ham to'lardi. Formulalarning SOF arifmetikasi — `tests/unit/test_accuracy_report.py`; ko'r serializer va 70/30 — `test_blind_audit.py` | ⛔ **DETEKTORNING HAQIQIY ANIQLIGI** — u BOSHQA talab (AI-02, `Blocked`) va u bu yerda o'lchanmaydi. Hisobot xolis o'lchov QURILMASI: u model yomon bo'lganda ham to'g'ri raqam beradi. Namunaning HAJMI (kunlik 30) real bozorda yetarlimi — `08-HUMAN-UAT.md`, egasi direktor |
| **FOUND-07** | `Pending` -> ⛔ **`Blocked`** | **Mexanizm uch qatlamda o'lchangan:** (a) zanjirning statik shakli — `tests/unit/test_backup_contract.py` (quvur YO'Q, `--compress=0`, yurak urishi ENG OXIRIDA va `trap` ichida emas, komponent nomi `alerting.BACKUP_COMPONENT` bilan bir xil); (b) yurak urishi halqasi — `test_backup_heartbeat.py` va `test_phase8_criteria.py::test_sc3_*`: SQL **mahsulot faylidan** (`ops/backup/heartbeat.sql`) o'qiladi, yozilishidan OLDIN `/internal/self-check` komponentni `never_seen` da ko'rsatadi, yozilgandan KEYIN chiqaradi; (c) tiklash MEXANIZMI — `test_restore_drill.py` (`pg_dump` -> TOZA `postgres:18.4` konteyneri -> `pg_restore` -> moliyaviy qatorlar, `pg_policies` va `audit_log` joyida) va u standart to'plamdan CHIQARILMAGAN (mezon `addopts` ni o'qib tekshiradi). ⛔ Mezon modulida yurak urishini QO'LDA yozadigan xom SQL **AST bilan taqiqlangan** | ⛔ **TALAB MATNINING IKKALA JUMLASI HAM YARIM QOLDI.** «Boshqa lokatsiyaga ketadi» — REAL offsite `restic` repo'si kerak, `RESTIC_REPOSITORY`/`RESTIC_PASSWORD` esa `.env` da **YO'Q** (`docker compose` ularni bo'sh satr bilan almashtiradi), ya'ni zanjir bugun **umuman yugurmaydi** va `backup_stale` (CRITICAL, `never_suppressed`) go-live'dan keyin ham chiqib turadi — ⛔ uni o'chirish TAQIQ. «Toza serverda tiklash mashqi kamida bir marta muvaffaqiyatli o'tkazilgan» — REAL VPS kerak. **Egasi: Ops. Tetigi: VPS deploy'i. Bandlari: `08-HUMAN-UAT.md` #1 va #2.** ⚠ Uchinchi ochiq band: tiklangan bazada `sbozor_app` ning **0 GRANT**i bor (`deferred-items.md` №5) — tiklash tartibiga migratsiyani qayta yugurtirish qadami kerak va u **o'lchanmagan** |

⛔ **NEGA `Blocked`, «deyarli tayyor» EMAS.** Uchala qatlam ham yashil,
zanjir kodda to'liq va u ishlashga tayyor — lekin **bugun u hech qachon
yugurmagan**. `Done` qo'yish 2-fazaning `02-VERIFICATION.md` da
hujjatlashtirilgan xatosining aynan takrori bo'lardi (890 yashil test
ortida to'rtta haqiqiy bo'shliq) va u **falokat kunida**, eng yomon
paytda ko'rinardi. ⚠ `Blocked` bu yerda ham «ish to'xtadi» degani EMAS —
u «dalil to'liq emas va yetishmayotgan dalil NOMLANGAN» degani.

### Qoidaning 10-fazadagi qo'llanishi (2026-08-17, `10-08`) — DALIL BILAN

Beshala LAND bandi shu fazada TUG'ILDI va shu fazada belgilandi:
**to'rttasi** `Done`, **bittasi** (`LAND-05`) `Blocked`. Bu nisbat 3-,
5- va 8-fazalarning shaklini takrorlaydi va ATAYIN: LAND-05 ning mexanik
yarmi to'liq o'lchangan, lekin talab MATNIDAGI ikki raqam (Lighthouse
≥95, LCP <1,5 s) CI'da bajarilmaydi.

⚠ **`Done` NIMANI ANGLATMAYDI.** Birorta qator «real sbozor.uz domenida,
real tashrif buyuruvchi bilan ishlaydi» degan da'voni bermaydi: frontend
da'volari jsdom + fayl-skan darvozalarida, backend da'vosi `respx` tutgan
tarmoq chegarasigacha o'lchangan. Oxirgi ustun har qatorda nima
o'lchanMAGANini ochiq aytadi va uning egasi `10-HUMAN-UAT.md` da turadi.

| Talab | Yangi holat | Nima o'lchandi va QAYSI test bilan | Nima o'lchanMAGAN |
|---|---|---|---|
| **LAND-01** | **`Done`** (tug'ilishida) | `phase10-criteria.test.mjs::SC#1` — eski himoyalangan `[locale]/page.tsx` YO'Q, `(marketing)/page.tsx`+`layout.tsx` BOR, `prerender-manifest.json` da `/uz-Latn`·`/uz-Cyrl`·`/ru` uchalasi (build artefakti bilan), header'da `/login`; `landing-surface.test.mjs` G-land-1(a–d): klient orollari reyestrga `deepEqual`, LCP faylida `"use client"` 0, provayder nomlari ikki tomonlama; SSG ning o'zi — `npm run gate` ning `next build` qadami (86 marshrut) | Haqiqiy **sbozor.uz** domenida servis (DNS, TLS, birinchi deploy) — Ops tetigi. Anonim tashrifchining REAL brauzer/qurilmadagi idroki (`10-HUMAN-UAT.md` #1/#3) |
| **LAND-02** | **`Done`** (tug'ilishida) | `hero-scene.test.tsx` (G-land-2 a–e): reduced-motion'da `setTimeout` 0 va DOM to'liq final-kadr; 0 ms da final-kadr, 13 500 ms da 1-fazaga qaytish; beshala faza yorlig'i ketma-ket; `unmount()` da `clearTimeout` = yaratilgan taymerlar; IO `isIntersecting:false` → yangi taymer 0; `landing-surface.test.mjs` G-land-3: transition xossalari ruxsat to'plami ⊂, `setInterval` 0, `@keyframes` 9 nom; `phase10-criteria::SC#2` — `<video>` 0 | **60fps real arzon Androidda** — jsdom kadr tushishini o'lchay olmaydi; `container-type`/`100cqw` xulqi [A2]. Bandlari: `10-HUMAN-UAT.md` #3 (KADR/SONIYA bilan) |
| **LAND-03** | **`Done`** (tug'ilishida) | `tests/integration/test_demo_request.py` (7 band): anonim POST autentifikatsiyasiz muvaffaqiyat + `Set-Cookie` YO'Q + javobda tenant izi YO'Q; 429 `rate_limited`; 422 `invalid_phone` (`normalize_phone`); honeypot → jim muvaffaqiyat, Telegram'ga 0 chaqiruv; yetkazish yiqilsa `delivery_failed` VA DB'da 0 yangi qator; `tests/tenancy/test_route_coverage.py` — `EXEMPT_ROUTES` qamrovi tiklangan (sabab `global` bilan); `demo-form.test.tsx` — holatlar + a11y; `error-codes.test.mjs` oltinchi juftlik — `DEMO_ERROR_CODES` ko'zgu + `landing.form.*` uchala tilda | **Haqiqiy Telegram chatiga tushishi** — `respx` tarmoq chegarasini tutadi; token/chat_id konfiguratsiyasi, chat huquqi va xabarning admin uchun o'qilishi. Bandi: `10-HUMAN-UAT.md` #4 («N dan M tasi chatga tushdi», SOXTA PII bilan — T-10-25) |
| **LAND-04** | **`Done`** (tug'ilishida) | `landing-surface.test.mjs` G-land-4(a–g): `sampleBadge` shartli render TASHQARISIDA, «namunаviy» o'zagi uchala locale'da, `trustBlock.residency.body` uchala tilda + hero anchor, FAQ JSON-LD matni katalogdan, taqiq da'vo tokenlari 0, `landing.pilot.*` da raqam 0, kirill override'lar; `phase10-criteria::SC#4` — pilot rozetkasi + residency + raqam-skan MUSTAQIL ikkinchi qatlam; `glossary.test.mjs` + `i18n:check` parity | Matnning **davlat auditoriyasida o'qilishi** (semantik siljish — `АИ`/`демонстратсия` sinfi darvoza ko'rmaydi) va **residency bandining yurist tasdig'i**. Bandlari: `10-HUMAN-UAT.md` #5 («N ta tuzatish») va #6 (go-live, STATE «Huquqiy ko'rik» tuguni) |
| **LAND-05** | ⛔ **`Blocked`** (tug'ilishida) | **Mexanik yarim TO'LIQ:** `sitemap.ts`/`robots.ts` mavjud, `openGraph` + `application/ld+json` sahifada (rasmiy escape), `--text-hero` `@theme` da — `phase10-criteria::SC#5` + `landing-surface` G-land-5; **payload farqi O'LCHANGAN** (10-03: ildiz JS 287,8→208,4 KB gz, HTML(ru) 32,3→8,0; `10-HUMAN-UAT.md` #2 SON bilan YOPIQ) | ⛔ **Talab matnining ikki RAQAMI CI'da UMUMAN o'lchanmaydi:** Lighthouse ≥95 va LCP <1,5 s — Lighthouse qo'shilmagan (10-UI-SPEC §16.5 [QAROR]: headless Chrome `gate` byudjetiga daqiqalar qo'shardi); 60fps ham real qurilmasiz. Mexanika yashilligi bilan o'lchov yo'qligini yopish TAQIQ (D-01, FOUND-07, AI-02). **Egasi: ijrochi. Tetigi: birinchi deploy. Bandlari: `10-HUMAN-UAT.md` #1 va #3** |

⚠ **`Blocked` bu yerda ham «ish to'xtadi» degani EMAS** — u «dalil to'liq
emas va yetishmayotgan dalil NOMLANGAN» degani. LAND-05 ning yopilish
yo'li o'z qatorida: birinchi deploy'da Lighthouse mobile profili bilan
uchala locale o'lchanadi va `10-HUMAN-UAT.md` #1 SON bilan imzolanadi.

⚠ **Faza mezonlari (SC#1…SC#5) bundan MUSTAQIL** va beshalasi ham yashil
(`frontend/scripts/phase10-criteria.test.mjs`, bitta buyruq). Mezonlar
fazaning yetkazib berish mahsulotini o'lchaydi — SC#5 ning mezon testi
SEO MEXANIKASINI tasdiqlaydi va o'z xato matnida Lighthouse/LCP bu yerda
o'lchanmasligini LITERAL aytadi; LAND-05 esa talab JUMLASINI belgilaydi
va aynan o'sha ikki raqam uchun `Blocked` turadi.

Yuqoridagi ro'yxat va bu jadvalning bir-biriga mosligi mexanik tekshiriladi:
`node scripts/check-requirements-sync.mjs` — qo'lda, har faza yopilishida
(doimiy CI darvozasi emas; sabab skript boshida yozilgan).

**Coverage:**

- v1 requirements: 54 total
- Mapped to phases: 54 ✓
- Unmapped: 0

**Faza kesimida:**

| Phase | Nomi | Talablar soni |
|-------|------|---------------|
| 1 | Poydevor va tenant xavfsizligi | 5 |
| 2 | Bozor domeni va "Yangi bozor" ustasi | 7 |
| 3 | NVR avtomatik kashfiyoti va tarmoq ulanishi | 5 |
| 4 | Snapshot pipeline | 5 |
| 5 | Kamera zonalari, CV va nazoratchi tasdig'i | 6 |
| 6 | Billing va kassir | 9 |
| 7 | Nomuvofiqlik, bildirishnoma va botlar | 9 |
| 8 | Hisobotlar, mustahkamlash va ishga tushirish | 3 |
| 10 | Landing — sbozor.uz | 5 |

*(9-faza qatori YO'Q va bu atayin: u yangi REQ-ID yaratmagan — ROADMAP
«Yangi REQ-ID YARATILMAYDI» bandi, 09-RESEARCH A7.)*

✅ **Sanoqlar 2026-08-17 da (`10-08`) faylning O'Z mazmunidan qayta
hisoblangan:** checkbox ro'yxati 54 ta band, Traceability jadvali 54 ta
qator beradi va ular faza bo'yicha 5/7/5/5/6/9/9/3/5 ga taqsimlanadi
(49 + 10-fazaning beshta LAND bandi). Oldingi qayta hisoblash 2026-08-02
(`02-24`, 46→49) — o'shanda ham eskirgan son jimgina yashab qolmagan:
`node scripts/check-requirements-sync.mjs` farqni har ishga tushganda
ogohlantirish sifatida ko'rsatib turadi.

---
*Requirements defined: 2026-07-29*
*Last updated: 2026-08-17 — `10-08`: beshta LAND talabi tug'ildi (ROADMAP
Phase 10 SC#1…SC#5 bilan bir-birga xaritalangan). LAND-01…04 o'lchangan
dalil bilan `Done` (dalillar jadvalda nomma-nom); LAND-05 `Blocked` —
Lighthouse ≥95 va LCP <1,5 s CI'da umuman o'lchanmaydi (egasi ijrochi,
tetigi birinchi deploy, bandlari `10-HUMAN-UAT.md` #1 va #3; payload
farqi esa 10-03 da O'LCHANGAN va #2 SON bilan yopiq). `**Coverage:**`
va `Faza kesimida` sanoqlari fayl mazmunidan qayta hisoblandi (49 → 54).
Yo'l-yo'lakay meros nomuvofiqlik tuzatildi: FOUND-07 ro'yxatda `[x]`
qolib ketgan edi (08-20 uni jadvalda `Blocked` qilgan) — belgi jadvalga
moslandi (`- [ ]`), 03-14 dagi CAM-02 presedenti bilan bir xil sinf.
Sanoq: Done 45 · Pending 5 · Blocked 4.*
*Oldingi: 2026-08-05 — `04-14`: FOUND-06 ning dalili SANOQDAN
HOSILAGA o'tkazildi. Holat O'ZGARMADI (`Done` bo'lib qoladi) — o'zgargani
DALILNING SHAKLI: «`init_sentry` shu ikki/uch kirish nuqtasida
chaqiriladi» ro'yxati o'rniga «`compose.yaml` da `SENTRY_DSN` oladigan HAR
jarayon Sentry o'rnatishi TALAB QILINADI» hosilasi
(`tests/unit/test_sentry_processes.py`). Sabab `04-VERIFICATION.md` da
o'lchangan: ro'yxatga tayangan dalil n+1-jarayonni struktura jihatidan
ko'ra olmaydi va aynan shu bo'shliq fazani `gaps_found` qilgan edi.
Chegara ustuniga uchinchi inson bandi qo'shildi (`04-HUMAN-UAT.md` #7 —
hodisaning haqiqiy Sentry loyihasiga yetib borishi, egasi Ops). Sanoq
o'zgarmadi: Done 16 · Pending 32 · Blocked 1.*
*Yangilandi: 2026-08-10 — `05-15`: 5-fazaning oltita talabidan beshtasi
(AI-01, AI-03, AI-04, AI-05, AI-06) o'lchangan dalil bilan `Done`; AI-02
`Blocked` — «detektor har zonani baholaydi» jumlasi CI'da REAL ONNX
artefakti bilan bajarilmaydi va modelning aniqligi oltin to'plam
bo'shligi uchun umuman o'lchanmagan (egasi nazoratchi + Ops, tetigi
Phase 0 kadrlari va GPU ijarasi, bandlari `05-HUMAN-UAT.md` #1, #2, #3).
Sanoq: Done 21 · Pending 26 · Blocked 2.*
*Oldingi: 2026-08-05 — `04-12`: 4-fazaning beshala talabi (CAM-04,
CAM-05, CAM-06, CAM-07, FOUND-06) o'lchangan dalil bilan `Done`; har
birining dalili va CHEGARASI yuqoridagi jadvalda nomma-nom. FOUND-06
ning holati oldindan yozilgan shart bo'yicha qo'yildi: `04-HUMAN-UAT.md`
ning #4 va #5 bandlari ega (Ops) va tetik bilan yozilgani uchun `Done`
(aks holda `Blocked` bo'lardi). Sanoq: Done 16 · Blocked 1 (CAM-02,
3-fazadan).*
*Oldingi: 2026-08-03 — `03-14`: GAP-1 va GAP-2 mock'siz uchidan-uchiga
o'lchov bilan yopilgach CAM-03 va CAM-09 `Blocked` -> `Done`
(dalil: `tests/integration/test_live_view_e2e.py` — kashfiyot hosil qilgan
oqimdan HAQIQIY JPEG kadr); CAM-02 `Blocked` bo'lib QOLDI va sababi,
egasi (Ops), tetigi (VPS deploy'i) hamda bandi (`03-HUMAN-UAT.md` #1, #2)
nomlandi. Sanoq: Done 11 · Blocked 1.*
*Oldingi: 2026-08-03 — `03-11`: CAM-01 va CAM-08 o'lchangan dalil bilan
`Done`; CAM-02, CAM-03, CAM-09 yetishmayotgan dalili NOMLANGAN holda
`Blocked`; «Faza kesimida» jadvalidagi 3-qator ROADMAP'dagi faza nomiga
moslandi (eskirgan sarlavha 2026-08-01 dagi qayta nomlashdan keyin
qolib ketgan edi — oldingi qiymati `03-11-SUMMARY.md` da) va soni (5)
Traceability qatorlaridan qayta hisoblandi.*
*Oldingi: 2026-08-02 — `02-24`: MARKET-07 (xodimlar rosteri importi)
o'lchangan dalil bilan `Done` qilindi va 2-faza talablari to'liq yopildi;
`**Coverage:**` hamda `Faza kesimida` sanoqlari faylning O'Z mazmunidan
qayta hisoblandi (46 -> 49)*
