# SBOZOR — Nazoratchi ekranlari uchun UI brief

> **Maqsad:** nazoratchi kamera kadriga qarab bitta savolga javob beradi — *«bu rasta band edimi?»*. Uning javoblari AI ning aniqligini o'lchaydigan **etalon** bo'ladi. Ya'ni bu ekran ma'lumot kiritish emas, **o'lchov asbobi**.
> **Sana:** 2026-08-18 · **Oila:** `Sbozor Landing v2`, `Sbozor Login`, `Sbozor Kassir` bilan bitta mahsulot.
> **Design system:** «Sbozor.uz Design System» — chizishda faqat o'sha komponentlar.
>
> ⚠️ Quyidagining hammasi kodda tekshirilgan. 8-bo'limda «chizilmasin» ro'yxati bor: undagilar tizimda **umuman yo'q** yoki **ataylab yo'q**.

---

## 1. ⚠️ Eng muhim tuzatish: nazoratchi nima QILMAYDI

Nomi «nazoratchi» bo'lgani uchun uni «to'lamaganlarni tekshiruvchi» deb tasavvur qilish oson. **Bu noto'g'ri.**

- U **to'lov holatini ko'rmaydi** — patta, summa, qarz: hech biri uning ekraniga kelmaydi.
- U **AI qарорини ko'rmaydi** — «ishonch darajasi», «tizim nima dedi» kabi maydonlar ma'lumotda **umuman yo'q** va ular kelib qolsa dastur xato beradi (schema qat'iy).
- U **sotuvchi shaxsini ko'rmaydi** — faqat «rastaga sotuvchi biriktirilgan» degan ha/yo'q belgisi (u ham bitta navbatda).
- U **o'z aniqligini ko'rmaydi** — bu ataylab: o'z ballini ko'rgan odam ballni yaxshilashga moslab javob bera boshlaydi va o'lchov buziladi.

**Uning butun ishi:** kadrga qarash → uchta javobdan birini bosish. Javob **o'zgartirilmaydi**.

## 2. Ikkita navbat — va ular bir xil emas

| | **Ko'rmasdan tekshirish** (blind) | **Noaniq navbati** (uncertain) |
|---|---|---|
| Nima uchun | AI aniqligini **o'lchash** | AI shubhalangan kadrlarni **hal qilish** |
| Javobdan keyin | Kadr ekranda **qotib qoladi**, natija ko'rsatiladi, «Keyingisi» tugmasi bilan davom etiladi | Natija **1,5 soniya** ko'rinadi va o'zi yo'qoladi, keyingi kadr o'zi keladi |
| Bir kadrga | **2 ta ta'sir** (javob + Keyingisi) | **1 ta ta'sir** (javob) |
| Kattalashtirish | Javobdan keyin **yo'qoladi** | Bor |
| Alohida banner | Bor — «javob qaytarilmaydi» ogohlantirishi doim ko'rinadi | Yo'q |
| Sotuvchi belgisi | **Yo'q** | Bor |

