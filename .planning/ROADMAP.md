# Roadmap: SBOZOR

## Overview

SBOZOR 12 haftada (2026-07-28 → ~2026-10-18) Karmana bozorida jonli ishga tushadi. Yo'l xaritasi bog'liqlik zanjiri bo'yicha qurilgan: avval keyinchalik retrofit qilib bo'lmaydigan poydevor (tenant izolyatsiyasi, audit, biznes-kun, o'zgarmas hisob sxemasi) → bozor domeni (rasta / tarif / sotuvchi) → tashqi ulanish (NVR / WireGuard) → kadr olish → CV aniqlash va nazoratchi tasdig'i → billing va kassir → nomuvofiqlik va botlar → hisobot va ishga tushirish. Bu ketma-ketlik uchta mustaqil tadqiqot yo'nalishida (ARCHITECTURE / PITFALLS / FEATURES) bir xil chiqqan.

Bu zanjir ustidan birinchi haftadanoq **parallel dala treki (Phase 0)** ishlaydi. U keyinroq bajarib bo'lmaydigan ikki narsani vaqtida qo'lga kiritadi: raqamlashtirishdan oldingi tushum bazasi (yig'uvchilar tizim haqida bilishidan oldin o'lchanishi shart) va NVR'ga masofaviy kirish (tashqi yetkazib berish muddati bizga bog'liq emas). Ikkalasi ham 12 haftalik, zaxirasiz jadvaldagi eng katta xavf.

Har faza "band rastadan patta to'liq yig'ilyaptimi?" savolini isbotlash zanjirining bir bo'g'ini. Oxirida direktor "band, lekin to'lovsiz" rastalarni rasm-dalil bilan ko'radi.

**Muddat:** 12 hafta, zaxirasiz. 12-faza (hafta 12) — yangi funksiya emas, mustahkamlash haftasi. Kesish ro'yxati (cut list) 1-haftada yozma kelishiladi (Phase 0), 11-haftada bosim ostida emas.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 0: Dala treki va tashqi bog'liqliklar** - Baza o'lchovi, NVR kirish, buyurtmachi qarorlari (parallel, 1-haftadan)
- [ ] **Phase 1: Poydevor va tenant xavfsizligi** - Rol, izolyatsiya, audit, biznes-kun, 3 til — retrofit qilinmaydigan qatlam
- [ ] **Phase 2: Bozor domeni va "Yangi bozor" ustasi** - Rasta, toifa, tarixiy tarif, sotuvchi, ish kunlari, sxematik plan-xarita
- [ ] **Phase 3: Kamera va tarmoq ulanishi** - WireGuard tunnel, shifrlangan RTSP, ulanish testi, jonli ko'rish
- [ ] **Phase 4: Snapshot pipeline** - Mavsumiy jadval, idempotent kadr olish, sifat filtri, S3 arxiv, alertlar
- [ ] **Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i** - Poligon muharriri, RF-DETR aniqlash, noaniq navbati, ko'r audit
- [ ] **Phase 6: Billing va kassir** - O'zgarmas kunlik patta, dalil bog'lash, qarz, ≤3 bosishli kassir, smena hisobi
- [ ] **Phase 7: Nomuvofiqlik, bildirishnoma va botlar** - "Band, lekin to'lovsiz" case oqimi, sotuvchi va direktor botlari
- [ ] **Phase 8: Hisobotlar, mustahkamlash va ishga tushirish** - Excel eksport, AI aniqlik hisoboti, backup mashqi, go-live

## Phase Details

### Phase 0: Dala treki va tashqi bog'liqliklar (PARALLEL TRACK)

