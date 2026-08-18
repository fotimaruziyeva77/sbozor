# SBOZOR — Direktor paneli uchun UI brief

> **Bu sahifa mahsulotning yuzi.** Uni uch xil odam ko'radi va uchalasi ham boshqa narsa izlaydi. Sotib olish qarori ham, davlat ishonchi ham shu ekranda hal bo'ladi.
> **Sana:** 2026-08-18 · **Design system:** «Sbozor.uz Design System» — faqat o'sha komponentlar.
> **Oila:** `Sbozor Landing v2` · `Sbozor Login` · `Sbozor Kassir` · `Sbozor Nazoratchi`.
>
> ⚠️ Quyidagi hamma narsa kodda tekshirilgan. «Bor» deyilgan narsa haqiqatan ishlaydi; «yo'q» deyilgani haqiqatan yo'q.

---

## 1. Kim ko'radi va nimadan hayratlanadi

| Kim | Qachon | Nima izlaydi | Ekran unga nima berishi kerak |
|---|---|---|---|
| **Bozor direktori** | Har kuni, 2–5 daqiqa | «Kecha qancha yig'ildi, nima yo'qoldi?» | Bir qarashda javob, so'ng sababga olib boradigan yo'l |
| **Sotib oluvchi** (boshqa bozor, MChJ) | Demo, 10 daqiqa | «Bu bizga ham kerakmi?» | Mahsulotning o'zi reklama bo'lishi — ishonchli, tez, aniq |
| **Tekshiruvchi** (hokimlik, soliq, audit) | Kutilmaganda | «Raqamlar rost ekaniga nima dalil?» | Har raqamdan **dalilga** olib boradigan zanjir va yuklab olinadigan hujjat |

### Hayratlanish qayerdan keladi — bu briefning bosh g'oyasi

⛔ Bezakdan emas. Gradient, uch o'lchamli grafik, parvoz qiluvchi zarrachalar — bular tekshiruvchini hayratlantirmaydi, **shubhalantiradi**.

Hayratlanish uchta narsadan keladi:

1. **Har raqam dalilga ulangan.** Tekshiruvchi istalgan songa bosadi va **ikki bosishda** uning manbasiga tushadi: qaysi rasta, qaysi kun, qaysi kassir, qaysi kamera kadri. Hech bir raqam «osmondan» kelmaydi.
2. **Tizim o'z xatosini o'zi ko'rsatadi.** Aniqlik ulushi, nomuvofiqliklar, qog'oz daftar bilan farq — hammasi ochiq turadi. Yashiradigan mahsulot ishonch qozonmaydi; **o'z farqini birinchi bo'lib ko'rsatadigan** mahsulot qozonadi.
3. **Ma'lumotning yoshi ko'rinib turadi.** Har blokda «qachon yangilandi» yozuvi bor. Tekshiruvchi ekranga qarab «bu eski raqam emasmi?» deb o'ylamaydi.

**Sifat mezoni:** tekshiruvchi ekranni ko'rib *«bu odamlar o'z ishini biladi»* desin — *«chiroyli ekan»* emas.

---

## 2. Bugungi holat — nima bor, nima yo'q

**Bor va yaxshi ishlaydi:** hisobot davri tanlash (oxirgi 30 kun · kecha · shu oy · o'tgan oy · qo'lda oraliq) · tushum hisoboti kunlar kesimida · **qarzdorlar reestri** (sotuvchi, rastalari, qarzi, eng eski qarz sanasi, qarz bo'yicha tartiblangan) · anomaliyalar arxivi · AI aniqligi (ishonch oralig'i bilan) · beshta Excel eksporti · qog'oz daftarni tizim va AI bilan solishtirish · nomuvofiqlik navbati va nizo qarori · audit jurnali · kamera kadrlariga kirish.

