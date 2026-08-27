# Phase 7: Nomuvofiqlik, bildirishnoma va botlar — Research

**Researched:** 2026-08-11
**Domain:** Telegram bot servisi (aiogram), chiquvchi xabar outboxi, case yuritish, rol bo'yicha bosh ko'rsatkich
**Confidence:** HIGH (stek va mexanizmlar), MEDIUM (Telegram yetkazilganlik semantikasi — quyida ochiq yozilgan)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

> ⛔ Quyidagilar **qulflangan**. Bu tadqiqot ularga muqobil izlamaydi — ularni **qanday
> bajarish** kerakligini aniqlaydi.

### Locked Decisions

**Fazaning tub farqi**

- **D-01**: **Bu faza — birinchi TASHQARIGA CHIQADIGAN faza.** 1–6-fazalarda butun tizim
  ishonch chegarasi ichida edi: foydalanuvchilar autentifikatsiya qilingan xodimlar,
  ma'lumot VPS'dan chiqmasdi. Bu yerda **sotuvchi** — xodim emas — tizimga kiradi, va har
  bir xabar **Telegram serverlariga**, ya'ni **data-rezidentlik chegarasidan tashqariga**
  chiqadi. Shuning uchun har qaror «bu bayt chegaradan chiqsa, uni **qaytarib
  bo'lmaydi**» savoliga javob berishi kerak.
- **D-02**: **Nizo modeli kengaydi.** 6-fazada nizo «sotuvchi pul to'laganini isbotlay
  olmasligi» edi. Bu yerda ikkinchi nizo qo'shiladi: «**xabar kelmadi**». Shuning uchun
  yetkazilganlik holati (BOT-04) mahsulot xossasi, log emas — u nizo paytida
  ko'rsatiladigan yozuv.

**⛔ Meros qilib olingan TAQIQLAR — muzokara qilinmaydi**

- **D-03**: ⛔ **DALIL-KADR TELEGRAMGA HECH QACHON BORMAYDI.**
  `services/core-api/app/services/alerts.py:1-45` da bu **struktura**, kelishuv emas: rasm
  biriktiruvchi Telegram metodi **umuman yozilmagan**, `AlertEvent` da `snapshot_id`
  ustuni **atayin yo'q**, va frontend jufti — alert komponentlarida `<img>` taqig'i
  (`04-UI-SPEC.md` G-3). Sababi ikki qatlamli va ikkalasi ham **huquqiy**: (a) kadrda
  tashrifchilar yuzi bor — O'zR shaxsiy ma'lumotlar qonuni ostida; (b) Telegram serverlari
  **chegaradan tashqarida** va o'chirilgan xabar ham qolishi mumkin.
  ⛔ **Bu faza o'sha taqiqni KENGAYTIRADI, yumshatmaydi**: sotuvchi boti ham, direktor
  dayjesti ham, kvitansiya ham **matn**. Nomuvofiqlik xabarida dalil **havola** bo'lib
  boradi (veb yuzasiga, autentifikatsiya ostida) — kadr **bayt** bo'lib bormaydi.
- **D-04**: ⛔ **BOT TOKENI URL'NING BIR QISMI** (`alerts.py` 2-taqiq). Ya'ni Telegram HTTP
  istisnosining **matni tokenni tashiydi**. Yangi jo'natuvchi kod istisno matnini logga,
  `outbox.last_error` ustuniga yoki alertga **xom holda yozmaydi** — faqat **TURI** va
  status kodi. Bu 6-fazaning T-06-40 naqshi bilan aynan bir sinf.
- **D-05**: ⛔ **`PERSONAL_ROUTES` O'SMAYDI.** 6-fazaning C-10/§5.5 qoidasi: moliyaviy
  marshrutlar `vendor_name`/`phone`/`full_name` **qaytarmaydi**, ism klientda **audit
  qilingan** `GET /vendors` bilan joinlanadi. Bot esa sotuvchining **o'ziga** o'z
  ma'lumotini ko'rsatadi — bu yangi yuza, va u **o'z marshrutida** yashaydi, mavjud
  moliyaviy marshrutlarni kengaytirmaydi.
- **D-06**: ⛔ **Saqlangan balans ustuni YO'Q** (BILL-03, 6-faza D-07/T-06-87). Bot
  ko'rsatadigan qoldiq — `vendor_outstanding()` ning **hosila** javobi.
  `balance`/`balance_soum` nomi **ham** paydo bo'lmaydi.
- **D-07**: Pul — **`BIGINT` so'm ↔ Python `int`**. `float`/`Decimal`/`round(` taqig'i
  (D-11, 6-faza) yangi modullarga ham **tarqaydi**. Xabar matnidagi summa formatlash ham
  butun sondan chiqadi.

**Servis chegarasi va outbox egaligi**

- **D-08**: ⛔ **Outbox va CHIQUVCHI jo'natish — `core-api` da; `bot-service` faqat
  KIRUVCHI.** Ya'ni: `outbox` jadvali + jo'natuvchi worker core-api ichida (`alerts.py`
  allaqachon shu naqshda Telegram'ga yozadi); `bot-service` esa faqat Telegram
  update'larini (`/start`, contact ulashish, tugma bosish) qabul qiladi va core-api ning
  **ichki API'siga** murojaat qiladi.
  **Sabab uchta, har biri mustaqil:** (1) pul haqiqati core-api da, **RLS ostida** —
  bot-service ga DB bersak, **ikkinchi RLS yuzasi** ochilardi va 6-fazaning T-06-21/22
  kafolatlari o'sha yuzada takrorlanishi kerak bo'lardi; (2) `aiogram 3.30`
  `redis[hiredis]>=6.2,<8` va `pydantic<2.14` talab qiladi, core-api esa `redis 8.0.1` ga
  qadalgan (`CLAUDE.md` Version Compatibility) — ⛔ **ikki servis bitta navbat klientini
  BO'LISHA OLMAYDI**; (3) `alerts.py` ning ikki taqig'i allaqachon core-api da
  **o'lchanadi** — jo'natishni ko'chirish o'sha darvozalarni **ikkilantirar** edi.
- **D-09**: `bot-service` ⛔ **o'z `pyproject.toml` va `uv.lock` iga ega** (`CLAUDE.md`:
  «Isolate service dependency sets — one per service»). Pinlar:
  `aiogram[fast,redis,i18n]==3.30.0`, `redis[hiredis]>=7.4,<8`, `pydantic<2.14`. ⛔ Bu
  pinlar core-api'nikiga **tegmaydi**.
- **D-10**: `bot-service` ↔ core-api aloqasi — **ichki HTTP**, compose tarmog'i ichida,
  **servis-servis tokeni** bilan. Bot foydalanuvchi sessiyasini **o'zi tug'dirmaydi**: u
  «bu Telegram ID — mana shu vendor» deb aytadi, qolganini core-api RLS ostida hal qiladi.

**Case modeli (RECON-01, RECON-02)**

- **D-11**: ⛔ **Case — ALOHIDA jadval** (`reconciliation_cases`), `billing_anomalies` ga
  ustun **qo'shilmaydi**. **Sabab:** anomaliya — **hodisa**, u 6-fazada dalil sinfiga
  kiritilgan va o'zgarmas bo'lishi kerak; case esa **jarayon** — mas'ul, holat, yechim
  **o'zgaradi**. Ikkisini bitta qatorga qo'shish o'zgarmas dalil qatorini **o'zgaruvchan**
  qilardi va bu 6-fazaning D-07/T-06-15 sinfini buzardi. Case anomaliyaga
  **ko'rsatkich** bilan bog'lanadi (muzlatilgan pointer naqshi, D-08/6-faza).
- **D-12**: Case holati — ⛔ **yopiq `StrEnum`**: `yangi` / `ko'rilmoqda` / `asosli` /
  `asossiz`. `other`/`custom` a'zosi **yo'q** (6-faza D-19/T-06-07 naqshi) — erkin matn
  hisobotda guruhlanmaydi va hit-rate ni o'lchab bo'lmasdi.
- **D-13**: **Hit-rate — hosila, saqlanmaydi.** `asosli / (asosli + asossiz)`,
  `yangi`/`ko'rilmoqda` maxrajga **kirmaydi** (hali hal qilinmagan case metrikani
  pasaytirmasligi kerak). Saqlangan ustun D-06 bilan bir sinf.
- **D-14**: Case holati o'zgarishi — **audit qatori** (aktor + eski/yangi holat + vaqt).
  Yechim matni **erkin**, lekin holat **yopiq ro'yxat** — ikkisi aralashmaydi.

**Xabar tetiklari va vaqt (RECON-03, CASH-05, BOT-03)**

- **D-15**: ⛔ **Kechki nomuvofiqlik xabari PROYEKSIYADAN o'qiydi, hisobdan EMAS.** Sabab
  mexanik: `BILLING_CLOSE_CRON = "10 4 * * *"` (`worker.py:445`) — D kunining hisobi
  **D+1 ning 04:10** da tug'iladi. Ya'ni kechqurun `daily_charges` da bugungi kun **hali
  yo'q**. Manba — `pending_projection()` (6-faza D-16), **o'sha bitta funksiya**, faqat
  `as_of` boshqa. ⛔ Ikkinchi implementatsiya yozilsa, kechki xabar bilan ertalabki
  dayjest **ajralib ketardi** — bu loyihada takroran topilgan «ikki haqiqat manbai» sinfi.
- **D-16**: **Ertalabki dayjest hisobdan o'qiydi** — u `04:10` dan keyin yuguradi, ya'ni
  kechagi kun **yozilgan** va **o'zgarmas**. Tavsiya: dayjest **08:00**, kechki xabar
  **20:45** Asia/Tashkent. ⛔ Lekin **tartib kafolati cron satrlariga tayanmaydi** (6-faza
  D-13 darsi): har ikki job **idempotent** va manbasini **o'zi** tekshiradi.
- **D-17**: ⛔ **Yangi cron joblar `EXPECTED_COMPONENTS` va `alert_sweep::watched` ga
  QO'SHILADI.** Bu 6-fazaning T-06-41 kafolati va `deferred-items.md` 2-bandining aynan
  darsi: ro'yxatga olinmagan cron nosozligi **jimgina** qoladi. Yurak urishining
  **yo'qligi** (`None` ham eskirish) alert beradi.
- **D-18**: ⛔ **Kvitansiya (CASH-05) HECH QACHON to'xtatilmaydi** — na quiet hours, na
  throttling uni ushlab qolmaydi. Sabab D-02: kvitansiya — sotuvchining **hozirgina
  to'laganini** isbotlaydigan yozuv; uni kechiktirish nizo modelini buzadi.
  `ALERT_META.never_suppressed` bayrog'i (`alerting.py`) aynan shu tushunchaning mavjud
  uyi — **o'sha naqsh qayta ishlatiladi**. Eslatma (BOT-03) va dayjest (RECON-03) esa quiet
  hours ga **bo'ysunadi**.
- **D-19**: Quiet hours va `N` kun chegarasi — **bozor kesimida sozlanadi** (`market_id`
  bo'yicha), global konstanta emas. Sabab: multi-tenant constraint — «yangi bozor kod
  yozmasdan wizard orqali ulanadi». Standart qiymatlar `[ASSUMED]` bo'lib **kodda sabab
  bilan** yoziladi va sozlash nuqtasi hujjatlashtiriladi.

**Outbox mexanikasi (BOT-04)**

- **D-20**: Outbox qatori — **append-only holat mashinasi**:
  `pending → sent → delivered | failed | blocked`. ⛔ O'chirish yo'q; qayta urinish **yangi
  urinish qatori** yoki `attempt_count` — lekin **asl niyat qatori o'zgarmaydi** (6-faza
  D-23 naqshi).
- **D-21**: **Idempotentlik strukturaviy** — `UNIQUE (market_id, dedupe_key)`. Bir to'lov
  uchun ikki kvitansiya yuborilishi 6-fazaning T-06-49 bilan aynan bir sinfdagi xato
  bo'lardi; u yerda yechim `UNIQUE` cheklov edi, bu yerda ham **shunday** — ilova intizomi
  emas.
- **D-22**: **Botni bloklagan foydalanuvchi belgilanadi** (`blocked`) va unga keyingi
  urinishlar **qilinmaydi**. Telegram ning `403 Forbidden: bot was blocked by the user`
  javobi — **ma'lumot**, xato emas: u sotuvchi bilan aloqa uzilganini bildiradi va
  **direktor ko'rishi** kerak.
- **D-23**: Jo'natuvchi ⛔ **bloklamaydi** (`alerts.py` ning «YUPQA, SIRSIZ va
  BLOKLAMAYDIGAN» qoidasi). Telegram sekinlashsa, pul yozuvi yoki case yuritish
  **to'xtamaydi**.

**Sotuvchi identifikatsiyasi (BOT-01)**

- **D-24**: ⛔ **Faqat Telegram ning `contact` obyekti qabul qilinadi** — qo'lda **terilgan
  raqam EMAS**. Sabab: terilgan raqam — foydalanuvchining **da'vosi**; `contact` esa
  Telegram **o'zi kafolatlagan** yagona narsa. Terilgan raqamni qabul qilish begona
  sotuvchining qarzini ko'rish yo'lini ochardi.
- **D-25**: Raqam `phonenumbers` bilan **E.164 ga normallashtiriladi** (`CLAUDE.md`:
  «normalise at the boundary or you will get duplicate vendors») va `vendors` reyestriga
  **bozor ichida** solishtiriladi.
- **D-26**: **Uch shox nomlangan:** (a) **mos kelmadi** → ulanish **yo'q**, neytral matn
  (⛔ «bu raqam ro'yxatda yo'q» deb **tasdiqlamaydi** — u reyestrni tashqaridan tekshirish
  yo'li bo'lardi), admin «kutilmoqda» ro'yxatida ko'radi; (b) **bir nechta moslik** →
  ulanish **yo'q** + anomaliya (reyestr nuqsoni, jimgina tanlanmaydi); (c) **qayta
  ulanish** (o'sha raqam, boshqa Telegram akkaunti) → eski bog'lanish **bekor qilinadi** +
  audit qatori.
- **D-27**: Bog'lanish `vendors` ga ustun sifatida emas, **alohida jadvalda**
  (`vendor_telegram_bindings`) — bitta sotuvchining vaqt bo'yicha bir nechta bog'lanish
  tarixi bo'lishi mumkin va D-26(c) shuni talab qiladi.

**Bosh ekran ko'rsatkichi (RECON-06)**

- **D-28**: ⛔ **BITTA marshrut** (`GET /me/headline`), rol bo'yicha **serverda**
  yechiladi — uch alohida marshrut emas. Sabab ikkita: (1) uch marshrut = uch haqiqat,
  ular ajralib ketadi; (2) ⛔ **kassir tizim summasini ko'rmasligi kerak** (6-faza
  T-06-53/T-06-59, ko'r deklaratsiya) — qaysi raqam qaysi rolga ruxsat etilganini
  **server** hal qiladi, klient **so'ramaydi**.
- **D-29**: Javob — **aynan bitta son + yorliq**. Yig'indi, ro'yxat yoki ikkinchi son
  **yo'q** (6-faza T-06-75 naqshi: ko'rinadigan sonlar **to'plami** o'lchanadi).

**Til va matn (uchala locale)**

- **D-30**: Bot matnlari — `aiogram[i18n]` + Babel, **bot-service ning o'z katalogida**.
  Lekin ⛔ **atamalar YAGONA** — «qarz», «patta», «rasta», «smena» bot va vebda **bir xil**
  so'z bo'lishi shart. Darvoza: ikkala manbadagi kalit atamalar to'plamini solishtiruvchi
  test.
