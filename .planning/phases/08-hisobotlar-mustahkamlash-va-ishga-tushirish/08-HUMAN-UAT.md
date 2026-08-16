---
status: partial
phase: 08-hisobotlar-mustahkamlash-va-ishga-tushirish
source: [08-CONTEXT.md, 08-VALIDATION.md, 08-05-SUMMARY.md, 08-08-SUMMARY.md, deferred-items.md]
started: 2026-08-16
updated: 2026-08-16
---

## Bu ro'yxat nima va nima EMAS

Bu — **go-live oldi ro'yxati** (D-22 ning ikkinchi yarmi): loyihaning
butun umri davomida to'plangan, CI'da **hech qachon o'lchanmaydigan**
bandlar **bitta joyda**, har biri **egasi**, **tetigi** va **imzosi**
bilan. Operatsion tartib esa `ops/docs/go-live.md` da — u buyruqlarni,
bu fayl esa **imzolarni** saqlaydi.

⛔ **Ro'yxat oldingi fazalarning bandlarini KO'CHIRMAYDI — HAVOLA
qiladi** (6-band). Matnni ikkinchi marta yozish ikki nusxa tug'dirardi
va ular bir kun ajralib ketardi: biri «yopildi» deb belgilanib,
ikkinchisi mangu `pending` bo'lib qolardi.

⚠ **Imzosiz band — bajarilmagan band.** Hech bir mexanik darvoza bu
imzolarning o'rnini bosmaydi va bosishga urinmaydi ham: quyidagi
bandlarning har biri uchun CI'da nima o'lchangani va nima
o'lchanmagani ochiq yozilgan.

### Fazaning mezonlari bilan bog'liqlik

| Mezon | Mexanik qatlam (yashil) | ⛔ IMZO shu yerda |
|-------|-------------------------|-------------------|
| **SC#3** — tiklash mashqi | `tests/integration/test_restore_drill.py` (MEXANIZM) | **1-band** |
| **SC#4** — runbook + uch til | `tests/unit/test_runbook_shape.py` (runbook SHAKLI), `i18n:check` + `glossary.test.mjs` + `error-codes.test.mjs` (parity) | **4-band** |
| **FOUND-07** — zaxira | `test_backup_contract.py`, `test_backup_heartbeat.py` | **1, 2, 3-bandlar** |

---

## Current Test

