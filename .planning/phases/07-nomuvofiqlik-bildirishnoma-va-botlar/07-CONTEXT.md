# Phase 7: Nomuvofiqlik, bildirishnoma va botlar - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

> ⚙ **`--auto` rejimida yig'ildi.** Foydalanuvchining doimiy ko'rsatmasi
> (`no-questions-autonomous-mode`, 2026-08-01): savol berilmaydi, **tavsiya
> etilgan variant** tanlanadi va zanjir davom etadi. Har kulrang soha uchun
> tanlangan variant va **sababi** quyida ochiq yozilgan — ular qaror sifatida
> qulflanadi, taxmin sifatida emas.

<domain>
## Phase Boundary

Bu faza **raqamni jarayonga** aylantiradi va **har rolga o'z xabarini** yetkazadi.

6-faza «band, lekin to'lovsiz» ni **hisoblab qo'ydi** (`billing_anomalies`,
`daily_charges`, `payments`, dalil zanjiri). 7-faza o'sha raqamning ustiga
**ish oqimini** quradi: har nomuvofiqlik **case** bo'lib yuritiladi, direktor
va sotuvchi **o'z vaqtida xabar** oladi, va sotuvchi birinchi marta tizimga
**o'zi kira oladi** (Telegram bot).

**Qamrovda:** RECON-01 (kunlik nomuvofiqlik hisoboti), RECON-02 (case
yuritish + hit-rate), RECON-03 (direktor dayjesti va kechki xabar), RECON-06
(rol bo'yicha bitta bosh ko'rsatkich), CASH-05 (zudlik push-kvitansiya),
BOT-01 (contact orqali ulanish), BOT-02 (qoldiq/qarz va to'lov tarixi),
BOT-03 (kechikkan qarz eslatmasi), BOT-04 (outbox + throttling + yetkazilganlik).

**⛔ Qamrovdan TASHQARIDA** (8-faza yoki keyingi milestone):
Excel eksport, AI aniqlik hisoboti, backup mashqi, go-live (8-faza);
direktor botining **buyruq** yuzasi (faqat **oluvchi** — RECON-03 shuni
yozadi); kassir botining o'zi (kassir yuzasi **veb**, 6-fazada qurilgan).

⛔ **Bu faza 3-servis chegarasini OCHADI va u YAKUNIY.** `PROJECT.md`
constraint: «Servislar soni: **aynan 3 ta** (core-api, cv-service,
bot-service) — ortiqcha mikroservis bo'linmaydi». `services/bot-service/`
bugun **umuman mavjud emas** va `compose.yaml` da ham yo'q — bu faza uni
yaratadi. To'rtinchi servis **tug'ilmaydi**.

</domain>

<decisions>
## Implementation Decisions

### Fazaning tub farqi (rejalashtirishga ta'sir qiladi)

- **D-01**: **Bu faza — birinchi TASHQARIGA CHIQADIGAN faza.** 1–6-fazalarda
  butun tizim ishonch chegarasi ichida edi: foydalanuvchilar autentifikatsiya
  qilingan xodimlar, ma'lumot VPS'dan chiqmasdi. Bu yerda **sotuvchi** —
  xodim emas — tizimga kiradi, va har bir xabar **Telegram serverlariga**,
  ya'ni **data-rezidentlik chegarasidan tashqariga** chiqadi. Shuning uchun
  har qaror «bu bayt chegaradan chiqsa, uni **qaytarib bo'lmaydi**» savoliga
  javob berishi kerak.
- **D-02**: **Nizo modeli kengaydi.** 6-fazada nizo «sotuvchi pul to'laganini
  isbotlay olmasligi» edi. Bu yerda ikkinchi nizo qo'shiladi: «**xabar
  kelmadi**». Shuning uchun yetkazilganlik holati (BOT-04) mahsulot
  xossasi, log emas — u nizo paytida ko'rsatiladigan yozuv.

### ⛔ Meros qilib olingan TAQIQLAR — muzokara qilinmaydi

- **D-03**: ⛔ **DALIL-KADR TELEGRAMGA HECH QACHON BORMAYDI.**
  `services/core-api/app/services/alerts.py:1-45` da bu **struktura**, kelishuv
  emas: rasm biriktiruvchi Telegram metodi **umuman yozilmagan**, `AlertEvent`
  da `snapshot_id` ustuni **atayin yo'q**, va frontend jufti — alert
  komponentlarida `<img>` taqig'i (`04-UI-SPEC.md` G-3). Sababi ikki qatlamli
  va ikkalasi ham **huquqiy**: (a) kadrda tashrifchilar yuzi bor — O'zR
  shaxsiy ma'lumotlar qonuni ostida; (b) Telegram serverlari
  **chegaradan tashqarida** va o'chirilgan xabar ham qolishi mumkin.
  ⛔ **Bu faza o'sha taqiqni KENGAYTIRADI, yumshatmaydi**: sotuvchi boti ham,
  direktor dayjesti ham, kvitansiya ham **matn**. Nomuvofiqlik xabarida dalil
  **havola** bo'lib boradi (veb yuzasiga, autentifikatsiya ostida) — kadr
  **bayt** bo'lib bormaydi.
- **D-04**: ⛔ **BOT TOKENI URL'NING BIR QISMI** (`alerts.py` 2-taqiq). Ya'ni
  Telegram HTTP istisnosining **matni tokenni tashiydi**. Yangi jo'natuvchi kod
  istisno matnini logga, `outbox.last_error` ustuniga yoki alertga **xom
  holda yozmaydi** — faqat **TURI** va status kodi. Bu 6-fazaning T-06-40
  naqshi bilan aynan bir sinf.
- **D-05**: ⛔ **`PERSONAL_ROUTES` O'SMAYDI.** 6-fazaning C-10/§5.5 qoidasi:
  moliyaviy marshrutlar `vendor_name`/`phone`/`full_name` **qaytarmaydi**, ism
  klientda **audit qilingan** `GET /vendors` bilan joinlanadi. Bot esa
  sotuvchining **o'ziga** o'z ma'lumotini ko'rsatadi — bu yangi yuza, va u
  **o'z marshrutida** yashaydi, mavjud moliyaviy marshrutlarni kengaytirmaydi.
- **D-06**: ⛔ **Saqlangan balans ustuni YO'Q** (BILL-03, 6-faza D-07/T-06-87).
  Bot ko'rsatadigan qoldiq — `vendor_outstanding()` ning **hosila** javobi.
  `balance`/`balance_soum` nomi **ham** paydo bo'lmaydi.
- **D-07**: Pul — **`BIGINT` so'm ↔ Python `int`**. `float`/`Decimal`/`round(`
  taqig'i (D-11, 6-faza) yangi modullarga ham **tarqaydi**. Xabar matnidagi
  summa formatlash ham butun sondan chiqadi.

### Servis chegarasi va outbox egaligi

- **D-08**: ⛔ **Outbox va CHIQUVCHI jo'natish — `core-api` da; `bot-service`
  faqat KIRUVCHI.** Ya'ni: `outbox` jadvali + jo'natuvchi worker core-api
  ichida (`alerts.py` allaqachon shu naqshda Telegram'ga yozadi);
  `bot-service` esa faqat Telegram update'larini (`/start`, contact ulashish,
  tugma bosish) qabul qiladi va core-api ning **ichki API'siga** murojaat
  qiladi.
  **Sabab uchta, har biri mustaqil:** (1) pul haqiqati core-api da, **RLS
  ostida** — bot-service ga DB bersak, **ikkinchi RLS yuzasi** ochilardi va
  6-fazaning T-06-21/22 kafolatlari o'sha yuzada takrorlanishi kerak bo'lardi;
  (2) `aiogram 3.30` `redis[hiredis]>=6.2,<8` va `pydantic<2.14` talab qiladi,
  core-api esa `redis 8.0.1` ga qadalgan (`CLAUDE.md` Version Compatibility) —
  ⛔ **ikki servis bitta navbat klientini BO'LISHA OLMAYDI**; (3) `alerts.py`
  ning ikki taqig'i allaqachon core-api da **o'lchanadi** — jo'natishni
  ko'chirish o'sha darvozalarni **ikkilantirar** edi.
- **D-09**: `bot-service` ⛔ **o'z `pyproject.toml` va `uv.lock` iga ega**
  (`CLAUDE.md`: «Isolate service dependency sets — one per service»). Pinlar:
  `aiogram[fast,redis,i18n]==3.30.0`, `redis[hiredis]>=7.4,<8`,
  `pydantic<2.14`. ⛔ Bu pinlar core-api'nikiga **tegmaydi**.
- **D-10**: `bot-service` ↔ core-api aloqasi — **ichki HTTP**, compose
  tarmog'i ichida, **servis-servis tokeni** bilan. Bot foydalanuvchi
  sessiyasini **o'zi tug'dirmaydi**: u «bu Telegram ID — mana shu vendor» deb
  aytadi, qolganini core-api RLS ostida hal qiladi.

### Case modeli (RECON-01, RECON-02)

- **D-11**: ⛔ **Case — ALOHIDA jadval** (`reconciliation_cases`),
  `billing_anomalies` ga ustun **qo'shilmaydi**.
  **Sabab:** anomaliya — **hodisa**, u 6-fazada dalil sinfiga kiritilgan va
  o'zgarmas bo'lishi kerak; case esa **jarayon** — mas'ul, holat, yechim
  **o'zgaradi**. Ikkisini bitta qatorga qo'shish o'zgarmas dalil qatorini
  **o'zgaruvchan** qilardi va bu 6-fazaning D-07/T-06-15 sinfini buzardi.
  Case anomaliyaga **ko'rsatkich** bilan bog'lanadi (muzlatilgan pointer
  naqshi, D-08/6-faza).
- **D-12**: Case holati — ⛔ **yopiq `StrEnum`**: `yangi` / `ko'rilmoqda` /
  `asosli` / `asossiz`. `other`/`custom` a'zosi **yo'q** (6-faza D-19/T-06-07
  naqshi) — erkin matn hisobotda guruhlanmaydi va hit-rate ni o'lchab
  bo'lmasdi.
- **D-13**: **Hit-rate — hosila, saqlanmaydi.** `asosli / (asosli + asossiz)`,
  `yangi`/`ko'rilmoqda` maxrajga **kirmaydi** (hali hal qilinmagan case
  metrikani pasaytirmasligi kerak). Saqlangan ustun D-06 bilan bir sinf.
- **D-14**: Case holati o'zgarishi — **audit qatori** (aktor + eski/yangi
  holat + vaqt). Yechim matni **erkin**, lekin holat **yopiq ro'yxat** — ikkisi
  aralashmaydi.

