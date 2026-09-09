# SBOZOR — Avtonom UI test hisoboti

**Sana:** 2026-08-14 · **Testchi:** Claude (brauzer-avtomatlash) · **Muhit:** lokal Docker stek, NVR simulyatori
**Qamrov:** chek-listning 0–8 bo'limlari (CV xulosalari, botlar va kanvas-chizish bundan mustasno — pastda sabablari)

---

## Xulosa

Tizim asosiy oqimlarda **mustahkam ishlaydi**: bozor yaratish ustasi 7/7 qadam, kassir sikli (smena → 3 bosishda to'lov → ko'r deklaratsiya), NVR avtokashfiyoti, jonli tasvir, uch til, audit jurnali va RLS izolyatsiyasi (731 avtomatik test) — hammasi o'tdi. **Bitta jiddiy muammo** topildi: sahifa almashishda sessiya to'satdan o'chib ketishi (№7). Qolganlari — o'rta va mayda UX/format nuqsonlari.

---

## ✗ Topilmalar (jiddiylik bo'yicha)

### №7 — JIDDIY: sessiya to'satdan o'chadi (auth/refresh 401) — ✅ TUZATILDI (commit `9cf8a66`)

> **Yechim (2026-08-14):** ildiz sabab rotatsiya poygasi EMAS — `change-password` joriy qurilmaga yangi sessiya bermasdi. Fix: bekor qilishdan keyin `_issue_session_cookie`. Jonli tasdiqlangan, 579/579 test yashil. RBAC ko'zgu nomuvofiqligi ham YO'Q deb tasdiqlandi (direktor↔billing huquqi ikkala tomonda bor).

Ikki marta, ikki xil rolda kuzatildi:
- Kassir `/uz/users` ga o'tganda (qo'lda URL) — login sahifasiga uloqtirildi, sessiya yo'q.
- **Direktor o'z navigatsiyasidagi "Patta hisobi" havolasini bosganda** — xuddi shunday.

