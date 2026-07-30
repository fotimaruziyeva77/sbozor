# Phase 2: Bozor domeni va "Yangi bozor" ustasi - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Platforma admini kod yozmasdan yangi bozorni tizimga kiritadi (usta orqali), bozor admini rasta / toifa / tarif / sotuvchi / ish-kunlari reestrini yuritadi, va sxematik plan-xarita rastalarni zona bo'yicha ko'rsatadi. **Karmananing real ma'lumoti aynan shu fazada tizimga kiradi** — keyingi fazalar fikstura emas, haqiqat ustida sinaladi.

Qamrovda: MARKET-01 … MARKET-06.

Qamrovdan tashqarida (boshqa fazalar): kamera qo'shish va ulanish testi (3-faza), snapshot jadvali (4-faza), kamera-zona poligonlari (5-faza), xaritaning to'lov/qarz/nomuvofiqlik ranglari va dalil-rasm (6–7 fazalar).

</domain>

<decisions>
## Implementation Decisions

### Rasta identifikatsiyasi va tuzilishi

- **D-01:** Rasta raqami — **bozor bo'yicha yagona** (butun bozorda takrorlanmaydi: 1, 2, 3 … 500). Zona tanlash shart emas: kassir raqamni yozadi va rasta topiladi. Bu 6-fazadagi "≤3 bosish" mezonining poydevori. Karmanada rastalar jismonan shunday belgilangan.
- **D-02:** Raqam **tahrirlanadi, lekin qayta ishlatilmaydi**. Admin xato kiritilgan yoki bozor qayta raqamlangan holatda raqamni tuzata oladi (har o'zgarish auditda). Yopilgan rastaning raqami YANGI rastaga berilmaydi — tizim rad etadi. Sabab: hisobotda "12-rasta" yillar davomida bitta jismoniy joyni anglashi kerak, aks holda qarz va dalil-rasm chalkashadi.
- **D-03:** Zona — **yassi ro'yxat, har rastada majburiy**. Ierarxiya (sektor→qator) qurilmaydi. Har rasta aynan bitta zonaga tegishli. Xarita har zonani alohida grid blok qilib chizadi; import faylida bitta ustun.
- **D-04:** Mahsulot toifasi **rastaning atributi** (sotuvchiniki emas) va **o'zgartirilishi mumkin**. Sotuvchi almashsa toifa qoladi. Toifa o'zgarishi sanadan kuchga kiradi — o'tmishdagi hisob buzilmaydi (tarif tarixi bilan bir xil mexanizm). Sabab: toifa sotuvchiga bog'lansa, sotuvchisiz band rastaning tarifi noaniq bo'lib qoladi va "ro'yxatga olinmagan savdo" anomaliyasini hisoblab bo'lmaydi.

### Tarif o'lchovi va tarixi

- **D-05:** Kunlik patta summasi **faqat mahsulot toifasi bo'yicha** belgilanadi. Zona, rasta o'lchami/maydoni, hafta kuni yoki mavsum bo'yicha farq YO'Q. Tarif kaliti: `(market_id, category_id, valid_from)`.
- **D-06:** Tarif tarixi — **amal qilish sanasi bilan qatorlar**. Yangi narx kiritilganda YANGI qator qo'shiladi, eskisi o'zgarmaydi. Hisob yozilayotganda o'sha `business_date` ga amal qilgan qator tanlanadi. Kelajakdagi sanaga oldindan narx kiritish mumkin ("1-sentabrdan 12 000"). MARKET-03 shu bilan bajariladi.
- **D-07:** Tarif tahriri — **kelajakdagi qatorni tahrirlash/o'chirish mumkin, sanasi o'tgani qulflanadi**. O'tmishdagi narx faqat yangi sanadan yangi qator bilan "tuzatiladi". Har amal auditda (`tariffs` allaqachon DB-trigger ostida — 1-faza D-10).
- **D-08:** **Tarif topilmasa — fail-closed**: kunlik hisob YOZILMAYDI, taxminiy summa ishlatilmaydi. Rasta "tarifsiz band rasta" anomaliyasi sifatida kunlik hisobotga chiqadi va adminga alert boradi. Sabab: noto'g'ri summali patta sotuvchi bilan nizoni keltirib chiqaradi — mahsulot aynan buni oldini olish uchun bor. Loyihaning `NULLIF` fail-closed qoidasiga mos.

### Sotuvchi biriktirish va qarz egaligi

- **D-09:** Munosabat — **bir vaqtda 1 rasta = 1 sotuvchi; 1 sotuvchi = ko'p rasta**. Model: `stall_assignments(stall_id, vendor_id, from_date, to_date)`, bir rasta uchun davrlar kesishmaydi. Qarz sotuvchida jamlanadi, har rasta bo'yicha ajratib ko'rsatiladi.
- **D-10:** Rasta almashinuvida **qarz eski sotuvchida qoladi** — rasta bilan o'tmaydi. Har kunlik hisob o'sha KUNI biriktirilgan sotuvchiga yoziladi va o'shanda qoladi (10-sanada almashsa: 1–9 kunlar eskisiniki, 10-kundan yangisiniki). Yangi sotuvchi hech qachon begona qarzni meros qilib olmaydi. Amalda: `daily_charges` yozuvi `vendor_id` ni o'zida saqlaydi → qo'shimcha mantiq kerak emas.
- **D-11:** **Sotuvchisi biriktirilmagan band rasta — hisob emas, anomaliya**. ROADMAP 6-faza 3-mezoni bilan bir xil: "ro'yxatga olinmagan savdo" sifatida hisobotga chiqadi. "Noma'lum sotuvchi" texnik hisobi yaratilmaydi.
- **D-12:** Sotuvchi telefoni — **majburiy va bozor ichida unique** (E.164, `phonenumbers` bilan normalizatsiya — 1-fazadan tayyor). Sabab: 7-fazada sotuvchi botga aynan telefon raqami orqali ulanadi (BOT-03) va kvitansiya shu kanal bilan boradi.

### Real ma'lumot kiritish (~300–1000 rasta)

- **D-13:** **Excel/CSV import + usta qadamlari**. Usta qo'lda oladi: rekvizit → zona → toifa → tarif (bular kam — 5–15 ta). Rastalar va sotuvchilar **Excel fayldan ommaviy yuklanadi**. Shablon fayl yuklab olinadi. `XlsxWriter` allaqachon stekda (1-fazadan).
- **D-14:** Import xatosi — **all-or-nothing**. Butun fayl bitta tranzaksiya: bitta xato bo'lsa ham hech narsa yozilmaydi. Admin barcha xatolarni **qator raqami va sababi bilan** ko'radi ("14-qator: 'Sabzavot' zonasi topilmadi", "88-qator: 12 raqami takrorlangan"), faylni tuzatib qayta yuklaydi. Yarim kiritilgan holat hech qachon yuzaga kelmaydi.
- **D-15:** Qayta import — **faqat yangi qo'shiladi, mavjudi tegilmaydi**. Rasta kodi bo'yicha solishtiriladi: faylda bor + bazada yo'q → qo'shiladi; ikkalasida bor → o'tkazib yuboriladi (mavjud yozuv, sotuvchisi va tarixi tegilmaydi). Eski faylni tasodifan qayta yuklash hech narsani buzmaydi. Upsert ham, "faylda yo'qlarni yopish" ham YO'Q. Tahrirlash reestr UI orqali qilinadi — u yerda har o'zgarish auditda.
- **D-16:** **Usta kamerasiz yakunlanadi** va bozor "ishlashga tayyor" holatiga o'tadi. Kamera / kamera-zona / snapshot qadamlari keyinroq qo'shiladigan **ixtiyoriy bo'lim** bo'lib turadi (3–5 fazalarda ulanadi). Doimiy ogohlantirish banneri qo'yilmaydi. Oqibat (ataylab): 6-faza (billing/kassir) NVR'siz to'liq quriladi va sinaladi — AI-bandlik o'rniga qo'lda kiritish bilan.

### Ish kunlari (MARKET-05)

- **D-17:** **Haftalik jadval + istisno sanalar**. Bozorning doimiy rejimi bir marta belgilanadi (masalan dushanba — dam olish), ustiga alohida sanalar qo'shiladi: bayram ("1-yanvar — yopiq") yoki istisno ish kuni ("bu dushanba ishlaymiz"). Har kunni qo'lda kiritish shart emas, lekin har qanday holat ifodalanadi.
- **D-18:** Yopiq kun — **faqat bozor darajasida**. Zona yoki rasta darajasidagi alohida jadval YO'Q. 6-fazadagi kunlik job bitta tekshiruv qiladi: "bugun bu bozor ishlaydimi?". Vaqtincha yopiq rasta ehtiyoji `status = ta'mirda/yopiq` bilan allaqachon qoplanadi.

### Plan-xarita (MARKET-06)

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Loyiha darajasi
- `CLAUDE.md` — qulflangan texnologiya steki (aniq versiyalar) va taqiqlangan kutubxonalar. `XlsxWriter 3.2.9` eksport uchun; **openpyxl** faqat mavjud `.xlsx` ni O'QISH kerak bo'lganda qo'shiladi — import shu fazada aynan shu ehtiyojni tug'diradi (CLAUDE.md "Alternatives Considered" jadvalida bu holat oldindan qayd etilgan).
- `.planning/ROADMAP.md` §"Phase 2" — faza chegarasi, 5 muvaffaqiyat mezoni, "Note" bandi (kamera qadamlari 3–5 fazalarda, xarita sxematik qoladi)
- `.planning/REQUIREMENTS.md` — MARKET-01 … MARKET-06 matnlari
- `.planning/PROJECT.md` — mahsulotning asosiy qiymati va cheklovlar

### 1-fazadan meros qoidalar (MAJBURIY o'qish)
- `.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-CONTEXT.md` — D-01…D-16 qulflangan qarorlar; ayniqsa **D-16** (DB kontenti bir tilda, faqat UI 3 tilda), **D-07** (direktor faqat ko'radi), **D-09/D-10** (audit qamrovi va DB-trigger mexanizmi), **D-05/D-06** (bozor konteksti, RLS bypass yo'q)
- `.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-RESEARCH.md` — jonli `postgres:18.4` da tasdiqlangan naqshlar: `NULLIF(...)` fail-closed RLS predikati, `SECURITY DEFINER` + pinned `search_path`, alembic-utils `entity_types=[PGPolicy, PGFunction]` filtri
- `.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-VERIFICATION.md` — 25/25 tasdiqlangan holat va hali ochiq qolgan bandlar
- `.planning/phases/01-poydevor-va-tenant-xavfsizligi/01-REVIEW-GAPS.md` — hali yopilmagan WARNING'lar; ayniqsa **WR-02/WR-03** (`POST /auth/select-market` `require_password_current` dan tashqarida va `is_platform_admin` ni token'dan qayta imzolaydi) — bu faza auth yuzasiga tegsa, e'tiborga olinsin

### Kod naqshlari (mavjud, qayta ishlatiladi)
- `migrations/helpers.py` — `enable_tenant_rls()`, `attach_audit_trigger()`, `financial_guards()` / `financial_guard_statements()`
- `migrations/entities/policies.py`, `functions.py`, `triggers.py`, `__init__.py` — `RLS_TABLES` / `TENANT_TABLES` reyestrlari; yangi jadval SHU YERGA qo'shilishi kerak
- `packages/sbozor-core/sbozor_core/schema_contract.py` — `AUDITED_TABLES`, `FINANCIAL_TABLES`, `GLOBAL_TABLES` reyestrlari
- `packages/sbozor-core/sbozor_core/money.py`, `timeutil.py`, `phone.py`, `enums.py` — BIGINT so'm, Asia/Tashkent biznes-kun, E.164 telefon, `Role`/`Locale`/`AuditAction`
- `tests/tenancy/test_meta.py` — har yangi tenant jadvalini avtomatik tekshiradigan meta-test (jadval qo'shilsa va RLS berilmasa test QIZARADI)
- `tests/fixtures/two_markets.py` — cross-tenant test seed'i; yangi jadvallar shunga qo'shiladi
- `frontend/src/components/users/` va `frontend/src/components/audit/` — admin ro'yxat + dialog + filtr naqshi (ro'yxat, yaratish dialogi, keyset paginatsiya)
- `frontend/src/lib/api-types.ts`, `queries.ts`, `rbac.ts` — zod kontraktlari, TanStack Query naqshi, huquq tekshiruvi

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`financial_guards()`** (`migrations/helpers.py`) — `business_date` STORED generated column, `CHECK(amount_soum > 0)`, `UNIQUE(market_id, …, business_date)`, composite FK va `ON CONFLICT DO NOTHING` idempotentligi. 6-faza uchun qurilgan va real jadvalda isbotlangan; `tariffs` jadvali uchun ham qismlari mos keladi.
- **`enable_tenant_rls(table)`** — ENABLE + FORCE + policy + GRANT'ni bitta chaqiruvda beradi. Har yangi tenant jadvali shuni ishlatadi.
- **`attach_audit_trigger(table)`** — DB-trigger auditi; `tariffs` va `stall_assignments` uchun majburiy (D-10).
- **`money.py` / `timeutil.py` / `phone.py`** — BIGINT so'm (float rad etiladi), Asia/Tashkent biznes-kun chegarasi, E.164 normalizatsiya. Sotuvchi telefoni (D-12) va tarif summasi to'g'ridan-to'g'ri shulardan foydalanadi.
- **Frontend admin naqshi** — `user-list.tsx` + `create-user-dialog.tsx` + `audit-filters.tsx` rasta/sotuvchi reestri uchun tayyor shablon.
- **`market-picker.test.tsx` va vitest+jsdom infratuzilmasi** — 1-fazaning gap-closure to'lqinida o'rnatildi; yangi React komponentlari uchun render testi yozish yo'li ochiq.

### Established Patterns

- **Har tenant jadvali**: `market_id` ustuni + RLS ENABLE **va** FORCE + `NULLIF(current_setting('app.market_id', true), '')::uuid` predikatli policy. `tests/tenancy/test_meta.py` buni avtomatik tekshiradi — istisno faqat hujjatlashtirilgan ro'yxat orqali.
- **Fail-closed falsafasi**: RLS predikati, `LIMIT COALESCE(p_limit, 0)`, tarifsiz hisob (D-08) — hammasi "noaniq bo'lsa hech narsa qilma" tamoyilida.
- **Migratsiya tartibi**: `migrations/versions/000N_*.py`, entity'lar `migrations/entities/` da e'lon qilinadi, `alembic revision --autogenerate` bo'sh diff berishi kerak.
- **Audit**: moliyaviy jadvallarda DB-trigger (kod yo'li chetlab o'tolmaydi), qolganida app-qatlam. Shaxsiy ma'lumot O'QISHLARI ham auditda (D-09) — sotuvchi qarzini ko'rish shunga kiradi.
- **API**: keyset paginatsiya (OFFSET emas), RLS ko'rinmasligi → 404 (403 emas), `require_permission` ichida `require_password_current` avtomatik ishlaydi.

### Integration Points

- **6-faza (billing)** shu fazaning uchta chiqishiga tayanadi: `stalls` (hisob kaliti), `tariffs` (summa manbai, D-05/D-06), `stall_assignments` (qarz egasi, D-09/D-10). Uchalasining shakli hozir qotadi.
- **5-faza (CV zonalari)** `stalls.id` ga poligon bog'laydi — rasta identifikatorining barqarorligi (D-02) shuning uchun muhim.
- **7-faza (bot)** `vendors.phone` bo'yicha sotuvchini topadi (D-12).
- **Xarita komponenti** 6–7 fazalarda rang qatlamlari bilan boyitiladi (D-20) — hozir kengaytiriladigan qilib qurilsin.

</code_context>

<specifics>
## Specific Ideas

- Import xato xabarlari **qator raqami + aniq sabab** ko'rinishida bo'lishi aniq talab qilindi: "14-qator: 'Sabzavot' zonasi topilmadi", "88-qator: 12 raqami takrorlangan".
- Foydalanuvchi strategiyasi: **NVR oxirida**. Shuning uchun D-16 (kamerasiz yakunlanadigan usta) — bu shunchaki qulaylik emas, keyingi fazalarni ochib beruvchi qaror. 3–5 fazalarning kodi yozilib, tasdiqlash NVR kelguncha kutadi; 2 → 6 → 7 yo'nalishi NVR'siz to'liq sinaladi.
- Karmanada rastalar jismonan **bozor bo'yicha yagona raqam** bilan belgilangan (D-01 shundan kelib chiqdi, sxema o'ylab topilmadi).

</specifics>

<deferred>
## Deferred Ideas

- **Toifa+zona yoki rasta o'lchamiga bog'liq tarif** — hozir faqat toifa (D-05). Agar ma'muriyat keyinchalik zonaga qarab narx belgilamoqchi bo'lsa, `tariffs` kalitiga ustun qo'shish kerak bo'ladi (migratsiya bilan).
- **Bir rastada bir necha sotuvchi (smena/sherik)** — D-09 rad etdi. Agar haqiqatda uchrasa, `stall_assignments` ga vaqt oralig'i (soat) qo'shish yoki ulush modeli kerak bo'ladi. v2.
- **Rasta qarzining rasta bilan o'tishi** — D-10 rad etdi. Agar bozor amaliyoti boshqacha bo'lsa (Phase 0 ning "rasta almashinuvi" savoli), qayta ko'riladi.
- **Xaritada qo'lda joylashtirish (drag-drop) va jismoniy koordinatalar** — D-19 rad etdi, v2. ROADMAP ham xaritani sxematik deb belgilagan.
- **Ko'p tilli DB kontenti** (zona/toifa nomlari 3 tilda) — 1-faza D-16 bo'yicha qurilmaydi.
- **Import orqali mavjud yozuvlarni yangilash (upsert) yoki to'liq sinxronizatsiya** — D-15 rad etdi. Agar ommaviy tuzatish ehtiyoji tug'ilsa, alohida "ommaviy tahrir" oqimi sifatida ko'riladi.
- **Sotuvchi bir necha bozorda savdo qilishi** — MVP bitta bozor; `vendors` tenant-scoped bo'ladi. Ko'p bozorli sotuvchi (va botda ikkala qarzni ko'rsatish) v2.
- **Telefonsiz sotuvchi** — D-12 majburiy qildi. Agar dala ishida telefonsiz savdogarlar ko'p chiqsa, qayta ko'riladi (ular bot xabarlarini ololmaydi).

</deferred>

---

*Phase: 2-bozor-domeni-va-yangi-bozor-ustasi*
*Context gathered: 2026-07-29*