[inson tekshiruvini kutmoqda — muhandislik yetkazmalari tugallandi;
quyidagi bandlar **go-live'ni** bloklaydi, ijro oqimini emas]

## Tests

### 1. FOUND-07 (SC#3) — REAL TOZA SERVERDA TIKLASH MASHQI

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ops** | **VPS deploy** (pilotdan oldin) | [ ] `____________` sana: `______` |

⛔ **BU BANDSIZ SC#3 NING IMZOSI QO'YILMAYDI.**
`tests/integration/test_restore_drill.py` faqat **MEXANIZMNI**
o'lchaydi: `pg_dump` -> toza `postgres:18.4-trixie` konteyneri ->
uchta smoke da'vosi. U **restic'ga umuman tegmaydi** — CI konteynerida
offsite rekvizitlar ham, `restic` binari ham yo'q. Ya'ni «offsite
repodan tiklandi» degan da'vo mexanik qatlamda **umuman
o'lchanmagan** va o'lchanishi ham mumkin emas.

⛔⛔ **GRANT QADAMI IMZODAN OLDIN BAJARILADI.** 08-08 da o'lchangan
fakt: manba `44 jadval / 83 policy / 163 GRANT`, tiklangan baza
`44 jadval / 83 policy / **0 GRANT**`. RLS policy'lari saqlanadi,
`sbozor_app` ning huquqlari esa **yo'q** — ya'ni tiklash «muvaffaqiyatli»
ko'rinishi va ilova baribir har so'rovda `permission denied for table`
olishi mumkin. Tartib `ops/docs/go-live.md` §4.4 da, to'rt qadam.

expected: Ops ⛔ **boshqa** (toza) serverda `ops/docs/go-live.md` §4.4
ning to'rt qadamini bajaradi: `restic restore` -> versiya tengligi ->
`pg_restore` -> `npm run migrate` (GRANT'lar). Keyin **ilova o'sha
bazaga ulanadi** va uch da'vo bajariladi: (1) kassir bitta patta
yozuvini ko'radi; (2) direktor kunlik tushum hisobotini ochadi;
(3) audit jurnalining oxirgi qatori joyida. ⛔ Uchalasi ham
`permission denied` **bo'lmasdan** o'tishi SHART — aks holda GRANT
qadami bajarilmagan. Mashqning sanasi, davomiyligi va tiklangan
snapshot ID'si shu yerga yoziladi.
result: [pending]

---

### 2. `RESTIC_PASSWORD` QAYERDA SAQLANGANI YOZILDI VA IKKI ODAM BILADI

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ops** | **birinchi zaxiradan keyin** | [ ] `____________` sana: `______` |

restic repo'si har doim shifrlangan (AES-256 + Poly1305) va uni
ochadigan yagona narsa — shu parol. ⛔ **Parolni tiklash yo'li YO'Q.**

⚠ Nosozlik shakli eng yomon sinfdan: parol faqat VPS ning `.env` ida
qolsa hech nima qizarmaydi, zaxira har kuni muvaffaqiyatli olinadi,
yurak urishi yoziladi va tizim o'zini sog'lom deb ko'rsatadi — va
faqat **falokat kuni**, VPS o'lganda ma'lum bo'ladi: zaxira bor, ochib
bo'lmaydi. Ya'ni bu bandning bajarilmagani **hech qanday signal
bermaydi** (T-08-85). Shuning uchun u imzolanadi.

expected: uch fakt **yozma** tasdiqlanadi (`ops/docs/go-live.md` §4.3):
(1) parol **serverdan tashqarida**, **ikki joyda** — parol menejeri
**va** qog'oz/seyf; (2) uni ⛔ **ikki odam** biladi; (3) saqlash
joylari **nomma-nom** yozilgan (qaysi menejer, qaysi seyf, kimda).
⛔ Parolning O'ZI bu faylga, tiketga yoki chatga **yozilmaydi** —
faqat uning **qayerdaligi**.
result: [pending]

---

### 3. OFFSITE S3 HISOBI OCHILGAN VA `RESTIC_REPOSITORY` TO'LDIRILGAN

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ops / buyurtmachi** | **byudjet qarori** | [ ] `____________` sana: `______` |

⚠⚠ **BU BAND ISHNI BLOKLAMAYDI** (self-service qoidasi 2: dala ishi
oqimni to'xtatmaydi, lekin bajarilmagani KO'RINADI). Kod hisobsiz ham
yozilgan va ishlaydi: besh kalit bo'sh bo'lsa `backup` konteyneri
`backup_unconfigured` yozadi, zaxirani **boshlamaydi**, yurak urishini
**yozmaydi** — va 26 soatdan keyin `backup_stale` (CRITICAL,
`never_suppressed`) alerti chiqadi. Bu **to'g'ri xulq**, kamchilik
emas.

⛔ Talab (D-14): offsite endpoint VPS bilan **boshqa failure domain**
bo'lishi SHART — Backblaze B2 yoki **ikkinchi** Contabo regioni.
Lokal SeaweedFS ning kalitlari (`S3_ACCESS_KEY`/`S3_SECRET_KEY`)
bu yerga **qo'yilmaydi**: o'shanda bitta diskning o'limi bazani,
arxivni va zaxirani birdan olib ketardi.

⚠ Bu band ayni paytda **data-rezidentlik** qarori hamdir: FOUND-07
loyihaning shaxsiy ma'lumotini **birinchi marta** VPS chegarasidan
tashqariga chiqaradi, ya'ni offsite bucket ham O'zbekiston hostingiga
ko'chish ro'yxatiga **kiradi** (`ops/docs/go-live.md` §5).

expected: buyurtmachi bilan ikki savol hal qilinadi: (a) offsite
provayder **kim** (va uning yurisdiksiyasi qayerda); (b) oylik byudjet
**bormi**. Javob «hali yo'q» bo'lsa — bu ⛔ **TO'G'RI** javob va band
**ochiq** qoladi; o'shanda `backup_stale` alerti go-live'dan keyin
ham chiqib turadi va uni ⛔ **o'chirib qo'yish TAQIQLANADI**.

⛔ **HOLAT 2026-08-16 GA (o'lchangan, faraz emas):** `.env` da bironta
`RESTIC*` kaliti **YO'Q** (`grep -c` -> **0**), `.env.example:240` dagi
`RESTIC_REPOSITORY=` **bo'sh**, `compose.yaml:846` esa o'zgaruvchini
kutadi va qiymat berilmagan. Ya'ni `backup` konteyneri
`backup_unconfigured` yozadi, zaxirani boshlamaydi va yurak urishini
yozmaydi — 26 soatdan keyin `backup_stale` (**CRITICAL**,
`never_suppressed`) chiqadi. ⛔ **Bu alertni o'chirib qo'yish
TAQIQLANADI:** u shu bandning ochiqligini ko'rsatuvchi **YAGONA**
signal, va uni o'chirish FOUND-07 ni qog'ozda bajarilgan, amalda
bajarilmagan holatga qaytarardi. Qarorning egasi — **buyurtmachi**
(byudjet) va **Ops** (provayder tanlovi).
result: [pending]

---

### 4. SC#4 — UCH TILLI YAKUNIY TEKSHIRUV (kassir · nazoratchi · admin)

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Mahsulot egasi** (uch rol egasi bilan) | **pilot tayyorgarligi haftasi** | [ ] `____________` sana: `______` |

Mexanik parity **allaqachon darvozada** va bu fazada **yangi mexanik
darvoza yozilmadi** (D-23): `npm --prefix frontend run i18n:check`
(kalit-parity), `glossary.test.mjs` (atama birligi va taqiqlangan
sinonimlar), `error-codes.test.mjs` (reyestrdan oldinga va teskari
skan). Ular **kalit va matn mavjudligini** o'lchaydi. O'lchanmagani —
⛔ **o'sha matnning ona tilida to'g'ri eshitilishi**.

expected: uch rol **har biri O'Z oqimini UCH TILDA** bajaradi
(uz-Latn, uz-Cyrl, ru): kassir — patta yig'ish oqimi; nazoratchi —
ko'r audit va zona tasdig'i; admin — hisobot va eksport. ⛔ Topilgan
har nuqson «yoqmadi» emas, ⛔ **KALIT NOMI** bilan yoziladi
(masalan `snapshots.alertKey.backup_stale`) — shundagina tuzatish
glossariyga kiradi va mexanik darvoza uni keyin ushlab turadi.

⛔ **Uch meros ochiq band shu tekshiruv bilan YOPILADI** va ular
nomma-nom:

| Band | Savol | Bugungi holat |
|------|-------|---------------|
| **07-UI-SPEC O-03** | ru'dagi `патта` ↔ `сбор` ikkiligi | `сбор` ru'da **13 kalitda, ikki ma'noda**: `nav.collect` = amal («Yig'ish») va `ежедневный сбор` = kunlik patta. Taqiqlash 1–6-fazaning 13 kalitini qizartirardi, ya'ni tuzatish **copy migratsiyasi** |
| **05-UI-SPEC O-01** | «Ko'rmasdan tekshirish» atamasi to'g'rimi | «Ko'r audit» kalkasi rad etilgan; ona tilida so'zlashuvchi ko'rigi **bo'lmagan**. Kod `blind_audit` da qoladi |
| **06-UI-SPEC O-07** | «Patta» uchala tilda tabiiy eshitiladimi | `патта` ru'da transliteratsiya bo'lib qoladi; `сбор`/`пошлина` ga o'girish tushunchani **boshqa narsaga** aylantirardi |

⚠ Uchala band ham **atama qarori**, nuqson emas: javob «shu shakl
qoladi» bo'lsa ham band **yopiladi** — muhimi qaror **odam
tomonidan** va uchala tilni ko'rgan holda qabul qilinishi.
result: [pending]

---

### 5. `npm run up` NING DEV MASHINASIDA BIR MARTA QO'LDA TASDIQLANISHI

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Ops / dasturchi** | **birinchi deploydan oldin** | [ ] `____________` sana: `______` |

07-fazaning `deferred-items.md` **№5** ining **ochiq qolgan** qismi.
Yopilgan yarmi: `scripts.up` ro'yxatiga `bot-service` (07-21) va
`backup` (08-05) qo'shildi, `bot-tests` prod tokenini meros olmaydi,
va `tests/unit/test_dev_environment.py` ro'yxatdagi HAR servis
`compose.yaml` da mavjudligini qulflaydi. Ochiq qolgani —
⛔ buyruqning **O'ZI** hech qachon uchidan-uchiga yugurtirilmagan.

⚠ Nega yugurtirilmagan (o'lchangan sabab): buyruq standart compose
loyihasiga (`sbozor`) tegadi va ijro muhitida `cv-service` ATAYIN
to'xtatilgan edi (`CV_MODEL_PATH` artefakti yo'q -> konteyner ~1 s da
bir qayta ishga tushib xostning ~80 % CPU sini yeydi). Ajratilgan
loyihada yugurtirish esa image qurishni talab qilardi.

expected: toza dev mashinasida `npm run up` bajariladi va
`docker compose ps` da ⛔ **o'nta** servis `running` bo'ladi:
`db`, `cache`, `storage`, `core-api`, `worker`, `scheduler`,
`cv-service`, `bot-service`, `go2rtc`, `backup`
(`ops/docs/go-live.md` §1.4). Kamroq chiqsa — ro'yxat mahsulot
to'plamidan **ajralgan** va bu №5 ning aynan takrori.
result: [pending]

---

### 6. OLDINGI FAZALARDAN MEROS OCHIQ BANDLAR — HAVOLA BILAN

| Egasi | Tetigi | Imzo |
|-------|--------|------|
| **Har fayl o'z egasi bilan** (quyidagi jadval) | **Karmana dala tashrifi / birinchi deploy** | [ ] `____________` sana: `______` |

⛔ **MATN KO'CHIRILMAYDI — FAQAT HAVOLA.** Bandlarning haqiqat manbai
o'z faylida qoladi; bu yerda ular **sanaladi**, ya'ni go-live oldida
bitta joydan ko'rinadi va hech biri jimgina tushib qolmaydi.

| Manba fayli | Ochiq bandlar | Ular orasidagi ENG OG'IRI |
|-------------|---------------|---------------------------|
| [`03-HUMAN-UAT.md`](../03-nvr-avtomatik-kashfiyoti-va-tarmoq-ulanishi/03-HUMAN-UAT.md) | 6 band (1–6) | ⛔ **CAM-02** — `ip route get` javobi `wg0` ni ko'rsatishi (SC#5 ning 3-da'vosi). CI konteynerida `wg0` **yo'q**, ya'ni band mexanik qatlamga kira olmaydi; skript `ops/scripts/verify-tunnel.sh` va tartib `ops/docs/go-live.md` §3 da |
| [`04-HUMAN-UAT.md`](../04-snapshot-pipeline/04-HUMAN-UAT.md) | 7 band (1–7) | Sifat chegaralarini REAL Karmana kadrida sozlash; 90 kunlik saqlash siyosatining KALENDAR bo'yicha ishlashi; haqiqiy Sentry DSN bilan planer istisnosi |
| [`05-HUMAN-UAT.md`](../05-kamera-zonalari-cv-va-nazoratchi-tasdig-i/05-HUMAN-UAT.md) | 8 band (1–8) | ⛔ **AI-02** — real ONNX artefakti va **oltin to'plam** ustida detektor aniqligi; COCO sinflarining o'zbek bozori mollarida ishlashi; O-01 atamasi (yuqoridagi 4-band bilan **bir yo'lda**) |
| [`06-HUMAN-UAT.md`](../06-billing-va-kassir/06-HUMAN-UAT.md) | 4 band (1–4) | Dalil kadrining nizoda O'QILISHI; kassir oqimining REAL telefonda bajarilishi; O-07 atamasi (4-band bilan **bir yo'lda**) |
| [`07-HUMAN-UAT.md`](../07-nomuvofiqlik-bildirishnoma-va-botlar/07-HUMAN-UAT.md) | 7 band (1–7) | ⛔ **Jonli Telegram** — haqiqiy token bilan yetkazish; «yetkazildi» so'zining sotuvchi uchun ma'nosi; `request_contact` ning iOS/Android/Desktop xulqi; bir tokenga bitta poller |

⚠ **Ikki band 1- va 2-fazadan ham ochiq** va ular go-live'ni
bloklamaydi, lekin ro'yxatning to'liqligi uchun nomlanadi:
[`01-HUMAN-UAT.md`](../01-poydevor-va-tenant-xavfsizligi/01-HUMAN-UAT.md)
(uz-Cyrl imlo sifati, Apple-uslub vizual muvofiqlik) va
[`02-HUMAN-UAT.md`](../02-bozor-domeni-va-yangi-bozor-ustasi/02-HUMAN-UAT.md)
(usta yo'lining foydalanuvchanligi, real Karmana faylining shakli).

expected: go-live oldidan yuqoridagi **beshala** fayl ochiladi va har
bir `result: [pending]` bandi uch holatdan biriga o'tkaziladi:
**bajarildi** (natija o'z faylida yoziladi), **go-live'ni
bloklamaydi** (sabab yoziladi) yoki **V2 ga qoldirildi** (egasi
yoziladi). ⛔ `pending` holida qolgan band — **javobsiz savol**, va
uni javobsiz qoldirish qarori ham **shu yerda** imzolanadi.
result: [pending]
