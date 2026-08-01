# Karmana bozorining real ma'lumotini kiritish

> Bu yo'riqnoma ROADMAP'ning 2-fazaga qo'ygan shartini bajaradi:
> *"Karmananing real ma'lumoti aynan shu fazada kiritiladi — keyingi fazalar
> fikstura emas, haqiqat ustida sinaladi."*
>
> Yo'l **brauzersiz** ham takrorlanadi: `scripts/karmana-import.mjs`.
> Katalogda real fayl **saqlanmaydi** — sabab `.gitignore` da.

---

## 1. Nima kerak (ma'muriyatdan)

Beshta hujjat. Ularsiz kiritishni boshlash **mumkin emas** — har biri
tizimdagi aniq bir maydonga tushadi va keyin tuzatish qimmat.

| # | Nima | Kimdan | Qayerga tushadi |
|---|------|--------|-----------------|
| 1 | **Rastalar reestri**: raqam, zona, toifa, holat, izoh | Hisobchi yoki yig'uvchilar boshlig'i | `stalls` + `stall_category_periods` (5-qadam) |
| 2 | **Toifalar bo'yicha amaldagi kunlik patta narxlari** va ular **qachondan** amal qilishi | Direktor (yozma tasdiq) | `tariffs` (4-qadam) |
| 3 | **Sotuvchilar ro'yxati**: F.I.Sh., telefon, qaysi rasta | Yig'uvchilar | `vendors` + `stall_assignments` (6-qadam) |
| 4 | **Haftalik ish rejimi** va yaqin bayram/yopiq kunlar | Direktor | `market_profile.open_weekdays` + `market_calendar_exceptions` (7-qadam) |
| 5 | **Bozor rekvizitlari**: nom, manzil, STIR, bank hisob raqami va MFO | Hisobchi | `markets` + `market_profile` (1-qadam) |

⚠ 5-band **ochiq savolni yopadi**: rekvizitlar to'plami va STIR raqamlarining
soni rasmiy hujjatdan tasdiqlanmagan (tadqiqotdagi A1/A2 taxminlari, LOW
confidence). Formani ma'muriyatga **ko'rsatib**, maydonlar to'plamini
tasdiqlatib oling — undan keyin forma qotiriladi.

Uchinchi band — **shaxsiy ma'lumot**. Faylni elektron pochta yoki messenjer
orqali emas, qo'lda yoki himoyalangan kanal orqali oling va ish tugagach
`ops/data/karmana/local/` dan **o'chiring**.

---

## 2. Tartib (majburiy)

```
1. Bozor yaratish (usta 1-qadam — rekvizitlar, operating_since)
2. Zonalar
3. Toifalar
4. TARIFLAR            <-- faollashtirishdan OLDIN, boshqa iloji yo'q
5. Rastalar importi    (.xlsx)
6. Sotuvchilar importi (.xlsx)
7. Ish kunlari + bayramlar
8. FAOLLASHTIRISH
```

**Tartib ixtiyoriy emas** va sabablari strukturaviy:

- Import zona va toifani **nom bo'yicha** qidiradi. Zona yo'q bo'lsa qator
  `zone_not_found` bilan rad etiladi va D-14 (all-or-nothing) tufayli
  **butun fayl** qaytariladi;
- Tarif toifaga FK bilan bog'langan, ya'ni toifasiz tarif yozilmaydi;
- Rasta importi har rastaga boshlang'ich toifa davrini yozadi, sotuvchi
  importi esa rasta **kodi** bo'yicha biriktiradi — ya'ni 6 hech qachon 5 dan
  oldin bo'lmaydi.

### ⚠ Tariflar faollashtirishdan OLDIN kiritilishi shart

Bozor **qoralama** (`is_active = false`) bo'lgan paytda `POST /api/v1/tariffs`
boshlang'ich narxni aynan `operating_since` sanasiga qabul qiladi — bu
02-09 da ochilgan **istisno** va u Karmananing yillar davomida amal qilib
kelgan narxlarini tizimga kiritish uchun mavjud.

Bozor faollashtirilgandan keyin bu yo'l **butunlay yopiladi**:

