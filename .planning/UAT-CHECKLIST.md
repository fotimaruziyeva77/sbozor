# SBOZOR — beshta rol uchun to'liq va tanqidiy tekshiruv ro'yxati

> Tuzilgan: 2026-08-20. Manba — **kod inventarizatsiyasi**, taxmin emas:
> `src/app/[locale]/(app)/**/page.tsx` (24 marshrut), `lib/rbac.ts`
> matritsasi va `src/components/**` dagi dialoglar.
>
> **Tanqidiy** degani: «sahifa ochildimi» emas, «ekran ROSTNI aytdimi».
> Har band ikki xil yiqilishi mumkin — ishlamaydi, yoki ishlaydi-yu
> yolg'on gapiradi. Ikkinchisi qimmatroq.
>
> Belgilar: `[ ]` tekshirilmagan · `[x]` o'tdi · `[!]` nuqson topildi ·
> `[–]` bu rolda qo'llanilmaydi.

---

## Hisoblar

| Rol | Telefon | Parol |
|---|---|---|
| Platforma admini | `+998901112233` | `Karmana-Bozor-2026` |
| Bozor admini | `+998904444444` | `BozorAdmin-Karmana-2026` |
| Direktor | `+998902222222` | `Direktor-Karmana-2026` |
| Kassir | `+998901111111` | `Kassir-Karmana-2026` |
| Nazoratchi | `+998903333333` | `Nazoratchi-Karmana-2026` |

⛔ Sessiya brauzer bo'yicha YAGONA: bir tabda boshqa rol bilan kirish
ikkinchisini almashtiradi.

---

## 0. UMUMIY — har rolda TAKRORLANADI

Bu blok beshala rolda alohida bajariladi; natija rol bo'limida yoziladi.

- [ ] **0.1** Kirish ishlaydi; noto'g'ri parol tushunarli xato beradi
- [ ] **0.2** Sarlavhada bozor nomi + rol TO'G'RI yozilgan (boshqa rol nomi emas)
- [ ] **0.3** Menyuda FAQAT shu rolga tegishli bo'limlar bor
- [ ] **0.4** Ruxsatsiz marshrutga URL bilan kirilsa — `ForbiddenNotice`, oq ekran emas
- [ ] **0.5** Tema: yorug' · quyuq · kontrast — uchalasi ham ishlaydi va saqlanadi
- [ ] **0.6** Til: uz-Latn · uz-Cyrl · ru — matn tarjimasiz qolmaydi
- [ ] **0.7** Telefon (375px): gorizontal siqilish 0, 44px'dan kichik nishon 0
- [ ] **0.8** Sahifa YANGILANGANDA sessiya va kontekst saqlanadi
- [ ] **0.9** Chiqish ishlaydi va qaytib kirish talab qilinadi
- [ ] **0.10** Bo'sh holatlar «nima yo'q va nima qilish kerak» deb aytadi
- [ ] **0.11** Xato holatlari texnik matn ko'rsatmaydi (stack, SQL, ichki nom)

---

## 1. PLATFORMA ADMINI (super admin)

> Huquqlar: `market_view_all`, `market_manage`, `user_manage`, `user_view`,
> `audit_view`, `stall_manage`, `tariff_manage`, `vendor_manage`,
> `market_data_view`, `vendor_view`, `camera_view`, `camera_manage`.
> **YO'Q**: `report_view`, `payment_create`, `shift_manage`,
> `occupancy_review`, `dispute_decide`, `billing_collect_view`.

### 1.1 Bozor tanlash — `/select-market`

- [ ] **1.1.1** Ro'yxatda BARCHA bozorlar bor, sanoq to'g'ri
- [ ] **1.1.2** Qoralama bozor `Qoralama` belgisi bilan ajratilgan
- [ ] **1.1.3** Qoralama bosilsa — birinchi TUGALLANMAGAN qadamga tushadi
- [ ] **1.1.4** Faol bozor bosilsa — boshqaruv paneliga tushadi
- [ ] **1.1.5** «Yangi bozor qo'shish» bor va ishlaydi
- [ ] **1.1.6** Ekran to'liq kenglikda, karta chekkaga yopishmagan
- [ ] **1.1.7** Chiqish tugmasi bor (boshi berk ko'cha yo'q)

### 1.2 Bozor yaratish — `/markets/new` (usta 1-qadam)