- **D-31**: Uchala locale (`uz-Latn`, `uz-Cyrl`, `ru`) — **majburiy**, parity darvozasi
  bilan (frontend `i18n:check` naqshi).

### Claude's Discretion

Quyidagilar **rejalashtirish va tadqiqotga** qoldiriladi — ular implementatsiya tafsiloti,
foydalanuvchi qarori emas: jadval/ustun nomlari; **webhook vs long-polling tanlovi**
(bot-service uchun); **outbox worker ning `taskiq` vazifasi sifatida yoki alohida sikl
bo'lib yugurishi**; **retry backoff egri chizig'i**; **case ro'yxatining sahifalash
usuli**; **`reconciliation_cases` ↔ `billing_anomalies` FK ning kompozit shakli**.

> Bu tadqiqot oltala bandning har biriga **bitta qaror** beradi (menyu emas) —
> §«Discretion qarorlari» ga qarang.

### Deferred Ideas (OUT OF SCOPE)

- **Direktor botining BUYRUQ yuzasi** (bot orqali case holatini o'zgartirish, hisobot
  so'rash) — bu faza direktorni **oluvchi** deb belgilaydi (RECON-03). Buyruq yuzasi yangi
  qobiliyat; tabiiy egasi — 8-faza yoki V2.
- **Sotuvchi botidan to'lov qilish / to'lovga da'vo** — CASH-05 faqat **kvitansiya** (bir
  tomonlama). Ikki tomonlama oqim yangi qobiliyat.
- **`V2-CASH-05` kassir offline-lite rejimi** — `REQUIREMENTS.md:93` da allaqachon V2 ga
  qo'yilgan.
- **`deferred-items.md` 9-band** (ism joinining 50 ta sahifa chegarasi) — egasi
  **8-fazaning hisobot yuzasi**, bu fazada tegilmaydi.
- **`deferred-items.md` 3-band** (`PUT /camera-zones` `QUERY_PARAM_ROUTES` istisnosi) —
  05-06 merosi, bu fazaning qamrovidan tashqarida.
- **5-fazadan meros flaky test**
  (`test_blind_audit.py::test_a_different_round_number_draws_a_different_sample`) —
  `deferred-items.md` 1-band.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Tavsif (`REQUIREMENTS.md`) | Tadqiqot qaysi topilma bilan qo'llab-quvvatlaydi |
|----|-----------|-------------------|
| **RECON-01** | Kunlik nomuvofiqlik hisoboti: «band, lekin to'lovsiz» + «ro'yxatga olinmagan savdo», rasm-dalil **havolalari** bilan | §«Nomuvofiqlik ikki SINF» — sinf A hosila (`daily_charges` − `payments`), sinf B mavjud `billing_anomalies`. Dalil `charge_evidence` → `snapshots/{id}/image` marshrutiga **havola** (D-03) |
| **RECON-02** | Case: mas'ul, holat, yechim; hit-rate | §«Case modeli» — `reconciliation_cases` ikki mustaqil kompozit FK + `CHECK` bilan; hit-rate SQL hosilasi (D-13) |
| **RECON-03** | Direktor ertalabki dayjest + kechki nomuvofiqlik xabari | §«Ikki xabar, ikki manba» — `08:00` hisobdan, `20:45` `pending_projection()` dan (D-15/D-16); ikkala cron `EXPECTED_COMPONENTS` da |
| **RECON-06** | Har rol bosh ekranida bitta asosiy ko'rsatkich | §«`GET /me/headline`» — huquq bo'yicha determinlashgan yechim + ⛔ **kassir uchun SON, SUMMA emas** (T-06-53 bilan to'qnashuv, §«Pitfall 1») |
| **CASH-05** | To'lov kiritilishi bilan zudlik push-kvitansiya | §«Outbox mexanikasi» — `POST /payments` ning **o'sha tranzaksiyasida** outbox qatori; `never_suppressed` (D-18) |
| **BOT-01** | Contact ulashish orqali ulanish | §«Vendor bog'lanishi» — `contact.user_id == message.from_user.id` darvozasi, `phonenumbers` E.164, uch nomlangan shox |
| **BOT-02** | Qoldiq/qarz va to'lov tarixi | §«Ichki bot API» — `vendor_outstanding()` + `vendor_charge_allocation()` (6-fazada yozilgan, **iste'molchisi bu faza**) |
| **BOT-03** | Qarz N kundan oshsa avtomatik eslatma | §«Eslatma jobi» — bozor kesimidagi `overdue_reminder_days`, quiet hours ga bo'ysunadi |
| **BOT-04** | Outbox + throttling + yetkazilganlik holati | §«Outbox mexanikasi» + ⛔ §«Telegram YETKAZILGANLIK haqida NIMA aytadi va NIMA aytmaydi» |
</phase_requirements>

---

## Summary

Bu faza uchta mustaqil ish bo'lagidan iborat va ularning **narxi teng emas**. Eng katta
strukturaviy ish — `bot-service` ning tug'ilishi: u bugun na diskda, na `compose.yaml` da
mavjud (`compose.yaml` da o'n besh servis bor, `services/` ostida uchta katalog:
`core-api`, `cv-service`, `nvr-sim`). Ikkinchisi — `core-api` ichida chiquvchi xabar
**outboxi** va uni haydaydigan uchta yangi cron job. Uchinchisi — case modeli va bosh
ekran ko'rsatkichi, ular sof `core-api` + frontend ishi.

Fazaning **eng muhim mexanik topilmasi**: nomuvofiqlik ikki xil sinfdan iborat va ular
bugungi sxemada **bir joyda yashamaydi**. «Ro'yxatga olinmagan savdo» —
`billing_anomalies` qatori (`kind='unassigned_occupied'`, `0020_billing_domain.py:623`).
«Band, lekin to'lovsiz» esa **qator emas** — u `daily_charges` dan `payments` ni ayirish
natijasi, ya'ni **hosila**, va uni anomaliya qatori qilib yozish D-06/D-13 taqiqlagan
«saqlangan hosila» sinfiga tushardi (to'lov ertaga kelsa qator yolg'onga aylanardi).
Shuning uchun `reconciliation_cases` **ikki mustaqil, o'zaro istisno qiluvchi kompozit FK**
oladi (`anomaly_id` XOR `charge_id`) va ikkalasi ham o'zgarmas jadvalga ishora qiladi —
`daily_charges` ham, `billing_anomalies` ham 6-fazada shartsiz trigger bilan qulflangan.

**Ikkinchi muhim topilma — talab to'qnashuvi.** RECON-06 kassirga «bugungi yig'im» ni
va'da qiladi; CASH-04/T-06-53/T-06-59 esa kassir smena yopishda **tizim summasini
ko'rmasligini** talab qiladi va `GET /payments/recent` aynan shu sababdan serverda
**qat'iy 5 qator** bilan cheklangan (`payment_repo.py:145`). Kassirning bosh ekraniga
bugungi yig'im **summasini** chiqarish o'sha butun mexanizmni bir qatorda bekor qiladi.
Yechim: kassir uchun ko'rsatkich — **yozilgan to'lovlar SONI**, summasi emas.

**Uchinchi topilma — webhook yo'li bugun yopiq.** Telegram webhook **HTTPS talab qiladi**
(rasmiy Bot API: «we will send an HTTPS POST request»; portlar 443/80/88/8443), bu repoda
esa TLS **umuman yo'q**: `ops/nginx/nginx.conf:8-9` ochiq yozadi — «TLS bu fazada YO'Q …
Let's Encrypt keyingi fazada certbot bilan qo'shiladi», `server { listen 80; }`. Ya'ni
webhook 8-fazaning ishini oldinga tortishni talab qiladi. **Long-polling tanlanadi.**

**Primary recommendation:** `bot-service` ni `cv-service` shabloni bo'yicha qur (o'z
`pyproject.toml`/`uv.lock`/`Dockerfile`/`observability.py`), uni **long-polling** bilan
bitta konteynerda yurit, core-api ga `/internal/bot/*` ostidagi **statik servis-token**
bilan bog'la; outboxni `core-api` da `notify.outbox_tick` taskiq vazifasi qilib yoz va
uni mavjud `AlertSender` ning **o'sha bitta metodi** orqali jo'nat — `chat_id` ni
konstruktor qiymatidan **argumentga** ko'chirish yo'li bilan, ya'ni Telegram metodlari
yuzasi **kengaymaydi**.

---

## Architectural Responsibility Map