⛔ Ikkalasi ham kunlik **byudjet** bilan cheklangan. Byudjet tugasa — «yana ko'raman» tugmasi **yo'q** (ataylab: ko'p ko'rish o'lchovni buzadi).

## 3. Ekranlar

### 3.1 Bosh ekran — «Ko'rib chiqish»

Sarlavha, sana va hafta kuni. Ostida **ikkita karta**:

**Birinchi — «Ko'rmasdan tekshirish».** Tavsif, `Bugun: 4 / 12` hisoblagichi, qulf ikonasi bilan «javob qaytarilmaydi» eslatmasi, «Boshlash» tugmasi.
**Ikkinchi — «Noaniq navbati».** Tavsif, hisoblagich, «Davom etish» tugmasi.

⛔ Blind kartasi **birinchi** turadi — bu qaror: ikkinchi bo'lsa u kun oxiriga, ya'ni charchagan paytga qolardi.
⛔ Byudjet tugagan karta **yo'qolmaydi** — yashil «Bajarildi» yorlig'i bilan qoladi. Yo'qolsa, «bunday ish yo'q edi» degan yolg'on chiqadi.
⛔ Hisoblagich **progress-bar bo'lmaydi** — faqat son.

### 3.2 Sessiya ekrani (ikkala navbat uchun bitta shakl)

Yuqorida: sarlavha, kunlik hisoblagich, «Chiqish». Blind'da ustiga yopishib turadigan **banner** — ogohlantirish rangida emas, neytral; yopib bo'lmaydi.

Markazda **dalil kadri** — 16:9, qorong'i fonda, zona konturi ustiga chizilgan. Ostida:
- `Rasta A-12 · Sabzavot zonasi`
- `18-avgust · 09:30 · Kanal 3`
- (faqat noaniq navbatda) «Rastaga sotuvchi biriktirilgan»

Pastda **savol va uchta javob**: `Band` · `Bo'sh` · `Aniq ayta olmayman`. Har birida raqam belgisi (1/2/3) — klaviaturadan ham javob berish mumkin. Ostida qisqa izoh: «Tugmalar: 1 — band, 2 — bo'sh, 3 — aniq emas».

**Javobdan keyin:** «Sizning javobingiz» / «Tizim javobi» / «Mos keldi» yoki «Farq qildi». Blind'da qulf ikonasi va «Javob qulflandi», so'ng yagona oldinga tugma — «Keyingisi».

### 3.3 Boshqaruv paneli

Nazoratchi uchun **bitta** ko'rsatkich: «Ko'rib chiqish navbati» — bu son, pul emas.

## 4. Holatlar — hammasi chizilsin

| Holat | Nima ko'rinadi |
|---|---|
| Yuklanmoqda | Kadr o'rni oldindan band (16:9) — sakrash yo'q |
| **Rasm ochilmadi** | Kadr o'rnida «Rasm ochilmadi — javob bera olmaysiz» + «Qayta urinish». **Uchala javob tugmasi ham bloklangan** |
| Navbat bo'sh (noaniq) | «Hozircha noaniq kadr yo'q» — amal tugmasi **yo'q** |
| Blind namunasi tugadi | «Bugungi tekshiruv tugadi 12/12» + «Ko'rib chiqishga qaytish» |
| Kunlik byudjet tugadi | «Bugungi byudjet tugadi» — «yana ko'raman» tugmasi **yo'q** |
| Namuna hali olinmagan | «Bugungi namuna hali tayyor emas» — «hozir ol» tugmasi **yo'q** |
| Javob allaqachon berilgan (blind) | Sariq blok: sabab + nima qilish + «Keyingisi». **Qayta urinish tugmasi yo'q** — u hech qachon o'tmaydi |
| Xato | «Ma'lumot yuklanmadi» + «Qayta urinish» |
| Ruxsat yo'q | «Bu amal uchun ruxsat yo'q» + panelga qaytish |
| Chiqish tasdig'i | Javobsiz kadr navbatda qoladi (noaniq) / hisobotda «javobsiz» bo'lib qoladi (blind) — **matn navbatga qarab boshqacha** |

## 5. Ekranda ko'rinadigan ma'lumot (to'liq ro'yxat)

Rasta kodi · zona nomi · sana · kadr vaqti · kamera kanali raqami · dalil rasmi · zona konturi · (noaniq navbatda) sotuvchi biriktirilganmi · kunlik hisoblagich · javobdan keyin: sizning javobingiz, tizim javobi, mos keldimi.

⛔ **Yo'q va bo'lmaydi:** AI ishonch darajasi, AI qarori, model versiyasi, to'lov/patta/summa, sotuvchi ismi yoki telefoni, nazoratchining o'z aniqlik ko'rsatkichi.

## 6. Dizayn tizimi

`Sbozor Kassir` briefidagi bilan **aynan bir xil**: Instrument Sans; sarlavha 26/600, blok 18/600, matn 14/1.65, yordamchi 12; aksent `oklch(0.56 0.19 255)`; yashil/sariq/qizil semantik ranglar; radius 8/12/16/20; uch tema (yorug' · quyosh ostida · tungi); harakat 150/250/400ms, faqat `transform`/`opacity`.

**Bu ekranning o'ziga xosligi:** kadr — sahifadagi eng katta va eng muhim element. Undan boshqa hamma narsa jim bo'lishi kerak. Kadr foni quyuq (rasm chetlari aniq ko'rinsin), zona konturi aksent rangda.

**Bloklangan tugma «o'chirilgan» emas** — ko'rinadi, fokus oladi va nega bloklanganini aytadi.

## 7. Mobil

Javob tugmalari telefonda **ustma-ust** (har biri to'liq kenglikda, ≥44px), kengroq ekranda yonma-yon. Pastda ikki bandli navigatsiya: «Boshqaruv paneli» va «Ko'rib chiqish». 390px asosiy.

## 8. Chizilmasin — ataylab yo'q

- ❌ **Ommaviy tasdiqlash, ko'p tanlash, «hammasini qabul qilish»** — bitta kadr, bitta javob. Klaviaturada tugmani bosib turish ham ishlamaydi (bu ommaviy tasdiqlashning klaviatura shakli)
- ❌ **Javobni o'zgartirish, orqaga qaytish, «qayta ko'rish»** — javob qulflanadi
- ❌ **Tashlab ketish / keyinroq / o'tkazib yuborish** — yagona «bilmayman» yo'li «Aniq ayta olmayman»
- ❌ **Filtr, saralash, qidiruv, navbatni oldindan ko'rish** — keyingi kadrni server tanlaydi
- ❌ **Nazoratchining aniqlik ballari, statistikasi, tarixi** — o'lchov butunligi uchun
- ❌ **Kadrni yuklab olish, ulashish, nusxalash**
- ❌ **Kadr ustiga chizish, belgilash**
- ❌ Byudjetdan keyin davom etish yo'li
- ❌ Oflayn rejim (yo'q — va'da berilmasin)

## 9. Kamchiliklar — dizayn shularni ham hal qilsin

### N-1 · «Kattalashtirish» aslida kattalashtirmaydi
**Bugun:** tugma bosilsa **480px** kenglikdagi oynada **ayni rasm** ochiladi. Surish yo'q, masshtab yo'q, to'liq ekran yo'q.
**Oqibat:** nazoratchining butun ishi rasmga qarab qaror qilish. Asosiy asbob ishlamayapti — «band» va «bo'sh» orasidagi farq ko'pincha mayda detalda.
**Dizayn:** haqiqiy ko'rish rejimi — to'liq ekran, surish va masshtab, zona konturi saqlangan holda.

### N-2 · Buzuq kamerani aytadigan joy yo'q
**Bugun:** nazoratchi — kamera qiyshayganini, ob'ektiv iflosligini yoki zona noto'g'ri chizilganini **birinchi ko'radigan odam**. Lekin uning uchtagina javobi bor va bularning hech biri buni ayta olmaydi. «Aniq ayta olmayman» hammasini yutib yuboradi va sabab yo'qoladi.
**Dizayn:** javobdan ALOHIDA, kichik «kadr bilan muammo» yo'li — sabab ro'yxatdan (kamera qiyshaygan · ob'ektiv iflos · zona noto'g'ri · kadr qorong'i). Bu javob emas, **signal**.

### N-3 · Kanal raqami odamga hech nima demaydi
**Bugun:** `Kanal 3` yoziladi. Kamera nomi ma'lumotda **bor**, lekin ekranga chiqarilmaydi.
**Dizayn:** kamera nomi ko'rsatilsin (kanal raqami yordamchi bo'lib qolsin).

### N-4 · Sessiya yakuni yo'q
**Bugun:** oxirgi kadrdan keyin bo'sh holat chiqadi, xolos.
**Dizayn:** qisqa yakun — bugun nechta kadr ko'rildi. ⛔ Aniqlik foizi **YO'Q** (o'lchov butunligi).

### N-5 · Noaniq navbatda ziddiyat holati chizilmagan
**Bugun:** kadr allaqachon javob berilgan bo'lsa — blind'da tushuntiriladi, noaniq navbatda **hech nima ko'rsatilmaydi** (matnlar tarjima qilingan, lekin hech qayerda ishlatilmaydi).
**Dizayn:** ikkala navbatda ham bir xil tushuntirish.

## 10. Kutilayotgan natija

1. **`Sbozor Nazoratchi.dc.html`** — sessiya ekrani: kadr, ma'lumot qatorlari, uchta javob, javobdan keyingi natija. **Ikkala navbat** ham (blind va noaniq) almashtirib ko'rsatiladigan bo'lsin.
2. **`Sbozor Nazoratchi — Bosh.dc.html`** — ikkita navbat kartasi bo'lgan bosh ekran, byudjet tugagan holati bilan.
3. 4-bo'limdagi **holatlar** va 9-bo'limdagi **kamchiliklar** yechimi ko'rsatib beriladigan boshqaruv bilan.
4. Mobil 390px asosiy; uch temadan kamida yorug' va quyosh ostida.