**Yo'q:** haftalik kesim · oylik yig'indi (faqat oraliq, natija baribir kunlar) · davrlarni solishtirish va o'sish · sotuvchi bo'yicha to'lov tarixi · qarzdordan ichiga bosib kirish · qarz yoshi (30/60/90) · ma'lumot yangilanish belgisi · audit jurnali eksporti · PDF/chop etish · bandlik foizi · panelda xato holati (xato bo'lsa karta umuman chizilmaydi).

---

## 3. Ekran arxitekturasi

Bitta uzun sahifa emas, **uch qatlam**:

**1-qatlam — «Bugun» (panel).** Direktorning har kungi 2 daqiqasi. Eng ko'pi bilan **oltita** ko'rsatkich, har biri bosiladigan.

**2-qatlam — «Davr» (hisobotlar).** Davr tanlanadi, to'rt blok chiqadi, har biri Excel'ga chiqadi.

**3-qatlam — «Dalil» (chuqurlik).** Har raqamdan pastga: kun → rasta → to'lov → kamera kadri → audit yozuvi.

⛔ **Ikki bosish qoidasi:** panelning istalgan sonidan uning dalili **ikki bosishda** ochilishi shart. Uch bosish bo'lsa — arxitektura noto'g'ri.

---

## 4. «Bugun» qatlami — panel

Oltita katak, ahamiyat tartibida:

1. **Kechagi tushum** — eng katta raqam. Yonida **o'tgan hafta shu kuniga nisbatan o'zgarish** (masalan `+12%` yoki `−4%`), o'q va rang bilan. ⚠️ Foiz ko'rsatiladi, lekin **faqat ikkala davr ham to'liq yopilgan bo'lsa**; aks holda foiz o'rniga «to'liq emas» yozuvi.
2. **«Band, lekin to'lovsiz»** — soni va summasi. Bu mahsulotning bosh va'dasi, shuning uchun panelda alohida katak.
3. **Qarz jami** — va nechta sotuvchida. Bosilsa qarzdorlar reestriga tushadi.
4. **Bandlik** — donut, **foiz bilan** (hozir foiz umuman ko'rsatilmaydi — bu kamchilik).
5. **AI aniqligi** — oxirgi o'lchov ulushi va namuna hajmi. Tekshiruvchi uchun eng qimmatli katak.
6. **Kassirlar** — nechta smena yopildi, deklaratsiya va tizim farqi.

Ostida **tushum trendi** — hozirgi 7 kun o'rniga **tanlanadigan kesim: 7 kun · 30 kun · 12 hafta · 12 oy**.

Har katakda:
- **«Yangilandi: 09:41»** yozuvi va yonida qayta yuklash tugmasi.
- Bosilganda — tegishli chuqur sahifaga o'tish.
- Yuklanayotganda — o'lchami oldindan band skelet (sakrash yo'q).
- **Xato bo'lsa — katak yo'qolmaydi**, ichida «Yuklanmadi · Qayta urinish» turadi. Hozirgi xatti-harakat (kartani umuman chizmaslik) yaramaydi: direktor «ruxsat yo'q», «ma'lumot yo'q» va «server o'lgan» ni farqlay olmaydi.

---

## 5. Vaqt kesimlari va solishtirish

**Kesimlar:** kun · **hafta** · **oy** · choraк · yil · qo'lda oraliq. Hafta va oy hozir umuman yo'q — bu eng ko'p so'raladigan kesim.

**Yig'indi qatori majburiy.** Oy tanlansa, jadval kunlar bilan boshlanmaydi — avval **oylik yakun**, keyin ochib ko'riladigan kunlar.

**Solishtirish** — alohida rejim: joriy davr va oldingi davr yonma-yon, farq va foiz bilan. Uch xil solishtirish kerak:
- oldingi davr bilan (oy → o'tgan oy)
- o'tgan yilning shu davri bilan
- qo'lda tanlangan ikki davr

⛔ **Halollik cheklovi:** foiz **faqat to'liq yopilgan davrlar** uchun. Yarim oyni to'liq oy bilan solishtirib «−48%» chiqarish — yolg'on. Davr to'liq bo'lmasa foiz o'rnida «davr tugamagan» belgisi turadi.

---

## 6. Sotuvchi hisobi — hozir umuman yo'q

Bu eng katta bo'shliq. Kerak: **sotuvchi sahifasi**, unda:
- Ismi, telefoni, rastalari, biriktirilgan sanasi
- **To'lov tarixi**: sana · rasta · summa · usul · kassir · holat (o'z vaqtida / kechikkan / bekor qilingan)
- **Qarz**: jami, eng eski qarz sanasi, **qaysi kunlardan yig'ilgani**
- Davr bo'yicha yig'indi va grafik
- Kechikish naqshi: «oxirgi 30 kunda 4 marta kechikkan»
- Excel eksporti — bitta sotuvchi bo'yicha

**Kirish yo'llari:** qarzdorlar reestridan bosib · sotuvchilar ro'yxatidan · nomuvofiqlikdan.

⛔ **Maxfiylik:** sotuvchi ismi **faqat shu yerda va direktor panelida** ko'rinadi (kassir va nazoratchida hech qachon). Sahifada ochiq eslatma: «Bu ma'lumotni ko'rganingiz audit jurnaliga yoziladi» — hozir sotuvchilar ro'yxatida shunday eslatma bor, uni saqlang.

---

## 7. Qarz va kechikish

Qarzdorlar reestri bor, lekin **jonsiz**: bosib bo'lmaydi, yoshi yo'q.

Kerak:
- **Qarz yoshi ustunlari**: 0–30 · 31–60 · 61–90 · 90+ kun. Rang: yangi qarz neytral, 90+ kun qizil.
- **Qatorga bosilsa** — sotuvchi hisobi ochiladi va qarz qaysi kunlardan tashkil topgani ko'rinadi.
- **Qarz dinamikasi**: davr davomida qarz o'sdimi yoki kamaydimi — bitta chiziq.
- Reestr tepasida: jami qarz · qarzdorlar soni · o'rtacha qarz yoshi.

---

## 8. Tekshiruvchi rejimi — yangi va eng muhim

Alohida ko'rinish: **«Tekshiruv uchun»**. Bitta sahifada, chop etish va Excel'ga yaroqli:

- Tanlangan davr va bozor nomi
- **Hisoblangan · Yig'ilgan · Farq** — uchtasi yonma-yon
- «Band, lekin to'lovsiz» soni va summasi
- Qog'oz daftar bilan solishtiruv natijasi (mos · daftar ortiq · tizim ortiq)
- AI aniqligi va namuna hajmi
- Nomuvofiqliklar: nechtasi ko'rildi, nechtasi asosli
- Dalillar: nechta rasm-dalil biriktirilgan
- **Har bandda «Batafsil»** — chuqur sahifaga
- Pastda: **hamma narsani bitta arxivda yuklab olish**

⛔ Bu sahifada **yangi raqam tug'ilmaydi** — hammasi mavjud bloklardan yig'iladi. U yangi haqiqat emas, **bir joyga yig'ilgan haqiqat**.

---

## 9. Ma'lumot yangiligi

Har blokda: **«Yangilandi: 09:41»** + qayta yuklash tugmasi. Ma'lumot 15 daqiqadan eski bo'lsa — yozuv kuchsiz sariq rangga o'tadi.

⛔ **Avtomatik jimgina yangilanish YO'Q.** Sababi mahsulotning o'zagida: o'zi o'zgargan raqam «men boshqa raqam ko'rgandim» degan nizoni tug'diradi. To'g'ri yechim — **yangilanish borligini aytish**: «Yangi ma'lumot bor — yangilash» degan kuchsiz yorliq, bosilsa yangilanadi. Direktor o'zi qaror qiladi.

---

## 10. Detal darajasi — eng kichigigacha

### Raqamlar
- Pul: butun son, so'm, mingliklar **bo'shliq** bilan (`12 480 000 so'm`), **tabular** raqamlar — ustunda sakramaydi
- Panel ko'rsatkichlari: **sanab o'sadi** (600 ms, tez boshlanib sekin tugaydi), oxirgi kadr **aniq qiymat** bo'ladi
- Foiz: bitta kasr belgisi (`+12.4%`), o'q bilan; nol o'zgarish — o'qsiz, neytral
- Sana: **`18-avgust, 2026`** ko'rinishida. ⛔ Hozir `2026 M08 18` chiqadi — bu nuqson, dizaynda to'g'ri format ko'rsatilsin
- Vaqt: `09:41`, Toshkent vaqti
- Sanoq: 1 000 dan katta bo'lsa ham to'liq yoziladi, qisqartirilmaydi (`12.4k` — YO'Q)

### Ranglar
- Aksent **bitta** — ko'k. Har blokda faqat bitta to'ldirilgan tugma
- Yashil = to'langan/mos · sariq = ogohlantirish/kechikish · qizil = qarz/xato. Rang **hech qachon yolg'iz signal emas** — yonida matn yoki ikona
- O'sish yashil, pasayish qizil **emas**: tushum pasayishi qizil bo'lsin, lekin qarz pasayishi **yashil** — ya'ni rang «yaxshi/yomon» ni bildirsin, «ko'p/kam» ni emas
- Uch tema: yorug' · **quyosh ostida** (soyasiz, kontrast 21:1) · tungi

### Animatsiya
- Kirish: kartalar 60 ms kechikish bilan navbatma-navbat (8px pastdan + shaffoflik)
- Grafik: chiziq chapdan o'ngga chiziladi (600 ms), donut to'ladi
- Qiymat o'zgarsa: karta bir marta **yumshoq nafas oladi** — cheksiz pulsatsiya YO'Q
- Davr almashsa: eski raqam yangisiga **sanab o'tadi**, sakrab almashmaydi
- Jadval qatori ochilsa: balandlik emas, **shaffoflik va siljish**
- Hammasi 150/250/400 ms doirasida, faqat `transform` va `opacity`
- «Harakatni kamaytirish» yoqilsa — hammasi o'chadi, ma'no yo'qolmaydi

### Kirish elementlari
- Davr tanlash: tayyor variantlar **tugma qatori** bo'lib (ro'yxat emas — bir bosish tejaydi), yonida qo'lda oraliq
- Tanlangan davr **URL'da** — havolani nusxalab yuborsa, xuddi shu ko'rinish ochiladi
- Sana maydonlari: kelajak sanani tanlab bo'lmaydi, chegara ko'rinib turadi
- Qidiruv: yozilganda kutish 300 ms, natija soni ko'rsatiladi
- Jadval: ustun bo'yicha tartiblash **serverda**, klientda qayta hisoblanmaydi
- Har eksport tugmasida: nima yuklanayotgani va davri yozilgan

### Bo'sh va xato holatlari
- Bo'sh: **sababi bilan** — «Bu davrda qarz yo'q» ≠ «Ma'lumot yuklanmadi» ≠ «Ruxsat yo'q»
- Nol qiymat **yashirilmaydi** — nol ham javob
- Xato: sabab + nima qilish + qayta urinish tugmasi
- Yuklanish: skelet **aniq o'lchamda** — kontent kelganda sahifa sakramaydi

---

## 11. Chizilmasin

- ❌ Yumaloqlangan yoki qisqartirilgan pul (`12.4 mln`) — tekshiruvchi aniq son izlaydi
- ❌ Uch o'lchamli grafik, gradient to'ldirilgan diagramma, aylanuvchi elementlar
- ❌ O'lchanmagan bashorat («keyingi oyda 15% o'sadi»)
- ❌ Foiz to'liq bo'lmagan davr uchun
- ❌ Cheksiz pulsatsiya, avtomatik aylanadigan slayd
- ❌ Kassir yoki nazoratchi ko'radigan ma'lumot bu yerda takrorlanmaydi
- ❌ Sotuvchi fotosurati yoki pasport ma'lumoti