| Qobiliyat | Asosiy tier | Ikkilamchi tier | Sabab |
|-----------|-------------|-----------------|-------|
| Telegram update qabul qilish (`/start`, contact, tugma) | **bot-service** | — | Kiruvchi yuza; `aiogram` pinlari core-api'nikiga sig'maydi (D-08/2) |
| Telefon → vendor moslashtirish qarori | **API (core-api)** | bot-service (faqat uzatadi) | Reyestr va RLS core-api da; bot «bu Telegram ID» deydi, xolos (D-10) |
| Qoldiq/qarz arifmetikasi | **API (core-api)** | — | `vendor_outstanding()` yagona manba (D-06) |
| Chiquvchi xabar navbati (outbox) | **API/worker (core-api)** | — | D-08: jo'natish core-api da, taqiqlar shu yerda o'lchanadi |
| Telegram'ga HTTP `sendMessage` | **worker (core-api)** | — | `AlertSender` mavjud; ikkinchi jo'natuvchi ikki taqiqni ikkilantirardi (D-23) |
| Kvitansiya tetigi | **API (core-api)** — `POST /payments` tranzaksiyasi | worker (jo'natish) | D-21: idempotentlik to'lov qatori bilan **bir** tranzaksiyada |
| Kechki/ertalabki xabar jadvali | **scheduler (core-api)** | worker | Mavjud `LabelScheduleSource` reyestri (`worker.py:558`) |
| Case yaratish (yangi) | **worker (core-api) cron** | — | `billing_close` dan keyin; idempotentlik qisman UNIQUE indeks bilan |
| Case holatini o'zgartirish | **API (core-api)** | Frontend | RBAC + audit qatori (D-14) |
| Nomuvofiqlik hisoboti yuzasi | **Frontend** | API | Dalil **havola** bo'lib boradi (D-03) |
| Bosh ekran ko'rsatkichi | **API (core-api)** | Frontend | Qaysi son qaysi rolga — **serverda** (D-28) |
| Bot matnlari (3 locale) | **bot-service** (Babel `.po/.mo`) | Frontend (glossariy jufti) | D-30: atamalar yagona, katalog alohida |
| Dalil-kadr baytlari | **⛔ HECH QAYSI TIER Telegramga bermaydi** | — | D-03; mavjud yagona proxy `GET /snapshots/{id}/image` (T-06-81) |

---

## Discretion qarorlari (CONTEXT.md «Claude's Discretion» — har biriga BITTA javob)

### DQ-1 — Webhook emas, **LONG-POLLING**

**Qaror:** `bot-service` `aiogram` ning `start_polling()` i bilan ishlaydi. Webhook
**qurilmaydi**.

**Dalil (taxmin emas):**

1. Telegram Bot API `setWebhook` **HTTPS talab qiladi** va qo'llab-quvvatlanadigan portlar
   — 443, 80, 88, 8443 [CITED: core.telegram.org/bots/api#setwebhook].
2. Bu repoda TLS **yo'q**: `ops/nginx/nginx.conf:8-9` — «TLS bu fazada YO'Q (RESEARCH A7)
   — dev/pilot uchun HTTP. Let's Encrypt keyingi fazada certbot `--webroot` bilan
   qo'shiladi»; `nginx.conf:68-69` — `server { listen 80; }`. Sertifikat 8-faza (go-live)
   ishi.
3. `getUpdates` va webhook **o'zaro istisno**: «This method will not work if an outgoing
   webhook is set up» [CITED: core.telegram.org/bots/api#getupdates]. Ya'ni ikkalasini
   «ikkalasi ham bo'lsin» deb qurish **mumkin emas** — tanlov majburiy.
4. Long-polling kiruvchi port, ommaviy URL va `secret_token` boshqaruvini **umuman
   talab qilmaydi**, ya'ni u loyihaning «NVR faqat VPN, tashqi yuza minimal» xavfsizlik
   holatiga mos.

**Operatsion oqibatlari — ochiq yoziladi va rejaga banddir:**

| Oqibat | Nima qilinadi |
|---|---|
| ⛔ **Bir tokenga AYNAN BITTA poller.** Ikkinchi jarayon `409 Conflict: terminated by other getUpdates request` beradi (aiogram: `TelegramConflictError`) | `compose.yaml` da `bot-service` **bitta** konteyner; `deploy.replicas` **yozilmaydi**; jurnalga «bitta nusxa» sharti izoh sifatida yoziladi |
| Lokal ishlab chiqishda o'sha token bilan ikkinchi nusxa ishga tushsa prod'dagi update'larni **o'g'irlaydi** | `.env.example` ga alohida `dev` bot tokeni bandi + `README` da ogohlantirish |
| Token ilgari webhook bilan ishlatilgan bo'lsa `getUpdates` **409** beradi | Ishga tushishda bir marta `delete_webhook(drop_pending_updates=False)` chaqiriladi (aiogram `start_polling` buni `drop_pending_updates` bilan qo'llab-quvvatlaydi) |
| Chiquvchi ulanish TLS bilan Telegram'ga boradi (long-poll) | Tarmoq chiquvchi 443 ni talab qiladi; `bot-service` **VPN tarmog'iga ulanmaydi** (u NVR ko'rmaydi) |
| Webhook'ga o'tish kelajakda | 8-fazada TLS qurilgach **sozlama** o'zgarishi bo'ladi (aiogram ikkalasini ham bir xil `Dispatcher` bilan yuritadi), qayta loyihalash emas |

### DQ-2 — Outbox jo'natuvchisi: **`taskiq` vazifasi**, alohida sikl EMAS

**Qaror:** `notify.outbox_tick`, cron `* * * * *` (`TICK_CRON` bilan bir xil literal
**ishlatilmaydi** — quyidagi ogohlantirishga qarang), mavjud `worker` konteynerida.

**Dalil:** `worker.py` modul docstringi (18–24, 59–75-qatorlar) qaror qoidasini
allaqachon yozgan: «**ikki mexanizm bir vaqtda saqlanmaydi**: ikkitasi turganda "bu job
qaysi yo'ldan ketdi?" savoli har nosozlikda qaytadan so'ralardi». Alohida sikl to'rtinchi
jarayon (yoki beshinchi konteyner) va **ikkinchi** orkestratsiya mexanizmi bo'lardi.
`capture.tick` (`worker.py:830`) aynan shu shaklda ishlaydi: planer **holatsiz** tik
beradi, ijara/idempotentlik/yo'qlik yozuvi Postgres'da. Outbox ham xuddi shu shaklga
tushadi — `SELECT … FOR UPDATE SKIP LOCKED` + `lease_until`, ya'ni `capture_repo` ning
o'lchangan naqshi qayta ishlatiladi.

⚠ **`TICK_CRON` literali qayta ishlatilmaydi.** `worker.py:334-339` ochiq yozadi: «SATR
AYNAN BITTA MARTA UCHRAYDI (dekoratorda) va buni matn darvozasi sanaydi». Yangi daqiqalik
job **o'z konstantasi** bilan yoziladi (masalan `OUTBOX_TICK_CRON`) — aks holda mavjud
darvoza qizaradi.

### DQ-3 — Retry backoff: **eksponensial, tepasi cheklangan, `retry_after` ustun**

```
attempt 1 -> darhol
attempt 2 -> +30 s      attempt 3 -> +2 daq
attempt 4 -> +8 daq     attempt 5 -> +32 daq       (max 5 urinish)
```

Formula: `next_attempt_at = now + min(30s * 4**(attempt-1), 1 soat)`.

⛔ **`TelegramRetryAfter.retry_after` FORMULADAN USTUN** — Telegram `429` bilan aniq
soniya qaytarganda o'sha qiymat ishlatiladi (`retry_after` atributi aiogram 3.x da
mavjud [VERIFIED: aiogram/exceptions.py]). Formulaga tayanish chegarani **qattiqroq**
urardi va bu `alerts.py:162-166` da yozilgan «`429` ga retry qilish holatni
yomonlashtiradi» qoidasining aynan takrori.

⛔ **`403` (blocked) va `400` (bad request) qayta urinilmaydi** — ikkalasi ham
konfiguratsiya/holat nosozligi. `403` → `blocked` (D-22), `400` → `failed`.

**Nega 5 urinish:** 5-urinishgacha jami kutish ~42 daqiqa. Kvitansiya (D-18) bir soatdan
ko'p kechiksa u allaqachon «zudlik» emas va uni cheksiz qayta urinish navbatni to'ldiradi.
`alerts.py:155-166` dagi «2 urinish × 5 s» arifmetikasi bilan bir xil uslub: **son
tanlanmaydi, hisoblanadi**.

### DQ-4 — Case ro'yxatining sahifalash usuli: **kun kesimi + keyset**

`GET /reconciliation/cases?day=YYYY-MM-DD&status=…&cursor=…` — javob envelopeи
`ChargeListResponse` naqshi bilan **bir xil shaklda**: `{day, rows, new_count,
in_review_count, justified_count, unjustified_count}` (`schemas.py:3101`). Tartib
`(created_at DESC, id DESC)`, sahifa 50 (`market-queries.ts:97` bilan bir xil son).

**Sabab:** `deferred-items.md` 2- va 4-bandlari **aynan shu sinfdagi** nosozlikni
ko'rsatgan — klient envelope'i serverning envelope'idan orqada qolib, `z.strictObject`
ostida **parse paytida** yiqilgan. Yangi yuza mavjud shaklni takrorlasa, klient sxemasi
birinchi kundan mos bo'ladi. `offset` **ishlatilmaydi**: case ro'yxati kun davomida
o'sadi va offset sahifalash takroriy/tushib qolgan qatorlar beradi.

### DQ-5 — Kompozit FK shakli: **ikki mustaqil FK + `CHECK` (XOR) + ikki qisman UNIQUE indeks**

```sql
market_id   uuid NOT NULL
anomaly_id  uuid NULL
charge_id   uuid NULL

CONSTRAINT fk_reconciliation_cases_anomaly
  FOREIGN KEY (market_id, anomaly_id)
  REFERENCES billing_anomalies (market_id, id)          -- uq_billing_anomalies_market_id_id ✓
CONSTRAINT fk_reconciliation_cases_charge
  FOREIGN KEY (market_id, charge_id)
  REFERENCES daily_charges (market_id, id)              -- uq_daily_charges_market_id_id ✓

CONSTRAINT subject_is_exclusive
  CHECK ((anomaly_id IS NULL) <> (charge_id IS NULL))

CREATE UNIQUE INDEX uq_reconciliation_cases_anomaly
  ON reconciliation_cases (market_id, anomaly_id) WHERE anomaly_id IS NOT NULL;
CREATE UNIQUE INDEX uq_reconciliation_cases_charge
  ON reconciliation_cases (market_id, charge_id)  WHERE charge_id  IS NOT NULL;
```

**Ikkala nishon UNIQUE cheklovi ALLAQACHON MAVJUD** — yangi migratsiya ularni yaratmaydi:
`uq_billing_anomalies_market_id_id` (`0020_billing_domain.py:662`) va
`uq_daily_charges_market_id_id` (`0020_billing_domain.py:414`) [VERIFIED: migratsiya
manbasi]. Qisman UNIQUE indeks naqshi loyihada allaqachon ishlatilgan
(`uq_alert_events_market_id_alert_key_open`, `SHIFT_OPEN_INDEX`).

⛔ **`subject_kind` yopiq `StrEnum` ustuni ham qo'shiladi** (`anomaly` / `occupied_unpaid`)
— `NULL` tekshirish orqali sinfni aniqlash hisobotni «qaysi ustun bo'sh?» mantig'iga
bog'lardi; yopiq diskriminator `GROUP BY` ni bir ustunga tushiradi va 6-fazaning
«yopiq to'plam + `other` yo'q» naqshini davom ettiradi.

### DQ-6 — Nomlar

| Obyekt | Nom | Sabab |
|---|---|---|
| Case jadvali | `reconciliation_cases` | CONTEXT.md da nomlangan |
| Case holati enumi | `ReconciliationCaseStatus` — `new` / `in_review` / `justified` / `unjustified` | ⚠ **Qiymatlar INGLIZCHA**, ko'rsatiladigan matn i18n kaliti. Loyihaning barcha enumlari shunday (`PaymentKind`, `AnomalyKind`); D-12 dagi o'zbekcha nomlar — **ma'no**, qiymat emas |
| Case audit qatori | `reconciliation_case_events` | `charge_adjustments` naqshi: o'zgarish **yangi qator** |
| Outbox | `notification_outbox` | `outbox` juda umumiy; prefiks domenni aytadi |
| Bog'lanish | `vendor_telegram_bindings` | CONTEXT.md da nomlangan |
| Bozor kesimidagi sozlama | `market_notification_settings` | 1:1 tenant jadvali; `market_profile` ga ustun qo'shish uning audit diffini bildirishnoma sozlamalari bilan aralashtirardi |

---

## Standard Stack

### Yangi (faqat `bot-service` ga)

| Kutubxona | Versiya | Vazifasi | Nega standart |
|-----------|---------|----------|---------------|
| `aiogram[fast,redis,i18n]` | **3.30.0** (2026-07-17) | Telegram Bot framework | `CLAUDE.md` da qat'iylashtirilgan; MIT; asyncio-native; FSM va i18n ichida [VERIFIED: PyPI metadata 2026-08-11] |
| `redis[hiredis]` | **7.4.1** (2026-06-05) | aiogram `RedisStorage` (FSM) | ⛔ aiogram 3.30 `redis[hiredis]<8,>=6.2.0` talab qiladi; 7.4.1 — o'sha oynadagi **eng yangi** [VERIFIED: PyPI] |
| `pydantic` | **2.13.4** | aiogram ichki modellari + `Settings` | ⛔ aiogram `pydantic<2.14,>=2.4.1`; core-api'dagi pin bilan **bir xil qiymat**, lekin **alohida lockfaylda** |
| `Babel` | **2.18.0** (2026-02-01) | `aiogram[i18n]` katalogi (CLDR `uz`, `uz_Cyrl`, `uz_Latn`, `ru`) | BSD-3-Clause; `aiogram[i18n]` `Babel<3,>=2.13.0` talab qiladi [VERIFIED: PyPI] |
| `aiodns` | **4.0.4** | `aiogram[fast]` ekstrasi | MIT; DNS ni asyncio ga chiqaradi |
| `uvloop` | **0.22.1** | `aiogram[fast]` ekstrasi | ⚠ Python 3.13 uchun aiogram `uvloop>=0.21.0` talab qiladi; cp313 `manylinux_2_28_x86_64` g'ildiragi **bor** [VERIFIED: PyPI]. ⛔ Windows xostda manbadan quriladi va yiqiladi — bu **faqat xost artefakti**, konteyner `python:3.13-slim-trixie` (Debian/glibc) |
| `httpx` | **0.28.1** | core-api ichki API'siga chaqiruv | Loyihada allaqachon standart klient; `respx` bilan testda tutiladi |
| `structlog` | **26.1.0** | Jurnal (JSON) | Uchala servisda bir xil |
| `sentry-sdk[fastapi]` | **2.66.1** | ⛔ **MAJBURIY** — pastdagi darvoza bandiga qarang | `tests/unit/test_sentry_processes.py` `SENTRY_DSN` beriladigan **har** jarayondan `init_sentry(` ni talab qiladi |
| `pydantic-settings` | **2.14.2** | `Settings` | `core-api`/`cv-service` bilan bir xil |
| `tzdata` | **2026.3** | `ZoneInfo("Asia/Tashkent")` slim image'da | Usiz `ZoneInfo` yiqiladi (`cv-service/pyproject.toml:62-63`) |

⛔ **`bot-service` ga QO'SHILMAYDIGAN paketlar va sabab:**

| Paket | Nega yo'q |
|---|---|
| `sqlalchemy`, `asyncpg` | D-08/1 — **ikkinchi RLS yuzasi ochilmaydi**. Bot bazani **ko'rmaydi** |
| `sbozor-core` | ⚠ Vasvasa katta (enumlar, pul turi). Lekin u `models/` orqali SQLAlchemy'ni **tortadi** va yuqoridagi taqiqni bilvosita buzadi. Bot ga kerak bo'lgan yagona narsa — pul formatlash va enum QIYMATLARI; ular ichki API javobidan **matn/son** bo'lib keladi |
| `taskiq`, `taskiq-redis` | Bot job bajarmaydi (D-08: faqat kiruvchi) |
| `phonenumbers` | ⛔ E.164 normalizatsiyasi **core-api da** (D-25): ikki joyda normallashtirish ikki xil natija bergan kunda bog'lanish jimgina buzilardi |

### `core-api` ga qo'shiladigan — **HECH NARSA**

Outbox, case, `/me/headline` va uchala job mavjud bog'liqliklar bilan yoziladi:
`sqlalchemy`, `httpx` (`AlertSender` orqali), `taskiq`, `phonenumbers` (allaqachon
`pyproject.toml:18`), `structlog`. ⛔ **Yangi paket qo'shilishi rejaning `pyproject.toml`
o'zgarishi bo'lib ko'rinsa — bu dizayn xatosi belgisidir.**

### Alternatives Considered

| O'rniga | Ishlatish mumkin edi | Nega yo'q |
|---|---|---|
| long-polling | webhook + `aiohttp` server | TLS yo'q (DQ-1); 8-faza ishini oldinga tortardi |
| `AlertSender` ni kengaytirish | Yangi `OutboxSender` sinfi | D-23 va `alerts.py` docstringi: ikkinchi jo'natuvchi ikki taqiqni **ikkilantirardi**; darvozalar bir joyda qolishi kerak |
| `taskiq` vazifasi | `asyncio` while-loop `bot-service` ichida | D-08 buzilardi (jo'natish botga ko'chardi) + ikkinchi orkestratsiya mexanizmi |
| `market_notification_settings` | `market_profile` ga ustun | Alohida jadval audit diffini toza saqlaydi; ⚠ narxi — bitta qo'shimcha `JOIN` va wizardda yana bir standart qator |
| `aiogram[i18n]` (Babel `.po`) | Bot matnlarini JSON dan o'qish (frontend fayllarini qayta ishlatish) | D-30 katalogni bot-service da deb belgilagan; `.po` gettext ko'plik qoidalarini (`uz` da 2 shakl, `ru` da 3) **to'g'ri** beradi, JSON esa bermaydi |

**Installation:**

```bash
# bot-service (YANGI, o'z lockfayli bilan — D-09)
cd services/bot-service
uv add "aiogram[fast,redis,i18n]==3.30.0" "redis[hiredis]==7.4.1" "pydantic==2.13.4" \
       "pydantic-settings==2.14.2" "httpx==0.28.1" "structlog==26.1.0" \
       "sentry-sdk[fastapi]==2.66.1" "tzdata==2026.3"
# ⛔ core-api ga: hech narsa
```

---

## Package Legitimacy Audit

Protokol bajarildi (2026-08-11): `pip install slopcheck` → `slopcheck 0.6.1`;
`slopcheck install -e pypi aiogram Babel aiodns uvloop redis phonenumbers`.

| Paket | Registry | Versiya | Chiqqan | Litsenziya | slopcheck | Holat |
|-------|----------|---------|---------|-----------|-----------|-------|
| `aiogram` | PyPI | 3.30.0 | 2026-07-17 | MIT | **[OK]** | Tasdiqlandi |
| `Babel` | PyPI | 2.18.0 | 2026-02-01 | BSD-3-Clause | **[OK]** | Tasdiqlandi (`aiogram[i18n]` tranzitiv) |
| `aiodns` | PyPI | 4.0.4 | 2026-05-20 | MIT | **[OK]** | Tasdiqlandi (`aiogram[fast]` tranzitiv) |
| `uvloop` | PyPI | 0.22.1 | 2025-10-16 | MIT | **[OK]** | Tasdiqlandi (`aiogram[fast]` tranzitiv) |
| `redis` | PyPI | 7.4.1 (pin) | 2026-06-05 | MIT | **[OK]** | Tasdiqlandi |
| `phonenumbers` | PyPI | 9.0.35 (mavjud pin) | — | Apache-2.0 | **[OK]** | ⚠ **Yangi emas** — `core-api/pyproject.toml:18` da allaqachon bor |

**`[SLOP]` verdikti tufayli olib tashlangan paketlar:** yo'q.
**`[SUS]` deb belgilangan paketlar:** yo'q.

⚠ **Xost artefakti, paket nuqsoni EMAS:** `uvloop` Windows xostda manbadan qurilishga
urinib yiqildi (Windows uchun g'ildirak yo'q). Konteyner bazasi `python:3.13-slim-trixie`
va PyPI'da `uvloop-0.22.1-cp313-cp313-manylinux…_2_28_x86_64.whl` **mavjud** — ya'ni
`uv sync` konteynerda g'ildirakdan o'rnatadi.

---

## Architecture Patterns

### System Architecture Diagram

```
   Telegram serverlari  (⛔ DATA-REZIDENTLIK CHEGARASIDAN TASHQARIDA — D-01)
        ▲  chiquvchi HTTPS                     │ long-poll (getUpdates)
        │  sendMessage                         ▼
 ┌──────┴──────────────────────────┐   ┌───────────────────────────────┐
 │  core-api / worker              │   │  bot-service  (YANGI, 3-SERVIS)│
 │  ─────────────────────────────  │   │  ─────────────────────────────│
 │  AlertSender.send_message(      │   │  Dispatcher                    │
 │      text, chat_id=…)           │   │   ├─ /start          → matn    │
 │   └─ YAGONA Telegram metodi     │   │   ├─ contact         → BOT-01  │
 │      (TELEGRAM_SEND_METHOD)     │   │   ├─ «Qarzim»        → BOT-02  │
 │   └─ ⛔ rasm metodi YO'Q (D-03) │   │   └─ «To'lovlarim»   → BOT-02  │
 │                                 │   │  RedisStorage (FSM) → Valkey   │
 │  notify.outbox_tick  (1 daq)    │   │  ⛔ DB ulanishi YO'Q (D-08/1)  │
 │   └─ SKIP LOCKED + lease        │   └───────────┬───────────────────┘
 │                                 │               │ httpx + Bearer
 │  ┌────────────────────────────┐ │               │ (servis-servis token, D-10)
 │  │ notification_outbox        │◀┼───────────────┘
 │  │ pending→sent→delivered     │ │        POST /internal/bot/resolve
 │  │        |failed|blocked     │ │        GET  /internal/bot/vendor/{id}/summary
 │  │ UNIQUE(market_id,dedupe)   │ │        GET  /internal/bot/vendor/{id}/payments
 │  └──────────▲─────────────────┘ │
 │             │ INSERT (bir tranzaksiyada)
 │  ┌──────────┴──────────────┐    │
 │  │ POST /payments (CASH-05)│    │      ┌──────────────────────────────┐
 │  └─────────────────────────┘    │      │ Frontend (Next 16)            │
 │                                 │      │  /dashboard  → GET /me/headline│
 │  cron reyestri (worker.py)      │      │  /reconciliation → case yuzasi│
 │   03:40 occupancy.day_close     │      │  ⛔ alertda <img> yo'q (G-3)  │
 │   04:10 billing.close  ────┐    │      └──────────────▲───────────────┘
 │   04:25 recon.open  ◀──────┘    │                     │ /api/ (nginx)
 │   08:00 notify.digest_morning   │                     │
 │   20:45 notify.digest_evening   │◀────────────────────┘
 │   09:00 notify.overdue (BOT-03) │
 └───────────┬─────────────────────┘
             │  faqat O'QISH
   ┌─────────▼──────────────────────────────────────────────┐
   │ PostgreSQL 18 — RLS ENABLE+FORCE, kompozit FK          │
   │  daily_charges (o'zgarmas) ◀── reconciliation_cases ──▶ billing_anomalies (o'zgarmas)
   │  payments  vendors  vendor_telegram_bindings           │
   │  market_notification_settings   notification_outbox    │
   └────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
services/bot-service/
├── Dockerfile                 # cv-service Dockerfile ning aynan shakli (base/dev/runtime)
├── pyproject.toml             # D-09: o'z pinlari
├── uv.lock                    # D-09: alohida lockfayl
├── README.md                  # nega alohida bog'liqlik to'plami (cv-service/README.md naqshi)
├── app/
│   ├── __init__.py
│   ├── main.py                # ⛔ KIRISH NUQTASI: init_sentry() SHU YERDA
│   ├── settings.py            # BOT_TOKEN(SecretStr), CORE_API_URL, BOT_SERVICE_TOKEN(SecretStr)
│   ├── observability.py       # init_sentry — cv-service/app/observability.py jufti
│   ├── core_client.py         # httpx qobig'i: Bearer, timeout, xato TURI (D-04)
│   ├── handlers/
│   │   ├── start.py           # /start + contact so'rash klaviaturasi
│   │   ├── binding.py         # BOT-01: contact qabul qilish
│   │   └── vendor.py          # BOT-02: qoldiq va to'lov tarixi
│   └── locales/               # Babel katalogi (D-30)
│       ├── uz_Latn/LC_MESSAGES/bot.po
│       ├── uz_Cyrl/LC_MESSAGES/bot.po
│       └── ru/LC_MESSAGES/bot.po
└── tests/
    ├── unit/test_sentry_entrypoints.py   # cv-service dagi jufti
    ├── unit/test_handlers.py             # aiogram MockedBot bilan
    └── unit/test_locale_parity.py        # D-31

services/core-api/app/
├── jobs/
│   ├── outbox.py              # notify.outbox_tick (DQ-2)
│   ├── reconciliation.py      # recon.open (case yaratish)
│   └── notifications.py       # digest_morning / digest_evening / overdue_reminder
├── repositories/
│   ├── outbox_repo.py         # SKIP LOCKED + lease + append-only holat
│   ├── reconciliation_repo.py # case ro'yxati, hit-rate (hosila SQL)
│   └── binding_repo.py        # vendor_telegram_bindings
└── api/
    ├── internal/bot.py        # ⛔ include_in_schema=False, servis-token
    └── v1/reconciliation.py   # case yuzasi (RBAC + audit)
    # + me.py ga `GET /me/headline`
```

### Pattern 1: `AlertSender` ni **kengaytirish**, takrorlamaslik (D-23, D-18)

**Nima:** `chat_id` konstruktordan **argumentga** ko'chadi; metodlar soni **o'zgarmaydi**.

**Nega:** `alerts.py:217-233` docstringi «AYNAN BITTA amal» deydi va
`tests/integration/test_alerting.py` bu yuzani `dir()` bilan sanaydi. Yangi **metod**
qo'shish darvozani siljitardi; yangi **kalit argument** esa metodlar to'plamini
tegilmagan qoldiradi va `TELEGRAM_SEND_METHOD` hamon **yagona** Bot API metodi bo'lib
qoladi — ya'ni 1-taqiq strukturaviy jihatdan **kuchsizlanmaydi**.

```python
# services/core-api/app/services/alerts.py  (o'zgarish MINIMAL)
async def send_message(self, text: str, *, chat_id: str | None = None) -> bool:
    """...ISTISNO KO'TARMAYDI (3-taqiq).

    ⛔ `chat_id` ARGUMENT: alert supurgisi ops chatiga, outbox esa
       sotuvchining shaxsiy chatiga yozadi. IKKINCHI JO'NATUVCHI SINF
       yozilmaydi — u ikki taqiqni (rasm yo'q, token matnga tushmaydi)
       IKKILANTIRARDI.
    ⛔ `chat_id` JURNALGA YOZILMAYDI: u Telegram foydalanuvchi
       identifikatori, ya'ni SHAXSIY ma'lumot (D-01).
    """
    target = chat_id or self._chat_id
    if self._client is None or not target:
        return False
    ...
```

⚠ **`alerts_enabled` bilan ziddiyat va uning yechimi.** `settings.py:417-428`
`alerts_enabled = bool(token and chat_id)`. Sotuvchiga xabar yuborish uchun **ops chat
ID kerak emas** — faqat token. Ikki bayroq qo'shish `settings.py` ochiq ogohlantirgan
«uchinchi holat» ni qaytarardi. **Yechim: bayroq qo'shilmaydi, chegara CHAQIRUV JOYIDA
qo'yiladi** — `_open_worker_resources` jo'natuvchini `enabled=bool(token)` bilan quradi
va `alert_sweep_task` ni `settings.alerts_enabled` shartiga o'raydi. Shunda «yoqilgan,
lekin manzilsiz» holati **har ikkala** yo'lda ham imkonsiz bo'lib qoladi.

### Pattern 2: Outbox — append-only holat mashinasi + ijara (D-20, D-21, DQ-2)

```
   POST /payments  ──(BIR TRANZAKSIYA)──▶  payments qatori
                                      └─▶  notification_outbox qatori
                                           status='pending'
                                           dedupe_key = f"receipt:{payment_id}"
                                           UNIQUE(market_id, dedupe_key)  ⛔ D-21

   notify.outbox_tick (har daqiqa)
     ├ SELECT ... WHERE status IN ('pending')
     │        AND next_attempt_at <= now()
     │        AND (quiet-hours darvozasi VEYA never_suppressed)
     │   ORDER BY created_at  FOR UPDATE SKIP LOCKED  LIMIT :batch
     ├ UPDATE status='sent', lease_until=now()+interval, attempt_count+1
     ├ await sender.send_message(text, chat_id=...)
     └ natija:
         200            -> status='delivered', provider_message_id=<message_id>
         403            -> status='blocked'   ⛔ QAYTA URINILMAYDI (D-22)
         429            -> status='pending', next_attempt_at=now()+retry_after
         5xx / tarmoq   -> status='pending', next_attempt_at=DQ-3 formulasi
         attempt >= 5   -> status='failed'
```

⛔ **`text` OUTBOX QATORIDA SAQLANMAYDI, U QURILADI.** Qatorda `kind`
(yopiq `StrEnum`) va `payload` (⛔ **allowlist bilan cheklangan** kalitlar — `alerting.py`
ning `ALERT_DETAIL_KEYS` naqshi) bo'ladi; matn jo'natish paytida shu ikkisidan quriladi.
Tayyor matnni saqlash sotuvchining ismi/summasini bazaga, u yerdan zaxiraga va tashqi
bucketga chiqarardi — `_detail()` (`alerting.py:435-445`) aynan shu sababdan yozilgan.

⛔ **`chat_id` OUTBOX QATORIDA SAQLANMAYDI** — u `vendor_telegram_bindings` dan `JOIN`
bilan olinadi. Sabab D-26(c): qayta ulanish eski bog'lanishni bekor qiladi, ya'ni
navbatda turgan xabar **eski** chatga ketmasligi kerak.

### Pattern 3: Ikki xabar, ikki manba — va farq **matnda aytiladi** (D-15/D-16)

| Vaqt | Job | Manba | Matnda |
|------|-----|-------|--------|
| **08:00** | `notify.digest_morning` | `daily_charges` + `payments` (kechagi kun, **yozilgan**) | «kecha **yozilgan**: …» |
| **20:45** | `notify.digest_evening` | `pending_projection(as_of=business_today())` | «bugun **kutilayotgan**: …» |

⛔ **Ikki son bir xil bo'lmasligi — NUQSON EMAS, DIZAYN** (CONTEXT.md «Specific Ideas»).
Matn buni **ochiq aytadi**, aks holda direktor ikki raqamni ko'rib tizimga ishonchini
yo'qotadi. Har ikki job **argument sifatida kun oladi** (`daily_digest_task` naqshi,
`worker.py:885-893`) — «qaysi kun?» savoli testda **bitta qiymatga** aylanadi.

⛔ **`pending_projection()` IKKINCHI MARTA YOZILMAYDI.** `billing_repo.py:1312` yagona
implementatsiya; kechki job unga `as_of=business_today()` beradi, kassir ekrani ham o'sha
funksiyani chaqiradi. Farq testda `==` bilan o'lchanadi (6-faza G-13/G-14 naqshi).

### Pattern 4: Nomuvofiqlik **ikki SINF** va ular bir jadvalga tushmaydi (RECON-01)

| Sinf | Manba | O'zgarmasmi | Dalil yo'li |
|------|-------|-------------|-------------|
| **A — «band, lekin to'lovsiz»** | `daily_charges` − `payments` (**hosila**) | Hisob o'zgarmas, «to'lansimi» esa **o'zgaruvchan** | `charge_evidence.snapshot_id` → `GET /snapshots/{id}/image` |
| **B — «ro'yxatga olinmagan savdo»** | `billing_anomalies(kind='unassigned_occupied')` | Qator **o'zgarmas** | `billing_anomalies.snapshot_id` → o'sha proxy |

⛔ **SINF A UCHUN TO'RTINCHI `AnomalyKind` QO'SHILMAYDI.** Sabab mexanik: `billing_close`
04:10 da ishlaydi, o'sha kunning to'lovlari esa hali kelmagan. «To'lanmagan» ni o'sha
paytda qator qilib yozish ertaga to'lov kelganda **yolg'onga** aylanadigan saqlangan
hosila bo'lardi — D-06/D-13 aynan shu sinfni taqiqlaydi. Bundan tashqari `AnomalyKind`
to'plami 6-fazada `ANOMALY_KIND_CHECK` bilan bazada qulflangan va uning yopiqligi
o'lchanadi.

⛔ **`no_coverage_stall` GA CASE OCHILMAYDI.** U kamera qamrovi nuqsoni, tushum
nomuvofiqligi emas; `06-UI-SPEC.md` §11.4 u uchun dalil affordansini **umuman
chizmaydi**. Uni case navbatiga qo'shish navbatni har kuni ko'r nuqtalar bilan to'ldirardi.

### Pattern 5: Case qachon TUG'ILADI (RECON-02)

`recon.open` cron — **04:25 Asia/Tashkent**, `billing.close` (04:10) dan keyin:

```
sinf B: har YANGI billing_anomalies qatori (kind IN ('unassigned_occupied',
        'closed_day_occupied'))                    -> case(status='new')
sinf A: daily_charges qatori TO'LANMAGAN va
        service_date <= today - overdue_days       -> case(status='new')
```

⛔ **Sinf A uchun kechikish chegarasi MAJBURIY.** Chegarasiz har ertalab **har** hisob
uchun case ochilardi (to'lov kun davomida keladi) va navbat birinchi haftada shovqinga
aylanardi — `alerting.py` D-22 bo'limi bu nosozlik sinfini raqam bilan yozgan («75 ta
xabar olgan admin ertasi kuni bildirishnomani o'chiradi»). Chegara —
`market_notification_settings.overdue_days`, ya'ni **BOT-03 bilan AYNAN BIR knob**
(ikki sozlama ajralib ketardi).

**Idempotentlik:** DQ-5 dagi ikki qisman UNIQUE indeks. Job qayta yugursa `ON CONFLICT
DO NOTHING` — `billing_close` bilan aynan bir xil shakl.

### Pattern 6: Vendor bog'lanishi — `contact` ning **kimga tegishli** ekanini tekshirish (BOT-01, D-24)

```python
# services/bot-service/app/handlers/binding.py
@router.message(F.contact)
async def on_contact(message: Message) -> None:
    """⛔ UCH DARVOZA — VA UCHALASI HAM MAJBURIY.

    Telegram `Contact` obyektida `user_id` — IXTIYORIY maydon
    [CITED: core.telegram.org/bots/api#contact]. Ya'ni:

      1. `contact.user_id is None`  -> vCard/qo'lda qo'shilgan kontakt,
         Telegram uni HECH KIM bilan bog'lamagan;
      2. `contact.user_id != message.from_user.id` -> foydalanuvchi
         BOSHQA odamning kontaktini ulashdi (Telegram klientida bu
         oddiy amal) — bu D-24 aynan yopmoqchi bo'lgan yo'l;
      3. `message.chat.type != 'private'` -> guruhdan yuborilgan.

    Faqat `request_contact=True` tugmasi bosilganda `user_id` sender
    bilan TENG bo'ladi va aynan o'shanda raqam Telegram tomonidan
    KAFOLATLANADI.
    """
    contact = message.contact
    if (
        message.chat.type != ChatType.PRIVATE
        or contact.user_id is None
        or contact.user_id != message.from_user.id
    ):
        await message.answer(_("binding.neutral"))     # ⛔ SABAB AYTILMAYDI (D-26a)
        return
    await core.bind(telegram_user_id=contact.user_id, raw_phone=contact.phone_number)
```

⚠ **`phone_number` ba'zan `+` siz keladi** (klient/platformaga qarab). `phonenumbers`
`+998…` shaklini kutadi — `normalize_phone()` chaqirilishidan oldin `+` ni **core-api
tomonda** qo'shish kerak; bu `sbozor_core/phone.py:32` ning kirish shartnomasi va u
`DEFAULT_REGION` bilan ishlaydi.

### Pattern 7: `bot-service` → core-api ichki API (D-10) va **RLS chegarasi**

```
POST /internal/bot/resolve         {telegram_user_id, phone_e164}
GET  /internal/bot/vendor/summary  ?telegram_user_id=...
GET  /internal/bot/vendor/payments ?telegram_user_id=...&cursor=...
```

**Auth:** `Authorization: Bearer <BOT_SERVICE_TOKEN>`, `hmac.compare_digest` bilan
solishtiriladi. ⛔ **Foydalanuvchi sessiyasi tug'ilmaydi** (D-10): `Principal` yaratilmaydi,
JWT chiqarilmaydi, refresh cookie qo'yilmaydi.

**Ikkinchi qatlam — tarmoq.** `ops/nginx/nginx.conf` da faqat ikki `location` tashqariga
proxy qiladi: `/api/` → core-api va `/` → frontend. Ya'ni `/internal/bot/*` tashqi
so'rovda **frontendga** boradi va 404 oladi; `/internal/live-authz` esa `internal;` bilan
alohida yopilgan. Core-api porti xost portiga publish qilinmaydi.

⛔⛔ **RLS MUAMMOSI VA UNING YAGONA TO'G'RI YECHIMI.** Bot «bu Telegram ID» deydi, lekin
**qaysi bozor** ekanini bilmaydi. `vendor_telegram_bindings` esa tenant jadvali (RLS
`FORCE`), ya'ni kontekstsiz `SELECT` **0 qator** beradi (fail-closed, `deps.py`
docstringi). Uch yo'ldan ikkitasi yopiq:

| Yo'l | Verdikt |
|---|---|
| Yangi `SECURITY DEFINER` funksiya | ⛔ **TAQIQ** — `DEFINER_SURFACES = ()` bo'sh qolishi shart (`test_occupancy_domain_meta.py:75`, T-06-22) |
| Jadvalni RLS'siz global qilish | ⛔ **TAQIQ** — har yangi jadval `market_id` + RLS `ENABLE`+`FORCE` + tenant policy oladi |
| ✅ **`active_market_ids()` bo'ylab iteratsiya** | Mavjud, **yagona** RLS-chetlab o'tuvchi yuza (`retention.py:347`, 6-faza D-15/T-06-37). Har bozor uchun `_tenant_session` ochiladi va bog'lanish qidiriladi |

⛔ **Iteratsiya «samarasizlik» emas, MEXANIZM.** `vendors` da `uq_vendors_market_id_
phone_e164` (`market.py:566`) bor, ya'ni **bitta bozor ichida** telefon ≤1 sotuvchiga mos
keladi. Demak D-26(b) («bir nechta moslik») **faqat bozorlar ARO** yuz beradi va uni
aniqlashning yagona yo'li — barcha faol bozorlarni ko'rib chiqish. Ya'ni bitta tsikl
ikkala vazifani ham bajaradi.

⚠ **Karmana pilotida (bitta bozor) D-26(b) shoxi ERISHIB BO'LMAYDI.** Uning testi
`TwoMarketSeed` fixture'ini (`tests/fixtures/two_markets.py`) ishlatishi **shart** — aks
holda test yashil bo'lib turadi va hech nima o'lchamaydi.

### Pattern 8: `GET /me/headline` — huquq bo'yicha, rol nomi bo'yicha EMAS (D-28/D-29)

```python
# app/api/v1/me.py ga qo'shiladi
HEADLINE_ORDER: Final[tuple[tuple[Permission, str], ...]] = (
    (Permission.REPORT_VIEW,          "headline.revenue_today"),
    (Permission.OCCUPANCY_REVIEW,     "headline.review_queue"),
    (Permission.PAYMENT_CREATE,       "headline.receipts_written"),
)
"""⛔ TARTIB DETERMINLASHGAN VA U ROL NOMIGA TAYANMAYDI.

Foydalanuvchi bir necha rolga ega bo'lishi mumkin (`permissions_for()`
ro'yxat oladi). «Rol -> ko'rsatkich» xaritasi ikki rolli foydalanuvchida
IKKI javob berardi va tanlov tasodifiy bo'lardi. Birinchi mos huquq
g'olib; tartib SHU YERDA, bitta joyda yozilgan.
"""
```

Javob: `HeadlineResponse(metric: str, value: int)` — ⛔ **aynan ikki maydon**, ulardan
biri **son**, ikkinchisi **i18n kaliti**. `label` matn sifatida **serverdan
qaytmaydi** — tarjima klientda (`alerting.py:1003-1008` naqshi).

⛔⛔ **KASSIR UCHUN QIYMAT — SUMMA EMAS, SON.** `headline.receipts_written` =
`COUNT(*)` (bugun, o'sha kassir, `kind='payment'`). Sabab §«Pitfall 1» da.

---

## Don't Hand-Roll

| Muammo | Qurma | Buning o'rniga | Nega |
|--------|-------|----------------|------|
| Telegram HTTP klienti | Yangi `httpx` qobig'i | `AlertSender` (`alerts.py:217`) | Ikki taqiq (rasm yo'q, token matnga tushmaydi) u yerda **o'lchanadi**; nusxa ularni ikkilantiradi |
| Telegram update parsing | Xom JSON parseri | `aiogram` `Dispatcher` + `F` filtrlari | Bot API sxemasi katta va o'zgaradi; `aiogram` modellari `pydantic` bilan tekshiriladi |
| Telefon normalizatsiyasi | Regex / `str.replace` | `sbozor_core.phone.normalize_phone` | Loyihada allaqachon bor; ikki implementatsiya = ikki xil dublikat |
| Qoldiq arifmetikasi | Yangi SQL | `billing_repo.vendor_outstanding()` | D-06; G-14 tengligi shu funksiyaga bog'langan |
| «Qaysi kunning pattasi to'landi» | Yangi taqsimlash | `billing_repo.vendor_charge_allocation()` (`billing_repo.py:1123`) | ⛔ 6-faza uni **ataylab** iste'molchisiz qoldirgan («to'lov tarixi keyingi fazaniki») — **bu faza uning iste'molchisi** |
| Navbat/ijara/idempotentlik | Yangi qulf mexanizmi | `capture_repo` naqshi: `FOR UPDATE SKIP LOCKED` + `lease_until` | 4-fazada o'lchangan; taskiq'ning xotiradagi holatiga ishonib bo'lmaydi (`worker.py:59-68`) |
| Debounce/guruhlash | Yangi sanagich | `alert_events` qisman UNIQUE indeksi (`alerting.py:906-944`) | «Xotiradagi `dict`» deploy'dan omon qolmaydi — modul docstringining 1-qoidasi |
| Ko'plik shakllari (uz/ru) | `if n == 1` | gettext `.po` ko'plik qoidalari (Babel/CLDR) | Rus tilida **uchta** shakl (1 / 2–4 / 5+); qo'lda yozilgani birinchi «2 ta patta» da buziladi |
| Cron mintaqasi | UTC arifmetikasi | `cron_offset: "Asia/Tashkent"` (`worker.py:342-357`) | ⚠ taskiq cronni **UTC'da** baholaydi; `cron_offset` siz `"45 20 …"` Toshkentda **01:45** da ishlardi |
| Retry siyosati | `while True: sleep` | `tenacity` (mavjud) + `next_attempt_at` ustuni | Jarayon qayta ishga tushganda xotiradagi holat yo'qoladi |

**Kalit xulosa:** bu fazaning **hech bir** yangi mexanizmi noldan qurilmaydi — beshtasi
(`AlertSender`, `ALERT_META`, `SKIP LOCKED`+lease, `active_market_ids`, qisman UNIQUE
indeks) allaqachon o'lchangan holda bazada turibdi. Yangi kod ularni **bog'laydi**,
almashtirmaydi.

---

## Runtime State Inventory

> ⚠ Bu faza rename/refactor emas, lekin u **birinchi marta** loyiha nazorat qilmaydigan
> tashqi tizimda (Telegram) holat tug'diradi. Shuning uchun jadval **qisqartirilgan
> shaklda** to'ldirilgan.

| Toifa | Topilganlari | Kerakli amal |
|-------|--------------|--------------|
| **Tashqi xizmat holati (Telegram)** | ⛔ **Bot tokeni webhook holatini TASHIYDI.** Token ilgari (sinov paytida) `setWebhook` bilan ishlatilgan bo'lsa `getUpdates` `409 Conflict` beradi va bot **hech qanday** update olmaydi | Ishga tushishda `delete_webhook()`; jarayon **bitta** nusxada |
| **Tashqi xizmat holati (Telegram)** | Chat tarixi — yuborilgan xabar Telegram serverlarida **qoladi** (D-01). Bizning `notification_outbox` dagi `DELETE` uni **o'chirmaydi** | Xabar matnida shaxsiy maydon minimal; `payload` allowlist bilan cheklangan |
| **Saqlangan ma'lumot** | Yangi jadvallar hozircha **bo'sh** (yangi domen). `vendors.phone_e164` allaqachon E.164 da (MARKET-07) — migratsiya kerak emas | Migratsiya yo'q; faqat `CREATE TABLE` |
| **OS/registratsiya holati** | ⛔ **Cron jadvali `import` PAYTIDA olinadi** (`worker.py:475-486`): yangi vazifalar `scheduler` konteyneri qayta ishga tushirilmaguncha **ro'yxatga olinmaydi** va hech qanday xato chiqmaydi | Deploy bandi: `docker compose up -d --force-recreate scheduler worker` **va** yangi `bot-service`. Mexanik himoya — D-17 (yurak urishining yo'qligi) |
| **Sir va env** | Yangi ikkita: `TELEGRAM_BOT_TOKEN` (mavjud, alertlar uchun ishlatiladi — ⚠ **bir xil token ikki maqsadda**) va `BOT_SERVICE_TOKEN` (yangi) | ⚠ **Qaror kerak:** alert boti va sotuvchi boti **bir xil** botmi? Tavsiya: **HA, bitta bot** — ikkinchi token ikkinchi bot profili, ikkinchi nom va foydalanuvchida chalkashlik demakdir. `.env.example` yangilanadi |
| **Build artefaktlari** | `services/bot-service/uv.lock` — **yangi fayl**; `frontend` message fayllari `i18n:gen` bilan qayta generatsiya qilinadi | `npm --prefix frontend run i18n:gen` |

---

## Common Pitfalls

### Pitfall 1 — ⛔ RECON-06 va CASH-04 TO'QNASHADI (eng qimmat topilma)

**Nima noto'g'ri ketadi:** RECON-06 kassirga «bugungi yig'im» ni va'da qiladi. Agar
`/me/headline` kassirga bugun yig'ilgan **summani** qaytarsa, u smena yopishda o'sha
sonni deklaratsiya qiladi va variance **har doim nol** bo'ladi.

**Nega yuz beradi:** CASH-04 ning butun qiymati kassir tizim summasini **bilmasligiga**
tayanadi. 6-faza buni uch qatlamda qurgan: `ShiftCloseResponse` da `system_*` maydoni
**umuman e'lon qilinmagan** (T-06-59), `GET /payments/recent` serverda **qat'iy 5 qator**
(`payment_repo.py:145`, T-06-53), `variance_soum` faqat `REPORT_VIEW` ostida
(`shifts.py:126`). Bosh ekranga summa chiqarish uchalasini ham **bir qatorda** bekor
qiladi.

**Qanday oldini olish:** kassir uchun ko'rsatkich — **yozilgan kvitansiyalar SONI**
(`headline.receipts_written`). Bu foydali («bugun 47 ta patta»), «bitta son» shartiga mos
(D-29) va pul summasini bermaydi.

**Ogohlantiruvchi belgi:** `/me/headline` javobida `*_soum` bilan tugaydigan maydon
kassir sessiyasida qaytsa. Darvoza: `T-07-*` testi kassir sessiyasi bilan chaqirib,
`value` ni o'sha kunning haqiqiy summasi bilan **teng emasligini** tekshiradi.

### Pitfall 2 — «Delivered» ni Telegram **tasdiqlamaydi**

**Nima noto'g'ri ketadi:** BOT-04 «yetkazilganlik holati» talab qiladi va D-20 holat
mashinasida `delivered` bor. Buni «foydalanuvchi ko'rdi» deb o'qish oson.

**Nega yuz beradi:** Bot API `sendMessage` javobi — `Message` obyekti (`message_id`,
`date`). **Yetkazilganlik yoki o'qilganlik kvitansiyasi YO'Q**
[CITED: core.telegram.org/bots/api#sendmessage].

**Qanday oldini olish — semantika ochiq yoziladi:**

| Holat | Ma'nosi (⛔ aynan shu, kam ham, ko'p ham emas) |
|-------|---------------------------------------------|
| `pending` | Qator yozilgan, urinish qilinmagan |
| `sent` | Ijara olingan, HTTP so'rov **yo'lda** |
| `delivered` | Telegram **200** qaytardi va `message_id` berdi — ya'ni xabar chatga **joylandi** |
| `failed` | Urinishlar tugadi yoki qayta urinib bo'lmaydigan xato |
| `blocked` | `403` — foydalanuvchi botni bloklagan (D-22) |

⛔ **UI matni «o'qildi» yoki «ko'rildi» DEMAYDI.** Uchala locale'dagi kalit
«Telegram qabul qildi» ma'nosini berishi shart — aks holda nizoda (D-02) tizim
isbotlab bo'lmaydigan da'vo qilardi.

### Pitfall 3 — `test_sentry_processes.py` yangi servis qo'shilganda **YIQILADI** (bu ATAYIN)

**Nima noto'g'ri ketadi:** `compose.yaml` ga `bot-service` `SENTRY_DSN` bilan qo'shiladi
va butun to'plam qizaradi.

**Nega:** darvoza servis nomlarini **bilmaydi** — u `compose.yaml` dan hosila:
«`SENTRY_DSN` beriladigan HAR servis uchun kirish nuqtasi `command` dan chiqariladi va
o'sha obyektning hodisa reyestrida `init_sentry(` bo'lishi TALAB qilinadi»
(`test_sentry_processes.py:24-33`). «O'tkazib yuborish» shoxi **ataylab yo'q**.

**Qanday oldini olish:** `bot-service/app/main.py` **kirish nuqtasi** bo'lsin
(`modul:atribut` shakliga mos), `init_sentry(` chaqirsin va faylda `FOREIGN_HOOK_MARKERS`
dan biri bo'lsin (`lifespan=` yoki taskiq hodisasi). ⚠ aiogram `start_polling` bu
markerlarning **hech qaysisiga** mos kelmaydi — ya'ni darvozaning `FOREIGN_HOOK_MARKERS`
ro'yxati **kengaytiriladi** (masalan `dp.startup.register`) va bu o'zgarish rejada
**ochiq band** bo'lishi kerak, jimgina emas.

### Pitfall 4 — cron `cron_offset` siz yozilsa xabar tunda ketadi

**Nima noto'g'ri ketadi:** `"45 20 * * *"` — 20:45 emas, **01:45** da (Toshkent).

**Nega:** taskiq cronni **UTC'da** baholaydi (`worker.py:342-357` da o'lchangan).

