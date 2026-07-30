# Phase 2: Bozor domeni va "Yangi bozor" ustasi - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 2-bozor-domeni-va-yangi-bozor-ustasi
**Areas discussed:** Rasta identifikatsiyasi, Tarif o'lchovi va tarixi, Sotuvchi biriktirish va qarz, Real ma'lumot kiritish yo'li, Ish kunlari, Plan-xarita

---

## Soha tanlash

| Option | Description | Selected |
|--------|-------------|----------|
| Rasta identifikatsiyasi | Raqamlash sxemasi, unikallik, bo'linish/birlashish | ✓ |
| Tarif o'lchovi va tarixi | Narx nima bo'yicha, tarixiylik mexanizmi | ✓ |
| Sotuvchi biriktirish va qarz | Ko'plik, almashinuv, qarz egaligi | ✓ |
| Real ma'lumot kiritish yo'li | 300–1000 rastani kiritish amaliyoti | ✓ |

**User's choice:** Barcha to'rttasi
**Notes:** Keyinroq Ish kunlari (MARKET-05) va Plan-xarita (MARKET-06) ham qo'shildi — foydalanuvchi "ikkalasini ham muhokama qilaylik" dedi.

---

## Rasta identifikatsiyasi

### 1. Jismoniy raqamlash holati

| Option | Description | Selected |
|--------|-------------|----------|
| Bozor bo'yicha yagona raqam | 1, 2, 3 … 500 — takrorlanmaydi; kassir uchun eng tez | ✓ |
| Har qator ichida qaytadan | Zona + raqam = to'liq identifikator | |
| Aralash / belgilanmagan | Erkin matn kod, bozor bo'yicha unique | |
| Hali bilmayman | Moslashuvchan sxema, Phase 0 da aniqlanadi | |

**User's choice:** Bozor bo'yicha yagona raqam
**Notes:** Bu Karmananing HOZIRGI jismoniy holati — sxema o'ylab topilmadi, haqiqatga moslashtirildi. 6-fazadagi "≤3 bosish" mezonini to'g'ridan-to'g'ri qo'llab-quvvatlaydi.

### 2. Raqam umri

| Option | Description | Selected |
|--------|-------------|----------|
| O'zgartirsa bo'ladi, qayta ishlatilmaydi | Tuzatish mumkin; yopilgan raqam yangi rastaga berilmaydi | ✓ |
| Raqam abadiy qotib qoladi | Umuman o'zgartirilmaydi | |
| O'zgartirsa ham, qayta ishlatsa ham bo'ladi | To'liq erkinlik | |

**User's choice:** O'zgartirsa bo'ladi, qayta ishlatilmaydi
**Notes:** Import paytida xato ehtimoli yuqori (300–1000 qator), shuning uchun tuzatish kerak. Lekin raqamning qayta ishlatilishi hisobotda "12-rasta" ni noaniq qilib qo'yardi.

### 3. Zona tuzilishi

| Option | Description | Selected |
|--------|-------------|----------|
| Yassi ro'yxat, har rastada majburiy | Har rasta aynan bitta zonada | ✓ |
| Yassi ro'yxat, ixtiyoriy | "Zonasiz" rastalar guruhi bo'lishi mumkin | |
| Ikki bosqichli: sektor → qator | Ierarxiya | |

**User's choice:** Yassi ro'yxat, har rastada majburiy
**Notes:** Ierarxiya Karmana hajmi (~300–1000) uchun ortiqcha; ixtiyoriy zona xaritada tartibsiz "boshqalar" blokini keltirib chiqarardi.

### 4. Toifa egaligi

| Option | Description | Selected |
|--------|-------------|----------|
| Rastaga — o'zgarishi mumkin | Toifa rasta atributi, sanadan kuchga kiruvchi o'zgarish | ✓ |
| Rastaga — qotib qoladi | Yaratilganda belgilanadi, o'zgarmaydi | |
| Sotuvchiga biriktiriladi | Toifa sotuvchi bilan keladi | |

