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
| FOUND-06 | Phase 4 | Done |
| FOUND-07 | Phase 8 | Pending |
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
| **FOUND-06** | `Pending` -> **`Done`** | `test_sc5_absence_reaches_telegram_and_sentry` — uchala tetik (o'tkazib yuborilgan slot · kamera javob bermayapti · zaxira yangilanmagan) xabar beradi va ular GURUHLANADI (bozor bo'yicha bitta, platforma bo'yicha bitta); birorta so'rovda rasm, havola yoki obyekt kaliti YO'Q (D-19). **«Xatolar Sentry'da»** — `app/observability.py::init_sentry` `SENTRY_DSN` beriladigan UCHALA jarayonda ham chaqiriladi: `app/main.py::lifespan` (`core-api`), `app/worker.py::_open_worker_resources` (`worker`, `WORKER_STARTUP`) va `app/worker.py::_install_client_observability` (`scheduler`, `CLIENT_STARTUP`). Hisob KOD kirish nuqtasi bo'yicha emas, JARAYON bo'yicha yuritiladi va uni `tests/unit/test_sentry_processes.py` `compose.yaml` dan HOSILA qiladi; `test_sc5_...` esa Sentry'ning haqiqiy planer jarayonida tirikligini SUBPROCESS bilan o'lchaydi (nazorat yugurishi DSN'siz `False` beradi). ⚠ Ikkinchisi `04-12` da, uchinchisi `04-13` da QO'SHILDI — `04-VERIFICATION.md` uchinchisining yo'qligini o'lchov bilan topgan va u fazani `gaps_found` qilgan edi | Telegram xabarining HAQIQATAN yetib borishi (token va chat ID CI'da yo'q) va tashqi dead-man's switch. ⚠ Ikkalasi ham `04-HUMAN-UAT.md` #4 va #5 da **ega (Ops) va tetik bilan** yozilgan — `Done` aynan shu shartga bog'liq edi va shart bajarildi (2026-08-01 self-service direktivasi: tashqi bog'liqlik `Blocks:` bo'lmaydi) |

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
| 3 | NVR avtomatik kashfiyoti va tarmoq ulanishi | 5 |
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
*Last updated: 2026-08-05 — `04-12`: 4-fazaning beshala talabi (CAM-04,
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