**Qanday oldini olish:** uchala yangi jadval ham `cron_offset: MARKET_CRON_OFFSET` oladi.
Darvoza allaqachon bor: «`worker.py` da `cron_offset` literali kamida uch marta uchraydi».

### Pitfall 5 — `getUpdates` va webhook o'zaro istisno; ikkinchi poller update'larni o'g'irlaydi

**Nima noto'g'ri ketadi:** dev mashinada `bot-service` ishga tushiriladi va prod bot
**jim** bo'lib qoladi. Xato yo'q, jurnal toza, sotuvchilar javob olmaydi.

**Nega:** bir tokenga faqat bitta `getUpdates` oqimi; ikkinchisi `409 Conflict` oladi
yoki update'ni tortib oladi [CITED: core.telegram.org/bots/api#getupdates].

**Qanday oldini olish:** `TelegramConflictError` ni `CRITICAL` darajada logga + Sentry'ga
chiqarish va ⛔ **jim yutmaslik**. `.env.example` da alohida dev token bandi.

### Pitfall 6 — `notification_outbox` ga tayyor matn yozish

**Nima noto'g'ri ketadi:** «kvitansiya matni» ustuni sotuvchi ismi, rasta kodi va summani
bazaga yozadi; u yerdan `pg_dump` → restic → **tashqi bucket** ga chiqadi.

