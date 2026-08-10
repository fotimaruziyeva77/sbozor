# Phase 6: Billing va kassir — Research

**Researched:** 2026-08-10
**Domain:** Kunlik patta hisobi (immutable ledger) + kassir to'lov oqimi (idempotent POST) + smena/variance
**Confidence:** HIGH sxema va darvozalar bo'yicha (kod o'qildi, `path:line` bilan) · MEDIUM konkurentlik oynasi bo'yicha (Wave 0 zondi kerak) · LOW faqat buyurtmachi qarorlari bo'yicha (OQ-3, OQ-4, OQ-6)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Fazaning tub farqi**
- **D-01**: **Bu faza 5-fazaning teskarisi.** 5-fazada haqiqat yo'q edi va yetkazib berish mahsuloti o'lchov mexanizmi bo'lgan. Bu yerda haqiqat **to'liq mavjud** — pul miqdori aniq, tarif jadvalda, bandlik `stall_slot_occupancy` da materializatsiya qilingan. Ya'ni **har bir mezon bugun mexanik isbotlanadi** va "hozir o'lchab bo'lmaydi" degan bandning bu fazada o'rni yo'q. Agar reja shunday band tug'dirsa — bu dizayn xatosi, tabiiy chegara emas.
- **D-02**: **Nizo modeli — sotuvchi bilan.** Oldingi fazalarda xato "noto'g'ri raqam" edi; bu yerda xato **odam pul to'laganini isbotlay olmasligi**. Shuning uchun har qaror "nizo paytida qaysi yozuv dalil bo'ladi?" savoliga javob berishi kerak. `float` taqig'i, `TIMESTAMPTZ` va o'zgarmaslik triggerlarining sababi aynan shu.

**Hisob (BILL-01, BILL-02)**
- **D-03**: Manba — **`stall_slot_occupancy`**, `occupancy_events` EMAS. Agregatsiya 5-fazada tugagan; ikkinchi marta agregatsiya qilish **ikkinchi haqiqat manbai** yaratardi va ikkalasi bir kun ajralib ketardi. Hisob faqat materializatsiya qilingan qatorlarni o'qiydi.
- **D-04**: Hisob sharti ROADMAP dagidek: **≥2 slotda `occupied`**, **yoki** 1 slot `occupied` + o'sha slotda nazoratchi tasdig'i (`resolution_source` inson qarorini ko'rsatadi). Bitta tasdiqlanmagan AI sloti hisob bermaydi — noaniqlik sotuvchi foydasiga hal qilinadi.
- **D-05**: **`no_coverage` slotlari sanoqqa KIRMAYDI** — na `occupied`, na `empty`. Barcha slotlari `no_coverage` bo'lgan rasta uchun hisob yozilmaydi va u **BILL-04 anomaliyasi ham emas**: "ko'ra olmadik" ≠ "band, lekin biriktirilmagan". Ikkisini bir joyga qo'shish **ko'r nuqtadan tushum da'vosi to'qish** bo'lardi. Alohida "qamrovsiz rasta" yozuvi chiqadi (0-fazadagi ~10% qamrovsizlik shu yerda ko'rinadi).
- **D-06**: **Idempotentlik `UNIQUE (market_id, stall_id, business_date)`** bilan strukturaviy (BILL-01 shuni yozadi). Job `ON CONFLICT DO NOTHING` — **`DO UPDATE` EMAS**: yozilgan hisob o'zgarmas (D-07), ya'ni qayta yugurish uni yangilay olmaydi. Bu 05-12 dagi "qayta yugurish idempotentmi?" testining zaifligini takrorlamaslik uchun **holat bilan** o'lchanadi: qayta yugurishdan keyin summa **ham**, `created_at` **ham** o'zgarmagan bo'lishi kerak.
- **D-07**: `charges` **o'zgarmas** — shartsiz `BEFORE UPDATE OR DELETE` trigger, `zone_reviews` (05-05) dagi aynan bir xil mexanizm. Tuzatish faqat `charge_adjustments` (sabab-kod + aktor + audit). Balans = hisoblar − to'lovlar + tuzatishlar, **hech qachon saqlangan ustun** (BILL-03).
- **D-08**: **Dalil hisobga NUSXA bilan bog'lanadi, so'rov bilan emas.** Hisobni asoslagan slot qatorlari (`stall_slot_occupancy.id` va ularning `winning_occupancy_event_id` lari) hisob yozuvi bilan birga **saqlanadi**. Keyin qayta hisoblangan so'rov boshqa javob bersa ham, nizo paytida ko'rsatiladigan kadr **o'zgarmaydi**. Bu 5-fazaning `audit_rounds.frame_size` "muzlatilgan doira" qarorining aynan o'zi.
- **D-09**: Tarif `business_date` ga ko'ra 2-fazaning **tarixiy** `stall_category_periods` + `tariffs` orqali yechiladi. Hisob **`tariff_id` ni ham, summani ham** saqlaydi: keyin tarif tahrirlansa yozilgan hisob **retroaktiv o'zgarmasligi** shart. Bitta `tariff_id` yetarli emas — u kelajakdagi tahrirga ochiq.
- **D-10**: **Yopiq kunda hisob yo'q.** `open_weekdays` + `market_calendar_exceptions` (2-faza) bo'yicha yopiq kunda bandlik ko'rinsa — hisob yozilmaydi, **anomaliya** yoziladi. Yopiq kunda savdo bo'lishi real hodisa va uni jimgina pulga aylantirish ham, jimgina yo'qotish ham noto'g'ri.
- **D-11**: Pul — **`BIGINT` so'm ↔ Python `int`**. `float`/`Decimal` ustuni YO'Q. Lint darvozasi billing modullarida `float` ni taqiqlaydi (5-fazada `float8` kvotasi aynan shu sinfdagi xato bergan edi).

**Kun yopilishi (tetik va tartib)**
- **D-12**: **`billing_close(business_date)` — argumentli job**, `now()` dan kun olmaydi. 4-fazaning `retention_daily(today=...)` va 5-fazaning `audit_draw` qoidasi; 05-11 aynan shu sababdan `audit_draw_due_markets()` ni ishlatmagan.
- **D-13**: Cron **20:30 Asia/Tashkent** — 5-fazaning `review.queue_tick` (19:30) dan keyin. Lekin **tartib kafolati cron jadvaliga tayanmaydi**: `billing_close` bandlikka faqat **o'qish** uchun tegadi va **idempotent**, ya'ni noto'g'ri tartibda yugursa ham qayta yugurish tuzatadi. 05-11 ning darsi: kafolat cron SATRLARIGA ko'chib ketmasligi kerak.
- **D-14**: **Tasdiqlanmagan noaniq slotlar kunni BLOKLAMAYDI** (mahsulot qoidasi #5 — hech narsa jarayonni to'xtatmaydi). Ular D-04 bo'yicha baribir hisob bermaydi, ya'ni kutish foyda bermaydi. Hisobot esa nechta rasta **nazoratchisiz** hal qilinganini ko'rsatadi — bu yashiriladigan emas, o'lchanadigan miqdor.
- **D-15**: Bozorlar ro'yxati **`active_market_ids()`** dan — `alert_sweep`/`retention_daily`/`audit_draw` ishlatadigan **yagona** RLS-chetlab o'tuvchi yuza. Yangi xavfsizlik yuzasi ochilmaydi (05-11 deviatsiya #4).

**Kutilayotgan patta (BILL-05)**
- **D-16**: Proyeksiya **jadval emas, so'rov**. Va muhimi: **kun yopilishi bilan BITTA kod yo'lidan yuradi**, faqat parametri boshqa (`as_of=hozir` / `as_of=kun oxiri`). Ikki alohida implementatsiya kassir yig'gan summa bilan kechqurun yozilgan hisobni **ajratib yuborardi** — bu loyihada takroran topilgan "ikki haqiqat manbai" sinfi. Bitta funksiya, ikki chaqiruvchi; farq **testda** o'lchanadi.
- **D-17**: Proyeksiya "kutilayotgan" ekani **payloadda ochiq** — u hisob emas. Ekran uni yozilgan hisobdan vizual ajratadi; `charge_id` maydoni proyeksiyada **umuman yo'q** (yashirilgan emas — 5-fazaning D-17.2 naqshi).

**Kassir (CASH-01, CASH-02)**
- **D-18**: **≤3 bosish aniq ta'rifi:** (1) rasta raqamini kiritish/tanlash, (2) to'lov turi (naqd/terminal), (3) tasdiqlash. **Summa bosish emas** — u tarifdan avtomatik keladi. Raqam terishdagi bosqichlar bitta qadam sifatida sanaladi. Bu **o'lchanadi**: test interaktiv hodisalarni sanaydi (05-13 dagi `decision-bar` testlari naqshi), "3 ta tugma bor" degan strukturaviy tekshiruv emas.
- **D-19**: Summani o'zgartirish **yopiq sabab-kod ro'yxati** bilan (erkin matn emas — erkin matn hisobotda guruhlanmaydi va amalda bo'sh qoladi). Har o'zgartirish auditda aktor va eski/yangi summa bilan.
- **D-20**: Kassir ekrani **tarif summasini o'zi hisoblamaydi** — server bergan summani ko'rsatadi. Mijozda qayta hisoblash 05-14 rad etgan naqsh: u jimgina **boshqa savolga** javob berardi.

**To'lov va storno (CASH-03)**
- **D-21**: **Idempotentlik kaliti mijozda** tug'iladi (to'lov varag'i ochilganda UUID) va `UNIQUE (market_id, idempotency_key)` bilan qulflanadi. Takror so'rov **o'sha to'lovni 200 bilan qaytaradi**, 409 emas: tarmoq uzilishida qayta yuborish kassir uchun **ko'rinmas** bo'lishi kerak.
- **D-22**: **Ikki qatlam majburiy** — server kaliti **va** mijozdagi `useRef` qulfi. 05-13 o'lchagan: uch tez bosish uchta so'rov yuborardi, chunki `isPending` faqat keyingi renderda o'zgaradi. Server kafolati yolg'iz UI ni to'xtatmagan.
- **D-23**: `payments` **append-only**: `kind ∈ {payment, reversal}`, `reverses_payment_id`, o'zgarmaslik triggeri. Storno **sabab-kod** talab qiladi va **o'z qatori** bo'ladi. O'chirish/tahrirlash YO'Q. Qoldiq — belgili summalar yig'indisi.
- **D-24**: To'lov **hisobga bog'lanadi** (`charge_id`), rastaga emas. Aks holda "qaysi kunning pattasi to'landi?" savoliga javob yo'qoladi va eski qarz bilan bugungi patta aralashadi.

**Smena va ko'r deklaratsiya (CASH-04)**
- **D-25**: **Ko'r deklaratsiya 5-fazaning ko'r audit naqshining AYNAN qayta ishlatilishi.** Smena yopish payloadida tizim summasi **e'lon qilinmagan** (yashirilgan emas), deklaratsiya yozilgach **o'zgarmas**, variance **serverda** hisoblanadi. `blind-audit` uchun yozilgan G-12 sinfidagi darvoza smena-yopish katalogini ham skanerlaydi.
- **D-26**: Variance **ikki tomonlama ko'rsatiladi** (kam ham, ortiq ham) va **hech qachon avtomatik "to'g'rilanmaydi"**. Ortiqcha naqd ham signal — uni jimgina yutish kamomadni yashirish bilan bir xil xato.
- **D-27**: Smena **kassirga bog'langan** va bir vaqtda bitta ochiq smena — qisman `UNIQUE` indeks bilan strukturaviy (5-fazadagi `uq_alert_events_..._open` naqshi).

**Anomaliya (BILL-04)**
- **D-28**: Biriktirilmagan band rasta uchun **hisob YOZILMAYDI** va `vendor_id NULL` bilan hisob ham yozilmaydi — "kimdir qarzdor, lekin kim ekani noma'lum" yozuvi qarz hisobotini buzardi. Alohida anomaliya qatori yoziladi; **case oqimi 7-fazaniki**.
- **D-29**: Anomaliya yozuvi ham **dalil kadriga** bog'lanadi (D-08 bilan bir xil nusxa qoidasi) — 7-faza uni qayta topishga majbur bo'lmasin.

**Tekshiruv intizomi**
- **D-30**: Har reja sabotaj o'tkazadi va **nima qizarganini ham, nima YASHIL qolganini ham** yozadi. Yashil natijadan xulosa chiqarishdan oldin ikki savol: **sabotaj o'lchanayotgan tizimga yetib bordimi** (05-11: trigger boshqa bazada o'chirilgan edi) va **umuman biror test bu ikki holatni ajrata oladimi** (05-10: `WHERE` sharti ikki ifodani teng qilgan edi).
- **D-31**: Inkor tasdiq (`not.toContain("...")`) **ishlatilmaydi** — u faqat aynan o'sha nomni ushlaydi. O'rniga **to'plam tengligi** (05-14 sabotaj S7 buni o'lchagan).
- **D-32**: Darvoza qamrovi **hosila bo'ladi**, qo'lda sanalmaydi (05-16 W-2/W-3). Yangi marshrut yoki yangi komponent katalogi darvozaga **o'zi** kirishi kerak.

### Claude's Discretion

CONTEXT.md `--auto` rejimda yig'ilgan: har gray area'da tavsiya tanlab qo'yilgan, ya'ni alohida "Claude's Discretion" bo'limi YO'Q. Ochiq qolgan yuzalar — `<open_questions>` dagi OQ-1…OQ-7 (pastda javob berildi) va CONTEXT.md nomlamagan har qanday implementatsiya detali (jadval ustunlari, marshrut nomlari, indekslar, huquq nomlari).

### Deferred Ideas (OUT OF SCOPE)

| Idea | Qayerga |
|---|---|
| Telegram push-kvitansiya (`CASH-05`) | Phase 7 — talab u yerga biriktirilgan |
| Nomuvofiqlik case oqimi va botlar | Phase 7 |
| Excel eksport, direktor hisobotlari | Phase 8 |
| Jonli undirish ro'yxati (`V2-CASH-01`) | v2 |
| Kassir↔zona biriktirish va samaradorlik (`V2-CASH-02`) | v2 |
| QR/bank o'tkazma + referens, UzQR solishtiruvi (`V2-CASH-03`) | v2 |
| Qonuniy fiskal kvitansiya maydonlari (`V2-CASH-04`) | v2 |
| Kassir offline-lite navbati (`V2-CASH-05`) | v2 |
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md:53-64) | Research Support |
|----|-------------|------------------|
| **BILL-01** | Kun yopilishida band rastaga (≥2 snapshotda band, yoki 1 snapshot + nazoratchi tasdig'i) toifa tarifi bo'yicha to'liq kunlik patta hisoblanadi; job idempotent — `UNIQUE(market_id, stall_id, business_date)` | §B.1 (predikat, `_PER_STALL_CTE` ni QAYTA ISHLATMASLIK sababi), §B.2 (`daily_charges` sxemasi va **`business_date` nomi to'qnashuvi** — C-2), §C.1 (`billing.close` job shakli), §C.2 (cron vaqti — C-3) |
| **BILL-02** | Har hisob yozuvi dalil-kadrlarga bog'langan; yaratilgach o'zgartirilmaydi — tuzatish faqat sabab ko'rsatilgan `charge_adjustments` orqali | §B.3 (dalil nusxasi va `stall_slot_occupancy` **mutable** ekani — C-7), §B.4 (`charge_immutable()` trigger, `0018` naqshi), §B.5 (`charge_adjustments` va `amount_soum > 0` darvozasi — C-5) |
| **BILL-03** | Qarz faqat biriktirilgan sotuvchiga; qoldiq har doim hisoblanadigan ko'rinish (hisoblar − to'lovlar), saqlangan balans ustuni emas | §D.1 (balans ko'rinishi va indekslar), §D.2 (**to'lov hisobga bog'lanmaydi** — C-4), §B.6 (`vendor_id` muzlatilgan nusxa, D-10 kontrakti `periods.py` da) |
| **BILL-04** | Biriktirilmagan rasta band ko'rinsa — hisob yozilmaydi, "ro'yxatga olinmagan savdo" anomaliyasi | §B.7 (`billing_anomalies` — bitta jadval, `kind` bilan; D-05/D-10/D-28 uchala holat) |
| **BILL-05** | Kun davomida kassir/direktor "kutilayotgan patta"ni (bugungi tarif + eski qarz) ko'radi — jonli projection | §E.1 (proyeksiya = tarif + qoldiq; **bandlik OYNASI hali yo'q** — C-8), §E.2 (bitta umumiy pul-yechuvchi) |
| **CASH-01** | Kassir rastani raqam bo'yicha topadi → summa tarifdan avtomatik → to'lov turi → ≤3 bosishda tasdiqlaydi | §F.1 (OQ-1/OQ-2 javobi, `02-UI-SPEC §6.9` kontrakti), §F.2 (bosishni SANAYDIGAN test naqshi) |
| **CASH-02** | Kassir summani faqat sabab-kod bilan o'zgartira oladi; har o'zgartirish auditda | §F.3 (sabab-kod enum'i, enum'dan HOSILA `CHECK`, `audit-actions.test.mjs` darvozasi) |
| **CASH-03** | To'lov idempotent; tuzatish faqat storno + qayta kiritish, o'chirish/tahrirlash yo'q | §G.1 (idempotentlik: `ON CONFLICT DO NOTHING` + qayta `SELECT`, `RETURNING` bo'sh qaytishi), §G.2 (storno: `kind` ustuni, belgili summa EMAS — C-5), §G.3 (mijoz qulfi) |
| **CASH-04** | Kassir smenani ochadi/yopadi; yopishda ko'r naqd deklaratsiyasi; tizim variance ni hisoblaydi | §H.1 (`cashier_shifts` sxemasi, qisman UNIQUE), §H.2 (ko'r payload va serializator darvozasi), §H.3 (variance ikki tomonlama, OQ-7) |
</phase_requirements>

