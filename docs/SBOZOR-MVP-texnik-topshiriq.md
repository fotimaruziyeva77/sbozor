# SBOZOR — MVP texnik topshiriq

**Versiya:** 1.1 · **Sana:** 2026-07-28 (v1.0: 2026-07-24)
**Pilot:** Karmana tumani bozori (Navoiy viloyati), ~300–1000 rasta
**Jamoa:** loyiha rahbari (arxitektura + AI/CV) · backend dasturchi (Python/FastAPI) · frontend dasturchi (Next.js)
**Boshlanish:** 2026-07-28 · **Jonli ishga tushirish maqsadi:** ~2026-10-18

---

## 1. Mahsulot maqsadi

SBOZOR — bozorlarni raqamlashtiruvchi universal platforma. MVP bitta savolga raqamlar bilan javob beradi: **"har bir band rastadan patta to'liq yig'ilyaptimi?"**

Ish tamoyili: bozordagi mavjud NVR kameralaridan kuniga 7 marta (ertalab 06:00–08:00 oralig'ida har 30 daqiqada: 06:00, 06:30, 07:00, 07:30, 08:00; kechqurun 16:00 va 18:00) rastalar surati olinadi → AI bo'sh/band rastani aniqlaydi → band rastaga mahsulot toifasi tarifiga ko'ra kunlik patta hisoblanadi → kassir to'lovni qayd etadi (naqd/terminal) → tizim AI ma'lumoti bilan to'lovlarni solishtirib **nomuvofiqlikni** ko'rsatadi.

Platforma universal: yangi bozor kod yozmasdan, faqat "Yangi bozor" ustasi (wizard) orqali ulanadi.

## 2. MVP qamrovi

**Kiradi:** rasta moduli (kunlik patta), kassir to'lov qaydi, AI snapshot-tahlil, Telegram-bot (sotuvchi + direktor), nomuvofiqlik hisoboti, kunlik dayjest, rasm-dalil arxivi, audit jurnali, 3 til, Excel eksport, jonli kamera ko'rish.

**Kirmaydi (keyingi bosqichlar):** do'kon ijarasi (yillik shartnoma), avtoturargoh (ANPR), hojatxona, onlayn to'lov (Payme/Click merchant), xaridor super-ilovasi, rasta broni, SMS kanal, heatmap, kassir offline rejimi, soliq/OFD va E-bozor integratsiyasi.

## 3. Rollar

| Rol | Kirish | Vazifasi |
|---|---|---|
| Platforma admini (siz) | Admin panel | Bozorlarni yaratish, tizim sozlamalari |
| Bozor direktori | Admin panel + bot | Hisobotlar, dayjest, nizolarni ko'rish |
| Bozor admini | Admin panel | Rastalar, tariflar, sotuvchilar reestri |
| Kassir | Panelning yengil mobil rejimi | Rastani tanlab to'lov kiritish (naqd/terminal) |
| Nazoratchi | Panel (cheklangan) | AI natijalarini tasdiqlash/tuzatish (human-in-the-loop). Karmanada — bozorning mavjud nazoratchilari |
| Sotuvchi | Telegram-bot | Qoldiq, qarz, to'lov tarixi, eslatmalar |

Har bir harakat audit jurnaliga yoziladi (kim, qachon, nima, eski→yangi qiymat).

## 4. Modullar

### 4.1. "Yangi bozor" ustasi (universallik yadrosi)
Qadamlar: bozor rekvizitlari → plan-rasm yuklash → rastalarni belgilash → mahsulot toifalari va tariflar → kameralarni ulash (RTSP/NVR manzil) → har kamera kadrida rasta zonalarini chizish → snapshot jadvalini sozlash (standart: 06:00–08:00 har 30 daqiqa + 16:00, 18:00; o'zgartiriladigan) → ishga tushirish.

Rasta belgilash ikki qatlamda ishlaydi:
- **Plan-xarita:** yuklangan bozor rasmida rastalar interaktiv belgilanadi (ko'rish/navigatsiya uchun).
- **Kamera zonalari:** har kameraning statik kadrida rasta chegaralari poligon qilib chiziladi — AI aynan shu zonalarni tahlil qiladi. Bitta rasta bir yoki bir necha kameraga bog'lanishi mumkin; bir necha kamera bo'lsa **agregatsiya qoidasi: birortasi "band" desa — band**.

### 4.2. Rasta va tarif moduli
Rasta: raqam, zona/qator, mahsulot toifasi, holat (faol/ta'mirda/yopiq), biriktirilgan sotuvchi (ixtiyoriy). Tarif: mahsulot toifasi → kunlik patta narxi; narxlar tarixiy saqlanadi (qaysi kundan qaysi narx). Toifalar ro'yxati har bozor uchun alohida sozlanadi.

### 4.3. Billing (kunlik hisob)

**Asosiy qoida:** kun davomidagi snapshotlarning birortasida rasta "band" bo'lsa — o'sha kunga toifa tarifi bo'yicha **to'liq kunlik patta** hisoblanadi (yarim tarif yo'q; bozorga chiqqan sotuvchidan to'liq patta olinadi). Hisob yozuvi dalil-snapshotlarga bog'lanadi.

**Vaqt oqimi:** kassir kun davomida ishlaydi, yakuniy hisob esa kun oxirida chiqadi. Shuning uchun:
- Kun davomida kassirga **"kutilayotgan patta = bugungi tarif + eski qarz"** ko'rinadi (birinchi "band" snapshot paytidayoq).
- Kun oxirida tizim yakuniy hisobni chiqarib, to'lovlar bilan solishtiradi (rekonsiliatsiya) — nomuvofiqlik hisoboti shundan tug'iladi.

**Qarzdorlik:** to'lovlar hisobdan ayiriladi, qoldiq qarz sifatida yuritiladi — **faqat biriktirilgan sotuvchi bor rastalarda** (qarz sotuvchiga yoziladi). Biriktirilmagan rasta "band" ko'rinsa — hisob yozilmaydi (to'lovchi yo'q), buning o'rniga u **"ro'yxatga olinmagan savdo"** anomaliyasi sifatida nomuvofiqlik hisobotiga tushadi (chora: sotuvchini ro'yxatga olish yoki joyida undirish).

**`noaniq` natija:** kun oxirigacha nazoratchi tasdiqlamasa, standart holat — **"bo'sh"** (kam hisoblash xavfsizroq, ortiqcha hisoblash nizo keltiradi); bunday kunlar hisobotda alohida belgi bilan ko'rinadi.

**Tuzatish:** chiqarilgan hisobni faqat sabab ko'rsatib bekor qilish/o'zgartirish mumkin (`charge_adjustments`), hammasi auditda.

### 4.4. Kassir moduli
Telefon brauzerida ochiladigan sodda interfeys: rasta qidirish (raqam bo'yicha) → bugungi hisob/qarz ko'rinadi → **summa tarifdan avtomatik olinadi** (qo'lda o'zgartirish faqat sabab-kod bilan, auditda belgilanadi — erkin summa korrupsiya teshigi) → to'lov turi (naqd / terminal) → tasdiqlash. Chek raqami ixtiyoriy maydon. Har to'lov kassir nomi bilan jurnalga tushadi.

### 4.5. CV xizmati (snapshot pipeline)
1. Rejalashtirilgan vaqtda har kameradan kadr olinadi (RTSP → ffmpeg, bitta kadr; muvaffaqiyatsiz bo'lsa 2 marta retry).
2. Kadr MinIO'ga saqlanadi (bozor/kamera/sana bo'yicha).
3. Detektor kadrni tahlil qiladi: har belgilangan zonada odam va/yoki mahsulot bor-yo'qligi → `band / bo'sh / noaniq`.
4. `noaniq` natijalar nazoratchi navbatiga tushadi (human-in-the-loop); tasdiqlangan javoblar keyinchalik fine-tuning dataseti bo'ladi.
5. Natijalar `occupancy_events` jadvaliga yoziladi.

**Model litsenziyasi:** faqat ruxsati erkin (Apache-2.0/MIT) modellar ishlatiladi — RT-DETR / D-FINE / YOLOX oilasi. **Ultralytics YOLO (AGPL-3.0) ishlatilmaydi** (tijoriy SaaS uchun pullik litsenziya talab qiladi).

Boshlanish: tayyor model (person + umumiy obyekt detektsiyasi) + zona qoidalari. 1–2 oy real Karmana ma'lumotida fine-tuning (o'qitish uchun vaqtincha ijaraga GPU; inference CPU'da — kuniga bir necha ming kadr bir necha daqiqada tahlil qilinadi).

### 4.6. Telegram-bot
**Sotuvchi:** telefon raqam orqali ro'yxatdan o'tish (admin biriktiradi) → qoldiq/qarz → to'lov tarixi → eslatmalar (qarz N kundan oshsa avtomatik).
**Direktor:** ertalabki dayjest (kechagi tushum, bandlik %, qarzdorlar TOP-10) va kechki **nomuvofiqlik hisoboti** ("band, lekin to'lovsiz" rastalar + "ro'yxatga olinmagan savdo" anomaliyalari, rasm havolalari bilan).

### 4.7. Hisobotlar va eksport
Davr bo'yicha: tushum (kunlik/oylik), bandlik dinamikasi, qarzdorlik reestri, kassir kesimida to'lovlar, nomuvofiqliklar arxivi, **AI aniqlik hisoboti** (AI bashorati vs nazoratchi qarori — 9-bo'limdagi ≥90% mezonini o'lchash uchun). Hammasi Excel (.xlsx) ko'rinishida yuklab olinadi.

## 5. Arxitektura

**Servislar (3 ta, ortiqcha bo'linmaydi):**
- `core-api` — FastAPI: auth, bozor/rasta/tarif, billing, to'lov, hisobot, audit.
- `cv-service` — FastAPI + scheduler: snapshot olish, detektor tahlili, occupancy events.
- `bot-service` — aiogram: sotuvchi va direktor botlari.

**Saqlash:** PostgreSQL (asosiy baza, multi-tenant: hamma jadvalda `market_id`) · Redis (navbat/kesh) · MinIO (S3-mos, rasm arxivi).

**Infra:** hammasi Docker Compose'da, Contabo VPS (boshlanishiga 8–16 GB RAM, 4–6 vCPU, 400+ GB disk yetadi). Nginx + HTTPS (Let's Encrypt). Kunlik avtomatik backup (baza dump + MinIO sync, boshqa lokatsiyaga; tiklash mashqi kamida bir marta o'tkaziladi).

> **Data-rezidentlik eslatmasi:** sotuvchilarning shaxsiy ma'lumotlari (F.I.Sh., telefon) O'zR "Shaxsga doir ma'lumotlar to'g'risida"gi qonuni (lokalizatsiya talabi) ostiga tushadi. Pilot Contabo'da (qaror 2026-07-28), lekin davlat bosqichiga chiqishdan oldin O'zbekistondagi hostingga ko'chish rejalashtiriladi — compose arxitektura ko'chishni arzon qiladi (compose'ni ko'tarish + ma'lumot migratsiyasi).

**Kamera ulanishi:** Karmana NVR — Hikvision (~20–25 kamera); ma'muriyat login/parol beradi, internet barqaror. Serverdan NVR'ga kirish VPN (WireGuard) orqali — NVR hech qachon to'g'ridan-to'g'ri internetga ochilmaydi; RTSP parollari bazada shifrlangan saqlanadi. Jonli ko'rish uchun panelda RTSP→WebRTC/HLS proksi (go2rtc).

**Tizim monitoringi:** kamera offline / snapshot o'tkazib yuborildi / backup bajarilmadi / disk to'lyapti — platforma adminiga Telegram-alert; xatolar Sentry'ga; oddiy healthcheck'lar.

**Rasm arxivi siyosati:** to'liq o'lchamli kadr 90 kun, keyin siqilgan nusxa 1 yil (sozlanadigan). Bozorda "video kuzatuv olib borilmoqda" belgisi va ma'muriyat bilan ma'lumotlardan foydalanish kelishuvi bo'ladi.

## 6. Ma'lumotlar modeli (asosiy jadvallar)

`markets` · `users` (rollar bilan) · `zones` · `stalls` (rasta) · `product_categories` · `tariffs` (tarixiy) · `vendors` (sotuvchilar) · `stall_assignments` · `cameras` · `camera_zones` (poligonlar) · `snapshots` · `occupancy_events` · `daily_charges` (kunlik hisob, snapshot havolalari bilan) · `charge_adjustments` (tuzatishlar, sabab bilan) · `payments` (kassir, tur: cash/terminal) · `debts` (hisoblanadigan ko'rinish) · `audit_log` · `notifications`.

Barchasida `market_id` — bitta kod bazasi, cheksiz bozor. Pul — `BIGINT` so'm; vaqt — UTC'da saqlanadi, Asia/Tashkent'da ko'rsatiladi.

## 7. UI/dizayn tamoyillari (Apple-uslub)

- Minimal, keng oq bo'shliqli, tinch rangli interfeys: oq/och kulrang fon, bitta aksent rang, yumshoq burchakli kartalar, yengil soyalar.
- Tipografika: Inter/SF-uslub, aniq ierarxiya; jadval emas — kartalar va toza ro'yxatlar.
- Har ekranda **bitta asosiy harakat**; kassir oqimi 3 bosishdan oshmaydi.
- Bozor xaritasi — markaziy element: rastalar rangli (yashil bo'sh, ko'k to'langan, qizil qarzdor, sariq nomuvofiq), bosilganda karta ochiladi (rasm-dalil bilan).
- 3 til: o'zbek-lotin (asosiy), o'zbek-kirill, rus; til almashtirish bir bosishda. **i18n skaffoldingi 1-haftadan** (keyin qo'shish og'riqli).
- Frontend: Next.js + Tailwind; dizayn-tizim komponentlari bir marta yaratilib hamma modulda ishlatiladi.

## 8. 0–3 oylik reja

| Hafta | Sanalar | Natija |
|---|---|---|
| 1–2 | 28.07 – 09.08 | Loyiha skeleti (repo, Docker, CI), ma'lumotlar modeli, auth/rollar; dizayn-tizim asoslari. **Parallel:** NVR login/parol olish, VPN ulanishini sinash, kamera qamrov auditi |
| 3–4 | 10.08 – 23.08 | Bozor ustasi (wizard): plan yuklash, rasta belgilash, tariflar; Karmana ma'lumotlari kiritiladi |
| 5–6 | 24.08 – 06.09 | Kamera ulanishi: NVR'dan snapshot olish jonli ishlaydi, MinIO arxiv, jonli ko'rish (go2rtc) |
| 7–8 | 07.09 – 20.09 | CV v1: zona tahlili, occupancy events, nazoratchi tasdiqlash oqimi |
| 9–10 | 21.09 – 04.10 | Billing + kassir moduli + qarzdorlik; audit jurnali |
| 11 | 05.10 – 11.10 | Telegram-bot: sotuvchi qismi + direktor dayjesti + nomuvofiqlik hisoboti |
| 12 | 12.10 – 18.10 | Hisobotlar, Excel eksport, 3 til sayqali; **Karmanada jonli ishga tushirish** |

Ishga tushirilgach 2–4 hafta parallel rejim: kassir eski usulda ham yozadi, tizim bilan solishtiriladi — ishonch va AI aniqligi shu davrda isbotlanadi. **Baza o'lchovi:** joriy (raqamlashtirishdan oldingi) kunlik tushumni birinchi 2 haftada kim va qanday formatda yozishi ma'muriyat bilan kelishiladi — "tushum o'sdi" argumenti shu bazaga tayanadi.

## 9. MVP muvaffaqiyat mezonlari (Karmana)

- AI bandlik aniqligi ≥ 90% (nazoratchi tasdiqlariga nisbatan), 2-oyda ≥ 95% — panel ichidagi aniqlik hisoboti bilan o'lchanadi.
- Kunlik nomuvofiqlik hisoboti barqaror chiqadi; "band-to'lovsiz" ulushi pasayib boradi.
- Rasmiylashtirilgan kunlik tushum joriy etishdan oldingi darajadan o'sadi (bazani birinchi 2 haftada o'lchaymiz).
- Sotuvchilarning ≥ 60% botga ulanadi (3-oy oxiriga).
- Yangi bozorni kiritish (wizard orqali) ≤ 3 ish kuni.

## 10. Xavflar (MVP darajasida)

| Xavf | Chora |
|---|---|
| Erta tong (06:00) kadrlarida yorug'lik yetishmasligi (ayniqsa kuz/qish) | Kameralarning IR rejimini tekshirish; kerak bo'lsa qorong'i snapshotni tahlildan chiqarib, faqat arxiv uchun saqlash |
| Kamera qamrovi ayrim rastalarni ko'rmasligi (~10%) | Onboarding'da qamrov auditi; ko'rinmaydigan rastalar "qo'lda rejim"da yuritiladi |
| NVR'ga masofaviy ulanish beqarorligi | VPN + qayta urinish logikasi; o'tkazib yuborilgan snapshot jurnalda ko'rinadi + admin'ga alert |
| Sotuvchi/kassir qarshiligi | Parallel rejim, sodda UX, direktor tomonidan qo'llab-quvvatlash |
| Internet uzilishi | Snapshot navbati NVR yozuvidan keyin olib olish imkoni; kassir offline rejimi 2-bosqichda |
| Wizard'dagi poligon/plan muharriri hajmi (eng og'ir frontend qism) | 3–4-haftada birinchi navbatda kamera-zona muharriri (funksional qatlam); plan-xarita sxematik versiyada boshlanishi mumkin |

## 11. Qarorlar jurnali

**2026-07-28** (buyurtmachi javoblari asosida):
1. Karmana: ~20–25 kamera, Hikvision NVR; login/parolni bozor ma'muriyati beradi; internet barqaror, stream uchun ham yetarli.
2. Kameralar rastalarning ~90% ini qamraydi; qolgani qo'lda rejimda.
3. Nazoratchi roli — bozorning mavjud nazoratchilari.
4. Snapshot jadvali: ertalab 06:00–08:00 har 30 daqiqada + kechqurun 16:00, 18:00 (04:00 olib tashlandi). Bozorga chiqqan sotuvchidan to'liq patta — yarim tarif yo'q.
5. Biriktirilmagan rasta = savdo yo'q, hech kim to'lamaydi; band ko'rinsa — "ro'yxatga olinmagan savdo" anomaliyasi.
6. Jonli kamera ko'rish MVP'da qoladi (snapshot-tahlil bilan birga).
7. Hosting hozircha Contabo; lokalizatsiya bo'yicha ko'chish keyinroq (5-bo'limdagi eslatma).
8. CV model: faqat bepul/erkin litsenziya (Apache-2.0) — Ultralytics AGPL ishlatilmaydi.
9. "SBOZOR" nomi yakuniy.
10. 12 haftalik reja 2026-07-28 dan hisoblanadi.
