# Phase 6: Billing va kassir — Context

**Gathered:** 2026-08-10
**Status:** Ready for planning
**Source:** ROADMAP Phase 6 + BILL-01…05 / CASH-01…04 + 2-fazaning tarif/biriktirish domeni + 5-fazaning `stall_slot_occupancy` tikuvi va o'lchangan naqshlari
**Mode:** `--auto` — foydalanuvchining doimiy ko'rsatmasi bo'yicha savol berilmadi; har gray area'da tavsiya tanlandi va sabab yozildi

<domain>
## Phase Boundary

**Bu fazada:** kun yopilishida band rastadan **o'zgarmas kunlik patta** (`charges`) hisoblash; hisobni **dalil kadriga** strukturaviy bog'lash; tuzatishni faqat `charge_adjustments` orqali qilish; qarzni **hisoblanadigan ko'rinish** sifatida berish (saqlangan balans YO'Q); "kutilayotgan patta" jonli proyeksiyasi; kassirning ≤3 bosishli to'lov oqimi; idempotent to'lov va **storno + qayta kiritish**; smena ochish/yopish va **ko'r naqd deklaratsiyasi** bilan variance.

**Bu fazada EMAS:** nomuvofiqlik case oqimi va botlar (7-faza — `BILL-04` bu yerda **yozuv** yaratadi, oqim esa u yerda); Telegram push-kvitansiya (`CASH-05` → 7-faza); Excel eksport va direktor hisobotlari (8-faza); jonli undirish ro'yxati, kassir↔zona biriktirish, QR/bank o'tkazma, qonuniy fiskal kvitansiya, offline-lite (`V2-CASH-01…05`).

</domain>

<decisions>
## Implementation Decisions

### Fazaning tub farqi (rejalashtirishga ta'sir qiladi)

- **D-01**: **Bu faza 5-fazaning teskarisi.** 5-fazada haqiqat yo'q edi va yetkazib berish mahsuloti o'lchov mexanizmi bo'lgan. Bu yerda haqiqat **to'liq mavjud** — pul miqdori aniq, tarif jadvalda, bandlik `stall_slot_occupancy` da materializatsiya qilingan. Ya'ni **har bir mezon bugun mexanik isbotlanadi** va "hozir o'lchab bo'lmaydi" degan bandning bu fazada o'rni yo'q. Agar reja shunday band tug'dirsa — bu dizayn xatosi, tabiiy chegara emas.
- **D-02**: **Nizo modeli — sotuvchi bilan.** Oldingi fazalarda xato "noto'g'ri raqam" edi; bu yerda xato **odam pul to'laganini isbotlay olmasligi**. Shuning uchun har qaror "nizo paytida qaysi yozuv dalil bo'ladi?" savoliga javob berishi kerak. `float` taqig'i, `TIMESTAMPTZ` va o'zgarmaslik triggerlarining sababi aynan shu.

### Hisob (BILL-01, BILL-02)