### Xabar tetiklari va vaqt (RECON-03, CASH-05, BOT-03)

- **D-15**: ⛔ **Kechki nomuvofiqlik xabari PROYEKSIYADAN o'qiydi, hisobdan
  EMAS.** Sabab mexanik: `BILLING_CLOSE_CRON = "10 4 * * *"`
  (`worker.py:445`) — D kunining hisobi **D+1 ning 04:10** da tug'iladi. Ya'ni
  kechqurun `daily_charges` da bugungi kun **hali yo'q**. Manba —
  `pending_projection()` (6-faza D-16), **o'sha bitta funksiya**, faqat
  `as_of` boshqa. ⛔ Ikkinchi implementatsiya yozilsa, kechki xabar bilan
  ertalabki dayjest **ajralib ketardi** — bu loyihada takroran topilgan
  «ikki haqiqat manbai» sinfi.
- **D-16**: **Ertalabki dayjest hisobdan o'qiydi** — u `04:10` dan keyin
  yuguradi, ya'ni kechagi kun **yozilgan** va **o'zgarmas**. Tavsiya:
  dayjest **08:00**, kechki xabar **20:45** Asia/Tashkent. ⛔ Lekin **tartib
  kafolati cron satrlariga tayanmaydi** (6-faza D-13 darsi): har ikki job
  **idempotent** va manbasini **o'zi** tekshiradi.
