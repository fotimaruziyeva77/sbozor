# SBOZOR — Kassir ekranlari uchun UI brief

> **Maqsad:** bozor kassiri kuniga yuzlab marta takrorlaydigan bitta amalni — «rasta uchun patta to'lovini yozish» — eng tez, eng xatosiz va quyosh ostida ham o'qiladigan qilib chizish.
> **Sana:** 2026-08-18 · **Ijro:** dizayn tasdiqlangach mavjud Next.js ilovasiga ko'chiriladi.
> **Oila:** `Sbozor Landing v2.dc.html` va `Sbozor Login.dc.html` bilan **bitta mahsulot** bo'lib ko'rinishi shart.
>
> ⚠️ Bu brief **mavjud, ishlayotgan ekranlarni qayta chizish** haqida. Quyidagi hamma narsa kodda tekshirilgan — o'ylab topilgan funksiya yo'q. 8-bo'limda «chizilmasin» ro'yxati bor: unda sanab o'tilgan narsalar tizimda **umuman yo'q** va ularni dizaynga qo'shish yolg'on va'da bo'ladi.

---

## 1. Kassir kim va qayerda ishlaydi

| Fakt | Dizaynga ta'siri |
|---|---|
| Bozor ichida, **tik turib**, ko'pincha bir qo'lda telefon | Asosiy harakatlar bosh barmoq yetadigan pastki zonada |
| Ikkinchi qo'lida **naqd pul** | Forma to'ldirish emas — tanlash; har ortiqcha bosish real sekinlashuv |
| **Quyosh ostida** ishlaydi | Uchinchi tema majburiy: sof oq fon, qora matn, **soya yo'q**, kontrast 21:1 |
| Kuniga **yuzlab** bir xil amal | Muvaffaqiyat sokin bo'lsin — bayram animatsiyasi kunda 300 marta charchatadi |
| Navbatda odam turadi | To'lov yozilgach kursor **o'zi** rasta maydoniga qaytadi (0 bosish) |
| Xato = pul masalasi | Bekor qilish bor, lekin **sababsiz va tasdiqsiz emas** |

**Yagona vazifa:** rasta raqami → summa → tasdiq. Qolgan hamma narsa ikkinchi darajali.

## 2. Buzilmaydigan talablar