- [ ] **1.2.1** Bo'sh nom bilan yuborilsa — maydon xatosi, 500 emas
- [ ] **1.2.2** Vaqt mintaqasi tanlanadi; standarti `Asia/Tashkent`
- [ ] **1.2.3** «Bozor ish boshlagan sana» — kelajak sana rad etiladi
- [ ] **1.2.4** Ish kunlari shu qadamda belgilanadi va saqlanadi
- [ ] **1.2.5** «Rasmiy rekvizitlar» yig'ma bo'limi ochiladi/yopiladi
- [ ] **1.2.6** Saqlangach sessiya YANGI bozorga o'tadi (sarlavhada ko'rinadi)
- [ ] **1.2.7** Yaratilgan bozor `is_active = false` (qoralama) bo'ladi
- [ ] **1.2.8** Bir xil nomli ikkinchi bozor — server javobi tushunarli

### 1.3 Usta — `/markets/setup` (2–7 qadam)

- [ ] **1.3.1** Steplerda bloklangan qadam QULF bilan va SABABI yozilgan
- [ ] **1.3.2** Bajarilgan qadam ✓ bilan; sanoq «7 qadamdan N tasi» to'g'ri
- [ ] **1.3.3** `?step=` diapazondan tashqarida bo'lsa — birinchi chalaga tushadi
- [ ] **1.3.4** **2-qadam Zonalar**: qo'shish · nomini o'zgartirish · o'chirish
- [ ] **1.3.5** Rastasi bor zonani o'chirish RAD etiladi va sabab aytiladi
- [ ] **1.3.6** **3-qadam Toifalar**: qo'shish · tahrirlash · o'chirish
- [ ] **1.3.7** **4-qadam Tariflar**: toifaga narx; kelajak sana ishlaydi
- [ ] **1.3.8** O'tgan tarif «o'zgartirilmaydi» deb qulflangan
- [ ] **1.3.9** **5-qadam Rastalar**: qo'lda qo'shish ishlaydi
- [ ] **1.3.10** **5-qadam Rastalar**: Excel shablon yuklab olinadi
- [ ] **1.3.11** Excel import: to'g'ri fayl — nechta qator qo'shilgani aytiladi
- [ ] **1.3.12** Excel import: BUZUQ fayl — qaysi qatorda nima xato ekani aytiladi
- [ ] **1.3.13** **6-qadam Sotuvchilar**: qo'lda + Excel import
- [ ] **1.3.14** 6-qadam «ixtiyoriy» deb belgilangan va o'tkazib yuborish mumkin
- [ ] **1.3.15** **7-qadam Ish kunlari**: haftalik jadval + istisno kunlar
- [ ] **1.3.16** Faollashtirish: chala bozorda RAD etiladi va NIMA yetishmagani aytiladi
- [ ] **1.3.17** Faollashtirish: to'liq bozorda ishlaydi, holat `Faol` bo'ladi
- [ ] **1.3.18** Usta yarim tashlab ketilsa — qaytganda o'sha joydan davom etadi

### 1.4 ⭐ BOZOR SXEMASI — chizish (foydalanuvchi alohida so'ragan)

- [ ] **1.4.1** `/map` plan-xarita ochiladi va rastalarni ko'rsatadi
- [ ] **1.4.2** Xaritada rasta bosilsa — tafsilot ochiladi
- [ ] **1.4.3** Xaritada zona bo'yicha guruhlash tushunarli
- [ ] **1.4.4** Rang izohi (legend) bor va ranglar ma'noli
- [ ] **1.4.5** ⛔ **Rastani sudrab joylashtirish MUMKINMI?** (koordinata bormi)
- [ ] **1.4.6** 40+ rastada xarita o'qilarli qoladimi
- [ ] **1.4.7** **Kamera zonasi chizish** — `/cameras/[id]/zones` ochiladi
- [ ] **1.4.8** Kadr ustida ko'pburchak CHIZILADI (nuqta qo'yish · yopish)
- [ ] **1.4.9** Chizilgan zonaga RASTA biriktiriladi
- [ ] **1.4.10** «Qator yordamchisi» (row assist) — bir qator rastani tez chizadi
- [ ] **1.4.11** Zonani tahrirlash · o'chirish · nuqtasini surish
- [ ] **1.4.12** Qamrov kartasi: nechta rasta zonasiz qolgani aytiladi
- [ ] **1.4.13** Chizishni bekor qilish (Esc / bekor) ishlaydi
- [ ] **1.4.14** Zona saqlangach kadrda ko'rinib turadi
- [ ] **1.4.15** ⛔ **Jarayon OSONMI?** — nechta bosishda bir rasta zonasi chiziladi

