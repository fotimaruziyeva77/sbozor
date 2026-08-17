# Roadmap: SBOZOR

## Overview

SBOZOR 12 haftada (2026-07-28 → ~2026-10-18) Karmana bozorida jonli ishga tushadi. Yo'l xaritasi bog'liqlik zanjiri bo'yicha qurilgan: avval keyinchalik retrofit qilib bo'lmaydigan poydevor (tenant izolyatsiyasi, audit, biznes-kun, o'zgarmas hisob sxemasi) → bozor domeni (rasta / tarif / sotuvchi) → tashqi ulanish (NVR / WireGuard) → kadr olish → CV aniqlash va nazoratchi tasdig'i → billing va kassir → nomuvofiqlik va botlar → hisobot va ishga tushirish. Bu ketma-ketlik uchta mustaqil tadqiqot yo'nalishida (ARCHITECTURE / PITFALLS / FEATURES) bir xil chiqqan.

Bu zanjir ustidan birinchi haftadanoq **parallel dala treki (Phase 0)** ishlaydi. U raqamlashtirishdan oldingi tushum bazasini o'lchaydi — bu Phase 8 dagi pilot ta'siri hisobotining mustaqil taqqoslash nuqtasi. **Phase 0 hech qanday build fazasini bloklamaydi** (2026-08-01 qarori): u o'lchov va sozlash treki, darvoza emas.

Har faza "band rastadan patta to'liq yig'ilyaptimi?" savolini isbotlash zanjirining bir bo'g'ini. Oxirida direktor "band, lekin to'lovsiz" rastalarni rasm-dalil bilan ko'radi.

## Mahsulot qoidasi: self-service onboarding (MAJBURIY)

**2026-08-01 da o'rnatilgan, barcha fazalarga taalluqli qat'iy qoida.** Har bir faza shu shaklda loyihalanadi va shu shaklda tekshiriladi:

> **Admin saytda faqat kerakli ma'lumotni kiritadi — tizim qolganini o'zi, xatosiz bajaradi.**

Amaliy ma'nosi:

| Onboarding qadami | Admin nima kiritadi | Tizim nima qiladi |
|---|---|---|
| Yangi bozor | Rekvizit + bozor chizmasi (plan-rasm) | Zona/rasta/toifa/tarif tuzilmasini ustadan o'tkazib quradi |
| Kameralar | NVR manzili + login/parol | ISAPI orqali qurilmani aniqlaydi, kanallarni sanaydi, **kameralarni avtomat qo'shadi** — qo'lda kamera kiritish YO'Q |
| Xodimlar | Ma'muriyat bergan odamlar ro'yxati (fayl) | Hisoblarni rollar bilan yaratadi, vaqtinchalik parollarni beradi |
| Rasta/sotuvchi ma'lumoti | Excel fayl | Validatsiya qilib, all-or-nothing yuklaydi |

Buning uchta oqibati bor va ular majburiy:

1. **Muhandis aralashuvi bilan ishlaydigan onboarding qabul qilinmaydi.** Yangi bozor kod yozmasdan, skript ishlatmasdan, SSH'siz ulanadi. Bu mahsulotning asosiy raqobat ustunligi.
2. **Tashqi bog'liqlik hech qachon `Blocks:` bo'lmaydi.** Yetishmayotgan real ma'lumot, kelmagan hujjat yoki ulanmagan uskuna — bularning hech biri fazani yoki jarayonni to'xtatmaydi. Ular keyin to'ldiriladigan ma'lumot sifatida modellashtiriladi.
3. **Tekshiruv simulyator ustida bajariladigan qilib loyihalanadi.** Real uskuna kelguncha to'liq yo'l simulyatsiya qilingan NVR (ISAPI mock + go2rtc RTSP manbasi) ustida ishlab chiqiladi va o'lchanadi. Real qurilmaga o'tish sozlama o'zgarishi bo'ladi, qayta loyihalash emas.

**Muddat:** 12 hafta, zaxirasiz. 12-faza (hafta 12) — yangi funksiya emas, mustahkamlash haftasi. Kesish ro'yxati (cut list) 1-haftada yozma kelishiladi (Phase 0), 11-haftada bosim ostida emas.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 0: Dala treki va o'lchov bazasi** - Tushum bazasi, kamera qamrovi, buyurtmachi javoblari (parallel, **hech narsani bloklamaydi**)
- [x] **Phase 1: Poydevor va tenant xavfsizligi** - Rol, izolyatsiya, audit, biznes-kun, 3 til — retrofit qilinmaydigan qatlam (completed 2026-07-29)
- [x] **Phase 2: Bozor domeni va "Yangi bozor" ustasi** - Rasta, toifa, tarixiy tarif, sotuvchi, ish kunlari, sxematik plan-xarita (24/24 reja bajarildi; 02-VERIFICATION.md ning to'rtala bo'shlig'i 16–20-to'lqinlarda yopildi — qayta tekshiruv kutilyapti) (plans completed 2026-08-03)
- [x] **Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi** - Simulyator, ISAPI kashfiyoti, Fernet rekvizitlari, WireGuard tunnel, jonli ko'rish (14/14 reja bajarildi; sakkizala mezon `tests/integration/test_phase3_criteria.py` bilan bitta buyruqda o'lchanadi. Qayta tekshiruv **5/8** (`gaps_found`) berdi va ikkala bo'shliq ham 03-12/03-13/03-14 bilan YOPILDI: jonli ko'rish yo'li endi rekvizit uzatadi va kadr mock'siz keladi — `tests/integration/test_live_view_e2e.py`. CAM-03 va CAM-09 dalil bilan `Done`; **CAM-02 `Blocked` bo'lib qoldi** — CI'da `wg0` yo'q, egasi Ops, tetigi VPS deploy'i, bandi `03-HUMAN-UAT.md` #1–#2) (plans completed 2026-08-03)
- [x] **Phase 4: Snapshot pipeline** - Mavsumiy jadval, idempotent kadr olish, sifat filtri, S3 arxiv, alertlar (14/14 reja bajarildi; beshala mezon `tests/integration/test_phase4_criteria.py` bilan BITTA buyruqda o'lchanadi va uchala darvozasi — mezon boshiga bitta test, meta-test, mock'siz o'lchov — yashil. CAM-04…CAM-07 va FOUND-06 dalil bilan `Done`; hammasi SIMULYATOR ustida o'lchangan va real uskuna/kalendar/tashqi xizmat talab qiladigan **yettita** band `04-HUMAN-UAT.md` da ega hamda tetik bilan. `npm run gate` chegarasi olti o'lchov asosida 1200 s dan **900 s** ga tushirildi. ⚠ **TEKSHIRUV O'TKAZILDI VA U BO'SHLIQ TOPDI:** `04-VERIFICATION.md` (2026-08-05) fazaga `4/5` ball qo'yib `gaps_found` deb yopdi — yagona bo'shliq SC#5 ning Sentry yarmi edi: `scheduler` konteyneri `SENTRY_DSN` ni olardi va 4-fazaning HAMMA jobini tetiklardi, lekin `init_sentry()` o'sha jarayonda hech qachon chaqirilmasdi. Bo'shliq `04-13` da yopildi (ilmoq + `ObservedScheduler` + `compose.yaml` dan HOSILA qilingan darvoza, uch mustaqil qatlam) va `04-14` uning atrofidagi ochiq bandlarni yopib regressiyasizligini o'lchadi. ⚠ **BELGI HAMON `- [ ]`:** fazani yopish qaroriniki QAYTA TEKSHIRUV (`/gsd-verify-work`), ijrochi emas — bu farq ataylab saqlanadi) (completed 2026-08-05)
- [x] **Phase 5: Kamera zonalari, CV va nazoratchi tasdig'i** - Poligon muharriri, RF-DETR aniqlash, noaniq navbati, ko'r audit (15/15 reja bajarildi; beshala mezon `tests/integration/test_phase5_criteria.py` bilan BITTA buyruqda o'lchanadi va uchala darvozasi - mezon boshiga bitta test, meta-test, soxtalashtirishsiz o'lchov - yashil. AI-01/03/04/05/06 dalil bilan `Done`; **AI-02 `Blocked`** - real ONNX artefakti CI'da yo'q va modelning ANIQLIGI oltin to'plam bo'shligi uchun umuman o'lchanmagan, egasi nazoratchi + Ops, bandlari `05-HUMAN-UAT.md` #1-#3. 4-fazadan meros `gate` bandi (D-26) TINCH XOSTDAGI uch o'lchov bilan yopildi: 1009/1004/983 s, chegara 900 s -> **1250 s**. Ochiq bandlar `05-HUMAN-UAT.md` da ega va tetik bilan. ✅ **QAYTA TEKSHIRUV O'TDI (2026-08-10): 5/5, holat `human_needed`** - `05-VERIFICATION.md`. Tekshiruvchi da'volarni o'qimay testlarni O'ZI yugurtirdi va uchta ogohlantirish topdi; uchalasi ham `05-16` da sabotaj bilan yopildi. IKKITASI HAQIQIY BO'SHLIQ edi: yangi `any`-darvozali marshrutda eski test YASHIL qolardi (W-3), ko'r audit ekraniga qo'yilgan haqiqiy `checkbox` da esa mavjud 40 ta test YASHIL qolardi (W-2). `human_needed` - `05-HUMAN-UAT.md` dagi qo'lda bajariladigan bandlar, kod bo'shlig'i emas) (plans completed 2026-08-10)
 (completed 2026-08-09)

- [x] **Phase 6: Billing va kassir** - O'zgarmas kunlik patta, dalil bog'lash, qarz, ≤3 bosishli kassir, smena hisobi (14/14 reja bajarildi; beshala mezon `tests/integration/test_phase6_criteria.py` bilan BITTA buyruqda o'lchanadi va uchala darvozasi — mezon boshiga bitta test, meta-test, soxtalashtirishsiz o'lchov — yashil. BILL-01…05 va CASH-01…04 dalil bilan `Done` (9/9). `## Manual-Only Verifications` jadvali BO'SH qoldi va bu fazaning NATIJASI: 5-fazadan farqli o'laroq bu yerda haqiqat to'liq mavjud edi (pul aniq, tarif jadvalda, bandlik materializatsiya qilingan), ya'ni «hozir o'lchab bo'lmaydi» bandining o'rni yo'q edi. 5-fazadan meros `gate` byudjeti TINCH XOSTDAGI uch o'lchov bilan qayta belgilandi: 1703/1733/1899 s, chegara 1250 s → **2300 s**; `gate:fast` 160/154/152 s, 180 s → **200 s** — ikkalasi ham o'sish TO'PLAMNING o'sishidan ekani raqam bilan asoslandi (173 backend testi, vitest 620 → 738, uchta yangi SSG marshruti). ⚠ **KOD KO'RIGI BO'SHLIQ TOPDI VA U YOPILDI:** `06-REVIEW.md` (2026-08-11) **5 bloker + 9 ogohlantirish** berdi — hammasi qatlam CHEGARALARIDA, ya'ni fazaning testlari to'xtagan joyda. Eng og'iri D-21 ning buzilishi edi: idempotentlik kvota darvozasidan KEYIN tekshirilardi, ya'ni qarz bilan to'lovni qayta yuborish 200 emas 422 berardi va to'lov ALLAQACHON yozilgan bo'lardi. O'n bir commitda yopildi va har blokerning tuzatilishi SABOTAJ bilan o'lchandi — har safar yangi test qizardi, mavjud testlar YASHIL qoldi (WR-09 ning aynan ko'rligi). ✅ **QAYTA TEKSHIRUV O'TDI (2026-08-11): 5/5, 9/9, holat `human_needed`** — `06-VERIFICATION.md`. Tekshiruvchi da'volarni o'qimay kodni O'ZI o'qidi, beshala tuzatishni mustaqil tasdiqladi va kafolatlarni migratsiya DDL'idan tekshirdi (idempotentlik kaliti — `UNIQUE` cheklov, ilova intizomi EMAS; o'zgarmaslik — shartsiz triggerlar; saqlangan `balance*` ustuni sxemada YO'Q). `human_needed` — `06-HUMAN-UAT.md` dagi to'rt band inson idroki, real qurilma va tashkiliy shart haqida, kod bo'shlig'i EMAS) (plans completed 2026-08-11)
- [x] **Phase 7: Nomuvofiqlik, bildirishnoma va botlar** - "Band, lekin to'lovsiz" case oqimi, sotuvchi va direktor botlari (23/23 reja: 17 asosiy + 6 bo'shliq yopish. **BIRINCHI TEKSHIRUV `2/5` — `gaps_found`** (2026-08-12): #3 NOT MET edi — `market_notification_settings` ga butun repo bo'ylab yozuv yo'li yo'q edi, ya'ni direktor produksiyada dayjest hech qachon olmasdi; `test_sc3` esa yashil turardi, chunki sozlama qatorini fixture orqali to'g'ridan-to'g'ri SQL bilan yozardi. Kod ko'rigi (`07-REVIEW.md`) 9 blocker qayd etdi. **07-18…07-23 shu 3 bo'shliq + 9 blocker + 10 warning'ni yopdi**, orkestrator esa `bot:lint` ni tikladi (`e32e40a`, u butun `gate` zanjirini to'xtatib turardi). **QAYTA TEKSHIRUV `5/5` — barcha mezon VERIFIED** (2026-08-13, `07-VERIFICATION.md`), `npm run gate` to'liq zanjiri **EXIT 0**. Status `human_needed`: 7 band faqat inson tomonidan tekshiriladi (jonli Telegram yetkazish, real `request_contact`, buyurtmachi bilan quiet-hours/overdue_days tasdig'i) — bular **bo'shliq emas, UAT**, `07-HUMAN-UAT.md` da kuzatiladi va `/gsd-progress` da ko'rinadi) (completed 2026-08-13)
- [x] **Phase 8: Hisobotlar, mustahkamlash va ishga tushirish** - Excel eksport, AI aniqlik hisoboti, backup mashqi, go-live (completed 2026-08-16)

## Phase Details

### Phase 0: Dala treki va o'lchov bazasi (PARALLEL TRACK — BLOKLAMAYDI)

**Goal**: Pilot ta'sirini o'lchash uchun raqamlashtirishdan oldingi baza va real dala ma'lumoti yig'iladi — build fazalarining hech biri buni kutmaydi
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
**Blocks**: **HECH NARSANI** (2026-08-01 qarori). Ilgari bu trek Phase 3/4/8 ni bloklardi; endi mahsulotning o'zi o'sha ishni yutadi — NVR avtomatik kashfiyoti (CAM-08) kamera qamrovi auditini keraksiz qiladi, simulyator (CAM-09) real kadrsiz ishlab chiqishga imkon beradi, self-service import esa hujjatlarni kutmaydi. Bu trekning natijalari **sozlash va o'lchov** uchun ishlatiladi:

- Tushum bazasi → Phase 8 dagi pilot ta'siri hisobotining taqqoslash nuqtasi (yagona qaytarilmas band — yig'uvchilar tizim haqida bilishidan oldin o'lchanishi kerak)
- Real kadrlar → Phase 4/5 dagi sifat chegaralari va CV aniqligini sozlash (standart qiymatlar simulyatorda o'rnatiladi, real ma'lumot ularni aniqlashtiradi)
- Buyurtmachining 7 javobi → Phase 6/7 dagi tarif/kvitansiya tafsilotlari (javobsiz — hujjatlashtirilgan standart qiymat ishlatiladi)

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

- [x] 01-04-PLAN.md — Alembic async infra, RLS asboblari (NULLIF), identifikatsiya sxemasi, SECURITY DEFINER login funksiyalari, tenancy meta-test (W3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — audit_log + DB-trigger, 4 qatlamli o'zgarmaslik, moliyaviy konstrayt asboblari (business_date, CHECK, UNIQUE) (W4)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 01-06-PLAN.md — Auth API: login/select-market/refresh/logout/change-password, RBAC matritsasi, tenant sessiyasi, bloklash keshi (W5)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 01-07-PLAN.md — Foydalanuvchi boshqaruvi, profil/til, bozorlar ro'yxati, audit ko'rish API va o'qish-audit dependency (W6)
- [x] 01-08-PLAN.md — Frontend auth qobig'i: login, majburiy parol almashtirish, bozor tanlash, app shell, til almashtirgich (W6)

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 01-09-PLAN.md — Ma'muriy ekranlar: foydalanuvchi boshqaruvi UI va audit jurnali UI + faza mezonlarining uchidan-uchiga tekshiruvi (W7)
- [x] 01-10-PLAN.md — Cross-tenant marshrut matritsasi, marshrut qamrovi darvozasi, CI yig'imi va validatsiya imzosi (W7)

**UI hint**: yes

### Phase 2: Bozor domeni va "Yangi bozor" ustasi

**Goal**: Platforma admini kod yozmasdan yangi bozorni tizimga kiritadi — rasta/tarif/sotuvchi va xodimlar ro'yxati saytning o'zidan, fayl yuklash orqali kiritiladi
**Depends on**: Phase 1
**Timeline**: Hafta 3–4 (2026-08-10 → 2026-08-23)
**Requirements**: MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06, MARKET-07
**Success Criteria** (what must be TRUE):

  1. Platforma admini ustadan o'tib yangi bozor yaratadi (rekvizit → zona → rasta → toifa → tarif) va oxirida bozor ishlashga tayyor holatda ko'rinadi — kod yozilmaydi
  2. Bozor admini rastalar va sotuvchilar reestrini yuritadi: rasta holati (faol/ta'mirda/yopiq), toifasi va sotuvchi biriktirish davri o'zgaradi, har o'zgarish auditda ko'rinadi
  3. Tarif o'zgartirilganda o'tmishdagi sanaga tegishli hisob eski narxda qoladi — yangi narx faqat belgilangan sanadan ta'sir qiladi
  4. Bozor admini bayram/ishlamaydigan kunni belgilaydi va o'sha kunga patta hisoblanmaydi
  5. Bozor admini sxematik plan-xaritada rastalarni zona bo'yicha grid ko'rinishida ko'radi; rasta bosilganda uning kartasi (raqam, toifa, tarif, sotuvchi, holat) ochiladi
  6. Bozor admini ma'muriyat bergan xodimlar ro'yxatini (F.I.Sh., telefon, rol) bitta fayl bilan yuklaydi; tizim hisoblarni rollar bilan yaratadi va vaqtinchalik parollarni beradi — qo'lda birma-bir kiritish shart emas

**Plans**: 24 plans in 20 waves (18–24 — bo‘shliqlarni yopish va self-service to‘lqini)
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Wave-0 backend darvozalari: reyestrlar, RBAC, `btree_gist`, WR-02/WR-03 (W1)
- [x] 02-02-PLAN.md — Wave-0 frontend: WCAG token tuzatishlari, 7 `ui/` primitivi, transliteratsiya darvozasi (W1)

**Wave 2** *(blocked on Wave 1)*

- [x] 02-03-PLAN.md — `MarketRef.is_active` zanjiri (6 band) va qoralama bozorning ko'rinishi (W2)

**Wave 3–5** *(sxema, ketma-ket migratsiya zanjiri)*

- [x] 02-04-PLAN.md — 10 domen modeli, `[)` davr yordamchisi, 5 DB funksiyasi, 3 trigger (W3)
- [x] 02-05-PLAN.md — `0007_market_domain` + `0008_temporal` + Alembic ko'rmaydigan darvozalar (W4)
- [x] 02-06-PLAN.md — `0009_vendors` (EXCLUDE) + `0010_calendar` + ikki bozorli domen seed'i (W5)

**Wave 6**

- [x] 02-07-PLAN.md — Domen darvozalari: SC#2/SC#3/SC#4 va D-09…D-12 ning DB isboti (W6)

**Wave 7–11** *(API, ketma-ket — `schemas.py`/`main.py`/marshrut matritsasi umumiy)*

- [x] 02-08-PLAN.md — API I: barcha domen DTO'lari + zona/toifa/rasta + xarita agregati (W7)
- [x] 02-09-PLAN.md — API II: tariflar (faqat qo'shadigan) va ish kunlari (W8)
- [x] 02-10-PLAN.md — API III: sotuvchilar (o'qish auditi) va biriktirish davrlari (W9)
- [x] 02-11-PLAN.md — API IV: usta — bozor yaratish, `setup-status`, faollashtirish (W10)
- [x] 02-12-PLAN.md — Excel import: xavfsiz o'qish, validatsiya, shablon, all-or-nothing (W11)

**Wave 12–14** *(frontend)*

- [x] 02-13-PLAN.md — Frontend domen kontrakti: zod, TanStack Query, 9 namespace, navigatsiya (W12)
- [x] 02-14-PLAN.md — Rasta reestri va sxematik plan-xarita (CSS Grid, react-konva EMAS) (W13)
- [x] 02-15-PLAN.md — Sotuvchi, tarif, kalendar, zona va toifa ekranlari (W13)
- [x] 02-16-PLAN.md — Usta UI (7 qadam, faollashtirish paneli) va Excel import paneli (W14)

**Wave 15**

- [x] 02-17-PLAN.md — Karmananing real ma'lumoti, faza mezonlari testi va darvoza (W15)

**Wave 16** *(bo‘shliqlarni yopish — 02-VERIFICATION.md)*

- [x] 02-18-PLAN.md — Ustaga yo‘l ochish: marshrut istisnosi, navigatsiya yozuvi, bo‘sh holat havolasi (+WR-09) (W16)
- [x] 02-19-PLAN.md — Shaxsiy ma’lumot o‘qishining auditi va MARKET_DATA_VIEW/VENDOR_VIEW chegarasi (W16)
- [x] 02-20-PLAN.md — Klient keshining tenant chegarasi: market_id bilan doiralangan kalitlar va tozalash (+WR-10) (W16)

**Wave 17**

- [x] 02-21-PLAN.md — Ish kunlari tanlovi majburiy (WR-06) va qolgan ko‘rik topilmalarining triaji (W17)

**Wave 18**

- [x] 02-22-PLAN.md — Yakuniy regressiya va REQUIREMENTS.md traceability yakunlanishi (W18)

**Wave 19**

- [x] 02-24-PLAN.md — MARKET-07: xodimlar ro‘yxatining ommaviy importi, rollar va vaqtinchalik parollar (W19)

**Wave 20**

- [x] 02-23-PLAN.md — Import qobiliyatining Karmana miqyosidagi isboti, operatsion runbook va validatsiya imzosi (W20)

**UI hint**: yes
**Note**: Ustaning kamera / kamera-zona / snapshot-jadval qadamlari 3–5 fazalarda ulanadi. Plan-xarita **sxematik** (grid) bo'lib qoladi — to'liq interaktiv xarita v2. Ranglar to'liq to'plami (ko'k to'langan, qizil qarzdor, sariq nomuvofiq) va dalil-rasm 6–7 fazalarda yonadi.

**Real ma'lumot haqida (2026-08-01 da qayta ta'riflandi).** Ilgari bu faza "Karmananing real ma'lumoti aynan shu fazada kiritiladi" deb yozilgan va bu fazani ma'muriyatdan hujjat kelishiga bog'lab qo'ygan edi. Self-service qoidasi bo'yicha **fazaning yetkazib berish mahsuloti — import qobiliyati, ma'lum bir fayl emas**: yo'l (shablon → validatsiya → all-or-nothing yuklash → D-15 takroriy import himoyasi) qurilgan, hujjatlashtirilgan va o'lchangan bo'lsa, faza yopiladi. Real Karmana ma'lumoti kelganda admin uni saytning o'zidan yuklaydi — bu operatsion amal, faza darvozasi emas. Keyingi fazalar realistik hajmdagi (~300–1000 rasta) seed ma'lumot ustida sinaladi va real ma'lumot kelganda ustiga qo'yiladi.

### Phase 3: NVR avtomatik kashfiyoti va tarmoq ulanishi

**Goal**: Admin saytga NVR manzili va login/parolini kiritadi — tizim Hikvision qurilmasini o'zi aniqlaydi, kanallarni sanab chiqadi va kameralarni avtomat qo'shadi; direktor jonli tasvirni panelda ko'radi
**Depends on**: Phase 1 *(Phase 0 bog'liqligi 2026-08-01 da olib tashlandi — self-service qoidasi)*
**Timeline**: Hafta 3–4 (2026-08-10 → 2026-08-23) — Phase 2 bilan parallel
**Requirements**: CAM-01, CAM-02, CAM-03, CAM-08, CAM-09
**Success Criteria** (what must be TRUE):

  1. Bozor admini **faqat** NVR manzili + login/parolni kiritadi va "kameralarni topish" tugmasini bosadi; tizim ISAPI orqali qurilma modelini aniqlaydi, barcha kanallarni sanaydi va har biri uchun kamera yozuvini (nom, kanal raqami, asosiy/sub oqim URL'i) **avtomat** yaratadi — qo'lda birorta RTSP URL yozilmaydi
  2. Qayta skanerlash idempotent: yangi kanal qo'shiladi, yo'qolgani `offline` deb belgilanadi, mavjudi tegilmaydi — takroriy kamera yozuvi yaratilmaydi
  3. Ulanish muvaffaqiyatsiz bo'lsa, xato **sababi va tuzatish yo'li** ko'rsatiladi (parol xato / NVR soati >5 daq farq qilyapti → NTP / firmware `digest/basic` talab qiladi / kanal offline / bir vaqtdagi sessiya limitiga yetildi) — "ulanmadi" degan quruq xabar qabul qilinmaydi
  4. RTSP login/parollari bazada Fernet bilan shifrlangan saqlanadi — bazaga kirgan odam ham ochiq matn parol ko'rmaydi; parol hech qachon API javobida yoki jurnalda ko'rinmaydi
  5. Server NVR'ga faqat WireGuard tunnel orqali kiradi; tunnel o'chirilsa ulanish uziladi va NVR internetdan to'g'ridan-to'g'ri ochiq emas
  6. Direktor avtorizatsiyadan keyin panelda jonli kamera tasvirini ko'radi; avtorizatsiyasiz to'g'ridan-to'g'ri havola ishlamaydi
  7. **Butun yuqoridagi oqim real uskunasiz, simulyatsiya qilingan Hikvision NVR ustida uchidan-uchiga ishlaydi va CI'da o'lchanadi** — real qurilmaga o'tish sozlama o'zgarishi bo'ladi, kod o'zgarishi emas
  8. **WR-02 (2-fazadan eskalatsiya, YUQORI ustuvorlik):** `market_delete_draft()` o'n ikki jadval bo'ylab kaskad o'chiradi va uning yagona chegarasi ilova qatlamida — DB darajasida hech narsa uni to'xtatmaydi. Bu fazada u migratsiya bilan DB darajasida cheklanadi (qoralama bo'lmagan bozorni o'chirish imkonsiz bo'lishi test bilan isbotlanadi). 2-fazada tuzatilmadi, chunki `0011` bilan bir oynaga tiqish downgrade'ni ishonchsiz qilardi

**Plans**: 14 plans in 12 waves (11 ta asosiy + 3 ta bo'shliq yopish, `03-VERIFICATION.md` 5/8)
Plans:
**Wave 1** *(Wave 0 darvozalari — birinchi migratsiyadan OLDIN, yolg'iz)*

- [x] 03-01-PLAN.md — `03-PATTERNS.md` §5 ning yetti bandi: httpx prod'ga, `CAMERA_MANAGE`, markerlar, kaskad darvozasi, tez teskari aloqa yo'li (W1)

**Wave 2** *(parallel — fayllar kesishmaydi)*

- [x] 03-02-PLAN.md — Hikvision NVR simulyatori: RFC 7616 server tomoni, real dump fixture'lari, `--profile sim`, sizib ketmaslik darvozasi (W2)
- [x] 03-03-PLAN.md — To'rt tenant jadvali, `0012_nvr_domain`, `0013_market_delete_guard` (WR-02) va NVR domenining meta-invariantlari (W2)

**Wave 3–6** *(backend zanjiri — ketma-ket)*

- [x] 03-04-PLAN.md — Fernet sirlari va rotatsiya, RTSP URL fabrikasi, xususiy-tarmoq validatsiyasi, idempotent upsert (W3)
- [x] 03-05-PLAN.md — ISAPI klienti: xato taksonomiyasi, namespace-agnostik parser, Digest, teskari retry siyosati, kashfiyot orkestratsiyasi (W4)
- [x] 03-06-PLAN.md — taskiq navbati, kashfiyot jobi (tenant konteksti) va NVR API: test-connection, 202 + poll (W5)
- [x] 03-07-PLAN.md — Kamera API, jonli ko'rish tokeni va `auth_request`, go2rtc allow-listi, nginx bloklari, WireGuard split-tunnel (W6)

**Wave 7–9** *(frontend)*

- [x] 03-08-PLAN.md — Frontend kontrakti: navigatsiya, ~95 kalit uch tilda, zod/query qatlami, G-1…G-7 darvozalari, vendored pleyer (W7)
- [x] 03-09-PLAN.md — `/cameras` sahifasi, NVR formasi va kartasi, xato bloki (sabab + tuzatish), auth qulfi (W8)
- [x] 03-10-PLAN.md — Kashfiyot paneli va uch hisoblagich, kameralar ro'yxati, arxivlash, jonli ko'rish dialogi (W9)

**Wave 10**

- [x] 03-11-PLAN.md — Sakkizala mezonning yagona darvozasi, bloklanmaydigan `hardware` to'plami, runbook va validatsiya imzosi (W10)

**Bo'shliq yopish** *(`03-VERIFICATION.md` GAP-1/GAP-2 — SC#6 ning ikkinchi yarmi ulanmagan edi)*

*Bo'shliq to'lqini 1 (parallel — fayllar kesishmaydi)*

- [x] 03-12-PLAN.md — Sim NVR o'z manzilida RTSP xizmat qiladi (autentifikatsiya majburiy), o'lik `SIM_*` konfiguratsiyasi olib tashlanadi, darvoza zanjiridagi 31 % qayta bajarish yo'q qilinadi (BW1)
- [x] 03-13-PLAN.md — go2rtc'ga RTSP rekvizitini yetkazish: `decrypt_nvr_password` ning ikkinchi chaqiruv joyi, `SecretStr` tashuvchisi va uchta oqish yo'lining yopilishi (BW1)

*Bo'shliq to'lqini 2*

- [x] 03-14-PLAN.md — Mock'siz uchidan-uchiga jonli ko'rish o'lchovi (kadr keladi), meta-darvoza, talab holatlari va `03-HUMAN-UAT.md` (BW2)

**UI hint**: yes
**Research flag**: yes — `/gsd-plan-phase 3 --research-phase 3`. Tadqiqot **simulyator-birinchi** yondashuvda o'tkaziladi: Hikvision ISAPI kashfiyot endpointlari (`/ISAPI/System/deviceInfo`, `/ISAPI/ContentMgmt/InputProxy/channels`, `/ISAPI/System/Video/inputs/channels`), kanal raqamlash qoidasi (`{ch}01` asosiy / `{ch}02` sub), Digest autentifikatsiyasining soat farqiga sezgirligi, firmware'ning `digest/basic` talabi, NVR'ning bir vaqtdagi masofaviy sessiya limiti (odatda 6–16) va CGNAT ostidagi WireGuard topologiyasi. Bularning har biri simulyatorda modellashtiriladi, real qurilmada esa tasdiqlanadi.
**Note**: CGNAT holati mahsulot muammosi emas — bozor tomonida oldindan sozlangan WireGuard qurilmasi (mini-PC yoki OpenWrt router) `PersistentKeepalive` bilan o'zi uyga qo'ng'iroq qiladi. Admin uni faqat rozetkaga ulaydi.

### Phase 4: Snapshot pipeline

**Goal**: Har kuni rejadagi kadrlar avtomatik olinadi, sifat tekshiruvidan o'tadi, ishonchli arxivlanadi va uzilish jim qolmaydi
**Depends on**: Phase 3 *(Phase 0 bog'liqligi 2026-08-01 da olib tashlandi — self-service qoidasi)*
**Timeline**: Hafta 5–6 (2026-08-24 → 2026-09-06)
**Requirements**: CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06
**Success Criteria** (what must be TRUE):

  1. Bozor admini snapshot jadvalini o'z bozori uchun sozlaydi (mavsumiy profil bilan, 7 ta qotib qolgan vaqt emas) va ertasi kuni aynan o'sha slotlarda kadrlar paydo bo'ladi
  2. Kadr olish uzilsa yoki takror ishga tushsa — dublikat yozuv yaratilmaydi, urinish qayta bajariladi, o'tkazib yuborilgan slot jurnalda ochiq ko'rinadi
  3. Qorong'i / buzuq / bo'sh kadr avtomatik belgilanadi va `light_mode` bilan saqlanadi — bunday kadr hech qachon hisob-kitobga ta'sir qilmaydi
  4. Kadrlar S3-mos omborda bozor/kamera/sana bo'yicha topiladi; 90 kun to'liq, keyin siqilgan saqlash siyosati amalda ishlaydi
  5. Kamera offline bo'lsa, slot o'tkazib yuborilsa yoki backup xato bersa — platforma adminiga Telegram-alert keladi va xato Sentry'da ko'rinadi

**Plans**: 14 plans (9 to'lqin — `04-13`/`04-14` bo'shliq yopish to'lqini)

- [x] `04-01-PLAN.md` — Wave 0/A: prod bog'liqliklari, `scheduler` va `storage` konteynerlari, reyestrlar, D-23 o'lchovi
- [x] `04-02-PLAN.md` — Wave 0/B: sintetik JPEG generatori, sim `frame_mode` + `/picture`, frontend darvozalari (W0-F1…F7)
- [x] `04-03-PLAN.md` — Sxema: beshta model, `0014_snapshot_domain`, `0015` kaskadi, `capture_due_markets()`, meta-invariantlar
- [x] `04-04-PLAN.md` — Sof xizmatlar: `Settings`, sifat filtri (`Pillow`), obyekt kaliti, xato taksonomiyasi
- [x] `04-05-PLAN.md` — Repozitoriylar: `capture_repo` (`SKIP LOCKED` + lease), `schedule_repo`, `snapshot_repo`
- [x] `04-06-PLAN.md` — Ombor: `aiobotocore` qobig'i va haqiqiy SeaweedFS ustidagi kalit tartibi
- [x] `04-07-PLAN.md` — Kadr olish oqimi: `frame_source`, ISAPI `/picture`, `capture_tick`/`capture_batch`, planer
- [x] `04-08-PLAN.md` — Saqlash siyosati va alertlar: `retention.daily`, Telegram jo'natuvchisi, `alert_sweep`, `ops/docs/monitoring.md`
- [x] `04-09-PLAN.md` — API: jadval CRUD, ijro jurnali, kadr rasmi proxysi (`audit_read`), `/internal/self-check`
- [x] `04-10-PLAN.md` — Frontend A: so'rov qatlami, `/snapshots` sahifasi, jadval kartasi va dialoglar
- [x] `04-11-PLAN.md` — Frontend B: kun xulosasi, ijro matritsasi (9 holat), kadr detali, ogohlantirishlar
- [x] `04-12-PLAN.md` — Faza darvozasi: `test_phase4_criteria.py`, chegara qarori, talab holatlari

**Bo'shliq yopish to'lqini** *(`04-VERIFICATION.md` — `4/5`, SC#5 qisman)*

- [x] `04-13-PLAN.md` — `scheduler` jarayonida Sentry (`CLIENT_STARTUP`), planerning yutilgan `on_ready` istisnosi va `compose.yaml` dan HOSILA qilingan jarayon darvozasi (W1)
- [x] `04-14-PLAN.md` — `.env.example` ↔ `s3.json.example` juftligi (`deferred-items.md` #2), FOUND-06 dalilining hujjatlardagi aksi, to'liq darvoza va bazaviy jadval (W2)

**Research flag**: yes — `/gsd-plan-phase 4 --research-phase 4`. **Kadr olish usuli endi kutilmaydi — standart tanlov: go2rtc `/api/frame.jpeg`, zaxira: Hikvision ISAPI `/picture`, oxirgi chora: ffmpeg** (tadqiqot tavsiyasi, CLAUDE.md da qat'iylashtirilgan). Uchala yo'l ham sozlanadigan qilib quriladi va simulyatorda o'lchanadi; real NVR ma'lumoti kelganda tanlov **sozlama** bilan o'zgaradi, qayta loyihalash talab qilmaydi.

**Faza yopilgandagi holat (2026-08-05, `04-12`).** Rejalashtirish paytida ochiq qolgan uch band yopildi va ularning har biri o'zgargan holda YOZILDI, jimgina qoldirilmadi:

| Ochiq band | Holat | Nima o'zgardi |
|---|---|---|
| Kadr olish usuli | **Yopiq** (2026-08-01) | Uchala yo'l qurildi va `nvr_devices.capture_method` bilan tanlanadi. Real qurilmaga o'tish — MA'LUMOT o'zgarishi (`test_snapshot_quality.py` uni aynan shu yo'l bilan o'lchaydi) |
| Job orchestration | **Yopiq** (2026-08-04; quyidagi ochiq qarorlar jadvalining 2-bandi) | Ikkalasi ham kerak edi: `taskiq scheduler` holatsiz 1-daqiqalik tik beradi, reja/ijara/idempotentlik/yo'qlik yozuvi Postgres `capture_runs` da (`SKIP LOCKED` + lease) |
| Sifat va `light_mode` chegaralari | **Ochiq, LEKIN EGA VA TETIK BILAN** | Simulyatorda standart qiymat oldi va MEXANIZM o'lchandi; QIYMAT real Karmana kadri bilan sozlanadi — `04-HUMAN-UAT.md` #1, egasi nazoratchi + ijrochi, tetigi Phase 0 kadrlari. D-15 bo'yicha o'lchovlar qatorda saqlanadi, ya'ni sozlash SQL bilan bo'ladi |

⚠ **3-fazadan meros qolgan `gate` bandi ham shu fazada yopildi:** chegara **olti o'lchov** asosida qayta belgilandi (`04-VALIDATION.md`) va 1200 s dan **900 s** ga TUSHIRILDI. `gate:fast` 180 s da qoldi.

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

**Plans**: 15 plans (9 to'lqin)

- [x] 05-01-PLAN.md — Wave 0/A: reyestrlar, ko'r audit urug'ining zondi, markerlar, oltin to'plam skeleti
- [x] 05-02-PLAN.md — Wave 0/B: `cv-service` bog'liqlik to'plami, litsenziya devori, `sv.Detections` fixture'i
- [x] 05-03-PLAN.md — Wave 0/C: zona geometriyasi, Wilson oralig'i, ko'r-payload darvozasi
- [x] 05-04-PLAN.md — Wave 0/D: xato reyestrlari, navigatsiya, matn darvozalari, D-27
- [x] 05-05-PLAN.md — `0018` bandlik domeni + `0019` kaskad (billing langari, o'zgarmaslik)
- [x] 05-06-PLAN.md — `camera_zones` API: server geometriyasi, versiyalash, qamrov (AI-01)
- [x] 05-07-PLAN.md — `cv-service` detektor yadrosi: ONNX, post-processing, zona verdicti (AI-02)
- [x] 05-08-PLAN.md — `detect` job: ombor klienti, orkestratsiya, `occupancy_events` (AI-02)
- [x] 05-09-PLAN.md — Frontend Y-1: zona muharriri (AI-01)
- [x] 05-10-PLAN.md — Noaniq navbat: byudjet, ustuvorlik, ommaviy endpointning yo'qligi (AI-03)
- [x] 05-11-PLAN.md — Ko'r audit: namuna tortish, ko'r serializer, olti invariant (AI-04)
- [x] 05-12-PLAN.md — Agregatsiya, kun yopilishi va aniqlik hisoboti (AI-05, AI-06, AI-04)
- [x] 05-13-PLAN.md — Frontend Y-2/Y-3: navbat va ko'r audit sessiyalari (AI-03, AI-04)
- [x] 05-14-PLAN.md — Frontend Y-4: bandlik va aniqlik hisoboti (AI-04, AI-05, AI-06)
- [x] 05-15-PLAN.md — Faza darvozasi, `gate` byudjeti (W0-13) va yakunlash

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

**Plans**: 14 plans (10 to'lqin)
**Wave 1**

- [x] 06-01-PLAN.md — Wave 0/A: A1 (parallel get-or-create) va A2 (generated-from-column) zondlari, sof funksiyalar (D-04/D-05/C-6, D-26) + D-24 ning taqsimlash qoidasi (`FIFO_OLDEST_SERVICE_DATE_FIRST`, G-13/G-14)
- [x] 06-02-PLAN.md — Wave 0/B: ikki huquq, yetti domen enumi, 14 xato kodi, butun matn va ikki yangi darvoza (OP-6/7/12, §5.10)
- [x] 06-03-PLAN.md — Wave 0/C: to'rt so'rov moduli (ikki ALOHIDA) va `collect-surface` darvozasi (W0-F3/F4, G-7/G-22/G-28d)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06-04-PLAN.md — `0020` billing domeni + `0021` kaskad; uch o'zgarmaslik qo'riqchisi, orfan DEFINER DROP (C-1/2/4/5/7/11/12)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06-05-PLAN.md — Seed (`day_close` orqali), sxema meta testi va o'zgarmaslikning xulqiy darvozasi (D-07/23/25/27)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 06-06-PLAN.md — `billing_repo`: yagona pul yechimi, D-04 predikati, muzlatilgan dalil, qoldiq (BILL-01…05, C-6/7/8)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 06-07-PLAN.md — `billing_close` job, cron `day_close` dan KEYIN, yurak urishining ko'rinishi (C-3, D-12…15, M-C)
- [x] 06-08-PLAN.md — `GET /billing/*`: maydonni e'lon qilmaslik va yangi 422 darvozasi (D-17/20, C-9/10)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 06-09-PLAN.md — `POST /payments` + storno: ikki bayonotli idempotentlik, fingerprint, CASH-02 auditi, yopiq kunda qarz undirish va `stall_not_assigned` (D-21/22/23/28, §9.4)

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 06-10-PLAN.md — Smena API: ko'r serializator va ikki tomonlama variance (CASH-04, D-25/26/27)

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 06-11-PLAN.md — Frontend Y-1: ≤3 bosish sanog'i, ikki qatlamli qulf, DL-1/DL-2 (D-18/19/21/22, OP-5)

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 06-12-PLAN.md — Frontend Y-3: ko'r naqd deklaratsiyasi va yo'qlikning o'lchovi (D-25, G-7/G-23b)
- [x] 06-13-PLAN.md — Frontend Y-4: hisoblar, dalil, anomaliya va variance (BILL-02/03/04, G-25/26/27/28)

**Wave 10** *(blocked on Wave 9 completion)*

- [x] 06-14-PLAN.md — Faza darvozasi, beshta sabotaj, `gate` byudjeti va yakunlash

⚠ **FAZA BELGISI (`- [ ] **Phase 6: …**`, 51-qator) ATAYIN O'ZGARTIRILMADI.**
Fazani yopish qarori ⛔ **qayta tekshiruvniki** (`/gsd-verify-work`), ijrochi
emas — 4- va 5-fazalarda AYNAN shunday saqlangan. 14 rejaning hammasi
bajarildi va beshala mezon bitta buyruqda yashil
(`tests/integration/test_phase6_criteria.py`), lekin «bajarildi» bilan
«tasdiqlandi» ikki BOSHQA da'vo va ularni bitta belgiga siqish
2-fazaning o'zini o'zi tasdiqlovchi shablonini qaytarardi.

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

**Plans**: 23 plans (8 to'lqin + 4 to'lqin bo'shliqni yopish)

Plans:
**Wave 1**

- [x] 07-01-PLAN.md — `bot-service` tug'ilishi: skelet, compose, `package.json`, Sentry darvozasining kengaytmasi
- [x] 07-02-PLAN.md — Bildirishnoma domeni: besh enum, besh model, `0023` migratsiya (RLS + kompozit FK + XOR CHECK)
- [x] 07-03-PLAN.md — `GET /me/headline` — rol bo'yicha serverda hal qilinadigan bitta son (RECON-06)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 07-04-PLAN.md — Strukturaviy meta darvoza (G7-2/G7-7/G7-8) + domen fixture'lari (ikki bozorli telefon to'qnashuvi)
- [x] 07-05-PLAN.md — Frontend: bosh ekran ko'rsatkichi

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 07-06-PLAN.md — `AlertSender` kengaytmasi (`chat_id` argument) + `outbox_repo` + D-18 siyosati
- [x] 07-07-PLAN.md — Case domeni: `reconciliation_repo` + `recon.open` jobi + hosila hit-rate
- [x] 07-08-PLAN.md — Ichki bot API + `binding_repo` (D-26 ning uch shoxi)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 07-09-PLAN.md — `notify.outbox_tick` jobi + G7-1/G7-4/G7-5
- [x] 07-10-PLAN.md — Nomuvofiqlik hisoboti va case yuzasi (API) + G7-6
- [x] 07-11-PLAN.md — `bot-service` handlerlari, uchala locale katalogi + G7-9
- [x] 07-12-PLAN.md — CASH-05: kvitansiya niyati to'lov tranzaksiyasida
- [x] 07-13-PLAN.md — Kechki/ertalabki xabar (D-15/D-16) va kechikkan qarz eslatmasi (BOT-03)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 07-14-PLAN.md — Cron reyestri va yurak urishi (D-17): besh vazifa, to'rt komponent

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 07-15-PLAN.md — Frontend: nomuvofiqlik hisoboti + case ro'yxati + G7-3

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 07-16-PLAN.md — Frontend: case detali + yetkazilganlik holati (BOT-04)

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 07-17-PLAN.md — Faza darvozasi: `test_phase7_criteria.py`, byudjet o'lchovi, talab holatlari

#### Bo'shliqni yopish (`07-VERIFICATION.md` — `gaps_found`, 2/5 mezon)

> ⚠ To'lqin raqamlari `--gaps-only` ijrosining O'Z zanjiriga tegishli — yuqoridagi
> sakkiz to'lqinning davomi EMAS. Har reja `gap_closure: true` bilan belgilangan.

**Gap Wave 1** — Mezon #3 (NOT MET) va navbat konvergentligi

- [x] 07-18-PLAN.md — Direktor bog'lanishi: `director_chat_id` ning yagona yozuv yo'li (B-1)
- [x] 07-19-PLAN.md — Outbox: urinish byudjeti, tik deadline va UNRESOLVED terminal chegara (B-3/B-4)

**Gap Wave 2** *(blocked on Gap Wave 1)*

- [x] 07-20-PLAN.md — Case mas'uli serverga yetadi + `user_market_roles` tekshiruvi (B-2, WR-01/WR-05)
- [x] 07-21-PLAN.md — Kuzatuv, matn rostgo'yligi va dev muhiti (WR-10/WR-02/WR-03, B-8/B-9)

**Gap Wave 3** *(blocked on Gap Wave 2)*

- [x] 07-22-PLAN.md — Frontend: to'rt ro'yxat yuzasi — sahifalash, a11y, arifmetika (B-6, WR-06/WR-08)

**Gap Wave 4** *(blocked on Gap Wave 3)*

- [x] 07-23-PLAN.md — Frontend: hukm dialogi yiqilganda buni AYTADI (B-5/B-7, WR-09/WR-16)

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

**Plans**: 20 plans in 7 waves
Plans:
**Wave 1** *(parallel — fayl to'plamlari kesishmaydi)*

- [x] 08-01-PLAN.md — Wave 0/A: bayt-determinik `xlsx_export`, `freeze_zip` mahsulotga, hisobot chegaralari (W1)
- [x] 08-02-PLAN.md — Wave 0/B: `0024_ledger_entries` + `0025_notification_settings_id`, reyestrlar, audit zondi (W1)
- [x] 08-03-PLAN.md — Wave 0/C: frontend kontrakti — reyestrlar, `report-queries`, uch locale, `report-copy` darvozasi (W1)
- [x] 08-04-PLAN.md — `report_repo`: tushum · qarzdorlik · nomuvofiqlik arxivining hosila so'rovlari (W1)
- [x] 08-05-PLAN.md — `backup` konteyneri: quvursiz zaxira, idempotent tsikl, yurak urishi, statik darvoza (W1)
- [x] 08-06-PLAN.md — Mustahkamlash A: backend WR-04/06/09 (W1)

**Wave 2** *(blocked on Wave 1)*

- [x] 08-07-PLAN.md — Hisobot API (JSON): huquq, bitta `audit_read`, davr chegaralari (W2)
- [x] 08-08-PLAN.md — Zaxira yurak urishi va tiklash mashqining CI qatlami (W2)
- [x] 08-09-PLAN.md — Frontend boshqaruvlari: davr tanlagichi (maks KECHA) va eksport tugmasi (W2)
- [x] 08-10-PLAN.md — Mustahkamlash B: frontend WR/IN + 07 №1-qo'shimcha + 07 №2 (ism bo'shlig'i) (W2)
- [x] 08-11-PLAN.md — Mustahkamlash C: bot WR-02/03/04 + IN-01/07 + WR-14 (W2)

**Wave 3** *(blocked on Wave 2)*

- [x] 08-12-PLAN.md — `.xlsx` eksport marshrutlari va bayt-tasnif darvozasining KENGAYTIRILISHI (W3)
- [x] 08-13-PLAN.md — Frontend Y-1a: tushum va qarzdorlik ko'rinishlari (G-39) (W3)

**Wave 4** *(blocked on Wave 3)*

- [x] 08-14-PLAN.md — Daftar importi: to'rtinchi shablon turi, validator, all-or-nothing marshrut (W4)
- [x] 08-15-PLAN.md — Frontend Y-1b: nomuvofiqlik arxivi va aniqlik bloki (G-40 a/b) (W4)

**Wave 5** *(blocked on Wave 4)*

- [x] 08-16-PLAN.md — Uch tomonlama solishtiruv: hosila so'rov, marshrutlar, imzoli eksport (W5)
- [x] 08-17-PLAN.md — Frontend: `/reports` sahifasi, blok darvozasi (G-37), navigatsiya, manba skani (W5)

**Wave 6** *(blocked on Wave 5)*

- [x] 08-18-PLAN.md — Frontend Y-3: solishtiruv sahifasi, daftar importi, uch farq sinfi (W6)
- [x] 08-19-PLAN.md — Go-live runbook, `08-HUMAN-UAT.md` va runbook shakli darvozasi (W6)

**Wave 7** *(blocked on Wave 6)*

- [x] 08-20-PLAN.md — Faza darvozasi: `test_phase8_criteria.py`, `gate` byudjeti, talab holatlari (W7)

**UI hint**: yes
**Note**: Faza belgisi (`- [ ] **Phase 8: ...**`) ijro tugagach ham
O'ZGARTIRILMAYDI — fazani yopish qarori ⛔ **qayta tekshiruvniki**
(`/gsd-verify-work`), ijrochi emas. 4–7-fazalarda aynan shunday saqlangan.

## Post-Launch: Parallel rejim (hafta 13–16, build'dan tashqari)

Bu build fazasi emas — 8-fazada loyihalanadigan va go-live'dan keyin bajariladigan operatsion tartib:

- Kunlik uchinchi tomon solishtiruvi (nazoratchi yoki admin bajaradi, **kassir emas**)
- Oldindan e'lon qilingan qat'iy cutover sanasi (2–4 hafta, cho'zilmaydi)
- Kiritish kechikishini o'lchash — "xotiradan tiklash" holatini pilot ta'sirining yagona mustaqil o'lchovini buzishidan oldin ushlash

## Requirements Coverage

| Faza | REQ-ID lar | Soni |
|------|-----------|------|
| Phase 0 | — (dala ishi, bloklamaydi) | 0 |
| Phase 1 | FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05 | 5 |
| Phase 2 | MARKET-01, MARKET-02, MARKET-03, MARKET-04, MARKET-05, MARKET-06, MARKET-07 | 7 |
| Phase 3 | CAM-01, CAM-02, CAM-03, CAM-08, CAM-09 | 5 |
| Phase 4 | CAM-04, CAM-05, CAM-06, CAM-07, FOUND-06 | 5 |
| Phase 5 | AI-01, AI-02, AI-03, AI-04, AI-05, AI-06 | 6 |
| Phase 6 | BILL-01, BILL-02, BILL-03, BILL-04, BILL-05, CASH-01, CASH-02, CASH-03, CASH-04 | 9 |
| Phase 7 | RECON-01, RECON-02, RECON-03, RECON-06, CASH-05, BOT-01, BOT-02, BOT-03, BOT-04 | 9 |
| Phase 8 | RECON-04, RECON-05, FOUND-07 | 3 |
| **Jami** | | **49 / 49** |

*2026-08-01 da qo'shildi (self-service qoidasi): MARKET-07 (xodimlar ro'yxatini ommaviy import), CAM-08 (NVR avtomatik kashfiyoti), CAM-09 (NVR simulyatori va test rejimi).*

Yetim (orphan) talab yo'q, dublikat biriktirish yo'q.

## Open Decisions (rejalashtirish paytida hal qilinadi)

| # | Qaror | Qachon |
|---|-------|--------|
| 1 | ~~Kadr olish usuli~~ — **HAL QILINDI 2026-08-01**: standart `go2rtc /api/frame.jpeg`, zaxira ISAPI `/picture`, oxirgi chora ffmpeg. Uchalasi ham sozlanadigan qilib quriladi; real NVR ma'lumoti tanlovni **sozlama** bilan o'zgartiradi | — (dala testini kutmaydi) |
| 2 | ~~Job orchestration~~ — **HAL QILINDI 2026-08-04**: bu yolg'on dilemma edi, ikkalasi ham kerak. `taskiq scheduler` faqat **holatsiz 1-daqiqalik tik** beradi; reja, ijara (lease), idempotentlik va **yo'qlik yozuvi** Postgres `capture_runs` da yashaydi (`SKIP LOCKED`). Sabab o'lchangan: taskiq'ning cron «oxirgi ijro» holati oddiy xotiradagi `dict`, taqsimlangan qulf yo'q — ya'ni slot-boshiga cron o'tkazib yuborilgan slotni **izsiz** yo'qotadi va bu CAM-05 ning o'z talabiga zid. `RedisScheduleSource` esa umuman yaroqsiz: loyihaning Valkey'i `--save "" --appendonly no` bilan ishlaydi, ya'ni kesh qayta ishga tushganda hamma bozorning jadvali jimgina yo'q bo'lardi. **Resolved 2026-08-05 (`04-12`)**: amalga oshirildi va o'lchandi — `taskiq scheduler` holatsiz tik + Postgres `capture_runs` + `SKIP LOCKED` + lease (D-02); `test_capture_tick.py`, `test_capture_repo.py` va `test_sc2_...` | ✅ Phase 4 da bajarildi |
| 3 | ~~Obyekt-ombor nomi~~ — **Resolved 2026-08-05 (`04-12`)**: SeaweedFS 4.40 `storage` xizmati sifatida ishlaydi (profilsiz), kalit tartibi `bozor/sana/kamera/slot`, kirish faqat `aiobotocore` orqali. `test_storage_layout.py` va `test_sc4_...` HAQIQIY konteynerga yozadi — mock yo'q | ✅ Phase 4 da bajarildi |
| 4 | Detektor: RF-DETR (Apache-2.0, Nano→Large) — XLarge/2XLarge PML litsenziyasi TAQIQ | Phase 5 rejasi; PROJECT.md Key Decisions yangilanadi |
| 5 | O'zbek huquqiy talablari (kvitansiya maydonlari, CCTV shaxsiy ma'lumot, KKM) — mahalliy yurist ko'rigi | Phase 1–2 bilan parallel, launch'gacha |

## Progress

**Execution Order:**
Phase 0 parallel ishlaydi. Build fazalari raqam tartibida: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (2 va 3 vaqt bo'yicha ustma-ust tushadi).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Dala treki va tashqi bog'liqliklar | N/A | Not started | - |
| 1. Poydevor va tenant xavfsizligi | 0/10 | Planned | - |
| 2. Bozor domeni va ustasi | 0/17 | Planned | - |
| 3. NVR avtomatik kashfiyoti va tarmoq ulanishi | 11/11 | Complete | 2026-08-03 |
| 4. Snapshot pipeline | 14/14 | Tekshirildi (human_needed — 5/5 mezon, 7 HUMAN-UAT bandi ochiq) | 2026-08-16 |
| 5. Kamera zonalari, CV va nazoratchi tasdig'i | 15/15 | Tekshirildi (human_needed — 4/5 to'liq, SC2 ONNX'ga bog'liq) | 2026-08-16 |
| 6. Billing va kassir | 14/14 | Complete   | 2026-08-11 |
| 7. Nomuvofiqlik, bildirishnoma va botlar | 23/23 | Complete   | 2026-08-13 |
| 8. Hisobotlar, mustahkamlash va ishga tushirish | 20/20 | Complete    | 2026-08-16 |

### Phase 9: UI-polish — motion qatlami

**Goal:** Foydalanuvchi ilovada Apple-darajadagi jilo his qiladi: to'lov muvaffaqiyati Apple Pay xoreografiyasi bilan yakunlanadi, direktor paneli skeleton→count-up bilan jonlanadi, iliq fon (rang 2.0) va dark rejim token-almashtirish orqali ishlaydi, barcha harakat `prefers-reduced-motion`ni hurmat qiladi
**Requirements**: ⛔ **Yangi REQ-ID YARATILMAYDI** (09-RESEARCH A7) — `.planning/REQUIREMENTS.md` ning ro'yxati ham, Traceability jadvali ham **TEGILMAYDI**. Bu faza mavjud talablarning **sifat qatlamini** yopadi va uning o'lchov birligi — quyidagi **SC#1…SC#5**. Rejalarning frontmatter'ida ular `SC-1`…`SC-5` deb yuritiladi. Sifat qatlamining meros egalari: **CASH-01** (SC#1 — kassir oqimining takrorlanuvchanligi), **RECON-06** (SC#2 — bosh ekran ko'rsatkichi), **FOUND-04** (SC#3 — uchala tildagi yangi copy). Sabab: `UX-01` kabi yangi ID ochish to'qqizta fazaning traceability tarixiga retroaktiv savol qo'shardi.
**Depends on:** Phase 8
**Success Criteria** (what must be TRUE):

  1. Kassir to'lovni tasdiqlaganda 6-qadam xoreografiya (bosish masshtabi → check-draw → halqa pulsi → summa uchishi → qator qo'nishi → qidiruv tozalanadi va avtofokus) ishlaydi va input ~150ms ichida keyingi mijozga tayyor — bayram bloklamaydi
  2. Direktor paneli skeleton (shimmer, spinner YO'Q) bilan ochiladi, kartalar stagger bilan kiradi, tushum count-up bilan sanaydi, sparkline/donut chizilib chiqadi
  3. Iliq fon (rang 2.0) va dark rejim token-almashtirish bilan ishlaydi — komponent kodi o'zgarmaydi; kassir "quyosh rejimi" tugmasi kontrast maksimal qiladi
  4. `prefers-reduced-motion` da barcha harakat o'chadi (G-motion-1 darvozasi), kassir interaktiv javoblari ≤150ms (G-motion-2 darvozasi) — ikkalasi testda o'lchanadi
  5. Motion faqat `transform`/`opacity` bilan (60fps arzon Androidda), `motion` kutubxonasi +35KB gzip byudjetida, mavjud G-* darvozalar yashil qoladi

⚠ **SC#1 qavsining tuzatilishi (2026-08-17, rejalashtirish):** qavsda ilgari `count-up` yozilgan edi. 09-UI-SPEC §0.2 uni **rad etdi va sabab mexanik**: kassir yuzasidagi har qanday sanaydigan yig'indi 6-fazaning **ko'r deklaratsiya** darvozasini buzadi (`collect-surface.test.mjs`, `MIN_BLIND_DECLARATION_TOKENS = 7`) — kassir o'z smenasining tizim summasini deklaratsiyadan OLDIN bilsa, nomuvofiqlik topish mexanizmi jimgina qadrsizlanadi. Qavs endi UI-SPEC §8.1 ning HAQIQIY olti qadamiga mos. Count-up **direktor** yuzasida qoladi (SC#2) va u yerda hech qanday ko'rlik chegarasi yo'q.

**Chegaralar:** redesign EMAS — mavjud dizayn-tizim ustiga; konfetti FAQAT kunlik plan bajarilganda; masterplan §7 mikro-UX tuzatishlaridan 8-fazada yopilmagani shu fazaga kiradi

⚠ **Chegaralarning rejalashtirishdagi holati (2026-08-17):**

1. **Konfetti** — 09-UI-SPEC §9 da shartnoma sifatida **to'liq yozilgan, LEKIN bu fazada QURILMAYDI**.
   Sabab mexanik: tetikning haqiqat manbai (`daily_plan`/`target`) kodbazada UMUMAN yo'q va
   `paymentResponseSchema` — `z.strictObject`, ya'ni `market_day_cleared` maydoni **ikki tomonlama,
   kelishilgan** o'zgarish (backend fazasining ishi). Klientdagi har qanday hosila esa ko'r deklaratsiya
   darvozasini buzadi. Band `deferred-items.md` da sabab va kelajakdagi ijro yo'li bilan yozilgan.

2. **Masterplan §7 mikro-UX** — 09-UI-SPEC §13 oltala bandning holatini O'LCHADI: uchtasi allaqachon
   YOPILGAN (sana utili, pul utili, bozor konteksti), ikkitasi ataylab KENGAYTIRILMAYDI (nisbiy vaqt,
   2-ustunli grid — §10.1 ikki karta bilan qisman), bittasi qamrovdan tashqarida (copy auditi).
   ⛔ Ya'ni 9-fazaga tushadigan **yangi mikro-UX bandi YO'Q** — bu topilma va u bo'sh to'lqin ochilishining
   oldini oladi.

**Plans:** 7/7 plans complete

Plans:

**Wave 1** *(langar — uchala CSS darvozasi bitta faylni o'qiydi)*

- [x] 09-01-PLAN.md — SPEC nomuvofiqliklarini rostlash, kontrast kalkulyatori (G-motion-5) va `globals.css` ning to'liq token/motion/tema qatlami (W1)

**Wave 2** *(parallel — fayl to'plamlari kesishmaydi)*

- [x] 09-02-PLAN.md — `ui/` primitivlari jilosi, beshala `Loader2` ning reduced-motion juftligi va G-motion-1/G-motion-3 (W2)
- [x] 09-03-PLAN.md — Tema qatlami: `lib/theme.ts`, FOUC'siz `<head>` skripti, `ThemeToggle`, 11 copy kaliti va G-motion-4 (W2)

**Wave 3** *(parallel — Y-1 va Y-2 mustaqil)*

- [x] 09-04-PLAN.md — Y-1 kassir vau-oqimi: 1–5-qadam, bloklamaydigan ulanish va G-motion-2 (W3)
- [x] 09-05-PLAN.md — Y-2 direktor jonlanishi: count-up, sparkline, donut va G-motion-6 ning ikki qatlamli huquq darvozasi (W3)

**Wave 4**

- [x] 09-06-PLAN.md — Qolgan jilo (til almashtirgich, jadval hover) va G-motion-7 (CLS + Display-XL) (W4)

**Wave 5**

- [x] 09-07-PLAN.md — Faza darvozasi: `phase9-criteria.test.mjs`, byudjet qayta o'lchovi va HUMAN-UAT (W5)

**UI hint**: yes
**Note**: Faza belgisi (`- [x] **Phase 9: ...**`) ijro tugagach ham O'ZGARTIRILMAYDI — fazani yopish (completed 2026-08-17)
qarori ⛔ **qayta tekshiruvniki** (`/gsd-verify-work`), ijrochi emas. 4–8-fazalarda aynan shunday saqlangan.

### Phase 10: Landing — sbozor.uz

**Goal:** Anonim tashrif buyuruvchi sbozor.uz'da 30 soniyada mahsulotni tushunadi va demo so'raydi: hero 12s "jonli bozor" sikli, 3-qadam "qanday ishlaydi" seksiyasi, davlat-ishonch bloki, demo-forma → admin Telegram-bot
**Requirements**: TBD (plan bosqichida — manba: `LANDING-BRIEF.md`, `sketch-findings-bozor` landing-sehri reference)
**Depends on:** Phase 9
**Success Criteria** (what must be TRUE):

  1. `sbozor.uz/` (anonim root) landing ko'rsatadi, uchala tilda SSG; «Kirish» app loginiga olib boradi
  2. Hero 12s "jonli bozor" siklini o'ynaydi (sketch 003-B: xarita → kamera nuri → amber «Band, lekin to'lovsiz» → to'lov → hisobot); video EMAS, `prefers-reduced-motion`da statik final-kadr
  3. Demo-forma yuborilganda so'rov admin Telegram-botga yetadi (mavjud bot-service orqali) — alohida CRM yo'q
  4. Ishonch bloki: ma'lumotlar O'zbekistonda · NVR faqat VPN · har amal auditda · 3 til; pilot holati halol («Karmana sinovda», yolg'on raqam YO'Q)
  5. Lighthouse ≥95, LCP <1.5s (statik sahifada), SEO meta/OG/structured data to'liq

**Chegaralar:** mavjud Next.js ichida `(marketing)` route-guruhi — alohida sayt EMAS; copy brief matnidan (yakuniy tahrir shu fazada, 3 tilda); maxfiylik siyosati sahifasi majburiy (CCTV shaxsiy ma'lumot)
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 10 to break down)

---
*Roadmap yaratildi: 2026-07-29*