---

## Xulosa

Bu faza kodga emas, **mavjud darvozalarga** uriladi. Sxema, RBAC va i18n qatlamlarida 1–5 fazalar davomida o'rnatilgan **mexanik qulflar** bor va ularning bir qismi CONTEXT.md ning bir necha qarorini **bugungi holida bajarib bo'lmaydigan** qiladi. Uchta eng qimmati: (a) `financial_guards()` va `test_financial_tables_have_guards` `business_date` ni **`created_at` dan hosila** qilib qulflagan, ya'ni BILL-01 ning `UNIQUE(market_id, stall_id, business_date)` kaliti **hisoblanayotgan kunga** tegishli bo'la olmaydi; (b) `stall_slot_occupancy` **faqat ertasi kuni 03:40 da** to'ladi, ya'ni D-13 ning 20:30 croni nol hisob yozadi; (c) kassir kun davomida to'lov yig'adi, hisob esa ertasi kuni tug'iladi — ya'ni D-24 ning `payments.charge_id` bog'lanishi o'sha paytda **mavjud bo'lmagan qatorga** ishora qilardi.

Yaxshi xabar: uchalasining ham **repoda o'z presedenti bor**. `tariffs` aynan shu `business_date` muammosini hal qilgan (`0008_temporal.py:164-182` — `financial_guards()` **chaqirilmaydi**, uchala qo'riqchi qo'lda yoziladi, hukmron sana alohida ustunda); `occupancy.day_close` aynan shu cron muammosini hal qilgan (`worker.py:410-440` — kechasi ishlaydi va **kechagi kunni** yopadi); `stall_repo.py:595-635` esa D-09 ning tarixiy tarif yechimini **allaqachon yozib qo'ygan** `LEFT JOIN LATERAL ... ORDER BY valid_from DESC LIMIT 1` shaklida — unga faqat `t.id` qo'shilishi kerak.

Pul modeli bo'yicha esa **tanlov qolmagan va bu foyda**: `money.py:78-79` manfiy summani rad etadi, `test_meta.py:1346` har moliyaviy jadvaldan `CHECK (amount_soum > 0)` talab qiladi. Ya'ni "belgili summa vs `kind` ustuni" savoli **mavjud darvozalar tomonidan hal qilingan**: har joyda **musbat kattalik + `kind`**, belgi esa faqat ko'rinishda (`CASE WHEN kind='reversal' THEN -amount_soum ...`). Bu tanlov tashqi amaliyot bilan ham bir xil ([Modern Treasury](https://www.moderntreasury.com/journal/enforcing-immutability-in-your-double-entry-ledger), storno adabiyoti) — ya'ni D-23 ning "belgili summalar yig'indisi" iborasi **hisoblash usuli**, ustun tipi emas.

**Primary recommendation:** Wave 0 da **uchta qarorni** yozib oling va ularni kod yozishdan oldin qulflang — (1) `daily_charges` nomi + `service_date` ustuni (`business_date` generated qoladi), (2) `billing.close` croni `occupancy.day_close` dan KEYIN (`"10 4 * * *"`, `business_today() - 1`), (3) `payments` sotuvchi darajasidagi kredit (`charge_id` YO'Q, `service_date` BOR). Qolgan hamma narsa mavjud naqshlarning takrori.

---

## Contradictions with CONTEXT.md

> Bu bo'lim fazaning **eng qimmat natijasi**. Har band: CONTEXT.md nima deb qabul qilgan · kod nima deydi (`path:line`) · nima qilish kerak.

### C-1 — Jadval nomi `charges` EMAS, `daily_charges` (BLOKLAYDI)

**CONTEXT.md** D-06/D-07/`<code_context>` `charges` deb yozadi.
**Kod:** `packages/sbozor-core/sbozor_core/schema_contract.py:69-80` — `FINANCIAL_TABLES = {"daily_charges", "charge_adjustments", "payments", "tariffs"}`. Nom **1-fazadan beri** qulflangan (`01-03-PLAN.md:131`) va `test_financial_tables_have_guards` (`tests/tenancy/test_meta.py:1327`) AYNAN shu nomni bazada izlaydi.
**Qilish:** jadval **`daily_charges`**. `charges` deb nomlash reyestrni o'zgartirishni talab qilardi va o'shanda darvoza jadval tug'ilgan kuni **umuman ishga tushmasdi** (reyestrda yo'q nom = tekshirilmaydigan jadval). Reja hamma joyda `daily_charges` yozishi shart; `charge_adjustments` va `payments` nomlari CONTEXT.md bilan mos.

### C-2 — `business_date` HISOBLANAYOTGAN KUN BO'LA OLMAYDI (BLOKLAYDI)

**CONTEXT.md** D-06: `UNIQUE (market_id, stall_id, business_date)` — bu yerda `business_date` "patta yozilayotgan kun" ma'nosida.
**Kod:**
- `migrations/helpers.py:357-361` — `financial_guards()` `business_date date GENERATED ALWAYS AS ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED` beradi, ya'ni **qator YOZILGAN kun**.
- `tests/tenancy/test_meta.py:1331-1339` — `FINANCIAL_TABLES` dagi har mavjud jadvaldan `business_date` ustuni `attgenerated = 's'` bo'lishini talab qiladi.
- `tests/integration/test_business_date.py:134-145` — `business_date` ga **aniq qiymat yozish RAD ETILADI** (generated ustun).

**Oqibat:** `billing_close(business_date=D)` ni **D+1 da** (yoki backfill sifatida keyinroq) yugurtirsak, generated `business_date` = yugurish kuni bo'ladi → `ON CONFLICT` **to'qnashmaydi** → o'sha rasta-kun uchun **ikkinchi hisob** yoziladi. Bu BILL-01 idempotentligini to'g'ridan-to'g'ri buzadi. Va C-3 ga ko'ra job **har doim** ertasi kuni yuguradi, ya'ni bu chetlab o'tiladigan burchak holati emas — **asosiy yo'l**.

**Presedent (aynan shu muammo, aynan shu sabab):** `migrations/versions/0008_temporal.py:164-182`:
> `financial_guards("tariffs", ...)` BU YERDA CHAQIRILMAYDI. Yordamchi `UNIQUE(market_id, category_id, business_date)` beradi, ya'ni idempotentlik kalitini QATOR YOZILGAN KUNGA bog'laydi. Tarifda esa hukmron sana `valid_from` … Shuning uchun uchala qo'riqchi ham QO'LDA yozilgan.

**Tavsiya (Variant A — presedentga aynan mos):**
```
daily_charges:
  service_date  date NOT NULL            -- HISOBLANAYOTGAN kun (argumentdan)
  business_date date GENERATED ALWAYS AS ((created_at AT TIME ZONE 'Asia/Tashkent')::date) STORED
  UNIQUE (market_id, stall_id, service_date)      -- BILL-01 idempotentligi
  CHECK  (amount_soum > 0)
  CHECK  (service_date <= business_date)          -- KELAJAK kunini yozib bo'lmaydi
```
`financial_guards()` **chaqirilmaydi** (uchala qo'riqchi qo'lda, `tariffs` naqshi). Meta-test o'tadi: `business_date` generated ✓, `CHECK (amount_soum > 0)` ✓, `market_id` bilan boshlanadigan UNIQUE ✓.

⚠ **Nom tuzog'i ochiq yozilishi SHART.** `stall_slot_occupancy.business_date` = *ma'lumot tegishli kun* (`models/occupancy.py:1012-1015` — `snapshots` dan NUSXALANADI), `daily_charges.business_date` esa = *qator yozilgan kun*. Ikkisini join qilish **jim nosozlik** beradi. Shuning uchun (a) domen ustuni `service_date` deb ATAYIN boshqa nomlanadi, (b) ustun docstringi ikki ma'noni yonma-yon yozadi, (c) `## Validation Architecture` da semantik invariant testi bor (`har charge.service_date uchun stall_slot_occupancy qatorlari mavjud`).

Muqobil variantlar va nega rad etilgani:
| Variant | Nega yo'q |
|---|---|
| `business_date` ni oddiy `date` qilish | `test_financial_tables_have_guards` qizaradi; yagona "tuzatish" — jadvalni `FINANCIAL_TABLES` dan olib tashlash, ya'ni **darvozani o'chirish** |
| `business_date GENERATED ALWAYS AS (service_date) STORED` | Mexanik o'tadi va nom to'qnashuvini yo'qotadi, LEKIN "qator qachon yozilgan" audit faktini **butunlay yo'qotadi** (backfill bilan normal close farqlanmaydi) va `attgenerated` talabini shakl uchun bajaradi. Ikkinchi tanlov sifatida qoldiriladi; PG 18 da ruxsat etilishi **Wave 0 zondi bilan o'lchanishi** kerak (`BILLABLE_ANCHOR_SUPPORTED` naqshi) |
| Meta-testni yumshatish | Darvozani bo'shatadi. Agar tanlansa — **kuchliroq** shart bilan almashtirilishi shart (masalan `CHECK (service_date <= (created_at AT TIME ZONE 'Asia/Tashkent')::date)` + reyestr), aks holda mezon #5 susayadi |

### C-3 — D-13 ning 20:30 croni NOL hisob yozadi (BLOKLAYDI)

**CONTEXT.md** D-13: cron 20:30, `review.queue_tick` (19:30) dan keyin.
**Kod:** `services/core-api/app/worker.py:410-440` — `DAY_CLOSE_CRON = "40 3 * * *"`; `worker.py:878` — `day_close(..., business_date=business_today() - timedelta(days=1))`. Ya'ni **`stall_slot_occupancy` D kuni uchun faqat D+1 ning 03:40 da yoziladi** va `occupancy_repo.materialize()` (`occupancy_repo.py:636`) — uning **yagona** yozuvchisi.
**Oqibat:** 20:30 da D kuni uchun `stall_slot_occupancy` da **0 qator** bor → D-03 ("faqat materializatsiya qilingan qatorlarni o'qiydi") bo'yicha `billing_close(D)` **hech nima yozmaydi** va xato ham bermaydi. Sukunat "hammasi joyida" bilan bir xil ko'rinadi — bu 4/5-fazalarda takroran nomlangan jim nosozlik sinfi.
**Qilish:** `BILLING_CLOSE_CRON = "10 4 * * *"` (`cron_offset = MARKET_CRON_OFFSET`) va qobiqda `business_date = business_today() - timedelta(days=1)` — `day_close_task` (`worker.py:860-878`) bilan **aynan bir xil shakl**. 03:40 (day_close) → 04:10 (billing) orasidagi 30 daqiqa `RETENTION_CRON`(03:20) → `DAY_CLOSE_CRON`(03:40) farqi bilan bir xil mulohaza.
⚠ D-13 ning **mazmuni saqlanadi**: tartib kafolati cron satrida emas — `billing_close` idempotent va konvergent, ya'ni tartib buzilsa qayta yugurish tuzatadi. Faqat **soat qiymati** o'zgaradi.

⚠ **Ikkinchi darajali oqibat (rejaga kiritilishi kerak):** nazoratchi kechagi navbatni **bugun** ko'radi (`worker.py:405-407`). Ya'ni D kuni uchun inson tasdig'i ko'pincha D+1 ning **kunduzida** keladi — 04:10 dan KEYIN. `ON CONFLICT DO NOTHING` sababli kech kelgan tasdiq **yo'q hisobni yaratishi mumkin** (ikkinchi yugurish INSERT qiladi), lekin **mavjud hisobni bekor qila olmaydi** (o'zgarmas) — u faqat `charge_adjustments` bo'lib ko'rinadi. Bu to'g'ri xulq, LEKIN u yozilishi va o'lchanishi kerak: `billing.close` **kuniga bir marta emas, ikki marta** chaqirilishi mumkin (04:10 va, masalan, 20:00 da "kechagi kunni yana bir ko'r") — yoki 7-fazaning case oqimi uni oladi. Tavsiya: **04:10 bitta chaqiruv** + `charge_adjustments` yo'li; ikkinchi cron qo'shish "ikki haqiqat manbai" xavfini oshiradi.

### C-4 — D-24 (`payments.charge_id`) bugungi to'lov uchun IMKONSIZ (BLOKLAYDI)