### 1.5 Kameralar / NVR — `/cameras`

- [ ] **1.5.1** NVR qo'shish formasi: IP · port · login · parol
- [ ] **1.5.2** «Ulanishni tekshirish» — muvaffaqiyat va XATO holati
- [ ] **1.5.3** Noto'g'ri parolda tushunarli xato (texnik matn emas)
- [ ] **1.5.4** Avtokashfiyot ishga tushadi va topilgan kameralarni ko'rsatadi
- [ ] **1.5.5** Kamera nomini o'zgartirish
- [ ] **1.5.6** Kamerani arxivlash va tiklash
- [ ] **1.5.7** Jonli ko'rish oynasi ochiladi (yoki halol xato beradi)
- [ ] **1.5.8** ⛔ NVR paroli ekranda HECH QACHON ochiq ko'rinmaydi
- [ ] **1.5.9** Parolni almashtirish dialogi ishlaydi

### 1.6 Kadr olish — `/snapshots`

- [ ] **1.6.1** Kunlik kadr jadvali ko'rinadi
- [ ] **1.6.2** Jadval slotlarini tahrirlash
- [ ] **1.6.3** Kadr bosilsa — rasm ochiladi
- [ ] **1.6.4** Olinmagan kadr uchun ALERT bor («yo'qlikka alert»)
- [ ] **1.6.5** Qamrov ogohlantirishi to'g'ri hisoblangan

### 1.7 Reestr va xodimlar

- [ ] **1.7.1** `/stalls` — qo'shish · tahrirlash · toifa berish · filtr
- [ ] **1.7.2** `/vendors` — qo'shish · tahrirlash · rasta biriktirish
- [ ] **1.7.3** Band rastaga ikkinchi sotuvchi — RAD etiladi, kim bandligini aytadi
- [ ] **1.7.4** `/tariffs` — zona · toifa · tarif CRUD
- [ ] **1.7.5** `/calendar` — haftalik jadval + istisno
- [ ] **1.7.6** `/users` — qo'shish (4 rol) · rol o'zgartirish · bloklash · parol tiklash
- [ ] **1.7.7** Vaqtinchalik parol BIR MARTA ko'rsatiladi
- [ ] **1.7.8** Xodimlarni Excel bilan yuklash
- [ ] **1.7.9** `/audit` — filtr (sana · amal · kim · jadval) ishlaydi
- [ ] **1.7.10** Audit yozuvida jadval nomi TARJIMA qilingan
- [ ] **1.7.11** Audit tafsiloti: eski/yangi qiymat farqi ko'rinadi

### 1.8 Platforma adminida BO'LMASLIGI kerak

- [ ] **1.8.1** `/reports` — YO'Q (`report_view` yo'q)
- [ ] **1.8.2** `/collect` — YO'Q (`payment_create` yo'q)
- [ ] **1.8.3** `/review` — YO'Q (`occupancy_review` yo'q)
- [ ] **1.8.4** `/billing` — YO'Q (`billing_collect_view` yo'q)

---

## 2. BOZOR ADMINI

> Huquqlar: platforma adminidagilar MINUS `market_view_all`/`market_manage`,
> PLUS `report_view`, `billing_collect_view`, `shift_manage`.

- [ ] **2.1** Bosh ekran — **Admin paneli** (direktorniki EMAS)
- [ ] **2.2** Sozlash halqasi: foiz va yetti qadam to'g'ri
- [ ] **2.3** «Diqqat talab qiladi» — faqat HAQIQIY bandlar; muammosiz bo'lsa bo'lim yo'q
- [ ] **2.4** Diqqat bandi OQIBATNI aytadi («patta hisoblanmaydi»), sanoqni emas
- [ ] **2.5** Reestr to'rt katagi to'g'ri sanoq beradi va havolalari ishlaydi
- [ ] **2.6** Xodimlar bloki + «Barchasi →»
- [ ] **2.7** Oxirgi o'zgarishlar + «To'liq jurnal →»
- [ ] **2.8** Sotuvchi: qo'shish · tahrirlash · rasta biriktirish · qidiruv
- [ ] **2.9** Tarif: qo'shish · kelajak sana · tarix to'g'ri yopiladi
- [ ] **2.10** Ish kunlari: o'zgartirish OQIBATI tasdiqda aytiladi
- [ ] **2.11** Xodim qo'shish: FAQAT kassir va nazoratchi; sabab yozilgan
- [ ] **2.12** Parol tiklash: vaqtinchalik parol bir marta
- [ ] **2.13** Xodimni bloklash / blokdan chiqarish
- [ ] **2.14** `/reports` ochiladi va eksport ishlaydi
- [ ] **2.15** `/billing` — kutilayotgan patta bozor kesimida
- [ ] **2.16** Kamera va NVR boshqaruvi ishlaydi
- [ ] **2.17** ⛔ Bozor yaratish YO'Q; `/markets/new` — 403
- [ ] **2.18** ⛔ Bozorni faollashtirish YO'Q

