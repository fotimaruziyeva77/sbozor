# Phase 2: Bozor domeni va "Yangi bozor" ustasi — Research

**Researched:** 2026-07-30
**Domain:** Multi-tenant domen modeli — vaqtga bog'liq (temporal) tarif/biriktirish tarixi, ish-kunlari kalendari, ommaviy Excel import, ko'p qadamli usta (wizard) va sxematik plan-xarita
**Confidence:** HIGH (kritik DB xulq-atvorlari jonli `postgres:18.4-trixie` konteynerida empirik o'lchandi; SQLAlchemy 2.0.51 + asyncpg 0.31.0 + Alembic 1.18.5 real ulanishda tekshirildi; 1-faza kodi fayl-fayl o'qildi)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rasta identifikatsiyasi va tuzilishi**
- **D-01:** Rasta raqami — **bozor bo'yicha yagona** (butun bozorda takrorlanmaydi: 1, 2, 3 … 500). Zona tanlash shart emas: kassir raqamni yozadi va rasta topiladi. Bu 6-fazadagi "≤3 bosish" mezonining poydevori. Karmanada rastalar jismonan shunday belgilangan.
- **D-02:** Raqam **tahrirlanadi, lekin qayta ishlatilmaydi**. Admin xato kiritilgan yoki bozor qayta raqamlangan holatda raqamni tuzata oladi (har o'zgarish auditda). Yopilgan rastaning raqami YANGI rastaga berilmaydi — tizim rad etadi. Sabab: hisobotda "12-rasta" yillar davomida bitta jismoniy joyni anglashi kerak, aks holda qarz va dalil-rasm chalkashadi.
- **D-03:** Zona — **yassi ro'yxat, har rastada majburiy**. Ierarxiya (sektor→qator) qurilmaydi. Har rasta aynan bitta zonaga tegishli. Xarita har zonani alohida grid blok qilib chizadi; import faylida bitta ustun.
- **D-04:** Mahsulot toifasi **rastaning atributi** (sotuvchiniki emas) va **o'zgartirilishi mumkin**. Sotuvchi almashsa toifa qoladi. Toifa o'zgarishi sanadan kuchga kiradi — o'tmishdagi hisob buzilmaydi (tarif tarixi bilan bir xil mexanizm). Sabab: toifa sotuvchiga bog'lansa, sotuvchisiz band rastaning tarifi noaniq bo'lib qoladi va "ro'yxatga olinmagan savdo" anomaliyasini hisoblab bo'lmaydi.

**Tarif o'lchovi va tarixi**
- **D-05:** Kunlik patta summasi **faqat mahsulot toifasi bo'yicha** belgilanadi. Zona, rasta o'lchami/maydoni, hafta kuni yoki mavsum bo'yicha farq YO'Q. Tarif kaliti: `(market_id, category_id, valid_from)`.
- **D-06:** Tarif tarixi — **amal qilish sanasi bilan qatorlar**. Yangi narx kiritilganda YANGI qator qo'shiladi, eskisi o'zgarmaydi. Hisob yozilayotganda o'sha `business_date` ga amal qilgan qator tanlanadi. Kelajakdagi sanaga oldindan narx kiritish mumkin ("1-sentabrdan 12 000"). MARKET-03 shu bilan bajariladi.
- **D-07:** Tarif tahriri — **kelajakdagi qatorni tahrirlash/o'chirish mumkin, sanasi o'tgani qulflanadi**. O'tmishdagi narx faqat yangi sanadan yangi qator bilan "tuzatiladi". Har amal auditda (`tariffs` allaqachon DB-trigger ostida — 1-faza D-10).
- **D-08:** **Tarif topilmasa — fail-closed**: kunlik hisob YOZILMAYDI, taxminiy summa ishlatilmaydi. Rasta "tarifsiz band rasta" anomaliyasi sifatida kunlik hisobotga chiqadi va adminga alert boradi. Sabab: noto'g'ri summali patta sotuvchi bilan nizoni keltirib chiqaradi — mahsulot aynan buni oldini olish uchun bor. Loyihaning `NULLIF` fail-closed qoidasiga mos.

**Sotuvchi biriktirish va qarz egaligi**
- **D-09:** Munosabat — **bir vaqtda 1 rasta = 1 sotuvchi; 1 sotuvchi = ko'p rasta**. Model: `stall_assignments(stall_id, vendor_id, from_date, to_date)`, bir rasta uchun davrlar kesishmaydi. Qarz sotuvchida jamlanadi, har rasta bo'yicha ajratib ko'rsatiladi.
- **D-10:** Rasta almashinuvida **qarz eski sotuvchida qoladi** — rasta bilan o'tmaydi. Har kunlik hisob o'sha KUNI biriktirilgan sotuvchiga yoziladi va o'shanda qoladi (10-sanada almashsa: 1–9 kunlar eskisiniki, 10-kundan yangisiniki). Yangi sotuvchi hech qachon begona qarzni meros qilib olmaydi. Amalda: `daily_charges` yozuvi `vendor_id` ni o'zida saqlaydi → qo'shimcha mantiq kerak emas.
- **D-11:** **Sotuvchisi biriktirilmagan band rasta — hisob emas, anomaliya**. ROADMAP 6-faza 3-mezoni bilan bir xil: "ro'yxatga olinmagan savdo" sifatida hisobotga chiqadi. "Noma'lum sotuvchi" texnik hisobi yaratilmaydi.
- **D-12:** Sotuvchi telefoni — **majburiy va bozor ichida unique** (E.164, `phonenumbers` bilan normalizatsiya — 1-fazadan tayyor). Sabab: 7-fazada sotuvchi botga aynan telefon raqami orqali ulanadi (BOT-03) va kvitansiya shu kanal bilan boradi.

**Real ma'lumot kiritish (~300–1000 rasta)**
- **D-13:** **Excel/CSV import + usta qadamlari**. Usta qo'lda oladi: rekvizit → zona → toifa → tarif (bular kam — 5–15 ta). Rastalar va sotuvchilar **Excel fayldan ommaviy yuklanadi**. Shablon fayl yuklab olinadi. `XlsxWriter` allaqachon stekda (1-fazadan).
- **D-14:** Import xatosi — **all-or-nothing**. Butun fayl bitta tranzaksiya: bitta xato bo'lsa ham hech narsa yozilmaydi. Admin barcha xatolarni **qator raqami va sababi bilan** ko'radi ("14-qator: 'Sabzavot' zonasi topilmadi", "88-qator: 12 raqami takrorlangan"), faylni tuzatib qayta yuklaydi. Yarim kiritilgan holat hech qachon yuzaga kelmaydi.
- **D-15:** Qayta import — **faqat yangi qo'shiladi, mavjudi tegilmaydi**. Rasta kodi bo'yicha solishtiriladi: faylda bor + bazada yo'q → qo'shiladi; ikkalasida bor → o'tkazib yuboriladi (mavjud yozuv, sotuvchisi va tarixi tegilmaydi). Eski faylni tasodifan qayta yuklash hech narsani buzmaydi. Upsert ham, "faylda yo'qlarni yopish" ham YO'Q. Tahrirlash reestr UI orqali qilinadi — u yerda har o'zgarish auditda.
- **D-16:** **Usta kamerasiz yakunlanadi** va bozor "ishlashga tayyor" holatiga o'tadi. Kamera / kamera-zona / snapshot qadamlari keyinroq qo'shiladigan **ixtiyoriy bo'lim** bo'lib turadi (3–5 fazalarda ulanadi). Doimiy ogohlantirish banneri qo'yilmaydi. Oqibat (ataylab): 6-faza (billing/kassir) NVR'siz to'liq quriladi va sinaladi — AI-bandlik o'rniga qo'lda kiritish bilan.

**Ish kunlari (MARKET-05)**
- **D-17:** **Haftalik jadval + istisno sanalar**. Bozorning doimiy rejimi bir marta belgilanadi (masalan dushanba — dam olish), ustiga alohida sanalar qo'shiladi: bayram ("1-yanvar — yopiq") yoki istisno ish kuni ("bu dushanba ishlaymiz"). Har kunni qo'lda kiritish shart emas, lekin har qanday holat ifodalanadi.
- **D-18:** Yopiq kun — **faqat bozor darajasida**. Zona yoki rasta darajasidagi alohida jadval YO'Q. 6-fazadagi kunlik job bitta tekshiruv qiladi: "bugun bu bozor ishlaydimi?". Vaqtincha yopiq rasta ehtiyoji `status = ta'mirda/yopiq` bilan allaqachon qoplanadi.

**Plan-xarita (MARKET-06)**
- **D-19:** Grid joylashuvi — **avtomatik**: har zona alohida blok, ichida rastalar kod (raqam) tartibida qatorlarga teriladi. Qo'shimcha ma'lumot kiritish shart emas — import qilinishi bilan xarita darhol ishlaydi. Drag-drop muharrir va koordinata ustunlari YO'Q (v2). ROADMAP xaritani ataylab "sxematik" deb belgilagan.
- **D-20:** 2-fazada xaritada **faqat rasta holati rangi**: faol (neytral), ta'mirda (kulrang), yopiq (o'chgan), ustiga sotuvchisi bor/yo'q farqi. Toifa rangi ishlatilmaydi. 6–7 fazalarda shu grid'ga to'lov/qarz/nomuvofiqlik ranglari qo'shiladi — komponent qayta yozilmaydi.

### Claude's Discretion

- Sxema detallari: jadval nomlari, ustunlar, indekslar, FK strategiyasi. Har yangi tenant jadvali `market_id` + RLS ENABLE+FORCE + policy talabini bajarishi SHART — 1-fazadagi `tests/tenancy/test_meta.py` meta-testi buni avtomatik qulflaydi va yangi jadval qo'shilganda test qizaradi.
- Qaysi jadvallar `AUDITED_TABLES` / `FINANCIAL_TABLES` reyestrlariga qo'shiladi (`packages/sbozor-core/sbozor_core/schema_contract.py`). `tariffs` va `stall_assignments` 1-faza D-10 bo'yicha DB-trigger auditi ostida bo'lishi kerak.
- API shakli: endpoint yo'llari, keyset paginatsiya, filtr parametrlari — 1-fazadagi `GET /api/v1/audit` va `GET /api/v1/users` naqshlariga mos.
- Usta qadamlarining UI oqimi, qoralama (draft) saqlash mexanikasi, qadamlar orasida orqaga qaytish.
- Excel shablon fayl tuzilishi, ustun nomlari va validatsiya xabarlarining aniq matni.
- Bozor rekvizitlari to'plami (nom, manzil, STIR, bank ma'lumotlari va h.k.) — oqilona minimal to'plam.
- Rasta holatlari o'rtasidagi o'tish qoidalari (faol ↔ ta'mirda ↔ yopiq) va yopiq rastaga hisob yozilmasligi.
- Xarita komponentining texnik amalga oshirilishi (SVG/grid vs react-konva) — 300–1000 rasta uchun ishlashi kerak; ROADMAP react-konva'ga o'tishni "real rasta sonidan oldin" tavsiya qilgan.
- Kim qaysi amalni qila oladi (bozor admini vs platforma admini) — 1-fazadagi RBAC matritsasi (`services/core-api/app/security/rbac.py`) kengaytiriladi; D-07 bo'yicha direktor faqat ko'radi.

### Deferred Ideas (OUT OF SCOPE)

- **Toifa+zona yoki rasta o'lchamiga bog'liq tarif** — hozir faqat toifa (D-05). Agar ma'muriyat keyinchalik zonaga qarab narx belgilamoqchi bo'lsa, `tariffs` kalitiga ustun qo'shish kerak bo'ladi (migratsiya bilan).
- **Bir rastada bir necha sotuvchi (smena/sherik)** — D-09 rad etdi. Agar haqiqatda uchrasa, `stall_assignments` ga vaqt oralig'i (soat) qo'shish yoki ulush modeli kerak bo'ladi. v2.
- **Rasta qarzining rasta bilan o'tishi** — D-10 rad etdi. Agar bozor amaliyoti boshqacha bo'lsa (Phase 0 ning "rasta almashinuvi" savoli), qayta ko'riladi.
- **Xaritada qo'lda joylashtirish (drag-drop) va jismoniy koordinatalar** — D-19 rad etdi, v2. ROADMAP ham xaritani sxematik deb belgilagan.
- **Ko'p tilli DB kontenti** (zona/toifa nomlari 3 tilda) — 1-faza D-16 bo'yicha qurilmaydi.
- **Import orqali mavjud yozuvlarni yangilash (upsert) yoki to'liq sinxronizatsiya** — D-15 rad etdi. Agar ommaviy tuzatish ehtiyoji tug'ilsa, alohida "ommaviy tahrir" oqimi sifatida ko'riladi.
- **Sotuvchi bir necha bozorda savdo qilishi** — MVP bitta bozor; `vendors` tenant-scoped bo'ladi. Ko'p bozorli sotuvchi (va botda ikkala qarzni ko'rsatish) v2.
- **Telefonsiz sotuvchi** — D-12 majburiy qildi. Agar dala ishida telefonsiz savdogarlar ko'p chiqsa, qayta ko'riladi (ular bot xabarlarini ololmaydi).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Tavsif (REQUIREMENTS.md) | Tadqiqot qanday qo'llab-quvvatlaydi |
|----|--------------------------|--------------------------------------|
| **MARKET-01** | Platforma admini "Yangi bozor" ustasi orqali bozorni kod yozmasdan kiritadi: rekvizitlar → zonalar → rastalar → toifalar → tariflar → kameralar → kamera zonalari → snapshot jadvali | Pattern 5 (usta holatsiz — domen ma'lumotining O'ZI holat), Pattern 6 (`market_create()` SECURITY DEFINER — `sbozor_app` da `markets` ga INSERT huquqi YO'Q, empirik tasdiqlangan), Pitfall 6 (RBAC matritsasida platforma adminida `STALL_MANAGE` yo'q), Code Example 6 |
| **MARKET-02** | Bozor admini rastalar reestrini yuritadi: raqam, zona/qator, mahsulot toifasi, holat (faol/ta'mirda/yopiq), sotuvchi biriktirish | Pattern 1 (sxema), Pattern 3 (`stall_category_periods` voris modeli — D-04), Pattern 8 (`stall_code_registry` — D-02 raqam qayta ishlatilmasligi DB kafolati), Pitfall 3 |
| **MARKET-03** | Tariflar tarixiy saqlanadi (qaysi sanadan qaysi narx) — o'tmishdagi hisoblar keyingi narx o'zgarishidan buzilmaydi | Pattern 2 (**voris modeli** — `valid_from`, eski qatorga TEGILMAYDI; `daterange`+EXCLUDE D-06 ni buzardi), Pattern 9 (`tariff_past_immutable()` DB triggeri — D-07 kafolati), Code Example 2, empirik EXPLAIN natijasi |
| **MARKET-04** | Bozor admini sotuvchilar reestrini yuritadi (F.I.Sh., telefon) va rasta biriktirish davrlarini boshqaradi | Pattern 4 (`stall_assignments` — `daterange` + `EXCLUDE USING gist`, D-09/D-10/D-11 uchtasi ham empirik tasdiqlangan), Pitfall 1 (`btree_gist` o'rnatish huquqi), Pitfall 2 (Alembic EXCLUDE ni KO'RMAYDI), Pattern 10 (sotuvchi O'QISHI auditda — D-09) |
| **MARKET-05** | Bozor admini ishlamaydigan/bayram kunlarini belgilaydi — o'sha kunlarga patta hisoblanmaydi | Pattern 7 (`market_is_open(market_id, date)` — haftalik massiv + istisno sanalar, invoker huquqi bilan RLS ostida fail-closed, empirik tasdiqlangan), Code Example 4 |
| **MARKET-06** | Sxematik plan-xarita: rastalar zona bo'yicha rangli grid; rasta bosilganda karta ochiladi | Pattern 11 (CSS Grid + memoizatsiya, react-konva EMAS — o'lchovli asos bilan), D-20 uchun kengaytiriladigan `tone` kontrakti, Pitfall 8 |
</phase_requirements>

---

## Summary

Bu faza **texnologiya tanlash fazasi emas va deyarli yangi bog'liqlik ham talab qilmaydi** — frontendga birorta yangi npm paketi qo'shilmaydi, backendga esa faqat uchta Python paketi (`openpyxl`, `defusedxml`, `XlsxWriter`) kiradi va ularning ikkitasi CLAUDE.md'da oldindan ruxsat etilgan. Butun risk **ma'lumot modelida** va **1-fazada o'rnatilgan darvozalarda** yotadi: bu faza to'qqizta yangi tenant jadvalini tug'diradi, ularning har biri `tests/tenancy/test_meta.py` ning beshta invariantidan o'tishi kerak, va ikkita mavjud reyestr (`FINANCIAL_TABLES`, `ROLE_PERMISSIONS`) bu fazada **hozirgi holatida ishlamaydi**.

Beshta empirik topilma rejaga bevosita ta'sir qiladi (barchasi jonli `postgres:18.4-trixie` + `SQLAlchemy 2.0.51` + `Alembic 1.18.5` da o'lchandi). **Birinchi:** tarif tarixi uchun `daterange` + `EXCLUDE` **noto'g'ri model** — u yangi narx kiritilganda eski qatorning yuqori chegarasini yopishni, ya'ni **o'tmishdagi qatorni UPDATE qilishni** talab qiladi, bu esa D-06 ("eskisi o'zgarmaydi") va D-07 ("sanasi o'tgani qulflanadi") ikkalasini ham buzadi. To'g'ri model — **voris (successor) modeli**: faqat `valid_from`, `UNIQUE(market_id, category_id, valid_from)`, va "D sanadagi amaldagi tarif" so'rovi `ORDER BY valid_from DESC LIMIT 1`. EXPLAIN shuni ko'rsatdiki bu so'rov aynan o'sha UNIQUE indeksda `Index Scan Backward` beradi — qo'shimcha indeks kerak emas, va 6-fazaning ko'p-rastali `LATERAL` so'rovi ham shu indeksdan foydalanadi. **Ikkinchi:** sotuvchi biriktirish uchun esa `daterange` + `EXCLUDE USING gist` **aynan to'g'ri**, chunki u yerda bo'shliq (rasta bo'sh qolishi — D-11) haqiqiy holat va davrni yopish tabiiy amal; D-10 ning "10-sanada almashinuv" stsenariysi, bo'shliq va qoplanishning rad etilishi uchalasi ham o'lchandi. **Uchinchi:** `btree_gist` kengaytmasini `sbozor_owner` **o'rnata olmaydi** — `ERROR: permission denied to create extension "btree_gist" / HINT: Must have CREATE privilege on current database`. Ya'ni migratsiya uni yarata olmaydi va bu faza superuser bilan bajariladigan init qadamini (yoki `GRANT CREATE ON DATABASE`) talab qiladi. **To'rtinchi:** Alembic 1.18.5 `compare_metadata()` **`ExcludeConstraint` ni umuman ko'rmaydi** — konstraytni modeldan olib tashlaganimda ham diff **0 element** qaytardi. Bu ikki tomonlama: autogenerate soxta drift bermaydi (yaxshi), lekin konstrayt bazadan yo'qolsa **hech qanday test buni sezmaydi** (yomon) → meta-test darvozasi majburiy. **Beshinchi:** RLS yoqilgan jadvalda PostgreSQL `UNIQUE`/`EXCLUDE` buzilishining **`DETAIL` qatorini butunlay o'chirib tashlaydi** (`duplicate key value violates unique constraint "..."` — qiymatsiz). Ya'ni D-14 talab qilgan "88-qator: 12 raqami takrorlangan" xabarini **DB xatosidan olib bo'lmaydi**; import validatsiyasi yozishdan OLDIN ilova qatlamida bajarilishi shart.

Bundan tashqari 1-fazadan ikkita **qulflangan mina** meros qoldi. `sbozor_core.schema_contract.FINANCIAL_TABLES` ichida `stall_assignments` bor, `tests/tenancy/test_meta.py::test_financial_tables_have_guards` esa ro'yxatdagi HAR BIR mavjud jadvaldan `CHECK (amount_soum > 0)` talab qiladi — biriktirish jadvalida esa pul ustuni yo'q va bo'lishi ham kerak emas. `services/core-api/app/security/rbac.py` da esa `Role.PLATFORM_ADMIN` da `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` **yo'q**, ya'ni MARKET-01 ni bajaradigan odam o'zi qurayotgan bozorga rasta ham, tarif ham kirita olmaydi. Ikkalasi ham reja Wave 0 ida, birinchi migratsiyadan oldin yopilishi kerak.

**Primary recommendation:** Tarif va toifa tarixini **voris modeli** (`valid_from` + `UNIQUE(market_id, <parent>, valid_from)`) bilan, sotuvchi biriktirishni esa **`daterange` + `EXCLUDE USING gist`** bilan quring; `btree_gist` ni superuser init skriptiga qo'ying va migratsiyada mavjudligini baland ovozda tekshiring; ustaning holatini alohida jadvalda emas, **`markets.is_active = false` qoralama bozor** ko'rinishida DB'ning o'zida saqlang va qadamlar orasida 1-fazaning `POST /auth/select-market` mexanizmini qayta ishlating; importni `openpyxl(read_only=True) + defusedxml` bilan o'qib, **butun validatsiyani yozishdan oldin ilovada** bajaring; xaritani CSS Grid + memoizatsiyalangan tugmalar bilan chizing (react-konva 2-fazada kerak emas).

---

## Architectural Responsibility Map

| Qobiliyat | Asosiy qatlam | Ikkinchi qatlam | Sabab |
|-----------|---------------|-----------------|-------|
| Tarif tarixi (qaysi sanadan qaysi narx) | **Database (`tariffs` voris qatorlari)** | API (LATERAL lookup) | Yagona haqiqat manbai; 6-faza ham, hisobot ham bir xil so'rovni yozadi |
| O'tmishdagi tarif qatorining daxlsizligi (D-07) | **Database (`BEFORE UPDATE/DELETE` trigger)** | API (403) | Ilova qatlamidagi tekshiruvni xom SQL chetlab o'tadi — 1-faza D-10 falsafasi |
| Bir rastada davrlarning kesishmasligi (D-09) | **Database (`EXCLUDE USING gist`)** | API (validatsiya, foydali xabar) | Yagona ishonchli yo'l — parallel yozuvda ilova tekshiruvi yetarli emas |
| Rasta raqamining qayta ishlatilmasligi (D-02) | **Database (`stall_code_registry` + trigger)** | API (409 + xabar) | "Hech qachon" kafolati faqat DB konstraytida bo'ladi |
| Tenant izolyatsiyasi (`market_id`) | **Database (RLS + composite FK)** | API (`TenantSessionDep`) | 1-fazadan meros; yangi 9 jadval ham istisnosiz |
| "Bugun bozor ishlaydimi?" (D-17/D-18) | **Database (`market_is_open()` STABLE funksiya)** | — | 6-faza uni bitta chaqiruv bilan ishlatadi; kod-qatlamida takrorlanmaydi |
| Bozor yaratish (`markets` ga INSERT) | **Database (`SECURITY DEFINER` funksiya)** | API (RBAC + audit) | `sbozor_app` da `markets` ga faqat `SELECT` grant'i bor (empirik) |
| Usta holati (qaysi qadamgacha bajarilgan) | **Database (domen ma'lumotining o'zi)** | Frontend (URL'dagi qadam raqami) | Alohida `wizard_session` jadvali ikkinchi haqiqat manbai bo'lardi |
| Excel faylni parse qilish va validatsiya | **API (core-api)** | — | Brauzerda parse qilish validatsiyani chetlab o'tish yo'lini ochardi |
| Import atomarligi (D-14) | **Database (bitta tranzaksiya)** | API (xatolar ro'yxati) | 1000 qator = 9 ms (o'lchandi) — batching keraksiz |
| Import xato xabarlari (qator + sabab) | **API (yozishdan oldin)** | — | RLS DB xatosining `DETAIL` ini o'chiradi (empirik) — DB'dan olib bo'lmaydi |
| Plan-xarita joylashuvi (D-19) | **Frontend (CSS Grid)** | API (zona + kod tartibi) | Koordinata saqlanmaydi; joylashuv hosila (derived) |
| Rasta rangi / holati (D-20) | **Frontend (`tone` kontrakti)** | API (holat + sotuvchi bayrog'i) | 6–7 fazalar `tone` ni kengaytiradi, komponent qayta yozilmaydi |
| Sotuvchi shaxsiy ma'lumotini O'QISH auditi (D-09) | **API (`Depends(audit_read(...))`)** | Database (append-only `audit_log`) | Postgres'da `SELECT` uchun trigger yo'q — 1-faza Pattern 6 |
| Barcha domen o'zgarishlari auditi | **Database (`fn_audit_row()` trigger)** | API (app-qatlam yozuvlari) | D-10: xom SQL yo'li ham qamraladi |

---

## Project Constraints (from CLAUDE.md)

Quyidagilar **majburiy** va rejada qayta muhokama qilinmaydi. Bu fazaga tegishlilari:

| Direktiva | Bu fazada nimani anglatadi |
|-----------|----------------------------|
| **`float` pul uchun TAQIQLANGAN** | `tariffs.amount_soum` — `bigint`, Python `int`; `CHECK (amount_soum > 0)` |
| **Naive datetime TAQIQLANGAN** | `created_at` — `timestamptz`; **lekin `valid_from`/`period` — `date`/`daterange`** (pastga qarang) |
| **`postgres:18.4-trixie`** | `uuidv7()` native, `daterange`, `btree_gist` 1.8 mavjud (tekshirildi) |
| **Testlarda SQLite TAQIQLANGAN** | RLS + EXCLUDE + generated column — faqat haqiqiy Postgres'da; testcontainers |
| **`alembic-utils` 0.8.8** | `PGPolicy`/`PGFunction`/`PGTrigger` uchun; `ENABLE`/`FORCE`/`REVOKE`/**`EXCLUDE`** uchun EMAS |
| **`XlsxWriter` 3.2.9** eksport uchun | Shablon fayl generatsiyasi (import shabloni) |
| **`openpyxl`** faqat `.xlsx` O'QISH kerak bo'lganda | Aynan shu faza — CLAUDE.md "Alternatives Considered" jadvalida oldindan qayd etilgan |
| **`Next.js 16.2.12` + `proxy.ts`** | Yangi sahifalar `app/[locale]/(app)/...` ostida; `middleware.ts` YO'Q |
| **`TypeScript 5.9.3`** (7.0.2 EMAS) | `frontend/package.json` da pin qilingan |
| **`Tailwind 4.3.3` CSS-first** | `tailwind.config.js` YO'Q — `@theme {}` |
| **Servislar soni aynan 3** | Import parsing `core-api` ichida; alohida "import-service" YO'Q |
| **`uv` per-service `pyproject.toml`** | Yangi paketlar faqat `services/core-api/pyproject.toml` ga |
| **Ultralytics / passlib / python-jose / MinIO SDK TAQIQLANGAN** | Bu fazada baribir kerak emas |
| **GSD Workflow Enforcement** | Fayl o'zgartirish faqat GSD komandasi ichida |
| **Apple-uslub minimal dizayn, kassir oqimi ≤3 bosish** | Xarita va reestr UI — 1-fazadagi `components/ui/` primitivlari ustida |

---

## Standard Stack

### Yangi paketlar (faqat `services/core-api`)

| Kutubxona | Versiya | Maqsad | Nega standart |
|-----------|---------|--------|---------------|
| `openpyxl` | **3.1.5** (2024-06-28, MIT) | `.xlsx` import faylini O'QISH (D-13) | CLAUDE.md'da bu holat uchun oldindan tasdiqlangan yagona variant; `read_only=True` lazy loading bilan doimiy xotira [VERIFIED: PyPI + rasmiy docs] |
| `defusedxml` | **0.7.1** (2021-03-08, PSFL) | openpyxl uchun XML hujum himoyasi | openpyxl **o'z hujjatida** talab qiladi: *"By default openpyxl does not guard against quadratic blowup or billion laughs xml attacks. To guard against these attacks install defusedxml."* [CITED: openpyxl.readthedocs.io/en/stable — Security] |
| `XlsxWriter` | **3.2.9** (2025-09-16, BSD-2) | Import shablonini generatsiya qilish | CLAUDE.md'da qulflangan; write-only, doimiy xotira [VERIFIED: PyPI] |

**Frontendga yangi paket QO'SHILMAYDI.** Barcha kerakli narsalar allaqachon o'rnatilgan (`frontend/package.json` da tasdiqlandi): `react-hook-form@7.83.0`, `@hookform/resolvers@5.5.7`, `zod@4.4.3`, `@tanstack/react-query@5.101.4`, `nuqs@2.9.2` (usta qadamini URL'da saqlash uchun), `@radix-ui/react-dialog@1.1.15` (rasta kartasi), `@radix-ui/react-select@2.2.6`, `sonner@2.0.7`.

### Alternatives Considered

| O'rniga | Ishlatish mumkin edi | Trade-off / qachon o'tiladi |
|---------|----------------------|------------------------------|
| `openpyxl` + `defusedxml` | **`python-calamine` 0.8.2** (Rust/calamine, MIT, 2026-07-13) | Rust parser → billion-laughs sinfiga **strukturaviy immunitet** (Python XML parseri umuman ishlatilmaydi), ~10× tezroq, `.xls`/`.csv`/`.ods` ham o'qiydi, cp313 `manylinux_2_17_x86_64` g'ildiragi mavjud [VERIFIED: PyPI]. **O'tish sharti:** openpyxl 1000 qatorda sekin chiqsa yoki `defusedxml` (oxirgi reliz 2021) bilan bog'liq muammo yuzaga kelsa. CONTEXT.md canonical_refs openpyxl ni ko'rsatgani uchun boshlang'ich tanlov o'sha |
| `tariffs`: voris modeli (`valid_from`) | `daterange` + `EXCLUDE` | **RAD ETILDI** — yangi narx kiritishda eski qatorni UPDATE qilishni talab qiladi, D-06/D-07 ni buzadi. Faqat "narx davri albatta yopiladi va bo'shliq bo'lishi mumkin" bo'lgan modelda ma'noli |
| `stall_assignments`: `daterange` + `EXCLUDE` | `from_date`/`to_date` + qisman unique indeks (`WHERE upper(period) IS NULL`) | **Fallback.** `btree_gist` init qadami juda invaziv deb topilsa: `CREATE UNIQUE INDEX ... ON stall_assignments (market_id, stall_id) WHERE to_date IS NULL` — bir rastada bitta OCHIQ davr kafolatlanadi, lekin **tarixiy qoplanish DB'da bloklanmaydi**. Loyihaning "kafolat DB konstraytida" uslubidan chekinish |
| CSS Grid + DOM | `react-konva@19.2.5` + `konva@10.3.0` [VERIFIED: npm] | 2-fazada kerak emas (pastdagi o'lchov). **O'tish sharti:** kadr-bo'yicha yangilanish (drag, pan/zoom) yoki >2000 katak. Renderer kontrakti shunga tayyor qilinadi |
| `market_profile` alohida tenant jadvali | Rekvizitlarni `markets` ga qo'shish | `markets` — `GLOBAL_TABLES` dagi maxsus jadval, `sbozor_app` da faqat `SELECT` grant'i bor. Rekvizitni u yerga qo'yish har tahrir uchun `SECURITY DEFINER` funksiya talab qilardi va owner-yozuv yuzasini kengaytirardi |
| `stall_category_periods` (voris modeli) | `stalls.category_id` (tarixsiz) | **RAD ETILDI** — D-04 "toifa o'zgarishi sanadan kuchga kiradi, tarif tarixi bilan bir xil mexanizm" deb qulflangan. Tarixsiz variant kelajakka sana qo'yish imkonini va hisobni qayta hisoblash to'g'riligini yo'qotardi |

**Installation:**
```bash
uv add --project services/core-api "openpyxl==3.1.5" "defusedxml==0.7.1" "XlsxWriter==3.2.9"
```

**Version verification (2026-07-30 da PyPI'da bajarildi):**
```bash
pip index versions openpyxl        # 3.1.5   (INSTALLED: 3.1.5)
pip index versions XlsxWriter      # 3.2.9   (INSTALLED: 3.2.9)
pip index versions python-calamine # 0.8.2   (INSTALLED: 0.8.2)
```

---

## Package Legitimacy Audit

`slopcheck` mahalliy muhitda mavjud edi va **PyPI ekotizimi aniq ko'rsatilgan holda** ishlatildi (`slopcheck install -e pypi ...`).

> ⚠️ **Rejaga eslatma:** `slopcheck` ekotizimni loyiha fayllaridan avtomatik aniqlaydi va bu repoda (`package.json` ildizda) **npm** deb topadi. Ekotizim ko'rsatilmasa uchala Python paketi ham soxta `[SLOP]` verdikti oladi ("does not exist on npm"). Har doim `-e pypi` bering.

| Paket | Registry | Yosh / oxirgi reliz | Litsenziya | Source repo | slopcheck | Disposition |
|-------|----------|---------------------|-----------|-------------|-----------|-------------|
| `openpyxl` | PyPI | 3.1.5 — 2024-06-28 | MIT | foss.heptapod.net/openpyxl | **[OK]** | Approved |
| `XlsxWriter` | PyPI | 3.2.9 — 2025-09-16 | BSD-2-Clause | github.com/jmcnamara/XlsxWriter | **[OK]** | Approved |
| `defusedxml` | PyPI | 0.7.1 — 2021-03-08 | PSFL | github.com/tiran/defusedxml | **[OK]** | Approved (yoshi qayd etilgan — pastdagi Open Question 3) |
| `python-calamine` | PyPI | 0.8.2 — 2026-07-13 | MIT | github.com/dimastbk/python-calamine | **[OK]** (`HALLUCINATION_PATTERN` info: `python-` prefiksi — "nom LLM-bait ko'rinadi, lekin paket haqiqiy") | Approved **alternativa sifatida** (hozir o'rnatilmaydi) |
| `react-konva` / `konva` | npm | 19.2.5 / 10.3.0 | MIT | github.com/konvajs | — (o'rnatilmaydi) | **Bu fazada RAD ETILDI** — Pattern 11 |

**slopcheck [SLOP] verdikti bilan olib tashlangan paketlar:** yo'q
**Shubhali [SUS] deb belgilangan paketlar:** yo'q

> `openpyxl`, `XlsxWriter` va `python-calamine` CLAUDE.md loyiha-darajasidagi tadqiqotida rasmiy manbalardan olingan va slopcheck [OK] bergan → `[VERIFIED: PyPI registry]`. `defusedxml` **openpyxl'ning rasmiy hujjatida nom bilan tavsiya etilgan** → `[CITED: openpyxl.readthedocs.io]`.

---

## Architecture Patterns

### System Architecture Diagram

```
┌─ BROWSER ─────────────────────────────────────────────────────────────────────┐
│  /uz/markets/new?step=3      (nuqs — qadam URL'da, holat DB'da)               │
│  /uz/stalls   /uz/vendors   /uz/tariffs   /uz/calendar   /uz/map              │
└─────────┬─────────────────────────────────────────────────────────────────────┘
          │  TanStack Query (server state)  ·  react-hook-form + zod (qadam formasi)
          │  .xlsx fayl -> multipart/form-data
┌─────────▼─ FRONTEND SERVER (Next 16, proxy.ts) ───────────────────────────────┐
│  app/[locale]/(app)/{markets/new, stalls, vendors, tariffs, calendar, map}     │
└─────────┬─────────────────────────────────────────────────────────────────────┘
          │ HTTPS (nginx)  ·  Bearer access token (mid = tanlangan bozor)
┌─────────▼─ core-api (FastAPI) ────────────────────────────────────────────────┐
│                                                                                │
│  ┌── USTA (MARKET-01) — HOLATSIZ, domen ma'lumotining o'zi holat ───────────┐ │
│  │  1. POST /api/v1/markets        require_permission(MARKET_MANAGE)         │ │
│  │        └─► market_create()  ◄── SECURITY DEFINER (sbozor_app da           │ │
│  │              is_active=false     `markets` ga INSERT huquqi YO'Q)         │ │
│  │  2. POST /api/v1/auth/select-market   ◄── 1-FAZADAN, o'zgarishsiz         │ │
│  │        └─► yangi token: mid = <qoralama bozor>                            │ │
│  │  3..8. zonalar → toifalar → tariflar → rastalar → sotuvchilar → kalendar  │ │
│  │        (hammasi ODDIY tenant RLS ostida — maxsus yo'l yo'q)               │ │
│  │  9. POST /api/v1/markets/{id}/activate  ─► to'liqlik tekshiruvi ─►        │ │
│  │        market_activate()  ◄── SECURITY DEFINER, is_active=true            │ │
│  │  GET /api/v1/markets/{id}/setup-status  ─► qadamlar holati (HISOBLANADI,  │ │
│  │                                             saqlanmaydi)                  │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  ┌── IMPORT (D-13/D-14/D-15) ────────────────────────────────────────────────┐ │
│  │  .xlsx ──► [1] hajm chegarasi (bayt)                                      │ │
│  │        ──► [2] ZIP siqilmagan hajmi (zip-bomba darvozasi)                 │ │
│  │        ──► [3] openpyxl(read_only=True, data_only=True) + defusedxml      │ │
│  │        ──► [4] qator/ustun chegarasi                                      │ │
│  │        ──► [5] TO'LIQ VALIDATSIYA (yozishdan OLDIN):                      │ │
│  │              · zona/toifa mavjudmi   · kod fayl ichida takrorlanganmi     │ │
│  │              · kod bazada bormi      · telefon E.164 ga tushadimi         │ │
│  │              └─► xato bo'lsa: 422 + [{row: 88, code: "duplicate_code",    │ │
│  │                                       message: "12 raqami takrorlangan"}] │ │
│  │        ──► [6] BITTA tranzaksiya: INSERT ... ON CONFLICT DO NOTHING       │ │
│  │              (1000 qator = 9 ms, o'lchandi)                               │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  REESTR: GET/POST/PATCH /api/v1/{zones,categories,stalls,vendors,tariffs,      │
│                                  calendar}     keyset paginatsiya (1-faza naqshi)│
│  GET /api/v1/vendors ─► Depends(audit_read("vendors", reason="vendor_view"))   │
│                          ▲ D-09: shaxsiy ma'lumot O'QISHI ham jurnalda         │
└─────────┬──────────────────────────────────────────────────────────────────────┘
          │  postgresql+asyncpg://sbozor_app@db   (NOSUPERUSER NOBYPASSRLS)