- yangi narx faqat **kelajakdagi** sanadan boshlanadi;
- o'tgan qator umuman o'zgartirilmaydi (D-06/D-07 — voris modeli);
- ya'ni *"avval faollashtiraylik, tariflarni keyin kiritamiz"* — **ishlamaydi**
  va bozorni **qayta yaratishga** majbur qiladi.

Ikkinchi qatlam himoya ham bor: tarifsiz bozorni faollashtirib bo'lmaydi —
`POST /markets/{id}/activate` `409 market_incomplete` va `blocking[]` ichida
`tariff_missing_for_category` beradi. Lekin bu himoyaga **tayanmang**: u
faqat toifada **umuman** tarif yo'qligini ushlaydi, "noto'g'ri sanaga
yozilgan tarif" ni emas.

---

## 3. Ustun tartibi

**Rasta fayli** (`?kind=stalls`):

| A | B | C | D | E |
|---|---|---|---|---|
| kod | zona | toifa | holat | izoh |

**Sotuvchi fayli** (`?kind=vendors`):

| A | B | C | D |
|---|---|---|---|
| F.I.Sh. | telefon | rasta kodi | boshlanish sanasi |

⚠ Parser ustunlarni **pozitsiya bo'yicha** o'qiydi — sarlavha matni
ahamiyatsiz, **tartib** ahamiyatli. Shu sababli:

- shablonni rus yoki o'zbek-kirill tilida yuklab olsangiz ham import bir xil
  ishlaydi (sarlavhalar tarjima qilinadi, tartib esa o'zgarmaydi);
- ustunlarni joyini almashtirsangiz fayl **jimgina noto'g'ri yozilmaydi** —
  zona/toifa nomlari topilmaydi va qator 422 bilan rad etiladi.

Qo'shimcha eslatmalar:

- **Birinchi qator — sarlavha.** Xato xabarlaridagi qator raqami Excel'dagi
  raqam bilan aynan bir xil (ikkinchi ma'lumot qatori = `3-qator`);
- **Holat** ustuni bo'sh bo'lsa `active` qabul qilinadi; mumkin qiymatlar
  shablonning yashirin `Ma'lumotnoma` varag'ida ochiluvchi ro'yxat sifatida;
- **Boshlanish sanasi** bo'sh bo'lsa `operating_since` qo'yiladi (ya'ni
  "sotuvchi bozor ochilganidan beri shu yerda"). Shakl: `2026-08-01` yoki
  `01.08.2026`;
- **Telefon** ixtiyoriy shaklda yozilishi mumkin (`90 991 00 03`,
  `+998909910003`) — server uni E.164 ga keltiradi;
- Rasta kodi bo'sh sotuvchi reestrga **rastasiz** tushadi va bu xato emas
  (D-11).

---

## 4. Chegaralar

| Chegara | Qiymat | Oshib ketsa |
|---------|--------|-------------|
| Fayl hajmi | **5 MB** | `422 file_too_large` |
| Qatorlar soni | **5 000** | `422 file_too_complex` |
| Ustunlar soni | **32** | `422 file_too_complex` |
| Varaqlar soni | **8** | `422 file_too_complex` |
| ZIP ichidagi elementlar | 200 | `422 file_too_complex` |
| Ochilgan hajm | 50 MB | `422 file_too_complex` |

Karmana uchun 300–1000 rasta kutilmoqda, ya'ni chegaralardan besh barobar
uzoq. Chegaralar muhit o'zgaruvchilaridan sozlanadi (`IMPORT_MAX_ROWS` va
h.k.) — deploy qayta qurilmaydi.

Faqat `.xlsx` qabul qilinadi. `.csv` va `.ods` `422 unsupported_file_type`
bilan rad etiladi (`.xlsx` deb **nomlangan** boshqa fayl ham).

---

## 5. Nima noto'g'ri bo'lishi mumkin

Server **hech qanday qatorni** yozmaydi, agar bitta xato bo'lsa ham
(D-14, all-or-nothing). Javob `422` bo'ladi va unda ikki narsa keladi:
kod bo'yicha **guruhlangan sanoq** (`error_counts`) hamda har bir qator
uchun alohida yozuv. Skript ikkalasini ham konsolga chiqaradi.