---

## 3. DIREKTOR

> Huquqlar: `report_view`, `audit_view`, `camera_view`, `dispute_decide`,
> `user_view`, `market_data_view`, `vendor_view`, `billing_collect_view`.
> **YO'Q**: barcha `*_manage`.

- [ ] **3.1** Bosh ekran — **Bozor paneli** (admin paneli EMAS)
- [ ] **3.2** Davr filtri: Bugun · Kecha · 7 kun · 30 kun — TO'RTALASI ham son beradi
- [ ] **3.3** Kalendar oralig'i ishlaydi; kelajak sana rad etiladi
- [ ] **3.4** «Bugun» tanlanganda: yig'ilgan ko'rinadi, daraja HALOL «—»
- [ ] **3.5** «Kecha» tanlanganda: halqa foiz va uch son to'g'ri
- [ ] **3.6** Bosh katak: yig'ilgan / hisoblangan / yig'ilmagan matematikasi to'g'ri
- [ ] **3.7** Olti katak: har biri o'z sahifasiga to'g'ri olib boradi
- [ ] **3.8** Tushum trendi: 7/30/12 hafta/12 oy oraliqlari ishlaydi
- [ ] **3.9** ⛔ Trend o'qi qiymatlari TAKRORLANMAYDI
- [ ] **3.10** Tugamagan kun trendda uzuq chiziq bilan ajratilgan
- [ ] **3.11** `/reports` — tushum · qarzdorlik · anomaliya · aniqlik
- [ ] **3.12** Har hisobot `.xlsx` bo'lib yuklanadi va faylda DAVR yozilgan
- [ ] **3.13** ⛔ Bugungi kunni qamragan eksport RAD etiladi (imzolanadigan hujjat)
- [ ] **3.14** `/reports/vendor` — sotuvchi kesimi
- [ ] **3.15** `/reports/audit` — tekshiruv varag'i, chop etishga tayyor
- [ ] **3.16** `/reports/compare` — uch tomonlama solishtiruv
- [ ] **3.17** `/reconciliation` — nizo qarori (`dispute_decide`)
- [ ] **3.18** `/audit` — jurnal o'qiladi
- [ ] **3.19** ⛔ `/vendors`, `/tariffs`, `/calendar`, `/users` — FAQAT KO'RISH,
      «Faqat ko'rish» qatori bor, qo'shish tugmasi YO'Q
- [ ] **3.20** ⛔ `/collect` — YO'Q

---

## 4. KASSIR

> Huquqlar: `payment_create`, `billing_collect_view`, `shift_manage`.
> **YO'Q**: `market_data_view`, `vendor_view`, `camera_view`, `report_view`.

- [ ] **4.1** Bosh ekran: smena holati + CTA; ⛔ SUMMA KO'RINMAYDI
- [ ] **4.2** Menyuda faqat: Boshqaruv paneli · Yig'ish (+ Patta hisobi)
- [ ] **4.3** Smena ochish ishlaydi
- [ ] **4.4** Ochiq smena bo'lsa ikkinchisini ochib bo'lmaydi
- [ ] **4.5** Rasta qidirish: kod bo'yicha · sotuvchi bo'yicha
- [ ] **4.6** Kutilayotgan patta: bugungi tarif + eski qarz alohida ko'rinadi
- [ ] **4.7** ⛔ To'lov ≤3 bosishda yoziladi
- [ ] **4.8** Naqd / terminal tanlanadi
- [ ] **4.9** Qisman to'lov: sababi so'raladi
- [ ] **4.10** Muvaffaqiyat animatsiyasi bloklamaydi (≤150ms javob)
- [ ] **4.11** Sotuvchiga cheK ko'rsatish dialogi
- [ ] **4.12** To'lovni bekor qilish (reversal) sababi bilan
- [ ] **4.13** ⛔ **KO'R SANOQ**: smena yopishda kassir SUMMANI KO'RMAYDI
- [ ] **4.14** Deklaratsiya kiritiladi, farq faqat KEYIN ko'rinadi
- [ ] **4.15** Smena yopilgach qayta ochib bo'lmaydi
- [ ] **4.16** ⛔ Telefonda (375px) butun oqim ishlaydi
- [ ] **4.17** ⛔ `/reports`, `/vendors`, `/stalls` — YO'Q