┌─────────▼─ PostgreSQL 18.4 ────────────────────────────────────────────────────┐
│  GLOBAL (1-fazadan)          YANGI TENANT JADVALLARI (RLS ENABLE+FORCE+policy) │
│  ├ markets  (SELECT only)    ├ market_profile           (PK = market_id)       │
│  ├ users    (GRANT yo'q)     ├ zones                                           │
│  └ alembic_version           ├ stall_categories                                │
│                              ├ stalls ──────────┐                              │
│  extension: btree_gist 1.8   ├ stall_code_registry (D-02 kafolati)             │
│    ⚠ superuser init          ├ stall_category_periods  ── voris modeli (D-04)  │
│                              ├ tariffs                 ── voris modeli (D-06)  │
│                              ├ vendors                                         │
│                              ├ stall_assignments  ── daterange + EXCLUDE (D-09)│
│                              └ market_calendar_exceptions                      │
│                                                                                │
│  FUNKSIYALAR:  market_create() · market_rename() · market_activate()           │
│                  └─ SECURITY DEFINER, search_path pin (meta-test darvozasi)    │
│                market_is_open(market_id, date)                                 │
│                  └─ INVOKER huquqi, STABLE, RLS ostida fail-closed             │
│  TRIGGERLAR:   fn_audit_row()  -> stalls · stall_category_periods · tariffs ·  │
│                                   vendors · stall_assignments ·                │
│                                   market_calendar_exceptions                   │
│                tariff_past_immutable()  -> o'tgan sanali tarifni qulflaydi     │
│                stall_code_claim()       -> raqam qayta ishlatilishini rad etadi│
└────────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

Faqat **yangi** yoki **o'zgaradigan** fayllar (1-faza strukturasi saqlanadi):

```
packages/sbozor-core/sbozor_core/
├── models/
│   └── market.py                 # YANGI: 9 ta domen modeli
├── enums.py                      # O'ZGARADI: StallStatus qo'shiladi
└── schema_contract.py            # O'ZGARADI: FINANCIAL_TABLES / AUDITED_TABLES

migrations/
├── entities/
│   ├── __init__.py               # O'ZGARADI: TENANT_TABLES += 9 jadval
│   ├── functions.py              # O'ZGARADI: MARKET_ADMIN_FUNCTIONS
│   └── triggers.py               # O'ZGARADI: tariff_past_immutable, stall_code_claim
├── helpers.py                    # O'ZGARADI: exclusion_constraint(), require_extension()
└── versions/
    ├── 0006_market_domain.py     # zones, categories, stalls, code_registry, profile
    ├── 0007_temporal.py          # stall_category_periods, tariffs + immutability trigger
    ├── 0008_vendors.py           # vendors, stall_assignments (btree_gist + EXCLUDE)
    └── 0009_calendar.py          # market_calendar_exceptions + market_is_open()

ops/db/init/
└── 00-extensions.sql             # YANGI: CREATE EXTENSION btree_gist (superuser)

services/core-api/app/
├── api/v1/
│   ├── markets.py                # O'ZGARADI: POST /, /activate, /setup-status
│   ├── zones.py  categories.py  stalls.py  vendors.py  tariffs.py  calendar.py
│   └── imports.py                # YANGI: shablon + yuklash
├── repositories/
│   └── market_repo.py  stall_repo.py  vendor_repo.py  tariff_repo.py
├── services/
│   ├── xlsx_reader.py            # YANGI: xavfsiz o'qish (limits + defusedxml)
│   ├── xlsx_template.py          # YANGI: XlsxWriter shablon
│   └── import_validator.py       # YANGI: qator-raqamli xatolar (D-14)
└── security/rbac.py              # O'ZGARADI: PLATFORM_ADMIN + 2 yangi Permission

frontend/src/
├── app/[locale]/(app)/
│   ├── markets/new/page.tsx      # usta
│   ├── stalls/page.tsx  vendors/page.tsx  tariffs/page.tsx  calendar/page.tsx
│   └── map/page.tsx
├── components/
│   ├── wizard/                   # qadam qobig'i, progress, navigatsiya
│   ├── stalls/{stall-list,stall-dialog,stall-map,stall-map.test.tsx}.tsx
│   ├── vendors/ tariffs/ calendar/
│   └── import/{import-dropzone,import-errors}.tsx
└── lib/api-types.ts              # O'ZGARADI: zod kontraktlari

tests/
├── fixtures/market_domain.py     # YANGI: ikki bozor uchun domen seed'i
├── tenancy/test_market_domain_meta.py   # YANGI: EXCLUDE + trigger darvozalari
└── integration/test_{tariff_history,stall_assignments,market_calendar,
                      stall_import,wizard_flow,stall_code_reuse}.py
```

---

### Pattern 1: Yangi tenant jadvalining majburiy shakli

**What:** 1-fazadagi beshta invariant har bir yangi jadvalga istisnosiz qo'llanadi.

**When to use:** to'qqizta yangi jadvalning har birida.

```python
# migrations/versions/0006_market_domain.py
def upgrade() -> None:
    op.create_table(
        "stalls",
        sa.Column("id", PgUuid(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("market_id", PgUuid(as_uuid=True), nullable=False),
        sa.Column("zone_id",  PgUuid(as_uuid=True), nullable=False),
        sa.Column("code",   sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'active'")),
        sa.PrimaryKeyConstraint("id", name="pk_stalls"),
        # Cross-tenant havolani STRUKTURAVIY imkonsiz qiladi (1-faza T-01-26)
        sa.ForeignKeyConstraint(["market_id"], ["markets.id"], name="fk_stalls_market_id_markets"),
        sa.ForeignKeyConstraint(["market_id", "zone_id"], ["zones.market_id", "zones.id"],
                                name="fk_stalls_market_id_zone_id_zones"),
        # Keyingi jadvallar `(market_id, id)` ga havola qiladi
        sa.UniqueConstraint("market_id", "id",   name="uq_stalls_market_id_id"),
        sa.UniqueConstraint("market_id", "code", name="uq_stalls_market_id_code"),   # D-01
        sa.CheckConstraint("status IN ('active','maintenance','closed')", name="status_allowed"),
    )
    enable_tenant_rls("stalls")                 # ENABLE + FORCE + GRANT (helpers.py)
    create_entity(tenant_policy("stalls"))      # NULLIF(...) predikati
    create_entity(owner_bootstrap_policy("stalls"))
    attach_audit_trigger("stalls")              # D-10
```

**Beshta invariant** (`tests/tenancy/test_meta.py` avtomatik tekshiradi):
1. `market_id` ustuni bor (`test_every_table_is_tenant_scoped`)
2. `ENABLE ROW LEVEL SECURITY` (`relrowsecurity`)
3. `FORCE ROW LEVEL SECURITY` (`relforcerowsecurity`)
4. Kamida bitta policy va u `app.market_id` GUC'iga tayanadi (`test_app_role_policies_all_reference_tenant_guc`)
5. PK'dan boshqa har bir indeks `market_id` bilan boshlanadi (`test_tenant_indexes_lead_with_market_id`)

> **Empirik tasdiq (5-invariant va EXCLUDE):** `EXCLUDE USING gist (market_id WITH =, stall_id WITH =, period WITH &&)` yaratgan GiST indeksning **birinchi ustuni `market_id`** ekani `pg_index.indkey[0]` orqali o'lchandi — ya'ni exclusion konstrayti darvozadan **o'tadi**. Meta-test faqat birinchi ustunni tekshiradi, `amname` ni emas.

**Yangi jadval qo'shganda TO'RT joyga qo'shiladi** (biri unutilsa CI qizaradi):
`migrations/entities/__init__.py::TENANT_TABLES` · migratsiya fayli · kerak bo'lsa `schema_contract.AUDITED_TABLES` · `tests/fixtures/market_domain.py` seed'i.

---

### Pattern 2: Tarif tarixi — VORIS (successor) modeli, `daterange` EMAS

**What:** `tariffs` da faqat `valid_from` bo'ladi; yuqori chegara **saqlanmaydi**, u keyingi qatordan hosila.

**When to use:** har qanday "davr uzluksiz, bo'shliq yo'q, eski qator hech qachon o'zgarmaydi" holatida — bu fazada `tariffs` va `stall_category_periods`.

```sql
CREATE TABLE tariffs (
  id           uuid PRIMARY KEY DEFAULT uuidv7(),
  market_id    uuid NOT NULL,
  category_id  uuid NOT NULL,
  amount_soum  bigint NOT NULL,
  valid_from   date   NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  business_date date GENERATED ALWAYS AS ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED,
  CONSTRAINT ck_tariffs_amount_soum_positive CHECK (amount_soum > 0),
  CONSTRAINT uq_tariffs_market_id_category_id_valid_from
             UNIQUE (market_id, category_id, valid_from),
  CONSTRAINT fk_tariffs_market_id_category_id_stall_categories
             FOREIGN KEY (market_id, category_id) REFERENCES stall_categories (market_id, id)
);
```

**"D sanadagi amaldagi tarif":**
```sql
SELECT amount_soum FROM tariffs
WHERE market_id = :m AND category_id = :c AND valid_from <= :d
ORDER BY valid_from DESC LIMIT 1;
```

**Empirik EXPLAIN (`postgres:18.4-trixie`):**
```
Limit
  ->  Index Scan Backward using uq_tariffs_market_id_category_id_valid_from on tariffs
        Index Cond: ((market_id = ...) AND (category_id = ...) AND (valid_from <= '2026-09-01'::date))
```
Qo'shimcha indeks **kerak emas** — UNIQUE konstraytining o'zi optimal.

**6-faza uchun ko'p-toifali variant (`LATERAL`) ham xuddi shu indeksdan foydalanadi:**
```
Nested Loop Left Join
  ->  Bitmap Index Scan on stall_categories_market_id_id_key
  ->  Limit -> Index Scan Backward using uq_tariffs_market_id_category_id_valid_from
```

**Nega `daterange` + `EXCLUDE` EMAS (bu fazadagi eng muhim model qarori):**

| Talab | Voris modeli | `daterange` + EXCLUDE |
|-------|--------------|------------------------|
| D-06: "yangi qator qo'shiladi, **eskisi o'zgarmaydi**" | ✅ INSERT'ning o'zi | ❌ eski qatorning `upper()` ini yopish uchun UPDATE SHART |
| D-07: "sanasi o'tgani **qulflanadi**" | ✅ o'tgan qatorga hech qachon tegilmaydi | ❌ o'tgan qatorni yopish D-07 ni buzadi |
| Kelajakka narx kiritish | ✅ `valid_from = '2026-09-01'` | ✅ lekin oldingi qatorni ham tahrirlash kerak |
| Bo'shliq (tarifsiz davr) | Faqat birinchi qatordan OLDIN → D-08 fail-closed | Har joyda bo'lishi mumkin — nazorat qiyin |
| `btree_gist` kengaytmasi | ❌ kerak emas | ✅ kerak (Pitfall 1) |
| Yozish amali soni | 1 INSERT | 1 UPDATE + 1 INSERT (tranzaksiya) |

**Empirik fail-closed tasdiqi:** birinchi tarifdan oldingi sanaga so'rov **0 qator** qaytardi — bu aynan D-08 talab qilgan xulq (hisob yozilmaydi, anomaliya chiqadi).

**Trade-offs:** (+) yozish yo'li mutlaq sodda, konkurent yozuvda konflikt yo'q. (+) audit diff'i toza (faqat `insert` qatorlari). (−) "bu tarif qachongacha amal qildi?" savoli hosila — UI uni `LEAD(valid_from) OVER (...)` bilan ko'rsatadi, DB'da saqlanmaydi. (−) "tarif hech qachon amal qilmagan davr" tushunchasi yo'q — agar bozor tarifni vaqtincha bekor qilmoqchi bo'lsa, model buni ifodalay olmaydi (v2 ehtiyoji, hozir talab yo'q).