**Nega:** matn qulay — u bir marta quriladi va qayta urinishda o'zgarmaydi.

**Qanday oldini olish:** `payload` **allowlist** bilan cheklanadi (`_detail()` naqshi,
`alerting.py:435`) va matn jo'natish paytida quriladi. Ro'yxatdan tashqari kalit
`ValueError` — «kodda xato, ma'lumot xatosi emas».

### Pitfall 7 — Quiet hours kvitansiyani ushlab qoladi

**Nima noto'g'ri ketadi:** 20:00 dan keyin to'lagan sotuvchi kvitansiyani **ertasi kuni**
oladi.

**Nega:** quiet hours filtri `WHERE` bandiga qo'yiladi va `kind` bo'yicha istisno
unutiladi.

**Qanday oldini olish:** D-18 — `NEVER_SUPPRESSED` bayrog'i `ALERT_META` naqshida
**metadan hosila** bo'lsin, qo'lda takrorlangan ro'yxat emas
(`alerting.py:324-332`). So'rov: `AND (nk.never_suppressed OR <quiet-hours darvozasi>)`.

### Pitfall 8 — `contact` ni tekshirmasdan qabul qilish

**Nima noto'g'ri ketadi:** foydalanuvchi **boshqa odamning** kontaktini ulashadi va o'sha
sotuvchining qarzini ko'radi.