**User's choice:** Rastaga — o'zgarishi mumkin
**Notes:** Sotuvchiga bog'lansa, sotuvchisiz band rastaning tarifi noaniq qolardi va "ro'yxatga olinmagan savdo" anomaliyasini hisoblab bo'lmasdi.

---

## Tarif o'lchovi va tarixi

### 1. Tarif kaliti

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat toifa bo'yicha | Har toifaga bitta kunlik narx | ✓ |
| Toifa + zona | Zonaga qarab narx farqi | |
| Rasta o'lchami/maydoni ham | m² yoki o'lcham sinfi | |
| Har rastaga alohida narx | Toifa ishlatilmaydi | |

**User's choice:** Faqat toifa bo'yicha
**Notes:** ROADMAP ham "toifa tarifi" deb yozgan. O'lcham varianti Phase 0 da rejalashtirilmagan dala o'lchovini talab qilardi.

### 2. Tarixiylik mexanizmi

| Option | Description | Selected |
|--------|-------------|----------|
| Amal qilish sanasi bilan qatorlar | `(toifa, valid_from)`; yangi narx = yangi qator | ✓ |
| Sana bilan + hisobda narx nusxasi | Ustiga: `daily_charges` narxni o'ziga nusxalaydi | |
| Faqat joriy narx, tarix yo'q | Ustiga yoziladi | |

**User's choice:** Amal qilish sanasi bilan qatorlar
**Notes:** Uchinchi variant MARKET-03 ni buzardi. Ikkinchi variant (hisobga narx nusxalash) 6-fazaning `daily_charges` dizayni doirasida qayta ko'rilishi mumkin — tanlangan model unga to'sqinlik qilmaydi.

### 3. Tarif tahriri

| Option | Description | Selected |
|--------|-------------|----------|
| Kelajakdagi — ha, o'tmishdagi — yo'q | Sanasi kelmagan tarif tahrirlanadi; o'tgani qulflanadi | ✓ |
| Umuman tahrirlanmaydi | Faqat yangi qator bilan tuzatish | |
| Ha, ammo sabab bilan | O'tmishdagi ham sabab-kod bilan o'zgaradi | |

**User's choice:** Kelajakdagi — ha, o'tmishdagi — yo'q
**Notes:** Uchinchi variant yozilgan hisoblar bilan tarifni nomuvofiq qilib qo'yardi (hisob 15 000, tarif 12 000 deydi).

### 4. Tarif topilmasa

| Option | Description | Selected |
|--------|-------------|----------|
| Hisob yozilmaydi + anomaliya | Fail-closed; "tarifsiz band rasta" hisobotga chiqadi | ✓ |
| Oxirgi ma'lum narx bilan yoziladi | Uzilish bo'lmaydi | |
| Nol summa bilan yoziladi | `CHECK(amount_soum > 0)` buni allaqachon rad etadi | |

**User's choice:** Hisob yozilmaydi + anomaliya
**Notes:** Loyihaning `NULLIF` fail-closed falsafasiga mos. Ikkinchi variant bozorni jimgina eski narxda ishlatib qo'yardi.

---

## Sotuvchi biriktirish va qarz

### 1. Munosabat ko'pligi

| Option | Description | Selected |
|--------|-------------|----------|
| 1 rasta = 1 sotuvchi; 1 sotuvchi = ko'p rasta | Davrlar bilan; qarz sotuvchida jamlanadi | ✓ |
| 1 rasta = 1 sotuvchi, qat'iy | Bir sotuvchi faqat bitta rasta | |
| Ko'p sotuvchi bir rastada | Smena/sherik modeli | |

**User's choice:** 1 rasta = 1 sotuvchi; 1 sotuvchi = ko'p rasta
**Notes:** Ikkinchi variant katta savdogar uchun soxta sotuvchi yaratishga majbur qilardi. Uchinchisi 6-fazaning qarz mantig'ini noaniq qilardi.

### 2. Almashinuvda qarz

