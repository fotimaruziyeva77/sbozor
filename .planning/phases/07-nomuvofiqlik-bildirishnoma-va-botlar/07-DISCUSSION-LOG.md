# Phase 7: Nomuvofiqlik, bildirishnoma va botlar - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-11
**Phase:** 7-nomuvofiqlik-bildirishnoma-va-botlar
**Areas discussed:** Servis chegarasi va outbox egaligi, Case modeli, Xabar tetiklari va vaqt, Sotuvchi identifikatsiyasi, Bosh ekran ko'rsatkichi, Til va matn manbai

> ⚙ **`--auto` rejimi.** Foydalanuvchining doimiy ko'rsatmasi bo'yicha
> (`no-questions-autonomous-mode`, 2026-08-01) `AskUserQuestion` **ishlatilmadi**
> — har savolda **tavsiya etilgan** variant tanlandi. Quyidagi jadvallar
> ko'rib chiqilgan alternativalarni va nega rad etilganini saqlaydi.
> ⛔ Tanlov **sababi** CONTEXT.md dagi tegishli D-band bilan bog'langan.

---

## Servis chegarasi va outbox egaligi (BOT-04, CASH-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Outbox core-api da, bot-service faqat kiruvchi | Chiquvchi jo'natish `alerts.py` naqshida core-api'da; bot faqat Telegram update'larini qabul qiladi va ichki API'ga yozadi | ✓ |
| Outbox bot-service da | Bot o'zi DB'ga yozadi va o'zi jo'natadi — «bot bilan bog'liq hamma narsa bir joyda» | |
| Gibrid: kvitansiya core-api'dan, eslatma bot'dan | Tetigi tranzaksion bo'lgan xabar core-api'da, jadvalli xabar bot'da | |

**Tanlov:** Outbox core-api da (D-08)
**Notes:** Uch mustaqil sabab. (1) Pul haqiqati core-api'da **RLS ostida** —
bot-service'ga DB berish **ikkinchi RLS yuzasi** ochardi va 6-fazaning
T-06-21/T-06-22 kafolatlari o'sha yuzada qaytadan isbotlanishi kerak bo'lardi.
(2) ⛔ **Mexanik to'siq:** `aiogram 3.30` `redis[hiredis]>=6.2,<8` va
`pydantic<2.14` talab qiladi, core-api esa `redis 8.0.1` ga qadalgan
(`CLAUDE.md` Version Compatibility) — ikki servis bitta navbat klientini
**bo'lisha olmaydi**. (3) `alerts.py` ning ikki taqig'i (kadr yo'q, token
sizmaydi) allaqachon core-api'da **o'lchanadi**; jo'natishni ko'chirish
darvozalarni ikkilantirardi. Gibrid varianti rad etildi: u ikki jo'natuvchi
yo'li demakdir va «bu xabar qaysi yo'ldan ketdi?» savolini tug'dirardi.

---

## Case modeli (RECON-01, RECON-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Alohida `reconciliation_cases` jadvali | Anomaliyaga muzlatilgan pointer bilan bog'lanadi; holat/mas'ul/yechim shu yerda | ✓ |
| `billing_anomalies` ga case ustunlari qo'shish | Bitta jadval, bitta qator — kamroq JOIN | |