- **D-17**: ⛔ **Yangi cron joblar `EXPECTED_COMPONENTS` va
  `alert_sweep::watched` ga QO'SHILADI.** Bu 6-fazaning T-06-41 kafolati va
  `deferred-items.md` 2-bandining aynan darsi: ro'yxatga olinmagan cron
  nosozligi **jimgina** qoladi. Yurak urishining **yo'qligi** (`None` ham
  eskirish) alert beradi.
- **D-18**: ⛔ **Kvitansiya (CASH-05) HECH QACHON to'xtatilmaydi** — na quiet
  hours, na throttling uni ushlab qolmaydi. Sabab D-02: kvitansiya —
  sotuvchining **hozirgina to'laganini** isbotlaydigan yozuv; uni kechiktirish
  nizo modelini buzadi. `ALERT_META.never_suppressed` bayrog'i (`alerting.py`)
  aynan shu tushunchaning mavjud uyi — **o'sha naqsh qayta ishlatiladi**.
  Eslatma (BOT-03) va dayjest (RECON-03) esa quiet hours ga **bo'ysunadi**.
- **D-19**: Quiet hours va `N` kun chegarasi — **bozor kesimida sozlanadi**
  (`market_id` bo'yicha), global konstanta emas. Sabab: multi-tenant
  constraint — «yangi bozor kod yozmasdan wizard orqali ulanadi». Standart
  qiymatlar `[ASSUMED]` bo'lib **kodda sabab bilan** yoziladi va sozlash
  nuqtasi hujjatlashtiriladi.

### Outbox mexanikasi (BOT-04)

- **D-20**: Outbox qatori — **append-only holat mashinasi**:
  `pending → sent → delivered | failed | blocked`. ⛔ O'chirish yo'q; qayta
  urinish **yangi urinish qatori** yoki `attempt_count` — lekin **asl niyat
  qatori o'zgarmaydi** (6-faza D-23 naqshi).
- **D-21**: **Idempotentlik strukturaviy** — `UNIQUE (market_id,
  dedupe_key)`. Bir to'lov uchun ikki kvitansiya yuborilishi 6-fazaning
  T-06-49 bilan aynan bir sinfdagi xato bo'lardi; u yerda yechim `UNIQUE`
  cheklov edi, bu yerda ham **shunday** — ilova intizomi emas.
- **D-22**: **Botni bloklagan foydalanuvchi belgilanadi** (`blocked`) va unga
  keyingi urinishlar **qilinmaydi**. Telegram ning `403 Forbidden: bot was
  blocked by the user` javobi — **ma'lumot**, xato emas: u sotuvchi bilan
  aloqa uzilganini bildiradi va **direktor ko'rishi** kerak.
- **D-23**: Jo'natuvchi ⛔ **bloklamaydi** (`alerts.py` ning «YUPQA, SIRSIZ va
  BLOKLAMAYDIGAN» qoidasi). Telegram sekinlashsa, pul yozuvi yoki case
  yuritish **to'xtamaydi**.

