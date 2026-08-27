---
status: partial
phase: 07-nomuvofiqlik-bildirishnoma-va-botlar
source: [07-VALIDATION.md, 07-RESEARCH.md, 07-UI-SPEC.md, 07-CONTEXT.md]
started: 2026-08-12
updated: 2026-08-12
---

## Bu fazada nima O'LCHANDI va nima O'LCHANMADI

`05-HUMAN-UAT.md` ning qoidasi shu yerda ham amal qiladi: ro'yxat faqat
ochiq bandlarni sanaydi, lekin YOPILGANINI ham nomlash kerak — aks holda
keyingi o'quvchi ro'yxatning qisqaligini «hammasi ishlayapti» deb
o'qirdi.

Fazaning beshala mezoni `tests/integration/test_phase7_criteria.py` da
**bitta buyruq** bilan o'lchanadi va meta-darvozalari (mezon boshiga
bitta test · AST bilan soxtalashtirish taqig'i · `respx` ning
`assert_all_mocked` bandi · reyestr nazorati · seed egaligi) yashil.
Baza — HAQIQIY `postgres:18.4`, marshrutlar — HAQIQIY FastAPI grafi,
jo'natuvchi — HAQIQIY `AlertSender`.

⛔⛔ **BU FAZADA CHEGARA BIRINCHI MARTA OCHILADI VA U SHU YERDA
BIRINCHI TURADI: XABAR TELEGRAM SERVERLARIGA CHIQADI.**

6-fazada butun tizim ishonch chegarasi ichida edi: har bayt VPS'da
qolardi va har foydalanuvchi autentifikatsiya qilingan xodim edi. Bu
fazada sotuvchi — **xodim emas** — tizimga kiradi va har xabar O'zR
data-rezidentlik chegarasidan **tashqariga** chiqadi.

CI'da haqiqiy Telegram **YO'Q** va bo'lishi ham mumkin emas. Mezon
moduli mahsulot jo'natuvchisini **oxirigacha** yuritadi va `respx`
faqat **tarmoq chegarasini** tutadi — ya'ni o'lchanadigan narsa
**chiqqan HTTP so'rovi**. Bu «xabar yaratildi» dan ancha kuchli, lekin
u **«Telegram uni qabul qildi»** DEGANI EMAS. Aynan shu farq quyidagi
1-bandning butun mazmuni.

⚠ Bu ro'yxat `07-VALIDATION.md` ning **Manual-Only Verifications**
jadvali bilan **bir xil to'plam emas**: u yerda ikkita band bor (ular
`nyquist_compliant` hisob-kitobiga kiradi va bu yerda **#2** va **#3**
bo'lib turadi), bu yerda esa yettitasi — qolgan beshtasi **qo'shimcha
operatsion va mahsulot bandlari** bo'lib, hisob-kitobga KIRMAYDI.
Ikkala ro'yxat bir-biriga ZID bo'lmasligi shart va ular birga o'qiladi.

---

## Current Test

[inson tekshiruvini kutmoqda — fazaning muhandislik yetkazmalari
tugallandi va beshala mezon yashil; bu bandlar oqimni bloklamaydi]

## Tests

### 1. HAQIQIY TELEGRAM YETKAZISHI — jonli token bilan

**Nega avtomatlashtirib bo'lmaydi:** CI'da bot tokeni YO'Q va bo'lmaydi
ham (`07-RESEARCH.md` § Environment Availability). Haqiqiy Bot API ga
chiqish testni tashqi xizmatga, tarmoqqa va **haqiqiy sirga** bog'lardi;
mezon moduli esa aksincha, `assert_all_mocked=True` bilan tashqariga
chiqishni **imkonsiz** qiladi (T-07-97). Ya'ni «so'rov to'g'ri
shakllandi» o'lchangan, «Telegram uni qabul qildi» esa **o'lchanmagan**.

**Egasi:** Ops
**Tetigi:** birinchi deploy (pilotdan oldin)

expected: real token bilan `notify.outbox_tick` bir marta yuguradi;
direktorning chatiga kechki va ertalabki dayjest **yetib keladi**;
`notification_outbox` da o'sha qatorlar `delivered` bo'ladi va
`provider_message_id` **nol emas**. ⛔ Sinov **test bozorida** va
**test chatida** bajariladi — real sotuvchilarning raqamlari bilan emas.
result: [pending]

### 2. «YETKAZILDI» SO'ZINING SOTUVCHI UCHUN MA'NOSI

**Nega avtomatlashtirib bo'lmaydi:** Telegram Bot API yetkazilganlik
kvitansiyasini **BERMAYDI** — `sendMessage` faqat `Message` qaytaradi
(`07-RESEARCH.md` Key Finding 4). Shuning uchun `delivered` =
«Telegram 200 qaytardi va `message_id` berdi», ya'ni xabar **chatga
joylandi** — **«sotuvchi o'qidi» EMAS**. Kod buni to'g'ri yozadi
(semantika `enums.py`, `outbox.py` va `test_outbox.py` da BIR XIL) va
yuza uni ko'rsatadi. O'lchanmagani — **nizoda direktor va sotuvchi bu
farqni tushunadimi**.

**Egasi:** direktor (mahsulot egasi kuzatadi)
**Tetigi:** pilotning birinchi «xabar kelmadi» nizosi

expected: direktor `GET /reconciliation/delivery` yuzasidagi holat
matnini o'qib, sotuvchiga **o'z so'zlari bilan** tushuntira oladi:
«tizim xabarni Telegramga topshirdi» va «siz uni ochdingiz» — ikki
**boshqa** fakt. Tushuntira olmasa — nuqson **matnda**, kodda emas:
yorliq matni `07-UI-SPEC.md` §12 bo'yicha qayta yoziladi.
result: [pending]