Dalil: sahifa yuklanishida `POST /api/v1/auth/refresh → 401 Unauthorized`, so'ng login'ga redirect. Audit jurnalida "Eski sessiya kaliti qayta ishlatildi" hodisa turi mavjud — ehtimoliy mexanizm: **refresh-token rotatsiyasi poygasi** (parallel yuklanishlarda eski token qayta ishlatiladi → reuse-detection butun sessiya oilasini o'chiradi). Sekin/parallel so'rovli real qurilmalarda tez-tez uchraydi.

*Qo'shimcha:* agar direktorga `/uz/billing` ko'rsatilishi noto'g'ri bo'lsa — bu `rbac.ts` (nav) va `rbac.py` (API) ko'zgu nomuvofiqligi; agar to'g'ri bo'lsa — faqat refresh poygasi. Ikkalasini ham tekshirish kerak.

### №6 — MUHIM: "Jadvalni tahrirlash" birinchi jadvalda abadiy "Yuklanmoqda" — ✅ TUZATILDI (commit `c411636`)

Kadr olish sahifasida jadval hali yo'q holatda "Jadvalni tahrirlash" dialogi API'dan `{"items":[]}` (200 OK) olsa ham loading holatidan chiqmaydi. Birinchi jadvalni faqat "Mavsumiy jadval qo'shish" orqali yaratish mumkin (chetlab o'tish ishladi).

### №2 — MUHIM (UX): Usta "Rastalar" qadamida qo'lda qo'shish yo'q — ✅ TUZATILDI (commit `dc2ea27`)

Bo'sh holat matni "...yoki birinchi rastani **qo'lda qo'shing**" deydi, lekin qadamda faqat Excel yuklash bor — tugma/havola yo'q. "Sotuvchilar" qadamida esa qo'lda qo'shish tugmasi BOR (ichki nomuvofiqlik). Qo'lda qo'shish asosiy "Rastalar" sahifasida mavjud — usta qadamiga tugma yoki havola yetarli.

### №4 — MUHIM (UX): rol tanlanmagan "Saqlash" jimgina hech nima qilmaydi — ✅ TUZATILDI (commit `d059a7d`)

Yangi foydalanuvchi formasi: rol belgilamasdan Saqlash bosilsa — so'rov ketmaydi, xato ham chiqmaydi, dialog ochiq qoladi. Foydalanuvchi "saqlandi" deb o'ylashi mumkin. (Kassir to'lov formasida ham validatsiya xabari juda qisqa: shunchaki "To'lov turi".)

### №8 — TEKSHIRISH KERAK: kassir qidiruvida Enter — ✅ TASHXIS: KOD SOG'LOM (quick 260814-p4g)

> **Xulosa (2026-08-14):** `stall-lookup.tsx` ishlovchisi to'g'ri (`onKeyDown`, `event.key`, `autoFocus`) — 5 gipoteza mexanik rad etildi, 8-holatli fokus-yo'naltirilgan regressiya darvozasi qo'shildi va sabotaj bilan isbotlandi (commit `8ee8e2e`, `e3e0cf4`). Kuzatuv avtomatlash artefakti edi. Real klaviaturada yakuniy 5-soniyalik tasdiq foydalanuvchida qoladi.

Avtomatlash yuborgan jismoniy Enter rasta qidiruvini ishga tushirmadi (JS-event ishladi). **Real klaviaturada 5 soniyada tekshiring:** `/uz/collect` da raqam kiritib Enter bosing. Ishlamasa — bu blocker, chunki butun kassir oqimi shu tugmaga bog'liq. (Avtomatlash vositasining o'ziga xosligi bo'lishi ham mumkin.)

### №1 — MAYDA (tizimiy): uz-lokal sana formati buzuq

"2026 M08 1", "2026 M08 14 12:21" — kamida 4 joyda (tarif dialogi va kartasi, foydalanuvchi kartasi, kadr jadvali). `Intl.DateTimeFormat`ning `uz` lokalidagi ma'lum quirk'i. Bitta umumiy sana-format util bilan tuzatiladi. *8-faza hisobot sahifalarida ham chiqadi — o'sha fazada birga tuzatish tabiiy.*

### №3 — MAYDA: pul formati nomuvofiq

Bitta uz-Latn lokalida ikki xil: tariflar sahifasi "10,000 so'm", rasta kartasi "UZS 8,000", kassir "8,000 so'm". (Ruschada "8 000 UZS".) UI-SPEC bo'yicha yagona formatga keltirish kerak.

### №5 — MAYDA: "oxirgi ko'rilgan: -22 s"

Kameralar ro'yxatida manfiy nisbiy vaqt (sim soat siljishi bilan bog'liq). `Math.max(0, …)` yoki serverdan kelgan vaqtni to'g'ri solishtirish kifoya.

---

## Platforma admin chuqur testi (2026-08-15, Chrome, barcha tugmalar)

Yangi topilmalar (avvalgi raqamlashdan davom — harflar bilan):

| # | Jiddiylik | Topilma |
|---|---|---|
| №A | MUHIM (UX) | Usta 7/7 bajarilgan bo'lsa ham, qoralama bozorni tanlash HAR SAFAR ustaning 1-qadamiga qaytaradi ("Davom etish" → step=2 → ... barcha qadamlar qayta). Dashboard'ga to'g'ri kirish yo'li yo'q |
| №B | MUHIM | Bozorni "Qoralama"dan FAOL holatga o'tkazish tugmasi UI'ning hech qayerida topilmadi (usta yakuni ham, dashboard ham, sozlamalar ham yo'q). Backend'da tushuncha bor (ops docs: "faollashtirilgan bozor o'chirilmaydi"), UI'da yo'l yo'q |
| №C | MUHIM — **MARKET-06 bo'shlig'i** | Plan-xaritada rasta katagi bosilganda HECH NARSA bo'lmaydi va to'lov ranglari yo'q. MARKET-06 ([x] deb belgilangan!) aniq talab qiladi: "rangli grid (yashil bo'sh, ko'k to'langan, qizil qarzdor, sariq nomuvofiq); rasta bosilganda karta (dalil-rasm bilan) ochiladi". Legendada faqat inventar holatlari (Faol/Sotuvchisiz/Ta'mirda/Yopiq) — rang qatlami "6–7-fazada yonadi" deyilgan (ROADMAP 205-qator), lekin 6–7 yakunlangan, yonmagan. Qo'shimcha kontekst: to'liq interaktiv xarita (plan-rasm ustida chizish) rasman V2-PROC-04 ga qoldirilgan — bu alohida; lekin sxematik versiyaning rang+karta qismi MVP talabi va ochiq |
| №D | MUHIM | Ish kunlari → "Istisno kun qo'shish" dialogi: sana+izoh to'ldirilgan holda "Saqlash" bosilganda so'rov ketmaydi, xato ko'rinmaydi, dialog ochiq qoladi (№4 oilasidagi jim no-op; №4 fix'i bu formani qamramagan) |
| №E | MAYDA-MUHIM | Kelajak tarif davri (9,000, 01.09 dan) tarixda "Hozircha amalda" deb yorliqlanadi — aslida "kutilmoqda/…dan kuchga kiradi" bo'lishi kerak. Davr zanjiri o'zi TO'G'RI ishlaydi (eski davr avtomatik yopildi) |
| №F | TEKSHIRISH | Kameralar sahifasida "Diagnostika" tugmasi qurilma ulanish-tahrirlash formasini ochdi ("Qurilma ma'lumotlari") — diagnostika paneli kutilardi. Yorliq-mazmun mosligini kodda tekshirish kerak |
| №G | KUZATUV | Foydalanuvchi amallar menyusida faqat Bloklash/Parol tiklash — mavjud foydalanuvchi ROLLARINI tahrirlash yo'li yo'q (kassirga qo'shimcha rol berish uchun yangi user yaratish kerak bo'ladi) |
| №H | KUZATUV | Platforma admin dashboardida kontent yo'q: bozor holati (qoralama!), rastalar/kameralar/foydalanuvchilar hisoblagichlari — hech nima. 2 ta havola xolos |

## Direktor chuqur testi (2026-08-15, Chrome, barcha yuzalar)

| # | Jiddiylik | Topilma |
|---|---|---|
| №I | MUHIM | Kvitansiya xabari (Olim Karimov, kecha 12:36) **18+ soat "Navbatda", 0 urinish** — navbat jim qotgan. Dev sababi ma'lum (bot token yo'q), lekin UI sababni ko'rsatmaydi va eskirgan-navbat alerti yo'q. Prod'da bu "sotuvchi kvitansiya olmayapti va hech kim bilmaydi" degani. Qatorda sana ham yo'q (faqat "12:36" — qaysi kun?) |
| №J | MUHIM (RBAC-ko'zgu) | Kameralar sahifasida direktorga admin tugmalari ko'rinadi (Qayta skanerlash / **Parolni yangilash** / Diagnostika); bosilganda "Bu amal uchun ruxsat yo'q". Backend to'g'ri 403 qiladi (xavfsizlik buzilmagan, sessiya ham tirik — №7 fix), lekin frontend huquq-ko'zgusi bu sahifada unutilgan — boshqa sahifalarda (rastalar/tariflar/kalendar/foydalanuvchilar) yozish elementlari TO'G'RI yashirilgan |
| — | ZANJIR (№B ta'siri) | Qoralama bozorda kunlik hisob yozilmaydi → to'lovlar "avans"da qoladi → direktor "Bu kunda hisob yozilmagan" ko'radi. Faollashtirish yo'li ochilmaguncha direktor yuzasi asosiy vazifasini bajara olmaydi |
| ⓘ | artefakt | "23" nomli rasta paydo bo'lgan (test qoldig'i) — dev bazadan tozalash kerak |

⭐ Direktor testining eng qimmatli tasdig'i: **ko'r deklaratsiya sikli to'liq ishlaydi** — Patta hisobi sahifasida "Smena hisobi" jadvali: Test Kassir · Deklaratsiya 8,000 · Tizim 8,000 · Farq 0 · "Mos keldi" + "Smenasiz to'lovlar: 0". Kassir yopishda ko'rmagan summa direktorda solishtirilgan holda turibdi — anti-fraud va'da bajarilgan.

✓ Ishlagan direktor funksiyalari: Bugungi tushum real vaqtda · Bandlik (halol bo'sh holatlar + "namuna qo'lda tortilmaydi — tasodifiylik saqlanadi" intizom matni) · Patta hisobi (anomaliya hisoblagichlari, smena solishtiruvi) · Nomuvofiqliklar (band-to'lovsiz / ro'yxatsiz savdo / navbat / aniqlik ulushi / xabar yetkazilishi — struktura to'liq) · RBAC ko'rish-rejimi 4/5 sahifada to'g'ri (kalendar checkboxlari disabled, tugmalar yashirilgan).

---

## Nazoratchi testi (2026-08-15, Chrome)

**Eng muhim tasdiq — ko'r audit yaxlitligi to'liq himoyalangan:** nazoratchi yuzasida AI xulosasi HECH QAYERDA ko'rinmaydi. "Ko'rib chiqish" hub'ining o'zi intizomni e'lon qiladi ("Tasodifiy tanlangan rastalar. Tizim javobini ko'rmaysiz", "Javobingiz yozilgandan keyin o'zgartirib bo'lmaydi"), AI-xulosa bor sahifalar (occupancy, reconciliation) esa route darajasida yopiq — AI-02 o'lchov metodikasining yagona mustaqil yo'li buzilmagan.

| Tekshiruv | Natija |
|---|---|
| Nav tor (Boshqaruv + Ko'rib chiqish) | ✓ |
| Ikki navbat: ko'r tekshirish (0/30) + noaniq (0/50), kunlik limitlar ko'rinadi | ✓ |
| Ko'r audit sahifasi bo'sh holati halol ("namuna kunlik kadrlardan keyin O'ZI tanlanadi — qo'lda tortilmaydi") | ✓ |
| 7 ta taqiqlangan URL (collect/billing/cameras/users/audit/occupancy/reconciliation) → toza "ruxsat yo'q", sessiya 7 tasidan ham omon qoldi (№7 fix zanjirda tasdiqlandi) | ✓ |
| Asosiy baholash oqimi (kadrni band/bo'sh deb belgilash) | CV modeli yo'q — sinab bo'lmadi, model kelganda qaytariladi |

| # | Jiddiylik | Topilma |
|---|---|---|
| №K | KICHIK (UX) | "Bu amal uchun ruxsat yo'q" sahifasi yalang'och — bitta satr, "Boshqaruv paneliga qaytish" havolasi yo'q. Adashgan foydalanuvchi boshi berk sahifada qoladi (faqat brauzer "orqaga") |

---

## Kassir chuqur testi — chekka holatlar (2026-08-15, Chrome)

⭐ **Ikki kuchli anti-fraud mexanizm tasdiqlandi:** (1) "Summani o'zgartirish" MAJBURIY sabab-kod bilan (5 sabab: nazoratchi tasdiqladi / tizim xato band dedi / tarif noto'g'ri / kun o'rtasida bo'shatilgan / direktor kechirdi); (2) "To'lovni bekor qilish" ham sabab-kodli (4 sabab). Har ikkisi audit hodisalari bilan juft ("To'lov summasi o'zgartirildi", "To'lov bekor qilindi"). Qisman to'lov (10,000→5,000) va bekor qilish oqimi ishladi.

| Tekshiruv | Natija |
|---|---|
| Mavjud bo'lmagan rasta (X-99) | ✓ "Bunday raqamli rasta topilmadi — Raqamni tekshirib qayta kiriting" |
| Sotuvchisiz rastaga to'lov (B-01) | Submit'da bloklanadi: "Bu rastaga sotuvchi biriktirilmagan" + **"Qayta yuborish dublikat yaratmaydi"** (idempotentlik va'dasi) ✓ — siyosat aniq |
| Dashboard hisoblagichi | ✓ "1 Bugun yozilgan kvitansiyalar" (biznes-kun to'g'ri) |
| RBAC: /uz/users zondi (№7 ning ASL stsenariysi) | ✓ toza "ruxsat yo'q", sessiya tirik |
| Terminal to'lov turi | ✓ tanlash ishlaydi |

| # | Jiddiylik | Topilma |
|---|---|---|
| №L | MUHIM (biznes-mantiq) | **Ta'mirdagi rasta (A-02) kassir qidiruvida hech qanday ogohlantirishsiz oddiy "Bugungi patta: 8,000" kartasi ko'rsatadi** — ta'mirdagi rastadan patta olinishi kerakmi? Kamida holat belgisi shart. Umuman: lookup kartasida rasta holati/sotuvchi konteksti yo'q — sotuvchisiz rasta ham normal karta ko'rsatib, faqat SUBMIT'da rad etiladi (kassir vaqti bekor ketadi) |
| №M | KICHIK | Bekor qilingandan keyin ro'yxatda ikkita bir xil ko'rinishli qator (original 06:46 + bekor hodisasi 21:19, ikkalasi "A-01 8,000 Bekor qilingan") — qaysi biri nima ekani ajratilmagan. Dashboard hisoblagichi bekordan keyin ham "1" ko'rsatadi ("yozilgan" semantikasi rost, lekin chalg'itishi mumkin) |

---

✓ Ishlagan admin funksiyalari: login/market-picker · rasta tahrirlash + holat almashtirish (Ta'mirda) · kelajak tarif davri + davr zanjiri · haftalik ish kunlari UI · foydalanuvchi Bloklash/Blokdan chiqarish (tasdiq dialoglari bilan) · audit jurnali (blok hodisalari darhol, eski/yangi qiymat, sahifa ko'rishlari ham) · NVR karta/kashfiyot (avvalgi sessiya) · kadr jadvali + №6 tuzatilgan dialog · 3 til.

Eslatma: dev bazada 2 ta "Jonli sinov admini" foydalanuvchisi qoldiq (debug sessiyasidan) — tozalash mumkin.

---

## ✓ O'tgan tekshiruvlar

| Bo'lim | Natija |
|---|---|
| **Auth** | Noto'g'ri parol: aniq xato, ma'lumot sizmaydi · logout ishlaydi · vaqtinchalik parol + majburiy almashtirish darvozasi (D-02) to'liq ishladi |
| **Usta (wizard)** | 7/7 qadam: rekvizitlar → zonalar (2) → toifalar (2) → tariflar (2) → rastalar (3) → sotuvchi (1) → jadval; qadam qulflari va progress to'g'ri |
| **Tariflar** | `10000.50` rad etildi ("butun son bo'lsin") ✓ · o'zgarmaslik xabari ("allaqachon amal qilgan — o'zgartirilmaydi") ✓ |
| **Rastalar** | Dublikat raqam rad ("allaqachon mavjud") ✓ · filtr/qidiruv UI bor · toifa tarifi kartada ko'rinadi |
| **Sotuvchilar** | Telefon `90 765 43 21` → `+998907654321` (E.164) ✓ · rasta biriktirish (o'tgan sanadan) ✓ · maxfiylik banneri ✓ |
| **Foydalanuvchilar** | Yaratish + rol + til · vaqtinchalik parol bir marta ko'rsatiladi ("boshqa ko'rsatilmaydi") ✓ |
| **3 til** | uz-Latn / uz-Cyrl / ru — dashboard, rastalar, sotuvchilar sahifalari to'liq tarjima, `missing.key` yo'q ✓ |
| **Audit jurnali** | 36 yozuv: `vendor_view`/`stall_view` (shaxsiy ma'lumot ko'rish!), yaratishlar, DB-trigger manbalari, eski/yangi qiymatlar, biznes-kun ✓ |
| **NVR (sim)** | Ulanish testi: model DS-7616NI-K2, 6 kanal, soat farqi −1 s ✓ · avtokashfiyot: 6 kamera (nom/IP/model/onlayn) ✓ · parol shifrlash xabari ✓ · zona qamrovi paneli ("3 rasta qamrovsiz") ✓ |
| **Jonli tasvir** | go2rtc → MSE, video 1280×720 o'ynadi ✓ |
| **Kadr jadvali** | Mavsumiy jadval: 4 slot (09–12), "eng erta — ertangi kun" cheklovi, "bugungi reja o'zgarmaydi" (CAM-05) ✓ |
| **Kassir sikli** | Smena ochish → rasta qidiruv → "Bugungi patta 8,000 so'm / Qarzi yo'q" → Naqd → tasdiq = **3 bosish** ✓ · to'lov ro'yxatda (12:36) ✓ · qayta qidiruvda "Ortiqcha to'langan — avans" ✓ · yopishda **ko'r deklaratsiya** ("tizim summasini ko'rsatmaydi — farqni direktor ko'radi") + o'zgarmaslik tasdig'i ✓ |
| **Direktor** | Kirishi bilan "8,000 so'm — Bugungi tushum" (kassir to'lovi real vaqtda) ✓ · nav'da Bandlik/Patta hisobi/Nomuvofiqliklar |
| **RBAC (nav)** | Kassir faqat 2 bo'lim ko'radi (Boshqaruv + Yig'ish) ✓ |
| **RLS izolyatsiyasi** | `npm run test:tenancy` — **731 test, exit 0, 100%** ✓ |

---

## Test qilinmagan (sabablari)

| Nima | Sabab | Qachon |
|---|---|---|
| CV band/bo'sh xulosalari, nazoratchi ko'r auditi, dalil-rasmlar | `.onnx` model yo'q (GPU eksport artefakti), cv-service to'xtatilgan | Model eksportidan keyin |
| Telegram botlar | Token `.env`da yo'q | Token qo'shilganda |
| Zona chizish (kanvas) | Brauzer paneli yashirin — koordinatali klik cheklangan | Qo'lda 2 daqiqa |
| Kadr olishning real ijrosi | Jadval ertadan boshlanadi (dizayn bo'yicha) | Ertaga 09:00 dan `capture_runs`da |
| Xlsx importlar (rastalar/sotuvchilar/xodimlar) | Fayl tayyorlash vaqt oladi; shablon yuklab olish tugmalari bor | Qo'lda |
| Plan-xarita, Bandlik, Nomuvofiqliklar sahifalari batafsil | №7 sessiya bug'i ish oqimini uzdi; ma'lumot ham yo'q (CV o'chiq) | №7 tuzatilgach |
| To'lovni bekor qilish, smena farqi (kam/ko'p naqd) | Vaqt chegarasi | Qo'lda yoki keyingi sessiya |

---

## Muhit holati (test oxirida)

- Stek ishlayapti: API `127.0.0.1:8001`, UI `localhost:8081` (portlar ko'chirilgan — 8000/8080 ni parnikkpi loyihasi band qilgan)
- `cv-service` to'xtatilgan (model yo'q — atayin)
- NVR simulyatori ulangan, 6 kamera ro'yxatda; kadr jadvali ertadan faol
- Test ma'lumotlari: 1 bozor, 2 zona, 2 toifa, 2 tarif, 3 rasta, 1 sotuvchi (A-01 ga biriktirilgan), 1 to'lov (8,000), 1 yopiq smena
- Hisoblar: admin `+998901234567`/`KarmanaDev-2026` · kassir `+998901111111`/`KassirTest-2026` · direktor `+998902222222`/`DirektorTest-2026` · nazoratchi `+998903333333`/`0AMwO6fp_jfp` (vaqtinchalik, hali kirilmagan)

## Tavsiya etilgan keyingi qadamlar

1. **№7 (sessiya)** — `/gsd:debug` bilan alohida tekshirish: refresh rotatsiya poygasi + direktor↔billing RBAC ko'zgusi. Bu go-live uchun bloker darajasida.
2. №8 — real klaviaturada Enter'ni 5 soniyada tekshirish (siz).
3. ~~№6, №4, №2 — `/gsd:quick` bilan arzon yopiladi.~~ — ✅ BAJARILDI (quick 260815-86p: `c411636`, `d059a7d`, `dc2ea27`). Uchalasi ham regressiya testi bilan qulflandi; №4 da IKKINCHI, yashirin nuqson ham topildi va tuzatildi (rol tanlangach xato xabari ekranda qolardi).
4. №1, №3, №5 — 8-faza UI ishlariga qo'shib yuborish tabiiy (hisobot sahifalari baribir sana/pul formatlariga tegadi).