**Goal**: Loyihaning tashqi bog'liqliklari va o'lchov bazasi 2-hafta oxiriga qadar qo'lga kiritilgan bo'ladi — keyinroq bajarib bo'lmaydigan ishlar o'z vaqtida bajariladi
**Depends on**: Hech narsa — 1-haftadan boshlanadi, 1–8 fazalar bilan parallel ishlaydi
**Timeline**: Hafta 1–2 (2026-07-28 → 2026-08-09); kuzatuv 12-haftagacha davom etadi
**Requirements**: — (dala/ops ishi; v1 REQ-ID biriktirilmagan)
**Success Criteria** (what must be TRUE):

  1. Birinchi haftaning har kuni uchun imzolangan baza varaqasi mavjud: band rastaga to'g'ri keladigan tushum (nafaqat umumiy summa) — yig'uvchilar tizim kelishini bilishidan oldin o'lchangan
  2. NVR'ga masofaviy kirish tasdiqlangan: login/parol topshirilgan, CGNAT holati aniqlangan, kerak bo'lsa WireGuard endpoint qurilmasi buyurtma qilingan
  3. Kamera qamrovi auditi real kadrlar bilan hujjatlashtirilgan: qaysi rastalar ko'rinadi, qaysi ~10% ko'rinmaydi, kameralar balandligi/IR masofasi
  4. 2-hafta oxirigacha kamida bitta real Karmana kadri bizning omborimizda saqlangan (uchidan-uchiga yo'l isbotlangan)
  5. Buyurtmachi bilan yozma kelishuv: 7 ochiq savol javob olgan (KKM/virtual kassa, UzQR, naqd egaligi, imtiyoz/kunlik tarif, rasta almashinuvi, Telegram qamrovi, nomuvofiqlik mas'uli), aniqlik mezoni formulasi va kesish ro'yxati (cut list) tasdiqlangan

**Plans**: N/A — dala/ops ishi, kod rejasi yo'q (`/gsd-plan-phase 0` ishlatilmaydi)
**Blocks**: Phase 3 (NVR kirish ma'lumotlari), Phase 4 (real kadrlar va capture usuli tanlovi), Phase 2 va 6 rejalashtirish (7 savol javobi), Phase 8 (baza bilan solishtirish)

### Phase 1: Poydevor va tenant xavfsizligi

**Goal**: Har foydalanuvchi o'z rolida, o'z bozorida, o'z tilida xavfsiz ishlaydi va har harakat o'chmas izda qoladi
**Depends on**: Nothing (birinchi build fazasi)
**Timeline**: Hafta 1–2 (2026-07-28 → 2026-08-09)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):

  1. Foydalanuvchi o'z roli bilan kiradi (platforma admini / direktor / bozor admini / kassir / nazoratchi) va faqat o'z bozori ma'lumotini ko'radi — boshqa bozorga urinish avtomatik testda rad etiladi
  2. Foydalanuvchi tilni bir bosishda o'zbek-lotin ↔ o'zbek-kirill ↔ rus orasida almashtiradi va interfeys to'liq tarjimada qoladi
  3. Har ma'muriy/moliyaviy harakatdan keyin audit jurnalida yozuv paydo bo'ladi (kim, qachon, nima, eski→yangi) va uni tahrirlab yoki o'chirib bo'lmaydi
  4. Har sana Asia/Tashkent biznes-kuni bo'yicha, har summa butun so'mda ko'rsatiladi — yarim tunda kun chegarasi to'g'ri suriladi
  5. Moliyaviy jadvallar dublikat-himoyasi bilan tug'iladi: `UNIQUE(market_id, stall_id, business_date)` va o'zgarmas hisob konstraytlari 6-fazadan oldin allaqachon o'rnida

**Plans**: 10 plans in 7 waves
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Monorepo skeleti, Compose steki, sbozor_owner/sbozor_app rollari, Wave 0 test infratuzilmasi (W1)
- [x] 01-02-PLAN.md — Next 16 skeleti, next-intl proxy.ts routing, 3 locale, uz-Cyrl transliteratsiya va parity skriptlari (W1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-03-PLAN.md — sbozor-core primitivlari: pul (BIGINT so'm), biznes-kun, telefon, Argon2id + JWT, tenancy helperi (W2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-04-PLAN.md — Alembic async infra, RLS asboblari (NULLIF), identifikatsiya sxemasi, SECURITY DEFINER login funksiyalari, tenancy meta-test (W3)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-05-PLAN.md — audit_log + DB-trigger, 4 qatlamli o'zgarmaslik, moliyaviy konstrayt asboblari (business_date, CHECK, UNIQUE) (W4)

**Wave 5** *(blocked on Wave 4 completion)*

- [ ] 01-06-PLAN.md — Auth API: login/select-market/refresh/logout/change-password, RBAC matritsasi, tenant sessiyasi, bloklash keshi (W5)

**Wave 6** *(blocked on Wave 5 completion)*

- [ ] 01-07-PLAN.md — Foydalanuvchi boshqaruvi, profil/til, bozorlar ro'yxati, audit ko'rish API va o'qish-audit dependency (W6)
- [ ] 01-08-PLAN.md — Frontend auth qobig'i: login, majburiy parol almashtirish, bozor tanlash, app shell, til almashtirgich (W6)

**Wave 7** *(blocked on Wave 6 completion)*

- [ ] 01-09-PLAN.md — Ma'muriy ekranlar: foydalanuvchi boshqaruvi UI va audit jurnali UI + faza mezonlarining uchidan-uchiga tekshiruvi (W7)
- [ ] 01-10-PLAN.md — Cross-tenant marshrut matritsasi, marshrut qamrovi darvozasi, CI yig'imi va validatsiya imzosi (W7)

**UI hint**: yes

### Phase 2: Bozor domeni va "Yangi bozor" ustasi

**Goal**: Platforma admini kod yozmasdan yangi bozorni tizimga kiritadi va Karmananing real rasta/tarif/sotuvchi ma'lumoti tizimda yashaydi
**Depends on**: Phase 1
**Timeline**: Hafta 3–4 (2026-08-10 → 2026-08-23)
**Requirements**: MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06
**Success Criteria** (what must be TRUE):

  1. Platforma admini ustadan o'tib yangi bozor yaratadi (rekvizit → zona → rasta → toifa → tarif) va oxirida bozor ishlashga tayyor holatda ko'rinadi — kod yozilmaydi
  2. Bozor admini rastalar va sotuvchilar reestrini yuritadi: rasta holati (faol/ta'mirda/yopiq), toifasi va sotuvchi biriktirish davri o'zgaradi, har o'zgarish auditda ko'rinadi
  3. Tarif o'zgartirilganda o'tmishdagi sanaga tegishli hisob eski narxda qoladi — yangi narx faqat belgilangan sanadan ta'sir qiladi
  4. Bozor admini bayram/ishlamaydigan kunni belgilaydi va o'sha kunga patta hisoblanmaydi
  5. Bozor admini sxematik plan-xaritada rastalarni zona bo'yicha grid ko'rinishida ko'radi; rasta bosilganda uning kartasi (raqam, toifa, tarif, sotuvchi, holat) ochiladi

**Plans**: TBD
**UI hint**: yes
**Note**: Ustaning kamera / kamera-zona / snapshot-jadval qadamlari 3–5 fazalarda ulanadi. Plan-xarita **sxematik** (grid) bo'lib qoladi — to'liq interaktiv xarita v2. Ranglar to'liq to'plami (ko'k to'langan, qizil qarzdor, sariq nomuvofiq) va dalil-rasm 6–7 fazalarda yonadi. Karmananing real ma'lumoti aynan shu fazada kiritiladi — keyingi fazalar fikstura emas, haqiqat ustida sinaladi.

### Phase 3: Kamera va tarmoq ulanishi

**Goal**: Bizning serverimiz Karmana NVR'iga xavfsiz yetib boradi va direktor jonli tasvirni panelda ko'radi
**Depends on**: Phase 1; Phase 0 (NVR kirish ma'lumotlari va CGNAT holati)
**Timeline**: Hafta 3–4 (2026-08-10 → 2026-08-23) — Phase 2 bilan parallel
**Requirements**: CAM-01, CAM-02, CAM-03
**Success Criteria** (what must be TRUE):

  1. Bozor admini kamera qo'shadi va "ulanishni tekshirish" tugmasi real NVR'dan javob oladi — muvaffaqiyat yoki xato sababi aniq ko'rsatiladi
  2. RTSP login/parollari bazada shifrlangan saqlanadi — bazaga kirgan odam ham ochiq matn parol ko'rmaydi
  3. Server NVR'ga faqat WireGuard tunnel orqali kiradi; tunnel o'chirilsa ulanish uziladi va NVR internetdan to'g'ridan-to'g'ri ochiq emas
  4. Direktor avtorizatsiyadan keyin panelda jonli kamera tasvirini ko'radi; avtorizatsiyasiz to'g'ridan-to'g'ri havola ishlamaydi

**Plans**: TBD
**UI hint**: yes
**Research flag**: yes — `/gsd-plan-phase 3 --research-phase 3`. Bu NVR modelining ISAPI/Digest xatti-harakati, bir vaqtdagi RTSP sessiya limiti va Karmanadagi haqiqiy CGNAT/WireGuard topologiyasi tadqiqotda LOW confidence deb belgilangan — dalada tekshiriladi.

### Phase 4: Snapshot pipeline

**Goal**: Har kuni rejadagi kadrlar avtomatik olinadi, sifat tekshiruvidan o'tadi, ishonchli arxivlanadi va uzilish jim qolmaydi
**Depends on**: Phase 3; Phase 0 (real kadr bilan capture usuli tanlovi)
**Timeline**: Hafta 5–6 (2026-08-24 → 2026-09-06)
**Requirements**: CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06
**Success Criteria** (what must be TRUE):

  1. Bozor admini snapshot jadvalini o'z bozori uchun sozlaydi (mavsumiy profil bilan, 7 ta qotib qolgan vaqt emas) va ertasi kuni aynan o'sha slotlarda kadrlar paydo bo'ladi
  2. Kadr olish uzilsa yoki takror ishga tushsa — dublikat yozuv yaratilmaydi, urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda ochiq ko'rinadi
  3. Qorong'i / buzuq / bo'sh kadr avtomatik belgilanadi va `light_mode` bilan saqlanadi — bunday kadr hech qachon hisob-kitobga ta'sir qilmaydi
  4. Kadrlar S3-mos omborda bozor/kamera/sana bo'yicha topiladi; 90 kun to'liq, keyin siqilgan saqlash siyosati amalda ishlaydi
  5. Kamera offline bo'lsa, slot o'tkazib yuborilsa yoki backup xato bersa — platforma adminiga Telegram-alert keladi va xato Sentry'da ko'rinadi

**Plans**: TBD
**Research flag**: yes — `/gsd-plan-phase 4 --research-phase 4`. Hal qilinmagan: kadr olish usuli (Hikvision ISAPI still-image / go2rtc frame endpoint / ffmpeg) real NVR'da o'lchanadi; job-orchestration mexanizmi (DB-materialized `capture_runs` + `SKIP LOCKED` vs `arq`) bitta aniq qaror talab qiladi; sifat va `light_mode` chegaralari pilot ma'lumotida sozlanadi.

### Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i

**Goal**: Tizim har rastaning band/bo'shligini kadrdan aniqlaydi va bu javobning aniqligi halol — noaniq navbatidan emas, ko'r namunadan — o'lchanadi
**Depends on**: Phase 4
**Timeline**: Hafta 7–8 (2026-09-07 → 2026-09-20)
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05, AI-06
**Success Criteria** (what must be TRUE):

  1. Bozor admini kamera kadrida rasta zonalarini poligon qilib chizadi va saqlaydi; koordinatalar normalangan (0..1), poligon versiyalangan, bitta rasta bir necha kameraga bog'lanadi
  2. Har kadrda har zona band/bo'sh/noaniq bahosini confidence bilan oladi; AI javobi hech qachon tahrirlanmaydi — nazoratchi qarori alohida yozuv sifatida ustiga qo'yiladi
  3. Nazoratchi kunlik byudjet doirasidagi ustuvorlashtirilgan "noaniq" navbatini ko'rib chiqadi; "hammasini tasdiqlash" tugmasi yo'q va tasdiqlangan javoblar fine-tuning dataseti sifatida yig'iladi
  4. Nazoratchi ko'r audit navbatida AI javobini ko'rmasdan tasodifiy tanlangan zonalarni baholaydi — aniqlik hisoboti faqat shu namunadan chiqadi
  5. Rasta bir necha kamerada ko'rinsa birortasi "band" desa rasta band; kun oxirigacha tasdiqlanmagan "noaniq" esa "bo'sh" bo'ladi va hisobotda alohida belgilanadi

**Plans**: TBD
**UI hint**: yes
**Research flag**: yes — `/gsd-plan-phase 5 --research-phase 5`. Detektor kechikishi/aniqligi Contabo AMD EPYC'da o'lchanmagan (raqamlar Intel/jamoa benchmarklaridan); kichik rastalar uchun tiling/SAHI qarori, ikki chegarali triage qiymatlari va poligon muharriri UX'i "o'lchang, taxmin qilmang" deb belgilangan.
**Note**: Aynan shu faza kesish ro'yxatining birinchi nomzodi — u moliyaviy yadroga (1, 6, 7) tegmasdan qisqartirilishi mumkin qilib ajratilgan.

### Phase 6: Billing va kassir

**Goal**: Band rasta kun oxirida o'zgarmas, dalilga bog'langan pattaga aylanadi va kassir uni telefonda ≤3 bosishda yig'adi
**Depends on**: Phase 5 (bandlik ma'lumoti), Phase 2 (tarif va biriktirish)
**Timeline**: Hafta 9–10 (2026-09-21 → 2026-10-04)
**Requirements**: BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, CASH-01, CASH-02, CASH-03, CASH-04
**Success Criteria** (what must be TRUE):

  1. Kun yopilganda band rastaga (kamida 2 snapshotda band, yoki 1 snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq kunlik patta yoziladi; job qayta ishga tushirilsa ikkinchi hisob paydo bo'lmaydi
  2. Har hisob yozuvidan dalil-kadrlarga o'tish mumkin; hisob yaratilgach o'zgarmaydi — tuzatish faqat sabab ko'rsatilgan `charge_adjustments` yozuvi sifatida ko'rinadi
  3. Qarz faqat biriktirilgan sotuvchida ko'rinadi (qoldiq har doim hisoblanadigan ko'rinish: hisoblar − to'lovlar); biriktirilmagan band rasta hisob emas, "ro'yxatga olinmagan savdo" anomaliyasi sifatida chiqadi
  4. Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi tarif + eski qarz) jonli ko'radi; kassir rastani raqamdan topib, tarifdan kelgan summani ≤3 bosishda tasdiqlaydi va summani faqat sabab-kod bilan o'zgartira oladi
  5. Takror bosilgan to'lov dublikat yaratmaydi, tuzatish faqat storno + qayta kiritish orqali; smena yopilishida kassir tizim summasini ko'rmasdan naqdni deklaratsiya qiladi va farq (variance) direktor hisobotiga chiqadi

**Plans**: TBD
**UI hint**: yes

### Phase 7: Nomuvofiqlik, bildirishnoma va botlar

**Goal**: "Band, lekin to'lovsiz" raqamdan jarayonga aylanadi va har rol o'z xabarini o'z vaqtida oladi
**Depends on**: Phase 6
**Timeline**: Hafta 11 (2026-10-05 → 2026-10-11)
**Requirements**: RECON-01, RECON-02, RECON-03, RECON-06, CASH-05, BOT-01, BOT-02, BOT-03, BOT-04
**Success Criteria** (what must be TRUE):

  1. Kunlik nomuvofiqlik hisoboti "band, lekin to'lovsiz" rastalar va "ro'yxatga olinmagan savdo" anomaliyalarini rasm-dalil havolalari bilan ko'rsatadi
  2. Har nomuvofiqlik case sifatida yuritiladi — mas'ul, holat (yangi/ko'rilmoqda/asosli/asossiz) va yechim yoziladi; hit-rate metrikasi hisoblanadi
  3. Direktor ertalab dayjest (kechagi tushum, bandlik %, TOP-10 qarzdor) va kechqurun nomuvofiqlik xabarini Telegramda oladi; har rol bosh ekranida o'ziga mos bitta asosiy raqamni ko'radi
  4. Sotuvchi contact ulashish orqali botga ulanadi (telefon raqami admin reestriga mos bo'lsa) va o'z qoldig'i/qarzi hamda to'lov tarixini ko'radi
  5. To'lov kiritilishi bilan sotuvchiga zudlik push-kvitansiya boradi (summa, rasta, kassir, vaqt) va qarz N kundan oshsa avtomatik eslatma keladi — barcha xabarlar outbox orqali, throttling va quiet hours hurmat qilinib, yetkazilganlik holati bilan

**Plans**: TBD
**UI hint**: yes

### Phase 8: Hisobotlar, mustahkamlash va ishga tushirish

**Goal**: Direktor raqamlarni o'zi chiqarib oladi, tizim tiklanishi isbotlangan va bozor jonli ishga tushishga tayyor
**Depends on**: Phase 7; Phase 0 (baza varaqalari — solishtirish uchun)
**Timeline**: Hafta 12 (2026-10-12 → 2026-10-18) — yangi funksiya emas, mustahkamlash haftasi
**Requirements**: RECON-04, RECON-05, FOUND-07
**Success Criteria** (what must be TRUE):

  1. Direktor tushum (kunlik/oylik), qarzdorlik reestri va nomuvofiqlik arxivini ko'radi hamda har birini `.xlsx` qilib yuklab oladi
  2. AI aniqlik hisoboti ko'r audit namunasidan chiqadi va xatolik turlarini ajratadi: "band deb xato" (nizo xavfi) va "bo'sh deb xato" (yo'qotish)
  3. Kunlik avtomatik backup (Postgres + obyekt-ombor) boshqa lokatsiyaga ketadi va toza serverda tiklash mashqi kamida bir marta muvaffaqiyatli o'tkazilgan
  4. Go-live runbook tayyor va uch tilli interfeys yakuniy tekshiruvdan o'tgan — kassir, nazoratchi va admin tizimda mashq qilib ko'rgan
  5. Parallel rejim uchun 3 tomonlama solishtiruv vositasi ishlaydi: daftar vs tizim vs AI-kutilgan — kunlik chiqariladi va imzolanadi

**Plans**: TBD
**UI hint**: yes

## Post-Launch: Parallel rejim (hafta 13–16, build'dan tashqari)

Bu build fazasi emas — 8-fazada loyihalanadigan va go-live'dan keyin bajariladigan operatsion tartib:

- Kunlik uchinchi tomon solishtiruvi (nazoratchi yoki admin bajaradi, **kassir emas**)
- Oldindan e'lon qilingan qat'iy cutover sanasi (2–4 hafta, cho'zilmaydi)
- Kiritish kechikishini o'lchash — "xotiradan tiklash" holatini pilot ta'sirining yagona mustaqil o'lchovini buzishidan oldin ushlash

## Requirements Coverage

| Faza | REQ-ID lar | Soni |
|------|-----------|------|
| Phase 0 | — (dala ishi) | 0 |
| Phase 1 | FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05 | 5 |
| Phase 2 | MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06 | 6 |
| Phase 3 | CAM-01, CAM-02, CAM-03 | 3 |
| Phase 4 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | 5 |
| Phase 5 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | 6 |
| Phase 6 | BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, CASH-01, CASH-02, CASH-03, CASH-04 | 9 |
| Phase 7 | RECON-01, RECON-02, RECON-03, RECON-06, CASH-05, BOT-01, BOT-02, BOT-03, BOT-04 | 9 |
| Phase 8 | RECON-04, RECON-05, FOUND-07 | 3 |
| **Jami** | | **46 / 46** |

Yetim (orphan) talab yo'q, dublikat biriktirish yo'q.

## Open Decisions (rejalashtirish paytida hal qilinadi)

| # | Qaror | Qachon |
|---|-------|--------|
| 1 | Kadr olish usuli: Hikvision ISAPI still-image vs go2rtc frame endpoint vs ffmpeg | Phase 4 rejasi (Phase 0 dala testidan keyin) |
| 2 | Job orchestration: DB-materialized `capture_runs` + `SKIP LOCKED` vs `arq` (yoki arq ostida) | Phase 4 rejasi |
| 3 | Obyekt-ombor nomi: MinIO arxivlangan → SeaweedFS (S3 API bir xil) | Phase 4 rejasi; PROJECT.md Key Decisions yangilanadi |
| 4 | Detektor: RF-DETR (Apache-2.0, Nano→Large) — XLarge/2XLarge PML litsenziyasi TAQIQ | Phase 5 rejasi; PROJECT.md Key Decisions yangilanadi |
| 5 | O'zbek huquqiy talablari (kvitansiya maydonlari, CCTV shaxsiy ma'lumot, KKM) — mahalliy yurist ko'rigi | Phase 1–2 bilan parallel, launch'gacha |

## Progress

**Execution Order:**
Phase 0 parallel ishlaydi. Build fazalari raqam tartibida: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (2 va 3 vaqt bo'yicha ustma-ust tushadi).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Dala treki va tashqi bog'liqliklar | N/A | Not started | - |
| 1. Poydevor va tenant xavfsizligi | 0/10 | Planned | - |
| 2. Bozor domeni va ustasi | 0/TBD | Not started | - |
| 3. Kamera va tarmoq ulanishi | 0/TBD | Not started | - |
| 4. Snapshot pipeline | 0/TBD | Not started | - |
| 5. Kamera zonalari, CV va HITL | 0/TBD | Not started | - |
| 6. Billing va kassir | 0/TBD | Not started | - |
| 7. Nomuvofiqlik, bildirishnoma va botlar | 0/TBD | Not started | - |
| 8. Hisobotlar, mustahkamlash va ishga tushirish | 0/TBD | Not started | - |

---
*Roadmap yaratildi: 2026-07-29*