### Sotuvchi identifikatsiyasi (BOT-01)

- **D-24**: ⛔ **Faqat Telegram ning `contact` obyekti qabul qilinadi** —
  qo'lda **terilgan raqam EMAS**. Sabab: terilgan raqam — foydalanuvchining
  **da'vosi**; `contact` esa Telegram **o'zi kafolatlagan** yagona narsa.
  Terilgan raqamni qabul qilish begona sotuvchining qarzini ko'rish yo'lini
  ochardi.
- **D-25**: Raqam `phonenumbers` bilan **E.164 ga normallashtiriladi**
  (`CLAUDE.md`: «normalise at the boundary or you will get duplicate
  vendors») va `vendors` reyestriga **bozor ichida** solishtiriladi.
- **D-26**: **Uch shox nomlangan:** (a) **mos kelmadi** → ulanish **yo'q**,
  neytral matn (⛔ «bu raqam ro'yxatda yo'q» deb **tasdiqlamaydi** — u
  reyestrni tashqaridan tekshirish yo'li bo'lardi), admin «kutilmoqda»
  ro'yxatida ko'radi; (b) **bir nechta moslik** → ulanish **yo'q** +
  anomaliya (reyestr nuqsoni, jimgina tanlanmaydi); (c) **qayta ulanish**
  (o'sha raqam, boshqa Telegram akkaunti) → eski bog'lanish **bekor
  qilinadi** + audit qatori.
- **D-27**: Bog'lanish `vendors` ga ustun sifatida emas, **alohida jadvalda**
  (`vendor_telegram_bindings`) — bitta sotuvchining vaqt bo'yicha bir nechta
  bog'lanish tarixi bo'lishi mumkin va D-26(c) shuni talab qiladi.

### Bosh ekran ko'rsatkichi (RECON-06)

- **D-28**: ⛔ **BITTA marshrut** (`GET /me/headline`), rol bo'yicha **serverda**
  yechiladi — uch alohida marshrut emas. Sabab ikkita: (1) uch marshrut = uch
  haqiqat, ular ajralib ketadi; (2) ⛔ **kassir tizim summasini ko'rmasligi
  kerak** (6-faza T-06-53/T-06-59, ko'r deklaratsiya) — qaysi raqam qaysi rolga
  ruxsat etilganini **server** hal qiladi, klient **so'ramaydi**.
- **D-29**: Javob — **aynan bitta son + yorliq**. Yig'indi, ro'yxat yoki
  ikkinchi son **yo'q** (6-faza T-06-75 naqshi: ko'rinadigan sonlar
  **to'plami** o'lchanadi).

### Til va matn (uchala locale)

- **D-30**: Bot matnlari — `aiogram[i18n]` + Babel, **bot-service ning o'z
  katalogida**. Lekin ⛔ **atamalar YAGONA** — «qarz», «patta», «rasta»,
  «smena» bot va vebda **bir xil** so'z bo'lishi shart. Darvoza: ikkala
  manbadagi kalit atamalar to'plamini solishtiruvchi test.
- **D-31**: Uchala locale (`uz-Latn`, `uz-Cyrl`, `ru`) — **majburiy**,
  parity darvozasi bilan (frontend `i18n:check` naqshi).

### Claude's Discretion

Quyidagilar **rejalashtirish va tadqiqotga** qoldiriladi — ular
implementatsiya tafsiloti, foydalanuvchi qarori emas:
jadval/ustun nomlari; webhook vs long-polling tanlovi (bot-service uchun);
outbox worker ning `taskiq` vazifasi sifatida yoki alohida sikl bo'lib
yugurishi; retry backoff egri chizig'i; case ro'yxatining sahifalash usuli;
`reconciliation_cases` ↔ `billing_anomalies` FK ning kompozit shakli.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### ⛔ Muzokara qilinmaydigan taqiqlar (BIRINCHI O'QILADI)
- `services/core-api/app/services/alerts.py` §1-45 — **1-TAQIQ** (dalil-kadr
  Telegram'ga hech qachon) va **2-TAQIQ** (bot tokeni URL'da → istisno matni
  uni tashiydi). Bu faza ikkalasini ham **kengaytiradi**.
- `.planning/phases/06-billing-va-kassir/06-SECURITY.md` — 106 tahdidli
  reyestr; ayniqsa T-06-05/06 (kassir huquqlari), T-06-21/22 (RLS +
  `SECURITY DEFINER` yuzasi), T-06-44/53/56 (kassirga axborot oshkorligi),
  T-06-81/82 (dalil-kadr yuzasining kengaymasligi), T-06-87 (saqlangan
  balans nomi).
- `.planning/phases/04-*/04-UI-SPEC.md` G-3 — alert komponentlarida `<img>`
  taqig'i (backend taqig'ining frontend jufti).