### 3. BOT MATNLARINING SOTUVCHI UCHUN TUSHUNARLILIGI

**Nega avtomatlashtirib bo'lmaydi:** glossariy parity **mexanik**
o'lchangan (G7-9: atama ikkala manbada bir xil, taqiqlangan sinonim
nol, uchala locale kalit-parity). O'lchanmagani — **o'qish savodxonligi
past sotuvchi** «qoldiq», «patta» va «kvitansiya» so'zlarini ajrata
oladimi. Bu lug'at emas, **idrok** savoli.

**Egasi:** mahsulot egasi (bozor adminining yordami bilan)
**Tetigi:** Karmanadagi birinchi dala tashrifi

expected: **5 sotuvchiga** bot ekrani ko'rsatiladi (bog'lanish, qoldiq,
to'lov tarixi, kvitansiya, qarz eslatmasi); har biridan «bu yerda nima
yozilgan?» so'raladi. Qaysi so'z tushunilmagani **nomma-nom** yoziladi.
⛔ Natija «tushundi/tushunmadi» emas, **qaysi so'z** — tuzatish
glossariyga kiradi va G7-9 uni keyin mexanik ushlab turadi.
result: [pending]

### 4. `request_contact` TUGMASINING HAQIQIY KLIENTLARDAGI XULQI

**Nega avtomatlashtirib bo'lmaydi:** `bot-tests` `MockedBot` bilan
ishlaydi, ya'ni `Contact` obyektini **test o'zi** yasaydi. D-24 ning
uch qo'riqchisi (`user_id is None`, `user_id != from_user.id`, guruh
chati) shu bilan to'liq o'lchangan — lekin ular **taxminga** tayanadi:
haqiqiy klient `request_contact` bosilganda `Contact.user_id` ni
**sender bilan teng** qilib yuboradi. ⚠ Tadqiqot buni **MEDIUM-HIGH**
ishonch bilan yozgan, ya'ni bu qat'iy fakt emas.

**Egasi:** Ops
**Tetigi:** birinchi deploy (2-band bilan bir tashrifda)

expected: **iOS**, **Android** va **Desktop** klientlarida bittadan
sinov: `request_contact` bosilganda bog'lanish **hosil bo'ladi**;
boshqa odamning kontaktini **qo'lda ulashganda** rad etiladi. Uchtadan
biri boshqacha xulq bersa — bu **bloklovchi** topilma va u D-24 ning
predikatini o'zgartiradi.
result: [pending]

### 5. DEPLOY BANDI — cron jadvali IMPORT PAYTIDA olinadi

**Nega avtomatlashtirib bo'lmaydi:** bu jarayon holati, kod emas.
07-14 beshta vazifani `worker.py` da ro'yxatga oladi va ⛔ **jadval
import paytida** o'qiladi. Ya'ni **qayta ishga tushirilmagan** planer
yangi vazifalarni **umuman ko'rmaydi** va ⛔ **hech qanday xato
chiqmaydi** — jurnal toza, navbat esa mangu bo'sh.

**Egasi:** Ops
**Tetigi:** har deploy (checklist bandi)

expected: `docker compose up -d --force-recreate scheduler worker
bot-service` bajariladi; keyin `system_heartbeats` da **beshala**
komponent (`outbox_tick`, `notify_digest`, `notify_overdue`,
`reconciliation_open` va mavjudlari) `last_seen_at` ni **yangilaydi**.
Yangilamasa — planer eski jadval bilan yuguryapti.
result: [pending]

### 6. BIR TOKENGA BITTA POLLER

**Nega avtomatlashtirib bo'lmaydi:** nosozlik **ikki mashina orasida**
tug'iladi va bitta muhitda ifodalanmaydi. Telegram `getUpdates` ni
bitta token uchun **bitta** klientga beradi: dev mashinasida o'sha
token bilan ikkinchi nusxa ishga tushsa, ⛔ **prod bot jim bo'lib
qoladi** va jurnal **toza** bo'ladi (Pitfall 5).

**Egasi:** Ops (jamoa qoidasi sifatida)
**Tetigi:** birinchi deploydan oldin — token taqsimoti belgilanganda

expected: prod tokeni **faqat** VPS'da; dev uchun **alohida** bot va
alohida token (`@BotFather` da ikkinchi bot). Qoida `ops/` hujjatiga
yoziladi. ⛔ Sinov: dev mashinasida prod tokeni bilan bot ishga
tushirib ko'riladi va prod botining **jim bo'lgani** kuzatiladi —
shundan keyin dev nusxa o'chiriladi.
result: [pending]

### 7. QUIET HOURS VA `overdue_days` STANDARTLARI

**Nega avtomatlashtirib bo'lmaydi:** ikkalasi ham `[ASSUMED]` qaror
(A2: quiet oyna 21:00–08:00; A3: `overdue_days = 3`) va ular
**buyurtmachi bilan tasdiqlanmagan**. Mexanika to'liq o'lchangan —
oyna bozor kesimida ishlaydi, kvitansiya undan **ozod**, eslatma
esa unga **bo'ysunadi** — lekin **RAQAMLARNING O'ZI** taxmin.

**Egasi:** mahsulot egasi (bozor ma'muriyati bilan)
**Tetigi:** pilotning birinchi haftasi

expected: Karmana ma'muriyati bilan ikki savol hal qilinadi: (a) qarz
necha kundan keyin «kechikkan» hisoblanadi; (b) sotuvchiga soat
nechagacha xabar yuborish **maqbul**. Javob `market_notification_settings`
ga yoziladi — ⛔ **kod o'zgarmaydi**, ikkalasi ham bozor kesimidagi
sozlama.
result: [pending]