- **D-03**: Manba — **`stall_slot_occupancy`**, `occupancy_events` EMAS. Agregatsiya 5-fazada tugagan; ikkinchi marta agregatsiya qilish **ikkinchi haqiqat manbai** yaratardi va ikkalasi bir kun ajralib ketardi. Hisob faqat materializatsiya qilingan qatorlarni o'qiydi.
- **D-04**: Hisob sharti ROADMAP dagidek: **≥2 slotda `occupied`**, **yoki** 1 slot `occupied` + o'sha slotda nazoratchi tasdig'i (`resolution_source` inson qarorini ko'rsatadi). Bitta tasdiqlanmagan AI sloti hisob bermaydi — noaniqlik sotuvchi foydasiga hal qilinadi.
- **D-05**: **`no_coverage` slotlari sanoqqa KIRMAYDI** — na `occupied`, na `empty`. Barcha slotlari `no_coverage` bo'lgan rasta uchun hisob yozilmaydi va u **BILL-04 anomaliyasi ham emas**: "ko'ra olmadik" ≠ "band, lekin biriktirilmagan". Ikkisini bir joyga qo'shish **ko'r nuqtadan tushum da'vosi to'qish** bo'lardi. Alohida "qamrovsiz rasta" yozuvi chiqadi (0-fazadagi ~10% qamrovsizlik shu yerda ko'rinadi).
- **D-06**: **Idempotentlik `UNIQUE (market_id, stall_id, business_date)`** bilan strukturaviy (BILL-01 shuni yozadi). Job `ON CONFLICT DO NOTHING` — **`DO UPDATE` EMAS**: yozilgan hisob o'zgarmas (D-07), ya'ni qayta yugurish uni yangilay olmaydi. Bu 05-12 dagi "qayta yugurish idempotentmi?" testining zaifligini takrorlamaslik uchun **holat bilan** o'lchanadi: qayta yugurishdan keyin summa **ham**, `created_at` **ham** o'zgarmagan bo'lishi kerak.
- **D-07**: `charges` **o'zgarmas** — shartsiz `BEFORE UPDATE OR DELETE` trigger, `zone_reviews` (05-05) dagi aynan bir xil mexanizm. Tuzatish faqat `charge_adjustments` (sabab-kod + aktor + audit). Balans = hisoblar − to'lovlar + tuzatishlar, **hech qachon saqlangan ustun** (BILL-03).
- **D-08**: **Dalil hisobga NUSXA bilan bog'lanadi, so'rov bilan emas.** Hisobni asoslagan slot qatorlari (`stall_slot_occupancy.id` va ularning `winning_occupancy_event_id` lari) hisob yozuvi bilan birga **saqlanadi**. Keyin qayta hisoblangan so'rov boshqa javob bersa ham, nizo paytida ko'rsatiladigan kadr **o'zgarmaydi**. Bu 5-fazaning `audit_rounds.frame_size` "muzlatilgan doira" qarorining aynan o'zi.
- **D-09**: Tarif `business_date` ga ko'ra 2-fazaning **tarixiy** `stall_category_periods` + `tariffs` orqali yechiladi. Hisob **`tariff_id` ni ham, summani ham** saqlaydi: keyin tarif tahrirlansa yozilgan hisob **retroaktiv o'zgarmasligi** shart. Bitta `tariff_id` yetarli emas — u kelajakdagi tahrirga ochiq.
- **D-10**: **Yopiq kunda hisob yo'q.** `open_weekdays` + `market_calendar_exceptions` (2-faza) bo'yicha yopiq kunda bandlik ko'rinsa — hisob yozilmaydi, **anomaliya** yoziladi. Yopiq kunda savdo bo'lishi real hodisa va uni jimgina pulga aylantirish ham, jimgina yo'qotish ham noto'g'ri.
- **D-11**: Pul — **`BIGINT` so'm ↔ Python `int`**. `float`/`Decimal` ustuni YO'Q. Lint darvozasi billing modullarida `float` ni taqiqlaydi (5-fazada `float8` kvotasi aynan shu sinfdagi xato bergan edi).

### Kun yopilishi (tetik va tartib)

- **D-12**: **`billing_close(business_date)` — argumentli job**, `now()` dan kun olmaydi. 4-fazaning `retention_daily(today=...)` va 5-fazaning `audit_draw` qoidasi; 05-11 aynan shu sababdan `audit_draw_due_markets()` ni ishlatmagan.
- **D-13**: Cron **20:30 Asia/Tashkent** — 5-fazaning `review.queue_tick` (19:30) dan keyin. Lekin **tartib kafolati cron jadvaliga tayanmaydi**: `billing_close` bandlikka faqat **o'qish** uchun tegadi va **idempotent**, ya'ni noto'g'ri tartibda yugursa ham qayta yugurish tuzatadi. 05-11 ning darsi: kafolat cron SATRLARIGA ko'chib ketmasligi kerak.
- **D-14**: **Tasdiqlanmagan noaniq slotlar kunni BLOKLAMAYDI** (mahsulot qoidasi #5 — hech narsa jarayonni to'xtatmaydi). Ular D-04 bo'yicha baribir hisob bermaydi, ya'ni kutish foyda bermaydi. Hisobot esa nechta rasta **nazoratchisiz** hal qilinganini ko'rsatadi — bu yashiriladigan emas, o'lchanadigan miqdor.
- **D-15**: Bozorlar ro'yxati **`active_market_ids()`** dan — `alert_sweep`/`retention_daily`/`audit_draw` ishlatadigan **yagona** RLS-chetlab o'tuvchi yuza. Yangi xavfsizlik yuzasi ochilmaydi (05-11 deviatsiya #4).

### Kutilayotgan patta (BILL-05)

- **D-16**: Proyeksiya **jadval emas, so'rov**. Va muhimi: **kun yopilishi bilan BITTA kod yo'lidan yuradi**, faqat parametri boshqa (`as_of=hozir` / `as_of=kun oxiri`). Ikki alohida implementatsiya kassir yig'gan summa bilan kechqurun yozilgan hisobni **ajratib yuborardi** — bu loyihada takroran topilgan "ikki haqiqat manbai" sinfi. Bitta funksiya, ikki chaqiruvchi; farq **testda** o'lchanadi.
- **D-17**: Proyeksiya "kutilayotgan" ekani **payloadda ochiq** — u hisob emas. Ekran uni yozilgan hisobdan vizual ajratadi; `charge_id` maydoni proyeksiyada **umuman yo'q** (yashirilgan emas — 5-fazaning D-17.2 naqshi).

### Kassir (CASH-01, CASH-02)

- **D-18**: **≤3 bosish aniq ta'rifi:** (1) rasta raqamini kiritish/tanlash, (2) to'lov turi (naqd/terminal), (3) tasdiqlash. **Summa bosish emas** — u tarifdan avtomatik keladi. Raqam terishdagi bosqichlar bitta qadam sifatida sanaladi. Bu **o'lchanadi**: test interaktiv hodisalarni sanaydi (05-13 dagi `decision-bar` testlari naqshi), "3 ta tugma bor" degan strukturaviy tekshiruv emas.
- **D-19**: Summani o'zgartirish **yopiq sabab-kod ro'yxati** bilan (erkin matn emas — erkin matn hisobotda guruhlanmaydi va amalda bo'sh qoladi). Har o'zgartirish auditda aktor va eski/yangi summa bilan.
- **D-20**: Kassir ekrani **tarif summasini o'zi hisoblamaydi** — server bergan summani ko'rsatadi. Mijozda qayta hisoblash 05-14 rad etgan naqsh: u jimgina **boshqa savolga** javob berardi.

### To'lov va storno (CASH-03)

- **D-21**: **Idempotentlik kaliti mijozda** tug'iladi (to'lov varag'i ochilganda UUID) va `UNIQUE (market_id, idempotency_key)` bilan qulflanadi. Takror so'rov **o'sha to'lovni 200 bilan qaytaradi**, 409 emas: tarmoq uzilishida qayta yuborish kassir uchun **ko'rinmas** bo'lishi kerak.
- **D-22**: **Ikki qatlam majburiy** — server kaliti **va** mijozdagi `useRef` qulfi. 05-13 o'lchagan: uch tez bosish uchta so'rov yuborardi, chunki `isPending` faqat keyingi renderda o'zgaradi. Server kafolati yolg'iz UI ni to'xtatmagan.
- **D-23**: `payments` **append-only**: `kind ∈ {payment, reversal}`, `reverses_payment_id`, o'zgarmaslik triggeri. Storno **sabab-kod** talab qiladi va **o'z qatori** bo'ladi. O'chirish/tahrirlash YO'Q. Qoldiq — belgili summalar yig'indisi.
- **D-24**: To'lov **hisobga bog'lanadi** (`charge_id`), rastaga emas. Aks holda "qaysi kunning pattasi to'landi?" savoliga javob yo'qoladi va eski qarz bilan bugungi patta aralashadi.

### Smena va ko'r deklaratsiya (CASH-04)

- **D-25**: **Ko'r deklaratsiya 5-fazaning ko'r audit naqshining AYNAN qayta ishlatilishi.** Smena yopish payloadida tizim summasi **e'lon qilinmagan** (yashirilgan emas), deklaratsiya yozilgach **o'zgarmas**, variance **serverda** hisoblanadi. `blind-audit` uchun yozilgan G-12 sinfidagi darvoza smena-yopish katalogini ham skanerlaydi.
- **D-26**: Variance **ikki tomonlama ko'rsatiladi** (kam ham, ortiq ham) va **hech qachon avtomatik "to'g'rilanmaydi"**. Ortiqcha naqd ham signal — uni jimgina yutish kamomadni yashirish bilan bir xil xato.
- **D-27**: Smena **kassirga bog'langan** va bir vaqtda bitta ochiq smena — qisman `UNIQUE` indeks bilan strukturaviy (5-fazadagi `uq_alert_events_..._open` naqshi).

### Anomaliya (BILL-04)

- **D-28**: Biriktirilmagan band rasta uchun **hisob YOZILMAYDI** va `vendor_id NULL` bilan hisob ham yozilmaydi — "kimdir qarzdor, lekin kim ekani noma'lum" yozuvi qarz hisobotini buzardi. Alohida anomaliya qatori yoziladi; **case oqimi 7-fazaniki**.
- **D-29**: Anomaliya yozuvi ham **dalil kadriga** bog'lanadi (D-08 bilan bir xil nusxa qoidasi) — 7-faza uni qayta topishga majbur bo'lmasin.

### Tekshiruv intizomi (5-fazadan meros, majburiy)

- **D-30**: Har reja sabotaj o'tkazadi va **nima qizarganini ham, nima YASHIL qolganini ham** yozadi. Yashil natijadan xulosa chiqarishdan oldin ikki savol: **sabotaj o'lchanayotgan tizimga yetib bordimi** (05-11: trigger boshqa bazada o'chirilgan edi) va **umuman biror test bu ikki holatni ajrata oladimi** (05-10: `WHERE` sharti ikki ifodani teng qilgan edi).
- **D-31**: Inkor tasdiq (`not.toContain("...")`) **ishlatilmaydi** — u faqat aynan o'sha nomni ushlaydi. O'rniga **to'plam tengligi** (05-14 sabotaj S7 buni o'lchagan).
- **D-32**: Darvoza qamrovi **hosila bo'ladi**, qo'lda sanalmaydi (05-16 W-2/W-3). Yangi marshrut yoki yangi komponent katalogi darvozaga **o'zi** kirishi kerak.
</decisions>

<canonical_refs>
## Canonical References

| Ref | Path | Nega kerak |
|---|---|---|
| Loyiha ta'rifi | `.planning/PROJECT.md` | Core value, cheklovlar, muddat |
| Talablar | `.planning/REQUIREMENTS.md` | BILL-01…05, CASH-01…04; lug'at `Done`/`Pending`/`Blocked` |
| Yo'l xaritasi | `.planning/ROADMAP.md` | Faza 6 maqsadi va beshta mezoni; self-service mahsulot qoidasi |
| Stek va taqiqlar | `./CLAUDE.md` | `float` taqig'i, `BIGINT` so'm, `TIMESTAMPTZ`, taskiq, RLS |
| Bandlik tikuvi | `packages/sbozor-core/sbozor_core/models/occupancy.py` | `stall_slot_occupancy` — manba jadval, `winning_occupancy_event_id` dalil havolasi |
| Tarif/biriktirish domeni | `packages/sbozor-core/sbozor_core/models/market.py` | `tariffs`, `stall_category_periods`, `stall_assignments`, `market_calendar_exceptions` |
| O'zgarmaslik naqshi | `.planning/phases/05-.../05-05-SUMMARY.md` | Shartsiz `BEFORE UPDATE` triggeri va kompozit FK langari |
| Ko'r naqsh | `.planning/phases/05-.../05-11-SUMMARY.md` | Ko'r payload, o'zgarmas javob, muzlatilgan doira |
| Mijoz qulfi | `.planning/phases/05-.../05-13-SUMMARY.md` | `useRef` latch — server kafolati yolg'iz yetmagani o'lchangan |
| Hisobot intizomi | `.planning/phases/05-.../05-14-SUMMARY.md` | Maxrajlar, inkor tasdiqning zaifligi, `strictObject` |
| Darvoza hosilaligi | `.planning/phases/05-.../05-VERIFICATION.md` + `05-16` commitlari | W-1/W-2/W-3 va ularning yopilishi |
| Job naqshlari | `services/core-api/app/jobs/retention.py`, `alerting.py`, `audit_draw.py` | `active_market_ids()`, argumentli kun, cron ro'yxatga olish |

</canonical_refs>

<code_context>
## Reusable Assets (scouted)

**To'g'ridan-to'g'ri qayta ishlatiladi:**
- `stall_slot_occupancy` — kunlik bandlik, slot kesimida, dalil havolasi bilan (5-faza)
- `tariffs` + `stall_category_periods` — tarixiy tarif yechimi (2-faza)
- `stall_assignments` — sotuvchi↔rasta, davr bilan (2-faza)
- `market_calendar_exceptions` + `open_weekdays` — ish kunlari (2-faza)
- `audit_log` + RLS + `market_id` — hamma jadvalda (1-faza)
- `active_market_ids()` — jobning yagona RLS-chetlab o'tuvchi yuzasi (4-faza)
- Taskiq cron ro'yxatga olish shakli va `MARKET_CRON_OFFSET` (4/5-faza)
- O'zgarmaslik triggeri generatori — `0018` dagi `attach_immutability_trigger`
- `require_any_permission()` — `deps.py` (05-15), agar kassir/direktor yuzalari kesishsa
- Frontend: `DecisionBar` qulf naqshi, `z.strictObject` sxema qoidasi, i18n uch lokal

**Yangi quriladi:** `charges`, `charge_adjustments`, `payments`, `shifts`, anomaliya jadvali; `billing_close` job; kassir PWA oqimi; smena yopish ekrani.
</code_context>

<deferred>
## Deferred Ideas

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
</deferred>

<open_questions>
## Research uchun ochiq savollar

Bular **qaror emas** — 06-RESEARCH.md javob berishi kerak:

1. **OQ-1**: Kassir qurilmasi PWA'mi yoki mavjud Next.js ilovasining mobil marshrutimi? ≤3 bosish o'lchovi va offline xulqi shunga bog'liq (offline-lite v2 da, lekin **tarmoq uzilishida nima ko'rinishi** bu fazada hal bo'ladi).
2. **OQ-2**: Rasta raqamini topish — to'liq ro'yxatdan qidiruvmi yoki raqamli klaviaturami? 300–1000 rasta miqyosida qaysi biri kamroq bosish beradi (o'lchash kerak, taxmin qilmaslik).
3. **OQ-3**: Sabab-kodlar ro'yxati (summa o'zgarishi va storno uchun) — buyurtmachi bilan kelishilganmi? Yopiq ro'yxat kerak; boshlang'ich to'plam qayerdan olinadi.
4. **OQ-4**: Qisman to'lov ruxsat etiladimi? BILL-03 qoldiqni hisoblanadigan qiladi, ya'ni qisman to'lov **texnik jihatdan** mumkin — lekin mahsulot qarori kerak.
5. **OQ-5**: Bir kunda bitta rastaga ikki sotuvchi biriktirilgan bo'lsa (almashinuv) — patta kimga yoziladi? 2-fazadagi `stall_assignments` davr modeli buni qanday hal qiladi.
6. **OQ-6**: Smena kassirga bog'langan bo'lsa, smenasiz kiritilgan to'lov mumkinmi (direktor tomonidan)? Agar yo'q bo'lsa, direktor to'lovi qanday yoziladi.
7. **OQ-7**: Variance chegarasi bormi (masalan >X so'm bo'lsa alert)? 4-fazaning alert mexanizmi tayyor.
</open_questions>

---
*Phase: 06-billing-va-kassir*