### Faza doirasi va talablar
- `.planning/ROADMAP.md` §«Phase 7» — maqsad, 5 muvaffaqiyat mezoni, timeline.
- `.planning/REQUIREMENTS.md` — RECON-01/02/03/06, CASH-05, BOT-01/02/03/04
  (65, 69-71, 74, 78-81-qatorlar).
- `.planning/PROJECT.md` — «aynan 3 ta servis» va data-rezidentlik cheklovi.

### Meros qilib olinadigan qarorlar
- `.planning/phases/06-billing-va-kassir/06-CONTEXT.md` — D-01…D-24 (ayniqsa
  D-07 o'zgarmaslik, D-08 muzlatilgan dalil, D-11 pul turi, D-16 proyeksiya
  bitta kod yo'lidan, D-19 yopiq sabab-kod, D-23 append-only).
- `.planning/phases/06-billing-va-kassir/06-VALIDATION.md` — `gate` byudjeti
  **2300 s**, `gate:fast` **200 s**; yangi testlar shu byudjet ichiga sig'ishi
  kerak.
- `.planning/phases/06-billing-va-kassir/deferred-items.md` **2-band** —
  `day_close` yurak urishi reyestrda yo'q; D-17 shu sinfdagi xatoni
  takrorlamaslik uchun.
- `.planning/phases/06-billing-va-kassir/06-UI-SPEC.md` §5.5, §8.8, §10.4 —
  shaxsiy maydon va yig'indi taqiqlari.

### Mavjud mexanizmlar (qayta ishlatiladi, takrorlanmaydi)
- `services/core-api/app/jobs/alerting.py` — `ALERT_META` reyestri
  (`never_suppressed`/`platform_scoped`/`storable`), `alert_sweep`,
  `daily_digest`, `_swallow`, `_write_heartbeat`. D-18 va D-17 shu fayldagi
  tushunchalarga suyanadi.
- `services/core-api/app/worker.py` §139-154, §445-453 — cron reyestri va
  `BILLING_CLOSE_CRON = "10 4 * * *"` (D-15 ning mexanik sababi).
- `services/core-api/app/repositories/billing_repo.py` —
  `pending_projection()`, `vendor_outstanding()`, `vendor_charge_allocation()`
  (D-06, D-15 manbasi).
- `CLAUDE.md` §Version Compatibility — `aiogram 3.30` ↔ `pydantic<2.14` ↔
  `redis<8` qarama-qarshiligi (D-08/D-09 ning uchinchi sababi).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`alerts.py::AlertSender`** — yupqa, sirsiz, bloklamaydigan Telegram
  jo'natuvchisi. Outbox jo'natuvchisi **shuni** kengaytiradi yoki **shu
  intizom bilan** yoziladi; yangi mustaqil jo'natuvchi yozish ikki taqiqni
  ikkilantirar edi.
- **`ALERT_META` + `never_suppressed`** — «bu xabar hech qachon
  bostirilmaydi» tushunchasining mavjud uyi. D-18 (kvitansiya) shu bayroqni
  ishlatadi.
- **`billing_repo.pending_projection()` / `vendor_outstanding()`** — kechki
  xabar va BOT-02 ning **yagona** arifmetika manbai.
- **`active_market_ids()`** — joblar uchun **yagona** RLS-chetlab o'tuvchi
  yuza (6-faza D-15/T-06-37). Yangi joblar **shundan** o'qiydi.
- **`phonenumbers`** — `CLAUDE.md` da allaqachon core-api bog'liqligi
  sifatida; D-25 uni ishlatadi, yangi paket **kerak emas**.
- **`system_heartbeats` + `EXPECTED_COMPONENTS`** — D-17 ning mexanizmi.

### Established Patterns
- **Yo'qlik = struktura, kelishuv emas.** Metod yo'q, ustun yo'q, marshrut
  yozilmagan — va buni `dir()`/to'plam tengligi darvozasi o'lchaydi.
  (`alerts.py`, `security.py:6-11`, `go2rtc.py:193-197`.)
- **Yopiq `StrEnum` + `other` a'zosining yo'qligi**, to'plam tengligi bilan
  o'lchanadi (6-faza T-06-07). D-12 shu naqshda.
- **Muzlatilgan pointer**: o'zgaruvchan qatorga emas, o'zgarmas qatorga
  ishora (6-faza D-08/T-06-24). D-11 shu naqshda.
- **Hosila, saqlanmaydi**: balans (BILL-03), taqsimlash
  (`FIFO_OLDEST_SERVICE_DATE_FIRST`). D-13 (hit-rate) shu sinfda.
- **Xato TURI yoziladi, MATNI emas** (6-faza T-06-40). D-04 shu naqshda.
- **Har servis o'z `pyproject.toml`/`uv.lock` i bilan** — pin
  qarama-qarshiliklari shu bilan hal qilingan (`taskiq` vs `arq` darsi).

### Integration Points
- **⚠ `services/bot-service/` MAVJUD EMAS** va `compose.yaml` da yo'q
  (servislar: db, cache, storage, migrate, core-api, worker, scheduler,
  cv-service, cv-tests, go2rtc, frontend, nginx, nvr-sim, nvr-sim-rtsp,
  tests). Bu faza **yangi servis + compose yozuvi + o'z lockfayli** ni
  yaratadi. Bu fazaning eng katta strukturaviy ishi.
- **Yangi jadvallar** `0023+` migratsiyalarida: `reconciliation_cases`,
  `outbox` (nomlar rejalashtirishga qoldiriladi), `vendor_telegram_bindings`.
  Hammasida `market_id` + RLS `ENABLE`+`FORCE` + tenant policy + kompozit FK
  (6-faza T-06-21 naqshi) — ⛔ **yangi `SECURITY DEFINER` funksiya
  qo'shilmaydi** (`DEFINER_SURFACES = ()` bo'sh qolishi kerak, T-06-22).