**Nega:** `Contact.user_id` — **ixtiyoriy** maydon
[CITED: core.telegram.org/bots/api#contact]; forward qilingan yoki qo'lda qo'shilgan
kontaktda u yo'q yoki boshqa.

**Qanday oldini olish:** Pattern 6 dagi uchala darvoza. Test: `user_id=None`,
`user_id != from_user.id` va guruh chatidan kelgan `contact` — **uch alohida** holat.

### Pitfall 9 — Chegara sinovi: `alerts_enabled` bo'sh chat ID bilan

**Nima noto'g'ri ketadi:** `TELEGRAM_CHAT_ID` bo'sh (ops chati sozlanmagan) → butun
jo'natuvchi o'chiq → **kvitansiya ham ketmaydi**, jimgina.

**Nega:** `settings.py:428` — `alerts_enabled = bool(token AND chat_id)`, va
`AlertSender` `enabled=False` da **klientni umuman ochmaydi**.

**Qanday oldini olish:** Pattern 1 ning oxirgi bandi — jo'natuvchi `enabled=bool(token)`
bilan quriladi, `alert_sweep` esa chaqiruv joyida `alerts_enabled` bilan o'raladi.

### Pitfall 10 — D-26(b) testi bitta bozorda **hech nimani o'lchamaydi**

**Nima noto'g'ri ketadi:** «bir nechta moslik» testi yashil, lekin shox **hech qachon**
bajarilmaydi.

**Nega:** `uq_vendors_market_id_phone_e164` (`market.py:566`) bir bozor ichida ko'p
moslikni **imkonsiz** qiladi.

**Qanday oldini olish:** test `TwoMarketSeed` bilan yoziladi va **ikkala** bozorga bir xil
`phone_e164` seed qilinadi. (5-fazaning W-2/W-3 darsi: darvoza o'lchayotgan holatning
mavjudligini isbotlash kerak.)

---

## Code Examples

### 1. Kvitansiya outboxga — to'lov bilan **BIR** tranzaksiyada (CASH-05, D-21)

```python
# app/api/v1/payments.py — 6-QADAM dan KEYIN, 7-QADAM (audit) yonida
    # ---- 6.5-QADAM: KVITANSIYA NIYATI (CASH-05, D-18/D-21).
    #
    # ⛔ AYNAN SHU TRANZAKSIYADA. Alohida tranzaksiyada yozish «to'lov
    #    yozildi, kvitansiya yozilmadi» oynasini ochardi va u D-02 ning
    #    ikkinchi nizosini (xabar kelmadi) tug'dirardi.
    #
    # ⛔ TAKROR SO'ROVDA IKKINCHI QATOR YOZILMAYDI: `created` `False`
    #    bo'lganda ham `dedupe_key` AYNAN o'sha (`receipt:{payment_id}`),
    #    ya'ni `UNIQUE (market_id, dedupe_key)` uni rad etadi — himoya
    #    ilova shartida emas, CHEKLOVDA (D-21, T-06-49 naqshi).
    if created:
        await outbox_repo.enqueue(
            session,
            market_id=market_id,
            vendor_id=vendor_id,
            kind=OutboxKind.PAYMENT_RECEIPT,
            dedupe_key=f"receipt:{row.payment_id}",
            payload={                       # ⛔ ALLOWLIST (Pitfall 6)
                "amount_soum": row.amount_soum,
                "stall_code": money.stall_code,
                "created_at": row.created_at.isoformat(),
            },
        )
```

### 2. Yangi cron vazifalari (D-16, D-17, Pitfall 4)

```python
# app/worker.py
OUTBOX_TICK_CRON: Final[str] = "* * * * *"
"""Outbox tiki — har daqiqada (DQ-2).

⚠ `TICK_CRON` LITERALI QAYTA ISHLATILMAYDI: `worker.py` ning matn
  darvozasi «`* * * * *` aynan bitta marta uchraydi» deb sanaydi va u
  `capture.tick` niki. Bu — IKKINCHI, mustaqil konstanta.
⚠ `cron_offset` ATAYIN YO'Q: daqiqalik cron mintaqadan MUSTAQIL
  (`TICK_CRON` docstringidagi bilan aynan bir xil sabab).
"""

RECON_OPEN_CRON: Final[str] = "25 4 * * *"
"""Case ochish — `BILLING_CLOSE_CRON` (04:10) dan KEYIN.

⛔ TARTIB KAFOLATI BU SATRGA TAYANMAYDI (`BILLING_CLOSE_CRON` (c) bandi):
   job idempotent (`ON CONFLICT DO NOTHING`) va manbasini O'ZI tekshiradi.
   Cron faqat NARXNI kamaytiradi.
"""

DIGEST_MORNING_CRON: Final[str] = "0 8 * * *"     # hisobdan  (D-16)
DIGEST_EVENING_CRON: Final[str] = "45 20 * * *"   # proyeksiyadan (D-15)
OVERDUE_REMINDER_CRON: Final[str] = "0 9 * * *"   # BOT-03


@broker.task(
    task_name="notify.digest_evening",
    schedule=[{"cron": DIGEST_EVENING_CRON, "cron_offset": MARKET_CRON_OFFSET}],
)
async def digest_evening_task(context: Annotated[Context, TaskiqDepends()]) -> None:
    """YUPQA QOBIQ — kechki nomuvofiqlik xabari (RECON-03, D-15).

    ⛔ BUGUNGI KUN, kechagisi EMAS: manba `pending_projection(as_of=…)` va
       u BUGUN kutilayotgan pattani beradi. `business_today() - 1` berilsa
       xabar ertalabki dayjest bilan BIR XIL raqamni qaytarardi va D-15
       ning butun mazmuni yo'qolardi.
    """
    state = context.state
    await digest_evening(state.sessionmaker, state.sender, as_of=business_today())
```

### 3. `EXPECTED_COMPONENTS` va `watched` — D-17 ning ikki joyi

```python
# app/api/internal/self_check.py
EXPECTED_COMPONENTS: Final[tuple[str, ...]] = (
    "capture_tick", "alert_sweep", "retention", "backup", "cv_detect",
    "billing_close",
    # --- 7-faza (D-17). `deferred-items.md` 2-bandi AYNAN shu bandning
    #     unutilishi edi: `day_close` yurak urishi YOZILADI, lekin uning
    #     YO'QLIGI hech qayerda ko'rinmasdi.
    "outbox_tick", "reconciliation_open", "notify_digest",
)

# app/jobs/alerting.py::_platform_signals
watched = (
    (BACKUP_COMPONENT, "backup_stale"),
    (RETENTION_COMPONENT, "retention_stale"),
    (BILLING_CLOSE_COMPONENT, "billing_close_stale"),
    (OUTBOX_COMPONENT, "outbox_stale"),
    (RECON_OPEN_COMPONENT, "reconciliation_stale"),
    (DIGEST_COMPONENT, "digest_stale"),
)
```

⚠ Har yangi kalit `ALERT_META` ga **yozuv** va uchala locale'ga **matn** talab qiladi
(`04-UI-SPEC.md` §11.9 bilan mos, `alerting.py:322`).

### 4. Hit-rate — **hosila** so'rov, saqlangan ustun emas (D-13)

```sql
-- app/repositories/reconciliation_repo.py
SELECT
    count(*) FILTER (WHERE status = 'justified')                       AS justified,
    count(*) FILTER (WHERE status = 'unjustified')                     AS unjustified,
    count(*) FILTER (WHERE status IN ('new', 'in_review'))             AS open_cases
  FROM reconciliation_cases
 WHERE market_id = :market_id
   AND service_date BETWEEN :from AND :to
-- ⛔ hit_rate USTUN EMAS: `justified / NULLIF(justified + unjustified, 0)`
--    Python tomonda hisoblanadi. `new`/`in_review` MAXRAJGA KIRMAYDI
--    (D-13) — hali ko'rilmagan case metrikani pasaytirmasligi kerak.
-- ⛔ NULLIF: bo'linish nolga tushganda javob `None` bo'ladi, `0.0` EMAS
--    («hali o'lchov yo'q» ≠ «nol aniqlik» — 5-fazaning Wilson qarori).
```

### 5. Telegram xatosini **TURGA** aylantirish (D-04)

```python
# app/jobs/outbox.py
def _classify(exc: Exception) -> tuple[str, int | None]:
    """Istisnoni SIRSIZ (holat, retry_after) juftligiga aylantiradi.

    ⛔ `str(exc)` HECH QAYERGA YOZILMAYDI. Telegram URL'i bot tokenini
       TASHIYDI (`alerts.py` 2-taqiq) va `httpx` istisnosining matni
       to'liq URL'ni o'z ichiga oladi. Bu funksiya `type(exc).__name__`
       va status kodidan boshqa hech nimaga tegmaydi — `_swallow()`
       (`alerting.py:1102`) bilan aynan bir xil qoida.
    """
```

---

## State of the Art

| Eski yondashuv | Joriy yondashuv | Qachon o'zgardi | Ta'siri |
|---|---|---|---|
| `python-telegram-bot` sync API | `aiogram` 3.x asyncio + `pydantic` modellari | aiogram 3.0 (2023) | Loyihaning asyncio steki bilan bir xil ilmoq |
| Webhook «har doim to'g'ri tanlov» | Long-polling kichik yuk va TLS'siz muhitda **to'g'riroq** | — | 175 kadr/kun miqyosida polling narxi ahamiyatsiz |
| `chat_id` ni `int` sifatida saqlash | `str`/`bigint` — Telegram ID lari 32-bit dan **oshib ketgan** | 2021+ | ⚠ Ustun `BIGINT` bo'lishi shart, `INTEGER` emas |
| «Delivered» ni Bot API dan olish | ⛔ **Bot API bunday signal bermaydi** | hech qachon bo'lmagan | Semantika hujjatlashtiriladi (Pitfall 2) |
| Redis 8.x hamma joyda | ⛔ aiogram 3.30 `redis<8` talab qiladi | aiogram 3.x | Servis kesimidagi lockfayl **majburiy** (D-09) |

**Eskirgan / ishlatilmaydi:**

- `aiogram` 2.x — 3.x bilan API mos emas; internetdagi ko'p namuna 2.x uchun.
- `python-telegram-bot` — loyihaning `CLAUDE.md` sida aiogram qat'iylashtirilgan.
- `sendPhoto` / `sendDocument` / `sendMediaGroup` — ⛔ **hech qachon** (D-03).

---

## Assumptions Log

| # | Da'vo | Bo'lim | Xato bo'lsa oqibati |
|---|---|---|---|
| **A1** | Alert boti va sotuvchi boti — **bitta** Telegram boti (bitta token) | Runtime State Inventory | Ikki bot kerak bo'lsa `.env`, `Settings` va `compose.yaml` ikki tokenga bo'linadi; jo'natuvchi ham ikkilanadi |
| **A2** | Quiet hours standarti — **21:00–08:00** Asia/Tashkent | D-19 | Sotuvchilar erta boshlaydi (06:00 birinchi slot); noto'g'ri bo'lsa eslatma savdo boshlanishidan keyin keladi |
| **A3** | `overdue_days` standarti — **3 kun** | D-19, Pattern 5 | Juda kichik bo'lsa case navbati shovqinga aylanadi; juda katta bo'lsa qarz kech ko'rinadi |
| **A4** | Kassirning bosh ko'rsatkichi — kvitansiyalar **soni** (summa emas) | Pitfall 1 | Agar buyurtmachi summani talab qilsa, CASH-04 ning ko'r deklaratsiyasi qayta loyihalanishi kerak (masalan smena yopilgandan **keyin** ko'rsatish) |
| **A5** | D-26(a) «kutilmoqda ro'yxati» = **bog'lanmagan sotuvchilar** ro'yxati (mos kelmagan urinishlar **saqlanmaydi**) | Open Question 1 | Agar urinishlar saqlanishi kerak bo'lsa — begona telefon raqamlarini saqlaydigan yangi jadval kerak (D-01 ostida qo'shimcha huquqiy yuk) |
| **A6** | `market_admin` va `platform_admin` bosh ko'rsatkichi — `REPORT_VIEW` orqali direktornikiga tushadi | Pattern 8 | Ular uchun alohida ko'rsatkich kerak bo'lsa `HEADLINE_ORDER` ga yozuv qo'shiladi |
| **A7** | Case ro'yxati sahifasi — **50** qator | DQ-4 | Faqat ishlash masalasi; nuqson emas |
| **A8** | Kvitansiya matni: summa + rasta kodi + kassir **ismi** + vaqt (CASH-05 matni «kassir» deydi) | Pattern 2 | ⚠ Kassir ismi — `PERSONAL_FIELDS` a'zosi (`full_name`). Sotuvchiga uni ko'rsatish **oqlanadi** (nizoda «kimga to'ladim?»), lekin u `payload` allowlistiga **ataylab** qo'shilishi va sababi yozilishi kerak |

---

## Open Questions (RESOLVED)

> ⚠ To'rtala savol ham rejalashtirish bosqichida **hal qilindi** (2026-08-11) va har biri **egasi bo'lgan rejaga** ko'chirildi. Quyidagi `RESOLVED:` markerlari qaror va uning **mexanik uyini** nomlaydi; savol matni tarix uchun **o'zgarmasdan** qoldirilgan.

1. **D-26(a) ning «kutilmoqda ro'yxati» nimani anglatadi?**
   - Bilamiz: neytral matn qaytariladi, reyestr tashqaridan tekshirilmaydi.
   - Noaniq: admin **muvaffaqiyatsiz urinishlarni** ko'radimi yoki **hali bog'lanmagan
     sotuvchilarni**?
   - Tavsiya: **ikkinchisi** (A5). Birinchisi tizimga sotuvchi bo'lmagan odamlarning
     telefon raqamlarini saqlatadi — D-01 ostida yangi huquqiy yuk va uni saqlashning
     mahsulot qiymati nolga yaqin. Ikkinchisi hech qanday yangi jadval talab qilmaydi
     (`vendors LEFT JOIN vendor_telegram_bindings`) va admin uchun **foydaliroq**.
   - **RESOLVED:** tavsiya qabul qilindi — «kutilmoqda ro'yxati» = **bog'lanmagan
     sotuvchilar**. Uyi: **07-08** Task 1 ning `pending_vendors()` funksiyasi
     (`vendors LEFT JOIN vendor_telegram_bindings ... WHERE binding.id IS NULL`).
     ⛔ Muvaffaqiyatsiz urinishlar **saqlanmaydi** va `ResolveOutcome` da telefon
     maydoni **yo'q** — bu 07-08 ning qabul mezoni bilan o'lchanadi (T-07-41).

2. **CASH-05 kvitansiyasida kassir ismi bo'lsinmi?**
   - Bilamiz: talab matni «summa, rasta, kassir, vaqt» deydi.
   - Noaniq: «kassir» — ism, tabel raqami yoki umuman ko'rsatilmaydimi.
   - Tavsiya: **ism** (nizoda foydali), lekin `payload` allowlistiga **ataylab** va
     sabab bilan qo'shilsin; muqobil — kassir kodi/inisiallari.
   - **RESOLVED:** tavsiya qabul qilindi — **ism**. Uyi: **07-06** Task 2
     (`NOTIFICATION_META["payment_receipt"].payload_keys` ga `cashier_name`
     ⛔ **ochiq yozuv** sifatida, sabab bilan) va **07-12** Task 1 (chaqiruv joyi
     `user_repo.list_profiles()` bilan). ⛔ Ism **javobga qaytmaydi** — faqat
     Telegram matniga tushadi, ya'ni `PERSONAL_ROUTES` **o'smaydi** (G7-6, T-07-74).

3. **`bot-service` ning Valkey ulanishi qaysi `db` raqamini oladi?**
   - Bilamiz: `core-api` `db 0` da ishlaydi va u yerda rate-limit, sessiya keshi va
     `sbozor:jobs` navbati bor (`worker.py:199-227`).
   - Noaniq: aiogram FSM kalitlari o'sha `db` ga qo'shilsinmi.
   - Tavsiya: **`db 1`** — kalit maydoni ajratiladi va `FLUSHDB` xatosi ikki tizimni
     birdan yiqitmaydi. Alternativa: `db 0` + `fsm:` prefiksi (aiogram `RedisStorage`
     prefiks beradi).
   - **RESOLVED:** tavsiya qabul qilindi — **`db 1`**. Uyi: **07-01** Task 1
     (`services/bot-service/app/settings.py` da `valkey_url` standarti
     `redis://cache:6379/1`, sabab izohda) va Task 2 (`compose.yaml` dagi
     `BOT_VALKEY_URL` — `.env.example` bandi bilan).

4. **`gate` byudjeti oshadimi?**
   - Bilamiz: `gate` 2300 s, `gate:fast` 200 s (`06-VALIDATION.md`); oxirgi o'lchov
     1899 s (82 %).
   - Noaniq: `bot-service` ning **to'rtinchi** konteyner-testi (`bot-tests`) va yangi
     backend testlari qancha qo'shadi.
   - Tavsiya: byudjet **oldindan oshirilmaydi**. `bot-service` testlari `aiogram` ning
     `MockedBot` i bilan tarmoqsiz ishlaydi (~10–20 s). Faza yopilishida uch o'lchov
     protokoli qayta yuritiladi (05-15 W0-13 qoidasi).
   - **RESOLVED:** tavsiya qabul qilindi — byudjet **oldindan oshirilmaydi**.
     Uyi: **07-01** Task 2 (`bot:test` `gate` zanjirida, `gate:fast` da ⛔ **yo'q**)
     va **07-17** Task 2 (tinch xostda **uch o'lchov**; oshsa avval `bot:test` ni
     `gate` dan ajratish tekshiriladi, keyin 05-15 W0-13 protokoli; raqam
     `package.json` va `07-VALIDATION.md` da ⛔ **bir xil** yoziladi).

---

## Environment Availability

| Bog'liqlik | Kim talab qiladi | Mavjudmi | Versiya | Zaxira |
|-----------|------------------|----------|---------|--------|
| Docker Compose v2 | Butun stek | ✓ | `compose.yaml` v2 | — |
| PostgreSQL 18.4 | Yangi jadvallar, RLS | ✓ | `postgres:18.4` (testcontainers) | — |
| Valkey 9.x | aiogram FSM, taskiq | ✓ | `cache` xizmati | — |
| `uv` 0.11.33 | `bot-service` lockfayli | ✓ | `ghcr.io/astral-sh/uv:0.11.33` | — |
| `python:3.13-slim-trixie` | `bot-service` bazasi | ✓ | mavjud shablon | — |
| **Telegram Bot API (internet)** | Haqiqiy jo'natish | ✗ (CI'da) | — | ⚠ `respx` (core-api) + `aiogram` `MockedBot` (bot-service); haqiqiy yetkazish **`07-HUMAN-UAT.md`** bandi |
| **Bot tokeni** | Jonli sinov | ✗ (CI'da) | — | `alerts_enabled=False` yo'li allaqachon mavjud va **jimgina emas** (`alerts.py:86-99`) |
| **TLS sertifikati** | Webhook | ✗ | — | ✅ **Kerak emas** — DQ-1 long-polling ni tanladi |
| `msgfmt` (gettext) | `.po` → `.mo` kompilyatsiyasi | ⚠ tekshirilmagan | — | ⚠ **Zaxira: `Babel` ning `pybabel compile`** — u allaqachon bog'liqlik va tashqi binar talab qilmaydi. ⛔ Reja `msgfmt` ga tayanmasin |

**Zaxirasi YO'Q, bloklovchi yetishmovchilik:** yo'q.

**Zaxirasi bor yetishmovchiliklar:** Telegram tarmoq yo'li (mock bilan o'lchanadi, haqiqiy
yetkazish `07-HUMAN-UAT.md` ga chiqadi — 4-fazaning `#4` bandi bilan **aynan bir xil**
shakl); `msgfmt` (`pybabel compile` bilan almashtiriladi).

---

## Validation Architecture

> `workflow.nyquist_validation = true` (`.planning/config.json`) — bu bo'lim **majburiy**.

### Test Framework

| Xossa | Qiymat |
|-------|--------|
| Backend framework | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), testcontainers 4.15.0 + **haqiqiy** `postgres:18.4` (⛔ SQLite TAQIQ — RLS yo'q) |
| Backend config | `pyproject.toml` (ildiz) + `tests/conftest.py` — **mavjud** |
| `bot-service` framework | pytest + `aiogram.test_utils.mocked_bot.MockedBot` — ⛔ **Wave 0 da quriladi** (`services/bot-service/pyproject.toml` + `bot-tests` konteyneri) |
| Frontend framework | vitest (`.test.tsx`) + `node --test` (`frontend/scripts/*.test.mjs`) |
| Tez buyruq | `npm run gate:fast` → `npm run test:fast && npm --prefix frontend test` |
| To'liq to'plam | `npm run test` + `npm run test:tenancy` + **`npm run bot:test`** (yangi) |
| Faza darvozasi | `npm run gate` + `tests/integration/test_phase7_criteria.py` |
| Byudjet | `gate` **2300 s**, `gate:fast` **200 s** (`06-VALIDATION.md`) — ⛔ **o'zgartirilmaydi**; oshsa 05-15 W0-13 protokoli (tinch xost, uch o'lchov, eng yomon × 1,20) |

### Byudjetga sig'ish — raqam bilan

Oxirgi o'lchov `gate` = **1899 s**, chegara 2300 s → **401 s zaxira**. Bu fazaning
qo'shimchasi:

| Manba | Taxminiy narx | Sabab |
|-------|---------------|-------|
| `bot-service` testlari (`bot:test`) | **~25 s** | `MockedBot` tarmoqqa chiqmaydi; `docker compose run` ning o'zi ~15 s |
| Backend integratsiya (~60 test) | **~120 s** | 6-faza **141** integratsiya+tenancy testi qo‘shdi va `gate` 1250 → 1899 s bo‘ldi; bu faza taxminan **yarmicha** qo‘shadi |
| `bot-service` lint/typecheck | **~20 s** | ruff + mypy, kichik kod bazasi |
| vitest (+~60 test) + 1 yangi SSG marshruti (`/reconciliation` × 3 locale) | **~60 s** | 6-faza vitest'ni 620 → 717 ga oshirdi va **uchta** SSG marshruti qo‘shdi; bu yerda **bitta** |
| **Jami** | **≈ 225 s** | Zaxira **401 s** ichida |

⚠ Agar o'lchov 2300 s dan oshsa — ⛔ **byudjet «shunchaki oshirilmaydi»**: avval
`bot:test` ni `gate:fast` dan **tashqarida** qoldirish tekshiriladi (u mustaqil kod
bazasi), keyin protokol yuritiladi.

### Phase Requirements → Test Map

| Req | Xulq | Turi | Avtomatik buyruq | Fayl bormi? |
|-----|------|------|------------------|-------------|
| RECON-01 | Hisobotda ikkala sinf va dalil **havolasi** ko'rinadi; ⛔ javobda kadr **bayti** yo'q | integration | `pytest tests/integration/test_phase7_criteria.py::test_sc1_report_shows_both_classes_with_evidence_links -x` | ❌ Wave 0 |
| RECON-02 | Case holati 4 a'zoli yopiq to'plam; o'zgarish **audit qatori**; hit-rate hosila | integration | `pytest tests/integration/test_reconciliation_api.py -x` | ❌ Wave 0 |
| RECON-02 | ⛔ `other` a'zosi **yo'q** — to'plam tengligi | unit | `pytest tests/unit/test_reconciliation_enums.py -x` | ❌ Wave 0 |
| RECON-03 | 20:45 xabari `pending_projection()` dan; 08:00 xabari `daily_charges` dan; **ikki son har xil** | integration | `pytest tests/integration/test_notifications.py::test_evening_reads_projection_and_morning_reads_ledger -x` | ❌ Wave 0 |
| RECON-03 | Uchala yangi komponent `EXPECTED_COMPONENTS` da **va** `watched` da (D-17) | unit | `pytest tests/unit/test_heartbeat_registry.py -x` | ❌ Wave 0 |
| RECON-06 | Javobda **aynan bitta son**; ⛔ kassir qiymati kunlik summaga **teng emas** | integration | `pytest tests/integration/test_headline.py -x` | ❌ Wave 0 |
| CASH-05 | To'lov → outbox qatori **o'sha tranzaksiyada**; takror `POST` **ikkinchi qator bermaydi** | integration | `pytest tests/integration/test_outbox.py::test_receipt_is_enqueued_once_per_payment -x` | ❌ Wave 0 |
| CASH-05 | Quiet hours kvitansiyani **ushlab qolmaydi** (D-18) | unit | `pytest tests/unit/test_outbox_policy.py -x` | ❌ Wave 0 |
| BOT-01 | `user_id is None` / `user_id != from_user.id` / guruh chati — **uch** rad | unit (bot) | `docker compose --profile test run --rm bot-tests pytest tests/unit/test_binding.py -x` | ❌ Wave 0 |
| BOT-01 | ⛔ Ikki bozorda bir xil telefon → bog'lanish **yo'q** + alert (D-26b) | integration | `pytest tests/integration/test_bot_internal_api.py::test_two_markets_same_phone_refuses_binding -x` | ❌ Wave 0 |
| BOT-02 | Qoldiq `vendor_outstanding()` bilan **teng**; tarix `vendor_charge_allocation()` dan | integration | `pytest tests/integration/test_bot_internal_api.py -x` | ❌ Wave 0 |
| BOT-03 | `overdue_days` bozor kesimida; quiet hours ga **bo'ysunadi** | integration | `pytest tests/integration/test_notifications.py::test_overdue_reminder_respects_market_settings -x` | ❌ Wave 0 |
| BOT-04 | `403` → `blocked`, qayta urinish **yo'q**; `429` → `retry_after`; 5 urinishdan keyin `failed` | integration | `pytest tests/integration/test_outbox.py -x` | ❌ Wave 0 |
| BOT-04 | ⛔ Jo'natuvchi **bloklamaydi**: Telegram yiqilganda to'lov yozuvi o'tadi (D-23) | integration | `pytest tests/integration/test_outbox.py::test_telegram_failure_does_not_block_payment -x` | ❌ Wave 0 |

### ⛔ Ikki TAQIQNING strukturaviy darvozalari (kelishuv EMAS)

| Darvoza | Nima o'lchanadi | Buyruq |
|---|---|---|
| **G7-1 (D-03)** | `AlertSender` ning ommaviy metodlari to'plami **o'zgarmadi** (`dir()`); `TELEGRAM_SEND_METHOD` matnda **aynan bitta** Bot API metodi; `sendPhoto\|sendDocument\|sendMediaGroup\|photo=\|InputFile` butun `app/jobs/outbox.py` + `app/services/alerts.py` bo'ylab → **0** | `pytest tests/integration/test_alerting.py tests/unit/test_outbox_surface.py -x` |
| **G7-2 (D-03)** | `notification_outbox` sxemasida `snapshot_id`/`image`/`object_key`/`url` nomli ustun **YO'Q** — `information_schema` **to'plam tengligi** bilan | `pytest tests/tenancy/test_notification_domain_meta.py -x` |
| **G7-3 (D-03, frontend)** | `components/reconciliation/**` da alert/xabar bloklarida `<img>` **yo'q**; dalil faqat mavjud `GET /snapshots/{id}/image` marshrutiga **havola** | `node --test frontend/scripts/reconciliation-copy.test.mjs` |
| **G7-4 (D-04)** | `app/jobs/outbox.py` + `app/services/alerts.py` da `str(exc)`/`{exc}`/`repr(exc)` → **0**; `last_error` ustuniga **faqat** `type(exc).__name__` yoziladi (AST bilan) | `pytest tests/unit/test_outbox_secrets.py -x` |
| **G7-5 (D-04)** | Jo'natuvchi yiqilganda `caplog` matnida token satri **yo'q** — soxta token bilan **xulqiy** o'lchov (`respx` bilan) | `pytest tests/integration/test_outbox.py::test_failure_log_carries_no_token -x` |
| **G7-6 (D-05)** | `PERSONAL_ROUTES` **o'smadi**: yangi `/api/v1/*` marshrutlarining birortasi `vendor_name`/`phone`/`full_name` qaytarmaydi | `pytest tests/tenancy/test_personal_data_coverage.py -x` |
| **G7-7 (T-06-22)** | `DEFINER_SURFACES == ()` va yangi `SECURITY DEFINER` funksiya **0** | `pytest tests/tenancy/test_occupancy_domain_meta.py tests/tenancy/test_meta.py -x` |
| **G7-8 (D-06/D-07)** | Yangi migratsiya va yangi modullarda `balance`/`balance_soum` ustuni **0**; `float(`/`Decimal`/`round(` **0** | `pytest tests/tenancy/test_notification_domain_meta.py -x` |
| **G7-9 (D-30/D-31)** | Glossariy atamalari **ikkala** manbada bir xil; uchala locale kalit-parity | `npm --prefix frontend run i18n:check && docker compose --profile test run --rm bot-tests pytest tests/unit/test_locale_parity.py -x` |

**G7-9 ning aniq shakli (D-30 ning yagona o'lchanadigan ta'rifi):**
`ops/i18n/glossary.json` — `{term: {uz-Latn, uz-Cyrl, ru}}` (kamida `qarz`, `patta`,
`rasta`, `smena`). Test ikki tomonlama:
(a) har atama har locale'da frontend `messages/<locale>.json` ning **flatten qilingan**
qiymatlarida ≥1 marta uchraydi; (b) o'sha atama bot `.po` katalogining `msgstr`
qiymatlarida ≥1 marta uchraydi; (c) **taqiqlangan sinonimlar** (masalan `yig'im` ↔
`patta`, `do'kon` ↔ `rasta`) **ikkalasida ham 0** marta. ⛔ Uchinchi band majburiy — usiz
gate «ikkalasida ham bor» ni tasdiqlaydi, lekin **ikkinchi so'z paydo bo'lishini**
to'smaydi. Bugungi holat o'lchandi: `uz-Latn.json` da `qarz` 6, `patta` 25, `rasta` 99,
`smena` 16 kalitda uchraydi (1109 kalit × 3 locale).

### Sampling Rate

- **Har task commitida:** `npm run gate:fast` (byudjet 200 s)
- **Har to'lqin merge'ida:** `npm run test` + `npm run test:tenancy` + `npm run bot:test`
- **Faza darvozasi:** to'liq `npm run gate` yashil **va**
  `tests/integration/test_phase7_criteria.py` beshala mezonni **bitta buyruqda** beradi

### Wave 0 Gaps

- [ ] `services/bot-service/` butun skeleti — `pyproject.toml`, `uv.lock`, `Dockerfile`,
      `app/main.py` (⛔ `init_sentry()` bilan), `app/observability.py`
- [ ] `compose.yaml` ga `bot-service` **va** `bot-tests` yozuvlari
- [ ] `package.json` ga `bot:test` / `bot:lint`; `gate` zanjiriga ulash
- [ ] ⛔ `tests/unit/test_sentry_processes.py::FOREIGN_HOOK_MARKERS` ni aiogram ilmog'i
      bilan kengaytirish (Pitfall 3) — **birinchi** migratsiyadan oldin
- [ ] `tests/tenancy/test_notification_domain_meta.py` — RLS/FORCE/kompozit FK/⛔ nomlar
      to'plami (G7-2, G7-8)
- [ ] `tests/unit/test_outbox_surface.py` + `test_outbox_secrets.py` (G7-1, G7-4)
- [ ] `ops/i18n/glossary.json` + `frontend/scripts/glossary.test.mjs` (G7-9)
- [ ] `tests/fixtures/notification_domain.py` — outbox/case/binding seed'lari
- [ ] `services/bot-service/tests/unit/test_sentry_entrypoints.py`
      (`cv-service` dagi juftining nusxasi)
- [ ] `tests/integration/test_phase7_criteria.py` skeleti — **beshta** mezon, **beshta**
      test, meta-test bilan

---

## Security Domain

`security_enforcement = true`, `security_asvs_level = 1`.

### Applicable ASVS Categories

| ASVS toifasi | Tegishlimi | Standart nazorat |
|---|---|---|
| **V1 Architecture** | ✅ | Ishonch chegarasi **kengaydi** (D-01): birinchi marta autentifikatsiyalanmagan tashqi shaxs (sotuvchi) tizim ma'lumotini oladi |
| **V2 Authentication** | ✅ | Bot: Telegram `contact` (`user_id == from_user.id`); servis-servis: statik Bearer + `hmac.compare_digest`. ⛔ Foydalanuvchi sessiyasi tug'ilmaydi (D-10) |
| **V3 Session Management** | ✅ | aiogram FSM `RedisStorage` (Valkey). ⛔ Bot **JWT ishlatmaydi** va cookie qo'ymaydi |
| **V4 Access Control** | ✅ | `vendor_telegram_bindings` — bitta Telegram ID ↔ bitta faol vendor; RLS `FORCE` + kompozit FK; case yuzasi mavjud `Permission` matritsasidan |
| **V5 Input Validation** | ✅ | `pydantic` (ikkala servisda); `phonenumbers` E.164 chegarada; case yechim matni uzunlik bilan cheklanadi |
| **V6 Cryptography** | ⚠ qisman | Yangi shifrlash **yo'q**. `BOT_SERVICE_TOKEN` — `SecretStr`; taqqoslash `hmac.compare_digest` (⛔ `==` emas) |
| **V7 Error Handling & Logging** | ✅✅ | ⛔ **Fazaning eng o'tkir bandi**: D-04 — istisno matni bot tokenini tashiydi. Faqat `type(exc).__name__` + status |
| **V8 Data Protection** | ✅✅ | D-01/D-03: har bayt chegaradan chiqadi. Kadr **hech qachon**; matn **minimal**; `payload` **allowlist** |
| **V13 API** | ✅ | `/internal/bot/*` — `include_in_schema=False`, nginx orqali **erishib bo'lmaydi** |

### Known Threat Patterns

| Naqsh | STRIDE | Standart mitigatsiya | Bu fazadagi shakli |
|---|---|---|---|
| Begona kontakt ulashish → boshqa sotuvchining qarzi | **Spoofing** | Egalik tekshiruvi | `contact.user_id == message.from_user.id` **va** `user_id is not None` (Pitfall 8) |
| Reyestrni tashqaridan tekshirish (raqam bo'yicha sanash) | **Information disclosure** | Neytral javob | D-26(a): «yo'q» deb **tasdiqlanmaydi**; ⚠ **rate-limit ham kerak** — cheksiz `contact` yuborish orqali «kim javob berdi» taymingi bo'yicha ajratish mumkin |
| Bot tokenining istisno matni orqali sizishi | **Information disclosure** | Xato **turi**, matni emas | D-04 / G7-4 / G7-5 (`alerts.py` 2-taqiq) |
| Dalil-kadrning Telegramga chiqishi | **Information disclosure** | Metodning **yo'qligi** | D-03 / G7-1 / G7-2 / G7-3 |
| Servis-servis tokenining brute-force'i | **Elevation of privilege** | Doimiy vaqtli taqqoslash + tarmoq izolyatsiyasi | `hmac.compare_digest`; nginx `/internal/*` ni proxy qilmaydi |
| Kassirning bosh ekrandan tizim summasini olishi | **Information disclosure** | Serverda qaror | Pitfall 1 (T-06-53/59 ning davomi) |
| Ikki kvitansiya bir to'lov uchun | **Repudiation** | `UNIQUE` cheklov | D-21 (T-06-49 naqshi) |
| Bozorlararo bog'lanish oqishi | **Information disclosure** | RLS `FORCE` + kompozit FK | Yangi uchala jadval; `active_market_ids()` **yagona** chetlab o'tish yuzasi |
| Telegram uzilishi butun tizimni to'xtatishi | **Denial of service** | Bloklamaydigan jo'natuvchi | D-23 (`alerts.py` 3-taqiq) |
| Bot orqali xabar bombardimoni (throttling yo'qligi) | **Denial of service** | Per-chat 1 msg/s, jami ~30 msg/s | Rasmiy chegaralar [CITED: core.telegram.org/bots/faq]; outbox `batch` va `sleep` bilan hurmat qiladi |
| Case yechim matnining XSS'i | **Tampering** | React avtomatik escape + uzunlik chegarasi | ⛔ `dangerouslySetInnerHTML` **ishlatilmaydi** |
| Telegram xabarining HTML injektsiyasi | **Tampering** | `parse_mode="HTML"` + qiymatlarni escape | ⚠ `alerts.py:336-338` HTML tanlagan (Markdown emas). Sotuvchi **ismi** matnga tushsa (A8) `html.escape()` **majburiy** — aks holda `<` bilan xabar rad etiladi |

---

## Project Constraints (from CLAUDE.md)

| Direktiva | Bu fazada qanday bajariladi |
|---|---|
| **Aynan 3 ta servis** | `bot-service` — **uchinchi va oxirgi**. ⛔ To'rtinchi tug'ilmaydi; `bot-tests` — o'sha image'ning boshqa entrypointi (`cv-tests` naqshi) |
| **Har servis o'z `pyproject.toml`/`uv.lock` i bilan** | D-09; `test_runtime_deps.py` naqshidagi darvoza `bot-service` uchun ham yoziladi |
| **`aiogram 3.30` ↔ `pydantic<2.14` ↔ `redis<8`** | [VERIFIED: PyPI 2026-08-11] `pydantic<2.14,>=2.4.1`, `redis[hiredis]<8,>=6.2.0` — pinlar: `pydantic==2.13.4`, `redis==7.4.1` |
| **Litsenziya: Apache-2.0 / MIT / BSD** | aiogram MIT, Babel BSD-3, aiodns MIT, uvloop MIT — ⛔ AGPL **yo'q** |
| **Pul — `BIGINT` so'm ↔ `int`** | `float`/`Decimal`/`round(` darvozasi yangi modullarga **tarqaydi** (G7-8) |
| **`TIMESTAMPTZ` + `ZoneInfo` + `tzdata`** | `bot-service` ga `tzdata` **majburiy**; cron `cron_offset` bilan |
| **Multi-tenant: hamma jadvalda `market_id`** | Uchala yangi jadval + RLS `ENABLE`+`FORCE` + tenant policy + kompozit FK |
| **Debian-slim baza (musl emas)** | `python:3.13-slim-trixie`; `uvloop` cp313 manylinux g'ildiragi |
| **UI: Apple-uslub minimal; 3 til majburiy** | D-30/D-31 + G7-9 |
| **Audit jurnali majburiy** | Case holati o'zgarishi (D-14) va bog'lanish bekor qilinishi (D-26c) — `write_app_audit` |
| **GSD Workflow Enforcement** | Ijro faqat `/gsd-execute-phase` orqali |

---

## Sources

### Primary (HIGH confidence)

- **Kod bazasi (bevosita o'qildi):** `services/core-api/app/services/alerts.py`,
  `app/jobs/alerting.py`, `app/worker.py`, `app/repositories/billing_repo.py`,
  `app/api/v1/payments.py`, `app/api/v1/me.py`, `app/api/internal/live_authz.py`,
  `app/api/internal/self_check.py`, `app/deps.py`, `app/settings.py`,
  `app/security/rbac.py`, `packages/sbozor-core/sbozor_core/enums.py`,
  `.../models/billing.py`, `.../models/market.py`,
  `migrations/versions/0020_billing_domain.py`, `compose.yaml`,
  `ops/nginx/nginx.conf`, `services/cv-service/pyproject.toml`,
  `services/core-api/Dockerfile`, `tests/unit/test_sentry_processes.py`,
  `tests/unit/test_runtime_deps.py`, `tests/tenancy/test_personal_data_coverage.py`,
  `tests/tenancy/test_occupancy_domain_meta.py`, `package.json`,
  `frontend/scripts/check-messages.mjs`, `frontend/messages/*.json`
- **Rejalashtirish artefaktlari:** `07-CONTEXT.md`, `06-CONTEXT.md`, `06-VALIDATION.md`,
  `06-SECURITY.md`, `06-UI-SPEC.md`, `04-UI-SPEC.md`, `deferred-items.md`,
  `ROADMAP.md`, `REQUIREMENTS.md`, `CLAUDE.md`, `.planning/config.json`
- **PyPI JSON API** (2026-08-11): `aiogram` 3.30.0 / MIT / `pydantic<2.14,>=2.4.1` /
  `redis[hiredis]<8,>=6.2.0` / `Babel<3,>=2.13.0` / `requires_python <3.15,>=3.10`;
  `Babel` 2.18.0; `aiodns` 4.0.4; `uvloop` 0.22.1 (cp313 manylinux_2_28); `redis` 7.4.1
- **slopcheck 0.6.1** — `slopcheck install -e pypi aiogram Babel aiodns uvloop redis
  phonenumbers` → **6/6 [OK]**
- **Telegram Bot API rasmiy hujjati** — `setWebhook` (HTTPS majburiy; portlar
  443/80/88/8443), `getUpdates` (webhook bilan o'zaro istisno), `Contact` obyekti
  (`user_id` **ixtiyoriy**), `sendMessage` (`Message` qaytaradi; ⛔ yetkazilganlik
  kvitansiyasi **yo'q**): https://core.telegram.org/bots/api
- **Telegram Bots FAQ** — ~30 xabar/s jami, chatga 1 xabar/s, guruhga 20 xabar/daqiqa,
  chegaradan oshsa `429`: https://core.telegram.org/bots/faq
- **aiogram manba kodi** — istisno ierarxiyasi va `TelegramRetryAfter.retry_after`:
  https://raw.githubusercontent.com/aiogram/aiogram/dev-3.x/aiogram/exceptions.py

### Secondary (MEDIUM confidence)

- aiogram i18n hujjati (`I18n`, `SimpleI18nMiddleware`, `locale/<loc>/LC_MESSAGES/<domain>.po`
  tuzilishi): https://docs.aiogram.dev/en/stable/utils/i18n.html
- `KeyboardButton.request_contact` semantikasi («faqat shaxsiy chatda»; bosilganda
  Telegram tasdiq oynasini ko'rsatadi) — rasmiy hujjatning kesilgan qismidan tashqari
  ikkilamchi manbalar bilan tasdiqlandi

### Tertiary (LOW confidence — tasdiqlash kerak)

- `403 Forbidden: bot was blocked by the user` ni **doimiy** nosozlik deb hisoblash
  amaliyoti — jamoa manbalaridan (GitHub issue muhokamalari). ⚠ Xato **matni**
  Telegram tomonidan o'zgartirilishi mumkin, shuning uchun kod **status 403** ga
  qarashi kerak, matnga **emas**
- Quiet hours va `overdue_days` ning standart qiymatlari (A2/A3) — buyurtmachi bilan
  tasdiqlanmagan

---

## Metadata

**Confidence breakdown:**

| Soha | Daraja | Sabab |
|------|--------|-------|
| Standard stack | **HIGH** | Har pin PyPI metadata'sidan **o'qildi**, slopcheck 6/6 `[OK]`, litsenziyalar tekshirildi |
| Webhook vs long-polling | **HIGH** | Ikki mustaqil dalil: rasmiy Bot API (HTTPS majburiy) va repodagi `nginx.conf:8-9` (TLS yo'q) |
| Outbox mexanikasi | **HIGH** | Mavjud `capture_repo` + `alerts.py` naqshlari o'qildi; barcha cheklovlar migratsiya manbasidan tasdiqlandi |
| Case modeli / kompozit FK | **HIGH** | ⛔ Ikkala nishon UNIQUE cheklovi **mavjudligi** `0020_billing_domain.py:414,662` da tasdiqlandi — taxmin emas |
| RECON-06 ↔ CASH-04 to'qnashuvi | **HIGH** | Uch mustaqil kod dalili (`payment_repo.py:145`, `shifts.py:126`, T-06-59) |
| Telegram yetkazilganlik semantikasi | **HIGH** (salbiy da'vo) | Rasmiy hujjatda `sendMessage` `Message` qaytaradi; yetkazilganlik/o'qilganlik maydoni **yo'q** |
| BOT-01 `contact` darvozasi | **MEDIUM-HIGH** | `Contact.user_id` ixtiyoriyligi rasmiy hujjatdan **tasdiqlangan**; `user_id == from_user.id` tengligi mantiqiy hosila va u **test bilan** o'lchanishi kerak |
| Quiet hours / `overdue_days` qiymatlari | **LOW** | `[ASSUMED]` — A2/A3 |
| `gate` byudjetiga sig'ish | **MEDIUM** | Hisob 6-fazaning o'lchangan o'sishidan ekstrapolyatsiya; haqiqiy o'lchov faza oxirida |

**Research date:** 2026-08-11
**Valid until:** 2026-09-10 (30 kun). ⚠ `aiogram` va `redis` pinlari **oy sayin**
o'zgaradi; reja yozilishidan oldin `pyproject.toml` yozilayotgan kuni PyPI qayta
tekshirilsin.