---

### Pattern 3: Toifa tarixi — tarif bilan AYNAN bir xil mexanizm (D-04)

```sql
CREATE TABLE stall_category_periods (
  id          uuid PRIMARY KEY DEFAULT uuidv7(),
  market_id   uuid NOT NULL,
  stall_id    uuid NOT NULL,
  category_id uuid NOT NULL,
  valid_from  date NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_scp_market_id_stall_id_valid_from UNIQUE (market_id, stall_id, valid_from),
  CONSTRAINT fk_scp_stall    FOREIGN KEY (market_id, stall_id)    REFERENCES stalls (market_id, id),
  CONSTRAINT fk_scp_category FOREIGN KEY (market_id, category_id)
                             REFERENCES stall_categories (market_id, id)
);
```

**"D sanada rasta qaysi toifada va tarifi qancha" — bitta so'rov (6-faza shuni ishlatadi):**
```sql
SELECT s.id AS stall_id, cat.category_id, t.amount_soum
FROM stalls s
LEFT JOIN LATERAL (
  SELECT p.category_id FROM stall_category_periods p
  WHERE p.market_id = s.market_id AND p.stall_id = s.id AND p.valid_from <= :d
  ORDER BY p.valid_from DESC LIMIT 1
) cat ON true
LEFT JOIN LATERAL (
  SELECT t.amount_soum FROM tariffs t
  WHERE t.market_id = s.market_id AND t.category_id = cat.category_id AND t.valid_from <= :d
  ORDER BY t.valid_from DESC LIMIT 1
) t ON true
WHERE s.market_id = :m AND s.status = 'active';
-- t.amount_soum IS NULL  ->  D-08 "tarifsiz band rasta" anomaliyasi
```