- **Yangi cron joblar** `worker.py` reyestriga + `EXPECTED_COMPONENTS` ga
  (D-17). ⛔ Deploy bandi: `docker compose up -d --force-recreate scheduler`
  **va** yangi `bot-service` — cron jadvali import paytida o'qiladi.
- **RECON-06** frontendning uchala rol bosh ekraniga ulanadi (mavjud
  `/[locale]/(app)/` marshrutlari).

</code_context>

<specifics>
## Specific Ideas

- **Kechki xabar va ertalabki dayjest bir xil raqamni bermasligi — NUQSON
  EMAS, dizayn.** Kechqurun proyeksiya (`as_of=hozir`), ertalab yozilgan
  hisob. Farq **kutilgan** va u xabar matnida **ochiq** aytilishi kerak
  («kutilayotgan» vs «yozilgan») — 6-fazaning D-17 naqshi. Aks holda direktor
  ikki raqamni ko'rib tizimga ishonchini yo'qotadi.
- **«Xabar kelmadi» nizosi uchun** yetkazilganlik holati **direktor ko'radigan
  yuzada** bo'lishi kerak, faqat jadvalda emas — aks holda BOT-04 ning
  amaliy qiymati nolga tushadi.
- **Bloklagan sotuvchi** — bu **ma'lumot**, xato emas (D-22). U direktorga
  «bu sotuvchi bilan aloqa yo'q» degan signal beradi va u qarz undirish
  jarayonining bir qismi.