**CONTEXT.md** D-24: to'lov `charge_id` ga bog'lanadi, rastaga emas.
**Kod/mantiq:** BILL-05 + CASH-01 bo'yicha kassir **kun davomida** bugungi pattani yig'adi; hisob esa C-3 bo'yicha **ertasi kuni 04:10 da** tug'iladi. Ya'ni to'lov paytida `charge_id` **mavjud emas**. Ikkinchi mustaqil to'siq: bitta to'lov (100 000 so'm) **bir necha kunlik** qarzni yopishi mumkin, ya'ni to'lov↔hisob **1:1 emas**.
**Nima qilmaslik kerak:**
- `charge_id NOT NULL` — bugungi to'lovni yozib bo'lmaydi;
- to'lov paytida hisobni **oldindan yaratish** — BILL-01 ni buzadi (bandlik darvozasini chetlab o'tadi, band bo'lmagan rastaga hisob yozadi);
- `charge_id NULLABLE` + kechasi "moslashtiruvchi" job — ikkinchi haqiqat manbai va yangi jim nosozlik yuzasi.

**Tavsiya:** standart AR (debitorlik) modeli — to'lov **sotuvchi darajasidagi kredit**:
```
payments:
  market_id, id
  stall_id      NOT NULL     -- kassir nimani bosgani (composite FK -> stalls)
  vendor_id     NOT NULL     -- MUZLATILGAN nusxa (service_date dagi biriktirish)
  service_date  date NOT NULL-- QAYSI kun uchun to'lanyapti (D-24 ning savoliga javob)
  amount_soum   bigint NOT NULL CHECK (> 0)
  kind          text NOT NULL CHECK (kind IN ('payment','reversal'))
  method        text NOT NULL CHECK (method IN ('cash','terminal'))
  reverses_payment_id uuid NULL
  reason_code   text NULL     -- storno va summa o'zgarishi uchun
  idempotency_key text NOT NULL
  shift_id      uuid NULL      -- OQ-6
  business_date date GENERATED ... STORED   -- pul KELGAN kun (mezon #5)
  UNIQUE (market_id, idempotency_key)
```
Qoldiq: `Σ daily_charges + Σ charge_adjustments − Σ signed(payments)` **sotuvchi kesimida** (BILL-03 ning so'zma-so'z talabi). "Qaysi kun to'landi?" — `service_date`. `charge_id` **umuman yo'q**, ya'ni D-24 ning *maqsadi* bajariladi, *mexanizmi* boshqa.
⚠ Bu **qaror o'zgarishi** — planner uni CONTEXT.md ga qaytarishi (yoki discuss-phase ga eskalatsiya qilishi) kerak.

### C-5 — D-23 "belgili summa" `CHECK (amount_soum > 0)` bilan to'qnashadi

**CONTEXT.md** D-23: "Qoldiq — belgili summalar yig'indisi". `charge_adjustments` uchun ham chegirma manfiy delta bo'lib tabiiy ko'rinadi.
**Kod:** `tests/tenancy/test_meta.py:1341-1347` — `FINANCIAL_TABLES` dagi har jadvalda `pg_get_constraintdef` ichida `amount_soum > 0` regeksi topilishi SHART (ya'ni **ustun nomi ham `amount_soum` bo'lishi kerak** — `delta_soum` darvozani qizartiradi). `packages/sbozor-core/sbozor_core/money.py:78-79` — `assert_safe_soum()` manfiy qiymatni `ValueError` bilan rad etadi; `money.py:72-73` docstringi buni ochiq aytadi: *"chegirma `charge_adjustments` da alohida yozuv sifatida saqlanadi"*.
**Qilish:** hamma joyda **musbat kattalik + `kind`/`direction` ustuni**:
- `payments.kind ∈ {payment, reversal}` (D-23 bilan mos);
- `charge_adjustments.direction ∈ {increase, decrease}` + `amount_soum > 0`;
- belgi FAQAT ko'rinishda: `CASE WHEN kind = 'reversal' THEN -amount_soum ELSE amount_soum END`;
- `money.format_soum()` manfiy qiymatni **ko'rsatish uchun** qabul qiladi (`money.py:87-96`) — ya'ni ekran tomoni allaqachon tayyor.
Tashqi amaliyot ham shu tomonda: *"A correct double-entry model is defined by … a side column (not signed amounts)"* ([Faysal Ahmed](https://faysalahmed.space/blog/double-entry-accounting-db-model-2026.md/), [Modern Treasury](https://www.moderntreasury.com/journal/enforcing-immutability-in-your-double-entry-ledger)).

### C-6 — Mavjud `human_confirmed` D-04 NING PREDIKATI EMAS (jim noto'g'ri hisob)

**CONTEXT.md** D-04: 1 slot `occupied` + **o'sha slotda** nazoratchi tasdig'i.
**Kod:** `services/core-api/app/repositories/occupancy_repo.py:369` —
```sql
bool_or(sso.resolution_source = :human) AS human_confirmed
```
Bu **barcha slotlar** ustidan, `verdict` bilan bog'lanmagan. Ya'ni: rasta 1 slotda AI-`occupied`, boshqa slotda nazoratchi **"bo'sh"** degan → `occupied_slots = 1 AND human_confirmed = true` → D-04 ni qayta ishlatilganda **hisob yoziladi**, holbuki hech kim bandlikni tasdiqlamagan. Bu aynan D-02 ning nizo sinfi (sotuvchi to'lamagan patta uchun qarzdor bo'ladi).
**Qilish:** billing o'z predikatini yozadi:
```sql
bool_or(sso.verdict = :occupied AND sso.resolution_source = :human) AS human_confirmed_occupied
```
va `_PER_STALL_CTE` ning `human_confirmed` i **hisobotda qoladi, billingda ishlatilmaydi**. 05-10 darsi (`WHERE` sharti ikki ifodani teng qilgan edi) shu yerda takrorlanmasligi uchun test **uchala holatni** ajratishi shart (pastda `## Validation Architecture` G-6).

### C-7 — D-08: `stall_slot_occupancy` MUTABLE, ya'ni `id` "muzlatilgan dalil" emas

**CONTEXT.md** D-08: slot qatorlari (`stall_slot_occupancy.id` va ularning `winning_occupancy_event_id` lari) saqlanadi.
**Kod:** `occupancy_repo.py:319-340` — `_MATERIALIZE_SLOT` `ON CONFLICT ... DO UPDATE SET verdict, resolution_source, winning_occupancy_event_id`. `occupancy_repo.py:341-352` buni ochiq izohlaydi: *"`stall_slot_occupancy` DALIL EMAS, u HOSILA"*. Ya'ni qator `id` si barqaror, lekin uning **mazmuni keyin o'zgaradi**.
**Oqibat:** faqat `stall_slot_occupancy.id` ni saqlash **muzlatmaydi** — kech kelgan tasdiqdan keyin o'sha qator boshqa hodisaga ishora qilishi mumkin.
**Qilish:** muzlatilgan pointer — **`occupancy_event_id`** (jadval `0018` bilan shartsiz o'zgarmas: `migrations/entities/triggers.py:468-488`). `stall_slot_occupancy_id` audit havolasi sifatida saqlanadi, **dalil esa hodisa**.
⚠ **Ikkinchi topilma:** `stall_slot_occupancy` da `UNIQUE (market_id, id)` **YO'Q** (`models/occupancy.py:972-1008` — faqat `uq_stall_slot_occupancy_market_stall_day_slot`). Ya'ni unga kompozit FK qo'yish **bugun imkonsiz**. Agar dalil jadvali FK bilan qadalishi kerak bo'lsa, `0020` avval `uq_stall_slot_occupancy_market_id_id` ni qo'shishi shart (va u `INDEX_EXCEPTIONS` ga TUSHMAYDI — `market_id` bilan boshlanadi).

### C-8 — D-16 "bitta kod yo'li, `as_of` parametri" so'zma-so'z bajarilmaydi

**Sabab:** proyeksiya **bugungi** kun uchun ishlaydi, `stall_slot_occupancy` esa bugun uchun **bo'sh** (C-3). Ya'ni "kun yopilishi bilan bitta yo'l" bandlik darvozasini ham bo'lishishni talab qilardi va u bugun **hech qachon rost bermasdi** (proyeksiya har doim 0 rasta ko'rsatardi).
**BILL-05 ning matni buni allaqachon hal qilgan:** "kutilayotgan patta = **bugungi tarif + eski qarz**" — bandlik shartisiz. Ya'ni proyeksiya **tarif-asosli**, yozilgan hisob esa **bandlik-asosli**.
**Qilish:** umumiy qilinadigan narsa — **pul yechimi**, bandlik darvozasi emas:
```
resolve_stall_day_money(market_id, as_of: date) -> [(stall_id, vendor_id, tariff_id, amount_soum)]
   ├── BILL-05 proyeksiyasi:  as_of = bugun          (+ qoldiq join)
   └── billing_close:         as_of = business_date  (+ bandlik darvozasi + yopiq kun + biriktirish)
```
D-16 ning **maqsadi** (kassir yig'gan summa kechqurun yozilgan summadan farq qilmasin) aynan shu bilan bajariladi: **summa** bitta funksiyadan keladi. Farqni o'lchash testi ham shu bo'g'inda yoziladi.

### C-9 — Kassirda O'QISH huquqi UMUMAN YO'Q

**Kod:** `services/core-api/app/security/rbac.py:214` — `Role.CASHIER: frozenset({Permission.PAYMENT_CREATE})`. Boshqa hech nima. Ya'ni kassir bugun **rasta ro'yxatini ham, proyeksiyani ham, smenani ham** olmaydi (403).
**Qilish (uchta mexanik shart):**
1. Yangi huquq(lar) **ikki faylda**: `app/security/rbac.py` **va** `frontend/src/lib/rbac.ts` — `frontend/scripts/role-gate.test.mjs:29-56` ikkalasini **matn sifatida o'qib** solishtiradi.
2. ⛔ `require_any_permission()` **ISHLATILMAYDI**. `tests/tenancy/test_personal_data_coverage.py:674-706` — bu darvozani ko'targan marshrutlar to'plami **AYNAN** `("/api/v1/snapshots/{snapshot_id}/image",)` ga teng bo'lishi shart. Kassir+direktor bitta marshrutni bo'lishishi kerak bo'lsa — **bitta yangi huquq** bir necha rolga beriladi (`require_permission`), "yo P yo Q" emas.
3. Tavsiya etilgan minimal to'plam:
   | Huquq | Kim oladi | Nima uchun |
   |---|---|---|
   | `PAYMENT_CREATE` (mavjud) | cashier | to'lov va storno yozish |
   | `BILLING_COLLECT_VIEW` (yangi) | cashier, market_admin, director | kutilayotgan patta + rasta bo'yicha qoldiq (BILL-05) |
   | `SHIFT_MANAGE` (yangi) | cashier, market_admin | smena ochish/yopish (CASH-04) |
   | `REPORT_VIEW` (mavjud) | director, market_admin | hisoblar/anomaliyalar reyestri (BILL-03/04) |

⚠ **Kassir `MARKET_DATA_VIEW` OLMAYDI.** `test_personal_data_coverage.py:761-787` — `MARKET_DATA_VIEW` egasida `VENDOR_VIEW` ham bo'lishi SHART, `VENDOR_VIEW` esa **butun shaxsiy-ma'lumot yuzasini** ochadi (`rbac.py:97-109`).

### C-10 — Kassir yuzasida shaxsiy maydon BO'LMASLIGI kerak

**Kod:** `tests/tenancy/test_personal_data_coverage.py:59` — `PERSONAL_FIELDS = {"vendor_name", "phone", "full_name"}`; `:732-758` — bunday maydon qaytaradigan har `GET` `VENDOR_VIEW` **va** `audit_read(...)` e'lon qilishi shart.
**Qilish:** kassir ekrani javobida faqat `stall_code`, `amount_soum`, `outstanding_soum`, `service_date` bo'ladi — **ism/telefon yo'q**. Aks holda kassirga `VENDOR_VIEW` berish kerak bo'lardi (C-9 ⚠) va har to'lov ekrani o'qish auditiga qator yozardi.
⚠ Darvoza **NOM bo'yicha** ishlaydi: maydonni `vendor_label` deb atash uni chetlab o'tadi. Bu **taqiqlanadi** va reja buni ochiq yozadi (D-31 ruhida: darvozani aylanib o'tish = darvozani buzish).

### C-11 — `occupancy_day_close_markets()` billingni HAYDAY OLMAYDI

**Kod:** `migrations/entities/functions.py:1716-1738` — funksiya kunni `((now() AT TIME ZONE 'Asia/Tashkent')::date)` dan oladi va `WHERE m.is_active` bilan **barcha faol bozorlarni** qaytaradi.
**Xulosa:** (a) bozorlar TO'PLAMI `active_market_ids()` bilan **aynan bir xil** (`app/jobs/day_close.py:69-72`), ya'ni yangi yuza foyda bermaydi; (b) `event_count` **boshqa kun** uchun noto'g'ri son bo'lardi — 05-11/05-12 aynan shu sababdan uni ishlatmagan (`day_close.py:54-73`).
**Tavsiya:** D-15 ga muvofiq `active_market_ids()` (`app/jobs/retention.py:138`) ishlatiladi va **ikkala orfan funksiya `0020` da DROP qilinadi** — sabab migratsiya docstringida: `business_date` argumentli job modeli (D-12) `now()` ga qadalgan yuzani prinsipial ravishda ishlatolmaydi, ya'ni ular chaqiruvchisiz **qoladi** va chaqiruvchisiz `SECURITY DEFINER` funksiya — RLS ni chetlab o'tadigan **ishlatilmayotgan yuza**. DROP qilinganda `DEFINER_SURFACES` (`tests/tenancy/test_occupancy_domain_meta.py:75-79`), `OCCUPANCY_FUNCTIONS` va `OCCUPANCY_GRANT_SIGNATURES` (`functions.py:1771-1793`) ham shu commitda tozalanadi — **ikki tomonlama qulf** (`PENDING_AUDIT_TRIGGERS` naqshi).
Muqobil: ularni qoldirib, `STATE.md` ga "abadiy chaqiruvchisiz, sababi X" deb yozish. Bu **kamroq** tavsiya etiladi — `05-15-SUMMARY.md:143` qarorni aynan shu fazaga qoldirgan, ya'ni "keyinroq" varianti tugadi.

### C-12 — D-05 ning "qamrovsiz rasta yozuvi" turi aniqlanmagan

CONTEXT.md aytadi: `no_coverage` **BILL-04 anomaliyasi emas**, "alohida yozuv chiqadi". Lekin jadvalmi, so'rovmi — yozilmagan. Va D-29 dalil talab qiladi, `no_coverage` da esa **dalil YO'Q** (`SLOT_OCCUPIED_HAS_WINNER_CHECK`, `models/occupancy.py:317-331` — g'olib hodisa faqat `occupied` da).
**Tavsiya:** bitta jadval `billing_anomalies` + `kind` ustuni (enum'dan hosila `CHECK`), dalil havolasi **NULLABLE** va `kind` bilan **juftlangan**:
```
kind ∈ { unassigned_occupied,   -- BILL-04 / D-28  (dalil MAJBURIY)
         closed_day_occupied,   -- D-10            (dalil MAJBURIY)
         no_coverage_stall }    -- D-05            (dalil YO'Q — CHECK buni majburlaydi)
CHECK ( (kind = 'no_coverage_stall') = (occupancy_event_id IS NULL) )
```
Bu `NO_COVERAGE_IS_PAIRED_CHECK` (`models/occupancy.py:333-344`) ning aynan takrori: ikki tomonlama tenglik, ya'ni "dalilsiz anomaliya" ham, "dalilli qamrovsizlik" ham **ifodalab bo'lmaydi**.

### C-13 — Yangi audit hodisalari UCH tilni ham talab qiladi

`sbozor_core/enums.py:442-464` — `AuditAction` da billing hodisalari yo'q. Yangi a'zo qo'shilsa `frontend/scripts/audit-actions.test.mjs:1-30` **uchala** locale faylida `audit.actions.<nom>` kalitini talab qiladi; `uz-Cyrl.json` **generatsiya qilinadi** (`frontend/scripts/gen-cyrillic.mjs`), ya'ni qo'lda yozilmaydi. Xuddi shu qoida yangi xato kodlari uchun (`frontend/scripts/error-codes.test.mjs`).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Kunlik patta hisoblash (BILL-01) | **API/Backend job** (`core-api` taskiq worker) | Database (UNIQUE + CHECK + trigger) | Bandlik va tarif ikkalasi ham DB da; hisob DB dan chiqmaydigan qarorga aylanadi. Idempotentlik **sxemada** (D-06) |
| Hisob o'zgarmasligi (BILL-02) | **Database** (`BEFORE UPDATE OR DELETE` trigger) | — | Ilova qatlami xom SQL/migratsiya yo'lini qamramaydi (`0018` naqshi) |
| Dalil bog'lanishi (BILL-02/D-08) | **Database** (nusxa ustunlar + FK) | API (o'qish marshruti) | Nusxa = muzlatish; so'rov = qayta hisoblash |
| Qoldiq (BILL-03) | **Database** (ko'rinish/so'rov, saqlangan ustun YO'Q) | API (serializator) | "Hisoblanadigan ko'rinish" talab matnida |
| Anomaliya yozuvi (BILL-04) | **API/Backend job** | Database (`kind` CHECK) | Yozuv kun yopilishida tug'iladi; oqim 7-fazada |
| Kutilayotgan patta (BILL-05) | **API/Backend** (so'rov) | Frontend (ko'rsatish) | D-20: mijoz hisoblamaydi |
| Rasta raqamidan topish (CASH-01) | **Frontend** (`autoFocus` + Enter) | API (`?q=` prefiks izlash) | `02-UI-SPEC §6.9` kontrakti: ≤2 o'zaro ta'sir |
| To'lov idempotentligi (CASH-03) | **Database** (`UNIQUE (market_id, idempotency_key)`) | Frontend (`useRef` qulfi) | D-22: ikki qatlam MAJBURIY, biri ikkinchisini almashtirmaydi |
| Storno (CASH-03) | **Database** (append-only + trigger) | API (sabab-kod validatsiyasi) | O'chirish yo'li **umuman yozilmaydi** |
| Ko'r deklaratsiya (CASH-04) | **API** (payloadda tizim summasi YO'Q) | Frontend (ekranda yo'q) + darvoza testi | 5-fazaning `blind_audit` naqshi: serializator darvoza bilan qulflanadi |
| Variance hisoblash (CASH-04) | **API/Backend** | Database (`GENERATED` yoki ko'rinish) | D-25: serverda; mijoz hisoblamaydi |
| Cron/tetik | **Worker + scheduler** (`app/worker.py` YAGONA uy) | — | D-06 (4-faza): `taskiq` faqat shu faylda |

---

## Standard Stack

### Core — YANGI BOG'LIQLIK YO'Q

| Library | Version (pinned) | Purpose | Why Standard |
|---------|------------------|---------|--------------|
| SQLAlchemy | 2.0.x (mavjud pin) | `pg_insert(...).on_conflict_do_nothing(...)`, `Mapped[]` modellar | `app/jobs/day_close.py:89` allaqachon `sqlalchemy.dialects.postgresql.insert` ishlatadi |
| Alembic + `alembic-utils` | mavjud pin | `0020` migratsiyasi, `PGFunction` trigger funksiyalari | `migrations/entities/` naqshi |
| taskiq + taskiq-redis | 0.12.4 / 1.2.3 | `billing.close` cron vazifasi | `worker.py` — kutubxona **faqat shu faylda** (D-06) |
| PostgreSQL | **18.4** | `uuidv7()`, generated columns, partial UNIQUE, `daterange @>` | CLAUDE.md: PG 19 **TAQIQ** |
| Pydantic | 2.13.x | request/response sxemalari | `schemas.py` naqshi |
| Next.js / React / next-intl / TanStack Query / zod | 16.2.12 / 19.2.8 / 4.13.4 / 5.101.4 / 4.4.3 | kassir ekrani, smena ekrani | `frontend/package.json:20-40` |

**Installation:** `—` **hech nima o'rnatilmaydi.** Fazaning butun ishi mavjud pinlar ustida bajariladi.

### Alternatives Considered (va nega YO'Q)

| Instead of | Could Use | Tradeoff / verdikt |
|------------|-----------|--------------------|
| `ON CONFLICT DO NOTHING` + qayta `SELECT` | PG 19 `ON CONFLICT DO SELECT` | Atomik get-or-create, CTE kerak emas — LEKIN PG 19 CLAUDE.md da **taqiqlangan** (`19beta2`). ⛔ |
| Qayta `SELECT` | `WITH ... UNION ALL` CTE | Bitta bayonot, lekin CTE ning `SELECT` qismi **tranzaksiya snapshotini** ko'radi, ya'ni parallel yozilgan qatorni topmaydi ([Haki Benita](https://hakibenita.com/postgresql-get-or-create)). ⛔ ikki bayonot ishonchliroq |
| `pg_advisory_xact_lock` | — | `.planning/research/ARCHITECTURE.md:305-307` billing run uchun taklif qilgan. **Kerak emas**: idempotentlik kaliti UNIQUE bilan, bir bozor — bitta tranzaksiya (`day_close.py:241-248` naqshi), replika bitta. Qo'shilsa yangi deadlock yuzasi ochiladi |
| Saqlangan balans ustuni | — | BILL-03 **taqiqlaydi**; drift ⇒ nizo |
| Alohida `billing_runs` jadvali (ARCHITECTURE.md:309) | `system_heartbeats['billing_close']` | Yurak urishi naqshi allaqachon bor (`day_close.py:321-353`) va `DayCloseResult` shaklidagi sanoqlarni yozadi. Yangi jadval **qo'shilmaydi** — 6-faza allaqachon 5 jadval qo'shadi |
| `react-konva` xarita | mavjud CSS Grid xarita | `02-UI-SPEC §7.1` — Konva **o'rnatilMAYDI**; xarita allaqachon bor |

---

## Package Legitimacy Audit

**Bu faza birorta yangi paket o'rnatmaydi** — `pyproject.toml` va `package.json` ga **hech qanday qator qo'shilmaydi**.

| Package | Registry | Disposition |
|---------|----------|-------------|
| — | — | Yangi paket YO'Q; slopcheck qo'llanadigan yuza mavjud emas |

⚠ Agar reja biror yangi paketni taklif qilsa (masalan pul formatlash yoki idempotentlik uchun kutubxona), u **avtomatik shubhali**: uchala vazifa ham mavjud kodda bor (`money.py`, `UNIQUE` konstrayti). Yangi paket qo'shilsa `slopcheck install <pkg> --json` + `pip index versions <pkg>` (Python) yoki `npm view <pkg> version` (JS) majburiy va natija `checkpoint:human-verify` bilan darvoza ortiga qo'yiladi.

---

## Architecture Patterns

### System Architecture Diagram

```
                       KUN DAVOMIDA (D kuni, 06:00–18:00)
  ┌───────────┐   HTTP GET /billing/pending?stall_code=NN
  │  Kassir   │──────────────────────────────────────────────┐
  │ (telefon) │                                              │
  └─────┬─────┘                                              ▼
        │  POST /payments  (Idempotency: client UUID)   ┌──────────────────────┐
        │  ─────────────────────────────────────────▶   │ resolve_stall_day_   │
        │                                               │ money(market, as_of) │◀── tariffs
        │                                               │  (BITTA umumiy yo'l) │◀── stall_category_periods
        │                                               └──────────┬───────────┘◀── stall_assignments
        │                                                          │
        ▼                                                          ▼
  ┌──────────────────────────────┐   qoldiq join    ┌────────────────────────────┐
  │ payments  (append-only)      │◀─────────────────│ pending = tarif + qoldiq   │
  │ UNIQUE(market_id, idem_key)  │                  │ (⚠ charge_id YO'Q — D-17)  │
  │ kind ∈ {payment, reversal}   │                  └────────────────────────────┘
  └──────────────┬───────────────┘
                 │
                 ▼
        ┌────────────────────┐         ┌──────────────────────────────┐
        │ cashier_shifts     │────────▶│ variance = declared − system │  (server, D-25)
        │ ko'r deklaratsiya  │         │ ikki tomonlama, D-26         │
        └────────────────────┘         └──────────────────────────────┘

                       ERTASI KUNI (D+1)
   03:40  occupancy.day_close(business_date = D)  ──▶ stall_slot_occupancy  (DO UPDATE)
                                                             │
   04:10  billing.close(business_date = D)                    │ FAQAT O'QISH (D-03)
          ├── active_market_ids()  (D-15)                     ▼
          ├── market_is_open(market, D)?  ──── yo'q ──▶ billing_anomalies(closed_day_occupied)
          ├── billable?  (≥2 occupied) OR (1 occupied AND human-confirmed-occupied)   ← C-6
          │      │
          │      ├── hammasi no_coverage ──▶ billing_anomalies(no_coverage_stall)   D-05
          │      └── biriktirilgan sotuvchi YO'Q ──▶ billing_anomalies(unassigned_occupied)  D-28
          │
          └── resolve_stall_day_money(market, as_of = D)
                     │
                     ▼
          ┌───────────────────────────────────────────┐
          │ daily_charges  (O'ZGARMAS — trigger)      │
          │ UNIQUE(market_id, stall_id, service_date) │──▶ charge_evidence (muzlatilgan nusxa)
          │ ON CONFLICT DO NOTHING  (D-06)            │        occupancy_event_id  ← DALIL (C-7)
          │ tariff_id + tariff_amount_soum  (D-09)    │        snapshot_id         ← kadrga yo'l
          │ vendor_id (muzlatilgan)                   │
          └───────────────┬───────────────────────────┘
                          │
                          ▼
                 charge_adjustments (sabab-kod, ± direction)  ──▶ balans = Σcharges + Σadj − Σsigned(payments)
                                                                    (KO'RINISH, saqlangan ustun YO'Q — BILL-03)
```

### Recommended Project Structure (mavjud daraxtga qo'shiladigan)

```
packages/sbozor-core/sbozor_core/
├── models/billing.py                # daily_charges, charge_adjustments, payments,
│                                    #   cashier_shifts, billing_anomalies, charge_evidence
├── enums.py         (MOD)           # PaymentKind, PaymentMethod, AdjustmentReason,
│                                    #   ReversalReason, AnomalyKind, ShiftStatus + AuditAction a'zolari
└── billing.py                       # SOF funksiyalar: billable_from_slots(), variance()

services/core-api/app/
├── jobs/billing_close.py            # day_close.py:1-354 ning shaklidagi juft
├── repositories/billing_repo.py     # resolve_stall_day_money(), charge yozish, balans
├── repositories/payment_repo.py     # idempotent INSERT + qayta SELECT, storno
├── api/v1/billing.py                # GET /billing/pending, GET /billing/charges
├── api/v1/payments.py               # POST /payments, POST /payments/{id}/reverse
├── api/v1/shifts.py                 # POST /shifts, POST /shifts/{id}/close
└── worker.py         (MOD)          # BILLING_CLOSE_CRON + billing_close_task

migrations/
├── versions/0020_billing_domain.py  # 6 jadval + RLS + policy + trigger + UNIQUE
├── versions/0021_market_delete_billing.py   # kaskad (0019 naqshi)
└── entities/triggers.py  (MOD)      # charge_immutable(), payment_immutable(),
                                     #   shift_declaration_immutable()

frontend/src/
├── app/[locale]/(app)/collect/page.tsx      # kassir oqimi
├── app/[locale]/(app)/collect/shift/page.tsx
├── components/collect/stall-lookup.tsx     # autoFocus + Enter (02-UI-SPEC §6.9)
├── components/collect/payment-bar.tsx      # useRef qulfi (D-22) — decision-bar naqshi
├── components/collect/reason-dialog.tsx    # yopiq sabab-kod ro'yxati (D-19)
├── components/collect/shift-close-form.tsx # ko'r deklaratsiya (D-25)
└── lib/billing-queries.ts, payment-queries.ts
```

### Pattern 1: Yangi tenant jadvali — OLTI JOY (`05-PATTERNS.md §S-1`)

Har yangi jadval uchun **oltita** joy yangilanadi, aks holda darvozalardan biri qizaradi:

1. `migrations/entities/__init__.py` — `BILLING_TENANT_TABLES` + `ALL_TENANT_TABLES`
2. `0020_billing_domain.py` — `op.create_table` + `enable_tenant_rls` + `tenant_policy` + `owner_bootstrap_policy`
3. `sbozor_core/schema_contract.py::AUDITED_TABLES` — **faqat** trigger ulanadigan jadvallar
4. `sbozor_core/models/__init__.py` barreli
5. `tests/fixtures/billing_domain.py` seed
6. `BILLING_DELETE_ORDER` + `market_delete_draft()` kaskadi (`0021`)

⚠ **Har jadvalda:** `market_id` + RLS `ENABLE` **va** `FORCE` + tenant policy + `market_id` bilan **boshlanadigan** domen konstraytlari + kompozit FK. `market_id` ustunida inline `ForeignKey` **YOZILMAYDI** (`models/base.py::market_fk_column()`).
⚠ **PG `ENUM` tipi ISHLATILMAYDI** — `text` + enum'dan **hosila** `CHECK` (`models/occupancy.py:60-64`).
⚠ `test_meta.py::test_tenant_indexes_lead_with_market_id` — har indeks/UNIQUE `market_id` bilan boshlanadi; istisno **`INDEX_EXCEPTIONS` ga sabab bilan** yoziladi.

### Pattern 2: O'zgarmaslik triggeri — `0018` naqshining aynan takrori

**What:** trigger FUNKSIYASI `migrations/entities/triggers.py` da (`alembic-utils` `PGFunction`), triggerning O'ZI migratsiyada `attach_immutability_trigger(table, function, name)` bilan (`migrations/helpers.py:269-304`).
**When:** `daily_charges`, `payments`, va `cashier_shifts` ning **deklaratsiya maydonlari**.
**Example (`ZONE_REVIEW_IMMUTABLE`, `triggers.py:520-540` dan hosila):**
```sql
CREATE OR REPLACE FUNCTION charge_immutable() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
BEGIN
  IF TG_OP = 'DELETE'
     AND EXISTS (SELECT 1 FROM public.markets AS m
                  WHERE m.id = OLD.market_id AND m.is_active = false) THEN
    RETURN OLD;                       -- FAQAT qoralama bozor (market_delete_draft yo'li)
  END IF;
  RAISE EXCEPTION 'daily_charges is append-only (attempted %)', TG_OP;
END $$;
```
⚠ `RETURN OLD` **faqat** istisno shoxida: `BEFORE DELETE` `NULL` qaytarsa amal **jimgina** bekor bo'ladi va kaskad "o'chirdim" deb yolg'on gapirardi (`triggers.py:508-512`).
⚠ Har jadval **o'z funksiyasiga** ega — `TG_TABLE_NAME` bo'yicha shoxlanadigan umumiy funksiya taqiqlanadi (`helpers.py:278-282`).
⚠ `BEFORE` `AFTER` dan oldin yuradi, ya'ni rad etilgan `UPDATE` `audit_log` ga qator **qoldirmaydi** (`helpers.py:295-298`).

### Pattern 3: Argumentli, konvergent, hech qachon yiqilmaydigan job

`app/jobs/day_close.py` **verbatim shablon**: har bozor uchun **alohida tranzaksiya**, xato **yutiladi va TURI bilan** `errors` ga yoziladi, `active_market_ids()` dan ro'yxat, oxirida `system_heartbeats` ga qisqa alohida tranzaksiyada yozuv, `taskiq` **import qilinmaydi**.
```python
async def billing_close(sessionmaker, *, business_date: date) -> BillingCloseResult:
    market_ids = await active_market_ids(sessionmaker)     # D-15
    for market_id in market_ids:
        try:
            await _close_market(sessionmaker, market_id=market_id,
                                business_date=business_date, result=result)
        except SQLAlchemyError as exc:
            result.errors.append(f"billing_close_failed:{type(exc).__name__}")
    await _write_heartbeat(sessionmaker, result)
    return result
```
⚠ `_close_market` **o'qish va yozishni bitta tranzaksiyada** qiladi (`day_close.py:241-248` sababi: izchillik, poyga emas).
⚠ **NOL — NATIJA**: `BillingCloseResult` da `charged`, `skipped_unbilled`, `anomalies_unassigned`, `anomalies_closed_day`, `anomalies_no_coverage` **har doim** qaytariladi (`day_close.py:130-150` qoidasi).

### Pattern 4: Idempotent to'lov — IKKI BAYONOT, bitta tranzaksiya

**What:** `INSERT ... ON CONFLICT DO NOTHING RETURNING *`; qator qaytmasa — **alohida** `SELECT`.
**Why:** `RETURNING` faqat haqiqatan yozilgan qatorlarni beradi ([PostgreSQL 18 `INSERT`](https://www.postgresql.org/docs/18/sql-insert.html): *"Only rows that were successfully inserted or updated will be returned"*). CTE + `UNION ALL` shakli **yaramaydi**: CTE ning `SELECT` qismi tranzaksiya snapshotini ko'radi.
**Isolation:** **READ COMMITTED** (PostgreSQL va SQLAlchemy standarti) — ikkinchi bayonot **yangi snapshot** oladi, ya'ni parallel yutgan tranzaksiyaning qatorini ko'radi. ⛔ `REPEATABLE READ` ga o'tkazilsa bu naqsh **jimgina buziladi**.
**Wave 0 zondi (MAJBURIY, `BILLABLE_ANCHOR_SUPPORTED` naqshi):** ikki parallel sessiya bir xil `idempotency_key` bilan yozadi; o'lchanadigan natija — **bitta** qator, **ikkala** so'rov ham **bir xil** `id` ni qaytaradi, ikkinchisi 409 **bermaydi**.

### Anti-Patterns to Avoid

- **Saqlangan balans ustuni** — BILL-03 ni buzadi va drift nizoga aylanadi.
- **`UPDATE daily_charges` / `DELETE + INSERT`** — trigger rad etadi; tuzatish faqat `charge_adjustments`.
- **`vendor_id NULL` bilan hisob** — D-28: "kimdir qarzdor, lekin kim ekani noma'lum".
- **`float`/`Decimal` pul ustuni** — `money.py` boundary'da `TypeError`; lint darvozasi ham (D-11).
- **Manfiy `amount_soum`** — `CHECK` va `assert_safe_soum()` rad etadi (C-5).
- **`require_any_permission()` yangi marshrutda** — yopiq to'plam darvozasi qizaradi (C-9).
- **`_PER_STALL_CTE.human_confirmed` ni billingda ishlatish** — C-6.
- **`stall_slot_occupancy.id` ni yolg'iz dalil deb hisoblash** — C-7.
- **Kassir javobiga `vendor_name`/`phone` qo'shish** — C-10.
- **`business_date` ni hisoblanayotgan kun deb o'qish** — C-2; `service_date` ishlatiladi.
- **Bandlikni qayta agregatsiya qilish** (`occupancy_events` dan) — D-03; ikkinchi haqiqat manbai.
- **Ko'r deklaratsiya payloadiga tizim summasini "yashirin" qo'yish** — D-25: maydon **e'lon qilinmaydi**, `null` qilinmaydi.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Biznes-kun chegarasi | `date.today()` yoki qo'lda UTC±5 | `sbozor_core.timeutil.business_today()` / DB `BUSINESS_DATE_EXPR` | Toshkent 00:00–04:59 naive UTC da **oldingi kunga** tushadi (`timeutil.py:63-90`) |
| Tarixiy tarif/toifa yechimi | yangi so'rov | `stall_repo.py:595-635` `LEFT JOIN LATERAL … ORDER BY valid_from DESC LIMIT 1` | Allaqachon o'lchangan; faqat `t.id` qo'shiladi (D-09) |
| "Shu kunda kim biriktirilgan?" | `>=`/`<` qo'lda | `sa.period @> :day` (GiST) — `review_repo.py:189-196` | `[)` chegara konventsiyasi **faqat** `periods.py` da yashaydi (`periods.py:47-60`) |
| `[)` davr qurish | `Range(...)` / `daterange(...)` | `sbozor_core.periods.assignment_period()` | Ikkinchi konventsiya almashinuv kunida **ikki sotuvchiga** patta yozardi |
| Yopiq kun tekshiruvi | `open_weekdays` ni o'qib qo'lda | `market_is_open(market_id, date)` (`functions.py:1345-1366`) | Uch qavatli `COALESCE`, fail-closed, **INVOKER** (RLS ostida) |
| Pul formatlash / tekshirish | qo'lda `f"{v:,}"` | `money.format_soum()` / `assert_safe_soum()` | NBSP ajratgich, 3 locale, `bool`/`float` rad etish (`money.py`) |
| Bandlik agregatsiyasi | yangi `CASE` | `stall_slot_occupancy` **o'qiladi** (D-03) | Ikkinchi agregatsiya = ikkinchi haqiqat |
| Idempotentlik | ilova qatlamida "avval tekshir, keyin yoz" | `UNIQUE` + `ON CONFLICT` + qayta `SELECT` | `nvr_repo.py:507-517`: poyga **DB ga topshiriladi** |
| Bitta ochiq smena | ilovada "ochiq smena bormi?" | qisman UNIQUE indeks (`ALERT_OPEN_INDEX` naqshi, `snapshot.py:209-222`) | `NULL` UNIQUE da o'ziga teng emas — `COALESCE` sentinel yoki `WHERE status='open'` |
| O'zgarmaslik | ORM `@validates` | DB trigger (`attach_immutability_trigger`) | Xom SQL/migratsiya ilova validatsiyasini chetlab o'tadi |
| Audit yozuvi | qo'lda `INSERT INTO audit_log` | `write_app_audit(...)` (`security/audit.py:253-315`) yoki DB trigger | `principal` dan standart qiymatlar, `changed_keys` mantig'i |
| O'qish auditi | qo'lda | `Depends(audit_read(TABLE, reason=...))` (`audit.py:410`) | Shaxsiy ma'lumot darvozasi shu tegni **o'qiydi** |
| Kassir mijoz qulfi | `isPending` | `useRef` latch (`blind-session.tsx:92`, `review-session.tsx`) | 05-13 o'lchagan: `isPending` faqat **keyingi** renderda |
| uz-Cyrl tarjima | qo'lda yozish | `npm --prefix frontend run i18n:gen` | `uz-Cyrl.json` **generatsiya**; `--check` CI darvozasi |

**Key insight:** bu fazada "qo'lda yozish" xatosi deyarli har doim **ikkinchi haqiqat manbai** shaklida keladi va u pul raqamida ko'rinadi — ya'ni aynan D-02 nomlagan nizo sinfida. Har qayta yozilgan so'rov "kassir yig'gan summa" va "kechqurun yozilgan summa" ni ajratib yuborishning bitta yo'li.

---

## Runtime State Inventory

> Bu faza rename/refactor emas, LEKIN u **kod tashqarisidagi holatga** tegadi: cron ro'yxati, ikki tildagi RBAC ko'zgusi, reyestrlar, generatsiya qilinadigan i18n fayli. Shuning uchun inventar to'ldiriladi.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Saqlangan ma'lumot** | Yangi jadvallarda **eski ma'lumot yo'q** (6 jadval nol holatdan tug'iladi). ⚠ `stall_slot_occupancy` da **mavjud kunlar bo'lishi mumkin** (5-faza test/seed ma'lumoti) — birinchi `billing.close` ularni ham hisoblaydi | Migratsiya **backfill qilmaydi**. Reja `billing.close` ni **qaysi kundan boshlab** yugurtirishni aniq yozadi (tavsiya: faqat kelgusi kunlar; tarixiy kunlar qo'lda argument bilan) |
| **Jonli servis konfiguratsiyasi** | `taskiq scheduler` **jarayoni** cron ro'yxatini `app.worker:scheduler` **import** paytida oladi (`worker.py:55-58`); jadval `LabelScheduleSource` orqali kod dekoratorlaridan keladi, DB/UI da EMAS | Yangi `billing_close_task` qo'shilgach **`scheduler` konteyneri qayta ishga tushirilishi SHART** — aks holda vazifa hech qachon rejalashtirilmaydi va xato ham chiqmaydi |
| **OS-registered state** | Yo'q — cron OS da emas, `taskiq scheduler` ichida | — |
| **Secrets/env vars** | Yangi sir **KERAK EMAS**. Mavjudlar (`VALKEY_URL`, `NVR_CREDENTIAL_KEY`, Sentry DSN) o'zgarmaydi | — |
| **Build artefaktlari / generatsiya** | (a) `frontend/messages/uz-Cyrl.json` — **generatsiya**, qo'lda tahrirlanmaydi; (b) Alembic `head` = `0019` (`0019_market_delete_occupancy.py:64`), ya'ni yangi revizyalar **`0020`, `0021`**; (c) `openapi` sxemasi darvoza testlari uchun ilovadan hosila | (a) `npm --prefix frontend run i18n:gen` har matn o'zgarishida; (b) revizya raqamlari to'g'ri zanjirda; (c) yangi marshrutlar `MINIMUM_MATRIX_ROUTES` (hozir **60**, `test_route_coverage.py:49`) chegarasini **ko'tarishni** talab qiladi |
| **Reyestrlar (kod ichidagi "holat")** | `FINANCIAL_TABLES` (3 nom **allaqachon** kutilyapti), `AUDITED_TABLES`, `ALL_TENANT_TABLES`, `BILLING_DELETE_ORDER`, `DEFINER_SURFACES`, `INDEX_EXCEPTIONS`, `PERSONAL_ROUTES`, `SNAPSHOT_EVIDENCE_FRAME_ROUTES` | Har biri **jadval/marshrut tug'ilgan commitda** yangilanadi. `PENDING_AUDIT_TRIGGERS` **bo'sh qolishi** kerak — bir migratsiyada ikkalasini ham qilish mumkin (`test_meta.py:240-247`) |

---

## Common Pitfalls

### Pitfall 1 — `business_date` ning IKKI ma'nosi
**Nima buziladi:** `daily_charges` ni `stall_slot_occupancy` bilan `business_date` bo'yicha join qilish. Normal kunda (job 04:10 da yuguradi, kun D) `daily_charges.business_date` = **D+1**, `stall_slot_occupancy.business_date` = **D** → join **0 qator**.
**Nega:** `financial_guards()` ning generated ustuni "qator yozilgan kun", occupancy zanjiri esa "ma'lumot tegishli kun" (C-2).
**Qanday oldini olish:** domen ustuni **`service_date`**; ikkala ma'no ustun docstringida yonma-yon; semantik invariant testi (`## Validation Architecture` G-2).
**Ogohlantiruvchi belgi:** hisobot bo'sh, xato yo'q.

### Pitfall 2 — 20:30 croni bilan "hammasi ishlayapti"
**Nima buziladi:** `billing.close` yuguradi, `errors` bo'sh, `charged = 0`. Test seed'da bandlikni **qo'lda** yozgani uchun yashil qoladi.
**Nega:** `stall_slot_occupancy` D kuni uchun 03:40 (D+1) da to'ladi (C-3).
**Qanday oldini olish:** faza darvozasida **ketma-ketlik testi**: `day_close(D)` **chaqirilmasdan** `billing_close(D)` → `charged = 0` **va** natija `no_slot_rows` sanog'ini qaytaradi; keyin `day_close(D)` → `billing_close(D)` → `charged > 0`. Ikki holat **ajralishi** shart (D-30 ning ikkinchi savoli).

### Pitfall 3 — `ON CONFLICT DO NOTHING` va `RETURNING` sukunati
**Nima buziladi:** `payment_repo` `RETURNING` dan `None` oladi va uni "xato" deb 500 qaytaradi (yoki, yomoni, `None` ni javobga solib yuboradi).
**Nega:** konflikt qatorni **qaytarmaydi**.
**Qanday oldini olish:** `None` → **majburiy** qayta `SELECT`; agar u ham bo'sh bo'lsa — bu **invariant buzilishi**, aniq xato bilan yiqilish (jimgina 200 emas).

### Pitfall 4 — Bir xil kalit, BOSHQA payload
**Nima buziladi:** kassir kalitni saqlab, summani o'zgartirib qayta yuboradi (yoki xato retry) → server **eski** to'lovni 200 bilan qaytaradi va yangi summa **jimgina yo'qoladi**.
**Nega:** D-21 faqat "o'sha to'lovni qaytar" deydi, payload solishtirishni aytmaydi. Stripe esa parametrlarni solishtiradi va **xato** beradi ([Stripe](https://docs.stripe.com/api/idempotent_requests)).
**Qanday oldini olish:** `request_fingerprint` (muhim maydonlar xeshi) saqlanadi; mos kelmasa **409** `idempotency_key_reused`. Bu D-21 ni buzmaydi — u faqat **aynan bir xil** so'rov uchun 200 talab qiladi.

### Pitfall 5 — Kech kelgan nazoratchi tasdig'i
**Nima buziladi:** nazoratchi D kunini D+1 kunduzida tasdiqlaydi; `billing.close` allaqachon 04:10 da yugurgan. Hisob **yo'q** bo'lib qoladi (yoki ortiqcha bo'lib qoladi) va hech kim sezmaydi.
**Qanday oldini olish:** (a) `day_close` qayta yugurishi `stall_slot_occupancy` ni yangilaydi; (b) `billing.close` ni qayta chaqirish **yo'q hisobni yaratadi** (`DO NOTHING` faqat mavjudini himoya qiladi); (c) **mavjud** hisobni kamaytirish faqat `charge_adjustments(direction='decrease', reason_code='late_review')`. Uchalasi hujjatda va testda.

### Pitfall 6 — Ko'r deklaratsiya "yashirilgan" bo'lib qoladi
**Nima buziladi:** `ShiftCloseResponse` da `system_total_soum` maydoni bor, UI uni ko'rsatmaydi. Kassir DevTools/tarmoq javobida ko'radi → ko'rlik yo'q.
**Nega:** 5-fazada aynan shu (`shown_ai_verdict`) bir necha qatlamda qulflangan.
**Qanday oldini olish:** maydon **sxemada umuman e'lon qilinmaydi** (`null` emas); `frontend/scripts/*.test.mjs` sinfidagi darvoza smena katalogini ham skanerlaydi (D-25); serializator testi **to'plam tengligi** bilan (D-31), `not.toContain` bilan **emas**.

### Pitfall 7 — Variance ishorasi
**Nima buziladi:** `abs(variance)` saqlanadi yoki "kamomad" faqat bir tomonga hisoblanadi → ortiqcha naqd yo'qoladi (D-26 buzilishi).
**Qanday oldini olish:** `declared_soum` va `system_soum` **ikkalasi ham** saqlanadi (`> 0` CHECK bilan), variance **ko'rinishda** ayirma sifatida hisoblanadi. `assert_safe_soum()` manfiyni rad etganini yodda tuting — variance **ustun emas**.

### Pitfall 8 — Yangi marshrut darvozadan tushib qolishi
**Nima buziladi:** `EXEMPT_ROUTES` ga "vaqtincha" qo'shish yoki `MINIMUM_MATRIX_ROUTES` ni ko'tarmaslik.
**Qanday oldini olish:** har yangi marshrut `tests/tenancy/test_cross_tenant.py` matritsasiga **o'zi** kiradi; chegara (`60`) yangi son bilan **ko'tariladi** va izohga sabab yoziladi (`test_route_coverage.py:49-80` uslubi). D-32: qamrov **hosila**, qo'lda sanoq emas.

### Pitfall 9 — Tenant konteksti va yopiq kun tekshiruvi
**Nima buziladi:** `market_is_open()` job ichida **tenant kontekstisiz** chaqiriladi → RLS 0 qator → `false` → **hamma kun yopiq** → hisob umuman yozilmaydi.
**Nega:** funksiya ATAYIN `SECURITY DEFINER` **emas** (`functions.py:1369-1376`), fail-closed.
**Qanday oldini olish:** chaqiruv **`set_tenant_context()` ostidagi** sessiyada (`day_close.py:208-231` `_tenant_session` naqshi). Sabotaj: kontekstni olib tashlash → **hamma kun anomaliya** bo'lib chiqishi kerak, jimgina 0 emas.

### Pitfall 10 — `scheduler` qayta ishga tushirilmasligi
**Nima buziladi:** kod yozildi, testlar yashil, prodda `billing.close` **hech qachon** ishlamaydi.
**Qanday oldini olish:** deploy bandi `## Runtime State Inventory` da; `system_heartbeats['billing_close']` ning **yo'qligi** 4-fazaning alert mexanizmi bilan ko'rinadi (`alert_sweep`).

---

## Code Examples

### 1. D-04 predikati — `_PER_STALL_CTE` DAN HOSILA, LEKIN O'Z SHARTI BILAN (C-6)

```sql
-- Manba: occupancy_repo.py:364-384 shakli; farqi ATAYIN va u C-6 da yozilgan
WITH per_stall AS (
    SELECT sso.stall_id,
           count(*) FILTER (WHERE sso.verdict = :occupied)          AS occupied_slots,
           bool_or(sso.verdict = :occupied
                   AND sso.resolution_source = :human)             AS human_confirmed_occupied,
           bool_or(sso.verdict <> :no_coverage)                     AS has_any_coverage
      FROM stall_slot_occupancy sso
     WHERE sso.market_id = :market_id
       AND sso.business_date = :service_date          -- ⚠ occupancy tomonda `business_date`
     GROUP BY sso.stall_id
)
SELECT stall_id,
       (occupied_slots >= 2)
       OR (occupied_slots >= 1 AND human_confirmed_occupied)        AS billable,
       NOT has_any_coverage                                         AS no_coverage_stall
  FROM per_stall
```
⚠ `no_coverage` slotlari `occupied_slots` ga **kirmaydi** (D-05 avtomatik bajariladi), lekin **butunlay qamrovsiz rasta** alohida bayroq bilan chiqadi.

### 2. Tarixiy tarif + biriktirish — MAVJUD so'rovning kengaytmasi (D-09)

```sql
-- Manba: services/core-api/app/repositories/stall_repo.py:595-635
-- FARQ: (a) :today -> :service_date, (b) t.id HAM olinadi (D-09: tariff_id + summa)
LEFT JOIN LATERAL (
  SELECT p.category_id
    FROM stall_category_periods p
   WHERE p.market_id = s.market_id AND p.stall_id = s.id
     AND p.valid_from <= :service_date
   ORDER BY p.valid_from DESC LIMIT 1
) cur ON true
LEFT JOIN LATERAL (
  SELECT t.id AS tariff_id, t.amount_soum          -- ⚠ t.id QO'SHILDI
    FROM tariffs t
   WHERE t.market_id = s.market_id AND t.category_id = cur.category_id
     AND t.valid_from <= :service_date
   ORDER BY t.valid_from DESC LIMIT 1
) tar ON true
LEFT JOIN LATERAL (
  SELECT sa.vendor_id
    FROM stall_assignments sa
   WHERE sa.market_id = s.market_id AND sa.stall_id = s.id
     AND sa.period @> :service_date                -- `[)` — almashinuv kuni YANGI sotuvchiga
   LIMIT 1
) asg ON true
```

### 3. Idempotent hisob yozish (D-06) — `DO NOTHING`, `DO UPDATE` EMAS

```python
# Manba: app/jobs/day_close.py:89 (pg_insert) + fixtures/financial.py:103-106 shakli
stmt = (
    pg_insert(DailyCharge)
    .values(
        market_id=market_id, stall_id=stall_id, service_date=business_date,
        vendor_id=vendor_id, tariff_id=tariff_id,
        tariff_amount_soum=amount, amount_soum=amount,     # D-09: IKKALASI ham
    )
    .on_conflict_do_nothing(
        index_elements=["market_id", "stall_id", "service_date"]
    )
    .returning(DailyCharge.id)
)
charge_id = (await session.execute(stmt)).scalar_one_or_none()
if charge_id is None:
    return None          # allaqachon bor — O'ZGARMAS, tegilmaydi (D-07)
```

### 4. Idempotent to'lov — ikki bayonot (CASH-03 / D-21)

```python
# Manba: PostgreSQL 18 INSERT docs (RETURNING faqat yozilgan qatorni beradi)
#       + nvr_repo.py:507-517 ("poyga DB ga topshiriladi")
stmt = (
    pg_insert(Payment)
    .values(**payload, idempotency_key=key, request_fingerprint=fingerprint)
    .on_conflict_do_nothing(index_elements=["market_id", "idempotency_key"])
    .returning(Payment.id, Payment.amount_soum, Payment.request_fingerprint)
)
row = (await session.execute(stmt)).one_or_none()
created = row is not None
if row is None:
    # ⚠ ALOHIDA bayonot: READ COMMITTED da yangi snapshot, ya'ni parallel
    #    yutgan tranzaksiyaning qatori KO'RINADI. CTE + UNION ALL YARAMAYDI.
    row = (await session.execute(
        select(Payment.id, Payment.amount_soum, Payment.request_fingerprint)
        .where(Payment.market_id == market_id, Payment.idempotency_key == key)
    )).one_or_none()
    if row is None:
        raise RuntimeError("idempotency invariant buzildi")      # jimgina 200 EMAS
if row.request_fingerprint != fingerprint:
    raise HTTPException(409, "idempotency_key_reused")            # Pitfall 4
return row, created            # created=False -> 200, created=True -> 201
```

### 5. Bitta ochiq smena (D-27) — qisman UNIQUE

```python
# Manba: models/snapshot.py:209-222 (ALERT_OPEN_INDEX) naqshi
SHIFT_OPEN_INDEX = "uq_cashier_shifts_market_id_cashier_open"
SHIFT_OPEN_PREDICATE = f"status = '{ShiftStatus.OPEN.value}'"     # enum'dan HOSILA
Index(SHIFT_OPEN_INDEX, "market_id", "cashier_id",
      unique=True, postgresql_where=text(SHIFT_OPEN_PREDICATE))
```
⚠ Indeks **modelda ham** e'lon qilinadi — aks holda `test_autogenerate_is_empty` `remove_index` bilan qizaradi (`models/occupancy.py:350-358`).

### 6. Kassir qulfi (D-22) — `decision-bar` naqshi

```tsx
// Manba: frontend/src/components/blind-audit/blind-session.tsx:85-125
const submittedRef = useRef<string | null>(null);   // ⚠ isPending EMAS — u keyingi renderda
const submit = useCallback((method: PaymentMethod) => {
  if (idempotencyKey === null || submittedRef.current === idempotencyKey) return;
  submittedRef.current = idempotencyKey;
  pay.mutate({ idempotencyKey, method, stallId },
    { onError: () => { submittedRef.current = null; } });
}, [idempotencyKey, stallId, pay]);
```

### 7. Balans — KO'RINISH, saqlangan ustun EMAS (BILL-03 / C-5)

```sql
-- Belgi KO'RINISHDA hosil bo'ladi; ustun har doim MUSBAT (C-5)
SELECT v.id AS vendor_id,
       COALESCE(ch.total, 0) + COALESCE(adj.total, 0) - COALESCE(pay.total, 0) AS balance_soum
  FROM vendors v
  LEFT JOIN LATERAL (SELECT sum(c.amount_soum) AS total FROM daily_charges c
                      WHERE c.market_id = v.market_id AND c.vendor_id = v.id) ch ON true
  LEFT JOIN LATERAL (SELECT sum(CASE WHEN a.direction = 'increase'
                                     THEN a.amount_soum ELSE -a.amount_soum END) AS total
                       FROM charge_adjustments a
                       JOIN daily_charges c2 ON c2.market_id = a.market_id AND c2.id = a.charge_id
                      WHERE a.market_id = v.market_id AND c2.vendor_id = v.id) adj ON true
  LEFT JOIN LATERAL (SELECT sum(CASE WHEN p.kind = 'reversal'
                                     THEN -p.amount_soum ELSE p.amount_soum END) AS total
                       FROM payments p
                      WHERE p.market_id = v.market_id AND p.vendor_id = v.id) pay ON true
 WHERE v.market_id = :market_id
```
**Indekslar (majburiy):** `daily_charges (market_id, vendor_id, service_date)`, `daily_charges (market_id, service_date, stall_id)`, `payments (market_id, vendor_id, service_date)`, `payments (market_id, stall_id, service_date)`, `charge_adjustments (market_id, charge_id)`.
**Miqyos:** 1000 rasta × 365 kun ≈ **365 k** hisob/yil/bozor — indeksli agregat bu hajmda muammo emas. Materializatsiya qilingan ko'rinish **kerak emas** va u BILL-03 ni buzardi.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact bu fazaga |
|--------------|------------------|--------------|--------|
| `charges` (CONTEXT.md) | **`daily_charges`** | 1-faza (`01-03-PLAN.md:131`) | C-1 |
| Cron 20:30 (D-13) | **`day_close` dan keyin, kechasi** | 5-faza (`worker.py:410-440`) | C-3 |
| Belgili summa ledger | **Kattalik + `kind`** | `money.py` + `test_meta.py:1346` | C-5 |
| `payments.charge_id` (D-24) | **Sotuvchi darajasidagi kredit + `service_date`** | tavsiya (C-4); `ARCHITECTURE.md:371-373` ham `(stall_id, business_date)` bilan join qilgan | C-4 |
| `pg_advisory_xact_lock` billing run uchun (`ARCHITECTURE.md:305`) | **UNIQUE + `ON CONFLICT`** | 1-faza mezon #5 | Advisory lock **qo'shilmaydi** |
| `billing_runs` jadvali (`ARCHITECTURE.md:309`) | **`system_heartbeats` + `*Result` dataclass** | 4/5-faza | Yangi jadval yo'q |
| `stall_day_occupancy` (`ARCHITECTURE.md:316`) | **`stall_slot_occupancy`** (slot kesimida) | 5-faza | Ikkinchi darajali agregatsiya 6-fazada, SLOT lardan |
| `ON CONFLICT DO NOTHING` + qayta SELECT | `ON CONFLICT DO SELECT` (PG 19) | PG 19 (beta) | ⛔ PG 19 taqiqlangan; naqsh o'zgarmaydi |
| `valid_to` ustuni | `LEAD(valid_from)` | 2-faza (`market.py:494-498`) | Tarif yechimida `valid_to` **yo'q** |

**Deprecated/outdated (bu fazada ishlatilmaydi):**
- `.planning/research/ARCHITECTURE.md` (2026-07) — `daily_charges.business_date` ni **oddiy ustun** deb ko'rsatadi (`:330`) va `tariffs.valid_to`/`daily_amount_soum` deb yozadi (`:337-339`). **Uchalasi ham bugungi sxemada YO'Q.** Faylni namuna sifatida ko'chirish sxema xatosiga olib keladi; u faqat **niyat** hujjati sifatida o'qiladi.
- `01-RESEARCH.md:1199-1218` — `daily_charges` DDL'i `business_date` ni generated qilib, UNIQUE ni **shu ustunga** qo'yadi. Bu C-2 ning **manbasi**: DDL o'sha paytda to'g'ri ko'rinardi, chunki job argumentli emas deb taxmin qilingan edi.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ON CONFLICT DO NOTHING` parallel yozuvda kutadi, so'ng alohida `SELECT` (READ COMMITTED, yangi snapshot) yutgan qatorni **ko'radi** | §Pattern 4 | Idempotentlik oynasi ochiq qoladi: ikkinchi so'rov 500 beradi. **Yumshatish:** Wave 0 zondi (ikki parallel sessiya, haqiqiy `postgres:18.4`) — `BILLABLE_ANCHOR_SUPPORTED` naqshi. `[ASSUMED]` |
| A2 | `business_date date GENERATED ALWAYS AS (service_date) STORED` PG 18 da ruxsat etiladi (C-2 ning ikkinchi varianti) | C-2 | Variant B umuman ishlamaydi → Variant A (tavsiya etilgan) baribir qoladi. Zond bilan o'lchanadi. `[ASSUMED]` |
| A3 | Sabab-kodlar boshlang'ich to'plami (OQ-3) buyurtmachi bilan **kelishilmagan** | §OQ-3 | Kodlar keyin o'zgarsa `CHECK` enum'dan hosila bo'lgani uchun migratsiya kerak. **Yumshatish:** to'plamni kichik boshlash, `other` **QO'SHMASLIK** (erkin matn qaytib kelardi). `[ASSUMED]` |
| A4 | Qisman to'lov (OQ-4) ruxsat etiladi | §OQ-4 | Agar taqiqlansa `amount_soum` = to'liq patta bo'lishi `CHECK` bilan majburlanadi. `[ASSUMED]` |
| A5 | Direktor smenasiz to'lov kirita olmaydi (OQ-6) | §OQ-6 | `shift_id NOT NULL` qilinsa direktor yo'li bloklanadi. Tavsiya: `NULL` ruxsat + `actor` auditda. `[ASSUMED]` |
| A6 | Variance chegarasi (OQ-7) — MVP da alert **yo'q** | §OQ-7 | Katta kamomad kechikib ko'rinadi. `alert_events` mexanizmi tayyor, qo'shish arzon. `[ASSUMED]` |
| A7 | Kassir vendor ismini ko'rmasligi mahsulot uchun **qabul qilinadi** (C-10) | C-10 | Kassir ekranida "kim to'layapti" ko'rinmaydi. `[ASSUMED]` — buyurtmachi tasdig'i kerak |
| A8 | `billing.close` **kuniga bir marta** (04:10) yetarli; kech tasdiqlar `charge_adjustments` bilan | C-3 | Kech tasdiqlar hisobga kirmay qoladi va qo'lda tuzatish ko'payadi. `[ASSUMED]` |

---

## Open Questions (CONTEXT.md OQ-1…OQ-7 — javoblar)

### OQ-1 — Kassir qurilmasi: PWA yoki mavjud Next.js marshruti?
**Javob: mavjud Next.js ilovasining mobil marshruti** (`app/[locale]/(app)/collect/`), PWA **emas**.
Dalil: (a) PWA manifest/service-worker repoda **yo'q** (`frontend/src/app` da `manifest` fayli topilmadi) va uni qo'shish offline keshlash kutilmasini tug'diradi — `V2-CASH-05` esa offline'ni **v2 ga** qo'ygan; (b) `(app)/layout.tsx` allaqachon auth/tenant/role qatlamini beradi; (c) `next-intl` locale marshrutlanishi tayyor.
**Tarmoq uzilishida nima ko'rinadi (bu fazada hal bo'ladi):** TanStack Query mutatsiyasi xato beradi → `sonner` toast "qayta urinish" bilan; **idempotentlik kaliti saqlanib qoladi** (to'lov varag'i yopilmaguncha), ya'ni qayta yuborish dublikat yaratmaydi (D-21). ⛔ Navbat/keshga yozish YO'Q.

### OQ-2 — Rasta raqamini topish: qidiruv yoki raqamli klaviatura?
**Javob: ikkalasi ham EMAS — `autoFocus` + `inputMode="numeric"` + `Enter`.** Kontrakt 2-fazada **allaqachon yozilgan va o'lchangan**: `02-UI-SPEC.md:503-513` — *"rasta raqami bo'yicha topish ≤2 ta o'zaro ta'sirda"*, *"aynan bitta natija bo'lsa rasta kartasi darhol ochiladi"*, *"6-fazaning ≤3 bosishi shundan bitta bosishni oladi"*.
Ya'ni D-18 ning 3 qadamidan **birinchisi allaqachon 1 o'zaro ta'sir** (raqam terish + Enter = bitta qadam). Maxsus raqamli klaviatura komponenti **qurilmaydi**: `inputMode="numeric"` OS klaviaturasini ochadi, `code` esa `text` (12a, A-3 bo'lishi mumkin — `market.py:154-183`), ya'ni faqat raqamli panel ba'zi kodlarni **kiritib bo'lmaydigan** qilardi.
**Tartib:** `stalls.code_sort` (`market.py:154-183`) inson-raqamli tartibni beradi — ro'yxat ko'rsatilsa shu tartib ishlatiladi.

### OQ-3 — Sabab-kodlar ro'yxati kelishilganmi?
**Javob: NOMA'LUM — kelishilmagan** (`[ASSUMED]`, A3). `.planning/` da birorta kelishilgan ro'yxat topilmadi; `STATE.md:265` "7 ochiq buyurtmachi savoli — javoblar Phase 2 va Phase 6 batafsil rejasidan oldin kerak" deydi.
**Tavsiya (boshlang'ich yopiq to'plam, enum'dan hosila `CHECK`):**
- Summa o'zgarishi (`AdjustmentReason`): `late_review` (kech tasdiq), `ai_false_positive` (AI xato band dedi), `tariff_correction` (tarif noto'g'ri kiritilgan), `partial_day` (rasta kun o'rtasida bo'shatilgan), `director_waiver` (direktor kechirdi).
- Storno (`ReversalReason`): `wrong_stall`, `wrong_amount`, `duplicate_entry`, `customer_refund`.
⛔ **`other`/`custom` QO'SHILMAYDI** — u erkin matnni qaytarib keltiradi (D-19 ni bo'shatadi) va hisobotda **eng katta guruh** bo'lib qoladi.
⚠ Har kod **uchala tilda** tarjima kalitiga ega bo'lishi shart (`error-codes.test.mjs` sinfidagi darvoza).

### OQ-4 — Qisman to'lov ruxsat etiladimi?
**Javob: HA, texnik jihatdan tabiiy va tavsiya etiladi** (`[ASSUMED]`, A4). BILL-03 qoldiqni hisoblanadigan qilgani uchun qisman to'lov **qo'shimcha mantiqsiz** ishlaydi: `amount_soum` shunchaki kichikroq kredit. Ustiga C-4 ning modeli (sotuvchi darajasidagi kredit) **bir to'lov bir necha kunlik** qarzni yopishini ham qo'llab-quvvatlaydi — bu real bozor xulqi.
⛔ `CHECK (amount_soum = tariff_amount_soum)` **yozilmaydi** — u qisman to'lovni imkonsiz qilardi va kassir yumaloqlashga majbur bo'lardi.
⚠ Ortiqcha to'lov (balans manfiy) **ruxsat etiladi** va ekranda "avans" deb ko'rsatiladi — uni bloklash kassirni pulni **umuman yozmaslikka** majburlardi.

### OQ-5 — Bir kunda ikki sotuvchi (almashinuv) — patta kimga?
**Javob: KODDA ALLAQACHON HAL QILINGAN — yangi sotuvchiga.** `packages/sbozor-core/sbozor_core/periods.py:19-33`:
> **D-10 KONTRAKTI — ALMASHINUV KUNI YANGI SOTUVCHIGA TEGISHLI:** `[2026-08-01, 2026-08-10)` → eski sotuvchi … 08-09; `[2026-08-10, ∞)` → yangi sotuvchi 08-10, …

`ex_stall_assignments_no_overlap` (`market.py:619-625`) bir kunda **ikki** biriktirishni strukturaviy imkonsiz qiladi, ya'ni `sa.period @> :service_date` **ko'pi bilan bitta** qator beradi. Bo'shliq esa **ATAYIN mumkin** (`periods.py:29-33`) va u **aynan BILL-04 anomaliyasining manbai**.
⚠ `LIMIT 1` qo'yilsa ham `ORDER BY` **kerak emas** — konstrayt noyoblikni kafolatlaydi. Lekin test uni **o'lchashi** kerak (sabotaj: konstraytni olib tashlash → ikki biriktirish → qaysi patta yozilgani **aniqlanmaydigan** bo'lishi kerak).

### OQ-6 — Smenasiz to'lov (direktor tomonidan) mumkinmi?
**Javob: HA, `shift_id NULL` ruxsat etiladi** (`[ASSUMED]`, A5).
Sabab: (a) `shift_id NOT NULL` direktorni **smena ochishga** majburlardi va u `SHIFT_MANAGE` huquqini talab qilardi — ya'ni CASH-04 ning kassir modeli direktorga ham yopishtirilardi; (b) mahsulot qoidasi #5 (hech narsa jarayonni to'xtatmaydi); (c) aktor baribir `audit_log` da (`write_app_audit`).
⚠ Smena yopilishining **tizim summasi** faqat `shift_id` bog'langan to'lovlardan hisoblanadi — direktor to'lovi variance ga **kirmaydi** va bu **to'g'ri**: u kassir qutisiga tushmagan.
⚠ Hisobotda "smenasiz to'lovlar" **alohida sanoq** bo'lishi kerak, aks holda ular jimgina yo'qoladi (D-14 ruhida: o'lchanadigan miqdor).

### OQ-7 — Variance chegarasi bormi?
**Javob: MVP da alert YO'Q, variance faqat hisobotda** (`[ASSUMED]`, A6).
Mexanizm tayyor: `alert_events` + `alert_key` + qisman UNIQUE debounce (`models/snapshot.py:840-880`) + `AlertSender`. Chegara qo'shilsa u **bozor bo'yicha sozlanadigan** bo'lishi kerak, kodda literal emas — aks holda Karmana uchun tanlangan son barcha bozorlarga tarqaladi. Chegara **kelishilmagan** (buyurtmachi savoli), shuning uchun bu fazada `alert_key = 'shift_variance'` **yozilmaydi**; 8-faza (direktor hisobotlari) tabiiy egasi.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | Butun faza (RLS, generated columns, partial UNIQUE, GiST) | ✓ | `postgres:18.4-trixie` (compose) | — (SQLite **TAQIQ**: RLS yo'q) |
| Valkey | `taskiq` broker + scheduler | ✓ | `valkey:9.1.1-alpine` | — |
| Docker Compose v2 | testlar (`npm run test`), migratsiya | ✓ | compose profillari `test`/`migrate` mavjud | — |
| testcontainers | haqiqiy PG da tenancy testlari | ✓ | mavjud pin | — |
| Node ≥ 20.9 | frontend testlari va darvozalar | ✓ | `package.json:44` | — |
| **cv-service / ONNX / go2rtc / NVR** | **KERAK EMAS** | n/a | — | Bu faza kadr **olmaydi**, faqat mavjud `snapshot_id` ga havola qiladi |
| Telegram bot tokeni | **KERAK EMAS** (7-faza) | n/a | — | — |
| Yangi npm/PyPI paketi | **YO'Q** | n/a | — | — |

**Missing dependencies with no fallback:** yo'q.
**Missing dependencies with fallback:** yo'q.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), testcontainers 4.15.0 |
| Backend config | `services/core-api/pyproject.toml` + `tests/conftest.py` (mavjud) |
| Frontend framework | vitest (komponent, `.test.tsx`) + `node --test` (`frontend/scripts/*.test.mjs`, **matn darvozalari**) |
| Quick run (task darajasi) | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` — **byudjet 180 s**, joriy o'lchov 87 s (`package.json` `//gate-fast-budget`) |
| Wave merge | `npm run test` (backend to'liq) + `npm run test:tenancy` |
| Phase gate | `npm run gate` — **byudjet 1250 s**, joriy ~1009 s (`package.json` `//gate-budget`) |
| ⚠ Byudjet xavfi | 6-faza ~6 jadval + ~8 marshrut + ~10 komponent qo'shadi. `gate` byudjeti **241 s zaxira** bilan turadi. Reja har to'lqinda `gate` vaqtini **o'lchashi** va oshsa byudjetni **sabab bilan** qayta belgilashi shart (05-15 W0-13 naqshi) |

### Faza mezonlari → o'lchanadigan signal

> Fayl: `tests/integration/test_phase6_criteria.py` — `test_phase5_criteria.py` ning **shakli** (uchta mustaqil darvoza: mezon boshiga bitta test · meta-test · mock'siz o'lchov).

| # | ROADMAP mezoni | Test qatlami | Kerakli holat (fixture) | Kuzatiladigan signal |
|---|---|---|---|---|
| **SC#1** | Band rastaga to'liq kunlik patta; job qayta ishga tushsa ikkinchi hisob yo'q | integration (haqiqiy PG) | `billing_domain` seed: 3 rasta — (a) 2 slot AI-`occupied`, (b) 1 slot AI-`occupied`, (c) 1 slot `occupied` + `resolution_source='human'` | `billing_close(D)` → hisob **faqat** (a) va (c) da; `amount_soum == tariffs.amount_soum`. Keyin **qayta** `billing_close(D)` → qator soni **o'zgarmaydi**, `amount_soum` **va** `created_at` **ikkalasi ham** o'zgarmaydi (D-06) |
| **SC#2** | Har hisobdan dalilga o'tish mumkin; hisob o'zgarmas; tuzatish faqat `charge_adjustments` | integration | SC#1 ning (a) hisobi | `charge_evidence` da `occupancy_event_id` bor va u `occupancy_events.snapshot_id` orqali `GET /snapshots/{id}/image` ga yetadi. `UPDATE daily_charges SET amount_soum=1` → **`RaiseException`**; `DELETE` → **`RaiseException`** (faol bozor). `charge_adjustments` INSERT → o'tadi va `audit_log` da qator paydo bo'ladi |
| **SC#3** | Qarz faqat biriktirilgan sotuvchida; qoldiq hisoblanadigan; biriktirilmagan band rasta = anomaliya | integration | 2 rasta: biri biriktirilgan, biri `stall_assignments` bo'shlig'ida | Biriktirilgan → hisob + qoldiq; biriktirilmagan → `daily_charges` da **0 qator** VA `billing_anomalies(kind='unassigned_occupied')` da **1 qator**. `information_schema` da `daily_charges`/`vendors` da **`balance*` nomli ustun YO'Q** (to'plam tengligi bilan, D-31) |
| **SC#4** | Kassir/direktor kutilayotgan pattani jonli ko'radi; ≤3 bosishda tasdiqlaydi; summani faqat sabab-kod bilan o'zgartiradi | integration + vitest | `GET /billing/pending` seed; komponent testida `apiFetch` mock'i | **(a)** proyeksiya javobida `charge_id` **umuman yo'q** (kalitlar to'plami tengligi); summa `resolve_stall_day_money` bilan **bir xil** (ikki chaqiruv, bir natija — D-16); **(b)** vitest: sahifa ochilgandan to muvaffaqiyatli `POST /payments` gacha **interaktiv hodisalar SANALADI** va `<= 3` (D-18, `review-session.test.tsx:403-429` naqshi); **(c)** sabab-kodsiz summa o'zgartirish → **422** |
| **SC#5** | Takror bosish dublikat bermaydi; tuzatish faqat storno; ko'r deklaratsiya + variance | integration + vitest + darvoza | ochiq smena, 1 to'lov | **(a)** bir xil `idempotency_key` bilan 2 `POST` → `payments` da **1 qator**, ikkinchi javob **200** va **o'sha `id`**; **(b)** 3 tez bosish → `apiFetch` **1 marta** (D-22); **(c)** `UPDATE payments` → `RaiseException`; storno → **yangi qator** `kind='reversal'` + `reason_code` majburiy; **(d)** `POST /shifts/{id}/close` javobi kalitlari to'plamida `system_*` **yo'q** (to'plam tengligi); variance **serverda** hisoblangan va `declared > system` holatida ham qaytariladi (D-26) |

### Meta-darvozalar (mezonlardan mustaqil)

| ID | Da'vo | Mexanizm |
|----|-------|----------|
| **G-1** | Beshala mezon o'lchanadi va **birortasi jimgina tushib qolmaydi** | `test_every_criterion_has_its_own_test()` — `test_phase5_criteria.py:1118` naqshi (modul funksiyalarini introspeksiya qiladi) |
| **G-2** | `daily_charges.service_date` ↔ `stall_slot_occupancy.business_date` **semantik mos** | Har yozilgan hisob uchun o'sha `(market_id, stall_id, service_date)` da kamida bitta `stall_slot_occupancy` qatori bor. Bu **Pitfall 1** ni ushlaydi |
| **G-3** | `float` billing modullarida **yo'q** | `information_schema.columns` da yangi jadvallar uchun `data_type` to'plami ⊆ `{uuid, bigint, date, text, timestamp with time zone, boolean, smallint}` — **to'plam tengligi**, `not in` emas (D-31) |
| **G-4** | Moliyaviy jadval qo'riqchilari o'rnida | mavjud `test_financial_tables_have_guards` (`test_meta.py:1313`) — jadval tug'ilgan kuni **o'zi** ishga tushadi |
| **G-5** | Yangi marshrutlar tenant matritsasida | mavjud `test_route_coverage.py` + `MINIMUM_MATRIX_ROUTES` **ko'tariladi** (D-32) |
| **G-6** | D-04 predikati `human_confirmed` dan **ajraladi** | Uchta holat: (1) 2 AI-`occupied` → **hisob**; (2) 1 AI-`occupied` + boshqa slotda `('empty','human')` → **hisob YO'Q**; (3) 1 `('occupied','human')` → **hisob**. Sabotaj: predikatni `_PER_STALL_CTE.human_confirmed` ga almashtirish → **(2) qizarishi SHART** (C-6, 05-10 darsi) |
| **G-7** | Ko'r deklaratsiya serializatori | `ShiftCloseResponse` maydonlari **to'plam tengligi** bilan; `frontend/scripts/` darvozasi `components/collect/**` katalogini **hosila** ravishda skanerlaydi (D-32, G-12/G-18 naqshi) |
| **G-8** | RBAC ikki tilda mos | mavjud `frontend/scripts/role-gate.test.mjs` — `rbac.py` **va** `rbac.ts` ni matn sifatida o'qiydi |
| **G-9** | Yangi `AuditAction`/xato kodlari uchala tilda | mavjud `audit-actions.test.mjs`, `error-codes.test.mjs` + `i18n:check` |
| **G-10** | Orfan `SECURITY DEFINER` funksiyalar **hal qilindi** | `DEFINER_SURFACES` (`test_occupancy_domain_meta.py:75-79`) to'plami `0020` dan keyin **bo'sh** (yoki qolganlar sabab bilan) — ikki tomonlama qulf |
| **G-11** | Kaskad yangi jadvallarni qamraydi | mavjud `test_market_delete_guard.py::test_cascade_covers_every_table_referencing_markets` — `0020` dan keyin **o'zi qizaradi**, `0021` uni yashil qiladi |
| **G-12** | Idempotentlik parallel yozuvda ham ishlaydi | **Wave 0 zondi**: ikki `asyncio` sessiya bir xil kalit bilan; natija 1 qator + bir xil `id` (A1) |

### Sampling Rate

- **Per task commit:** `npm run gate:fast` (≤180 s)
- **Per wave merge:** `npm run test` + `npm run test:tenancy`
- **Phase gate:** `npm run gate` to'liq yashil (byudjet 1250 s) + `test_phase6_criteria.py` beshala mezoni

### Wave 0 Gaps

- [ ] `tests/fixtures/billing_domain.py` — 6 jadval seed'i (`fixtures/occupancy_domain.py` naqshi); ⚠ `stall_slot_occupancy` qatorlarini **`day_close` orqali** yozish (qo'lda `INSERT` emas) — aks holda C-3 sinfidagi xato testda **ko'rinmaydi**
- [ ] `tests/tenancy/test_idempotency_concurrency.py` — **Wave 0 zondi** (A1/G-12), haqiqiy PG, ikki parallel sessiya
- [ ] `tests/tenancy/test_generated_from_column_probe.py` — **Wave 0 zondi** (A2): `GENERATED ALWAYS AS (<plain column>) STORED` PG 18 da ruxsat etiladimi
- [ ] `tests/integration/test_phase6_criteria.py` — beshta mezon + meta-test + G-2/G-3/G-6
- [ ] `tests/tenancy/test_billing_domain_meta.py` — sxema konstraytlari (`test_occupancy_domain_meta.py` naqshi)
- [ ] `frontend/scripts/collect-surface.test.mjs` — G-7 (ko'r deklaratsiya + ommaviy amal yo'qligi), **katalogdan hosila**
- [ ] `frontend/src/components/collect/*.test.tsx` — bosish sanog'i (SC#4b), `useRef` qulfi (SC#5b)
- [ ] `packages/sbozor-core/tests` yo'q → sof funksiyalar `tests/unit/test_billable_from_slots.py`, `test_variance.py` (`test_aggregate_stall_slot.py` naqshi: **jadval testi**, bitta holat emas)
- [ ] Framework install: **kerak emas** — hamma narsa mavjud

---

## Security Domain

**`security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`** (`.planning/config.json`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control (mavjud) |
|---------------|---------|-----------------|
| V2 Authentication | ha (meros) | PyJWT access 15 min + refresh cookie; `CurrentPasswordDep` darvozasi (`deps.py:415`) — **yangi mexanizm qurilmaydi** |
| V3 Session Management | ha (meros) | `refresh_tokens` + `auth_refresh_*` `SECURITY DEFINER` yuzasi |
| V4 Access Control | **ha, ASOSIY** | `require_permission()` (`deps.py:456`) marshrut **dekoratorida** (imzoda emas — 403 audit yozuvidan oldin); RLS `ENABLE`+`FORCE` + tenant policy; kompozit FK. ⛔ `require_any_permission()` **yopiq to'plam** (C-9) |
| V5 Input Validation | ha | Pydantic `strictObject`-ekvivalenti server tomonda; zod `z.strictObject` mijozda (05-14 qoidasi); enum'dan hosila `CHECK` DB da |
| V6 Cryptography | yo'q (yangi sir yo'q) | Fernet faqat NVR sirlari uchun (3-faza) — bu faza tegmaydi |
| V7 Error handling / Logging | **ha** | `structlog` + `asgi-correlation-id`; xato **TURI** yoziladi, matni emas (`day_close.py:164-167`); `audit_log` append-only |
| V8 Data Protection | **ha** | Kassir yuzasida shaxsiy maydon **yo'q** (C-10); `PERSONAL_FIELDS` darvozasi; dalil-kadr baytlari alohida huquq ostida |
| V11 Business Logic | **ha, ASOSIY** | Idempotentlik kaliti, o'zgarmaslik triggerlari, ko'r deklaratsiya, `CHECK (amount_soum > 0)` |
| V13 API | ha | OpenAPI dan hosila darvozalar; `MINIMUM_MATRIX_ROUTES` |

### Known Threat Patterns for {FastAPI + PG RLS + pul yozuvi}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Takror to'lov (tarmoq retry / uch bosish) | Repudiation | `UNIQUE (market_id, idempotency_key)` + `useRef` latch (D-21/D-22) |
| Bir xil kalit, boshqa summa | Tampering | `request_fingerprint` mos kelmasa **409** (Pitfall 4) |
| Yozilgan hisobni jimgina tahrirlash | Tampering | `charge_immutable()` trigger; `UPDATE` **shartsiz** rad etiladi |
| To'lovni o'chirib "pul kelmagan" qilish | Repudiation | `payment_immutable()`; storno **yangi qator** + sabab-kod |
| Kassir tizim summasini ko'rib deklaratsiyani moslashtirishi | Tampering | Maydon **sxemada yo'q** + serializator darvozasi (D-25, G-7) |
| Cross-tenant to'lov/hisob | Information Disclosure | RLS `FORCE` + **kompozit FK** (`market_id, stall_id`) — sxema darajasida |
| Job orqali RLS chetlab o'tish yuzasini kengaytirish | Elevation of Privilege | Faqat `active_market_ids()` (D-15); yangi `SECURITY DEFINER` funksiya **qo'shilmaydi**; orfanlar DROP (C-11) |
| Kassirga shaxsiy ma'lumot oqishi | Information Disclosure | Javob modelida `vendor_name`/`phone` **yo'q**; `VENDOR_VIEW` berilmaydi (C-9/C-10) |
| Yopiq kunda hisob yozish (jimgina tushum) | Tampering | `market_is_open()` tenant konteksti ostida; yopiq kun → anomaliya (D-10, Pitfall 9) |
| Sabab-kod maydonini erkin matn qilib bo'shatish | Tampering | Enum'dan hosila `CHECK`; `other` **yo'q** (OQ-3) |
| Pul `float` bo'lib qolishi | Tampering | `money.py` boundary `TypeError` + `bigint` ustun + G-3 to'plam tengligi |
| Audit yozuviga sir tushishi | Information Disclosure | `fn_audit_row()` `to_jsonb(NEW)` yozadi — yangi jadvallarda **sir ustuni yo'q**, `idempotency_key` esa sir emas (mijoz UUID'i) |

---

## Project Constraints (from CLAUDE.md)

| Directive | Bu fazada nima degani |
|---|---|
| **Aynan 3 servis** (core-api, cv-service, bot-service) | Butun faza `core-api` ichida. Yangi servis/konteyner **yo'q** (worker/scheduler — mavjud `core-api` image'ining jarayonlari) |
| **Pul: `BIGINT` so'm ↔ Python `int`; `float`/`Decimal` TAQIQ** | Har ustun `bigint`; `money.assert_safe_soum()` chegarada; G-3 darvozasi |
| **`TIMESTAMPTZ` + `Asia/Tashkent`; naive datetime TAQIQ** | `created_at timestamptz`; `business_today()`; `ZoneInfo` — `date.today()` **ishlatilmaydi** |
| **Multi-tenant: har jadvalda `market_id` + RLS** | 6 yangi jadval, har birida `ENABLE`+`FORCE`+policy+kompozit FK |
| **PostgreSQL 18.4; PG 19 TAQIQ** | `ON CONFLICT DO SELECT` (PG 19) **ishlatilmaydi** |
| **SQLite testlarda TAQIQ** | Barcha sxema/RLS testlari testcontainers + haqiqiy `postgres:18.4` |
| **taskiq (arq EMAS); `redis[hiredis]==8.0.1`** | `billing_close_task` `worker.py` da; yangi navbat kutubxonasi yo'q |
| **Next.js 16: `middleware.ts` YO'Q, `proxy.ts`** | `frontend/src/proxy.ts` mavjud — yangi kassir marshrutlari locale routing'ga **o'zi** kiradi |
| **TypeScript 5.9.3 (7.x EMAS)** | Mavjud pin |
| **UI: Apple-uslub minimal, kassir oqimi ≤3 bosish, 3 til majburiy** | D-18 o'lchanadi; uchala locale fayli (uz-Cyrl **generatsiya**) |
| **Audit jurnali majburiy** | `AUDITED_TABLES` ga `daily_charges`?/`payments`?/`cashier_shifts`? — pastdagi tavsiya |
| **`frontend/AGENTS.md`: "This is NOT the Next.js you know"** | Next.js kodi yozishdan oldin `frontend/node_modules/next/dist/docs/` dagi tegishli qo'llanma **o'qilishi shart** |
| **GSD workflow enforcement** | Fayl o'zgarishlari faqat GSD buyruqlari orqali |

**Audit qamrovi bo'yicha tavsiya (`AUDITED_TABLES`):**
| Jadval | Auditda? | Sabab |
|---|---|---|
| `daily_charges` | **YO'Q** | Shartsiz o'zgarmas → audit faqat `INSERT` ni ko'rardi = **ikkinchi nusxa** (`occupancy_events` bilan aynan bir xil dalil, `models/occupancy.py:13-18`). Hajm ham katta (1000/kun/bozor) |
| `charge_adjustments` | **HA** | **Insonning moliyaviy oqibatli qarori** — `tariffs`/`zone_reviews` bilan bir oilada; hajmi kichik |
| `payments` | **YO'Q** | Append-only + o'zgarmas; hajm katta; iz `payments` ning O'ZIDA (`kind`, `reverses_payment_id`, `reason_code`, aktor ustuni) |
| `cashier_shifts` | **HA** | Deklaratsiya — insonning qarori va variance ning asosi; hajmi juda kichik (kuniga bir necha qator) |
| `billing_anomalies` | **YO'Q** | Hodisa jurnali, faqat qo'shiladi |
| `charge_evidence` | **YO'Q** | `daily_charges` ning muzlatilgan nusxasi |

⚠ Har "YO'Q" uchun sabab `AUDITED_TABLES` docstringida **yozilishi shart** — reyestrning butun mexanizmi shunda (`schema_contract.py:220-252` uslubi).

---

## Sources

### Primary (HIGH — kodni o'zim o'qidim, `path:line`)

- `packages/sbozor-core/sbozor_core/schema_contract.py:69-126` — `FINANCIAL_TABLES` (**`daily_charges`**) va uning kutilmalari
- `packages/sbozor-core/sbozor_core/schema_contract.py:128-252` — `AUDITED_TABLES` va istisnolar mantig'i
- `migrations/helpers.py:269-309` — `attach_immutability_trigger()` (`BEFORE UPDATE OR DELETE`, funksiya/nom parametr, trigger tartibi)
- `migrations/helpers.py:316-419` — `BUSINESS_DATE_EXPR`, `financial_guard_statements()`, `financial_guards()` va per-market timezone cheklovi
- `migrations/versions/0008_temporal.py:164-226` — **`tariffs` da `financial_guards()` CHAQIRILMAGANI** va uchala qo'riqchi qo'lda (C-2 presedenti)
- `migrations/entities/triggers.py:440-566` — `OCCUPANCY_EVENT_IMMUTABLE` / `ZONE_REVIEW_IMMUTABLE` (D-07 uchun shablon)
- `migrations/entities/functions.py:1345-1390` — `market_is_open()` (INVOKER, fail-closed, uch qavatli COALESCE)
- `migrations/entities/functions.py:1650-1793` — `audit_draw_due_markets()`, `occupancy_day_close_markets()`, grant reyestrlari (C-11)
- `migrations/entities/__init__.py:262-384` — `SNAPSHOT_*`/`OCCUPANCY_*` reyestrlari va DELETE tartibi
- `migrations/versions/0019_market_delete_occupancy.py:1-64` — kaskad kengaytirish naqshi; `down_revision = "0018"` (head = **0019**)
- `packages/sbozor-core/sbozor_core/models/occupancy.py:931-1029` — `StallSlotOccupancy` **to'liq sxemasi**; `UNIQUE (market_id, id)` **YO'Q** (C-7)
- `packages/sbozor-core/sbozor_core/models/occupancy.py:185-203, 317-344` — `SLOT_VERDICT_VALUES`, `occupied_has_winning_event`, `no_coverage_is_paired`
- `packages/sbozor-core/sbozor_core/models/market.py:428-547` — `StallCategoryPeriod`, `Tariff` (`valid_to` YO'Q, `business_date` Computed)
- `packages/sbozor-core/sbozor_core/models/market.py:579-643` — `StallAssignment` (`ExcludeConstraint`, `lower_bound_required`)
- `packages/sbozor-core/sbozor_core/models/market.py:154-183` — `STALL_CODE_SORT_EXPR` (kassir qidiruvi tartibi)
- `packages/sbozor-core/sbozor_core/periods.py:1-105` — `[)` konventsiyasi, **D-10 almashinuv kontrakti** (OQ-5)
- `packages/sbozor-core/sbozor_core/money.py:1-111` — `Soum`, `assert_safe_soum()` (manfiy rad), `format_soum()` (C-5)
- `packages/sbozor-core/sbozor_core/timeutil.py:1-90` — `business_today()`, qamrov ogohlantirishi
- `packages/sbozor-core/sbozor_core/occupancy.py:100-273` — `effective_verdict()`, `aggregate_stall_slot()`, manba kuchi tartibi (C-6 asosi)
- `packages/sbozor-core/sbozor_core/enums.py:38-487` — `Role`, `ResolutionSource`, `AuditAction`, `ActorKind`
- `services/core-api/app/jobs/day_close.py:1-354` — argumentli job shabloni; `occupancy_day_close_markets()` **rad etilishi** (C-3/C-11)
- `services/core-api/app/jobs/retention.py:138-170` — `active_market_ids()` (D-15)
- `services/core-api/app/worker.py:356-440` — cron konstantalari (`DAY_CLOSE_CRON = "40 3 * * *"`, `QUEUE_TICK_CRON`) — C-3 ning dalili
- `services/core-api/app/worker.py:834-878` — `daily_queue_tick_task`, `day_close_task` (`business_today() - 1` qobiqda)
- `services/core-api/app/repositories/occupancy_repo.py:319-448` — `_MATERIALIZE_SLOT` (**DO UPDATE**, C-7), `_PER_STALL_CTE` (**`human_confirmed`**, C-6), `_DAY_SUMMARY`
- `services/core-api/app/repositories/stall_repo.py:595-640` — **tarixiy tarif/toifa/biriktirish yechimi** (D-09)
- `services/core-api/app/repositories/review_repo.py:189-200` — `sa.period @> ev.business_date` naqshi
- `services/core-api/app/repositories/nvr_repo.py:507-517` — "poyga DB ga topshiriladi"
- `services/core-api/app/security/rbac.py:49-245` — `Permission`, `ROLE_PERMISSIONS`, **kassirda faqat `payment_create`** (C-9)
- `services/core-api/app/security/audit.py:253-315, 410-450` — `write_app_audit()`, `audit_read()`
- `services/core-api/app/deps.py:456-554` — `require_permission()`, `require_any_permission()` va introspeksiya teglari
- `services/core-api/app/api/v1/snapshots.py:176, 236, 476-479` — dalil-kadr marshruti va uning huquqlari
- `tests/tenancy/test_meta.py:40-292` — `INDEX_EXCEPTIONS`, `EXPECTED_DEFINER_FUNCTIONS`, `PENDING_AUDIT_TRIGGERS`, `POLICY_TENANT_GUC_EXCEPTIONS`
- `tests/tenancy/test_meta.py:1313-1362` — **`test_financial_tables_have_guards`** (C-2/C-5 ning dalili)
- `tests/tenancy/test_personal_data_coverage.py:59-103, 488-508, 674-787` — `PERSONAL_FIELDS`, evidence-frame yopiq to'plami, `VENDOR_VIEW` juftligi (C-9/C-10)
- `tests/tenancy/test_occupancy_domain_meta.py:67-96, 534-593` — `DEFINER_SURFACES`, `FORBIDDEN_SURFACE_TOKENS`, yuza tekshiruvi
- `tests/tenancy/test_route_coverage.py:1-80, 202` — `MINIMUM_MATRIX_ROUTES = 60` va o'sish tarixi
- `tests/integration/test_business_date.py:134-145` — **`business_date` ga yozish RAD ETILADI** (C-2)
- `tests/integration/test_idempotency.py:1-50` + `tests/fixtures/financial.py:82-113` — probe jadvali va `ON CONFLICT DO NOTHING` kontrakti
- `tests/integration/test_occupancy_billing_fence.py:1-60` — billing langari (uchta inkor + nazorat holati)
- `tests/integration/test_phase5_criteria.py:1-70, 1118-1262` — faza darvozasining **uch mustaqil qatlami**
- `frontend/src/components/review/decision-bar.tsx:1-166` — `event.repeat`, `aria-disabled`, ommaviy amal yo'qligi
- `frontend/src/components/review/review-session.test.tsx:380-429` — **bosish/so'rov SANOG'I** testlari (D-18/D-22 naqshi)
- `frontend/src/components/blind-audit/blind-session.tsx:85-130` — `useRef` latch
- `frontend/src/lib/rbac.ts:95-155` + `frontend/scripts/role-gate.test.mjs:1-56` — ikki tildagi RBAC ko'zgusi (C-9)
- `frontend/scripts/check-messages.mjs:1-45`, `gen-cyrillic.mjs:1-30`, `audit-actions.test.mjs:1-30`, `error-codes.test.mjs:1-28` — i18n va parity darvozalari (C-13)
- `package.json:23-31` — `gate` (1250 s) va `gate:fast` (180 s) byudjetlari
- `.planning/phases/02-bozor-domeni-va-yangi-bozor-ustasi/02-UI-SPEC.md:503-513` — **≤2 o'zaro ta'sir kontrakti** (OQ-2)
- `.planning/phases/05-.../05-PATTERNS.md:175-240` — §S-1 yangi tenant jadvali oltita joyi
- `.planning/STATE.md:98-104` — orfan `SECURITY DEFINER` funksiyalar qarori 6-fazada

### Secondary (MEDIUM — tekshirilgan, lekin bevosita o'lchanmagan)

- [PostgreSQL 18 `INSERT`](https://www.postgresql.org/docs/18/sql-insert.html) — *"Only rows that were successfully inserted or updated will be returned"*. ⚠ Konkurentlik/izolyatsiya xulqi bu sahifada **yozilmagan** → A1 zondi
- [Haki Benita — PostgreSQL Get-or-Create](https://hakibenita.com/postgresql-get-or-create) — CTE + `UNION ALL` va uning **snapshot muammosi**; "ikki bayonot ishonchliroq" xulosasi
- [Stripe — Idempotent requests](https://docs.stripe.com/api/idempotent_requests) — kalit ↔ saqlangan javob; parametrlar mos kelmasa **xato** (Pitfall 4)
- [brandur.org — Implementing Stripe-like Idempotency Keys in Postgres](https://brandur.org/idempotency-keys) — kalit va effekt **bitta tranzaksiyada**
- [Modern Treasury — Enforcing Immutability in your Double-Entry Ledger](https://www.moderntreasury.com/journal/enforcing-immutability-in-your-double-entry-ledger) — reversal = kompensatsiya qatori, balans **hosila**
- [Faysal Ahmed — Double-Entry Accounting in a Relational Database](https://faysalahmed.space/blog/double-entry-accounting-db-model-2026.md/) — *side column, not signed amounts* (C-5)
- [Microsoft Learn — Storno accounting](https://learn.microsoft.com/en-us/dynamics365/finance/localizations/europe/emea-storno) — storno vs reverse farqi
- [Microsoft Learn — Cash management (Dynamics 365 Commerce)](https://learn.microsoft.com/en-us/dynamics365/commerce/cash-mgmt) — **blind close**: naqd seyfga tushiriladi, tender **deklaratsiya qilinadi**, smena ko'r yopiladi
- [NRS — Shift Reconciliation from the Back Office](https://nrsplus.com/blog/shift-reconciliation-from-the-back-office/) — *blind count prevents "fudging"*; variance = ochilish + sotuv − chiqimlar vs sanoq; chegara oshsa tekshiruv
- [MangoApps — Cash Drawer Close & Reconcile](https://www.mangoapps.com/templates/sop/cash-drawer-close-reconcile) — smena maydonlari ro'yxati (starting float, cash sales, refunds, paid-outs, expected closing)
- [Neon — PostgreSQL 19 `ON CONFLICT DO SELECT`](https://neon.com/postgresql/postgresql-19/on-conflict-do-select) — kelajakdagi atomik get-or-create (bu fazada **ishlatilmaydi**)

### Tertiary (LOW — rejada shunday belgilansin)

- `.planning/research/ARCHITECTURE.md:286-376` — ikki fazali billing niyati **to'g'ri**, lekin sxema detallari **eskirgan** (`stall_day_occupancy`, `tariffs.valid_to`, `daily_amount_soum`, `billing_runs`, advisory lock). Namuna sifatida **ko'chirilmaydi**
- `.planning/phases/01-.../01-RESEARCH.md:1196-1219` — `daily_charges` DDL'i; C-2 ning manbasi, bugun **noto'g'ri**
- OQ-3/OQ-4/OQ-6/OQ-7 — buyurtmachi javoblari **yo'q** (`STATE.md:265`); tavsiyalar `[ASSUMED]`

---

## Metadata

**Confidence breakdown:**
- Mavjud sxema, darvozalar, reyestrlar: **HIGH** — har da'vo `path:line` bilan o'qildi
- Contradictions (C-1…C-13): **HIGH** — har biri kodda ko'rsatilgan konstrayt/test/cron qiymatiga tayanadi
- Tavsiya etilgan sxema (6 jadval, ustunlar): **MEDIUM** — presedentlardan hosila, lekin haqiqiy migratsiyada o'lchanmagan
- Idempotentlik konkurentligi (A1): **MEDIUM** — rasmiy hujjat bu oynani yozmaydi; Wave 0 zondi kerak
- `GENERATED ALWAYS AS (<column>)` (A2): **LOW** — o'lchanmagan; faqat ikkinchi variant uchun kerak
- Buyurtmachi qarorlari (OQ-3/4/6/7): **LOW** — `[ASSUMED]`, tasdiq kerak
- Kassir UI o'lchovi (D-18): **HIGH** — o'lchov naqshi mavjud testda ishlaydi (`review-session.test.tsx`)

**Research date:** 2026-08-10
**Valid until:** ~2026-09-10 (30 kun) — LEKIN har `stall_slot_occupancy`, `worker.py` cron, `rbac.py`/`rbac.ts`, yoki `tests/tenancy/test_meta.py` o'zgarishida **qayta o'qilishi** shart: bu fayldagi contradictions aynan o'sha to'rt joyga tayanadi.

---
*Phase: 06-billing-va-kassir*