**KRITIK detal — boshlang'ich `valid_from`:** import va usta yaratgan **birinchi** toifa/tarif qatorlarining `valid_from` i `market_profile.operating_since` dan olinadi (usta 1-qadamda so'raydi). Agar import kuni qo'yilsa, 6-faza o'sha sanadan oldingi har qanday kunni **tarifsiz** deb topadi va butun tarixni anomaliyaga aylantiradi.

---

### Pattern 4: Sotuvchi biriktirish — `daterange` + `EXCLUDE USING gist` (D-09/D-10/D-11)

**What:** bu yerda `daterange` **to'g'ri model**, chunki (a) davr haqiqatan yopiladi (sotuvchi ketadi), (b) bo'shliq — ma'noli holat (D-11 anomaliyasi), (c) o'tmishdagi davrni yopish D-07 kabi qoida bilan taqiqlanmagan.

```python
# packages/sbozor-core/sbozor_core/models/market.py
class StallAssignment(Base, TenantMixin):
    __tablename__ = "stall_assignments"
    __table_args__ = (
        ExcludeConstraint(
            ("market_id", "="), ("stall_id", "="), ("period", "&&"),
            name="ex_stall_assignments_no_overlap", using="gist",
        ),
        CheckConstraint("lower(period) IS NOT NULL", name="lower_bound_required"),
        ForeignKeyConstraint(["market_id", "stall_id"],  ["stalls.market_id", "stalls.id"],  ...),
        ForeignKeyConstraint(["market_id", "vendor_id"], ["vendors.market_id", "vendors.id"], ...),
        UniqueConstraint("market_id", "id", name="uq_stall_assignments_market_id_id"),
    )
    id: Mapped[UUID] = uuid_pk()
    stall_id:  Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    vendor_id: Mapped[UUID] = mapped_column(PgUuid(as_uuid=True), nullable=False)
    period:    Mapped[Range[date]] = mapped_column(DATERANGE, nullable=False)
```

**SQLAlchemy 2.0.51 chiqaradigan DDL (o'lchandi):**
```sql
CONSTRAINT ex_stall_assignments_no_overlap
  EXCLUDE USING gist (market_id WITH =, stall_id WITH =, period WITH &&)
```

**D-10 stsenariysi empirik tasdiqlandi** (10-sanada almashinuv):

| Kun | Kim biriktirilgan |
|-----|-------------------|
| 2026-08-08 | Eski sotuvchi |
| 2026-08-09 | Eski sotuvchi |
| **2026-08-10** | **Yangi sotuvchi** |
| 2026-08-11 | Yangi sotuvchi |

`[2026-08-01, 2026-08-10)` + `[2026-08-10, ∞)` — `'[)'` chegaralari bilan kun aynan joyiga tushadi. Qoplanadigan uchinchi urinish (`[2026-08-05, 2026-08-20)`) `ExclusionViolationError` (**SQLSTATE 23P01**) bilan rad etildi.

**D-11 bo'shlig'i ham tasdiqlandi:** `[08-01, 08-05)` va `[08-20, ∞)` orasidagi kunlarda `period @> d` **0 qator** beradi → "sotuvchisiz band rasta" anomaliyasi.

**"Bugun kim biriktirilgan" so'rovi (SQLAlchemy):**
```python
select(StallAssignment.vendor_id).where(
    StallAssignment.market_id == m,
    StallAssignment.stall_id == s,
    StallAssignment.period.contains(business_date),   # -> `period @> :d`
)
```

**asyncpg round-trip o'lchandi:** `Range(lower=date(2026,8,10), upper=None, bounds='[)', empty=False)` — ochiq oxirli davr `upper=None` bo'lib to'g'ri qaytadi, qo'shimcha konversiya kerak emas.

**Xatoni ajratish (API 409 uchun):**
```python
except IntegrityError as exc:
    sqlstate = getattr(exc.orig, "sqlstate", None)
    if sqlstate == "23P01":   # exclusion_violation -> davr kesishdi
        raise HTTPException(409, detail="assignment_period_overlaps") from exc
    if sqlstate == "23505":   # unique_violation
        ...
```
> `exc.orig.constraint_name` asyncpg dialektining o'ram'ida **`None`** bo'lib qaytadi (o'lchandi) — ishonchli diskriminator faqat `sqlstate`.

---

### Pattern 5: Usta — holatsiz. Domen ma'lumotining O'ZI holat.

**What:** alohida `wizard_session` jadvali ham, klient-tomon global store ham **yaratilmaydi**. Usta 1-qadamda `is_active = false` qoralama bozorni tug'diradi va keyingi har bir qadam haqiqiy domen jadvaliga yozadi.

**Nega bu yagona to'g'ri variant:**

| Variant | Muammo |
|---------|--------|
| `wizard_session(market_id, payload jsonb)` | `market_id` hali yo'q → RLS'siz global jadval kerak (butun 1-faza naqshiga zid). 1000 rastali import JSONB'da yashaydi. Validatsiya ikki marta yoziladi |
| Faqat klient tomonda (Zustand va h.k.) | Sahifa yangilanishi butun ishni yo'q qiladi. Yangi kutubxona. 1000 rasta brauzer xotirasida |
| **Qoralama bozor (`is_active=false`)** | ✅ Har qadam alohida tranzaksiya, RLS tabiiy ishlaydi, boshqa qurilmadan davom ettirish mumkin, sahifa yangilash xavfsiz |

**Oqim:**
```
1. POST /api/v1/markets        {name, timezone, operating_since, requisites...}
      ├─ require_permission(MARKET_MANAGE)     [platforma admini]
      ├─ market_create()  SECURITY DEFINER  ->  markets(is_active=false)
      └─ so'ng bir xil tranzaksiyada market_profile qatori
2. POST /api/v1/auth/select-market {market_id}          ◄── 1-FAZADAN, O'ZGARISHSIZ
      └─ `_platform_admin_market()` a'zoligi bo'lmagan bozorni tanlashga ruxsat beradi
      └─ audit: "platforma admini X bozorida" (D-06)
3..8. Oddiy tenant endpointlari — hech qanday maxsus "wizard" API'si yo'q
9. POST /api/v1/markets/{id}/activate
      ├─ TO'LIQLIK TEKSHIRUVI (serverda!):  zona ≥1 · toifa ≥1 · har toifada
      │    valid_from <= operating_since bo'lgan tarif · rasta ≥1 ·
      │    har rastada toifa davri · haftalik jadval o'rnatilgan
      └─ market_activate()  ->  is_active = true
```

**Qadam holati hisoblanadi, saqlanmaydi:**
```
GET /api/v1/markets/{id}/setup-status
->  { "zones": 4, "categories": 6, "tariffs": 6, "stalls": 512, "vendors": 380,
      "calendar_configured": true, "cameras": 0,
      "can_activate": true, "blocking": [] }
```
Frontend shu javobdan progress chizadi. Qadam raqami URL'da (`?step=4`, `nuqs` bilan) — u faqat ko'rinish, haqiqat emas.

**Qoralama bozor xavfsizligi (majburiy):**
- `auth_list_markets()` `is_active` ni qaytaradi → bozor tanlash ekranida "chala — davom ettirish" deb ko'rsatiladi (1-fazada allaqachon mavjud maydon)
- **6-faza ilgagi:** kunlik billing job `WHERE m.is_active` bilan filtrlanadi. Bu hozir yozilmaydi, lekin `setup-status` va `activate` mantig'i shu shartnomani o'rnatadi
- Qoralama bozor **o'chirilishi mumkin** (`DELETE /api/v1/markets/{id}` faqat `is_active=false` va hech qanday `daily_charges` bo'lmasa) — aks holda tashlab ketilgan qoralamalar to'planadi

**Trade-offs:** (+) noldan yangi mexanizm yaratilmaydi — 1-fazaning `select-market` + RLS + audit oqimi qayta ishlatiladi. (+) 1000 rastali import hech qachon "sessiya"da turmaydi. (−) Yarim to'ldirilgan bozor DB'da yashaydi → har bir global ro'yxatda `is_active` filtri esdan chiqmasligi kerak (Pitfall 7).

---

### Pattern 6: `markets` ga yozish — faqat `SECURITY DEFINER` orqali

**What:** `sbozor_app` roliga `markets` da **faqat `SELECT`** grant'i berilgan (`migrations/versions/0001_identity.py:106` — `grant_app_dml("markets", ops="SELECT")`), va policy predikati `id = NULLIF(current_setting('app.market_id', true), '')::uuid`.

**Ikki mustaqil to'siq:**
1. GRANT yo'q → `INSERT INTO markets` = `permission denied`
2. Grant berilganda ham: yangi bozorning `id` si hali `app.market_id` ga teng emas → `WITH CHECK` rad etadi

→ **Bozor yaratish `auth_create_user` bilan bir xil naqshni takrorlaydi:**

```sql
CREATE OR REPLACE FUNCTION market_create(p_name text, p_timezone text)
RETURNS uuid
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public        -- meta-test darvozasi (T-01-23)
VOLATILE
AS $$
    INSERT INTO public.markets (name, timezone, is_active)
    VALUES (p_name, COALESCE(NULLIF(p_timezone,''), 'Asia/Tashkent'), false)
    RETURNING id
$$;
REVOKE ALL ON FUNCTION market_create(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION market_create(text, text) TO sbozor_app;
```

Xuddi shunday `market_activate(p_market_id uuid)` va `market_rename(p_market_id uuid, p_name text)`.

> **`tests/tenancy/test_meta.py::test_security_definer_functions_pin_search_path`** butun `public` sxemani skanerlaydi — yangi funksiyalar avtomatik qamraladi va `SET search_path` unutilsa CI qizaradi. Ular `EXPECTED_DEFINER_FUNCTIONS` ga ham qo'shilishi kerak (aks holda faqat "bor" tekshiruvi o'tkazib yuboriladi).

**Nega `is_active=false` funksiyaning ICHIDA literal:** `auth_create_user` da `must_change_password` literal `true` bo'lgani bilan bir xil sabab — parametr bo'lsa, kimdir bir kun `true` bilan chaqirib to'liqlik tekshiruvini butunlay chetlab o'tardi. Faollashtirish **alohida funksiya**, ya'ni alohida GRANT va alohida audit hodisasi.

---

### Pattern 7: Ish kunlari — haftalik massiv + istisno sanalar (D-17/D-18)

```sql
-- market_profile ustuni (bozorga bitta qator)
open_weekdays smallint[] NOT NULL DEFAULT '{1,2,3,4,5,6,7}'   -- ISO: 1=dushanba .. 7=yakshanba
CONSTRAINT ck_market_profile_open_weekdays CHECK (
  open_weekdays <@ ARRAY[1,2,3,4,5,6,7]::smallint[] AND array_length(open_weekdays,1) IS NOT NULL
)

-- istisnolar
CREATE TABLE market_calendar_exceptions (
  id uuid PRIMARY KEY DEFAULT uuidv7(),
  market_id uuid NOT NULL,
  exception_date date NOT NULL,
  is_open boolean NOT NULL,          -- false = bayram/yopiq, true = istisno ish kuni
  note text,
  CONSTRAINT uq_mce_market_id_exception_date UNIQUE (market_id, exception_date)
);
```

```sql
CREATE OR REPLACE FUNCTION market_is_open(p_market_id uuid, p_date date) RETURNS boolean
LANGUAGE sql STABLE SET search_path = pg_catalog, public AS $$
  SELECT COALESCE(
    (SELECT e.is_open FROM market_calendar_exceptions e
      WHERE e.market_id = p_market_id AND e.exception_date = p_date),   -- 1) istisno ustun
    (SELECT EXTRACT(ISODOW FROM p_date)::smallint = ANY(p.open_weekdays)
       FROM market_profile p WHERE p.market_id = p_market_id),          -- 2) haftalik jadval
    false                                                              -- 3) FAIL-CLOSED
  )
$$;
```

**`SECURITY DEFINER` ATAYIN EMAS** — funksiya chaqiruvchi huquqi bilan ishlaydi, ya'ni RLS unga to'liq qo'llanadi va boshqa bozor so'ralganda 0 qator → `false`.

**Empirik natija (`sbozor_app` roli, `app.market_id = A`):**