| Kod | Ma'nosi | Tuzatish |
|-----|---------|----------|
| `empty_code` | Rasta raqami katagi bo'sh | Qatorni to'ldiring yoki o'chiring |
| `duplicate_code_in_file` | Bir xil rasta kodi **faylda** ikki marta (sotuvchi faylida: bitta rastaga ikki sotuvchi) | Xabarda **ikkala** qator raqami bor — ortiqchasini o'chiring |
| `row_too_short` | Majburiy ustun bo'sh (zona, toifa, F.I.Sh., telefon) | Xabarda ustun nomi ko'rsatilgan |
| `zone_not_found` | Fayldagi zona nomi bozorda yo'q | Avval zonani qo'shing (2-qadam) yoki fayldagi nomni to'g'rilang |
| `category_not_found` | Fayldagi toifa nomi bozorda yo'q | Avval toifani qo'shing (3-qadam) yoki fayldagi nomni to'g'rilang |
| `invalid_status` | Holat ustunidagi so'z tanilmadi | Ochiluvchi ro'yxatdan tanlang (`active` / `repair` / `closed`) |
| `invalid_phone` | Telefon raqami O'zbekiston formatiga tushmadi | `+998XXXXXXXXX` yoki `90 123 45 67` shaklida yozing |
| `duplicate_phone_in_file` | Bir xil telefon faylda ikki marta | Xabarda ikkala qator raqami bor |
| `stall_not_found` | Sotuvchi faylidagi rasta kodi bozorda yo'q | Avval rastalarni import qiling (5-qadam) yoki kodni to'g'rilang |
| `invalid_date` | Boshlanish sanasi o'qilmadi | `2026-08-01` yoki `01.08.2026`; bo'sh qoldirsangiz `operating_since` qo'yiladi |

Nomlar **registrga sezgir emas** (`Sabzavot` = `SABZAVOT`), lekin
**noaniqlik** xato bo'lib qoladi: bozorda `Sabzavot` ham, `SABZAVOT` ham
mavjud bo'lsa taxmin qilinmaydi va qator `zone_not_found` oladi.

Yana ikkita javob mumkin:

- **`409 import_conflict`** — faylda **chetlangan** (yopilgan) rastaning
  eski raqami bor. Raqam qayta ishlatilmaydi (D-02): "12-rasta" hisobotda
  yillar davomida bitta jismoniy joyni anglatadi. Fayldagi raqamni
  o'zgartiring;
- **`409 market_incomplete`** — bozorning profil qatori yo'q. Bu bozor usta
  orqali yaratilmaganini bildiradi.

---

## 6. Qayta yuklash xavfsiz

D-15: **mavjud kodlar o'tkazib yuboriladi, hech narsa o'zgartirilmaydi.**

- Rasta importi mavjud **kodni** o'tkazib yuboradi;
- Sotuvchi importi mavjud **telefonni** o'tkazib yuboradi (biriktirish ham
  yozilmaydi — aks holda har qayta import yangi davr qo'shib, qoplanmaslik
  konstraytiga urilardi);
- Javobda `inserted` va `skipped` sonlari keladi.

Ya'ni faylni tuzatib **butunlay** qayta yuklash mumkin: yangi qatorlar
qo'shiladi, eskilari **tegilmaydi**. Bu import xatolarini tuzatishning
normal yo'li.

⚠ Import mavjud qatorni **tahrirlamaydi**. Noto'g'ri yozilgan rastaning
zonasi yoki toifasi faylni qayta yuklash bilan **tuzalmaydi** — uni
reestr ekranidan tahrirlaysiz.

---

## 7. Tekshiruv ro'yxati (import tugagach)

Har bir raqamni ma'muriyatning **o'z reestri** bilan solishtiring va
farqlarni yozib qo'ying — 8-fazadagi baza solishtiruvi shunga tayanadi
(T-02-132).