</specifics>

<deferred>
## Deferred Ideas

- **Direktor botining BUYRUQ yuzasi** (bot orqali case holatini o'zgartirish,
  hisobot so'rash) — bu faza direktorni **oluvchi** deb belgilaydi (RECON-03).
  Buyruq yuzasi yangi qobiliyat; tabiiy egasi — 8-faza yoki V2.
- **Sotuvchi botidan to'lov qilish / to'lovga da'vo** — CASH-05 faqat
  **kvitansiya** (bir tomonlama). Ikki tomonlama oqim yangi qobiliyat.
- **`V2-CASH-05` kassir offline-lite rejimi** — `REQUIREMENTS.md:93` da
  allaqachon V2 ga qo'yilgan.
- **`deferred-items.md` 9-band** (ism joinining 50 ta sahifa chegarasi) —
  egasi **8-fazaning hisobot yuzasi**, bu fazada tegilmaydi.
- **`deferred-items.md` 3-band** (`PUT /camera-zones` `QUERY_PARAM_ROUTES`
  istisnosi) — 05-06 merosi, bu fazaning qamrovidan tashqarida.
- **5-fazadan meros flaky test** (`test_blind_audit.py::test_a_different_
  round_number_draws_a_different_sample`) — `deferred-items.md` 1-band.

</deferred>

---

*Phase: 7-Nomuvofiqlik, bildirishnoma va botlar*
*Context gathered: 2026-08-11*