| Holat | Natija |
|-------|--------|
| 2026-08-24 (dushanba, haftalik jadvalda yo'q) | `false` |
| 2026-08-17 (dushanba, LEKIN `is_open=true` istisnosi) | `true` |
| 2026-01-01 (`is_open=false` bayram) | `false` |
| **Boshqa bozor `market_id` si so'raldi** | **`false`** (fail-closed) |
| Sozlamasi yo'q bozor | `false` (fail-closed) |

**6-fazaga kontrakt:** kunlik job bitta shart yozadi — `WHERE market_is_open(:market_id, :business_date)`.

**⚠ Fail-closed'ning teskari tomoni:** sozlama yo'q bo'lsa bozor **hech qachon ishlamaydi**, ya'ni tushum jimgina nolga tushadi. Shuning uchun `market_profile` qatori **bozor bilan BIR TRANZAKSIYADA** yaratiladi (usta 1-qadam) va `activate` to'liqlik tekshiruvi `open_weekdays` ni ham talab qiladi. Qo'shimcha: 6-fazada "N kun ketma-ket yopiq" alert ilgagi qoldiriladi.

---

### Pattern 8: Rasta raqamining qayta ishlatilmasligi (D-02) — DB kafolati

**What:** `UNIQUE(market_id, code)` **yetarli emas**: rasta kodi tahrirlangach eski kod bo'shab qoladi va yangi rastaga berilishi mumkin bo'lib qoladi. D-02 buni aynan taqiqlaydi.

```sql
CREATE TABLE stall_code_registry (
  market_id  uuid NOT NULL,
  code       text NOT NULL,
  stall_id   uuid NOT NULL,
  first_seen timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pk_stall_code_registry PRIMARY KEY (market_id, code),
  CONSTRAINT fk_scr_stall FOREIGN KEY (market_id, stall_id) REFERENCES stalls (market_id, id)
);

CREATE OR REPLACE FUNCTION stall_code_claim() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  INSERT INTO public.stall_code_registry (market_id, code, stall_id)
  VALUES (NEW.market_id, NEW.code, NEW.id)
  ON CONFLICT (market_id, code) DO NOTHING;
  IF NOT EXISTS (SELECT 1 FROM public.stall_code_registry r
                  WHERE r.market_id = NEW.market_id AND r.code = NEW.code
                    AND r.stall_id = NEW.id) THEN
    RAISE EXCEPTION 'stall code % is already retired in this market (D-02)', NEW.code
      USING ERRCODE = '23505';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER trg_stall_code_claim
  BEFORE INSERT OR UPDATE OF code ON stalls
  FOR EACH ROW EXECUTE FUNCTION stall_code_claim();
```

Natija: kod bir marta bozorda ishlatilgach, u **boshqa** rastaga hech qachon o'tmaydi — hisobotdagi "12-rasta" yillar davomida bitta jismoniy joy bo'lib qoladi. Eski rastaning o'z kodini qaytarib olishi (tuzatishni bekor qilish) ruxsat etiladi.

**Arzonroq (lekin zaifroq) muqobil:** faqat `UNIQUE(market_id, code)` + ilova qatlamida "kod avval ishlatilganmi" tekshiruvi. Rad etish sababi: bu tekshiruv xom SQL yo'lini ushlamaydi va D-02 "tizim rad etadi" deb qulflangan.

---

### Pattern 9: O'tmishdagi tarifning daxlsizligi (D-07) — DB triggeri

```sql
CREATE OR REPLACE FUNCTION tariff_past_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  IF OLD.valid_from <= (now() AT TIME ZONE 'Asia/Tashkent')::date THEN
    RAISE EXCEPTION 'tariff row valid from % is locked (D-07)', OLD.valid_from
      USING ERRCODE = '23514';
  END IF;
  RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END $$;

CREATE TRIGGER trg_tariff_past_immutable
  BEFORE UPDATE OR DELETE ON tariffs
  FOR EACH ROW EXECUTE FUNCTION tariff_past_immutable();
```

**Nega DB'da, ilovada emas:** 1-faza D-10 falsafasi — moliyaviy qoidani xom SQL chetlab o'tmasligi kerak. Ilova qatlami baribir 403 qaytaradi (foydalanuvchiga tushunarli xabar uchun), lekin **kafolat** shu triggerda.

`stall_category_periods` uchun ham xuddi shunday trigger tavsiya etiladi (D-04 "o'tmishdagi hisob buzilmaydi").

---

### Pattern 10: Sotuvchi ma'lumotini O'QISH auditi (D-09) — 1-fazaning birinchi iste'molchisi

1-faza RESEARCH Pattern 6 buni aniq oldindan aytgan: *"1-fazada qamrov: sotuvchilar (`vendors`) hali 2-fazada tug'iladi… Mexanizm shu yerda quriladi va keyingi fazalar unga bir dekorator bilan ulanadi."*

```python
# services/core-api/app/api/v1/vendors.py
VendorViewerDep = Annotated[Principal, Depends(require_permission(Permission.VENDOR_VIEW))]
VendorReadIntentDep = Annotated[
    AuditReadIntent, Depends(audit_read(TABLE_VENDORS, reason="vendor_view")),
]

@router.get("", response_model=VendorListResponse)
async def list_vendors(
    principal: VendorViewerDep,          # ← BIRINCHI: 403 olgan so'rov iz qoldirmaydi
    intent: VendorReadIntentDep,         # ← IKKINCHI: o'qish niyati
    session: TenantSessionDep,
) -> VendorListResponse: ...
```

**E'lon tartibi majburiy** — `audit.py` docstringida hujjatlashtirilgan ikki qatlamli qoida: `require_permission` `audit_read` dan OLDIN turadi, aks holda rad etilgan so'rov jurnalga **yolg'on dalil** yozadi.

`TABLE_VENDORS = "vendors"` konstantasi `app/security/audit.py` ga qo'shiladi (`TABLE_USERS` bilan bir joyda).

---

### Pattern 11: Plan-xarita — CSS Grid, react-konva EMAS (MARKET-06)

**Qaror:** 2-fazada `react-konva` **o'rnatilmaydi**.

**Asos:**

| Omil | O'lchov / holat |
|------|-----------------|
| Katak soni | 300–1000 (Karmana) |
| Render turi | **Statik** — D-19 drag-drop'ni RAD ETDI, D-20 faqat holat rangini beradi |
| 1000 elementli React yangilanishi | **~21 ms** optimizatsiyasiz; `shouldComponentUpdate`/memo bilan **~4 ms** [CITED: Anton Lavrenov (Konva muallifi), medium.com/@lavrton] |
| 16 ms kadr byudjeti | Faqat **animatsiya/drag** uchun ahamiyatli — bizda ikkalasi ham yo'q |
| Bir martalik render | 21 ms — foydalanuvchi sezmaydi |

Ya'ni Konva'ning ustunligi (kadr-bo'yicha qayta chizish) bu fazada **umuman ishlatilmaydi**, narxi esa haqiqiy: yangi bog'liqlik, SSR yo'q (canvas faqat klientda), a11y yo'q (canvasda tugma yo'q — klaviatura va skrinrider ishlamaydi), matn o'lchamlari qo'lda hisoblanadi.

**Amalga oshirish qoidalari (majburiy):**
1. Katak — haqiqiy `<button>` (a11y + klaviatura + `aria-label="12-rasta, faol, Sabzavot"`)
2. Katak komponenti `React.memo` bilan; `onSelect` — `useCallback` bilan barqaror havola
3. **Tanlangan rasta katakning propiga TUSHMAYDI** — u Radix Dialog holatida yashaydi, aks holda har bosishda 1000 katak qayta render bo'ladi
4. Renderer kontrakti 6–7 fazaga tayyor (D-20):
   ```ts
   type StallTone = 'neutral' | 'muted' | 'off'          // 2-faza
                  | 'paid' | 'debt' | 'mismatch';        // 6–7 fazalarda qo'shiladi
   type StallCell = { id: string; code: string; tone: StallTone; hasVendor: boolean };
   type ZoneBlock = { id: string; name: string; cells: StallCell[] };   // kod tartibida
   ```
   `tone` ni **API hisoblab beradi** emas, **frontend `status` + `hasVendor` dan hosil qiladi** — 6-fazada yangi manba qo'shilganda faqat hosila funksiya o'zgaradi
5. Joylashuv: har zona `<section>` + `grid-template-columns: repeat(auto-fill, minmax(3rem, 1fr))`; koordinata saqlanmaydi (D-19)

**Konva'ga o'tish sharti (v2):** kadr-bo'yicha yangilanish (drag/pan/zoom) kerak bo'lsa yoki katak soni >2000 ga chiqsa. O'tish narxi — faqat renderer komponenti (`stall-map.tsx`), ma'lumot kontrakti o'zgarmaydi.

---

### Anti-Patterns to Avoid

- **`financial_guards("tariffs", unique_cols=["category_id"])` chaqirish** — u `UNIQUE(market_id, category_id, business_date)` beradi, ya'ni bir kunda ikkita kelajak tarifini ("1-sentabrdan" va "1-oktabrdan") kiritib bo'lmaydi. `tariffs` uchun uchta qo'riqchi **qo'lda** yoziladi.
- **`stall_assignments` ni `FINANCIAL_TABLES` da qoldirish** — meta-test `CHECK (amount_soum > 0)` talab qiladi, jadvalda esa pul ustuni yo'q va bo'lmasligi kerak.
- **Tarif tarixini `daterange` bilan modellashtirish** — D-06/D-07 ni buzadi (Pattern 2).
- **Import xato xabarini DB xatosidan olish** — RLS ostida `DETAIL` bo'sh (Pitfall 4).
- **`markets` ga to'g'ridan-to'g'ri `INSERT`** — GRANT ham, policy ham rad etadi (Pattern 6).
- **`market_is_open()` ni `SECURITY DEFINER` qilish** — u RLS'dan chiqib ketadi va bir bozor boshqasining kalendarini o'qiy oladi.
- **Xaritada `key={index}`** — kod tartibi o'zgarganda React noto'g'ri katakni qayta ishlatadi; `key={stall.id}`.
- **Rasta kartasini har katakka o'rnatilgan `<Dialog>` bilan** — 1000 ta Radix portali. Bitta dialog + tanlangan ID.
- **Import faylini brauzerda parse qilish** — validatsiya chetlab o'tiladi.
- **`valid_from` ni `timestamptz` qilish** — biznes-kun chegarasi `date` bilan ishlaydi; `timestamptz` "1-sentabr soat nechadan?" degan javobsiz savolni tug'diradi.
- **`op.execute("CREATE EXTENSION btree_gist")`** migratsiyada — `sbozor_owner` uchun `permission denied` (Pitfall 1).

---

## Don't Hand-Roll

| Muammo | Qurmang | O'rniga | Nega |
|--------|---------|---------|------|
| Davrlarning kesishmasligi | Ilovada `SELECT ... WHERE overlaps` keyin `INSERT` | **`EXCLUDE USING gist` + `btree_gist`** | Parallel yozuvda ilova tekshiruvi yorilib ketadi; DB konstraytida atomik |
| Sana oralig'i arifmetikasi | `from_date <= d AND (to_date IS NULL OR d < to_date)` | **`daterange` + `@>`** | Chegara inklyuzivligi (`[)`) bir joyda e'lon qilinadi, har so'rovda takrorlanmaydi |
| "D sanadagi amaldagi qiymat" | Ilovada barcha qatorlarni o'qib saralash | **`ORDER BY valid_from DESC LIMIT 1` + `LATERAL`** | Indeksdan `Index Scan Backward` (o'lchandi); ilovada N+1 |
| `.xlsx` parse qilish | ZIP + XML qo'lda | **`openpyxl(read_only=True)`** | Umumiy jadval (shared strings), sana seriallari, birlashtirilgan kataklar |
| XML hujumlaridan himoya | O'z parser cheklovlari | **`defusedxml`** | openpyxl **o'z hujjatida** shuni talab qiladi |
| Telefon normalizatsiyasi | Regex | **`sbozor_core.phone`** (1-fazadan) | D-12 unique kaliti; formatlar ko'p |
| Pul turlari | `Decimal`/`float` | **`sbozor_core.money`** (BIGINT so'm) | `float` TAQIQLANGAN |
| Biznes-kun | Kodda `astimezone().date()` | **`GENERATED ALWAYS AS ... STORED`** (`BUSINESS_DATE_EXPR`) | 1-faza Pattern 7 |
| Tenant filtri | `WHERE market_id=` intizomi | **RLS + `TenantSessionDep`** | 1-fazadan meros |
| Idempotent qayta import | "Avval SELECT keyin INSERT" | **`ON CONFLICT (market_id, code) DO NOTHING`** | D-15 aynan shu; race yo'q (o'lchandi: 1000 qator 6 ms) |
| Ko'p qadamli forma holati | Yangi global store (Zustand va h.k.) | **DB qoralama + `nuqs` qadam raqami** | Ikkinchi haqiqat manbai yaratilmaydi |
| Xarita virtualizatsiyasi | `react-window` va h.k. | **Oddiy CSS Grid** | 1000 statik tugma virtualizatsiyani talab qilmaydi |
| Formula injection'dan himoya | "Foydalanuvchi bunday yozmaydi" | **`=`,`+`,`-`,`@`,`\t`,`\r` bilan boshlanadigan katakni `'` bilan prefikslash** | [CITED: OWASP CSV Injection] |

**Key insight:** bu fazadagi har bir "qo'lda qilish" varianti **jimgina** buziladi. Kesishgan biriktirish davri faqat 6-fazada ikki sotuvchiga bir kunning hisobi yozilganda ko'rinadi; qayta ishlatilgan rasta raqami faqat nizo paytida ko'rinadi; tarif tarixining buzilishi esa hech qachon ko'rinmaydi — u shunchaki noto'g'ri raqam beradi. Shuning uchun uchalasi ham **DB konstraytiga** aylantirilgan.

---

## Common Pitfalls

### Pitfall 1: `btree_gist` ni `sbozor_owner` o'rnata olmaydi (VERIFIED)

**Nima buziladi:** `0008_vendors.py` migratsiyasida `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")` yozilsa, migratsiya yiqiladi:
```
ERROR:  permission denied to create extension "btree_gist"
HINT:  Must have CREATE privilege on current database to create this extension.
```
**Nega:** `btree_gist` — *trusted* kengaytma, lekin trusted bo'lish **baza darajasidagi `CREATE` huquqini** talab qiladi. `ops/db/init/01-roles.sql` `sbozor_owner` ni `NOCREATEDB` qilib yaratadi va u bazaning egasi emas (`public` sxemaning egasi, boshqa narsa).
**Qanday oldini olish — ikki yo'l:**
1. **Tavsiya etiladi:** yangi `ops/db/init/00-extensions.sql` (superuser bilan bajariladi, `docker-entrypoint-initdb.d` orqali) + `tests/conftest.py` uni ham `01-roles.sql` kabi VERBATIM o'qiydi. Migratsiya esa **baland ovozda tekshiradi**:
   ```python
   if not op.get_bind().execute(sa.text(
       "SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")).first():
       raise RuntimeError("btree_gist yo'q — ops/db/init/00-extensions.sql superuser bilan bajarilsin")
   ```
2. `GRANT CREATE ON DATABASE <db> TO sbozor_owner` (o'lchandi: shundan keyin owner kengaytmani muvaffaqiyatli o'rnatdi va `extowner = sbozor_owner` bo'ldi). **Kamchiligi:** owner baza darajasida sxema yaratish huquqini oladi — imtiyoz kengayishi.
**Ogohlantirish belgilari:** CI'da migratsiya `permission denied to create extension` bilan yiqiladi; lokalda ishlagani uchun (dev superuser) sezilmaydi.

### Pitfall 2: Alembic `ExcludeConstraint` ni KO'RMAYDI (VERIFIED)

**Nima buziladi:** `alembic revision --autogenerate` exclusion konstraytini **hech qachon generatsiya qilmaydi**, va u bazadan yo'qolsa ham **drift ko'rsatmaydi**.
**Empirik o'lchov (Alembic 1.18.5 + SQLAlchemy 2.0.51, `compare_metadata()`):**

| Holat | `diff` elementlari |
|-------|--------------------|
| Model va DB **aynan bir xil** | **0** ✓ (soxta drift yo'q — bu yaxshi) |
| `ExcludeConstraint` model'dan **olib tashlandi** | **0** ❌ (drift SEZILMAYDI) |

**Qanday oldini olish:**
1. Konstraytni migratsiyada **aniq yozing** (`op.create_table(..., postgresql.ExcludeConstraint(...))` yoki `op.execute("ALTER TABLE ... ADD CONSTRAINT ... EXCLUDE USING gist (...)")`)
2. **Meta-test darvozasi majburiy** — `tests/tenancy/test_market_domain_meta.py`:
   ```python
   def test_stall_assignments_has_exclusion_constraint(sync_app_conn, migrated) -> None:
       row = sync_app_conn.execute(
           "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
           "WHERE conname = 'ex_stall_assignments_no_overlap'").fetchone()
       assert row is not None, "EXCLUDE konstrayti yo'q — Alembic buni SEZMAYDI"
       assert "EXCLUDE USING gist" in row[0] and "market_id" in row[0] and "&&" in row[0]
   ```
**Ogohlantirish belgilari:** yo'q — bu aynan shu qopqonning xavfi. Faqat maxsus test ushlaydi.

### Pitfall 3: `FINANCIAL_TABLES` reyestri `stall_assignments` da yiqiladi (VERIFIED — kod o'qildi)

**Nima buziladi:** `stall_assignments` jadvali yaratilgan kuni `tests/tenancy/test_meta.py::test_financial_tables_have_guards` qizaradi:
```
stall_assignments: `CHECK (amount_soum > 0)` yo'q
```
**Nega:** `sbozor_core/schema_contract.py:49-57` da `FINANCIAL_TABLES` ichida `stall_assignments` bor, meta-test esa ro'yxatdagi har bir MAVJUD jadvaldan uchta narsani talab qiladi: `business_date` STORED generated · `CHECK (amount_soum > 0)` · `market_id` bilan boshlanadigan UNIQUE. Biriktirish jadvalida pul ustuni **yo'q va bo'lmasligi ham kerak** (D-10: qarz `daily_charges` da).
**Qanday oldini olish (Wave 0, birinchi migratsiyadan OLDIN):**
- `FINANCIAL_TABLES` dan `stall_assignments` ni **olib tashlash** va sababni docstringda yozish
- Uning o'rniga `AUDITED_TABLES` ga qo'shish (D-10 aynan **audit** ni talab qiladi, pul konstraytini emas)
- `tariffs` esa `FINANCIAL_TABLES` da **qoladi** (unda haqiqiy pul bor), lekin qo'riqchilari `financial_guards()` bilan emas, qo'lda yoziladi (Anti-Patterns)
**Ogohlantirish belgilari:** `test_financial_tables_have_guards` "vakuum" testdan haqiqiy darvozaga aylanadi va faza o'rtasida qizaradi.

### Pitfall 4: RLS `UNIQUE`/`EXCLUDE` xatosining `DETAIL` ini o'chiradi (VERIFIED)

**Nima buziladi:** D-14 "88-qator: 12 raqami takrorlangan" xabarini DB xatosidan olishga urinish. RLS yoqilgan jadvalda PostgreSQL kalit qiymatlarini **butunlay yashiradi**:
```
-- RLS'siz (odatdagi kutish):
ERROR:  duplicate key value violates unique constraint "uq_stalls_market_id_code"
DETAIL:  Key (market_id, code)=(1111..., 12) already exists.

-- RLS yoqilgan (o'lchandi — HAM app-rol, HAM ega uchun):
ERROR:  duplicate key value violates unique constraint "uq_stalls_market_id_code"
        (DETAIL qatori UMUMAN YO'Q)
```
EXCLUDE uchun ham xuddi shunday: `DETAIL: Key conflicts with existing key.` — qiymatlarsiz.
**Nega:** Postgres RLS faol bo'lgan jadvalda konstrayt buzilishining tafsilotini oshkor qilmaydi (ko'rinmaydigan qator haqida ma'lumot sizib chiqmasligi uchun). Bu **xavfsizlik uchun to'g'ri**, lekin xato xabarini DB'dan olish yo'lini yopadi.
**Qanday oldini olish:** import **butun validatsiyani yozishdan OLDIN ilovada** bajaradi (fayl ichidagi dublikatlar, bazadagi mavjud kodlar, zona/toifa nomlari, telefon formati) va faqat toza ma'lumotni yozadi. DB konstrayti — ikkinchi qatlam (race himoyasi), foydalanuvchi xabarining manbai emas.
**Ogohlantirish belgilari:** import xatosi "duplicate key value violates unique constraint" degan xom matn bilan foydalanuvchiga chiqadi.

### Pitfall 5: Import faylining ikkita hujum yuzasi

**Nima buziladi:**
- **Billion laughs / quadratic blowup** — `.xlsx` ichidagi XML entity kengaytmasi bilan xotira portlashi. openpyxl **standart holatda himoyalanmagan** [CITED: openpyxl docs].
- **ZIP bomba** — `.xlsx` — bu ZIP. 1 MB fayl 10 GB ga ochilishi mumkin. `defusedxml` bunga **yordam bermaydi** (u faqat XML).
**Qanday oldini olish — parse qilishdan OLDIN, tartib bilan:**
```python
MAX_UPLOAD_BYTES        = 5 * 1024 * 1024      # 5 MB
MAX_UNCOMPRESSED_BYTES  = 50 * 1024 * 1024     # 50 MB
MAX_ROWS, MAX_COLS, MAX_SHEETS = 5_000, 32, 8

if len(raw) > MAX_UPLOAD_BYTES: reject("file_too_large")
with zipfile.ZipFile(io.BytesIO(raw)) as zf:                 # ZIP bombasi darvozasi
    if sum(i.file_size for i in zf.infolist()) > MAX_UNCOMPRESSED_BYTES: reject("file_too_large")
    if len(zf.infolist()) > 200: reject("file_too_complex")
wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)  # defusedxml faol
```
`data_only=True` — formula matnini emas, hisoblangan qiymatni oladi. `read_only=True` — lazy loading, doimiy xotira.
**Ogohlantirish belgilari:** core-api konteyneri import paytida OOM bilan qayta ishga tushadi.

### Pitfall 6: Platforma admini o'zi qurgan bozorga rasta kirita olmaydi (VERIFIED — kod o'qildi)

**Nima buziladi:** MARKET-01 ("platforma admini ustadan o'tib bozor yaratadi") bajarilmaydi — `POST /api/v1/stalls` 403 qaytaradi.
**Nega:** `services/core-api/app/security/rbac.py:71-79` — `Role.PLATFORM_ADMIN` da `MARKET_VIEW_ALL`, `MARKET_MANAGE`, `USER_MANAGE`, `USER_VIEW`, `AUDIT_VIEW` bor, **lekin `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE` yo'q** (ular faqat `MARKET_ADMIN` da).
**Qanday oldini olish (Wave 0):** `ROLE_PERMISSIONS[Role.PLATFORM_ADMIN]` ga uchtasini qo'shish. `tests/unit/test_rbac_matrix.py` buni **bloklamaydi** — u faqat `DIRECTOR` da bu uchtasi yo'qligini qulflaydi (`test_director_cannot_manage`) va `MARKET_VIEW_ALL` faqat platforma adminida ekanini. Ya'ni o'zgarish mavjud testlarni buzmaydi, lekin **yangi test** qo'shilishi kerak: "platforma admini usta qadamlarining hammasini bajara oladi".
**Ogohlantirish belgilari:** usta 3-qadamda 403 bilan to'xtaydi va sabab RBAC matritsasida ko'rinmaydi (endpoint kodi to'g'ri ko'rinadi).

### Pitfall 7: Qoralama bozor mahsulot oqimlariga sizib chiqadi

**Nima buziladi:** `is_active=false` bozor bozor tanlash ro'yxatida oddiy bozor kabi ko'rinadi; kelajakda billing job uni ham qamrab oladi va tarifsiz rastalar ustidan anomaliya to'foni chiqaradi.
**Qanday oldini olish:** (1) `auth_list_markets()` allaqachon `is_active` ni qaytaradi — frontend uni "chala — davom ettirish" holatida ko'rsatadi; (2) `activate` endpointi serverda to'liqlik tekshiruvi qiladi; (3) 6-faza kontrakti hujjatlashtiriladi: kunlik job `WHERE m.is_active`; (4) qoralamani o'chirish yo'li beriladi.
**Ogohlantirish belgilari:** bozor ro'yxatida nomi bor, ichida hech narsa yo'q bozorlar to'planadi.

### Pitfall 8: Xarita har bosishda 1000 katakni qayta render qiladi

**Nima buziladi:** tanlangan rasta ID'si katak propiga tushsa (`<Cell selected={id === selectedId}>`), har bosishda butun grid qayta render bo'ladi — 21 ms → sezilarli kechikish, mobil qurilmada yomonroq.
**Qanday oldini olish:** tanlangan ID **faqat dialogda**; katak `React.memo` bilan va `onSelect` `useCallback` bilan barqaror; tanlash ko'rsatkichi kerak bo'lsa CSS (`:focus-visible`) bilan.
**Ogohlantirish belgilari:** React DevTools Profiler'da har bosishda 1000 komponent yonadi.

### Pitfall 9: `valid_from` uchun ikkinchi haqiqat manbai

**Nima buziladi:** UI qulayligi uchun `tariffs` ga `valid_to` ustuni qo'shiladi ("ko'rsatish oson bo'lsin") va u keyingi qatorning `valid_from` i bilan ajralib ketadi.
**Qanday oldini olish:** `valid_to` **saqlanmaydi**. Ko'rsatish uchun so'rovda hisoblanadi:
```sql
SELECT valid_from,
       LEAD(valid_from) OVER (PARTITION BY market_id, category_id ORDER BY valid_from) AS valid_to,
       amount_soum
FROM tariffs WHERE market_id = :m AND category_id = :c ORDER BY valid_from DESC;
```
**Ogohlantirish belgilari:** "tarif oxiri" ustuni bilan "keyingi tarif boshi" mos kelmaydigan qator paydo bo'ladi.

### Pitfall 10: `[)` chegara konventsiyasi hujjatlashtirilmagan

**Nima buziladi:** biri `daterange(a, b, '[]')` yozadi, ikkinchisi `'[)'` — almashinuv kunida ikkita sotuvchi bir vaqtda biriktirilgan bo'lib chiqadi (yoki EXCLUDE ni yiqitadi).
**Qanday oldini olish:** loyihada **YAGONA** konventsiya: `'[)'` — quyi chegara kiradi, yuqori chegara kirmaydi. Bitta yordamchi:
```python
def assignment_period(start: date, end: date | None) -> Range[date]:
    """`[start, end)` — end KUNI YANGI sotuvchiga tegishli (D-10)."""
    return Range(start, end, bounds="[)")
```
`CHECK (lower(period) IS NOT NULL)` — quyi chegarasiz davr yozib bo'lmaydi. Yozish yo'lida `daterange` xom qurilmaydi.
**Ogohlantirish belgilari:** almashinuv kuni ikki sotuvchiga hisob yoziladi (6-fazada).

---

## Code Examples

### 1. Migratsiya — EXCLUDE konstraytli jadval (kengaytma tekshiruvi bilan)

```python
# migrations/versions/0008_vendors.py
from sqlalchemy.dialects import postgresql

def upgrade() -> None:
    conn = op.get_bind()
    if not conn.execute(sa.text(
            "SELECT 1 FROM pg_extension WHERE extname = 'btree_gist'")).first():
        raise RuntimeError(
            "btree_gist kengaytmasi yo'q. `sbozor_owner` uni O'ZI o'rnata olmaydi "
            "(permission denied) — ops/db/init/00-extensions.sql superuser bilan bajarilsin."
        )

    op.create_table(
        "stall_assignments",
        sa.Column("id", PgUuid(as_uuid=True), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("market_id", PgUuid(as_uuid=True), nullable=False),
        sa.Column("stall_id",  PgUuid(as_uuid=True), nullable=False),
        sa.Column("vendor_id", PgUuid(as_uuid=True), nullable=False),
        sa.Column("period", postgresql.DATERANGE(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stall_assignments"),
        sa.UniqueConstraint("market_id", "id", name="uq_stall_assignments_market_id_id"),
        sa.ForeignKeyConstraint(["market_id", "stall_id"], ["stalls.market_id", "stalls.id"],
                                name="fk_stall_assignments_market_id_stall_id_stalls"),
        sa.ForeignKeyConstraint(["market_id", "vendor_id"], ["vendors.market_id", "vendors.id"],
                                name="fk_stall_assignments_market_id_vendor_id_vendors"),
        sa.CheckConstraint("lower(period) IS NOT NULL",
                           name="ck_stall_assignments_lower_bound_required"),
        # Alembic buni AVTOGENERATSIYA QILMAYDI (empirik) — shuning uchun bu yerda ANIQ:
        postgresql.ExcludeConstraint(
            ("market_id", "="), ("stall_id", "="), ("period", "&&"),
            name="ex_stall_assignments_no_overlap", using="gist",
        ),
    )
    enable_tenant_rls("stall_assignments")
    create_entity(tenant_policy("stall_assignments"))
    create_entity(owner_bootstrap_policy("stall_assignments"))
    attach_audit_trigger("stall_assignments")        # D-10
```

### 2. Tarif qo'shish — eski qatorga TEGILMAYDI (D-06)

```python
async def add_tariff(session: AsyncSession, *, market_id: UUID, category_id: UUID,
                     amount_soum: int, valid_from: date) -> UUID:
    """D-06: YANGI qator. Hech qanday UPDATE yo'q — eski narx daxlsiz qoladi."""
    if valid_from <= business_today():          # sbozor_core.timeutil
        raise HTTPException(422, detail="valid_from_must_be_future")   # D-07
    try:
        row = await session.execute(
            insert(Tariff)
            .values(market_id=market_id, category_id=category_id,
                    amount_soum=amount_soum, valid_from=valid_from)
            .returning(Tariff.id)
        )
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise HTTPException(409, detail="tariff_already_set_for_date") from exc
        raise
    return row.scalar_one()
```

### 3. Import — validatsiya yozishdan OLDIN (D-14)

```python
@dataclass(frozen=True)
class ImportError_:
    row: int          # Excel qator raqami (sarlavha = 1)
    code: str         # mashina uchun: "zone_not_found" | "duplicate_code" | ...
    message: str      # foydalanuvchi uchun (i18n kaliti + parametrlar)

async def validate_stall_rows(session, market_id, rows) -> list[ImportError_]:
    """RLS DB xatosining DETAIL ini o'chiradi (empirik) — validatsiya SHU YERDA."""
    zones      = await load_names(session, Zone, market_id)             # {name: id}
    categories = await load_names(session, StallCategory, market_id)
    existing   = await load_codes(session, market_id)                   # {code}
    errors, seen = [], {}

    for r in rows:
        if r.code in seen:
            errors.append(ImportError_(r.row, "duplicate_code_in_file",
                f"{r.row}-qator: {r.code} raqami {seen[r.code]}-qatorda ham bor"))
        seen.setdefault(r.code, r.row)
        if r.zone_name not in zones:
            errors.append(ImportError_(r.row, "zone_not_found",
                f"{r.row}-qator: '{r.zone_name}' zonasi topilmadi"))
        if r.category_name not in categories:
            errors.append(ImportError_(r.row, "category_not_found",
                f"{r.row}-qator: '{r.category_name}' toifasi topilmadi"))
    return errors
    # D-15: `existing` dagi kodlar XATO EMAS — ular yozishda `ON CONFLICT DO NOTHING`
    #        bilan jimgina o'tkazib yuboriladi va javobda `skipped` sifatida sanaladi.
```

```python
# Yozish — BITTA tranzaksiya (D-14). O'lchandi: 1000 qator = 9 ms, qayta import = 6 ms.
async with session.begin():
    result = await session.execute(
        pg_insert(Stall).values(payload)
        .on_conflict_do_nothing(index_elements=["market_id", "code"])
        .returning(Stall.id)
    )
    inserted = result.scalars().all()
    await session.execute(insert(StallCategoryPeriod), category_rows_for(inserted))
```

### 4. Ish kuni tekshiruvi — 6-faza kontrakti

```python
IS_OPEN = text("SELECT market_is_open(:market_id, :business_date)")

async def market_is_open(session: AsyncSession, market_id: UUID, day: date) -> bool:
    """D-17/D-18. Sozlama yo'q bo'lsa -> False (fail-closed, empirik tasdiqlangan)."""
    return bool((await session.execute(
        IS_OPEN, {"market_id": market_id, "business_date": day})).scalar_one())
```

### 5. Zod kontrakti — usta qadami (frontend)

```ts
// frontend/src/lib/api-types.ts
export const marketRequisitesSchema = z.object({
  name: z.string().trim().min(2).max(120),
  timezone: z.literal('Asia/Tashkent'),          // MVP: bitta mintaqa
  operating_since: z.string().date(),            // barcha boshlang'ich valid_from shu sanadan
  address: z.string().trim().max(300).optional(),
  // STIR — 9 raqam (O'zbekiston soliq to'lovchi identifikatsiya raqami)
  tin: z.string().regex(/^\d{9}$/, 'stir_must_be_9_digits').optional(),
  bank_account: z.string().trim().max(30).optional(),
  bank_mfo: z.string().regex(/^\d{5}$/).optional(),
  contact_phone: z.string().trim().max(20).optional(),
});

export const tariffCreateSchema = z.object({
  category_id: z.uuid(),
  amount_soum: z.int().positive().max(9_007_199_254_740_991),   // JS xavfsiz chegarasi
  valid_from: z.string().date(),
});
```

### 6. RBAC kengaytmasi (Wave 0)

```python
# services/core-api/app/security/rbac.py
class Permission(StrEnum):
    ...
    MARKET_DATA_VIEW = "market_data_view"   # YANGI: zona/toifa/rasta/tarif/kalendar O'QISH
    VENDOR_VIEW      = "vendor_view"        # YANGI: sotuvchi (SHAXSIY MA'LUMOT) — D-09 auditli

ROLE_PERMISSIONS = {
    Role.PLATFORM_ADMIN: frozenset({
        Permission.MARKET_VIEW_ALL, Permission.MARKET_MANAGE,
        Permission.USER_MANAGE, Permission.USER_VIEW, Permission.AUDIT_VIEW,
        # MARKET-01: usta qadamlarini bajarish uchun MAJBURIY (Pitfall 6)
        Permission.STALL_MANAGE, Permission.TARIFF_MANAGE, Permission.VENDOR_MANAGE,
        Permission.MARKET_DATA_VIEW, Permission.VENDOR_VIEW,
    }),
    Role.DIRECTOR: frozenset({
        Permission.REPORT_VIEW, Permission.AUDIT_VIEW, Permission.CAMERA_VIEW,
        Permission.DISPUTE_DECIDE, Permission.USER_VIEW,
        # D-07: FAQAT ko'rish — *_MANAGE qo'shilmaydi (test_director_cannot_manage qulflaydi)
        Permission.MARKET_DATA_VIEW, Permission.VENDOR_VIEW,
    }),
    Role.MARKET_ADMIN: frozenset({... , Permission.MARKET_DATA_VIEW, Permission.VENDOR_VIEW}),
    Role.CASHIER:   frozenset({Permission.PAYMENT_CREATE}),      # 6-fazada kengayadi
    Role.INSPECTOR: frozenset({Permission.OCCUPANCY_REVIEW}),    # 5-fazada kengayadi
}
```

---

## State of the Art

| Eski yondashuv | Joriy yondashuv | Qachon o'zgargan | Ta'siri |
|----------------|-----------------|------------------|---------|
| `valid_from`/`valid_to` juft ustunlari + ilova tekshiruvi | `daterange` + `EXCLUDE USING gist` (qoplanish bo'lmasligi kerak bo'lganda) | PG 9.0 (2010), `btree_gist` bilan birga | Qoplanish DB kafolati bo'ladi; ammo "eski qator o'zgarmaydi" talabi bo'lsa **voris modeli** afzal |
| Bitemporal / SQL:2011 `SYSTEM VERSIONING` | PostgreSQL'da hali **yo'q** (`temporal_tables` kengaytmasi yoki qo'lda) | — | PG 18 da ham system-versioned jadval yo'q; audit-trigger + voris modeli amaldagi yechim |
| `uuid_generate_v4()` (uuid-ossp) | **`uuidv7()`** — PG 18 native | PG 18 (2025) | Kengaytma kerak emas; vaqt-tartiblangan → B-tree fragmentatsiyasi kam. 1-fazada allaqachon ishlatilgan |
| `openpyxl` yagona xlsx o'quvchi | `python-calamine` (Rust) tezroq va XML-hujum immun | 2023→ (0.8.2, 2026-07) | Alternativa mavjud; openpyxl hamon standart va CLAUDE.md tanlovi |
| Ko'p qadamli forma = klient store | Server-tomon qoralama + URL qadami | RSC/App Router davri | Sahifa yangilash xavfsiz; yangi kutubxona kerak emas |

**Deprecated / eskirgan:**
- **`middleware.ts`** Next 16 da → `proxy.ts` (1-fazada allaqachon to'g'ri)
- **`openpyxl` `use_iterators=True`** → `read_only=True`
- **`sa.Column(...)` deklarativ uslub** → `Mapped[...]` + `mapped_column(...)` (SQLAlchemy 2.0; 1-fazada allaqachon)

---

## Assumptions Log

| # | Da'vo | Bo'lim | Xato bo'lsa oqibati |
|---|-------|--------|---------------------|
| A1 | Bozor rekvizitlari to'plami (nom, manzil, STIR, bank hisob raqami, MFO, aloqa telefoni) Karmana uchun yetarli | Code Example 5 | Kvitansiya/hisobotda majburiy maydon yetishmaydi → keyinchalik migratsiya. **Phase 0 ning buyurtmachi savollari bilan tasdiqlansin** |
| A2 | STIR — 9 raqam (oxirgisi nazorat raqami) | Code Example 5 | Validatsiya haqiqiy raqamlarni rad etadi. Qidiruv natijasi (gov.uz manbalari) asosida, rasmiy hujjat bevosita o'qilmadi |
| A3 | `market_profile.operating_since` — bozorning tizimdagi ish boshlash sanasi; barcha boshlang'ich `valid_from` shundan olinadi | Pattern 3 | O'tmishga hisob qayta hisoblanganda tarifsiz davr chiqadi (D-08 anomaliyalari to'foni) |
| A4 | Rasta holatlari: `active` / `maintenance` / `closed`; `closed` va `maintenance` rastalarga hisob yozilmaydi | Pattern 1 | 6-faza billing filtri noto'g'ri bo'ladi. CONTEXT.md buni "Claude's Discretion" ga qo'ygan — **discuss-phase tasdig'i foydali** |
| A5 | Bozor admini (platforma admini emas) ish kunlari kalendarini o'zgartira oladi (MARKET-05 "Bozor admini …" matni) | Pattern 7 / RBAC | Yopiq kun belgilash — tushumni nolga tushiruvchi amal; noto'g'ri rolda bo'lsa nazorat teshigi |
| A6 | Import shabloni ustunlari: rasta uchun `kod, zona, toifa, holat, izoh`; sotuvchi uchun `F.I.Sh., telefon, rasta kodi, boshlanish sanasi` | Architecture Diagram | Karmananing mavjud ro'yxati boshqa ustunlarda bo'lsa qayta ishlash kerak |
| A7 | Import chegaralari (5 MB fayl / 50 MB ochilgan / 5000 qator / 8 varaq) real ehtiyoj uchun yetarli | Pitfall 5 | 1000 rastadan kattaroq bozor kelganda chegaraga urilinadi (sozlanadigan qilinsin) |
| A8 | Kassir/nazoratchi 2-fazada rasta reestrini ko'rmaydi (`MARKET_DATA_VIEW` berilmaydi) | Code Example 6 | 5–6 fazalarda matritsa yana kengayadi (bu kutilgan, muammo emas) |
| A9 | `defusedxml` 0.7.1 (2021) Python 3.13 da openpyxl bilan hamon to'g'ri ishlaydi | Standard Stack | Import himoyasi jimgina ishlamaydi. **Reja Wave 0 da bitta smoke-test bilan tekshirsin** (billion-laughs namunasi rad etilishi) |
| A10 | Qoralama bozorni o'chirish (`DELETE`) kerak bo'ladi | Pattern 5 | Tashlab ketilgan qoralamalar to'planadi (funksional emas, tozalik masalasi) |

---

## Open Questions

1. **`btree_gist` init qadami qayerga qo'yiladi?**
   - Bilamiz: `sbozor_owner` uni o'rnata olmaydi (empirik); superuser init yoki `GRANT CREATE ON DATABASE` kerak.
   - Noaniq: `tests/conftest.py` hozir faqat `ops/db/init/01-roles.sql` ni o'qiydi. Yangi `00-extensions.sql` qo'shilsa conftest ham o'zgaradi — bu 1-faza faylini o'zgartirish.
   - Tavsiya: `00-extensions.sql` + conftest o'zgarishi Wave 0 vazifasi bo'lsin (migratsiyalardan oldin). Muqobil (`GRANT CREATE ON DATABASE`) imtiyoz kengaytirgani uchun ikkinchi o'rinda.

2. **`stall_category_periods` haqiqatan kerakmi, yoki `stalls.category_id` yetarlimi?**
   - Bilamiz: D-04 "tarif tarixi bilan bir xil mexanizm" deb **qulflangan** → periods jadvali.
   - Noaniq: bu qo'shimcha jadval + har so'rovda LATERAL 2 hafta byudjetiga ta'sir qiladi.
   - Tavsiya: qulflangan qarorni bajarish. Agar reja byudjetdan chiqsa, **kesish nomzodi** sifatida `stalls.category_id` (tarixsiz) ni discuss-phase'ga qaytarish — lekin bu D-04 ni ochish demak, jimgina qilinmaydi.

3. **`defusedxml` yoki `python-calamine`?**
   - Bilamiz: openpyxl rasmiy hujjati `defusedxml` ni talab qiladi; `defusedxml` oxirgi relizi 2021-03-08; `python-calamine` Rust bo'lgani uchun bu sinf hujumlariga strukturaviy immun va faol (2026-07-13).
   - Noaniq: `defusedxml` 0.7.1 Python 3.13 + openpyxl 3.1.5 bilan hozir ham to'g'ri ulanadimi.
   - Tavsiya: `openpyxl + defusedxml` bilan boshlash (CONTEXT.md yo'nalishi) **va Wave 0 da billion-laughs smoke-testi yozish**. Test qizarsa — `python-calamine` ga o'tish (allaqachon tekshirilgan, cp313 g'ildiragi bor).

4. **Kim ish kunlari kalendarini o'zgartiradi?**
   - Bilamiz: MARKET-05 "Bozor admini" deydi; yopiq kun belgilash tushumni nolga tushiruvchi amal va `market_calendar_exceptions` DB-trigger auditi ostida bo'ladi.
   - Noaniq: nazorat nuqtai nazaridan bu direktor tasdig'ini talab qiladimi (1-faza "maker-checker" ni v2 ga qoldirgan).
   - Tavsiya: MVP'da bozor admini + majburiy audit; 8-fazada "ketma-ket N yopiq kun" hisoboti.

5. **Zona nomi tahrirlanganda import fayllari eskiradimi?**
   - Bilamiz: import zonani **nom bo'yicha** topadi (admin uchun qulay).
   - Noaniq: zona nomi o'zgargach eski fayl "zona topilmadi" beradi.
   - Tavsiya: shablon faylida zona ro'yxatini alohida (yashirin) varaqda va data-validation ro'yxati sifatida berish — XlsxWriter buni qo'llab-quvvatlaydi.

---

## Environment Availability

| Bog'liqlik | Kim talab qiladi | Mavjud | Versiya | Fallback |
|------------|------------------|--------|---------|----------|
| Docker | testcontainers, compose steki | ✓ | 29.4.2 | — |
| `postgres:18.4-trixie` | barcha DB testlari | ✓ | 18.4 (ishga tushirildi) | — |
| `btree_gist` kengaytmasi | `stall_assignments` EXCLUDE | ✓ (image ichida 1.8) | 1.8 | **superuser init kerak** (Pitfall 1) |
| Node / npm | frontend | ✓ | npm 11.11.0 | — |
| Python + pip | paket tekshiruvi | ✓ | pip 25.3 | — |
| `slopcheck` | paket legitimligi | ✓ | mavjud (`-e pypi` majburiy) | — |
| `uv` | per-service deps | konteyner ichida | 0.11.33 (compose) | — |
| `ctx7` CLI / Context7 MCP | kutubxona hujjatlari | ✗ | — | WebFetch + rasmiy docs (ishlatildi) |
| Brave / Exa / Firecrawl | qidiruv | ✗ (config: false) | — | Built-in WebSearch (ishlatildi) |

**Fallback'siz yetishmayotgan bog'liqliklar:** yo'q.
**Fallback bilan yetishmayotganlar:** `ctx7` — rasmiy hujjatlar to'g'ridan-to'g'ri o'qildi (openpyxl Security, SQLAlchemy PostgreSQL dialekti), va kritik API'lar **o'rnatilgan paketda kod bilan tekshirildi** (SQLAlchemy 2.0.51 `Range`/`ExcludeConstraint` imzolari, Alembic 1.18.5 `compare_metadata`).

---

## Validation Architecture

### Test Framework

| Xususiyat | Qiymat |
|-----------|--------|
| Framework | `pytest 9.1.1` + `pytest-asyncio 1.4.0` (`asyncio_mode = "auto"`), `testcontainers 4.15.0` |
| Config fayl | `pyproject.toml` → `[tool.pytest.ini_options]` (`pythonpath = [".", "tests", "services/core-api"]`, marker: `tenancy`) |
| Baza | **`postgres:18.4-trixie`, `sbozor_app` roli bilan** — `tests/conftest.py`. SQLite TAQIQLANGAN |
| Frontend | `vitest 4.1.10` + `jsdom 30.0.1` + Testing Library; `node --test` skriptlar uchun |
| Quick run (backend unit) | `docker compose --profile test run --rm tests pytest tests/unit -x -q` |
| Quick run (tenancy darvozasi) | `npm run test:tenancy` |
| Full suite (backend) | `npm run test` → `docker compose --profile test run --rm tests pytest -q` |
| Full suite (frontend) | `npm --prefix frontend test` |
| Faza darvozasi | `npm run gate` (lint + mypy + backend + tenancy + i18n + typecheck + eslint + build) |

### Phase Requirements → Test Map

| Req / Mezon | Xulq-atvor (kuzatiladigan dalil) | Test turi | Avtomatik buyruq | Fayl bormi? |
|-------------|----------------------------------|-----------|------------------|-------------|
| **SC#1** / MARKET-01 | Platforma admini `POST /markets` → `select-market` → zona/toifa/tarif/rasta → `activate`; oxirida `is_active=true` va `can_activate` ilgari `false` bo'lgan | integration (API) | `pytest tests/integration/test_wizard_flow.py -x` | ❌ Wave 0 |
| SC#1 | Chala bozorni faollashtirishga urinish 409 + yetishmayotgan qadamlar ro'yxati | integration | `pytest tests/integration/test_wizard_flow.py::test_activate_rejects_incomplete_market -x` | ❌ Wave 0 |
| SC#1 / Pitfall 6 | Platforma admini usta qadamlarining **hammasini** bajara oladi (403 yo'q) | unit + integration | `pytest tests/unit/test_rbac_matrix.py::test_platform_admin_can_run_the_wizard -x` | ❌ Wave 0 |
| SC#1 / Pattern 6 | `sbozor_app` `markets` ga to'g'ridan-to'g'ri `INSERT` qila **olmaydi** | tenancy | `pytest tests/tenancy/test_market_domain_meta.py::test_app_role_cannot_insert_markets -x` | ❌ Wave 0 |
| **SC#2** / MARKET-02 | Rasta holati `active→maintenance→closed` o'zgaradi va har o'zgarish `audit_log` da `old→new` bilan ko'rinadi | integration | `pytest tests/integration/test_stall_registry.py -x` | ❌ Wave 0 |
| SC#2 / D-10 | **Xom SQL** bilan `UPDATE stalls SET status=...` ham audit qatorini hosil qiladi | integration | `pytest tests/integration/test_stall_registry.py::test_raw_sql_update_is_audited -x` | ❌ Wave 0 |
| SC#2 / D-02 | Yopilgan rastaning kodini yangi rastaga berishga urinish **rad etiladi** | integration | `pytest tests/integration/test_stall_code_reuse.py -x` | ❌ Wave 0 |
| SC#2 / D-02 | Rasta kodini tahrirlash **ruxsat etiladi** va audit qoldiradi | integration | `pytest tests/integration/test_stall_code_reuse.py::test_code_edit_is_allowed_and_audited -x` | ❌ Wave 0 |
| **SC#3** / MARKET-03 | `valid_from=2026-09-01` qo'shilgach: `2026-08-31` → eski narx, `2026-09-01` → yangi narx, `2026-08-31` qayta so'ralganda **hamon eski narx** | integration (real PG) | `pytest tests/integration/test_tariff_history.py::test_past_date_keeps_old_price -x` | ❌ Wave 0 |
| SC#3 chegara | **Aynan kuchga kirgan kun** (`valid_from` ning o'zi) yangi narxni beradi | integration | `...::test_effective_day_uses_new_price -x` | ❌ Wave 0 |
| SC#3 chegara | Birinchi tarifdan **oldingi** sana → 0 qator (D-08 fail-closed) | integration | `...::test_before_first_tariff_is_fail_closed -x` | ❌ Wave 0 |
| SC#3 / D-07 | O'tgan sanali tarif qatorini `UPDATE`/`DELETE` qilish — **ilova 403 VA xom SQL DB xatosi** | integration | `...::test_past_tariff_is_immutable_even_via_raw_sql -x` | ❌ Wave 0 |
| SC#3 / D-07 | Kelajakdagi tarif qatori tahrirlanadi va o'chiriladi | integration | `...::test_future_tariff_is_editable -x` | ❌ Wave 0 |
| SC#3 / D-06 | Yangi tarif qo'shilganda **eski qator qatori o'zgarmaydi** (`updated_at`/`amount_soum` bir xil) | integration | `...::test_existing_row_is_never_touched -x` | ❌ Wave 0 |
| **SC#4** / MARKET-05 | Dushanba yopiq bozorda `market_is_open(m, <dushanba>)` → `false`; istisno `is_open=true` qo'yilgan dushanba → `true`; bayram → `false` | integration | `pytest tests/integration/test_market_calendar.py -x` | ❌ Wave 0 |
| SC#4 fail-closed | Sozlamasi yo'q bozor / boshqa bozor konteksti → `false` | integration | `...::test_calendar_is_fail_closed -x` | ❌ Wave 0 |
| **SC#5** / MARKET-06 | Xarita zona bloklarini kod tartibida chizadi; rasta bosilganda dialog raqam/toifa/tarif/sotuvchi/holat bilan ochiladi | component (vitest+jsdom) | `npm --prefix frontend run test:component -- stall-map` | ❌ Wave 0 |
| SC#5 ishlash | 1000 katakli grid render bo'ladi va tanlash butun gridni qayta render qilmaydi | component | `...stall-map.test.tsx::renders 1000 cells without re-rendering on select` | ❌ Wave 0 |
| MARKET-04 / D-09 | Bir rastada qoplanadigan davr yozishga urinish → `409 assignment_period_overlaps` (SQLSTATE 23P01) | integration | `pytest tests/integration/test_stall_assignments.py::test_overlapping_period_is_rejected -x` | ❌ Wave 0 |
| MARKET-04 / D-10 | 10-sanada almashinuv: 9-kun eski sotuvchi, 10-kun yangi sotuvchi | integration | `...::test_handover_day_boundary -x` | ❌ Wave 0 |
| MARKET-04 / D-11 | Davrlar orasidagi bo'shliqda `period @> d` 0 qator | integration | `...::test_vacancy_gap_returns_no_vendor -x` | ❌ Wave 0 |
| MARKET-04 / D-12 | Bir bozorda takroriy telefon rad etiladi; boshqa bozorda bir xil telefon **qabul qilinadi** | integration | `pytest tests/integration/test_vendors.py::test_phone_is_unique_per_market -x` | ❌ Wave 0 |
| MARKET-04 / D-09 audit | `GET /api/v1/vendors` chaqiruvi `audit_log` ga `action='read', reason='vendor_view'` yozadi; **403 olgan so'rov yozmaydi** | integration | `pytest tests/integration/test_vendors.py::test_vendor_read_is_audited -x` | ❌ Wave 0 |
| D-13/D-14 | 3 xatoli fayl → 422, **javobda uchala xato qator raqami bilan**, bazada 0 yangi qator | integration | `pytest tests/integration/test_stall_import.py::test_all_or_nothing -x` | ❌ Wave 0 |
| D-15 | Bir xil faylni ikki marta yuklash → ikkinchisida `inserted=0, skipped=N`, mavjud qatorlar va ularning sotuvchi tarixi **o'zgarmagan** | integration | `...::test_reimport_is_idempotent -x` | ❌ Wave 0 |
| Pitfall 5 | Billion-laughs XML namunasi rad etiladi; zip-bomba hajm darvozasida rad etiladi | unit | `pytest tests/unit/test_xlsx_reader.py -x` | ❌ Wave 0 |
| Formula injection | Eksport qilingan shablon/hisobotda `=`,`+`,`-`,`@`,`\t`,`\r` bilan boshlanuvchi qiymat `'` bilan prefikslanadi | unit | `pytest tests/unit/test_xlsx_template.py::test_formula_injection_is_escaped -x` | ❌ Wave 0 |
| FOUND-02 (regressiya) | To'qqizta yangi jadvalning har birida `market_id` + RLS ENABLE+FORCE + tenant policy + `market_id` bilan boshlanuvchi indekslar | tenancy (**mavjud, avtomatik**) | `npm run test:tenancy` | ✅ `tests/tenancy/test_meta.py` |
| Pitfall 2 | `ex_stall_assignments_no_overlap` konstrayti bazada mavjud (Alembic buni sezmaydi) | tenancy | `pytest tests/tenancy/test_market_domain_meta.py::test_stall_assignments_has_exclusion_constraint -x` | ❌ Wave 0 |
| Pitfall 3 | `FINANCIAL_TABLES` / `AUDITED_TABLES` reyestrlari amaldagi sxema bilan mos | tenancy (**mavjud**) | `pytest tests/tenancy/test_meta.py::test_financial_tables_have_guards tests/tenancy/test_meta.py::test_audited_tables_have_trigger -x` | ✅ mavjud |
| Cross-tenant | Har yangi endpoint A tokeni bilan B obyektida **404** beradi; qamrab olinmagan marshrut CI'ni yiqitadi | tenancy (**mavjud, avtomatik**) | `pytest tests/tenancy/test_cross_tenant.py tests/tenancy/test_route_coverage.py -x` | ✅ mavjud (yangi marshrutlar qo'shiladi) |
| Migratsiya butunligi | `alembic upgrade head` → `alembic revision --autogenerate` **bo'sh diff** beradi | integration | mavjud CI qadami | ✅ mavjud |

### Sampling Rate

- **Har task commit'ida:** `docker compose --profile test run --rm tests pytest tests/unit -x -q` + o'zgargan modulning integration fayli
- **Har to'lqin (wave) birlashuvida:** `npm run test` + `npm run test:tenancy` + `npm --prefix frontend test`
- **Faza darvozasi:** `npm run gate` to'liq yashil, so'ng `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `sbozor_core/schema_contract.py` — `FINANCIAL_TABLES` dan `stall_assignments` olib tashlash (sabab izohi bilan); `AUDITED_TABLES` ni 6 jadvalga kengaytirish — **Pitfall 3**
- [ ] `services/core-api/app/security/rbac.py` — `PLATFORM_ADMIN` ga `STALL_MANAGE`/`TARIFF_MANAGE`/`VENDOR_MANAGE`; ikkita yangi `Permission` — **Pitfall 6**
- [ ] `ops/db/init/00-extensions.sql` + `tests/conftest.py` da o'qish — `btree_gist` — **Pitfall 1**
- [ ] `tests/fixtures/market_domain.py` — ikki bozor uchun zona/toifa/rasta/tarif/sotuvchi/biriktirish seed'i (`two_markets.py` ustiga)
- [ ] `tests/tenancy/test_market_domain_meta.py` — EXCLUDE konstrayti, `tariff_past_immutable` triggeri, `stall_code_claim` triggeri, `market_is_open` ning `SECURITY DEFINER` **emasligi**
- [ ] `tests/integration/test_{tariff_history,stall_assignments,market_calendar,stall_import,wizard_flow,stall_registry,stall_code_reuse,vendors}.py`
- [ ] `tests/unit/test_{xlsx_reader,xlsx_template}.py` — parser chegaralari, billion-laughs, formula injection
- [ ] `frontend/src/components/stalls/stall-map.test.tsx` — vitest+jsdom (infratuzilma 1-fazada tayyor)
- [ ] `tests/tenancy/test_route_coverage.py` — yangi marshrutlarni qamrovga qo'shish (aks holda CI qizaradi — bu **ataylab**)
- Framework o'rnatish: **kerak emas** — barcha vositalar 1-fazadan mavjud

---

## Security Domain

**ASVS darajasi:** L1 (`.planning/config.json` → `security_asvs_level: 1`, `security_block_on: "high"`)

### Applicable ASVS Categories

| ASVS toifasi | Qo'llanadimi | Standart nazorat (bu fazada) |
|--------------|--------------|------------------------------|
| V2 Authentication | qisman | 1-fazadan o'zgarishsiz; yangi auth yuzasi qo'shilmaydi |
| V3 Session Management | qisman | `POST /auth/select-market` qayta ishlatiladi (usta 2-qadami); yangi sessiya mexanizmi yo'q. ⚠ `01-REVIEW-GAPS.md` WR-02/WR-03 shu endpointga tegishli va **hali ochiq** |
| **V4 Access Control** | **ha** | RLS ENABLE+FORCE + `NULLIF(...)` policy · composite FK · `require_permission(...)` · cross-tenant marshrut matritsasi · 404 (403 emas) |
| **V5 Input Validation** | **ha** | `zod 4.4.3` (klient) + `pydantic 2.13.4` (server); Excel import uchun alohida chegaralar va tip-tekshiruvi |
| V6 Cryptography | yo'q | Bu fazada shifrlash yo'q (RTSP parollari — 3-faza) |
| V7 Error Handling & Logging | ha | `structlog` + `asgi-correlation-id`; DB konstrayt xatosi foydalanuvchiga xom holda **berilmaydi** |
| **V8 Data Protection** | **ha** | Sotuvchi telefoni — shaxsiy ma'lumot: RLS + `audit_read` (D-09) + `mask_sensitive` audit yozuvlarida |
| **V12 File Upload** | **ha** | Fayl hajmi, ochilgan hajm (zip-bomba), qator/ustun/varaq chegaralari, `defusedxml`, faqat `.xlsx` MIME/kengaytma |
| V13 API | ha | Keyset paginatsiya (OFFSET emas), aniq pydantic modellari (mass-assignment yo'q) |
| V14 Configuration | qisman | `btree_gist` init qadami; sirlar `.env` da (1-fazadan) |

### Known Threat Patterns for {FastAPI + PostgreSQL RLS + Next.js + Excel import}

| Naqsh | STRIDE | Standart mitigatsiya |
|-------|--------|----------------------|
| Boshqa bozorning rastasini/tarifini tahrirlash (`stall_id` ni almashtirish) | Tampering / Elevation | RLS `WITH CHECK` + composite FK `(market_id, stall_id)`; javob **404**. `test_cross_tenant.py` avtomatik qamraydi |
| Boshqa bozorning sotuvchisiga rasta biriktirish | Tampering | `fk_stall_assignments_market_id_vendor_id_vendors` composite FK — strukturaviy imkonsiz |
| **O'tmishdagi tarifni retroaktiv o'zgartirib qarzni yashirish** | Tampering / Repudiation | `tariff_past_immutable()` **DB triggeri** (xom SQL ham) + `fn_audit_row()` + ilova 403 |
| **Rasta raqamini qayta ishlatib tarixni chalkashtirish** | Tampering | `stall_code_registry` + `stall_code_claim()` triggeri (D-02) |
| **Yopiq kunni soxta belgilab kunlik yig'imni yashirish** | Tampering / Repudiation | `market_calendar_exceptions` DB-trigger auditi ostida; 8-fazada "ketma-ket yopiq kunlar" hisoboti |
| Sotuvchi biriktirish davrini orqaga surib qarzni boshqasiga o'tkazish | Tampering | `fn_audit_row()` `period` o'zgarishini `old→new` bilan yozadi (empirik tasdiqlangan: `changed_keys={period}`) |
| **XML billion laughs / quadratic blowup** (`.xlsx`) | DoS | `defusedxml` (openpyxl rasmiy talabi) |
| **ZIP bomba** (`.xlsx` = ZIP) | DoS | Ochilgan hajm `zf.infolist()` bilan parse'dan OLDIN tekshiriladi |
| Xotira portlashi (10⁶ qatorli varaq) | DoS | `read_only=True` + `MAX_ROWS`/`MAX_COLS`/`MAX_SHEETS` chegaralari |
| Uzoq tranzaksiya bilan jadval qulflash | DoS | Qator chegarasi + o'lchangan tezlik (1000 qator = 9 ms) |
| **CSV / formula injection** (eksport qilingan shablon va hisobotlar) | Tampering (mijoz mashinasida) | `=`,`+`,`-`,`@`,`\t`,`\r` bilan boshlanuvchi katakni `'` bilan prefikslash [CITED: OWASP CSV Injection] |
| Yarim yaratilgan (qoralama) bozordan foydalanish | Tampering | `is_active=false` + serverdagi `activate` to'liqlik tekshiruvi + 6-faza `WHERE m.is_active` kontrakti |
| Audit jurnalini chetlab o'tish (ORM'siz yozish) | Repudiation | `fn_audit_row()` **DB triggeri** oltita domen jadvalida (D-10) |
| Sotuvchi shaxsiy ma'lumotini izsiz o'qish | Information Disclosure | `Depends(audit_read("vendors", reason="vendor_view"))` — `require_permission` dan KEYIN e'lon qilinadi |
| Mass-assignment (`status`/`market_id` ni PATCH bilan o'zgartirish) | Elevation | Aniq pydantic request modellari; `market_id` **hech qachon** so'rov tanasidan olinmaydi — `principal.market_id` dan |
| SQL injection dinamik DDL/so'rovda | Tampering | `migrations/helpers.py::_ident()` darvozasi; `ruff --select S608` CI qadami (1-fazadan) |
| Rad etilgan so'rovning auditda "o'qidi" bo'lib ko'rinishi | Repudiation | Dependency e'lon tartibi + `BackgroundTasks` (1-faza `audit.py` da hujjatlashtirilgan) |

---

## Scope Fence — bu fazada QURILMAYDIGAN narsalar

| Narsa | Qaysi faza | Bu fazada nima qilinadi (arzon ilgak) |
|-------|-----------|----------------------------------------|
| Kamera qo'shish, RTSP, ulanish testi | 3-faza | **Hech narsa.** Usta oxirida "kamera bo'limi keyinroq" (D-16). `setup-status` javobida `"cameras": 0` maydoni — bitta kalit |
| Snapshot jadvali, mavsumiy profil | 4-faza | Hech narsa |
| Kamera-zona poligonlari | 5-faza | **Faqat `stalls.id` barqarorligi** (D-02) — allaqachon qilinadi. Poligon jadvali YO'Q |
| `daily_charges`, `payments`, kassir | 6-faza | **Faqat kontrakt:** `stalls(market_id, id)` composite unique (composite FK maqsadi uchun), `tariffs` lookup so'rovi, `market_is_open()`, `stall_assignments` — to'rttasi ham 6-fazada o'zgarishsiz ishlatiladi |
| Xarita ranglari: ko'k to'langan / qizil qarzdor / sariq nomuvofiq | 6–7 fazalar | **Faqat `tone` tipi kengaytiriladigan qilib e'lon qilinadi** (D-20). Rang mantiqi 2-fazada yozilmaydi |
| Rasta kartasida dalil-rasm | 6–7 fazalar | Karta komponentida `children` sloti — bitta prop |
| Sotuvchi qarzi va to'lov tarixi | 6–7 fazalar | Hech narsa. `vendors` da balans ustuni **YO'Q** (BILL-03: hisoblanadigan ko'rinish) |
| Telegram bot ulanishi | 7-faza | **Faqat `vendors.phone_e164` E.164 unique** (D-12) — allaqachon qilinadi |
| Excel hisobot eksporti (reestrlar) | 8-faza | `XlsxWriter` shu fazada import shabloni uchun keladi — 8-faza uni qayta ishlatadi |
| To'liq interaktiv xarita (rasm ustida belgilash) | v2 | Renderer kontrakti ajratiladi (Pattern 11) |
| Ko'p tilli DB kontenti | Qurilmaydi | 1-faza D-16 |
| Import orqali upsert / sinxronizatsiya | Qurilmaydi | D-15 |

**Erta optimizatsiya deb baholangan va QILINMAYDIGAN "ilgaklar":**
- `tariffs` ga `zone_id` ustuni "kelajak uchun" — deferred (D-05); migratsiya bilan qo'shiladi
- `stall_assignments` ga soatlik oraliq — deferred (D-09)
- Xarita koordinatalari uchun `x`/`y` ustunlari — deferred (D-19)
- `market_profile` da har bozor uchun mintaqa (`timezone`) — `markets.timezone` allaqachon bor, generated column'da literal ishlatiladi (1-faza cheklovi)
- Sozlanadigan permission tizimi — 1-faza deferred

---

## Sources

### Primary (HIGH confidence — o'zim o'lchadim yoki rasmiy manba)

- **Jonli `postgres:18.4-trixie` konteyneri** (2026-07-30, 21 ta o'lchov): `btree_gist` o'rnatish huquqi · EXCLUDE indeksining ustun tartibi · qoplanish/bo'shliq semantikasi · voris modeli EXPLAIN rejasi · RLS ostida `DETAIL` yo'qolishi · 1000 qatorli import vaqti · `market_is_open()` fail-closed xulqi · `to_jsonb(daterange)` audit yozuvi
- **SQLAlchemy 2.0.51 + asyncpg 0.31.0** (haqiqiy ulanish): `Range(lower, upper, *, bounds='[)', empty=False)` imzosi · `ExcludeConstraint(*elements, **kw)` · chiqarilgan DDL · `Range` round-trip · `.contains()` → `@>` · `ExclusionViolationError` SQLSTATE `23P01`
- **Alembic 1.18.5 `compare_metadata()`** (haqiqiy DB): `ExcludeConstraint` ikki tomonlama sezilmasligi (0 diff)
- `E:\bozor\migrations\helpers.py` — `enable_tenant_rls`, `attach_audit_trigger`, `financial_guards`, `BUSINESS_DATE_EXPR`
- `E:\bozor\migrations\entities\{__init__,policies,functions,triggers}.py` — `TENANT_TABLES`, `tenant_policy`, `owner_bootstrap_policy`, `AUTH_CREATE_USER` naqshi
- `E:\bozor\migrations\versions\0001_identity.py:106` — `grant_app_dml("markets", ops="SELECT")`
- `E:\bozor\packages\sbozor-core\sbozor_core\schema_contract.py:49-57` — `FINANCIAL_TABLES` mazmuni
- `E:\bozor\tests\tenancy\test_meta.py` — beshta invariant va `test_financial_tables_have_guards` mantig'i
- `E:\bozor\services\core-api\app\security\rbac.py:68-112` — `ROLE_PERMISSIONS` matritsasi
- `E:\bozor\services\core-api\app\api\v1\{auth,markets,users,audit}.py` — `select-market`, `_platform_admin_market`, keyset/audit naqshlari
- `E:\bozor\ops\db\init\01-roles.sql` — `sbozor_owner` NOCREATEDB
- `E:\bozor\tests\conftest.py`, `pyproject.toml`, `package.json`, `.github/workflows/` — test infratuzilmasi
- https://openpyxl.readthedocs.io/en/stable/ (Security) — *"By default openpyxl does not guard against quadratic blowup or billion laughs xml attacks. To guard against these attacks install defusedxml."*
- https://docs.sqlalchemy.org/en/20/dialects/postgresql.html — Range/DATERANGE/ExcludeConstraint
- PyPI JSON API — `openpyxl 3.1.5` (2024-06-28, MIT) · `XlsxWriter 3.2.9` (2025-09-16, BSD-2) · `defusedxml 0.7.1` (2021-03-08, PSFL) · `python-calamine 0.8.2` (2026-07-13, MIT, cp313 manylinux_2_17 g'ildiragi)
- npm registry — `react-konva 19.2.5` (peer: react ^19.2.0, konva ^10) · `konva 10.3.0`

### Secondary (MEDIUM confidence — tekshirilgan qidiruv natijasi)

- https://owasp.org/www-community/attacks/CSV_Injection — formula injection va `'` prefiksi tavsiyasi
- https://medium.com/@lavrton/how-to-optimise-rendering-of-a-set-of-elements-in-react-ad01f5b161ae — Anton Lavrenov (Konva muallifi): 1000 element ~21 ms, memo bilan ~4 ms, 16 ms kadr byudjeti

### Tertiary (LOW confidence — tasdiq talab qiladi)

- STIR = 9 raqam (oxirgisi nazorat raqami) — my.gov.uz / oldmy.gov.uz qidiruv natijalari asosida; rasmiy me'yoriy hujjat bevosita o'qilmadi → **A2 taxmini**
- `defusedxml` 0.7.1 ning Python 3.13 + openpyxl 3.1.5 bilan amaldagi samaradorligi — hujjat asosida kutiladi, **o'lchanmadi** → **A9 taxmini**, Wave 0 smoke-testi bilan yopiladi

---

## Metadata

**Confidence breakdown:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Temporal ma'lumot modeli (tarif / biriktirish) | **HIGH** | Ikkala model ham jonli `postgres:18.4` da qurildi va D-06…D-11 stsenariylari o'lchandi; EXPLAIN rejalari olindi |
| 1-fazadan meros naqshlar va darvozalar | **HIGH** | Kod fayl-fayl o'qildi; `FINANCIAL_TABLES` va RBAC minalari test mantig'idan bevosita chiqarildi |
| `btree_gist` / Alembic / RLS `DETAIL` topilmalari | **HIGH** | Uchalasi ham empirik reproduktsiya bilan |
| Import (openpyxl + xavfsizlik) | **MEDIUM-HIGH** | Kutubxona tanlovi va xavfsizlik talabi rasmiy hujjatdan; parser xulqi bu sessiyada ishga tushirilmadi |
| Usta (wizard) arxitekturasi | **MEDIUM-HIGH** | Mavjud `select-market` / `markets` GRANT mexanikasi tekshirildi; oqimning o'zi hali qurilmagan |
| Plan-xarita ishlashi | **MEDIUM** | Tashqi benchmark (Konva muallifi) + arxitektura mulohazasi; 1000 katakli render bu sessiyada brauzerda o'lchanmadi |
| Bozor rekvizitlari va STIR formati | **LOW** | Assumptions Log A1/A2 — buyurtmachi tasdig'i kerak |

**Research date:** 2026-07-30
**Valid until:** 2026-08-29 (30 kun — stek qulflangan va tez o'zgarmaydi; `python-calamine` bundan mustasno, u faol reliz siklida)