| Nima solishtiriladi | Qayerdan olinadi |
|---------------------|------------------|
| Umumiy rasta soni | `GET /api/v1/stalls?limit=1` → sahifani oxirigacha varaqlash **yoki** `/uz/map` sahifasidagi kataklar soni |
| Zona bo'yicha rasta soni | `GET /api/v1/zones` → har qatorda `stall_count`; xaritada har zona bloki |
| Holat bo'yicha taqsimot | `GET /api/v1/stalls?status=active` / `?status=repair` / `?status=closed` |
| Toifa bo'yicha rasta soni | `GET /api/v1/categories` → har qatorda `stall_count` |
| Sotuvchi soni | `GET /api/v1/vendors` |
| Biriktirilgan rasta soni | Rastalar ro'yxatida `vendor_name` bo'sh bo'lmagan qatorlar; xaritada `has_vendor` |
| Toifalar bo'yicha amaldagi narx | `GET /api/v1/categories` → `current_tariff_soum` (`null` bo'lsa — tarif kiritilmagan) |

Farq topilsa **avval qaysi tomon to'g'ri ekanini** aniqlang: qog'oz reestr
ham eskirgan bo'lishi mumkin. Har bir farq uchun yozing: rasta raqami,
qog'ozda nima, tizimda nima, kim tasdiqladi.

---

## 8. `operating_since` haqida ogohlantirish

`operating_since` — bozorning **ish boshlagan sanasi**. U 1-qadamda bir
marta yoziladi va keyin:

- **barcha** boshlang'ich tarif qatorlarining `valid_from` i bo'ladi;
- **barcha** boshlang'ich toifa davrlarining `valid_from` i bo'ladi;
- import qilingan sotuvchilarning biriktirish davri shu sanadan ochiladi
  (sana ustuni bo'sh bo'lganda).

⚠ Qoralama bozorda `POST /api/v1/tariffs` boshlang'ich narxni **aynan shu**
sanaga qabul qiladi. `operating_since ± 1 kun` ham **rad etiladi** — ya'ni
"taxminan" yozib bo'lmaydi.

Noto'g'ri qo'yilsa nima bo'ladi:

- sana **haddan tashqari kech** bo'lsa — 6-faza undan **oldingi** har qanday
  kunni **tarifsiz** deb topadi. Tarifsiz kun `0 so'm` emas, **anomaliya**
  (D-08 fail-closed): o'sha kunlarning hisobi umuman yozilmaydi va
  "band, lekin to'lovsiz" hisoboti o'sha davrni ko'rmaydi;
- sana **haddan tashqari erta** bo'lsa — bozor ishlamagan kunlar uchun ham
  tarif amal qilgan bo'lib ko'rinadi.

Tuzatishning yagona yo'li — bozorni **qayta yaratish** (qoralama holatida
`DELETE /api/v1/markets/{id}` ishlaydi; faollashtirilgan bozor
o'chirilmaydi). Shuning uchun bu sanani **direktordan yozma** tasdiqlab
oling.

---

## Skript bilan ishlash

Muhit o'zgaruvchilari (**parol va telefon argv'da qabul qilinmaydi** —
ular protsess ro'yxatida ko'rinardi):

```sh
export API_BASE_URL=http://localhost:8000
export SBOZOR_PHONE=+998901234567
export SBOZOR_PASSWORD='...'
export SBOZOR_MARKET_ID=<qoralama bozorning UUID'i>
```

```sh
# 1) Shablonni olish (zona va toifa ro'yxati ichiga solingan holda)
npm run karmana:template -- --kind=stalls --out=./ops/data/karmana/local/stalls.xlsx

# 2) To'ldirilgan faylni yuklash
npm run karmana:upload -- --kind=stalls --file=./ops/data/karmana/local/stalls.xlsx

# 3) Sotuvchilar uchun ham xuddi shunday
npm run karmana:template -- --kind=vendors --out=./ops/data/karmana/local/vendors.xlsx
npm run karmana:upload -- --kind=vendors --file=./ops/data/karmana/local/vendors.xlsx
```

Xato bo'lsa skript avval **guruhlangan sanoqni**, so'ng birinchi 50 xatoni
`{qator}-qator: {sabab}` shaklida chiqaradi va **exit kodi 1** bo'ladi —
ya'ni uni CI yoki `&&` zanjirida ishlatish mumkin.

⚠ Importni **ish vaqtidan tashqarida** bajaring: butun fayl bitta
tranzaksiyada yoziladi (T-02-133).