**Tanlov:** Alohida jadval (D-11)
**Notes:** Anomaliya — **hodisa** (6-fazada dalil sinfiga kiritilgan,
o'zgarmas bo'lishi kerak); case — **jarayon** (mas'ul, holat, yechim
o'zgaradi). Ikkisini bitta qatorga qo'shish o'zgarmas dalil qatorini
**o'zgaruvchan** qilardi — 6-fazaning D-07/T-06-15 sinfini to'g'ridan-to'g'ri
buzardi. «Kamroq JOIN» — bu narxga arzimaydi.

---

## Xabar tetiklari va vaqt (RECON-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Kechki xabar proyeksiyadan, ertalabki dayjest hisobdan | `pending_projection()` (as_of=hozir) kechqurun; `daily_charges` ertalab | ✓ |
| Ikkalasi ham hisobdan | Bitta manba, sodda | |
| Kechki xabarni 04:10 dan keyinga surish | Hisob tayyor bo'lgach yuborish | |

**Tanlov:** Proyeksiya + hisob, ikki manba (D-15, D-16)
**Notes:** ⛔ **«Ikkalasi ham hisobdan» MEXANIK ravishda imkonsiz:**
`BILLING_CLOSE_CRON = "10 4 * * *"` (`worker.py:445`) — D kunining hisobi
**D+1 ning 04:10** da tug'iladi, ya'ni kechqurun `daily_charges` da bugungi
kun **hali yo'q**. Uchinchi variant («kechki xabarni ertalabga surish») esa
mahsulotni buzadi: «kechqurun nomuvofiqlik xabari» ROADMAP mezoni va uning
qiymati **o'sha kuni** ta'sir qilishida. ⚠ Ikki raqam farq qilishi
**kutilgan** va bu xabar matnida **ochiq** aytilishi kerak (6-faza D-17
naqshi) — aks holda direktor ikki sonni ko'rib ishonchni yo'qotadi.

---

## Kvitansiyaning quiet hours ga munosabati (CASH-05, BOT-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Kvitansiya hech qachon bostirilmaydi | `never_suppressed` bayrog'i; eslatma va dayjest quiet hours ga bo'ysunadi | ✓ |
| Hammasi quiet hours ga bo'ysunadi | Bitta qoida, istisnosiz | |

**Tanlov:** Kvitansiya istisno (D-18)
**Notes:** Kvitansiya — sotuvchining **hozirgina to'laganini** isbotlaydigan
yozuv. Uni kechiktirish nizo modelini (D-02) buzadi: sotuvchi to'lab ketadi,
tasdiq esa ertalab keladi. `ALERT_META.never_suppressed` bayrog'i
(`alerting.py`) aynan shu tushunchaning **mavjud uyi** — yangi mexanizm
o'ylab topilmaydi.

---

## Sotuvchi identifikatsiyasi (BOT-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Faqat Telegram `contact` obyekti | Telegram kafolatlagan raqam; E.164 normallashtirish; uch shox nomlangan | ✓ |
| Qo'lda terilgan raqam + SMS kod | Universal, Telegram'ga bog'liq emas | |
| Admin bergan bir martalik kod | Admin sotuvchiga kod beradi, u botga kiritadi | |

**Tanlov:** Faqat `contact` (D-24, D-25, D-26)
**Notes:** Terilgan raqam — foydalanuvchining **da'vosi**; `contact` —
Telegram **o'zi kafolatlagan** yagona narsa. Terilganni qabul qilish begona
sotuvchining qarzini ko'rish yo'lini ochardi. SMS varianti yangi tashqi
bog'liqlik (provayder, xarajat, yetkazilmaslik) qo'shadi va 12 haftalik
jadvalga sig'maydi. Admin kodi — dala ishi talab qiladi va
`sbozor-self-service-principle` ga zid. ⛔ Mos kelmagan raqamga «bu raqam
ro'yxatda yo'q» **deyilmaydi** — u reyestrni tashqaridan tekshirish yo'li
bo'lardi.

---

## Bosh ekran ko'rsatkichi (RECON-06)

| Option | Description | Selected |
|--------|-------------|----------|
| Bitta `GET /me/headline`, rol serverda | Aynan bitta son + yorliq; qaysi raqam qaysi rolga — server hal qiladi | ✓ |
| Rol boshiga alohida marshrut | Har rol o'z endpointini chaqiradi | |

**Tanlov:** Bitta marshrut (D-28, D-29)
**Notes:** Uch marshrut = uch haqiqat, ular vaqt bilan ajralib ketadi. Va
muhimi: ⛔ **kassir tizim summasini ko'rmasligi kerak** (6-faza T-06-53/59,
ko'r deklaratsiya) — ruxsatni **server** hal qilishi kerak, klient
so'ramasligi. Javobda ikkinchi son bo'lmasligi 6-fazaning T-06-75 naqshida
(ko'rinadigan sonlar **to'plami**) o'lchanadi.

---

## Til va matn manbai (BOT-02, uchala locale)

| Option | Description | Selected |
|--------|-------------|----------|
| Bot o'z Babel katalogi, atamalar YAGONA (darvoza bilan) | aiogram i18n; kalit atamalar frontend bilan solishtiriladi | ✓ |
| Frontend `messages/*.json` ni bot ham o'qisin | Bitta fayl, drift imkonsiz | |

**Tanlov:** Alohida katalog + atama darvozasi (D-30, D-31)
**Notes:** Umumiy fayl jozibali, lekin u servis chegarasini teshadi (D-08
bilan zid) va ICU/Babel formatlari bir xil emas. O'rniga drift **darvoza**
bilan ushlanadi: «qarz», «patta», «rasta», «smena» ikkala manbada bir xil
so'z bo'lishi test bilan o'lchanadi.

---

## Claude's Discretion

Quyidagilar implementatsiya tafsiloti sifatida rejalashtirish va tadqiqotga
qoldirildi: jadval/ustun nomlari; webhook vs long-polling; outbox worker'ning
`taskiq` vazifasi bo'lishi yoki alohida sikl; retry backoff egri chizig'i;
case ro'yxatining sahifalash usuli; `reconciliation_cases` ↔
`billing_anomalies` kompozit FK shakli.

## Deferred Ideas

- Direktor botining **buyruq** yuzasi — bu fazada direktor faqat **oluvchi**
- Sotuvchi botidan to'lov/da'vo — CASH-05 bir tomonlama
- `V2-CASH-05` kassir offline-lite (`REQUIREMENTS.md:93`)
- `deferred-items.md` 9-band (ism joini 50 ta sahifa chegarasi) — 8-faza
- `deferred-items.md` 3-band (`PUT /camera-zones` istisnosi) — 05-06 merosi
- 5-fazadan meros flaky test (`deferred-items.md` 1-band)