---

## 12. Backend talab qiladiganlar

| Band | Bugun chiziladimi | Backend kerakmi |
|---|---|---|
| Panelning 6 kataki | Ha | Qisman — «band lekin to'lovsiz» va kassirlar kesimi bor, qolganiga yangi so'rov |
| Yangilanish vaqti belgisi | Ha | Yo'q (javob vaqti allaqachon bor) |
| Xato holati kartada | Ha | Yo'q |
| Bandlik foizi | Ha | Yo'q (ikkala son bor) |
| Haftalik/oylik yig'indi | Ha | **Ha** |
| Davrlarni solishtirish, o'sish | Ha | **Ha** |
| Sotuvchi hisobi | Ha | **Ha** |
| Qarz yoshi (30/60/90) | Ha | **Ha** |
| Qarzdordan bosib kirish | Ha | **Ha** (sotuvchi hisobi bilan birga) |
| Tekshiruvchi rejimi | Ha | Qisman — bloklar bor, yig'ma so'rov kerak |
| Audit jurnali eksporti | Ha | **Ha** |
| Chop etish ko'rinishi | Ha | Yo'q |
| Sana formati tuzatilishi | Ha | Yo'q |

---

## 13. Kutilayotgan natija

1. **`Sbozor Direktor.dc.html`** — «Bugun» paneli: olti katak, trend (4 kesim), yangilanish belgilari, xato/bo'sh/yuklanish holatlari almashtiriladigan.
2. **`Sbozor Direktor — Hisobot.dc.html`** — davr qatlami: kesim tanlash, yig'indi + kunlar, qarzdorlar (yosh ustunlari bilan), anomaliyalar, AI aniqligi, eksportlar; **solishtirish rejimi** ham.
3. **`Sbozor Direktor — Sotuvchi.dc.html`** — sotuvchi hisobi: profil, to'lov tarixi, qarz tarkibi, kechikish naqshi, eksport.
4. **`Sbozor Direktor — Tekshiruv.dc.html`** — tekshiruvchi uchun bitta yig'ma sahifa, chop etishga yaroqli.
5. Mobil 390px ham buzilmasin (direktor telefondan qaraydi), desktop 1280px asosiy.
6. Uch temadan kamida **yorug'** va **tungi**; quyosh ostida varianti ham ko'rsatilsin.