| Option | Description | Selected |
|--------|-------------|----------|
| Qarz eski sotuvchida qoladi | Har hisob o'sha kungi sotuvchiga yoziladi | ✓ |
| Qarz rasta bilan o'tadi | Yangi sotuvchi meros qilib oladi | |
| Admin har safar qo'lda hal qiladi | Almashtirishda so'raladi | |

**User's choice:** Qarz eski sotuvchida qoladi
**Notes:** `daily_charges` yozuvi `vendor_id` ni o'zida saqlagani uchun bu qo'shimcha mantiqsiz tabiiy chiqadi.

### 3. Sotuvchisiz band rasta

| Option | Description | Selected |
|--------|-------------|----------|
| Yozilmaydi — anomaliya sifatida chiqadi | ROADMAP 6-faza 3-mezoni bilan bir xil | ✓ |
| "Noma'lum sotuvchi" nomiga yoziladi | Texnik hisob | |
| Rastaga yoziladi, sotuvchisiz | Keyin biriktirilsa qarz o'tadi | |

**User's choice:** Yozilmaydi — anomaliya sifatida chiqadi
**Notes:** Uchinchi variant oldingi qaror (qarz o'tmaydi) bilan zid kelardi.

### 4. Sotuvchi identifikatori

| Option | Description | Selected |
|--------|-------------|----------|
| Majburiy va bozor ichida unique | E.164; bot ulanishi kafolatlanadi | ✓ |
| Ixtiyoriy, lekin kiritilsa unique | Telefonsiz sotuvchi ham ro'yxatda | |
| Majburiy, takrorlanishi mumkin | Oila bitta telefondan | |

**User's choice:** Majburiy va bozor ichida unique
**Notes:** 7-fazadagi BOT-03 (contact ulashish orqali ulanish) aynan shunga tayanadi.

---

## Real ma'lumot kiritish yo'li

### 1. Kiritish usuli

| Option | Description | Selected |
|--------|-------------|----------|
| Excel/CSV import + usta qadamlari | Rasta/sotuvchi importdan, qolgani qo'lda | ✓ |
| Faqat usta ichida generatsiya | "Bu zonaga 1–120 rasta yarat" | |
| Faqat qo'lda, bittalab | ~4 soat uzluksiz kiritish | |
| Import + generatsiya, ikkalasi ham | Ikkita alohida oqim | |

**User's choice:** Excel/CSV import + usta qadamlari
**Notes:** Ikkinchi variant sotuvchilarni (F.I.Sh. + telefon) baribir qo'lda kiritishni talab qilardi.

### 2. Import xatosi

| Option | Description | Selected |
|--------|-------------|----------|
| Hech narsa yozilmaydi, xatolar ro'yxati | All-or-nothing; qator raqami + sabab | ✓ |
| To'g'rilari yoziladi, xatolari o'tkaziladi | Yarim holat | |
| Oldindan ko'rish, keyin tasdiq | Ikki bosqichli oqim | |

**User's choice:** Hech narsa yozilmaydi, xatolar ro'yxati
**Notes:** Yarim kiritilgan holat xavfli — rasta yo'q bo'lsa hisob ham yozilmaydi va buni hech kim sezmaydi.

### 3. Qayta import

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat yangi qo'shiladi, mavjudi tegilmaydi | Eski faylni qayta yuklash zararsiz | ✓ |
| Mavjudi yangilanadi (upsert) | Ommaviy tuzatish uchun | |
| Faylda yo'q rastalar yopiladi | To'liq sinxronizatsiya | |

**User's choice:** Faqat yangi qo'shiladi, mavjudi tegilmaydi
**Notes:** Uchinchi variant chala fayl yuklanganda yuzlab rastani jimgina yopib qo'yardi.

### 4. Usta yakunlanishi

| Option | Description | Selected |
|--------|-------------|----------|
| Ha — kamerasiz "ishlashga tayyor" | Kamera qadamlari ixtiyoriy bo'lim | ✓ |
| Ha, lekin "chala" deb belgilanadi | Doimiy ogohlantirish banneri | |
| Yo'q — kamera majburiy | Phase 2 NVR gacha tugamaydi | |

**User's choice:** Ha — kamerasiz "ishlashga tayyor"
**Notes:** Bu foydalanuvchining "NVR oxirida" strategiyasini ochib beruvchi qaror — 2 → 6 → 7 yo'nalishi NVR'siz to'liq sinaladi.

---

## Ish kunlari (MARKET-05)

### 1. Belgilash usuli

| Option | Description | Selected |
|--------|-------------|----------|
| Haftalik jadval + istisno sanalar | Doimiy rejim + bayram/istisno | ✓ |
| Faqat alohida sanalar | Yiliga 52 ta sana kiritish | |
| Faqat haftalik jadval | Bayramlar ifodalanmaydi | |

**User's choice:** Haftalik jadval + istisno sanalar

### 2. Qamrov darajasi

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat bozor darajasida | Bitta tekshiruv: "bugun bu bozor ishlaydimi?" | ✓ |
| Zona bo'yicha ham | Ayrim zonalar boshqa jadval bilan | |
| Rasta darajasigacha | Har rasta o'z jadvali | |

**User's choice:** Faqat bozor darajasida
**Notes:** Vaqtincha yopiq rasta ehtiyojini `status = ta'mirda/yopiq` allaqachon qoplaydi.

---

## Plan-xarita (MARKET-06)

### 1. Joylashuv manbai

| Option | Description | Selected |
|--------|-------------|----------|
| Avtomatik: zona bo'yicha guruh, kod tartibida | Qo'shimcha ma'lumot shart emas | ✓ |
| Avtomatik + admin qo'lda ko'chira oladi | Drag-drop muharrir | |
| Import faylida koordinata ustuni | Dala ishi qo'shiladi | |

**User's choice:** Avtomatik: zona bo'yicha guruh, kod tartibida
**Notes:** ROADMAP xaritani ataylab "sxematik" deb belgilagan — jismoniy aniqlik talab qilinmaydi.

### 2. Ranglar qamrovi

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat rasta holati | Faol/ta'mirda/yopiq + sotuvchisi bor/yo'q | ✓ |
| Holat + toifa rangi | Ikkita rang tizimi to'qnashishi mumkin | |
| Rangsiz — faqat grid va karta | MARKET-06 qisman bajarilmagan bo'lardi | |

**User's choice:** Faqat rasta holati
**Notes:** 6–7 fazalarda shu grid'ga to'lov/qarz/nomuvofiqlik ranglari qo'shiladi — komponent qayta yozilmaydi.

---

## Claude's Discretion

- Sxema detallari (jadval nomlari, ustunlar, indekslar, FK strategiyasi) — RLS/audit reyestrlariga qo'shish majburiyati bilan
- API shakli: endpoint yo'llari, keyset paginatsiya, filtr parametrlari
- Usta qadamlarining UI oqimi, qoralama saqlash, orqaga qaytish mexanikasi
- Excel shablon tuzilishi, ustun nomlari, validatsiya xabarlarining aniq matni
- Bozor rekvizitlari to'plami (nom, manzil, STIR, bank ma'lumotlari)
- Rasta holatlari o'rtasidagi o'tish qoidalari
- Xarita komponentining texnik amalga oshirilishi (SVG/grid vs react-konva)
- RBAC matritsasini kengaytirish (bozor admini vs platforma admini huquqlari)

## Deferred Ideas

- Toifa+zona yoki rasta o'lchamiga bog'liq tarif — v2
- Bir rastada bir necha sotuvchi (smena/sherik) — v2
- Qarzning rasta bilan o'tishi — Phase 0 "rasta almashinuvi" savolidan keyin qayta ko'riladi
- Xaritada qo'lda joylashtirish (drag-drop) va jismoniy koordinatalar — v2
- Ko'p tilli DB kontenti — 1-faza D-16 bo'yicha qurilmaydi
- Import orqali upsert yoki to'liq sinxronizatsiya — alohida "ommaviy tahrir" oqimi sifatida
- Sotuvchi bir necha bozorda savdo qilishi — v2
- Telefonsiz sotuvchi — dala ishida ko'p chiqsa qayta ko'riladi