1. **To'lov AYNAN 3 ta o'zaro ta'sirda.** Bu shior emas — testlar bilan qulflangan. Bir nechta rasta topilsa, qo'shimcha tanlov **birinchi qadam ichida** qoladi (jami 4), yangi qadam ochilmaydi.
2. **Barmoq nishoni:** oddiy tugma ≥44px, asosiy oqim elementlari 56px (rasta maydoni, tasdiqlash tugmasi, naqd summa maydoni), to'lov turi 48px.
3. **Uch til:** o'zbek lotin · o'zbek kirill · rus. ⚠️ `Instrument Sans` da **kirill yo'q** — kirill matn tizim shriftiga tushadi. Shuning uchun tugma va yorliqlar matn uzunligiga bog'lanib qolmasin.
4. **Uch tema:** yorug' · tungi · **quyosh ostida**. Bitta tuzilma, uch rang to'plami.
5. **Pul:** butun son, so'm; mingliklar bo'shliq bilan, raqamlar **tabular** (ustunda sakramaydi). Kasr yo'q. Pul va texnik qiymatlar **monospace**, rasta raqami esa **monospace EMAS** (u odam o'qiydigan yorliq).
6. **Vaqt:** Asia/Tashkent.
7. **Harakat:** faqat `transform`/`opacity`; «harakatni kamaytirish» yoqilsa hammasi o'chadi; **cheksiz pulsatsiya yo'q**.
8. **Bloklangan tugma «o'chirilgan» emas** — u ko'rinadi, fokus oladi va nega bloklanganini aytadi (ekran o'quvchi o'chirilgan tugmani umuman o'qimaydi).

## 3. Kassirning butun dunyosi — atigi 3 ta ekran

Kassirga ruxsat: to'lov yozish · yig'ish ekranini ko'rish · smena boshqaruvi. **Boshqa hech nima:** hisobotlar, kameralar, sotuvchilar ro'yxati, xarita, tariflar — hammasi yopiq.

Navigatsiyada **atigi ikkita** band: «Boshqaruv paneli» va «Yig'ish». «Ko'proq» tugmasi umuman chizilmaydi. Smena — navigatsiyada emas, «Yig'ish» sarlavhasi yonidagi havola.

### 3.1 «Patta yig'ish» — asosiy ekran (kassirning uyi)

**Old shart:** smena ochiq bo'lmasa, ekranda **faqat** bo'sh holat turadi: «Ochiq smena yo'q» → «Avval smenani ochish kerak» → [Smenani ochish]. To'lov yuzasi umuman chizilmaydi.

**1-qadam — rasta.** Yorliq «Rasta raqami», izoh «Raqamni kiritib «Enter» bosing». Maydon raqamli klaviatura chaqiradi, avtomatik fokusda. Bir nechta moslik topilsa — raqamlar ro'yxati (har biri katta tugma).

**Summani ko'rsatish (bosishsiz).** Rasta topilgach summa **o'zi** chiqadi:
- Kutilayotgan patta banneri: «Bu kutilayotgan summa — hisob hali yozilmagan.»
- Rasta raqami
- **Ekrandagi eng katta raqam** — summa + «so'm»
- Yon holatlar: eski qarz · «Qarzi yo'q» · «Ortiqcha to'langan — avans»
- Qarz bo'lsa: **[Qarzni ham olish · N so'm]** — server hisoblagan jami
- **[Summani o'zgartirish]** — kam ishlatiladigan, ataylab **kuchsiz** ko'rinishdagi havola

**2-qadam — to'lov turi.** Ikki katta tanlov: **Naqd** / **Terminal**. Ikkalasida ham ikona **va** matn (faqat ikona yaramaydi).

**3-qadam — tasdiq.** [To'lovni tasdiqlash] — ekrandagi **yagona** to'ldirilgan aksent tugma.

**Yozilgach:** qisqa tasdiq (belgi chizilishi ~250ms), summa ro'yxatga «uchib» tushadi (~400ms), yangi qator joyiga qo'nadi (~800ms), toast: «To'lov yozildi · A-01 · 8 000 so'm». Kursor rasta maydoniga qaytadi.

**«Oxirgi to'lovlar».** Har doim ko'rinadi (bo'sh bo'lsa ham). Server **qat'iy 5 ta** yozuv beradi — sahifalash, «yana yuklash», jami summa, hisoblagich **yo'q** va bo'lishi ham mumkin emas. Har qatorda: rasta · summa (ishorali) · usul (ikona+matn) · vaqt · holat yorlig'i. Uch holat: **To'lov yozildi** / **Bekor qilingan** (summa chizilgan) / **Bekor qilish yozuvi** (manfiy summa).

**Bekor qilish.** Yozilgan qatordagi [Bekor qilish] → tasdiq oynasi: sabab **ro'yxatdan** tanlanadi (erkin matn yo'q), sababsiz tasdiq bloklangan. Bekor qilingan yozuv ro'yxatdan **yo'qolmaydi** — audit izi.

### 3.2 «Smena»

**A — smena yo'q:** «Ochiq smena yo'q» → [Smenani ochish].
**B — smena ochiq:** yorliq «Boshlangan vaqt» + sana-vaqt + [Smenani yopish].
⛔ Bu kartada to'lovlar soni, yig'ilgan naqd, o'rtacha, «bugungi natija» — **hech qanday raqam yo'q**.
**C — yopish formasi:** «Qo'lingizdagi naqdni sanab kiriting. Tizim summasini ko'rsatmaydi — farqni direktor ko'radi.» Bitta katta raqamli maydon → tasdiq oynasi (kiritilgan summa takrorlanadi) → yoziladi.
**D — natija: aynan 3 element** — yashil «Deklaratsiya yozildi» yorlig'i · kiritilgan summa · [Yangi smena ochish]. To'rtinchi element qo'shilmaydi.

> **«Ko'r» deklaratsiya — mahsulotning mag'zi.** Kassir kutilayotgan summani ko'rmaydi, shuning uchun unga moslab yozolmaydi. Dizayn buni **yashirmasin**, aksincha halol tushuntirsin.

### 3.3 «Boshqaruv paneli»

Kassir uchun **bitta** ko'rsatkich: «Bugun yozilgan kvitansiyalar (bekor qilingani ham)» — bu **son**, pul emas, shuning uchun «so'm» so'zi chiqmaydi. Boshqa kartalar (daromad, bandlik, bozor holati) kassirga umuman yuborilmaydi.

## 3.4 ⚠️ HAL QILINMAGAN MASALA: kassir rastani qanday topadi?

Kassir bozor ichida yuradi, rasta yoniga boradi. **Bu rasta aynan qaysi raqam ekanini u qayerdan biladi?**

**Bugungi holat (o'lchangan):**
- Yagona yo'l — **raqamni yoddan yozish**. Boshqa usul yo'q.
- Qidiruv maydoni **prefiks** bo'yicha ishlaydi: `A` yozilsa `A-01`, `A-02` ro'yxati chiqadi. Ya'ni ko'rish imkoni **bor, lekin yashirin** — foydalanuvchiga bu hech qayerda aytilmagan («Raqamni kiritib Enter bosing» deydi, xolos).
- Ro'yxatda **faqat raqam** ko'rinadi: sotuvchi ismi ham, qator nomi ham, holat ham yo'q.
- **Rastalar ro'yxati va bozor xaritasi kassirga YOPIQ** — bu sahifalar tizimda bor, lekin kassirda ruxsat yo'q.
- **QR / shtrix-kod skaneri yo'q**, NFC yo'q, «yaqin atrofdagi rastalar» yo'q, rasta fotosurati yo'q.

**Demak bugun tizim jimgina shuni talab qiladi:** har bir rastada raqam **jismonan** yozilgan bo'lsin (taxta, stiker, bo'yoq). Aks holda kassir ishlay olmaydi. Bu operatsion talab hech qayerda yozilmagan.

**Dizayn hal qilishi kerak — variantlar (birini yoki bir nechtasini taklif eting):**

| Variant | Nima beradi | Narxi |
|---|---|---|
| **A. Prefiks ro'yxatini ochiq qilish** | `A` yozilsa — o'sha qatordagi hamma rasta ro'yxat bo'lib chiqadi; izoh «Qator harfini yozing — ro'yxat chiqadi» | Eng arzon: server allaqachon shunday ishlaydi, faqat ko'rinish va matn |
| **B. Qator bo'yicha tanlash** | Maydon ustida qator tugmalari: `A` `B` `C` … → bosilsa o'sha qatordagi rastalar | O'rtacha: ro'yxat bor, guruhlash kerak |
| **C. Rasta yorlig'ida QR** | Rastadagi stikerda QR; kassir kamerada skanerlaydi → to'g'ridan-to'g'ri summa | Qimmat: stiker chop etish + kamera ruxsati + yangi ekran |
| **D. Kassir uchun sodda xarita** | Bozor plani, rastalar rangi bilan (to'langan/to'lanmagan) | Eng qimmat: ruxsat qarori + xarita yuzasi |

**Tavsiyam:** dizaynda **A + B** ko'rsatilsin (arzon va darhol foyda beradi), C esa keyingi bosqich uchun alohida ekran sifatida eskiz qilinsin. Har holatda ro'yxat qatorida **raqamdan tashqari** yana bitta belgi bo'lsin (masalan «bugun to'langan / to'lanmagan»), aks holda kassir bir xil raqamlar orasida adashadi.

⛔ **Sotuvchi ismi kassir ekranida CHIZILMAYDI.** Bu qat'iy qoida: sotuvchi ismi **faqat direktorning boshqaruv panelida** ko'rinadi. Kassir rastani **raqami bilan** ishlaydi, shaxs bilan emas.

## 4. Holatlar — hammasi chizilsin

Har xato ikki qatorli: **sabab** + **nima qilish kerak**. Uchta ohang: qizil (to'siq), sariq (ogohlantirish), neytral.

| Holat | Ohang | Sabab → Yechim |
|---|---|---|
| Smena ochilmagan | sariq | «Ochiq smena yo'q» → «Avval smenani ochish kerak» |
| Rasta topilmadi | qizil | «Bunday raqamli rasta topilmadi» → «Raqamni tekshirib qayta kiriting» |
| Bozor bugun yopiq | sariq | «Bugun bozor yopiq — bugungi patta hisoblanmaydi» (to'lov baribir mumkin) |
| Tarif yo'q | qizil | «Tarif topilmadi» → summa **umuman chizilmaydi** |
| Rasta ta'mirda/yopiq | sariq | Reyestr holati eslatiladi, to'lov **bloklanmaydi** |
| Rastaga sotuvchi biriktirilmagan | sariq | Ogohlantiriladi, lekin to'lov **bloklanmaydi** |
| Server summani bermadi | qizil | Tasdiq tugmasi ishlamaydi |
| Tarmoq uzildi | qizil | «Tarmoq uzildi» + **«Qayta yuborish dublikat yaratmaydi»** + [Qayta yuborish] |
| Yuborilmoqda | — | Tugmada aylanma; takror bosish **hech nima qilmaydi** |
| Yuklanmoqda | — | Summa o'rni oldindan band (sakrash yo'q) |
| Bo'sh ro'yxat | — | «Bu smenada to'lov yozilmagan» — son ko'rsatilmaydi |
| Ruxsat yo'q | qizil | «Bu amal uchun ruxsat yo'q» + panelga qaytish havolasi |

**Ikkilamchi oqim — summani o'zgartirish:** sabab ro'yxatdan (erkin matn yo'q) + yangi summa. Bu oqim ataylab **noqulayroq** — u kundalik emas, istisno.

## 5. Ekranda ko'rinadigan ma'lumot (to'liq ro'yxat)

**Rasta bo'yicha:** raqam · bugungi patta summasi · eski qarz · jami to'lanadigan · reyestr holati (faol/ta'mirda/yopiq) · sotuvchi biriktirilganmi (ha/yo'q).
**To'lov bo'yicha:** rasta raqami · summa · turi (to'lov/bekor qilish) · usul (naqd/terminal) · vaqt · bekor qilinganmi.
**Smena bo'yicha:** boshlangan vaqt · kassir · kiritilgan naqd summa.

⛔ **Kassir ekranida chizilmaydi:** sotuvchi ismi, telefoni, fotosurati (**sotuvchi ismi faqat direktor panelida** — qat'iy qoida); kvitansiya raqami; tarif nomi.

## 6. Dizayn tizimi — landing/login bilan bitta oila

**Shrift:** Instrument Sans (400 / 600 / 700).

**Tipografiya:** sahifa sarlavhasi 26px/600 · blok sarlavhasi 18px/600 · asosiy matn 14px/1.65 · yordamchi 12px · kicker 12px/600/`0.14em`. **Pul summasi — 40px/1.1, monospace, tabular** (ekrandagi eng katta element; bu o'lcham butun ilovada faqat ikki joyda ishlatiladi).

**Ranglar — yorug':** fon `oklch(0.985 0.002 95)` · yuza `oklch(0.999 0.001 95)` · chegara `oklch(0.91 0.005 95)` · matn `oklch(0.235 0.012 95)` · ikkilamchi matn `oklch(0.45 0.015 95)` · aksent `oklch(0.56 0.19 255)`.
**Semantik:** to'langan/yashil `oklch(0.42 0.08 155)` · to'lovsiz-ogohlantirish/sariq `oklch(0.55 0.11 80)` · xato/qizil `oklch(0.58 0.21 27)`. Rang **yolg'iz signal bo'lmaydi** — har doim matn yoki ikona bilan juft.

**Ranglar — quyosh ostida:** fon sof oq, matn sof qora, chegara `oklch(0.62 0 0)`, **soya yo'q**.
**Ranglar — tungi:** login sahnasidagi indigo oila (`oklch(0.19 0.028 262)` fon, `oklch(0.24 0.03 260)` panel).

**Shakl:** input 8px · tugma/kichik karta 12px · karta/modal 16px · katta panel 20px.
**Harakat:** tez 150ms · asosiy 250ms · sekin 400ms; egri `cubic-bezier(0.22, 1, 0.36, 1)`.

**Ohang:** Apple-uslub minimalizm. Bitta ekranda **bitta** to'ldirilgan aksent tugma. Bezak ikona yo'q.

## 7. Mobil tuzilma

- Pastda ikki bandli navigatsiya (56px balandlik), yuqorida bozor nomi + tema/til/profil.
- Asosiy oqim bir ustunda; dialoglar telefonda **pastdan chiqadigan varaq**.
- Tasdiq dialoglarida asosiy tugma **o'ngda**, ochilganda fokus **bekor qilish**da (tasodifiy Enter pul yozmasin).
- 390px asosiy o'lcham; 1200px da ham buzilmasin.

## 8. Chizilmasin — bular ataylab yo'q

> ⚠️ Bu ro'yxat 9-bo'lim bilan **ziddiyatli emas**: 9-bo'limdagilar — tuzatiladigan kamchiliklar, quyidagilar esa **ongli qarorlar**.

- ❌ **Chek chop etish** — printer integratsiyasi yo'q va rejada ham yo'q. *(Sotuvchiga ko'rsatiladigan ekran tasdig'i — K-3 — bu boshqa narsa va u chizilsin.)*
- ❌ **Kvitansiya raqami** — ma'lumotda umuman yo'q
- ❌ **Smena jamlanmasi kassirda** — to'lovlar soni, yig'ilgan summa, farq: «ko'r» deklaratsiyaning mag'zi shu
- ❌ **To'lovni tahrirlash yoki o'chirish** — faqat bekor qilish yozuvi (audit izi qoladi)
- ❌ **Sotuvchi ismi/telefoni/fotosurati kassirda** — ism **faqat direktor panelida**
- ❌ **Rasm-dalil (kamera kadri) tugmasi** — kassirda kamera ruxsati yo'q
- ❌ **Orqaga sana qo'yish, qaysi kunga to'lashni TANLASH** — *(qaysi kun yopilayotganini KO'RSATISH esa kerak — K-7)*
- ❌ **Ommaviy amallar, ko'p tanlash, klaviatura yorliqlari** — tasodifiy bosish pul yozib yuboradi
- ❌ **Kassirga push-bildirishnoma**
- ❌ Foiz, «tezlashadi», «kafolatlaymiz» — hech qanday da'vo

## 9. Kamchiliklar — dizayn shularni ham hal qilsin

Quyidagilar **o'lchangan** kamchiliklar: har biri kassirning dala ishida real zarar keltiradi. Dizayn har biriga yechim ko'rsatsin. «Backend kerak» ustuni — dizayn baribir chizilsin, ijro navbati keyin belgilanadi.

### K-1 · Rastani topib bo'lmaydi
**Bugun:** raqamni yoddan yozishdan boshqa yo'l yo'q; ro'yxat/xarita yopiq; QR yo'q.
**Oqibat:** yangi kassir umuman ishlay olmaydi; rasta raqami o'chib ketgan bo'lsa ish to'xtaydi.
**Dizayn:** 3.4-bo'limdagi variantlar (prefiks ro'yxati · qator tugmalari · QR · xarita).
**Backend kerak:** yo'q (A va B uchun) · ha (QR/xarita uchun).

### K-2 · «Kimdan olganman, kimdan olmaganman?» — bilib bo'lmaydi
**Bugun:** ekranda faqat **oxirgi 5 ta** to'lov ko'rinadi; bugun to'lagan rastalar ro'yxati yo'q; qolganlari ro'yxati ham yo'q; qidiruv natijasida «to'langan» belgisi ham chiqmaydi.
**Oqibat:** kassir bir rastadan **ikki marta** olishi yoki bir qatorni **butunlay tashlab ketishi** mumkin. Bozor kattalashgani sayin xato kafolatlangan. Bu — 3.4 dan keyingi eng katta bo'shliq.
**Dizayn:** «Bugun» ko'rinishi — qatorlar bo'yicha rastalar, har birida **to'langan / to'lanmagan** holati; kassir yurgan sari ro'yxat qisqaradi. Qidiruv ro'yxatida ham shu belgi bo'lsin.
**Backend kerak:** ha (bugungi holat ro'yxati uchun yangi so'rov).

### K-3 · Sotuvchida to'lov dalili qolmaydi
**Bugun:** naqd pul beriladi — sotuvchi hech nima olmaydi: chek yo'q, kvitansiya raqami yo'q, avtomatik xabar ham **yuborilmaydi**. Sotuvchi Telegram botda o'z to'lovlarini ko'ra oladi, lekin buning uchun **o'zi kirib qarashi** kerak.
**Oqibat:** «men to'lagandim» degan nizoda kassirning so'ziga qarshi sotuvchining so'zi turadi — mahsulot aynan shu nizoni yo'q qilish uchun qurilgan.
**Dizayn:** to'lov yozilgach kassir ekranida **sotuvchiga ko'rsatiladigan tasdiq** (rasta · summa · vaqt, katta va uzoqdan o'qiladigan) — telefonni burib ko'rsatish uchun. Ixtiyoriy: QR/havola orqali sotuvchi o'z tasdig'ini oladi.
**Backend kerak:** yo'q (ekrandagi tasdiq uchun) · ha (sotuvchiga xabar uchun).

### K-4 · Internet uzilsa ish to'xtaydi
**Bugun:** tarmoq uzilsa to'lov **yozilmaydi**; «Tarmoq uzildi» + [Qayta yuborish] chiqadi. Navbat, saqlash, oflayn rejim **yo'q**.
**Oqibat:** bozorda aloqa zaif — kassir navbat oldida qotib qoladi.
**Dizayn:** aloqa yo'q holatining ochiq ko'rinishi (yuqorida doimiy tasma) + «qayta yuborish dublikat yaratmaydi» kafolatining ko'rinishi. Kelajak uchun: «kutayotgan to'lovlar» navbati qanday ko'rinishi.
**Backend kerak:** yo'q (holat ko'rinishi) · ha (navbat).

### K-5 · Bekor qilishning javobi yo'q
**Bugun:** bekor qilish muvaffaqiyatli bo'ldimi yoki xato bo'ldimi — ekranda **hech nima o'zgarmaydi**. Bu haqiqiy nuqson.
**Dizayn:** bekor qilishning tasdig'i (toast + qator holati) va xatosi chizilsin.
**Backend kerak:** yo'q.

### K-6 · Sana buzuq chiqadi
**Bugun:** `2026 M08 15 06:45` — o'zbek lotin tilida brauzerda oy nomlari yo'q.
**Dizayn:** to'g'ri mahalliy format ko'rsatilsin (masalan «15-avgust, 06:45»).
**Backend kerak:** yo'q.

### K-7 · Qaysi kun uchun to'lanayotgani ko'rinmaydi
**Bugun:** to'lov qaysi kunga tegishli ekani ma'lumotda **bor**, lekin ekranda **chizilmaydi**. Eski qarz to'langanda kassir ham, sotuvchi ham qaysi kun yopilganini ko'rmaydi.
**Dizayn:** summa yonida kun ko'rsatilsin; qarz to'langanda esa **qaysi kunlar** yopilayotgani.
**Backend kerak:** yo'q (kun allaqachon keladi) · ha (qarz taqsimoti tafsiloti uchun).

## 10. Kutilayotgan natija

1. **`Sbozor Kassir.dc.html`** — asosiy oqim: bo'sh → **rastani topish (3.4 va K-1)** → summa → to'lov turi → tasdiq → **sotuvchiga ko'rsatiladigan tasdiq (K-3)** + oxirgi to'lovlar ro'yxati (bekor qilish va uning javobi bilan — K-5).
2. **`Sbozor Kassir — Bugun.dc.html`** — K-2 ning yechimi: qatorlar bo'yicha rastalar, to'langan/to'lanmagan holati bilan. Kassirning «yo'l xaritasi».
3. **`Sbozor Smena.dc.html`** — smena ochish · ochiq smena · yopish formasi · natija (aynan 3 element).
4. Yuqoridagi **holatlar** (4-bo'lim) va **kamchiliklar** (9-bo'lim) ko'rsatib beriladigan qilib — masalan yon paneldagi tanlovlar bilan almashtirib.
5. Mobil (390px) birinchi; desktop ham buzilmasin. Uch temadan kamida **yorug'** va **quyosh ostida** variantlari ko'rsatilsin.