---

## 5. NAZORATCHI

> Huquqlar: `occupancy_review`. Boshqa hech narsa.

- [ ] **5.1** Bosh ekran: nazoratchi uchun mazmunli (bo'sh emas)
- [ ] **5.2** Menyuda faqat: Boshqaruv paneli · Ko'rib chiqish · Bandlik
- [ ] **5.3** `/review` — ko'rib chiqish navbati ochiladi
- [ ] **5.4** Kadr ko'rinadi; kattalashtirish (zoom) ishlaydi
- [ ] **5.5** Qaror paneli: band / bo'sh / noaniq
- [ ] **5.6** Byudjet hisoblagichi: nechta qoldi
- [ ] **5.7** `/review/uncertain` — noaniqlar navbati
- [ ] **5.8** ⛔ `/review/blind` — KO'R sessiya: AI qarorini KO'RMAY baholaydi
- [ ] **5.9** Ko'r sessiya oxirida natija ochiladi (reveal)
- [ ] **5.10** `/occupancy` — kunlik bandlik va chalkashlik matritsasi
- [ ] **5.11** Rasta tafsiloti: kadr + qaror tarixi
- [ ] **5.12** ⛔ Telefonda ishlaydi (nazoratchi dalada)
- [ ] **5.13** ⛔ `/collect`, `/reports`, `/vendors` — YO'Q

---

## 6. IZOLYATSIYA VA XAVFSIZLIK (rollararo)

- [ ] **6.1** Bozor almashtirilgach BOSHQA bozor ma'lumoti ko'rinmaydi
- [ ] **6.2** Begona `market_id` URL'da — 404 (bo'sh ro'yxat EMAS)
- [ ] **6.3** Audit jurnalida faqat SHU bozor yozuvlari
- [ ] **6.4** Ruxsatsiz endpointga to'g'ridan so'rov — 403
- [ ] **6.5** Access token muddati tugagach avtomatik yangilanadi
- [ ] **6.6** Majburiy parol almashtirish chetlab o'tilmaydi

---

## 7. HALOLLIK QOIDALARI (barcha ekranlarda)

- [ ] **7.1** ⛔ O'lchanmagan qiymat o'rniga NOL yozilmaydi — `—` bo'ladi
- [ ] **7.2** ⛔ Hisoblanmagan foiz 0% yoki 100% bo'lib ko'rinmaydi
- [ ] **7.3** ⛔ Kassir kamomadi `abs()` bilan berkitilmaydi (belgi ma'noli)
- [ ] **7.4** ⛔ To'qilgan sana/ism/summa yo'q
- [ ] **7.5** ⛔ Rang YOLG'IZ signal emas — ikonka yoki matn ham bor
- [ ] **7.6** ⛔ Jimgina kesish yo'q: sig'masa RAD etiladi
- [ ] **7.7** Har son o'z dalilagacha ikki bosishda olib boradi

---

## NATIJALAR — 2026-08-20, Chrome, jonli

### Qamrov

| Rol | Bajarildi | Izoh |
|---|---|---|
| Platforma admini | **chuqur** | Bozor yaratishdan zona chizishgacha to'liq |
| Kassir | **chuqur** | Smena · to'lov · ko'r sanoq — uchtasi ham oxirigacha |
| Nazoratchi | **o'rta** | Yuza va navbatlar; navbat bo'sh (kadr yo'q) |
| Bozor admini | **chuqur** | Oldingi sessiyada 8 nuqson topilib tuzatilgan |
| Direktor | **chuqur** | Oldingi sessiyada panel · davr · trend tekshirilgan |

⛔ **Bajarilmadi va sababi bor:** kadr olish (`/snapshots`) va nizo
(`/reconciliation`) oqimlari — ular kamera KADRLARINI talab qiladi,
kadrlar esa zona chizilgandan keyin jadval bo'yicha olinadi. Zona
endi bitta chizildi; kadr sikli aylanganda alohida sinaladi.

### Tuzatilgan nuqsonlar

| # | Nuqson | Og'irlik |
|---|---|---|
| 1 | `setup-status` kamera sonini **qotirilgan 0** qaytarardi — panel 6 ta ishlayotgan kamerani ko'rmay, soxta qizil ogohlantirish chizardi | **jiddiy** |
| 2 | Sahifa yangilansa bozorning **qoralama holati yo'qolardi** — «Faollashtirish» havolasi g'oyib bo'lardi | **jiddiy** |
| 3 | Zona muharririda o'chirilgan tugma sababini **faqat skrinriderga** aytardi | o'rta |
| 4 | Platforma adminida **ikki sarlavha** — bozor nomi va rol ikki marta | o'rta |
| 5 | «Bozor holati» kartasi panel bilan **takrorlanardi** | o'rta |
| 6 | Bozor tanlash ekrani 1878px'da **210px karta**, chap chekkada | o'rta |
| 7 | «Yangi bozor» amali **faqat bo'sh ro'yxatda** bor edi | o'rta |
| 8 | `.dir-tile-note` qoidasi boshqa kartalarga sizib, ~200px teshik qoldirardi | kichik |
| 9 | Rastalar yuzasida pul **`UZS 10,000`** — vergul va ISO kodi bilan | kichik |

### Tasdiqlangan asosiy kafolatlar

- ✅ **Ko'r sanoq**: kassir smena yopishda tizim summasini ham, farqni
  ham KO'RMAYDI. 10 000 yozib, 9 000 deklaratsiya qilindi — ekranda
  faqat 9 000 qoldi.
- ✅ **Ijara izolyatsiyasi**: yangi bozorda Karmananing 41 rastasi,
  26 sotuvchisi va 3700+ audit yozuvidan BIRI HAM ko'rinmadi.
- ✅ **Rasta biriktirish konflikti**: band rastaga ikkinchi sotuvchi
  rad etilib, kim bandligi aytiladi.
- ✅ **Tarif tarixi**: kelajak sana ishlaydi, o'tgan narx qulflangan.
- ✅ **Ish kunlari**: o'zgartirish OQIBATI tasdiqda aytiladi.
- ✅ **Halollik**: «Bu kutilayotgan summa — hisob hali yozilmagan»,
  «Bugungi patta hisobi hali yakunlanmagan» — soxta son yo'q.

### ⭐ Bozor sxemasini chizish — javob

**Rastalarni qo'lda chizib bo'lmaydi.** `stalls` jadvalida koordinata
ustuni yo'q, `konva`/`react-konva` o'rnatilmagan. `/map` — sxematik:
zona = qator, rastalar kod tartibida, «Rasta qo'shilgach xarita
AVTOMATIK chiziladi».

**Haqiqiy chizish kamera zonalarida bor va u yaxshi ishlaydi:**
bir rasta zonasi = **4 bosish** (Yangi zona → ro'yxatdan tanlash →
Rastani biriktirish → rastani tanlash). Tepalar sichqoncha bilan ham,
klaviatura bilan ham suriladi; nusxalash, qaytarish, qator bo'yicha
bo'lish bor; 60 zona chegarasi.

⚠ **«Qator bo'yicha bo'lish» AYNAN IKKI zona tanlangan bo'lishini
talab qiladi** — endi bu ekranda yozilgan (avval faqat skrinrider
eshitardi).

### Ochiq savollar (qaror foydalanuvchida)

1. **Plan-xaritani qo'lda chizish** — qurilsinmi? Kerak: `stalls` ga
   `x/y` (nullable), API, `react-konva` muharrir.
2. **Bozorni sessiya ichida almashtirish** yo'q — platforma admini
   chiqib qayta kirishi kerak. Kodda «v2 ga qoldirildi, alohida audit
   talab qiladi» deb yozilgan, lekin audit yozuvi ALLAQACHON bor
   («Bozorlar · Bozor tanlandi»).
3. **Nazoratchi `/occupancy` ni ko'rmaydi** (`report_view` yo'q) —
   ya'ni o'z ishining natijasini ko'ra olmaydi. Bu qaror atayinmi?
4. **Yig'ish ekranidagi A/B/C/D prefikslari** — bu bozorda C va D
   yo'q; ular ma'lumotdan hosil bo'lishi kerakmi?
5. **Prefiks bosilgach fokus maydonga o'tmaydi** — kassir raqamni
   darhol tera olmaydi (telefonda muhim).
